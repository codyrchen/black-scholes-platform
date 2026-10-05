"""Shared plotting style and output helpers for the research scripts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# LEARN_OUT_DIR lets you write somewhere else (e.g. to try a script without touching the site).
OUT_DIR = Path(os.environ.get("LEARN_OUT_DIR", ROOT / "frontend" / "public" / "research"))
RESULTS = OUT_DIR / "results.json"

# Categorical slots in fixed order (validated palette), plus ink and chrome.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

plt.rcParams.update(
    {
        "figure.figsize": (7.5, 4.2),
        "figure.dpi": 150,
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "legend.frameon": False,
        "legend.labelcolor": INK_2,
        "lines.linewidth": 2,
        "font.family": "sans-serif",
    }
)


def save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_DIR / name, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_DIR / name}")


def update_results(section: str, values: dict) -> None:
    data = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    data[section] = values
    RESULTS.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"updated {RESULTS} [{section}]")


def loglog_slope(x, y) -> float:
    import numpy as np

    return float(np.polyfit(np.log(x), np.log(y), 1)[0])
