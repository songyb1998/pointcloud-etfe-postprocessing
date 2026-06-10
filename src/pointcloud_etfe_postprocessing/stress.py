from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from .config import GridConfig, StressConfig, TriangulationConfig
from .mesh import renumber_grid_points, triangle_areas, triangulate_elements


def estimate_normals(points: pd.DataFrame, config: StressConfig = StressConfig()) -> pd.DataFrame:
    """Estimate point normals with Open3D."""

    try:
        import open3d as o3d
    except ImportError as exc:
        raise RuntimeError("open3d is required for stress calculations") from exc

    xyz = points.loc[:, ["point_x", "point_y", "point_z"]].to_numpy(dtype=float)
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(xyz)
    cloud.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=config.normal_radius,
            max_nn=config.normal_max_nn,
        )
    )
    o3d.geometry.PointCloud.orient_normals_to_align_with_direction(
        cloud,
        orientation_reference=np.array([0.0, 0.0, 1.0]),
    )
    normals = np.asarray(cloud.normals)
    return pd.DataFrame(
        {
            "point_ID": points["point_ID"].astype(int).to_numpy(),
            "normal_x": normals[:, 0],
            "normal_y": normals[:, 1],
            "normal_z": normals[:, 2],
        }
    )


def link_angle(points: pd.DataFrame, point1_id: int, point2_id: int) -> float:
    p1 = points.loc[point1_id, ["point_x", "point_y"]].to_numpy(dtype=float)
    p2 = points.loc[point2_id, ["point_x", "point_y"]].to_numpy(dtype=float)
    dx, dy = p2 - p1
    return float(np.degrees(np.arctan2(dy, dx)))


def link_length(points: pd.DataFrame, point1_id: int, point2_id: int) -> float:
    p1 = points.loc[point1_id, ["point_x", "point_y", "point_z"]].to_numpy(dtype=float)
    p2 = points.loc[point2_id, ["point_x", "point_y", "point_z"]].to_numpy(dtype=float)
    return float(np.linalg.norm(p1 - p2))


def element_links(points: pd.DataFrame, elements: np.ndarray, config: StressConfig = StressConfig()) -> pd.DataFrame:
    """Convert triangle elements to membrane links and drop diagonal links."""

    edge_set: set[tuple[int, int]] = set()
    for element in np.asarray(elements, dtype=int):
        for a, b in combinations(sorted(element.tolist()), 2):
            edge_set.add((int(a), int(b)))

    rows = []
    for point1_id, point2_id in sorted(edge_set):
        angle = link_angle(points, point1_id, point2_id)
        normalized = angle % 180
        exclusion = config.link_angle_exclusion_deg
        if exclusion < normalized < 90 - exclusion or 90 + exclusion < normalized < 180 - exclusion:
            continue
        p1 = points.loc[point1_id]
        p2 = points.loc[point2_id]
        rows.append(
            {
                "point1_ID": point1_id,
                "point1_x": p1["point_x"],
                "point1_y": p1["point_y"],
                "point1_z": p1["point_z"],
                "point2_ID": point2_id,
                "point2_x": p2["point_x"],
                "point2_y": p2["point_y"],
                "point2_z": p2["point_z"],
                "length": link_length(points, point1_id, point2_id),
                "angle": angle,
            }
        )

    links = pd.DataFrame(rows)
    links.insert(0, "link_ID", np.arange(len(links), dtype=int))
    return links


def subordinate_areas(points: pd.DataFrame, elements: np.ndarray) -> pd.Series:
    areas = triangle_areas(points, elements)
    result = pd.Series(0.0, index=points["point_ID"].astype(int))
    for area, element in zip(areas, elements):
        for point_id in element:
            result.loc[int(point_id)] += area / 3.0
    return result


def pressure_load_vectors(
    points: pd.DataFrame,
    normals: pd.DataFrame,
    elements: np.ndarray,
    config: StressConfig = StressConfig(),
) -> pd.DataFrame:
    areas = subordinate_areas(points, elements)
    loads = normals.copy()
    loads = loads.set_index("point_ID").sort_index()
    for axis in ["normal_x", "normal_y", "normal_z"]:
        loads[axis] = loads[axis] * areas * config.pressure_mpa
    return loads.rename(columns={"normal_x": "Px", "normal_y": "Py", "normal_z": "Pz"}).reset_index()


def connected_nodes(points: pd.DataFrame, links: pd.DataFrame) -> dict[int, np.ndarray]:
    result: dict[int, list[int]] = {int(point_id): [] for point_id in points["point_ID"]}
    for _, row in links.iterrows():
        p1 = int(row["point1_ID"])
        p2 = int(row["point2_ID"])
        result[p1].append(p2)
        result[p2].append(p1)
    return {point_id: np.asarray(sorted(set(neighbors)), dtype=int) for point_id, neighbors in result.items()}


def solve_link_forces(
    points: pd.DataFrame,
    links: pd.DataFrame,
    loads: pd.DataFrame,
) -> pd.DataFrame:
    """Solve link force densities at four-connected internal nodes."""

    coords = points.set_index("point_ID").loc[:, ["point_x", "point_y", "point_z"]]
    load_vectors = loads.set_index("point_ID").loc[:, ["Px", "Py", "Pz"]]
    neighbors_by_point = connected_nodes(points, links)
    link_lookup = {
        frozenset((int(row["point1_ID"]), int(row["point2_ID"]))): int(row["link_ID"])
        for _, row in links.iterrows()
    }
    force_density: dict[int, list[float]] = {int(link_id): [] for link_id in links["link_ID"]}

    eye = np.eye(3)
    c_matrix = np.concatenate((eye, -eye), axis=1)
    for point_id, neighbors in neighbors_by_point.items():
        if len(neighbors) != 4:
            continue
        center = coords.loc[point_id].to_numpy(dtype=float)
        neighbor_coords = coords.loc[neighbors].to_numpy(dtype=float)
        x_matrix = np.concatenate((np.tile(center, (len(neighbors), 1)).T, neighbor_coords.T), axis=0)
        q_coeff = x_matrix.T @ c_matrix.T @ c_matrix @ x_matrix
        p_coeff = x_matrix.T @ c_matrix.T
        load = load_vectors.loc[point_id].to_numpy(dtype=float).reshape(-1, 1)
        q_values = np.linalg.pinv(q_coeff) @ p_coeff @ load
        for neighbor_id, q_value in zip(neighbors, q_values.reshape(-1)):
            link_id = link_lookup.get(frozenset((point_id, int(neighbor_id))))
            if link_id is not None:
                force_density[link_id].append(float(q_value))

    updated = links.copy()
    updated["force_density"] = [force_density[int(link_id)] for link_id in updated["link_ID"]]
    updated["link_force"] = [
        max(0.0, float(np.mean(values)) * float(length)) if values else 0.0
        for values, length in zip(updated["force_density"], updated["length"])
    ]
    return updated


def calculate_link_stresses(links: pd.DataFrame, config: StressConfig = StressConfig()) -> tuple[pd.DataFrame, pd.DataFrame]:
    links = links.copy()
    normalized = links["angle"] % 180
    links_x = links[(normalized < 45) | (normalized > 135)].reset_index(drop=True).copy()
    links_y = links[(normalized >= 45) & (normalized <= 135)].reset_index(drop=True).copy()

    def equivalent_width(row: pd.Series, perpendicular: pd.DataFrame) -> float:
        p1 = row["point1_ID"]
        p2 = row["point2_ID"]
        mask = (
            (perpendicular["point1_ID"] == p1)
            | (perpendicular["point2_ID"] == p1)
            | (perpendicular["point1_ID"] == p2)
            | (perpendicular["point2_ID"] == p2)
        )
        lengths = perpendicular.loc[mask, "length"]
        return float(lengths.mean()) if not lengths.empty else np.nan

    links_x["equivalent_width"] = links_x.apply(lambda row: equivalent_width(row, links_y), axis=1)
    links_y["equivalent_width"] = links_y.apply(lambda row: equivalent_width(row, links_x), axis=1)
    links_x["stress"] = links_x["link_force"] / (links_x["equivalent_width"] * config.thickness_mm)
    links_y["stress"] = links_y["link_force"] / (links_y["equivalent_width"] * config.thickness_mm)
    return links_x, links_y


def calculate_point_stresses(points: pd.DataFrame, links_x: pd.DataFrame, links_y: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for point_id in points["point_ID"].astype(int):
        sx_mask = (links_x["point1_ID"] == point_id) | (links_x["point2_ID"] == point_id)
        sy_mask = (links_y["point1_ID"] == point_id) | (links_y["point2_ID"] == point_id)
        sxx = float(links_x.loc[sx_mask, "stress"].mean()) if sx_mask.any() else np.nan
        syy = float(links_y.loc[sy_mask, "stress"].mean()) if sy_mask.any() else np.nan
        principal = np.nanmax([sxx, syy])
        smax = np.nanmax([sxx, syy])
        smin = np.nanmin([sxx, syy])
        mises = np.sqrt(0.5 * (smax**2 + smin**2 + (smax - smin) ** 2))
        rows.append((point_id, sxx, syy, principal, mises))
    stress = pd.DataFrame(rows, columns=["point_ID", "Sxx", "Syy", "principal_stress", "mises_stress"])
    return points.merge(stress, on="point_ID", validate="one_to_one")


def calculate_stress_distribution(
    points: pd.DataFrame,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(boundary_scale=1.8),
    stress: StressConfig = StressConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Calculate point stress distribution and derived link stresses."""

    renumbered = renumber_grid_points(points, grid)
    elements = triangulate_elements(renumbered, grid, triangulation)
    normals = estimate_normals(renumbered, stress)
    links = element_links(renumbered, elements, stress)
    loads = pressure_load_vectors(renumbered, normals, elements, stress)
    solved_links = solve_link_forces(renumbered, links, loads)
    links_x, links_y = calculate_link_stresses(solved_links, stress)
    point_stress = calculate_point_stresses(renumbered, links_x, links_y)
    return point_stress, links_x, links_y, elements

