# pointcloud-etfe-postprocessing

Python tools for post-processing ETFE cushion photogrammetry point clouds to calculate displacement, strain, and stress distributions.

This repository was refactored from three exploratory Jupyter notebooks into a reusable Python package with a command-line interface. The original notebooks are kept as examples, while the core calculations now live under `src/pointcloud_etfe_postprocessing/`.

## What It Does

- Loads photogrammetry Excel workbooks containing `points` and `links` sheets.
- Reorders the sparse point cloud into the original structured grid.
- Builds triangular elements for surface interpolation.
- Calculates node displacement between a reference and deformed point cloud.
- Calculates element-level and point-level principal logarithmic strains.
- Calculates membrane link and point stress distributions from pressure loading.
- Writes reusable CSV outputs and optional figures.

## Repository Layout

```text
.
├── src/pointcloud_etfe_postprocessing/
│   ├── cli.py
│   ├── config.py
│   ├── displacement.py
│   ├── io.py
│   ├── mesh.py
│   ├── plotting.py
│   ├── strain.py
│   └── stress.py
├── tests/
├── Displacement_Calculation.ipynb
├── Strain_Distribution_Calculation.ipynb
├── Stress_Distribution_Calculation.ipynb
├── zxt_*.xlsx
├── pyproject.toml
└── requirements.txt
```

## Installation

Create and activate a virtual environment, then install the package:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If Open3D is slow to install, you can still run displacement and strain after installing the core scientific stack:

```powershell
python -m pip install numpy pandas matplotlib openpyxl pytest
```

Stress calculation requires `open3d`.

## Command-Line Usage

Displacement from a reference point cloud to a deformed point cloud:

```powershell
pointcloud-etfe displacement --reference zxt_300Pa.xlsx --target zxt_13000Pa.xlsx --out-dir outputs
```

Principal strain:

```powershell
pointcloud-etfe strain --reference zxt_300Pa.xlsx --target zxt_9000Pa.xlsx --out-dir outputs
```

Stress distribution:

```powershell
pointcloud-etfe stress --input zxt_14000Pa_failure.xlsx --out-dir outputs --boundary-scale 1.8
```

Batch displacement for all non-failure `zxt_*.xlsx` files:

```powershell
pointcloud-etfe batch --data-dir . --reference zxt_300Pa.xlsx --out-dir outputs
```

Optional plots can be created with `--plot` when `matplotlib` is installed.

## Important Parameters

The original notebooks used fixed values. They are now command-line options:

- `--rows-x` and `--rows-y`: grid dimensions, default `16 x 16`
- `--target-spacing`: nominal target spacing, default `100`
- `--boundary-scale`: boundary triangle filter scale, default `1.3` for displacement/strain and `1.8` for stress
- `--pressure-mpa`: membrane pressure for stress, default `0.014`
- `--thickness-mm`: membrane thickness for stress, default `0.25`

## Input Workbook Format

Each Excel workbook is expected to include:

`points` sheet:

- `point_ID`
- `point_x`
- `point_y`
- `point_z`

`links` sheet:

- `link_ID`
- `point1_ID`, `point1_x`, `point1_y`, `point1_z`
- `point2_ID`, `point2_x`, `point2_y`, `point2_z`
- `length`
- `angle`

## Tests

Run the test suite:

```powershell
python -m unittest discover -s tests
```

The current tests cover point reordering, displacement, structured grid elements, and the principal strain formula on a synthetic case.
