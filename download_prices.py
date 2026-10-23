"""Download the fixed ETF universe/date range from the public chart endpoint.

Provider histories can be revised. This does not promise the exact published
snapshot; use the original snapshot hashes to distinguish a new data vintage.
Never silently overwrite the supplied research snapshot.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import argparse
import datetime as dt
import hashlib
import json

import pandas as pd

ROOT = Path(__file__).resolve().parent
TICKERS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def download(ticker):
    start = int(dt.datetime(2004, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    end = int(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={start}&period2={end}&interval=1d&events=div%2Csplits&includeAdjustedClose=true")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=40) as response:
        raw = response.read()
    result = json.loads(raw)["chart"]["result"][0]
    dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(
        "America/New_York").tz_localize(None).normalize()
    series = pd.Series(result["indicators"]["adjclose"][0]["adjclose"], index=dates, name=ticker)
    metadata = {"ticker": ticker, "url": url, "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    return series, raw, metadata


def main(output):
    if (output / "adjusted_prices.csv").exists():
        raise FileExistsError("Price file already exists. Choose a new --output folder to preserve it.")
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(download, TICKERS))
    prices = pd.concat([row[0] for row in rows], axis=1).sort_index()
    if prices.index.has_duplicates or prices.isna().any().any() or (prices <= 0).any().any():
        raise ValueError("Downloaded history failed structural checks; no filling is applied.")
    prices.index.name = "date"
    (output / "raw").mkdir(parents=True, exist_ok=True)
    for ticker, (_, raw, _) in zip(TICKERS, rows):
        (output / "raw" / (ticker + ".json")).write_bytes(raw)
    prices.to_csv(output / "adjusted_prices.csv")
    (output / "download_metadata.json").write_text(json.dumps([row[2] for row in rows], indent=2))
    print("Downloaded", len(prices), "price dates to", output)
    print("This is a new provider snapshot: rerun the data review before making final claims.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "research/data")
    main(parser.parse_args().output)
