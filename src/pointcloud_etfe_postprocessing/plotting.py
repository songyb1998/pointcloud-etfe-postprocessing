from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def plot_scalar_field(
    points: pd.DataFrame,
    elements: np.ndarray,
    values: str,
    output_path: str | Path,
    *,
    label: str | None = None,
    hide_axes: bool = False,
) -> Path:
    """Plot a node scalar field over triangular elements."""

    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    xy = points.loc[:, ["point_x", "point_y"]].to_numpy(dtype=float)
    triangulation = mtri.Triangulation(xy[:, 0], xy[:, 1], elements)

    fig = plt.figure(dpi=300)
    plt.triplot(triangulation)
    plt.axis("equal")
    plt.gca().set_aspect("equal", adjustable="box")
    cp = plt.tripcolor(triangulation, points[values].to_numpy(dtype=float), cmap="rainbow", shading="gouraud")
    if label:
        plt.colorbar(cp, label=label)
    if hide_axes:
        plt.axis("off")
    else:
        plt.xlabel("X / mm")
        plt.ylabel("Y / mm")
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output

