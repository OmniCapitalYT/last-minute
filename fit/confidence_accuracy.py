#!/usr/bin/env python3
"""The confidence figure re-based as a measured probability: the chance the realised price lands within 25% of the
value model's fitted value (MODELS.fitted.confidence). October 2026, third round (round 2's script and outputs are kept
unchanged as confidence_accuracy.v2.py and /tmp/claude-0/fit6/out/confidence_accuracy.v2/).

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/confidence_accuracy.py [B]   (about 8 min with B = 200, the shipped run;
      needs node and pdftotext. B < 200 is a quick check: it writes to the scratch directory's quick/, not to Out)
Out:  /tmp/claude-0/fit6/out/confidence_accuracy/RESULT.json (key js_table = MODELS.fitted.confidence; js_code = the
      reference function conf(s,out); test_vectors = inputs -> p, label, note, sigma, band80 computed here), js_line.txt,
      conf.js, level_gap.csv, gradients.csv, robustness.csv, sensitivity.csv, industry.csv, extrapolation.csv,
      extrapolation_rule.csv, mix_check.csv, labels.csv, compare_current.csv, test_vectors.json
      Scratch (node probe and JS checks, their configs and outputs): /tmp/claude-0/fit6/work/fit3-confidence_accuracy/
      (round 2's scratch, fit2-..., is left as it was). The snapshot and the downloads are only read; nothing in the
      repo or the snapshot is written.

The estimate
  "The estimate" is the value model's fitted value: fitValue(SDE, revenue, industry, 2026).point = out.fv.point, written
  V below. BIZCOMPS's within_25pct and fan_quantiles describe closed prices around it, and the listing residuals here are
  measured around it. The console's model value out.V = out.fv.point x out.qFactor also carries the quality position
  inside the measured spread, which is judgment; this probability does not cover it (it gives the quality position no
  credit for narrowing the spread).

Why
  The console's confidence figure is an index, conf = .34 comps + .30 min(1, yrs/8) + .22 reporting + .14 max(0, 1 -
  mean|z|/2.2), labelled High above .68 and Moderate above .46, all hand-set (display only: nothing else reads
  out.conf). The research round (/tmp/claude-0/fit6/research/H-interv-cats-conf.md, section 5) proposed re-basing it as
  P(realised price within 25% of the estimate): the LEVEL from BIZCOMPS's out-of-fold accuracy (MODELS.value.within_25pct
  0.4454), the SHAPE of the residual from MODELS.value.fan_quantiles, and gradients (size, distance from the typical
  margin, industry, extrapolation, comparables depth) from DealLedger broker asks around the fitted value. The critic
  (results_all.json, "critique") objected that the gradients come from asks and that the research panel's median ask is
  1.84x the fitted value (ask/SDE 3.67 against 2.98 in another DealLedger panel). Round 2 found the cause (parse
  errors), rebuilt the panel and re-estimated every gradient on a Main-Street-only panel with robustness checks.

Round 3 (the analyst's decisions on the round-2 review in /tmp/claude-0/fit6/out/fits_round2b.json)
  1. Location versus scale. P describes the spread of realised prices around V ASSUMING V IS CENTRED. A location trend
     is therefore not counted as inaccuracy, for size and margin alike: each listing's residual is centred on a median
     regression on industry, ln SDE, signed z.em and z.em^2 (round 2 removed the size trend but not the margin trend;
     its centred residual's median rose from -0.21 to +0.13 across signed z.em). The scale gradients estimated on that
     residual ship (scale only). Round 2's location-inclusive centring and two broker-fixed-effect centrings are
     sensitivities (gradients, K and P at the reference, sensitivity.csv). The table and the JS state that P assumes V
     is centred on today's prices; the BizBuySell 2025 level check (median sale 1.13x the model value of the median
     business) is carried as a stated range for P at the reference and as a component of its SE.
  2. Cut-offs: the quartiles of p across Main-Street listings with the shipped gradients, rounded to 0.01 (round 2
     rounded to 0.05, which made the lower cut a knife-edge); the label shares are reported. The labels are relative
     standing among listed businesses ("High: more predictable than three quarters of listed businesses").
  3. Extrapolation: the label is Low, with the note "outside the fitted data", when out.extrapMax > 3 or the margin
     (SDE / revenue, as model() computes it) lies outside MODELS.value.support.margin [p1, p99]. Evidence: Main-Street
     listings whose margin is past support land within 25% far less often than the formula says
     (extrapolation_rule.csv).
  4. Depth: conf() computes comps itself, n6 / (n6 + k_naics6) of the value model's own 6-digit cell
     (MODELS.value.industry_n6 at naics6For(industry), k_naics6 = MODELS.value.industry_shrinkage.k_naics6), and 0 when
     the industry has no 6-digit cell in the table (saas): the variance the value model's industry effect carries.
     It no longer reads I.comps (hand-set today, fit6 D's later).
  5. Claims corrected (review (a)-(e)): the ask panel's own scale is not a level bridge (between-broker premia are a
     sizable share of ask dispersion); the hold-out is restated from its numbers (gain in each direction, quintile
     misses with their binomial SEs); the Empire Flippers check reports the gradient levels under both centrings, not
     only sale minus ask; the size p-value straddles the 0.10 rule across specifications; the estimate is named
     (above). Metadata: 103 snapshot files are read but the 2026-02-23 file has no id column and contributes nothing,
     so the data are 102 files from 2026-02-28 to 2026-10-06; the test count is computed, not typed; test vectors are
     rounded to 6 decimals.
  6. js_code: conf(s, out), reading MODELS, FAN and naics6For, returns {p, label, note, sigma, band80}; band80 is the
     business's 80% band of price / V implied by sigma (the fan's p10 and p90 raised to sigma), for the equation panel.
     Ten test vectors; a node check runs conf() inside the snapshot's model section on the vectors and on model()
     outputs, and runs model() with the documented integration line in place of the old block.

What it does
  0. Sources. sha256 of every input (the 103 DealLedger listings.csv files are hashed together). Lie & Lie (2002) Table 3
     numbers are documented constants confirmed against the PDF's text layer (pdftotext -layout; nothing from a download
     is run or imported). The snapshot's index.html is read for MODELS (value, fitted.sde_margin), IND, IND2NAICS6 and
     the current confidence formula; the model itself is run through the harness (node).
  1. Panel. The research rules (dl_listings.py: the snapshot files, last non-null value per listing id after sorting by
     snapshot date, ask $20k-$50M, cash flow $10k-$20M, ask/cash flow 0.3-15, de-duplicated on ask, cash flow and title,
     industry by the regexes of fit/hedonic.py) reproduce 12,247 listings, 5,940 with revenue > SDE (the research
     panel). 103 files are read; the first (2026-02-23) has no id column, so its rows drop out at the per-id step and
     the panel comes from 102 files, 2026-02-28 to 2026-10-06. Added per listing: broker domain, and flags from the
     listing's own text (read as data):
       parse errors: the ask field equals the revenue field (within 0.5%) or the cash-flow field (within 0.5%); or the
         asking price written in the title/description ("Asking Price: $X", "Price $X") differs from the ask field by 1%
         or more (this catches asks and revenues swapped: "Price $135,000 Gross Sales $1,072,379" stored as ask
         1,072,379, revenue 135,000);
       online-business brokers (ONLINE_BROKERS, by domain);
       real estate in the ask where the text says so (RE_INCLUDED).
     Main-Street panel = revenue > SDE, no parse error, not an online-business broker, no real estate in the ask.
  2. Model quantities (node, the harness, the frozen snapshot): fitValue(SDE, revenue, industry, 2026), typMargin,
     z.em = ln(margin / typMargin) / sd clamped to +-3.2 and the extrapolation flags exactly as model() computes them
     (checked against model() itself for every classified listing). Unclassified listings use key 'zz_other'.
  3. Level gap. Median ask / fitted value, ask / SDE and fitted value / SDE along the cleaning steps, by broker, flag,
     industry and size; the reconciliation with fit6 E's panel (ask/SDE 2.98 over all listings); BizBuySell's 2025 median
     closed sale against the model's value of the median business.
  4. Replication of the research's joint |r - industry median| regression (conf_rebase.py: all 5,940 listings, with the
     outside-support and ln(times past the edge) terms) and of its within-25 shares.
  5. Gradients (Main-Street panel, inside MODELS.value.support). Residual r = ln(ask / V), centred on a median (L1)
     regression on industry, ln SDE, signed z.em and z.em^2 (CENTRE_MAIN), so a location trend in the ask premium, in
     size or in margin, is not read as a change in accuracy. The outcome is the event the confidence figure is about:
     the centred residual inside [ln 0.8, ln 1.333]. Model: P(inside) = G(s), G(s) = Fan(ln 1.333 / s) - Fan(ln 0.8 / s),
     where Fan is the BIZCOMPS out-of-fold residual distribution (probit-linear through MODELS.value.fan_quantiles, as
     the console's FAN) and ln s = a + b_size ln(min(max(SDE, p1), p99) / $700k) + b_em |z.em| + industry, fitted by
     maximum likelihood (Fisher scoring; industry terms carry a weak N(0, 1) prior so that 4-listing cells stay finite).
     Only the central mass enters, so stray outliers cannot drive the fit. SEs: broker-cluster bootstrap (B draws,
     brokers resampled).
  6. Sensitivities of the centring (sensitivity.csv; each with its own broker-cluster bootstrap and its own K and P at
     the reference): round 2's location-inclusive centring (industry and ln SDE only), broker fixed effects (brokers
     with BFE_MIN or more in-support listings in the sample) added to the location-inclusive centring, and to the
     shipped one. Robustness, all on the shipped centring: the research panel and the panel with only the parse errors
     removed; |r| regressions (OLS as in the research, median regression, OLS trimmed at the top 2.5% and 5%);
     centring on industry only (location-inclusive in size and margin); subsets (SDE >= $100k, |z.em| <= 2, early and
     late halves by first-seen date, classified industries, the two large networks and the rest; a subset with fewer
     than 20 brokers is bootstrapped by listing); functional forms (hinge, asymmetric, quadratic margin terms); a
     temporal hold-out both ways (the gradients fitted on one half by first-seen date score the other half, which keeps
     its own location and base rate, against a constant probability; listing bootstrap SE; calibration by quintile with
     the binomial SE of each quintile); attenuation by ask noise; an Empire Flippers bridge test (the same deals' asks
     and reconstructed sale prices around the console value, under both centrings: the gradient levels, their
     difference, and the location slope on signed z.em); Lie & Lie (2002): the size elasticity of the valuation-error
     scale implied by their Table 3 (fan shape, class median error as location, class centres from a lognormal through
     their Table 1 asset quartiles).
  7. Industry shifts: empirical-Bayes shrinkage (DerSimonian-Laird toward 0, the unclassified listings being the
     reference) and Cochran's Q. Extrapolation: penalty in ln s for listings past a p1/p99 edge, by the console's
     out.extrap distance buckets (1-1.5x, 1.5-3x, >3x, 1-3x pooled), with the in-support fit as offset; the decision
     reads the listings conf() still labels by p (size or revenue 1-3x past support with the margin inside), since the
     label rule takes the margin-past-support and past-3x ones. And the evidence for that rule: Main-Street listings
     with the margin past support (within-25 share, median centred residual, under the shipped and round 2's
     centrings) against the in-support fit's prediction for the same listings (extrapolation_rule.csv).
  8. Depth of comparables: tau^2 of the 6-digit industry effects from MODELS.value (method of moments on the de-shrunk
     deviations from the 2-digit parent, raw^2 on 1/n, as fit6 industry_tailwind_and_comps.py; cell bootstrap SE), in
     log price (x ind_eff^2). A business's industry effect then has posterior variance tau^2 k/(n+k) = tau^2 (1 - comps),
     comps = n/(n+k), k = k_naics6 = 25, the value model's own shrinkage (exact when k equals the moment estimate
     k_hat; the gap at k = 25 against k_hat is reported), and n = 0 when the industry has no 6-digit cell (saas). It is
     added to the scale: sigma = sqrt((K e^(..))^2 + tau^2 (1 - comps) / S_EQ^2). S_EQ (the fan's normal-equivalent
     spread for this purpose) is chosen to minimise the largest gap to the exact convolution (Gauss-Hermite) over a
     grid that covers the console's range of the scale (checked). Asks cannot test this term (centring removes an
     industry's level error).
  9. Decision rule (stated before fitting): a block ships if, on the Main-Street panel, its main estimate differs from
     zero at two-sided p < 0.10 (broker-cluster SE; for the industry block Cochran's Q) and its sign holds in every
     robustness variant. The size gradient ships in any case (the analyst's fallback), marked weak if it fails. Blocks that
     fail go to not_shipped with their estimates. The depth term is not from asks and ships on BIZCOMPS's own tau^2.
 10. Normalisation. K solves mean(G(sigma_i)) = 0.4454 over a BIZCOMPS-like mix: SDE and SDE margin from
     MODELS.value.support (probit-linear quantile functions, joined by a Gaussian copula whose correlation reproduces the
     stored revenue p5-p95 spread), z.em against typMargin('other'), the deal's own 6-digit cell depth from
     industry_n6 (cells under the table's cut at the full tau^2), and the shipped industry and extrapolation terms if
     any. SE of K: bootstrap of the gradients, tau^2, the level's binomial SE and the mix assumptions. P at the
     reference ($700k, typical margin, deep cell) with its SE; the level check (P if today's prices sit at the
     BizBuySell ratio above V) as a stated range and an SE component; P at the reference under each sensitivity.
 11. Labels: relative standing, a stated convention: High at or above the upper quartile of p across Main-Street
     listings, Low below the lower quartile, each rounded to 0.01; outside the fitted data (out.extrapMax > 3 or the
     margin outside support) the label is Low. Shares reported with and without that rule, and at the cuts +- 0.01.
 12. Output: the js_table, a reference JavaScript conf(s, out) that reads s.ern, s.rev, s.ind, out.z.em,
     out.extrapMax, MODELS.fitted.confidence, MODELS.value (fan_quantiles, support, industry_n6, industry_shrinkage),
     FAN and naics6For, ten test vectors computed by the Python port (the console's own ncdf and nqnt; 6 decimals),
     and node checks: the JavaScript, run in the snapshot's model section, reproduces the vectors and the Python value
     on model() outputs, and model() with the integration line in place of the old block gives out.conf = conf().p.
     RESULT.json (sorted keys, rounded floats) also holds every shipped value with its SE and the console's current
     value, the sensitivities, the checks with outcomes, the sources and a not_shipped block. Tests are listed in
     RESULT.json; the script exits 1 if any fails.

Data and fetch (each download in its own directory; read with python3 -I; nothing from a download is run)
  DealLedger broker listings (CC0): /tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots/<date>/listings.csv
     git clone --depth 1 https://github.com/jeffsosville/dealledger   (data/snapshots: 103 files 2026-02-23 to
     2026-10-06 are read; the 2026-02-23 file has no id column, so the data are 102 files, 2026-02-28 to 2026-10-06)
  Lie, E. and H. J. Lie (2002), "Multiples Used to Estimate Corporate Value", Financial Analysts Journal 58(2), 44-54:
     /tmp/claude-0/fit6/data/H-interv-cats-conf/acad_lie_lie_2002/paper.pdf
     curl -L -o paper.pdf https://www.biz.uiowa.edu/faculty/elie/ValByMult.pdf   (Table 3, p. 6; Table 1, p. 3)
  Empire Flippers sold listings with reconstructed sale prices (check only):
     /tmp/claude-0/data5/extra_ef_sale_ask_reconstruction/clean/ef_sale_ask_reconstructed.csv (Empire Flippers public
     marketplace API; reconstruction documented in that directory's DATA_DICTIONARY.md)
  BizBuySell Insight national medians (level check only): /tmp/claude-0/data5/marketplaces_sold/clean/
     bizbuysell_insight_long.csv (2025: median sale price, cash flow and revenue, sale/ask)
  Snapshot /tmp/claude-0/fit6snap/index.html (read only); harness /tmp/claude-0/fit6/harness.js.
  Research outputs, for the replication check only (optional): /tmp/claude-0/fit6/work/H-interv-cats-conf/v2/out/
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')      # deterministic sums
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import glob, hashlib, json, math, re, subprocess, sys, time
import numpy as np
import pandas as pd
from scipy import optimize, special, stats
from numpy.polynomial.hermite_e import hermegauss

T0 = time.time()
B_MAIN = int(sys.argv[1]) if len(sys.argv) > 1 else 200     # broker-cluster bootstrap draws, shipped SEs
QUICK = B_MAIN < 200                                         # a quick check: outputs go to the scratch directory
WORK = '/tmp/claude-0/fit6/work/fit3-confidence_accuracy'    # round 2's scratch (fit2-...) is left as it was
OUT = WORK + '/quick' if QUICK else '/tmp/claude-0/fit6/out/confidence_accuracy'
for _d in (OUT, WORK):
    os.makedirs(_d, exist_ok=True)
SNAP = '/tmp/claude-0/fit6snap/index.html'                 # frozen snapshot, read only
HARNESS = '/tmp/claude-0/fit6/harness.js'
DL_DIR = '/tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots'
LIE_PDF = '/tmp/claude-0/fit6/data/H-interv-cats-conf/acad_lie_lie_2002/paper.pdf'
EF_CSV = '/tmp/claude-0/data5/extra_ef_sale_ask_reconstruction/clean/ef_sale_ask_reconstructed.csv'
BBS_CSV = '/tmp/claude-0/data5/marketplaces_sold/clean/bizbuysell_insight_long.csv'
RESEARCH = '/tmp/claude-0/fit6/work/H-interv-cats-conf/v2/out'
R_REBASE = RESEARCH + '/conf_rebase.json'
R_ACC = RESEARCH + '/dl_accuracy.json'

B_ROB = max(40, B_MAIN // 2)                                 # draws for each robustness variant
SEED = 20261014
P_SHIP = 0.10                                                # decision rule: two-sided p below this ships a block
REF_SDE = 7e5                                                # reference SDE of the size term (the console's z.size centre)
RIDGE_VAR = 1.0                                              # judgment: N(0, 1) prior on industry terms in ln scale
TEXT_TOL = 0.01                                              # text price vs ask field: conflict at 1% or more
EQ_TOL = 0.005                                               # ask == revenue / ask == SDE within 0.5%
K_N6 = None                                                  # read from MODELS.value.industry_shrinkage.k_naics6
D_SAAS_N6 = 7                                                # fit6 D's n_override for saas (511210 rows, under the table's
                                                             # 8-row cut): the round-2 comparison only; conf() uses n = 0
CENTRE_MAIN = 'ind+size+em'                                  # shipped centring: industry, ln SDE, signed z.em, z.em^2
SENS_MODES = [('location-inclusive (round 2): industry + ln SDE', 'ind+size'),
              ('broker fixed effects + industry + ln SDE (location-inclusive)', 'ind+size+bfe'),
              ('broker fixed effects + shipped centring', 'ind+size+em+bfe')]
BFE_MIN = 15                                                 # broker fixed effect for brokers with 15+ in-support listings
CUT_STEP = 0.01                                              # label cut-offs: listing quartiles of p rounded to 0.01
EXTRAP_X = 3.0                                               # label Low, 'outside the fitted data', when out.extrapMax > 3
LO, HI = math.log(0.8), math.log(1 / 0.75)                   # BIZCOMPS within_25pct: |estimate - price| <= 25% of price
INDS = ['home', 'medical', 'vet', 'msp', 'saas', 'prof', 'mfg', 'dist', 'ecom', 'staff', 'land', 'wash', 'auto',
        'constr', 'fit', 'rest']

# online-business brokers (domains); their asks are multiples of a different market (research critique)
ONLINE_BROKERS = ['quietlight.com', 'websiteclosers.com', 'websiteproperties.com', 'latonas.com', 'appbusinessbrokers.com',
                  'feinternational.com', 'empireflippers.com', 'flippa.com', 'investors.club', 'acquire.com',
                  'digitalexits.com', 'motioninvest.com']
# the ask includes real estate where the listing's text says so
RE_INCLUDED = (r'(?:real estate|property|building|land and building|land & building|the land)\s+(?:is\s+)?(?:included|includes|incl\.?)'
               r'|includ(?:es|ing|ed)\s+(?:the\s+)?(?:commercial\s+)?(?:real estate|property|building|land)'
               r'|(?:with|plus)\s+(?:the\s+)?(?:commercial\s+)?real estate|real estate (?:and|&) business'
               r'|business (?:and|&) (?:the\s+)?real estate|price includes (?:the )?(?:real estate|property|building)')
TEXT_FLAGS = {'inventory_in_ask': r'inventory (?:is )?included|includ(?:es|ing) (?:all )?inventory|plus inventory|\+ ?inventory',
              'ebitda_word': r'ebitda', 'sde_word': r'\bsde\b|seller.?s discretionary|discretionary (?:earnings|cash)',
              'franchise': r'franchis'}
MONEY = r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(k|m|mm|million|thousand)?\b'
P_ASK = re.compile(r'(?:asking price|asking|list price|listing price|(?<![a-z])price)\s*(?:is|of)?\s*[:\-]?\s*' + MONEY, re.I)
P_REV = re.compile(r'(?:gross sales|gross revenue|annual revenue|gross annual revenue|revenue|sales)\s*(?:of)?\s*[:\-]?\s*' + MONEY, re.I)
IND_RE = {   # fit/hedonic.py's industry regexes (first match wins), as the research used them
    'rest': r'restaurant|pizza|cafe|coffee|bakery|bar\b|pub\b|tavern|grill|diner|sushi|taco|food truck|catering|brewery|ice cream|yogurt|deli\b|bistro',
    'home': r'hvac|plumb|electrical contractor|electrician|heating|air condition|roofing|pest control|garage door|handyman|home service|septic|water heater',
    'medical': r'dental|dentist|medical practice|clinic|physician|chiropract|physical therap|optometr|med ?spa|orthodont|pharmacy|home health|urgent care',
    'vet': r'veterinar|animal hospital|vet clinic|pet clinic',
    'msp': r'managed service|it services|it support|msp\b|cybersecurity|network services',
    'saas': r'saas|software|subscription platform|app\b',
    'prof': r'accounting|cpa\b|bookkeeping|tax practice|law firm|insurance agency|consulting firm|engineering firm|architect',
    'mfg': r'manufactur|machine shop|fabricat|cnc|plastics|printing company',
    'dist': r'distribut|wholesale',
    'ecom': r'e-?commerce|amazon|shopify|online store|fba\b',
    'staff': r'staffing|recruit|employment agency|temp agency',
    'land': r'landscap|lawn|tree service|irrigation|snow removal',
    'wash': r'car wash|carwash|laundromat|laundry|dry clean',
    'auto': r'auto repair|automotive|collision|body shop|tire|oil change|transmission|mechanic',
    'constr': r'construction|contractor|concrete|excavat|paving|drywall|framing|remodel',
    'fit': r'fitness|gym\b|yoga|pilates|martial arts|studio|crossfit|dance',
}
# Lie & Lie (2002), Table 3 (p. 6), Total Enterprise Valuation, Value/EBITDA column: fraction of |ln(estimate/actual)| < 0.15,
# number of observations and median error, by book value of assets; Table 1 (p. 3): book assets p25/p50/p75 $27M/$136M/$716M
LIE = [('small (assets <= $100M)', 0.0, 100.0, 0.178, 1692, 0.037),
       ('medium ($100M-$1B)', 100.0, 1000.0, 0.286, 1942, 0.023),
       ('large (> $1B)', 1000.0, math.inf, 0.389, 1127, -0.059)]
LIE_ASSETS_Q = (27.0, 136.0, 716.0)
# BizBuySell Insight 2025 national figures (bizbuysell_insight_long.csv, source_key businessexits_2025)
BBS_KEYS = {'median_sale_price': 'sale', 'median_cash_flow': 'cf', 'median_revenue': 'rev', 'avg_sale_to_ask_ratio': 'sale_to_ask'}
CURRENT = {'w_comps': .34, 'w_yrs': .30, 'w_fin': .22, 'w_typ': .14, 'typ_scale': 2.2, 'cut_high': .68, 'cut_moderate': .46}
# round 2's shipped table (out/confidence_accuracy.v2/RESULT.json), documented constants for the change log only
ROUND2 = dict(K=0.7442, b_size=-0.0617, b_size_se=0.0388, p_size=0.11, b_em=0.1989, b_em_se=0.0586, p_em=0.0007, tau2=0.0358, s_eq=0.41,
              cut_high=0.50, cut_moderate=0.40, p_reference=0.566, comps='I.comps (fit6 D: saas 7/32)', centring='industry + ln SDE')

RES = {'name': 'confidence_accuracy', 'js_key': 'confidence', 'round': 3, 'parameters': dict(
       B_main=B_MAIN, B_robust=B_ROB, seed=SEED, p_ship=P_SHIP, ref_sde=REF_SDE, ridge_var=RIDGE_VAR, text_tol=TEXT_TOL,
       eq_tol=EQ_TOL, band=[0.8, 1 / 0.75], centre_main=CENTRE_MAIN, sensitivity_centrings=dict(SENS_MODES), bfe_min=BFE_MIN,
       cut_step=CUT_STEP, extrap_x=EXTRAP_X)}
TESTS = {}
CHECKS = {}


def log(*a):
    print('[%5.0fs]' % (time.time() - T0), *a, flush=True)


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()[:n]


def rnd(o, sig=6):
    if isinstance(o, float):
        if not math.isfinite(o):
            return None
        return float('%.*g' % (sig, o))
    if isinstance(o, (np.floating,)):
        return rnd(float(o), sig)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, dict):
        return {str(k): rnd(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple, np.ndarray)):
        return [rnd(v, sig) for v in o]
    return o


# ------------------------------------------------------------------------------------------------------------------
# console replicas: the Abramowitz-Stegun normal CDF and Acklam's inverse, exactly as index.html has them
# ------------------------------------------------------------------------------------------------------------------
def ncdf_c(x):
    t = 1 / (1 + .2316419 * abs(x)); d = .3989423 * math.exp(-x * x / 2)
    p = d * t * (.3193815 + t * (-.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1 - p if x > 0 else p


def nqnt_c(p):
    a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924]
    b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857]
    c = [-.00778489400243029, -.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878]
    d = [.00778469570904146, .32246712907004, 2.445134137143, 3.75440866190742]
    pl = .02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - .5; r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


# ------------------------------------------------------------------------------------------------------------------
# 0. snapshot: MODELS, IND, current confidence formula
# ------------------------------------------------------------------------------------------------------------------
HTML = open(SNAP, encoding='utf-8').read()
_m = re.search(r'^const MODELS = (\{.*\});?\s*$', HTML, re.M)
MODELS = json.loads(_m.group(1).rstrip(';'))
_mf = re.search(r'^MODELS\.fitted=(\{.*\});\s*$', HTML, re.M)
FITTED = json.loads(_mf.group(1))
MV = MODELS['value']
FQ = MV['fan_quantiles']; SUP = MV['support']; LEVEL = MV['within_25pct']; N_FIT = MV['n_fit']
K_N6 = MV['industry_shrinkage']['k_naics6']
SD_EM = FITTED['sde_margin']['sd']
conf_src = re.search(r'const conf=clamp\((.*?)\);\s*\n\s*out\.conf=conf;\s*\n\s*out\.confLabel = (.*?);', HTML, re.S)
assert conf_src, 'current confidence formula not found'
TESTS['snapshot holds the confidence formula the brief describes (.34/.30/.22/.14, /2.2, .68/.46)'] = (
    '.34*I.comps+.30*clamp(s.yrs/8,0,1)+.22*s.fin+.14*clamp(1-typ/2.2,0,1)' in conf_src.group(1)
    and 'conf>.68?"High":conf>.46?"Moderate":"Low"' in conf_src.group(2))
_ob = re.search(r'\n(  const typ=Object\.values\(z\)[^\n]*\n  const conf=clamp\([^\n]*\n  out\.conf=conf;\n'
                r'  out\.confLabel = conf>\.68\?"High":conf>\.46\?"Moderate":"Low";)\n', HTML)
assert _ob, 'old confidence block not found'
OLD_BLOCK = _ob.group(1)                     # the four lines the integration line replaces inside model()
IND_COMPS_NOW = {}
for k in INDS:
    mm = re.search(r'\b' + k + r':\s*\{n:"[^"]*",\s*anchor:[0-9.]+,.*?comps:([0-9.]+)', HTML)
    IND_COMPS_NOW[k] = float(mm.group(1)) if mm else None
N6_FOR = dict(MV['naics6_for_industry'])
N6 = MV['industry_n6']
_i6 = re.search(r'^const IND2NAICS6=(\{[^\n]*\});\s*$', HTML, re.M)
IND2NAICS6 = json.loads(_i6.group(1))       # what naics6For() reads in the console
TESTS['naics6For (IND2NAICS6) maps every industry as MODELS.value.naics6_for_industry; saas has no 6-digit cell'] = (
    IND2NAICS6 == N6_FOR and 'saas' not in IND2NAICS6 and all(N6_FOR[k] in N6 for k in N6_FOR))


def comps_v(ind):
    """the depth conf() computes: n6/(n6+k_naics6) of the value model's own 6-digit cell; 0 without a cell (saas)"""
    n = N6.get(IND2NAICS6.get(ind, ''), 0)
    return n / (n + K_N6)


def comps_d(ind):
    """fit6 D's comps (industry_tailwind_and_comps.py), round 2's input: as comps_v but saas n = 7 (D's override)"""
    n = D_SAAS_N6 if ind == 'saas' else N6.get(N6_FOR.get(ind, ''), 0)
    return n / (n + K_N6)


COMPS_V = {k: comps_v(k) for k in INDS}
COMPS_D = {k: comps_d(k) for k in INDS}

# fan CDF in log space: probit-linear through the stored quantiles, end slopes beyond (the console's FAN / fanRatio)
FAN_P = sorted(float(k[1:]) / 100 for k in FQ)
FAN_Y = np.array([math.log(FQ['p%d' % round(p * 100)]) for p in FAN_P])
FAN_Z = np.array([stats.norm.ppf(p) for p in FAN_P])           # fitting (scipy)
FAN_ZC = [nqnt_c(p) for p in FAN_P]                             # shipped arithmetic (console's nqnt)


def zof(y, Z=FAN_Z):
    y = np.asarray(y, float); z = np.empty_like(y); dz = np.empty_like(y); Y = FAN_Y
    lo = y <= Y[0]; hi = y >= Y[-1]; mid = ~lo & ~hi
    s0 = (Z[1] - Z[0]) / (Y[1] - Y[0]); s1 = (Z[-1] - Z[-2]) / (Y[-1] - Y[-2])
    z[lo] = Z[0] + (y[lo] - Y[0]) * s0; dz[lo] = s0
    z[hi] = Z[-1] + (y[hi] - Y[-1]) * s1; dz[hi] = s1
    j = np.clip(np.searchsorted(Y, y[mid]) - 1, 0, len(Y) - 2); sl = (Z[j + 1] - Z[j]) / (Y[j + 1] - Y[j])
    z[mid] = Z[j] + (y[mid] - Y[j]) * sl; dz[mid] = sl
    return z, dz


def Fan(y):
    return special.ndtr(zof(y)[0])


def fan_pdf(y):
    z, dz = zof(y); return np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi) * dz


def G(s):
    s = np.asarray(s, float); return Fan(HI / s) - Fan(LO / s)


def dG(s):
    s = np.asarray(s, float); return -fan_pdf(HI / s) * HI / s ** 2 + fan_pdf(LO / s) * LO / s ** 2


def Fan_c(y):
    """shipped arithmetic: the console's nqnt knots and ncdf"""
    Y, Z, n = FAN_Y, FAN_ZC, len(FAN_Y)
    if y <= Y[0]:
        z = Z[0] + (y - Y[0]) * (Z[1] - Z[0]) / (Y[1] - Y[0])
    elif y >= Y[n - 1]:
        z = Z[n - 1] + (y - Y[n - 1]) * (Z[n - 1] - Z[n - 2]) / (Y[n - 1] - Y[n - 2])
    else:
        i = 0
        while y > Y[i + 1]:
            i += 1
        z = Z[i] + (y - Y[i]) * (Z[i + 1] - Z[i]) / (Y[i + 1] - Y[i])
    return ncdf_c(z)


def G_c(sig):
    return Fan_c(HI / sig) - Fan_c(LO / sig)


G1 = float(G(1.0)); G1c = G_c(1.0)
alt_def = float(Fan(math.log(1.25)) - Fan(math.log(0.75)))
CHECKS['level_definition'] = dict(stored_within_25pct=LEVEL, fan_reproduces=G1, fan_reproduces_console_arith=G1c,
                                  alt_definition_price_within_25pct_of_estimate=alt_def,
                                  note='MODELS.value.within_25pct is |estimate - price| <= 25% of the price, i.e. price/estimate in [0.80, 1.333]: '
                                       'the stored fan reproduces 0.4450 under that reading and 0.4346 under |price - estimate| <= 25% of the estimate')
TESTS['the stored fan reproduces within_25pct within 0.001 (BIZCOMPS definition)'] = abs(G1 - LEVEL) < 0.001
log('snapshot read; G(1) = %.5f (stored %.4f); alt definition %.4f' % (G1, LEVEL, alt_def))

# ------------------------------------------------------------------------------------------------------------------
# 1. DealLedger panel (research rules) and flags
# ------------------------------------------------------------------------------------------------------------------
FILES = sorted(glob.glob(os.path.join(DL_DIR, '*', 'listings.csv')))
_h = hashlib.sha256()
for f in FILES:
    _h.update(os.path.relpath(f, DL_DIR).encode()); _h.update(sha(f, 64).encode())
DL_DIGEST = _h.hexdigest()[:16]
COLS = ['id', 'title', 'asking_price', 'cash_flow', 'revenue', 'state', 'vertical', 'description', 'status', 'first_seen',
        'last_seen', 'broker_name', 'url', 'broker_domain', 'source_url']
frames = []
SNAP_ID = []                                    # snapshot dates whose file has an id column (the others drop out per id)
for f in FILES:
    d = pd.read_csv(f, low_memory=False, usecols=lambda c: c in COLS, dtype=str)
    d['snap'] = os.path.basename(os.path.dirname(f))
    if 'id' in d.columns:
        SNAP_ID.append(d['snap'].iloc[0] if len(d) else os.path.basename(os.path.dirname(f)))
    frames.append(d)
SNAP_ALL = [os.path.basename(os.path.dirname(f)) for f in FILES]
FILES_META = dict(read=len(FILES), first_read=SNAP_ALL[0], last_read=SNAP_ALL[-1], with_id=len(SNAP_ID), first_with_id=SNAP_ID[0],
                  last_with_id=SNAP_ID[-1], without_id=[s for s in SNAP_ALL if s not in SNAP_ID],
                  note='a file without an id column contributes no rows to the per-id panel (pandas groupby drops a missing key)')
A = pd.concat(frames, ignore_index=True)
for c in ['asking_price', 'cash_flow', 'revenue']:
    A[c] = pd.to_numeric(A[c], errors='coerce')
A = A.sort_values('snap')                       # the research's call (default sort): reproduces its 12,247 / 5,940
g = A.groupby('id', sort=False)
P = g.last()
P['first_snap'] = g['snap'].min(); P['last_snap'] = g['snap'].max(); P['n_snaps'] = g['snap'].nunique()
P = P.reset_index()
P['ask'] = P['asking_price']; P['cf'] = P['cash_flow']; P['rev'] = P['revenue']
D = P[(P.ask >= 2e4) & (P.ask <= 5e7) & (P.cf >= 1e4) & (P.cf <= 2e7)].copy()
D['mult'] = D.ask / D.cf
D = D[(D.mult >= .3) & (D.mult <= 15)]
D['text'] = (D['title'].fillna('') + ' . ' + D['vertical'].fillna('') + ' . ' + D['description'].fillna('')).str.lower()
D = D.drop_duplicates(subset=['ask', 'cf', 'title'])


def classify(t):
    for k, p in IND_RE.items():
        if re.search(p, t):
            return k
    return 'other'


D['ind'] = D.text.apply(classify)
D['has_rev'] = (D.rev.notna() & (D.rev > D.cf))
n_all, n_rev = len(D), int(D.has_rev.sum())
TESTS['panel reproduces the research (12,247 listings, 5,940 with revenue > SDE)'] = (n_all == 12247 and n_rev == 5940)
FILES_META.update(panel_first_seen_min=str(D.first_snap.min()), panel_last_seen_max=str(D.last_snap.max()))
TESTS['the panel comes from the files with an id column only (first seen no earlier than the first such file)'] = (
    str(D.first_snap.min()) >= FILES_META['first_with_id'] and set(FILES_META['without_id']) <= {FILES_META['first_read']})
H = D[D.has_rev].copy().reset_index(drop=True)
H['src'] = H.url.fillna(H.source_url).fillna('')
H['dom'] = (H.broker_domain.fillna(H.src.str.extract(r'https?://([^/]+)', expand=False)).fillna('')
            .str.replace(r'^www\.', '', regex=True).str.lower())
H['dom'] = np.where(H.dom == '', 'unknown:' + H.broker_name.fillna('').str.lower(), H.dom)
tl = (H.title.fillna('') + ' . ' + H.description.fillna('')).str.lower()
H['online_broker'] = H.dom.isin(ONLINE_BROKERS)
H['re_in_ask'] = tl.str.contains(RE_INCLUDED, regex=True)
for k, p in TEXT_FLAGS.items():
    H[k] = tl.str.contains(p, regex=True)


def money(m):
    v = float(m.group(1).replace(',', '')); u = (m.group(2) or '').lower()
    return v * (1e3 if u in ('k', 'thousand') else 1e6 if u in ('m', 'mm', 'million') else 1)


def first_money(p, t):
    m = p.search(t); return money(m) if m else np.nan


TT = (H.title.fillna('') + ' . ' + H.description.fillna(''))
H['t_ask'] = [first_money(P_ASK, t) for t in TT]
H['t_rev'] = [first_money(P_REV, t) for t in TT]
H['ask_eq_rev'] = (H.ask / H.rev - 1).abs() < EQ_TOL
H['ask_eq_cf'] = (H.ask / H.cf - 1).abs() < EQ_TOL
H['text_conflict'] = H.t_ask.notna() & ~((H.t_ask / H.ask - 1).abs() < TEXT_TOL)
H['swapped'] = (H.text_conflict & ((H.t_ask / H.rev - 1).abs() < TEXT_TOL) & ((H.t_rev / H.ask - 1).abs() < TEXT_TOL))
H['parse_error'] = H.ask_eq_rev | H.ask_eq_cf | H.text_conflict
H['main_street'] = ~H.parse_error & ~H.online_broker & ~H.re_in_ask
log('panel: %d listings, %d with revenue > SDE; parse errors %d (ask=rev %d, ask=SDE %d, text conflict %d of which swapped %d); '
    'online %d; RE in ask %d; Main Street %d' % (n_all, n_rev, H.parse_error.sum(), H.ask_eq_rev.sum(), H.ask_eq_cf.sum(),
                                                  H.text_conflict.sum(), H.swapped.sum(), H.online_broker.sum(), H.re_in_ask.sum(),
                                                  H.main_street.sum()))

# ------------------------------------------------------------------------------------------------------------------
# 2. node probe: fitted value, typMargin, z.em, extrapolation, model() check, current confidence
# ------------------------------------------------------------------------------------------------------------------
EF = pd.read_csv(EF_CSV)
EF = EF[(~EF.flag_top_censored) & (~EF.flag_wide_bracket) & (~EF.flag_no_ask) & (EF.listing_price > 0)
        & (EF.average_annual_net_profit > 0) & (EF.profit_margin > 0) & (EF.profit_margin < 100)].copy().reset_index(drop=True)
EF['cf'] = EF.average_annual_net_profit.astype(float); EF['rev'] = EF.cf / (EF.profit_margin / 100.0)
BBS = pd.read_csv(BBS_CSV)
bb = BBS[(BBS.segment == 'all') & (BBS.period == '2025') & (BBS.source_key == 'businessexits_2025') & BBS.metric.isin(list(BBS_KEYS))]
BBS25 = {BBS_KEYS[m]: float(v) for m, v in zip(bb.metric, bb.value)}
assert set(BBS25) == set(BBS_KEYS.values()), BBS25
GRID_SDE = [5e4, 1.5e5, 3e5, 7e5, 1.45e6, 2.5e6]
PROBE_JS = r"""/* probe: console quantities for listings and test businesses, through the harness (frozen snapshot).
   usage: node probe.js HARNESS CFG.json OUT.json ; CFG holds numbers only (no downloaded text) */
const fs=require('fs'); const H=require(process.argv[2]); const A=H.load();
const cfg=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const SUP=A.MODELS.value.support, SD=A.MODELS.fitted.sde_margin.sd, clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function ext(ern,rev){ const w=[];
  const chk=(v,s2,f)=>{ if(v>s2.p99) w.push([f,+(v/s2.p99).toFixed(1),v/s2.p99]); else if(v<s2.p1) w.push([f,+(s2.p1/v).toFixed(1),s2.p1/v]); };
  chk(ern,SUP.ern,'ern'); chk(rev,SUP.rev,'rev'); chk(ern/Math.max(rev,1),SUP.margin,'margin'); return w; }
function row(key,cf,rev){ const f=A.fitValue(cf,rev,key,2026), tm=A.typMargin(key,cf);
  const zr=Math.log(Math.max(cf/Math.max(rev,1),1e-4)/tm)/SD, w=ext(cf,rev);
  return [f.point,f.naics6||'',tm,zr,clamp(zr,-3.2,3.2),w.length?Math.max(...w.map(v=>v[1])):0,w.map(v=>v[0]).join('|'),w.length?Math.max(...w.map(v=>v[2])):0]; }
function full(key,cf,rev,ask){ const I=A.IND[key], R=A.sizeRefs(cf);
  const s={ind:key,rev:rev,ern:cf,ask:ask,grw:I.grw,gm:I.gm,rec:I.rec,cc:.16,ret:I.ret,plt:.40,own:R.own,mgt:R.mgt,fin:R.fin,
           yrs:10,buyers:I.buyers||50,st:null,franchise:false};
  const o=A.model(s); return [o.emRaw,o.z.em,o.extrap.map(e=>e.x),o.extrapMax,o.conf,o.confLabel,o.fv.point]; }
const res={}; for(const k in cfg.sets){ res[k]=cfg.sets[k].map(([key,cf,rev])=>row(key,cf,rev)); }
res.full=(cfg.full||[]).map(([key,cf,rev,ask])=>full(key,cf,rev,ask));
res.typm=cfg.typm.map(([key,cf])=>A.typMargin(key,cf));
fs.writeFileSync(process.argv[4],JSON.stringify(res)); console.log('ok');
"""
open(WORK + '/probe.js', 'w').write(PROBE_JS)
keyof = lambda k: k if k in INDS else 'zz_other'
cfg = {'sets': {'dl': [[keyof(k), float(c), float(r)] for k, c, r in zip(H.ind, H.cf, H.rev)],
                'ef': [['ecom', float(c), float(r)] for c, r in zip(EF.cf, EF.rev)],
                'bbs': [[keyof(k), BBS25['cf'], BBS25['rev']] for k in INDS + ['other']]},
       'typm': [[k, e] for k in INDS for e in GRID_SDE]}
json.dump(cfg, open(WORK + '/probe_cfg.json', 'w'))
r = subprocess.run(['node', WORK + '/probe.js', HARNESS, WORK + '/probe_cfg.json', WORK + '/probe_out.json'], capture_output=True, text=True, timeout=3000)
assert r.returncode == 0, r.stderr[-3000:]
PR = json.load(open(WORK + '/probe_out.json'))
TYPM = {(k, e): v for (k, e), v in zip([(k, e) for k in INDS for e in GRID_SDE], PR['typm'])}
# second pass: model() for every classified listing (check) and for peer-median businesses (current confidence)
cols = ['V', 'n6', 'tm', 'zem_raw', 'zem', 'xmax', 'xdims', 'ext_raw']
H = pd.concat([H, pd.DataFrame(PR['dl'], columns=cols)], axis=1)
full_rows = [[k, float(c), float(r), float(v)] for k, c, r, v in zip(H.ind, H.cf, H.rev, H.V) if k in INDS]
peer_rows = [[k, e, e / TYPM[(k, e)], 1.0] for k in INDS for e in GRID_SDE]
cfg2 = {'sets': {'peer': [[k, e, rv] for k, e, rv, _ in peer_rows]}, 'full': full_rows + peer_rows, 'typm': []}
json.dump(cfg2, open(WORK + '/probe_cfg2.json', 'w'))
r = subprocess.run(['node', WORK + '/probe.js', HARNESS, WORK + '/probe_cfg2.json', WORK + '/probe_out2.json'], capture_output=True, text=True, timeout=3000)
assert r.returncode == 0, r.stderr[-3000:]
PR2 = json.load(open(WORK + '/probe_out2.json'))
FULL = PR2['full']
cls_idx = [i for i, k in enumerate(H.ind) if k in INDS]
bad = 0
for j, i in enumerate(cls_idx):
    emRaw, zem, xs, xm, cnow, lnow, pt = FULL[j]
    row = H.iloc[i]
    if abs(zem - row.zem) > 1e-12 or abs(xm - row.xmax) > 1e-12 or abs(pt - row.V) > 1e-6 * max(1, pt):
        bad += 1
TESTS['probe z.em, extrapolation and value equal model() for every classified listing'] = (bad == 0)
PEER = []
for j, (k, e, rv, _) in enumerate(peer_rows):
    emRaw, zem, xs, xm, cnow, lnow, pt = FULL[len(cls_idx) + j]
    PEER.append(dict(ind=k, ern=e, rev=rv, zem=zem, xmax=xm, xlist=xs, conf_now=cnow, label_now=lnow, V=pt))
PEER = pd.DataFrame(PEER)
EFX = pd.DataFrame(PR['ef'], columns=cols); EF = pd.concat([EF, EFX], axis=1)
BBX = pd.DataFrame(PR['bbs'], columns=cols); BBX['ind'] = INDS + ['other']
log('node probe done: %d listings, %d model() checks (mismatches %d), %d EF deals' % (len(H), len(cls_idx), bad, len(EF)))

H['r'] = np.log(H.ask / H.V)
H['lsde_c'] = np.log(np.clip(H.cf, SUP['ern']['p1'], SUP['ern']['p99']) / REF_SDE)
H['azem'] = H.zem.abs()
H['in_sup'] = H.xmax == 0
H['margin'] = H.cf / np.maximum(H.rev, 1.0)                     # as model() computes it: s.ern / max(s.rev, 1)
H['m_out'] = (H.margin < SUP['margin']['p1']) | (H.margin > SUP['margin']['p99'])
H['outside'] = (H.xmax > EXTRAP_X) | H.m_out                    # the label rule: Low, 'outside the fitted data'
TESTS['the margin flag agrees with the probe\'s extrapolation dimensions (margin past support)'] = bool(
    (H.m_out == H.xdims.str.contains('margin')).all())

# ------------------------------------------------------------------------------------------------------------------
# 3. level gap
# ------------------------------------------------------------------------------------------------------------------
def lev(x):
    return dict(n=int(len(x)), ask_over_V=float(np.exp(np.median(x.r))) if len(x) else np.nan, ask_over_SDE=float(x.mult.median()) if len(x) else np.nan,
                V_over_SDE=float(np.median(x.V / x.cf)) if len(x) else np.nan, median_SDE=float(x.cf.median()) if len(x) else np.nan,
                share_in_support=float(x.in_sup.mean()) if len(x) else np.nan)


G0 = H; G1_ = H[~H.parse_error]; G2_ = G1_[~G1_.online_broker]; G3_ = G2_[~G2_.re_in_ask]
LG = [('research panel (revenue > SDE)', lev(G0)), ('  in support', lev(G0[G0.in_sup])),
      ('  ask field = revenue field', lev(G0[G0.ask_eq_rev])), ('  ask field = cash-flow field', lev(G0[G0.ask_eq_cf])),
      ('  text price contradicts ask field', lev(G0[G0.text_conflict & ~G0.ask_eq_rev & ~G0.ask_eq_cf])),
      ('  of which ask and revenue swapped', lev(G0[G0.swapped])),
      ('A: parse errors removed', lev(G1_)), ('  online-business brokers', lev(G1_[G1_.online_broker])),
      ('B: A without online brokers', lev(G2_)), ('  real estate in the ask (text)', lev(G2_[G2_.re_in_ask])),
      ('C: Main Street (B without real estate)', lev(G3_)), ('  C in support', lev(G3_[G3_.in_sup])),
      ('  C, EBITDA in the text', lev(G3_[G3_.ebitda_word])), ('  C, inventory in the ask (text)', lev(G3_[G3_.inventory_in_ask])),
      ('  C, franchise', lev(G3_[G3_.franchise])),
      ('  C, two largest networks (fcbb.com, sunbeltnetwork.com)', lev(G3_[G3_.dom.isin(['fcbb.com', 'sunbeltnetwork.com'])])),
      ('  C, other brokers', lev(G3_[~G3_.dom.isin(['fcbb.com', 'sunbeltnetwork.com'])]))]
LGT = pd.DataFrame([dict(step=s, **v) for s, v in LG])
LGT.to_csv(OUT + '/level_gap.csv', index=False, float_format='%.4f')
C_in = G3_[G3_.in_sup]
by_ind = {k: lev(g) for k, g in C_in.groupby('ind')}
by_band = {str(b): lev(g) for b, g in C_in.groupby(pd.cut(C_in.cf, [0, 1e5, 2e5, 3.5e5, 7e5, 1.5e6, 2e7]), observed=True)}
bbs_ratio = {k: BBS25['sale'] / v for k, v in zip(BBX.ind, BBX.V)}
_nr = D[~D.has_rev]
RECON = dict(all_listings=dict(n=int(len(D)), ask_over_SDE=float(D.mult.median())),
             all_listings_sde_50k_20M=dict(n=int(((D.cf >= 5e4) & (D.cf <= 2e7)).sum()), ask_over_SDE=float(D[(D.cf >= 5e4) & (D.cf <= 2e7)].mult.median())),
             without_revenue=dict(n=int(len(_nr)), ask_over_SDE=float(_nr.mult.median()), share_ask_equals_cash_flow=float(((_nr.ask / _nr.cf - 1).abs() < EQ_TOL).mean())),
             with_revenue=dict(n=int(len(H)), ask_over_SDE=float(H.mult.median()), share_ask_equals_revenue=float(H.ask_eq_rev.mean())),
             note=("fit6 E's 2.98 is over all listings with SDE $50k-$20M (keyed on URL, 109 files); the research's 3.67 is the revenue-bearing "
                   "subset, where a third of asks are the revenue; listings without revenue carry the opposite error (ask = cash flow, multiple 1.0), "
                   "which pulls the all-listing median down"))
RES['level_gap'] = dict(
    steps={s: v for s, v in LG}, main_street_in_support_by_industry=by_ind, main_street_in_support_by_sde=by_band,
    bizbuysell_2025=dict(median_sale=BBS25['sale'], median_cash_flow=BBS25['cf'], median_revenue=BBS25['rev'],
                         sale_to_ask=BBS25['sale_to_ask'], model_value_of_median_business=dict(zip(BBX.ind, BBX.V)),
                         median_sale_over_model_value=bbs_ratio,
                         note='ratio of medians (indicative): BizBuySell 2025 median closed sale over the model value of a business with the median cash flow and revenue'),
    explanation=None, reconcile_with_E_panel=None)
RES['level_gap']['reconcile_with_E_panel'] = RECON
ex_parse = lev(G0)['ask_over_V'] / lev(G1_)['ask_over_V']
share_parse = float(H.parse_error.mean())
RES['level_gap']['explanation'] = (
    'The research panel\'s gap (median ask %.2fx the fitted value in support, %.2fx overall) is mostly a parse error: in %d of the %d revenue-bearing listings (%.0f%%) the ask field '
    'holds the revenue (median ask/value %.2f), in %d it holds the cash flow, and in %d more the asking price written in the listing '
    'contradicts the field (%d of them ask and revenue swapped). Removing them brings the median ask to %.2fx the fitted value and '
    'ask/SDE from %.2f to %.2f. Online-business brokers (%d listings) move it little (%.2fx); asks that include real estate (%d, '
    '%.2fx) take it to %.2fx; the two largest Main-Street networks sit at %.2fx. What remains (about 1.4-1.6x) is the ordinary ask '
    'premium (BizBuySell 2025 sale/ask %.2f) on top of a market level above BIZCOMPS: the 2025 median BizBuySell sale is %.2fx the '
    'model value of a business with the median cash flow and revenue (unclassified industry). Centred spreads do not depend on the '
    'level, but the parse errors do move the spreads: a listing whose ask is its revenue has r = ln(revenue / V), a function of '
    'the margin, which manufactured most of the margin gradient.' % (
        lev(G0[G0.in_sup])['ask_over_V'], lev(G0)['ask_over_V'], int(H.ask_eq_rev.sum()), len(H), 100 * H.ask_eq_rev.mean(), lev(G0[G0.ask_eq_rev])['ask_over_V'], int(H.ask_eq_cf.sum()),
        int((H.text_conflict & ~H.ask_eq_rev & ~H.ask_eq_cf).sum()), int(H.swapped.sum()), lev(G1_)['ask_over_V'],
        lev(G0)['ask_over_SDE'], lev(G1_)['ask_over_SDE'], int(G1_.online_broker.sum()), lev(G1_[G1_.online_broker])['ask_over_V'],
        int(G2_.re_in_ask.sum()), lev(G2_[G2_.re_in_ask])['ask_over_V'], lev(G3_)['ask_over_V'],
        lev(G3_[G3_.dom.isin(['fcbb.com', 'sunbeltnetwork.com'])])['ask_over_V'], BBS25['sale_to_ask'], bbs_ratio['other']))
log('level gap: research %.3f -> parse errors removed %.3f -> Main Street %.3f' % (lev(G0)['ask_over_V'], lev(G1_)['ask_over_V'], lev(G3_)['ask_over_V']))

# ------------------------------------------------------------------------------------------------------------------
# estimation helpers
# ------------------------------------------------------------------------------------------------------------------
IK = [k for k in INDS]                                     # industry dummies; 'other' (unclassified) is the reference


def l1fit(X, y, it=200, tol=1e-9):
    """median (L1) regression by iteratively reweighted least squares"""
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(it):
        w = 1 / np.maximum(np.abs(y - X @ b), 1e-4)
        nb = np.linalg.solve(X.T @ (X * w[:, None]) + 1e-10 * np.eye(X.shape[1]), X.T @ (w * y))
        if np.max(np.abs(nb - b)) < tol:
            b = nb; break
        b = nb
    return b


def ind_cols(S):
    return [(S.ind.values == k).astype(float) for k in IK]


def centre(S, ref=None, mode=CENTRE_MAIN):
    """centred residual; the location model (a median regression) is fitted on ref (default S in support) and applied to
    S. mode: 'ind' (industry medians), or '+'-joined terms on top of industry and ln SDE: 'em' adds signed z.em and
    z.em^2 (the shipped centring), 'bfe' adds a fixed effect for each broker with BFE_MIN or more listings in ref"""
    ref = S[S.in_sup] if ref is None else ref
    if mode == 'ind':
        med = ref.groupby('ind').r.median()
        return S.r.values - S.ind.map(med).fillna(ref.r.median()).values
    parts = mode.split('+')
    assert parts[:2] == ['ind', 'size'] and set(parts[2:]) <= {'em', 'bfe'}, mode
    bro = []
    if 'bfe' in parts:
        vc = ref.dom.value_counts(); bro = sorted(vc[vc >= BFE_MIN].index)

    def X_of(T):
        cols = [np.ones(len(T)), T.lsde_c.values]
        if 'em' in parts:
            cols += [T.zem.values, T.zem.values ** 2]
        return np.column_stack(cols + ind_cols(T) + [(T.dom.values == d).astype(float) for d in bro])
    a = l1fit(X_of(ref), ref.r.values)
    return S.r.values - X_of(S) @ a


def n_bfe(S):
    vc = S[S.in_sup].dom.value_counts(); return int((vc >= BFE_MIN).sum())


def inside(c):
    return ((c >= LO) & (c <= HI)).astype(float)


def scale_mle(X, y, prior=None, b0=None, offset=None, it=100):
    """y ~ Bernoulli(G(exp(offset + X b))) by Fisher scoring; prior = {col: variance} (zero-mean Gaussian)"""
    k = X.shape[1]; b = np.zeros(k) if b0 is None else b0.copy(); off = 0.0 if offset is None else offset
    pv = np.zeros(k)
    if prior:
        for j, v in prior.items():
            pv[j] = 1.0 / v

    def ll(bb):
        p = np.clip(G(np.exp(off + X @ bb)), 1e-12, 1 - 1e-12)
        return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)) - 0.5 * np.sum(pv * bb * bb))
    cur = ll(b)
    for _ in range(it):
        s = np.exp(off + X @ b); p = np.clip(G(s), 1e-12, 1 - 1e-12); dp = dG(s) * s
        w = dp / (p * (1 - p))
        score = X.T @ ((y - p) * w) - pv * b
        info = X.T @ (X * (dp * w)[:, None]) + np.diag(pv)
        step = np.linalg.solve(info + 1e-12 * np.eye(k), score)
        if np.max(np.abs(step)) < 1e-9:
            break
        t, ok = 1.0, False
        for _h in range(12):
            nb = b + t * step; nl = ll(nb)
            if nl >= cur - 1e-10:
                ok = True; break
            t /= 2
        if not ok:
            break
        gain = nl - cur
        b, cur = nb, nl
        if gain < 1e-8 or np.max(np.abs(t * step)) < 1e-9:     # the fan link is piecewise: stop at 1e-8 in log-likelihood
            break
    return b, cur


def design(S, terms=('size', 'em'), ind=True):
    cols = [np.ones(len(S))]
    for t in terms:
        cols.append({'size': S.lsde_c.values, 'em': S.azem.values, 'hinge': np.maximum(S.azem.values - 1, 0), 'em2': S.azem.values ** 2,
                     'em_lo': np.maximum(-S.zem.values, 0), 'em_hi': np.maximum(S.zem.values, 0)}[t])
    nt = len(cols)
    if ind:
        cols += ind_cols(S)
    X = np.column_stack(cols)
    prior = {j: RIDGE_VAR for j in range(nt, X.shape[1])} if ind else None
    return X, prior, nt


def fit_bin(S, terms=('size', 'em'), mode=CENTRE_MAIN, ind=True):
    In = S[S.in_sup]
    c = centre(In, mode=mode); y = inside(c)
    X, prior, nt = design(In, terms, ind)
    b, L = scale_mle(X, y, prior)
    return b, L, nt


def fit_abs(S, est='ols', trim=None, mode=CENTRE_MAIN):
    In = S[S.in_sup]
    a = np.abs(centre(In, mode=mode)); X = np.column_stack([np.ones(len(In)), In.lsde_c.values, In.azem.values] + ind_cols(In))
    if trim is not None:
        keep = a <= np.quantile(a, 1 - trim); a = a[keep]; X = X[keep]
    b = np.linalg.lstsq(X, a, rcond=None)[0] if est == 'ols' else l1fit(X, a)
    return np.array([b[1] / b[0], b[2] / b[0]]), b


def cluster_boot(S, fn, B, seed):
    """broker-cluster bootstrap; with fewer than 20 brokers (one subset), listings are resampled instead"""
    rng = np.random.default_rng(seed)
    br = S.dom.values if S.dom.nunique() >= 20 else np.arange(len(S)).astype(str)
    ub = np.array(sorted(set(br))); idx = {u: np.where(br == u)[0] for u in ub}
    out = []
    for _ in range(B):
        pick = rng.choice(ub, len(ub)); ii = np.concatenate([idx[u] for u in pick])
        out.append(fn(S.iloc[ii]))
    return np.array(out)


def pval(est, se):
    return float(2 * stats.norm.sf(abs(est) / se)) if se > 0 else 0.0


# ------------------------------------------------------------------------------------------------------------------
# 4. replication of the research's regression on its own panel
# ------------------------------------------------------------------------------------------------------------------
def research_ols(S):
    In = S[S.in_sup]
    c = In.r.values - In.groupby('ind').r.transform('median').values
    X = np.column_stack([np.ones(len(In)), np.log(In.cf.values / 7e5), In.azem.values] + ind_cols(In))
    w_all = float(np.mean(inside(In.r.values - np.median(In.r.values))))       # dl_accuracy.py: centred on the pooled median
    return np.linalg.lstsq(X, np.abs(c), rcond=None)[0][:3], w_all, float(np.mean(inside(c)))


def research_joint(S):
    """conf_rebase.py: |r - industry median| on ln(SDE/700k), |z.em|, outside-support, ln(times past the edge), industry; all listings"""
    c = np.abs(S.r.values - S.groupby('ind').r.transform('median').values)
    X = np.column_stack([np.ones(len(S)), np.log(S.cf.values / 7e5), S.azem.values, (S.ext_raw.values > 0).astype(float),
                         np.log(np.maximum(S.ext_raw.values, 1.0))] + ind_cols(S))
    return np.linalg.lstsq(X, c, rcond=None)[0][:5]


rep_b, rep_w, rep_wi = research_ols(H)
rep_j = research_joint(H)
rep = dict(panel_n=len(H), in_support_n=int(H.in_sup.sum()), in_support_regression=dict(const=rep_b[0], ln_sde=rep_b[1], abs_zem=rep_b[2]),
           joint_regression=dict(const=rep_j[0], ln_sde_700k=rep_j[1], abs_zem=rep_j[2], outside_support=rep_j[3], ln_times_past_edge=rep_j[4]),
           within25_in_support=rep_w, within25_in_support_industry_centred=rep_wi)
if os.path.exists(R_REBASE) and os.path.exists(R_ACC):
    rr = json.load(open(R_REBASE)); ra = json.load(open(R_ACC))
    rep['research_joint_regression_all_listings'] = {k: rr['coefficients'][k] for k in ['const', 'ln_sde_700k', 'abs_zem']}
    rep['research_in_support_within25'] = ra['in_support']['within25']
    rep['research_n'] = rr['n_listings']
    rep['note'] = 'the research panel is reproduced listing for listing (5,940) and its joint regression coefficient for coefficient'
    TESTS['research in-support within-25 share reproduced (0.369 pooled-median centring)'] = abs(rep_w - ra['in_support']['within25']) < 0.002
    TESTS['research joint regression reproduced (0.2475, -0.0371, 0.1601)'] = (abs(rep_j[0] - rr['coefficients']['const'][0]) < 0.0006
        and abs(rep_j[1] - rr['coefficients']['ln_sde_700k'][0]) < 0.0006 and abs(rep_j[2] - rr['coefficients']['abs_zem'][0]) < 0.0006)
RES['replication'] = rep

# ------------------------------------------------------------------------------------------------------------------
# 5-6. gradients: main estimate and robustness
# ------------------------------------------------------------------------------------------------------------------
PANELS = {'research panel': H, 'parse errors removed': H[~H.parse_error], 'Main Street': H[H.main_street]}
MS = PANELS['Main Street']
bm, Lm, ntm = fit_bin(MS)
boot = cluster_boot(MS, lambda S: fit_bin(S)[0], B_MAIN, SEED)
se_m = boot.std(0, ddof=1)
MAIN = dict(centring='industry, ln SDE, signed z.em and z.em^2 (median regression); scale only',
            n_in_support=int(MS.in_sup.sum()), n_brokers=int(MS[MS.in_sup].dom.nunique()), within25=float(np.mean(inside(centre(MS[MS.in_sup])))),
            ln_s0=bm[0], ln_s0_se=se_m[0], b_size=bm[1], b_size_se=se_m[1], b_em=bm[2], b_em_se=se_m[2],
            p_size=pval(bm[1], se_m[1]), p_em=pval(bm[2], se_m[2]), loglik=Lm,
            industry=dict(zip(IK, bm[3:])), industry_se=dict(zip(IK, se_m[3:])))
log('main (location-adjusted centring): b_size %.4f (%.4f) b_em %.4f (%.4f) on %d listings, %d brokers' % (
    bm[1], se_m[1], bm[2], se_m[2], MAIN['n_in_support'], MAIN['n_brokers']))


# the location trend the shipped centring removes: median centred residual by signed z.em, under round 2's centring and the shipped one
def loc_trend(S, mode):
    In_ = S[S.in_sup]; c = centre(In_, mode=mode)
    bins = pd.cut(In_.zem.values, [-3.3, -2, -1, -0.5, 0, 0.5, 1, 2, 3.3])
    t = pd.Series(c).groupby(bins, observed=True).agg(['size', 'median'])
    return [dict(z_em=str(k), n=int(v['size']), median_centred=float(v['median'])) for k, v in t.iterrows()]


LOC_TREND = {'industry + ln SDE (round 2)': loc_trend(MS, 'ind+size'), 'shipped (+ signed z.em, z.em^2)': loc_trend(MS, CENTRE_MAIN)}

# sensitivities of the centring, each with its own broker-cluster bootstrap (B_MAIN draws); K and P at the reference in section 10
SENS = []
for j, (lab, mode) in enumerate(SENS_MODES):
    b, L, _ = fit_bin(MS, mode=mode)
    bs = cluster_boot(MS, lambda S, m=mode: fit_bin(S, mode=m)[0][:3], B_MAIN, SEED + 90 + j)
    se = bs.std(0, ddof=1)
    SENS.append(dict(centring=lab, mode=mode, b_size=b[1], b_size_se=se[1], p_size=pval(b[1], se[1]), b_em=b[2], b_em_se=se[2], p_em=pval(b[2], se[2]),
                     ask_scale_at_reference=float(np.exp(b[0])), ask_scale_se=float(np.exp(b[0]) * se[0]),
                     within25=float(np.mean(inside(centre(MS[MS.in_sup], mode=mode)))), n_broker_effects=n_bfe(MS) if 'bfe' in mode else 0))
    log('sensitivity %s: b_size %.4f (%.4f) b_em %.4f (%.4f) ask scale %.3f' % (mode, b[1], se[1], b[2], se[2], np.exp(b[0])))

ROB = []


def add_rob(label, panel, kind, est, se, n, role='robustness'):
    ROB.append(dict(variant=label, panel=panel, role=role, kind=kind, size=est[0], size_se=se[0], em=est[1], em_se=se[1], n=n))


for i, (pn, S) in enumerate(PANELS.items()):
    if pn == 'Main Street':
        add_rob('binary within-25 scale model (main)', pn, 'ln scale per unit', bm[1:3], se_m[1:3], MAIN['n_in_support'], role='main')
        for sv in SENS:
            add_rob('binary, centring: ' + sv['centring'], pn, 'ln scale per unit', [sv['b_size'], sv['b_em']], [sv['b_size_se'], sv['b_em_se']],
                    MAIN['n_in_support'], role='sensitivity (centring)')
        continue
    b, _, _ = fit_bin(S); bs = cluster_boot(S, lambda X: fit_bin(X)[0][1:3], B_ROB, SEED + 1 + i)
    add_rob('binary within-25 scale model', pn, 'ln scale per unit', b[1:3], bs.std(0, ddof=1), int(S.in_sup.sum()), role='panel comparison')
log('panels done')
variants = [('binary, centred on industry only (location-inclusive in size and margin)', lambda S: fit_bin(S, mode='ind')[0][1:3], 'ln scale per unit'),
            ('|r| OLS (research form), relative', lambda S: fit_abs(S, 'ols')[0], 'relative to intercept'),
            ('|r| median regression, relative', lambda S: fit_abs(S, 'lad')[0], 'relative to intercept'),
            ('|r| OLS trimmed top 2.5%, relative', lambda S: fit_abs(S, 'ols', .025)[0], 'relative to intercept'),
            ('|r| OLS trimmed top 5%, relative', lambda S: fit_abs(S, 'ols', .05)[0], 'relative to intercept')]
for j, (lab, fn, kind) in enumerate(variants):
    e = fn(MS); bs = cluster_boot(MS, fn, B_ROB, SEED + 10 + j)
    add_rob(lab, 'Main Street', kind, e, bs.std(0, ddof=1), int(MS.in_sup.sum()))
log('estimators done')
_fs = np.sort(MS[MS.in_sup].first_snap.astype(str).values); first_med = str(_fs[(len(_fs) - 1) // 2])     # median first-seen date
SUBSETS = [('SDE >= $100k', MS.cf >= 1e5), ('|z.em| <= 2', MS.azem <= 2), ('first seen <= %s (early half)' % first_med, MS.first_snap <= first_med),
           ('first seen > %s (late half)' % first_med, MS.first_snap > first_med), ('classified industries only', MS.ind != 'other'),
           ('fcbb.com and sunbeltnetwork.com', MS.dom.isin(['fcbb.com', 'sunbeltnetwork.com'])),
           ('other brokers', ~MS.dom.isin(['fcbb.com', 'sunbeltnetwork.com']))]
for j, (lab, m) in enumerate(SUBSETS):
    S = MS[m.values]
    b, _, _ = fit_bin(S); bs = cluster_boot(S, lambda X: fit_bin(X)[0][1:3], B_ROB, SEED + 20 + j)
    add_rob('binary, subset: ' + lab, 'Main Street', 'ln scale per unit', b[1:3], bs.std(0, ddof=1), int(S.in_sup.sum()))
log('subsets done')
ROBT = pd.DataFrame(ROB)
ROBT['size_p'] = [pval(a, b) for a, b in zip(ROBT['size'], ROBT.size_se)]
ROBT['em_p'] = [pval(a, b) for a, b in zip(ROBT.em, ROBT.em_se)]
ROBT.to_csv(OUT + '/robustness.csv', index=False, float_format='%.4f')
ms_rows = ROBT[(ROBT.panel == 'Main Street') & ROBT.role.isin(['main', 'robustness'])]           # the decision rule's variants
sens_rows = ROBT[ROBT.role == 'sensitivity (centring)']
sign_size = bool((ms_rows['size'] < 0).all()); sign_em = bool((ms_rows.em > 0).all())
sign_size_sens = bool((sens_rows['size'] < 0).all()); sign_em_sens = bool((sens_rows.em > 0).all())

# functional forms (Main Street, in support)
FORMS = {}
for lab, terms in [('size only', ('size',)), ('size + |z.em| (shipped form)', ('size', 'em')), ('size + max(|z.em|-1, 0)', ('size', 'hinge')),
                   ('size + |z.em| + max(|z.em|-1, 0)', ('size', 'em', 'hinge')), ('size + z.em<0 and z.em>0 slopes', ('size', 'em_lo', 'em_hi')),
                   ('size + |z.em|^2', ('size', 'em2'))]:
    b, L, nt = fit_bin(MS, terms=terms)
    FORMS[lab] = dict(loglik=L, coefficients=dict(zip(terms, b[1:nt])))
log('forms done')

# temporal hold-out: the gradients fitted on one half score the other half; the test half keeps its own location (ask premium) and
# base rate, so what is scored is only the gradients' out-of-sample value against a constant probability
def holdout(Fit, Test, seed):
    bF, _, _ = fit_bin(Fit)
    Tin = Test[Test.in_sup]; yT = inside(centre(Tin))
    XT, _, _ = design(Tin); offF = XT[:, 1:] @ bF[1:]                     # size, |z.em| and industry terms from the fit half
    XT0, _, _ = design(Tin, ind=False); off0 = XT0[:, 1:] @ bF[1:3]        # size and |z.em| only
    one = np.ones((len(Tin), 1))

    def lls(y, off):
        a, _ = scale_mle(one, y, offset=off); p = np.clip(G(np.exp(a[0] + off)), 1e-12, 1 - 1e-12)
        return np.log(p) * y + np.log(1 - p) * (1 - y), p
    l_c, _ = lls(yT, np.zeros(len(Tin))); l_f, _ = lls(yT, offF); l_0, p0 = lls(yT, off0)
    rng = np.random.default_rng(seed); n = len(Tin)
    gb = [];
    for _ in range(500):
        ii = rng.integers(0, n, n); gb.append([np.mean(l_f[ii] - l_c[ii]), np.mean(l_0[ii] - l_c[ii])])
    gb = np.array(gb)
    q = pd.qcut(p0, 5, labels=False, duplicates='drop')
    cal = []
    for k in sorted(set(q)):
        nk = int((q == k).sum()); pr = float(p0[q == k].mean()); ob = float(yT[q == k].mean()); se_k = math.sqrt(pr * (1 - pr) / nk)
        cal.append(dict(quintile=int(k), n=nk, predicted=pr, observed=ob, se=se_k, z=(ob - pr) / se_k))
    return dict(n_fit=int(Fit.in_sup.sum()), n_test=n, fit=dict(b_size=bF[1], b_em=bF[2]), base_rate_test=float(yT.mean()),
                gain_per_listing_size_em=float(np.mean(l_0 - l_c)), gain_se_size_em=float(gb[:, 1].std(ddof=1)),
                gain_per_listing_with_industry=float(np.mean(l_f - l_c)), gain_se_with_industry=float(gb[:, 0].std(ddof=1)),
                calibration_quintiles_size_em=cal, quintiles_off_by_2se=int(sum(abs(c_['z']) >= 1.96 for c_ in cal)),
                max_abs_z=float(max(abs(c_['z']) for c_ in cal)))


E_, L_ = MS[MS.first_snap <= first_med], MS[MS.first_snap > first_med]
HOLD = dict(split_first_seen=first_med, early_to_late=holdout(E_, L_, SEED + 30), late_to_early=holdout(L_, E_, SEED + 31),
            note='gain = mean log-likelihood per test listing over a constant probability, both with the base rate refitted on the test half; '
                 'SE: listing bootstrap of the test half')
log('hold-out gain per listing (size+em): early->late %.4f (%.4f), late->early %.4f (%.4f)' % (HOLD['early_to_late']['gain_per_listing_size_em'],
    HOLD['early_to_late']['gain_se_size_em'], HOLD['late_to_early']['gain_per_listing_size_em'], HOLD['late_to_early']['gain_se_size_em']))

# ------------------------------------------------------------------------------------------------------------------
# 7. industry shifts (EB) and extrapolation
# ------------------------------------------------------------------------------------------------------------------
g_hat = np.array([MAIN['industry'][k] for k in IK]); g_se = np.array([MAIN['industry_se'][k] for k in IK])
n_k = np.array([int((MS.in_sup & (MS.ind == k)).sum()) for k in IK])
w_ = 1 / g_se ** 2
Q = float(np.sum(w_ * g_hat ** 2)); dfQ = len(IK); pQ = float(stats.chi2.sf(Q, dfQ))
tau2_ind = max(0.0, (Q - dfQ) / (np.sum(w_) - np.sum(w_ ** 2) / np.sum(w_)))
shr = g_hat * tau2_ind / (tau2_ind + g_se ** 2)
INDT = pd.DataFrame({'industry': IK, 'n_in_support': n_k, 'shift_ln_scale': g_hat, 'se': g_se, 'shrunk': shr})
INDT.to_csv(OUT + '/industry.csv', index=False, float_format='%.4f')
research_shift = json.load(open(R_REBASE))['industry_shift_shrunk'] if os.path.exists(R_REBASE) else {}
IND_RES = dict(Q=Q, df=dfQ, p=pQ, tau2_DL=tau2_ind, shrunk=dict(zip(IK, shr)), raw=dict(zip(IK, g_hat)), se=dict(zip(IK, g_se)), n=dict(zip(IK, n_k.tolist())),
               research_shift_abs_resid_units=research_shift,
               note='research shifts are additive in |r| (mean |r| about 0.45); these are in ln scale. Reference = unclassified listings.')


EXT_KEY = '1-3x, margin inside support'                      # the decision's bucket: the listings conf() still labels by p


def fit_ext(S, b_in):
    """penalty in ln scale for listings past a support edge, with the in-support fit as offset. EXT_KEY is the set conf() still labels
    by p (the label rule takes the margin-past-support and past-3x listings), so the decision reads that bucket; the others are reported"""
    c = centre(S, ref=S[S.in_sup]); y = inside(c)
    X, _, _ = design(S); off = X @ b_in
    out = {}
    for lab, m in [('1-1.5x', (S.xmax > 0) & (S.xmax <= 1.5)), ('1.5-3x', (S.xmax > 1.5) & (S.xmax <= 3)), ('>3x', S.xmax > 3),
                   ('1-3x pooled', (S.xmax > 0) & (S.xmax <= 3)), (EXT_KEY, (S.xmax > 0) & (S.xmax <= 3) & ~S.m_out)]:
        m = m.values
        if m.sum() < 5:
            out[lab] = np.nan; continue
        b, _ = scale_mle(np.ones((int(m.sum()), 1)), y[m], offset=off[m])
        out[lab] = float(b[0])
    return out


EXT = fit_ext(MS, bm)
ext_boot = cluster_boot(MS, lambda S: list(fit_ext(S, fit_bin(S)[0]).values()), B_ROB, SEED + 40)
ext_se = dict(zip(EXT.keys(), np.nanstd(ext_boot, axis=0, ddof=1)))
Out_ = MS[~MS.in_sup].copy(); Out_['c'] = centre(Out_, ref=MS[MS.in_sup]); Out_['y'] = inside(Out_.c)
Out_['bucket'] = pd.cut(Out_.xmax, [0, 1.5, 3, 1e9], labels=['1-1.5x', '1.5-3x', '>3x'])
EXTT = Out_.groupby(['bucket', 'xdims'], observed=True).agg(n=('y', 'size'), within25=('y', 'mean'), median_centred_r=('c', 'median')).reset_index()
EXTT.to_csv(OUT + '/extrapolation.csv', index=False, float_format='%.4f')
EXT_RES = dict(penalty_ln_scale=EXT, se=ext_se, n={k: int(v) for k, v in [('1-1.5x', ((MS.xmax > 0) & (MS.xmax <= 1.5)).sum()), ('1.5-3x', ((MS.xmax > 1.5) & (MS.xmax <= 3)).sum()),
                                                                         ('>3x', (MS.xmax > 3).sum()), ('1-3x pooled', ((MS.xmax > 0) & (MS.xmax <= 3)).sum()),
                                                                         (EXT_KEY, ((MS.xmax > 0) & (MS.xmax <= 3) & ~MS.m_out).sum())]},
               within25_in_support=MAIN['within25'],
               by_bucket_and_dimension=EXTT.to_dict(orient='records'),
               note='>3x is dominated by revenue fields in the wrong units (margin and revenue both past their edges, centred r about -6.6): not measurable')
# evidence for the label rule (Low, 'outside the fitted data', past 3x or with the margin outside support): the within-25 share of
# Main-Street listings by where they sit, under the shipped centring and round 2's, against what the in-support fit of the same
# centring predicts for the same listings (its industry, size and |z.em| terms; a listing past support gets no extra term)
FIT_B = {CENTRE_MAIN: bm, 'ind+size': fit_bin(MS, mode='ind+size')[0]}
RULE_GROUPS = [('in support', MS.in_sup),
               ('size or revenue past support only, x <= 3 (no label change)', ~MS.in_sup & ~MS.m_out & (MS.xmax <= EXTRAP_X)),
               ('margin alone past support, x <= 1.5', (MS.xdims == 'margin') & (MS.xmax <= 1.5)),
               ('margin past support, x <= 3', MS.m_out & (MS.xmax <= EXTRAP_X)),
               ('margin past support, all', MS.m_out),
               ('any dimension past 3x', MS.xmax > EXTRAP_X)]
RULE_ROWS = []
for mode, mlab in [(CENTRE_MAIN, 'shipped'), ('ind+size', 'round 2 (industry + ln SDE)')]:
    cc = centre(MS, ref=MS[MS.in_sup], mode=mode); yy = inside(cc)
    Xa, _, _ = design(MS); pred = np.asarray(G(np.exp(Xa @ FIT_B[mode])))
    for glab, gm in RULE_GROUPS:
        gm = gm.values
        RULE_ROWS.append(dict(centring=mlab, group=glab, n=int(gm.sum()), within25=float(yy[gm].mean()) if gm.any() else np.nan,
                              se=float(math.sqrt(max(yy[gm].mean() * (1 - yy[gm].mean()), 1e-12) / gm.sum())) if gm.any() else np.nan,
                              predicted_in_support_fit=float(pred[gm].mean()) if gm.any() else np.nan,
                              median_centred_r=float(np.median(cc[gm])) if gm.any() else np.nan,
                              mean_abs_zem=float(MS.azem.values[gm].mean()) if gm.any() else np.nan))
RULET = pd.DataFrame(RULE_ROWS)
RULET.to_csv(OUT + '/extrapolation_rule.csv', index=False, float_format='%.4f')
_r = lambda c_, g_: RULET[(RULET.centring == c_) & (RULET.group == g_)].iloc[0]
EXT_RES['label_rule_evidence'] = dict(
    rows=RULET.to_dict(orient='records'),
    note=('Main-Street listings with the margin past MODELS.value.support.margin land within 25%% of the centred value in %.2f of cases '
          '(n = %d with the margin alone 1-1.5x past the edge, round 2\'s centring; %.2f under the shipped centring) against %.2f that the in-support fit predicts '
          'for the same listings; all margin-past-support listings %.2f (n = %d). Size or revenue past support alone (x <= 3) is no worse than '
          'in support (%.2f, n = %d, against %.2f). Past 3x the listings are mostly revenue fields in the wrong units.' % (
              _r('round 2 (industry + ln SDE)', 'margin alone past support, x <= 1.5').within25, _r('round 2 (industry + ln SDE)', 'margin alone past support, x <= 1.5').n,
              _r('shipped', 'margin alone past support, x <= 1.5').within25, _r('shipped', 'margin alone past support, x <= 1.5').predicted_in_support_fit,
              _r('shipped', 'margin past support, all').within25, _r('shipped', 'margin past support, all').n,
              _r('shipped', 'size or revenue past support only, x <= 3 (no label change)').within25,
              _r('shipped', 'size or revenue past support only, x <= 3 (no label change)').n, _r('shipped', 'in support').within25)))
log('industry Q %.1f p %.3f; extrapolation 1-3x pooled %.3f (%.3f), margin inside %.3f (%.3f); margin past support within-25 %.3f (n %d) vs predicted %.3f' % (
    Q, pQ, EXT['1-3x pooled'], ext_se['1-3x pooled'], EXT[EXT_KEY], ext_se[EXT_KEY], _r('shipped', 'margin alone past support, x <= 1.5').within25,
    _r('shipped', 'margin alone past support, x <= 1.5').n, _r('shipped', 'margin alone past support, x <= 1.5').predicted_in_support_fit))

# ------------------------------------------------------------------------------------------------------------------
# 6b. checks: Lie & Lie, attenuation, Empire Flippers bridge
# ------------------------------------------------------------------------------------------------------------------
lie_txt = subprocess.run(['pdftotext', '-layout', LIE_PDF, '-'], capture_output=True, text=True, timeout=300).stdout
lie_ok = all(s in lie_txt for s in ['0.178', '0.286', '0.389', '1,692', '1,942', '1,127', 'Fraction within 15%'])
mu_a = math.log(LIE_ASSETS_Q[1]); sd_a = (math.log(LIE_ASSETS_Q[2]) - math.log(LIE_ASSETS_Q[0])) / (2 * stats.norm.ppf(.75))


def cls_centre(a, b):
    pa = stats.norm.cdf((math.log(a) - mu_a) / sd_a) if a > 0 else 0.0
    pb = stats.norm.cdf((math.log(b) - mu_a) / sd_a) if math.isfinite(b) else 1.0
    return mu_a + sd_a * stats.norm.ppf((pa + pb) / 2)


def lie_scale(P_, m_):
    return optimize.brentq(lambda s: float(Fan((0.15 - m_) / s) - Fan((-0.15 - m_) / s)) - P_, 0.01, 50)


xl = np.array([cls_centre(a, b) for _, a, b, _, _, _ in LIE]); lsg = []; wl = []
for name, a, b, P_, n_, m_ in LIE:
    s = lie_scale(P_, m_); s1 = lie_scale(P_ + math.sqrt(P_ * (1 - P_) / n_), m_)
    lsg.append(math.log(s)); wl.append(1 / (math.log(s1) - math.log(s)) ** 2)
Xl = np.c_[np.ones(3), xl]; Wl = np.diag(wl); covl = np.linalg.inv(Xl.T @ Wl @ Xl); bl = covl @ Xl.T @ Wl @ np.array(lsg)
lie_el, lie_se = float(bl[1]), float(math.sqrt(covl[1, 1]))
LIE_RES = dict(table3_confirmed_in_pdf=lie_ok, class_centres_assets_musd=np.exp(xl).tolist(), ln_scale=lsg, elasticity=lie_el, elasticity_se=lie_se,
               main_street_b_size=bm[1], main_street_se=se_m[1], difference=bm[1] - lie_el, z=(bm[1] - lie_el) / math.hypot(se_m[1], lie_se),
               note='scale of ln(estimate/actual) under the BIZCOMPS fan shape with each class median error as location; class centres from a '
                    'lognormal through Table 1 book assets p25/p50/p75; public firms, EV/EBITDA comparables: direction check, not pooled')
TESTS['Lie & Lie Table 3 figures found in the PDF text layer'] = lie_ok
# attenuation: homoscedastic ask noise of sd n in ln units, given the Main-Street ask scale
s_ask_typ = float(np.exp(bm[0]))
fan_sd_eq = (FAN_Y[FAN_P.index(0.75)] - FAN_Y[FAN_P.index(0.25)]) / (2 * stats.norm.ppf(.75))
ATT = {}
for nsd in (0.10, 0.15, 0.215):
    tot = s_ask_typ * fan_sd_eq; share = max(0.0, 1 - (nsd / tot) ** 2)
    ATT['%.3f' % nsd] = dict(sale_share_of_variance=share, b_size_sale=bm[1] / share if share > 0 else None, b_em_sale=bm[2] / share if share > 0 else None)
ATT['note'] = ('if c = sale residual + independent ask noise of constant sd, the ask-measured ln-scale gradients understate the sale-price ones by the '
               "sale share of variance at the panel's typical scale; 0.215 = sd of ln(sale/ask) among Empire Flippers deals")
# Empire Flippers bridge: same deals, ask vs reconstructed sale
EF['in_sup'] = EF.xmax == 0
EF['lsde_c'] = np.log(np.clip(EF.cf, SUP['ern']['p1'], SUP['ern']['p99']) / REF_SDE); EF['azem'] = EF.zem.abs()
EF['dom'] = EF.listing_number.astype(str); EF['ind'] = 'ecom'
EFin = EF[EF.in_sup].copy()


def ef_fit(S, col, loc):
    """binary within-25 scale model on one price column; centring on ln SDE (loc False, round 2) or also on signed z.em and
    z.em^2 (loc True, the shipped rule); one industry (ecom)"""
    S = S.assign(r=np.log(S[col] / S.V))
    X = np.column_stack([np.ones(len(S)), S.lsde_c.values] + ([S.zem.values, S.zem.values ** 2] if loc else [])); a = l1fit(X, S.r.values)
    c = S.r.values - X @ a; y = inside(c)
    Xd = np.column_stack([np.ones(len(S)), S.lsde_c.values, S.azem.values])
    return scale_mle(Xd, y)[0], float(y.mean())


def ef_slope(S, col):
    """location trend: OLS slope on signed z.em of ln(price / V) centred on ln SDE (median regression)"""
    r_ = np.log(S[col] / S.V).values; X = np.column_stack([np.ones(len(S)), S.lsde_c.values]); c = r_ - X @ l1fit(X, r_)
    return float(np.polyfit(S.zem.values, c, 1)[0])


def ef_both(S):
    o = []
    for loc in (False, True):
        ba, _ = ef_fit(S, 'listing_price', loc); bs_, _ = ef_fit(S, 'sale_price_mean', loc)
        o += list(ba[1:3]) + list(bs_[1:3]) + list(bs_[1:3] - ba[1:3])
    return np.r_[o, ef_slope(S, 'listing_price'), ef_slope(S, 'sale_price_mean')]


ef_est = ef_both(EFin); rng_ef = np.random.default_rng(SEED + 50)
ef_bs = np.array([ef_both(EFin.iloc[rng_ef.integers(0, len(EFin), len(EFin))]) for _ in range(B_ROB)]); ef_se = ef_bs.std(0, ddof=1)


def ef_block(o, loc, lab):
    return dict(centring=lab,
                ask=dict(b_size=ef_est[o], b_size_se=ef_se[o], b_em=ef_est[o + 1], b_em_se=ef_se[o + 1], within25=ef_fit(EFin, 'listing_price', loc)[1]),
                sale=dict(b_size=ef_est[o + 2], b_size_se=ef_se[o + 2], b_em=ef_est[o + 3], b_em_se=ef_se[o + 3], within25=ef_fit(EFin, 'sale_price_mean', loc)[1]),
                sale_minus_ask=dict(b_size=ef_est[o + 4], b_size_se=ef_se[o + 4], b_em=ef_est[o + 5], b_em_se=ef_se[o + 5]))


EF_RES = dict(n_deals_in_support=int(len(EFin)), years=[int(EFin.sold_year.min()), int(EFin.sold_year.max())],
              location_inclusive=ef_block(0, False, 'ln SDE only (round 2)'),
              location_adjusted=ef_block(6, True, 'ln SDE, signed z.em and z.em^2 (the shipped rule)'),
              location_slope_on_signed_zem=dict(ask=ef_est[12], ask_se=ef_se[12], sale=ef_est[13], sale_se=ef_se[13],
                                                note='OLS slope of ln(price / V), centred on ln SDE, on signed z.em: sale prices share the asks\' margin trend'),
              sd_ln_sale_over_ask=float(np.std(np.log(EFin.sale_price_mean / EFin.listing_price), ddof=1)),
              note='online businesses (an analog, one industry): the same deals\' asks and reconstructed sale prices around the console value (ecom cell); '
                   'deal bootstrap. The levels matter as much as the differences: the size gradient is positive on these deals (the opposite sign '
                   'to Main Street), and once the location is adjusted the |z.em| scale gradient is near zero for asks and sales alike, i.e. on '
                   'these deals the margin effect is location, not spread')
log('Lie & Lie elasticity %.3f (%.3f); EF location-adjusted: ask size %+.3f em %+.3f, sale size %+.3f em %+.3f; location slope ask %.3f sale %.3f' % (
    lie_el, lie_se, ef_est[6], ef_est[7], ef_est[8], ef_est[9], ef_est[12], ef_est[13]))

# ------------------------------------------------------------------------------------------------------------------
# 8. depth: tau^2 of the 6-digit effects (method of moments, as fit6 industry_tailwind_and_comps.py)
# ------------------------------------------------------------------------------------------------------------------
E6, E2 = MV['industry_effects_naics6'], MV['industry_effects']
keys = sorted(c for c in E6 if c[:2] in E2 and c in N6)
n6v = np.array([N6[c] for c in keys], float); dev = np.array([E6[c] - E2[c[:2]] for c in keys])
raw = dev * (n6v + K_N6) / n6v


def mom(nn, rr):
    X = np.c_[np.ones_like(nn), 1 / nn]; t = np.linalg.lstsq(X, rr ** 2, rcond=None)[0]; return float(t[0]), float(t[1])


tau2_e, s2_e = mom(n6v, raw)
rng_c = np.random.default_rng(SEED + 60)
tb = []
for _ in range(2000):
    ii = rng_c.integers(0, len(keys), len(keys)); tb.append(mom(n6v[ii], raw[ii])[0])
tau2_e_se = float(np.std(tb, ddof=1))
IE = MV['coefficients']['ind_eff']
TAU2 = tau2_e * IE ** 2; TAU2_SE = tau2_e_se * IE ** 2
n_thin = N_FIT - int(n6v.sum())
K_HAT = s2_e / tau2_e
# the value model shrinks with k = 25, not the moment estimate k_hat: the exact error variance of its shrunk effect is
# tau2 (k^2 + n k_hat) / (n + k)^2, against tau2 k / (n + k) = tau2 (1 - comps); the gap n (k - k_hat) / (n + k)^2 peaks at n = k
EXACT_UNIT = lambda n: (K_N6 ** 2 + n * K_HAT) / (n + K_N6) ** 2
GAP_UNIT_MAX = float(max(abs(EXACT_UNIT(n) - K_N6 / (n + K_N6)) for n in range(0, 5001)))
DEPTH = dict(tau2_effect_units=tau2_e, tau2_effect_se=tau2_e_se, s2=s2_e, k_hat=K_HAT, k_console=K_N6, ind_eff=IE, tau2_ln_price=TAU2,
             tau2_ln_price_se=TAU2_SE, cells=len(keys), deals_in_cells=int(n6v.sum()), deals_in_thin_cells=n_thin,
             comps_by_industry=COMPS_V, comps_fit6_D=COMPS_D,
             exact_vs_one_minus_comps=dict(max_gap_in_tau2_units=GAP_UNIT_MAX, at_n=K_N6,
                                           by_industry={k: dict(one_minus_comps=1 - COMPS_V[k], exact=EXACT_UNIT(N6.get(IND2NAICS6.get(k, ''), 0))) for k in INDS}),
             note='posterior variance of a business\'s industry effect = tau2 k/(n+k) = tau2 (1 - comps), comps = n/(n+k), k = k_naics6 = 25, n the '
                  'value model\'s own 6-digit cell count at naics6For(industry); an industry with no 6-digit cell in the table (saas) is priced off its '
                  '2-digit sector: n = 0, variance tau2. With k = 25 rather than k_hat the exact variance differs from tau2 (1 - comps) by at most '
                  '%.3f tau2 (n = 25). Not testable on asks: centring on the industry removes it.' % GAP_UNIT_MAX)
TESTS['depth tau^2 reproduces the research and fit6 D (0.0205 effect units, k_hat 17.9)'] = abs(tau2_e - 0.0205) < 0.0003 and abs(s2_e / tau2_e - 17.93) < 0.1
TESTS['comps: saas 0 (no 6-digit cell), every other industry n6/(n6+25) of its own cell'] = (
    COMPS_V['saas'] == 0.0 and all(abs(COMPS_V[k] - N6[N6_FOR[k]] / (N6[N6_FOR[k]] + K_N6)) < 1e-15 for k in N6_FOR))
# S_EQ: normal-equivalent spread for folding the depth variance into the scale (min max gap to exact convolution); the grid's scale
# range (0.4-2.0) covers the console's (tested once K is known)
xg, wg = hermegauss(40); wg = wg / wg.sum()
FOLD_SH = (0.4, 2.0)
FOLD_GRID = [(sh, v) for sh in np.linspace(FOLD_SH[0], FOLD_SH[1], 33) for v in np.linspace(0, TAU2, 8)]
EXACT = np.array([float(np.sum(wg * (Fan((HI - math.sqrt(v) * xg) / sh) - Fan((LO - math.sqrt(v) * xg) / sh)))) for sh, v in FOLD_GRID])


def fold_gap(s_eq):
    return float(np.max(np.abs(np.array([float(G(math.sqrt(sh * sh + v / s_eq ** 2))) for sh, v in FOLD_GRID]) - EXACT)))


S_EQ = float(optimize.minimize_scalar(fold_gap, bounds=(0.30, 0.60), method='bounded', options={'xatol': 1e-5}).x)
S_EQ = round(S_EQ, 2)
DEPTH.update(s_eq=S_EQ, fold_max_gap=fold_gap(S_EQ), fan_iqr_sd=float(fan_sd_eq))
log('depth tau2 %.5f (%.5f) ln price; S_EQ %.2f (max gap %.4f)' % (TAU2, TAU2_SE, S_EQ, DEPTH['fold_max_gap']))

# ------------------------------------------------------------------------------------------------------------------
# 9. decision rule
# ------------------------------------------------------------------------------------------------------------------
ship_em = (MAIN['p_em'] < P_SHIP) and sign_em
size_strong = (MAIN['p_size'] < P_SHIP) and sign_size
ship_ind = pQ < P_SHIP
p_ext = pval(EXT[EXT_KEY], ext_se[EXT_KEY]); p_ext_pooled = pval(EXT['1-3x pooled'], ext_se['1-3x pooled'])
ship_ext = (p_ext < P_SHIP) and EXT[EXT_KEY] > 0
P_SIZE_SPECS = {'shipped centring': MAIN['p_size'], **{sv['centring']: sv['p_size'] for sv in SENS}, 'round 2 (its own bootstrap)': ROUND2['p_size']}
size_straddles = min(P_SIZE_SPECS.values()) < P_SHIP <= max(P_SIZE_SPECS.values())
DECISION = dict(size=dict(ship=True, strong=size_strong, p=MAIN['p_size'], sign_stable=sign_size, p_by_specification=P_SIZE_SPECS,
                          straddles_rule=size_straddles,
                          reason='ships in any case (the analyst\'s fallback); ' + ('passes on the shipped centring' if size_strong else 'weak: fails the p < %.2f or sign test' % P_SHIP)
                                 + ('; the p-value straddles the %.2f rule across specifications (%.3f to %.3f), so "passes" is not robust' % (
                                     P_SHIP, min(P_SIZE_SPECS.values()), max(P_SIZE_SPECS.values())) if size_straddles else '')),
                margin_distance=dict(ship=ship_em, p=MAIN['p_em'], sign_stable=sign_em, sign_stable_in_sensitivities=sign_em_sens,
                                     note='scale only: the location trend in signed z.em is removed by the centring (the analyst\'s decision 1)'),
                industry=dict(ship=ship_ind, p=pQ, Q=Q, df=dfQ),
                extrapolation=dict(ship=ship_ext, p=p_ext, estimate=EXT[EXT_KEY], se=ext_se[EXT_KEY], bucket=EXT_KEY,
                                   pooled=dict(estimate=EXT['1-3x pooled'], se=ext_se['1-3x pooled'], p=p_ext_pooled),
                                   note='the decision reads the listings conf() still labels by p (size or revenue 1-3x past support, margin inside): '
                                        'the margin-past-support and past-3x listings, which drive the pooled estimate, take the label rule instead'),
                depth=dict(ship=True, reason='BIZCOMPS\'s own tau^2 (not an ask gradient)'))
log('decision:', {k: v['ship'] for k, v in DECISION.items()})

# ------------------------------------------------------------------------------------------------------------------
# 10. normalisation on a BIZCOMPS-like mix
# ------------------------------------------------------------------------------------------------------------------
def qfun(knots, lo_clip, hi_clip):
    """ln-value quantile function, probit-linear through (p, value) knots, end slopes beyond, clipped"""
    ps_ = np.array([k[0] for k in knots]); zs = stats.norm.ppf(ps_); ys = np.log([k[1] for k in knots])

    def f(z):
        z = np.asarray(z, float); y = np.interp(z, zs, ys)
        lo = z < zs[0]; hi = z > zs[-1]
        y[lo] = ys[0] + (z[lo] - zs[0]) * (ys[1] - ys[0]) / (zs[1] - zs[0])
        y[hi] = ys[-1] + (z[hi] - zs[-1]) * (ys[-1] - ys[-2]) / (zs[-1] - zs[-2])
        return np.clip(y, math.log(lo_clip), math.log(hi_clip))
    return f


Se, Sm, Sr = SUP['ern'], SUP['margin'], SUP['rev']
q_ern = qfun([(.005, Se['p0_5']), (.01, Se['p1']), (.05, Se['p5']), (.5, Se['p50']), (.95, Se['p95']), (.99, Se['p99']), (.995, Se['p99_5'])], Se['min'], Se['max'])
q_mar = qfun([(.01, Sm['p1']), (.05, Sm['p5']), (.5, Sm['p50']), (.95, Sm['p95']), (.99, Sm['p99'])], 0.002, 1.0)
NMIX = 100000
rng_m = np.random.default_rng(SEED + 70)
U1 = rng_m.standard_normal(NMIX); U2 = rng_m.standard_normal(NMIX)
cell_keys = keys + ['thin']; cell_n = np.r_[n6v, n_thin]; cell_p = cell_n / cell_n.sum()
CELL = rng_m.choice(len(cell_keys), NMIX, p=cell_p)
target_spread = math.log(Sr['p95']) - math.log(Sr['p5'])


def mix_draw(rho):
    z2 = rho * U1 + math.sqrt(1 - rho * rho) * U2
    le = q_ern(U1); lm = q_mar(z2); lr = le - lm
    return le, lm, lr


def rev_spread(rho):
    _, _, lr = mix_draw(rho); return float(np.quantile(lr, .95) - np.quantile(lr, .05))


RHO = float(optimize.brentq(lambda r_: rev_spread(r_) - target_spread, -0.9, 0.9, xtol=1e-6))
le, lm, lr = mix_draw(RHO)
SDm = FITTED['sde_margin']
v_m_unit = np.where(np.array(cell_keys, dtype=object)[CELL] == 'thin', 1.0, K_N6 / (cell_n[CELL] + K_N6))   # depth variance / tau2
ind_of_cell = {N6_FOR[k]: k for k in N6_FOR}
mix_ind = np.array([ind_of_cell.get(cell_keys[c], 'other') for c in CELL], dtype=object)
MIXCHK = dict(rho=RHO, rev_quantiles_mix={'p1': float(np.exp(np.quantile(lr, .01))), 'p5': float(np.exp(np.quantile(lr, .05))), 'p50': float(np.exp(np.quantile(lr, .5))),
                                          'p95': float(np.exp(np.quantile(lr, .95))), 'p99': float(np.exp(np.quantile(lr, .99)))},
              rev_quantiles_stored={k: Sr[k] for k in ['p1', 'p5', 'p50', 'p95', 'p99']}, mean_depth_var_over_tau2=float(np.mean(v_m_unit)))
pd.DataFrame([dict(q=k, mix=MIXCHK['rev_quantiles_mix'][k], stored=MIXCHK['rev_quantiles_stored'][k]) for k in ['p1', 'p5', 'p50', 'p95', 'p99']]).to_csv(
    OUT + '/mix_check.csv', index=False, float_format='%.1f')


def lnscale_terms(b_size, b_em, lsde, zem_abs, ind=None, xmax=None, ind_shift=None, ext_pen=None):
    t = b_size * lsde + b_em * zem_abs
    if ind_shift is not None and ind is not None:
        t = t + np.array([ind_shift.get(k, 0.0) for k in ind])
    if ext_pen is not None and xmax is not None:
        t = t + np.where(xmax > 3, ext_pen[2], np.where(xmax > 1.5, ext_pen[1], np.where(xmax > 0, ext_pen[0], 0.0)))
    return t


def sigma_of(K, terms, vdepth, s_eq=S_EQ):
    sh = K * np.exp(terms); return np.sqrt(sh * sh + vdepth / s_eq ** 2)


def make_mix(le_, lm_):
    """one BIZCOMPS-like mix: ln SDE and ln margin draws -> the console's size term, |z.em|, extrapolation, depth, industry"""
    e_, m_ = np.exp(le_), np.exp(lm_); r_ = e_ / m_
    typ = np.exp(SDm['ln_at_ref']['other'] + SDm['slope'] * (np.clip(le_, *SDm['sde_range']) - math.log(SDm['ref_sde'])))
    x_ = np.zeros(len(le_))
    for v_, s2 in [(e_, Se), (r_, Sr), (m_, Sm)]:
        x_ = np.maximum(x_, np.where(v_ > s2['p99'], np.round(v_ / s2['p99'], 1), np.where(v_ < s2['p1'], np.round(s2['p1'] / v_, 1), 0)))
    return dict(lsde=np.log(np.clip(e_, Se['p1'], Se['p99']) / REF_SDE), zem=np.abs(np.clip(np.log(np.maximum(m_, 1e-4) / typ) / SD_EM, -3.2, 3.2)),
                xmax=x_, ind=mix_ind, vunit=v_m_unit, ern=e_, rev=r_, margin=m_)


def solve_K(b_size, b_em, tau2=None, level=LEVEL, mix=None, ind_shift=None, ext_pen=None):
    M = MIX if mix is None else mix; tau2 = TAU2 if tau2 is None else tau2
    t = lnscale_terms(b_size, b_em, M['lsde'], M['zem'], M['ind'], M['xmax'], ind_shift, ext_pen); vd = tau2 * M['vunit']
    return float(optimize.brentq(lambda K: float(np.mean(G(sigma_of(K, t, vd)))) - level, 0.05, 5.0, xtol=1e-10))


def mix_mean_p(K, b_size, b_em, mix=None, ind_shift=None, ext_pen=None):
    M = MIX if mix is None else mix
    t = lnscale_terms(b_size, b_em, M['lsde'], M['zem'], M['ind'], M['xmax'], ind_shift, ext_pen)
    return float(np.mean(G(sigma_of(K, t, TAU2 * M['vunit']))))


MIX = make_mix(le, lm)
MIXCHK['mean_abs_zem'] = float(np.mean(MIX['zem'])); MIXCHK['share_outside_support'] = float(np.mean(MIX['xmax'] > 0))
SH_IND = {k: float(v) for k, v in zip(IK, shr)} if ship_ind else None
EXT_PEN = [EXT[EXT_KEY]] * 3 if ship_ext else None      # never used: conf() has no penalty term (asserted below)
B_SIZE = float(bm[1]); B_EM = float(bm[2]) if ship_em else 0.0
K = solve_K(B_SIZE, B_EM, ind_shift=SH_IND, ext_pen=EXT_PEN)
# SE of K: gradients (bootstrap), tau2, level, mix assumptions
Kb = np.array([solve_K(b[1], b[2] if ship_em else 0.0, ind_shift=SH_IND, ext_pen=EXT_PEN) for b in boot])
K_se_grad = float(Kb.std(ddof=1))
K_se_tau = abs(solve_K(B_SIZE, B_EM, tau2=TAU2 + TAU2_SE, ind_shift=SH_IND, ext_pen=EXT_PEN)
               - solve_K(B_SIZE, B_EM, tau2=max(TAU2 - TAU2_SE, 0.0), ind_shift=SH_IND, ext_pen=EXT_PEN)) / 2
lev_se = math.sqrt(LEVEL * (1 - LEVEL) / N_FIT)
K_se_lev = abs(solve_K(B_SIZE, B_EM, level=LEVEL + lev_se, ind_shift=SH_IND, ext_pen=EXT_PEN)
               - solve_K(B_SIZE, B_EM, level=LEVEL - lev_se, ind_shift=SH_IND, ext_pen=EXT_PEN)) / 2
# mix variants: SDE and margin independent; z.em against the deal industry's own typMargin where its cell maps to a console industry
le0, lm0, _ = mix_draw(0.0)
K_rho0 = solve_K(B_SIZE, B_EM, mix=make_mix(le0, lm0), ind_shift=SH_IND, ext_pen=EXT_PEN)
lvl = np.array([SDm['ln_at_ref'].get(k, SDm['ln_at_ref']['other']) for k in mix_ind])
typ_ind = np.exp(lvl + SDm['slope'] * (np.clip(le, *SDm['sde_range']) - math.log(SDm['ref_sde'])))
MIX_TI = dict(MIX, zem=np.abs(np.clip(np.log(np.maximum(MIX['margin'], 1e-4) / typ_ind) / SD_EM, -3.2, 3.2)))
K_typind = solve_K(B_SIZE, B_EM, mix=MIX_TI, ind_shift=SH_IND, ext_pen=EXT_PEN)
K_se_mix = max(abs(K_rho0 - K), abs(K_typind - K))
K_se = math.sqrt(K_se_grad ** 2 + K_se_tau ** 2 + K_se_lev ** 2 + K_se_mix ** 2)
# the research's rule for comparison: divide by the mix's mean scale (not mean probability)
mean_scale_K = float(1 / np.mean(np.exp(lnscale_terms(B_SIZE, B_EM, MIX['lsde'], MIX['zem']))))
NORM = dict(K=K, K_se=K_se, se_parts=dict(gradients=K_se_grad, tau2=K_se_tau, level=K_se_lev, mix=K_se_mix), K_independent_sde_margin=K_rho0,
            K_industry_typmargin=K_typind, K_mean_scale_rule=mean_scale_K,
            p_mean_scale_rule=mix_mean_p(mean_scale_K, B_SIZE, B_EM, ind_shift=SH_IND, ext_pen=EXT_PEN),
            p_reference=G_c(K), mix_mean_p=mix_mean_p(K, B_SIZE, B_EM, ind_shift=SH_IND, ext_pen=EXT_PEN), mix=MIXCHK)
NORM['p_reference_se'] = abs(G_c(K + K_se) - G_c(K - K_se)) / 2
# sensitivities of the centring: their own gradients give their own K and P at the reference
for sv in SENS:
    sv['K'] = solve_K(sv['b_size'], sv['b_em'], ind_shift=SH_IND, ext_pen=EXT_PEN); sv['p_reference'] = G_c(sv['K'])
    sv['mix_mean_p'] = mix_mean_p(sv['K'], sv['b_size'], sv['b_em'], ind_shift=SH_IND, ext_pen=EXT_PEN)
NORM['sensitivity'] = {sv['centring']: dict(b_size=sv['b_size'], b_em=sv['b_em'], K=sv['K'], p_reference=sv['p_reference']) for sv in SENS}
# the level check: P assumes V is centred on today's prices. If the median price sits BBS_SHIFT above V (BizBuySell 2025 median sale over
# the model value of a business with the median cash flow and revenue), P(price / V in [0.80, 1.333]) is lower
BBS_SHIFT = float(bbs_ratio['other']); LSH = math.log(BBS_SHIFT)
P_SHIFT = Fan_c((HI - LSH) / K) - Fan_c((LO - LSH) / K)
_tm = lnscale_terms(B_SIZE, B_EM, MIX['lsde'], MIX['zem'], MIX['ind'], MIX['xmax'], SH_IND, EXT_PEN); _sg = sigma_of(K, _tm, TAU2 * MIX['vunit'])
MIX_SHIFT = float(np.mean(Fan((HI - LSH) / _sg) - Fan((LO - LSH) / _sg)))
NORM['level_check'] = dict(market_over_V=BBS_SHIFT, p_reference_if_shifted=P_SHIFT, mix_mean_p_if_shifted=MIX_SHIFT,
                           p_reference_centred=NORM['p_reference'], difference=NORM['p_reference'] - P_SHIFT,
                           note='ratio of medians (indicative), BizBuySell 2025 median closed sale over the model value of a business with the median '
                                'cash flow and revenue (unclassified industry): P assumes V is centred on today\'s prices; it is carried as a stated range '
                                'and as an SE component, not applied, until the value model\'s level is settled')
NORM['p_reference_se_with_level_check'] = math.hypot(NORM['p_reference_se'], NORM['p_reference'] - P_SHIFT)
NORM['p_reference_range'] = dict(level_check=[min(P_SHIFT, NORM['p_reference']), max(P_SHIFT, NORM['p_reference'])],
                                 centring_specifications=[min([NORM['p_reference']] + [sv['p_reference'] for sv in SENS]),
                                                          max([NORM['p_reference']] + [sv['p_reference'] for sv in SENS])])
NORM['ask_panel_scale_at_reference'] = float(np.exp(bm[0]))
NORM['ask_panel_scale_by_centring'] = {'shipped': float(np.exp(bm[0])), **{sv['centring']: sv['ask_scale_at_reference'] for sv in SENS}}
_bfe_scale = min(sv['ask_scale_at_reference'] for sv in SENS if 'bfe' in sv['mode'])
NORM['ask_panel_scale_note'] = ('the Main-Street ask residuals\' own scale on the fan at the same reference ($700k, typical margin, unclassified industry) '
                                'is %.3f with the shipped centring but %.3f once broker fixed effects enter the centring: between-broker ask premia are a '
                                'sizable share of ask dispersion, and that is the noise that attenuates the gradients. The ask scale is therefore no bridge '
                                'to the level of sale-price scatter; the level comes from BIZCOMPS alone (K), the asks supply only the gradients' % (
                                    np.exp(bm[0]), _bfe_scale))
TESTS['K reproduces 0.4454 on the BIZCOMPS-like mix (to 1e-6)'] = abs(NORM['mix_mean_p'] - LEVEL) < 1e-6
TESTS['each sensitivity K reproduces 0.4454 on the mix (to 1e-6)'] = all(abs(sv['mix_mean_p'] - LEVEL) < 1e-6 for sv in SENS)
log('K = %.4f (se %.4f); P at $700k, typical margin, deep cell = %.4f (%.4f if prices sit %.2fx V); rho %.3f; sensitivities K %s P %s' % (
    K, K_se, NORM['p_reference'], P_SHIFT, BBS_SHIFT, RHO, [round(sv['K'], 4) for sv in SENS], [round(sv['p_reference'], 4) for sv in SENS]))


# ------------------------------------------------------------------------------------------------------------------
# shipped function (Python port, console arithmetic)
# ------------------------------------------------------------------------------------------------------------------
assert not ship_ind and not ship_ext, 'conf() carries no industry or extrapolation term: extend the JS and its port before shipping one'
LABEL_NOTES = {'High': 'more predictable than three quarters of listed businesses',
               'Moderate': 'in the middle half of listed businesses',
               'Low': 'less predictable than three quarters of listed businesses',
               'outside': 'outside the fitted data'}


def conf_py(ern, rev, ind, zem, xmax, T, comps=None):
    """the shipped conf(s, out), console arithmetic; comps from the industry's own 6-digit cell unless given (unclassified listings)"""
    lx = math.log(min(max(ern, SUP['ern']['p1']), SUP['ern']['p99']) / T['ref_sde'])     # MODELS.value.support, as the JS reads it
    sh = T['K'] * math.exp(T['b_size'] * lx + T['b_em'] * min(abs(zem), 3.2))
    cp = comps_v(ind) if comps is None else comps
    sig = math.sqrt(sh * sh + T['tau2'] * (1 - cp) / (T['s_eq'] * T['s_eq']))
    p = G_c(sig)
    m = ern / max(rev, 1)
    outside = xmax > T['extrap_x'] or m < SUP['margin']['p1'] or m > SUP['margin']['p99']
    lab = 'Low' if outside else 'High' if p >= T['cut_high'] else 'Moderate' if p >= T['cut_moderate'] else 'Low'
    return dict(p=p, label=lab, note=T['notes']['outside' if outside else lab], sigma=sig, band80=[FQ['p10'] ** sig, FQ['p90'] ** sig])


# ------------------------------------------------------------------------------------------------------------------
# 11. labels from the listing distribution (relative standing)
# ------------------------------------------------------------------------------------------------------------------
T = dict(K=round(K, 4), b_size=round(B_SIZE, 4), b_em=round(B_EM, 4), tau2=round(TAU2, 4), s_eq=S_EQ, ref_sde=REF_SDE,
         cut_high=0.0, cut_moderate=0.0, extrap_x=EXTRAP_X, notes=LABEL_NOTES)
vbar_unit = float(np.mean(v_m_unit))
MSL = MS.copy()
MSL['comps'] = [COMPS_V[k] if k in COMPS_V else 1 - vbar_unit for k in MSL.ind]
MSL['p'] = [conf_py(e, rv, k, z, x, T, cm)['p'] for e, rv, k, z, x, cm in zip(MSL.cf, MSL.rev, MSL.ind, MSL.zem, MSL.xmax, MSL.comps)]
q25, q50, q75 = [float(np.quantile(MSL.p, q)) for q in (.25, .5, .75)]
rcut = lambda q: round(round(q / CUT_STEP) * CUT_STEP, 2)
CUT_HIGH, CUT_MOD = rcut(q75), rcut(q25)
T['cut_high'], T['cut_moderate'] = CUT_HIGH, CUT_MOD
rng_q = np.random.default_rng(SEED + 80)
qb = np.array([[np.quantile(MSL.p.values[rng_q.integers(0, len(MSL), len(MSL))], q) for q in (.25, .75)] for _ in range(500)])


def shares(p, outside, hi, mo):
    hi_ = (p >= hi) & ~outside; lo_ = (p < mo) | outside
    return dict(High=float(np.mean(hi_)), Moderate=float(np.mean(~hi_ & ~lo_)), Low=float(np.mean(lo_)))


_pv, _ov, _no = MSL.p.values, MSL.outside.values, np.zeros(len(MSL), bool)
ALT_HIGH = round(CUT_HIGH + (CUT_STEP if q75 > CUT_HIGH else -CUT_STEP), 2); ALT_MOD = round(CUT_MOD + (CUT_STEP if q25 > CUT_MOD else -CUT_STEP), 2)
LAB = dict(convention='relative standing among Main-Street broker listings: High at or above the upper quartile of p (more predictable than three '
                      'quarters of listed businesses), Low below the lower quartile, each rounded to %.2f; Low, "outside the fitted data", when '
                      'out.extrapMax > %g or the margin is outside MODELS.value.support.margin' % (CUT_STEP, EXTRAP_X),
           quartiles=dict(p25=q25, p50=q50, p75=q75, p25_se=float(qb[:, 0].std(ddof=1)), p75_se=float(qb[:, 1].std(ddof=1))),
           p10=float(np.quantile(MSL.p, .1)), p90=float(np.quantile(MSL.p, .9)), cut_high=CUT_HIGH, cut_moderate=CUT_MOD, n_listings=int(len(MSL)),
           shares_main_street_by_p=shares(_pv, _no, CUT_HIGH, CUT_MOD),
           shares_main_street_with_outside_rule=shares(_pv, _ov, CUT_HIGH, CUT_MOD),
           share_outside=float(np.mean(_ov)), n_outside=int(_ov.sum()),
           shares_in_support_only=shares(_pv[MSL.in_sup.values], _no[MSL.in_sup.values], CUT_HIGH, CUT_MOD),
           shares_at_cuts_plus_minus_step={'%+.2f' % d: shares(_pv, _ov, round(CUT_HIGH + d, 2), round(CUT_MOD + d, 2)) for d in (-CUT_STEP, CUT_STEP)},
           bootstrap_rounded_cuts_differ=dict(cut_high=float(np.mean([rcut(x) != CUT_HIGH for x in qb[:, 1]])),
                                              cut_moderate=float(np.mean([rcut(x) != CUT_MOD for x in qb[:, 0]]))),
           if_rounded_the_other_way={'cut_high %.2f' % ALT_HIGH: shares(_pv, _ov, ALT_HIGH, CUT_MOD), 'cut_moderate %.2f' % ALT_MOD: shares(_pv, _ov, CUT_HIGH, ALT_MOD)},
           classified_only_quartiles=[float(np.quantile(MSL[MSL.ind != 'other'].p, q)) for q in (.25, .5, .75)],
           note='unclassified listings take the BIZCOMPS deal-weighted depth (comps = 1 - mean posterior variance / tau2); the quartiles are of p '
                'over all Main-Street listings (the outside rule then relabels some Low). p is concentrated (interquartile range about 0.06), so '
                'rounding a quartile to 0.01 moves a share by up to about 4 points, and a 0.01 step in a cut by about 8 (round 2 rounded to 0.05)')
pd.DataFrame([dict(quantile=q, p=float(np.quantile(MSL.p, q))) for q in (.05, .1, .25, .5, .75, .9, .95)]).to_csv(OUT + '/labels.csv', index=False, float_format='%.4f')
log('labels: quartiles %.4f / %.4f / %.4f -> High >= %.2f, Moderate >= %.2f; shares with the outside rule %s' % (
    q25, q50, q75, CUT_HIGH, CUT_MOD, {k: round(v, 3) for k, v in LAB['shares_main_street_with_outside_rule'].items()}))

# ------------------------------------------------------------------------------------------------------------------
# 12. js_table, js_code, test vectors, node check
# ------------------------------------------------------------------------------------------------------------------
_gm = ((MS.xdims == 'margin') & (MS.xmax <= 1.5)).values
EXT_RES['label_rule_evidence']['shipped_p_for_margin_alone_group'] = float(MSL.p.values[_gm].mean())   # console scale, no outside rule
_mg, _mg2 = _r('shipped', 'margin alone past support, x <= 1.5'), _r('round 2 (industry + ln SDE)', 'margin alone past support, x <= 1.5')
# the band80 the JS returns (fan p10 and p90 raised to sigma) against the exact quantiles of the convolution it folds (scale x fan +
# normal depth error), over the console's range of the scale
SH_LO = T['K'] * math.exp(T['b_size'] * math.log(SUP['ern']['p99'] / REF_SDE))
SH_HI = T['K'] * math.exp(T['b_size'] * math.log(SUP['ern']['p1'] / REF_SDE) + T['b_em'] * 3.2)
TESTS['the fold grid covers the console\'s range of the scale (%.2f-%.2f inside %.1f-%.1f)' % (SH_LO, SH_HI, *FOLD_SH)] = FOLD_SH[0] <= SH_LO and SH_HI <= FOLD_SH[1]


def conv_q(sh, v, q):
    f = lambda x: float(np.sum(wg * Fan((x - math.sqrt(v) * xg) / sh))) - q
    return optimize.brentq(f, -12, 12, xtol=1e-12)


def band_gap(vunit):
    g = 0.0
    for sh in np.linspace(SH_LO, SH_HI, 9):
        v = TAU2 * vunit; sg = math.sqrt(sh * sh + v / S_EQ ** 2)
        for q, kq in ((0.1, 'p10'), (0.9, 'p90')):
            g = max(g, abs(FQ[kq] ** sg / math.exp(conv_q(sh, v, q)) - 1))
    return float(g)


BAND_BY_IND = {k: band_gap(1 - COMPS_V[k]) for k in INDS}
BAND_CHECK = dict(max_relative_gap=max(BAND_BY_IND.values()), by_industry=BAND_BY_IND, no_depth_variance=band_gap(0.0), scale_range=[SH_LO, SH_HI],
                  deep_cells_max=max(v for k, v in BAND_BY_IND.items() if COMPS_V[k] >= 0.85),
                  note='band80 = [fan p10^sigma, fan p90^sigma] against the exact 10th and 90th percentiles of price / V under the depth convolution '
                       '(scale x fan + normal industry-effect error), over the console\'s range of the scale, at each industry\'s own depth. Exact '
                       'without depth variance; the fold (s_eq) is tuned to the window probability, not the tails, so the band edges drift most where '
                       'the depth variance is largest (saas, no 6-digit cell). Display only')
TESTS['band80 is exact without depth variance, within 1% of the exact quantiles for cells with comps >= 0.85 and 3% for every industry'] = (
    BAND_CHECK['no_depth_variance'] < 1e-9 and BAND_CHECK['deep_cells_max'] < 0.01 and BAND_CHECK['max_relative_gap'] < 0.03)
SENS_T = {sv['mode']: dict(centring=sv['centring'], b_size=round(sv['b_size'], 4), b_em=round(sv['b_em'], 4), K=round(sv['K'], 4),
                           p_reference=round(sv['p_reference'], 3)) for sv in SENS}
LS = LAB['shares_main_street_with_outside_rule']
JS_TABLE = dict(
    target='P(realised price within 25% of the estimate V): price / V in [0.80, 1.333], BIZCOMPS within_25pct definition. V is the value '
           'model\'s fitted value (out.fv.point); the quality position (out.qFactor) is judgment and is not covered',
    assumes='P assumes V is centred on today\'s prices (median price / V = 1). If the median price sits %.2fx V (BizBuySell 2025 median sale over '
            'the model value of the median business) P at the reference is %.3f, not %.3f' % (BBS_SHIFT, P_SHIFT, NORM['p_reference']),
    level=LEVEL, K=T['K'], b_size=T['b_size'], b_em=T['b_em'], tau2=T['tau2'], s_eq=S_EQ, ref_sde=REF_SDE,
    cut_high=CUT_HIGH, cut_moderate=CUT_MOD, extrap_x=EXTRAP_X, notes=LABEL_NOTES,
    se=dict(K=round(K_se, 4), b_size=round(float(se_m[1]), 4), b_em=round(float(se_m[2]), 4) if ship_em else None, tau2=round(TAU2_SE, 4)),
    reference=dict(business='$700k SDE, typical margin, deep 6-digit cell', p=round(NORM['p_reference'], 3), se=round(NORM['p_reference_se'], 3),
                   prices_over_V=round(BBS_SHIFT, 3), p_if_prices_over_V=round(P_SHIFT, 3),
                   se_with_level_check=round(NORM['p_reference_se_with_level_check'], 3),
                   range_level_check=[round(x, 3) for x in NORM['p_reference_range']['level_check']],
                   range_centring=[round(x, 3) for x in NORM['p_reference_range']['centring_specifications']]),
    sensitivity=SENS_T,
    n=dict(listings=MAIN['n_in_support'], brokers=MAIN['n_brokers'], bizcomps=N_FIT, cells=len(keys)),
    form='sigma = sqrt((K exp(b_size ln(clamp(SDE, support.ern p1, p99) / ref_sde) + b_em min(|z.em|, 3.2)))^2 + tau2 (1 - comps) / s_eq^2); '
         'comps = n6 / (n6 + k_naics6) of the value model\'s 6-digit cell at naics6For(industry), 0 without one; '
         'p = Fan(ln(1/.75) / sigma) - Fan(ln .8 / sigma), Fan = the fan_quantiles CDF as FAN; band80 = [fan p10^sigma, fan p90^sigma]',
    centring='scale only: each listing\'s ln(ask / V) is centred on industry, ln SDE, signed z.em and z.em^2 (median regression) before the scale '
             'gradients are fitted, so a location trend in size or margin is not counted as inaccuracy',
    labels='relative standing among Main-Street broker listings: High at or above the upper quartile of p (more predictable than three quarters '
           'of listed businesses), Low below the lower quartile, both rounded to 0.01 (a convention); listing shares High %.2f, Moderate %.2f, '
           'Low %.2f' % (LS['High'], LS['Moderate'], LS['Low']),
    extrapolation='Low, "outside the fitted data", when out.extrapMax > %g or SDE / revenue is outside support.margin [p1, p99]: Main-Street '
                  'listings with the margin alone 1-1.5x past support land within 25%% in %.2f of cases (%.2f under round 2\'s centring; n %d), '
                  'against %.2f that the in-support fit predicts for them (the shipped p averages %.2f)' % (
                      EXTRAP_X, _mg.within25, _mg2.within25, _mg.n, _mg.predicted_in_support_fit,
                      EXT_RES['label_rule_evidence']['shipped_p_for_margin_alone_group']),
    source='level: BIZCOMPS out-of-fold (MODELS.value.within_25pct, n = 18,941); shape: MODELS.value.fan_quantiles; gradients: DealLedger broker '
           'listings (CC0, 102 daily files 2026-02-28 to 2026-10-06), Main-Street panel with parse errors, online brokers and real estate '
           'removed, binary within-25 scale model, broker-cluster bootstrap; depth: tau^2 of the 6-digit effects in MODELS.value (method of '
           'moments); K solves the mean over a BIZCOMPS-like mix = 0.4454. fit6 confidence_accuracy.py (round 3)',
    not_shipped=dict(industry_shift=('Q = %.1f on %d df, p = %.2f' % (Q, dfQ, pQ)) if not ship_ind else None,
                     extrapolation_penalty=('size or revenue 1-3x past support with the margin inside: %.2f (SE %.2f) in ln scale, p = %.2f; pooled with the '
                                            'margin cases %.2f (SE %.2f), which the label rule takes' % (EXT[EXT_KEY], ext_se[EXT_KEY], p_ext, EXT['1-3x pooled'],
                                                                                                        ext_se['1-3x pooled'])) if not ship_ext else None,
                     margin_distance=None if ship_em else 'not significant'))
JS_TABLE = rnd(JS_TABLE)
JS_LINE = 'MODELS.fitted.confidence=' + json.dumps(JS_TABLE, separators=(',', ':'), sort_keys=True) + ';'
open(OUT + '/js_line.txt', 'w').write(JS_LINE + '\n')

JS_CODE = r"""/* Confidence: the chance the realised price lands within 25% of the estimate V, BIZCOMPS's definition (price / V between
   0.80 and 1.333). V is the value model's fitted value, out.fv.point; the quality position (out.qFactor) is judgment and is
   not covered. P ASSUMES V IS CENTRED ON TODAY'S PRICES: if today's median price sits @SHIFT@x V (BizBuySell 2025 level
   check), P at the reference business is @PSHIFT@, not @PREF@ (MODELS.fitted.confidence.reference).
   Level and residual shape: BIZCOMPS out-of-fold accuracy (within_25pct 0.4454; fan_quantiles, read through FAN). Scale: K at
   $700k SDE and the typical margin, moving with size (b_size per ln SDE, SDE held at support p1..p99) and with distance from
   the typical margin (b_em per unit |z.em|) as the SPREAD of DealLedger Main-Street asks around V does once each listing is
   centred on industry, ln SDE, z.em and z.em^2: a location trend, in size or in margin, is not counted as inaccuracy.
   Depth: tau2 (1 - comps), comps = n6/(n6 + k_naics6) of the value model's own 6-digit cell, 0 without one (saas).
   Labels are relative standing among listed businesses (quartiles of p over Main-Street listings: High = more predictable
   than three quarters of them); past 3x the fitted data, or with the margin outside support, the label is Low with the note
   "outside the fitted data". band80: this business's 80% band of price / V implied by sigma (fan p10 and p90 raised to
   sigma), for the equation panel. Display only: nothing else reads it. fit/confidence_accuracy.py.
   Integration (index.html):
   - model(): replace the four lines from "const typ=Object.values(z)" to "out.confLabel = ..." with
       { const C=conf(s,out); out.conf=C.p; out.confLabel=C.label; out.confNote=C.note; out.confSigma=C.sigma; out.confBand80=C.band80; }
     (no `const conf` may stay in model(): it would shadow this function). Years in business and reporting no longer move it.
     Keep the console's own extrapolation warnings (out.extrap): the note here does not replace them.
   - eq_c: the formula text; eq_cs: print fv.point x band80 (this business's band) and the note, not V x fan p10/p90.
   - Data tab (~line 4743) and tests/model.test.js:1133 count the confidence numbers by slicing model() from "const conf=" to
     "out.conf=conf": that slice comes back empty. Count MODELS.fitted.confidence instead (K, b_size, b_em, tau2 fitted;
     s_eq an approximation; cut_high, cut_moderate a convention; extrap_x a rule).
   - tests: invariants/identities.js cats-conf (the .68/.46 labels), invariants/statics.js:258-259 (monotone in years and
     reporting: now constant in both), invariants/app.js:529 (the eq_cs sequence). */
function conf(s,out){
  const C=MODELS.fitted.confidence, MV=MODELS.value, E=MV.support.ern, M=MV.support.margin, Q=MV.fan_quantiles;
  const Z=FAN.z, Y=FAN.y, n=Z.length;
  const F=y=>{ let z;                                  /* the fan's CDF in log space, probit-linear as FAN */
    if(y<=Y[0]) z=Z[0]+(y-Y[0])*(Z[1]-Z[0])/(Y[1]-Y[0]);
    else if(y>=Y[n-1]) z=Z[n-1]+(y-Y[n-1])*(Z[n-1]-Z[n-2])/(Y[n-1]-Y[n-2]);
    else { let i=0; while(y>Y[i+1]) i++; z=Z[i]+(y-Y[i])*(Z[i+1]-Z[i])/(Y[i+1]-Y[i]); }
    return ncdf(z); };
  const lx=Math.log(Math.min(Math.max(s.ern,E.p1),E.p99)/C.ref_sde);              /* size, held at the fitted support */
  const sh=C.K*Math.exp(C.b_size*lx+C.b_em*Math.min(Math.abs(out.z.em),3.2));
  const c6=naics6For(s.ind), n6=(c6&&MV.industry_n6[c6])||0, comps=n6/(n6+MV.industry_shrinkage.k_naics6);
  const sigma=Math.sqrt(sh*sh+C.tau2*(1-comps)/(C.s_eq*C.s_eq));                    /* multiplier on the BIZCOMPS fan */
  const p=F(Math.log(1/.75)/sigma)-F(Math.log(.8)/sigma);
  const m=s.ern/Math.max(s.rev,1), outside=out.extrapMax>C.extrap_x||m<M.p1||m>M.p99;
  const label=outside?"Low":p>=C.cut_high?"High":p>=C.cut_moderate?"Moderate":"Low";
  return {p:p, label:label, note:C.notes[outside?"outside":label], sigma:sigma, band80:[Math.pow(Q.p10,sigma),Math.pow(Q.p90,sigma)]};
}""".replace('@SHIFT@', '%.2f' % BBS_SHIFT).replace('@PSHIFT@', '%.3f' % P_SHIFT).replace('@PREF@', '%.3f' % NORM['p_reference'])
INTEGRATION_LINE = ('  { const C=conf(s,out); out.conf=C.p; out.confLabel=C.label; out.confNote=C.note; out.confSigma=C.sigma; '
                    'out.confBand80=C.band80; }')
open(OUT + '/conf.js', 'w').write(JS_CODE + '\n')
TV_IN = [  # (description, ern, rev, ind, z.em, out.extrapMax)
    ('home, $700k SDE on $3.5M revenue, typical margin', 7e5, 3.5e6, 'home', 0.0, 0.0),
    ('restaurant, $150k on $1.2M, margin 0.5 sd below typical', 1.5e5, 1.2e6, 'rest', -0.5, 0.0),
    ('saas (no 6-digit cell: comps 0), $2.5M SDE (1.5x past the SDE support) on $8M, margin 1 sd above', 2.5e6, 8e6, 'saas', 1.0, 1.5),
    ('vet, $300k on $1M, margin 2 sd above', 3e5, 1e6, 'vet', 2.0, 0.0),
    ('medical, $1.45M on $5M (the framework example), margin 0.1 sd above', 1.45e6, 5e6, 'medical', 0.1, 0.0),
    ('msp, $50k on $400k, margin 1.5 sd below', 5e4, 4e5, 'msp', -1.5, 0.0),
    ('distribution, $20M SDE on $130M, typical margin: 11.9x past support, High by p but outside the fitted data', 2e7, 1.3e8, 'dist', 0.0, 11.9),
    ('auto repair, $5.1M SDE on $20M: 3.0x past support, the rule is > 3 (not outside)', 5.1e6, 2e7, 'auto', 0.0, 3.0),
    ('fitness, $100k SDE on $110k: margin 0.91, past the margin support (outside the fitted data)', 1e5, 1.1e5, 'fit', 3.2, 1.1),
    ('landscaping, $20k SDE on $1.5M: margin 1.3%, below the margin support (outside the fitted data)', 2e4, 1.5e6, 'land', -3.2, 1.7)]
TV = []
for desc, e, rv, k, z, xm in TV_IN:
    c = conf_py(e, rv, k, z, xm, JS_TABLE)
    TV.append(dict(description=desc, s={'ern': e, 'rev': rv, 'ind': k}, out={'z': {'em': z}, 'extrapMax': xm}, comps=round(comps_v(k), 6),
                   p=round(c['p'], 6), label=c['label'], note=c['note'], sigma=round(c['sigma'], 6), band80=[round(x, 6) for x in c['band80']]))
json.dump(TV, open(OUT + '/test_vectors.json', 'w'), indent=1, sort_keys=True)      # 6 decimals as computed: not re-rounded by rnd()
TESTS['test vectors cover High, Moderate, Low, outside past 3x (a High p relabelled Low), the 3.0 boundary, margin above and below support, comps 0'] = (
    {v['label'] for v in TV} == {'High', 'Moderate', 'Low'} and TV[6]['note'] == LABEL_NOTES['outside'] and TV[6]['label'] == 'Low'
    and TV[6]['p'] >= CUT_HIGH and TV[7]['note'] != LABEL_NOTES['outside']
    and TV[8]['note'] == LABEL_NOTES['outside'] and TV[9]['note'] == LABEL_NOTES['outside'] and TV[2]['comps'] == 0.0)
# node checks: (1) the JS injected into the snapshot's model section reproduces the vectors; (2) on model() outputs it equals the Python
# port; (3) model() with the integration line in place of the old block sets out.conf etc. from conf(), and moves nothing else
CHECK_JS = r"""const fs=require('fs'); const H=require(process.argv[2]);
const tbl=fs.readFileSync(process.argv[3],'utf8').trim(), code=fs.readFileSync(process.argv[4],'utf8'), cfg=JSON.parse(fs.readFileSync(process.argv[5],'utf8'));
const inj=['function sizeAnchor(E){', tbl+'\n'+code+'\nMODELS.__conf=conf;\nfunction sizeAnchor(E){'];
const A=H.load([inj]), B=H.load([inj,[cfg.old_block,cfg.integration_line]]);
const out={tv:[],model:[],integ:[]};
for(const v of cfg.tv){ const r=A.MODELS.__conf(v.s,v.out); out.tv.push([r.p,r.label,r.note,r.sigma,r.band80]); }
for(const [k,e,rv] of cfg.model){ const I=A.IND[k], R=A.sizeRefs(e);
  const s={ind:k,rev:rv,ern:e,ask:1e6,grw:I.grw,gm:I.gm,rec:I.rec,cc:.16,ret:I.ret,plt:.40,own:R.own,mgt:R.mgt,fin:R.fin,yrs:10,buyers:I.buyers||50,st:null,franchise:false};
  const o=A.model(s), r=A.MODELS.__conf(s,o); out.model.push([o.z.em,o.extrapMax,r.p,r.label,r.note,r.sigma,r.band80]);
  const ob=B.model(s), rb=B.MODELS.__conf(s,ob);
  out.integ.push([ob.conf===rb.p&&ob.confLabel===rb.label&&ob.confNote===rb.note&&ob.confSigma===rb.sigma&&ob.confBand80[0]===rb.band80[0]&&ob.confBand80[1]===rb.band80[1],
                  ob.conf===r.p, ob.V===o.V&&ob.PC===o.PC&&ob.EVp===o.EVp&&ob.catMean===o.catMean]); }
fs.writeFileSync(process.argv[6],JSON.stringify(out)); console.log('ok');
"""
open(WORK + '/check_conf.js', 'w').write(CHECK_JS)
model_cases = []
for k in INDS:
    for e in GRID_SDE + [1.3e4, 5e6, 2e7]:
        for mfac in (1.0, 0.35, 2.6, 0.06):
            tm = math.exp(SDm['ln_at_ref'][k] + SDm['slope'] * (min(max(math.log(e), SDm['sde_range'][0]), SDm['sde_range'][1]) - math.log(SDm['ref_sde'])))
            model_cases.append([k, e, e / min(tm * mfac, 0.95)])
json.dump({'tv': TV, 'model': model_cases, 'old_block': OLD_BLOCK, 'integration_line': INTEGRATION_LINE}, open(WORK + '/check_cfg.json', 'w'))
r = subprocess.run(['node', WORK + '/check_conf.js', HARNESS, OUT + '/js_line.txt', OUT + '/conf.js', WORK + '/check_cfg.json', WORK + '/check_out.json'],
                   capture_output=True, text=True, timeout=3000)
assert r.returncode == 0, r.stderr[-3000:]
CO = json.load(open(WORK + '/check_out.json'))
tv_gap = max(max(abs(a[0] - b['p']), abs(a[3] - b['sigma']), abs(a[4][0] - b['band80'][0]), abs(a[4][1] - b['band80'][1])) for a, b in zip(CO['tv'], TV))
tv_lab = all(a[1] == b['label'] and a[2] == b['note'] for a, b in zip(CO['tv'], TV))
m_gap = 0.0; m_lab = True; m_lab_counts = {}; n_outside = 0
for (zem_js, xm_js, pj, lj, nj, sj, bj), (k, e, rv) in zip(CO['model'], model_cases):
    c = conf_py(e, rv, k, zem_js, xm_js, JS_TABLE)
    m_gap = max(m_gap, abs(c['p'] - pj), abs(c['sigma'] - sj), abs(c['band80'][0] - bj[0]), abs(c['band80'][1] - bj[1]))
    m_lab = m_lab and c['label'] == lj and c['note'] == nj
    m_lab_counts[lj] = m_lab_counts.get(lj, 0) + 1; n_outside += nj == LABEL_NOTES['outside']
integ_ok = all(a for a, _, _ in CO['integ']); integ_same = all(b for _, b, _ in CO['integ']); integ_display = all(c_ for _, _, c_ in CO['integ'])
TESTS['JS conf() in the snapshot reproduces the Python test vectors (p, sigma, band80 to 1e-6; same labels and notes)'] = tv_gap < 1e-6 and tv_lab
TESTS['JS conf() on model() outputs equals the Python port (|d| < 1e-9; same labels and notes)'] = m_gap < 1e-9 and m_lab
TESTS['model() with the integration line: out.conf, label, note, sigma and band80 come from conf(); value, P_C, EV and categories unchanged'] = (
    integ_ok and integ_same and integ_display)
JS_CHECK = dict(test_vectors_max_abs_diff=tv_gap, model_cases=len(model_cases), model_max_abs_diff=m_gap, model_labels=m_lab_counts,
                model_outside=n_outside, integration_cases=len(CO['integ']), integration_conf_from_conf=integ_ok, integration_same_p=integ_same,
                integration_display_only=integ_display, integration_line=INTEGRATION_LINE.strip(),
                note='test vectors are stored at 6 decimals, so their gap is rounding; the model() cases compare unrounded values')
log('node check: test vectors max |d| %.2e; model() cases max |d| %.2e over %d cases (%s, %d outside); integration %s' % (
    tv_gap, m_gap, len(model_cases), m_lab_counts, n_outside, 'ok' if integ_ok and integ_same and integ_display else 'FAILED'))

# ------------------------------------------------------------------------------------------------------------------
# 13. comparison with the current formula
# ------------------------------------------------------------------------------------------------------------------
cmp_rows = []
for _, rw in PEER.iterrows():
    c = conf_py(rw.ern, rw.rev, rw.ind, rw.zem, rw.xmax, JS_TABLE)
    cmp_rows.append(dict(ind=rw.ind, sde=rw.ern, rev=rw.rev, conf_now=rw.conf_now, label_now=rw.label_now, p_new=c['p'], label_new=c['label'],
                         note_new=c['note'], sigma=c['sigma'], band80_lo=c['band80'][0], band80_hi=c['band80'][1],
                         comps_now=IND_COMPS_NOW[rw.ind], comps_new=COMPS_V[rw.ind], comps_fit6_D=COMPS_D[rw.ind], extrap_max=rw.xmax))
CMP = pd.DataFrame(cmp_rows); CMP.to_csv(OUT + '/compare_current.csv', index=False, float_format='%.4f')
cls_l = [i for i, k in enumerate(H.ind) if k in INDS]
now_lab = pd.Series([FULL[j][5] for j in range(len(cls_l))], index=cls_l)
H['label_now'] = now_lab
msc = MSL[MSL.ind != 'other']
lab_new = pd.Series(['Low' if o else 'High' if p >= CUT_HIGH else 'Moderate' if p >= CUT_MOD else 'Low' for p, o in zip(msc.p, msc.outside)], index=msc.index)
_c7 = CMP[CMP.sde == 7e5]
COMPARE = dict(peer_median_by_sde=CMP.groupby('sde').agg(conf_now=('conf_now', 'mean'), p_new=('p_new', 'mean')).reset_index().to_dict(orient='records'),
               peer_median_label_shares_now=CMP.label_now.value_counts(normalize=True).to_dict(),
               peer_median_label_shares_new=CMP.label_new.value_counts(normalize=True).to_dict(),
               peer_median_at_700k=dict(p_min=float(_c7.p_new.min()), p_max=float(_c7.p_new.max()), labels=_c7.label_new.value_counts().to_dict()),
               main_street_classified_labels_now=H.loc[msc.index, 'label_now'].value_counts(normalize=True).to_dict(),
               main_street_classified_labels_new=lab_new.value_counts(normalize=True).to_dict(),
               note='current formula evaluated by model() with soft inputs at their peer medians, 10 years of history and the snapshot\'s hand-set comps; '
                    'new: the shipped conf() (comps from the value model\'s own cell, the outside rule)')

# ------------------------------------------------------------------------------------------------------------------
# 14. shipped values, not shipped, checks, sources
# ------------------------------------------------------------------------------------------------------------------
SENST = pd.DataFrame([dict(centring='shipped: industry, ln SDE, signed z.em, z.em^2', mode=CENTRE_MAIN, b_size=bm[1], b_size_se=se_m[1], p_size=MAIN['p_size'],
                           b_em=bm[2], b_em_se=se_m[2], p_em=MAIN['p_em'], ask_scale_at_reference=float(np.exp(bm[0])), K=K, p_reference=NORM['p_reference'],
                           within25=MAIN['within25'], n_broker_effects=0)] +
                     [{k: sv[k] for k in ['centring', 'mode', 'b_size', 'b_size_se', 'p_size', 'b_em', 'b_em_se', 'p_em', 'ask_scale_at_reference', 'K',
                                          'p_reference', 'within25', 'n_broker_effects']} for sv in SENS])
SENST.to_csv(OUT + '/sensitivity.csv', index=False, float_format='%.4f')
LRE = EXT_RES.pop('label_rule_evidence')
_ref7 = CMP[CMP.sde == 7e5]
SHIPPED = {
    'level': dict(value=LEVEL, se=lev_se, console=None, note='BIZCOMPS out-of-fold within_25pct (n = 18,941); the current figure is an index with no level'),
    'K': dict(value=JS_TABLE['K'], unrounded=K, se=K_se, se_parts=NORM['se_parts'], console=None, round2=ROUND2['K'],
              note='scale on the BIZCOMPS fan at $700k SDE, typical margin, no depth variance; solves the BIZCOMPS-like mix mean = 0.4454'),
    'b_size': dict(value=JS_TABLE['b_size'], unrounded=B_SIZE, se=float(se_m[1]), p=MAIN['p_size'], strong=size_strong, straddles_p_rule=size_straddles,
                   p_by_specification=P_SIZE_SPECS, console=None, round2=ROUND2['b_size'],
                   note='ln scale per ln SDE (SDE held at support p1..p99), scale only (shipped centring); the current formula has no size term (the '
                        'hand-set z.size reaches it only through mean|z|)'),
    'b_em': dict(value=JS_TABLE['b_em'], unrounded=float(bm[2]), se=float(se_m[2]), p=MAIN['p_em'], shipped=ship_em, console=None, round2=ROUND2['b_em'],
                 note='ln scale per unit |z.em| (clamped 3.2), scale only: the location trend in signed z.em is centred out first (round 2\'s %.3f '
                      'mixed it in); the current formula has .14 max(0, 1 - mean|z|/2.2) over all z' % ROUND2['b_em']),
    'tau2': dict(value=JS_TABLE['tau2'], unrounded=TAU2, se=TAU2_SE, console=None,
                 note='ln price; with comps = n6/(n6 + k_naics6) of the value model\'s own cell (0 without one) it replaces the weight .34 on comps'),
    's_eq': dict(value=S_EQ, se=None, console=None, note='fold of the depth variance into the scale; max gap to the exact convolution %.4f over scales %.1f-%.1f '
                                                        '(the console runs %.2f-%.2f)' % (DEPTH['fold_max_gap'], FOLD_SH[0], FOLD_SH[1], SH_LO, SH_HI)),
    'cut_high': dict(value=CUT_HIGH, se=LAB['quartiles']['p75_se'], unrounded=LAB['quartiles']['p75'], console=CURRENT['cut_high'], round2=ROUND2['cut_high'],
                     note='upper quartile of p across Main-Street listings, rounded to 0.01: High = more predictable than three quarters of listed businesses'),
    'cut_moderate': dict(value=CUT_MOD, se=LAB['quartiles']['p25_se'], unrounded=LAB['quartiles']['p25'], console=CURRENT['cut_moderate'],
                         round2=ROUND2['cut_moderate'], note='lower quartile, rounded to 0.01'),
    'extrap_x': dict(value=EXTRAP_X, se=None, console=None, note='a rule (the analyst\'s decision): Low, "outside the fitted data", when out.extrapMax > 3 or the '
                                                                  'margin is outside support.margin; evidence in checks.extrapolation_label_rule'),
    'reference_business': dict(value=NORM['p_reference'], se=NORM['p_reference_se'], se_with_level_check=NORM['p_reference_se_with_level_check'],
                               if_prices_over_V=dict(ratio=BBS_SHIFT, p=P_SHIFT), range_centring=NORM['p_reference_range']['centring_specifications'],
                               round2=ROUND2['p_reference'], peer_median_700k_mean=float(_ref7.p_new.mean()), console_index_700k_mean=float(_ref7.conf_now.mean()),
                               note='P at $700k SDE, typical margin, deep cell; the peer-median businesses at $700k average %.3f across the 16 industries '
                                    '(the index today %.3f)' % (_ref7.p_new.mean(), _ref7.conf_now.mean())),
    'weights_removed': dict(value=None, console=dict(comps=.34, yrs=.30, fin=.22, typ=.14, typ_scale=2.2),
                            note='replaced; years of history and reporting showed no effect in the research (n = 732 and 105 flagged listings)'),
}
NOT_SHIPPED = dict(
    centring_sensitivities=dict(decision='recorded as sensitivities (the analyst\'s decision 1): a location trend is not counted as inaccuracy',
                                rows=SENST.to_dict(orient='records')),
    industry_shifts=dict(decision=('shipped' if ship_ind else 'not shipped: no industry heterogeneity on the Main-Street panel'), **IND_RES),
    extrapolation_penalty=dict(decision=('shipped' if ship_ext else 'not shipped: for the listings conf() still labels by p (size or revenue 1-3x past '
                                         'support, margin inside) the penalty is not distinguishable from zero; the margin-past-support and past-3x '
                                         'cases take the label rule'), p=p_ext, p_pooled=p_ext_pooled, **EXT_RES),
    margin_distance=None if ship_em else dict(estimate=float(bm[2]), se=float(se_m[2])),
    research_gradients=dict(note='the research panel\'s gradients are mostly the ask-equals-revenue parse error; see robustness.csv (research panel row)',
                            research_panel=ROBT[ROBT.panel == 'research panel'].to_dict(orient='records'),
                            research_abs_regression=rep['joint_regression']),
    size_from_lie_lie=dict(elasticity=lie_el, se=lie_se, note='public firms; a direction check, not pooled into the shipped value'),
    years_and_reporting=dict(note='research: clamp(yrs/8) on |r| -0.008 (SE 0.066), n = 732; documented-financials phrase on the within-25 share -0.008 (SE 0.048), n = 105. Not re-estimated; no term.'),
    fallback_level_and_size_only=dict(K=solve_K(B_SIZE, 0.0, tau2=0.0), b_size=B_SIZE, note='the analyst\'s literal fallback (no margin, no depth term), for reference'),
)
_lt0, _lt1 = LOC_TREND['industry + ln SDE (round 2)'], LOC_TREND['shipped (+ signed z.em, z.em^2)']
_core = lambda L: [x['median_centred'] for x in L if x['n'] >= 50]
_h0, _h1 = HOLD['early_to_late'], HOLD['late_to_early']
_ef0, _ef1 = EF_RES['location_inclusive'], EF_RES['location_adjusted']
_sh = LAB['shares_main_street_with_outside_rule']; _pm = LAB['shares_at_cuts_plus_minus_step']
CHECKS.update(dict(
    research_replication=rep, level_gap_explanation=RES['level_gap']['explanation'], lie_lie=LIE_RES, attenuation=ATT, empire_flippers_bridge=EF_RES,
    temporal_holdout=HOLD, functional_forms=FORMS, location_trend=LOC_TREND,
    sign_stability=dict(size_negative_in_all_main_street_variants=sign_size, margin_positive_in_all=sign_em,
                        sensitivities_size_negative=sign_size_sens, sensitivities_margin_positive=sign_em_sens),
    model_check=dict(listings_checked=len(cls_idx), mismatches=bad), js_check=JS_CHECK, band80=BAND_CHECK, extrapolation_label_rule=LRE,
    normalisation=NORM, depth=DEPTH, labels=LAB, compare_current=COMPARE, files=FILES_META))
CHECKS['outcomes'] = {
    'research replication': 'pass: panel 5,940 listing for listing; joint regression %.4f / %.4f / %.4f vs 0.2475 / -0.0371 / 0.1601' % (rep_j[0], rep_j[1], rep_j[2]),
    'files': '%d files read; %s has no id column and contributes nothing: the data are %d files, %s to %s' % (
        FILES_META['read'], ', '.join(FILES_META['without_id']) or 'none', FILES_META['with_id'], FILES_META['first_with_id'], FILES_META['last_with_id']),
    'level gap explained': 'parse errors %.0f%% of the research panel (ask = revenue %d, ask = SDE %d, text conflicts %d); median ask/value %.2f -> %.2f without them, %.2f on Main Street; '
                           'rest = ask premium and a market above BIZCOMPS (BizBuySell 2025 median sale %.2fx the model value of the median business)' % (
                               100 * share_parse, int(H.ask_eq_rev.sum()), int(H.ask_eq_cf.sum()), int((H.text_conflict & ~H.ask_eq_rev & ~H.ask_eq_cf).sum()),
                               lev(G0)['ask_over_V'], lev(G1_)['ask_over_V'], lev(G3_)['ask_over_V'], bbs_ratio['other']),
    'location versus scale': ('round 2\'s centring (industry, ln SDE) left a location trend in signed z.em: the median centred residual runs %+.2f to %+.2f across the '
                              'bins with 50+ listings; the shipped centring (+ signed z.em, z.em^2) holds it to %+.2f to %+.2f. P describes the spread around V '
                              'assuming V is centred, so the trend is not counted as inaccuracy' % (min(_core(_lt0)), max(_core(_lt0)), min(_core(_lt1)), max(_core(_lt1)))),
    'gradients on Main Street': ('scale only (shipped): size %.4f (SE %.4f, p %.3f), margin distance %.4f (SE %.4f, p %.4f) on %d listings, %d brokers. '
                                 'Sensitivities: %s' % (bm[1], se_m[1], MAIN['p_size'], bm[2], se_m[2], MAIN['p_em'], MAIN['n_in_support'], MAIN['n_brokers'],
                                                        '; '.join('%s: %.3f (%.3f) / %.3f (%.3f), K %.3f, P_ref %.3f' % (sv['centring'], sv['b_size'], sv['b_size_se'], sv['b_em'],
                                                                                                                   sv['b_em_se'], sv['K'], sv['p_reference']) for sv in SENS))),
    'size p-value': ('p %.3f on the shipped centring; %s across the specifications (%s): %s. Size ships under the analyst\'s fallback either way' % (
        MAIN['p_size'], 'it straddles the %.2f rule' % P_SHIP if size_straddles else 'on one side of the %.2f rule' % P_SHIP,
        ', '.join('%s %.3f' % (k, v) for k, v in P_SIZE_SPECS.items()), 'weak evidence, not a firm pass' if size_straddles else 'stable')),
    'robustness (estimators, subsets)': 'on the shipped centring: size %.3f to %.3f, all negative: %s; margin %.3f to %.3f, all positive: %s; the centring sensitivities agree in sign: %s' % (
        ms_rows['size'].min(), ms_rows['size'].max(), sign_size, ms_rows.em.min(), ms_rows.em.max(), sign_em, sign_size_sens and sign_em_sens),
    'temporal hold-out': ('out-of-sample gain over a constant probability per listing: early->late %+.4f (SE %.4f), late->early %+.4f (SE %.4f)%s. '
                          'Calibration by quintile: %d of %d quintiles miss by 2 SE or more (largest |z| %.1f early->late, %.1f late->early); the predicted '
                          'quintile means span only %.2f-%.2f, so the check has little power' % (
                              _h0['gain_per_listing_size_em'], _h0['gain_se_size_em'], _h1['gain_per_listing_size_em'], _h1['gain_se_size_em'],
                              '' if min(_h0['gain_per_listing_size_em'] / _h0['gain_se_size_em'], _h1['gain_per_listing_size_em'] / _h1['gain_se_size_em']) >= 1.96
                              else ': the support is one-directional (a gain of 2 SE or more in %s only)' % (
                                  ' and '.join(lab for lab, h in (('early->late', _h0), ('late->early', _h1)) if h['gain_per_listing_size_em'] / h['gain_se_size_em'] >= 1.96) or 'neither direction'),
                              _h0['quintiles_off_by_2se'] + _h1['quintiles_off_by_2se'], len(_h0['calibration_quintiles_size_em']) + len(_h1['calibration_quintiles_size_em']),
                              _h0['max_abs_z'], _h1['max_abs_z'],
                              min(c_['predicted'] for h in (_h0, _h1) for c_ in h['calibration_quintiles_size_em']),
                              max(c_['predicted'] for h in (_h0, _h1) for c_ in h['calibration_quintiles_size_em']))),
    'Lie & Lie size gradient': 'direction agrees; public-firm elasticity %.3f (SE %.3f) is steeper than Main Street %.3f (z = %.1f)' % (lie_el, lie_se, bm[1], LIE_RES['z']),
    'ask vs sale (Empire Flippers)': ('online businesses (one industry), same deals. Round 2\'s centring: ask size %+.3f (SE %.3f), margin %+.3f (SE %.3f); sale size %+.3f (%.3f), '
                                      'margin %+.3f (%.3f). Shipped centring: ask %+.3f (%.3f) / %+.3f (%.3f); sale %+.3f (%.3f) / %+.3f (%.3f); sale minus ask %+.3f (%.3f) / '
                                      '%+.3f (%.3f). Location slope on signed z.em: ask %.3f, sale %.3f. So on these deals the size gradient is positive (the opposite sign '
                                      'to Main Street) and the margin effect is location, not spread, for asks and sales alike: the analog supports the centring rule '
                                      'but does not confirm the Main-Street gradients' % (
                                          _ef0['ask']['b_size'], _ef0['ask']['b_size_se'], _ef0['ask']['b_em'], _ef0['ask']['b_em_se'], _ef0['sale']['b_size'], _ef0['sale']['b_size_se'],
                                          _ef0['sale']['b_em'], _ef0['sale']['b_em_se'], _ef1['ask']['b_size'], _ef1['ask']['b_size_se'], _ef1['ask']['b_em'], _ef1['ask']['b_em_se'],
                                          _ef1['sale']['b_size'], _ef1['sale']['b_size_se'], _ef1['sale']['b_em'], _ef1['sale']['b_em_se'],
                                          _ef1['sale_minus_ask']['b_size'], _ef1['sale_minus_ask']['b_size_se'], _ef1['sale_minus_ask']['b_em'], _ef1['sale_minus_ask']['b_em_se'],
                                          EF_RES['location_slope_on_signed_zem']['ask'], EF_RES['location_slope_on_signed_zem']['sale'])),
    'industry shifts': ('shipped' if ship_ind else 'not shipped') + ': Q = %.1f on %d df, p = %.2f' % (Q, dfQ, pQ),
    'extrapolation penalty': ('shipped' if ship_ext else 'not shipped') + (': size or revenue 1-3x past support with the margin inside %.3f (SE %.3f), p = %.2f; '
                                                                           'pooled with the margin cases %.3f (SE %.3f), p = %.2f, which the label rule takes' % (
                                                                               EXT[EXT_KEY], ext_se[EXT_KEY], p_ext, EXT['1-3x pooled'], ext_se['1-3x pooled'], p_ext_pooled)),
    'extrapolation label rule': LRE['note'] + ' The shipped p for the margin-alone group averages %.2f.' % LRE['shipped_p_for_margin_alone_group'],
    'depth': ('comps from the value model\'s own 6-digit cell, n6/(n6+25), 0 without one (saas, %.3f in round 2 via fit6 D); the exact shrinkage variance at k = 25 '
              '(k_hat %.1f) differs from tau2 (1 - comps) by at most %.3f tau2' % (COMPS_D['saas'], K_HAT, GAP_UNIT_MAX)),
    'normalisation': 'mix mean P = %.6f vs 0.4454; mix revenue p5/p50/p95 %.0f/%.0f/%.0f vs stored %.0f/%.0f/%.0f' % (
        NORM['mix_mean_p'], MIXCHK['rev_quantiles_mix']['p5'], MIXCHK['rev_quantiles_mix']['p50'], MIXCHK['rev_quantiles_mix']['p95'], Sr['p5'], Sr['p50'], Sr['p95']),
    'reference P': ('P at $700k, typical margin, deep cell %.3f (SE %.3f); %.3f if today\'s median price sits %.2fx V (SE with that level check %.3f); %.3f to %.3f across '
                    'the centring specifications' % (NORM['p_reference'], NORM['p_reference_se'], P_SHIFT, BBS_SHIFT, NORM['p_reference_se_with_level_check'],
                                                     *NORM['p_reference_range']['centring_specifications'])),
    'ask scale (not a level bridge)': NORM['ask_panel_scale_note'],
    'JS check': ('test vectors max |d| %.1e (6-decimal rounding); %d model() outputs max |d| %.1e, labels %s, %d outside; model() with the integration line: '
                 'out.conf from conf() %s, nothing else moves %s' % (tv_gap, len(model_cases), m_gap, m_lab_counts, n_outside, integ_ok and integ_same, integ_display)),
    'band80': ('relative gap to the exact convolution quantiles over the console\'s scale range %.2f-%.2f: 0 without depth variance, at most %.4f for cells with '
               'comps >= 0.85, %.4f at worst (%s)' % (SH_LO, SH_HI, BAND_CHECK['deep_cells_max'], BAND_CHECK['max_relative_gap'],
                                                     max(BAND_BY_IND, key=BAND_BY_IND.get))),
    'labels': ('High >= %.2f, Moderate >= %.2f (Main-Street quartiles %.4f / %.4f, SE %.4f / %.4f, rounded to 0.01): listings %.0f%% / %.0f%% / %.0f%% High / Moderate / '
               'Low with the outside rule (%.1f%% outside; by p alone %.0f%% / %.0f%% / %.0f%%). Rounding: %.0f%% of bootstrap draws round the High cut to %.2f '
               '(High %.0f%%) and %.0f%% round the Moderate cut to %.2f (Low %.0f%%). Peer-median businesses at $700k: p %.3f-%.3f, labels %s' % (
                   CUT_HIGH, CUT_MOD, LAB['quartiles']['p75'], LAB['quartiles']['p25'], LAB['quartiles']['p75_se'], LAB['quartiles']['p25_se'],
                   100 * _sh['High'], 100 * _sh['Moderate'], 100 * _sh['Low'], 100 * LAB['share_outside'],
                   100 * LAB['shares_main_street_by_p']['High'], 100 * LAB['shares_main_street_by_p']['Moderate'], 100 * LAB['shares_main_street_by_p']['Low'],
                   100 * LAB['bootstrap_rounded_cuts_differ']['cut_high'], ALT_HIGH, 100 * LAB['if_rounded_the_other_way']['cut_high %.2f' % ALT_HIGH]['High'],
                   100 * LAB['bootstrap_rounded_cuts_differ']['cut_moderate'], ALT_MOD, 100 * LAB['if_rounded_the_other_way']['cut_moderate %.2f' % ALT_MOD]['Low'],
                   COMPARE['peer_median_at_700k']['p_min'], COMPARE['peer_median_at_700k']['p_max'], COMPARE['peer_median_at_700k']['labels']))}
GRADT = pd.DataFrame([dict(term='b_size', estimate=bm[1], se=se_m[1], p=MAIN['p_size']), dict(term='b_em', estimate=bm[2], se=se_m[2], p=MAIN['p_em']),
                      dict(term='ln_s0 (ask panel)', estimate=bm[0], se=se_m[0], p=np.nan)] +
                     [dict(term='industry ' + k, estimate=MAIN['industry'][k], se=MAIN['industry_se'][k], p=pval(MAIN['industry'][k], MAIN['industry_se'][k])) for k in IK])
GRADT.to_csv(OUT + '/gradients.csv', index=False, float_format='%.4f')
SOURCES = [
    dict(name='DealLedger broker listings (CC0): %d daily snapshot files read, %d with an id column' % (FILES_META['read'], FILES_META['with_id']),
         url='https://github.com/jeffsosville/dealledger', file=DL_DIR + '/<date>/listings.csv',
         sha256=DL_DIGEST, sha256_note='digest of the sorted (path, sha256) list of all files read',
         years='%s to %s (the %s file has no id column and contributes nothing)' % (FILES_META['first_with_id'], FILES_META['last_with_id'], ', '.join(FILES_META['without_id'])),
         n='%d listings after the research filters; %d with revenue > SDE; %d Main-Street; %d Main-Street in support (%d brokers)' % (n_all, n_rev, int(H.main_street.sum()), MAIN['n_in_support'], MAIN['n_brokers'])),
    dict(name='The Omni Method snapshot (HEAD 56ba230): MODELS.value (BIZCOMPS 18,941 closed sales: within_25pct, fan_quantiles, support, industry tables), MODELS.fitted.sde_margin, IND2NAICS6',
         url='local', file=SNAP, sha256=sha(SNAP), years='BIZCOMPS fit as stored', n='18,941 sales; 274 6-digit cells (18,143 sales)'),
    dict(name='harness (loads the snapshot\'s model section)', url='local', file=HARNESS, sha256=sha(HARNESS), years='-', n='-'),
    dict(name='Lie & Lie (2002), Multiples Used to Estimate Corporate Value, FAJ 58(2): Table 3 (p. 6) EV/EBITDA, Table 1 (p. 3)', url='https://www.biz.uiowa.edu/faculty/elie/ValByMult.pdf',
         file=LIE_PDF, sha256=sha(LIE_PDF), years='Compustat fiscal 1998', n='1,692 / 1,942 / 1,127 nonfinancial firms by size'),
    dict(name='Empire Flippers sold listings, per-deal sale price reconstruction (check only)', url='Empire Flippers public marketplace API', file=EF_CSV, sha256=sha(EF_CSV),
         years='%d-%d' % (int(EF.sold_year.min()), int(EF.sold_year.max())), n='%d deals usable, %d in the console support' % (len(EF), len(EFin))),
    dict(name='BizBuySell Insight national medians 2025 (secondary pages; level check only)', url='bizbuysell.com/insight-report via businessexits.com', file=BBS_CSV, sha256=sha(BBS_CSV),
         years='2025', n='%.0f closed sales' % 9586),
]
for f, nm in [(R_REBASE, 'research conf_rebase.json (replication check)'), (R_ACC, 'research dl_accuracy.json (replication check)')]:
    if os.path.exists(f):
        SOURCES.append(dict(name=nm, url='local', file=f, sha256=sha(f), years='-', n='-'))

_pt = lambda e, z=0.0, cp=None: conf_py(e, e / 0.2, 'home', z, 0.0, JS_TABLE, cp)['p']
TESTS['b_size negative, b_em positive'] = B_SIZE < 0 and (B_EM > 0 or not ship_em)
TESTS['p increases with SDE and falls with |z.em| on the shipped table'] = _pt(1e5) < _pt(1e6) and _pt(7e5, 1.5) <= _pt(7e5, 0.0)
TESTS['p falls as comps falls (depth)'] = _pt(7e5, 0.0, .2) < _pt(7e5, 0.0, .98)
TESTS['cut-offs ordered and inside (0, 1)'] = 0 < CUT_MOD < CUT_HIGH < 1
TESTS['each cut-off is its Main-Street quartile of p rounded to 0.01'] = (
    abs(CUT_HIGH - LAB['quartiles']['p75']) <= CUT_STEP / 2 + 1e-12 and abs(CUT_MOD - LAB['quartiles']['p25']) <= CUT_STEP / 2 + 1e-12)
TESTS['all shipped SEs positive and finite'] = all(isinstance(v, float) and math.isfinite(v) and v > 0 for v in [K_se, float(se_m[1]), float(se_m[2]), TAU2_SE])
TESTS['the level check lowers P at the reference (prices above V)'] = BBS_SHIFT > 1 and P_SHIFT < NORM['p_reference']
TESTS['the shipped centring removes most of the location trend (range of bin medians, 50+ listings, under half of round 2\'s)'] = (
    max(_core(_lt1)) - min(_core(_lt1)) < 0.5 * (max(_core(_lt0)) - min(_core(_lt0))))

ROUND3 = dict(
    decisions=['1 location vs scale: centring on industry, ln SDE, signed z.em, z.em^2; scale-only gradients ship; location-inclusive and broker-FE values are sensitivities; '
               'P assumes V centred on today\'s prices, the BizBuySell level check carried as a range and an SE component',
               '2 cut-offs: Main-Street quartiles of p rounded to 0.01; labels are relative standing; label shares reported',
               '3 extrapolation: Low, "outside the fitted data", when out.extrapMax > 3 or the margin is outside support.margin',
               '4 depth: comps computed in conf() from industry_n6, naics6For and k_naics6; 0 without a 6-digit cell (saas)',
               '5 claims (a)-(e) and metadata corrected', '6 conf(s, out) -> {p, label, note, sigma, band80}; ten test vectors'],
    round2=ROUND2,
    round3=dict(K=JS_TABLE['K'], b_size=JS_TABLE['b_size'], b_size_se=JS_TABLE['se']['b_size'], p_size=MAIN['p_size'], b_em=JS_TABLE['b_em'],
                b_em_se=JS_TABLE['se']['b_em'], p_em=MAIN['p_em'], tau2=JS_TABLE['tau2'], s_eq=S_EQ, cut_high=CUT_HIGH, cut_moderate=CUT_MOD,
                p_reference=NORM['p_reference'], comps='computed in conf(): n6/(n6+k_naics6), saas 0', centring=MAIN['centring']))
RES.update(dict(
    tier='mixed', tier_note=('fitted: the level (BIZCOMPS out-of-fold), the gradients (DealLedger listings, broker-cluster SEs) and tau^2 (BIZCOMPS cells); '
                             'calibrated: K, which pins the BIZCOMPS-like mix to 0.4454; convention: the label cut-offs; rule: the outside-the-data label; '
                             'approximation: s_eq'),
    js_table=JS_TABLE, js_line=JS_LINE, js_code=JS_CODE, integration_line=INTEGRATION_LINE.strip(), shipped=SHIPPED, not_shipped=NOT_SHIPPED, decision=DECISION,
    main=MAIN, sensitivity=SENST.to_dict(orient='records'), robustness=ROBT.to_dict(orient='records'), checks=CHECKS, sources=SOURCES, tests=TESTS,
    round3=ROUND3,
    console_current=dict(formula='conf = .34 comps + .30 min(1, yrs/8) + .22 fin + .14 max(0, 1 - mean|z|/2.2); High > .68, Moderate > .46',
                         comps_hand_set=IND_COMPS_NOW, comps_fit6_D=COMPS_D, comps_shipped=COMPS_V),
    readme_row=('| `confidence` (P(realised price within 25%% of the fitted value V, price / V in [0.80, 1.333]; assumes V centred on today\'s prices): BIZCOMPS '
                'out-of-fold level 0.4454 and fan shape; scale-only ln scale %.3f per ln SDE (SE %.3f) and +%.3f per unit |z.em| (SE %.3f) from DealLedger '
                'Main-Street asks with parse errors removed, each centred on industry, ln SDE, z.em and z.em^2; depth tau^2 %.4f (1 - comps), comps from the '
                'value model\'s own 6-digit cell; K %.3f normalises a BIZCOMPS-like mix to 0.4454; relative labels High >= %.2f, Moderate >= %.2f (listing '
                'quartiles); Low "outside the fitted data" past 3x or with the margin outside support) | `confidence_accuracy.py` (writes RESULT.json, conf.js '
                'and tables to `/tmp/claude-0/fit6/out/confidence_accuracy/`; runs the model through the harness) | DealLedger listings (%d daily files, %s to %s; '
                '%d Main-Street listings in support, %d brokers); MODELS.value (BIZCOMPS); BizBuySell 2025 medians (level check); Lie & Lie (2002) Table 3 '
                '(check); Empire Flippers sale reconstruction (check) | `git clone --depth 1 https://github.com/jeffsosville/dealledger`; '
                '`curl -L -O https://www.biz.uiowa.edu/faculty/elie/ValByMult.pdf` |'
                % (B_SIZE, se_m[1], B_EM, se_m[2], TAU2, K, CUT_HIGH, CUT_MOD, FILES_META['with_id'], FILES_META['first_with_id'], FILES_META['last_with_id'],
                   MAIN['n_in_support'], MAIN['n_brokers']))))
failed = [k for k, v in TESTS.items() if not v]
CHECKS['outcomes']['tests'] = '%d tests listed in RESULT.json: %s' % (len(TESTS), 'all pass' if not failed else '%d fail' % len(failed))
OUTJ = rnd(RES)
OUTJ['test_vectors'] = TV                                # stored at 6 decimals as computed (rnd() would cut sigma to 6 significant digits)
json.dump(OUTJ, open(OUT + '/RESULT.json', 'w'), indent=1, sort_keys=True)
log('RESULT.json written; %d tests; failed: %s' % (len(TESTS), failed or 'none'))
sys.exit(1 if failed else 0)
