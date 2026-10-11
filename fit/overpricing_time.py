#!/usr/bin/env python3
"""overpricing_time.py - does overpricing lengthen time to sale? (revision 3, after the second independent review)

Run:  python3 -I /home/user/last-minute/fit/overpricing_time.py
Out:  /tmp/claude-0/fit5/overpricing_time/  (RESULT.json, results_full.json, tables, log, patched pages, diffs)

Question. The console's time to close (fitTiming) ignores the ask; its close probability falls with the
price gap through Pepperdine's gap penalty (gapPenalty, fitClose). Estimate
  (a) d log(time to sale | sale) / d log(ask / fair value) from per-listing analogs -> a time multiplier
  (b) the effect of the relative ask on the probability of selling -> shape check of gapPenalty
and turn it into an exact, shrunk change to index.html.

Sections
  A  Flippa March-2026 open-stock cohort followed 219 days (n=3,409 profitable listings). Fair multiple =
     cross-fitted ridge hedonic of the log ask multiple (March information only). cloglog single-interval
     sale hazard on the hinge of the relative ask; competing exits (multinomial); bins with empirical-Bayes
     shrinkage; shape test against Pepperdine's curve; REGRESSION CALIBRATION of the reconstructed ask
     (calibration slope of the true relative ask on the leave-out reconstruction, reference listings);
     Flippa's own Weibull shape by profile likelihood; competing-risk map of the window hazard to an
     ultimate close probability; 10-fold and leave-one-type-out CV.
  B  Flippa 2019 auctions without bids at the snapshot (start price = the seller's ask).
  C  Empire Flippers sold listings, FIRST ask (reconstructed) vs a cross-fitted hedonic fair SALE value
     (group folds by listing, so bootstrap copies of a listing never sit in both the training and the
     held-out fold). Weibull AFT with analytic gradient and Hessian; linear slope (the pooled entry),
     hinge, knot at fair value, right-truncation-corrected fits (sold-only sample cut at the data date),
     winsorised / trimmed relative asks, quintile dummies; bootstrap SEs; 10-fold CV and a 2019-22 ->
     2023-25H1 temporal hold-out (plain and truncation-adjusted likelihood).
  D  DealLedger US broker listings (Main Street), active -> sold, keyed by the listing `id` (stable across
     snapshots and price changes; a directory URL is shared by many listings), at risk only from the first
     snapshot that records a 'sold' status (2026-08-23): exponential hazard with a log-exposure OFFSET;
     held-out Poisson log-likelihood and a concordance index on the rate (no offset).
  E  IBBA Market Pulse band x quarter: realized/ask vs months listing->close (ecological, reverse-causal).
  F  Synthesis: every source on ONE scale, the sale-clock elasticity (-d ln sale hazard / k per log point of
     overpricing; EF's time-given-sale slope divided by EF's sell-through), random-effects pooling, then
     CONVERTED to the console's estimand before shrinking: d ln(time to close | close) / d ln(ask/value) =
     clock elasticity x P_C at value (competing risks, proportional hazards, withdrawal unaffected);
     shrinkage toward the current model value with a transfer sd FIXED in advance, a specification grid, the JS
     change written so it composes with fit/time_to_close_shape.py (applied after it or alone), the
     optimiser note rewritten on the delay-inclusive objective, model checks through the harness, and the
     repo's tests on the patched page and on the page merged with time_to_close_shape.
All inputs are read as untrusted data (CSV/JSON parsing only).

Changes from revision 1 (review of 2026-10-10): EF enters the pooling at its LINEAR slope (no midpoint);
Flippa's classical-error correction replaced by regression calibration; DealLedger uses an exposure offset;
pooled with a fixed transfer sd (monotone in the evidence) and a modified Hartung-Knapp SE; T_ELAST is a
LABELLED JUDGMENT with a specification range; EF hedonic cross-fitting by listing groups; analytic Hessians;
EF right truncation; the patch scales the band median once after `out.ft=FT;` and carries variants for
the Weibull page and the log-logistic (time_to_close_shape) page; the optimiser note uses the optimiser's
own objective (optNote); Data-tab, tile and Model III wording; non-tautological tests.

Changes from revision 2 (review of 2026-10-11): DealLedger keyed by listing id (revision 2 keyed on the URL,
which merged 320 of its 584 'listings'), at risk from the first sold-status snapshot, concordance and AUC on the
rate without the outcome-dependent offset; all sources pooled on the sale-clock scale and converted to time to
close | close with the console's P_C BEFORE shrinking; the specification range and grid include the conversion,
the DealLedger choices and leave-one-source-out; Flippa's regression calibration substitutes E[true | reconstructed]
for the non-reference listings only (reference listings carry their exact ask) with a bootstrap SE that refits the
calibration; EF reported across estimators and one-sided trims, entered with the largest SE across estimators;
EF temporal hold-out with the hedonic fitted on the training years only; outcome-defined EF subsamples removed;
the browser smoke check waits for the equation to render and asserts it."""
import os, sys, json, glob, subprocess, warnings, difflib, hashlib, shutil
import numpy as np, pandas as pd
from scipy import optimize, stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.base import clone
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

warnings.filterwarnings('ignore')
pd.set_option('display.width', 220)
OUT = '/tmp/claude-0/fit5/overpricing_time'
D5 = '/tmp/claude-0/data5'
HARNESS = '/tmp/claude-0/fit5/harness.js'
REPO = '/home/user/last-minute'
TTCS_DIR = '/tmp/claude-0/fit5/time_to_close_shape'   # concurrent fit: its page = time_to_close_shape applied to index.html
TTCS_PAGE = f'{TTCS_DIR}/patched/index.html'
SEED = 20261010
QUICK = os.environ.get('OT_QUICK') == '1'      # development only: fewer bootstrap replicates and fuzz samples
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, 'log.txt'), 'w')


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + '\n'); LOG.flush()


RES = {}          # everything that goes to results_full.json
CLL = sm.families.Binomial(link=sm.families.links.CLogLog())


def ridge_pipe(num, cat):
    pre = ColumnTransformer([('n', StandardScaler(), num),
                             ('c', OneHotEncoder(handle_unknown='ignore'), cat)])
    return Pipeline([('pre', pre), ('r', RidgeCV(alphas=np.logspace(-2, 3, 26)))])


def group_fold_ids(groups, folds, seed):
    """fold id per row such that all rows of a group share a fold (random partition of the groups)"""
    groups = np.asarray(groups)
    ug = pd.unique(groups)
    perm = np.random.default_rng(seed).permutation(len(ug))
    f = dict(zip(ug, perm % folds))
    return np.array([f[g] for g in groups])


def oof_ridge(df, y, num, cat, folds=10, seed=SEED, groups=None):
    """cross-fitted (out-of-fold) ridge predictions; the ridge penalty shrinks thin category cells toward the
    grand mean (an empirical-Bayes-like shrinkage with alpha chosen by CV). With `groups`, every copy of a
    group (e.g. a listing drawn twice by the bootstrap) is held out together, so a listing's own outcome
    never enters its own fair value."""
    y = np.asarray(y, float); pred = np.zeros(len(df))
    if groups is None:
        splits = list(KFold(folds, shuffle=True, random_state=seed).split(df))
    else:
        fid = group_fold_ids(groups, folds, seed)
        splits = [(np.where(fid != k)[0], np.where(fid == k)[0]) for k in range(folds)]
    for tr, te in splits:
        m = clone(ridge_pipe(num, cat)).fit(df.iloc[tr][num + cat], y[tr])
        pred[te] = m.predict(df.iloc[te][num + cat])
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    return pred, r2


def fit_glm(formula, df, family=CLL, cluster=None, offset=None):
    m = smf.glm(formula, df, family=family, offset=offset)
    if cluster is not None:
        return m.fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(df[cluster])[0]})
    return m.fit(cov_type='HC1')


def coef(r, name):
    return dict(est=float(r.params[name]), se=float(r.bse[name]))


def bernoulli_ll(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def cv_compare(df, y, formulas, family=CLL, folds=10, reps=3, groups=None, seed=SEED):
    """mean held-out log-likelihood per listing and AUC for several formulas on the same folds"""
    out = {k: dict(ll=[], auc=[]) for k in formulas}
    if groups is not None:
        splits = [(np.where(df[groups] != g)[0], np.where(df[groups] == g)[0]) for g in df[groups].unique()]
    else:
        splits = []
        for r in range(reps):
            splits += list(StratifiedKFold(folds, shuffle=True, random_state=seed + r).split(df, df[y]))
    for tr, te in splits:
        dtr, dte = df.iloc[tr], df.iloc[te]
        for k, f in formulas.items():
            try:
                m = smf.glm(f, dtr, family=family).fit()
                p = np.asarray(m.predict(dte))
            except Exception:
                p = np.full(len(dte), dtr[y].mean())
            out[k]['ll'].append(bernoulli_ll(dte[y].values, p) * len(dte))
            if dte[y].nunique() > 1:
                out[k]['auc'].append(roc_auc_score(dte[y].values, p))
    n = len(df) * (1 if groups is not None else reps)
    return {k: dict(heldout_loglik_per_obs=sum(v['ll']) / n,
                    auc_mean=float(np.mean(v['auc'])) if v['auc'] else None) for k, v in out.items()}


# ---------------------------------------------------------------------------------------------
# Pepperdine gap penalty exactly as the console computes it (harness), on a dense grid
# ---------------------------------------------------------------------------------------------
def node(js):
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    return json.loads(r.stdout)


GRID = np.arange(0, 1000.01, 0.25)
PEN = np.array(node(f"""const A=require({json.dumps(HARNESS)}).load([]);
const g=[];for(let x=0;x<=1000.001;x+=0.25)g.push(A.gapPenalty(x));console.log(JSON.stringify(g));"""))


def pen_of_gap(g):
    return np.interp(np.clip(g, 0, 1000), GRID, PEN)


def pc_ratio_model(rho):
    """console's P_C multiplier (1 - gapPenalty) at ask/value = rho"""
    return 1 - pen_of_gap(100 * (np.asarray(rho, float) - 1))


say('Pepperdine P_C multiplier at rho 1.1/1.2/1.3/1.5/2/3:',
    np.round(pc_ratio_model([1.1, 1.2, 1.3, 1.5, 2, 3]), 4))

# =============================================================================================
# A. Flippa March-2026 cohort
# =============================================================================================
say('\n=== A. Flippa March-2026 cohort ===')
P = pd.read_csv(f'{D5}/extra_flippa_outcome_panel/clean/flippa_march2026_cohort_panel.csv', low_memory=False)
A = P[(P.ann_profit > 0) & P.log_mult.notna()].copy().reset_index(drop=True)
A['monet'] = A.mar_monetization.fillna('NA').astype(str)
A['ind'] = A.mar_industry.fillna('NA').astype(str)
A['typ'] = A.mar_type.astype(str)
A['lp'] = np.log(A.ann_profit)
A['lp2'] = (A.lp - A.lp.mean()) ** 2
A['clu'] = A.tgroup.astype(str) + '|' + A.ind
A['ended'] = (A.y == 'ended').astype(int)
A['zombie'] = (A.age_mkt_class == '>2y').astype(int)
# hedonic fair multiple from March information only (no outcome, no October badge)
numA, catA = ['lp', 'lp2', 'log_age'], ['typ', 'monet', 'ind', 'tgroup']
predA, r2A = oof_ridge(A, A.log_mult.values, numA, catA)
A['rel_h'] = A.log_mult - predA
A['rel_t'] = A.rel_log_mult
for v in ['rel_h', 'rel_t']:
    A[v + '_p'] = A[v].clip(lower=0); A[v + '_n'] = A[v].clip(upper=0)
say(f'n={len(A)} sold={A.sold.sum()} ended={A.ended.sum()}  hedonic OOF R2={r2A:.3f}  sd(rel_h)={A.rel_h.std():.3f}')

# --- measurement error of the reconstructed March ask -------------------------------------------------
# The March ask of most listings is reconstructed from the March price RANK through an isotonic map fitted on
# the reference listings whose exact ask is known. Leave-out (10-fold) reconstruction of the reference
# listings reproduces the error a non-reference listing carries. Revision 1 divided the slope by a CLASSICAL
# reliability (1 - var(err)/var(rel)); the review showed the error is closer to Berkson (the map is E[ask |
# rank]). Regression calibration needs neither assumption: it divides by the slope of E[true | reconstructed,
# controls], estimated directly on the reference listings. For the hinge the relevant slope is that of the
# true POSITIVE part on the reconstructed positive part.
ref = P[P.ask_reference_listing.astype(str).isin(['True', '1', '1.0'])].sort_values('mar_rank_lowest_price').copy()
lr_ref = np.log(ref.oct_card_price.values); rk = ref.mar_rank_lowest_price.values
lhat = np.zeros(len(ref))
for tr, te in KFold(10, shuffle=True, random_state=SEED).split(ref):
    rm = pd.Series(lr_ref[tr]).rolling(15, center=True, min_periods=5).median().values
    iso = IsotonicRegression(out_of_bounds='clip').fit(rk[tr], rm)
    lhat[te] = iso.predict(rk[te])
err = lr_ref - lhat
err_w = np.clip(err, -1.5, 1.5)          # |err| > 1.5 log points (4.5x) are mostly asks changed between March and October
var_err = float(np.var(err_w))
lam_rel = float(1 - var_err / A.rel_h.var())                  # revision 1's classical reliability (kept as the upper bracket)
gam_logask = float(np.polyfit(lhat, lr_ref, 1)[0])            # slope of true log ask on reconstruction (Berkson => 1)
ref['lhat_lo'] = lhat; ref['e_w'] = err_w; ref['e_raw'] = err
RA_ = A.merge(ref[['listing_id', 'lhat_lo', 'e_w', 'e_raw']], on='listing_id', how='inner')
RA_['rel_hat'] = RA_.rel_h + (RA_.lhat_lo - RA_.log_ask)       # relative ask with the leave-out reconstruction
RA_['rel_true'] = RA_.rel_hat + RA_.e_w                        # with the exact ask (error winsorised at 1.5)
RA_['hp'] = RA_.rel_hat.clip(lower=0); RA_['hn'] = RA_.rel_hat.clip(upper=0); RA_['tp'] = RA_.rel_true.clip(lower=0)
ctrl = 'lp + log_age + id_rank + C(tgroup)'
r_cal = smf.ols(f'tp ~ hp + hn + {ctrl}', RA_).fit(cov_type='HC1')
r_cal_lin = smf.ols(f'rel_true ~ rel_hat + {ctrl}', RA_).fit(cov_type='HC1')
r_cal_ex = smf.ols(f'tp ~ hp + hn + {ctrl}', RA_[np.abs(RA_.e_raw) < 1.5]).fit(cov_type='HC1')
gam_p, gam_p_se = float(r_cal.params['hp']), float(r_cal.bse['hp'])
CAL = dict(n_reference_in_sample=len(RA_), reference_sale_rate=float(RA_.sold.mean()),
           nonreference_sale_rate=float(A[~A.listing_id.isin(RA_.listing_id)].sold.mean()),
           err_sd_winsorised=float(np.sqrt(var_err)), share_abs_err_lt_0p10=float(np.mean(np.abs(err) < .1)),
           slope_true_on_hat_logask=gam_logask, corr_err_hat=float(np.corrcoef(err, lhat)[0, 1]),
           corr_err_true=float(np.corrcoef(err, lr_ref)[0, 1]),
           classical_reliability=lam_rel, calib_slope_positive_part=dict(est=gam_p, se=gam_p_se),
           calib_slope_positive_part_excl_gross=coef(r_cal_ex, 'hp'),
           calib_slope_linear_rel=coef(r_cal_lin, 'rel_hat'))
say('reconstructed-ask calibration:', json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in CAL.items()}))

specs = {
    'main_hinge_hedonic': f'sold ~ rel_h_p + rel_h_n + {ctrl}',
    'linear_hedonic': f'sold ~ rel_h + {ctrl}',
    'hinge_type_median': f'sold ~ rel_t_p + rel_t_n + {ctrl}',
    'plus_verified_oct': f'sold ~ rel_h_p + rel_h_n + {ctrl} + verified',
    'age_on_market_proxy': f'sold ~ rel_h_p + rel_h_n + lp + log_age + log_age_mkt + C(tgroup)',
}
FA = {}
for k, f in specs.items():
    r = fit_glm(f, A, cluster='clu')
    term = 'rel_h_p' if 'rel_h_p' in f else ('rel_t_p' if 'rel_t_p' in f else 'rel_h')
    FA[k] = dict(formula=f, n=int(r.nobs), events=int(A.sold.sum()), beta_above=coef(r, term),
                 beta_below=coef(r, term.replace('_p', '_n')) if term.endswith('_p') else None, llf=float(r.llf),
                 aic=float(r.aic))
    say(f'  {k:24s} beta_above={r.params[term]:+.3f} ({r.bse[term]:.3f})' +
        (f'  beta_below={r.params[term.replace("_p","_n")]:+.3f} ({r.bse[term.replace("_p","_n")]:.3f})' if term.endswith('_p') else ''))
for lab, sub in [('non_zombie_listed_lt_2y', A[A.zombie == 0]), ('classified_only', A[A.sale_method_oct == 'classified'])]:
    r = fit_glm(specs['main_hinge_hedonic'], sub, cluster='clu')
    FA[lab] = dict(formula=specs['main_hinge_hedonic'], n=int(r.nobs), events=int(sub.sold.sum()),
                   beta_above=coef(r, 'rel_h_p'), beta_below=coef(r, 'rel_h_n'))
    say(f'  {lab:24s} beta_above={r.params["rel_h_p"]:+.3f} ({r.bse["rel_h_p"]:.3f})  n={int(r.nobs)}')
rA = fit_glm(specs['main_hinge_hedonic'], A, cluster='clu')
bA, seA = float(rA.params['rel_h_p']), float(rA.bse['rel_h_p'])
# REGRESSION CALIBRATION (revision 3). The reference listings (classified, never cut, still listed in October)
# carry their exact ask; only the other listings carry the rank reconstruction. For those listings only, the
# hinge terms are replaced by E[true hinge term | reconstructed hinge terms, controls], estimated on the reference
# listings' leave-out reconstruction (both hinge terms, so the cross-loadings are used); the reference listings
# keep their own values. Revision 2 divided the whole-sample slope by the calibration slope, over-correcting the
# third of the sample whose ask is already exact. SE: cluster bootstrap that redraws the reference listings with
# their clusters and refits the calibration inside every replicate.
CCAL = 'lp + log_age + id_rank'          # type-group levels absent among the reference listings: numeric controls only
RA_['tn'] = RA_.rel_true.clip(upper=0)
isrefA = A.listing_id.isin(RA_.listing_id).values


def rc_terms(D, RA):
    cp_ = smf.ols(f'tp ~ hp + hn + {CCAL}', RA).fit(); cn_ = smf.ols(f'tn ~ hp + hn + {CCAL}', RA).fit()
    X = D.assign(hp=D.rel_h_p, hn=D.rel_h_n); rf = D.listing_id.isin(RA_.listing_id).values
    return np.where(rf, D.rel_h_p, cp_.predict(X)), np.where(rf, D.rel_h_n, cn_.predict(X)), cp_, cn_


A['cal_p'], A['cal_n'], rcp_, rcn_ = rc_terms(A, RA_)
rA_rc = fit_glm(f'sold ~ cal_p + cal_n + {ctrl}', A, cluster='clu')
bA_rc, seA_rc_cl = float(rA_rc.params['cal_p']), float(rA_rc.bse['cal_p'])
rng = np.random.default_rng(SEED)
cl_idx = [np.where(A.clu.values == c_)[0] for c_ in A.clu.unique()]
bs_rc = []
for bi in range(20 if QUICK else 200):
    pick = rng.integers(0, len(cl_idx), len(cl_idx))
    Db = A.iloc[np.concatenate([cl_idx[j] for j in pick])].reset_index(drop=True)
    RAb = RA_.merge(Db[['listing_id']], on='listing_id')            # reference listings with their bootstrap multiplicity
    Db['cal_p'], Db['cal_n'], _, _ = rc_terms(Db, RAb)
    try:
        bs_rc.append(float(smf.glm(f'sold ~ cal_p + cal_n + {ctrl}', Db, family=CLL).fit().params['cal_p']))
    except Exception:
        pass
seA_rc_boot = float(np.std(bs_rc))
seA_rc = max(seA_rc_cl, seA_rc_boot)
# variants: revision 2 (whole-sample slope / calibration slope); uniform reconstruction (the reference listings get
# their leave-out reconstruction too, so every listing carries the same error, then the same substitution); the
# non-reference listings alone; revision 1's classical reliability
bA_rc2 = bA / gam_p
seA_rc2 = float(np.sqrt((seA / gam_p) ** 2 + (bA * gam_p_se / gam_p ** 2) ** 2))
bA_cl, seA_cl = bA / lam_rel, seA / lam_rel
lo_map = RA_.set_index('listing_id').lhat_lo
A['log_mult_u'] = A.log_mult + (np.where(isrefA, A.listing_id.map(lo_map), A.log_ask) - A.log_ask)
pu_, r2u_ = oof_ridge(A, A.log_mult_u.values, numA, catA)
A['rel_u'] = A.log_mult_u - pu_
Ru = A[isrefA].copy(); Ru['err'] = Ru.listing_id.map(RA_.set_index('listing_id').e_w)
Ru['tp'] = (Ru.rel_u + Ru.err).clip(lower=0); Ru['tn'] = (Ru.rel_u + Ru.err).clip(upper=0)
Ru['hp'] = Ru.rel_u.clip(lower=0); Ru['hn'] = Ru.rel_u.clip(upper=0)
Xu = A.assign(hp=A.rel_u.clip(lower=0), hn=A.rel_u.clip(upper=0))
A['ucal_p'] = smf.ols(f'tp ~ hp + hn + {CCAL}', Ru).fit().predict(Xu)
A['ucal_n'] = smf.ols(f'tn ~ hp + hn + {CCAL}', Ru).fit().predict(Xu)
rA_u = fit_glm(f'sold ~ ucal_p + ucal_n + {ctrl}', A, cluster='clu')
rA_nr = fit_glm(f'sold ~ cal_p + cal_n + {ctrl}', A[~isrefA], cluster='clu')
CAL.update(substitution=dict(main=dict(est=bA_rc, se=seA_rc, se_cluster=seA_rc_cl, se_boot=seA_rc_boot, B=len(bs_rc),
                                       below=coef(rA_rc, 'cal_n')),
                             calib_tp_coefs=rcp_.params[['hp', 'hn']].to_dict(), calib_tn_coefs=rcn_.params[['hp', 'hn']].to_dict(),
                             revision2_whole_sample_division=dict(est=bA_rc2, se=seA_rc2),
                             uniform_reconstruction=coef(rA_u, 'ucal_p'), nonreference_only=coef(rA_nr, 'cal_p'),
                             nonreference_n=int((~isrefA).sum()), nonreference_sales=int(A.sold[~isrefA].sum()),
                             reference_sales=int(A.sold[isrefA].sum()),
                             mean_rel_reference=float(A.rel_h[isrefA].mean()), mean_rel_nonreference=float(A.rel_h[~isrefA].mean())))
say(f'  beta_above raw {bA:+.3f} ({seA:.3f}); regression-calibrated (non-reference listings only) {bA_rc:+.3f} '
    f'(cluster {seA_rc_cl:.3f}, bootstrap incl. calibration {seA_rc_boot:.3f}); revision 2 whole-sample {bA_rc2:+.3f}; uniform '
    f'reconstruction {rA_u.params["ucal_p"]:+.3f}; non-reference only {rA_nr.params["cal_p"]:+.3f}; classical {bA_cl:+.3f} ({seA_cl:.3f})')
# split-half stability (random halves)
half = rng.random(len(A)) < .5
sh = [coef(fit_glm(specs['main_hinge_hedonic'], A[m], cluster='clu'), 'rel_h_p') for m in (half, ~half)]

# Flippa's own Weibull shape (time since listing): profile likelihood of the single-interval cloglog with
# offset log((a+w)^k - a^k), a = days on market at the March snapshot (an ID-envelope lower bound), w = 219.
# Under a Weibull proportional-hazards sale clock this is the exact interval probability. Age on market is
# nearly collinear with the vintage control id_rank, so k is weakly identified; it is a consistency check.
a_mkt = A.age_mkt_days_lb.clip(lower=1).astype(float).values
KPROF = []
for kk in np.round(np.arange(0.30, 2.001, 0.025), 3):
    off = np.log((a_mkt + 219.0) ** kk - a_mkt ** kk)
    rkk = smf.glm(specs['main_hinge_hedonic'], A, family=CLL, offset=off).fit()
    KPROF.append(dict(k=float(kk), llf=float(rkk.llf), beta_above=float(rkk.params['rel_h_p'])))
KPROF = pd.DataFrame(KPROF)
kF = KPROF.loc[KPROF.llf.idxmax()]
kF_ci = KPROF[KPROF.llf >= KPROF.llf.max() - stats.chi2.ppf(.95, 1) / 2].k
FLIPPA_K = dict(k_hat=float(kF.k), ci95=[float(kF_ci.min()), float(kF_ci.max())], beta_above_at_k_hat=float(kF.beta_above),
                corr_log_age_on_market_vs_id_rank=float(np.corrcoef(np.log(a_mkt), A.id_rank)[0, 1]))
say('  Flippa own Weibull shape (profile):', FLIPPA_K)

# competing exits: multinomial logit sold / ended / open
y3 = A.y.map({'open': 0, 'sold': 1, 'ended': 2}).values
X3 = pd.get_dummies(A[['rel_h_p', 'rel_h_n', 'lp', 'log_age', 'id_rank', 'tgroup']], columns=['tgroup'], drop_first=True, dtype=float)
X3 = sm.add_constant(X3)
mn = sm.MNLogit(y3, X3).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(A.clu)[0]})
MN = dict(sold_vs_open=dict(est=float(mn.params.loc['rel_h_p', 0]), se=float(mn.bse.loc['rel_h_p', 0])),
          ended_vs_open=dict(est=float(mn.params.loc['rel_h_p', 1]), se=float(mn.bse.loc['rel_h_p', 1])))
say('  mnlogit (base=open) overpricing slope: sold', MN['sold_vs_open'], ' ended', MN['ended_vs_open'])

# out-of-sample: 10-fold x3 and leave-one-type-group-out
cvA = cv_compare(A, 'sold', {'with_ask_hinge': specs['main_hinge_hedonic'], 'with_ask_linear': specs['linear_hedonic'],
                             'no_ask': f'sold ~ {ctrl}'})
logoA = cv_compare(A, 'sold', {'with_ask_hinge': specs['main_hinge_hedonic'].replace(' + C(tgroup)', ''),
                               'no_ask': f'sold ~ {ctrl}'.replace(' + C(tgroup)', '')}, groups='tgroup')
say('  10-fold x3 CV:', json.dumps(cvA)); say('  leave-one-type-group-out:', json.dumps(logoA))

# relative-ask bins, EB-shrunk toward the fitted hinge line
edges = [-np.inf, -.5, -.2, .2, .5, 1, np.inf]; labs = ['<-0.5', '-0.5..-0.2', '-0.2..0.2', '0.2..0.5', '0.5..1', '>1']
A['bin'] = pd.cut(A.rel_h, edges, labels=labs).astype(str)
rb = fit_glm(f"sold ~ C(bin, Treatment('-0.2..0.2')) + {ctrl}", A, cluster='clu')
binrows = []
for b in labs:
    sub = A[A.bin == b]
    nm = f"C(bin, Treatment('-0.2..0.2'))[T.{b}]"
    est, se = (float(rb.params[nm]), float(rb.bse[nm])) if nm in rb.params else (0.0, 0.0)
    xm = float(sub.rel_h.mean())
    lin = float(rA.params['rel_h_p'] * max(xm, 0) + rA.params['rel_h_n'] * min(xm, 0)
                - (rA.params['rel_h_p'] * max(A[A.bin == '-0.2..0.2'].rel_h.mean(), 0) + rA.params['rel_h_n'] * min(A[A.bin == '-0.2..0.2'].rel_h.mean(), 0)))
    binrows.append(dict(bin=b, n=len(sub), sold=int(sub.sold.sum()), raw_sale_rate=float(sub.sold.mean()),
                        mean_rel=xm, loghr=est, se=se, linear_fit=lin))
B = pd.DataFrame(binrows)
nz = B.se > 0
dev = (B.loghr - B.linear_fit)[nz]; v = (B.se ** 2)[nz]
tau2 = max(0.0, float((np.sum(dev ** 2) - np.sum(v)) / nz.sum()))      # method-of-moments between-bin variance
B['eb_shrink_w'] = np.where(nz, tau2 / (tau2 + B.se ** 2), 0.0)
B['loghr_eb'] = B.linear_fit + B.eb_shrink_w * (B.loghr - B.linear_fit)
say(B.round(3).to_string()); say(f'  EB between-bin tau^2 around the hinge line = {tau2:.4f}')

# shape test vs Pepperdine: P_C multiplier at rho = exp(rel + c) where c = log ask premium of the
# comparables' typical ask over buyers' value (0 or the marketplace sale/ask gap 0.15)
shape = {}
for c in (0.0, 0.15):
    A['zpep'] = np.log(np.clip(pc_ratio_model(np.exp(A.rel_h + c)), 1e-6, 1))
    r_p = fit_glm(f'sold ~ zpep + {ctrl}', A, cluster='clu')
    r_b = fit_glm(f'sold ~ zpep + rel_h_p + rel_h_n + {ctrl}', A, cluster='clu')
    cvs = cv_compare(A, 'sold', {'pepperdine_shape_free_amplitude': f'sold ~ zpep + {ctrl}',
                                 'loglinear_hinge': specs['main_hinge_hedonic'],
                                 'both': f'sold ~ zpep + rel_h_p + rel_h_n + {ctrl}'})
    shape[f'c={c}'] = dict(theta_pepperdine_amplitude=coef(r_p, 'zpep'), aic_pepperdine=float(r_p.aic),
                           aic_hinge=float(rA.aic), both_model=dict(theta=coef(r_b, 'zpep'), beta_above=coef(r_b, 'rel_h_p')),
                           cv=cvs)
    say(f'  shape c={c}: theta={r_p.params["zpep"]:.3f} ({r_p.bse["zpep"]:.3f}) AIC pep={r_p.aic:.1f} hinge={rA.aic:.1f}; '
        f'both: theta={r_b.params["zpep"]:.3f}({r_b.bse["zpep"]:.3f}) beta={r_b.params["rel_h_p"]:.3f}({r_b.bse["rel_h_p"]:.3f})')
    say('     CV', json.dumps(cvs))

# where does the sale hazard start to fall? profile the hinge knot by CV
KN = {}
for kn in (-0.3, -0.15, 0.0, 0.15, 0.3, 0.5):
    A['kp'] = (A.rel_h - kn).clip(lower=0); A['kn_'] = (A.rel_h - kn).clip(upper=0)
    rk_ = fit_glm(f'sold ~ kp + kn_ + {ctrl}', A, cluster='clu')
    cvk = cv_compare(A, 'sold', {'m': f'sold ~ kp + kn_ + {ctrl}'}, reps=2)
    KN[str(kn)] = dict(beta_above=coef(rk_, 'kp'), beta_below=coef(rk_, 'kn_'), aic=float(rk_.aic),
                       cv_loglik=cvk['m']['heldout_loglik_per_obs'])
    say(f'  knot {kn:+.2f}: above={rk_.params["kp"]:+.3f} ({rk_.bse["kp"]:.3f}) below={rk_.params["kn_"]:+.3f} AIC={rk_.aic:.1f} CV={cvk["m"]["heldout_loglik_per_obs"]:.5f}')
# Pepperdine shape above the knot plus the same below-knot slope, so the two shapes compete only above it
for c in (0.0, 0.15):
    A['zpep'] = np.log(np.clip(pc_ratio_model(np.exp(A.rel_h + c)), 1e-6, 1))
    r_pb = fit_glm(f'sold ~ zpep + rel_h_n + {ctrl}', A, cluster='clu')
    cvpb = cv_compare(A, 'sold', {'pep_plus_below': f'sold ~ zpep + rel_h_n + {ctrl}'})
    shape[f'c={c}']['pepperdine_plus_below_slope'] = dict(theta=coef(r_pb, 'zpep'), aic=float(r_pb.aic),
                                                          cv_loglik=cvpb['pep_plus_below']['heldout_loglik_per_obs'])
    say(f'  pep+below c={c}: theta={r_pb.params["zpep"]:.3f} ({r_pb.bse["zpep"]:.3f}) AIC={r_pb.aic:.1f} (hinge {rA.aic:.1f}) CV={cvpb["pep_plus_below"]["heldout_loglik_per_obs"]:.5f}')


# standardized (marginal) P(sale in window) ratio curve from the hinge model, with a cluster bootstrap
def p_ratio_curve(fit_params, df, xs):
    base = df.copy(); out = []
    for x in [0.0] + list(xs):
        base['rel_h_p'] = max(x, 0); base['rel_h_n'] = min(x, 0)
        out.append(float(np.mean(fit_params.predict(base))))
    return np.array(out[1:]) / out[0]


RHOS = [1.1, 1.2, 1.3, 1.5, 2.0, 3.0]
xs = np.log(RHOS)
curve = p_ratio_curve(rA, A, xs)
bs = []
for bi in range(20 if QUICK else 200):
    pick = rng.integers(0, len(cl_idx), len(cl_idx))
    Db = A.iloc[np.concatenate([cl_idx[j] for j in pick])].reset_index(drop=True)
    try:
        rb_ = smf.glm(specs['main_hinge_hedonic'], Db, family=CLL).fit()
        bs.append(p_ratio_curve(rb_, A, xs))
    except Exception:
        pass
bs = np.array(bs)


# The window probability is NOT the ultimate close probability (slow sales count as failures in a 219-day
# window). Map the cause-specific sale hazard to an ultimate close probability with competing withdrawal:
# P = h_s/(h_s+h_w), h_s ~ e^{beta_s x}, h_w ~ e^{beta_w x}  =>  P(x) = 1/(1 + ((1-P0)/P0) e^{(beta_w-beta_s) x}).
# P0 = 0.61 (console broker base, Pepperdine resolved outcomes); beta_w = 0 (withdrawal unaffected) or the
# multinomial 'ended' slope (overpriced listings also end less often).
PC_MS = 0.61


def ultimate_ratio(beta_s, beta_w, rho, p0=PC_MS):
    x = np.log(np.asarray(rho, float))
    return (1 / (1 + (1 - p0) / p0 * np.exp((beta_w - beta_s) * x))) / p0


CURVE = pd.DataFrame(dict(rho_vs_comparables=RHOS, p_sale_ratio_flippa_window=curve, se_boot=bs.std(0),
                          ultimate_ratio_withdrawal_unaffected=ultimate_ratio(bA_rc, 0.0, RHOS),
                          ultimate_ratio_withdrawal_as_mnlogit=ultimate_ratio(bA_rc, MN['ended_vs_open']['est'], RHOS),
                          pepperdine_pc_ratio_c0=pc_ratio_model(RHOS),
                          pepperdine_pc_ratio_c015=pc_ratio_model(np.exp(xs + .15)) / pc_ratio_model(np.exp(.15))))
say(CURVE.round(3).to_string())


# local elasticities d ln P / d ln rho of the console curve vs the data
def local_el(f, r, h=1e-3):
    return (np.log(f(r * np.exp(h))) - np.log(f(r * np.exp(-h)))) / (2 * h)


EL = pd.DataFrame(dict(rho=[1.05, 1.1, 1.2, 1.3, 1.5, 2.0, 3.0]))
EL['console_dlnPC_dlnrho'] = [float(local_el(lambda q: pc_ratio_model(q), r)) for r in EL.rho]
H = -np.log(1 - A.sold.mean())
EL['flippa_dlnP_dlnrho_window'] = bA_rc * H * np.exp(-H) / (1 - np.exp(-H))
EL['flippa_ultimate_dlnP_dlnrho'] = [float(local_el(lambda q: ultimate_ratio(bA_rc, 0.0, q), r)) for r in EL.rho]
say(EL.round(3).to_string())

RES['A_flippa_march'] = dict(
    n=len(A), events=int(A.sold.sum()), window_days=219, hedonic_oof_r2=r2A, sd_rel=float(A.rel_h.std()),
    ask_calibration=CAL, fits=FA, beta_above_raw=dict(est=bA, se=seA),
    beta_above_regression_calibrated=dict(est=bA_rc, se=seA_rc), beta_above_classical=dict(est=bA_cl, se=seA_cl),
    flippa_weibull_shape_profile=FLIPPA_K, split_half=sh, mnlogit=MN, cv_10fold_x3=cvA,
    cv_leave_one_type_group_out=logoA, bins=B.to_dict('records'), eb_tau2=tau2, shape_test=shape, knot_profile=KN,
    p_ratio_curve=CURVE.to_dict('records'), elasticities=EL.to_dict('records'))
B.to_csv(os.path.join(OUT, 'A_flippa_bins.csv'), index=False)
CURVE.to_csv(os.path.join(OUT, 'A_flippa_p_ratio_curve.csv'), index=False)
KPROF.to_csv(os.path.join(OUT, 'A_flippa_k_profile.csv'), index=False)

# =============================================================================================
# B. Flippa 2019 auctions with no bid at the snapshot: start price = the seller's ask
# =============================================================================================
say('\n=== B. Flippa 2019 auctions (no bids at snapshot) ===')
F19 = pd.read_csv(f'{D5}/extra_flippa_outcome_panel/clean/flippa2019_open_cohort_outcomes.csv')
Bq = F19[(F19.sale_method == 'auction') & (F19.bid_count == 0) & (F19.outcome != 'open')].copy()
Bq['ver'] = (Bq.verified_revenue.astype(str).isin(['True', '1']) | Bq.verified_traffic.astype(str).isin(['True', '1'])).astype(int)
Bq['log_dur'] = np.log(Bq.duration_days.clip(1, 90))
Bq['has_bin'] = Bq.bin_price_usd.notna().astype(int)
Bq['bin_gap'] = Bq.log_bin_to_price.fillna(0)
Bq['ptype'] = Bq.property_type.astype(str)
Bq['rel_p'] = Bq.rel_price.clip(lower=0); Bq['rel_n'] = Bq.rel_price.clip(upper=0)
fB = 'sold ~ rel_p + rel_n + has_bin + bin_gap + ver + log_dur + C(ptype)'
rB = fit_glm(fB, Bq, family=sm.families.Binomial())
cvB = cv_compare(Bq, 'sold', {'with_price': fB, 'no_price': 'sold ~ has_bin + ver + log_dur + C(ptype)'},
                 family=sm.families.Binomial())
RES['B_flippa_2019_auctions'] = dict(n=len(Bq), events=int(Bq.sold.sum()), formula=fB, link='logit',
                                    beta_start_price_above_type_median=coef(rB, 'rel_p'),
                                    beta_start_price_below_type_median=coef(rB, 'rel_n'),
                                    beta_bin_gap=coef(rB, 'bin_gap'), cv_10fold_x3=cvB)
say(json.dumps(RES['B_flippa_2019_auctions'], indent=1))

# =============================================================================================
# C. Empire Flippers: FIRST ask vs fair sale value, time on market | sale
# =============================================================================================
say('\n=== C. Empire Flippers first ask (sold listings) ===')
L = pd.read_csv(f'{D5}/empireflippers/clean/ef_listings.csv', low_memory=False)
R = pd.read_csv(f'{D5}/extra_ef_sale_ask_reconstruction/clean/ef_sale_ask_reconstructed.csv')
FAK = pd.read_csv(f'{D5}/extra_ef_sale_ask_reconstruction/clean/ef_first_ask_reconstructed.csv')
MM = pd.read_csv(f'{D5}/empireflippers/clean/ef_monthly_metrics.csv')
MM['month'] = pd.to_datetime(MM.month)
# data date: the last first-listing timestamp in the snapshot (sold listings are observed only if they sold by then)
DATA_DATE = pd.to_datetime(L.first_listed_at, utc=True).dt.tz_localize(None).max().normalize()
keepL = ['listing_number', 'first_listed_at', 'metrics_last_month', 'monetizations_n', 'sites_n', 'average_annual_gross_revenue']
E = R.merge(FAK[['listing_number', 'first_ask_est']], on='listing_number').merge(L[keepL], on='listing_number')
E['fl'] = pd.to_datetime(E.first_listed_at, utc=True).dt.tz_localize(None)
E['fl_m'] = E.fl.dt.to_period('M').dt.to_timestamp()
E = E[E.first_ask_est.notna() & (E.average_monthly_net_profit > 0) & E.listing_price.notna()
      & ~E.flag_top_censored & ~E.flag_wide_bracket & ~E.flag_no_ask & (E.listing_multiple >= 6)
      & (E.fl >= '2019-01-01') & (E.fl < '2025-07-01') & E.days_on_marketplace.notna()].copy()
# profit EF priced the FIRST ask on: mean of the last P months available before the first-listing month.
# Everything the fair value conditions on must be known at first listing: the API's trend, margin and
# average profit describe the LAST pricing window, which moves with what happened while the listing sat
# (a profit fall re-prices the ask down AND slows the sale), so they are rebuilt from pre-listing months.
G = MM.groupby('listing_number')
prof0, nmon, trend0, margin0 = [], [], [], []
for ln_, fm, Pm in zip(E.listing_number, E.fl_m, E.pricing_period_months.fillna(12)):
    if ln_ not in G.groups:
        prof0.append(np.nan); nmon.append(0); trend0.append(np.nan); margin0.append(np.nan); continue
    g = G.get_group(ln_)
    g = g[g.month < fm].sort_values('month')
    w = g[g.month >= fm - pd.DateOffset(months=int(Pm) + 1)].tail(int(Pm))
    ok = len(w) >= 3
    prof0.append(w.net_profit.mean() if ok else np.nan); nmon.append(len(w))
    if len(w) >= 6:
        a, b_ = w.net_profit.iloc[:3].mean(), w.net_profit.iloc[-3:].mean()
        trend0.append(np.clip((b_ - a) / max(abs(w.net_profit.mean()), 1.0), -1.5, 1.5))
    else:
        trend0.append(np.nan)
    gr = w.gross_revenue.sum()
    margin0.append(np.clip(w.net_profit.sum() / gr, -0.5, 1.0) if ok and gr > 0 else np.nan)
E['profit0_m'] = prof0; E['n_months0'] = nmon; E['trend0'] = trend0; E['margin0'] = margin0
E['rebased'] = (E.fl - pd.to_datetime(E.metrics_last_month)).dt.days < 15
E = E[E.profit0_m > 0].copy().reset_index(drop=True)
E['cat'] = E.monetizations.astype(str).str.split('|').str[0].map(lambda m: {
    'Amazon Associates': 'content', 'Display Advertising': 'content', 'Affiliate': 'content', 'YouTube': 'content',
    'Lead Gen': 'content', 'Newsletter': 'content', 'Amazon FBA': 'amazon_fba', 'Amazon FBM': 'amazon_fba',
    'eCommerce': 'ecommerce', 'DropShipping': 'ecommerce', 'Subscription-Box': 'ecommerce', 'Amazon KDP': 'kdp_merch',
    'Amazon Merch': 'kdp_merch', 'SaaS': 'saas_digital', 'Subscription': 'saas_digital', 'Application': 'saas_digital',
    'Digital Product': 'saas_digital', 'Info Product': 'saas_digital', 'Service': 'service', 'Agency': 'service'}.get(m, 'other'))
E['ly'] = E.fl.dt.year.astype(str)
E['lp0'] = np.log(12 * E.profit0_m)
E['lp0_2'] = (E.lp0 - E.lp0.mean()) ** 2
E['l_age'] = np.log1p(pd.to_numeric(E.business_age_years_at_listing, errors='coerce').clip(0, 25).fillna(3))
E['trend_na'] = E.trend0.isna().astype(int)
E['trend'] = E.trend0.fillna(0)                                   # pre-listing profit trend (last 3 vs first 3 months)
E['l_hours'] = np.log1p(pd.to_numeric(E.hours_worked_per_week, errors='coerce').clip(0, 60).fillna(5))
E['margin'] = E.margin0.fillna(E.margin0.median())                # pre-listing margin
E['tm'] = E.has_trademark.astype(str).isin(['True', '1']).astype(str)
E['ppm'] = E.pricing_period_months.fillna(12).astype(int).astype(str)
E['monet_n'] = E.monetizations_n.fillna(1).clip(1, 4).astype(int).astype(str)
E['first_mult'] = np.log(E.first_ask_est / (12 * E.profit0_m))                 # log annual multiple at first ask
E['sale_mult_cur'] = np.log(E.sale_price_mean / (12 * E.profit0_m))            # sale price over the profit at listing
E['last_mult'] = np.log(E.listing_price / (12 * E.profit0_m))                  # LAST ask over the profit at listing
E['mult_change'] = np.log(E.listing_multiple) - np.log(E.first_ask_est / E.profit0_m)   # multiple cut (+ = raised)
E['T'] = E.days_on_marketplace.clip(lower=0.5)
E['T2'] = E.days_first_listed_to_sold_est.clip(lower=0.5)
E['tau'] = (DATA_DATE - E.fl).dt.days.astype(float)               # follow-up: sold listings are seen only if T <= tau
assert (E['T'] <= E['tau']).all()
numE, catE = ['lp0', 'lp0_2', 'l_age', 'trend', 'trend_na', 'l_hours', 'margin'], ['cat', 'ly', 'tm', 'ppm', 'monet_n']
say(f'EF analysis sample n={len(E)} (first listed 2019-01..2025-06, sold); re-based share={E.rebased.mean():.3f}; '
    f'median months used for profit0={np.median(E.n_months0):.0f}; data date {DATA_DATE.date()}; min follow-up {E.tau.min():.0f} d')


def ef_build(df, seed=SEED, num=None):
    """cross-fitted hedonics, folds by listing (bootstrap copies of one listing are held out together)"""
    num = num or numE
    d = df.copy()
    grp = d.listing_number.values
    ps, r2s = oof_ridge(d, d.sale_mult_cur.values, num, catE, seed=seed, groups=grp)
    pa, r2a = oof_ridge(d, d.first_mult.values, num, catE, seed=seed, groups=grp)
    d['rho_sale'] = d.first_mult - ps          # log(first ask / hedonic fair SALE value at listing)
    d['rho_ask'] = d.first_mult - pa           # log(first ask / comparables' typical first ask)
    d['rho_last'] = d.last_mult - ps           # LAST ask (contaminated by cuts that follow a slow sale)
    c = float(np.median(d.rho_sale))
    for v, cc in [('rho_sale', c), ('rho_ask', 0.0), ('rho_last', float(np.median(d.rho_last)))]:
        d[v + '_p'] = (d[v] - cc).clip(lower=0); d[v + '_n'] = (d[v] - cc).clip(upper=0); d[v + '_l'] = d[v] - cc
    d['r0_p'] = d.rho_sale.clip(lower=0); d['r0_n'] = d.rho_sale.clip(upper=0)      # knot at the fair value itself
    return d, dict(r2_sale_hedonic=float(r2s), r2_ask_hedonic=float(r2a), typical_log_premium_c=c)


E, hedE = ef_build(E)
say('  hedonic:', hedE, f' sd(rho_sale)={E.rho_sale.std():.3f}')


def design(df, xcols, cats=None):
    cats = catE if cats is None else cats
    X = pd.get_dummies(df[xcols + cats], columns=cats, drop_first=True, dtype=float)
    X = X.loc[:, X.std() > 0]
    return np.column_stack([np.ones(len(df)), X.values]), ['const'] + list(X.columns)


# ---- Weibull AFT: log T = Xb + s W, W ~ standard minimum extreme value; optional right truncation at tau ----
def wb_parts(th, y, X, logtau=None):
    b, ls = th[:-1], th[-1]; s = np.exp(ls); mu = X @ b; z = (y - mu) / s; ez = np.exp(z)
    nll = -np.sum(z - ez - ls)
    g = np.r_[X.T @ (1 - ez) / s, np.sum((1 - ez) * z + 1)]
    if logtau is not None:          # likelihood f(T)/F(tau): only listings that sold by the data date are seen
        zt = (logtau - mu) / s; ezt = np.exp(zt)
        F = np.clip(-np.expm1(-ezt), 1e-300, 1)
        nll += np.sum(np.log(F))
        rr = ezt * np.exp(-ezt) / F
        g = g + np.r_[X.T @ (-rr) / s, np.sum(-rr * zt)]
    return nll, g


def wb_hess(th, y, X):
    """analytic Hessian of the untruncated negative log-likelihood"""
    b, ls = th[:-1], th[-1]; s = np.exp(ls); z = (y - X @ b) / s; ez = np.exp(z)
    Hbb = (X * ez[:, None]).T @ X / s ** 2
    Hbl = X.T @ (z * ez - (1 - ez)) / s
    Hll = np.sum(z * z * ez - z + z * ez)
    Hm = np.zeros((len(th), len(th))); Hm[:-1, :-1] = Hbb; Hm[:-1, -1] = Hbl; Hm[-1, :-1] = Hbl; Hm[-1, -1] = Hll
    return Hm


def num_hess(gfun, th, h=1e-5):
    """Hessian by central differences of the analytic gradient (truncated likelihood)"""
    Hm = np.zeros((len(th), len(th)))
    for j in range(len(th)):
        e = np.zeros(len(th)); e[j] = h
        Hm[:, j] = (gfun(th + e) - gfun(th - e)) / (2 * h)
    return (Hm + Hm.T) / 2


def weibull_aft(y, X, logtau=None, start=None, want_se=True):
    if start is None:
        start = np.r_[np.linalg.lstsq(X, y, rcond=None)[0], 0.0]
    f = lambda th: wb_parts(th, y, X, logtau)
    res = optimize.minimize(lambda th: f(th)[0], start, jac=lambda th: f(th)[1], method='BFGS',
                            options={'maxiter': 50000, 'gtol': 1e-7})
    se = None
    if want_se:
        Hm = wb_hess(res.x, y, X) if logtau is None else num_hess(lambda th: f(th)[1], res.x)
        se = np.sqrt(np.diag(np.linalg.pinv(Hm)))
    return res.x, se, -float(res.fun)


def aft(df, xvars, tvar='T', dist='weibull', num=None, trunc=False, want_se=True, cats=None):
    """AFT of log time on the relative-ask terms xvars + controls; returns slopes on xvars with SEs.
    dist: 'weibull' (main), 'lognormal' (OLS on log T, HC1 SEs), or a quantile 'q0.25' / 'q0.5' / 'q0.75'
    (linear quantile regression of log T, robust SEs)"""
    num = numE if num is None else num
    X, names = design(df, xvars + num, cats)
    y = np.log(df[tvar].values)
    if dist == 'weibull':
        lt = np.log(df['tau'].values) if trunc else None
        st = None
        if trunc:
            st, _, _ = weibull_aft(y, X, None, want_se=False)
        th, se, ll = weibull_aft(y, X, lt, start=st, want_se=want_se)
        out = dict(coef={v: dict(est=float(th[1 + i]), se=(float(se[1 + i]) if se is not None else None)) for i, v in enumerate(xvars)},
                   shape_k=float(np.exp(-th[-1])), loglik=ll, aic=-2 * ll + 2 * len(th), n=len(df))
        return out
    if dist.startswith('q'):
        m = sm.QuantReg(y, X).fit(q=float(dist[1:]), max_iter=5000)
        return dict(coef={v: dict(est=float(m.params[1 + i]), se=float(m.bse[1 + i])) for i, v in enumerate(xvars)}, n=len(df))
    m = sm.OLS(y, X).fit(cov_type='HC1')
    s = np.sqrt(np.mean(m.resid ** 2))
    ll = float(np.sum(stats.norm.logpdf(m.resid, 0, s) - y))      # lognormal log-lik on the T scale
    return dict(coef={v: dict(est=float(m.params[1 + i]), se=float(m.bse[1 + i])) for i, v in enumerate(xvars)},
                sigma=float(s), loglik=ll, aic=-2 * ll + 2 * (X.shape[1] + 1), n=len(df))


HING = ['rho_sale_p', 'rho_sale_n']; LIN = ['rho_sale_l']
CE = {}


def rec(lab, f, keys):
    CE[lab] = f
    txt = '  '.join(f'{k}={f["coef"][k]["est"]:+.3f} ({f["coef"][k]["se"]:.3f})' for k in keys)
    say(f'  {lab:52s} {txt}' + (f'  k={f["shape_k"]:.3f}' if 'shape_k' in f else ''))


mainH = aft(E, HING); rec('hinge_median_knot|weibull', mainH, HING)
mainL = aft(E, LIN); rec('linear|weibull', mainL, LIN)
rec('hinge_median_knot|lognormal', aft(E, HING, dist='lognormal'), HING)
rec('linear|lognormal', aft(E, LIN, dist='lognormal'), LIN)
rec('knot_at_fair_value|weibull', aft(E, ['r0_p', 'r0_n']), ['r0_p', 'r0_n'])
rec('linear_truncation_corrected|weibull', aft(E, LIN, trunc=True), LIN)
rec('hinge_truncation_corrected|weibull', aft(E, HING, trunc=True), HING)
rec('listing_to_sold_clock_hinge|weibull', aft(E, HING, tvar='T2'), HING)
rec('listing_to_sold_clock_linear|weibull', aft(E, LIN, tvar='T2'), LIN)
rec('vs_comparables_asks_hinge|weibull', aft(E, ['rho_ask_p', 'rho_ask_n']), ['rho_ask_p', 'rho_ask_n'])
rec('vs_comparables_asks_linear|weibull', aft(E, ['rho_ask_l']), ['rho_ask_l'])
rec('LAST_ask_hinge|weibull', aft(E, ['rho_last_p', 'rho_last_n']), ['rho_last_p', 'rho_last_n'])
say(f'  share of first asks below the hedonic fair value: {np.mean(E.rho_sale < 0):.3f}')

# outlier treatment of the relative ask (the review showed the hinge arms move with it)
cE = hedE['typical_log_premium_c']
for lab, (plo, phi, how) in {'winsor_1_99': (1, 99, 'w'), 'winsor_5_95': (5, 95, 'w'), 'trim_5_95': (5, 95, 't')}.items():
    lo_, hi_ = np.percentile(E.rho_sale, plo), np.percentile(E.rho_sale, phi)
    D_ = E.copy()
    if how == 'w':
        D_['rho_sale'] = D_.rho_sale.clip(lo_, hi_)
    else:
        D_ = D_[(D_.rho_sale >= lo_) & (D_.rho_sale <= hi_)].reset_index(drop=True)
    D_['rho_sale_p'] = (D_.rho_sale - cE).clip(lower=0); D_['rho_sale_n'] = (D_.rho_sale - cE).clip(upper=0); D_['rho_sale_l'] = D_.rho_sale - cE
    rec(f'hinge_{lab}|weibull', aft(D_, HING), HING)
    rec(f'linear_{lab}|weibull', aft(D_, LIN), LIN)
# quintile dummies (middle quintile = reference): is the V shape real or an outlier artefact?
E['q'] = pd.qcut(E.rho_sale, 5, labels=False)
for j in (0, 1, 3, 4):
    E[f'q{j}'] = (E.q == j).astype(float)
rec('quintile_dummies_vs_q2|weibull', aft(E, ['q0', 'q1', 'q3', 'q4']), ['q0', 'q1', 'q3', 'q4'])
# subsamples defined BEFORE listing (listing year). Revision 2's re-based / not re-based split was defined by the
# outcome (a P&L refreshed while the listing was up means it sat longer: median days on market 102 vs 14), so it
# is no longer reported.
for lab, sub in [('listed_2019_2021', E[E.ly.astype(int) <= 2021]), ('listed_2022_2025H1', E[E.ly.astype(int) >= 2022])]:
    sub = sub.reset_index(drop=True)
    rec(f'subsample_{lab}_hinge|weibull', aft(sub, HING), HING)
    rec(f'subsample_{lab}_linear|weibull', aft(sub, LIN), LIN)
# estimators other than the Weibull AFT, and ONE-SIDED trims (the linear slope balances the two arms of a V, so
# dropping one tail moves it a lot): reported so the stated EF range covers estimator and outlier choices
rec('linear|median_regression', aft(E, LIN, dist='q0.5'), LIN)
rec('linear|quantile_0.25', aft(E, LIN, dist='q0.25'), LIN)
rec('linear|quantile_0.75', aft(E, LIN, dist='q0.75'), LIN)
for lab, keep in [('drop_top_2p5', E.rho_sale <= np.percentile(E.rho_sale, 97.5)), ('drop_bottom_2p5', E.rho_sale >= np.percentile(E.rho_sale, 2.5))]:
    rec(f'linear_{lab}|weibull', aft(E[keep].reset_index(drop=True), LIN), LIN)
EF_BY_YEAR = {}
for yy in sorted(E.ly.unique()):
    f_ = aft(E[E.ly == yy].reset_index(drop=True), LIN, cats=[c for c in catE if c != 'ly'])
    EF_BY_YEAR[yy] = dict(n=int((E.ly == yy).sum()), **f_['coef']['rho_sale_l'])
say('  linear slope by listing year:', json.dumps({k: (v['n'], round(v['est'], 3), round(v['se'], 3)) for k, v in EF_BY_YEAR.items()}))
# contrast: the API's FINAL-state trend, margin and average profit as covariates (they move with what happened
# while the listing sat, a leak)
E['trend_api'] = pd.to_numeric(E.net_profit_trend_percent, errors='coerce').clip(-60, 150).fillna(0) / 100
E['margin_api'] = pd.to_numeric(E.profit_margin, errors='coerce').clip(-50, 100).fillna(30) / 100
E['lp_api'] = np.log(E.average_annual_net_profit)
num_api = ['lp_api', 'l_age', 'trend_api', 'l_hours', 'margin_api']
Ea, _ = ef_build(E.assign(sale_mult_cur=np.log(E.sale_price_mean / E.average_annual_net_profit)), num=num_api)
rec('contrast_final_state_covariates_hinge|weibull', aft(Ea, HING, num=num_api), HING)
diagE = dict(sd_rho_sale=float(E.rho_sale.std()), by_year_linear=EF_BY_YEAR)

# bootstrap: rows resampled, both hedonics re-cross-fitted inside each replicate with folds by listing
BB = 20 if QUICK else 300
bb = []
for bi in range(BB):
    idx = rng.integers(0, len(E), len(E))
    d, _ = ef_build(E.iloc[idx].reset_index(drop=True), seed=SEED + bi + 1)
    fh = aft(d, HING, want_se=False); fl_ = aft(d, LIN, want_se=False)
    bb.append([fh['coef']['rho_sale_p']['est'], fh['coef']['rho_sale_n']['est'], fl_['coef']['rho_sale_l']['est'], fl_['shape_k']])
bb = np.array(bb)
bootE = dict(B=BB, hinge_above_se=float(bb[:, 0].std()), hinge_below_se=float(bb[:, 1].std()),
             monotone_component_se=float((bb[:, 0] + bb[:, 1]).std()), linear_se=float(bb[:, 2].std()),
             linear_p05=float(np.percentile(bb[:, 2], 5)), linear_p95=float(np.percentile(bb[:, 2], 95)),
             shape_k_se=float(bb[:, 3].std()))
say('  bootstrap (group-fold hedonics):', bootE)


# out-of-sample checks of the AFT slopes. The fair value is the cross-fitted hedonic (it uses sale multiples,
# never durations), as the console's V is given. Temporal hold-out: fit on first listed 2019-2022, apply the
# slopes to 2023-2025H1 and re-estimate only the intercept and scale there (EF's days on market rose from
# ~70 to ~120 between 2022 and 2025, a level shift both models share). The truncation-adjusted version uses
# f(T)/F(tau) in both the fit and the test likelihood: 2023-25 listings are seen only if they sold by the
# data date. 10-fold CV: slopes and year effects.
def aft_oos(tr, te, xvars, recal, trunc=False):
    cats = [c for c in catE if c != 'ly'] if recal else catE
    cols = xvars + numE
    allX = pd.get_dummies(pd.concat([tr, te])[cols + cats], columns=cats, drop_first=True, dtype=float)
    keep = (allX.iloc[:len(tr)].std() > 0).values
    Xtr = np.column_stack([np.ones(len(tr)), allX.iloc[:len(tr)].loc[:, keep].values])
    Xte = np.column_stack([np.ones(len(te)), allX.iloc[len(tr):].loc[:, keep].values])
    ltr = np.log(tr.tau.values) if trunc else None
    lte = np.log(te.tau.values) if trunc else None
    th, _, _ = weibull_aft(np.log(tr['T'].values), Xtr, ltr, want_se=False)
    b, ls = th[:-1], th[-1]
    y = np.log(te['T'].values)

    def te_nll(i0, ls_, lp):
        mu = i0 + lp; s = np.exp(ls_); z = (y - mu) / s
        v = -np.sum(z - np.exp(z) - ls_)
        if trunc:
            v += np.sum(np.log(np.clip(-np.expm1(-np.exp((lte - mu) / s)), 1e-300, 1)))
        return v
    lp = Xte[:, 1:] @ b[1:]
    if recal:
        th2 = optimize.minimize(lambda t: te_nll(t[0], t[1], lp), [b[0], ls], method='Nelder-Mead',
                                options={'xatol': 1e-8, 'fatol': 1e-10, 'maxiter': 20000}).x
        i0, ls_ = th2
    else:
        i0, ls_ = b[0], ls
    ll = (-te_nll(i0, ls_, lp) - np.sum(y)) / len(y)               # log density of T (days), per listing
    mu = i0 + lp
    med = mu + np.exp(ls_) * np.log(np.log(2))
    return dict(loglik_per_obs=float(ll), mae_log_T=float(np.mean(np.abs(y - med))),
                spearman_pred_obs=float(stats.spearmanr(mu, y).correlation))


def ef_build_holdout(tr, te, seed=SEED):
    """STRICT temporal split (revision 3): training rows get the hedonic cross-fitted within the training years
    (folds by listing); test rows get the hedonic fitted on all training rows, so no test-period sale multiple
    enters any fair value. The listing-year category is dropped from this hedonic (no test-year level is known in
    training; the recalibrated intercept absorbs the level); the hinge knot is the training median."""
    tr, te = tr.copy(), te.copy(); cats = [c for c in catE if c != 'ly']
    ps_tr, _ = oof_ridge(tr, tr.sale_mult_cur.values, numE, cats, seed=seed, groups=tr.listing_number.values)
    ps_te = clone(ridge_pipe(numE, cats)).fit(tr[numE + cats], tr.sale_mult_cur.values).predict(te[numE + cats])
    tr['rho_sale'] = tr.first_mult - ps_tr; te['rho_sale'] = te.first_mult - ps_te
    c_ = float(np.median(tr.rho_sale))
    for d_ in (tr, te):
        d_['rho_sale_p'] = (d_.rho_sale - c_).clip(lower=0); d_['rho_sale_n'] = (d_.rho_sale - c_).clip(upper=0)
        d_['rho_sale_l'] = d_.rho_sale - c_
    return tr, te


trE0 = E[E.ly.astype(int) <= 2022].reset_index(drop=True); teE0 = E[E.ly.astype(int) >= 2023].reset_index(drop=True)
trE, teE = ef_build_holdout(trE0, teE0)
MODS = [('with_rho_hinge', HING), ('with_rho_linear', LIN), ('no_rho', [])]
ho = {k: aft_oos(trE, teE, xv, True) for k, xv in MODS}
ho_tr = {k: aft_oos(trE, teE, xv, True, trunc=True) for k, xv in MODS}
ho['n_train'], ho['n_test'] = len(trE), len(teE)
ho_rev2 = {k: aft_oos(trE0, teE0, xv, True)['loglik_per_obs'] for k, xv in MODS}     # revision 2: hedonic cross-fitted on all years
say('  temporal hold-out (train 2019-22, test 2023-25H1, hedonic fitted on the training years only, intercept+scale recalibrated):', json.dumps(ho))
say('  temporal hold-out, truncation-adjusted likelihood:', json.dumps(ho_tr))
say('  (revision 2 version, hedonic cross-fitted on all years):', json.dumps(ho_rev2))
cvE = {k: [] for k, _ in MODS}
for trn, tst in KFold(10, shuffle=True, random_state=SEED).split(E):
    for k, xv in MODS:
        cvE[k].append(aft_oos(E.iloc[trn].reset_index(drop=True), E.iloc[tst].reset_index(drop=True), xv, False))
cvE = {k: {m: float(np.mean([d[m] for d in v])) for m in v[0]} for k, v in cvE.items()}
say('  10-fold CV:', json.dumps(cvE))

# mechanism: overpriced first asks get their MULTIPLE cut (EF re-pricing), the visible channel for lost time
E['cut'] = (E.mult_change < -0.03).astype(int)
cut_f = 'cut ~ rho_sale_p + rho_sale_n + ' + ' + '.join(numE) + ' + ' + ' + '.join(f'C({c})' for c in catE)
rc = fit_glm(cut_f, E, family=sm.families.Binomial())
cvC = cv_compare(E, 'cut', {'with_rho': cut_f, 'no_rho': cut_f.replace('rho_sale_p + rho_sale_n + ', '')},
                 family=sm.families.Binomial())
dom_cut = E.groupby('cut').T.median().to_dict()
say(f'  P(multiple cut) logit: above={rc.params["rho_sale_p"]:+.3f} ({rc.bse["rho_sale_p"]:.3f}); share cut={E.cut.mean():.3f}; '
    f'median DOM by cut={dom_cut}; CV={json.dumps(cvC)}')

QT = E.groupby('q').agg(n=('T', 'size'), rho_mean=('rho_sale', 'mean'), median_dom=('T', 'median'),
                        mean_log_dom=('T', lambda s: np.log(s).mean()), cut_share=('cut', 'mean')).reset_index()
QT['sale_over_first_ask'] = E.groupby('q').apply(lambda g: np.mean(g.sale_price_mean / g.first_ask_est)).values
say(QT.round(3).to_string())
QT.to_csv(os.path.join(OUT, 'C_ef_quintiles.csv'), index=False)
k_mkt = float(mainL['shape_k']); k_se = float(bootE['shape_k_se'])
ef_lin = mainL['coef']['rho_sale_l']
# the EF entry's SE is the LARGEST across estimators (Weibull analytic, bootstrap, OLS on log T, median regression):
# the Weibull SE understates how much the slope depends on the estimator and on a few extreme asks
EF_SE_PARTS = dict(weibull_analytic=ef_lin['se'], weibull_bootstrap=bootE['linear_se'],
                   ols_hc1=CE['linear|lognormal']['coef']['rho_sale_l']['se'], median_regression=CE['linear|median_regression']['coef']['rho_sale_l']['se'])
ef_lin_se = float(max(EF_SE_PARTS.values()))
EF_EST_KEYS = ['linear|weibull', 'linear_truncation_corrected|weibull', 'linear_winsor_1_99|weibull', 'linear_winsor_5_95|weibull',
               'linear_trim_5_95|weibull', 'linear_drop_top_2p5|weibull', 'linear_drop_bottom_2p5|weibull', 'linear|lognormal',
               'linear|median_regression', 'linear|quantile_0.25', 'linear|quantile_0.75']
EF_EST_RNG = (min(CE[k]['coef']['rho_sale_l']['est'] for k in EF_EST_KEYS), max(CE[k]['coef']['rho_sale_l']['est'] for k in EF_EST_KEYS))
say(f'  EF entry SE (largest across estimators) {ef_lin_se:.3f} from {json.dumps({k: round(v, 3) for k, v in EF_SE_PARTS.items()})}; '
    f'linear slope range across estimators and outlier treatments {EF_EST_RNG[0]:.3f}..{EF_EST_RNG[1]:.3f}')
ef_hi = mainH['coef']['rho_sale_p']['est']; ef_lo_ = ef_hi + mainH['coef']['rho_sale_n']['est']
RES['C_empire_flippers'] = dict(n=len(E), period='first listed 2019-01..2025-06, sold', data_date=str(DATA_DATE.date()),
                                hedonic=hedE, fits=CE, bootstrap=bootE, temporal_holdout=ho,
                                temporal_holdout_truncation_adjusted=ho_tr, temporal_holdout_revision2_full_sample_hedonic=ho_rev2, cv_10fold=cvE, diagnostics=diagE,
                                pooled_entry=dict(estimator='linear Weibull AFT slope on log(first ask / fair sale value)',
                                                  est=ef_lin['est'], se=ef_lin_se, se_parts=EF_SE_PARTS),
                                estimator_and_outlier_range=dict(keys=EF_EST_KEYS, min=EF_EST_RNG[0], max=EF_EST_RNG[1]),
                                cut_logit=dict(beta_above=coef(rc, 'rho_sale_p'), beta_below=coef(rc, 'rho_sale_n'),
                                               share_cut=float(E.cut.mean()), cv=cvC, median_dom_by_cut=dom_cut),
                                quintiles=QT.to_dict('records'), sell_through_scoreboard_2019_2020='88-95% (EF scoreboard, ef_scoreboard_cc_series.csv)')

# =============================================================================================
# D. DealLedger: US broker listings, active -> sold (Main Street)
# =============================================================================================
say('\n=== D. DealLedger broker listings (Main Street) ===')
snaps = sorted(glob.glob('/tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots/*/listings.csv'))
fr = []
for f in snaps:
    d = pd.read_csv(f, low_memory=False, usecols=lambda c: c in ('id', 'url', 'url_is_listing_specific', 'source_url', 'status',
                                                                 'asking_price', 'cash_flow', 'broker_name', 'vertical', 'state'))
    d['snap'] = pd.to_datetime(f.split('/')[-2]); fr.append(d)
DL = pd.concat(fr, ignore_index=True)
DL['url'] = DL['url'].fillna(DL['source_url'])                     # revision 2's (wrong) key
DL['st'] = DL.status.astype(str).str.lower()                       # missing where a snapshot has no status column
for c in ['asking_price', 'cash_flow']:
    DL[c] = pd.to_numeric(DL[c], errors='coerce')
DL['spec'] = DL.url_is_listing_specific.map(lambda v: np.nan if pd.isna(v) else float(str(v) in ('True', '1', '1.0')))
DL_R2 = DL.sort_values('snap')                                     # revision 2's row order (default sort): its replica only
# MAIN PANEL: one record per (snapshot, listing id). A card can appear twice on one broker page (featured strip and
# list), and the duplicates sometimes disagree, so a 'first row' rule would depend on the sort. Deterministic rule:
# sold if any row of the snapshot says sold, ask and cash flow = median of the positive values, other fields from
# the first row in file order.
DL['_row'] = np.arange(len(DL))
for c in ['asking_price', 'cash_flow']:
    DL.loc[~(DL[c] > 0), c] = np.nan
_W = DL[DL['id'].notna()].sort_values(['snap', '_row']).assign(_sold=lambda d: (d.st == 'sold').astype(int))
_g = _W.groupby(['snap', 'id'], sort=True)
DLP = pd.DataFrame(dict(any_sold=_g._sold.max(), st=_g.st.first(), asking_price=_g.asking_price.median(), cash_flow=_g.cash_flow.median(),
                        broker_name=_g.broker_name.first(), vertical=_g.vertical.first(), state=_g.state.first(), spec=_g.spec.mean(),
                        url=_g.url.first(), rows=_g.size())).reset_index()
DLP.loc[DLP.any_sold == 1, 'st'] = 'sold'
DLP['id_'] = DLP['id']
DUPCELLS = dict(cells=len(DLP), cells_with_duplicate_rows=int((DLP.rows > 1).sum()),
                cells_with_conflicting_status=int((_g.st.nunique() > 1).sum()))
# The listing key. The scraper's `id` is sha256(detail URL) when the card links to its own page, else
# sha256(broker domain | title); a directory page shared by many cards therefore does NOT merge them under one id,
# while the URL does (revision 2 keyed on the URL). Checks: listing-specific URLs carrying more than one id, and
# ids whose ask changes across snapshots (the id must survive a price change).
spec_rows = DL.spec == 1
DLCHK = dict(rows=len(DL), null_id_rows=int(DL['id'].isna().sum()),
             listing_specific_urls_with_gt1_id=int((DL[spec_rows].groupby('url')['id'].nunique() > 1).sum()),
             listing_specific_urls=int(DL[spec_rows].url.nunique()),
             ids_with_gt1_distinct_ask=int((DL[DL.asking_price > 0].groupby('id').asking_price.nunique() > 1).sum()),
             ids=int(DL['id'].nunique()))
# 'sold' is recorded only from this snapshot on: before it every row reads 'active', so a listing could not be
# observed to sell and is not at risk of an OBSERVED sale. Revision 2 counted exposure from the first snapshot (Feb).
T0_DL = DL.loc[DL.st == 'sold', 'snap'].min()
DLCHK.update(first_sold_status_snapshot=str(T0_DL.date()), share_rows_status_missing_in_window=float(DL[DL.snap >= T0_DL].st.isna().mean()),
             snapshots_in_window=int(DL[DL.snap >= T0_DL].snap.nunique()), window_end=str(DL.snap.max().date()))
DLCHK.update(DUPCELLS)
say('  DealLedger checks:', json.dumps(DLCHK))


def dl_build(keycol, window=True, panel=None):
    """one row per listing: entry = first snapshot (in the risk window), ask at entry, cash flow, sold = first
    'sold' snapshot; listings already 'sold' at entry are dropped; only brokers that ever mark a sale"""
    panel = DLP if panel is None else panel
    D = panel[panel[keycol].notna()].copy(); D['key'] = D[keycol]
    if window:
        D = D[D.snap >= T0_DL]
    g = D.groupby('key')
    fs = D[D.st == 'sold'].groupby('key').snap.min()
    Q_ = pd.DataFrame(dict(first=g.snap.min(), last=g.snap.max(), nsnap=g.snap.nunique(), st0=g.st.first(), ask0=g.asking_price.first(),
                           cf=g.cash_flow.median(), broker=g.broker_name.last(), vertical=g.vertical.last(), state=g.state.last(),
                           spec=g.spec.mean(), n_ids=g['id_'].nunique()))
    Q_['first_sold'] = fs
    Q_ = Q_[Q_.st0 != 'sold']
    Q_['sold'] = Q_.first_sold.notna().astype(int)
    mk = Q_.groupby('broker').sold.sum()
    Q_ = Q_[Q_.broker.isin(mk[mk > 0].index)]
    Q_ = Q_[(Q_.ask0 > 0) & (Q_.cf > 0) & (Q_.nsnap > 1)].copy()
    Q_['lm'] = np.log(Q_.ask0 / Q_.cf)
    Q_ = Q_[Q_.lm.between(np.log(.5), np.log(20))].reset_index()
    # exposure: entry to the first 'sold' snapshot (event) or to the last snapshot seen (censored)
    Q_['expo'] = np.where(Q_.sold == 1, (Q_.first_sold - Q_['first']).dt.days, (Q_['last'] - Q_['first']).dt.days).clip(1)
    Q_['lexpo'] = np.log(Q_.expo)
    Q_['lcf'] = np.log(Q_.cf); Q_['lcf2'] = (Q_.lcf - Q_.lcf.mean()) ** 2
    Q_['vert'] = Q_.vertical.fillna('NA').astype(str); Q_['brk'] = Q_.broker.astype(str)
    pq, r2q = oof_ridge(Q_, Q_.lm.values, ['lcf', 'lcf2'], ['vert', 'brk'])
    Q_['rel'] = Q_.lm - pq
    Q_['rel_p'] = Q_.rel.clip(lower=0); Q_['rel_n'] = Q_.rel.clip(upper=0)
    return Q_, float(r2q)


def cindex(t, e, risk):
    """Harrell's concordance for right-censored times: among usable pairs (the shorter time is an event), the share
    in which the listing that sold first has the higher predicted rate"""
    t, e, risk = np.asarray(t, float), np.asarray(e, int), np.asarray(risk, float); num = den = 0.0
    for i in np.where(e == 1)[0]:
        m = t > t[i]
        den += m.sum(); num += (risk[i] > risk[m]).sum() + 0.5 * (risk[i] == risk[m]).sum()
    return float(num / den) if den > 0 else np.nan


POIS = sm.families.Poisson()
fDp = 'sold ~ rel_p + rel_n + lcf'


def cv_poisson(df, formulas, folds=10, reps=3, seed=SEED):
    """held-out Poisson log-likelihood (exposure offset: part of the likelihood) and, for ranking, the concordance
    index and the AUC on the predicted RATE exp(Xb) WITHOUT the offset (exposure ends at the sale, so a ranking
    that includes it measures the outcome, not the ask)"""
    out = {k: dict(ll=[], auc=[], c=[]) for k in formulas}
    for r_ in range(reps):
        for tr, te in StratifiedKFold(folds, shuffle=True, random_state=seed + r_).split(df, df.sold):
            dtr, dte = df.iloc[tr], df.iloc[te]
            for k, f in formulas.items():
                m = smf.glm(f, dtr, family=POIS, offset=dtr.lexpo).fit()
                mu = np.asarray(m.predict(dte, offset=dte.lexpo))
                rate = np.asarray(m.predict(dte, offset=np.zeros(len(dte))))
                out[k]['ll'].append(float(np.sum(dte.sold.values * np.log(np.clip(mu, 1e-12, None)) - mu)))
                if dte.sold.nunique() > 1:
                    out[k]['auc'].append(roc_auc_score(dte.sold.values, rate))
                out[k]['c'].append(cindex(dte.expo.values, dte.sold.values, rate))
    return {k: dict(heldout_poisson_loglik_per_obs=sum(v['ll']) / (len(df) * reps), cindex_rate_mean=float(np.nanmean(v['c'])),
                    auc_rate_mean=float(np.mean(v['auc'])) if v['auc'] else None) for k, v in out.items()}


def dl_fit(Q_, lab):
    r_ = fit_glm(fDp, Q_, family=POIS, cluster='brk', offset=Q_.lexpo)
    rl_ = fit_glm('sold ~ rel + lcf', Q_, family=POIS, cluster='brk', offset=Q_.lexpo)
    cv_ = cv_poisson(Q_, {'with_ask': fDp, 'no_ask': 'sold ~ lcf'})
    sb_ = Q_.groupby('brk').sold.sum().sort_values(ascending=False)
    o = dict(n=len(Q_), events=int(Q_.sold.sum()), brokers=int(Q_.brk.nunique()), beta_above=coef(r_, 'rel_p'), beta_below=coef(r_, 'rel_n'),
             beta_linear=coef(rl_, 'rel'), cv_10fold_x3=cv_, exposure_days_median_sold=float(Q_[Q_.sold == 1].expo.median()),
             exposure_days_median_unsold=float(Q_[Q_.sold == 0].expo.median()),
             share_sold_with_1day_exposure=float(np.mean(Q_[Q_.sold == 1].expo <= 1)),
             top_broker_sales=int(sb_.iloc[0]), keys_merging_gt1_id=int((Q_.n_ids > 1).sum()),
             sales_on_merged_keys=int(Q_[Q_.n_ids > 1].sold.sum()))
    say(f'  {lab:52s} n={o["n"]:4d} sales={o["events"]:3d} brokers={o["brokers"]:2d} beta_above={o["beta_above"]["est"]:+.3f} '
        f'({o["beta_above"]["se"]:.3f}) below={o["beta_below"]["est"]:+.3f}  CV LL {cv_["with_ask"]["heldout_poisson_loglik_per_obs"]:.4f} vs '
        f'{cv_["no_ask"]["heldout_poisson_loglik_per_obs"]:.4f}  C {cv_["with_ask"]["cindex_rate_mean"]:.3f} vs {cv_["no_ask"]["cindex_rate_mean"]:.3f}'
        f'  merged keys {o["keys_merging_gt1_id"]} ({o["sales_on_merged_keys"]} sales)')
    return o


Q, r2Q = dl_build('id', window=True)                                  # MAIN: listing id, at risk from the first sold-status snapshot
DLV = {'id key, at risk from the first sold-status snapshot (main)': dl_fit(Q, 'id key, risk window (main)')}
Qs_ = Q[Q.spec > 0.5].reset_index(drop=True)
DLV['id key, listing-specific URLs only'] = dl_fit(Qs_, 'id key, risk window, listing-specific URLs')
Qnw, _ = dl_build('id', window=False)
DLV['id key, exposure from the first snapshot (revision 2 exposure)'] = dl_fit(Qnw, 'id key, exposure from first snapshot')
Qu2, _ = dl_build('url', window=False, panel=DL_R2.assign(id_=DL_R2['id']))
DLV['URL key, exposure from the first snapshot (revision 2; join error)'] = dl_fit(Qu2, 'URL key (revision 2 replica)')
# the review's id-keyed sketch: raw rows (first row of a snapshot wins), exposure from the first snapshot; and the same
# with the risk window. Both carry the duplicate-card artefact: a listing that another card of the entry snapshot
# already shows as sold counts as a one-day 'sale'. Recorded, kept out of the grid.
RAWP = DL_R2[DL_R2['id'].notna()].assign(id_=lambda d: d['id'])
Qrs, _ = dl_build('id', window=False, panel=RAWP)
DLV['id key, raw rows, exposure from the first snapshot (review sketch; duplicate-card error)'] = dl_fit(Qrs, 'id key, raw rows, no window (review sketch)')
Qrw, _ = dl_build('id', window=True, panel=RAWP)
DLV['id key, raw rows, risk window (duplicate-card error)'] = dl_fit(Qrw, 'id key, raw rows, risk window')
_ent = DLP[DLP.snap >= T0_DL].sort_values('snap').groupby('id').st.first()          # status at window entry, one record per snapshot
DUP_ART = {}
for lab_, Qx in [('review_sketch', Qrs), ('raw_rows_window', Qrw)]:
    ks = Qx[Qx.sold == 1].key
    DUP_ART[lab_] = dict(sales=int(len(ks)), sales_sold_at_entry_in_main_panel=int((_ent.reindex(ks) == 'sold').sum()),
                         brokers=int(Qx.brk.nunique()), brokers_in_main=int(Qx[Qx.brk.isin(set(Q.brk))].brk.nunique()))
DLCHK['duplicate_card_artefacts'] = DUP_ART
say('  duplicate-card artefacts:', json.dumps(DUP_ART))
assert DLV['id key, at risk from the first sold-status snapshot (main)']['keys_merging_gt1_id'] == 0
DLM = DLV['id key, at risk from the first sold-status snapshot (main)']
RES['D_dealledger_main_street'] = dict(n=len(Q), events=int(Q.sold.sum()), brokers=int(Q.brk.nunique()), hedonic_oof_r2=r2Q,
                                       share_directory_page_listings=float(np.mean(Q.spec <= 0.5)), checks=DLCHK,
                                       main_exposure_offset=dict(formula=fDp + ' + offset(log exposure)', family='Poisson (exponential hazard)', **DLM),
                                       variants=DLV, exposure_days_median_sold=DLM['exposure_days_median_sold'],
                                       exposure_days_median_unsold=DLM['exposure_days_median_unsold'],
                                       share_sold_with_1day_exposure=DLM['share_sold_with_1day_exposure'],
                                       top_broker_sales=DLM['top_broker_sales'], top_broker_share_of_sales=DLM['top_broker_sales'] / max(1, DLM['events']),
                                       note=('listings keyed by id; at risk from the first snapshot that records a sold status; only brokers that ever mark '
                                             'a listing sold; ask = the ask at entry to the risk window'))
say(json.dumps({k: v for k, v in RES['D_dealledger_main_street'].items() if k not in ('variants', 'main_exposure_offset')}, indent=1))

# =============================================================================================
# E. IBBA band x quarter: realized/ask vs months listing -> close (ecological)
# =============================================================================================
say('\n=== E. IBBA Market Pulse band x quarter ===')
H_ = pd.read_csv(f'{D5}/aggregates_research/clean/ibba_mp_band_histograms_long.csv')
H_ = H_[H_.measure == 'listing_to_close_months'].copy()
H_['mid'] = np.where(H_.cat_hi.isna(), 30.0, np.where(H_.cat_lo == H_.cat_hi, H_.cat_lo + 0.5, (H_.cat_lo + H_.cat_hi) / 2))
H_.loc[H_.cat_lo == 0, 'mid'] = 0.5


def cell_stats(g):
    w = g.pct.values / g.pct.sum(); m = g['mid'].values; o = np.argsort(m); cw = np.cumsum(w[o])
    return pd.Series(dict(mean_log_months=float(np.sum(w * np.log(m))), median_months=float(m[o][np.searchsorted(cw, .5)]),
                          n_closed=float(g.n_closed.iloc[0]) if g.n_closed.notna().any() else np.nan))


HC = H_.groupby(['period', 'band']).apply(cell_stats).reset_index()
RAi = pd.read_csv(f'{D5}/aggregates_research/clean/ibba_mp_realized_to_ask_panel.csv')
RAi = RAi[RAi.stat == 'average'][['period', 'band', 'pct_of_ask_or_benchmark']]
EC = HC.merge(RAi, on=['period', 'band'])
EC['l_ask_over_price'] = -np.log(EC.pct_of_ask_or_benchmark / 100)    # log(ask / realized price)
EC = EC.dropna(subset=['mean_log_months', 'l_ask_over_price'])
rE = smf.ols('mean_log_months ~ l_ask_over_price + C(band) + C(period)', EC).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(EC.period)[0]})
rE2 = smf.ols('mean_log_months ~ l_ask_over_price + C(band)', EC).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(EC.period)[0]})
loqo = {'with': [], 'without': []}
for q in EC.period.unique():
    trq, teq = EC[EC.period != q], EC[EC.period == q]
    for k, f in [('with', 'mean_log_months ~ l_ask_over_price + C(band)'), ('without', 'mean_log_months ~ C(band)')]:
        m = smf.ols(f, trq).fit()
        loqo[k].append(np.sum((teq.mean_log_months - m.predict(teq)) ** 2))
RES['E_ibba_ecological'] = dict(n_cells=len(EC), n_quarters=int(EC.period.nunique()),
                                slope_band_and_quarter_FE=coef(rE, 'l_ask_over_price'),
                                slope_band_FE_only=coef(rE2, 'l_ask_over_price'),
                                loqo_mse_with=float(np.sum(loqo['with']) / len(EC)), loqo_mse_without=float(np.sum(loqo['without']) / len(EC)),
                                note='cell mean log months (histogram midpoints, >2 yr at 30) on log(ask/realized price); band-level averages: '
                                     'ecological and REVERSE-CAUSAL (slow deals get cut, so the realized/ask ratio falls because of time); '
                                     'not informative about the direction of the ask effect')
say(json.dumps(RES['E_ibba_ecological'], indent=1))
EC.to_csv(os.path.join(OUT, 'E_ibba_cells.csv'), index=False)

# =============================================================================================
# F. Synthesis
# =============================================================================================
say('\n=== F. Synthesis ===')


def to_time(beta, se_beta, k, k_se_):
    """a log sale-hazard ratio beta per log point is a log time ratio -beta/k under a Weibull PH clock of shape k"""
    return float(-beta / k), float(np.sqrt((se_beta / k) ** 2 + (beta * k_se_ / k ** 2) ** 2))


TAU0 = 0.5     # between-source sd FIXED in advance (three sources cannot estimate it), on the sale-clock scale


def pool(bs_, ses_, tau_fixed=None):
    """random effects: with tau_fixed, inverse-variance weights 1/(se^2 + tau_fixed^2) (a fixed linear combination of the
    sources, so the result is monotone in each); without, DerSimonian-Laird with a modified Hartung-Knapp SE"""
    bs_, ses_ = np.asarray(bs_, float), np.asarray(ses_, float)
    w_ = 1 / ses_ ** 2; bf = float(np.sum(w_ * bs_) / np.sum(w_)); q_ = float(np.sum(w_ * (bs_ - bf) ** 2)); kk = len(bs_)
    t2 = max(0.0, (q_ - (kk - 1)) / (np.sum(w_) - np.sum(w_ ** 2) / np.sum(w_))) if kk > 1 else 0.0
    wr_ = 1 / (ses_ ** 2 + t2); mu = float(np.sum(wr_ * bs_) / np.sum(wr_)); v_dl = float(1 / np.sum(wr_))
    v_hk = float(np.sum(wr_ * (bs_ - mu) ** 2) / ((kk - 1) * np.sum(wr_))) if kk > 1 else v_dl
    se_m = float(np.sqrt(max(v_dl, v_hk)))
    tq = stats.t.ppf(.975, max(kk - 1, 1))
    wf = 1 / (ses_ ** 2 + (TAU0 if tau_fixed is None else tau_fixed) ** 2)
    mu_f, se_f = float(np.sum(wf * bs_) / np.sum(wf)), float(np.sqrt(1 / np.sum(wf)))
    return dict(re_fixed_tau=mu_f, se_fixed_tau=se_f, weights_fixed_tau=(wf / np.sum(wf)).tolist(), fe=bf, se_fe=float(np.sqrt(1 / np.sum(w_))),
                Q=q_, tau=float(np.sqrt(t2)), re=mu, se_dl=float(np.sqrt(v_dl)), se_hk=float(np.sqrt(v_hk)), se_mhk=se_m,
                hk_ci95=[mu - tq * se_m, mu + tq * se_m])


# Transfer to brokered Main-Street deals: b_MS ~ N(b_analog, se^2 + DELTA^2), prior b_MS ~ N(0, PRIOR_SD^2) at the
# current model value (time ignores the ask). Both on the CONSOLE's scale (time to close | close), fixed in advance.
PRIOR_SD, DELTA = 0.5, 0.5


def shrink(mu, se, prior_sd=PRIOR_SD, delta=DELTA):
    v_ = se ** 2 + delta ** 2
    wgt = prior_sd ** 2 / (prior_sd ** 2 + v_)
    return float(mu * wgt), float(np.sqrt(1 / (1 / prior_sd ** 2 + 1 / v_))), float(wgt)


# ---- the console's estimand. tMed is the median time to close AMONG DEALS THAT CLOSE. With competing risks (sale,
# withdrawal), proportional hazards and a common clock shape, the time to sale given sale has the distribution of
# the time to ANY exit, whose hazard is h_s + h_w, so
#     d ln(T | close) / d ln rho = P(close) x (sale-clock elasticity) + (1 - P(close)) x (withdrawal-clock elasticity),
# with clock elasticity = -d ln hazard / k. The sources measure different things: EF's slope is time | sale at EF's
# sell-through; Flippa's and DealLedger's are sale-hazard (clock) elasticities. All three are put on the clock scale,
# pooled, and converted with the console's own P_C at value (withdrawal unaffected) BEFORE shrinkage. Because a
# window hazard cannot separate a slower clock from a larger never-sells fraction, the converted value is an upper
# bound on the time channel; the never-sells channel is the console's Pepperdine P_C penalty.
PCQ = node(f"""const A=require({json.dumps(HARNESS)}).load([]); const pc=[],loi=[];
for(const ind of Object.keys(A.IND)) for(const ern of [1.5e5,4e5,1.45e6,5e6]){{
  const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/A.typMargin(ind,ern);
  const s={{ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40}};
  const V=A.model({{...s,ask:1}}).V, r=A.model({{...s,ask:V}}); pc.push(r.PC); loi.push(r.ft.loi*30.44/r.ft.days); }}
console.log(JSON.stringify({{pc,loi}}));""")
PC_V, PC_LO, PC_HI = float(np.median(PCQ['pc'])), float(np.min(PCQ['pc'])), float(np.max(PCQ['pc']))
LOI_SHARE = float(np.median(PCQ['loi'])); LOI_RNG = (float(np.min(PCQ['loi'])), float(np.max(PCQ['loi'])))
SB = pd.read_csv(f'{D5}/extra_wayback_retry_aggregates/clean/ef_scoreboard_cc_series.csv')
sbp = pd.to_numeric(SB.pct_of_listings_sold, errors='coerce').dropna() / 100
P_EF, P_EF_LO, P_EF_HI = float(sbp.median()), float(sbp.min()), float(sbp.max())
S_FL = float(A.sold.sum() / (A.sold.sum() + A.ended.sum()))       # Flippa: share of exits within the window that are sales
bw_, bw_se_ = MN['ended_vs_open']['est'], MN['ended_vs_open']['se']
say(f'  console P_C at value over {len(PCQ["pc"])} median businesses: median {PC_V:.3f} ({PC_LO:.3f}-{PC_HI:.3f}); LOI->close share of the band '
    f'median {LOI_SHARE:.2f} ({LOI_RNG[0]:.2f}-{LOI_RNG[1]:.2f}); EF sell-through {P_EF:.2f} ({P_EF_LO:.2f}-{P_EF_HI:.2f}, n={len(sbp)} scoreboard '
    f'captures); Flippa sale share of exits {S_FL:.3f}; Flippa withdrawal (ended) slope {bw_:.3f} ({bw_se_:.3f})')

kF_hat, (kF_lo, kF_hi) = FLIPPA_K['k_hat'], FLIPPA_K['ci95']
kF_se = (kF_hi - kF_lo) / (2 * 1.96)
cf = lambda lab: CE[lab]['coef']['rho_sale_l']
# EF time-given-sale slopes (variants); SEs floored at the main entry's estimator-robust SE so that choosing an
# estimator never raises EF's weight
EF_TS = {
    'linear Weibull (main)': (ef_lin['est'], ef_lin_se),
    'linear, right-truncation corrected': (cf('linear_truncation_corrected|weibull')['est'], max(ef_lin_se, cf('linear_truncation_corrected|weibull')['se'])),
    'linear, winsorised 1-99': (cf('linear_winsor_1_99|weibull')['est'], max(ef_lin_se, cf('linear_winsor_1_99|weibull')['se'])),
    'linear, winsorised 5-95': (cf('linear_winsor_5_95|weibull')['est'], max(ef_lin_se, cf('linear_winsor_5_95|weibull')['se'])),
    'linear, trimmed 5-95': (cf('linear_trim_5_95|weibull')['est'], max(ef_lin_se, cf('linear_trim_5_95|weibull')['se'])),
    'linear, top 2.5% of asks dropped': (cf('linear_drop_top_2p5|weibull')['est'], max(ef_lin_se, cf('linear_drop_top_2p5|weibull')['se'])),
    'linear, bottom 2.5% of asks dropped': (cf('linear_drop_bottom_2p5|weibull')['est'], max(ef_lin_se, cf('linear_drop_bottom_2p5|weibull')['se'])),
    'linear, OLS on log days': (cf('linear|lognormal')['est'], max(ef_lin_se, cf('linear|lognormal')['se'])),
    'linear, median regression': (cf('linear|median_regression')['est'], max(ef_lin_se, cf('linear|median_regression')['se'])),
    'monotone component (hinge above + below)': (ef_lo_, max(ef_lin_se, bootE['monotone_component_se'])),
    'hinge above the median premium (upper end)': (ef_hi, max(ef_lin_se, mainH['coef']['rho_sale_p']['se'], bootE['hinge_above_se'])),
}
EF_V = {k: (v[0] / P_EF, v[1] / P_EF) for k, v in EF_TS.items()}          # clock scale: time | sale = clock x sell-through
FL_RAW = {
    'regression-calibrated, non-reference listings (main)': (bA_rc, seA_rc, k_mkt, k_se),
    'uncorrected': (bA, seA, k_mkt, k_se),
    'calibrated as revision 2 (whole sample / 0.93)': (bA_rc2, seA_rc2, k_mkt, k_se),
    'uniform reconstruction, calibrated': (float(rA_u.params['ucal_p']), max(float(rA_u.bse['ucal_p']), seA_rc), k_mkt, k_se),
    'non-reference listings only, calibrated': (float(rA_nr.params['cal_p']), max(float(rA_nr.bse['cal_p']), seA_rc), k_mkt, k_se),
    'classical reliability (revision 1)': (bA_cl, seA_cl, k_mkt, k_se),
    'calibrated, Flippa profile k': (bA_rc, seA_rc, kF_hat, kF_se),
    'calibrated, Flippa k at its CI low': (bA_rc, seA_rc, kF_lo, 0.0),
    'calibrated, Flippa k at its CI high': (bA_rc, seA_rc, kF_hi, 0.0),
    'classical reliability, Flippa k at its CI low (upper end)': (bA_cl, seA_cl, kF_lo, 0.0),
    'uncorrected, Flippa k at its CI high (lower end)': (bA, seA, kF_hi, 0.0),
}
FL_V = {k: to_time(*v) for k, v in FL_RAW.items()}
dl_main_key = 'id key, at risk from the first sold-status snapshot (main)'
DL_RAW = {k: (v['beta_above']['est'], v['beta_above']['se']) for k, v in DLV.items()}
# exponential hazard (k = 1): time entry -beta. Revision 2's URL-keyed entry is a join error, kept out of the grid
DL_V = {k: (-v[0], v[1]) for k, v in DL_RAW.items() if 'error' not in k}
DL_V['excluded'] = None
DL_REV2 = [(-v[0], v[1]) for k, v in DL_RAW.items() if 'join error' in k][0]
DL_REVIEW = [(-v[0], v[1]) for k, v in DL_RAW.items() if 'review sketch' in k][0]
POOLS = ['random effects, between-source sd fixed at 0.5 (main)', 'DerSimonian-Laird random effects, modified HK SE', 'fixed effect']
CONVS = {
    'x P_C at value, median business (main)': dict(f=PC_V),
    'x P_C at value, lowest across businesses': dict(f=PC_LO),
    'x P_C at value, highest across businesses': dict(f=PC_HI),
    'x P_C, plus Flippa\'s withdrawal slope for (1 - P_C)': dict(f=PC_V, add=(1 - PC_V) * (-bw_ / k_mkt), add_se=(1 - PC_V) * bw_se_ / k_mkt),
    'x P_C x marketing share (LOI-to-close leg unaffected)': dict(f=PC_V * (1 - LOI_SHARE)),
    'EF sell-through 0.88 instead of the median': dict(f=PC_V, p_ef=P_EF_LO),
    'EF sell-through 0.95 instead of the median': dict(f=PC_V, p_ef=P_EF_HI),
    'time | sale on each source\'s own scale (Flippa at its own sale share)': dict(f=1.0, own_scale=True),
    'no conversion (revision 2: sale-clock elasticity used as T_ELAST)': dict(f=1.0),
}
MAIN = ('linear Weibull (main)', 'regression-calibrated, non-reference listings (main)', dl_main_key, POOLS[0], 'x P_C at value, median business (main)')


def entries(ef, fl, dl, conv):
    c_ = CONVS[conv]
    if c_.get('own_scale'):
        bF, sF, kF_, ksF = FL_RAW[fl]
        fl_ts = -(S_FL * bF + (1 - S_FL) * bw_) / kF_
        fl_ts_se = float(np.sqrt((S_FL * sF / kF_) ** 2 + ((1 - S_FL) * bw_se_ / kF_) ** 2))
        ent = [EF_TS[ef], (fl_ts, fl_ts_se)] + ([(DL_V[dl][0] * PC_V, DL_V[dl][1] * PC_V)] if DL_V[dl] is not None else [])
        return ent
    pe = c_.get('p_ef', P_EF)
    ent = [(EF_TS[ef][0] / pe, EF_TS[ef][1] / pe), FL_V[fl]] + ([DL_V[dl]] if DL_V[dl] is not None else [])
    return ent


def run_spec(ef, fl, dl, pm, conv, prior_sd=PRIOR_SD, delta=DELTA, delta_rule=None, fl_scale=1.0):
    ent = entries(ef, fl, dl, conv)
    ent[1] = (ent[1][0] * fl_scale, ent[1][1])
    p_ = pool([e[0] for e in ent], [e[1] for e in ent])
    mu_c, se_c = {POOLS[0]: (p_['re_fixed_tau'], p_['se_fixed_tau']), POOLS[1]: (p_['re'], p_['se_mhk']), POOLS[2]: (p_['fe'], p_['se_fe'])}[pm]
    c_ = CONVS[conv]
    mu = mu_c * c_['f'] + c_.get('add', 0.0)
    se = float(np.sqrt((se_c * c_['f']) ** 2 + c_.get('add_se', 0.0) ** 2))
    dlt = {'0.5|mu|': 0.5 * abs(mu), 'tau': p_['tau'] * c_['f']}.get(delta_rule, delta)
    b_, sd_, w_ = shrink(mu, se, prior_sd, dlt)
    return dict(EF=ef, Flippa=fl, DealLedger=dl, pooling=pm, conversion=conv, prior_sd=prior_sd, delta=dlt, delta_rule=delta_rule or 'fixed',
                pooled_clock=mu_c, pooled_clock_se=se_c, pooled=mu, pooled_se=se, tau=p_['tau'], weights=p_['weights_fixed_tau'],
                weight=w_, T_ELAST=b_, posterior_sd=sd_)


ent0 = entries(*MAIN[:3], MAIN[4])
S_ = pd.DataFrame([dict(source='EF first ask vs fair sale value: linear Weibull AFT of days on market | sale, / EF sell-through', b=ent0[0][0], se=ent0[0][1],
                        n=len(E), time_given_sale=EF_TS[MAIN[0]][0], time_given_sale_se=EF_TS[MAIN[0]][1]),
                   dict(source='Flippa March-2026 cloglog sale hazard, regression-calibrated, -beta/k (k from EF)', b=ent0[1][0], se=ent0[1][1], n=len(A)),
                   dict(source='DealLedger Main Street, exponential sale hazard (id key, risk window), -beta', b=ent0[2][0], se=ent0[2][1], n=len(Q))])
PM = pool(S_.b.values, S_.se.values)
say(S_.round(4).to_string())
say('  pooled sale-clock elasticity:', json.dumps({k: (np.round(v, 4).tolist() if isinstance(v, list) else round(v, 4)) for k, v in PM.items()}))
MAINSPEC = run_spec(*MAIN)
b_post, sd_post, w_post = MAINSPEC['T_ELAST'], MAINSPEC['posterior_sd'], MAINSPEC['weight']
T_REC = float(np.round(b_post / 0.05) * 0.05)        # a labelled judgment: rounded to 0.05, no false precision
W_SRC = dict(zip(['EF', 'Flippa', 'DealLedger'], MAINSPEC['weights']))
CONTRIB = {k: float(w_post * PC_V * W_SRC[k] * S_.b.iloc[i]) for i, k in enumerate(['EF', 'Flippa', 'DealLedger'])}
say(f'  main: pooled clock {MAINSPEC["pooled_clock"]:.3f} (SE {MAINSPEC["pooled_clock_se"]:.3f}), weights {json.dumps({k: round(v, 3) for k, v in W_SRC.items()})}; '
    f'x P_C {PC_V:.3f} = {MAINSPEC["pooled"]:.3f} (SE {MAINSPEC["pooled_se"]:.3f}); weight on the analogs {w_post:.3f} -> {b_post:.3f} '
    f'(posterior sd {sd_post:.3f}); contributions {json.dumps({k: round(v, 3) for k, v in CONTRIB.items()})}; recommended T_ELAST = {T_REC:g}')
# leave-one-source-out (main pooling and conversion)
loo = {}
for i, s_ in S_.iterrows():
    p_ = pool(S_.b.drop(i).values, S_.se.drop(i).values)
    mu_, se_ = p_['re_fixed_tau'] * PC_V, p_['se_fixed_tau'] * PC_V
    loo[s_.source] = dict(pooled_clock=p_['re_fixed_tau'], se_clock=p_['se_fixed_tau'], pooled=mu_, se=se_, shrunk=shrink(mu_, se_)[0])
LOO_NOFL = [v['shrunk'] for k, v in loo.items() if k.startswith('Flippa')][0]
say('  leave-one-source-out:', json.dumps({k.split(' ')[0]: round(v['shrunk'], 3) for k, v in loo.items()}))
# what revision 2's URL-keyed DealLedger entry would give in this chain (it is a join error; for the record)
p_r2 = pool([ent0[0][0], ent0[1][0], DL_REV2[0]], [ent0[0][1], ent0[1][1], DL_REV2[1]])
REV2_DL_IN_CHAIN = shrink(p_r2['re_fixed_tau'] * PC_V, p_r2['se_fixed_tau'] * PC_V)[0]
p_rv = pool([ent0[0][0], ent0[1][0], DL_REVIEW[0]], [ent0[0][1], ent0[1][1], DL_REVIEW[1]])
REVIEW_DL_IN_CHAIN = shrink(p_rv['re_fixed_tau'] * PC_V, p_rv['se_fixed_tau'] * PC_V)[0]
# specification grid: every combination of the data choices (EF entry, Flippa entry, DealLedger entry, pooling,
# conversion) at the main prior and transfer sd; and one-at-a-time departures from the main specification
GRIDS = pd.DataFrame([run_spec(ef, fl, dl, pm, cv) for ef in EF_V for fl in FL_V for dl in DL_V for pm in POOLS for cv in CONVS])
one = [MAINSPEC]
for ef in EF_V:
    if ef != MAIN[0]: one.append(run_spec(ef, *MAIN[1:]))
for fl in FL_V:      # the two bracket ends change two choices at once (correction and k): grid only
    if fl != MAIN[1] and 'end)' not in fl: one.append(run_spec(MAIN[0], fl, *MAIN[2:]))
for dl in DL_V:
    if dl != MAIN[2]: one.append(run_spec(MAIN[0], MAIN[1], dl, *MAIN[3:]))
for pm in POOLS[1:]:
    one.append(run_spec(*MAIN[:3], pm, MAIN[4]))
for cv in CONVS:
    if cv != MAIN[4]: one.append(run_spec(*MAIN[:4], cv))
ONE = pd.DataFrame(one)
SPEC_LO, SPEC_HI = float(ONE.T_ELAST.min()), float(ONE.T_ELAST.max())
LOSO_MIN, LOSO_MAX = min(v['shrunk'] for v in loo.values()), max(v['shrunk'] for v in loo.values())
RANGE_LO = float(np.floor(min(SPEC_LO, LOSO_MIN) * 100 + 1e-9) / 100)      # rounded outward to 0.01
RANGE_HI = float(np.ceil(max(SPEC_HI, LOSO_MAX) * 100 - 1e-9) / 100)
GRID_P = GRIDS.T_ELAST.quantile([0.05, 0.5, 0.95]).tolist()
say(ONE[['EF', 'Flippa', 'DealLedger', 'pooling', 'conversion', 'pooled_clock', 'pooled', 'pooled_se', 'T_ELAST']].round(3).to_string())
say(f'  one-at-a-time specification range {SPEC_LO:.3f}..{SPEC_HI:.3f}; leave-one-source-out {LOSO_MIN:.3f}..{LOSO_MAX:.3f}; stated '
    f'{RANGE_LO:.2f}-{RANGE_HI:.2f}; full grid ({len(GRIDS)} combinations) min {GRIDS.T_ELAST.min():.3f}, 5/50/95% '
    f'{GRID_P[0]:.3f}/{GRID_P[1]:.3f}/{GRID_P[2]:.3f}, max {GRIDS.T_ELAST.max():.3f}; revision 2 URL-keyed DealLedger in this chain {REV2_DL_IN_CHAIN:.3f}')
# shrinkage sensitivity: prior sd and transfer sd (rule) at the main data choices
SENS = pd.DataFrame([run_spec(*MAIN, prior_sd=psd, delta=dl_, delta_rule=rule)
                     for psd in (0.25, 0.5, 1.0) for dl_, rule in [(0.25, None), (0.5, None), (0.75, None), (None, '0.5|mu|'), (None, 'tau')]])
say(SENS[['prior_sd', 'delta_rule', 'delta', 'weight', 'T_ELAST', 'posterior_sd']].round(3).to_string())
# monotonicity of the rule in the evidence: scale the Flippa entry and watch the recommendation
MONO = pd.DataFrame([dict(flippa_scale=fac, main_rule=run_spec(*MAIN, fl_scale=fac)['T_ELAST']) for fac in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)])
say(MONO.round(3).to_string())
assert (np.diff(MONO.main_rule.values) > 0).all()
# the same chain at higher asks: the console's P_C falls with the ask, so the time | close elasticity falls too; a
# constant T_ELAST (at the P_C at value) is the upper end there. Shrunk the same way on both sides.
STRUCT = {}
for m_ in (1.0, 1.2, 1.5, 2.0):
    f_ = PC_V * float(pc_ratio_model([m_])[0])
    mu_, se_ = MAINSPEC['pooled_clock'] * f_, MAINSPEC['pooled_clock_se'] * f_
    STRUCT[f'{m_:g}'] = dict(P_C=f_, b_T_given_close=mu_, shrunk=shrink(mu_, se_)[0])
say('  chain at higher asks (pooled clock x console P_C(rho), shrunk):', json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in STRUCT.items()}))
GRIDS.drop(columns=['weights']).to_csv(os.path.join(OUT, 'F_specification_grid.csv'), index=False)
ONE.to_csv(os.path.join(OUT, 'F_one_at_a_time.csv'), index=False)
SENS.to_csv(os.path.join(OUT, 'F_shrinkage_sensitivity.csv'), index=False)
H_SMOOTH = 0.10
RES['F_synthesis'] = dict(sources_clock_scale=S_.to_dict('records'), pooling_main=PM, weights_main=W_SRC, contributions_to_shrunk_value=CONTRIB,
                          conversion=dict(P_C_at_value_median=PC_V, P_C_range=[PC_LO, PC_HI], n_businesses=len(PCQ['pc']), EF_sell_through=P_EF,
                                          EF_sell_through_range=[P_EF_LO, P_EF_HI], flippa_sale_share_of_exits=S_FL,
                                          loi_share_of_band_median=LOI_SHARE, loi_share_range=list(LOI_RNG)),
                          leave_one_source_out=loo, revision2_url_keyed_dealledger_in_this_chain=REV2_DL_IN_CHAIN,
                          review_sketch_dealledger_in_this_chain=REVIEW_DL_IN_CHAIN,
                          shrinkage=dict(prior_mean=0.0, prior_sd=PRIOR_SD, transfer_sd_fixed=DELTA, weight_on_data=w_post,
                                         posterior=dict(est=b_post, sd=sd_post)),
                          specification_one_at_a_time=ONE.to_dict('records'),
                          specification_range=dict(one_at_a_time=[SPEC_LO, SPEC_HI], leave_one_source_out=[LOSO_MIN, LOSO_MAX], stated=[RANGE_LO, RANGE_HI]),
                          specification_grid_summary=dict(n=len(GRIDS), min=float(GRIDS.T_ELAST.min()), p05=GRID_P[0], p50=GRID_P[1],
                                                          p95=GRID_P[2], max=float(GRIDS.T_ELAST.max())),
                          shrinkage_sensitivity=SENS.to_dict('records'), monotonicity_check=MONO.to_dict('records'),
                          chain_at_higher_asks=STRUCT,
                          recommended=dict(T_ELAST=T_REC, T_ELAST_posterior_sd=sd_post, T_SMOOTH=H_SMOOTH,
                                           label='labelled judgment anchored on the analogs\' sign'),
                          flippa_time_entry_variants={k: dict(b=v[0], se=v[1]) for k, v in FL_V.items()},
                          ef_entry_variants={k: dict(time_given_sale=EF_TS[k][0], se=EF_TS[k][1], clock=v[0], clock_se=v[1]) for k, v in EF_V.items()},
                          dealledger_entry_variants={k: (dict(b=v[0], se=v[1]) if v else None) for k, v in DL_V.items()})

# ---------------------------------------------------------------------------------------------
# the exact change to index.html
# ---------------------------------------------------------------------------------------------
fl_main_b, fl_main_se = FL_V[MAIN[1]]
FL_RNG = (min(v[0] for v in FL_V.values()), max(v[0] for v in FL_V.values()))
q4E = CE['quintile_dummies_vs_q2|weibull']['coef']['q4']
dlm_ = RES['D_dealledger_main_street']; dlb_ = dlm_['main_exposure_offset']['beta_above']
CONST_LINE = f'const T_ELAST={T_REC:g}, T_SMOOTH={H_SMOOTH:g};'
JS_CONST = (
    "/* Overpricing costs time - a LABELLED JUDGMENT, not a Main-Street estimate (fit/overpricing_time.py, Oct 2026).\n"
    "   Above model value the band median (fitTiming: deals sold at their usual ask) is stretched by\n"
    "   e^{T_ELAST*h}, h = ln(ask/V) with its first T_SMOOTH rounded (Huber): exactly 1 at or below value,\n"
    "   continuous with a continuous slope at value (no optimiser sits on a kink), log-linear above. It\n"
    f"   stretches the WHOLE listing-to-close median, LOI-to-close included (about {LOI_SHARE:.0%} of it), which the\n"
    "   analogs barely measure: their clocks time the marketing leg.\n"
    f"   Evidence as sale-clock elasticities. Flippa ({len(A):,} listings, 219-day window): sale hazard {bA:.2f} per log\n"
    f"   point above comparables, {bA_rc:.2f} with the reconstructed asks calibrated, {fl_main_b:.2f} in time. Empire Flippers\n"
    f"   ({len(E):,} sold listings): time to sale {ef_lin['est']:.2f} (SE {ef_lin_se:.2f}; {EF_EST_RNG[0]:.2f} to {EF_EST_RNG[1]:.2f} across estimators\n"
    "   and outlier trims; only the top fifth of first asks is robustly slower), no gain in the 2023-25\n"
    f"   hold-out. DealLedger broker listings (Main Street, {dlm_['n']} listings, {dlm_['events']} sales): {dlb_['est']:+.2f} (SE {dlb_['se']:.2f}),\n"
    f"   no predictive power. Pooled with a between-source sd of {TAU0:g} (weights EF {W_SRC['EF']:.2f}, Flippa {W_SRC['Flippa']:.2f},\n"
    f"   DealLedger {W_SRC['DealLedger']:.2f}): {MAINSPEC['pooled_clock']:.2f}; times P_C at value {PC_V:.2f} (time to close among deals that\n"
    f"   close) = {MAINSPEC['pooled']:.2f}; shrunk toward zero (prior sd {PRIOR_SD:g}, transfer sd {DELTA:g}) = {b_post:.2f}; rounded.\n"
    "   The size rests on Flippa's window hazard, which also counts listings that never sell, so as a\n"
    f"   time effect it is an upper bound that overlaps the Pepperdine P_C penalty; without Flippa the rule\n"
    f"   gives {LOO_NOFL:.2f}. Specification range {RANGE_LO:.2f}-{RANGE_HI:.2f}. */\n"
    f"{CONST_LINE}\n"
    "function timeMult(ask,val){\n"
    "  if(!(ask>0&&val>0)) return 1;\n"
    "  const x=Math.log(ask/val);\n"
    "  if(!(x>0)) return 1;\n"
    "  const h=x<T_SMOOTH?x*x/(2*T_SMOOTH):x-T_SMOOTH/2;\n"
    "  return Math.exp(T_ELAST*h);\n"
    "}\n")
TBAND_JS = (
    "  /* Overpricing costs time (T_ELAST, a labelled judgment). The band stays keyed on Vbase, so the size\n"
    "     band never moves with the ask; only the gap between the ask and model value stretches the band\n"
    "     median, and the curve is scaled with it, whatever its family. (Named tMedA so that\n"
    "     fit/time_to_close_shape.py can also be applied after this change.) */\n"
    "  out.tMult=timeMult(s.ask,out.V);\n"
    "  const tMedA=FT.days*out.tMult;\n")
OPTNOTE_JS = r'''/* The note under the two listing cards, written from the optimiser's own objective with the cost of
   delay included. Above model value a higher ask lengthens the time to close (timeMult), so a cost of
   delay can pull the walk-away ask BELOW the proceeds-maximising one; the note then says so instead of
   calling it "the higher price", and a gain is never printed below zero. */
function optNote(s,V,rSell,rKeep){
  const U=x=>x.EVp+(1-x.PC)*s.theta*x.V-s.lamT*x.tMed;
  const gain=Math.max(0,U(rKeep)-U(rSell)), coin=gain<Math.abs(U(rSell))*.01;
  const atEdge=s.optRho>RHO_MAX-.02, days=Math.round(Math.abs(rSell.tMed-rKeep.tMed));
  const lam=s.lamT>0?` and a cost of delay of ${money(s.lamT)} a day`:"";
  if(money(V*s.optRho)===money(V*s.rhoSell))
    return {kind:"same",gain,coin:false,text:`With ${pc(s.theta)} of value retained if the sale fails${lam}, both objectives agree on the same price. `
      +`Above model value a higher ask also lengthens the time to close, which only the second figure charges for.`};
  if(s.optRho<s.rhoSell)
    return {kind:"lower",gain,coin,text:`The cost of delay pulls the second figure below the proceeds-maximising price. `
      +`Listing at ${money(V*s.optRho)} gives up ${money(Math.max(0,rSell.EVp-rKeep.EVp))} of expected proceeds, but it is `
      +`${pp(Math.max(0,rKeep.PC-rSell.PC)).replace("+","")} more likely to close and closes ${days>=1?`about ${days} days`:"slightly"} sooner, `
      +`which at ${money(s.lamT)} a day is worth ${money(gain)} to this owner`
      +(coin?`, so the two are close to a coin toss. `:`. `)
      +`An owner who does not count the wait should use the left-hand number.`};
  return {kind:"higher",gain,coin,text:`The gap between these is the real decision. The higher price gives up `
    +`${pp(Math.max(0,rSell.PC-rKeep.PC)).replace("+","")} of closing probability and `
    +`${money(Math.max(0,rSell.EVp-rKeep.EVp))} of expected proceeds for a bigger cheque if it does close`
    +(days>=1?`, takes about ${days} days longer to close,`:``)+` and only `
    +`pays off if the owner genuinely can walk away: it assumes a failed process still leaves them `
    +`${pc(s.theta)} of the value. `
    +(coin?`Even then it is worth only ${money(gain)} more to this owner${s.lamT>0?" after the cost of delay":""}, so the two are close to a coin toss. `:"")
    +(atEdge?`It sits at ${RHO_MAX.toFixed(1)}× value, the highest ask the closing data resolve, so read it as "test the market", not as a measured optimum. `:"")
    +`A seller who must exit should use the left-hand number.`};
}
'''
TILE_JS = (
    '  { const pv=$("o_t_pv"), j=r.tMult>1.0005;   /* above value the median carries a judgment multiplier */\n'
    '    pv.className="pv "+(j?"j":"a"); pv.innerHTML="<i></i>"+(j?"aggregate × judgment":"aggregate");\n'
    '    pv.title=j?`Band median ${Math.round(r.ft.days)} days × ${r.tMult.toFixed(3)} for an ask above model value (Overpricing costs time, a labelled judgment)`:""; }\n')
JROW = (
    '        <tr><td>Overpricing time multiplier<div class="muted" style="font-size:11.5px">T_ELAST, T_SMOOTH</div></td>\n'
    '            <td class="n" style="padding-right:18px">2</td>\n'
    '            <td style="color:#ff8e7a;padding-left:6px">Median time to close above model value (sign from online-marketplace analogs, size judgment), and through it the walk-away ask when a cost of delay is set.</td></tr>\n')

# model-section edits. Variants: 'w' = the Weibull page as it is today; 'll1' = the first time_to_close_shape page
# (log-logistic scaled by FT.days). The revised time_to_close_shape page pins its curve to out.tMed, so there
# only M4 is needed and M3 finds nothing (optional); afterwards FT.days must be read exactly once (tMedA).
M_EDITS = [
    dict(label='M1 timeMult and T_ELAST before gapPenalty', variants=[('any', 'function gapPenalty(gap){', JS_CONST + 'function gapPenalty(gap){')]),
    dict(label='M2 scale the band median once, after out.ft=FT', variants=[('any', '  out.ft=FT;\n', '  out.ft=FT;\n' + TBAND_JS)]),
    dict(label='M3 the curve scale reads tMedA', optional=True,
         variants=[('w', 'const lamFit=FT.days/Math.pow(Math.log(2),1/KW);', 'const lamFit=tMedA/Math.pow(Math.log(2),1/KW);'),
                   ('ll1', 'const beta=FT.beta, tMd=FT.days;', 'const beta=FT.beta, tMd=tMedA;')]),
    dict(label='M4 the median reads tMedA', variants=[('any', 'out.tMed=FT.days;', 'out.tMed=tMedA;')]),
    dict(label='M5 first time_to_close_shape comment no longer true', optional=True,
         variants=[('ll1', 'scale to solve. Conditional on closing; nothing here reads the ask.     */',
                    'scale to solve. Conditional on closing. The ask enters only through tMedA\n'
                    '     above (timeMult): an overpriced ask stretches the band median.        */')]),
    dict(label='M6 optNote before applyAll', variants=[('any', 'function applyAll(s0,r0,keys,rho){', OPTNOTE_JS + 'function applyAll(s0,r0,keys,rho){')]),
]


def model_section(html):
    src = html[html.rindex('<script>') + 8:]
    return src[:src.index('/* ============ bar helpers')]


def apply_edits(html, edits):
    applied = []
    for e in edits:
        cnt = [(tag, html.count(a)) for tag, a, b in e['variants']]
        assert all(c <= 1 for _, c in cnt), ('anchor not unique', e['label'], cnt)
        hit = [(tag, a, b) for tag, a, b in e['variants'] if html.count(a) == 1]
        if not hit:
            assert e.get('optional'), ('no variant of this edit found', e['label'])
            applied.append([e['label'], None]); continue
        assert len(hit) == 1, ('more than one variant present', e['label'])
        tag, a, b = hit[0]
        html = html.replace(a, b); applied.append([e['label'], tag])
    return html, applied


HTML0 = open(f'{REPO}/index.html', encoding='utf-8').read()
P1M = os.path.join(OUT, 'work_model_only_patched.html')
html_m, applied_m = apply_edits(HTML0, M_EDITS)
assert model_section(html_m).count('FT.days') == 1 and 'const tMedA=FT.days*out.tMult;' in html_m
open(P1M, 'w', encoding='utf-8').write(html_m)
LOADER = os.path.join(OUT, 'loader.js')
open(LOADER, 'w').write(r'''/* load the model section of any page file, optionally with exact-substring overrides (each must occur once) */
const fs=require("fs"),vm=require("vm");
function loadFile(file,overrides){
  const html=fs.readFileSync(file,"utf8");
  let src=html.slice(html.lastIndexOf("<script>")+8);
  const cut=src.indexOf("/* ============ bar helpers"); if(cut<0) throw new Error("model section end not found"); src=src.slice(0,cut);
  for(const [a,b] of (overrides||[])){ const n=src.split(a).length-1; if(n!==1) throw new Error("override count "+n+": "+a.slice(0,80)); src=src.split(a).join(b); }
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN};
  vm.createContext(ctx);
  vm.runInContext(src+`;this.API={model,omniScore,bestRatio,optimize,fitTiming,gapPenalty,RHO_MAX,MODELS,sizeRefs,IND,typMargin,money,
    optNote:(typeof optNote==="function"?optNote:null),timeMult:(typeof timeMult==="function"?timeMult:null),
    T_ELAST:(typeof timeMult==="function"?T_ELAST:null)};`,ctx);
  return ctx.API;
}
module.exports={loadFile};
''')

EX = {"ind": "medical", "rev": 6e6, "ern": 1.45e6, "grw": .14, "gm": .64, "rec": .72, "cc": .18, "ret": .91, "plt": .38, "own": .72,
      "mgt": .36, "fin": .74, "yrs": 6, "buyers": 65, "st": None, "franchise": False, "ask": 3.24e6}
T_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6]
SIZES = [1.5e5, 4e5, 1.45e6, 5e6]
js1 = f"""
const H=require({json.dumps(HARNESS)}), Ld=require({json.dumps(LOADER)});
const A0=H.load([]), A1=Ld.loadFile({json.dumps(P1M)});
const ex={json.dumps(EX)}, SIZES={json.dumps(SIZES)};
const V=A0.model({{...ex,ask:1}}).V;
const rows=[];
for(const m of [0.5,0.8,0.95,1,1.02,1.05,1.1,1.2,1.3,1.5,2,3,10]){{
  const r0=A0.model({{...ex,ask:V*m}}), r1=A1.model({{...ex,ask:V*m}});
  rows.push({{rho:m,tMed0:r0.tMed,tMed1:r1.tMed,mult:r1.tMult,PC0:r0.PC,PC1:r1.PC,EVp0:r0.EVp,EVp1:r1.EVp,t180_0:r0.t180,t180_1:r1.t180,loi0:r0.ft.loi,loi1:r1.ft.loi}});
}}
let mono=true,maxJump=0,prev=null;
for(let m=0.5;m<=3.0001;m+=0.001){{ const t=A1.model({{...ex,ask:V*m}}).tMed; if(prev!==null){{ if(t<prev-1e-9) mono=false; maxJump=Math.max(maxJump,Math.abs(t-prev)); }} prev=t; }}
let atOrBelow=0; for(let m=0.3;m<=1.0000001;m+=0.01){{ const a=A0.model({{...ex,ask:V*m}}).tMed,b=A1.model({{...ex,ask:V*m}}).tMed; atOrBelow=Math.max(atOrBelow,Math.abs(a-b)); }}
let otherChanged=0; for(const m of [0.7,1,1.2,1.5,2.5]){{ const a=A0.model({{...ex,ask:V*m}}),b=A1.model({{...ex,ask:V*m}});
  for(const k of ['V','PC','EVp','Vmean','Vreal','Vbase']) otherChanged=Math.max(otherChanged,Math.abs(a[k]-b[k])/Math.max(1,Math.abs(a[k])));
  otherChanged=Math.max(otherChanged,Math.abs(A0.omniScore(a)-A1.omniScore(b))); }}
const d=1e-5, t1=A1.model({{...ex,ask:V}}).tMed, dR=(A1.model({{...ex,ask:V*(1+d)}}).tMed-t1)/d, dL=(t1-A1.model({{...ex,ask:V*(1-d)}}).tMed)/d;
const el=(Math.log(A1.model({{...ex,ask:V*3}}).tMed)-Math.log(A1.model({{...ex,ask:V*1.5}}).tMed))/Math.log(2);
let finite=true; for(const a of [1e-6,1,1e3,1e9,1e12]) for(const e of [5e4,1.45e6,5e7]) {{ const r=A1.model({{...ex,ern:e,rev:e/0.24,ask:a}}); if(!isFinite(r.tMed)||!isFinite(r.t180)) finite=false; }}
const opt=[]; let proceedsIdentity=0;
for(const ern of SIZES){{
  const s={{...ex,ern:ern,rev:ern/0.24}};
  const p1=A1.bestRatio(s,0,0);
  for(const lam of [0,900,4000]){{ proceedsIdentity=Math.max(proceedsIdentity,Math.abs(p1-A0.bestRatio(s,0,lam)));
    for(const th of [0,0.2,0.75]) opt.push({{ern:ern,lamT:lam,theta:th,ratio0:A0.bestRatio(s,th,lam),ratio1:A1.bestRatio(s,th,lam)}}); }}
}}
const flat=[];
for(const ern of SIZES){{
  const s={{...ex,ern:ern,rev:ern/0.24}}, Vs=A0.model({{...s,ask:1}}).V;
  const U=(A,m,lam)=>{{const r=A.model({{...s,ask:Vs*m}});return r.EVp+(1-r.PC)*0.75*r.V-lam*r.tMed;}};
  const m1=A1.bestRatio(s,0.75,900);
  flat.push({{ern:ern,V:Vs,new_opt:m1,U_old_at_1p5:U(A0,1.5,900),U_new_at_new:U(A1,m1,900),U_new_at_1p5:U(A1,1.5,900),
             U_old_at_1p15:U(A0,1.15,900),U_new_at_1p15:U(A1,1.15,900)}});
}}
// the optimiser note on the patched model, and what the old note logic (no delay in Uat) would have shown
const notes=[];
for(const ern of SIZES) for(const th of [0,0.2,0.75]) for(const lam of [0,900,4000]){{
  const s={{...ex,ern:ern,rev:ern/0.24,theta:th,lamT:lam}}, Vs=A1.model({{...s,ask:1}}).V;
  s.rhoSell=A1.bestRatio(s,0,0); s.optRho=A1.bestRatio(s,th,lam);
  const rS=A1.model({{...s,ask:Vs*s.rhoSell}}), rK=A1.model({{...s,ask:Vs*s.optRho}});
  const n=A1.optNote(s,Vs,rS,rK);
  const Uold=x=>x.EVp+(1-x.PC)*th*x.V, oldGain=Uold(rK)-Uold(rS), oldSame=A1.money(Vs*s.optRho)===A1.money(Vs*A1.bestRatio(s,0,lam));
  notes.push({{ern:ern,theta:th,lamT:lam,V:Vs,rhoSell:s.rhoSell,optRho:s.optRho,kind:n.kind,gain:n.gain,coin:n.coin,
    threshold:Math.abs(rS.EVp+(1-rS.PC)*th*rS.V-lam*rS.tMed)*.01,old_gain_without_delay:oldGain,old_coin:oldGain<Math.abs(Uold(rS))*.01,
    dDays:rS.tMed-rK.tMed,text:n.text}});
}}
// where does the patient-seller ask (theta .75) switch from the RHO_MAX corner as T_ELAST varies?
const regime=[];
for(const Tv of {json.dumps(T_GRID)}){{
  const At=Ld.loadFile({json.dumps(P1M)},[[{json.dumps(CONST_LINE)},{json.dumps(CONST_LINE)}.replace("T_ELAST={T_REC:g},","T_ELAST="+Tv+",")]]);
  for(const ern of SIZES){{ const s={{...ex,ern:ern,rev:ern/0.24}};
    regime.push({{T_ELAST:Tv,ern:ern,ratio_900:At.bestRatio(s,0.75,900),ratio_4000:At.bestRatio(s,0.75,4000)}}); }}
}}
// knife edge already in the model: the patient-seller ask at lamT = 0 on the CURRENT page, theta .70 vs .75
const knife={{th070:A0.bestRatio(ex,0.70,0),th075:A0.bestRatio(ex,0.75,0)}};
// the walk-away ask (theta .75, $900/day) across earnings on the patched page: where does it jump to the cap?
const escan=[]; for(let i=0;i<=80;i++){{ const ern=1e5*Math.pow(60,i/80); const s={{...ex,ern:ern,rev:ern/0.24}};
  escan.push({{ern:ern,ratio:A1.bestRatio(s,0.75,900),ratio_current:A0.bestRatio(s,0.75,900)}}); }}
// combined loss in a window (closing probability x share closed by t), console, relative to an ask at value
const win=[];
for(const [lab,A] of [['current',A0],['patched',A1]]){{
  const r1_=A.model({{...ex,ask:V}});
  for(const t of [219,r1_.tMed]) for(const m of [1.2,1.5,2]){{ const r=A.model({{...ex,ask:V*m}});
    win.push({{page:lab,t:t,rho:m,ratio:(r.PC*r.F(t))/(r1_.PC*r1_.F(t)),pc_ratio:r.PC/r1_.PC}}); }}
}}
console.log(JSON.stringify({{V:V,rows:rows,monotone:mono,flat:flat,max_step_tMed_days_per_0p001:maxJump,max_abs_change_at_or_below_value:atOrBelow,
  max_change_other_outputs:otherChanged,dtMed_drho_left:dL,dtMed_drho_right:dR,elasticity_1p5_to_3:el,finite_extremes:finite,opt:opt,
  proceeds_optimum_identity_max_abs_diff:proceedsIdentity,notes:notes,regime:regime,window:win,knife:knife,escan:escan}}));
"""
MC = node(js1)
ROWS = pd.DataFrame(MC['rows']); OPT = pd.DataFrame(MC['opt']); NOTES = pd.DataFrame(MC['notes']); REG = pd.DataFrame(MC['regime'])
WIN = pd.DataFrame(MC['window'])
say('  model rows (example business):'); say(ROWS.round(4).to_string())
say(f"  monotone={MC['monotone']} max step={MC['max_step_tMed_days_per_0p001']:.4f} d  change at/below value={MC['max_abs_change_at_or_below_value']}"
    f"  other outputs max change={MC['max_change_other_outputs']:.2e}  dT/drho left={MC['dtMed_drho_left']:.4f} right={MC['dtMed_drho_right']:.4f}"
    f"  elasticity 1.5->3 = {MC['elasticity_1p5_to_3']:.6f}  finite={MC['finite_extremes']}  proceeds optimum identity max diff={MC['proceeds_optimum_identity_max_abs_diff']:.2e}")
say(pd.DataFrame(MC['flat']).round(1).to_string())
say(OPT.round(4).to_string())
say(NOTES.drop(columns=['text']).round(3).to_string())
say(REG.round(3).to_string())
say(WIN.round(3).to_string())
OPT.to_csv(os.path.join(OUT, 'F_best_ratio_before_after.csv'), index=False)
NOTES.to_csv(os.path.join(OUT, 'F_optimiser_notes.csv'), index=False)
REG.to_csv(os.path.join(OUT, 'F_regime_switch.csv'), index=False)
WIN.to_csv(os.path.join(OUT, 'F_window_loss_check.csv'), index=False)
assert MC['monotone'] and MC['finite_extremes'] and MC['max_abs_change_at_or_below_value'] == 0
assert MC['max_change_other_outputs'] < 1e-9 and MC['proceeds_optimum_identity_max_abs_diff'] < 1e-9
assert abs(MC['elasticity_1p5_to_3'] - T_REC) < 1e-9

# where the patient-seller ask leaves the RHO_MAX corner (theta .75, $900/day), per size
SWITCH = {}
for ern in SIZES:
    g_ = REG[REG.ern == ern].sort_values('T_ELAST')
    below = g_[g_.ratio_900 < 1.45]
    SWITCH[int(ern)] = dict(first_T_below_1p45=(float(below.T_ELAST.min()) if len(below) else None),
                            last_T_at_corner=(float(g_[g_.ratio_900 >= 1.45].T_ELAST.max()) if (g_.ratio_900 >= 1.45).any() else None),
                            ratio_at_T_REC=float(g_[np.isclose(g_.T_ELAST, T_REC)].ratio_900.iloc[0]) if np.isclose(g_.T_ELAST, T_REC).any() else None)
say('  regime switch (theta .75, $900/day):', json.dumps(SWITCH))
rowsMC = {r['rho']: r for r in MC['rows']}
# knife edge (review): the default theta sits on the point where the patient-seller ask switches to the cap even
# without any time effect; and on the patched page the walk-away ask jumps from about 1.15x to the cap as earnings rise
ESC = pd.DataFrame(MC['escan'])
jump = ESC[(ESC.ratio >= 1.45) & (ESC.ratio.shift(1) < 1.45)]
KNIFE = dict(current_page_lamT0_theta070=MC['knife']['th070'], current_page_lamT0_theta075=MC['knife']['th075'],
             patched_jump_earnings=(float(jump.ern.iloc[0]) if len(jump) else None),
             patched_ratio_below_jump=(float(ESC[ESC.ern < jump.ern.iloc[0]].ratio.iloc[-1]) if len(jump) else None),
             patched_n_jumps=int(len(jump)), current_page_all_at_cap=bool((ESC.ratio_current >= 1.45).all()))
say('  knife edge:', json.dumps(KNIFE))
ESC.to_csv(os.path.join(OUT, 'F_walkaway_by_earnings.csv'), index=False)
RES['F_synthesis']['regime_switch'] = SWITCH
RES['F_synthesis']['knife_edge'] = KNIFE

# ---------------------------------------------------------------------------------------------
# UI edits. None of them touches a text that fit/time_to_close_shape.py anchors on (its lede, equation label,
# Model III note and ledger row), so either fit can be applied first: amendments are insertions next to those
# texts, not rewrites of them.
# ---------------------------------------------------------------------------------------------
cvL_w, cvL_n = cvE['with_rho_linear'], cvE['no_rho']
hoL_w, hoL_n = ho['with_rho_linear'], ho['no_rho']
hoLt_w, hoLt_n = ho_tr['with_rho_linear'], ho_tr['no_rho']
EF_CV_GAIN = cvL_w['loglik_per_obs'] > cvL_n['loglik_per_obs']
EF_HO_GAIN = hoL_w['loglik_per_obs'] > hoL_n['loglik_per_obs']
EF_HOT_GAIN = hoLt_w['loglik_per_obs'] > hoLt_n['loglik_per_obs']
d_cv = cvL_w['loglik_per_obs'] - cvL_n['loglik_per_obs']; d_ho = hoL_w['loglik_per_obs'] - hoL_n['loglik_per_obs']
d_hot = hoLt_w['loglik_per_obs'] - hoLt_n['loglik_per_obs']
ef_oos_txt = (f'changes the held-out log-likelihood by {d_cv:+.4f} per listing in 10-fold cross-validation and by {d_ho:+.4f} in the '
              '2023&ndash;25 hold-out (hedonic fitted on 2019&ndash;22 only): '
              + ('negligible either way' if max(abs(d_cv), abs(d_ho)) < 0.002 else ('a gain' if d_cv > 0 and d_ho > 0 else 'no consistent gain')))
dlm = RES['D_dealledger_main_street']
money_s = lambda v: (f'${v/1e6:.2f}M'.replace('.00M', 'M') if v >= 1e6 else f'${v/1e3:.0f}k')
low_ = [(e, SWITCH[int(e)]['ratio_at_T_REC']) for e in SIZES if SWITCH[int(e)]['ratio_at_T_REC'] < 1.45]
high_ = [(e, SWITCH[int(e)]['first_T_below_1p45']) for e in SIZES if SWITCH[int(e)]['ratio_at_T_REC'] >= 1.45]
sw_min = min(v['first_T_below_1p45'] for v in SWITCH.values() if v['first_T_below_1p45'] is not None)
regime_txt = ('With $900 a day of delay cost and 75% of value kept if a sale fails, the walk-away ask is '
              + (' and '.join(f'{r:.2f}&times;' for _, r in low_) + ' for earnings of ' + ' and '.join(money_s(e) for e, _ in low_) if low_ else
                 'unchanged at the 1.5&times; cap for every size shown'))
for e, t in high_:
    regime_txt += (f'; for {money_s(e)} it stays at the 1.5&times; cap and drops to about 1.15&times; only from b = {t:.2f}'
                   if t is not None else f'; for {money_s(e)} it stays at the 1.5&times; cap up to b = {max(T_GRID):.2f}')
regime_txt += (f' (the specification range ends at {RANGE_HI:.2f}). That switch is a knife edge already in the model, not a measurement of b: '
               f'with no time effect and no delay cost the patient-seller ask is {KNIFE["current_page_lamT0_theta070"]:.2f}&times; at 70% kept and '
               f'the {KNIFE["current_page_lamT0_theta075"]:.1f}&times; cap at 75% (the default). For small deals it leaves the cap at any positive b '
               f'(from {sw_min:.2f})' +
               (f', and the walk-away ask jumps from about {KNIFE["patched_ratio_below_jump"]:.2f}&times; to the cap as earnings pass about '
                f'{money_s(KNIFE["patched_jump_earnings"])}.' if KNIFE['patched_jump_earnings'] else '.'))
grid_p_txt = f'{GRID_P[0]:.2f}&ndash;{GRID_P[2]:.2f}'
DATA_TAB = (
    '<p class="note"><b>Overpricing costs time (added Oct 2026) &mdash; a labelled judgment, not a Main-Street estimate.</b> The band median above, '
    'and the curve drawn through it, hold for an ask at or below model value. Above it the median is multiplied by '
    f'e<sup>b&middot;h</sup>, where h is the log gap between the ask and model value with its first {int(H_SMOOTH*100)}% rounded '
    f'smoothly, and <b>b = {T_REC:.2f}</b> (posterior SD {sd_post:.2f}). It stretches the whole listing-to-close median, including the '
    f'LOI-to-close leg (about {LOI_SHARE:.0%} of it), which the analogs barely measure; stretching only the marketing leg would add '
    f'{LOI_SHARE:.0%} fewer days. Online-marketplace analogs fix the <b>sign</b>, not the size: an ask above comparables slows the sale. '
    f'Each source is put on one scale, the sale clock. Flippa, {len(A):,} listings followed 219 days: sale hazard &minus;{abs(bA):.2f} '
    f'(SE {seA:.2f}) per log point above comparables, &minus;{abs(bA_rc):.2f} after calibrating its reconstructed asks, {fl_main_b:.2f} in time. '
    f'Empire Flippers, {len(E):,} sold listings, first ask against a hedonic fair price: time-to-sale elasticity {ef_lin["est"]:.2f} '
    f'(SE {ef_lin_se:.2f}, the largest across estimators), {EF_EST_RNG[0]:.2f}&ndash;{EF_EST_RNG[1]:.2f} across estimators and outlier trims; '
    f'only the slowest-selling top fifth of first asks is robust (+{q4E["est"]:.2f} log-days, SE {q4E["se"]:.2f}); it {ef_oos_txt}. '
    f'DealLedger broker listings (Main Street; {dlm["n"]} listings, {dlm["events"]} sales, {dlm["brokers"]} brokers): '
    f'{"&minus;" if dlb_["est"] < 0 else "+"}{abs(dlb_["est"]):.2f} (SE {dlb_["se"]:.2f}) on the sale hazard, no predictive power. '
    f'Pooled with a between-source SD of {TAU0:g}, the weights are EF {W_SRC["EF"]:.2f}, Flippa {W_SRC["Flippa"]:.2f} and DealLedger '
    f'{W_SRC["DealLedger"]:.2f}: {MAINSPEC["pooled_clock"]:.2f} (SE {MAINSPEC["pooled_clock_se"]:.2f}). The median here counts only deals '
    f'that close, so that is multiplied by the closing probability at value ({PC_V:.2f}; competing risks): {MAINSPEC["pooled"]:.2f}, then shrunk '
    f'toward zero (prior SD {PRIOR_SD:g}, transfer SD {DELTA:g}) to {b_post:.2f} and rounded. <b>The size rests on Flippa</b>, whose window '
    'hazard also counts listings that never sell: as a time effect it is an upper bound that overlaps the Pepperdine closing-probability '
    f'penalty. Without Flippa the same rule gives {LOO_NOFL:.2f}. Changing one analysis choice at a time, or leaving one source out, gives '
    f'{RANGE_LO:.2f}&ndash;{RANGE_HI:.2f}; across all {len(GRIDS):,} combinations of choices, 5&ndash;95% {grid_p_txt}. '
    'The price penalty on the closing probability (Pepperdine) and this time effect are separate judgments that no '
    f'source identifies jointly. {regime_txt}</p>')
EQ_PREFIX = r't_{\\text{med}}=t_{\\text{band}}\\,e^{${T_ELAST}\\,h}=${tn(r.ft.days)}\\times${r.tMult.toFixed(3)}=${tn(r.tMed)}\\text{ d},\\qquad '
STRETCH_P = '        <p class="note" id="o_tstretch" style="margin:4px 0 0"></p>\n'
TILE_JS = (
    '  { const pv=$("o_t_pv"), j=r.tMult>1.0005;   /* above value the median carries a judgment multiplier */\n'
    '    pv.className="pv "+(j?"j":"a"); pv.innerHTML="<i></i>"+(j?"aggregate × judgment":"aggregate");\n'
    '    pv.title=j?`Band median ${Math.round(r.ft.days)} days × ${r.tMult.toFixed(3)} for an ask above model value (Overpricing costs time, a labelled judgment)`:"";\n'
    '    $("o_tstretch").textContent=j?`Your ask is ${Math.round((s.ask/r.V-1)*100)}% above model value, so the median here is the band\'s `\n'
    '      +`${Math.round(r.ft.days)} days × ${r.tMult.toFixed(3)} (overpricing costs time: a labelled judgment, see the Data tab).`:""; }\n')
_ns, _ne = '  /* "agree" only when the two figures on screen are the same figure */\n', '+`A seller who must exit should use the left-hand number.`;\n'
assert HTML0.count(_ns) == 1 and HTML0.count(_ne) == 1
NOTE_OLD_BLOCK = HTML0[HTML0.index(_ns):HTML0.index(_ne) + len(_ne)]
NOTE_NEW_BLOCK = ('  /* written from the optimiser\'s own objective, cost of delay included (optNote, model section) */\n'
                  '  $("o_listnote").textContent=optNote(s,r.V,rSell,rKeep).text;\n')
CROSS_ANCHOR = '    <p class="grp-title" style="margin-top:18px">Cross-source validation &mdash; added 2 Oct 2026</p>'
JTAB_ANCHOR = '      </tbody></table></div>\n\n    <p class="note" style="margin-top:14px"><b>Read the third column carefully.</b>'
PROV_SENT = 'Above model value the band median is stretched by a <b>judgment</b> multiplier (Model III, <i>Overpricing costs time</i>).\n'
U_EDITS = [
    dict(label='U1 live note under the time curve', variants=[('any', 'aria-label="Cumulative probability of closing over time"></svg>\n',
                                                               'aria-label="Cumulative probability of closing over time"></svg>\n' + STRETCH_P)]),
    dict(label='U2 the equation line shows the multiplier', variants=[('any', '  eq("eq_ts",`', '  eq("eq_ts",`' + EQ_PREFIX)]),
    dict(label='U3 tile provenance tag gets an id', variants=[('any', 'Median time to close <span class="pv a"><i></i>aggregate</span>',
                                                               'Median time to close <span class="pv a" id="o_t_pv"><i></i>aggregate</span>')]),
    dict(label='U4 tile tag and live note follow the multiplier', variants=[('any', '  $("o_t").textContent=Math.round(r.tMed)+" days";\n',
                                                                             '  $("o_t").textContent=Math.round(r.tMed)+" days";\n' + TILE_JS)]),
    dict(label='U5 rhoSell is the pure proceeds optimum', variants=[('any', 's.rhoSell=bestRatio(s,0,s.lamT);        // expected-proceeds optimum: does not',
                                                                     's.rhoSell=bestRatio(s,0,0);             // expected-proceeds optimum: reads neither theta nor the cost of delay')]),
    dict(label='U6 optimiser note from optNote()', variants=[('any', NOTE_OLD_BLOCK, NOTE_NEW_BLOCK)]),
    dict(label='U7 Data tab paragraph after the Model III note', variants=[('any', CROSS_ANCHOR, '    ' + DATA_TAB + '\n' + CROSS_ANCHOR)]),
    dict(label='U8 provenance list: time to close', variants=[('any', '<b>Time to close</b> &mdash;\n', '<b>Time to close</b> &mdash;\n' + PROV_SENT)]),
    dict(label='U9 judgment inventory row', variants=[('any', JTAB_ANCHOR, JROW + JTAB_ANCHOR)]),
    dict(label='U10 judgment count', variants=[('any', '+ BUYERS.length*4 + INTERV.length*3 + 13 + 9 + 11;',
                                                '+ BUYERS.length*4 + INTERV.length*3 + 13 + 9 + 11 + 2;')]),
    dict(label='U11 what the quality sliders move', variants=[('any', 'the closing probability, the\n    expected proceeds and the loan size behind the survival risk.',
                                                               'the closing probability, the\n    expected proceeds, the loan size behind the survival risk and, for an ask above model value, the time to close.')]),
]
# the repo tests that call bestRatio(s,0,lamT) as "the proceeds optimum" (semantics-preserving edits)
TEST_OVR = [
    ('fuzz.test.js', 'const rs=A.bestRatio(s,0,s.lamT)', 'const rs=A.bestRatio(s,0,0)'),
    ('fuzz.test.js', 'A.bestRatio({...s,theta:.9},0,s.lamT)', 'A.bestRatio({...s,theta:.9},0,0)'),
    ('model.test.js', 'rhoSell:A.bestRatio(EX,0,900)', 'rhoSell:A.bestRatio(EX,0,0)'),
    ('model.test.js', 'ask:V*A.bestRatio(s,0,900)}),"opt")', 'ask:V*A.bestRatio(s,0,0)}),"opt")'),
]
NEW_TEST = r'''/* Overpricing costs time: invariants of timeMult, tMed, the proceeds optimum and the optimiser note.
   Run: node tests/overpricing_time.test.js */
const fs=require("fs"),path=require("path"),vm=require("vm");
const A=require("./load.js");
/* names load.js does not export: evaluate the same model section once more and pick them up */
const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const L=(()=>{ const src=html.slice(html.lastIndexOf("<script>")+8), cut=src.indexOf("/* ============ bar helpers");
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN}; vm.createContext(ctx);
  vm.runInContext(src.slice(0,cut)+";this.X={timeMult,T_ELAST,T_SMOOTH,optNote,money};",ctx); return ctx.X; })();
let pass=0,fail=0; const ok=(c,m)=>{ if(c) pass++; else { fail++; console.log("FAIL:",m); } };
const T_ELAST=L.T_ELAST, LO=@@LO@@, HI=@@HI@@;
ok(T_ELAST>=LO-1e-12&&T_ELAST<=HI+1e-12,`T_ELAST ${T_ELAST} inside its documented specification range ${LO}-${HI}`);
ok([[1,1],[.5,1],[0,1],[-1,1],[NaN,1],[2,0],[2,-1],[2,NaN]].every(([a,v])=>L.timeMult(a,v)===1),"timeMult is exactly 1 at or below value and for invalid inputs");
ok(Math.abs(Math.log(L.timeMult(Math.E,1))-T_ELAST*(1-L.T_SMOOTH/2))<1e-12,"timeMult = e^{T_ELAST (x - T_SMOOTH/2)} past the rounding zone");
/* the business score is priced at the proceeds optimum, which must not read the cost of delay */
ok(/s\.rhoSell=bestRatio\(s,0,0\);/.test(html),"render computes rhoSell as bestRatio(s,0,0)");
ok(!/rhoSell=bestRatio\(s,0,s\.lamT\)/.test(html),"rhoSell no longer reads the cost of delay");
ok(/optNote\(s,r\.V,rSell,rKeep\)/.test(html),"the optimiser note is written by optNote");
const median=(ind,ern)=>{ const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/A.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40}; };
for(const ind of ["medical","rest","msp","mfg"]) for(const ern of [2e5,1e6,5e6]) for(const lamT of [0,900,4000]){
  const s={...median(ind,ern),lamT}, V=A.model({...s,ask:1}).V;
  ok(A.omniScore(A.model({...s,ask:V*A.bestRatio(s,0,0)}),"opt")===50,`median ${ind} ${ern}: business score 50 at ${lamT}/day`); }
/* why rhoSell must not take lamT: once time reads the ask, a cost of delay lowers the delay-aware ask */
{ const s=median("rest",1.5e5); ok(A.bestRatio(s,0,4000)<A.bestRatio(s,0,0)-1e-3,"a cost of delay lowers the delay-aware ask"); }
const EX={grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false};
/* documented knife edge (Data tab): with 75% kept and $900/day the walk-away ask of a small deal leaves the 1.5x cap at
   any positive T_ELAST, while a $5M deal stays at the cap across the documented range of T_ELAST */
{ const small={...EX,ind:"medical",ern:1.5e5,rev:1.5e5/0.24}, big={...EX,ind:"medical",ern:5e6,rev:5e6/0.24};
  if(T_ELAST>=0.05) ok(A.bestRatio(small,0.75,900)<1.25,`small deal: the walk-away ask leaves the cap (${A.bestRatio(small,0.75,900)})`);
  ok(A.bestRatio(big,0.75,900)>A.RHO_MAX-0.02,`$5M deal: the walk-away ask stays at the cap (${A.bestRatio(big,0.75,900)})`); }
for(const [ind,ern] of [["medical",1.45e6],["rest",1.5e5],["mfg",5e6],["msp",4e5],["prof",5e4]]){
  const s={...EX,ind,ern,rev:ern/0.24}, V=A.model({...s,ask:1}).V, r1=A.model({...s,ask:V});
  const base=A.fitTiming(r1.Vbase,ind).days;
  for(const m of [0,0.3,0.6,0.9,0.999,1]) ok(A.model({...s,ask:V*m}).tMed===base,`time unchanged at ${m}x value (${ind})`);
  let prev=-Infinity,maxStep=0,mono=true,prevT180=Infinity,mono180=true;
  for(let m=0.5;m<=3.0001;m+=0.001){ const r=A.model({...s,ask:V*m}); if(r.tMed<prev-1e-9) mono=false;
    if(prev>-Infinity) maxStep=Math.max(maxStep,r.tMed-prev); prev=r.tMed; if(r.t180>prevT180+1e-12) mono180=false; prevT180=r.t180; }
  ok(mono,`tMed non-decreasing in the ask (${ind})`); ok(maxStep<0.5,`tMed continuous in the ask (${ind}): ${maxStep}`);
  ok(mono180,`t180 non-increasing in the ask (${ind})`);
  ok(A.model({...s,ask:V*1.01}).tMed>base,`time strictly longer above value (${ind})`);
  const d=1e-6, dR=(A.model({...s,ask:V*(1+d)}).tMed-r1.tMed)/d;
  ok(Math.abs(dR)<1,`slope of tMed continuous (zero) at value (${ind}): ${dR}`);
  const el=Math.log(A.model({...s,ask:V*3}).tMed/A.model({...s,ask:V*1.5}).tMed)/Math.log(2);
  ok(Math.abs(el-T_ELAST)<1e-9,`elasticity above the rounding zone is T_ELAST (${ind}): ${el}`);
  { const r2=A.model({...s,ask:V*2}); ok(Math.abs(r2.tMed-r2.ft.days*L.timeMult(2*V,r2.V))<1e-9*r2.tMed,`tMed = band median x timeMult (${ind})`);
    ok(r2.ft.days===base&&r2.ft.loi===r1.ft.loi,`band median and LOI to close unchanged by the ask (${ind})`); }
  for(const a of [1e-6,1,1e3,1e9,1e12]) ok(isFinite(A.model({...s,ask:a}).tMed),`finite at ask ${a} (${ind})`);
  /* a better business at the same ask is never slower: a higher model value narrows the gap */
  const better={rec:Math.min(1,s.rec+.1),cc:Math.max(.005,s.cc-.05),ret:Math.min(.99,s.ret+.03),plt:Math.max(.02,s.plt-.08),
    grw:Math.min(1.5,s.grw+.05),gm:Math.min(.97,s.gm+.03),own:Math.max(.02,s.own-.1),mgt:Math.min(.99,s.mgt+.1),fin:Math.min(1,s.fin+.1)};
  for(const k in better){ const a0=A.model({...s,ask:1.4*V}), a1=A.model({...s,[k]:better[k],ask:1.4*V});
    ok(a1.tMed<=a0.tMed+1e-9,`better ${k} never lengthens the time to close at a fixed ask (${ind})`); }
  for(const lam of [0,900,4000]) for(const th of [0,.2,.75]){
    const tag=`(${ind}, theta ${th}, ${lam}/day)`, ru=A.bestRatio(s,th,lam);
    ok(ru<=A.RHO_MAX+1e-9,`utility optimum within RHO_MAX ${tag}`);
    ok(ru<=A.bestRatio(s,th,0)+1e-9,`a cost of delay never raises the recommended ask ${tag}`);
    /* the note under the two listing cards describes the cards actually shown */
    const ss={...s,theta:th,lamT:lam}; ss.rhoSell=A.bestRatio(ss,0,0); ss.optRho=ru;
    const rSell=A.model({...ss,ask:V*ss.rhoSell}), rKeep=A.model({...ss,ask:V*ss.optRho});
    const n=L.optNote(ss,V,rSell,rKeep), U=x=>x.EVp+(1-x.PC)*th*x.V-lam*x.tMed;
    ok(U(rKeep)>=U(rSell)-1e-6*Math.abs(U(rSell)),`walk-away card at least as good on the optimiser's objective ${tag}`);
    ok(!/[−-]\$/.test(n.text),`no negative money in the note ${tag}: ${n.text}`);
    const same=L.money(V*ss.optRho)===L.money(V*ss.rhoSell);
    if(same) ok(n.kind==="same",`same figure: 'agree' note ${tag}`);
    else if(ss.optRho<ss.rhoSell) ok(n.kind==="lower"&&n.text.includes(L.money(V*ss.optRho))&&!n.text.includes("higher price")&&rKeep.tMed<=rSell.tMed&&/sooner/.test(n.text),
      `a lower walk-away ask is described as lower and faster ${tag}: ${n.text}`);
    else ok(n.kind==="higher"&&n.text.includes("higher price"),`a higher walk-away ask is described as higher ${tag}`);
    ok(n.coin===(!same&&U(rKeep)-U(rSell)<Math.abs(U(rSell))*.01)&&(!n.coin||/coin toss/.test(n.text)),`coin-toss wording on the delay-inclusive gain ${tag}`);
  }
}
console.log(`${pass} passed, ${fail} failed`); if(fail) process.exitCode=1;
'''.replace('@@LO@@', f'{RANGE_LO:.2f}').replace('@@HI@@', f'{RANGE_HI:.2f}')


def udiff(a, b, na, nb):
    return ''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), na, nb, n=2))


def build_dir(base_html, d, label):
    page, applied = apply_edits(base_html, M_EDITS + U_EDITS)
    assert model_section(page).count('FT.days') == 1 and 'out.tMed=tMedA;' in page
    os.makedirs(os.path.join(d, 'tests'), exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page)
    for f in ('load.js', 'model.test.js', 'fuzz.test.js'):
        t_ = open(f'{REPO}/tests/{f}').read()
        for ff, a, b in TEST_OVR:
            if ff == f:
                assert t_.count(a) == 1, ('test override target not unique', f, a)
                t_ = t_.replace(a, b)
        open(os.path.join(d, 'tests', f), 'w').write(t_)
    open(os.path.join(d, 'tests', 'overpricing_time.test.js'), 'w').write(NEW_TEST)
    say(f'  built {label}: ' + '; '.join(f'{l} [{t}]' for l, t in applied))
    return page, applied


PDIR = os.path.join(OUT, 'patched')                                   # index.html + this change (read by time_to_close_shape)
PAGE_W, APPLIED_W = build_dir(HTML0, PDIR, 'repo page + this change')
open(os.path.join(OUT, 'index.html.diff'), 'w', encoding='utf-8').write(udiff(HTML0, PAGE_W, 'a/index.html', 'b/index.html'))
MERGED = None
if os.path.exists(TTCS_PAGE):
    HTML_TT = open(TTCS_PAGE, encoding='utf-8').read()
    TT_SHA = hashlib.sha256(HTML_TT.encode()).hexdigest()
    open(os.path.join(OUT, 'work_time_to_close_shape_base.html'), 'w', encoding='utf-8').write(HTML_TT)
    MDIR = os.path.join(OUT, 'patched_after_time_to_close_shape')
    PAGE_LL, APPLIED_LL = build_dir(HTML_TT, MDIR, 'time_to_close_shape page + this change')
    open(os.path.join(OUT, 'index_after_time_to_close_shape.html.diff'), 'w', encoding='utf-8').write(
        udiff(HTML_TT, PAGE_LL, 'a/index.html (time_to_close_shape applied)', 'b/index.html'))
    MERGED = dict(base=TTCS_PAGE, base_sha256=TT_SHA, base_mtime=float(os.path.getmtime(TTCS_PAGE)), applied=APPLIED_LL)
else:
    say('  WARNING: time_to_close_shape page not found; merged-page checks skipped')

# the other order: does time_to_close_shape's own change still find its anchors on this patched page? Check every
# hunk of its published diff (old side) against PAGE_W; hunks that touch the lines this change rewrites on purpose
# (the lamFit line, out.tMed, eq_ts) are handled there by its after-overpricing mode (regexes on tMedA and eq_ts).
ORDER_C = None
if os.path.exists(f'{TTCS_DIR}/index.html.diff'):
    dtxt = open(f'{TTCS_DIR}/index.html.diff', encoding='utf-8').read().split('\n')
    hunks, cur = [], None
    for line in dtxt[2:]:
        if line.startswith('@@'):
            if cur: hunks.append(cur)
            cur = []
        elif cur is not None and (line.startswith(' ') or line.startswith('-')):
            cur.append(line[1:])
    if cur: hunks.append(cur)
    # the removed text of each hunk (consecutive '-' lines) is what its string anchors match; context lines are not anchors
    blocks = []
    for line in dtxt[2:]:
        if line.startswith('-'):
            if blocks and blocks[-1][1]:
                blocks[-1][0].append(line[1:])
            else:
                blocks.append([[line[1:]], True])
        elif blocks:
            blocks[-1][1] = False
    res_h = [dict(first_line=b_[0][0][:90], lines=len(b_[0]), in_repo=HTML0.count('\n'.join(b_[0])), in_patched=PAGE_W.count('\n'.join(b_[0])))
             for b_ in blocks]
    RH = pd.DataFrame(res_h)
    ORDER_C = dict(removed_blocks=len(RH), found_in_repo=int((RH.in_repo == 1).sum()), found_in_patched=int((RH.in_patched == 1).sum()),
                   blocks_changed_here=RH[(RH.in_repo == 1) & (RH.in_patched != 1)].first_line.tolist(),
                   tMedA_lamFit_line_present=('\n  const lamFit=tMedA/Math.pow(Math.log(2),1/KW);' in PAGE_W),
                   eq_ts_single_line=len(__import__('re').findall(r'  eq\("eq_ts",`[^\n]*`\);', PAGE_W)) == 1,
                   overpricing_marker_present=('out.tMult=timeMult(s.ask,out.V);' in PAGE_W))
    say('  other order (time_to_close_shape after this change):', json.dumps(ORDER_C))

# ---------------------------------------------------------------------------------------------
# checks on the built pages: the full patched page reproduces the model-only page; on the page merged with
# time_to_close_shape the multiplier scales its log-logistic curve exactly and changes nothing else
# ---------------------------------------------------------------------------------------------
P_W = os.path.join(PDIR, 'index.html')
js2 = f"""
const Ld=require({json.dumps(LOADER)});
const A1=Ld.loadFile({json.dumps(P1M)}), A1f=Ld.loadFile({json.dumps(P_W)});
const ex={json.dumps(EX)}; const V=A1.model({{...ex,ask:1}}).V;
let same=0; for(const m of [0.5,1,1.2,1.5,2,3]) same=Math.max(same,Math.abs(A1.model({{...ex,ask:V*m}}).tMed-A1f.model({{...ex,ask:V*m}}).tMed));
const out={{full_vs_model_only_max_diff:same}};
const MP={json.dumps(os.path.join(OUT, 'patched_after_time_to_close_shape', 'index.html') if MERGED else '')};
if(MP){{
  const A2=Ld.loadFile({json.dumps(os.path.join(OUT, 'work_time_to_close_shape_base.html'))}), A3=Ld.loadFile(MP);
  const rows=[]; let scaleErr=0, belowDiff=0, other=0;
  for(const m of [0.5,0.8,1,1.05,1.2,1.5,2,3]){{
    const r2=A2.model({{...ex,ask:V*m}}), r3=A3.model({{...ex,ask:V*m}}), k=r3.tMult;
    rows.push({{rho:m,tMed_ttcs:r2.tMed,tMed_merged:r3.tMed,mult:k,t180_ttcs:r2.t180,t180_merged:r3.t180,PC:r3.PC}});
    scaleErr=Math.max(scaleErr,Math.abs(r3.tMed-r2.tMed*k)/r2.tMed);
    for(const t of [60,180,365]) scaleErr=Math.max(scaleErr,Math.abs(r3.F(t)-r2.F(t/k)));
    if(m<=1) for(const t of [30,90,180,365,540]) belowDiff=Math.max(belowDiff,Math.abs(r3.F(t)-r2.F(t)),Math.abs(r3.tMed-r2.tMed));
    for(const key of ['V','PC','EVp','Vmean','Vreal','Vbase']) other=Math.max(other,Math.abs(r2[key]-r3[key])/Math.max(1,Math.abs(r2[key])));
    other=Math.max(other,Math.abs(A2.omniScore(r2)-A3.omniScore(r3)));
  }}
  let mono=true,prev=null,prev180=null,mono180=true;
  for(let m=0.5;m<=3.0001;m+=0.002){{ const r=A3.model({{...ex,ask:V*m}}); if(prev!==null&&r.tMed<prev-1e-9) mono=false; if(prev180!==null&&r.t180>prev180+1e-12) mono180=false; prev=r.tMed; prev180=r.t180; }}
  const el=Math.log(A3.model({{...ex,ask:V*3}}).tMed/A3.model({{...ex,ask:V*1.5}}).tMed)/Math.log(2);
  const win=[]; const r1_=A3.model({{...ex,ask:V}});
  for(const t of [219,r1_.tMed]) for(const m of [1.2,1.5,2]){{ const r=A3.model({{...ex,ask:V*m}}); win.push({{page:'merged',t:t,rho:m,ratio:(r.PC*r.F(t))/(r1_.PC*r1_.F(t)),pc_ratio:r.PC/r1_.PC}}); }}
  Object.assign(out,{{merged_rows:rows,merged_scale_max_err:scaleErr,merged_at_or_below_max_diff:belowDiff,merged_other_outputs_max_change:other,
    merged_monotone:mono,merged_t180_nonincreasing:mono180,merged_elasticity_1p5_to_3:el,merged_window:win}});
}}
console.log(JSON.stringify(out));
"""
MC2 = node(js2)
say('  page checks:', json.dumps({k: v for k, v in MC2.items() if k not in ('merged_rows', 'merged_window')}))
assert MC2['full_vs_model_only_max_diff'] == 0
if MERGED:
    say(pd.DataFrame(MC2['merged_rows']).round(4).to_string())
    assert MC2['merged_scale_max_err'] < 1e-9 and MC2['merged_at_or_below_max_diff'] == 0 and MC2['merged_other_outputs_max_change'] < 1e-9
    assert MC2['merged_monotone'] and MC2['merged_t180_nonincreasing'] and abs(MC2['merged_elasticity_1p5_to_3'] - T_REC) < 1e-9
    WIN = pd.concat([WIN, pd.DataFrame(MC2['merged_window'])], ignore_index=True)
    WIN.to_csv(os.path.join(OUT, 'F_window_loss_check.csv'), index=False)

# the repo's own test suites on the patched copies (index.html in the repo is not touched)
TESTS = {}
NFUZZ = '200' if QUICK else '1500'
for lab, d in [('repo+this', PDIR)] + ([('time_to_close_shape+this', os.path.join(OUT, 'patched_after_time_to_close_shape'))] if MERGED else []):
    TESTS[lab] = {}
    for f in ('overpricing_time.test.js', 'model.test.js', 'fuzz.test.js'):
        r = subprocess.run(['node', os.path.join(d, 'tests', f)] + ([NFUZZ] if f == 'fuzz.test.js' else []), capture_output=True, text=True, timeout=3600)
        TESTS[lab][f] = dict(returncode=r.returncode, tail=(r.stdout.strip().splitlines() or [''])[-1],
                             fails=[l for l in r.stdout.splitlines() if l.startswith('FAIL')][:10])
        say(f'  repo test {f} on {lab}: rc={r.returncode} {TESTS[lab][f]["tail"]}')
        if r.returncode != 0:
            say('\n'.join(TESTS[lab][f]['fails']))
for lab in TESTS:
    for f in TESTS[lab]:
        assert TESTS[lab][f]['returncode'] == 0, (lab, f, TESTS[lab][f])
# render-side checks in headless Chromium (the model tests do not reach render()): a focused smoke test of the new
# pieces on both pages and, outside QUICK mode, the repo's own browser sweep (every select, every slider at five
# positions, typed values; page errors, KaTeX errors, NaN/undefined, horizontal scroll)
SMOKE_JS = os.path.join(OUT, 'browser_smoke.js')
open(SMOKE_JS, 'w').write(r"""const path=require("path"); let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{
  const b=await pw.chromium.launch(), p=await b.newPage({viewport:{width:1440,height:900}}), errs=[];
  p.on("pageerror",e=>errs.push(e.message)); p.on("console",m=>{ if(m.type()==="error") errs.push(m.text()); });
  await p.goto("file://"+process.argv[2]); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000});
  const settle=async()=>{ await p.waitForTimeout(500); await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))); };
  const setAsk=async m=>{ const V=await p.evaluate(()=>STATE.r.V); await p.fill("#v_ask",String(Math.round(V*m))); await p.press("#v_ask","Enter"); await settle(); };
  const setRange=async (id,v)=>{ await p.$eval("#"+id,(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));},v); await settle(); };
  /* eq() renders lazily (IntersectionObserver): bring the equation into view and wait until it shows the CURRENT
     multiplier and median before reading it (revision 2 read a stale equation after a fixed 500 ms) */
  const eqReady=async()=>{ await p.$eval("#eq_ts",e=>e.scrollIntoView({block:"center"}));
    await p.waitForFunction(()=>{ const r=STATE.r, t=document.getElementById("eq_ts").textContent;
      return t.includes(r.tMult.toFixed(3))&&t.includes(Math.round(r.tMed).toLocaleString()); },null,{timeout:30000}); };
  const snap=async()=>{ await eqReady(); return p.evaluate(()=>({ratio:STATE.s.ask/STATE.r.V,tMult:STATE.r.tMult,tMed:STATE.r.tMed,band:STATE.r.ft.days,
    eqOK:(()=>{ const t=document.getElementById("eq_ts").textContent, days=Number(document.getElementById("o_t").textContent.replace(/[^0-9]/g,"")).toLocaleString();
      return t.includes(STATE.r.tMult.toFixed(3))&&t.includes(days)&&t.includes(Math.round(STATE.r.ft.days).toLocaleString()); })(),
    tag:document.getElementById("o_t_pv").className,tagText:document.getElementById("o_t_pv").textContent,
    stretch:document.getElementById("o_tstretch").textContent,tile:document.getElementById("o_t").textContent,
    note:document.getElementById("o_listnote").textContent,katex:document.querySelectorAll(".katex-error").length,
    eqts:document.getElementById("eq_ts").textContent.slice(0,160),
    bad:(document.getElementById("view-console").innerText.match(/NaN|Infinity|undefined/g)||[]).length,
    optRho:STATE.s.optRho,rhoSell:STATE.s.rhoSell,lamT:STATE.s.lamT,theta:STATE.s.theta,
    card1:document.getElementById("o_list").textContent,card2:document.getElementById("o_list2").textContent})); };
  const out={};
  await setAsk(0.9); out.below=await snap();
  await setAsk(2.0); out.above=await snap();
  await setRange("i_th",0); await setRange("i_lam",4000); await setAsk(1.0); out.theta0_delay4000=await snap();
  await p.click(".tab[data-v=data]"); await p.waitForTimeout(300);
  const dt=await p.evaluate(()=>document.getElementById("view-data").innerText);
  out.data_tab_has_paragraph=dt.includes("Overpricing costs time"); out.data_tab_bad=(dt.match(/NaN|Infinity|undefined/g)||[]).length;
  out.errors=errs; console.log(JSON.stringify(out)); await b.close();
})();
""")
BROWSER = {}
for lab, d in [('repo+this', PDIR)] + ([('time_to_close_shape+this', os.path.join(OUT, 'patched_after_time_to_close_shape'))] if MERGED else []):
    r = subprocess.run(['node', SMOKE_JS, os.path.join(d, 'index.html')], capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    sm_ = json.loads(r.stdout.strip().splitlines()[-1])
    say(f'  browser smoke {lab}: ' + json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk not in ('note', 'eqts')})
                                                 for k, v in sm_.items()}))
    say(f'    note at theta 0, $4,000/day: {sm_["theta0_delay4000"]["note"]}')
    assert not sm_['errors'] and sm_['data_tab_has_paragraph'] and sm_['data_tab_bad'] == 0
    assert sm_['below']['tag'] == 'pv a' and sm_['below']['stretch'] == '' and sm_['below']['tMult'] == 1
    assert sm_['above']['tag'] == 'pv j' and 'judgment' in sm_['above']['tagText'] and '×' in sm_['above']['stretch'] and sm_['above']['tMed'] > sm_['above']['band']
    for k_ in ('below', 'above', 'theta0_delay4000'):
        assert sm_[k_]['katex'] == 0 and sm_[k_]['bad'] == 0 and '−$' not in sm_[k_]['note']
        assert sm_[k_]['eqOK'], (lab, k_, sm_[k_]['eqts'])          # the equation shows band days x multiplier = the tile's days
    t0_ = sm_['theta0_delay4000']
    assert t0_['optRho'] <= t0_['rhoSell'] + 1e-9
    assert ('agree' in t0_['note']) if t0_['card1'] == t0_['card2'] else ('sooner' in t0_['note'] and 'higher price' not in t0_['note'])
    BROWSER[lab] = dict(smoke=sm_)
    if not QUICK:
        os.makedirs(os.path.join(d, 'tests'), exist_ok=True)
        shutil.copyfile(f'{REPO}/tests/browser.sweep.js', os.path.join(d, 'tests', 'browser.sweep.js'))
        r = subprocess.run(['node', os.path.join(d, 'tests', 'browser.sweep.js')], capture_output=True, text=True, timeout=3600)
        BROWSER[lab]['sweep'] = dict(returncode=r.returncode, tail=r.stdout.strip().splitlines()[-3:])
        say(f'  browser sweep {lab}: rc={r.returncode} {r.stdout.strip().splitlines()[-3:]}')
        assert r.returncode == 0
RES['F_synthesis'].update(browser_checks=BROWSER)
RES['F_synthesis'].update(model_check=MC, page_check=MC2, repo_tests=TESTS, js_edits_model=M_EDITS, js_edits_ui=U_EDITS,
                          applied_repo=APPLIED_W, merged_with_time_to_close_shape=MERGED, other_order_check=ORDER_C,
                          test_overrides=TEST_OVR, new_test_file=NEW_TEST, data_tab_html=DATA_TAB)
json.dump(RES, open(os.path.join(OUT, 'results_full.json'), 'w'), indent=1, default=float)
say('\nwrote', os.path.join(OUT, 'results_full.json'))

# =============================================================================================
# RESULT.json (same content as the structured return)
# =============================================================================================
f2 = lambda x: f'{x:.2f}'
cA = RES['A_flippa_march']; cvA_ = cA['cv_10fold_x3']; loA = cA['cv_leave_one_type_group_out']
sh0 = cA['shape_test']['c=0.0']
CUR = {round(r['rho_vs_comparables'], 2): r for r in cA['p_ratio_curve']}
opt_def = OPT[(OPT.lamT == 900) & (OPT.theta == 0.75)]
opt_4k = OPT[(OPT.lamT == 4000) & (OPT.theta == 0.75)]
cvH_w, cvH_n = cvE['with_rho_hinge'], cvE['no_rho']
hoH_w = ho['with_rho_hinge']
dlo = dlm['main_exposure_offset']
cfE = lambda lab, k='rho_sale_l': CE[lab]['coef'][k]
fp = lambda lab: f"{cfE(lab, 'rho_sale_p')['est']:.2f}"
NOTEX = NOTES[(NOTES.ern == 1.45e6) & (NOTES.theta == 0.75) & (NOTES.lamT == 900)].iloc[0]
NOTE150 = NOTES[(NOTES.ern == 1.5e5) & (NOTES.theta == 0) & (NOTES.lamT == 900)].iloc[0]
NOTE5M = NOTES[(NOTES.ern == 5e6) & (NOTES.theta == 0.75) & (NOTES.lamT == 900)].iloc[0]
w219 = lambda pg, r_: float(WIN[(WIN.page == pg) & (WIN.t == 219) & (WIN.rho == r_)].ratio.iloc[0])
fl_rng_txt = f'{FL_RNG[0]:.2f}-{FL_RNG[1]:.2f}'
grid_txt = (f'{len(GRIDS):,} combinations: min {GRIDS.T_ELAST.min():.2f}, 5/50/95% {GRID_P[0]:.2f}/{GRID_P[1]:.2f}/{GRID_P[2]:.2f}, '
            f'max {GRIDS.T_ELAST.max():.2f}')
sens_txt = ', '.join(f'prior sd {r.prior_sd:g} with transfer ' + (f'sd {r.delta:g}' if r.delta_rule == 'fixed' else f'{r.delta_rule} ({r.delta:.2f})')
                     + f': {r.T_ELAST:.2f}' for r in SENS.itertuples() if r.prior_sd == 0.5 or (r.delta_rule == 'fixed' and abs(r.delta - 0.5) < 1e-9))
loo_short = {k.split(' ')[0]: v for k, v in loo.items()}
loo_txt = '; '.join(f'without {k} {v["shrunk"]:.2f}' for k, v in loo_short.items())
ONE['choice'] = ONE.apply(lambda r: next((r[c] for c in ['EF', 'Flippa', 'DealLedger', 'pooling', 'conversion'] if '(main)' not in str(r[c])), 'main'), axis=1)
one_lo, one_hi = ONE.loc[ONE.T_ELAST.idxmin()], ONE.loc[ONE.T_ELAST.idxmax()]
one_txt = '; '.join(f'{r.choice} {r.T_ELAST:.2f}' for r in ONE.iloc[1:].itertuples())
cvD_ = dlo['cv_10fold_x3']
dl_pull = float(b_post - loo_short['DealLedger']['shrunk'])
DLV_txt = '; '.join(f'{k}: {v["beta_above"]["est"]:+.3f} ({v["beta_above"]["se"]:.3f}), n {v["n"]}, {v["events"]} sales' for k, v in DLV.items() if '(main)' not in k)
by_year_txt = ', '.join(f'{k} {v["est"]:+.2f}' for k, v in EF_BY_YEAR.items())
by_year_se = (min(v['se'] for v in EF_BY_YEAR.values()), max(v['se'] for v in EF_BY_YEAR.values()))
mod = lambda x: f'{"&minus;" if x < 0 else ""}{abs(x):.2f}'
params = [
    dict(param='T_ELAST: d ln(median time to close | close) / d ln(ask/value), above value (new constant; a LABELLED JUDGMENT, not a Main-Street estimate)',
         current_value='0 (fitTiming keys on value only; the ask never changes time)',
         fitted_value=(f'not identified for Main Street. Sale-clock elasticity pooled over the three analogs: {MAINSPEC["pooled_clock"]:.2f} (between-source sd fixed at '
                       f'{TAU0:g}; weights EF {W_SRC["EF"]:.2f}, Flippa {W_SRC["Flippa"]:.2f}, DealLedger {W_SRC["DealLedger"]:.2f}); DerSimonian-Laird {PM["re"]:.2f} '
                       f'(tau {PM["tau"]:.2f}, Q {PM["Q"]:.1f} on 2 df), fixed effect {PM["fe"]:.2f}. Converted to the console\'s estimand (time to close among deals '
                       f'that close) with P_C at value {PC_V:.2f}: {MAINSPEC["pooled"]:.2f}. Shrunk toward the current value 0: {b_post:.3f}'),
         se=(f'pooled clock {MAINSPEC["pooled_clock_se"]:.2f} (DerSimonian-Laird with modified Hartung-Knapp SE {PM["se_mhk"]:.2f}, 95% interval '
             f'{PM["hk_ci95"][0]:.2f} to {PM["hk_ci95"][1]:.2f}); converted {MAINSPEC["pooled_se"]:.2f}; posterior sd {sd_post:.2f} after transfer shrinkage '
             f'(weight on the analogs {w_post:.2f})'),
         n=f'{len(E):,} EF sold listings + {len(A):,} Flippa listings ({int(A.sold.sum())} sales) + {dlm["n"]} DealLedger listings ({dlm["events"]} sales, {dlm["brokers"]} brokers)',
         method=('All three analogs on ONE scale, the sale-clock elasticity (-d ln sale hazard / k per log point of overpricing): EF linear Weibull AFT slope of '
                 'days on market | sale on log(first ask / cross-fitted hedonic fair sale value), divided by EF\'s sell-through '
                 f'({P_EF:.2f}, median of {len(sbp)} scoreboard captures) because time | sale = clock x P(sale) under competing risks; Flippa cloglog sale hazard '
                 'above comparables, regression-calibrated for the reconstructed asks of the non-reference listings, -beta/k with k = '
                 f'{k_mkt:.2f} (EF\'s Weibull shape); DealLedger exponential sale hazard keyed by listing id, at risk from the first sold-status snapshot, -beta. '
                 f'Random-effects pooling with the between-source sd fixed at {TAU0:g} (monotone in each source). Converted BEFORE shrinkage to '
                 'd ln(time to close | close) / d ln rho = P_C x clock elasticity (competing risks, proportional hazards, common shape, withdrawal unaffected), '
                 f'with the console\'s P_C at value (median over {len(PCQ["pc"])} median businesses; {PC_LO:.2f}-{PC_HI:.2f}). Prior N(0, {PRIOR_SD:g}^2) at the '
                 f'current value and transfer sd {DELTA:g}, both on the console\'s scale and fixed in advance; rounded to 0.05'),
         validation=(f'per source: EF 10-fold CV log-lik/obs {cvL_w["loglik_per_obs"]:.4f} (linear) / {cvH_w["loglik_per_obs"]:.4f} (hinge) vs '
                     f'{cvL_n["loglik_per_obs"]:.4f} without the ask; EF 2023-25H1 hold-out with the hedonic fitted on 2019-22 only {hoL_w["loglik_per_obs"]:.4f} '
                     f'(linear) / {hoH_w["loglik_per_obs"]:.4f} (hinge) vs {hoL_n["loglik_per_obs"]:.4f}, truncation-adjusted {hoLt_w["loglik_per_obs"]:.4f} vs '
                     f'{hoLt_n["loglik_per_obs"]:.4f} (differences below 0.001 per listing: negligible); Flippa 10-fold x3 CV '
                     f'{cvA_["with_ask_hinge"]["heldout_loglik_per_obs"]:.4f} vs {cvA_["no_ask"]["heldout_loglik_per_obs"]:.4f}, AUC '
                     f'{cvA_["with_ask_hinge"]["auc_mean"]:.3f} vs {cvA_["no_ask"]["auc_mean"]:.3f}, leave-one-type-group-out '
                     f'{loA["with_ask_hinge"]["heldout_loglik_per_obs"]:.4f} vs {loA["no_ask"]["heldout_loglik_per_obs"]:.4f}; DealLedger 10-fold x3 CV Poisson log-lik '
                     f'{cvD_["with_ask"]["heldout_poisson_loglik_per_obs"]:.4f} vs {cvD_["no_ask"]["heldout_poisson_loglik_per_obs"]:.4f}, concordance of the rate '
                     f'{cvD_["with_ask"]["cindex_rate_mean"]:.3f} vs {cvD_["no_ask"]["cindex_rate_mean"]:.3f} (worse with the ask). One analysis choice at a time: '
                     f'{SPEC_LO:.2f}-{SPEC_HI:.2f} (lowest: {one_lo.choice}; highest: {one_hi.choice}); leave-one-source-out {loo_txt}; stated range '
                     f'{RANGE_LO:.2f}-{RANGE_HI:.2f}; all {grid_txt}; shrinkage sensitivity {sens_txt}; the rule rises monotonically with each source '
                     f'(Flippa entry x0.5..x2: {", ".join(f"{v:.2f}" for v in MONO.main_rule)}); the same chain at higher asks, where the console\'s P_C is lower, '
                     f'shrunk the same way: {STRUCT["1.2"]["shrunk"]:.2f} at 1.2x, {STRUCT["1.5"]["shrunk"]:.2f} at 1.5x, {STRUCT["2"]["shrunk"]:.2f} at 2x'),
         recommended_value=(f'T_ELAST = {T_REC:.2f}, a labelled judgment anchored on the analogs\' sign (overpricing slows the sale clock); size set by the conversion '
                            f'to time | close and shrinkage toward zero; stated range {RANGE_LO:.2f}-{RANGE_HI:.2f} (one choice at a time and leave-one-source-out; '
                            f'without Flippa {LOO_NOFL:.2f}); posterior sd {sd_post:.2f}. An upper bound on the time channel: the Flippa window hazard behind most of '
                            'it also counts listings that never sell')),
    dict(param='EF direct estimate: AFT slope of log days-on-market | sale on log(first ask / fair sale value)',
         current_value='n/a (source estimate)',
         fitted_value=(f'linear {ef_lin["est"]:.3f} (the pooled entry; {ef_lin["est"] / P_EF:.2f} on the clock scale); hinge around the median premium '
                       f'{fp("hinge_median_knot|weibull")} above / {cfE("hinge_median_knot|weibull", "rho_sale_n")["est"]:.2f} below (monotone component {ef_lo_:.2f}); '
                       f'knot at fair value {cfE("knot_at_fair_value|weibull", "r0_p")["est"]:.2f} above / {cfE("knot_at_fair_value|weibull", "r0_n")["est"]:.2f} below '
                       f'({np.mean(E.rho_sale < 0):.0%} of first asks below); right-truncation corrected: linear {cfE("linear_truncation_corrected|weibull")["est"]:.2f}, '
                       f'hinge {fp("hinge_truncation_corrected|weibull")}; quintile dummies vs the middle quintile q0 {cfE("quintile_dummies_vs_q2|weibull", "q0")["est"]:+.2f}, '
                       f'q1 {cfE("quintile_dummies_vs_q2|weibull", "q1")["est"]:+.2f}, q3 {cfE("quintile_dummies_vs_q2|weibull", "q3")["est"]:+.2f}, '
                       f'q4 {cfE("quintile_dummies_vs_q2|weibull", "q4")["est"]:+.2f} log-days; linear slope by listing year {by_year_txt}'),
         se=(f'linear: Weibull analytic {EF_SE_PARTS["weibull_analytic"]:.3f}, bootstrap {EF_SE_PARTS["weibull_bootstrap"]:.3f} (B={bootE["B"]}, hedonics re-cross-fitted '
             f'with folds by listing), OLS HC1 {EF_SE_PARTS["ols_hc1"]:.3f}, median regression {EF_SE_PARTS["median_regression"]:.3f}: entered with the largest, '
             f'{ef_lin_se:.3f}; hinge above {cfE("hinge_median_knot|weibull", "rho_sale_p")["se"]:.3f} analytic / {bootE["hinge_above_se"]:.3f} bootstrap; monotone '
             f'component {bootE["monotone_component_se"]:.3f} (bootstrap); quintile dummies {cfE("quintile_dummies_vs_q2|weibull", "q4")["se"]:.3f}; by year '
             f'{by_year_se[0]:.2f}-{by_year_se[1]:.2f}'),
         n=f'{len(E):,} sold listings first listed 2019-01..2025-06 (data date {DATA_DATE.date()}, follow-up at least {E.tau.min():.0f} days)',
         method=(f'Weibull AFT (shape k = {k_mkt:.2f}) with analytic gradient and Hessian; also OLS on log days and median / quartile regressions; controls: '
                 'listing-time profit, age, pre-listing trend and margin, hours, category, listing year; fair value = cross-fitted ridge hedonic of the sale '
                 f'multiple on listing-time information (OOF R2 {hedE["r2_sale_hedonic"]:.2f}); truncation-corrected fits use f(T)/F(data date - first listed)'),
         validation=(f'linear slope across estimators and outlier treatments {EF_EST_RNG[0]:.2f} to {EF_EST_RNG[1]:.2f}: winsorised 1-99 '
                     f'{cfE("linear_winsor_1_99|weibull")["est"]:.2f}, 5-95 {cfE("linear_winsor_5_95|weibull")["est"]:.2f}, trimmed 5-95 '
                     f'{cfE("linear_trim_5_95|weibull")["est"]:.2f}, truncation-corrected {cfE("linear_truncation_corrected|weibull")["est"]:.2f}, top 2.5% of asks '
                     f'dropped {cfE("linear_drop_top_2p5|weibull")["est"]:.2f}, bottom 2.5% dropped {cfE("linear_drop_bottom_2p5|weibull")["est"]:.2f}, OLS '
                     f'{cfE("linear|lognormal")["est"]:.2f}, median regression {cfE("linear|median_regression")["est"]:.2f}, quartile regressions '
                     f'{cfE("linear|quantile_0.25")["est"]:.2f} / {cfE("linear|quantile_0.75")["est"]:.2f}; listing-year halves (defined before listing) 2019-21 '
                     f'{cfE("subsample_listed_2019_2021_linear|weibull")["est"]:.2f}, 2022-25H1 {cfE("subsample_listed_2022_2025H1_linear|weibull")["est"]:.2f}; '
                     f'hinge above {fp("hinge_trim_5_95|weibull")}-{fp("hinge_winsor_5_95|weibull")} across outlier treatments; listing-to-sold clock linear '
                     f'{cfE("listing_to_sold_clock_linear|weibull")["est"]:.2f}; vs comparables\' asks linear {cfE("vs_comparables_asks_linear|weibull", "rho_ask_l")["est"]:.2f}. '
                     f'10-fold CV log-lik {cvL_w["loglik_per_obs"]:.4f} vs {cvL_n["loglik_per_obs"]:.4f} without the ask (hinge {cvH_w["loglik_per_obs"]:.4f}); 2023-25H1 '
                     f'hold-out with the hedonic fitted on the training years only {hoL_w["loglik_per_obs"]:.4f} vs {hoL_n["loglik_per_obs"]:.4f} (revision 2, hedonic '
                     f'on all years: {ho_rev2["with_rho_linear"]:.4f} vs {ho_rev2["no_rho"]:.4f}), truncation-adjusted {hoLt_w["loglik_per_obs"]:.4f} vs '
                     f'{hoLt_n["loglik_per_obs"]:.4f}: negligible either way. The robust part is the top quintile of first asks '
                     f'(+{q4E["est"]:.2f} log-days, SE {q4E["se"]:.2f})'),
         recommended_value=(f'enters the pooling at {ef_lin["est"]:.2f} (SE {ef_lin_se:.2f}, the largest across estimators), {ef_lin["est"] / P_EF:.2f} '
                            f'({ef_lin_se / P_EF:.2f}) on the clock scale; weight {W_SRC["EF"]:.2f}; contributes {CONTRIB["EF"]:.3f} of the shrunk {b_post:.3f}')),
    dict(param='Flippa sale hazard: cloglog slope on log(ask / hedonic comparable ask), above and below comparables',
         current_value='n/a (source estimate)',
         fitted_value=(f'above {bA:.3f} raw; {bA_rc:.3f} regression-calibrated for the non-reference listings only (main); variants: revision 2\'s whole-sample '
                       f'division {bA_rc2:.3f}, uniform reconstruction then calibration {rA_u.params["ucal_p"]:.3f}, non-reference listings alone '
                       f'{rA_nr.params["cal_p"]:.3f}, revision 1\'s classical reliability {bA_cl:.3f}; below {rA_rc.params["cal_n"]:.3f} (calibrated). In time units '
                       f'(-beta/k): {fl_main_b:.2f} (range {fl_rng_txt} across error corrections and k). Flippa\'s own Weibull shape by profile likelihood '
                       f'{FLIPPA_K["k_hat"]:.2f} (95% {FLIPPA_K["ci95"][0]:.2f}-{FLIPPA_K["ci95"][1]:.2f})'),
         se=(f'{seA:.3f} raw / {seA_rc:.3f} calibrated (cluster {seA_rc_cl:.3f}; cluster bootstrap that refits the calibration, B={len(bs_rc)}, {seA_rc_boot:.3f}; '
             f'the larger) / below {rA_rc.bse["cal_n"]:.3f} (clustered by type x industry, {A.clu.nunique()} clusters); time entry {fl_main_se:.2f} (incl. k SE {k_se:.3f})'),
         n=(f'{len(A):,} profitable listings open in March 2026, {int(A.sold.sum())} sold within 219 days; calibration on {CAL["n_reference_in_sample"]:,} '
            f'reference listings with exact asks ({CAL["substitution"]["reference_sales"]} sales; {CAL["substitution"]["nonreference_n"]:,} non-reference listings, '
            f'{CAL["substitution"]["nonreference_sales"]} sales)'),
         method=(f'single-interval cloglog with profit, site age, listing vintage, type group. Reconstructed-ask error: slope of the true log ask on the leave-out '
                 f'reconstruction {CAL["slope_true_on_hat_logask"]:.3f} (near-Berkson), corr(err, reconstruction) {CAL["corr_err_hat"]:.2f}, corr(err, truth) '
                 f'{CAL["corr_err_true"]:.2f}. Regression calibration by substitution: for the non-reference listings the hinge terms are replaced by E[true '
                 'hinge term | reconstructed hinge terms, controls], estimated on the reference listings\' leave-out reconstruction (positive part: '
                 f'{CAL["substitution"]["calib_tp_coefs"]["hp"]:.3f} x hp {CAL["substitution"]["calib_tp_coefs"]["hn"]:+.3f} x hn; negative part '
                 f'{CAL["substitution"]["calib_tn_coefs"]["hp"]:.3f} x hp + {CAL["substitution"]["calib_tn_coefs"]["hn"]:.3f} x hn); the reference listings keep '
                 f'their own asks. Multinomial (sold/ended/open) sold slope {MN["sold_vs_open"]["est"]:.3f} ({MN["sold_vs_open"]["se"]:.3f}), ended '
                 f'{MN["ended_vs_open"]["est"]:.3f} ({MN["ended_vs_open"]["se"]:.3f})'),
         validation=(f'split halves {sh[0]["est"]:.3f} / {sh[1]["est"]:.3f}; type-median version {cA["fits"]["hinge_type_median"]["beta_above"]["est"]:.3f}; non-zombie '
                     f'{cA["fits"]["non_zombie_listed_lt_2y"]["beta_above"]["est"]:.3f}; classified only {cA["fits"]["classified_only"]["beta_above"]["est"]:.3f}; knot '
                     f'profile AIC flat from -0.3 to +0.3; bins EB-shrunk onto the hinge line (between-bin variance {cA["eb_tau2"]:.3f}); 10-fold x3 CV and '
                     'leave-one-type-group-out both improve with the ask'),
         recommended_value=(f'input on the clock scale at {fl_main_b:.2f} (SE {fl_main_se:.2f}), range {fl_rng_txt}; weight {W_SRC["Flippa"]:.2f}; contributes '
                            f'{CONTRIB["Flippa"]:.3f} of the shrunk {b_post:.3f}. A window hazard: it also counts listings that never sell, so as a time effect it is an '
                            'upper bound; window-probability evidence for gapPenalty (no change)')),
    dict(param='DealLedger (Main Street) sale hazard on the relative ask, above comparables',
         current_value='n/a (source estimate)',
         fitted_value=(f'exponential hazard with exposure offset, keyed by listing id, at risk from {DLCHK["first_sold_status_snapshot"]}: above '
                       f'{dlo["beta_above"]["est"]:+.3f} (time entry {-dlo["beta_above"]["est"]:+.2f}), below {dlo["beta_below"]["est"]:+.3f}. Variants: {DLV_txt}. '
                       f'The URL key (revision 2) merged {DLV[[k for k in DLV if "join error" in k][0]]["keys_merging_gt1_id"]} of its '
                       f'{DLV[[k for k in DLV if "join error" in k][0]]["n"]} keys over more than one listing, with '
                       f'{DLV[[k for k in DLV if "join error" in k][0]]["sales_on_merged_keys"]} of its {DLV[[k for k in DLV if "join error" in k][0]]["events"]} sales on merged keys'),
         se=f'{dlo["beta_above"]["se"]:.3f} (clustered by broker, {dlm["brokers"]} brokers); time entry SE {dlo["beta_above"]["se"]:.2f}',
         n=(f'{dlm["n"]} listings, {dlm["events"]} sales, {dlm["brokers"]} brokers (risk window {DLCHK["first_sold_status_snapshot"]} to {DLCHK["window_end"]}, '
            f'{DLCHK["snapshots_in_window"]} snapshots; {dlm["share_directory_page_listings"]:.0%} of listings on directory pages)'),
         method=('Poisson likelihood with log exposure as an offset (exponential hazard: event or censoring at the end of exposure). Listing key = the scraper\'s '
                 'id (sha256 of the detail URL, or of broker domain | title for a card without its own page); one record per (snapshot, id): sold if any card '
                 'of that snapshot says sold, ask and cash flow = median. At risk only from the first snapshot that records a sold status (every earlier row reads '
                 '"active"); listings already sold at entry dropped; only brokers that ever mark a sale; relative ask = log(ask / cash flow) minus a cross-fitted '
                 'ridge hedonic (cash flow, vertical, broker)'),
         validation=(f'10-fold x3 CV: Poisson log-lik {cvD_["with_ask"]["heldout_poisson_loglik_per_obs"]:.4f} with the ask vs '
                     f'{cvD_["no_ask"]["heldout_poisson_loglik_per_obs"]:.4f} without; concordance of the rate exp(Xb) without the offset '
                     f'{cvD_["with_ask"]["cindex_rate_mean"]:.3f} vs {cvD_["no_ask"]["cindex_rate_mean"]:.3f}; AUC of the rate '
                     f'{cvD_["with_ask"]["auc_rate_mean"]:.3f} vs {cvD_["no_ask"]["auc_rate_mean"]:.3f}. Key checks: 0 of {DLCHK["listing_specific_urls"]:,} '
                     f'listing-specific URLs carry more than one id; {DLCHK["ids_with_gt1_distinct_ask"]} ids keep their id through a price change; '
                     f'{DLCHK["cells_with_duplicate_rows"]:,} (snapshot, id) cells have duplicate cards, {DLCHK["cells_with_conflicting_status"]} with conflicting '
                     f'status. {dlm["share_sold_with_1day_exposure"]:.0%} of sales have a 1-day exposure; the top broker supplies {dlm["top_broker_sales"]} of '
                     f'{dlm["events"]} sales'),
         recommended_value=(f'uninformative (no predictive power; SE {dlo["beta_above"]["se"]:.2f}); kept in the pooling as the only Main-Street source, where it '
                            f'carries {W_SRC["DealLedger"]:.0%} of the weight (the fixed between-source sd swamps its own SE) and moves the shrunk value by '
                            f'{dl_pull:+.3f} (without it {loo_short["DealLedger"]["shrunk"]:.2f}); not evidence for any Main-Street size')),
    dict(param='gapPenalty shape (PEN_MAX, GAP_CDF, GAP_TAIL_K) on P_C',
         current_value='Pepperdine cumulative gap distribution x 0.45, zero at/below value, tail decay past 100%',
         fitted_value=('Flippa P(sale within 219 d) ratio by ask/comparables (window, not ultimate): ' +
                       ', '.join(f'{r_:g}x {CUR[r_]["p_sale_ratio_flippa_window"]:.2f}' for r_ in (1.2, 1.5, 2.0, 3.0)) +
                       '. Mapped to an ultimate close probability by competing risks at a 61% base (withdrawal unaffected / as the multinomial): ' +
                       ', '.join(f'{r_:g}x {CUR[r_]["ultimate_ratio_withdrawal_unaffected"]:.2f}/{CUR[r_]["ultimate_ratio_withdrawal_as_mnlogit"]:.2f}' for r_ in (1.2, 1.5, 2.0, 3.0)) +
                       '. Console P_C ratio: ' + ', '.join(f'{r_:g}x {CUR[r_]["pepperdine_pc_ratio_c0"]:.2f}' for r_ in (1.2, 1.5, 2.0, 3.0)) +
                       f'. Pepperdine shape with free amplitude (plus below slope) theta = {sh0["pepperdine_plus_below_slope"]["theta"]["est"]:.2f}'),
         se=f'theta SE {sh0["pepperdine_plus_below_slope"]["theta"]["se"]:.2f}; window-ratio SEs ' + ', '.join(f'{CUR[r_]["se_boot"]:.2f}' for r_ in (1.2, 1.5, 2.0, 3.0)) + ' (cluster bootstrap)',
         n=f'{len(A):,} Flippa listings; Flippa 2019 auctions {RES["B_flippa_2019_auctions"]["n"]} ({RES["B_flippa_2019_auctions"]["events"]} sold)',
         method='cloglog shape comparison: log-linear hinge vs log(1 - gapPenalty) with free amplitude (plus the same below-value slope), AIC and 10-fold x3 CV; competing-risk map P(x) = 1/(1 + ((1-P0)/P0) e^{(beta_w - beta_s) x})',
         validation=f'AIC hinge {sh0["aic_hinge"]:.1f} vs Pepperdine shape {sh0["pepperdine_plus_below_slope"]["aic"]:.1f}; CV log-lik {sh0["cv"]["loglinear_hinge"]["heldout_loglik_per_obs"]:.5f} vs {sh0["pepperdine_plus_below_slope"]["cv_loglik"]:.5f}',
         recommended_value='leave level and shape unchanged (Pepperdine is the only Main-Street source); see caveats for what the analogs corroborate and contradict'),
    dict(param='T_SMOOTH: width of the rounded start of the time multiplier (log points)',
         current_value='n/a (new)', fitted_value='not identified', se='n/a', n='0',
         method='engineering choice: Huber rounding makes the objective C1 at value so bestRatio cannot sit on a kink',
         validation=f'dtMed/drho at value: left {MC["dtMed_drho_left"]:.3f}, right {MC["dtMed_drho_right"]:.3f} days per unit rho; max shortfall vs a pure power law = T_ELAST*T_SMOOTH/2 = {T_REC*H_SMOOTH/2:.4f} log points',
         recommended_value=f'{H_SMOOTH:g} (labelled judgment)'),
]
not_identified = [
    f'The Main-Street size of the time elasticity. The only brokered US per-listing sample (DealLedger; {dlm["n"]} listings, {dlm["events"]} sales, keyed by '
    f'listing) is uninformative: {dlo["beta_above"]["est"]:+.2f} (SE {dlo["beta_above"]["se"]:.2f}) on the sale hazard, no out-of-sample gain. T_ELAST = '
    f'{T_REC:.2f} is a labelled judgment: its sign comes from the online analogs, its size from the conversion to time | close and shrinkage toward zero.',
    'Whether overpricing makes a listing sell LATER or NEVER. A window hazard (Flippa, DealLedger) cannot separate a slower sale clock from a larger fraction '
    'that never sells. The conversion (x P_C) assigns the (1 - P_C) share of the clock effect to never closing, which the console already prices through '
    'Pepperdine\'s P_C penalty; if the whole effect were a never-sells fraction, the time effect would be zero. The converted value is therefore an upper '
    'bound on the time channel, and P_C and T_ELAST remain separate judgments that no source identifies jointly.',
    'Whether the hazard ratio or the time ratio transfers. The conversion -beta/k uses the analog\'s own clock shape (k ~ 1). If the hazard ratio transferred '
    'instead, Main Street\'s steeper clock (the console\'s Weibull k = 1.42; the time_to_close_shape log-logistic beta 2.2-2.8) would cut the time effect by '
    'roughly a third to a half.',
    f'Causal separation of overpricing from unobserved quality. Every relative ask is measured against a hedonic (OOF R2 {r2A:.2f} Flippa, '
    f'{hedE["r2_sale_hedonic"]:.2f} EF), so part of the residual is quality the hedonic cannot see. EF sets its own asks, so the EF residual partly carries '
    'EF\'s private valuation. That is the most likely reason for the V shape: first asks far below the hedonic also sell slowly.',
    'Where the time effect starts relative to model value. The data locate the knot relative to comparables\' typical ask, not relative to a fair value, and '
    'Flippa\'s knot profile is flat from -0.3 to +0.3. Placing the knot at model value (rho = 1) is a modelling choice the task imposes.',
    'The withdrawal response on Main Street. The main conversion assumes overpricing does not change the withdrawal hazard. Flippa\'s multinomial says '
    f'overpriced listings end less often ({MN["ended_vs_open"]["est"]:.2f}); carried over, that would raise the shrunk value to '
    f'{ONE[ONE.conversion.str.contains("withdrawal")].T_ELAST.iloc[0]:.2f}.',
    f'Whether overpricing lengthens the LOI-to-close leg (about {LOI_SHARE:.0%} of the band median; diligence and lender appraisal). The analogs time the '
    'marketing leg. The patch stretches the whole median, so it implicitly gives that leg the same elasticity; if it is unaffected the equivalent '
    f'whole-median value is {ONE[ONE.conversion.str.contains("marketing")].T_ELAST.iloc[0]:.2f}.',
    'The effect of the ask on the ULTIMATE probability of closing. Flippa measures sale within 219 days, EF hides withdrawn listings, and DealLedger observes '
    'sales for six weeks. P_C stays Pepperdine\'s.',
    'Any time effect of underpricing. The task requires zero below value, and the data cannot overturn that: EF\'s slow under-hedonic first asks are most '
    'likely hidden problems.',
    'Size dependence of the elasticity. The analog deals run from micro to about $5M, so no band-specific estimate is possible.',
    'T_SMOOTH, the rounding width, is judgment.',
]
CONST_BLOCK = JS_CONST
implementation = (
    'index.html, last <script>. Exact edits are in results_full.json (F_synthesis.js_edits_model / js_edits_ui, each as [variant, old, new]); unified diffs: '
    f'{OUT}/index.html.diff (repo page) and {OUT}/index_after_time_to_close_shape.html.diff (after fit/time_to_close_shape.py). Every anchor must occur exactly once.\n'
    'MODEL SECTION. (M1) Immediately before `function gapPenalty(gap){` insert:\n' + CONST_BLOCK +
    '(M2) Immediately after `  out.ft=FT;` in model() §9 insert (one scaling of the band median, whatever the curve family):\n' + TBAND_JS +
    '(M3) Weibull page (today): replace `const lamFit=FT.days/Math.pow(Math.log(2),1/KW);` with `const lamFit=tMedA/Math.pow(Math.log(2),1/KW);`. On the first '
    'time_to_close_shape page `const beta=FT.beta, tMd=FT.days;` becomes `const beta=FT.beta, tMd=tMedA;`. The revised time_to_close_shape page pins its curve '
    'to out.tMed, so no edit is needed there. (M4) Replace `out.tMed=FT.days;` with `out.tMed=tMedA;`. After M2-M4, FT.days is read exactly once (in tMedA): '
    'out.ft.days stays the band median, and t90/t180/t365, the curve and its quantiles follow the stretched median. fitTiming, its keying on Vbase, LOI->close, '
    'gapPenalty, fitClose and PEN_MAX are NOT changed. (M5, first time_to_close_shape page only) its comment "nothing here reads the ask" is reworded. '
    '(M6) Immediately before `function applyAll(s0,r0,keys,rho){` insert optNote(s,V,rSell,rKeep) (results_full.json js_edits_model[5]). It writes the '
    'optimiser note from the optimiser\'s own objective U = EVp + (1-P_C) theta V - lamT tMed. It has three branches: same figure; a lower walk-away ask '
    '("the cost of delay pulls the second figure below the proceeds-maximising price ... closes about N days sooner"); and a higher one (the old text, plus '
    '"takes about N days longer to close"). The coin-toss wording fires on the delay-inclusive gain, and no gain is printed below zero.\n'
    'RENDER AND DATA TAB (insertions only, so the texts that time_to_close_shape anchors on stay intact). (U1) After the `<svg id="tcurve" ...></svg>` line add '
    '`<p class="note" id="o_tstretch" style="margin:4px 0 0"></p>`. (U2) Prefix the eq_ts expression with `t_med = t_band e^{T_ELAST h} = ${tn(r.ft.days)} x '
    '${r.tMult.toFixed(3)} = ${tn(r.tMed)} d,`. (U3) Give the "Median time to close" tile tag id="o_t_pv". (U4) After `$("o_t").textContent=...` set that tag '
    'to "aggregate x judgment" (class pv j, with a title) when r.tMult > 1.0005, and fill o_tstretch with the band median and the multiplier. (U5) Replace '
    '`s.rhoSell=bestRatio(s,0,s.lamT);` with `s.rhoSell=bestRatio(s,0,0);`. The business score is priced at rhoSell and its reference population at '
    'bestRatio(..,0,0); without this a median business would stop scoring 50 and the score would move with the delay-cost slider. (U6) Replace the note block '
    '(from `/* "agree" only when the two figures on screen are the same figure */` to `A seller who must exit should use the left-hand number.`;) with '
    '`$("o_listnote").textContent=optNote(s,r.V,rSell,rKeep).text;`. (U7) Insert data_tab_text as its own paragraph before the "Cross-source validation '
    '&mdash; added 2 Oct 2026" title, right after the Model III note. It opens by saying the band median holds at or below model value. (U8) Provenance list, '
    'Time to close: add "Above model value the band median is stretched by a judgment multiplier". (U9, U10) Judgment inventory: add a row "Overpricing time '
    'multiplier (T_ELAST, T_SMOOTH), 2", and nJudg +2. (U11) "What the quality sliders move" adds "and, for an ask above model value, the time to close".\n'
    'TESTS. tests/fuzz.test.js: A.bestRatio(s,0,0) and A.bestRatio({...s,theta:.9},0,0) for the proceeds optimum. tests/model.test.js: rhoSell:A.bestRatio(EX,0,0) '
    'and ask:V*A.bestRatio(s,0,0) in the business-score check. Add tests/overpricing_time.test.js (results_full.json new_test_file).\n'
    'MERGE ORDER with fit/time_to_close_shape.py. Either order works. (a) time_to_close_shape first, then this change: tested here on its current page; every edit '
    'applies and all three test files pass. (b) This change first, then time_to_close_shape: its after-overpricing mode detects `out.tMult=timeMult(s.ask,out.V);` '
    'and rewrites the `const lamFit=tMedA/...` line and the single-line eq_ts by regex; '
    + (f'{ORDER_C["found_in_patched"]} of its {ORDER_C["removed_blocks"]} removed-text anchors are intact on this page '
       f'(the others are the lamFit and eq_ts lines its regexes handle: {ORDER_C["blocks_changed_here"]}). ' if ORDER_C else '') +
    f'Effect on the example business (V = ${MC["V"]/1e6:.2f}M): tMed {rowsMC[1.0]["tMed1"]:.0f} d at value, {rowsMC[1.2]["tMed1"]:.0f} d at 1.2x, {rowsMC[1.5]["tMed1"]:.0f} d at 1.5x, '
    f'{rowsMC[2]["tMed1"]:.0f} d at 2x (was {rowsMC[1.0]["tMed0"]:.0f} d at every ask). Default optimiser setting (lamT $900/day, theta 0.75): walk-away ratio '
    f'{", ".join(f"{r.ratio0:.2f}" for r in opt_def.itertuples())} -> {", ".join(f"{r.ratio1:.2f}" for r in opt_def.itertuples())} for earnings $150k/$400k/$1.45M/$5M; '
    f'at $4,000/day {", ".join(f"{r.ratio1:.2f}" for r in opt_4k.itertuples())}. With lamT = 0 nothing changes.')
test_invariants = [
    'timeMult(ask,V) === 1 exactly for every ask <= V, ask <= 0, NaN, V <= 0 or NaN; model().tMed === fitTiming(Vbase).days there, so the console is unchanged at or below value.',
    'model().tMed === model().ft.days * timeMult(ask, V) everywhere; ft.days and ft.loi do not depend on the ask; FT.days is read exactly once in model() (the tMedA line).',
    'tMed is non-decreasing in the ask (scan rho 0.5..3 in 0.001 steps), strictly increasing above value, and steps by less than 0.5 day per 0.001 of rho; '
    'both one-sided derivatives at value are 0 (|.| < 1 day per unit rho).',
    f'Above the rounding zone the elasticity is exact: ln(tMed(3V)/tMed(1.5V))/ln 2 === T_ELAST to 1e-9, and T_ELAST lies in the documented range {RANGE_LO:.2f}-{RANGE_HI:.2f}.',
    'P_C, EVp, Vmean, Vreal, V, Vbase and omniScore are unchanged by the patch, on the repo page and on the page merged with time_to_close_shape. Only tMed, '
    'lamE, F and t90/t180/t365 move.',
    'On the merged page the log-logistic curve is exactly rescaled: F_merged(t) = F_ttcs(t / tMult), with identical curves at or below value.',
    't90, t180 and t365 are non-increasing in the ask.',
    'A better business (any of the nine quality inputs improved) never has a longer tMed at a fixed ask, because a higher model value narrows the gap.',
    'bestRatio(s,0,0) on the patched model equals the current page\'s bestRatio(s,0,lamT) for lamT in {0,900,4000}. render() computes rhoSell as bestRatio(s,0,0), '
    'and a median business priced there scores 50 at every lamT.',
    'For theta in {0,.2,.75} and lamT in {0,900,4000}: bestRatio(s,theta,lamT) <= bestRatio(s,theta,0) and <= RHO_MAX. The walk-away card is at least as good on '
    'the delay-inclusive objective. optNote returns "same" exactly when the two money figures are equal, "lower" (text names the lower ask and "sooner") when '
    'optRho < rhoSell, and "higher" otherwise. It never prints a negative amount, and its coin-toss flag equals gain < 1% of |U(rhoSell)| with delay included.',
    'Documented knife edge (Data tab): with theta .75 and $900/day the walk-away ask of a $150k-earnings business is below 1.25 for any T_ELAST >= 0.05, while '
    'a $5M business stays at RHO_MAX across the documented range.',
    'Self-audit row "Days on market, main street, fairly priced" unchanged (ask = V); tMed finite for asks 1e-6..1e12 and earnings 5e4..5e7.',
    'Render checks in headless Chromium on both pages: the tile tag reads "aggregate" and the live note is empty at or below value; above value the tag reads '
    '"aggregate x judgment" and the note gives band days x multiplier; the eq_ts equation, scrolled into view and awaited, shows the band days, the current '
    'multiplier and the tile\'s days; at theta 0 and $4,000/day ' +
    ('both cards show the same figure for the example business and the note is the "agree" note (the lower-ask branch of optNote is exercised in '
     'tests/overpricing_time.test.js, e.g. restaurants at $150k)' if all(v['smoke']['theta0_delay4000']['card1'] == v['smoke']['theta0_delay4000']['card2']
                                                                   for v in BROWSER.values()) else 'the note describes the lower walk-away ask') +
    '; no page errors, no KaTeX errors, no NaN/undefined'
    + ('; tests/browser.sweep.js passes on both pages' if not QUICK else '') + '.',
    'Repo tests on both patched pages: ' + '; '.join(f'{lab}: ' + ', '.join(f'{f} {v["tail"]}' for f, v in d_.items()) for lab, d_ in TESTS.items()) + '.',
]
dl_nowin = DLV['id key, exposure from the first snapshot (revision 2 exposure)']
dl_r2 = DLV[[k for k in DLV if 'join error' in k][0]]
dl_rv = DLV[[k for k in DLV if 'review sketch' in k][0]]
one_val = lambda key, col='DealLedger': float(ONE[ONE[col] == key].T_ELAST.iloc[0])
caveats = (
    f'(1) What changed, and the result. T_ELAST = {T_REC:.2f} (was 0.20), a judgment anchored on the analogs\' sign, not an estimate: weight on the analogs '
    f'{w_post:.2f}, posterior sd {sd_post:.2f}, and the 95% interval includes zero. Following review: (a) DealLedger is keyed by listing id; revision 2 keyed on '
    f'the URL, which merged {dl_r2["keys_merging_gt1_id"]} of its {dl_r2["n"]} "listings" (and {dl_r2["sales_on_merged_keys"]} of {dl_r2["events"]} sales). '
    f'(b) Every source is put on the sale-clock scale, pooled, and converted to time to close | close with the console\'s P_C at value ({PC_V:.2f}) BEFORE '
    f'shrinkage; revision 2 shrank the unconverted clock elasticity and compared it with unshrunk converted values. (c) The stated range now covers the '
    f'conversion, the DealLedger choices and leave-one-source-out: {RANGE_LO:.2f}-{RANGE_HI:.2f}. '
    f'(2) Why {T_REC:.2f} and not the reviewer\'s 0.10. The reviewer\'s id-keyed DealLedger sketch, reproduced here ({dl_rv["n"]} listings, '
    f'{dl_rv["events"]} sales, {dl_rv["beta_above"]["est"]:+.2f} on the hazard, {-dl_rv["beta_above"]["est"]:+.2f} in time; {REVIEW_DL_IN_CHAIN:.2f} in this '
    f'chain), carried two further construction errors. First, "sold" is recorded only from {DLCHK["first_sold_status_snapshot"]} (every earlier row reads '
    '"active"), yet exposure was counted from February, so months in which no sale could be observed entered the denominator. Second, duplicate cards for '
    f'one listing in a snapshot sometimes disagree ({DLCHK["cells_with_conflicting_status"]} (snapshot, id) cells with conflicting status). The first-row rule '
    'then turned listings that another card already showed as sold at entry into one-day "sales": '
    f'{DUP_ART["review_sketch"]["sales_sold_at_entry_in_main_panel"]} of its {DUP_ART["review_sketch"]["sales"]}, and they also brought in brokers with no '
    'other sale mark. With the risk window and one record per (snapshot, id), DealLedger is '
    f'{dlo["beta_above"]["est"]:+.2f} (SE {dlo["beta_above"]["se"]:.2f}) on the hazard. In this chain the variants give: listing-specific URLs '
    f'{one_val("id key, listing-specific URLs only"):.2f}, exposure from the first snapshot {one_val("id key, exposure from the first snapshot (revision 2 exposure)"):.2f} '
    f'(the closest to the reviewer\'s sketch), DealLedger excluded {one_val("excluded"):.2f}, and revision 2\'s URL-keyed entry {REV2_DL_IN_CHAIN:.2f}. '
    f'Every DealLedger version has an SE of at least {min(v["beta_above"]["se"] for v in DLV.values()):.2f} and none predicts out of sample, so the choice moves '
    f'T_ELAST within {min(one_val(k) for k in DL_V if k != MAIN[2]):.2f}-{max(one_val(k) for k in DL_V if k != MAIN[2]):.2f}. Flippa on its own time-given-sale '
    f'scale (the reviewer\'s other route) gives {float(ONE[ONE.conversion.str.contains("own scale")].T_ELAST.iloc[0]):.2f}. The main route converts with the '
    'console\'s P_C instead of Flippa\'s 18% sale share, because the clock elasticity is what transfers, while the mix of sale and withdrawal is the '
    'console\'s own (P_C). '
    f'(3) The size rests on Flippa. Of the shrunk {b_post:.3f}, Flippa contributes {CONTRIB["Flippa"]:.3f}, EF {CONTRIB["EF"]:.3f} and DealLedger '
    f'{CONTRIB["DealLedger"]:.3f}; without Flippa the rule gives {LOO_NOFL:.2f}. Flippa\'s 219-day hazard counts listings that never sell, so as a time effect '
    'it is an upper bound that overlaps the Pepperdine P_C penalty. The conversion removes the (1 - P_C) share, but a pure never-sells mechanism would leave '
    'nothing. Double counting check: combined with Pepperdine\'s P_C, the patched console\'s chance of closing within 219 days, relative to an ask at value, is '
    f'{w219("patched", 1.2):.2f} at 1.2x, {w219("patched", 1.5):.2f} at 1.5x and {w219("patched", 2.0):.2f} at 2x. Today it is {w219("current", 1.2):.2f}, '
    f'{w219("current", 1.5):.2f} and {w219("current", 2.0):.2f} (P_C alone). Flippa\'s whole window effect is {CUR[1.2]["p_sale_ratio_flippa_window"]:.2f}, '
    f'{CUR[1.5]["p_sale_ratio_flippa_window"]:.2f} and {CUR[2.0]["p_sale_ratio_flippa_window"]:.2f}. So in Flippa\'s own frame, the console\'s P_C penalty '
    'alone already uses up the window loss at 1.2-2x. That is why T_ELAST is kept small and labelled as judgment, and why the Data tab says so. '
    '(4) Transferability. EF and Flippa are online marketplaces (EF median first ask '
    f'${E.first_ask_est.median()/1e3:.0f}k; Flippa analysis-sample median March ask ${A.mar_ask_hat.median()/1e3:.1f}k). Flippa\'s asks are seller-set; EF '
    'sets its own. They fix the DIRECTION (overpricing slows the sale clock in both) and the SHAPE (little effect below comparables, roughly log-linear '
    'above). They do not fix the Main-Street level. The constant elasticity is set at P_C at value; the same chain at higher asks, where the console\'s P_C is '
    f'lower, gives {STRUCT["1.2"]["shrunk"]:.2f} at 1.2x and {STRUCT["1.5"]["shrunk"]:.2f} at 1.5x, so a constant b is the upper end there. If the hazard '
    'ratio rather than the time ratio transfers, Main Street\'s steeper clock lowers it further. '
    f'(5) EF. The linear slope ({ef_lin["est"]:.2f}) balances the two arms of a V and is fragile: {EF_EST_RNG[0]:.2f} to {EF_EST_RNG[1]:.2f} across '
    f'estimators and outlier trims (top 2.5% of asks dropped {cfE("linear_drop_top_2p5|weibull")["est"]:.2f}; bottom 2.5% dropped '
    f'{cfE("linear_drop_bottom_2p5|weibull")["est"]:.2f}; OLS {cfE("linear|lognormal")["est"]:.2f}; median regression {cfE("linear|median_regression")["est"]:.2f}), '
    f'and by listing year {by_year_txt}. It therefore enters with the largest SE across estimators ({ef_lin_se:.2f}). The robust evidence is the top quintile '
    f'of first asks (+{q4E["est"]:.2f} log-days, SE {q4E["se"]:.2f}) and the much higher rate of multiple cuts among overpriced first asks (logit '
    f'{rc.params["rho_sale_p"]:.2f}, SE {rc.bse["rho_sale_p"]:.2f}; {QT.cut_share.iloc[0]:.0%} in the lowest quintile vs {QT.cut_share.iloc[-1]:.0%} in the '
    f'highest). Out of sample the ask is negligible: 10-fold CV {d_cv:+.4f} per listing, 2023-25H1 hold-out with the hedonic fitted on 2019-22 only '
    f'{d_ho:+.4f}, truncation-adjusted {d_hot:+.4f}. Revision 2\'s re-based subsamples were defined by the outcome and are dropped; the listing-year halves '
    f'give {cfE("subsample_listed_2019_2021_linear|weibull")["est"]:.2f} (2019-21) and {cfE("subsample_listed_2022_2025H1_linear|weibull")["est"]:.2f} '
    f'(2022-25H1). EF\'s days on market time the marketing leg (frozen when the listing goes off the marketplace). EF contributes only {CONTRIB["EF"]:.3f} of '
    'the result. The LAST ask and the API\'s final-state covariates leak the outcome and are not used (contrast hinge '
    f'{fp("contrast_final_state_covariates_hinge|weibull")}). '
    f'(6) Flippa calibration. The reconstructed March ask is E[ask | price rank], so its error is closer to Berkson than classical (slope of the true log '
    f'ask on the reconstruction {CAL["slope_true_on_hat_logask"]:.2f}). The reference listings carry exact asks, so only the other '
    f'{CAL["substitution"]["nonreference_n"]:,} listings are calibrated, by substituting E[true | reconstructed]. That gives {bA_rc:.3f} instead of revision 2\'s '
    f'{bA_rc2:.3f}, which over-corrected the exact third. Reference status is selected on the outcome (never cut, still listed in October: '
    f'{CAL["reference_sale_rate"]:.1%} sold against {CAL["nonreference_sale_rate"]:.0%}). Group-specific slopes are therefore not interpretable, and the '
    f'full cohort is kept. Giving every listing the same rank reconstruction, so that the error is not differential, gives {rA_u.params["ucal_p"]:.3f} after '
    f'calibration; the non-reference listings alone give {rA_nr.params["cal_p"]:.3f}. Converting to time uses EF\'s k = {k_mkt:.2f}; Flippa\'s own profile k is '
    f'{FLIPPA_K["k_hat"]:.2f} ({FLIPPA_K["ci95"][0]:.2f}-{FLIPPA_K["ci95"][1]:.2f}), weakly identified because age on market and the vintage control '
    f'correlate at {FLIPPA_K["corr_log_age_on_market_vs_id_rank"]:.2f}. '
    f'(7) DealLedger. It carries {W_SRC["DealLedger"]:.0%} of the pooling weight (the between-source sd of {TAU0:g} swamps its own SE) and moves the shrunk '
    f'value by {dl_pull:+.3f}; revision 2\'s "little weight" was wrong. Its sale window is six weeks ({DLCHK["snapshots_in_window"]} snapshots); '
    f'{dlm["share_sold_with_1day_exposure"]:.0%} of its sales have a 1-day exposure, and the top broker supplies {dlm["top_broker_sales"]} of '
    f'{dlm["events"]} sales. AUC and concordance are now computed on the rate without the outcome-dependent exposure offset. '
    f'(8) Aggregates. IBBA band x quarter cells give d ln(months)/d ln(ask/price) = {RES["E_ibba_ecological"]["slope_band_and_quarter_FE"]["est"]:.2f} '
    f'(SE {RES["E_ibba_ecological"]["slope_band_and_quarter_FE"]["se"]:.2f}). It is ecological and reverse-causal (slow deals get cut, so realized/ask falls '
    'because of time) and is not informative about direction. In the Flippa 2019 auctions, a start price above the type median lowers the sale probability '
    f'(logit {RES["B_flippa_2019_auctions"]["beta_start_price_above_type_median"]["est"]:.2f}, SE '
    f'{RES["B_flippa_2019_auctions"]["beta_start_price_above_type_median"]["se"]:.2f}) but adds nothing out of sample. '
    '(9) gapPenalty shape. The analogs corroborate that the closing probability falls monotonically with the ask, and that pricing below comparables earns '
    f'little (below-slope {abs(rA_rc.params["cal_n"] / bA_rc):.2f} of the above-slope). The 219-day window ratio at 2x '
    f'({CUR[2.0]["p_sale_ratio_flippa_window"]:.2f}) matches the console\'s P_C ratio ({CUR[2.0]["pepperdine_pc_ratio_c0"]:.2f}). Mapped through competing '
    f'risks at a 61% base, the Flippa hazard implies an ultimate-close ratio of {CUR[2.0]["ultimate_ratio_withdrawal_unaffected"]:.2f}-'
    f'{CUR[2.0]["ultimate_ratio_withdrawal_as_mnlogit"]:.2f} at 2x and {CUR[1.2]["ultimate_ratio_withdrawal_unaffected"]:.2f} at 1.2x, against the console\'s '
    f'{CUR[1.2]["pepperdine_pc_ratio_c0"]:.2f}. Pepperdine measures where negotiated deals die among broker-priced listings, a more relevant population, so '
    'it is kept and the disagreement noted. '
)
caveats += ('(10) Behavioural consequence and the knife edge. The expected-proceeds optimum and every lamT = 0 optimum are unchanged. With theta 0.75 the '
            f'utility optimum was the RHO_MAX corner at every size; at $900/day it becomes {", ".join(f"{r.ratio1:.2f}" for r in opt_def.itertuples())} and at '
            f'$4,000/day {", ".join(f"{r.ratio1:.2f}" for r in opt_4k.itertuples())} for earnings $150k/$400k/$1.45M/$5M. The switch is a knife edge already in '
            f'the model: on today\'s page at lamT = 0 the patient-seller ask is {KNIFE["current_page_lamT0_theta070"]:.2f}x at theta 0.70 and '
            f'{KNIFE["current_page_lamT0_theta075"]:.2f}x at 0.75 (the default). For small deals any positive T_ELAST tips it (from {sw_min:.2f}), so the switch '
            'does not measure T_ELAST. At $900/day it happens from T_ELAST = ' +
            ', '.join(f'{SWITCH[int(e)]["first_T_below_1p45"]:.2f} ({money_s(e)})' for e in SIZES if SWITCH[int(e)]['first_T_below_1p45'] is not None) +
            (f', and the walk-away ask jumps from about {KNIFE["patched_ratio_below_jump"]:.2f}x to the cap as earnings pass about '
             f'{money_s(KNIFE["patched_jump_earnings"])} (F_walkaway_by_earnings.csv)' if KNIFE['patched_jump_earnings'] else '') +
            '. The Data tab says this, and a test pins it. The note uses the delay-inclusive utility. For the $1.45M example at the default settings, the gain '
            f'shown is ${NOTEX.gain:,.0f} against a coin-toss threshold of ${NOTEX.threshold:,.0f}; the old formula showed ${NOTEX.old_gain_without_delay:,.0f}. '
            f'With theta 0 and $900/day at $150k of earnings the walk-away ask ({NOTE150.optRho:.3f}x) sits below the proceeds optimum ({NOTE150.rhoSell:.3f}x), '
            'and the note says the cost of delay pulls it down. '
            f'(11) LOI-to-close. The patch stretches the whole listing-to-close median, LOI-to-close included (about {LOI_SHARE:.0%} of it). The analogs time '
            'the marketing leg, so this folds in a mismatch, which the comment and the Data tab disclose. Stretching only the marketing leg (tMed = LOI + '
            f'(band - LOI) x timeMult) would add {LOI_SHARE:.0%} fewer days; equivalently, T_ELAST would be '
            f'{ONE[ONE.conversion.str.contains("marketing")].T_ELAST.iloc[0]:.2f}. It is not implemented because fit/time_to_close_shape.py, when applied after '
            'this change, writes the hard-coded equation t_med = t_band e^{T_ELAST h} = t_band x tMult, which would then be wrong; the whole-median form keeps '
            'both merge orders consistent. On Main Street the LOI leg plausibly also lengthens (lender appraisal gaps on overpriced deals), but no source '
            'measures it. '
            '(12) Composition with fit/time_to_close_shape.py. The tested merged page is its patched/index.html as of this run '
            + (f'(sha256 {MERGED["base_sha256"][:12]}). ' if MERGED else '(not available in this run). ') +
            'The Model III amendment ("lands on the band median at or below model value") is made as a separate paragraph that opens the "Overpricing costs '
            'time" note, because the time_to_close_shape change anchors on the Model III text; the same holds for the lede, the equation label and the ledger row.')
RESULT = dict(name='overpricing_time', script='/home/user/last-minute/fit/overpricing_time.py', parameters=params,
              not_identified=not_identified, implementation=implementation, data_tab_text=DATA_TAB,
              test_invariants=test_invariants, caveats=caveats)
json.dump(RESULT, open(os.path.join(OUT, 'RESULT.json'), 'w'), indent=1)
say('wrote', os.path.join(OUT, 'RESULT.json'))
LOG.close()
