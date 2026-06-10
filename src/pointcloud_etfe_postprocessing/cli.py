from __future__ import annotations

import argparse
from pathlib import Path

from .config import GridConfig, StressConfig, TriangulationConfig
from .displacement import calculate_displacements
from .io import ensure_output_dir, list_workbooks, load_points, workbook_label, write_csv
from .plotting import plot_scalar_field
from .strain import calculate_strain_distribution
from .stress import calculate_stress_distribution

DEFAULT_DATA_DIR = Path("data/raw")
DEFAULT_OUT_DIR = Path("outputs")


def _grid_from_args(args: argparse.Namespace) -> GridConfig:
    return GridConfig(rows_x=args.rows_x, rows_y=args.rows_y)


def _triangulation_from_args(args: argparse.Namespace, default_scale: float = 1.3) -> TriangulationConfig:
    return TriangulationConfig(
        target_spacing=args.target_spacing,
        boundary_scale=args.boundary_scale if args.boundary_scale is not None else default_scale,
        method=args.triangulation_method,
    )


def _add_common_grid_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rows-x", type=int, default=16, help="Number of point rows in the first grid direction.")
    parser.add_argument("--rows-y", type=int, default=16, help="Number of point rows in the second grid direction.")
    parser.add_argument("--target-spacing", type=float, default=100.0, help="Target spacing used for boundary filtering.")
    parser.add_argument("--boundary-scale", type=float, default=None, help="Boundary filtering scale.")
    parser.add_argument(
        "--triangulation-method",
        choices=["auto", "matplotlib", "structured"],
        default="auto",
        help="Triangulation backend.",
    )


def run_displacement(args: argparse.Namespace) -> list[Path]:
    out_dir = ensure_output_dir(args.out_dir)
    reference = load_points(args.reference)
    target = load_points(args.target)
    result = calculate_displacements(reference, target, _grid_from_args(args))
    label = f"{workbook_label(args.target)}_displacement"
    paths = [write_csv(result, out_dir / f"{label}.csv")]
    if args.plot:
        elements = _triangulation_from_args(args).method
        # Reuse strain triangulation path only when plotting is requested.
        from .mesh import renumber_grid_points, triangulate_elements

        grid = _grid_from_args(args)
        target_points = renumber_grid_points(target, grid)
        tri = triangulate_elements(target_points, grid, _triangulation_from_args(args))
        paths.append(plot_scalar_field(result, tri, "displacement", out_dir / f"{label}.png", label="Displacement / mm"))
        _ = elements
    return paths


def run_strain(args: argparse.Namespace) -> list[Path]:
    out_dir = ensure_output_dir(args.out_dir)
    reference = load_points(args.reference)
    target = load_points(args.target)
    element_strain, point_strain, elements = calculate_strain_distribution(
        reference,
        target,
        _grid_from_args(args),
        _triangulation_from_args(args),
    )
    label = workbook_label(args.target)
    paths = [
        write_csv(element_strain, out_dir / f"{label}_element_strain.csv"),
        write_csv(point_strain, out_dir / f"{label}_point_strain.csv"),
    ]
    if args.plot:
        paths.append(plot_scalar_field(point_strain, elements, "epsilon1", out_dir / f"{label}_epsilon1.png", label="Principal Strain"))
    return paths


def run_stress(args: argparse.Namespace) -> list[Path]:
    out_dir = ensure_output_dir(args.out_dir)
    points = load_points(args.input)
    point_stress, links_x, links_y, elements = calculate_stress_distribution(
        points,
        _grid_from_args(args),
        _triangulation_from_args(args, default_scale=1.8),
        StressConfig(
            pressure_mpa=args.pressure_mpa,
            thickness_mm=args.thickness_mm,
            normal_radius=args.normal_radius,
            normal_max_nn=args.normal_max_nn,
            link_angle_exclusion_deg=args.link_angle_exclusion,
        ),
    )
    label = workbook_label(args.input)
    paths = [
        write_csv(point_stress, out_dir / f"{label}_point_stress.csv"),
        write_csv(links_x, out_dir / f"{label}_links_x_stress.csv"),
        write_csv(links_y, out_dir / f"{label}_links_y_stress.csv"),
    ]
    if args.plot:
        paths.append(
            plot_scalar_field(
                point_stress,
                elements,
                "mises_stress",
                out_dir / f"{label}_mises_stress.png",
                label="Mises Stress / MPa",
            )
        )
    return paths


def run_batch(args: argparse.Namespace) -> list[Path]:
    data_dir = Path(args.data_dir)
    reference_path = Path(args.reference) if args.reference else data_dir / "zxt_300Pa.xlsx"
    outputs: list[Path] = []
    for workbook in list_workbooks(data_dir):
        if workbook.resolve() == reference_path.resolve():
            continue
        if "failure" in workbook.stem.lower():
            continue
        target_args = argparse.Namespace(**vars(args))
        target_args.reference = reference_path
        target_args.target = workbook
        outputs.extend(run_displacement(target_args))
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pointcloud-etfe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    displacement = subparsers.add_parser("displacement", help="Calculate displacement between two point clouds.")
    displacement.add_argument("--reference", required=True, type=Path)
    displacement.add_argument("--target", required=True, type=Path)
    displacement.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    displacement.add_argument("--plot", action="store_true")
    _add_common_grid_options(displacement)
    displacement.set_defaults(func=run_displacement)

    strain = subparsers.add_parser("strain", help="Calculate element and point principal strain.")
    strain.add_argument("--reference", required=True, type=Path)
    strain.add_argument("--target", required=True, type=Path)
    strain.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    strain.add_argument("--plot", action="store_true")
    _add_common_grid_options(strain)
    strain.set_defaults(func=run_strain)

    stress = subparsers.add_parser("stress", help="Calculate stress distribution for one point cloud.")
    stress.add_argument("--input", required=True, type=Path)
    stress.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    stress.add_argument("--plot", action="store_true")
    stress.add_argument("--pressure-mpa", type=float, default=0.014)
    stress.add_argument("--thickness-mm", type=float, default=0.25)
    stress.add_argument("--normal-radius", type=float, default=200.0)
    stress.add_argument("--normal-max-nn", type=int, default=30)
    stress.add_argument("--link-angle-exclusion", type=float, default=20.0)
    _add_common_grid_options(stress)
    stress.set_defaults(func=run_stress)

    batch = subparsers.add_parser("batch", help="Batch displacement calculation for all zxt_*.xlsx files.")
    batch.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    batch.add_argument("--reference", type=Path, default=None)
    batch.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    batch.add_argument("--plot", action="store_true")
    _add_common_grid_options(batch)
    batch.set_defaults(func=run_batch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = args.func(args)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
