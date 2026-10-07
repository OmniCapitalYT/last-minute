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
| `gm_wage` (general-manager wage percentiles) | `oews.py` | BLS OEWS May 2021, SOC 11-1021 | `git clone --depth 1 https://github.com/cran/oews2021` |
| `sde_margin` (typical SDE margin by industry and size) | `dl_panel.py`, `hedonic.py`, `margin.py` | DealLedger broker-direct listings, CC0 | `git clone --depth 1 https://github.com/jeffsosville/dealledger` |
| `quality_weights` (owner dependence, management depth) | `hed_fit.py`, `quality_weights.py` | same listings, those with descriptions; phrase effects converted to per-sd weights with a threshold model, shrunk toward 1 with a N(1, 0.5²) prior | as above |
| `buyer_mix` (individual / strategic / financial by deal size) | `ibba_buyer_mix.py`; band knots built in `build_models.py` (`buyer_mix_fit.py` is the parametric check) | IBBA / M&A Source Market Pulse reports, 2012–2023; values transcribed in `ibba_buyer_mix.csv` | ibba.org |

The prime rate (6.75%, in effect since 2025-12-11) is entered by hand in `build_models.py`.
Update it when it changes.

**Tried and not usable:**
- The listing panel's time-on-market. The median listing appears in one snapshot, and only
  164 sales were observed.
- Anchoring of sale price on ask. No reachable dataset has both prices for small private
  deals.
