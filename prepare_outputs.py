"""Prepare presentation tables and charts from saved results, without rerunning strategies."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "research/results/all"
METHODS = ["Equal weight", "Sample minimum variance", "Shrinkage minimum variance"]
NAMES = ["Equal weight", "Sample min. variance", "Shrinkage min. variance"]
TICKERS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def main():
    summary = pd.read_csv(OUTPUT / "summary.csv")
    paths = pd.read_csv(OUTPUT / "daily_paths.csv", parse_dates=["date"])
    baseline = paths[(paths.window == 252) & (paths.cost_bps == 5)]
    holdout = baseline[baseline.date >= "2020-01-01"]
    selected = summary[(summary.period == "Holdout") & (summary.window == 252) & (summary.cost_bps == 5)]
    selected.to_csv(OUTPUT / "headline_holdout.csv", index=False)
    mean_weights = holdout.groupby("method")[TICKERS].mean().reindex(METHODS)
    mean_weights.to_csv(OUTPUT / "average_holdout_weights.csv")
    annual = holdout.groupby([holdout.date.dt.year.rename("year"), "method"])["net_return"].agg(
        annualised_volatility=lambda x: x.std(ddof=1) * np.sqrt(252),
        total_return=lambda x: (1 + x).prod() - 1,
    )
    annual.to_csv(OUTPUT / "annual_holdout_results.csv")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colors = ["#2563a6", "#dd7933", "#259279"]
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True, gridspec_kw={"height_ratios": [1.5, 1]})
    for method, name, color in zip(METHODS, NAMES, colors):
        full = baseline[baseline.method == method].set_index("date")
        start_value = full.loc[:"2019-12-31", "nav"].iloc[-1]
        value = full.loc["2020-01-01":, "nav"] / start_value
        # The segment opens at the previous close, before its first daily return.
        value = pd.concat([pd.Series([1.0], index=[pd.Timestamp("2019-12-31")]), value])
        axes[0].plot(value.index, value, label=name, color=color, linewidth=1.5)
        axes[1].plot(value.index, 100 * (value / value.cummax() - 1), color=color, linewidth=1.2)
    axes[0].set(title="Held-out evaluation, 2020-2025", ylabel="Growth of opening $1")
    axes[0].legend(loc="upper left", fontsize=8)
    axes[1].set(ylabel="Drawdown (%)", xlabel="Date")
    for axis in axes:
        axis.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(OUTPUT / "holdout_wealth_drawdown.png", dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(9, 3.6))
    left = np.zeros(3)
    palette = plt.get_cmap("tab10").colors
    for ticker, color in zip(TICKERS, palette):
        width = 100 * mean_weights[ticker].to_numpy()
        axis.barh(NAMES, width, left=left, label=ticker, color=color)
        left += width
    axis.invert_yaxis()
    axis.set(xlabel="Average daily holding weight (%)", xlim=(0, 100),
             title="Concentration in consumer staples and health care")
    axis.legend(ncol=9, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.23))
    fig.tight_layout()
    fig.savefig(OUTPUT / "holdout_average_weights.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    x = np.arange(3)
    for offset, period, color in [(-0.19, "Development", "#8ca7c7"), (0.19, "Holdout", "#2563a6")]:
        rows = summary[(summary.period == period) & (summary.window == 252) & (summary.cost_bps == 5)].set_index("method").reindex(METHODS)
        axes[0].bar(x + offset, 100 * rows.annualised_volatility, width=0.38, label=period, color=color)
    base = selected.set_index("method").reindex(METHODS)
    axes[1].bar(x, 100 * base.annualised_one_way_turnover, color=colors)
    axes[0].set(title="Annualised volatility", ylabel="Percent")
    axes[1].set(title="Holdout one-way turnover", ylabel="Percent per year")
    for axis in axes:
        axis.set_xticks(x, ["Equal", "Sample", "Shrinkage"])
        axis.grid(axis="y", alpha=0.15)
        axis.set_axisbelow(True)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT / "risk_and_turnover.png", dpi=180)
    plt.close(fig)
    print("Saved presentation tables and three charts from existing outputs.")


if __name__ == "__main__":
    main()
