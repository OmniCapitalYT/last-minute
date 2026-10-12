#!/usr/bin/env python3
"""SBA 7(a) acquisition-loan risk and rate refresh (fit5 / sba_risk_refresh).

Run:  python3 -I /home/user/last-minute/fit/sba_risk_refresh.py
Inputs (read-only, absolute paths):
  /tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv   SBA 7(a) FOIA as of 2026-06-30, change-of-ownership loans
  /tmp/claude-0/data5/sba_foia/clean/prime_rate_daily_h15.csv           Fed H.15 bank prime, daily, to 2026-10-02
  /tmp/claude-0/data5/sba_foia/raw/FOIA_7a_FY2000_FY2009_asof_260630.csv  all 7(a) loans (through-the-cycle vintages)
  /tmp/claude-0/data5/sba_foia/raw/FOIA_7a_FY2010_FY2019_asof_260630.csv  all 7(a) loans (tail shape, like-for-like comparison)
  /tmp/claude-0/data5/sba_foia/raw/FOIA_7a_FY2020_Present_asof_260630.csv
  /home/user/last-minute/index.html (read only: current MODELS.risk, to score the current model on the same holdouts)
Outputs: /tmp/claude-0/fit5/sba_risk_refresh/  (fits.json, tables, run.log, patched copy of index.html + tests, RESULT.json)

What it does
  1. Prime: current H.15 value and the date it took effect.
  2. Spread over prime by loan size from FY2025-26 change-of-ownership term loans (variable; fixed reported apart):
     median regression on a tent basis in ln(loan), made non-increasing (PAV), FY2025->FY2026 holdout. Rates heap at
     quarter points, so the bootstrap SE understates knot uncertainty; the reported uncertainty is the larger of the
     bootstrap SE and the sample-choice range (disbursed only, FY2025 only, FY2026 only, FY2018-26).
  3. Charge-off risk with censoring handled: cause-specific piecewise-exponential hazards (charge-off; paid-in-full as the
     competing event; open loans censored at 2026-06-30) by months on book, covariates ln(loan) with an effect that
     fades with months on book (to 72 months), franchise, spread over prime, fixed-rate, calendar-year terms
     (2019-2022 vs 2023-26 = current conditions), sector random effects (Schall/EM-estimated variance), NAICS-6-within-
     sector and state effects by Poisson-gamma empirical Bayes. Staffing (SBA JobsSupported) is fitted as a check only:
     the console's head count (Census employees per revenue) is a different measure, so it is not a model input. SEs: Hessian, and sandwich clustered by loan, lender,
     calendar quarter and two-way lender x quarter (shipped: the largest of Hessian, lender and two-way). Cumulative incidence of
     charge-off at 60 and 96 months; the 10-year term borrows years 9-10 from mature FY2010-15 7(a) vintages,
     size-matched to the acquisition mix (judgment SE). Validation: 5-fold CV by loan, vintage holdout (train FY2018-21,
     test FY2022-24), calendar holdout (train before 2024-07-01, forecast 2024-07..2026-06), with the sector variance
     re-estimated inside every split; calibration by decile, by vintage and by loan band x age. The out-of-time slope on
     the loan-level log hazard (pooled over the two holdouts) shrinks every loan-level effect toward the population.
     The level shift is solved so that the console's own pricing (table spread, variable note, 2023-26 conditions,
     shrunk) of every FY2024-26 acquisition loan averages the fitted 5-year level of that book (fixed-rate notes at
     their own fitted hazard); base_cif is that console-priced mean, so rel averages 1 over the book. Sensitivity of the
     population level to the specification (calendar vs approval-cohort terms, payoff-hazard prime term, payoff
     censoring at 2026-03-31, all censoring at 2025-12-31) and to the reference period (2023-24 vs 2025-26 charge-off
     and payoff conditions; quarter effects), a model without the spread (the marginal risk given size), the share of
     real-estate-term notes by loan band, the rate level given the spread, lender fixed effects, and through-the-cycle
     10-year charge-off by vintage FY2000-16 (all 7(a) term loans >= $150k).
  4. LGD (gross charge-off / original approval) by size: fractional logit with bootstrap SEs, CV and temporal holdout.
"""
import json, math, os, re, shutil, subprocess, sys, time, warnings
import numpy as np
import pandas as pd
from scipy import optimize, special, stats
import statsmodels.api as sm

warnings.filterwarnings('ignore')
T0 = time.time()
OUT = '/tmp/claude-0/fit5/sba_risk_refresh/'
SBA = '/tmp/claude-0/data5/sba_foia/'
REPO = '/home/user/last-minute/'
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + 'run.log', 'w')
ASOF = pd.Timestamp('2026-06-30')
MPD = 30.4375  # days per month
RNG = np.random.default_rng(20261010)


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n'); LOG.flush()


def r4(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else float(round(float(x), 4))


# ----------------------------------------------------------------------------------------------------------------
# 0. data
# ----------------------------------------------------------------------------------------------------------------
pr = pd.read_csv(SBA + 'clean/prime_rate_daily_h15.csv', parse_dates=['date']).sort_values('date').reset_index(drop=True)
PR_D = pr.date.values.astype('datetime64[D]').astype(np.int64)
PR_V = pr.prime_rate_pct.values


def prime_on(days):
    return PR_V[np.clip(np.searchsorted(PR_D, days, side='right') - 1, 0, len(PR_V) - 1)]


def prime_month(days):
    """the base rate SBA rules peg a variable 7(a) rate to: the prime "in effect on the first business day of the month"
    (13 CFR 120.214(c); SOP 50 10 8 Sec. B Ch. 1 Para. B.4.a.v, as amended by Procedural Notice 5000-875051), i.e. the
    H.15 prime on the first H.15 business day on or after the 1st of the month containing `days` (int days since epoch).
    Rate adjustments after disbursement use the same rule for the adjustment month (120.214(a))."""
    m1 = np.asarray(days, dtype=np.int64).astype('datetime64[D]').astype('datetime64[M]').astype('datetime64[D]').astype(np.int64)
    return PR_V[np.clip(np.searchsorted(PR_D, m1, side='left'), 0, len(PR_V) - 1)]


chg = pr.prime_rate_pct.ne(pr.prime_rate_pct.shift())
PRIME_NOW = float(pr.prime_rate_pct.iloc[-1])
PRIME_SINCE = str(pr.date[chg].iloc[-1].date())
PRIME_LAST_OBS = str(pr.date.iloc[-1].date())
prime_changes = pr[chg].tail(12)
say('== 1. prime: %.2f%% since %s (H.15 through %s)' % (PRIME_NOW, PRIME_SINCE, PRIME_LAST_OBS))

raw = pd.read_csv(SBA + 'clean/sba7a_chow_loans_fy2018_2026.csv', low_memory=False,
                  dtype={'NaicsCode': str, 'naics2': str, 'naics4': str, 'BorrZip': str, 'FranchiseCode': str},
                  parse_dates=['ApprovalDate', 'FirstDisbursementDate', 'start_date', 'ChargeOffDate', 'PaidInFullDate'])
say('CHOW file rows', len(raw))
# The clean file's prime_at_approval / spread_over_prime use the H.15 prime ON the approval date. SBA rules set a variable
# 7(a) rate as base rate + spread with the base "the prime rate ... in effect on the first business day of the month"
# (13 CFR 120.214(c); SOP 50 10 8 Sec. B Ch. 1 Para. B.4.a.v.b.iii, PN 5000-875051), so a loan approved after a mid-month
# prime change is priced off the month-start prime. Recompute both on that rule (approval month; FOIA has no application
# date), and check it on the data: in months with a mid-month change, loans approved after the change should show the same
# spread as those approved before it under the right convention.
_ad = raw.ApprovalDate.values.astype('datetime64[D]').astype(np.int64)
raw['prime_h15_approval_date'] = prime_on(_ad)
raw['prime_at_approval'] = prime_month(_ad)
raw['spread_over_prime'] = (raw.InitialInterestRate - raw.prime_at_approval).round(4)
_tv = (raw.RevolverStatus == 0) & raw.InitialInterestRate.gt(0)
_dif = (raw.prime_at_approval - raw.prime_h15_approval_date).abs()
PRIME_RULE = {'rule': 'prime in effect on the first business day of the approval month (H.15), the base 13 CFR 120.214(c) and SOP 50 10 8 '
                      'Sec. B Ch. 1 Para. B.4.a.v (PN 5000-875051) peg variable 7(a) rates to; previously the H.15 prime on the approval date',
              'citation': ['13 CFR 120.214(c) (eCFR, current 2026-10-01): "The prime rate will be that which is in effect on the first business '
                           'day of the month, as printed in a national financial newspaper published each business day."',
                           'SOP 50 10 8 Sec. B, Ch. 1, Para. B.4.a.v.b.iii as amended by SBA Procedural Notice 5000-875051 (eff. 2026-03-01): '
                           '"The Prime Rate will be that rate which is in effect on the first business day of the month, as identified in a '
                           'national financial newspaper or website."',
                           '13 CFR 120.214(d): the initial maximum allowable rate is determined as of the date SBA receives the application'],
              'share_changed_term_loans': float(np.mean(_dif[_tv] > 1e-9)),
              'share_changed_variable_fy2025_26': float(np.mean(_dif[_tv & (raw.FixedorVariableInterestInd == 'V') & (raw.ApprovalFY >= 2025)] > 1e-9)),
              'abs_change_counts': {('%.2f' % k): int(v) for k, v in _dif[_tv & (_dif > 1e-9)].round(2).value_counts().sort_index().items()}}
# empirical check: months with a mid-month prime change (FY2018-26), variable term loans approved in that month after vs before it
_vv = raw[_tv & (raw.FixedorVariableInterestInd == 'V')]
_chg = pr[pr.prime_rate_pct.ne(pr.prime_rate_pct.shift())]
_chg = _chg[(_chg.date >= '2017-10-01') & (_chg.date <= ASOF)]
_rows = []
for _, c in _chg.iterrows():
    if c.date.day == 1: continue
    m_ = _vv.ApprovalDate.dt.to_period('M') == c.date.to_period('M')
    post, pre = _vv[m_ & (_vv.ApprovalDate >= c.date)], _vv[m_ & (_vv.ApprovalDate < c.date)]
    if len(post) < 10 or len(pre) < 10: continue
    dP = float(c.prime_rate_pct - prime_on(np.array([np.datetime64(c.date.date(), 'D').astype(np.int64) - 1]))[0])
    _rows.append({'change': str(c.date.date()), 'dprime': dP, 'n_pre': len(pre), 'n_post': len(post),
                  'pre_mean': float(pre.spread_over_prime.mean()),
                  'post_mean_month_rule': float(post.spread_over_prime.mean()),
                  'post_mean_approval_date': float((post.InitialInterestRate - post.prime_h15_approval_date).mean())})
_pc = pd.DataFrame(_rows)
_w = _pc.n_post.values
_slope = lambda y: float(np.sum(_w * _pc.dprime * y) / np.sum(_w * _pc.dprime ** 2))   # share of the prime move seen in the spread
PRIME_RULE['midmonth_check'] = {
    'months': int(len(_pc)), 'loans_after_change': int(_pc.n_post.sum()),
    'slope_post_minus_pre_on_dprime_month_rule': _slope(_pc.post_mean_month_rule - _pc.pre_mean),
    'slope_post_minus_pre_on_dprime_approval_date': _slope(_pc.post_mean_approval_date - _pc.pre_mean),
    'mean_abs_gap_month_rule': float(np.average(np.abs(_pc.post_mean_month_rule - _pc.pre_mean), weights=_w)),
    'mean_abs_gap_approval_date': float(np.average(np.abs(_pc.post_mean_approval_date - _pc.pre_mean), weights=_w)),
    'by_month': [{k: (r4(v) if isinstance(v, float) else v) for k, v in r.items()} for r in _rows]}
say('prime reference date: %s' % PRIME_RULE['rule'])
say('  term loans whose base changes: %.3f (variable FY2025-26 %.3f); |change| counts %s' % (
    PRIME_RULE['share_changed_term_loans'], PRIME_RULE['share_changed_variable_fy2025_26'], PRIME_RULE['abs_change_counts']))
say('  mid-month check (%d months, %d loans approved after a change): share of the prime move that shows up in the post-vs-pre '
    'spread gap: month rule %.3f, approval-date prime %.3f; mean |gap| %.3f vs %.3f pp' % (
        PRIME_RULE['midmonth_check']['months'], PRIME_RULE['midmonth_check']['loans_after_change'],
        PRIME_RULE['midmonth_check']['slope_post_minus_pre_on_dprime_month_rule'], PRIME_RULE['midmonth_check']['slope_post_minus_pre_on_dprime_approval_date'],
        PRIME_RULE['midmonth_check']['mean_abs_gap_month_rule'], PRIME_RULE['midmonth_check']['mean_abs_gap_approval_date']))

# ----------------------------------------------------------------------------------------------------------------
# 1. spread over prime by loan size, FY2025-26 approvals
# ----------------------------------------------------------------------------------------------------------------
say('\n== 2. spreads over prime (term loans, spread within [-2,10] pp)')
sp = raw[(raw.RevolverStatus == 0) & raw.spread_over_prime.between(-2, 10) & raw.InitialInterestRate.gt(0)].copy()
sp['x'] = np.log(sp.GrossApproval)
SP_KNOTS_USD = [1e5, 3e5, 6e5, 1.2e6, 2.5e6, 4.5e6]
SPK = np.log(SP_KNOTS_USD)


def tent(x, K=SPK):
    """piecewise-linear 'tent' basis: coefficient j = value at knot j, flat outside [K0,Kn]."""
    x = np.clip(x, K[0], K[-1])
    B = np.zeros((len(x), len(K)))
    for j in range(len(K)):
        if j > 0:
            m = (x >= K[j - 1]) & (x <= K[j]); B[m, j] = (x[m] - K[j - 1]) / (K[j] - K[j - 1])
        if j < len(K) - 1:
            m = (x >= K[j]) & (x < K[j + 1]); B[m, j] = (K[j + 1] - x[m]) / (K[j + 1] - K[j])
    B[x >= K[-1], -1] = 1.0
    return B


def pav_dec(v, w):
    """weighted pool-adjacent-violators, non-increasing."""
    v = list(map(float, v)); w = list(map(float, w)); blocks = [[v[i], w[i], 1] for i in range(len(v))]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] < blocks[i + 1][0] - 1e-12:
            a, b = blocks[i], blocks[i + 1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / (a[1] + b[1]), a[1] + b[1], a[2] + b[2]]; del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    out = []
    for val, _, c in blocks: out += [val] * c
    return np.array(out)


def fit_spread(df):
    B = tent(df.x.values)
    r = sm.QuantReg(df.spread_over_prime.values, B).fit(q=0.5, max_iter=5000)
    return pav_dec(r.params, B.sum(0))


def lerp_knots(x, K, V):
    return np.interp(np.clip(x, K[0], K[-1]), K, V)


SPREAD_ROWS = []
spread_res = {}
for fv in ['V', 'F']:
    s = sp[(sp.ApprovalFY >= 2025) & (sp.FixedorVariableInterestInd == fv)]
    tab = s.groupby('size_band').spread_over_prime
    for band, g in tab:
        bs = [np.median(RNG.choice(g.values, len(g))) for _ in range(500)]
        SPREAD_ROWS.append({'type': fv, 'size_band': band, 'n': len(g), 'p25': g.quantile(.25), 'median': g.median(),
                            'p75': g.quantile(.75), 'mean': g.mean(), 'se_median_boot': np.std(bs)})
    kv = fit_spread(s)
    boots = np.array([fit_spread(s.sample(len(s), replace=True, random_state=int(RNG.integers(1e9)))) for _ in range(200)])
    spread_res[fv] = {'n': int(len(s)), 'knots_usd': SP_KNOTS_USD, 'values': kv.tolist(), 'se': boots.std(0).tolist(),
                      'median_all': float(s.spread_over_prime.median()), 'mean_all': float(s.spread_over_prime.mean()),
                      'status_counts': s.LoanStatus.value_counts().to_dict()}
    say(fv, 'n', len(s), 'knot medians', np.round(kv, 3), 'boot SE', np.round(boots.std(0), 3), 'status', spread_res[fv]['status_counts'])
    # rates heap at quarter points (prime + 2.75, 2.50, 2.00 ...), so bootstrap medians stick to mass points and the
    # bootstrap SE understates how much the knots depend on the sample. Refit on reasonable alternative samples.
    sall = sp[sp.FixedorVariableInterestInd == fv]
    alts = {'disbursed_only': s[~s.LoanStatus.isin(['CANCLD', 'COMMIT'])], 'FY2025_only': s[s.ApprovalFY == 2025],
            'FY2026_only': s[s.ApprovalFY == 2026], 'FY2018_26': sall}
    alt_k = {k: fit_spread(v).tolist() for k, v in alts.items()}
    dev_ = np.max(np.abs(np.array(list(alt_k.values())) - kv[None, :]), axis=0)
    spread_res[fv]['alt_samples'] = {k: {'n': int(len(alts[k])), 'values': v} for k, v in alt_k.items()}
    spread_res[fv]['sample_range'] = dev_.tolist()
    spread_res[fv]['unc'] = np.maximum.reduce([boots.std(0), dev_, np.full(len(kv), 0.05)]).tolist()   # 0.05 pp floor: heaped rates
    say('   alternative samples', {k: np.round(v, 2).tolist() for k, v in alt_k.items()}, 'max |dev|', np.round(dev_, 3))
    if True:
        say('   share of loans at the three most common spreads', s.spread_over_prime.round(2).value_counts(normalize=True).head(3).round(3).to_dict())
spread_band_tab = pd.DataFrame(SPREAD_ROWS)
_sv_old = sp[(sp.ApprovalFY >= 2025) & (sp.FixedorVariableInterestInd == 'V')].copy()
_sv_old['spread_over_prime'] = _sv_old.InitialInterestRate - _sv_old.prime_h15_approval_date
PRIME_RULE['knots_approval_date_prime'] = fit_spread(_sv_old).tolist()
say('knots with the approval-date prime (previous definition):', np.round(PRIME_RULE['knots_approval_date_prime'], 3), ' month-start rule:', np.round(spread_res['V']['values'], 3))
spread_band_tab.to_csv(OUT + 'spread_by_band_fy2025_26.csv', index=False)
say(spread_band_tab.round(3).to_string())
# drift by FY (variable)
drift = sp[sp.FixedorVariableInterestInd == 'V'].groupby('ApprovalFY').spread_over_prime.agg(['size', 'median', 'mean']).round(3)
say('variable spread by FY\n' + drift.to_string())
# validation: temporal FY2025 -> FY2026, and 5-fold CV on FY2025-26 (variable)
CUR_SPREAD = [[11.512925464970229, 2.0], [13.527828485512494, 2.0], [14.22097566607244, 1.75], [15.068273526459642, 1.5]]
v25 = sp[(sp.ApprovalFY == 2025) & (sp.FixedorVariableInterestInd == 'V')]
v26 = sp[(sp.ApprovalFY == 2026) & (sp.FixedorVariableInterestInd == 'V')]
k25 = fit_spread(v25)
mae = lambda y, p: float(np.mean(np.abs(y - p)))
cK = np.array([k[0] for k in CUR_SPREAD]); cV = np.array([k[1] for k in CUR_SPREAD])
spread_val = {
    'holdout_FY2026_n': int(len(v26)),
    'mae_new_fit_on_FY2025': mae(v26.spread_over_prime, lerp_knots(v26.x.values, SPK, k25)),
    'mae_current_FY2023_knots': mae(v26.spread_over_prime, lerp_knots(v26.x.values, cK, cV)),
    'mae_flat_FY2025_median': mae(v26.spread_over_prime, np.median(v25.spread_over_prime)),
    'bias_current_knots_pp': float(np.mean(v26.spread_over_prime - lerp_knots(v26.x.values, cK, cV))),
    'bias_new_pp': float(np.mean(v26.spread_over_prime - lerp_knots(v26.x.values, SPK, k25))),
}
vv = sp[(sp.ApprovalFY >= 2025) & (sp.FixedorVariableInterestInd == 'V')].reset_index(drop=True)
fold = RNG.integers(0, 5, len(vv)); cvp = np.zeros(len(vv))
for f in range(5):
    kf = fit_spread(vv[fold != f]); cvp[fold == f] = lerp_knots(vv.x.values[fold == f], SPK, kf)
spread_val['cv5_mae_new'] = mae(vv.spread_over_prime, cvp)
spread_val['cv5_mae_current_knots'] = mae(vv.spread_over_prime, lerp_knots(vv.x.values, cK, cV))
say('spread validation', {k: r4(v) if isinstance(v, float) else v for k, v in spread_val.items()})
# SBA maximum allowed spreads (variable; SOP 50 10 7.1, loans approved from 2023): context only
SBA_MAX_SPREAD = {'<=50k': 6.5, '50-250k': 6.0, '250-350k': 4.5, '>350k': 3.0}
_ga = vv.GrossApproval.values
cap_ = np.select([_ga <= 5e4, _ga <= 2.5e5, _ga <= 3.5e5], [SBA_MAX_SPREAD['<=50k'], SBA_MAX_SPREAD['50-250k'], SBA_MAX_SPREAD['250-350k']],
                 SBA_MAX_SPREAD['>350k'])
frac_above_cap = float(np.mean(vv.spread_over_prime.values > cap_ + 1e-9))
say('share of FY2025-26 variable loans above the SBA max spread for their size: %.4f' % frac_above_cap)

# ----------------------------------------------------------------------------------------------------------------
# 2. competing-risk hazard data
# ----------------------------------------------------------------------------------------------------------------
say('\n== 3. charge-off hazard (PIF competing, open loans censored at 2026-06-30)')
d = raw[raw.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (raw.months_on_book >= 0) & (raw.RevolverStatus == 0)
        & raw.InitialInterestRate.gt(0) & raw.spread_over_prime.between(-2, 10)].copy().reset_index(drop=True)
excl = {'all_disbursed_chow': int((raw.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (raw.months_on_book >= 0)).sum()),
        'revolvers_dropped': int(((raw.RevolverStatus == 1) & raw.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT'])).sum())}
d['ev'] = d.LoanStatus.map({'EXEMPT': 0, 'CHGOFF': 1, 'PIF': 2}).astype(int)
st_day = d.start_date.values.astype('datetime64[D]').astype(np.int64)
asof_day = np.datetime64('2026-06-30', 'D').astype(np.int64)
d['C'] = (asof_day - st_day) / MPD                       # administrative follow-up (months)
d['T'] = np.minimum(np.maximum(d.months_on_book.values, 0.01), np.maximum(d.C.values, 0.01))
fx = (d.FixedorVariableInterestInd.values == 'F').astype(float)
g2 = d.naics2.fillna('00').astype(str).replace({'32': '31', '33': '31', '45': '44', '49': '48'}).values
SECS = sorted(set(g2))
sec_ix = np.array([SECS.index(s) for s in g2])
d['g2'] = g2
d['state'] = d.ProjectState.fillna(d.BorrState).fillna('NA').astype(str)
d['n6'] = d.NaicsCode.fillna('000000').astype(str).str[:6]
SPREAD_CLIP = (float(np.quantile(d.spread_over_prime, .005)), 3.0)   # hazard is flat in spread above 3 pp (hinge test below)
SPREAD_P995 = float(np.quantile(d.spread_over_prime, .995))
CENT = {'ln_loan': math.log(650000.0), 'ln1p_jobs': math.log(9.0), 'spread': 2.25}
LV = {  # loan-level covariates (centred)
    'lnamt': np.log(d.GrossApproval.values) - CENT['ln_loan'],
    'lnjobs': np.log1p(np.clip(d.JobsSupported.values, 0, 100)) - CENT['ln1p_jobs'],
    'franchise': d.is_franchise.values.astype(float),
    'spread': np.clip(d.spread_over_prime.values, *SPREAD_CLIP) - CENT['spread'],
    'fixed': fx,
}
LV['spread_x_fixed'] = LV['spread'] * fx
LV['spread_above3'] = np.maximum(np.minimum(d.spread_over_prime.values, SPREAD_P995) - 3.0, 0)
LV['jobs_linear'] = np.clip(d.JobsSupported.values, 0, 100) - 8.0
LV['express'] = (d.ProcessingMethod.values == 'SBA Express Program').astype(float)
prime0 = d.prime_at_approval.values
say('loans', len(d), 'events', np.bincount(d.ev.values).tolist(), 'spread clip', SPREAD_CLIP, excl)

EDGES = np.array([0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 72, 84], float)
NB = len(EDGES)
CAL_YEARS = [2019, 2020, 2021, 2022]   # 2018 merged into 2019 (few exposures); 2023-26 is the reference = current conditions
W = 3.0


def pieces(a0, a1, start_day):
    """split [a0,a1) months on book of each loan on the global 3-month grid. returns loan index, piece start, length,
    bucket and calendar year (float) of the piece midpoint."""
    k0 = np.floor(a0 / W).astype(int); k1 = np.maximum(np.ceil(a1 / W).astype(int), k0 + 1)
    n = k1 - k0
    i = np.repeat(np.arange(len(a0)), n)
    k = k0[i] + (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n))
    s = np.maximum(k * W, a0[i]); e = np.minimum(k * W + W, a1[i]); dt = e - s
    b = np.searchsorted(EDGES, k * W, side='right') - 1
    mid = start_day[i] + (s + dt / 2) * MPD
    cy = 1970 + mid / 365.2425
    return i, s, dt, b, cy, mid


AGE_CAP, AGE_C = 72.0, 4.0   # the size effect changes linearly with years on book up to 6 years, centred at 4 (selected below)


def age_term(b):
    """years on book at the start of hazard piece b, capped at AGE_CAP, minus AGE_C (multiplies ln loan)."""
    return np.minimum(EDGES[b], AGE_CAP) / 12.0 - AGE_C


def panel(rows, a0, a1, ev):
    """person-piece panel for loans `rows` observed from age a0 to a1 (months) with event code ev (0 censor, 1 CO, 2 PIF)
    at a1. Piece-level covariates: prime change since approval (variable loans) and ln loan x years on book."""
    i, s, dt, b, cy, mid = pieces(a0, a1, st_day[rows])
    last = np.zeros(len(i), bool); last[np.r_[np.flatnonzero(np.diff(i)), len(i) - 1]] = True
    y = np.where(last, ev[i], 0)
    keep = dt > 1e-9
    i, dt, b, cy, mid, y = i[keep], dt[keep], b[keep], cy[keep], mid[keep], y[keep]
    loan = rows[i]
    P = {'loan': loan, 'dt': dt, 'b': b, 'cy': cy, 'y': y}
    P['dprimeV'] = (prime_month(mid.astype(np.int64)) - prime0[loan]) * (1 - fx[loan])   # base resets on the month-start prime
    P['lnamt_x_age'] = LV['lnamt'][loan] * age_term(b)
    return P


def build_panel(rows, T, ev):
    """person-piece panel from origination to T."""
    return panel(rows, np.zeros(len(rows)), T, ev)


def cal_mat(cy):
    yr = np.clip(np.floor(cy).astype(int), 2019, 2100)
    return np.column_stack([(yr == y).astype(float) for y in CAL_YEARS])


# ----------------------------------------------------------------------------------------------------------------
# penalised Poisson (piecewise-exponential) with sector random effects
# ----------------------------------------------------------------------------------------------------------------
def pois_newton(X, y, off, R, b0=None, maxit=60, tol=1e-8):
    p = X.shape[1]; b = np.zeros(p) if b0 is None else b0.copy()
    if b0 is None:
        b[:] = 0
    def pll(bb):
        e = X @ bb + off; return float(np.sum(y * e - np.exp(e)) - 0.5 * np.sum(R * bb * bb))
    l0 = pll(b)
    for _ in range(maxit):
        e = X @ b + off; mu = np.exp(e)
        g = X.T @ (y - mu) - R * b
        H = (X * mu[:, None]).T @ X + np.diag(R)
        step = np.linalg.solve(H, g); s = 1.0
        while True:
            bn = b + s * step; ln = pll(bn)
            if ln >= l0 - 1e-9 or s < 1e-6: break
            s /= 2
        b, l0 = bn, ln
        if np.max(np.abs(s * step)) < tol: break
    e = X @ b + off; mu = np.exp(e)
    H = (X * mu[:, None]).T @ X + np.diag(R)
    return b, np.linalg.inv(H), float(np.sum(y * e - mu))


def design(P, cause, covs, use_cal=True):
    """columns: bucket dummies (CO: bucket 0 dropped, its hazard is 0), covariates, calendar dummies, sector dummies."""
    b = P['b']
    rows = np.ones(len(b), bool) if cause == 2 else (b >= 1)
    bb = b[rows]
    first = 0 if cause == 2 else 1
    A = np.zeros((rows.sum(), NB - first)); A[np.arange(rows.sum()), bb - first] = 1
    present = A.sum(0) > 0          # buckets with no exposure (e.g. 84+ months before mid-2024) are not estimable
    A = A[:, present]
    loan = P['loan'][rows]
    cols = [A]; names = ['base%d' % j for j in range(first, NB) if present[j - first]]
    for c in covs:
        v = P[c][rows] if c in P else LV[c][loan]
        cols.append(v[:, None]); names.append(c)
    if use_cal:
        cols.append(cal_mat(P['cy'][rows])); names += ['cal%d' % y for y in CAL_YEARS]
    S = np.zeros((rows.sum(), len(SECS))); S[np.arange(rows.sum()), sec_ix[loan]] = 1
    cols.append(S); names += ['sec_' + s for s in SECS]
    X = np.hstack(cols)
    return X, (P['y'][rows] == cause).astype(float), np.log(P['dt'][rows]), names, rows


def fit_cause(P, cause, covs, tau2=None, use_cal=True, verbose=False, tau2_init=0.05):
    """tau2=None: estimate the sector variance by Schall/EM iteration (started at tau2_init; the fixed point does not
    depend on the start). tau2 given: hold it fixed."""
    X, y, off, names, rows = design(P, cause, covs, use_cal)
    nS = len(SECS); p = X.shape[1]
    est_tau = tau2 is None
    t2 = tau2_init if est_tau else tau2
    b = None
    for it in range(80):
        R = np.zeros(p); R[-nS:] = 1.0 / t2
        b, cov, ll = pois_newton(X, y, off, R, b0=b)
        if not est_tau: break
        u = b[-nS:]; t2n = (np.sum(u * u) + np.trace(cov[-nS:, -nS:])) / nS
        t2n = max(t2n, 1e-4)
        if verbose: say('   tau2 iter', it, round(t2n, 5))
        if abs(t2n - t2) < 1e-4 * max(t2, 1e-3): t2 = t2n; break
        t2 = t2n
    R = np.zeros(p); R[-nS:] = 1.0 / t2
    b, cov, ll = pois_newton(X, y, off, R, b0=b)
    del X
    return {'b': b, 'cov': cov, 'names': names, 'tau2': t2, 'll': ll, 'covs': covs, 'cause': cause, 'use_cal': use_cal,
            'events': int(y.sum())}


def par(fit, name):
    return fit['b'][fit['names'].index(name)] if name in fit['names'] else 0.0


def log_base(fit, bvec=None):
    """per-bucket log baseline hazard (per month); an unestimable bucket carries the previous one forward (flat)."""
    lb = np.full(NB, -np.inf); bv = fit['b'] if bvec is None else bvec
    for j in range(NB):
        if 'base%d' % j in fit['names']: lb[j] = bv[fit['names'].index('base%d' % j)]
        elif j > 0 and np.isfinite(lb[j - 1]): lb[j] = lb[j - 1]
    return lb


def lin_pred(fit, rows, extra=None):
    """loan-level linear predictor (no baseline, no calendar): covariates + sector effect (+ optional extra log-RR)."""
    eta = np.zeros(len(rows))
    for c in fit['covs']:
        if c in LV: eta += par(fit, c) * LV[c][rows]
    sec = np.array([par(fit, 'sec_' + s) for s in SECS])
    eta += sec[sec_ix[rows]]
    if extra is not None: eta += extra
    return eta


def predict_cif(fco, fpif, rows, a0, a1, use_cal=True, extra_co=None, override=None, shrink=None):
    """P(charge-off in [a0,a1) | open at a0) for each loan in rows, piecewise-constant cause-specific hazards.
    override: dict of covariate -> value (scalar or per-loan array) applied to the CO and PIF linear predictors.
    shrink: (gamma, shift) applied to the loan-level CO log hazard (covariates, size x age, sector, extra):
    log h1 = base + calendar + shift + gamma * loan-level part. None = the fitted model."""
    lc = lin_pred(fco, rows, extra_co); lp = lin_pred(fpif, rows); la = LV['lnamt'][rows].copy()
    if override:
        for c, v in override.items():
            if c in LV:
                v = np.broadcast_to(np.asarray(v, float), (len(rows),))
                lc += par(fco, c) * (v - LV[c][rows]); lp += par(fpif, c) * (v - LV[c][rows])
    i, s, dt, b, cy, mid = pieces(a0, a1, st_day[rows])
    keep = dt > 1e-9; i, dt, b, cy = i[keep], dt[keep], b[keep], cy[keep]
    lbc, lbp = log_base(fco), log_base(fpif)
    cc = np.array([par(fco, 'cal%d' % y) for y in CAL_YEARS]); cp = np.array([par(fpif, 'cal%d' % y) for y in CAL_YEARS])
    calc = cal_mat(cy) @ cc if (use_cal and fco['use_cal']) else 0.0
    calp = cal_mat(cy) @ cp if (use_cal and fpif['use_cal']) else 0.0
    loanpart = lc[i] + par(fco, 'lnamt_x_age') * la[i] * age_term(b)
    if shrink is not None: loanpart = shrink[1] + shrink[0] * loanpart
    h1 = np.exp(lbc[b] + calc + loanpart); h2 = np.exp(lbp[b] + lp[i] + calp)
    if 'dprimeV' in fpif['covs'] and use_cal:   # realised prime path (validation only); 0 in the app (flat prime)
        mday = st_day[rows][i] + (s[keep] + dt / 2) * MPD
        h2 = h2 * np.exp(par(fpif, 'dprimeV') * (prime_month(mday.astype(np.int64)) - prime0[rows][i]) * (1 - fx[rows][i]))
    L = h1 + h2; Ld = L * dt
    cs = np.cumsum(Ld); first = np.r_[0, np.flatnonzero(np.diff(i)) + 1]
    base = (cs - Ld)[first]; grp = np.repeat(np.arange(len(first)), np.diff(np.r_[first, len(i)]))
    Sb = np.exp(-(cs - Ld - base[grp]))
    inc = np.where(L > 0, Sb * h1 / np.where(L > 0, L, 1) * (1 - np.exp(-Ld)), 0)
    out = np.zeros(len(rows)); out[np.unique(i)] = np.bincount(grp, weights=inc)
    return out


def cif_profile(lbc, lbp, lc, lp, H, la=0.0, bta=0.0, shrink=(1.0, 0.0), sev=None):
    """the exact JS recursion (reference calendar, flat prime): scalar loan-level linear predictors lc (CO, without the
    size x age part) and lp (payoff); la = centred ln loan, bta = size x age coefficient; shrink = (gamma, shift).
    With sev (a function of age in months) it also returns the expected-loss sum."""
    S, F, EL = 1.0, 0.0, 0.0
    for j in range(NB):
        a = EDGES[j]; b = EDGES[j + 1] if j + 1 < NB else np.inf
        if a >= H: break
        dt = min(b, H) - a
        lcj = shrink[1] + shrink[0] * (lc + bta * la * (min(a, AGE_CAP) / 12.0 - AGE_C))
        l1 = 0.0 if not np.isfinite(lbc[j]) else math.exp(lbc[j] + lcj); l2 = math.exp(lbp[j] + lp); L = l1 + l2
        if L > 0:
            inc = S * l1 / L * (1 - math.exp(-L * dt)); F += inc; S *= math.exp(-L * dt)
            if sev is not None: EL += inc * sev(a + dt / 2)
    return (F, EL) if sev is not None else F


def cif_matrix(lbc, lbp, LC, LP, H):
    """vectorised CIF over loans: LC (n x NB) loan-level CO log hazard per piece (shrink already applied), LP (n)."""
    S = np.ones(len(LP)); F = np.zeros(len(LP))
    for j in range(NB):
        a = EDGES[j]; b = EDGES[j + 1] if j + 1 < NB else np.inf
        if a >= H: break
        dt = min(b, H) - a
        l1 = np.exp(lbc[j] + LC[:, j]) if np.isfinite(lbc[j]) else np.zeros(len(LP))
        l2 = np.exp(lbp[j] + LP); L = l1 + l2
        F += S * l1 / L * (1 - np.exp(-L * dt)); S *= np.exp(-L * dt)
    return F


# ----------------------------------------------------------------------------------------------------------------
# metrics
# ----------------------------------------------------------------------------------------------------------------
def auc(y, p):
    y = np.asarray(y).astype(bool); r = stats.rankdata(p); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float('nan')


def auc_se(y, p, B=300):
    y = np.asarray(y); p = np.asarray(p); out = []
    for _ in range(B):
        ix = RNG.integers(0, len(y), len(y)); out.append(auc(y[ix], p[ix]))
    return float(np.nanstd(out))


def calib(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6); lg = np.log(p / (1 - p))
    try:
        m = sm.GLM(y, sm.add_constant(lg), family=sm.families.Binomial()).fit()
        slope = float(m.params[1]); slope_se = float(m.bse[1])
        m2 = sm.GLM(y, np.ones((len(y), 1)), family=sm.families.Binomial(), offset=lg).fit()
        citl = float(m2.params[0])
    except Exception:
        slope, slope_se, citl = float('nan'), float('nan'), float('nan')
    return {'n': int(len(y)), 'events': int(np.sum(y)), 'pred_sum': float(np.sum(p)), 'O_over_E': float(np.sum(y) / np.sum(p)),
            'auc': auc(y, p), 'auc_se_boot': auc_se(y, p), 'brier': float(np.mean((y - p) ** 2)),
            'brier_null_meanrate': float(np.mean((y - np.mean(y)) ** 2)),
            'logloss': float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            'calib_slope': slope, 'calib_slope_se': slope_se, 'calib_in_the_large': citl}


def deciles(y, p, label):
    q = pd.qcut(pd.Series(p).rank(method='first'), 10, labels=False)
    t = pd.DataFrame({'dec': q, 'y': y, 'p': p}).groupby('dec').agg(n=('y', 'size'), observed=('y', 'sum'), predicted=('p', 'sum'))
    t['split'] = label
    return t.reset_index()


# current model (resolved-only logistic) linear predictor, for comparison on the same splits
html = open(REPO + 'index.html', encoding='utf-8').read()
mi = html.index('const MODELS = ') + len('const MODELS = ')
CUR_MODELS, _ = json.JSONDecoder().raw_decode(html, mi)
CR = CUR_MODELS['risk']


def current_z(rows):
    co = CR['coefficients']; dd = d.iloc[rows]
    ie = dd.naics2.map(CR['industry_effects']).fillna(0).values
    se = dd.state.map(CR['state_effects']).fillna(0).values
    return (CR['intercept'] + co['ln_amt'] * np.log(np.maximum(dd.GrossApproval.values, 1e4)) + co['ind_eff'] * ie
            + co['franchise'] * dd.is_franchise.values + co['jobs'] * np.clip(dd.JobsSupported.values, 0, 100)
            + co['rate_c'] * (dd.InitialInterestRate.values - 7) + co.get('st_eff', 0) * se)


# ----------------------------------------------------------------------------------------------------------------
# 3a. specification checks (full sample, likelihood-ratio / AIC)
# ----------------------------------------------------------------------------------------------------------------
ALL = np.arange(len(d))
Pall = build_panel(ALL, d['T'].values, d.ev.values)
say('panel pieces', len(Pall['y']), 'exposure loan-months', round(Pall['dt'].sum()), 'events', np.bincount(Pall['y']).tolist())
say('CO events in bucket 0 (first 6 months):', int(((Pall['b'] == 0) & (Pall['y'] == 1)).sum()))
# staffing is not a model input: SBA JobsSupported (jobs created plus retained, lender-reported) is not what the console
# can supply (Census employees per revenue, several times larger for the same loan); it is fitted below as a check.
CO_COVS = ['lnamt', 'franchise', 'spread', 'fixed', 'spread_x_fixed', 'lnamt_x_age']
PIF_COVS = ['lnamt', 'franchise', 'spread', 'fixed', 'dprimeV']
# extra covariates for specification checks only
FY = d.ApprovalFY.values
LV['prime0'] = prime0 - float(prime0.mean())                 # prime at approval (rate level given the spread)
LV['level'] = d.InitialInterestRate.values - 7.0              # rate level (replacement comparison)
LV['coh1819'] = (FY <= 2019).astype(float); LV['coh2021'] = ((FY >= 2020) & (FY <= 2021)).astype(float)
LV['coh2426'] = (FY >= 2024).astype(float)
PRIME0_MEAN = float(prime0.mean())
_age_raw = EDGES[Pall['b']]
Pall['la_uncapped'] = LV['lnamt'][Pall['loan']] * (_age_raw / 12.0 - AGE_C)
Pall['la_cap60'] = LV['lnamt'][Pall['loan']] * (np.minimum(_age_raw, 60.0) / 12.0 - AGE_C)
Pall['la_post2024H2'] = LV['lnamt'][Pall['loan']] * (Pall['cy'] >= 2024.5)
Pall['spread_x_age'] = LV['spread'][Pall['loan']] * age_term(Pall['b'])
Pall['lnjobs_x_age'] = LV['lnjobs'][Pall['loan']] * age_term(Pall['b'])
spec = {}
t = time.time()
f_main = fit_cause(Pall, 1, CO_COVS, verbose=True)
say('CO main fit %.1fs tau2 %.4f ll %.2f' % (time.time() - t, f_main['tau2'], f_main['ll']))
TAU2_CO = f_main['tau2']
NO_AGE = [c for c in CO_COVS if c != 'lnamt_x_age']
for lab, covs, cal in [('no_calendar_terms', CO_COVS, False), ('+express_processing', CO_COVS + ['express'], True),
                       ('-spread_x_fixed', [c for c in CO_COVS if c != 'spread_x_fixed'], True),
                       ('+spread_above_3pp', CO_COVS + ['spread_above3'], True),
                       ('+dprimeV_payment_shock', CO_COVS + ['dprimeV'], True),
                       # staffing (SBA JobsSupported): log, linear, and log with an age interaction (checks; not shipped)
                       ('+ln(1+jobs) (SBA JobsSupported)', CO_COVS + ['lnjobs'], True), ('+jobs linear', CO_COVS + ['jobs_linear'], True),
                       ('+ln(1+jobs) and ln(1+jobs) x age', CO_COVS + ['lnjobs', 'lnjobs_x_age'], True),
                       # the size effect and loan age: proportional (no interaction), uncapped, capped at 60 months,
                       # and whether a calendar-period interaction is still needed once age is in
                       ('-lnamt_x_age (proportional size effect)', NO_AGE, True),
                       ('size x age uncapped instead of capped at 72m', NO_AGE + ['la_uncapped'], True),
                       ('size x age capped at 60m instead of 72m', NO_AGE + ['la_cap60'], True),
                       ('+size x exposure after 2024-07', CO_COVS + ['la_post2024H2'], True),
                       ('proportional + size x exposure after 2024-07', NO_AGE + ['la_post2024H2'], True),
                       ('+spread x age', CO_COVS + ['spread_x_age'], True),
                       # rate level: given the spread, with calendar terms; with calendar and approval-cohort terms; and
                       # the level in place of the spread
                       ('+prime at approval (rate level given spread)', CO_COVS + ['prime0'], True),
                       ('+prime at approval + approval cohorts', CO_COVS + ['prime0', 'coh1819', 'coh2021'], True),
                       ('+rate level (given spread)', CO_COVS + ['level'], True),
                       ('+rate level + approval cohorts', CO_COVS + ['level', 'coh1819', 'coh2021'], True),
                       ('rate level instead of spread', [c if c != 'spread' else 'level' for c in CO_COVS], True)]:
    f = fit_cause(Pall, 1, covs, tau2=TAU2_CO, use_cal=cal)
    extra = [c for c in covs if c not in CO_COVS]
    spec[lab] = {'ll': f['ll'], 'lr_vs_main': 2 * (f['ll'] - f_main['ll']), 'df': len(covs) - len(CO_COVS) + (0 if cal else -4),
                 'aic_vs_main': -2 * (f['ll'] - f_main['ll']) + 2 * (len(f['b']) - len(f_main['b'])),
                 'terms': {c: [r4(par(f, c)), r4(math.sqrt(f['cov'][f['names'].index(c), f['names'].index(c)]))] for c in extra},
                 'core': {c: r4(par(f, c)) for c in ['lnamt', 'lnamt_x_age', 'spread', 'lnjobs']}}
    say('  spec', lab, {k: (r4(v) if isinstance(v, float) else v) for k, v in spec[lab].items()})
f_pif = fit_cause(Pall, 2, PIF_COVS, verbose=False)
TAU2_PIF = f_pif['tau2']
say('PIF fit tau2 %.4f ll %.2f' % (TAU2_PIF, f_pif['ll']))
_fpj = fit_cause(Pall, 2, PIF_COVS + ['lnjobs'], tau2=TAU2_PIF)
JOBS_CHECK = {'co_lnjobs': spec['+ln(1+jobs) (SBA JobsSupported)']['terms']['lnjobs'], 'co_lr': r4(spec['+ln(1+jobs) (SBA JobsSupported)']['lr_vs_main']),
              'co_lr_log_vs_linear': r4(2 * (spec['+ln(1+jobs) (SBA JobsSupported)']['ll'] - spec['+jobs linear']['ll'])),
              'co_core_with_jobs': spec['+ln(1+jobs) (SBA JobsSupported)']['core'],
              'pif_lnjobs': [r4(par(_fpj, 'lnjobs')), r4(math.sqrt(_fpj['cov'][_fpj['names'].index('lnjobs'), _fpj['names'].index('lnjobs')]))],
              'sba_jobs_median_by_loan_band': None}
del _fpj
say('staffing check (not shipped):', JOBS_CHECK)
# lender heterogeneity: the 40 largest lenders as fixed effects (not shipped; the console prices an average lender)
LENDER = (d.BankName.fillna('NA').astype(str).str.upper().str.replace(r'[^A-Z0-9 ]', '', regex=True)
          .str.replace(r'\s+', ' ', regex=True).str.strip().values)
LEND_ID = pd.factorize(LENDER)[0]
TOPL = pd.Series(LENDER).value_counts().head(40).index
for i_, nm in enumerate(TOPL): LV['lender%02d' % i_] = (LENDER == nm).astype(float)
f_lfe = fit_cause(Pall, 1, CO_COVS + ['lender%02d' % i_ for i_ in range(40)], tau2=TAU2_CO)
LENDER_FE = {'lr': 2 * (f_lfe['ll'] - f_main['ll']), 'df': 40, 'share_of_loans': float(np.isin(LENDER, TOPL).mean()),
             'n_lenders': int(LEND_ID.max() + 1), 'core_with_fe': {c: r4(par(f_lfe, c)) for c in ['lnamt', 'lnamt_x_age', 'spread']}}
say('lender fixed effects (top 40):', LENDER_FE)
for i_ in range(40): del LV['lender%02d' % i_]
del f_lfe


def coef_table(f):
    rows = []
    for j, nme in enumerate(f['names']):
        rows.append({'term': nme, 'est': f['b'][j], 'se': math.sqrt(f['cov'][j, j])})
    return pd.DataFrame(rows)


def cluster_cov(f, P):
    """sandwich covariances with the penalised-likelihood bread: clustered by loan, by lender, by calendar quarter of
    exposure (SBA processes charge-offs in batches), and two-way lender x quarter (Cameron-Gelbach-Miller:
    V_lender + V_quarter - V_lender-quarter, made positive semi-definite). Small-sample factor G/(G-1)."""
    X, y, off, names, rows = design(P, f['cause'], f['covs'], f['use_cal'])
    mu = np.exp(X @ f['b'] + off); sc = X * (y - mu)[:, None]
    loan = P['loan'][rows]; L = LEND_ID[loan].astype(np.int64); q = np.floor(P['cy'][rows] * 4).astype(np.int64)
    out = {}
    for lab, cl in [('loan', loan), ('lender', L), ('quarter', q), ('lender_x_quarter', L * 100000 + q)]:
        codes = pd.factorize(cl)[0]; G = np.zeros((codes.max() + 1, X.shape[1])); np.add.at(G, codes, sc)
        nG = G.shape[0]; out[lab] = f['cov'] @ (G.T @ G * nG / (nG - 1)) @ f['cov']; out['n_' + lab] = int(nG)
    V2 = out['lender'] + out['quarter'] - out['lender_x_quarter']
    w, U = np.linalg.eigh((V2 + V2.T) / 2); out['twoway'] = (U * np.maximum(w, 0)) @ U.T
    del X, sc
    return out


def sim_cov(f, CV):
    """covariance for parameter simulation: for the non-sector parameters, the two-way correlation scaled to the shipped
    SE (the largest of Hessian, lender-clustered and two-way); the sector block keeps its model-based posterior covariance
    (a random effect's sandwich is not meaningful), with zero cross-covariance (the console's reference loan carries
    no sector effect)."""
    nS = len(SECS); p = len(f['b']); ns = p - nS
    se_ship = np.sqrt(np.maximum.reduce([np.diag(f['cov']), np.diag(CV['lender']), np.diag(CV['twoway'])]))
    tw = CV['twoway'][:ns, :ns]; sd = np.sqrt(np.maximum(np.diag(tw), 1e-300))
    C = tw / np.outer(sd, sd); C[~np.isfinite(C)] = 0; np.fill_diagonal(C, 1.0)
    V = np.zeros((p, p)); V[:ns, :ns] = C * np.outer(se_ship[:ns], se_ship[:ns]); V[ns:, ns:] = f['cov'][ns:, ns:]
    w, U = np.linalg.eigh((V + V.T) / 2)
    return (U * np.maximum(w, 1e-12)) @ U.T, se_ship


CV_CO = cluster_cov(f_main, Pall); CV_PIF = cluster_cov(f_pif, Pall)
SIMV_CO, SE_SHIP_CO = sim_cov(f_main, CV_CO); SIMV_PIF, SE_SHIP_PIF = sim_cov(f_pif, CV_PIF)
N_CLUST = {k: v for k, v in CV_CO.items() if k.startswith('n_')}
tco = coef_table(f_main); tpf = coef_table(f_pif)
for tab_, CV_, SH_ in [(tco, CV_CO, SE_SHIP_CO), (tpf, CV_PIF, SE_SHIP_PIF)]:
    for k in ['loan', 'lender', 'quarter', 'twoway']:
        tab_['se_cluster_' + k] = np.sqrt(np.diag(CV_[k]))
    tab_['se_shipped'] = SH_
    tab_.loc[tab_.term.str.startswith('sec_'), 'se_shipped'] = tab_.loc[tab_.term.str.startswith('sec_'), 'se']
tco.to_csv(OUT + 'hazard_chargeoff_coefficients.csv', index=False)
tpf.to_csv(OUT + 'hazard_pif_coefficients.csv', index=False)
say('clusters', N_CLUST)
say('CO coefficients\n' + tco[~tco.term.str.startswith('sec_')].round(4).to_string())
say('PIF coefficients (covariates/calendar)\n' + tpf[~tpf.term.str.startswith('sec_')].round(4).to_string())

# ----------------------------------------------------------------------------------------------------------------
# 3b. NAICS-6 within sector and state: Poisson-gamma empirical Bayes on observed/expected charge-offs
# ----------------------------------------------------------------------------------------------------------------
def expected_co(fco, P):
    X, y, off, names, rows = design(P, 1, fco['covs'], fco['use_cal'])
    mu = np.exp(X @ fco['b'] + off)
    return P['loan'][rows], mu, y


def pg_eb(O, E):
    """Poisson-gamma: RR ~ Gamma(a,a); returns a, posterior mean RR, posterior sd of log RR."""
    O = np.asarray(O, float); E = np.asarray(E, float)
    def nll(la):
        a = math.exp(la)
        return -np.sum(special.gammaln(O + a) - special.gammaln(a) + a * math.log(a) - (O + a) * np.log(E + a))
    r = optimize.minimize_scalar(nll, bounds=(math.log(0.05), math.log(1e5)), method='bounded')
    a = math.exp(r.x)
    rr = (O + a) / (E + a)
    sdlog = np.sqrt(special.polygamma(1, O + a))
    return a, rr, sdlog, r.x >= math.log(1e5) - 0.01


def eb_table(key, fco, P, rows_subset=None):
    loan, mu, y = expected_co(fco, P)
    df = pd.DataFrame({'k': d[key].values[loan], 'E': mu, 'O': y})
    g = df.groupby('k').agg(O=('O', 'sum'), E=('E', 'sum')).reset_index()
    a, rr, sdl, atcap = pg_eb(g.O.values, g.E.values)
    g['rr'] = rr; g['log_rr'] = np.log(rr); g['sd_log_rr'] = sdl
    nloan = d.groupby(key).size(); g['n_loans'] = g.k.map(nloan).values
    return g, a, atcap


n6_tab, A_N6, n6_cap = eb_table('n6', f_main, Pall)
st_tab, A_ST, st_cap = eb_table('state', f_main, Pall)
# between-lender spread of the charge-off hazard (not shipped: the console prices an average lender), same Poisson-gamma EB
d['lender'] = LENDER
ld_tab, A_LD, ld_cap = eb_table('lender', f_main, Pall)
LENDER_FE['eb_gamma_shape'] = r4(A_LD); LENDER_FE['eb_sd'] = r4(math.sqrt(special.polygamma(1, A_LD))); LENDER_FE['eb_at_cap'] = bool(ld_cap)
LENDER_FE['eb_rr_p5_p95_lenders_20plus_loans'] = [r4(v) for v in np.quantile(ld_tab.rr[ld_tab.n_loans >= 20], [.05, .95])]
say('lender EB: cells %d, gamma shape %.2f, implied sd of log RR %.3f; RR p5-p95 among lenders with >= 20 loans %s'
    % (len(ld_tab), A_LD, LENDER_FE['eb_sd'], LENDER_FE['eb_rr_p5_p95_lenders_20plus_loans']))
say('NAICS-6 EB: cells %d, gamma shape a=%.2f (at cap: %s), sd of log-RR across cells implied %.3f' % (len(n6_tab), A_N6, n6_cap, math.sqrt(special.polygamma(1, A_N6))))
say('state EB: cells %d, gamma shape a=%.2f (at cap: %s), implied sd %.3f' % (len(st_tab), A_ST, st_cap, math.sqrt(special.polygamma(1, A_ST))))
n6_tab.to_csv(OUT + 'eb_naics6_within_sector.csv', index=False)
st_tab.to_csv(OUT + 'eb_state.csv', index=False)
# the console's own 6-digit codes. ecom deliberately has none: 541512 is a BIZCOMPS label (see index.html) and in SBA
# data means computer-systems design, so e-commerce stays on its retail sector.
APP_N6 = {"home": "238220", "medical": "621111", "vet": "541940", "msp": "541511", "prof": "541211", "mfg": "339950",
          "dist": "423310", "staff": "561320", "land": "561730", "wash": "811192", "auto": "811111", "constr": "238990",
          "fit": "713940", "rest": "722511"}
say(n6_tab[n6_tab.k.isin(APP_N6.values())].round(4).to_string())

# final CO extra log-RR per loan (NAICS-6 within sector + state)
n6map = dict(zip(n6_tab.k, n6_tab.log_rr)); stmap = dict(zip(st_tab.k, st_tab.log_rr))
EXTRA_ALL = d.n6.map(n6map).fillna(0).values + d.state.map(stmap).fillna(0).values

# ----------------------------------------------------------------------------------------------------------------
# 3b2. does the size effect fade with loan age? in-sample observed/expected by loan band x age window
# ----------------------------------------------------------------------------------------------------------------
LBANDS = [('<250K', 0, 2.5e5), ('250-500K', 2.5e5, 5e5), ('500K-1M', 5e5, 1e6), ('1-2M', 1e6, 2e6), ('2-5M', 2e6, 5e6 + 1)]
f_ph = fit_cause(Pall, 1, NO_AGE, tau2=TAU2_CO)
_g6, _, _ = eb_table('n6', f_ph, Pall); _gs, _, _ = eb_table('state', f_ph, Pall)
EXTRA_PH = d.n6.map(dict(zip(_g6.k, _g6.log_rr))).fillna(0).values + d.state.map(dict(zip(_gs.k, _gs.log_rr))).fillna(0).values
BA_ROWS = []
for lab, f_, ex_ in [('proportional size effect', f_ph, EXTRA_PH), ('size effect fading to 72 months (shipped)', f_main, EXTRA_ALL)]:
    X_, y_, off_, nm_, rr_ = design(Pall, 1, f_['covs'], True)
    mu_ = np.exp(X_ @ f_['b'] + off_) * np.exp(ex_[Pall['loan'][rr_]]); del X_
    loan_ = Pall['loan'][rr_]; age_ = EDGES[Pall['b'][rr_]]; amt_ = d.GrossApproval.values[loan_]
    for nm, lo, hi in LBANDS:
        for aw, a0, a1 in [('6-36', 0, 36), ('36-60', 36, 60), ('60+', 60, 999)]:
            m = (amt_ >= lo) & (amt_ < hi) & (age_ >= a0) & (age_ < a1)
            BA_ROWS.append({'model': lab, 'band': nm, 'age_months': aw, 'observed': float(y_[m].sum()), 'expected': float(mu_[m].sum())})
band_age = pd.DataFrame(BA_ROWS); band_age['O_over_E'] = band_age.observed / band_age.expected
band_age['pearson_z'] = (band_age.observed - band_age.expected) / np.sqrt(band_age.expected)
band_age.to_csv(OUT + 'calibration_band_by_age.csv', index=False)
BAND_AGE_CHI2 = band_age.groupby('model').pearson_z.apply(lambda z: float((z ** 2).sum())).to_dict()
say('band x age O/E\n' + band_age.pivot_table(index='band', columns=['model', 'age_months'], values='O_over_E').round(2).to_string())
say('Pearson chi2 over the 15 band x age cells:', {k: round(v, 1) for k, v in BAND_AGE_CHI2.items()})
SIZE_BY_AGE = {a: r4(par(f_main, 'lnamt') + par(f_main, 'lnamt_x_age') * (min(a * 12, AGE_CAP) / 12 - AGE_C)) for a in [1, 2, 3, 4, 5, 6, 8]}
say('size log hazard ratio per log point of loan, by years on book:', SIZE_BY_AGE)
del f_ph

# ----------------------------------------------------------------------------------------------------------------
# 3c. Aalen-Johansen (non-parametric) checks
# ----------------------------------------------------------------------------------------------------------------
def aj(T, ev, grid):
    o = np.argsort(T, kind='stable'); t = T[o]; e = ev[o]; n = len(t)
    ut, first = np.unique(t, return_index=True); cnt = np.diff(np.r_[first, n])
    d1 = np.add.reduceat((e == 1).astype(float), first); d2 = np.add.reduceat((e == 2).astype(float), first)
    atrisk = n - first
    haz1 = d1 / atrisk; S = np.cumprod(1 - (d1 + d2) / atrisk); Sprev = np.r_[1, S[:-1]]
    F = np.cumsum(Sprev * haz1)
    res = {}
    for g in grid:
        j = np.searchsorted(ut, g, side='right') - 1
        res[g] = float(F[j]) if j >= 0 and ut.max() >= g else float('nan')
    return res


GRID = [12, 24, 36, 48, 60, 72, 84, 96]
aj_pool = aj(d['T'].values, d.ev.values, GRID)
aj_boot = np.array([[v for v in aj(d['T'].values[ix], d.ev.values[ix], GRID).values()] for ix in
                    (RNG.integers(0, len(d), len(d)) for _ in range(200))])
say('AJ pooled CIF', {k: r4(v) for k, v in aj_pool.items()}, 'SE60 %.4f SE96 %.4f' % (np.nanstd(aj_boot[:, 4]), np.nanstd(aj_boot[:, 7])))

# by loan-size band (app keys, by LOAN amount)
band_rows = {}
for nm, lo, hi in LBANDS:
    m = (d.GrossApproval >= lo) & (d.GrossApproval < hi); T_, e_ = d['T'].values[m], d.ev.values[m]
    v = aj(T_, e_, [60, 96]); bs = np.array([[x for x in aj(T_[ix], e_[ix], [60, 96]).values()] for ix in
                                            (RNG.integers(0, m.sum(), m.sum()) for _ in range(200))])
    band_rows[nm] = {'n': int(m.sum()), 'chgoff': int((e_ == 1).sum()), 'cif60': r4(v[60]), 'cif60_se': r4(np.nanstd(bs[:, 0])),
                     'cif96': r4(v[96]), 'cif96_se': r4(np.nanstd(bs[:, 1])),
                     'resolved_only_rate': r4((e_ == 1).sum() / max(((e_ == 1) | (e_ == 2)).sum(), 1)),
                     'loan_median': float(d.GrossApproval[m].median()), 'jobs_median': float(d.JobsSupported[m].median())}
say('AJ by loan band', band_rows)

# ----------------------------------------------------------------------------------------------------------------
# 3d. validation (the sector variance is re-estimated inside every split; the 6-digit and state empirical-Bayes maps
#     are refitted inside every split; functional forms were chosen on the full sample)
# ----------------------------------------------------------------------------------------------------------------
say('\n== 3d. validation')
VAL = {}; DEC = []; TAU_SPLITS = {}


def eb_maps(fco, P):
    g6, a6, _ = eb_table('n6', fco, P); gs, as_, _ = eb_table('state', fco, P)
    return dict(zip(g6.k, g6.log_rr)), dict(zip(gs.k, gs.log_rr))


def extra_vec(rows, m6, ms):
    return pd.Series(d.n6.values[rows]).map(m6).fillna(0).values + pd.Series(d.state.values[rows]).map(ms).fillna(0).values


def null_fit(P):
    return fit_cause(P, 1, [], tau2=1e-6), fit_cause(P, 2, [], tau2=1e-6)


def split_fits(Ptr, label):
    """both hazards on a training panel, sector variances re-estimated (warm start at the full-sample value)."""
    fc = fit_cause(Ptr, 1, CO_COVS, tau2=None, tau2_init=TAU2_CO); fp = fit_cause(Ptr, 2, PIF_COVS, tau2=None, tau2_init=TAU2_PIF)
    TAU_SPLITS[label] = {'co': r4(fc['tau2']), 'pif': r4(fp['tau2'])}
    return fc, fp


def oot_slope(fc, m6, ms, Pte, use_cal=True):
    """slope of the observed charge-off hazard on the training model's loan-level log hazard (covariates, size x age,
    sector, 6-digit and state), on held-out loan-pieces, with the age baseline left free (bucket dummies) and the
    training calendar terms as offset. 1 = effects transfer at full strength. Also by component."""
    m = (Pte['b'] >= 1); loan = Pte['loan'][m]; b = Pte['b'][m]
    comp = {'size': par(fc, 'lnamt') * LV['lnamt'][loan] + par(fc, 'lnamt_x_age') * Pte['lnamt_x_age'][m],
            'spread_franchise_fixed': sum(par(fc, c) * LV[c][loan] for c in ['spread', 'franchise', 'fixed', 'spread_x_fixed'])}
    sec = np.array([par(fc, 'sec_' + s_) for s_ in SECS]); comp['sector'] = sec[sec_ix[loan]]
    comp['naics6_state'] = extra_vec(loan, m6, ms)
    lp = sum(comp.values())
    cc = np.array([par(fc, 'cal%d' % y) for y in CAL_YEARS])
    off = np.log(Pte['dt'][m]) + (cal_mat(Pte['cy'][m]) @ cc if use_cal else 0)
    ub = np.unique(b); B = (b[:, None] == ub[None, :]).astype(float); y = (Pte['y'][m] == 1).astype(float)
    r = sm.GLM(y, np.column_stack([B, lp]), family=sm.families.Poisson(), offset=off).fit()
    r2 = sm.GLM(y, np.column_stack([B] + list(comp.values())), family=sm.families.Poisson(), offset=off).fit()
    k = len(ub)
    return {'gamma': float(r.params[-1]), 'se': float(r.bse[-1]), 'events': int(y.sum()), 'sd_lp': float(np.std(lp)),
            'by_component': {nm: [r4(r2.params[k + j]), r4(r2.bse[k + j])] for j, nm in enumerate(comp)}}


# (i) 5-fold CV by loan; outcome = charge-off within the loan's own administrative window (only administrative
#     censoring remains, so the outcome is fully observed); plus charge-off by 60 months for loans with >= 60 months.
fold = RNG.integers(0, 5, len(d))
pcv = np.zeros(len(d)); pcv_core = np.zeros(len(d)); pnull = np.zeros(len(d)); p60 = np.zeros(len(d)); p60n = np.zeros(len(d))
CV_SLOPES = []
for f in range(5):
    tr = np.flatnonzero(fold != f); te = np.flatnonzero(fold == f)
    Ptr = build_panel(tr, d['T'].values[tr], d.ev.values[tr])
    fc, fp = split_fits(Ptr, 'cv_fold%d' % f)
    m6, ms = eb_maps(fc, Ptr)
    ex = extra_vec(te, m6, ms)
    pcv[te] = predict_cif(fc, fp, te, np.zeros(len(te)), d.C.values[te], use_cal=True, extra_co=ex)
    pcv_core[te] = predict_cif(fc, fp, te, np.zeros(len(te)), d.C.values[te], use_cal=True)
    p60[te] = predict_cif(fc, fp, te, np.zeros(len(te)), np.full(len(te), 60.0), use_cal=True, extra_co=ex)
    CV_SLOPES.append(oot_slope(fc, m6, ms, build_panel(te, d['T'].values[te], d.ev.values[te])))
    nc, npf = null_fit(Ptr)
    pnull[te] = predict_cif(nc, npf, te, np.zeros(len(te)), d.C.values[te], use_cal=True)
    p60n[te] = predict_cif(nc, npf, te, np.zeros(len(te)), np.full(len(te), 60.0), use_cal=True)
    say('  fold', f, 'tau2', TAU_SPLITS['cv_fold%d' % f], 'slope %.3f (%.3f)' % (CV_SLOPES[-1]['gamma'], CV_SLOPES[-1]['se']), 'done %.0fs' % (time.time() - T0))
del Ptr
yadm = (d.ev.values == 1).astype(float)
zc = current_z(ALL)
VAL['cv5_admin_window'] = {'new_full': calib(yadm, pcv), 'new_core_no_state_naics6': calib(yadm, pcv_core),
                           'null_age_calendar_only': calib(yadm, pnull), 'current_model_auc': auc(yadm, zc),
                           'current_model_auc_se': auc_se(yadm, zc)}
m60 = d.C.values >= 60
y60 = ((d.ev.values == 1) & (d['T'].values <= 60)).astype(float)
VAL['cv5_chargeoff_by_60m'] = {'population': 'loans with >= 60 months of administrative follow-up (approved FY2018-FY2021)',
                               'new_full': calib(y60[m60], p60[m60]), 'null_age_calendar_only': calib(y60[m60], p60n[m60]),
                               'current_model_auc': auc(y60[m60], zc[m60])}
_w = np.array([1 / s_['se'] ** 2 for s_ in CV_SLOPES])
VAL['cv5_slope_loan_level'] = {'by_fold': [[r4(s_['gamma']), r4(s_['se'])] for s_ in CV_SLOPES],
                               'pooled': float(np.sum(_w * np.array([s_['gamma'] for s_ in CV_SLOPES])) / _w.sum()), 'pooled_se': float(1 / math.sqrt(_w.sum()))}
DEC.append(deciles(yadm, pcv, 'cv5_admin_window')); DEC.append(deciles(y60[m60], p60[m60], 'cv5_by_60m'))
say('CV admin window: new AUC %.4f Brier %.5f | core %.4f | null %.4f | current-model AUC %.4f'
    % (VAL['cv5_admin_window']['new_full']['auc'], VAL['cv5_admin_window']['new_full']['brier'],
       VAL['cv5_admin_window']['new_core_no_state_naics6']['auc'], VAL['cv5_admin_window']['null_age_calendar_only']['auc'],
       VAL['cv5_admin_window']['current_model_auc']))
say('CV by 60m: new AUC %.4f Brier %.5f O/E %.3f slope %.3f | null AUC %.4f Brier %.5f | current AUC %.4f' % (
    VAL['cv5_chargeoff_by_60m']['new_full']['auc'], VAL['cv5_chargeoff_by_60m']['new_full']['brier'],
    VAL['cv5_chargeoff_by_60m']['new_full']['O_over_E'], VAL['cv5_chargeoff_by_60m']['new_full']['calib_slope'],
    VAL['cv5_chargeoff_by_60m']['null_age_calendar_only']['auc'], VAL['cv5_chargeoff_by_60m']['null_age_calendar_only']['brier'],
    VAL['cv5_chargeoff_by_60m']['current_model_auc']))
say('CV in-period slope on the loan-level log hazard: %.3f (%.3f)' % (VAL['cv5_slope_loan_level']['pooled'], VAL['cv5_slope_loan_level']['pooled_se']))

# (ii) vintage holdout: train FY2018-21 loans (their whole histories), test FY2022-24 loans
tr = np.flatnonzero(d.ApprovalFY.values <= 2021); te = np.flatnonzero(d.ApprovalFY.between(2022, 2024).values)
Ptr = build_panel(tr, d['T'].values[tr], d.ev.values[tr])
fc, fp = split_fits(Ptr, 'vintage_holdout'); m6, ms = eb_maps(fc, Ptr)
pv = predict_cif(fc, fp, te, np.zeros(len(te)), d.C.values[te], use_cal=True, extra_co=extra_vec(te, m6, ms))
nc, npf = null_fit(Ptr); pvn = predict_cif(nc, npf, te, np.zeros(len(te)), d.C.values[te], use_cal=True)
SLOPE_V = oot_slope(fc, m6, ms, build_panel(te, d['T'].values[te], d.ev.values[te]), use_cal=True)
VAL['vintage_holdout_train_FY18_21_test_FY22_24'] = {'new_full': calib(yadm[te], pv), 'null_age_calendar_only': calib(yadm[te], pvn),
                                                     'current_model_auc': auc(yadm[te], zc[te]),
                                                     'current_model_auc_se': auc_se(yadm[te], zc[te]), 'loan_level_slope': SLOPE_V}
DEC.append(deciles(yadm[te], pv, 'vintage_holdout'))
say('vintage holdout', {k: (round(v['auc'], 4), round(v['O_over_E'], 3), round(v['calib_slope'], 3)) if isinstance(v, dict) and 'auc' in v else v
                        for k, v in VAL['vintage_holdout_train_FY18_21_test_FY22_24'].items()})

# (iii) calendar holdout: train on exposure before 2024-07-01; forecast charge-offs 2024-07-01..2026-06-30 for loans open then
cut_day = np.datetime64('2024-07-01', 'D').astype(np.int64)
c_age = (cut_day - st_day) / MPD
trm = c_age > 0
tr = np.flatnonzero(trm)
Ttr = np.minimum(d['T'].values[tr], c_age[tr]); etr = np.where(d['T'].values[tr] <= c_age[tr], d.ev.values[tr], 0)
Ptr = build_panel(tr, np.maximum(Ttr, 0.01), etr)
fc, fp = split_fits(Ptr, 'calendar_holdout'); m6, ms = eb_maps(fc, Ptr)
te = np.flatnonzero(trm & (d['T'].values > c_age))
yte = (d.ev.values[te] == 1).astype(float)
pc_ = predict_cif(fc, fp, te, c_age[te], d.C.values[te], use_cal=False, extra_co=extra_vec(te, m6, ms))
nc, npf = null_fit(Ptr); pcn = predict_cif(nc, npf, te, c_age[te], d.C.values[te], use_cal=False)
SLOPE_C = oot_slope(fc, m6, ms, panel(te, c_age[te], d['T'].values[te], d.ev.values[te]), use_cal=False)
VAL['calendar_holdout_train_pre_2024H2_forecast_2024H2_2026H1'] = {
    'new_full': calib(yte, pc_), 'null_age_only': calib(yte, pcn), 'current_model_auc': auc(yte, zc[te]),
    'current_model_auc_se': auc_se(yte, zc[te]), 'loan_level_slope': SLOPE_C,
    'note': 'forecast under reference (2023+) calendar conditions; actual prime path ignored'}
DEC.append(deciles(yte, pc_, 'calendar_holdout'))
say('calendar holdout', {k: (round(v['auc'], 4), round(v['O_over_E'], 3), round(v['calib_slope'], 3)) if isinstance(v, dict) and 'auc' in v else v
                         for k, v in VAL['calendar_holdout_train_pre_2024H2_forecast_2024H2_2026H1'].items()})
del Ptr
pd.concat(DEC).to_csv(OUT + 'calibration_deciles.csv', index=False)

# out-of-time shrinkage of the loan-level log hazard: inverse-variance pooling of the two out-of-time slopes. The two
# holdouts share test exposure (FY2022-24 loans after 2024-07), so the pooled SE is not allowed below the more precise
# single holdout's. Capped at 1 (effects are never amplified).
_wv, _wc = 1 / SLOPE_V['se'] ** 2, 1 / SLOPE_C['se'] ** 2
GAMMA_RAW = (SLOPE_V['gamma'] * _wv + SLOPE_C['gamma'] * _wc) / (_wv + _wc)
GAMMA = float(min(1.0, GAMMA_RAW))
GAMMA_SE = float(max(1 / math.sqrt(_wv + _wc), min(SLOPE_V['se'], SLOPE_C['se'])))
VAL['oot_shrink'] = {'vintage': [r4(SLOPE_V['gamma']), r4(SLOPE_V['se'])], 'calendar': [r4(SLOPE_C['gamma']), r4(SLOPE_C['se'])],
                     'pooled_raw': r4(GAMMA_RAW), 'applied': r4(GAMMA), 'se': r4(GAMMA_SE)}
say('out-of-time slope on the loan-level log hazard: vintage %.3f (%.3f), calendar %.3f (%.3f) -> applied %.3f (SE %.3f); in-period CV %.3f'
    % (SLOPE_V['gamma'], SLOPE_V['se'], SLOPE_C['gamma'], SLOPE_C['se'], GAMMA, GAMMA_SE, VAL['cv5_slope_loan_level']['pooled']))
say('   by component: vintage', SLOPE_V['by_component'], '| calendar', SLOPE_C['by_component'])
say('sector variance by split', TAU_SPLITS)

# (iv) in-sample calibration by vintage: model (with realised calendar) vs observed share charged off by t
vrows = []
pt = {}
for tt in [24, 36, 48, 60, 84]:
    m = d.C.values >= tt; rows = np.flatnonzero(m)
    pt[tt] = predict_cif(f_main, f_pif, rows, np.zeros(len(rows)), np.full(len(rows), float(tt)), use_cal=True, extra_co=EXTRA_ALL[rows])
    obs = ((d.ev.values[rows] == 1) & (d['T'].values[rows] <= tt)).astype(float)
    for fy, g in pd.DataFrame({'fy': d.ApprovalFY.values[rows], 'o': obs, 'p': pt[tt]}).groupby('fy'):
        vrows.append({'months': tt, 'vintage': int(fy), 'n': len(g), 'observed': g.o.mean(), 'predicted': g.p.mean(),
                      'binom_se': math.sqrt(max(g.p.mean() * (1 - g.p.mean()), 1e-12) / len(g))})
vint_cal = pd.DataFrame(vrows); vint_cal.to_csv(OUT + 'calibration_by_vintage.csv', index=False)
say('calibration by vintage\n' + vint_cal.round(4).to_string())
# observed vs expected charge-offs by approval cohort over each loan's own window (realised calendar)
_loan, _mu, _y = expected_co(f_main, Pall); _mu = _mu * np.exp(EXTRA_ALL[_loan])
COHORT_OE = {}
for lo, hi in [(2018, 2019), (2020, 2021), (2022, 2023), (2024, 2026)]:
    mm = (FY[_loan] >= lo) & (FY[_loan] <= hi)
    O_, E_ = float(_y[mm].sum()), float(_mu[mm].sum())
    COHORT_OE['FY%d-%d' % (lo, hi % 100)] = {'O': int(O_), 'E': r4(E_), 'O_over_E': r4(O_ / E_), 'poisson_p_le': r4(stats.poisson.cdf(O_, E_))}
say('cohort O/E (in-sample, realised calendar):', COHORT_OE)
del _loan, _mu, _y

# ----------------------------------------------------------------------------------------------------------------
# 3e. shrunk console model: population level, reference loan, parameter uncertainty, specification range
# ----------------------------------------------------------------------------------------------------------------
say('\n== 3e. console model (loan-level effects x %.3f; level shift solved so the console-priced FY2024-26 book averages its fitted 5-year level)' % GAMMA)
lbc, lbp = log_base(f_main), log_base(f_pif)
H5, HT = 60.0, 120.0
recent = np.flatnonzero(d.ApprovalFY.values >= 2024)
ZERO_COVS = ('fixed', 'spread_x_fixed', 'coh1819', 'coh2021', 'coh2426')   # the console: variable note, reference cohort
ZERO_COH = ('coh1819', 'coh2021', 'coh2426')                                 # the fitted book: each note at its own rate type
# what the console sees for a loan: the note clamped to [$25k, $5M] and the FY2025-26 table spread for its size (sbaRate)
LNAMT_CON = np.log(np.clip(d.GrossApproval.values, 25000.0, 5e6)) - CENT['ln_loan']
TABSPREAD_C = np.clip(lerp_knots(np.log(np.maximum(d.GrossApproval.values, 1e4)), SPK, np.round(spread_res['V']['values'], 2)), *SPREAD_CLIP) - CENT['spread']


def console_set(rows):
    return {'spread': TABSPREAD_C[rows], 'lnamt': LNAMT_CON[rows]}


def loan_lps(fco, fpif, bc, bp, rows, zero=ZERO_COVS, set_=None, extra=None):
    """raw loan-level CO log hazard per piece (n x NB: covariates, size x age, sector, EB extras) and payoff log hazard (n)
    under parameter vectors bc, bp, current conditions (calendar at reference), flat prime. Covariates in `zero` are held
    at 0 (default: variable note, reference cohort). set_: covariate -> per-loan values that replace LV (e.g. the table
    spread and the clamped note: console_set)."""
    set_ = set_ or {}
    lc = (EXTRA_ALL[rows] if extra is None else extra).astype(float).copy(); lp = np.zeros(len(rows))
    for f_, bv_, acc in [(fco, bc, 'c'), (fpif, bp, 'p')]:
        for c in f_['covs']:
            if c not in LV or c in zero: continue
            v = set_[c] if c in set_ else LV[c][rows]
            if acc == 'c': lc += bv_[f_['names'].index(c)] * v
            else: lp += bv_[f_['names'].index(c)] * v
    secc = np.array([bc[fco['names'].index('sec_' + s_)] for s_ in SECS]); secp = np.array([bp[fpif['names'].index('sec_' + s_)] for s_ in SECS])
    lc += secc[sec_ix[rows]]; lp += secp[sec_ix[rows]]
    bta = bc[fco['names'].index('lnamt_x_age')] if 'lnamt_x_age' in fco['names'] else 0.0
    la = set_['lnamt'] if 'lnamt' in set_ else LV['lnamt'][rows]
    LC = lc[:, None] + bta * la[:, None] * age_term(np.arange(NB))[None, :]
    return LC, lp


def solve_shift(lbc_, lbp_, LC, LP, g, target):
    """level shift that puts the mean 5-year charge-off of these loans at `target` once loan-level effects are x g."""
    return float(optimize.brentq(lambda sh: cif_matrix(lbc_, lbp_, sh + g * LC, LP, H5).mean() - target, -5, 5, xtol=1e-12))


def pop_level2(fco, fpif, dco=0.0, dpif=0.0, extra=None, extra_set=None, zt=ZERO_COH, rows=None, g=None):
    """population level of the FY2024-26 book under a specification. Target = the book's mean fitted (unshrunk) 5-year
    charge-off, each loan at its own spread and rate type, reference conditions (+dco/dpif on the log baselines). The
    level shift is solved so that the console's pricing of the same loans (table spread, variable note, clamped loan,
    loan-level effects x g) has that mean; h96 is the console-priced 8-year mean."""
    rows = recent if rows is None else rows; g = GAMMA if g is None else g
    lbc_ = log_base(fco) + dco; lbp_ = log_base(fpif) + dpif
    ex = None if extra is None else extra[rows]; es = extra_set or {}
    LCt, LPt = loan_lps(fco, fpif, fco['b'], fpif['b'], rows, zero=zt, set_=dict(es), extra=ex)
    t60 = float(cif_matrix(lbc_, lbp_, LCt, LPt, H5).mean())
    LCc, LPc = loan_lps(fco, fpif, fco['b'], fpif['b'], rows, zero=tuple(zt) + ('fixed', 'spread_x_fixed'), set_={**console_set(rows), **es}, extra=ex)
    sh = solve_shift(lbc_, lbp_, LCc, LPc, g, t60)
    return {'h60': t60, 'h96': float(cif_matrix(lbc_, lbp_, sh + g * LCc, LPc, 96.0).mean()), 'shift': sh,
            'h96_book_unshrunk': float(cif_matrix(lbc_, lbp_, LCt, LPt, 96.0).mean())}


MAIN_LEVEL = pop_level2(f_main, f_pif)
BASE60_RAW, BASE96_RAW = MAIN_LEVEL['h60'], MAIN_LEVEL['h96_book_unshrunk']     # the fitted book, unshrunk
_chk = predict_cif(f_main, f_pif, recent, np.zeros(len(recent)), np.full(len(recent), H5), use_cal=False, extra_co=EXTRA_ALL[recent]).mean()
assert abs(_chk - BASE60_RAW) < 1e-9, (_chk, BASE60_RAW)
LP_SHIFT = MAIN_LEVEL['shift']
SHR = (GAMMA, LP_SHIFT)
LC_r, LP_r = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], recent, set_=console_set(recent))    # the book as the console prices it
BASE60 = float(cif_matrix(lbc, lbp, LP_SHIFT + GAMMA * LC_r, LP_r, H5).mean())
BASE96 = float(cif_matrix(lbc, lbp, LP_SHIFT + GAMMA * LC_r, LP_r, 96.0).mean())
BASE120 = float(cif_matrix(lbc, lbp, LP_SHIFT + GAMMA * LC_r, LP_r, HT).mean())
assert abs(BASE60 - BASE60_RAW) < 1e-9
say('population (FY2024-26 book, n %d): fitted 5-year level %.4f (unshrunk, own spreads and rate type; 8-year %.4f); console-priced (table spread, '
    'variable, shrunk, shift %.4f): 60m %.4f 96m %.4f 120m-flat %.4f' % (len(recent), BASE60_RAW, BASE96_RAW, LP_SHIFT, BASE60, BASE96, BASE120))
# what the previous fit shipped: shift solved on the book with fixed-rate notes' terms zeroed (their low spreads run through the
# variable slope), base = that book's mean; the console's own pricing of the same book then averaged above base (review finding)
_LCo, _LPo = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], recent)
_o60 = float(cif_matrix(lbc, lbp, _LCo, _LPo, H5).mean()); _sho = solve_shift(lbc, lbp, _LCo, _LPo, GAMMA, _o60)
_vr = recent[fx[recent] == 0]
_LCv, _LPv = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], _vr, zero=ZERO_COH)
BASE_DIAG = {'previous_definition': {'shift': r4(_sho), 'h60': r4(_o60), 'h96': r4(float(cif_matrix(lbc, lbp, _sho + GAMMA * _LCo, _LPo, 96.0).mean())),
                                     'console_priced_h60': r4(float(cif_matrix(lbc, lbp, _sho + GAMMA * LC_r, LP_r, H5).mean())),
                                     'console_priced_h96': r4(float(cif_matrix(lbc, lbp, _sho + GAMMA * LC_r, LP_r, 96.0).mean()))},
             'variable_notes_own_spread_unshrunk_h60': r4(float(cif_matrix(lbc, lbp, _LCv, _LPv, H5).mean())), 'n_variable': int(len(_vr)),
             'fixed_share': r4(float(fx[recent].mean())), 'fixed_mean_spread': r4(float(d.spread_over_prime.values[recent][fx[recent] == 1].mean())),
             'table_spread_mean': r4(float((TABSPREAD_C[recent] + CENT['spread']).mean())),
             'hazard_multiple_vs_previous_shift': r4(math.exp(LP_SHIFT - _sho))}
BASE_DIAG['previous_definition']['console_over_base'] = [r4(BASE_DIAG['previous_definition']['console_priced_h60'] / _o60),
                                                         r4(BASE_DIAG['previous_definition']['console_priced_h96'] / BASE_DIAG['previous_definition']['h96'])]
say('base diagnostics (previous definition vs now):', BASE_DIAG)
del _LCo, _LPo, _LCv, _LPv
_q = np.quantile(LC_r[:, 8], [.01, .5, .99])
say('spread of the loan-level log hazard at 4 years, FY2024-26 book as the console prices it: p1 %.2f, median %.2f, p99 %.2f; shrunk: %.2f %.2f %.2f'
    % (*_q, *(LP_SHIFT + GAMMA * _q)))


def prof_lp(f, bvec, x, sec):
    eta = 0.0
    for c in f['covs']:
        if c in x: eta += bvec[f['names'].index(c)] * x[c]
    if ('sec_' + sec) in f['names']: eta += bvec[f['names'].index('sec_' + sec)]
    return eta


def xprof(loan, spread, franchise=0):
    return {'lnamt': math.log(min(max(loan, 25000.0), 5e6)) - CENT['ln_loan'], 'franchise': franchise,
            'spread': min(max(spread, SPREAD_CLIP[0]), SPREAD_CLIP[1]) - CENT['spread'], 'fixed': 0.0, 'spread_x_fixed': 0.0}


def prof_point(x, sec, H, fco=None, fpif=None, shr=None):
    fco = fco or f_main; fpif = fpif or f_pif; shr = shr or SHR
    return cif_profile(log_base(fco), log_base(fpif), prof_lp(fco, fco['b'], x, sec), prof_lp(fpif, fpif['b'], x, sec), H,
                       la=x['lnamt'], bta=par(fco, 'lnamt_x_age'), shrink=shr)


# parameter uncertainty: draws from the clustered (shipped-SE) covariance of both hazards and from the shrink factor;
# each draw recomputes the fitted 5-year level of a fixed subsample of the FY2024-26 book and re-solves the level shift
# for the console's pricing of it (deviation from the subsample's own point shift added to the full-book shift)
NS = 2000
Dco = RNG.multivariate_normal(f_main['b'], SIMV_CO, size=NS, method='cholesky')
Dpf = RNG.multivariate_normal(f_pif['b'], SIMV_PIF, size=NS, method='cholesky')
Dg = np.minimum(RNG.normal(GAMMA, GAMMA_SE, NS), 1.0)
SUB = np.sort(RNG.choice(recent, 2000, replace=False))
_LCt, _LPt = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], SUB, zero=ZERO_COH)
_LCs, _LPs = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], SUB, set_=console_set(SUB))
_sh_sub0 = solve_shift(lbc, lbp, _LCs, _LPs, GAMMA, float(cif_matrix(lbc, lbp, _LCt, _LPt, H5).mean()))
ref_x = xprof(650000, float(lerp_knots(np.log([650000]), SPK, np.round(spread_res['V']['values'], 2))[0]))
REF_DRAWS = {60: [], 96: [], 120: []}; POP_DRAWS = {60: [], 96: []}
for s_ in range(NS):
    bc, bp, g_ = Dco[s_], Dpf[s_], Dg[s_]
    lbc_d, lbp_d = log_base(f_main, bc), log_base(f_pif, bp)
    LCt, LPt = loan_lps(f_main, f_pif, bc, bp, SUB, zero=ZERO_COH)
    LCs, LPs = loan_lps(f_main, f_pif, bc, bp, SUB, set_=console_set(SUB))
    tgt = float(cif_matrix(lbc_d, lbp_d, LCt, LPt, H5).mean())
    sh_ = LP_SHIFT + solve_shift(lbc_d, lbp_d, LCs, LPs, g_, tgt) - _sh_sub0
    POP_DRAWS[60].append(tgt); POP_DRAWS[96].append(float(cif_matrix(lbc_d, lbp_d, sh_ + g_ * LCs, LPs, 96.0).mean()))
    for H_ in (60, 96, 120):
        REF_DRAWS[H_].append(cif_profile(lbc_d, lbp_d, prof_lp(f_main, bc, ref_x, '__none__'), prof_lp(f_pif, bp, ref_x, '__none__'),
                                         float(H_), la=ref_x['lnamt'], bta=bc[f_main['names'].index('lnamt_x_age')], shrink=(g_, sh_)))
REF60 = (prof_point(ref_x, '__none__', H5), float(np.std(REF_DRAWS[60])))
REF96 = (prof_point(ref_x, '__none__', 96.0), float(np.std(REF_DRAWS[96])))
REF120 = (prof_point(ref_x, '__none__', HT), float(np.std(REF_DRAWS[120])))
POP_SE = {60: float(np.std(POP_DRAWS[60])), 96: float(np.std(POP_DRAWS[96]))}
say('reference loan ($650k, table spread, average sector, no state): CIF60 %.4f (SE %.4f)  CIF96 %.4f (SE %.4f) CIF120-flat %.4f (SE %.4f); population SE 60m %.4f 96m %.4f'
    % (REF60[0], REF60[1], REF96[0], REF96[1], REF120[0], REF120[1], POP_SE[60], POP_SE[96]))
# the same with the Hessian covariance (what the earlier fit reported), for comparison
_Dh = RNG.multivariate_normal(f_main['b'], f_main['cov'], size=500, method='cholesky'); _Dhp = RNG.multivariate_normal(f_pif['b'], f_pif['cov'], size=500, method='cholesky')
REF96_HESS_SE = float(np.std([cif_profile(log_base(f_main, _Dh[k]), log_base(f_pif, _Dhp[k]), prof_lp(f_main, _Dh[k], ref_x, '__none__'),
                                          prof_lp(f_pif, _Dhp[k], ref_x, '__none__'), 96.0, la=ref_x['lnamt'],
                                          bta=_Dh[k][f_main['names'].index('lnamt_x_age')], shrink=SHR) for k in range(500)]))
say('   reference CIF96 SE with the Hessian covariance (shrink fixed): %.4f' % REF96_HESS_SE)

# model at table spreads vs the observed 5-year rate, by loan band (current conditions, own sector and state)
_tabspread = TABSPREAD_C
for nm, lo, hi in LBANDS:
    rows = np.flatnonzero((d.GrossApproval.values >= lo) & (d.GrossApproval.values < hi))
    LCb, LPb = loan_lps(f_main, f_pif, f_main['b'], f_pif['b'], rows, set_=console_set(rows))
    band_rows[nm]['model60_table_spread'] = r4(float(cif_matrix(lbc, lbp, LP_SHIFT + GAMMA * LCb, LPb, H5).mean()))
    band_rows[nm]['model96_table_spread'] = r4(float(cif_matrix(lbc, lbp, LP_SHIFT + GAMMA * LCb, LPb, 96.0).mean()))
    # the fitted model on the band's own loans: own spread and rate type, realised calendar and prime path (apples to apples)
    band_rows[nm]['model60_insample'] = r4(float(predict_cif(f_main, f_pif, rows, np.zeros(len(rows)), np.full(len(rows), H5), use_cal=True, extra_co=EXTRA_ALL[rows]).mean()))
    band_rows[nm]['model96_insample'] = r4(float(predict_cif(f_main, f_pif, rows, np.zeros(len(rows)), np.full(len(rows), 96.0), use_cal=True, extra_co=EXTRA_ALL[rows]).mean()))
    vr = rows[fx[rows] == 0]
    band_rows[nm]['spread_mean_variable_observed'] = r4(float((LV['spread'][vr] + CENT['spread']).mean()))
    band_rows[nm]['spread_mean_all_observed'] = r4(float((LV['spread'][rows] + CENT['spread']).mean()))
    band_rows[nm]['spread_mean_table'] = r4(float((_tabspread[rows] + CENT['spread']).mean()))
    band_rows[nm]['fixed_share'] = r4(float(fx[rows].mean()))
say('observed vs fitted in-sample vs console (table spread, current conditions, shrunk), by band [cif60, insample60, console60 | cif96, insample96, console96]:',
    {k: (v['cif60'], v['model60_insample'], v['model60_table_spread'], v['cif96'], v['model96_insample'], v['model96_table_spread']) for k, v in band_rows.items()})
say('   mean spread by band [variable observed, all observed, table]:',
    {k: (v['spread_mean_variable_observed'], v['spread_mean_all_observed'], v['spread_mean_table']) for k, v in band_rows.items()})
BAND_CONSOLE_RATIO = {k: r4(v['model60_table_spread'] / v['cif60']) for k, v in band_rows.items()}
BAND_CONSOLE_Z = {k: r4((v['model60_table_spread'] - v['cif60']) / v['cif60_se']) for k, v in band_rows.items()}
say('   console / observed 5-year rate by band:', BAND_CONSOLE_RATIO, 'z:', BAND_CONSOLE_Z)

# real-estate notes by loan band: TermInMonths > 120 among loans that were not charged off (SBA overwrites the term of
# charged-off loans with months to charge-off, so it can be read only for paid-off and open loans)
_nc = d.ev.values != 1
RE_SHARE = {}
for nm, lo, hi in LBANDS:
    m = _nc & (d.GrossApproval.values >= lo) & (d.GrossApproval.values < hi)
    RE_SHARE[nm] = {'n': int(m.sum()), 'share_term_over_120m': r4(float((d.TermInMonths.values[m] > 120).mean()))}
_co_std = float(np.mean(np.isin(d.TermInMonths.values[d.ev.values == 1], [84, 120, 180, 240, 300])))
_nc_std = float(np.mean(np.isin(d.TermInMonths.values[_nc], [84, 120, 180, 240, 300])))
RE_NOTE = {'by_band': RE_SHARE, 'standard_term_share_chargeoffs': r4(_co_std), 'standard_term_share_others': r4(_nc_std)}
say('real-estate-term (>120 months) share by band, paid-off and open loans:', {k: v['share_term_over_120m'] for k, v in RE_SHARE.items()},
    '| standard-term share, charged-off %.3f vs others %.3f' % (_co_std, _nc_std))
JOBS_CHECK['sba_jobs_median_by_loan_band'] = {k: v['jobs_median'] for k, v in band_rows.items()}

# specification range of the population level (each re-solves its own shift as above, same shrink): calendar-year vs
# approval-cohort terms, both, neither; the payoff hazard without its prime-change term; payoffs censored at 2026-03-31
# (2026Q2 payoffs look under-recorded); everything censored at 2025-12-31 (the last fully reported quarter)
SPEC_BASE = {}


def trunc_panel(cut):
    """panel with administrative censoring moved to `cut` (events after it count as censored)."""
    cday = np.datetime64(cut, 'D').astype(np.int64); cm = (cday - st_day) / MPD
    rows = np.flatnonzero(cm > 0); T_ = np.minimum(d['T'].values[rows], cm[rows])
    e_ = np.where(d['T'].values[rows] <= cm[rows], d.ev.values[rows], 0)
    P_ = build_panel(rows, np.maximum(T_, 0.01), e_)
    P_['cal2025p'] = (P_['cy'] >= 2025.0).astype(float)
    return P_, int(np.sum(e_ == 1)), int(np.sum(e_ == 2))


P_q1, _nco_q1, _npf_q1 = trunc_panel('2026-03-31')
P_q4, _nco_q4, _npf_q4 = trunc_panel('2025-12-31')
fp_q1 = fit_cause(P_q1, 2, PIF_COVS, tau2=TAU2_PIF)
fc_q4 = fit_cause(P_q4, 1, CO_COVS, tau2=TAU2_CO); fp_q4 = fit_cause(P_q4, 2, PIF_COVS, tau2=TAU2_PIF)
COH = ['coh1819', 'coh2021']
for lab, cc_, ccal, pc_l, pcal in [('main: calendar-year terms, payoff prime-change held at 0', CO_COVS, True, PIF_COVS, True),
                                   ('approval-cohort terms instead of calendar', CO_COVS + COH, False, PIF_COVS + COH, False),
                                   ('calendar and approval-cohort terms', CO_COVS + COH, True, PIF_COVS + COH, True),
                                   ('payoff hazard without the prime-change term', CO_COVS, True, [c for c in PIF_COVS if c != 'dprimeV'], True),
                                   ('neither calendar nor cohort terms', CO_COVS, False, PIF_COVS, False),
                                   ('payoffs censored at 2026-03-31', None, None, None, None),
                                   ('everything censored at 2025-12-31', None, None, None, None)]:
    if lab == 'payoffs censored at 2026-03-31': fc_, fp_ = f_main, fp_q1
    elif lab == 'everything censored at 2025-12-31': fc_, fp_ = fc_q4, fp_q4
    else:
        fc_ = f_main if (cc_ == CO_COVS and ccal) else fit_cause(Pall, 1, cc_, tau2=TAU2_CO, use_cal=ccal)
        fp_ = f_pif if (pc_l == PIF_COVS and pcal) else fit_cause(Pall, 2, pc_l, tau2=TAU2_PIF, use_cal=pcal)
    lv_ = pop_level2(fc_, fp_)
    SPEC_BASE[lab] = {'h60': r4(lv_['h60']), 'h96': r4(lv_['h96']), 'shift': r4(lv_['shift']), 'lnamt': r4(par(fc_, 'lnamt')), 'spread': r4(par(fc_, 'spread'))}
    say('  base spec %-58s 60m %.4f 96m %.4f (shift %.4f)' % (lab, lv_['h60'], lv_['h96'], lv_['shift']))
fc_ = fit_cause(Pall, 1, CO_COVS + COH + ['coh2426'], tau2=TAU2_CO, use_cal=False)
fp_ = fit_cause(Pall, 2, PIF_COVS + COH + ['coh2426'], tau2=TAU2_PIF, use_cal=False)
NEWEST_REF = {'coef': [r4(par(fc_, 'coh2426')), r4(math.sqrt(fc_['cov'][fc_['names'].index('coh2426'), fc_['names'].index('coh2426')]))]}
# loan_lps skips zeroed covariates; coh2426 must be switched on explicitly for this variant
_lv = pop_level2(fc_, fp_, extra_set={'coh2426': np.ones(len(recent))}, zt=('coh1819', 'coh2021'))
NEWEST_REF.update({'h60': r4(_lv['h60']), 'h96': r4(_lv['h96'])})
del fc_, fp_
SPEC_RANGE = {'h60': [min(v['h60'] for v in SPEC_BASE.values()), max(v['h60'] for v in SPEC_BASE.values())],
              'h96': [min(v['h96'] for v in SPEC_BASE.values()), max(v['h96'] for v in SPEC_BASE.values())]}
say('specification range', SPEC_RANGE, '| FY2024-26 approvals as reference (not used):', NEWEST_REF)

# reference period: is "2023-26 conditions" one level? A 2025-26 calendar dummy (piece midpoint in calendar 2025 or
# later) against 2023-24 on the charge-off hazard, and quarter effects 2023Q1-2026Q2 (2023Q1 = 0); the payoff hazard
# gets the same dummy on the panel censored at 2026-03-31 (2026Q2 payoffs under-recorded). Population levels under
# 2023-24 and 2025-26 conditions bracket the reference period.
Pall['cal2025p'] = (Pall['cy'] >= 2025.0).astype(float)
f_c25 = fit_cause(Pall, 1, CO_COVS + ['cal2025p'], tau2=TAU2_CO)
fp_c25 = fit_cause(P_q1, 2, PIF_COVS + ['cal2025p'], tau2=TAU2_PIF)
_j = f_c25['names'].index('cal2025p'); _jp = fp_c25['names'].index('cal2025p')
_cvq = cluster_cov(f_c25, Pall)
D25 = {'co': [r4(f_c25['b'][_j]), r4(math.sqrt(f_c25['cov'][_j, _j])), r4(math.sqrt(_cvq['quarter'][_j, _j])), r4(math.sqrt(_cvq['lender'][_j, _j]))],
       'pif': [r4(fp_c25['b'][_jp]), r4(math.sqrt(fp_c25['cov'][_jp, _jp]))], 'lr_co': r4(2 * (f_c25['ll'] - f_main['ll']))}
del _cvq
_qi = np.floor(Pall['cy'] * 4 + 1e-9).astype(int)
QTRS = [y * 4 + q for y in range(2023, 2027) for q in range(4) if y * 4 + q <= 2026 * 4 + 1]
for k in QTRS[1:]: Pall['q%d' % k] = (_qi == k).astype(float)
f_qt = fit_cause(Pall, 1, CO_COVS + ['q%d' % k for k in QTRS[1:]], tau2=TAU2_CO)
QEFF = {'%dQ%d' % (k // 4, k % 4 + 1): (0.0 if k == QTRS[0] else r4(par(f_qt, 'q%d' % k))) for k in QTRS}
_qa = np.array([QEFF['%dQ%d' % (k // 4, k % 4 + 1)] for k in QTRS if k < 2025 * 4]); _qb = np.array([QEFF['%dQ%d' % (k // 4, k % 4 + 1)] for k in QTRS if k >= 2025 * 4])
_wt = stats.ttest_ind(_qb, _qa, equal_var=False)
_coq = pd.Series(pd.to_datetime(d.ChargeOffDate[(d.ev == 1)]).dt.to_period('Q').astype(str)).value_counts().sort_index()
QDIAG = {'quarter_effects_vs_2023Q1': QEFF, 'welch_t_2025_26_vs_2023_24': r4(_wt.statistic), 'welch_p': r4(_wt.pvalue),
         'n_quarters': [int(len(_qb)), int(len(_qa))], 'max_2025Q2_2026Q2': r4(max(QEFF[k] for k in ['2025Q2', '2025Q3', '2025Q4', '2026Q1', '2026Q2'])),
         'min_2023_24': r4(float(_qa.min())), 'chargeoffs_by_quarter': {k: int(v) for k, v in _coq.items() if '2023Q1' <= k <= '2026Q2'}}
QDIAG['largest_batch'] = max(QDIAG['chargeoffs_by_quarter'].items(), key=lambda kv: kv[1])
for k in QTRS[1:]: del Pall['q%d' % k]
del f_qt
COND = {}
for lab, fp_, dco, dpf in [('2023-24 charge-off and payoff conditions', fp_c25, 0.0, 0.0),
                           ('2025-26 charge-off and payoff conditions (payoffs to 2026-03-31)', fp_c25, f_c25['b'][_j], fp_c25['b'][_jp]),
                           ('2023-24 charge-off conditions, pooled 2023-26 payoffs', f_pif, 0.0, 0.0),
                           ('2025-26 charge-off conditions, pooled 2023-26 payoffs', f_pif, f_c25['b'][_j], 0.0)]:
    lv_ = pop_level2(f_c25, fp_, dco=dco, dpif=dpf)
    COND[lab] = {'h60': r4(lv_['h60']), 'h96': r4(lv_['h96']), 'ratio_h96_to_main': r4(lv_['h96'] / BASE96)}
    say('  conditions %-66s 60m %.4f 96m %.4f (x%.3f)' % (lab, lv_['h60'], lv_['h96'], lv_['h96'] / BASE96))
# the range takes each period whole (its charge-off AND payoff conditions); the mixed rows are reported beside it
_cw = [v for k, v in COND.items() if 'charge-off and payoff' in k]
COND_RANGE = {'h60': [min(v['h60'] for v in _cw), max(v['h60'] for v in _cw)], 'h96': [min(v['h96'] for v in _cw), max(v['h96'] for v in _cw)],
              'ratio_h96': [min(v['ratio_h96_to_main'] for v in _cw), max(v['ratio_h96_to_main'] for v in _cw)],
              'mixed_h96': [min(v['h96'] for v in COND.values()), max(v['h96'] for v in COND.values())]}
LEVEL_RANGE = {k: [min(SPEC_RANGE[k][0], COND_RANGE[k][0]), max(SPEC_RANGE[k][1], COND_RANGE[k][1])] for k in ('h60', 'h96')}
say('reference period: 2025-26 vs 2023-24 charge-off log hazard %s (Hessian, quarter-clustered, lender-clustered SE), payoff %s, LR %.1f; '
    'quarter effects %s; Welch t %.2f p %.3f' % (D25['co'], D25['pif'], D25['lr_co'], QEFF, QDIAG['welch_t_2025_26_vs_2023_24'], QDIAG['welch_p']))
say('conditions range', COND_RANGE, '| level range (specifications and reference periods)', LEVEL_RANGE)
del f_c25, fp_c25, fc_q4, fp_q4, fp_q1, P_q1, P_q4

# a model without the spread: with no rate entered the console reads the spread off the median table, so the spread
# coefficient acts as a second size effect (lender pricing). The marginal risk given size: both hazards refitted without
# the spread (sector variance re-estimated, 6-digit and state maps refitted), same shrink, own level shift.
f_ns = fit_cause(Pall, 1, [c for c in CO_COVS if c not in ('spread', 'spread_x_fixed')], tau2=None, tau2_init=TAU2_CO)
fp_ns = fit_cause(Pall, 2, [c for c in PIF_COVS if c != 'spread'], tau2=None, tau2_init=TAU2_PIF)
_m6n, _msn = eb_maps(f_ns, Pall); EX_NS = extra_vec(ALL, _m6n, _msn)
LV_NS = pop_level2(f_ns, fp_ns, extra=EX_NS)
SHR_NS = (GAMMA, LV_NS['shift'])
NOSPREAD = {'lnamt': [r4(par(f_ns, 'lnamt')), r4(math.sqrt(f_ns['cov'][f_ns['names'].index('lnamt'), f_ns['names'].index('lnamt')]))],
            'lnamt_x_age': r4(par(f_ns, 'lnamt_x_age')), 'll': r4(f_ns['ll']), 'll_main': r4(f_main['ll']), 'tau2': r4(f_ns['tau2']),
            'h60': r4(LV_NS['h60']), 'h96': r4(LV_NS['h96']), 'shift': r4(LV_NS['shift']), 'cif96_ratio_shipped_over_nospread': {}, 'band_console60': {}}
for L_ in [1e5, 2.5e5, 5e5, 1e6, 2e6, 4e6]:
    x_s = xprof(L_, float(lerp_knots(np.log([L_]), SPK, np.round(spread_res['V']['values'], 2))[0])); x_n = xprof(L_, 2.25)
    NOSPREAD['cif96_ratio_shipped_over_nospread']['%g' % L_] = r4(prof_point(x_s, '__none__', 96.0) / prof_point(x_n, '__none__', 96.0, fco=f_ns, fpif=fp_ns, shr=SHR_NS))
for nm, lo, hi in LBANDS:
    rows = np.flatnonzero((d.GrossApproval.values >= lo) & (d.GrossApproval.values < hi))
    LCb, LPb = loan_lps(f_ns, fp_ns, f_ns['b'], fp_ns['b'], rows, set_=console_set(rows), extra=EX_NS[rows])
    NOSPREAD['band_console60'][nm] = r4(float(cif_matrix(log_base(f_ns), log_base(fp_ns), SHR_NS[1] + GAMMA * LCb, LPb, H5).mean()))
_rr = list(NOSPREAD['cif96_ratio_shipped_over_nospread'].values())
NOSPREAD['diff_range'] = [r4(min(_rr) - 1), r4(max(_rr) - 1)]
say('no-spread model (marginal risk given size):', NOSPREAD)
del f_ns, fp_ns

# rate level given the spread (not applied): the hazard multiple it would imply for a loan written at today's prime
_rl_cal = spec['+prime at approval (rate level given spread)']['terms']['prime0']
_rl_coh = spec['+prime at approval + approval cohorts']['terms']['prime0']
RATE_LEVEL = {'coef_calendar': _rl_cal, 'coef_calendar_cohort': _rl_coh,
              'level_coef_calendar': spec['+rate level (given spread)']['terms']['level'],
              'level_coef_calendar_cohort': spec['+rate level + approval cohorts']['terms']['level'],
              'aic_level_instead_of_spread': r4(spec['rate level instead of spread']['aic_vs_main']),
              'prime_sample_mean': r4(PRIME0_MEAN), 'prime_now': PRIME_NOW,
              'uplift_range': [r4(math.exp(min(_rl_cal[0], _rl_coh[0]) * (PRIME_NOW - PRIME0_MEAN)) - 1),
                               r4(math.exp(max(_rl_cal[0], _rl_coh[0]) * (PRIME_NOW - PRIME0_MEAN)) - 1)]}
say('rate level given spread (not applied):', RATE_LEVEL)

# ----------------------------------------------------------------------------------------------------------------
# 3f. years 9-10 from mature all-7(a) vintages (size-matched); through-the-cycle vintages; like-for-like comparison
# ----------------------------------------------------------------------------------------------------------------
say('\n== 3f. tail shape from mature 7(a) vintages, through-the-cycle vintages, like-for-like comparison')
cols = ['ApprovalFY', 'ApprovalDate', 'FirstDisbursementDate', 'LoanStatus', 'PaidInFullDate', 'ChargeOffDate',
        'GrossApproval', 'BusinessAge', 'RevolverStatus', 'GrossChargeOffAmount']
r0 = pd.read_csv(SBA + 'raw/FOIA_7a_FY2000_FY2009_asof_260630.csv', usecols=cols, encoding='latin-1', low_memory=False)
r1 = pd.read_csv(SBA + 'raw/FOIA_7a_FY2010_FY2019_asof_260630.csv', usecols=cols, encoding='latin-1', low_memory=False)
r2 = pd.read_csv(SBA + 'raw/FOIA_7a_FY2020_Present_asof_260630.csv', usecols=cols, encoding='latin-1', low_memory=False)
A7 = pd.concat([r0, r1, r2], ignore_index=True); del r0, r1, r2
A7['LoanStatus'] = A7.LoanStatus.astype(str).str.replace(' ', '')
A7['rev'] = A7.RevolverStatus.astype(str).str.upper().map({'Y': 1, 'N': 0, '1': 1, '0': 0})
A7 = A7[A7.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (A7.rev == 0)].copy()
for c in ['ApprovalDate', 'FirstDisbursementDate', 'PaidInFullDate', 'ChargeOffDate']:
    A7[c] = pd.to_datetime(A7[c], errors='coerce')
A7['start'] = A7.FirstDisbursementDate.fillna(A7.ApprovalDate)
endd = A7.PaidInFullDate.where(A7.LoanStatus == 'PIF', A7.ChargeOffDate.where(A7.LoanStatus == 'CHGOFF', ASOF))
A7['T'] = (endd - A7.start).dt.days / MPD
A7 = A7[A7['T'] >= 0]
A7['ev'] = A7.LoanStatus.map({'EXEMPT': 0, 'CHGOFF': 1, 'PIF': 2})
mat = A7[A7.ApprovalFY.between(2010, 2015) & (A7.GrossApproval >= 1.5e5)]
TG = [60, 84, 96, 120]
tail = {'population': 'all 7(a) term loans >= $150k approved FY2010-2015 (>= 10.75 years of follow-up), any business age',
        'n': int(len(mat)), 'chgoff': int((mat.ev == 1).sum())}
tv = aj(mat['T'].values, mat.ev.values, TG); tail.update({'cif%d' % g: r4(tv[g]) for g in TG})
bt = []
for _ in range(200):
    ix = RNG.integers(0, len(mat), len(mat)); v = aj(mat['T'].values[ix], mat.ev.values[ix], TG); bt.append([v[60], v[84], v[96], v[120]])
bt = np.array(bt)
tail['ratio_120_over_96'] = r4(tv[120] / tv[96]); tail['ratio_120_over_96_se'] = r4(np.std(bt[:, 3] / bt[:, 2]))
tail['ratio_120_over_84'] = r4(tv[120] / tv[84]); tail['ratio_120_over_84_se'] = r4(np.std(bt[:, 3] / bt[:, 1]))
tail['ratio_96_over_60'] = r4(tv[96] / tv[60]); tail['ratio_96_over_60_se'] = r4(np.std(bt[:, 2] / bt[:, 0]))
byv = {}
for fy in range(2010, 2016):
    m = mat[mat.ApprovalFY == fy]; v = aj(m['T'].values, m.ev.values, TG)
    byv[fy] = {'n': int(len(m)), **{'cif%d' % g: r4(v[g]) for g in TG}, 'r120_96': r4(v[120] / v[96])}
tail['by_vintage'] = byv
# the ratio rises with loan size; part of that is term mix (larger mature loans more often carry 25-year real-estate
# terms, and TermInMonths cannot be used to separate it because SBA overwrites it for charged-off loans)
mat_all = A7[A7.ApprovalFY.between(2010, 2015)]
TBANDS = [('<150k', 0, 1.5e5), ('150-350k', 1.5e5, 3.5e5), ('350-750k', 3.5e5, 7.5e5), ('0.75-1.5M', 7.5e5, 1.5e6), ('>=1.5M', 1.5e6, 1e12)]
tail_band = {}
for nm, lo, hi in TBANDS:
    g = mat_all[(mat_all.GrossApproval >= lo) & (mat_all.GrossApproval < hi)]; v = aj(g['T'].values, g.ev.values, [96, 120])
    w = float(((d.GrossApproval >= lo) & (d.GrossApproval < hi)).mean())
    tail_band[nm] = {'n': int(len(g)), 'cif96': r4(v[96]), 'cif120': r4(v[120]), 'ratio': r4(v[120] / v[96]), 'acq_share': r4(w)}
TAIL_SIZE_MATCHED = sum(v['acq_share'] * v['cif120'] for v in tail_band.values()) / sum(v['acq_share'] * v['cif96'] for v in tail_band.values())
_big = {k: v for k, v in tail_band.items() if k != '<150k'}
TAIL_SIZE_MATCHED_150 = sum(v['acq_share'] * v['cif120'] for v in _big.values()) / sum(v['acq_share'] * v['cif96'] for v in _big.values())
tail['by_loan_band'] = tail_band
tail['size_matched_all'] = r4(TAIL_SIZE_MATCHED); tail['size_matched_150k_up'] = r4(TAIL_SIZE_MATCHED_150)
model_ratio_120_96 = BASE120 / BASE96
tail['chow_model_ratio_120_over_96_flat_tail'] = r4(model_ratio_120_96)
tail['chow_aj_ratio_96_over_60'] = r4(aj_pool[96] / aj_pool[60])
# post-term charge-offs (loans that defaulted in years 8-10 are charged off after month 120): CIF144/CIF120, FY2010-13
_m13 = mat[mat.ApprovalFY.between(2010, 2013)]; _v13 = aj(_m13['T'].values, _m13.ev.values, [120, 144])
tail['ratio_144_over_120_FY2010_13'] = r4(_v13[144] / _v13[120])
# shipped: the size-matched ratio. Its SE is a judgment: it has to cover the loan-band range (x1.07 small to x1.33 large,
# partly term mix), the CHOW model's own flat-hazard ratio, the vintage spread (FY2011-12 vintages are lowest; their
# years 9-10 fell in FY2020-22, when CARES s.1112 paid borrowers' P&I) and the bootstrap. The composite of the
# measurable parts is reported beside it; the shipped SE is not allowed below 0.08 (about 1.05-1.35 at 2 SE).
TAIL = float(TAIL_SIZE_MATCHED)
TAIL_SD_VINT = float(np.std([v['r120_96'] for v in byv.values()], ddof=1))
TAIL_COMPOSITE = float(math.sqrt(float(np.std(bt[:, 3] / bt[:, 2])) ** 2 + TAIL_SD_VINT ** 2 + (TAIL - tv[120] / tv[96]) ** 2
                                 + (model_ratio_120_96 - TAIL) ** 2))
TAIL_SE = float(max(0.08, TAIL_COMPOSITE))
tail['tail_factor_used'] = r4(TAIL); tail['tail_factor_se'] = r4(TAIL_SE); tail['tail_factor_se_measurable_parts'] = r4(TAIL_COMPOSITE)
say('tail', json.dumps(tail))

# through the cycle: 10-year charge-off of all 7(a) term loans >= $150k by approval year (not acquisitions only; the
# console's figure assumes 2023-26 conditions persist)
cyc = {}
for fy, g in A7[(A7.GrossApproval >= 1.5e5) & A7.ApprovalFY.between(2000, 2016)].groupby('ApprovalFY'):
    v = aj(g['T'].values, g.ev.values, [60, 96, 120, 144])
    cyc[int(fy)] = {'n': int(len(g)), 'cif60': r4(v[60]), 'cif96': r4(v[96]), 'cif120': r4(v[120]),
                    'r120_96': r4(v[120] / v[96]), 'r144_120': r4(v[144] / v[120]) if np.isfinite(v[144]) else None}
CYCLE = {'by_vintage': cyc, 'population': 'all SBA 7(a) term loans >= $150k, any business age, Aalen-Johansen, PIF competing'}
_c = pd.DataFrame(cyc).T
CYCLE['cif120_FY2006_08'] = [r4(_c.loc[[2006, 2007, 2008], 'cif120'].min()), r4(_c.loc[[2006, 2007, 2008], 'cif120'].max())]
CYCLE['cif120_FY2010_16'] = [r4(_c.loc[2010:2016, 'cif120'].min()), r4(_c.loc[2010:2016, 'cif120'].max())]
CYCLE['r120_96_range'] = [r4(_c.r120_96.min()), r4(_c.r120_96.max())]
say('through the cycle (all 7(a) >= $150k)\n' + _c.to_string())

# like-for-like: FY2018-26 term loans by business age, Aalen-Johansen CIF at 60 months
def bage(s):
    s = str(s)
    if 'Change of Ownership' in s: return 'acquisition'
    if s.startswith('Startup') or s.startswith('New'): return 'startup_or_new'
    if s.startswith('Existing') or s.startswith('Less than'): return 'existing'
    return 'other'


rec7 = A7[A7.ApprovalFY.between(2018, 2026)].copy(); rec7['grp'] = rec7.BusinessAge.map(bage)
lfl = {}
for gname, g in rec7.groupby('grp'):
    v = aj(g['T'].values, g.ev.values, [60]); res = g.ev.isin([1, 2])
    lfl[gname] = {'n': int(len(g)), 'cif60': r4(v[60]), 'resolved_only_rate': r4((g.ev == 1).sum() / max(res.sum(), 1)),
                  'median_loan': float(g.GrossApproval.median())}
mlarge = rec7.GrossApproval >= 1.5e5
for gname, g in rec7[mlarge].groupby('grp'):
    lfl[gname]['cif60_loans_150k_up'] = r4(aj(g['T'].values, g.ev.values, [60])[60])
    lfl[gname]['n_loans_150k_up'] = int(len(g))
# all 7(a) term loans >= $150k approved FY2018-21 at 60 months, to scale the through-the-cycle figures
CYCLE['acq_to_all_150k_ratio_cif60'] = r4(lfl['acquisition']['cif60_loans_150k_up'] / float(aj(rec7[mlarge]['T'].values, rec7[mlarge].ev.values, [60])[60]))
say('like-for-like FY2018-26 7(a) term loans', json.dumps(lfl))
say('acquisition / all-loan 5-year ratio (>= $150k, FY2018-26):', CYCLE['acq_to_all_150k_ratio_cif60'])
del A7, rec7

BASE_TERM = BASE96 * TAIL
REF_TERM = (REF96[0] * TAIL, math.sqrt((REF96[1] * TAIL) ** 2 + (REF96[0] * TAIL_SE) ** 2))
POP_TERM_SE = math.sqrt((POP_SE[96] * TAIL) ** 2 + (BASE96 * TAIL_SE) ** 2)
say('term (120m) = CIF96 x %.4f (SE %.4f): population %.4f (SE %.4f; flat-hazard alternative %.4f), reference loan %.4f (SE %.4f)'
    % (TAIL, TAIL_SE, BASE_TERM, POP_TERM_SE, BASE120, REF_TERM[0], REF_TERM[1]))

# ----------------------------------------------------------------------------------------------------------------
# 4. LGD by size
# ----------------------------------------------------------------------------------------------------------------
say('\n== 4. LGD')
co = d[d.ev == 1].copy()
co['lr'] = co.chargeoff_loss_ratio.clip(0, 1)
co['x'] = np.log(co.GrossApproval) - CENT['ln_loan']
co['mob'] = co.months_on_book
co['age_c'] = co.months_on_book / 12.0 - 4.0          # years on book at charge-off, centred at 4
co['co_day'] = co.ChargeOffDate
LGD_AGE_RANGE = [12.0, 96.0]                           # charge-off ages observed: %.1f to %.1f months
lgd_bands = []
for nm, lo, hi in LBANDS:
    g = co[(co.GrossApproval >= lo) & (co.GrossApproval < hi)].lr
    bs = [RNG.choice(g.values, len(g)).mean() for _ in range(1000)]
    lgd_bands.append({'band': nm, 'n': len(g), 'mean': g.mean(), 'se_mean': np.std(bs), 'median': g.median(),
                      'p25': g.quantile(.25), 'p75': g.quantile(.75)})
lgd_bands = pd.DataFrame(lgd_bands); lgd_bands.to_csv(OUT + 'lgd_by_band.csv', index=False)
say(lgd_bands.round(4).to_string())


def frac_logit(df, cols):
    X = sm.add_constant(df[cols].values) if cols else np.ones((len(df), 1))
    return sm.GLM(df.lr.values, X, family=sm.families.Binomial()).fit(cov_type='HC0')


fl = frac_logit(co, ['x'])
fl2 = frac_logit(co, ['x', 'mob'])
fla = frac_logit(co, ['x', 'age_c'])                  # the shipped severity model
say('fractional logit lr ~ ln(loan): b0 %.4f (%.4f) b1 %.4f (%.4f); +months on book at charge-off: b_mob %.4f (%.4f)'
    % (fl.params[0], fl.bse[0], fl.params[1], fl.bse[1], fl2.params[2], fl2.bse[2]))
say('severity model lr ~ ln(loan) + years on book: b0 %.4f (%.4f) b_size %.4f (%.4f) b_age %.4f (%.4f)'
    % (fla.params[0], fla.bse[0], fla.params[1], fla.bse[1], fla.params[2], fla.bse[2]))
LGD_AGE_FIT = {'b0': float(fla.params[0]), 'b_size': float(fla.params[1]), 'b_age': float(fla.params[2]),
               'se': [float(v) for v in fla.bse], 'cov': fla.cov_params().tolist()}
LGD_KNOTS_USD = [1.5e5, 4e5, 1e6, 2.5e6, 5e6]
say('charge-off ages %.1f-%.1f months' % (co.mob.min(), co.mob.max()))
LK = np.log(LGD_KNOTS_USD) - CENT['ln_loan']
lgd_fit = special.expit(fl.params[0] + fl.params[1] * LK)
bsk = []
for _ in range(1000):
    s = co.sample(len(co), replace=True, random_state=int(RNG.integers(1e9)))
    f_ = frac_logit(s, ['x']); bsk.append(special.expit(f_.params[0] + f_.params[1] * LK))
lgd_se = np.std(bsk, axis=0)
say('LGD mean curve at', LGD_KNOTS_USD, np.round(lgd_fit, 4), 'SE', np.round(lgd_se, 4))
# validation: 10-fold CV and temporal holdout (charge-offs before / after 2024-07-01)
CURK = np.array(CR['lgd']['by_size_curve']['ln_price_knots']); CURW = np.array(CR['lgd']['by_size_curve']['lgd'])
fo = RNG.integers(0, 10, len(co)); pf = np.zeros(len(co)); pm = np.zeros(len(co)); pa = np.zeros(len(co))
for f in range(10):
    trn = co[fo != f]; tst = fo == f
    m_ = frac_logit(trn, ['x']); pf[tst] = special.expit(m_.params[0] + m_.params[1] * co.x.values[tst]); pm[tst] = trn.lr.mean()
    m_ = frac_logit(trn, ['x', 'age_c']); pa[tst] = special.expit(m_.params[0] + m_.params[1] * co.x.values[tst] + m_.params[2] * co.age_c.values[tst])
pcur = np.interp(np.clip(np.log(co.GrossApproval.values / 0.85), CURK[0], CURK[-1]), CURK, CURW)
mse = lambda a, b: float(np.mean((a - b) ** 2))
early = co.co_day < '2024-07-01'
m_e = frac_logit(co[early], ['x'])
p_late = special.expit(m_e.params[0] + m_e.params[1] * co.x.values[~early])
m_ea = frac_logit(co[early], ['x', 'age_c'])
p_late_a = special.expit(m_ea.params[0] + m_ea.params[1] * co.x.values[~early] + m_ea.params[2] * co.age_c.values[~early])
LGDV = {'n': int(len(co)), 'cv10_mse_size_age': mse(co.lr, pa), 'cv10_mse_frac_logit': mse(co.lr, pf), 'cv10_mse_pooled_mean': mse(co.lr, pm),
        'temporal_mse_size_age': mse(co.lr[~early], p_late_a), 'temporal_mean_error_size_age': float(np.mean(co.lr[~early] - p_late_a)),
        'b_size_age_model': float(fla.params[1]), 'b_size_age_model_se': float(fla.bse[1]),
        'b_age': float(fla.params[2]), 'b_age_se': float(fla.bse[2]),
        'mse_current_median_curve': mse(co.lr, pcur), 'mean_error_current_median_curve': float(np.mean(co.lr - pcur)),
        'temporal_train_n': int(early.sum()), 'temporal_test_n': int((~early).sum()),
        'temporal_mse_frac_logit': mse(co.lr[~early], p_late), 'temporal_mse_train_mean': mse(co.lr[~early], co.lr[early].mean()),
        'temporal_mean_error': float(np.mean(co.lr[~early] - p_late)),
        'slope_ln_loan': float(fl.params[1]), 'slope_se': float(fl.bse[1]),
        'mob_coef': float(fl2.params[2]), 'mob_se': float(fl2.bse[2]),
        'pooled_mean': float(co.lr.mean()), 'pooled_median': float(co.lr.median()), 'n_ratio_above_1_capped': int((co.chargeoff_loss_ratio > 1).sum())}
say('LGD validation', {k: r4(v) if isinstance(v, float) else v for k, v in LGDV.items()})

# ----------------------------------------------------------------------------------------------------------------
# 5. timing of charge-offs within the observed window (replaces the resolved-only median)
# ----------------------------------------------------------------------------------------------------------------
fine = aj(d['T'].values, d.ev.values, list(range(6, 97, 1)))
tot96 = fine[96]
half = min(k for k, v in fine.items() if v >= tot96 / 2)
TIMING = {'cif96_pooled': r4(tot96), 'median_months_given_chargeoff_by_96': half,
          'share_by_24_of_96': r4(fine[24] / tot96), 'share_by_36_of_96': r4(fine[36] / tot96), 'share_by_60_of_96': r4(fine[60] / tot96),
          'resolved_only_median_months_to_chargeoff': float(d.loc[d.ev == 1, 'months_on_book'].median())}
say('timing', TIMING)

# ----------------------------------------------------------------------------------------------------------------
# save the fit (consumed by section 6: JS tables, patched copy, RESULT.json)
# ----------------------------------------------------------------------------------------------------------------
FIT = {'prime': {'value': PRIME_NOW, 'since': PRIME_SINCE, 'h15_last_obs': PRIME_LAST_OBS,
                 'recent_changes': [[str(a.date()), float(b)] for a, b in zip(prime_changes.date, prime_changes.prime_rate_pct)], 'spread_base': PRIME_RULE},
       'spread': spread_res, 'spread_validation': spread_val, 'spread_drift_variable_by_fy': drift.reset_index().to_dict('records'),
       'spread_share_above_sba_max': frac_above_cap,
       'hazard': {'n_loans': int(len(d)), 'events': np.bincount(d.ev.values).tolist(), 'exclusions': excl,
                  'tau2_co': TAU2_CO, 'tau2_pif': TAU2_PIF, 'spread_clip': SPREAD_CLIP, 'centers': CENT,
                  'edges': EDGES.tolist(), 'co_log_base': [None if not np.isfinite(v) else float(v) for v in lbc],
                  'pif_log_base': lbp.tolist(), 'co_terms': tco.to_dict('records'), 'pif_terms': tpf.to_dict('records'),
                  'spec_checks': spec, 'eb_naics6_a': A_N6, 'eb_state_a': A_ST, 'n6_at_cap': bool(n6_cap), 'st_at_cap': bool(st_cap),
                  'base60': BASE60, 'base96': BASE96, 'base120_flat': BASE120, 'base_term': BASE_TERM, 'ref60': REF60, 'ref96': REF96,
                  'ref120_flat': REF120, 'ref_term': REF_TERM, 'tail_factor': TAIL, 'tail_factor_se': TAIL_SE,
                  'aj_pooled': aj_pool, 'aj_pooled_se60': float(np.nanstd(aj_boot[:, 4])), 'aj_pooled_se96': float(np.nanstd(aj_boot[:, 7])),
                  'band_cif': band_rows, 'tail': tail, 'like_for_like': lfl, 'timing': TIMING},
       'validation': VAL, 'lgd': {'bands': lgd_bands.to_dict('records'), 'knots_usd': LGD_KNOTS_USD, 'mean_curve': lgd_fit.tolist(),
                                   'mean_curve_se': lgd_se.tolist(), 'validation': LGDV,
                                   'frac_logit': [float(fl.params[0]), float(fl.params[1]), float(fl.bse[0]), float(fl.bse[1])],
                                   'age_model': LGD_AGE_FIT}}
FIT['eb_app_naics6'] = n6_tab[n6_tab.k.isin(APP_N6.values())].to_dict('records')
FIT['eb_states'] = st_tab.to_dict('records')
FIT['sector_n'] = d.groupby('g2').size().to_dict()
FIT['hazard'].update({'clusters': N_CLUST, 'lender_fe': LENDER_FE, 'size_by_age': SIZE_BY_AGE, 'band_age_chi2': BAND_AGE_CHI2,
                      'shrink': {'gamma': GAMMA, 'gamma_se': GAMMA_SE, 'gamma_raw': GAMMA_RAW, 'shift': LP_SHIFT},
                      'base60_unshrunk': BASE60_RAW, 'base96_unshrunk': BASE96_RAW, 'pop_se': POP_SE, 'pop_term_se': POP_TERM_SE,
                      'ref96_se_hessian': REF96_HESS_SE, 'spec_base': SPEC_BASE, 'spec_range': SPEC_RANGE, 'newest_cohort_reference': NEWEST_REF,
                      'cohort_oe': COHORT_OE, 'rate_level': RATE_LEVEL, 'tau2_by_split': TAU_SPLITS, 'cycle': CYCLE,
                      'base_diag': BASE_DIAG, 'conditions': {'d25': D25, 'quarters': QDIAG, 'levels': COND, 'range': COND_RANGE},
                      'level_range': LEVEL_RANGE, 'no_spread': NOSPREAD, 'real_estate': RE_NOTE, 'jobs_check': JOBS_CHECK,
                      'band_console_ratio': BAND_CONSOLE_RATIO, 'band_console_z': BAND_CONSOLE_Z})
json.dump(FIT, open(OUT + 'fits.json', 'w'), indent=1, default=float)
say('\nsaved fits.json  (%.0fs)' % (time.time() - T0))

# ----------------------------------------------------------------------------------------------------------------
# 6. implementation: MODELS.risk (v3) and MODELS.fitted.sba_rate tables, new fitRisk, patched COPY of index.html, tests
# ----------------------------------------------------------------------------------------------------------------
say('\n== 6. implementation tables, patched copy, tests')
R4 = lambda v: float(round(float(v), 4))
SEC_MEMBERS = {'31': ['31', '32', '33'], '44': ['44', '45'], '48': ['48', '49']}


def expand(dct):
    out = {}
    for g, v in dct.items():
        for m in SEC_MEMBERS.get(g, [g]): out[m] = v
    return dict(sorted(out.items()))


def sd_of(f, nm):
    return math.sqrt(f['cov'][f['names'].index(nm), f['names'].index(nm)])


co_sec = {s: R4(par(f_main, 'sec_' + s)) for s in SECS if s != '00'}
co_sec_sd = {s: R4(sd_of(f_main, 'sec_' + s)) for s in SECS if s != '00'}
pif_sec = {s: R4(par(f_pif, 'sec_' + s)) for s in SECS if s != '00'}
APP_COVS = ['lnamt', 'franchise', 'spread']
n6_app = n6_tab[n6_tab.k.isin(APP_N6.values())].set_index('k')
st_keep = st_tab[(st_tab.k.str.len() == 2) & (st_tab.k != 'NA')].set_index('k')
v60 = VAL['cv5_chargeoff_by_60m']; vh = VAL['vintage_holdout_train_FY18_21_test_FY22_24']
ch = VAL['calendar_holdout_train_pre_2024H2_forecast_2024H2_2026H1']
n_open = int((d.ev == 0).sum()); n_co = int((d.ev == 1).sum()); n_pif = int((d.ev == 2).sum())
RESOLVED_ONLY = n_co / (n_co + n_pif)
lgd_b = lgd_bands.set_index('band')
SHIP_COVS = APP_COVS + ['lnamt_x_age']
_infl = [100 * (tco.set_index('term').loc[c, 'se_shipped'] / tco.set_index('term').loc[c, 'se'] - 1) for c in ['lnamt', 'spread', 'lnamt_x_age']]
SE_INFL = (min(_infl), max(_infl))
def se_of(tab_, col, c): return R4(tab_.set_index('term').loc[c, col])
RISK = {
    "model": "omni_risk_v3_hazard",
    "source": "SBA 7(a) FOIA (data.sba.gov), snapshot 2026-06-30; Fed H.15 prime",
    "population": "Change of Ownership (acquisition) 7(a) term loans approved FY2018-FY2026, disbursed; revolving lines excluded",
    "asof": "2026-06-30", "fitted": "2026-10-10", "script": "fit/sba_risk_refresh.py",
    "conditions": "2023-26",
    "n_fit": int(len(d)), "n_chgoff": n_co, "n_pif": n_pif, "n_open": n_open, "resolved_only_rate": R4(RESOLVED_ONLY),
    "form": ("cause-specific piecewise-exponential hazards by months on book; charge-off, with paid-in-full as the competing exit and "
             "open loans censored. Per piece j of age_edges: loan-level part u_j = co.coef.x + co.age_coef.lnamt*x.lnamt*(min(age_j,"
             "co.age_cap_months)/12 - co.age_center_years) + sector + naics6 + state; l1 = exp(co.log_base[j] + co.lp_shift + "
             "co.lp_shrink*u_j); l2 = exp(pif.log_base[j] + pif.coef.x + pif.sector); CIF(H) = sum_j S_j*l1/(l1+l2)*(1-exp(-(l1+l2)*dt_j)), "
             "S_{j+1} = S_j*exp(-(l1+l2)*dt_j). Term = CIF(observed_months) x tail_factor. Calendar terms at their 2023-26 level."),
    "horizon_months": 60, "observed_months": 96, "term_months": 120,
    "tail_factor": R4(TAIL), "tail_factor_se": R4(TAIL_SE),
    "tail_note": ("years 9-10 borrowed from all 7(a) term loans approved FY2010-15 (no acquisition loan is older than 8.5 years): "
                  "CIF(120)/CIF(96) by loan band x%.2f (under $150k) to x%.2f ($1.5M and up), partly because larger mature loans more often "
                  "carry 25-year terms; x%.2f = size-matched to acquisition loans (unweighted >= $150k x%.2f; the acquisition model's flat "
                  "hazard after 84 months x%.2f). The SE is a judgment covering that range. FY2011-12 vintages are lowest (x1.14): their years "
                  "9-10 fell in FY2020-22, when CARES s.1112 paid borrowers' P&I. Across FY2000-16 vintages the ratio ran x%.2f-%.2f."
                  % (tail_band['<150k']['ratio'], tail_band['>=1.5M']['ratio'], TAIL, tv[120] / tv[96], model_ratio_120_96,
                     CYCLE['r120_96_range'][0], CYCLE['r120_96_range'][1])),
    "tail_by_band": {k: {"ratio": v['ratio'], "n": v['n'], "acq_share": v['acq_share']} for k, v in tail_band.items()},
    "age_edges": [int(x) for x in EDGES],
    "centers": {"ln_loan": R4(CENT['ln_loan']), "ln1p_jobs": R4(CENT['ln1p_jobs']), "spread": CENT['spread']},
    "loan_share": 0.85, "loan_range": [25000, 5000000], "spread_range": [R4(SPREAD_CLIP[0]), 3.0],
    "co": {"log_base": [None if not np.isfinite(v) else R4(v) for v in lbc],
           "coef": {c: R4(par(f_main, c)) for c in APP_COVS},
           "age_coef": {"lnamt": R4(par(f_main, 'lnamt_x_age'))}, "age_cap_months": int(AGE_CAP), "age_center_years": AGE_C,
           "lp_shrink": R4(GAMMA), "lp_shrink_se": R4(GAMMA_SE), "lp_shift": R4(LP_SHIFT),
           "se": {c: se_of(tco, 'se_shipped', c) for c in SHIP_COVS},
           "se_hessian": {c: se_of(tco, 'se', c) for c in SHIP_COVS},
           "se_lender": {c: se_of(tco, 'se_cluster_lender', c) for c in SHIP_COVS},
           "se_twoway": {c: se_of(tco, 'se_cluster_twoway', c) for c in SHIP_COVS},
           "se_note": ("se = the largest of the Hessian, lender-clustered (%d lenders) and two-way lender x calendar-quarter (%d quarters) sandwich SEs; "
                       "for size, spread and size x age that is %.0f-%.0f%% above the Hessian SE" % (N_CLUST['n_lender'], N_CLUST['n_quarter'], *SE_INFL)),
           "sector": co_sec, "sector_sd": co_sec_sd,
           "not_applied": {"fixed": R4(par(f_main, 'fixed')), "spread_x_fixed": R4(par(f_main, 'spread_x_fixed')),
                           **{'cal%d' % y: R4(par(f_main, 'cal%d' % y)) for y in CAL_YEARS},
                           "note": "fixed-rate terms (the console assumes a variable-rate note) and calendar-year terms 2019-2022 (the console uses 2023-26 = current conditions)"}},
    "pif": {"log_base": [R4(v) for v in lbp], "coef": {c: R4(par(f_pif, c)) for c in APP_COVS},
            "se": {c: se_of(tpf, 'se_shipped', c) for c in APP_COVS}, "sector": expand(pif_sec)},
    "industry_effects": expand(co_sec), "sector_tau": R4(math.sqrt(TAU2_CO)),
    "naics6_effects": {k: R4(v) for k, v in n6_app.log_rr.items()},
    "naics6_n": {k: int(v) for k, v in n6_app.n_loans.items()},
    "naics6_sd": R4(math.sqrt(special.polygamma(1, A_N6))), "naics6_gamma_shape": R4(A_N6),
    "state_effects": {k: R4(v) for k, v in st_keep.log_rr.items()},
    "state_n": {k: int(v) for k, v in st_keep.n_loans.items()},
    "state_sd": R4(math.sqrt(special.polygamma(1, A_ST))), "state_gamma_shape": R4(A_ST),
    "base_cif": {"h60": R4(BASE60), "h96": R4(BASE96), "term": R4(BASE_TERM),
                 "definition": ("the console's own pricing (fitRisk: table spread, variable note, 2023-26 conditions, shrunk) averaged over every "
                                "FY2024-26 acquisition loan (n %d) with its own size, sector, 6-digit industry, state and franchise flag; co.lp_shift is "
                                "solved so that this 5-year mean equals the book's fitted 5-year level (each note at its own spread and rate type, "
                                "%.1f%% of them fixed-rate), so rel averages 1 over the book" % (len(recent), 100 * BASE_DIAG['fixed_share'])),
                 "se": {"h60": R4(POP_SE[60]), "h96": R4(POP_SE[96]), "term": R4(POP_TERM_SE)},
                 "spec_range": {"h60": SPEC_RANGE['h60'], "h96": SPEC_RANGE['h96']},
                 "conditions_range": {"h60": COND_RANGE['h60'], "h96": COND_RANGE['h96']},
                 "level_range": {"h60": LEVEL_RANGE['h60'], "h96": LEVEL_RANGE['h96'],
                                 "term": [R4(LEVEL_RANGE['h96'][0] * TAIL), R4(LEVEL_RANGE['h96'][1] * TAIL)]},
                 "conditions": {"ratio": R4(math.exp(D25['co'][0])), "log_coef": D25['co'][0], "se": max(D25['co'][1], D25['co'][2]),
                                "se_hessian": D25['co'][1], "se_quarter": D25['co'][2], "payoff_log_coef": D25['pif'][0], "payoff_se": D25['pif'][1],
                                "quarter_effects": QDIAG['quarter_effects_vs_2023Q1'], "welch_p": QDIAG['welch_p'],
                                "levels": COND,
                                "note": ("age-, size- and spread-adjusted charge-off hazard in calendar 2025-26 against 2023-24: x%.2f (log %.2f, SE %.2f "
                                         "quarter-clustered); every quarter from 2025Q2 to 2026Q2 sits below every 2023-24 quarter (Welch p %.3f, quarters "
                                         "as units). By charge-off date the largest quarterly batch is %s (%d), which fits a processing backlog being cleared "
                                         "as well as a lower underlying rate. Whether 2023-24 was a post-relief catch-up or 2025-26 slower SBA charge-off "
                                         "processing cannot be told apart, so the 2023-26 pooled level is shipped and the two periods bracket it."
                                         % (math.exp(D25['co'][0]), D25['co'][0], max(D25['co'][1], D25['co'][2]), QDIAG['welch_p'], QDIAG['largest_batch'][0], QDIAG['largest_batch'][1]))},
                 "newest_cohort": {"O": COHORT_OE['FY2024-26']['O'], "E": COHORT_OE['FY2024-26']['E'], "O_over_E": COHORT_OE['FY2024-26']['O_over_E']},
                 "note": ("mean of the console's pricing over FY2024-26 approvals if 2023-26 conditions hold (all notes, each priced as a variable note at "
                          "the table spread; the level shift absorbs the fixed-rate share). The 8-year figure runs %.1f-%.1f%% across specifications "
                          "(calendar-year vs approval-cohort terms, both or neither; payoff prime term; payoffs censored at 2026-03-31; everything "
                          "censored at the last fully reported quarter, 2025-12-31: %.1f%%) and %.1f-%.1f%% across reference periods (charge-off and "
                          "payoff conditions of 2023-24 only or 2025-26 only); the shipped %.1f%% is at the top of the specification range and just below the middle of the combined %.1f-%.1f%%. "
                          "Its parameter SE (%.2f pp) covers neither. The two-year forecast over-predicted (observed/predicted %.2f) and loans "
                          "approved FY2024-26 have so far been charged off at %.1fx the model on %d charge-offs (Poisson p %.2f); the vintage holdout "
                          "under-predicted (%.2f)."
                          % (100 * SPEC_RANGE['h96'][0], 100 * SPEC_RANGE['h96'][1], 100 * SPEC_BASE['everything censored at 2025-12-31']['h96'],
                             100 * COND_RANGE['h96'][0], 100 * COND_RANGE['h96'][1], 100 * BASE96, 100 * LEVEL_RANGE['h96'][0], 100 * LEVEL_RANGE['h96'][1],
                             100 * POP_SE[96], VAL['calendar_holdout_train_pre_2024H2_forecast_2024H2_2026H1']['new_full']['O_over_E'],
                             COHORT_OE['FY2024-26']['O_over_E'], COHORT_OE['FY2024-26']['O'], COHORT_OE['FY2024-26']['poisson_p_le'],
                             VAL['vintage_holdout_train_FY18_21_test_FY22_24']['new_full']['O_over_E'])),
                 "sensitivity": SPEC_BASE, "newest_cohort_as_reference": NEWEST_REF, "previous_definition": BASE_DIAG['previous_definition']},
    "staffing": {"applied": False, "coef_if_fitted": JOBS_CHECK['co_lnjobs'], "lr": JOBS_CHECK['co_lr'], "sba_jobs_median_by_loan_band": JOBS_CHECK['sba_jobs_median_by_loan_band'],
                 "note": ("SBA JobsSupported (jobs created plus retained, lender-reported) would add %+.3f (SE %.3f, Hessian) per unit of ln(1+jobs), LR %.1f; "
                          "not used, because the console's head count is a different measure (Census employees per revenue, several times the SBA "
                          "figure for the same loan), so risk does not move with staffing" % (JOBS_CHECK['co_lnjobs'][0], JOBS_CHECK['co_lnjobs'][1], JOBS_CHECK['co_lr']))},
    "real_estate": {"share_term_over_120m": {k: v['share_term_over_120m'] for k, v in RE_SHARE.items()},
                    "note": ("share of SBA acquisition notes with a term over 10 years (real-estate notes), paid-off and open loans: %s. A business-only "
                             "acquisition of the same size is probably riskier, and more severe, than shown; the data cannot separate it because SBA "
                             "overwrites the term of charged-off loans (standard terms on %.0f%% of charged-off loans against %.0f%% of others)."
                             % (', '.join('%s %.0f%%' % (k, 100 * v['share_term_over_120m']) for k, v in RE_SHARE.items()), 100 * RE_NOTE['standard_term_share_chargeoffs'],
                                100 * RE_NOTE['standard_term_share_others']))},
    "spread_channel": {"no_spread_lnamt": NOSPREAD['lnamt'], "cif96_ratio_shipped_over_nospread": NOSPREAD['cif96_ratio_shipped_over_nospread'],
                       "band_console60_nospread": NOSPREAD['band_console60'], "diff_range": NOSPREAD['diff_range'],
                       "note": ("with no rate entered the spread comes from the median table by loan size, so risk by size includes lender pricing "
                                "(larger loans get lower spreads). Against a model without the spread (the marginal risk given size: ln loan %.3f at 4 "
                                "years), the shipped 8-year figure runs x%.2f to x%.2f across $100k-$4M loans (average sector; %s)"
                                % (NOSPREAD['lnamt'][0], min(_rr), max(_rr), ', '.join('$%s x%.2f' % (('%gk' % (float(k) / 1e3)) if float(k) < 1e6 else ('%gM' % (float(k) / 1e6)), v)
                                                                                      for k, v in NOSPREAD['cif96_ratio_shipped_over_nospread'].items())))},
    "aj_pooled": {"cif60": R4(aj_pool[60]), "cif60_se": R4(np.nanstd(aj_boot[:, 4])), "cif96": R4(aj_pool[96]),
                  "cif96_se": R4(np.nanstd(aj_boot[:, 7]))},
    "size_band_cif": band_rows,
    "like_for_like": {k: {"n": v['n'], "cif60": v['cif60'], "cif60_150k": v['cif60_loans_150k_up']} for k, v in lfl.items() if k != 'other'},
    "rate_level": {"coef_given_spread": RATE_LEVEL['coef_calendar'], "coef_given_spread_and_cohorts": RATE_LEVEL['coef_calendar_cohort'],
                   "prime_sample_mean": RATE_LEVEL['prime_sample_mean'], "uplift_range": RATE_LEVEL['uplift_range'], "applied": False,
                   "note": ("prime at approval given the spread: %+.3f (SE %.3f) per pp with calendar terms, %+.3f (SE %.3f) once approval cohorts "
                            "are controlled; not applied (cohort-confounded, and prime moves after approval show no effect). At today's %.2f%% prime "
                            "against the sample mean %.2f%% it would raise the hazard %.0f-%.0f%%."
                            % (RATE_LEVEL['coef_calendar'][0], RATE_LEVEL['coef_calendar'][1], RATE_LEVEL['coef_calendar_cohort'][0],
                               RATE_LEVEL['coef_calendar_cohort'][1], PRIME_NOW, PRIME0_MEAN, 100 * RATE_LEVEL['uplift_range'][0],
                               100 * RATE_LEVEL['uplift_range'][1]))},
    "through_cycle": {"cif120_by_vintage": {str(k): v['cif120'] for k, v in cyc.items()}, "cif120_FY2006_08": CYCLE['cif120_FY2006_08'],
                      "cif120_FY2010_16": CYCLE['cif120_FY2010_16'], "acq_to_all_ratio": CYCLE['acq_to_all_150k_ratio_cif60'],
                      "note": "all SBA 7(a) term loans >= $150k (not acquisitions only), charged off within 10 years, by approval year"},
    "lender_heterogeneity": {"lr_top40": R4(LENDER_FE['lr']), "df": 40, "sd": LENDER_FE['eb_sd'], "rr_p5_p95": LENDER_FE['eb_rr_p5_p95_lenders_20plus_loans'],
                             "note": "not modelled: the console prices an average lender"},
    "cv_auc": R4(v60['new_full']['auc']), "cv_brier": R4(v60['new_full']['brier']),
    "validation": {"cv5_auc60": R4(v60['new_full']['auc']), "cv5_auc60_se": R4(v60['new_full']['auc_se_boot']),
                   "cv5_brier60": R4(v60['new_full']['brier']), "cv5_oe60": R4(v60['new_full']['O_over_E']),
                   "cv5_slope60": R4(v60['new_full']['calib_slope']), "cv5_auc60_null": R4(v60['null_age_calendar_only']['auc']),
                   "cv5_auc60_current": R4(v60['current_model_auc']),
                   "vintage_auc": R4(vh['new_full']['auc']), "vintage_oe": R4(vh['new_full']['O_over_E']),
                   "vintage_slope": R4(vh['new_full']['calib_slope']), "vintage_slope_se": R4(vh['new_full']['calib_slope_se']),
                   "vintage_auc_current": R4(vh['current_model_auc']), "n_events_vintage": int(vh['new_full']['events']),
                   "cal_holdout_auc": R4(ch['new_full']['auc']), "cal_holdout_oe": R4(ch['new_full']['O_over_E']),
                   "cal_holdout_slope": R4(ch['new_full']['calib_slope']), "cal_holdout_slope_se": R4(ch['new_full']['calib_slope_se']),
                   "cal_holdout_auc_current": R4(ch['current_model_auc']),
                   "n_events_60": int(v60['new_full']['events']), "n_events_cal_holdout": int(ch['new_full']['events']),
                   "oot_loan_level_slope": VAL['oot_shrink'], "cv5_loan_level_slope": [R4(VAL['cv5_slope_loan_level']['pooled']), R4(VAL['cv5_slope_loan_level']['pooled_se'])],
                   "cohort_oe": COHORT_OE, "band_age_chi2": {k: R4(v) for k, v in BAND_AGE_CHI2.items()},
                   "note": ("unshrunk model scored on each split; variance components re-estimated in every split; 6-digit and state maps refitted "
                            "in every split; functional forms (spread cap, size x age, log jobs, calendar grouping) chosen on the full sample")},
    "timing": TIMING,
    "lgd": {"form": "severity(age) = 1/(1+exp(-(b0 + b_size*(ln loan - centers.ln_loan) + b_age*(clamp(age,age_range)/12 - age_center_years)))); "
                    "expected loss = sum over hazard pieces of P(charge-off in piece) x severity(piece midpoint) + tail x severity(108 months)",
            "b0": R4(LGD_AGE_FIT['b0']), "b_size": R4(LGD_AGE_FIT['b_size']), "b_age": R4(LGD_AGE_FIT['b_age']),
            "se": {"b0": R4(LGD_AGE_FIT['se'][0]), "b_size": R4(LGD_AGE_FIT['se'][1]), "b_age": R4(LGD_AGE_FIT['se'][2])},
            "age_center_years": 4.0, "age_range": LGD_AGE_RANGE,
            "size_only_curve": {"loan_usd": LGD_KNOTS_USD, "lgd": [R4(v) for v in lgd_fit], "se": [R4(v) for v in lgd_se],
                                "note": "mean severity by size ignoring when the loan fails (fractional logit on ln loan); display/reference only"},
            "mean": R4(LGDV['pooled_mean']), "median": R4(LGDV['pooled_median']), "n": LGDV['n'],
            "by_loan_size": {b: {"n": int(lgd_b.loc[b, 'n']), "mean": R4(lgd_b.loc[b, 'mean']), "se": R4(lgd_b.loc[b, 'se_mean']),
                                 "median": R4(lgd_b.loc[b, 'median'])} for b in lgd_b.index},
            "post_term_ratio": tail['ratio_144_over_120_FY2010_13'],
            "note": ("gross charge-off / original approval on charged-off acquisition term loans; gross of recoveries, after amortisation. "
                     "expLoss counts charge-offs by month 120; loans that default in years 8-10 are charged off later (mature 7(a) loans "
                     "approved FY2010-13: CIF(144)/CIF(120) = %.2f), so lifetime loss on the note runs higher" % tail['ratio_144_over_120_FY2010_13'])},
    "EXCLUDED_FIELD": "TermInMonths - SBA overwrites it with months-to-chargeoff. Leaks the label. Never use.",
    "not_used": ("rate level at approval (confounded with the COVID-relief cohorts; the spread over prime carries the risk signal) and "
                 "prime moves after approval (payment-shock term %.3f, SE %.3f): prime is held flat at today's value"
                 % (spec['+dprimeV_payment_shock']['terms']['dprimeV'][0], spec['+dprimeV_payment_shock']['terms']['dprimeV'][1])),
}
spq = spread_res['V']
_stc = spq['status_counts']
SBA_RATE = {"prime": PRIME_NOW, "prime_asof": PRIME_SINCE, "prime_source": "Fed H.15 bank prime loan rate (RIFSPBLP_N.B), observed through %s" % PRIME_LAST_OBS,
            "spread_knots": [[R4(math.log(k)), float(round(v, 2))] for k, v in zip(SP_KNOTS_USD, spq['values'])],
            "spread_knots_se": [float(round(v, 3)) for v in spq['unc']],
            "spread_knots_boot_se": [float(round(v, 3)) for v in spq['se']],
            "spread_base": "prime in effect on the first business day of the approval month (13 CFR 120.214(c))",
            "n": spq['n'], "n_cancelled": int(_stc.get('CANCLD', 0)), "n_undisbursed": int(_stc.get('COMMIT', 0)),
            "median_spread": float(spq['median_all']),
            "fixed_rate_knots": [[R4(math.log(k)), float(round(v, 2))] for k, v in zip(SP_KNOTS_USD, spread_res['F']['values'])],
            "fixed_rate_n": spread_res['F']['n'],
            "source": ("SBA FOIA 7(a) as of 2026-06-30, change-of-ownership variable-rate term loans approved FY2025-26 (Oct 2024 - Jun 2026), "
                       "including %d cancelled and %d approved but not yet disbursed: median of initial rate minus the prime in effect on the first business day of the approval month (Fed H.15; the base SBA rules peg variable 7(a) rates to, 13 CFR 120.214(c)), "
                       "by ln(loan), made non-increasing. Knot uncertainty %.2f-%.2f pp (the largest of the bootstrap SE, the range across "
                       "samples - disbursed only, FY2025 only, FY2026 only, FY2018-26 - and 0.05 pp, because rates heap at quarter points)"
                       % (_stc.get('CANCLD', 0), _stc.get('COMMIT', 0), min(spq['unc']), max(spq['unc'])))}

# the new JavaScript ---------------------------------------------------------------------------------------------
JS_FITRISK = r'''/* ---- Model V: post-acquisition survival risk (FITTED, SBA 7(a) competing-risk hazard) ----
   The probability that the acquisition loan is CHARGED OFF within a stated horizon, if 2023-26 conditions
   hold. Fitted on every change-of-ownership 7(a) term loan approved FY2018-26 (SBA FOIA as of 2026-06-30)
   as two hazards by months on book: charge-off, and payoff as the competing exit; the 69% of loans still
   open are censored, not dropped. The old logistic used resolved loans only, which over-weights early
   failures and early payoffs and gave 5.7% with no horizon. Reported: within 5 years (fitted on loans
   observed that long), and within 10 years (fitted to 8 years; years 9-10 borrowed from mature 7(a)
   vintages, x tail_factor, a labelled judgment). The note is 85% of the price (as in sbaRate), held inside
   the 7(a) range. Larger loans are charged off less often through month 72 (x0.89 per tenfold loan size in the
   piece starting at month 60); from month 72 the sign reverses (about x1.16 per tenfold, held there): the hazard
   reads years on book at each piece's start, so the effect moves in steps (larger
   SBA acquisition notes are more often 25-year real-estate notes, which may simply take longer to liquidate).
   Out of time, risk differences held at about three quarters of their fitted size, so every loan-level
   effect is shrunk by co.lp_shrink toward the average loan. co.lp_shift is solved so that this function,
   applied to every FY2024-26 acquisition loan, averages the book's fitted level; base_cif is that average,
   so rel compares a deal with the average loan as this console prices it.
   The rate enters as its spread over today's prime: the rate LEVEL is not identified apart from the
   COVID-relief cohorts, and prime moves after approval showed no effect, so prime is held flat. The spread
   is lender risk-pricing, an association, not a lever; with no rate entered it comes from the median table
   by size. Calendar terms sit at their 2023-26 level; the loan is priced as a variable-rate note at the
   table spread; the lender is an average lender. Staffing is not used: SBA's jobs count is not the
   console's head count (the `jobs` argument is kept for the interface and ignored). */
const RISK_NAICS6={"home":"238220","medical":"621111","vet":"541940","msp":"541511","prof":"541211","mfg":"339950",
  "dist":"423310","staff":"561320","land":"561730","wash":"811192","auto":"811111","constr":"238990","fit":"713940","rest":"722511"};
/* no "ecom": its value model reads BIZCOMPS' 541512 (an online-retail label there), but in SBA data 541512 is
   computer-systems design. Online retailers are filed under 44-45, which is where their default history is. */
function fitRisk(price,naicsKey,rate,jobs,franchise,st){
  const R=MODELS.risk,C=R.co,Q=R.pif,c0=R.centers,n2=naicsFor(naicsKey),n6=RISK_NAICS6[naicsKey]||null;
  const loan=clamp(R.loan_share*Math.max(price,1),R.loan_range[0],R.loan_range[1]);
  const r=(rate!=null&&isFinite(rate))?rate:sbaRate(price);
  const spread=clamp(r-MODELS.fitted.sba_rate.prime,R.spread_range[0],R.spread_range[1]);
  const x={lnamt:Math.log(loan)-c0.ln_loan,franchise:franchise?1:0,spread:spread-c0.spread};
  /* sector: random effect, shrunk toward the average sector. 6-digit industry and state: Poisson-gamma
     empirical-Bayes multipliers on the charge-off hazard, shrunk toward the sector and the nation. 0 when unknown. */
  const ie=R.industry_effects[n2]!==undefined?R.industry_effects[n2]:0;
  const e6=(n6&&R.naics6_effects[n6]!==undefined)?R.naics6_effects[n6]:0;
  const se=(st&&R.state_effects&&R.state_effects[st]!==undefined)?R.state_effects[st]:0;
  let lc=ie+e6+se, lp=Q.sector[n2]!==undefined?Q.sector[n2]:0;
  for(const k in C.coef) lc+=C.coef[k]*x[k];
  for(const k in Q.coef) lp+=Q.coef[k]*x[k];
  /* severity: MEAN charge-off as a share of the original advance (expected loss needs the mean, not the
     median). It falls the later a loan fails, because the note has amortised, and a little with size. */
  const G=R.lgd, sev=a=>1/(1+Math.exp(-(G.b0+G.b_size*x.lnamt
                    +G.b_age*(clamp(a,G.age_range[0],G.age_range[1])/12-G.age_center_years))));
  const E=R.age_edges;
  const run=H=>{ let S=1,F=0,EL=0;
    for(let j=0;j<E.length&&E[j]<H;j++){
      const dt=Math.min(j+1<E.length?E[j+1]:Infinity,H)-E[j];
      /* the size effect changes with years on book (to age_cap_months); then every loan-level effect is shrunk */
      const ya=Math.min(E[j],C.age_cap_months)/12-C.age_center_years; let u=lc;
      for(const k in C.age_coef) u+=C.age_coef[k]*x[k]*ya;
      const l1=C.log_base[j]==null?0:Math.exp(C.log_base[j]+C.lp_shift+C.lp_shrink*u),
            l2=Math.exp(Q.log_base[j]+lp), L=l1+l2;
      if(L>0){ const inc=S*l1/L*(1-Math.exp(-L*dt)); F+=inc; EL+=inc*sev(E[j]+dt/2); S*=Math.exp(-L*dt); } }
    return {F:F,EL:EL}; };
  const r5=run(R.horizon_months), r8=run(R.observed_months);
  const p5=r5.F, p8=r8.F, pTerm=p8*R.tail_factor;
  /* expected loss charged off by month 120, as a share of the original loan: each slice of charge-off
     probability times the severity at that age; the borrowed last two years at the midpoint of years 9-10.
     Loans that default late are charged off after month 120, so the note's lifetime loss runs higher. */
  const expLoss=r8.EL+(pTerm-p8)*sev((R.observed_months+R.term_months)/2), lgd=expLoss/pTerm;
  /* the multiple compares this loan with the average FY2024-26 acquisition loan, priced the same way, at the
     headline's horizon */
  const base=R.base_cif.term, rel=pTerm/base;
  /* the observed share charged off within 5 years for loans of this size (Aalen-Johansen), beside the model */
  const SB=R.size_band_cif||{};
  const sbk=loan<250e3?"<250K":loan<500e3?"250-500K":loan<1e6?"500K-1M":loan<2e6?"1-2M":"2-5M";
  const emp=SB[sbk]?SB[sbk].cif60:null;
  return {p:pTerm,p5:p5,p8:p8,pTerm:pTerm,horizon:R.horizon_months,term:R.term_months,base:base,rel:rel,
    loan:loan,spread:spread,indEff:ie,naics6Eff:e6,stateEff:se,
    empBand:emp,empBandKey:sbk,empBandN:SB[sbk]?SB[sbk].n:0,
    tier:rel<.75?"low":rel<.95?"below average":rel<1.25?"average":rel<1.75?"elevated":"high",
    medYears:R.timing.median_months_given_chargeoff_by_96/12,within3:R.timing.share_by_36_of_96,
    lgd:lgd,expLoss:expLoss};
}
'''

JS_HERO = r'''(function(){const e=$("o_risk"),k=r.risk,R=MODELS.risk,B=R.base_cif;
    /* headline: charged off within 10 years if 2023-26 conditions hold; the 5-year figure is the part
       fitted on loans observed that long. The multiple compares with the average acquisition loan, priced
       the same way, at the same 10-year horizon. */
    let h=pc(k.p,1)+'  <span class="muted">('+k.rel.toFixed(2)+'×)</span>'
      +'<span class="sub2">charged off within '+(k.term/12)+' yrs if '+R.conditions+' conditions hold; '
      +pc(k.p5,1)+' within '+(k.horizon/12)+' yrs</span>';
    let t="";
    if(k.empBand!=null){
      t="SBA acquisition loans of "+k.empBandKey+": "+(k.empBand*100).toFixed(2)
        +"% charged off within 5 years (Aalen-Johansen, "+k.empBandN.toLocaleString()+" loans). ";
      h+='<span class="sub2">'+k.empBandKey+' loans: '+(k.empBand*100).toFixed(1)+'% observed by 5 yrs</span>';
    }
    t+="Charge-offs in 2025-26 ran about "+B.conditions.ratio.toFixed(2)+"× the 2023-24 rate (age-adjusted); taking either period as current puts this figure at about "
      +pc(k.p*B.conditions_range.h96[0]/B.h96,1)+"-"+pc(k.p*B.conditions_range.h96[1]/B.h96,1)+". ";
    t+="Loans written at today's prime may run "+Math.round(R.rate_level.uplift_range[0]*100)+"-"
      +Math.round(R.rate_level.uplift_range[1]*100)+"% higher (rate level, not applied). Through the cycle, 7(a) loans over $150k approved 2006-08 were "
      +Math.round(R.through_cycle.cif120_FY2006_08[0]*100)+"-"+Math.round(R.through_cycle.cif120_FY2006_08[1]*100)+"% charged off within 10 years.";
    e.title=t;
    if(k.expLoss!=null)
      h+='<span class="sub2">expected loss '+(k.expLoss*100).toFixed(1)+'% of the loan, charged off by year '+(k.term/12)+' ('
        +(k.lgd*100).toFixed(0)+'% mean severity)</span>';
    e.innerHTML=h;})();'''

old_hero_start = '(function(){const e=$("o_risk");'
old_hero_end = 'e.innerHTML=h;})();'

i0 = html.index(old_hero_start); i1 = html.index(old_hero_end, i0) + len(old_hero_end)
OLD_HERO = html[i0:i1]
fr0 = html.index('/* ---- Model V: post-acquisition survival risk (FITTED, SBA) ---- */')
fr1 = html.index('/* ---- Model I: probability of closing', fr0)
OLD_FITRISK = html[fr0:fr1]
dv0 = html.index('<div class="panel" style="margin-top:14px"><p class="grp-title">Model V')
dv1 = html.index('</div></section>`;', dv0)
OLD_DATAV = html[dv0:dv1]
trap1 = re.search(r'<p class="note"><b>1\. <code>TermInMonths</code> is excluded\.</b>.*?</p>', OLD_DATAV, re.S).group(0)

DATA_V = r'''<div class="panel" style="margin-top:14px"><p class="grp-title">Model V — post-acquisition survival risk</p>
    <p class="note" style="margin-bottom:12px">Competing-risk hazard on <b>${R.n_fit.toLocaleString()}</b>
    SBA 7(a) <i>acquisition</i> term loans (<code>BusinessAge = "Change of Ownership"</code>), FY2018&ndash;2026, SBA FOIA as of ${R.asof}:
    ${R.n_chgoff.toLocaleString()} charged off, ${R.n_pif.toLocaleString()} paid in full and ${R.n_open.toLocaleString()} still open, which are
    censored rather than dropped. Charge-off and payoff are fitted as two hazards by months on book, so the number reported is a
    probability with a horizon: <b>charged off within ${R.horizon_months/12} years</b>, and within ${R.term_months/12} years,
    <b>if ${R.conditions} conditions hold</b>.</p>
    <div class="tw"><table>
      <thead><tr><th>Charge-off hazard</th><th class="n">Coefficient</th><th class="n">SE</th><th>Reads as</th></tr></thead>
      <tbody>
        <tr><td>ln(loan) at 4 years on book, loan = 85% of price</td><td class="n" style="color:#5ee0a8">${R.co.coef.lnamt.toFixed(3)}</td><td class="n">${R.co.se.lnamt.toFixed(3)}</td><td>larger loans are charged off less often</td></tr>
        <tr><td>ln(loan) &times; years on book (to ${R.co.age_cap_months/12})</td><td class="n">${R.co.age_coef.lnamt.toFixed(3)}</td><td class="n">${R.co.se.lnamt_x_age.toFixed(3)}</td><td>and later: the gap closes by year ${R.co.age_cap_months/12}</td></tr>
        <tr><td>spread over prime (pp, capped at 3)</td><td class="n" style="color:var(--amber)">${R.co.coef.spread.toFixed(3)}</td><td class="n">${R.co.se.spread.toFixed(3)}</td><td>lenders charge more where they see more risk (an association, not a lever)</td></tr>
        <tr><td>franchise</td><td class="n">${R.co.coef.franchise.toFixed(3)}</td><td class="n">${R.co.se.franchise.toFixed(3)}</td><td>no measurable difference</td></tr>
        <tr><td>sector, ${Object.keys(R.co.sector).length} groups</td><td class="n">sd ${R.sector_tau.toFixed(2)}</td><td class="n">&mdash;</td><td>random effect, shrunk toward the average</td></tr>
        <tr><td>6-digit industry within sector</td><td class="n">sd ${R.naics6_sd.toFixed(2)}</td><td class="n">&mdash;</td><td>empirical Bayes, shrunk toward the sector</td></tr>
        <tr><td>state, ${Object.keys(R.state_effects||{}).length}</td><td class="n">sd ${R.state_sd.toFixed(2)}</td><td class="n">&mdash;</td><td>empirical Bayes, shrunk toward the nation</td></tr>
        <tr><td>all of the above, out of time</td><td class="n">&times;${R.co.lp_shrink.toFixed(2)}</td><td class="n">${R.co.lp_shrink_se.toFixed(2)}</td><td>held at this share of their fitted size on later loans and later years; applied, toward the average loan</td></tr>
        <tr><td>rate level, given the spread</td><td class="n muted">0</td><td class="n">&mdash;</td><td style="color:#ff8e7a;padding-left:6px">${R.rate_level.coef_given_spread[0]>=0?"+":""}${R.rate_level.coef_given_spread[0].toFixed(2)} (SE ${R.rate_level.coef_given_spread[1].toFixed(2)}) per pt, ${R.rate_level.coef_given_spread_and_cohorts[0]>=0?"+":""}${R.rate_level.coef_given_spread_and_cohorts[0].toFixed(2)} (${R.rate_level.coef_given_spread_and_cohorts[1].toFixed(2)}) with approval cohorts; not applied</td></tr>
        <tr><td>staffing (SBA jobs supported)</td><td class="n muted">0</td><td class="n">&mdash;</td><td style="color:#ff8e7a;padding-left:6px">${R.staffing.coef_if_fitted[0]>=0?"+":""}${R.staffing.coef_if_fitted[0].toFixed(2)} (SE ${R.staffing.coef_if_fitted[1].toFixed(2)}) per ln(1+jobs) if fitted; not used: SBA counts jobs created and retained, the console counts Census employees, several times more</td></tr>
      </tbody>
    </table></div>
    <p class="note" style="margin-top:6px;font-size:11.8px">SEs are the largest of the model-based, lender-clustered and two-way lender &times; calendar-quarter estimates: SBA processes charge-offs
    in batches and lenders differ (between-lender sd ${R.lender_heterogeneity.sd.toFixed(2)} in log hazard, empirical Bayes; the 40 largest as fixed effects: LR ${R.lender_heterogeneity.lr_top40.toFixed(0)} on 40 df). The console prices an average lender.
    Loans written at today's prime may run ${Math.round(R.rate_level.uplift_range[0]*100)}&ndash;${Math.round(R.rate_level.uplift_range[1]*100)}% above the level shown.
    With no rate entered, the spread is read off the median table for the loan size, so risk by size includes lender pricing (larger loans get lower spreads):
    against a model without the spread, the 8-year figure here runs &times;${Math.min(...Object.values(R.spread_channel.cif96_ratio_shipped_over_nospread)).toFixed(2)}&ndash;${Math.max(...Object.values(R.spread_channel.cif96_ratio_shipped_over_nospread)).toFixed(2)} across $100K&ndash;$4M loans.
    Real-estate notes: ${(R.real_estate.share_term_over_120m["<250K"]*100).toFixed(0)}% of SBA acquisition notes under $250K run longer than 10 years, against ${(R.real_estate.share_term_over_120m["2-5M"]*100).toFixed(0)}% over $2M.
    A business-only acquisition of the same size is probably riskier than shown; SBA overwrites the term of charged-off loans, so this cannot be separated.</p>
    <div class="chk" style="margin-top:10px"><div>Out-of-sample AUC, charge-off within 5 years<div class="muted" style="font-size:11.8px">5-fold CV by loan; the resolved-only logistic scored ${R.validation.cv5_auc60_current.toFixed(3)} on the same loans</div></div>
      <span class="n" style="color:#5ee0a8">${R.validation.cv5_auc60.toFixed(3)}</span><span class="n muted">Brier ${R.validation.cv5_brier60.toFixed(4)} &middot; observed/predicted ${R.validation.cv5_oe60.toFixed(2)}</span><span class="st pub">fitted</span></div>
    <div class="chk"><div>Newer loans<div class="muted" style="font-size:11.8px">fitted on FY2018&ndash;21 approvals, scored on the ${R.validation.n_events_vintage} charge-offs of FY2022&ndash;24 approvals: under-predicted</div></div>
      <span class="n" style="color:var(--amber)">AUC ${R.validation.vintage_auc.toFixed(3)}</span><span class="n muted">observed/predicted ${R.validation.vintage_oe.toFixed(2)} &middot; slope ${R.validation.vintage_slope.toFixed(2)}</span><span class="st pub">fitted</span></div>
    <div class="chk"><div>Two-year forecast<div class="muted" style="font-size:11.8px">fitted on data before July 2024, scored on the ${R.validation.n_events_cal_holdout} charge-offs of July 2024&ndash;June 2026: over-predicted, and too spread out</div></div>
      <span class="n" style="color:var(--amber)">AUC ${R.validation.cal_holdout_auc.toFixed(3)}</span><span class="n muted">observed/predicted ${R.validation.cal_holdout_oe.toFixed(2)} &middot; slope ${R.validation.cal_holdout_slope.toFixed(2)}</span><span class="st pub">fitted</span></div>
    <div class="chk"><div>Population level across specifications and reference periods<div class="muted" style="font-size:11.8px">specifications (calendar vs approval-cohort terms, payoff censoring, the last fully reported quarter) ${(R.base_cif.spec_range.h96[0]*100).toFixed(1)}&ndash;${(R.base_cif.spec_range.h96[1]*100).toFixed(1)}%;
      charge-offs in 2025&ndash;26 ran ${R.base_cif.conditions.ratio.toFixed(2)}&times; the 2023&ndash;24 rate (age-adjusted), and taking either period as current gives ${(R.base_cif.conditions_range.h96[0]*100).toFixed(1)}&ndash;${(R.base_cif.conditions_range.h96[1]*100).toFixed(1)}%.
      The shipped level is in the upper part: the two-year forecast over-predicted, and FY2024&ndash;26 approvals so far run ${R.base_cif.newest_cohort.O_over_E.toFixed(1)}&times; the model on ${R.base_cif.newest_cohort.O} charge-offs</div></div>
      <span class="n" style="color:var(--bright)">${(R.base_cif.level_range.h96[0]*100).toFixed(1)}&ndash;${(R.base_cif.level_range.h96[1]*100).toFixed(1)}%</span><span class="n muted">within 8 years; ${(R.base_cif.h96*100).toFixed(1)}% shipped</span><span class="st pub">fitted</span></div>
    <div class="chk"><div>Acquisition loans charged off within 5 years<div class="muted" style="font-size:11.8px">same horizon, same data: startups and new businesses ${(R.like_for_like.startup_or_new.cif60*100).toFixed(1)}%, existing businesses ${(R.like_for_like.existing.cif60*100).toFixed(1)}%; loans over $150k only: ${(R.like_for_like.acquisition.cif60_150k*100).toFixed(1)}% vs ${(R.like_for_like.startup_or_new.cif60_150k*100).toFixed(1)}% and ${(R.like_for_like.existing.cif60_150k*100).toFixed(1)}%</div></div>
      <span class="n" style="color:#5ee0a8">${(R.aj_pooled.cif60*100).toFixed(2)}%</span><span class="n muted">${(R.aj_pooled.cif96*100).toFixed(2)}% within 8 years</span><span class="st pub">measured</span></div>
    <div class="chk"><div>Through the cycle<div class="muted" style="font-size:11.8px">all 7(a) loans over $150k charged off within 10 years: approved 2010&ndash;16 ${(R.through_cycle.cif120_FY2010_16[0]*100).toFixed(1)}&ndash;${(R.through_cycle.cif120_FY2010_16[1]*100).toFixed(1)}%; the 10-year figure here assumes ${R.conditions} conditions hold</div></div>
      <span class="n" style="color:#ff8e7a">${(R.through_cycle.cif120_FY2006_08[0]*100).toFixed(0)}&ndash;${(R.through_cycle.cif120_FY2006_08[1]*100).toFixed(0)}%</span><span class="n muted">approved 2006&ndash;08</span><span class="st pub">measured</span></div>
    <div class="chk"><div>Charge-offs come late<div class="muted" style="font-size:11.8px">of loans charged off within 8 years, ${(R.timing.share_by_36_of_96*100).toFixed(0)}% went by year 3; charge-off trails default by 1&ndash;2 years</div></div>
      <span class="n" style="color:var(--bright)">${(R.timing.median_months_given_chargeoff_by_96/12).toFixed(1)} yr</span><span class="n muted">median, given charge-off within 8 years</span><span class="st pub">measured</span></div>
    </div>

    <div class="panel" style="margin-top:14px;border-color:rgba(255,142,122,.34)">
    <p class="grp-title" style="color:#ff8e7a">Four traps in the source data, handled</p>
    ''' + trap1 + r'''
    <p class="note"><b>2. Open loans are censored, not dropped.</b> ${(R.n_open/R.n_fit*100).toFixed(0)}% of these loans are still
    open. A model of loans that have ended sees only those that failed or paid off early; it read
    ${(R.resolved_only_rate*100).toFixed(1)}% with no horizon. The hazard model uses every month each loan has been watched.</p>
    <p class="note"><b>3. COVID relief.</b> The SBA paid borrowers' principal and interest for months in 2020&ndash;21, and
    charge-offs trail defaults. Calendar-year terms absorb it, and the console uses the 2023&ndash;26 level as current conditions.</p>
    <p class="note" style="margin-bottom:0"><b>4. The last two years are borrowed.</b> No acquisition loan here is older than
    8.5 years. The curve is fitted to 8 years; years 9&ndash;10 are borrowed from mature 7(a) loans approved 2010&ndash;15:
    &times;${R.tail_by_band["<150k"].ratio.toFixed(2)} (small loans) to &times;${R.tail_by_band[">=1.5M"].ratio.toFixed(2)} (loans over $1.5M), partly because larger
    mature loans more often carry 25-year terms; &times;${R.tail_factor.toFixed(2)} used (matched to the size of acquisition loans; SE ${R.tail_factor_se.toFixed(2)}, a judgment).
    The 2011&ndash;12 vintages, whose years 9&ndash;10 overlapped CARES relief, are the lowest.</p>
    '''

PATCHES = [
    (OLD_FITRISK, JS_FITRISK + '\n'),
    (OLD_HERO, JS_HERO),
    ("""  /* The SBA's own default rate for this deal size sits beside the fitted number:
     the console held size_band_rates and never showed it, so there was no way to see
     whether the model was anywhere near the population it came from. */""",
     """  /* The observed share of SBA acquisition loans of this size charged off within 5 years
     (Aalen-Johansen, open loans censored) sits beside the fitted number, so the model can be
     checked against the population it came from. */"""),
    (OLD_DATAV, DATA_V),
    ("""     risk  : SBA 7(a)  13,613 resolved acqs CV AUC 0.6255, Brier 0.05321
             + state effects, + loss-given-default 0.774
             (industry table from 1,152,544 mature loans)""",
     """     risk  : SBA 7(a) %s acquisition loans, competing-risk hazard (open loans censored);
             charge-off within 5 years: CV AUC %.3f, Brier %.4f; size effect fades with loan age;
             + sector, 6-digit and state empirical-Bayes effects; loan-level effects x%.2f (out-of-time
             slope); mean loss-given-default %.3f; 10-year figure if 2023-26 conditions hold (refit 2026-10-10)"""
     % (format(len(d), ','), v60['new_full']['auc'], v60['new_full']['brier'], GAMMA, LGDV['pooled_mean'])),
    ("""/* SBA 7(a) acquisition rate: today's prime plus the spread lenders actually charged on
   change-of-ownership loans of this size (FY2023 FOIA file). Was a flat 10.5%. The loan
   is taken as 85% of the price, the usual SBA acquisition structure. */""",
     """/* SBA 7(a) acquisition rate: today's prime (Fed H.15) plus the median spread lenders charged on
   variable-rate change-of-ownership loans of this size approved FY2025-26 (SBA FOIA as of
   2026-06-30), measured over the prime in effect on the first business day of the approval
   month, the base SBA rules peg variable 7(a) rates to (13 CFR 120.214(c)). Was a flat 10.5%.
   The loan is taken as 85% of the price, the usual SBA acquisition structure. */"""),
    ("""  $("o_conf").textContent=`Fitted on ${MODELS.value.n_fit.toLocaleString()} closed sales and ${MODELS.risk.n_fit.toLocaleString()} resolved acquisitions — value R² ${MODELS.value.cv_r2_log}, risk AUC ${MODELS.risk.cv_auc}`;""",
     """  $("o_conf").textContent=`Fitted on ${MODELS.value.n_fit.toLocaleString()} closed sales and ${MODELS.risk.n_fit.toLocaleString()} acquisition loans — value R² ${MODELS.value.cv_r2_log}, 5-year risk AUC ${MODELS.risk.cv_auc}`;"""),
    ("""             + 1 + Object.keys(R.coefficients).length + Object.keys(R.industry_effects).length
             + Object.keys(R.state_effects||{}).length""",
     """             + R.co.log_base.filter(v=>v!=null).length + R.pif.log_base.length    /* hazard baselines */
             + Object.keys(R.co.coef).length + Object.keys(R.co.age_coef).length + Object.keys(R.pif.coef).length
             + 3   /* covariates, size x age, shrink and level shift, tail factor */
             + Object.keys(R.co.sector).length + Object.keys(R.naics6_effects).length
             + Object.keys(R.state_effects||{}).length"""),
    ("""    <p class="note"><b>When these loans fail, they fail hard.</b> Median loss is 77.4% of the
    original advance across 774 charged-off acquisition loans, and that barely moves with loan size
    (${(R.lgd.by_size_curve.lgd[0]*100).toFixed(1)}% under $250K, ${(R.lgd.by_size_curve.lgd[R.lgd.by_size_curve.lgd.length-1]*100).toFixed(1)}% from $500K up, after pooling). A 6% chance of default on a $2M note is not a 6% problem.</p>""",
     """    <p class="note"><b>When these loans fail, they fail hard.</b> A charged-off acquisition loan loses on average
    ${(R.lgd.mean*100).toFixed(1)}% of the original advance (median ${(R.lgd.median*100).toFixed(1)}%, ${R.lgd.n} loans). The later it fails, the
    less is left to lose: ${(R.lgd.display.sev_at_24m*100).toFixed(0)}% for a $650K note charged off at two years, ${(R.lgd.display.sev_at_84m*100).toFixed(0)}% at seven.
    Size matters little. Expected loss weights severity by when charge-offs happen
    (${(R.lgd.display.term_weighted*100).toFixed(0)}% over a 10-year term, counting charge-offs by month 120; loans that default in years 8&ndash;10
    are charged off later, so the note's lifetime loss runs higher, by about ${((R.lgd.post_term_ratio-1)*100).toFixed(0)}% on mature 7(a) loans).
    A 6% chance of default on a $2M note is not a 6% problem.</p>"""),
    ("""        <td>${Fv.sba_rate.n.toLocaleString()} change-of-ownership 7(a) loans, FY2023 (SBA FOIA)</td></tr>""",
     """        <td>${Fv.sba_rate.n.toLocaleString()} variable-rate change-of-ownership 7(a) loans approved FY2025&ndash;26, including cancelled and undisbursed approvals (SBA FOIA as of 2026-06-30); spread over the prime on the first business day of the approval month, as SBA rules set it (Fed H.15); each size point &plusmn;${Math.min(...Fv.sba_rate.spread_knots_se).toFixed(2)}&ndash;${Math.max(...Fv.sba_rate.spread_knots_se).toFixed(2)} pts</td></tr>"""),
    ("""<li><span class="pv f"><i></i>fitted</span> <b>Post-acquisition survival risk</b> &mdash;
logistic on <b>${MODELS.risk.n_fit.toLocaleString()}</b> resolved SBA 7(a) acquisition loans, industry
table from <b>1,152,544</b> mature loans. CV AUC <b>${MODELS.risk.cv_auc}</b>, Brier ${MODELS.risk.cv_brier}.
Acquisition baseline <b>${(MODELS.risk.base_rate*100).toFixed(2)}%</b> versus ${(MODELS.risk.full_dataset_base_rate*100).toFixed(2)}% across every 7(a) loan in the same SBA data &mdash;
buying an existing business is measurably safer than starting one. Median time to failure
<b>${MODELS.risk.timing.median_years_to_failure} years</b>; only ${(MODELS.risk.timing.pct_within_2yr*100).toFixed(0)}% fail inside two.</li>""",
     """<li><span class="pv f"><i></i>fitted</span> <b>Post-acquisition survival risk</b> &mdash;
competing-risk hazard on <b>${MODELS.risk.n_fit.toLocaleString()}</b> SBA 7(a) acquisition loans; open loans are censored and payoff
is a competing exit. Reported as the chance the loan is charged off within ${MODELS.risk.term_months/12} years (the term) and within
${MODELS.risk.horizon_months/12}, if ${MODELS.risk.conditions} conditions hold. Out-of-sample AUC <b>${MODELS.risk.cv_auc}</b> at 5 years, Brier ${MODELS.risk.cv_brier};
loan-level effects shrunk &times;${MODELS.risk.co.lp_shrink.toFixed(2)} to match how they held up out of time.
<b>${(MODELS.risk.aj_pooled.cif60*100).toFixed(1)}%</b> of acquisition loans are charged off within 5 years against
${(MODELS.risk.like_for_like.startup_or_new.cif60*100).toFixed(1)}% of startup and new-business loans over the same span &mdash;
buying an existing business is measurably safer than starting one. Charge-offs come late: the median is
<b>${(MODELS.risk.timing.median_months_given_chargeoff_by_96/12).toFixed(1)} years</b> among loans charged off within 8, and only ${(MODELS.risk.timing.share_by_24_of_96*100).toFixed(0)}% go inside two.</li>"""),
    ("""Including that field yields a fraudulent AUC of 0.957, so it is excluded. The vintage coefficient is
pinned to zero because its negative fitted value is a censoring artifact that would understate risk
on every live deal.</li>""",
     """Including that field yields a fraudulent AUC of 0.957, so it is excluded. Loans still open are censored
rather than dropped: a model of resolved loans sees only the early failures and early payoffs, and has no horizon.</li>"""),
    ("""${MODELS.value.n_fit.toLocaleString()} closed sales and ${MODELS.risk.n_fit.toLocaleString()} resolved
acquisitions; closing""",
     """${MODELS.value.n_fit.toLocaleString()} closed sales and ${MODELS.risk.n_fit.toLocaleString()} SBA
acquisition loans; closing"""),
    ('<div class="stat"><dt>Transactions fitted</dt><dd>32,554</dd></div>',
     '<div class="stat"><dt>Transactions fitted</dt><dd>%s</dd></div>' % format(CUR_MODELS['value']['n_fit'] + len(d), ',')),
    ('<div><div class="n" style="color:#d8ecff">32,554</div>',
     '<div><div class="n" style="color:#d8ecff">${(V.n_fit+R.n_fit).toLocaleString()}</div>'),
    ("""/* State default effects are empirical-Bayes deviations from the national rate, shrunk by
   n/(n+250), so a thin state collapses to the national number rather than inventing a
   signal. Only states with >=60 resolved acquisition loans are offered at all. */""",
     """/* State effects are Poisson-gamma empirical-Bayes multipliers on the charge-off hazard
   (observed over expected charge-offs, shrunk toward 1), so a thin state collapses to the
   national number rather than inventing a signal. */"""),
    ("""  /* label each state with what it does to THIS deal's default probability. The raw
     figure is a population deviation that the model applies in log-odds through a fitted
     coefficient, so printing it overstated the effect about eightfold. */""",
     """  /* label each state with what it does to THIS deal's 10-year charge-off probability (the
     headline): the state multiplier is applied to the charge-off hazard through fitRisk, so the
     label is the model's own difference, not the raw state deviation. */"""),
    ('var txt=STNAMES[k]+"  ("+(d>=0?"+":"\\u2212")+Math.abs(d).toFixed(2)+" pts default risk)";',
     'var txt=STNAMES[k]+"  ("+(d>=0?"+":"\\u2212")+Math.abs(d).toFixed(2)+" pts charge-off risk, 10 yr)";'),
]


def replace_member(src, anchor, key, newobj):
    """replace the JSON value of "key" inside the object literal that starts right after `anchor`."""
    a = src.index(anchor) + len(anchor)
    obj, end = json.JSONDecoder().raw_decode(src, a)
    k = src.index('"%s":' % key, a)
    assert k < end
    v0 = k + len('"%s":' % key)
    _, v1 = json.JSONDecoder().raw_decode(src, v0)
    return src[:v0] + json.dumps(newobj, separators=(',', ':')) + src[v1:]


patched = html
for old, new in PATCHES:
    assert patched.count(old) == 1, 'patch target not unique/missing: ' + old[:90]
    patched = patched.replace(old, new)
patched = replace_member(patched, 'const MODELS = ', 'risk', RISK)
patched = replace_member(patched, 'MODELS.fitted=', 'sba_rate', SBA_RATE)
PDIR = OUT + 'patched/'
if os.path.isdir(PDIR): shutil.rmtree(PDIR)
os.makedirs(PDIR + 'tests')
open(PDIR + 'index.html', 'w', encoding='utf-8').write(patched)
for fn in os.listdir(REPO + 'tests'):
    shutil.copy(REPO + 'tests/' + fn, PDIR + 'tests/' + fn)
json.dump(RISK, open(OUT + 'MODELS_risk_v3.json', 'w'), indent=1)
json.dump(SBA_RATE, open(OUT + 'MODELS_fitted_sba_rate.json', 'w'), indent=1)
open(OUT + 'fitRisk_v3.js', 'w').write(JS_FITRISK)
open(OUT + 'hero_tile_v3.js', 'w').write(JS_HERO)
diff = subprocess.run(['diff', '-u', REPO + 'index.html', PDIR + 'index.html'], capture_output=True, text=True).stdout
open(OUT + 'index.html.diff', 'w').write(diff)
for chk in ['R.coefficients', 'base_rate', 'full_dataset_base_rate', 'median_years_to_failure', 'size_band_rates', 'pct_within_2yr']:
    say('  leftover reference %-26s : %d' % (chk, patched.count(chk)))

# Python mirror of the JS, on the ROUNDED shipped tables, for pinned test values ----------------------------------
IND2NAICS = dict(re.findall(r'(\w+):"(\d\d)"', re.search(r'const IND2NAICS=\{(.*?)\};', html, re.S).group(1)))


def js_mirror(price, key, rate, jobs, franchise, st, sec=None):
    """fitRisk in Python on the shipped tables. sec=(co, pif) replaces the sector effects (e.g. (0, 0) = the average
    sector, or a book loan's own sector + 6-digit effect); jobs is ignored, as in the JS."""
    R, SR = RISK, SBA_RATE
    n2 = IND2NAICS.get(key, '81'); n6 = APP_N6.get(key)
    loan = min(max(R['loan_share'] * max(price, 1), R['loan_range'][0]), R['loan_range'][1])
    K = np.array([k[0] for k in SR['spread_knots']]); V = np.array([k[1] for k in SR['spread_knots']])
    r = rate if rate is not None else SR['prime'] + float(np.interp(min(max(math.log(max(price * .85, 1e4)), K[0]), K[-1]), K, V))
    spread = min(max(r - SR['prime'], R['spread_range'][0]), R['spread_range'][1])
    c0 = R['centers']
    x = {'lnamt': math.log(loan) - c0['ln_loan'], 'franchise': 1 if franchise else 0, 'spread': spread - c0['spread']}
    if sec is None:
        lc = R['industry_effects'].get(n2, 0) + (R['naics6_effects'].get(n6, 0) if n6 else 0); lp = R['pif']['sector'].get(n2, 0)
    else:
        lc, lp = sec
    lc += (R['state_effects'].get(st, 0) if st else 0)
    for k_, v_ in R['co']['coef'].items(): lc += v_ * x[k_]
    for k_, v_ in R['pif']['coef'].items(): lp += v_ * x[k_]
    E = R['age_edges']
    G = R['lgd']
    def sev(a):
        a = min(max(a, G['age_range'][0]), G['age_range'][1])
        return 1 / (1 + math.exp(-(G['b0'] + G['b_size'] * x['lnamt'] + G['b_age'] * (a / 12 - G['age_center_years']))))
    C = R['co']
    def run(H):
        S, F, EL = 1.0, 0.0, 0.0
        for j in range(len(E)):
            if E[j] >= H: break
            dt = min(E[j + 1] if j + 1 < len(E) else float('inf'), H) - E[j]
            ya = min(E[j], C['age_cap_months']) / 12 - C['age_center_years']
            u = lc + sum(v_ * x[k_] * ya for k_, v_ in C['age_coef'].items())
            lb = C['log_base'][j]
            l1 = 0.0 if lb is None else math.exp(lb + C['lp_shift'] + C['lp_shrink'] * u); l2 = math.exp(R['pif']['log_base'][j] + lp); L = l1 + l2
            if L > 0:
                inc = S * l1 / L * (1 - math.exp(-L * dt)); F += inc; EL += inc * sev(E[j] + dt / 2); S *= math.exp(-L * dt)
        return F, EL
    p5, _ = run(R['horizon_months']); p8, el8 = run(R['observed_months'])
    pT = p8 * R['tail_factor']
    el = el8 + (pT - p8) * sev((R['observed_months'] + R['term_months']) / 2)
    return {'p5': p5, 'p8': p8, 'pTerm': pT, 'lgd': el / pT, 'expLoss': el, 'rel': pT / R['base_cif']['term'],
            'sev24': sev(24), 'sev84': sev(84)}


PINS = []
for args in [(1.0e6, 'medical', None, 10, False, None), (3.0e5, 'rest', 10.5, 12, True, 'TX'), (5.0e6, 'home', None, 30, False, 'CA'),
             (4.0e7, 'ecom', 9.0, 60, False, 'NY'), (6.5e5 / 0.85, 'fit', None, 8, False, None), (1.5e5, 'auto', 12.0, 4, False, 'FL')]:
    m = js_mirror(*args)
    PINS.append({'args': list(args), **{k: m[k] for k in ['p5', 'p8', 'pTerm', 'lgd', 'expLoss', 'rel']}})
REFM = js_mirror(6.5e5 / 0.85, 'zzz', None, 8, False, None, sec=(0.0, 0.0))     # $650k note, average sector, no state
# the FY2024-26 book as fitRisk prices it, on the shipped (rounded) tables: every loan with its own size, sector + 6-digit
# effect, state and franchise flag. Written as a test fixture; its mean must reproduce base_cif (the denominator of rel).
_bk = d.iloc[recent]
_sk = sorted(set(_bk.g2))
_stk = sorted(set(_bk.state))
_n6v = pd.Series(_bk.n6.values).map(n6map).fillna(0).values
BOOK = {'note': 'FY2024-26 change-of-ownership 7(a) term loans in the hazard sample (SBA FOIA as of 2026-06-30): loan amount, sector index, '
                '6-digit log-RR x 1e4, state index, franchise flag; sec_co/sec_pif = fitted sector effects (pooled 2-digit groups)',
        'n': int(len(_bk)), 'loan': [int(round(v)) for v in _bk.GrossApproval.values], 'sec': [_sk.index(v) for v in _bk.g2.values],
        'n6': [int(round(1e4 * v)) for v in _n6v], 'st': [_stk.index(v) for v in _bk.state.values], 'fr': [int(v) for v in _bk.is_franchise.values],
        'sec_keys': _sk, 'sec_co': [R4(par(f_main, 'sec_' + k)) for k in _sk], 'sec_pif': [R4(par(f_pif, 'sec_' + k)) for k in _sk], 'st_keys': _stk}
_bm = [js_mirror(BOOK['loan'][i] / RISK['loan_share'], 'zzz', None, None, BOOK['fr'][i] == 1, BOOK['st_keys'][BOOK['st'][i]],
                 sec=(BOOK['sec_co'][BOOK['sec'][i]] + BOOK['n6'][i] / 1e4, BOOK['sec_pif'][BOOK['sec'][i]])) for i in range(BOOK['n'])]
BOOK_CHECK = {'mean_p5': float(np.mean([m['p5'] for m in _bm])), 'mean_p8': float(np.mean([m['p8'] for m in _bm])), 'mean_rel': float(np.mean([m['rel'] for m in _bm]))}
BOOK_CHECK.update({'p5_over_h60': BOOK_CHECK['mean_p5'] / RISK['base_cif']['h60'], 'p8_over_h96': BOOK_CHECK['mean_p8'] / RISK['base_cif']['h96']})
say('book check (shipped tables, Python mirror of fitRisk):', {k: round(v, 5) for k, v in BOOK_CHECK.items()})
del _bm, _bk
RISK['lgd']['display'] = {'ref_loan_usd': 650000, 'sev_at_24m': R4(REFM['sev24']), 'sev_at_84m': R4(REFM['sev84']),
                          'term_weighted': R4(REFM['lgd'])}
# re-write the shipped JSON into the patched copy with the display block
patched = replace_member(patched, 'const MODELS = ', 'risk', RISK)
open(PDIR + 'index.html', 'w', encoding='utf-8').write(patched)
json.dump(RISK, open(OUT + 'MODELS_risk_v3.json', 'w'), indent=1)
diff = subprocess.run(['diff', '-u', REPO + 'index.html', PDIR + 'index.html'], capture_output=True, text=True).stdout
open(OUT + 'index.html.diff', 'w').write(diff)
say('reference loan severity: %.4f at 24 months, %.4f at 84 months, %.4f timing-weighted over the term' % (REFM['sev24'], REFM['sev84'], REFM['lgd']))
say('pins', json.dumps(PINS))

TEST_JS = r'''/* Invariants for the SBA risk refresh (fit/sba_risk_refresh.py). Run: node tests/sba_risk_refresh.test.js */
const A=require("./load.js"), fs=require("fs"), path=require("path");
const HTML=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
let pass=0,fail=0; const ok=(c,m)=>{ if(c) pass++; else { fail++; console.log("FAIL:",m); } };
const R=A.MODELS.risk, F=A.MODELS.fitted, PR=F.sba_rate.prime;
const PINS=__PINS__;
/* the average sector: fitRisk with every sector table emptied ("zzz" maps to 81, which then carries no effect) */
const avgSector=fn=>{ const a=R.industry_effects,b=R.pif.sector; R.industry_effects={}; R.pif.sector={};
  try{ return fn(); } finally { R.industry_effects=a; R.pif.sector=b; } };
/* 1. the console reproduces the fitted model exactly (Python mirror on the shipped, rounded tables) */
for(const c of PINS){ const r=A.fitRisk(...c.args);
  for(const k of ["p5","p8","pTerm","lgd","expLoss","rel"]) ok(Math.abs(r[k]-c[k])<=1e-9*Math.max(1,Math.abs(c[k])),`pin ${JSON.stringify(c.args)} ${k}: ${r[k]} vs ${c[k]}`); }
/* 2. horizons: 0 < p5 < p8 < pTerm < 1, headline is the term, and the term uses the stated tail factor */
for(const k of Object.keys(A.IND)) for(const v of [2e5,1e6,4e6]){ const r=A.fitRisk(v,k,null,10,false,null);
  ok(r.p5>0&&r.p5<r.p8&&r.p8<r.pTerm&&r.pTerm<0.5,`${k} ${v}: horizons ordered ${r.p5} ${r.p8} ${r.pTerm}`);
  ok(r.p===r.pTerm&&Math.abs(r.pTerm-r.p8*R.tail_factor)<1e-12,`${k}: headline is the term`); }
ok(R.horizon_months===60&&R.observed_months===96&&R.term_months===120,"horizons are 5 / 8 / 10 years");
/* the tail factor is a labelled transfer judgment: inside the loan-band range of mature vintages, with an SE that covers it */
ok(R.tail_factor>=1.1&&R.tail_factor<=1.3,"tail factor inside the 1.1-1.3 range mature vintages show");
ok(R.tail_factor_se>=0.07,"tail factor SE covers the loan-band range (>= 0.07)");
ok(R.tail_by_band["<150k"].ratio<R.tail_factor&&R.tail_factor<R.tail_by_band[">=1.5M"].ratio,"tail factor between the small- and large-loan ratios");
/* 3. larger loans are no riskier at the table rate over 5 years; flat beyond the 7(a) cap */
for(const k of Object.keys(A.IND)){ let prev=1;
  for(const v of [5e4,1e5,3e5,1e6,3e6,5.8e6]){ const p=A.fitRisk(v,k,null,10,false,null).p5; ok(p<=prev+1e-12,`${k}: 5-year risk falls with size at ${v}`); prev=p; }
  ok(Math.abs(A.fitRisk(6e6,k,null,10,false,null).p5-A.fitRisk(6e8,k,null,10,false,null).p5)<1e-12,`${k}: flat above the $5M loan cap`); }
/* 3b. the size effect fades with time on book: the large/small ratio is closer to 1 over 8 years than over 5 */
{ const s=A.fitRisk(2e5,"prof",null,10,false,null), b=A.fitRisk(5e6,"prof",null,10,false,null);
  ok(R.co.age_coef.lnamt>0&&R.co.coef.lnamt<0,"size lowers risk, less so with time on book");
  ok(b.p8/s.p8>b.p5/s.p5,"size gradient flatter at 8 years than at 5"); }
/* 4. a higher spread raises risk up to prime+3, and is flat above (the fitted hinge) */
{ let prev=0; for(const s of [0,1,2,2.5,3]){ const p=A.fitRisk(1e6,"rest",PR+s,10,false,null).p5; ok(p>prev,`spread ${s}: risk rises`); prev=p; }
  ok(A.fitRisk(1e6,"rest",PR+3,10,false,null).p5===A.fitRisk(1e6,"rest",PR+6,10,false,null).p5,"flat above prime+3"); }
/* 4b. risk depends on the spread, not the rate level: moving prime and the rate together changes nothing */
{ const p0=A.fitRisk(9e5,"auto",PR+2,6,false,null).p; F.sba_rate.prime=PR+1.5; const p1=A.fitRisk(9e5,"auto",PR+3.5,6,false,null).p; F.sba_rate.prime=PR;
  ok(Math.abs(p0-p1)<1e-15,"rate level not applied (spread only)"); }
/* 5. rate omitted = rate from sbaRate */
ok(A.fitRisk(8e5,"auto",undefined,6,false,null).p5===A.fitRisk(8e5,"auto",A.sbaRate(8e5),6,false,null).p5,"default rate is sbaRate");
/* 6. population anchors: base and observed 5-year rate are the same order; reference loan near the base */
ok(R.base_cif.h60>0.01&&R.base_cif.h60<0.035,"population 5-year charge-off between 1% and 3.5%");
ok(Math.abs(R.base_cif.h60-R.aj_pooled.cif60)<3*R.aj_pooled.cif60_se+0.003,"model population average near the Aalen-Johansen 5-year rate");
ok(Math.abs(R.base_cif.term-R.base_cif.h96*R.tail_factor)<1e-3,"population term = 8-year x tail factor");
ok(R.base_cif.spec_range.h96[0]<=R.base_cif.h96+1e-4&&R.base_cif.h96<=R.base_cif.spec_range.h96[1]+1e-4,"shipped 8-year level inside its specification range");
/* the stated level uncertainty includes the reference period: 2025-26 ran below 2023-24, and the range brackets the shipped level */
ok(R.base_cif.conditions.ratio<1&&R.base_cif.conditions_range.h96[0]<R.base_cif.h96&&R.base_cif.h96<R.base_cif.conditions_range.h96[1],"reference-period range brackets the shipped 8-year level");
ok(R.base_cif.level_range.h96[0]<=Math.min(R.base_cif.spec_range.h96[0],R.base_cif.conditions_range.h96[0])+1e-9&&R.base_cif.level_range.h96[1]>=Math.max(R.base_cif.spec_range.h96[1],R.base_cif.conditions_range.h96[1])-1e-9,"level range = specifications and reference periods");
ok((R.base_cif.level_range.h96[1]-R.base_cif.level_range.h96[0])/R.base_cif.h96>0.2,"stated level range is not the narrow specification range alone");
/* the reference loan ($650k note, table rate, average sector, no state) sits near the average loan */
{ const r=avgSector(()=>A.fitRisk(6.5e5/0.85,"zzz",null,8,false,null)); ok(r.rel>0.8&&r.rel<1.2,`reference loan rel ${r.rel}`);
  ok(Math.abs(r.rel-r.pTerm/R.base_cif.term)<1e-12,"rel = pTerm / base_cif.term"); }
/* 6d. base_cif is what fitRisk prices: fitRisk applied to every FY2024-26 acquisition loan (its own size, sector and 6-digit
       effect, state and franchise flag; table rate, variable note) averages base_cif.h60 / h96 within 2%, and rel averages 1 */
{ const BK=JSON.parse(fs.readFileSync(path.join(__dirname,"sba_book_fy2024_26.json"),"utf8"));
  const ie=R.industry_effects, ps=R.pif.sector; let s5=0,s8=0,sr=0; const n=BK.loan.length;
  try{ for(let i=0;i<n;i++){ R.industry_effects={"81":BK.sec_co[BK.sec[i]]+BK.n6[i]/1e4}; R.pif.sector={"81":BK.sec_pif[BK.sec[i]]};
      const r=A.fitRisk(BK.loan[i]/R.loan_share,"zzz",null,null,BK.fr[i]===1,BK.st_keys[BK.st[i]]); s5+=r.p5; s8+=r.p8; sr+=r.rel; } }
  finally { R.industry_effects=ie; R.pif.sector=ps; }
  ok(n===BK.n&&n>10000,`book fixture has ${n} loans`);
  ok(Math.abs(s5/n/R.base_cif.h60-1)<0.02,`console-priced book 5-yr mean ${s5/n} vs base_cif.h60 ${R.base_cif.h60}`);
  ok(Math.abs(s8/n/R.base_cif.h96-1)<0.02,`console-priced book 8-yr mean ${s8/n} vs base_cif.h96 ${R.base_cif.h96}`);
  ok(Math.abs(sr/n-1)<0.02,`rel averages 1 over the book: ${sr/n}`); }
/* 6b. by loan band: the fitted model (own spreads and rate type, realised calendar) matches the observed 5-year rate within
       2 SE; the console (table spreads, variable note, current conditions, shrunk) within 1.5 SE and 0.90-1.25x */
for(const b of Object.keys(R.size_band_cif)){ const B=R.size_band_cif[b];
  ok(B.cif60>0.003&&B.cif60<0.06,`band ${b} observed 5-yr rate`);
  ok(Math.abs(B.model60_insample-B.cif60)<=2*B.cif60_se,`band ${b}: fitted model (own spreads, realised calendar) ${B.model60_insample} vs observed ${B.cif60} (SE ${B.cif60_se})`);
  ok(Math.abs(B.model60_table_spread-B.cif60)<=1.5*B.cif60_se&&B.model60_table_spread/B.cif60>0.90&&B.model60_table_spread/B.cif60<1.25,
     `band ${b}: console at table spreads ${B.model60_table_spread} vs observed ${B.cif60}`);
  const r=avgSector(()=>A.fitRisk(B.loan_median/R.loan_share,"zzz",null,null,false,null));
  ok(Math.abs(r.p5-B.cif60)<=3*B.cif60_se+0.004,`band ${b}: fitRisk at the band median (average sector) ${r.p5} vs observed ${B.cif60}`); }
/* 6c. multiples stay in a believable range for realistic console inputs (table rate, any industry, $200k-$10M, 2-50 staff) */
for(const k of Object.keys(A.IND)) for(const v of [2e5,6e5,2e6,1e7]) for(const j of [2,8,50]){ const r=A.fitRisk(v,k,null,j,false,null);
  ok(r.rel>0.2&&r.rel<3.5,`${k} ${v} ${j} staff: rel ${r.rel}`); }
/* 6e. staffing does not enter: SBA's jobs count is not the console's head count */
for(const k of ["staff","rest","medical"]) ok(A.fitRisk(2e6,k,null,2,false,"TX").p===A.fitRisk(2e6,k,null,90,false,"TX").p,`${k}: risk does not move with staffing`);
ok(R.co.coef.lnjobs===undefined&&R.pif.coef.lnjobs===undefined&&R.staffing.applied===false,"no staffing coefficient shipped");
/* 7. effects: unknown state/industry = 0; shrunk effects bounded; out-of-time shrink in (0,1] */
ok(A.fitRisk(1e6,"medical",null,10,false,"ZZ").p5===A.fitRisk(1e6,"medical",null,10,false,null).p5,"unknown state is national");
for(const k in R.state_effects) ok(Math.abs(R.state_effects[k])<0.6,`state ${k} bounded`);
for(const k in R.naics6_effects) ok(Math.abs(R.naics6_effects[k])<0.6,`naics6 ${k} bounded`);
for(const k of Object.keys(A.IND)){ ok(R.industry_effects[A.IND2NAICS[k]]!==undefined,`${k} has a charge-off sector effect`);
  ok(R.pif.sector[A.IND2NAICS[k]]!==undefined,`${k} has a payoff sector effect`); }
ok(R.co.log_base[0]===null,"no charge-off in the first six months on book");
ok(R.co.lp_shrink>0.5&&R.co.lp_shrink<=1,"out-of-time shrink in (0.5, 1]");
/* 7b. shipped SEs are clustered (lender / two-way), never below the Hessian SEs */
for(const k in R.co.se) ok(R.co.se[k]>=R.co.se_hessian[k]-1e-4,`co.se ${k} clustered >= Hessian`);
ok(R.co.se.lnamt>=1.2*R.co.se_hessian.lnamt,"size SE inflated by clustering");
/* 8. severity: timing-weighted mean LGD in a sane band, falling with age at charge-off and not rising with size;
      expected loss below the term probability */
ok(R.lgd.b_age<0,"severity falls the later a loan fails (amortisation)");
{ let prev=1; for(const v of [3e4,2e5,1e6,3e6,6e6]){ const r=A.fitRisk(v,"prof",null,10,false,null);
  ok(r.lgd>0.4&&r.lgd<0.95,`lgd at ${v}: ${r.lgd}`);
  if(R.lgd.b_size<=0) ok(r.lgd<=prev+0.01,`lgd does not rise with size at ${v}`); prev=r.lgd;
  ok(r.expLoss>0&&r.expLoss<r.pTerm&&Math.abs(r.expLoss-r.pTerm*r.lgd)<1e-12,"expected loss = term probability x mean severity"); } }
/* 9. rate table: H.15 prime and date; spreads non-increasing in size and inside SBA's maximum; knot uncertainty >= 0.05 */
ok(PR===7.00&&F.sba_rate.prime_asof==="2026-09-17","prime 7.00% since 2026-09-17 (H.15)");
{ let prev=99; for(const v of [5e4,2e5,6e5,1.5e6,4e6,1e7]){ const s=A.sbaRate(v)-PR; ok(s<=prev+1e-12&&s>=1.3&&s<=2.6,`spread at ${v}: ${s}`); prev=s; } }
ok(F.sba_rate.spread_knots_se.every(v=>v>=0.0)&&Math.max(...F.sba_rate.spread_knots_se)>=0.05,"knot uncertainty reflects sample choice, not the heaped bootstrap");
ok(/cancelled/.test(F.sba_rate.source),"rate source says the sample includes cancelled and undisbursed approvals");
/* 10. the full model carries it through; headline risk never rises with revenue at a fixed margin (within 1%), and is flat once
       the note hits the $5M cap */
{ const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
  const r=A.model(EX);
  ok(isFinite(r.risk.p)&&r.risk.p>0&&r.risk.p<0.3&&r.risk.p5<r.risk.p,"model() risk finite and ordered");
  for(const k of Object.keys(A.IND)){ let prev=Infinity, bad=0;
    for(let i=0;i<=48;i++){ const rev=3e5*Math.pow(4e7/3e5,i/48); const o=A.model({...EX,ind:k,rev,ern:rev*1.45/6,ask:rev*.54});
      if(o.risk.p>prev*1.01) bad++; prev=o.risk.p; }
    ok(bad===0,`${k}: headline risk rises with revenue in ${bad} steps`); } }
/* 11. labels: the 10-year figure is conditional on current conditions; checks the Data tab must show; state label */
ok(R.conditions==="2023-26","conditions label");
{ const i=HTML.indexOf('const e=$("o_risk")'), j=HTML.indexOf('e.innerHTML=h;})();',i), H=HTML.slice(i,j);
  ok(i>0&&j>i&&/conditions hold/.test(H),"hero says 'if 2023-26 conditions hold'");
  ok(!/-yr term/.test(H)&&/charged off within /.test(H),"hero says 'within 10 yrs', not 'the 10-yr term'");
  ok(/conditions_range/.test(H),"hero tooltip shows the reference-period range"); }
for(const f of ["vintage_oe","cal_holdout_slope","lp_shrink","spec_range","conditions_range","level_range","through_cycle","rate_level.uplift_range","tail_by_band","real_estate","spread_channel","staffing"])
  ok(HTML.indexOf("R."+f)>=0||HTML.indexOf("R.validation."+f)>=0||HTML.indexOf("R.co."+f)>=0||HTML.indexOf("R.base_cif."+f)>=0,`Data tab shows ${f}`);
ok(HTML.indexOf("pts default risk")<0&&HTML.indexOf("pts charge-off risk, 10 yr")>=0,"state dropdown labels the 10-year charge-off risk");
console.log(`sba_risk_refresh: ${pass} passed, ${fail} failed`); if(fail) process.exitCode=1;
'''
TEST_JS = TEST_JS.replace('__PINS__', json.dumps(PINS))
open(PDIR + 'tests/sba_risk_refresh.test.js', 'w').write(TEST_JS)
open(OUT + 'sba_risk_refresh.test.js', 'w').write(TEST_JS)
for _dst in (PDIR + 'tests/', OUT):
    json.dump(BOOK, open(_dst + 'sba_book_fy2024_26.json', 'w'), separators=(',', ':'))
TESTRES = {}
for t in ['model.test.js', 'fuzz.test.js', 'sba_risk_refresh.test.js']:
    pr_ = subprocess.run(['node', PDIR + 'tests/' + t], capture_output=True, text=True, timeout=900)
    tail_out = (pr_.stdout + pr_.stderr).strip().splitlines()
    TESTRES[t] = {'exit': pr_.returncode, 'tail': tail_out[-6:]}
    say('  test', t, 'exit', pr_.returncode, '|', ' / '.join(tail_out[-4:]))

# before / after on the example business and a few deals ------------------------------------------------------------
NODE_CMP = r'''
const fs=require("fs"),vm=require("vm");
function load(p){ let html=fs.readFileSync(p,"utf8"); let src=html.slice(html.lastIndexOf("<script>")+8);
  src=src.slice(0,src.indexOf("/* ============ bar helpers"));
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN}; vm.createContext(ctx);
  vm.runInContext(src+";this.API={model,fitRisk,sbaRate,MODELS};",ctx); return ctx.API; }
const O=load(process.argv[2]), N=load(process.argv[3]);
const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
const rows=[];
for(const [ind,rev,ern] of [["medical",6e6,1.45e6],["rest",1.2e6,2.2e5],["home",3e6,6e5],["auto",8e5,1.8e5],["fit",2e6,4.5e5],["msp",1.5e7,3e6]]){
  const s={...EX,ind,rev,ern,ask:ern*3}; const o=O.model(s), n=N.model(s);
  rows.push({ind,rev,ern,V_old:o.V,V_new:n.V,rate_old:o.rate,rate_new:n.rate,jobs_console:n.jobs,loan_new:n.risk.loan,p_old:o.risk.p,rel_old:o.risk.rel,lgd_old:o.risk.lgd,el_old:o.risk.expLoss,
             p5_new:n.risk.p5,pTerm_new:n.risk.pTerm,rel_new:n.risk.rel,lgd_new:n.risk.lgd,el_new:n.risk.expLoss,score_same:o.score===n.score&&o.PC===n.PC&&o.V===n.V}); }
/* what moved the headline: the new model with pieces switched off, on the example business and a small deal */
const R=N.MODELS.risk, C=R.co, keep={sh:C.lp_shrink, sf:C.lp_shift, ag:C.age_coef.lnamt, tf:R.tail_factor};
const dec=[];
for(const [ind,rev,ern] of [["medical",6e6,1.45e6],["rest",1.2e6,2.2e5]]){ const s={...EX,ind,rev,ern,ask:ern*3}; const row={ind};
  row.shipped=N.model(s).risk.pTerm;
  R.tail_factor=1.1745; row.old_tail=N.model(s).risk.pTerm; R.tail_factor=keep.tf;
  C.lp_shrink=1; C.lp_shift=0; row.no_shrink=N.model(s).risk.pTerm;
  C.age_coef.lnamt=0; row.no_shrink_no_size_age=N.model(s).risk.pTerm;
  C.lp_shrink=keep.sh; C.lp_shift=keep.sf; C.age_coef.lnamt=keep.ag; row.old=O.model(s).risk.p; dec.push(row); }
console.log(JSON.stringify(rows)); console.log(JSON.stringify(dec));
'''
open(OUT + 'before_after.js', 'w').write(NODE_CMP)
ba = subprocess.run(['node', OUT + 'before_after.js', REPO + 'index.html', PDIR + 'index.html'], capture_output=True, text=True, timeout=300)
BA = json.loads(ba.stdout.strip().splitlines()[-2]) if ba.returncode == 0 else []
BA_DECOMP = json.loads(ba.stdout.strip().splitlines()[-1]) if ba.returncode == 0 else []
say('headline decomposition (pTerm):', BA_DECOMP)
pd.DataFrame(BA).to_csv(OUT + 'before_after.csv', index=False)
say('before/after\n' + pd.DataFrame(BA).round(4).to_string() if BA else 'before/after failed: ' + ba.stderr[-500:])
FIT['implementation'] = {'pins': PINS, 'tests': TESTRES, 'before_after': BA, 'headline_decomposition': BA_DECOMP}
json.dump(FIT, open(OUT + 'fits.json', 'w'), indent=1, default=float)
say('section 6 done (%.0fs)' % (time.time() - T0))

# 6b. the patched page in headless Chromium: existing browser suites + Data tab and hero tile render ------------------
BROWSER_JS = r'''
const path=require("path");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{
  const b=await pw.chromium.launch(); const out={errors:[]};
  for(const width of [1440,390]){
    const p=await b.newPage({viewport:{width,height:900}});
    p.on("pageerror",e=>out.errors.push(`[${width}] ${e.message}`));
    p.on("console",m=>{ if(m.type()==="error") out.errors.push(`[${width}] console: ${m.text()}`); });
    await p.goto("file://"+process.argv[2]);
    await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000});
    await p.evaluate(()=>new Promise(r=>setTimeout(r,300)));
    const hero=await p.evaluate(()=>document.getElementById("o_risk").innerText);
    const conf=await p.evaluate(()=>document.getElementById("o_conf").textContent);
    await p.evaluate(()=>{ if(!document.getElementById("dataviews").innerHTML) renderData(); });
    const dv=await p.evaluate(()=>{ const t=document.getElementById("dataviews").innerText;
      const i=t.indexOf("Model V"); return {bad:(t.match(/NaN|Infinity|undefined/g)||[]).length, modelV:t.slice(i,i+2600),
        lgd:(t.match(/When these loans fail[^\n]*/)||[""])[0], rate:(t.match(/SBA loan rate in the survival-risk model[^\n]*/)||[""])[0],
        methods:(t.match(/Post-acquisition survival risk[^\n]*\n?[^\n]*/)||[""])[0]}; });
    const foot=await p.evaluate(()=>document.getElementById("foot").innerText);
    out["w"+width]={hero,conf,data:dv,foot};
    if(width===1440){ await p.screenshot({path:process.argv[3]+"hero.png",clip:{x:0,y:0,width:1440,height:900}}); }
  }
  await b.close(); console.log(JSON.stringify(out));
})().catch(e=>{ console.log(JSON.stringify({fatal:String(e)})); process.exit(1); });
'''
open(OUT + 'browser_check.js', 'w').write(BROWSER_JS)
BROWSER = {}
try:
    bc = subprocess.run(['node', OUT + 'browser_check.js', PDIR + 'index.html', OUT], capture_output=True, text=True, timeout=600)
    BROWSER['data_tab_and_hero'] = json.loads(bc.stdout.strip().splitlines()[-1])
    say('browser: errors %s; hero (1440): %s' % (BROWSER['data_tab_and_hero'].get('errors'),
                                                  BROWSER['data_tab_and_hero'].get('w1440', {}).get('hero', '').replace('\n', ' | ')))
    say('browser: data-tab NaN/undefined count %s' % BROWSER['data_tab_and_hero'].get('w1440', {}).get('data', {}).get('bad'))
except Exception as e:
    BROWSER['data_tab_and_hero'] = {'fatal': str(e)}
    say('browser check failed', e)
for t in ['browser.sweep.js', 'browser.inputs.js']:
    # these drive a real browser with timing-sensitive clicks; a failure is retried once and both attempts are reported
    att = []
    for attempt in range(2):
        try:
            r_ = subprocess.run(['node', PDIR + 'tests/' + t], capture_output=True, text=True, timeout=1800)
            lines = (r_.stdout + r_.stderr).strip().splitlines()
            att.append({'exit': r_.returncode, 'tail': lines[-4:], 'fails': [l for l in lines if 'FAIL' in l or 'error' in l.lower()][:5]})
        except Exception as e:
            att.append({'exit': None, 'tail': [str(e)], 'fails': [str(e)]})
        if att[-1]['exit'] == 0: break
    BROWSER[t] = {'exit': att[-1]['exit'], 'attempts': att, 'tail': att[-1]['tail']}
    say('  browser test', t, json.dumps(BROWSER[t])[:600])


def browser_summary(t):
    b_ = BROWSER.get(t, {}); at = b_.get('attempts', [])
    if not at: return '%s not run' % t
    if len(at) == 1: return '%s exit %s (%s)' % (t, at[0]['exit'], (at[0]['tail'] or [''])[-1].strip())
    return '%s exit %s on retry; first attempt exit %s (%s)' % (t, at[-1]['exit'], at[0]['exit'], '; '.join(x.strip() for x in at[0]['fails']) or 'see fits.json')
FIT['implementation']['browser'] = BROWSER
json.dump(FIT, open(OUT + 'fits.json', 'w'), indent=1, default=float)

# ----------------------------------------------------------------------------------------------------------------
# 7. RESULT.json (the structured return)
# ----------------------------------------------------------------------------------------------------------------
pc_ = lambda v, dd=2: ('%.' + str(dd) + 'f%%') % (100 * v)
f3 = lambda v: '%.3f' % v
cot = tco.set_index('term'); pft = tpf.set_index('term')
def cse(nm, t=None):
    t = cot if t is None else t
    return ('%.3f (shipped SE %.3f = largest of Hessian %.3f, lender-clustered %.3f and two-way lender x calendar-quarter %.3f; loan-clustered %.3f)'
            % (t.loc[nm, 'est'], t.loc[nm, 'se_shipped'], t.loc[nm, 'se'], t.loc[nm, 'se_cluster_lender'], t.loc[nm, 'se_cluster_twoway'], t.loc[nm, 'se_cluster_loan']))
cvf, cvn = v60['new_full'], v60['null_age_calendar_only']
VALTXT = ('5-fold CV by loan (sector variance re-estimated and 6-digit/state maps refitted in every fold; functional forms chosen on the full sample), '
          'charge-off within 60 months on the %s loans with >=60 months of follow-up (%d events): AUC %.3f (boot SE %.3f) vs %.3f '
          'for age+calendar only and %.3f for the current resolved-only logistic (fitted in-sample on these loans); Brier %.5f vs %.5f null; '
          'observed/predicted %.3f, calibration slope %.2f. Vintage holdout (train FY2018-21, test FY2022-24 loans over their own window, %d events): '
          'AUC %.3f vs null %.3f and current %.3f; observed/predicted %.2f (under-predicted), slope %.2f (SE %.2f). Calendar holdout (fit on exposure before 2024-07-01, forecast '
          'charge-offs 2024-07..2026-06 of the %s loans open then, %d events): AUC %.3f vs null %.3f and current %.3f; observed/predicted %.2f (over-predicted), slope %.2f (SE %.2f). '
          'Slope of held-out charge-offs on the loan-level log hazard (age baseline free): in-period CV %.2f (SE %.2f), vintage %.2f (SE %.2f), calendar %.2f (SE %.2f): '
          'the out-of-time pair sets the shipped shrink. In-sample observed/expected by loan band x age window: Pearson chi2 over 15 cells %.1f (vs %.1f with a proportional size effect).'
          % (format(cvf['n'], ','), cvf['events'], cvf['auc'], cvf['auc_se_boot'], cvn['auc'], v60['current_model_auc'], cvf['brier'], cvn['brier'],
             cvf['O_over_E'], cvf['calib_slope'], vh['new_full']['events'], vh['new_full']['auc'], vh['null_age_calendar_only']['auc'],
             vh['current_model_auc'], vh['new_full']['O_over_E'], vh['new_full']['calib_slope'], vh['new_full']['calib_slope_se'],
             format(ch['new_full']['n'], ','), ch['new_full']['events'], ch['new_full']['auc'],
             ch['null_age_only']['auc'], ch['current_model_auc'], ch['new_full']['O_over_E'], ch['new_full']['calib_slope'], ch['new_full']['calib_slope_se'],
             VAL['cv5_slope_loan_level']['pooled'], VAL['cv5_slope_loan_level']['pooled_se'], SLOPE_V['gamma'], SLOPE_V['se'], SLOPE_C['gamma'], SLOPE_C['se'],
             BAND_AGE_CHI2['size effect fading to 72 months (shipped)'], BAND_AGE_CHI2['proportional size effect']))
HAZ_METHOD = ('cause-specific piecewise-exponential (Poisson, exact exposure) hazards by months on book in 3-month pieces, baseline constant within '
              '6-month bands to 60 months then 12-month bands, open after 84; charge-off and paid-in-full fitted separately (PIF = competing exit), '
              'EXEMPT (open) loans right-censored at 2026-06-30; ln(loan) effect varies linearly with years on book to 6 years; cumulative incidence from the two hazards; '
              'SEs: sandwich clustered by lender (%d) and two-way lender x calendar quarter (%d quarters); the largest of those and the Hessian SE is shipped; derived probabilities by '
              'simulation (2,000 draws) from those covariances plus the out-of-time shrink factor' % (N_CLUST['n_lender'], N_CLUST['n_quarter']))
st_sorted = st_keep.sort_values('log_rr')
salt = spq['alt_samples']
lg = LENDER_FE['core_with_fe']
PARAMS = [
 {'param': 'MODELS.fitted.sba_rate.prime / prime_asof', 'current_value': '6.75 since 2025-12-11',
  'fitted_value': '%.2f since %s' % (PRIME_NOW, PRIME_SINCE), 'se': '0 (administered rate, published)', 'n': 'Fed H.15 daily series to %s' % PRIME_LAST_OBS,
  'method': 'last change in H.15 RIFSPBLP_N.B (bank prime loan rate)', 'validation': 'n/a: a published administered rate; last changes %s' % FIT['prime']['recent_changes'][-4:],
  'recommended_value': 'prime: %.2f, prime_asof: "%s"' % (PRIME_NOW, PRIME_SINCE)},
 {'param': 'MODELS.fitted.sba_rate.spread_knots (variable-rate spread over prime by ln loan)',
  'current_value': '[[ln 100k,2.00],[ln 750k,2.00],[ln 1.5M,1.75],[ln 3.5M,1.50]] from 4,812 FY2023 loans',
  'fitted_value': ', '.join('$%s: %.2f' % (('%gk' % (k / 1e3)) if k < 1e6 else ('%gM' % (k / 1e6)), v) for k, v in zip(SP_KNOTS_USD, spq['values'])),
  'se': ('knot uncertainty %s pp = the largest of the bootstrap SE (%s; understated because %.0f%% of rates sit at one value and medians stick to mass points), '
         'a 0.05 pp floor for that heaping, and the range across samples: disbursed only (n %s) %s; FY2025 only %s; FY2026 only %s; FY2018-26 (n %s) %s'
         % (', '.join('%.3f' % v for v in spq['unc']), ', '.join('%.3f' % v for v in spq['se']),
            100 * float(sp[(sp.ApprovalFY >= 2025) & (sp.FixedorVariableInterestInd == 'V')].spread_over_prime.round(2).value_counts(normalize=True).iloc[0]),
            format(salt['disbursed_only']['n'], ','), '/'.join('%.2f' % v for v in salt['disbursed_only']['values']),
            '/'.join('%.2f' % v for v in salt['FY2025_only']['values']), '/'.join('%.2f' % v for v in salt['FY2026_only']['values']),
            format(salt['FY2018_26']['n'], ','), '/'.join('%.2f' % v for v in salt['FY2018_26']['values']))),
  'n': ('%s variable-rate change-of-ownership term loans approved FY2025-26, including %d cancelled and %d approved but undisbursed (the rate offered at approval); '
        'fixed-rate: %s, reported apart' % (format(spq['n'], ','), SBA_RATE['n_cancelled'], SBA_RATE['n_undisbursed'], format(spread_res['F']['n'], ','))),
  'method': 'median regression on a piecewise-linear (tent) basis in ln(loan), knots $100k/$300k/$600k/$1.2M/$2.5M/$4.5M, then pool-adjacent-violators to make it non-increasing; spread = InitialInterestRate - the prime in effect on the first business day of the approval month (H.15), the base SBA rules peg variable 7(a) rates to: 13 CFR 120.214(c) "The prime rate will be that which is in effect on the first business day of the month"; SOP 50 10 8 Sec. B Ch. 1 Para. B.4.a.v as amended by PN 5000-875051 (eff. 2026-03-01). Earlier fits used the prime on the approval date, which mis-measured %.1f%% of term loans by 0.25-1.5 pp (loans approved after a mid-month prime change)' % (100 * PRIME_RULE['share_changed_term_loans']),
  'validation': ('temporal: fitted on FY2025, predicting FY2026 loans (n=%s): MAE %.3f pp vs %.3f for the current FY2023 knots (bias %+.2f pp%s) and %.3f for a flat median; 5-fold CV MAE %.3f vs %.3f current. %.1f%% of loans exceed the SBA maximum spread for their size (full SOP 50 10 schedule: 6.5/6.0/4.5/3.0 pp). '
                 'Reference date checked on the data: in the %d months with a mid-month prime change (FY2018-26, %s variable loans approved after the change), the post-vs-pre-change gap in mean spread carries %.2f of the prime move under the month-start rule vs %.2f with the approval-date prime (mean |gap| %.2f vs %.2f pp), so lenders price off the month-start prime. '
                 'Knots with the approval-date prime (previous fit, same sample rule): %s; MAE on the holdout is not comparable across the two definitions.')
                % (format(spread_val['holdout_FY2026_n'], ','), spread_val['mae_new_fit_on_FY2025'], spread_val['mae_current_FY2023_knots'], spread_val['bias_current_knots_pp'],
                   ': spreads rose' if spread_val['bias_current_knots_pp'] > 0.02 else (': spreads fell' if spread_val['bias_current_knots_pp'] < -0.02 else ''),
                   spread_val['mae_flat_FY2025_median'], spread_val['cv5_mae_new'], spread_val['cv5_mae_current_knots'], 100 * frac_above_cap,
                   PRIME_RULE['midmonth_check']['months'], format(PRIME_RULE['midmonth_check']['loans_after_change'], ','),
                   PRIME_RULE['midmonth_check']['slope_post_minus_pre_on_dprime_month_rule'], PRIME_RULE['midmonth_check']['slope_post_minus_pre_on_dprime_approval_date'],
                   PRIME_RULE['midmonth_check']['mean_abs_gap_month_rule'], PRIME_RULE['midmonth_check']['mean_abs_gap_approval_date'],
                   '/'.join('%.2f' % v for v in PRIME_RULE['knots_approval_date_prime'])),
  'recommended_value': json.dumps(SBA_RATE['spread_knots']) + '; spread_knots_se ' + json.dumps(SBA_RATE['spread_knots_se']) + ' (sample-choice uncertainty); source string says "including cancelled and undisbursed approvals"'},
 {'param': 'fixed-rate spread over prime (report only; not used)', 'current_value': 'not modelled',
  'fitted_value': ', '.join('%.2f' % v for v in spread_res['F']['values']) + ' at the same knots', 'se': ', '.join('%.3f' % v for v in spread_res['F']['unc']) + ' (same rule as variable)',
  'n': '%s fixed-rate loans FY2025-26 (%.0f%% of term loans)' % (format(spread_res['F']['n'], ','), 100 * spread_res['F']['n'] / (spread_res['F']['n'] + spq['n'])),
  'method': 'same as variable', 'validation': 'none needed (not wired in)',
  'recommended_value': 'keep sbaRate on the variable-rate table (%.0f%% of loans, and SBA acquisition notes are usually prime-based); store fixed_rate_knots for display' % (100 * spq['n'] / (spread_res['F']['n'] + spq['n']))},
 {'param': 'Charge-off probability: horizon and population base (replaces MODELS.risk.base_rate 0.0569 "resolved-only"); base_cif = the denominator of rel',
  'current_value': 'base_rate 5.69%% = 774/13,613 resolved loans, no horizon; resolved-only rate on this term-loan population %s. Previous fit: base_cif 1.93%% / 4.81%% (FY2024-26 book with fixed-rate notes\' low spreads run through the variable slope); the console\'s own pricing of that book averaged %.3fx / %.3fx of it, so rel ran about 10%% high'
                   % (pc_(RESOLVED_ONLY), *BASE_DIAG['previous_definition']['console_over_base']),
  'fitted_value': ('population (FY2024-26 book, n %s, if 2023-26 conditions hold): %s within 5 yrs, %s within 8, %s within 10; = the mean of the console\'s own pricing of every loan in that book '
                   '(table spread, variable note, shrunk, its own size, sector, 6-digit industry, state and franchise flag), with co.lp_shift solved so the 5-year mean equals the book\'s fitted level '
                   '(each note at its own spread and rate type; %.1f%% fixed-rate at a mean spread of %.2f pp). Aalen-Johansen (non-parametric, FY2018-26 loans) %s at 5 yrs, %s at 8. '
                   'Reference loan ($650k note, table spread, average sector, no state) %s / %s / %s (rel %.2f). '
                   'Level uncertainty beyond parameters, 8-year: specifications (calendar vs approval-cohort terms, both or neither, payoff prime term, payoffs censored at 2026-03-31, everything censored at 2025-12-31) %s-%s; '
                   'reference period (charge-offs in 2025-26 ran x%.2f the 2023-24 rate, log %.2f, quarter-clustered SE %.2f; taking either period whole as current) %s-%s; combined %s-%s. '
                   'The shipped level is in the upper part: the two-year forecast over-predicted (O/E %.2f) and FY2024-26 approvals so far run O/E %.2f on %d charge-offs (p %.2f); the vintage holdout under-predicted (O/E %.2f).'
                   % (format(len(recent), ','), pc_(BASE60), pc_(BASE96), pc_(BASE_TERM), 100 * BASE_DIAG['fixed_share'], BASE_DIAG['fixed_mean_spread'], pc_(aj_pool[60]), pc_(aj_pool[96]),
                      pc_(REF60[0]), pc_(REF96[0]), pc_(REF_TERM[0]), REF_TERM[0] / BASE_TERM,
                      pc_(SPEC_RANGE['h96'][0]), pc_(SPEC_RANGE['h96'][1]), math.exp(D25['co'][0]), D25['co'][0], D25['co'][2], pc_(COND_RANGE['h96'][0]), pc_(COND_RANGE['h96'][1]),
                      pc_(LEVEL_RANGE['h96'][0]), pc_(LEVEL_RANGE['h96'][1]), ch['new_full']['O_over_E'], COHORT_OE['FY2024-26']['O_over_E'], COHORT_OE['FY2024-26']['O'],
                      COHORT_OE['FY2024-26']['poisson_p_le'], vh['new_full']['O_over_E'])),
  'se': ('parameter SE: reference loan 5-yr %s, 8-yr %s, 10-yr %s; population 5-yr %s, 8-yr %s, 10-yr %s. Parameter simulation from the lender/two-way clustered covariances of both hazards '
         'and the shrink factor, with the level shift re-solved in every draw (the 8-yr reference SE with the Hessian covariance would be %s); the 10-yr figure adds the tail-factor judgment SE %.2f. These cover parameter error only, '
         'not the specification and reference-period range above (8-yr %s-%s) or a change in conditions. Aalen-Johansen bootstrap: 5-yr %s, 8-yr %s'
         % (pc_(REF60[1]), pc_(REF96[1]), pc_(REF_TERM[1]), pc_(POP_SE[60]), pc_(POP_SE[96]), pc_(POP_TERM_SE), pc_(REF96_HESS_SE), TAIL_SE,
            pc_(LEVEL_RANGE['h96'][0]), pc_(LEVEL_RANGE['h96'][1]), pc_(float(np.nanstd(aj_boot[:, 4]))), pc_(float(np.nanstd(aj_boot[:, 7]))))),
  'n': '%s loans: %s charged off, %s paid in full, %s open (censored); %s loan-months; %d lenders; base on the %s FY2024-26 loans' % (format(len(d), ','), format(n_co, ','), format(n_pif, ','), format(n_open, ','), format(int(Pall['dt'].sum()), ','), N_CLUST['n_lender'], format(len(recent), ',')),
  'method': HAZ_METHOD, 'validation': VALTXT + (' Base check: fitRisk on the shipped tables applied to every FY2024-26 loan averages %.4f at 5 years and %.4f at 8 (%.4fx and %.4fx of base_cif), mean rel %.4f.'
                                                % (BOOK_CHECK['mean_p5'], BOOK_CHECK['mean_p8'], BOOK_CHECK['p5_over_h60'], BOOK_CHECK['p8_over_h96'], BOOK_CHECK['mean_rel'])),
  'recommended_value': ('base_cif {h60: %.4f, h96: %.4f, term: %.4f, definition, se, spec_range, conditions_range, level_range, conditions, newest_cohort, note}; co.lp_shift %.4f; '
                        'headline = charged off within 10 years if 2023-26 conditions hold, with the 5-year figure beside it; rel = pTerm / base_cif.term (averages 1 over the FY2024-26 book as fitRisk prices it). '
                        'Data tab row "Population level across specifications and reference periods" shows level_range (8-yr %s-%s), not the specification range alone'
                        % (RISK['base_cif']['h60'], RISK['base_cif']['h96'], RISK['base_cif']['term'], RISK['co']['lp_shift'], pc_(LEVEL_RANGE['h96'][0], 1), pc_(LEVEL_RANGE['h96'][1], 1)))},
 {'param': 'base_cif.conditions / conditions_range (is "2023-26 conditions" one level?); new',
  'current_value': 'none (2023-26 pooled as one reference period)',
  'fitted_value': ('charge-off hazard in calendar 2025-26 vs 2023-24, given age, size, spread and rate type: log %.3f (x%.2f), LR %.1f; payoff %.3f (payoff panel censored at 2026-03-31). Quarter effects vs 2023Q1: %s. '
                   'Population 8-year level: 2023-24 charge-off and payoff conditions %s (x%.2f of shipped), 2025-26 %s (x%.2f); mixed (one period\'s charge-offs with pooled payoffs) %s-%s'
                   % (D25['co'][0], math.exp(D25['co'][0]), D25['lr_co'], D25['pif'][0], ', '.join('%s %+.2f' % (k, v) for k, v in QDIAG['quarter_effects_vs_2023Q1'].items()),
                      pc_(COND['2023-24 charge-off and payoff conditions']['h96']), COND['2023-24 charge-off and payoff conditions']['ratio_h96_to_main'],
                      pc_(COND['2025-26 charge-off and payoff conditions (payoffs to 2026-03-31)']['h96']), COND['2025-26 charge-off and payoff conditions (payoffs to 2026-03-31)']['ratio_h96_to_main'],
                      pc_(COND_RANGE['mixed_h96'][0]), pc_(COND_RANGE['mixed_h96'][1]))),
  'se': 'log ratio: Hessian %.3f, quarter-clustered %.3f (shipped), lender-clustered %.3f; quarters as units (%d vs %d): Welch t %.2f, p %.3f; every quarter 2025Q2-2026Q2 (max %+.2f) below every 2023-24 quarter (min %+.2f)'
        % (D25['co'][1], D25['co'][2], D25['co'][3], QDIAG['n_quarters'][0], QDIAG['n_quarters'][1], QDIAG['welch_t_2025_26_vs_2023_24'], QDIAG['welch_p'], QDIAG['max_2025Q2_2026Q2'], QDIAG['min_2023_24']),
  'n': 'same loans; charge-offs by quarter of charge-off date %s' % ', '.join('%s %d' % (k, v) for k, v in QDIAG['chargeoffs_by_quarter'].items()),
  'method': 'calendar dummy (piece midpoint in calendar 2025 or later) added to the shipped charge-off hazard; the same on the payoff hazard fitted on the panel censored at 2026-03-31 (2026Q2 payoffs look under-recorded); quarter dummies 2023Q2-2026Q2 as a check; each population level re-solves its own shift as for base_cif',
  'validation': ('the calendar holdout (O/E %.2f) and the FY2024-26 cohort (O/E %.2f) point the same way; the vintage holdout (O/E %.2f) the other. By charge-off date the largest quarterly batch '
                 'is %s (%d charge-offs), which fits a backlog being cleared as much as a lower rate. Not identified: whether 2023-24 was a post-relief catch-up or 2025-26 slower SBA charge-off processing'
                % (ch['new_full']['O_over_E'], COHORT_OE['FY2024-26']['O_over_E'], vh['new_full']['O_over_E'], QDIAG['largest_batch'][0], QDIAG['largest_batch'][1])),
  'recommended_value': ('not applied to the level (the pooled 2023-26 reference is kept); MODELS.risk.base_cif.conditions {ratio %.2f, log_coef, se, quarter_effects, levels} and conditions_range {h96: [%.4f, %.4f]}; '
                        'level_range = specifications and reference periods; hero tooltip: "Charge-offs in 2025-26 ran about %.2fx the 2023-24 rate (age-adjusted); taking either period as current puts this figure at about <p x %.2f>-<p x %.2f>"'
                        % (math.exp(D25['co'][0]), COND_RANGE['h96'][0], COND_RANGE['h96'][1], math.exp(D25['co'][0]), COND_RANGE['h96'][0] / BASE96, COND_RANGE['h96'][1] / BASE96))},
 {'param': 'tail_factor (8-year to 10-year cumulative charge-off; a transfer judgment)', 'current_value': 'none (no horizon); previous fit 1.1745, SE 0.029',
  'fitted_value': ('%.3f = CIF(120)/CIF(96) of mature 7(a) term loans approved FY2010-15, size-matched to the acquisition-loan mix (by band: %s; >= $150k size-matched %.3f, unweighted %.3f; '
                   'the acquisition model\'s own flat hazard after 84 months %.3f; FY2000-16 vintages %.2f-%.2f)'
                   % (TAIL, ', '.join('%s %.3f' % (k, v['ratio']) for k, v in tail_band.items()), TAIL_SIZE_MATCHED_150, tv[120] / tv[96], model_ratio_120_96,
                      CYCLE['r120_96_range'][0], CYCLE['r120_96_range'][1])),
  'se': ('%.2f (judgment; the measurable parts - bootstrap %.3f, across-vintage sd %.3f, size-matching %.3f, flat-hazard alternative %.3f - combine to %.3f). It covers the loan-band range '
         '1.07-1.33 at about 2 SE; the band gradient is partly term mix (larger mature loans more often carry 25-year real-estate terms) and cannot be separated because SBA '
         'overwrites TermInMonths for charged-off loans' % (TAIL_SE, tail['ratio_120_over_96_se'], TAIL_SD_VINT, abs(TAIL - tv[120] / tv[96]), abs(model_ratio_120_96 - TAIL), TAIL_COMPOSITE)),
  'n': '%s loans (FY2010-15, all sizes, for the band table); %s loans >= $150k, %s charge-offs' % (format(int(sum(v['n'] for v in tail_band.values())), ','), format(tail['n'], ','), format(tail['chgoff'], ',')),
  'method': 'Aalen-Johansen cumulative incidence (PIF competing) by loan band on the raw FOIA FY2010-2019 file, weighted by the acquisition loans\' share in each band; transfer from all 7(a) term loans to acquisitions (no CHOW loan is older than 8.5 years)',
  'validation': ('cross-check: mature-vintage CIF(96)/CIF(60) = %.2f vs %.2f observed in CHOW loans, so the shape transfers to within ~13%%; the 8-year point itself is fitted on acquisition loans. '
                 'FY2011-12 vintages (x1.14) are lowest; their years 9-10 fell in FY2020-22 (CARES s.1112 payments)' % (tail['ratio_96_over_60'], tail['chow_aj_ratio_96_over_60'])),
  'recommended_value': 'tail_factor %.4f, tail_factor_se %.2f, tail_by_band (display), tail_note; pTerm = CIF(96) x tail_factor; label as borrowed from mature 7(a) loans (a judgment)' % (RISK['tail_factor'], RISK['tail_factor_se'])},
 {'param': 'co.coef.lnamt (ln loan at 4 years on book; loan = 0.85 x price clamped to [$25k, $5M])', 'current_value': 'ln_amt -0.2093 on ln(PRICE), logistic on resolved loans; earlier fits -0.2991 (proportional) and -0.2684 (with staffing)',
  'fitted_value': '%.4f per log point (log hazard ratio at 4 years on book); by years on book: %s' % (cot.loc['lnamt', 'est'], ', '.join('%d yr %+.2f' % (k, v) for k, v in SIZE_BY_AGE.items())),
  'se': cse('lnamt'), 'n': '%d charge-offs in %s loans' % (n_co, format(len(d), ',')),
  'method': HAZ_METHOD, 'validation': 'enters every validation above; with the 40 largest lenders as fixed effects %.3f' % lg['lnamt'],
  'recommended_value': '%.4f' % RISK['co']['coef']['lnamt']},
 {'param': 'co.age_coef.lnamt (ln loan x (min(years on book, 6) - 4)); new', 'current_value': 'none (proportional size effect)',
  'fitted_value': '%.4f per year: larger loans are charged off less often and later; the hazard gap closes by year 6 (possibly longer liquidation of the real-estate notes that dominate large loans, not lower default risk; see not_identified)' % cot.loc['lnamt_x_age', 'est'],
  'se': cse('lnamt_x_age'), 'n': 'same',
  'method': ('piece-level interaction on the start age of each hazard piece. Selected: LR %.1f (1 df) against the proportional model; capped at 72 months beats uncapped (dLL %.1f) and a 60-month cap (dLL %.1f); '
             'a size x (exposure after 2024-07) term adds LR %.1f once age is in (vs LR %.1f without it), so the drift seen in the calendar holdout is loan age, not calendar time. '
             'Spread x age LR %.1f and jobs x age LR %.1f: no.'
             % (-spec['-lnamt_x_age (proportional size effect)']['lr_vs_main'], -spec['size x age uncapped instead of capped at 72m']['lr_vs_main'] / 2,
                -spec['size x age capped at 60m instead of 72m']['lr_vs_main'] / 2, spec['+size x exposure after 2024-07']['lr_vs_main'],
                spec['proportional + size x exposure after 2024-07']['lr_vs_main'] - spec['-lnamt_x_age (proportional size effect)']['lr_vs_main'],
                max(0.0, spec['+spread x age']['lr_vs_main']), max(0.0, 2 * (spec['+ln(1+jobs) and ln(1+jobs) x age']['ll'] - spec['+ln(1+jobs) (SBA JobsSupported)']['ll'])))),
  'validation': ('in-sample O/E by loan band x age window: chi2 %.1f over 15 cells vs %.1f proportional ($2-5M loans: O/E %.2f at 6-36 months and %.2f at 60+ proportional; %.2f and %.2f now)'
                 % (BAND_AGE_CHI2['size effect fading to 72 months (shipped)'], BAND_AGE_CHI2['proportional size effect'],
                    *[float(band_age[(band_age.model == mm) & (band_age.band == '2-5M') & (band_age.age_months == aa)].O_over_E.iloc[0])
                      for mm in ['proportional size effect', 'size effect fading to 72 months (shipped)'] for aa in ['6-36', '60+']])),
  'recommended_value': 'co.age_coef {lnamt: %.4f}, co.age_cap_months 72, co.age_center_years 4' % RISK['co']['age_coef']['lnamt']},
 {'param': 'co.coef.spread (spread over prime at approval, pp, clipped to [%.2f, 3.00], centred 2.25); replaces rate_c' % SPREAD_CLIP[0],
  'current_value': 'rate_c +0.1724 per point of the rate LEVEL minus 7',
  'fitted_value': '%.4f per pp of spread (hazard x%.2f per pp before the out-of-time shrink)' % (cot.loc['spread', 'est'], math.exp(cot.loc['spread', 'est'])),
  'se': cse('spread'), 'n': 'same',
  'method': ('spread as lender risk-pricing (an association, not a lever; the rate is not a console input); flat above 3 pp: a hinge above 3 pp adds %.3f (SE %.3f, LR %.1f, 1 df). '
             'Fixed-rate loans get their own slope (spread x fixed %.3f, SE %.3f; dropping it costs LR %.1f) and a level shift (fixed %.3f, SE %.3f); neither is priced by the console (variable note at the table spread; the level shift absorbs the fixed-rate share). '
             'The rate LEVEL in place of the spread fits far worse (AIC +%.0f).'
             % (spec['+spread_above_3pp']['terms']['spread_above3'][0], spec['+spread_above_3pp']['terms']['spread_above3'][1], spec['+spread_above_3pp']['lr_vs_main'],
                cot.loc['spread_x_fixed', 'est'], cot.loc['spread_x_fixed', 'se_shipped'], -spec['-spread_x_fixed']['lr_vs_main'], cot.loc['fixed', 'est'], cot.loc['fixed', 'se_shipped'],
                spec['rate level instead of spread']['aic_vs_main'])),
  'validation': 'enters every validation above; held its full strength out of time (component slope %.2f calendar, %.2f vintage); with the 40 largest lenders as fixed effects %.3f (mostly within-lender)'
                % (SLOPE_C['by_component']['spread_franchise_fixed'][0], SLOPE_V['by_component']['spread_franchise_fixed'][0], lg['spread']),
  'recommended_value': '%.4f; spread = clamp(rate - prime, %.4f, 3)' % (RISK['co']['coef']['spread'], RISK['spread_range'][0])},
 {'param': 'co.coef.lnjobs (staffing): removed from the console model', 'current_value': 'jobs +0.0024 per job, linear (console passes jobsFor(rev, ind)); previous fit ln(1+jobs) 0.1201 (SE 0.062)',
  'fitted_value': ('not shipped. Fitted as a check with SBA JobsSupported: ln(1+jobs) %+.4f (Hessian SE %.4f), LR %.1f (1 df); log beats linear by LR %.1f; payoff hazard %+.3f (SE %.3f). '
                   'With it, ln loan %.3f and spread %.3f (without: %.3f and %.3f)'
                   % (JOBS_CHECK['co_lnjobs'][0], JOBS_CHECK['co_lnjobs'][1], JOBS_CHECK['co_lr'], JOBS_CHECK['co_lr_log_vs_linear'], JOBS_CHECK['pif_lnjobs'][0], JOBS_CHECK['pif_lnjobs'][1],
                      JOBS_CHECK['co_core_with_jobs']['lnamt'], JOBS_CHECK['co_core_with_jobs']['spread'], cot.loc['lnamt', 'est'], cot.loc['spread', 'est'])),
  'se': '%.4f (Hessian; with clustering it was 0.062 in the previous fit, so the coefficient was under 2 clustered SE)' % JOBS_CHECK['co_lnjobs'][1],
  'n': 'same; SBA JobsSupported median by loan band %s' % ', '.join('%s %g' % (k, v) for k, v in JOBS_CHECK['sba_jobs_median_by_loan_band'].items()),
  'method': 'same hazard model with ln(1+JobsSupported) added (jobs clipped to [0,100], centred at 8)',
  'validation': ('the measure does not transfer: SBA JobsSupported is jobs created plus retained, reported by the lender; the console passes jobsFor(rev, ind), Census employees per revenue, '
                 'e.g. %s for the example medical deal (note %s) against an SBA median of %g for $2-5M loans, so with the coefficient the console\'s hazards ran high (by 6-20%%, as the review measured) and rose with revenue at a fixed price'
                 % (('%d' % BA[0]['jobs_console']) if BA else 'n/a', ('$%.2fM' % (BA[0]['loan_new'] / 1e6)) if BA else 'n/a', JOBS_CHECK['sba_jobs_median_by_loan_band']['2-5M'])),
  'recommended_value': 'drop lnjobs from MODELS.risk.co.coef and pif.coef (the shipped model is refitted without it); fitRisk keeps the jobs argument for the interface and ignores it; MODELS.risk.staffing {applied:false, coef_if_fitted, note}; Data tab row "staffing (SBA jobs supported)" shown as not used'},
 {'param': 'co.coef.franchise', 'current_value': '-0.0655 (logistic)', 'fitted_value': '%.4f' % cot.loc['franchise', 'est'], 'se': cse('franchise'),
  'n': '%s franchise loans' % format(int(d.is_franchise.sum()), ','), 'method': 'same model', 'validation': 'not distinguishable from 0',
  'recommended_value': '%.4f (kept for the interface; the Data tab says "no measurable difference")' % RISK['co']['coef']['franchise']},
 {'param': 'co.lp_shrink and co.lp_shift (out-of-time shrink of every loan-level effect; level shift solved on the console-priced FY2024-26 book); new', 'current_value': 'none (effects at full fitted size)',
  'fitted_value': ('lp_shrink %.4f, lp_shift %.4f: log h = base + shift + %.2f x (covariates + size x age + sector + 6-digit + state). The shift puts the console-priced FY2024-26 book at the book\'s fitted 5-year level %s '
                   '(previous fit: shift %.4f on the book with fixed-rate notes run as variable at their own low spreads; the new shift multiplies every console hazard by %.3f); '
                   'the p1-p99 range of the console-priced book\'s loan-level log hazard narrows from %.2f..%.2f to %.2f..%.2f'
                   % (GAMMA, LP_SHIFT, GAMMA, pc_(BASE60), BASE_DIAG['previous_definition']['shift'], BASE_DIAG['hazard_multiple_vs_previous_shift'], _q[0], _q[2], LP_SHIFT + GAMMA * _q[0], LP_SHIFT + GAMMA * _q[2])),
  'se': '%.3f (not below the more precise single holdout\'s SE, because the two holdouts share test exposure)' % GAMMA_SE,
  'n': '%d + %d held-out charge-offs (vintage, calendar holdouts)' % (SLOPE_V['events'], SLOPE_C['events']),
  'method': ('Poisson regression of held-out charge-offs on the training model\'s loan-level log hazard, age baseline free, per holdout; inverse-variance pooled: vintage %.3f (SE %.3f), '
             'calendar %.3f (SE %.3f) -> %.3f, capped at 1. By component (calendar / vintage): size %.2f / %.2f, spread %.2f / %.2f, sector %.2f / %.2f, 6-digit+state %.2f / %.2f. '
             'In-period CV slope %.2f (SE %.2f): most of the attenuation is temporal, not overfitting. The level shift solves: mean CIF60 of the FY2024-26 book as fitRisk prices it (table spread, variable note, shrunk) = the book\'s fitted (unshrunk) mean with each note at its own spread and rate type.'
             % (SLOPE_V['gamma'], SLOPE_V['se'], SLOPE_C['gamma'], SLOPE_C['se'], GAMMA_RAW,
                SLOPE_C['by_component']['size'][0], SLOPE_V['by_component']['size'][0], SLOPE_C['by_component']['spread_franchise_fixed'][0],
                SLOPE_V['by_component']['spread_franchise_fixed'][0], SLOPE_C['by_component']['sector'][0], SLOPE_V['by_component']['sector'][0],
                SLOPE_C['by_component']['naics6_state'][0], SLOPE_V['by_component']['naics6_state'][0], VAL['cv5_slope_loan_level']['pooled'], VAL['cv5_slope_loan_level']['pooled_se'])),
  'validation': 'estimated on the two out-of-time holdouts themselves, so their calibration slopes after shrinkage are not an independent check; the unshrunk model is what the validation above scores',
  'recommended_value': 'co.lp_shrink %.4f, co.lp_shrink_se %.4f, co.lp_shift %.4f; fitRisk: l1 = exp(log_base[j] + lp_shift + lp_shrink*u_j)' % (RISK['co']['lp_shrink'], RISK['co']['lp_shrink_se'], RISK['co']['lp_shift'])},
 {'param': 'rate level given the spread (judgment, not applied); new', 'current_value': 'rate_c +0.1724 on the level (no spread)',
  'fitted_value': ('prime at approval given spread: %+.3f per pp with calendar terms; %+.3f once approval cohorts are controlled (rate level given spread: %+.3f and %+.3f). '
                   'Applied at today\'s %.2f%% against the sample mean %.2f%% it would raise hazards %.0f-%.0f%%'
                   % (RATE_LEVEL['coef_calendar'][0], RATE_LEVEL['coef_calendar_cohort'][0], RATE_LEVEL['level_coef_calendar'][0], RATE_LEVEL['level_coef_calendar_cohort'][0],
                      PRIME_NOW, PRIME0_MEAN, 100 * RATE_LEVEL['uplift_range'][0], 100 * RATE_LEVEL['uplift_range'][1])),
  'se': '%.3f / %.3f (Hessian; prime at approval) ; level %.3f / %.3f' % (RATE_LEVEL['coef_calendar'][1], RATE_LEVEL['coef_calendar_cohort'][1], RATE_LEVEL['level_coef_calendar'][1], RATE_LEVEL['level_coef_calendar_cohort'][1]),
  'n': 'same', 'method': 'added to the shipped model; cohort dummies FY2018-19 and FY2020-21 vs FY2022-26',
  'validation': 'attenuates toward 0 once approval cohorts are controlled; payment-shock term (prime moves after approval) %.3f (SE %.3f): the cohort-confound reading holds'
                % (spec['+dprimeV_payment_shock']['terms']['dprimeV'][0], spec['+dprimeV_payment_shock']['terms']['dprimeV'][1]),
  'recommended_value': 'MODELS.risk.rate_level (display only, applied:false); Data tab and hero tooltip: "loans written at today\'s prime may run %.0f-%.0f%% higher (rate level, not applied)"' % (100 * RATE_LEVEL['uplift_range'][0], 100 * RATE_LEVEL['uplift_range'][1])},
 {'param': 'calendar-year terms 2019/2020/2021/2022 vs 2023-26 (COVID relief, charge-off processing)', 'current_value': 'vintage term fitted then pinned to 0',
  'fitted_value': ', '.join('%s %.3f' % (y, cot.loc['cal%d' % y, 'est']) for y in CAL_YEARS) + ' (charge-off); PIF ' + ', '.join('%s %.3f' % (y, pft.loc['cal%d' % y, 'est']) for y in CAL_YEARS),
  'se': ', '.join('%.3f' % cot.loc['cal%d' % y, 'se_shipped'] for y in CAL_YEARS) + ' (shipped, clustered)', 'n': 'same',
  'method': 'calendar dummies on the piece midpoint; LR for all four = %.1f (4 df). Not applied in the console: 2023-26 is current conditions' % (-spec['no_calendar_terms']['lr_vs_main']),
  'validation': 'calendar holdout above; payment shock on variable loans after prime moves: %.3f (SE %.3f) per pp, LR %.2f, i.e. none'
                % (spec['+dprimeV_payment_shock']['terms']['dprimeV'][0], spec['+dprimeV_payment_shock']['terms']['dprimeV'][1], spec['+dprimeV_payment_shock']['lr_vs_main']),
  'recommended_value': 'stored under co.not_applied; prime held flat'},
 {'param': 'industry_effects (sector random effect on the charge-off log hazard, NAICS-2 groups)', 'current_value': 'sector log-odds from 1,152,544 loans of all types x ind_eff 0.695',
  'fitted_value': 'sd tau %.3f; e.g. ' % math.sqrt(TAU2_CO) + ', '.join('%s %+.3f' % (k, v) for k, v in sorted(co_sec.items(), key=lambda kv: kv[1]) if k in ('62', '61', '31', '54', '44', '72', '23', '71', '48')),
  'se': 'posterior sd %.3f-%.3f' % (min(co_sec_sd.values()), max(co_sec_sd.values())), 'n': '%d groups (31-33, 44-45, 48-49 pooled)' % len(co_sec),
  'method': 'penalised (Gaussian random-effect) Poisson; tau^2 by Schall/EM iteration ((sum u^2 + trace Cov_u)/S) to convergence, re-estimated in every validation split (%s); shrinks each sector toward the average'
            % ', '.join('%s %.3f' % (k, v['co']) for k, v in TAU_SPLITS.items()),
  'validation': 'core model (sector + covariates) CV AUC on the admin window %.3f vs %.3f null' % (VAL['cv5_admin_window']['new_core_no_state_naics6']['auc'], VAL['cv5_admin_window']['null_age_calendar_only']['auc']),
  'recommended_value': 'MODELS.risk.industry_effects (2-digit keys incl. 32,33,45,49) as shipped; ind_eff coefficient = 1 (folded in); multiplied by co.lp_shrink in fitRisk'},
 {'param': 'naics6_effects (6-digit within sector, the console\'s 14 codes; ecom deliberately none)', 'current_value': 'none (sector only)',
  'fitted_value': ', '.join('%s %+.3f' % (k, v) for k, v in RISK['naics6_effects'].items()),
  'se': 'posterior sd of log RR %.2f-%.2f' % (n6_app.sd_log_rr.min(), n6_app.sd_log_rr.max()),
  'n': '%d 6-digit cells; app cells hold %s loans' % (len(n6_tab), ', '.join(str(int(v)) for v in n6_app.n_loans)),
  'method': 'Poisson-gamma empirical Bayes on observed/expected charge-offs given the sector model: RR = (O + a)/(E + a), a = %.2f by marginal likelihood (implied between-cell sd of log RR %.2f)' % (A_N6, math.sqrt(special.polygamma(1, A_N6))),
  'validation': 're-estimated inside every CV fold: adding 6-digit and state effects lifts CV AUC (admin window) from %.3f to %.3f; out of time they held at %.2f (calendar) and %.2f (vintage) of their size, covered by the shrink'
                % (VAL['cv5_admin_window']['new_core_no_state_naics6']['auc'], VAL['cv5_admin_window']['new_full']['auc'], SLOPE_C['by_component']['naics6_state'][0], SLOPE_V['by_component']['naics6_state'][0]),
  'recommended_value': 'RISK_NAICS6 map (index.html IND2NAICS6 minus ecom) + MODELS.risk.naics6_effects'},
 {'param': 'state_effects (log RR on the charge-off hazard)', 'current_value': 'probability-scale deviation shrunk n/(n+250) x st_eff 2.674',
  'fitted_value': '%d states/territories; lowest %s, highest %s' % (len(st_keep), ', '.join('%s %+.2f' % (k, v) for k, v in st_sorted.log_rr.head(3).items()), ', '.join('%s %+.2f' % (k, v) for k, v in st_sorted.log_rr.tail(3).items())),
  'se': 'posterior sd of log RR %.2f-%.2f' % (st_keep.sd_log_rr.min(), st_keep.sd_log_rr.max()), 'n': 'ProjectState (BorrState if blank)',
  'method': 'Poisson-gamma empirical Bayes, a = %.2f (implied sd %.2f)' % (A_ST, math.sqrt(special.polygamma(1, A_ST))), 'validation': 'as above (in-fold)',
  'recommended_value': 'MODELS.risk.state_effects as shipped; the state dropdown label becomes "pts charge-off risk, 10 yr"'},
 {'param': 'pif (competing payoff hazard: log_base, coef, sector)', 'current_value': 'none',
  'fitted_value': 'coef ' + ', '.join('%s %.3f' % (c, pft.loc[c, 'est']) for c in APP_COVS) + '; payoff faster after prime rises on variable loans (%.3f per pp, not applied)' % pft.loc['dprimeV', 'est'],
  'se': ', '.join('%.3f' % pft.loc[c, 'se_shipped'] for c in APP_COVS) + ' (shipped: largest of Hessian, lender-clustered and two-way; Hessian ' + ', '.join('%.3f' % pft.loc[c, 'se'] for c in APP_COVS) + ')',
  'n': '%s payoffs' % format(n_pif, ','),
  'method': 'same piecewise-exponential model with its own sector random effect (tau^2 %.4f); not shrunk (payoff only sets how long a loan is at risk)' % TAU2_PIF, 'validation': 'part of every CIF prediction above',
  'recommended_value': 'MODELS.risk.pif as shipped'},
 {'param': 'lgd (severity = gross charge-off / original approval)', 'current_value': 'MEDIAN by price band, isotonic: 0.806 / 0.796 / 0.725 (pooled median 0.774), applied as p x median',
  'fitted_value': 'mean %.3f, median %.3f; fractional logit: b0 %.3f, ln loan %.3f, years on book at charge-off %.3f (centred 4). Reference $650k note (average sector): %.0f%% if charged off at 2 years, %.0f%% at 7; timing-weighted over 10 years %.0f%%'
                  % (LGDV['pooled_mean'], LGDV['pooled_median'], LGD_AGE_FIT['b0'], LGD_AGE_FIT['b_size'], LGD_AGE_FIT['b_age'], 100 * REFM['sev24'], 100 * REFM['sev84'], 100 * REFM['lgd']),
  'se': 'robust (HC0): b0 %.3f, ln loan %.3f, age %.3f; size-only curve bootstrap SE %.3f-%.3f' % (LGD_AGE_FIT['se'][0], LGD_AGE_FIT['se'][1], LGD_AGE_FIT['se'][2], min(lgd_se), max(lgd_se)),
  'n': '%d charged-off acquisition term loans (%d ratios above 1 capped at 1)' % (LGDV['n'], LGDV['n_ratio_above_1_capped']),
  'method': 'quasi-binomial fractional logit; MEAN not median because expected loss = PD x E[LGD]; expected loss integrates severity over the hazard model\'s timing of charge-offs',
  'validation': '10-fold CV MSE: size+age %.4f, size only %.4f, pooled mean %.4f, current median curve %.4f (biased +%.1f pp). Temporal (charge-offs before vs after 2024-07-01, %d/%d): size+age MSE %.4f, mean error %+.3f; size only %.4f, mean error %+.3f'
                % (LGDV['cv10_mse_size_age'], LGDV['cv10_mse_frac_logit'], LGDV['cv10_mse_pooled_mean'], LGDV['mse_current_median_curve'], -100 * LGDV['mean_error_current_median_curve'],
                   LGDV['temporal_train_n'], LGDV['temporal_test_n'], LGDV['temporal_mse_size_age'], LGDV['temporal_mean_error_size_age'], LGDV['temporal_mse_frac_logit'], LGDV['temporal_mean_error']),
  'recommended_value': ('MODELS.risk.lgd {b0 %.4f, b_size %.4f, b_age %.4f, age_center_years 4, age_range [12,96], post_term_ratio %.2f}; expLoss = loss charged off by month 120 (the note\'s lifetime loss runs higher: '
                        'mature 7(a) CIF(144)/CIF(120) = %.2f); lgd shown = expLoss / pTerm' % (RISK['lgd']['b0'], RISK['lgd']['b_size'], RISK['lgd']['b_age'], tail['ratio_144_over_120_FY2010_13'], tail['ratio_144_over_120_FY2010_13']))},
 {'param': 'timing (replaces median_years_to_failure 4.3 / pct_within_2yr 0.08, resolved-only)', 'current_value': 'median 4.3 yr, 8% within 2 yr, 22% within 3 yr',
  'fitted_value': 'given charge-off within 8 years: median %d months (%.1f yr); %.0f%% by 2 yr, %.0f%% by 3 yr, %.0f%% by 5 yr' % (TIMING['median_months_given_chargeoff_by_96'], TIMING['median_months_given_chargeoff_by_96'] / 12, 100 * TIMING['share_by_24_of_96'], 100 * TIMING['share_by_36_of_96'], 100 * TIMING['share_by_60_of_96']),
  'se': 'Aalen-Johansen; CIF(96) SE %s' % pc_(float(np.nanstd(aj_boot[:, 7]))), 'n': 'all %s loans' % format(len(d), ','),
  'method': 'Aalen-Johansen cumulative incidence, PIF competing, open censored; horizon-conditional (lifetime median is not identified)',
  'validation': 'resolved-only median %.1f months was biased short by construction' % TIMING['resolved_only_median_months_to_chargeoff'],
  'recommended_value': 'MODELS.risk.timing as shipped; label "given charge-off within 8 years"'},
 {'param': 'size_band_cif (observed 5-year charge-off by LOAN band; replaces size_band_rates, resolved-only by price)', 'current_value': '<250K 7.82%, 250-500K 6.69%, 500K-1M 5.21%, 1-2M 3.92%, 2-5M 3.13% (resolved-only)',
  'fitted_value': ', '.join('%s %s (8-yr %s; fitted in-sample %s; console at table spread %s)' % (k, pc_(v['cif60']), pc_(v['cif96']) if v['cif96'] is not None else 'n/a', pc_(v['model60_insample']), pc_(v['model60_table_spread'])) for k, v in band_rows.items()),
  'se': ', '.join('%s' % pc_(v['cif60_se']) for v in band_rows.values()), 'n': ', '.join('%s' % format(v['n'], ',') for v in band_rows.values()),
  'method': ('Aalen-Johansen by loan band, bootstrap SE (B=200). "Fitted in-sample" = mean 5-year probability of the band\'s loans under the fitted model with their own spread and rate type and the realised calendar; '
             '"console" = the same loans as the console prices them: FY2025-26 table spread, variable note, 2023-26 conditions, out-of-time shrink'),
  'validation': ('fitted in-sample within %.2f SE of the observed rate in every band (max |z|); the console version runs %s of observed (max |z| %.2f; previous fit 1.17x, 1.07x, 1.21x, 1.29x, 1.06x). '
                 'What remains comes from today\'s table spread (%.2f pp under $250k against a band mean of %.2f for variable notes and %.2f for all notes) and the shrink lifting below-average bands; '
                 'a model without the spread gives %s at 5 years. At 8 years the console runs %s of the observed rates, partly because it assumes 2023-26 payoff speeds: the 2021-22 payoff wave '
                 '(payoff calendar terms %+.2f/%+.2f) took many FY2018-19 loans out of risk.'
                 % (max(abs(v['model60_insample'] - v['cif60']) / v['cif60_se'] for v in band_rows.values()),
                    ', '.join('%.2fx' % (v['model60_table_spread'] / v['cif60']) for v in band_rows.values()),
                    max(abs(v['model60_table_spread'] - v['cif60']) / v['cif60_se'] for v in band_rows.values()),
                    band_rows['<250K']['spread_mean_table'], band_rows['<250K']['spread_mean_variable_observed'], band_rows['<250K']['spread_mean_all_observed'],
                    ', '.join('%s %.2fx' % (k, NOSPREAD['band_console60'][k] / v['cif60']) for k, v in band_rows.items()),
                    ', '.join('%s %.2fx' % (k, v['model96_table_spread'] / v['cif96']) for k, v in band_rows.items()), pft.loc['cal2021', 'est'], pft.loc['cal2022', 'est'])),
  'recommended_value': 'MODELS.risk.size_band_cif (with loan_median, jobs_median, model60_insample, model60_table_spread, model96_*); band keyed by loan = 0.85 x price; the hero tooltip shows the observed band rate'},
 {'param': 'spread_channel (risk by size with no rate entered; display only); new', 'current_value': 'none (the spread coefficient also acts through the median spread table)',
  'fitted_value': ('model without the spread (both hazards refitted, sector variance re-estimated, 6-digit/state maps refitted, same shrink, own shift): ln loan %.3f at 4 years (vs %.3f), size x age %.3f; '
                   'shipped / no-spread 8-year probability at average sector: %s; console 5-year rate by band, no-spread model: %s'
                   % (NOSPREAD['lnamt'][0], cot.loc['lnamt', 'est'], NOSPREAD['lnamt_x_age'], ', '.join('$%s x%.2f' % (('%gk' % (float(k) / 1e3)) if float(k) < 1e6 else ('%gM' % (float(k) / 1e6)), v) for k, v in NOSPREAD['cif96_ratio_shipped_over_nospread'].items()),
                      ', '.join('%s %s' % (k, pc_(v)) for k, v in NOSPREAD['band_console60'].items()))),
  'se': 'ln loan %.3f (Hessian); the two models differ in specification, not sampling' % NOSPREAD['lnamt'][1],
  'n': 'same', 'method': 'refit without spread and spread x fixed; log-likelihood %.1f vs %.1f' % (NOSPREAD['ll'], NOSPREAD['ll_main']),
  'validation': 'neither dominates by band against the observed 5-year rates (see size_band_cif)',
  'recommended_value': 'keep the spread (an entered rate is informative; LR large); MODELS.risk.spread_channel (display); Data tab note: with no rate entered, risk by size includes lender pricing through the median spread table; against a model without the spread the 8-year figure runs x%.2f-x%.2f across $100k-$4M' % (min(_rr), max(_rr))},
 {'param': 'real_estate (share of acquisition notes with a term over 10 years, by loan band; display only); new', 'current_value': 'none',
  'fitted_value': ', '.join('%s %.1f%%' % (k, 100 * v['share_term_over_120m']) for k, v in RE_SHARE.items()) + ' (paid-off and open loans)',
  'se': 'binomial, < 1 pp per band', 'n': ', '.join('%s %s' % (k, format(v['n'], ',')) for k, v in RE_SHARE.items()),
  'method': 'TermInMonths > 120 among loans not charged off (SBA overwrites the term of charged-off loans: a standard term on %.0f%% of them against %.0f%% of others)' % (100 * RE_NOTE['standard_term_share_chargeoffs'], 100 * RE_NOTE['standard_term_share_others']),
  'validation': 'n/a (descriptive); the confound with the size gradient is not identified (see not_identified)',
  'recommended_value': 'MODELS.risk.real_estate (display); Data tab caveat: a business-only acquisition of the same size is probably riskier than shown'},
 {'param': 'like-for-like comparison (replaces full_dataset_base_rate 0.1718, all 7(a) loans of all vintages, resolved-only)', 'current_value': '5.69% vs 17.18%',
  'fitted_value': 'charged off within 5 years, 7(a) term loans FY2018-26: acquisitions %s, existing businesses %s, startups/new %s; size-matched (loans >= $150k): %s / %s / %s'
                  % (pc_(lfl['acquisition']['cif60']), pc_(lfl['existing']['cif60']), pc_(lfl['startup_or_new']['cif60']), pc_(lfl['acquisition']['cif60_loans_150k_up']), pc_(lfl['existing']['cif60_loans_150k_up']), pc_(lfl['startup_or_new']['cif60_loans_150k_up'])),
  'se': 'n large (SE < 0.1 pp)', 'n': ', '.join('%s %s' % (k, format(v['n'], ',')) for k, v in lfl.items()),
  'method': 'Aalen-Johansen on the raw FOIA files, same horizon and censoring', 'validation': 'n/a (descriptive)', 'recommended_value': 'MODELS.risk.like_for_like (cif60 and cif60_150k; the Data tab shows both)'},
 {'param': 'through_cycle (context for the 10-year figure; new, display only)', 'current_value': 'none',
  'fitted_value': ('10-year charge-off of all 7(a) term loans >= $150k by approval year: FY2000-04 %s-%s, FY2005 %s, FY2006-08 %s-%s, FY2009 %s, FY2010-16 %s-%s. '
                   'Acquisition loans >= $150k ran %.2fx all loans >= $150k at 5 years in FY2018-26'
                   % (pc_(min(cyc[y]['cif120'] for y in range(2000, 2005)), 1), pc_(max(cyc[y]['cif120'] for y in range(2000, 2005)), 1), pc_(cyc[2005]['cif120'], 1),
                      pc_(CYCLE['cif120_FY2006_08'][0], 1), pc_(CYCLE['cif120_FY2006_08'][1], 1), pc_(cyc[2009]['cif120'], 1),
                      pc_(CYCLE['cif120_FY2010_16'][0], 1), pc_(CYCLE['cif120_FY2010_16'][1], 1), CYCLE['acq_to_all_150k_ratio_cif60'])),
  'se': 'n 12k-25k per vintage (SE < 0.4 pp)', 'n': ', '.join('%d %s' % (k, format(v['n'], ',')) for k, v in cyc.items()),
  'method': 'Aalen-Johansen on the raw FOIA FY2000-2019 files, PIF competing, open censored', 'validation': 'n/a (descriptive)',
  'recommended_value': 'MODELS.risk.through_cycle; Data tab row "Through the cycle"; hero tooltip; the headline is labelled "if 2023-26 conditions hold"'},
]
NOT_ID = [
 ('The rate LEVEL as a risk factor separate from the spread: given the spread, prime at approval is %+.2f (SE %.2f) per pp with calendar terms and %+.2f (SE %.2f) once approval cohorts are controlled '
  '(rate level: %+.2f (%.2f) and %+.2f (%.2f)); approval-month prime varied mainly across the COVID-relief cohorts (3.25%% in FY2021), and prime moves after approval show no effect, so the level is '
  'not applied. Direction stated as a labelled judgment: a loan written at today\'s %.2f%% prime (sample mean %.2f%%) may run %.0f-%.0f%% above the level shown.'
  % (RATE_LEVEL['coef_calendar'][0], RATE_LEVEL['coef_calendar'][1], RATE_LEVEL['coef_calendar_cohort'][0], RATE_LEVEL['coef_calendar_cohort'][1],
     RATE_LEVEL['level_coef_calendar'][0], RATE_LEVEL['level_coef_calendar'][1], RATE_LEVEL['level_coef_calendar_cohort'][0], RATE_LEVEL['level_coef_calendar_cohort'][1],
     PRIME_NOW, PRIME0_MEAN, 100 * RATE_LEVEL['uplift_range'][0], 100 * RATE_LEVEL['uplift_range'][1])),
 'Future prime moves: a payment-shock term (prime change since approval on variable loans) is %.3f (SE %.3f) per pp, i.e. no detectable effect; prime is held flat at today\'s %.2f%%.' % (spec['+dprimeV_payment_shock']['terms']['dprimeV'][0], spec['+dprimeV_payment_shock']['terms']['dprimeV'][1], PRIME_NOW),
 ('Conditions over the next ten years: the 10-year figure assumes 2023-26 conditions hold. The same FOIA files show 10-year charge-off of %.0f-%.0f%% for all 7(a) loans >= $150k approved FY2006-08 '
  'against %.1f-%.1f%% for FY2010-16; nothing in the data forecasts which regime comes next, so no cycle adjustment is applied and the SEs do not cover it.'
  % (100 * CYCLE['cif120_FY2006_08'][0], 100 * CYCLE['cif120_FY2006_08'][1], 100 * CYCLE['cif120_FY2010_16'][0], 100 * CYCLE['cif120_FY2010_16'][1])),
 'Default (missed payments, SBA purchase) as opposed to charge-off: FOIA has no default or purchase date; charge-off trails default by 1-2+ years, so the 5-year charge-off probability corresponds roughly to defaults within 3-4 years.',
 ('Acquisition-loan hazards beyond 8.5 years on book: none observed (SBA flags change of ownership only from Dec 2017); years 9-10 use the mature all-7(a) ratio x%.2f, a labelled transfer judgment '
  '(SE %.2f): by loan band x%.2f-%.2f, partly term mix that the data cannot separate.' % (TAIL, TAIL_SE, tail_band['<150k']['ratio'], tail_band['>=1.5M']['ratio'])),
 ('Lender: lenders differ (between-lender sd of the log hazard %.2f by Poisson-gamma empirical Bayes; the 40 largest as fixed effects LR %.0f on 40 df, with the spread at %.3f and size at %.3f) '
  'but the buyer\'s lender is not a console input; the console prices an average lender, and the SEs are clustered by lender for that reason.'
  % (LENDER_FE['eb_sd'], LENDER_FE['lr'], LENDER_FE['core_with_fe']['spread'], LENDER_FE['core_with_fe']['lnamt'])),
 'Business-quality inputs (owner dependence, management depth, recurring revenue, concentration): no counterpart in SBA data, so survival risk does not move with them; it conditions on size, spread, industry, franchise and state only.',
 ('Staffing in the console\'s terms: SBA JobsSupported (jobs created plus retained, lender-reported) carries %+.3f (SE %.3f) per unit of ln(1+jobs), but the console\'s head count (Census employees per revenue) '
  'measures something else and runs several times higher, so staffing is not a model input; a labour-intensity effect, if any, is not captured.' % (JOBS_CHECK['co_lnjobs'][0], JOBS_CHECK['co_lnjobs'][1])),
 ('Real-estate collateral: SBA acquisition notes with a term over 10 years (real-estate notes) rise from %.0f%% of loans under $250k to %.0f%% over $2M. Part of the size gradient, and of the fading of the size '
  'effect with loan age (longer liquidation before charge-off), may be collateral rather than default risk; a business-only acquisition of the same size is probably riskier and more severe than shown. '
  'Not identifiable: SBA overwrites TermInMonths of charged-off loans (a standard term on %.0f%% of them against %.0f%% of others), in mature vintages too.'
  % (100 * RE_SHARE['<250K']['share_term_over_120m'], 100 * RE_SHARE['2-5M']['share_term_over_120m'], 100 * RE_NOTE['standard_term_share_chargeoffs'], 100 * RE_NOTE['standard_term_share_others'])),
 ('Which part of 2023-26 is "current": charge-offs in calendar 2025-26 ran x%.2f the 2023-24 rate (age-, size- and spread-adjusted; quarter-clustered SE of the log %.2f). The data cannot say whether 2023-24 '
  'was a post-relief catch-up or 2025-26 slower SBA charge-off processing; the pooled level is shipped and the two periods bracket it (8-year %.1f-%.1f%%).'
  % (math.exp(D25['co'][0]), D25['co'][2], 100 * COND_RANGE['h96'][0], 100 * COND_RANGE['h96'][1])),
 'Deals above a $5M loan and deals financed without SBA: 7(a) caps at $5M, so the loan is clamped and risk (and the table rate) is flat above about $5.9M of price; non-SBA-financed acquisitions are not in the data.',
 'Underwriting variables lenders see (DSCR, equity injection, collateral value, seller note, borrower experience): not in FOIA.',
 'Net loss after recoveries: GrossChargeOffAmount is gross; severity is an upper bound on net loss. Loss on charge-offs after month 120 (late defaults) is not in expLoss.',
 '504 acquisition risk: only 3 charge-offs among 1,419 504 change-of-ownership loans.',
]
IMPL = (
 'All edits are to /home/user/last-minute/index.html (last <script>) and are applied, verbatim, in the patched copy '
 '/tmp/claude-0/fit5/sba_risk_refresh/patched/index.html (unified diff /tmp/claude-0/fit5/sba_risk_refresh/index.html.diff), written by fit/sba_risk_refresh.py section 6.\n'
 '(1) MODELS literal ("const MODELS = {...}", ~line 2029): replace the whole value of key "risk" with the object in /tmp/claude-0/fit5/sba_risk_refresh/MODELS_risk_v3.json (its size, sha256 and every number fitRisk reads are listed at the end of this field). '
 'New against the previous revision: co.coef and pif.coef no longer carry lnjobs (both hazards refitted without staffing; MODELS.risk.staffing {applied:false} records the check); co.lp_shift is re-solved so that fitRisk over the FY2024-26 book averages the book\'s fitted level, and base_cif is that console-priced mean '
 '(base_cif.definition, previous_definition); base_cif.conditions/conditions_range/level_range (reference-period heterogeneity); real_estate and spread_channel (display); size_band_cif.*.fixed_share. Kept from earlier revisions: co.age_coef/age_cap_months/age_center_years, co.lp_shrink, '
 'co.se = clustered SEs (with se_hessian, se_lender, se_twoway beside them), tail_factor %.4f with tail_factor_se %.2f and tail_by_band/tail_note, base_cif.se/spec_range/newest_cohort/note, '
 'conditions "2023-26", rate_level (applied:false), through_cycle, lender_heterogeneity, like_for_like.*.cif60_150k, size_band_cif.*.model60_insample/model60_table_spread/loan_median/jobs_median, validation.vintage_slope/oot_loan_level_slope/cohort_oe, lgd.post_term_ratio.\n'
 '(2) MODELS.fitted literal (~line 2032): replace the value of key "sba_rate" with ' % (RISK['tail_factor'], RISK['tail_factor_se']) + json.dumps(SBA_RATE, separators=(',', ':')) + '\n'
 '    sbaRate() itself is unchanged (prime + lerpKnots(ln(max(0.85 price,1e4)), spread_knots)); update its comment to "FY2025-26 variable-rate loans, prime from Fed H.15".\n'
 '(3) Replace function fitRisk (from "/* ---- Model V: post-acquisition survival risk (FITTED, SBA) ---- */" up to "/* ---- Model I") with:\n' + JS_FITRISK +
 '    Interface unchanged: fitRisk(price,naicsKey,rate,jobs,franchise,st); jobs is accepted and ignored. Returned p is the probability of charge-off within 10 years if 2023-26 conditions hold (headline); p5 (5 years), p8 (8 years), pTerm, horizon, term, loan, spread and naics6Eff are added; '
 'rel = pTerm / base_cif.term (same horizon as the headline; averages 1 over the FY2024-26 book as fitRisk prices it); lgd is the timing-weighted mean severity and expLoss the expected loss charged off by month 120 as a share of the loan; empBand is the observed 5-year rate for the LOAN band; medYears/within3 read MODELS.risk.timing.\n'
 '(4) Hero tile: replace the IIFE that starts \'(function(){const e=$("o_risk");\' (~line 3770) with:\n' + JS_HERO + '\n'
 '(5) Data tab and text (exact strings in the diff): Model V panel and the traps panel in renderData() rewritten (coefficients with clustered SEs incl. the size x age row and the out-of-time shrink row, '
 'the rate level given the spread and staffing as not-applied rows, a note on lenders, the rate level, the spread channel with no rate entered and real-estate notes, checks: CV AUC, newer loans (vintage holdout O/E and slope), two-year forecast (O/E and slope), population level across specifications and reference periods (level_range), '
 'like-for-like incl. loans over $150k, through the cycle, timing; trap 4 rewritten with the loan-band tail range); nFit counts the new tables; LGD note says expected loss counts charge-offs by month 120; v4 table row for the SBA rate '
 '(approved incl. cancelled and undisbursed, knot uncertainty); methods list item ("if 2023-26 conditions hold", shrink); "Two traps handled" item; o_conf and footer say "acquisition loans" and "5-year risk AUC"; header comment; '
 'state-dropdown comment and label ("pts charge-off risk, 10 yr"); the masthead "Transactions fitted" (hard-coded 32,554 = 18,941 + 13,613 resolved loans) becomes 18,941 + the new loan count, and the Data-tab tally of transactions is computed as V.n_fit+R.n_fit instead of hard-coded.\n'
 '(6) Outside index.html: fit/README.md table gets rows for sba_rate (FY2025-26) and risk (sba_risk_refresh.py) and the prime note becomes "7.00%%, in effect since 2026-09-17 (Fed H.15)"; add tests/sba_risk_refresh.test.js and its fixture tests/sba_book_fy2024_26.json (the FY2024-26 book for the base_cif test; copies in /tmp/claude-0/fit5/sba_risk_refresh/); AUDIT.md entry.\n'
 'Verified on the patched copy: tests/model.test.js %s; tests/fuzz.test.js %s; tests/sba_risk_refresh.test.js %s; browser: %s; %s; renderData() and the hero tile render with no page errors and no NaN/undefined at 1440 and 390 px; value, score and close probability unchanged on six test deals.\n'
 % (TESTRES['model.test.js']['tail'][-1], TESTRES['fuzz.test.js']['tail'][-1], TESTRES['sba_risk_refresh.test.js']['tail'][-1],
    browser_summary('browser.sweep.js'), browser_summary('browser.inputs.js'))
 + 'MODELS.risk (v3): the exact object is /tmp/claude-0/fit5/sba_risk_refresh/MODELS_risk_v3.json (%d bytes, sha256 %s; the patched copy embeds the same object). '
   'The numbers fitRisk reads: age_edges %s; co.log_base %s; co.coef %s; co.age_coef %s, age_cap_months %s, age_center_years %s; co.lp_shrink %s, co.lp_shift %s; pif.log_base %s; pif.coef %s; centers %s; loan_share 0.85; loan_range %s; spread_range %s; '
   'horizon/observed/term 60/96/120 months; tail_factor %s; base_cif.term %s; lgd b0 %s, b_size %s, b_age %s, age_center_years 4, age_range %s; '
   'industry_effects, pif.sector, naics6_effects, state_effects, size_band_cif, timing, rate_level, through_cycle as in the file.'
   % (os.path.getsize(OUT + 'MODELS_risk_v3.json'), __import__('hashlib').sha256(open(OUT + 'MODELS_risk_v3.json', 'rb').read()).hexdigest(),
      *[json.dumps(v, separators=(',', ':')) for v in (RISK['age_edges'], RISK['co']['log_base'], RISK['co']['coef'], RISK['co']['age_coef'], RISK['co']['age_cap_months'],
        RISK['co']['age_center_years'], RISK['co']['lp_shrink'], RISK['co']['lp_shift'], RISK['pif']['log_base'],
        RISK['pif']['coef'], RISK['centers'], RISK['loan_range'], RISK['spread_range'], RISK['tail_factor'], RISK['base_cif']['term'],
        RISK['lgd']['b0'], RISK['lgd']['b_size'], RISK['lgd']['b_age'], RISK['lgd']['age_range'])]))
ex = BA[0] if BA else {}
hero_txt = BROWSER.get('data_tab_and_hero', {}).get('w1440', {}).get('hero', '').replace('\n', ' / ')
DATA_TAB = (
 'Hero tile "Survival risk" (fitted), example business: "%s" (was "%s (%.2fx)", resolved-only, no horizon; previous revision 3.9%% (0.67x)); tooltip: observed 5-year rate of the loan band, '
 '"Charge-offs in 2025-26 ran about %.2fx the 2023-24 rate (age-adjusted); taking either period as current puts this figure at about <p x %.2f>-<p x %.2f>. Loans written at today\'s prime may run %.0f-%.0f%% higher (rate level, not applied). Through the cycle, 7(a) loans over $150k approved 2006-08 were %.0f-%.0f%% charged off within 10 years." '
 % (hero_txt, pc_(ex.get('p_old', 0), 1), ex.get('rel_old', 0), math.exp(D25['co'][0]), COND_RANGE['h96'][0] / BASE96, COND_RANGE['h96'][1] / BASE96,
    100 * RATE_LEVEL['uplift_range'][0], 100 * RATE_LEVEL['uplift_range'][1], 100 * CYCLE['cif120_FY2006_08'][0], 100 * CYCLE['cif120_FY2006_08'][1])
 + 'Data tab, Model V: "Competing-risk hazard on %s SBA 7(a) acquisition term loans, FY2018-2026, SBA FOIA as of 2026-06-30: %s charged off, %s paid in full and %s still open, which are censored rather than dropped. ... probability with a horizon: charged off within 5 years, and within 10 years, if 2023-26 conditions hold." '
   % (format(len(d), ','), format(n_co, ','), format(n_pif, ','), format(n_open, ','))
 + 'Coefficient table, SE = largest of model-based, lender-clustered and two-way lender x quarter: ln(loan) at 4 years %.3f (%.3f), "larger loans are charged off less often"; ln(loan) x years on book to 6 %.3f (%.3f), "and later: the gap closes by year 6"; spread over prime capped at 3 %.3f (%.3f), "an association, not a lever"; '
   'franchise %.3f (%.3f, no measurable difference); sector sd %.2f; 6-digit sd %.2f; state sd %.2f; all of the above out of time x%.2f (SE %.2f), applied toward the average loan; '
   'rate level given the spread %+.2f (%.2f), %+.2f (%.2f) with approval cohorts, not applied; staffing (SBA jobs supported) %+.2f (SE %.2f) per ln(1+jobs) if fitted, "not used: SBA counts jobs created and retained, the console counts Census employees, several times more". '
   'Note: "SEs are the largest of the model-based, lender-clustered and two-way estimates ... lenders differ (between-lender sd %.2f) ... The console prices an average lender. Loans written at today\'s prime may run %.0f-%.0f%% above the level shown. '
   'With no rate entered, the spread is read off the median table for the loan size, so risk by size includes lender pricing (larger loans get lower spreads): against a model without the spread, the 8-year figure here runs x%.2f-%.2f across $100K-$4M loans. '
   'Real-estate notes: %.0f%% of SBA acquisition notes under $250K run longer than 10 years, against %.0f%% over $2M. A business-only acquisition of the same size is probably riskier than shown; SBA overwrites the term of charged-off loans, so this cannot be separated." '
   % (RISK['co']['coef']['lnamt'], RISK['co']['se']['lnamt'], RISK['co']['age_coef']['lnamt'], RISK['co']['se']['lnamt_x_age'], RISK['co']['coef']['spread'], RISK['co']['se']['spread'],
      RISK['co']['coef']['franchise'], RISK['co']['se']['franchise'], RISK['sector_tau'], RISK['naics6_sd'], RISK['state_sd'],
      GAMMA, GAMMA_SE, RATE_LEVEL['coef_calendar'][0], RATE_LEVEL['coef_calendar'][1], RATE_LEVEL['coef_calendar_cohort'][0], RATE_LEVEL['coef_calendar_cohort'][1],
      JOBS_CHECK['co_lnjobs'][0], JOBS_CHECK['co_lnjobs'][1],
      LENDER_FE['eb_sd'], 100 * RATE_LEVEL['uplift_range'][0], 100 * RATE_LEVEL['uplift_range'][1], min(_rr), max(_rr),
      100 * RE_SHARE['<250K']['share_term_over_120m'], 100 * RE_SHARE['2-5M']['share_term_over_120m'])
 + 'Checks: out-of-sample AUC at 5 years %.3f (Brier %.4f, observed/predicted %.2f; the resolved-only logistic %.3f on the same loans); newer loans (FY2018-21 -> FY2022-24, %d charge-offs): AUC %.3f, observed/predicted %.2f, slope %.2f, "under-predicted"; '
   'two-year forecast AUC %.3f, observed/predicted %.2f, slope %.2f on %d charge-offs, "over-predicted, and too spread out"; "Population level across specifications and reference periods" %s-%s within 8 years (%s shipped): specifications %s-%s, '
   'charge-offs in 2025-26 ran %.2fx the 2023-24 rate and either period as current gives %s-%s; "the shipped level is in the upper part: the two-year forecast over-predicted, and FY2024-26 approvals so far run %.1fx the model on %d charge-offs"; '
   'acquisition loans charged off within 5 years %s (8 years %s) vs startups %s and existing businesses %s, loans over $150k %s vs %s and %s; through the cycle: all 7(a) over $150k approved 2010-16 %s-%s within 10 years, 2006-08 %s-%s; '
   'charge-offs come late: median %.1f yr given charge-off within 8, %.0f%% by year 3. '
   % (RISK['validation']['cv5_auc60'], RISK['validation']['cv5_brier60'], RISK['validation']['cv5_oe60'], RISK['validation']['cv5_auc60_current'], RISK['validation']['n_events_vintage'],
      RISK['validation']['vintage_auc'], RISK['validation']['vintage_oe'], RISK['validation']['vintage_slope'],
      RISK['validation']['cal_holdout_auc'], RISK['validation']['cal_holdout_oe'], RISK['validation']['cal_holdout_slope'], RISK['validation']['n_events_cal_holdout'],
      pc_(LEVEL_RANGE['h96'][0], 1), pc_(LEVEL_RANGE['h96'][1], 1), pc_(BASE96, 1), pc_(SPEC_RANGE['h96'][0], 1), pc_(SPEC_RANGE['h96'][1], 1),
      math.exp(D25['co'][0]), pc_(COND_RANGE['h96'][0], 1), pc_(COND_RANGE['h96'][1], 1), COHORT_OE['FY2024-26']['O_over_E'], COHORT_OE['FY2024-26']['O'],
      pc_(aj_pool[60]), pc_(aj_pool[96]), pc_(lfl['startup_or_new']['cif60'], 1), pc_(lfl['existing']['cif60'], 1),
      pc_(lfl['acquisition']['cif60_loans_150k_up'], 1), pc_(lfl['startup_or_new']['cif60_loans_150k_up'], 1), pc_(lfl['existing']['cif60_loans_150k_up'], 1),
      pc_(CYCLE['cif120_FY2010_16'][0], 1), pc_(CYCLE['cif120_FY2010_16'][1], 1), pc_(CYCLE['cif120_FY2006_08'][0], 0), pc_(CYCLE['cif120_FY2006_08'][1], 0),
      TIMING['median_months_given_chargeoff_by_96'] / 12, 100 * TIMING['share_by_36_of_96'])
 + 'Four traps: TermInMonths excluded (unchanged text); open loans censored, not dropped (the resolved-only rate was %s with no horizon); COVID relief absorbed by calendar-year terms, 2023-26 used as current conditions; '
   'trap 4: "The last two years are borrowed. ... years 9-10 are borrowed from mature 7(a) loans approved 2010-15: x%.2f (small loans) to x%.2f (loans over $1.5M), partly because larger mature loans more often carry 25-year terms; x%.2f used (matched to the size of acquisition loans; SE %.2f, a judgment). The 2011-12 vintages, whose years 9-10 overlapped CARES relief, are the lowest." '
   % (pc_(RESOLVED_ONLY, 1), tail_band['<150k']['ratio'], tail_band['>=1.5M']['ratio'], TAIL, TAIL_SE)
 + 'LGD note: mean loss %s of the advance (median %s, %d loans); %s if charged off at two years, %s at seven, for a $650K note; size matters little; expected loss weights severity by timing (%s over a 10-year term, counting charge-offs by month 120; lifetime loss runs higher, by about %.0f%% on mature 7(a) loans). '
   % (pc_(LGDV['pooled_mean'], 1), pc_(LGDV['pooled_median'], 1), LGDV['n'], pc_(REFM['sev24'], 0), pc_(REFM['sev84'], 0), pc_(REFM['lgd'], 0), 100 * (tail['ratio_144_over_120_FY2010_13'] - 1))
 + 'Fitted-from-public-data row: "WSJ prime %.2f%% (since %s) + %.2f-%.2f pts, smaller loans higher | %s variable-rate change-of-ownership 7(a) loans approved FY2025-26, including cancelled and undisbursed approvals (SBA FOIA as of 2026-06-30); prime from Fed H.15; each size point +/-%.2f-%.2f pts". '
   % (PRIME_NOW, PRIME_SINCE, min(spq['values']), max(spq['values']), format(spq['n'], ','), min(SBA_RATE['spread_knots_se']), max(SBA_RATE['spread_knots_se']))
 + 'State dropdown: "<State>  (+0.12 pts charge-off risk, 10 yr)". Methods list: reported as the chance the loan is charged off within 10 years (the term) and within 5, if 2023-26 conditions hold; out-of-sample AUC %.3f at 5 years; loan-level effects shrunk x%.2f to match how they held up out of time; charge-off trails default by 1-2 years. '
   'Source line for the Data tab: SBA 7(a) FOIA as of 2026-06-30, n = %s acquisition loans (%d charge-offs); base = the console\'s pricing of %s FY2024-26 loans; SEs clustered; caveat: if 2023-26 conditions hold, the reference period alone moves the 8-year level %s-%s.'
   % (RISK['cv_auc'], GAMMA, format(len(d), ','), n_co, format(len(recent), ','), pc_(COND_RANGE['h96'][0], 1), pc_(COND_RANGE['h96'][1], 1)))
TESTS = [
 'fitRisk reproduces the Python fit on the shipped (rounded) tables to 1e-9 for 6 pinned deals: p5, p8, pTerm, lgd, expLoss, rel (rel = pTerm / base_cif.term).',
 '0 < p5 < p8 < pTerm < 0.5 for every industry and size; p === pTerm; pTerm === p8 x tail_factor; horizons 60/96/120 months.',
 'tail_factor in [1.1, 1.3], strictly between the <$150k and >=$1.5M band ratios of tail_by_band, and tail_factor_se >= 0.07 (a labelled judgment covering the band range).',
 'At the table rate, 5-year risk is non-increasing in price for every industry, and identical for all prices above the $5M loan cap.',
 'The size effect fades with time on book: co.coef.lnamt < 0 < co.age_coef.lnamt, and the $5M/$200k risk ratio is closer to 1 at 8 years than at 5.',
 'Risk strictly increases with the rate for spreads 0..3 pp over prime and is flat above prime + 3; moving prime and the rate together leaves risk unchanged (rate level not applied).',
 'Omitting the rate equals passing sbaRate(price).',
 'Population base_cif.h60 in (1%, 3.5%) and within 3 SE + 0.3 pp of the Aalen-Johansen 5-year rate; base_cif.term = h96 x tail_factor; the shipped 8-year level lies inside base_cif.spec_range and strictly inside base_cif.conditions_range (with conditions.ratio < 1); level_range spans both and is wider than 20% of h96.',
 'base_cif is what fitRisk prices: fitRisk applied to every FY2024-26 loan in tests/sba_book_fy2024_26.json (its own size, sector + 6-digit effect, state, franchise; table rate) averages base_cif.h60 and base_cif.h96 within 2%, and rel averages 1 within 2%.',
 'The reference loan ($650k note, table rate, explicit average sector with the sector tables emptied, no state) has rel in (0.8, 1.2), and rel === pTerm / base_cif.term.',
 'By loan band, the fitted model (own spreads and rate type, realised calendar) is within 2 SE of the observed (Aalen-Johansen) 5-year rate; the console version (FY2025-26 table spreads, variable note, 2023-26 conditions, shrunk) within 1.5 SE and 0.90-1.25x; fitRisk at each band\'s median loan (average sector) within 3 SE + 0.4 pp.',
 'Staffing does not enter: fitRisk gives identical p for 2 and 90 staff, and neither co.coef nor pif.coef carries lnjobs (MODELS.risk.staffing.applied === false).',
 'For realistic console inputs (every industry, $200k-$10M, 2-50 staff, table rate, national) the multiple rel stays in (0.2, 3.5).',
 'Unknown state = national; every console industry has a charge-off and a payoff sector effect; |state| and |naics6| log effects < 0.6; no charge-off hazard in the first 6 months (log_base[0] null); co.lp_shrink in (0.5, 1].',
 'Shipped coefficient SEs (co.se) are clustered: never below the Hessian SEs, and the size SE at least 1.2x its Hessian SE.',
 'Severity: b_age < 0; timing-weighted lgd in (0.4, 0.95) and not rising with size when b_size <= 0; 0 < expLoss < pTerm and expLoss = pTerm x lgd.',
 'sbaRate: prime 7.00 since 2026-09-17; spread over prime in [1.3, 2.6] and non-increasing in size; spread_knots_se reflects sample choice (max >= 0.05); the source string mentions cancelled and undisbursed approvals.',
 'model() on the example business gives finite risk.p in (0, 0.3) with risk.p5 < risk.p; for every industry, model().risk.p never rises by more than 1% as revenue grows from $300k to $40M at a fixed margin and ask multiple; value, score and close probability unchanged by the refresh.',
 'Labels: MODELS.risk.conditions === "2023-26"; the hero block says "conditions hold" and "charged off within", never "-yr term", and its tooltip reads base_cif.conditions_range; renderData reads validation.vintage_oe, validation.cal_holdout_slope, co.lp_shrink, base_cif.spec_range, conditions_range, level_range, through_cycle, rate_level.uplift_range, tail_by_band, real_estate, spread_channel and staffing; the state dropdown says "pts charge-off risk, 10 yr" and never "pts default risk".',
 'Existing suites still pass: tests/model.test.js, tests/fuzz.test.js, tests/browser.sweep.js and tests/browser.inputs.js (no NaN/undefined, no page errors), and renderData() renders the new Model V panel without errors.',
]
vc = vint_cal.set_index(['vintage', 'months'])
def _oe(fy, m): return vc.loc[(fy, m), 'observed'] / vc.loc[(fy, m), 'predicted']
def _ev(fy, m): return int(round(vc.loc[(fy, m), 'observed'] * vc.loc[(fy, m), 'n']))
COHORT = ('Cohort pattern not captured by calendar terms: FY2020 loans were charged off less than predicted at young ages (observed/predicted %.2f at 24 months; relief deferred defaults), '
          'FY2022 and FY2023 loans more (%.2f and %.2f at 24 months, on %d and %d charge-offs); over each cohort\'s whole window O/E is %s. New loans may therefore run somewhat above the 5-year figure, '
          'in the same direction as the rate-level reading; the FY2024-26 cohort so far runs below (O/E %.2f on %d charge-offs).'
          % (_oe(2020, 24), _oe(2022, 24), _oe(2023, 24), _ev(2022, 24), _ev(2023, 24),
             ', '.join('%s %.2f' % (k, v['O_over_E']) for k, v in COHORT_OE.items()), COHORT_OE['FY2024-26']['O_over_E'], COHORT_OE['FY2024-26']['O']))
CAVEATS = (
 'Transferability: this is the target population itself (US small-business acquisitions financed with SBA 7(a)), not an analog, so no shrinkage toward the old values is applied beyond the empirical-Bayes shrinkage of sector, 6-digit and state effects and the out-of-time shrink. '
 'It describes SBA-financed deals: lender underwriting has already screened them, and deals financed otherwise (seller notes only, cash, conventional or PE debt) may differ. '
 'The horizon is explicit: the old 5.69%% was a share of resolved loans, which mixes horizons and over-weights early failures and payoffs, so it is not comparable with the new 5-year (about %.1f%%) or 10-year (about %.1f%%) population figures. '
 'Conditions: the 10-year headline is labelled "if 2023-26 conditions hold". Its SEs are parameter-only (clustered); they do not cover a change in conditions (all 7(a) loans >= $150k approved FY2006-08: %.0f-%.0f%% charged off within 10 years; acquisitions ran about %.2fx all loans in FY2018-26) '
 'nor the specification and reference-period range (8-year %.1f-%.1f%%). '
 'RESPONSE TO THIS REVIEW. (1) base_cif and rel (major, both reviews): accepted, option (b). The previous shift and base were computed on the FY2024-26 book with the fixed-rate notes\' low spreads (%.1f%% of the book, mean %.2f pp) run through the variable slope; '
 'the console\'s own pricing of that book averaged %.3fx (5 yr) and %.3fx (8 yr) of base, so rel ran about 10%% high. Now co.lp_shift (%.4f, was %.4f) is solved so that fitRisk applied to every FY2024-26 loan (table spread, variable note, shrunk, own size, sector, 6-digit, state, franchise) averages the book\'s fitted 5-year level '
 '(each note at its own spread and rate type), and base_cif is that console-priced mean (%.2f%% / %.2f%% / %.2f%%). Every console hazard is x%.3f of the previous fit\'s, and rel averages 1 over the book: the shipped tables reproduce base within %.2f%% (5 yr) and %.2f%% (8 yr) in the Python mirror, '
 'and a new test runs fitRisk over all %s loans (fixture tests/sba_book_fy2024_26.json) and requires 2%%. Option (a) was not taken because it would leave the console\'s absolute level about 9%% above the fitted population level: the console does not know the note type, and the fitted fixed-rate gap is an association. '
 'The base_cif note no longer says "variable rate"; it gives the definition. The reference-loan test now uses an explicit average sector (sector tables emptied) instead of "zzz" (sector 81) and requires rel in (0.8, 1.2); the LGD display figures use the average sector too. '
 '(2) Reference period (major, review 2): accepted. With a calendar-2025-26 dummy the charge-off hazard runs x%.2f the 2023-24 rate (log %.2f, quarter-clustered SE %.2f, Hessian %.2f; LR %.1f); every quarter 2025Q2-2026Q2 sits below every 2023-24 quarter (Welch p %.3f); '
 'payoffs also slowed (%.2f, on the panel censored at 2026-03-31). Taking either period whole as current gives an 8-year level of %.1f%% (2023-24) or %.1f%% (2025-26) against %.1f%% shipped (mixed: %.1f-%.1f%%). The pooled 2023-26 level is kept, because the data cannot tell a post-relief catch-up in 2023-24 from slower SBA processing in 2025-26 '
 '(the Oct-Nov 2025 federal shutdown fell in that period; by charge-off date the largest quarterly batch is %s, %d), and base_cif carries conditions, conditions_range and level_range (8-year %.1f-%.1f%%). The Data-tab row now shows that range, not 4.4-4.8%%, and the hero tooltip gives the deal\'s own figure under either period. '
 '(3) Staffing (minor, both): accepted; dropped and both hazards refitted. With SBA JobsSupported the coefficient is %+.3f (SE %.3f Hessian, %.3f clustered previously), but the console passes Census employees per revenue, several times the SBA figure, so console hazards ran high (6-20%% as the review measured) and rose with revenue at a fixed price. '
 'Without it, ln loan is %.3f (was %.3f) and the spread %.3f (was %.3f). fitRisk keeps the jobs argument and ignores it; a test checks that risk does not move with staffing and that model().risk.p never rises with revenue at a fixed margin (16 industries, $300k-$40M); "flat above $5.9M" is now true of model() too. '
 '(4) Real estate (minor, review 2): accepted: not_identified entry and Data-tab caveat with the shares by band (%.0f%% under $250k to %.0f%% over $2M); the hero says "within 10 yrs"; the fitRisk comment and Data tab say larger loans are "charged off less often and later". '
 '(5) Spread as a second size effect (minor, review 1): the Data tab now says that with no rate entered risk by size includes lender pricing through the median spread table, and that against a model without the spread the 8-year figure runs x%.2f-x%.2f across $100k-$4M (review 1 found x0.78-x1.09 on the earlier model). '
 'The band test is tightened from 0.85-1.35x and 2.5 SE to 0.90-1.25x and 1.5 SE; the console now runs %s of the observed 5-year rates. The no-spread variant is not shipped for the no-rate case: an entered rate is informative and neither variant dominates by band. '
 '(6) Upper end (minor, review 1): the base_cif note and the Data tab say the shipped level sits in the upper part of the range; everything censored at 2025-12-31 gives %.1f%% at 8 years (%+.0f%%). '
 'Earlier rounds, kept: tail factor size-matched %.3f with judgment SE %.2f; shipped SEs the largest of Hessian, lender-clustered and two-way lender x quarter; size effect fading with loan age (LR %.1f); out-of-time shrink x%.2f (SE %.2f; vintage %.2f, calendar %.2f; in-period CV %.2f); '
 'spread knots with sample-choice uncertainty %.2f-%.2f pp; sector variance re-estimated in every validation split; SBA maximum-spread check (%.2f%% above). '
 'COVID relief (CARES s.1112 and the 2021 extension paid P&I for months on FY2018-21 loans) and PPP/EIDL depressed charge-offs in 2020-22. Calendar-year terms absorb it (LR %.1f), and the 2023-26 level is used as current conditions. '
 'Charge-off dates are administrative and lag default by 1-2+ years, so these are charge-off, not default, probabilities. '
 'Calibration varies by split: observed/predicted %.2f in CV, %.2f for new vintages (under-predicted) and %.2f for the two-year forecast (over-predicted). '
 'The note is assumed to be 85%% of the price (sbaRate convention), priced as a variable note at the table spread; fixed-rate notes carry a lower fitted hazard (%.2f log level, SE %.2f, and a flatter spread slope), absorbed into the level shift rather than priced. '
 'Severity is gross of recoveries and measured on the original advance; the timing weighting extrapolates severity at ages 96-120 months from the clamp at 96; expLoss counts charge-offs by month 120 only. '
 'FY2026 covers Oct 2025 to Jun 2026 only; 164 possible split or duplicate loans were kept; revolvers (%s disbursed) are excluded. '
 'The next FOIA snapshot (2026-09-30) was not yet posted when this was fitted.'
 % (100 * BASE60, 100 * BASE_TERM, 100 * CYCLE['cif120_FY2006_08'][0], 100 * CYCLE['cif120_FY2006_08'][1], CYCLE['acq_to_all_150k_ratio_cif60'], 100 * LEVEL_RANGE['h96'][0], 100 * LEVEL_RANGE['h96'][1],
    100 * BASE_DIAG['fixed_share'], BASE_DIAG['fixed_mean_spread'], *BASE_DIAG['previous_definition']['console_over_base'], LP_SHIFT, BASE_DIAG['previous_definition']['shift'],
    100 * BASE60, 100 * BASE96, 100 * BASE_TERM, BASE_DIAG['hazard_multiple_vs_previous_shift'], 100 * abs(BOOK_CHECK['p5_over_h60'] - 1), 100 * abs(BOOK_CHECK['p8_over_h96'] - 1), format(len(recent), ','),
    math.exp(D25['co'][0]), D25['co'][0], D25['co'][2], D25['co'][1], D25['lr_co'], QDIAG['welch_p'], D25['pif'][0],
    100 * COND['2023-24 charge-off and payoff conditions']['h96'], 100 * COND['2025-26 charge-off and payoff conditions (payoffs to 2026-03-31)']['h96'], 100 * BASE96,
    100 * COND_RANGE['mixed_h96'][0], 100 * COND_RANGE['mixed_h96'][1], QDIAG['largest_batch'][0], QDIAG['largest_batch'][1], 100 * LEVEL_RANGE['h96'][0], 100 * LEVEL_RANGE['h96'][1],
    JOBS_CHECK['co_lnjobs'][0], JOBS_CHECK['co_lnjobs'][1], 0.062, cot.loc['lnamt', 'est'], JOBS_CHECK['co_core_with_jobs']['lnamt'], cot.loc['spread', 'est'], JOBS_CHECK['co_core_with_jobs']['spread'],
    100 * RE_SHARE['<250K']['share_term_over_120m'], 100 * RE_SHARE['2-5M']['share_term_over_120m'], min(_rr), max(_rr),
    ', '.join('%.2fx' % v for v in BAND_CONSOLE_RATIO.values()),
    100 * SPEC_BASE['everything censored at 2025-12-31']['h96'], 100 * (SPEC_BASE['everything censored at 2025-12-31']['h96'] / BASE96 - 1),
    TAIL, TAIL_SE, -spec['-lnamt_x_age (proportional size effect)']['lr_vs_main'], GAMMA, GAMMA_SE, SLOPE_V['gamma'], SLOPE_C['gamma'], VAL['cv5_slope_loan_level']['pooled'],
    min(SBA_RATE['spread_knots_se']), max(SBA_RATE['spread_knots_se']), 100 * frac_above_cap,
    -spec['no_calendar_terms']['lr_vs_main'], cvf['O_over_E'], vh['new_full']['O_over_E'], ch['new_full']['O_over_E'],
    cot.loc['fixed', 'est'], cot.loc['fixed', 'se_shipped'], format(excl['revolvers_dropped'], ',')))
if BA_DECOMP:
    _e = BA_DECOMP[0]
    CAVEATS += (' Example business (medical, $3.48M note): the 10-year headline moves from %s (old resolved-only logistic, no horizon) to %s. With the previous tail factor it would be %s; '
                'without the out-of-time shrink %s; without the shrink and with the size effect held at its 4-year value at all ages %s (the first fit shipped 2.07%%; the previous revision 3.86%%, rel 0.67). '
                'The largest single step is the %s; for $2-5M loans the in-sample O/E at 60+ months was %.2f under a proportional size effect and %.2f now.'
                % (pc_(_e['old'], 2), pc_(_e['shipped'], 2), pc_(_e['old_tail'], 2), pc_(_e['no_shrink'], 2), pc_(_e['no_shrink_no_size_age'], 2),
                   max([('size effect fading with loan age', abs(_e['no_shrink'] - _e['no_shrink_no_size_age'])),
                        ('out-of-time shrink', abs(_e['shipped'] - _e['no_shrink'])),
                        ('tail factor', abs(_e['shipped'] - _e['old_tail']))], key=lambda t: t[1])[0],
                   float(band_age[(band_age.model == 'proportional size effect') & (band_age.band == '2-5M') & (band_age.age_months == '60+')].O_over_E.iloc[0]),
                   float(band_age[(band_age.model == 'size effect fading to 72 months (shipped)') & (band_age.band == '2-5M') & (band_age.age_months == '60+')].O_over_E.iloc[0])))
CAVEATS = CAVEATS + ' ' + COHORT.strip()
RESULT = {'name': 'sba_risk_refresh', 'script': '/home/user/last-minute/fit/sba_risk_refresh.py', 'parameters': PARAMS, 'not_identified': NOT_ID,
          'implementation': IMPL, 'data_tab_text': DATA_TAB, 'test_invariants': TESTS, 'caveats': CAVEATS}
for prm in PARAMS:
    for k in ['param', 'current_value', 'fitted_value', 'se', 'n', 'method', 'validation', 'recommended_value']:
        prm[k] = str(prm[k])
json.dump(RESULT, open(OUT + 'RESULT.json', 'w'), indent=1)
say('\nwrote RESULT.json (%d parameters)  total %.0fs' % (len(PARAMS), time.time() - T0))
