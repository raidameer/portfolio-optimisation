"""Hand-computable and timing checks. Run: python -m unittest -v test_backtest"""
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from Portfolio_Research import (
    minimum_variance, estimate_weights, build_targets, simulate, summarise,
    apply_daily_returns, execute_trade, run_study, METHODS, TICKERS,
)


class AllocationTests(unittest.TestCase):
    def test_analytical_solution_and_scale(self):
        covariance = np.diag([0.04, 0.01])
        weights = minimum_variance(covariance)
        np.testing.assert_allclose(weights, [0.2, 0.8], atol=1e-6)
        np.testing.assert_allclose(minimum_variance(covariance / 252), weights, atol=1e-6)

    def test_boundary_solution(self):
        covariance = np.array([[0.04, 0.018], [0.018, 0.01]])
        np.testing.assert_allclose(minimum_variance(covariance), [0, 1], atol=1e-6)

    def test_equal_risk_symmetry(self):
        np.testing.assert_allclose(minimum_variance(np.eye(9)), np.full(9, 1 / 9), atol=1e-6)

    def test_invalid_covariance_rejected(self):
        with self.assertRaises(ValueError):
            minimum_variance(np.array([[1, 2], [2, 1]]))

    def test_shrinkage_constraints(self):
        history = pd.DataFrame(np.random.default_rng(7).normal(size=(50, 9)))
        weights, strength = estimate_weights(history, METHODS[2])
        self.assertAlmostEqual(weights.sum(), 1)
        self.assertGreaterEqual(weights.min(), 0)
        self.assertTrue(0 <= strength <= 1)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.bdate_range("2019-01-02", periods=4)
        self.returns = pd.DataFrame([[0.9, -0.8], [0.1, 0], [0, 0.1], [0.1, 0]],
                                    index=self.dates, columns=["A", "B"])

    def targets(self, rows):
        return pd.DataFrame(rows, columns=["A", "B"], index=self.dates[:len(rows)])

    def test_daily_drift(self):
        weights, nav, daily_return = apply_daily_returns(np.array([0.5, 0.5]), 1, np.array([0.1, 0]))
        self.assertAlmostEqual(nav, 1.05)
        self.assertAlmostEqual(daily_return, 0.05)
        np.testing.assert_allclose(weights, [0.55 / 1.05, 0.5 / 1.05])

    def test_buy_and_hold_matches_fixed_units(self):
        path = simulate(self.returns, self.targets([[0.5, 0.5]]), 0)
        # We enter at first close; that day's 90%/-80% returns are not earned.
        expected = np.array([1, 1.05, 1.10, 1.155])
        np.testing.assert_allclose(path["nav"], expected)
        self.assertAlmostEqual(path.iloc[2]["A"], 0.5)

    def test_execution_day_uses_old_holdings(self):
        targets = self.targets([[1, 0], [0, 1]])
        path = simulate(self.returns, targets, 0)
        # Second-day return is A's 10%, before switching to B at the close.
        self.assertAlmostEqual(path.iloc[1]["nav"], 1.1)
        self.assertAlmostEqual(path.iloc[2]["nav"], 1.21)

    def test_initial_and_round_trip_costs(self):
        path = simulate(self.returns, self.targets([[1, 0], [0, 1]]), 5)
        self.assertAlmostEqual(path.iloc[0]["nav"], 0.9995)
        self.assertAlmostEqual(path.iloc[1]["gross_traded"], 2)
        self.assertAlmostEqual(path.iloc[1]["one_way_turnover"], 1)
        self.assertAlmostEqual(path.iloc[1]["nav"], 0.9995 * 1.1 * 0.999)
        self.assertEqual(path.iloc[0]["one_way_turnover"], 0)

    def test_turnover_uses_drifted_weights(self):
        path = simulate(self.returns, self.targets([[0.5, 0.5], [0.5, 0.5]]), 0)
        self.assertAlmostEqual(path.iloc[1]["one_way_turnover"], 0.55 / 1.05 - 0.5)

    def test_trade_cost_formula(self):
        _, nav, gross, cost = execute_trade(np.array([0.7, 0.3]), np.array([0.4, 0.6]), 100, 0.0005)
        self.assertAlmostEqual(gross, 0.6)
        self.assertAlmostEqual(cost, 0.03)
        self.assertAlmostEqual(nav, 99.97)

    def test_cost_does_not_change_relative_holdings(self):
        targets = self.targets([[0.5, 0.5], [0.4, 0.6]])
        free = simulate(self.returns, targets, 0)
        costly = simulate(self.returns, targets, 5)
        np.testing.assert_allclose(free[["A", "B", "gross_traded"]], costly[["A", "B", "gross_traded"]])
        self.assertTrue((costly["nav"] <= free["nav"]).all())

    def test_drawdown_includes_opening_capital(self):
        flat = self.returns * 0
        path = simulate(flat, self.targets([[0.5, 0.5]]), 5)
        metrics = summarise(path)
        self.assertAlmostEqual(metrics["total_return"], -0.0005)
        self.assertAlmostEqual(metrics["maximum_drawdown"], -0.0005)
        self.assertAlmostEqual(metrics["annualised_volatility"], 0)
        self.assertEqual(metrics["return_observations"], 3)

    def test_segment_uses_previous_nav(self):
        path = simulate(self.returns, self.targets([[0.5, 0.5]]), 0)
        metrics = summarise(path, str(self.dates[2].date()))
        self.assertAlmostEqual(metrics["total_return"], 1.155 / 1.05 - 1)


class TimingTests(unittest.TestCase):
    def test_windows_share_the_same_start(self):
        dates = pd.bdate_range("2004-01-02", "2007-12-31")
        history = pd.DataFrame(np.random.default_rng(3).normal(0, 0.01, (len(dates), 2)),
                               index=dates, columns=["A", "B"])
        short = build_targets(history, 252, METHODS[1])
        long = build_targets(history, 504, METHODS[1])
        pd.testing.assert_index_equal(short.index, long.index)

    def test_future_changes_cannot_change_earlier_decision(self):
        dates = pd.bdate_range("2018-01-01", "2019-06-30")
        history = pd.DataFrame(np.random.default_rng(4).normal(0, 0.01, (len(dates), 2)),
                               index=dates, columns=["A", "B"])
        first = build_targets(history, 40, METHODS[1], common_warmup=40)
        changed = history.copy()
        cutoff = pd.Timestamp("2018-12-31")
        changed.loc[changed.index > cutoff] *= 100
        second = build_targets(changed, 40, METHODS[1], common_warmup=40)
        a = first[first["signal_date"] <= cutoff]
        b = second[second["signal_date"] <= cutoff]
        pd.testing.assert_frame_equal(a, b)
        for execution, row in first.iterrows():
            signal_position = dates.get_loc(row["signal_date"])
            self.assertEqual(execution, dates[signal_position + 1])
            self.assertEqual(row["observations"], 40)


class CompleteStudyTests(unittest.TestCase):
    def test_full_pipeline_uses_fictional_data_for_holdout_branch(self):
        # This exercises the final-evaluation code without opening real 2020-25 results.
        dates = pd.bdate_range("2004-01-02", "2025-12-31")
        fictional_returns = np.random.default_rng(11).normal(0.0002, 0.01, (len(dates), 9))
        prices = pd.DataFrame(100 * np.cumprod(1 + fictional_returns, axis=0),
                              index=dates, columns=TICKERS)
        prices.index.name = "date"
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prices.to_csv(folder / "prices.csv")
            with redirect_stdout(StringIO()):
                summary = run_study(folder / "prices.csv", folder / "output", "all", charts=False)
            self.assertEqual(set(summary["period"]), {"Development", "Holdout", "Full sample"})
            self.assertEqual(len(summary), 36)
            self.assertTrue(np.isfinite(summary["annualised_volatility"]).all())
            self.assertTrue((folder / "output/run_manifest.json").exists())
            holdout = summary[summary["period"] == "Holdout"]
            self.assertEqual(holdout["first_date"].nunique(), 1)
            for _, group in summary.groupby(["period", "window", "method"]):
                zero_cost = group[group["cost_bps"] == 0].iloc[0]
                with_cost = group[group["cost_bps"] == 5].iloc[0]
                self.assertLess(with_cost["total_return"], zero_cost["total_return"])
                self.assertAlmostEqual(with_cost["annualised_one_way_turnover"],
                                       zero_cost["annualised_one_way_turnover"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
