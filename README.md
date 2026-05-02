# imc-nextflow-pipeline

[![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A523.10-brightgreen.svg)](https://www.nextflow.io/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![Steinbock](https://img.shields.io/badge/steinbock-0.16.1-orange.svg)](https://bodenmillergroup.github.io/steinbock/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Institutional](https://img.shields.io/badge/institution-Humanitas%20IRCCS-teal.svg)](https://www.humanitas.it/)

> **A reproducible, containerised Nextflow pipeline for end-to-end Imaging Mass Cytometry (IMC) data processing — from raw per-channel TIFF acquisition files through Steinbock-based cell segmentation, morphological feature extraction, and single-cell data export in multiple formats.**

---

## Abstract

Imaging Mass Cytometry (IMC) enables simultaneous quantification of >40 protein markers at single-cell resolution in intact tissue sections, but the absence of standardised, reproducible processing workflows remains a barrier to multi-cohort studies. Here we present **imc-nextflow-pipeline**, a Nextflow DSL2 pipeline that automates the full IMC data processing cascade — channel validation, multi-channel image stacking, panel generation, deep-learning-based cell segmentation using the Steinbock framework with DeepCell (Mesmer), and multi-format single-cell feature export. All computational steps execute within pinned Docker containers, ensuring full reproducibility across computing environments. The pipeline produces analysis-ready outputs compatible with standard single-cell frameworks including AnnData/Scanpy and graph-based neighbourhood analysis tools. This pipeline was developed as part of the **Sarcoma Microenvironment Score (SMS)** project at Humanitas Research Hospital (IRCCS), Milan.

---

## Pipeline summary

The pipeline executes the following steps in order:

1. **Channel validation** — Cross-ROI consistency check: verifies that all ROI directories contain an identical set of channel TIFF files before any processing begins (`VALIDATE_ROI_CHANNELS`)
2. **Panel generation** — Constructs `panel.csv` from the first ROI, assigning DeepCell segmentation labels (nuclear = `1`, membrane = `2`) based on canonical IMC marker names (`MAKE_SHARED_PANEL`)
3. **Channel stacking** — Sorts per-channel TIFFs by isotope mass number and stacks them into a single multi-channel TIFF per ROI (`STACK_ROI`)
4. **Image metadata** — Generates `images.csv` encoding image dimensions and channel count for Steinbock compatibility (`MAKE_IMAGES_CSV`)
5. **Cell segmentation** — Runs Steinbock DeepCell (Mesmer) segmentation with min–max normalisation to produce single-cell masks (`STEINBOCK_SEGMENT`)
6. **Intensity measurement** — Extracts per-cell mean marker intensities from segmentation masks (`STEINBOCK_MEASURE_INTENSITIES`)
7. **Morphological features** — Computes region properties (area, eccentricity, major/minor axis length, etc.) for each segmented cell (`STEINBOCK_MEASURE_REGIONPROPS`)
8. **Neighbourhood graphs** — Constructs cell–cell spatial neighbourhood graphs by pixel expansion with `dmax = 4` (`STEINBOCK_MEASURE_NEIGHBORS`)
9. **Single-cell export** — Exports combined single-cell feature tables as `cells.csv`, `cells.h5ad` (AnnData), and `GraphML` cell graphs (`STEINBOCK_EXPORT_CSV`, `STEINBOCK_EXPORT_ANNDATA`, `STEINBOCK_EXPORT_GRAPHS`)

---

## Workflow diagram

```
 data/Tiffs/
 ├── ROI_001/   ← per-channel TIFFs (e.g. 191Ir_DNA1.tiff, 145Nd_CD8.tiff)
 ├── ROI_002/
 └── ...
        │
        ▼
┌─────────────────────────┐
│  VALIDATE_ROI_CHANNELS  │  → results/validation/channel_check.json
└────────────┬────────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌──────────────┐  ┌───────────┐
│ MAKE_SHARED  │  │ STACK_ROI │  → results/stacked/<ROI>.tiff
│    PANEL     │  └─────┬─────┘
└──────┬───────┘        │
       │          ┌─────▼──────────┐
       │          │ MAKE_IMAGES_CSV │  → results/images.csv
       │          └─────┬──────────┘
       │                │
       └────────┬───────┘
                ▼
      ┌──────────────────┐
      │ STEINBOCK_SEGMENT│  → results/steinbock/masks/
      └────────┬─────────┘
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
┌──────────┐ ┌───────────┐ ┌───────────┐
│INTENSITIES│ │REGIONPROPS│ │ NEIGHBORS │
└────┬─────┘ └─────┬─────┘ └─────┬─────┘
     │             │              │
     └──────┬──────┘              │
            ▼                     ▼
  ┌──────────────────┐   ┌──────────────────┐
  │   EXPORT_CSV     │   │   EXPORT_GRAPHS  │
  │   EXPORT_ANNDATA │   │   (GraphML)      │
  └──────────────────┘   └──────────────────┘
  → cells.csv
  → cells.h5ad
  → graphs/
```

---

## Requirements

| Dependency | Version | Purpose |
|---|---|---|
| [Nextflow](https://www.nextflow.io/) | ≥ 23.10 | Workflow execution |
| [Docker](https://www.docker.com/) | any | Container runtime |
| `imc-python-tools` | local build | Channel stacking, panel generation, validation |
| [Steinbock](https://bodenmillergroup.github.io/steinbock/) | 0.16.1 | Segmentation, measurement, export |

Python packages within `imc-python-tools`: `numpy`, `tifffile` (Python 3.11-slim base)

---

## Installation

**Step 1 — Install Nextflow**

```bash
curl -s https://get.nextflow.io | bash
mv nextflow ~/bin/
```

**Step 2 — Clone this repository**

```bash
git clone https://github.com/ComputationalPathologyLab/imc-nextflow-pipeline.git
cd imc-nextflow-pipeline
```

**Step 3 — Build the local Python tools container**

```bash
docker build -f Dockerfile.python -t imc-python-tools .
```

---

## Input

Organise raw IMC acquisition data as one subdirectory per ROI under a single parent directory. Each ROI directory must contain one single-plane TIFF file per acquired channel, named using the convention `{isotope}_{marker}.tiff` (e.g. `191Ir_DNA1.tiff`, `145Nd_CD8.tiff`). Channels are sorted by isotope mass number prior to stacking.

```
data/
└── Tiffs/
    ├── ROI_001/
    │   ├── 191Ir_DNA1.tiff
    │   ├── 193Ir_DNA2.tiff
    │   ├── 141Pr_SMA.tiff
    │   ├── 145Nd_CD8.tiff
    │   ├── 148Nd_CD4.tiff
    │   └── ...
    ├── ROI_002/
    │   └── ...              ← must share identical channel set
    └── ...
```

> **Note:** All ROI directories must share an identical channel set. The pipeline will raise an error and halt before processing if any mismatch is detected.

---

## Quick start

```bash
nextflow run main.nf -profile docker
```

**With custom paths:**

```bash
nextflow run main.nf -profile docker \
  --input /path/to/Tiffs \
  --outdir /path/to/results
```

---

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `--input` | `data/Tiffs` | Path to parent directory containing per-ROI subdirectories |
| `--outdir` | `results` | Root output directory |
| `--python` | `python` | Python executable (overridden inside containers) |
| `--steinbock_image` | `ghcr.io/bodenmillergroup/steinbock:0.16.1` | Steinbock container image |

---

## Output

```
results/
├── validation/
│   └── channel_check.json        # reference ROI, channel names, n_channels, n_rois, status
├── panel/
│   └── panel.csv                 # channel, name, keep=1, deepcell label (1=nuclear, 2=membrane)
├── stacked/
│   └── <ROI_name>.tiff           # (C × H × W) multi-channel TIFF, channels sorted by mass
├── images.csv                    # image name, width_px, height_px, num_channels
├── steinbock/
│   ├── masks/                    # per-ROI single-cell segmentation masks
│   ├── intensities/              # per-cell mean marker intensities
│   ├── regionprops/              # morphological features per cell
│   ├── neighbors/                # cell neighbourhood graphs (expansion, dmax=4)
│   ├── cells.csv                 # combined single-cell feature table (intensities + regionprops)
│   ├── cells.h5ad                # AnnData object for Scanpy / scverse workflows
│   └── graphs/                   # cell graphs in GraphML format
├── timeline.html                 # Nextflow process execution timeline
├── report.html                   # Nextflow run report (CPU, memory, duration)
└── trace.txt                     # per-process resource usage trace
```

---

## Methods

### Channel validation

Prior to processing, `VALIDATE_ROI_CHANNELS` scans all ROI directories and compares TIFF file lists against a reference (first ROI, sorted lexicographically). Any missing or additional channels in any ROI raise a descriptive `ValueError` that reports the mismatched ROI and its channel list, preventing propagation of incomplete data into downstream steps.

### Panel generation

`MAKE_SHARED_PANEL` parses channel filenames from the reference ROI and assigns DeepCell segmentation labels based on curated sets of canonical nuclear markers (`DNA1`, `DNA2`, `Ir191`, `Ir193`) and membrane markers (`CD3`, `CD4`, `CD8`, `CD45`, `PanCK`, `aSMA`, and 20+ others). Channels not matching either set are written with an empty `deepcell` field and preserved for downstream measurement.

### Image stacking

`STACK_ROI` sorts per-channel TIFFs by isotope mass number (parsed from the filename prefix, e.g. `191` from `191Ir_DNA1.tiff`) and concatenates single-plane 2-D arrays into a `(C × H × W)` stack using `numpy.stack`. Spatial dimension consistency across channels is enforced; mismatches raise an error before writing.

### Cell segmentation

Segmentation is performed via the Steinbock framework (`steinbock:0.16.1`) using the **DeepCell Mesmer** model with `--minmax` intensity normalisation. Steinbock receives the stacked TIFF images, panel, and image metadata as inputs and produces binary cell masks as TIFF files.

### Feature extraction

Per-cell features are extracted in three parallel processes:

- **Intensities** (`STEINBOCK_MEASURE_INTENSITIES`): mean marker intensity per cell per channel
- **Region properties** (`STEINBOCK_MEASURE_REGIONPROPS`): morphological descriptors (area, eccentricity, major/minor axis length, centroid coordinates)
- **Neighbourhood graphs** (`STEINBOCK_MEASURE_NEIGHBORS`): cell–cell spatial adjacency by pixel expansion with maximum distance `dmax = 4`

### Data export

Single-cell data are exported in three complementary formats:

| Format | File | Compatible tools |
|---|---|---|
| CSV | `cells.csv` | pandas, R data frames |
| AnnData | `cells.h5ad` | Scanpy, squidpy, scverse |
| GraphML | `graphs/` | NetworkX, iGraph, Cytoscape |

---

## Reproducibility

All pipeline steps execute within pinned, versioned Docker containers:

| Container | Version | Steps |
|---|---|---|
| `imc-python-tools` | local (Python 3.11-slim) | Validation, stacking, panel, image CSV |
| `ghcr.io/bodenmillergroup/steinbock` | `0.16.1` | Segmentation, measurement, export |

Nextflow generates `timeline.html`, `report.html`, and `trace.txt` for every run, providing full process-level resource and timing records.

---

## Credits

Developed by **Rashid Hussain, Ph.D., RSci, MRSC** at the **Computational Pathology Lab**, Humanitas Research Hospital (IRCCS), Milan, Italy, as part of the Sarcoma Microenvironment Score (SMS) project.

This pipeline would not have been possible without the tools and infrastructure provided by:

- The [Bodenmiller Group](http://www.bodenmillerlab.com/) (University of Zurich) — [Steinbock](https://github.com/BodenmillerGroup/steinbock) framework
- The [Van Valen Lab](https://vanvalenlab.com/) — [DeepCell / Mesmer](https://github.com/vanvalenlab/deepcell-tf) segmentation model
- [Nextflow](https://www.nextflow.io/) — Di Tommaso et al., *Nat Biotechnol* (2017)

---

## Citation


Please also cite the following tools used by the pipeline:

> **Steinbock:**
> Windhager J., Bodenmiller B., Eling N. (2023). An end-to-end workflow for multiplexed image processing and analysis. *Nature Protocols*, 18, 3565–3613. [doi:10.1038/s41596-023-00881-0](https://doi.org/10.1038/s41596-023-00881-0)

> **DeepCell / Mesmer:**
> Greenwald N.F. *et al.* (2022). Whole-cell segmentation of tissue images with human-level performance using large-scale data annotation and deep learning. *Nature Biotechnology*, 40, 555–565. [doi:10.1038/s41587-021-01094-0](https://doi.org/10.1038/s41587-021-01094-0)

> **Nextflow:**
> Di Tommaso P. *et al.* (2017). Nextflow enables reproducible computational workflows. *Nature Biotechnology*, 35, 316–319. [doi:10.1038/nbt.3820](https://doi.org/10.1038/nbt.3820)

---

## Contributions and support

Contributions are welcome. Please open an issue or pull request via [GitHub](https://github.com/ComputationalPathologyLab/imc-nextflow-pipeline).

**Contact:** Rashid Hussain — [rashid.bioinfo@gmail.com](mailto:rashid.bioinfo@gmail.com) | [rashid-bioinfo.github.io](https://rashid-bioinfo.github.io)
