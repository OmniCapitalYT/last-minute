# Fitting scripts for `MODELS.fitted`

These scripts produce the tables embedded in `index.html` as `MODELS.fitted`. Each one
replaces a number that used to be set by hand. Raw data is not committed. Fetch it with
the commands below, then run the scripts with `python3 -I`. They need pandas, openpyxl
and pyreadr. Paths inside the scripts point at `/tmp/claude-0/...`; edit them to match
your machine.

| Table | Script | Data | Fetch |
|---|---|---|---|
| `sba_rate` (spread over prime by loan size) | `sba_rate.py` | SBA FOIA 7(a) loans, FY2020 to 2023-09-30, change-of-ownership loans | `curl -LO https://raw.githubusercontent.com/CSISdefense/Vendor/HEAD/Data_Raw/Assistance/SBA/foia-7afy2020-present-asof-230930.csv` |
| `jobs` (receipts and payroll per employee) | `build_models.py` | Census SUSB 2022, US 6-digit NAICS by receipts size (`us_6digitnaics_rcptsize_2022.xlsx`) | census.gov/programs-surveys/susb |
| `gm_wage` (general-manager wage percentiles, June 2026 $; sets `by_industry` p10–p90 with `se_sampling`/`se_total`, `wage_growth`, `wage_growth_se`, `noise`; no top-code) | `oews_refresh.py` (with `--write-repo` it writes `gm_wage.json`, which `build_models.py` reads; supersedes `oews.py`) | BLS OEWS May 2021, 2023, 2024, 2025, SOC 11-1021, national by industry; BLS ECI `ci.data.0.Current` (series CIU2020000110000I, management, business and financial W&S) | `curl -A 'your-project/1.0 (contact)' -H 'Accept: */*' -H 'Accept-Language: en-US' -H 'Accept-Encoding: gzip, deflate, br' -O https://www.bls.gov/oes/special-requests/oesm25in4.zip` (likewise `oesm21/23/24in4.zip` and `oesm2Xnat.zip`; the ECI from `download.bls.gov/pub/time.series/ci/`; BLS answers 403 without a descriptive User-Agent and these headers) |
| `sde_margin` (typical SDE margin by industry and size) | `dl_panel.py`, `hedonic.py`, `margin.py` | DealLedger broker-direct listings, CC0 | `git clone --depth 1 https://github.com/jeffsosville/dealledger` |
| `quality_weights` (owner dependence, management depth) | `hed_fit.py`, `quality_weights.py` | same listings, those with descriptions; phrase effects converted to per-sd weights with a threshold model, shrunk toward 1 with a N(1, 0.5²) prior | as above |
| `buyer_mix` (individual / strategic / financial by deal size) | `ibba_buyer_mix.py`; band knots built in `build_models.py` (`buyer_mix_fit.py` is the parametric check) | IBBA / M&A Source Market Pulse reports, 2012–2023; values transcribed in `ibba_buyer_mix.csv` | ibba.org |

The app's old May-2021 GM wage table came from `cran/oews2021`, a third-party CRAN repackaging (Sep 2022).
`oews_refresh.py` reads the official BLS `oesm21in4.zip` (sha256 61d1eb0a77e8be52...) and checks the mirror
against it: identical on all 413 rows. The firm-size rank used to read the wage distribution and the
e-commerce bridge (NAICS 2022 has no e-commerce row) are labelled judgment; OEWS publishes no wages by firm
size. Follow-up: an ECEC-based employer-cost loading (benefits, payroll taxes) for the hire-a-GM cost.

The prime rate (6.75%, in effect since 2025-12-11) is entered by hand in `build_models.py`.
Update it when it changes.

**Tried and not usable:**
- The listing panel's time-on-market. The median listing appears in one snapshot, and only
  164 sales were observed.
- Anchoring of sale price on ask. No reachable dataset has both prices for small private
  deals.
