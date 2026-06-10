from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GridConfig
from .mesh import renumber_grid_points


def calculate_displacements(
    reference_points: pd.DataFrame,
    target_points: pd.DataFrame,
    grid: GridConfig = GridConfig(),
    renumber: bool = True,
) -> pd.DataFrame:
    """Calculate x/y/z and resultant displacement between two point clouds."""

    reference = renumber_grid_points(reference_points, grid) if renumber else reference_points.copy()
    target = renumber_grid_points(target_points, grid) if renumber else target_points.copy()

    merged = target.merge(
        reference,
        on="point_ID",
        suffixes=("_target", "_reference"),
        validate="one_to_one",
    ).sort_values("point_ID")

    ux = merged["point_x_target"] - merged["point_x_reference"]
    uy = merged["point_y_target"] - merged["point_y_reference"]
    uz = merged["point_z_target"] - merged["point_z_reference"]

    result = target.sort_values("point_ID").reset_index(drop=True).copy()
    result["ux"] = ux.to_numpy()
    result["uy"] = uy.to_numpy()
    result["uz"] = uz.to_numpy()
    result["displacement"] = np.sqrt(result["ux"] ** 2 + result["uy"] ** 2 + result["uz"] ** 2)
    return result

