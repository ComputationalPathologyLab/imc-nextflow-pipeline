from __future__ import annotations

import json
import sys
from pathlib import Path


def list_tiff_names(folder: Path) -> list[str]:
    return sorted(
        [
            p.name
            for p in folder.iterdir()
            if p.is_file() and p.name.lower().endswith((".tif", ".tiff"))
        ]
    )


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage: python validate_roi_channels.py <output_json> <roi_dir1> <roi_dir2> ..."
        )

    output_json = Path(sys.argv[1])
    roi_dirs = [Path(x) for x in sys.argv[2:]]

    if not roi_dirs:
        raise ValueError("No ROI directories were provided.")

    for roi in roi_dirs:
        if not roi.exists():
            raise FileNotFoundError(f"ROI directory does not exist: {roi}")
        if not roi.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {roi}")

    reference_roi = roi_dirs[0]
    reference_channels = list_tiff_names(reference_roi)

    if not reference_channels:
        raise ValueError(f"No TIFF files found in reference ROI: {reference_roi}")

    mismatches: list[dict] = []

    for roi in roi_dirs[1:]:
        current_channels = list_tiff_names(roi)
        if current_channels != reference_channels:
            mismatches.append(
                {
                    "roi": roi.name,
                    "channels": current_channels,
                }
            )

    if mismatches:
        lines = []
        lines.append("Channel mismatch detected across ROI folders.")
        lines.append(f"Reference ROI: {reference_roi.name}")
        lines.append("Reference channel list:")
        lines.extend(reference_channels)
        lines.append("")
        lines.append("Mismatched ROI folders:")
        for item in mismatches:
            lines.append(f"ROI: {item['roi']}")
            lines.extend(item["channels"])
            lines.append("")
        raise ValueError("\n".join(lines))

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(
            {
                "reference_roi": reference_roi.name,
                "n_channels": len(reference_channels),
                "channels": reference_channels,
                "n_rois": len(roi_dirs),
                "status": "ok",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Validated {len(roi_dirs)} ROI folders")
    print(f"Reference ROI: {reference_roi.name}")
    print(f"Channel count: {len(reference_channels)}")
    print(f"Wrote: {output_json}")


if __name__ == "__main__":
    main()