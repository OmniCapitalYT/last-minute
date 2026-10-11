#!/usr/bin/env python3
"""Shape of the time-to-close distribution (Model III), fitted by deal-size band.  Round 3 (after the second review).

Run:  python3 -I /home/user/last-minute/fit/time_to_close_shape.py          (about 20 min with the JS checks)
      python3 -I /home/user/last-minute/fit/time_to_close_shape.py 60 nojs   (quick test: B=60, no node runs)
Out:  /tmp/claude-0/fit5/time_to_close_shape/
      fits.json (everything), band_shape_table.csv, sensitivity_table.csv, ibba_fits_by_band.csv,
      cv_loqo_<spec>.csv, size_order_calibration.csv, recommended_table.csv,
      patched/index.html (+ tests) = repo index.html with the recommended change,
      patched_after_overpricing/index.html (+ tests) = the same change applied on top of the overpricing_time patch,
      index.html.diff, index_after_overpricing.html.diff, check_invariants.js, js_checks.json.
      The repo's index.html is read, never written.  RESULT.json is written by hand from these outputs.

What it does
  0. Data: IBBA / M&A Source Market Pulse per-band histograms of months listing/engagement -> close and
     LOI/offer -> close: 15 quarters (2020Q1-2021Q4, 2022Q2-2023Q3, 2025Q4), closed deals only. Each chart is a
     share of the band's closed deals in the questionnaire's dropdown categories (<1 month, 1..12 months,
     1.1-1.5 yr, 1.6-2 yr, >2 yr). Shares are renormalised to their chart sum and multiplied by n_closed.
     Parse fix: in three <500K listing->close charts (2020Q3, 2022Q2, 2022Q4) the tidy table carries the
     '1.1-1.5 years' bar as '1.1-1.6 yr' and the '1.6-2 years' bar as a second '2 mo' (it sits after the year
     bar). The raw report text shows '1.1 - 1.5 years' and '1.6 - 2 years' (IBBA_Q3_2020_final.txt l.820-823,
     MP_Q2_2022.txt l.681-685, q4_2022_market_pulse.txt l.1001-1004). Recoded by chart position.
  1. Interval convention ("spec"). Central: integer answers are rounded months, k -> [k-0.5, k+0.5), and the
     '<1 month' and '1 month' answers are MERGED into [0, 1.5). '<1 month' is ambiguous under rounding (a
     0.8-month deal can truthfully be reported either way); the merged bin is valid under both readings.
     Sensitivities: floor convention ([k, k+1), merged [0, 2)); '<1 mo' as [0, 0.5) (round 1's central);
     '<1 mo' as [0, 1) with '1 mo' as [1, 1.5); sub-month deals dropped with left truncation at 0.5 months;
     censoring at 18.5 months (the console's axis ends at 17.7); 3-6-month coarse bins; heaped answers widened
     (6 mo -> [4, 8), 12 mo -> [9, 15)); and round 1's data before the parse fix.
  2. Interval-censored maximum likelihood for Weibull, gamma, lognormal, log-logistic and the Prentice
     generalised gamma (nests Weibull Q=1, lognormal Q=0) for each band.
  3. Standard errors: observed-information (Hessian) SEs, and a cluster bootstrap that resamples QUARTERS
     JOINTLY across bands (B=1000), so it also gives the covariance of the band estimates.
  4. Empirical Bayes: each band's shape is shrunk toward a weighted straight line in ln(band centre)
     (Fay-Herriot, DerSimonian-Laird moment estimate of tau^2). Shrinking toward the overall mean (round 1)
     is reported as a sensitivity. Total SE = EB posterior SE (+) half the floor-round gap (+) half the range
     of the four '<1 month' readings (in quadrature).
  4b. Structure of the size effect (round 3). Is there a gradient above $500K? Homogeneity of the four upper
     bands (independent and with the joint-bootstrap covariance), slope among them, step-at-$500K vs straight
     line (same number of parameters), tau^2 for the upper bands (DL, REML, Q-profile CI). Candidate structures
     scored on held-out quarters as the console draws them (median pinned): one beta; TWO LEVELS (<500K own
     beta; the four upper bands share one beta, joint MLE with a free median per band); partial pooling toward
     that step; isotonic; five bands shrunk toward the line (round 2). Selection rule: the structure with the
     fewest shape parameters whose held-out score is within one SE of the best. The pooled upper beta is refitted
     under every interval spec (convention terms) and bootstrapped over quarters jointly with the bands.
  5. Out of sample: leave-one-quarter-out (LOQO) held-out log-likelihood, under the central spec, under round
     1's spec, and censored at 18.5 months, with pairwise gains, quarter-clustered SEs and t(14) p-values;
     leave-a-block-of-4-quarters-out (4 folds, t(3)); a temporal holdout (fit 2020Q1-2022Q4, test 2023Q1-2023Q3
     + 2025Q4) with an SE over its 4 test quarters. Curves are scored both free and with the median pinned to
     the console's band median (how the console draws them). The console medians (IBBA 2018-23 editions) overlap
     the test quarters and are not refitted per fold, so only PAIRWISE gains between pinned curves are out of
     sample, not their levels.
  6. Size order and calibration of the curve the console would draw: F(t | value) on a fine value grid for
     t = 90/180/365/540 days, with today's curve, the proposed curve, round 2's five-band curve and the proposed
     shape on the histograms' own medians; F(90/180/365) at the band centres against the histograms.
  7. Cross-checks on analogs (direction only): Pepperdine PCM 2016, TRANBI Japan, Empire Flippers, Flippa.
     The tidy PCM table already labels each band's listing->close and LOI->close charts separately; the script
     uses those labels and checks (no-op) that they agree with the chart order.
  8. Recommended table, the exact index.html edits (applied to copies), and node checks of the patched copies.
Family rule, fixed in advance in round 1: the best LOQO family among those closed-form in JS that pin
exactly to a median (Weibull, lognormal, log-logistic). Gamma is reported but not eligible.
"""
import difflib, json, os, re, shutil, subprocess, sys, time
import numpy as np
import pandas as pd
from scipy import optimize, special, stats

T0 = time.time()
OUT = '/tmp/claude-0/fit5/time_to_close_shape'
os.makedirs(OUT, exist_ok=True)
IBBA = '/tmp/claude-0/data5/aggregates_research/clean/ibba_mp_band_histograms_long.csv'
PCM = '/tmp/claude-0/data5/aggregates_research/clean/pcm2016_band_histograms_long.csv'
TRANBI = '/tmp/claude-0/data5/extra_japan_platform_closed_deals/clean/tranbi_closed_deals.csv'
EF = '/tmp/claude-0/data5/empireflippers/clean/ef_sold_derived.csv'
FLIPPA = '/tmp/claude-0/data5/extra_flippa_outcome_panel/clean/fit_march_results.json'
REPO = '/home/user/last-minute'
INDEX = REPO + '/index.html'
OVERPRICING_DIR = '/tmp/claude-0/fit5/overpricing_time/patched'   # the overpricing_time fit's patched copy (if present)
B_BOOT = int(sys.argv[1]) if len(sys.argv) > 1 else 1000           # argv only for quick test runs
RUN_JS = not (len(sys.argv) > 2 and sys.argv[2] == 'nojs')
RNG = np.random.default_rng(20261010)
BANDS = ['<500K', '500K-1M', '1M-2M', '2M-5M', '5M-50M']
JS_BANDS = ['<500K', '500K-1M', '1-2M', '2-5M', '5-50M']        # keys used in index.html
CENTRES = [2.5e5, np.sqrt(5e5 * 1e6), np.sqrt(1e6 * 2e6), np.sqrt(2e6 * 5e6), np.sqrt(5e6 * 5e7)]  # BAND_KNOTS
DAYS_PER_MONTH = 30.44
MEASURES = ['listing_to_close_months', 'loi_to_close_months']
LISTING = MEASURES[0]

# ---------------------------------------------------------------- current console values (read only)
html = open(INDEX, encoding='utf-8').read()
KW_NOW = float(re.search(r'KW=([0-9.]+)', html).group(1))
ttc = json.loads('{' + re.search(r'"time_to_close":(\{.*?\}\})', html).group(0) + '}')['time_to_close']
MED_NOW = [ttc['median_months_listing_to_close_recent'][b] for b in JS_BANDS]
LOI_NOW = [ttc['median_months_loi_to_close_recent'][b] for b in JS_BANDS]

# ---------------------------------------------------------------- distribution families
LN2 = np.log(2.0)


def _logt(t):
    with np.errstate(divide='ignore'):
        return np.log(t)


def cdf(fam, th, t):
    """CDF at t (months) for unconstrained parameter vector th. t may contain 0 and inf."""
    t = np.asarray(t, float)
    lt = _logt(t)
    if fam == 'weibull':          # th = (log k, log lambda)
        k, lam = np.exp(th[0]), np.exp(th[1])
        z = np.exp(np.clip(k * (lt - np.log(lam)), -700, 700))
        return -np.expm1(-z)
    if fam == 'gamma':            # th = (log a, log scale)
        a, s = np.exp(th[0]), np.exp(th[1])
        return special.gammainc(a, np.where(np.isinf(t), 1e300, t) / s)
    if fam == 'lognormal':        # th = (mu, log sigma)
        return special.ndtr((lt - th[0]) / np.exp(th[1]))
    if fam == 'loglogistic':      # th = (log beta, log alpha); alpha is the median
        return special.expit(np.exp(th[0]) * (lt - th[1]))
    if fam == 'gengamma':         # Prentice: th = (mu, log sigma, Q)
        mu, sg, Q = th[0], np.exp(th[1]), th[2]
        w = (lt - mu) / sg
        if abs(Q) < 1e-5:
            return special.ndtr(w)
        a = 1.0 / Q ** 2
        with np.errstate(over='ignore', invalid='ignore'):
            u = a * np.exp(np.clip(Q * w, -700, 700))
        return special.gammainc(a, u) if Q > 0 else special.gammaincc(a, u)
    raise ValueError(fam)


NPAR = {'weibull': 2, 'gamma': 2, 'lognormal': 2, 'loglogistic': 2, 'gengamma': 3}
FAMS = ['weibull', 'gamma', 'lognormal', 'loglogistic']


def median_of(fam, th):
    if fam == 'weibull':
        return np.exp(th[1]) * LN2 ** (1 / np.exp(th[0]))
    if fam == 'gamma':
        return special.gammaincinv(np.exp(th[0]), 0.5) * np.exp(th[1])
    if fam == 'lognormal':
        return np.exp(th[0])
    if fam == 'loglogistic':
        return np.exp(th[1])
    return optimize.brentq(lambda x: cdf(fam, th, np.array([x]))[0] - .5, 1e-6, 1e4)


def shape_of(fam, th):
    """the scale-free dispersion parameter reported for each family"""
    if fam == 'gengamma':
        return th[2]
    return np.exp(th[1]) if fam == 'lognormal' else np.exp(th[0])


def nll(fam, th, lo, hi, c, tr=0.0):
    """interval-censored negative log-likelihood; tr > 0 = left truncation (condition on T > tr)"""
    p = cdf(fam, th, hi) - cdf(fam, th, lo)
    v = -np.sum(c * np.log(np.clip(p, 1e-300, None)))
    if tr > 0:
        v += np.sum(c) * np.log(max(1.0 - float(cdf(fam, th, np.array([tr]))[0]), 1e-300))
    return v


def start_points(fam, lo, hi, c):
    mid = np.where(np.isinf(hi), lo * 1.5, np.where(lo == 0, hi / 2, (lo + hi) / 2))
    mid = np.maximum(mid, 0.05)
    w = c / c.sum()
    m, s = np.sum(w * np.log(mid)), np.sqrt(np.sum(w * (np.log(mid) - np.sum(w * np.log(mid))) ** 2))
    s = max(s, 0.2)
    k0 = 1.2 / s
    if fam == 'weibull':
        return [[np.log(k0), m + 0.3], [np.log(1.0), m + 0.4], [np.log(2.0), m + 0.2]]
    if fam == 'gamma':
        a0 = max(1 / s ** 2, 0.3)
        return [[np.log(a0), m - np.log(a0) + 0.2], [np.log(1.5), m - 0.2], [np.log(3), m - 0.9]]
    if fam == 'lognormal':
        return [[m, np.log(s)], [m + 0.2, np.log(0.8)]]
    if fam == 'loglogistic':
        return [[np.log(1.8 / s), m], [np.log(2.0), m + 0.1]]
    if fam == 'gengamma':
        return [[m, np.log(s), 0.5], [m, np.log(s), 1.0], [m, np.log(s), 0.05], [m + .1, np.log(s), -0.3]]


def fit(fam, lo, hi, c, x0=None, fixed=None, tr=0.0):
    """Interval-censored MLE. fixed={'idx': i, 'val': v} holds one unconstrained parameter fixed."""
    keep = c > 0
    lo, hi, c = lo[keep], hi[keep], c[keep]
    starts = [x0] if x0 is not None else start_points(fam, lo, hi, c)
    best = None
    for s0 in starts:
        s0 = np.array(s0, float)
        if fixed is not None:
            free = [i for i in range(len(s0)) if i != fixed['idx']]

            def f(x):
                th = s0.copy(); th[free] = x; th[fixed['idx']] = fixed['val']
                return nll(fam, th, lo, hi, c, tr)
            r = optimize.minimize(f, s0[free], method='Nelder-Mead', options=dict(xatol=1e-8, fatol=1e-10, maxiter=4000))
            th = s0.copy(); th[free] = r.x; th[fixed['idx']] = fixed['val']
            r.x = th
        else:
            r = optimize.minimize(lambda th: nll(fam, th, lo, hi, c, tr), s0, method='BFGS', options=dict(gtol=1e-7))
            if not np.isfinite(r.fun):
                continue
            r2 = optimize.minimize(lambda th: nll(fam, th, lo, hi, c, tr), r.x, method='Nelder-Mead',
                                   options=dict(xatol=1e-9, fatol=1e-11, maxiter=4000))
            if r2.fun < r.fun:
                r = r2
        if best is None or r.fun < best.fun:
            best = r
    return np.array(best.x), float(best.fun)


def hessian(f, x, h=1e-4):
    x = np.asarray(x, float); n = len(x); H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            e_i = np.zeros(n); e_j = np.zeros(n); e_i[i] = h; e_j[j] = h
            H[i, j] = H[j, i] = (f(x + e_i + e_j) - f(x + e_i - e_j) - f(x - e_i + e_j) + f(x - e_i - e_j)) / (4 * h * h)
    return H


def hessian_se(fam, th, lo, hi, c, tr=0.0):
    keep = c > 0
    H = hessian(lambda x: nll(fam, x, lo[keep], hi[keep], c[keep], tr), th)
    cov = np.linalg.inv(H)
    se_th = np.sqrt(np.diag(cov))
    sh = shape_of(fam, th)
    if fam == 'gengamma':
        se_sh = se_th[2]
    elif fam == 'lognormal':
        se_sh = sh * se_th[1]
    else:
        se_sh = sh * se_th[0]
    g = np.zeros(len(th))
    for i in range(len(th)):
        e = np.zeros(len(th)); e[i] = 1e-5
        g[i] = (median_of(fam, th + e) - median_of(fam, th - e)) / 2e-5
    return float(se_sh), float(np.sqrt(g @ cov @ g))


# ================================================================ 0. data, parse fix, interval specs
def load_ibba(fix=True):
    h = pd.read_csv(IBBA)
    h = h[h.measure.isin(MEASURES)].reset_index(drop=True)
    fixes = []
    if fix:
        for (m, p, b), g in h.groupby(['measure', 'period', 'band'], sort=False):
            if not (g.category == '1.1-1.6 yr').any():
                continue
            i16 = list(g.index[g.category == '1.1-1.6 yr']); two = list(g.index[g.category == '2 mo'])
            # chart order: ..., 12 mo, 1.1-1.5 yr, 1.6-2 yr, >2 yr. The second '2 mo' sits after the year bar.
            assert len(i16) == 1 and len(two) == 2 and two[0] < i16[0] < two[1] and not (g.category == '1.6-2 yr').any()
            fixes.append(dict(measure=m, period=p, band=b, pct_1_1_to_1_5_yr=int(h.loc[i16[0], 'pct']),
                              pct_1_6_to_2_yr=int(h.loc[two[1], 'pct']), n_closed=int(h.loc[i16[0], 'n_closed']),
                              deals_moved_from_2mo_to_19_24mo=float(h.loc[two[1], 'pct'] / h.loc[two[1], 'row_sum'] * h.loc[two[1], 'n_closed'])))
            h.loc[i16[0], 'category'] = '1.1-1.5 yr'; h.loc[two[1], 'category'] = '1.6-2 yr'
        assert len(fixes) == 3, fixes
        assert not h.duplicated(['measure', 'period', 'band', 'category']).any()
    return h, fixes


H_FIX, PARSE_FIXES = load_ibba(True)
H_RAW, _ = load_ibba(False)

SPECS = {
    'central':          dict(conv='round', lt1='merge', post=None, fix=True),
    'floor':            dict(conv='floor', lt1='merge', post=None, fix=True),
    'lt1_half':         dict(conv='round', lt1='half', post=None, fix=True),    # round 1's mapping, data fixed
    'lt1_unit':         dict(conv='round', lt1='unit', post=None, fix=True),
    'lt1_drop':         dict(conv='round', lt1='drop', post=None, fix=True),    # left-truncated at 0.5 months
    'censor18':         dict(conv='round', lt1='merge', post='censor', fix=True),
    'censor18_lt1_half': dict(conv='round', lt1='half', post='censor', fix=True),
    'coarse':           dict(conv='round', lt1='merge', post='coarse', fix=True),
    'heap':             dict(conv='round', lt1='merge', post='heap', fix=True),
    'round1_unfixed':   dict(conv='round', lt1='half', post=None, fix=False),   # exactly round 1's inputs
}
SPEC_LIST = {LISTING: list(SPECS), 'loi_to_close_months': ['central', 'floor', 'lt1_half', 'lt1_unit', 'lt1_drop']}
LT1_SPECS = ['central', 'lt1_half', 'lt1_unit', 'lt1_drop']


def interval(cat, conv, lt1):
    """map a dropdown category to [lo, hi) months"""
    off = 0.5 if conv == 'round' else 0.0          # boundaries at k-0.5 (round) or k (floor)
    if cat == '<1 mo':
        return {'merge': (0.0, 2 - off), 'half': (0.0, 1 - off), 'unit': (0.0, 1.0), 'drop': (np.nan, np.nan)}[lt1]
    if cat == '1 mo':
        return {'merge': (0.0, 2 - off), 'half': (1 - off, 2 - off), 'unit': (1.0, 2 - off), 'drop': (1 - off, 2 - off)}[lt1]
    m = re.fullmatch(r'(\d+) mo', cat)
    if m:
        k = float(m.group(1)); return (k - off, k + 1 - off)
    if cat == '1.1-1.5 yr':
        return (13 - off, 19 - off)
    if cat == '1.6-2 yr':
        return (19 - off, 25 - off)
    if cat == '1.1-1.6 yr':          # only in the unfixed data (parse error): union of the two year bins
        return (13 - off, 25 - off)
    if cat == '>2 yr':
        return (25 - off, np.inf)
    raise ValueError(cat)


COARSE = [0, 2.5, 5.5, 8.5, 12.5, 18.5, 24.5, np.inf]
HEAP = {(5.5, 6.5): (4.0, 8.0), (11.5, 12.5): (9.0, 15.0)}


def cells(h, spec, nominal_n=None):
    s = SPECS[spec]
    g = h.copy()
    if nominal_n is not None:
        g['n_closed'] = nominal_n
    g['count'] = g.pct / g.row_sum * g.n_closed
    iv = [interval(c, s['conv'], s['lt1']) for c in g.category]
    g['lo'] = [a for a, b in iv]; g['hi'] = [b for a, b in iv]
    g = g[g.lo.notna()].copy()
    if s['post'] == 'censor':
        cut = 18.5
        sel = g.lo >= cut
        g.loc[sel, 'lo'] = cut; g.loc[sel, 'hi'] = np.inf
    elif s['post'] == 'coarse':
        g['lo'] = [max(e for e in COARSE[:-1] if e <= l) for l in g.lo]
        g['hi'] = [min(e for e in COARSE[1:] if e >= u) for u in g.hi]
    elif s['post'] == 'heap':
        nl = [HEAP.get((a, b), (a, b)) for a, b in zip(g.lo, g.hi)]
        g['lo'] = [a for a, b in nl]; g['hi'] = [b for a, b in nl]
    tr = (1.0 - (0.5 if s['conv'] == 'round' else 0.0)) if s['lt1'] == 'drop' else 0.0
    return g, tr


def matrices(g, band):
    """per-quarter count matrix over the band's unique intervals"""
    g = g[g.band == band]
    ints = sorted(set(zip(g.lo, g.hi)))
    qs = sorted(g.period.unique())
    C = np.zeros((len(qs), len(ints)))
    idx = {iv: j for j, iv in enumerate(ints)}
    for p, lo_, hi_, cnt in zip(g.period, g.lo, g.hi, g['count']):
        C[qs.index(p), idx[(lo_, hi_)]] += cnt
    lo = np.array([a for a, b in ints]); hi = np.array([b for a, b in ints])
    return qs, lo, hi, C


def grouped_median(lo, hi, c):
    """median from grouped data, uniform within the bin that holds it (always a single-month bin here)"""
    o = np.argsort(lo); lo, hi, c = lo[o], hi[o], c[o]
    cum = np.cumsum(c) / c.sum(); prev = np.concatenate([[0], cum[:-1]])
    j = int(np.argmax(cum >= 0.5))
    return float(lo[j] + (0.5 - prev[j]) / (cum[j] - prev[j]) * (hi[j] - lo[j]))


def median_bin(lo, hi, c):
    o = np.argsort(lo); lo, hi, c = lo[o], hi[o], c[o]
    cum = np.cumsum(c) / c.sum()
    j = int(np.argmax(cum >= 0.5))
    return [float(lo[j]), float(hi[j])]


# ================================================================ 1. pooled fits per band and spec
results = {'meta': dict(kw_now=KW_NOW, median_now_months=dict(zip(BANDS, MED_NOW)), loi_now_months=dict(zip(BANDS, LOI_NOW)),
                        b_boot=B_BOOT, source=IBBA, specs=SPECS, parse_fixes=PARSE_FIXES,
                        quarters=sorted(H_FIX[H_FIX.measure == LISTING].period.unique()))}
fit_rows = []
DATA = {}
for measure in MEASURES:
    for spec in SPEC_LIST[measure]:
        g, tr = cells(H_FIX if SPECS[spec]['fix'] else H_RAW[H_RAW.measure == measure].copy(), spec)
        g = g[g.measure == measure]
        for band in BANDS:
            qs, lo, hi, C = matrices(g, band)
            DATA[(measure, spec, band)] = (qs, lo, hi, C, tr)
            c = C.sum(0)
            ths = {}
            fams = FAMS + (['gengamma'] if spec == 'central' else [])
            for fam in fams:
                if fam == 'gengamma':
                    th_ln = ths['lognormal']; th_w = ths['weibull']
                    s_w = 1 / np.exp(th_w[0])
                    starts = [[th_ln[0], th_ln[1], 0.02], [th_w[1], np.log(s_w), 1.0],
                              [th_ln[0], th_ln[1], 0.5], [th_ln[0], th_ln[1], -0.3]]
                    best = None
                    for s0 in starts:
                        th, f = fit(fam, lo, hi, c, x0=s0, tr=tr)
                        if best is None or f < best[1]:
                            best = (th, f)
                    th, f = best
                else:
                    th, f = fit(fam, lo, hi, c, tr=tr)
                ths[fam] = th
                se_sh, se_med = hessian_se(fam, th, lo, hi, c, tr) if spec == 'central' else (np.nan, np.nan)
                fit_rows.append(dict(measure=measure, spec=spec, band=band, family=fam, n=c.sum(), n_quarters=len(qs),
                                     nll=f, aic=2 * f + 2 * NPAR[fam], shape=shape_of(fam, th), shape_se_hessian=se_sh,
                                     median=median_of(fam, th), median_se_hessian=se_med, th=list(map(float, th)),
                                     grouped_median=grouped_median(lo, hi, c) if tr == 0 else np.nan))
fits = pd.DataFrame(fit_rows)
fits['daic'] = fits.aic - fits.groupby(['measure', 'spec', 'band']).aic.transform('min')
fits.drop(columns='th').to_csv(os.path.join(OUT, 'ibba_fits_by_band.csv'), index=False)
TH = {(r.measure, r.spec, r.band, r.family): np.array(r.th) for r in fits.itertuples()}
QS = DATA[(LISTING, 'central', BANDS[0])][0]
for k, v in DATA.items():
    assert v[0] == QS, k                           # every band has the same 15 quarters -> joint bootstrap
print('[1] pooled fits done %.0fs' % (time.time() - T0))

# median pinned to the console's band median: profile shape (central spec)
PINNED_PROFILE = {}
for i, band in enumerate(BANDS):
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    c = C.sum(0)
    thl, _ = fit('loglogistic', lo, hi, c, x0=TH[(LISTING, 'central', band, 'loglogistic')], fixed={'idx': 1, 'val': np.log(MED_NOW[i])})
    PINNED_PROFILE[band] = dict(loglogistic_beta_with_console_median=float(np.exp(thl[0])))

# ================================================================ 2. cluster bootstrap over quarters, joint across bands
Q = len(QS)
W = RNG.multinomial(Q, np.ones(Q) / Q, size=B_BOOT)
boot = {}
for measure in MEASURES:
    for band in BANDS:
        qs, lo, hi, C, tr = DATA[(measure, 'central', band)]
        res = {f: np.empty(B_BOOT) for f in FAMS}
        med = np.empty(B_BOOT)
        for b in range(B_BOOT):
            c = W[b] @ C
            med[b] = grouped_median(lo, hi, c)
            for fam in FAMS:
                th, _ = fit(fam, lo, hi, c, x0=TH[(measure, 'central', band, fam)])
                res[fam][b] = shape_of(fam, th)
        boot[(measure, band)] = dict(res, grouped_median=med)
print('[2] bootstrap done %.0fs' % (time.time() - T0))

NGG = min(300, B_BOOT)
ggQ = {}
for band in BANDS:
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    v = []
    for b in range(NGG):
        th, _ = fit('gengamma', lo, hi, W[b] @ C, x0=TH[(LISTING, 'central', band, 'gengamma')])
        v.append(th[2])
    ggQ[band] = np.array(v)
print('[2b] gengamma bootstrap done %.0fs' % (time.time() - T0))

BOOT_COV = {}
for measure in MEASURES:
    M = np.c_[[boot[(measure, b)]['loglogistic'] for b in BANDS]]
    BOOT_COV[measure] = dict(loglogistic_beta_corr=np.corrcoef(M).round(3).tolist())


def fval(measure, spec, band, fam, what='shape'):
    r = fits[(fits.measure == measure) & (fits.spec == spec) & (fits.band == band) & (fits.family == fam)].iloc[0]
    return float(r[what])


band_tab = []
for measure in MEASURES:
    for i, band in enumerate(BANDS):
        f = fits[(fits.measure == measure) & (fits.band == band)]
        fr = f[f.spec == 'central'].set_index('family')
        bt = boot[(measure, band)]
        row = dict(measure=measure, band=band, centre_usd=CENTRES[i], n_deals=round(fr.loc['weibull', 'n']),
                   n_quarters=int(fr.loc['weibull', 'n_quarters']),
                   weibull_k=fr.loc['weibull', 'shape'], weibull_k_se_hess=fr.loc['weibull', 'shape_se_hessian'],
                   weibull_k_se_boot=bt['weibull'].std(ddof=1),
                   weibull_k_ci95=list(np.percentile(bt['weibull'], [2.5, 97.5])),
                   loglogistic_beta=fr.loc['loglogistic', 'shape'], loglogistic_beta_se_hess=fr.loc['loglogistic', 'shape_se_hessian'],
                   loglogistic_beta_se_boot=bt['loglogistic'].std(ddof=1),
                   loglogistic_beta_ci95=list(np.percentile(bt['loglogistic'], [2.5, 97.5])),
                   gamma_a=fr.loc['gamma', 'shape'], gamma_a_se_boot=bt['gamma'].std(ddof=1),
                   lognormal_sigma=fr.loc['lognormal', 'shape'], lognormal_sigma_se_boot=bt['lognormal'].std(ddof=1),
                   gengamma_Q=(fr.loc['gengamma', 'shape'] if 'gengamma' in fr.index else np.nan),
                   gengamma_Q_se_hess=(fr.loc['gengamma', 'shape_se_hessian'] if 'gengamma' in fr.index else np.nan),
                   gengamma_Q_se_boot=(ggQ[band].std(ddof=1) if measure == LISTING else np.nan),
                   grouped_median=fr.loc['weibull', 'grouped_median'], grouped_median_se_boot=bt['grouped_median'].std(ddof=1),
                   console_median=(MED_NOW if measure == LISTING else LOI_NOW)[i],
                   daic_weibull=fr.loc['weibull', 'daic'], daic_gamma=fr.loc['gamma', 'daic'],
                   daic_lognormal=fr.loc['lognormal', 'daic'], daic_loglogistic=fr.loc['loglogistic', 'daic'],
                   daic_gengamma=(fr.loc['gengamma', 'daic'] if 'gengamma' in fr.index else np.nan),
                   best_aic=fr.daic.idxmin())
        for spec in SPEC_LIST[measure]:
            row['weibull_k__' + spec] = fval(measure, spec, band, 'weibull')
            row['loglogistic_beta__' + spec] = fval(measure, spec, band, 'loglogistic')
            row['grouped_median__' + spec] = fval(measure, spec, band, 'weibull', 'grouped_median')
        for col in ['weibull_k', 'loglogistic_beta']:
            row[col + '_floor'] = row[col + '__floor']
            row[col + '_conv_half_gap'] = abs(row[col + '__floor'] - row[col]) / 2
            lt = [row[col + '__' + s] for s in LT1_SPECS]
            row[col + '_lt1_half_range'] = (max(lt) - min(lt)) / 2
        band_tab.append(row)
band_tab = pd.DataFrame(band_tab)


# ================================================================ 3. empirical Bayes: shrink toward a line in ln(size)
def eb_mean(est, se):
    """round 1: DerSimonian-Laird random effects, shrink toward the precision-weighted mean"""
    est, se = np.asarray(est, float), np.asarray(se, float)
    w = 1 / se ** 2
    mu = np.sum(w * est) / w.sum()
    k = len(est)
    Qs = np.sum(w * (est - mu) ** 2)
    tau2 = max(0.0, (Qs - (k - 1)) / (w.sum() - np.sum(w ** 2) / w.sum()))
    wr = 1 / (se ** 2 + tau2)
    mu_r = np.sum(wr * est) / wr.sum()
    Bf = tau2 / (tau2 + se ** 2)
    post = mu_r + Bf * (est - mu_r)
    post_se = np.sqrt(Bf * se ** 2 + (1 - Bf) ** 2 / wr.sum())
    return dict(target='weighted mean', mu=float(mu_r), tau=float(np.sqrt(tau2)), Q=float(Qs), df=k - 1,
                weight_on_band=list(map(float, Bf)), post=list(map(float, post)), post_se=list(map(float, post_se)))


def eb_trend(est, se, x):
    """Fay-Herriot: shrink each band toward a WLS line in x = ln(centre/1M); tau^2 by the DerSimonian-Laird
    moment estimator for meta-regression; posterior MSE = B se^2 + (1-B)^2 Var(line at x)."""
    est, se, x = np.asarray(est, float), np.asarray(se, float), np.asarray(x, float)
    k = len(est); X = np.c_[np.ones(k), x]; p = X.shape[1]

    def wls(w):
        A = (X.T * w) @ X
        return np.linalg.solve(A, (X.T * w) @ est), np.linalg.inv(A)
    w = 1 / se ** 2
    b0, A0 = wls(w)
    Qr = float(np.sum(w * (est - X @ b0) ** 2))
    trP = float(np.sum(w) - np.trace(A0 @ ((X.T * w ** 2) @ X)))
    tau2 = max(0.0, (Qr - (k - p)) / trP)
    b, cov = wls(1 / (se ** 2 + tau2))
    pred = X @ b
    Bf = tau2 / (tau2 + se ** 2)
    post = pred + Bf * (est - pred)
    var_pred = np.einsum('ij,jk,ik->i', X, cov, X)
    post_se = np.sqrt(Bf * se ** 2 + (1 - Bf) ** 2 * var_pred)
    return dict(target='WLS line in ln(value)', intercept_at_1M=float(b[0]), slope=float(b[1]),
                slope_se=float(np.sqrt(cov[1, 1])), tau=float(np.sqrt(tau2)), Q_resid=Qr, df=k - p,
                weight_on_band=list(map(float, Bf)), line=list(map(float, pred)),
                post=list(map(float, post)), post_se=list(map(float, post_se)))


XC = np.log(np.array(CENTRES) / 1e6)
EB, EB_MEAN = {}, {}
for measure in MEASURES:
    bt = band_tab[band_tab.measure == measure]
    EB[measure], EB_MEAN[measure] = {}, {}
    for col, sec in [('weibull_k', 'weibull_k_se_boot'), ('loglogistic_beta', 'loglogistic_beta_se_boot'),
                     ('lognormal_sigma', 'lognormal_sigma_se_boot'), ('gamma_a', 'gamma_a_se_boot')]:
        EB[measure][col] = eb_trend(bt[col], bt[sec], XC)
        EB_MEAN[measure][col] = eb_mean(bt[col], bt[sec])
        band_tab.loc[band_tab.measure == measure, col + '_eb'] = EB[measure][col]['post']
        band_tab.loc[band_tab.measure == measure, col + '_eb_se'] = EB[measure][col]['post_se']
        band_tab.loc[band_tab.measure == measure, col + '_eb_mean'] = EB_MEAN[measure][col]['post']

# trend of the shape in ln(centre) (WLS with bootstrap SEs): is a straight line enough?
TREND = {}
for measure in MEASURES:
    bt = band_tab[band_tab.measure == measure]
    TREND[measure] = {}
    for col in ['weibull_k', 'loglogistic_beta']:
        y = bt[col].values; w = 1 / bt[col + '_se_boot'].values ** 2
        X = np.c_[np.ones_like(XC), XC]
        A = (X.T * w) @ X
        beta = np.linalg.solve(A, (X.T * w) @ y); cov = np.linalg.inv(A)
        chi2 = float(np.sum(w * (y - X @ beta) ** 2))
        se_disp = float(np.sqrt(cov[1, 1]) * np.sqrt(max(1.0, chi2 / (len(XC) - 2))))   # scaled for the line's misfit
        TREND[measure][col] = dict(intercept_at_1M=float(beta[0]), slope_per_ln_value=float(beta[1]),
                                   slope_se_inverse_variance=float(np.sqrt(cov[1, 1])),
                                   slope_se_dispersion_scaled=se_disp, slope_z_dispersion_scaled=float(beta[1] / se_disp),
                                   fay_herriot_slope=EB[measure][col]['slope'], fay_herriot_slope_se=EB[measure][col]['slope_se'],
                                   resid_chi2=chi2, df=len(XC) - 2)
for col in ['weibull_k', 'loglogistic_beta']:
    band_tab[col + '_se_total'] = np.sqrt(band_tab[col + '_eb_se'] ** 2 + band_tab[col + '_conv_half_gap'] ** 2
                                          + band_tab[col + '_lt1_half_range'] ** 2)
band_tab.to_csv(os.path.join(OUT, 'band_shape_table.csv'), index=False)
print('[3] EB done %.0fs' % (time.time() - T0))

# sensitivity table (listing -> close): raw shape under each spec, shift from central, |shift| / total SE
lt_ = band_tab[band_tab.measure == LISTING].reset_index(drop=True)
sens = []
for spec in SPEC_LIST[LISTING]:
    for i, band in enumerate(BANDS):
        b_ = lt_.loc[i, 'loglogistic_beta__' + spec]; k_ = lt_.loc[i, 'weibull_k__' + spec]
        sens.append(dict(spec=spec, band=band, loglogistic_beta=b_, shift_vs_central=b_ - lt_.loc[i, 'loglogistic_beta'],
                         shift_in_total_se=(b_ - lt_.loc[i, 'loglogistic_beta']) / lt_.loc[i, 'loglogistic_beta_se_total'],
                         weibull_k=k_, grouped_median=lt_.loc[i, 'grouped_median__' + spec]))
sens = pd.DataFrame(sens)
sens.to_csv(os.path.join(OUT, 'sensitivity_table.csv'), index=False)


# ================================================================ 3b. structure of the size effect: is there a gradient above $500K?
def fit_common(fam, cells_, x0, tr=0.0, polish=True):
    """ONE shape across the given bands and a free scale (median for the log-logistic) per band: joint
    interval-censored MLE. x = (log shape, log scale_1..m)."""
    def f(x):
        return sum(nll(fam, np.array([x[0], x[1 + j]]), lo, hi, c, tr) for j, (lo, hi, c) in enumerate(cells_))
    r = optimize.minimize(f, np.asarray(x0, float), method='BFGS', options=dict(gtol=1e-8))
    if polish:
        r2 = optimize.minimize(f, r.x, method='Nelder-Mead', options=dict(xatol=1e-9, fatol=1e-11, maxiter=8000))
        if r2.fun < r.fun:
            r = r2
    return np.array(r.x), float(r.fun)


def step_partial_pool(est, se):
    """Fay-Herriot toward a step at $500K: the <500K band is its own group (kept as is); the four upper bands
    are shrunk toward their random-effects mean, tau^2 by the DerSimonian-Laird moment estimator."""
    est, se = np.asarray(est, float), np.asarray(se, float)
    bu, su = est[1:], se[1:]
    w = 1 / su ** 2; mu = np.sum(w * bu) / w.sum(); Qs = np.sum(w * (bu - mu) ** 2)
    t2 = max(0.0, (Qs - (len(bu) - 1)) / (w.sum() - np.sum(w ** 2) / w.sum()))
    wr = 1 / (su ** 2 + t2); mur = np.sum(wr * bu) / wr.sum(); Bf = t2 / (t2 + su ** 2)
    return np.r_[est[0], mur + Bf * (bu - mur)], float(t2), Bf


def pava(y, w):
    """weighted isotonic (non-decreasing) regression, pool-adjacent-violators"""
    blocks = [[float(a), float(b), 1] for a, b in zip(y, w)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            a, b = blocks[i], blocks[i + 1]; ww = a[1] + b[1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / ww, ww, a[2] + b[2]]; del blocks[i + 1]; i = max(i - 1, 0)
        else:
            i += 1
    return np.array([v for v, _, n in blocks for _ in range(n)])


UP = BANDS[1:]


def upper_cells(spec, wq=None):
    out = []
    for b in UP:
        qs, lo, hi, C, tr = DATA[(LISTING, spec, b)]
        out.append((lo, hi, C.sum(0) if wq is None else wq @ C))
    return out, DATA[(LISTING, spec, UP[0])][4]


TWO = {}
for spec in SPEC_LIST[LISTING]:
    cs, tr = upper_cells(spec)
    x, f = fit_common('loglogistic', cs, [np.log(2.6)] + [TH[(LISTING, spec, b, 'loglogistic')][1] for b in UP], tr)
    xw, fw = fit_common('weibull', cs, [np.log(1.7)] + [TH[(LISTING, spec, b, 'weibull')][1] for b in UP], tr)
    TWO[spec] = dict(beta_lt500k=fval(LISTING, spec, '<500K', 'loglogistic'), beta_upper=float(np.exp(x[0])),
                     upper_medians=[float(np.exp(v)) for v in x[1:]], weibull_k_lt500k=fval(LISTING, spec, '<500K', 'weibull'),
                     weibull_k_upper=float(np.exp(xw[0])), x_ll=list(map(float, x)), x_w=list(map(float, xw)))
# quarter bootstrap of the pooled upper beta, with the same quarter draws W as the band bootstrap (joint)
BU = np.empty(B_BOOT)
for b in range(B_BOOT):
    BU[b] = np.exp(fit_common('loglogistic', upper_cells('central', W[b])[0], TWO['central']['x_ll'], polish=False)[0][0])
BKU = np.empty(NGG)
for b in range(NGG):
    BKU[b] = np.exp(fit_common('weibull', upper_cells('central', W[b])[0], TWO['central']['x_w'], polish=False)[0][0])
B_LT = boot[(LISTING, '<500K')]['loglogistic']


def level_summary(key, bs):
    vals = {s: TWO[s][key] for s in SPEC_LIST[LISTING]}
    conv = abs(vals['floor'] - vals['central']) / 2
    lt1 = (max(vals[s] for s in LT1_SPECS) - min(vals[s] for s in LT1_SPECS)) / 2
    se_b = float(np.std(bs, ddof=1))
    return dict(estimate=vals['central'], se_boot=se_b, ci95=list(map(float, np.percentile(bs, [2.5, 97.5]))),
                conv_half_gap=float(conv), lt1_half_range=float(lt1), se_total=float(np.sqrt(se_b ** 2 + conv ** 2 + lt1 ** 2)),
                by_spec=vals)


LEVELS = dict(lt500k=level_summary('beta_lt500k', B_LT), upper=level_summary('beta_upper', BU),
              weibull_k_lt500k=level_summary('weibull_k_lt500k', boot[(LISTING, '<500K')]['weibull']),
              weibull_k_upper=level_summary('weibull_k_upper', BKU))
LEVELS['step'] = dict(estimate=LEVELS['upper']['estimate'] - LEVELS['lt500k']['estimate'],
                      se_boot=float(np.std(BU - B_LT, ddof=1)), corr_boot=float(np.corrcoef(BU, B_LT)[0, 1]))
LEVELS['step']['z'] = LEVELS['step']['estimate'] / LEVELS['step']['se_boot']

# homogeneity of the four upper bands; slope among them; step vs line over all five (same number of parameters)
raw5 = lt_.loglogistic_beta.values; se5 = lt_.loglogistic_beta_se_boot.values
SIG = np.cov(np.c_[[boot[(LISTING, b)]['loglogistic'] for b in BANDS]])         # joint-bootstrap covariance
bu_, su_, Su_ = raw5[1:], se5[1:], SIG[1:, 1:]
w_ = 1 / su_ ** 2; mu_ = np.sum(w_ * bu_) / w_.sum(); Q_ind = float(np.sum(w_ * (bu_ - mu_) ** 2))
Si_ = np.linalg.inv(Su_); one = np.ones(4); mu_g = float(one @ Si_ @ bu_ / (one @ Si_ @ one)); Q_gls = float((bu_ - mu_g) @ Si_ @ (bu_ - mu_g))
Xu = np.c_[np.ones(4), XC[1:]]
A_ = (Xu.T * w_) @ Xu; bb_ = np.linalg.solve(A_, (Xu.T * w_) @ bu_); slope_up = (float(bb_[1]), float(np.sqrt(np.linalg.inv(A_)[1, 1])))
A_ = Xu.T @ Si_ @ Xu; bb_ = np.linalg.solve(A_, Xu.T @ Si_ @ bu_); slope_up_gls = (float(bb_[1]), float(np.sqrt(np.linalg.inv(A_)[1, 1])))
Si5 = np.linalg.inv(SIG)


def gls_chi2(X):
    A = X.T @ Si5 @ X; bb = np.linalg.solve(A, X.T @ Si5 @ raw5); r = raw5 - X @ bb
    return float(r @ Si5 @ r), list(map(float, bb))


chi_line, b_line = gls_chi2(np.c_[np.ones(5), XC])
chi_step, b_step = gls_chi2(np.c_[np.ones(5), (np.arange(5) == 0).astype(float)])


def q_of_tau2(t2):
    ww = 1 / (su_ ** 2 + t2); m = np.sum(ww * bu_) / ww.sum(); return float(np.sum(ww * (bu_ - m) ** 2))


def reml(t2):
    ww = 1 / (su_ ** 2 + t2); m = np.sum(ww * bu_) / ww.sum()
    return 0.5 * (np.sum(np.log(su_ ** 2 + t2)) + np.log(ww.sum()) + np.sum(ww * (bu_ - m) ** 2))


t2_lo = 0.0 if q_of_tau2(0) < stats.chi2.ppf(.975, 3) else optimize.brentq(lambda t: q_of_tau2(t) - stats.chi2.ppf(.975, 3), 0, 10)
t2_hi = optimize.brentq(lambda t: q_of_tau2(t) - stats.chi2.ppf(.025, 3), 0, 10)
pp, t2_dl, B_pp = step_partial_pool(raw5, se5)
STRUCT = dict(homogeneity_upper_independent=dict(Q=Q_ind, df=3, p=float(stats.chi2.sf(Q_ind, 3)), mean=float(mu_)),
              homogeneity_upper_gls_boot_cov=dict(Q=Q_gls, df=3, p=float(stats.chi2.sf(Q_gls, 3)), mean=mu_g),
              slope_upper_wls=dict(slope=slope_up[0], se=slope_up[1], z=slope_up[0] / slope_up[1]),
              slope_upper_gls=dict(slope=slope_up_gls[0], se=slope_up_gls[1], z=slope_up_gls[0] / slope_up_gls[1]),
              all5_gls_line=dict(chi2=chi_line, df=3, p=float(stats.chi2.sf(chi_line, 3)), coef=b_line),
              all5_gls_step_at_500k=dict(chi2=chi_step, df=3, p=float(stats.chi2.sf(chi_step, 3)), coef=b_step),
              tau_upper=dict(dl=float(np.sqrt(t2_dl)), reml=float(np.sqrt(optimize.minimize_scalar(reml, bounds=(0, 1), method='bounded').x)),
                             q_profile_ci95=[float(np.sqrt(t2_lo)), float(np.sqrt(t2_hi))]),
              partial_pool_toward_step=dict(post=list(map(float, pp)), weight_on_band=[1.0] + list(map(float, B_pp))),
              isotonic=list(map(float, pava(raw5, 1 / se5 ** 2))),
              two_level_by_spec=TWO, levels=LEVELS)
print('[3b] structure done %.0fs' % (time.time() - T0))


# ================================================================ 4. out-of-sample validation
def fit_common_k(cells_, k_fixed=None):
    """Weibull with one shape across bands and a free scale per band (or k held at k_fixed)."""
    nb = len(cells_)

    def f(x):
        lk = np.log(k_fixed) if k_fixed is not None else x[0]
        lams = x[1:] if k_fixed is None else x
        return sum(nll('weibull', np.array([lk, l]), lo, hi, c) for (lo, hi, c), l in zip(cells_, lams))
    x0 = [np.log(1.5)] + [np.log(8)] * nb if k_fixed is None else [np.log(8)] * nb
    r = optimize.minimize(f, x0, method='BFGS', options=dict(gtol=1e-7))
    if k_fixed is None:
        return r.x[0], list(r.x[1:])
    return np.log(k_fixed), list(r.x)


PIN = {'weibull': lambda th, m: np.array([th[0], np.log(m / LN2 ** (1 / np.exp(th[0])))]),
       'gamma': lambda th, m: np.array([th[0], np.log(m / special.gammaincinv(np.exp(th[0]), .5))]),
       'lognormal': lambda th, m: np.array([np.log(m), th[1]]),
       'loglogistic': lambda th, m: np.array([th[0], np.log(m)])}


def evaluate_split(measure, spec, train_q, test_q):
    """held-out log-lik per band (5-vector) for each candidate representation"""
    out = {}
    cells_tr, cells_te = [], []
    for band in BANDS:
        qs, lo, hi, C, tr = DATA[(measure, spec, band)]
        assert tr == 0
        itr = [qs.index(q) for q in train_q if q in qs]; ite = [qs.index(q) for q in test_q if q in qs]
        cells_tr.append((lo, hi, C[itr].sum(0))); cells_te.append((lo, hi, C[ite].sum(0)))
    n_te = np.array([c.sum() for _, _, c in cells_te])
    meds = MED_NOW if measure == LISTING else LOI_NOW
    th_tr = {}
    for fam in FAMS:
        th_tr[fam] = [fit(fam, lo, hi, ctr, x0=TH[(measure, spec, band, fam)])[0] for (lo, hi, ctr), band in zip(cells_tr, BANDS)]
        out['%s_per_band' % fam] = np.array([-nll(fam, th, lo, hi, cte) for th, (lo, hi, cte) in zip(th_tr[fam], cells_te)])
        out['pinned_%s_per_band' % fam] = np.array([-nll(fam, PIN[fam](th, m), lo, hi, c)
                                                    for th, m, (lo, hi, c) in zip(th_tr[fam], meds, cells_te)])
    lk, lams = fit_common_k(cells_tr)
    out['weibull_common_k'] = np.array([-nll('weibull', np.array([lk, l]), lo, hi, c) for (lo, hi, c), l in zip(cells_te, lams)])
    lk, lams = fit_common_k(cells_tr, k_fixed=KW_NOW)
    out['weibull_console_k'] = np.array([-nll('weibull', np.array([lk, l]), lo, hi, c) for (lo, hi, c), l in zip(cells_te, lams)])
    # the curve the console draws today: Weibull k=KW with the median pinned to the console's band median
    out['pinned_weibull_console_k'] = np.array([-nll('weibull', np.array([np.log(KW_NOW), np.log(m / LN2 ** (1 / KW_NOW))]), lo, hi, c)
                                                for (lo, hi, c), m in zip(cells_te, meds)])
    xs = np.log(CENTRES)
    for fam in ['weibull', 'loglogistic']:
        kb = np.array([np.exp(th[0]) for th in th_tr[fam]])
        v = []
        for i, ((lo, hi, ctr), (_, _, cte)) in enumerate(zip(cells_tr, cells_te)):
            others = [j for j in range(5) if j != i]
            k_pred = float(np.interp(xs[i], xs[others], kb[others]))
            r = optimize.minimize_scalar(lambda l: nll(fam, np.array([np.log(k_pred), l]), lo, hi, ctr), bounds=(-3, 5), method='bounded')
            v.append(-nll(fam, np.array([np.log(k_pred), r.x]), lo, hi, cte))
        out['%s_shape_from_neighbour_bands' % fam] = np.array(v)
    # shape structures across bands (round 3), each estimated on the training quarters only; scored pinned to the
    # console medians with beta rounded to 2 dp (as shipped), and free (training medians)
    raw = np.array([np.exp(th[0]) for th in th_tr['loglogistic']]); lmed = np.array([th[1] for th in th_tr['loglogistic']])
    se_h = np.array([hessian_se('loglogistic', th, lo, hi, ctr)[0] for th, (lo, hi, ctr) in zip(th_tr['loglogistic'], cells_tr)])
    xu, _ = fit_common('loglogistic', cells_tr[1:], np.r_[np.log(2.6), lmed[1:]], polish=False)
    xa, _ = fit_common('loglogistic', cells_tr, np.r_[np.log(2.5), lmed], polish=False)
    struct = {'two_level': (np.r_[raw[0], [np.exp(xu[0])] * 4], np.r_[lmed[0], xu[1:]]),
              'common': (np.array([np.exp(xa[0])] * 5), np.asarray(xa[1:])),
              'eb_line': (np.array(eb_trend(raw, se_h, XC)['post']), lmed),      # round 2's pipeline (Hessian SEs in the fold)
              'eb_step': (step_partial_pool(raw, se_h)[0], lmed),
              'isotonic': (pava(raw, 1 / se_h ** 2), lmed)}
    for nm, (be, lm) in struct.items():
        out['pinned_ll_' + nm] = np.array([-nll('loglogistic', np.array([np.log(b_), np.log(m)]), lo, hi, c)
                                           for b_, m, (lo, hi, c) in zip(np.round(be, 2), meds, cells_te)])
        if nm in ('two_level', 'common'):
            out['ll_' + nm] = np.array([-nll('loglogistic', np.array([np.log(b_), l_]), lo, hi, c) for b_, l_, (lo, hi, c) in zip(be, lm, cells_te)])
    return out, n_te


PAIRS = [('loglogistic_per_band', 'weibull_per_band'), ('loglogistic_per_band', 'gamma_per_band'),
         ('loglogistic_per_band', 'lognormal_per_band'), ('gamma_per_band', 'weibull_per_band'),
         ('pinned_loglogistic_per_band', 'pinned_weibull_console_k'),     # proposed curve vs the curve drawn today
         ('pinned_weibull_per_band', 'pinned_weibull_console_k'), ('pinned_gamma_per_band', 'pinned_weibull_console_k'),
         ('pinned_loglogistic_per_band', 'pinned_weibull_per_band'),
         ('loglogistic_per_band', 'pinned_loglogistic_per_band'),         # histogram median vs console median
         ('weibull_per_band', 'weibull_common_k'), ('weibull_per_band', 'weibull_console_k'),
         ('loglogistic_per_band', 'loglogistic_shape_from_neighbour_bands'),
         ('weibull_per_band', 'weibull_shape_from_neighbour_bands'),
         # round 3: structure of the size effect, as drawn (pinned) and free
         ('pinned_ll_two_level', 'pinned_weibull_console_k'),            # RECOMMENDED curve vs the curve drawn today
         ('pinned_ll_eb_line', 'pinned_weibull_console_k'),              # round 2's curve vs today
         ('pinned_ll_two_level', 'pinned_ll_eb_line'), ('pinned_ll_two_level', 'pinned_loglogistic_per_band'),
         ('pinned_ll_two_level', 'pinned_ll_eb_step'), ('pinned_ll_two_level', 'pinned_ll_isotonic'),
         ('pinned_ll_common', 'pinned_ll_two_level'),
         ('ll_two_level', 'loglogistic_per_band'), ('ll_common', 'll_two_level'),
         ('ll_two_level', 'pinned_ll_two_level')]                         # option B: training-quarter medians vs console medians


def pair_stats(per_q, nq, a, b, quarters):
    """gain of a over b per held-out deal; SE = sqrt(Q) x sd of per-quarter gains / N (quarters independent);
    t = gain / SE referred to t(Q-1)"""
    ga = np.array([d[a].sum() for d in per_q]) - np.array([d[b].sum() for d in per_q])
    N = nq.sum(); Qn = len(ga); Nb = nq.sum(0)
    band = np.array([d[a] for d in per_q]) - np.array([d[b] for d in per_q])
    g_, s_ = float(ga.sum() / N), float(np.sqrt(Qn) * ga.std(ddof=1) / N)
    t_ = g_ / s_ if s_ > 0 else float('nan')           # identical curves (s_ = 0) -> no test
    return dict(gain_per_deal=g_, se=s_, t=t_, df=Qn - 1, p_two_sided=float(2 * stats.t.sf(abs(t_), Qn - 1)) if s_ > 0 else float('nan'),
                quarters_better=int((ga > 1e-9).sum()), quarters=Qn,
                by_band=dict(zip(BANDS, map(float, band.sum(0) / Nb))),
                by_band_se=dict(zip(BANDS, map(float, np.sqrt(Qn) * band.std(0, ddof=1) / Nb))),
                per_quarter_gain_per_deal=dict(zip(quarters, map(float, ga / nq.sum(1)))))


CV, PERQ = {}, {}
CV_SPECS = {LISTING: ['central', 'lt1_half', 'censor18', 'censor18_lt1_half'], 'loi_to_close_months': ['central']}
for measure in MEASURES:
    CV[measure] = {}
    for spec in CV_SPECS[measure]:
        allq = QS
        per_q, nq = [], []
        for q in allq:
            o, n = evaluate_split(measure, spec, [x for x in allq if x != q], [q])
            per_q.append(o); nq.append(n)
        nq = np.array(nq)
        pd.DataFrame([{**{k: v.sum() for k, v in o.items()}, 'quarter': q, 'n': n.sum()} for o, q, n in zip(per_q, allq, nq)]) \
            .to_csv(os.path.join(OUT, 'cv_loqo_%s_%s.csv' % (measure.split('_')[0], spec)), index=False)
        PERQ[(measure, spec)] = (per_q, nq)
        heldout = {nm: float(np.sum([d[nm].sum() for d in per_q]) / nq.sum()) for nm in per_q[0]}
        pairs = {'%s__vs__%s' % (a, b): pair_stats(per_q, nq, a, b, allq) for a, b in PAIRS}
        # temporal holdout: one fit on 2020Q1-2022Q4, scored per test quarter (the log-lik is additive over quarters,
        # so the totals equal one pooled test set); SE over the 4 test quarters, t(3)
        train = [q for q in allq if q <= '2022Q4']; test = [q for q in allq if q > '2022Q4']
        per_t, n_t = [], []
        for q in test:
            o, n = evaluate_split(measure, spec, train, [q]); per_t.append(o); n_t.append(n)
        n_t = np.array(n_t)
        temporal = {'%s__vs__%s' % (a, b): pair_stats(per_t, n_t, a, b, test) for a, b in PAIRS}
        temporal_ll = {nm: float(np.sum([d[nm].sum() for d in per_t]) / n_t.sum()) for nm in per_t[0]}
        # leave a block of 4 consecutive quarters out (4 folds; adjacent quarters share market conditions), t(3)
        blocks = [allq[0:4], allq[4:8], allq[8:12], allq[12:]]
        per_b, n_b = [], []
        for blk in blocks:
            o, n = evaluate_split(measure, spec, [x for x in allq if x not in blk], blk); per_b.append(o); n_b.append(n)
        n_b = np.array(n_b)
        blockcv = {'%s__vs__%s' % (a, b): pair_stats(per_b, n_b, a, b, ['-'.join([blk[0], blk[-1]]) for blk in blocks]) for a, b in PAIRS}
        CV[measure][spec] = dict(loqo_heldout_ll_per_deal=heldout, loqo_pairs=pairs, n_heldout=float(nq.sum()),
                                 temporal=dict(train=train, test=test, n_test=float(n_t.sum()), heldout_ll_per_deal=temporal_ll,
                                               pairs=temporal),
                                 block4=dict(blocks=blocks, pairs=blockcv))
print('[4] CV done %.0fs' % (time.time() - T0))

# temporal stability and closing-cohort drift: shapes fitted on 2020-22 and on 2023-25 separately
STAB = {}
for band in BANDS:
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    a = [i for i, q in enumerate(qs) if q <= '2022Q4']; b = [i for i, q in enumerate(qs) if q > '2022Q4']
    STAB[band] = dict(k_2020_2022=float(np.exp(fit('weibull', lo, hi, C[a].sum(0))[0][0])),
                      k_2023_2025=float(np.exp(fit('weibull', lo, hi, C[b].sum(0))[0][0])),
                      beta_2020_2022=float(np.exp(fit('loglogistic', lo, hi, C[a].sum(0))[0][0])),
                      beta_2023_2025=float(np.exp(fit('loglogistic', lo, hi, C[b].sum(0))[0][0])),
                      n_2020_2022=float(C[a].sum()), n_2023_2025=float(C[b].sum()))

# within-quarter shape: common shape, separate median per quarter (how much is between-quarter drift?)
FRAIL = {}
for band in BANDS:
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    cells_ = [(lo, hi, C[i]) for i in range(len(qs))]
    lk, lams = fit_common_k(cells_)
    meds = [float(np.exp(l) * LN2 ** (1 / np.exp(lk))) for l in lams]

    def fll(x):
        return sum(nll('loglogistic', np.array([x[0], x[1 + j]]), lo, hi, C[j]) for j in range(len(qs)))
    r = optimize.minimize(fll, np.r_[np.log(2.4), np.log(8) * np.ones(len(qs))], method='L-BFGS-B')
    FRAIL[band] = dict(k_within_quarter=float(np.exp(lk)), beta_within_quarter=float(np.exp(r.x[0])),
                       quarter_median_min=min(meds), quarter_median_max=max(meds),
                       quarter_grouped_median=[grouped_median(lo, hi, C[i]) for i in range(len(qs))])

# heaping: observed vs fitted counts at the 6- and 12-month answers, and Pearson chi2 per family (central spec)
HEAPING = {}
for band in BANDS:
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    c = C.sum(0); n = c.sum()
    d = {}
    for fam in FAMS:
        th = TH[(LISTING, 'central', band, fam)]
        e = n * (cdf(fam, th, hi) - cdf(fam, th, lo))
        j6 = int(np.where((lo == 5.5) & (hi == 6.5))[0][0]); j12 = int(np.where((lo == 11.5) & (hi == 12.5))[0][0])
        d[fam] = dict(obs_6mo=float(c[j6]), fit_6mo=float(e[j6]), obs_12mo=float(c[j12]), fit_12mo=float(e[j12]),
                      pearson_chi2=float(np.sum((c - e) ** 2 / e)), bins=int(len(c)))
    HEAPING[band] = d

# ================================================================ 5. practical size, size order, calibration
lt = band_tab[band_tab.measure == LISTING].reset_index(drop=True)
li = band_tab[band_tab.measure == 'loi_to_close_months'].reset_index(drop=True)
# Recommended: TWO LEVELS (selected in section 4b/4 by the fewest-parameters-within-one-SE rule); round 2's five
# band values (EB toward the line) are kept for comparison.
BETA_TWO = np.array([LEVELS['lt500k']['estimate']] + [LEVELS['upper']['estimate']] * 4)
BETA_REC = np.round(BETA_TWO, 2)
BETA_SE_REC = np.round([LEVELS['lt500k']['se_total']] + [LEVELS['upper']['se_total']] * 4, 3)
BETA_EB5 = np.round(lt.loglogistic_beta_eb.values, 2)
HIST_MED = lt.grouped_median.values


def emp_cdf_band(band, spec='central'):
    qs, lo, hi, C, tr = DATA[(LISTING, spec, band)]
    c = C.sum(0)
    edges = np.array(sorted(set(hi[np.isfinite(hi)]) & set(lo)))
    emp = np.array([c[hi <= e].sum() / c.sum() for e in edges])
    return edges, emp


def emp_F_days(band, d):
    edges, emp = emp_cdf_band(band)
    return float(np.interp(d / DAYS_PER_MONTH, np.r_[0.0, edges], np.r_[0.0, emp]))


grid_d = np.arange(0, 541, 1.0)
PRACT = {}
for i, band in enumerate(BANDS):
    m = MED_NOW[i]
    k, a, sg, be = lt.loc[i, 'weibull_k_eb'], lt.loc[i, 'gamma_a'], lt.loc[i, 'lognormal_sigma'], BETA_REC[i]
    tm = grid_d / DAYS_PER_MONTH
    pinned = {'console_weibull_%.2f' % KW_NOW: ('weibull', [np.log(KW_NOW), np.log(m / LN2 ** (1 / KW_NOW))]),
              'weibull_fit': ('weibull', [np.log(k), np.log(m / LN2 ** (1 / k))]),
              'gamma_fit': ('gamma', [np.log(a), np.log(m / special.gammaincinv(a, .5))]),
              'lognormal_fit': ('lognormal', [np.log(m), np.log(sg)]),
              'loglogistic_fit': ('loglogistic', [np.log(be), np.log(m)])}
    Fc = {nm: cdf(f, th, tm) for nm, (f, th) in pinned.items()}
    edges, emp = emp_cdf_band(band)
    gof_free = {fam: float(np.max(np.abs(cdf(fam, TH[(LISTING, 'central', band, fam)], edges) - emp))) for fam in FAMS + ['gengamma']}
    gof_pinned = {nm: float(np.max(np.abs(cdf(f, th, edges) - emp))) for nm, (f, th) in pinned.items()}
    mh = HIST_MED[i]
    gof_pinned_histmed = {
        'console_weibull_%.2f' % KW_NOW: float(np.max(np.abs(cdf('weibull', [np.log(KW_NOW), np.log(mh / LN2 ** (1 / KW_NOW))], edges) - emp))),
        'weibull_fit': float(np.max(np.abs(cdf('weibull', [np.log(k), np.log(mh / LN2 ** (1 / k))], edges) - emp))),
        'loglogistic_fit': float(np.max(np.abs(cdf('loglogistic', [np.log(be), np.log(mh)], edges) - emp)))}
    PRACT[band] = dict(console_median_days=m * DAYS_PER_MONTH,
                       F90={nm: float(F[90]) for nm, F in Fc.items()},
                       F180={nm: float(F[180]) for nm, F in Fc.items()},
                       F365={nm: float(F[365]) for nm, F in Fc.items()},
                       max_abs_diff_on_0_540d_vs_loglogistic={nm: float(np.max(np.abs(F - Fc['loglogistic_fit']))) for nm, F in Fc.items()},
                       max_abs_dev_from_grouped_ecdf_free_fit=gof_free,
                       max_abs_dev_from_grouped_ecdf_pinned_console_median=gof_pinned,
                       max_abs_dev_from_grouped_ecdf_pinned_histogram_median=gof_pinned_histmed,
                       emp_cdf_at_edges=dict(zip([float(e) for e in edges], [float(x) for x in emp])),
                       emp_F_at_days={d: emp_F_days(band, d) for d in (90, 180, 365, 540)})


def band_interp(price, vals):          # mirror of the JS bandInterp: linear in ln(price), flat beyond the end centres
    return np.interp(np.log(np.maximum(price, 1.0)), np.log(CENTRES), vals)


def F_curve(kind, price, tdays, meds=MED_NOW, betas=BETA_REC):
    tmed = band_interp(price, meds) * DAYS_PER_MONTH
    if kind == 'weibull_console':
        lam = tmed / LN2 ** (1 / KW_NOW)
        return 1 - np.exp(-(tdays / lam) ** KW_NOW)
    be = band_interp(price, betas)
    return 1 / (1 + (tdays / tmed) ** (-be))


VGRID = np.exp(np.linspace(np.log(1e5), np.log(3e7), 6001))
CURVES = {'current (Weibull 1.42, console medians)': dict(kind='weibull_console', meds=MED_NOW),
          'proposed (log-logistic, console medians)': dict(kind='ll', meds=MED_NOW),
          'round 2 five-band betas (console medians)': dict(kind='ll', meds=MED_NOW, betas=BETA_EB5),
          'proposed shape on histogram medians': dict(kind='ll', meds=list(HIST_MED))}
SIZE_ORDER, CALIB, rows_sc = {}, {}, []
for nm, cv in CURVES.items():
    SIZE_ORDER[nm], CALIB[nm] = {}, {}
    for d in (90, 180, 365, 540):
        F = F_curve(cv['kind'], VGRID, d, meds=cv['meds'], betas=cv.get('betas', BETA_REC))
        dF = np.diff(F)
        up = dF > 1e-12
        rise = float(np.max(F - np.minimum.accumulate(F)))           # largest rise of F with size anywhere
        SIZE_ORDER[nm][d] = dict(steps_rising=int(up.sum()), steps=int(len(dF)), max_rise_pts=100 * rise,
                                 rising_from_usd=(float(VGRID[:-1][up].min()) if up.any() else None),
                                 rising_to_usd=(float(VGRID[1:][up].max()) if up.any() else None))
    errs = []
    for i, band in enumerate(BANDS):
        CALIB[nm][band] = {}
        for d in (90, 180, 365, 540):      # 540 d is reported only (not in the 15 markers or the tests)
            f = float(F_curve(cv['kind'], np.array([CENTRES[i]]), d, meds=cv['meds'], betas=cv.get('betas', BETA_REC))[0]); h_ = PRACT[band]['emp_F_at_days'][d]
            CALIB[nm][band][d] = dict(model_pct=100 * f, hist_pct=100 * h_, err_pts=100 * (f - h_))
            if d != 540:
                errs.append(100 * (f - h_))
            rows_sc.append(dict(curve=nm, band=band, day=d, model_pct=100 * f, hist_pct=100 * h_, err_pts=100 * (f - h_)))
    CALIB[nm]['mean_abs_err_pts_15_markers'] = float(np.mean(np.abs(errs)))
    CALIB[nm]['max_abs_err_pts_15_markers'] = float(np.max(np.abs(errs)))
    for d in (90, 180, 365):
        CALIB[nm]['max_abs_err_pts_day%d' % d] = float(np.max([abs(CALIB[nm][b][d]['err_pts']) for b in BANDS]))
pd.DataFrame(rows_sc).to_csv(os.path.join(OUT, 'size_order_calibration.csv'), index=False)
HIST_ORDER = {d: [PRACT[b]['emp_F_at_days'][d] for b in BANDS] for d in (90, 180, 365, 540)}

# median diagnostics: grouped medians, the middle answer (bin holding the 50th percentile), offsets
MEDIANS = {}
for i, band in enumerate(BANDS):
    qs, lo, hi, C, tr = DATA[(LISTING, 'central', band)]
    mb = median_bin(lo, hi, C.sum(0))
    MEDIANS[band] = dict(console=MED_NOW[i], grouped=float(HIST_MED[i]), grouped_se=float(lt.loc[i, 'grouped_median_se_boot']),
                         middle_answer_months=round((mb[0] + mb[1]) / 2), console_minus_grouped=float(MED_NOW[i] - HIST_MED[i]),
                         console_minus_middle_answer=float(MED_NOW[i] - round((mb[0] + mb[1]) / 2)))
print('[5] practical done %.0fs' % (time.time() - T0))

# ================================================================ 6. cross-checks on other sources (direction only)
CROSS = {}


def pcm_with_check(p):
    """The tidy PCM 2016 table already labels each band's listing/engagement -> close chart and its LOI/offer -> close
    chart separately (measure column). Use those labels. No-op check: within each band the listing rows come first,
    the category order restarts exactly where the label changes, and each chart is in category order."""
    order = lambda c: 0 if c == '<1 mo' else (int(c.split()[0]) if c.endswith(' mo') else {'1.1-1.5 yr': 13, '1.6-2 yr': 14, '>2 yr': 15}[c])
    info = {}
    for band, g in p.groupby('band', sort=False):
        o = [order(c) for c in g.category]
        cut = next(i for i in range(1, len(o)) if o[i] <= o[i - 1])
        assert all(o[i] > o[i - 1] for i in range(1, cut)) and all(o[i] > o[i - 1] for i in range(cut + 1, len(o)))
        assert (g.measure.iloc[:cut] == 'listing_to_close_months').all() and (g.measure.iloc[cut:] == 'loi_to_close_months').all()
        info[band] = dict(listing_rows=int(cut), loi_rows=int(len(g) - cut), order_split_agrees_with_labels=True)
    return p, info


pcm_split, PCM_SPLIT = pcm_with_check(pd.read_csv(PCM))
CROSS['pcm2016_2015deals'] = dict(label_check=PCM_SPLIT)
for measure in MEASURES:
    pcm, _ = cells(pcm_split[pcm_split.measure == measure], 'central', nominal_n=100)   # per-band n unpublished: nominal 100, no SE
    for band in BANDS:
        qs, lo, hi, C = matrices(pcm, band)
        c = C.sum(0)
        th, _ = fit('weibull', lo, hi, c); thl, _ = fit('lognormal', lo, hi, c); thll, _ = fit('loglogistic', lo, hi, c)
        CROSS['pcm2016_2015deals'].setdefault(band, {})[measure] = dict(
            weibull_k=float(np.exp(th[0])), lognormal_sigma=float(np.exp(thl[1])), loglogistic_beta=float(np.exp(thll[0])),
            grouped_median=grouped_median(lo, hi, c), se='not computable: n per band unpublished')
# round 1's PCM betas came from the same listing chart under round 1's reading of '<1 month' (shown here)
pcm_h, _ = cells(pcm_split[pcm_split.measure == LISTING], 'lt1_half', nominal_n=100)
for band in BANDS:
    qs, lo, hi, C = matrices(pcm_h, band)
    CROSS['pcm2016_2015deals'][band][LISTING]['loglogistic_beta_round1_reading'] = float(np.exp(fit('loglogistic', lo, hi, C.sum(0))[0][0]))


def iid_boot_fit(lo, hi, B, fams=('weibull', 'loglogistic', 'lognormal', 'gamma')):
    n = len(lo)
    est = {}
    for fam in fams:
        th, f = fit(fam, lo, hi, np.ones(n))
        bs = []
        for b in range(B):
            w = np.bincount(RNG.integers(0, n, n), minlength=n).astype(float)
            thb, _ = fit(fam, lo, hi, w, x0=th)
            bs.append(shape_of(fam, thb))
        est[fam] = dict(shape=float(shape_of(fam, th)), se_boot=float(np.std(bs, ddof=1)),
                        median_months=float(median_of(fam, th)), aic=float(2 * f + 4), n=int(n))
    m = min(est, key=lambda k: est[k]['aic'])
    for k in est:
        est[k]['daic'] = est[k]['aic'] - est[m]['aic']
    return est


B_X = min(500, B_BOOT); B_X3 = min(300, B_BOOT)
tr_ = pd.read_csv(TRANBI)
tr_ = tr_[tr_.months_hi.notna()]
lo = tr_.months_lo.values.astype(float); hi = tr_.months_hi.values.astype(float)
CROSS['tranbi'] = dict(all=iid_boot_fit(lo, hi, B_X))
med_code = tr_.seller_revenue_mid_jpy.median()
for nm, g in [('revenue_below_median', tr_[tr_.seller_revenue_mid_jpy < med_code]), ('revenue_at_or_above_median', tr_[tr_.seller_revenue_mid_jpy >= med_code])]:
    CROSS['tranbi'][nm] = iid_boot_fit(g.months_lo.values.astype(float), g.months_hi.values.astype(float), B_X3, fams=('weibull', 'loglogistic'))
ef = pd.read_csv(EF)
ef = ef[ef.days_first_listed_to_sold_hi.notna()]
lo = np.clip(ef.days_first_listed_to_sold_lo.values, 0, None) / DAYS_PER_MONTH
hi = np.maximum(ef.days_first_listed_to_sold_hi.values, 1.0) / DAYS_PER_MONTH
lo = np.minimum(lo, hi - 1e-6)
CROSS['empire_flippers'] = dict(all=iid_boot_fit(lo, hi, B_X3))
price = ef.listing_price.values
for nm, sel in [('ask_lt_100k', price < 1e5), ('ask_100k_500k', (price >= 1e5) & (price < 5e5)), ('ask_ge_500k', price >= 5e5)]:
    CROSS['empire_flippers'][nm] = iid_boot_fit(lo[sel], hi[sel], B_X3, fams=('weibull', 'loglogistic'))
fl = json.load(open(FLIPPA))
CROSS['flippa_march2026_panel'] = dict(weibull_k=fl['weibull_interval']['k_shape'], k_se_boot=fl['weibull_interval']['k_bootstrap']['se'],
                                       n=fl['weibull_interval']['n'], estimand='sale hazard over all listings incl. never-sold; length-biased stock; read from fit_march_results.json, not refitted')
print('[6] cross-checks done %.0fs' % (time.time() - T0))

# ================================================================ 7. recommended table
# Structure selection (round 3): among the structures scored as drawn (median pinned, beta rounded), take the one
# with the fewest shape parameters whose LOQO held-out log-lik (central spec) is within one SE of the best.
NPAR_STRUCT = {'pinned_ll_common': 1, 'pinned_ll_two_level': 2, 'pinned_ll_eb_step': 5, 'pinned_ll_isotonic': 5,
               'pinned_ll_eb_line': 5, 'pinned_loglogistic_per_band': 5}
SELECT = {}
for spec in CV_SPECS[LISTING]:
    per_q, nq = PERQ[(LISTING, spec)]
    hl = {k: CV[LISTING][spec]['loqo_heldout_ll_per_deal'][k] for k in NPAR_STRUCT}
    best = max(hl, key=hl.get)
    vs = {k: pair_stats(per_q, nq, k, best, QS) for k in NPAR_STRUCT}
    ok_ = [k for k in sorted(NPAR_STRUCT, key=lambda k: (NPAR_STRUCT[k], -hl[k])) if vs[k]['gain_per_deal'] >= -vs[k]['se']]
    SELECT[spec] = dict(best=best, heldout_ll_per_deal=hl, n_shape_params=NPAR_STRUCT, selected=ok_[0],
                        vs_best={k: dict(gain_per_deal=v['gain_per_deal'], se=v['se'], quarters_better=v['quarters_better']) for k, v in vs.items()})
assert SELECT['central']['selected'] == 'pinned_ll_two_level', SELECT['central']

# Stated judgment prior centred on today's curve (Weibull k=KW mapped to the log-logistic with the same t75/t25),
# N(that, 0.5^2), combined with the total SE: shows how far a judgment anchor would move the fitted values.
iqr_w = (np.log(4) / np.log(4 / 3)) ** (1 / KW_NOW)
BETA_JUDG = 2 * np.log(3) / np.log(iqr_w)
PRIOR_SD = 0.5
lev_est = np.array([LEVELS['lt500k']['estimate'], LEVELS['upper']['estimate']])
lev_se = np.array([LEVELS['lt500k']['se_total'], LEVELS['upper']['se_total']])
wd = 1 / lev_se ** 2; wp = 1 / PRIOR_SD ** 2
JUDG = dict(beta_equivalent_of_console_k=float(BETA_JUDG), prior_sd=PRIOR_SD, levels=['<500K', '500K and up'],
            weight_on_data=[float(x) for x in wd / (wd + wp)],
            posterior=[float(x) for x in (wd * lev_est + wp * BETA_JUDG) / (wd + wp)],
            shift=[float(x) for x in (wd * lev_est + wp * BETA_JUDG) / (wd + wp) - lev_est])

cvc = CV[LISTING]['central']['loqo_heldout_ll_per_deal']
eligible = {f: cvc['%s_per_band' % f] for f in ['weibull', 'lognormal', 'loglogistic']}
FAMILY = max(eligible, key=eligible.get)
assert FAMILY == 'loglogistic', eligible
two_spec = lambda key: [round(float(TWO[s_][key]), 3) for s_ in SPEC_LIST[LISTING]]
REC = dict(family=FAMILY, shape_name='beta', structure='two levels: <500K, and 500K and up (four upper bands pooled)',
           eligible_heldout_ll_per_deal=eligible, gamma_heldout_ll_per_deal=cvc['gamma_per_band'], bands=JS_BANDS,
           shape=[float(x) for x in BETA_REC],
           shape_unrounded=[float(x) for x in BETA_TWO],
           shape_se_boot=[round(LEVELS['lt500k']['se_boot'], 3)] + [round(LEVELS['upper']['se_boot'], 3)] * 4,
           shape_conv_half_gap=[round(LEVELS['lt500k']['conv_half_gap'], 3)] + [round(LEVELS['upper']['conv_half_gap'], 3)] * 4,
           shape_lt1_half_range=[round(LEVELS['lt500k']['lt1_half_range'], 3)] + [round(LEVELS['upper']['lt1_half_range'], 3)] * 4,
           shape_se_total=[float(x) for x in BETA_SE_REC],
           shape_by_spec={s_: [round(TWO[s_]['beta_lt500k'], 3), round(TWO[s_]['beta_upper'], 3)] for s_ in SPEC_LIST[LISTING]},
           band_raw=[round(float(x), 3) for x in lt.loglogistic_beta],
           band_se_boot=[round(float(x), 3) for x in lt.loglogistic_beta_se_boot],
           five_band_eb_line=[round(float(x), 3) for x in lt.loglogistic_beta_eb],
           five_band_eb_line_se_total=[round(float(x), 3) for x in lt.loglogistic_beta_se_total],
           five_band_eb_toward_mean=[round(float(x), 3) for x in lt.loglogistic_beta_eb_mean],
           partial_pool_toward_step=[round(float(x), 3) for x in STRUCT['partial_pool_toward_step']['post']],
           weibull_k_two_level=[round(LEVELS['weibull_k_lt500k']['estimate'], 3), round(LEVELS['weibull_k_upper']['estimate'], 3)],
           weibull_k_two_level_se_total=[round(LEVELS['weibull_k_lt500k']['se_total'], 3), round(LEVELS['weibull_k_upper']['se_total'], 3)],
           weibull_k_band_raw=[round(float(x), 3) for x in lt.weibull_k],
           n=[int(x) for x in lt.n_deals], n_quarters=int(lt.n_quarters.iloc[0]),
           loi_shape=[round(float(x), 2) for x in li.loglogistic_beta_eb],
           loi_shape_se_total=[round(float(x), 3) for x in li.loglogistic_beta_se_total],
           loi_hist_median=[round(float(x), 2) for x in li.grouped_median],
           loi_hist_median_se=[round(float(x), 2) for x in li.grouped_median_se_boot],
           listing_hist_median=[round(float(x), 2) for x in lt.grouped_median],
           listing_hist_median_se=[round(float(x), 2) for x in lt.grouped_median_se_boot],
           listing_fitted_ll_median=[round(fval(LISTING, 'central', b, 'loglogistic', 'median'), 2) for b in BANDS],
           loi_fitted_ll_median=[round(fval('loi_to_close_months', 'central', b, 'loglogistic', 'median'), 2) for b in BANDS])
pd.DataFrame(dict(band=JS_BANDS, n=REC['n'], beta=REC['shape'], beta_se_boot=REC['shape_se_boot'], beta_se_total=REC['shape_se_total'],
                  beta_floor=[round(TWO['floor']['beta_lt500k'], 3)] + [round(TWO['floor']['beta_upper'], 3)] * 4,
                  band_beta_raw=REC['band_raw'], band_beta_se_boot=REC['band_se_boot'], five_band_eb_line=REC['five_band_eb_line'],
                  weibull_k=[REC['weibull_k_two_level'][0]] + [REC['weibull_k_two_level'][1]] * 4, console_median=MED_NOW,
                  hist_median=REC['listing_hist_median'], hist_median_se_sampling=REC['listing_hist_median_se'],
                  fitted_ll_median=REC['listing_fitted_ll_median'], console_loi=LOI_NOW,
                  hist_loi=REC['loi_hist_median'], hist_loi_se_sampling=REC['loi_hist_median_se'], loi_beta=REC['loi_shape'])
             ).to_csv(os.path.join(OUT, 'recommended_table.csv'), index=False)

# ================================================================ 8. the index.html change, applied to copies
f2 = lambda xs: '[' + ','.join('%.2f' % x for x in xs) + ']'
f1 = lambda xs: '[' + ','.join('%.1f' % x for x in xs) + ']'
N_TOT = sum(REC['n'])
NT = format(N_TOT, ',')
B_LO, B_HI = min(REC['shape']), max(REC['shape'])
QLAB = '15 quarters (2020Q1&ndash;2021Q4, 2022Q2&ndash;2023Q3 and 2025Q4)'
QLAB2 = '15 quarters, 2020Q1&ndash;2021Q4, 2022Q2&ndash;2023Q3 and 2025Q4'
pc = CV[LISTING]['central']['loqo_pairs']
PROP = pc['pinned_ll_two_level__vs__pinned_weibull_console_k']
LLW = pc['loglogistic_per_band__vs__weibull_per_band']
BNAME = {'<500K': 'under-$500K', '500K-1M': '$500K&ndash;$1M', '1M-2M': '$1&ndash;2M', '2M-5M': '$2&ndash;5M', '5M-50M': '$5&ndash;50M'}
TIE = [BNAME[b] for b in BANDS if LLW['by_band'][b] < 2 * LLW['by_band_se'][b]]
TIE_TXT = (' (its edge is within noise in the %s band%s)' % (' and '.join(TIE), 's' if len(TIE) > 1 else '')) if TIE else ''
CAL_NOW = CALIB['current (Weibull 1.42, console medians)']
I_LO, I_HI = int(np.argmin(REC['shape'])), int(np.argmax(REC['shape']))
SO = SIZE_ORDER['proposed (log-logistic, console medians)']
CAL = CALIB['proposed (log-logistic, console medians)']
OVER365 = CAL['2M-5M'][365]['err_pts']
P_HOM = sorted([STRUCT['homogeneity_upper_gls_boot_cov']['p'], STRUCT['homogeneity_upper_independent']['p']])
P_HOM = '%.2f&ndash;%.2f' % tuple(P_HOM)       # with the joint-bootstrap covariance, and treating bands as independent


def usd(x):
    return ('$%dk' % round(x / 1e3)) if x < 1e6 else ('$%.3gM' % (x / 1e6))


RISE540 = SO[540]['max_rise_pts'] if SO[540]['steps_rising'] else 0.0
RISE_TXT = ('between %s and %s' % (usd(SO[540]['rising_from_usd']), usd(SO[540]['rising_to_usd']))) if RISE540 else ''
SHORT = [i for i, b in enumerate(BANDS) if MEDIANS[b]['console_minus_grouped'] < -0.5]
SHORT_TXT = ' and '.join(BNAME[BANDS[i]] for i in SHORT)
SHORT_RNG = '%.1f&ndash;%.1f' % (min(-MEDIANS[BANDS[i]]['console_minus_grouped'] for i in SHORT), max(-MEDIANS[BANDS[i]]['console_minus_grouped'] for i in SHORT))
B_UP = REC['shape'][1]

TABLE = ('/* Shape of the time-to-close curve (fit/time_to_close_shape.py, 2026-10). IBBA / M&A Source Market Pulse per-band\n'
         '   histograms of months listing->close, 15 quarters (2020Q1-2021Q4, 2022Q2-2023Q3 and 2025Q4), %s closed deals, interval-censored\n'
         '   MLE. Log-logistic: as good as a gamma on held-out quarters, at least as good as a refitted Weibull, better than\n'
         '   a lognormal, and closed-form. beta has two levels: under $500K, and one shared value from $500K up (the four\n'
         '   upper bands differ by no more than noise and no gradient among them is identified, so they are pooled); it is\n'
         '   interpolated in ln(value) between the $250k and $707k centres, like the band medians. beta_se = quarter-bootstrap\n'
         '   SE widened for how months are reported (rounded or truncated; what "<1 month" covers). hist_* are the histograms\'\n'
         '   own grouped medians (display only); hist_*_se are quarter-bootstrap SEs, sampling only (they ignore where deals\n'
         '   sit inside a one-month answer). Closed deals only. */\n'
         'MODELS.fitted.ttc_shape={"family":"loglogistic","bands":["<500K","500K-1M","1-2M","2-5M","5-50M"],'
         '"beta":%s,"beta_se":%s,"n":%s,"n_quarters":%d,'
         '"hist_median_listing":%s,"hist_median_listing_se":%s,"hist_median_loi":%s,"hist_median_loi_se":%s,'
         '"source":"IBBA / M&A Source Market Pulse full reports, 15 quarters (2020Q1-2021Q4, 2022Q2-2023Q3 and 2025Q4), per-band histograms of months listing/engagement to close; closed deals only"};\n'
         % (NT, f2(REC['shape']), f2(REC['shape_se_total']), json.dumps(REC['n'], separators=(',', ':')), REC['n_quarters'],
            f1(REC['listing_hist_median']), f2(REC['listing_hist_median_se']), f1(REC['loi_hist_median']), f2(REC['loi_hist_median_se'])))

CODE_CURVE = """  /* drawn curve: log-logistic pinned to the FINAL median out.tMed (set above), shape beta by size band */
  const betaT=FT.beta, tMd=out.tMed;
  const Ffit=t=>t>0?1/(1+Math.pow(t/tMd,-betaT)):0;
  out.lamE=tMd; out.betaT=betaT; out.F=Ffit;
  out.tQ=p=>tMd*Math.pow(p/(1-p),1/betaT);   // closed-form quantile, for display
  out.t90=Ffit(90); out.t180=Ffit(180); out.t365=Ffit(365);"""

EQ_T_OLD = """  eq("eq_t",`S(t)=e^{-(t/\\\\lambda_{\\\\text{band}})^{k}},\\\\qquad F(t)=1-S(t),\\\\qquad
    F(t_{\\\\text{med}})=\\\\tfrac12\\\\;\\\\text{by construction}`);"""
EQ_T_NEW = """  eq("eq_t",`F(t)=\\\\frac{1}{1+(t/t_{\\\\text{med}})^{-\\\\beta_{\\\\text{band}}}},\\\\qquad S(t)=1-F(t),\\\\qquad
    F(t_{\\\\text{med}})=\\\\tfrac12\\\\;\\\\text{by construction}`);"""
EQ_TS_NEW = """  eq("eq_ts",`\\\\beta=${r.betaT.toFixed(2)},\\\\quad t_{\\\\text{med}}=${tn(r.tMed)}\\\\text{ d},\\\\quad
    t_{25\\\\%}=${tn(r.tQ(.25))}\\\\text{ d},\\\\quad t_{75\\\\%}=${tn(r.tQ(.75))}\\\\text{ d}`);"""
EQ_TS_NEW_OVERPRICING = """  eq("eq_ts",`t_{\\\\text{med}}=t_{\\\\text{band}}\\\\,e^{${T_ELAST}\\\\,h}=${tn(r.ft.days)}\\\\times${r.tMult.toFixed(3)}=${tn(r.tMed)}\\\\text{ d},\\\\qquad
    \\\\beta=${r.betaT.toFixed(2)},\\\\quad t_{25\\\\%}=${tn(r.tQ(.25))}\\\\text{ d},\\\\quad t_{75\\\\%}=${tn(r.tQ(.75))}\\\\text{ d}`);"""

LEDE_OLD = """        <p class="lede"><b>The reported median is a published size-band lookup</b> — no source
          publishes deal-level durations, so there is no hazard model to fit. The Weibull below is drawn
          only to give the curve a shape; its scale is re-solved so the median lands exactly on the
          published band median, and its tails carry no evidence.</p>"""
LEDE_NEW = ("""        <p class="lede"><b>The median is a published size-band lookup; the spread is fitted.</b> The curve
          is a log-logistic whose shape comes from IBBA&rsquo;s per-band histograms of months to close
          (%s closed deals over %s), with its median pinned to the band median. It describes deals that
          closed and says nothing about a listing that never does. Its shape depends on deal size, never on
          the ask: deals under $500K are more spread out than larger ones.%s</p>"""
            % (NT, QLAB2, (' Because the published $500K&ndash;$1M median is shorter than the recent histograms show,\n'
                           '          the curve&rsquo;s long end can rise slightly with size %s.' % RISE_TXT) if RISE540 else ''))

NOTE_OLD = """    <p class="note"><b>This is a lookup, not a hazard model.</b> No source anywhere publishes
    deal-level durations, so there is nothing to fit a survival curve to. The console draws a smooth
    Weibull only so the curve has a shape &mdash; its scale is re-solved so the median lands exactly on
    the published band median above. Read the median; treat the curve's tails as decoration.</p>"""
NOTE_NEW = ("""    <p class="note"><b>The median is a lookup; the curve&rsquo;s shape is fitted.</b> IBBA&rsquo;s Market Pulse
    full reports chart how many months each closed deal took, by size band: %s, %s closed deals.
    Fitted to those histograms and scored on held-out quarters, a log-logistic fits as well as a gamma, at least
    as well as a refitted Weibull%s, and better than a lognormal. It predicts held-out quarters better than the Weibull
    curve drawn before (%+.2f nats per deal, better in %d of %d quarters). The gamma was set aside only because it has no
    closed form in the browser. The shape differs between deals under $500K (&beta; %.2f, more spread out) and deals
    above it (&beta; %.2f). The four bands from $500K to $50M differ by no more than noise (homogeneity p = %s) and
    one shared value predicts held-out quarters as well as four, so they share one &beta;: no gradient within
    $500K&ndash;$50M is identified. &beta; is interpolated in ln(value) between the $250k
    and $707k band centres, as the medians are. The &plusmn; is the standard error from resampling quarters, widened
    because brokers may round or truncate months and because &ldquo;under one month&rdquo; is ambiguous. The
    under-$500K shape is the least certain: its improvement over the old curve depends on how &ldquo;under one
    month&rdquo; is read. Months are counted from engagement or listing, so for larger deals part of the steeper shape
    may be preparation time. The median stays on the band figure (IBBA, 2018&ndash;23). The histogram medians beside
    it come from the 15 quarters above and run about %s months longer in the %s bands.%s For $2&ndash;5M deals the
    curve overstates the share closed by day 180 by about %.0f pts (%.0f before) and by day 365 by about %.0f (%.0f
    before). Everything here describes deals that closed, sampled by the quarter they closed in; the most recent
    quarters run slightly steeper.</p>"""
            % (QLAB, NT, TIE_TXT, PROP['gain_per_deal'], PROP['quarters_better'], PROP['quarters'], REC['shape'][0], B_UP, P_HOM,
               SHORT_RNG, SHORT_TXT,
               (' Because the published $500K&ndash;$1M median is shorter than its histogram median, the curve&rsquo;s long end rises\n'
                '    slightly with size %s (up to %.1f pts at 540 days).' % (RISE_TXT, RISE540)) if RISE540 else '',
               CAL['2M-5M'][180]['err_pts'], CAL_NOW['2M-5M'][180]['err_pts'], OVER365, CAL_NOW['2M-5M'][365]['err_pts']))

EDITS_COMMON = [
    ('table', 'const VBANDS=[["<500K",0,5e5]', TABLE + 'const VBANDS=[["<500K",0,5e5]'),
    ('model III header comment',
     """/* ---- Model III: time to close (AGGREGATE, IBBA Market Pulse) ----
   Size-band medians. NOT a hazard model - no deal-level durations exist. */""",
     """/* ---- Model III: time to close (AGGREGATE, IBBA Market Pulse) ----
   Size-band medians (a lookup) and a curve shape fitted by size band to IBBA's grouped
   histograms (MODELS.fitted.ttc_shape). No deal-level durations exist, so nothing here
   has covariates beyond deal size. */"""),
    ('fitTiming beta',
     """  return {months:months,
          loi:bandInterp(price,col(T.median_months_loi_to_close_recent)),""",
     """  return {months:months,
          beta:bandInterp(price,MODELS.fitted.ttc_shape.beta),
          loi:bandInterp(price,col(T.median_months_loi_to_close_recent)),"""),
    ('constants comment',
     """const LAM0=250, KW=1.42, PHI=.38;
const LAM_FLOOR=118;   // no marketed process realistically clears ~90 days
const PMIN=.05, PMAX=.93;  // irreducible deal risk at both ends   // Weibull scale/shape, seller share of synergy""",
     """/* LAM0 and KW are the scale and shape of the judgment hazard (out.lamEjudg), which is not drawn; the drawn
   curve's shape is fitted (MODELS.fitted.ttc_shape). PHI is the seller's share of synergy. */
const LAM0=250, KW=1.42, PHI=.38;
const LAM_FLOOR=118;   // no marketed process realistically clears ~90 days
const PMIN=.05, PMAX=.93;  // irreducible deal risk at both ends"""),
    ('override comment',
     """  /* ---- AGGREGATE OVERRIDE (Model III) ----------------------------
     Pepperdine gives median months to close by deal-size band. No deal-level
     durations exist anywhere, so there is no hazard model to fit. The Weibull
     is retained ONLY to draw a smooth curve; its scale is re-solved so the
     median lands exactly on the published band median.                    */""",
     """  /* ---- AGGREGATE OVERRIDE (Model III) ----------------------------
     The median is the IBBA band median, interpolated in ln(value). The shape
     is fitted: a log-logistic whose spread beta comes from IBBA's per-band
     histograms of months to close (MODELS.fitted.ttc_shape). The odds of
     having closed by day t are (t/t_med)^beta, so F(t_med)=1/2 exactly with no
     scale to solve. The curve is pinned to the final out.tMed; beta is keyed
     on Vbase like the band, never on the ask. Conditional on closing.       */"""),
    ('section 9: Weibull curve lines',
     """  const Ffit=t=>1-Math.exp(-Math.pow(t/lamFit,KW));
  out.etaT=etaT; out.lamEjudg=lamE; out.lamE=lamFit; out.F=Ffit;""",
     """  out.etaT=etaT; out.lamEjudg=lamE;"""),
    ('section 9: curve after out.tMed', """  out.t90=Ffit(90); out.t180=Ffit(180); out.t365=Ffit(365);""", CODE_CURVE),
    ('lede', LEDE_OLD, LEDE_NEW),
    ('eq label', """<div class="lbl">Scale re-solved to the published band median</div>""",
     """<div class="lbl">Median pinned to the band median; shape fitted by size band</div>"""),
    ('eq_t', EQ_T_OLD, EQ_T_NEW),
    ('data tab table',
     """      <thead><tr><th>Deal size</th><th class="n">Listing &rarr; close</th><th class="n">LOI &rarr; close</th><th class="n">Price / ask</th></tr></thead><tbody>
      ${C.time_to_close.bands.map(b=>`<tr><td>${b}</td>
        <td class="n">${C.time_to_close.median_months_listing_to_close_recent[b]} mo</td>
        <td class="n">${C.time_to_close.median_months_loi_to_close_recent[b]} mo</td>
        <td class="n">${(C.time_to_close.price_pct_of_asking[b]*100).toFixed(0)}%</td></tr>`).join('')}""",
     """      <thead><tr><th>Deal size</th><th class="n">Listing &rarr; close</th><th class="n">LOI &rarr; close</th><th class="n">Curve shape &beta;</th><th class="n">Histogram medians, listing / LOI</th><th class="n">Price / ask</th></tr></thead><tbody>
      ${C.time_to_close.bands.map((b,i)=>{ const S=MODELS.fitted.ttc_shape; return `<tr><td>${b}</td>
        <td class="n">${C.time_to_close.median_months_listing_to_close_recent[b]} mo</td>
        <td class="n">${C.time_to_close.median_months_loi_to_close_recent[b]} mo</td>
        <td class="n">${S.beta[i].toFixed(2)} &plusmn; ${S.beta_se[i].toFixed(2)}</td>
        <td class="n">${S.hist_median_listing[i].toFixed(1)} / ${S.hist_median_loi[i].toFixed(1)} mo</td>
        <td class="n">${(C.time_to_close.price_pct_of_asking[b]*100).toFixed(0)}%</td></tr>`; }).join('')}"""),
    ('data tab note', NOTE_OLD, NOTE_NEW),
    ('ledger row',
     """      <tr><td>Shape of the time-to-close curve (Weibull k = ${KW}); any effect of the ask on time</td>""",
     """      <tr><td>Effect of business quality on time to close, and the Main-Street size of any effect of the ask
          (the curve&rsquo;s shape by size band is now fitted)</td>"""),
    ('sources item',
     """<b>Size-band lookup, not a hazard model</b> &mdash; no deal-level durations exist in any source we hold.
The curve is drawn by re-solving a Weibull so its median lands on the published band median;
the <b>shape parameter is still judgment</b>, and Stanford&rsquo;s search-fund distribution suggests it
should be steeper than the 1.42 used here.</li>""",
     ("""Median is a size-band lookup; the curve shape is <b>fitted</b> from IBBA&rsquo;s per-band histograms
of months to close (%s; %s closed deals; no deal-level durations): a log-logistic with
&beta; %.2f under $500K and %.2f from $500K up (no gradient above $500K is identified).</li>""" % (QLAB2, NT, REC['shape'][0], B_UP))),
    ('bounds row', """<td style="color:#ff8e7a;padding-left:6px">Price anchoring, competitive premium, curve shape.</td>""",
     """<td style="color:#ff8e7a;padding-left:6px">Price anchoring, competitive premium (LAM0 and KW feed only the undisplayed judgment hazard).</td>"""),
]
RE_LAMFIT = re.compile(r'\n  const lamFit=(?:FT\.days|tMedA)/Math\.pow\(Math\.log\(2\),1/KW\);')
RE_EQTS = re.compile(r'  eq\("eq_ts",`[^\n]*`\);')


def build_patch(src):
    """apply the change to the repo page OR to a page that already carries the overpricing_time patch"""
    after_overpricing = 'out.tMult=timeMult(s.ask,out.V);' in src
    out = src
    log = []
    for name, old, new in EDITS_COMMON:
        c = out.count(old)
        assert c == 1, ('anchor count %d' % c, name)
        out = out.replace(old, new); log.append(name)
    assert len(RE_LAMFIT.findall(out)) == 1
    out = RE_LAMFIT.sub('', out); log.append('section 9: remove lamFit')
    assert len(RE_EQTS.findall(out)) == 1
    eqts = EQ_TS_NEW_OVERPRICING if after_overpricing else EQ_TS_NEW
    out = RE_EQTS.sub(lambda m: eqts, out); log.append('eq_ts (%s)' % ('with overpricing' if after_overpricing else 'repo'))
    assert 'lamFit' not in out and 'Weibull scale/shape' not in out and 'NOT a hazard model' not in out
    return out, log, after_overpricing


def udiff(a, b, na, nb):
    return ''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), na, nb, n=2))


PATCH = {}
patched, log, _ = build_patch(html)
pdir = os.path.join(OUT, 'patched'); os.makedirs(os.path.join(pdir, 'tests'), exist_ok=True)
open(os.path.join(pdir, 'index.html'), 'w', encoding='utf-8').write(patched)
for f in ['load.js', 'model.test.js', 'fuzz.test.js']:
    shutil.copyfile(os.path.join(REPO, 'tests', f), os.path.join(pdir, 'tests', f))
open(os.path.join(OUT, 'index.html.diff'), 'w', encoding='utf-8').write(udiff(html, patched, 'a/index.html', 'b/index.html'))
PATCH['repo'] = dict(edits=log, n_edits=len(log))
OV_BASE = os.path.join(OUT, 'overpricing_base', 'index.html')
cdir = os.path.join(OUT, 'patched_after_overpricing')
for d_ in (cdir, os.path.dirname(OV_BASE)):           # never check a composed page left over from an earlier run
    shutil.rmtree(d_, ignore_errors=True)
if os.path.exists(os.path.join(OUT, 'index_after_overpricing.html.diff')):
    os.remove(os.path.join(OUT, 'index_after_overpricing.html.diff'))
comp = None
if os.path.exists(os.path.join(OVERPRICING_DIR, 'index.html')):
    # snapshot the other fit's page and tests ONCE (that fit may be revised while this runs); everything
    # below (composition, baseline for the checks, its tests) uses the snapshot
    ov = open(os.path.join(OVERPRICING_DIR, 'index.html'), encoding='utf-8').read()
    ov_tests = {f: open(os.path.join(OVERPRICING_DIR, 'tests', f), 'rb').read() for f in sorted(os.listdir(os.path.join(OVERPRICING_DIR, 'tests')))}
    os.makedirs(os.path.dirname(OV_BASE), exist_ok=True)
    open(OV_BASE, 'w', encoding='utf-8').write(ov)
    try:
        comp, logc, flag = build_patch(ov)
        assert flag
    except AssertionError as e:                        # that page is mid-revision: record it, do not compose
        comp = None
        PATCH['after_overpricing'] = dict(error='composition failed: %r' % (e.args,),
                                          base_sha1=__import__('hashlib').sha1(ov.encode('utf-8')).hexdigest())
if os.path.exists(OV_BASE) and comp is not None:
    os.makedirs(os.path.join(cdir, 'tests'), exist_ok=True)
    open(os.path.join(cdir, 'index.html'), 'w', encoding='utf-8').write(comp)
    for f, b_ in ov_tests.items():                     # the tests as snapshotted with the page
        open(os.path.join(cdir, 'tests', f), 'wb').write(b_)
    open(os.path.join(OUT, 'index_after_overpricing.html.diff'), 'w', encoding='utf-8').write(
        udiff(ov, comp, 'a/index.html (overpricing_time applied)', 'b/index.html'))
    PATCH['after_overpricing'] = dict(edits=logc, n_edits=len(logc), base_snapshot=OV_BASE,
                                      base_T_ELAST=float(re.search(r'const T_ELAST=([0-9.]+)', ov).group(1)),
                                      base_sha1=__import__('hashlib').sha1(ov.encode('utf-8')).hexdigest())

# reference values for the node checks
KNOWN = {}
for d in (90, 180, 365):
    for i, band in enumerate(BANDS):
        e = abs(CAL[band][d]['err_pts'])
        if e > 4.0:
            KNOWN.setdefault(str(d), {})[JS_BANDS[i]] = float(np.ceil(e) + 1)
STRICT = [d for d in (90, 180, 365, 540) if SO[d]['steps_rising'] == 0]
assert 90 in STRICT and 180 in STRICT, SO          # the drawn curve must stay ordered by size at 90 and 180 days
# tolerated rise of F with size (pts): measured + 0.05, rounded up to 0.1; capped at 0.1 (365 d) and 1.7 (540 d)
SO_CAP = {365: 0.1, 540: 1.7}
SO_TOL = {d: float(np.ceil((SO[d]['max_rise_pts'] + 0.05) * 10) / 10) for d in (365, 540) if d not in STRICT}
assert all(SO_TOL[d] <= SO_CAP[d] + 1e-12 for d in SO_TOL), (SO_TOL, SO)
REF = dict(beta=REC['shape'], centres=CENTRES, edges=[5e5, 1e6, 2e6, 5e6],
           hist_F={str(d): [100 * PRACT[b]['emp_F_at_days'][d] for b in BANDS] for d in (90, 180, 365)},
           calib_tol_pts={'90': 4.0, '180': 4.0, '365': 4.0}, calib_known_exception=KNOWN,
           size_order_strict_days=STRICT, size_order_known_exception_days={str(d): v for d, v in SO_TOL.items()})
json.dump(REF, open(os.path.join(OUT, 'check_ref.json'), 'w'), indent=1)

CHECK_JS = r'''/* Invariant checks for the time-to-close shape change.  node check_invariants.js <patched.html> <baseline.html> <check_ref.json>
   baseline = the same page without this change (repo page, or the overpricing_time page). */
const fs=require("fs"),vm=require("vm"),os=require("os"),path=require("path");
function load(p){
  const html=fs.readFileSync(p,"utf8");
  let src=html.slice(html.lastIndexOf("<script>")+8);
  src=src.slice(0,src.indexOf("/* ============ bar helpers"));
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN};
  vm.createContext(ctx);
  vm.runInContext(src+";this.API={model,fitTiming,bestRatio,optimize,interventionTable,sensitivity,MODELS,IND,sizeRefs,typMargin,bandInterp};",ctx);
  return {A:ctx.API,html,ctx};
}
const [P,B,R]=process.argv.slice(2);
const {A,html,ctx:CTX}=load(P), A0=load(B).A, REF=JSON.parse(fs.readFileSync(R,"utf8"));
let pass=0,fail=0; const fails=[];
const ok=(c,m)=>{ if(c) pass++; else { fail++; if(fails.length<30) fails.push(m);} };
const S=A.MODELS.fitted.ttc_shape, T=A.MODELS.close_and_timing.time_to_close;
/* table */
ok(JSON.stringify(S.bands)===JSON.stringify(T.bands),"ttc_shape.bands equal time_to_close.bands");
for(const k of ["beta","beta_se","n","hist_median_listing","hist_median_listing_se","hist_median_loi","hist_median_loi_se"]) ok(S[k].length===5,`${k} has 5 entries`);
ok(S.beta.every(b=>b>1)&&S.beta_se.every(s=>s>0),"beta>1, beta_se>0");
ok(JSON.stringify(S.beta)===JSON.stringify(REF.beta),"beta equals the fitted table");
ok(S.beta.every((b,i)=>i===0||b>=S.beta[i-1]),"beta non-decreasing across bands");
/* shape keyed on value only, interpolated, flat beyond the end centres, continuous at the band edges */
const bmin=Math.min(...S.beta), bmax=Math.max(...S.beta);
REF.centres.forEach((c,i)=>ok(Math.abs(A.fitTiming(c,"medical").beta-S.beta[i])<1e-12,`beta at centre ${c}`));
for(const p of [1,1e3,1e5,2.5e5]) ok(A.fitTiming(p,"medical").beta===S.beta[0],`flat below $250k (${p})`);
for(const p of [1.5812e7,3e7,1e9]) ok(Math.abs(A.fitTiming(p,"medical").beta-S.beta[4])<1e-9,`flat above $15.8M (${p})`);
for(const e of REF.edges) ok(Math.abs(A.fitTiming(e*(1+1e-9),"medical").beta-A.fitTiming(e*(1-1e-9),"medical").beta)<1e-3,`beta continuous at ${e}`);
for(const ind of Object.keys(A.IND)) ok(A.fitTiming(1.3e6,ind).beta===A.fitTiming(1.3e6,"medical").beta,`beta independent of industry ${ind}`);
ok(A.fitTiming(3.1623e6,"medical").beta>A.fitTiming(2.5e5,"medical").beta,"steeper with size: beta($3.16M) > beta($250k)");
{ let pb=-Infinity, mono=true; for(let i=0;i<=600;i++){ const b=A.fitTiming(Math.exp(Math.log(1e4)+(Math.log(1e9)-Math.log(1e4))*i/600),"medical").beta; if(b<pb-1e-12) mono=false; pb=b; }
  ok(mono,"beta non-decreasing in value ($10k-$1B)"); }
/* size order of the curve at fair price (fitTiming level = what model() draws when ask <= value) */
const Fat=(p,t)=>{ const ft=A.fitTiming(p,"medical"); return 1/(1+Math.pow(t/ft.days,-ft.beta)); };
const grid=[]; for(let i=0;i<=6000;i++) grid.push(Math.exp(Math.log(1e5)+(Math.log(3e7)-Math.log(1e5))*i/6000));
const sizeOrder={};
for(const t of [90,180,365,540]){
  let rises=0, runMin=Infinity, maxRise=0, prev=null;
  for(const p of grid){ const f=Fat(p,t); if(prev!==null&&f>prev+1e-12) rises++; runMin=Math.min(runMin,f); maxRise=Math.max(maxRise,f-runMin); prev=f; }
  sizeOrder[t]={rises,maxRisePts:100*maxRise};
  if(REF.size_order_strict_days.includes(t)) ok(rises===0,`F(${t}d) non-increasing in value (rises ${rises})`);
  else ok(100*maxRise<=REF.size_order_known_exception_days[String(t)],`tolerance: F(${t}d) rises at most ${REF.size_order_known_exception_days[String(t)]} pts with value (${(100*maxRise).toFixed(2)})`);
}
/* calibration guard at the band centres (2020-25 histograms) */
const calib={};
REF.centres.forEach((c,i)=>{ for(const d of ["90","180","365"]){
  const f=100*Fat(c,+d), h=REF.hist_F[d][i], band=S.bands[i];
  const ex=(REF.calib_known_exception[d]||{})[band], tol=ex!==undefined?ex:REF.calib_tol_pts[d];
  calib[band+"@"+d]=+(f-h).toFixed(2);
  ok(Math.abs(f-h)<=tol,`F(${d}d) at ${band} centre within ${tol} pts of the histogram: ${f.toFixed(1)} vs ${h.toFixed(1)}`); } });
/* per-business sweep */
const median=(ind,ern)=>{ const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/A.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40}; };
const STRIP=new Set(["t90","t180","t365","lamE","betaT"]);
const ser=o=>JSON.stringify(o,function(k,v){ if(typeof v==="function") return undefined; if(STRIP.has(k)) return undefined;
  if(k==="beta"&&this&&this.months!==undefined&&this.loi!==undefined) return undefined; return v; });
let nCase=0, composed=false;
const budget=10**(4+2.778*.36);
for(const ind of Object.keys(A.IND)) for(const ern of [6e4,1.5e5,3e5,6e5,1e6,1.45e6,2.5e6,5e6,1.2e7]) for(const rho of [.8,1,1.3,1.7]){
  const s0=median(ind,ern); const V0=A.model({...s0,ask:ern*3}).V; const s={...s0,ask:rho*V0};
  const r=A.model(s), r0=A0.model(s); nCase++; if(r.tMult!==undefined) composed=true;
  const tag=`${ind} ern ${ern} rho ${rho}`;
  ok(Math.abs(r.F(r.tMed)-.5)<1e-12,`median exact ${tag}`);
  ok(Math.abs(r.tQ(.5)/r.tMed-1)<1e-9,`tQ(.5)=tMed ${tag}`);
  ok(r.tMed===r0.tMed,`tMed unchanged ${tag}`);
  ok(r.F(0)===0,`F(0)=0 ${tag}`);
  let prev=-1, okm=true; for(let t=0;t<=3000;t++){ const f=r.F(t); if(!(f>=prev&&f>=0&&f<=1&&isFinite(f))) okm=false; prev=f; }
  ok(okm,`F proper CDF on 0..3000 ${tag}`);
  ok(r.F(20*r.tMed)>.99,`F(20 tMed)>.99 ${tag}`);
  ok(r.betaT>=bmin-1e-12&&r.betaT<=bmax+1e-12,`beta in range ${tag}`);
  for(const p of [.1,.25,.75,.9]) ok(Math.abs(r.F(r.tQ(p))-p)<1e-9,`quantile inverts F at ${p} ${tag}`);
  const ra=A.model({...s,ask:s.ask*1.7}); ok(ra.betaT===r.betaT,`beta independent of the ask ${tag}`);
  ok(Math.abs(ra.F(ra.tMed)-.5)<1e-12,`median exact after an ask change ${tag}`);
  if(r.tMult===undefined){ for(const t of [30,90,180,365,540]) ok(ra.F(t)===r.F(t),`F independent of the ask without overpricing_time ${tag}`); }
  const rq=A.model({...s,own:.2,mgt:.9,fin:.2}); ok(rq.betaT===r.betaT,`beta independent of quality ${tag}`);
  if(r.tMult===undefined) for(const t of [30,90,180,365]) ok(rq.F(t)===r.F(t),`F independent of quality ${tag}`);
  ok(ser(r)===ser(r0),`model() identical apart from the curve ${tag}`);
  if(nCase%6===0){ ok(ser(A.optimize(s,r,budget,900,.75))===ser(A0.optimize(s,r0,budget,900,.75)),`optimize identical ${tag}`);
    ok(A.bestRatio(s,.75,900)===A0.bestRatio(s,.75,900)&&A.bestRatio(s,0,0)===A0.bestRatio(s,0,0),`bestRatio identical ${tag}`);
    ok(ser(A.interventionTable(s,r))===ser(A0.interventionTable(s,r0)),`interventionTable identical ${tag}`); }
}
/* KaTeX: render the two new equation strings with the page's own KaTeX build */
let katexOK=null;
try{
  const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
  const kt=scripts.find(x=>x.includes("renderToString")&&x.includes("KaTeX"));
  const tmp=path.join(os.tmpdir(),"ttc_katex_"+process.pid+".js"); fs.writeFileSync(tmp,kt);
  const katex=require(tmp); fs.unlinkSync(tmp);
  const m=html.match(/  eq\("eq_t",`([\s\S]*?)`\);\n  eq\("eq_ts",`([\s\S]*?)`\);/);
  const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
  const r=A.model(ex), tn=x=>Math.round(x).toString();
  const ev=s=>vm.runInContext("(r,tn)=>`"+s+"`",CTX)(r,tn);   // in the page's own scope (KW, T_ELAST, ...)
  for(const s of [m[1],m[2]]) katex.renderToString(ev(s),{throwOnError:true,displayMode:true});
  katexOK=true; ok(true,"KaTeX renders eq_t and eq_ts");
}catch(e){ katexOK=String(e).slice(0,200); ok(false,"KaTeX: "+katexOK); }
const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
const r=A.model(ex), r0=A0.model(ex);
const example={Vbase:r.Vbase,beta:r.betaT,tMed:r.tMed,t25:r.tQ(.25),t75:r.tQ(.75),F90:[r0.t90,r.t90],F180:[r0.t180,r.t180],F365:[r0.t365,r.t365]};
console.log(JSON.stringify({pass,fail,fails,nCase,composed,sizeOrder,calib,katexOK,example}));
'''
open(os.path.join(OUT, 'check_invariants.js'), 'w').write(CHECK_JS)

JS = {}
if RUN_JS and shutil.which('node'):
    def run(cmd, cwd=None):
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=1800)
        return p.returncode, (p.stdout.strip().splitlines() or [''])[-1], p.stderr.strip()[-500:]
    # syntax check of the patched main script, invariant checks, and the repo's test files on each patched copy
    for nm, d, base in [('repo', os.path.join(OUT, 'patched'), INDEX),
                        ('after_overpricing', os.path.join(OUT, 'patched_after_overpricing'), OV_BASE)]:
        if not os.path.exists(os.path.join(d, 'index.html')):
            continue
        page = open(os.path.join(d, 'index.html'), encoding='utf-8').read()
        st = page.rfind('<script>') + 8
        main_js = page[st: page.find('</script>', st)]
        jsf = os.path.join(d, 'main_script.js'); open(jsf, 'w', encoding='utf-8').write(main_js)
        rc, last, err = run(['node', '--check', jsf])
        JS[nm] = dict(node_check=('ok' if rc == 0 else err))
        rc, last, err = run(['node', os.path.join(OUT, 'check_invariants.js'), os.path.join(d, 'index.html'), base, os.path.join(OUT, 'check_ref.json')])
        try:
            JS[nm]['invariants'] = json.loads(last)
        except Exception:
            JS[nm]['invariants'] = dict(error=err or last)
        for tf in sorted(os.listdir(os.path.join(d, 'tests'))):
            if tf.endswith('.test.js'):
                rc, last, err = run(['node', os.path.join(d, 'tests', tf)])
                JS[nm][tf] = last if rc == 0 else ('rc=%d %s %s' % (rc, last, err))
        print('[8] node checks %s done %.0fs: %s' % (nm, time.time() - T0, json.dumps({k: (v if k != 'invariants' else {kk: v.get(kk) for kk in ('pass', 'fail', 'fails')}) for k, v in JS[nm].items()})[:900]))
    json.dump(JS, open(os.path.join(OUT, 'js_checks.json'), 'w'), indent=1)

results.update(dict(band_table=band_tab.to_dict(orient='records'), sensitivity=sens.to_dict(orient='records'),
                    eb=EB, eb_toward_mean=EB_MEAN, trend=TREND, structure=STRUCT, structure_selection=SELECT, boot_cov=BOOT_COV, cv=CV, stability=STAB, frailty=FRAIL,
                    heaping=HEAPING, pinned_profile=PINNED_PROFILE, practical=PRACT, size_order=SIZE_ORDER, calibration=CALIB,
                    hist_share_by_day=HIST_ORDER, medians=MEDIANS, cross=CROSS, recommended=REC, judgment_prior=JUDG,
                    gengamma_Q_boot_se={b: float(v.std(ddof=1)) for b, v in ggQ.items()}, patch=PATCH, js_checks=JS))


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


json.dump(clean(results), open(os.path.join(OUT, 'fits.json'), 'w'), indent=1)

# ---------------------------------------------------------------- printed summary
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 60)
print('\nconsole KW=%.2f; console medians %s' % (KW_NOW, MED_NOW))
print('parse fixes', json.dumps(PARSE_FIXES))
cols = ['measure', 'band', 'n_deals', 'weibull_k', 'weibull_k_se_boot', 'weibull_k_eb', 'loglogistic_beta', 'loglogistic_beta_se_hess',
        'loglogistic_beta_se_boot', 'loglogistic_beta_eb', 'loglogistic_beta_eb_mean', 'loglogistic_beta_eb_se', 'loglogistic_beta_conv_half_gap',
        'loglogistic_beta_lt1_half_range', 'loglogistic_beta_se_total', 'gamma_a', 'lognormal_sigma', 'gengamma_Q', 'gengamma_Q_se_boot',
        'grouped_median', 'grouped_median_se_boot', 'console_median', 'daic_weibull', 'daic_gamma', 'daic_lognormal', 'daic_loglogistic', 'best_aic']
print(band_tab[cols].round(3).to_string())
print('\nsensitivity (listing, log-logistic beta raw):')
print(sens.pivot(index='spec', columns='band', values='loglogistic_beta')[BANDS].round(3).to_string())
print(sens.pivot(index='spec', columns='band', values='shift_in_total_se')[BANDS].round(2).to_string())
print('\nEB trend:', json.dumps(clean({m: EB[m]['loglogistic_beta'] for m in EB})))
print('EB mean :', json.dumps(clean({m: EB_MEAN[m]['loglogistic_beta']['post'] for m in EB_MEAN})))
print('trend:', json.dumps(clean(TREND)))
print('boot corr:', json.dumps(BOOT_COV))
for m in CV:
    for spec, d in CV[m].items():
        print('\nLOQO %s [%s] n=%.0f' % (m, spec, d['n_heldout']))
        print('  held-out ll/deal:', json.dumps({k: round(v, 4) for k, v in d['loqo_heldout_ll_per_deal'].items()}))
        for k, v in d['loqo_pairs'].items():
            print('  %-75s %+.4f +/- %.4f  (%d/%d) p(t%d)=%.3f  by band %s' % (k, v['gain_per_deal'], v['se'], v['quarters_better'], v['quarters'],
                                                                   v['df'], v['p_two_sided'], ' '.join('%+.3f' % x for x in v['by_band'].values())))
        print('  temporal (n_test=%.0f):' % d['temporal']['n_test'])
        for k, v in d['temporal']['pairs'].items():
            print('    %-73s %+.4f +/- %.4f (%d/%d) p(t3)=%.3f' % (k, v['gain_per_deal'], v['se'], v['quarters_better'], v['quarters'], v['p_two_sided']))
        print('  block-of-4 CV:')
        for k, v in d['block4']['pairs'].items():
            print('    %-73s %+.4f +/- %.4f (%d/%d) p(t3)=%.3f' % (k, v['gain_per_deal'], v['se'], v['quarters_better'], v['quarters'], v['p_two_sided']))
print('\nper-quarter gain, proposed vs today:', json.dumps({q: round(v, 4) for q, v in CV[LISTING]['central']['loqo_pairs']['pinned_loglogistic_per_band__vs__pinned_weibull_console_k']['per_quarter_gain_per_deal'].items()}))
print('\nstructure', json.dumps(clean({k: v for k, v in STRUCT.items() if k != 'two_level_by_spec'})))
print('two-level by spec', json.dumps(clean({k: {kk: vv for kk, vv in v.items() if not kk.startswith('x_')} for k, v in TWO.items()})))
print('selection', json.dumps(clean(SELECT)))
print('\nstability', json.dumps(clean(STAB)))
print('\nfrailty', json.dumps({b: {k: v for k, v in d.items() if k != 'quarter_grouped_median'} for b, d in clean(FRAIL).items()}))
print('\nheaping', json.dumps(clean(HEAPING)))
print('\npinned profile', json.dumps(PINNED_PROFILE))
print('\npractical')
for b, d in PRACT.items():
    print(b, json.dumps(clean({k: v for k, v in d.items() if k != 'emp_cdf_at_edges'})))
print('\nsize order', json.dumps(clean(SIZE_ORDER)))
print('\ncalibration', json.dumps(clean(CALIB)))
print('\nhist share by day', json.dumps(clean(HIST_ORDER)))
print('\nmedians', json.dumps(clean(MEDIANS)))
print('\ncross', json.dumps(clean(CROSS), indent=0)[:5000])
print('\njudgment prior', json.dumps(clean(JUDG)))
print('\nREC', json.dumps(clean(REC)))
print('\npatch', json.dumps(PATCH))
print('done %.0fs' % (time.time() - T0))
