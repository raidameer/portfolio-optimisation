# Does Portfolio Optimisation Deliver?
## Research specification v1 — 20 October 2026

Question: Does long-only minimum-variance allocation reduce subsequent volatility relative to equal weights, and what concentration and turnover accompany the reduction?

This specification is written before examining strategy performance. No winner is assumed. This is a student empirical investigation, not a novel optimiser or investment recommendation. AI assists implementation and exposition; the student reviews methods, checks and interpretation.

## Fixed design
- Universe, in order: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY. These are long-history funds, not a constant representation of all modern GICS sectors. Holdings and classifications change.
- Requested raw daily observations: 2004-01-01 through 2025-12-31. The first two years provide warm-up for the alternative window.
- Development performance period: 2006–2019. Final evaluation: 2020–2025. Data-quality checks may inspect all dates, but no test-period strategy outcomes will be examined until implementation and choices are frozen.
- Methods: equal weights; minimum variance with sample covariance; minimum variance with sklearn LedoitWolf covariance (scaled identity target, 2004 methodology).
- Sample covariance uses denominator T to match sklearn's convention. Its scalar normalisation does not affect the minimum-variance weights.
- Constraints: weights sum to one, each between zero and one. No additional cap, leverage, shorting, or expected-return forecasts.
- Estimation: last 252 complete daily simple-return observations available at calendar month-end. One robustness check: 504 observations, evaluated on the same performance dates.
- Timing: compute target after month-end close, execute at the following trading day's close. Existing holdings earn that execution day's return; new weights start earning the next close-to-close return. No same-close information/execution assumption.
- Holdings drift between monthly rebalances. Equal weighting also rebalances monthly.
- Adjusted close is treated as a total-return proxy, subject to provider/action audit. It is not an executable price. This is a frictionless-close allocation approximation with explicit cost sensitivity, not a precise exchange execution simulation.
- Initial portfolio enters at first eligible execution close. Include initial establishment cost; no assumed terminal liquidation.
- One-way turnover = 0.5 sum(abs(target minus pre-trade drifted weights)); also report gross traded fraction = sum(abs(...)). Initial gross traded fraction = 1, treated separately from switching between invested assets.
- Baseline cost assumption: 5 basis points per dollar bought or sold, hence cost fraction = 0.0005 times gross traded fraction. Report zero-cost results alongside it. This is an illustrative cost assumption, not a measured historical spread. Cost deducted from NAV at execution; target weights apply to remaining NAV. ETF expenses already reflected in fund prices must not be deducted again.

## Evaluation
Primary: annualised realised daily volatility, using sample standard deviation times sqrt(252). Report ratios versus equal weight without assuming statistical significance.
Secondary: compound return/CAGR, maximum drawdown, annualised turnover, largest weight, and sum of squared weights. Do not declare highest-return or lowest-drawdown portfolio the winner of a variance objective.
Interpret weights to distinguish broad diversification from concentration in defensive sectors. Compare sample and shrinkage portfolios under identical constraints.
No Sharpe ratio required for the first version. No optimisation of costs, windows or universe after seeing final outcomes. No claim of causality or universal dominance. Formal significance tests require time-series-aware uncertainty; a naive daily independent-observation t-test is not acceptable.

## Data gate
Preserve downloaded responses and SHA256 hashes, retrieval timestamps, source URLs and versions. Check positive prices, duplicates, common dates, missing rows, extreme changes and corporate actions. Never silently forward-fill missing prices. Validate selected distribution/split dates against independent sources, particularly XLF's September 2016 special distribution; review 2018 sector reclassifications. Provider adjusted-close fields alone do not establish correct adjustment. A failure here blocks final empirical claims.

## Build gates
1. Obtain data and write a data audit (in progress).
2. Explain and test covariance and the two-asset analytical solution; inspect one development-only allocation.
3. Implement drift, trading lag and costs; test with hand-computable paths.
4. Run development analysis and freeze code/configuration.
5. Open final evaluation once, run the predeclared alternative window, write findings.

## References
- DeMiguel, Garlappi & Uppal (2009): https://doi.org/10.1093/rfs/hhm075
- Ledoit & Wolf (2004), A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices. Implementation: https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html
- The different single-index shrinkage estimator in Ledoit & Wolf (2003) is not what sklearn implements: https://econ-papers.upf.edu/en/onepaper.php?id=586
- WFS Mathematical Finance Magazine, Vol. 5, pp. 35–42 motivates correlation/diversification questions; it is not the source of this exact experiment.

Completion target: 31 October 2026. Preserve application and test-preparation time. Full portfolio backtest is intentionally not part of the first teaching milestone.
