#!/usr/bin/env python3
"""Held-out score of the pairing the console actually uses for the thin-pool factor. October 2026 (AUDIT_FINDINGS R2-3).

Run:  python3 -I /home/user/last-minute/fit/competition_heldout_poisson.py      (after fit/competition_buyers.py; seconds)
Out:  /tmp/claude-0/fit5/competition_buyers/heldout_poisson.json

fit/competition_buyers.py scores, on leave-one-quarter-out IBBA offer histograms, the zero-truncated negative binomial
it calibrates ENG_SHARE with (-1.588 per deal) against a Poisson on the same size gradient whose scale is refitted to
the counts (0.255, 39% above ENG_SHARE: -1.702). The Data tab called that second figure 'a Poisson at the same scale'.
The console keeps the Poisson SHAPE for the thin-pool factor but at the NB's scale, ENG_SHARE = 0.184. This scores that
pairing directly, with the scale taken from each fold's NB fit and, for reference, fixed at the shipped 0.184, next to
the old judgment scale 0.34. It reuses competition_buyers.py's data loader, likelihoods and fitting code unchanged,
and the band gradient g_b that script wrote to offers_by_band.csv.
"""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # the fit/ directory (trusted code, not downloaded data)
import competition_buyers as cb

ENG_SHIPPED, ENG_OLD = 0.184, 0.34
gb = pd.read_csv(os.path.join(cb.OUT, "offers_by_band.csv")).g_model.values
o = cb.load_offer_hist()
qs = sorted(o.period.unique())
th5, _, _ = cb.fit_model(o, "M5", g=gb)
th5p, _, _ = cb.fit_model(o, "M5P", g=gb)
tot = dict(nb=0.0, poisson_own_scale=0.0, poisson_at_fold_nb_scale=0.0, poisson_at_shipped_scale=0.0, poisson_old_judgment=0.0)
per_q = []
W = 0.0
for q in qs:
    tr, te = o[o.period != q], o[o.period == q]
    k, op, w, b = te.k.values, te.open.values, te.w.values, te.b.values
    t5, _, _ = cb.fit_model(tr, "M5", g=gb, start=th5)
    t5p, _, _ = cb.fit_model(tr, "M5P", g=gb, start=th5p)
    m5, r5 = cb.band_params("M5", t5, gb)
    ll = dict(nb=np.sum(w * cb.cell_logp(k, op, m5[b], r5[b])),
              poisson_own_scale=np.sum(w * cb.cell_logp_pois(k, op, (np.exp(t5p[0]) * gb)[b])),
              poisson_at_fold_nb_scale=np.sum(w * cb.cell_logp_pois(k, op, m5[b])),
              poisson_at_shipped_scale=np.sum(w * cb.cell_logp_pois(k, op, (ENG_SHIPPED * gb)[b])),
              poisson_old_judgment=np.sum(w * cb.cell_logp_pois(k, op, (ENG_OLD * gb)[b])))
    for kk, v in ll.items():
        tot[kk] += float(v)
    W += float(w.sum())
    per_q.append(dict(quarter=q, n=float(w.sum()), **{kk: float(v / w.sum()) for kk, v in ll.items()}))
res = dict(per_deal={kk: round(v / W, 4) for kk, v in tot.items()},
           full_sample=dict(nb_scale=round(float(np.exp(th5[0])), 4), nb_r=round(float(np.exp(th5[1])), 3),
                            poisson_own_scale=round(float(np.exp(th5p[0])), 4)),
           quarters=qs, per_quarter=per_q, deals=round(W),
           note="leave-one-quarter-out log-likelihood per deal on IBBA's offers-per-closed-deal histograms; the console's thin-pool "
                "factor is the Poisson shape at the NB scale (poisson_at_fold_nb_scale out of sample, poisson_at_shipped_scale at 0.184)")
json.dump(res, open(os.path.join(cb.OUT, "heldout_poisson.json"), "w"), indent=1)
print(json.dumps(res["per_deal"]), json.dumps(res["full_sample"]))
