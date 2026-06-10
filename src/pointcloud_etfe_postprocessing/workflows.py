from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import GridConfig, StressConfig, TriangulationConfig
from .displacement import calculate_displacements
from .io import ensure_output_dir, list_workbooks, load_points, workbook_label, write_csv
from .mesh import renumber_grid_points, triangulate_elements
from .plotting import plot_scalar_field
from .strain import calculate_strain_distribution
from .stress import calculate_stress_distribution

DEFAULT_DATA_DIR = Path("data/raw")
DEFAULT_OUT_DIR = Path("outputs")


@dataclass(frozen=True)
class WorkflowOutputs:
    """Files written by a processing workflow."""

    paths: list[Path]


def run_displacement_workflow(
    reference_path: str | Path,
    target_path: str | Path,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(),
    plot: bool = False,
) -> WorkflowOutputs:
    """Load two workbooks, calculate nodal displacement, and write output files."""

    output_dir = ensure_output_dir(out_dir)
    reference = load_points(reference_path)
    target = load_points(target_path)
    result = calculate_displacements(reference, target, grid)

    label = f"{workbook_label(target_path)}_displacement"
    paths = [write_csv(result, output_dir / f"{label}.csv")]

    if plot:
        target_points = renumber_grid_points(target, grid)
        elements = triangulate_elements(target_points, grid, triangulation)
        paths.append(
            plot_scalar_field(
                result,
                elements,
                "displacement",
                output_dir / f"{label}.png",
                label="Displacement / mm",
            )
        )

    return WorkflowOutputs(paths)


def run_strain_workflow(
    reference_path: str | Path,
    target_path: str | Path,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(),
    plot: bool = False,
) -> WorkflowOutputs:
    """Load two workbooks, calculate strain distributions, and write output files."""

    output_dir = ensure_output_dir(out_dir)
    reference = load_points(reference_path)
    target = load_points(target_path)
    element_strain, point_strain, elements = calculate_strain_distribution(
        reference,
        target,
        grid,
        triangulation,
    )

    label = workbook_label(target_path)
    paths = [
        write_csv(element_strain, output_dir / f"{label}_element_strain.csv"),
        write_csv(point_strain, output_dir / f"{label}_point_strain.csv"),
    ]

    if plot:
        paths.append(
            plot_scalar_field(
                point_strain,
                elements,
                "epsilon1",
                output_dir / f"{label}_epsilon1.png",
                label="Principal Strain",
            )
        )

    return WorkflowOutputs(paths)


def run_stress_workflow(
    input_path: str | Path,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(boundary_scale=1.8),
    stress: StressConfig = StressConfig(),
    plot: bool = False,
) -> WorkflowOutputs:
    """Load one workbook, calculate stress distributions, and write output files."""

    output_dir = ensure_output_dir(out_dir)
    points = load_points(input_path)
    point_stress, links_x, links_y, elements = calculate_stress_distribution(
        points,
        grid,
        triangulation,
        stress,
    )

    label = workbook_label(input_path)
    paths = [
        write_csv(point_stress, output_dir / f"{label}_point_stress.csv"),
        write_csv(links_x, output_dir / f"{label}_links_x_stress.csv"),
        write_csv(links_y, output_dir / f"{label}_links_y_stress.csv"),
    ]

    if plot:
        paths.append(
            plot_scalar_field(
                point_stress,
                elements,
                "mises_stress",
                output_dir / f"{label}_mises_stress.png",
                label="Mises Stress / MPa",
            )
        )

    return WorkflowOutputs(paths)


def run_batch_displacement_workflow(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    reference_path: str | Path | None = None,
    grid: GridConfig = GridConfig(),
    triangulation: TriangulationConfig = TriangulationConfig(),
    plot: bool = False,
) -> WorkflowOutputs:
    """Run displacement calculations for all non-failure workbooks in a directory."""

    source_dir = Path(data_dir)
    reference = Path(reference_path) if reference_path else source_dir / "zxt_300Pa.xlsx"
    paths: list[Path] = []

    for workbook in list_workbooks(source_dir):
        if workbook.resolve() == reference.resolve():
            continue
        if "failure" in workbook.stem.lower():
            continue
        result = run_displacement_workflow(
            reference,
            workbook,
            out_dir,
            grid=grid,
            triangulation=triangulation,
            plot=plot,
        )
        paths.extend(result.paths)

    return WorkflowOutputs(paths)
