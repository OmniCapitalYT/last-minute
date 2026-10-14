#!/usr/bin/env python3
"""Checks on the peer-table fields that stay judgment: strategic interest (IND.strat) and typical buyer pools
(IND.buyers). October 2026, second round.

Run:  python3 -I /home/user/last-minute/fit/peer_checks.py
Out:  /tmp/claude-0/fit6/out/peer_checks/RESULT.json (js_table = MODELS.fitted.peer_checks)

Why
  The research round found no source that measures either field for small businesses by industry, so both stay
  judgment. What it did find is recorded here, so the Data tab can quote it from a table instead of typing it:
  - strat: vendor M&A trackers (Capstone Partners sector updates; counts from the Datawrapper tables behind their
    charts) see only institutional deals. Their pure-strategic share by sector and their strategic-plus-add-on share
    are stored with the rank correlation against the console's hand-set values. A crude ratio of institutional to
    SBA-financed acquisitions (SBA 7(a) change-of-ownership loans) is stored too: the only measure that touches the
    small-business population, ordering only.
  - buyers: Axial's Q4 2025 SMB M&A Pipeline ranks seven sectors by pursuit rate (bar lengths measured from the
    published infographic); its rank correlation with the console's typical pools, and Axial's per-deal levels for
    lower-middle-market banks and for brokers, are stored.
  Nothing here is read by the model.

Data (all produced by the research round's own scripts; see /tmp/claude-0/fit6/research/D-tail-comps-strat-buyers.md)
  /tmp/claude-0/fit6/work/D-tail-comps-strat-buyers/out/strat_capstone_pooled.csv  (Capstone Partners, capstonepartners.com
     WordPress REST API and datawrapper.dwcdn.net/<id>/<ver>/dataset.csv, read 2026-10)
  /tmp/claude-0/fit6/work/D-tail-comps-strat-buyers/out/checks_buyers_strat.json   (Axial pages via the Wayback Machine;
     SBA FOIA change-of-ownership extract /tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv)
"""
import csv, json, os, sys
OUT = '/tmp/claude-0/fit6/out/peer_checks'
os.makedirs(OUT, exist_ok=True)
D = '/tmp/claude-0/fit6/work/D-tail-comps-strat-buyers/out'
from statistics import mean

def spearman(a, b):
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j+1]] == v[o[i]]: j += 1
            for k in range(i, j+1): r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b); ma, mb = mean(ra), mean(rb)
    num = sum((x-ma)*(y-mb) for x, y in zip(ra, rb))
    den = (sum((x-ma)**2 for x in ra) * sum((y-mb)**2 for y in rb)) ** .5
    return num / den

rows = list(csv.DictReader(open(os.path.join(D, 'strat_capstone_pooled.csv'))))
# the primary sectors map to one console industry each; proxies (software, distribution, landscaping) and the SEG text row are kept apart
PRIMARY = {'HVAC services', 'Construction services', 'Automotive aftermarket', 'HR & staffing services', 'E-commerce',
           'Metals / precision manufacturing', 'Restaurants', 'Accounting services'}
prim = [r for r in rows if r['sector'] in PRIMARY]
ss = [float(r['strategic_share']) for r in prim]
cur = [float(r['current_strat']) for r in prim]
sa = [float(r['synergy_bearing_share']) for r in prim if r['synergy_bearing_share']]
chk = json.load(open(os.path.join(D, 'checks_buyers_strat.json')))

def axial_levels():
    """Per-deal levels parsed from the two Axial pages' text (saved by the research round from Wayback captures
    20260511121943 and 20260216085038)."""
    import re
    num = lambda t: int(t.replace(',', ''))
    lg = open(os.path.join(D, 'axial_league_q1_2026.txt'), encoding='utf-8').read()
    bf = open(os.path.join(D, 'axial_brokerfest.txt'), encoding='utf-8').read()
    d1 = num(re.search(r'marketed ([0-9,]+) of those deals', lg).group(1))
    m = re.search(r'matched with ([0-9,]+) recommended buyers and received a total of ([0-9,]+) buyer pursuits', lg)
    inv1, pur1 = num(m.group(1)), num(m.group(2))
    d2 = num(re.search(r'In total, ([0-9,]+) qualified deals', bf).group(1))
    m = re.search(r'there were ([0-9,]+) recommendations .*? and ([0-9,]+) pursuits', bf)
    inv2, pur2 = num(m.group(1)), num(m.group(2))
    return {"lmm_deals": d1, "lmm_invited_per_deal": round(inv1 / d1), "lmm_pursuits_per_deal": round(pur1 / d1),
            "broker_deals": d2, "broker_invited_per_deal": round(inv2 / d2), "broker_pursuits_per_deal": round(pur2 / d2, 1),
            "source": "Axial: Top 25 lower-middle-market investment banks Q1 2026 (%d deals, %s buyers recommended, %s pursuits) and Brokerfest broker deals ($1M+ EBITDA; %d deals, %s recommendations, %s pursuits), read through the Wayback Machine" % (d1, f"{inv1:,}", f"{pur1:,}", d2, f"{inv2:,}", f"{pur2:,}")}
inst = chk['inst_vs_sba']
ax = chk['axial_vs_buyers']
table = {
  "strat": {
    "capstone": {"sectors": len(prim), "deals": int(sum(float(r['n_deals']) for r in prim)),
                 "strategic_share_range": [round(min(ss), 2), round(max(ss), 2)],
                 "strategic_plus_addon_range": [round(min(sa), 2), round(max(sa), 2)],
                 "spearman_vs_console": round(spearman(ss, cur), 2),
                 "population": "announced institutional M&A in each sector (Capital IQ and similar trackers): individual buyers are not in it",
                 "by_industry": {r['ind']: round(float(r['strategic_share']), 3) for r in prim}},
    "inst_vs_sba": {"spearman_vs_console": round(inst['spearman'], 2), "n": inst['n'],
                    "share": {r['ind']: r['ratio_inst_share'] for r in inst['rows']},
                    "note": "institutional deals a year over institutional plus SBA-financed acquisitions: coverage differs, ordering only"},
    "verdict": "judgment: no source measures the strategic share of the buyers of small businesses by industry"},
  "buyers": {
    "axial_pursuit_rank": {"sectors": len(chk['axial_pursuit_index']), "industries_mapped": ax['n'],
                           "spearman_vs_console": round(ax['spearman'], 2),
                           "population": "Axial lower-middle-market deals, Q4 2025: pursuit rate (share of invited buyers who register interest), not buyers contacted"},
    "levels": axial_levels(),
    "verdict": "judgment: no source counts the qualified buyers contacted per listing by industry"},
  "source": "fit/peer_checks.py: Capstone Partners sector M&A updates (Datawrapper tables), SBA 7(a) FOIA change-of-ownership loans FY2018-26, Axial SMB M&A Pipeline Q4 2025 and Axial league and Brokerfest pages",
  "method": "check only; nothing here is read by the model"}
res = {"name": "peer_checks", "js_key": "peer_checks", "js_table": table}
open(os.path.join(OUT, 'RESULT.json'), 'w').write(json.dumps(res, indent=1, sort_keys=True))
print(json.dumps(table, sort_keys=True)[:1500])
