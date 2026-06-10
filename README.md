# pointcloud-etfe-postprocessing

Python tools for post-processing ETFE cushion photogrammetry point clouds to calculate displacement, strain, and stress distributions.

The project keeps reusable code in `src/`, tests in `tests/`, original Excel workbooks in `data/raw/`, lightweight example notebooks in `notebooks/`, script examples in `examples/`, and generated results in `outputs/`.

## What It Does

- Loads photogrammetry Excel workbooks containing `points` and `links` sheets.
- Reorders sparse point clouds into the original structured grid.
- Builds triangular elements for surface interpolation.
- Calculates node displacement between a reference and deformed point cloud.
- Calculates element-level and point-level principal logarithmic strains.
- Calculates membrane link and point stress distributions from pressure loading.
- Writes reusable CSV outputs and optional figures.

## Project Layout

```text
.
|-- data/
|   |-- README.md
|   `-- raw/
|       `-- zxt_*.xlsx
|-- examples/
|   |-- README.md
|   `-- run_preview.py
|-- notebooks/
|   |-- README.md
|   |-- Displacement_Calculation.ipynb
|   |-- Strain_Distribution_Calculation.ipynb
|   `-- Stress_Distribution_Calculation.ipynb
|-- outputs/
|   `-- generated CSV files and figures
|-- src/
|   `-- pointcloud_etfe_postprocessing/
|       |-- cli.py
|       |-- config.py
|       |-- displacement.py
|       |-- io.py
|       |-- mesh.py
|       |-- plotting.py
|       |-- strain.py
|       |-- stress.py
|       `-- workflows.py
|-- tests/
|   `-- test_core.py
|-- pyproject.toml
`-- requirements.txt
```

## Directory Roles

- `data/raw/`: source Excel workbooks. Keep original measurement data here.
- `examples/`: runnable Python scripts that call the package API.
- `notebooks/`: lightweight tutorial notebooks that call the package API. Algorithm implementations should not live here.
- `outputs/`: generated CSV files and plots. This directory is ignored by Git.
- `src/pointcloud_etfe_postprocessing/`: reusable package, command-line entry point, and high-level workflows.
- `tests/`: regression tests for core calculations and workflow behavior.

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
pointcloud-etfe displacement `
  --reference data/raw/zxt_300Pa.xlsx `
  --target data/raw/zxt_13000Pa.xlsx `
  --out-dir outputs/displacement `
  --plot `
  --triangulation-method structured `
  --boundary-scale 1.6
```

Principal strain:

```powershell
pointcloud-etfe strain `
  --reference data/raw/zxt_300Pa.xlsx `
  --target data/raw/zxt_9000Pa.xlsx `
  --out-dir outputs/strain `
  --plot `
  --triangulation-method structured `
  --boundary-scale 1.6
```

Stress distribution:

```powershell
pointcloud-etfe stress `
  --input data/raw/zxt_14000Pa_failure.xlsx `
  --out-dir outputs/stress `
  --plot `
  --triangulation-method structured `
  --boundary-scale 1.8
```

Batch displacement for all non-failure `zxt_*.xlsx` files in `data/raw/`:

```powershell
pointcloud-etfe batch --out-dir outputs/batch_displacement
```

## Python API Usage

The `workflows.py` module is the preferred API for scripts and notebooks:

```python
from pathlib import Path

from pointcloud_etfe_postprocessing.config import TriangulationConfig
from pointcloud_etfe_postprocessing.workflows import run_displacement_workflow

result = run_displacement_workflow(
    Path("data/raw/zxt_300Pa.xlsx"),
    Path("data/raw/zxt_13000Pa.xlsx"),
    Path("outputs/displacement"),
    triangulation=TriangulationConfig(method="structured", boundary_scale=1.6),
    plot=True,
)

print(result.paths)
```

For a complete script example:

```powershell
py -3.12 examples/run_preview.py
```

## Important Parameters

The original notebooks used fixed values. They are now command-line options and Python configuration objects:

- `--rows-x` and `--rows-y`: grid dimensions, default `16 x 16`.
- `--target-spacing`: nominal target spacing, default `100`.
- `--boundary-scale`: boundary triangle filter scale, default `1.3` for displacement/strain and `1.8` for stress.
- `--triangulation-method`: `auto`, `matplotlib`, or `structured`. Use `structured` for the regular ETFE `16 x 16` grid.
- `--pressure-mpa`: membrane pressure for stress, default `0.014`.
- `--thickness-mm`: membrane thickness for stress, default `0.25`.

## Input Workbook Format

Each Excel workbook is expected to include a `points` sheet and, for stress workflows, a `links` sheet.

Required `points` columns:

- `point_ID`
- `point_x`
- `point_y`
- `point_z`

Required `links` columns:

- `link_ID`
- `point1_ID`, `point1_x`, `point1_y`, `point1_z`
- `point2_ID`, `point2_x`, `point2_y`, `point2_z`
- `length`
- `angle`

## Tests

Run the test suite:

```powershell
$env:PYTHONPATH='src'
py -3.12 -m unittest discover -s tests
```

The current tests cover point reordering, displacement, structured grid elements, the principal strain formula, and batch workflow filtering.
