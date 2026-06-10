from __future__ import annotations

from pathlib import Path

from pointcloud_etfe_postprocessing.config import TriangulationConfig
from pointcloud_etfe_postprocessing.workflows import (
    run_displacement_workflow,
    run_strain_workflow,
    run_stress_workflow,
)

DATA_DIR = Path("data/raw")
OUT_DIR = Path("outputs/examples/preview")


def main() -> int:
    workflows = [
        run_displacement_workflow(
            DATA_DIR / "zxt_300Pa.xlsx",
            DATA_DIR / "zxt_13000Pa.xlsx",
            OUT_DIR / "displacement",
            triangulation=TriangulationConfig(method="structured", boundary_scale=1.6),
            plot=True,
        ),
        run_strain_workflow(
            DATA_DIR / "zxt_300Pa.xlsx",
            DATA_DIR / "zxt_9000Pa.xlsx",
            OUT_DIR / "strain",
            triangulation=TriangulationConfig(method="structured", boundary_scale=1.6),
            plot=True,
        ),
        run_stress_workflow(
            DATA_DIR / "zxt_14000Pa_failure.xlsx",
            OUT_DIR / "stress",
            triangulation=TriangulationConfig(method="structured", boundary_scale=1.8),
            plot=True,
        ),
    ]

    for workflow in workflows:
        for path in workflow.paths:
            print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
