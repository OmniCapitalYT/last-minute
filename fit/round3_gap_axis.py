#!/usr/bin/env python3
"""The axis of Pepperdine's valuation-gap distribution (MODELS.fitted.gap_axis), October 2026, third round.

Run:  python3 -I fit/round3_gap_axis.py [readings.csv] [reports.csv] [index.html] [out.json]
      defaults: fit/data_round3/pepperdine_ib_valuation_gap.csv, fit/data_round3/pepperdine_reports.csv,
      index.html (read only, for the shares the console already ships), /tmp/claude-0/fit8/out/gap_axis/RESULT.json
Data: the investment-bank survey of the Pepperdine Private Capital Markets reports 2017-2026, "valuation gap in pricing for
      transactions that didn't close" (one figure a year; the page and figure of each reading are in the CSV). The PDFs
      come from the Internet Archive's copies of digitalcommons.pepperdine.edu (the live endpoint is behind a bot
      challenge, which was not bypassed); each PDF's digest is in pepperdine_reports.csv. Fetch:
        curl -L -o pcm2025.pdf '<wayback_url from pepperdine_reports.csv>'
      The readings were transcribed from the pie labels and checked against the rendered pages by an independent reviewer.

Why
  The console's penalty for pricing above value reads Pepperdine's distribution of the gaps at which price-killed deals
  died, with the buckets 1-10%, ..., 41-50%, >50% placed at gaps of 10, 20, ..., 50 and 100 PERCENT OF VALUE. Pepperdine
  defines the gap as a percentage of the seller's ASKING PRICE (PCM 2025, PDF p.62: "For transactions that did not close,
  respondents estimated the valuation gap between buyer and seller as a percentage of the seller's asking price"; the 2026
  report repeats the sentence). With the offer at the value the console compares the ask with, a gap of p of the ask is
  ask/value = 1/(1-p), a gap over value of g = p/(1-p): the bucket edges 10/20/30/40/50% of the ask sit at 11.1, 25.0,
  42.9, 66.7 and 100% over value. Read on the wrong axis, the penalty arrived too early: at 1.5x value (a gap of 33% of
  the ask, inside the 31-40% bucket) the console charged the share of price-killed deals that died at gaps up to 50%.

What it does
  1. The bucket edges on the stated axis, g = p/(1-p).
  2. The shares: per-vintage normalised shares, their equal-weight pool over 2017-2026 with between-vintage SEs, and the
     largest difference from the shares the console ships (a check: the console's shares stay; they are within it).
  3. The open ">50%" bucket (gaps above half the ask, more than 100% over value) is not resolved by the survey. The console
     places its mass at a knot of 200% over value, twice the last edge, as it placed it at twice the old last edge
     (judgment). Checks: logit-t and logit-normal fits of the pooled shares, and where they put the open bucket's median.
Out:  RESULT.json, key js_table = MODELS.fitted.gap_axis (one line to embed).
"""
import sys, json, csv, math, re, os
import numpy as np
from scipy import optimize, stats

here = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:] + [None] * 4
RD = a[0] or os.path.join(here, 'data_round3', 'pepperdine_ib_valuation_gap.csv')
RP = a[1] or os.path.join(here, 'data_round3', 'pepperdine_reports.csv')
HT = a[2] or os.path.join(here, '..', 'index.html')
OUT = a[3] or '/tmp/claude-0/fit8/out/gap_axis/RESULT.json'

B = ['1-10', '11-20', '21-30', '31-40', '41-50', '>50']
P_EDGE = [.10, .20, .30, .40, .50]                       # bucket upper edges, share of the asking price
G_EDGE = [round(100 * p / (1 - p), 3) for p in P_EDGE]   # the same edges over value, %
OPEN_KNOT = 200.0                                        # judgment: twice the last edge, as the old axis had it

rows = list(csv.DictReader(open(RD)))
years = sorted({int(r['year']) for r in rows})
M = np.zeros((len(years), len(B)))
for r in rows: M[years.index(int(r['year'])), B.index(r['bucket_pct_of_ask'])] = float(r['share_pct'])
S = M / M.sum(1, keepdims=True)                          # rows sum to 99-101 as printed: normalise each vintage
n_ib = {int(r['year']): int(r['ib_respondents']) for r in csv.DictReader(open(RP))}
pool = S.mean(0); se = S.std(0, ddof=1) / math.sqrt(len(years))
w = np.array([n_ib[y] for y in years], float); pool_w = (S * w[:, None]).sum(0) / w.sum()

# the shares the console ships (MODELS.close_and_timing.close_probability.valuation_gap_distribution)
html = open(HT, encoding='utf-8').read()
m = re.search(r'"valuation_gap_distribution":(\{[^}]*\})', html)
console = json.loads(m.group(1)) if m else None
cvec = np.array([console[k] for k in B]) if console else None
diff = (pool - cvec / cvec.sum()) if console else None

# checks for the open bucket: fits of the pooled shares on the logit of the share of the ask
logit_edges = np.log(np.array(P_EDGE) / (1 - np.array(P_EDGE)))
def cells(th, fam):
    mu, s = th[0], math.exp(th[1])
    z = np.r_[-np.inf, (logit_edges - mu) / s, np.inf]
    if fam == 'logit_t': return np.diff(stats.t.cdf(z, math.exp(th[2]) + .5))
    return np.diff(stats.norm.cdf(z))
def fit(fam, N=500.):
    x0 = [math.log(.25 / .75), math.log(.5)] + ([math.log(2.)] if fam == 'logit_t' else [])
    r = optimize.minimize(lambda th: -np.sum(N * pool * np.log(np.clip(cells(th, fam), 1e-300, 1))), x0,
                          method='Nelder-Mead', options=dict(xatol=1e-10, fatol=1e-12, maxiter=40000))
    th = r.x; mu, s = th[0], math.exp(th[1])
    dist = (stats.t(math.exp(th[2]) + .5) if fam == 'logit_t' else stats.norm())
    # the open bucket (p > .5, g > 100%): median of its mass, as a ratio ask/value = 1 + g
    p_open = dist.sf((0 - mu) / s)                       # logit(.5) = 0
    z_med = dist.isf(p_open / 2)                         # halfway into the open mass
    g_med = math.exp(mu + s * z_med)                     # odds p/(1-p) = g
    return {'fitted': dict(zip(B, [round(x, 4) for x in cells(th, fam)])), 'open_mass': round(float(p_open), 4),
            'open_median_pct_over_value': round(100 * g_med, 1)}
checks = {fam: fit(fam) for fam in ('logit_t', 'logitnormal')}

table = {
    'definition': "the gap between buyer and seller as a percentage of the seller's asking price (Pepperdine PCM 2025, PDF p.62, and 2026, PDF p.64)",
    'bridge': 'with the offer at value, a gap of p of the ask is ask/value = 1/(1-p), a gap over value of g = p/(1-p)',
    'edges_pct_of_ask': [10, 20, 30, 40, 50],
    'knots_pct_over_value': G_EDGE,
    'open_knot': OPEN_KNOT,
    'open_note': ('the open >50% bucket (above half the ask, more than 100% over value) is not resolved by the survey: its mass is '
                  'placed at a knot of 200% over value, twice the last edge (judgment, as the old axis placed it at twice its last '
                  "edge). Fits of the pooled shares put the open bucket's median at {}% (logit-t) and {}% (logit-normal) over value"
                  .format(checks['logit_t']['open_median_pct_over_value'], checks['logitnormal']['open_median_pct_over_value'])),
    'was': {'knots_pct_over_value': [10, 20, 30, 40, 50], 'open_knot': 100},
    'pool': {'vintages': [years[0], years[-1]], 'n_vintages': len(years), 'shares': dict(zip(B, [round(float(x), 4) for x in pool])),
             'se': dict(zip(B, [round(float(x), 4) for x in se])),
             'respondent_weighted': dict(zip(B, [round(float(x), 4) for x in pool_w]))},
    'shares_check': ({'max_abs_diff_vs_shipped': round(float(np.abs(diff).max()), 4),
                      'note': 'the shipped shares (valuation_gap_distribution) are kept: the 2017-2026 pool is within .013 of them'}
                     if console else None),
    'checks': checks,
    'tier': 'aggregate (the axis is Pepperdine\'s stated definition; the open knot is judgment)',
    'source': 'Pepperdine Private Capital Markets reports 2017-2026, investment-bank survey, "Valuation gap in pricing for '
              'transactions that didn\'t close" (Internet Archive copies of digitalcommons.pepperdine.edu; fit/data_round3/)',
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
res = {'js_table': table, 'js_line': 'MODELS.fitted.gap_axis=' + json.dumps(table, separators=(',', ':')) + ';',
       'shares_by_year': {str(y): dict(zip(B, [round(float(x), 4) for x in S[i]])) for i, y in enumerate(years)}}
json.dump(res, open(OUT, 'w'), indent=1)
print('knots over value:', G_EDGE, '| open knot', OPEN_KNOT)
print('pool 2017-2026:', table['pool']['shares'])
print('se:', table['pool']['se'])
if console: print('max |pool - shipped| =', table['shares_check']['max_abs_diff_vs_shipped'])
for fam, c in checks.items(): print(fam, 'open mass', c['open_mass'], 'open median', c['open_median_pct_over_value'], '% over value')
print('wrote', OUT)
