# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 프로젝트 개요

MapleSao는 **MapleStory World Studio (MSW)** (Core v26.1.0.0) 기반의 2D SAO(소드 아트 온라인) 스타일 아인크라드 층 공략 게임입니다. 스크립트는 데코레이터, 타입 프로퍼티, 실행 공간 어노테이션을 지원하는 확장 Lua 문법의 `.mlua` 파일로 작성됩니다.

코드 주석 및 게임 내 문자열의 기본 언어는 **한국어**입니다.

## 개발 환경

- **IDE:** VSCode + MSW 디버거
- **런타임:** 독립 빌드/테스트 명령어 없음 — 게임은 전적으로 MSW Studio 내에서 실행
- **타입 정의:** `Environment/NativeScripts/`에 `.d.mlua` 파일 (읽기 전용, 엔진 자동 생성)

## 스크립트 언어 (확장 Lua / .mlua)

MSW 확장 Lua 형식의 주요 구문:

```lua
@Component            -- 엔티티 컴포넌트 스크립트
@Logic                -- 상태 없는 서비스/로직 스크립트 (전역 싱글톤)
@Event                -- 이벤트 타입 정의

script MyComponent extends Component

    property integer myProp = 0          -- 타입 프로퍼티 선언

    @ExecSpace("ServerOnly")             -- 서버 전용 실행
    method void MyMethod()
        -- ...
    end

    @ExecSpace("ClientOnly")             -- 클라이언트 전용 실행
    method void OnMapEnter(Entity map)
        -- ...
    end

end
```

### ExecSpace 어노테이션

- `@ExecSpace("Server")` — 서버에서 실행, 클라이언트에서 RPC 호출 가능
- `@ExecSpace("ServerOnly")` — 서버에서만 실행, RPC 불가
- `@ExecSpace("Client")` — 클라이언트에서 실행, 서버에서 특정 클라이언트로 RPC 호출 가능 (userId 파라미터로 라우팅)
- `@ExecSpace("ClientOnly")` — 클라이언트에서만 실행, RPC 불가
- 기본값은 서버

### 엔진 내장 콜백 메서드

- `OnBeginPlay()` — 엔티티/로직 생성 시 호출
- `OnEndPlay()` — 엔티티/로직 파괴 시 호출
- `OnMapEnter(Entity map)` — 새로운 맵 입장 시 자동 호출 (OnBeginPlay 이후). **반드시 `Entity map` 매개변수 포함**

### 엔티티 위치 접근

`Entity`에는 `GetWorldPosition()` 메서드가 없음. 반드시 `TransformComponent`를 통해 접근:

```lua
local transformComp = self.Entity:GetComponent(TransformComponent)
local pos = transformComp.WorldPosition    -- Vector3
local localPos = transformComp.Position    -- Vector3 (부모 기준)
```

## 아키텍처

### 게임 흐름

10층 구조의 아인크라드 탑: **Town(안전지대)** → **Battle(전투)** → **Boss(보스)**

각 층은 독립된 맵 파일(`map01`~`map10`)으로 구성되며, 포탈을 통해 이동합니다.

### 서비스 레이어 (전역 싱글톤)

`@Logic` 스크립트는 언더스코어 접두사 전역 변수로 접근:

| 전역 변수 | 역할 |
|-----------|------|
| `_FloorData` | 10층 데이터 정의 (이름, 타입, 몬스터, 보스, EXP) |
| `_FloorManager` | 층 이동, 보스룸 인스턴싱, 클리어 판정, 보상 분배 |
| `_FloorProgress` | 플레이어별 층 진행도 (현재 층, 최고 층, 킬카운트, 보스 키) |
| `_PlayerDataManager` | DataStorageService 기반 플레이어 데이터 영속성 |
| `_LevelSystem` | 레벨 1-50, EXP, 스탯 포인트 (HP/ATK) |
| `_MonsterData` | 몬스터 타입별 기본 스탯, 층별 스케일링 |
| `_FloorInfoUI` | 상단 층 정보 UI 업데이트 |
| `_UIToast` | 토스트 알림 메시지 표시 |
| `_UIPopup` | 팝업 다이얼로그 표시 |
| `_UserService` | 엔진 내장 — 플레이어 조회, LocalUserId |
| `_TimerService` | 엔진 내장 — SetTimerRepeat, SetTimerOnce, ClearTimer |
| `_RoomService` | 엔진 내장 — 인스턴스 룸, SharedMemory |
| `_SpawnService` | 엔진 내장 — SpawnByModelId로 런타임 엔티티 생성 |
| `_EntityService` | 엔진 내장 — Destroy, IsValid, GetEntitiesByTag |
| `_DataStorageService` | 엔진 내장 — 유저별 데이터 저장/로드 |

### 컴포넌트 스크립트

| 스크립트 | 역할 |
|----------|------|
| `FloorPortal` | 포탈 컴포넌트 (상행/하행/보스, 트리거 기반 활성화) |
| `MonsterSpawner` | 배틀맵 스폰존, 타이머 기반 자동 리스폰 |
| `MonsterComponent` | 몬스터 HP/피격/사망/EXP 지급 처리 |

### 데이터 영속성

`DataStorageService`로 플레이어별 데이터 저장:
- 키: `"highestFloor"`, `"currentFloor"`, `"floorCleared"`, `"level"`, `"exp"`, `"statPoints"`, `"statHp"`, `"statAtk"`
- 직렬화: `tostring()` / `tonumber()`으로 문자열 변환
- floorCleared: 쉼표 구분 문자열 (`"1,2,4"`)

### 충돌 그룹

6종: Default, TriggerBox, HitBox, Interaction, Portal, Climbable

### 전투 시스템 (엔진 내장)

- `AttackComponent` — `CalcDamage`, `CalcCritical`, `IsAttackTarget` 오버라이드로 커스텀 전투
- `HitComponent` — `OnHit` 핸들러로 피격 처리
- `StateComponent` — `IDLE`/`DEAD` 상태 머신
- `AIChaseComponent` / `AIWanderComponent` — BehaviorTree 기반 몬스터 AI

## 파일 구조

### 스크립트 파일 규칙

각 `.mlua` 파일에는 대응하는 `.codeblock` 파일 필요:
- `.codeblock`의 `Type` 필드: `5` = @Logic, `1` = @Component
- 고유 UUID 형식 ID 필요

```
RootDesk/MyDesk/Script/
├── Floor/          -- 층 시스템 (FloorData, FloorManager, FloorProgress, FloorPortal)
├── Player/         -- 플레이어 (PlayerDataManager, LevelSystem)
├── Monster/        -- 몬스터 (MonsterData, MonsterSpawner, MonsterComponent)
└── CommonUI/       -- UI (FloorInfoUI, UIToast, UIPopup)
```

### 기타 디렉토리

- `Environment/NativeScripts/` — 엔진 API 타입 정의 (읽기 전용)
- `map/` — 맵 파일 (`map01`~`map10`)
- `ui/` — UI 정의 파일 (DefaultGroup, PopupGroup, FloorInfoGroup, ToastGroup)
- `Global/` — 월드 설정, 충돌 그룹, DefaultPlayer 모델

## 네이밍 규칙

- 비공개 프로퍼티: 언더스코어 접두사 (`_playerLevels`, `_spawnedMonsters`)
- 전역 서비스: 언더스코어 접두사 (`_FloorData`, `_LevelSystem`)
- 상수: UPPER_SNAKE_CASE (`FLOOR_TYPE_TOWN`, `MAX_LEVEL`)
- 열거형 문자열: 소문자 (`"town"`, `"battle"`, `"boss"`)

## 작업 규칙

- 모든 작업 후에는 오류가 있는지 체크한 후 오류가 있을 경우 수정한다.
- 오류 체크 과정을 마친 후에는 코드 최적화를 해야하는 부분이 있는지 검토한다.
- `Entity`의 위치는 반드시 `TransformComponent`를 통해 접근한다 (`GetWorldPosition()` 사용 금지).
- `OnMapEnter`는 반드시 `Entity map` 매개변수를 포함해야 한다.
- 새 스크립트 생성 시 `.mlua`와 `.codeblock` 파일을 함께 생성한다.
