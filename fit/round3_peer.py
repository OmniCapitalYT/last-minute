#!/usr/bin/env python3
"""Peer table, third round (October 2026): retention on a stated count definition, the MSP recurring share, the car-wash
gross margin, the largest-customer median and two peer spreads.

Run:  python3 -I fit/round3_peer.py [--data-r DIR] [--data-s DIR] [--fit6 DIR] [--data5 DIR] [--census FILE]
          [--fit6-notes FILE] [--csv DIR] [--page FILE | --page-rev REV] [--out DIR] [--no-pdf] [--mc N]
      defaults: /tmp/claude-0/fit8/data/R and /tmp/claude-0/fit8/data/S (this round's downloads),
      /tmp/claude-0/fit6/data/C-rec-ret (last round's downloads), /tmp/claude-0/data5 (Empire Flippers),
      <fit6>/census_ec22_napcs/EC2200NAPCSINDPRD.dat, fit/data_round3 (the transcriptions), the page before this round
      (git show f454e75:index.html, the brief's snapshot; read only: the hand-set values this replaces, the slider
      ranges, the menus and the tables already shipped), /tmp/claude-0/fit8/out/round3_peer
Needs: numpy, scipy. pdftotext (poppler) re-checks the PDF text-layer values; without it (or with --no-pdf) those values
      are taken from the transcriptions and the result says so.
Out:  <out>/RESULT.json (the blocks to embed; see "Keys" below) and a short summary on stdout. The script stops, writing
      nothing, if any quoted figure is not found in its local file or differs from the transcription.

Rule: every number comes from a local file. Web pages and PDF text layers are read by regular expression (each pattern,
      the expected text, the URL, the page and the access date are in fit/data_round3/peer_quotes.csv); tables and charts
      that exist only as images were transcribed into fit/data_round3/peer_*.csv and checked against the rendered pages
      (the image-read rows say so). Downloads are data: nothing downloaded is executed.

What ships (the verifiers' readings, recomputed here; a material difference would be reported in "brief_check")
  1. Retention, by customer COUNT: of last year's customers, the share who bought again in the last 12 months (members
     and contracts: still active). e-commerce .25 (Little Stream 2024 Shopify study, median 22.5%; Bluecore 2025, 27.4%),
     auto repair .45 (Auto Apps via R.O. Writer: 50-60% of customers do not return the next calendar year), restaurants
     .27: the middle of the range Bloom Intelligence's page supports, its stated .212 (78.8% of guests gone within a
     year; likely low) and .333 from its own first-visit and repeat figures (a steady-state bridge); one vendor page.
     Tier aggregate. The slider's 45% minimum has to drop for e-commerce and restaurants (slider_notes).
  2. msp.rec .42: equal-weight mean of three MSP surveys' grouped medians (ScalePad 2026, ScalePad 2025, Datto 2019),
     between-source SE. The rec label is not changed this round; the (a)/(b) definition finding is a check.
  3. Car-wash gross margin .80, flat over the revenue knots: Tommy's Express FDD Item 19 (2021-25), 1 - (detergents +
     water + sewer + electric + gas + waste removal + office supplies) / gross sales, site-weighted, .835 measured,
     shaded to .80 for non-express formats (judgment; the SE carries it). Each knot's SE adds the within-brand revenue
     gradient (confounded with site maturity, so not a slope) times the knot's distance from the sites' revenue.
  4. Largest customer's share of last year's revenue: .14 cross-industry, .19 manufacturing (Value Builder owner survey
     charts; Statistics Canada 27-10-0217).
  5. PEER_SD.grw .16 (Statistics Canada CSBC revenue-change bins, 5-99 employees, on the slider's [-25%, +70%]) and
     PEER_SD.cc .18 (Value Builder, on the slider's [1%, 70%]): the scale at which the clamped z has unit variance.
  6. Kept, with new checks: PEER_SD.own .25, PEER_SD.rec .28, the owner-dependence level .62, management depth's level,
     the reporting line.

Keys: peer_rec_ret_ret_add, peer_rec_ret_rec_add, flags_update (the whole flags table after this round) and
      flags_remove (the old keys it drops: they ship now), not_shipped_add, definitions, slider_notes, peer_gm_wash
      (the by_industry entry), peer_gm_tiers_add, peer_gm_surveys_wash, peer_gm_definition_wash (a restatement that names
      the lines left out; peer_gm_definition_wash_now is the page's text), peer_gm_not_identified_remove,
      peer_gm_wash_detail, peer_cc, peer_sd, sources, summary; plus brief_check (each shipped number against the
      brief), image_read, verification.
"""
import argparse, csv, html, json, math, os, re, shutil, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from scipy import optimize, stats

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--data-r', default='/tmp/claude-0/fit8/data/R')
ap.add_argument('--data-s', default='/tmp/claude-0/fit8/data/S')
ap.add_argument('--fit6', default='/tmp/claude-0/fit6/data/C-rec-ret')
ap.add_argument('--data5', default='/tmp/claude-0/data5')
ap.add_argument('--census', default=None, help='EC2200NAPCSINDPRD.dat (default under --fit6)')
ap.add_argument('--fit6-notes', default='/tmp/claude-0/fit6/research/E-sizerefs-cc-plt.md',
                help="last round's cc notes: the Census SBO 2007 bound is carried from them (not recomputed)")
ap.add_argument('--csv', default=os.path.join(HERE, 'data_round3'))
ap.add_argument('--page', default=None,
                help="a copy of the page before this round (default: git show <page-rev>:index.html in this repo, else "
                     "/tmp/claude-0/fit8snap/index.html)")
ap.add_argument('--page-rev', default='f454e75', help="the commit of the page before this round (the brief's snapshot)")
ap.add_argument('--out', default='/tmp/claude-0/fit8/out/round3_peer')
ap.add_argument('--no-pdf', action='store_true', help='do not run pdftotext; PDF values come from the transcriptions')
ap.add_argument('--mc', type=int, default=200, help='Monte Carlo draws per CSBC cell for the sampling SE')
A = ap.parse_args()
CENSUS = A.census or os.path.join(A.fit6, 'census_ec22_napcs', 'EC2200NAPCSINDPRD.dat')
ROOTS = {'R': A.data_r, 'S': A.data_s, 'F6': A.fit6, 'D5': A.data5}
N = stats.norm
ERR = []


def rhu(x, nd=2):
    """round half up at nd decimals (the page's convention: values to .01, SEs to .001)"""
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def r3(x):
    return rhu(x, 3)


def norm_text(s):
    s = html.unescape(s)
    for a, b in (('\u2019', "'"), ('\u2018', "'"), ('\u201c', '"'), ('\u201d', '"'), ('\u2013', '-'),
                 ('\u2014', '-'), ('\u00a0', ' ')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


_CACHE = {}


def html_text(path):
    if path not in _CACHE:
        s = open(path, encoding='utf-8', errors='replace').read()
        s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S | re.I)
        s = re.sub(r'<style.*?</style>', ' ', s, flags=re.S | re.I)
        _CACHE[path] = norm_text(re.sub(r'<[^>]+>', ' ', s))
    return _CACHE[path]


PDFTOTEXT = None if A.no_pdf else shutil.which('pdftotext')


def pdf_text(path, page):
    """the text layer of one PDF page (pdftotext, a local tool reading the file as data); None when not available"""
    if PDFTOTEXT is None:
        return None
    key = (path, int(page))
    if key not in _CACHE:
        r = subprocess.run([PDFTOTEXT, '-f', str(page), '-l', str(page), path, '-'], capture_output=True, timeout=300)
        if r.returncode != 0:
            ERR.append(f'pdftotext failed on {path} p.{page}')
            return ''
        _CACHE[key] = norm_text(r.stdout.decode('utf-8', 'replace'))
    return _CACHE[key]


def num(s):
    t = s.replace(',', '').strip()
    try:
        return float(t)
    except ValueError:
        return s


def path_of(root, rel):
    return os.path.join(ROOTS[root], rel)


# ------------------------------------------------------------------ the page before this round (read only)
# Pinned, as the second round's scripts pin theirs: once this round is integrated, the live page carries the new values,
# and reading it would turn them into the 'was' values (and append the Aspire sentence to land.rec's flag twice).
def read_page():
    if A.page:
        return open(A.page, encoding='utf-8').read(), A.page
    git = shutil.which('git')
    if git:
        r = subprocess.run([git, '-C', os.path.join(HERE, '..'), 'show', f'{A.page_rev}:index.html'], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode('utf-8'), f'git {A.page_rev}:index.html'
    snap = '/tmp/claude-0/fit8snap/index.html'
    if os.path.exists(snap):
        return open(snap, encoding='utf-8').read(), snap
    sys.exit('the page before this round was not found: pass --page')


PAGE, PAGE_FROM = read_page()


def page_json(name):
    m = re.search(r'^MODELS\.fitted\.' + name + r'=(\{.*\});?\s*$', PAGE, flags=re.M)
    if not m:
        sys.exit(f'page: MODELS.fitted.{name} not found in {A.page}')
    return json.loads(m.group(1))


def page_re(pat, what, flags=0):
    m = re.search(pat, PAGE, flags)
    if not m:
        sys.exit(f'page: {what} not found (pattern {pat})')
    return m


IND = {}
for m in re.finditer(r'^\s*(\w+)\s*:\s*\{n:"[^"]*",([^}]*)\}', page_re(r'const IND = \{(.*?)\n\};', 'IND', re.S).group(1),
                     flags=re.M):
    IND[m.group(1)] = {f: float(v) for f, v in re.findall(r'\b(rec|ret|gm|grw|buyers|strat|anchor):\s*(-?[\d.]+)',
                                                         m.group(2))}
PEER_SD = {k: float(v) for k, v in re.findall(r'(\w+):(-?[\d.]+)', page_re(r'const PEER_SD=\{([^}]*)\}', 'PEER_SD').group(1))}
CC_WAS = float(page_re(r'cc:(\.\d+), own:RF\.own', 'peerMedians cc').group(1))
mz = page_re(r'Math\.log10\(Math\.max\(ern,1e4\)\)-([\d.]+)\)/([\d.]+)', 'sizeRefs axis')
Z_CENTRE, Z_HALF = float(mz.group(1)), float(mz.group(2))
OWN_A = float(page_re(r'own:(\.\d+)\+S\.own\.b\*z', 'sizeRefs own').group(1))
MGT_A = float(page_re(r'mgt:(\.\d+)\+S\.mgt\.b\*z', 'sizeRefs mgt').group(1))
mf = page_re(r'fin:(\.\d+)\+(\.\d+)\*z', 'sizeRefs fin')
FIN_A, FIN_B = float(mf.group(1)), float(mf.group(2))
SLIDER = {k: (float(a), float(b)) for k, a, b in re.findall(r'<input type="range" id="i_(\w+)" min="(-?\d+)" max="(-?\d+)"', PAGE)}
MENU = {k: sorted(float(v) for v in re.findall(r'<option value="([\d.]+)"', body))
        for k, body in re.findall(r'<select id="i_(own|mgt|fin)">(.*?)</select>', PAGE, flags=re.S)}
CUTS = {k: [(v[i] + v[i + 1]) / 2 for i in range(len(v) - 1)] for k, v in MENU.items()}
SR = page_json('size_refs')
BR_A, BR_G = SR['checks']['bridge']['a'], SR['checks']['bridge']['g']
OWN_B, MGT_B = SR['own']['b'], SR['mgt']['b']
PRR = page_json('peer_rec_ret')
PGM = page_json('peer_gm')
PGR = page_json('peer_grw')


def z_of_rev(rev):
    """the console's size z for a business with this revenue, through the fitted seller bridge
    log10 revenue = a + g log10 SDE (MODELS.fitted.size_refs.checks.bridge); not clamped"""
    return ((math.log10(rev) - BR_A) / BR_G - Z_CENTRE) / Z_HALF


# ------------------------------------------------------------------ 1. quoted figures (pages and PDF text layers)
Q = {}
QROWS = list(csv.DictReader(open(os.path.join(A.csv, 'peer_quotes.csv'), encoding='utf-8')))
n_html = n_pdf = n_pdf_skipped = 0
for r in QROWS:
    p = path_of(r['root'], r['file'])
    if not os.path.exists(p):
        ERR.append(f"quote {r['id']}: local file missing: {p}")
        continue
    exp = r['expect'].split('|') if r['expect'] != '' else []
    if r['kind'] == 'html':
        text = html_text(p); n_html += 1
    elif r['kind'] == 'raw':
        text = open(p, encoding='utf-8', errors='replace').read(); n_html += 1
    else:
        text = pdf_text(p, r['page'])
    if text is None:                                   # pdftotext not available: the transcription stands
        n_pdf_skipped += 1
        Q[r['id']] = {'v': [num(x) for x in exp], 'raw': exp, 'row': r, 'status': 'transcribed; PDF text not re-read'}
        continue
    if r['kind'] == 'pdf':
        n_pdf += 1
    m = re.search(r['pattern'], text, flags=re.S)
    if not m:
        ERR.append(f"quote {r['id']}: pattern not found in {r['file']} {('p.' + r['page']) if r['page'] else ''}")
        continue
    got = [g for g in m.groups()]
    if got != exp:
        ERR.append(f"quote {r['id']}: read {got} but the transcription says {exp}")
        continue
    Q[r['id']] = {'v': [num(x) for x in got], 'raw': got, 'row': r, 'status': 'verified against the local file'}


def qv(i, k=0):
    return Q[i]['v'][k]


def qf(i, k=0):
    """a quoted percentage as a share"""
    return Q[i]['v'][k] / 100.0


# ------------------------------------------------------------------ 2. ScalePad 2026 charts (text layer + rendered page)
SP26 = {}
for r in csv.DictReader(open(os.path.join(A.csv, 'peer_scalepad_2026_charts.csv'), encoding='utf-8')):
    SP26.setdefault(r['chart'], {}).setdefault(r['group'], []).append(r)
    if 'text' in r['layer']:
        t = pdf_text(path_of('R', r['file']), r['pdf_page'])
        if t is not None and not re.search(r'(?<![\d.])' + re.escape(r['pct']) + '%', t):
            ERR.append(f"ScalePad 2026 {r['chart']} {r['group']} {r['bin']}: {r['pct']}% not in the text of PDF p.{r['pdf_page']}")


def bins_of(rows):
    return [(float(r['lo']), float(r['hi']), float(r['pct'])) for r in rows if r['lo'] != '']


def gmed(bins):
    """grouped median, linear within the median bin; bins (lo, hi, weight) with don't-know already left out"""
    tot = sum(w for *_, w in bins); cum = 0.0
    for lo, hi, w in bins:
        q = w / tot
        if cum + q >= .5:
            return lo + (.5 - cum) / q * (hi - lo)
        cum += q


def edges(label):
    t = label.replace(' ', '').replace('%', '')
    if t == '0':
        return (0.0, .005)
    if t == '100':
        return (.995, 1.0)
    a, b = (float(x) for x in t.split('-'))
    return ((a - .5) / 100 if a > 0 else 0.0, min((b + .5) / 100, 1.0))


# ------------------------------------------------------------------ 3. Tommy's Express FDD Item 19
FDD = {}
FDD_ROWS = list(csv.DictReader(open(os.path.join(A.csv, 'peer_tommys_fdd_item19.csv'), encoding='utf-8')))
for r in FDD_ROWS:
    g = FDD.setdefault(r['data_year'], {}).setdefault(r['group'], {})
    g[r['line']] = (num(r['value']), float(r['pct_of_gross_sales']) if r['pct_of_gross_sales'] else None, r)
for r in FDD_ROWS:                                     # the text-layer cells, against the PDF's own text
    if r['layer'] != 'text' or r['line'] == 'sites':
        continue
    t = pdf_text(path_of('R', r['file']), r['pdf_page'])
    if t is None:
        continue
    if r['line'] == 'avg_gross_sales':                 # "39 $1,142,179": the site count, then (a few amounts later) the average
        sites = FDD[r['data_year']][r['group']]['sites'][2]['value']
        pat = r'(?<![\d,.])' + re.escape(sites) + r' (?:\$[\d,. ]+ ){0,4}\$' + re.escape(r['value']) + r'(?![\d,])'
    else:                                              # "$80,455 7.0%"
        pat = r'\$' + re.escape(r['value']) + r' ' + re.escape(r['pct_of_gross_sales']) + '%'
    if not re.search(pat, t):
        ERR.append(f"FDD {r['fdd']} p.{r['pdf_page']} {r['group']} {r['line']}: {r['value']} not found in the text layer")
SUBS = ['waste_removal', 'communications', 'gas', 'sewer', 'water', 'electric']
fdd_checks = {'utilities_total_vs_subaccounts': [], 'percent_base': {}}
for yr, groups in FDD.items():
    for gname, L in groups.items():
        if 'utilities_total' in L:                      # the sub-accounts must add up to the total (transcription check)
            s = sum(L[k][0] for k in SUBS); d = abs(s - L['utilities_total'][0])
            fdd_checks['utilities_total_vs_subaccounts'].append(round(d, 2))
            if d > 3:
                ERR.append(f'FDD {yr} {gname}: utilities sub-accounts {s} against total {L["utilities_total"][0]}')
        # every line's dollars over its printed percent must imply the same gross-sales base: each line gives an
        # interval (the percent's rounding, widened by 0.1% for the tables' own small inconsistencies: CY2021 first-year
        # labour prints 18.92% for 18.905%); the base is the point inside most intervals, and a line whose interval
        # misses it is a mistyped or misplaced cell. The base is then compared with the sales table's average.
        iv = {}
        for k, v in L.items():
            if not v[1]:
                continue
            ps = v[2]['pct_of_gross_sales']; h = 0.5 * 10 ** -(len(ps.split('.')[-1]) if '.' in ps else 0)
            if v[1] - h <= 0:
                continue
            iv[k] = ((v[0] - 1) / (v[1] + h) * 100 / 1.001, (v[0] + 1) / (v[1] - h) * 100 * 1.001)
        cands = sorted(x for lo_, hi_ in iv.values() for x in (lo_, hi_))
        cover = [sum(lo_ <= c <= hi_ for lo_, hi_ in iv.values()) for c in cands]
        best = [c for c, n_ in zip(cands, cover) if n_ == max(cover)]
        base = float(np.median(best))
        for k, (lo_, hi_) in iv.items():
            if not lo_ <= base <= hi_:
                ERR.append(f'FDD {yr} {gname} {k}: its dollars and percent imply a base outside {base:,.0f}')
        avg = L['avg_gross_sales'][0]
        fdd_checks['percent_base'][f'{yr} {gname}'] = {'implied_base': round(base), 'sales_table_average': avg,
                                                       'consistent': bool(abs(base / avg - 1) < .005)}
base_off = {k: v for k, v in fdd_checks['percent_base'].items() if not v['consistent']}

VARIANTS = {
    'A0': ['detergents', 'water', 'sewer', 'electric', 'gas', 'waste_removal'],
    'A': ['detergents', 'water', 'sewer', 'electric', 'gas', 'waste_removal', 'office_supplies'],
    'A2': ['detergents', 'water', 'sewer', 'electric', 'gas', 'waste_removal', 'communications', 'office_supplies'],
    'B': ['detergents', 'water', 'sewer', 'electric', 'gas', 'waste_removal', 'communications', 'office_supplies',
          'merchandise', 'team_member_uniforms'],
    'C': ['detergents', 'water', 'sewer', 'electric', 'gas', 'waste_removal', 'communications', 'office_supplies',
          'merchandise', 'team_member_uniforms', 'customer_claims', 'repairs_maintenance'],
}
YEARS = sorted(FDD)


def gm_group(L, var):
    return 1 - sum(L[k][1] for k in VARIANTS[var] if k in L) / 100.0


wash = {}
for var in VARIANTS:
    by_year, pooled_num, pooled_den = {}, 0.0, 0.0
    for yr in YEARS:
        G = FDD[yr]; n = sum(G[g]['sites'][0] for g in G)
        v = sum(G[g]['sites'][0] * gm_group(G[g], var) for g in G) / n
        by_year[yr] = v; pooled_num += v * n; pooled_den += n
    vals = list(by_year.values())
    wash[var] = {'by_year': by_year, 'mean': float(np.mean(vals)), 'sd_years': float(np.std(vals, ddof=1)),
                 'pooled_site_years': pooled_num / pooled_den}
SITES = {yr: int(sum(FDD[yr][g]['sites'][0] for g in FDD[yr])) for yr in YEARS}
first_year = {yr: gm_group(FDD[yr]['y1'], 'A') for yr in YEARS}
# dollars instead of the printed percentages, where the expense table's base matches the sales table (a check)
dollar_A = {}
for yr in YEARS:
    G = FDD[yr]
    ok = [g for g in G if f'{yr} {g}' not in base_off]
    if ok:
        n = sum(G[g]['sites'][0] for g in ok)
        dollar_A[yr] = sum(G[g]['sites'][0] * (1 - sum(G[g][k][0] for k in VARIANTS['A']) / G[g]['avg_gross_sales'][0])
                           for g in ok) / n
# the within-brand association of margin with a site's revenue (tenure groups; confounded with maturity): a check
xs, ys, ws = [], [], []
for yr in YEARS:
    for g, L in FDD[yr].items():
        xs.append(math.log10(L['avg_gross_sales'][0])); ys.append(gm_group(L, 'A')); ws.append(L['sites'][0])
wn = np.array(ws, float) / np.mean(ws)                  # weighted least squares, weights = sites (normalised)
X = np.column_stack([np.ones(len(xs)), xs]); W = np.diag(wn)
beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ np.array(ys))
resid = np.array(ys) - X @ beta
s2 = float(np.sum(wn * resid ** 2) / (len(ys) - 2))
brand_slope, brand_slope_se = float(beta[1]), float(math.sqrt(s2 * np.linalg.inv(X.T @ W @ X)[1, 1]))
# FDD 2020 (calendar 2019): dollars per car; the text layer lists each table's values in the order of its labels
PC_ROWS = list(csv.DictReader(open(os.path.join(A.csv, 'peer_tommys_fdd2020_per_car.csv'), encoding='utf-8')))
PC = {}
for r in PC_ROWS:
    PC.setdefault(r['group'], {})[r['line']] = num(r['value'])
PC_ORDER = ['detergents', 'repairs_maintenance', 'water', 'electric', 'sewer', 'gas', 'waste_removal', 'communications',
            'customer_claims', 'labor']
for g in PC:
    rows_g = {r['line']: r for r in PC_ROWS if r['group'] == g}
    f0 = path_of('R', rows_g['sites']['file'])
    t = pdf_text(f0, rows_g['sites']['pdf_page'])
    if t is None:
        continue
    if not re.search(r'Number of Outlets ' + re.escape(rows_g['sites']['value']) + r' Average Gross Sales \$'
                     + re.escape(rows_g['avg_gross_sales']['value']), t):
        ERR.append(f'FDD 2020 {g}: sites and average gross sales not found together')
    for pg in sorted({rows_g[k]['pdf_page'] for k in PC_ORDER}):
        seq = ' '.join('$' + rows_g[k]['value'] for k in PC_ORDER if rows_g[k]['pdf_page'] == pg)
        if seq not in pdf_text(f0, pg):
            ERR.append(f'FDD 2020 {g} p.{pg}: the per-car sequence {seq} is not in the text layer')
    t2 = pdf_text(f0, rows_g['other_opex_pct']['pdf_page'])
    if not re.search(re.escape(rows_g['other_opex_pct']['value']) + r'% of revenue or a cost per car total of \$'
                     + re.escape(rows_g['other_opex_per_car']['value']) + ' per car', t2):
        ERR.append(f'FDD 2020 {g}: other operating expenses (% and per car) not found')
per_car = {}
for g, L in PC.items():
    rev_car = L['other_opex_per_car'] / (L['other_opex_pct'] / 100)
    cost = sum(L[k] for k in VARIANTS['A0'])
    per_car[g] = {'revenue_per_car': rev_car, 'chemicals_utilities_per_car': cost, 'gm_A0': 1 - cost / rev_car,
                  'sites': L['sites'], 'avg_gross_sales': L['avg_gross_sales']}

# ------------------------------------------------------------------ 4. Value Builder charts (image-read)
VB = {}
for r in csv.DictReader(open(os.path.join(A.csv, 'peer_valuebuilder_charts.csv'), encoding='utf-8')):
    VB.setdefault((r['chart'], r['series']), []).append(r)
    if not os.path.exists(path_of('S', r['file'])):
        ERR.append(f"Value Builder chart file missing: {r['file']}")


def vb(chart, series, drop_unsure=True):
    rows = VB[(chart, series)]
    return [float(r['pct']) for r in rows if not (drop_unsure and r['bin'] == 'Unsure')]


# ------------------------------------------------------------------ 5. image-read figures
FIG = {}
for r in csv.DictReader(open(os.path.join(A.csv, 'peer_figures_image_read.csv'), encoding='utf-8')):
    FIG.setdefault((r['figure'], r['series']), []).append((int(r['x']), float(r['value'])))
    if not os.path.exists(path_of(r['root'], r['file'])):
        ERR.append(f"figure source missing: {r['file']}")

if ERR:
    print('STOP: a figure did not reproduce from its local file; nothing written.\n  ' + '\n  '.join(ERR))
    sys.exit(1)

# ------------------------------------------------------------------ 6. Census 2022 product lines (streamed)
CEN = {}
WANT = {'561320', '541211', '541219', '811192', '541513', '561730', '713940'}
with open(CENSUS, encoding='latin-1', newline='') as f:
    rd = csv.reader(f, delimiter='|'); hd = next(rd); ix = {k.lstrip('#'): i for i, k in enumerate(hd)}
    for row in rd:
        if row[ix['NAICS2022']] in WANT and row[ix['GEOTYPE']] == '01' and row[ix['TYPOP']] == '00' \
                and row[ix['TAXSTAT']] in ('00', 'T'):
            k = (row[ix['NAICS2022']], row[ix['TAXSTAT']], row[ix['NAPCS2022']])
            CEN[k] = {'label': row[ix['NAPCS2022_LABEL']], 'lineall': float(row[ix['LINEALL_PCT']] or 0),
                      'line': float(row[ix['LINE_PCT']] or 0), 'estab_pct': float(row[ix['ESTAB_PCT']] or 0)}


def cen(naics, napcs, tax='00'):
    k = (naics, tax, napcs)
    if k not in CEN:
        sys.exit(f'Census line {naics} {napcs} ({tax}) not found')
    return CEN[k]


# ------------------------------------------------------------------ 7. Empire Flippers listings (local extract)
EF = list(csv.DictReader(open(os.path.join(A.data5, 'empireflippers', 'clean', 'ef_listings.csv'), encoding='utf-8')))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


ecom_keys = ('eCommerce', 'Amazon FBA', 'Amazon FBM', 'DropShipping', 'Dropshipping')
ef_ecom = [r for r in EF if any(k in (r['monetizations'] or '') for k in ecom_keys)]
ef_ecom_sub = [r for r in ef_ecom if 'Subscription' in (r['monetizations'] or '')]
saas_keys = ('SaaS', 'Subscription', 'Application')
ef_ret = sorted((1 - c / 100) ** 12 for c in (fnum(r['churn_percent']) for r in EF
                                                 if any(k in (r['monetizations'] or '') for k in saas_keys))
                if c is not None and 0 <= c < 100)
rng = np.random.default_rng(11)
ef_boot = [float(np.median(rng.choice(ef_ret, len(ef_ret)))) for _ in range(4000)]

# ================================================================== RETENTION (count definition)
DEF_RET = ("Customer retention, by count: of the customers who bought from you in the previous 12 months, the share who "
           "bought again in the last 12 months (members and contract customers: the share still active). Customers, "
           "not revenue.")
RET_MIN = SLIDER['ret'][0] / 100
# ---- e-commerce
ls_med, ls_mean, ls_sd = qf('ls_rpr', 1), qf('ls_rpr', 0), qf('ls_rpr', 2)
bc_total = qf('bc25_total', 1)
verts = dict(zip(['jewelry_accessories', 'home_goods', 'footwear', 'sports_hobbies', 'apparel', 'department_stores',
                  'health_beauty'], [x / 100 for x in Q['bc25_vert']['v']]))
ecom_mean = (ls_med + bc_total) / 2
ecom_se_between = float(np.std([ls_med, bc_total], ddof=1) / math.sqrt(2))
Q1, P2 = (.20, .225, .25), (.40, .50, .60)          # the verifier's steady-state bridge (judgment ranges)
bridge = [q1 / (1 - p2 + q1) for q1 in Q1 for p2 in P2]
ecom_sd_bridge = float(np.std(bridge, ddof=1))
ecom_se = math.sqrt(ecom_se_between ** 2 + ecom_sd_bridge ** 2)
ECOM = {
    'v': rhu(ecom_mean), 'se': r3(ecom_se),
    'se_note': (f"SE {r3(ecom_se)}: the two sources' between-source SE ({r3(ecom_se_between)}) and the untested step from a "
                f"store's repeat-purchase rate to the count definition, in quadrature. The step: in a steady state the "
                f"share of last year's buyers who buy again is r = q1/(1 - p2 + q1), q1 a new buyer's chance of buying "
                f"again within a year (.20-.25, around the measured rates), p2 a repeat buyer's annual repurchase (.40-.60, "
                f"judgment); over that grid r runs {min(bridge):.2f}-{max(bridge):.2f} (SD {r3(ecom_sd_bridge)}), above "
                f"the shipped value, while selection pulls the other way (stores on a repeat-customer app; Bluecore's "
                f"enterprise retailers), so the level stays at the measured mean and the SE carries the step"),
    'source': (f"Little Stream Software 2024 data study (over {Q['ls_scope']['v'][0]:,.0f} Shopify stores: full repeat "
               f"purchase rate median {ls_med * 100:.1f}%, mean {ls_mean * 100:.0f}%, SD {ls_sd * 100:.1f}%); Bluecore 2025 "
               f"Customer Growth Benchmarks via the Shopify blog ({bc_total * 100:.1f}% across seven retail verticals, "
               f"{min(verts.values()) * 100:.1f}-{max(verts.values()) * 100:.1f}% by vertical)"),
    'note': (f"count definition: {ecom_mean:.4f} = the mean of the Little Stream median ({ls_med:.3f}) and Bluecore's total "
             f"({bc_total:.3f}), rounded half up. Both measure the share of a store's customers who buy again, over the "
             f"store's data window rather than exactly 12 months. Bluecore's 2024 report: {qv('bc24_once'):.0f}% of "
             f"customers buy once and never return. Little Stream's stores use a repeat-customer analytics app for CPG "
             f"brands; Bluecore's are enterprise retailers. Below the retention slider's {RET_MIN * 100:.0f}% minimum"),
    'parts': {'little_stream_2024': {'median': ls_med, 'mean': ls_mean, 'sd': ls_sd,
                                     'stores': f"over {Q['ls_scope']['v'][0]:,.0f}"},
              'bluecore_2025': {'v': bc_total, 'verticals': verts},
              'bluecore_2024_buy_once': qf('bc24_once'),
              'bridge_range': [r3(min(bridge)), r3(max(bridge))]},
    'tier': 'aggregate', 'was': IND['ecom']['ret']}
# ---- auto repair
ro = Q['ro_groups']['v']
auto_lo, auto_hi = 1 - qf('ro_total', 1), 1 - qf('ro_total', 0)
AUTO = {
    'v': rhu((auto_lo + auto_hi) / 2), 'se': r3((auto_hi - auto_lo) / 2),
    'se_note': (f"SE {r3((auto_hi - auto_lo) / 2)} = half the published range ({auto_lo:.2f}-{auto_hi:.2f}); one vendor "
                f"source (shops that commissioned an analysis; collision shops, which the console's industry includes, "
                f"probably keep fewer customers)"),
    'source': (f"Auto Apps (Paul Stewart) via the R.O. Writer blog (2022): {qv('ro_scope', 0)} of customer analyses of "
               f"service centres across the {qv('ro_scope', 1)}, {qv('ro_scope', 2)} years: {qv('ro_total', 0):.0f}-"
               f"{qv('ro_total', 1):.0f}% of the total customers serviced do not return the following calendar year"),
    'note': (f"count definition exactly: last year's customers who came back. Midpoint of {auto_lo:.2f}-{auto_hi:.2f}. By "
             f"group, the share returning: new customers {1 - ro[3] / 100:.2f}-{1 - ro[2] / 100:.2f}, returning "
             f"{1 - ro[5] / 100:.2f}-{1 - ro[4] / 100:.2f}, best {1 - ro[7] / 100:.2f}-{1 - ro[6] / 100:.2f}. On the "
             f"retention slider's {RET_MIN * 100:.0f}% minimum"),
    'parts': {'total': [auto_lo, auto_hi], 'new': [1 - ro[3] / 100, 1 - ro[2] / 100],
              'returning': [1 - ro[5] / 100, 1 - ro[4] / 100], 'best': [1 - ro[7] / 100, 1 - ro[6] / 100]},
    'tier': 'aggregate', 'was': IND['auto']['ret']}
# ---- restaurants: the middle of the range the page's own figures support (coordinator's rule, mid-round): Bloom's
#      stated annual retention (likely low: guest matching misses repeat visits) and the steady-state bridge from the
#      same page's first-visit and repeat figures, at its central repeat rate
rest_v = 1 - qf('bloom_head', 2)
q1r = qf('bloom_first', 0)
rest_bridge = [q1r / (1 - p2 + q1r) for p2 in P2]
rest_central = rest_bridge[len(P2) // 2]                 # p2 = .50, the middle of .40-.60
assert rest_central == float(np.median(rest_bridge))
rest_mid = (rest_v + rest_central) / 2
REST_SE = .10      # judgment: one vendor page; its stated reading and the bridge's central value are .12 apart
REST = {
    'v': rhu(rest_mid), 'se': REST_SE,
    'se_note': (f"SE .10 is judgment: one vendor marketing page, and its stated reading ({rest_v:.3f}) and the bridge's "
                f"central value ({rest_central:.3f}) are {rest_central - rest_v:.2f} apart. The stated figure is taken over "
                f"a repeat-guest base ({qv('bloom_base', 1):.0f} of {qv('bloom_base', 0):.0f} per location) and the guest "
                f"matching misses returning guests, which biases it down; the bridge rests on judgment repeat rates"),
    'source': (f"Bloom Intelligence, State of Restaurant Guest Retention 2025: restaurant locations {qv('bloom_head', 0)} to "
               f"{qv('bloom_head', 1)} lost {qv('bloom_head', 2)}% of their existing guests within a year, 'an annual "
               f"retention rate of about {qv('bloom_head', 3):.0f}%'; {q1r * 100:.0f}% of first-time visitors return within "
               f"90 days"),
    'note': (f"the middle of the range the page's own figures support: its stated {rest_v:.2f}, likely low, and "
             f"{rest_central:.2f} from its first-visit and repeat figures (the steady-state share of last year's guests "
             f"who come back, r = q1/(1 - p2 + q1), with q1 = {q1r:.2f} of first-time guests back within 90 days and "
             f"repeat guests' annual return p2 = .50, the middle of .40-.60; {min(rest_bridge):.2f}-{max(rest_bridge):.2f} "
             f"over that range): ({rest_v:.3f} + {rest_central:.3f}) / 2 = {rest_mid:.4f}, rounded. The stated {rest_v:.2f} "
             f"fixes the direction only: any value from it to about .35 fits the page's figures. One vendor's marketing "
             f"page; {qv('bloom_first', 1):.0f}% of guests never return after one visit; Toast data (Resy-Toast Regulars "
             f"Report, {qv('resy_toast', 0)}): up to {qv('resy_toast', 1):.0f}% of restaurant order volume comes from "
             f"{qv('resy_toast', 2):.0f}% of guests. Below the retention slider's {RET_MIN * 100:.0f}% minimum"),
    'parts': {'bloom_2025': {'lost_within_a_year': qf('bloom_head', 2), 'retention': r3(rest_v),
                             'one_visit_only': qf('bloom_first', 1), 'first_timers_back_within_90_days': q1r},
              'steady_state_bridge': {'repeat_rate_p2': list(P2), 'r': [r3(x) for x in rest_bridge],
                                      'central': r3(rest_central)},
              'rule': 'v = round((stated retention + the bridge at p2 = .50) / 2, 2)',
              'toast_2026': {'share_of_order_volume': qf('resy_toast', 1), 'share_of_guests': qf('resy_toast', 2)}},
    'tier': 'aggregate', 'was': IND['rest']['ret']}

# ================================================================== RECURRING: msp.rec
sp26_all = gmed(bins_of(SP26['recurring_share']['all']))
sp26_bands = {g: gmed(bins_of(SP26['recurring_share'][g])) for g in ('small_1_10', 'medium_11_50', 'large_50plus')}
lab25 = [x.strip('"') for x in Q['sp25_rec_all']['raw'][0].split('","')]
E25 = [edges(x) for x in lab25]


def sp25(qid, k=0):
    vals = [float(x) for x in Q[qid]['raw'][k].split(',')]
    return gmed([(lo, hi, w) for (lo, hi), w in zip(E25, vals)])


sp25_all = sp25('sp25_rec_all', 1)
sp25_bands = {'small': sp25('sp25_rec_small'), 'medium': sp25('sp25_rec_medium'), 'large': sp25('sp25_rec_large')}
d_share = qf('datto_44', 0); d_cut = qf('datto_44', 1)
datto = {s: d_cut + s * N.ppf(d_share) for s in (.20, .25, .30)}   # P(share > .50) = .44 under N(m, s)
msp_pts = {'scalepad_2026': sp26_all, 'scalepad_2025': sp25_all, 'datto_2019': datto[.25]}
msp_mean = float(np.mean(list(msp_pts.values())))
msp_sd = float(np.std(list(msp_pts.values()), ddof=1))
msp_se = msp_sd / math.sqrt(3)
kaseya = qf('kaseya_mean')
alt = {'drop_scalepad_2025': float(np.mean([sp26_all, datto[.25]])),
       'add_kaseya_2016': float(np.mean([sp26_all, sp25_all, datto[.25], kaseya])),
       'drop_scalepad_2025_add_kaseya': float(np.mean([sp26_all, datto[.25], kaseya]))}
c513 = cen('541513', '7014450000')
MSP_REC = {
    'v': rhu(msp_mean), 'se': r3(msp_se),
    'se_note': (f"SE {r3(msp_se)} = between-source SD ({r3(msp_sd)}) over sqrt(3): survey instability, not sampling "
                f"(ScalePad's 2025 and 2026 surveys differ by {abs(sp26_all - sp25_all) * 100:.0f} points). Which surveys "
                f"are kept moves the level over {min(alt.values()):.2f}-{max(alt.values()):.2f} (without ScalePad 2025 "
                f"{alt['drop_scalepad_2025']:.3f}; with Kaseya 2016 {alt['add_kaseya_2016']:.3f})"),
    'source': (f"ScalePad 2026 MSP Trends Report (1,100+ North American MSPs, November 2025; 'Percentage of Recurring "
               f"Revenue', PDF p.15); ScalePad 2025 MSP Trends Report, chapter 1 ('Recurring revenue rate', Wayback copy); "
               f"Datto State of the MSP 2019 via ITPro ({qv('datto_n'):,.0f}+ MSPs worldwide: {qv('datto_44', 0):.0f}% earn "
               f"more than half of revenue from recurring services)"),
    'note': (f"{msp_mean:.4f} = the equal-weight mean of the grouped medians, don't-know left out and linear within the "
             f"median bin: ScalePad 2026 {sp26_all:.3f} (1-10 employees {sp26_bands['small_1_10']:.3f}, 11-50 "
             f"{sp26_bands['medium_11_50']:.3f}, 50+ {sp26_bands['large_50plus']:.3f}), ScalePad 2025 {sp25_all:.3f}, Datto "
             f"{datto[.25]:.3f} (the median a normal with SD .25 puts {qv('datto_44', 0):.0f}% above half; {datto[.30]:.3f}-"
             f"{datto[.20]:.3f} for SD .30-.20). The measure is managed-service MRR under monthly agreements: recurring "
             f"under either reading of the label. Check: Kaseya 2016 (n={qv('kaseya_n'):.0f}) mean {kaseya:.2f}; Census "
             f"2022 NAICS 541513: IT infrastructure and network management {c513['lineall'] / 100:.3f} of revenue "
             f"(service type). The console's msp industry (NAICS 541511) is broader and more project-based than MSPs, "
             f"which if anything puts its median lower. Self-reported, mixed job roles"),
    'parts': {'scalepad_2026': {'median': r3(sp26_all), **{k: r3(v) for k, v in sp26_bands.items()}},
              'scalepad_2025': {'median': r3(sp25_all), **{k: r3(v) for k, v in sp25_bands.items()}},
              'datto_2019': {'median_sd_25': r3(datto[.25]), 'range': [r3(datto[.30]), r3(datto[.20])],
                             'share_above_half': d_share},
              'kaseya_2016_mean': kaseya, 'census_541513_infrastructure_share': c513['lineall'] / 100,
              'level_by_choice_of_surveys': {k: r3(v) for k, v in alt.items()}},
    'tier': 'aggregate', 'was': IND['msp']['rec']}

# ================================================================== RETENTION AND RECURRING CHECKS (not shipped)
churn26 = gmed(bins_of(SP26['client_churn']['all']))
lab4 = [x.strip('"') for x in Q['sp25_ret']['raw'][0].split('","')]
w4 = [float(x) for x in Q['sp25_ret']['raw'][1].split(',')]
ret25 = gmed([edges(l) + (w,) for l, w in zip(lab4, w4) if l != 'Unsure'])
itg_ret = 1 - qf('itg_churn', 1)
msp_ret_pts = [1 - churn26, itg_ret, ret25]
msp_ret_pool = {'mean': float(np.mean(msp_ret_pts)), 'median': float(np.median(msp_ret_pts)),
                'sd': float(np.std(msp_ret_pts, ddof=1)), 'se': float(np.std(msp_ret_pts, ddof=1) / math.sqrt(3))}
# HS1 dental: mean to median under a Beta with the top decile at the published top-10% value; a 12-month window
hs_mean, hs_top = qf('hs1_avg', 0), qf('hs1_avg', 1)


def beta_median(mean, p90):
    def f(c):
        return stats.beta.ppf(.9, mean * c, (1 - mean) * c) - p90
    c = optimize.brentq(f, 0.5, 500)
    return float(stats.beta.median(mean * c, (1 - mean) * c))


hs_med = {cut: beta_median(hs_mean, cut) for cut in (hs_top, .90)}
hs_12m = 1 - (1 - hs_mean) ** (12 / qv('hs1_def'))
nbb_u = [v for _, v in sorted(FIG[('nbb_wp444_fig8', 'unweighted')])]
nbb_w = [v for _, v in sorted(FIG[('nbb_wp444_fig8', 'value_weighted')])]
nbb_u_late = float(np.mean([v for y, v in FIG[('nbb_wp444_fig8', 'unweighted')] if 2010 <= y <= 2018]))
nbb_w_late = float(np.mean([v for y, v in FIG[('nbb_wp444_fig8', 'value_weighted')] if y >= 2010]))
ifdp = {k: v for (fig, k), L in FIG.items() if fig == 'ifdp1218_fig4' for _, v in L}
home_g = PGR['by_industry']['home']
home_rep = qf('st_repeat')
rinsed = {'2025-02 release': qf('rinsed_feb25'), '2025Q2': qf('rinsed_25q2', 1), '2025Q4': qf('rinsed_25q4'),
          '2026Q2': qf('rinsed_26q2')}
life = qv('rinsed_life', 4)
c320_temp, c320_ttp, c320_perm = (cen('561320', c)['lineall'] / 100 for c in ('7010350000', '7010400000', '7010300000'))
prof_lines = {n: sum(cen(n, c)['lineall'] for c in ('7016450000', '7016475000', '7016500000')) / 100
              for n in ('541211', '541219')}
audit_541211 = cen('541211', '7016325000')['lineall'] / 100
land_care = sum(cen('561730', c)['lineall'] for c in ('7000645000', '7006750000', '7006725000')) / 100
wash_lines = {lab: (cen('811192', c, 'T')['lineall'] / 100, cen('811192', c, 'T')['estab_pct'] / 100) for lab, c in
              (('automatic', '7002650006'), ('detailing', '7002650003'), ('hand', '7002650009'),
               ('self_service', '7002650012'))}
fit_line = cen('713940', '7001900003', 'T')

NOT_SHIPPED = {
    'msp.ret': {'v': IND['msp']['ret'], 'judgment': True, 'verdict': 'check_only: the surveys disagree (ScalePad 2026 reads .95, ScalePad 2025 .60), and pooled as the recurring share is they do not reject .87',
                'readings': {'scalepad_2026_churn_median': r3(churn26), 'scalepad_2026_retention': r3(1 - churn26),
                             'scalepad_2025_retention_median': r3(ret25),
                             'scalepad_2025_share_below_half': qf('sp25_ret_text'),
                             'it_glue_2021_share_under_5pct_churn': qf('itg_churn', 0)},
                'pooled_as_for_rec': {k: r3(v) for k, v in msp_ret_pool.items()},
                'note': (f"ScalePad 2026 (PDF p.37, no period stated): client churn grouped median {churn26 * 100:.1f}%, "
                         f"so {1 - churn26:.3f}; IT Glue 2021 ({qv('itg_n', 0):,.0f} respondents, {qv('itg_msp'):.0f}% MSPs): "
                         f"{qv('itg_churn', 0):.0f}% under {qv('itg_churn', 1):.0f}% churn, so about {itg_ret:.2f}; ScalePad "
                         f"2025 (chapter 4): retention grouped median {ret25:.3f}, {qv('sp25_ret_text'):.0f}% of MSPs below "
                         f"half. Pooled as the recurring share is (all three kept): mean {msp_ret_pool['mean']:.3f}, SE "
                         f"{msp_ret_pool['se']:.3f}, so .87 is not rejected. Only a little over one-third of MSPs track "
                         f"churn, and executives report rosier retention than frontline staff (ScalePad 2026). Read as "
                         f"monthly, 4.7% would be {(1 - churn26) ** 12:.2f} a year")},
    'medical.ret': {'v': IND['medical']['ret'], 'judgment': True,
                    'verdict': 'check_only (dental only, an 18-month window, a mean)',
                    'readings': {'hs1_dental_1_7_locations_mean': hs_mean, 'top_10pct': hs_top,
                                 'hs1_8plus_locations_mean': qf('hs1_dso', 0), 'top_10pct_8plus': qf('hs1_dso', 2),
                                 'window_months': qv('hs1_def'),
                                 'median_if_beta': {f'p90_{k:.2f}': r3(v) for k, v in hs_med.items()},
                                 'twelve_month_constant_hazard': r3(hs_12m)},
                    'note': (f"Henry Schein One 2026 Catalyst Index ('thousands of dental offices'): practices with 1-7 "
                             f"locations average {hs_mean * 100:.0f}% patient retention (top 10% {hs_top * 100:.0f}%), 8+ "
                             f"locations {qf('hs1_dso', 0) * 100:.0f}%; active patients returning within "
                             f"{qv('hs1_def'):.0f} months. A Beta with that mean and top decile has median "
                             f"{min(hs_med.values()):.2f}-{max(hs_med.values()):.2f}; a 12-month window reads lower "
                             f"({hs_12m:.2f} under a constant hazard). Dental only: the console maps medical to physician "
                             f"offices (NAICS 621111), and no physician figure was found")},
    'dist.ret': {'v': IND['dist']['ret'], 'judgment': True, 'verdict': 'check_only (count about .60, value about .90)',
                 'readings': {'nbb_links_count_2002_19': [min(nbb_u), max(nbb_u)], 'nbb_count_2010_18_mean': r3(nbb_u_late),
                              'nbb_links_value_2002_19': [min(nbb_w), max(nbb_w)], 'nbb_value_2010_19_mean': r3(nbb_w_late),
                              'us_importer_supplier_survival_by_age_2011': ifdp,
                              'share_of_us_imports_in_existing_relationships': qf('ifdp_80')},
                 'note': (f"Image-read figures. NBB WP 444 Fig. 8: one-year survival of Belgian firm-to-firm links (EUR "
                          f"{qv('nbb_thr'):.0f} a year or more) {min(nbb_u):.2f}-{max(nbb_u):.2f} by count, "
                          f"{min(nbb_w):.2f}-{max(nbb_w):.2f} by value (the text's 'less than {qv('nbb_text'):.0f}%' is "
                          f"contradicted by the figure). FRB IFDP 1218 Fig. 4: US importers' relationships with a foreign "
                          f"supplier survive the year {ifdp['age_0']:.2f} of the time when new, {ifdp['age_1']:.2f} at one "
                          f"year old, {ifdp['age_9']:.2f} at nine. Whole-economy links, not the median small distributor's "
                          f"customers")},
    'mfg.ret': {'v': IND['mfg']['ret'], 'judgment': True, 'verdict': 'check_only (count about .60, value about .90-.96)',
                'readings': {'nbb_count_2010_18_mean': r3(nbb_u_late), 'nbb_value_2010_19_mean': r3(nbb_w_late),
                             'nber_w31231_supplier_separation_share': {'median': qv('nber_a5', 7),
                                                                      'mean': qv('nber_a5', 5),
                                                                      'firm_years': qv('nber_a5', 9)}},
                'note': (f"As for dist; Belgian manufacturers drop suppliers worth a median {qv('nber_a5', 7) * 100:.1f}% "
                         f"of input spending a year (mean {qv('nber_a5', 5) * 100:.1f}%, {qv('nber_a5', 9):,.0f} "
                         f"firm-years; NBER WP 31231, Table A5), about {1 - qv('nber_a5', 7):.2f} by value")},
    'home.ret': {'v': IND['home']['ret'], 'judgment': True, 'verdict': 'check_only (a revenue bound; no count measure)',
                 'readings': {'repeat_customer_share_of_revenue': home_rep, 'peer_growth': home_g,
                              'revenue_retention_bound': r3(home_rep * (1 + home_g)),
                              'bound_at_growth_05_12': [r3(home_rep * 1.05), r3(home_rep * 1.12)]},
                 'note': (f"ServiceTitan / Thrive Analytics ({qv('st_n'):,.0f}+ US residential contractors, "
                          f"{qv('st_date')}): repeat customers {home_rep * 100:.0f}% of annual revenue, so last year's "
                          f"revenue kept is at most {home_rep:.2f} x (1 + g) = {home_rep * (1 + home_g):.2f} at the peer "
                          f"growth {home_g:.2f}. No count measure; .70 fits maintenance-agreement members only")},
    'staff.ret': {'v': IND['staff']['ret'], 'judgment': True, 'verdict': 'check_only (the only sourced figure is about .80)',
                  'readings': {'clearlyrated_staffing_annual_retention': qf('cr_table'),
                               'clients_churned_per_100': f"{qv('cr_staff', 0):.0f} or more"},
                  'note': (f"ClearlyRated: 'the average staffing firm churns {qv('cr_staff', 0):.0f} or more clients for "
                           f"every {qv('cr_staff', 1):.0f} in a normal economic year, which implies annual client retention "
                           f"near {qv('cr_staff', 2):.0f} percent'. .70 is 10 points below the only sourced figure")},
    'wash.ret': {'v': IND['wash']['ret'], 'judgment': True, 'verdict': 'check_only (members only)',
                 'readings': {'monthly_member_churn': rinsed,
                              'annual_member_survival': {k: r3((1 - c) ** 12) for k, c in rinsed.items()},
                              'median_average_lifetime_months': life,
                              'survival_if_mean_lifetime': r3(math.exp(-12 / life)),
                              'survival_if_median_lifetime': r3(2 ** (-12 / life)),
                              'winbacks_share_of_new_signups': qf('rinsed_winback')},
                 'note': (f"Rinsed (washes on its CRM, {qv('rinsed_sites'):,.0f}+ sites): monthly member churn "
                          f"{min(rinsed.values()) * 100:.1f}-{max(rinsed.values()) * 100:.1f}%, so "
                          f"{min((1 - c) ** 12 for c in rinsed.values()):.2f}-{max((1 - c) ** 12 for c in rinsed.values()):.2f} "
                          f"of members stay a year; the industry median of a wash's average member lifetime, {life} months, "
                          f"gives {math.exp(-12 / life):.2f} ({2 ** (-12 / life):.2f} if read as a median lifetime); "
                          f"{qv('rinsed_winback')}% of new 2025Q4 signups were win-backs. Retail customers are not "
                          f"measured, so the count is not identified")},
    'saas.ret': {'v': IND['saas']['ret'], 'judgment': True, 'verdict': 'check_only (depends on population: .42-.91)',
                 'readings': {'empire_flippers_micro_saas_median': r3(float(np.median(ef_ret))),
                              'empire_flippers_n': len(ef_ret), 'empire_flippers_boot_se': r3(float(np.std(ef_boot, ddof=1))),
                              'chartmogul_top_quartile_3_8m_arr': qf('cm_top', 0),
                              'chartmogul_top_quartile_15_30m_arr': qf('cm_top', 1),
                              'chartmogul_share_above_85': [qf('cm_share', 0), qf('cm_share', 1)],
                              'kbcm_2021_logo': r3(1 - qf('kbcm_logo')), 'kbcm_2021_gross_dollar': r3(1 - qf('kbcm_gross')),
                              'saas_capital_2025_grr_median': qf('rb32_med', 1), 'bootstrapped_grr': qf('rb32_boot', 1),
                              'month_to_month_grr': qf('rb32_m2m', 1)},
                 'note': (f"By count: micro-SaaS sold on Empire Flippers (1 - monthly churn)^12 median "
                          f"{np.median(ef_ret):.3f} (n={len(ef_ret)}); ChartMogul top-quartile customer retention "
                          f"{qf('cm_top', 0):.3f} ($3-8M ARR) and {qf('cm_top', 1):.3f} ($15-30M), {qv('cm_share', 0):.0f}-"
                          f"{qv('cm_share', 1):.0f}% of SaaS businesses above {qv('cm_share', 2):.0f}%; KBCM 2021 (companies "
                          f"of ${qv('kbcm_scope'):.0f}M+ ARR) logo {1 - qf('kbcm_logo'):.3f}. By value: KBCM gross dollar "
                          f"{1 - qf('kbcm_gross'):.3f}; SaaS Capital 2025 median GRR {qf('rb32_med', 1):.2f}. .88 fits B2B "
                          f"firms of $5M+ ARR, not the median small software seller; a size slope would fit better than "
                          f"one level")},
    'prof.ret': {'v': IND['prof']['ret'], 'judgment': True, 'verdict': 'not_identified',
                 'readings': {'clearlyrated_cross_industry_directional': qf('cr_prof')},
                 'note': (f"ClearlyRated: the widely quoted 'around {qv('cr_prof'):.0f} percent' professional-services "
                          f"retention 'is older and should be treated as directional'; for accounting, legal, AEC and IT "
                          f"services: '{qv('cr_noprof')}'. .84 is probably that figure")},
    'vet.ret': {'v': IND['vet']['ret'], 'judgment': True, 'verdict': 'not_found',
                'note': 'IDEXX and dvm360 pages give no figures; other claims appear only in vendor blogs citing unopened reports'},
    'constr.ret': {'v': IND['constr']['ret'], 'judgment': True, 'verdict': 'not_found', 'note': 'no source found'},
    'staff.rec': {'v': IND['staff']['rec'], 'judgment': True, 'verdict': 'definition (the label is not changed this round)',
                  'readings': {'census_561320_temporary_staffing': c320_temp, 'temp_to_perm': c320_ttp,
                               'permanent_placement': c320_perm, 'subscriptions_and_agreements_only': 'about 0'},
                  'note': (f"Census 2022 NAICS 561320: temporary staffing {c320_temp * 100:.1f}% of revenue "
                           f"(temp-to-perm {c320_ttp * 100:.1f}%, permanent placement {c320_perm * 100:.1f}%): about "
                           f"{c320_temp:.2f} if assignments renewing without a new sale count as contracted, about 0 if "
                           f"only subscriptions and service agreements do; .30 matches neither")},
    'ecom.rec': {'v': IND['ecom']['rec'], 'judgment': True, 'verdict': 'definition (the label is not changed this round)',
                 'readings': {'ef_ecommerce_listings': len(ef_ecom), 'with_subscription_monetization': len(ef_ecom_sub),
                              'share': r3(len(ef_ecom_sub) / len(ef_ecom))},
                 'note': (f"{len(ef_ecom_sub)} of {len(ef_ecom):,} Empire Flippers e-commerce listings "
                          f"({len(ef_ecom_sub) / len(ef_ecom) * 100:.1f}%) carry a subscription monetization (any "
                          f"subscription product), so subscriptions alone put the median near 0; .18 needs repeat orders "
                          f"counted")},
    'prof.rec': {'v': IND['prof']['rec'], 'judgment': True, 'verdict': 'check_only (service type, not contract status)',
                 'readings': {'census_541211_monthly_type_lines': r3(prof_lines['541211']),
                              'census_541219_monthly_type_lines': r3(prof_lines['541219']),
                              'census_541211_financial_auditing': audit_541211},
                 'note': (f"Census 2022: general accounting, bookkeeping and payroll lines are "
                          f"{prof_lines['541211'] * 100:.1f}% of CPA-office (541211) revenue and "
                          f"{prof_lines['541219'] * 100:.1f}% of other accounting (541219) revenue; usually monthly "
                          f"engagements, but the lines record service type, not contract status (financial auditing is "
                          f"{audit_541211 * 100:.1f}% of 541211, a large-firm mix). Legal: nothing")},
    'land.rec': {'v': IND['land']['rec'], 'judgment': True, 'verdict': 'check_only (commercial median above .50)',
                 'readings': {'aspire_share_with_majority_recurring_maintenance': qf('aspire_59'),
                              'aspire_n': qv('aspire_n'), 'census_561730_care_lines': r3(land_care)},
                 'note': (f"Aspire 2026 (Thrive Analytics, {qv('aspire_n'):,.0f} commercial landscape contractors, "
                          f"{qv('aspire_dates', 0)}-{qv('aspire_dates', 1)}): {qv('aspire_59'):.0f}% earn the majority of "
                          f"revenue from recurring maintenance, so the commercial median is above .50; residential firms are "
                          f"not measured. Census 2022 care lines {land_care:.3f} of NAICS 561730 revenue (an upper bound)")},
    'wash.rec': {'v': IND['wash']['rec'], 'judgment': True,
                 'verdict': 'check_only: a revenue-weighted share driven by express chains, not the median seller',
                 'readings': {'marq_membership_share_of_2025_revenue': qf('marq_sub', 0),
                              'marq_express_share_of_revenue': qf('marq_express'),
                              'mcw_uwc_share_of_wash_sales': {'2025': qf('mcw_uwc', 0), '2024': qf('mcw_uwc', 1),
                                                              'as_quoted_by_marq': qf('marq_mcw', 1)},
                              'census_811192_lines_revenue_and_estab_share': {k: [r3(a), r3(b)] for k, (a, b) in wash_lines.items()}},
                 'note': (f"MarQ (method not published): memberships about {qv('marq_sub', 0):.0f}% of 2025 US car-wash "
                          f"revenue (USD {qv('marq_sub', 1)}bn of {qv('marq_size', 1)}bn), express tunnels "
                          f"{qv('marq_express'):.0f}%; Mister Car Wash members {qv('mcw_uwc', 0):.0f}% of wash sales (10-K; "
                          f"MarQ quotes {qv('marq_mcw', 1):.0f}%). A revenue-weighted share driven by express chains: Census "
                          f"2022 lines small by revenue are common by site (self-service {wash_lines['self_service'][0] * 100:.1f}% "
                          f"of revenue, {wash_lines['self_service'][1] * 100:.1f}% of establishments), so .35 is an upper-side "
                          f"reading for the median seller")},
}
# keep the second round's fit.rec and saas.rec entries as they are (not repeated here)

# ================================================================== CAR-WASH GROSS MARGIN
W_LEVEL = .80            # judgment: the measured express margin shaded for the sellers' format mix
inbay = 1 - qv('tax_inbay', 1) / qv('tax_inbay', 0)
selfs = 1 - qv('tax_self', 1) / qv('tax_self', 0)
measured = wash['A']['mean']
fmt_readings = [measured, inbay, selfs]
s_year = wash['A']['sd_years']
s_def = float(np.std([wash[v]['mean'] for v in ('A0', 'A', 'A2', 'B')], ddof=1))
s_fmt = float(np.std(fmt_readings, ddof=1))
w_se = math.sqrt(s_year ** 2 + s_def ** 2 + s_fmt ** 2)
shade = measured - W_LEVEL
KNOTS = PGM['knots_log10_rev']
# the sites' revenue, site-weighted: the flat level is measured there. Away from it the curve could be off by as much as
# the within-brand gradient (confounded with maturity, so not shipped as a slope), so each knot's SE adds that gradient
# times the knot's distance from the sites' revenue, in quadrature
W_REV = float(np.average([FDD[y][g]['avg_gross_sales'][0] for y in YEARS for g in FDD[y]],
                         weights=[FDD[y][g]['sites'][0] for y in YEARS for g in FDD[y]]))
W_SE_KNOTS = [r3(math.sqrt(w_se ** 2 + (abs(brand_slope) * (k - math.log10(W_REV))) ** 2)) for k in KNOTS]
PEER_GM_WASH = {'gm': [W_LEVEL] * len(KNOTS), 'se': W_SE_KNOTS, 'slope': 0,
                'slope_se': r3(abs(brand_slope)), 'tier': 'franchise disclosure'}
WASH_SURVEY = {
    'source': "Tommy's Express franchise disclosure documents, Item 19 (2022, 2024, 2025, 2026; Minnesota CARDS registry)",
    'measure': ('1 - (detergents + water + sewer + electric + gas + waste removal + office supplies) / gross sales, by '
                'tenure group, site-weighted'),
    'median': r3(measured), 'statistic': 'mean of the four years\' site-weighted means (n = site-years; sd = between years)',
    'n': sum(SITES.values()), 'sd': r3(s_year),
    'revenue': round(W_REV),
    'definition_match': True,
    'by_year': {y: r3(v) for y, v in wash['A']['by_year'].items()}, 'sites_by_year': SITES,
    'variants': {v: r3(wash[v]['mean']) for v in VARIANTS},
    'verdict': (f"sets the level: {measured:.3f} measured (mean of four years; {wash['A']['pooled_site_years']:.3f} pooling "
                f"site-years), shaded {shade:.3f} to {W_LEVEL:.2f} for non-express formats (judgment), flat in revenue"),
}
DEF_WASH_NOW = PGM['definition']['wash']
DEF_WASH_NEW = ("Revenue less chemicals, water and sewer, energy and other utilities, and supplies (car washes: wages, "
                "repairs and maintenance, customer claims and merchandise bought for resale are not in it).")

# ================================================================== LARGEST CUSTOMER (cc)
CC_EDGES = [0.01, 0.155, 0.255, 0.505]
CC_DOM = (SLIDER['cc'][0] / 100, SLIDER['cc'][1] / 100)


def lognorm_fit(sh, n=10000):
    cnt = np.array(sh, float) / sum(sh) * n

    def nll(p):
        mu, ls = p; s = math.exp(ls)
        c = [0.0] + [N.cdf((math.log(e) - mu) / s) for e in CC_EDGES[1:]] + [1.0]
        return -float(np.sum(cnt * np.log(np.clip(np.diff(c), 1e-12, 1))))
    r = optimize.minimize(nll, [math.log(.12), 0.0], method='Nelder-Mead',
                          options={'xatol': 1e-10, 'fatol': 1e-12, 'maxiter': 20000})
    return float(r.x[0]), float(math.exp(r.x[1]))


def lognorm_pts(mu, s, n=20000):
    u = (np.arange(n) + .5) / n
    return np.minimum(np.exp(mu + s * N.ppf(u)), 1.0), np.full(n, 1.0 / n)


def pw_uniform(sh, top, n=400):
    sh = np.array(sh, float) / sum(sh); xs, ws = [], []
    ends = CC_EDGES + [top]
    for i in range(4):
        a, b = ends[i], ends[i + 1]
        xs += list(a + (b - a) * (np.arange(n) + .5) / n); ws += [sh[i] / n] * n
    return np.array(xs), np.array(ws)


def wq(x, w, p):
    o = np.argsort(x, kind='stable'); c = np.cumsum(w[o]) / w.sum()
    return float(x[o][np.searchsorted(c, p)])


def zsd(x, w, med, s, dom=None, cl=3.2):
    g = np.clip(x, dom[0], dom[1]) if dom else x
    z = np.clip((g - med) / s, -cl, cl); m = np.sum(w * z) / w.sum()
    return float(math.sqrt(np.sum(w * (z - m) ** 2) / w.sum()))


def svar(x, w, med, dom=None):
    return optimize.brentq(lambda s: zsd(x, w, med, s, dom) - 1.0, 0.01, 2.0, xtol=1e-12)


ccfit = {}
for key in (('1fc1e4fe', 'total'), ('737e5440', 'total'), ('1fc1e4fe', 'manufacturing'), ('737e5440', 'retail')):
    sh = vb(*key)
    mu, s = lognorm_fit(sh)
    xl, wl = lognorm_pts(mu, s)
    shn = np.array(sh) / sum(sh)
    unif = {top: pw_uniform(sh, top) for top in (.70, .85, 1.0)}
    ccfit[key] = {'shares': shn, 'mu': mu, 's': s, 'median_lognormal': math.exp(mu),
                  'median_uniform': wq(*unif[.85], .5), 'p_lt_10_lognormal': float(N.cdf((math.log(.10) - mu) / s)),
                  'p_gt_50_lognormal': float(1 - N.cdf((math.log(.505) - mu) / s)),
                  'svar_lognormal_at': lambda c, xl=xl, wl=wl: svar(xl, wl, c, CC_DOM),
                  'svar_uniform_at': lambda c, unif=unif: {t: svar(*unif[t], c, CC_DOM) for t in unif},
                  'unsure': float(next(r['pct'] for r in VB[key] if r['bin'] == 'Unsure'))}
TOT = [('1fc1e4fe', 'total'), ('737e5440', 'total')]
cc_med_ln = [ccfit[k]['median_lognormal'] for k in TOT]
cc_med_un = [ccfit[k]['median_uniform'] for k in TOT]
cc_v = float(np.mean(cc_med_ln))
# unsure answers read as answers above 15% (not missing at random): the lognormal median moves up
cc_unsure_shift = []
for k in TOT:
    sh = list(vb(*k)); u = ccfit[k]['unsure']; up = sum(sh[1:])
    sh2 = [sh[0]] + [x + u * x / up for x in sh[1:]]
    cc_unsure_shift.append(math.exp(lognorm_fit(sh2)[0]) - ccfit[k]['median_lognormal'])
cc_terms = {'chart_to_chart': abs(cc_med_ln[0] - cc_med_ln[1]) / 2,
            'shape_within_bin': abs(np.mean(cc_med_un) - cc_v),
            'unsure_answers': float(np.mean(cc_unsure_shift)) / 2}
cc_terms_q = math.sqrt(sum(v ** 2 for v in cc_terms.values()))
first_bin_known = [ccfit[k]['shares'][0] for k in TOT]
first_bin_all = [float(VB[k][0]['pct']) / 100 for k in TOT]
# manufacturing: Value Builder and Statistics Canada 27-10-0217 (2004, plants of 20+ employees)
SCB = [("0% of", 0.0, 0.0), ("1% to 9%", 0.01, 0.10), ("10% to 24%", 0.10, 0.25), ("25% to 49%", 0.25, 0.50),
       ("50% to 74%", 0.50, 0.75), ("75% to 100%", 0.75, 1.00)]
sc_rows = list(csv.DictReader(open(os.path.join(A.data_s, 'statcan_innov2005', 'x27100217', '27100217.csv'),
                                   encoding='utf-8-sig')))
SC = {}
for r in sc_rows:
    if r['GEO'] != 'Canada' or r['Type of plant'] != 'All plants' or not r['VALUE']:
        continue
    ind = r['North American Industry Classification System (NAICS)'].strip()
    c = r["Percentage range of the plant's total revenue"]
    d = SC.setdefault(ind, {})
    if c.startswith('Average'):
        d['avg'] = float(r['VALUE']) / 100
    for i, (l, a, b) in enumerate(SCB):
        if c.startswith(l):
            d[i] = float(r['VALUE']) / 100


def sc_quant(sh, p, tilt):
    acc = 0.0
    for i, (l, a, b) in enumerate(SCB):
        w = sh[i]
        if acc + w >= p:
            if a == b:
                return a
            f_ = (p - acc) / w
            if abs(tilt) < 1e-9:
                u = f_
            else:
                A_, B_, C_ = -tilt, 1 + tilt, -f_
                u = (-B_ + math.sqrt(B_ * B_ - 4 * A_ * C_)) / (2 * A_)
            return a + (b - a) * u
        acc += w
    return 1.0


def sc_mean(sh, tilt):
    return sum(sh[i] * (a + (b - a) * (0.5 - tilt / 6)) for i, (l, a, b) in enumerate(SCB) if a != b)


def sc_medians(ind):
    d = SC[ind]; tot = sum(d[i] for i in range(6)); sh = [d[i] / tot for i in range(6)]
    lo, hi = -1.0, 1.0
    for _ in range(80):                       # within-bin linear density, tilted until the mean is the published one
        m = (lo + hi) / 2
        if sc_mean(sh, m) > d['avg']:
            lo = m
        else:
            hi = m
    t = (lo + hi) / 2
    return {'shares': [round(x, 3) for x in sh], 'average': d['avg'], 'median_calibrated': sc_quant(sh, .5, t),
            'median_uniform': sc_quant(sh, .5, 0.0), 'tilt': t}


sc_mfg = sc_medians('Manufacturing [31-33]')
sc_339 = sc_medians('Miscellaneous manufacturing [339]')
mfg_vb = ccfit[('1fc1e4fe', 'manufacturing')]['median_lognormal']
mfg_v = (mfg_vb + sc_mfg['median_calibrated']) / 2
mfg_terms = {'between_sources': abs(mfg_vb - sc_mfg['median_calibrated']) / 2,
             'vb_shape': abs(ccfit[('1fc1e4fe', 'manufacturing')]['median_uniform'] - mfg_vb),
             'statcan_placement': abs(sc_mfg['median_uniform'] - sc_mfg['median_calibrated']) / 2}
mfg_terms_q = math.sqrt(sum(v ** 2 for v in mfg_terms.values()))
# Census SBO 2007 customer-class bound: carried from the second round's notes (not recomputed here)
sbo_txt = open(A.fit6_notes, encoding='utf-8').read()
msbo = re.search(r'no business or government customer class reaches 10% of sales in (\d+)% of firms under \$0\.5M receipts, '
                 r'(\d+)% at \$0\.5.1M, (\d+)% at \$1.2\.5M, (\d+)% at \$2\.5.5M; by sector \(receipts \$0\.5.5M\) (\d+)% '
                 r'food services, (\d+)% health care, (\d+)% retail', sbo_txt)
if not msbo:
    sys.exit('fit6 notes: the SBO 2007 bound sentence was not found')
sbo = [int(x) for x in msbo.groups()]
retail_cc = ccfit[('737e5440', 'retail')]
PEER_CC = {
    'v': rhu(cc_v), 'se': .02, 'was': CC_WAS,
    'definition': "the largest customer's share of last year's revenue",
    'by_industry': {'mfg': {'v': rhu(mfg_v), 'se': .02,
                            'note': (f"mean of Value Builder's manufacturing owners ({mfg_vb:.3f}, lognormal) and Statistics "
                                     f"Canada's manufacturing plants ({sc_mfg['median_calibrated']:.3f}, placed to match the "
                                     f"published average {sc_mfg['average'] * 100:.1f}%); SE .02 covers the sources' gap, the "
                                     f"within-bin shape and the placement ({mfg_terms_q:.3f} in quadrature). Miscellaneous "
                                     f"manufacturing (339) alone reads {sc_339['median_calibrated']:.3f}-"
                                     f"{sc_339['median_uniform']:.3f}")}},
    'se_note': (f"SE .02, one-sided in effect: the measured terms are small (charts {cc_terms['chart_to_chart']:.3f}, "
                f"within-bin shape {cc_terms['shape_within_bin']:.3f}, the {ccfit[TOT[0]]['unsure']:.0f}% and "
                f"{ccfit[TOT[1]]['unsure']:.0f}% 'unsure' answers {cc_terms['unsure_answers']:.3f}; {cc_terms_q:.3f} in "
                f"quadrature); the rest is the lean of Value Builder's base toward business customers, so sellers that "
                f"serve consumers sit lower (Value Builder retail {retail_cc['median_lognormal']:.2f}-"
                f"{retail_cc['median_uniform']:.2f})"),
    'source': (f"Value Builder Analytics owner-survey charts (Advisor News newsletter, N {VB[TOT[0]][0]['n_label']}): 'What "
               f"percentage of your overall revenue did your largest customer represent last year?', bins 1-15/16-25/26-50/"
               f"51+/unsure (two total-base charts, manufacturing and retail owners); Statistics Canada table 27-10-0217 "
               f"(Survey of Innovation 2005: share of the plant's 2004 revenue from its most important customer; plants of "
               f"{qv('daily_cov', 0):.0f}+ employees and ${qv('daily_cov', 1):,.0f}+ revenue)"),
    'method': (f"Cross-industry: the lognormal fitted by multinomial maximum likelihood to each total-base chart (unsure "
               f"left out), median {cc_med_ln[0]:.3f} and {cc_med_ln[1]:.3f}, mean {cc_v:.4f}. Robust to the shape: "
               f"{first_bin_known[0] * 100:.1f}% and {first_bin_known[1] * 100:.1f}% of known answers are 15% or less, so "
               f"the median is under .155 whatever the shape (uniform within bins {cc_med_un[0]:.3f} / {cc_med_un[1]:.3f}). "
               f"Every industry but manufacturing reads the cross-industry value"),
    'checks': {
        'charts_median_lognormal': [r3(x) for x in cc_med_ln], 'charts_median_uniform': [r3(x) for x in cc_med_un],
        'first_bin_share_known_answers': [r3(x) for x in first_bin_known],
        'first_bin_share_all_answers': first_bin_all,
        'p_lt_10_lognormal': [r3(ccfit[k]['p_lt_10_lognormal']) for k in TOT],
        'p_gt_50': {'lognormal': [r3(ccfit[k]['p_gt_50_lognormal']) for k in TOT],
                    'data': [r3(ccfit[k]['shares'][3]) for k in TOT],
                    'console_N_016_013': r3(1 - N.cdf((.505 - CC_WAS) / PEER_SD['cc']))},
        'retail_owners': {'median_lognormal': r3(retail_cc['median_lognormal']),
                          'median_uniform': r3(retail_cc['median_uniform'])},
        'statcan_manufacturing': {k: (r3(v) if isinstance(v, float) else v) for k, v in sc_mfg.items()},
        'statcan_misc_manufacturing_339': {k: (r3(v) if isinstance(v, float) else v) for k, v in sc_339.items()},
        'sbo_2007_bound_carried': {
            'share_with_no_business_or_government_class_at_10pct': {'under_0.5M': sbo[0] / 100, '0.5_1M': sbo[1] / 100,
                                                                    '1_2.5M': sbo[2] / 100, '2.5_5M': sbo[3] / 100},
            'by_sector_0.5_5M': {'food_services': sbo[4] / 100, 'health_care': sbo[5] / 100, 'retail': sbo[6] / 100},
            'note': ("carried from the second round's check (Census SBO 2007 PUMS), not recomputed: if no "
                     "business or government customer class reaches 10% of sales, no single such customer does, so "
                     "P(cc < .10) is at least that share for consumer-facing firms; not size-matched to Value Builder's base")}},
}

# ================================================================== PEER SPREADS
# ---- cc: the scale at which the clamped z has unit variance among peers, on the slider's domain, around the median
cc_sv_ln = [ccfit[k]['svar_lognormal_at'](PEER_CC['v']) for k in TOT]
cc_sv_un = [ccfit[k]['svar_uniform_at'](PEER_CC['v']) for k in TOT]
cc_sv_all = cc_sv_ln + [v for d in cc_sv_un for v in d.values()]
cc_sd_v = float(np.mean(cc_sv_ln))
sd_retail = ccfit[('737e5440', 'retail')]['svar_lognormal_at'](ccfit[('737e5440', 'retail')]['median_lognormal'])
sd_mfg = ccfit[('1fc1e4fe', 'manufacturing')]['svar_lognormal_at'](PEER_CC['by_industry']['mfg']['v'])
sdz_was = [zsd(*lognorm_pts(ccfit[k]['mu'], ccfit[k]['s']), CC_WAS, PEER_SD['cc'], CC_DOM) for k in TOT]
cc_sd_terms = {'charts': abs(cc_sv_ln[0] - cc_sv_ln[1]) / 2, 'shape': (max(cc_sv_all) - min(cc_sv_all)) / 2,
               'industry_mix': abs(sd_mfg - sd_retail) / 2}
SD_CC = {
    'v': rhu(cc_sd_v), 'se': .02, 'was': PEER_SD['cc'], 'domain': list(CC_DOM),
    'parts': {'lognormal_by_chart': [r3(x) for x in cc_sv_ln],
              'uniform_within_bins_top_070_085_100': [[r3(v) for v in d.values()] for d in cc_sv_un],
              'all_shapes': [r3(min(cc_sv_all)), r3(max(cc_sv_all))], 'all_shapes_mean': r3(float(np.mean(cc_sv_all))),
              'within_industry': {'manufacturing': r3(sd_mfg), 'retail': r3(sd_retail)},
              'sd_of_clamped_z_at_the_old_013_and_016': [r3(x) for x in sdz_was]},
    'se_note': (f"SE .02 covers the chart-to-chart gap ({cc_sd_terms['charts']:.3f}), the unobserved shape inside the "
                f"51%+ bin ({min(cc_sv_all):.3f}-{max(cc_sv_all):.3f} across lognormal and uniform placements) and the "
                f"spread between industries a single value ignores (retail {sd_retail:.3f}, manufacturing "
                f"{sd_mfg:.3f})"),
    'source': PEER_CC['source'].split('; Statistics Canada')[0],
    'method': (f"PEER_SD.cc = the scale at which z = clamp((cc - median)/s, +-3.2) has unit variance among peers, cc first "
               f"held to the slider's domain [{CC_DOM[0]:.2f}, {CC_DOM[1]:.2f}] (a typed value is clamped to it), the "
               f"median at the shipped {PEER_CC['v']:.2f}; the lognormal fit of each total-base chart gives "
               f"{cc_sv_ln[0]:.4f} and {cc_sv_ln[1]:.4f}, mean {cc_sd_v:.5f}. At .13 around .16 the clamped z had SD "
               f"{min(sdz_was):.2f}-{max(sdz_was):.2f}: cc carried more than an equal share of the composite. A log or "
               f"logit scale would fit the skew better than any linear spread"),
}
# ---- grw: Statistics Canada CSBC (tables 33-10-0778, 0924, 1123), the verifier's method (v_grw.py), on the slider
G_LO, G_HI = SLIDER['grw'][0] / 100, SLIDER['grw'][1] / 100
CL = 3.2


def csbc_parse(c):
    c = c.strip()
    m = re.match(r'Revenues were (higher|lower|the same) in \d{4}$', c)
    if m:
        return ('top', m.group(1))
    m = re.match(r'Revenues were (higher|lower), average percentage$', c)
    if m:
        return ('avg', m.group(1))
    m = re.match(r'Revenues were (?:up to|1% to) 9% (higher|lower)', c)
    if m:
        return ('bin', m.group(1), 0)
    m = re.match(r'Revenues were (\d+)% to (\d+)% (higher|lower)', c)
    if m:
        return ('bin', m.group(3), int(m.group(1)))
    if re.match(r'Revenues were 100% or more higher', c):
        return ('bin', 'higher', 100)
    if re.match(r'Revenues were 100% lower', c):
        return ('bin', 'lower', 100)
    return None


def csbc_load(path, groups):
    rd = csv.DictReader(open(path, encoding='utf-8-sig'))
    col = [k for k in rd.fieldnames if 'compared with' in k][0]
    D = {}
    for r in rd:
        if r['GEO'] != 'Canada' or r['VALUE'] in ('', None) or r['Business characteristics'].strip() not in groups:
            continue
        p = csbc_parse(r[col])
        if p is None:
            continue
        d = D.setdefault((r['REF_DATE'], r['Business characteristics'].strip()), {'top': {}, 'avg': {}, 'higher': {}, 'lower': {}})
        v = float(r['VALUE']); q = (r['STATUS'] or 'A').strip() or 'A'
        if p[0] == 'top':
            d['top'][p[1]] = (v, q)
        elif p[0] == 'avg':
            d['avg'][p[1]] = (v, q)
        else:
            d[p[1]][p[2]] = (v, q)
    return D


LOWS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


def side_points(shares, avg, scheme, sign, n=40):
    def pts(param):
        xs, ws = [], []
        for lo in LOWS:
            w = shares.get(lo, 0.0)
            if w <= 0:
                continue
            if sign < 0 and lo == 100:                # '100% lower': revenue went to zero
                xs.append(100.0); ws.append(w); continue
            width = 100.0 if lo == 100 else 10.0
            if scheme == 'uni':
                g = lo + width * (np.arange(n) + .5) / n; xs += list(g); ws += [w / n] * n
            elif scheme == 'cmp':
                g = lo + param * width * (np.arange(n) + .5) / n; xs += list(g); ws += [w / n] * n
            else:
                xs.append(5.0 if lo == 0 else float(lo)); ws.append(w * param)
                g = lo + width * (np.arange(n) + .5) / n; xs += list(g); ws += [w * (1 - param) / n] * n
        return np.array(xs), np.array(ws)

    def mean(a):
        return float(np.sum(a[0] * a[1]) / np.sum(a[1]))
    if scheme == 'uni' or avg is None:
        return pts(1.0 if scheme == 'cmp' else 0.0) if scheme != 'heap' else pts(0.0)
    if scheme == 'cmp':                               # compressed toward the bin's low edge until the side mean = average
        if mean(pts(1.0)) <= avg:
            return pts(1.0)
        if mean(pts(0.0)) >= avg:
            return pts(0.0)
        lo_, hi_ = 0.0, 1.0
        for _ in range(60):
            m = (lo_ + hi_) / 2
            if mean(pts(m)) < avg:
                lo_ = m
            else:
                hi_ = m
        return pts((lo_ + hi_) / 2)
    if mean(pts(0.0)) <= avg:                         # heaped at round numbers until the side mean = average
        return pts(0.0)
    if mean(pts(1.0)) >= avg:
        return pts(1.0)
    lo_, hi_ = 0.0, 1.0
    for _ in range(60):
        m = (lo_ + hi_) / 2
        if mean(pts(m)) > avg:
            lo_ = m
        else:
            hi_ = m
    return pts((lo_ + hi_) / 2)


def csbc_build(top, hi_sh, lo_sh, avg_h, avg_l, scheme):
    tot = sum(top.values()); H, S_, L = top['higher'] / tot, top['the same'] / tot, top['lower'] / tot
    xh, wh = side_points(hi_sh, avg_h, scheme, +1)
    xl, wl = side_points(lo_sh, avg_l, scheme, -1)
    x = np.concatenate([xh / 100.0, -xl / 100.0, [0.0]]); w = np.concatenate([wh / wh.sum() * H, wl / wl.sum() * L, [S_]])
    o = np.argsort(x, kind='stable')
    return x[o], w[o]


def csbc_unpack(d):
    top = {k: d['top'][k][0] for k in ('higher', 'the same', 'lower')}

    def sh(side):
        tot = sum(v for v, q in d[side].values())
        return {lo: v / tot for lo, (v, q) in d[side].items()} if tot > 0 else {}
    return top, sh('higher'), sh('lower'), d['avg'].get('higher', (None,))[0], d['avg'].get('lower', (None,))[0]


def zvar(x, w, med, s, censor):
    g = np.clip(x, G_LO, G_HI) if censor else x
    z = np.clip((g - med) / s, -CL, CL); m = np.sum(w * z) / np.sum(w)
    return float(np.sum(w * (z - m) ** 2) / np.sum(w))


def s_unit(x, w, med, censor):
    return optimize.brentq(lambda s: zvar(x, w, med, s, censor) - 1, 0.005, 2.0, xtol=1e-10)


ABS_MID = {'B': 3.75, 'C': 6.25, 'D': 8.75, 'E': 12.5}   # quality letters read as absolute SEs in points (verifier)


def csbc_draw(d, rng_):
    def pert(v, q, nA):
        if q == 'A':
            p = v / 100.0; se = min(1.25, 100 * math.sqrt(max(p * (1 - p), 1e-6) / nA))
        else:
            se = ABS_MID.get(q, 12.5)
        return max(0.0, rng_.normal(v, se))
    return {'top': {k: (pert(v, q, 1000), q) for k, (v, q) in d['top'].items()},
            'avg': {k: (max(0.5, pert(v, q, 300)), q) for k, (v, q) in d['avg'].items()},
            'higher': {k: (pert(v, q, 150), q) for k, (v, q) in d['higher'].items()},
            'lower': {k: (pert(v, q, 150), q) for k, (v, q) in d['lower'].items()}}


CLASSES = ['5 to 19 employees', '20 to 99 employees']
CSBC_FILES = [('33100778', '2023'), ('33100924', '2024'), ('33101123', '2025')]
grw = {}
PTS = [-0.25, -0.20, -0.15, -0.10, 0.10, 0.15, 0.20, 0.30, 0.50]
cdf_acc = {p: [] for p in PTS}
mc_se = []
rng2 = np.random.default_rng(20261016)
for tab, yr in CSBC_FILES:
    D = csbc_load(os.path.join(A.data_s, 'statcan_csbc', 'x' + tab, tab + '.csv'), CLASSES)
    for (ref, g), d in D.items():
        top, hs, ls, ah, al = csbc_unpack(d)
        for scheme in ('uni', 'cmp', 'heap'):
            x, w = csbc_build(top, hs, ls, ah, al, scheme)
            med = wq(x, w, .5)
            grw[(ref, g, scheme)] = {'s_slider': s_unit(x, w, med, True), 's_free': s_unit(x, w, med, False),
                                     'sdz_was_slider': math.sqrt(zvar(x, w, med, PEER_SD['grw'], True)),
                                     'below': float(np.sum(w[x < G_LO])), 'above': float(np.sum(w[x > G_HI]))}
            for p in PTS:
                cdf_acc[p].append(float(np.sum(w[x <= p + 1e-12]) / np.sum(w)))
        draws = []
        for _ in range(A.mc):
            t2, h2, l2, a2, b2 = csbc_unpack(csbc_draw(d, rng2))
            x, w = csbc_build(t2, h2, l2, a2, b2, 'cmp')
            draws.append(s_unit(x, w, wq(x, w, .5), True))
        mc_se.append(float(np.std(draws, ddof=1)))
s_sl = {k: v['s_slider'] for k, v in grw.items()}
v_var = float(np.mean(list(s_sl.values())))
grid = np.arange(.100, .2505, .0005)
data_F = {p: float(np.mean(v)) for p, v in cdf_acc.items()}
err = [float(np.mean([abs(N.cdf(p / s) - data_F[p]) for p in PTS])) for s in grid]
v_pct = float(grid[int(np.argmin(err))])
grw_v = (v_var + v_pct) / 2
cls_mean = {g: float(np.mean([v for (r, gg, sc), v in s_sl.items() if gg == g])) for g in CLASSES}
plc_mean = {sc: float(np.mean([v for (r, gg, s2), v in s_sl.items() if s2 == sc])) for sc in ('uni', 'cmp', 'heap')}
yr_mean = {r: float(np.mean([v for (rr, gg, sc), v in s_sl.items() if rr == r])) for r in sorted({k[0] for k in s_sl})}
TRANSFER = .02     # judgment (lane S): Canada to the US, all operating businesses to sellers
grw_terms = {'size_class': abs(cls_mean[CLASSES[0]] - cls_mean[CLASSES[1]]) / 2,
             'placement': (max(plc_mean.values()) - min(plc_mean.values())) / 2,
             'year': float(np.std(list(yr_mean.values()), ddof=1)),
             'sampling': float(np.mean(mc_se)),
             'definition': abs(v_var - v_pct) / 2,
             'transfer': TRANSFER}
grw_se = math.sqrt(sum(v ** 2 for v in grw_terms.values()))
s_free = float(np.mean([v['s_free'] for v in grw.values()]))
sdz_was = [v['sdz_was_slider'] for v in grw.values()]
below = float(np.mean([v['below'] for v in grw.values()])); above = float(np.mean([v['above'] for v in grw.values()]))
SD_GRW = {
    'v': rhu(grw_v), 'se': r3(grw_se), 'was': PEER_SD['grw'], 'domain': [G_LO, G_HI],
    'parts': {'variance_matched_slider_domain': r3(v_var), 'percentile_match': r3(v_pct),
              'by_class': {k: r3(v) for k, v in cls_mean.items()}, 'by_placement': {k: r3(v) for k, v in plc_mean.items()},
              'by_year': {k: r3(v) for k, v in yr_mean.items()},
              'variance_matched_without_the_slider_domain': r3(s_free),
              'share_outside_the_slider': {'below': r3(below), 'above': r3(above)},
              'sd_of_clamped_z_at_013': [r3(min(sdz_was)), r3(max(sdz_was))]},
    'se_note': ('SE ' + str(r3(grw_se)) + ' = ' + ', '.join(f"{k.replace('_', ' ')} {v:.3f}" for k, v in grw_terms.items())
                + ' in quadrature (transfer: Canada to the US and operating businesses to sellers, judgment; sampling: '
                  'Monte Carlo with the quality letters read as absolute SEs)'),
    'source': ("Statistics Canada, Canadian Survey on Business Conditions, tables 33-10-0778, 33-10-0924 and 33-10-1123 "
               "(revenue in 2023, 2024 and 2025 against the year before: higher / same / lower, 10-point bins and each "
               "side's average; employer businesses with 5-19 and 20-99 employees)"),
    'method': (f"Each class-year is a distribution: 'the same' at 0, each bin filled three ways (uniform; compressed toward "
               f"its low edge until the side's mean is the published average; heaped at round numbers to that average). "
               f"Variance-matched on the slider's domain [{G_LO:.2f}, {G_HI:.2f}] (a typed value is clamped to it): the "
               f"scale at which clamp((g - median)/s, +-3.2) has unit variance, mean {v_var:.4f} over 3 years x 2 classes x "
               f"3 placements; percentile-matched: the s at which ncdf(g/s) best matches the observed CDF at +-10-50% "
               f"(mean absolute error), {v_pct:.4f}. PEER_SD.grw = their mean, {grw_v:.4f}. Without the slider's domain the "
               f"variance-matched scale is {s_free:.3f} (about .20): the tails it fits cannot be entered. At .13 the "
               f"clamped growth z had SD {min(sdz_was):.2f}-{max(sdz_was):.2f}: growth carried more than an equal share of "
               f"the composite"),
}
# ---- kept spreads and levels: checks
OWN_MAP = MENU['own']                      # Low .14, Moderate .42, High .72, Critical .95
own_rows = {'rev_under_1m': vb('598217fe', 'rev_under_1m'), 'rev_1m_10m': vb('598217fe', 'rev_1m_10m')}
own_cuts = np.array(CUTS['own'])


def oprobit(sh, n=5000):
    cnt = np.array(sh, float) / sum(sh) * n

    def nll(p):
        m, ls = p; s = math.exp(ls)
        c = np.concatenate([[0.0], N.cdf((own_cuts - m) / s), [1.0]])
        return -float(np.sum(cnt * np.log(np.clip(np.diff(c), 1e-12, 1))))
    r = optimize.minimize(nll, [0.5, math.log(0.25)], method='Nelder-Mead', options={'xatol': 1e-10, 'fatol': 1e-12})
    return float(r.x[0]), float(math.exp(r.x[1]))


own_fit, own_menu_sd, own_shift_sd, own_single = {}, {}, {}, {}
for k, v in own_rows.items():
    p = np.array(v, float) / sum(v)
    own_fit[k] = oprobit(v)
    vals = np.array(sorted(OWN_MAP))                          # hardly -> Low, little -> Moderate, lot -> High, not survive -> Critical
    mean_ = float(np.sum(p * vals)); own_menu_sd[k] = float(math.sqrt(np.sum(p * (vals - mean_) ** 2)))
    sv = np.array([vals[1], vals[2], vals[3], vals[3]])       # shifted: hardly -> Moderate, little -> High, lot -> Critical
    ms = float(np.sum(p * sv)); own_shift_sd[k] = float(math.sqrt(np.sum(p * (sv - ms) ** 2)))
    own_single[k] = {'low_only': own_cuts[0] - N.ppf(p[0]) * PEER_SD['own'],
                     'low_or_moderate': own_cuts[1] - N.ppf(p[0]) * PEER_SD['own']}
REPS = {'rev_under_1m': (250e3, 400e3, 600e3), 'rev_1m_10m': (2.0e6, 3.16e6, 4.5e6)}   # class representatives (judgment)
lines = {'ordered_probit': [], 'low_only': [], 'low_or_moderate': []}
for lo in REPS['rev_under_1m']:
    for hi in REPS['rev_1m_10m']:
        z1, z2 = z_of_rev(lo), z_of_rev(hi)
        for tag in lines:
            m1 = own_fit['rev_under_1m'][0] if tag == 'ordered_probit' else own_single['rev_under_1m'][tag]
            m2 = own_fit['rev_1m_10m'][0] if tag == 'ordered_probit' else own_single['rev_1m_10m'][tag]
            b = (m2 - m1) / (z2 - z1); lines[tag].append((m2 - b * z2, b))
own_level = {t: {'at_z0': r3(float(np.median([a for a, b in L]))), 'range': [r3(min(a for a, b in L)), r3(max(a for a, b in L))],
                 'slope': r3(float(np.median([b for a, b in L])))} for t, L in lines.items()}
rec_sd = {}
for chart, series in (('6c180576', 'manufacturing'), ('fcdb44f7', 'retail'), ('9537f3d8', 'construction')):
    v = vb(chart, series); p = np.array(v, float) / sum(v)
    edges_ = [(0.0, 0.0), (0.01, 0.255), (0.255, 0.505), (0.505, 0.755), (0.755, 1.0)]
    xs_, ws_ = [], []
    for (a, b), w in zip(edges_, p):
        if a == b:
            xs_.append(a); ws_.append(w)
        else:
            xs_ += list(a + (b - a) * (np.arange(200) + .5) / 200); ws_ += [w / 200] * 200
    xx, ww = np.array(xs_), np.array(ws_); m_ = float(np.sum(xx * ww))
    rec_sd[series] = float(math.sqrt(np.sum(ww * (xx - m_) ** 2)))
epi57 = qf('epi_57')
mgt_cut_deep, mgt_cut_solid = CUTS['mgt'][2], CUTS['mgt'][1]
epi_rev = Q['epi_rev']['v']
z5, z25 = z_of_rev(5e6), z_of_rev(25e6)
lm_lt20, lm_20_50 = qf('lm_lt20', 1), qf('lm_20_50', 1)
fin_cut = CUTS['fin'][2]


def fin_console(rev):
    return FIN_A + FIN_B * max(-1, min(1, z_of_rev(rev)))


CHECKS = {
    'own': {'kept': PEER_SD['own'],
            'value_builder_3_month_absence': {k: {'ordered_probit_s': r3(v[1]), 'median': r3(v[0]),
                                                  'menu_coded_sd': r3(own_menu_sd[k]), 'shifted_mapping_sd': r3(own_shift_sd[k])}
                                              for k, v in own_fit.items()},
            'note': (f"Value Builder ('out of action for 3 months', N {VB[('598217fe', 'rev_under_1m')][0]['n_label']}): the "
                     f"spread within a revenue class is {own_fit['rev_1m_10m'][1]:.3f}-{own_fit['rev_under_1m'][1]:.3f} with "
                     f"the four answers mapped one-to-one onto the four menu levels, "
                     f"{min(own_shift_sd.values()):.2f}-{max(own_shift_sd.values()):.2f} with them shifted half a step; .25 "
                     f"is kept (the value depends on the mapping)")},
    'rec': {'kept': PEER_SD['rec'], 'value_builder_within_industry_sd': {k: r3(v) for k, v in rec_sd.items()},
            'mean': r3(float(np.mean(list(rec_sd.values())))), 'sd_across': r3(float(np.std(list(rec_sd.values()), ddof=1))),
            'note': ("Value Builder 'What percentage of your sales is recurring?' (none at 0, uniform within bins): "
                     + ', '.join(f'{k} {v:.3f}' for k, v in rec_sd.items())
                     + f"; mean {np.mean(list(rec_sd.values())):.3f}. Owner-defined 'recurring'; three of 16 industries. "
                       f".28 is kept")},
    'own_level': {'kept': OWN_A, 'value_builder_level_at_z0': own_level,
                  'note': (f"The 3-month item bounds the level rather than identifying it: 'hardly suffer' read as Low only "
                           f"gives {own_level['low_only']['at_z0']:.2f} at z = 0, read as Low or Moderate "
                           f"{own_level['low_or_moderate']['at_z0']:.2f} (ordered probit, one-to-one: "
                           f"{own_level['ordered_probit']['at_z0']:.2f}; slope {own_level['ordered_probit']['slope']:.3f}/z "
                           f"against the fitted {OWN_B}). {OWN_A} lies inside. Revenue classes placed on the size axis "
                           f"through the fitted seller bridge at $250k-600k and $2.0M-4.5M (judgment)")},
    'mgt_level': {'kept': MGT_A,
                  'epi_2023_very_comfortable_with_management_taking_over': epi57,
                  'median_if_deep_only': r3(mgt_cut_deep + PEER_SD['mgt'] * N.ppf(epi57)),
                  'median_if_solid_or_deep': r3(mgt_cut_solid + PEER_SD['mgt'] * N.ppf(epi57)),
                  'console_at_5M_25M_revenue': [r3(MGT_A + MGT_B * max(-1, min(1, z))) for z in (z5, z25)],
                  'note': (f"Exit Planning Institute 2023 (respondents {epi_rev[0]:.0f}% under $5M revenue, "
                           f"{epi_rev[1]:.0f}% $5-25M, {epi_rev[2] + epi_rev[3] + epi_rev[4]:.0f}% above $25M; "
                           f"self-selected): {epi57 * 100:.0f}% 'very comfortable' with their management team taking over. "
                           f"Read as Deep: median {mgt_cut_deep + PEER_SD['mgt'] * N.ppf(epi57):.2f}; as Solid or Deep "
                           f"{mgt_cut_solid + PEER_SD['mgt'] * N.ppf(epi57):.2f}, the console's "
                           f"{MGT_A + MGT_B * max(-1, min(1, z5)):.2f}-{MGT_A + MGT_B * max(-1, min(1, z25)):.2f} at $5-25M. "
                           f"A weak check")},
    'fin': {'kept': f'{FIN_A} + {FIN_B} z',
            'lisowsky_minnis_audited_gaap_share': {'revenue_under_20M': lm_lt20, 'revenue_20_50M': lm_20_50,
                                                   'firm_years': [qv('lm_lt20', 0), qv('lm_20_50', 0)],
                                                   'all_filers': qf('lm_37')},
            'median_if_audit_means_top_level': [r3(fin_cut + PEER_SD['fin'] * N.ppf(lm_lt20)),
                                                r3(fin_cut + PEER_SD['fin'] * N.ppf(lm_20_50))],
            'console_at_20M_50M_revenue': [r3(fin_console(20e6)), r3(fin_console(50e6))],
            'note': ("Lisowsky and Minnis (IRS Schedule M-3 filers with $10M+ of assets, 2008-10): audited GAAP statements "
                     f"{lm_lt20 * 100:.0f}% under $20M of revenue, {lm_20_50 * 100:.0f}% at $20-50M. Not a bound: the "
                     "console's top level is 'reviewed or audited, with a QoE', and the sample tilts toward audits. A weak "
                     "check")},
    'ret': {'kept': PEER_SD['ret'], 'little_stream_store_sd': ls_sd,
            'note': (f"Retention's scale stays .13; Little Stream's Shopify stores spread {ls_sd:.3f}. With count medians "
                     f"near .25, values near the slider's floor clamp")},
}

# ================================================================== FLAGS (the strings the Data tab shows)
old_flags = PRR['flags']
FLAGS = {k: v for k, v in old_flags.items() if k not in ('auto.ret', 'ecom.ret', 'msp.rec')}
FLAGS['dist.ret'] = (f"Count definition: one-year survival of Belgian firm-to-firm links (NBB WP 444, Fig. 8, image-read; "
                     f"links of EUR {qv('nbb_thr'):.0f} a year or more) is {min(nbb_u):.2f}-{max(nbb_u):.2f} by count "
                     f"(about {nbb_u_late:.2f} in 2010-18) and {min(nbb_w):.2f}-{max(nbb_w):.2f} by value; US importers' "
                     f"relationships with a foreign supplier survive the year {ifdp['age_0']:.2f} of the time when new and "
                     f"{ifdp['age_9']:.2f} at nine years (FRB IFDP 1218, Fig. 4, 2011, image-read). .80 is above every count reading but long-standing relationships. "
                     f"Not shipped: whole-economy links, not a small distributor's customers")
FLAGS['mfg.ret'] = (f"As for dist: link survival about {nbb_u_late:.2f} by count and {nbb_w_late:.2f} by value (NBB WP 444, "
                    f"Fig. 8); Belgian manufacturers drop suppliers worth a median {qv('nber_a5', 7) * 100:.1f}% of input "
                    f"spending a year (mean {qv('nber_a5', 5) * 100:.1f}%, {qv('nber_a5', 9):,.0f} firm-years; Baqaee "
                    f"et al., NBER WP 31231, Table A5), so about {1 - qv('nber_a5', 7):.2f} by value. .78 is above the "
                    f"count readings")
FLAGS['home.ret'] = (f"No count measure. ServiceTitan / Thrive Analytics survey of {qv('st_n'):,.0f}+ US residential "
                     f"contractors (2023): repeat customers are {home_rep * 100:.0f}% of annual revenue, so last year's "
                     f"revenue kept is at most {home_rep:.2f} x (1 + g) = {home_rep * (1 + home_g):.2f} at the peer growth "
                     f"{home_g:.2f}, against .70; only maintenance-agreement members come near .70")
FLAGS['land.rec'] = old_flags['land.rec'] + (f" Aspire 2026 (Thrive Analytics, {qv('aspire_n'):,.0f} commercial landscape "
                                             f"contractors, May 2025): {qv('aspire_59'):.0f}% earn the majority of revenue "
                                             f"from recurring maintenance, so the commercial median is above .50.")
FLAGS['staff.rec'] = (f"Definition: temporary staffing is {c320_temp * 100:.1f}% of NAICS 561320 revenue (Census 2022; "
                      f"temp-to-perm {c320_ttp * 100:.1f}%, permanent placement {c320_perm * 100:.1f}%), billed continuously "
                      f"under client contracts: about {c320_temp:.2f} if work that renews without a new sale counts as "
                      f"contracted, about 0 if only subscriptions and service agreements do. .30 matches neither reading; "
                      f"the slider's label is not changed this round")
FLAGS['wash.rec'] = (f"MarQ (market-research page, method not published): memberships about {qv('marq_sub', 0):.0f}% of "
                     f"2025 US car-wash revenue (USD {qv('marq_sub', 1)}bn of {qv('marq_size', 1)}bn), express tunnels "
                     f"{qv('marq_express'):.0f}% of revenue; Mister Car Wash members {qv('mcw_uwc', 0):.0f}% of wash sales "
                     f"in 2025 ({qv('mcw_uwc', 1):.0f}% in 2024; MarQ quotes {qv('marq_mcw', 1):.0f}%). A revenue-weighted "
                     f"share driven by express chains: Census 2022 NAICS 811192 lines that are small by revenue are common "
                     f"by site (self-service {wash_lines['self_service'][0] * 100:.1f}% of revenue, "
                     f"{wash_lines['self_service'][1] * 100:.1f}% of establishments; hand washing "
                     f"{wash_lines['hand'][0] * 100:.1f}% and {wash_lines['hand'][1] * 100:.1f}%), so the median seller sits "
                     f"below .35. Kept hand-set, not relabelled")
FLAGS['msp.ret'] = (f"ScalePad 2026 (1,100+ North American MSPs): client churn median {churn26 * 100:.1f}% (no period "
                    f"stated), so {1 - churn26:.2f}; ScalePad 2025: retention median {ret25:.2f} ({qv('sp25_ret_text'):.0f}% "
                    f"of MSPs below half); IT Glue 2021: {qv('itg_churn', 0):.0f}% of {qv('itg_n', 0):,.0f} respondents under "
                    f"{qv('itg_churn', 1):.0f}% churn. Pooled as the recurring share is, mean {msp_ret_pool['mean']:.2f} (SE "
                    f"{msp_ret_pool['se']:.2f}): .87 is not rejected. Only about a third of MSPs track churn")
FLAGS['medical.ret'] = (f"Dental only: Henry Schein One 2026 Catalyst Index, practices with 1-7 locations average "
                        f"{hs_mean * 100:.0f}% patient retention (top 10% {hs_top * 100:.0f}%; 8+ locations "
                        f"{qf('hs1_dso', 0) * 100:.0f}%), counting active patients who return within {qv('hs1_def'):.0f} "
                        f"months; a 12-month count reads lower ({hs_12m:.2f} at a constant hazard). No physician figure "
                        f"(the console maps medical to physician offices); .82 stays")
FLAGS['staff.ret'] = (f"ClearlyRated (first-party staffing research): the average staffing firm churns "
                      f"{qv('cr_staff', 0):.0f} or more clients per {qv('cr_staff', 1):.0f} in a normal year, about "
                      f"{qv('cr_table'):.0f}% annual client retention; .70 is 10 points below the only sourced figure")
FLAGS['wash.ret'] = (f"Members only (Rinsed, {qv('rinsed_sites'):,.0f}+ washes): monthly member churn "
                     f"{min(rinsed.values()) * 100:.1f}-{max(rinsed.values()) * 100:.1f}%, so "
                     f"{min((1 - c) ** 12 for c in rinsed.values()):.2f}-{max((1 - c) ** 12 for c in rinsed.values()):.2f} "
                     f"of members stay a year (the median wash's average member lifetime, {life} months, gives "
                     f"{math.exp(-12 / life):.2f}); {qv('rinsed_winback')}% of new 2025Q4 signups were win-backs. Retail "
                     f"customers are not measured: the count is not identified")
FLAGS['saas.ret'] = (f"Depends on population: micro-SaaS sold on Empire Flippers {np.median(ef_ret):.2f} (median, "
                     f"n={len(ef_ret)}); ChartMogul top-quartile customer retention {qf('cm_top', 0):.2f}-{qf('cm_top', 1):.2f} "
                     f"($3-30M ARR), {qv('cm_share', 0):.0f}-{qv('cm_share', 1):.0f}% of SaaS businesses above "
                     f"{qv('cm_share', 2):.0f}%; KBCM 2021 ($5M+ ARR) logo {1 - qf('kbcm_logo'):.2f}; SaaS Capital 2025 "
                     f"median gross revenue retention {qf('rb32_med', 1):.2f} (by value). .88 fits B2B firms of $5M+ ARR")
FLAGS['prof.ret'] = (f"ClearlyRated: the much-quoted 'around {qv('cr_prof'):.0f} percent' professional-services retention "
                     f"comes from an older dataset, to be treated as directional; no first-party accounting or legal "
                     f"figure. .84 is probably that number")
FLAGS['ecom.rec'] = (f"Definition: {len(ef_ecom_sub)} of {len(ef_ecom):,} Empire Flippers e-commerce listings "
                     f"({len(ef_ecom_sub) / len(ef_ecom) * 100:.1f}%) carry any subscription product, so subscriptions alone "
                     f"put the median near 0; .18 needs repeat orders counted. The slider's label is not changed this round")
FLAGS['prof.rec'] = (f"Census 2022: general accounting, bookkeeping and payroll are {prof_lines['541211'] * 100:.1f}% of "
                     f"CPA-office (541211) revenue and {prof_lines['541219'] * 100:.1f}% of other accounting (541219) "
                     f"revenue: usually monthly engagements, but service type, not contract status. Legal: nothing")
FLAGS_REMOVE = {k: 'ships as an aggregate cell this round' for k in ('auto.ret', 'ecom.ret', 'msp.rec') if k in old_flags}

DEF_REC_CHECK = (
    "Not adopted this round: the slider keeps 'Recurring or contracted revenue'. Two readings: (a) subscriptions, memberships "
    "and service agreements billed on a schedule until the customer cancels; (b) anything under a contract that renews "
    "without a new sale. MSP managed-service revenue is recurring under both (msp ships). They part where work is "
    f"contracted but not subscribed: staffing {c320_temp:.2f} under (b) (temporary staffing's share of NAICS 561320 revenue) "
    f"and about 0 under (a); e-commerce about 0 under (a) ({len(ef_ecom_sub)} of {len(ef_ecom):,} listings sell any "
    f"subscription); accounting's monthly-type lines {prof_lines['541211']:.3f} / {prof_lines['541219']:.3f} of revenue "
    f"(541211 / 541219; service type); commercial landscaping above .50 ({qv('aspire_59'):.0f}% of {qv('aspire_n'):,.0f} "
    f"contractors earn a majority from recurring maintenance); car washes' {qv('marq_sub', 0):.0f}% is a revenue-weighted "
    f"market share, not the median seller. Fitness (.70) and software (.85) stay judgment with their checks. Reading (a) is "
    f"unambiguous but would restate staffing, distribution, manufacturing and professional services with no data, and "
    f"needs a relabelled slider and a review of the contracts intervention.")

# ================================================================== brief check, sources, summary
BRIEF = {'ecom.ret': (.25, .05), 'auto.ret': (.45, .05), 'rest.ret': (.27, .10), 'msp.rec': (.42, .07),
         'wash.gm': (.80, .055), 'cc': (.14, .02), 'cc.mfg': (.19, .02), 'PEER_SD.cc': (.18, .02), 'PEER_SD.grw': (.16, .03)}
OURS = {'ecom.ret': (ECOM['v'], ECOM['se'], ecom_mean), 'auto.ret': (AUTO['v'], AUTO['se'], (auto_lo + auto_hi) / 2),
        'rest.ret': (REST['v'], REST['se'], rest_mid), 'msp.rec': (MSP_REC['v'], MSP_REC['se'], msp_mean),
        'wash.gm': (W_LEVEL, r3(w_se), measured), 'cc': (PEER_CC['v'], PEER_CC['se'], cc_v),
        'cc.mfg': (PEER_CC['by_industry']['mfg']['v'], .02, mfg_v), 'PEER_SD.cc': (SD_CC['v'], SD_CC['se'], cc_sd_v),
        'PEER_SD.grw': (SD_GRW['v'], SD_GRW['se'], grw_v)}
BRIEF_CHECK = {}
for k, (bv, bse) in BRIEF.items():
    v, se, raw = OURS[k]
    BRIEF_CHECK[k] = {'brief': [bv, bse], 'shipped': [v, se], 'unrounded': round(raw, 5),
                      'material': bool(abs(v - bv) > .5 * bse or abs(se - bse) > .5 * bse)}
BRIEF_CHECK['wash.gm']['note'] = (f"measured {measured:.4f} (mean of years) / {wash['A']['pooled_site_years']:.4f} (site-years "
                                  f"pooled); .835 - .03 = .805, which rounds half up to .81, so .80 is a shade of "
                                  f"{shade:.3f}: shipped at .80 as the verifier read it (0.2 SE)")
BRIEF_CHECK['PEER_SD.cc']['note'] = (f"lognormal on the slider domain {cc_sd_v:.5f}, which rounds to .18; across all within-bin "
                                     f"shapes {min(cc_sv_all):.3f}-{max(cc_sv_all):.3f}, mean {np.mean(cc_sv_all):.3f} (.19 "
                                     f"rounded): the choice of shape moves it by under half an SE")
BRIEF_CHECK['PEER_SD.grw']['note'] = (f"variance-matched {v_var:.4f}, percentile-matched {v_pct:.4f}")
BRIEF_CHECK['msp.rec']['note'] = f'SE {r3(msp_se)} reported at three decimals (the brief rounds it to .07)'
BRIEF_CHECK['ecom.ret']['note'] = f'SE {r3(ecom_se)} by the stated rule (the brief: about .05)'
BRIEF_CHECK['rest.ret']['note'] = (f"the coordinator's mid-round rule replaced the brief's .21: ({rest_v:.3f} + "
                                   f"{rest_central:.3f}) / 2 = {rest_mid:.4f}; the stated .212 and the bridge stay in parts")

IMAGE_READ = [
    "Value Builder Analytics charts (fit/data_round3/peer_valuebuilder_charts.csv): 1fc1e4fe and 737e5440 (largest "
    "customer), 598217fe and 2d096c7f (owner dependence), 6c180576, fcdb44f7 and 9537f3d8 (recurring share), 369e25c4 "
    "(revenue mix): printed bar labels read off the downloaded images",
    "Tommy's Express FDD 2025 (calendar 2024) pp.56-57, FDD 2024 (calendar 2023) p.56 and FDD 2022 (calendar 2021) p.48: "
    "expense tables embedded as images (fit/data_round3/peer_tommys_fdd_item19.csv, layer 'image'); checked here by the "
    "utilities sub-accounts adding to the total and by every line implying the same gross-sales base",
    "ScalePad 2026 p.15, the Medium and Large panels of 'Percentage of Recurring Revenue' (the text layer holds the "
    "Baseline and Small labels)",
    "NBB WP 444 Fig. 8 and FRB IFDP 1218 Fig. 4 (fit/data_round3/peer_figures_image_read.csv): line charts read off the "
    "rendered pages, about +-0.01 (checks only)",
]


def src(row):
    return f"{row['source']} | {row['url']} | {row['file']} | accessed {row['accessed']}"


seen, SOURCES = set(), []
for r in QROWS:
    if r['url'] not in seen:
        seen.add(r['url']); SOURCES.append(src(r))
SOURCES += [
    "Tommy's Express LLC FDDs 2022, 2024, 2025, 2026, Item 19 | https://www.cards.commerce.state.mn.us/franchise-registrations?doSearch=true&franchisor=Tommy (document URLs in peer_tommys_fdd_item19.csv) | mn_cards_tommys/fdd20{22,24,25,26}_clean.pdf | accessed 2026-10-16",
    "Tommy's Express FDD 2020, Item 19 (calendar 2019, dollars per car) | https://keycommercialcapital.com/wp-content/uploads/2020/09/Tommys-Express-Car-Wash-FDD.pdf | tommys_fdd/fdd2020.pdf | accessed 2026-10-16",
    "Value Builder Analytics charts, Advisor News newsletter | https://advisor-news.beehiiv.com/p/<post> (posts and image URLs in peer_valuebuilder_charts.csv) | valuebuilder_charts/*.png | accessed 2026-10-16",
    "Statistics Canada, Canadian Survey on Business Conditions, tables 33-10-0778, 33-10-0924, 33-10-1123 | https://www150.statcan.gc.ca/n1/tbl/csv/33100778-eng.zip (and 33100924, 33101123) | statcan_csbc/x*/ | accessed 2026-10-16",
    "Statistics Canada, table 27-10-0217 (Survey of Innovation 2005, most important customer's share of revenue) | https://www150.statcan.gc.ca/n1/tbl/csv/27100217-eng.zip | statcan_innov2005/x27100217/27100217.csv | accessed 2026-10-16",
    "US Census Bureau, 2022 Economic Census, products by industry (EC2200NAPCSINDPRD) | https://www2.census.gov/programs-surveys/economic-census/data/2022/sector00/EC2200NAPCSINDPRD.zip | census_ec22_napcs/EC2200NAPCSINDPRD.dat | accessed 2026-10-14 (fit6 download)",
    "Empire Flippers marketplace listings (local extract) | https://empireflippers.com/marketplace-api/ | data5/empireflippers/clean/ef_listings.csv | retrieved 2026-10-10",
    "NBB Working Paper 444 Figure 8; FRB IFDP 1218 Figure 4 (image-read) | https://www.nbb.be/doc/ts/publications/wp/wp444en.pdf ; https://www.federalreserve.gov/econres/ifdp/files/ifdp1218.pdf | peer_figures_image_read.csv | accessed 2026-10-14 / 2026-10-16",
    "Census SBO 2007 customer-class bound, carried from the second round's notes (not recomputed) | https://www2.census.gov/programs-surveys/sbo/datasets/2007/pums_csv.zip | /tmp/claude-0/fit6/research/E-sizerefs-cc-plt.md | 2026-10-14",
]

out = {
    'peer_rec_ret_ret_add': {'ecom': ECOM, 'auto': AUTO, 'rest': REST},
    'peer_rec_ret_rec_add': {'msp': MSP_REC},
    'flags_update': FLAGS,
    'flags_remove': FLAGS_REMOVE,
    'not_shipped_add': NOT_SHIPPED,
    'definitions': {'ret': DEF_RET, 'rec_check': DEF_REC_CHECK,
                    'ret_note': (f"Count has more benchmarks than revenue retention, and the cells already shipped are "
                                 f"counts (landscaping .88: customers of 12 months ago still customers; fitness .66: member "
                                 f"retention). For B2B sellers the readings differ a lot (Belgian links about "
                                 f"{nbb_u_late:.2f} by count, {nbb_w_late:.2f} by value), so the slider should say "
                                 f"customers, not revenue")},
    'slider_notes': {'ret': {'min_now': SLIDER['ret'][0], 'max_now': SLIDER['ret'][1], 'min_suggested': 10,
                             'why': (f"a typed value is clamped to the slider's range: e-commerce ({ECOM['v']:.2f}) and "
                                     f"restaurants ({REST['v']:.2f}) sit below the {SLIDER['ret'][0]:.0f}% minimum and auto "
                                     f"repair ({AUTO['v']:.2f}) on it. Little Stream's stores (mean {ls_mean:.2f}, SD "
                                     f"{ls_sd:.3f}) put the tenth percentile near {ls_mean - N.ppf(.9) * ls_sd:.2f} under a "
                                     f"normal approximation, so a minimum of about 10% (judgment) lets typical sellers in")},
                     'grw': {'domain': [G_LO, G_HI], 'note': 'PEER_SD.grw is fitted on this domain; widening the slider to about -65% would call for about .20'},
                     'cc': {'domain': list(CC_DOM)}},
    'peer_gm_wash': PEER_GM_WASH,
    'peer_gm_tiers_add': {'franchise disclosure': ("a franchisor's disclosed unit-level cost shares (FDD Item 19, state "
                                                   "franchise registry), shaded for the format mix of sellers (Aggregate)")},
    'peer_gm_surveys_wash': WASH_SURVEY,
    'peer_gm_definition_wash': DEF_WASH_NEW,
    'peer_gm_definition_wash_now': DEF_WASH_NOW,
    'peer_gm_not_identified_remove': ['wash'],
    'peer_gm_wash_detail': {
        'level': W_LEVEL, 'measured': r3(measured), 'shade': r3(shade),
        'se': r3(w_se), 'se_terms': {'between_years': r3(s_year), 'definition_variants': r3(s_def),
                                     'format': r3(s_fmt)},
        'se_note': (f"SE {r3(w_se)} = the between-year SD ({s_year:.3f}), the spread of the definition's readings (A0 "
                    f"{wash['A0']['mean']:.3f} without supplies, A {wash['A']['mean']:.3f}, A2 {wash['A2']['mean']:.3f} with "
                    f"Tommy's utility total incl. communications, B {wash['B']['mean']:.3f} with merchandise and uniforms; SD "
                    f"{s_def:.3f}) and a format term, the SD of the three formats' readings ({s_fmt:.3f}: express "
                    f"{measured:.3f} measured, in-bay {inbay:.3f} and self-serve {selfs:.3f} from illustrative P&Ls, which "
                    f"are not data), in quadrature. The format term carries the shade, which is judgment"),
        'variants_by_year': {v: {y: r3(x) for y, x in wash[v]['by_year'].items()} for v in VARIANTS},
        'first_year_sites_A': {y: r3(v) for y, v in first_year.items()},
        'dollar_based_A': {y: r3(v) for y, v in dollar_A.items()},
        'expense_table_base_mismatch': base_off,
        'calendar_2019_per_car': {g: {k: (r3(v) if isinstance(v, float) else v) for k, v in d.items()} for g, d in per_car.items()},
        'within_brand_revenue_gradient': {'per_decade': r3(brand_slope), 'se': r3(brand_slope_se),
                                          'note': ("gm on log10 average gross sales across tenure groups and years, "
                                                   "site-weighted: confounded with site maturity, so not a size slope; it "
                                                   "is the slope_se of the flat curve (how far the flat curve could be off), "
                                                   "not a sampling SE; each knot's SE adds it times the knot's distance in "
                                                   "log10 revenue from the sites' site-weighted revenue, in quadrature")},
        'illustrative_formats_not_data': {'in_bay': r3(inbay), 'self_serve': r3(selfs)},
        'definition_check': (f"The page's definition ('{DEF_WASH_NOW}') maps onto the FDD's lines: chemicals = detergents; "
                             f"water = water and sewer; utilities = electric, gas and waste removal (Tommy's own utility "
                             f"total also holds communications: variant A2, {wash['A2']['mean']:.3f}); supplies = office "
                             f"supplies; labour, repairs and maintenance, customer claims and merchandise are left out. A "
                             f"broker's P&L guide defines car-wash gross profit the same way ('{qv('ind_gp')}'). The "
                             f"restatement only names the lines left out: repairs and claims are in Tommy's own 'COGS', and "
                             f"with them (variant C) the margin is {wash['C']['mean']:.3f}"),
        'notes': ("Utilities sub-accounts 'are calculated based on historical average dispersion of the utilities account' "
                  "(only the totals are measured); franchisee-reported, unaudited, full-year outlets only. One brand of "
                  "new franchised express tunnels; listings for sale are mixed formats")},
    'peer_cc': PEER_CC,
    'peer_sd': {'grw': SD_GRW, 'cc': SD_CC, 'checks': CHECKS},
    'sources': SOURCES,
    'integration_notes': [
        "peer_rec_ret: add peer_rec_ret_ret_add to .ret and peer_rec_ret_rec_add to .rec (FITTED_CELLS then writes "
        "ecom.ret, auto.ret, rest.ret and msp.rec into IND); replace .flags with flags_update (it drops "
        + ', '.join(FLAGS_REMOVE) + "); add not_shipped_add to .not_shipped (fit.rec and saas.rec stay as they are)",
        f"the retention slider (id i_ret) runs {SLIDER['ret'][0]:.0f}-{SLIDER['ret'][1]:.0f} and a typed value is clamped "
        f"to it, so e-commerce {ECOM['v']:.2f} and restaurants {REST['v']:.2f} cannot be entered until the minimum drops "
        f"(about 10); its label should carry definitions.ret",
        "peer_gm: by_industry.wash = peer_gm_wash (flat), tiers += peer_gm_tiers_add, surveys.wash = peer_gm_surveys_wash, "
        "delete not_identified.wash; definition.wash may take peer_gm_definition_wash. peerGm then reads the curve, so "
        f"IND.wash.gm ({IND['wash']['gm']:.2f}) is no longer read; the Data tab's aggregate tally counts gm.length (4) per "
        "non-listing curve, although the wash curve is one number",
        f"peerMedians: cc {CC_WAS:.2f} -> peer_cc.v ({PEER_CC['v']:.2f}), manufacturing peer_cc.by_industry.mfg.v "
        f"({PEER_CC['by_industry']['mfg']['v']:.2f}); PEER_SD.grw {PEER_SD['grw']:.2f} -> {SD_GRW['v']:.2f}, PEER_SD.cc "
        f"{PEER_SD['cc']:.2f} -> {SD_CC['v']:.2f}: these move every quality composite, so value effects should be re-run",
        "tests/model.test.js 38a and 38b assert the old state (15 gross-margin curves and none for car washes, "
        "IND.wash.gm .70, no recurring cell, the FITTED_CELLS list) and will need the new cells",
    ],
    'brief_check': BRIEF_CHECK,
    'image_read': IMAGE_READ,
    'verification': {'quotes_checked': len(Q), 'html_or_raw_reads': n_html, 'pdf_text_reads': n_pdf,
                     'pdf_quotes_not_reread': n_pdf_skipped, 'pdftotext': PDFTOTEXT or 'not used', 'page': PAGE_FROM,
                     'fdd_utilities_check_max_gap': max(fdd_checks['utilities_total_vs_subaccounts']),
                     'statuses': {k: v['status'] for k, v in Q.items()}},
}
SUMMARY = (
    f"Retention, by customer count (last year's customers who bought again in the last 12 months): e-commerce "
    f"{ECOM['v']:.2f} (SE {ECOM['se']:.3f}; was {ECOM['was']:.2f}), auto repair {AUTO['v']:.2f} ({AUTO['se']:.3f}; was "
    f"{AUTO['was']:.2f}), restaurants {REST['v']:.2f} ({REST['se']:.3f}; was {REST['was']:.2f}; the middle of the range "
    f"Bloom's page supports: its stated {rest_v:.2f}, likely low, and {rest_central:.2f} from its first-visit and repeat "
    f"figures; one vendor page). The slider's {SLIDER['ret'][0]:.0f}% minimum must drop to about 10%. msp.rec "
    f"{MSP_REC['v']:.2f} (SE {MSP_REC['se']:.3f}; was {MSP_REC['was']:.2f}); the rec label is unchanged and the (a)/(b) "
    f"definition finding is a check. Car-wash gross margin {W_LEVEL:.2f} (SE {r3(w_se):.3f} at the sites' revenue, "
    f"up to {max(W_SE_KNOTS):.2f} at the curve's ends; was {IND['wash']['gm']:.2f}), "
    f"flat: Tommy's Express FDD Item 19, {measured:.3f} measured on the page's definition over {sum(SITES.values())} "
    f"site-years, shaded for formats. Largest customer {PEER_CC['v']:.2f} (SE .02; was {CC_WAS:.2f}), manufacturing "
    f"{PEER_CC['by_industry']['mfg']['v']:.2f} (.02). PEER_SD.grw {SD_GRW['v']:.2f} (SE {SD_GRW['se']:.3f}; was "
    f"{PEER_SD['grw']:.2f}) on the slider's [{G_LO:.2f}, {G_HI:.2f}]; PEER_SD.cc {SD_CC['v']:.2f} (SE .02; was "
    f"{PEER_SD['cc']:.2f}). Kept: PEER_SD.own {PEER_SD['own']:.2f}, PEER_SD.rec {PEER_SD['rec']:.2f}, the owner level "
    f"{OWN_A:.2f} (Value Builder bounds it at {min(own_level['ordered_probit']['at_z0'], own_level['low_only']['at_z0']):.2f}-"
    f"{own_level['low_or_moderate']['at_z0']:.2f}), "
    f"management depth and reporting (weak checks). Not shipped, recorded as checks: msp.ret, medical.ret, dist/mfg.ret, "
    f"home.ret, staff.ret, wash.ret, saas.ret, prof.ret (vet and construction not found), and the recurring-definition "
    f"readings for staffing, e-commerce, accounting, landscaping and car washes.")
out['summary'] = SUMMARY


def clean(o, top=None):
    """floats without binary noise; prose in the page's style (.25, not 0.25), except sources and file records"""
    if isinstance(o, float):
        if o.is_integer() and abs(o) >= 1:
            return int(o)
        return round(o, 2) if abs(o) >= 1000 else float(f'{o:.6g}')
    if isinstance(o, dict):
        return {k: clean(v, top if top is not None else k) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v, top) for v in o]
    if isinstance(o, str) and top not in ('sources', 'image_read', 'verification') and 'http' not in o:
        return re.sub(r'(?<![\w.$])0\.(\d)', r'.\1', o)
    return o


out = clean(out)
SUMMARY = out['summary']
os.makedirs(A.out, exist_ok=True)
with open(os.path.join(A.out, 'RESULT.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(SUMMARY)
print(f"\nchecked {len(Q)} quoted figures ({n_pdf} from PDF text layers"
      + (f", {n_pdf_skipped} PDF quotes taken from the transcription: pdftotext not run" if n_pdf_skipped else '')
      + f"); FDD utilities sub-accounts within ${max(fdd_checks['utilities_total_vs_subaccounts']):.2f} of the totals"
      + (f"; expense-table base differs from the sales table for {', '.join(base_off)}" if base_off else ''))
for k, v in BRIEF_CHECK.items():
    if v['material']:
        print(f"  differs from the brief: {k} {v}")
print('wrote', os.path.join(A.out, 'RESULT.json'))
