from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run OpenCV multi-scale template matching against a screenshot.")
    parser.add_argument("--screen", required=True, help="Path to screenshot image")
    parser.add_argument("--templates", required=True, help="Folder containing template PNG files")
    parser.add_argument("--out-image", default="opencv_match_result.png", help="Output annotated image path")
    parser.add_argument("--out-json", default="opencv_match_result.json", help="Output JSON report path")
    parser.add_argument("--min-scale", type=float, default=0.7)
    parser.add_argument("--max-scale", type=float, default=1.3)
    parser.add_argument("--scale-step", type=float, default=0.06)
    parser.add_argument("--threshold", type=float, default=0.75, help="Highlight threshold")
    parser.add_argument("--topk", type=int, default=10, help="How many top matches to draw")
    return parser.parse_args()


def locate_best_multiscale(
    gray_screen,
    template_path: Path,
    min_scale: float,
    max_scale: float,
    scale_step: float,
):
    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None

    th, tw = template.shape[:2]
    best_score = -1.0
    best_rect = None
    best_scale = None

    scale = min_scale
    while scale <= max_scale + 1e-9:
        rw = max(8, int(tw * scale))
        rh = max(8, int(th * scale))
        if rw >= gray_screen.shape[1] or rh >= gray_screen.shape[0]:
            scale += scale_step
            continue

        resized = cv2.resize(template, (rw, rh), interpolation=cv2.INTER_LINEAR)
        result = cv2.matchTemplate(gray_screen, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = float(max_val)
            best_rect = (int(max_loc[0]), int(max_loc[1]), int(rw), int(rh))
            best_scale = float(scale)

        scale += scale_step

    if best_rect is None:
        return None

    return {
        "template": str(template_path.name),
        "score": best_score,
        "scale": best_scale,
        "x": best_rect[0],
        "y": best_rect[1],
        "w": best_rect[2],
        "h": best_rect[3],
    }


def main() -> int:
    args = parse_args()

    screen_path = Path(args.screen)
    templates_dir = Path(args.templates)
    out_image = Path(args.out_image)
    out_json = Path(args.out_json)

    if not screen_path.exists():
        print(f"ERROR: screen not found: {screen_path}")
        return 1
    if not templates_dir.exists() or not templates_dir.is_dir():
        print(f"ERROR: templates folder not found: {templates_dir}")
        return 1

    screen_bgr = cv2.imread(str(screen_path), cv2.IMREAD_COLOR)
    if screen_bgr is None:
        print(f"ERROR: failed to read screenshot: {screen_path}")
        return 1

    gray_screen = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

    template_files = sorted(templates_dir.glob("*.png"))
    if not template_files:
        print(f"ERROR: no PNG templates found in: {templates_dir}")
        return 1

    results = []
    for template_path in template_files:
        best = locate_best_multiscale(
            gray_screen,
            template_path,
            args.min_scale,
            args.max_scale,
            args.scale_step,
        )
        if best is not None:
            results.append(best)

    results.sort(key=lambda item: item["score"], reverse=True)

    annotated = screen_bgr.copy()
    for idx, item in enumerate(results[: args.topk], start=1):
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        score = item["score"]
        color = (0, 255, 0) if score >= args.threshold else (0, 165, 255)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        label = f"{idx}:{item['template']} {score:.3f}"
        cv2.putText(annotated, label, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    out_image.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_image), annotated)

    report = {
        "screen": str(screen_path),
        "templates": str(templates_dir),
        "min_scale": args.min_scale,
        "max_scale": args.max_scale,
        "scale_step": args.scale_step,
        "threshold": args.threshold,
        "count": len(results),
        "results": results,
    }
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved annotated image: {out_image}")
    print(f"Saved JSON report: {out_json}")
    print("Top matches:")
    for item in results[: min(10, len(results))]:
        print(
            f"- {item['template']}: score={item['score']:.4f}, "
            f"scale={item['scale']:.2f}, xy=({item['x']},{item['y']}), wh=({item['w']},{item['h']})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
