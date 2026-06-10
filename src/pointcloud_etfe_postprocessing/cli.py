from __future__ import annotations

import argparse
from pathlib import Path

from .config import GridConfig, StressConfig, TriangulationConfig
from .workflows import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUT_DIR,
    run_batch_displacement_workflow,
    run_displacement_workflow,
    run_strain_workflow,
    run_stress_workflow,
)


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
    return run_displacement_workflow(
        args.reference,
        args.target,
        args.out_dir,
        grid=_grid_from_args(args),
        triangulation=_triangulation_from_args(args),
        plot=args.plot,
    ).paths


def run_strain(args: argparse.Namespace) -> list[Path]:
    return run_strain_workflow(
        args.reference,
        args.target,
        args.out_dir,
        grid=_grid_from_args(args),
        triangulation=_triangulation_from_args(args),
        plot=args.plot,
    ).paths


def run_stress(args: argparse.Namespace) -> list[Path]:
    return run_stress_workflow(
        args.input,
        args.out_dir,
        grid=_grid_from_args(args),
        triangulation=_triangulation_from_args(args, default_scale=1.8),
        stress=StressConfig(
            pressure_mpa=args.pressure_mpa,
            thickness_mm=args.thickness_mm,
            normal_radius=args.normal_radius,
            normal_max_nn=args.normal_max_nn,
            link_angle_exclusion_deg=args.link_angle_exclusion,
        ),
        plot=args.plot,
    ).paths


def run_batch(args: argparse.Namespace) -> list[Path]:
    return run_batch_displacement_workflow(
        args.data_dir,
        args.out_dir,
        reference_path=args.reference,
        grid=_grid_from_args(args),
        triangulation=_triangulation_from_args(args),
        plot=args.plot,
    ).paths


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
