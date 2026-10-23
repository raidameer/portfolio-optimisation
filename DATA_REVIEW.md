# Data review - selected independent checks completed

Reviewed 22 October 2026, before opening real final-evaluation strategy outcomes.
The original adjusted-price snapshot is retained unchanged. This is an
exploratory provider-price-proxy study with documented limitations, not a
certification of every historical market closing price.

## Structural checks and provenance

- 5,535 common positive price dates per ETF, 2 January 2004 to 31 December 2025.
- No missing/nonfinite/nonpositive prices, duplicate dates or silent filling.
- All nine original raw-response SHA256 hashes match the download metadata.
- All 49,815 exported adjusted prices reconcile to the original raw responses.
- Original snapshot hash remains unchanged from CODE_FREEZE.json.

## Independent date coverage

Issuer historical NAV files for all nine funds cover every date in the study.
Each contains three additional dates: 29 and 30 October 2012 and 18 April 2014.
The first two were exchange closures for Hurricane Sandy; the third was Good
Friday. Exchange notices confirm these were non-trading days. Excluding those
issuer valuation dates leaves no unexplained differences. We retain the
market-price calendar and add no observations.

Sources:
- https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2012-44
- https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2012-45
- https://www.nyse.com/publicdocs/nyse/markets/american-options/rule-interpretations/2014/NYSEAmex%20RBO-14-04%20Good%20Friday%20%20EED%20Processing.pdf

This is an independent issuer-date cross-check with exchange confirmation of
exceptions, not an independently rebuilt exchange calendar for every day.

## XLF special distribution: checked, with an approximation retained

In September 2016, XLF distributed 0.139146 XLRE shares for each XLF share.
This was a distribution of another fund's shares, not a genuine XLF share split.
The issuer distribution spreadsheet labels the numeric field as dollars, but
this entry is a SHARE RATIO. Treating 0.139146 as dollars would be wrong.

The provider uses a split-style 1231:1000 adjustment to represent reinvestment.
Its pre-event close values already reflect that treatment. Adding the special
distribution again would double-count it. No extra adjustment is applied to
the provider series in the main backtest.

Independent issuer NAV values give this event-day cross-check:

    (XLF NAV on 19 September + 0.139146 * XLRE NAV on 19 September)
    / XLF NAV on 16 September - 1

This gives +0.58271%, versus +0.63761% in the provider adjusted market-price
series: a 5.49 bp difference. It corroborates that the large distribution is
accounted for; it does not establish exact equivalence between NAV, traded
prices and the provider's reinvestment approximation.

For 2016, the provider proxy returns 22.41518%. An issuer NAV/ex-date-distribution
reconstruction returns approximately 22.65879%, while the issuer prospectus
reports 22.69%. These use different prices and/or reinvestment conventions.
The approximately 0.275 percentage-point provider/prospectus difference is
retained as a limitation, not forced to zero or called an exact reconciliation.
All research returns remain conditional on the provider adjusted-close proxy.

Event sources:
- https://www.sec.gov/Archives/edgar/data/1064641/000119312516699787/d246445d497.htm
- https://new.streetinsider.com/Press%2BReleases/State%2BStreet%2BGlobal%2BAdvisors%2BAnnounces%2BDividend%2BDistributions%2BResulting%2BFrom%2BModifications%2Bto%2BThe%2BFinancial%2BSelect%2BSector%2BSPDR%C2%AE%2BFund/12049060.html
- https://www.ssga.com/ch/fr/institutional/library-content/products/fund-docs/etfs/emea/us-etf/xlc-prospectus.pdf

## XLE extreme return: independently corroborated

The flagged 9 March 2020 adjusted market-price return is -20.14118%.
Issuer NAV changes from 42.496283 on 6 March to 33.917774 on 9 March,
giving -20.18649%. The difference is 4.53 bp. The magnitude/direction are
independently corroborated; the observation is retained. NAV and traded-price
returns are different measurements, so equality is not required or claimed.

## Ordinary distributions and genuine share splits

Nine ordinary-distribution entries were checked: XLF, XLE and XLK on
20 December 2019, 18 December 2023 and 22 December 2025. Pre-split provider
amounts were brought onto the issuer's original share basis. The selected
amounts agree to within $0.0005 per original share; differences remain recorded.

An issuer announcement independently confirms 2:1 splits for XLB, XLE, XLK,
XLU and XLY, effective for trading on 5 December 2025. The adjusted series
contains normal daily movements rather than artificial 50% losses. Split-
corrected issuer NAV returns corroborate the direction/magnitude of treatment.

https://investors.statestreet.com/investor-news-events/press-releases/news-details/2025/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs/default.aspx

## Sector coverage

Tickers remain constant, but holdings and classifications change. The 2016
real-estate separation and 2018 communication-services reclassification mean
these are nine long-history sector ETFs, not nine unchanging sectors or every
modern sector throughout the study.

https://www.msci.com/documents/1296102/11185224/GICS%2BSector%2Bdefinitions%2BSept%2B2018.pdf/afc87e7b-bbfe-c492-82af-69400ee19e4f

## Reproduction and remaining limits

verify_data.py reproduces the selected checks without strategy calculations.
Install requirements-audit.txt only if rerunning this optional audit. It caches
issuer workbooks in research/issuer_cache, excluded from Git. The main backtest
needs only requirements.txt.

Source URLs, hashes, checked timestamps and computed comparisons appear in
reference/independent_data_review.json. Issuer workbooks are not redistributed
in the source package. They are available at:

- https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-xlf.xlsx
- The same navhist-us-en-TICKER.xlsx pattern for the other funds and XLRE.
- https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx

The selected checks support proceeding with the frozen exploratory study.
They do not independently validate every daily exchange price, remove NAV/
market-price differences, establish exact reinvestment conventions or eliminate
later provider revisions. These limitations must accompany the findings.
