from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


DEFAULT_MEMBRANE_MARKERS = {
    "CD3", "CD4", "CD8", "CD10", "CD11c", "CD20", "CD21", "CD31", "CD44",
    "CD45", "CD45RO", "CD47", "CD56", "CD66b", "CD68", "CD72a", "CD80",
    "CD86", "CD138", "CD163", "MHC_II", "MHCII", "HLA_DR", "HLADR",
    "PDL1", "PD-L1", "aSMA", "SMA", "ERG", "Ecad", "PanCK", "PDGFRb"
}

DEFAULT_NUCLEAR_MARKERS = {"DNA1", "DNA2", "Ir191", "Ir193"}

TIFF_SUFFIXES = (".ome.tiff", ".ome.tif", ".tiff", ".tif")


def strip_tiff_suffix(name: str) -> str:
    lower = name.lower()
    for suffix in TIFF_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return Path(name).stem


def parse_channel_file(path: Path):
    base = strip_tiff_suffix(path.name)
    if "_" in base:
        channel, marker = base.split("_", 1)
    else:
        channel, marker = base, base
    return channel, marker


def channel_sort_key(path: Path):
    channel, marker = parse_channel_file(path)
    match = re.match(r"^(\d+)([A-Za-z].*)?$", channel)
    if match:
        mass = int(match.group(1))
        tail = match.group(2) or ""
    else:
        mass = 10**9
        tail = channel
    return mass, tail, marker


def list_tiff_files(folder: Path):
    files = [
        p for p in folder.iterdir()
        if p.is_file() and p.name.lower().endswith((".tif", ".tiff"))
    ]
    return sorted(files, key=channel_sort_key)


def infer_deepcell(marker: str) -> str:
    marker = marker.strip()
    if marker in DEFAULT_NUCLEAR_MARKERS:
        return "1"
    if marker in DEFAULT_MEMBRANE_MARKERS:
        return "2"
    return ""


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python make_shared_panel.py <roi_dir> <output_panel_csv>")

    roi_dir = Path(sys.argv[1])
    out_csv = Path(sys.argv[2])

    files = list_tiff_files(roi_dir)
    if not files:
        raise FileNotFoundError(f"No TIFF files found in: {roi_dir}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["channel", "name", "keep", "deepcell"]
        )
        writer.writeheader()

        for f in files:
            channel, marker = parse_channel_file(f)
            writer.writerow(
                {
                    "channel": channel,
                    "name": marker,
                    "keep": "1",
                    "deepcell": infer_deepcell(marker),
                }
            )

    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()