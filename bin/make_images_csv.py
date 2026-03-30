from __future__ import annotations

import csv
import sys
from pathlib import Path

import tifffile as tiff


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python make_images_csv.py <stacked_dir> <output_csv>"
        )

    stacked_dir = Path(sys.argv[1])
    output_csv = Path(sys.argv[2])

    if not stacked_dir.exists():
        raise FileNotFoundError(f"Stacked directory does not exist: {stacked_dir}")
    if not stacked_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {stacked_dir}")

    tiff_files = sorted(stacked_dir.glob("*.tiff"))
    if not tiff_files:
        raise FileNotFoundError(f"No stacked TIFF files found in: {stacked_dir}")

    rows = []
    for f in tiff_files:
        img = tiff.imread(f)

        if img.ndim != 3:
            raise ValueError(f"{f.name} is not 3D. Shape: {img.shape}")

        channels, height, width = img.shape

        rows.append(
            {
                "image": f.stem,
                "width_px": width,
                "height_px": height,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["image", "width_px", "height_px"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {output_csv}")
    print(f"Number of images: {len(rows)}")


if __name__ == "__main__":
    main()