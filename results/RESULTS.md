# Portfolio optimisation: computational results

**Selected issuer checks completed; adjusted-close proxy limitations apply.**
Results describe this dataset, universe and fixed allocation rules.

Run selection: all. Price snapshot: 2004-01-02 to 2025-12-31.

## Fixed comparison
Three long-only portfolios; monthly decisions, next-trading-day close execution;
holdings drift between trades. The 252- and 504-day windows use identical evaluation dates.
Costs are 0 or 5 basis points per dollar bought or sold. Initial purchase costs are included.

## Results

| Period | Window | Cost (bp) | Portfolio | Ann. vol. | CAGR | Max drawdown | Turnover/year | Avg. largest weight |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Development | 252 | 0 | Equal weight | 18.10% | 9.12% | -53.27% | 13.62% | 11.45% |
| Holdout | 252 | 0 | Equal weight | 19.82% | 12.49% | -36.71% | 17.24% | 11.58% |
| Full sample | 252 | 0 | Equal weight | 18.63% | 10.12% | -53.27% | 14.71% | 11.49% |
| Development | 252 | 5 | Equal weight | 18.10% | 9.10% | -53.29% | 13.62% | 11.45% |
| Holdout | 252 | 5 | Equal weight | 19.82% | 12.47% | -36.72% | 17.24% | 11.58% |
| Full sample | 252 | 5 | Equal weight | 18.63% | 10.11% | -53.29% | 14.71% | 11.49% |
| Development | 252 | 0 | Sample minimum variance | 12.98% | 10.30% | -35.69% | 76.21% | 61.52% |
| Holdout | 252 | 0 | Sample minimum variance | 16.82% | 5.95% | -32.94% | 77.90% | 57.28% |
| Full sample | 252 | 0 | Sample minimum variance | 14.25% | 8.97% | -35.69% | 76.72% | 60.24% |
| Development | 252 | 5 | Sample minimum variance | 12.98% | 10.21% | -35.76% | 76.21% | 61.52% |
| Holdout | 252 | 5 | Sample minimum variance | 16.82% | 5.87% | -32.95% | 77.90% | 57.28% |
| Full sample | 252 | 5 | Sample minimum variance | 14.25% | 8.88% | -35.76% | 76.72% | 60.24% |
| Development | 252 | 0 | Shrinkage minimum variance | 13.01% | 10.28% | -35.87% | 70.54% | 56.64% |
| Holdout | 252 | 0 | Shrinkage minimum variance | 16.84% | 7.08% | -32.88% | 73.95% | 50.50% |
| Full sample | 252 | 0 | Shrinkage minimum variance | 14.27% | 9.30% | -35.87% | 71.57% | 54.80% |
| Development | 252 | 5 | Shrinkage minimum variance | 13.01% | 10.20% | -35.93% | 70.54% | 56.64% |
| Holdout | 252 | 5 | Shrinkage minimum variance | 16.84% | 7.00% | -32.89% | 73.95% | 50.50% |
| Full sample | 252 | 5 | Shrinkage minimum variance | 14.27% | 9.22% | -35.93% | 71.57% | 54.80% |
| Development | 504 | 0 | Equal weight | 18.10% | 9.12% | -53.27% | 13.62% | 11.45% |
| Holdout | 504 | 0 | Equal weight | 19.82% | 12.49% | -36.71% | 17.24% | 11.58% |
| Full sample | 504 | 0 | Equal weight | 18.63% | 10.12% | -53.27% | 14.71% | 11.49% |
| Development | 504 | 5 | Equal weight | 18.10% | 9.10% | -53.29% | 13.62% | 11.45% |
| Holdout | 504 | 5 | Equal weight | 19.82% | 12.47% | -36.72% | 17.24% | 11.58% |
| Full sample | 504 | 5 | Equal weight | 18.63% | 10.11% | -53.29% | 14.71% | 11.49% |
| Development | 504 | 0 | Sample minimum variance | 12.92% | 10.32% | -35.26% | 43.17% | 62.77% |
| Holdout | 504 | 0 | Sample minimum variance | 17.18% | 5.46% | -34.72% | 46.84% | 61.90% |
| Full sample | 504 | 0 | Sample minimum variance | 14.34% | 8.83% | -35.26% | 44.28% | 62.51% |
| Development | 504 | 5 | Sample minimum variance | 12.92% | 10.27% | -35.31% | 43.17% | 62.77% |
| Holdout | 504 | 5 | Sample minimum variance | 17.18% | 5.41% | -34.73% | 46.84% | 61.90% |
| Full sample | 504 | 5 | Sample minimum variance | 14.34% | 8.78% | -35.31% | 44.28% | 62.51% |
| Development | 504 | 0 | Shrinkage minimum variance | 12.94% | 10.25% | -35.49% | 41.25% | 59.72% |
| Holdout | 504 | 0 | Shrinkage minimum variance | 17.20% | 6.01% | -34.62% | 45.07% | 56.28% |
| Full sample | 504 | 0 | Shrinkage minimum variance | 14.36% | 8.95% | -35.49% | 42.40% | 58.68% |
| Development | 504 | 5 | Shrinkage minimum variance | 12.94% | 10.20% | -35.53% | 41.25% | 59.72% |
| Holdout | 504 | 5 | Shrinkage minimum variance | 17.20% | 5.96% | -34.62% | 45.07% | 56.28% |
| Full sample | 504 | 5 | Shrinkage minimum variance | 14.36% | 8.90% | -35.53% | 42.40% | 58.68% |

## Read the findings carefully
Volatility is the primary outcome. Lower historical volatility is not a guarantee of future protection.
Concentration and turnover describe the price of any risk reduction. A variance objective does not maximise return.
No statistical significance, universal dominance or causal claim is made.

## Accounting definitions
Annualised volatility = sample standard deviation of daily net returns times sqrt(252).
CAGR uses elapsed calendar years; initial establishment cost is included in return and drawdown,
but its isolated opening row is excluded from daily return volatility.
One-way turnover is half the sum of absolute changes from drifted weights to target weights.
Initial establishment has gross traded fraction 1 and is excluded from recurring turnover.
Concentration is the sum of squared weights, measured after each daily close and trade.
Segment drawdowns restart from segment-opening capital; a holdout segment inherits existing holdings.

## Limitations
Provider adjusted closes proxy reinvested total returns; they are not executable prices.
Costs use a pre-cost-NAV approximation and constant illustrative rates, with no spread/impact calibration.
ETF classifications and holdings change; these nine ETFs do not cover every modern sector.
No terminal liquidation cost, taxes or separate fund-fee deduction is assumed.
The fixed universe was selected with hindsight; this is not a point-in-time universe-selection study.
Independent checks and remaining source/convention limitations are documented in DATA_REVIEW.md.
