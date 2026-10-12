#!/usr/bin/env python3
"""Band medians of the time to close (Model III), refitted to the IBBA histograms. October 2026.

Run:  python3 -I /home/user/last-minute/fit/time_to_close_medians.py          (about 1 min)
Out:  /tmp/claude-0/fit5/time_to_close_medians/RESULT.json

Why
  The console draws a log-logistic whose SHAPE (beta 2.20 under $500K, 2.64 from $500K up) was fitted to
  IBBA / M&A Source Market Pulse per-band histograms of months to close (fit/time_to_close_shape.py), but
  pinned to MEDIANS from IBBA's published 2018-23 band medians (6.5 / 7.25 / 8 / 8 / 10.5 months). The two
  disagree: the 2020-25 histograms put the $500K-1M and $2-5M medians 0.8 and 1.3 months higher, which made
  the drawn curve's long end rise with size between $250k and $707k (AUDIT.md, open follow-up). This script
  fits the medians to the same histograms the shape came from, with the shape held at the shipped values,
  and checks out of sample that the refitted medians predict held-out quarters better than the published
  ones before anything is shipped.

What it does
  0. Data: the same tidy table and the same parse fix as fit/time_to_close_shape.py (three <500K charts carry
     the '1.1-1.5 years' bar under a wrong label; recoded by chart position). Central interval convention:
     integer answers are rounded months, k -> [k-0.5, k+0.5); '<1 month' and '1 month' merged into [0, 1.5).
  1. Per band and measure (listing -> close, LOI -> close), the maximum-likelihood median of an interval-
     censored log-logistic with beta fixed at the shipped two-level values. Grouped medians beside it.
  2. Standard errors: cluster bootstrap over QUARTERS (B = 1000), resampled jointly across bands (sampling SE).
     The reporting convention is not identified: read as truncated months (k -> [k, k+1), sub-2-month answers
     [0, 2)) every median comes out about 0.55 months longer than under the central rounded reading. As
     time_to_close_shape.py does for beta, half that floor-round gap is added to the sampling SE in quadrature
     (total SE, shipped as listing_se / loi_se); the medians themselves stay on the central reading.
  3. Out of sample: leave-one-quarter-out. Each quarter's medians are refitted on the other 14 quarters, put
     through the shipped pipeline (shrunk toward the line with tau^2 re-estimated in the fold, rounded to 0.01
     month) and the held-out quarter is scored; the comparison is the same curve pinned to the published
     medians. Gain per held-out deal with a quarter-clustered SE and t(14). The raw MLE medians are scored
     too, for reference. Temporal holdout: fit on 2020Q1-2022Q4, score 2023Q1-2023Q3 and 2025Q4. The published
     medians come from editions that overlap the test quarters, which favours them; the refit has to win anyway.
     In a fold the log-scale SEs used for the shrinkage are the full-sample bootstrap SEs scaled by
     sqrt(quarters / training quarters), an approximation (no bootstrap inside each fold).
  4. Shrinkage: the band estimates are shrunk toward a weighted straight line in ln(band centre) (Fay-Herriot,
     DerSimonian-Laird tau^2). The weight on the line is B = v / (v + tau^2); RESULT stores it and its
     complement, the weight on the band's own estimate.
  5. Recommendation: ship the shrunk MLE medians (rounded to 0.01 month) if both out-of-sample comparisons
     favour them; otherwise keep the published medians and say why.
"""
import json, os, re, sys
import numpy as np
import pandas as pd
from scipy import optimize, special, stats

OUT = '/tmp/claude-0/fit5/time_to_close_medians'
os.makedirs(OUT, exist_ok=True)
IBBA = '/tmp/claude-0/data5/aggregates_research/clean/ibba_mp_band_histograms_long.csv'
INDEX = '/home/user/last-minute/index.html'
BANDS = ['<500K', '500K-1M', '1M-2M', '2M-5M', '5M-50M']
JS_BANDS = ['<500K', '500K-1M', '1-2M', '2-5M', '5-50M']
CENTRES = np.array([2.5e5, np.sqrt(5e5 * 1e6), np.sqrt(1e6 * 2e6), np.sqrt(2e6 * 5e6), np.sqrt(5e6 * 5e7)])
MEASURES = {'listing_to_close_months': 'median_months_listing_to_close_recent',
            'loi_to_close_months': 'median_months_loi_to_close_recent'}
B_BOOT = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
rng = np.random.default_rng(20261012)

html = open(INDEX, encoding='utf-8').read()
ttc = json.loads('{' + re.search(r'"time_to_close":(\{.*?\}\})', html).group(0) + '}')['time_to_close']
shape = json.loads(re.search(r'MODELS\.fitted\.ttc_shape=(\{.*?\});', html).group(1))
BETA = np.array(shape['beta'], float)                       # shipped two-level shape: 2.20, 2.64 x 4


def load_ibba():
    h = pd.read_csv(IBBA)
    h = h[h.measure.isin(list(MEASURES))].reset_index(drop=True)
    n_fix = 0
    for (m, p, b), g in h.groupby(['measure', 'period', 'band'], sort=False):
        if not (g.category == '1.1-1.6 yr').any():
            continue
        i16 = list(g.index[g.category == '1.1-1.6 yr']); two = list(g.index[g.category == '2 mo'])
        assert len(i16) == 1 and len(two) == 2 and two[0] < i16[0] < two[1]
        h.loc[i16[0], 'category'] = '1.1-1.5 yr'; h.loc[two[1], 'category'] = '1.6-2 yr'; n_fix += 1
    assert n_fix == 3, n_fix
    return h


def interval(cat, conv='round'):
    off = 0.5 if conv == 'round' else 0.0          # boundaries at k-0.5 (rounded months) or k (truncated months)
    if cat in ('<1 mo', '1 mo'):
        return (0.0, 2 - off)
    m = re.fullmatch(r'(\d+) mo', cat)
    if m:
        k = float(m.group(1)); return (k - off, k + 1 - off)
    return {'1.1-1.5 yr': (13 - off, 19 - off), '1.6-2 yr': (19 - off, 25 - off), '>2 yr': (25 - off, np.inf)}[cat]


H = load_ibba()
H['count'] = H.pct / H.row_sum * H.n_closed
for conv in ('round', 'floor'):
    iv = [interval(c, conv) for c in H.category]
    H['lo_' + conv] = [a for a, b in iv]; H['hi_' + conv] = [b for a, b in iv]


def matrices(measure, band, conv='round'):
    g = H[(H.measure == measure) & (H.band == band)]
    los, his = g['lo_' + conv], g['hi_' + conv]
    ints = sorted(set(zip(los, his))); qs = sorted(g.period.unique())
    C = np.zeros((len(qs), len(ints))); idx = {v: j for j, v in enumerate(ints)}
    for p, lo, hi, c in zip(g.period, los, his, g['count']):
        C[qs.index(p), idx[(lo, hi)]] += c
    return qs, np.array([a for a, b in ints]), np.array([b for a, b in ints]), C


def cdf(beta, med, t):
    with np.errstate(divide='ignore'):
        lt = np.log(np.asarray(t, float))
    return special.expit(beta * (lt - np.log(med)))


def loglik(beta, med, lo, hi, c):
    p = cdf(beta, med, hi) - cdf(beta, med, lo)
    return float(np.sum(c * np.log(np.clip(p, 1e-300, None))))


def mle_median(beta, lo, hi, c):
    r = optimize.minimize_scalar(lambda lm: -loglik(beta, np.exp(lm), lo, hi, c), bounds=(np.log(1), np.log(40)), method='bounded',
                                 options=dict(xatol=1e-9))
    return float(np.exp(r.x))


def grouped_median(lo, hi, c):
    o = np.argsort(lo); lo, hi, c = lo[o], hi[o], c[o]
    cum = np.cumsum(c); half = cum[-1] / 2; j = int(np.searchsorted(cum, half))
    prev = cum[j - 1] if j else 0.0
    return float(lo[j] + (hi[j] - lo[j]) * (half - prev) / c[j])


def eb_line(est, se, x):
    """Fay-Herriot shrinkage toward a weighted line in x; DerSimonian-Laird tau^2"""
    X = np.c_[np.ones_like(x), x]; v = se ** 2
    W = np.diag(1 / v); b = np.linalg.solve(X.T @ W @ X, X.T @ W @ est)
    Q = float(np.sum((est - X @ b) ** 2 / v)); k = len(est); p = 2
    trP = float(np.sum(1 / v) - np.trace(np.linalg.solve(X.T @ W @ X, X.T @ W @ W @ X)))
    tau2 = max(0.0, (Q - (k - p)) / trP)
    W2 = np.diag(1 / (v + tau2)); b2 = np.linalg.solve(X.T @ W2 @ X, X.T @ W2 @ est); fit = X @ b2
    B = v / (v + tau2) if tau2 > 0 else np.ones_like(v)
    post = fit + (1 - B) * (est - fit)
    return post, tau2, Q, B


RES = {'beta_shipped': BETA.tolist(), 'bands': JS_BANDS}
for measure, key in MEASURES.items():
    pub = np.array([ttc[key][b] for b in JS_BANDS], float)
    mats = [matrices(measure, b) for b in BANDS]
    qs = mats[0][0]; assert all(m[0] == qs for m in mats)
    nq = len(qs)
    mle = np.array([mle_median(BETA[i], m[1], m[2], m[3].sum(0)) for i, m in enumerate(mats)])
    grp = np.array([grouped_median(m[1], m[2], m[3].sum(0)) for m in mats])
    n_deals = np.array([m[3].sum() for m in mats])
    # 2. quarter-cluster bootstrap, joint across bands
    boot = np.zeros((B_BOOT, 5))
    for bb in range(B_BOOT):
        w = np.bincount(rng.integers(0, nq, nq), minlength=nq).astype(float)
        boot[bb] = [mle_median(BETA[i], m[1], m[2], (w[:, None] * m[3]).sum(0)) for i, m in enumerate(mats)]
    se = boot.std(0, ddof=1)
    # log-scale SE for the shrinkage
    lse = np.log(boot).std(0, ddof=1)
    # 4. shrinkage toward a line in ln(centre), on the log median
    post_l, tau2, Qstat, Bw = eb_line(np.log(mle), lse, np.log(CENTRES))
    shrunk = np.exp(post_l)
    # 2b. the reporting convention: the same pipeline with months read as truncated; half the gap joins the SE
    mats_f = [matrices(measure, b, 'floor') for b in BANDS]
    mle_f = np.array([mle_median(BETA[i], m[1], m[2], m[3].sum(0)) for i, m in enumerate(mats_f)])
    shrunk_f = np.exp(eb_line(np.log(mle_f), lse, np.log(CENTRES))[0])
    conv_shift = np.round(shrunk_f, 2) - np.round(shrunk, 2)
    se_total = np.sqrt(se ** 2 + (conv_shift / 2) ** 2)

    def pipeline_meds(cmat, scale):
        """the shipped pipeline on a subset of quarters: MLE per band, shrunk toward the line, rounded to 0.01"""
        raw = np.array([mle_median(BETA[i], m[1], m[2], cm) for i, (m, cm) in enumerate(zip(mats, cmat))])
        return raw, np.round(np.exp(eb_line(np.log(raw), lse * scale, np.log(CENTRES))[0]), 2)

    def summarise(gq, nq_, extra=None):
        N = nq_.sum(); g_ = gq.sum() / N; s_ = np.sqrt(len(gq)) * gq.std(ddof=1) / N
        d = dict(gain_per_deal=float(g_), se=float(s_), t=float(g_ / s_), df=len(gq) - 1,
                 p_two_sided=float(2 * stats.t.sf(abs(g_ / s_), len(gq) - 1)), quarters_better=int((gq > 0).sum()), quarters=len(gq))
        if extra: d.update(extra)
        return d
    # 3. leave-one-quarter-out: the shipped pipeline (headline) and the raw MLE (reference)
    gain_q = np.zeros(nq); gain_raw = np.zeros(nq); n_q = np.zeros(nq); gain_qb = np.zeros((nq, 5)); n_qb = np.zeros((nq, 5))
    for qi in range(nq):
        keep = np.arange(nq) != qi
        raw_tr, ship_tr = pipeline_meds([m[3][keep].sum(0) for m in mats], np.sqrt(nq / (nq - 1)))
        for i, m in enumerate(mats):
            te = m[3][qi]; base = loglik(BETA[i], pub[i], m[1], m[2], te)
            g = loglik(BETA[i], ship_tr[i], m[1], m[2], te) - base
            gain_q[qi] += g; gain_raw[qi] += loglik(BETA[i], raw_tr[i], m[1], m[2], te) - base
            n_q[qi] += te.sum(); gain_qb[qi, i] = g; n_qb[qi, i] = te.sum()
    loqo = summarise(gain_q, n_q, dict(scored='shipped pipeline: shrunk in the fold, rounded to 0.01 month',
                                       by_band=dict(zip(JS_BANDS, (gain_qb.sum(0) / n_qb.sum(0)).round(5).tolist())),
                                       raw_mle=summarise(gain_raw, n_q)))
    # temporal holdout, same two scorings
    train = [i for i, q in enumerate(qs) if q <= '2022Q4']; test = [i for i, q in enumerate(qs) if q > '2022Q4']
    raw_tr, ship_tr = pipeline_meds([m[3][train].sum(0) for m in mats], np.sqrt(nq / len(train)))
    tg = np.zeros(len(test)); tgr = np.zeros(len(test)); tn = np.zeros(len(test))
    for i, m in enumerate(mats):
        for j, qi in enumerate(test):
            te = m[3][qi]; base = loglik(BETA[i], pub[i], m[1], m[2], te)
            tg[j] += loglik(BETA[i], ship_tr[i], m[1], m[2], te) - base
            tgr[j] += loglik(BETA[i], raw_tr[i], m[1], m[2], te) - base; tn[j] += te.sum()
    temporal = dict(train=[qs[i] for i in train], test=[qs[i] for i in test], gain_per_deal=float(tg.sum() / tn.sum()),
                    se=float(np.sqrt(len(test)) * tg.std(ddof=1) / tn.sum()), quarters_better=int((tg > 0).sum()),
                    scored='shipped pipeline', raw_mle=dict(gain_per_deal=float(tgr.sum() / tn.sum()), quarters_better=int((tgr > 0).sum())))
    # in-sample fit of the shipped curve against each median set, per deal
    ll = lambda meds: sum(loglik(BETA[i], meds[i], m[1], m[2], m[3].sum(0)) for i, m in enumerate(mats)) / n_deals.sum()
    adopt = loqo['gain_per_deal'] > 0 and temporal['gain_per_deal'] > 0
    # 6. calibration of the drawn curve against the histograms: share closed by day 90 / 180 / 365 (uniform within bins)
    def emp(lo, hi, c, t):
        return float(sum(n if b <= t else (n * (t - a) / (b - a) if a < t else 0.0) for a, b, n in zip(lo, hi, c)) / c.sum())
    calib = {}
    for d in (90, 180, 365):
        t = d / 30.44; rows = []
        for i, m in enumerate(mats):
            c = m[3].sum(0); ev = emp(m[1], m[2], c, t)
            rows.append(dict(band=JS_BANDS[i], empirical=round(100 * ev, 1),
                             published=round(100 * (float(cdf(BETA[i], pub[i], t)) - ev), 1),
                             refit=round(100 * (float(cdf(BETA[i], np.round(shrunk[i], 2), t)) - ev), 1)))
        calib[f'd{d}'] = dict(rows=rows, max_abs_pts_published=max(abs(r['published']) for r in rows),
                              max_abs_pts_refit=max(abs(r['refit']) for r in rows))
    RES[measure] = dict(quarters=qs, n_deals=n_deals.round(0).tolist(), published=pub.tolist(), mle=mle.round(4).tolist(),
                        mle_se_boot=se.round(4).tolist(), grouped=grp.round(4).tolist(),
                        convention=dict(floor_mle=mle_f.round(4).tolist(), floor_shrunk=shrunk_f.round(4).tolist(),
                                        shift_months=conv_shift.round(2).tolist(), se_total=se_total.round(4).tolist(),
                                        note='months read as truncated instead of rounded; half the shift is added to the sampling SE in quadrature'),
                        eb=dict(tau2_log=tau2, Q=Qstat, weight_on_line=Bw.round(4).tolist(), weight_on_own_estimate=(1 - Bw).round(4).tolist(),
                                shrunk=shrunk.round(4).tolist()),
                        loqo=loqo, temporal=temporal,
                        insample_ll_per_deal=dict(published=ll(pub), mle=ll(mle), shrunk=ll(shrunk)), calibration_pts=calib,
                        recommended=(np.round(shrunk, 2).tolist() if adopt else pub.tolist()), adopted=bool(adopt))
    print(measure)
    for i, b in enumerate(JS_BANDS):
        print(f'  {b:8s} published {pub[i]:5.2f}  mle {mle[i]:5.2f} (se {se[i]:.2f})  grouped {grp[i]:5.2f}  shrunk {shrunk[i]:5.2f}  n {n_deals[i]:.0f}')
    print(f'  tau2(log) {tau2:.4g}  weight on line {np.round(Bw, 3).tolist()}  floor-round shift {conv_shift.round(2).tolist()}  total SE {se_total.round(2).tolist()}')
    print(f'  LOQO (shipped) gain/deal {loqo["gain_per_deal"]:+.5f} (se {loqo["se"]:.5f}, t {loqo["t"]:.2f}, {loqo["quarters_better"]}/{nq} quarters);'
          f' raw MLE {loqo["raw_mle"]["gain_per_deal"]:+.5f} ({loqo["raw_mle"]["quarters_better"]}/{nq})')
    print(f'  temporal (shipped) {temporal["gain_per_deal"]:+.5f} (se {temporal["se"]:.5f}, {temporal["quarters_better"]}/{len(test)});'
          f' raw MLE {temporal["raw_mle"]["gain_per_deal"]:+.5f}  adopt {adopt}')

json.dump(RES, open(OUT + '/RESULT.json', 'w'), indent=1)
print('wrote', OUT + '/RESULT.json')
