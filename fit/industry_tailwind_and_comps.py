#!/usr/bin/env python3
"""Industry tailwind (IND.tail) from BLS Employment Projections 2025-35, and comparables depth (IND.comps) as the value
model's own shrinkage weight on each industry's BIZCOMPS cell. October 2026.

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/industry_tailwind_and_comps.py          (about 5 s)
Out:  /tmp/claude-0/fit6/out/industry_tailwind_and_comps/RESULT.json (key js_table = {"tailwind": ..., "comps": ...}, the
      two tables to embed as MODELS.fitted.tailwind and MODELS.fitted.comps; js_lines = the exact lines), js_lines.txt,
      tail_16.csv, tail_sectors_2025_35.csv, tail_eval_matched.csv, tail_lovo.csv, tail_stability_2024_34.csv,
      comps_16.csv, comps_cells.csv, comps_bbs_yoy.csv

Why
  IND.tail (industry tailwind, -1..1) and IND.comps (density of comparable transactions, 0..1) are hand-set for the 16
  industries. tail is read only by two category sub-scores, Growth = 1.0 z.grw + .55 tail and Market position =
  .9 tail + .45 z.gm + .4 (comps - .65) (and by inert judgment terms). comps is read by Market position and by the
  confidence score, conf = .34 comps + .30 clamp(yrs/8) + .22 fin + .14 clamp(1 - typ/2.2) (High above .68, Moderate
  above .46). (These are the readers on the page this script read, commit 56ba230. Since the second round's integration,
  Market position reads comps against COMPS_MEAN, the mean of the 16 values, and the fitted confidence figure reads the
  value model's own cell weight, n/(n+k), directly.) The research round (/tmp/claude-0/fit6/research/D-tail-comps-strat-buyers.md) found a tested source for
  each: BLS's ten-year industry projections, which in four past vintages predicted which industries actually grew
  faster, and the value model's own BIZCOMPS cell counts, whose shrinkage weight n/(n+k) is exactly how much the
  console's value rests on the industry's own comparables. The analyst fixed the construction of both tables; this script
  rebuilds them from the downloads, runs the checks and writes the tables.

What it does
  A. Tailwind (MODELS.fitted.tailwind)
  0. Data. BLS EP 2025-35 data files (industry.zip: real output 1997-2025 by sector, jobs 2013-2025, 2025 and projected
     2035 output and jobs, the 176-sector plan) and Table 2.11 (industry.xlsx: jobs and output by detailed industry,
     2025 and 2035); the archived "Employment and output by industry" tables of the 2012-22, 2014-24, 2016-26 and
     2018-28 vintages (evaluation) and the 2024-34 Table 2.11 (stability). Zip members are read in memory; nothing is
     extracted or run. Today's IND.tail and IND.comps are read from the snapshot index.html (context only).
  1. Evaluation sample. Each archived vintage's industry rows are matched to the current sector plan by NAICS code
     (plus the research's fixed concordance for renumbered codes and aggregates); realised real-output growth is the
     CAGR from the vintage's base year to min(target, 2025) in the current chained-2017-dollar history; every growth
     rate is relative to the all-industry total; detailed sectors only (548 sector-vintages, 141 sectors).
  2. Output bridge. Realised relative growth on projected relative growth and on prior-decade realised relative growth
     (momentum), pooled OLS, SEs clustered by sector: E = 0.958 proj_rel + 0.273 prev_rel. The intercept is a
     composition term and is centred out in step 5.
  3. Leave-one-vintage-out. Each vintage is predicted from a bridge fitted on the other three, against BLS's raw
     projection and "no difference": MSE as the research defined it (with intercepts), MSE centred within the held-out
     vintage (what the shipped, centred table uses) and Spearman. The realised windows overlap in calendar time
     (2012-25), so held-out vintages are not independent; an expanding-window version (earlier vintages only) is
     reported beside it.
  4. Jobs. Realised relative job growth on projected relative job growth, 3 vintages (the jobs history starts 2013):
     pooled slope 0.98 (clustered SE 0.13), so projected jobs are used unscaled. Per-vintage slope, Spearman and
     centred MSE. The blend itself is scored too: in each of the 3 vintages, the Spearman of (clamped standardised
     held-out output prediction + clamped standardised projected jobs)/2 with realised output growth, realised job
     growth and their standardised average, beside each part alone.
  5. Apply to 2025-35. Per sector: proj_rel (projected 2025-35 real-output CAGR minus the total's), prev_rel (realised
     2015-25, minus the total's) and emp_rel (projected jobs CAGR minus all jobs). Output map: E centred on its
     output-weighted mean over BLS's 174 detailed sectors with output, divided by 2 x its output-weighted SD (3.062
     pp/yr). Where the console's industry is finer than BLS's output line (home, constr, auto, wash, land, fit, staff)
     the 6-digit job differential (cell jobs CAGR minus its output sector's) is added to proj_rel, i.e. the cell is
     assumed to share its sector's productivity growth. Jobs map: the industry's 6-digit (or finest) projected jobs CAGR
     minus all jobs, divided by 2 x the employment-weighted SD of emp_rel across detailed sectors (1.107 pp/yr). Each map
     is clamped to [-1, 1]; tail = their mean. 0 = the all-industry average and +-1 = +-2 cross-sector SDs are
     conventions, not data.
  6. SEs, on the tail scale. se_coef: 4,000 draws of the two output coefficients from their clustered covariance, with
     the centre and the 2-SD anchor recomputed in each draw (the convention is in SD units, so only the relative weight
     of momentum and projection matters; the jobs map has no fitted coefficient). se_revision: the pooled RMS change of
     the 16 values between the 2024-34 and 2025-35 vintages (step 7) / sqrt(2), read as per-vintage noise (an upper
     bound: part of a revision is news). se_proxy: half the gap between the output and jobs maps (which proxy is the
     tailwind is not identified). se = sqrt of the sum of squares. A fixed-anchor (pp/yr) coefficient SE, with the jobs
     slope drawn from N(1, 0.13^2), is stored as a sensitivity.
  7. Stability. The same pipeline on the 2024-34 vintage. The 2024-34 archive has no sector data files, so both
     vintages are rebuilt from Table 2.11 rows: the 167 detailed sectors whose output appears in Table 2.11 are found
     by matching 2025 and 2035 output levels with the 2025-35 sector file (the two vintages' Table 2.11 codes are
     identical). Momentum is 2014-24 for the earlier vintage. Correlations and changes of the 16 values; the research's
     tolerance for the next vintage is 0.3.
  8. Context. Spearman, Pearson and means against today's hand-set IND.tail.
  B. Comps (MODELS.fitted.comps)
  1. Rule. comps = n6/(n6 + k), computed in the page from MODELS.value.industry_n6 (BIZCOMPS rows in the NAICS-6 cell
     the value model prices the industry from, MODELS.value.naics6_for_industry) and k =
     MODELS.value.industry_shrinkage.k_naics6 = 25: the weight the value model puts on the industry's own comparables
     (effect = parent + (cell - parent) n/(n+k)). saas has no cell (software publishers 511210 holds 7 rows, below the
     table's cut of 8; the page states this at its IND2NAICS6 comment), so n = 7 ships explicitly. The values at k = 25
     are stored for the Data tab and for the page's test.
  2. Is k = 25 consistent with the data? Method of moments on the value model's own table: each of the 274 NAICS-6
     effects is de-shrunk against its 2-digit parent, raw = (effect - parent)(n + 25)/n, and raw^2 is regressed on 1/n
     (E raw^2 = tau^2 + sigma^2/n), so k_hat = sigma^2/tau^2. OLS (headline; HC1 SEs), the research's WLS, a feasible
     GLS and a normal ML version beside it; 90% interval from a cell bootstrap (B = 2,000, fixed seed; a draw with
     tau^2 <= 0 would count as k = infinity). se_from_k: the SD of n/(n+k) over the bootstrap draws (how far the true
     reliability weight could sit from the one the page uses).
  3. Does depth matter for a comparable multiple? BizBuySell's full-year 2016 and 2017 closed-deal tables by
     sub-sector (same taxonomy, 61 sub-sectors with at least 2 sales in both years): the year-to-year correlation of
     the average cash-flow multiple where both years have at least 50 sales against the rest (Fisher z test; cuts 30
     and 100 as sensitivity), the mean absolute change, and a variance decomposition (d^2 on 1/n16 + 1/n17) giving the
     deal-level variance, the between-sub-sector variance and k on that scale.
  4. Spearman of the 16 values with today's hand-set IND.comps and with SBA 7(a) change-of-ownership loans per year in
     the same NAICS-6 cell (FY2018-26; saas adds 513210, ecom adds 454110 where SBA files online retailers); BizBuySell
     closed-deal counts (2025 from the snapshot, 2018 mapped sub-sectors) as context.
  C. Output. tail values, components and SEs rounded half away from zero (Decimal ROUND_HALF_UP) to 0.01; anchors to
     0.001 pp/yr; comps values and se_from_k to 0.001; k to 0.1. Tests (assertions on the shipped tables, and agreement
     with the research numbers the analyst decided on) are printed and stored in RESULT.json, with open issues.

Data and fetch (each download in its own directory under /tmp/claude-0/fit6/data/D-tail-comps-strat-buyers/; read with
python3 -I; BLS answers 403 unless curl sends a descriptive User-Agent:
curl -A 'your-project/1.0 (contact)' -H 'Accept: */*' -H 'Accept-Language: en-US' -H 'Accept-Encoding: gzip, deflate, br'
--compressed -O <url>)
  bls_ep_data/industry.zip        https://www.bls.gov/emp/industry-employment/industry.zip  (modified 2026-08-27; page
                                  https://www.bls.gov/emp/data/industry-out-and-emp.htm)
  bls_ep_industry/industry.xlsx   https://www.bls.gov/emp/industry-employment/industry.xlsx  (Tables 2.1-2.11; page
                                  https://www.bls.gov/emp/tables/industry-employment-and-output.htm)
  bls_ep_archive/<v>.zip          https://www.bls.gov/emp/projections-archive/<v>.zip, v = 2012-22, 2014-24, 2016-26,
                                  2018-28, 2024-34 (page https://www.bls.gov/emp/data/projections-archive.htm)
  Local, read only:
  /tmp/claude-0/fit6snap/index.html  MODELS.value (BIZCOMPS industry_n6 and effects, industry_shrinkage.k_naics6,
                                     naics6_for_industry, price_realisation_by_industry.n), IND, IND2NAICS6
  /tmp/claude-0/data5/extra_wayback_retry_aggregates/clean/bbs_closed_tables.csv   BizBuySell Insight Report closed-deal
                                     tables by sector, full-year 2016-18 (Common Crawl captures of
                                     https://www.bizbuysell.com/news/media_insight.html)
  /tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv   SBA 7(a) change-of-ownership loans from the FOIA
                                     files as of 2026-06-30 (https://data.sba.gov/dataset/7a-504-foia)
"""
import hashlib, io, json, os, re, zipfile
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
import openpyxl
import xlrd
import statsmodels.api as sm
from scipy import optimize, stats

OUT = '/tmp/claude-0/fit6/out/industry_tailwind_and_comps'
DATA = '/tmp/claude-0/fit6/data/D-tail-comps-strat-buyers'
EP_ZIP = DATA + '/bls_ep_data/industry.zip'
EP_TABLES = DATA + '/bls_ep_industry/industry.xlsx'
EVAL_VINTAGES = ['2012-22', '2014-24', '2016-26', '2018-28']
EP_ARCH = {v: DATA + '/bls_ep_archive/' + v + '.zip' for v in EVAL_VINTAGES + ['2024-34']}
BBS = '/tmp/claude-0/data5/extra_wayback_retry_aggregates/clean/bbs_closed_tables.csv'
SBA = '/tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv'
INDEX = '/tmp/claude-0/fit6snap/index.html'
SEED = 20261014
B_COEF = 4000           # draws of the output coefficients (A6)
B_K = 2000              # cell bootstrap of k (B2)
TOTAL = 178             # 'Total, all industries' in the 2035 sector plan
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED)

KEYS = ['home', 'medical', 'vet', 'msp', 'saas', 'prof', 'mfg', 'dist', 'ecom', 'staff', 'land', 'wash', 'auto', 'constr',
        'fit', 'rest']

# ---- constants carried over from the research scripts (work/D-tail-comps-strat-buyers/) ----
# ep_eval.py: archived-table NAICS codes (2007/2012/2017 NAICS) -> sector numbers of the 2035 plan, where the plan's
# NAICS 2022 code differs or the row is an aggregate (aggregates, numbers > 176, drop out of the detailed sample)
MANUAL = {'5112': 94, '31-33': 184, '44-45': 201, '48-49': 202, '722': 223, '7225': 223, '811': 225, '812': 226, '339': 199,
          '3399': 200, '6211': 133, '6212': 134, '54194': 118, '5419': 211, '5617': 127, '5613': 123, '7139': 153,
          '8111': 157, '5415': 113, '5412': 110, '5411': 109, '23': 15, '42': 80, '621': 216, '713': 221, '561': 213,
          '54': 210, '56': 212, '62': 215, '71': 219, '72': 222, '81': 224, '51': 203, '52': 206, '53': 208, '61': 214}
# tail_table.py / tail_final.py: console industry -> BLS output sector(s) of the 2035 plan (several: output-weighted);
# the 6-digit jobs refinement (cell code, the code of its output sector) where the output line is coarser than the cell;
# the finest Table 2.11 jobs code(s) (several: employment-weighted)
OUT_SECTORS = {'home': [15], 'medical': [133, 134], 'vet': [118], 'msp': [113], 'saas': [94], 'prof': [110, 109],
               'mfg': [184], 'dist': [80], 'ecom': [201], 'staff': [123], 'land': [127], 'wash': [157], 'auto': [157],
               'constr': [15], 'fit': [153], 'rest': [155]}
REFINE = {'home': ('238220', '230000'), 'constr': ('238900', '230000'), 'auto': ('811110', '811100'),
          'wash': ('811190', '811100'), 'land': ('561730', '561700'), 'fit': ('713940', '713900'),
          'staff': ('561320', '561300')}
JOBS = {'home': ['238220'], 'medical': ['621100', '621200'], 'vet': ['541940'], 'msp': ['541500'], 'saas': ['513200'],
        'prof': ['541200', '541100'], 'mfg': ['31-330'], 'dist': ['420000'], 'ecom': ['44-450'], 'staff': ['561320'],
        'land': ['561730'], 'wash': ['811190'], 'auto': ['811110'], 'constr': ['238900'], 'fit': ['713940'],
        'rest': ['722511']}
# Table 2.11 code of each output sector above (verified against the sector file's output levels in A7)
SECTOR_CODE = {15: '230000', 80: '420000', 94: '513200', 109: '541100', 110: '541200', 113: '541500', 118: '541940',
               123: '561300', 127: '561700', 133: '621100', 134: '621200', 153: '713900', 155: '722511', 157: '811100',
               184: '31-330', 201: '44-450'}
MAP_NOTE = {'ecom': ' (NAICS 2022 has no e-commerce line; retail stands in, the weakest mapping)',
            'saas': ' (output growth 2015-25 rests on quality-adjusted software prices)'}
# comps: index.html snapshot, IND2NAICS6 comment (lines 2054-55) and Data tab (line 5270): "SaaS has no usable cell
# (511210 holds 7 rows)". The BIZCOMPS rows are not available here; industry_n6 starts at 8 rows (checked below).
SAAS_CELL, SAAS_N = '511210', 7
# sba_counts.py: SBA cells per console industry (ecom adds 454110: SBA files online retailers under retail)
SBA_CELLS = {'home': ['238220'], 'medical': ['621111'], 'vet': ['541940'], 'msp': ['541511'], 'saas': ['511210', '513210'],
             'prof': ['541211'], 'mfg': ['339950'], 'dist': ['423310'], 'ecom': ['454110', '541512'], 'staff': ['561320'],
             'land': ['561730'], 'wash': ['811192'], 'auto': ['811111'], 'constr': ['238990'], 'fit': ['713940'],
             'rest': ['722511']}
# comps_fit.py: BizBuySell 2018 sub-sectors per console industry (context only; vet has none)
BBS18 = {'home': ['HVAC Businesses', 'Plumbing Businesses', 'Electrical and Mechanical Contracting Businesses'],
         'medical': ['Medical Practices', 'Dental Practices'], 'vet': [], 'msp': ['IT and Software Service Businesses'],
         'saas': ['Software and App Companies'], 'prof': ['Accounting Businesses and Tax Practices', 'Legal Services and Law Firms'],
         'mfg': 'MANUFACTURING', 'dist': ['Durable Goods Wholesalers and Distributors', 'Nondurable Goods Wholesalers and Distributors',
                                          'Other Wholesalers and Distributors'],
         'ecom': ['Websites and Ecommerce Businesses'], 'staff': ['Staffing Agencies'], 'land': ['Landscaping and Yard Service Businesses'],
         'wash': ['Car Washes'], 'auto': ['Auto Repair and Service Shops'],
         'constr': ['Concrete Businesses', 'Heavy Construction Businesses', 'Other Building and Construction Businesses'],
         'fit': ['Gyms and Fitness Centers', 'Dance, Pilates and Yoga Studios'], 'rest': ['Restaurants']}
# the research numbers the analyst decided on (report sections 4.2-4.3, 5.2-5.3), for the agreement tests
REPORT_BLEND = {'home': .05, 'medical': .37, 'vet': .38, 'msp': .87, 'saas': .95, 'prof': -.30, 'mfg': -.33, 'dist': -.08,
                'ecom': -.04, 'staff': -.42, 'land': .12, 'wash': -.20, 'auto': -.03, 'constr': -.03, 'fit': .25, 'rest': -.02}
REPORT = dict(b_proj=0.958, b_prev=0.273, anchor_out=3.06, anchor_jobs=1.11, k_hat=17.9, k_ci90=(6.9, 43.8), r_thick=0.92,
              r_thin=0.24, n_thick=29, n_thin=32, k_bbs=8.6, jobs_slope=0.98)
STABILITY_TOL = 0.3     # research report 4.5: the 16 values should move by less than about 0.3 per vintage


# ---------------------------------------------------------------- helpers
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()


def rnd(x, nd):
    """half-up rounding of the shortest decimal representation (round() is half-even on binary floats)"""
    if x is None or not np.isfinite(x):
        return None
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def r6(x):
    return None if x is None or not np.isfinite(x) else float('%.6g' % x)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, np.ndarray)):
        return [jsonable(v) for v in list(o)]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    return o


def cagr(a, b, years):
    return 100.0 * ((b / a) ** (1.0 / years) - 1.0) if (a > 0 and b > 0) else np.nan


def norm(c):
    return str(c).strip().replace(' ', '')


def num(v):
    if v is None or (isinstance(v, str) and v.strip() in ('', '—', '-', 'NA')):
        return np.nan
    try:
        return float(str(v).replace(',', ''))
    except ValueError:
        return np.nan


def wmean(x, w):
    return float(np.sum(w * x) / np.sum(w))


def wsd(x, w):
    """weighted SD as numpy's cov(x, aweights=w) (reliability weights, ddof 1)"""
    m = wmean(x, w)
    return float(np.sqrt(np.sum(w * (x - m) ** 2) / (np.sum(w) - np.sum(w ** 2) / np.sum(w))))


def spearman(a, b):
    return float(stats.spearmanr(a, b)[0])


def mse_c(y, p):
    """MSE after centring prediction and outcome within the sample (the shipped table is centred)"""
    y = np.asarray(y, float); p = np.asarray(p, float)
    return float(np.mean(((y - y.mean()) - (p - p.mean())) ** 2))


def read_book(data, name):
    """[(sheet, rows)] of an .xls or .xlsx workbook held in memory"""
    if name.endswith('.xls'):
        wb = xlrd.open_workbook(file_contents=data)
        return [(s.name, [s.row_values(i) for i in range(s.nrows)]) for s in wb.sheets()]
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]


def js_object(src, start):
    """the JSON object literal that starts at src[start] == '{' (brace matching outside strings)"""
    depth, instr, esc = 0, False, False
    for k in range(start, len(src)):
        c = src[k]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[start:k + 1]
    raise ValueError('unbalanced object')


TESTS, TEST_DETAIL = {}, {}


def check(name, ok, detail=None):
    TESTS[name] = bool(ok)
    if detail is not None:
        TEST_DETAIL[name] = jsonable(detail)
    print(('  PASS ' if ok else '  FAIL ') + name + ('' if detail is None else '  ' + json.dumps(jsonable(detail))))


# ---------------------------------------------------------------- 0. data
html = open(INDEX, encoding='utf-8').read()
MV = json.loads(js_object(html, html.index('const MODELS = ') + len('const MODELS = ')))['value']
blk = html[html.index('const IND = {'):]
blk = blk[:blk.index('};')]
IND_NOW = {}
for line in blk.splitlines()[1:]:
    m = re.match(r'\s*(\w+):\s*\{(.*)\},?\s*$', line)
    if m:
        body = re.sub(r'n:"[^"]*",?', '', m.group(2))
        IND_NOW[m.group(1)] = {k: float(v) for k, v in re.findall(r'(\w+):\s*(-?\d*\.?\d+)', body)}
assert list(IND_NOW) == KEYS, list(IND_NOW)
TAIL_NOW = np.array([IND_NOW[k]['tail'] for k in KEYS]); COMPS_NOW = np.array([IND_NOW[k]['comps'] for k in KEYS])
assert IND_NOW['rest']['tail'] == -0.25 and IND_NOW['home']['comps'] == 0.85
I2N6 = json.loads(re.search(r'const IND2NAICS6=(\{[^}]*\});', html).group(1))

zf = zipfile.ZipFile(EP_ZIP)
zcsv = lambda name: pd.read_csv(io.BytesIO(zf.read(name)))
_ih, _eh, PROJ = zcsv('ind2025.csv'), zcsv('emp2025.csv'), zcsv('proj2035.csv')
OUTH = _ih[_ih.SERIESNUMBER == 2].drop(columns='SERIESNUMBER').set_index('SECTORNUMBER')
OUTH.columns = [int(c) for c in OUTH.columns]
JOBH = _eh[_eh.SERIESNUMBER == 4].drop(columns='SERIESNUMBER').set_index('SECTORNUMBER')
JOBH.columns = [int(c) for c in JOBH.columns]
PO = PROJ[PROJ.SERIESNUMBER == 2].set_index('SECTORNUMBER')       # real output, millions of chained 2017 $
PE = PROJ[PROJ.SERIESNUMBER == 4].set_index('SECTORNUMBER')       # total jobs, thousands
plan = dict(read_book(zf.read('SectorPlan2035.xlsx'), 'SectorPlan2035.xlsx'))
CODE2SEC, SEC_TITLE = {}, {}
for sheet in ('Industry Commodity Sectors', 'Summary Sectors'):
    for r in plan[sheet]:
        if isinstance(r[0], (int, float)) and r[2] is not None:
            CODE2SEC.setdefault(norm(r[2]), int(r[0]))
            SEC_TITLE.setdefault(int(r[0]), str(r[1]).strip())
assert SEC_TITLE[TOTAL].startswith('Total')


def table211(data):
    rows = dict(read_book(data, 'industry.xlsx'))['Table 2.11']
    recs = []
    for r in rows[2:]:
        if r[0] is None or r[1] is None:
            continue
        t = str(r[0])
        recs.append(dict(title=t.strip(), code=str(r[1]).strip(), depth=(len(t) - len(t.lstrip(' '))) // 2,
                         emp0=num(r[3]), emp1=num(r[4]), out0=num(r[8]), out1=num(r[9])))
    return pd.DataFrame(recs)


T25 = table211(open(EP_TABLES, 'rb').read())
T24 = table211(zipfile.ZipFile(EP_ARCH['2024-34']).read('2024-34/industry.xlsx'))
assert len(T25) == len(T24) == 423 and (T25.code.values == T24.code.values).all()
title211 = dict(zip(T25.code, T25.title))


def archived(v):
    z = zipfile.ZipFile(EP_ARCH[v])
    name = [n for n in z.namelist() if n.split('/')[-1].startswith('industry.xls')][0]
    for sheet, rows in read_book(z.read(name), name):
        title = ' '.join(str(x) for x in (rows[0] if rows else []) if x not in (None, ''))
        if 'output by industry' not in title.lower():
            continue
        base, target = int('20' + v[2:4]), int('20' + v[5:7])
        recs = []
        for r in rows[4:]:
            t = str(r[0]) if r[0] is not None else ''
            code = str(r[1]).strip() if r[1] is not None else ''
            vals = [num(x) for x in r[2:14]]   # emp prev, base, target, 2 changes, 2 CAGRs; out prev, base, target, 2 CAGRs
            if not t.strip() or (np.isnan(vals[0]) and np.isnan(vals[7])):
                continue
            recs.append(dict(vintage=v, base=base, target=target, title=t.strip(), naics=code, emp_base=vals[1],
                             emp_target=vals[2], out_base=vals[8], out_target=vals[9], cagr_out_prev=vals[10],
                             cagr_out_proj=vals[11]))
        return pd.DataFrame(recs), name, sheet
    raise ValueError(v)


ARCH = {v: archived(v) for v in EVAL_VINTAGES}


def realised(sec, b, e):
    return cagr(OUTH.loc[sec, b], OUTH.loc[sec, e], e - b) if sec in OUTH.index else np.nan


def realised_jobs(sec, b, e):
    return cagr(JOBH.loc[sec, b], JOBH.loc[sec, e], e - b) if sec in JOBH.index else np.nan


# ---------------------------------------------------------------- A1-2. evaluation sample and the output bridge
print('A. tailwind')
per_vintage, mats = {}, []
for v in EVAL_VINTAGES:
    d = ARCH[v][0]
    d = d[d.cagr_out_proj.notna()].copy()
    b, t = int(d.base.iloc[0]), int(d.target.iloc[0]); e = min(t, 2025)
    tot = d[d.title.str.startswith('Total')].iloc[0]
    tot_real, tot_real_prev = realised(TOTAL, b, e), realised(TOTAL, b - 10, b)
    d['code'] = d.naics.map(norm)
    d['sec'] = d.code.map(lambda c: MANUAL.get(c, CODE2SEC.get(c)))
    d = d[d.sec.notna() & ~d.title.str.startswith('Total') & (d.code != 'NA')].drop_duplicates('sec').copy()
    d['sec'] = d.sec.astype(int)
    d['real'] = [realised(s, b, e) for s in d.sec]
    d['real_prev_cur'] = [realised(s, b - 10, b) for s in d.sec]
    d = d[d.real.notna()].copy()
    d['proj_rel'] = d.cagr_out_proj - tot.cagr_out_proj
    d['real_rel'] = d.real - tot_real
    d['prev_rel_cur'] = d.real_prev_cur - tot_real_prev
    det = d[d.sec <= 176].copy()
    det['end'] = e
    m1 = sm.OLS(det.real_rel, sm.add_constant(det[['proj_rel']])).fit(cov_type='HC1')
    per_vintage[v] = dict(base=b, end=e, n=int(len(det)), total_projected=float(tot.cagr_out_proj), total_realised=tot_real,
                          slope=float(m1.params['proj_rel']), slope_se=float(m1.bse['proj_rel']), r2=float(m1.rsquared),
                          spearman=spearman(det.proj_rel, det.real_rel), sd_projected_rel=float(det.proj_rel.std()),
                          sd_realised_rel=float(det.real_rel.std()))
    mats.append(det)
MATCHED = pd.concat(mats, ignore_index=True)
A = MATCHED[MATCHED.prev_rel_cur.notna()].copy()
FITS = {}
for nm, cols in [('proj', ['proj_rel']), ('prev', ['prev_rel_cur']), ('both', ['proj_rel', 'prev_rel_cur'])]:
    FITS[nm] = sm.OLS(A.real_rel, sm.add_constant(A[cols])).fit(cov_type='cluster', cov_kwds={'groups': A.sec.to_numpy()})
fb = FITS['both']
B_PROJ, B_PREV = float(fb.params['proj_rel']), float(fb.params['prev_rel_cur'])
VB = fb.cov_params().loc[['proj_rel', 'prev_rel_cur'], ['proj_rel', 'prev_rel_cur']].to_numpy()
huber = sm.RLM(A.real_rel, sm.add_constant(A[['proj_rel', 'prev_rel_cur']]), M=sm.robust.norms.HuberT()).fit()
bridge = {nm: dict(coef={k: r6(x) for k, x in f.params.items()}, se={k: r6(x) for k, x in f.bse.items()}, r2=r6(f.rsquared))
          for nm, f in FITS.items()}
bridge['both_huber'] = dict(coef={k: r6(x) for k, x in huber.params.items()}, se={k: r6(x) for k, x in huber.bse.items()})
bridge.update(n=int(len(A)), sectors=int(A.sec.nunique()), per_vintage_raw_projection=jsonable(per_vintage))
print('  bridge: %.4f (%.4f) proj + %.4f (%.4f) momentum, n %d, %d sectors, R2 %.3f'
      % (B_PROJ, fb.bse['proj_rel'], B_PREV, fb.bse['prev_rel_cur'], len(A), A.sec.nunique(), fb.rsquared))

# ---------------------------------------------------------------- A3. leave-one-vintage-out (and expanding window)
def score(tr, te):
    mp = sm.OLS(tr.real_rel, sm.add_constant(tr[['proj_rel']])).fit()
    mb = sm.OLS(tr.real_rel, sm.add_constant(tr[['proj_rel', 'prev_rel_cur']])).fit()
    pp = mp.predict(sm.add_constant(te[['proj_rel']])); pb = mb.predict(sm.add_constant(te[['proj_rel', 'prev_rel_cur']]))
    y = te.real_rel.to_numpy()
    return dict(n=int(len(te)), mse_zero=float(np.mean((y - tr.real_rel.mean()) ** 2)),
                mse_bls_raw=float(np.mean((y - te.proj_rel) ** 2)), mse_proj_fit=float(np.mean((y - pp) ** 2)),
                mse_bridge=float(np.mean((y - pb) ** 2)), msec_zero=mse_c(y, np.zeros(len(y))),
                msec_bls_raw=mse_c(y, te.proj_rel), msec_proj_fit=mse_c(y, pp), msec_bridge=mse_c(y, pb),
                spearman_bls_raw=spearman(te.proj_rel, y), spearman_bridge=spearman(pb, y),
                bridge_coef=[float(mb.params['proj_rel']), float(mb.params['prev_rel_cur'])])


LOVO = {v: score(A[A.vintage != v], A[A.vintage == v]) for v in EVAL_VINTAGES}
EXPAND = {v: score(A[A.vintage.isin(EVAL_VINTAGES[:i])], A[A.vintage == v]) for i, v in enumerate(EVAL_VINTAGES) if i > 0}
pd.DataFrame([dict(vintage=v, scheme='leave-one-vintage-out', **{k: x for k, x in s.items() if k != 'bridge_coef'})
              for v, s in LOVO.items()] +
             [dict(vintage=v, scheme='expanding window', **{k: x for k, x in s.items() if k != 'bridge_coef'})
              for v, s in EXPAND.items()]).to_csv(OUT + '/tail_lovo.csv', index=False, float_format='%.6g')
for v, s in LOVO.items():
    print('  LOVO %s n %d  MSE bridge %.2f raw %.2f zero %.2f | centred %.2f %.2f %.2f | Spearman bridge %.2f raw %.2f'
          % (v, s['n'], s['mse_bridge'], s['mse_bls_raw'], s['mse_zero'], s['msec_bridge'], s['msec_bls_raw'],
             s['msec_zero'], s['spearman_bridge'], s['spearman_bls_raw']))

# ---------------------------------------------------------------- A4. jobs, and the blend scored as a whole
jobs_eval, jrows, blend_eval = {}, [], {}
for v in EVAL_VINTAGES:
    g = MATCHED[MATCHED.vintage == v].copy()
    b, t = int(g.base.iloc[0]), int(g.target.iloc[0]); e = min(t, 2025)
    if b < int(JOBH.columns.min()):
        continue
    g['emp_proj'] = [cagr(r.emp_base, r.emp_target, t - b) for r in g.itertuples()]
    g['emp_real'] = [realised_jobs(s, b, e) for s in g.sec]
    g = g.dropna(subset=['emp_proj', 'emp_real']).copy()
    g['jproj_rel'] = g.emp_proj - np.average(g.emp_proj, weights=g.emp_base)    # vintage total row not matched: weighted mean
    g['jreal_rel'] = g.emp_real - realised_jobs(TOTAL, b, e)
    mj = sm.OLS(g.jreal_rel, sm.add_constant(g[['jproj_rel']])).fit(cov_type='HC1')
    jobs_eval[v] = dict(n=int(len(g)), slope=float(mj.params['jproj_rel']), se=float(mj.bse['jproj_rel']), r2=float(mj.rsquared),
                        spearman=spearman(g.jproj_rel, g.jreal_rel), msec_projection=mse_c(g.jreal_rel, g.jproj_rel),
                        msec_zero=mse_c(g.jreal_rel, np.zeros(len(g))))
    jrows.append(g)
    # the blend: held-out output bridge and projected jobs, each standardised and clamped as shipped, on both outcomes
    h = g[g.prev_rel_cur.notna() & (g.emp_base > 0)].copy()
    tr = A[A.vintage != v]
    mb = sm.OLS(tr.real_rel, sm.add_constant(tr[['proj_rel', 'prev_rel_cur']])).fit()
    po_ = mb.params['proj_rel'] * h.proj_rel + mb.params['prev_rel_cur'] * h.prev_rel_cur
    wo, we = h.out_base.to_numpy(), h.emp_base.to_numpy()
    t_o = np.clip((po_ - wmean(po_, wo)) / (2 * wsd(po_, wo)), -1, 1)
    t_j = np.clip((h.jproj_rel - wmean(h.jproj_rel, we)) / (2 * wsd(h.jproj_rel, we)), -1, 1)
    bl = (t_o + t_j) / 2
    zo = (h.real_rel - wmean(h.real_rel, wo)) / wsd(h.real_rel, wo)
    zj = (h.jreal_rel - wmean(h.jreal_rel, we)) / wsd(h.jreal_rel, we)
    comb = (zo + zj) / 2
    blend_eval[v] = dict(n=int(len(h)), blend_vs_combined=spearman(bl, comb), output_vs_combined=spearman(t_o, comb),
                         jobs_vs_combined=spearman(t_j, comb), blend_vs_output=spearman(bl, zo), output_vs_output=spearman(t_o, zo),
                         jobs_vs_output=spearman(t_j, zo), blend_vs_jobs=spearman(bl, zj), jobs_vs_jobs=spearman(t_j, zj),
                         output_vs_jobs=spearman(t_o, zj))
G = pd.concat(jrows, ignore_index=True)
mjp = sm.OLS(G.jreal_rel, sm.add_constant(G[['jproj_rel']])).fit(cov_type='cluster', cov_kwds={'groups': G.sec.to_numpy()})
JOBS_SLOPE, JOBS_SLOPE_SE = float(mjp.params['jproj_rel']), float(mjp.bse['jproj_rel'])
jobs_eval['pooled'] = dict(n=int(len(G)), slope=JOBS_SLOPE, se=JOBS_SLOPE_SE, r2=float(mjp.rsquared))
print('  jobs: pooled slope %.3f (%.3f), n %d; Spearman %s' % (JOBS_SLOPE, JOBS_SLOPE_SE, len(G),
      {v: round(x['spearman'], 2) for v, x in jobs_eval.items() if v != 'pooled'}))
print('  blend OOS (Spearman with combined outcome): %s' % {v: [round(x['blend_vs_combined'], 2), round(x['output_vs_combined'], 2),
      round(x['jobs_vs_combined'], 2)] for v, x in blend_eval.items()})
MATCHED.merge(G[['vintage', 'sec', 'emp_proj', 'emp_real', 'jproj_rel', 'jreal_rel']], on=['vintage', 'sec'], how='left')\
    .to_csv(OUT + '/tail_eval_matched.csv', index=False, float_format='%.6g')

# ---------------------------------------------------------------- A5. apply to 2025-35
def jobs_cagr(T, code, years=10):
    r = T[T.code == code]
    assert len(r) == 1, code
    return cagr(float(r.emp0.iloc[0]), float(r.emp1.iloc[0]), years)


def jobs_weight(T, code):
    return float(T[T.code == code].emp0.iloc[0])


tot_proj = cagr(PO.loc[TOTAL, '2025'], PO.loc[TOTAL, '2035'], 10)
tot_prev = realised(TOTAL, 2015, 2025)
tot_emp = cagr(PE.loc[TOTAL, '2025'], PE.loc[TOTAL, '2035'], 10)
S = pd.DataFrame({'sec': [int(s) for s in PO.index if s <= 231]})
S['title'] = S.sec.map(SEC_TITLE)
S['proj_rel'] = [cagr(PO.loc[s, '2025'], PO.loc[s, '2035'], 10) - tot_proj for s in S.sec]
S['prev_rel'] = [realised(s, 2015, 2025) - tot_prev for s in S.sec]
S['emp_rel'] = [cagr(PE.loc[s, '2025'], PE.loc[s, '2035'], 10) - tot_emp if s in PE.index else np.nan for s in S.sec]
S['out2025'] = [PO.loc[s, '2025'] for s in S.sec]
S['jobs2025'] = [PE.loc[s, '2025'] if s in PE.index else np.nan for s in S.sec]
S['E'] = B_PROJ * S.proj_rel + B_PREV * S.prev_rel
DO = S[(S.sec <= 176) & S.proj_rel.notna() & S.prev_rel.notna()]
DJ = S[(S.sec <= 176) & S.emp_rel.notna()]
WO, WJ = DO.out2025.to_numpy(), DJ.jobs2025.to_numpy()
CEN = wmean(DO.E.to_numpy(), WO)
SD_O = wsd(DO.E.to_numpy(), WO)
SD_J = wsd(DJ.emp_rel.to_numpy(), WJ)
assert abs(SD_O - float(np.sqrt(np.cov(DO.E, aweights=WO)))) < 1e-12
ANCHOR_O, ANCHOR_J = 2 * SD_O, 2 * SD_J
JOBS_MEAN_REL = wmean(DJ.emp_rel.to_numpy(), WJ)
S['tail_output_sector'] = np.clip((S.E - CEN) / ANCHOR_O, -1, 1)
S['tail_jobs_sector'] = np.clip(S.emp_rel / ANCHOR_J, -1, 1)
S.to_csv(OUT + '/tail_sectors_2025_35.csv', index=False, float_format='%.6g')
no174 = DO[DO.sec != 174]
anchor_sens = dict(sector_174=SEC_TITLE.get(174), sector_174_output_share=wmean((DO.sec == 174).to_numpy(float), WO),
                   anchor_output_without_174=2 * wsd(no174.E.to_numpy(), no174.out2025.to_numpy()),
                   centre_without_174=wmean(no174.E.to_numpy(), no174.out2025.to_numpy()))
print('  2025-35: %d output sectors, centre %.4f, anchor %.4f pp/yr; %d jobs sectors, anchor %.4f pp/yr (weighted mean emp_rel %.4f)'
      % (len(DO), CEN, ANCHOR_O, len(DJ), ANCHOR_J, JOBS_MEAN_REL))
Sx = S.set_index('sec')
emp_tot_211 = jobs_cagr(T25, 'TE1000')
rows = []
for k in KEYS:
    secs = OUT_SECTORS[k]; ww = np.array([Sx.loc[s, 'out2025'] for s in secs], float)
    proj_rel = float(np.average([Sx.loc[s, 'proj_rel'] for s in secs], weights=ww))
    prev_rel = float(np.average([Sx.loc[s, 'prev_rel'] for s in secs], weights=ww))
    adj = jobs_cagr(T25, REFINE[k][0]) - jobs_cagr(T25, REFINE[k][1]) if k in REFINE else 0.0
    E = B_PROJ * (proj_rel + adj) + B_PREV * prev_rel - CEN
    jw = np.array([jobs_weight(T25, c) for c in JOBS[k]])
    emp_rel = float(np.average([jobs_cagr(T25, c) for c in JOBS[k]], weights=jw)) - emp_tot_211
    rows.append(dict(ind=k, out_sectors='+'.join(map(str, secs)), proj_rel=proj_rel, jobs_adj=adj, proj_rel_detail=proj_rel + adj,
                     prev_rel=prev_rel, E=E, emp_codes='+'.join(JOBS[k]), emp_rel=emp_rel,
                     output=float(np.clip(E / ANCHOR_O, -1, 1)), jobs=float(np.clip(emp_rel / ANCHOR_J, -1, 1)),
                     jobs_weights='+'.join('%.1f' % x for x in jw), current=IND_NOW[k]['tail']))
R = pd.DataFrame(rows).set_index('ind')
R['blend'] = (R.output + R.jobs) / 2
assert np.allclose([jobs_weight(T25, c) for c in ('621100', '621200', '541200', '541100')], [3008.8, 1052.0, 1128.5, 1221.0])

# ---------------------------------------------------------------- A7. stability: 2024-34 against 2025-35, from Table 2.11
SECMAP = {}
for s in PO.index:
    if s > 176:
        continue
    o0, o1 = PO.loc[s, '2025'] / 1000, PO.loc[s, '2035'] / 1000
    c = T25[(abs(T25.out0 - o0) < 0.051) & (abs(T25.out1 - o1) < 0.051)]
    if len(c) == 1:
        SECMAP[int(s)] = c.code.iloc[0]
for s, c in SECTOR_CODE.items():
    r = T25[T25.code == c].iloc[0]
    assert abs(r.out0 - PO.loc[s, '2025'] / 1000) < 0.051 and abs(r.out1 - PO.loc[s, '2035'] / 1000) < 0.051, (s, c)
    if s <= 176:
        assert SECMAP.get(s) == c, (s, c, SECMAP.get(s))


def pipeline_211(T, base, beta):
    """tail for the 16 industries from one vintage's Table 2.11 (167 matched detailed sectors), with fixed coefficients"""
    i = T.set_index('code')
    to, te_ = cagr(i.loc['TE1000', 'out0'], i.loc['TE1000', 'out1'], 10), cagr(i.loc['TE1000', 'emp0'], i.loc['TE1000', 'emp1'], 10)
    tp = realised(TOTAL, base - 10, base)
    sec = pd.DataFrame({'sec': sorted(SECMAP)}); sec['code'] = sec.sec.map(SECMAP)
    sec['proj_rel'] = [cagr(i.loc[c, 'out0'], i.loc[c, 'out1'], 10) - to for c in sec.code]
    sec['prev_rel'] = [realised(s, base - 10, base) - tp for s in sec.sec]
    sec['emp_rel'] = [cagr(i.loc[c, 'emp0'], i.loc[c, 'emp1'], 10) - te_ for c in sec.code]
    sec['w_out'] = [i.loc[c, 'out0'] for c in sec.code]; sec['w_emp'] = [i.loc[c, 'emp0'] for c in sec.code]
    sec['E'] = beta[0] * sec.proj_rel + beta[1] * sec.prev_rel
    so = sec[sec.proj_rel.notna() & sec.prev_rel.notna()]; sj = sec[sec.emp_rel.notna() & (sec.w_emp > 0)]
    cen, ao = wmean(so.E.to_numpy(), so.w_out.to_numpy()), 2 * wsd(so.E.to_numpy(), so.w_out.to_numpy())
    aj = 2 * wsd(sj.emp_rel.to_numpy(), sj.w_emp.to_numpy())
    out = {}
    for k in KEYS:
        cs = [SECTOR_CODE[s] for s in OUT_SECTORS[k]]; ww = np.array([i.loc[c, 'out0'] for c in cs])
        pr = float(np.average([cagr(i.loc[c, 'out0'], i.loc[c, 'out1'], 10) - to for c in cs], weights=ww))
        pv = float(np.average([realised(s, base - 10, base) - tp for s in OUT_SECTORS[k]], weights=ww))
        adj = jobs_cagr(T, REFINE[k][0]) - jobs_cagr(T, REFINE[k][1]) if k in REFINE else 0.0
        E = beta[0] * (pr + adj) + beta[1] * pv - cen
        er = float(np.average([jobs_cagr(T, c) for c in JOBS[k]], weights=[jobs_weight(T, c) for c in JOBS[k]])) - te_
        o, j = float(np.clip(E / ao, -1, 1)), float(np.clip(er / aj, -1, 1))
        out[k] = dict(proj_rel=pr + adj, prev_rel=pv, emp_rel=er, output=o, jobs=j, tail=(o + j) / 2)
    return out, dict(sectors_output=int(len(so)), sectors_jobs=int(len(sj)), centre=cen, anchor_output=ao, anchor_jobs=aj)


ST25, st25 = pipeline_211(T25, 2025, (B_PROJ, B_PREV))
ST24, st24 = pipeline_211(T24, 2024, (B_PROJ, B_PREV))
stab = pd.DataFrame({k: dict(tail_2025_35=ST25[k]['tail'], tail_2024_34=ST24[k]['tail'], output_2025_35=ST25[k]['output'],
                             output_2024_34=ST24[k]['output'], jobs_2025_35=ST25[k]['jobs'], jobs_2024_34=ST24[k]['jobs'],
                             proj_rel_2025_35=ST25[k]['proj_rel'], proj_rel_2024_34=ST24[k]['proj_rel'],
                             emp_rel_2025_35=ST25[k]['emp_rel'], emp_rel_2024_34=ST24[k]['emp_rel'], shipped=R.loc[k, 'blend'])
                     for k in KEYS}).T
stab['change'] = stab.tail_2025_35 - stab.tail_2024_34
stab.index.name = 'ind'
stab.to_csv(OUT + '/tail_stability_2024_34.csv', float_format='%.6g')
RMS_REV = float(np.sqrt(np.mean(stab.change.to_numpy(float) ** 2)))
imax = stab.change.abs().astype(float).idxmax()
stability = dict(vintages=['2024-34', '2025-35'], machinery='both vintages from Table 2.11 rows, 167 matched detailed sectors, '
                 'coefficients fixed; momentum 2014-24 vs 2015-25',
                 pearson=float(np.corrcoef(stab.tail_2024_34.astype(float), stab.tail_2025_35.astype(float))[0, 1]),
                 spearman=spearman(stab.tail_2024_34, stab.tail_2025_35),
                 mean_abs_change=float(stab.change.abs().mean()), rms_change=RMS_REV,
                 max_abs_change=[float(abs(stab.loc[imax, 'change'])), imax],
                 inputs=dict(output_proj_rel_pearson=float(np.corrcoef(stab.proj_rel_2024_34.astype(float), stab.proj_rel_2025_35.astype(float))[0, 1]),
                             output_proj_rel_spearman=spearman(stab.proj_rel_2024_34, stab.proj_rel_2025_35),
                             jobs_emp_rel_pearson=float(np.corrcoef(stab.emp_rel_2024_34.astype(float), stab.emp_rel_2025_35.astype(float))[0, 1]),
                             jobs_emp_rel_spearman=spearman(stab.emp_rel_2024_34, stab.emp_rel_2025_35)),
                 machinery_vs_shipped_max_abs=float((stab.tail_2025_35 - stab.shipped).abs().max()),
                 table211_2025_35=st25, table211_2024_34=st24, tolerance=STABILITY_TOL)
print('  stability 2024-34 -> 2025-35: r %.3f rho %.3f, mean |change| %.3f, max %.3f (%s), RMS %.3f; machinery vs shipped %.3f'
      % (stability['pearson'], stability['spearman'], stability['mean_abs_change'], stability['max_abs_change'][0], imax,
         RMS_REV, stability['machinery_vs_shipped_max_abs']))

# ---------------------------------------------------------------- A6. SEs on the tail scale
XD = DO[['proj_rel', 'prev_rel']].to_numpy()
XI = R[['proj_rel_detail', 'prev_rel']].to_numpy()
draws = rng.multivariate_normal([B_PROJ, B_PREV], VB, size=B_COEF)
ED = XD @ draws.T
cen_d = (WO[:, None] * ED).sum(0) / WO.sum()
sd_d = np.sqrt((WO[:, None] * (ED - cen_d) ** 2).sum(0) / (WO.sum() - (WO ** 2).sum() / WO.sum()))
EI = XI @ draws.T - cen_d
out_d = np.clip(EI / (2 * sd_d), -1, 1)
JOBS_V = R.jobs.to_numpy()
blend_d = (out_d + JOBS_V[:, None]) / 2
R['se_coef_output'] = out_d.std(1, ddof=1)
R['se_coef'] = blend_d.std(1, ddof=1)
R['se_revision'] = RMS_REV / np.sqrt(2)
R['se_proxy'] = (R.output - R.jobs).abs() / 2
R['se'] = np.sqrt(R.se_coef ** 2 + R.se_revision ** 2 + R.se_proxy ** 2)
# sensitivity: anchors fixed in pp/yr; jobs slope drawn from N(1, se^2)
out_fa = np.clip(EI / ANCHOR_O, -1, 1)
mj = rng.normal(1.0, JOBS_SLOPE_SE, size=B_COEF)
jobs_fa = np.clip(np.outer(R.emp_rel.to_numpy(), mj) / ANCHOR_J, -1, 1)
R['se_coef_fixed_anchor'] = ((out_fa + jobs_fa) / 2).std(1, ddof=1)
R['se_coef_fixed_anchor_output'] = out_fa.std(1, ddof=1)
R['se_coef_fixed_anchor_jobs'] = jobs_fa.std(1, ddof=1)
R['change_vs_2024_34'] = stab.change.astype(float)
R.to_csv(OUT + '/tail_16.csv', float_format='%.6g')

# ---------------------------------------------------------------- A8. context: today's values
context_tail = dict(spearman=dict(blend=spearman(R.blend, TAIL_NOW), output=spearman(R.output, TAIL_NOW), jobs=spearman(R.jobs, TAIL_NOW)),
                    pearson=dict(blend=float(np.corrcoef(R.blend, TAIL_NOW)[0, 1]), output=float(np.corrcoef(R.output, TAIL_NOW)[0, 1]),
                                 jobs=float(np.corrcoef(R.jobs, TAIL_NOW)[0, 1])),
                    spearman_output_vs_jobs=spearman(R.output, R.jobs), mean_shipped=float(R.blend.mean()),
                    mean_current=float(TAIL_NOW.mean()), sd_shipped=float(R.blend.std()), sd_current=float(TAIL_NOW.std(ddof=1)),
                    mean_change_growth_subscore_arg=float(0.55 * (R.blend.mean() - TAIL_NOW.mean())),
                    mean_change_market_position_arg=float(0.9 * (R.blend.mean() - TAIL_NOW.mean())))
print('  vs today: Spearman blend %.2f (output %.2f, jobs %.2f); mean %.3f vs %.3f'
      % (context_tail['spearman']['blend'], context_tail['spearman']['output'], context_tail['spearman']['jobs'],
         context_tail['mean_shipped'], context_tail['mean_current']))
for k in KEYS:
    r = R.loc[k]
    print('  %-7s E %+.2f pp -> out %+.3f | jobs %+.2f pp -> %+.3f | tail %+.3f se %.3f (coef %.3f rev %.3f proxy %.3f) | now %+.2f'
          % (k, r.E, r.output, r.emp_rel, r.jobs, r.blend, r.se, r.se_coef, r.se_revision, r.se_proxy, r.current))

# ---------------------------------------------------------------- B1. comps rule
print('B. comps')
K6 = MV['industry_shrinkage']['k_naics6']
N6, E6, E2 = MV['industry_n6'], MV['industry_effects_naics6'], MV['industry_effects']
CELL = dict(MV['naics6_for_industry'])
assert K6 == 25 and CELL == I2N6 and set(CELL) == set(KEYS) - {'saas'} and SAAS_CELL not in N6 and min(N6.values()) == 8 > SAAS_N
N_IND = {k: (N6[CELL[k]] if k in CELL else SAAS_N) for k in KEYS}
COMPS = {k: N_IND[k] / (N_IND[k] + K6) for k in KEYS}

# ---------------------------------------------------------------- B2. method-of-moments k from the value model's table
cells = sorted(N6)
assert set(cells) == set(E6) and all(c[:2] in E2 for c in cells)
n = np.array([N6[c] for c in cells], float)
dev = np.array([E6[c] - E2[c[:2]] for c in cells])
raw = dev * (n + K6) / n
y, x = raw ** 2, 1.0 / n
mo = sm.OLS(y, sm.add_constant(x)).fit(cov_type='HC1')
TAU2, SIG2 = float(mo.params[0]), float(mo.params[1])
K_HAT = SIG2 / TAU2
mw = sm.WLS(y, sm.add_constant(x), weights=1.0 / (x + 0.02)).fit()          # the research's weights
tg, sg = TAU2, SIG2
for _ in range(50):                                                         # feasible GLS: var(raw^2) ~ 2 (tau2 + sig2/n)^2
    f = sm.WLS(y, sm.add_constant(x), weights=1.0 / (max(tg, 1e-6) + max(sg, 1e-6) * x) ** 2).fit()
    tg, sg = float(f.params[0]), float(f.params[1])


def nll(p):
    v = np.exp(p[0]) + np.exp(p[1]) * x
    return 0.5 * float(np.sum(np.log(v) + raw ** 2 / v))


ml = optimize.minimize(nll, np.log([TAU2, SIG2]), method='Nelder-Mead', options=dict(xatol=1e-10, fatol=1e-12, maxiter=5000))
TAU2_ML, SIG2_ML = float(np.exp(ml.x[0])), float(np.exp(ml.x[1]))
XB = np.c_[np.ones_like(x), x]
idx = rng.integers(0, len(cells), size=(B_K, len(cells)))
kb = np.empty(B_K)
for i in range(B_K):
    cb = np.linalg.lstsq(XB[idx[i]], y[idx[i]], rcond=None)[0]
    kb[i] = cb[1] / cb[0] if cb[0] > 0 else np.inf
share_pos = float(np.mean(np.isfinite(kb)))
qm = 'linear' if share_pos == 1.0 else 'inverted_cdf'
K_LO, K_MED, K_HI = (float(np.quantile(kb, q, method=qm)) for q in (0.05, 0.5, 0.95))
SE_FROM_K = {k: float(np.std(N_IND[k] / (N_IND[k] + kb), ddof=1)) for k in KEYS}
kmom = dict(cells=len(cells), rows=int(n.sum()), tau2=TAU2, tau2_se=float(mo.bse[0]), sigma2=SIG2, sigma2_se=float(mo.bse[1]),
            k_ols=K_HAT, k_wls_research=float(mw.params[1] / mw.params[0]), k_fgls=sg / tg, k_ml=SIG2_ML / TAU2_ML,
            tau2_ml=TAU2_ML, sigma2_ml=SIG2_ML, boot=dict(B=B_K, median=K_MED, ci90=[K_LO, K_HI], share_tau2_positive=share_pos),
            per_deal_sd_effect_scale=float(np.sqrt(SIG2)), between_cell_sd_effect_scale=float(np.sqrt(TAU2)))
pd.DataFrame(dict(naics6=cells, n=n.astype(int), effect=[E6[c] for c in cells], parent=[E2[c[:2]] for c in cells], dev=dev,
                  raw=raw, weight_k25=n / (n + K6))).to_csv(OUT + '/comps_cells.csv', index=False, float_format='%.6g')
print('  k_hat OLS %.2f (tau2 %.4f se %.4f, sigma2 %.3f se %.3f); WLS %.1f, FGLS %.1f, ML %.1f; bootstrap median %.1f, 90%% %.1f-%.1f'
      % (K_HAT, TAU2, mo.bse[0], SIG2, mo.bse[1], kmom['k_wls_research'], kmom['k_fgls'], kmom['k_ml'], K_MED, K_LO, K_HI))

# ---------------------------------------------------------------- B3. BizBuySell 2016 -> 2017 stability
D = pd.read_csv(BBS)
sub = D[(D.dimension != 'market') & D.data_year.isin([2016, 2017])].copy()
sub['lab'] = sub.label2.str.replace('Internet-', '', regex=False).str.replace('Wholesale-', '', regex=False).str.strip()
assert not sub.duplicated(['data_year', 'lab']).any()
w = sub.pivot_table(index='lab', columns='data_year', values=['n_sales', 'cash_flow_multiple_avg'])
w.columns = ['%s_%s' % (a, b) for a, b in w.columns]
w = w.dropna()
w = w[(w.n_sales_2016 >= 2) & (w.n_sales_2017 >= 2)].copy()
w['d'] = w.cash_flow_multiple_avg_2017 - w.cash_flow_multiple_avg_2016
w['h'] = 1 / w.n_sales_2016 + 1 / w.n_sales_2017
mb_ = sm.OLS(w.d ** 2, sm.add_constant(w.h)).fit(cov_type='HC1')
s2, vchange = float(mb_.params['h']), float(mb_.params['const'])
mm = (w.cash_flow_multiple_avg_2016 + w.cash_flow_multiple_avg_2017) / 2
tau2b = float(mm.var() - ((s2 / 4) * w.h).mean())


def thick_thin(cut):
    th = w[(w.n_sales_2016 >= cut) & (w.n_sales_2017 >= cut)]; tn = w[(w.n_sales_2016 < cut) | (w.n_sales_2017 < cut)]
    r1 = float(np.corrcoef(th.cash_flow_multiple_avg_2016, th.cash_flow_multiple_avg_2017)[0, 1])
    r2 = float(np.corrcoef(tn.cash_flow_multiple_avg_2016, tn.cash_flow_multiple_avg_2017)[0, 1])
    z = (np.arctanh(r1) - np.arctanh(r2)) / np.sqrt(1 / (len(th) - 3) + 1 / (len(tn) - 3))
    return dict(cut=cut, r_thick=r1, n_thick=int(len(th)), r_thin=r2, n_thin=int(len(tn)), fisher_z=float(z),
                p_two_sided=float(2 * stats.norm.sf(abs(z))), mean_abs_change_thick=float(th.d.abs().mean()),
                mean_abs_change_thin=float(tn.d.abs().mean()))


TT = {c: thick_thin(c) for c in (30, 50, 100)}
bbs = dict(subsectors=int(len(w)), deals_2016=int(w.n_sales_2016.sum()), deals_2017=int(w.n_sales_2017.sum()),
           corr_all=float(np.corrcoef(w.cash_flow_multiple_avg_2016, w.cash_flow_multiple_avg_2017)[0, 1]),
           deal_level_var=s2, deal_level_var_se=float(mb_.bse['h']), var_true_change=vchange, var_true_change_se=float(mb_.bse['const']),
           between_var=tau2b, k=s2 / tau2b, spearman_abs_change_vs_h=spearman(w.d.abs(), w.h), thick_thin=TT)
w.to_csv(OUT + '/comps_bbs_yoy.csv', float_format='%.6g')
print('  BizBuySell 2016->2017: %d sub-sectors; r thick %.3f (n %d) vs thin %.3f (n %d), Fisher p %.2g; k %.1f (deal var %.2f se %.2f)'
      % (len(w), TT[50]['r_thick'], TT[50]['n_thick'], TT[50]['r_thin'], TT[50]['n_thin'], TT[50]['p_two_sided'], bbs['k'], s2,
         bbs['deal_level_var_se']))

# ---------------------------------------------------------------- B4. orderings: today's comps, SBA, BizBuySell counts
sba = pd.read_csv(SBA, dtype={'NaicsCode': str}, usecols=['Program', 'ApprovalDate', 'NaicsCode', 'LoanStatus'])
sba = sba[(sba.Program.str.strip() == '7A') & (sba.LoanStatus != 'CANCLD')]
dates = pd.to_datetime(sba.ApprovalDate)
SPAN = (dates.max() - dates.min()).days / 365.25
SBA_N = {k: int(sba.NaicsCode.isin(SBA_CELLS[k]).sum()) for k in KEYS}
SBA_PY = {k: SBA_N[k] / SPAN for k in KEYS}
b18 = D[(D.dimension != 'market') & (D.data_year == 2018)].set_index('label2').n_sales
BBS18_N = {}
for k in KEYS:
    labs = [l for l in b18.index if l.endswith('Manufacturers') or 'Manufacturing' in l] if BBS18[k] == 'MANUFACTURING' else BBS18[k]
    BBS18_N[k] = float(sum(b18.get(l, 0) for l in labs)) if labs else np.nan
BBS25_N = {k: MV['price_realisation_by_industry']['n'].get(k, np.nan) for k in KEYS}
cv = np.array([COMPS[k] for k in KEYS])


def sp_ok(other):
    o = np.array([other[k] for k in KEYS], float); ok = np.isfinite(o)
    return [spearman(cv[ok], o[ok]), int(ok.sum())]


orderings = dict(current=sp_ok(dict(zip(KEYS, COMPS_NOW))), sba_chow_per_year=sp_ok(SBA_PY), bizbuysell_2025=sp_ok(BBS25_N),
                 bizbuysell_2018=sp_ok(BBS18_N), sba_span_years=SPAN, sba_loans=int(len(sba)),
                 sba_first=str(dates.min().date()), sba_last=str(dates.max().date()))
C = pd.DataFrame({k: dict(naics6=CELL.get(k, SAAS_CELL), n6=N_IND[k], comps_k25=COMPS[k], se_from_k=SE_FROM_K[k],
                          comps_k_lo=N_IND[k] / (N_IND[k] + K_HI), comps_k_hi=N_IND[k] / (N_IND[k] + K_LO),
                          comps_k_hat=N_IND[k] / (N_IND[k] + K_HAT), current=IND_NOW[k]['comps'], sba_cells='+'.join(SBA_CELLS[k]),
                          sba_loans=SBA_N[k], sba_per_year=SBA_PY[k], bizbuysell_2025=BBS25_N[k], bizbuysell_2018=BBS18_N[k])
                  for k in KEYS}).T
C.index.name = 'ind'
C.to_csv(OUT + '/comps_16.csv', float_format='%.6g')
context_comps = dict(mean_values=float(cv.mean()), mean_current=float(COMPS_NOW.mean()),
                     mean_change_confidence=float(0.34 * (cv.mean() - COMPS_NOW.mean())),
                     mean_change_market_position_arg=float(0.4 * (cv.mean() - COMPS_NOW.mean())),
                     above_high_threshold_68=dict(values=int((cv > .68).sum()), current=int((COMPS_NOW > .68).sum())),
                     saas_note='the value model has no saas cell and prices saas from its 2-digit sector 51; n = 7 gives the weight '
                               'a 7-row cell would get (%.3f), not a weight the value model uses' % COMPS['saas'])
print('  Spearman with today %.2f, with SBA CHOW %.2f (BizBuySell 2025 %.2f n %d, 2018 %.2f n %d); mean %.3f vs today %.3f'
      % (orderings['current'][0], orderings['sba_chow_per_year'][0], orderings['bizbuysell_2025'][0], orderings['bizbuysell_2025'][1],
         orderings['bizbuysell_2018'][0], orderings['bizbuysell_2018'][1], cv.mean(), COMPS_NOW.mean()))
for k in KEYS:
    print('  %-7s %s n %4d  comps %.3f (se_k %.3f, band %.3f-%.3f)  now %.2f  SBA/yr %.1f'
          % (k, C.loc[k, 'naics6'], N_IND[k], COMPS[k], SE_FROM_K[k], C.loc[k, 'comps_k_lo'], C.loc[k, 'comps_k_hi'],
             IND_NOW[k]['comps'], SBA_PY[k]))

# ---------------------------------------------------------------- tables to embed
lovo_vs = EVAL_VINTAGES
mapping = {}
for k in KEYS:
    o = ' + '.join('%d %s' % (s, SEC_TITLE[s]) for s in OUT_SECTORS[k])
    if k in REFINE:
        o += ' (plus jobs %s minus %s)' % REFINE[k]
    mapping[k] = 'output: ' + o + '; jobs: ' + ' + '.join('%s %s' % (c, title211[c]) for c in JOBS[k]) + MAP_NOTE.get(k, '')
tail_table = {
    'by_industry': {k: rnd(R.loc[k, 'blend'], 2) for k in KEYS},
    'se': {k: rnd(R.loc[k, 'se'], 2) for k in KEYS},
    'components': {'output': {k: rnd(R.loc[k, 'output'], 2) for k in KEYS}, 'jobs': {k: rnd(R.loc[k, 'jobs'], 2) for k in KEYS}},
    'pp_per_yr': {'output': {k: rnd(R.loc[k, 'E'], 2) for k in KEYS}, 'jobs': {k: rnd(R.loc[k, 'emp_rel'], 2) for k in KEYS}},
    'anchors_pp_per_yr': {'output': rnd(ANCHOR_O, 3), 'jobs': rnd(ANCHOR_J, 3)},
    'coef': {'proj': [rnd(B_PROJ, 3), rnd(fb.bse['proj_rel'], 3)], 'prev': [rnd(B_PREV, 3), rnd(fb.bse['prev_rel_cur'], 3)],
             'n': int(len(A)), 'sectors': int(A.sec.nunique()), 'r2': rnd(fb.rsquared, 3)},
    'vintage': 'BLS EP 2025-35, released 2026-08-27',
    'oos': {
        'vintages': lovo_vs, 'n': [LOVO[v]['n'] for v in lovo_vs],
        'mse_centred': {'bridge': [rnd(LOVO[v]['msec_bridge'], 2) for v in lovo_vs],
                        'bls_raw': [rnd(LOVO[v]['msec_bls_raw'], 2) for v in lovo_vs],
                        'no_difference': [rnd(LOVO[v]['msec_zero'], 2) for v in lovo_vs]},
        'mse': {'bridge': [rnd(LOVO[v]['mse_bridge'], 2) for v in lovo_vs], 'bls_raw': [rnd(LOVO[v]['mse_bls_raw'], 2) for v in lovo_vs],
                'no_difference': [rnd(LOVO[v]['mse_zero'], 2) for v in lovo_vs]},
        'spearman': {'bridge': [rnd(LOVO[v]['spearman_bridge'], 2) for v in lovo_vs],
                     'bls_raw': [rnd(LOVO[v]['spearman_bls_raw'], 2) for v in lovo_vs]},
        'jobs': {'vintages': [v for v in jobs_eval if v != 'pooled'],
                 'spearman': [rnd(jobs_eval[v]['spearman'], 2) for v in jobs_eval if v != 'pooled'],
                 'slope': [rnd(JOBS_SLOPE, 2), rnd(JOBS_SLOPE_SE, 2)], 'n': int(len(G))},
        'expanding': {'vintages': list(EXPAND), 'mse_centred': {
            'bridge': [rnd(s['msec_bridge'], 2) for s in EXPAND.values()], 'bls_raw': [rnd(s['msec_bls_raw'], 2) for s in EXPAND.values()],
            'no_difference': [rnd(s['msec_zero'], 2) for s in EXPAND.values()]}},
        'blend_check': {'vintages': list(blend_eval), 'outcomes': 'Spearman with realised relative growth: output, jobs, their '
                        'standardised average', **{o: {p: [rnd(x['%s_vs_%s' % (p, o)], 2) for x in blend_eval.values()]
                                                       for p in ('blend', 'output', 'jobs')} for o in ('output', 'jobs', 'combined')}},
        'note': 'held-out vintages overlap in calendar time (realised windows 2012-25), so expanding (earlier vintages only) is '
                'the cleaner check; MSE in (pp/yr)^2 of realised relative real-output growth; centred = after removing each '
                'vintage mean (the shipped table is centred)'},
    'stability': {'vs': '2024-34', 'pearson': rnd(stability['pearson'], 2), 'spearman': rnd(stability['spearman'], 2),
                  'mean_abs_change': rnd(stability['mean_abs_change'], 2), 'max_abs_change': [rnd(stability['max_abs_change'][0], 2), imax],
                  'tolerance': STABILITY_TOL},
    'current': {'spearman': rnd(context_tail['spearman']['blend'], 2), 'mean': rnd(context_tail['mean_current'], 2),
                'mean_fitted': rnd(context_tail['mean_shipped'], 2)},
    'mapping': mapping,
    'source': 'BLS Employment Projections 2025-35 (released 2026-08-27): real output (chained 2017 $) and jobs by industry, 2025 '
              'and projected 2035 (industry.zip: proj2035.csv, ind2025.csv 1997-2025, emp2025.csv, SectorPlan2035.xlsx; '
              'industry.xlsx Table 2.11). Bridge fitted on the archived 2012-22, 2014-24, 2016-26 and 2018-28 projections '
              'against realised growth to 2025; stability against 2024-34. fit6 industry_tailwind_and_comps.py',
    'method': 'tail = mean of two maps, each clamped to [-1,1]. Output: E = %.3f proj_rel + %.3f prev_rel (pp/yr; proj_rel = '
              'projected 2025-35 real-output CAGR minus the total, prev_rel = realised 2015-25 minus the total; coefficients '
              'from realised-on-projected regressions over 4 past vintages, %d sector-vintages, sector-clustered), centred on '
              'the output-weighted sector mean, divided by %.3f pp/yr = 2 output-weighted cross-sector SDs of E; where the '
              'console industry is finer than BLS output (home, constr, auto, wash, land, fit, staff) its 6-digit job growth '
              'differential is added to proj_rel. Jobs: projected 2025-35 job CAGR of the industry\'s finest Table 2.11 line '
              '(6-digit where BLS has one) minus all jobs, divided by %.3f pp/yr '
              '= 2 job-weighted cross-sector SDs (realised-on-projected slope %.2f, so unscaled). 0 = all-industry average and '
              '+-1 = +-2 cross-sector SDs are conventions. Values and SEs rounded half away from zero to 0.01.'
              % (B_PROJ, B_PREV, len(A), ANCHOR_O, ANCHOR_J, JOBS_SLOPE),
    'se_note': 'se = sqrt(coef^2 + revision^2 + proxy^2): coef = output coefficients drawn from their clustered covariance '
               '(anchor and centre re-derived per draw; %.2f-%.2f); revision = RMS change of the 16 values 2024-34 to 2025-35 '
               '/ sqrt 2 (%.2f, all industries); proxy = half the output-jobs gap (0-%.2f). Expected tailwind only: one '
               'industry\'s realised decade varies far more (R2 about 0.2-0.3).'
               % (R.se_coef.min(), R.se_coef.max(), RMS_REV / np.sqrt(2), R.se_proxy.max()),
}
comps_table = {
    'rule': 'n6/(n6+k)',
    'k_source': 'MODELS.value.industry_shrinkage.k_naics6',
    'n_source': 'MODELS.value.industry_n6[MODELS.value.naics6_for_industry[ind]]',
    'n_override': {'saas': SAAS_N},
    'k_hat': rnd(K_HAT, 1),
    'k_hat_ci90': [rnd(K_LO, 1), rnd(K_HI, 1)],
    'k_hat_alt': {'wls': rnd(kmom['k_wls_research'], 1), 'fgls': rnd(kmom['k_fgls'], 1), 'ml': rnd(kmom['k_ml'], 1)},
    'stability': {'r_thick': rnd(TT[50]['r_thick'], 2), 'r_thin': rnd(TT[50]['r_thin'], 2), 'n_thick': TT[50]['n_thick'],
                  'n_thin': TT[50]['n_thin'], 'cut': 50, 'fisher_p': float('%.2g' % TT[50]['p_two_sided']),
                  'mean_abs_change': [rnd(TT[50]['mean_abs_change_thick'], 2), rnd(TT[50]['mean_abs_change_thin'], 2)],
                  'k_hat_bbs': rnd(bbs['k'], 1), 'subsectors': bbs['subsectors'], 'deals': [bbs['deals_2016'], bbs['deals_2017']]},
    'spearman': {'current': rnd(orderings['current'][0], 2), 'sba_chow': rnd(orderings['sba_chow_per_year'][0], 2), 'n': 16},
    'values_at_k25': {k: rnd(COMPS[k], 3) for k in KEYS},
    'se_from_k': {k: rnd(SE_FROM_K[k], 3) for k in KEYS},
    'source': 'BIZCOMPS closed-sale counts per NAICS-6 cell held by the value model (MODELS.value.industry_n6: %d cells, %s '
              'sales; k_naics6 = 25); saas 511210 = 7 rows (below the 8-row cut). Checks: BizBuySell Insight closed-deal tables '
              'by sub-sector, full-year 2016-17 (Common Crawl captures); SBA 7(a) change-of-ownership loans FY2018-26 (FOIA as '
              'of 2026-06-30). fit6 industry_tailwind_and_comps.py' % (len(cells), '{:,}'.format(int(n.sum()))),
    'method': 'comps = n6/(n6+k), the weight the value model puts on the industry\'s own BIZCOMPS cell (effect = parent + '
              '(cell - parent) n/(n+k)), computed in the page. k = 25 is the value model\'s; a method-of-moments estimate '
              'from its own 274-cell table (de-shrunk effects, raw^2 on 1/n) gives k_hat = %.1f, cell-bootstrap 90%% %.1f-%.1f, '
              'so 25 is consistent. BizBuySell sub-sector multiples: year-to-year r %.2f where both years have 50+ sales vs '
              '%.2f below. se_from_k = SD of n/(n+k) over the bootstrap draws of k. Values rounded to 0.001.'
              % (K_HAT, K_LO, K_HI, TT[50]['r_thick'], TT[50]['r_thin']),
}
JS = {'tailwind': tail_table, 'comps': comps_table}
dumps = lambda o: json.dumps(jsonable(o), sort_keys=True, separators=(',', ':'))
JS_LINES = ['MODELS.fitted.tailwind=' + dumps(tail_table) + ';', 'MODELS.fitted.comps=' + dumps(comps_table) + ';']

# ---------------------------------------------------------------- C. tests
print('C. tests')
bi = tail_table['by_industry']; cp = tail_table['components']
check('tail: 16 industries, finite, in [-1, 1]', list(bi) == KEYS and all(v is not None and -1 <= v <= 1 for v in bi.values()))
check('tail: components in [-1, 1] and by_industry within 0.01 of their mean',
      all(-1 <= cp[c][k] <= 1 for c in cp for k in KEYS) and all(abs(bi[k] - (cp['output'][k] + cp['jobs'][k]) / 2) <= 0.0100001 for k in KEYS))
check('tail: SEs positive', all(v > 0 for v in tail_table['se'].values()))
check('tail: bridge coefficients round to the decision (0.958, 0.273)', rnd(B_PROJ, 3) == REPORT['b_proj'] and rnd(B_PREV, 3) == REPORT['b_prev'],
      [B_PROJ, B_PREV])
check('tail: anchors round to the decision (3.06, 1.11 pp/yr)', rnd(ANCHOR_O, 2) == REPORT['anchor_out'] and rnd(ANCHOR_J, 2) == REPORT['anchor_jobs'],
      [ANCHOR_O, ANCHOR_J])
diff = {k: float(R.loc[k, 'blend'] - REPORT_BLEND[k]) for k in KEYS}
check('tail: reproduces the research blend (within 0.006 of the report table)', max(abs(v) for v in diff.values()) <= 0.006,
      {k: round(v, 4) for k, v in diff.items() if abs(v) > 0.004})
check('tail: bridge beats no-difference in all 4 held-out vintages (centred MSE)',
      all(LOVO[v]['msec_bridge'] < LOVO[v]['msec_zero'] for v in lovo_vs))
nb = sum(LOVO[v]['msec_bridge'] < LOVO[v]['msec_bls_raw'] for v in lovo_vs)
check('tail: bridge beats BLS raw projection in at least 3 of 4 held-out vintages (centred MSE)', nb >= 3, nb)
check('tail: bridge rank correlation positive in every held-out vintage', all(LOVO[v]['spearman_bridge'] > 0 for v in lovo_vs))
check('tail: jobs slope within 2 SE of 1 (projected jobs used unscaled)', abs(JOBS_SLOPE - 1) < 2 * JOBS_SLOPE_SE, [JOBS_SLOPE, JOBS_SLOPE_SE])
check('tail: the blend ranks the combined outcome at least as well as the weaker part in every vintage',
      all(x['blend_vs_combined'] >= min(x['output_vs_combined'], x['jobs_vs_combined']) for x in blend_eval.values()))
check('tail: the blend ranks realised output growth better than the output map alone in every vintage',
      all(x['blend_vs_output'] > x['output_vs_output'] for x in blend_eval.values()),
      {v: [round(x['blend_vs_output'], 3), round(x['output_vs_output'], 3)] for v, x in blend_eval.items()})
check('tail: expanding window: bridge beats BLS raw projection and no-difference in every later vintage (centred MSE)',
      all(s['msec_bridge'] < min(s['msec_bls_raw'], s['msec_zero']) for s in EXPAND.values()),
      {v: [round(s['msec_bridge'], 2), round(s['msec_bls_raw'], 2), round(s['msec_zero'], 2)] for v, s in EXPAND.items()})
check('tail: 2024-34 -> 2025-35 changes all below the 0.3 tolerance', stability['max_abs_change'][0] < STABILITY_TOL,
      stability['max_abs_change'])
check('tail: Table 2.11 machinery reproduces the shipped values within 0.05', stability['machinery_vs_shipped_max_abs'] < 0.05,
      stability['machinery_vs_shipped_max_abs'])
cv25 = comps_table['values_at_k25']
recomp = {k: (MV['industry_n6'][MV['naics6_for_industry'][k]] if k in MV['naics6_for_industry'] else comps_table['n_override'][k])
          for k in KEYS}
check('comps: page rule n6/(n6+k) from MODELS.value reproduces values_at_k25', all(abs(recomp[k] / (recomp[k] + K6) - cv25[k]) <= 0.0005 for k in KEYS))
check('comps: 16 values in (0, 1)', list(cv25) == KEYS and all(0 < v < 1 for v in cv25.values()))
check('comps: k = 25 inside the bootstrap 90% interval of k_hat', K_LO <= K6 <= K_HI, [K_LO, K_HI])
check('comps: k_hat and its interval match the research (17.9, 6.9-43.8) within 10%',
      abs(K_HAT / REPORT['k_hat'] - 1) < 0.1 and abs(K_LO / REPORT['k_ci90'][0] - 1) < 0.1 and abs(K_HI / REPORT['k_ci90'][1] - 1) < 0.1,
      [K_HAT, K_LO, K_HI])
check('comps: BizBuySell thick sub-sectors more stable than thin (Fisher p < 0.05) at cuts 30, 50 and 100',
      all(TT[c]['r_thick'] > TT[c]['r_thin'] and TT[c]['p_two_sided'] < 0.05 for c in TT), {c: [round(TT[c]['r_thick'], 3), round(TT[c]['r_thin'], 3), round(TT[c]['p_two_sided'], 4)] for c in TT})
check('comps: BizBuySell numbers match the research (r 0.92 / 0.24, n 29 / 32, k 8.6)',
      rnd(TT[50]['r_thick'], 2) == REPORT['r_thick'] and rnd(TT[50]['r_thin'], 2) == REPORT['r_thin'] and TT[50]['n_thick'] == REPORT['n_thick']
      and TT[50]['n_thin'] == REPORT['n_thin'] and rnd(bbs['k'], 1) == REPORT['k_bbs'])
check('comps: positive rank agreement with today and with SBA CHOW counts', orderings['current'][0] > 0 and orderings['sba_chow_per_year'][0] > 0,
      [orderings['current'], orderings['sba_chow_per_year']])

# ---------------------------------------------------------------- RESULT.json
def src(name, url, path, years, nobs, used):
    return dict(name=name, url=url, file=path, sha256=sha256(path)[:16], years=years, n=nobs, used=used)


ARCH_N = {v: int(len(ARCH[v][0])) for v in EVAL_VINTAGES}
sources = [
    src('BLS Employment Projections 2025-35, industry output and employment data files', 'https://www.bls.gov/emp/industry-employment/industry.zip',
        EP_ZIP, 'output 1997-2025, jobs 2013-2025, 2025 and projected 2035 (released 2026-08-27)',
        '%d sectors (176 detailed + 54 aggregates); members ind2025.csv, emp2025.csv, proj2035.csv, SectorPlan2035.xlsx' % PO.shape[0],
        'sector projections and history; realised growth for the evaluation; centre and anchors'),
    src('BLS Employment Projections 2025-35, Table 2.11 Employment and output by industry', 'https://www.bls.gov/emp/industry-employment/industry.xlsx',
        EP_TABLES, '2025, projected 2035', '%d rows' % len(T25), '6-digit jobs (jobs map, refinement); stability machinery'),
] + [src('BLS EP projections archive %s, "Employment and output by industry" (%s)' % (v, ARCH[v][2]),
         'https://www.bls.gov/emp/projections-archive/%s.zip' % v, EP_ARCH[v], v, '%d rows; %d detailed sectors matched' % (ARCH_N[v], per_vintage[v]['n']),
         'evaluation (bridge, leave-one-vintage-out, jobs slope)') for v in EVAL_VINTAGES] + [
    src('BLS EP projections archive 2024-34, Table 2.11', 'https://www.bls.gov/emp/projections-archive/2024-34.zip', EP_ARCH['2024-34'],
        '2024, projected 2034', '%d rows' % len(T24), 'stability check'),
    src('Console snapshot index.html (MODELS.value from BIZCOMPS, IND, IND2NAICS6)', 'local, frozen snapshot of HEAD 56ba230', INDEX,
        'BIZCOMPS closed sales (value model n_fit %s)' % MV.get('n_fit'), '%d NAICS-6 cells, %d rows' % (len(cells), int(n.sum())),
        'comps counts and k; method-of-moments k; today\'s tail and comps (context)'),
    src('BizBuySell Insight Report closed-deal tables by sector, full-year 2016-18 (Common Crawl captures)',
        'https://www.bizbuysell.com/news/media_insight.html (via data.commoncrawl.org)', BBS, '2016, 2017 (2018 context)',
        '%d sub-sectors matched 2016-17 (%d and %d sales)' % (bbs['subsectors'], bbs['deals_2016'], bbs['deals_2017']), 'stability test; 2018 counts (context)'),
    src('SBA 7(a) FOIA change-of-ownership loans (data5 extract)', 'https://data.sba.gov/dataset/7a-504-foia', SBA,
        'FY2018-26 (%s to %s)' % (orderings['sba_first'], orderings['sba_last']), '%d non-cancelled 7(a) loans' % len(sba), 'ordering check'),
]
shipped = {'tailwind': {k: dict(value=tail_table['by_industry'][k], se=tail_table['se'][k], unrounded=r6(R.loc[k, 'blend']),
                                output=r6(R.loc[k, 'output']), jobs=r6(R.loc[k, 'jobs']), E_pp=r6(R.loc[k, 'E']), emp_rel_pp=r6(R.loc[k, 'emp_rel']),
                                jobs_adj_pp=r6(R.loc[k, 'jobs_adj']), se_coef=r6(R.loc[k, 'se_coef']), se_revision=r6(R.loc[k, 'se_revision']),
                                se_proxy=r6(R.loc[k, 'se_proxy']), se_coef_fixed_anchor=r6(R.loc[k, 'se_coef_fixed_anchor']),
                                change_vs_2024_34=r6(R.loc[k, 'change_vs_2024_34']), current=IND_NOW[k]['tail'],
                                current_minus_value_in_se=r6((IND_NOW[k]['tail'] - R.loc[k, 'blend']) / R.loc[k, 'se'])) for k in KEYS},
           'comps': {k: dict(value_at_k25=cv25[k], se_from_k=comps_table['se_from_k'][k], unrounded=r6(COMPS[k]), n6=N_IND[k],
                             naics6=CELL.get(k, SAAS_CELL), band_k_ci90=[r6(C.loc[k, 'comps_k_lo']), r6(C.loc[k, 'comps_k_hi'])],
                             current=IND_NOW[k]['comps']) for k in KEYS}}
be = blend_eval; bev = list(be)
f2 = lambda xs: '/'.join('%.2f' % x for x in xs)
wide = [k for k in KEYS if R.loc[k, 'se_proxy'] > 0.15]
c74 = anchor_sens['anchor_output_without_174']
OPEN = [
    'tail level: the 16 fitted values average %.2f against %.2f today (SD %.2f vs %.2f), so the Growth sub-score argument falls by '
    '%.2f and Market position by %.2f on average (before the comps change); the wider spread also widens those sub-scores across '
    'industries. 0 = all-industry average is a convention; on it the console industries carry little tailwind on average.'
    % (context_tail['mean_shipped'], context_tail['mean_current'],
                                                                  context_tail['sd_shipped'], context_tail['sd_current'],
                                                                  -context_tail['mean_change_growth_subscore_arg'], -context_tail['mean_change_market_position_arg']),
    'tail SEs are dominated by the output-vs-jobs disagreement where BLS output is coarse: %s. The sign is not pinned for %s.'
    % ('; '.join('%s %.2f (output %+.2f, jobs %+.2f, se %.2f)' % (k, R.loc[k, 'blend'], R.loc[k, 'output'], R.loc[k, 'jobs'], R.loc[k, 'se']) for k in wide),
       ', '.join(k for k in KEYS if abs(R.loc[k, 'blend']) < R.loc[k, 'se'])),
    'blend vs parts (Spearman, vintages %s): on realised output growth the blend beats both parts (%s vs output map %s, jobs map %s); '
    'on realised job growth the jobs map alone is best (%s vs blend %s); on their average the jobs map alone edges the blend '
    '(%s vs %s), within noise. The blend is defensible; the output map alone is the weakest predictor.'
    % (', '.join(bev), f2([be[v]['blend_vs_output'] for v in bev]), f2([be[v]['output_vs_output'] for v in bev]),
       f2([be[v]['jobs_vs_output'] for v in bev]), f2([be[v]['jobs_vs_jobs'] for v in bev]), f2([be[v]['blend_vs_jobs'] for v in bev]),
       f2([be[v]['jobs_vs_combined'] for v in bev]), f2([be[v]['blend_vs_combined'] for v in bev])),
    'leave-one-vintage-out: held-out windows overlap in calendar time; in 2012-22 BLS\'s raw projection beats the bridge on centred '
    'MSE (%.2f vs %.2f). The expanding-window check (earlier vintages only) has the bridge ahead in all 3 later vintages (%s vs raw %s).'
    % (LOVO['2012-22']['msec_bls_raw'], LOVO['2012-22']['msec_bridge'], f2([s['msec_bridge'] for s in EXPAND.values()]),
       f2([s['msec_bls_raw'] for s in EXPAND.values()])),
    'stability: from 2024-34 to 2025-35 the 16 values moved %.2f on average (RMS %.2f); %s moved %.2f, close to the 0.3 tolerance '
    '(BLS revised employment-services output from %+.2f to %+.2f pp/yr relative); fit %+.2f, dist %+.2f, home %+.2f. A future vintage '
    'can breach 0.3 for a volatile industry.' % (stability['mean_abs_change'], RMS_REV, imax, stability['max_abs_change'][0],
                                                stab.loc['staff', 'proj_rel_2024_34'], stab.loc['staff', 'proj_rel_2025_35'],
                                                stab.loc['fit', 'change'], stab.loc['dist', 'change'], stab.loc['home', 'change']),
    'rounding: home ships %.2f (unrounded %.4f); the research table shows +0.05 because it averaged rounded components. Anchors are '
    'stored to 0.001 (%.3f and %.3f pp/yr); the decision\'s 3.06 and 1.11 are their 2-decimal roundings (using 1.11 would move a '
    'jobs component by at most %.3f).' % (tail_table['by_industry']['home'], R.loc['home', 'blend'], ANCHOR_O, ANCHOR_J,
                                          float(np.max(np.abs(np.clip(R.emp_rel / 1.11, -1, 1) - R.jobs)))),
    'anchor sensitivity: the output centre and anchor include owner-occupied dwellings (sector 174, %.1f%% of output, no jobs); '
    'without it the anchor is %.3f pp/yr (output components x%.3f). The jobs zero is total jobs growth; the job-weighted mean of '
    'sector relative growth is %.4f pp/yr (%.3f on the tail scale). Both negligible.'
    % (100 * anchor_sens['sector_174_output_share'], c74, ANCHOR_O / c74, JOBS_MEAN_REL, JOBS_MEAN_REL / ANCHOR_J),
    'comps saas: the value model has no saas cell and prices saas from its 2-digit sector 51 (n2 = %d), so n = 7 (the 511210 count '
    'quoted in the page comment; the BIZCOMPS rows are not available to verify it) gives the weight a 7-row cell would get (%.3f), '
    'not a weight the value model uses; for the other 15 industries comps is exactly the value model\'s weight.'
    % (MV['industry_n'].get('51', -1), COMPS['saas']),
    'comps level: mean %.3f against %.3f today, so confidence rises by %.3f on average and Market position\'s .4(comps - .65) term by '
    '%.3f; %d of 16 values exceed the High threshold .68 (7 today). The integration should decide whether to keep the confidence '
    'label thresholds (High > .68, Moderate > .46) and the .65 centring.' % (context_comps['mean_values'], context_comps['mean_current'],
                                                                           context_comps['mean_change_confidence'], context_comps['mean_change_market_position_arg'],
                                                                           context_comps['above_high_threshold_68']['values']),
    'comps k: OLS method of moments %.1f (cell-bootstrap 90%% %.1f-%.1f), FGLS %.1f and normal ML %.1f; k = 25 sits inside every '
    'reading. The BizBuySell scale k (%.1f) is on levels of mean multiples, not comparable to 25. The moment sigma implies a '
    'per-deal SD of %.2f on the effect scale (x%.2f = %.2f in log price), above the final model\'s out-of-fold spread (log '
    'IQR/1.349 = %.2f); the page does not record whether the effects were built on first-stage residuals, so this scale '
    'cannot be checked here. A smaller sigma^2 would mean a smaller k (comps values closer to 1).'
    % (K_HAT, K_LO, K_HI, kmom['k_fgls'], kmom['k_ml'], bbs['k'], np.sqrt(SIG2), MV['coefficients']['ind_eff'],
       np.sqrt(SIG2) * MV['coefficients']['ind_eff'],
       np.log(MV['prediction_intervals']['p75'] / MV['prediction_intervals']['p25']) / 1.349),
]
RES = dict(name='industry_tailwind_and_comps', js_key='tailwind+comps', tier=dict(tailwind='aggregate', comps='fitted'),
           open_issues=OPEN,
           js_table=JS, js_lines=JS_LINES, shipped=shipped,
           parameters=dict(b_proj=B_PROJ, b_prev=B_PREV, cov_b=VB.tolist(), centre=CEN, anchor_output=ANCHOR_O, anchor_jobs=ANCHOR_J,
                           jobs_weighted_mean_rel=JOBS_MEAN_REL, total_output_cagr=tot_proj, total_prev_cagr=tot_prev, total_jobs_cagr=tot_emp,
                           total_jobs_cagr_table211=emp_tot_211, sectors_output=int(len(DO)), sectors_jobs=int(len(DJ)), anchor_sensitivity=anchor_sens,
                           k_naics6=K6, saas_n=SAAS_N, seed=SEED, B_coef=B_COEF, B_k=B_K,
                           rounding='half away from zero (Decimal ROUND_HALF_UP): tail values, components and SEs 0.01; anchors 0.001; comps values and se_from_k 0.001; k 0.1'),
           tail=dict(bridge=bridge, lovo=LOVO, expanding_window=EXPAND, jobs=jobs_eval, blend_oos=blend_eval, stability=stability,
                     context=context_tail, research_diff=diff),
           comps=dict(k_mom=kmom, bizbuysell=bbs, orderings=orderings, context=context_comps,
                      sba_per_year={k: r6(SBA_PY[k]) for k in KEYS}, bizbuysell_2018={k: BBS18_N[k] for k in KEYS}),
           tests=TESTS, tests_detail=TEST_DETAIL, sources=sources)
with open(OUT + '/RESULT.json', 'w') as f:
    json.dump(jsonable(RES), f, indent=1, sort_keys=True)
with open(OUT + '/js_lines.txt', 'w') as f:
    f.write('\n'.join(JS_LINES) + '\n')
print('tests passed: %d of %d' % (sum(TESTS.values()), len(TESTS)))
print('wrote', OUT + '/RESULT.json')
