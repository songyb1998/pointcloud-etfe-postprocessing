from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

POINT_COLUMNS = ["point_ID", "point_x", "point_y", "point_z"]
LINK_COLUMNS = [
    "link_ID",
    "point1_ID",
    "point1_x",
    "point1_y",
    "point1_z",
    "point2_ID",
    "point2_x",
    "point2_y",
    "point2_z",
    "length",
    "angle",
]


def _validate_columns(frame: pd.DataFrame, required: list[str], source: Path) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{source} is missing required columns: {joined}")
    return frame.loc[:, required].copy()


def load_points(path: str | Path, sheet_name: str = "points") -> pd.DataFrame:
    """Load and validate a sparse point cloud from an Excel workbook."""

    source = Path(path)
    frame = pd.read_excel(source, sheet_name=sheet_name)
    frame = _validate_columns(frame, POINT_COLUMNS, source)
    frame["point_ID"] = frame["point_ID"].astype(int)
    for column in POINT_COLUMNS[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def load_links(path: str | Path, sheet_name: str = "links") -> pd.DataFrame:
    """Load and validate membrane links from an Excel workbook."""

    source = Path(path)
    frame = pd.read_excel(source, sheet_name=sheet_name)
    frame = _validate_columns(frame, LINK_COLUMNS, source)
    for column in ["link_ID", "point1_ID", "point2_ID"]:
        frame[column] = frame[column].astype(int)
    for column in [column for column in LINK_COLUMNS if column not in {"link_ID", "point1_ID", "point2_ID"}]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def list_workbooks(data_dir: str | Path) -> list[Path]:
    """Return sorted `zxt_*.xlsx` data files."""

    return sorted(Path(data_dir).glob("zxt_*.xlsx"))


def workbook_label(path: str | Path) -> str:
    """Convert a workbook filename into a stable output label."""

    stem = Path(path).stem
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("_")


def ensure_output_dir(path: str | Path) -> Path:
    out_dir = Path(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    return destination

