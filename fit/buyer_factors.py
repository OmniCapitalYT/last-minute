#!/usr/bin/env python3
"""Buyer factors (MODELS.fitted.buyers), revision 3: the individual owner-operator's multiple factor (calibrated), and
the evidence on the search fund's presence by deal size (measured, NOT adopted: the hand-set window stays), what the
measured curve would do to the typical pool and to ENG_SHARE, and benchmark checks on PHI, the synergy pool and the
search-fund multiple factor. October 2026.

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/buyer_factors.py            (10-20 min; needs node and pdftotext)
      python3 -I .../buyer_factors.py --quick   (smoke test: small bootstraps, everything in the scratch directory)
Out:  /tmp/claude-0/fit6/out/buyer_factors/RESULT.json (js_table = MODELS.fitted.buyers), js_table.json, tables *.csv
      and the node probe it ran (probe.js, probe_cfg_*.json). Scratch: /tmp/claude-0/fit6/work/fit3-buyer_factors/
      (patched copies of the snapshot page in pages/, the copied fit/competition_buyers.py with its harness wrappers and
      outputs in competition_buyers/, the repo tests' scratch copies in testrun/). Nothing in the repo or the snapshot is
      written; the snapshot is only read. Round 1 is kept as buyer_factors.v1.py and out/buyer_factors.v1/, revision 2
      as buyer_factors.v2.py and out/buyer_factors.v2/ (its scratch in work/fit2-buyer_factors/).

Revision 3 (the analyst's decisions on the round-2 review)
  - The measured search-fund presence curve is NOT adopted. Its effect on the ENG_SHARE calibration depends on how it
    is built (+.23 to +.69 se over the knot-table constructions; +.73 se read in 2026 dollars), it fits IBBA's offers per
    closed deal by band worse than the trapezoid (chi2 3.4 -> 5.1, the size-gradient LR p .086 -> .044), and with the
    refit it breaks the repo's 2M-5M calibration pin. The window stays judgment at [$0.6M, $3.2M] (the trapezoid with
    its linear tails), ENG_SHARE stays 0.184 and MODELS.fitted.competition is unchanged (only its strategic_premium.status
    text changes, because ind's mf is now calibrated). The evidence is recorded in js_table.eta_check: the measured half
    presence, the trapezoid's half-presence points, the ENG_SHARE shift by construction, the IBBA fit comparison and the
    dollar-basis and step-function caveats. No MODELS.fitted.competition update ships (round 2's competition_update is
    dropped).
  - mf_ind ships 0.97 CALIBRATED, re-solved on the snapshot page as shipped (the trapezoid, ENG_SHARE 0.184). Its se is
    labelled sampling only (the IBBA band-quarter bootstrap); the specification range (.959-.990) and the per-size
    solutions (.918-.978) are stored beside it.
  - Texts: the corrected code comment (Stanford 2026 median EBITDA $2.0M, Stanford 2024 $1.9M; the window contains
    both), the BUYERS header, the Data-tab sentence, and the strategic_premium.status string.

What ships (js_table, key "buyers") and why
  - mf_ind = 0.97 (was 0.90), CALIBRATED, not fitted. Model value is BIZCOMPS's calibrated closed-sale value; with the
    shipped factors the buyer-type-weighted price sits about 5% (log) below the value it multiplies. The adding-up
    identity solves for mf_ind with everything else as shipped (raw 0.969; se 0.003 from the IBBA-mix bootstrap,
    sampling only; specification range 0.959-0.990; per-size solutions 0.918-0.978 over SDE $35k-$728k; the research
    round's 0.968 is reproduced on its own grid). Caveats, stored with it: it calibrates ONE degree of freedom given the
    other seven mf, PHI and syn (all judgment); it treats IBBA's buyer-type mix at the deal value as BIZCOMPS's buyer
    composition (untested: neither source has the other's field); re-solve whenever another mf, syn, PHI, the synergy
    pool or buyerMix changes; one constant cannot balance every size.
  - eta_check (evidence, nothing ships): the search fund's presence by deal size measured as a knot table ln(SDE) ->
    presence (w = 0.9 x self-funded searchers' EBITDA targets, SIG 2023 Fig 7, + 0.1 x traditional funds' acquired
    EBITDA, Stanford 2026, each mapped to SDE with sdeEbitdaWedge), its half presence ($0.79M-$3.47M) against the
    shipped trapezoid's ($0.345M-$5.76M), what it would do to the typical pool and to ENG_SHARE under each construction,
    how it fits IBBA's offers by band, and two caveats: the dollar basis (SIG's 2023 targets and Stanford's all-years
    median read as 2026 dollars; in 2026 dollars the low knots fall sharply) and the step function (five knots sit on
    SIG bin edges mapped to SDE, so they read the step at a step; the bootstrap SEs do not cover where the edges fall).
  - eta_mf_check, phi_check, pool_check: checks only; eta mf .98, PHI .38 and the synergy pool stay judgment. The pool's
    level (strat x (.050 + .028 gm + .015) of revenue) is conditional on IND.strat, which is judgment, so the BCG match
    cannot move it to Aggregate. The evidence is in RESULT.json's not_shipped block.
  - comment_fix and strategic_premium_status: the code comment claimed the window matched "the Stanford 2024 study's
    median deal ($1.6M of EBITDA)". Stanford 2024's median is $1.9M and Stanford 2026's $2.0M ($1.6M appears in Stanford
    2026's Exhibit 4 only as the minimum, -$1.6M). The window, full presence from $0.6M to $3.2M of SDE, contains both.

What it does
  0. Sources: sha256 of every input. Every number transcribed from a PDF is a documented constant below, and step 0
     checks it against that page's own text layer (pdftotext -layout, the system poppler tool, run on the file;
     nothing from a download is executed or imported). Fig 23 of SIG is a grouped bar chart: its 16 labels are
     assigned to groups by their x position in the text layer, and the check repeats that assignment.
  1. mf_ind, the adding-up identity (as round 1). The value model is fitted to ln(BIZCOMPS price) and calibrated so its
     median log residual is 0 in every size bin. If buyer type g pays Vj/V times model value and the residual shape is
     common to the types, sum_g s_g(V) * mean_{j in g} ln(Vj/V) = 0. s_g is IBBA's fitted buyer-type mix at the deal
     value (buyerMix; groups as BUYER_GROUP: individual = ind; strategic = str, adj; financial = pep, add, fo; eta and
     mbo are in no IBBA group, so the eta window does not enter the central identity). Vj/V = 1 + (mf-1)*sizeFit +
     min(PHI*syn*(synE/SDE)*sizeFit, 0.40), read from the console (node, the harness, median-quality businesses of all
     16 industries on a 161-point grid in ln SDE) and checked to 1e-12 against the model's own Vj. Weighted over the
     BIZCOMPS SDE distribution (MODELS.value.support, CDF linear in ln SDE through p0.5 ... p99.5) up to its p95 ($728k)
     and solved exactly (brentq) on the snapshot page as shipped (the search fund's trapezoid, ENG_SHARE 0.184). SE:
     bootstrap over IBBA's complete band-quarters (B = 2000), labelled SAMPLING ONLY. Specification range: the other
     archetypes' factors, PHI at the BCG ends, the pool at BCG's level, IBBA's strategic share +-25%, MBOs inside
     BIZCOMPS, the estimator (full support, p99, the research's per-size average, engagement-weighted groups, BIZCOMPS
     sector weights, searchers counted as IBBA individuals under the shipped trapezoid; the same under the measured knot
     table is recorded beside the range, not in it). Per-size solutions over BIZCOMPS p5-p95 are stored beside the
     range. The shipped 0.97 is checked through the patched model itself.
  2. eta presence, measured (evidence only: not adopted). Presence by size (what sizeFit stands for: the group's
     presence relative to its maximum) is the mixture w * self-funded + (1-w) * traditional, w = 0.9 (judgment:
     traditional funds close about 25-35 deals a year in the US and Canada, self-funded searchers several times as
     many):
     - self-funded: SIG Fig 7, the share of 279 searchers whose EBITDA target includes each bin, a step function
       normalised to its peak (the open '<$500k' bin held from $250k and ramped to 0 at $100k: judgment);
     - traditional: Stanford 2026's acquired EBITDA, lognormal with the published median $2.0M; its log-sd from the
       price bins (binned MLE) through sigma_P^2 = (1+b)^2 sigma_E^2 + s^2, b and s from a joint binned MLE on SIG
       Fig 23 x Fig 21;
     - EBITDA -> SDE with the console's sdeEbitdaWedge (all-sector level) at revenue = EBITDA / margin (self-funded:
       SIG's revenue and EBITDA lognormal medians; traditional: Stanford 2026's median margin 23%), checked against the
       harness.
     Knots: the curve at the research round's 15 SDE points, ln SDE to 4 decimals, presence to 3. The research file is
     reproduced exactly with its own construction (coarser grids, a 25% traditional margin); the shipped table uses finer
     grids and Stanford 2026's 23% and differs from it by at most 0.015, at $5M, a knot on a SIG bin edge. SEs:
     bootstrap (B = 1000) over SIG Fig 7 (binomial per bin, n = 279), SIG Figs 20, 21 and 23 (multinomial, n = 109;
     the joint b, s refitted), Stanford 2026's price bins (multinomial, n = 318) and its median EBITDA; the same draws
     give the step curve's half-maximum crossings (round 1's numbers, reproduced), the knot table's own crossings and
     each knot's se. Like-for-like comparison with the shipped trapezoid, and the least-squares trapezoid with the
     code's ramps. Variants (knot tables): w = 0.8, the SIG shares interpolated between bin centres, a flat 1.2 wedge,
     presence read from where searchers BUY (SIG Fig 21's acquired-EBITDA lognormal in place of the target shares; the
     research round flagged that 30% of self-funded deals are under $500k of EBITDA while 14% of searchers target that
     range), and (revision 3) the dollar basis: the whole curve read in 2026 dollars (SIG's 2023 targets and Stanford's
     median scaled by CPI-U, Feb-Aug 2026 over the 2023 average). Step-function caveat (revision 3): the SIG bin edges
     and the end of the low ramp mapped to SDE, and each knot's distance to the nearest of them.
  3. What the knot table would do (evidence for the decision not to adopt it), through patched copies of the snapshot
     page (scratch): MODELS.fitted.buyers =
     {eta_presence:{knots}} after MODELS.fitted.competition; the eta row's lo/hi replaced by knots:...; one line added
     to sizeFit (b.knots ? clamp(lerpKnots(ln max(SDE,1e4), knots), 0, 1)). The model's eta sizeFit is checked against
     np.interp of the knots (1e-12) and the MBO's window is checked unchanged. Then: eta sizeFit and peRef for all 16
     industries on 50 SDE points $100k-$10M; ENG_SHARE re-run with the snapshot's fit/competition_buyers.py, copied and
     patched minimally (its harness path to a wrapper that loads the page under test; its probe's compPrem override and
     its peRef read brought up to the page as it now is: COMP_H for the literal 3 and ENG_SHARE for the literal 0.34; an
     early exit after the NB specification range, dumping the calibration as JSON). Run on the unpatched snapshot it
     must reproduce MODELS.fitted.competition (0.184, se 0.027, ci [0.13, 0.226], nb_r 1.07, the 9-specification range
     0.164-0.201, nb_r range 0.82-1.9, the PLN scale 0.21); on the knot page it gives the refit. A replica of its M5
     likelihood checks it and evaluates the variants. The analyst's rule (refit ENG_SHARE if the shift exceeds half its se)
     is evaluated and recorded as what adoption would require; nothing is refitted. Output effects (P_C, the competition
     premium and expected proceeds of median businesses at a typical and a half pool) at the shipped ENG_SHARE and at
     the refit; offers per closed deal by band against IBBA's band-free fits and the repo's calibration pins (within
     0.40 of IBBA's lower-bound means).
  4. eta mf check: SIG Fig 23 multiples by EBITDA bucket (binned lognormal, multinomial bootstrap) and Stanford / IESE
     median multiples against the console's model value at the same SDE (fitValue through the harness).
  5. PHI check: BCG/TUM 2013 (median 31% of the NPV of announced synergies, 12 industry medians) and BCG 2018 (10
     annual medians, mean 53.7%), DerSimonian-Laird random effects. Pool check: BCG/TUM 2013 Exhibit 1, median announced
     synergies 4.8% of target sales, against strat x (.050 + .028 gm + .015) over the 16 industries; nearest-industry
     mapping as the research; the gross-margin slope across BCG's industries with Damodaran's US gross margins.
  6. The page as it would ship (scratch): the snapshot plus MODELS.fitted.buyers = js_table (after
     MODELS.fitted.competition), ind's mf read from it, the corrected comments and Data-tab sentence, and the
     strategic_premium.status text; the eta row, sizeFit and every other MODELS.fitted.competition field unchanged.
     Checks: the identity balances through the model's own Vj at 0.97; eta's sizeFit is still the trapezoid and the
     MBO keeps its window; ENG_SHARE is 0.184; the typical pool reproduces the shipped offers per closed deal; and
     fit/competition_buyers.py's own invariant probe (EVp monotone in buyers contacted, thinF in (0,1], the typical
     pool independent of quality, a median business at a typical pool with no premium and thinF = 1) has no failures,
     as on the snapshot; the model source names neither the NB dispersion nor the PLN scale (the repo test's scan).
     The repo's own tests/model.test.js runs on scratch copies of the repo with the snapshot page (it must pass) and
     with the as-shipped page; the failures it reports are what integration must re-pin or decide (RESULT.json
     integration.repo_model_tests).

Data and fetch commands (downloads are untrusted: each in its own directory, read with python3 -I, never executed)
  Search Investment Group, 2023 Self-Funded Search Study (72 pp.; searchinvestgroup.com/study redirects to
     sigpartners.com, which answers 403; the full report is in SIG's public Google Drive folder, file id
     1Aq1XHtCNtVD0_Jkx8CAYyDF20YpPCERh: 'https://drive.google.com/uc?export=download&id=<id>', with Drive's
     confirm step for large files; the Wayback copy of the study page links only a 1-page teaser)
  Stanford GSB 2026 Search Fund Study: Selected Observations (E967), from
     https://www.gsb.stanford.edu/faculty-research/case-studies/2026-search-fund-study-selected-observations (the
     'download' button redirects through gsb-box to dl.boxcloud.com; save as stanford_2026_E967.pdf)
  IESE International Search Funds 2024 (ST-658-E): curl -L -o ST-0658-E.pdf https://iese.edu/media/research/pdfs/ST-0658-E
  BCG/TUM, Divide and Conquer (2013): https://web-assets.bcg.com/img-src/BCG_Divide_and_Conquer_Mar_2013_tcm9-62259.pdf
     (Akamai 403; read through the Wayback Machine: https://web.archive.org/web/2020id_/<that url>)
  BCG, Synergies Take Center Stage (2018 M&A Report):
     curl -LO http://boston-consulting-group-brightspot.s3.amazonaws.com/img-src/BCG-Synergies-Take-Center-Stage-Sep-2018_tcm9-202243.pdf
  Local (earlier rounds; revisions 2 and 3 download nothing new): Stanford 2024 study table (data5 aggregates_research/
     clean/stanford_2024_search_fund_stats.csv), IBBA offers histograms and average-offers panel, the 2025Q4 report text
     and the TRANBI applications table (the last three read by the copied competition_buyers.py), IBBA buyer-mix
     transcription (fit/ibba_buyer_mix.csv, read from the snapshot), Damodaran margin.xls (January 2026; git clone of a
     public mirror in /tmp/claude-0/dl), the research round's knot table (work/F-buyers/out/eta_knots.json, a check only),
     FRED CPIAUCNS (data/peer_gross_margin/fred_cpi_fx/CPIAUCNS.csv, another fit's download, sha256-pinned; the dollar-
     basis caveat only): curl -L -o CPIAUCNS.csv 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS'
"""
import hashlib, json, math, os, re, shutil, subprocess, sys
from collections import Counter
import numpy as np
import pandas as pd
from scipy import optimize, stats

QUICK = len(sys.argv) > 1 and sys.argv[1] == '--quick'       # smoke test: small bootstraps, scratch output
WORK = '/tmp/claude-0/fit6/work/fit3-buyer_factors'                # revision 3 (revision 2's scratch stays in fit2-buyer_factors)
OUT = WORK + '/quick' if QUICK else '/tmp/claude-0/fit6/out/buyer_factors'
SCR = WORK + '/quick' if QUICK else WORK                      # scratch: patched pages, the copied competition_buyers.py
PAGES = SCR + '/pages'
CB_DIR = SCR + '/competition_buyers'
for _d in (OUT, PAGES, CB_DIR):
    os.makedirs(_d, exist_ok=True)
SNAP_DIR = '/tmp/claude-0/fit6snap'
SNAP = SNAP_DIR + '/index.html'
HARNESS = '/tmp/claude-0/fit6/harness.js'
CB_SRC = '/tmp/claude-0/fit6snap/fit/competition_buyers.py'
CB_COPY = CB_DIR + '/competition_buyers.py'
DL = '/tmp/claude-0/fit6/data/F-buyers'
SIG_PDF = DL + '/sig_selffunded/SIG_2023_Self_Funded_Search_Study.pdf'
ST26_PDF = DL + '/stanford_2026/stanford_2026_E967.pdf'
IESE_PDF = DL + '/iese_2024/ST-0658-E.pdf'
BCG13_PDF = DL + '/bcg_divide_conquer_2013/BCG_Divide_and_Conquer_Mar_2013.pdf'
BCG18_PDF = DL + '/bcg_2018_synergies/BCG_2018_Synergies.pdf'
ST24_CSV = '/tmp/claude-0/data5/aggregates_research/clean/stanford_2024_search_fund_stats.csv'
IBBA_OFFERS = '/tmp/claude-0/data5/aggregates_research/clean/ibba_mp_band_histograms_long.csv'
IBBA_MIX = '/tmp/claude-0/fit6snap/fit/ibba_buyer_mix.csv'
DAMODARAN = '/tmp/claude-0/dl/dam_labelco-pilotes_data-damodaran/margin.xls'
RESEARCH_KNOTS = '/tmp/claude-0/fit6/work/F-buyers/out/eta_knots.json'
CPI = '/tmp/claude-0/fit6/data/peer_gross_margin/fred_cpi_fx/CPIAUCNS.csv'    # FRED CPIAUCNS (another fit's download): the dollar-basis caveat
CPI_SHA = 'f79e3a7883714229'
B_WIN, B_MIX, B_MF, CB_BOOT, N_INV = (20, 50, 50, 30, 60) if QUICK else (1000, 2000, 1000, 400, 400)
RNG_WIN = np.random.default_rng(20261014)
RNG_MIX = np.random.default_rng(20261015)
RNG_MF = np.random.default_rng(20261016)

# ------------------------------------------------------------------------------------------------------------------
# Transcribed numbers. PDF page = page index in the file (printed page in brackets). Each is checked in step 0.
# ------------------------------------------------------------------------------------------------------------------
# SIG 2023 Self-Funded Search Study (sha256 295d3011e4b84785...).
SIG_N_RESP = 279              # p.7 [p.7] "1,027 invitations were sent and 279 responses"
SIG_N_ACQ = 109               # p.35 "Of all 279 respondents, 109 had successfully" acquired
SIG_FIG7 = [14, 36, 54, 64, 50, 37, 26, 21, 17, 14]   # p.21 Fig 7: % whose EBITDA TARGET includes each bin (multiple answers)
SIG_FIG7_EDGES = [5e5, 7.5e5, 1e6, 1.5e6, 2e6, 2.5e6, 3e6, 4e6, 5e6]     # <$500k, $500-749k, ..., $4.0-4.9M, >=$5.0M
SIG_FIG20 = [29, 26, 12, 8, 13, 12]                    # p.37 Fig 20: acquired revenue, % of 109
SIG_FIG20_EDGES = [2.5, 5.0, 7.5, 10.0, 15.0]          # $M: <2.5, 2.5-4.9, 5.0-7.4, 7.5-9.9, 10.0-14.9, >=15.0
SIG_FIG21 = [30, 15, 9, 16, 9, 7, 14]                  # p.38 Fig 21: acquired EBITDA, % of 109
SIG_FIG21_EDGES = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5]      # $M: <0.5, 0.5-0.749, 0.75-0.999, 1.0-1.4, 1.5-1.9, 2.0-2.4, >=2.5
SIG_FIG23 = [[54, 30, 3, 13], [21, 42, 33, 4], [4, 46, 33, 17], [19, 19, 24, 38]]   # p.39 Fig 23: % in multiple bins
SIG_FIG23_EBITDA_EDGES = [0.5, 1.0, 2.0]               # $M groups: <0.5, 0.5-0.999, 1.0-1.9, >=2.0 (left to right on the chart)
SIG_FIG23_MULT_EDGES = [3.0, 4.0, 5.0]                 # bars: <3.0x, 3.0-3.9x, 4.0-4.9x, >=5.0x
SIG_FIG23_EBITDA_W = [30, 24, 25, 21]                  # Fig 21 collapsed to Fig 23's groups (15+9, 16+9, 7+14)
# Stanford GSB 2026 Search Fund Study (E967; sha256 c2e94f0f0e019467...), p.23 [PAGE 22] Exhibit 4.
ST26_PRICE = [10, 17, 20, 15, 38]                      # <$5M, $5M to $8M, $9M to $12M, $13M to $16M, >$16M (n=318)
ST26_PRICE_EDGES = [5.0, 8.5, 12.5, 16.5]              # integer $M labels read as rounded: edges half-way between
ST26_N_PRICE = 318
ST26_MED_EBITDA, ST26_MED_MARGIN = 2.0, 0.23           # all acquisitions 1984-2025 (EBITDA range -$1.6M to $25.0M)
ST26_MED_EBITDA_2425, ST26_MARGIN_2425 = 2.5, 0.25     # 2024-25 cohort column
ST26_MULT = {'all': 6.3, '2022-23': 7.0, '2024-25': 6.2}
ST26_EBITDA_2223, ST26_MARGIN_2223 = 2.2, 0.269
ST26_MIN_EBITDA = -1.6                                 # the same table's minimum (the only $1.6M in Exhibit 4)
# IESE International Search Funds 2024 (ST-658-E; sha256 c32b16298323c54a...), p.28 Exhibit 7.
IESE_PRICE = [6, 23, 24, 47]                           # <$4M, $4-$8, $8-$12, >$12 ($M)
IESE_PRICE_EDGES = [4.0, 8.0, 12.0]
IESE_MED_EBITDA, IESE_MED_MARGIN, IESE_MULT = 2.2, 0.24, 5.7
IESE_N_ACQ = 146               # p.8 "146 had acquired a company"; the price-statistics n is not printed
IESE_N_PRICE = 93              # used for sampling: Exhibit 8's N of acquired funds with ROI data (conservative)
# BCG/TUM 2013, Divide and Conquer (sha256 6743e68f5f051fdc...): 365 deals over $300M, 2000-2011.
BCG13_PHI_IND = [6, 13, 21, 23, 23, 29, 30, 39, 39, 44, 48, 51]   # p.11 Exhibit 4: target CAR, % of NPV of synergies
BCG13_PHI_MEDIAN = 31          # p.11 "Median = 31%" (p.5: "sellers collect, on average, 31 percent")
BCG13_POOL_MEDIAN = 4.8        # p.6 Exhibit 1: median announced synergy, % of target sales
BCG13_POOL = {"Mining": 7.3, "Chemicals": 8.0, "Other": 5.7, "Finance": 8.6, "Service": 4.9, "Health care": 9.9,
              "Business equipment": 5.4, "Books": 4.4, "Construction": 5.6, "Retail": 3.0, "Transportation": 3.9,
              "Steel": 3.2, "Telecommunications": 4.4, "Food": 3.2, "Fabricated products": 5.7, "Household": 5.1,
              "Beer": 4.2, "Autos": 2.9, "Oil": 2.4, "Gaming": 1.8, "Utilities": 2.5, "Wholesale": 2.0}   # p.6 (Paper: n/a)
BCG13_N = 365
# BCG 2018 M&A Report (sha256 437bea4c6935a013...), p.21 Exhibit 12, 2008 ... 2017 (1,000 public-to-public deals).
BCG18_TARGET = [34, 36, 44, 67, 65, 44, 67, 62, 64, 54]
BCG18_BUYER = [66, 64, 56, 33, 35, 57, 34, 38, 36, 46]
BCG18_N = 1000
# Console industry -> nearest BCG/TUM industry (research round's mapping)
BCG_MAP = {"home": "Construction", "medical": "Health care", "vet": "Health care", "msp": "Service", "saas": "Service",
           "prof": "Service", "mfg": "Fabricated products", "dist": "Wholesale", "ecom": "Retail", "staff": "Service",
           "land": "Service", "wash": "Service", "auto": "Service", "constr": "Construction", "fit": "Gaming", "rest": "Retail"}
DAMO_MAP = {"Mining": ["Metals & Mining"], "Chemicals": ["Chemical (Basic)", "Chemical (Diversified)", "Chemical (Specialty)"],
            "Other": ["Total Market (without financials)"], "Service": ["Business & Consumer Services", "Computer Services", "Information Services"],
            "Health care": ["Healthcare Products", "Drugs (Pharmaceutical)", "Drugs (Biotechnology)", "Hospitals/Healthcare Facilities",
                            "Healthcare Support Services", "Heathcare Information and Technology"],
            "Business equipment": ["Computers/Peripherals", "Electronics (General)", "Semiconductor", "Telecom. Equipment", "Software (System & Application)"],
            "Books": ["Publishing & Newspapers"], "Construction": ["Engineering/Construction", "Homebuilding", "Building Materials", "Construction Supplies"],
            "Retail": ["Retail (General)", "Retail (Special Lines)", "Retail (Grocery and Food)", "Retail (Automotive)", "Retail (Building Supply)", "Retail (Distributors)"],
            "Transportation": ["Transportation", "Trucking", "Air Transport", "Transportation (Railroads)"], "Steel": ["Steel"],
            "Telecommunications": ["Telecom. Services", "Telecom (Wireless)", "Cable TV"], "Food": ["Food Processing"],
            "Fabricated products": ["Machinery"], "Household": ["Household Products"], "Beer": ["Beverage (Alcoholic)"], "Autos": ["Auto & Truck", "Auto Parts"],
            "Oil": ["Oil/Gas (Integrated)", "Oil/Gas (Production and Exploration)", "Oilfield Svcs/Equip."], "Gaming": ["Hotel/Gaming", "Recreation", "Entertainment"],
            "Utilities": ["Utility (General)", "Utility (Water)", "Power"], "Wholesale": ["Food Wholesalers", "Retail (Distributors)"]}
W_SF = 0.9                    # self-funded share of searchers (judgment, the analyst's)
LOW_RAMP = (1e5, 2.5e5)       # SIG's open '<$500k' bin: 0 at EBITDA $100k, full at $250k (judgment)
GROUPS = {"individual": ["ind"], "strategic": ["str", "adj"], "financial": ["pep", "add", "fo"]}
GROUPED = ["ind", "str", "adj", "pep", "add", "fo"]
BANDS = ["<500K", "500K-1M", "1M-2M", "2M-5M", "5M-50M"]
VC = [2.5e5, math.sqrt(5e5 * 1e6), math.sqrt(1e6 * 2e6), math.sqrt(2e6 * 5e6), math.sqrt(5e6 * 5e7)]   # as competition_buyers.py
# the knot table: the research round's 15 SDE points (out/eta_knots.json); report points for the effect, $100k-$10M
KNOT_SDE = [1.5e5, 2.5e5, 4e5, 6e5, 8e5, 1e6, 1.5e6, 2e6, 2.5e6, 3e6, 4e6, 5e6, 7e6, 1e7, 1.5e7]
LNK = np.log(KNOT_SDE)
REPORT_SDE = [1e5] + KNOT_SDE[:-1]
EFFECT_SDE = sorted(REPORT_SDE + [float(x) for x in np.exp(np.linspace(math.log(1e5), math.log(1e7), 37))[1:-1]])
# exact source texts of the snapshot page that the patched copies replace (each must occur exactly once)
ETA_ROW = '{k:"eta", n:"Search fund / ETA buyer",    syn:.04, mf:.98, lo:.6e6,  hi:3.2e6, fit:'
ETA_ROW_KNOTS = '{k:"eta", n:"Search fund / ETA buyer",    syn:.04, mf:.98, knots:MODELS.fitted.buyers.eta_presence.knots, fit:'
ETA_WIN = 'syn:.04, mf:.98, lo:.6e6,  hi:3.2e6,'
SIZEFIT_LINE = '    const sizeFit = grp ? Math.min(1,buyerMix(out.Vbase)[grp]/MIX_MAX[grp])\n'
SIZEFIT_KNOTS = '                  : b.knots ? clamp(lerpKnots(Math.log(Math.max(s.ern,1e4)),b.knots),0,1)\n'
IND_ROW = '{k:"ind", n:"Individual owner-operator",  syn:0,   mf:.90,'
IND_ROW_NEW = '{k:"ind", n:"Individual owner-operator",  syn:0,   mf:MODELS.fitted.buyers.mf_ind,'
OLD_COMMENT = ("    /* how present this buyer's group is at this deal value, from IBBA's buyer-type mix\n"
               "       (fitted). Search funds keep their own earnings window, which matches the Stanford\n"
               "       2024 study's median deal ($1.6M of EBITDA). Was a hand-set window per archetype. */\n")
OLD_HEADER = ("   mf   : multiple factor relative to model value (the BIZCOMPS closed-sale value, where most buyers are\n"
              "          individuals; financial archetypes sit above 1 too, so it is not a financial-buyer baseline)\n"
              "   lo/hi: earnings window, used only by the search fund and the MBO; every other archetype's\n"
              "          presence by deal size comes from IBBA's fitted buyer-type mix (buyerMix)\n")
# revision 3: the header keeps lo/hi for the search fund and the MBO (the measured presence curve is not adopted)
NEW_HEADER = ("   mf   : multiple factor relative to model value (the BIZCOMPS closed-sale value, where most buyers are\n"
              "          individuals; financial archetypes sit above 1 too, so it is not a financial-buyer baseline).\n"
              "          ind's is calibrated (MODELS.fitted.buyers.mf_ind): with the other factors, PHI and syn as\n"
              "          set, the buyer-type-weighted price averages to the fitted value over BIZCOMPS sizes. Re-solve\n"
              "          it (fit: buyer_factors.py) when another mf, syn, PHI, the synergy pool or buyerMix changes\n"
              "   lo/hi: earnings window (hand-set), used only by the search fund and the MBO; every other\n"
              "          archetype's presence by deal size comes from IBBA's fitted buyer-type mix (buyerMix). A\n"
              "          measured search-fund presence curve was checked and not adopted: MODELS.fitted.buyers.eta_check\n")
OLD_DATATAB = ("individual / strategic / financial shares by deal value (search funds keep their window, which matches "
               "Stanford&rsquo;s 2024 median deal)")
ICOMP = "/* ---- §20 competition"           # a no-op override for the copied probe (it then skips its compPrem hook)
# revision 3: MODELS.fitted.competition.strategic_premium.status (the only competition text that changes: ind's mf is calibrated)
STATUS_OLD = '"status":"consistency check only; BUYERS mf, syn and PHI unchanged (judgment)"'
STATUS_NEW = ('"status":"consistency check only; BUYERS strategic and financial mf, syn and PHI unchanged (judgment); '
              'the individual\'s mf is calibrated (MODELS.fitted.buyers)"')
ENG_PINS_TOL = 0.40                          # the repo's calibration pin: model offers per closed deal within 0.40 of IBBA's lower-bound mean
CHECKS = []


def check(name, ok, detail):
    CHECKS.append(dict(name=name, outcome='pass' if ok else 'FAIL', detail=detail))
    print(('PASS ' if ok else 'FAIL ') + name + ': ' + detail, flush=True)


def note(name, detail):
    CHECKS.append(dict(name=name, outcome='info', detail=detail))
    print('INFO ' + name + ': ' + detail, flush=True)


def sha(p, k=16):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:k]


def rnd(x, d=6):
    """round floats recursively (significant digits) so RESULT.json is stable"""
    if isinstance(x, float):
        return float('%.*g' % (d, x)) if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: rnd(v, d) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, d) for v in x]
    if isinstance(x, (np.floating,)):
        return rnd(float(x), d)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return rnd(x.tolist(), d)
    return x


# ------------------------------------------------------------------------------------------------------------------
# node probe (written to OUT and run with the harness, which loads the frozen snapshot or a patched copy of it)
# ------------------------------------------------------------------------------------------------------------------
PROBE_JS = r"""/* buyer_factors probe (written by buyer_factors.py): evaluates the console's model on the frozen snapshot, or on a
   patched copy of it (cfg.page), through the harness. usage: node probe.js HARNESS CFG.json  ->  JSON on stdout */
const H=require(process.argv[2]); const cfg=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const load=(page,ov)=>H.load(ov||[],page||undefined);
/* the peer median gross margin at this revenue: the page's fitted curve where it has one (MODELS.fitted.peer_gm, October
   2026 on: read linearly in log10 revenue, flat beyond the knots, as the page's peerGm reads it), else IND's hand-set
   median (the snapshot; car washes). On the snapshot it returns IND[ind].gm, so the shipped results are unchanged. */
function gmAt(A,ind,rev){ const F=A.MODELS.fitted.peer_gm, G=F&&F.by_industry[ind];
  if(!G) return A.IND[ind].gm;
  const x=Math.log10(Math.max(rev,1e4)), K=F.knots_log10_rev, n=K.length;
  if(x<=K[0]) return G.gm[0]; if(x>=K[n-1]) return G.gm[n-1];
  let i=0; while(x>K[i+1]) i++; return G.gm[i]+(G.gm[i+1]-G.gm[i])*(x-K[i])/(K[i+1]-K[i]); }
function med(A,ind,ern){ const I=A.IND[ind], RF=A.sizeRefs(ern), m=A.typMargin(ind,ern);
  return {ind,rev:ern/m,ern,grw:I.grw,gm:gmAt(A,ind,ern/m),rec:I.rec,cc:.16,ret:I.ret,plt:.40,own:RF.own,mgt:RF.mgt,fin:RF.fin,
          yrs:6,buyers:I.buyers,st:null,franchise:false,ask:1e6}; }
function peRefOf(A,ind,r){ return r.nEngRef/((A.IND[ind].buyers||50)*A.ENG_SHARE); }
/* the earnings at which the pre-quality fitted value equals V, found as fit/competition_buyers.py does */
function atV(A,ind,V){ let lo=Math.log(2e3),hi=Math.log(2e8);
  for(let i=0;i<70;i++){const m=(lo+hi)/2; const r=A.model(med(A,ind,Math.exp(m))); if(r.Vbase<V) lo=m; else hi=m;}
  return Math.exp((lo+hi)/2); }
const out={};
if(cfg.mode==="identity"){
  const A=load(cfg.page,cfg.overrides);
  out.PHI=A.PHI; out.ENG_SHARE=A.ENG_SHARE; out.REF_RATIO=A.REF_RATIO;
  out.BUYERS=A.BUYERS.map(b=>({k:b.k,mf:b.mf,syn:b.syn,lo:(b.lo===undefined)?null:b.lo,hi:(b.hi!==undefined&&isFinite(b.hi))?b.hi:null}));
  out.IND={}; for(const k of Object.keys(A.IND)) out.IND[k]={buyers:A.IND[k].buyers,strat:A.IND[k].strat};   /* gm: per row (gmAt) */
  out.buyer_mix=A.MODELS.fitted.buyer_mix; out.support=A.MODELS.value.support;
  const C=A.MODELS.fitted.competition;
  out.competition={eng_share:C.eng_share,eng_share_se:C.eng_share_se,nb_r:C.nb_r,band_centres:C.band_centres,
    offers_per_closed_deal_model:C.offers_per_closed_deal_model,offers_per_closed_deal_bandfree_fit:C.offers_per_closed_deal_bandfree_fit,
    offers_per_closed_deal_bandfree_se:C.offers_per_closed_deal_bandfree_se,strategic_premium:C.strategic_premium};
  out.wedge={S:A.MODELS.value.soi_size_wedge,D:A.MODELS.value.sde_to_ebitda_wedge||{}};
  out.wedge_test=[]; for(const n2 of [null,"54","56","81","62","51"]) for(const rev of [2e5,1e6,2.5e6,5e6,7.6e6,1e7,2e7,4e7,1.5e8])
    out.wedge_test.push([n2,rev,A.sdeEbitdaWedge(n2,rev)]);
  out.rows=[];
  for(const ern of cfg.sde) for(const ind of Object.keys(A.IND)){ const s=med(A,ind,ern), r=A.model(s), B={};
    for(const b of r.buyers) B[b.k]=[b.sizeFit,b.Vj/r.V,b.PE];
    const mx=A.buyerMix(r.Vbase);
    out.rows.push({ind,ern,gm:s.gm,V:r.V,Vbase:r.Vbase,M:r.M,x:r.synE/s.ern,synE_rev:r.synE/s.rev,mix:[mx.individual,mx.strategic,mx.financial],B}); }
}
if(cfg.mode==="effect"){
  const A0=load(); const inds=Object.keys(A0.IND);
  out.band_ern=cfg.band_V.map(V=>inds.map(ind=>atV(A0,ind,V)));
  out.runs={};
  for(const run of cfg.runs){
    const A=load(run.page,run.overrides), grid=[], bands=[];
    if(run.grid) for(const ern of cfg.sde) for(const ind of inds){
      const s=med(A,ind,ern); const r0=A.model(s); s.ask=A.REF_RATIO*r0.V;
      const r=A.model(s), h=A.model(Object.assign({},s,{buyers:Math.max(1,Math.round(A.IND[ind].buyers/2))}));
      grid.push({ind,ern,peRef:peRefOf(A,ind,r),nEngRef:r.nEngRef,sf_eta:r.buyers.find(b=>b.k==="eta").sizeFit,avgPE:r.avgPE,
                 PC:r.PC,compPrem:r.compPrem,EVp:r.EVp,PC_half:h.PC,compPrem_half:h.compPrem,EVp_half:h.EVp,thin_half:h.thinF}); }
    cfg.band_V.forEach((V,bi)=>inds.forEach((ind,i)=>{ const s=med(A,ind,out.band_ern[bi][i]); const r=A.model(s);
      bands.push({b:bi,ind,ern:s.ern,Vbase:r.Vbase,peRef:peRefOf(A,ind,r),g:A.IND[ind].buyers*peRefOf(A,ind,r),
                  sf_eta:r.buyers.find(b=>b.k==="eta").sizeFit}); }));
    out.runs[run.tag]={eng_share:A.ENG_SHARE,grid,bands};
  }
}
if(cfg.mode==="knotcheck"){
  const A=load(cfg.page,cfg.overrides), eta=A.BUYERS.find(b=>b.k==="eta"), mbo=A.BUYERS.find(b=>b.k==="mbo");
  out.knots=eta.knots||null; out.eta_lo=(eta.lo===undefined)?null:eta.lo; out.eta_hi=(eta.hi===undefined)?null:eta.hi;
  out.mbo=[mbo.lo,isFinite(mbo.hi)?mbo.hi:null]; out.mf={}; for(const b of A.BUYERS) out.mf[b.k]=b.mf;
  out.eng_share=A.ENG_SHARE; out.buyers_table=A.MODELS.fitted.buyers||null;
  out.rows=[]; for(const ern of cfg.sde) for(const ind of cfg.inds){ const r=A.model(med(A,ind,ern));
    out.rows.push([ind,ern,r.buyers.find(b=>b.k==="eta").sizeFit,r.buyers.find(b=>b.k==="mbo").sizeFit]); }
}
if(cfg.mode==="etamf"){
  const A=H.load(); out.rows=[];
  for(const c of cfg.cases) for(const ind of Object.keys(A.IND)){
    const rev=c.E/c.margin, w=A.sdeEbitdaWedge(A.naicsFor(ind),rev), sde=c.E*w, fv=A.fitValue(sde,rev,ind,c.year);
    out.rows.push({lab:c.lab,ind,E:c.E,wedge:w,sde,V_over_E:fv.point/c.E}); }
}
process.stdout.write(JSON.stringify(out));
"""


def run_probe(cfg, tag):
    jpath = os.path.join(OUT, 'probe.js')
    with open(jpath, 'w') as f:
        f.write(PROBE_JS)
    cpath = os.path.join(OUT, 'probe_cfg_%s.json' % tag)
    with open(cpath, 'w') as f:
        json.dump(cfg, f, sort_keys=True)
    r = subprocess.run(['node', jpath, HARNESS, cpath], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    return json.loads(r.stdout)


# ------------------------------------------------------------------------------------------------------------------
# patched copies of the snapshot page (scratch) and the copied fit/competition_buyers.py
# ------------------------------------------------------------------------------------------------------------------
def build_page(name, edits):
    html = open(SNAP, encoding='utf-8').read()
    for a, b in edits:
        n = html.count(a)
        if n != 1:
            raise RuntimeError('page edit target occurs %d times: %r' % (n, a[:100]))
        html = html.replace(a, b)
    p = os.path.join(PAGES, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(html)
    return p


# Minimal patches to the snapshot's fit/competition_buyers.py (written against the page before ENG_SHARE was
# integrated): (1) its harness: a wrapper that loads the page under test through /tmp/claude-0/fit6/harness.js;
# (2) its probe's compPrem hook: the page now has COMP_H where the literal 3 was; (3) its peRef read: the page now has
# ENG_SHARE where the literal 0.34 was (nEngRef / (I.buyers x ENG_SHARE) = peRef exactly); (4) an early exit after the
# ENG_SHARE calibration and its NB specification range, dumping them as JSON. Nothing else is changed.
CB_PATCHES = [
    ('HARNESS = "/tmp/claude-0/fit5/harness.js"',
     'HARNESS = os.environ["CB_HARNESS"]                      # buyer_factors.py: wrapper loading the page under test'),
    ('const base=[["out.compPrem=clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);",\n'
     '             "out.compPrem=(MODELS.__comp!=null)?MODELS.__comp:clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);"]];',
     'const base=[["out.compPrem=clamp(out.compK*Math.log((COMP_H+out.nEng)/(COMP_H+out.nEngRef)),-.08,.14);",\n'
     '             "out.compPrem=(MODELS.__comp!=null)?MODELS.__comp:clamp(out.compK*Math.log((COMP_H+out.nEng)/(COMP_H+out.nEngRef)),-.08,.14);"]];'),
    ('peRef:r.nEngRef/(A.IND[ind].buyers*0.34)', 'peRef:r.nEngRef/(A.IND[ind].buyers*A.ENG_SHARE)'),
    ('           qtxt(QL["pln_vs_nb (same parameter count, not nested; LR = dAIC)"]), qtxt(QL["pepperdine_constrained"])))\n',
     '           qtxt(QL["pln_vs_nb (same parameter count, not nested; LR = dAIC)"]), qtxt(QL["pepperdine_constrained"])))\n'
     '    if os.environ.get("CB_ENG_ONLY"):                    # buyer_factors.py: stop after the ENG_SHARE calibration\n'
     '        json.dump(dict(eng_share=float(c_hat), eng_share_se=float(c_hat * c_se_log), eng_share_ci95=[float(x) for x in c_ci],\n'
     '                       nb_r=float(r_hat), nb_r_se=float(r_hat * r_se_log), nb_r_ci95=[float(x) for x in r_ci], jk_se_log=[float(x) for x in jk_se],\n'
     '                       g_b=[float(x) for x in gb], G_industries=list(PB.pivot_table(index="b", columns="ind", values="g").columns), G=G.tolist(),\n'
     '                       nll_M5=float(fits["M5"][1]), nll_M2=float(fits["M2"][1]), lr_M5_vs_M2=float(tests["M5_vs_M2 (console size gradient) LR, df4"]),\n'
     '                       p_M5_vs_M2=float(tests_p["M5_vs_M2"]), spec=SPEC[["spec", "family", "c", "dispersion", "nll"]].to_dict("records"),\n'
     '                       eng_share_spec_range=[float(nbspec.c.min()), float(nbspec.c.max())],\n'
     '                       nb_r_spec_range=[float(nbspec.dispersion.min()), float(nbspec.dispersion.max())], eng_share_spec_n=n_spec_nb,\n'
     '                       pln=dict(c=float(pln_row.c), se=float(pln_c_se), log_sd=float(pln_row.dispersion), nll=float(pln_row.nll)),\n'
     '                       n_boot=B_BOOT, log=LOG), open(os.path.join(OUT, "eng_share_calibration.json"), "w"), indent=1)\n'
     '        return\n'),
]


def prepare_cb():
    src = open(CB_SRC, encoding='utf-8').read()
    for a, b in CB_PATCHES:
        n = src.count(a)
        if n != 1:
            raise RuntimeError('competition_buyers.py patch target occurs %d times: %r' % (n, a[:100]))
        src = src.replace(a, b)
    with open(CB_COPY, 'w', encoding='utf-8') as f:
        f.write(src)


def cb_harness(tag, page):
    hj = os.path.join(CB_DIR, 'harness_%s.js' % tag)
    with open(hj, 'w') as f:
        f.write('/* written by buyer_factors.py: %s through the fit6 harness */\nconst H=require(%s);\nmodule.exports={load:o=>H.load(o,%s)};\n'
                % (os.path.basename(page), json.dumps(HARNESS), json.dumps(page)))
    return hj


def start_cb(tag, page):
    d = os.path.join(CB_DIR, tag)
    os.makedirs(d, exist_ok=True)
    hj = cb_harness(tag, page)
    env = dict(os.environ, CB_HARNESS=hj, CB_OUT=d, CB_ENG_ONLY='1', CB_BOOT=str(CB_BOOT))
    log = open(os.path.join(d, 'run.log'), 'w')
    p = subprocess.Popen(['python3', '-I', CB_COPY], env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
    return p, d, log


def finish_cb(h):
    p, d, log = h
    rc = p.wait(timeout=7200)
    log.close()
    if rc != 0:
        raise RuntimeError(open(os.path.join(d, 'run.log')).read()[-3000:])
    return json.load(open(os.path.join(d, 'eng_share_calibration.json')))


def copy_tree_plain(src, dst):
    """copy a directory's files by content only (the snapshot is read-only; the copy must be writable and removable)"""
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for fn in sorted(files):
            shutil.copyfile(os.path.join(root, fn), os.path.join(dst, rel, fn))


def start_repo_tests(tag, page):
    """the snapshot's own tests/model.test.js on a scratch copy of the repo whose index.html is `page`"""
    d = os.path.join(SCR, 'testrun', tag)
    if os.path.isdir(d):
        shutil.rmtree(d)
    for sub in ('tests', 'fit'):
        copy_tree_plain(os.path.join(SNAP_DIR, sub), os.path.join(d, sub))
    for fn in ('AUDIT.md', 'AUDIT_FINDINGS.md'):
        shutil.copyfile(os.path.join(SNAP_DIR, fn), os.path.join(d, fn))
    shutil.copyfile(page, os.path.join(d, 'index.html'))
    return subprocess.Popen(['node', 'tests/model.test.js'], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def finish_repo_tests(p):
    out, _ = p.communicate(timeout=3600)
    m = re.search(r'(\d+) passed, (\d+) failed', out)
    fails = [ln[5:].strip() for ln in out.splitlines() if ln.startswith('FAIL:')]
    return dict(passed=int(m.group(1)) if m else None, failed=int(m.group(2)) if m else None, fails=fails, exit=p.returncode)


def run_invariants(tag, page, ex):
    """fit/competition_buyers.py's own invariant probe ('check' mode of its probe.js, written by the copied script) on a page"""
    hj = cb_harness(tag, page)
    cpath = os.path.join(OUT, 'probe_cfg_invariants_%s.json' % tag)
    with open(cpath, 'w') as f:
        json.dump({'mode': 'check', 'n': N_INV, 'example': ex, 'overrides': [[ICOMP, ICOMP]]}, f, sort_keys=True)
    r = subprocess.run(['node', os.path.join(CB_DIR, 'snapshot', 'probe.js'), hj, cpath], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    c = json.loads(r.stdout)['check']
    return {k: c[k] for k in ('n', 'mono_fail', 'thin_fail', 'ref_fail', 'qual_fail', 'median_fail', 'median_max_abs_comp', 'median_max_thin_gap')}


# ------------------------------------------------------------------------------------------------------------------
# 0. sources and transcription checks
# ------------------------------------------------------------------------------------------------------------------
def page_text(pdf, p):
    r = subprocess.run(['pdftotext', '-layout', '-f', str(p), '-l', str(p), pdf, '-'], capture_output=True, text=True, timeout=300)
    return r.stdout


def pcts(text):
    return [float(x) for x in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*%', text)]


def is_subseq(seq, pool):
    it = iter(pool)
    return all(any(abs(v - p) < 1e-9 for p in it) for v in seq)


def sub_multiset(a, b):
    return not (Counter(a) - Counter(b))


def transcription_checks():
    t = page_text(SIG_PDF, 7)
    check('SIG respondents (p.7)', '279 responses' in re.sub(r'\s+', ' ', t), '"1,027 invitations were sent and 279 responses"')
    t = page_text(SIG_PDF, 35)
    check('SIG acquirers (p.35)', 'Of all 279 respondents, 109 had successfully' in t, '109 of 279 had acquired')
    t = page_text(SIG_PDF, 21)
    check('SIG Fig 7 (p.21)', 'Figure 7:' in t and is_subseq(SIG_FIG7, pcts(t)), 'ten target shares in bin order %s' % SIG_FIG7)
    t = page_text(SIG_PDF, 37)
    check('SIG Fig 20 (p.37)', 'Figure 20:' in t and sub_multiset(SIG_FIG20, pcts(t)) and sum(SIG_FIG20) == 100, 'revenue shares %s' % SIG_FIG20)
    t = page_text(SIG_PDF, 38)
    t21 = t[t.index('Figure 21:'):t.index('Figure 22:')]
    check('SIG Fig 21 (p.38)', sub_multiset(SIG_FIG21, pcts(t21)) and sum(SIG_FIG21) == 100, 'EBITDA shares %s' % SIG_FIG21)
    t = page_text(SIG_PDF, 39)
    body = t[t.index('Figure 23:'):]
    toks = []
    for ln in body.splitlines():
        for m in re.finditer(r'(\d+)%', ln):
            if m.start() > 8:                      # the y-axis labels sit in the first columns
                toks.append((m.start(), float(m.group(1))))
    by_x = [v for _, v in sorted(toks)]
    flat = [float(v) for g in SIG_FIG23 for v in g]
    check('SIG Fig 23 (p.39)', by_x == flat and all(sum(g) == 100 for g in SIG_FIG23),
          '16 bar labels ordered by x position = the four groups left to right %s' % SIG_FIG23)
    t = page_text(ST26_PDF, 23)
    tt = re.sub(r'[ \t]+', ' ', t)
    ok = all(re.search(p, tt) for p in [r'<\$5M 10%', r'\$5M to \$8M 17%', r'\$9M to \$12M 20%', r'\$13M to \$16M 15%', r'>\$16M 38%', r'n=318',
                                        r'Company EBITDA at Purchase -\$1\.6M \$2\.0M \$25\.0M', r'EBITDA Margin at Purchase -23% 23% 67%',
                                        r'Purchase Price/EBITDA Multiple NM 6\.3x'])
    row = [ln for ln in t.splitlines() if ln.strip().startswith('Company EBITDA at Purchase') and '$1.3M' in ln][0].split()
    mrow = [ln for ln in t.splitlines() if ln.strip().startswith('Company EBITDA Margin at Purchase') and '18.2%' in ln][0].split()
    prow = [ln for ln in t.splitlines() if ln.strip().startswith('Purchase Price/EBITDA') and '5.2x' in ln][0].split()
    ok = ok and row[-1] == '$2.5M' and row[-2] == '$2.2M' and mrow[-1] == '25.0%' and mrow[-2] == '26.9%' and prow[-1] == '6.2x' and prow[-2] == '7.0x'
    hdr = [ln for ln in t.splitlines() if 'Minimum' in ln and 'Median' in ln and 'Maximum' in ln]
    ok = ok and len(hdr) == 1 and '1.6M' not in ' '.join(row)
    check('Stanford 2026 Exhibit 4 (p.23)', ok, 'price bins %s n=318; all acquisitions: EBITDA minimum -$1.6M, median $2.0M, maximum $25.0M '
          '(2024-25 $2.5M, 2022-23 $2.2M); margin 23%%; 6.3x / 7.0x / 6.2x' % ST26_PRICE)
    t = page_text(IESE_PDF, 28); tt = re.sub(r'\s+', ' ', t)
    ok = bool(re.search(r'<\$4M \$4-\$8 \$8-\$12 >\$12 0\.8 11\.7 65\.4 6% 23% 24% 47%', tt)) and bool(re.search(r'EBITDA at Purchase \(\$M\) 0\.0 2\.2 11\.6', tt)) \
        and bool(re.search(r'EBITDA Margin at Purchase 0% 24% 70%', tt)) and bool(re.search(r'Purchase Price / EBITA 0\.0 5\.7x', tt))
    t8 = re.sub(r'\s+', ' ', page_text(IESE_PDF, 8))
    check('IESE 2024 Exhibit 7 (p.28)', ok and '146 had acquired a company' in t8, 'price bins %s; median EBITDA $2.2M, margin 24%%, 5.7x; 146 acquisitions (p.8)' % IESE_PRICE)
    t = page_text(BCG13_PDF, 11)
    ints = [float(x) for x in re.findall(r'(?<![\d.])(\d+)(?![\d.%])', t[t.index('Exhibit 4'):])]
    check('BCG 2013 Exhibit 4 (p.11)', 'Median = 31%' in t and is_subseq(BCG13_PHI_IND, ints) and '365 deals' in t,
          '12 industry medians in order %s, median 31%%, 365 deals' % BCG13_PHI_IND)
    t = page_text(BCG13_PDF, 6)
    ok = 'Median = 4.8%' in t and '365 deals' in t
    for name, v in BCG13_POOL.items():
        lns = [ln for ln in t.splitlines() if re.match(r'^\s*' + re.escape(name) + r'\s', ln)]
        ok = ok and len(lns) >= 1 and lns[0].split()[-1] == ('%.1f' % v)
    check('BCG 2013 Exhibit 1 (p.6)', ok, 'median 4.8% of target sales and the 22 industry values (target-sales column)')
    t = page_text(BCG18_PDF, 21)
    i12 = t.index('Exhibit 12'); vals = [float(x) for x in re.findall(r'(?<![\d.])(\d{2})(?![\d.%])', t[i12:t.index('Sources', i12)])]
    ok = sub_multiset(BCG18_TARGET + BCG18_BUYER, vals) and all(abs(a + b - 100) <= 1 for a, b in zip(BCG18_TARGET, BCG18_BUYER)) and '1,000' in t
    check('BCG 2018 Exhibit 12 (p.21)', ok, 'target shares 2008-17 %s (mean %.1f; buyer share = 100 - target within rounding)' % (BCG18_TARGET, np.mean(BCG18_TARGET)))


# ------------------------------------------------------------------------------------------------------------------
# helpers: console replicas (checked against the harness)
# ------------------------------------------------------------------------------------------------------------------
def wedge_fn(S, D):
    K, Wd = np.array(S['ln_rev_knots'], float), np.array(S['wedge'], float)

    def wedge(rev, n2=None, override=None):
        rev = np.asarray(rev, float)
        if override:
            return np.full_like(rev, float(override))
        sw = np.interp(np.log(np.maximum(rev, 1e4)), K, Wd)
        lvl = D.get(n2, S['dvi_median']) if n2 else S['dvi_median']
        return np.clip(lvl * sw / S['pin_wedge'], 1.02, 2.75)
    return wedge


def mix_fn(knots):
    K = np.asarray(knots, float)

    def mix(v):
        x = np.log(np.maximum(np.asarray(v, float), 1e4))
        es = np.exp(np.interp(x, K[:, 0], K[:, 1])); ef = np.exp(np.interp(x, K[:, 0], K[:, 2])); s = 1 + es + ef
        return np.stack([1 / s, es / s, ef / s], -1)
    grid = 1e5 * np.power(500.0, np.arange(201) / 200)
    mmax = mix(grid).max(0)
    return mix, mmax


def binned_ln_fit(edges, counts):
    """MLE of a lognormal from binned counts; edges are the interior cut points. Returns mu, sigma, theta, nll."""
    counts = np.asarray(counts, float); e = np.log(np.asarray(edges, float))

    def probs(mu, sg):
        c = stats.norm.cdf((e - mu) / sg)
        return np.diff(np.r_[0.0, c, 1.0])

    def nll(th):
        return -float(np.sum(counts * np.log(np.clip(probs(th[0], math.exp(th[1])), 1e-300, None))))
    x0 = np.array([float(np.sum(np.r_[e[0], (e[1:] + e[:-1]) / 2, e[-1]] * counts) / counts.sum()), math.log(0.8)])
    r = optimize.minimize(nll, x0, method='Nelder-Mead', options=dict(xatol=1e-9, fatol=1e-11, maxiter=4000))
    th = r.x
    return th[0], math.exp(th[1]), th, nll


def hessian_cov(nll, th, h=1e-4):
    k = len(th); Hm = np.zeros((k, k)); I = np.eye(k) * h
    for i in range(k):
        for j in range(k):
            Hm[i, j] = (nll(th + I[i] + I[j]) - nll(th + I[i] - I[j]) - nll(th - I[i] + I[j]) + nll(th - I[i] - I[j])) / (4 * h * h)
    return np.linalg.inv(Hm)


def chi2_fit(edges, counts, mu, sg, npar):
    counts = np.asarray(counts, float); n = counts.sum()
    p = np.diff(np.r_[0.0, stats.norm.cdf((np.log(edges) - mu) / sg), 1.0])
    return float(np.sum((counts - n * p) ** 2 / (n * p))), len(counts) - 1 - npar


# SIG joint model: ln E ~ N(muE, sE) binned in Fig 23's four EBITDA groups; ln m | E ~ N(a + b ln E($M), s) binned.
_ZG = np.linspace(0.0, 1.0, 81)
_EL = np.log(np.r_[1e-12, SIG_FIG23_EBITDA_EDGES]); _EH = np.log(np.r_[SIG_FIG23_EBITDA_EDGES, 1e12])
_ML = np.log(np.r_[1e-12, SIG_FIG23_MULT_EDGES]); _MH = np.log(np.r_[SIG_FIG23_MULT_EDGES, 1e12])


def joint_nll(th, C):
    muE, sE, a, b, s = th[0], math.exp(th[1]), th[2], th[3], math.exp(th[4])
    zlo = np.maximum((_EL - muE) / sE, -8.0); zhi = np.minimum((_EH - muE) / sE, 8.0)
    z = zlo[:, None] + (zhi - zlo)[:, None] * _ZG[None, :]                     # 4 x 81
    lnE = muE + sE * z; mu_m = a + b * lnE
    pm = stats.norm.cdf((_MH[None, :, None] - mu_m[:, None, :]) / s) - stats.norm.cdf((_ML[None, :, None] - mu_m[:, None, :]) / s)   # 4 x 4 x 81
    val = np.trapezoid(stats.norm.pdf(z)[:, None, :] * pm, z[:, None, :], axis=2)
    return -float(np.sum(C * np.log(np.clip(val, 1e-300, None))))


def joint_fit(C, x0):
    r = optimize.minimize(joint_nll, x0, args=(C,), method='Nelder-Mead', options=dict(maxiter=20000, xatol=1e-8, fatol=1e-10))
    return r.x


def sigma_E(sigP, b, s):
    return math.sqrt(max((sigP ** 2 - s ** 2) / (1 + b) ** 2, 0.05 ** 2))


# ------------------------------------------------------------------------------------------------------------------
# presence curve, half-presence window, knot table
# ------------------------------------------------------------------------------------------------------------------
GE = np.exp(np.linspace(math.log(5e4), math.log(2e7), 3000))       # EBITDA grid, $
XS = np.exp(np.linspace(math.log(1e5), math.log(3e7), 6000))       # SDE grid, $
GE_R = np.exp(np.linspace(math.log(5e4), math.log(2e7), 1500))     # the research round's grids (eta_knots.py), for the check only
XS_R = np.exp(np.linspace(math.log(1e5), math.log(3e7), 2000))


def sig_presence(shares, smooth=False, ge=None):
    ge = GE if ge is None else ge
    sh = np.asarray(shares, float); sh = sh / sh.max()
    if smooth:      # linear in ln EBITDA between bin centres (open bins: $350k and $6M), flat beyond, same lower ramp
        cen = np.exp(np.r_[math.log(3.5e5), (np.log(SIG_FIG7_EDGES[:-1]) + np.log(SIG_FIG7_EDGES[1:])) / 2, math.log(6e6)])
        p = np.interp(np.log(ge), np.log(cen), sh)
    else:
        idx = np.searchsorted(SIG_FIG7_EDGES, ge, side='right')
        p = sh[np.clip(idx, 0, len(sh) - 1)]
    ramp = np.clip((ge - LOW_RAMP[0]) / (LOW_RAMP[1] - LOW_RAMP[0]), 0, 1) * sh[0]
    return np.where(ge < LOW_RAMP[1], ramp, p)


def presence(shares, m_sf, medE, sE, m_tr, w, wedge, wov=None, smooth=False, acq=None, ge=None, xs=None):
    """presence by SDE on XS (or xs), normalised to its maximum. acq=(mu, sigma) of ln acquired EBITDA ($M) replaces the
    self-funded target shares by the acquired-EBITDA density (a variant)"""
    ge = GE if ge is None else ge; xs = XS if xs is None else xs
    x_sf = ge * wedge(ge / m_sf, override=wov); x_tr = ge * wedge(ge / m_tr, override=wov)
    assert np.all(np.diff(x_sf) > 0) and np.all(np.diff(x_tr) > 0)
    if acq is None:
        p_sf = sig_presence(shares, smooth, ge)
        right = p_sf[-1]
    else:
        p_sf = np.exp(-0.5 * ((np.log(ge / 1e6) - acq[0]) / acq[1]) ** 2)
        right = 0.0
    p_tr = np.exp(-0.5 * ((np.log(ge) - math.log(medE)) / sE) ** 2)
    c = w * np.interp(xs, x_sf, p_sf, left=0.0, right=right) + (1 - w) * np.interp(xs, x_tr, p_tr, left=0.0, right=0.0)
    return c / c.max()


def half_window(c):
    on = np.where(c >= 0.5)[0]
    return float(XS[on[0]]), float(XS[on[-1]]), float(XS[np.argmax(c)])


def knots_of(c):
    return np.interp(KNOT_SDE, XS, c)


def knot_table(c):
    return [[round(float(x), 4), round(float(y), 3)] for x, y in zip(LNK, knots_of(c))]


def knot_halfmax(yk, xk=None, level=0.5):
    """where a knot table, read as lerpKnots reads it (linear in ln SDE), first rises to and last falls from `level`"""
    xk = LNK if xk is None else np.asarray(xk, float); yk = np.asarray(yk, float)
    lo = hi = None
    for i in range(len(xk) - 1):
        if yk[i] < level <= yk[i + 1]:
            lo = xk[i] + (level - yk[i]) / (yk[i + 1] - yk[i]) * (xk[i + 1] - xk[i]); break
    for i in range(len(xk) - 2, -1, -1):
        if yk[i] >= level > yk[i + 1]:
            hi = xk[i] + (yk[i] - level) / (yk[i] - yk[i + 1]) * (xk[i + 1] - xk[i]); break
    return math.exp(lo), math.exp(hi)


def lerp_knots(sde, K):
    """the page's lerpKnots on ln SDE (flat beyond the end knots), clamped to [0,1] as the patched sizeFit does"""
    K = np.asarray(K, float)
    return np.clip(np.interp(np.log(np.maximum(np.asarray(sde, float), 1e4)), K[:, 0], K[:, 1]), 0, 1)


def trap(x, lo, hi):
    """the shipped sizeFit trapezoid: 1 on [lo, hi], linear to 0 at 0.15 lo and at 2.6 hi"""
    x = np.asarray(x, float)
    return np.where(x < lo, np.maximum(0, 1 - (lo - x) / (lo * .85)), np.where(x > hi, np.maximum(0, 1 - (x - hi) / (hi * 1.6)), 1.0))


def ls_trapezoid(c):
    """least-squares trapezoid with the code's ramps (.85, 1.6) against a presence curve on XS (points where c > 0.01),
    from a 3 x 3 grid of starts, as the research round's eta_presence.py"""
    m = c > 0.01
    f = lambda th: float(np.sum((trap(XS[m], math.exp(th[0]), math.exp(th[1])) - c[m]) ** 2))
    best = None
    for l0 in (3e5, 6e5, 1e6):
        for h0 in (1.5e6, 3e6, 5e6):
            r = optimize.minimize(f, [math.log(l0), math.log(h0)], method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-10, maxiter=4000))
            if best is None or r.fun < best.fun:
                best = r
    return math.exp(best.x[0]), math.exp(best.x[1]), 1 - best.fun / float(np.sum((c[m] - c[m].mean()) ** 2))


# ------------------------------------------------------------------------------------------------------------------
# IBBA buyer mix: the complete band-quarters behind MODELS.fitted.buyer_mix (fit/ibba_buyer_mix.py's rule)
# ------------------------------------------------------------------------------------------------------------------
def ibba_complete_rows():
    R = pd.read_csv(IBBA_MIX, dtype=str, keep_default_na=False)
    out = {b: [] for b in BANDS}
    for _, x in R.iterrows():
        if x.band not in out or 'chart-mapped' in x.note:
            continue
        v = lambda k: float(x[k]) if x[k] != '' else None
        parts = [v('individual') or 0.0, v('strategic') or 0.0, v('pe') or 0.0, v('other') or 0.0]
        s = sum(parts)
        if s >= 95:
            out[x.band].append([parts[0] / s * 100, parts[1] / s * 100, (parts[2] + parts[3]) / s * 100])
    return {b: np.array(v) for b, v in out.items()}


def knots_from(means):
    kn = []
    for b, c in zip(BANDS, VC):
        q = means[b]; s = [max(q[0], 1) / 100, max(q[1], 1) / 100, max(q[2], 1) / 100]
        kn.append([math.log(c), math.log(s[1] / s[0]), math.log(s[2] / s[0])])
    return kn


# ------------------------------------------------------------------------------------------------------------------
# IBBA offers histograms and a replica of fit/competition_buyers.py's M5 likelihood (ENG_SHARE)
# ------------------------------------------------------------------------------------------------------------------
def load_offers():
    d = pd.read_csv(IBBA_OFFERS); o = d[d.measure == 'offers'].copy()
    o['open'] = o.cat_hi.isna(); o['k'] = o.cat_lo.astype(int)
    g = o.groupby(['period', 'band'])
    o['share'] = o.pct / g.pct.transform('sum'); o['w'] = o.share * o.n_closed.astype(float)
    o['b'] = o.band.map({b: i for i, b in enumerate(BANDS)})
    return o[o.pct > 0].reset_index(drop=True)


def ztnb_logp(k, op, mu, r):
    p = r / (r + mu); den = np.log(-np.expm1(r * np.log(p)))
    return np.where(op, stats.nbinom.logsf(k - 1, r, p), stats.nbinom.logpmf(k, r, p)) - den


def fit_m5(o, gb):
    k, op, w, b = o.k.values, o.open.values, o.w.values, o.b.values

    def nll(th):
        v = -np.sum(w * ztnb_logp(k, op, (np.exp(th[0]) * gb)[b], np.exp(th[1])))
        return v if np.isfinite(v) else 1e12
    f = optimize.minimize(nll, np.array([np.log(0.17), 0.0]), method='L-BFGS-B', bounds=[(-8, 8)] * 2)
    f2 = optimize.minimize(nll, f.x, method='Nelder-Mead', options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000))
    th = f2.x if f2.fun <= f.fun else f.x
    return float(np.exp(th[0])), float(np.exp(th[1])), float(nll(th))


def zt_mean(mu, r):
    return mu / (1 - (r / (r + mu)) ** r)


def p_any_nb(mu, r):
    return 1 - (r / (r + mu)) ** r


def cap_one(x, w=0.05):
    """the page's capOne (THIN_W = 0.05)"""
    x = np.asarray(x, float); t = (x - 1 + w) / w
    return np.where(x >= 1, 1.0, np.where(x <= 1 - w, x, x + t ** 3 * (t * (6 * t - 15) + 10) * (1 - x)))


def comp_derived(c, r, G, pln=None):
    """fields of MODELS.fitted.competition that follow from the scale c, the NB r and G (bands x industries of
    I.buyers x peRef at the band centres), as the shipped block states them"""
    n = c * G; gb = G.mean(1)
    d = {"expected_offers_typical_pool": [round(float((c * gb).min()), 2), round(float((c * gb).max()), 2)],
         "expected_offers_typical_pool_by_industry": [round(float(n.min()), 2), round(float(n.max()), 2)],
         "offers_per_closed_deal_model": {b: round(float(zt_mean(n[i], r).mean()), 3) for i, b in enumerate(BANDS)},
         "offers_per_closed_deal_poisson_shape": {b: round(float((n[i] / (1 - np.exp(-n[i]))).mean()), 3) for i, b in enumerate(BANDS)},
         "thin_half_pool": [round(float(cap_one((1 - np.exp(-.5 * n)) / (1 - np.exp(-n))).min()), 2), round(float(cap_one((1 - np.exp(-.5 * n)) / (1 - np.exp(-n))).max()), 2)],
         "thin_quarter_pool": [round(float(cap_one((1 - np.exp(-.25 * n)) / (1 - np.exp(-n))).min()), 2), round(float(cap_one((1 - np.exp(-.25 * n)) / (1 - np.exp(-n))).max()), 2)],
         "nb_thin_pool.thin_half_pool": [round(float((p_any_nb(.5 * n, r) / p_any_nb(n, r)).min()), 2), round(float((p_any_nb(.5 * n, r) / p_any_nb(n, r)).max()), 2)],
         "nb_thin_pool.thin_quarter_pool": [round(float((p_any_nb(.25 * n, r) / p_any_nb(n, r)).min()), 2), round(float((p_any_nb(.25 * n, r) / p_any_nb(n, r)).max()), 2)]}
    if pln is not None:
        XGh, WGh = np.polynomial.hermite_e.hermegauss(60); WGh = WGh / WGh.sum()
        lam = (pln[0] * G[0])[:, None] * np.exp(pln[1] * XGh[None, :] - pln[1] ** 2 / 2)
        d["nb_thin_pool.p_any_offer_typical_under_500k"] = [round(float(p_any_nb(n[0], r).mean()), 2), round(float((1 - (np.exp(-lam) * WGh).sum(1)).mean()), 2)]
    return d


# ==================================================================================================================
def main():
    RES = {'name': 'buyer_factors', 'js_key': 'buyers', 'revision': 3,
           'decisions': ['mf_ind: the adding-up identity re-solved on the snapshot page as shipped (the trapezoid, ENG_SHARE 0.184); ship 0.97 '
                         'CALIBRATED; its se is sampling only, with the specification range and the per-size solutions stored beside it',
                         'eta (revision 3, analyst): the measured presence curve is NOT adopted (its ENG_SHARE effect depends on the construction, '
                         'it fits IBBA\'s offers by band worse, and the refit breaks the 2M-5M calibration pin); the window stays judgment at '
                         '[$0.6M, $3.2M]; ENG_SHARE stays 0.184; MODELS.fitted.competition unchanged except the strategic_premium.status text; '
                         'the evidence goes to eta_check; no competition_update ships',
                         'PHI .38 and the synergy pool stay judgment (the pool level is conditional on IND.strat): record the BCG checks',
                         'fix the code comment (Stanford 2026 median EBITDA $2.0M; Stanford 2024 $1.9M) and the strategic_premium.status string']}
    # ---------------------------------------------------------------- 0. sources
    transcription_checks()
    html = open(SNAP, encoding='utf-8').read()
    support = json.loads(re.search(r'"support":(\{"ern":\{[^}]*\})', html).group(1) + '}')['ern']
    eta_line = re.search(r'\{k:"eta".*', html).group(0)
    check('snapshot eta window', ETA_ROW in eta_line and html.count(ETA_ROW) == 1, eta_line.strip()[:110])
    ind_line = re.search(r'\{k:"ind".*', html).group(0)
    check('snapshot ind factor', IND_ROW in ind_line and html.count(IND_ROW) == 1, ind_line.strip()[:110])
    PHI_SHIPPED = float(re.search(r'\bPHI=(\.\d+)', html).group(1))
    COMP_LINE = [ln for ln in html.split('\n') if ln.startswith('MODELS.fitted.competition=')]
    assert len(COMP_LINE) == 1
    COMP_LINE = COMP_LINE[0] + '\n'
    COMP0 = json.loads(COMP_LINE.strip()[len('MODELS.fitted.competition='):-1])
    ENG0, ENG_SE0, NBR0 = COMP0['eng_share'], COMP0['eng_share_se'], COMP0['nb_r']
    for a_ in (OLD_COMMENT, OLD_HEADER, OLD_DATATAB, SIZEFIT_LINE):
        assert html.count(a_) == 1, a_[:60]
    assert COMP_LINE.count(STATUS_OLD) == 1 and html.count(STATUS_OLD) == 1, 'strategic_premium.status changed in the snapshot'
    assert sha(CPI) == CPI_SHA, 'the CPI file changed'

    # ---------------------------------------------------------------- 1. model probe for the identity
    lq = np.log([support[k] for k in ('p0_5', 'p1', 'p5', 'p50', 'p95', 'p99', 'p99_5')])
    pq = np.array([.005, .01, .05, .5, .95, .99, .995])
    grid = np.exp(np.linspace(lq[0], lq[-1], 161))
    P = run_probe({'mode': 'identity', 'sde': grid.tolist()}, 'identity')
    BUY = {b['k']: b for b in P['BUYERS']}; MF0 = {k: b['mf'] for k, b in BUY.items()}; SYN = {k: b['syn'] for k, b in BUY.items()}
    PHI = P['PHI']; IND = P['IND']; INDS = list(IND)
    check('PHI read from the snapshot', abs(PHI - PHI_SHIPPED) < 1e-12 and abs(PHI - 0.38) < 1e-12, 'PHI = %.2f' % PHI)
    check('ENG_SHARE read from the snapshot', abs(P['ENG_SHARE'] - ENG0) < 1e-12 and abs(ENG0 - 0.184) < 1e-12 and abs(ENG_SE0 - 0.027) < 1e-12,
          'ENG_SHARE %.3f (se %.3f), nb_r %.2f' % (ENG0, ENG_SE0, NBR0))
    wedge = wedge_fn(P['wedge']['S'], P['wedge']['D'])
    werr = max(abs(float(wedge(rev, n2)) - w) for n2, rev, w in P['wedge_test'])
    check('Python sdeEbitdaWedge = harness', werr < 1e-12, 'max |difference| %.1e over %d points' % (werr, len(P['wedge_test'])))
    rows = P['rows']; nR = len(rows)
    ern = np.array([r['ern'] for r in rows]); Vb = np.array([r['Vbase'] for r in rows]); X = np.array([r['x'] for r in rows])
    SF = {k: np.array([r['B'][k][0] for r in rows]) for k in BUY}; RAT = {k: np.array([r['B'][k][1] for r in rows]) for k in BUY}
    PEm = {k: np.array([r['B'][k][2] for r in rows]) for k in BUY}
    MIX = np.array([r['mix'] for r in rows])
    tr_id = float(np.max(np.abs(SF['eta'] - trap(ern, 6e5, 3.2e6))))
    check('mf_ind solved on the snapshot page as shipped (the search fund\'s trapezoid, ENG_SHARE 0.184)',
          BUY['eta']['lo'] == 6e5 and BUY['eta']['hi'] == 3.2e6 and tr_id < 1e-12 and abs(P['ENG_SHARE'] - ENG0) < 1e-12,
          'identity probe on the unpatched snapshot: eta window [%.0f, %.0f], eta sizeFit = the trapezoid to %.1e over %d rows; ENG_SHARE %.3f'
          % (BUY['eta']['lo'], BUY['eta']['hi'], tr_id, len(rows), P['ENG_SHARE']))

    def ratio(k, sf, mf=None, phi=None, pool=1.0):
        mf = MF0[k] if mf is None else mf; phi = PHI if phi is None else phi
        return 1 + (mf - 1) * sf + np.minimum(phi * SYN[k] * X * pool * sf, 0.40)
    rerr = max(float(np.max(np.abs(ratio(k, SF[k]) - RAT[k]))) for k in BUY)
    check('Vj/V formula = model', rerr < 1e-12, 'max |1+(mf-1)sf+min(PHI syn x sf,.4) - Vj/V| = %.1e over %d rows x 8 archetypes' % (rerr, nR))
    mixf, mmax = mix_fn(P['buyer_mix']['knots'])
    sf_py = np.minimum(1.0, mixf(Vb) / mmax)
    gi = {'ind': 0, 'str': 1, 'adj': 1, 'pep': 2, 'add': 2, 'fo': 2}
    serr = max(float(np.max(np.abs(sf_py[:, gi[k]] - SF[k]))) for k in GROUPED)
    merr = float(np.max(np.abs(mixf(Vb) - MIX)))
    check('buyerMix / MIX_MAX / sizeFit replica', serr < 1e-12 and merr < 1e-12, 'max |sizeFit diff| %.1e, |mix diff| %.1e' % (serr, merr))
    CR = ibba_complete_rows()
    kn0 = knots_from({b: np.round(CR[b].mean(0), 1) for b in BANDS})      # ibba_buyer_mix.py rounds the pooled shares to 0.1
    kerr = float(np.max(np.abs(np.round(np.array(kn0), 4) - np.array(P['buyer_mix']['knots']))))
    ns = [len(CR[b]) for b in BANDS]
    check('IBBA complete band-quarters reproduce buyer_mix', kerr < 1e-9 and ns == P['buyer_mix']['n_complete'],
          'knots equal to 4 decimals; n_complete %s' % ns)

    # BIZCOMPS weights: CDF linear in ln SDE through the published quantiles; each node carries its cell's mass
    lg = np.log(grid); mids = np.r_[lg[0], (lg[1:] + lg[:-1]) / 2, lg[-1]]

    def size_w(upper):
        hi_ = np.minimum(mids[1:], math.log(upper)); lo_ = mids[:-1]
        return np.where(hi_ > lo_, np.interp(hi_, lq, pq) - np.interp(lo_, lq, pq), 0.0)
    node = {e: i for i, e in enumerate(grid)}
    ni = np.array([node[e] for e in ern])
    W_P95, W_P99, W_FULL = size_w(support['p95'])[ni], size_w(support['p99'])[ni], size_w(support['p99_5'])[ni]

    def group_terms(sf, s_str_mult=1.0, mf=None, phi=None, pool=1.0, mbo=0.0, pe_weighted=False, mixm=None, pem=None):
        """per-row pieces: s_ind_eff, sf_ind, the rest of the identity (all but the ind term), the log ratios"""
        mf = dict(MF0, **(mf or {})); mixm = MIX if mixm is None else mixm; pem = PEm if pem is None else pem
        s_str = mixm[:, 1] * s_str_mult; s_fin = mixm[:, 2]; s_ind = 1 - s_str - s_fin
        L = {k: np.log(ratio(k, sf[k], mf[k], phi, pool)) for k in ('str', 'adj', 'pep', 'add', 'fo', 'mbo', 'eta')}
        if pe_weighted:
            def gm(ks):
                w = np.stack([np.maximum(pem[k], 1e-9) for k in ks]); return (w * np.stack([L[k] for k in ks])).sum(0) / w.sum(0)
        else:
            def gm(ks):
                return np.mean([L[k] for k in ks], 0)
        rest = s_str * gm(('str', 'adj')) + s_fin * gm(('pep', 'add', 'fo')) + s_ind * mbo * L['mbo']
        return s_ind * (1 - mbo), sf['ind'], rest, L

    def solve(W, terms, eta_in_ind=False, pem=None):
        s_i, sfi, rest, L = terms; pem = PEm if pem is None else pem
        if eta_in_ind:      # searchers counted among IBBA's individuals, engagement-weighted against ind
            pi, pe_ = np.maximum(pem['ind'], 1e-9), pem['eta']; a = pi / (pi + pe_)
            f = lambda m: float(np.sum(W * (s_i * (a * np.log(1 + (m - 1) * sfi) + (1 - a) * L['eta']) + rest)))
        else:
            f = lambda m: float(np.sum(W * (s_i * np.log(1 + (m - 1) * sfi) + rest)))
        return optimize.brentq(f, 0.3, 1.6, xtol=1e-12)

    def imbalance(W, terms, m):
        s_i, sfi, rest, _ = terms
        return float(np.sum(W * (s_i * np.log(1 + (m - 1) * sfi) + rest)) / np.sum(W))
    T0 = group_terms(SF)
    mf_c = solve(W_P95, T0)
    imb_shipped = imbalance(W_P95, T0, MF0['ind']); imb_097 = imbalance(W_P95, T0, 0.97)
    imb_full_097 = imbalance(W_FULL, T0, 0.97); imb_full_shipped = imbalance(W_FULL, T0, MF0['ind'])
    per_size = []
    for e in grid[::8]:
        m = ern == e; s_i, sfi, rest, _ = T0
        try:
            sol = optimize.brentq(lambda v: float(np.sum(s_i[m] * np.log(1 + (v - 1) * sfi[m]) + rest[m])), 0.05, 1.6)
        except ValueError:
            sol = float('nan')
        per_size.append(dict(sde=float(e), mf_ind_solution=sol, imbalance_at_097=float(np.mean(s_i[m] * np.log(1 + (0.97 - 1) * sfi[m]) + rest[m])),
                             s_ind=float(np.mean(MIX[m, 0])), sf_ind=float(np.mean(sfi[m])), bizcomps_mass_p95=float(size_w(support['p95'])[node[e]])))
    pd.DataFrame(per_size).to_csv(os.path.join(OUT, 'mf_ind_by_size.csv'), index=False)
    in_core = [r for r in per_size if support['p5'] <= r['sde'] <= support['p95']]
    econ = {
        'str_adj_1.25_1.20 (Pepperdine 2016 alone)': solve(W_P95, group_terms(SF, mf={'str': 1.25, 'adj': 1.20})),
        'str_adj_1.00 (no strategic mf premium)': solve(W_P95, group_terms(SF, mf={'str': 1.0, 'adj': 1.0})),
        'PHI_0.31 (BCG 2013)': solve(W_P95, group_terms(SF, phi=0.31)),
        'PHI_0.54 (BCG 2018)': solve(W_P95, group_terms(SF, phi=0.54)),
        'pool_x0.857 (BCG median level)': solve(W_P95, group_terms(SF, pool=BCG13_POOL_MEDIAN / 5.6)),
        'IBBA_strategic_share_x0.75': solve(W_P95, group_terms(SF, s_str_mult=0.75)),
        'IBBA_strategic_share_x1.25': solve(W_P95, group_terms(SF, s_str_mult=1.25)),
        'MBO_5pct_of_BIZCOMPS_at_0.86': solve(W_P95, group_terms(SF, mbo=0.05)),
        'MBO_5pct_of_BIZCOMPS_at_1.00': solve(W_P95, group_terms(SF, mbo=0.05, mf={'mbo': 1.0})),
    }
    sec = {"home": "23", "constr": "23", "medical": "62", "vet": "54", "msp": "54", "prof": "54", "ecom": "54", "saas": "51", "mfg": "31-33",
           "dist": "42", "staff": "56", "land": "56", "wash": "81", "auto": "81", "fit": "71", "rest": "72"}
    n2 = json.loads(re.search(r'"industry_n":(\{[^}]*\})', html).group(1))
    n2['31-33'] = n2['31'] + n2['32'] + n2['33']
    per_sec = Counter(sec.values())
    iw = np.array([n2[sec[r['ind']]] / per_sec[sec[r['ind']]] for r in rows])
    s_i, sfi, rest, _ = T0
    per_row = np.exp(-rest / s_i)          # the research's per-size solution with sizeFit_ind taken as 1
    mu_ln, sd_ln = math.log(support['p50']), (math.log(support['p95']) - math.log(support['p50'])) / 1.645
    w_ln = np.exp(-0.5 * ((np.log(ern) - mu_ln) / sd_ln) ** 2) * (ern <= 7e5)
    est = {
        'full_support_p0.5_p99.5': solve(W_FULL, T0),
        'support_to_p99': solve(W_P99, T0),
        'research_estimator (mean of per-size solutions, sizeFit_ind=1, lognormal weights, SDE<=$700k)': float(np.sum(w_ln * per_row) / np.sum(w_ln)),
        'engagement_weighted_within_groups': solve(W_P95, group_terms(SF, pe_weighted=True)),
        'industries_weighted_by_BIZCOMPS_sector_counts': solve(W_P95 * iw, T0),
        'searchers_counted_as_IBBA_individuals': solve(W_P95, T0, eta_in_ind=True),
    }
    RG = [5e4, 1e5, 1.5e5, 2e5, 3e5, 4e5, 5e5, 7e5]
    num = den = 0.0
    for r in run_probe({'mode': 'identity', 'sde': RG}, 'identity_research_grid')['rows']:
        B = r['B']; mx_ = r['mix']
        oth = mx_[1] * np.mean([math.log(B[k][1]) for k in ('str', 'adj')]) + mx_[2] * np.mean([math.log(B[k][1]) for k in ('pep', 'add', 'fo')])
        wgt = math.exp(-0.5 * ((math.log(r['ern']) - mu_ln) / sd_ln) ** 2)
        num += wgt * math.exp(-oth / mx_[0]); den += wgt
    research_rep = num / den
    check("research round's 0.968 reproduced on its own grid", abs(research_rep - 0.9677647545733685) < 1e-9,
          '%.6f (research adding_up_sens.py: 0.967765); the same estimator on the 161-point grid gives %.4f, the exact identity %.4f' % (
              research_rep, est['research_estimator (mean of per-size solutions, sizeFit_ind=1, lognormal weights, SDE<=$700k)'], mf_c))
    est['research_estimator_on_its_8_point_grid'] = research_rep
    boot = []
    for _ in range(B_MIX):
        means = {b: CR[b][RNG_MIX.integers(0, len(CR[b]), len(CR[b]))].mean(0) for b in BANDS}
        mf_b, mm_b = mix_fn(knots_from(means))
        mx = mf_b(Vb); sfb = np.minimum(1.0, mx / mm_b)
        sfd = dict(SF); sfd.update({k: sfb[:, gi[k]] for k in GROUPED})
        boot.append(solve(W_P95, group_terms(sfd, mixm=mx)))
    boot = np.array(boot); mf_se = float(boot.std(ddof=1)); mf_ci = np.percentile(boot, [2.5, 97.5]).tolist()
    P97 = run_probe({'mode': 'identity', 'sde': grid.tolist(), 'overrides': [[IND_ROW, IND_ROW.replace('mf:.90,', 'mf:.97,')]]}, 'identity_097')
    imb_model = 0.0
    for r, w in zip(P97['rows'], W_P95):
        m = r['mix']; B = r['B']
        imb_model += w * (m[0] * math.log(B['ind'][1]) + m[1] * np.mean([math.log(B[k][1]) for k in ('str', 'adj')])
                          + m[2] * np.mean([math.log(B[k][1]) for k in ('pep', 'add', 'fo')]))
    imb_model /= float(np.sum(W_P95))
    check('mf_ind 0.97 in the patched model', abs(imb_model - imb_097) < 1e-9 and abs(imb_model) < 0.005,
          'weighted mean log imbalance %+.4f from the model\'s own Vj (Python %+.4f); |.| < 0.005' % (imb_model, imb_097))
    check('mf_ind identity: shipped 0.90 is off balance', imb_shipped < -0.03,
          'weighted mean ln(price/V) at 0.90 = %+.4f (full support %+.4f)' % (imb_shipped, imb_full_shipped))
    note('mf_ind residual imbalance by size at 0.97 (BIZCOMPS p5-p95)',
         'buyer-type mean ln(price/V) runs %+.4f to %+.4f across SDE $35k-$728k (per-size solutions %.3f-%.3f): one factor cannot balance every size, '
         '0.97 balances the BIZCOMPS-weighted mean' % (min(r['imbalance_at_097'] for r in in_core), max(r['imbalance_at_097'] for r in in_core),
                                                         min(r['mf_ind_solution'] for r in in_core), max(r['mf_ind_solution'] for r in in_core)))
    print('mf_ind: raw %.4f (se %.4f, 95%% %.3f-%.3f); imbalance at .90 %+.4f, at .97 %+.4f' % (mf_c, mf_se, mf_ci[0], mf_ci[1], imb_shipped, imb_097), flush=True)

    # ---------------------------------------------------------------- 2. eta presence curve and the knot table
    fs = binned_ln_fit(SIG_FIG21_EDGES, np.array(SIG_FIG21) / 100 * SIG_N_ACQ)
    fr = binned_ln_fit(SIG_FIG20_EDGES, np.array(SIG_FIG20) / 100 * SIG_N_ACQ)
    m_sf = math.exp(fs[0]) / math.exp(fr[0])
    C23 = np.array([[SIG_N_ACQ * wE / 100 * s_ / sum(sh) for s_ in sh] for sh, wE in zip(SIG_FIG23, SIG_FIG23_EBITDA_W)])
    th_j = joint_fit(C23, np.array([fs[0], math.log(fs[1]), math.log(3.6), 0.2, math.log(0.35)]))
    cov_j = hessian_cov(lambda t: joint_nll(t, C23), th_j)
    b_hat, s_hat = th_j[3], math.exp(th_j[4]); b_se = math.sqrt(cov_j[3, 3])
    f26 = binned_ln_fit(ST26_PRICE_EDGES, np.array(ST26_PRICE) / 100 * ST26_N_PRICE)
    fie = binned_ln_fit(IESE_PRICE_EDGES, np.array(IESE_PRICE) / 100 * IESE_N_PRICE)
    s24 = pd.read_csv(ST24_CSV)
    get24 = lambda metric, stat: float(s24[(s24.metric == metric) & (s24.stat == stat)].value.iloc[0])
    st24_bins = [get24('purchase_price_share_<$4M', '% of acquisitions'), get24('purchase_price_share_$4M-$8M', '% of acquisitions'),
                 get24('purchase_price_share_$8M-$12M', '% of acquisitions'), float(s24[s24.metric.str.startswith('purchase_price_share_>$12M')].value.iloc[0])]
    st24_med = float(s24[(s24.metric == 'ebitda_at_purchase_usd_m') & (s24.stat == 'median') & (s24.cohort == 'All')].value.iloc[0])
    st24_marg = float(s24[(s24.table.str.startswith('Exhibit 6 additional')) & (s24.metric == 'ebitda_margin_pct') & (s24.stat == 'median')].value.iloc[0]) / 100
    check('Stanford 2024 median EBITDA (local table)', abs(st24_med - 1.9) < 1e-9, 'all acquisitions 1984-2023: $%.1fM (the comment said $1.6M)' % st24_med)
    f24 = binned_ln_fit([4.0, 8.0, 12.0], np.array(st24_bins) / 100 * 268)
    sE26, sEie, sE24 = sigma_E(f26[1], b_hat, s_hat), sigma_E(fie[1], b_hat, s_hat), sigma_E(f24[1], b_hat, s_hat)
    fits = {
        'sig_acquired_ebitda': dict(median_m=math.exp(fs[0]), sigma=fs[1], chi2_dof=chi2_fit(SIG_FIG21_EDGES, np.array(SIG_FIG21) / 100 * SIG_N_ACQ, fs[0], fs[1], 2)),
        'sig_acquired_revenue': dict(median_m=math.exp(fr[0]), sigma=fr[1], chi2_dof=chi2_fit(SIG_FIG20_EDGES, np.array(SIG_FIG20) / 100 * SIG_N_ACQ, fr[0], fr[1], 2)),
        'sig_margin_median_ratio': m_sf,
        'sig_joint_multiple_on_ebitda': dict(b=b_hat, b_se=b_se, s=s_hat, a=th_j[2], muE=th_j[0], sE=math.exp(th_j[1]),
                                             note='ln multiple = a + b ln EBITDA($M) + e, e ~ N(0, s); binned MLE on Fig 23 x Fig 21'),
        'stanford2026_price': dict(median_m=math.exp(f26[0]), sigma=f26[1], chi2_dof=chi2_fit(ST26_PRICE_EDGES, np.array(ST26_PRICE) / 100 * ST26_N_PRICE, f26[0], f26[1], 2), sigma_E=sE26),
        'iese2024_price': dict(median_m=math.exp(fie[0]), sigma=fie[1], sigma_E=sEie),
        'stanford2024_price': dict(median_m=math.exp(f24[0]), sigma=f24[1], sigma_E=sE24, bins=st24_bins, median_ebitda_m=st24_med, margin=st24_marg),
    }
    print('SIG: EBITDA median $%.2fM sd %.2f; margin %.3f; joint b %.3f (se %.3f) s %.3f; Stanford 2026 price sd %.2f -> sigma_E %.3f'
          % (math.exp(fs[0]), fs[1], m_sf, b_hat, b_se, s_hat, f26[1], sE26), flush=True)
    E6 = 1e6
    base_kw = dict(shares=SIG_FIG7, m_sf=m_sf, medE=ST26_MED_EBITDA * E6, sE=sE26, m_tr=ST26_MED_MARGIN, w=W_SF, wedge=wedge)
    c0 = presence(**base_kw)
    lo_c, hi_c, pk_c = half_window(c0)
    KN = knot_table(c0)
    KY = np.array([k[1] for k in KN])
    kl_c, kh_c = knot_halfmax(KY)
    # variants: the step curve's half-max window (round 1) and the knot table each variant would give
    VAR_KW = {'w=0.8': dict(w=0.8), 'w=0.67': dict(w=0.67), 'w=1 (self-funded only)': dict(w=1.0), 'w=0.5': dict(w=0.5),
              'wedge 1.2 flat': dict(wov=1.2), 'traditional = IESE 2024': dict(medE=IESE_MED_EBITDA * E6, sE=sEie, m_tr=IESE_MED_MARGIN),
              'traditional = Stanford 2024': dict(medE=st24_med * E6, sE=sE24, m_tr=st24_marg),
              'traditional margin 0.25 (research)': dict(m_tr=0.25), 'traditional = Stanford 2024-25 cohort ($2.5M)': dict(medE=ST26_MED_EBITDA_2425 * E6, m_tr=ST26_MARGIN_2425),
              'SIG shares interpolated (smooth)': dict(smooth=True),
              'acquired size (SIG Fig 21 density in place of targets)': dict(acq=(fs[0], fs[1]))}
    variants, var_knots = {}, {}
    for lab, kw in VAR_KW.items():
        a = dict(base_kw); a.update(kw); cv = presence(**a)
        variants[lab] = half_window(cv); var_knots[lab] = knot_table(cv)
    # revision 3, the dollar-basis caveat: SIG's targets are in 2023 dollars and Stanford's median mixes 1984-2025 dollars, yet the
    # knot table reads them as 2026 dollars. Read in 2026 dollars (CPI-U, Feb-Aug 2026 mean over the 2023 average), the whole
    # curve moves right by that factor: presence at SDE x is the 2026-dollar reading c(x / INF).
    cpi_ = pd.read_csv(CPI, parse_dates=['observation_date'])
    CPI_26 = float(cpi_[cpi_.observation_date >= '2026-02-01'].CPIAUCNS.mean()); CPI_23 = float(cpi_[cpi_.observation_date.dt.year == 2023].CPIAUCNS.mean())
    INF = CPI_26 / CPI_23
    DB_LAB = 'dollar basis: SIG and Stanford read in 2026 dollars'
    c_inf = np.interp(XS / INF, XS, c0, left=0.0, right=float(c0[-1]))
    variants[DB_LAB] = half_window(c_inf); var_knots[DB_LAB] = knot_table(c_inf)
    KY_INF = np.array([k[1] for k in var_knots[DB_LAB]])
    kl_inf, kh_inf = knot_halfmax(KY_INF)
    # revision 3, the step-function caveat: SIG's EBITDA bin edges and the end of the judgment ramp, mapped to SDE at the self-funded margin
    # (the same mapping the curve uses); a knot near an edge reads the step at a step, and the bootstrap SEs do not cover where it falls
    edge_ebitda = list(SIG_FIG7_EDGES) + [LOW_RAMP[1]]
    edge_sde = [float(E * wedge(np.array([E / m_sf]))[0]) for E in edge_ebitda]
    edge_lab = ['SIG bin edge EBITDA $%.2fM' % (E / 1e6) for E in SIG_FIG7_EDGES] + ['end of the judgment ramp, EBITDA $%.2fM' % (LOW_RAMP[1] / 1e6)]
    near_edges = []
    for xk in KNOT_SDE:
        jk = int(np.argmin([abs(math.log(xk / e)) for e in edge_sde]))
        dist = xk / edge_sde[jk] - 1
        if abs(dist) <= 0.05:
            near_edges.append(dict(knot_sde_m=xk / 1e6, edge_sde_m=edge_sde[jk] / 1e6, edge=edge_lab[jk], distance_pct=100 * dist))
    # the research round's knot table (out/eta_knots.json) against this one
    RK = json.load(open(RESEARCH_KNOTS))
    rk = np.array(RK['w0.9_wedgeconsole']['knots_lnSDE_presence']); rk8 = np.array(RK['w0.8_wedgeconsole']['knots_lnSDE_presence'])
    rk_dx = float(np.max(np.abs(rk[:, 0] - np.array([k[0] for k in KN]))))
    rk_dy = np.abs(rk[:, 1] - KY); rk_dy_i = int(np.argmax(rk_dy))
    rk_m25 = np.array([k[1] for k in var_knots['traditional margin 0.25 (research)']])
    a_r = dict(base_kw); a_r.update(m_tr=0.25, ge=GE_R, xs=XS_R)
    rk_rep = np.round(np.interp(KNOT_SDE, XS_R, presence(**a_r)), 3)          # the research's construction: its grids, 25% margin
    a_r.update(w=0.8); rk8_rep = np.round(np.interp(KNOT_SDE, XS_R, presence(**a_r)), 3)
    rk_rep_err = max(float(np.max(np.abs(rk[:, 1] - rk_rep))), float(np.max(np.abs(rk8[:, 1] - rk8_rep))))
    check('knot table reproduces the research round\'s (out/eta_knots.json, w0.9 console wedge)', rk_dx < 1e-9 and float(rk_dy.max()) <= 0.02 and rk_rep_err <= 0.0011,
          'same 15 ln SDE knots; the research\'s construction (its 1,500 x 2,000-point grids, traditional margin 25%%) is reproduced to %.3f (w = 0.9 and 0.8). '
          'The shipped table (finer grids, Stanford 2026\'s 23%% margin) differs by at most %.3f, at $%.1fM (%.3f here, %.3f there): that knot sits on a SIG '
          'bin edge, where a coarse grid interpolates across the step; margin alone moves it by %.3f'
          % (rk_rep_err, rk_dy.max(), KNOT_SDE[rk_dy_i] / E6, KY[rk_dy_i], rk[rk_dy_i, 1], float(np.max(np.abs(KY - rk_m25)))))
    # acquired-size reading
    zq = stats.norm.ppf([0.25, 0.75])

    def acquired_iqr(w):
        xs = np.exp(np.linspace(math.log(5e4), math.log(4e7), 4000))
        sde_sf = GE * wedge(GE / m_sf); sde_tr = GE * wedge(GE / ST26_MED_MARGIN)
        F_sf = np.interp(xs, sde_sf, stats.norm.cdf((np.log(GE / E6) - fs[0]) / fs[1]), left=0, right=1)
        F_tr = np.interp(xs, sde_tr, stats.norm.cdf((np.log(GE / E6) - math.log(ST26_MED_EBITDA)) / sE26), left=0, right=1)
        F = w * F_sf + (1 - w) * F_tr
        return [float(np.interp(q, F, xs)) for q in (0.25, 0.5, 0.75)]
    acq = acquired_iqr(W_SF)
    # bootstrap (round 1's draws, in the same order): step-curve window, smooth window, knot table and its own half-max
    p7 = np.array(SIG_FIG7) / 100; p20 = np.array(SIG_FIG20) / sum(SIG_FIG20); p21 = np.array(SIG_FIG21) / sum(SIG_FIG21)
    pC = (C23 / C23.sum()).ravel(); p26 = np.array(ST26_PRICE) / sum(ST26_PRICE)
    bl, bh, bpk, bsm, bkn, bkl, bkh = [], [], [], [], [], [], []
    for _ in range(B_WIN):
        sh = RNG_WIN.binomial(SIG_N_RESP, p7) / SIG_N_RESP
        if sh.max() <= 0:
            continue
        fs_b = binned_ln_fit(SIG_FIG21_EDGES, RNG_WIN.multinomial(SIG_N_ACQ, p21))
        fr_b = binned_ln_fit(SIG_FIG20_EDGES, RNG_WIN.multinomial(SIG_N_ACQ, p20))
        Cb = RNG_WIN.multinomial(SIG_N_ACQ, pC).reshape(4, 4).astype(float)
        thb = joint_fit(Cb, th_j)
        f26b = binned_ln_fit(ST26_PRICE_EDGES, RNG_WIN.multinomial(ST26_N_PRICE, p26))
        sEb = sigma_E(f26b[1], thb[3], math.exp(thb[4]))
        medb = ST26_MED_EBITDA * math.exp(RNG_WIN.normal(0, 1.2533 * sEb / math.sqrt(ST26_N_PRICE)))
        mb = math.exp(fs_b[0]) / math.exp(fr_b[0])
        cb = presence(sh, mb, medb * E6, sEb, ST26_MED_MARGIN, W_SF, wedge)
        l_, h_, k_ = half_window(cb)
        ls_, hs_, _ = half_window(presence(sh, mb, medb * E6, sEb, ST26_MED_MARGIN, W_SF, wedge, smooth=True))
        kb = knots_of(cb); kl_, kh_ = knot_halfmax(kb)
        bl.append(l_); bh.append(h_); bpk.append(k_); bsm.append((ls_, hs_)); bkn.append(kb); bkl.append(kl_); bkh.append(kh_)
    bl, bh, bsm, bkn, bkl, bkh = np.array(bl), np.array(bh), np.array(bsm), np.array(bkn), np.array(bkl), np.array(bkh)
    lo_se, hi_se = float(bl.std(ddof=1)), float(bh.std(ddof=1))
    sm_se = bsm.std(0, ddof=1)
    kl_se, kh_se = float(bkl.std(ddof=1)), float(bkh.std(ddof=1))
    knot_se = bkn.std(0, ddof=1)
    knot_ci = np.percentile(bkn, [2.5, 97.5], axis=0)
    print('eta presence: step-curve half-max $%.3fM (se %.3f) - $%.3fM (se %.3f); knot table half-max $%.3fM (se %.3f) - $%.3fM (se %.3f); peak $%.2fM'
          % (lo_c / E6, lo_se / E6, hi_c / E6, hi_se / E6, kl_c / E6, kl_se / E6, kh_c / E6, kh_se / E6, pk_c / E6), flush=True)
    print('knots:', KN, flush=True)
    rd = round
    rob = {k: ((variants[k][0] - lo_c) / lo_se, (variants[k][1] - hi_c) / hi_se) for k in
           ('w=0.8', 'wedge 1.2 flat', 'traditional = IESE 2024', 'traditional = Stanford 2024', 'traditional margin 0.25 (research)', 'SIG shares interpolated (smooth)')}
    data_keys = [k for k in rob if k != 'w=0.8']
    check('presence curve robust to data choices (traditional source and margin, smooth reading, wedge 1.2): each half-max end moves < 1.5 se',
          all(abs(rob[k][0]) < 1.5 and abs(rob[k][1]) < 1.5 for k in data_keys), '; '.join('%s %+.2f/%+.2f se' % (k, rob[k][0], rob[k][1]) for k in data_keys))
    note('presence curve and the judgment weight w', 'w=0.8 moves the step curve\'s half presence to $%.2fM-$%.2fM (%+.2f / %+.2f se) and the knots by up to %.3f; '
         'what that does to ENG_SHARE is in eta_effect.variants' % (variants['w=0.8'][0] / E6, variants['w=0.8'][1] / E6, rob['w=0.8'][0], rob['w=0.8'][1],
                                                                     float(np.max(np.abs(np.array([k[1] for k in var_knots['w=0.8']]) - KY)))))
    check('step curve reproduces round 1 (same draws)', abs(lo_c / 773765.0 - 1) < 1e-5 and abs(hi_c / 3276610.0 - 1) < 1e-5
          and (QUICK or (abs(lo_se / 143222.0 - 1) < 1e-5 and abs(hi_se / 214906.0 - 1) < 1e-5)),
          'half-max $%.0f-$%.0f (round 1 $773,765-$3,276,610), se %.0f / %.0f (round 1 143,222 / 214,906)' % (lo_c, hi_c, lo_se, hi_se))
    # like for like with the shipped trapezoid
    t_lo, t_hi = 0.575 * 6e5, 1.8 * 3.2e6
    trap_vs = dict(shipped_halfmax=[t_lo, t_hi], in_se_of_knot_halfmax=[(t_lo - kl_c) / kl_se, (t_hi - kh_c) / kh_se],
                   in_se_of_step_halfmax=[(t_lo - lo_c) / lo_se, (t_hi - hi_c) / hi_se],
                   presence_at_0_6M=[float(trap([6e5], 6e5, 3.2e6)[0]), float(lerp_knots([6e5], KN)[0])],
                   presence_at_5M=[float(trap([5e6], 6e5, 3.2e6)[0]), float(lerp_knots([5e6], KN)[0])])
    ls_lo, ls_hi, ls_r2 = ls_trapezoid(c0)
    check('shipped trapezoid is outside the measured half-presence band like for like (the critique)', trap_vs['in_se_of_knot_halfmax'][0] < -2 and trap_vs['in_se_of_knot_halfmax'][1] > 2,
          'trapezoid half presence $%.3fM / $%.2fM vs knot table $%.3fM / $%.2fM (%.1f / %+.1f se; step curve %.1f / %+.1f se); presence at $0.6M %.2f vs %.2f, '
          'at $5M %.2f vs %.2f; best least-squares trapezoid with the code\'s ramps: plateau $%.2fM-$%.2fM, R2 %.2f'
          % (t_lo / E6, t_hi / E6, kl_c / E6, kh_c / E6, trap_vs['in_se_of_knot_halfmax'][0], trap_vs['in_se_of_knot_halfmax'][1],
             trap_vs['in_se_of_step_halfmax'][0], trap_vs['in_se_of_step_halfmax'][1], trap_vs['presence_at_0_6M'][0], trap_vs['presence_at_0_6M'][1],
             trap_vs['presence_at_5M'][0], trap_vs['presence_at_5M'][1], ls_lo / E6, ls_hi / E6, ls_r2))
    check('knot table half presence within 1 se of the step curve it samples', abs(kl_c - lo_c) < max(lo_se, kl_se) and abs(kh_c - hi_c) < max(hi_se, kh_se),
          'knots $%.3fM-$%.3fM vs step curve $%.3fM-$%.3fM (the 15 knots smooth the SIG bin steps; the smooth reading gives $%.2fM-$%.2fM)'
          % (kl_c / E6, kh_c / E6, lo_c / E6, hi_c / E6, variants['SIG shares interpolated (smooth)'][0] / E6, variants['SIG shares interpolated (smooth)'][1] / E6))
    wE_sde = float(ST26_MED_EBITDA * E6 * wedge(ST26_MED_EBITDA * E6 / ST26_MED_MARGIN))
    wE_sde_2425 = float(ST26_MED_EBITDA_2425 * E6 * wedge(ST26_MED_EBITDA_2425 * E6 / ST26_MARGIN_2425))
    check('Stanford 2026 median deal inside the knot table\'s half-presence band', kl_c <= wE_sde <= kh_c,
          'median EBITDA $2.0M = $%.2fM of SDE at the console wedge (2024-25: $%.2fM) vs [%.2f, %.2f]' % (wE_sde / E6, wE_sde_2425 / E6, kl_c / E6, kh_c / E6))
    note('presence against the acquired-size range', 'interquartile SDE of what searchers bought (same mixture, w=0.9): $%.2fM-$%.2fM (median $%.2fM); '
         'the targeting curve\'s half presence $%.2fM-$%.2fM' % (acq[0] / E6, acq[2] / E6, acq[1] / E6, kl_c / E6, kh_c / E6))
    PTS = [1e5, 1.5e5, 2.5e5, 4e5, 6e5, 8e5, 1e6, 1.5e6, 2e6, 2.5e6, 3e6, 4e6, 5e6, 7e6, 1e7, 1.5e7, 3e7]
    curve = pd.DataFrame(dict(sde=PTS, measured_step_curve=np.interp(PTS, XS, c0), knot_table=lerp_knots(PTS, KN), shipped_trapezoid=trap(PTS, 6e5, 3.2e6),
                              knots_w08=lerp_knots(PTS, var_knots['w=0.8']), knots_smooth=lerp_knots(PTS, var_knots['SIG shares interpolated (smooth)']),
                              knots_acquired=lerp_knots(PTS, var_knots['acquired size (SIG Fig 21 density in place of targets)']),
                              knots_wedge12=lerp_knots(PTS, var_knots['wedge 1.2 flat'])))
    curve.to_csv(os.path.join(OUT, 'eta_presence_curve.csv'), index=False)
    pd.DataFrame(dict(sde=KNOT_SDE, ln_sde=[k[0] for k in KN], presence=KY, se=knot_se, ci95_lo=knot_ci[0], ci95_hi=knot_ci[1],
                      research=rk[:, 1], w08=[k[1] for k in var_knots['w=0.8']], smooth=[k[1] for k in var_knots['SIG shares interpolated (smooth)']],
                      acquired=[k[1] for k in var_knots['acquired size (SIG Fig 21 density in place of targets)']],
                      shipped_trapezoid=trap(KNOT_SDE, 6e5, 3.2e6))).to_csv(os.path.join(OUT, 'eta_knots.csv'), index=False)

    # ---------------------------------------------------------------- 3. what the knot table does
    STUB = 'MODELS.fitted.buyers=' + json.dumps({"eta_presence": {"knots": KN}}, separators=(',', ':')) + ';'
    stub_for = lambda K: 'MODELS.fitted.buyers=' + json.dumps({"eta_presence": {"knots": K}}, separators=(',', ':')) + ';'
    PAGE_KNOTS = build_page('index_eta_knots.html', [(COMP_LINE, COMP_LINE + STUB + '\n'), (ETA_ROW, ETA_ROW_KNOTS), (SIZEFIT_LINE, SIZEFIT_LINE + SIZEFIT_KNOTS)])
    prepare_cb()
    h_snap = start_cb('snapshot', SNAP)              # the two ENG_SHARE calibrations run in the background
    h_knots = start_cb('eta_knots', PAGE_KNOTS)
    chk_sde = sorted(set(KNOT_SDE + [float(math.exp((a + b) / 2)) for a, b in zip(LNK[:-1], LNK[1:])] + [5e4, 1e5, 1.2e5, 2e7, 5e7]))
    KC = run_probe({'mode': 'knotcheck', 'page': PAGE_KNOTS, 'sde': chk_sde, 'inds': ['home', 'rest', 'saas']}, 'knotcheck')
    KC0 = run_probe({'mode': 'knotcheck', 'sde': chk_sde, 'inds': ['home', 'rest', 'saas']}, 'knotcheck_snapshot')
    kc_err = max(abs(r[2] - float(lerp_knots([r[1]], KN)[0])) for r in KC['rows'])
    tr_err = max(abs(r[2] - float(trap([r[1]], 6e5, 3.2e6)[0])) for r in KC0['rows'])
    mbo_same = max(abs(a[3] - b[3]) for a, b in zip(KC['rows'], KC0['rows']))
    check('knot page: the model reads the knot table', KC['knots'] == KN and KC['eta_lo'] is None and KC['eta_hi'] is None and kc_err < 1e-12 and tr_err < 1e-12
          and mbo_same == 0 and KC['mbo'] == KC0['mbo'] and KC['eng_share'] == ENG0,
          'eta sizeFit = lerpKnots(ln SDE) to %.1e at %d SDE x 3 industries (the snapshot\'s = the trapezoid to %.1e); MBO window unchanged %s; ENG_SHARE %.3f'
          % (kc_err, len(chk_sde), tr_err, KC['mbo'], KC['eng_share']))
    # effect probe: the snapshot, the knot page, and the variants' band centres
    runs = [{'tag': 'snapshot', 'page': None, 'grid': True}, {'tag': 'knots', 'page': PAGE_KNOTS, 'grid': True}]
    VAR_RUN = {'w=0.8': 'w0.8', 'SIG shares interpolated (smooth)': 'smooth', 'wedge 1.2 flat': 'wedge1.2',
               'acquired size (SIG Fig 21 density in place of targets)': 'acquired', 'traditional margin 0.25 (research)': 'research_margin',
               DB_LAB: 'dollar_basis_2026'}
    for lab, tag in VAR_RUN.items():
        runs.append({'tag': tag, 'page': PAGE_KNOTS, 'overrides': [[STUB, stub_for(var_knots[lab])]], 'grid': False})
    lo_r, hi_r = round(lo_c / 1e4) * 1e4, round(hi_c / 1e4) * 1e4
    runs.append({'tag': 'trapezoid_at_step_halfmax', 'page': None, 'overrides': [[ETA_WIN, 'syn:.04, mf:.98, lo:%d,  hi:%d,' % (lo_r, hi_r)]], 'grid': False})
    EF = run_probe({'mode': 'effect', 'sde': EFFECT_SDE, 'band_V': VC, 'runs': runs}, 'effect')
    o = load_offers()
    Gm = {}
    rep = {}
    for tag, rr in EF['runs'].items():
        Bd = pd.DataFrame(rr['bands']); Gm[tag] = Bd.pivot_table(index='b', columns='ind', values='g').sort_index().values
        rep[tag] = fit_m5(o, Gm[tag].mean(1))
    g0 = pd.DataFrame(EF['runs']['snapshot']['grid']); g1 = pd.DataFrame(EF['runs']['knots']['grid'])
    mg = g0.merge(g1, on=['ind', 'ern'], suffixes=('_s', '_k'))
    mg['rel'] = mg.peRef_k / mg.peRef_s - 1
    # the eta term alone explains the change: (1/8) x sig(1.35 (fit0_eta - .72)) x 0.775 x delta sizeFit
    k_eta = 1 / (1 + math.exp(-1.35 * ((.55 + .5 * .5 + .5 * .5) - .72))) * 0.775 / 8
    pr_err = float(np.max(np.abs((mg.peRef_k - mg.peRef_s) - k_eta * (mg.sf_eta_k - mg.sf_eta_s))))
    check('peRef change is the eta term alone', pr_err < 1e-12, 'max |delta peRef - (1/8)(0.775)sig(1.35(1.05-.72)) delta sizeFit_eta| = %.1e over %d rows' % (pr_err, len(mg)))
    by_sde = mg.groupby('ern').agg(sf_eta_trapezoid=('sf_eta_s', 'mean'), sf_eta_knots=('sf_eta_k', 'mean'), peRef_trapezoid=('peRef_s', 'mean'),
                                   peRef_knots=('peRef_k', 'mean'), rel_mean=('rel', 'mean'), rel_min=('rel', 'min'), rel_max=('rel', 'max')).reset_index()
    by_sde.to_csv(os.path.join(OUT, 'eta_effect_by_sde.csv'), index=False)
    at = by_sde.set_index('ern')
    rep_rows = at.loc[REPORT_SDE]
    imax = int(np.argmax(np.abs(mg.rel.values)))

    # the ENG_SHARE calibration with the snapshot's fit/competition_buyers.py: control (snapshot) and the knot page
    CBS = finish_cb(h_snap); CBK = finish_cb(h_knots)
    spec0 = (COMP0['eng_share_spec_range'], COMP0['nb_r_spec_range'], COMP0['eng_share_spec_n'], COMP0['eng_share_pln'])
    ok_ctrl = (round(CBS['eng_share'], 3) == ENG0 and round(CBS['nb_r'], 2) == NBR0 and (QUICK or (round(CBS['eng_share_se'], 3) == ENG_SE0
               and [round(x, 3) for x in CBS['eng_share_ci95']] == COMP0['eng_share_ci95'] and round(CBS['nb_r_se'], 2) == COMP0['nb_r_se']
               and [round(x, 2) for x in CBS['nb_r_ci95']] == COMP0['nb_r_ci95']))
               and [round(x, 3) for x in CBS['eng_share_spec_range']] == spec0[0] and [round(x, 2) for x in CBS['nb_r_spec_range']] == spec0[1]
               and CBS['eng_share_spec_n'] == spec0[2] and round(CBS['pln']['c'], 3) == spec0[3]['c'] and round(CBS['pln']['se'], 3) == spec0[3]['se']
               and round(CBS['pln']['log_sd'], 2) == spec0[3]['log_sd'])
    check('copied fit/competition_buyers.py on the snapshot reproduces MODELS.fitted.competition', ok_ctrl,
          'ENG_SHARE %.5f (se %.4f, 95%% %.3f-%.3f), nb_r %.4f (se %.2f, %.2f-%.2f); NB specification range %.3f-%.3f over %d, nb_r %.2f-%.2f; PLN %.3f (se %.3f, log-sd %.2f); '
          'shipped 0.184 (0.027, 0.13-0.226), 1.07 (0.55, 0.4-2.86), 0.164-0.201 over 9, 0.82-1.9, 0.21 (0.015, 0.78); %d bootstrap draws'
          % (CBS['eng_share'], CBS['eng_share_se'], CBS['eng_share_ci95'][0], CBS['eng_share_ci95'][1], CBS['nb_r'], CBS['nb_r_se'], CBS['nb_r_ci95'][0], CBS['nb_r_ci95'][1],
             CBS['eng_share_spec_range'][0], CBS['eng_share_spec_range'][1], CBS['eng_share_spec_n'], CBS['nb_r_spec_range'][0], CBS['nb_r_spec_range'][1],
             CBS['pln']['c'], CBS['pln']['se'], CBS['pln']['log_sd'], CBS['n_boot']))
    gerr = max(float(np.max(np.abs(np.array(CBS['g_b']) - Gm['snapshot'].mean(1)))), float(np.max(np.abs(np.array(CBK['g_b']) - Gm['knots'].mean(1)))))
    Gk_cb = np.array(CBK['G']); inds_sorted = sorted(INDS)
    gerr2 = float(np.max(np.abs(Gk_cb - pd.DataFrame(EF['runs']['knots']['bands']).pivot_table(index='b', columns='ind', values='g').sort_index()[CBK['G_industries']].values)))
    rerr_c = max(abs(rep['snapshot'][0] - CBS['eng_share']), abs(rep['knots'][0] - CBK['eng_share']))
    check('replica M5 = the copied script', gerr < 1e-9 and gerr2 < 1e-9 and rerr_c < 1e-5 and CBK['G_industries'] == inds_sorted,
          'g_b equal to %.1e (16 x 5 g to %.1e); ENG_SHARE equal to %.1e (snapshot %.5f, knots %.5f)' % (gerr, gerr2, rerr_c, rep['snapshot'][0], rep['knots'][0]))
    d_eng = CBK['eng_share'] - CBS['eng_share']; d_in_se = d_eng / ENG_SE0
    # revision 3 (analyst): the knot table is NOT adopted, so nothing is refitted. The rule (refit if the shift exceeds half
    # the se) is evaluated only to record what adoption would have required.
    rule_refit = bool(abs(d_eng) > 0.5 * ENG_SE0)
    eng_if = round(CBK['eng_share'], 3); nbr_if = round(CBK['nb_r'], 2)        # the refit adoption would have required
    var_eng = {tag: dict(eng_share=rep[tag][0], nb_r=rep[tag][1], shift=rep[tag][0] - rep['snapshot'][0], shift_in_se=(rep[tag][0] - rep['snapshot'][0]) / ENG_SE0,
                         rule_says_refit=bool(abs(rep[tag][0] - rep['snapshot'][0]) > 0.5 * ENG_SE0)) for tag in rep}
    KNOT_CONSTRUCTIONS = ['knots', 'w0.8', 'smooth', 'research_margin', 'wedge1.2', 'acquired', 'dollar_basis_2026']
    shift_rng = [min(var_eng[t]['shift_in_se'] for t in KNOT_CONSTRUCTIONS if t != 'dollar_basis_2026'),
                 max(var_eng[t]['shift_in_se'] for t in KNOT_CONSTRUCTIONS if t != 'dollar_basis_2026')]
    note('ENG_SHARE if the knot table were adopted (not adopted; the analyst\'s rule recorded)',
         'knot page %.4f vs snapshot %.4f: shift %+.4f = %+.2f x se %.3f; the rule would %s (to %.3f, se %.3f); ENG_SHARE stays %.3f'
         % (CBK['eng_share'], CBS['eng_share'], d_eng, d_in_se, ENG_SE0, 'refit' if rule_refit else 'keep', eng_if, CBK['eng_share_se'], ENG0))
    note('ENG_SHARE shift by construction of the presence curve (replica M5; se 0.027)',
         'central %+.2f, w=0.8 %+.2f, smooth %+.2f, research margin %+.2f, wedge 1.2 %+.2f, acquired size %+.2f: %+.2f to %+.2f se over the knot-table '
         'constructions; read in 2026 dollars %+.2f; the round-1 trapezoid at the step curve\'s half-max ($%.2fM-$%.2fM) %+.2f'
         % (var_eng['knots']['shift_in_se'], var_eng['w0.8']['shift_in_se'], var_eng['smooth']['shift_in_se'], var_eng['research_margin']['shift_in_se'],
            var_eng['wedge1.2']['shift_in_se'], var_eng['acquired']['shift_in_se'], shift_rng[0], shift_rng[1], var_eng['dollar_basis_2026']['shift_in_se'],
            lo_r / E6, hi_r / E6, var_eng['trapezoid_at_step_halfmax']['shift_in_se']))
    lr0, lrk = CBS['lr_M5_vs_M2'], CBK['lr_M5_vs_M2']
    qd = COMP0['quasi_dispersion']
    # offers per closed deal by band, the calibration moment: the snapshot, the knots at 0.184, and the knots at the refit adoption would require
    bf = COMP0['offers_per_closed_deal_bandfree_fit']; bfse = COMP0['offers_per_closed_deal_bandfree_se']; lb = COMP0['offers_per_closed_deal_lower_bound']
    zt_s = zt_mean(ENG0 * Gm['snapshot'], NBR0).mean(1); zt_k = zt_mean(ENG0 * Gm['knots'], NBR0).mean(1); zt_kr = zt_mean(CBK['eng_share'] * Gm['knots'], CBK['nb_r']).mean(1)
    chi_s = float(sum(((a - bf[b]) / bfse[b]) ** 2 for a, b in zip(zt_s, BANDS))); chi_k = float(sum(((a - bf[b]) / bfse[b]) ** 2 for a, b in zip(zt_kr, BANDS)))
    pins = {b: dict(ibba_lower_bound=lb[b], snapshot=float(zt_s[i]), knots_at_refit=float(zt_kr[i]), knots_at_0184=float(zt_k[i]),
                    snapshot_inside=bool(abs(zt_s[i] - lb[b]) <= ENG_PINS_TOL), knots_at_refit_inside=bool(abs(zt_kr[i] - lb[b]) <= ENG_PINS_TOL))
            for i, b in enumerate(BANDS)}
    pins_broken = [b for b in BANDS if pins[b]['snapshot_inside'] and not pins[b]['knots_at_refit_inside']]
    note('fit of the console size gradient to IBBA\'s bands (M5 vs free band means, 4 df)', 'LR %.2f (p %.3f) on the snapshot, %.2f (p %.3f) with the knot table '
         '(with quarter dependence, LR / %.1f-%.1f: p %.2f-%.2f against %.2f-%.2f): the knots lower g_b most in the $1M-2M band (%+.1f%%), where IBBA\'s free '
         'band mean is high; NLL %.2f -> %.2f; offers per closed deal against IBBA\'s band-free fits, sum of squared se: %.1f -> %.1f at the refit; '
         'repo calibration pins (within %.2f of IBBA\'s lower-bound means) the refit would break: %s'
         % (lr0, CBS['p_M5_vs_M2'], lrk, CBK['p_M5_vs_M2'], qd[0], qd[1], stats.chi2.sf(lrk / qd[0], 4), stats.chi2.sf(lrk / qd[1], 4),
            stats.chi2.sf(lr0 / qd[0], 4), stats.chi2.sf(lr0 / qd[1], 4), 100 * (CBK['g_b'][2] / CBS['g_b'][2] - 1), CBS['nll_M5'], CBK['nll_M5'], chi_s, chi_k,
            ENG_PINS_TOL, ', '.join('%s (%.3f against %.2f)' % (b, pins[b]['knots_at_refit'], pins[b]['ibba_lower_bound']) for b in pins_broken) or 'none'))
    check('model offers per closed deal at the shipped calibration = MODELS.fitted.competition', max(abs(round(a, 3) - COMP0['offers_per_closed_deal_model'][b]) for a, b in zip(zt_s, BANDS)) <= 0.0015,
          'snapshot %s vs shipped %s' % (np.round(zt_s, 3).tolist(), [COMP0['offers_per_closed_deal_model'][b] for b in BANDS]))
    check('the snapshot keeps every repo calibration pin (offers within %.2f of IBBA\'s lower-bound means)' % ENG_PINS_TOL, all(pins[b]['snapshot_inside'] for b in BANDS),
          '; '.join('%s %.3f vs %.2f' % (b, pins[b]['snapshot'], pins[b]['ibba_lower_bound']) for b in BANDS))
    offers = {b: dict(ibba_bandfree=bf[b], ibba_se=bfse[b], snapshot=zt_s[i], knots_at_0184=zt_k[i], knots_refit=zt_kr[i]) for i, b in enumerate(BANDS)}
    # output effects at the shipped ENG_SHARE and at the refit adoption would require
    EFR = run_probe({'mode': 'effect', 'sde': EFFECT_SDE, 'band_V': VC, 'runs': [{'tag': 'knots_refit', 'page': PAGE_KNOTS, 'grid': True,
                     'overrides': [['"eng_share":%s,' % json.dumps(ENG0), '"eng_share":%s,' % json.dumps(eng_if)]]}]}, 'effect_refit')
    check('ENG_SHARE override reached the model (the refit adoption would require)', abs(EFR['runs']['knots_refit']['eng_share'] - eng_if) < 1e-12,
          'knot page with ENG_SHARE %.3f' % EFR['runs']['knots_refit']['eng_share'])
    g2 = pd.DataFrame(EFR['runs']['knots_refit']['grid']); mr = g0.merge(g2, on=['ind', 'ern'], suffixes=('_s', '_r'))

    def effects(m, t):
        return dict(PC_pp_typical=float(100 * np.max(np.abs(m['PC_' + t] - m.PC_s))), PC_pp_half_pool=float(100 * np.max(np.abs(m['PC_half_' + t] - m.PC_half_s))),
                    compPrem_pp_typical=float(100 * np.max(np.abs(m['compPrem_' + t] - m.compPrem_s))),
                    compPrem_pp_half_pool=float(100 * np.max(np.abs(m['compPrem_half_' + t] - m.compPrem_half_s))),
                    EVp_pct_typical=float(100 * np.max(np.abs(m['EVp_' + t] / m.EVp_s - 1))), EVp_pct_half_pool=float(100 * np.max(np.abs(m['EVp_half_' + t] / m.EVp_half_s - 1))),
                    EVp_pct_half_pool_signed_range=[float(100 * np.min(m['EVp_half_' + t] / m.EVp_half_s - 1)), float(100 * np.max(m['EVp_half_' + t] / m.EVp_half_s - 1))],
                    nEngRef_pct_range=[float(100 * np.min(m['nEngRef_' + t] / m.nEngRef_s - 1)), float(100 * np.max(m['nEngRef_' + t] / m.nEngRef_s - 1))])
    eff = {'knots_at_shipped_eng_share': effects(mg, 'k'), 'knots_at_the_refit_adoption_would_require': effects(mr, 'r'),
           'note': ('if the knot table were adopted (it is not): max change over 16 industries x %d SDE points $100k-$10M, median-quality businesses '
                    'asking REF_RATIO x V; half pool = round(IND.buyers/2) buyers contacted; EVp = P_C x E[price | close] (expected proceeds); '
                    'nEngRef = the typical pool\'s expected offers' % len(EFFECT_SDE))}
    print('ENG_SHARE: snapshot %.5f, knots %.5f (shift %+.4f = %+.2f se); not adopted, kept %.3f; peRef max |rel| %.1f%% at $%.2fM'
          % (CBS['eng_share'], CBK['eng_share'], d_eng, d_in_se, ENG0, 100 * abs(mg.rel.values[imax]), mg.ern.values[imax] / E6), flush=True)
    peRef_shift = dict(sde_m=[rd(x / E6, 3) for x in REPORT_SDE], pct=[rd(100 * x, 2) for x in rep_rows.rel_mean],
                       pct_range_over_industries=[[rd(100 * a, 2), rd(100 * b, 2)] for a, b in zip(rep_rows.rel_min, rep_rows.rel_max)],
                       max_abs_pct=rd(100 * float(abs(mg.rel.values[imax])), 2), sde_at_max_m=rd(float(mg.ern.values[imax]) / E6, 3),
                       nEngRef_net_pct_at_the_refit=[rd(100 * ((1 + x) * eng_if / ENG0 - 1), 2) for x in rep_rows.rel_mean],
                       note='if adopted: mean over the 16 industries of peRef(knots)/peRef(trapezoid) - 1, median-quality businesses; '
                            'nEngRef_net_pct_at_the_refit adds the ENG_SHARE change adoption would require (the typical pool\'s expected offers)')
    sizefit_eta = dict(sde_m=[rd(x / E6, 3) for x in REPORT_SDE], trapezoid=[rd(float(x), 3) for x in rep_rows.sf_eta_trapezoid],
                       knots=[rd(float(x), 3) for x in rep_rows.sf_eta_knots])

    # ---------------------------------------------------------------- 1b. the identity with the knot table
    PK = run_probe({'mode': 'identity', 'sde': grid.tolist(), 'page': PAGE_KNOTS}, 'identity_knots')
    same_rows = all(a['ind'] == b['ind'] and a['ern'] == b['ern'] for a, b in zip(rows, PK['rows']))
    SFk = {k: np.array([r['B'][k][0] for r in PK['rows']]) for k in BUY}; PEk = {k: np.array([r['B'][k][2] for r in PK['rows']]) for k in BUY}
    d_grouped = max(float(np.max(np.abs(SFk[k] - SF[k]))) for k in GROUPED)
    mf_c_k = solve(W_P95, group_terms(SFk))
    # revision 3: the knot table is not adopted, so its estimator variant is recorded beside the range, not in it
    mf_searchers_knots = solve(W_P95, group_terms(SFk), eta_in_ind=True, pem=PEk)
    check('the measured knot table would leave the central identity unchanged', same_rows and d_grouped == 0 and abs(mf_c_k - mf_c) < 1e-12,
          'IBBA archetypes\' sizeFit identical; mf_ind %.6f vs %.6f; searchers counted as IBBA individuals: %.4f under the knots (not adopted; '
          'trapezoid %.4f, in the range)' % (mf_c_k, mf_c, mf_searchers_knots, est['searchers_counted_as_IBBA_individuals']))
    allv = [mf_c] + list(econ.values()) + list(est.values())
    rng_econ = [min([mf_c] + list(econ.values())), max([mf_c] + list(econ.values()))]
    rng_all = [min(allv), max(allv)]
    check('mf_ind 0.97 inside the specification range and the IBBA bootstrap interval', rng_all[0] <= 0.97 <= rng_all[1] and mf_ci[0] <= 0.97 <= mf_ci[1],
          'range %.3f-%.3f; bootstrap 95%% %.3f-%.3f' % (rng_all[0], rng_all[1], mf_ci[0], mf_ci[1]))

    # ---------------------------------------------------------------- 4. eta mf check
    cases = [dict(lab='sig_lt500k', E=0.35e6, margin=m_sf, year=2021), dict(lab='sig_500k_1m', E=math.sqrt(0.5e6 * 1e6), margin=m_sf, year=2021),
             dict(lab='sig_1m_2m', E=math.sqrt(1e6 * 2e6), margin=m_sf, year=2021), dict(lab='sig_ge2m', E=2.8e6, margin=m_sf, year=2021),
             dict(lab='stanford_all', E=ST26_MED_EBITDA * E6, margin=ST26_MED_MARGIN, year=2018),
             dict(lab='stanford_2022_23', E=ST26_EBITDA_2223 * E6, margin=ST26_MARGIN_2223, year=2023),
             dict(lab='stanford_2024_25', E=ST26_MED_EBITDA_2425 * E6, margin=ST26_MARGIN_2425, year=2025),
             dict(lab='iese_all', E=IESE_MED_EBITDA * E6, margin=IESE_MED_MARGIN, year=2018)]
    EM = pd.DataFrame(run_probe({'mode': 'etamf', 'cases': cases}, 'etamf')['rows'])
    model_VE = EM.groupby('lab').V_over_E.median()
    rows_sf = []
    for lab, sh, wE in zip(['sig_lt500k', 'sig_500k_1m', 'sig_1m_2m', 'sig_ge2m'], SIG_FIG23, SIG_FIG23_EBITDA_W):
        n = round(SIG_N_ACQ * wE / 100); cnt = np.array(sh) / sum(sh) * n
        mu, sg, _, _ = binned_ln_fit(SIG_FIG23_MULT_EDGES, cnt)
        bs = [binned_ln_fit(SIG_FIG23_MULT_EDGES, RNG_MF.multinomial(n, np.array(sh) / sum(sh)))[0] for _ in range(B_MF)]
        se_log = float(np.std(bs, ddof=1))
        rows_sf.append(dict(bucket=lab, n=n, paid_median_multiple=math.exp(mu), se_log=se_log, model_V_over_EBITDA=float(model_VE[lab]),
                            ratio=math.exp(mu) / float(model_VE[lab])))
    lr = np.log([r['ratio'] for r in rows_sf]); lse = np.array([r['se_log'] for r in rows_sf]); wv = 1 / lse ** 2
    pooled = float(np.sum(wv * lr) / wv.sum()); pooled_se = float(math.sqrt(1 / wv.sum())); Qh = float(np.sum(wv * (lr - pooled) ** 2))
    trad = {lab: dict(paid=p, model=float(model_VE[lab]), ratio=p / float(model_VE[lab])) for lab, p in
            [('stanford_all', ST26_MULT['all']), ('stanford_2022_23', ST26_MULT['2022-23']), ('stanford_2024_25', ST26_MULT['2024-25']), ('iese_all', IESE_MULT)]}
    z_eta = (math.log(MF0['eta']) - pooled) / pooled_se
    check('eta mf .98 against self-funded searchers\' price / model value', abs(z_eta) < 2,
          'pooled ratio %.3f (se of log %.3f, Q %.1f on 3 df); z of ln(.98) %.2f' % (math.exp(pooled), pooled_se, Qh, z_eta))

    # ---------------------------------------------------------------- 5. PHI and the synergy pool
    ind13 = np.array(BCG13_PHI_IND) / 100; yr18 = np.array(BCG18_TARGET) / 100
    est_phi = [(BCG13_PHI_MEDIAN / 100, float(ind13.std(ddof=1) / math.sqrt(len(ind13)))), (float(yr18.mean()), float(yr18.std(ddof=1) / math.sqrt(len(yr18))))]
    y = np.array([e[0] for e in est_phi]); s = np.array([e[1] for e in est_phi]); w = 1 / s ** 2
    ybar = float(np.sum(w * y) / w.sum()); Qp = float(np.sum(w * (y - ybar) ** 2))
    tau2 = max(0.0, (Qp - (len(y) - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    wr = 1 / (s ** 2 + tau2); phi_re = float(np.sum(wr * y) / wr.sum()); phi_se = float(math.sqrt(1 / wr.sum()))
    z_phi = (PHI - phi_re) / phi_se
    check('PHI .38 against the BCG pooled seller share', abs(z_phi) < 2, 'random effects %.3f (se %.3f, tau %.3f); z %.2f' % (phi_re, phi_se, math.sqrt(tau2), z_phi))
    gmr = {r['ind']: r['gm'] for r in rows}   # the profile's peer gm, from the same row as synr below (IND's, or the curve's)
    console_pool = {k: IND[k]['strat'] * (.050 + .028 * gmr[k] + .015) for k in INDS}
    cp = np.array([console_pool[k] for k in INDS]); bm = np.array([BCG13_POOL[BCG_MAP[k]] / 100 for k in INDS])
    rho_map, p_map = stats.spearmanr(cp, bm)
    synr = {r['ind']: r['synE_rev'] for r in rows}
    perr = max(abs(synr[k] - console_pool[k]) for k in INDS)
    check('synergy pool formula = model synE / revenue', perr < 1e-12, 'max |strat x (.050+.028 gm+.015) - synE/rev| = %.1e' % perr)
    xl = pd.read_excel(DAMODARAN, sheet_name='Industry Averages', header=None)
    hdr = next(i for i in range(20) if str(xl.iloc[i, 0]).strip().lower().startswith('industry'))
    dm = xl.iloc[hdr + 1:, :3].copy(); dm.columns = ['industry', 'n', 'gross']; dm = dm.dropna(subset=['industry'])
    dm['n'] = pd.to_numeric(dm.n, errors='coerce'); dm['gross'] = pd.to_numeric(dm.gross, errors='coerce'); Gd = dm.set_index('industry')
    gmv = {k: float(np.average(Gd.loc[v].gross, weights=Gd.loc[v].n)) for k, v in DAMO_MAP.items()}
    xr = np.array([gmv[k] for k in BCG13_POOL if k in gmv]); yr = np.array([BCG13_POOL[k] / 100 for k in BCG13_POOL if k in gmv])
    import statsmodels.api as sm
    ols = sm.OLS(yr, sm.add_constant(xr)).fit(cov_type='HC1')
    strat = np.array([IND[k]['strat'] for k in INDS])
    pool = dict(bcg2013_median=BCG13_POOL_MEDIAN / 100, n_deals=BCG13_N, years='2000-2011', console_median=float(np.median(cp)),
                console_range=[float(cp.min()), float(cp.max())], ratio_of_medians=float(np.median(cp)) / (BCG13_POOL_MEDIAN / 100),
                bcg_industry_median=float(np.median(list(BCG13_POOL.values()))) / 100,
                bcg_median_se_industry_spread=float(1.2533 * np.std(list(BCG13_POOL.values()), ddof=1) / 100 / math.sqrt(len(BCG13_POOL))),
                mapped_bcg_median=float(np.median(bm)), median_ratio_mapped=float(np.median(cp / bm)), spearman_mapped=[float(rho_map), float(p_map)],
                coefficient_sum_at_median_gm=float(.050 + .028 * np.median([gmr[k] for k in INDS]) + .015),
                strat_median=float(np.median(strat)), strat_range=[float(strat.min()), float(strat.max())],
                by_industry={k: dict(console=console_pool[k], bcg=BCG13_POOL[BCG_MAP[k]] / 100, bcg_industry=BCG_MAP[k], strat=IND[k]['strat']) for k in INDS},
                gm_slope=dict(slope=float(ols.params[1]), se=float(ols.bse[1]), const=float(ols.params[0]), r2=float(ols.rsquared), n=len(xr), console_slope=0.028,
                              source='BCG/TUM 2013 Exhibit 1 industries x Damodaran US gross margins (margin.xls, January 2026)'))
    z_pool = (pool['console_median'] - pool['bcg2013_median']) / pool['bcg_median_se_industry_spread']
    pool['z_vs_bcg'] = z_pool
    check('synergy pool level against BCG/TUM 2013 (conditional on IND.strat, judgment)', abs(math.log(pool['ratio_of_medians'])) < 0.25,
          'console median %.2f%% of revenue vs BCG %.1f%% (ratio %.2f; %.1f se of BCG\'s industry spread); mapped %.2f%%, median ratio %.2f, Spearman %.2f. '
          'The level is strat x %.3f (median strat %.2f, judgment): it matches only given strat'
          % (100 * pool['console_median'], BCG13_POOL_MEDIAN, pool['ratio_of_medians'], z_pool, 100 * pool['mapped_bcg_median'], pool['median_ratio_mapped'], rho_map,
             pool['coefficient_sum_at_median_gm'], pool['strat_median']))
    check('pool gm slope against BCG industries', abs(pool['gm_slope']['slope'] - 0.028) < 2 * pool['gm_slope']['se'],
          'slope %.3f (se %.3f, n %d, R2 %.2f) vs the console\'s 0.028' % (pool['gm_slope']['slope'], pool['gm_slope']['se'], len(xr), pool['gm_slope']['r2']))

    # ---------------------------------------------------------------- texts
    # revision 3: the window stays, so the comment says what the window is and what the data say about it
    st24_sde = float(st24_med * E6 * wedge(np.array([st24_med * E6 / st24_marg]))[0])
    in_window = bool(6e5 <= wE_sde <= 3.2e6 and 6e5 <= st24_sde <= 3.2e6)
    check('Stanford\'s median search-fund deals lie inside the hand-set window (full presence $0.6M-$3.2M of SDE)', in_window,
          'Stanford 2026: median EBITDA $2.0M = $%.2fM of SDE at the console wedge (margin %.0f%%); Stanford 2024: $%.1fM = $%.2fM (margin %.0f%%)'
          % (wE_sde / E6, 100 * ST26_MED_MARGIN, st24_med, st24_sde / E6, 100 * st24_marg))
    comment_txt = ("how present this buyer's group is at this deal value, from IBBA's buyer-type mix (fitted). Search funds are in no IBBA "
                   "group and keep a hand-set earnings window: full presence from $0.6M to $3.2M of SDE, linear tails. It contains "
                   "Stanford's median search-fund deal, $2.0M of EBITDA in the 2026 study and $%.1fM in the 2024 study (about $%.1fM and "
                   "$%.1fM of SDE). A measured presence curve was checked and not adopted (MODELS.fitted.buyers.eta_check; fit: "
                   "buyer_factors.py). Was a hand-set window per archetype." % (st24_med, wE_sde / E6, st24_sde / E6))
    words = comment_txt.split(' '); lines_ = []; cur = '    /* '
    for wd in words:
        if len(cur) + len(wd) + 1 > 96 and cur.strip() not in ('/*', ''):
            lines_.append(cur.rstrip()); cur = '       ' + wd + ' '
        else:
            cur += wd + ' '
    lines_.append(cur.rstrip() + ' */')
    NEW_COMMENT = '\n'.join(lines_) + '\n'
    NEW_DATATAB = ("individual / strategic / financial shares by deal value (search funds keep a hand-set window, which contains "
                   "Stanford&rsquo;s median search-fund deal: $2.0M of EBITDA in the 2026 study, $%.1fM in 2024)" % st24_med)
    status_txt = json.loads('{%s}' % STATUS_NEW)['status']

    # ---------------------------------------------------------------- js_table
    sens_keys = {"full_support": est['full_support_p0.5_p99.5'], "research_round": est['research_estimator_on_its_8_point_grid'],
                 "str_adj_1.25_1.20": econ['str_adj_1.25_1.20 (Pepperdine 2016 alone)'], "no_strategic_premium": econ['str_adj_1.00 (no strategic mf premium)'],
                 "phi_0.31": econ['PHI_0.31 (BCG 2013)'], "phi_0.54": econ['PHI_0.54 (BCG 2018)'], "pool_bcg_level": econ['pool_x0.857 (BCG median level)'],
                 "strategic_share_x0.75": econ['IBBA_strategic_share_x0.75'], "strategic_share_x1.25": econ['IBBA_strategic_share_x1.25'],
                 "searchers_as_individuals": est['searchers_counted_as_IBBA_individuals']}
    top_core = max(in_core, key=lambda r: r['sde'])
    per_size_rng = [min(r['mf_ind_solution'] for r in in_core), max(r['mf_ind_solution'] for r in in_core)]
    kn_at = lambda K, x: float(K[KNOT_SDE.index(x)][1])
    shift_tags = ['knots', 'w0.8', 'smooth', 'research_margin', 'wedge1.2', 'acquired', 'dollar_basis_2026', 'trapezoid_at_step_halfmax']
    eta_check = {
        "status": ("measured, not adopted (analyst): the search fund's window stays judgment at [$0.6M, $3.2M] of SDE (full presence; linear tails "
                   "to 0 at 0.15 lo and 2.6 hi); ENG_SHARE stays %.3f and MODELS.fitted.competition is unchanged" % ENG0),
        "why_not_adopted": ("its effect on the ENG_SHARE calibration depends on how the curve is built (%+.2f to %+.2f se over the knot-table "
                            "constructions; %+.2f se read in 2026 dollars); it fits IBBA's offers per closed deal by band worse than the trapezoid "
                            "(chi2 against the band-free fits %.2f -> %.2f; the size-gradient LR p %.3f -> %.3f); and the refit it would require "
                            "breaks the repo's %s calibration pin"
                            % (shift_rng[0], shift_rng[1], var_eng['dollar_basis_2026']['shift_in_se'], chi_s, chi_k, CBS['p_M5_vs_M2'],
                               CBK['p_M5_vs_M2'], ', '.join(pins_broken) or 'no')),
        "measured_half_presence": {"knot_table": [rd(kl_c / E6, 3), rd(kh_c / E6, 3)], "se": [rd(kl_se / E6, 3), rd(kh_se / E6, 3)],
                                   "step_curve": [rd(lo_c / E6, 3), rd(hi_c / E6, 3)], "step_curve_se": [rd(lo_se / E6, 3), rd(hi_se / E6, 3)],
                                   "smooth_reading": [rd(variants['SIG shares interpolated (smooth)'][0] / E6, 3), rd(variants['SIG shares interpolated (smooth)'][1] / E6, 3)],
                                   "peak": rd(pk_c / E6, 2), "units": "$M of SDE",
                                   "reading": "where presence first reaches and last leaves half its peak (knot table read with lerpKnots; the step curve it samples)"},
        "shipped_trapezoid": {"plateau": [0.6, 3.2], "half_presence": [rd(t_lo / E6, 3), rd(t_hi / E6, 3)],
                              "half_presence_in_se_of_measured": [rd(trap_vs['in_se_of_knot_halfmax'][0], 2), rd(trap_vs['in_se_of_knot_halfmax'][1], 2)],
                              "presence_at_0_6M": [rd(trap_vs['presence_at_0_6M'][0], 3), rd(trap_vs['presence_at_0_6M'][1], 3)],
                              "presence_at_5M": [rd(trap_vs['presence_at_5M'][0], 3), rd(trap_vs['presence_at_5M'][1], 3)],
                              "pairs": "[trapezoid, measured knot table]",
                              "least_squares_plateau_with_the_code_ramps": [rd(ls_lo / E6, 2), rd(ls_hi / E6, 2)], "least_squares_r2": rd(ls_r2, 2)},
        "knots_measured": KN, "knots_se": [rd(float(x), 3) for x in knot_se], "w": W_SF,
        "knots_source": ("SIG 2023 Self-Funded Search Study Fig 7 (share of 279 searchers whose EBITDA target includes each bin) x %.1f + Stanford "
                         "GSB 2026 Search Fund Study (E967) acquired-EBITDA lognormal (median $2.0M, 318 priced deals) x %.1f, each mapped to SDE "
                         "with sdeEbitdaWedge; ln SDE -> presence; se from a bootstrap over the survey counts (sampling only)" % (W_SF, 1 - W_SF)),
        "eng_share_shift_by_construction": dict(
            {t: rd(var_eng[t]['shift_in_se'], 2) for t in shift_tags},
            se_used=ENG_SE0, central_eng_share=rd(CBK['eng_share'], 4), central_eng_share_se=rd(CBK['eng_share_se'], 4),
            central_spec_range=[rd(x, 3) for x in CBK['eng_share_spec_range']],
            range_over_knot_constructions=[rd(shift_rng[0], 2), rd(shift_rng[1], 2)],
            rule=("the analyst's rule if adopted: refit ENG_SHARE when |shift| > 0.5 se (0.0135); it would refit under %s and keep 0.184 under %s"
                  % (', '.join(t for t in shift_tags if var_eng[t]['rule_says_refit']), ', '.join(t for t in shift_tags if not var_eng[t]['rule_says_refit']) or 'none')),
            note=("ENG_SHARE (the snapshot's fit/competition_buyers.py M5 on IBBA offers per closed deal) on a page carrying each knot table, "
                  "minus 0.184, in units of its se 0.027; knots = the central construction (full script; the others by the replica, equal to 1e-5); "
                  "trapezoid_at_step_halfmax = round 1's reading: the trapezoid moved to the step curve's half-maximum")),
        "ibba_fit": {"offers_per_closed_deal": {b: [rd(offers[b]['ibba_bandfree'], 2), rd(offers[b]['snapshot'], 3), rd(offers[b]['knots_at_0184'], 3),
                                                    rd(offers[b]['knots_refit'], 3)] for b in BANDS},
                     "columns": ["IBBA band-free fit", "snapshot (trapezoid, 0.184)", "knots at 0.184", "knots at the refit"],
                     "chi2_vs_bandfree": [rd(chi_s, 2), rd(chi_k, 2)], "size_gradient_lr": [rd(lr0, 2), rd(lrk, 2)],
                     "size_gradient_p": [rd(CBS['p_M5_vs_M2'], 3), rd(CBK['p_M5_vs_M2'], 3)],
                     "calibration_pins": {"tolerance": ENG_PINS_TOL, "ibba_lower_bound": {b: lb[b] for b in BANDS},
                                          "snapshot": {b: rd(pins[b]['snapshot'], 3) for b in BANDS},
                                          "knots_at_refit": {b: rd(pins[b]['knots_at_refit'], 3) for b in BANDS}, "broken_by_the_refit": pins_broken,
                                          "test": "tests/model.test.js CALIBRATION: model offers per closed deal within 0.40 of IBBA's lower-bound mean"}},
        "dollar_basis": {"caveat": ("SIG's targets are in 2023 dollars and Stanford's median mixes 1984-2025 dollars, but the knot table reads both as "
                                    "2026 dollars. Read in 2026 dollars (CPI-U, Feb-Aug 2026 mean %.2f over the 2023 average %.2f = x%.4f) the curve "
                                    "moves right and the low knots fall sharply" % (CPI_26, CPI_23, INF)),
                         "cpi_2026_over_2023": rd(INF, 4), "knots_2026_dollars": var_knots[DB_LAB],
                         "knot_0_8M": [rd(kn_at(KN, 8e5), 3), rd(kn_at(var_knots[DB_LAB], 8e5), 3)],
                         "knot_1_5M": [rd(kn_at(KN, 1.5e6), 3), rd(kn_at(var_knots[DB_LAB], 1.5e6), 3)],
                         "half_presence": [[rd(kl_c / E6, 3), rd(kh_c / E6, 3)], [rd(kl_inf / E6, 3), rd(kh_inf / E6, 3)]],
                         "half_presence_lo_shift_in_se": rd((kl_inf - kl_c) / kl_se, 2),
                         "eng_share_shift_in_se": rd(var_eng['dollar_basis_2026']['shift_in_se'], 2), "pairs": "[as read (2026 dollars assumed), in 2026 dollars]"},
        "step_function": {"caveat": ("the self-funded targets are a step function in EBITDA; knots that sit on a step read it at the step, and the "
                                     "bootstrap SEs (over the survey counts) do not cover where the edges fall"),
                          "edges_sde_m": [rd(e / E6, 3) for e in edge_sde], "edges": edge_lab,
                          "knots_within_5pct_of_an_edge": [{k: (rd(v, 3) if isinstance(v, float) else v) for k, v in d_.items()} for d_ in near_edges],
                          "smooth_reading_knots": var_knots['SIG shares interpolated (smooth)'], "flat_wedge_1_2_knots": var_knots['wedge 1.2 flat'],
                          "acquired_size_knots": var_knots['acquired size (SIG Fig 21 density in place of targets)']},
        "typical_pool_if_adopted": {"sizefit_eta": sizefit_eta, "peRef_pct": peRef_shift['pct'], "peRef_sde_m": peRef_shift['sde_m'],
                                    "peRef_max_abs_pct": peRef_shift['max_abs_pct'], "peRef_sde_at_max_m": peRef_shift['sde_at_max_m'],
                                    "half_pool_pc_pp": [rd(eff['knots_at_shipped_eng_share']['PC_pp_half_pool'], 2), rd(eff['knots_at_the_refit_adoption_would_require']['PC_pp_half_pool'], 2)],
                                    "half_pool_proceeds_pct": [rd(eff['knots_at_shipped_eng_share']['EVp_pct_half_pool'], 2), rd(eff['knots_at_the_refit_adoption_would_require']['EVp_pct_half_pool'], 2)],
                                    "note": "median businesses, 16 industries, SDE $0.1M-$10M; [at 0.184, at the refit]; peRef = the typical pool's engagement"},
        "flat_tail": ("read with lerpKnots the measured table would hold presence at %.2f beyond $15M of SDE (SIG's open >= $5M EBITDA bin); the "
                      "trapezoid is 0 above $8.3M" % KY[-1]),
        "judgment_inside": "w = 0.9; the ramp below EBITDA $250k (0 at $100k); flat beyond the end knots",
    }
    js = {
        "mf_ind": 0.97, "mf_ind_raw": rd(mf_c, 3), "mf_ind_tier": "calibrated",
        "mf_ind_page": "solved on the snapshot page as shipped: the search fund's trapezoid (lo $0.6M, hi $3.2M) and ENG_SHARE %.3f" % ENG0,
        "mf_ind_se": rd(mf_se, 3),
        "mf_ind_se_kind": ("sampling only: bootstrap over IBBA's complete band-quarters (B=%d; 95%% %.3f-%.3f); it leaves out the specification "
                           "(mf_ind_range) and the size pattern (mf_ind_per_size)" % (B_MIX, mf_ci[0], mf_ci[1])),
        "mf_ind_range": [rd(rng_all[0], 3), rd(rng_all[1], 3)],
        "mf_ind_range_kind": ("specification range: the other archetypes' factors, PHI at the BCG ends, the pool at BCG's level, IBBA's strategic "
                              "share +-25%, MBOs inside BIZCOMPS, and the estimator"),
        "mf_ind_per_size": [rd(per_size_rng[0], 3), rd(per_size_rng[1], 3)],
        "mf_ind_per_size_kind": ("solutions of the identity at single sizes, the grid points SDE $%.0fk-$%.0fk inside BIZCOMPS p5-p95 ($%.0fk-$%.0fk): "
                                 "one constant cannot balance every size; at $%.0fk the constant 0.97 leaves a %+.1f%% imbalance (solution %.3f)"
                                 % (min(r['sde'] for r in in_core) / 1e3, max(r['sde'] for r in in_core) / 1e3, support['p5'] / 1e3, support['p95'] / 1e3,
                                    top_core['sde'] / 1e3, 100 * top_core['imbalance_at_097'], top_core['mf_ind_solution'])),
        "mf_ind_sens": {k: rd(v, 3) for k, v in sens_keys.items()} | {"mbo_5pct": [rd(econ['MBO_5pct_of_BIZCOMPS_at_0.86'], 3), rd(econ['MBO_5pct_of_BIZCOMPS_at_1.00'], 3)]},
        "identity": ("sum over IBBA buyer groups of share(V) x mean ln(Vj/V) = 0: the value model is BIZCOMPS's calibrated median sale, so the "
                     "buyer-type-weighted price must average to it. Weighted over the BIZCOMPS SDE distribution up to its p95 ($728k), "
                     "median-quality businesses, 16 industries; solved for mf_ind with the other BUYERS values, PHI and the pool as shipped"),
        "mf_ind_caveats": ["calibrates one degree of freedom given the other seven mf, PHI and syn, all judgment: it does not measure what individuals pay",
                           "treats IBBA's fitted buyer-type mix at the deal value as BIZCOMPS's buyer composition (untested: no buyer-type field in BIZCOMPS)",
                           "re-solve whenever another mf, syn, PHI, the synergy pool or buyerMix changes",
                           "one factor cannot balance every size: per-size solutions %.3f-%.3f over SDE $%.0fk-$%.0fk (BIZCOMPS p5-p95)"
                           % (per_size_rng[0], per_size_rng[1], support['p5'] / 1e3, support['p95'] / 1e3)],
        "imbalance_at_090": rd(imb_shipped, 4), "imbalance_at_097": rd(imb_097, 4),
        "eta_check": eta_check,
        "eta_mf_check": {"self_funded": rd(math.exp(pooled), 2), "se_log": rd(pooled_se, 3), "n": SIG_N_ACQ,
                         "by_ebitda": [rd(r['ratio'], 2) for r in rows_sf], "traditional": [rd(min(v['ratio'] for v in trad.values()), 2), rd(max(v['ratio'] for v in trad.values()), 2)],
                         "shipped": MF0['eta'], "z": rd(z_eta, 2), "status": "judgment, checked"},
        "phi_check": {"bcg2013": rd(BCG13_PHI_MEDIAN / 100, 2), "bcg2018": rd(est_phi[1][0], 3), "pooled": rd(phi_re, 2), "se": rd(phi_se, 2),
                      "tau": rd(math.sqrt(tau2), 2), "console": PHI, "z": rd(z_phi, 2), "n_deals": [BCG13_N, BCG18_N], "status": "judgment, checked",
                      "population": "public deals over $300M (BCG/TUM 2000-11; BCG 2008-17), not small businesses"},
        "pool_check": {"bcg2013_median": BCG13_POOL_MEDIAN / 100, "console_median": rd(pool['console_median'], 4), "ratio": rd(pool['ratio_of_medians'], 2),
                       "mapped_median_ratio": rd(pool['median_ratio_mapped'], 2), "spearman": rd(float(rho_map), 2),
                       "gm_slope": [rd(pool['gm_slope']['slope'], 3), rd(pool['gm_slope']['se'], 3)], "console_gm_slope": 0.028, "n_deals": BCG13_N,
                       "status": "judgment, checked", "conditional_on": "IND.strat (judgment): the console's pool is strat x (.050 + .028 gm + .015) of revenue, so the level match holds only given strat"},
        "comment_fix": comment_txt,
        "strategic_premium_status": status_txt,
        "source": ("mf_ind: identity on the BIZCOMPS-fitted value model (18,941 closed sales; MODELS.value) with the IBBA/M&A Source Market Pulse buyer-type mix "
                   "(fitted buyerMix, 2012-23). eta_check: Search Investment Group 2023 Self-Funded Search Study (279 searchers, 109 acquirers; Figs 7, 20, 21, 23), "
                   "Stanford GSB 2026 Search Fund Study (E967, n=318 priced deals 1984-2025; Exhibit 4), IESE 2024 and Stanford 2024 as variants; "
                   "ENG_SHARE re-run with fit/competition_buyers.py on IBBA offers-per-closed-deal histograms (2023Q1-Q4, 2025Q4); FRED CPI-U. Checks: BCG/TUM 2013 "
                   "Divide and Conquer (365 deals > $300M, 2000-11), BCG 2018 M&A Report (1,000 deals 2008-17), Damodaran US gross margins (Jan 2026)"),
        "method": ("mf_ind CALIBRATED: exact solve of the adding-up identity through the console's own Vj (node harness) on the snapshot page as shipped, "
                   "BIZCOMPS quantile weights, se = bootstrap over IBBA complete band-quarters (B=%d, sampling only); shipped at 2 decimals. eta_check "
                   "(evidence, not adopted): w=%.1f x SIG target shares (steps, normalised to the peak) + (1-w) x Stanford 2026 acquired-EBITDA lognormal, "
                   "EBITDA->SDE by sdeEbitdaWedge, sampled at 15 SDE points, bootstrap B=%d; ENG_SHARE on a page carrying each knot table with the "
                   "snapshot's fit/competition_buyers.py (%d two-stage bootstrap draws) and a replica of its M5 likelihood. PHI and pool: benchmark "
                   "checks, values unchanged") % (B_MIX, W_SF, B_WIN, CBK['n_boot']),
    }
    hits_js = sorted(set(re.findall(r'nb_r|eng_share_pln|NB_R|pAnyOffer', json.dumps(js))))
    check('the buyers table names neither the NB dispersion nor the PLN scale (it sits in the model source the repo test scans)', not hits_js,
          'js_table text clear of nb_r, eng_share_pln, NB_R and pAnyOffer%s' % ((' (found %s)' % hits_js) if hits_js else ''))

    # ---------------------------------------------------------------- 6. the page as it would ship (scratch)
    # revision 3: no knots, no MODELS.fitted.competition change but the strategic_premium.status text; the eta row and sizeFit as shipped
    assert COMP_LINE.count(STATUS_OLD) == 1
    comp_line_new = COMP_LINE.replace(STATUS_OLD, STATUS_NEW)
    js_txt = json.dumps(rnd(js), separators=(',', ':'))
    PAGE_SHIP = build_page('index_as_shipped.html', [(COMP_LINE, comp_line_new + 'MODELS.fitted.buyers=' + js_txt + ';\n'), (IND_ROW, IND_ROW_NEW),
                                                     (OLD_COMMENT, NEW_COMMENT), (OLD_HEADER, NEW_HEADER), (OLD_DATATAB, NEW_DATATAB)])
    t_snap = start_repo_tests('snapshot', SNAP); t_ship = start_repo_tests('as_shipped', PAGE_SHIP)      # run in the background
    ship_html = open(PAGE_SHIP, encoding='utf-8').read()
    src_ = ship_html[ship_html.rindex('<script>'):]
    MOD = re.sub(r'MODELS\.fitted\.competition=\{.*\};\n', '', src_[:src_.index('/* ============ bar helpers')])
    hits = sorted(set(re.findall(r'nb_r|eng_share_pln|NB_R|pAnyOffer', MOD)))
    check('as-shipped page: the model source names neither the NB dispersion nor the PLN scale (the repo test\'s scan)', not hits,
          'MODELS.fitted.buyers and the edits add none of nb_r, eng_share_pln, NB_R, pAnyOffer outside MODELS.fitted.competition%s' % ((' (found %s)' % hits) if hits else ''))
    comp_ship = json.loads([ln for ln in ship_html.split('\n') if ln.startswith('MODELS.fitted.competition=')][0][len('MODELS.fitted.competition='):-1])
    comp_diff = sorted(k for k in set(COMP0) | set(comp_ship) if COMP0.get(k) != comp_ship.get(k))
    sp_diff = sorted(k for k in set(COMP0['strategic_premium']) | set(comp_ship['strategic_premium'])
                     if COMP0['strategic_premium'].get(k) != comp_ship['strategic_premium'].get(k))
    check('as-shipped page: MODELS.fitted.competition unchanged except the strategic_premium.status text', comp_diff == ['strategic_premium'] and sp_diff == ['status'],
          'fields that differ: %s (strategic_premium: %s); status now "%s"' % (comp_diff, sp_diff, comp_ship['strategic_premium']['status']))
    KS = run_probe({'mode': 'knotcheck', 'page': PAGE_SHIP, 'sde': chk_sde, 'inds': ['home', 'rest', 'saas']}, 'knotcheck_as_shipped')
    ks_err = max(abs(r[2] - float(trap([r[1]], 6e5, 3.2e6)[0])) for r in KS['rows'])
    mbo_ship = max(abs(a[3] - b[3]) for a, b in zip(KS['rows'], KC0['rows']))
    PS = run_probe({'mode': 'identity', 'sde': grid.tolist(), 'page': PAGE_SHIP}, 'identity_as_shipped')
    imb_ship = 0.0
    for r, w in zip(PS['rows'], W_P95):
        m = r['mix']; B = r['B']
        imb_ship += w * (m[0] * math.log(B['ind'][1]) + m[1] * np.mean([math.log(B[k][1]) for k in ('str', 'adj')])
                         + m[2] * np.mean([math.log(B[k][1]) for k in ('pep', 'add', 'fo')]))
    imb_ship /= float(np.sum(W_P95))
    EFS = run_probe({'mode': 'effect', 'sde': [], 'band_V': VC, 'runs': [{'tag': 'ship', 'page': PAGE_SHIP, 'grid': False}]}, 'effect_as_shipped')
    Gship = pd.DataFrame(EFS['runs']['ship']['bands']).pivot_table(index='b', columns='ind', values='g').sort_index().values
    zt_ship = zt_mean(EFS['runs']['ship']['eng_share'] * Gship, NBR0).mean(1)
    check('as-shipped page: ind mf 0.97 read from MODELS.fitted.buyers; the trapezoid, the MBO window and ENG_SHARE as on the snapshot; the identity balances',
          KS['mf']['ind'] == 0.97 and all(KS['mf'][k] == MF0[k] for k in MF0 if k != 'ind') and KS['eta_lo'] == 6e5 and KS['eta_hi'] == 3.2e6
          and ks_err < 1e-12 and mbo_ship == 0 and KS['mbo'] == KC0['mbo'] and KS['eng_share'] == ENG0 and abs(imb_ship - imb_097) < 1e-9
          and abs(imb_ship) < 0.005 and KS['buyers_table'] is not None and float(np.max(np.abs(zt_ship - zt_s))) < 1e-12,
          'ind mf %.2f from MODELS.fitted.buyers (other mf unchanged); eta sizeFit = the trapezoid to %.1e, window [%.0f, %.0f]; MBO window %s; '
          'ENG_SHARE %.3f; weighted mean log imbalance %+.4f; offers per closed deal by band %s (= the snapshot)'
          % (KS['mf']['ind'], ks_err, KS['eta_lo'], KS['eta_hi'], KS['mbo'], KS['eng_share'], imb_ship, np.round(zt_ship, 3).tolist()))
    ex = {"ind": "medical", "rev": 6e6, "ern": 1.45e6, "grw": .14, "gm": .64, "rec": .72, "cc": .18, "ret": .91, "plt": .38,
          "own": .72, "mgt": .36, "fin": .74, "yrs": 6, "buyers": 65, "st": None, "franchise": False, "ask": 3.24e6}
    inv0 = run_invariants('snapshot_inv', SNAP, ex); inv1 = run_invariants('as_shipped', PAGE_SHIP, ex)
    fails = ('mono_fail', 'thin_fail', 'ref_fail', 'qual_fail', 'median_fail')
    check('fit/competition_buyers.py invariant probe: no failures on the as-shipped page (as on the snapshot)', all(inv1[k] == 0 for k in fails) and all(inv0[k] == 0 for k in fails),
          'as shipped %s; snapshot %s (%d random businesses x 11 pool sizes, plus 80 median businesses at band centres)'
          % ({k: inv1[k] for k in fails + ('median_max_abs_comp', 'median_max_thin_gap')}, {k: inv0[k] for k in fails}, inv1['n']))
    RT = {'snapshot': finish_repo_tests(t_snap), 'as_shipped': finish_repo_tests(t_ship)}
    check('repo tests/model.test.js on a scratch copy of the snapshot: all pass (the copy is a valid harness)', RT['snapshot']['failed'] == 0 and RT['snapshot']['exit'] == 0,
          '%s passed, %s failed' % (RT['snapshot']['passed'], RT['snapshot']['failed']))
    kinds = {'buyer multiple factors and PHI unchanged': 'update (asserts ind mf === .90)'}
    RT['as_shipped']['classified'] = [dict(fail=f, kind=next((v for k, v in kinds.items() if f.startswith(k)), 'unexpected')) for f in RT['as_shipped']['fails']]
    note('repo tests/model.test.js on the as-shipped page (what integration must update)',
         '%s passed, %s failed: %s' % (RT['as_shipped']['passed'], RT['as_shipped']['failed'],
                                       '; '.join('%s [%s]' % (c['fail'], c['kind']) for c in RT['as_shipped']['classified']) or 'none'))
    check('repo tests on the as-shipped page: the only failures are expected updates (the ind mf pin)', all(c['kind'] != 'unexpected' for c in RT['as_shipped']['classified']),
          '%d failing, %d unexpected' % (len(RT['as_shipped']['classified']), sum(c['kind'] == 'unexpected' for c in RT['as_shipped']['classified'])))

    # ---------------------------------------------------------------- RESULT
    RES['js_table'] = js
    RES['tier'] = 'calibrated (mf_ind); everything else judgment with checks'
    RES['mf_ind'] = dict(
        shipped=0.97, raw=mf_c, se_ibba_mix=mf_se, se_kind='sampling only (IBBA band-quarter bootstrap)', ci95_ibba_mix=mf_ci, range_economic=rng_econ,
        range_all=rng_all, per_size_range=per_size_rng, per_size_top=top_core, page='the snapshot as shipped (trapezoid, ENG_SHARE %.3f)' % ENG0,
        current=MF0['ind'], imbalance_current_p95=imb_shipped, imbalance_current_full=imb_full_shipped,
        imbalance_at_097_p95=imb_097, imbalance_at_097_full=imb_full_097, imbalance_at_097_model=imb_model, imbalance_at_097_as_shipped_page=imb_ship,
        sensitivity_economic=econ, sensitivity_estimator=est, searchers_as_individuals_under_the_knots_not_adopted=mf_searchers_knots, per_size=per_size,
        weights=dict(kind='BIZCOMPS SDE distribution (MODELS.value.support), CDF linear in ln SDE through p0.5..p99.5',
                     central='SDE up to p95 ($728k)', grid_points=len(grid), industries='16, equal weight'),
        others_held=dict(mf={k: v for k, v in MF0.items() if k != 'ind'}, syn=SYN, PHI=PHI),
        bootstrap=dict(B=B_MIX, unit='IBBA complete band-quarters resampled within band', n_complete=ns))
    RES['eta_presence_not_adopted'] = dict(
        status='measured and recorded in js_table.eta_check; not adopted (analyst, revision 3): the window stays judgment at [$0.6M, $3.2M]',
        knots=KN, knots_unrounded=knots_of(c0).tolist(), knots_se=knot_se.tolist(), knots_ci95=knot_ci.tolist(), knot_sde=KNOT_SDE,
        halfmax_knots=dict(lo=kl_c, hi=kh_c, lo_se=kl_se, hi_se=kh_se, lo_ci95=np.percentile(bkl, [2.5, 97.5]).tolist(), hi_ci95=np.percentile(bkh, [2.5, 97.5]).tolist()),
        halfmax_step_curve=dict(lo=lo_c, hi=hi_c, peak=pk_c, lo_se=lo_se, hi_se=hi_se, lo_ci95=np.percentile(bl, [2.5, 97.5]).tolist(),
                                hi_ci95=np.percentile(bh, [2.5, 97.5]).tolist(), lo_bootstrap_quantiles=np.percentile(bl, [10, 25, 50, 75, 90]).tolist(),
                                smooth=dict(lo=variants['SIG shares interpolated (smooth)'][0], hi=variants['SIG shares interpolated (smooth)'][1],
                                            lo_se=float(sm_se[0]), hi_se=float(sm_se[1]))),
        research_knots=dict(file=RESEARCH_KNOTS, sha256=sha(RESEARCH_KNOTS), max_abs_diff=float(rk_dy.max()), at_sde=KNOT_SDE[rk_dy_i],
                            max_abs_diff_with_research_margin=float(np.max(np.abs(rk[:, 1] - rk_m25))),
                            w08_max_abs_diff=float(np.max(np.abs(rk8[:, 1] - np.array([k[1] for k in var_knots['w=0.8']]))))),
        trapezoid_like_for_like=dict(trap_vs, ls_trapezoid=dict(lo=ls_lo, hi=ls_hi, r2=ls_r2, note='least squares with the code\'s ramps; the research round got $1.59M-$2.08M on its grid')),
        w_selffunded=W_SF, variants={k: dict(lo=v[0], hi=v[1], peak=v[2], knots=var_knots[k]) for k, v in variants.items()}, fits=fits,
        robustness_in_se=rob, acquired_sde_q25_q50_q75=acq, presence_curve=curve.to_dict('records'),
        dollar_basis=dict(cpi_2026_feb_aug=CPI_26, cpi_2023=CPI_23, factor=INF, knots=var_knots[DB_LAB], halfmax=[kl_inf, kh_inf], step_halfmax=list(variants[DB_LAB][:2])),
        step_function=dict(edges_ebitda=edge_ebitda, edges_sde=edge_sde, edges=edge_lab, knots_near_edges=near_edges),
        stanford2026=dict(median_ebitda_m=ST26_MED_EBITDA, median_ebitda_2024_25_m=ST26_MED_EBITDA_2425, median_margin=ST26_MED_MARGIN, min_ebitda_m=ST26_MIN_EBITDA,
                          median_sde_at_console_wedge=wE_sde, median_sde_2024_25=wE_sde_2425, n_priced=ST26_N_PRICE),
        stanford2024=dict(median_ebitda_m=st24_med, median_sde_at_console_wedge=st24_sde, margin=st24_marg))
    RES['eta_effect_if_adopted'] = dict(
        sizefit_eta=sizefit_eta, peRef_shift=peRef_shift, peRef_by_sde=by_sde.to_dict('records'),
        eng_share=dict(control_snapshot={k: v for k, v in CBS.items() if k not in ('log', 'G')}, knots={k: v for k, v in CBK.items() if k not in ('log', 'G')},
                       shift=d_eng, shift_in_se=d_in_se, se_used=ENG_SE0, rule_would_refit=rule_refit, refit_adoption_would_require=eng_if,
                       nb_dispersion_adoption_would_require=nbr_if, kept=ENG0, adopted=False,
                       rule='analyst: refit ENG_SHARE only if |shift| > 0.5 x eng_share_se (0.0135); revision 3: the knot table is not adopted, so ENG_SHARE stays 0.184',
                       copied_script=dict(source=CB_SRC, source_sha256=sha(CB_SRC), copy=CB_COPY, copy_sha256=sha(CB_COPY),
                                          patches=['harness path -> wrapper loading the page under test (/tmp/claude-0/fit6/harness.js with a file argument)',
                                                   'probe compPrem hook: (3+...) -> (COMP_H+...), the page as it now is',
                                                   'probe peRef: nEngRef/(I.buyers x 0.34) -> nEngRef/(I.buyers x ENG_SHARE), the page as it now is',
                                                   'early exit after the NB specification range (CB_ENG_ONLY), dumping eng_share_calibration.json'],
                                          bootstrap_draws=CBK['n_boot'], outputs=CB_DIR)),
        replica_and_variants=var_eng, shift_range_over_knot_constructions=shift_rng, offers_per_closed_deal=offers, calibration_pins=pins,
        calibration_pins_broken_by_the_refit=pins_broken, output_effects=eff,
        size_gradient_fit=dict(lr_M5_vs_M2=[lr0, lrk], p=[CBS['p_M5_vs_M2'], CBK['p_M5_vs_M2']], quasi_dispersion=qd,
                               p_quasi=[[float(stats.chi2.sf(lr0 / qd[0], 4)), float(stats.chi2.sf(lr0 / qd[1], 4))], [float(stats.chi2.sf(lrk / qd[0], 4)), float(stats.chi2.sf(lrk / qd[1], 4))]],
                               nll_M5=[CBS['nll_M5'], CBK['nll_M5']], g_b=[CBS['g_b'], CBK['g_b']], offers_chi2_vs_ibba_bands=[chi_s, chi_k]))
    RES['as_shipped_page'] = dict(path=PAGE_SHIP, sha256=sha(PAGE_SHIP), invariants=inv1, invariants_snapshot=inv0, imbalance=imb_ship,
                                  competition_fields_changed=comp_diff, strategic_premium_fields_changed=sp_diff)
    RES['eta_mf'] = dict(self_funded=rows_sf, pooled_ratio=math.exp(pooled), pooled_se_log=pooled_se, Q=Qh, z_shipped=z_eta, traditional=trad, shipped=MF0['eta'])
    RES['phi'] = dict(bcg2013=dict(value=BCG13_PHI_MEDIAN / 100, se=est_phi[0][1], n_deals=BCG13_N, years='2000-2011', industries=BCG13_PHI_IND),
                      bcg2018=dict(value=est_phi[1][0], se=est_phi[1][1], n_deals=BCG18_N, years='2008-2017', annual=BCG18_TARGET),
                      fixed_effect=ybar, Q=Qp, tau=math.sqrt(tau2), pooled=phi_re, pooled_se=phi_se, console=PHI, z=z_phi,
                      bcg2016_note='BCG 2016 (167 deals 2010-15): premium / pretax annual synergies averaged 8.6x, about 0.72 of synergies capitalised at 12x (not pooled: a mean of ratios on a different basis)')
    RES['pool'] = pool
    RES['shipped'] = [
        dict(param='BUYERS ind mf (MODELS.fitted.buyers.mf_ind)', current=MF0['ind'], value=0.97, unrounded=mf_c, se=mf_se, se_kind='sampling only',
             range=rng_all, range_kind='specification', per_size=per_size_rng, tier='calibrated (identity)',
             note='solved on the snapshot page as shipped; one degree of freedom given the other mf, PHI and syn; IBBA mix taken as BIZCOMPS composition; '
                  're-solve when those change'),
        dict(param='texts: the sizeFit comment, the BUYERS header, the Data-tab buyer-mix sentence, MODELS.fitted.competition.strategic_premium.status',
             value=dict(comment=comment_txt, status=status_txt, data_tab=NEW_DATATAB), tier='text')]
    RES['not_shipped'] = {
        'eta presence curve (measured knot table)': dict(status='not adopted (analyst, revision 3); evidence in js_table.eta_check', evidence=dict(
            halfmax=[kl_c, kh_c], halfmax_se=[kl_se, kh_se], trapezoid_halfmax=[t_lo, t_hi], eng_share_shift_in_se={t: var_eng[t]['shift_in_se'] for t in shift_tags},
            offers_chi2=[chi_s, chi_k], size_gradient_p=[CBS['p_M5_vs_M2'], CBK['p_M5_vs_M2']], pins_broken=pins_broken),
            why='its effect on ENG_SHARE depends on the construction, it fits IBBA\'s offers by band worse, and the refit it would require breaks the 2M-5M calibration pin'),
        'eta window (lo .6e6, hi 3.2e6, tails .85/1.6)': dict(status='judgment, kept', evidence=dict(trap_vs, ls_trapezoid=[ls_lo, ls_hi, ls_r2]),
                                                              why='the measured curve is not adopted; the window contains Stanford\'s median deals (2026 and 2024)'),
        'ENG_SHARE (0.184) and MODELS.fitted.competition': dict(status='unchanged (analyst, revision 3)', evidence=dict(refit_adoption_would_require=eng_if, shift_in_se=d_in_se),
                                                                why='the knot table is not adopted; only strategic_premium.status changes (a text)'),
        'PHI': dict(value=PHI, status='judgment, checked', evidence=dict(bcg2013=0.31, bcg2018=est_phi[1][0], pooled=phi_re, pooled_se=phi_se, tau=math.sqrt(tau2), z=z_phi),
                    why='public deals over $300M; the two BCG vintages differ by more than their sampling (tau %.2f); .38 sits inside the pooled band' % math.sqrt(tau2)),
        'synergy pool coefficients (.050, .028, .015)': dict(status='judgment, checked', evidence=dict(console_median=pool['console_median'], bcg2013_median=0.048,
                                                                                                         ratio=pool['ratio_of_medians'], spearman_mapped=float(rho_map),
                                                                                                         gm_slope=[pool['gm_slope']['slope'], pool['gm_slope']['se']]),
                                                             why='the pool is strat x coefficients; IND.strat is judgment (the research round found no data for its level or ordering), '
                                                                 'so a level match is conditional on judgment; BCG/TUM is public deals over $300M'),
        'BUYERS eta mf (.98)': dict(status='judgment, checked', evidence=dict(self_funded_pooled_ratio=math.exp(pooled), se_log=pooled_se, z=z_eta,
                                                                                  traditional_ratio_range=[min(v['ratio'] for v in trad.values()), max(v['ratio'] for v in trad.values())]),
                                    why='self-funded searchers pay about model value (z %.2f); traditional funds pay 1.5-1.9x model value but are a tenth of searchers' % z_eta),
        'BUYERS mbo window (lo .3e6, hi Infinity) and mf .86': dict(status='judgment', evidence=None, why='no data found on MBO presence or price by size'),
        'other BUYERS mf (str 1.18, adj 1.14, pep 1.06, add 1.12, fo 1.02), syn and fit coefficients': dict(status='judgment, checked earlier (fit/competition_buyers.py: Pepperdine, GF Data)',
                                                                                                           evidence=COMP0['strategic_premium'], why='consistency checks only'),
    }
    RES['integration'] = dict(
        js_line='MODELS.fitted.buyers=<js_table>; (after MODELS.fitted.competition)',
        page_edits=[dict(old=IND_ROW, new=IND_ROW_NEW), dict(old=OLD_COMMENT, new=NEW_COMMENT), dict(old=OLD_HEADER, new=NEW_HEADER),
                    dict(old=OLD_DATATAB, new=NEW_DATATAB), dict(old=STATUS_OLD, new=STATUS_NEW, where='inside the MODELS.fitted.competition line')],
        not_changed=['the eta row (lo .6e6, hi 3.2e6) and sizeFit', 'ENG_SHARE 0.184 and every other MODELS.fitted.competition field', 'the MBO window'],
        as_shipped_page=PAGE_SHIP,
        repo_model_tests=RT,
        data_tab_notes=['the BUYERS row of the judgment ledger: mf_ind is calibrated; the search-fund window stays judgment (a measured curve was checked: eta_check)',
                        'the ledger count nBuy (renderData) counts every mf as judgment: move ind\'s mf to the Calibrated count; the window numbers stay judgment',
                        '"Synergy shares, phi and the individual, MBO and family-office factors have no data": the individual factor is now calibrated (identity)',
                        'the comparison note "search funds pay about PE multiples at equal quality (Stanford 2024)" is unchanged'],
        competition_notes=['MODELS.fitted.competition is unchanged except strategic_premium.status (the page edit above); no refit, no derived-field update',
                           'tests/model.test.js "buyer multiple factors and PHI unchanged" asserts ind mf === .90: update it to read MODELS.fitted.buyers.mf_ind (0.97)'])
    RES['checks'] = CHECKS
    RES['sources'] = [
        dict(name='Search Investment Group, 2023 Self-Funded Search Study (72 pp.)', url='https://www.searchinvestgroup.com/study (full report: SIG public Google Drive, file id 1Aq1XHtCNtVD0_Jkx8CAYyDF20YpPCERh)',
             file=SIG_PDF, sha256=sha(SIG_PDF), years='survey 2022; acquisitions mostly 2019-22', n='279 searchers (Fig 7), 109 acquirers (Figs 20-23)', used='Figs 7, 20, 21, 23 (pp. 21, 37-39)'),
        dict(name='Stanford GSB 2026 Search Fund Study: Selected Observations (E967)', url='https://www.gsb.stanford.edu/faculty-research/case-studies/2026-search-fund-study-selected-observations',
             file=ST26_PDF, sha256=sha(ST26_PDF), years='1984-2025', n='318 priced acquisitions (381 total)', used='Exhibit 4 (p.23): price bins, median and minimum EBITDA, margins, multiples'),
        dict(name='IESE International Search Funds 2024 (ST-658-E)', url='https://iese.edu/media/research/pdfs/ST-0658-E', file=IESE_PDF, sha256=sha(IESE_PDF),
             years='to 2023', n='146 acquisitions (price n not printed; 93 used)', used='Exhibit 7 (p.28): price bins, median EBITDA, margin, multiple (variant and eta mf check)'),
        dict(name='Stanford GSB 2024 Search Fund Study (E870), transcribed table', url='https://www.gsb.stanford.edu/faculty-research/case-studies/2024-search-fund-study',
             file=ST24_CSV, sha256=sha(ST24_CSV), years='1984-2023', n='268 priced acquisitions', used='Exhibit 5/6: median EBITDA $1.9M (comment fix), price bins (variant)'),
        dict(name='BCG/TUM, Divide and Conquer: How Successful M&A Deals Split the Synergies (2013)', url='https://web-assets.bcg.com/img-src/BCG_Divide_and_Conquer_Mar_2013_tcm9-62259.pdf (via web.archive.org 2020id_)',
             file=BCG13_PDF, sha256=sha(BCG13_PDF), years='2000-2011', n='365 deals > $300M', used='Exhibit 1 (p.6) synergies / target sales; Exhibit 4 (p.11) seller share'),
        dict(name='BCG, Synergies Take Center Stage (2018 M&A Report)', url='http://boston-consulting-group-brightspot.s3.amazonaws.com/img-src/BCG-Synergies-Take-Center-Stage-Sep-2018_tcm9-202243.pdf',
             file=BCG18_PDF, sha256=sha(BCG18_PDF), years='2008-2017', n='1,000 public-to-public deals', used='Exhibit 12 (p.21) seller share by year'),
        dict(name='IBBA / M&A Source Market Pulse, buyer-type mix (transcribed)', url='https://www.ibba.org/ (Market Pulse reports)', file=IBBA_MIX, sha256=sha(IBBA_MIX),
             years='2012-2023', n='154 band-quarter rows; complete %s' % ns, used='bootstrap of buyerMix for the mf_ind se'),
        dict(name='IBBA / M&A Source Market Pulse, offers per closed deal by band', url='https://www.ibba.org/ (Market Pulse full reports)', file=IBBA_OFFERS, sha256=sha(IBBA_OFFERS),
             years='2023Q1-Q4, 2025Q4', n='25 band-quarters, about 1,523 closed deals', used='ENG_SHARE re-run (copied fit/competition_buyers.py and the replica)'),
        dict(name='Damodaran, US industry margins (margin.xls, January 2026)', url='https://pages.stern.nyu.edu/~adamodar/pc/datasets/margin.xls (local git mirror)',
             file=DAMODARAN, sha256=sha(DAMODARAN), years='2026', n='%d BCG industries mapped' % len(xr), used='pool gm slope check'),
        dict(name='Research round knot table (F-buyers, eta_knots.py)', url='local', file=RESEARCH_KNOTS, sha256=sha(RESEARCH_KNOTS), years='-', n='15 knots per variant',
             used='check that this script reproduces it'),
        dict(name='fit/competition_buyers.py (snapshot), copied and patched', url='local', file=CB_SRC, sha256=sha(CB_SRC), years='-', n='IBBA histograms (above)',
             used='ENG_SHARE calibration on the snapshot (control) and on the knot page; its invariant probe on the as-shipped page'),
        dict(name='The Omni Method snapshot (HEAD 56ba230) and harness', url='local', file=SNAP, sha256=sha(SNAP), years='-', n='BIZCOMPS 18,941 closed sales (MODELS.value)',
             used='model values (node, %s sha256 %s); patched copies in %s' % (HARNESS, sha(HARNESS), PAGES))]
    RES['readme_row'] = ('| `buyers` (revision 3: BUYERS `ind` mf 0.90 -> 0.97, **calibrated**: the adding-up identity on the BIZCOMPS-fitted value with '
                         'IBBA\'s buyerMix, solved on the snapshot page as shipped, BIZCOMPS SDE weights to p95; se %.3f sampling only, specification range '
                         '%.3f-%.3f, per-size solutions %.3f-%.3f. The search fund\'s presence by size was measured (SIG 2023 targets x 0.9 + Stanford 2026 '
                         'deals x 0.1, sdeEbitdaWedge; half presence $%.2fM-$%.2fM against the trapezoid\'s $%.3fM-$%.2fM) and NOT adopted: its ENG_SHARE '
                         'effect depends on the construction (%+.2f to %+.2f se), it fits IBBA\'s offers by band worse, and the refit breaks the 2M-5M pin; '
                         'the $0.6M-$3.2M window stays judgment, ENG_SHARE stays 0.184 (evidence in `eta_check`). PHI, the synergy pool and `eta` mf '
                         'recorded as BCG / survey checks, unchanged) '
                         '| `buyer_factors.py` (writes `RESULT.json`, `js_table.json` and tables to `/tmp/claude-0/fit6/out/buyer_factors/`; runs the model through '
                         'the harness on patched copies of the page; 10-20 min) | SIG 2023 Self-Funded Search Study (Figs 7, 20, 21, 23); Stanford GSB 2026 Search '
                         'Fund Study (E967, Exhibit 4); IESE 2024 (ST-658-E, Exhibit 7); Stanford 2024 table; IBBA Market Pulse buyer mix and offers histograms; '
                         'BCG/TUM 2013, BCG 2018; Damodaran margin.xls; FRED CPI-U (dollar-basis check) '
                         '| SIG report from SIG\'s public Google Drive (file id 1Aq1XHtCNtVD0_Jkx8CAYyDF20YpPCERh); Stanford: gsb.stanford.edu case page (Box download); '
                         '`curl -L -o ST-0658-E.pdf https://iese.edu/media/research/pdfs/ST-0658-E`; BCG 2013 via web.archive.org; `curl -LO` the BCG 2018 S3 PDF; '
                         '`curl -L -o CPIAUCNS.csv \'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS\'` |'
                         % (mf_se, rng_all[0], rng_all[1], per_size_rng[0], per_size_rng[1], kl_c / E6, kh_c / E6, t_lo / E6, t_hi / E6, shift_rng[0], shift_rng[1]))
    RES = rnd(RES)
    with open(os.path.join(OUT, 'RESULT.json'), 'w') as f:
        json.dump(RES, f, indent=1)
    with open(os.path.join(OUT, 'js_table.json'), 'w') as f:
        json.dump(RES['js_table'], f, separators=(',', ':'))
    cnt = Counter(c['outcome'] for c in CHECKS)
    print('checks: %d passed, %d failed, %d info' % (cnt['pass'], cnt['FAIL'], cnt['info']))
    print('wrote', os.path.join(OUT, 'RESULT.json'))


if __name__ == '__main__':
    main()
