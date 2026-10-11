"""Quality weights v2 (revised after two rounds of review): can online-business sales and broker-listing text move
the relative weights of the nine quality dimensions in the quality position?

Round-2 revisions (both reviewers accept_with_changes; no weight moves):
  - Recurring revenue: only growth has a confirmed direction. The recurring premium appears in ASKING prices
    (EF last ask, Flippa final asks) and not in sale prices (EF sale, Flippa auctions); a price-type x era table
    (ef_recurring_by_price.csv) documents it, and every patched text and test says so.
  - The 12-month-window sample is defined on the OBSERVED pricing_period_months (the median-imputed rows are no
    longer counted as 12-month windows).
  - Growth on twelve months of earnings is reported as two readings: within the sales EF priced on twelve months
    (a subsample EF selects on low growth; quoted as a range over the per-sd scale: own-sample sd to whole-EF sd)
    and on TTM re-basing of every full P&L (partly mechanical, corroborated by EF's published trend tables,
    ef_report_trend_tables.csv, re-estimated here). A primary-niche fixed-effects variant is in the spec set.
  - Ratio intervals are simulated from the JOINT sampling distribution of the nine pooled estimates (within-source
    correlations from the EF niche bootstrap, the DealLedger broker bootstrap and the Flippa row bootstrap); the
    independent-draw version is kept as a sensitivity, and a ratio against the Main Street-sourced dimensions only
    is reported because the full denominator leans on attenuated single-analog proxies.
  - Metadata key "identified" -> "fitted" plus "weak":["mgt"]; checked.grw.bracket -> ef_range and
    checked.rec.bracket -> posterior_range; tests use structural checks instead of hard-coded own/mgt/norm and no
    longer rank growth above the judgment dimensions.

The console places a business inside the measured residual band with a weighted composite
    qz = sum_k w_k s_k z_k / sqrt(sum_k w_k^2)            (QW in index.html)
At the median the per-sd effect of dimension k on ln(value) is slope * w_k / ||w||, with
slope = phi(0) * (ln hi + ln 1/lo) and, under equal weights, ||w|| = 3, so one dimension's
equal-weight per-sd effect is beq = phi(0) * (ln hi + ln 1/lo) / 3 = 0.0791.
A measured per-sd effect e_k converts to a relative weight w_k = e_k / beq (fit/quality_weights.py).
QW is SCALE-FREE: only the ratios w_k / w_j change any number in the console.

Sources
  1. Empire Flippers (EF) sold listings, reconstructed per-deal SALE multiple and exact last ASK multiple
     (extra_ef_sale_ask_reconstruction, n = 2,644 after the reconstruction's own exclusions).
     Hedonic OLS of ln sale multiple on one proxy per dimension plus controls (size, SDE margin, pricing window,
     business age, trademark, lender approval, monetisation count, sites, PBN, text length, business model,
     sold year). SEs: the largest of niche-, quarter-clustered and HC1, and a niche-cluster bootstrap of the
     whole pipeline (the larger of bootstrap and analytic is used).
     EARNINGS BASIS (review): EF prices a listing on the average profit of a pricing window that it shortens for
     growing businesses; the console prices on twelve months of earnings (BIZCOMPS annual SDE). The growth weight
     is therefore estimated on the sales priced on an observed 12-month window (window = trailing twelve months),
     with the per-sd scale of the whole EF growth distribution (observed rows only) and, as the other end of the
     range, the subsample's own sd. Window basis, TTM re-basing, an explicit growth x window-length interaction,
     functional form, era, niche fixed effects and console-unit variants are reported.
  2. Flippa 2026 recently sold: 208 auction sale prices and 419 classified FINAL ASKS (not sale prices), keyword
     flags. Micro deals. HC1 and row-bootstrap SEs; 5-fold CV of the keyword block; auction-only, ask-only and
     strict-wording variants of the recurring flag.
  3. DealLedger broker listings (Main Street asks): the settled fit/quality_weights.py pipeline, reproduced
     exactly (own 1.371 / 0.368, mgt 0.482 / 0.273), extended to the other phrase flags it already carries;
     broker-grouped 5-fold CV of the phrase block and of each phrase.
  4. GF Data AAFP premium (lower-middle-market PE buyouts): growth+margin joint check only, not pooled.

Conversion (one scale for every source, as fit/quality_weights.py)
  continuous proxy: e = beta * sd(x) over OBSERVED rows; binary flag: threshold model,
  e = beta / [phi(c)/(p(1-p))], c = Phi^-1(1-p). Sign set so that e > 0 means "better on the dimension is worth
  more". w = e / 0.0791. Sensitivities: each market scaled by its own residual spread; EF growth in the console's
  own units (per 13 points of growth); rank-normal and IQR scales.
Screening (construct validity, before pooling): EF owner hours, Flippa owner wording (own) and EF/Flippa "team"
  wording (mgt) are reported but not pooled (EF owners work a median 3 h/week; online "teams" are freelancers
  already costed in net profit). DealLedger "repeat customers" stays excluded (wrong-signed boilerplate).
Combination: every estimate except the two settled DealLedger phrases gets a transfer/validity variance tau^2,
  tau = max(method of moments EF vs DealLedger on the pooled shared dims, 0.30 floor = judgment); inverse-
  variance pooling; then the N(1, 0.5^2) prior of fit/quality_weights.py.
Scale-free check (review): because only ratios matter, each dimension's pooled estimate is divided by the
  DerSimonian-Laird random-effects common level of the OTHER eight measured dimensions; Cochran's Q tests
  whether the nine differ at all. The anchor 0.0791 cancels in that ratio.
Identification rule v2 (review): a weight moves off 1 only if (a) the pooled data SE < prior SD, (b) a Main Street
  source or >= 2 sources, (c) some source shows out-of-sample value of the proxy (drop-one loss rise > 1.645 se),
  (d) the scale-free ratio's 95% interval excludes 1, and (e) the ratio stays on the same side of 1 across the
  specification set (earnings basis, scale, wording, sample, tau). Settled own/mgt are reported, not re-decided.
Model impact and implementation: the recommended vector (unchanged weights) is applied with metadata and Data-tab
  text to a COPY of index.html (OUT/testrepo/index.html, OUT/index.html.diff); tests/model.test.js,
  tests/fuzz.test.js and a new tests/quality_weights.test.js run on that copy; every model output is compared with
  the unpatched page on random businesses; the Data tab is rendered in headless Chromium when playwright is
  available. The repo's index.html is never modified.

Run: python3 -I /home/user/last-minute/fit/quality_weights_v2.py   (env NB = bootstrap reps, default 400; FUZZ=0 skips
     the fuzz test; BROWSER=0 skips the headless render; QW2_OUT redirects the outputs)
Outputs: /tmp/claude-0/fit5/quality_weights_v2/  (RESULT.json, run.log, summary.json, *.csv, index.html.diff)
"""
import os, re, json, subprocess, warnings, time
for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'          # small least-squares problems: threading only adds overhead
from math import erf, sqrt, exp, log, pi
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
warnings.filterwarnings('ignore')

OUT = os.environ.get('QW2_OUT', '/tmp/claude-0/fit5/quality_weights_v2')   # override only for replication / debug runs
os.makedirs(OUT, exist_ok=True)
EFR = '/tmp/claude-0/data5/extra_ef_sale_ask_reconstruction/clean/ef_sale_ask_reconstructed.csv'
EFL = '/tmp/claude-0/data5/empireflippers/clean/ef_listings.csv'
EFT = '/tmp/claude-0/data5/empireflippers/clean/ef_listings_text.jsonl'
EFM = '/tmp/claude-0/data5/empireflippers/clean/ef_monthly_metrics.csv'
EFTT = '/tmp/claude-0/data5/empireflippers/clean/ef_report_trend_tables.csv'
DLP = '/tmp/claude-0/fit/hed.pkl'
FLP = '/tmp/claude-0/data5/flippa/clean/flippa2026_recently_sold.csv'
GFD = '/tmp/claude-0/data5/aggregates_research/clean/gfdata_quality_premium.csv'
HARN = '/tmp/claude-0/fit5/harness.js'
IDX = '/home/user/last-minute/index.html'
REPO_TESTS = '/home/user/last-minute/tests'
NB = int(os.environ.get('NB', '400'))
PRIOR_SD = 0.5
TAU_FLOOR = 0.30
TAU_REVIEW = 0.62           # the reviewers' all-shared-dims method-of-moments value, reported as a headline sensitivity
CONSOLE_GRW_SD = 0.13       # the z scale of growth in model()
Z_OOS = 1.645               # out-of-sample criterion: loss rise when the proxy is dropped > 1.645 cluster se
DIMS = ['rec', 'own', 'mgt', 'grw', 'gm', 'ret', 'fin', 'cc', 'plt']
LOG = []
T0 = time.time()


def say(*a):
    s = ' '.join(str(x) for x in a)
    if s.startswith('\n['): s = s + f'   (t={time.time() - T0:.0f}s)'
    print(s)
    LOG.append(s)


def Phi(x): return 0.5 * (1 + erf(x / sqrt(2)))
def phi(x): return exp(-x * x / 2) / sqrt(2 * pi)
def Pinv(p): return float(stats.norm.ppf(p))


def gap(p):
    """threshold model: a flag marks the top share p of a standard-normal latent; mean-z gap flagged vs not"""
    c = Pinv(1 - p)
    return phi(c) / (p * (1 - p))


# ------------------------------------------------------------------ model constants from index.html
html = open(IDX, encoding='utf8').read()
qb = re.search(r'"quality_band":\{"lo":([0-9.]+),"mid":[0-9.]+,"hi":([0-9.]+)', html)
LO, HI = float(qb.group(1)), float(qb.group(2))
SLOPE = phi(0) * (log(HI) + log(1 / LO))
BEQ = SLOPE / 3
cur = re.search(r'"quality_weights":\{"own":([0-9.]+),"mgt":([0-9.]+)', html)
CUR = {k: 1.0 for k in DIMS}
CUR['own'], CUR['mgt'] = float(cur.group(1)), float(cur.group(2))
say(f'quality band lo {LO} hi {HI}; slope at median {SLOPE:.4f}; equal-weight per-sd effect beq {BEQ:.4f}; current QW {CUR}')


def beq_from_resid(e):
    q25, q50, q75 = np.percentile(e, [25, 50, 75])
    return phi(0) * ((q75 - q50) + (q50 - q25)) / 3


# ================================================================== 1. EMPIRE FLIPPERS
r = pd.read_csv(EFR)
L = pd.read_csv(EFL, low_memory=False)
T = pd.read_json(EFT, lines=True)
M = pd.read_csv(EFM)
excl = r.flag_top_censored | r.flag_wide_bracket | r.flag_no_ask | (r.listing_multiple < 6) | r.ratio_mean.isna()
d = r[~excl].copy()
keepL = ['listing_number', 'cogs_percent', 'uses_pbn', 'sites_n', 'monetizations_n', 'mrr', 'churn_percent',
         'data_providers_n', 'work_required_n']
assert r.listing_number.is_unique and L.listing_number.is_unique and T.listing_number.is_unique
d = d.merge(L[keepL], on='listing_number', how='left')
d = d.merge(T[['listing_number', 'summary', 'work_required', 'assets_included', 'risks']], on='listing_number', how='left')
say(f'\n[EF] reconstructed sold deals {len(r)}, analysis sample {len(d)} (same exclusions as the reconstruction fit)')


def cat_of(m):
    first = (m if isinstance(m, str) else '').split('|')[0]
    if first in ('Amazon Associates', 'Display Advertising', 'Affiliate', 'YouTube', 'Lead Gen', 'Newsletter'): return 'content'
    if first in ('Amazon FBA', 'Amazon FBM'): return 'amazon_fba'
    if first in ('eCommerce', 'DropShipping', 'Subscription-Box'): return 'ecommerce'
    if first in ('Amazon KDP', 'Amazon Merch'): return 'kdp_merch'
    if first in ('SaaS', 'Subscription', 'Application', 'Digital Product', 'Info Product'): return 'saas_digital'
    if first in ('Service', 'Agency'): return 'service'
    return 'other'


def tb(x): return x.astype(str).str.lower().eq('true').astype(float)


d['cat'] = d.monetizations.apply(cat_of)
d['ls'] = np.log(d.sale_mult_mean)
d['la'] = np.log(d.listing_multiple)
d['lr'] = d.ls - d.la
d['yr'] = d.sold_year.astype(int)
d['qtr'] = pd.to_datetime(d.sold_date_est).dt.to_period('Q').astype(str)
d['niche1'] = d.niches.fillna('none').str.split('|').str[0]
# controls
d['l_np'] = np.log(np.clip(d.average_annual_net_profit, 1000, None))
d['l_np_c'] = d.l_np - d.l_np.median()
d['l_np2'] = d.l_np_c ** 2


def wz(c, lo, hi):
    v = pd.to_numeric(d[c], errors='coerce').clip(lo, hi)
    return v.fillna(v.median()), v.isna().astype(float)


d['margin'], d['margin_miss'] = wz('profit_margin', 0, 100)
d['margin'] /= 100
d['ppm'], d['ppm_miss'] = wz('pricing_period_months', 1, 24)   # control (median-imputed where missing)
d['ppm_obs'] = pd.to_numeric(d.pricing_period_months, errors='coerce')   # observed window, for sample definitions (review 2)
age, _ = wz('business_age_years_at_listing', 0, 25)
d['l_age'] = np.log1p(age)
d['tm'] = tb(d.has_trademark)
d['lender'] = tb(d.private_lender_approved)
d['n_mon'] = d.monetizations.fillna('').str.count(r'\|') + 1
d['l_sites'] = np.log(d.sites_n.fillna(1).clip(1, 20))
d['pbn'] = tb(d.uses_pbn)
txt_sum = d.summary.fillna('').str.lower()
txt_ops = (d.work_required.fillna('') + ' . ' + d.assets_included.fillna('')).str.lower()
txt_all = txt_sum + ' . ' + txt_ops
d['l_txt'] = np.log1p(txt_all.str.len())

# ---- quality proxies (one primary per dimension) ----
# own: seller-reported owner hours per week (log1p). 0 h is mostly a 2014-17 default, treated as missing.
h = pd.to_numeric(d.hours_worked_per_week, errors='coerce')
d['hours_miss'] = ((h <= 0) | h.isna()).astype(float)
hh = np.log1p(h.where(h > 0).clip(upper=60))
d['own_hours'] = hh.fillna(hh.median())
# mgt: operations delegated to a team (staff, VAs, contractors, writers, managers) per work_required/assets/summary
RX_TEAM = (r'\b(staff|employees?|team members?|virtual assistants?|vas?|contractors?|freelancers?|writers?|editors?|'
           r'managers?|outsourc\w*|customer (service|support) (rep|agent|team)\w*)\b|\bteam\b')
d['mgt_team'] = txt_all.str.contains(RX_TEAM, regex=True).astype(float)
d['mgt_sop'] = txt_all.str.contains(r'\bsops?\b|standard operating|documented (process|procedure)', regex=True).astype(float)
# grw: annualised log revenue growth inside the P&L window: last k months vs first k months, k = min(6, n/2)
M = M[M.listing_status == 'Sold'].sort_values(['listing_number', 'month'])
assert not M.duplicated(['listing_number', 'month']).any()


def growth(g):
    v = g.gross_revenue.clip(lower=1).values
    n = len(v)
    if n < 6: return np.nan
    k = min(6, n // 2)
    return np.log(v[-k:].mean() / v[:k].mean()) * 12 / (n - k)


G = M.groupby('listing_number').apply(growth).rename('g_rev')
d = d.merge(G, left_on='listing_number', right_index=True, how='left')
lo_, hi_ = d.g_rev.quantile([.025, .975])
d['grw_miss'] = d.g_rev.isna().astype(float)
d['grw_rev'] = d.g_rev.clip(lo_, hi_).fillna(d.g_rev.median())
tr = pd.to_numeric(d.gross_revenue_trend_percent, errors='coerce').clip(-60, 150) / 100
d['grw_trend_miss'] = tr.isna().astype(float)
d['grw_trend'] = tr.fillna(tr.median())
# rank-normal (van der Waerden) growth score among observed rows, 0 where missing (functional-form check)
nobs_g = int(d.g_rev.notna().sum())
d['grw_rn'] = pd.Series(stats.norm.ppf((d.g_rev.rank(method='average') - 0.5) / nobs_g), index=d.index).fillna(0.0)

# ---- earnings bases (review). EF's multiple = price / (12 x mean monthly net profit over the pricing window).
# The P&L has at most 12 months; trailing-twelve-month (TTM) profit exists where all 12 are present.
NM = M.groupby('listing_number').size().rename('nmon')
TTMP = M.groupby('listing_number').net_profit.apply(lambda v: float(v.values.mean()) if len(v) == 12 else np.nan).rename('ttm_np')
n_before = len(d)
d = d.merge(NM, left_on='listing_number', right_index=True, how='left').merge(TTMP, left_on='listing_number', right_index=True, how='left')
assert len(d) == n_before
d['ttm_ok'] = ((d.nmon == 12) & (d.ttm_np > 0)).astype(bool)
d['ls_ttm'] = np.log(d.sale_price_mean / (12 * d.ttm_np.where(d.ttm_ok)))
d['l_win_ttm'] = np.log(d.average_monthly_net_profit / d.ttm_np.where(d.ttm_ok))
d['g_x_ppm'] = d.grw_rev * (d.ppm - 12)          # growth effect allowed to vary with window length; 0 at a 12-month window
Mg = {k: g.net_profit.values for k, g in M.groupby('listing_number')}
_chk = np.array([Mg[ln][-int(p):].mean() / a - 1 if ln in Mg and len(Mg[ln]) >= p else np.nan
                 for ln, p, a in zip(d.listing_number, d.ppm, d.average_monthly_net_profit)])
WIN_CHECK = float(np.nanmean(np.abs(_chk) < 0.01))
say(f'[EF] data check: mean net profit of the last pricing_period_months P&L months equals average_monthly_net_profit '
    f'within 1% for {WIN_CHECK:.1%} of {int(np.isfinite(_chk).sum())} deals; 12-month P&L with positive TTM profit: {int(d.ttm_ok.sum())}; '
    f'observed pricing window = 12 months: {int(d.ppm_obs.eq(12).sum())} ({int(d.ppm_miss.sum())} deals have no pricing window: '
    f'listings {sorted(d.listing_number[d.ppm_miss > 0].astype(int).tolist())}, sold {sorted(d.yr[d.ppm_miss > 0].unique().tolist())}, '
    f'{int(d.g_rev[d.ppm_miss > 0].notna().sum())} with a growth measure; median-imputed as a control only, never counted as 12-month windows)')

# gm: gross margin = 1 - COGS share (physical-product listings, 2022+); centred where observed, 0 + flag otherwise
gmv = 1 - pd.to_numeric(d.cogs_percent, errors='coerce') / 100
d['gm_miss'] = gmv.isna().astype(float)
d['gm_obs'] = (gmv - gmv.mean()).fillna(0.0)
# rec: recurring / subscription revenue
RX_REC = (r'recurring (revenue|income|billing|payments?|subscri\w*)|subscription[- ](model|revenue|plans?|box|service|'
          r'business|based|income)|monthly recurring|\bmrr\b|\barr\b|membership (site|fees?|revenue|model|plans?)|retainers?\b')
RX_NEG = r'opportunit|could |potential|consider|no recurring|not recurring|plans? to|would be'


def sent_flag(texts, rx):
    """1 if any sentence matches rx and is not about an opportunity / hypothetical / negation"""
    out = []
    for t in texts:
        out.append(float(any(re.search(rx, z) and not re.search(RX_NEG, z) for z in re.split(r'(?<=[.!?])\s+', t))))
    return np.array(out)


mon = d.monetizations.fillna('')
d['rec_mon'] = (mon.str.contains(r'SaaS|Subscription') | d.mrr.notna()).astype(float)
d['rec_txt'] = (sent_flag(txt_sum, RX_REC) > 0).astype(float)
d['rec_flag'] = ((d.rec_mon > 0) | (d.rec_txt > 0)).astype(float)
# ret: retention / repeat-purchase wording (churn_percent is reported for too few deals)
RX_RET = (r'repeat (customers?|purchases?|buyers?|orders?|rate|business)|returning (customers?|buyers?)|customer retention|'
          r'retention rate|loyal (customers?|customer base|following|audience)|low churn')
d['ret_flag'] = sent_flag(txt_sum, RX_RET)
# plt: number of distinct acquisition channels named in the summary (more channels = less channel concentration)
CH = {'search': r'organic (search|traffic)|\bseo\b|google search|search engines?|organic rankings?',
      'pinterest': r'pinterest', 'meta': r'facebook|instagram', 'tiktok': r'tik ?tok', 'youtube': r'youtube',
      'email': r'email (list|marketing|subscribers|campaigns?)|newsletter', 'paid': r'\bppc\b|paid (ads|advertising|traffic|search|social)|google ads|adwords|sponsored (products|ads)|amazon ads',
      'direct': r'direct traffic|referral traffic|word of mouth|repeat traffic', 'other_social': r'twitter|reddit|quora|linkedin|snapchat'}
d['plt_nch'] = sum(txt_sum.str.contains(p, regex=True).astype(float) for p in CH.values())
say(f'[EF] churn_percent reported for {int(d.churn_percent.notna().sum())} deals; data_providers only for sold_year>=2023 '
    f'({int((d.data_providers_n > 0).sum())} deals, collinear with year): retention and reporting have no usable EF measure')

# proxies: (column, dimension, kind, sign) sign = +1 if a higher proxy is BETTER on the dimension
PROX = [('own_hours', 'own', 'cont', -1), ('mgt_team', 'mgt', 'flag', +1), ('grw_rev', 'grw', 'cont', +1),
        ('gm_obs', 'gm', 'cont', +1), ('rec_flag', 'rec', 'flag', +1), ('ret_flag', 'ret', 'flag', +1),
        ('plt_nch', 'plt', 'cont', +1)]
QCOLS = [p[0] for p in PROX]
CTRL = ['l_np_c', 'l_np2', 'margin', 'margin_miss', 'ppm', 'l_age', 'tm', 'lender', 'n_mon', 'l_sites', 'pbn', 'l_txt',
        'hours_miss', 'grw_miss', 'gm_miss']
# per-sd scales use OBSERVED rows only (review: median-imputed rows shrink the sd)
OBSM = {'own_hours': d.hours_miss.values == 0, 'grw_rev': d.grw_miss.values == 0, 'grw_rn': d.grw_miss.values == 0,
        'gm_obs': d.gm_miss.values == 0, 'grw_trend': d.grw_trend_miss.values == 0}
desc = {}
for c in QCOLS + ['mgt_sop', 'grw_trend', 'rec_mon', 'rec_txt']:
    ob = OBSM.get(c, np.ones(len(d), bool))
    desc[c] = dict(mean=float(d[c][ob].mean()), sd=float(d[c][ob].std()), n_obs=int(ob.sum()))
for c in ['mgt_team', 'rec_flag', 'ret_flag', 'mgt_sop', 'rec_mon', 'rec_txt']: desc[c]['n_flagged'] = int(d[c].sum())
desc['grw_rev']['sd_incl_imputed'] = float(d.grw_rev.std())
say('[EF] proxies (observed rows):', json.dumps({k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in desc.items()}))
SD_G = desc['grw_rev']['sd']
say(f'[EF] growth scales: P&L growth sd {SD_G:.3f}/yr on {desc["grw_rev"]["n_obs"]} observed rows ({desc["grw_rev"]["sd_incl_imputed"]:.3f} with the '
    f'{len(d) - desc["grw_rev"]["n_obs"]} median-imputed rows, as v1 used) = {SD_G / CONSOLE_GRW_SD:.1f}x the console\'s {CONSOLE_GRW_SD:.2f}; '
    f'EF displayed 12-month trend sd {desc["grw_trend"]["sd"]:.3f} = {desc["grw_trend"]["sd"] / CONSOLE_GRW_SD:.1f}x')

ALTCOLS = ['grw_trend', 'grw_trend_miss', 'mgt_sop', 'grw_rn', 'g_x_ppm', 'rec_mon', 'rec_txt']


def design(x, qcols):
    """full design: const, business-model and sold-year dummies, controls, quality proxies (column set fixed by x)"""
    X = pd.get_dummies(x[['cat']].astype(str), drop_first=True, dtype=float)
    Y = pd.get_dummies(x.yr.astype(str), prefix='y', drop_first=True, dtype=float)
    X = pd.concat([X, Y], axis=1)
    for c in list(CTRL) + list(qcols): X[c] = x[c].values
    X.insert(0, 'const', 1.0)
    return X


def unit_of(col, kind, idx):
    """per-sd unit of a proxy on rows idx: threshold-model gap for a flag, observed-row sd for a continuous proxy"""
    xv = d[col].values[idx]
    if kind == 'flag': return 1 / gap(float(xv.mean()))
    ob = OBSM.get(col)
    return float(xv[ob[idx]].std(ddof=1)) if ob is not None else float(xv.std(ddof=1))


def ols(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b, y - X @ b


XALL = design(d, QCOLS + ALTCOLS)          # one fixed column set; variants pick columns by name
COLS = list(XALL.columns)
XV = XALL.values
BASECOLS = [c for c in COLS if c not in QCOLS + ALTCOLS]
BASEIDX = [COLS.index(c) for c in BASECOLS]
BASEIDX_NOCAT = [COLS.index(c) for c in BASECOLS if not c.startswith('cat_')]


def ef_fit(idx, yname, prox=PROX, extra_ctrl=(), base=None):
    """fit on rows idx; returns {dim: per-sd effect}, beq of the controls-only residual spread, {dim: coefficient}"""
    base = BASEIDX if base is None else base
    qc = [p[0] for p in prox]
    ci = base + [COLS.index(c) for c in list(extra_ctrl) + qc]
    X = XV[idx][:, ci]
    y = d[yname].values[idx]
    b, _ = ols(y, X)
    _, e0 = ols(y, XV[idx][:, base + [COLS.index(c) for c in extra_ctrl]])
    out, cf = {}, {}
    for j, (col, dim, kind, sign) in enumerate(prox):
        cf[dim] = b[len(base) + len(extra_ctrl) + j]
        out[dim] = sign * cf[dim] * unit_of(col, kind, idx)
    return out, beq_from_resid(e0), cf


def sm_fit(idx, yname, cols, groups=('niche1', 'qtr')):
    """statsmodels OLS on rows idx with columns cols; returns params and the largest of the clustered and HC1 SEs"""
    X = XALL.iloc[idx][cols]
    X = X.loc[:, (X.std() > 0) | (X.columns == 'const')]
    y = d[yname].values[idx]
    fits = [sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d[g].values[idx])[0]}) for g in groups]
    fits.append(sm.OLS(y, X).fit(cov_type='HC1'))
    se = pd.concat([f.bse for f in fits], axis=1).max(axis=1)
    return fits[0].params, se, fits


ALL = np.arange(len(d))
P12 = d.ppm_obs.eq(12).values           # OBSERVED 12-month pricing window (review 2: imputed windows excluded)
TTMOK = d.ttm_ok.values
I12 = np.where(P12)[0]
ITTM = np.where(TTMOK)[0]
JG = QCOLS.index('grw_rev')
rows = []
EF = {}
for yname, lab in [('ls', 'ln sale multiple'), ('la', 'ln last ask multiple'), ('lr', 'ln sale/ask')]:
    X = XALL[BASECOLS + QCOLS]
    y = d[yname].values
    m_n = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.niche1)[0]})
    m_q = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.qtr)[0]})
    m_h = sm.OLS(y, X).fit(cov_type='HC1')
    m0 = sm.OLS(y, XALL[BASECOLS]).fit()
    est, bq, _ = ef_fit(ALL, yname)
    say(f'\n[EF] {lab} (pricing-window basis): n={int(m_n.nobs)} R2={m_n.rsquared:.3f} (controls only {m0.rsquared:.3f}); controls-only resid sd '
        f'{np.sqrt(m0.scale):.3f}; own-spread beq_src {bq:.4f} (Main Street beq {BEQ:.4f})')
    for col, dim, kind, sign in PROX:
        bcoef = m_n.params[col]
        se = max(m_n.bse[col], m_q.bse[col], m_h.bse[col])
        unit = unit_of(col, kind, ALL)
        assert abs(abs(est[dim]) - abs(bcoef) * unit) < 1e-9, (col, est[dim], bcoef * unit)
        rows.append(dict(source='EF', y=yname, proxy=col, dim=dim, kind=kind, coef=bcoef, se_niche=m_n.bse[col], se_quarter=m_q.bse[col],
                         se_hc1=m_h.bse[col], se_used=se, t=bcoef / se, per_sd=est[dim], per_sd_se=se * unit,
                         w_main=est[dim] / BEQ, w_main_se_analytic=se * unit / BEQ, w_ownspread=est[dim] / bq, n=int(m_n.nobs)))
        say(f'   {col:10s}->{dim:4s} coef {bcoef:+.4f} se(niche {m_n.bse[col]:.4f}, qtr {m_q.bse[col]:.4f}, HC1 {m_h.bse[col]:.4f}) '
            f'per-sd {est[dim]:+.4f} (se {se * unit:.4f})  w {est[dim] / BEQ:+.3f} (se {se * unit / BEQ:.3f})  [own-spread scale {est[dim] / bq:+.3f}]')
    EF[yname] = dict(est=est, beq_src=bq, r2=float(m_n.rsquared), r2_controls=float(m0.rsquared), n=int(m_n.nobs))
coef_tab = pd.DataFrame(rows)


# ---- growth on the console's earnings basis (review, blocking): EF shortens the pricing window for growing businesses,
# so on the window basis part of the growth premium sits in the denominator. Two twelve-month readings (review 2):
# (i) sales priced on an observed 12-month window (window = TTM): a subsample EF selects on LOW growth; per-sd scale
#     quoted as a range, whole-EF growth sd (headline) to the subsample's own sd (narrower; the slope saturates above
#     the median, so the whole-EF scale extrapolates linearly into the flat region);
# (ii) TTM re-basing of every full 12-month P&L: on short-window deals the price was set on recent profit, so growth
#     lowers TTM profit without lowering the price (partly mechanical), but EF's own published trend tables show the
#     same TTM-basis premium. Check: growth x (window - 12) interaction at 12.
def ef_growth_variants(idx):
    sd = float(d.grw_rev.values[idx][OBSM['grw_rev'][idx]].std(ddof=1))
    ci = BASEIDX + [COLS.index(c) for c in QCOLS]
    out = {}
    s12 = idx[P12[idx]]
    for y in ['ls', 'la']:
        b, e = ols(d[y].values[s12], XV[s12][:, ci]); out[f'ttm12_{y}'] = b[len(BASEIDX) + JG] * sd
    _, e0 = ols(d.ls.values[s12], XV[s12][:, BASEIDX])
    out['ttm12_beq_src'] = beq_from_resid(e0)
    st = idx[TTMOK[idx]]
    b, _ = ols(d.ls_ttm.values[st], XV[st][:, ci]); out['ttm_rebased'] = b[len(BASEIDX) + JG] * sd
    b, _ = ols(d.ls.values[idx], XV[idx][:, ci + [COLS.index('g_x_ppm')]]); out['interaction_at12'] = b[len(BASEIDX) + JG] * sd
    return out, sd


GV, _ = ef_growth_variants(ALL)

# ---- niche-cluster bootstrap of the whole EF pipeline (sale and ask on the same draws, so sale-ask has an SE) ----
say(f'\n[EF] niche-cluster bootstrap of per-sd effects and weights, B={NB}')
gidx = {g: np.where(d.niche1.values == g)[0] for g in sorted(d.niche1.unique())}
gl = list(gidx)
DIMS_EF = [p[1] for p in PROX]
BS = {y: [] for y in ['ls', 'la']}
BSG = []
for bi in range(NB):
    pick = np.random.default_rng(1000 + bi).choice(len(gl), len(gl))
    idx = np.concatenate([gidx[gl[i]] for i in pick])
    for y in ['ls', 'la']:
        est, bq, _ = ef_fit(idx, y)
        BS[y].append([est[k] for k in DIMS_EF] + [bq])
    gv, _ = ef_growth_variants(idx)
    BSG.append(gv)
BS = {y: np.array(v) for y, v in BS.items()}
BSG = pd.DataFrame(BSG)
efw = []
for j, (col, dim, kind, sign) in enumerate(PROX):
    cs = coef_tab[(coef_tab.y == 'ls') & (coef_tab.proxy == col)].iloc[0]
    ca = coef_tab[(coef_tab.y == 'la') & (coef_tab.proxy == col)].iloc[0]
    bs_s = BS['ls'][:, j].std(ddof=1) / BEQ; bs_a = BS['la'][:, j].std(ddof=1) / BEQ
    diff = (BS['ls'][:, j] - BS['la'][:, j]) / BEQ
    efw.append(dict(dim=dim, proxy=col, basis='pricing window', w_sale=cs.w_main, w_sale_se_boot=bs_s, w_sale_se_analytic=cs.w_main_se_analytic,
                    w_sale_se=max(bs_s, cs.w_main_se_analytic), w_ask=ca.w_main, w_ask_se=max(bs_a, ca.w_main_se_analytic),
                    sale_minus_ask=cs.w_main - ca.w_main, sale_minus_ask_se=float(diff.std(ddof=1)),
                    boot_share_positive=float((BS['ls'][:, j] > 0).mean()), w_sale_ownspread=cs.w_ownspread,
                    w_sale_ownspread_se=float((BS['ls'][:, j] / BS['ls'][:, -1]).std(ddof=1))))
efw = pd.DataFrame(efw)
beq_ef_se = float(BS['ls'][:, -1].std(ddof=1))
say(efw.round(3).to_string(index=False))
say(f'   EF own-spread beq: sale {EF["ls"]["beq_src"]:.4f} (boot se {beq_ef_se:.4f}), ask {EF["la"]["beq_src"]:.4f}; '
    f'Main Street {BEQ:.4f}. Weights above use the Main Street scale (as fit/quality_weights.py).')

# ---- EARNINGS BASIS, ERA AND FUNCTIONAL FORM OF THE GROWTH WEIGHT (review) ----
say('\n[EF growth] earnings basis, era and functional form (weights on the Main Street per-sd scale; per-sd = whole-EF observed growth sd '
    f'{SD_G:.3f} unless stated)')
ob_g = OBSM['grw_rev']
ob_p = d.ppm_miss.values == 0
corr_ppm_obs = float(np.corrcoef(d.ppm[ob_g & ob_p], d.grw_rev[ob_g & ob_p])[0, 1]); corr_ppm_all = float(np.corrcoef(d.ppm, d.grw_rev)[0, 1])
by_ppm = d[ob_g & ob_p].groupby(pd.cut(d.ppm_obs[ob_g & ob_p], [0, 5, 9, 11, 12, 30])).grw_rev.agg(['mean', 'count'])
say(f'   corr(pricing window months, growth) {corr_ppm_obs:+.2f} on observed rows ({corr_ppm_all:+.2f} incl. imputed); mean annualised growth by '
    'window: ' + ', '.join(f'{k}: {v["mean"]:.2f} (n {int(v["count"])})' for k, v in by_ppm.iterrows()))
gb = []                                         # growth-basis table


def gb_row(label, idx, yname, gcol='grw_rev', sd=None, extra=(), boot=None, note=''):
    cols = BASECOLS + [c for c in QCOLS if c != 'grw_rev'] + [gcol] + list(extra)
    p_, se_, fits = sm_fit(idx, yname, cols)
    s = SD_G if sd is None else sd
    w, w_se = p_[gcol] * s / BEQ, se_[gcol] * s / BEQ
    if boot is not None: w_se = max(w_se, boot)
    row = dict(variant=label, n=len(idx), y=yname, proxy=gcol, scale_sd=s, coef=p_[gcol], coef_se=se_[gcol], w=w, w_se=w_se,
               w_se_boot=boot, w_console_units=p_[gcol] * CONSOLE_GRW_SD / BEQ if gcol == 'grw_rev' else np.nan,
               w_console_units_se=se_[gcol] * CONSOLE_GRW_SD / BEQ if gcol == 'grw_rev' else np.nan, note=note)
    for e in extra: row[f'coef_{e}'], row[f'se_{e}'] = p_[e], se_[e]
    gb.append(row)
    return row


bse = lambda k: float(BSG[k].std(ddof=1)) / BEQ
R_WIN = gb_row('pricing-window basis, all sales (v1 primary)', ALL, 'ls', boot=float(BS['ls'][:, JG].std(ddof=1) / BEQ))
gb_row('pricing-window basis, v1 scale (sd incl. imputed rows)', ALL, 'ls', sd=desc['grw_rev']['sd_incl_imputed'], note='v1 reported 0.49')
R_12 = gb_row('12-month window (= TTM) sales [PRIMARY]', I12, 'ls', boot=bse('ttm12_ls'))
R_12A = gb_row('12-month window sales, ask multiple', I12, 'la', boot=bse('ttm12_la'))
sd12 = float(d.grw_rev.values[I12][ob_g[I12]].std(ddof=1))
R_12OS = gb_row('12-month window sales, subsample own sd', I12, 'ls', sd=sd12, boot=bse('ttm12_ls') * sd12 / SD_G,
                note='selected on low growth: narrower sd; lower end of the twelve-month range')
R_INT = gb_row('all sales, growth x (window-12) interaction, at 12', ALL, 'ls', extra=('g_x_ppm',), boot=bse('interaction_at12'))
R_TTM = gb_row('every 12-month P&L re-based to TTM profit', ITTM, 'ls_ttm', boot=bse('ttm_rebased'),
               note='TTM basis over all full P&Ls: partly mechanical (price set on window profit), corroborated by EF trend tables')
_m12 = P12 & TTMOK                       # review 2: on 12-month windows the window IS the TTM, so both readings use the same months
MECH12 = np.abs(d.ls_ttm.values[_m12] - d.ls.values[_m12] + np.log(12))
say(f'   12-month-window deals with a full P&L (n={int(_m12.sum())}): |ln TTM multiple - ln window multiple + ln 12| median {np.median(MECH12):.5f}, '
    f'99th pct {np.percentile(MECH12, 99):.4f}: the two readings differ through the sample (window shortening for growers), not through shared months')
sdT = float(d.grw_rev.values[ITTM][ob_g[ITTM]].std(ddof=1))
gb_row('TTM re-based, sample own sd', ITTM, 'ls_ttm', sd=sdT)
gb_row('TTM re-based, rank-normal growth', ITTM, 'ls_ttm', gcol='grw_rn', sd=float(d.grw_rn.values[ob_g].std(ddof=1)))
gb_row('TTM re-based sample, pricing-window multiple', ITTM, 'ls')
R_RN12 = gb_row('12-month window sales, rank-normal growth', I12, 'ls', gcol='grw_rn', sd=float(d.grw_rn.values[ob_g].std(ddof=1)))
R_RNW = gb_row('pricing-window basis, rank-normal growth', ALL, 'ls', gcol='grw_rn', sd=float(d.grw_rn.values[ob_g].std(ddof=1)))
IQR_G = float(np.subtract(*np.percentile(d.grw_rev[ob_g], [75, 25])) / 1.349)
gb_row('pricing-window basis, IQR/1.349 scale', ALL, 'ls', sd=IQR_G)
R_12I = gb_row('12-month window sales, IQR/1.349 scale', I12, 'ls', sd=IQR_G)
p_mech, s_mech, _ = sm_fit(ITTM, 'l_win_ttm', BASECOLS + QCOLS)
I22 = np.where(d.yr.values >= 2022)[0]
R_22 = gb_row('sold 2022-26, all windows', I22, 'ls')
I12_22 = np.where(P12 & (d.yr.values >= 2022))[0]
gb_row('sold 2022-26, 12-month window', I12_22, 'ls')
gb_row('sold <= 2018, 12-month window', np.where(P12 & (d.yr.values <= 2018))[0], 'ls')
gb_row('sold 2019-26, 12-month window', np.where(P12 & (d.yr.values >= 2019))[0], 'ls')


def niche_fe(idx, yname, col, unit):
    """the primary design plus primary-niche fixed effects (review 2 replicator); returns weight and se on the Main Street scale"""
    X = XALL.iloc[idx][BASECOLS + QCOLS].copy()
    N_ = pd.get_dummies(d.niche1.iloc[idx].astype(str), prefix='n', drop_first=True, dtype=float)
    X = pd.concat([X.reset_index(drop=True), N_.reset_index(drop=True)], axis=1)
    X = X.loc[:, (X.std() > 0) | (X.columns == 'const')]
    y = d[yname].values[idx]
    fits = [sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d[g].values[idx])[0]}) for g in ('niche1', 'qtr')]
    fits.append(sm.OLS(y, X).fit(cov_type='HC1'))
    return float(fits[0].params[col] * unit / BEQ), float(max(f_.bse[col] for f_ in fits) * unit / BEQ), int(N_.shape[1] + 1)


NFE_G12 = niche_fe(I12, 'ls', 'grw_rev', SD_G)
gb.append(dict(variant='12-month window sales, primary-niche fixed effects', n=len(I12), y='ls', proxy='grw_rev', scale_sd=SD_G,
               w=NFE_G12[0], w_se=NFE_G12[1], note=f'{NFE_G12[2]} niches'))
gb_tab = pd.DataFrame(gb)
for _, rr in gb_tab.iterrows():
    say(f'   {rr.variant:58s} n={rr.n:5d} w {rr.w:+.2f} (se {rr.w_se:.2f})' + (f'  console units {rr.w_console_units:+.2f} (se {rr.w_console_units_se:.2f})'
        if np.isfinite(rr.w_console_units) else '') + (f'  [{rr.note}]' if rr.note else ''))
say(f'   interaction growth x (window - 12): {R_INT["coef_g_x_ppm"]:+.4f} per month (se {R_INT["se_g_x_ppm"]:.4f}, z {R_INT["coef_g_x_ppm"] / R_INT["se_g_x_ppm"]:+.1f}): '
    'the shorter the window, the less growth shows up in the window multiple')
say(f'   mechanical gap: ln(window profit / TTM profit) rises {p_mech["grw_rev"]:.3f} per unit of annualised growth (se {s_mech["grw_rev"]:.3f})')
# era: one regression with era-specific growth slopes (whole-EF observed sd), niche- and quarter-clustered
ERAS = [('2014-17', 2000, 2017), ('2018-19', 2018, 2019), ('2020-21', 2020, 2021), ('2022-23', 2022, 2023), ('2024-26', 2024, 2030)]
for lab, a, b in ERAS: d[f'g_era_{lab}'] = d.grw_rev * ((d.yr >= a) & (d.yr <= b))
ecols = [f'g_era_{lab}' for lab, _, _ in ERAS]
XE = design(d, [c for c in QCOLS if c != 'grw_rev'] + ecols)
fe = [sm.OLS(d.ls.values, XE).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d[g])[0]}) for g in ['niche1', 'qtr']]
era_tab = []
for (lab, a, b), c in zip(ERAS, ecols):
    sel = (d.yr >= a) & (d.yr <= b)
    era_tab.append(dict(era=lab, n=int(sel.sum()), w=fe[0].params[c] * SD_G / BEQ, w_se=max(f.bse[c] for f in fe) * SD_G / BEQ,
                        share_short_window=float((d.ppm_obs[sel & ob_p] < 12).mean()),
                        corr_window_growth=float(np.corrcoef(d.ppm[sel & ob_g], d.grw_rev[sel & ob_g])[0, 1])))
era_tab = pd.DataFrame(era_tab)
d['g_post19'] = d.grw_rev * (d.yr >= 2019)
brk = {}
for lab_, cols_ in [('all windows', QCOLS + ['g_post19']), ('12-month windows only', None)]:
    idx_ = ALL if cols_ else I12
    Xb_ = design(d.iloc[idx_], QCOLS + ['g_post19'])
    zz = []
    for g in ['niche1', 'qtr']:
        mm = sm.OLS(d.ls.values[idx_], Xb_.loc[:, (Xb_.std() > 0) | (Xb_.columns == 'const')]).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d[g].values[idx_])[0]})
        zz.append((mm.params['g_post19'] * SD_G / BEQ, mm.bse['g_post19'] * SD_G / BEQ, mm.params['g_post19'] / mm.bse['g_post19']))
    brk[lab_] = dict(diff=zz[0][0], se=max(zz[0][1], zz[1][1]), z_niche=zz[0][2], z_quarter=zz[1][2])
say('   era slopes (one regression): ' + ', '.join(f'{rr.era} {rr.w:+.2f} (se {rr.w_se:.2f}; {rr.share_short_window:.0%} short windows, corr(window, growth) {rr.corr_window_growth:+.2f})'
                                                for _, rr in era_tab.iterrows()))
say('   break 2019+ vs before: ' + '; '.join(f'{k}: {v["diff"]:+.2f} (se {v["se"]:.2f}, z niche {v["z_niche"]:+.1f}, quarter {v["z_quarter"]:+.1f})' for k, v in brk.items()))
# functional form: quintiles of observed growth
qg = pd.qcut(d.g_rev, 5, labels=False)
for j in range(1, 5): d[f'gq{j}'] = (qg == j).astype(float)
XQd = design(d, [c for c in QCOLS if c != 'grw_rev'] + [f'gq{j}' for j in range(1, 5)])
mqf = sm.OLS(d.ls.values, XQd).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.niche1)[0]})
quint = dict(mean_growth=[float(v) for v in d.groupby(qg).g_rev.mean()], effect=[0.0] + [float(mqf.params[f'gq{j}']) for j in range(1, 5)],
             se=[0.0] + [float(mqf.bse[f'gq{j}']) for j in range(1, 5)])
say('   quintiles of growth (mean ' + ', '.join(f'{v:+.2f}' for v in quint['mean_growth']) + '/yr): ln sale multiple vs bottom quintile '
    + ', '.join(f'{e:+.3f} ({s:.3f})' for e, s in zip(quint['effect'][1:], quint['se'][1:])) + ': saturates above the median')
# EF's own published trend tables (2021 report: Amazon Associates p42, Amazon FBA p67; segment x year x price tier x
# trailing-12-month trend): log difference of the average multiple, trend class minus Stable, within cells, weighted by
# 1/(1/n_a + 1/n_stable); cell-bootstrap SE. Corroborates (or not) a TTM-basis growth premium independently of our P&L
# growth measure (review 2).
tt = pd.read_csv(EFTT)
tt = tt[tt.price_tier != 'Annual']
TT = {}
for a_ in ['Increasing', 'Decreasing']:
    rows_ = []
    for _, g_ in tt.groupby(['segment', 'year', 'price_tier']):
        g_ = g_.set_index('trailing_12m_trend')
        if a_ in g_.index and 'Stable' in g_.index:
            rows_.append(dict(w=1 / (1 / g_.n_sold[a_] + 1 / g_.n_sold['Stable']),
                              win=np.log(g_.avg_pricing_window_sale_multiple_monthly[a_] / g_.avg_pricing_window_sale_multiple_monthly['Stable']),
                              ttm=np.log(g_.avg_ttm_sale_multiple_monthly[a_] / g_.avg_ttm_sale_multiple_monthly['Stable'])))
    r_ = pd.DataFrame(rows_)
    rg_ = np.random.default_rng(3); bt_ = []
    for _ in range(2000):
        s_ = r_.iloc[rg_.integers(0, len(r_), len(r_))]
        bt_.append([np.average(s_.win, weights=s_.w), np.average(s_.ttm, weights=s_.w)])
    bt_ = np.array(bt_)
    TT[a_] = dict(cells=len(r_), n=int(tt[tt.trailing_12m_trend.isin([a_, 'Stable'])].n_sold.sum()),
                  window=[float(np.average(r_.win, weights=r_.w)), float(bt_[:, 0].std(ddof=1))],
                  ttm=[float(np.average(r_.ttm, weights=r_.w)), float(bt_[:, 1].std(ddof=1))])
say('   EF 2021 report trend tables (log multiple vs Stable within segment x year x tier cells; cell-bootstrap se): '
    + '; '.join(f'{k} ({v["cells"]} cells): pricing-window multiple {v["window"][0]:+.3f} ({v["window"][1]:.3f}), TTM multiple {v["ttm"][0]:+.3f} ({v["ttm"][1]:.3f})'
                for k, v in TT.items()) + ': growth carries a premium on the TTM basis and almost none on the pricing-window basis, as in the deal-level fit')

# ---- out-of-sample validation ----
say('\n[EF] out-of-sample validation (year effects are not transported: y and X are demeaned within sold year on each side)')
XQ = XALL.drop(columns=['const'] + [c for c in COLS if c.startswith('y_')])


def oos_pred(trn, tst, yname, qcols):
    keep = [c for c in XQ.columns if c not in QCOLS + ALTCOLS] + list(qcols)
    def dm(ix):
        X = XQ.iloc[ix][keep]; yr = d.yr.values[ix]
        X = X - X.groupby(yr).transform('mean')
        y = pd.Series(d[yname].values[ix]); y = y - y.groupby(yr).transform('mean')
        return X.values, y.values
    Xtr, ytr = dm(trn); Xte, yte = dm(tst)
    b, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
    return yte, Xte @ b


def clmean(v, g):
    """mean of v and its cluster-robust SE (clusters g)"""
    v = np.asarray(v, float); m = v.mean()
    sc = pd.Series(v - m).groupby(np.asarray(g)).sum().values
    C = len(sc)
    return float(m), float(np.sqrt(C / (C - 1) * (sc ** 2).sum()) / len(v))


cv_rows = []
for yname in ['ls', 'la']:
    d_r2 = []
    for rep in range(20):
        perm = np.random.default_rng(500 + rep).permutation(len(d)); folds = np.array_split(perm, 5)
        ld = np.zeros(len(d)); sst = 0.0; sse0 = sse1 = 0.0
        drop = {c: np.zeros(len(d)) for c in QCOLS}
        for fo in folds:
            trn = np.setdiff1d(perm, fo)
            yte, p0 = oos_pred(trn, fo, yname, [])
            _, p1 = oos_pred(trn, fo, yname, QCOLS)
            ld[fo] = (yte - p0) ** 2 - (yte - p1) ** 2
            sse0 += ((yte - p0) ** 2).sum(); sse1 += ((yte - p1) ** 2).sum(); sst += (yte ** 2).sum()
            if rep == 0:
                for c in QCOLS:
                    _, p2 = oos_pred(trn, fo, yname, [q for q in QCOLS if q != c])
                    drop[c][fo] = ((yte - p2) ** 2) - ((yte - p1) ** 2)
        d_r2.append((sse0 - sse1) / sst)
        if rep == 0:
            mean_ld, se_ld = clmean(ld, d.niche1.values); drop0 = {c: clmean(v, d.niche1.values) for c, v in drop.items()}; var0 = sst / len(d)
    cv_rows.append(dict(y=yname, kind='5-fold x20 repeats, within-year', n=len(d), delta_r2_oos=float(np.mean(d_r2)),
                        delta_r2_sd_over_repeats=float(np.std(d_r2)), mse_gain_per_deal=mean_ld, mse_gain_cluster_se=se_ld,
                        within_year_var=float(var0), **{f'drop_one_mse_gain_{k}': v[0] for k, v in drop0.items()},
                        **{f'drop_one_mse_gain_se_{k}': v[1] for k, v in drop0.items()}))
    say(f'   {yname}: 5-fold x20: OOS within-year R2 gain of the quality block {np.mean(d_r2):+.4f} (sd over repeats {np.std(d_r2):.4f}); '
        f'per-deal MSE gain {mean_ld:.5f} (niche-cluster se {se_ld:.5f}); MSE rise when one proxy is dropped (niche-cluster se): '
        + ', '.join(f'{k} {v[0]:+.5f} ({v[1]:.5f})' for k, v in drop0.items()))
# growth on the 12-month-window (TTM-consistent) sales: does it predict out of sample there?
lg12 = np.zeros(len(I12))
for rep in range(5):
    perm = np.random.default_rng(800 + rep).permutation(len(I12))
    for fo in np.array_split(perm, 5):
        trn, tst = I12[np.setdiff1d(perm, fo)], I12[fo]
        yte, p1 = oos_pred(trn, tst, 'ls', QCOLS)
        _, p2 = oos_pred(trn, tst, 'ls', [q for q in QCOLS if q != 'grw_rev'])
        lg12[fo] += (((yte - p2) ** 2) - ((yte - p1) ** 2)) / 5
OOS12 = clmean(lg12, d.niche1.values[I12])
say(f'   12-month-window sales (n={len(I12)}): MSE rise when growth is dropped {OOS12[0]:+.5f} (niche-cluster se {OOS12[1]:.5f}), 5-fold x5')
tr_ = np.where(d.yr.values <= 2021)[0]; te_ = np.where(d.yr.values >= 2022)[0]
for yname in ['ls', 'la']:
    yte, p0 = oos_pred(tr_, te_, yname, [])
    _, p1 = oos_pred(tr_, te_, yname, QCOLS)
    ld = (yte - p0) ** 2 - (yte - p1) ** 2
    m_, se_ = clmean(ld, d.niche1.values[te_])
    e_tr, _, _ = ef_fit(tr_, yname); e_te, _, _ = ef_fit(te_, yname)
    g_tr, _ = ef_growth_variants(tr_); g_te, _ = ef_growth_variants(te_)
    cv_rows.append(dict(y=yname, kind='temporal: fit sold<=2021, test 2022-26', n_train=len(tr_), n_test=len(te_),
                        delta_r2_oos=float((((yte - p0) ** 2).sum() - ((yte - p1) ** 2).sum()) / (yte ** 2).sum()),
                        mse_gain_per_deal=m_, mse_gain_cluster_se=se_,
                        **{f'w_train_{k}': v / BEQ for k, v in e_tr.items()}, **{f'w_test_{k}': v / BEQ for k, v in e_te.items()},
                        w_train_grw_ttm12=g_tr[f'ttm12_{yname}'] / BEQ, w_test_grw_ttm12=g_te[f'ttm12_{yname}'] / BEQ))
    say(f'   {yname}: temporal holdout (train {len(tr_)} sold<=2021, test {len(te_)} sold 2022-26): OOS within-year R2 gain '
        f'{cv_rows[-1]["delta_r2_oos"]:+.4f}; per-deal MSE gain {m_:.5f} (se {se_:.5f})')
    say('      weights train / test: ' + ', '.join(f'{k} {e_tr[k] / BEQ:+.2f}/{e_te[k] / BEQ:+.2f}' for k in e_tr)
        + f'; growth on 12-month windows {g_tr[f"ttm12_{yname}"] / BEQ:+.2f}/{g_te[f"ttm12_{yname}"] / BEQ:+.2f}')
cv_tab = pd.DataFrame(cv_rows)

# ---- robustness: alternative proxies, samples, estimator ----
say('\n[EF] robustness (sale multiple, pricing-window basis; weights on the Main Street scale)')
rob = []
P_trend = [p if p[1] != 'grw' else ('grw_trend', 'grw', 'cont', +1) for p in PROX]
P_sop = [p if p[1] != 'mgt' else ('mgt_sop', 'mgt', 'flag', +1) for p in PROX]
P_recmon = [p if p[1] != 'rec' else ('rec_mon', 'rec', 'flag', +1) for p in PROX]
P_rectxt = [p if p[1] != 'rec' else ('rec_txt', 'rec', 'flag', +1) for p in PROX]
for lab, idx, prox, extra, base in [('base', ALL, PROX, (), None), ('grw: EF trend % instead of P&L growth', ALL, P_trend, ('grw_trend_miss',), None),
                                    ('mgt: SOPs instead of team', ALL, P_sop, (), None),
                                    ('rec: no business-model dummies', ALL, PROX, (), BASEIDX_NOCAT),
                                    ('rec: SaaS/Subscription model or MRR only', ALL, P_recmon, (), None),
                                    ('rec: summary wording only', ALL, P_rectxt, (), None),
                                    ('sold 2019+ only', np.where(d.yr.values >= 2019)[0], PROX, (), None),
                                    ('sold <= 2018 only', np.where(d.yr.values <= 2018)[0], PROX, (), None),
                                    ('content sites only', np.where(d.cat.values == 'content')[0], PROX, (), None),
                                    ('Amazon FBA + ecommerce only', np.where(d.cat.isin(['amazon_fba', 'ecommerce']).values)[0], PROX, (), None)]:
    est, bq, _ = ef_fit(idx, 'ls', prox, extra, base)
    rob.append(dict(variant=lab, n=len(idx), **{k: v / BEQ for k, v in est.items()}))
    say(f'   {lab:42s} n={len(idx):5d} ' + ', '.join(f'{k} {v / BEQ:+.2f}' for k, v in est.items()))
Xh = XALL[BASECOLS + QCOLS]
mh = sm.RLM(d.ls.values, Xh, M=sm.robust.norms.HuberT()).fit()
esth = {dim: sign * mh.params[col] * unit_of(col, kind, ALL) for col, dim, kind, sign in PROX}
rob.append(dict(variant='Huber-robust', n=len(d), **{k: v / BEQ for k, v in esth.items()}))
say(f'   {"Huber-robust":42s} n={len(d):5d} ' + ', '.join(f'{k} {v / BEQ:+.2f}' for k, v in esth.items()))
rob = pd.DataFrame(rob)
# analytic SEs of the rec variants (used in the specification bracket)
REC_VAR = {}
for lab, cols in [('EF rec: no business-model dummies', [c for c in BASECOLS if not c.startswith('cat_')] + QCOLS),
                  ('EF rec: model or MRR only', BASECOLS + [c if c != 'rec_flag' else 'rec_mon' for c in QCOLS])]:
    rc = 'rec_mon' if 'rec_mon' in cols else 'rec_flag'
    p_, se_, _ = sm_fit(ALL, 'ls', cols)
    u = unit_of(rc, 'flag', ALL)
    REC_VAR[lab] = (float(p_[rc] * u / BEQ), float(se_[rc] * u / BEQ))
say('   rec variants with SEs: ' + ', '.join(f'{k} {v[0]:+.2f} (se {v[1]:.2f})' for k, v in REC_VAR.items()))
NFE_REC = niche_fe(ALL, 'ls', 'rec_flag', unit_of('rec_flag', 'flag', ALL))
say(f'   primary-niche fixed effects ({NFE_REC[2]} niches): rec {NFE_REC[0]:+.2f} (se {NFE_REC[1]:.2f}); growth on 12-month windows {NFE_G12[0]:+.2f} (se {NFE_G12[1]:.2f})')

# ---- recurring revenue by price type and era (review 2: is there a SALE-price premium at all?) ----
# sale, last ask and sale/ask on the same design; all windows and 12-month windows; era-specific slopes on the sale
# multiple (one regression, flag converted with the era's own share). SE: max of niche-, quarter-clustered and HC1.
rec_rows = []
u_rec = unit_of('rec_flag', 'flag', ALL)
for lab, idx in [('all sales', ALL), ('12-month windows', I12)]:
    u_ = unit_of('rec_flag', 'flag', idx)
    for yname, ylab in [('ls', 'sale'), ('la', 'last ask'), ('lr', 'sale minus ask')]:
        p_, se_, _ = sm_fit(idx, yname, BASECOLS + QCOLS)
        rec_rows.append(dict(sample=lab, price=ylab, era='all', n=len(idx), n_flagged=int(d.rec_flag.values[idx].sum()),
                             w=float(p_['rec_flag'] * u_ / BEQ), w_se=float(se_['rec_flag'] * u_ / BEQ)))
REC_ERAS = [('2014-18', 2000, 2018), ('2019-21', 2019, 2021), ('2022-26', 2022, 2030)]
for lab_, a_, b_ in REC_ERAS: d[f'r_era_{lab_}'] = d.rec_flag * ((d.yr >= a_) & (d.yr <= b_))
XR = design(d, [c for c in QCOLS if c != 'rec_flag'] + [f'r_era_{lab_}' for lab_, _, _ in REC_ERAS])
for yname, ylab in [('ls', 'sale'), ('la', 'last ask')]:
    fr = [sm.OLS(d[yname].values, XR).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d[g])[0]}) for g in ['niche1', 'qtr']]
    fr.append(sm.OLS(d[yname].values, XR).fit(cov_type='HC1'))
    for lab_, a_, b_ in REC_ERAS:
        sel = ((d.yr >= a_) & (d.yr <= b_)).values; c_ = f'r_era_{lab_}'
        u_ = 1 / gap(float(d.rec_flag.values[sel].mean()))
        rec_rows.append(dict(sample='all sales', price=ylab, era=lab_, n=int(sel.sum()), n_flagged=int(d.rec_flag.values[sel].sum()),
                             w=float(fr[0].params[c_] * u_ / BEQ), w_se=float(max(f_.bse[c_] for f_ in fr) * u_ / BEQ)))
rec_tab = pd.DataFrame(rec_rows)
rec_tab['z'] = rec_tab.w / rec_tab.w_se
say('   recurring revenue by price type (Main Street scale; z): ' + '; '.join(
    f'{rr["sample"]}/{rr.price}/{rr.era} {rr.w:+.2f} (se {rr.w_se:.2f}, z {rr.z:+.1f}, flagged {rr.n_flagged})' for _, rr in rec_tab.iterrows()))
RT = rec_tab.set_index(['sample', 'price', 'era'])
REC_SALE_MAXZ = float(rec_tab[rec_tab.price == 'sale'].z.max())
REC_ASK_MINZ = float(rec_tab[(rec_tab.price == 'last ask') & (rec_tab.era == 'all')].z.min())
say(f'   largest z of the recurring flag on SALE prices in any EF sample or era: {REC_SALE_MAXZ:+.2f}; smallest z on the last ASK '
    f'(all eras): {REC_ASK_MINZ:+.2f}: the premium is in asking prices, not in sale prices')
# is EF growth positive in EVERY specification? (review 2: the direction claim rests on EF alone)
EF_GRW_SPECS = ([(f'basis: {r_.variant}', r_.w) for _, r_ in gb_tab.iterrows()] + [(f'era {r_.era}', r_.w) for _, r_ in era_tab.iterrows()]
                + [(f'robustness: {r_.variant}', r_.grw) for _, r_ in rob.iterrows()]
                + [(f'temporal {a_} {r_.y}', r_[f'w_{a_}_grw']) for _, r_ in cv_tab[cv_tab.kind.str.startswith('temporal')].iterrows() for a_ in ('train', 'test')])
QUINT_POS = bool(all(e_ > 0 for e_ in quint['effect'][1:]))
EF_GRW_POS = bool(all(v_ > 0 for _, v_ in EF_GRW_SPECS) and QUINT_POS)
EF_GRW_MIN = min(EF_GRW_SPECS, key=lambda t: t[1])
say(f'   EF growth weight positive in every one of {len(EF_GRW_SPECS)} specifications (bases, scales, eras, robustness, temporal halves) and in all four '
    f'quintile contrasts: {EF_GRW_POS}; smallest weight {EF_GRW_MIN[0]} {EF_GRW_MIN[1]:+.3f}')

# ================================================================== 2. FLIPPA 2026 recently sold (micro deals)
say('\n[Flippa] 2026 recently sold')
f = pd.read_csv(FLP, low_memory=False)
f['price'] = np.where(f.sale_method == 'auction', f.final_bid_usd, f.final_ask_usd)
f['ap'] = f.annual_profit_usd_card
f = f[(f.price > 0) & (f.ap > 0) & f.sale_method.isin(['auction', 'classified'])].copy()
f['ly'] = np.log(f.price / f.ap)
f = f[(f.ly > np.log(.1)) & (f.ly < np.log(20))].copy()
f['lap'] = np.log(f.ap); f['lap_c'] = f.lap - f.lap.median(); f['lap2'] = f.lap_c ** 2
f['auction'] = (f.sale_method == 'auction').astype(float)
f['l_age'] = np.log1p(f.age_years.clip(0, 25))
f['l_txt'] = np.log1p((f.summary.fillna('') + ' ' + f.description.fillna('')).str.len())
ftl = (f.summary.fillna('') + ' ' + f.description.fillna('')).str.lower()
f['kw_rec_strict'] = ftl.str.contains(r'recurring|subscription|\bmrr\b|\barr\b|retainer', regex=True).astype(float)
FPROX = [('kw_recurring', 'rec', +1), ('kw_team', 'mgt', +1), ('kw_passive', 'own', +1), ('kw_owner_heavy', 'own', -1),
         ('kw_growth', 'grw', +1), ('kw_decline', 'grw', -1)]


def fl_design(x, q):
    X = pd.concat([pd.get_dummies(x[['type', 'industry']].fillna('na').astype(str), drop_first=True, dtype=float)], axis=1)
    for c in ['lap_c', 'lap2', 'auction', 'l_age', 'l_txt'] + q: X[c] = x[c].fillna(0).values
    X.insert(0, 'const', 1.0)
    return X


def fl_pipeline(x):
    q = [p[0] for p in FPROX]
    X = fl_design(x, q); b, _ = ols(x.ly.values, X.values)
    _, e0 = ols(x.ly.values, fl_design(x, []).values)
    bq = beq_from_resid(e0)
    out = {}
    for col, dim, sign in FPROX:
        p = float(x[col].fillna(0).mean())
        e = sign * b[list(X.columns).index(col)] / gap(p) if 0 < p < 1 else np.nan
        out[col] = (dim, e, e / bq)
    return out, bq


mf = sm.OLS(f.ly.values, fl_design(f, [p[0] for p in FPROX])).fit(cov_type='HC1')
fl_est, fl_bq = fl_pipeline(f)
FB = []
for bi in range(NB):
    ib = np.random.default_rng(9000 + bi).integers(0, len(f), len(f))
    o, _ = fl_pipeline(f.iloc[ib].reset_index(drop=True))
    FB.append([o[c][1] for c, _, _ in FPROX] + [o[c][2] for c, _, _ in FPROX])
FB = np.array(FB)
nF = len(FPROX)
fl_rows = []
for j, (col, dim, sign) in enumerate(FPROX):
    sh = float(f[col].fillna(0).mean())
    se_an = mf.bse[col] / gap(sh) / BEQ
    se_bs = float(np.nanstd(FB[:, j], ddof=1)) / BEQ
    fl_rows.append(dict(source='Flippa', proxy=col, dim=dim, coef=mf.params[col], se_hc1=mf.bse[col], share=sh, n_flagged=int(f[col].fillna(0).sum()),
                        per_sd=fl_est[col][1], w=fl_est[col][1] / BEQ, w_se_boot=se_bs, w_se_analytic=se_an, w_se=max(se_bs, se_an),
                        w_ownspread=fl_est[col][2], w_ownspread_se=float(np.nanstd(FB[:, nF + j], ddof=1)), n=len(f)))
fl_tab = pd.DataFrame(fl_rows)
N_AUC, N_ASK = int(f.auction.sum()), int((1 - f.auction).sum())
say(f'   n={len(f)} prices: {N_AUC} auction sale prices and {N_ASK} classified FINAL ASKS ({N_ASK / len(f):.0%}; not sale prices); R2 {mf.rsquared:.3f}; '
    f'resid sd {np.sqrt(mf.scale):.3f}; beq_src {fl_bq:.4f}')
say(fl_tab.round(3).to_string(index=False))
fl_gain = []
for rep_ in range(20):
    perm = np.random.default_rng(700 + rep_).permutation(len(f)); folds = np.array_split(perm, 5)
    X1 = fl_design(f, [p[0] for p in FPROX]).values; X0 = fl_design(f, []).values; yy = f.ly.values
    s0 = s1 = 0.0
    for fo in folds:
        trn = np.setdiff1d(perm, fo)
        b0, _ = ols(yy[trn], X0[trn]); b1, _ = ols(yy[trn], X1[trn])
        s0 += ((yy[fo] - X0[fo] @ b0) ** 2).sum(); s1 += ((yy[fo] - X1[fo] @ b1) ** 2).sum()
    fl_gain.append((s0 - s1) / ((yy - yy.mean()) ** 2).sum())
say(f'   Flippa 5-fold x20 OOS R2 gain of the keyword block {np.mean(fl_gain):+.4f} (sd over repeats {np.std(fl_gain):.4f})')
FL = {}
for dim in ['rec', 'mgt', 'own', 'grw']:
    s_ = fl_tab[(fl_tab.dim == dim) & fl_tab.w_se.notna() & (fl_tab.n_flagged >= 15)]
    if len(s_):
        wv = 1 / s_.w_se ** 2; wo = 1 / s_.w_ownspread_se ** 2
        FL[dim] = (float((s_.w * wv).sum() / wv.sum()), float(wv.sum() ** -.5),
                   float((s_.w_ownspread * wo).sum() / wo.sum()), float(wo.sum() ** -.5))
say('   pooled per dimension (flags with >= 15 listings; Main Street scale): ' + ', '.join(f'{k} {v[0]:+.2f} (se {v[1]:.2f})' for k, v in FL.items()))
# recurring flag: which prices and which wording carry the premium (review)
FLV = {}
for lab, ff, col in [('all prices, kw_recurring (as pooled)', f, 'kw_recurring'), ('all prices, strict recurring/subscription/MRR/ARR/retainer', f, 'kw_rec_strict'),
                     ('auction sale prices only, kw_recurring', f[f.auction == 1], 'kw_recurring'), ('classified final asks only, kw_recurring', f[f.auction == 0], 'kw_recurring')]:
    q_ = [col] + [p[0] for p in FPROX if p[0] != 'kw_recurring']
    Xf = fl_design(ff, q_); Xf = Xf.loc[:, (Xf.std() > 0) | (Xf.columns == 'const')]
    mm = sm.OLS(ff.ly.values, Xf).fit(cov_type='HC1'); p_ = float(ff[col].fillna(0).mean())
    FLV[lab] = (float(mm.params[col] / gap(p_) / BEQ), float(mm.bse[col] / gap(p_) / BEQ), len(ff), int(ff[col].fillna(0).sum()))
say('   Flippa recurring flag by price type and wording: ' + '; '.join(f'{k}: {v[0]:+.2f} (se {v[1]:.2f}; n {v[2]}, flagged {v[3]})' for k, v in FLV.items()))

# ================================================================== 3. DEALLEDGER (settled pipeline, reproduced)
say('\n[DealLedger] reproducing fit/quality_weights.py')
dl = pd.read_pickle(DLP); dl = dl[dl.has_desc == 1].copy()
feats = ['absentee', 'owner_op', 'recurring', 'growth', 'repeat', 'books', 'staff_in', 'realestate', 'sba', 'franchise', 'relocatable']
dl['hinge'] = np.maximum(0, dl.lcf - np.log(3e5))
inds = sorted(dl.ind.unique()); D = pd.get_dummies(dl.ind)[[i for i in inds if i != 'other']].astype(float)
cl = pd.factorize(dl.broker.fillna('na'))[0]


def huber(X, y, c=1.345, it=40):
    X = np.column_stack([np.ones(len(X)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(it):
        e = y - X @ b; s = np.median(np.abs(e)) / 0.6745; u = np.abs(e) / (c * s); w = np.where(u <= 1, 1, 1 / u); W = np.sqrt(w)
        b = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)[0]
    return b


def dl_fit(fl):
    X = np.column_stack([dl[['lcf', 'hinge'] + fl].values, D.values]); y = dl.ly.values
    b = huber(X, y); rg = np.random.default_rng(1); ub = np.unique(cl); B = []
    for _ in range(150):
        pick = rg.choice(ub, len(ub)); idx = np.concatenate([np.where(cl == g)[0] for g in pick]); B.append(huber(X[idx], y[idx], it=25))
    B = np.array(B); se = B.std(0)
    Xb = np.column_stack([np.ones(len(X)), X]); e = y - Xb @ b
    # bootstrap draws per phrase as well (same seed in every call, so draws are aligned across calls: joint distribution)
    return {f_: (float(b[3 + i]), float(se[3 + i])) for i, f_ in enumerate(fl)}, e, {f_: B[:, 3 + i] for i, f_ in enumerate(fl)}


dcoef, dl_res, DLB = dl_fit(feats)
dcoef_x, _, DLBX = dl_fit(feats + ['diversified', 'concentr', 'decline'])
dl_beq_own = beq_from_resid(dl_res)
DLMAP = [('own', 'owner_op', -1, dcoef), ('mgt', 'staff_in', +1, dcoef), ('rec', 'recurring', +1, dcoef),
         ('grw', 'growth', +1, dcoef), ('fin', 'books', +1, dcoef), ('cc', 'diversified', +1, dcoef_x), ('ret', 'repeat', +1, dcoef)]
dl_rows = []
for dim, ph, sign, cf in DLMAP:
    p = float(dl[ph].mean()); g_ = gap(p); b_, s_ = cf[ph]
    dl_rows.append(dict(source='DealLedger', dim=dim, phrase=ph, share=p, coef=b_, se=s_, per_sd=sign * b_ / g_,
                        w=sign * b_ / g_ / BEQ, w_se=s_ / g_ / BEQ, w_ownspread=sign * b_ / g_ / dl_beq_own, w_ownspread_se=s_ / g_ / dl_beq_own,
                        used=dim != 'ret', n=len(dl)))
dl_tab = pd.DataFrame(dl_rows)
say(dl_tab.round(3).to_string(index=False))
ub = np.unique(cl); fold_of = {g: i % 5 for i, g in enumerate(np.random.default_rng(11).permutation(ub))}
fid = np.array([fold_of[g] for g in cl])
X1 = np.column_stack([dl[['lcf', 'hinge'] + feats].values, D.values]); X0 = np.column_stack([dl[['lcf', 'hinge']].values, D.values]); yy = dl.ly.values
ae = np.zeros(len(dl)); se2 = np.zeros(len(dl))
for k_ in range(5):
    tr, te = fid != k_, fid == k_
    b0 = huber(X0[tr], yy[tr]); b1 = huber(X1[tr], yy[tr])
    e0 = yy[te] - np.column_stack([np.ones(te.sum()), X0[te]]) @ b0; e1 = yy[te] - np.column_stack([np.ones(te.sum()), X1[te]]) @ b1
    ae[te] = np.abs(e0) - np.abs(e1); se2[te] = e0 ** 2 - e1 ** 2
dl_mae_gain, dl_mae_se = clmean(ae, cl)
dl_mse_gain, dl_mse_se = clmean(se2, cl)
say(f'   DealLedger broker-grouped 5-fold: OOS MAE gain of the phrase block {dl_mae_gain:+.4f} (broker-cluster se {dl_mae_se:.4f}), '
    f'MSE gain {dl_mse_gain:+.4f} (se {dl_mse_se:.4f})')
dl_drop = {}
for ph in ['owner_op', 'staff_in', 'recurring', 'growth', 'books']:
    keep_ = [c for c in feats if c != ph]
    X2 = np.column_stack([dl[['lcf', 'hinge'] + keep_].values, D.values]); ad = np.zeros(len(dl))
    for k_ in range(5):
        tr, te = fid != k_, fid == k_
        b1 = huber(X1[tr], yy[tr]); b2 = huber(X2[tr], yy[tr])
        e1 = yy[te] - np.column_stack([np.ones(te.sum()), X1[te]]) @ b1; e2 = yy[te] - np.column_stack([np.ones(te.sum()), X2[te]]) @ b2
        ad[te] = np.abs(e2) - np.abs(e1)
    dl_drop[ph] = clmean(ad, cl)
say('   DealLedger OOS MAE rise when one phrase is dropped (positive = the phrase predicts out of sample): '
    + ', '.join(f'{k} {v[0]:+.5f} (se {v[1]:.5f})' for k, v in dl_drop.items()))
say(f'   DealLedger own residual-spread beq {dl_beq_own:.4f} vs Main Street band beq {BEQ:.4f}; '
    f'reproduction check own raw {dl_tab.w[0]:.3f} (settled 1.371), mgt raw {dl_tab.w[1]:.3f} (settled 0.482)')
assert abs(dl_tab.w[0] - 1.371) < 5e-4 and abs(dl_tab.w[1] - 0.482) < 5e-4

# ================================================================== 4. GF DATA (check only)
gf = pd.read_csv(GFD)
gfa = gf[gf.segment == 'all buyouts'].copy()
gfa['lp'] = np.log1p(gfa.premium_pct / 100)
hist = gfa[gfa.period == '2003-2020 avg'].iloc[0]
yrs_ = gfa[gfa.period.isin(['2021', '2022', '2023', '2024', '2025'])]
p_aafp = float(yrs_.aafp_share_pct.mean() / 100)
eff_joint = float(hist.lp / gap(hist.aafp_share_pct / 100))
eff_joint_lo = float(yrs_.lp.min() / gap(p_aafp)); eff_joint_hi = float(yrs_.lp.max() / gap(p_aafp))
GF = dict(half=eff_joint / sqrt(2) / BEQ, all=eff_joint / BEQ, half_lo=eff_joint_lo / sqrt(2) / BEQ, half_hi=eff_joint_hi / sqrt(2) / BEQ,
          all_lo=eff_joint_lo / BEQ, all_hi=eff_joint_hi / BEQ)
say(f'\n[GF Data] AAFP (growth & EBITDA margin >= 10%) premium 2003-20 avg {hist.premium_pct}% at share {hist.aafp_share_pct}%: growth weight '
    f'{GF["half"]:.2f} equal shares if half the joint latent is growth (2021-25 range {GF["half_lo"]:.2f}-{GF["half_hi"]:.2f}), {GF["all"]:.2f} if all of it '
    f'(2021-25 range {GF["all_lo"]:.2f}-{GF["all_hi"]:.2f}). Check only: growth and EBITDA margin are confounded there.')

# ================================================================== 5. COMBINE
say('\n[combine]')
SCREEN = {('EF sale', 'own'): 'EF owner hours: median 3 h/week, outside the Main Street range of owner dependence',
          ('EF sale', 'mgt'): 'EF team = freelancers/VAs already costed in net profit, not management depth',
          ('Flippa', 'own'): 'Flippa micro deals: passive/owner-heavy wording, outside the Main Street range',
          ('Flippa', 'mgt'): 'Flippa team wording = freelancers, not management depth',
          ('EF sale, window basis', 'grw'): "EF's pricing-window earnings, not the console's twelve-month earnings (replaced by the 12-month-window estimate)"}
w12 = R_12['w']; w12_se = R_12['w_se']
w12_os = GV['ttm12_ls'] / GV['ttm12_beq_src']; w12_os_se = float((BSG.ttm12_ls / BSG.ttm12_beq_src).std(ddof=1))
src = []
for _, rr in efw.iterrows():
    if rr.dim == 'grw':
        src.append(dict(source='EF sale', dim='grw', cls='analog', w=w12, se=w12_se, w_os=w12_os, se_os=w12_os_se,
                        w_ask=R_12A['w'], se_ask=R_12A['w_se']))
        src.append(dict(source='EF sale, window basis', dim='grw', cls='analog', w=R_WIN['w'], se=R_WIN['w_se'], w_os=rr.w_sale_ownspread,
                        se_os=rr.w_sale_ownspread_se, w_ask=rr.w_ask, se_ask=rr.w_ask_se))
        continue
    src.append(dict(source='EF sale', dim=rr.dim, cls='analog', w=rr.w_sale, se=rr.w_sale_se, w_os=rr.w_sale_ownspread, se_os=rr.w_sale_ownspread_se,
                    w_ask=rr.w_ask, se_ask=rr.w_ask_se))
for dim, (w_, s_, wo_, so_) in FL.items():
    src.append(dict(source='Flippa', dim=dim, cls='analog', w=w_, se=s_, w_os=wo_, se_os=so_, w_ask=w_, se_ask=s_))
for _, rr in dl_tab[dl_tab.used].iterrows():
    src.append(dict(source='DealLedger', dim=rr.dim, cls='main_settled' if rr.dim in ('own', 'mgt') else 'main_text', w=rr.w, se=rr.w_se,
                    w_os=rr.w_ownspread, se_os=rr.w_ownspread_se, w_ask=rr.w, se_ask=rr.w_se))
src = pd.DataFrame(src)
src['screened_out'] = [SCREEN.get((a, b), '') for a, b in zip(src.source, src.dim)]
src['pooled'] = src.screened_out == ''
say(src.round(3).to_string(index=False))


def mom_tau(S, dims, wcol='w', scol='se'):
    dd = []
    for k in dims:
        a = S[(S.source == 'EF sale') & (S.dim == k)].iloc[0]; b = S[(S.source == 'DealLedger') & (S.dim == k)].iloc[0]
        dd.append((a[wcol] - b[wcol]) ** 2 - a[scol] ** 2 - b[scol] ** 2)
    return sqrt(max(0.0, float(np.mean(dd)))) if dd else 0.0


S_ef = src[src.source == 'EF sale']; S_dl = src[src.source == 'DealLedger']
both_used = sorted(set(S_ef[S_ef.pooled].dim) & set(S_dl.dim))
both_all = sorted(set(S_ef.dim) & set(S_dl.dim))
tau_mom = mom_tau(src, both_used)
tau_mom_all = mom_tau(src, both_all)
tau_mom_os = mom_tau(src, both_used, 'w_os', 'se_os')
TAU = max(tau_mom, TAU_FLOOR)
say(f'   transfer/validity sd: method of moments, EF vs DealLedger on pooled dims {both_used}: {tau_mom:.3f} (on the own-spread scale {tau_mom_os:.3f}: '
    f'the agreement depends on the scale anchor); used tau = max(that, {TAU_FLOOR}) = {TAU:.3f}. On all shared dims {both_all} '
    f'(incl. the screened own/mgt proxies): {tau_mom_all:.3f}; the reviewers\' {TAU_REVIEW} is reported as a headline sensitivity')


def pool(dim, tau=TAU, S=None, sources=None, wcol='w', scol='se', screened=True):
    s = (src if S is None else S)
    s = s[(s.dim == dim) & (s.source != 'EF sale, window basis')]     # an alternative basis, never pooled alongside the primary
    if screened: s = s[s.pooled]
    if sources is not None: s = s[s.source.isin(sources)]
    if not len(s): return dict(m=np.nan, se=np.inf, post=1.0, post_se=PRIOR_SD, n_src=0, main=False)
    v = s[scol].values ** 2 + np.where(s.cls.values == 'main_settled', 0.0, tau ** 2)
    wv = 1 / v
    m = float((s[wcol].values * wv).sum() / wv.sum()); se = float(wv.sum() ** -.5)
    w0 = 1 / PRIOR_SD ** 2
    return dict(m=m, se=se, post=float((w0 + wv.sum() * m) / (w0 + wv.sum())), post_se=float((w0 + wv.sum()) ** -.5),
                n_src=int(s.source.nunique()), main=bool(s.source.eq('DealLedger').any()))


def with_row(source, dim, w, se, S=None):
    """copy of the source table with one estimate replaced (w and se, on every scale column)"""
    S = (src if S is None else S).copy()
    m_ = (S.source == source) & (S.dim == dim)
    assert m_.sum() == 1, (source, dim)
    S.loc[m_, ['w', 'w_ask', 'w_os']] = w; S.loc[m_, ['se', 'se_ask', 'se_os']] = se
    return S


# EF growth in the console's own units (per 13 points of growth) on the 12-month windows, and the displayed-trend reliability
obs_both = (d.grw_miss == 0) & (d.grw_trend_miss == 0)
rel_grw = float(np.corrcoef(d.grw_rev[obs_both], d.grw_trend[obs_both])[0, 1])
W_UNITS = (R_12['w_console_units'], R_12['w_console_units_se'])
say(f'   EF growth in console units (per {CONSOLE_GRW_SD:.2f} of growth) on 12-month windows: {W_UNITS[0]:.3f} (se {W_UNITS[1]:.3f}); window basis '
    f'{R_WIN["w_console_units"]:.3f}; TTM re-based {R_TTM["w_console_units"]:.3f}. Correlation of P&L growth with EF\'s displayed trend {rel_grw:.2f} '
    '(measured growth is noisy, so every EF growth weight is attenuated)')

# ---- specification set (review): each spec changes one source estimate or the scale; the ratio and the absolute
# posterior of rec and grw are recomputed under every spec ----
SPECS = {'primary': dict(S=src)}
SPECS[f'tau {TAU_REVIEW}'] = dict(S=src, tau=TAU_REVIEW)
SPECS['tau 0 (no transfer variance)'] = dict(S=src, tau=0.0)
SPECS['own-spread scale, all sources'] = dict(S=src, wcol='w_os', scol='se_os')
SPECS['EF ask instead of sale'] = dict(S=src, wcol='w_ask', scol='se_ask')
SPECS['EF growth: pricing-window basis'] = dict(S=with_row('EF sale', 'grw', R_WIN['w'], R_WIN['w_se']), only=('grw',))
SPECS['EF growth: interaction at 12'] = dict(S=with_row('EF sale', 'grw', R_INT['w'], R_INT['w_se']), only=('grw',))
SPECS['EF growth: TTM re-based'] = dict(S=with_row('EF sale', 'grw', R_TTM['w'], R_TTM['w_se']), only=('grw',))
SPECS['EF growth: console units'] = dict(S=with_row('EF sale', 'grw', W_UNITS[0], W_UNITS[1]), only=('grw',))
SPECS['EF growth: 12-month windows, own-sample sd'] = dict(S=with_row('EF sale', 'grw', R_12OS['w'], R_12OS['w_se']), only=('grw',))
SPECS['EF growth: rank-normal'] = dict(S=with_row('EF sale', 'grw', R_RN12['w'], R_RN12['w_se']), only=('grw',))
SPECS['EF growth: IQR scale'] = dict(S=with_row('EF sale', 'grw', R_12I['w'], R_12I['w_se']), only=('grw',))
SPECS['EF growth: sold 2022-26'] = dict(S=with_row('EF sale', 'grw', R_22['w'], R_22['w_se']), only=('grw',))
SPECS['EF: primary-niche fixed effects (rec, grw)'] = dict(S=with_row('EF sale', 'rec', *NFE_REC[:2], S=with_row('EF sale', 'grw', *NFE_G12[:2])),
                                                          only=('rec', 'grw'))
SPECS['EF: niche fixed effects and own-sample growth sd'] = dict(
    S=with_row('EF sale', 'rec', *NFE_REC[:2], S=with_row('EF sale', 'grw', NFE_G12[0] * sd12 / SD_G, NFE_G12[1] * sd12 / SD_G)), only=('rec', 'grw'))
SPECS['EF rec: no business-model dummies'] = dict(S=with_row('EF sale', 'rec', *REC_VAR['EF rec: no business-model dummies']), only=('rec',))
SPECS['EF rec: model or MRR only'] = dict(S=with_row('EF sale', 'rec', *REC_VAR['EF rec: model or MRR only']), only=('rec',))
SPECS['EF rec: 12-month windows'] = dict(S=with_row('EF sale', 'rec', RT.w[('12-month windows', 'sale', 'all')], RT.w_se[('12-month windows', 'sale', 'all')]), only=('rec',))
SPECS['Flippa rec: strict wording'] = dict(S=with_row('Flippa', 'rec', *FLV['all prices, strict recurring/subscription/MRR/ARR/retainer'][:2]), only=('rec',))
SPECS['Flippa rec: auction sale prices only'] = dict(S=with_row('Flippa', 'rec', *FLV['auction sale prices only, kw_recurring'][:2]), only=('rec',))
SPECS['Flippa rec: final asks only'] = dict(S=with_row('Flippa', 'rec', *FLV['classified final asks only, kw_recurring'][:2]), only=('rec',))
SPECS['without Flippa'] = dict(S=src, sources=['EF sale', 'DealLedger'])
SPECS['analogs only (no DealLedger text)'] = dict(S=src, sources=['EF sale', 'Flippa'])


def nine(spec):
    kw = {k: v for k, v in spec.items() if k in ('S', 'tau', 'wcol', 'scol', 'sources')}
    return {k: pool(k, **kw) for k in DIMS}


def dl_re(m, s):
    """DerSimonian-Laird random-effects common level of estimates m with SEs s"""
    m = np.asarray(m, float); s = np.asarray(s, float)
    w = 1 / s ** 2; mfe = (w * m).sum() / w.sum(); Q = float((w * (m - mfe) ** 2).sum()); k = len(m)
    C = w.sum() - (w ** 2).sum() / w.sum(); t2 = max(0.0, (Q - (k - 1)) / C)
    wr = 1 / (s ** 2 + t2)
    return dict(mu=float((wr * m).sum() / wr.sum()), se=float(wr.sum() ** -.5), Q=Q, df=k - 1, p=float(1 - stats.chi2.cdf(Q, k - 1)),
                tau=sqrt(t2), I2=float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0)


# ---- joint sampling distribution of the nine pooled estimates (review 2): EF proxies come from one regression, the
# DealLedger phrases from another, the Flippa flags from a third, so estimates from one source are correlated across
# dimensions. Within-source correlations from each source's own bootstrap (EF niche-cluster draws, with the 12-month
# growth estimate on the same draws; DealLedger broker-cluster draws, aligned across its two regressions by the common
# seed; Flippa row draws), scaled to the SEs actually used. Transfer variance tau^2 is dimension-specific (independent).
EF_DRAWS = pd.DataFrame({dim: BS['ls'][:, j] / BEQ for j, dim in enumerate(DIMS_EF)})
EF_DRAWS['grw'] = BSG['ttm12_ls'].values / BEQ
DL_DRAWS = pd.DataFrame({dim: sign * (DLB if cf is dcoef else DLBX)[ph] / gap(float(dl[ph].mean())) / BEQ for dim, ph, sign, cf in DLMAP})
FL_DRAWS = {}
for dim in FL:
    s_ = fl_tab[(fl_tab.dim == dim) & fl_tab.w_se.notna() & (fl_tab.n_flagged >= 15)]
    wv_ = (1 / s_.w_se ** 2).values; js_ = [[p[0] for p in FPROX].index(c) for c in s_.proxy]
    FL_DRAWS[dim] = (FB[:, js_] / BEQ) @ wv_ / wv_.sum()
FL_DRAWS = pd.DataFrame(FL_DRAWS)
SRC_CORR = {'EF sale': EF_DRAWS.corr(), 'DealLedger': DL_DRAWS.corr(), 'Flippa': FL_DRAWS.corr()}


def pooled_cov(S=None, tau=TAU, independent=False):
    """covariance of the nine pooled-data estimates of pool() (primary pooling rules)"""
    S = (src if S is None else S)
    S = S[S.pooled & (S.source != 'EF sale, window basis')]
    om = {}
    for k in DIMS:
        s_ = S[S.dim == k]
        v_ = s_.se.values ** 2 + np.where(s_.cls.values == 'main_settled', 0.0, tau ** 2)
        om[k] = {r_.source: (1 / v_[i]) / (1 / v_).sum() for i, (_, r_) in enumerate(s_.iterrows())}
    se_of = {(r_.source, r_.dim): r_.se for _, r_ in S.iterrows()}
    cls_of = {(r_.source, r_.dim): r_.cls for _, r_ in S.iterrows()}
    C = np.zeros((len(DIMS), len(DIMS)))
    for i, k in enumerate(DIMS):
        for j, l in enumerate(DIMS):
            for s_name in sorted(set(om[k]) & set(om[l])):     # sorted: deterministic summation order (string hashing is randomised)
                if i == j:
                    C[i, i] += om[k][s_name] ** 2 * (se_of[(s_name, k)] ** 2 + (0.0 if cls_of[(s_name, k)] == 'main_settled' else tau ** 2))
                elif not independent:
                    C[i, j] += om[k][s_name] * om[l][s_name] * float(SRC_CORR[s_name].loc[k, l]) * se_of[(s_name, k)] * se_of[(s_name, l)]
    return C


def ratio_sim(vec, cov=None, ref=None, nsim=4000, seed=7):
    """ratio of each dimension's pooled estimate to the random-effects common level of the OTHER measured dimensions (all
    eight, or those in ref); the Main Street anchor cancels. Interval by simulation of the nine estimates: joint normal
    with covariance cov (pooled_cov), or independent normal draws when cov is None."""
    m = np.array([vec[k]['m'] for k in DIMS]); s = np.array([vec[k]['se'] for k in DIMS])
    if cov is not None: assert np.allclose(np.sqrt(np.diag(cov)), s, rtol=1e-9), 'pooled_cov diagonal must equal the pooled SEs'
    L = np.linalg.cholesky(cov) if cov is not None else np.diag(s)
    others = {i: [j for j, kk in enumerate(DIMS) if j != i and (ref is None or kk in ref)] for i in range(len(DIMS))}
    pt = {k: m[i] / dl_re(m[others[i]], s[others[i]])['mu'] for i, k in enumerate(DIMS)}
    rg = np.random.default_rng(seed); R = np.zeros((nsim, len(DIMS)))
    for j in range(nsim):
        mm = m + L @ rg.standard_normal(len(DIMS))
        for i in range(len(DIMS)): R[j, i] = mm[i] / dl_re(mm[others[i]], s[others[i]])['mu']
    return {k: dict(r=float(pt[k]), lo=float(np.percentile(R[:, i], 2.5)), hi=float(np.percentile(R[:, i], 97.5)),
                    p_below_1=float((R[:, i] < 1).mean())) for i, k in enumerate(DIMS)}


spec_rows = []
for lab, sp in SPECS.items():
    vec = nine(sp)
    dk = [k for k in DIMS if np.isfinite(vec[k]['m'])]          # a spec that drops a source can leave a dimension unmeasured
    m = [vec[k]['m'] for k in dk]; s = [vec[k]['se'] for k in dk]
    re_all = dl_re(m, s)
    for k in dk:
        if sp.get('only') is not None and k not in sp['only']: continue
        i = dk.index(k)
        mu_o = dl_re(np.delete(m, i), np.delete(s, i))['mu']
        spec_rows.append(dict(spec=lab, dim=k, data_mean=vec[k]['m'], data_se=vec[k]['se'], posterior=vec[k]['post'], posterior_se=vec[k]['post_se'],
                              common_level_others=mu_o, ratio=vec[k]['m'] / mu_o, common_level_all=re_all['mu'], ratio_all9=vec[k]['m'] / re_all['mu'],
                              Q=re_all['Q'], Q_p=re_all['p']))
spec_tab = pd.DataFrame(spec_rows)
say('   specification set (pooled data mean, posterior, ratio to the common level of the other eight):')
for _, rr in spec_tab[spec_tab.dim.isin(['rec', 'grw'])].iterrows():
    say(f'      {rr.dim} {rr.spec:40s} data {rr.data_mean:+.2f} (se {rr.data_se:.2f})  posterior {rr.posterior:.2f}  ratio {rr.ratio:+.2f}  '
        f'[common level {rr.common_level_others:.2f}; Q p {rr.Q_p:.2f}]')

VEC = nine(SPECS['primary'])
RE9 = dl_re([VEC[k]['m'] for k in DIMS], [VEC[k]['se'] for k in DIMS])
RE7 = dl_re([VEC[k]['m'] for k in DIMS if k not in ('own', 'mgt')], [VEC[k]['se'] for k in DIMS if k not in ('own', 'mgt')])
COV9 = pooled_cov()
CORR9 = COV9 / np.sqrt(np.outer(np.diag(COV9), np.diag(COV9)))
RAT = ratio_sim(VEC, cov=COV9)                              # primary: joint draws (review 2)
RAT_IND = ratio_sim(VEC)                                    # v2 round-1 version: independent draws
MS_DIMS = sorted(set(src[src.pooled & (src.source == 'DealLedger')].dim))   # dimensions with a Main Street (DealLedger) estimate
RAT_MS = ratio_sim(VEC, cov=COV9, ref=MS_DIMS)
say('   within-source sampling correlations of the pooled estimates (largest |r| off the diagonal): ' + ', '.join(
    f'{DIMS[i]}-{DIMS[j]} {CORR9[i, j]:+.2f}' for i, j in sorted([(i, j) for i in range(9) for j in range(i + 1, 9)], key=lambda t: -abs(CORR9[t]))[:6]))
say(f'   scale-free check, primary: random-effects common level of the nine pooled-data estimates {RE9["mu"]:.3f} (se {RE9["se"]:.3f}); Cochran Q {RE9["Q"]:.2f} '
    f'on {RE9["df"]} df (p {RE9["p"]:.2f}, I2 {RE9["I2"]:.2f}): equal relative weights are not rejected. Without the settled own/mgt: {RE7["mu"]:.3f} '
    f'(Q {RE7["Q"]:.2f} on {RE7["df"]} df, p {RE7["p"]:.2f})')
say('   ratio to the common level of the other eight (95% interval, JOINT draws): ' + ', '.join(
    f'{k} {RAT[k]["r"]:.2f} [{RAT[k]["lo"]:.2f}, {RAT[k]["hi"]:.2f}]' for k in DIMS))
say('   same, independent draws (round-1 version): ' + ', '.join(f'{k} [{RAT_IND[k]["lo"]:.2f}, {RAT_IND[k]["hi"]:.2f}]' for k in DIMS))
say(f'   ratio to the common level of the other dimensions with a Main Street estimate {MS_DIMS} (joint draws; the full denominator leans on '
    'attenuated single-analog proxies gm, ret, plt): ' + ', '.join(f'{k} {RAT_MS[k]["r"]:.2f} [{RAT_MS[k]["lo"]:.2f}, {RAT_MS[k]["hi"]:.2f}]' for k in DIMS))

# ---- per-dimension table, identification rule v2 ----
_cv5 = cv_tab.set_index(['y', 'kind']).loc[('ls', '5-fold x20 repeats, within-year')]
efev = lambda c: (float(_cv5[f'drop_one_mse_gain_{c}']), float(_cv5[f'drop_one_mse_gain_se_{c}']))
OOS_EV = {  # (label, mean loss rise when the proxy is dropped (EF: MSE, DealLedger: MAE), cluster se)
    'grw': [('EF all sales', *efev('grw_rev')), ('EF 12-month windows', *OOS12), ('DealLedger growth phrase', *dl_drop['growth'])],
    'rec': [('EF', *efev('rec_flag')), ('DealLedger recurring phrase', *dl_drop['recurring'])],
    'gm': [('EF', *efev('gm_obs'))], 'ret': [('EF', *efev('ret_flag'))], 'plt': [('EF', *efev('plt_nch'))],
    'fin': [('DealLedger clean-books phrase', *dl_drop['books'])],
    'own': [('DealLedger owner-operated phrase', *dl_drop['owner_op'])],
    'mgt': [('DealLedger staff-in-place phrase', *dl_drop['staff_in'])],
    'cc': []}
comb = []
for k in DIMS:
    p = VEC[k]
    sens = {f'tau_{t}': pool(k, tau=t)['post'] for t in [0.0, 0.15, 0.5, TAU_REVIEW, 1.0]}
    sens['all_in_unscreened'] = pool(k, tau=max(tau_mom_all, TAU_FLOOR), screened=False)['post']
    sens['DL_only'] = pool(k, sources=['DealLedger'])['post']
    sens['analogs_only'] = pool(k, sources=['EF sale', 'Flippa'])['post']
    sens['no_flippa'] = pool(k, sources=['EF sale', 'DealLedger'])['post']
    sens['EF_ask_instead_of_sale'] = pool(k, wcol='w_ask', scol='se_ask')['post']
    sens['own_spread_scale_all_sources'] = pool(k, wcol='w_os', scol='se_os')['post']
    ev = OOS_EV.get(k, [])
    oos_ok = any(np.isfinite(b) and b > 0 and a > Z_OOS * b for _, a, b in ev)
    st = spec_tab[spec_tab.dim == k]
    if len(st):
        r_lo, r_hi = float(st.ratio.min()), float(st.ratio.max()); a_lo, a_hi = float(st.posterior.min()), float(st.posterior.max())
    else:
        r_lo = r_hi = a_lo = a_hi = np.nan
    crit = dict(a_se=bool(np.isfinite(p['se']) and p['se'] < PRIOR_SD), b_breadth=bool(p['main'] or p['n_src'] >= 2), c_oos=bool(oos_ok),
                d_ratio_excludes_1=bool(RAT[k]['lo'] > 1 or RAT[k]['hi'] < 1),
                e_ratio_stable=bool(np.isnan(r_lo) or (r_lo > 1) or (r_hi < 1)))
    settled = k in ('own', 'mgt')
    idf = all(crit.values())
    rec = CUR[k] if (settled or not idf) else round(p['post'], 2)
    comb.append(dict(dim=k, current=CUR[k], settled=settled, n_sources_pooled=p['n_src'], has_main_street=p['main'], data_mean=p['m'], data_se=p['se'],
                     posterior=p['post'], posterior_se=p['post_se'], ratio=RAT[k]['r'], ratio_lo=RAT[k]['lo'], ratio_hi=RAT[k]['hi'],
                     ratio_lo_independent=RAT_IND[k]['lo'], ratio_hi_independent=RAT_IND[k]['hi'],
                     ratio_ms=RAT_MS[k]['r'], ratio_ms_lo=RAT_MS[k]['lo'], ratio_ms_hi=RAT_MS[k]['hi'],
                     d_under_independent=bool(RAT_IND[k]['lo'] > 1 or RAT_IND[k]['hi'] < 1),
                     spec_ratio_min=r_lo, spec_ratio_max=r_hi, spec_posterior_min=a_lo, spec_posterior_max=a_hi, **crit,
                     identified_v2=idf, recommended=rec, oos_evidence='; '.join(f'{a} {b:+.5f} (se {c:.5f})' for a, b, c in ev), **sens))
comb = pd.DataFrame(comb)
say(comb.drop(columns=['oos_evidence']).round(3).to_string(index=False))
for _, rr in comb.iterrows():
    say(f'   {rr.dim}: a se<{PRIOR_SD} {rr.a_se}, b breadth {rr.b_breadth}, c out-of-sample {rr.c_oos} [{rr.oos_evidence}], d ratio CI excludes 1 {rr.d_ratio_excludes_1}, '
        f'e ratio stable across specs {rr.e_ratio_stable} -> identified {rr.identified_v2}{" (settled; not re-decided here)" if rr.settled else ""}')

# leave-one-source-out calibration of the variance model, over dimensions with two or more pooled sources only (review)
loso = []
multi = [k for k in DIMS if src[(src.dim == k) & src.pooled].source.nunique() >= 2]
for tau_ in [TAU, TAU_REVIEW, 0.0]:
    for i_, rr in src[src.pooled & src.dim.isin(multi)].iterrows():
        others = src[(src.dim == rr.dim) & src.pooled & (src.index != i_)]
        v = others.se.values ** 2 + np.where(others.cls.values == 'main_settled', 0.0, tau_ ** 2)
        pred = float((others.w.values / v).sum() / (1 / v).sum()); pred_v = float(1 / (1 / v).sum())
        own_v = rr.se ** 2 + (0.0 if rr.cls == 'main_settled' else tau_ ** 2)
        loso.append(dict(tau=tau_, source=rr.source, dim=rr.dim, estimate=rr.w, prediction=pred, z=(rr.w - pred) / sqrt(pred_v + own_v)))
loso = pd.DataFrame(loso)
LZ = {t: g for t, g in loso.groupby('tau')}
say(f'   leave-one-source-out (dims with >= 2 sources: {multi}; prediction from the OTHER sources only, no prior): '
    + '; '.join(f'tau {t:.2f}: mean z^2 {np.mean(g.z ** 2):.2f} (n {len(g)}, chi2 p {1 - stats.chi2.cdf((g.z ** 2).sum(), len(g)):.2f})' for t, g in LZ.items()))
say('      z at the used tau: ' + ', '.join(f'{a}/{b} {z:+.2f}' for a, b, z in zip(LZ[TAU].source, LZ[TAU].dim, LZ[TAU].z)))

# ================================================================== 6. MODEL IMPACT through the harness
REC = {k: float(v) for k, v in zip(comb.dim, comb.recommended)}
assert REC == CUR, 'v2 rule recommends no change; anything else needs a new review'
POST_ALL = {k: round(float(v), 2) for k, v in zip(comb.dim, comb.posterior)}
POST_ALL['own'], POST_ALL['mgt'] = CUR['own'], CUR['mgt']
V1 = dict(CUR, rec=0.54, grw=0.51)
nrm = sqrt(sum(v * v for v in REC.values()))
say(f'\n[impact] recommended QW = current {REC}; norm {nrm:.3f}. For the record: the rejected v1 vector (rec 0.54, grw 0.51) and the vector of '
    f'all nine pooled posteriors {POST_ALL} (not adopted: the level is not identified)')


def qw_head(vec):
    return '"quality_weights":{' + ','.join(f'"{k}":{vec[k]}' for k in ['own', 'mgt', 'rec', 'grw', 'gm', 'ret', 'fin', 'cc', 'plt']) + ','


old_head = '"quality_weights":{"own":%s,"mgt":%s,' % (cur.group(1), cur.group(2))
EX = dict(ind="medical", rev=6e6, ern=1.45e6, grw=.14, gm=.64, rec=.72, cc=.18, ret=.91, plt=.38, own=.72, mgt=.36, fin=.74, yrs=6,
          buyers=65, st=None, franchise=False, ask=3.24e6)
PROF = {'example': {}, 'owner-run, thin team': dict(own=.95, mgt=.08), 'absentee, deep team': dict(own=.14, mgt=.92),
        'recurring, growing': dict(rec=.95, grw=.40), 'no recurring, shrinking': dict(rec=.05, grw=-.15),
        'channel-concentrated': dict(plt=.90), 'all poor': dict(own=.95, mgt=.08, fin=.14, rec=0, cc=.6, grw=-.2, gm=.3, ret=.6, plt=.9)}
js = """
const H=require(%s); const base=%s, prof=%s, vecs=%s;
const out={};
for (const [lab,o] of Object.entries(vecs)){ const A=H.load(o); out[lab]={rows:{},w:{}};
  let s2=0; for(const k in A.QW.w) s2+=(A.QW.w[k]/A.QW.norm)**2; out[lab].s2=s2;
  for (const k in A.QW.w) out[lab].w[k]=A.QW.w[k]/A.QW.norm;
  for (const [p,ch] of Object.entries(prof)){ const r=A.model({...base,...ch}); out[lab].rows[p]={V:r.V,qz:r.qz,qPct:r.qPct,PC:r.PC}; } }
console.log(JSON.stringify(out));
""" % (json.dumps(HARN), json.dumps(EX), json.dumps(PROF),
       json.dumps({'current': [], 'v1 (rejected)': [[old_head, qw_head(V1)]], 'all nine posteriors (not adopted)': [[old_head, qw_head(POST_ALL)]]}))
imp = None
try:
    res_js = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=180)
    imp = json.loads(res_js.stdout)
    for lab in imp:
        say(f'   {lab}: sum (w/norm)^2 = {imp[lab]["s2"]:.12f}; per-sd effect on ln(value) at the median: '
            + ', '.join(f'{k} {SLOPE * imp[lab]["w"][k]:.3f}' for k in DIMS))
    for p in PROF:
        a = imp['current']['rows'][p]
        say(f'   {p:24s} V {a["V"]:>12,.0f}; v1 {(imp["v1 (rejected)"]["rows"][p]["V"] / a["V"] - 1) * 100:+.1f}%; all-nine '
            f'{(imp["all nine posteriors (not adopted)"]["rows"][p]["V"] / a["V"] - 1) * 100:+.1f}%')
except Exception as ex:  # the harness is optional for the fit itself
    say('   harness evaluation failed:', repr(ex))

# ================================================================== 7. WRITE TABLES
coef_tab.to_csv(f'{OUT}/ef_coefficients.csv', index=False)
efw.to_csv(f'{OUT}/ef_weights_bootstrap.csv', index=False)
gb_tab.to_csv(f'{OUT}/ef_growth_basis.csv', index=False)
era_tab.to_csv(f'{OUT}/ef_growth_by_era.csv', index=False)
cv_tab.to_csv(f'{OUT}/ef_out_of_sample.csv', index=False)
rob.to_csv(f'{OUT}/ef_robustness.csv', index=False)
fl_tab.to_csv(f'{OUT}/flippa_coefficients.csv', index=False)
pd.DataFrame([dict(variant=k, w=v[0], se=v[1], n=v[2], n_flagged=v[3]) for k, v in FLV.items()]).to_csv(f'{OUT}/flippa_recurring_variants.csv', index=False)
dl_tab.to_csv(f'{OUT}/dealledger_weights.csv', index=False)
src.to_csv(f'{OUT}/sources_by_dimension.csv', index=False)
spec_tab.to_csv(f'{OUT}/specification_set.csv', index=False)
comb.to_csv(f'{OUT}/combined_weights.csv', index=False)
loso.to_csv(f'{OUT}/leave_one_source_out.csv', index=False)
rec_tab.to_csv(f'{OUT}/ef_recurring_by_price.csv', index=False)
pd.DataFrame(COV9, index=DIMS, columns=DIMS).to_csv(f'{OUT}/pooled_covariance.csv')
pd.DataFrame([dict(trend=k, cells=v['cells'], n=v['n'], window=v['window'][0], window_se=v['window'][1], ttm=v['ttm'][0], ttm_se=v['ttm'][1])
              for k, v in TT.items()]).to_csv(f'{OUT}/ef_report_trend_check.csv', index=False)
for stale in ['index.patched.html']:
    if os.path.exists(f'{OUT}/{stale}'): os.remove(f'{OUT}/{stale}')
summary = dict(beq_main=BEQ, slope=SLOPE, band=[LO, HI],
               ef=dict(n=EF['ls']['n'], n_12m_window=int(len(I12)), n_ttm=int(len(ITTM)), window_check_within_1pct=WIN_CHECK,
                       beq_sale=EF['ls']['beq_src'], beq_sale_se=beq_ef_se, beq_ask=EF['la']['beq_src'], r2_sale=EF['ls']['r2'], r2_ask=EF['la']['r2'],
                       proxies=desc, growth_sd_observed=SD_G, corr_window_growth=[corr_ppm_obs, corr_ppm_all], quintiles=quint, break_2019=brk,
                       oos_growth_12m=OOS12, growth_measure_corr=rel_grw, n_ppm_missing=int(d.ppm_miss.sum()),
                       growth_12m_own_sd=[R_12OS['w'], R_12OS['w_se'], sd12], niche_fe=dict(grw_12m=NFE_G12, rec=NFE_REC),
                       report_trend_tables=TT, recurring_by_price=rec_tab.to_dict('records'), rec_sale_max_z=REC_SALE_MAXZ,
                       rec_ask_min_z=REC_ASK_MINZ, growth_all_ef_specs_positive=EF_GRW_POS, growth_ef_spec_min=list(EF_GRW_MIN),
                       n_growth_ef_specs=len(EF_GRW_SPECS)),
               flippa=dict(n=len(f), n_auction=N_AUC, n_ask=N_ASK, beq=fl_bq, pooled=FL, recurring_variants=FLV),
               dealledger=dict(n=len(dl), beq_own_resid=dl_beq_own), gfdata=GF,
               tau_mom=tau_mom, tau_mom_ownspread=tau_mom_os, tau_mom_all_dims=tau_mom_all, tau=TAU,
               common_level=dict(nine=RE9, seven=RE7), ratios=RAT, ratios_independent=RAT_IND, ratios_main_street_ref=RAT_MS,
               main_street_dims=MS_DIMS, pooled_corr=CORR9.tolist(), recommended=REC, impact=imp, runtime_s=time.time() - T0, NB=NB)
json.dump(summary, open(f'{OUT}/summary.json', 'w'), indent=1, default=float)

# ================================================================== 8. PATCH A COPY OF index.html AND RUN THE TESTS ON IT
# The repo file is never modified: the patched page goes to OUT/testrepo/index.html with a copy of tests/.
import shutil, difflib
say('\n[patch] applying the recommendation (weights unchanged; metadata and Data-tab text) to a copy of index.html')
cb = comb.set_index('dim')
r2 = lambda v: round(float(v), 2)
efs = efw.set_index('dim')
dlt = dl_tab.set_index('dim')
sg = spec_tab[spec_tab.dim == 'grw']; sr = spec_tab[spec_tab.dim == 'rec']
EFG_VARIANTS = [W_UNITS[0], R_WIN['w'], R_12['w'], R_12OS['w'], R_INT['w'], R_RN12['w'], R_12I['w'], R_22['w'], R_TTM['w'], NFE_G12[0]]   # EF growth estimates across bases and scales
era_d = era_tab.set_index('era')
FLA = FLV['classified final asks only, kw_recurring']; FLU = FLV['auction sale prices only, kw_recurring']
FLS = FLV['all prices, strict recurring/subscription/MRR/ARR/retainer']
CHECKED = {
    "source": "fit/quality_weights_v2.py",
    "ef_n": int(EF['ls']['n']), "ef_12m_n": int(len(I12)), "flippa_n": int(len(f)), "flippa_auctions": N_AUC,
    "grw": {"ef_12m": [r2(R_12['w']), r2(R_12['w_se'])], "ef_12m_own_sd": [r2(R_12OS['w']), r2(R_12OS['w_se'])],
            "ef_window": [r2(R_WIN['w']), r2(R_WIN['w_se'])],
            "ef_ttm_rebased": [r2(R_TTM['w']), r2(R_TTM['w_se'])], "ef_console_units": [r2(W_UNITS[0]), r2(W_UNITS[1])],
            "ef_2014_17": [r2(era_d.w['2014-17']), r2(era_d.w_se['2014-17'])], "ef_2024_26": [r2(era_d.w['2024-26']), r2(era_d.w_se['2024-26'])],
            "ef_report_increasing_vs_stable": {"window": [round(TT['Increasing']['window'][0], 3), round(TT['Increasing']['window'][1], 3)],
                                               "ttm": [round(TT['Increasing']['ttm'][0], 3), round(TT['Increasing']['ttm'][1], 3)],
                                               "cells": TT['Increasing']['cells']},
            "ef_all_specs_positive": EF_GRW_POS,
            "dl": [r2(dlt.w['grw']), r2(dlt.w_se['grw'])], "flippa": [r2(FL['grw'][0]), r2(FL['grw'][1])],
            "pooled": [r2(cb.data_mean['grw']), r2(cb.data_se['grw'])],
            "ratio": [r2(cb.ratio['grw']), r2(cb.ratio_lo['grw']), r2(cb.ratio_hi['grw'])],
            "ef_range": [r2(min(EFG_VARIANTS)), r2(max(EFG_VARIANTS))],
            "oos": bool(cb.c_oos['grw'])},
    "rec": {"ef": [r2(efs.w_sale['rec']), r2(efs.w_sale_se['rec'])], "ef_ask": [r2(efs.w_ask['rec']), r2(efs.w_ask_se['rec'])],
            "ef_sale_minus_ask": [r2(efs.sale_minus_ask['rec']), r2(efs.sale_minus_ask_se['rec'])],
            "dl": [r2(dlt.w['rec']), r2(dlt.w_se['rec'])],
            "flippa": [r2(FL['rec'][0]), r2(FL['rec'][1])],
            "flippa_auctions": [r2(FLU[0]), r2(FLU[1])], "flippa_asks": [r2(FLA[0]), r2(FLA[1])],
            "flippa_strict": [r2(FLS[0]), r2(FLS[1])],
            "pooled": [r2(cb.data_mean['rec']), r2(cb.data_se['rec'])],
            "ratio": [r2(cb.ratio['rec']), r2(cb.ratio_lo['rec']), r2(cb.ratio_hi['rec'])],
            "posterior_range": [r2(sr.posterior.min()), r2(sr.posterior.max())], "oos": bool(cb.c_oos['rec'])},
    "common_level": [round(RE9['mu'], 2), round(RE9['se'], 2)], "q": [round(RE9['Q'], 1), RE9['df'], round(RE9['p'], 2)]}
J = lambda o: json.dumps(o, separators=(',', ':'))
html0 = open(IDX, encoding='utf8').read()
EDITS = [
 # (1) metadata: which weights are fitted, which are judgment, and what the online-business check found
 ('"prior":"N(1, 0.5^2) on the relative weight","source":"DealLedger listings with descriptions: Huber regression of ln(ask / cash flow) on ln(cash flow), industry and description phrases; broker-clustered bootstrap SEs. Per-sd effects from the threshold model, relative to the equal weight 0.079 per sd."}',
  '"prior":"N(1, 0.5^2) on the relative weight","source":"DealLedger listings with descriptions: Huber regression of ln(ask / cash flow) on ln(cash flow), industry and description phrases; broker-clustered bootstrap SEs. Per-sd effects from the threshold model, relative to the equal weight 0.079 per sd."'
  ',"fitted":["own","mgt"],"weak":["mgt"],"weak_note":"management depth adds nothing out of sample in broker listings and its ratio to the other measured dimensions is not distinguishable from 1 (fit/quality_weights_v2.py); settled weight, not re-decided"'
  ',"judgment":["rec","grw","gm","ret","fin","cc","plt"],"checked":' + J(CHECKED) + '}'),
 # (2) quality_band.weighting (stale: predates the fitted own/mgt weights)
 ('"weighting":"equal weight on the standardized z of each dimension, then the composite z through the normal CDF. Equal weighting is a choice, not an estimate: no dataset we hold prices these dimensions, so inventing a weight vector would add precision that is not there."',
  '"weighting":"weighted sum of the standardized z of each dimension, divided by the norm of the weights, then the composite z through the normal CDF. Owner dependence and management depth carry weights fitted on broker listings (MODELS.fitted.quality_weights); the other seven carry equal weight. For those seven equal weighting is a choice, not an estimate: listing text cannot price them, and online-business sales (fit/quality_weights_v2.py) show that growth raises the sale price while recurring revenue raises only the asking price, without identifying either weight relative to the other dimensions, so inventing a weight vector would add precision that is not there."'),
 # (3) QW comment
 ('/* composite quality weights: owner dependence and management depth are priced in broker\n   listings; the other seven are not identifiable there and keep weight 1 */',
  '/* composite quality weights: owner dependence and management depth are priced in broker\n'
  '   listings (fit/quality_weights.py); the other seven keep weight 1. Recurring revenue and growth\n'
  '   were checked against online-business sales (fit/quality_weights_v2.py): the direction of growth\n'
  '   is confirmed, recurring revenue shows no reliable sale-price effect (its premium is in asking\n'
  '   prices), and neither weight relative to the other dimensions is identified. Only ratios matter:\n'
  '   the composite divides by the norm, so lowering one weight raises all the others. */'),
 # (4), (5) model() comments
 ('     The relative weights of owner dependence and management depth are fitted on broker\n     listings (MODELS.fitted.quality_weights); the other seven are not identifiable there. */',
  '     The relative weights of owner dependence and management depth are fitted on broker\n     listings (MODELS.fitted.quality_weights); the other seven are not identified by any reachable data. */'),
 ("  /* Weighted: owner dependence and management depth carry the relative weights broker\n     listings price them at (fit/quality_weights.py); the other seven are not\n     identifiable in listing text and keep weight 1.",
  "  /* Weighted: owner dependence and management depth carry the relative weights broker\n     listings price them at (fit/quality_weights.py); the other seven keep weight 1:\n     listing text cannot price them, and online-business sales fix only the direction of\n     growth (fit/quality_weights_v2.py)."),
 # (6) quality note under the band
 ("      +MODELS.fitted.quality_weights.mgt.toFixed(2)+' of an equal share); the other seven are '\n      +'weighted equally because no reachable data prices them.</p></div>';",
  "      +MODELS.fitted.quality_weights.mgt.toFixed(2)+' of an equal share); the other seven are '\n      +'weighted equally because no reachable data identifies their relative weight.</p></div>';"),
 # (7) Data tab, quality-position table: judgment row
 ("""      <tr><td>Weights of the other seven, and the peer medians and spreads</td><td><span class="pv j"><i></i>judgment</span> &mdash;
        recurring revenue, growth and clean books show no measurable asking premium in listing text, and
        &ldquo;repeat customers&rdquo; carries the wrong sign (restaurant and retail copy), so listing text cannot
        price them</td></tr>""",
  """      <tr><td>Weights of the other seven, and the peer medians and spreads</td><td><span class="pv j"><i></i>judgment</span> &mdash;
        recurring revenue, growth and clean books show no measurable asking premium in listing text, and
        &ldquo;repeat customers&rdquo; carries the wrong sign (restaurant and retail copy), so listing text cannot
        price them. ${(C=>`Recurring revenue and growth were also checked against
        ${C.ef_n.toLocaleString()} online-business sales (Empire Flippers, sale multiples reconstructed per deal) and
        ${C.flippa_n} Flippa micro-deal prices (${C.flippa_n-C.flippa_auctions} of them final asks, not sales).
        Growth raises the sale price in the Empire Flippers sales, also out of sample, but how much depends on the
        earnings basis and the scale: on the ${C.ef_12m_n.toLocaleString()} sales priced on twelve months of earnings
        (mostly steady businesses) it is ${Math.min(C.grw.ef_12m_own_sd[0],C.grw.ef_12m[0]).toFixed(2)}&ndash;${Math.max(C.grw.ef_12m_own_sd[0],C.grw.ef_12m[0]).toFixed(2)}
        of an equal share depending on which growth spread is used; with every full twelve-month record re-based to
        trailing earnings it is ${C.grw.ef_ttm_rebased[0].toFixed(2)} (partly mechanical, but Empire Flippers&rsquo; own
        tables show growing businesses selling for about ${((Math.exp(C.grw.ef_report_increasing_vs_stable.ttm[0])-1)*100).toFixed(0)}% more
        of trailing earnings than stable ones); across all bases and units it runs from ${C.grw.ef_range[0].toFixed(2)}
        to ${C.grw.ef_range[1].toFixed(2)}. Recurring revenue carries a premium in asking prices only (Empire Flippers
        ${C.rec.ef_ask[0].toFixed(2)} of an equal share, se ${C.rec.ef_ask[1].toFixed(2)}; Flippa final asks
        ${C.rec.flippa_asks[0].toFixed(2)}, se ${C.rec.flippa_asks[1].toFixed(2)}), none in sale prices (Empire Flippers
        ${C.rec.ef[0].toFixed(2)}, se ${C.rec.ef[1].toFixed(2)}; Flippa auctions ${C.rec.flippa_auctions[0].toFixed(2)},
        se ${C.rec.flippa_auctions[1].toFixed(2)}), and adds nothing out of sample in Empire Flippers or broker listings.
        Against the other measured dimensions neither is distinguishable from an equal share`)(MODELS.fitted.quality_weights.checked)}</td></tr>"""),
 # (8) weak-proxy note under that table
 ("""    flags the high end of owner dependence, and the asking price stands in for the sale price. The weights
    are converted from those phrase effects with a threshold model, so read them as the best public""",
  """    flags the high end of owner dependence, and the asking price stands in for the sale price. Empire Flippers
    sales record the sale price (reconstructed per deal); Flippa adds auction prices and final asks. Both come from
    another market, where owners work a few hours a week and measured growth varies five to ten times as much: they
    confirm the direction of growth, show a recurring-revenue premium in asking prices only, and say nothing about
    owner dependence or management depth. The weights
    are converted from those phrase effects with a threshold model, so read them as the best public"""),
 # (9) "what the sliders move" note
 ("""    dependence and management depth carry weights fitted on broker listings, and the other seven are weighted
    equally because no reachable data prices them.""",
  """    dependence and management depth carry weights fitted on broker listings, and the other seven are weighted
    equally because no reachable data identifies their relative weight."""),
 # (10) judgment ledger
 ("""          <td><span class="st free">no source sells this; listing text could not identify them</span></td></tr>""",
  """          <td><span class="st free">no source sells this; listing text could not identify them, and online-business sales
          confirm only the direction of growth</span></td></tr>"""),
]
html1 = html0
for o, n in EDITS:
    assert html1.count(o) == 1, 'anchor not unique/found: ' + o[:90]
    html1 = html1.replace(o, n)
TR = f'{OUT}/testrepo'
if os.path.isdir(TR): shutil.rmtree(TR)
shutil.copytree(REPO_TESTS, f'{TR}/tests')
open(f'{TR}/index.html', 'w', encoding='utf8').write(html1)
open(f'{OUT}/index.patched.html', 'w', encoding='utf8').write(html1)
diff = ''.join(difflib.unified_diff(html0.splitlines(True), html1.splitlines(True), 'a/index.html', 'b/index.html', n=1))
open(f'{OUT}/index.html.diff', 'w', encoding='utf8').write(diff)
say(f'   {len(EDITS)} edits; diff {len(diff.splitlines())} lines -> {OUT}/index.html.diff')

NEWTEST = r"""/* quality weights (fit/quality_weights.py; rec and grw checked by fit/quality_weights_v2.py): node tests/quality_weights.test.js */
const A=require("./load.js");
let pass=0,fail=0; const ok=(c,m)=>{ if(c) pass++; else { fail++; console.log("FAIL:",m); } };
const near=(a,b,t)=>Math.abs(a-b)<=t;
const W=A.MODELS.fitted.quality_weights, D=A.MODELS.value.quality_band.dimensions, C=W.checked;
let s2=0,ss=0; for(const k in A.QW.w){ s2+=(A.QW.w[k]/A.QW.norm)**2; ss+=A.QW.w[k]**2; }
ok(near(s2,1,1e-12),"composite stays standard normal");
ok(near(A.QW.norm,Math.sqrt(ss),1e-12),"the norm is the root sum of the squared weights");
ok(D.length===9&&D.every(k=>A.QW.w[k]>0&&A.QW.w[k]<=2),"every weight positive and at most 2");
ok(W.fitted.length+W.judgment.length===9&&D.every(k=>W.fitted.includes(k)!==W.judgment.includes(k)),"fitted and judgment partition the nine");
ok(D.filter(k=>W[k]!==undefined).sort().join()===W.fitted.slice().sort().join(),"fitted = exactly the dimensions with a fitted weight");
ok(Array.isArray(W.weak)&&W.weak.every(k=>W.fitted.includes(k)),"weakly supported weights are a subset of the fitted ones");
for(const k of W.judgment) ok(A.QW.w[k]===1&&W[k]===undefined,`${k} is judgment and keeps weight 1`);
for(const k of W.fitted) ok(A.QW.w[k]===W[k]&&W.se[k]>0&&W.se[k]<0.5,`${k} uses its fitted weight, with a standard error below the prior sd`);
ok(W.judgment.includes("rec")&&W.judgment.includes("grw"),"recurring revenue and growth stay judgment (relative weight not identified)");
/* the stored evidence must keep agreeing with what the Data tab says about it */
ok(C.grw.ef_range[0]<1&&C.grw.ef_range[1]>1&&C.grw.ratio[1]<1&&C.grw.ratio[2]>1,"growth: EF range across bases and units, and the ratio interval, both include an equal share");
ok(C.grw.oos===true&&C.grw.ef_all_specs_positive===true&&C.grw.ef_12m[0]/C.grw.ef_12m[1]>1.96&&C.grw.ef_12m_own_sd[0]>0,"growth direction: positive in every EF specification, significant on twelve-month windows, adds out of sample");
ok(C.grw.ef_report_increasing_vs_stable.ttm[0]>0,"growth: EF's published tables show a premium on trailing earnings, as the Data tab says");
ok(C.rec.oos===false&&C.rec.ratio[1]<1&&C.rec.ratio[2]>1,"recurring revenue: no out-of-sample value and a ratio interval that includes an equal share");
ok(Math.abs(C.rec.ef[0]/C.rec.ef[1])<1.96&&C.rec.flippa_auctions[0]/C.rec.flippa_auctions[1]<1.96,"recurring revenue: no significant sale-price premium (EF sales, Flippa auctions)");
ok(C.rec.ef_ask[0]/C.rec.ef_ask[1]>1.96&&C.rec.flippa_asks[0]>0&&C.rec.ef_sale_minus_ask[0]<0,"recurring revenue: the premium is in asking prices and partly lost in negotiation");
ok(C.q[2]>0.05,"equal relative weights across the nine measured dimensions are not rejected");
const I=A.IND.medical, RF=A.sizeRefs(1.45e6);
const med={ind:"medical",rev:6e6,ern:1.45e6,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40,ask:3.24e6};
const r0=A.model(med);
ok(near(r0.qz,0,1e-12)&&near(r0.qFactor,1,1e-6),"a business at every peer median sits at the band midpoint");
const dz={rec:.28,grw:.13,gm:.13,ret:.13,cc:.13,plt:.22};
for(const k of Object.keys(dz)){ const sg=(k==="cc"||k==="plt")?-1:1, r1=A.model({...med,[k]:med[k]+dz[k]});
  ok(near(r1.qz-r0.qz,sg*A.QW.w[k]/A.QW.norm,1e-9),`one sd of ${k} moves the composite by w/norm`); }
ok(A.model({...med,rec:med.rec+.2}).V>r0.V&&A.model({...med,grw:med.grw+.1}).V>r0.V,"more recurring revenue or growth still raises value (confirmed for growth; judgment for recurring revenue)");
const jw=W.judgment.map(k=>A.QW.w[k]/A.QW.norm); ok(jw.every(x=>near(x,jw[0],1e-15)),"the seven judgment dimensions share one per-sd effect");
console.log(`${pass} passed, ${fail} failed`); process.exit(fail?1:0);
"""
open(f'{TR}/tests/quality_weights.test.js', 'w').write(NEWTEST)
open(f'{OUT}/quality_weights.test.js', 'w').write(NEWTEST)
TESTS = {}
for t in ['quality_weights.test.js', 'model.test.js'] + (['fuzz.test.js'] if os.environ.get('FUZZ', '1') == '1' else []):
    rr_ = subprocess.run(['node', f'{TR}/tests/{t}'], capture_output=True, text=True, timeout=900)
    TESTS[t] = dict(code=rr_.returncode, tail=(rr_.stdout.strip().splitlines() or [''])[-1], fails=[l for l in rr_.stdout.splitlines() if l.startswith('FAIL')][:20])
    say(f'   node tests/{t} on the patched copy: exit {rr_.returncode}; {TESTS[t]["tail"]}' + ('; ' + ' | '.join(TESTS[t]['fails'][:5]) if TESTS[t]['fails'] else ''))
# every model output identical to the unpatched page (the change is metadata and text only)
JSEQ = r"""
const A=require(%s), B=require(%s);
let seed=20261010; const rnd=()=>{ seed=(seed*16807)%%2147483647; return (seed-1)/2147483646; };
const inds=Object.keys(A.IND); let n=0, diff=0, keys=0;
for(let i=0;i<400;i++){
  const ern=Math.exp(Math.log(2e4)+rnd()*Math.log(500)), rev=ern/(0.05+rnd()*0.5);
  const x={ind:inds[Math.floor(rnd()*inds.length)],rev,ern,grw:-0.2+rnd()*0.6,gm:0.1+rnd()*0.8,rec:rnd(),cc:rnd()*0.8,ret:0.5+rnd()*0.5,
    plt:rnd(),own:rnd(),mgt:rnd(),fin:rnd(),yrs:1+Math.floor(rnd()*20),buyers:1+Math.floor(rnd()*150),st:null,franchise:rnd()<0.2,ask:ern*(1+rnd()*5)};
  const a=A.model(x), b=B.model(x); n++;
  for(const k in a){ if(typeof a[k]==='number'){ keys++; if(!(a[k]===b[k]||(Number.isNaN(a[k])&&Number.isNaN(b[k])))) diff++; } }
}
console.log(JSON.stringify({n,keys,diff,normA:A.QW.norm,normB:B.QW.norm}));
""" % (json.dumps(f'{REPO_TESTS}/load.js'), json.dumps(f'{TR}/tests/load.js'))
try:
    eq_ = json.loads(subprocess.run(['node', '-e', JSEQ], capture_output=True, text=True, timeout=300).stdout)
except Exception as ex:
    eq_ = dict(error=repr(ex))
say(f'   model outputs, unpatched vs patched page, 400 random businesses: {eq_}')
# headless render of the Data tab (needs playwright)
BR = None
if os.environ.get('BROWSER', '1') == '1':
    JSBR = r"""
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{ const b=await pw.chromium.launch(); const out={};
 for (const [lab,f] of [["current",%s],["patched",%s]]){
  const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[];
  p.on("pageerror",e=>errs.push(e.message)); p.on("console",m=>{ if(m.type()==="error") errs.push(m.text()); });
  await p.goto("file://"+f); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
  await p.click('.tab[data-v="data"]'); await p.waitForTimeout(1500);
  const t=await p.evaluate(()=>document.getElementById("view-data").innerText);
  const c=await p.evaluate(()=>document.getElementById("view-console").innerText);
  out[lab]={errs,bad:(t.match(/NaN|Infinity|undefined/g)||[]).length,len:t.length,
    checked:(t.match(/[^\n]*Recurring revenue and growth were also checked[^\n]*/g)||[]).slice(0,1),
    ledger:(t.match(/[^\n]*confirm only the direction[^\n]*/g)||[]).slice(0,1),
    note:(c.match(/[^\n]*identifies their relative weight[^\n]*/g)||[]).slice(0,1),
    askonly:(t.match(/asking prices only/g)||[]).length, recdir:(t.match(/direction of recurring/g)||[]).length};
  await p.close(); }
 console.log(JSON.stringify(out)); await b.close(); })().catch(e=>{ console.log(JSON.stringify({error:String(e)})); });
""" % (json.dumps(IDX), json.dumps(f'{TR}/index.html'))
    try:
        BR = json.loads(subprocess.run(['node', '-e', JSBR], capture_output=True, text=True, timeout=600).stdout.strip().splitlines()[-1])
    except Exception as ex:
        BR = dict(error=repr(ex))
    say(f'   headless Data tab: {json.dumps(BR)[:1500]}')
    if BR and 'patched' in BR:
        say('   headless Data tab, wording counts (patched): "asking prices only" ' + str(BR['patched'].get('askonly')) + ', "direction of recurring" '
            + str(BR['patched'].get('recdir')) + f'; NaN/undefined {BR["patched"]["bad"]}; page errors {len(BR["patched"]["errs"])}')

# ================================================================== 9. RESULT.json
say('\n[result] writing RESULT.json')
cvs = cv_tab.set_index(['y', 'kind'])
k5 = '5-fold x20 repeats, within-year'; kt = 'temporal: fit sold<=2021, test 2022-26'
cv5 = cvs.loc[('ls', k5)]; cva = cvs.loc[('la', k5)]; ctt = cvs.loc[('ls', kt)]
lz = {(a, b): z for a, b, z in zip(LZ[TAU].source, LZ[TAU].dim, LZ[TAU].z)}
rb = rob.set_index('variant')
fls = fl_tab.set_index('proxy')
gbt = gb_tab.set_index('variant')
st_ = spec_tab.set_index(['dim', 'spec'])
P = lambda x, n=2: f'{x:.{n}f}'
fv = lambda k: FLV[k]
ex_V = imp['current']['rows']['example']['V'] if imp else float('nan')


def pct(lab, p_): return (imp[lab]['rows'][p_]['V'] / imp['current']['rows'][p_]['V'] - 1) * 100


def srcline(k):
    out = []
    for _, r_ in src[(src.dim == k)].iterrows():
        out.append(f'{r_.source} {P(r_.w)} (se {P(r_.se)}){" [not pooled: " + r_.screened_out.split(":")[0] + "]" if not r_.pooled else ""}')
    return '; '.join(out)


def critline(k):
    c = cb.loc[k]
    return (f'rule v2: (a) pooled se < 0.5 {"yes" if c.a_se else "no"}; (b) Main Street or >= 2 sources {"yes" if c.b_breadth else "no"}; '
            f'(c) out-of-sample value {"yes" if c.c_oos else "no"}; (d) ratio interval excludes 1 {"yes" if c.d_ratio_excludes_1 else "no"}; '
            f'(e) ratio on one side of 1 across specs ({P(c.spec_ratio_min)} to {P(c.spec_ratio_max)}) {"yes" if c.e_ratio_stable else "no"}')


g_specs = spec_tab[spec_tab.dim == 'grw'].set_index('spec'); r_specs = spec_tab[spec_tab.dim == 'rec'].set_index('spec')
RTs = lambda s_, p_, e_='all': f'{P(RT.w[(s_, p_, e_)])} (se {P(RT.w_se[(s_, p_, e_)])})'
OSLO, OSHI = min(R_12OS['w'], R_12['w']), max(R_12OS['w'], R_12['w'])
D_SAME = bool((comb.d_ratio_excludes_1 == comb.d_under_independent).all())
era_txt = ', '.join(f'{rr.era} {P(rr.w)} ({P(rr.w_se)})' for _, rr in era_tab.iterrows())
brk_txt = (f'break 2019+ z {P(brk["all windows"]["z_niche"], 1)} (niche) / {P(brk["all windows"]["z_quarter"], 1)} (quarter) on all windows, '
           f'{P(brk["12-month windows only"]["z_niche"], 1)} / {P(brk["12-month windows only"]["z_quarter"], 1)} on 12-month windows only: short windows fell from '
           f'{era_d.share_short_window["2014-17"]:.0%} of sales in 2014-17 to {era_d.share_short_window["2024-26"]:.0%} in 2024-26, so most of the drift is the earnings basis')
tt_txt = (f'EF\'s own 2021-report tables ({TT["Increasing"]["cells"]} segment x year x price-tier cells, Amazon Associates and Amazon FBA 2018-20; inverse-variance by n, '
          f'cell-bootstrap se) show it independently of our growth measure: Increasing minus Stable {TT["Increasing"]["window"][0]:+.3f} log (se {TT["Increasing"]["window"][1]:.3f}) '
          f'on the pricing-window multiple but {TT["Increasing"]["ttm"][0]:+.3f} (se {TT["Increasing"]["ttm"][1]:.3f}) on the TTM multiple; Decreasing minus Stable '
          f'{TT["Decreasing"]["window"][0]:+.3f} / {TT["Decreasing"]["ttm"][0]:+.3f}')
ratio_txt = lambda k: (f'ratio to the common level of the other eight {P(cb.ratio[k])} [95% {P(cb.ratio_lo[k])}, {P(cb.ratio_hi[k])}] (joint draws; independent draws '
                       f'[{P(cb.ratio_lo_independent[k])}, {P(cb.ratio_hi_independent[k])}]); against the other dimensions with a Main Street estimate only '
                       f'{P(cb.ratio_ms[k])} [{P(cb.ratio_ms_lo[k])}, {P(cb.ratio_ms_hi[k])}]')
params = [
 dict(param='MODELS.fitted.quality_weights.grw (QW.w.grw, revenue growth)', current_value='1 (equal share, judgment)',
      fitted_value=(
        f'Direction identified in EF sales alone; relative weight not identified. Two twelve-month readings, per sd of the whole EF observed growth distribution '
        f'({SD_G:.2f}/yr) unless stated. (i) Within the {len(I12):,} sales EF priced on an observed 12-month window, a subsample EF selects on low growth (mean '
        f'{by_ppm["mean"].iloc[3]:.2f}/yr vs {by_ppm["mean"].iloc[0]:.2f} for windows of 5 months or less): {P(R_12["w"])} (se {P(R_12["w_se"])}); on the subsample\'s '
        f'own sd ({sd12:.2f}) {P(R_12OS["w"])} (se {P(R_12OS["w_se"])}), so {P(OSLO)}-{P(OSHI)} depending on the per-sd scale, a choice the se leaves out (quintile '
        f'effects vs the bottom ' + ', '.join(f'{e:+.3f}' for e in quint['effect'][1:]) + ' saturate above the median, so the whole-EF scale extrapolates linearly into '
        f'the flat region); with primary-niche fixed effects {P(NFE_G12[0])} (se {P(NFE_G12[1])}); growth x window-length interaction at 12 months {P(R_INT["w"])} '
        f'(se {P(R_INT["w_se"])}). (ii) TTM basis over all {len(ITTM):,} full 12-month P&Ls: {P(R_TTM["w"])} (se {P(R_TTM["w_se"])}; '
        f'{P(gbt.w["TTM re-based, sample own sd"])} on that sample\'s own sd). Partly mechanical: on short-window deals the price was set on recent profit, so '
        f'growth lowers TTM profit without lowering the price (ln window/TTM profit rises {p_mech["grw_rev"]:.3f} per unit of growth); but {tt_txt}. '
        f'Other bases: EF pricing window (v1) {P(R_WIN["w"])} (se {P(R_WIN["w_se"])}); console units (per {CONSOLE_GRW_SD:.2f} of growth) {P(W_UNITS[0])} on '
        f'12-month windows, {P(R_WIN["w_console_units"])} window, {P(R_TTM["w_console_units"])} TTM; rank-normal {P(R_RN12["w"])} and IQR scale {P(R_12I["w"])} on '
        f'12-month windows. Range over EF bases and units {P(min(EFG_VARIANTS))}-{P(max(EFG_VARIANTS))}. Positive in all {len(EF_GRW_SPECS)} EF specifications '
        f'(bases, scales, eras, robustness subsamples, temporal halves; smallest {EF_GRW_MIN[0]} {EF_GRW_MIN[1]:+.2f}) and in all four quintile contrasts. Era (all windows): {era_txt}; '
        f'{brk_txt}. Other sources, not significant: DealLedger growth phrase {P(dlt.w["grw"])} (se {P(dlt.w_se["grw"])}); Flippa {P(FL["grw"][0])} '
        f'(se {P(FL["grw"][1])}; growth wording alone {P(fls.w["kw_growth"])} (se {P(fls.w_se["kw_growth"])}), the positive part comes from the decline flag '
        f'{P(fls.w["kw_decline"])} (se {P(fls.w_se["kw_decline"])})). Pooled data {P(cb.data_mean["grw"])} (se {P(cb.data_se["grw"])}), posterior '
        f'{P(cb.posterior["grw"])}; {ratio_txt("grw")}; across the specification set the posterior runs {P(cb.spec_posterior_min["grw"])}-'
        f'{P(cb.spec_posterior_max["grw"])} and the ratio {P(cb.spec_ratio_min["grw"])}-{P(cb.spec_ratio_max["grw"])}. GF Data AAFP check (not pooled): '
        f'{P(GF["half"])} if half the premium is growth (2021-25 range {P(GF["half_lo"])}-{P(GF["half_hi"])}), {P(GF["all"])} if all of it '
        f'(2021-25 {P(GF["all_lo"])}-{P(GF["all_hi"])}).'),
      se=(f'EF 12-month windows {P(R_12["w_se"])} (max of niche-cluster bootstrap B={NB}, niche-, quarter-clustered and HC1; excludes the per-sd scale choice, '
          f'{P(OSLO)}-{P(OSHI)}); TTM basis {P(R_TTM["w_se"])}; pooled data {P(cb.data_se["grw"])} with transfer sd {P(TAU)}; posterior {P(cb.posterior_se["grw"])}; '
          'ratio interval by simulation from the joint sampling distribution'),
      n=(f'EF {EF["ls"]["n"]:,} sales ({desc["grw_rev"]["n_obs"]:,} with P&L growth; {len(I12):,} priced on an observed 12-month window; {len(ITTM):,} with a full '
         f'12-month P&L); EF report tables {TT["Increasing"]["cells"]} cells; DealLedger {len(dl):,} listings ({dlt.share["grw"]:.0%} growth phrase); Flippa {len(f)} '
         f'prices ({N_AUC} auction sales, {N_ASK} final asks)'),
      method=('EF: OLS of ln sale multiple on one proxy per dimension + ln profit (quadratic), SDE margin, pricing window, ln age, trademark, lender approval, '
              'monetisation count, sites, PBN, text length, business-model and sold-year effects; growth = annualised log revenue growth inside the P&L (last k vs first '
              'k months), winsorised 2.5/97.5%; twelve-month readings on the observed 12-month-window sales (per sd of the whole EF distribution, and of the subsample) '
              'and on TTM re-basing of every full P&L; EF trend tables as an independent check. Converted with the Main Street equal-weight per-sd effect 0.0791. '
              'Inverse-variance pool with transfer sd, N(1, 0.5^2) prior; scale-free ratio to the DerSimonian-Laird common level of the other eight, interval from '
              'the joint sampling distribution (within-source bootstrap correlations); identification rule v2.'),
      validation=(f'EF out of sample: dropping growth raises the 5-fold within-year MSE by {cv5["drop_one_mse_gain_grw_rev"]:+.5f} (niche-cluster se '
                  f'{cv5["drop_one_mse_gain_se_grw_rev"]:.5f}) on all sales and by {OOS12[0]:+.5f} (se {OOS12[1]:.5f}) on the 12-month-window sales; temporal holdout '
                  f'(fit sold<=2021, test 2022-26) growth weight train/test {ctt["w_train_grw"]:+.2f}/{ctt["w_test_grw"]:+.2f} on all windows, '
                  f'{ctt["w_train_grw_ttm12"]:+.2f}/{ctt["w_test_grw_ttm12"]:+.2f} on 12-month windows. DealLedger drop-one MAE {dl_drop["growth"][0]:+.5f} '
                  f'(se {dl_drop["growth"][1]:.5f}). Leave-one-source-out z (tau {P(TAU)}): EF {lz[("EF sale", "grw")]:+.2f}, DealLedger {lz[("DealLedger", "grw")]:+.2f}, '
                  f'Flippa {lz[("Flippa", "grw")]:+.2f}. Posterior under: tau {TAU_REVIEW} {P(cb[f"tau_{TAU_REVIEW}"]["grw"])}; own-spread scale '
                  f'{P(cb.own_spread_scale_all_sources["grw"])}; EF window basis {P(g_specs.posterior["EF growth: pricing-window basis"])}; EF TTM basis '
                  f'{P(g_specs.posterior["EF growth: TTM re-based"])}; EF 12-month own-sample sd {P(g_specs.posterior["EF growth: 12-month windows, own-sample sd"])}; '
                  f'EF niche fixed effects + own-sample sd {P(g_specs.posterior["EF: niche fixed effects and own-sample growth sd"])} (ratio '
                  f'{P(g_specs.ratio["EF: niche fixed effects and own-sample growth sd"])}); EF console units {P(g_specs.posterior["EF growth: console units"])}; '
                  f'EF sold 2022-26 {P(g_specs.posterior["EF growth: sold 2022-26"])}. ' + critline('grw') + '.'),
      recommended_value='1 (unchanged; labelled judgment: direction confirmed in EF sales, relative weight not identified)'),
 dict(param='MODELS.fitted.quality_weights.rec (QW.w.rec, recurring or contracted revenue)', current_value='1 (equal share, judgment)',
      fitted_value=(
        f'Not identified, and no reliable sale-price effect: the recurring premium is in ASKING prices. Asks: EF last ask {P(efs.w_ask["rec"])} (se '
        f'{P(efs.w_ask_se["rec"])}), on 12-month windows {RTs("12-month windows", "last ask")}; Flippa final asks {P(FLA[0])} (se {P(FLA[1])}); DealLedger '
        f'recurring phrase (also an ask) {P(dlt.w["rec"])} (se {P(dlt.w_se["rec"])}). Sale prices: EF {P(efs.w_sale["rec"])} (se {P(efs.w_sale_se["rec"])}; '
        f'{desc["rec_flag"]["n_flagged"]} of {EF["ls"]["n"]:,} sales flagged), on 12-month windows {RTs("12-month windows", "sale")}; Flippa auctions {P(FLU[0])} '
        f'(se {P(FLU[1])}). EF sale minus ask {P(efs.sale_minus_ask["rec"])} (se {P(efs.sale_minus_ask_se["rec"])}), on 12-month windows '
        f'{RTs("12-month windows", "sale minus ask")}: more than half of the ask premium is lost in negotiation. EF by era, sale: '
        + ', '.join(f'{e_} {RTs("all sales", "sale", e_)}' for e_, _, _ in REC_ERAS) + '; ask: '
        + ', '.join(f'{e_} {RTs("all sales", "last ask", e_)}' for e_, _, _ in REC_ERAS)
        + f'. Largest z of any EF sale-price estimate {REC_SALE_MAXZ:+.1f}. Other EF sale specs: without business-model dummies '
        f'{P(REC_VAR["EF rec: no business-model dummies"][0])} (se {P(REC_VAR["EF rec: no business-model dummies"][1])}); model or MRR only '
        f'{P(REC_VAR["EF rec: model or MRR only"][0])} (se {P(REC_VAR["EF rec: model or MRR only"][1])}); primary-niche fixed effects {P(NFE_REC[0])} '
        f'(se {P(NFE_REC[1])}). Flippa as pooled (two-thirds final asks) {P(FL["rec"][0])} (se {P(FL["rec"][1])}); strict recurring/subscription/MRR/ARR/retainer '
        f'wording {P(FLS[0])} (se {P(FLS[1])}). Pooled data {P(cb.data_mean["rec"])} (se {P(cb.data_se["rec"])}), posterior {P(cb.posterior["rec"])}; '
        f'{ratio_txt("rec")}; across the specification set posterior {P(cb.spec_posterior_min["rec"])}-{P(cb.spec_posterior_max["rec"])}, ratio '
        f'{P(cb.spec_ratio_min["rec"])}-{P(cb.spec_ratio_max["rec"])}.'),
      se=(f'pooled data {P(cb.data_se["rec"])}; posterior {P(cb.posterior_se["rec"])} (EF niche bootstrap / clustered; DealLedger broker bootstrap; Flippa row '
          f'bootstrap and HC1; transfer sd {P(TAU)}); era and 12-month-window SEs: max of niche-, quarter-clustered and HC1'),
      n=(f'EF {EF["ls"]["n"]:,} sales ({desc["rec_flag"]["n_flagged"]} flagged; {int(RT.n_flagged[("12-month windows", "sale", "all")])} of them on 12-month windows); '
         f'DealLedger {len(dl):,} ({dlt.share["rec"]:.0%} recurring phrase); Flippa {len(f)} prices ({int(fls.n_flagged["kw_recurring"])} recurring wording; '
         f'{N_ASK} of the {len(f)} are final asks)'),
      method='as grw (flag converted with the threshold model); price-type split: the same design on ln sale, ln last ask and ln sale/ask; era-specific slopes in one regression',
      validation=(f'No out-of-sample value anywhere: EF drop-one {cv5["drop_one_mse_gain_rec_flag"]:+.5f} (se {cv5["drop_one_mse_gain_se_rec_flag"]:.5f}); DealLedger '
                  f'drop-one MAE {dl_drop["recurring"][0]:+.5f} (se {dl_drop["recurring"][1]:.5f}); for Flippa only the whole keyword block was cross-validated '
                  f'(OOS R2 {np.mean(fl_gain):+.4f}). EF temporal holdout weight train/test {ctt["w_train_rec"]:+.2f}/{ctt["w_test_rec"]:+.2f} (separate fits flip sign; one '
                  f'regression with era slopes gives ' + ', '.join(f'{e_} {P(RT.w[("all sales", "sale", e_)])}' for e_, _, _ in REC_ERAS) + ', none significant). '
                  f'Leave-one-source-out z: EF {lz[("EF sale", "rec")]:+.2f}, DealLedger {lz[("DealLedger", "rec")]:+.2f}, Flippa {lz[("Flippa", "rec")]:+.2f}. '
                  f'Posterior under: tau {TAU_REVIEW} {P(cb[f"tau_{TAU_REVIEW}"]["rec"])}; Flippa auctions only {P(r_specs.posterior["Flippa rec: auction sale prices only"])}; '
                  f'Flippa strict wording {P(r_specs.posterior["Flippa rec: strict wording"])}; EF without business-model dummies '
                  f'{P(r_specs.posterior["EF rec: no business-model dummies"])}; EF niche fixed effects {P(r_specs.posterior["EF: primary-niche fixed effects (rec, grw)"])}; '
                  f'EF 12-month windows {P(r_specs.posterior["EF rec: 12-month windows"])}. ' + critline('rec')
                  + '. The absolute-scale estimates sit below 1 in every spec, but so does every measured dimension (common level '
                  + f'{P(RE9["mu"])}): that is attenuation of noisy proxies, not a lower relative weight.'),
      recommended_value='1 (unchanged; labelled judgment; its positive direction in the console is judgment too)'),
 dict(param='MODELS.fitted.quality_weights.own (owner dependence)', current_value=f'{cur.group(1)} (DealLedger, settled)',
      fitted_value=(f'unchanged: DealLedger owner-operated {P(dlt.w["own"], 3)} (se {P(dlt.w_se["own"], 3)}) -> {P(cb.posterior["own"])}. EF owner hours '
                    f'{P(efs.w_sale["own"])} (se {P(efs.w_sale_se["own"])}) and Flippa owner wording {P(FL["own"][0])} (se {P(FL["own"][1])}) reported, screened out. '
                    f'{ratio_txt("own")[0].upper()}{ratio_txt("own")[1:]}: above an equal share, the same side as 1.24.'),
      se=f'{P(cb.posterior_se["own"])}', n=f'DealLedger {len(dl):,} ({dlt.share["own"]:.1%} owner-operated)',
      method='settled fit/quality_weights.py, reproduced exactly (1.371 / 0.368)',
      validation=f'broker-grouped 5-fold CV: dropping the owner-operated phrase raises OOS absolute error by {dl_drop["owner_op"][0]:+.5f} (broker-cluster se {dl_drop["owner_op"][1]:.5f}). {critline("own")}.',
      recommended_value=f'{cur.group(1)} (unchanged, settled; metadata lists it under "fitted")'),
 dict(param='MODELS.fitted.quality_weights.mgt (management depth)', current_value=f'{cur.group(2)} (DealLedger, settled)',
      fitted_value=(f'unchanged: DealLedger staff-in-place {P(dlt.w["mgt"], 3)} (se {P(dlt.w_se["mgt"], 3)}). EF team {P(efs.w_sale["mgt"])} and Flippa team '
                    f'{P(FL["mgt"][0])} screened out. {ratio_txt("mgt")[0].upper()}{ratio_txt("mgt")[1:]}: on that reading about an equal share rather than 0.6.'),
      se=f'{P(cb.posterior_se["mgt"])}', n=f'DealLedger {len(dl):,} ({dlt.share["mgt"]:.1%} staff in place)', method='settled fit/quality_weights.py',
      validation=(f'dropping staff-in-place does not hurt OOS prediction ({dl_drop["staff_in"][0]:+.5f}, se {dl_drop["staff_in"][1]:.5f}). {critline("mgt")}: under this '
                  'fit\'s rule v2 management depth would not be identified. It is settled work and is not re-decided here; the metadata lists it under "fitted" and '
                  'flags it "weak" (weak_note), for the owner of fit/quality_weights.py.'),
      recommended_value=f'{cur.group(2)} (unchanged, settled; flagged weak in metadata)'),
]
for k, why in [('gm', f'EF only: 1 - COGS share on {desc["gm_obs"]["n_obs"]} physical-product sales, {P(efs.w_sale["gm"])} (se {P(efs.w_sale_se["gm"])}); one analog market'),
               ('ret', f'EF only: retention / repeat-purchase wording on {desc["ret_flag"]["n_flagged"]} sales, {P(efs.w_sale["ret"])} (se {P(efs.w_sale_se["ret"])}); churn reported for 27 deals; DealLedger "repeat customers" is wrong-signed boilerplate ({P(dlt.w["ret"])}), excluded'),
               ('fin', f'DealLedger clean-books phrase on {dlt.share["fin"]:.1%} of listings, {P(dlt.w["fin"])} (se {P(dlt.w_se["fin"])}); EF verified data connections only for 2023+ sales (collinear with year)'),
               ('cc', f'DealLedger diversified-customer phrase on {int(round(dlt.share["cc"] * len(dl)))} listings, {P(dlt.w["cc"])} (se {P(dlt.w_se["cc"])}); online businesses have no concentration measure'),
               ('plt', f'EF only: number of acquisition channels named in the summary, {P(efs.w_sale["plt"])} (se {P(efs.w_sale_se["plt"])})')]:
    c = cb.loc[k]
    params.append(dict(param=f'MODELS.fitted.quality_weights.{k} (absent -> QW weight 1)', current_value='1 (judgment)',
                       fitted_value=f'not identified: {why}. Pooled data {P(c.data_mean)} (se {P(c.data_se)}), ratio to the other eight {P(c.ratio)} [95% {P(c.ratio_lo)}, {P(c.ratio_hi)}]',
                       se=f'pooled data se {P(c.data_se)}', n='see fitted_value', method='same pipeline',
                       validation=f'{c.oos_evidence or "no out-of-sample measure"}; {critline(k)}', recommended_value='1 (keep, labelled judgment)'))
_corr_pairs = sorted([(i, j) for i in range(9) for j in range(i + 1, 9)], key=lambda t: -abs(CORR9[t]))[:3]
params.append(dict(param='common level of the nine measured relative weights (fit-internal, scale-free check; not a console parameter)', current_value='n/a',
                   fitted_value=(f'DerSimonian-Laird random-effects mean of the nine pooled-data estimates {P(RE9["mu"])} (se {P(RE9["se"])}), between-dimension sd {P(RE9["tau"])}; '
                                 f'Cochran Q {P(RE9["Q"])} on {RE9["df"]} df, p {P(RE9["p"])}; without the settled own/mgt {P(RE7["mu"])} (Q p {P(RE7["p"])})'),
                   se=f'{P(RE9["se"])}', n='9 pooled per-dimension estimates (13 source x dimension estimates)', method='random-effects meta-analysis across dimensions',
                   validation=('equal relative weights are not rejected; the level below 1 is common to all measured dimensions (proxy attenuation and anchor), so it cannot '
                               'reallocate weight among them. Ratio intervals now use the joint sampling distribution of the nine pooled estimates (largest within-source '
                               'correlations ' + ', '.join(f'{DIMS[i]}-{DIMS[j]} {CORR9[i, j]:+.2f}' for i, j in _corr_pairs) + '); rule (d) gives the same verdict as the '
                               f'independent-draw version for {"every dimension" if D_SAME else "NOT every dimension"}. Against the dimensions with a Main Street estimate only ({", ".join(MS_DIMS)}), '
                               f'grw {P(cb.ratio_ms["grw"])} and rec {P(cb.ratio_ms["rec"])}: the full denominator leans on attenuated single-analog proxies (gm, ret, plt).'),
                   recommended_value='none (diagnostic; a common level would bear on the slope of the whole quality band, a separate parameter)'))
params.append(dict(param='transfer / validity sd tau added to analog and low-specificity phrase estimates before pooling (fit-internal)',
                   current_value='none (analog data not used before)',
                   fitted_value=(f'method of moments EF vs DealLedger on the pooled dims rec, grw: {tau_mom:.2f} on the Main Street scale, {tau_mom_os:.2f} on each market\'s own spread '
                                 f'(agreement depends on the anchor); on all four shared dims incl. the screened own/mgt proxies {tau_mom_all:.2f}'),
                   se='n/a', n='EF vs DealLedger on 2 (4) shared dimensions', method=f'tau = max(MoM, {TAU_FLOOR}); the floor is judgment',
                   validation=('leave-one-source-out over dims with >= 2 sources only (rec, grw; prediction from the other sources, no prior): '
                               + '; '.join(f'tau {t:.2f}: mean z^2 {np.mean(g.z ** 2):.2f} (n {len(g)}, chi2 p {1 - stats.chi2.cdf((g.z ** 2).sum(), len(g)):.2f})' for t, g in LZ.items())
                               + '. With six estimates this does not pin tau down; it is not cited as validation.'),
                   recommended_value=f'{TAU:.2f} for reporting; no console effect (no weight moves)'))

impl = [('NO CHANGE TO ANY WEIGHT. MODELS.fitted.quality_weights keeps own 1.24 and mgt 0.6; rec, grw, gm, ret, fin, cc, plt stay absent (QW weight 1). '
         'The v1 proposal (rec 0.54, grw 0.51) is withdrawn. All edits are metadata and text in /home/user/last-minute/index.html; the model output is bit-identical '
         f'(400 random businesses: {eq_.get("diff", "?")} differing numeric fields of {eq_.get("keys", "?")}). New metadata keys in MODELS.fitted.quality_weights: '
         '"fitted" (["own","mgt"]), "weak" (["mgt"]) with "weak_note", "judgment" (the other seven) and "checked" (the evidence the Data tab quotes; QW reads none of them). '
         f'The script applies exactly these {len(EDITS)} edits to a copy: {OUT}/index.patched.html, diff in {OUT}/index.html.diff. '
         'Tests on the patched copy: ' + '; '.join(f'{t} -> {v["tail"]}' for t, v in TESTS.items()) + '. '
         f'Headless Data tab render: ' + (f'NaN/undefined count current {BR["current"]["bad"]}, patched {BR["patched"]["bad"]}; page errors {len(BR["patched"]["errs"])}' if BR and 'patched' in BR else f'not run ({BR})') + '. '
         f'New test file: {OUT}/quality_weights.test.js (copy to tests/).')]
for i_, (o, n) in enumerate(EDITS, 1):
    impl.append(f'({i_}) REPLACE:\n{o}\nWITH:\n{n}')
impl.append('Effect at the worked example and every profile: none (weights unchanged). For the record, through the harness: the rejected v1 vector would have moved the example '
            f'{pct("v1 (rejected)", "example"):+.1f}%, a channel-concentrated business {pct("v1 (rejected)", "channel-concentrated"):+.1f}% and a non-recurring, shrinking one '
            f'{pct("v1 (rejected)", "no recurring, shrinking"):+.1f}% with no evidence on channels; applying all nine pooled posteriors at once would move the example '
            f'{pct("all nine posteriors (not adopted)", "example"):+.1f}%. Optional (not part of the model): add a row for quality_weights_v2.py to fit/README.md '
            '("rec and grw checked against EF/Flippa sales: growth raises the sale price, recurring revenue only the asking price; relative weights not identified; no change").')
C_ = CHECKED
data_tab = (
    'Quality-position table, judgment row "Weights of the other seven, and the peer medians and spreads" keeps its label and adds (numbers are read from '
    'MODELS.fitted.quality_weights.checked): "Recurring revenue and growth were also checked against '
    f'{C_["ef_n"]:,} online-business sales (Empire Flippers, sale multiples reconstructed per deal) and {C_["flippa_n"]} Flippa micro-deal prices '
    f'({C_["flippa_n"] - C_["flippa_auctions"]} of them final asks, not sales). Growth raises the sale price in the Empire Flippers sales, also out of sample, but how '
    f'much depends on the earnings basis and the scale: on the {C_["ef_12m_n"]:,} sales priced on twelve months of earnings (mostly steady businesses) it is '
    f'{min(C_["grw"]["ef_12m_own_sd"][0], C_["grw"]["ef_12m"][0]):.2f}-{max(C_["grw"]["ef_12m_own_sd"][0], C_["grw"]["ef_12m"][0]):.2f} of an equal share depending on '
    f'which growth spread is used; with every full twelve-month record re-based to trailing earnings it is {C_["grw"]["ef_ttm_rebased"][0]:.2f} (partly mechanical, '
    f'but Empire Flippers\' own tables show growing businesses selling for about {(exp(C_["grw"]["ef_report_increasing_vs_stable"]["ttm"][0]) - 1) * 100:.0f}% more of '
    f'trailing earnings than stable ones); across all bases and units it runs from {C_["grw"]["ef_range"][0]:.2f} to {C_["grw"]["ef_range"][1]:.2f}. Recurring revenue '
    f'carries a premium in asking prices only (Empire Flippers {C_["rec"]["ef_ask"][0]:.2f} of an equal share, se {C_["rec"]["ef_ask"][1]:.2f}; Flippa final asks '
    f'{C_["rec"]["flippa_asks"][0]:.2f}, se {C_["rec"]["flippa_asks"][1]:.2f}), none in sale prices (Empire Flippers {C_["rec"]["ef"][0]:.2f}, se {C_["rec"]["ef"][1]:.2f}; '
    f'Flippa auctions {C_["rec"]["flippa_auctions"][0]:.2f}, se {C_["rec"]["flippa_auctions"][1]:.2f}), and adds nothing out of sample in Empire Flippers or broker '
    'listings. Against the other measured dimensions neither is distinguishable from an equal share." Weak-proxy note: "Empire Flippers sales record the sale price '
    '(reconstructed per deal); Flippa adds auction prices and final asks. Both come from another market, where owners work a few hours a week and measured growth '
    'varies five to ten times as much: they confirm the direction of growth, show a recurring-revenue premium in asking prices only, and say nothing about owner '
    'dependence or management depth." Quality note under the band and the "what the sliders move" note: "...the other seven are weighted equally because no reachable '
    'data identifies their relative weight." Judgment ledger status: "no source sells this; listing text could not identify them, and online-business sales confirm only '
    'the direction of growth." No fitted-parameter row is added and the fitted-parameter count stays (two quality weights). Source: fit/quality_weights_v2.py; n EF '
    f'{C_["ef_n"]:,} ({C_["ef_12m_n"]:,} on observed 12-month windows), EF report tables {C_["grw"]["ef_report_increasing_vs_stable"]["cells"]} cells, Flippa '
    f'{C_["flippa_n"]} ({C_["flippa_auctions"]} auction sales), DealLedger {len(dl):,}; SE as stated (the growth se excludes the per-sd scale choice, hence the range); '
    'caveat: online sales are an analog, and the level is anchor-, scale- and basis-dependent.')
tests_inv = [
 'sum over the nine dimensions of (QW.w[k]/QW.norm)^2 == 1 to 1e-12 (composite stays standard normal); QW.norm == sqrt(sum QW.w[k]^2) to 1e-12',
 'every QW.w[k] is > 0 and <= 2',
 'quality_weights.fitted and quality_weights.judgment partition the nine dimensions; fitted is exactly the set of dimension keys present in MODELS.fitted.quality_weights; weak is a subset of fitted',
 'each judgment dimension has no key in MODELS.fitted.quality_weights and QW.w[k] === 1; each fitted one uses QW.w[k] === MODELS.fitted.quality_weights[k] with 0 < se[k] < 0.5 (structural: no hard-coded weight values, so a later data-backed refit of own/mgt does not break the test)',
 'rec and grw are in judgment (relative weight not identified)',
 'stored evidence agrees with the Data-tab text: checked.grw.ef_range and checked.grw.ratio interval both include 1; checked.grw.oos === true, ef_all_specs_positive === true, ef_12m z > 1.96, ef_report_increasing_vs_stable.ttm > 0',
 'stored evidence agrees with the Data-tab text: checked.rec.oos === false, ratio interval includes 1; |ef z| < 1.96 and flippa_auctions z < 1.96 (no sale-price premium); ef_ask z > 1.96, flippa_asks > 0 and ef_sale_minus_ask < 0 (premium in asks, partly lost in negotiation)',
 'checked.q p-value > 0.05 (equal relative weights not rejected)',
 'a business at every peer median has qz === 0 and qFactor === 1',
 'one model-sd move of any dimension (rec +0.28, grw/gm/ret/cc +0.13, plt +0.22) changes qz by exactly sign*QW.w[k]/QW.norm',
 'raising rec or grw raises V (confirmed for growth; judgment for recurring revenue)',
 'the seven judgment dimensions share one per-sd effect 1/QW.norm',
 'every numeric model() output is identical to the unpatched page for random businesses (metadata/text-only change; run by the fit script, not part of the test file)',
 'Data tab renders with no NaN/Infinity/undefined and shows the checked numbers (headless browser sweep)']
not_ident = [
 (f'grw (revenue growth) relative weight: the direction is identified in EF sales alone (positive in all {len(EF_GRW_SPECS)} EF specifications and out of sample; not '
  f'significant in DealLedger, {P(dlt.w["grw"])} (se {P(dlt.w_se["grw"])}), or Flippa, {P(FL["grw"][0])} (se {P(FL["grw"][1])})), the level is not. On twelve months '
  f'of earnings: {P(OSLO)}-{P(OSHI)} within the sales EF priced on twelve months (a low-growth subsample; the range is the per-sd scale), {P(R_TTM["w"])} with every '
  f'full P&L re-based to TTM profit (partly mechanical; EF\'s own trend tables show the same TTM-basis premium); {P(min(EFG_VARIANTS))}-{P(max(EFG_VARIANTS))} across '
  f'bases and units; pooled posterior {P(cb.spec_posterior_min["grw"])}-{P(cb.spec_posterior_max["grw"])} across specs; ratio to the other dimensions {P(cb.ratio["grw"])} '
  f'[{P(cb.ratio_lo["grw"])}, {P(cb.ratio_hi["grw"])}], {P(cb.ratio_ms["grw"])} against the Main Street-sourced ones. Keep 1 as judgment.'),
 (f'rec (recurring revenue): not even the direction is established on sale prices. The premium is in asking prices (EF last ask {P(efs.w_ask["rec"])}, se '
  f'{P(efs.w_ask_se["rec"])}; Flippa final asks {P(FLA[0])}, se {P(FLA[1])}) and not in sale prices (EF {P(efs.w_sale["rec"])}, se {P(efs.w_sale_se["rec"])}; Flippa '
  f'auctions {P(FLU[0])}, se {P(FLU[1])}; largest z of any EF sale-price estimate {REC_SALE_MAXZ:+.1f}); EF sale minus ask {P(efs.sale_minus_ask["rec"])}; no '
  f'out-of-sample value in EF or DealLedger; not significant in any EF era on sale prices (' + ', '.join(f'{e_} {P(RT.w[("all sales", "sale", e_)])}' for e_, _, _ in REC_ERAS)
  + f') and sign-unstable across separately fitted periods (sold <= 2021 {ctt["w_train_rec"]:+.2f}, 2022-26 {ctt["w_test_rec"]:+.2f}); ratio to the other dimensions {P(cb.ratio["rec"])} [{P(cb.ratio_lo["rec"])}, '
  f'{P(cb.ratio_hi["rec"])}]. Keep 1; its positive direction in the console is judgment.'),
 f'gm (gross margin): only EF COGS on {desc["gm_obs"]["n_obs"]} physical-product sales ({P(efs.w_sale["gm"])}, se {P(efs.w_sale_se["gm"])}); one analog market; keep 1',
 f'ret (customer retention): EF wording {P(efs.w_sale["ret"])} (se {P(efs.w_sale_se["ret"])}, {desc["ret_flag"]["n_flagged"]} sales) is a single analog; DealLedger "repeat customers" is wrong-signed boilerplate; keep 1',
 f'fin (reporting quality): DealLedger clean-books phrase too rare ({P(dlt.w["fin"])}, se {P(dlt.w_se["fin"])}); EF verified-data connections exist only from 2023 (collinear with year); keep 1',
 f'cc (customer concentration): DealLedger diversified-customer phrase on {int(round(dlt.share["cc"] * len(dl)))} listings ({P(dlt.w["cc"])}, se {P(dlt.w_se["cc"])}); pooled se above the prior sd; online businesses have no measure; keep 1',
 f'plt (channel concentration): EF channel count {P(efs.w_sale["plt"])} (se {P(efs.w_sale_se["plt"])}) is one analog with no out-of-sample value; keep 1',
 'own and mgt from online data: EF owner hours (median 3 h/week) and freelance "teams" lie outside the Main Street range; they cannot move those weights',
 (f'The absolute level of every measured weight (common level {P(RE9["mu"])}, se {P(RE9["se"])}) rests on the conversion anchor 0.0791 and on proxy attenuation; Q p {P(RE9["p"])} does not reject equal relative weights. '
  'A common level below 1 bears on the slope of the whole quality band (a separate parameter, not fitted here), not on the allocation among dimensions.'),
 (f'Flag for the settled fit (not re-decided here; metadata "weak":["mgt"]): on the same scale-free reading management depth sits at about an equal share (ratio {P(cb.ratio["mgt"])} '
  f'[{P(cb.ratio_lo["mgt"])}, {P(cb.ratio_hi["mgt"])}]) and has no out-of-sample value, so its settled 0.60 is weakly supported; owner dependence (ratio {P(cb.ratio["own"])}) stays on the side of 1.24.')]
caveats = (
 'RESPONSE TO REVIEW, ROUND 2 (both reviewers accept_with_changes; every problem accepted; no weight moves). '
 f'(Major, both reviewers) Recurring revenue: only growth has a confirmed direction. Edits (2), (3), (5), (7), (8) and (10) now say growth raises the sale price and '
 f'recurring revenue raises only the asking price. A new price-type table (ef_recurring_by_price.csv) backs this: EF sale {P(efs.w_sale["rec"])} (z '
 f'{efs.w_sale["rec"] / efs.w_sale_se["rec"]:+.1f}), last ask {P(efs.w_ask["rec"])} (z {efs.w_ask["rec"] / efs.w_ask_se["rec"]:+.1f}), sale minus ask '
 f'{P(efs.sale_minus_ask["rec"])} (z {efs.sale_minus_ask["rec"] / efs.sale_minus_ask_se["rec"]:+.1f}); 12-month windows sale {RTs("12-month windows", "sale")}, ask '
 f'{RTs("12-month windows", "last ask")}, sale minus ask {RTs("12-month windows", "sale minus ask")}; by era on sale prices '
 + ', '.join(f'{e_} {RTs("all sales", "sale", e_)}' for e_, _, _ in REC_ERAS)
 + f' (one regression with era-specific slopes; reviewer 2\'s own era re-estimate gave -0.16/-0.06/+0.47: none significant either way, same conclusion); '
 f'largest z of any EF sale-price estimate {REC_SALE_MAXZ:+.1f}; Flippa auctions {P(FLU[0])} (se {P(FLU[1])}) vs final asks {P(FLA[0])} (se {P(FLA[1])}). '
 'In the test, rec is out of the direction invariant; it now asserts no significant sale-price premium, a significant ask premium partly lost in negotiation, and '
 'oos === false. checked.rec stores ef_ask, ef_sale_minus_ask and flippa_asks. '
 f'(Minor, reviewer 1) 12-month sample: defined on the observed pricing_period_months, n {len(I12):,} (was 1,559; the {int(d.ppm_miss.sum())} deals with no window, all '
 f'sold in 2015 without a growth measure, are no longer counted); growth weight {P(R_12["w"])} (se {P(R_12["w_se"])}), unchanged. '
 f'(Minor, reviewer 1) TTM reading: agreed that "shares months with the growth measure" did not distinguish the two readings. On 12-month-window deals ln TTM multiple '
 f'= ln window multiple - ln 12 (median deviation {np.median(MECH12):.5f}), so they share the months exactly; the difference is the sample, because EF shortens the window '
 f'for growers. {P(R_TTM["w"])} is now described as the TTM-basis estimate over all full P&Ls, partly mechanical but corroborated by EF\'s trend tables (re-estimated in '
 f'the script: Increasing minus Stable {TT["Increasing"]["window"][0]:+.3f} log on the window multiple, {TT["Increasing"]["ttm"][0]:+.3f} on the TTM multiple), and '
 f'{P(R_12["w"])} as the estimate within a subsample EF selects on low growth. The Data tab presents both twelve-month readings and no longer says "as the console is". '
 f'(Minor, both) Per-sd scale: the Data tab quotes {P(OSLO)}-{P(OSHI)} on twelve-month windows and says the range is the choice of growth spread; checked.grw stores '
 f'ef_12m_own_sd [{P(R_12OS["w"])}, {P(R_12OS["w_se"])}]; the own-sample-sd spec (posterior {P(g_specs.posterior["EF growth: 12-month windows, own-sample sd"])}, ratio '
 f'{P(g_specs.ratio["EF growth: 12-month windows, own-sample sd"])}) and reviewer 1\'s alternative (primary-niche fixed effects plus own-sample sd: pooled '
 f'{P(g_specs.data_mean["EF: niche fixed effects and own-sample growth sd"])} (se {P(g_specs.data_se["EF: niche fixed effects and own-sample growth sd"])}), ratio '
 f'{P(g_specs.ratio["EF: niche fixed effects and own-sample growth sd"])}) are in the specification set; neither changes the decision. The EF range across bases and units '
 f'is kept ({P(min(EFG_VARIANTS))}-{P(max(EFG_VARIANTS))}). '
 f'(Minor, reviewer 1) Wording and keys: growth is "positive in all {len(EF_GRW_SPECS)} EF specifications; not significant in DealLedger or Flippa" (Flippa growth '
 f'wording alone {P(fls.w["kw_growth"])}); checked.grw.bracket -> ef_range and checked.rec.bracket -> posterior_range, template and test updated. '
 '(Minor, both) Tests: the "grw >= every judgment weight" invariant is dropped, and the round-1 caveat that ranking growth below the unmeasured dimensions "inverts '
 f'what transfers" is withdrawn: the growth ratio interval [{P(cb.ratio_lo["grw"])}, {P(cb.ratio_hi["grw"])}] and the Main Street-reference ratio '
 f'{P(cb.ratio_ms["grw"])} do not establish a ranking. Hard-coded own 1.24 / mgt 0.6 / norm are replaced by structural checks (norm = root sum of squares; fitted '
 'weights = MODELS.fitted.quality_weights[k]; judgment weights = 1); the bit-identical output comparison run by the script guards this patch. '
 '(Minor, reviewer 2) "identified" -> "fitted", plus "weak":["mgt"] and a weak_note, so the metadata does not claim an identification this fit disputes. '
 f'(Minor, reviewer 2) Ratio intervals now come from the joint sampling distribution (within-source bootstrap correlations, scaled to the SEs used; largest '
 + ', '.join(f'{DIMS[i]}-{DIMS[j]} {CORR9[i, j]:+.2f}' for i, j in _corr_pairs)
 + f'); grw [{P(cb.ratio_lo["grw"])}, {P(cb.ratio_hi["grw"])}] vs [{P(cb.ratio_lo_independent["grw"])}, {P(cb.ratio_hi_independent["grw"])}] independent; rec '
 f'[{P(cb.ratio_lo["rec"])}, {P(cb.ratio_hi["rec"])}] vs [{P(cb.ratio_lo_independent["rec"])}, {P(cb.ratio_hi_independent["rec"])}]; rule (d) gives the same verdict '
 f'under both for {"every dimension" if D_SAME else "NOT every dimension"}. Because the denominator leans on attenuated single-analog proxies, a ratio against the dimensions with a Main Street estimate is also '
 f'reported (grw {P(cb.ratio_ms["grw"])} [{P(cb.ratio_ms_lo["grw"])}, {P(cb.ratio_ms_hi["grw"])}], rec {P(cb.ratio_ms["rec"])} [{P(cb.ratio_ms_lo["rec"])}, '
 f'{P(cb.ratio_ms_hi["rec"])}]); the Data tab cites the ratios only as "not distinguishable from an equal share". Transfer error is treated as independent across '
 'dimensions; a source-wide transfer bias common to all its dimensions would cancel in the ratio. '
 '(Minor, reviewer 2) Wording: edit (8) now reads "Empire Flippers sales record the sale price (reconstructed per deal); Flippa adds auction prices and final asks"; '
 'edit (7) reads "adds nothing out of sample in Empire Flippers or broker listings" (for Flippa only the whole keyword block was cross-validated). '
 'Both reviewers reported writing into other agents\' scratchpad folders; this fit reads none of those folders, and all its outputs are regenerated by this run. '
 'ROUND 1, STILL IN FORCE. Earnings basis: EF prices on a pricing window it shortens for growers (corr(window, growth) '
 f'{corr_ppm_obs:+.2f}; mean growth {by_ppm["mean"].iloc[0]:.2f}/yr for windows of 5 months or less vs {by_ppm["mean"].iloc[3]:.2f} for 12), so the v1 window-basis '
 f'estimate ({P(R_WIN["w"])}) understated growth on the console\'s basis; grw stays 1, judgment. Only ratios matter: common level {P(RE9["mu"])} (se {P(RE9["se"])}; '
 f'Q {P(RE9["Q"])} on {RE9["df"]} df, p {P(RE9["p"])}). Era: all-window slopes run from {P(era_d.w["2014-17"])} (2014-17) to {P(era_d.w["2024-26"])} (2024-26), break '
 f'z {P(brk["all windows"]["z_niche"], 1)}/{P(brk["all windows"]["z_quarter"], 1)}, but only z {P(brk["12-month windows only"]["z_niche"], 1)}/'
 f'{P(brk["12-month windows only"]["z_quarter"], 1)} on 12-month windows: mostly the earnings basis. Functional form: concave (quintiles saturate above the median). '
 f'tau: method of moments {tau_mom:.2f} on the Main Street scale and {tau_mom_os:.2f} on each market\'s own spread; tau {TAU_REVIEW} posteriors are reported. GF Data: '
 f'{P(GF["half"])} equal shares if half the AAFP premium is growth, {P(GF["all"])} if all of it; it brackets 1 and decides nothing. '
 'TRANSFERABILITY. Online-business sales (Empire Flippers; Flippa, a third of it auctions) are analogs for Main Street deals. What transfers: the direction of growth '
 '(positive in every EF specification, out of sample, and in EF\'s own trend tables) and its shape (concave, and carried by trailing earnings rather than by the '
 'recent-months basis EF lists on). For recurring revenue not even the direction transfers on sale prices: the analog premium is in asks, which is what broker '
 'listings (DealLedger) measure too. What does not transfer: the level relative to the other dimensions (anchor, earnings basis, a growth scale ten times wider than '
 'the console\'s, era-specific pricing practice) and anything about owner dependence or management depth. Shrinkage toward the current value is therefore complete: '
 'the recommended values equal the current ones. '
 f'OTHER. The EF sale price is a reconstruction (stored integer multiple, +-0.5) net of earnout shortfalls (3-8% below EF\'s headline average sale price for 2017-20, per the reconstruction\'s dictionary); survivorship (only sold '
 f'listings). EF growth is measured with noise (correlation {rel_grw:.2f} with EF\'s displayed trend), so all EF growth weights are attenuated. Ratio intervals assume '
 'normal sampling errors. The cross-validation folds demean by sold year within each fold (both compared models alike), so drop-one comparisons are fair but '
 'absolute out-of-sample R2 is slightly optimistic.')
RESULT = dict(name='quality_weights_v2', script='/home/user/last-minute/fit/quality_weights_v2.py', parameters=params, not_identified=not_ident,
              implementation='\n\n'.join(impl), data_tab_text=data_tab, test_invariants=tests_inv, caveats=caveats)
json.dump(RESULT, open(f'{OUT}/RESULT.json', 'w'), indent=1)
say(f'   wrote {OUT}/RESULT.json')
say(f'\nwrote {OUT}')
open(f'{OUT}/run.log', 'w').write('\n'.join(LOG) + '\n')
