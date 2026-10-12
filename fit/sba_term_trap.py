#!/usr/bin/env python3
"""The TermInMonths leak, measured on the population the shipped survival-risk model is fitted to. October 2026
(AUDIT_FINDINGS R3-9).

Run:  python3 -I /home/user/last-minute/fit/sba_term_trap.py
Out:  /tmp/claude-0/fit5/sba_term_trap/RESULT.json   (embedded as MODELS.risk.term_trap)

The Data tab quoted the leak from the superseded 13,613-loan resolved logistic (86.9% / 13.0% standard terms, AUC
0.957). This recomputes it on the hazard model's loans: SBA 7(a) change-of-ownership loans FY2018-26, the same
filter as fit/sba_risk_refresh.py (paid in full, charged off or open; not revolvers; a positive rate; spread over
prime between -2 and 10 points). The spread here is the clean file's (prime on the approval date); the risk script
re-keys it to the month-start prime, which moves the filter's edge by about one loan, so n can differ by 1.
  - share of loans carrying a standard contractual term (60, 84, 120 or 300 months), by status;
  - the most common recorded terms among charged-off loans;
  - how well TermInMonths alone separates charged-off from paid-in-full loans (AUC, Mann-Whitney).
"""
import json, os
import numpy as np, pandas as pd
from scipy import stats

SRC = '/tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv'
OUT = '/tmp/claude-0/fit5/sba_term_trap'
os.makedirs(OUT, exist_ok=True)
STD = [60, 84, 120, 300]
raw = pd.read_csv(SRC, low_memory=False, usecols=['LoanStatus', 'months_on_book', 'RevolverStatus', 'InitialInterestRate',
                                                   'spread_over_prime', 'TermInMonths', 'term_is_standard'])
d = raw[raw.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (raw.months_on_book >= 0) & (raw.RevolverStatus == 0)
        & raw.InitialInterestRate.gt(0) & raw.spread_over_prime.between(-2, 10)].copy()
d['std'] = d.TermInMonths.isin(STD)
by = {s: dict(n=int((d.LoanStatus == s).sum()), standard_term_share=round(float(d.loc[d.LoanStatus == s, 'std'].mean()), 4),
              flag_share=round(float(d.loc[d.LoanStatus == s, 'term_is_standard'].astype(float).mean()), 4))
      for s in ['PIF', 'CHGOFF', 'EXEMPT']}
co_terms = d.loc[d.LoanStatus == 'CHGOFF', 'TermInMonths'].value_counts().head(6)
res = d[d.LoanStatus.isin(['PIF', 'CHGOFF'])]
y = (res.LoanStatus == 'CHGOFF').values
u = stats.mannwhitneyu(-res.TermInMonths.values[y], -res.TermInMonths.values[~y], alternative='two-sided').statistic
auc = float(u / (y.sum() * (~y).sum()))                    # P(a charged-off loan records a shorter term than a paid one)
R = dict(n=int(len(d)), standard_terms=STD, by_status=by,
         chgoff_most_common_terms=[[int(k), int(v)] for k, v in co_terms.items()],
         chgoff_median_term=float(d.loc[d.LoanStatus == 'CHGOFF', 'TermInMonths'].median()),
         pif_median_term=float(d.loc[d.LoanStatus == 'PIF', 'TermInMonths'].median()),
         auc_term_alone_resolved=round(auc, 3),
         note='TermInMonths is excluded from the hazard model; these figures describe the leak on its population')
json.dump(R, open(OUT + '/RESULT.json', 'w'), indent=1)
print(json.dumps(R, indent=1))
