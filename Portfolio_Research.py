"""Compare equal weight, sample minimum variance and shrinkage minimum variance.

Run this file in PyCharm. The default run uses development data through 2019.
Read WALKTHROUGH.md alongside the numbered sections below.
"""

# 1. Imports and settings -----------------------------------------------------
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

ROOT = Path(__file__).resolve().parent
TICKERS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
METHODS = ["Equal weight", "Sample minimum variance", "Shrinkage minimum variance"]
WINDOWS = [252, 504]
COSTS_BPS = [0, 5]
TRADING_DAYS = 252
DEVELOPMENT_END = "2019-12-31"
HOLDOUT_START = "2020-01-01"
STUDY_END = "2025-12-31"


# 2. Read and check the adjusted-price data ----------------------------------
def load_prices(path):
    """Reject questionable structure rather than silently filling missing data."""
    prices = pd.read_csv(path, index_col="date", parse_dates=["date"])
    if list(prices.columns) != TICKERS:
        raise ValueError(f"Expected columns in this order: {TICKERS}")
    if prices.index.has_duplicates or prices.index.hasnans:
        raise ValueError("Prices contain duplicate or invalid dates.")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("Price dates must be sorted from oldest to newest.")
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError("Prices must be finite, positive and complete; do not fill gaps.")
    if len(prices) < max(WINDOWS) + 3:
        raise ValueError("Not enough history for the estimation windows.")
    return prices


def check_data(prices):
    returns = prices.pct_change(fill_method=None).dropna()
    flags = []
    for ticker in prices.columns:
        for date, value in returns[ticker][returns[ticker].abs() > 0.20].items():
            flags.append({"date": str(date.date()), "ticker": ticker, "return": value})
    return {
        "price_rows": len(prices), "return_rows": len(returns),
        "first_price": str(prices.index[0].date()),
        "last_price": str(prices.index[-1].date()),
        "missing_prices": int(prices.isna().sum().sum()),
        "large_return_flags": flags,
        "status": "Structural checks passed; independent adjustment review is incomplete.",
        "limitation": "These checks cannot detect a missing date shared by every ETF.",
    }


# 3. Estimate risk and choose portfolio weights ------------------------------
def portfolio_variance(weights, covariance):
    return weights @ covariance @ weights


def fully_invested(weights):
    return weights.sum() - 1


def minimum_variance(covariance):
    """Long-only minimum variance, with numerical checks on the solution."""
    covariance = np.asarray(covariance, dtype=float)
    if (covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]
            or not np.isfinite(covariance).all()):
        raise ValueError("Covariance must be a finite square matrix.")
    if (not np.allclose(covariance, covariance.T, atol=1e-12)
            or np.linalg.eigvalsh(covariance).min() < -1e-10):
        raise ValueError("Covariance must be symmetric and positive semidefinite.")
    number_of_assets = len(covariance)
    equal_weights = np.full(number_of_assets, 1 / number_of_assets)
    risk_scale = np.diag(covariance).mean()
    if risk_scale <= 0:
        raise ValueError("Average estimated variance must be positive.")
    scaled_covariance = covariance / risk_scale
    result = minimize(
        portfolio_variance,
        x0=equal_weights,
        args=(scaled_covariance,),
        # The derivative makes the numerical search more precise and efficient.
        jac=lambda weights, matrix: 2 * matrix @ weights,
        method="SLSQP",
        bounds=[(0, 1)] * number_of_assets,
        constraints={"type": "eq", "fun": fully_invested},
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    if not result.success:
        raise RuntimeError(f"Optimisation failed: {result.message}")
    weights = result.x
    if abs(weights.sum() - 1) > 1e-8 or weights.min() < -1e-8:
        raise RuntimeError("Optimiser returned invalid weights.")
    if (portfolio_variance(weights, scaled_covariance)
            > portfolio_variance(equal_weights, scaled_covariance) + 1e-8):
        raise RuntimeError("Optimiser returned more variance than equal weighting.")
    # Remove tiny numerical negatives and restore an exact sum of one.
    weights = np.maximum(weights, 0)
    return weights / weights.sum()


def estimate_weights(history, method):
    """Return target weights and the fitted shrinkage strength, if applicable."""
    if method == METHODS[0]:
        return np.full(history.shape[1], 1 / history.shape[1]), np.nan
    if method == METHODS[1]:
        # ddof=0 matches sklearn's denominator T; it changes risk scale, not weights.
        covariance = np.cov(history.to_numpy(), rowvar=False, ddof=0)
        return minimum_variance(covariance), np.nan
    if method == METHODS[2]:
        estimator = LedoitWolf().fit(history)
        return minimum_variance(estimator.covariance_), float(estimator.shrinkage_)
    raise ValueError(f"Unknown portfolio method: {method}")


# 4. Create month-end decisions and next-trading-day execution dates -----------
def build_targets(returns, window, method, common_warmup=504):
    """Only observations through the signal close can enter its risk estimate."""
    month_ends = returns.groupby(returns.index.to_period("M")).tail(1).index
    records = []
    for signal_date in month_ends:
        position = returns.index.get_loc(signal_date)
        if position + 1 < max(window, common_warmup):
            continue
        if position + 1 >= len(returns):
            continue  # No subsequent execution close in this dataset.
        history = returns.iloc[position - window + 1:position + 1]
        weights, shrinkage = estimate_weights(history, method)
        record = {
            "signal_date": signal_date,
            "execution_date": returns.index[position + 1],
            "history_start": history.index[0],
            "observations": len(history), "shrinkage": shrinkage,
        }
        record.update(dict(zip(returns.columns, weights)))
        records.append(record)
    if not records:
        raise ValueError("No eligible monthly allocations; check the history length.")
    return pd.DataFrame(records).set_index("execution_date")


# 5. Simulate changing holdings and trading costs -----------------------------
def apply_daily_returns(weights, nav, asset_returns):
    """Existing holdings earn today's return before any trade at today's close."""
    portfolio_return = float(weights @ asset_returns)
    growth = 1 + portfolio_return
    if growth <= 0:
        raise ValueError("Portfolio value became nonpositive.")
    drifted_weights = weights * (1 + asset_returns) / growth
    return drifted_weights, nav * growth, portfolio_return


def execute_trade(weights, target, nav, cost_rate, initial=False):
    """Cost approximation: rate times gross traded fraction of pre-cost NAV."""
    gross_traded = 1.0 if initial else float(np.abs(target - weights).sum())
    cost_fraction = cost_rate * gross_traded
    if cost_fraction >= 1:
        raise ValueError("Transaction costs would exhaust portfolio value.")
    cost_paid = nav * cost_fraction
    return target.copy(), nav - cost_paid, gross_traded, cost_paid


def simulate(returns, targets, cost_bps):
    """Start with one unit of capital; hold no position before first execution."""
    dates = returns.loc[targets.index[0]:].index
    target_lookup = {date: row for date, row in targets.iterrows()}
    weights = np.zeros(returns.shape[1])
    nav = 1.0
    cost_rate = cost_bps / 10000
    records = []
    for day_number, date in enumerate(dates):
        initial = day_number == 0
        previous_nav = nav
        market_return = 0.0
        if not initial:
            weights, nav, market_return = apply_daily_returns(
                weights, nav, returns.loc[date].to_numpy()
            )
        gross_traded, cost_paid = 0.0, 0.0
        if date in target_lookup:
            target = target_lookup[date][list(returns.columns)].to_numpy(dtype=float)
            weights, nav, gross_traded, cost_paid = execute_trade(
                weights, target, nav, cost_rate, initial=initial
            )
        record = {
            "date": date, "nav": nav, "net_return": nav / previous_nav - 1,
            "market_return": market_return, "cost_paid": cost_paid,
            "gross_traded": gross_traded,
            # Establishment is reported separately from portfolio rebalancing.
            "one_way_turnover": 0.0 if initial else gross_traded / 2,
            "initial_purchase": initial,
            "largest_weight": float(weights.max()),
            "concentration": float(weights @ weights),
        }
        record.update(dict(zip(returns.columns, weights)))
        records.append(record)
    return pd.DataFrame(records).set_index("date")


# 6. Measure performance on identical dates ----------------------------------
def summarise(path, start=None, end=None):
    selected = path.loc[start:end]
    if len(selected) < 2:
        raise ValueError("At least two dates are needed for a performance summary.")
    first_position = path.index.get_loc(selected.index[0])
    if first_position == 0:
        starting_nav = 1.0  # Includes the initial purchase cost in total return.
        starting_date = selected.index[0]
    else:
        starting_nav = path.iloc[first_position - 1]["nav"]
        starting_date = path.index[first_position - 1]
    years = (selected.index[-1] - starting_date).days / 365.25
    realised_returns = selected.loc[~selected["initial_purchase"], "net_return"]
    relative_nav = selected["nav"] / starting_nav
    # Include the opening capital as a possible high-water mark.
    running_peak = relative_nav.cummax().clip(lower=1.0)
    drawdown = relative_nav / running_peak - 1
    return {
        "first_date": str(selected.index[0].date()),
        "last_date": str(selected.index[-1].date()),
        "return_observations": len(realised_returns),
        "annualised_volatility": realised_returns.std(ddof=1) * np.sqrt(TRADING_DAYS),
        "total_return": relative_nav.iloc[-1] - 1,
        "cagr": relative_nav.iloc[-1] ** (1 / years) - 1,
        "maximum_drawdown": drawdown.min(),
        "annualised_one_way_turnover": selected["one_way_turnover"].sum() / years,
        "initial_gross_traded": selected.loc[selected["initial_purchase"], "gross_traded"].sum(),
        "average_largest_weight": selected["largest_weight"].mean(),
        "maximum_largest_weight": selected["largest_weight"].max(),
        "average_concentration": selected["concentration"].mean(),
    }


# 7. Save tables, charts and a readable research summary ----------------------
def save_charts(paths, targets, output):
    import matplotlib
    matplotlib.use("Agg")  # Save files without opening a native GUI window.
    import matplotlib.pyplot as plt

    selected = paths[(paths["window"] == 252) & (paths["cost_bps"] == 5)]
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for method in METHODS:
        rows = selected[selected["method"] == method].set_index("date")
        axes[0].plot(rows.index, rows["nav"], label=method, linewidth=1.4)
        peak = rows["nav"].cummax().clip(lower=1)
        axes[1].plot(rows.index, 100 * (rows["nav"] / peak - 1), linewidth=1.2)
    axes[0].set(title="Portfolio value: 252-day window, 5 bp trading cost", ylabel="Value of initial $1")
    axes[0].set_yscale("log")
    axes[0].legend(fontsize=8)
    axes[1].set(ylabel="Drawdown (%)", xlabel="Date")
    for axis in axes:
        axis.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output / "wealth_and_drawdown.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for axis, method in zip(axes, METHODS[1:]):
        rows = targets[(targets["window"] == 252) & (targets["method"] == method)]
        axis.stackplot(rows["execution_date"], *[rows[t] for t in TICKERS], labels=TICKERS)
        axis.set(title=method, ylabel="Target weight", ylim=(0, 1))
    axes[0].legend(ncol=9, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.35))
    axes[1].set_xlabel("Execution date")
    fig.tight_layout()
    fig.savefig(output / "target_weights.png", dpi=160)
    plt.close(fig)


def write_report(summary, audit, output, period):
    review_note = (
        "**Selected issuer checks completed; adjusted-close proxy limitations apply.**"
        if audit.get("independent_review_completed")
        else "**Provisional: independent price/corporate-action review is incomplete.**"
    )
    lines = [
        "# Portfolio optimisation: computational results",
        "", review_note,
        "Results describe this dataset, universe and fixed allocation rules.",
        "", f"Run selection: {period}. Price snapshot: {audit['first_price']} to {audit['last_price']}.",
        "", "## Fixed comparison",
        "Three long-only portfolios; monthly decisions, next-trading-day close execution;",
        "holdings drift between trades. The 252- and 504-day windows use identical evaluation dates.",
        "Costs are 0 or 5 basis points per dollar bought or sold. Initial purchase costs are included.",
        "", "## Results", "",
        "| Period | Window | Cost (bp) | Portfolio | Ann. vol. | CAGR | Max drawdown | Turnover/year | Avg. largest weight |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['period']} | {row['window']} | {row['cost_bps']} | {row['method']} "
            f"| {row['annualised_volatility']:.2%} | {row['cagr']:.2%} "
            f"| {row['maximum_drawdown']:.2%} | {row['annualised_one_way_turnover']:.2%} "
            f"| {row['average_largest_weight']:.2%} |"
        )
    lines.extend([
        "", "## Read the findings carefully",
        "Volatility is the primary outcome. Lower historical volatility is not a guarantee of future protection.",
        "Concentration and turnover describe the price of any risk reduction. A variance objective does not maximise return.",
        "No statistical significance, universal dominance or causal claim is made.",
        "", "## Accounting definitions",
        "Annualised volatility = sample standard deviation of daily net returns times sqrt(252).",
        "CAGR uses elapsed calendar years; initial establishment cost is included in return and drawdown,",
        "but its isolated opening row is excluded from daily return volatility.",
        "One-way turnover is half the sum of absolute changes from drifted weights to target weights.",
        "Initial establishment has gross traded fraction 1 and is excluded from recurring turnover.",
        "Concentration is the sum of squared weights, measured after each daily close and trade.",
        "Segment drawdowns restart from segment-opening capital; a holdout segment inherits existing holdings.",
        "", "## Limitations",
        "Provider adjusted closes proxy reinvested total returns; they are not executable prices.",
        "Costs use a pre-cost-NAV approximation and constant illustrative rates, with no spread/impact calibration.",
        "ETF classifications and holdings change; these nine ETFs do not cover every modern sector.",
        "No terminal liquidation cost, taxes or separate fund-fee deduction is assumed.",
        "The fixed universe was selected with hindsight; this is not a point-in-time universe-selection study.",
        "Independent checks and remaining source/convention limitations are documented in DATA_REVIEW.md.",
    ])
    if period == "development":
        lines.extend(["", "The 2020–2025 final evaluation was not run. Do not quote these development results as holdout findings."])
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# 8. Run the complete experiment --------------------------------------------
def run_study(price_file, output, period="development", charts=True):
    prices = load_prices(price_file)
    audit = check_data(prices)
    review_file = ROOT / "reference/independent_data_review.json"
    if review_file.exists():
        review = json.loads(review_file.read_text(encoding="utf-8"))
        matches = review.get("prices_sha256") == hashlib.sha256(Path(price_file).read_bytes()).hexdigest()
        if matches and review.get("status") == "reviewed_with_limitations":
            audit["independent_review_completed"] = True
            audit["status"] = "Selected issuer checks completed with documented source/convention limitations."
            audit["independent_review_limits"] = review["limits"]
    # Truncate BEFORE creating returns/targets: development cannot access future outcomes.
    end = DEVELOPMENT_END if period == "development" else STUDY_END
    returns = prices.loc[:end].pct_change(fill_method=None).dropna()
    paths, targets, summaries = [], [], []
    for window in WINDOWS:
        for method in METHODS:
            monthly_targets = build_targets(returns, window, method, max(WINDOWS))
            target_table = monthly_targets.reset_index().assign(window=window, method=method)
            targets.append(target_table)
            for cost_bps in COSTS_BPS:
                path = simulate(returns, monthly_targets, cost_bps)
                paths.append(path.reset_index().assign(window=window, method=method, cost_bps=cost_bps))
                segments = {"Development": (None, DEVELOPMENT_END)}
                if period != "development":
                    segments["Holdout"] = (HOLDOUT_START, STUDY_END)
                    if period == "all":
                        segments["Full sample"] = (None, STUDY_END)
                for label, (start, finish) in segments.items():
                    statistics = summarise(path, start, finish)
                    summaries.append(dict(period=label, window=window, method=method,
                                          cost_bps=cost_bps, **statistics))
    summary = pd.DataFrame(summaries)
    for _, indices in summary.groupby(["period", "window", "cost_bps"]).groups.items():
        group = summary.loc[indices]
        benchmark = group.loc[group["method"] == METHODS[0], "annualised_volatility"].iloc[0]
        summary.loc[indices, "relative_volatility_reduction"] = 1 - group["annualised_volatility"] / benchmark
    all_paths = pd.concat(paths, ignore_index=True)
    all_targets = pd.concat(targets, ignore_index=True)
    output.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output / "summary.csv", index=False)
    all_paths.to_csv(output / "daily_paths.csv", index=False)
    all_targets.to_csv(output / "target_weights.csv", index=False)
    (output / "data_checks.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    manifest = {
        "period": period, "windows": WINDOWS, "costs_bps": COSTS_BPS,
        "tickers": TICKERS, "python": platform.python_version(),
        "versions": {name: importlib.metadata.version(name) for name in
                     ["numpy", "pandas", "scipy", "scikit-learn"]},
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "prices_sha256": hashlib.sha256(Path(price_file).read_bytes()).hexdigest(),
        "final_evaluation_opened": period != "development",
        "data_review": audit["status"],
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_report(summary, audit, output, period)
    if charts:
        save_charts(all_paths, all_targets, output)
    print("\n" + audit["status"])
    print(summary[["period", "window", "cost_bps", "method", "annualised_volatility",
                   "cagr", "annualised_one_way_turnover"]].to_string(index=False, formatters={
                       name: lambda value: f"{value:.2%}" for name in
                       ["annualised_volatility", "cagr", "annualised_one_way_turnover"]
                   }))
    print(f"\nSaved results to: {output}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices", type=Path, default=ROOT / "research/data/adjusted_prices.csv")
    parser.add_argument("--period", choices=["development", "all"], default="development",
                        help="Finish the independent data review before opening the final evaluation.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-charts", action="store_true")
    arguments = parser.parse_args()
    output = arguments.output or ROOT / "research/results" / arguments.period
    run_study(arguments.prices, output, arguments.period, charts=not arguments.no_charts)


if __name__ == "__main__":
    main()
