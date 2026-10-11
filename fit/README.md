# Fitting scripts for `MODELS.fitted`

These scripts produce the tables embedded in `index.html` as `MODELS.fitted`. Each one
replaces a number that used to be set by hand. Raw data is not committed. Fetch it with
the commands below, then run the scripts with `python3 -I`. They need pandas, openpyxl
and pyreadr. Paths inside the scripts point at `/tmp/claude-0/...`; edit them to match
your machine.

| Table | Script | Data | Fetch |
|---|---|---|---|
| `sba_rate` FY2023 table (*superseded by `sba_risk_refresh.py`, next row*) | `sba_rate.py` | SBA FOIA 7(a) loans, FY2020 to 2023-09-30, change-of-ownership loans | `curl -LO https://raw.githubusercontent.com/CSISdefense/Vendor/HEAD/Data_Raw/Assistance/SBA/foia-7afy2020-present-asof-230930.csv` |
| `sba_rate` (Fed H.15 prime 7.00% since 2026-09-17 + the median spread of FY2025–26 variable-rate change-of-ownership loans, measured over the prime on the first business day of the approval month as 13 CFR 120.214(c) sets it; knots $100k–$4.5M with `spread_knots_se`; stored in `sba_rate_fy2025_26.json`, which `build_models.py` reads) and `MODELS.risk` (embedded in `index.html` outside `MODELS.fitted`: competing-risk charge-off / payoff hazards with clustered SEs, out-of-time shrink `co.lp_shrink`, level shift and `base_cif`, sector / 6-digit / state effects, 10-year `tail_factor` (a labelled judgment), mean LGD by loan age; read by `fitRisk`) | `sba_risk_refresh.py` (writes `fits.json`, tables, a patched copy of the page and `RESULT.json` to `/tmp/claude-0/fit5/sba_risk_refresh/`; the repo page is read, never written; the test fixture `tests/sba_book_fy2024_26.json` comes from the same run) | SBA 7(a) FOIA as of 2026-06-30 (FY2000–09, FY2010–19, FY2020–present files): 41,200 change-of-ownership term loans approved FY2018–26 for the hazards, all 7(a) term loans for the 10-year tail and the through-the-cycle and like-for-like rates; Fed H.15 bank prime (RIFSPBLP_N.B), daily to 2026-10-02. The script reads cleaned extracts (`sba7a_chow_loans_fy2018_2026.csv`, `prime_rate_daily_h15.csv`) built from those files; the columns used are listed in its header | `curl -LO https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2020_Present_asof_260630.csv` (likewise `FOIA_7a_FY2010_FY2019_asof_260630.csv` and `FOIA_7a_FY2000_FY2009_asof_260630.csv`; dataset page data.sba.gov/dataset/7a-504-foia); prime from `https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip` |
| `jobs` (receipts and payroll per employee) | `build_models.py` | Census SUSB 2022, US 6-digit NAICS by receipts size (`us_6digitnaics_rcptsize_2022.xlsx`) | census.gov/programs-surveys/susb |
| `gm_wage` (general-manager wage percentiles, June 2026 $; sets `by_industry` p10–p90 with `se_sampling`/`se_total`, `wage_growth`, `wage_growth_se`, `noise`; no top-code) | `oews_refresh.py` (with `--write-repo` it writes `gm_wage.json`, which `build_models.py` reads; supersedes `oews.py`) | BLS OEWS May 2021, 2023, 2024, 2025, SOC 11-1021, national by industry; BLS ECI `ci.data.0.Current` (series CIU2020000110000I, management, business and financial W&S) | `curl -A 'your-project/1.0 (contact)' -H 'Accept: */*' -H 'Accept-Language: en-US' -H 'Accept-Encoding: gzip, deflate, br' -O https://www.bls.gov/oes/special-requests/oesm25in4.zip` (likewise `oesm21/23/24in4.zip` and `oesm2Xnat.zip`; the ECI from `download.bls.gov/pub/time.series/ci/`; BLS answers 403 without a descriptive User-Agent and these headers) |
| `sde_margin` (typical SDE margin by industry and size) | `dl_panel.py`, `hedonic.py`, `margin.py` | DealLedger broker-direct listings, CC0 | `git clone --depth 1 https://github.com/jeffsosville/dealledger` |
| `quality_weights` (owner dependence, management depth) | `hed_fit.py`, `quality_weights.py` | same listings, those with descriptions; phrase effects converted to per-sd weights with a threshold model, shrunk toward 1 with a N(1, 0.5²) prior | as above |
| `buyer_mix` (individual / strategic / financial by deal size) | `ibba_buyer_mix.py`; band knots built in `build_models.py` (`buyer_mix_fit.py` is the parametric check) | IBBA / M&A Source Market Pulse reports, 2012–2023; values transcribed in `ibba_buyer_mix.csv` | ibba.org |
| `ttc_shape` (time-to-close curve shape: log-logistic β, two levels, under $500K and $500K up; also the histograms' own grouped medians, shown in the Data tab) | `time_to_close_shape.py` (writes the patched page and checks to `/tmp/claude-0/fit5/time_to_close_shape/`; the repo page is read, never written) | IBBA / M&A Source Market Pulse full reports, 15 quarters (2020Q1–2023Q3 and 2025Q4), per-band histograms of months listing → close and LOI → close, 4,533 closed deals (`aggregates_research/clean/ibba_mp_band_histograms_long.csv`; the script recodes three mis-parsed <$500K charts: 2020Q3, 2022Q2, 2022Q4) | ibba.org Market Pulse reports (full PDF editions; the 2023Q4 band charts are images and were not used) |

The app's old May-2021 GM wage table came from `cran/oews2021`, a third-party CRAN repackaging (Sep 2022).
`oews_refresh.py` reads the official BLS `oesm21in4.zip` (sha256 61d1eb0a77e8be52...) and checks the mirror
against it: identical on all 413 rows. The firm-size rank used to read the wage distribution and the
e-commerce bridge (NAICS 2022 has no e-commerce row) are labelled judgment; OEWS publishes no wages by firm
size. Follow-up: an ECEC-based employer-cost loading (benefits, payroll taxes) for the hire-a-GM cost.

The prime rate (7.00%, in effect since 2026-09-17, Fed H.15) is read by `sba_risk_refresh.py` from the H.15
series and stored with the spread table in `sba_rate_fy2025_26.json`. Update it when it changes: the survival
risk reads only the spread over prime, so a new prime moves the table rate, not the risk at the table rate.

**Tried and not usable:**
- The listing panel's time-on-market. The median listing appears in one snapshot, and only
  164 sales were observed. (The curve's shape by size band is now fitted from IBBA's histograms instead.)
- Anchoring of sale price on ask. No reachable dataset has both prices for small private
  deals.
