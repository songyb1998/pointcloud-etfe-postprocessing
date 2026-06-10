from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridConfig:
    """Structured sparse point-cloud grid settings."""

    rows_x: int = 16
    rows_y: int = 16


@dataclass(frozen=True)
class TriangulationConfig:
    """Triangulation and boundary filtering settings."""

    target_spacing: float = 100.0
    boundary_scale: float = 1.3
    method: str = "auto"

    @property
    def max_axis_delta(self) -> float:
        return self.target_spacing * self.boundary_scale


@dataclass(frozen=True)
class StressConfig:
    """Membrane stress calculation settings."""

    pressure_mpa: float = 0.014
    thickness_mm: float = 0.25
    normal_radius: float = 200.0
    normal_max_nn: int = 30
    link_angle_exclusion_deg: float = 20.0

