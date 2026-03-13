"""
map 파일에서 맵 레이어(MapleMapLayer) + 타일 배치(TileMap) 데이터만 추출하는 스크립트.

사용법:
    python extract_tile_layers.py <map_file> [--layer <layer_number>]

예시:
    python extract_tile_layers.py ../../map/map01.map          # 전체 레이어 추출
    python extract_tile_layers.py ../../map/map01.map --layer 1 # Layer1만 추출
    python extract_tile_layers.py ../../map/map01.map --layer 2 # Layer2만 추출
"""

import json
import argparse
import sys
from pathlib import Path


def extract_tile_layers(map_path: str, target_layer: int | None = None) -> dict:
    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data["ContentProto"]["Entities"]

    # MapleMapLayer와 TileMap 엔티티 분류
    map_layers = {}
    tile_maps = {}

    for entity in entities:
        path = entity.get("path", "")
        components = entity.get("jsonString", {}).get("@components", [])

        for comp in components:
            comp_type = comp.get("@type", "")

            if comp_type == "MOD.Core.MapLayerComponent":
                sorting_index = comp.get("LayerSortOrder", -1)
                map_layers[sorting_index] = entity
                break

            if comp_type == "MOD.Core.TileMapComponent":
                sorting_layer = comp.get("SortingLayer", "")
                # "MapLayer0" -> 0
                try:
                    idx = int(sorting_layer.replace("MapLayer", ""))
                except ValueError:
                    idx = -1
                tile_maps[idx] = entity
                break

    # 레이어 번호 기준으로 매칭 (Layer1 = index 0, Layer2 = index 1, ...)
    result = {}
    all_indices = sorted(set(map_layers.keys()) | set(tile_maps.keys()))

    for idx in all_indices:
        layer_num = idx + 1  # 사용자 친화적 번호 (1-based)

        if target_layer is not None and layer_num != target_layer:
            continue

        layer_info = {}
        if idx in map_layers:
            layer_info["MapleMapLayer"] = map_layers[idx]["jsonString"]
        if idx in tile_maps:
            layer_info["TileMap"] = tile_maps[idx]["jsonString"]

        if layer_info:
            result[f"Layer{layer_num}"] = layer_info

    return result


def main():
    parser = argparse.ArgumentParser(description="맵 파일에서 타일 레이어 데이터 추출")
    parser.add_argument("map_file", help="맵 파일 경로 (.map)")
    parser.add_argument("--layer", type=int, default=None,
                        help="특정 레이어만 추출 (1, 2, 3, ...)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="출력 파일 경로 (미지정 시 stdout)")
    args = parser.parse_args()

    map_path = Path(args.map_file)
    if not map_path.exists():
        print(f"파일을 찾을 수 없습니다: {map_path}", file=sys.stderr)
        sys.exit(1)

    result = extract_tile_layers(str(map_path), args.layer)

    if not result:
        layer_msg = f"Layer{args.layer}" if args.layer else "레이어"
        print(f"{layer_msg} 데이터를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"추출 완료: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
