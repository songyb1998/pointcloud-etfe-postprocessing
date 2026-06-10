from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from pointcloud_etfe_postprocessing.config import GridConfig
from pointcloud_etfe_postprocessing.displacement import calculate_displacements
from pointcloud_etfe_postprocessing.mesh import renumber_grid_points, structured_grid_elements
from pointcloud_etfe_postprocessing.strain import calculate_element_strain


class CoreCalculationTests(unittest.TestCase):
    def test_renumber_grid_points_sorts_by_y_chunks_then_x(self) -> None:
        points = pd.DataFrame(
            {
                "point_ID": [10, 11, 12, 13],
                "point_x": [1.0, 0.0, 1.0, 0.0],
                "point_y": [1.0, 0.0, 0.0, 1.0],
                "point_z": [0.0, 0.0, 0.0, 0.0],
            }
        )
        result = renumber_grid_points(points, GridConfig(rows_x=2, rows_y=2))
        self.assertEqual(result["point_ID"].tolist(), [0, 1, 2, 3])
        self.assertEqual(result[["point_x", "point_y"]].to_numpy().tolist(), [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])

    def test_calculate_displacements_uses_resultant_norm(self) -> None:
        reference = pd.DataFrame(
            {
                "point_ID": [0, 1, 2, 3],
                "point_x": [0.0, 1.0, 0.0, 1.0],
                "point_y": [0.0, 0.0, 1.0, 1.0],
                "point_z": [0.0, 0.0, 0.0, 0.0],
            }
        )
        target = reference.copy()
        target["point_x"] += 1.0
        target["point_y"] += 2.0
        target["point_z"] += 2.0
        result = calculate_displacements(reference, target, GridConfig(rows_x=2, rows_y=2))
        self.assertTrue(np.allclose(result["ux"], 1.0))
        self.assertTrue(np.allclose(result["uy"], 2.0))
        self.assertTrue(np.allclose(result["uz"], 2.0))
        self.assertTrue(np.allclose(result["displacement"], 3.0))

    def test_structured_grid_elements_for_two_by_two_grid(self) -> None:
        elements = structured_grid_elements(GridConfig(rows_x=2, rows_y=2))
        self.assertEqual(elements.shape, (2, 3))
        self.assertEqual(elements.tolist(), [[0, 2, 3], [0, 3, 1]])

    def test_uniform_planar_scale_has_equal_log_principal_strains(self) -> None:
        reference = pd.DataFrame(
            {
                "point_ID": [0, 1, 2],
                "point_x": [0.0, 1.0, 0.0],
                "point_y": [0.0, 0.0, 1.0],
                "point_z": [0.0, 0.0, 0.0],
            }
        )
        target = reference.copy()
        target["point_x"] *= 1.1
        target["point_y"] *= 1.1
        elements = np.array([[0, 1, 2]])
        strain = calculate_element_strain(reference, target, elements)
        self.assertTrue(math.isclose(strain.loc[0, "epsilon1"], math.log(1.1), rel_tol=1e-10))
        self.assertTrue(math.isclose(strain.loc[0, "epsilon2"], math.log(1.1), rel_tol=1e-10))


if __name__ == "__main__":
    unittest.main()

