#!/usr/bin/env python3
"""oews_refresh.py - refresh MODELS.fitted.gm_wage (general-manager wage percentiles).

What it does
  1. Reads BLS OEWS May 2021/2023/2024/2025 national industry-specific estimates for
     SOC 11-1021 (General and Operations Managers) straight from the raw BLS xlsx files
     (May 2021 from the official oesm21in4/oesm21nat zips, cross-checked cell by cell against
     the cran/oews2021 mirror the app's old table came from), and cross-checks 2023-25
     against the cleaned extract.
  2. Measurement error per cell and percentile from the published MEAN_PRSE, converted to
     a log-percentile SE with a lognormal quantile/mean ratio (k_p).
  3. Empirical Bayes: each cell's log percentile is shrunk toward its nearest published
     parent NAICS row. Because the parent row contains the child, the child-parent gap is
     about (1-w) x the child-vs-rest gap (w = child share of parent GM employment), so the
     prior variance is tau0^2 (1-w)^2; tau0^2 by Paule-Mandel per parent level x percentile,
     5-fold cross-validated by parent against the constant-tau prior.
     Posterior SE = exact MSE of the estimator with the child-in-parent covariance, plus
     tau^2 uncertainty (delta method), checked by Monte Carlo.
  4. Noise beyond BLS's sampling SEs: a variance-component model fitted by Gaussian
     quasi-likelihood to the within-cell changes between six pairs of OEWS vintages, using
     the six-panel/three-year design (shared panels, panel dates): PRSE scale kappa^2,
     transient (panel-level) non-sampling noise, random-walk cell drift and May-2021
     interval-coding noise. Validated leave-one-window-out and 5-fold by sector. Gives the
     total SE of each cell's June-2026 value.
  5. Growth: ECI private wages & salaries for management, business and financial
     occupations (actual through 2026Q2) from the OEWS May 2025 reference to 2026Q2;
     validated against within-cell OEWS growth, with p75/p90 censoring at the old top-codes
     handled by a two-sided Tobit; percentile-specific drift carried over the effective
     2.33-year lag (panels Nov 2022 - May 2025 are aged by a broad-group factor).
  6. Builds the app table for every app industry (saas -> 513200; ecom bridged, labelled),
     evaluates old vs new gmSalary in the model harness, and writes RESULT.json.

Run:  python3 -I /home/user/last-minute/fit/oews_refresh.py [--write-repo]
Out:  /tmp/claude-0/fit5/oews_refresh/   (--write-repo also writes fit/gm_wage.json, the
      file fit/build_models.py reads; without it no repo file is touched)
Needs: pandas numpy scipy openpyxl pyreadr; node (optional, for the harness comparison).
"""
import os, sys, json, math, re, subprocess, hashlib
import numpy as np, pandas as pd
import openpyxl, pyreadr
from scipy import stats, optimize

OUT = '/tmp/claude-0/fit5/oews_refresh'
RAW = '/tmp/claude-0/data5/bls_oews/raw'
CLEAN = '/tmp/claude-0/data5/bls_oews/clean'
R21 = '/tmp/claude-0/dl/oews2021_cran/data/oews2021.rda'      # third-party mirror (cross-check only)
RAW21 = '/tmp/claude-0/dl/bls_oesm21/raw'                     # official BLS oesm21in4.zip / oesm21nat.zip, extracted
ZIP21 = ['/tmp/claude-0/dl/bls_oesm21/oesm21in4.zip', '/tmp/claude-0/dl/bls_oesm21/oesm21nat.zip']
REPO_JSON = '/home/user/last-minute/fit/gm_wage.json'          # written only with --write-repo
SUSB = '/tmp/claude-0/bundle/data/us_6digitnaics_rcptsize_2022.xlsx'
INDEX = '/home/user/last-minute/index.html'
HARNESS = '/tmp/claude-0/fit5/harness.js'
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(20261010)
NBOOT = 400

PC = ['A_PCT10', 'A_PCT25', 'A_MEDIAN', 'A_PCT75', 'A_PCT90']
PN = ['p10', 'p25', 'p50', 'p75', 'p90']
PP = np.array([.10, .25, .50, .75, .90])
ZP = stats.norm.ppf(PP)
LEVEL = {'cross-industry': 0, 'sector': 2, '3-digit': 3, '4-digit': 4, '5-digit': 5, '6-digit': 6}
LOG = []
LOG21 = {}
CAP = {2021: 208000.0, 2023: 239200.0, 2024: 239200.0, 2025: None}   # published top-codes ('#'); none from May 2025


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def num(x):
    if x is None:
        return np.nan, ''
    if isinstance(x, (int, float)):
        return float(x), ''
    s = str(x).strip()
    try:
        return float(s.replace(',', '')), ''
    except ValueError:
        return np.nan, s


# ----------------------------------------------------------------------------------------
# 1. data
# ----------------------------------------------------------------------------------------
def read_raw_year(yr, root=RAW):
    yy = str(yr)[2:]
    files = [(f'oesm{yy}nat/national_M{yr}_dl.xlsx', 'national'),
             (f'oesm{yy}in4/natsector_M{yr}_dl.xlsx', 'sector'),
             (f'oesm{yy}in4/nat3d_M{yr}_dl.xlsx', '3d'),
             (f'oesm{yy}in4/nat4d_M{yr}_dl.xlsx', '4d'),
             (f'oesm{yy}in4/nat5d_6d_M{yr}_dl.xlsx', '5d_6d')]
    rows = []
    for rel, lvl in files:
        p = os.path.join(root, rel)
        ws = openpyxl.load_workbook(p, read_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        hdr = [str(h).strip().upper() if h is not None else '' for h in next(it)]
        ix = {h: i for i, h in enumerate(hdr)}
        for r in it:
            if r[ix['OCC_CODE']] != '11-1021':
                continue
            if str(r[ix['AREA']]).strip() not in ('99', '99.0'):
                continue
            rec = {'YEAR': yr, 'FILE': rel, 'FILE_LEVEL': lvl, 'NAICS': str(r[ix['NAICS']]).strip(),
                   'NAICS_TITLE': str(r[ix['NAICS_TITLE']]).strip(), 'I_GROUP': str(r[ix['I_GROUP']]).strip(),
                   'OWN_CODE': str(r[ix['OWN_CODE']]).strip()}
            for c in ['TOT_EMP', 'EMP_PRSE', 'MEAN_PRSE', 'A_MEAN'] + PC:
                v, fl = num(r[ix[c]])
                rec[c] = v
                rec[c + '_FLAG'] = fl
            rows.append(rec)
    d = pd.DataFrame(rows)
    return d


def load_oews_2325():
    frames = [read_raw_year(y) for y in (2023, 2024, 2025)]
    d = pd.concat(frames, ignore_index=True)
    d = d[d.I_GROUP.isin(LEVEL.keys())].copy()
    d['LEVEL'] = d.I_GROUP.map(LEVEL)
    # one row per (YEAR, NAICS): the 4-digit file repeats some 3-digit industries verbatim
    d = d.sort_values(['YEAR', 'NAICS', 'LEVEL']).copy()
    dup = d.duplicated(['YEAR', 'NAICS'], keep=False)
    for (y, c), g in d[dup].groupby(['YEAR', 'NAICS']):
        a = g[PC].to_numpy(float)
        assert np.allclose(np.nan_to_num(a[0], nan=-1), np.nan_to_num(a[1:], nan=-1)), (y, c)
    d = d.drop_duplicates(['YEAR', 'NAICS'], keep='first').reset_index(drop=True)
    # cross-check against the cleaned extract
    cl = pd.read_csv(os.path.join(CLEAN, 'oews_gm_11-1021_by_naics_2023_2025.csv'), dtype={'NAICS': str, 'OWN_CODE': str})
    cl = cl.drop_duplicates(['YEAR', 'NAICS'])
    m = d.merge(cl[['YEAR', 'NAICS'] + PC + ['MEAN_PRSE', 'TOT_EMP']], on=['YEAR', 'NAICS'], suffixes=('', '_cl'))
    bad = 0
    for c in PC + ['MEAN_PRSE', 'TOT_EMP']:
        a, b = m[c].to_numpy(float), m[c + '_cl'].to_numpy(float)
        bad += int(np.sum(~((np.isnan(a) & np.isnan(b)) | (np.abs(a - b) < 1e-6))))
    say(f'[data] OEWS 2023-25 raw rows (one per year x NAICS): {len(d)}; matched to clean extract: {len(m)}; mismatching values: {bad}')
    assert bad == 0
    d['TOPCODED'] = d[[c + '_FLAG' for c in PC]].apply(lambda r: any(x == '#' for x in r), axis=1)
    return d


def load_oews_2021():
    """May 2021 from the official BLS files; the cran/oews2021 mirror (the source of the app's old
    table) is checked against it cell by cell."""
    d = read_raw_year(2021, RAW21)
    d = d[d.I_GROUP.isin(LEVEL.keys())].copy()
    d['LEVEL'] = d.I_GROUP.map(LEVEL)
    d = d.sort_values(['NAICS', 'LEVEL']).copy()
    dup = d.duplicated('NAICS', keep=False)
    for c, g in d[dup].groupby('NAICS'):
        a = g[PC].to_numpy(float)
        assert np.allclose(np.nan_to_num(a[0], nan=-1), np.nan_to_num(a[1:], nan=-1)), c
    d = d.drop_duplicates('NAICS', keep='first').reset_index(drop=True)
    # May 2021 censors wages >= $208,000 (published as '#')
    d['TOPCODED'] = d[[c + '_FLAG' for c in PC]].apply(lambda r: any(x == '#' for x in r), axis=1)
    r = pyreadr.read_r(R21)
    df = list(r.values())[0]
    g = df[(df.OCC_CODE.astype(str) == '11-1021') & (df.AREA.astype(int) == 99)].copy()
    g['NAICS'] = g.NAICS.astype(str)
    g = g[g.I_GROUP.astype(str).isin(LEVEL.keys())].drop_duplicates('NAICS')
    m = d.merge(g[['NAICS', 'NAICS_TITLE'] + PC + ['TOT_EMP', 'MEAN_PRSE']], on='NAICS', how='outer', suffixes=('', '_cran'), indicator=True)
    both = m[m._merge == 'both']
    bad = 0
    for c in PC + ['TOT_EMP', 'MEAN_PRSE']:
        a, b = both[c].to_numpy(float), both[c + '_cran'].to_numpy(float)
        bad += int(np.sum(~((np.isnan(a) & np.isnan(b)) | (np.abs(np.nan_to_num(a) - np.nan_to_num(b)) < 1e-6))))
    bad += int((both.NAICS_TITLE != both.NAICS_TITLE_cran.astype(str)).sum())
    LOG21.update({'rows': int(len(d)), 'matched_mirror': int(len(both)), 'only_bls': int((m._merge == 'left_only').sum()),
                  'only_mirror': int((m._merge == 'right_only').sum()), 'mismatches': bad, 'topcoded': int(d.TOPCODED.sum())})
    say(f"[data] OEWS May 2021 national industry rows (official BLS oesm21in4/oesm21nat): {len(d)}; cran/oews2021 mirror rows matched: {len(both)} "
        f"(only in BLS {LOG21['only_bls']}, only in mirror {LOG21['only_mirror']}); mismatching values/titles: {bad}; top-coded cells: {LOG21['topcoded']}")
    assert bad == 0
    keep = ['YEAR', 'NAICS', 'NAICS_TITLE', 'I_GROUP', 'OWN_CODE', 'LEVEL', 'TOT_EMP', 'EMP_PRSE', 'MEAN_PRSE', 'A_MEAN', 'TOPCODED'] + PC + [c + '_FLAG' for c in PC]
    return d[keep].reset_index(drop=True)


def load_eci():
    p = os.path.join(RAW, 'eci', 'ci.data.0.Current')
    e = pd.read_csv(p, sep='\t', dtype=str)
    e.columns = [c.strip() for c in e.columns]
    e = e.apply(lambda s: s.str.strip())
    ids = {'CIU2020000000000I': 'all_nsa', 'CIS2020000000000I': 'all_sa',
           'CIU2020000110000I': 'mbf_nsa', 'CIS2020000110000I': 'mbf_sa'}
    e = e[e.series_id.isin(ids) & e.period.str.match(r'Q0[1-4]')].copy()
    e['value'] = e.value.astype(float)
    e['t'] = e.year.astype(int) + (e.period.str[-1].astype(int) * 3) / 12.0   # quarter-end month as year fraction (Mar=+.25)
    w = e.pivot_table(index='t', columns='series_id', values='value').rename(columns=ids).sort_index()
    # cross-check against the cleaned extract
    cl = pd.read_csv(os.path.join(CLEAN, 'eci_private_wages_salaries_nsa.csv'))
    cl['t'] = cl.year + cl.period.str[-1].astype(int) * 3 / 12.0
    mm = cl.set_index('t').index_dec2005_100.reindex(w.index).dropna()
    assert np.allclose(mm.values, w.all_nsa.reindex(mm.index).values), 'ECI mismatch'
    say(f'[data] ECI series {list(w.columns)}; last quarter {w.index.max():.2f} (2026.50 = 2026Q2, June)')
    return w


def eci_at(w, col, t, mode='log'):
    """ECI at time t (year fraction; May = .4167) by interpolation between quarter-end months."""
    s = w[col].dropna()
    x, y = s.index.to_numpy(), s.to_numpy()
    if mode == 'log':
        return float(np.exp(np.interp(t, x, np.log(y))))
    return float(np.interp(t, x, y))


MAY = lambda y: y + 5 / 12.0


def read_app():
    html = open(INDEX, encoding='utf8').read()
    i = html.index('const MODELS = ')
    j = html.index('\n', i)
    M = json.loads(html[i + len('const MODELS = '):j].rstrip().rstrip(';'))
    i2 = html.index('MODELS.fitted=')
    j2 = html.index('\n', i2)
    F = json.loads(html[i2 + len('MODELS.fitted='):j2].rstrip().rstrip(';'))
    # exact substring of the embedded gm_wage block (for harness overrides)
    k = html.index('"gm_wage":', i2)
    depth = 0
    for q in range(k + len('"gm_wage":'), j2):
        ch = html[q]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    gm_sub = html[k:q + 1]
    assert json.loads('{' + gm_sub + '}')['gm_wage'] == F['gm_wage']
    inds = re.findall(r'^\s+(\w+):\s*\{n:"', html[html.index('const IND'):html.index('const IND') + 6000], re.M)
    return M, F, gm_sub, inds


# ----------------------------------------------------------------------------------------
# 2. measurement error and hierarchy
# ----------------------------------------------------------------------------------------
def sector_of(code):
    two = code[:2]
    return {'31': '31-33', '32': '31-33', '33': '31-33', '44': '44-45', '45': '44-45',
            '48': '48-49', '49': '48-49'}.get(two, two)


def kp(sig):
    """SE(ln q_p) / relative SE(mean) for a lognormal with log-sd sig (same effective n)."""
    sig = np.clip(sig, .15, 1.5)
    return np.sqrt(PP * (1 - PP)) / stats.norm.pdf(ZP) * sig / np.sqrt(np.exp(sig ** 2) - 1)


def prep_year(d, kappa=1.0):
    """log percentiles y, measurement SEs s, parent links for one vintage."""
    d = d[~d.NAICS.str.startswith('99')].copy()
    Q = d[PC].to_numpy(float)
    Y = np.log(Q)
    sig = np.where(np.isfinite(Y[:, 0]) & np.isfinite(Y[:, 4]), (Y[:, 4] - Y[:, 0]) / (ZP[4] - ZP[0]),
                   np.where(np.isfinite(Y[:, 1]) & np.isfinite(Y[:, 3]), (Y[:, 3] - Y[:, 1]) / (ZP[3] - ZP[1]), .6))
    prse = np.clip(d.MEAN_PRSE.to_numpy(float), .3, None)
    prse = np.where(np.isfinite(prse), prse, np.nanmedian(prse))
    S = kappa * (prse / 100.0)[:, None] * np.vstack([kp(s) for s in sig])
    d = d.reset_index(drop=True)
    for j, p in enumerate(PN):
        d['y_' + p] = Y[:, j]
        d['s_' + p] = S[:, j]
    d['sigma_log'] = sig
    lv = dict(zip(d.NAICS, d.LEVEL))
    par = []
    for c, L in zip(d.NAICS, d.LEVEL):
        pc = None
        if L >= 3:
            for j in range(L - 1, 2, -1):
                cand = c[:j].ljust(6, '0')
                if cand != c and lv.get(cand, -1) == j:
                    pc = cand
                    break
            if pc is None:
                s2 = sector_of(c)
                pc = s2 if s2 in lv else '000000'
        elif L == 2:
            pc = '000000'
        par.append(pc)
    d['PARENT'] = par
    d['SECTOR'] = [sector_of(c) if L >= 2 else '00' for c, L in zip(d.NAICS, d.LEVEL)]
    return d


def pairs(dy):
    """child/parent differences d and their measurement variances v (one vintage)."""
    ix = dy.set_index('NAICS')
    rows = []
    for _, r in dy.iterrows():
        if r.PARENT is None or r.PARENT not in ix.index:
            continue
        P = ix.loc[r.PARENT]
        w = r.TOT_EMP / P.TOT_EMP if P.TOT_EMP > 0 else np.nan
        if not np.isfinite(w) or w >= .95:
            continue                     # child is (almost) the parent itself: no information on tau
        rec = {'YEAR': r.YEAR, 'NAICS': r.NAICS, 'PARENT': r.PARENT, 'PLEVEL': int(P.LEVEL), 'LEVEL': int(r.LEVEL),
               'SECTOR': r.SECTOR, 'w': w}
        for p in PN:
            rec['d_' + p] = r['y_' + p] - P['y_' + p]
            v = r['s_' + p] ** 2 + P['s_' + p] ** 2 - 2 * w * r['s_' + p] ** 2
            rec['v_' + p] = max(v, (1 - w) ** 2 * r['s_' + p] ** 2)
        rows.append(rec)
    return pd.DataFrame(rows)


def pgroup(plevel):
    return {0: 'sector->US', 2: '3d->sector', 3: '4d+->3d'}.get(plevel, '5d+->4d+')


TAU_SCALED = True   # prior variance of the child-parent gap = tau0^2 (1-w)^2 (the parent row contains the child); False = constant tau^2


def prior_scale(w, scaled=None):
    scaled = TAU_SCALED if scaled is None else scaled
    return (1.0 - w) ** 2 if scaled else 1.0


def paule_mandel(dv, vv, a=None):
    """tau0^2 solving sum d^2/(a tau0^2 + v) = n (a = per-pair prior-variance scale; 1 = classic)."""
    a = np.ones(len(dv)) if a is None else np.asarray(a, float)
    m = np.isfinite(dv) & np.isfinite(vv) & np.isfinite(a)
    dv, vv, a = dv[m], vv[m], a[m]
    n = len(dv)
    if n < 3:
        return np.nan
    f = lambda t2: np.sum(dv ** 2 / (a * t2 + vv)) - n
    if f(0.0) <= 0:
        return 0.0
    return optimize.brentq(f, 0.0, 50.0)


def fit_tau(P, scaled=None):
    """tau0^2 by parent group x percentile (prior mean = parent, df = n)."""
    out = {}
    P = P.assign(G=P.PLEVEL.map(pgroup))
    for g, h in P.groupby('G'):
        a = prior_scale(h.w.to_numpy(float), scaled) * np.ones(len(h))
        for p in PN:
            out[(g, p)] = paule_mandel(h['d_' + p].to_numpy(float), h['v_' + p].to_numpy(float), a)
    return out


def tau_bootstrap(P, nb=NBOOT):
    P = P.assign(G=P.PLEVEL.map(pgroup))
    # resample parent clusters; a group with fewer than 5 parents (sector->US has one) resamples children
    P['CL'] = np.where(P.groupby('G').PARENT.transform('nunique') >= 5, P.PARENT, P.G + ':' + P.NAICS)
    cl = P.CL.unique()
    byc = {c: P[P.CL == c] for c in cl}
    draws = []
    for b in range(nb):
        pick = RNG.choice(cl, len(cl), replace=True)
        Pb = pd.concat([byc[c] for c in pick], ignore_index=True)
        draws.append(fit_tau(Pb))
    keys = draws[0].keys()
    return {k: float(np.nanstd([dd.get(k, np.nan) for dd in draws])) for k in keys}


def tau_cv(P, k=5):
    """k-fold CV by parent cluster: calibration of N(0, prior var + v) for held-out child/parent gaps,
    scaled prior tau0^2 (1-w)^2 and constant prior tau^2 fitted on the same training folds."""
    P = P.assign(G=P.PLEVEL.map(pgroup))
    cl = np.array(sorted(P.PARENT.unique()))
    fold = dict(zip(cl, RNG.permutation(len(cl)) % k))
    P['fold'] = P.PARENT.map(fold)
    rec = []
    for f in range(k):
        tr, te = P[P.fold != f], P[P.fold == f]
        Ts, Tc = fit_tau(tr, scaled=True), fit_tau(tr, scaled=False)
        for _, r in te.iterrows():
            for p in PN:
                dv, vv = r['d_' + p], r['v_' + p]
                ts, tc = Ts.get((r.G, p), np.nan), Tc.get((r.G, p), np.nan)
                if not (np.isfinite(dv) and np.isfinite(ts) and np.isfinite(tc)):
                    continue
                vs, vc = ts * (1 - r.w) ** 2 + vv, tc + vv
                naive = np.nanvar(tr[tr.G == r.G]['d_' + p])      # prior variance ignoring measurement error
                use = vs if TAU_SCALED else vc
                rec.append({'G': r.G, 'p': p, 'w': r.w, 'PARENT': r.PARENT, 'z2': dv ** 2 / use,
                            'z2_scaled': dv ** 2 / vs, 'z2_const': dv ** 2 / vc,
                            'lpd_eb': stats.norm.logpdf(dv, 0, math.sqrt(use)),
                            'lpd_scaled': stats.norm.logpdf(dv, 0, math.sqrt(vs)), 'lpd_const': stats.norm.logpdf(dv, 0, math.sqrt(vc)),
                            'lpd_pool': stats.norm.logpdf(dv, 0, math.sqrt(vv)),
                            'lpd_naive': stats.norm.logpdf(dv, 0, math.sqrt(naive + vv)),
                            'cover90': abs(dv) <= 1.645 * math.sqrt(use),
                            'cover90_scaled': abs(dv) <= 1.645 * math.sqrt(vs), 'cover90_const': abs(dv) <= 1.645 * math.sqrt(vc)})
    return pd.DataFrame(rec)


BMODE = 'tau'      # shrinkage factor used: 'tau' = tau^2/(tau^2+v); 'star' = MSE-optimal with the child-in-parent covariance (sensitivity; see log)


def shrink_weights(s, sP, w, t2):
    """Measurement model: y = th_c + e_c, yP = th_P + e_P, th_c ~ N(th_P, t2), Var e_c = s^2, Var e_P = sP^2,
    Cov(e_c, e_P) = c = w s^2 (the child's sample is part of the parent's). v = Var(e_c - e_P).
    Estimator th_hat = yP + B (y - yP). Classical B_tau = t2/(t2+v) ignores c in the weight; the MSE-optimal
    weight is B_star = (t2 + sP^2 - c)/(t2 + v) (derivative of post_var in B set to zero).
    If e_P = w e_c + (1-w) e_rest then sP >= w s; where the published SEs violate this the parent SE is raised to
    w s (identical to the floor v >= (1-w)^2 s^2 used when estimating tau), which keeps (s, sP, c) a valid covariance."""
    sPe = max(sP, w * s)
    c = w * s * s
    v = s * s + sPe * sPe - 2 * c
    if t2 + v <= 0:
        return v, c, sPe, 1.0, 1.0
    B_tau = t2 / (t2 + v)
    B_star = min(max((t2 + sPe * sPe - c) / (t2 + v), 0.0), 1.0)
    return v, c, sPe, B_tau, B_star


def post_var(B, s, sP, c, t2):
    """MSE of th_hat = yP + B (y - yP) for th_c: error = (1-B)(th_P - th_c) + (1-B) e_P + B e_c."""
    return (1 - B) ** 2 * (t2 + sP * sP) + B * B * s * s + 2 * B * (1 - B) * c


def eb_cell(dy, code, T, Tse=None, extra_prior_var=0.0, bmode=None, scaled=None):
    """posterior for one cell: shrink each log percentile toward the parent row.
    Prior variance t2 = tau0^2 x (1-w)^2 (TAU_SCALED) or tau^2.
    Tse (bootstrap SE of tau0^2) adds tau^2 estimation uncertainty to the posterior SE by the delta method."""
    bmode = bmode or BMODE
    ix = dy.set_index('NAICS')
    r = ix.loc[code]
    P = ix.loc[r.PARENT]
    w = r.TOT_EMP / P.TOT_EMP
    g = pgroup(int(P.LEVEL))
    a = prior_scale(w, scaled)
    res = {'naics': code, 'title': r.NAICS_TITLE, 'parent': r.PARENT, 'parent_title': P.NAICS_TITLE,
           'group': g, 'emp': float(r.TOT_EMP), 'parent_emp': float(P.TOT_EMP), 'mean_prse': float(r.MEAN_PRSE), 'w': float(w)}
    for p in PN:
        y, s, yP, sP_raw = r['y_' + p], r['s_' + p], P['y_' + p], P['s_' + p]
        t2 = T[(g, p)] * a + extra_prior_var
        v, c, sP, B_tau, B_star = shrink_weights(s, sP_raw, w, t2)
        B = B_star if bmode == 'star' else B_tau
        post = yP + B * (y - yP)
        pv = post_var(B, s, sP, c, t2)
        # closed-form check: with B_tau the MSE reduces to B s^2 + (1-B) sP^2
        assert abs(post_var(B_tau, s, sP, c, t2) - (B_tau * s * s + (1 - B_tau) * sP * sP)) < 1e-12
        dB = ((v - sP * sP + c) if bmode == 'star' else v) / (t2 + v) ** 2
        pv_tau = (dB * (y - yP)) ** 2 * ((Tse[(g, p)] * a) ** 2 if Tse is not None else 0.0)
        res[p] = {'raw': float(np.exp(y)), 'parent': float(np.exp(yP)), 'se_log': float(s), 'se_parent_log': float(sP), 'cov': float(c),
                  'tau': float(math.sqrt(T[(g, p)] * a)), 'tau0': float(math.sqrt(T[(g, p)])), 't2': float(t2), 'B': float(B), 'B_tau': float(B_tau), 'B_star': float(B_star),
                  'post': float(np.exp(post)), 'post_Btau': float(np.exp(yP + B_tau * (y - yP))), 'post_Bstar': float(np.exp(yP + B_star * (y - yP))),
                  'post_se_Bstar_known_tau': float(math.sqrt(post_var(B_star, s, sP, c, t2))),
                  'post_se_known_tau': float(math.sqrt(pv)), 'post_se_log': float(math.sqrt(pv + pv_tau)),
                  'old_formula_se': float(math.sqrt(B_tau * v + (1 - B_tau) ** 2 * sP_raw ** 2)), 'sP_floor_binds': bool(sP > sP_raw)}
    return res


def mc_check(table, ndraw=400000):
    """Monte Carlo check of the posterior-SE formula and of B_star, using each app cell's own inputs."""
    rows = []
    for k, t in table.items():
        for p in PN:
            q = t[p]
            s, sP, c, t2 = q['se_log'], q['se_parent_log'], q['cov'], q['t2']
            z = RNG.standard_normal((ndraw, 2))
            ec = s * z[:, 0]
            eP = (c / s) * z[:, 0] + math.sqrt(max(sP * sP - c * c / (s * s), 0.0)) * z[:, 1]
            th = RNG.normal(0.0, math.sqrt(t2), ndraw)        # th_P = 0
            y, yP = th + ec, eP
            err = lambda B: yP + B * (y - yP) - th
            grid = np.linspace(max(q['B'] - .3, 0), 1, 301)
            mse = [np.mean(err(b) ** 2) for b in grid]
            rows.append({'industry': k, 'p': p, 'B_used': q['B'], 'B_tau': q['B_tau'], 'B_star': q['B_star'],
                         'B_mc_opt': float(grid[int(np.argmin(mse))]),
                         'se_mc': float(np.sqrt(np.mean(err(q['B']) ** 2))), 'se_formula': q['post_se_known_tau'],
                         'se_mc_Btau': float(np.sqrt(np.mean(err(q['B_tau']) ** 2))), 'se_old_formula_Btau': q['old_formula_se'],
                         'se_raw': s})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------
# 3. validation helpers
# ----------------------------------------------------------------------------------------
def norm_title(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def matched(Ya, Yb, min_level=2):
    A = Ya.assign(t=Ya.NAICS_TITLE.map(norm_title))
    B = Yb.assign(t=Yb.NAICS_TITLE.map(norm_title))
    m = A.merge(B, on=['NAICS', 't'], suffixes=('_a', '_b'))
    return m[m.LEVEL_a >= min_level].reset_index(drop=True)


def cluster_boot(df, stat, cl='SECTOR_a', nb=NBOOT):
    keys = df[cl].unique()
    groups = {k: df[df[cl] == k] for k in keys}
    out = []
    for _ in range(nb):
        pick = RNG.choice(keys, len(keys), replace=True)
        out.append(stat(pd.concat([groups[k] for k in pick], ignore_index=True)))
    return float(np.nanstd(out))


GL_X, GL_W = np.polynomial.legendre.leggauss(64)


def bvn_upper(za, zb, rho):
    """P(Xa > za, Xb > zb) for standard bivariate normal with correlation rho (vectorised Gauss-Legendre on [za, za+9])."""
    za, zb = np.atleast_1d(za), np.atleast_1d(zb)
    x = za[:, None] + (GL_X[None, :] + 1) * 4.5
    f = stats.norm.pdf(x) * stats.norm.sf((zb[:, None] - rho * x) / math.sqrt(1 - rho * rho))
    return np.clip(np.sum(f * GL_W[None, :], axis=1) * 4.5, 1e-300, 1)


def bvn_growth(ya, yb, ca, cb, x0=None):
    """Mean within-cell growth mu_b - mu_a from a bivariate normal model of (y_a, y_b) across cells with
    top-code censoring at known thresholds ca / cb (log; None = no top-code). Censoring on the observed levels is
    ignorable given the joint model, so cells crossing a top-code (and cells top-coded in both) are kept.
    ya, yb: arrays with NaN where censored (rows with other missing values must be removed by the caller)."""
    ya, yb = np.asarray(ya, float), np.asarray(yb, float)
    oa, ob = np.isfinite(ya), np.isfinite(yb)
    k1, k2, k3, k4 = oa & ob, ~oa & ob, oa & ~ob, ~oa & ~ob
    if not (k2.any() or k3.any() or k4.any()):
        D = yb[k1] - ya[k1]
        return float(np.mean(D)), None

    def nll(th):
        ma, mb, la, lb, zr = th
        sa, sb, r = math.exp(la), math.exp(lb), math.tanh(zr)
        q = math.sqrt(1 - r * r)
        ll = 0.0
        if k1.any():
            ua, ub = (ya[k1] - ma) / sa, (yb[k1] - mb) / sb
            ll += np.sum(-np.log(2 * math.pi * sa * sb * q) - (ua * ua - 2 * r * ua * ub + ub * ub) / (2 * q * q))
        if k2.any():          # y_a above ca, y_b observed
            ub = (yb[k2] - mb) / sb
            ll += np.sum(stats.norm.logpdf(yb[k2], mb, sb) + stats.norm.logsf(((ca - ma) / sa - r * ub) / q))
        if k3.any():          # y_a observed, y_b above cb
            ua = (ya[k3] - ma) / sa
            ll += np.sum(stats.norm.logpdf(ya[k3], ma, sa) + stats.norm.logsf(((cb - mb) / sb - r * ua) / q))
        if k4.any():
            ll += k4.sum() * math.log(bvn_upper(np.array([(ca - ma) / sa]), np.array([(cb - mb) / sb]), r)[0])
        return -ll
    if x0 is None:
        x0 = [np.nanmean(ya), np.nanmean(yb), math.log(np.nanstd(ya)), math.log(np.nanstd(yb)), math.atanh(.9)]
    o = optimize.minimize(nll, x0, method='L-BFGS-B',
                          bounds=[(None, None), (None, None), (-5, 2), (-5, 2), (-3, 3.8)])
    return float(o.x[1] - o.x[0]), o.x


def tobit_mean(D, lo, hi):
    """Marginal two-sided Tobit for the growth itself (sensitivity only: it treats the censoring thresholds as
    independent of the growth, which they are not, since a cell crosses a top-code partly through its own noise)."""
    D, lo, hi = np.asarray(D, float), np.asarray(lo, float), np.asarray(hi, float)
    if len(lo) == 0 and len(hi) == 0:
        return float(np.mean(D)), float(np.std(D))

    def nll(th):
        mu, sd = th[0], math.exp(th[1])
        ll = np.sum(stats.norm.logpdf(D, mu, sd))
        if len(lo):
            ll += np.sum(stats.norm.logsf(lo, mu, sd))
        if len(hi):
            ll += np.sum(stats.norm.logcdf(hi, mu, sd))
        return -ll
    o = optimize.minimize(nll, [float(np.mean(D)), math.log(max(np.std(D), 1e-3))], method='Nelder-Mead',
                          options={'xatol': 1e-7, 'fatol': 1e-9, 'maxiter': 4000})
    return float(o.x[0]), float(math.exp(o.x[1]))


def growth_obs(m, a, b, p):
    """within-cell log growth a->b for one percentile with top-code censoring: exact D, right-censored lower bounds
    (finite at a, '#' at b: D > ln cap_b - y_a), left-censored upper bounds ('#' at a, finite at b: D < y_b - ln cap_a)."""
    ya, yb = m['y_' + p + '_a'], m['y_' + p + '_b']
    fa = m.get(PC[PN.index(p)] + '_FLAG_a', pd.Series('', index=m.index)).fillna('')
    fb = m.get(PC[PN.index(p)] + '_FLAG_b', pd.Series('', index=m.index)).fillna('')
    ex = ya.notna() & yb.notna()
    rc = ya.notna() & (fb == '#') & (CAP[b] is not None)
    lc = (fa == '#') & yb.notna()
    lo = (math.log(CAP[b]) - ya[rc]) if CAP[b] else ya[rc] * np.nan
    hi = yb[lc] - math.log(CAP[a]) if CAP[a] else yb[lc] * np.nan
    return ex, rc, lc, (yb - ya), lo, hi


def growth_validation(Y, eci, nb=60):
    """within-cell OEWS log growth vs ECI-predicted log growth, by vintage pair and percentile.
    mean_dlog: bivariate-normal censored model of the two vintages' levels (cells crossing the old top-codes kept);
    sensitivities: mean_dlog_drop drops censored cells (previous fit), mean_dlog_lb sets end-censored cells to their
    lower bound (start-censored dropped), mean_dlog_tobit is the marginal two-sided Tobit."""
    series = ['mbf_nsa', 'all_nsa', 'mbf_sa', 'all_sa']
    rows = []
    for a, b, kind in [(2021, 2023, '1/3 shared panels'), (2021, 2024, 'no shared panels'), (2021, 2025, 'no shared panels'),
                       (2023, 2024, '2/3 shared (adjacent)'), (2024, 2025, '2/3 shared (adjacent)'), (2023, 2025, '1/3 shared panels')]:
        m = matched(Y[a], Y[b])
        lnG = {s: math.log(eci_at(eci, s, MAY(b)) / eci_at(eci, s, MAY(a))) for s in series}
        ca = math.log(CAP[a]) if CAP[a] else None
        cb = math.log(CAP[b]) if CAP[b] else None
        for p in PN:
            ex, rc, lc, D, lo, hi = growth_obs(m, a, b, p)
            fa = m.get(PC[PN.index(p)] + '_FLAG_a', pd.Series('', index=m.index)).fillna('')
            fb = m.get(PC[PN.index(p)] + '_FLAG_b', pd.Series('', index=m.index)).fillna('')
            # usable rows: each vintage either finite or top-coded ('#'); other missing values ('*') dropped
            use = (m['y_' + p + '_a'].notna() | (fa == '#')) & (m['y_' + p + '_b'].notna() | (fb == '#'))
            ya, yb = m['y_' + p + '_a'][use].to_numpy(float), m['y_' + p + '_b'][use].to_numpy(float)
            sec = m.SECTOR_a[use].to_numpy()
            mu, x0 = bvn_growth(ya, yb, ca, cb)
            mm = m[ex].assign(D=D[ex])
            if x0 is not None:
                keys = np.unique(sec)
                idx = {k: np.where(sec == k)[0] for k in keys}
                bs = []
                for _ in range(nb):
                    ii = np.concatenate([idx[k] for k in RNG.choice(keys, len(keys), replace=True)])
                    bs.append(bvn_growth(ya[ii], yb[ii], ca, cb, x0=x0)[0])
                se_mu = float(np.std(bs))
            else:
                se_mu = cluster_boot(mm, lambda h: h.D.mean())
            lb = pd.concat([mm.D, lo]) if rc.sum() else mm.D
            rec = {'a': a, 'b': b, 'overlap': kind, 'p': p, 'cells': int(len(m)), 'n': int(ex.sum()),
                   'n_censored_start': int(lc.sum()), 'n_censored_end': int(rc.sum()),
                   'n_censored_both': int(((fa == '#') & (fb == '#')).sum()),
                   'mean_dlog': mu, 'se_mean': se_mu, 'mean_dlog_drop': float(mm.D.mean()),
                   'mean_dlog_lb': float(lb.mean()), 'mean_dlog_tobit': tobit_mean(D[ex], lo, hi)[0],
                   'median_dlog': float(mm.D.median()), 'sd_dlog': float(mm.D.std())}
            for s in series:
                rec['lnG_' + s] = lnG[s]
                rec['bias_' + s] = rec['mean_dlog'] - lnG[s]
                rec['bias_drop_' + s] = rec['mean_dlog_drop'] - lnG[s]
                rec['rmse_' + s] = float(np.sqrt(np.mean((mm.D - lnG[s]) ** 2)))
            rows.append(rec)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------
# 3b. noise beyond BLS's sampling SEs: variance components from the six-panel design
# ----------------------------------------------------------------------------------------
T_TARGET = 2026.5          # June 2026 (2026Q2), the date the app's dollars refer to
NOISE_WINDOWS = [(2023, 2024), (2024, 2025), (2023, 2025), (2021, 2023), (2021, 2024), (2021, 2025)]
EXACT_WINDOWS = [(2023, 2024), (2024, 2025), (2023, 2025)]


def panel_dates(v):
    """reference dates of the six semiannual panels behind the May-v estimates (May v, Nov v-1, ..., Nov v-3)."""
    return [round(MAY(v) - 0.5 * i, 4) for i in range(6)]


def lin_coefs(wts):
    """For a linear combination sum_k w_k x(t_k) of panel-level quantities: c_h = sum w^2 (variance per unit of transient
    panel noise h) and c_q = -1/2 sum_kl w_k w_l |t_k - t_l| (variance per unit of random-walk drift q per year; needs sum w = 0)."""
    w = {t: x for t, x in wts.items() if abs(x) > 1e-12}
    ts = list(w)
    return sum(x * x for x in w.values()), -0.5 * sum(w[a] * w[b] * abs(a - b) for a in ts for b in ts)


def window_coefs(a, b):
    w = {}
    for t in panel_dates(b):
        w[t] = w.get(t, 0) + 1 / 6
    for t in panel_dates(a):
        w[t] = w.get(t, 0) - 1 / 6
    ch, cq = lin_coefs(w)
    shared = len(set(panel_dates(a)) & set(panel_dates(b))) / 6.0
    return ch, cq, shared


def target_coefs():
    """June-2026 truth minus the May-2025 six-panel estimate: transient noise enters the estimate as h/6; the cell's drift
    from the panel dates to June 2026 as c_T q."""
    w = {T_TARGET: 1.0}
    for t in panel_dates(2025):
        w[t] = w.get(t, 0) - 1 / 6
    return 1 / 6.0, lin_coefs(w)[1], float(np.mean([T_TARGET - t for t in panel_dates(2025)]))


def noise_frame(Y):
    """level-neutral within-cell changes r (each window x percentile mean removed) with PRSE-implied noise V of the
    difference (shared panels: Cov = shared x s_a s_b). Cells with a top-coded value in either vintage are left out."""
    rows = []
    for k, (a, b) in enumerate(NOISE_WINDOWS):
        ch, cq, sh = window_coefs(a, b)
        m = matched(Y[a], Y[b], min_level=3)
        for j, p in enumerate(PN):
            D = m['y_' + p + '_b'] - m['y_' + p + '_a']
            ok = D.notna()
            V = m['s_' + p + '_a'] ** 2 + m['s_' + p + '_b'] ** 2 - 2 * sh * m['s_' + p + '_a'] * m['s_' + p + '_b']
            prse = np.sqrt(m.MEAN_PRSE_a.clip(lower=.3) * m.MEAN_PRSE_b.clip(lower=.3))
            rows.append(pd.DataFrame({'win': k, 'a': a, 'b': b, 'j': j, 'r': (D - D[ok].mean()), 'V': V, 'prse': prse,
                                      'SECTOR': m.SECTOR_a, 'code': m.NAICS, 'ch': ch, 'cq': cq, 'i21': float(a == 2021)})[ok])
    return pd.concat(rows, ignore_index=True)


def nz_unpack(th):
    J = len(PN)
    return {'h': np.exp(th[:J]), 'q': np.exp(th[J:2 * J]), 'r21': float(np.exp(th[2 * J])), 'k2': float(np.exp(th[2 * J + 1]))}


def nz_var(par, R, use_k=True):
    j = R.j.to_numpy()
    return ((par['k2'] if use_k else 1.0) * R.V.to_numpy() + par['h'][j] * R.ch.to_numpy() + par['q'][j] * R.cq.to_numpy()
            + par['r21'] * R.i21.to_numpy())


def fit_noise(R, fix_k2=None, x0=None):
    """Gaussian quasi-likelihood for Var(r) = kappa^2 V + h_p c_h + q_p c_q + r21 [2021 window] (consistent for the variance
    function whatever the tails)."""
    J = len(PN)
    r2 = R.r.to_numpy() ** 2

    def nll(th):
        par = nz_unpack(th)
        if fix_k2 is not None:
            par['k2'] = fix_k2
        v = nz_var(par, R)
        return 0.5 * np.sum(np.log(v) + r2 / v)
    th0 = x0 if x0 is not None else np.r_[np.log(np.full(J, .02)), np.log(np.full(J, 5e-4)), math.log(5e-4), 0.0]
    o = optimize.minimize(nll, th0, method='L-BFGS-B', bounds=[(-16, 1)] * (2 * J + 1) + [(-4, 3)])
    par = nz_unpack(o.x)
    if fix_k2 is not None:
        par['k2'] = fix_k2
    par['nll'] = float(o.fun)
    par['x'] = o.x
    return par


def extra_var(par, s2, cT):
    """single-vintage extra variance of the June-2026 value beyond BLS sampling error, per percentile:
    (kappa^2 - 1)^+ s^2 + h/6 + c_T q."""
    return max(par['k2'] - 1.0, 0.0) * np.asarray(s2) + par['h'] / 6.0 + cT * par['q']


def noise_model(Y, app_cells, nb=60):
    R = noise_frame(Y)
    hT, cT, lagT = target_coefs()
    full = fit_noise(R)
    exact = fit_noise(R[R.i21 == 0])
    k1 = fit_noise(R, fix_k2=1.0)
    # sector-cluster bootstrap
    sec = R.SECTOR.unique()
    idx = {s_: R.index[R.SECTOR == s_] for s_ in sec}
    boots = []
    for _ in range(nb):
        pick = RNG.choice(sec, len(sec), replace=True)
        boots.append(fit_noise(R.loc[np.concatenate([idx[s_] for s_ in pick])], x0=full['x']))
    ref_s2 = np.array([(0.02 * kp(.6)[j]) ** 2 for j in range(len(PN))])          # a cell with MEAN_PRSE 2%
    Xref = extra_var(full, ref_s2, cT)
    Xref_b = np.array([extra_var(b_, ref_s2, cT) for b_ in boots])
    se = {'k2': float(np.std([b_['k2'] for b_ in boots])), 'h': np.std([b_['h'] for b_ in boots], axis=0),
          'q': np.std([b_['q'] for b_ in boots], axis=0), 'r21': float(np.std([b_['r21'] for b_ in boots])),
          'Xref': Xref_b.std(axis=0), 'sd_ref_lo': np.sqrt(np.quantile(Xref_b, .05, axis=0)), 'sd_ref_hi': np.sqrt(np.quantile(Xref_b, .95, axis=0))}
    # validation 1: leave one window out (fit on the other five, score the held-out window)
    lowo = []
    for k, (a, b) in enumerate(NOISE_WINDOWS):
        tr, te = R[R.win != k], R[R.win == k]
        par = fit_noise(tr, x0=full['x'])
        v_m, v_0 = nz_var(par, te), te.V.to_numpy()
        r2 = te.r.to_numpy() ** 2
        lowo.append({'a': a, 'b': b, 'n': len(te), 'z2_model': float(np.mean(r2 / v_m)), 'z2_prse_only': float(np.mean(r2 / v_0)),
                     'cover90_model': float(np.mean(r2 <= 1.645 ** 2 * v_m)), 'cover90_prse_only': float(np.mean(r2 <= 1.645 ** 2 * v_0)),
                     'k2_train': par['k2']})
        if (a, b) == (2024, 2025):
            par_no2425 = par
    # validation 2: 5-fold by sector
    fold = dict(zip(sorted(sec), RNG.permutation(len(sec)) % 5))
    R['fold'] = R.SECTOR.map(fold)
    R['pq'] = pd.qcut(R.prse, 4, labels=False, duplicates='drop')
    cvr = []
    for f in range(5):
        tr, te = R[R.fold != f], R[R.fold == f]
        par = fit_noise(tr, x0=full['x'])
        park = fit_noise(tr, fix_k2=1.0)           # kappa fixed at 1: all excess as a constant per percentile
        cvr.append(te.assign(v_m=nz_var(par, te), v_0=te.V, v_k=nz_var(park, te)))
    CV = pd.concat(cvr)
    CV['z2m'], CV['z20'], CV['z2k'] = CV.r ** 2 / CV.v_m, CV.r ** 2 / CV.v_0, CV.r ** 2 / CV.v_k
    CV['lpd_gain'] = 0.5 * (np.log(CV.v_k / CV.v_m) + CV.r ** 2 / CV.v_k - CV.r ** 2 / CV.v_m)
    CV['c90m'], CV['c900'] = CV.r ** 2 <= 1.645 ** 2 * CV.v_m, CV.r ** 2 <= 1.645 ** 2 * CV.v_0
    cv_q = CV.groupby('pq').agg(prse=('prse', 'median'), n=('r', 'size'), z2_model=('z2m', 'mean'), z2_prse_only=('z20', 'mean'),
                                z2_kappa1=('z2k', 'mean'), cover90_model=('c90m', 'mean'), cover90_prse_only=('c900', 'mean')).reset_index()
    lg = CV.groupby('SECTOR').lpd_gain.agg(['sum', 'size'])
    bs_ = []
    for _ in range(400):
        pk = RNG.choice(len(lg), len(lg), replace=True)
        bs_.append(lg['sum'].to_numpy()[pk].sum() / lg['size'].to_numpy()[pk].sum())
    lpd_k = {'mean': float(CV.lpd_gain.mean()), 'se': float(np.std(bs_))}
    cv_p = CV.groupby('j').agg(z2_model=('z2m', 'mean'), z2_prse_only=('z20', 'mean'), cover90_model=('c90m', 'mean')).reset_index()
    # validation 3: the app cells' own 2024 -> 2025 changes, scored with the model fitted without that window
    ta = R[(R.a == 2024) & (R.b == 2025) & R.code.isin(set(app_cells))]
    app_z = {'n': int(len(ta)), 'z2_prse_only': float(np.mean(ta.r ** 2 / ta.V)), 'z2_model': float(np.mean(ta.r ** 2 / nz_var(par_no2425, ta))),
             'share_absz_gt2_prse_only': float(np.mean(ta.r ** 2 > 4 * ta.V)), 'share_absz_gt2_model': float(np.mean(ta.r ** 2 > 4 * nz_var(par_no2425, ta)))}
    # descriptive: excess dispersion per window and percentile (mean r^2 - mean V), the reviewers' statistic
    exw = R.assign(ex=R.r ** 2 - R.V).groupby(['a', 'b', 'j']).ex.mean().unstack('j')
    exw.columns = PN
    # pure random-walk alternative (h = 0) fitted on the exact-wage windows, scored on the long 2021-based windows
    Rx = R[R.i21 == 0]
    J = len(PN)

    def nll_rw(th):
        par = {'h': np.zeros(J), 'q': np.exp(th[:J]), 'r21': 0.0, 'k2': 1.0}
        v = nz_var(par, Rx)
        return 0.5 * np.sum(np.log(v) + Rx.r.to_numpy() ** 2 / v)
    o = optimize.minimize(nll_rw, np.log(np.full(J, 1e-3)), method='L-BFGS-B', bounds=[(-16, 1)] * J)
    par_rw = {'h': np.zeros(J), 'q': np.exp(o.x), 'r21': 0.0, 'k2': 1.0}
    Rl = R[R.i21 == 1]
    rw_long = {'z2_rw': float(np.mean(Rl.r ** 2 / nz_var(par_rw, Rl))), 'z2_full': float(np.mean(Rl.r ** 2 / nz_var(full, Rl))),
               'q_rw': par_rw['q'], 'X_rw_ref': par_rw['q'] * cT}
    return {'R': R, 'full': full, 'exact': exact, 'k1': k1, 'se': se, 'cT': cT, 'hT': hT, 'lagT': lagT, 'ref_s2': ref_s2,
            'Xref': Xref, 'Xref_exact': extra_var(exact, ref_s2, cT), 'Xref_k1': extra_var(k1, ref_s2, cT), 'lowo': pd.DataFrame(lowo),
            'cv_q': cv_q, 'cv_p': cv_p, 'lpd_vs_kappa1': lpd_k, 'cv_all': {'z2_model': float(CV.z2m.mean()), 'z2_prse_only': float(CV.z20.mean()),
                                                   'cover90_model': float(CV.c90m.mean()), 'cover90_prse_only': float(CV.c900.mean())},
            'app_z': app_z, 'exw': exw, 'rw_long': rw_long, 'coefs': {f'{a}-{b}': window_coefs(a, b) for a, b in NOISE_WINDOWS}}


def shrink_validation(Y, raw, pairs_list=((2021, 2025), (2021, 2024), (2023, 2025), (2024, 2025)), kappas=(1.0,)):
    """predict vintage b from vintage a: raw cell, EB-shrunk cell (tau from vintage a only), parent row.
    Errors are level-neutral (each predictor's mean growth per percentile removed) so only the
    cross-sectional part is scored."""
    out = []
    for kappa in kappas:
        YY = Y if kappa == 1.0 else {k: prep_year(v, kappa) for k, v in raw.items()}
        for a, b in pairs_list:
            T = fit_tau(pairs(YY[a]))
            Tc = fit_tau(pairs(YY[a]), scaled=False)
            A = YY[a]
            ixA = A.set_index('NAICS')
            Bt = YY[b].assign(t=YY[b].NAICS_TITLE.map(norm_title)).set_index('NAICS')
            rec = []
            for _, r in A.iterrows():
                if r.LEVEL < 3 or r.PARENT not in ixA.index or r.NAICS not in Bt.index:
                    continue
                if norm_title(r.NAICS_TITLE) != Bt.loc[r.NAICS, 't']:
                    continue
                P = ixA.loc[r.PARENT]
                w = r.TOT_EMP / P.TOT_EMP
                if w >= .95:
                    continue
                for p in PN:
                    y, s, yP, sP, yb = r['y_' + p], r['s_' + p], P['y_' + p], P['s_' + p], Bt.loc[r.NAICS, 'y_' + p]
                    if not (np.isfinite(y) and np.isfinite(yP) and np.isfinite(yb)):
                        continue
                    gg = pgroup(int(P.LEVEL))
                    t2 = T[(gg, p)] * prior_scale(w)
                    v, c, sPe, B_tau, B_star = shrink_weights(s, sP, w, t2)
                    B = B_star if BMODE == 'star' else B_tau
                    Bc = shrink_weights(s, sP, w, Tc[(gg, p)])[3]          # constant-tau prior (previous fit)
                    rec.append({'p': p, 'code': r.NAICS, 'SECTOR_a': r.SECTOR, 's': s, 'B': B, 'yb': yb, 'w': w,
                                'raw': y, 'eb': yP + B * (y - yP), 'ebt': yP + B_tau * (y - yP), 'ebs': yP + B_star * (y - yP),
                                'ebc': yP + Bc * (y - yP), 'par': yP})
            R = pd.DataFrame(rec)
            for c in ('raw', 'eb', 'ebt', 'ebs', 'ebc', 'par'):
                R['e_' + c] = R.yb - R[c] - R.groupby('p').apply(lambda h: (h.yb - h[c]).mean()).reindex(R.p).values
            thin = R.s >= .05
            rm = lambda e: float(np.sqrt(np.mean(e ** 2)))
            dm = lambda h: float(np.mean(h.e_eb ** 2 - h.e_raw ** 2))
            dst = lambda h: float(np.mean(h.e_ebs ** 2 - h.e_ebt ** 2))
            dsc = lambda h: float(np.mean(h.e_eb ** 2 - h.e_ebc ** 2))
            out.append({'a': a, 'b': b, 'kappa': kappa, 'n': len(R), 'cells': int(R.code.nunique()),
                        'rmse_raw': rm(R.e_raw), 'rmse_eb': rm(R.e_eb), 'rmse_eb_Btau': rm(R.e_ebt), 'rmse_eb_Bstar': rm(R.e_ebs),
                        'rmse_parent': rm(R.e_par), 'rmse_eb_const_tau': rm(R.e_ebc),
                        'dMSE_scaled_minus_const': dsc(R), 'dMSE_scaled_minus_const_se': cluster_boot(R, dsc),
                        'dMSE_eb_minus_raw': dm(R), 'dMSE_se': cluster_boot(R, dm),
                        'dMSE_Bstar_minus_Btau': dst(R), 'dMSE_Bstar_minus_Btau_se': cluster_boot(R, dst),
                        'thin_n': int(thin.sum()), 'thin_cells': int(R[thin].code.nunique()),
                        'thin_rmse_raw': rm(R.e_raw[thin]), 'thin_rmse_eb': rm(R.e_eb[thin]),
                        'thin_rmse_eb_Btau': rm(R.e_ebt[thin]), 'thin_rmse_eb_Bstar': rm(R.e_ebs[thin]),
                        'thin_rmse_parent': rm(R.e_par[thin]), 'thin_mean_B': float(R.B[thin].mean()),
                        'thin_dMSE': dm(R[thin]), 'thin_dMSE_se': cluster_boot(R[thin], dm)})
    return pd.DataFrame(out)


def kappa_paired_test(Y, raw, kappa, pairs_list=((2021, 2025), (2021, 2024), (2023, 2025), (2024, 2025))):
    """paired out-of-time test of the EB point values with sampling SEs scaled by kappa vs kappa = 1 (level-neutral log errors;
    targets are the published later-vintage cells)."""
    Yk = {k: prep_year(v, kappa) for k, v in raw.items()}

    def preds(YY, a, b):
        T = fit_tau(pairs(YY[a]))
        A = YY[a]
        ixA = A.set_index('NAICS')
        Bt = Y[b].assign(t=Y[b].NAICS_TITLE.map(norm_title)).set_index('NAICS')
        rec = []
        for _, r in A.iterrows():
            if r.LEVEL < 3 or r.PARENT not in ixA.index or r.NAICS not in Bt.index or norm_title(r.NAICS_TITLE) != Bt.loc[r.NAICS, 't']:
                continue
            P = ixA.loc[r.PARENT]
            w = r.TOT_EMP / P.TOT_EMP
            if w >= .95:
                continue
            for p in PN:
                y, s_, yP, sP, yb = r['y_' + p], r['s_' + p], P['y_' + p], P['s_' + p], Bt.loc[r.NAICS, 'y_' + p]
                if not (np.isfinite(y) and np.isfinite(yP) and np.isfinite(yb)):
                    continue
                B = shrink_weights(s_, sP, w, T[(pgroup(int(P.LEVEL)), p)] * prior_scale(w))[3]
                rec.append({'code': r.NAICS, 'p': p, 'SECTOR_a': r.SECTOR, 'yb': yb, 'eb': yP + B * (y - yP)})
        return pd.DataFrame(rec)
    out = []
    for a, b in pairs_list:
        m = preds(Y, a, b).merge(preds(Yk, a, b)[['code', 'p', 'eb']], on=['code', 'p'], suffixes=('', '_k'))
        for c in ('eb', 'eb_k'):
            m['e_' + c] = m.yb - m[c] - m.groupby('p')[['yb', c]].apply(lambda h: (h.yb - h[c]).mean()).reindex(m.p).values
        m['d'] = m.e_eb_k ** 2 - m.e_eb ** 2
        out.append({'a': a, 'b': b, 'kappa': kappa, 'n': len(m), 'rmse_k1': float(np.sqrt(np.mean(m.e_eb ** 2))),
                    'rmse_k': float(np.sqrt(np.mean(m.e_eb_k ** 2))), 'dMSE': float(m.d.mean()), 'dMSE_se': cluster_boot(m, lambda h: h.d.mean())})
    return pd.DataFrame(out)


def kappa_calibration(Y, a, b):
    """E[r^2] = tau_drift_p^2 + kappa^2 (s_a^2 + s_b^2) on non-overlapping vintages."""
    m = matched(Y[a], Y[b])
    rows = []
    for j, p in enumerate(PN[:4]):
        D = m['y_' + p + '_b'] - m['y_' + p + '_a']
        r = D - D.mean()
        V = m['s_' + p + '_a'] ** 2 + m['s_' + p + '_b'] ** 2
        for rr, vv, sec in zip(r, V, m.SECTOR_a):
            if np.isfinite(rr):
                rows.append((j, rr * rr, vv, sec))
    R = pd.DataFrame(rows, columns=['p', 'r2', 'V', 'SECTOR_a'])

    def slope(h):
        X = np.column_stack([pd.get_dummies(h.p).to_numpy(float), h.V])
        return np.linalg.lstsq(X, h.r2.to_numpy(), rcond=None)[0][-1]
    return {'a': a, 'b': b, 'n': len(R), 'kappa2': float(slope(R)), 'kappa2_se': cluster_boot(R, slope)}


# ----------------------------------------------------------------------------------------
# 4. e-commerce bridge (no NAICS-2022 row) and p90 shape model
# ----------------------------------------------------------------------------------------
def bridge_validation(Y, eci):
    """How well does a May-2021 cell carried to May 2025 predict the May-2025 cell?
    (a) via its sector's 2025 row and its 2021 ratio to the sector, (b) via the cross-industry
    row, (c)/(d) own 2021 value x ECI. Scored on cells whose code and title are unchanged."""
    a, b = 2021, 2025
    m = matched(Y[a], Y[b], min_level=3)
    ia, ib = Y[a].set_index('NAICS'), Y[b].set_index('NAICS')
    lnG = {s: math.log(eci_at(eci, s, MAY(b)) / eci_at(eci, s, MAY(a))) for s in ('mbf_nsa', 'all_nsa')}
    rec = []
    for _, r in m.iterrows():
        sec = r.SECTOR_a
        if sec not in ia.index or sec not in ib.index or norm_title(ia.loc[sec, 'NAICS_TITLE']) != norm_title(ib.loc[sec, 'NAICS_TITLE']):
            continue
        for p in PN:
            ya, yb = r['y_' + p + '_a'], r['y_' + p + '_b']
            if not (np.isfinite(ya) and np.isfinite(yb)):
                continue
            pr = {'sector': ib.loc[sec, 'y_' + p] + ya - ia.loc[sec, 'y_' + p],
                  'us': ib.loc['000000', 'y_' + p] + ya - ia.loc['000000', 'y_' + p],
                  'own_eci_mbf': ya + lnG['mbf_nsa'], 'own_eci_all': ya + lnG['all_nsa']}
            pr['combo'] = 0.5 * (pr['sector'] + pr['own_eci_mbf'])      # used: mean of the sector bridge and own x ECI-MBF (fixed, not tuned)
            for k, v in pr.items():
                if np.isfinite(v):
                    rec.append({'p': p, 'method': k, 'err': yb - v, 'SECTOR_a': sec, 'retail': sec == '44-45'})
    R = pd.DataFrame(rec)
    tab = R.groupby(['method', 'p']).err.agg(n='size', bias='mean', rmse=lambda e: float(np.sqrt(np.mean(e ** 2)))).reset_index()
    pooled = R[R.p.isin(PN[:4])].groupby('method').err.agg(n='size', bias='mean', rmse=lambda e: float(np.sqrt(np.mean(e ** 2)))).reset_index()
    pooled['rmse_se'] = [cluster_boot(R[(R.method == k) & R.p.isin(PN[:4])], lambda h: float(np.sqrt(np.mean(h.err ** 2)))) for k in pooled.method]
    return tab, pooled


def p90_shape_model(dy, k=5):
    """ln(p90/p75) = a + b ln(p75/p50) + c ln(p50/p25), fitted on May-2025 cells (no top-code)."""
    h = dy[(dy.LEVEL >= 3)].dropna(subset=['y_' + p for p in PN]).reset_index(drop=True)
    X = np.column_stack([np.ones(len(h)), h.y_p75 - h.y_p50, h.y_p50 - h.y_p25])
    y = (h.y_p90 - h.y_p75).to_numpy()
    fold = RNG.permutation(len(h)) % k
    e_m, e_0 = [], []
    for f in range(k):
        tr, te = fold != f, fold == f
        bb = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
        e_m += list(y[te] - X[te] @ bb)
        e_0 += list(y[te] - y[tr].mean())
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    res = y - X @ beta
    cov = np.linalg.inv(X.T @ X) * (res @ res) / (len(y) - 3)
    return {'beta': beta.tolist(), 'se': np.sqrt(np.diag(cov)).tolist(), 'n': len(h),
            'cv_rmse': float(np.sqrt(np.mean(np.square(e_m)))), 'cv_rmse_constant_ratio': float(np.sqrt(np.mean(np.square(e_0))))}


# ----------------------------------------------------------------------------------------
# 5. firm-size rank (Census SUSB) - sensitivity of the employment-weighted CDF
# ----------------------------------------------------------------------------------------
def susb_knots(codes):
    ws = openpyxl.load_workbook(SUSB, read_only=True).worksheets[0]
    rows = {}
    for r in ws.iter_rows(min_row=4, values_only=True):
        if not r[3] or str(r[0]) not in codes:
            continue
        try:
            rows.setdefault(str(r[0]), {})[str(r[2])] = (float(r[3]), float(r[4]), float(r[5]), float(r[9]) * 1000)
        except (TypeError, ValueError):
            pass
    out = {}
    for c, sz in rows.items():
        tot = sz['01: Total']
        kn, ce, cs = [], 0.0, 0.0
        for k, (f, est, e, rc) in sorted(sz.items()):
            if k.startswith('01') or e < 20 or f < 20:
                continue
            kn.append([math.log(rc / f), (ce + e / 2) / tot[2], (cs + est / 2) / tot[1], est])
            ce += e
            cs += est
        out[c] = kn
    return out


def lerp(x, X, Yv):
    return float(np.interp(x, X, Yv))


def gm_salary_py(G, pct, growth):
    pct = min(max(pct, .1), .9)
    return lerp(pct, [.1, .25, .5, .75, .9], [G['p10'], G['p25'], G['p50'], G['p75'], G['p90']]) * growth


# ----------------------------------------------------------------------------------------
# 6. harness (old vs new gmSalary inside the real model)
# ----------------------------------------------------------------------------------------
def harness_compare(gm_sub_old, gm_new, ex):
    if not os.path.exists(HARNESS):
        return {'skipped': 'harness not found'}
    ov = [[gm_sub_old, '"gm_wage":' + json.dumps(gm_new, separators=(',', ':'))],
          ['return w*F.gm_wage.wage_growth_2021_2026;', 'return w*F.gm_wage.wage_growth;']]
    p = os.path.join(OUT, '_overrides.json')
    json.dump(ov, open(p, 'w'))
    js = r'''
const H=require(process.argv[2]); const ov=JSON.parse(require("fs").readFileSync(process.argv[3],"utf8"));
const EX=JSON.parse(process.argv[4]); const out={};
for(const [tag,o] of [["old",[]],["new",ov]]){ const A=H.load(o); const r={};
  r.grid={}; for(const k of Object.keys(A.IND)) r.grid[k]=[3e5,1e6,3e6,6e6,2e7,1e8].map(v=>Math.round(A.gmSalary({ind:k,rev:v})));
  r.example_gm=A.gmSalary(EX); const r0=A.model(EX); r.example_V=r0.V;
  const it=A.interventionTable(EX,r0).find(x=>x.k==="gm"); r.example_gm_row={c:it.c,dV:it.dV,dE:it.dE,dP:it.dP,roi:it.roi,net:it.net};
  const mono=[]; for(const k of Object.keys(A.IND)){ let prev=0; for(const v of [1e5,3e5,1e6,3e6,1e7,3e7,1e8,1e9]){ const s=A.gmSalary({ind:k,rev:v}); if(s<prev-1e-9) mono.push(k); prev=s; } }
  r.nonmonotone=mono; out[tag]=r; }
console.log(JSON.stringify(out));'''
    jp = os.path.join(OUT, '_cmp.js')
    open(jp, 'w').write(js)
    try:
        res = subprocess.run(['node', jp, HARNESS, p, json.dumps(ex)], capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            return {'error': res.stderr[-2000:]}
        return json.loads(res.stdout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'skipped': str(e)}


# ----------------------------------------------------------------------------------------
# 7. main
# ----------------------------------------------------------------------------------------
EX = {"ind": "medical", "rev": 6e6, "ern": 1.45e6, "grw": .14, "gm": .64, "rec": .72, "cc": .18, "ret": .91, "plt": .38,
      "own": .72, "mgt": .36, "fin": .74, "yrs": 6, "buyers": 65, "st": None, "franchise": False, "ask": 3.24e6}


def finest_cell(code6, codes25):
    for k in (6, 5, 4, 3):
        c = code6[:k].ljust(6, '0')
        if c in codes25:
            return c
    return sector_of(code6)


def main():
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    say('# oews_refresh  (python3 -I /home/user/last-minute/fit/oews_refresh.py)')
    inputs = {p: sha(p) for p in [os.path.join(RAW, f'oesm{y}in4/nat4d_M20{y}_dl.xlsx') for y in ('23', '24', '25')] +
              ZIP21 + [os.path.join(RAW, 'eci/ci.data.0.Current'), R21, SUSB]}
    d = load_oews_2325()
    g21 = load_oews_2021()
    eci = load_eci()
    M, F, gm_sub, inds = read_app()
    raw = {2021: g21, 2023: d[d.YEAR == 2023], 2024: d[d.YEAR == 2024], 2025: d[d.YEAR == 2025]}
    Y = {k: prep_year(v) for k, v in raw.items()}
    say(f'[data] cells per vintage (ex-government): ' + ', '.join(f'{k}: {len(v)}' for k, v in Y.items()))
    say(f'[data] May 2023/2024 top-coded cells (>= $239,200): {int(raw[2023].TOPCODED.sum())}/{int(raw[2024].TOPCODED.sum())}; May 2025: {int(raw[2025].TOPCODED.sum())}')
    bunch = {}
    for yr, dy in Y.items():
        v = dy[PC].to_numpy(float).ravel()
        v = v[np.isfinite(v)]
        vc = pd.Series(v).value_counts()
        bunch[yr] = {'n': int(len(v)), 'distinct': int(vc.size), 'top10_share': float(vc.iloc[:10].sum() / len(v)), 'mode': float(vc.index[0]), 'mode_n': int(vc.iloc[0])}
    say('[data] wage-value bunching (BLS processed private wages in 12 intervals before May 2022): ' + '; '.join(
        f"{yr}: {b['distinct']:,} distinct of {b['n']:,} cell-percentiles, top-10 values cover {b['top10_share']*100:.1f}% (mode {b['mode']:,.0f} x{b['mode_n']})" for yr, b in bunch.items()))

    # ---- between-sibling variance tau^2 (May 2025 cross-section) ------------------------
    P25 = pairs(Y[2025])
    T25 = fit_tau(P25)                         # tau0^2: prior variance tau0^2 (1-w)^2
    T25c = fit_tau(P25, scaled=False)          # constant tau^2 (previous fit), for comparison
    Tse = tau_bootstrap(P25)
    cv = tau_cv(P25)
    cv.to_csv(os.path.join(OUT, 'tau_cv.csv'), index=False)
    grp_n = P25.PLEVEL.map(pgroup).value_counts().to_dict()
    tau_rows = []
    for (gname, p), t2 in sorted(T25.items()):
        h_ = P25[P25.PLEVEL.map(pgroup) == gname]
        tau_rows.append({'group': gname, 'p': p, 'n_pairs': grp_n.get(gname, 0), 'tau0_2': t2, 'tau0_2_se': Tse[(gname, p)], 'tau0': math.sqrt(t2),
                         'tau_at_median_w': math.sqrt(t2) * (1 - float(h_.w.median())), 'median_w': float(h_.w.median()),
                         'tau_const': math.sqrt(T25c[(gname, p)]), 'mean_gap': float(h_['d_' + p].mean())})
    tau_df = pd.DataFrame(tau_rows)
    tau_df.to_csv(os.path.join(OUT, 'tau.csv'), index=False)
    say('[EB] tau0 (log points; prior SD of the child-parent gap = tau0 (1-w)) by parent level x percentile, May 2025, Paule-Mandel; '
        'cluster-bootstrap SE of tau0^2 in brackets; constant-tau fit in braces')
    for gname, h in tau_df.groupby('group'):
        say(f'     {gname:>10} (n={int(h.n_pairs.iloc[0])}, median w {h.median_w.iloc[0]:.2f}): ' +
            '  '.join(f'{r.p} {r.tau0:.3f} [{r.tau0_2_se:.4f}] {{{r.tau_const:.3f}}}' for r in h.itertuples()))
    cvs = cv.groupby('G').agg(n=('z2', 'size'), mean_z2=('z2', 'mean'), mean_z2_const=('z2_const', 'mean'), cover90=('cover90', 'mean'),
                              lpd_eb=('lpd_eb', 'mean'), lpd_const=('lpd_const', 'mean'), lpd_pool=('lpd_pool', 'mean'),
                              lpd_naive=('lpd_naive', 'mean')).reset_index()
    say('[EB] 5-fold CV by parent cluster (held-out child/parent gaps): mean z^2 (1 = calibrated), 90% coverage, mean log predictive density '
        'scaled prior vs constant tau vs complete pooling vs naive prior')
    for r in cvs.itertuples():
        say(f'     {r.G:>10}: n={r.n} z2={r.mean_z2:.2f} (constant tau {r.mean_z2_const:.2f}) cover90={r.cover90:.2f} lpd {r.lpd_eb:.3f} | const {r.lpd_const:.3f} '
            f'| pool {r.lpd_pool:.1f} | naive {r.lpd_naive:.2f}')
    cv['hiw'] = np.where(cv.w >= .3, 'w>=0.3', 'w<0.3')
    cvw = cv.groupby('hiw').agg(n=('z2', 'size'), z2_scaled=('z2_scaled', 'mean'), z2_const=('z2_const', 'mean'),
                                cover90_scaled=('cover90_scaled', 'mean'), cover90_const=('cover90_const', 'mean')).reset_index()
    gain = (cv.lpd_scaled - cv.lpd_const)
    pg = cv.assign(g=gain).groupby('PARENT').g.agg(['sum', 'size'])
    bs_ = []
    for _ in range(NBOOT):
        pk = RNG.choice(len(pg), len(pg), replace=True)
        bs_.append(pg['sum'].to_numpy()[pk].sum() / pg['size'].to_numpy()[pk].sum())
    cv_gain = {'mean': float(gain.mean()), 'se': float(np.std(bs_)), 'n': int(len(cv)), 'parents': int(len(pg))}
    say('[EB] calibration by child share w (scaled vs constant prior): ' + '; '.join(
        f'{r.hiw}: n={r.n} z2 {r.z2_scaled:.2f} vs {r.z2_const:.2f}, cover90 {r.cover90_scaled:.2f} vs {r.cover90_const:.2f}' for r in cvw.itertuples()) +
        f"; log predictive density gain of the scaled prior {cv_gain['mean']:+.3f} per cell-percentile (parent-cluster bootstrap SE {cv_gain['se']:.3f}, n={cv_gain['n']})")
    cv_all = {'mean_z2': float(cv.z2.mean()), 'cover90': float(cv.cover90.mean()), 'n': int(len(cv))}

    # ---- measurement-SE calibration --------------------------------------------------
    kc = [kappa_calibration(Y, 2021, 2025), kappa_calibration(Y, 2021, 2024)]
    for k in kc:
        say(f"[SE] kappa^2 (residual variance per unit of PRSE-implied variance), {k['a']}->{k['b']} (no shared panels): {k['kappa2']:.2f} (SE {k['kappa2_se']:.2f}), n={k['n']}")

    # ---- EB temporal validation --------------------------------------------------------
    sv = shrink_validation(Y, raw, kappas=(1.0, 1.5, 2.0))
    sv.to_csv(os.path.join(OUT, 'shrink_validation.csv'), index=False)
    say('[EB] predict a later vintage from an earlier one (level-neutral log errors). RMSE raw / EB / parent; thin cells = SE >= 0.05')
    for r in sv.itertuples():
        say(f'     kappa {r.kappa:.1f} {r.a}->{r.b}: n={r.n} ({r.cells} cells) {r.rmse_raw:.4f} / {r.rmse_eb:.4f} / {r.rmse_parent:.4f}; '
            f'dMSE {r.dMSE_eb_minus_raw:+.5f} (SE {r.dMSE_se:.5f}) | thin n={r.thin_n} ({r.thin_cells} cells, mean B {r.thin_mean_B:.2f}) '
            f'{r.thin_rmse_raw:.4f} / {r.thin_rmse_eb:.4f} / {r.thin_rmse_parent:.4f}; dMSE {r.thin_dMSE:+.5f} (SE {r.thin_dMSE_se:.5f})')
        say(f'          B_star vs B_tau: RMSE {r.rmse_eb_Bstar:.4f} vs {r.rmse_eb_Btau:.4f}, dMSE {r.dMSE_Bstar_minus_Btau:+.6f} (SE {r.dMSE_Bstar_minus_Btau_se:.6f}); '
            f'thin {r.thin_rmse_eb_Bstar:.4f} vs {r.thin_rmse_eb_Btau:.4f} | scaled vs constant-tau prior: RMSE {r.rmse_eb:.4f} vs {r.rmse_eb_const_tau:.4f}, '
            f'dMSE {r.dMSE_scaled_minus_const:+.6f} (SE {r.dMSE_scaled_minus_const_se:.6f})')

    # ---- growth validation ------------------------------------------------------------
    gv = growth_validation(Y, eci)
    gv.to_csv(os.path.join(OUT, 'growth_validation.csv'), index=False)
    say('[growth] within-cell OEWS log growth vs ECI (wages & salaries, private; MBF = management, business & financial occupations)')
    for (a, b), h in gv.groupby(['a', 'b'], sort=False):
        say(f"     {a}->{b} ({h.overlap.iloc[0]}): ECI MBF {h.lnG_mbf_nsa.iloc[0]:.4f}, all {h.lnG_all_nsa.iloc[0]:.4f} | OEWS mean dlog " +
            ' '.join(f'{r.p} {r.mean_dlog:.4f}({r.se_mean:.4f})' for r in h.itertuples()))
    def gsummary(pcts):
        h = gv[gv.p.isin(pcts)].groupby(['a', 'b'], sort=False).agg(D=('mean_dlog', 'mean'), G_mbf=('lnG_mbf_nsa', 'first'),
                                                                     G_all=('lnG_all_nsa', 'first'), cells=('cells', 'first'),
                                                                     n_min=('n', 'min')).reset_index()
        h['years'] = h.b - h.a
        h['bias_mbf_pa'] = (h.D - h.G_mbf) / h.years
        h['bias_all_pa'] = (h.D - h.G_all) / h.years
        return h
    gsum = gsummary(['p25', 'p50', 'p75'])
    g2550 = gsummary(['p25', 'p50']).set_index(['a', 'b'])
    gsum['bias_mbf_pa_p25p50'] = [g2550.loc[(a, b), 'bias_mbf_pa'] for a, b in zip(gsum.a, gsum.b)]
    gsum['bias_all_pa_p25p50'] = [g2550.loc[(a, b), 'bias_all_pa'] for a, b in zip(gsum.a, gsum.b)]
    cz = gv[gv.p.isin(['p75', 'p90'])]
    say('[growth] top-code censoring (2021 >= $208,000; 2023/2024 >= $239,200; none in 2025): cells top-coded in the start vintage (low growth) '
        'and in the end vintage (high growth) are both kept, through a bivariate-normal censored model of the two vintages\' levels; '
        'start/end/both-censored cells by window: ' + '; '.join(f'{r.a}->{r.b} {r.p} {r.n_censored_start}/{r.n_censored_end}/{r.n_censored_both}' for r in cz.itertuples()))
    say('[growth] p75/p90 mean growth, censored model vs dropping censored cells (previous fit) vs end-censored at lower bound vs marginal Tobit: ' + '; '.join(
        f'{r.a}->{r.b} {r.p} {r.mean_dlog:.4f} / {r.mean_dlog_drop:.4f} / {r.mean_dlog_lb:.4f} / {r.mean_dlog_tobit:.4f}' for r in cz.itertuples()))
    for r in gsum.itertuples():
        say(f'     p25-p75 average {r.a}->{r.b} ({r.cells} matched cells): OEWS {r.D:.4f} vs MBF {r.G_mbf:.4f} (bias {r.bias_mbf_pa*100:+.2f} pp/yr; '
            f'p25/p50 only {r.bias_mbf_pa_p25p50*100:+.2f}) vs all {r.G_all:.4f} (bias {r.bias_all_pa*100:+.2f} pp/yr; p25/p50 only {r.bias_all_pa_p25p50*100:+.2f})')
    CHAIN = [(2021, 2023), (2023, 2024), (2024, 2025)]
    EXACT = [(2023, 2024), (2024, 2025)]          # both vintages use exact reported wages (BLS switched with May 2022)
    sel = lambda h, ws: h[h.apply(lambda r: (r.a, r.b) in ws, axis=1)]
    rms = lambda x: float(np.sqrt(np.mean(np.square(x))))
    chain, exact = sel(gsum, CHAIN), sel(gsum, EXACT)
    rms_mbf, rms_all = rms(chain.bias_mbf_pa), rms(chain.bias_all_pa)
    rms_mbf_x, rms_all_x = rms(exact.bias_mbf_pa), rms(exact.bias_all_pa)
    nono = gsum[(gsum.a == 2021) & (gsum.b.isin([2024, 2025]))]
    say(f'[growth] annualised bias RMS, chained windows 2021-23, 2023-24, 2024-25: MBF {rms_mbf*100:.2f} pp/yr, all-private {rms_all*100:.2f} pp/yr; '
        f'exact-wage windows only (2023-24, 2024-25): MBF {rms_mbf_x*100:.2f}, all-private {rms_all_x*100:.2f}')
    say(f'[growth] 2021->2024 / 2021->2025 bias (cross the 2022 interval->exact wage break): MBF {nono.bias_mbf_pa.iloc[0]*100:+.2f} / {nono.bias_mbf_pa.iloc[1]*100:+.2f} pp/yr '
        f'(p25/p50 only {nono.bias_mbf_pa_p25p50.iloc[0]*100:+.2f} / {nono.bias_mbf_pa_p25p50.iloc[1]*100:+.2f}); all-private {nono.bias_all_pa.iloc[0]*100:+.2f} / {nono.bias_all_pa.iloc[1]*100:+.2f}')
    # per-percentile tracking vs ECI-MBF (annualised): total bias, and the percentile-specific part (bias minus the
    # window's p25-p75 average bias), chained and exact-wage windows
    avg = gsum.set_index(['a', 'b']).bias_mbf_pa
    pct_rows = []
    for p in PN:
        h = gv[gv.p == p].assign(bias=lambda q: (q.mean_dlog - q.lnG_mbf_nsa) / (q.b - q.a))
        h['spec'] = [bb - avg.loc[(a_, b_)] for bb, a_, b_ in zip(h.bias, h.a, h.b)]
        rc, rx = rms(sel(h, CHAIN).bias), rms(sel(h, EXACT).bias)
        sc, sx = rms(sel(h, CHAIN).spec), rms(sel(h, EXACT).spec)
        g_ = lambda a_, b_, col='bias': float(h[(h.a == a_) & (h.b == b_)][col].iloc[0])
        pct_rows.append({'p': p, 'rms_chain_pa': rc, 'rms_exact_pa': rx, 'rms_spec_chain_pa': sc, 'rms_spec_exact_pa': sx,
                         'bias_2021_2025_pa': g_(2021, 2025), 'bias_2024_2025': g_(2024, 2025), 'bias_2023_2025_pa': g_(2023, 2025),
                         'bias_2023_2024': g_(2023, 2024), 'spec_2021_2025_pa': g_(2021, 2025, 'spec'), 'spec_2023_2025_pa': g_(2023, 2025, 'spec'),
                         'bias_drop_2023_2024': float(gv[(gv.p == p) & (gv.a == 2023) & (gv.b == 2024)].bias_drop_mbf_nsa.iloc[0])})
    pct_df = pd.DataFrame(pct_rows)

    # ---- forward growth factor May 2025 -> 2026Q2 ---------------------------------------
    t0, t1 = MAY(2025), T_TARGET
    variants = {}
    for s in ('mbf_nsa', 'mbf_sa', 'all_nsa', 'all_sa'):
        for mode in ('log', 'lin'):
            variants[f'{s}_{mode}'] = eci_at(eci, s, t1, mode) / eci_at(eci, s, t0, mode)
    G = variants['mbf_nsa_log']
    # the series choice (MBF vs all-private) is not discriminated by the exact-wage windows, so it is part of the spec spread
    G_spec_sd = float(np.std(list(variants.values())))
    G_all = variants['all_nsa_log']
    yrs = t1 - t0
    hT, cT, LAG = target_coefs()           # LAG = mean time from the May-2025 panels (Nov 2022 - May 2025) to June 2026
    rms_used = max(rms_mbf, rms_mbf_x)
    # economy-wide factor: how well the ECI tracks average within-cell GM wage growth, over the forward 1.083 yr
    # (broad-group movement over the panels' own lag is absorbed by BLS's aging factors)
    G_se = math.sqrt(G_spec_sd ** 2 + (rms_used * yrs * G) ** 2)
    G_se_lag = math.sqrt(G_spec_sd ** 2 + (rms_used * LAG * G) ** 2)      # sensitivity: if aging missed it too
    pct_df['rms_spec_used_pa'] = pct_df[['rms_spec_chain_pa', 'rms_spec_exact_pa']].max(axis=1)
    pct_df['rms_used_pa'] = pct_df[['rms_chain_pa', 'rms_exact_pa']].max(axis=1)
    # percentile-specific movement enters the six-panel estimate only through new panels (older panels are aged by a
    # broad-group factor that is the same for every percentile), so it accumulates over the full 2.33-yr lag
    pct_df['growth_se'] = np.sqrt(G_se ** 2 + (pct_df.rms_spec_used_pa * LAG * G) ** 2)
    pct_df['growth_se_prev_def'] = np.sqrt(G_spec_sd ** 2 + (pct_df.rms_used_pa * yrs * G) ** 2)
    # if a percentile's drift continued: the forward 1.083 yr add its whole bias vs the ECI, the panels' own 1.25-yr lag only
    # its percentile-specific part (BLS ages old panels by a broad-group factor)
    pct_df['shortfall_if_drift_continues_2021_25'] = np.exp(pct_df.bias_2021_2025_pa * yrs + pct_df.spec_2021_2025_pa * (LAG - yrs)) - 1
    pct_df['shortfall_if_drift_continues_2023_25'] = np.exp(pct_df.bias_2023_2025_pa * yrs + pct_df.spec_2023_2025_pa * (LAG - yrs)) - 1
    pct_df.to_csv(os.path.join(OUT, 'growth_by_percentile.csv'), index=False)
    say(f'[growth] factor May 2025 -> 2026Q2 (June 2026), {yrs:.3f} yr: ECI MBF {G:.4f} (I {eci_at(eci,"mbf_nsa",t0):.3f} -> {eci_at(eci,"mbf_nsa",t1):.3f}); '
        f'all-private {G_all:.4f}; spec SD (8 variants incl. all-private) {G_spec_sd:.4f}; economy-wide SE incl. tracking RMS {rms_used*100:.2f} pp/yr x {yrs:.3f} yr '
        f'= {G_se:.4f} ({G_se_lag:.4f} if the tracking error also ran over the {LAG:.2f}-yr panel lag)')
    say('          variants: ' + ', '.join(f'{k} {v:.4f}' for k, v in variants.items()))
    say(f'[growth] per-percentile tracking vs ECI-MBF (pp/yr; percentile-specific part = bias minus the window\'s p25-p75 average, carried over the {LAG:.2f}-yr lag): ' + '; '.join(
        f"{r.p} RMS chain {r.rms_chain_pa*100:.2f} / exact {r.rms_exact_pa*100:.2f}, specific chain {r.rms_spec_chain_pa*100:.2f} / exact {r.rms_spec_exact_pa*100:.2f}, "
        f"bias 2021-25 {r.bias_2021_2025_pa*100:+.2f}, 2023-25 {r.bias_2023_2025_pa*100:+.2f}, 2024-25 {r.bias_2024_2025*100:+.2f} -> growth SE {r.growth_se:.4f}" for r in pct_df.itertuples()))
    old_growth_check = (eci_at(eci, 'all_nsa', T_TARGET) / eci_at(eci, 'all_nsa', MAY(2021)))
    say(f'[growth] old factor 1.233 (May 2021 -> 2026, partly assumed); actual ECI all-private May 2021 -> 2026Q2 = {old_growth_check:.4f}, '
        f'MBF = {eci_at(eci,"mbf_nsa",2026.5)/eci_at(eci,"mbf_nsa",MAY(2021)):.4f}')

    # ---- app cells ----------------------------------------------------------------------
    n6 = M['value']['naics6_for_industry']
    codes25 = set(Y[2025][Y[2025].LEVEL >= 3].NAICS)
    oldgm = F['gm_wage']['by_industry']
    cell = {}
    for k in inds:
        if k == 'saas':
            cell[k] = '513200'
        elif k == 'ecom':
            cell[k] = None
        else:
            cell[k] = finest_cell(n6[k], codes25)
    say('[map] app industry -> May-2025 OEWS cell (old May-2021 cell): ' + ', '.join(f"{k} {cell[k]} ({oldgm[k]['naics']})" for k in inds))
    table = {}
    for k in inds:
        if cell[k] is None:
            continue
        table[k] = eb_cell(Y[2025], cell[k], T25, Tse)
    mc = mc_check(table)
    mc.to_csv(os.path.join(OUT, 'posterior_se_mc_check.csv'), index=False)
    mc['rel'] = mc.se_formula / mc.se_mc - 1
    mc['rel_old'] = mc.se_old_formula_Btau / mc.se_mc_Btau - 1
    say(f'[EB] Monte Carlo check of the posterior SE (400k draws per app cell x percentile, each with its own s, sP, cov, tau^2): '
        f'formula / simulated RMSE - 1 within {mc.rel.abs().max()*100:.2f}% (old formula B v + (1-B)^2 sP^2 was off by {mc.rel_old.min()*100:+.0f}% to {mc.rel_old.max()*100:+.0f}%); '
        f'B_star vs simulated MSE-optimal B: max |diff| {np.max(np.abs(mc.B_star - mc.B_mc_opt)):.3f}; B_tau vs it: max |diff| {np.max(np.abs(mc.B_tau - mc.B_mc_opt)):.3f}')
    # constant-tau prior (previous fit) for comparison
    table_c = {k: eb_cell(Y[2025], cell[k], T25c, scaled=False) for k in table}
    cdiff = {k: max(abs(table[k][p]['post'] / table_c[k][p]['post'] - 1) for p in PN) for k in table}
    say('[EB] scaled prior tau0^2 (1-w)^2 vs constant tau^2: largest app-cell changes ' +
        ', '.join(f"{k} (w {table[k]['w']:.2f}) {v*100:.2f}%" for k, v in sorted(cdiff.items(), key=lambda kv: -kv[1])[:5]) +
        '; B p10..p90 ' + ', '.join(f"{k} " + '/'.join(f"{table_c[k][p]['B']:.2f}->{table[k][p]['B']:.2f}" for p in PN)
                                    for k, v in sorted(cdiff.items(), key=lambda kv: -kv[1])[:2]))
    bdiff = {k: max(abs(table[k][p]['post_Bstar'] / table[k][p]['post_Btau'] - 1) for p in PN) for k in table}
    say(f'[EB] shrinkage factor used: {BMODE}. B_star (MSE-optimal with child-in-parent covariance) vs B_tau = tau^2/(tau^2+v): largest app-cell changes ' +
        ', '.join(f'{k} {v*100:.2f}%' for k, v in sorted(bdiff.items(), key=lambda kv: -kv[1])[:4]))
    # kappa sensitivity
    Y15 = prep_year(raw[2025], 1.5)
    T15 = fit_tau(pairs(Y15))
    sens15 = {}
    for k, c in cell.items():
        if c is None:
            continue
        e15 = eb_cell(Y15, c, T15)
        sens15[k] = max(abs(e15[p]['post'] / table[k][p]['post'] - 1) for p in PN)

    # ---- noise beyond the published sampling SEs; total SE of each cell's June-2026 value ------------------------
    NZ = noise_model(Y, [c for c in cell.values() if c])
    nzf, nzse = NZ['full'], NZ['se']
    NZ['lowo'].to_csv(os.path.join(OUT, 'noise_lowo.csv'), index=False)
    NZ['cv_q'].to_csv(os.path.join(OUT, 'noise_cv_by_prse.csv'), index=False)
    NZ['exw'].to_csv(os.path.join(OUT, 'excess_dispersion_by_window.csv'))
    say(f"[noise] variance components (quasi-likelihood, 6 vintage pairs, {len(NZ['R'])} cell-percentile changes, sector-cluster bootstrap SE): "
        f"kappa^2 {nzf['k2']:.2f} (SE {nzse['k2']:.2f}); transient panel noise h p10..p90 " + '/'.join(f'{x:.4f}' for x in nzf['h']) +
        ' (SE ' + '/'.join(f'{x:.4f}' for x in nzse['h']) + '); random-walk drift q ' + '/'.join(f'{x:.5f}' for x in nzf['q']) +
        f" per yr; May-2021 interval noise {nzf['r21']:.4f} (SE {nzse['r21']:.4f}); design coefficients (c_h, c_q, shared) " +
        ', '.join(f'{k} ({v[0]:.3f}, {v[1]:.3f}, {v[2]:.2f})' for k, v in NZ['coefs'].items()) + f"; target c_T {NZ['cT']:.3f}, mean panel lag {NZ['lagT']:.2f} yr")
    say('[noise] extra SD of a June-2026 value for a cell with MEAN_PRSE 2% (beyond its published SE), p10..p90: ' + '/'.join(f'{math.sqrt(x):.3f}' for x in NZ['Xref']) +
        ' (bootstrap 90% ' + '/'.join(f'{lo:.3f}-{hi:.3f}' for lo, hi in zip(nzse['sd_ref_lo'], nzse['sd_ref_hi'])) + '); exact-wage windows only ' +
        '/'.join(f'{math.sqrt(x):.3f}' for x in NZ['Xref_exact']) + f" (kappa^2 {NZ['exact']['k2']:.2f}); kappa fixed at 1 " + '/'.join(f'{math.sqrt(x):.3f}' for x in NZ['Xref_k1']))
    say('[noise] excess dispersion of level-neutral changes (mean r^2 - mean V), by window, p10..p90: ' + '; '.join(
        f'{a}->{b} ' + '/'.join(f'{x:.4f}' for x in r) for (a, b), r in NZ['exw'].iterrows()))
    say('[noise] leave-one-window-out (fit on 5 windows, score the 6th): mean z^2 model vs PRSE-only, 90% coverage: ' + '; '.join(
        f'{r.a}->{r.b} {r.z2_model:.2f} vs {r.z2_prse_only:.2f}, {r.cover90_model:.2f} vs {r.cover90_prse_only:.2f}' for r in NZ['lowo'].itertuples()))
    say('[noise] 5-fold by sector, by MEAN_PRSE quartile (median PRSE): mean z^2 model / kappa-fixed-at-1 / PRSE-only, coverage model: ' + '; '.join(
        f'{r.prse:.1f}%: {r.z2_model:.2f} / {r.z2_kappa1:.2f} / {r.z2_prse_only:.2f}, {r.cover90_model:.2f}' for r in NZ['cv_q'].itertuples()) +
        f"; overall {NZ['cv_all']['z2_model']:.2f} / PRSE-only {NZ['cv_all']['z2_prse_only']:.2f}, coverage {NZ['cv_all']['cover90_model']:.2f} vs {NZ['cv_all']['cover90_prse_only']:.2f}; "
        f"log predictive density gain over kappa=1 {NZ['lpd_vs_kappa1']['mean']:+.3f} (SE {NZ['lpd_vs_kappa1']['se']:.3f})")
    say(f"[noise] app cells' own 2024->2025 changes (model fitted without that window): mean z^2 {NZ['app_z']['z2_model']:.2f} vs PRSE-only {NZ['app_z']['z2_prse_only']:.2f}; "
        f"|z|>2 {NZ['app_z']['share_absz_gt2_model']*100:.0f}% vs {NZ['app_z']['share_absz_gt2_prse_only']*100:.0f}% (n={NZ['app_z']['n']})")
    say(f"[noise] pure random-walk drift fitted on the exact-wage windows over-predicts the 3-4 year 2021-based windows: mean z^2 there {NZ['rw_long']['z2_rw']:.2f} "
        f"(full model {NZ['rw_long']['z2_full']:.2f}); it would give extra SDs " + '/'.join(f'{math.sqrt(x):.3f}' for x in NZ['rw_long']['X_rw_ref']))
    # typical one-year move of a cell relative to the economy-wide change (PRSE-2% cell, p25-p75): model-implied, and observed
    ch1, cq1, sh1 = window_coefs(2024, 2025)
    v1 = [nzf['k2'] * (2 - 2 * sh1) * NZ['ref_s2'][j] + nzf['h'][j] * ch1 + nzf['q'][j] * cq1 for j in (1, 2, 3)]
    move_1y_ref = float(math.sqrt(np.mean(v1)))
    R1 = NZ['R'][(NZ['R'].a == 2024) & (NZ['R'].b == 2025) & NZ['R'].j.isin([1, 2, 3]) & (NZ['R'].prse <= 3.0)]
    move_1y_obs = float(np.sqrt(np.mean(R1.r ** 2)))
    say(f'[noise] one-year move of a cell relative to the economy-wide change (p25-p75): model SD for a PRSE-2% cell {move_1y_ref:.3f}; '
        f'observed RMS 2024->2025 for cells with PRSE <= 3% {move_1y_obs:.3f} (n={len(R1)})')
    gse_p = pct_df.growth_se.to_numpy()
    for k in table:
        s2raw = np.array([table[k][p]['se_log'] ** 2 for p in PN])
        X = extra_var(nzf, s2raw, NZ['cT'])
        for j, p in enumerate(PN):
            table[k][p]['extra_sd'] = float(math.sqrt(X[j]))
            table[k][p]['se_total'] = float(math.sqrt(table[k][p]['post_se_log'] ** 2 + X[j] + gse_p[j] ** 2))

    # EB point values if the sampling SEs were scaled by the fitted kappa (sensitivity; the EB keeps kappa = 1)
    kh = math.sqrt(nzf['k2'])
    Yk = prep_year(raw[2025], kh)
    Tk = fit_tau(pairs(Yk))
    sensk = {k: max(abs(eb_cell(Yk, c, Tk)[p]['post'] / table[k][p]['post'] - 1) for p in PN) for k, c in cell.items() if c}
    say(f'[EB] point values with sampling SEs scaled by the fitted kappa {kh:.2f}: largest app-cell changes ' +
        ', '.join(f'{k} {v*100:.1f}%' for k, v in sorted(sensk.items(), key=lambda kv: -kv[1])[:4]))
    kpt = kappa_paired_test(Y, raw, kh)
    kpt.to_csv(os.path.join(OUT, 'kappa_paired_test.csv'), index=False)
    say(f'[EB] paired out-of-time test, EB with kappa {kh:.2f} minus kappa 1 (dMSE of level-neutral log errors; negative = fitted kappa better): ' +
        '; '.join(f'{r.a}->{r.b} RMSE {r.rmse_k1:.4f} -> {r.rmse_k:.4f}, dMSE {r.dMSE:+.5f} (SE {r.dMSE_se:.5f})' for r in kpt.itertuples()))

    # ---- e-commerce bridge ---------------------------------------------------------------
    btab, bpool = bridge_validation(Y, eci)
    btab.to_csv(os.path.join(OUT, 'bridge_validation.csv'), index=False)
    say('[ecom] bridge methods scored on cells with unchanged code and title, May 2021 -> May 2025 (p10-p75 pooled log errors):')
    for r in bpool.sort_values('rmse').itertuples():
        say(f'     {r.method:>12}: n={r.n} bias {r.bias:+.4f} RMSE {r.rmse:.4f} (SE {r.rmse_se:.4f})')
    best = bpool.sort_values('rmse').method.iloc[0]
    USE = 'combo'        # the candidates are statistically tied, so the two conceptually distinct ones are averaged
    shp = p90_shape_model(Y[2025])
    say(f"[ecom] p90 shape model ln(p90/p75) = {shp['beta'][0]:.3f} + {shp['beta'][1]:.3f} ln(p75/p50) + {shp['beta'][2]:.3f} ln(p50/p25); "
        f"n={shp['n']}, 5-fold CV RMSE {shp['cv_rmse']:.4f} vs constant ratio {shp['cv_rmse_constant_ratio']:.4f}")
    i21, i25 = Y[2021].set_index('NAICS'), Y[2025].set_index('NAICS')
    e21 = i21.loc['454100']
    lnG2125 = {s: math.log(eci_at(eci, s, MAY(2025)) / eci_at(eci, s, MAY(2021))) for s in ('mbf_nsa', 'all_nsa')}

    def bridge(meth):
        v = {}
        for p in PN[:4]:
            sec_ = i25.loc['44-45', 'y_' + p] + e21['y_' + p] - i21.loc['44-45', 'y_' + p]
            v[p] = {'sector': sec_, 'us': i25.loc['000000', 'y_' + p] + e21['y_' + p] - i21.loc['000000', 'y_' + p],
                    'own_eci_mbf': e21['y_' + p] + lnG2125['mbf_nsa'], 'own_eci_all': e21['y_' + p] + lnG2125['all_nsa'],
                    'combo': 0.5 * (sec_ + e21['y_' + p] + lnG2125['mbf_nsa'])}[meth]
        v['p90'] = v['p75'] + shp['beta'][0] + shp['beta'][1] * (v['p75'] - v['p50']) + shp['beta'][2] * (v['p50'] - v['p25'])
        return v
    ecom = bridge(USE)
    ret75 = math.exp(i25.loc['44-45', 'y_p75'] - i21.loc['44-45', 'y_p75']) - 1        # Retail's own p75 growth May 2021 -> May 2025
    eci2125 = math.exp(lnG2125['mbf_nsa']) - 1
    lb90 = math.log(208000.0) + (i25.loc['44-45', 'y_p90'] - i21.loc['44-45', 'y_p90'])   # 2021 p90 was >= $208k
    brm = btab[btab.method == USE].set_index('p').rmse
    ecom_se = {p: float(brm[p]) for p in PN[:4]}
    ecom_se['p90'] = float(math.sqrt(brm['p75'] ** 2 + shp['cv_rmse'] ** 2))
    alt = {meth: [round(float(np.exp(bridge(meth)[p])), -1) for p in PN] for meth in ('sector', 'combo', 'own_eci_mbf', 'own_eci_all', 'us')}
    table['ecom'] = {'naics': '44-45 (bridged from 454100, May 2021)', 'title': 'E-commerce (bridged)', 'parent': '44-45',
                     'parent_title': 'Retail Trade', 'group': 'bridge:' + USE, 'emp': float(e21.TOT_EMP), 'mean_prse': float(e21.MEAN_PRSE)}
    for j, p in enumerate(PN):
        # bridge RMSE is scored against observed (noisy) May-2025 cells, so it already contains a cell's own noise; add the
        # forward drift (May 2025 -> June 2026, 1.083 yr x q) and the percentile growth SE
        se_tot = math.sqrt(ecom_se[p] ** 2 + (T_TARGET - MAY(2025)) * nzf['q'][j] + gse_p[j] ** 2)
        table['ecom'][p] = {'raw': float(np.exp(ecom[p])), 'parent': float(np.exp(i25.loc['44-45', 'y_' + p])), 'se_log': ecom_se[p],
                            'tau': float('nan'), 'B': float('nan'), 'post': float(np.exp(ecom[p])), 'post_se_log': ecom_se[p],
                            'se_total': se_tot, 'extra_sd': float('nan')}
    say(f"[ecom] bridge used '{USE}' (mean of sector bridge and own x ECI-MBF; lowest-RMSE candidate '{best}'): " +
        ' '.join(f"{p} {table['ecom'][p]['post']:,.0f} (SE {ecom_se[p]:.3f})" for p in PN) +
        f"; p90 lower bound from the 2021 top-code {math.exp(lb90):,.0f}; all methods p10..p90 (p90 by the shape model): {alt}")
    assert ecom['p90'] >= lb90 - 1e-9, 'bridged ecom p90 below the bound implied by the 2021 top-code'

    # ---- assemble new block --------------------------------------------------------------
    by = {}
    rows = []
    for k in inds:
        t = table[k]
        vals = [round(t[p]['post'], -1) for p in PN]
        assert all(np.diff(vals) > 0), f'{k}: percentiles not increasing {vals}'
        ent = {'naics': cell[k] if cell[k] else '44-45', 'p10': vals[0], 'p25': vals[1], 'p50': vals[2], 'p75': vals[3], 'p90': vals[4],
               'se_sampling': [round(t[p]['post_se_log'], 3) for p in PN], 'se_total': [round(t[p]['se_total'], 3) for p in PN]}
        if k == 'ecom':
            ent['bridge'] = ('mean of 454100 (May 2021) relative to Retail 44-45 and 454100 x ECI; p75 ' +
                             f"{min(v[3] for v in alt.values()):,.0f}-{max(v[3] for v in alt.values()):,.0f}, p90 {min(v[4] for v in alt.values()):,.0f}-"
                             f"{max(v[4] for v in alt.values()):,.0f} across bridges")
        by[k] = ent
        o = oldgm[k]
        rows.append({'industry': k, 'cell_2025': t['naics'], 'title': t['title'], 'parent': t['parent'], 'parent_title': t['parent_title'],
                     'group': t['group'], 'emp_2025': t['emp'], 'mean_prse': t['mean_prse'],
                     **{f'raw_{p}': round(t[p]['raw'], -1) for p in PN}, **{f'parent_{p}': round(t[p]['parent'], -1) for p in PN},
                     **{f'B_{p}': round(t[p]['B'], 3) for p in PN}, **{f'Btau_{p}': round(t[p].get('B_tau', float('nan')), 3) for p in PN},
                     **{f'post_{p}': round(t[p]['post'], -1) for p in PN}, **{f'postBtau_{p}': round(t[p].get('post_Btau', float('nan')), -1) for p in PN},
                     **{f'se_{p}': round(t[p]['post_se_log'], 4) for p in PN}, **{f'se_raw_{p}': round(t[p]['se_log'], 4) for p in PN},
                     **{f'se_total_{p}': round(t[p]['se_total'], 4) for p in PN}, **{f'extra_sd_{p}': round(t[p].get('extra_sd', float('nan')), 4) for p in PN},
                     **{f'postconst_{p}': round(table_c[k][p]['post'], -1) if k in table_c else float('nan') for p in PN},
                     **{f'se_oldformula_{p}': round(t[p].get('old_formula_se', float('nan')), 4) for p in PN},
                     **{f'old_{p}': o[p] for p in PN},
                     **{f'new2026_{p}': round(t[p]['post'] * G, -1) for p in PN}, **{f'old2026_{p}': round(o[p] * 1.233, -1) for p in PN},
                     'kappa15_max_change': sens15.get(k, float('nan'))})
    app = pd.DataFrame(rows)
    app.to_csv(os.path.join(OUT, 'app_table.csv'), index=False)
    say('[table] May-2025 EB percentiles (raw -> shrunk, B) and 2026Q2 dollars vs old app (2021 x 1.233):')
    for r in app.itertuples():
        say(f"     {r.industry:>7} {r.cell_2025[:6]:>6}->{r.parent:>6} PRSE {r.mean_prse:4.1f}: " +
            ' '.join(f"{p} {getattr(r,'raw_'+p):>7,.0f}->{getattr(r,'post_'+p):>7,.0f}(B {getattr(r,'B_'+p):.2f})" for p in PN))
        say(f"             2026$: new " + ' '.join(f"{getattr(r,'new2026_'+p):>7,.0f}" for p in PN) +
            ' | old ' + ' '.join(f"{getattr(r,'old2026_'+p):>7,.0f}" for p in PN) + f" | kappa=1.5 max change {r.kappa15_max_change * 100:.1f}%")
        say(f"             SE sampling " + '/'.join(f"{getattr(r,'se_'+p):.3f}" for p in PN) + ' | extra ' + '/'.join(f"{getattr(r,'extra_sd_'+p):.3f}" for p in PN) +
            ' | total ' + '/'.join(f"{getattr(r,'se_total_'+p):.3f}" for p in PN))
    se_note = ('log-point SEs p10..p90. se_sampling: BLS sampling error of the May-2025 value after shrinkage (published PRSE, kappa=1). '
               f"se_total: SE of the June-2026 value; adds the noise the published SEs miss (fitted on six OEWS vintage pairs: kappa^2 {nzf['k2']:.1f} "
               'plus panel-level noise; little persistent drift) and wage_growth_se_pct. Documentation only; gmSalary does not read them.')
    gm_new = {'by_industry': by, 'base': 'OEWS May 2025', 'wage_growth': round(G, 4), 'wage_growth_to': '2026Q2',
              'wage_growth_se': round(G_se, 4), 'wage_growth_se_pct': [round(float(x), 4) for x in pct_df.growth_se],
              'wage_growth_se_note': (f'wage_growth_se: SE of the economy-wide factor (ECI vs average within-industry OEWS growth). wage_growth_se_pct adds '
                                      f'percentile-specific drift over the {LAG:.2f}-yr panel lag. A single industry cell moves about '
                                      f"{100 * move_1y_ref:.0f}% (SD) from one annual OEWS release to the next relative to it, mostly measurement noise."),
              'se_note': se_note,
              'noise': {'kappa2': round(nzf['k2'], 2), 'h': [round(float(x), 4) for x in nzf['h']], 'q': [round(float(x), 5) for x in nzf['q']],
                        'windows': '2021-23, 2021-24, 2021-25, 2023-24, 2023-25, 2024-25'},
              'wage_growth_alt_all_private': round(G_all, 4), 'eci_series': 'CIU2020000110000I', 'topcode': None,
              'source': ('BLS OEWS May 2025, SOC 11-1021 General and Operations Managers, national by industry (no top-code), '
                         'each cell shrunk toward its parent NAICS row by empirical Bayes using the published relative standard errors; '
                         'e-commerce bridged from the May 2021 NAICS 454100 row (eliminated in NAICS 2022); carried from May 2025 to June 2026 '
                         'by the ECI wages & salaries index for private-industry management, business and financial occupations. '
                         'Wages and salaries only (no benefits, payroll taxes or non-production bonuses).')}
    json.dump(gm_new, open(os.path.join(OUT, 'gm_wage_new.json'), 'w'), separators=(',', ':'))
    if '--write-repo' in sys.argv[1:]:
        json.dump(gm_new, open(REPO_JSON, 'w'), separators=(',', ':'))
        say(f'[out] --write-repo: wrote {REPO_JSON} (read by fit/build_models.py)')

    # ---- topcode effect -------------------------------------------------------------------
    tc = []
    for k in inds:
        for p in ('p75', 'p90'):
            if oldgm[k][p] == 208000.0:
                tc.append((k, p, by[k][p], oldgm[k][p] * math.exp(lnG2125['mbf_nsa'])))
    say('[topcode] old cells pinned at $208,000 (May 2021 top-code): May-2025 EB value vs 208k x ECI-MBF 2021->2025: ' +
        ', '.join(f'{k} {p} {a:,.0f} vs {b:,.0f}' for k, p, a, b in tc))

    # ---- firm-size rank sensitivity (Census SUSB) -------------------------------------------
    J = F['jobs']['by_industry']
    sk = susb_knots({J[k]['naics'] for k in inds if k in J})
    rank_rows = []
    for k in inds:
        if k not in J or J[k]['naics'] not in sk:
            continue
        kn = np.array(sk[J[k]['naics']])
        app_kn = np.array([[x[0], x[3]] for x in J[k]['knots']])
        assert len(app_kn) == len(kn) and np.allclose(app_kn[:, 0], kn[:, 0], atol=1e-3) and np.allclose(app_kn[:, 1], kn[:, 1], atol=1e-3), k
        # third bracket: one GM per establishment, but only in the largest establishments, as many as OEWS counts
        jc = J[k]['naics']
        oc = jc if ('-' in jc or len(jc) == 2) else jc.ljust(6, '0')
        oc = {'511200': '511200', '454100': '454100'}.get(oc, oc)
        src = i25 if oc in i25.index else i21
        n_gm = float(src.loc[oc, 'TOT_EMP']) if oc in src.index else float('nan')
        est = kn[:, 3]
        gm_band = np.zeros(len(est))
        left = n_gm
        for b in range(len(est) - 1, -1, -1):
            gm_band[b] = min(est[b], max(left, 0.0))
            left -= gm_band[b]
        cdf_top = (np.cumsum(gm_band) - gm_band / 2) / gm_band.sum() if gm_band.sum() > 0 else np.full(len(est), np.nan)
        for rev in (1e6, 6e6, 2e7):
            pe = float(np.interp(math.log(rev), kn[:, 0], kn[:, 1]))
            ps = float(np.interp(math.log(rev), kn[:, 0], kn[:, 2]))
            pt = float(np.interp(math.log(rev), kn[:, 0], cdf_top))
            rank_rows.append({'industry': k, 'rev': rev, 'oews_gm_emp': n_gm, 'oews_cell': oc, 'establishments': float(est.sum()),
                              'pct_top_establishments': pt, 'pct_employment': pe, 'pct_establishment': ps,
                              'gm_top_establishments': gm_salary_py(by[k], pt, G),
                              'gm_employment': gm_salary_py(by[k], pe, G), 'gm_establishment': gm_salary_py(by[k], ps, G)})
    rank = pd.DataFrame(rank_rows)
    rank.to_csv(os.path.join(OUT, 'rank_sensitivity.csv'), index=False)
    ex_r = rank[(rank.industry == 'medical') & (rank.rev == 6e6)].iloc[0]
    rr = rank.assign(ratio=rank.gm_establishment / rank.gm_employment)
    rr['ratio_top'] = rr.gm_top_establishments / rr.gm_employment
    say(f"[rank] example (medical, $6M; OEWS counts {ex_r.oews_gm_emp:,.0f} GMs in {ex_r.establishments:,.0f} establishments): rank / salary under "
        f"GMs-only-in-largest-establishments {ex_r.pct_top_establishments:.3f} ${ex_r.gm_top_establishments:,.0f} | employment CDF (app) {ex_r.pct_employment:.3f} ${ex_r.gm_employment:,.0f} | "
        f"one-GM-per-establishment {ex_r.pct_establishment:.3f} ${ex_r.gm_establishment:,.0f}")
    say(f"[rank] across industries at $1M/$6M/$20M vs the app's employment CDF: establishment-weighted median {np.median(rr.ratio)*100-100:+.0f}% "
        f"(range {rr.ratio.min()*100-100:+.0f}% to {rr.ratio.max()*100-100:+.0f}%); largest-establishments-only median {np.nanmedian(rr.ratio_top)*100-100:+.0f}% "
        f"(range {np.nanmin(rr.ratio_top)*100-100:+.0f}% to {np.nanmax(rr.ratio_top)*100-100:+.0f}%).")
    lowest = rr.pct_employment < rr[['pct_top_establishments', 'pct_establishment']].min(axis=1) - 1e-9
    rank_between = float(np.mean(~lowest))
    low_inds = sorted(rr[lowest].groupby('industry').size().loc[lambda x: x == 3].index)
    say(f"[rank] the app's employment weighting gives the LOWEST of the three ranks in {int(lowest.sum())} of {len(rr)} industry x size cases "
        f"(all three sizes: {', '.join(low_inds)}); it is never the highest.")
    assert not np.any(rr.pct_employment > rr[['pct_top_establishments', 'pct_establishment']].max(axis=1) + 1e-9)

    # ---- harness --------------------------------------------------------------------------
    hc = harness_compare(gm_sub, gm_new, EX)
    if 'old' in hc:
        say(f"[harness] example business gmSalary: old ${hc['old']['example_gm']:,.0f} -> new ${hc['new']['example_gm']:,.0f}; "
            f"nonmonotone industries old {hc['old']['nonmonotone']} new {hc['new']['nonmonotone']}")
        for k in inds:
            say(f"     {k:>7} old " + ' '.join(f'{v:>7,}' for v in hc['old']['grid'][k]) + ' | new ' + ' '.join(f'{v:>7,}' for v in hc['new']['grid'][k]))
        go, gn = hc['old']['example_gm_row'], hc['new']['example_gm_row']
        say('[harness] example "hire a GM" row old: ' + json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in go.items() if k != 'n'}))
        say('[harness] example "hire a GM" row new: ' + json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in gn.items() if k != 'n'}))
    else:
        say('[harness] ' + json.dumps(hc)[:500])
    json.dump(hc, open(os.path.join(OUT, 'harness_compare.json'), 'w'), indent=1, default=str)

    return dict(ret75=ret75, eci2125=eci2125, kpt=kpt, sensk=sensk, kh=kh, move_1y_ref=move_1y_ref, move_1y_obs=move_1y_obs, T25c=T25c, cvw=cvw, cv_gain=cv_gain, table_c=table_c, cdiff=cdiff, NZ=NZ, G_se_lag=G_se_lag, LAG=LAG, USE=USE, ecom_se=ecom_se,
                inputs=inputs, Y=Y, T25=T25, Tse=Tse, tau_df=tau_df, cvs=cvs, cv_all=cv_all, kc=kc, sv=sv, gv=gv, gsum=gsum,
                rms_mbf=rms_mbf, rms_all=rms_all, nono=nono, G=G, G_all=G_all, G_se=G_se, G_spec_sd=G_spec_sd, variants=variants,
                app=app, by=by, gm_new=gm_new, bpool=bpool, btab=btab, best=best, shp=shp, alt=alt, lb90=lb90, tc=tc, rank=rank,
                ex_r=ex_r, rr=rr, rank_between=rank_between, rank_lowest=int(lowest.sum()), rank_low_inds=low_inds, hc=hc, cell=cell, inds=inds, oldgm=oldgm, sens15=sens15, gm_sub=gm_sub, raw=raw,
                rms_mbf_x=rms_mbf_x, rms_all_x=rms_all_x, rms_used=rms_used, pct_df=pct_df, bunch=bunch, mc=mc, bdiff=bdiff, table=table)


# ----------------------------------------------------------------------------------------
# 8. RESULT.json
# ----------------------------------------------------------------------------------------
def fmt_d(x):
    return f'${x:,.0f}'


def build_result(R):
    by, app, G, inds, oldgm = R['by'], R['app'], R['G'], R['inds'], R['oldgm']
    sv = R['sv'].set_index(['kappa', 'a', 'b'])
    s25, s24, s2325, sadj = (sv.loc[(1.0, 2021, 2025)], sv.loc[(1.0, 2021, 2024)], sv.loc[(1.0, 2023, 2025)], sv.loc[(1.0, 2024, 2025)])
    tau = R['tau_df']
    cvs = R['cvs'].set_index('G')
    cvw = R['cvw'].set_index('hiw')
    cg = R['cv_gain']
    hc, ex_r = R['hc'], R['ex_r']
    nono = R['nono'].set_index(['a', 'b'])
    n21_24, n21_25 = nono.loc[(2021, 2024)], nono.loc[(2021, 2025)]
    gsum = R['gsum'].set_index(['a', 'b'])
    adj, g2325, g2324 = gsum.loc[(2024, 2025)], gsum.loc[(2023, 2025)], gsum.loc[(2023, 2024)]
    gv = R['gv'].set_index(['a', 'b', 'p'])
    bp = R['bpool'].set_index('method')
    pdf = R['pct_df'].set_index('p')
    bunch, mc, NZ = R['bunch'], R['mc'], R['NZ']
    nzf, nzse = NZ['full'], NZ['se']
    LAG = R['LAG']
    yrs = T_TARGET - MAY(2025)
    cv_z = [cvs.loc[g, 'mean_z2'] for g in cvs.index]
    gse_pct = [round(float(pdf.loc[p, 'growth_se']), 4) for p in PN]
    sf21 = float(pdf.loc['p10', 'shortfall_if_drift_continues_2021_25'])
    sf23 = float(pdf.loc['p10', 'shortfall_if_drift_continues_2023_25'])
    mc_rel = float((mc.se_formula / mc.se_mc - 1).abs().max())
    mc_old = (float((mc.se_old_formula_Btau / mc.se_mc_Btau - 1).min()), float((mc.se_old_formula_Btau / mc.se_mc_Btau - 1).max()))
    bmax_k = max(R['bdiff'], key=R['bdiff'].get)
    cmax_k = max(R['cdiff'], key=R['cdiff'].get)
    kmax_k = max(R['sensk'], key=R['sensk'].get)
    kpt = R['kpt']
    f2 = lambda xs, d=3: '/'.join(f'{x:.{d}f}' for x in xs)
    q_txt = 'below 0.0001' if max(nzf['q']) < 1e-4 else f2(nzf['q'], 5)
    lowo = NZ['lowo']
    cvq = NZ['cv_q']
    xref = [math.sqrt(x) for x in NZ['Xref']]
    nonb = app[app.industry != 'ecom']
    st50 = nonb.se_total_p50
    typ50 = float(np.median(st50))
    lo_k, hi_k = nonb.industry.iloc[int(np.argmin(st50))], nonb.industry.iloc[int(np.argmax(st50))]
    tau_txt = '; '.join(f"{g}: tau0 {h.tau0.min():.2f}-{h.tau0.max():.2f}, i.e. {h.tau_at_median_w.min():.2f}-{h.tau_at_median_w.max():.2f} at the median "
                        f"child share {h.median_w.iloc[0]:.2f} (constant-tau fit {h.tau_const.min():.2f}-{h.tau_const.max():.2f}; n={int(h.n_pairs.iloc[0])} pairs, "
                        f"SE of tau0^2 <= {h.tau0_2_se.max():.3f})" for g, h in tau.groupby('group'))
    brk = (f"May 2021 predates BLS's switch (with May 2022) from 12 interval-coded wage values to exact reported wages for private employers "
           f"(oes_ques.htm); the 2021 cells are visibly bunched ({bunch[2021]['distinct']:,} distinct values among {bunch[2021]['n']:,} cell-percentiles, "
           f"top-10 values cover {bunch[2021]['top10_share']*100:.1f}%, vs {bunch[2025]['distinct']:,} of {bunch[2025]['n']:,} and "
           f"{bunch[2025]['top10_share']*100:.1f}% in May 2025), so every 2021-based comparison crosses a measurement break")
    nz_val = (f"Leave-one-window-out (fit on five vintage pairs, score the sixth), mean z^2 model vs BLS-SE-only: " +
              '; '.join(f"{r.a}->{r.b} {r.z2_model:.2f} vs {r.z2_prse_only:.1f} (90% coverage {r.cover90_model:.2f} vs {r.cover90_prse_only:.2f})" for r in lowo.itertuples()) +
              ". 5-fold by sector, by MEAN_PRSE quartile (median PRSE): mean z^2 model / kappa-fixed-at-1 / BLS-SE-only " +
              '; '.join(f"{r.prse:.1f}%: {r.z2_model:.2f} / {r.z2_kappa1:.2f} / {r.z2_prse_only:.1f}" for r in cvq.itertuples()) +
              f" (coverage {NZ['cv_all']['cover90_model']:.2f} overall; the top quartile, which holds physicians' offices, is still under-dispersed by about "
              f"{(math.sqrt(cvq.z2_model.iloc[-1]) - 1) * 100:.0f}% in SD); log predictive density gain over kappa = 1 {NZ['lpd_vs_kappa1']['mean']:+.3f} "
              f"(SE {NZ['lpd_vs_kappa1']['se']:.3f}). The app cells' own 2024->2025 changes, scored with the model fitted without that window: mean z^2 "
              f"{NZ['app_z']['z2_model']:.2f} (BLS-SE-only {NZ['app_z']['z2_prse_only']:.2f}; |z|>2 {NZ['app_z']['share_absz_gt2_model']*100:.0f}% vs "
              f"{NZ['app_z']['share_absz_gt2_prse_only']*100:.0f}%, n={NZ['app_z']['n']}). Persistent drift is small: a pure random-walk model fitted on the exact-wage "
              f"windows over-predicts the 3-4-year 2021-based windows (mean z^2 there {NZ['rw_long']['z2_rw']:.2f}; full model {NZ['rw_long']['z2_full']:.2f}); "
              f"it would have given extra SDs {f2([math.sqrt(x) for x in NZ['rw_long']['X_rw_ref']])}.")
    val_eb = (f"Prior: tau0^2 (1-w)^2 (the parent row contains the child). 5-fold CV by parent: held-out mean z^2 {min(cv_z):.2f}-{max(cv_z):.2f}, 90% coverage "
              f"{R['cv_all']['cover90']:.2f}; by child share, w < 0.3: z^2 {cvw.loc['w<0.3','z2_scaled']:.2f} (constant tau {cvw.loc['w<0.3','z2_const']:.2f}), "
              f"w >= 0.3: {cvw.loc['w>=0.3','z2_scaled']:.2f} ({cvw.loc['w>=0.3','z2_const']:.2f}); log predictive density gain over constant tau "
              f"{cg['mean']:+.3f} per cell-percentile (parent-cluster bootstrap SE {cg['se']:.3f}, n={cg['n']}). Temporal checks (tau from the earlier vintage only, "
              f"level-neutral log errors), RMSE raw vs EB: May 2021 -> May 2025 {s25.rmse_raw:.3f} vs {s25.rmse_eb:.3f} (dMSE {s25.dMSE_eb_minus_raw:+.4f}, SE "
              f"{s25.dMSE_se:.4f}); 2021 -> 2024 {s24.rmse_raw:.3f} vs {s24.rmse_eb:.3f}; but {brk}. In the exact-wage windows the gain is not significant: "
              f"2023 -> 2025 {s2325.rmse_raw:.3f} vs {s2325.rmse_eb:.3f} (dMSE {s2325.dMSE_eb_minus_raw:+.5f}, SE {s2325.dMSE_se:.5f}); 2024 -> 2025 (2/3 panels "
              f"shared, which favours the raw cell) {sadj.rmse_raw:.3f} vs {sadj.rmse_eb:.3f}. Parent-only prediction is far worse ({s25.rmse_parent:.3f}; "
              f"{s2325.rmse_parent:.3f} for 2023 -> 2025), so full pooling is rejected. Scaled vs constant-tau prior out of time: dMSE 2021->2025 "
              f"{s25.dMSE_scaled_minus_const:+.5f} (SE {s25.dMSE_scaled_minus_const_se:.5f}), 2023->2025 {s2325.dMSE_scaled_minus_const:+.5f} "
              f"({s2325.dMSE_scaled_minus_const_se:.5f}), 2024->2025 {sadj.dMSE_scaled_minus_const:+.5f} ({sadj.dMSE_scaled_minus_const_se:.5f}): slightly worse "
              f"only across the 2022 break, neutral to better in the exact-wage windows. Posterior SE: closed form B s_c^2 + (1-B) s_P^2 (+ tau^2 uncertainty by "
              f"the delta method); Monte Carlo with each app cell's inputs (400k draws) matches it within {mc_rel*100:.1f}%.")
    params = []
    params.append({
        'param': 'MODELS.fitted.gm_wage.wage_growth (replaces wage_growth_2021_2026)',
        'current_value': '1.233 (May 2021 -> 2026; ECI private wages & salaries, 2026 assumed)',
        'fitted_value': (f"{G:.4f} (May 2025 -> 2026Q2/June 2026; ECI W&S, private, management/business/financial occupations, CIU2020000110000I, "
                         f"166.21 -> 171.91; all-private alternative {R['G_all']:.4f})"),
        'se': (f"{R['G_se']:.4f}: SE of the economy-wide factor only (specification SD {R['G_spec_sd']:.4f} over 8 variants: MBF/all-private x NSA/SA x "
               f"log/linear interpolation; plus the ECI's tracking RMS of average within-industry OEWS growth, {R['rms_used']*100:.2f} pp/yr x {yrs:.3f} yr, the "
               f"larger of the chained-window RMS {R['rms_mbf']*100:.2f} and the exact-wage-window RMS {R['rms_mbf_x']*100:.2f}); {R['G_se_lag']:.4f} if that "
               f"tracking error also ran over the panels' {LAG:.2f}-yr lag (BLS's aging factors should absorb broad-group movement, so not used). It is not "
               f"the SE of one industry's growth: a single cell moves about {R['move_1y_ref']*100:.1f}% (SD) a year relative to it (observed RMS "
               f"{R['move_1y_obs']*100:.1f}% for cells with PRSE <= 3%, 2024->2025), mostly noise, carried in by_industry[*].se_total. ECI's own sampling SE "
               f"is not in the downloaded files."),
        'n': (f"1 index series (quarterly, actual through 2026Q2); validated on {int(n21_25.cells)} matched OEWS cells (code and title unchanged) for the "
              f"2021-based windows and {int(g2325.cells)}-{int(g2324.cells)} for the 2023/2024-based windows, x 5 percentiles"),
        'method': ('ECI ratio, OEWS May reference interpolated log-linearly between March and June. The management/business/financial (MBF) series '
                   'is chosen on conceptual grounds (occupational match to SOC 11-1021); the validation does not discriminate it from the all-private series. '
                   'p75/p90 growth with top-code censoring (2021 at $208,000, 2023/2024 at $239,200) from a bivariate-normal censored model of the two '
                   "vintages' levels, so cells crossing a top-code in either direction are kept."),
        'validation': (f"Within-cell OEWS growth vs ECI-MBF, annualised bias, p25-p75 mean (p25/p50 only in brackets): 2021->2024 {n21_24.bias_mbf_pa*100:+.2f} "
                       f"({n21_24.bias_mbf_pa_p25p50*100:+.2f}) pp/yr, 2021->2025 {n21_25.bias_mbf_pa*100:+.2f} ({n21_25.bias_mbf_pa_p25p50*100:+.2f}); these cross the "
                       f"2022 interval->exact wage break. Exact-wage windows: 2023->2024 {g2324.bias_mbf_pa*100:+.2f} ({g2324.bias_mbf_pa_p25p50*100:+.2f}), 2024->2025 "
                       f"{adj.bias_mbf_pa*100:+.2f} ({adj.bias_mbf_pa_p25p50*100:+.2f}), 2023->2025 {g2325.bias_mbf_pa*100:+.2f} ({g2325.bias_mbf_pa_p25p50*100:+.2f}). "
                       f"All-private ECI: 2021-based {n21_24.bias_all_pa*100:+.2f}/{n21_25.bias_all_pa*100:+.2f}, exact-wage {g2324.bias_all_pa*100:+.2f}/"
                       f"{adj.bias_all_pa*100:+.2f}/{g2325.bias_all_pa*100:+.2f} pp/yr: MBF tracks better only across the break, so the two are treated as "
                       f"equivalent (factors {G:.4f} vs {R['G_all']:.4f}). Bias RMS: chained 2021-23/23-24/24-25 MBF {R['rms_mbf']*100:.2f} vs all-private "
                       f"{R['rms_all']*100:.2f}; exact-wage MBF {R['rms_mbf_x']*100:.2f} vs {R['rms_all_x']*100:.2f} pp/yr. Top-code treatment, 2023->2024 p90 mean "
                       f"growth: censored model {gv.loc[(2023,2024,'p90'),'mean_dlog']:.4f}, dropping censored cells (previous fit) "
                       f"{gv.loc[(2023,2024,'p90'),'mean_dlog_drop']:.4f}, end-censored at their lower bound {gv.loc[(2023,2024,'p90'),'mean_dlog_lb']:.4f}; "
                       f"p75 {gv.loc[(2023,2024,'p75'),'mean_dlog']:.4f} / {gv.loc[(2023,2024,'p75'),'mean_dlog_drop']:.4f} / {gv.loc[(2023,2024,'p75'),'mean_dlog_lb']:.4f}. "
                       f"Lower percentiles outgrew the index: p10 {pdf.loc['p10','bias_2021_2025_pa']*100:+.2f} pp/yr over 2021-25, "
                       f"{pdf.loc['p10','bias_2023_2025_pa']*100:+.2f} over 2023-25 (exact wages) and {pdf.loc['p10','bias_2024_2025']*100:+.2f} in 2024-25; p25 "
                       f"{pdf.loc['p25','bias_2021_2025_pa']*100:+.2f}/{pdf.loc['p25','bias_2023_2025_pa']*100:+.2f}/{pdf.loc['p25','bias_2024_2025']*100:+.2f}. "
                       f"Not extrapolated (a continuation would leave p10 {sf21*100:.1f}-{sf23*100:.1f}% low by June 2026, counting the panels' lag); carried in "
                       f"wage_growth_se_pct instead."),
        'recommended_value': f'{G:.4f}'})
    params.append({
        'param': 'MODELS.fitted.gm_wage.wage_growth_se / wage_growth_se_pct (new, documentation only; gmSalary does not read them)',
        'current_value': 'none',
        'fitted_value': f"wage_growth_se {R['G_se']:.4f} (economy-wide factor); wage_growth_se_pct [p10..p90] " + str(gse_pct),
        'se': 'n/a (these are SEs); each rests on 2-3 tracking windows, so treat as rough',
        'n': 'chained windows 2021-23, 2023-24, 2024-25 and exact-wage windows 2023-24, 2024-25',
        'method': (f"wage_growth_se_pct_p = sqrt(wage_growth_se^2 + (RMS_p x {LAG:.3f} yr x G)^2), RMS_p = the larger of the chained and exact-wage RMS of "
                   f"the percentile-specific annual bias (percentile bias vs ECI minus the window's p25-p75 average). The {LAG:.2f}-yr horizon is the mean time "
                   "from the six May-2025 panels (Nov 2022 - May 2025) to June 2026: BLS ages older panels by a broad-group factor that is the same for every "
                   "percentile (oes_ques.htm), so percentile-specific movement enters only through new panels."),
        'validation': '; '.join(f"{p}: specific RMS chained {pdf.loc[p,'rms_spec_chain_pa']*100:.2f} / exact {pdf.loc[p,'rms_spec_exact_pa']*100:.2f} pp/yr "
                                f"(total RMS {pdf.loc[p,'rms_chain_pa']*100:.2f} / {pdf.loc[p,'rms_exact_pa']*100:.2f})" for p in PN) +
                      ". p90 values rest on the censored model (about half of p90 cells top-coded in 2021/2023/2024).",
        'recommended_value': json.dumps(gse_pct)})
    clamp_note = {}
    revs = ['$0.3M', '$1M', '$3M', '$6M', '$20M', '$100M']
    if 'new' in hc:
        for k in inds:
            at = [revs[j] for j, v in enumerate(hc['new']['grid'][k]) if abs(v - by[k]['p10'] * R['gm_new']['wage_growth']) <= 1.0]
            if at:
                clamp_note[k] = at[-1]
    alt = R['alt']
    for k in inds:
        r = app[app.industry == k].iloc[0]
        o = oldgm[k]
        newv = by[k]
        tot_txt = 'se_total ' + f2(newv['se_total'])
        if k == 'ecom':
            meth = (f"Labelled bridge (NAICS 2022 has no e-commerce row): mean (in logs) of two bridges from the May-2021 NAICS 454100 percentiles: relative to Retail "
                    f"44-45 (May 2021 ratio applied to Retail May 2025) and carried by the ECI-MBF May 2021 -> May 2025; p90 from a shape model fitted on May-2025 "
                    f"cells (CV RMSE {R['shp']['cv_rmse']:.3f}). The candidates are statistically tied, so the two conceptually distinct ones are averaged rather than "
                    "the lowest-RMSE one picked.")
            val = (f"Bridge methods scored on {int(bp.loc['combo','n'])} cell-percentiles with unchanged code and title 2021->2025 (p10-p75 pooled): mean bridge "
                   f"RMSE {bp.loc['combo','rmse']:.3f} (SE {bp.loc['combo','rmse_se']:.3f}), sector {bp.loc['sector','rmse']:.3f}, own x ECI-MBF "
                   f"{bp.loc['own_eci_mbf','rmse']:.3f}, own x ECI-all {bp.loc['own_eci_all','rmse']:.3f}, cross-industry {bp.loc['us','rmse']:.3f} (this scoring "
                   f"crosses the 2022 wage-processing break, which inflates every method's RMSE). All methods p10..p90: {alt}; p75 spans "
                   f"{min(v[3] for v in alt.values()):,.0f}-{max(v[3] for v in alt.values()):,.0f} and p90 {min(v[4] for v in alt.values()):,.0f}-"
                   f"{max(v[4] for v in alt.values()):,.0f} (Retail's own p75 rose only {R['ret75']*100:.0f}% from May 2021 to May 2025 against {R['eci2125']*100:.0f}% for the ECI-MBF, which holds the sector bridge down). Bridged p90 "
                   f"{newv['p90']:,.0f} >= {math.exp(R['lb90']):,.0f}, the floor implied by the 2021 top-code.")
            nn = f"May 2021 454100: {r.emp_2025:,.0f} GMs, PRSE {r.mean_prse:.1f}%"
            se_txt = ('se_sampling p10..p90 ' + f2(newv['se_sampling']) + " (the mean bridge's out-of-sample RMSE per percentile; p90 adds the shape model); "
                      + tot_txt + ' for the June-2026 value (adds the percentile growth SE)')
        else:
            meth = (f"EB shrink of each log percentile of OEWS {r.cell_2025} ({r.title}) toward parent {r.parent} ({r.parent_title}), child share w "
                    f"{R['table'][k]['w']:.2f}, prior variance tau0^2 (1-w)^2; B = " + f2([getattr(r, 'B_' + p) for p in PN], 2) +
                    f"; constant-tau prior would give " + '/'.join(f"{getattr(r,'postconst_'+p):,.0f}" for p in PN) +
                    f" (max change {R['cdiff'][k]*100:.1f}%); the MSE-optimal B* would move these by at most {R['bdiff'][k]*100:.1f}%")
            val = val_eb if k == 'home' else 'See the home entry (EB validation, shared) and the se_total entry (noise model).'
            nn = f"{r.emp_2025:,.0f} GMs (TOT_EMP), MEAN_PRSE {r.mean_prse:.1f}%"
            se_txt = ('se_sampling p10..p90 ' + f2(newv['se_sampling']) + ' (posterior, BLS PRSE at kappa 1; raw cell ' +
                      f2([getattr(r, 'se_raw_' + p) for p in PN]) + '); ' + tot_txt + ' for the June-2026 value (adds extra noise SD ' +
                      f2([getattr(r, 'extra_sd_' + p) for p in PN]) + ' and the percentile growth SE ' + f2(gse_pct) + ')')
        if k in clamp_note:
            val += f" Small firms read p10 here (gmSalary sits at the p10 clamp up to {clamp_note[k]} revenue), where se_total is {newv['se_total'][0]:.3f}."
        params.append({
            'param': f'MODELS.fitted.gm_wage.by_industry.{k}',
            'current_value': f"naics {o['naics']} May 2021: " + '/'.join(f"{o[p]:,.0f}" for p in PN) + ' (x1.233 = ' + '/'.join(f"{o[p]*1.233:,.0f}" for p in PN) + ' in 2026 $)',
            'fitted_value': f"May 2025: " + '/'.join(f"{newv[p]:,.0f}" for p in PN) + f' (raw ' + '/'.join(f"{getattr(r,'raw_'+p):,.0f}" for p in PN) +
                            f'); x{G:.4f} = ' + '/'.join(f"{newv[p]*G:,.0f}" for p in PN) + ' in June-2026 $',
            'se': se_txt, 'n': nn, 'method': meth, 'validation': val,
            'recommended_value': json.dumps(newv, separators=(',', ':'))})
    params.append({
        'param': 'MODELS.fitted.gm_wage.by_industry[*].se_total and gm_wage.noise (new, documentation only): noise the published SEs miss',
        'current_value': 'none (the previous fit embedded only the sampling SE, as se)',
        'fitted_value': (f"kappa^2 {nzf['k2']:.2f}, transient panel noise h p10..p90 {f2(nzf['h'], 4)}, random-walk drift q {q_txt} per yr, May-2021 "
                         f"interval noise {nzf['r21']:.4f}; extra SD of a June-2026 value for a cell with MEAN_PRSE 2%: {f2(xref)}; se_total across the 15 cells "
                         f"at p50 {st50.min():.3f} ({lo_k}) to {st50.max():.3f} ({hi_k}), median {typ50:.3f}"),
        'se': (f"sector-cluster bootstrap: kappa^2 {nzse['k2']:.2f}; h {f2(nzse['h'], 4)}; extra SD (PRSE 2%) 90% interval " +
               '/'.join(f'{lo:.3f}-{hi:.3f}' for lo, hi in zip(nzse['sd_ref_lo'], nzse['sd_ref_hi']))),
        'n': f"{len(NZ['R'])} level-neutral cell-percentile changes over 6 vintage pairs (2021-23, 2021-24, 2021-25, 2023-24, 2023-25, 2024-25), LEVEL >= 3, code and title unchanged",
        'method': ("Var(within-cell change minus the window's mean change) = kappa^2 V + h c_h + q c_q + r21 [2021 window], V = the BLS-SE-implied variance "
                   "(Cov = shared-panel share x s_a s_b), c_h and c_q from the six-panel/three-year design (panel dates per oes_ques.htm: transient panel-level noise "
                   "and random-walk drift), fitted by Gaussian quasi-likelihood (consistent for the variance function whatever the tails). Extra variance of a "
                   f"cell's June-2026 value = (kappa^2-1) s_raw^2 + h/6 + {NZ['cT']:.3f} q (B = 1, conservative); se_total = sqrt(se_sampling^2 + extra + "
                   "wage_growth_se_pct^2); e-commerce: sqrt(bridge RMSE^2 + 1.083 q + wage_growth_se_pct^2) (its RMSE is scored against noisy 2025 cells)."),
        'validation': nz_val + (f" Sensitivities for the PRSE-2% cell: exact-wage windows only {f2([math.sqrt(x) for x in NZ['Xref_exact']])} (kappa^2 "
                                f"{NZ['exact']['k2']:.2f}); kappa fixed at 1 {f2([math.sqrt(x) for x in NZ['Xref_k1']])}. Descriptive excess dispersion (mean r^2 - mean V), "
                                "2024->2025 p10..p90 " + f2(NZ['exw'].loc[(2024, 2025)].to_numpy(), 4) + ', 2023->2025 ' + f2(NZ['exw'].loc[(2023, 2025)].to_numpy(), 4) + '.'),
        'recommended_value': 'embed se_total per industry (see by_industry entries) and gm_wage.noise = ' + json.dumps(R['gm_new']['noise'], separators=(',', ':'))})
    s2 = lambda a, b, k: sv.loc[(k, a, b)]
    params.append({
        'param': 'EB hyperparameters tau0 (prior SD of the child-parent log gap = tau0 (1-w))',
        'current_value': 'none (no shrinkage; raw May-2021 cells). Previous fit: constant tau',
        'fitted_value': tau_txt,
        'se': 'parent-cluster bootstrap SE of tau0^2, see tau.csv; posterior SEs carry it by the delta method',
        'n': f"{int(tau.groupby('group').n_pairs.first().sum())} child/parent pairs in May 2025 ({cg['parents']} parents in the CV)",
        'method': ('Paule-Mandel per parent level x percentile on d_i ~ N(0, (1-w_i)^2 tau0^2 + v_i); prior mean = parent row; v = s_c^2 + s_P^2 - 2 w s_c^2 '
                   '(child is part of parent), with s_P raised to w s_c where the published SEs fall below that'),
        'validation': (f"5-fold CV by parent, scaled vs constant prior: mean z^2 by group " +
                       ', '.join(f"{g} {cvs.loc[g,'mean_z2']:.2f} vs {cvs.loc[g,'mean_z2_const']:.2f}" for g in cvs.index) +
                       f"; w < 0.3 {cvw.loc['w<0.3','z2_scaled']:.2f} vs {cvw.loc['w<0.3','z2_const']:.2f}, w >= 0.3 {cvw.loc['w>=0.3','z2_scaled']:.2f} vs "
                       f"{cvw.loc['w>=0.3','z2_const']:.2f}; lpd gain {cg['mean']:+.3f} (SE {cg['se']:.3f}). App cells move by at most {R['cdiff'][cmax_k]*100:.1f}% "
                       f"({cmax_k}, w {R['table'][cmax_k]['w']:.2f}) relative to the constant-tau prior."),
        'recommended_value': 'used offline only (not embedded)'})
    params.append({
        'param': 'EB shrinkage factor B (tau^2/(tau^2+v) vs the MSE-optimal B* = (tau^2 + s_P^2 - w s_c^2)/(tau^2 + v))',
        'current_value': 'n/a', 'fitted_value': 'B = tau^2/(tau^2+v) kept',
        'se': 'n/a',
        'n': f"{int(s25.n)}-{int(sadj.n)} cell-percentiles per temporal window",
        'method': ("B* minimises MSE when the child's sample is part of the parent's (Cov = w s_c^2); confirmed by Monte Carlo on the app cells "
                   f"(simulated MSE-optimal B within {np.max(np.abs(mc.B_star - mc.B_mc_opt)):.3f} of B*, vs up to {np.max(np.abs(mc.B_tau - mc.B_mc_opt)):.3f} for B)."),
        'validation': (f"Out of sample at kappa 1, dMSE(B* - B) 2021->2025 {s25.dMSE_Bstar_minus_Btau:+.6f} (SE {s25.dMSE_Bstar_minus_Btau_se:.6f}), "
                       f"2021->2024 {s24.dMSE_Bstar_minus_Btau:+.6f} ({s24.dMSE_Bstar_minus_Btau_se:.6f}), 2023->2025 {s2325.dMSE_Bstar_minus_Btau:+.6f} "
                       f"({s2325.dMSE_Bstar_minus_Btau_se:.6f}), 2024->2025 {sadj.dMSE_Bstar_minus_Btau:+.6f} ({sadj.dMSE_Bstar_minus_Btau_se:.6f}); at kappa 2, "
                       f"{s2(2021,2025,2.0).dMSE_Bstar_minus_Btau:+.6f}. No consistent gain; app cells differ by at most {R['bdiff'][bmax_k]*100:.1f}% ({bmax_k}). Kept B; "
                       "the posterior SE is the exact MSE of the estimator actually used."),
        'recommended_value': 'B = tau^2/(tau^2+v) (no change to embedded values from this choice)'})
    params.append({
        'param': 'measurement-SE scale kappa (log-percentile SE = kappa x MEAN_PRSE x k_p(sigma))',
        'current_value': 'n/a', 'fitted_value': f"EB point values: 1 (kept); se_total: kappa^2 = {nzf['k2']:.2f} from the noise model",
        'se': f"kappa^2 {nzf['k2']:.2f} (sector-cluster bootstrap SE {nzse['k2']:.2f}); exact-wage windows only {NZ['exact']['k2']:.2f}",
        'n': f"{len(NZ['R'])} cell-percentile changes",
        'method': 'quasi-likelihood variance-component model (see the se_total entry); the earlier OLS regressions of squared changes on V (0.93 and 1.43) are dominated by the noisiest cells',
        'validation': (f"Paired out-of-time test of the point values, EB with kappa {R['kh']:.2f} minus kappa 1 (dMSE of level-neutral log errors): " +
                       '; '.join(f"{r.a}->{r.b} {r.dMSE:+.5f} (SE {r.dMSE_se:.5f})" for r in kpt.itertuples()) +
                       ". Better across the 2022 break (where 2021's interval noise favours shrinkage), not significantly better 2023->2025, worse 2024->2025 "
                       "(shared panels favour the raw cell there); so the exact-wage evidence does not decide it. EB RMSE at kappa 1 / 1.5 / 2: 2023->2025 "
                       f"{s2325.rmse_eb:.4f} / {s2(2023,2025,1.5).rmse_eb:.4f} / {s2(2023,2025,2.0).rmse_eb:.4f}; 2024->2025 {sadj.rmse_eb:.4f} / "
                       f"{s2(2024,2025,1.5).rmse_eb:.4f} / {s2(2024,2025,2.0).rmse_eb:.4f}. With the fitted kappa the app cells would move by at most "
                       f"{R['sensk'][kmax_k]*100:.1f}% ({kmax_k}; " + ', '.join(f'{k} {v*100:.1f}%' for k, v in sorted(R['sensk'].items(), key=lambda kv: -kv[1])[1:3]) +
                       "), inside their se_total. Kept kappa = 1 for the point values (labelled; switching is defensible) and used the fitted kappa for se_total."),
        'recommended_value': '1 for the shrinkage; fitted value documented in gm_wage.noise'})
    params.append({
        'param': 'MODELS.fitted.gm_wage.topcode', 'current_value': '208000 (May 2021 top-code; p75/p90 pinned for medical, msp, prof, dist, staff, ecom, saas)',
        'fitted_value': 'null (May 2025 publishes all percentiles)', 'se': 'n/a', 'n': '0 top-coded cells in May 2025 (159 in 2023, 174 in 2024, 199 in 2021)',
        'method': 'BLS stopped top-coding with May 2025 estimates (oes_ques.htm)',
        'validation': 'formerly pinned cells now: ' + ', '.join(f"{k} {p} {a:,.0f} (vs 208k x ECI {b:,.0f})" for k, p, a, b in R['tc']),
        'recommended_value': 'null'})
    params.append({
        'param': 'gmSalary firm-size rank (Census SUSB employment-weighted CDF by receipts size)',
        'current_value': 'employment CDF, clamped to p10-p90', 'fitted_value': 'kept (not identified)',
        'se': 'n/a',
        'n': 'SUSB 2022 receipts-size bands; OEWS GM counts',
        'method': 'bracketed by two alternative weightings of GM jobs across firms',
        'validation': (f"Example (medical, $6M): largest-establishments-only rank {ex_r.pct_top_establishments:.2f} -> {fmt_d(ex_r.gm_top_establishments)}; "
                       f"employment CDF {ex_r.pct_employment:.2f} -> {fmt_d(ex_r.gm_employment)}; one-GM-per-establishment {ex_r.pct_establishment:.2f} -> "
                       f"{fmt_d(ex_r.gm_establishment)}. Across 16 industries x $1M/$6M/$20M the employment weighting is the lowest of the three ranks in "
                       f"{R['rank_lowest']} of {len(R['rr'])} cases and never the highest (always lowest for {', '.join(R['rank_low_inds'])}): in industries "
                       "where a few very large firms hold most employment it probably understates a mid-size firm's GM pay. No data here measures GM pay by firm size."),
        'recommended_value': 'keep; label as judgment'})

    G_txt = f'{(G-1)*100:.1f}%'
    if 'old' in hc:
        ch = np.array([[n / o - 1 for o, n in zip(hc['old']['grid'][k], hc['new']['grid'][k])] for k in inds])
        go, gn = hc['old']['example_gm_row'], hc['new']['example_gm_row']
        flat = sorted(((ch[i, j], inds[i], revs[j]) for i in range(len(inds)) for j in range(len(revs))), key=lambda t: t[0])
        seen, downs_l, ups_l = set(), [], []
        for v, k, rv in flat:
            if k not in seen and len(downs_l) < 3:
                downs_l.append(f'{k} at {rv} {v*100:+.0f}%'); seen.add(k)
        seen = set()
        for v, k, rv in reversed(flat):
            if k not in seen and len(ups_l) < 3:
                ups_l.append(f'{k} at {rv} {v*100:+.0f}%'); seen.add(k)
        impact = (f"Impact (model harness, current index.html with only edits 1-2): gmSalary over 16 industries x revenue 0.3/1/3/6/20/100 $M changes by a median "
                  f"{np.median(np.abs(ch))*100:.1f}% (range {ch.min()*100:+.0f}% to {ch.max()*100:+.0f}%; largest rises {', '.join(ups_l)}; largest falls "
                  f"{', '.join(downs_l)}); non-monotone in revenue: old {hc['old']['nonmonotone'] or 'none'}, new {hc['new']['nonmonotone'] or 'none'}. Example "
                  f"business (medical, $6M): gmSalary {fmt_d(hc['old']['example_gm'])} -> {fmt_d(hc['new']['example_gm'])}; 'hire a GM' row: cost {fmt_d(go['c'])} -> "
                  f"{fmt_d(gn['c'])}, dV {fmt_d(go['dV'])} -> {fmt_d(gn['dV'])}, expected-proceeds gain {fmt_d(go['dE'])} -> {fmt_d(gn['dE'])}, net {fmt_d(go['net'])} -> "
                  f"{fmt_d(gn['net'])}. The p10 clamp binds (small firms read p10) for: " + ', '.join(f'{k} up to {v}' for k, v in clamp_note.items()) + '.')
    else:
        impact = 'Impact: harness not run.'
    gm_json = json.dumps(R['gm_new'], separators=(',', ':'))
    mv = {r.industry: max(abs(getattr(r, 'post_' + p) / getattr(r, 'raw_' + p) - 1) for p in PN) for r in nonb.itertuples()}
    big = [k for k, v in sorted(mv.items(), key=lambda kv: -kv[1]) if v > .01]
    namemap = {'medical': 'physicians&rsquo; offices', 'vet': 'veterinary', 'prof': 'accounting', 'msp': 'IT services', 'saas': 'software',
               'dist': 'wholesale', 'land': 'landscaping', 'fit': 'fitness', 'staff': 'staffing'}
    big_txt = ', '.join(namemap.get(k, k) for k in big[:-1]) + (' and ' if len(big) > 1 else '') + namemap.get(big[-1], big[-1]) if big else ''
    ecse = by['ecom']['se_sampling'][2]
    c75 = by['ecom']['p75']
    lo75, hi75 = min(v[3] for v in alt.values()) / c75 - 1, max(v[3] for v in alt.values()) / c75 - 1
    lo_b, hi_b = round(ex_r.gm_top_establishments, -3), round(ex_r.gm_establishment, -3)
    data_tab = (
        f"BLS OEWS May 2025 (SOC 11-1021, national by industry, no top-code; {len(nonb)} industry cells of {nonb.emp_2025.min():,.0f}&ndash;{nonb.emp_2025.max():,.0f} GMs), "
        f"each percentile shrunk toward its parent industry by empirical Bayes on BLS&rsquo;s published standard errors (most move under 1%; "
        f"{big_txt} up to {max(mv.values())*100:.0f}%); e-commerce, which NAICS 2022 abolished, is a judgment bridge from the May 2021 e-commerce row "
        f"(mean of a Retail-relative and an ECI-carried bridge, SE ~{ecse*100:.0f}%; other bridges put its 75th percentile {lo75*100:+.0f}% to {hi75*100:+.0f}%). "
        f"Carried to June 2026 by the ECI for private management, business and financial wages (+{G_txt}; the all-private ECI gives "
        f"+{(R['G_all']-1)*100:.1f}%). That factor&rsquo;s SE of {R['G_se']*100:.1f} pts is for the economy-wide trend only: one industry&rsquo;s published figure "
        f"moves about {R['move_1y_ref']*100:.0f}% a year relative to it, mostly survey noise beyond BLS&rsquo;s published errors, so a typical industry&rsquo;s "
        f"median here is uncertain by about {typ50*100:.0f}% ({st50.min()*100:.0f}% for {namemap.get(lo_k, lo_k)} to {st50.max()*100:.0f}% for {namemap.get(hi_k, hi_k)}). The smallest "
        f"firms read the 10th percentile, which has outgrown the index by {pdf.loc['p10','bias_2021_2025_pa']*100:.1f}&ndash;{pdf.loc['p10','bias_2023_2025_pa']*100:.1f} "
        f"pt/yr since 2021; as the May 2025 figures average surveys back to November 2022, their GM cost may be {sf21*100:.0f}&ndash;{sf23*100:.0f}% low "
        f"(SE ~{gse_pct[0]*100:.0f} pts). Wages only: a buyer&rsquo;s all-in cost including payroll taxes, benefits and bonuses is higher and is not modelled. "
        f"Census employment by firm size; ranking bigger firms&rsquo; GMs higher is a judgment (for a $6M physicians&rsquo; practice, other plausible rankings "
        f"give {fmt_d(lo_b)} to {fmt_d(hi_b)} instead of {fmt_d(round(ex_r.gm_employment, -3))}).")
    impl = (
        "1) index.html MODELS.fitted (line ~2032): replace the whole \"gm_wage\":{...} object with the contents of "
        "/tmp/claude-0/fit5/oews_refresh/gm_wage_new.json, i.e. \"gm_wage\":" + gm_json + "\n"
        "2) gmSalary() (line ~3029): `return w*F.gm_wage.wage_growth_2021_2026;` -> `return w*F.gm_wage.wage_growth;` "
        "(firm-size rank, clamp to [.1,.9] and the dollar-linear interpolation between p10/p25/p50/p75/p90 are unchanged; no fallback to the old "
        "field, so a stale table fails test 19 loudly instead of silently using 1.233). In the comment above it change 'carried to 2026 by wage growth' "
        "to 'carried to June 2026 by the ECI for management wages; wages and salaries only, so a buyer's all-in cost (payroll taxes, benefits) is higher'.\n"
        "3) tests/model.test.js line 176: `w=F.gm_wage.wage_growth_2021_2026` -> `w=F.gm_wage.wage_growth`; add the invariants below.\n"
        "4) Data tab row 'General manager salary' (line ~4540-4542): Now cell -> 'the industry&rsquo;s BLS wage distribution (wages only), read at this firm&rsquo;s "
        "size rank, p10&ndash;p90, June 2026 dollars'; Data cell -> data_tab_text (already HTML-escaped). In the note under the ledger (line ~4595) delete "
        "'<code>download.bls.gov</code> (OEWS 2024 wages),' since OEWS May 2021-2025 are now in hand.\n"
        "5) fit/build_models.py (so a rebuild cannot restore the 2021 table): delete line 21 (`oews=json.load(open('oews.json'))`) and line 22 (`gm={...}`), "
        "and replace the `'gm_wage':{'by_industry':gm,'wage_growth_2021_2026':1.233,...},` entry of `out` with `'gm_wage':json.load(open('gm_wage.json')),` "
        "(relative path, like the script's other inputs). Create that file with `python3 -I fit/oews_refresh.py --write-repo`, which writes fit/gm_wage.json "
        "(byte-identical to /tmp/claude-0/fit5/oews_refresh/gm_wage_new.json), and commit it; oews.py is superseded.\n"
        "6) fit/README.md line 13 (gm_wage row) -> `| `gm_wage` (general-manager wage percentiles) | `oews_refresh.py` (with `--write-repo` it writes "
        "`gm_wage.json`, which `build_models.py` reads) | BLS OEWS May 2021, 2023, 2024, 2025, SOC 11-1021, national by industry; BLS ECI ci.data.0.Current | "
        "`curl -A 'your-project/1.0 (contact)' -H 'Accept: */*' -H 'Accept-Language: en-US' -H 'Accept-Encoding: gzip, deflate, br' -O "
        "https://www.bls.gov/oes/special-requests/oesm25in4.zip` (likewise oesm21/23/24in4.zip and oesm2Xnat.zip; BLS answers 403 without a descriptive "
        "User-Agent and these headers) |`, and under the table add: 'The app's old May-2021 table came from cran/oews2021, a third-party CRAN repackaging "
        f"(Sep 2022). oews_refresh.py reads the official BLS oesm21in4.zip (sha256 {R['inputs'].get(ZIP21[0], '')[:16]}...) and checks the mirror against it: "
        f"identical on all {LOG21.get('matched_mirror', 0)} rows.' AUDIT.md line 426 -> '| GM salary = 2.4% of revenue | BLS industry wage distribution "
        "(wages only) read at the firm's size rank, p10–p90, June 2026 $ | OEWS May 2025 (EB-shrunk to parent NAICS) × ECI management W&S to 2026Q2; Census "
        "employment by size |'. Log as a follow-up fit: an ECEC-based employer-cost loading (benefits and payroll taxes by occupation group and "
        "establishment size) for the hire-a-GM cost.\n" + impact)
    inv = [
        'For every key of IND, MODELS.fitted.gm_wage.by_industry[k] exists with numeric p10<p25<p50<p75<p90 (strictly increasing) and 25000 < p10, p90 < 500000.',
        "MODELS.fitted.gm_wage.base === 'OEWS May 2025'; wage_growth is a number in [1.00, 1.08]; wage_growth_2021_2026 is undefined; topcode is null.",
        'Each by_industry entry has se_sampling and se_total, arrays of 5 numbers with 0 < se_sampling[i] <= se_total[i] <= 0.35, and no key named se; for every non-ecom entry se_sampling[i] >= 0.005 and se_total[i] >= 0.03.',
        'gm_wage.wage_growth_se is in (0, 0.03]; gm_wage.wage_growth_se_pct is an array of 5 numbers, each in [wage_growth_se, 0.08], with se_pct[0] (p10) the largest.',
        'gm_wage.noise.kappa2 is in [1, 6]; gm_wage.se_note and gm_wage.wage_growth_se_note are non-empty strings; gm_wage.source mentions that the figures are wages only.',
        'No by_industry percentile equals the old top-code 208000 (the May-2025 table has no censored cells).',
        'gmSalary({ind:k,rev}) lies within [p10*wage_growth, p90*wage_growth] (+/-1) for rev in {3e5,5e6,2e8} and every k (existing test 19, with the renamed field).',
        'gmSalary is finite and non-decreasing in revenue for every industry (1e5..1e9).',
        'gmSalary of the example medical business (rev 6e6) is between 80000 and 100000 (was 94,076; new ~' + (f"{hc['new']['example_gm']:,.0f}" if 'new' in hc else 'n/a') + ').',
        'saas uses naics 513200; ecom naics is 44-45 with a bridge note naming its p75/p90 range; all other industries keep their May-2021 naics codes.',
        'The GM intervention still deducts exactly gmSalary(s) from ern (existing test 7/line 102).']
    cav = (
        "Revision 2 after review. (R1, major: uncertainty understated) by_industry[*].se is renamed se_sampling (BLS sampling error after shrinkage, kappa 1) "
        f"and se_total is added for the June-2026 value, from a variance-component model of within-cell changes across six OEWS vintage pairs that uses the "
        f"six-panel design: kappa^2 {nzf['k2']:.2f} (SE {nzse['k2']:.2f}) plus transient panel-level noise, essentially no persistent drift. Extra SD for a "
        f"PRSE-2% cell {f2(xref)} (R1 suggested 0.09/0.05/0.05/0.05/0.05); se_total at p50 runs {st50.min():.3f}-{st50.max():.3f}. Leave-one-window-out and "
        "sector-fold z^2 are near 1 where the BLS-SE-only z^2 is 4-14. "
        f"The Data tab now says the {R['G_se']*100:.1f}-pt SE is for the economy-wide trend and that one "
        f"industry moves about {R['move_1y_ref']*100:.0f}% a year. Where I differ from R1: the excess is not mainly drift. R1's OLS of squared changes on V is "
        "dominated by the noisiest cells. The quasi-likelihood fit puts much of the excess in a PRSE multiple, and a kappa-fixed-at-1 model is miscalibrated "
        f"across cell size (sector-fold z^2 {cvq.z2_kappa1.iloc[0]:.2f} in the lowest PRSE quartile to {cvq.z2_kappa1.iloc[-1]:.2f} in the highest, vs "
        f"{cvq.z2_model.min():.2f}-{cvq.z2_model.max():.2f}). R1's three-vintage average moves (msp p10 +10%, medical p50 +10%, saas p10 -9%) are about one se_total "
        f"(0.09-0.13). The point-value method is unchanged, as both reviewers advised; values move only through the minor fixes below (scaled prior <= "
        f"{R['cdiff'][cmax_k]*100:.1f}%; e-commerce p75 {by['ecom']['p75']/alt['sector'][3]*100-100:+.1f}% and p90 {by['ecom']['p90']/alt['sector'][4]*100-100:+.1f}% "
        "from the bridge average). "
        f"(R1, minor: constant tau) adopted tau0^2 (1-w)^2. CV lpd {cg['mean']:+.3f} (SE {cg['se']:.3f}). Out of time it is slightly worse only across the 2022 "
        f"break. App cells move <= {R['cdiff'][cmax_k]*100:.1f}% ({cmax_k}). "
        "(R1, minor: end-vintage censoring) both start- and end-censored cells are now kept, through a bivariate-normal censored model of the two vintages' "
        "levels. Setting end-censored cells to their lower bound (R1's check) ignores that a cell crosses a top-code partly through its own noise. The "
        f"censored model gives 2023->24 p90 growth {gv.loc[(2023,2024,'p90'),'mean_dlog']:.4f} vs {gv.loc[(2023,2024,'p90'),'mean_dlog_drop']:.4f} dropped. "
        f"p75/p90 exact-wage RMS is now {pdf.loc['p75','rms_exact_pa']*100:.2f}/{pdf.loc['p90','rms_exact_pa']*100:.2f} pp/yr, as R1 predicted. "
        f"(R1 minor p10 wording; R2 minor horizon) p10 drift is quoted as {pdf.loc['p10','bias_2021_2025_pa']*100:.1f}-{pdf.loc['p10','bias_2023_2025_pa']*100:.1f} "
        f"pt/yr, and the {LAG:.2f}-yr panel lag is applied to percentile-specific drift (wage_growth_se_pct p10 {gse_pct[0]:.3f}; shortfall if it continued "
        f"{sf21*100:.1f}-{sf23*100:.1f}%). R2's random-walk horizon scaling for cell-level drift is not adopted: a pure random walk over-predicts the 3-4-year "
        f"windows (z^2 {NZ['rw_long']['z2_rw']:.2f}), and the fitted drift q is ~0. The total SE embedded is nonetheless of R2's order (~0.07 at p50 for "
        "mid-size cells). "
        f"(R1 minor: e-commerce) mean of the sector and own-x-ECI bridges; p75/p90 ranges stated. (R1 minor: build path) build_models.py reads fit/gm_wage.json, "
        f"written by --write-repo. The May-2021 vintage now comes from the official BLS oesm21in4/oesm21nat zips, and the CRAN mirror is identical on all "
        f"{LOG21.get('matched_mirror', 0)} rows. (R2 minor: base wages) the Data tab, source string and gmSalary comment say wages only; an ECEC loading is "
        "logged as a follow-up. "
        "Standing caveats: OEWS covers wage-and-salary GMs only (owner-managers and self-employed are excluded). It records straight-time wages including "
        "incentive pay, but not non-production bonuses, overtime or benefits. In physicians' offices the practice manager is often coded 11-9111 (Medical "
        "and Health Services Managers), not 11-1021. "
        f"{brk[0].upper() + brk[1:]}. se_total treats the cell's extra noise with B = 1 (conservative) and still runs about "
        f"{(math.sqrt(cvq.z2_model.iloc[-1]) - 1) * 100:.0f}% low in SD for the noisiest quartile of cells (physicians' offices). "
        "The firm-size rank is not identified by any data here. Two other plausible ways of weighting GM jobs across firms rank a $1M-$20M firm above the "
        f"app's employment weighting in every case for {', '.join(R['rank_low_inds'])}. There the app probably understates a mid-size firm's GM pay. Keep "
        "the rule, labelled as judgment. No online-marketplace or foreign data were used, so no analog-transfer shrinkage applies; the OEWS cells are the "
        "US population itself.")
    not_id = [
        'Firm-size rank of a business within the OEWS GM wage distribution: OEWS publishes no wages by firm or establishment size, and GM jobs per firm by size are not observed. Keep the Census employment-CDF rule as labelled judgment; bracket shown in validation.',
        'Rank correlation between firm size and GM pay (the rule assumes it is perfect, which spreads salaries to the p10/p90 clamps): not identified.',
        'E-commerce GM wages under NAICS 2022: no OEWS row exists. The bridge is a labelled judgment; its premise, that the 2021 e-commerce relationship persisted, cannot be tested for this industry.',
        'Whether the 2021-25 low-wage (p10/p25) drift above the ECI continues past May 2025: two exact-wage windows only; carried in wage_growth_se_pct (horizon 2.33 yr), not as a point shift.',
        f"Economy-wide gap between BLS's panel aging factors and true GM wage growth over the panels' lag: not identified from OEWS alone (vintage-on-vintage growth is unaffected by it); wage_growth_se would be {R['G_se_lag']:.3f} if it were as large as the ECI tracking error.",
        'How the noise beyond BLS SEs splits between a PRSE multiple (kappa) and constant panel-level noise for the very largest cells (wholesale, PRSE 0.7%): the variance function is fitted on cells down to PRSE ~1%, so the smallest se_total values are an extrapolation.',
        f"Whether the shrinkage itself should use the fitted kappa ({R['kh']:.2f}) instead of 1: the exact-wage windows do not decide it (see the kappa entry); it would move medical, vet and saas by up to {R['sensk'][kmax_k]*100:.1f}%. Kept at 1 as labelled judgment.",
        'Total employer cost of a GM (payroll taxes, benefits, non-production bonuses): OEWS records wages only; an ECEC-based loading (not in the downloaded files) is a follow-up fit.',
        "ECI sampling error (BLS publishes it separately; not in the downloaded files)."]
    script = '/home/user/last-minute/fit/oews_refresh.py'
    return {'name': 'oews_refresh', 'script': script, 'parameters': params, 'not_identified': not_id,
            'implementation': impl, 'data_tab_text': data_tab, 'test_invariants': inv, 'caveats': cav}


if __name__ == '__main__':
    R = main()
    res = build_result(R)
    json.dump(res, open(os.path.join(OUT, 'RESULT.json'), 'w'), indent=1)
    open(os.path.join(OUT, 'log.txt'), 'w').write('\n'.join(LOG) + '\n')
    json.dump({'inputs_sha256': R['inputs']}, open(os.path.join(OUT, 'inputs.json'), 'w'), indent=1)
    say(f'[out] wrote {OUT}/RESULT.json, app_table.csv, gm_wage_new.json, tau.csv, growth_validation.csv, growth_by_percentile.csv, shrink_validation.csv, '
        'posterior_se_mc_check.csv, bridge_validation.csv, rank_sensitivity.csv, harness_compare.json, log.txt')
