# How to understand the finished project

Read the main Python file from top to bottom. You do not need to learn everything
in one sitting. The numbered sections in that file correspond to this guide.

## The question in one sentence

We estimate how nine sector ETFs move together, choose the long-only allocation
with the lowest estimated variance, and check whether that allocation reduces
volatility in subsequent observations compared with equal weighting.

There are two optimised portfolios because estimated covariance contains noise.
Ledoit–Wolf shrinkage is an alternative way to estimate covariance, rather than
a different definition of what the portfolio is trying to minimise.

## 1. Imports and settings

`import` makes functions from an installed package available. `as np` and `as pd`
give NumPy and pandas shorter names. `from ... import ...` imports one named item.

- pandas handles dated tables: a DataFrame has rows and columns; a Series is one
  column or one-dimensional labelled sequence.
- NumPy handles arrays and matrix calculations.
- SciPy performs constrained numerical minimisation.
- scikit-learn fits the Ledoit–Wolf covariance estimate.
- matplotlib creates saved charts. Its Agg backend avoids opening a native GUI.
- pathlib handles file locations; argparse reads optional terminal settings.
- hashlib records fingerprints of code/data. A hash establishes which bytes were
  used; it does not establish that a financial data source is correct.

`ROOT = Path(__file__).resolve().parent` finds the folder containing the script.
Data paths therefore work even when PyCharm's working directory differs.
Uppercase names are a convention for settings we intend to keep fixed.

`WINDOWS = [252, 504]` means roughly one and two trading years of observations.
These are lookback lengths, not lengths of the eventual backtest.
`COSTS_BPS = [0, 5]`: one basis point is 0.0001 in decimal units, so 5 bp is 0.0005.
`TRADING_DAYS = 252` is an annualisation convention, not a guarantee that each
calendar year contains exactly 252 trading days.

## 2. Prices become daily returns

`read_csv` loads the price table. `index_col='date'` makes dates row labels;
`parse_dates` converts their text into datetime values.

The code rejects duplicate dates, unsorted dates, missing/nonfinite values,
nonpositive prices, and an unexpected asset order. Asset order matters because
NumPy weight arrays do not carry ticker labels.

We use simple returns: r_t = P_t / P_(t-1) - 1.
`pct_change(fill_method=None)` calculates them without filling gaps.
The first observation has no preceding price, so its return is missing and
`dropna()` removes that first row. Prior validation means no other gaps should
be hidden by this operation.

Adjusted prices are a proxy for reinvested distributions and split-adjusted value.
They are not prices at which we could literally trade. Corporate-action handling
is a separate data-quality question; no Python formula automatically verifies it.

`check_data` also lists daily moves exceeding 20% in absolute magnitude for review.
An extreme move is a flag to investigate, not an instruction to delete it.

## 3. From covariance to an allocation

For nine ETF returns, covariance is a 9-by-9 matrix S. Its diagonal entries are
variances. Off-diagonal entries are covariances between pairs of ETFs.

With weight vector w, portfolio variance is w^T S w.
`weights @ covariance @ weights` computes this quantity with NumPy's matrix
multiplication operator. The first/last vectors are one-dimensional arrays;
NumPy handles the row/column orientation for this scalar expression.

The optimiser minimises variance rather than standard deviation because the
square root is increasing: both objectives have the same minimiser.
We impose sum(w)=1 and 0 <= w_i <= 1. We do not forecast expected returns.

`minimum_variance` validates the matrix and divides it by its average diagonal
variance. Multiplying an entire objective by a positive constant leaves its
minimiser unchanged; this scaling helps numerical stopping tolerances.

`minimize` receives the objective function itself, an equal-weight starting point,
the matrix in `args`, bounds, and an equality constraint. The comma in `(matrix,)`
makes it a one-element tuple rather than a parenthesised expression.

`fully_invested` returns sum(w)-1. SciPy's equality constraint requires its return
value to equal zero. `result.success` tells us whether optimisation converged;
`result.x` contains the resulting weights.

`jac=lambda weights, matrix: 2 * matrix @ weights` supplies the gradient of w^T S w
for symmetric S. A lambda is a short unnamed function. SciPy could approximate
this derivative numerically, but the exact derivative is simple here.
`ftol` and `maxiter` control solver convergence, not any economic forecast.

The code checks feasibility and that the reported objective is no worse than
the feasible equal-weight starting portfolio. Tiny numerical negative weights
are clipped to zero and weights are normalised after these checks.

The sample estimate uses `np.cov(..., rowvar=False, ddof=0)`. Columns are assets;
the denominator is T, matching sklearn's empirical covariance convention.
Your earlier pandas `.cov()` used T-1. This uniform scale difference does not
change the sample minimum-variance weights.

For shrinkage, `LedoitWolf().fit(history)` estimates
S_LW = (1-lambda) S + lambda mu I, with mu = trace(S)/number_of_assets.
`covariance_` and `shrinkage_` are fitted attributes. Lambda is estimated from
the past window; it is not manually selected after looking at results.

The target has equal variances and zero covariances. Its contribution to the
objective is lambda * mu * sum(w_i^2), which discourages concentrated weights.
That helps explain why shrinkage can spread allocations, but it does not
guarantee lower future risk, lower turnover or a particular weight change.

## 4. Monthly decisions and the trading lag

`groupby(returns.index.to_period('M')).tail(1)` finds the last observed trading
date in each month. `.get_loc` finds its integer position in the date index.

For a signal at position i, the risk window includes rows i-window+1 through i.
The slice ends at i+1 because Python's right-hand slice endpoint is excluded.
It includes the signal-day close, which is available after that close.

Execution is at position i+1: the following trading day's close. If no execution
date remains, that final signal is not used. This dataset ends at a complete
calendar month-end; a truncated in-progress month should not be added as if it
were a completed month without changing the schedule rules.

Both lookbacks wait until 504 observations are available. The 252-day method
therefore does not receive an earlier evaluation start than the 504-day method.
On the supplied data, the first common signal is 31 January 2006, execution is
1 February, and the first invested close-to-close return ends on 2 February.

Each target record saves its signal date, history start, observation count,
execution date, shrinkage strength where applicable, and nine target weights.
This makes the timing inspectable rather than implicit.

## 5. Why we simulate holdings, not just multiply every day by fixed weights

If an ETF rises faster than the others, its share of portfolio value grows.
For previous-close weights w and today's returns r:

- portfolio return = sum(w_i * r_i)
- value before trading = old value * (1 + portfolio return)
- drifted weight i = w_i * (1+r_i) / (1+portfolio return)

`apply_daily_returns` implements these equations. The simulation applies them
BEFORE a trade at that day's close. New target weights earn returns from the
next close-to-close interval onwards. The initial entry earns no return on its
purchase date because we were not invested at the preceding close.

`simulate` uses a loop over dates. A dictionary connects execution dates to
target rows, so the code can ask `if date in target_lookup`.
Most dates have no trade; the drifted holdings simply carry into tomorrow.

For a rebalance, gross traded fraction G = sum(abs(target - drifted weights)).
Switching entirely from A to B gives G=2: sell 100%, buy 100%.
One-way turnover is G/2. Rebalancing an already equal-weight portfolio back to
equal weight can still require trading because its holdings have drifted.

With cost rate c, the model charges pre-trade NAV * c * G. The target allocation
is applied to the remaining value. This is a transparent pre-cost-weight
approximation, not an exact share-level execution model with endogenous costs.
At entry from cash, G=1. That purchase cost is included but not counted as
recurring one-way turnover. No terminal liquidation cost is charged.

`nav` means net asset value: here it starts at one unit of capital.
The cost amount is in those capital units, not an independently assumed £ amount.

## 6. What each metric actually answers

| Metric | Definition and purpose |
|---|---|
| Annualised volatility | Sample daily return standard deviation times sqrt(252); primary risk outcome |
| Total return | Ending value / opening capital minus 1 |
| CAGR | Geometric annual growth using elapsed calendar years |
| Maximum drawdown | Worst decline from a previous high-water mark |
| Annualised one-way turnover | Sum of recurring one-way turnover / elapsed calendar years |
| Average largest weight | Average across daily post-close holdings of the largest allocation |
| Maximum largest weight | Largest observed single holding weight in the period |
| Average concentration | Average daily sum of squared holding weights |
| Relative volatility reduction | 1 - portfolio volatility / equal-weight volatility, on matching dates |

For concentration, equal weights across nine assets give 1/9; a single-asset
portfolio gives 1. Drift can move equal-weight holdings away from 1/9 between trades.

Initial establishment affects total return, CAGR and drawdown. Its isolated
entry-cost row has no invested market return and is excluded from realised
daily return volatility. Subsequent rebalance costs remain in daily net returns.

For a holdout segment starting in 2020, opening capital is the preceding
portfolio NAV. Existing positions carry over. Segment drawdown restarts at
the segment's opening value, rather than importing a high-water mark from 2019.

Zero-cost and cost-inclusive volatility need not move in one direction: costs
alter the daily return sequence. However, on the same holdings path, costs must
lower final wealth. Our tests check that relationship.

## 7. What gets saved

`summary.csv` has one row per period, lookback, method and cost scenario.
Percentages are decimal values: 0.15 means 15%; turnover 0.70 means 70% per year.
`daily_paths.csv` records each day's value, return, costs, trading and holdings.
`target_weights.csv` records monthly decisions and estimation dates.
The readable RESULTS.md formats the main comparisons as percentages.

Charts show value/drawdown for the baseline 252-day window with 5 bp costs,
and target allocations for the two optimised methods. The wealth chart uses
a logarithmic vertical scale. Colours represent ETFs in the weight chart.
The final evaluation has now been run. The all-results folder also contains holdout-specific charts and a short research report.

The manifest records code/data hashes and package versions. The original
provider responses and download metadata are retained separately.

## 8. How the script starts and how to study it

`def` defines a reusable function; its body runs when called. Parameters are
placeholders for the arguments supplied to that call. `return` sends a result
back. A returned tuple can be unpacked into several names, such as
`weights, strength = estimate_weights(...)`.

`run_study` connects the preceding functions. Its nested loops cover two
lookbacks, three methods and two cost assumptions. Each method's weights are
estimated once per lookback and reused across cost assumptions: costs do not
feed into the minimum-variance objective in this project.

`if __name__ == '__main__': main()` runs the study when the file is executed,
but allows tests to import functions without accidentally running the study.
The default argument `--period development` cuts the performance input at 2019
before constructing returns and allocations. `--period all` opens the final
evaluation and produces separate development, holdout and whole-period tables.

Suggested reading order:

1. Follow one two-asset variance calculation through `minimum_variance`.
2. Follow one month-end signal through `build_targets`.
3. Work through the three-day fictional example in `test_buy_and_hold_matches_fixed_units`.
4. Work through a full switch between assets in the cost test.
5. Read `summarise`, checking what its opening capital means.
6. Read `run_study` last, once each smaller function makes sense.

## Questions to be able to answer without notes

- Why is covariance needed rather than just ranking individual volatilities?
- What makes the sample covariance estimate noisy?
- What does Ledoit–Wolf shrink towards, and what does its strength mean?
- Why is the minimum of historical variance not evidence of future success?
- Why does multiplying returns by the same weights every day imply rebalancing?
- What information is available at a signal date, and when can it be traded?
- How is turnover different from a change in target weights between months?
- Why can a low-volatility portfolio still be highly concentrated?
- Why can't development findings be presented as unseen final-evaluation results?
- What do the data checks and tests still fail to establish?

The defensible interview explanation is the question, design, verified findings
and limitations you understand. The code and this guide give you a concrete
implementation to study; completing the reading remains part of the project.

## Completion update - 22 October 2026

Selected issuer checks and the real 2020-2025 evaluation are complete. Read DATA_REVIEW.md for the source limitations and RESEARCH_FINDINGS.pdf for the results. The methods were retained unchanged when opening the final period. The teaching sequence above still applies.
