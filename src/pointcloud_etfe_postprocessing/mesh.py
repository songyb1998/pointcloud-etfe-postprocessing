from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from .config import GridConfig, TriangulationConfig


def renumber_grid_points(points: pd.DataFrame, grid: GridConfig = GridConfig()) -> pd.DataFrame:
    """Sort points into the original row-major grid order and assign 0-based IDs."""

    expected = grid.rows_x * grid.rows_y
    if len(points) != expected:
        raise ValueError(f"Expected {expected} points for a {grid.rows_x}x{grid.rows_y} grid, got {len(points)}")

    sorted_by_y = points.sort_values(by="point_y").reset_index(drop=True)
    rows = []
    for row_index in range(grid.rows_x):
        start = grid.rows_y * row_index
        stop = grid.rows_y * (row_index + 1)
        rows.append(sorted_by_y.iloc[start:stop].sort_values(by="point_x"))

    renumbered = pd.concat(rows, ignore_index=True).reset_index(drop=True)
    renumbered = renumbered.copy()
    renumbered["point_ID"] = np.arange(len(renumbered), dtype=int)
    return renumbered


def structured_grid_elements(grid: GridConfig = GridConfig()) -> np.ndarray:
    """Create two triangular elements for each cell in the structured grid."""

    elements: list[tuple[int, int, int]] = []
    for row in range(grid.rows_x - 1):
        for col in range(grid.rows_y - 1):
            p00 = row * grid.rows_y + col
            p01 = row * grid.rows_y + col + 1
            p10 = (row + 1) * grid.rows_y + col
            p11 = (row + 1) * grid.rows_y + col + 1
            elements.append((p00, p10, p11))
            elements.append((p00, p11, p01))
    return np.asarray(elements, dtype=int)


def matplotlib_triangulation_elements(points: pd.DataFrame) -> np.ndarray:
    """Triangulate by x/y projection with matplotlib's Delaunay wrapper."""

    try:
        import matplotlib.tri as mtri
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for triangulation method='matplotlib'") from exc

    xy = points.loc[:, ["point_x", "point_y"]].to_numpy(dtype=float)
    return np.asarray(mtri.Triangulation(xy[:, 0], xy[:, 1]).triangles, dtype=int)


def filter_boundary_triangles(
    points: pd.DataFrame,
    elements: np.ndarray,
    config: TriangulationConfig = TriangulationConfig(),
) -> np.ndarray:
    """Remove triangles with x/y axis deltas larger than the configured threshold."""

    coords = points.loc[:, ["point_x", "point_y"]].to_numpy(dtype=float)
    max_delta = config.max_axis_delta
    keep = []
    for element in np.asarray(elements, dtype=int):
        element_coords = coords[element]
        too_wide = False
        for a, b in combinations(range(3), 2):
            dx, dy = np.abs(element_coords[a] - element_coords[b])
            if dx > max_delta or dy > max_delta:
                too_wide = True
                break
        keep.append(not too_wide)
    return np.asarray(elements, dtype=int)[np.asarray(keep, dtype=bool)]


def triangulate_elements(
    points: pd.DataFrame,
    grid: GridConfig = GridConfig(),
    config: TriangulationConfig = TriangulationConfig(),
) -> np.ndarray:
    """Build and filter triangular elements for the point cloud."""

    if config.method not in {"auto", "matplotlib", "structured"}:
        raise ValueError("Triangulation method must be 'auto', 'matplotlib', or 'structured'")

    if config.method == "structured":
        elements = structured_grid_elements(grid)
    elif config.method == "matplotlib":
        elements = matplotlib_triangulation_elements(points)
    else:
        try:
            elements = matplotlib_triangulation_elements(points)
        except RuntimeError:
            elements = structured_grid_elements(grid)

    return filter_boundary_triangles(points, elements, config)


def triangle_areas(points: pd.DataFrame, elements: np.ndarray) -> np.ndarray:
    xyz = points.loc[:, ["point_x", "point_y", "point_z"]].to_numpy(dtype=float)
    p0 = xyz[elements[:, 0]]
    p1 = xyz[elements[:, 1]]
    p2 = xyz[elements[:, 2]]
    return np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1) / 2.0

