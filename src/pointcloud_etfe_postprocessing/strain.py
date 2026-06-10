from __future__ import annotations

import numpy as np
import pandas as pd

from .config import GridConfig, TriangulationConfig
from .mesh import renumber_grid_points, triangle_areas, triangulate_elements


def _element_edge_lengths(points: pd.DataFrame, elements: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xyz = points.loc[:, ["point_x", "point_y", "point_z"]].to_numpy(dtype=float)
    p0 = xyz[elements[:, 0]]
    p1 = xyz[elements[:, 1]]
    p2 = xyz[elements[:, 2]]
    line0 = np.linalg.norm(p0 - p1, axis=1)
    line1 = np.linalg.norm(p1 - p2, axis=1)
    line2 = np.linalg.norm(p0 - p2, axis=1)
    return line0, line1, line2


def calculate_element_strain(
    reference_points: pd.DataFrame,
    target_points: pd.DataFrame,
    elements: np.ndarray,
) -> pd.DataFrame:
    """Calculate element-level principal logarithmic strains from edge-length changes."""

    a, b, c = _element_edge_lengths(reference_points, elements)
    A, B, C = _element_edge_lengths(target_points, elements)

    with np.errstate(divide="raise", invalid="raise"):
        e11 = (A**2 - a**2) / (2 * a**2)
        e22 = (
            (A**2 + a**2) * (a**2 + c**2 - b**2) ** 2
            + 4 * a**4 * C**2
            - 2 * a**2 * (A**2 + C**2 - B**2) * (a**2 + c**2 - b**2)
            - 4 * a**4 * c**2
        ) / (8 * a**4 * c**2 - 2 * a**2 * (a**2 + c**2 - b**2) ** 2)
        e12 = (
            A**2 * (a**2 + c**2 - b**2) ** 2
            - a**2 * (a**2 + c**2 - b**2) * (A**2 + C**2 - B**2)
        ) / (4 * a**4 * c**2)

        tau = np.sqrt(((e11 - e22) / 2) ** 2 + e12**2)
        mean = (e11 + e22) / 2
        epsilon1 = np.log(np.sqrt(1 + 2 * mean + tau))
        epsilon2 = np.log(np.sqrt(1 + 2 * mean - tau))

    return pd.DataFrame(
        {
            "element_ID": np.arange(len(elements), dtype=int),
            "node0": elements[:, 0],
            "node1": elements[:, 1],
            "node2": elements[:, 2],
            "E11": e11,
            "E22": e22,
            "E12": e12,
            "epsilon1": epsilon1,
            "epsilon2": epsilon2,
            "tau": tau,
        }
    )


def calculate_point_strain(
    target_points: pd.DataFrame,
    elements: np.ndarray,
    element_strain: pd.DataFrame,
) -> pd.DataFrame:
    """Area-weight element strains onto point nodes."""

    areas = triangle_areas(target_points, elements)
    epsilon1 = element_strain["epsilon1"].to_numpy(dtype=float)
    epsilon2 = element_strain["epsilon2"].to_numpy(dtype=float)

    rows = []
    for point_id in target_points["point_ID"].astype(int):
        mask = np.any(elements == point_id, axis=1)
        if not mask.any():
            rows.append((point_id, np.nan, np.nan))
            continue
        weights = areas[mask]
        rows.append(
            (
                point_id,
                np.average(epsilon1[mask], weights=weights),
                np.average(epsilon2[mask], weights=weights),
            )
        )

    frame = pd.DataFrame(rows, columns=["point_ID", "epsilon1", "epsilon2"])
    return target_points.merge(frame, on="point_ID", validate="one_to_one")


def calculate_strain_distribution(
    reference_points: pd.DataFrame,
    target_points: pd.DataFrame,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Calculate element and point principal strain distributions."""

    reference = renumber_grid_points(reference_points, grid)
    target = renumber_grid_points(target_points, grid)
    elements = triangulate_elements(reference, grid, triangulation)
    element_strain = calculate_element_strain(reference, target, elements)
    point_strain = calculate_point_strain(target, elements, element_strain)
    return element_strain, point_strain, elements

