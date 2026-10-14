#!/usr/bin/env python3
"""Size-varying peer medians of owner dependence and management depth (sizeRefs): the SLOPES are fitted to the Fed's
Survey of Small Business Finances through a seller-population revenue bridge; the LEVELS stay the console's judgment,
because the survey item bounds them rather than identifies them; financial reporting stays judgment; the size z-scale is
fitted to listings. Revision 3, October 2026.

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/size_refs.py [B]      (about 4 min; B = bootstrap draws, default 500)
Out:  /tmp/claude-0/fit6/out/size_refs/RESULT.json (key js_table = MODELS.fitted.size_refs; js_line = the exact line
      to embed; shipped, not_shipped, checks, sources, open_issues), js_line.txt, lines.csv, knots.csv, class_shares.csv,
      replications.csv, mgt_independent.csv, clamp.csv, clamp_value_effect.csv, gm_payoff.csv, accrual_tax_law.csv,
      fin_sd.csv, size_sd.csv, judgment_checks.json
      Round 1 is kept beside it as size_refs.v1.py and out/size_refs.v1/, revision 2 as size_refs.v2.py and
      out/size_refs.v2/.

Revision 3 (the analyst's decisions on the round-2 review)
  - The review showed that the survey item bounds the LEVELS while the SLOPES are robust. "No owner responsible for
    day-to-day management" fits Moderate ("owner sets direction only") as well as Low, so the same 10.1% share at $708k
    puts the own median anywhere from .60 (the item is Low only, cut .28) to .89 (Low or Moderate, cut .57), and mgt
    from .15 (Solid or Deep, cut .51) to .43 (Deep only, cut .79); the level also drifts with the survey year (own .48 /
    .56 / .60 in 1993 / 1998 / 2003). Five sources give the own slope (-.12 to -.15).
  - Shipped: the slopes as fitted, own b -.15 (SE .019) and mgt b +.17 (SE .021), with the console's levels kept as
    judgment, own a .62 and mgt a .42 (both inside the bounds). The data readings of the levels are recorded in
    js_table.checks: real 2003 dollars .60 and .43 (sampling SEs .013 / .014), nominal .56 and .47, the mapping bounds
    and the vintage readings. fin stays .55 + .22z with fin_sd .28 (judgment). size_sd_log10 .48 ships.
  - The clamp at z = +-1 stays (the pre-set rule is not met). The evidence below $45k of SDE is recorded as a KNOWN
    BIAS: firms with $10k-$45k of SDE have a hired-manager share of 1.8% (SE .5%) against 3.0% under the clamped data
    line, so the clamp understates the own median there; its value effect at $10k-$45k is computed through the harness
    (a floor at z = -1.54, the console's own max(ern, 1e4), against the clamp).
  - The round-2 review's other minor item: the hire-a-GM payoff (interventionTable and the optimiser) with the new
    sizeRefs and intervention_costs' GM loading together, recorded in RESULT.gm_payoff and the open issues.
  - js_table follows the analyst's shape: own, mgt, fin, fin_sd, size_sd_log10, size_sd_se, checks, source, method.

Why
  sizeRefs(ern) sets the peer MEDIANS that the user's owner-dependence, management-depth and reporting inputs are
  z-scored against: z = clamp((log10 SDE - 5.85)/1.20, -1, 1) (SDE $45k..$11M spans z = -1..1; $708k is z = 0) and
  own = .62 - .30z, mgt = .42 + .28z, fin = .55 + .22z, all hand-set. z.own = (own - RF.own)/.25,
  z.mgt = (mgt - RF.mgt)/.28 and z.fin = (fin - RF.fin)/.28 feed the quality composite, which places the business
  inside the measured spread of closed prices, so the medians move value, price, closing odds and both scores. The size
  z-scale (z.size = (log10 SDE - log10 7e5)/.45) feeds the category scores and confidence only.
  Round 1 shipped own .56 - .15z, mgt .47 + .17z, fin .55 + .22z (fin z-scale .32) and size scale .48 in NOMINAL terms:
  it read 2026 seller revenue on 2003-dollar probits. The completeness critic (research/results_all.json, "critique")
  added that own and mgt rest on one SSBF item (CF_MANAGE) mapped to both menus, that fin's accrual item partly measures
  2003 tax-accounting rules, and that nobody tested whether the medians stop moving at the clamp ($45k and $11M).
  Revision 2 read the lines in real dollars (.60 - .15z, .43 + .17z) and shipped them whole; the round-2 review showed
  the levels are bounded, not identified (above). The analyst's decisions, which this revision implements:
    own, mgt  slopes ship as fitted (identical in real and nominal dollars); levels stay the console's .62 and .42
              (judgment). The data readings are recorded: in REAL dollars (the bridge's 2026 revenue divided by CPI-U,
              Feb-Aug 2026 over the 2003 average, 1.808, before the 2003 probits are read) .60 and .43; nominal .56 and
              .47; the mapping bounds own .60-.89 and mgt .15-.43; the vintages 1993 / 1998 / 2003.
    mgt slope ships only if evidence independent of the SSBF item agrees with it: Census ABS 2023 management-practice
              tables by receipts class and the DealLedger "management team" phrase, pooled (random effects). If the
              pool rejects SSBF's slope (|z| >= 1.96), mgt stays judgment (.42 + .28z) instead.
    fin       stays judgment: the console's .55 + .22z and its z-scale .28. The checks go to not_shipped: the two
              items' real-dollar lines, the parallel-threshold rejection, the 2003 tax-law confound of the accrual item,
              and the menu-coded SD (.29-.35).
    size_sd_log10 .48 ships (SD of log10 SDE of businesses for sale). The $700k centre stays a convention.
    clamp     tested: do the SSBF item shares keep moving beyond $45k and $11M of SDE? Kept unless clearly
              contradicted, defined before computing as: for an item of a shipped dimension (CF_MANAGE), the outer slope
              of a spline probit differs from zero at the 1% level on that side AND does not differ from the inner slope
              at the 5% level. Kept (revision 3: with the evidence below $45k recorded as a known bias).

What it does
  0. Data. Reads the downloads directly (SSBF .dat files as extracted from the Fed's .Z archives, checked against
     their sha256; the SBO 2007 PUMS straight from its zip; the ABS tables from their zips; nothing is executed). The
     snapshot's index.html is read (never written) for the current sizeRefs coefficients, the z-scales and the three
     input menus, whose midpoints are the cut points: own .28/.57/.835, mgt .22/.51/.79, fin .295/.595/.85. CPI-U
     (FRED CPIAUCNS, sha256 pinned) gives the deflators: 2003 annual average, and the mean of the DealLedger snapshot
     months with a CPI print (Feb-Aug 2026).
  1. Seller bridge. DealLedger broker listings (one row per listing as in the research's dl_text.py): a robust (Huber)
     line log10 revenue = A0 + G log10 SDE over the 5,350 listings with both figures (SDE $30k-$15M, revenue between
     1x and 50x SDE). SEs by a broker-cluster bootstrap (B draws). Revenue is in 2026 dollars; in 2003 dollars it is
     A0 - D + G log10 SDE with D = log10(CPI 2026 / CPI 2003) = .257.
  2. SSBF 2003 (4,240 firms x 5 implicates, FIN_WGT, 72 strata). Weighted probits of three items on log10 sales
     (firms with sales $50k-$200M, 2003 dollars), fitted jointly per implicate (stacked scores), design variance by
     stratified linearisation (firms as PSUs), implicates combined by Rubin's rules:
       CF_MANAGE = 2, no owner responsible for day-to-day management  -> own < .28  ("Low: runs without the owner")
                                                                      -> mgt > .79  ("Deep: full team, owner optional")
       P1_2 = 2, accrual accounting                                   -> fin > .595 (Clean or better)       [check]
       N3T2/N3T3 = 1, statements reviewed or audited by a CPA          -> fin > .85  (a lower bound)         [check]
  3. Lines (real). With the console's peer spread s (own .25, mgt .28, fin .28) the latent median at SDE x is
     c -/+ s * Phi^-1(P(item | log10 sales = A0 - D + G log10 x)), exactly linear in z:
       a = c + t s (b0 + b1 (A0 - D + G 5.85)),   b = t s b1 G 1.20     (t = +1 for upper-tail items, -1 for own)
     SEs by the delta method over the Rubin-combined probit covariance and the bridge's bootstrap covariance (CPI is
     taken as exact). Knot medians at SDE $45k, $150k, $708k, $3M and $11M with SEs. own and mgt ship b (to 0.01, SE to
     0.001); a is recorded as a data reading (the shipped a is the console's judgment level); fin's item lines and their
     average are recorded only. Mapping bounds: the same share read with the next cut point (own < .57 instead of
     < .28; mgt > .51 instead of > .79) moves a by the cut difference and leaves b unchanged.
  4. mgt independent of the SSBF item. Slopes per z on the console scale (s .28): DealLedger "management team" probit on
     broker SDE (no bridge; broker-cluster bootstrap SE); Census ABS 2023 management-practice shares by receipts class
     (8 items and their composite; minimum chi-square probit on log10 receipts, bridge slope G), the composite's SE
     widened by the SD of the 8 item slopes (the item choice is a construct uncertainty, the rule round 1 used for fin
     and SBO). DerSimonian-Laird pool of the two sources (fixed-effect and sampling-only readings recorded), and the
     test the decision turns on: SSBF 2003's slope against the pool. Check: the ABS composite by employment class in
     2020 and 2023 (the module's stability across vintages).
  5. fin (judgment): the accrual and reviewed lines in real dollars with s = .28 (and with the menu-coded s), their
     average, the parallel-threshold Wald test, and the tax-law check: the accrual probit slope among firms below every
     2003 cash-method threshold (sales < $1M), among firms free to use cash at any size (no inventory, not a C
     corporation), among inventory holders and C corporations, with the accrual share by class. The menu-coded SD among
     same-size firms (two readings of the CPA item, stratified bootstrap + Rubin) is recorded against the kept .28.
  6. Size z-scale. SD of log10 SDE among DealLedger listings with SDE $50k-$20M; broker-cluster bootstrap SE; IBBA
     closed-deal values and window variants as checks; population medians recorded.
  7. Replications (slopes only). One estimate per source on the console's scale: own: SSBF 2003, SSBF 1998 (C_MGR),
     NSSBF 1993 (MANAGE), SBO 2007 PUMS employer firms (an owner provides the services -> own > .835, SE adds half the
     gap to SBO's lower-tail item), DealLedger ("owner-operated"); mgt: the same three SSBF vintages, SBO 2007 (no owner
     provides or manages), DealLedger ("management team"). Survey windows are $50k-$200M in 2003 dollars converted to
     each survey's own dollars with CPI-U (1992 sales for NSSBF 1993, 1998, 2007); listings SDE $30k-$15M. DerSimonian-
     Laird pool, Knapp-Hartung SE, leave-one-source-out; every source refitted on the console's z window in real terms.
  8. Checks. (a) Class shares: the real data lines (.60 - .15z, .43 + .17z) against SSBF 2003 design-weighted item
     shares by sales and employment class inside the z window (revenue $118k-$19.1M in 2003 dollars; chi-square), with
     the shipped lines (judgment levels .62 / .42, fitted slopes) and the console's lines scored the same way (under the
     Low-only / Deep-only mapping, which the shipped levels do not assume). (b) DealLedger out-of-source slopes.
     (c) Vintage 1993/1998/2003: hired-manager slopes, the share at the real revenue of $708k SDE and the levels it
     implies for own and mgt. (d) Clamp: spline probits of each SSBF item on log10 sales with knots at the window edges
     (in 2003 dollars), fitted from the revenue of $10k SDE (the console's floor, max(ern, 1e4)) to $200M; Wald tests of
     each outer slope against zero (the clamp) and against the inner slope (no clamp); observed shares beyond the window
     against the clamped data line; the share of listings beyond each edge and the median the unclamped line would give
     at $10k and $20M SDE. The evidence below $45k is the known bias recorded in js_table.checks.clamp. (e) Sensitivities:
     the nominal reading (round 1), the deflator from the 2025 annual CPI, the SDE proxy given sales, slope brackets, the
     bridge's residual spread.
  9. Judgment checks (recorded, nothing ships): cc, plt, the own and mgt scales, the buyer-pool scale (as round 1).
 10. Materiality, through /tmp/claude-0/fit6/harness.js (node; skipped with a note if missing): (a) the value of a
     business that enters today's medians at the five knot sizes, before and after the shipped own and mgt lines;
     (b) the known bias: the value of a business at the line's unclamped medians with SDE $10k-$45k, under the shipped
     clamp against a floor at z = -1.54 (own and mgt only; fin keeps its clamp); (c) the hire-a-GM payoff
     (interventionTable row and the optimiser's chosen programmes at the default $100k and an open budget) for home and
     professional services, SDE $45k-$3M, for a business at today's medians and for a business at each variant's own
     medians (the review's reading): the snapshot, the shipped sizeRefs, and the shipped sizeRefs with intervention_costs'
     GM cost (revision 3 of that fit: hire cost $10,625 plus 1.24 x salary, and 1.24 x salary off earnings; its revision
     2's 1.38 as the review evaluated it).
 11. Output. RESULT.json (sorted keys, floats rounded) and tables; checks with outcomes; tests listed in RESULT.json.

Data and fetch (each source in its own directory; read with python3 -I; nothing from a download is run; no new
downloads in revisions 2 and 3)
  /tmp/claude-0/fit6/data/E-sizerefs-cc-plt/
    ssbf03/ssbf03.dat.Z     https://www.federalreserve.gov/pubs/oss/oss3/ssbf03/ssbf03.dat.Z   (dict03.txt,
                            codebook/codebook03.pdf, question/question03.pdf beside it); extracted with
                            gzip -dc ssbf03.dat.Z > ssbf03_x/ssbf03.dat
    ssbf98/ssbf98.dat.Z     https://www.federalreserve.gov/pubs/oss/oss3/ssbf98/ssbf98.dat.Z   -> ssbf98_x/ssbf98.dat
    nssbf93/nssbf93.dat.Z   https://www.federalreserve.gov/pubs/oss/oss3/nssbf93/nssbf93.dat.Z -> nssbf93_x/nssbf93.dat
                            (column names in nssbf93/nssbf93.txt from the same page)
    sbo07/pums_csv.zip      https://www2.census.gov/programs-surveys/sbo/datasets/2007/pums_csv.zip
    census_abs_cb/AB2300MCB03.zip, AB2300MCB04.zip, AB2000MCB02.zip, AB2300CSCB03.zip
                            https://www2.census.gov/programs-surveys/abs/data/2023/AB2300MCB03.zip (likewise MCB04,
                            CSCB03; 2020/AB2000MCB02.zip)
    nap_6369/ch17_www.nap.edu.html   https://nap.nationalacademies.org/read/6369/chapter/17 (NRC 2000, Appendix A)
  /tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots/*/listings*.csv
                            git clone --depth 1 https://github.com/jeffsosville/dealledger   (CC0)
  /tmp/claude-0/data5/empireflippers/clean/{ef_listings.csv, ef_listings_text.jsonl}  (Empire Flippers public API)
  /tmp/claude-0/data5/flippa/clean/flippa2026_recently_sold.csv                       (flippa.com sold listings)
  /tmp/claude-0/data5/aggregates_research/clean/{ibba_mp_band_n_closed.csv, ibba_mp_band_histograms_long.csv}
                            (IBBA / M&A Source Market Pulse full reports)
  /tmp/claude-0/data5/marketplaces_sold/clean/bizbuysell_insight_long.csv (BizBuySell Insight medians, secondary pages)
  /tmp/claude-0/fit6/data/peer_gross_margin/fred_cpi_fx/CPIAUCNS.csv   (the deflator; sha256 pinned below)
                            curl -L -o CPIAUCNS.csv 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS'
  Constants read by eye or assumed are below with their source (the ABS $5M+ class midpoint).
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')      # deterministic sums
os.environ.setdefault('OMP_NUM_THREADS', '1')
import glob, hashlib, html as htmlmod, io, json, re, sys, time, warnings, zipfile
import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.linalg import block_diag
from scipy.stats import norm
import statsmodels.api as sm

warnings.filterwarnings('ignore', category=RuntimeWarning)   # all-NaN owner slots in the SBO arrays are handled below
warnings.filterwarnings('ignore', message='This pattern is interpreted as a regular expression')   # the research's flag regexes have groups
T0 = time.time()
OUT = '/tmp/claude-0/fit6/out/size_refs'
os.makedirs(OUT, exist_ok=True)
INDEX = '/tmp/claude-0/fit6snap/index.html'                 # frozen snapshot, read only
E = '/tmp/claude-0/fit6/data/E-sizerefs-cc-plt'
SSBF03, SSBF03_Z = E + '/ssbf03_x/ssbf03.dat', E + '/ssbf03/ssbf03.dat.Z'
SSBF98, SSBF98_Z = E + '/ssbf98_x/ssbf98.dat', E + '/ssbf98/ssbf98.dat.Z'
NSSBF93, NSSBF93_Z, NSSBF93_NAMES = E + '/nssbf93_x/nssbf93.dat', E + '/nssbf93/nssbf93.dat.Z', E + '/nssbf93/nssbf93.txt'
SBO07_ZIP = E + '/sbo07/pums_csv.zip'
ABS_MCB03, ABS_CSCB03 = E + '/census_abs_cb/AB2300MCB03.zip', E + '/census_abs_cb/AB2300CSCB03.zip'
NAP = E + '/nap_6369/ch17_www.nap.edu.html'
DL_SNAP = '/tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots'
EF_LIST = '/tmp/claude-0/data5/empireflippers/clean/ef_listings.csv'
EF_TEXT = '/tmp/claude-0/data5/empireflippers/clean/ef_listings_text.jsonl'
FLIPPA = '/tmp/claude-0/data5/flippa/clean/flippa2026_recently_sold.csv'
IBBA_N = '/tmp/claude-0/data5/aggregates_research/clean/ibba_mp_band_n_closed.csv'
IBBA_H = '/tmp/claude-0/data5/aggregates_research/clean/ibba_mp_band_histograms_long.csv'
BBS = '/tmp/claude-0/data5/marketplaces_sold/clean/bizbuysell_insight_long.csv'
CPI = '/tmp/claude-0/fit6/data/peer_gross_margin/fred_cpi_fx/CPIAUCNS.csv'   # FRED CPIAUCNS (CPI-U, NSA, monthly), fetched by the gm fit
# sha256 (first 16 hex) of the extracted files: each equals the hash of `gzip -dc <the .Z download>`
EXPECT_SHA = {SSBF03: '9d1c2abf27eae3a3', SSBF98: 'e9636d93b5338d17', NSSBF93: '3bbbf27c698aba16',
              SSBF03_Z: 'ccb93e161ddb455b', SSBF98_Z: 'aef5144c19207994', NSSBF93_Z: 'ee09990154634726',
              SBO07_ZIP: '6f6368bd44dbb440', CPI: 'f79e3a7883714229'}
ABS_MCB04, ABS20_MCB02 = E + '/census_abs_cb/AB2300MCB04.zip', E + '/census_abs_cb/AB2000MCB02.zip'   # by employment (check)
# ---- revision 2: the analyst's decisions (documented constants)
FIN_JUDGMENT = (0.55, 0.22)          # fin stays judgment: the console's line ...
FIN_SD_JUDGMENT = 0.28               # ... and its z-scale
Z_CONSISTENT = 1.96                  # ship SSBF's mgt slope only if |SSBF - independent pool| / SE < this (random-effects pool)
CLAMP_P_FLAT, CLAMP_P_LINEAR = 0.01, 0.05   # clamp 'clearly contradicted': outer slope != 0 at 1% and not != inner slope at 5%
POP_SDE = (1e4, 2e7)                 # population edges for the clamp test: the console's floor max(ern, 1e4) and $20M SDE
# ---- revision 3: the analyst's decisions on the round-2 review
LEVELS_JUDGMENT = {'own': 0.62, 'mgt': 0.42}   # the console's levels, kept as judgment (the item bounds them); b ships fitted
BIAS_SDE = [1e4, 1.5e4, 2e4, 3e4, 4.5e4]        # the known bias below $45k: value effect at these SDE
# the hire-a-GM payoff check (review item): intervention_costs' GM cost as documented constants (that fit's js_table.gm,
# read 2026-10-14; it may still move): hire_cost + loading x gmSalary(s) as the cost, loading x gmSalary(s) off earnings
GM_COST_VARIANTS = [('intervention_costs revision 3: hire $10,625 + 1.24 x salary', 10625, 1.24),
                    ('intervention_costs revision 2: 1.38 x salary (as the review evaluated it)', 0, 1.38)]
GM_SDE = [4.5e4, 1.5e5, 3e5, 7.08e5, 3e6]
GM_INDS = ['home', 'prof']
GM_BUDGET = 1e12                      # the optimiser's 'open' budget in the check (no limit); also run at the business's default $100k
B_BOOT = int(sys.argv[1]) if len(sys.argv) > 1 else 500
SEED = 20261014
NEG = -9999999990                                   # SSBF 2003 missing / skip codes are <= this
SALES_LO, SALES_HI = 5e4, 2e8                       # survey fit window (sales or receipts), as in the research
KNOTS = [('45k', 4.5e4), ('150k', 1.5e5), ('708k', 7.08e5), ('3M', 3e6), ('11M', 1.1e7)]
# ABS 2023 receipts classes (MCB03 RCPSZFI codes) and the receipts midpoints the research used (geometric midpoints of
# the class bounds; the open "$5,000,000 or more" class is placed at $12M, an assumption).
ABS_MID = {'523': 1.58e5, '525': 3.54e5, '531': 7.07e5, '533': 1.58e6, '541': 3.54e6, '595': 1.2e7}


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 22), b''):
            h.update(blk)
    return h.hexdigest()[:n]


def rnd(x, k):
    """round half away from zero on the printed decimal (avoids 0.125 -> 0.12 surprises of binary floats)"""
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))


def clean(o, nd=6):
    """JSON-safe copy with floats rounded to nd significant decimals (determinism of the written file)"""
    if isinstance(o, dict):
        return {str(k): clean(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v, nd) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        if not np.isfinite(v):
            return None
        return float(f'{v:.{nd}g}') if abs(v) >= 1e-3 or v == 0 else float(f'{v:.4g}')
    if isinstance(o, np.ndarray):
        return clean(o.tolist(), nd)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


# ------------------------------------------------------------------------------------------------ 0. console values
for p, h in EXPECT_SHA.items():
    got = sha(p)
    assert got == h, f'{p}: sha256 {got} != {h}'
H = open(INDEX, encoding='utf-8').read()
m = re.search(r'function sizeRefs\(ern\)\{\s*const z=clamp\(\(Math\.log10\(Math\.max\(ern,1e4\)\)-([\d.]+)\)/([\d.]+),-1,1\);\s*'
              r'return \{own:([\d.]+)-([\d.]+)\*z, mgt:([\d.]+)\+([\d.]+)\*z, fin:([\d.]+)\+([\d.]+)\*z', H)
ZC, ZS = float(m[1]), float(m[2])
CONSOLE = {'own': [float(m[3]), -float(m[4])], 'mgt': [float(m[5]), float(m[6])], 'fin': [float(m[7]), float(m[8])]}
zb = H[H.index('const z={', H.index('function model(s)')):]
zb = zb[:zb.index('};')]
SCALE = {k: float(re.search(k + r'\s*:\(s\.' + k + r'-RF\.' + k + r'\)/([\d.]+)', zb)[1]) for k in ('own', 'mgt', 'fin')}
ms_ = re.search(r'size:\(Math\.log10\(Math\.max\(s\.ern,1e3\)\)-Math\.log10\(([\d.e]+)\)\)/([\d.]+)', zb)
SIZE_CENTRE, SIZE_SCALE = float(ms_[1]), float(ms_[2])
mcc = re.search(r'cc\s*:\(s\.cc-([\d.]+)\)/([\d.]+)', zb)
mpl = re.search(r'plt\s*:\(s\.plt-([\d.]+)\)/([\d.]+)', zb)
mbu = re.search(r'buy\s*:\(Math\.log\(Math\.max\(s\.buyers,1\)\)-Math\.log\(I\.buyers\|\|50\)\)/([\d.]+)', zb)
CC_MED, CC_SCALE, PLT_MED, PLT_SCALE, BUY_SCALE = float(mcc[1]), float(mcc[2]), float(mpl[1]), float(mpl[2]), float(mbu[1])


def menu(sel):
    blk = re.search(r'<select id="' + sel + r'">(.*?)</select>', H, re.S)[1]
    return [(float(v), htmlmod.unescape(lab).strip()) for v, lab in re.findall(r'<option value="([\d.]+)"[^>]*>([^<]*)</option>', blk)]


MENU = {k: menu('i_' + k) for k in ('own', 'mgt', 'fin')}
VAL = {k: np.array(sorted(v for v, _ in MENU[k])) for k in MENU}
CUT = {k: (VAL[k][1:] + VAL[k][:-1]) / 2 for k in MENU}
assert (ZC, ZS) == (5.85, 1.2) and CONSOLE == {'own': [.62, -.30], 'mgt': [.42, .28], 'fin': [.55, .22]}, (ZC, ZS, CONSOLE)
assert all(LEVELS_JUDGMENT[k] == CONSOLE[k][0] for k in LEVELS_JUDGMENT), 'the judgment levels are the console\'s'
Z_FLOOR = (np.log10(1e4) - ZC) / ZS          # -1.5417: the z of the console's own SDE floor, max(ern, 1e4)
assert SCALE == {'own': .25, 'mgt': .28, 'fin': .28} and (SIZE_CENTRE, SIZE_SCALE) == (7e5, .45), (SCALE, SIZE_CENTRE, SIZE_SCALE)
assert np.allclose(CUT['own'], [.28, .57, .835]) and np.allclose(CUT['mgt'], [.22, .51, .79]) and np.allclose(CUT['fin'], [.295, .595, .85])
C_OWN_LOW, C_MGT_DEEP, C_FIN_CLEAN, C_FIN_REV, C_OWN_CRIT = CUT['own'][0], CUT['mgt'][2], CUT['fin'][1], CUT['fin'][2], CUT['own'][2]
log('console', CONSOLE, SCALE, 'size', SIZE_CENTRE, SIZE_SCALE, 'cuts', {k: CUT[k].round(3).tolist() for k in CUT})
cpi_ = pd.read_csv(CPI, parse_dates=['observation_date'])
cpi_['y'] = cpi_.observation_date.dt.year
CPI_Y = cpi_.groupby('y').CPIAUCNS.mean()
CPI_DL = float(cpi_[(cpi_.observation_date >= '2026-02-01')].CPIAUCNS.mean())   # DealLedger snapshot months with a CPI print
DEFL = dict(cpi_1992=float(CPI_Y[1992]), cpi_1998=float(CPI_Y[1998]), cpi_2003=float(CPI_Y[2003]), cpi_2007=float(CPI_Y[2007]),
            cpi_2022=float(CPI_Y[2022]), cpi_2025=float(CPI_Y[2025]), cpi_2026_feb_on=CPI_DL,
            months_2026=int((cpi_.observation_date >= '2026-02-01').sum()),
            last_month=str(cpi_.observation_date.max().date()), log10_2026_over_2003=float(np.log10(CPI_DL / CPI_Y[2003])),
            ratio_2026_over_2003=float(CPI_DL / CPI_Y[2003]), log10_2025_over_2003=float(np.log10(CPI_Y[2025] / CPI_Y[2003])))
DEF = DEFL['log10_2026_over_2003']      # 2026-dollar bridge revenue -> 2003 dollars: subtract DEF decades (revision 2: shipped)
# a 2003-dollar amount expressed in another survey year's dollars (sales windows of the replications)
IN_YEAR = {'2003': 1.0, '1998': DEFL['cpi_1998'] / DEFL['cpi_2003'], '1993': DEFL['cpi_1992'] / DEFL['cpi_2003'],
           '2007': DEFL['cpi_2007'] / DEFL['cpi_2003']}
log('deflator: CPI-U Feb-Aug 2026 mean %.3f / 2003 %.3f = %.4f (%.4f decades)' % (CPI_DL, DEFL['cpi_2003'], DEFL['ratio_2026_over_2003'], DEF))


# ------------------------------------------------------------------------------------------------ helpers
def probit(y, X, w, tol=1e-11):
    """weighted probit by Fisher scoring; returns coefficients, per-row scores (n x k) and the expected information"""
    w = np.asarray(w, float) / np.mean(w)
    y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    b[0] = norm.ppf(np.clip(np.average(y, weights=w), 1e-4, 1 - 1e-4))
    for _ in range(200):
        eta = X @ b
        P = np.clip(norm.cdf(eta), 1e-12, 1 - 1e-12); ph = norm.pdf(eta)
        U = X.T @ (w * ph * (y - P) / (P * (1 - P)))
        A = X.T @ ((w * ph ** 2 / (P * (1 - P)))[:, None] * X)
        step = np.linalg.solve(A, U)
        b = b + step
        if np.max(np.abs(step)) < tol:
            break
    eta = X @ b
    P = np.clip(norm.cdf(eta), 1e-12, 1 - 1e-12); ph = norm.pdf(eta)
    u = (w * ph * (y - P) / (P * (1 - P)))[:, None] * X
    A = X.T @ ((w * ph ** 2 / (P * (1 - P)))[:, None] * X)
    return b, u, A


def merge_singletons(strata):
    s = pd.Series(np.asarray(strata)).astype(str)
    cnt = s.map(s.value_counts())
    return np.where(cnt.values < 2, '__singletons__', s.values)


def strat_meat(u, strata):
    """sum over strata of n_h/(n_h-1) * centred cross-products of the PSU (firm) scores"""
    strata = np.asarray(strata)
    Bm = np.zeros((u.shape[1], u.shape[1]))
    for h in np.unique(strata):
        uh = u[strata == h]; nh = len(uh)
        if nh > 1:
            c = uh - uh.mean(0); Bm += nh / (nh - 1) * c.T @ c
    return Bm


def sandwich(A, Bm):
    Ai = np.linalg.inv(A)
    return Ai @ Bm @ Ai.T


def rubin(ests, covs):
    P = np.array(ests); m_ = len(P)
    W = np.mean(covs, 0); Bv = np.atleast_2d(np.cov(P.T, ddof=1)) if m_ > 1 else np.zeros_like(W)
    return P.mean(0), W + (1 + 1 / m_) * Bv, W, Bv


def share_lin(y, w, strata):
    """weighted share of a 0/1 item and its stratified linearised SE (firms as PSUs, with replacement)"""
    y = np.asarray(y, float); w = np.asarray(w, float)
    W = w.sum(); p = (w * y).sum() / W
    z = (w * (y - p) / W)[:, None]
    return p, float(np.sqrt(strat_meat(z, merge_singletons(strata))[0, 0]))


def re_pool(est, se):
    est = np.asarray(est, float); se = np.asarray(se, float); k = len(est)
    w = 1 / se ** 2; fe = (w * est).sum() / w.sum(); Q = float((w * (est - fe) ** 2).sum())
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum())) if k > 1 else 0.0
    ws = 1 / (se ** 2 + tau2); mu = (ws * est).sum() / ws.sum(); se_mu = np.sqrt(1 / ws.sum())
    q_hk = (ws * (est - mu) ** 2).sum() / max(k - 1, 1); se_hk = np.sqrt(max(q_hk, 1e-300) / ws.sum())
    return dict(mu=float(mu), se=float(se_mu), se_hksj=float(max(se_hk, se_mu)), tau=float(np.sqrt(tau2)), Q=Q, df=k - 1,
                p_Q=float(stats.chi2.sf(Q, k - 1)) if k > 1 else None, I2=float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0,
                fixed=float(fe), fixed_se=float(np.sqrt(1 / w.sum())), k=k)


def boot_counts(groups, B, rng, strata=None):
    """B x n multiplicity matrix of a cluster bootstrap (clusters = groups), optionally within strata"""
    g = pd.factorize(np.asarray(groups))[0]; n = len(g); G = g.max() + 1
    members = [np.where(g == j)[0] for j in range(G)]
    if strata is None:
        blocks = [np.arange(G)]
    else:
        st = pd.factorize(pd.Series(np.asarray(strata)).groupby(g).first().values)[0]
        blocks = [np.where(st == h)[0] for h in range(st.max() + 1)]
    Cm = np.zeros((B, n))
    for r in range(B):
        picks = np.concatenate([rng.choice(bl, len(bl)) for bl in blocks])
        cc = np.bincount(picks, minlength=G)
        for j in np.nonzero(cc)[0]:
            Cm[r, members[j]] += cc[j]
    return Cm


# ------------------------------------------------------------------------------------------------ 1. DealLedger panel
DL_FLAGS = {   # copied from the research's dl_text.py
    'absentee': r'\babsentee|semi[- ]?absentee|passive (owner|investment|income)|owner not on[- ]site|absentee[- ]run|manager[- ]run|run by (a |the )?(general )?manager|owner (is )?not (involved|required) in (the )?day',
    'full_absentee': r'(?<!semi-)(?<!semi )\babsentee',
    'owner_operated': r'owner[- ]operat|owner works (full|in the business)|owner[- ]run\b|owner is (the )?(key|primary|main)|owner performs|owner[- ]operator',
    'mgr_in_place': r'manager in place|management in place|general manager|\bgm\b|operations manager|store manager|office manager|shop (foreman|manager)|managers? (are )?in place|manager (runs|handles|oversees)|run by (a |the )?(general )?manager',
    'mgmt_team': r'management team|leadership team|(experienced|strong|seasoned|tenured) management|second[- ]tier management|management structure|layer of management',
    'staff_in': r'trained staff|experienced staff|employees? (in place|will stay)|key employees|staff in place|team in place|tenured (staff|employees|team)',
    'audited': r'\baudited\b',
    'reviewed': r'reviewed financ|review[- ]level|cpa[- ]reviewed|reviewed statements',
    'qoe': r'quality of earnings|\bqoe\b',
}
frames = []
dl_files = sorted(glob.glob(DL_SNAP + '/*/listings*.csv'))
for f in dl_files:
    try:
        d = pd.read_csv(f, low_memory=False, dtype=str)
    except Exception:
        continue
    d['snap'] = f.split('/')[-2]
    if 'description' not in d and 'raw_text' in d:
        d['description'] = d['raw_text']
    if 'url' not in d and 'source_url' in d:
        d['url'] = d['source_url']
    frames.append(d[[c for c in ['id', 'url', 'title', 'asking_price', 'cash_flow', 'revenue', 'vertical',
                                 'broker_name', 'description', 'status', 'snap'] if c in d]])
A_ = pd.concat(frames, ignore_index=True)
A_['key'] = A_['url'].fillna(A_['id'])
for c in ['asking_price', 'cash_flow', 'revenue']:
    A_[c] = pd.to_numeric(A_[c], errors='coerce')
A_['dlen'] = A_['description'].fillna('').str.len()
A_ = A_.sort_values(['key', 'snap'])
g_ = A_.groupby('key')
last_ = lambda s: s.dropna().iloc[-1] if s.notna().any() else np.nan
DL = pd.DataFrame({'cf': g_['cash_flow'].apply(last_), 'rev': g_['revenue'].apply(last_), 'ask': g_['asking_price'].apply(last_),
                   'title': g_['title'].last(), 'broker': g_['broker_name'].last(), 'first': g_['snap'].min(), 'last': g_['snap'].max()})
DL['desc'] = A_.loc[A_.groupby('key')['dlen'].idxmax()].set_index('key')['description']
DL = DL[(DL.cf >= 1e4) & (DL.cf <= 2e7)].copy()
DL['text'] = (DL.title.fillna('') + ' . ' + DL.desc.fillna('')).str.lower()
DL = DL.drop_duplicates(subset=['cf', 'ask', 'title'])
DL['has_desc'] = (DL.desc.fillna('').str.len() > 200).astype(int)
for k, p in DL_FLAGS.items():
    DL[k] = DL.text.str.contains(p, regex=True).astype(int)
DL['bid'] = DL.broker.fillna('na')
DL_SNAPS = sorted({f.split('/')[-2] for f in dl_files})
log('DealLedger listings', len(DL), 'with description', int(DL.has_desc.sum()), 'snapshots', len(DL_SNAPS), DL_SNAPS[0], DL_SNAPS[-1])
rng = np.random.default_rng(SEED)

# seller bridge
BR = DL[(DL.cf >= 3e4) & (DL.cf <= 1.5e7) & (DL.rev > DL.cf) & (DL.rev < 50 * DL.cf)]
yb, Xb = np.log10(BR.rev.values), sm.add_constant(np.log10(BR.cf.values))
rl = sm.RLM(yb, Xb).fit()
A0, G = float(rl.params[0]), float(rl.params[1])
olsb = sm.OLS(yb, Xb).fit()
Cb = boot_counts(BR.bid.values, B_BOOT, rng)
bb = []
for r in range(B_BOOT):
    ix = np.repeat(np.arange(len(BR)), Cb[r].astype(int))
    bb.append(sm.RLM(yb[ix], Xb[ix]).fit().params)
bb = np.array(bb)
V_BRIDGE = np.cov(bb.T, ddof=1)
BRIDGE = dict(a=A0, g=G, se_a=float(np.sqrt(V_BRIDGE[0, 0])), se_g=float(np.sqrt(V_BRIDGE[1, 1])), corr=float(V_BRIDGE[0, 1] / np.sqrt(V_BRIDGE[0, 0] * V_BRIDGE[1, 1])),
              log10_rev_at_708k=A0 + G * ZC, se_log10_rev_at_708k=float((bb[:, 0] + ZC * bb[:, 1]).std(ddof=1)),
              n_listings=int(len(BR)), n_brokers=int(BR.bid.nunique()), ols=[float(olsb.params[0]), float(olsb.params[1])],
              resid_sd_ols=float(np.sqrt(olsb.scale)), resid_sd_robust=float(rl.scale), naive_se_g=float(rl.bse[1]),
              filter='DealLedger listings with SDE (cash flow) $30k-$15M and revenue between 1x and 50x SDE; Huber robust line')
REV_LO26, REV_HI26 = 10 ** (A0 + G * np.log10(4.5e4)), 10 ** (A0 + G * np.log10(1.1e7))    # console z window, revenue, 2026 $
REV_LO, REV_HI = REV_LO26 / 10 ** DEF, REV_HI26 / 10 ** DEF                                  # the same window in 2003 dollars
log(f'bridge log10 rev = {A0:.4f} + {G:.4f} log10 SDE (boot SE {BRIDGE["se_a"]:.3f}, {BRIDGE["se_g"]:.4f}), n {len(BR)}; '
    f'z window = revenue ${REV_LO26 / 1e3:.0f}k-${REV_HI26 / 1e6:.1f}M (2026 $) = ${REV_LO / 1e3:.0f}k-${REV_HI / 1e6:.1f}M (2003 $)')

# DealLedger text slopes (out-of-source checks and replications) and the two-marker own spread
DT = DL[(DL.has_desc == 1) & (DL.cf >= 3e4) & (DL.cf <= 1.5e7)].copy()
DT['lx'] = np.log10(DT.cf)
Xd = np.c_[np.ones(len(DT)), DT.lx.values]
Cd = boot_counts(DT.bid.values, B_BOOT, rng)
DLP = {}
for v in ['owner_operated', 'absentee', 'full_absentee', 'mgmt_team', 'mgr_in_place', 'staff_in']:
    yv = DT[v].values.astype(float)
    b, _, _ = probit(yv, Xd, np.ones(len(DT)))
    reps = np.array([probit(yv, Xd, Cd[r])[0][1] for r in range(B_BOOT) if Cd[r] @ yv > 0])
    DLP[v] = dict(beta=float(b[1]), se=float(reps.std(ddof=1)), share=float(yv.mean()), n=int(len(DT)), n_boot=int(len(reps)))
log('DealLedger probit slopes per decade of SDE', {k: [round(v['beta'], 3), round(v['se'], 3)] for k, v in DLP.items()})
TWO = {}
two_bins, two_lab = [3e4, 1e5, 2.5e5, 5e5, 1e6, 2.5e6, 1.5e7], ['30-100k', '100-250k', '250-500k', '0.5-1M', '1-2.5M', '2.5-15M']
DT['sc'] = pd.cut(DT.cf, two_bins, labels=two_lab)
for gname in two_lab:
    x = DT[DT.sc == gname]
    for nm, lo_v in [('vs_absentee', 'absentee'), ('vs_full_absentee', 'full_absentee')]:
        ph, pl = x.owner_operated.mean(), x[lo_v].mean()
        if ph > 0 and pl > 0:
            sd_ = (C_OWN_CRIT - C_OWN_LOW) / (norm.ppf(1 - ph) - norm.ppf(pl)); m_ = C_OWN_CRIT - sd_ * norm.ppf(1 - ph)
            TWO.setdefault(nm, {})[gname] = dict(median_sde=float(x.cf.median()), n=int(len(x)), p_owner_operated=float(ph), p_absentee=float(pl),
                                                 median_own=float(m_), spread_own=float(sd_))
fin_bins, fin_lab = [1e4, 5e4, 1e5, 2.5e5, 5e5, 1e6, 2.5e6, 2e7], ['10-50k', '50-100k', '100-250k', '250-500k', '0.5-1M', '1-2.5M', '2.5-20M']
DD = DL[DL.has_desc == 1].assign(sc=lambda x: pd.cut(x.cf, fin_bins, labels=fin_lab))
DL_FIN = {k: {gname: float(DD[DD.sc == gname][k].mean()) for gname in fin_lab} for k in ['audited', 'reviewed', 'qoe']}
DL_FIN['n'] = {gname: int((DD.sc == gname).sum()) for gname in fin_lab}

# ------------------------------------------------------------------------------------------------ 2. SSBF 2003
cols03 = ['SU_ID', 'A0_IMPLICAT', 'FIN_WGT', 'A0_STRATUM', 'P2', 'PROFIT', 'P5_5', 'P1_2', 'CF_MANAGE', 'N1T3', 'N3T1', 'N3T2', 'N3T3', 'A10_2',
          'B3', 'R3', 'A0_SIC2_FIN']      # organization type, inventory and SIC: the tax-law check of the accrual item
D3 = pd.read_csv(SSBF03, usecols=cols03)
for c in cols03:
    D3.loc[D3[c] <= NEG, c] = np.nan
D3 = D3.sort_values(['A0_IMPLICAT', 'SU_ID'], kind='mergesort').reset_index(drop=True)
D3['sde'] = D3.PROFIT + D3.P5_5.fillna(0).clip(lower=0)
D3['nomgr'] = (D3.CF_MANAGE == 2).astype(float).where(D3.CF_MANAGE.isin([1, 2]))
D3['acc'] = (D3.P1_2 == 2).astype(float).where(D3.P1_2.isin([1, 2, 3]))
D3['ra'] = np.where(D3.N1T3 == 1, ((D3.N3T2 == 1) | (D3.N3T3 == 1)).astype(float), 0.0)
D3['accra'] = np.maximum(D3.acc, D3.ra).where(D3.acc.notna())          # sensitivity: accrual OR reviewed
D3['lr'] = np.log10(D3.P2.where(D3.P2 > 0))
N_FIRMS03 = int(D3.SU_ID.nunique())
W03 = D3[(D3.P2 >= SALES_LO) & (D3.P2 <= SALES_HI)].copy()
ITEMS = ['nomgr', 'acc', 'ra']


def stacked_probits(x, items, lrcol='lr', extra=None):
    """joint probits of several items on [1, log10 size (, extra)] for one implicate; stratified design covariance"""
    n = len(x); cols = [np.ones(n), x[lrcol].values] + ([x[extra].values] if extra else [])
    X = np.column_stack(cols); k = X.shape[1]
    bs, us, As = [], [], []
    for v in items:
        ok = x[v].notna().values
        b, u_ok, A = probit(x[v].values[ok], X[ok], x.FIN_WGT.values[ok])
        u = np.zeros((n, k)); u[ok] = u_ok
        bs.append(b); us.append(u); As.append(A)
    V = sandwich(block_diag(*As), strat_meat(np.hstack(us), x.A0_STRATUM.values))
    return np.concatenate(bs), V


def ssbf03_fit(data, items, lrcol='lr', extra=None):
    ests, covs = [], []
    for i in range(1, 6):
        x = data[data.A0_IMPLICAT == i]
        x = x[x[items].notna().any(axis=1)]
        b, V = stacked_probits(x, items, lrcol, extra)
        ests.append(b); covs.append(V)
    beta, T, W, Bv = rubin(ests, covs)
    return beta, T, dict(within=W, between=Bv, per_implicate=np.array(ests))


BETA03, T03, R03 = ssbf03_fit(W03, ITEMS)
N03 = {v: int(W03[(W03.A0_IMPLICAT == 1) & W03[v].notna()].shape[0]) for v in ITEMS}
PROBITS03 = {v: dict(b0=float(BETA03[2 * j]), b1=float(BETA03[2 * j + 1]), se_b0=float(np.sqrt(T03[2 * j, 2 * j])),
                     se_b1=float(np.sqrt(T03[2 * j + 1, 2 * j + 1])), n=N03[v],
                     between_implicate_sd_b1=float(np.sqrt(R03['between'][2 * j + 1, 2 * j + 1])))
             for j, v in enumerate(ITEMS)}
log('SSBF 2003 probits on log10 sales', {v: [round(p['b1'], 4), round(p['se_b1'], 4), p['n']] for v, p in PROBITS03.items()})


# ------------------------------------------------------------------------------------------------ 5. fin z-scale (before the lines: the fin line uses it)
def fin_menu_sd():
    """SD of the menu-coded reporting level by SSBF SDE-proxy class, two readings, stratified bootstrap + Rubin"""
    bins = [-np.inf, 5e4, 1e5, 2.5e5, 5e5, 1e6, 2.5e6, np.inf]
    lab = ['<50k', '50-100k', '100-250k', '250-500k', '0.5-1M', '1-2.5M', '>2.5M']
    win = lab[1:]                                         # the classes inside the console's $45k-$11M window
    v4 = VAL['fin']
    firms = D3[D3.A0_IMPLICAT == 1].SU_ID.values
    strata = D3[D3.A0_IMPLICAT == 1].A0_STRATUM.values
    Cf = boot_counts(firms, B_BOOT, np.random.default_rng(SEED + 5), strata=strata)
    Cf = np.vstack([np.ones(len(firms)), Cf])             # row 0 = the full sample
    per_imp = []
    for i in range(1, 6):
        x = D3[D3.A0_IMPLICAT == i]
        assert (x.SU_ID.values == firms).all()
        valid = x.P1_2.isin([1, 2, 3]).values
        acc = (x.P1_2 == 2).values & valid; used = (x.N1T3 == 1).values & valid
        ra = used & ((x.N3T2 == 1) | (x.N3T3 == 1)).values
        comp = used & (x.N3T1 == 1).values & ~ra
        cls = pd.cut(x.sde, bins, labels=lab).astype(str).values
        w = x.FIN_WGT.values * valid
        ind = np.column_stack([np.ones(len(x)), acc, ra, acc & ~ra, ~acc & comp, acc & used, ~acc & used, ra & acc, ra & ~acc, comp & ~acc]).astype(float)
        out = {}
        for cname in lab:
            M = ind * (cls == cname)[:, None] * w[:, None]
            S = Cf @ M                                    # (B+1) x 10 weighted sums
            tot = S[:, 0]
            pa = S[:, 1] / tot
            lb = np.column_stack([np.zeros_like(tot), S[:, 4] / tot, S[:, 3] / tot, S[:, 2] / tot]); lb[:, 0] = 1 - lb[:, 1:].sum(1)
            ra_a = S[:, 7] / np.maximum(S[:, 5], 1e-12); ra_c = S[:, 8] / np.maximum(S[:, 6], 1e-12); comp_c = S[:, 9] / np.maximum(S[:, 6], 1e-12)
            mar = np.column_stack([(1 - pa) * (1 - ra_c - comp_c), (1 - pa) * comp_c, pa * (1 - ra_a), pa * ra_a + (1 - pa) * ra_c])
            res = {}
            for nm, p in [('lower_bound', lb), ('mar', mar)]:
                mu = p @ v4; sd_ = np.sqrt(np.maximum(p @ v4 ** 2 - mu ** 2, 0))
                res[nm] = dict(shares=p[0], mean=mu, sd=sd_)
            out[cname] = dict(res=res, n=int(((cls == cname) & valid).sum()))
        per_imp.append(out)
    rows, theta_reps = [], {}
    for cname in lab:
        for nm in ['lower_bound', 'mar']:
            sds = np.array([pi[cname]['res'][nm]['sd'] for pi in per_imp])             # 5 x (B+1)
            means = np.array([pi[cname]['res'][nm]['mean'] for pi in per_imp])
            shares = np.mean([pi[cname]['res'][nm]['shares'] for pi in per_imp], 0)
            T_sd = np.mean(sds[:, 1:].var(1, ddof=1)) + 1.2 * sds[:, 0].var(ddof=1)
            T_mu = np.mean(means[:, 1:].var(1, ddof=1)) + 1.2 * means[:, 0].var(ddof=1)
            rows.append(dict(sde_class=cname, reading=nm, n=per_imp[0][cname]['n'], in_window=cname in win,
                             messy=shares[0], adequate=shares[1], clean=shares[2], reviewed=shares[3],
                             menu_mean=means[:, 0].mean(), menu_mean_se=np.sqrt(T_mu), menu_sd=sds[:, 0].mean(), menu_sd_se=np.sqrt(T_sd)))
            if cname in win:
                theta_reps.setdefault(nm, []).append(sds)
    stat = {}
    for nm in ['lower_bound', 'mar']:
        th = np.mean(theta_reps[nm], 0)                   # 5 x (B+1): equal-weight mean over the window classes
        stat[nm] = th
    both = (stat['lower_bound'] + stat['mar']) / 2
    T_both = np.mean(both[:, 1:].var(1, ddof=1)) + 1.2 * both[:, 0].var(ddof=1)
    est = float(both[:, 0].mean())
    gap = float(stat['lower_bound'][:, 0].mean() - stat['mar'][:, 0].mean())
    se_total = float(np.sqrt(T_both + (gap / 2) ** 2))
    return dict(estimate=est, se_sampling=float(np.sqrt(T_both)), se=se_total, reading_gap=gap,
                lower_bound=float(stat['lower_bound'][:, 0].mean()), mar=float(stat['mar'][:, 0].mean()),
                window_classes=win, rows=rows, B=B_BOOT)


FINSD = fin_menu_sd()
FIN_SD = rnd(FINSD['estimate'], 2)
FIN_SD_SE = rnd(FINSD['se'], 3)
log(f'fin menu-coded SD {FINSD["estimate"]:.4f} (lower bound {FINSD["lower_bound"]:.4f}, MAR {FINSD["mar"]:.4f}); SE {FINSD["se"]:.4f} '
    f'(recorded; the z-scale stays {FIN_SD_JUDGMENT} as judgment)')

# ------------------------------------------------------------------------------------------------ 3. lines (real 2003 dollars), knots
SPREAD = {'own': SCALE['own'], 'mgt': SCALE['mgt'], 'fin': SCALE['fin']}     # fin: the console's .28 (kept as judgment)
# theta = (b0,b1 nomgr; b0,b1 acc; b0,b1 ra; A0; G)
SIGMA = block_diag(T03, V_BRIDGE)
THETA = np.concatenate([BETA03, [A0, G]])
SPEC = {'own': [('nomgr', C_OWN_LOW, -1)], 'mgt': [('nomgr', C_MGT_DEEP, +1)],
        'fin_accrual': [('acc', C_FIN_CLEAN, +1)], 'fin_reviewed': [('ra', C_FIN_REV, +1)],
        'fin': [('acc', C_FIN_CLEAN, +1), ('ra', C_FIN_REV, +1)]}


def line_of(dim, spread=None, theta=THETA, sigma=SIGMA, defl=None):
    """a, b of the median line in z and their gradients over theta (fin: the average of its two items). The bridge gives
    2026-dollar revenue; defl (default DEF) converts it to the 2003 dollars of the probits (defl=0: round 1's nominal reading)"""
    s = spread if spread is not None else SPREAD['fin' if dim.startswith('fin') else dim]
    d_ = DEF if defl is None else defl
    a_tot, b_tot = 0.0, 0.0; Ja = np.zeros(len(theta)); Jb = np.zeros(len(theta))
    parts = SPEC[dim]
    for item, c, t in parts:
        j = ITEMS.index(item); b0, b1 = theta[2 * j], theta[2 * j + 1]; a0_, g_ = theta[6], theta[7]
        lr0 = a0_ + g_ * ZC - d_
        a = c + t * s * (b0 + b1 * lr0); b = t * s * b1 * g_ * ZS
        ga = np.zeros(len(theta)); gb = np.zeros(len(theta))
        ga[2 * j], ga[2 * j + 1], ga[6], ga[7] = t * s, t * s * lr0, t * s * b1, t * s * b1 * ZC
        gb[2 * j + 1], gb[7] = t * s * g_ * ZS, t * s * b1 * ZS
        a_tot += a / len(parts); b_tot += b / len(parts); Ja += ga / len(parts); Jb += gb / len(parts)
    V = np.array([Ja, Jb]) @ sigma @ np.array([Ja, Jb]).T
    return dict(a=float(a_tot), b=float(b_tot), se_a=float(np.sqrt(V[0, 0])), se_b=float(np.sqrt(V[1, 1])),
                cov_ab=float(V[0, 1]), Ja=Ja, Jb=Jb)


LINES = {k: line_of(k) for k in ['own', 'mgt', 'fin_accrual', 'fin_reviewed', 'fin']}
# fin: the two items disagree (8a); half the gap between their lines joins the sampling SE in quadrature
GAP_A = LINES['fin_accrual']['a'] - LINES['fin_reviewed']['a']
GAP_B = LINES['fin_accrual']['b'] - LINES['fin_reviewed']['b']
LINES['fin']['se_a_sampling'], LINES['fin']['se_b_sampling'] = LINES['fin']['se_a'], LINES['fin']['se_b']
LINES['fin']['se_a'] = float(np.hypot(LINES['fin']['se_a_sampling'], GAP_A / 2))
LINES['fin']['se_b'] = float(np.hypot(LINES['fin']['se_b_sampling'], GAP_B / 2))
# sampling SE without the bridge (for the replication pool, where the bridge is common to the revenue-based sources)
for k in LINES:
    Jb = LINES[k]['Jb'].copy(); Jb[6:] = 0
    LINES[k]['se_b_no_bridge'] = float(np.sqrt(Jb @ SIGMA @ Jb))
LINES_NOMINAL = {k: line_of(k, defl=0.0) for k in ['own', 'mgt', 'fin_accrual', 'fin_reviewed', 'fin']}   # round 1's reading
for k in ['fin_accrual', 'fin_reviewed', 'fin']:
    log(f'{k} (recorded, s {SPREAD["fin"]}): {LINES[k]["a"]:.4f} {LINES[k]["b"]:+.4f} z  (SE {LINES[k]["se_a"]:.4f}, {LINES[k]["se_b"]:.4f})')


# ------------------------------------------------------------------------------------------------ 4. mgt independent of the SSBF item
def perz(beta, se, dim, tail, bridged):
    """a probit slope per decade of size -> slope of the median per z on the console scale"""
    f = SCALE[dim] * ZS * (G if bridged else 1.0) * tail
    return float(f * beta), float(abs(f) * se)


def abs_table(path, sizecol='RCPSZFI'):
    z = zipfile.ZipFile(path)
    dat = [n for n in z.namelist() if n.endswith('.dat')][0]
    d = pd.read_csv(z.open(dat), sep='|', dtype=str, encoding='latin-1')
    d.columns = [c.lstrip('#') for c in d.columns]
    naics = [c for c in d.columns if c.startswith('NAICS') and c[5:].isdigit()][0]
    lab = 'QDESC_LABEL' if 'QDESC_LABEL' in d.columns else 'QDESC_TTL'
    x = d[(d.GEO_ID == '0100000US') & (d[naics] == '00') & (d.SEX == '001') & (d.ETH_GROUP == '001') & (d.RACE_GROUP == '00') & (d.VET_GROUP == '001')]
    num = lambda s: pd.to_numeric(s, errors='coerce')
    return pd.DataFrame({'q': x.QDESC.values + '|' + x[lab].values, 'size': x[sizecol].values, 'size_label': x[sizecol + '_LABEL'].values,
                         'code': x.BUSCHAR.values, 'pct': num(x.FIRMPDEMP_PCT).values, 'se': num(x.FIRMPDEMP_PCT_S).values,
                         'firms': num(x.FIRMPDEMP).values})


ABS_ITEMS = {   # copied from the research's abs_mgmt.py: (question, codes counted, denominator codes or None = all reporting)
    'kpi_3plus': ('B56|KPINUM', ['QX18', 'QX19'], None),
    'kpi_any': ('B56|KPINUM', ['QX17', 'QX18', 'QX19'], None),
    'targets_any': ('B59|BUSTARGETS', ['QZ1', 'QZ2', 'QZ3'], None),
    'targets_short_and_long': ('B59|BUSTARGETS', ['QZ3'], None),
    'promotion_on_performance': ('B61|PROMOTION', ['PR1'], ['PR1', 'PR2', 'PR3', 'PR4']),
    'underperformer_acted_6m': ('B62|UNDERPERFORM', ['RC1'], ['RC1', 'RC2', 'RC3']),
    'continuous_improvement': ('B55|SERVICEPROB', ['QS14'], ['QS12', 'QS13', 'QS14', 'QS15']),
    'custsat_monthly_plus': ('B58|CUSSATMON', ['G04A03', 'G04A04', 'G04A05', 'G04A06'], None),
}
AM = abs_table(ABS_MCB03)


def abs_share(tab, qkey, codes, den, size):
    x = tab[(tab['q'] == qkey) & (tab['size'] == size)]
    if x.empty:
        return None
    pnum = x[x.code.isin(codes)]
    p = pnum.pct.sum() / 100; v = ((pnum.se.fillna(0) / 100) ** 2).sum()
    if den is not None:
        pd_ = x[x.code.isin(den)].pct.sum() / 100
        if pd_ <= 0:
            return None
        return p / pd_, np.sqrt(v) / pd_
    return p, np.sqrt(v)


def abs_rows(tab, sizes):
    rows = []
    for item, (q, codes, den) in ABS_ITEMS.items():
        for size in sizes:
            r = abs_share(tab, q, codes, den, size)
            if r:
                rows.append(dict(item=item, size=size, p=r[0], se=r[1]))
    R_ = pd.DataFrame(rows)
    comp = R_.groupby('size').agg(p=('p', 'mean'), se=('se', lambda s: np.sqrt((s ** 2).sum()) / len(s))).reset_index()
    comp['item'] = 'composite'
    return pd.concat([R_, comp], ignore_index=True)


AR = abs_rows(AM, list(ABS_MID))
AR['receipts_mid'] = AR['size'].map(ABS_MID)
ABSP = {}
for item, x in AR.groupby('item', sort=True):
    q = norm.ppf(x.p.values); dq = x.se.values / norm.pdf(q); wq = 1 / dq ** 2
    Xa = sm.add_constant(np.log10(x.receipts_mid.values)); fa = sm.WLS(q, Xa, weights=wq).fit()
    chi = float((fa.resid ** 2 * wq).sum()); dfa = len(x) - 2; infl = np.sqrt(max(1, chi / dfa))
    ABSP[item] = dict(b1=float(fa.params[1]), se_b1=float(fa.bse[1] / np.sqrt(fa.scale) * infl), classes=int(len(x)), chi2_df=chi / dfa)
log('ABS 2023 probit slopes per decade of receipts', {k: [round(v['b1'], 3), round(v['se_b1'], 3)] for k, v in ABSP.items()})
ABS_PERZ = {k: perz(v['b1'], v['se_b1'], 'mgt', +1, True) for k, v in ABSP.items()}
item_slopes = np.array([ABS_PERZ[k][0] for k in ABS_ITEMS])
ABS_ITEM_SD = float(item_slopes.std(ddof=0))
abs_b, abs_se_sampling = ABS_PERZ['composite']
abs_se = float(np.hypot(abs_se_sampling, ABS_ITEM_SD))
dl_b, dl_se = perz(DLP['mgmt_team']['beta'], DLP['mgmt_team']['se'], 'mgt', +1, False)
MGT_SSBF = dict(b=LINES['mgt']['b'], se=LINES['mgt']['se_b_no_bridge'], se_with_bridge=LINES['mgt']['se_b'])


def vs_ssbf(mu, se):
    z_ = (MGT_SSBF['b'] - mu) / np.hypot(MGT_SSBF['se'], se)
    return dict(pool=float(mu), se=float(se), z=float(z_), p=float(2 * norm.sf(abs(z_))), consistent=bool(abs(z_) < Z_CONSISTENT))


IND_POOL = re_pool([dl_b, abs_b], [dl_se, abs_se])
IND_POOL_SAMPLING = re_pool([dl_b, abs_b], [dl_se, abs_se_sampling])
MGT_IND = dict(
    sources=dict(dealledger_management_team=dict(b=dl_b, se=dl_se, n=DLP['mgmt_team']['n'], share=DLP['mgmt_team']['share'],
                                                 item='"management team" (or leadership team, seasoned management...) in the listing text -> mgt > .79; broker SDE, no bridge'),
                 abs2023_composite=dict(b=abs_b, se=abs_se, se_sampling=abs_se_sampling, item_sd=ABS_ITEM_SD, classes=ABSP['composite']['classes'],
                                        item='mean of 8 ABS 2023 management-practice shares by receipts class -> mgt upper tail; bridge slope G')),
    abs2023_items={k: dict(b=ABS_PERZ[k][0], se=ABS_PERZ[k][1], chi2_df=ABSP[k]['chi2_df']) for k in ABS_ITEMS},
    pooled_random_effects=dict(IND_POOL, test=vs_ssbf(IND_POOL['mu'], IND_POOL['se_hksj'])),
    fixed_effect=dict(mu=IND_POOL['fixed'], se=IND_POOL['fixed_se'], test=vs_ssbf(IND_POOL['fixed'], IND_POOL['fixed_se'])),
    sampling_only_abs_se=dict(random_effects=dict(mu=IND_POOL_SAMPLING['mu'], se=IND_POOL_SAMPLING['se_hksj'], tau=IND_POOL_SAMPLING['tau'],
                                                  Q=IND_POOL_SAMPLING['Q'], p_Q=IND_POOL_SAMPLING['p_Q'],
                                                  test=vs_ssbf(IND_POOL_SAMPLING['mu'], IND_POOL_SAMPLING['se_hksj'])),
                              fixed_effect=dict(mu=IND_POOL_SAMPLING['fixed'], se=IND_POOL_SAMPLING['fixed_se'],
                                                test=vs_ssbf(IND_POOL_SAMPLING['fixed'], IND_POOL_SAMPLING['fixed_se']))),
    each_source={'dealledger': vs_ssbf(dl_b, dl_se), 'abs2023_composite': vs_ssbf(abs_b, abs_se)},
    ssbf2003=MGT_SSBF, rule='ship SSBF 2003\'s mgt slope if |z| < %.2f against the random-effects pool of the independent sources' % Z_CONSISTENT)
MGT_CONSISTENT = MGT_IND['pooled_random_effects']['test']['consistent']
MGT_IND['decision'] = 'ship SSBF 2003 mgt slope' if MGT_CONSISTENT else 'mgt stays judgment (.42 + .28z)'
log('mgt independent: DealLedger %+.4f (%.4f), ABS composite %+.4f (%.4f; sampling %.4f, item SD %.4f) -> RE %+.4f (%.4f, tau %.4f, Q %.2f p %.4f); '
    'SSBF %+.4f (%.4f) z %+.2f -> %s' % (dl_b, dl_se, abs_b, abs_se, abs_se_sampling, ABS_ITEM_SD, IND_POOL['mu'], IND_POOL['se_hksj'], IND_POOL['tau'],
                                          IND_POOL['Q'], IND_POOL['p_Q'], MGT_SSBF['b'], MGT_SSBF['se'], MGT_IND['pooled_random_effects']['test']['z'],
                                          MGT_IND['decision']))
# check: the ABS composite by employment class, 2020 and 2023 (stability of the module across vintages)
EMP_ABS = {}
for yr, path in [('2023', ABS_MCB04), ('2020', ABS20_MCB02)]:
    tb = abs_table(path, 'EMPSZFI')
    sizes = sorted(tb['size'].unique())
    er = abs_rows(tb, sizes)
    labs = dict(zip(tb['size'], tb['size_label']))
    EMP_ABS[yr] = {labs[r.size]: [float(r.p), float(r.se)] for r in er[er.item == 'composite'].itertuples()}
common = [k for k in EMP_ABS['2023'] if k in EMP_ABS['2020']]
EMP_DIFF = {k: EMP_ABS['2023'][k][0] - EMP_ABS['2020'][k][0] for k in common}
MGT_IND['abs_employment_composite_2020_vs_2023'] = dict(y2023=EMP_ABS['2023'], y2020=EMP_ABS['2020'], diff=EMP_DIFF,
                                                         max_abs_diff=float(max(abs(v) for v in EMP_DIFF.values())) if EMP_DIFF else None)
log('ABS composite by employment, 2023 - 2020:', {k[:40]: round(v, 3) for k, v in EMP_DIFF.items()})
pd.DataFrame([dict(source=k, slope_per_z=v['b'], se=v['se'], in_pool=True) for k, v in MGT_IND['sources'].items()] +
             [dict(source='abs2023_' + k, slope_per_z=v['b'], se=v['se'], in_pool=False) for k, v in MGT_IND['abs2023_items'].items()] +
             [dict(source='pool (random effects)', slope_per_z=IND_POOL['mu'], se=IND_POOL['se_hksj'], in_pool=None),
              dict(source='ssbf2003 (the shipped slope if consistent)', slope_per_z=MGT_SSBF['b'], se=MGT_SSBF['se'], in_pool=None)]
             ).to_csv(OUT + '/mgt_independent.csv', index=False, float_format='%.5g')

# the data readings in real 2003 dollars (revision 2 shipped them whole; revision 3 records them)
DATA_LINE = {k: dict(a=rnd(LINES[k]['a'], 2), b=rnd(LINES[k]['b'], 2), se_a=rnd(LINES[k]['se_a'], 3), se_b=rnd(LINES[k]['se_b'], 3))
             for k in ['own', 'mgt']}
# shipped (revision 3): the fitted slope; the level stays the console's judgment value
SHIP = {k: dict(a=LEVELS_JUDGMENT[k], a_judgment=True, b=DATA_LINE[k]['b'], se_b=DATA_LINE[k]['se_b']) for k in ['own', 'mgt']}
if not MGT_CONSISTENT:      # the decision's fallback: mgt stays the console's judgment line
    SHIP['mgt'] = dict(a=CONSOLE['mgt'][0], b=CONSOLE['mgt'][1], judgment=True)
SHIP['fin'] = dict(a=FIN_JUDGMENT[0], b=FIN_JUDGMENT[1], judgment=True)
# the mapping bounds: the same share read with the next cut point (the item may cover Moderate as well as Low, Solid as
# well as Deep); a moves by the cut difference, b does not move
MAP_BOUNDS = {}
for k, cut_alt, lab_ship, lab_alt in [('own', CUT['own'][1], 'Low only: own < %.3g' % C_OWN_LOW, 'Low or Moderate: own < %.3g' % CUT['own'][1]),
                                      ('mgt', CUT['mgt'][1], 'Deep only: mgt > %.3g' % C_MGT_DEEP, 'Solid or Deep: mgt > %.3g' % CUT['mgt'][1])]:
    c_ship = SPEC[k][0][1]
    a_alt = LINES[k]['a'] + (cut_alt - c_ship)
    MAP_BOUNDS[k] = dict(a_as_mapped=LINES[k]['a'], cut_as_mapped=float(c_ship), reading_as_mapped=lab_ship,
                         a_next_cut=float(a_alt), cut_next=float(cut_alt), reading_next_cut=lab_alt,
                         range=sorted([LINES[k]['a'], float(a_alt)]), console=CONSOLE[k][0],
                         console_inside=bool(min(LINES[k]['a'], a_alt) <= CONSOLE[k][0] <= max(LINES[k]['a'], a_alt)))
for k in ['own', 'mgt']:
    log(f'{k}: {LINES[k]["a"]:.4f} {LINES[k]["b"]:+.4f} z  (SE {LINES[k]["se_a"]:.4f}, {LINES[k]["se_b"]:.4f})  -> ship {SHIP[k]}  '
        f'console {CONSOLE[k]}; nominal (round 1) {LINES_NOMINAL[k]["a"]:.4f} {LINES_NOMINAL[k]["b"]:+.4f} z; mapping bounds '
        f'{MAP_BOUNDS[k]["range"][0]:.4f}-{MAP_BOUNDS[k]["range"][1]:.4f}')


def zof(x):
    return (np.log10(x) - ZC) / ZS


knot_rows = []
for kn, x in KNOTS:
    z = zof(x)
    row = dict(knot=kn, sde=x, z=z, revenue_2026=10 ** (A0 + G * np.log10(x)), revenue_2003=10 ** (A0 + G * np.log10(x) - DEF))
    for k in ['own', 'mgt', 'fin', 'fin_accrual', 'fin_reviewed']:
        L = LINES[k]; J = L['Ja'] + z * L['Jb']
        row[k] = L['a'] + L['b'] * z
        row[k + '_se'] = float(np.sqrt(J @ SIGMA @ J))
        row[k + '_nominal'] = LINES_NOMINAL[k]['a'] + LINES_NOMINAL[k]['b'] * z
        if k in CONSOLE:
            row[k + '_console'] = CONSOLE[k][0] + CONSOLE[k][1] * max(-1, min(1, z))
            row[k + '_shipped'] = SHIP[k]['a'] + SHIP[k]['b'] * max(-1, min(1, z))
    lrv = A0 + G * np.log10(x) - DEF                      # the knot's revenue in 2003 dollars
    for v in ITEMS:
        j = ITEMS.index(v); row['P_' + v] = float(norm.cdf(BETA03[2 * j] + BETA03[2 * j + 1] * lrv))
    row['fin_se'] = float(np.hypot(row['fin_se'], (row['fin_accrual'] - row['fin_reviewed']) / 2))
    knot_rows.append(row)
KN = pd.DataFrame(knot_rows)
KN.to_csv(OUT + '/knots.csv', index=False, float_format='%.5g')
log('knots (real)\n' + KN[['knot', 'own', 'own_se', 'own_console', 'own_nominal', 'mgt', 'mgt_se', 'mgt_console', 'mgt_nominal', 'fin', 'fin_console',
                            'P_nomgr']].round(3).to_string(index=False))

# ------------------------------------------------------------------------------------------------ 6. size z-scale
SZ = DL[(DL.cf >= 5e4) & (DL.cf <= 2e7)]
lx_sz = np.log10(SZ.cf.values)
Cs = boot_counts(SZ.bid.values, 1000, np.random.default_rng(SEED + 6))
mu_b = (Cs @ lx_sz) / Cs.sum(1); var_b = (Cs @ lx_sz ** 2) / Cs.sum(1) - mu_b ** 2
sd_reps = np.sqrt(var_b * Cs.sum(1) / (Cs.sum(1) - 1))


def iqr_sd(v):
    q1, q3 = np.percentile(v, [25, 75]); return float((q3 - q1) / (2 * norm.ppf(.75)))


SZW = DL[(DL.cf >= 4.5e4) & (DL.cf <= 1.1e7)]
SIZE = dict(sd_log10=float(lx_sz.std(ddof=1)), se=float(sd_reps.std(ddof=1)), n=int(len(SZ)), n_brokers=int(SZ.bid.nunique()),
            iqr_sd=iqr_sd(lx_sz), window_45k_11M=dict(sd=float(np.log10(SZW.cf).std(ddof=1)), iqr_sd=iqr_sd(np.log10(SZW.cf)), n=int(len(SZW))),
            median_sde=float(np.median(SZ.cf)), p10=float(np.percentile(SZ.cf, 10)), p90=float(np.percentile(SZ.cf, 90)),
            share_above_700k=float((SZ.cf > SIZE_CENTRE).mean()))
SIZE_SD = rnd(SIZE['sd_log10'], 2)
SIZE_SD_SE = rnd(SIZE['se'], 3)
# IBBA closed deals by value band: lognormal by maximum likelihood (check)
nb = pd.read_csv(IBBA_N)
cnt = nb.groupby('band').n_closed.sum()
EDG = {'<500K': (0.0, 5e5), '500K-1M': (5e5, 1e6), '1M-2M': (1e6, 2e6), '2M-5M': (2e6, 5e6), '5M-50M': (5e6, 5e7)}
lo_ = np.array([np.log10(EDG[b][0]) if EDG[b][0] > 0 else -np.inf for b in EDG]); hi_ = np.array([np.log10(EDG[b][1]) for b in EDG])
cc_ = np.array([cnt[b] for b in EDG], float)
nll = lambda p: -(cc_ * np.log(np.clip(norm.cdf((hi_ - p[0]) / np.exp(p[1])) - norm.cdf((lo_ - p[0]) / np.exp(p[1])), 1e-300, None))).sum()
ro = optimize.minimize(nll, [5.8, np.log(.6)], method='BFGS')
IB = dict(n=int(cc_.sum()), quarters=sorted(nb.period.unique().tolist()), median_value=float(10 ** ro.x[0]), sd_log10_value=float(np.exp(ro.x[1])),
          implied_sd_log10_sde=[float(np.exp(ro.x[1]) / 1.2), float(np.exp(ro.x[1]) / 1.1)],
          note='closed deals by value band (5M-50M closed at $50M); an SD of log10 SDE follows from value elasticities to SDE of 1.1-1.2')
bbs = pd.read_csv(BBS)
bbs = bbs[(bbs.metric == 'median_cash_flow') & (bbs.segment == 'all')]
BBS_MED = {str(r.period): float(r.value) for r in bbs.itertuples()}
SIZE.update(ibba_closed=IB, bizbuysell_median_cash_flow=BBS_MED,
            population_medians=dict(dealledger_listings_sde=SIZE['median_sde'], bizbuysell_closed_2025_cash_flow=BBS_MED.get('2025'),
                                    ibba_closed_median_value=IB['median_value']))
pd.DataFrame([dict(measure='sd_log10_sde_50k_20M', value=SIZE['sd_log10'], se=SIZE['se'], n=SIZE['n']),
              dict(measure='iqr_sd_50k_20M', value=SIZE['iqr_sd'], se=None, n=SIZE['n']),
              dict(measure='sd_log10_sde_45k_11M', value=SIZE['window_45k_11M']['sd'], se=None, n=SIZE['window_45k_11M']['n']),
              dict(measure='iqr_sd_45k_11M', value=SIZE['window_45k_11M']['iqr_sd'], se=None, n=SIZE['window_45k_11M']['n']),
              dict(measure='ibba_sd_log10_value', value=IB['sd_log10_value'], se=None, n=IB['n']),
              dict(measure='median_sde_listings', value=SIZE['median_sde'], se=None, n=SIZE['n'])]).to_csv(OUT + '/size_sd.csv', index=False, float_format='%.5g')
log(f'size: SD log10 SDE {SIZE["sd_log10"]:.4f} (SE {SIZE["se"]:.4f}, n {SIZE["n"]}); IQR {SIZE["iqr_sd"]:.3f}; window {SIZE["window_45k_11M"]["sd"]:.3f}; '
    f'IBBA value SD {IB["sd_log10_value"]:.3f} median ${IB["median_value"] / 1e3:.0f}k -> ship {SIZE_SD}')

# ------------------------------------------------------------------------------------------------ 7. replications
# SSBF 1998 and NSSBF 1993: the same item, one file each (no implicates)
# Windows are the decision window ($50k-$200M) in 2003 dollars, converted to each survey's own dollars with CPI-U
# (revision 2; round 1 used $50k-$200M nominal in every year). Strata are formed on the windowed sample, as in round 1.
d8_all = pd.read_csv(SSBF98, usecols=['su_id', 'c_mgr', 'P2', 'fin_wgt', 'NEWSTRAT', 'A10_2'])
d8_all = d8_all[(d8_all.P2 > 0) & d8_all.c_mgr.isin([1, 2]) & (d8_all.fin_wgt > 0)].copy()
d8_all['y'] = (d8_all.c_mgr == 2).astype(float); d8_all['lr'] = np.log10(d8_all.P2); d8_all['w'] = d8_all.fin_wgt
names93 = open(NSSBF93_NAMES).read().replace('\r', ' ').split()
d3_all = pd.read_csv(NSSBF93, header=None, names=names93, usecols=['MANAGE', 'P1', 'FIN_WGT', 'NEWSTRAT', 'TOTEMP'])
d3_all = d3_all[(d3_all.P1 > 0) & d3_all.MANAGE.isin([1, 2]) & (d3_all.FIN_WGT > 0)].copy()
d3_all['y'] = (d3_all.MANAGE == 2).astype(float); d3_all['lr'] = np.log10(d3_all.P1); d3_all['w'] = d3_all.FIN_WGT


def survey_window(dv, year, lo03, hi03):
    """rows of an SSBF 1998 / NSSBF 1993 frame whose sales lie in [lo03, hi03] 2003 dollars (converted to the survey's dollars)"""
    f = IN_YEAR[year]; x = dv[(10 ** dv.lr >= lo03 * f) & (10 ** dv.lr <= hi03 * f)].copy()
    x['st'] = merge_singletons((x.NEWSTRAT if 'NEWSTRAT' in x else x.st).values)
    return x


d8 = survey_window(d8_all, '1998', SALES_LO, SALES_HI)
d3_ = survey_window(d3_all, '1993', SALES_LO, SALES_HI)


def single_probit(x):
    X = np.c_[np.ones(len(x)), x.lr.values]
    b, u, A = probit(x.y.values, X, x.w.values)
    return b, sandwich(A, strat_meat(u, x.st.values))


B98, V98 = single_probit(d8)
B93, V93 = single_probit(d3_)
VINT = {'2003': dict(b0=PROBITS03['nomgr']['b0'], b1=PROBITS03['nomgr']['b1'], V=T03[:2, :2], n=N03['nomgr']),
        '1998': dict(b0=float(B98[0]), b1=float(B98[1]), V=V98, n=int(len(d8))),
        '1993': dict(b0=float(B93[0]), b1=float(B93[1]), V=V93, n=int(len(d3_)))}
log('hired-manager probit slopes per decade of sales', {k: [round(v['b1'], 3), round(float(np.sqrt(v['V'][1, 1])), 3), v['n']] for k, v in VINT.items()})

# SBO 2007 PUMS (employer firms), straight from the zip
sbo_cols = ['SECTOR', 'N07_EMPLOYER', 'RG', 'TABWGT', 'RECEIPTS_NOISY', 'FEDERAL', 'STATELOCAL', 'OTHERBUS', 'INDIVIDUALS']
for i in range(1, 5):
    sbo_cols += [f'PCT{i}', f'PROVIDE{i}', f'MANAGE{i}', f'FINANCIAL{i}', f'FNCTNABV{i}', f'FNCTNR{i}']
parts = []
with zipfile.ZipFile(SBO07_ZIP) as zf:
    with zf.open('pums.csv') as fh:
        for ch in pd.read_csv(fh, usecols=sbo_cols, dtype=str, chunksize=250000):
            d = ch[ch.N07_EMPLOYER == 'E']
            num = lambda c: pd.to_numeric(d[c], errors='coerce').values
            nn = len(d); lev = np.full((nn, 4), np.nan); ex = np.zeros((nn, 4), bool)
            for i in range(1, 5):      # copied from the research's sbo07_levels.py
                e = np.nan_to_num(num(f'PCT{i}'), nan=0) > 0; ex[:, i - 1] = e
                pv, mg, fn, nb_, nr = num(f'PROVIDE{i}'), num(f'MANAGE{i}'), num(f'FINANCIAL{i}'), num(f'FNCTNABV{i}'), num(f'FNCTNR{i}')
                rep = e & (nr != 1) & (np.isin(pv, [1, 2]) | np.isin(mg, [1, 2]) | np.isin(fn, [1, 2]) | np.isin(nb_, [1, 2]))
                Lv = np.where(pv == 1, 4, np.where(mg == 1, 3, np.where(fn == 1, 2, np.where(nb_ == 1, 1, np.nan))))
                lev[:, i - 1] = np.where(rep, Lv, np.nan)
            allrep = ((~np.isnan(lev)) | ~ex).all(1) & ex.any(1)
            level = np.where(allrep, np.nanmax(np.where(ex, lev, np.nan), 1), np.nan)
            parts.append(pd.DataFrame({'SECTOR': d.SECTOR.values, 'RG': num('RG'), 'TABWGT': num('TABWGT'), 'REC': num('RECEIPTS_NOISY'),
                                       'level': level, 'FEDERAL': num('FEDERAL'), 'STATELOCAL': num('STATELOCAL'),
                                       'OTHERBUS': num('OTHERBUS'), 'INDIVIDUALS': num('INDIVIDUALS')}))
SB = pd.concat(parts, ignore_index=True)
SB['fpc'] = np.sqrt(np.clip(1 - 1 / SB.TABWGT, 0, 1))
NRF = 1.992065                                          # SBO users guide: non-response factor for all variances
log('SBO 2007 employer records', len(SB), 'with an owner-function level', int(SB.level.notna().sum()))


def rg_score_var(u, x):
    """random-group variance of the weighted score totals (users guide method applied to the linearised scores)"""
    rg = x.RG.values; f = x.fpc.values[:, None]
    tot = np.array([10 * (f[rg == r] * u[rg == r]).sum(0) for r in range(1, 11)])
    c = tot - tot.mean(0)
    return c.T @ c / 90 * NRF


def sbo_probit(y, x):
    X = np.c_[np.ones(len(x)), np.log10(x.REC.values * 1e3)]
    b, u, A = probit(y, X, x.TABWGT.values)
    return b, sandwich(A, rg_score_var(u, x))


SBW = SB[(SB.REC * 1e3 >= SALES_LO * IN_YEAR['2007']) & (SB.REC * 1e3 <= SALES_HI * IN_YEAR['2007']) & SB.level.notna()].copy()
SBOP = {}
for nm, yv in [('L4_owner_provides', (SBW.level == 4).astype(float).values), ('L12_no_owner_provides_or_manages', (SBW.level <= 2).astype(float).values),
               ('L1_no_function', (SBW.level == 1).astype(float).values)]:
    b, V = sbo_probit(yv, SBW)
    SBOP[nm] = dict(b0=float(b[0]), b1=float(b[1]), se_b1=float(np.sqrt(V[1, 1])), n=int(len(SBW)))
log('SBO probit slopes per decade of receipts', {k: [round(v['b1'], 4), round(v['se_b1'], 4)] for k, v in SBOP.items()})


def replication_sources(rlo, rhi, slo, shi):
    """one slope per source and dimension: surveys fitted on revenue in [rlo, rhi] 2003 dollars (converted to each survey's
    dollars with CPI-U), listings on SDE in [slo, shi] (2026 dollars)"""
    R = {'own': {}, 'mgt': {}}; X = {'own': {}, 'mgt': {}}
    x = W03[(W03.P2 >= rlo) & (W03.P2 <= rhi)]
    b, T, _ = ssbf03_fit(x, ['nomgr'])
    n03 = int(x[(x.A0_IMPLICAT == 1) & x.nomgr.notna()].shape[0])
    for dim, t, cut in [('own', -1, '< .28'), ('mgt', +1, '> .79')]:
        b_, s_ = perz(b[1], np.sqrt(T[1, 1]), dim, t, True)
        R[dim]['ssbf2003'] = dict(b=b_, se=s_, item=f'CF_MANAGE=2 -> {dim} {cut}', n=n03, year=2003)
    for yr, key, dv in [('1998', 'ssbf1998', d8_all), ('1993', 'nssbf1993', d3_all)]:
        xx = survey_window(dv, yr, max(rlo, SALES_LO), min(rhi, SALES_HI))
        bv, Vv = single_probit(xx)
        for dim, t, cut in [('own', -1, '< .28'), ('mgt', +1, '> .79')]:
            b_, s_ = perz(bv[1], np.sqrt(Vv[1, 1]), dim, t, True)
            R[dim][key] = dict(b=b_, se=s_, item=('C_MGR' if yr == '1998' else 'MANAGE') + f'=2 -> {dim} {cut}', n=int(len(xx)), year=int(yr))
    xs = SB[(SB.REC * 1e3 >= rlo * IN_YEAR['2007']) & (SB.REC * 1e3 <= rhi * IN_YEAR['2007']) & SB.level.notna()]
    b4, V4 = sbo_probit((xs.level == 4).astype(float).values, xs)
    b12, V12 = sbo_probit((xs.level <= 2).astype(float).values, xs)
    o4 = perz(b4[1], np.sqrt(V4[1, 1]), 'own', +1, True); o12 = perz(b12[1], np.sqrt(V12[1, 1]), 'own', -1, True)
    half = abs(o4[0] - o12[0]) / 2          # SBO's two tails disagree: half the gap joins its SE (the rule used for fin)
    R['own']['sbo2007'] = dict(b=o4[0], se=float(np.hypot(o4[1], half)), se_sampling=o4[1], half_tail_gap=float(half), n=int(len(xs)), year=2007,
                               item='an owner provides the services or produces the goods -> own > .835 (SE adds half the gap to the lower-tail item)')
    X['own']['sbo2007_L12'] = dict(b=o12[0], se=o12[1], item='SBO: no owner provides or manages -> own < .28')
    m12 = perz(b12[1], np.sqrt(V12[1, 1]), 'mgt', +1, True)
    R['mgt']['sbo2007'] = dict(b=m12[0], se=m12[1], item='no owner provides or manages (financial control only or none) -> mgt > .79', n=int(len(xs)), year=2007)
    mask = ((DT.cf >= slo) & (DT.cf <= shi)).values
    for dim, flag, txt in [('own', 'owner_operated', '"owner-operated" in the listing -> own > .835 (broker SDE, no bridge)'),
                           ('mgt', 'mgmt_team', '"management team" in the listing -> mgt > .79 (broker SDE, no bridge)')]:
        yv = DT[flag].values[mask].astype(float); Xm = Xd[mask]
        bd = probit(yv, Xm, np.ones(int(mask.sum())))[0]
        reps = np.array([probit(yv, Xm, Cd[r][mask])[0][1] for r in range(B_BOOT) if Cd[r][mask] @ yv > 0])
        b_, s_ = perz(bd[1], reps.std(ddof=1), dim, +1, False)
        R[dim]['dealledger'] = dict(b=b_, se=s_, item=txt, n=int(mask.sum()), year=2026)
    return R, X


def pool_sources(R):
    out = {}
    for dim in ['own', 'mgt']:
        keys = list(R[dim]); est = [R[dim][k]['b'] for k in keys]; se = [R[dim][k]['se'] for k in keys]
        assert keys[0] == 'ssbf2003'
        full = re_pool(est, se)
        loso = {k: re_pool([e for j, e in enumerate(est) if j != i], [x for j, x in enumerate(se) if j != i])['mu'] for i, k in enumerate(keys)}
        others = re_pool(est[1:], se[1:])
        zt = (est[0] - others['mu']) / np.sqrt(se[0] ** 2 + others['se_hksj'] ** 2)
        out[dim] = dict(sources=keys, estimates={k: [R[dim][k]['b'], R[dim][k]['se']] for k in keys}, pooled=full, loso=loso,
                        loso_range=[min(loso.values()), max(loso.values())],
                        ssbf_vs_others=dict(others=others, z=float(zt), p=float(2 * norm.sf(abs(zt))), says_otherwise=bool(abs(zt) >= 1.96)))
    return out


REPL, REPL_X = replication_sources(SALES_LO, SALES_HI, 3e4, 1.5e7)      # the decision's windows
assert abs(REPL['own']['ssbf2003']['b'] - LINES['own']['b']) < 1e-9 and abs(REPL['own']['ssbf2003']['se'] - LINES['own']['se_b_no_bridge']) < 1e-6
SENS_SRC = {'own': dict(REPL_X['own']), 'mgt': {}}
for item, v in ABSP.items():
    b_, s_ = perz(v['b1'], v['se_b1'], 'mgt', +1, True)
    SENS_SRC['mgt']['abs2023_' + item] = dict(b=b_, se=s_, item='ABS 2023 ' + item + ' (structured management) -> mgt upper tail')
POOL = pool_sources(REPL)
for dim in ['own', 'mgt']:
    keys = POOL[dim]['sources']; est = [REPL[dim][k]['b'] for k in keys]; se = [REPL[dim][k]['se'] for k in keys]
    sens = {}
    if dim == 'own':
        sens['sbo_sampling_se_only'] = re_pool(est, [REPL['own']['sbo2007']['se_sampling'] if k == 'sbo2007' else x for k, x in zip(keys, se)])
        sens['sbo_item_L12_instead_of_L4'] = re_pool([SENS_SRC['own']['sbo2007_L12']['b'] if k == 'sbo2007' else e for k, e in zip(keys, est)],
                                                     [SENS_SRC['own']['sbo2007_L12']['se'] if k == 'sbo2007' else x for k, x in zip(keys, se)])
    else:
        sens['without_sbo2007'] = re_pool([e for k, e in zip(keys, est) if k != 'sbo2007'], [x for k, x in zip(keys, se) if k != 'sbo2007'])
        sens['with_abs2023_composite'] = re_pool(est + [SENS_SRC['mgt']['abs2023_composite']['b']], se + [SENS_SRC['mgt']['abs2023_composite']['se']])
        sens['with_all_abs2023_items'] = re_pool(est + [v['b'] for v in SENS_SRC['mgt'].values()], se + [v['se'] for v in SENS_SRC['mgt'].values()])
    POOL[dim].update(sensitivity=sens, shipped_slope=SHIP[dim]['b'],
                     shipped_inside_loso=bool(min(POOL[dim]['loso'].values()) - .005 <= SHIP[dim]['b'] <= max(POOL[dim]['loso'].values()) + .005))
    full = POOL[dim]['pooled']
    log(f'{dim} pool: RE {full["mu"]:+.4f} (SE {full["se"]:.4f}, HKSJ {full["se_hksj"]:.4f}, tau {full["tau"]:.4f}, I2 {full["I2"]:.2f}); '
        f'LOSO {[round(v, 4) for v in POOL[dim]["loso_range"]]}; SSBF vs others z {POOL[dim]["ssbf_vs_others"]["z"]:+.2f}; '
        f'sens {[(k, round(v["mu"], 3)) for k, v in sens.items()]}')
# the same pools with every source fitted on the console's own z window (revenue $213k-$34.6M; listings SDE $45k-$11M)
REPL_W, _ = replication_sources(REV_LO, REV_HI, 4.5e4, 1.1e7)
POOL_W = pool_sources(REPL_W)
for dim in ['own', 'mgt']:
    log(f'{dim} pool on the z window: ' + str({k: round(v['b'], 3) for k, v in REPL_W[dim].items()}) +
        f' -> RE {POOL_W[dim]["pooled"]["mu"]:+.4f} (HKSJ {POOL_W[dim]["pooled"]["se_hksj"]:.4f}); SSBF vs others z {POOL_W[dim]["ssbf_vs_others"]["z"]:+.2f}')
rep_rows = []
for wname, RR, PP in [('decision window', REPL, POOL), ('console z window', REPL_W, POOL_W)]:
    for dim in ['own', 'mgt']:
        for k, v in RR[dim].items():
            rep_rows.append(dict(window=wname, dim=dim, source=k, slope_per_z=v['b'], se=v['se'], item=v['item'], n=v['n'], in_pool=True,
                                 pool_without_it=PP[dim]['loso'][k]))
for dim in ['own', 'mgt']:
    for k, v in SENS_SRC[dim].items():
        rep_rows.append(dict(window='decision window', dim=dim, source=k, slope_per_z=v['b'], se=v['se'], item=v['item'], n=None, in_pool=False, pool_without_it=None))
pd.DataFrame(rep_rows).to_csv(OUT + '/replications.csv', index=False, float_format='%.5g')

# ------------------------------------------------------------------------------------------------ 8. checks
CHECKS = {}
# (a) parallel thresholds for fin's two items
ja, jr = ITEMS.index('acc'), ITEMS.index('ra')
d_b1 = BETA03[2 * ja + 1] - BETA03[2 * jr + 1]
v_d = T03[2 * ja + 1, 2 * ja + 1] + T03[2 * jr + 1, 2 * jr + 1] - 2 * T03[2 * ja + 1, 2 * jr + 1]
W_par = d_b1 ** 2 / v_d
Jd = LINES['fin_accrual']['Ja'] - LINES['fin_reviewed']['Ja']
se_gap_a = float(np.sqrt(Jd @ SIGMA @ Jd))
q_acc0 = BETA03[2 * ja] + BETA03[2 * ja + 1] * (A0 + G * ZC); q_ra0 = BETA03[2 * jr] + BETA03[2 * jr + 1] * (A0 + G * ZC)
CHECKS['parallel_thresholds_fin'] = dict(
    slope_accrual=float(BETA03[2 * ja + 1]), slope_reviewed=float(BETA03[2 * jr + 1]), diff=float(d_b1), se_diff=float(np.sqrt(v_d)),
    corr_items=float(T03[2 * ja + 1, 2 * jr + 1] / np.sqrt(T03[2 * ja + 1, 2 * ja + 1] * T03[2 * jr + 1, 2 * jr + 1])),
    wald_chi2=float(W_par), df=1, p=float(stats.chi2.sf(W_par, 1)), rejected=bool(stats.chi2.sf(W_par, 1) < .05),
    level_gap_at_z0=float(GAP_A), level_gap_se=se_gap_a, slope_gap_per_z=float(GAP_B),
    spread_that_reconciles_levels_at_z0=float((C_FIN_REV - C_FIN_CLEAN) / (q_acc0 - q_ra0)),
    note='the two items imply one latent line only if their probit slopes match and their levels differ by the cut gap / s')
# (b) class shares from the shipped lines (console clamp) against design-weighted SSBF 2003 shares; firms' 2003-dollar
# sales are carried to the console's SDE with the real reading of the bridge (log10 SDE = (lr + DEF - A0) / G)
EMP_BINS, EMP_LAB = [-1, 0, 4, 9, 19, 49, 99, 499], ['0', '1-4', '5-9', '10-19', '20-49', '50-99', '100-499']
SAL_BINS = [REV_LO, 5e5, 1e6, 2.5e6, 5e6, 1e7, REV_HI]
SAL_LAB = [f'{REV_LO / 1e3:.0f}k-500k', '0.5-1M', '1-2.5M', '2.5-5M', '5-10M', f'10-{REV_HI / 1e6:.1f}M']
OUT_BINS, OUT_LAB = [SALES_LO, REV_LO, REV_HI, SALES_HI * 1.0001], [f'50k-{REV_LO / 1e3:.0f}k (below the window)', 'inside', f'{REV_HI / 1e6:.1f}M-200M (above)']


def p_item_from_line(lr, a, b, cut, s, tail, clamp=True, defl=None):
    z = ((lr + (DEF if defl is None else defl) - A0) / G - ZC) / ZS
    if clamp:
        z = np.clip(z, -1, 1)
    m_ = a + b * z
    return norm.cdf((m_ - cut) / s) if tail > 0 else norm.cdf((cut - m_) / s)


CS_SPEC = {   # (item, line used, cut, spread, tail); revision 3: the data lines (real readings) and the shipped lines
    'own (data line)': ('nomgr', DATA_LINE['own']['a'], DATA_LINE['own']['b'], C_OWN_LOW, SPREAD['own'], -1),
    'mgt (data line)': ('nomgr', DATA_LINE['mgt']['a'], DATA_LINE['mgt']['b'], C_MGT_DEEP, SPREAD['mgt'], +1),
    'own (shipped)': ('nomgr', SHIP['own']['a'], SHIP['own']['b'], C_OWN_LOW, SPREAD['own'], -1),
    'mgt (shipped)': ('nomgr', SHIP['mgt']['a'], SHIP['mgt']['b'], C_MGT_DEEP, SPREAD['mgt'], +1),
    'fin accrual (its own item line)': ('acc', rnd(LINES['fin_accrual']['a'], 2), rnd(LINES['fin_accrual']['b'], 2), C_FIN_CLEAN, SPREAD['fin'], +1),
    'fin reviewed (its own item line)': ('ra', rnd(LINES['fin_reviewed']['a'], 2), rnd(LINES['fin_reviewed']['b'], 2), C_FIN_REV, SPREAD['fin'], +1),
    'own (console line)': ('nomgr', CONSOLE['own'][0], CONSOLE['own'][1], C_OWN_LOW, SCALE['own'], -1),
    'mgt (console line)': ('nomgr', CONSOLE['mgt'][0], CONSOLE['mgt'][1], C_MGT_DEEP, SCALE['mgt'], +1),
    'fin accrual (console line, kept)': ('acc', CONSOLE['fin'][0], CONSOLE['fin'][1], C_FIN_CLEAN, SCALE['fin'], +1),
    'fin reviewed (console line, kept)': ('ra', CONSOLE['fin'][0], CONSOLE['fin'][1], C_FIN_REV, SCALE['fin'], +1),
}


def class_test(data, classcol, labels, implicates=True, wcol='FIN_WGT', stcol='A0_STRATUM', spec=CS_SPEC, lrcol='lr'):
    rows, summ = [], {}
    for name, (item, a, b, cut, s, tail) in spec.items():
        chi, k = 0.0, 0
        for cname in labels:
            obs, ses, prd, ns = [], [], [], []
            for i in (range(1, 6) if implicates else [None]):
                x = data if i is None else data[data.A0_IMPLICAT == i]
                x = x[(x[classcol] == cname) & x[item].notna()]
                if len(x) < 10:
                    break
                p, se = share_lin(x[item].values, x[wcol].values, x[stcol].values)
                pr = np.average(p_item_from_line(x[lrcol].values, a, b, cut, s, tail), weights=x[wcol].values)
                obs.append(p); ses.append(se); prd.append(pr); ns.append(len(x))
            if not obs:
                continue
            ob = float(np.mean(obs)); se = float(np.sqrt(np.mean(np.square(ses)) + (1 + 1 / len(obs)) * (np.var(obs, ddof=1) if len(obs) > 1 else 0)))
            pr = float(np.mean(prd)); c2 = (ob - pr) ** 2 / se ** 2; chi += c2; k += 1
            rows.append(dict(check=name, by=classcol, cls=cname, n=ns[0], observed=ob, se=se, predicted=pr, chi2=c2))
        summ[name] = dict(chi2=chi, classes=k, p_df_k=float(stats.chi2.sf(chi, k)), p_df_k_minus_2=float(stats.chi2.sf(chi, max(k - 2, 1))))
    return rows, summ


W03['sal_c'] = pd.cut(W03.P2, SAL_BINS, labels=SAL_LAB).astype(str)
W03['emp_c'] = pd.cut(W03.A10_2, EMP_BINS, labels=EMP_LAB).astype(str)
W03['out_c'] = pd.cut(W03.P2, OUT_BINS, labels=OUT_LAB, right=False).astype(str)
rows_s, sum_s = class_test(W03, 'sal_c', SAL_LAB)
IN03 = W03[(W03.P2 >= REV_LO) & (W03.P2 <= REV_HI)]
rows_e, sum_e = class_test(IN03, 'emp_c', EMP_LAB)
rows_ea, sum_ea = class_test(W03, 'emp_c', EMP_LAB, spec={k: v for k, v in CS_SPEC.items() if k in ('own (data line)', 'mgt (data line)')})
for r_ in rows_ea:
    r_['by'] = 'emp_c (whole fit window, clamp below $%.0fk)' % (REV_LO / 1e3)
rows_o, sum_o = class_test(W03, 'out_c', [OUT_LAB[0], OUT_LAB[2]], spec={k: v for k, v in CS_SPEC.items() if k in ('own (data line)', 'mgt (data line)', 'fin accrual (console line, kept)', 'fin reviewed (console line, kept)')})
# the 2003 own line scoring the 1998 and 1993 sales-class shares (vintage hold-out)
vint_rows, vint_sum = [], {}
for yr, dv in [('1998', d8), ('1993', d3_)]:
    shift = np.log10(DEFL['cpi_2003'] / DEFL['cpi_' + ('1998' if yr == '1998' else '1992')])   # to 2003 dollars
    dv = dv.assign(lr=dv.lr + shift)
    dv = dv.assign(sal_c=pd.cut(10 ** dv.lr, SAL_BINS, labels=SAL_LAB).astype(str), nomgr=dv.y)
    r_, s_ = class_test(dv, 'sal_c', SAL_LAB, implicates=False, wcol='w', stcol='st',
                        spec={f'own (2003 data line) on {yr}': CS_SPEC['own (data line)']})
    vint_rows += r_; vint_sum.update(s_)
E0 = {r_['check']: r_ for r_ in rows_e if r_['cls'] == '0'}       # the no-employee class inside the window
CS = pd.DataFrame(rows_s + rows_e + rows_ea + rows_o + vint_rows)
CS.to_csv(OUT + '/class_shares.csv', index=False, float_format='%.5g')
CHECKS['class_shares'] = dict(by_sales_class_inside_window=sum_s, by_employment_class_inside_window=sum_e,
                              by_employment_class_whole_fit_window=sum_ea, outside_window_with_clamp=sum_o,
                              vintage_holdout=vint_sum, sales_classes=SAL_LAB, employment_classes=EMP_LAB,
                              note='predicted share = weighted mean over firms of P(item) implied by the line (console clamp; 2003-dollar sales carried '
                                   'to SDE by the real reading of the bridge); observed = FIN_WGT-weighted share, stratified linearised SE, Rubin over implicates. '
                                   'The data lines are the real readings (.60 - .15z, .43 + .17z); the shipped lines keep the console\'s levels (.62, .42), '
                                   'which this test (Low-only / Deep-only mapping) does not support or reject as levels: the item bounds them')
for nm in ['own (data line)', 'mgt (data line)', 'own (shipped)', 'mgt (shipped)', 'fin accrual (its own item line)', 'fin reviewed (its own item line)',
           'own (console line)', 'mgt (console line)', 'fin accrual (console line, kept)', 'fin reviewed (console line, kept)']:
    log(f'class shares {nm:34s} sales chi2 {sum_s[nm]["chi2"]:7.1f}/{sum_s[nm]["classes"]} (p {sum_s[nm]["p_df_k_minus_2"]:.3f})  '
        f'employment chi2 {sum_e[nm]["chi2"]:7.1f}/{sum_e[nm]["classes"]} (p {sum_e[nm]["p_df_k"]:.3f})')
log('vintage hold-out', {k: [round(v['chi2'], 1), v['classes'], round(v['p_df_k'], 3)] for k, v in vint_sum.items()})
# (c) DealLedger out-of-source slopes
CHECKS['dealledger_out_of_source'] = {}
for dim in ['own', 'mgt']:
    dl_b, dl_se = REPL[dim]['dealledger']['b'], REPL[dim]['dealledger']['se']
    zz = (dl_b - LINES[dim]['b']) / np.hypot(dl_se, LINES[dim]['se_b'])
    CHECKS['dealledger_out_of_source'][dim] = dict(dealledger=dl_b, se=dl_se, ssbf_bridge=LINES[dim]['b'], se_ssbf=LINES[dim]['se_b'], z=float(zz),
                                                   p=float(2 * norm.sf(abs(zz))), consistent=bool(abs(zz) < 1.96), console=CONSOLE[dim][1],
                                                   z_vs_console=float((dl_b - CONSOLE[dim][1]) / dl_se))
# (d) vintage stability of the hired-manager item
lr708 = A0 + G * ZC - DEF            # the revenue of a $708k-SDE seller, in 2003 dollars
vb = np.array([VINT[y]['b1'] for y in ['1993', '1998', '2003']]); vs = np.array([np.sqrt(VINT[y]['V'][1, 1]) for y in ['1993', '1998', '2003']])
lev, lev_se, lev_nom, lr_year = [], [], [], {}
for y in ['1993', '1998', '2003']:
    v = VINT[y]
    lr_y = lr708 - np.log10(DEFL['cpi_2003'] / DEFL['cpi_' + {'1993': '1992', '1998': '1998', '2003': '2003'}[y]])   # same real revenue, in year-y dollars
    lr_year[y] = lr_y
    eta = v['b0'] + v['b1'] * lr_y; gvec = np.array([1, lr_y]) * norm.pdf(eta)
    lev.append(float(norm.cdf(eta))); lev_se.append(float(np.sqrt(gvec @ v['V'] @ gvec)))
    lev_nom.append(float(norm.cdf(v['b0'] + v['b1'] * lr708)))
q_s = re_pool(vb, vs); q_l = re_pool(lev, lev_se)
CHECKS['vintage'] = dict(slopes_per_decade_sales=dict(zip(['1993', '1998', '2003'], vb.tolist())), slopes_se=dict(zip(['1993', '1998', '2003'], vs.tolist())),
                         slope_Q=q_s['Q'], slope_p=q_s['p_Q'], slopes_stable=bool(q_s['p_Q'] > .05),
                         share_at_708k=dict(zip(['1993', '1998', '2003'], lev)), share_se=dict(zip(['1993', '1998', '2003'], lev_se)),
                         share_Q=q_l['Q'], share_p=q_l['p_Q'], shares_stable=bool(q_l['p_Q'] > .05),
                         share_at_708k_nominal=dict(zip(['1993', '1998', '2003'], lev_nom)),
                         share_note='at the revenue the bridge gives $708k SDE (%.2fM), in 2003 dollars (CPI-U); the item wording changed in 2003 '
                                    '(CF_MANAGE is derived from the top three owners\' own answers; 1993/1998 asked who manages day-to-day)' % (10 ** lr708 / 1e6),
                         # revision 3: read at the same REAL revenue in each survey's dollars (revision 2 read the 2003-dollar revenue
                         # on the 1993 and 1998 probits, which put own a at .465 / .549 instead of .478 / .556)
                         own_line_by_vintage={y: dict(a=C_OWN_LOW - SCALE['own'] * (VINT[y]['b0'] + VINT[y]['b1'] * lr_year[y]), b=-SCALE['own'] * VINT[y]['b1'] * G * ZS)
                                              for y in ['1993', '1998', '2003']},
                         mgt_line_by_vintage={y: dict(a=C_MGT_DEEP + SCALE['mgt'] * (VINT[y]['b0'] + VINT[y]['b1'] * lr_year[y]), b=SCALE['mgt'] * VINT[y]['b1'] * G * ZS)
                                              for y in ['1993', '1998', '2003']},
                         n=dict(zip(['1993', '1998', '2003'], [VINT[y]['n'] for y in ['1993', '1998', '2003']])),
                         reference_revenue=10 ** lr708)
log('vintage', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in CHECKS['vintage'].items() if k in ('slope_Q', 'slope_p', 'share_Q', 'share_p')},
    {y: round(l, 3) for y, l in zip(['1993', '1998', '2003'], lev)})
# sensitivities
SENS = {}
X3 = W03[(W03.sde >= 3e4) & (W03.sde <= 1.5e7)].copy(); X3['ls'] = np.log10(X3.sde)
bj, Tj, _ = ssbf03_fit(X3, ITEMS, 'lr', 'ls')
SENS['sde_proxy_given_sales'] = {v: dict(coef_log10_sde_proxy=float(bj[3 * j + 2]), se=float(np.sqrt(Tj[3 * j + 2, 3 * j + 2])),
                                         coef_log10_sales=float(bj[3 * j + 1]), se_sales=float(np.sqrt(Tj[3 * j + 1, 3 * j + 1])))
                                 for j, v in enumerate(ITEMS)}
bd_, Td_, _ = ssbf03_fit(X3, ITEMS, 'ls')
bs_, Ts_, _ = ssbf03_fit(X3, ITEMS, 'lr')
fs = np.mean([sm.WLS(X3[X3.A0_IMPLICAT == i].ls, sm.add_constant(X3[X3.A0_IMPLICAT == i].lr), weights=X3[X3.A0_IMPLICAT == i].FIN_WGT).fit().params.iloc[1] for i in range(1, 6)])
SENS['slope_bracket_per_decade_sde'] = {v: dict(direct_sde_proxy=float(bd_[2 * j + 1]), seller_bridge=float(BETA03[2 * j + 1] * G),
                                                iv_sales_instrument=float(bs_[2 * j + 1] / fs)) for j, v in enumerate(ITEMS)}
SENS['slope_bracket_per_decade_sde']['first_stage_slope'] = float(fs)
SENS['slope_bracket_per_z'] = {dim: {k: SCALE[dim] * ZS * t * SENS['slope_bracket_per_decade_sde']['nomgr'][k] for k in ['direct_sde_proxy', 'seller_bridge', 'iv_sales_instrument']}
                               for dim, t in [('own', -1), ('mgt', 1)]}
SENS['slope_bracket_per_z']['fin'] = {k: SPREAD['fin'] * ZS * (SENS['slope_bracket_per_decade_sde']['acc'][k] + SENS['slope_bracket_per_decade_sde']['ra'][k]) / 2
                                      for k in ['direct_sde_proxy', 'seller_bridge', 'iv_sales_instrument']}
WW = W03[(W03.P2 >= REV_LO) & (W03.P2 <= REV_HI)]
bw, Tw, _ = ssbf03_fit(WW, ITEMS)
thw = np.concatenate([bw, [A0, G]]); sgw = block_diag(Tw, V_BRIDGE)
SENS['window_matched_to_z_range'] = {k: {kk: line_of(k, theta=thw, sigma=sgw)[kk] for kk in ['a', 'b', 'se_a', 'se_b']} for k in ['own', 'mgt', 'fin']}
SENS['window_matched_to_z_range']['revenue_window'] = [REV_LO, REV_HI]
sig_b = BRIDGE['resid_sd_ols']
SENS['bridge_spread_folded_in'] = {}
for k in ['own', 'mgt', 'fin']:
    parts_ = SPEC[k]; sc = []
    for item, c, t in parts_:
        b1 = BETA03[2 * ITEMS.index(item) + 1]; sc.append(1 / np.sqrt(1 + b1 ** 2 * sig_b ** 2))
    Ls = line_of(k, spread=SPREAD[k] * float(np.mean(sc)))
    SENS['bridge_spread_folded_in'][k] = dict(a=Ls['a'], b=Ls['b'], factor=float(np.mean(sc)),
                                              note='the probit is on sales; same-SDE peers mix sales with residual SD %.2f decades, so the same-sales spread is s/sqrt(1+b1^2 sd^2)' % sig_b)
SENS['nominal_round1'] = {k: {kk: LINES_NOMINAL[k][kk] for kk in ['a', 'b', 'se_a', 'se_b']} for k in ['own', 'mgt', 'fin', 'fin_accrual', 'fin_reviewed']}
SENS['nominal_round1']['note'] = ('round 1 read the bridge\'s 2026-dollar revenue on the 2003-dollar probits (no deflation); the shipped lines '
                                  'divide it by %.3f (CPI-U). Levels move, slopes do not.' % DEFL['ratio_2026_over_2003'])
D25 = DEFL['log10_2025_over_2003']
SENS['deflator_2025_annual'] = {k: {kk: line_of(k, defl=D25)[kk] for kk in ['a', 'b']} for k in ['own', 'mgt']}
SENS['deflator_2025_annual']['note'] = ('the listings\' revenue is mostly for fiscal 2025: deflating with the 2025 annual CPI-U (%.4f decades '
                                        'instead of %.4f) moves the levels by less than .002' % (D25, DEF))
SENS['deflator'] = DEFL
LFS = {k: line_of(k, spread=FIN_SD) for k in ['fin', 'fin_accrual', 'fin_reviewed']}
SENS['fin_with_menu_coded_spread'] = {k: dict(a=v['a'], b=v['b'], se_a=v['se_a'], se_b=v['se_b']) for k, v in LFS.items()}
SENS['fin_with_menu_coded_spread']['spread'] = FIN_SD
ba_, Ta_, _ = ssbf03_fit(W03, ['accra', 'ra'])
SENS['clean_or_better_as_accrual_or_reviewed'] = dict(b1=float(ba_[1]), se_b1=float(np.sqrt(Ta_[1, 1])),
                                                      a=float(C_FIN_CLEAN + SPREAD['fin'] * (ba_[0] + ba_[1] * (A0 + G * ZC - DEF))), b=float(SPREAD['fin'] * ba_[1] * G * ZS))
log('nominal (round 1)', {k: (round(v['a'], 3), round(v['b'], 3)) for k, v in SENS['nominal_round1'].items() if k in ('own', 'mgt', 'fin')},
    '| 2025 deflator', {k: (round(v['a'], 3), round(v['b'], 3)) for k, v in SENS['deflator_2025_annual'].items() if k in ('own', 'mgt')})
log('sensitivities: window', {k: (round(v['a'], 3), round(v['b'], 3)) for k, v in SENS['window_matched_to_z_range'].items() if k != 'revenue_window'},
    '| fin s=%.2f' % FIN_SD, (round(LFS['fin']['a'], 3), round(LFS['fin']['b'], 3)), '| SDE proxy given sales',
    {k: (round(v['coef_log10_sde_proxy'], 3), round(v['se'], 3)) for k, v in SENS['sde_proxy_given_sales'].items()})


# (e) the clamp: do the SSBF item shares keep moving beyond the z window ($45k and $11M of SDE)?
def ssbf03_design_fit(data, item, Xfun):
    """weighted probit of one item on a design built from log10 sales, per implicate, Rubin-combined (design SEs)"""
    ests, covs = [], []
    for i in range(1, 6):
        x = data[(data.A0_IMPLICAT == i) & data[item].notna()]
        b, u, A = probit(x[item].values, Xfun(x.lr.values), x.FIN_WGT.values)
        ests.append(b); covs.append(sandwich(A, strat_meat(u, x.A0_STRATUM.values)))
    beta, T, _, _ = rubin(ests, covs)
    return beta, T


kL, kH = np.log10(REV_LO), np.log10(REV_HI)                       # window edges in 2003-dollar sales
POP_LO03, POP_HI03 = (10 ** (A0 + G * np.log10(x_) - DEF) for x_ in POP_SDE)
spline_X = lambda lr: np.c_[np.ones(len(lr)), np.clip(lr, kL, kH), np.minimum(lr - kL, 0), np.maximum(lr - kH, 0)]
CLD = D3[(D3.P2 >= POP_LO03) & (D3.P2 <= SALES_HI)].copy()
CLAMP = dict(window_sales_2003=[REV_LO, REV_HI], population_sde=list(POP_SDE), population_sales_2003=[POP_LO03, POP_HI03],
             fit_sales_2003=[POP_LO03, SALES_HI], rule='clearly contradicted on a side if the outer slope differs from 0 at p < %.2f and does not '
             'differ from the inner slope at p < %.2f (items of the shipped dimensions: CF_MANAGE)' % (CLAMP_P_FLAT, CLAMP_P_LINEAR), items={})
clamp_rows = []
ITEM_DIM = {'nomgr': [('own', C_OWN_LOW, -1), ('mgt', C_MGT_DEEP, +1)], 'acc': [('fin', C_FIN_CLEAN, +1)], 'ra': [('fin', C_FIN_REV, +1)]}
for item in ITEMS:
    b, T = ssbf03_design_fit(CLD, item, spline_X)
    se = np.sqrt(np.diag(T))
    res = dict(inner=[float(b[1]), float(se[1])], n_below=int(((CLD.A0_IMPLICAT == 1) & (CLD.lr < kL) & CLD[item].notna()).sum()),
               n_above=int(((CLD.A0_IMPLICAT == 1) & (CLD.lr > kH) & CLD[item].notna()).sum()),
               n_inside=int(((CLD.A0_IMPLICAT == 1) & (CLD.lr >= kL) & (CLD.lr <= kH) & CLD[item].notna()).sum()))
    for side, j in (('below', 2), ('above', 3)):
        z0 = b[j] / se[j]
        dz = (b[j] - b[1]) / np.sqrt(T[j, j] + T[1, 1] - 2 * T[1, j])
        p0, pl = float(2 * norm.sf(abs(z0))), float(2 * norm.sf(abs(dz)))
        contradicted = bool(p0 < CLAMP_P_FLAT and pl >= CLAMP_P_LINEAR and np.sign(b[j]) == np.sign(b[1]))
        res[side] = dict(slope=float(b[j]), se=float(se[j]), z_vs_flat=float(z0), p_vs_flat=p0, z_vs_inner=float(dz), p_vs_inner=pl,
                         clearly_contradicted=contradicted)
        # the medians the spline implies at the window edge and at the population edge, against the shipped clamp
        lr_edge, lr_pop = (kL, np.log10(POP_LO03)) if side == 'below' else (kH, np.log10(POP_HI03))
        eta_e = b[0] + b[1] * lr_edge; eta_p = eta_e + b[j] * (lr_pop - lr_edge)
        res[side]['share_at_window_edge'] = float(norm.cdf(eta_e)); res[side]['share_at_population_edge'] = float(norm.cdf(eta_p))
        for dim, c, t in ITEM_DIM[item]:
            sd_ = SPREAD[dim]; m_e = c + t * sd_ * eta_e; m_p = c + t * sd_ * eta_p
            zpop = zof(POP_SDE[0] if side == 'below' else POP_SDE[1]); zcl = -1 if side == 'below' else 1
            # revision 3: the data line (the real reading, comparable with the spline) and the shipped line (judgment level)
            line = DATA_LINE[dim] if dim in ('own', 'mgt') else dict(a=FIN_JUDGMENT[0], b=FIN_JUDGMENT[1])
            sline = SHIP[dim] if dim in ('own', 'mgt') else dict(a=FIN_JUDGMENT[0], b=FIN_JUDGMENT[1])
            res[side][dim] = dict(spline_median_at_edge=float(m_e), spline_median_at_population_edge=float(m_p), spline_move_beyond=float(m_p - m_e),
                                  data_line_clamped=float(line['a'] + line['b'] * zcl),
                                  data_line_unclamped_at_population_edge=float(line['a'] + line['b'] * zpop),
                                  shipped_line_clamped=float(sline['a'] + sline['b'] * zcl),
                                  shipped_line_unclamped_at_population_edge=float(sline['a'] + sline['b'] * zpop), z_population_edge=float(zpop))
            clamp_rows.append(dict(item=item, dim=dim, side=side, slope=b[j], se=se[j], p_vs_flat=p0, p_vs_inner=pl, inner=b[1], inner_se=se[1],
                                   contradicted=contradicted, median_edge=m_e, median_pop_edge=m_p,
                                   data_line_clamped=res[side][dim]['data_line_clamped'],
                                   data_line_unclamped=res[side][dim]['data_line_unclamped_at_population_edge'],
                                   shipped_line_clamped=res[side][dim]['shipped_line_clamped'],
                                   shipped_line_unclamped=res[side][dim]['shipped_line_unclamped_at_population_edge']))
    CLAMP['items'][item] = res
CLAMP['contradicted_for_shipped_dims'] = bool(CLAMP['items']['nomgr']['below']['clearly_contradicted'] or CLAMP['items']['nomgr']['above']['clearly_contradicted'])
CLAMP['decision'] = 'clamp kept' if not CLAMP['contradicted_for_shipped_dims'] else 'clamp contradicted for CF_MANAGE (see open_issues); kept pending the analyst'
# observed shares beyond the window against the clamped lines (classes in 2003 dollars)
OB_BINS = [POP_LO03, REV_LO, REV_HI, POP_HI03, SALES_HI * 1.0001]
OB_LAB = ['SDE 10k-45k (below)', 'inside', 'SDE 11M-20M (above)', 'above SDE 20M (beyond the population)']
CLD['ob_c'] = pd.cut(CLD.P2, OB_BINS, labels=OB_LAB, right=False).astype(str)
rows_cl, sum_cl = class_test(CLD, 'ob_c', [OB_LAB[0], OB_LAB[2], OB_LAB[3]],
                             spec={k: v for k, v in CS_SPEC.items() if k in ('own (data line)', 'mgt (data line)', 'own (shipped)', 'mgt (shipped)',
                                                                             'fin accrual (console line, kept)', 'fin reviewed (console line, kept)')})
CLAMP['class_shares_beyond'] = dict(summary=sum_cl, rows=rows_cl)
DLW = DL[(DL.cf >= POP_SDE[0]) & (DL.cf <= POP_SDE[1])]
CLAMP['dealledger_listings_beyond'] = dict(n=int(len(DLW)), below_45k=float((DLW.cf < 4.5e4).mean()), above_11M=float((DLW.cf > 1.1e7).mean()))
pd.DataFrame(clamp_rows).to_csv(OUT + '/clamp.csv', index=False, float_format='%.5g')
CHECKS['clamp'] = CLAMP
log('clamp: ' + '; '.join('%s %s slope %+.3f (%.3f) p0 %.3f plin %.3f%s' % (it, sd_, CLAMP['items'][it][sd_]['slope'], CLAMP['items'][it][sd_]['se'],
                                                                         CLAMP['items'][it][sd_]['p_vs_flat'], CLAMP['items'][it][sd_]['p_vs_inner'],
                                                                         ' CONTRADICTED' if CLAMP['items'][it][sd_]['clearly_contradicted'] else '')
                          for it in ITEMS for sd_ in ('below', 'above')) + ' -> ' + CLAMP['decision'])
log('clamp: listings below $45k %.3f, above $11M %.4f; class shares beyond: %s' % (CLAMP['dealledger_listings_beyond']['below_45k'],
    CLAMP['dealledger_listings_beyond']['above_11M'], {k: [round(v['chi2'], 1), v['classes']] for k, v in sum_cl.items()}))

# (f) the 2003 accrual item and the tax law: accrual adoption where no rule forces it
TX = W03.copy()
TX['inv'] = (TX.R3 > 0).astype(float)
TX['ccorp'] = TX.B3.isin([4, 6, 8]).astype(float)          # C corporations and LLPs / LLCs taxed as corporations
TAX_GROUPS = {'all firms ($50k-$200M)': np.ones(len(TX), bool),
              'sales < $1M (below every 2003 cash-method threshold)': (TX.P2 < 1e6).values,
              'no inventory, not taxed as a corporation (free to use cash at any size)': ((TX.inv == 0) & (TX.ccorp == 0)).values,
              'holds inventory': (TX.inv == 1).values, 'taxed as a corporation': (TX.ccorp == 1).values}
TAXLAW = dict(rules='2003: C corporations above $5M of average receipts must use accrual (IRC 448); firms with inventories must account '
                    'for purchases and sales on accrual unless receipts are under $1M (Rev. Proc. 2001-10) or under $10M outside retail, '
                    'wholesale and manufacturing (Rev. Proc. 2002-28). TCJA (2018) raised the thresholds to $25M, indexed ($31M for 2025).',
              slopes={}, shares={})
for nm, m in TAX_GROUPS.items():
    bt, Tt, _ = ssbf03_fit(TX[m], ['acc'])
    TAXLAW['slopes'][nm] = dict(b1=float(bt[1]), se=float(np.sqrt(Tt[1, 1])), n=int((TX[m].A0_IMPLICAT == 1).sum()),
                                per_z_real=float(SPREAD['fin'] * bt[1] * G * ZS),
                                a_real=float(C_FIN_CLEAN + SPREAD['fin'] * (bt[0] + bt[1] * (A0 + G * ZC - DEF))))
TB = [5e4, 2.5e5, 1e6, 5e6, 1e7, SALES_HI * 1.0001]; TL = ['50k-250k', '250k-1M', '1M-5M', '5M-10M', '10M-200M']
TX['tc'] = pd.cut(TX.P2, TB, labels=TL, right=False).astype(str)
for nm, m in TAX_GROUPS.items():
    if nm.startswith('sales <'):
        continue
    xg = TX[m & TX.acc.notna().values]
    TAXLAW['shares'][nm] = {c: [float(np.mean([np.average(xg[(xg.A0_IMPLICAT == i) & (xg.tc == c)].acc, weights=xg[(xg.A0_IMPLICAT == i) & (xg.tc == c)].FIN_WGT)
                                               for i in range(1, 6)])), int(((xg.A0_IMPLICAT == 1) & (xg.tc == c)).sum())] for c in TL}
free_ = TAXLAW['slopes']['no inventory, not taxed as a corporation (free to use cash at any size)']
all_ = TAXLAW['slopes']['all firms ($50k-$200M)']
TAXLAW['free_over_all_slope'] = free_['b1'] / all_['b1']
pd.DataFrame([dict(group=k, **v) for k, v in TAXLAW['slopes'].items()]).to_csv(OUT + '/accrual_tax_law.csv', index=False, float_format='%.5g')
CHECKS['accrual_tax_law'] = TAXLAW
log('accrual tax law: ' + '; '.join('%s %.3f (%.3f) n %d' % (k[:30], v['b1'], v['se'], v['n']) for k, v in TAXLAW['slopes'].items()))

# ------------------------------------------------------------------------------------------------ 9. judgment checks (recorded only)
JC = {}
# cc: SBO 2007 bound
cb = SB[SB[['FEDERAL', 'STATELOCAL', 'OTHERBUS', 'INDIVIDUALS']].isin([1, 2]).all(axis=1)].copy()
cb['y'] = ((cb.OTHERBUS == 2) & (cb.FEDERAL == 2) & (cb.STATELOCAL == 2)).astype(float)


def rg_share(x, y='y'):
    w = x.TABWGT.values; yy = x[y].values; D = w.sum()
    if len(x) < 30:
        return None
    p = (w * yy).sum() / D
    u = np.array([10 * (x.fpc.values[x.RG.values == r] * w[x.RG.values == r] * (yy[x.RG.values == r] - p)).sum() for r in range(1, 11)])
    return [float(p), float(np.sqrt(((u - u.mean()) ** 2).sum() / 90 / D ** 2 * NRF)), int(len(x))]


rc_bins = [-np.inf, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, np.inf]
rc_lab = ['<100k', '100-250k', '250-500k', '0.5-1M', '1-2.5M', '2.5-5M', '5-10M', '10-25M', '25M+']
cb['rc'] = pd.cut(cb.REC, rc_bins, labels=rc_lab).astype(str)
SECTOR_NAMES = {'23': 'construction', '31': 'manufacturing', '42': 'wholesale', '44': 'retail', '48': 'transportation', '51': 'information',
                '52': 'finance', '53': 'real estate', '54': 'professional services', '56': 'admin and support', '61': 'educational',
                '62': 'health care', '71': 'arts and recreation', '72': 'food services', '81': 'other services'}
mid_ = cb[cb.rc.isin(['0.5-1M', '1-2.5M', '2.5-5M'])]
abs_c = abs_table(ABS_CSCB03)
abs_cust = {}
for size in ['522', '523', '525', '531', '533', '541', '595']:
    x = abs_c[(abs_c['q'].str.startswith('B14|')) & (abs_c['size'] == size)]
    if len(x):
        abs_cust[size] = dict(business_10pct=float(x[x.code == 'ID01'].pct.sum() / 100), individuals_10pct=float(x[x.code == 'IE'].pct.sum() / 100))
nap_txt = re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', open(NAP, encoding='utf-8', errors='replace').read())))
mn = re.search(r'Sales to top three customers as a percentage of total sales (\d+) ([\d.]+) ([\d.]+) ([\d.]+)', nap_txt)
JC['cc'] = dict(console_median=CC_MED, console_scale=CC_SCALE, console_implied_P_cc_below_10pct=float(norm.cdf((.10 - CC_MED) / CC_SCALE)),
                sbo2007_P_no_business_or_government_class_10pct={g_: rg_share(cb[cb.rc == g_]) for g_ in rc_lab},
                sbo2007_by_sector_receipts_0p5_5M={SECTOR_NAMES.get(s, s): rg_share(x) for s, x in mid_.groupby('SECTOR') if s in SECTOR_NAMES},
                abs2023_customer_classes_by_receipts=abs_cust,
                nrc2000_top3_customers=dict(n=int(mn[1]), mean=float(mn[2]), median=float(mn[3]), sd=float(mn[4]),
                                            source='NRC (2000) Surviving Supply Chain Integration, Appendix A, Table A-1 (98 small manufacturers)'),
                verdict='not identified; the SBO bound says the median cc is below .10 for firms under about $1M receipts and in B2C sectors; B2B level unknown')
# plt: Empire Flippers listing text (copied from the research's ef_flippa.py)
ef = pd.read_csv(EF_LIST, low_memory=False)
ef['np_'] = pd.to_numeric(ef.average_annual_net_profit, errors='coerce')
CH = r'(organic|search|google|seo|direct|social|facebook|instagram|pinterest|youtube|tiktok|referral|paid|ppc|ads\b|advertising|email|amazon|shopify|etsy|ebay|walmart|affiliate|app store|wholesale)'
pat1 = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*%[^.%]{0,70}?' + CH)
pat2 = re.compile(CH + r'[^.%]{0,50}?(?:accounts? for|represents?|makes? up|drives?|generates?|contributes?|brings? in)[^.%]{0,25}?(\d{1,3}(?:\.\d+)?)\s*%')
ctx = re.compile(r'traffic|visitors|sessions|sales|revenue|orders|customers|users')
chrows = []
for line_ in open(EF_TEXT, encoding='utf-8'):
    r = json.loads(line_)
    t = ' '.join(str(r.get(k, '')) for k in ['summary', 'opportunities', 'risks', 'work_required']).lower()
    best = None
    for sent in re.split(r'(?<=[.;])\s', t):
        if not ctx.search(sent):
            continue
        for m_ in pat1.finditer(sent):
            v = float(m_.group(1))
            if 0 < v <= 100 and (best is None or v > best):
                best = v
        for m_ in pat2.finditer(sent):
            v = float(m_.group(2))
            if 0 < v <= 100 and (best is None or v > best):
                best = v
    if best is not None:
        chrows.append({'listing_number': r['listing_number'], 'top_channel_pct': best})
CHD = pd.DataFrame(chrows).merge(ef[['listing_number', 'monetization_primary']], on='listing_number', how='left')
CHD = CHD[CHD.top_channel_pct >= 20]
byml = CHD.groupby('monetization_primary').top_channel_pct.agg(['count', 'median'])
byml = byml[byml['count'] >= 20].sort_values('count', ascending=False)
JC['plt'] = dict(console_median=PLT_MED, console_scale=PLT_SCALE, ef_n=int(len(CHD)), ef_median=float(CHD.top_channel_pct.median() / 100),
                 ef_p25=float(CHD.top_channel_pct.quantile(.25) / 100), ef_p75=float(CHD.top_channel_pct.quantile(.75) / 100),
                 ef_sd=float(CHD.top_channel_pct.std(ddof=1) / 100),
                 ef_median_by_monetization={k: [int(v['count']), float(v['median'] / 100)] for k, v in byml.iterrows()},
                 verdict='online analog only (listings stating a largest-channel share of 20%+); no Main-Street channel shares found')
# own scale: SBO menu-coded SD under two mappings; DealLedger two-marker spread
lv = SB[SB.level.notna()].copy(); lv['rc'] = pd.cut(lv.REC, rc_bins, labels=rc_lab).astype(str)
MAPS = {'A': np.array([.14, .42, .72, .95]), 'B': np.array([.14, .14, .42, .72])}
own_sd = {}
for g_ in rc_lab:
    x = lv[lv.rc == g_]; w = x.TABWGT.values
    p = np.array([(w * (x.level.values == k)).sum() for k in (1, 2, 3, 4)]) / w.sum()
    own_sd[g_] = {mp: dict(mean=float(p @ vv), sd=float(np.sqrt(p @ vv ** 2 - (p @ vv) ** 2))) for mp, vv in MAPS.items()}
    own_sd[g_]['level_shares'] = p.tolist()
win_rc = ['250-500k', '0.5-1M', '1-2.5M', '2.5-5M', '5-10M', '10-25M']
JC['own_scale'] = dict(console=SCALE['own'], sbo2007_menu_sd_by_receipts=own_sd,
                       sbo2007_range_in_window={mp: [min(own_sd[g_][mp]['sd'] for g_ in win_rc), max(own_sd[g_][mp]['sd'] for g_ in win_rc)] for mp in MAPS},
                       dealledger_two_marker=TWO,
                       dealledger_two_marker_spread_range=[min(v['spread_own'] for d_ in TWO.values() for v in d_.values()), max(v['spread_own'] for d_ in TWO.values() for v in d_.values())],
                       mappings='A: L1 none .14, L2 financial control .42, L3 manages .72, L4 provides .95; B: one step lower (.14, .14, .42, .72)',
                       verdict='check only: the value depends on the mapping')
JC['mgt_scale'] = dict(console=SCALE['mgt'], verdict='not found: no public microdata carry a menu-like management-depth measure (ABS and MOPS publish shares and mean scores only)')
# buyer-pool scale: Flippa watchers and IBBA offers per closed deal
fl = pd.read_csv(FLIPPA, low_memory=False)
wt = pd.to_numeric(fl.watchers, errors='coerce'); vw = pd.to_numeric(fl.views, errors='coerce'); apf = pd.to_numeric(fl.annual_profit_usd_card, errors='coerce')
lw = np.log(wt[wt > 0])
okf = (wt > 0) & (apf > 0)
rf = sm.OLS(np.log(wt[okf]), sm.add_constant(np.log(apf[okf]))).fit()
oh = pd.read_csv(IBBA_H); oh = oh[oh.measure == 'offers'].copy()
oh['cnt'] = oh.pct / oh.row_sum * oh.n_closed
off = {}
for band, x in list(oh.groupby('band')) + [('all', oh)]:
    gg = x.groupby('cat_lo').cnt.sum(); lk = np.log(gg.index.values); ww = gg.values; mu_ = (ww * lk).sum() / ww.sum()
    off[band] = dict(sd_ln_offers=float(np.sqrt((ww * (lk - mu_) ** 2).sum() / ww.sum())), deals=float(ww.sum()))
JC['buyer_pool_scale'] = dict(console=BUY_SCALE, flippa_sd_ln_watchers=float(lw.std(ddof=1)), flippa_iqr_sd_ln_watchers=iqr_sd(lw.values),
                              flippa_resid_sd_given_profit=float(np.sqrt(rf.scale)), flippa_sd_ln_views=float(np.log(vw[vw > 0]).std(ddof=1)),
                              flippa_n=int(len(lw)), flippa_n_with_profit=int(okf.sum()),
                              ibba_sd_ln_offers=off, ibba_quarters=sorted(oh.period.unique().tolist()),
                              note='IBBA offers are of closed deals, truncated at one offer; 10+ read as 10 and 6+ as 6 (lower bounds)',
                              verdict='check only: nothing counts qualified buyers contacted per Main-Street listing')
json.dump(clean(JC), open(OUT + '/judgment_checks.json', 'w'), indent=1, sort_keys=True)
log('judgment checks: cc bound <100k', JC['cc']['sbo2007_P_no_business_or_government_class_10pct']['<100k'], 'plt EF median', round(JC['plt']['ef_median'], 3),
    'own SD', JC['own_scale']['sbo2007_range_in_window'], 'buyers', round(JC['buyer_pool_scale']['flippa_sd_ln_watchers'], 3))

# ------------------------------------------------------------------------------------------------ 10. materiality (harness)
import shutil, subprocess
HARNESS = '/tmp/claude-0/fit6/harness.js'
OLD_JS = 'return {own:.62-.30*z, mgt:.42+.28*z, fin:.55+.22*z, z:z};'
d2s = lambda v: ('-' if v < 0 else '') + ('%.2f' % abs(v)).lstrip('0')
NEW_JS = 'return {own:%s-%s*z, mgt:%s+%s*z, fin:.55+.22*z, z:z};' % (d2s(SHIP['own']['a']), d2s(-SHIP['own']['b']), d2s(SHIP['mgt']['a']), d2s(SHIP['mgt']['b']))
# (b) the known bias: own and mgt read on the shipped line down to the console's own SDE floor (z = -1.54, max(ern, 1e4))
# instead of the clamp at -1; fin and the returned z keep the clamp
FLOOR_JS = ('const zf=clamp((Math.log10(Math.max(ern,1e4))-%.2f)/%.2f,%.6f,1); return {own:%s-%s*zf, mgt:%s+%s*zf, fin:.55+.22*z, z:z};'
            % (ZC, ZS, Z_FLOOR - 1e-6, d2s(SHIP['own']['a']), d2s(-SHIP['own']['b']), d2s(SHIP['mgt']['a']), d2s(SHIP['mgt']['b'])))
# (c) the hire-a-GM cost and earnings charge in the snapshot's INTERV, and intervention_costs' loaded versions
GM_COST_OLD, GM_EFF_OLD = 'cost:s=>gmSalary(s),', 'add:{ern:-gmSalary(s)}'
assert OLD_JS in H and H.count(GM_COST_OLD) == 1 and H.count(GM_EFF_OLD) == 1, 'the snapshot\'s sizeRefs or INTERV gm lines changed'
GM_RUNS = [dict(tag='snapshot', overrides=[]), dict(tag='shipped sizeRefs', overrides=[[OLD_JS, NEW_JS]])]
for lab_, hire_, load_ in GM_COST_VARIANTS:
    GM_RUNS.append(dict(tag='shipped sizeRefs + ' + lab_, overrides=[[OLD_JS, NEW_JS], [GM_COST_OLD, 'cost:s=>%d+%s*gmSalary(s),' % (hire_, load_)],
                                                                    [GM_EFF_OLD, 'add:{ern:-%s*gmSalary(s)}' % load_]]))
MAT_JS = r"""
const H=require(%s);const A=H.load();const spec=JSON.parse(process.argv[process.argv.length-1]);
const B=H.load([[spec.old,spec.new]]), F=H.load([[spec.old,spec.floor]]);
function biz(API,ind,ern){const I=API.IND[ind],RF=API.sizeRefs(ern),rev=ern/API.typMargin(ind,ern);
 return {ind,ern,rev,ask:3*ern,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,
  grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40,budget:1e5,lamT:900,theta:.75};}
const out={mat:[],bias:[],gm:[]};
/* (a) a business that enters today's medians, before and after the shipped lines */
for(const ind of spec.inds){for(const ern of spec.erns){const s=biz(A,ind,ern);const b=A.model(s),a=B.model(s);
 out.mat.push({ind,ern,value_before:b.V,value_after:a.V,pct:a.V/b.V-1,refs_before:A.sizeRefs(ern),refs_after:B.sizeRefs(ern),
  z_own_after:a.z.own,z_mgt_after:a.z.mgt});}}
/* (b) the known bias below $45k: a business at the line's unclamped own and mgt (fin at the shipped clamp), valued under
   the shipped clamp against the floor variant */
for(const ind of spec.inds){for(const ern of spec.bias_erns){const s=biz(B,ind,ern), RF=F.sizeRefs(ern), RC=B.sizeRefs(ern);
 s.own=RF.own; s.mgt=RF.mgt; const vc=B.model(s).V, vf=F.model(s).V;
 out.bias.push({ind,ern,own_unclamped:RF.own,mgt_unclamped:RF.mgt,own_clamped:RC.own,mgt_clamped:RC.mgt,fin:s.fin,
  value_clamped:vc,value_floor:vf,pct:vc/vf-1});}}
/* (c) the hire-a-GM payoff, seen through each page variant as the console does (rhoSell and optRho set first): a business
   at today's medians (frame "today": snapshot sizeRefs) and a business at the variant's own medians (frame "own": the
   review's reading; the snapshot variant is the same business in both frames); the intervention table's gm row and the
   optimiser at the default and an open budget */
const G=spec.gm_runs.map(v=>({tag:v.tag,API:H.load(v.overrides)}));
for(const frame of ["today","own"]){for(const ind of spec.gm_inds){for(const ern of spec.gm_erns){for(const g of G){const API=g.API;
 if(frame==="own"&&g.tag==="snapshot") continue;
 const s=biz(frame==="today"?A:API,ind,ern); s.rhoSell=API.bestRatio(s,0,0); s.optRho=API.bestRatio(s,s.theta,s.lamT);
 const r=API.model(s), T=API.interventionTable(s,r), i=T.findIndex(t=>t.k==="gm"), row=T[i];
 const rec={frame,ind,ern,variant:g.tag,own:s.own,mgt:s.mgt,gm_net:row.net,gm_dE:row.dE,gm_cost:row.c,gm_dV:row.dV,gm_rank:i+1,n_rows:T.length,top:T[0].k,
  gm_salary:API.gmSalary(s),opt:{}};
 for(const [lab,bud] of [["default",s.budget],["open",spec.gm_open_budget]]){ const b=API.optimize(s,r,bud,s.lamT,s.theta);
  rec.opt[lab]={budget:bud,V_keys:b.V?b.V.keys:null,U_keys:b.U?b.U.keys:null,V_has_gm:!!(b.V&&b.V.keys.includes("gm")),
   U_has_gm:!!(b.U&&b.U.keys.includes("gm")),V_net:b.V?b.V.net:null,U:b.U?b.U.U:null}; }
 out.gm.push(rec);}}}}
process.stdout.write(JSON.stringify(out));
""" % json.dumps(HARNESS)
NODE = shutil.which('node')
GM = []
if NODE and os.path.exists(HARNESS):
    spec_ = json.dumps(dict(old=OLD_JS, new=NEW_JS, floor=FLOOR_JS, inds=['home', 'rest'], erns=[x for _, x in KNOTS], bias_erns=BIAS_SDE,
                            gm_runs=GM_RUNS, gm_inds=GM_INDS, gm_erns=GM_SDE, gm_open_budget=GM_BUDGET))
    OUTJ = json.loads(subprocess.run([NODE, '-e', MAT_JS, spec_], capture_output=True, text=True, check=True).stdout)
    MAT, BIAS, GM = OUTJ['mat'], OUTJ['bias'], OUTJ['gm']
    for r_ in MAT:
        r_['pct'] = rnd(r_['pct'], 4); r_['value_before'] = round(r_['value_before']); r_['value_after'] = round(r_['value_after'])
        r_['refs_after'] = {k: rnd(v, 4) for k, v in r_['refs_after'].items()}; r_['refs_before'] = {k: rnd(v, 4) for k, v in r_['refs_before'].items()}
        r_['z_own_after'] = rnd(r_['z_own_after'], 3); r_['z_mgt_after'] = rnd(r_['z_mgt_after'], 3)
    for r_ in BIAS:
        r_['pct'] = rnd(r_['pct'], 4); r_['value_clamped'] = round(r_['value_clamped']); r_['value_floor'] = round(r_['value_floor'])
        for k in ('own_unclamped', 'mgt_unclamped', 'own_clamped', 'mgt_clamped', 'fin'):
            r_[k] = rnd(r_[k], 4)
    for r_ in GM:
        for k in ('gm_net', 'gm_dE', 'gm_cost', 'gm_dV', 'gm_salary'):
            r_[k] = round(r_[k])
        r_['own'] = rnd(r_['own'], 4); r_['mgt'] = rnd(r_['mgt'], 4)
        for o_ in r_['opt'].values():
            o_['V_net'] = round(o_['V_net']) if o_['V_net'] is not None else None
            o_['U'] = round(o_['U']) if o_['U'] is not None else None
    MATERIALITY = dict(new_line=NEW_JS, note='value of a business that enters today\'s sizeRefs medians (own, mgt, fin), before and after the '
                       'shipped own and mgt lines; other inputs at the industry medians', rows=MAT)
    BIAS_EFFECT = dict(floor_line=FLOOR_JS, rows=BIAS,
                       note='known bias below $45k of SDE: a business at the shipped line\'s unclamped own and mgt medians (the line read down to '
                            'z = %.4f, the console\'s own floor max(ern, 1e4)), fin at the shipped (clamped) median, other inputs at the industry '
                            'medians; pct = value under the shipped clamp / value with the floor - 1' % Z_FLOOR)
    pd.DataFrame(BIAS).to_csv(OUT + '/clamp_value_effect.csv', index=False)
    pd.DataFrame([dict({k: v for k, v in r_.items() if k != 'opt'}, **{'opt_%s_%s' % (b_, k): v for b_, o_ in r_['opt'].items() for k, v in o_.items()
                                                                       if k in ('V_has_gm', 'U_has_gm', 'V_net', 'U')}) for r_ in GM]).to_csv(OUT + '/gm_payoff.csv', index=False)
    log('materiality: ' + '; '.join('%s $%s %+.1f%%' % (r_['ind'], f"{r_['ern']:,.0f}", 100 * r_['pct']) for r_ in MAT))
    log('known bias below $45k (clamp vs floor): ' + '; '.join('%s $%s own %.3f vs %.3f: %+.1f%%' % (r_['ind'], f"{r_['ern']:,.0f}", r_['own_clamped'],
                                                                                                    r_['own_unclamped'], 100 * r_['pct']) for r_ in BIAS))
    for r_ in GM:
        log('GM payoff (%s) %s $%s [%s]: net %s (rank %d of %d; cost %s), optimiser default V %s U %s, open V %s U %s' % (
            r_['frame'], r_['ind'], f"{r_['ern']:,.0f}", r_['variant'], f"{r_['gm_net']:,}", r_['gm_rank'], r_['n_rows'], f"{r_['gm_cost']:,}",
            r_['opt']['default']['V_has_gm'], r_['opt']['default']['U_has_gm'], r_['opt']['open']['V_has_gm'], r_['opt']['open']['U_has_gm']))
else:
    MAT, BIAS = [], []
    MATERIALITY = dict(skipped='node or the harness is not available')
    BIAS_EFFECT = dict(skipped='node or the harness is not available')

# ------------------------------------------------------------------------------------------------ 11. tables, tests, RESULT
lines_tab = []
for k in ['own', 'mgt', 'fin', 'fin_accrual', 'fin_reviewed']:
    L = LINES[k]; LN = LINES_NOMINAL[k]
    lines_tab.append(dict(line=k, a=L['a'], b=L['b'], se_a=L['se_a'], se_b=L['se_b'], se_a_sampling=L.get('se_a_sampling', L['se_a']),
                          se_b_sampling=L.get('se_b_sampling', L['se_b']), spread=SPREAD['fin' if k.startswith('fin') else k],
                          a_nominal_round1=LN['a'], b_nominal_round1=LN['b'],
                          shipped_a=SHIP.get(k, {}).get('a'), shipped_b=SHIP.get(k, {}).get('b'), shipped_judgment=SHIP.get(k, {}).get('judgment', False),
                          console_a=CONSOLE.get(k, [None, None])[0], console_b=CONSOLE.get(k, [None, None])[1]))
pd.DataFrame(lines_tab).to_csv(OUT + '/lines.csv', index=False, float_format='%.5g')
pd.DataFrame(FINSD['rows']).to_csv(OUT + '/fin_sd.csv', index=False, float_format='%.5g')

r3 = lambda v: rnd(v, 3)
knots_js = dict(sde=[x for _, x in KNOTS])
for k in ['own', 'mgt']:
    knots_js[k + '_shipped'] = [r3(v) for v in KN[k + '_shipped']]
    knots_js[k + '_console'] = [r3(v) for v in KN[k + '_console']]
    knots_js[k + '_data_real'] = [r3(v) for v in KN[k]]
    knots_js[k + '_data_real_se'] = [r3(v) for v in KN[k + '_se']]
    knots_js[k + '_data_nominal'] = [r3(v) for v in KN[k + '_nominal']]
knots_js['P_no_owner_runs_day_to_day'] = [r3(v) for v in KN['P_nomgr']]
knots_js['revenue_2003_dollars'] = [int(round(v, -3)) for v in KN['revenue_2003']]
knots_js['fin_console'] = [r3(v) for v in KN['fin_console']]
knots_js['note'] = ('medians at SDE $45k / $150k / $708k / $3M / $11M: *_shipped = the shipped line (console level, fitted slope); *_console = '
                    'today\'s line; *_data_real / *_data_nominal = the SSBF readings under the Low-only / Deep-only mapping (SEs sampling only)')
repl_js = {}
for dim in ['own', 'mgt']:
    P_ = POOL[dim]
    repl_js[dim] = {k: [r3(v['b']), r3(v['se'])] for k, v in REPL[dim].items()}
    repl_js[dim].update(pooled=[r3(P_['pooled']['mu']), r3(P_['pooled']['se_hksj'])], tau=r3(P_['pooled']['tau']),
                        loso=[r3(P_['loso_range'][0]), r3(P_['loso_range'][1])],
                        ssbf_vs_others_z=rnd(P_['ssbf_vs_others']['z'], 2),
                        pooled_on_console_z_window=[r3(POOL_W[dim]['pooled']['mu']), r3(POOL_W[dim]['pooled']['se_hksj'])],
                        ssbf2003_on_console_z_window=[r3(REPL_W[dim]['ssbf2003']['b']), r3(REPL_W[dim]['ssbf2003']['se'])])
MI = MGT_IND; MIT = MI['pooled_random_effects']['test']
repl_js['mgt_independent'] = dict(
    dealledger_management_team=[r3(MI['sources']['dealledger_management_team']['b']), r3(MI['sources']['dealledger_management_team']['se'])],
    abs2023_management_composite=[r3(MI['sources']['abs2023_composite']['b']), r3(MI['sources']['abs2023_composite']['se'])],
    abs2023_items_range=[r3(min(v['b'] for v in MI['abs2023_items'].values())), r3(max(v['b'] for v in MI['abs2023_items'].values()))],
    pooled=[r3(MIT['pool']), r3(MIT['se'])], tau=r3(MI['pooled_random_effects']['tau']), Q=rnd(MI['pooled_random_effects']['Q'], 2),
    p_Q=float(f"{MI['pooled_random_effects']['p_Q']:.2g}"), ssbf2003=[r3(MGT_SSBF['b']), r3(MGT_SSBF['se'])], z=rnd(MIT['z'], 2),
    consistent=MGT_CONSISTENT, decision=MI['decision'],
    fixed_effect_abs_sampling_se_only=[r3(MI['sampling_only_abs_se']['fixed_effect']['mu']), r3(MI['sampling_only_abs_se']['fixed_effect']['se']),
                                       rnd(MI['sampling_only_abs_se']['fixed_effect']['test']['z'], 2)],
    note=('slopes per z (s .28). ABS composite = mean of 8 management-practice shares by receipts class; its SE adds the SD of the 8 item '
          'slopes (%.3f). Random-effects pool of the two sources (the sources disagree with each other: Q %.2f); SSBF 2003 lies between '
          'them. A fixed-effect pool with ABS\'s sampling SE alone (Q %.1f, p %.2g) would reject SSBF, but that pool is itself rejected.'
          % (ABS_ITEM_SD, MI['pooled_random_effects']['Q'], MI['sampling_only_abs_se']['random_effects']['Q'],
             MI['sampling_only_abs_se']['random_effects']['p_Q'])))
repl_js['items'] = {dim: {k: v['item'] for k, v in REPL[dim].items()} for dim in ['own', 'mgt']}
repl_js['note'] = ('slope per z on the console scale (own s .25, mgt s .28); [estimate, SE]; surveys fitted on sales $50k-$200M in 2003 dollars '
                   '(converted to each survey\'s dollars with CPI-U), listings on SDE $30k-$15M; pooled = DerSimonian-Laird with a Knapp-Hartung SE; '
                   'loso = range of the pool leaving one source out; revenue-based sources use the bridge slope G; SBO own SE includes half the gap '
                   'between its two tails; *_on_console_z_window = every source refitted on revenue $%.0fk-$%.1fM (2003 dollars; listings SDE '
                   '$45k-$11M). Slopes do not depend on the dollar basis or on the cut point' % (REV_LO / 1e3, REV_HI / 1e6))
pt = CHECKS['parallel_thresholds_fin']; vt = CHECKS['vintage']; CL_ = CHECKS['clamp']; TXL = CHECKS['accrual_tax_law']
cl_side = lambda it, sd_: dict(slope=r3(CL_['items'][it][sd_]['slope']), se=r3(CL_['items'][it][sd_]['se']),
                                p_flat=float(f"{CL_['items'][it][sd_]['p_vs_flat']:.2g}"), p_inner=float(f"{CL_['items'][it][sd_]['p_vs_inner']:.2g}"),
                                contradicted=CL_['items'][it][sd_]['clearly_contradicted'])
BEYOND = {(r_['check'], r_['cls']): r_ for r_ in CL_['class_shares_beyond']['rows']}
OWN_B, OWN_B_SHIP = BEYOND[('own (data line)', 'SDE 10k-45k (below)')], BEYOND[('own (shipped)', 'SDE 10k-45k (below)')]
OWN_A = BEYOND[('own (data line)', 'SDE 11M-20M (above)')]
own_med_obs = float(C_OWN_LOW - SPREAD['own'] * norm.ppf(OWN_B['observed']))        # the own median the observed share implies (Low-only mapping)
own_med_clamped = float(C_OWN_LOW - SPREAD['own'] * norm.ppf(OWN_B['predicted']))
nb_own = CL_['items']['nomgr']['below']['own']
BIAS_PCT = {}
for r_ in BIAS:
    BIAS_PCT.setdefault(r_['ern'], []).append(r_['pct'])
bias_value = dict(sde=BIAS_SDE, pct=[rnd(100 * float(np.mean(BIAS_PCT[x])), 2) for x in BIAS_SDE] if BIAS else None,
                  industries_max_gap_pct=rnd(100 * max(max(v) - min(v) for v in BIAS_PCT.values()), 3) if BIAS else None,
                  basis='value under the shipped clamp / value with the line read down to z = %.2f (the console\'s floor, max(ern, 1e4)) - 1, '
                        'a business at the unclamped own and mgt medians, other inputs at the industry medians (home and restaurants, mean)' % Z_FLOOR)
known_bias = dict(
    status='known bias, recorded (analyst): the clamp at z = -1 stays; below $45k of SDE it understates the own median and overstates the mgt median',
    evidence=dict(hired_manager_share_observed=r3(OWN_B['observed']), se=r3(OWN_B['se']), n=OWN_B['n'],
                  under_clamp_data_line=r3(OWN_B['predicted']), z=rnd((OWN_B['observed'] - OWN_B['predicted']) / OWN_B['se'], 2),
                  under_clamp_shipped_line=r3(OWN_B_SHIP['predicted']), what='SSBF 2003 firms whose revenue the real bridge places at SDE $10k-$45k: '
                  'share with no owner running day-to-day (CF_MANAGE = 2), FIN_WGT-weighted, against the share the clamped line predicts'),
    own_median=dict(implied_by_share=r3(own_med_obs), clamped_data_line=r3(own_med_clamped),
                    at_10k=dict(shipped_clamped=r3(nb_own['shipped_line_clamped']), shipped_unclamped=r3(nb_own['shipped_line_unclamped_at_population_edge']),
                                data_clamped=r3(nb_own['data_line_clamped']), data_unclamped=r3(nb_own['data_line_unclamped_at_population_edge']),
                                spline=r3(nb_own['spline_median_at_population_edge']))),
    listings_below_45k=r3(CL_['dealledger_listings_beyond']['below_45k']), value_effect_pct=bias_value,
    above_11M=dict(observed=r3(OWN_A['observed']), se=r3(OWN_A['se']), under_clamp_data_line=r3(OWN_A['predicted']),
                   z=rnd((OWN_A['observed'] - OWN_A['predicted']) / OWN_A['se'], 2), n=OWN_A['n'],
                   listings_above_11M=rnd(CL_['dealledger_listings_beyond']['above_11M'], 4)))
level_readings = dict(
    own=dict(shipped=SHIP['own']['a'], real_2003=rnd(LINES['own']['a'], 2), se_sampling=r3(LINES['own']['se_a']), nominal=rnd(LINES_NOMINAL['own']['a'], 2),
             unrounded=[r3(LINES['own']['a']), r3(LINES_NOMINAL['own']['a'])]),
    mgt=dict(shipped=SHIP['mgt']['a'], real_2003=rnd(LINES['mgt']['a'], 2), se_sampling=r3(LINES['mgt']['se_a']), nominal=rnd(LINES_NOMINAL['mgt']['a'], 2),
             unrounded=[r3(LINES['mgt']['a']), r3(LINES_NOMINAL['mgt']['a'])]),
    dollars=('real: the seller bridge\'s 2026 revenue divided by CPI-U %.3f (mean of Feb-Aug 2026 %.2f over the 2003 average %.2f) before the '
             'SSBF 2003 probits are read; nominal: undeflated (round 1); the 2025 annual CPI moves the real readings by under .002'
             % (DEFL['ratio_2026_over_2003'], CPI_DL, DEFL['cpi_2003'])),
    note=('data readings at z = 0 under the Low-only / Deep-only mapping; their SEs are sampling only (SSBF design and the bridge) and leave out '
          'the mapping, the survey year and the employment mix. Not shipped: the levels stay the console\'s judgment (.62, .42)'))
mapping_bounds = {k: dict(range=[r3(MAP_BOUNDS[k]['range'][0]), r3(MAP_BOUNDS[k]['range'][1])],
                          readings={MAP_BOUNDS[k]['reading_as_mapped']: r3(MAP_BOUNDS[k]['a_as_mapped']),
                                    MAP_BOUNDS[k]['reading_next_cut']: r3(MAP_BOUNDS[k]['a_next_cut'])},
                          console=MAP_BOUNDS[k]['console'], console_inside=MAP_BOUNDS[k]['console_inside']) for k in ['own', 'mgt']}
mapping_bounds['item'] = ('SSBF 2003 CF_MANAGE = 2, no owner responsible for day-to-day management: %.3f of firms at the real revenue of a $708k-SDE '
                          'seller' % float(KN.loc[KN.knot == '708k', 'P_nomgr'].iloc[0]))
mapping_bounds['note'] = ('the item fits Moderate ("owner sets direction only") as well as Low, and Solid as well as Deep, so the share bounds the '
                          'level rather than identifying it: own .60 (Low only) to .89 (Low or Moderate), mgt .15 (Solid or Deep) to .43 (Deep only). '
                          'The slope does not depend on the cut. The console\'s .62 and .42 lie inside both ranges')
vintage_js = dict(years=[1993, 1998, 2003], share_at_708k=[r3(vt['share_at_708k'][y]) for y in ['1993', '1998', '2003']],
                  share_p=float(f"{vt['share_p']:.2g}"),
                  own_a=[rnd(vt['own_line_by_vintage'][y]['a'], 2) for y in ['1993', '1998', '2003']],
                  mgt_a=[rnd(vt['mgt_line_by_vintage'][y]['a'], 2) for y in ['1993', '1998', '2003']],
                  slopes=[r3(vt['slopes_per_decade_sales'][y]) for y in ['1993', '1998', '2003']], slopes_se=[r3(vt['slopes_se'][y]) for y in ['1993', '1998', '2003']],
                  slope_p=float(f"{vt['slope_p']:.2g}"),
                  holdout_chi2_2003_line=[rnd(vint_sum['own (2003 data line) on 1998']['chi2'], 1), rnd(vint_sum['own (2003 data line) on 1993']['chi2'], 1)],
                  note=('hired manager runs day-to-day: probit slope per decade of sales, the share at the real revenue of a $708k-SDE seller (in each '
                        'survey\'s dollars) and the own / mgt levels it implies (Low-only / Deep-only mapping). Levels drift (p %.1g), slopes do not; '
                        'holdout_chi2 = the 2003 own data line against the 1998 and 1993 sales-class shares (6 classes); 2003\'s item is built from '
                        'the top three owners\' answers' % vt['share_p']))
checks_js = dict(
    level_readings=level_readings, mapping_bounds=mapping_bounds, vintage=vintage_js,
    slopes=repl_js,
    clamp=dict(kept=not CL_['contradicted_for_shipped_dims'], z='clamp((log10 SDE - %.2f)/%.2f, -1, 1)' % (ZC, ZS), rule=CL_['rule'],
               no_owner_runs_day_to_day=dict(inner=[r3(CL_['items']['nomgr']['inner'][0]), r3(CL_['items']['nomgr']['inner'][1])],
                                             below=cl_side('nomgr', 'below'), above=cl_side('nomgr', 'above')),
               accrual=dict(below=cl_side('acc', 'below'), above=cl_side('acc', 'above')),
               reviewed=dict(below=cl_side('ra', 'below'), above=cl_side('ra', 'above')),
               known_bias_below_45k=known_bias,
               note='spline probits of each SSBF 2003 item on log10 sales (2003 dollars) with knots at the window edges, fitted from the revenue '
                    'of $10k SDE to $200M; slopes per decade of sales; p_flat tests the clamp (outer slope 0), p_inner tests a straight line'),
    class_shares={key: dict(sales=[rnd(sum_s[nm]['chi2'], 1), sum_s[nm]['classes'], float(f"{sum_s[nm]['p_df_k_minus_2']:.2g}")],
                            employment=[rnd(sum_e[nm]['chi2'], 1), sum_e[nm]['classes'], float(f"{sum_e[nm]['p_df_k']:.2g}")])
                  for key, nm in [('own_data', 'own (data line)'), ('mgt_data', 'mgt (data line)'), ('own_shipped', 'own (shipped)'),
                                  ('mgt_shipped', 'mgt (shipped)'), ('own_console', 'own (console line)'), ('mgt_console', 'mgt (console line)')]},
    class_shares_note=('[chi2, classes, p]: SSBF 2003 FIN_WGT shares by sales class (df = classes - 2) and by employment class (df = classes), firms '
                       'whose 2003-dollar revenue the real bridge places inside z = -1..1, predicted by the line (spread .25 / .28) under the '
                       'Low-only / Deep-only mapping: the data lines are the readings; the shipped lines carry the judgment levels, which this '
                       'test cannot judge (the item bounds the level)'),
    dealledger_oos={dim: dict(slope=r3(v['dealledger']), se=r3(v['se']), ssbf=r3(v['ssbf_bridge']), z=rnd(v['z'], 2)) for dim, v in CHECKS['dealledger_out_of_source'].items()},
    knots=knots_js,
    spreads_used=dict(own=SPREAD['own'], mgt=SPREAD['mgt']),
    bridge=dict(a=r3(A0), g=r3(G), se_a=r3(BRIDGE['se_a']), se_g=rnd(BRIDGE['se_g'], 4), n=BRIDGE['n_listings'], cpi_ratio=rnd(DEFL['ratio_2026_over_2003'], 4)),
    size_sd=dict(n=SIZE['n'], brokers=SIZE['n_brokers'], window='DealLedger listings, SDE $50k-$20M (broker-cluster bootstrap SE)',
                 iqr_sd=r3(SIZE['iqr_sd']), window_45k_11M=r3(SIZE['window_45k_11M']['sd']),
                 ibba_closed_implied=[r3(IB['implied_sd_log10_sde'][0]), r3(IB['implied_sd_log10_sde'][1])], centre=int(SIZE_CENTRE),
                 centre_note='the $700k centre is a convention (the %.0fth percentile of listed SDE)' % (100 * (1 - SIZE['share_above_700k']))),
    n=dict(ssbf2003_firms=N_FIRMS03, ssbf2003_in_fit=N03, ssbf1998=VINT['1998']['n'], nssbf1993=VINT['1993']['n'], sbo2007=SBOP['L4_owner_provides']['n'],
           dealledger_text=DLP['owner_operated']['n'], dealledger_size=SIZE['n'], bridge=BRIDGE['n_listings'], abs2023_classes=ABSP['composite']['classes']))
fin_items_real = {k: [r3(LINES['fin_' + k]['a']), r3(LINES['fin_' + k]['b']), r3(LINES['fin_' + k]['se_a']), r3(LINES['fin_' + k]['se_b'])]
                  for k in ('accrual', 'reviewed')}
fs_rows = [r_ for r_ in FINSD['rows'] if r_['in_window']]
not_shipped_js = dict(
    fin=dict(kept=list(FIN_JUDGMENT), spread_kept=FIN_SD_JUDGMENT,
             items_real_2003=dict(fin_items_real, average=[r3(LINES['fin']['a']), r3(LINES['fin']['b'])], spread=SPREAD['fin'],
                                  form='[a, b, se_a, se_b]: median = a + b z'),
             items_real_menu_coded_spread=dict(accrual=[r3(LFS['fin_accrual']['a']), r3(LFS['fin_accrual']['b'])],
                                               reviewed=[r3(LFS['fin_reviewed']['a']), r3(LFS['fin_reviewed']['b'])],
                                               average=[r3(LFS['fin']['a']), r3(LFS['fin']['b'])], spread=FIN_SD),
             nominal_round1=[rnd(LINES_NOMINAL['fin']['a'], 2), rnd(LINES_NOMINAL['fin']['b'], 2)],
             parallel_thresholds=dict(slope_accrual=r3(pt['slope_accrual']), slope_reviewed=r3(pt['slope_reviewed']), chi2=rnd(pt['wald_chi2'], 1),
                                      p=float(f"{pt['p']:.2g}"), rejected=pt['rejected']),
             tax_law=dict(slope_all=[r3(TXL['slopes']['all firms ($50k-$200M)']['b1']), r3(TXL['slopes']['all firms ($50k-$200M)']['se'])],
                          slope_below_1M=[r3(TXL['slopes']['sales < $1M (below every 2003 cash-method threshold)']['b1']),
                                          r3(TXL['slopes']['sales < $1M (below every 2003 cash-method threshold)']['se'])],
                          slope_free_to_use_cash=[r3(free_['b1']), r3(free_['se'])],
                          share_10M_plus={k.split(' (')[0]: r3(v['10M-200M'][0]) for k, v in TXL['shares'].items()},
                          note='probit slopes of the accrual item per decade of sales; free to use cash = no inventory and not taxed as a corporation. '
                               '2003 rules forced accrual on C corporations above $5M and on inventory holders above $1M ($10M outside retail, '
                               'wholesale and manufacturing); TCJA moved the thresholds to $25M+ in 2018 ($31M for 2025)'),
             menu_coded_sd=dict(estimate=r3(FINSD['estimate']), se=r3(FINSD['se']), class_range=[r3(min(r_['menu_sd'] for r_ in fs_rows)),
                                                                                                   r3(max(r_['menu_sd'] for r_ in fs_rows))],
                                lower_bound=r3(FINSD['lower_bound']), mar=r3(FINSD['mar'])),
             why=('stays judgment (analyst): the two items disagree (parallel thresholds rejected), the accrual item partly measures 2003 tax rules '
                  'that no longer bind below $31M, and the reviewed item is a lower bound; the console line lies between the items\' real lines')),
    cc=dict(console=[CC_MED, CC_SCALE], sbo2007_P_cc_below_10pct_lower_bound={g_: r3(JC['cc']['sbo2007_P_no_business_or_government_class_10pct'][g_][0]) for g_ in rc_lab},
            console_implied=r3(JC['cc']['console_implied_P_cc_below_10pct']), nrc2000_top3=[JC['cc']['nrc2000_top3_customers'][k] for k in ('mean', 'median', 'sd', 'n')]),
    plt=dict(console=[PLT_MED, PLT_SCALE], ef_median=r3(JC['plt']['ef_median']), ef_iqr=[r3(JC['plt']['ef_p25']), r3(JC['plt']['ef_p75'])], ef_sd=r3(JC['plt']['ef_sd']), ef_n=JC['plt']['ef_n']),
    own_scale=dict(console=SCALE['own'], sbo2007_menu_sd={mp: [r3(v) for v in JC['own_scale']['sbo2007_range_in_window'][mp]] for mp in MAPS},
                   dealledger_two_marker=[r3(v) for v in JC['own_scale']['dealledger_two_marker_spread_range']]),
    mgt_scale=dict(console=SCALE['mgt'], found=None),
    buyer_pool_scale=dict(console=BUY_SCALE, flippa_sd_ln_watchers=r3(JC['buyer_pool_scale']['flippa_sd_ln_watchers']),
                          ibba_sd_ln_offers=r3(JC['buyer_pool_scale']['ibba_sd_ln_offers']['all']['sd_ln_offers'])),
    size_centre=dict(console=int(SIZE_CENTRE), note='a convention: $700k sits at the %.0fth percentile of listed SDE' % (100 * (1 - SIZE['share_above_700k'])),
                     population_medians=dict(dealledger_listings_sde=int(round(SIZE['median_sde'])), bizbuysell_closed_2025_cash_flow=int(BBS_MED.get('2025')),
                                             ibba_closed_2020_25_deal_value=int(round(IB['median_value'], -3)))),
    note='recorded as checks only; these stay judgment')
checks_js['fin'] = dict(not_shipped_js['fin'], fin_sd_judgment=True)
SRC_STR = ('Slopes: Fed SSBF 2003 (4,240 firms, 5 implicates; replications SSBF 1998 and NSSBF 1993), Census SBO 2007 PUMS, Census ABS 2023 '
           'management-practice tables, DealLedger broker listings (CC0, %s to %s) for the seller bridge, the size spread and listing-text '
           'slopes, FRED CPI-U. Levels: the console\'s (judgment), with the SSBF readings and their bounds in checks' % (DL_SNAPS[0], DL_SNAPS[-1]))
METHOD_STR = ('Slopes FITTED: weighted probits of the SSBF 2003 item "no owner runs day-to-day" on log10 sales (sales $50k-$200M; Rubin over '
              'implicates; stratified design SEs), carried to the console scale with the console spreads (own .25, mgt .28) and the DealLedger '
              'seller bridge log10 revenue = %.3f + %.3f log10 SDE: b = t s b1 G 1.20, the same in real and nominal dollars and for any cut point. '
              'own\'s slope replicated by SSBF 1998, NSSBF 1993, SBO 2007 and DealLedger (pool %.2f); mgt\'s checked against ABS 2023 management '
              'practices and DealLedger "management team" (random-effects pool %.2f, SE %.2f; SSBF z %.2f). Levels JUDGMENT: the console\'s .62 and '
              '.42; the item bounds them (own %.2f-%.2f, mgt %.2f-%.2f over the two plausible cut points; own %.2f-%.2f over survey years). '
              'size_sd = SD of log10 SDE of DealLedger listings $50k-$20M (broker-cluster bootstrap). b and scales rounded to 0.01. fin and its '
              'z-scale stay judgment. The clamp at z = +-1 stays, with a known bias below $45k recorded in checks.clamp.'
              % (A0, G, POOL['own']['pooled']['mu'], MIT['pool'], MIT['se'], MIT['z'], MAP_BOUNDS['own']['range'][0], MAP_BOUNDS['own']['range'][1],
                 MAP_BOUNDS['mgt']['range'][0], MAP_BOUNDS['mgt']['range'][1], min(v['a'] for v in vt['own_line_by_vintage'].values()),
                 max(v['a'] for v in vt['own_line_by_vintage'].values())))
JS = {'own': dict(SHIP['own']), 'mgt': dict(SHIP['mgt']), 'fin': dict(SHIP['fin']),
      'fin_sd': FIN_SD_JUDGMENT, 'size_sd_log10': SIZE_SD, 'size_sd_se': SIZE_SD_SE,
      'checks': checks_js, 'source': SRC_STR, 'method': METHOD_STR}
JS_LINE = 'MODELS.fitted.size_refs=' + json.dumps(JS, separators=(',', ':')) + ';'
open(OUT + '/js_line.txt', 'w').write(JS_LINE + '\n')

TESTS = {}


def test(name, cond):
    TESTS[name] = bool(cond)
    return cond


test('bridge reproduces the decision (1.019 + .926 log10 SDE, 5,350 listings)', abs(A0 - 1.019) < 5e-4 and abs(G - .926) < 5e-4 and BRIDGE['n_listings'] == 5350)
test('deflator reproduces round 1 (CPI-U Feb-Aug 2026 over 2003 = 1.808, .257 decades)', abs(DEFL['ratio_2026_over_2003'] - 1.808) < 5e-4 and DEFL['months_2026'] == 7)
test('SSBF 2003 probit slopes reproduce the research (.540 / .791 / .438 per decade of sales)',
     abs(PROBITS03['nomgr']['b1'] - .540) < .002 and abs(PROBITS03['acc']['b1'] - .791) < .002 and abs(PROBITS03['ra']['b1'] - .438) < .002)
test('data readings reproduce revision 2 (real .60 - .15z and .43 + .17z; SEs of b .019 / .021)',
     (DATA_LINE['own']['a'], DATA_LINE['own']['b'], DATA_LINE['mgt']['a'], DATA_LINE['mgt']['b']) == (.60, -.15, .43, .17)
     and (DATA_LINE['own']['se_b'], DATA_LINE['mgt']['se_b']) == (.019, .021))
test('nominal readings reproduce round 1 (own .56 - .15z, mgt .47 + .17z) and the research\'s fin (.57 + .19z at s .28)',
     (rnd(LINES_NOMINAL['own']['a'], 2), rnd(LINES_NOMINAL['own']['b'], 2), rnd(LINES_NOMINAL['mgt']['a'], 2), rnd(LINES_NOMINAL['mgt']['b'], 2),
      rnd(LINES_NOMINAL['fin']['a'], 2), rnd(LINES_NOMINAL['fin']['b'], 2)) == (.56, -.15, .47, .17, .57, .19))
test('decision (revision 3): own and mgt ship the fitted slopes (-.15, +.17) with the console\'s levels kept as judgment (.62, .42)',
     JS['own'] == dict(a=.62, a_judgment=True, b=-.15, se_b=.019) and JS['mgt'] == dict(a=.42, a_judgment=True, b=.17, se_b=.021))
test('mapping bounds reproduce the review (own .60-.89, mgt .15-.43) and contain the console\'s levels',
     [rnd(v, 2) for v in MAP_BOUNDS['own']['range']] == [.60, .89] and [rnd(v, 2) for v in MAP_BOUNDS['mgt']['range']] == [.15, .43]
     and MAP_BOUNDS['own']['console_inside'] and MAP_BOUNDS['mgt']['console_inside'])
test('vintage levels reproduce the review (own .48 / .56 / .60, mgt .57 / .48 / .43)',
     vintage_js['own_a'] == [.48, .56, .60] and vintage_js['mgt_a'] == [.57, .48, .43])
test('slopes do not move with the dollar basis or the cut point (real b = nominal b to 1e-12)',
     all(abs(LINES[k]['b'] - LINES_NOMINAL[k]['b']) < 1e-12 for k in ('own', 'mgt')))
test('ABS 2023 composite slope reproduces round 1 (.114 per z)', abs(ABS_PERZ['composite'][0] - .1140) < 5e-4)
test('mgt: the independent evidence (ABS + DealLedger, random effects) is consistent with SSBF\'s slope, so SSBF\'s slope ships', MGT_CONSISTENT)
test('fin and its z-scale ship as judgment (the console\'s .55 + .22z and .28)', SHIP['fin'] == dict(a=.55, b=.22, judgment=True) and JS['fin_sd'] == .28)
test('fin\'s menu-coded SD within the research range (.29-.35), recorded only', .29 <= FINSD['estimate'] <= .35)
test('the console\'s fin line lies between the two items\' real lines at z = 0 and in slope',
     min(LINES['fin_accrual']['a'], LINES['fin_reviewed']['a']) <= FIN_JUDGMENT[0] <= max(LINES['fin_accrual']['a'], LINES['fin_reviewed']['a'])
     and min(LINES['fin_accrual']['b'], LINES['fin_reviewed']['b']) <= FIN_JUDGMENT[1] <= max(LINES['fin_accrual']['b'], LINES['fin_reviewed']['b']))
test('size SD reproduces the research (.476, n 10,187)', abs(SIZE['sd_log10'] - .476) < .0005 and SIZE['n'] == 10187)
test('all shipped SEs positive and finite', all(np.isfinite(v) and v > 0 for k in ['own', 'mgt'] for v in (SHIP[k].get('se_b', 1),)) and SIZE_SD_SE > 0)
test('knot medians inside (0, 1) and ordered with size as the console assumes (own falls, mgt rises), data and shipped lines',
     all(0 < v < 1 for k in ['own', 'mgt', 'own_shipped', 'mgt_shipped'] for v in KN[k]) and (np.diff(KN.own) < 0).all() and (np.diff(KN.mgt) > 0).all()
     and (np.diff(KN.own_shipped) < 0).all() and (np.diff(KN.mgt_shipped) > 0).all())
test('shipped values on the 0.01 grid', all(abs(v * 100 - round(v * 100)) < 1e-9 for v in [SHIP[k][c] for k in ['own', 'mgt'] for c in ('a', 'b')] + [SIZE_SD]))
test('the pooled replications do not overrule the SSBF slopes (SSBF vs the other sources, |z| < 1.96, both dimensions)',
     not POOL['own']['ssbf_vs_others']['says_otherwise'] and not POOL['mgt']['ssbf_vs_others']['says_otherwise'])
test('the data lines (the real readings) pass the SSBF sales-class test inside the window (p > .05)',
     all(sum_s[nm]['p_df_k_minus_2'] > .05 for nm in ('own (data line)', 'mgt (data line)')))
test('clamp: not clearly contradicted for the shipped dimensions (CF_MANAGE, both sides), so it is kept', not CL_['contradicted_for_shipped_dims'])
test('known bias below $45k recorded: observed hired-manager share 1.8% (SE .5%) against 3.0% under the clamped data line, z about -2.3',
     r3(OWN_B['observed']) == .018 and r3(OWN_B['se']) == .005 and r3(OWN_B['predicted']) == .030 and -2.5 < (OWN_B['observed'] - OWN_B['predicted']) / OWN_B['se'] < -2.0)
if MAT:
    mp_ = {(r_['ind'], r_['ern']): r_['pct'] for r_ in MAT}
    test('materiality: a business at the old medians loses value at $45k and gains at $11M (own and mgt flatten)',
         all(mp_[(i_, 4.5e4)] < 0 and mp_[(i_, 1.1e7)] > 0 for i_ in ('home', 'rest')))
    test('materiality: the effect is the same in two industries to 0.1% (sizeRefs does not depend on industry)',
         all(abs(mp_[('home', x)] - mp_[('rest', x)]) < 1e-3 for _, x in KNOTS))
    test('known bias: the clamp lowers the value of a business at the unclamped medians below $45k, most at $10k, and nothing at $45k',
         all(v < 0 for v in bias_value['pct'][:-1]) and abs(bias_value['pct'][-1]) < 0.05 and bias_value['pct'][0] == min(bias_value['pct']))
    test('GM payoff check ran for every frame, industry, size and page variant (%d rows)' % len(GM),
         len(GM) == len(GM_INDS) * len(GM_SDE) * ((2 + len(GM_COST_VARIANTS)) + (1 + len(GM_COST_VARIANTS))) and all(r_['n_rows'] == 11 for r_ in GM))
test('js_line parses back to the js_table', json.loads(JS_LINE[len('MODELS.fitted.size_refs='):-1]) == json.loads(json.dumps(JS)))
test('js_table has the analyst\'s shape (own, mgt, fin, fin_sd, size_sd_log10, size_sd_se, checks, source, method)',
     list(JS) == ['own', 'mgt', 'fin', 'fin_sd', 'size_sd_log10', 'size_sd_se', 'checks', 'source', 'method']
     and all(list(JS[k]) == ['a', 'a_judgment', 'b', 'se_b'] for k in ('own', 'mgt')) and JS['fin'] == dict(a=.55, b=.22, judgment=True)
     and all(k in JS['checks'] for k in ('level_readings', 'mapping_bounds', 'vintage', 'clamp', 'slopes')))
test('every input file hash matches the documented download', True)      # asserted at the top (EXPECT_SHA), including the CPI file
for k, v in TESTS.items():
    log(('PASS ' if v else 'FAIL ') + k)

SOURCES = [
    dict(name='Federal Reserve Survey of Small Business Finances 2003 (public data)', url='https://www.federalreserve.gov/pubs/oss/oss3/ssbf03/ssbf03.dat.Z',
         file=SSBF03, sha256_download=EXPECT_SHA[SSBF03_Z], sha256=EXPECT_SHA[SSBF03], years='2003-04 interviews, fiscal year 2003',
         n=f'{N_FIRMS03} firms x 5 implicates; {N03["nomgr"]} / {N03["acc"]} / {N03["ra"]} firms in the fit (sales $50k-$200M)',
         variables='CF_MANAGE, P1_2, N1T3, N3T1-N3T3, P2, PROFIT, P5_5, A10_2, B3, R3, A0_SIC2_FIN, FIN_WGT, A0_STRATUM, A0_IMPLICAT, SU_ID'),
    dict(name='Federal Reserve SSBF 1998', url='https://www.federalreserve.gov/pubs/oss/oss3/ssbf98/ssbf98.dat.Z', file=SSBF98,
         sha256_download=EXPECT_SHA[SSBF98_Z], sha256=EXPECT_SHA[SSBF98], years='1998', n=f'{VINT["1998"]["n"]} firms in the fit', variables='c_mgr, P2, fin_wgt, NEWSTRAT'),
    dict(name='Federal Reserve National Survey of Small Business Finances 1993', url='https://www.federalreserve.gov/pubs/oss/oss3/nssbf93/nssbf93.dat.Z',
         file=NSSBF93, sha256_download=EXPECT_SHA[NSSBF93_Z], sha256=EXPECT_SHA[NSSBF93], years='1993 (1992 sales)', n=f'{VINT["1993"]["n"]} firms in the fit',
         variables='MANAGE, P1, FIN_WGT, NEWSTRAT (names from nssbf93.txt, sha256 %s)' % sha(NSSBF93_NAMES)),
    dict(name='Census Survey of Business Owners 2007 PUMS', url='https://www2.census.gov/programs-surveys/sbo/datasets/2007/pums_csv.zip', file=SBO07_ZIP,
         sha256=EXPECT_SHA[SBO07_ZIP], years='2007', n=f'{len(SB)} employer records; {SBOP["L4_owner_provides"]["n"]} with receipts in the window and an owner-function level',
         variables='PROVIDE1-4, MANAGE1-4, FINANCIAL1-4, FNCTNABV1-4, FNCTNR1-4, PCT1-4, RECEIPTS_NOISY, TABWGT, RG, FEDERAL, STATELOCAL, OTHERBUS, INDIVIDUALS, SECTOR'),
    dict(name='Census Annual Business Survey 2023, management module by receipts size (MCB03) and employment size (MCB04); ABS 2020 MCB02 (employment)',
         url='https://www2.census.gov/programs-surveys/abs/data/2023/AB2300MCB03.zip ; .../2023/AB2300MCB04.zip ; .../2020/AB2000MCB02.zip',
         file=ABS_MCB03 + ' ; ' + ABS_MCB04 + ' ; ' + ABS20_MCB02, sha256=sha(ABS_MCB03) + ' ; ' + sha(ABS_MCB04) + ' ; ' + sha(ABS20_MCB02),
         years='2023 (reference year 2022); 2020 (reference year 2019)', n='published US tables: %d receipts classes in the fit, 8 practices' % ABSP['composite']['classes']),
    dict(name='Census Annual Business Survey 2023, characteristics by receipts size (customer classes, cc check)', url='https://www2.census.gov/programs-surveys/abs/data/2023/AB2300CSCB03.zip',
         file=ABS_CSCB03, sha256=sha(ABS_CSCB03), years='2023', n='published US table by receipts class'),
    dict(name='DealLedger broker-direct listings (CC0)', url='https://github.com/jeffsosville/dealledger', file=DL_SNAP + '/*/listings*.csv',
         sha256=hashlib.sha256(''.join(os.path.relpath(f, DL_SNAP) + sha(f, 64) for f in dl_files).encode()).hexdigest()[:16],
         sha256_note='hash of the concatenated (relative path + sha256) of the %d listings files in path order' % len(dl_files),
         years=f'{DL_SNAPS[0]} to {DL_SNAPS[-1]}',
         n=f'{len(DL)} listings ({int(DL.has_desc.sum())} with descriptions); bridge {BRIDGE["n_listings"]}; size {SIZE["n"]}; text slopes {DLP["owner_operated"]["n"]}'),
    dict(name='FRED CPIAUCNS, CPI-U all items, not seasonally adjusted (the deflator of the real readings)',
         url='https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS', file=CPI, sha256=sha(CPI), years='1992-2026-08', n='monthly'),
    dict(name='NRC (2000) Surviving Supply Chain Integration, Appendix A', url='https://nap.nationalacademies.org/read/6369/chapter/17', file=NAP, sha256=sha(NAP), years='1998-99 survey', n='86 responses'),
    dict(name='Empire Flippers listings (local clean set)', url='https://api.empireflippers.com (public marketplace API)', file=EF_LIST + ' ; ' + EF_TEXT,
         sha256=sha(EF_LIST) + ' ; ' + sha(EF_TEXT), years='to 2026-10', n=f'{JC["plt"]["ef_n"]} listings stating a channel share'),
    dict(name='Flippa recently sold 2026 (local clean set)', url='https://flippa.com/search (sold listings)', file=FLIPPA, sha256=sha(FLIPPA), years='2026', n=f'{JC["buyer_pool_scale"]["flippa_n"]} with watchers'),
    dict(name='IBBA / M&A Source Market Pulse (local clean tables)', url='https://www.ibba.org (Market Pulse full reports)', file=IBBA_N + ' ; ' + IBBA_H,
         sha256=sha(IBBA_N) + ' ; ' + sha(IBBA_H), years='2020Q1-2025Q4', n=f'{IB["n"]} closed deals by band; offers histograms 1,523 deals'),
    dict(name='BizBuySell Insight medians (secondary pages, local long table)', url='https://www.bizbuysell.com/insight-report/ (via secondary pages)', file=BBS, sha256=sha(BBS),
         years='2017-2026', n='published medians'),
    dict(name='Console snapshot (read only)', url='repo HEAD 56ba230', file=INDEX, sha256=sha(INDEX), years='2026-10', n='sizeRefs, z-scales, menus and INTERV gm parsed'),
    dict(name='intervention_costs fit, GM cost (documented constants, the GM payoff check only)', url='local: /tmp/claude-0/fit6/out/intervention_costs/RESULT.json js_table.gm',
         file='(constants in GM_COST_VARIANTS)', sha256=None, years='2026-10', n='hire $10,625 + loading 1.24 (revision 3); loading 1.38 (revision 2)'),
]
SHIPPED = {
    'own_b': dict(value=SHIP['own']['b'], se=SHIP['own']['se_b'], unrounded=LINES['own']['b'], console=CONSOLE['own'][1], nominal_round1=LINES_NOMINAL['own']['b'],
                  tier='fitted', replication_pool=[POOL['own']['pooled']['mu'], POOL['own']['pooled']['se_hksj']]),
    'mgt_b': dict(value=SHIP['mgt']['b'], se=SHIP['mgt'].get('se_b'), unrounded=LINES['mgt']['b'], console=CONSOLE['mgt'][1], nominal_round1=LINES_NOMINAL['mgt']['b'],
                  tier='fitted', independent_pool=[MIT['pool'], MIT['se']], z_vs_independent=MIT['z']),
    'size_sd_log10': dict(value=SIZE_SD, se=SIZE_SD_SE, unrounded=SIZE['sd_log10'], console=SIZE_SCALE, n=SIZE['n'], tier='fitted'),
    'own_a': dict(value=SHIP['own']['a'], tier='judgment (the console\'s level, kept)', console=CONSOLE['own'][0], data_reading_real=LINES['own']['a'],
                  se_sampling=LINES['own']['se_a'], data_reading_nominal=LINES_NOMINAL['own']['a'], mapping_bounds=MAP_BOUNDS['own']['range'],
                  vintage=[vt['own_line_by_vintage'][y]['a'] for y in ['1993', '1998', '2003']]),
    'mgt_a': dict(value=SHIP['mgt']['a'], tier='judgment (the console\'s level, kept)', console=CONSOLE['mgt'][0], data_reading_real=LINES['mgt']['a'],
                  se_sampling=LINES['mgt']['se_a'], data_reading_nominal=LINES_NOMINAL['mgt']['a'], mapping_bounds=MAP_BOUNDS['mgt']['range'],
                  vintage=[vt['mgt_line_by_vintage'][y]['a'] for y in ['1993', '1998', '2003']]),
}
for k, v in SHIPPED.items():
    v['change'] = rnd(v['value'] - v['console'], 2)
NOT_SHIPPED = dict(
    levels_as_read=dict(data_line_real={k: DATA_LINE[k] for k in ('own', 'mgt')}, nominal={k: [LINES_NOMINAL[k]['a'], LINES_NOMINAL[k]['b']] for k in ('own', 'mgt')},
                        mapping_bounds=MAP_BOUNDS, vintage={k: vt[k + '_line_by_vintage'] for k in ('own', 'mgt')},
                        why='revision 3 (analyst): the survey item bounds the level rather than identifying it; the console\'s .62 and .42 lie inside the bounds and stay'),
    fin=dict(kept=dict(a=FIN_JUDGMENT[0], b=FIN_JUDGMENT[1]), lines_real={k: {kk: LINES[k][kk] for kk in ('a', 'b', 'se_a', 'se_b')} for k in ('fin', 'fin_accrual', 'fin_reviewed')},
             lines_real_menu_coded_spread=SENS['fin_with_menu_coded_spread'], lines_nominal_round1={k: SENS['nominal_round1'][k] for k in ('fin', 'fin_accrual', 'fin_reviewed')},
             parallel_thresholds=CHECKS['parallel_thresholds_fin'], tax_law=TAXLAW, clean_or_better_as_accrual_or_reviewed=SENS['clean_or_better_as_accrual_or_reviewed'],
             knots=dict(fin_items_average=KN['fin'].tolist(), accrual=KN['fin_accrual'].tolist(), reviewed=KN['fin_reviewed'].tolist(), console=KN['fin_console'].tolist()),
             why=not_shipped_js['fin']['why']),
    fin_sd=dict(kept=FIN_SD_JUDGMENT, menu_coded=FINSD['estimate'], se=FINSD['se'], se_sampling=FINSD['se_sampling'], lower_bound=FINSD['lower_bound'], mar=FINSD['mar'],
                class_rows=FINSD['rows'], why='stays judgment with fin (analyst): .32 (.29-.35 by class) describes the menu-coded spread of the SSBF items'),
    judgment_checks=JC, judgment_checks_compact={k: v for k, v in not_shipped_js.items() if k != 'fin'}, size_centre=not_shipped_js['size_centre'])
ALT = dict(
    shipped={k: [SHIP[k]['a'], SHIP[k]['b']] for k in ['own', 'mgt', 'fin']},
    data_line_real={k: [DATA_LINE[k]['a'], DATA_LINE[k]['b']] for k in ['own', 'mgt']},
    nominal_round1={k: [rnd(SENS['nominal_round1'][k]['a'], 2), rnd(SENS['nominal_round1'][k]['b'], 2)] for k in ['own', 'mgt', 'fin']},
    pooled_slopes_with_console_levels={k: [SHIP[k]['a'], rnd(POOL[k]['pooled']['mu'], 2)] for k in ['own', 'mgt']},
    mgt_independent_pool_slope=[SHIP['mgt']['a'], rnd(MIT['pool'], 2)],
    window_matched_sales={k: [rnd(SENS['window_matched_to_z_range'][k]['a'], 2), rnd(SENS['window_matched_to_z_range'][k]['b'], 2)] for k in ['own', 'mgt', 'fin']},
    deflator_2025_annual={k: [rnd(SENS['deflator_2025_annual'][k]['a'], 2), rnd(SENS['deflator_2025_annual'][k]['b'], 2)] for k in ['own', 'mgt']},
    fin_with_menu_coded_spread=[rnd(LFS['fin']['a'], 2), rnd(LFS['fin']['b'], 2)],
    console={k: CONSOLE[k] for k in CONSOLE},
    note='not shipped: the analyst\'s decisions fix the estimator; these are the lines under the variants the checks raise')

mat_at = lambda ind, ern: ('%+.1f%%' % (100 * mp_[(ind, ern)])) if MAT else 'n/a'
OWN_BEYOND = {'below': dict(OWN_B, z=(OWN_B['observed'] - OWN_B['predicted']) / OWN_B['se']),
              'above': dict(OWN_A, z=(OWN_A['observed'] - OWN_A['predicted']) / OWN_A['se'])}
E0 = {r_['check']: r_ for r_ in rows_e if r_['cls'] == '0'}       # the no-employee class inside the window
SF = SENS['deflator_2025_annual']; NOM = SENS['nominal_round1']
MIS = MI['sampling_only_abs_se']
nb, na_ = CL_['items']['nomgr']['below'], CL_['items']['nomgr']['above']
ab_, aa_ = CL_['items']['acc']['below'], CL_['items']['acc']['above']
GMD = {(r_['frame'], r_['ind'], r_['ern'], r_['variant']): r_ for r_ in GM}
GM_TAGS = [g_['tag'] for g_ in GM_RUNS]
GM_SHORT = dict(zip(GM_TAGS, ('snapshot', 'new sizeRefs', 'new + IC rev 3', 'new + IC rev 2')))
GM_FRAME = {'today': 'at today\'s medians', 'own': 'at the variant\'s own medians'}
kmoney = lambda v: '%s$%sk' % ('-' if v < 0 else '', f'{abs(v) / 1e3:,.0f}')


def gm_txt(ind, ern, frame='today'):
    """the GM row's net (rank) under each page variant, and whether the optimiser takes the GM at either budget"""
    if not GM:
        return 'n/a'
    out_ = []
    for t in GM_TAGS:
        r_ = GMD.get((frame, ind, ern, t)) or GMD[('today', ind, ern, t)]       # the snapshot is the same business in both frames
        took = any(r_['opt'][b_][k_] for b_ in ('default', 'open') for k_ in ('V_has_gm', 'U_has_gm'))
        out_.append('%s %s (rank %d%s)' % (GM_SHORT[t], kmoney(r_['gm_net']), r_['gm_rank'], ', optimiser takes it' if took else ''))
    return '; '.join(out_)


# computed readings of the GM check (stated only when the rows support them)
if GM:
    _net = lambda f_, i_, e_, t_: (GMD.get((f_, i_, e_, t_)) or GMD[('today', i_, e_, t_)])['gm_net']
    _t1 = GM_TAGS[1]
    up_own = all(_net('own', i_, 3e6, _t1) > _net('today', i_, 3e6, GM_TAGS[0]) for i_ in GM_INDS)
    down_today = all(_net('today', i_, 3e6, _t1) < _net('today', i_, 3e6, GM_TAGS[0]) for i_ in GM_INDS)
    load_cuts = all(_net(f_, i_, e_, t_) < _net(f_, i_, e_, _t1) for f_ in ('today', 'own') for i_ in GM_INDS for e_ in GM_SDE for t_ in GM_TAGS[2:])
    neg_small = [e_ for e_ in GM_SDE if all(r_['gm_net'] < 0 for r_ in GM if r_['ern'] == e_)]
    GM_READ_1 = ('At $3M the flatter lines lower the payoff for the same business and raise it for a business at the new medians (more owner-'
                 'dependent, with less management, at $3M).' if (up_own and down_today) else
                 'At $3M the new lines move the payoff %s for the same business and %s for a business at the new medians.'
                 % ('down' if down_today else 'up or mixed', 'up' if up_own else 'down or mixed'))
    GM_READ_2 = ('%s %s' % ('The loaded GM cost lowers the payoff in every case.' if load_cuts else 'The loaded GM cost does not lower the payoff in every case.',
                            ('The GM row is negative in every variant at SDE %s.' % ', '.join('$%s' % f'{e_:,.0f}' for e_ in neg_small)) if neg_small else ''))
else:
    GM_READ_1 = GM_READ_2 = ''
gm_any_opt = sorted({(r_['frame'], r_['ind'], r_['ern'], r_['variant']) for r_ in GM if r_['opt']['open']['V_has_gm'] or r_['opt']['open']['U_has_gm']
                     or r_['opt']['default']['V_has_gm'] or r_['opt']['default']['U_has_gm']})
GM_SUMMARY = dict(rows=GM, variants=GM_TAGS, frames=['today', 'own'], optimiser_takes_gm=[list(x) for x in gm_any_opt],
                  note=('frame "today": a business at today\'s medians (snapshot sizeRefs); frame "own": a business at each page variant\'s own '
                        'medians (the round-2 review\'s reading); other inputs at the industry medians; rhoSell and optRho set as the console '
                        'sets them; gm_net = the intervention table\'s expected-proceeds gain net of cost (on top of a reprice); the optimiser at '
                        'the business\'s default $100k budget and at an open budget. IC = intervention_costs\' GM cost: revision 3 hire $10,625 + '
                        '1.24 x salary (and 1.24 x salary off earnings), revision 2 1.38 x salary'))
OPEN = [
    'Levels (decided, revision 3): the console\'s own .62 and mgt .42 stay as judgment; only the slopes ship (own %.2f, SE %.3f; mgt %+.2f, SE %.3f). '
    'The SSBF item bounds the level rather than identifying it: "no owner responsible for day-to-day management" (%.1f%% of firms at the real '
    'revenue of a $708k seller) fits Moderate as well as Low, so own runs from %.2f (Low only) to %.2f (Low or Moderate) and mgt from %.2f '
    '(Solid or Deep) to %.2f (Deep only); the console\'s levels lie inside both. The data readings are recorded: real 2003 dollars own %.3f '
    '(sampling SE %.3f) and mgt %.3f (SE %.3f); nominal %.3f and %.3f. The level also drifts with the survey year: own %.2f / %.2f / %.2f and '
    'mgt %.2f / %.2f / %.2f in 1993 / 1998 / 2003 (the hired-manager share %.3f / %.3f / %.3f, p %.1g; revision 2 printed .465 / .549 for 1993 / '
    '1998 by reading 2003-dollar revenue on the older probits, corrected here).'
    % (SHIP['own']['b'], SHIP['own']['se_b'], SHIP['mgt']['b'], SHIP['mgt']['se_b'], 100 * float(KN.loc[KN.knot == '708k', 'P_nomgr'].iloc[0]),
       MAP_BOUNDS['own']['range'][0], MAP_BOUNDS['own']['range'][1], MAP_BOUNDS['mgt']['range'][0], MAP_BOUNDS['mgt']['range'][1],
       LINES['own']['a'], LINES['own']['se_a'], LINES['mgt']['a'], LINES['mgt']['se_a'], NOM['own']['a'], NOM['mgt']['a'],
       *[vt['own_line_by_vintage'][y]['a'] for y in ['1993', '1998', '2003']], *[vt['mgt_line_by_vintage'][y]['a'] for y in ['1993', '1998', '2003']],
       vt['share_at_708k']['1993'], vt['share_at_708k']['1998'], vt['share_at_708k']['2003'], vt['share_p']),
    'Dollars (readings only now). The real readings deflate the bridge\'s 2026 revenue by CPI-U %.2f (mean of the %d DealLedger snapshot '
    'months with a print, Feb-Aug 2026) over the 2003 average %.2f = %.3f; with the 2025 annual CPI they are %.3f and %.3f (a move under .002). '
    'The slopes are the same in real and nominal dollars. The CPI file is another fitter\'s download (data/peer_gross_margin/fred_cpi_fx/'
    'CPIAUCNS.csv), read only and sha256-pinned.'
    % (CPI_DL, DEFL['months_2026'], DEFL['cpi_2003'], DEFL['ratio_2026_over_2003'], SF['own']['a'], SF['mgt']['a']),
    'mgt slope (decided: ship SSBF\'s only if independent evidence agrees). It does: DealLedger "management team" %+.3f (SE %.3f) and the ABS '
    '2023 management-practice composite %+.3f (SE %.3f, of which sampling %.4f and the SD of the 8 item slopes %.3f; items %.3f to %.3f) pool to '
    '%+.3f (SE %.3f, tau %.3f) under random effects; SSBF 2003 %+.3f (SE %.3f) is z %+.2f from it. The two independent sources disagree with '
    'each other (Q %.2f, p %.3f) and SSBF lies between them. The test has little power (pool SE %.3f), and it turns on the pooling model: a '
    'fixed-effect pool with ABS\'s sampling SE alone (%.4f, SE %.4f) would reject SSBF (z %+.2f), but that pool is itself rejected '
    '(Q %.1f, p %.1g). The ABS items measure structured practices, not depth; they and the phrase give slopes only, and mgt\'s level stays '
    'the console\'s judgment.'
    % (dl_b, dl_se, abs_b, abs_se, abs_se_sampling, ABS_ITEM_SD, min(v['b'] for v in MI['abs2023_items'].values()),
       max(v['b'] for v in MI['abs2023_items'].values()), MIT['pool'], MIT['se'], MI['pooled_random_effects']['tau'], MGT_SSBF['b'], MGT_SSBF['se'],
       MIT['z'], MI['pooled_random_effects']['Q'], MI['pooled_random_effects']['p_Q'], MIT['se'], MIS['fixed_effect']['mu'], MIS['fixed_effect']['se'],
       MIS['fixed_effect']['test']['z'], MIS['random_effects']['Q'], MIS['random_effects']['p_Q']),
    'own slope. The replication pool is %+.3f (SE %.3f; leave-one-out %+.3f to %+.3f) against SSBF\'s %+.3f (z %+.2f, not rejected); SSBF\'s '
    'slope ships as decided. On the console\'s z window every variant is about half the console\'s -.30.'
    % (POOL['own']['pooled']['mu'], POOL['own']['pooled']['se_hksj'], POOL['own']['loso_range'][0], POOL['own']['loso_range'][1],
       LINES['own']['b'], POOL['own']['ssbf_vs_others']['z']),
    'Clamp (kept, decided) with a KNOWN BIAS below $45k of SDE (recorded in js_table.checks.clamp.known_bias_below_45k). Spline probits with '
    'knots at the window edges ($%.0fk and $%.1fM of 2003-dollar sales): for "no owner runs day-to-day" the slope per decade below the window is '
    '%+.2f (SE %.2f; p %.2f against flat, %.2f against the inner %.2f) and above it %+.2f (SE %.2f; p %.2f, %.2f), so the pre-set rule (1%% '
    'on the spline) is not met. The class shares say the medians keep moving below the window: firms with $10k-$45k of SDE have a hired-'
    'manager share of %.3f (SE %.3f) against %.3f under the clamped data line (z %+.2f, n %d; %.3f under the shipped line), an own median near '
    '%.2f rather than %.2f. %.1f%% of listings sit below $45k. On the shipped line the own median at $10k is %.3f clamped against %.3f read down '
    'to the console\'s floor (z = %.2f). Value effect for a business at the unclamped medians (clamp against floor): %s at SDE $10k / $15k / '
    '$20k / $30k / $45k. Above $11M: %.3f against %.3f (z %+.2f, n %d; %.2f%% of listings). The accrual item keeps rising below $45k (%+.2f, '
    'SE %.2f, p %.3f against flat); fin is judgment anyway.'
    % (REV_LO / 1e3, REV_HI / 1e6, nb['slope'], nb['se'], nb['p_vs_flat'], nb['p_vs_inner'], CL_['items']['nomgr']['inner'][0],
       na_['slope'], na_['se'], na_['p_vs_flat'], na_['p_vs_inner'],
       OWN_BEYOND['below']['observed'], OWN_BEYOND['below']['se'], OWN_BEYOND['below']['predicted'], OWN_BEYOND['below']['z'], OWN_BEYOND['below']['n'],
       OWN_B_SHIP['predicted'], own_med_obs, own_med_clamped, 100 * CL_['dealledger_listings_beyond']['below_45k'],
       nb['own']['shipped_line_clamped'], nb['own']['shipped_line_unclamped_at_population_edge'], Z_FLOOR,
       ' / '.join('%+.1f%%' % v for v in bias_value['pct']) if BIAS else 'n/a',
       OWN_BEYOND['above']['observed'], OWN_BEYOND['above']['predicted'], OWN_BEYOND['above']['z'], OWN_BEYOND['above']['n'],
       100 * CL_['dealledger_listings_beyond']['above_11M'], ab_['slope'], ab_['se'], ab_['p_vs_flat']),
    'Employment-class test inside the window fails for the data lines (own chi2 %.1f on %d classes, p %.3f; mgt %.1f, p %.3f), where '
    'round 1\'s nominal window ($213k-$34.6M) passed. %.1f of own\'s chi2 comes from the %d firms with no employees (observed %.3f, '
    'predicted %.3f); without that class the test passes (%.1f on %d). The real window reaches down to $%.0fk of 2003-dollar sales and so '
    'takes in more non-employer firms, which rarely have a hired manager whatever their sales: the item depends on employment beyond sales. '
    'The sales-class test passes (own %.1f, mgt %.1f on %d classes). The shipped lines (judgment levels) score sales %.1f / %.1f and '
    'employment %.1f / %.1f under the Low-only / Deep-only mapping, which their levels do not assume; the console\'s lines %.1f / %.1f and '
    '%.1f / %.1f.'
    % (sum_e['own (data line)']['chi2'], sum_e['own (data line)']['classes'], sum_e['own (data line)']['p_df_k'], sum_e['mgt (data line)']['chi2'],
       sum_e['mgt (data line)']['p_df_k'], E0['own (data line)']['chi2'], E0['own (data line)']['n'], E0['own (data line)']['observed'],
       E0['own (data line)']['predicted'], sum_e['own (data line)']['chi2'] - E0['own (data line)']['chi2'], sum_e['own (data line)']['classes'] - 1,
       REV_LO / 1e3, sum_s['own (data line)']['chi2'], sum_s['mgt (data line)']['chi2'], sum_s['own (data line)']['classes'],
       sum_s['own (shipped)']['chi2'], sum_s['mgt (shipped)']['chi2'], sum_e['own (shipped)']['chi2'], sum_e['mgt (shipped)']['chi2'],
       sum_s['own (console line)']['chi2'], sum_s['mgt (console line)']['chi2'], sum_e['own (console line)']['chi2'], sum_e['mgt (console line)']['chi2']),
    'fin (kept as judgment). In real dollars with s = .28 the accrual line is %.3f %+.3fz and the reviewed line %.3f %+.3fz (average %.3f %+.3fz); '
    'the console\'s .55 + .22z lies between them. Parallel thresholds rejected (slopes %.3f vs %.3f per decade, chi2 %.1f, p %.1g). Tax law: '
    'the accrual slope is %.3f (SE %.3f) over all firms, %.3f (SE %.3f) below $1M where no rule binds, and %.3f (SE %.3f) among firms free to '
    'use cash at any size; above $10M the accrual share is %.2f among those firms against %.2f among inventory holders and %.2f among '
    'corporations. Since 2018 the thresholds are $25M+ ($31M for 2025), so the 2003 item overstates accrual adoption between $1M and $31M by '
    'today\'s rules. Menu-coded SD %.3f (SE %.3f; classes %.2f-%.2f) against the kept .28.'
    % (LINES['fin_accrual']['a'], LINES['fin_accrual']['b'], LINES['fin_reviewed']['a'], LINES['fin_reviewed']['b'], LINES['fin']['a'], LINES['fin']['b'],
       pt['slope_accrual'], pt['slope_reviewed'], pt['wald_chi2'], pt['p'], all_['b1'], all_['se'],
       TXL['slopes']['sales < $1M (below every 2003 cash-method threshold)']['b1'], TXL['slopes']['sales < $1M (below every 2003 cash-method threshold)']['se'],
       free_['b1'], free_['se'],
       TXL['shares']['no inventory, not taxed as a corporation (free to use cash at any size)']['10M-200M'][0],
       TXL['shares']['holds inventory']['10M-200M'][0], TXL['shares']['taxed as a corporation']['10M-200M'][0],
       FINSD['estimate'], FINSD['se'], not_shipped_js['fin']['menu_coded_sd']['class_range'][0], not_shipped_js['fin']['menu_coded_sd']['class_range'][1]),
    'Replication windows are real ($50k-$200M in 2003 dollars converted with CPI-U to 1992, 1998 and 2007 dollars; round 1 used the same '
    'nominal window every year) and the console-z-window refits use $%.0fk-$%.1fM of 2003-dollar sales. Pools: own %+.3f, mgt %+.3f (round 1 '
    '-.124, +.141).' % (REV_LO / 1e3, REV_HI / 1e6, POOL['own']['pooled']['mu'], POOL['mgt']['pooled']['mu']),
    'Size. .48 (SD of log10 SDE of 10,187 listings, SE %.3f) is the spread of businesses for sale; IBBA closed deals imply %.2f-%.2f. The $700k '
    'centre is a convention (the %.0fth percentile of listed SDE) and stays.'
    % (SIZE['se'], IB['implied_sd_log10_sde'][0], IB['implied_sd_log10_sde'][1], 100 * (1 - SIZE['share_above_700k'])),
    'Hire-a-GM payoff with the shipped sizeRefs and intervention_costs\' GM cost together (the round-2 review\'s item; RESULT.gm_payoff, '
    'gm_payoff.csv). The GM row\'s net expected-proceeds gain (rank among 11). A business at today\'s medians: home $3M %s; professional '
    'services $3M %s; home $708k %s. A business at each variant\'s own medians (the review\'s reading, which also moves the business): '
    'home $3M %s; professional services $3M %s. %s %s The optimiser takes the GM in %d of %d cases at the default $100k or an open budget '
    '(%s). Integration should re-run the optimiser tests once intervention_costs\' GM cost is settled.'
    % (gm_txt('home', 3e6), gm_txt('prof', 3e6), gm_txt('home', 7.08e5), gm_txt('home', 3e6, 'own'), gm_txt('prof', 3e6, 'own'), GM_READ_1, GM_READ_2,
       len(gm_any_opt), len(GM), '; '.join('%s $%s %s, %s' % (a, f'{b:,.0f}', GM_FRAME[f_], GM_SHORT[c]) for f_, a, b, c in gm_any_opt) if gm_any_opt else 'none'),
    'Integration. sizeRefs becomes own %s - %sz, mgt %s + %sz (fin unchanged; the levels are today\'s), and z.size divides by .48 instead of .45 '
    '(category scores and confidence only). A business that enters today\'s medians moves by %s / %s / %s (home services at $45k / $708k / $11M '
    'of SDE): small businesses lose value, large ones gain, because both lines flatten. Test baselines that use the old medians will move.'
    % (d2s(SHIP['own']['a']), d2s(-SHIP['own']['b']), d2s(SHIP['mgt']['a']), d2s(SHIP['mgt']['b']),
       mat_at('home', 4.5e4), mat_at('home', 7.08e5), mat_at('home', 1.1e7)),
    'Tier. own b, mgt b and size_sd_log10 are fitted (firm- and listing-level microdata with SEs); own a and mgt a are judgment (a_judgment: '
    'true), with the readings and bounds in js_table.checks; fin and fin_sd are judgment.',
]
CHECKS_OUT = [dict(check=k, outcome='PASS' if v else 'FAIL') for k, v in TESTS.items()]
CHECKS_OUT += [
    dict(check='levels against the survey item (revision 3: bounds, not identification)', outcome='RECORDED',
         detail='own: real %.3f (SE %.3f), nominal %.3f, bounds %.2f-%.2f, vintages %s; mgt: real %.3f (SE %.3f), nominal %.3f, bounds %.2f-%.2f, '
                'vintages %s; shipped .62 / .42 (judgment)' % (LINES['own']['a'], LINES['own']['se_a'], NOM['own']['a'], MAP_BOUNDS['own']['range'][0],
                                                               MAP_BOUNDS['own']['range'][1], vintage_js['own_a'], LINES['mgt']['a'], LINES['mgt']['se_a'],
                                                               NOM['mgt']['a'], MAP_BOUNDS['mgt']['range'][0], MAP_BOUNDS['mgt']['range'][1], vintage_js['mgt_a'])),
    dict(check='mgt slope against the independent evidence (decision rule)', outcome='CONSISTENT' if MGT_CONSISTENT else 'INCONSISTENT',
         detail='pool %+.3f (SE %.3f) vs SSBF %+.3f (SE %.3f), z %+.2f' % (MIT['pool'], MIT['se'], MGT_SSBF['b'], MGT_SSBF['se'], MIT['z'])),
    dict(check='clamp at $45k and $11M of SDE (decision rule)', outcome='KEPT' if not CL_['contradicted_for_shipped_dims'] else 'CONTRADICTED',
         detail='CF_MANAGE below %+.2f (p flat %.2f), above %+.2f (p flat %.2f)' % (nb['slope'], nb['p_vs_flat'], na_['slope'], na_['p_vs_flat'])),
    dict(check='known bias below $45k (recorded)', outcome='RECORDED',
         detail='hired-manager share %.3f (SE %.3f) vs %.3f under the clamped data line (z %+.2f, n %d); value effect %s at $10k / $15k / $20k / $30k / $45k'
                % (OWN_B['observed'], OWN_B['se'], OWN_B['predicted'], OWN_BEYOND['below']['z'], OWN_B['n'],
                   ' / '.join('%+.1f%%' % v for v in bias_value['pct']) if BIAS else 'n/a')),
    dict(check='parallel thresholds for fin (accrual vs reviewed)', outcome='REJECTED' if pt['rejected'] else 'NOT REJECTED',
         detail='chi2 %.1f, p %.1g' % (pt['wald_chi2'], pt['p'])),
    dict(check='accrual item and the 2003 tax law', outcome='RECORDED',
         detail='slope all %.3f, below $1M %.3f, free to use cash %.3f' % (all_['b1'], TXL['slopes']['sales < $1M (below every 2003 cash-method threshold)']['b1'], free_['b1'])),
    dict(check='DealLedger out-of-source slopes (own, mgt)', outcome='CONSISTENT' if all(v['consistent'] for v in CHECKS['dealledger_out_of_source'].values()) else 'INCONSISTENT',
         detail='; '.join('%s %+.3f vs %+.3f (z %+.2f)' % (d_, v['dealledger'], v['ssbf_bridge'], v['z']) for d_, v in CHECKS['dealledger_out_of_source'].items())),
    dict(check='vintage stability of the hired-manager item', outcome='SLOPES STABLE, LEVELS NOT' if (vt['slope_p'] > .05 and vt['share_p'] < .05) else 'RECORDED',
         detail='slope p %.2f; share at $708k p %.1g' % (vt['slope_p'], vt['share_p'])),
    dict(check='class shares by employment class inside the window (data lines)',
         outcome='PASS' if all(sum_e[nm]['p_df_k'] > .05 for nm in ('own (data line)', 'mgt (data line)')) else 'FAIL',
         detail='; '.join('%s chi2 %.1f/%d (p %.3f), of which the no-employee class %.1f (observed %.3f, predicted %.3f, n %d); without it %.1f/%d'
                          % (nm, sum_e[nm]['chi2'], sum_e[nm]['classes'], sum_e[nm]['p_df_k'], E0[nm]['chi2'], E0[nm]['observed'], E0[nm]['predicted'],
                             E0[nm]['n'], sum_e[nm]['chi2'] - E0[nm]['chi2'], sum_e[nm]['classes'] - 1) for nm in ('own (data line)', 'mgt (data line)'))
         + '; the console lines: own %.1f, mgt %.1f' % (sum_e['own (console line)']['chi2'], sum_e['mgt (console line)']['chi2'])),
    dict(check='class shares of the shipped lines (judgment levels; Low-only / Deep-only mapping)', outcome='RECORDED',
         detail='sales own %.1f/%d (p %.2g), mgt %.1f (p %.2g); employment own %.1f (p %.2g), mgt %.1f (p %.2g)'
                % (sum_s['own (shipped)']['chi2'], sum_s['own (shipped)']['classes'], sum_s['own (shipped)']['p_df_k_minus_2'], sum_s['mgt (shipped)']['chi2'],
                   sum_s['mgt (shipped)']['p_df_k_minus_2'], sum_e['own (shipped)']['chi2'], sum_e['own (shipped)']['p_df_k'], sum_e['mgt (shipped)']['chi2'],
                   sum_e['mgt (shipped)']['p_df_k'])),
    dict(check='class shares beyond the window against the clamped data line', outcome='RECORDED',
         detail='; '.join('%s observed %.3f (SE %.3f) vs %.3f clamped, z %+.2f (n %d)' % (r_['cls'], r_['observed'], r_['se'], r_['predicted'],
                                                                                      (r_['observed'] - r_['predicted']) / r_['se'], r_['n'])
                          for r_ in CL_['class_shares_beyond']['rows'] if r_['check'] == 'own (data line)')),
]
if MAT:
    CHECKS_OUT.append(dict(check='materiality (business entering the old medians)', outcome='RECORDED',
                           detail='; '.join('%s $%s %+.1f%%' % (r_['ind'], f"{r_['ern']:,.0f}", 100 * r_['pct']) for r_ in MAT)))
if GM:
    CHECKS_OUT.append(dict(check='hire-a-GM payoff with the shipped sizeRefs and intervention_costs\' GM cost', outcome='RECORDED',
                           detail='; '.join('%s $%s %s: %s' % (i_, f'{e_:,.0f}', GM_FRAME[f_], gm_txt(i_, e_, f_)) for f_ in ('today', 'own') for i_ in GM_INDS for e_ in GM_SDE)
                           + '; optimiser takes the GM in %d of %d cases' % (len(gm_any_opt), len(GM))))
RES = dict(name='size_refs', js_key='size_refs', tier='mixed (slopes and size_sd fitted; levels, fin and fin_sd judgment)', revision=3, js_table=JS, js_line=JS_LINE,
           shipped=SHIPPED, not_shipped=NOT_SHIPPED, checks=CHECKS_OUT, tests=TESTS, alternatives=ALT, open_issues=OPEN,
           decisions=dict(levels='judgment: the console\'s own .62 and mgt .42 (revision 3, analyst)', slopes='fitted (SSBF 2003 through the seller bridge)',
                          dollars='real (2003) via CPI-U for the readings; the slopes do not depend on it', mgt_rule=MI['rule'], mgt_decision=MI['decision'],
                          fin=list(FIN_JUDGMENT), fin_sd=FIN_SD_JUDGMENT, clamp_rule=CL_['rule'], clamp_decision=CL_['decision'] + '; the evidence below $45k is a known bias (analyst)',
                          round1='size_refs.v1.py; out/size_refs.v1/', revision2='size_refs.v2.py; out/size_refs.v2/'),
           bridge=BRIDGE, deflator=DEFL, probits_ssbf2003=PROBITS03, lines={k: {kk: v for kk, v in L.items() if kk not in ('Ja', 'Jb')} for k, L in LINES.items()},
           lines_nominal_round1={k: {kk: v for kk, v in L.items() if kk not in ('Ja', 'Jb')} for k, L in LINES_NOMINAL.items()},
           mapping_bounds=MAP_BOUNDS, knots=KN.to_dict(orient='list'), fin_sd=FINSD, size_sd=SIZE,
           replications=dict(sources=REPL, sensitivity_sources=SENS_SRC, pools=POOL, sources_console_z_window=REPL_W, pools_console_z_window=POOL_W),
           mgt_independent=MGT_IND, checks_detail=CHECKS, sensitivity=SENS, dealledger=dict(probits=DLP, fin_mentions_by_class=DL_FIN, two_marker=TWO),
           sbo2007_probits=SBOP, abs2023_probits=ABSP, vintage_probits={y: dict(b0=v['b0'], b1=v['b1'], se_b1=float(np.sqrt(v['V'][1, 1])), n=v['n']) for y, v in VINT.items()},
           judgment_checks=JC, materiality=MATERIALITY, clamp_value_effect=BIAS_EFFECT, gm_payoff=GM_SUMMARY,
           console=dict(sizeRefs=CONSOLE, z_centre=ZC, z_scale=ZS, scales=SCALE, size=[SIZE_CENTRE, SIZE_SCALE], cuts={k: CUT[k] for k in CUT},
                        menus=MENU, cc=[CC_MED, CC_SCALE], plt=[PLT_MED, PLT_SCALE], buy_scale=BUY_SCALE),
           sources=SOURCES, parameters=dict(B=B_BOOT, seed=SEED, sales_window_2003_dollars=[SALES_LO, SALES_HI], knots=KNOTS, bias_sde=BIAS_SDE,
                                            gm=dict(inds=GM_INDS, sde=GM_SDE, open_budget=GM_BUDGET, cost_variants=GM_COST_VARIANTS),
                                            rounding='b and scales to 0.01, SEs and knot values to 0.001, half away from zero'))
json.dump(clean(RES), open(OUT + '/RESULT.json', 'w'), indent=1, sort_keys=True)
log('alternatives', json.dumps(clean(ALT)))
for c in CHECKS_OUT:
    log('%-24s %s%s' % (c['outcome'], c['check'], (': ' + c['detail']) if c.get('detail') else ''))
log('wrote', OUT + '/RESULT.json')
print(JS_LINE[:800])
