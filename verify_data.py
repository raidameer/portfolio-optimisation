"""Reproduce selected issuer cross-checks without calculating strategy performance.

Optional audit tool, separate from the main backtest. Requires openpyxl to read
issuer spreadsheets. Raw issuer files are cached locally and excluded from Git.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import argparse
import datetime
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
TICKERS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
BASE_URL = "https://www.ssga.com/library-content/products/fund-data/etfs/us/"
SPLIT_TICKERS = ["XLB", "XLE", "XLK", "XLU", "XLY"]
SPECIAL_DATE = pd.Timestamp("2016-09-19")
CLOSED_DATES = pd.DatetimeIndex(["2012-10-29", "2012-10-30", "2014-04-18"])


def get_source(name, cache):
    path = cache / name
    if not path.exists():
        request = Request(BASE_URL + name, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            path.write_bytes(response.read())
    return {"name": name, "url": BASE_URL + name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def read_nav(path):
    table = pd.read_excel(path, header=3).iloc[:, :2]
    table.columns = ["date", "nav"]
    table["date"] = pd.to_datetime(table["date"], format="%d-%b-%Y", errors="coerce")
    return table.dropna(subset=["date"]).set_index("date")["nav"].sort_index().astype(float)


def review(cache):
    cache.mkdir(parents=True, exist_ok=True)
    names = [f"navhist-us-en-{ticker.lower()}.xlsx" for ticker in TICKERS + ["XLRE"]]
    names.append("spdr-etf-historical-distributions.xlsx")
    with ThreadPoolExecutor(max_workers=3) as pool:
        sources = list(pool.map(lambda name: get_source(name, cache), names))
    price_file = ROOT / "research/data/adjusted_prices.csv"
    prices = pd.read_csv(price_file, index_col="date", parse_dates=["date"])
    returns = prices.pct_change(fill_method=None).dropna()
    navs = {ticker: read_nav(cache / f"navhist-us-en-{ticker.lower()}.xlsx")
            for ticker in TICKERS + ["XLRE"]}
    distributions = pd.read_excel(cache / "spdr-etf-historical-distributions.xlsx")
    distributions["EX-DATE"] = pd.to_datetime(distributions["EX-DATE"], format="%m/%d/%Y", errors="coerce")
    original_sources = json.loads((ROOT / "reference/source_data_audit.json").read_text())
    for item in original_sources["tickers"]:
        raw_file = ROOT / "research/data/raw" / (item["ticker"] + ".json")
        if hashlib.sha256(raw_file.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Original raw source hash has changed.")
    calendar_checks = []
    for ticker in TICKERS:
        nav_dates = navs[ticker].loc["2004-01-02":"2025-12-31"].index
        unexplained_missing = nav_dates.difference(prices.index).difference(CLOSED_DATES)
        extra_dates = prices.index.difference(nav_dates)
        if len(unexplained_missing) or len(extra_dates):
            raise ValueError(f"Unexplained date differences for {ticker}.")
        calendar_checks.append({"ticker": ticker, "price_dates": len(prices),
                                "issuer_nav_only_closed_dates": [str(d.date()) for d in nav_dates.difference(prices.index)],
                                "unexplained_missing": 0, "unexplained_extra": 0})
        raw = json.loads((ROOT / "research/data/raw" / (ticker + ".json")).read_text())["chart"]["result"][0]
        np.testing.assert_allclose(raw["indicators"]["adjclose"][0]["adjclose"], prices[ticker], rtol=1e-14)

    # The issuer labels the special entry as a dividend but its numeric amount
    # is an XLRE SHARE RATIO, not dollars of cash. Value those shares explicitly.
    special = distributions[(distributions["TICKER"] == "XLF") &
                            (distributions["EX-DATE"] == SPECIAL_DATE)]
    ratio = float(special["DIVIDEND ($)"].iloc[0])
    if not np.isclose(ratio, 0.139146, atol=1e-9):
        raise ValueError("Unexpected XLF special distribution ratio.")
    special_value = ratio * navs["XLRE"].loc[SPECIAL_DATE]
    xlf_nav_return = (navs["XLF"].loc[SPECIAL_DATE] + special_value) / navs["XLF"].loc["2016-09-16"] - 1
    xlf_provider_return = returns.loc[SPECIAL_DATE, "XLF"]
    xle_nav_return = navs["XLE"].loc["2020-03-09"] / navs["XLE"].loc["2020-03-06"] - 1
    xle_provider_return = returns.loc["2020-03-09", "XLE"]

    # These corroborate direction/magnitude across NAV and traded-price series;
    # they do not assume NAV equals the exchange closing price.
    event_checks = {
        "xlf_2016_special": {"xlre_shares_per_xlf": ratio,
                             "same_day_issuer_nav_total_return": float(xlf_nav_return),
                             "provider_adjusted_return": float(xlf_provider_return),
                             "difference_basis_points": float(10000 * (xlf_provider_return - xlf_nav_return))},
        "xle_2020_03_09": {"issuer_nav_return": float(xle_nav_return),
                            "provider_adjusted_return": float(xle_provider_return),
                            "difference_basis_points": float(10000 * (xle_provider_return - xle_nav_return))},
    }
    # Independently announced five genuine 2:1 share splits. No manual split
    # adjustment is applied to the already adjusted provider price series.
    split_checks = []
    for ticker in SPLIT_TICKERS:
        issuer_return = 2 * navs[ticker].loc["2025-12-05"] / navs[ticker].loc["2025-12-04"] - 1
        split_checks.append({"ticker": ticker, "date": "2025-12-05", "ratio": 2,
                             "issuer_nav_return": float(issuer_return),
                             "provider_adjusted_return": float(returns.loc["2025-12-05", ticker])})

    cash_checks = []
    for ticker in ["XLF", "XLE", "XLK"]:
        raw = json.loads((ROOT / "research/data/raw" / (ticker + ".json")).read_text())["chart"]["result"][0]
        for date in ["2019-12-20", "2023-12-18", "2025-12-22"]:
            issuer_row = distributions[(distributions["TICKER"] == ticker) &
                                       (distributions["EX-DATE"] == date)]
            issuer_cash = float(issuer_row["DIVIDEND ($)"].iloc[0])
            match = [entry for entry in raw["events"]["dividends"].values()
                     if str(pd.to_datetime(entry["date"], unit="s", utc=True)
                            .tz_convert("America/New_York").date()) == date][0]
            # Provider distributions before Dec 2025 are split-normalised.
            scale = 2 if ticker in SPLIT_TICKERS and date < "2025-12-05" else 1
            provider_cash = match["amount"] * scale
            cash_checks.append({"ticker": ticker, "date": date,
                                "issuer_cash": issuer_cash, "provider_same_share_basis_cash": provider_cash,
                                "absolute_difference_dollars": abs(issuer_cash - provider_cash)})

    # Quantify the original annual-return discrepancy without forcing equality.
    xlf_nav = navs["XLF"]
    cash_rows = distributions[distributions["TICKER"] == "XLF"].copy()
    cash_rows["cash"] = cash_rows[["DIVIDEND ($)", "SHORT TERM CAPITAL GAIN ($)",
                                    "LONG TERM CAPITAL GAIN ($)"]].fillna(0).sum(axis=1)
    cash_rows.loc[cash_rows["EX-DATE"] == SPECIAL_DATE, "cash"] = special_value
    cash = cash_rows.groupby("EX-DATE")["cash"].sum().reindex(xlf_nav.index, fill_value=0)
    nav_total_return = (xlf_nav + cash) / xlf_nav.shift() - 1
    xlf_annual = {"year": 2016,
                  "provider_price_proxy": float((1 + returns.loc["2016", "XLF"]).prod() - 1),
                  "issuer_nav_ex_date_reinvestment_reconstruction": float((1 + nav_total_return.loc["2016"]).prod() - 1),
                  "issuer_prospectus_return": 0.2269,
                  "interpretation": "Different price and reinvestment conventions; not exact independent market-close replication."}
    result = {
        "status": "reviewed_with_limitations", "date": "2026-10-22",
        "prices_sha256": hashlib.sha256(price_file.read_bytes()).hexdigest(),
        "source_files": sources, "calendar_checks": calendar_checks,
        "event_checks": event_checks, "split_checks": split_checks,
        "ordinary_distribution_checks": cash_checks, "xlf_2016_annual_comparison": xlf_annual,
        "decision": "Retain the original provider adjusted-close proxy unchanged. Selected independent checks corroborate events and calendar; carry provider/convention limitations into the research findings.",
        "limits": ["Not an independent replication of every daily exchange closing price.",
                   "XLF spin-off uses a provider split-style proxy for reinvestment; no extra distribution is added.",
                   "Issuer NAV returns and market-close adjusted returns differ, especially during stress.",
                   "The issuer and reconstructed XLF annual returns do not match exactly; no claim of exact reconciliation is made.",
                   "Cash-distribution values are not identical across providers; rounding/convention differences remain."]}
    output = ROOT / "reference/independent_data_review.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Selected issuer checks completed; data-source limitations documented.")
    print(json.dumps(event_checks, indent=2))
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "research/issuer_cache")
    args = parser.parse_args()
    review(args.cache)
