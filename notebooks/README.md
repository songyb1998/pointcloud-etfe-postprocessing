# Notebooks

These notebooks are lightweight examples around the package API. They should not contain duplicated algorithm implementations.

Run them from either the repository root or this `notebooks/` directory. Each notebook adds `../src` or `src` to `sys.path` when needed, reads workbooks from `data/raw/`, and writes generated files to `outputs/notebooks/`.

## Files

- `Displacement_Calculation.ipynb`: runs the displacement workflow and previews nodal displacement.
- `Strain_Distribution_Calculation.ipynb`: runs the strain workflow and previews point and element strain.
- `Stress_Distribution_Calculation.ipynb`: runs the stress workflow and previews point/link stress.

For repeatable production runs, prefer the `pointcloud-etfe` CLI or the workflow functions in `src/pointcloud_etfe_postprocessing/workflows.py`.
