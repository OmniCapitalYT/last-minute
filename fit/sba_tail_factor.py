#!/usr/bin/env python3
"""SBA tail factor (MODELS.risk.tail): years 9-10 of the acquisition-loan charge-off curve, fitted from mature 7(a)
term loans matched to the change-of-ownership book. October 2026, third round (the round-2 script and outputs are kept
as sba_tail_factor.v2.py and /tmp/claude-0/fit6/out/sba_tail_factor.v2/).

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/sba_tail_factor.py            (9-10 min on a busy 4-core machine; the
                                                                              raw files are re-read only when the
                                                                              loan-level cache is stale or missing)
      python3 -I .../sba_tail_factor.py --rebuild    re-read the raw FOIA files even if the cache is current
      python3 -I .../sba_tail_factor.py --quick      smoke test (small bootstraps; output to the scratch directory)
Out:  /tmp/claude-0/fit6/out/sba_tail_factor/RESULT.json (js_table = MODELS.risk.tail; js_key "tail"; js_code = tailAt),
      tables *.csv, run.log, the node probe it ran (probe.js, probe_cfg.json) and cache/ (the matched loan-level table,
      keyed by the sha256 of every raw input). Nothing in the repo or the snapshot is written.

Third round (the analyst's decisions on the round-2 review)
  - factor 1.21, factor_se 0.06: the SE is the like-for-like root sum of squares of the measured parts (0.057), drift
    included. The age-period model along each window's own calendar path gives a gap between recent and FY2010-15
    vintages that is consistent with a calendar explanation of the drift, but it cannot show one: free age and calendar
    effects absorb any linear cohort trend. The SE without the drift part (0.035) is reported as a lower bound only, and
    by_band.se_total carries the same drift part.
  - by_band ships the like-for-like table: the main estimator per band (startups excluded; raked within band to the
    acquisition book's sector, SBA Express, franchise and term-class margins; midpoint of the two- and three-class
    matches), with scale (so the table aggregates to the factor on the factor's own population) and book_tail (its
    p8-weighted mean over the FY2024-26 book, so the page sets base_cif.term = base_cif.h96 x book_tail). Its size
    profile is tested by vintage, leaving one vintage out and on FY2016. The round-2 table (the research's all-ages,
    term-mix-only construction) is kept as a cross-check. js_code is tailAt(loan), run here against the table.
  - spread.age_period_by_conditions ships 2009-11 with calendar 2009 merged into 2010 (2009 has no charge-offs, so its
    own effect is not identified).
  - note_facts: the change-of-ownership shares of notes of 96 months or less by band; "a note longer than 10 years";
    "startups excluded"; "observed through 2026-06".
  - late_hazard_by_term: each late charge-off whose original term is unknown is spread over the term classes by the
    split of late charge-offs whose term is known, given its rule-A class. Rule A errs both ways late in a loan's life,
    so both classes are allocated.
  - Replacement text for MODELS.risk.real_estate.note and the Data tab, whose "the term of charged-off loans cannot be
    separated" no longer holds: rule A separates long notes, and the book's 8-year charge-off by term class shows how
    much riskier a business-only acquisition note is.

Why
  The console's 10-year charge-off figure is pTerm = p8 x tail_factor, p8 being the change-of-ownership (CHOW) hazard
  model's cumulative charge-off at 96 months (no acquisition loan is older than 8.5 years). tail_factor = 1.1989 with
  a judgment SE of 0.0822: CIF(120)/CIF(96) of all 7(a) term loans approved FY2010-15 by loan band, weighted by the
  CHOW book's band shares (fit/sba_risk_refresh.py 3f). Term, sector, delivery method and business age were not
  matched, because "SBA does not keep the contractual TermInMonths for charged-off loans", and the tail note explains
  the band gradient (x1.07 to x1.33) as "partly because larger mature loans more often carry 25-year terms".
  The research round (/tmp/claude-0/fit6/research/G-mechanics-tail.md) found that the term can be classified after
  all and that the 25-year explanation has the sign backwards. This script consolidates its code (work/G-mechanics-
  tail/v2: tailcommon, tail_all_terms, tail_terms, tail_term3, tail_recent, agep_fy, decomp, clean_landmark,
  proportionality, run_termem's rule-A validation, overwrite_timing, transition_check, summarize) into one run from
  the raw files, and fits the factor, its SE and a band table.

What it does
  0. Sources: sha256 of every input. The 2026-06-30 FOIA files (three CSVs) and the 2023-09-30 snapshot (CSIS mirror:
     two zips and a CSV) are read with explicit types; nothing in a download is executed. Loans are matched loan by
     loan on borrower name | ZIP | approval date | gross approval (keys duplicated in either snapshot, about 1.2%, are
     not matched; match.py). The matched term-loan table is cached in cache/ under the inputs' sha256.
  1. Event coding exactly as fit/sba_risk_refresh.py 3f: term loans (RevolverStatus 0), status PIF / CHGOFF / EXEMPT,
     start = first disbursement else approval, T = months to payoff, charge-off or 2026-06-30, ev 1 = charge-off,
     2 = paid in full (competing), 0 = open; Aalen-Johansen cumulative incidence of charge-off. The CHOW book is
     sba7a_chow_loans_fy2018_2026.csv filtered as the snapshot's sba_risk_refresh.py `d` (spread over the prime in
     effect on the first business day of the approval month, 13 CFR 120.214(c), within [-2, 10] pp; rate > 0;
     term loan; PIF / CHGOFF / EXEMPT; months on book >= 0).
  2. Term classes. SBA rewrites TermInMonths of charged-off loans to R = N - E_P, the remaining term at a reference
     age about guaranty purchase. Rule A: a charged-off loan is long if R > 120 (a 20-25-year note charged off within
     10 years always shows R > 120). Two classes: business-length (N or R <= 120) / long. Three classes: <= 96 /
     97-120 / > 120 months, a charged-off loan being 120-month if R <= 120 and N = 120 is feasible (R + E >= 117).
     The two-class match leans low (mature business-length notes carry many 60/84-month notes), the three-class
     match leans high (late charge-offs of 84-month notes with long lags fall in the 120-month cell). CHOW classes from
     TermInMonths. Rule A is validated on charged-off loans whose original term is known from the 2023 snapshot.
  3. Main estimator: CIF(120)/CIF(96) of mature FY2010-15 term loans (>= 10.75 years of follow-up), startups excluded
     (CHOW loans buy existing businesses), raked (iterative proportional fitting) to the CHOW margins band, band x
     NAICS sector, band x SBA Express, band x franchise and band x term class; two-class and three-class. The
     shipped point is the midpoint of the two (rounded to 0.01). SE of each: delete-one-approval-year jackknife.
     Beside it: band only (the console's current construction), odds weights (logit of CHOW against mature membership on a
     ln-loan B-spline, sector, Express, franchise; trimmed at p99.5), all ages, startups-and-new excluded,
     business-length-only and 120-month-only subsets, recent vintages (FY2013-16, FY2014-16, FY2016 alone) and
     crisis-inclusive windows (FY2005-15, FY2001-15).
  4. Constant conditions (the console's convention: p8 holds calendar terms at their 2023-26 level): Poisson
     cause-specific hazards (charge-off, payoff) on FY2010-16 cohorts, startups excluded, by 12-month age bins with
     age x term3, age x band and band x term3 terms and calendar-year effects; CIF(96), CIF(120) per band x term3 with
     both hazards at the exposure-weighted 2023-26 calendar level, weighted to the CHOW book's band x term3 counts.
     Cluster bootstrap over approval years (B = 200). Other calendar levels for contrast. Calendar 2009 (only the
     first months of FY2010 loans) is the reference year in the research coding and its charge-off effect is not
     identified (no charge-offs); the 2023-26 level does not depend on it, and a variant merges 2009 into 2010 (the
     2009-11 level shipped). The same model along each window's own calendar path (its exposure-weighted calendar
     effects by age) gives the gap between recent (FY2013-16) and FY2010-15 vintages that the calendar path alone
     would produce. A gap that matches the realized one is consistent with a calendar explanation but does not show
     it, because free age and calendar effects absorb any linear cohort trend. The FY2005-16 version is run once to
     document why it was rejected (no cohort term: crisis cohorts load their excess onto the late ages).
  5. Transport. Ratio transport (the console's construction) assumes proportional hazards between matched mature
     loans and CHOW loans. Late-hazard (q) transport instead: tail = 1 + sum_b n_b S96_b q_b / sum_b n_b CIF96_b with
     CIF96 and S96 from the CHOW book and q = P(charge-off in months 96-120 | on the books at 96) from mature loans.
     Proportionality across vintages: ln q on ln CIF96 by approval year FY2001-16 and in band x vintage cells with
     band effects (slope 1 = proportional).
  6. SE build-up (root sum of squares): estimation (jackknife of the midpoint estimator; the age-period bootstrap
     beside it), term bracket (half the two/three-class gap), transport (ratio against q transport, all terms) and
     drift (recent FY2013-16 vintages against FY2010-15, same estimator). The shipped SE is this sum, rounded; the sum
     without the drift part is a lower bound (the jackknife carries part of the vintage spread).
  7. Band-specific tails, shipped: the main estimator per band (startups excluded, raked to class + sector + Express +
     franchise within band, midpoint of two and three classes), delete-one-vintage jackknife SEs; beside it the
     research's table (CHOW's within-band term3 mix post-stratified on FY2010-15 loans of all ages). Band centres: the
     CHOW book's geometric-mean loan in the band; tailAt interpolates linearly in ln loan size between centres, flat
     beyond the outer ones. scale = factor / (the shipped table aggregated on the factor's own population: CHOW band
     shares x the main estimator's matched mature CIF96), so the table supplies the size profile and the factor the
     level. Tests of band-specific against single (each band weighted by its share of the CHOW book's 8-year
     charge-offs), on the shipped construction and on the research table: the slope of the band ratio on ln loan in
     every vintage (t across vintages); leave-one-vintage-out within FY2010-15 and FY2016 out of time (loan bootstrap
     SEs), on the size profile (band ratio over the vintage's own aggregate, which removes the vintage-level shift both
     share) and on levels.
  8. Clean window: loans that started 2015-10 to 2016-12 (month 96 after the 2023-09-30 snapshot; years 9-10 run
     2023-10..2026-12, observed through 2026-06): q by band and term class, loan bootstrap SEs. A late charge-off's
     original term is known exactly when the 2023 snapshot still carried a standard term (not yet rewritten); the
     others are spread over short / 120-month / long by the known-term split of late charge-offs (FY2001-16 loans
     charged off after month 96 and after 2023-09-30) given their rule-A class, and the SE adds a bootstrap of that
     split. Decomposition 1 + S96 q / CIF96 by band and class.
  9. Checks: the shipped 1.1989 rebuilt with the snapshot's own formula; raking margins and Kish effective n; the
     rewrite's timing (standard-term shares by charge-off year; terms of loans open in 2023 and charged off later);
     through-the-cycle vintages FY2000-16 (the snapshot's table) and FY1991-99 from the 2023 snapshot. Real-estate
     notes: the CHOW book's 8-year charge-off (Aalen-Johansen) by sba_risk_refresh.py's loan bands and rule-A term
     class, loan bootstrap SEs, for the replacement of MODELS.risk.real_estate.note.
 10. Console: through the harness (node; the snapshot's model), p8 and the 10-year figure of $50k-$5M loans (average
     sector, no state, table rate, variable note) under the current factor, the single 1.21 and the shipped band table
     (scaled, as tailAt applies it; base_cif.term recomputed as h96 x book_tail); the tables' p8-weighted tail over the
     FY2024-26 book fixture (base_cif's population), decomposed into the book's size mix and the console's p8 profile
     by band. The shipped js_code (tailAt) runs in the probe against the shipped table.

Data and fetch (all local, read-only; raw data is not committed)
  SBA 7(a) FOIA as of 2026-06-30 (data.sba.gov/dataset/7a-504-foia):
    curl -LO https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2000_FY2009_asof_260630.csv
    (likewise FOIA_7a_FY2010_FY2019_asof_260630.csv and FOIA_7a_FY2020_Present_asof_260630.csv)
    -> /tmp/claude-0/data5/sba_foia/raw/
  SBA 7(a) FOIA as of 2023-09-30, CSISdefense/Vendor mirror (SBA no longer serves this snapshot):
    curl -LO https://raw.githubusercontent.com/CSISdefense/Vendor/HEAD/Data_Raw/Assistance/SBA/foia-7afy2020-present-asof-230930.csv
    (likewise foia-7afy2010-fy2019-asof-230930.zip, foia-7afy2000-fy2009-asof-230930.zip, foia-7afy1991-fy1999-asof-230930.zip)
    -> /tmp/claude-0/dl/sba_foia_csis/
  CHOW extract and H.15 prime (built from the 2026 files and the Fed H.15 download by /tmp/claude-0/data5/sba_foia/
    _scripts/02_extract.py and 01_prime_from_h15.py): /tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv,
    prime_rate_daily_h15.csv
  Snapshot (HEAD 56ba230, read-only): /tmp/claude-0/fit6snap/index.html (MODELS.risk, through the harness
    /tmp/claude-0/fit6/harness.js) and tests/sba_book_fy2024_26.json (the FY2024-26 book fixture).
"""
import hashlib, json, math, os, subprocess, sys, time, warnings, zipfile
from decimal import Decimal, ROUND_HALF_UP
# one BLAS thread, set before numpy loads: the GLM designs here are small (about 1,700 x 95), so threads only add
# overhead (one fit took 46 s instead of 0.3 s on a busy 4-core machine), and a fixed thread count keeps every
# floating-point result independent of the machine's core count and load
for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrix
from scipy import stats

warnings.filterwarnings('ignore')
T0 = time.time()
QUICK = '--quick' in sys.argv
REBUILD = '--rebuild' in sys.argv

# ---------------------------------------------------------------------------------------------------------------
# inputs (read-only) and outputs
# ---------------------------------------------------------------------------------------------------------------
SBA26_DIR = '/tmp/claude-0/data5/sba_foia/raw/'
SBA26 = ['FOIA_7a_FY2000_FY2009_asof_260630.csv', 'FOIA_7a_FY2010_FY2019_asof_260630.csv', 'FOIA_7a_FY2020_Present_asof_260630.csv']
SBA26_URL = 'https://data.sba.gov/sites/default/files/uploaded_resources/'
SBA23_DIR = '/tmp/claude-0/dl/sba_foia_csis/'
SBA23 = ['foia-7afy2000-fy2009-asof-230930.zip', 'foia-7afy2010-fy2019-asof-230930.zip', 'foia-7afy2020-present-asof-230930.csv']
SBA23_90S = 'foia-7afy1991-fy1999-asof-230930.zip'
SBA23_URL = 'https://raw.githubusercontent.com/CSISdefense/Vendor/HEAD/Data_Raw/Assistance/SBA/'
CHOW = '/tmp/claude-0/data5/sba_foia/clean/sba7a_chow_loans_fy2018_2026.csv'
PRIME = '/tmp/claude-0/data5/sba_foia/clean/prime_rate_daily_h15.csv'
SNAP = '/tmp/claude-0/fit6snap/'
SNAP_HTML = SNAP + 'index.html'
BOOK = SNAP + 'tests/sba_book_fy2024_26.json'
HARNESS = '/tmp/claude-0/fit6/harness.js'
SCRIPT = '/tmp/claude-0/fit6/fitscripts/sba_tail_factor.py'
OUT = '/tmp/claude-0/fit6/work/fit3-sba_tail_factor/quick/' if QUICK else '/tmp/claude-0/fit6/out/sba_tail_factor/'
CACHE = '/tmp/claude-0/fit6/out/sba_tail_factor/cache/'
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)
LOG = open(OUT + 'run.log', 'w')

ASOF = pd.Timestamp('2026-06-30')
ASOF23 = pd.Timestamp('2023-09-30')
MPD = 30.4375                                    # days per month
BANDS = [0, 1.5e5, 3.5e5, 7.5e5, 1.5e6, 1e12]
BLAB = ['<150k', '150-350k', '350-750k', '0.75-1.5M', '>=1.5M']
STD = [60, 84, 120, 180, 240, 300]              # standard original terms
SECT_MAP = {'31': 'mfg', '32': 'mfg', '33': 'mfg', '44': 'retail', '45': 'retail', '48': 'transp', '49': 'transp'}
SECT_KEEP = ['11', '23', '42', '51', '52', '53', '54', '56', '61', '62', '71', '72', '81']
B_AP = 20 if QUICK else 200                     # age-period cluster bootstrap draws
B_LAND = 20 if QUICK else 200                   # clean-window loan bootstrap draws
SEED_AP = 20261014                              # the research's seeds
SEED_LAND = 7
SEED_SPLIT = 8                                  # bootstrap of the known-term split (clean-window allocation)
SEED_RE = 9                                     # bootstrap of the real-estate-note ratios
# the analyst's decisions for this fit (shipped values): factor 1.21 and its SE 0.06, the like-for-like root sum of squares
# of the measured parts rounded (checked below against the parts recomputed here)
DECISION = {'factor': 1.21, 'factor_se': 0.06}
CURRENT = {'tail_factor': 1.1989, 'tail_factor_se': 0.0822,
           'tail_by_band': {'<150k': 1.0706, '150-350k': 1.1121, '350-750k': 1.1919, '0.75-1.5M': 1.2883, '>=1.5M': 1.3306}}
CACHE_VERSION = 'loans_matched v1: 2026 FOIA term loans (PIF/CHGOFF/EXEMPT) + 2023 term and status by name|zip|date|amount'
# sba_risk_refresh.py's loan bands and standard-term list for MODELS.risk.real_estate (its note is rebuilt in section 10e)
LBANDS = [('<250K', 0, 2.5e5), ('250-500K', 2.5e5, 5e5), ('500K-1M', 5e5, 1e6), ('1-2M', 1e6, 2e6), ('2-5M', 2e6, 5e6 + 1)]
STD_RE = [84, 120, 180, 240, 300]
# js_code: the body of tailAt(loan) for fitRisk (loan = fitRisk's clamped note amount). It is run in the node probe
# (section 11) against the shipped table, so what ships is what was tested.
JS_CODE = """/* tailAt(loan): the years 9-10 multiplier for a note of this size (loan = fitRisk's clamped note amount).
   Reads MODELS.risk.tail.by_band: the like-for-like band table, linear in ln loan between the band centres, flat beyond
   the outer centres, times scale (which ties the table's level to tail.factor).
   In fitRisk: const pTerm = p8 * tailAt(loan);  and set base_cif.term = base_cif.h96 * MODELS.risk.tail.by_band.book_tail
   so rel = pTerm / base_cif.term still averages 1 over the FY2024-26 book. */
const B=MODELS.risk.tail.by_band, x=Math.log(Math.max(loan,1)), c=B.centres.map(Math.log), v=B.ratio, n=c.length;
let r;
if(x<=c[0]) r=v[0];
else if(x>=c[n-1]) r=v[n-1];
else { let j=1; while(x>c[j]) j++; r=v[j-1]+(v[j]-v[j-1])*(x-c[j-1])/(c[j]-c[j-1]); }
return B.scale*r;"""


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n'); LOG.flush()


def r4(x):
    return None if x is None or not np.isfinite(x) else float(round(float(x), 4))


def half_up(x, nd=2):
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def clean(o, nd=6):
    """JSON-safe copy with floats rounded to nd decimals (byte-stable output)."""
    if isinstance(o, dict):
        return {str(k): clean(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v, nd) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(round(float(o), nd))
    return o


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# 0. sources
# ---------------------------------------------------------------------------------------------------------------
say('== 0. sources (sha256)')
SHA = {}
for p in [SBA26_DIR + f for f in SBA26] + [SBA23_DIR + f for f in SBA23 + [SBA23_90S]] + [CHOW, PRIME, SNAP_HTML, BOOK, HARNESS]:
    SHA[p] = sha256(p)
    say('  %s %s' % (SHA[p][:16], p))


# ---------------------------------------------------------------------------------------------------------------
# 1. loan-level table: 2026 snapshot matched to the 2023 snapshot (cached)
# ---------------------------------------------------------------------------------------------------------------
COLS26 = ['ApprovalFY', 'ApprovalDate', 'FirstDisbursementDate', 'LoanStatus', 'PaidInFullDate', 'ChargeOffDate', 'GrossApproval',
          'BusinessAge', 'RevolverStatus', 'TermInMonths', 'NaicsCode', 'BorrName', 'BorrZip', 'FranchiseCode', 'ProcessingMethod']
DATES = ['ApprovalDate', 'FirstDisbursementDate', 'PaidInFullDate', 'ChargeOffDate']
KEEP = ['ApprovalFY', 'ApprovalDate', 'FirstDisbursementDate', 'LoanStatus', 'PaidInFullDate', 'ChargeOffDate', 'GrossApproval',
        'BusinessAge', 'TermInMonths', 'NaicsCode', 'FranchiseCode', 'ProcessingMethod', 'TermInMonths_23', 'LoanStatus_23', 'matched']


def match_key(df):
    """match.py: upper-cased alphanumeric borrower name | 5-digit ZIP | approval date | gross approval (whole dollars)"""
    nm = df.BorrName.fillna('').str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
    z = df.BorrZip.fillna('').astype(str).str.extract(r'(\d{1,5})')[0].fillna('').str.zfill(5)
    return (nm + '|' + z + '|' + df.ApprovalDate.dt.strftime('%Y%m%d').fillna('') + '|'
            + df.GrossApproval.round(0).astype('Int64').astype(str))


def build_loans():
    meta = {'rows_2026': {}, 'rows_2023': {}}
    fr = []
    for f in SBA26:
        x = pd.read_csv(SBA26_DIR + f, usecols=COLS26, encoding='latin-1', low_memory=False,
                        dtype={'NaicsCode': str, 'BorrZip': str, 'FranchiseCode': str, 'BorrName': str, 'BusinessAge': str,
                               'ProcessingMethod': str, 'RevolverStatus': str, 'LoanStatus': str})
        meta['rows_2026'][f] = int(len(x)); fr.append(x)
        say('  read %s %s' % (f, x.shape))
    A = pd.concat(fr, ignore_index=True); del fr
    A['LoanStatus'] = A.LoanStatus.astype(str).str.replace(' ', '')
    A['rev'] = A.RevolverStatus.astype(str).str.upper().map({'Y': 1, 'N': 0, '1': 1, '0': 0})
    for c in DATES:
        A[c] = pd.to_datetime(A[c], format='%Y-%m-%d', errors='coerce')
    fr = []
    cols23 = ['BorrName', 'BorrZip', 'GrossApproval', 'ApprovalDate', 'TermInMonths', 'LoanStatus']
    dt23 = {'BorrName': str, 'BorrZip': str, 'LoanStatus': str}
    for f in SBA23:
        if f.endswith('.zip'):
            z = zipfile.ZipFile(SBA23_DIR + f)
            with z.open(z.namelist()[0]) as fh:
                x = pd.read_csv(fh, usecols=cols23, encoding='latin-1', low_memory=False, dtype=dt23)
        else:
            x = pd.read_csv(SBA23_DIR + f, usecols=cols23, encoding='latin-1', low_memory=False, dtype=dt23)
        meta['rows_2023'][f] = int(len(x)); fr.append(x)
        say('  read %s %s' % (f, x.shape))
    B = pd.concat(fr, ignore_index=True); del fr
    B['ApprovalDate'] = pd.to_datetime(B.ApprovalDate, format='%m/%d/%Y', errors='coerce')
    B['LoanStatus'] = B.LoanStatus.astype(str).str.replace(' ', '')
    A['k'] = match_key(A); B['k'] = match_key(B)
    dupA = A.duplicated('k', keep=False); dupB = B.duplicated('k', keep=False)
    meta['dup_share_2026'] = float(dupA.mean()); meta['dup_share_2023'] = float(dupB.mean())
    Bu = B.loc[~dupB, ['k', 'TermInMonths', 'LoanStatus']].rename(columns={'TermInMonths': 'TermInMonths_23', 'LoanStatus': 'LoanStatus_23'})
    M = A.merge(Bu, on='k', how='left')
    assert len(M) == len(A)
    M.loc[dupA.values, ['TermInMonths_23', 'LoanStatus_23']] = np.nan
    M['matched'] = M.TermInMonths_23.notna() | M.LoanStatus_23.notna()
    mr = M[M.ApprovalFY <= 2023].groupby('ApprovalFY').matched.mean()
    meta['match_rate_by_fy'] = {int(k): float(v) for k, v in mr.items()}
    L = M.loc[(M.rev == 0) & M.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']), KEEP].reset_index(drop=True)
    meta['n_term_loans_resolved_or_open'] = int(len(L))
    return L, meta


cache_tag = hashlib.sha256((CACHE_VERSION + '|' + '|'.join(SHA[SBA26_DIR + f] for f in SBA26) + '|'
                            + '|'.join(SHA[SBA23_DIR + f] for f in SBA23)).encode()).hexdigest()[:16]
CPKL, CMETA = CACHE + 'loans_matched.pkl', CACHE + 'loans_matched.meta.json'
say('\n== 1. loan-level table (cache tag %s)' % cache_tag)
use_cache = (not REBUILD) and os.path.exists(CPKL) and os.path.exists(CMETA) and json.load(open(CMETA)).get('tag') == cache_tag
if use_cache:
    L = pd.read_pickle(CPKL)                    # written by this script from the raw files (see the meta file's tag)
    LMETA = json.load(open(CMETA))['meta']
    say('  cache hit: %s (%d rows)' % (CPKL, len(L)))
else:
    L, LMETA = build_loans()
    if not QUICK or not os.path.exists(CPKL):
        L.to_pickle(CPKL)
        json.dump({'tag': cache_tag, 'version': CACHE_VERSION, 'meta': LMETA,
                   'inputs': {p: SHA[p] for p in [SBA26_DIR + f for f in SBA26] + [SBA23_DIR + f for f in SBA23]}},
                  open(CMETA, 'w'), indent=1)
    say('  built from the raw files: %d term loans; cached at %s' % (len(L), CPKL))
say('  rows 2026 %s; rows 2023 %s; duplicate keys %.4f / %.4f' % (LMETA['rows_2026'], LMETA['rows_2023'], LMETA['dup_share_2026'], LMETA['dup_share_2023']))
say('  match rate FY2005-23: %.3f-%.3f; FY2000-04: %.3f-%.3f' % (
    min(v for k, v in LMETA['match_rate_by_fy'].items() if int(k) >= 2005), max(v for k, v in LMETA['match_rate_by_fy'].items() if int(k) >= 2005),
    min(v for k, v in LMETA['match_rate_by_fy'].items() if int(k) < 2005), max(v for k, v in LMETA['match_rate_by_fy'].items() if int(k) < 2005)))


# ---------------------------------------------------------------------------------------------------------------
# shared code (tailcommon.py)
# ---------------------------------------------------------------------------------------------------------------
def sector(n):
    n2 = str(n)[:2]
    return SECT_MAP.get(n2, n2 if n2 in SECT_KEEP else 'oth')


def bage(s):
    s = str(s)
    if s.startswith('Startup'):
        return 'startup'
    if s.startswith('New'):
        return 'new'          # 'New, Less than 1 Year old' (FY2005-17) / 'New Business or 2 years or less'
    if s.startswith('Existing') or s.startswith('Less than'):
        return 'existing'
    if 'Change of Ownership' in s:
        return 'chow'
    return 'unknown'


def add_keys(df):
    b = df.band.astype(str)
    df['k_band'] = b.values
    df['k_bs'] = (b + '|' + df.sect.astype(str)).values
    df['k_be'] = (b + '|' + df.express.astype(str)).values
    df['k_bf'] = (b + '|' + df.franchise.astype(str)).values
    df['k_bc'] = (b + '|' + df.cls.astype(str)).values
    df['k_bt'] = (b + '|' + df.t3.astype(str)).values
    return df


def prep_mature(fy_lo, fy_hi):
    m = L[L.ApprovalFY.between(fy_lo, fy_hi)].copy()
    m['start'] = m.FirstDisbursementDate.fillna(m.ApprovalDate)
    endd = m.PaidInFullDate.where(m.LoanStatus == 'PIF', m.ChargeOffDate.where(m.LoanStatus == 'CHGOFF', ASOF))
    m['T'] = (endd - m.start).dt.days / MPD
    m = m[m['T'] >= 0].copy()
    m['ev'] = m.LoanStatus.map({'EXEMPT': 0, 'CHGOFF': 1, 'PIF': 2}).astype(int)
    m['band'] = pd.cut(m.GrossApproval, BANDS, right=False, labels=BLAB).astype(str)
    m['E'] = np.where(m.ev == 1, (m.ChargeOffDate - m.start).dt.days / MPD, np.nan)
    m['R'] = m.TermInMonths
    m['sect'] = m.NaicsCode.fillna('').map(sector)
    m['bage'] = m.BusinessAge.map(bage)
    m['express'] = (m.ProcessingMethod == 'SBA Express Program').astype(int)
    fc = m.FranchiseCode.fillna('').astype(str).str.strip()
    m['franchise'] = (~fc.isin(['', '0', '00000', '0.0'])).astype(int)
    m['lnamt'] = np.log(m.GrossApproval)
    co = (m.ev == 1).values; R = m.R.values; E = m.E.values
    # two classes (rule A): business-length if the recorded term (N, or R for a charged-off loan) <= 120
    m['cls'] = np.where(R <= 120, 'BL', 'LONG')
    # three classes: charged-off 120-month if R <= 120 and N = 120 is feasible (R + E >= 117)
    with np.errstate(invalid='ignore'):
        m['t3'] = np.where(co, np.where(R > 120, 'long', np.where(R + E >= 117, 'n120', 'short')),
                           np.where(R > 120, 'long', np.where(R >= 97, 'n120', 'short')))
        m['T2'] = np.where(co, (R <= 120) & (R + E >= 117), (R >= 97) & (R <= 120))
        m['SH'] = np.where(co, (R <= 120) & (R + E < 117), R <= 96)
    m['BL'] = m.cls.values == 'BL'
    return add_keys(m)


def waj(T, ev, w, grid):
    """weighted Aalen-Johansen cumulative incidence of cause 1 (cause 2 competing, 0 censored) at the grid points."""
    T = np.asarray(T, float); ev = np.asarray(ev); w = np.asarray(w, float)
    keep = w > 0
    T, ev, w = T[keep], ev[keep], w[keep]
    if len(T) == 0:
        return {g: float('nan') for g in grid}
    o = np.argsort(T, kind='stable'); t = T[o]; e = ev[o]; ww = w[o]
    ut, first = np.unique(t, return_index=True)
    d1 = np.add.reduceat(ww * (e == 1), first); d2 = np.add.reduceat(ww * (e == 2), first)
    atrisk = np.cumsum(ww[::-1])[::-1][first]
    with np.errstate(divide='ignore', invalid='ignore'):
        h1 = np.where(atrisk > 0, d1 / atrisk, 0.0); h = np.where(atrisk > 0, (d1 + d2) / atrisk, 0.0)
    S = np.cumprod(1 - h); Sprev = np.r_[1, S[:-1]]
    F = np.cumsum(Sprev * h1)
    out = {}
    for g in grid:
        j = np.searchsorted(ut, g, side='right') - 1
        out[g] = float(F[j]) if (j >= 0 and ut.max() >= g) else float('nan')
    return out


def ratio(df, w, a=96, b=120):
    v = waj(df['T'].values, df.ev.values, w, [a, b])
    return (v[b] / v[a] if v[a] > 0 else float('nan')), v[a], v[b]


def rake(df, margins, n_iter=50, tol=1e-9):
    """iterative proportional fitting of unit weights to target margins: [(key column, {key: share})]."""
    w = np.ones(len(df))
    prepared = []
    for col, tgt in margins:
        uniq, code = np.unique(df[col].values, return_inverse=True)
        share = np.array([tgt.get(u, 0.0) for u in uniq])      # sample cells absent from the target get weight 0
        prepared.append((code, share, len(uniq)))
    for it in range(n_iter):
        maxdev = 0.0
        for code, share, nk in prepared:
            cur = np.bincount(code, weights=w, minlength=nk) / w.sum()
            f = np.where(cur > 0, share / np.where(cur > 0, cur, 1), 0.0)
            maxdev = max(maxdev, float(np.max(np.abs(cur - share)[cur > 0])) if (cur > 0).any() else 0.0)
            w = w * f[code]
        if maxdev < tol:
            break
    return w / w.sum() * len(w)


def jackknife(df, fn, key='ApprovalFY'):
    """delete-one-cluster jackknife over approval years: (estimate, se, {cluster: leave-out estimate})."""
    est = fn(df)
    vs = sorted(df[key].unique())
    reps = np.array([fn(df[df[key] != v]) for v in vs])
    k = len(vs)
    se = float(np.sqrt((k - 1) / k * np.sum((reps - reps.mean()) ** 2)))
    return float(est), se, dict(zip([int(v) for v in vs], [float(r) for r in reps]))


def poststrat(h, col, shares):
    """weights reproducing `shares` over the values of h[col] (zero for values absent from shares)."""
    w = np.zeros(len(h))
    for k, s in shares.items():
        mk = (h[col] == k).values
        if mk.sum():
            w[mk] = s / mk.sum()
    return w * len(h)


# ---------------------------------------------------------------------------------------------------------------
# 2. the CHOW book, filtered as the snapshot's fit/sba_risk_refresh.py `d`
# ---------------------------------------------------------------------------------------------------------------
say('\n== 2. CHOW book (snapshot filter)')
pr = pd.read_csv(PRIME, parse_dates=['date']).sort_values('date').reset_index(drop=True)
PR_D = pr.date.values.astype('datetime64[D]').astype(np.int64)
PR_V = pr.prime_rate_pct.values


def prime_month(days):
    """the prime in effect on the first business day of the approval month (13 CFR 120.214(c)); as sba_risk_refresh.py"""
    m1 = np.asarray(days, dtype=np.int64).astype('datetime64[D]').astype('datetime64[M]').astype('datetime64[D]').astype(np.int64)
    return PR_V[np.clip(np.searchsorted(PR_D, m1, side='left'), 0, len(PR_V) - 1)]


craw = pd.read_csv(CHOW, low_memory=False, dtype={'NaicsCode': str, 'naics2': str, 'naics4': str, 'BorrZip': str, 'FranchiseCode': str},
                   parse_dates=['ApprovalDate', 'FirstDisbursementDate', 'start_date', 'ChargeOffDate', 'PaidInFullDate'])
CHOW_ROWS = int(len(craw))
_ad = craw.ApprovalDate.values.astype('datetime64[D]').astype(np.int64)
craw['spread_month_rule'] = (craw.InitialInterestRate - prime_month(_ad)).round(4)
_base = (craw.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (craw.months_on_book >= 0) & (craw.RevolverStatus == 0)
         & craw.InitialInterestRate.gt(0))
N_CHOW_APPROVAL_DATE_PRIME = int((_base & craw.spread_over_prime.between(-2, 10)).sum())   # the research's filter
d = craw[_base & craw.spread_month_rule.between(-2, 10)].copy().reset_index(drop=True)
d['ev'] = d.LoanStatus.map({'EXEMPT': 0, 'CHGOFF': 1, 'PIF': 2}).astype(int)
_st = d.start_date.values.astype('datetime64[D]').astype(np.int64)
_C = (np.datetime64('2026-06-30', 'D').astype(np.int64) - _st) / MPD
d['T'] = np.minimum(np.maximum(d.months_on_book.values, 0.01), np.maximum(_C, 0.01))
d['band'] = pd.cut(d.GrossApproval, BANDS, right=False, labels=BLAB).astype(str)
d['sect'] = d.naics2.astype(str).map(sector)
d['express'] = (d.ProcessingMethod == 'SBA Express Program').astype(int)
d['franchise'] = d.is_franchise.astype(int)
d['lnamt'] = np.log(d.GrossApproval)
d['cls'] = np.where(d.TermInMonths <= 120, 'BL', 'LONG')
d['t3'] = np.where(d.TermInMonths > 120, 'long', np.where(d.TermInMonths >= 97, 'n120', 'short'))
d['BL'] = d.cls.values == 'BL'
d['N120'] = (d.LoanStatus != 'CHGOFF') & d.TermInMonths.between(97, 120)
d = add_keys(d)
N_CHOW = int(len(d))
say('  CHOW rows %d; hazard sample %d (month-start prime; the research used the approval-date prime: %d)' % (CHOW_ROWS, N_CHOW, N_CHOW_APPROVAL_DATE_PRIME))


def shares(df, col):
    v = df[col].value_counts(normalize=True)
    return {str(k): float(s) for k, s in sorted(v.items())}


TGT = {c: shares(d, c) for c in ['k_band', 'k_bs', 'k_be', 'k_bf', 'k_bc', 'k_bt']}
MARG_2 = [('k_band', TGT['k_band']), ('k_bs', TGT['k_bs']), ('k_be', TGT['k_be']), ('k_bf', TGT['k_bf']), ('k_bc', TGT['k_bc'])]
MARG_3 = [('k_band', TGT['k_band']), ('k_bt', TGT['k_bt']), ('k_bs', TGT['k_bs']), ('k_be', TGT['k_be']), ('k_bf', TGT['k_bf'])]
CHOW_PROFILE = {
    'n': N_CHOW, 'band_share': {b: TGT['k_band'].get(b, 0.0) for b in BLAB},
    'express_share': float(d.express.mean()), 'franchise_share': float(d.franchise.mean()),
    'term_120_exactly_nonCO': float((d.TermInMonths[d.ev != 1] == 120).mean()),
    'term_le_120_nonCO': float((d.TermInMonths[d.ev != 1] <= 120).mean()),
    'term_ge_240_nonCO': float((d.TermInMonths[d.ev != 1] >= 240).mean()),
    'band_t3_mix': {b: shares(d[d.band == b], 't3') for b in BLAB},
    # contractual terms (loans not charged off; a charged-off loan's term is rewritten): notes of 96 months or less, by band
    'term_le96_nonCO': {b: float((d.TermInMonths[(d.band == b) & (d.ev != 1)] <= 96).mean()) for b in BLAB},
    'term_60_96_nonCO': {b: float(d.TermInMonths[(d.band == b) & (d.ev != 1)].between(60, 96).mean()) for b in BLAB},
    'term_60_or_84_nonCO': {b: float(d.TermInMonths[(d.band == b) & (d.ev != 1)].isin([60, 84]).mean()) for b in BLAB},
    'centre_geomean': {b: float(np.exp(d.lnamt[d.band == b].mean())) for b in BLAB},
    'centre_median': {b: float(d.GrossApproval[d.band == b].median()) for b in BLAB}}
say('  band shares %s; Express %.3f; franchise %.3f' % ({k: float(round(v, 4)) for k, v in CHOW_PROFILE['band_share'].items()},
                                                        CHOW_PROFILE['express_share'], CHOW_PROFILE['franchise_share']))


# ---------------------------------------------------------------------------------------------------------------
# 3. CHOW-matched CIF(120)/CIF(96) of mature loans
# ---------------------------------------------------------------------------------------------------------------
say('\n== 3. CHOW-matched ratios')
W_BAND = lambda h: poststrat(h, 'k_band', TGT['k_band'])
W_2 = lambda h: rake(h, MARG_2)
W_3 = lambda h: rake(h, MARG_3)
W_BC = lambda h: rake(h, [('k_band', TGT['k_band']), ('k_bc', TGT['k_bc'])])
W_BT = lambda h: rake(h, [('k_band', TGT['k_band']), ('k_bt', TGT['k_bt'])])


def odds_weights(g, trim=0.995):
    X = pd.concat([d[['lnamt', 'sect', 'express', 'franchise']].assign(y=1), g[['lnamt', 'sect', 'express', 'franchise']].assign(y=0)],
                  ignore_index=True)
    B = dmatrix('bs(lnamt, df=6, include_intercept=False)', X, return_type='dataframe')
    D = pd.get_dummies(X.sect, prefix='s', drop_first=True, dtype=float)
    Z = pd.concat([B, D, X[['express', 'franchise']].astype(float)], axis=1)
    fit = sm.GLM(X.y.values, Z.values, family=sm.families.Binomial()).fit()
    p = fit.predict(Z.values[len(d):])
    w = p / (1 - p)
    w = np.minimum(w, np.quantile(w, trim))
    return w / w.mean()


def spec(H, wf, name, vint=True):
    est, se, loo = jackknife(H, lambda x: ratio(x, wf(x))[0]) if H.ApprovalFY.nunique() > 1 else (ratio(H, wf(H))[0], float('nan'), {})
    r, c96, c120 = ratio(H, wf(H))
    out = {'ratio': r, 'se_jk': se, 'cif96': c96, 'cif120': c120, 'n': int(len(H)), 'chgoff': int((H.ev == 1).sum()),
           'chgoff_96_120': int(((H.ev == 1) & (H['T'] > 96) & (H['T'] <= 120)).sum()), 'jk_leave_out': loo}
    if vint and H.ApprovalFY.nunique() > 1:
        byv = {int(v): ratio(H[H.ApprovalFY == v], wf(H[H.ApprovalFY == v]))[0] for v in sorted(H.ApprovalFY.unique())}
        vv = np.array(list(byv.values()))
        out.update({'by_vintage': byv, 'vintage_min': float(vv.min()), 'vintage_max': float(vv.max()), 'vintage_sd': float(vv.std(ddof=1)),
                    'se_predictive': float(math.sqrt(se ** 2 + vv.std(ddof=1) ** 2))})
    say('  %-78s %.4f (jk %.4f)%s n %d' % (name, r, se, (' vint %.3f-%.3f' % (out['vintage_min'], out['vintage_max'])) if 'by_vintage' in out else '', len(H)))
    return out


M10 = prep_mature(2010, 2015)
M10x = M10[M10.bage != 'startup']
M10xn = M10[~M10.bage.isin(['startup', 'new'])]
SPEC = {}
SPEC['all ages | band only (the console\'s current construction)'] = spec(M10, W_BAND, 'FY2010-15 all ages | band only')
SPEC['all ages | band x 2-class'] = spec(M10, W_BC, 'FY2010-15 all ages | band x 2-class')
SPEC['all ages | band x 3-class'] = spec(M10, W_BT, 'FY2010-15 all ages | band x 3-class')
SPEC['all ages | 2-class + sector + Express + franchise'] = spec(M10, W_2, 'FY2010-15 all ages | 2-class + sector + Express + franchise')
SPEC['all ages | 3-class + sector + Express + franchise'] = spec(M10, W_3, 'FY2010-15 all ages | 3-class + sector + Express + franchise')
SPEC['excl. startups | band only'] = spec(M10x, W_BAND, 'FY2010-15 excl. startups | band only')
SPEC['excl. startups | 2-class + sector + Express + franchise'] = spec(M10x, W_2, 'FY2010-15 excl. startups | 2-class + sector + Express + franchise')
SPEC['excl. startups | 3-class + sector + Express + franchise'] = spec(M10x, W_3, 'FY2010-15 excl. startups | 3-class + sector + Express + franchise')
SPEC['excl. startups | odds weights'] = spec(M10x, odds_weights, 'FY2010-15 excl. startups | odds weights (ln-loan spline, sector, Express, franchise)')
SPEC['excl. startups and new | 2-class + sector + Express + franchise'] = spec(M10xn, W_2, 'FY2010-15 excl. startups and new | 2-class + full')
SPEC['excl. startups and new | 3-class + sector + Express + franchise'] = spec(M10xn, W_3, 'FY2010-15 excl. startups and new | 3-class + full')
_mbl = [('k_band', shares(d[d.BL], 'k_band')), ('k_bs', shares(d[d.BL], 'k_bs')), ('k_be', shares(d[d.BL], 'k_be')), ('k_bf', shares(d[d.BL], 'k_bf'))]
_m120 = [('k_band', shares(d[d.N120], 'k_band')), ('k_bs', shares(d[d.N120], 'k_bs')), ('k_be', shares(d[d.N120], 'k_be')), ('k_bf', shares(d[d.N120], 'k_bf'))]
SPEC['excl. startups | business-length only, band + sector + Express + franchise'] = spec(M10x[M10x.BL], lambda h: rake(h, _mbl), 'FY2010-15 excl. startups | business-length only')
SPEC['excl. startups | 120-month notes only, band + sector + Express + franchise'] = spec(M10x[M10x.T2], lambda h: rake(h, _m120), 'FY2010-15 excl. startups | 120-month notes only (T2)')
S2 = SPEC['excl. startups | 2-class + sector + Express + franchise']
S3 = SPEC['excl. startups | 3-class + sector + Express + franchise']
MID = 0.5 * (S2['ratio'] + S3['ratio'])
_, MID_SE, _ = jackknife(M10x, lambda x: 0.5 * (ratio(x, W_2(x))[0] + ratio(x, W_3(x))[0]))
MID_BYV = {v: 0.5 * (S2['by_vintage'][v] + S3['by_vintage'][v]) for v in S2['by_vintage']}
say('  midpoint of the two- and three-class matches: %.4f (jackknife SE %.4f); single vintages %s' % (MID, MID_SE, {k: float(round(v, 3)) for k, v in MID_BYV.items()}))

# raking diagnostics: margins reproduced, Kish effective sample
RAKE_DIAG = {}
for nm, mg in [('2-class + sector + Express + franchise', MARG_2), ('3-class + sector + Express + franchise', MARG_3)]:
    w = rake(M10x, mg, n_iter=200)
    dev = 0.0
    for col, tgt in mg:
        got = pd.Series(w).groupby(M10x[col].values).sum() / w.sum()
        dev = max(dev, max(abs(float(got.get(k, 0.0)) - v) for k, v in tgt.items()))
    RAKE_DIAG[nm] = {'max_abs_margin_dev': dev, 'kish_n': float(w.sum() ** 2 / (w ** 2).sum()), 'n': int(len(w)),
                     'max_weight_over_mean': float(w.max() / w.mean()),
                     'express_share': float((w * M10x.express.values).sum() / w.sum()), 'franchise_share': float((w * M10x.franchise.values).sum() / w.sum())}
    say('  raking %s: max |margin dev| %.2e, Kish n %.0f of %d, max weight %.1f x mean' % (nm, dev, RAKE_DIAG[nm]['kish_n'], len(w), RAKE_DIAG[nm]['max_weight_over_mean']))

# other windows (startups excluded)
say('  -- other windows')
WIN = {}
for wn, lo, hi in [('FY2013-16', 2013, 2016), ('FY2014-16', 2014, 2016), ('FY2016', 2016, 2016)]:
    A_ = prep_mature(lo, hi); A_ = A_[A_.bage != 'startup']
    WIN[wn] = {'2-class + sector + Express + franchise': spec(A_, W_2, '%s excl. startups | 2-class + full' % wn),
               '3-class + sector + Express + franchise': spec(A_, W_3, '%s excl. startups | 3-class + full' % wn),
               'at_risk_120': int((A_['T'] >= 120).sum())}
    WIN[wn]['midpoint'] = 0.5 * (WIN[wn]['2-class + sector + Express + franchise']['ratio'] + WIN[wn]['3-class + sector + Express + franchise']['ratio'])
for wn, lo, hi in [('FY2005-15', 2005, 2015), ('FY2001-15', 2001, 2015)]:
    A_ = prep_mature(lo, hi); A_ = A_[A_.bage != 'startup']
    WIN[wn] = {'band only': spec(A_, W_BAND, '%s excl. startups | band only' % wn),
               '2-class + sector + Express + franchise': spec(A_, W_2, '%s excl. startups | 2-class + full' % wn)}
    if wn == 'FY2005-15':
        WIN[wn]['3-class + sector + Express + franchise'] = spec(A_, W_3, '%s excl. startups | 3-class + full' % wn)
    del A_


# ---------------------------------------------------------------------------------------------------------------
# 4. age-period hazards at constant calendar conditions (agep_fy.py)
# ---------------------------------------------------------------------------------------------------------------
say('\n== 4. age-period hazards (constant calendar conditions)')
W_CELLS = d.groupby(['band', 't3']).size()
LEVELS = {'2023-26': [2023, 2024, 2025, 2026], '2017-19': [2017, 2018, 2019], '2020-22 (CARES relief)': [2020, 2021, 2022],
          '2012-16': [2012, 2013, 2014, 2015, 2016], '2009-11 (post-crisis)': [2009, 2010, 2011]}


def ap_cells(A):
    t0 = ((A.start - pd.Timestamp('2000-01-01')).dt.days / 365.25).values
    Ty = np.minimum(A['T'].values, 120.0) / 12.0
    ev = A.ev.values; Tm = A['T'].values
    rows = []
    for a in range(10):
        seg = np.clip(Ty - a, 0, 1)
        m = seg > 0
        s0 = t0[m] + a; y0 = np.floor(s0); l1 = np.minimum(seg[m], y0 + 1 - s0); l2 = seg[m] - l1
        base = pd.DataFrame({'fy': A.ApprovalFY.values[m], 'band': A.band.values[m], 't3': A.t3.values[m], 'age': a})
        rows.append(base.assign(cal=(2000 + y0).astype(int), expo=l1, co=0.0, pif=0.0))
        rows.append(base.assign(cal=(2000 + y0 + 1).astype(int), expo=l2, co=0.0, pif=0.0))
    evm = (ev > 0) & (Tm <= 120)
    ae = np.minimum(np.floor(Tm[evm] / 12), 9).astype(int); ye = (2000 + np.floor(t0[evm] + Tm[evm] / 12)).astype(int)
    rows.append(pd.DataFrame({'fy': A.ApprovalFY.values[evm], 'band': A.band.values[evm], 't3': A.t3.values[evm], 'age': ae,
                              'cal': ye, 'expo': 0.0, 'co': (ev[evm] == 1).astype(float), 'pif': (ev[evm] == 2).astype(float)}))
    X = pd.concat(rows, ignore_index=True)
    cells = X.groupby(['fy', 'band', 't3', 'age', 'cal'], as_index=False)[['expo', 'co', 'pif']].sum()
    cells = cells[cells.expo > 0].copy()
    cells['cal'] = cells.cal.clip(upper=2026)
    return cells.reset_index(drop=True)


def ap_design(df, cal_levels):
    cols = {}
    for t in ['short', 'n120', 'long']:
        for a in range(10):
            cols['a%d_%s' % (a, t)] = ((df.age == a) & (df.t3 == t)).astype(float).values
    for b in BLAB[1:]:
        for a in range(10):
            cols['a%d_%s' % (a, b)] = ((df.age == a) & (df.band == b)).astype(float).values
        for t in ['n120', 'long']:
            cols['%s_%s' % (b, t)] = ((df.band == b) & (df.t3 == t)).astype(float).values
    for c in cal_levels[1:]:
        cols['c%d' % c] = (df.cal == c).astype(float).values
    return pd.DataFrame(cols, index=df.index)


def ap_fit(cl, merge_first_year=False):
    agg = cl.groupby(['band', 't3', 'age', 'cal'], as_index=False)[['expo', 'co', 'pif']].sum()
    if merge_first_year:
        c0 = int(agg.cal.min())
        agg['cal'] = np.where(agg.cal == c0, c0 + 1, agg.cal)
        agg = agg.groupby(['band', 't3', 'age', 'cal'], as_index=False)[['expo', 'co', 'pif']].sum()
    cals = sorted(agg.cal.unique())
    D = ap_design(agg, cals)
    keep = D.columns[D.sum(0) > 0]
    D = D[keep]
    par = {}
    for k in ['co', 'pif']:
        g = sm.GLM(agg[k].values, D.values, family=sm.families.Poisson(), offset=np.log(agg.expo.values)).fit(maxiter=200)
        par[k] = pd.Series(g.params, index=keep)
    w_cal = agg.groupby('cal').expo.sum()
    ev_cal = agg.groupby('cal')[['co', 'pif']].sum()
    return par, cals, w_cal, ev_cal


def ap_cif(par, cal_eff, band, t3):
    S = 1.0; F = 0.0; F96 = None
    for a in range(10):
        lam = {}
        for k in ['co', 'pif']:
            p = par[k]
            x = p.get('a%d_%s' % (a, t3), np.nan)
            if band != BLAB[0]:
                x += p.get('a%d_%s' % (a, band), 0.0)
                if t3 != 'short':
                    x += p.get('%s_%s' % (band, t3), 0.0)
            lam[k] = np.exp(x + cal_eff[k])
        tot = lam['co'] + lam['pif']
        F += S * lam['co'] / tot * (1 - np.exp(-tot))
        S *= np.exp(-tot)
        if a == 7:
            F96 = F
    return F96, F


def ap_level(par, cals, w_cal, yrs):
    ce = {}
    for k in ['co', 'pif']:
        eff = np.array([0.0 if c == cals[0] else par[k].get('c%d' % c, 0.0) for c in yrs])
        ww = np.array([w_cal.get(c, 0.0) for c in yrs])
        ce[k] = float(np.sum(eff * ww) / ww.sum())
    return ce


def ap_tails(par, cals, w_cal, levels, sel=None):
    res = {}
    for nm, yrs in levels.items():
        ce = ap_level(par, cals, w_cal, yrs)
        num = den = 0.0; per = {}
        for (b, t), n in W_CELLS.items():
            f96, f120 = ap_cif(par, ce, b, t)
            per['%s|%s' % (b, t)] = [f96, f120, f120 / f96]
            if sel is None or t in sel:
                num += n * f120; den += n * f96
        res[nm] = {'tail': num / den, 'cells': per}
    return res


AP_A = prep_mature(2010, 2016); AP_A = AP_A[AP_A.bage != 'startup']
AP_CELLS = ap_cells(AP_A)
AP_N = {'loans': int(len(AP_A)), 'cells': int(len(AP_CELLS)), 'chgoff_by_120': float(AP_CELLS.co.sum()), 'pif_by_120': float(AP_CELLS.pif.sum())}
par, cals, w_cal, ev_cal = ap_fit(AP_CELLS)
AP = ap_tails(par, cals, w_cal, LEVELS)
AP_SUB = {nm: ap_tails(par, cals, w_cal, {'2023-26': LEVELS['2023-26']}, sel)['2023-26']['tail']
          for nm, sel in [('business-length (short + 120-month)', ['short', 'n120']), ('120-month only', ['n120']), ('long only', ['long'])]}
AP_CAL0 = {'year': int(cals[0]), 'exposure_loan_years': float(w_cal.get(cals[0], 0.0)), 'chgoff': float(ev_cal.co.get(cals[0], 0.0)),
           'payoffs': float(ev_cal.pif.get(cals[0], 0.0)), 'co_effect_other_years_mean': float(np.mean([par['co'].get('c%d' % c, 0.0) for c in cals[1:]]))}
par_m, cals_m, w_cal_m, _ = ap_fit(AP_CELLS, merge_first_year=True)
AP_MERGED = {k: v['tail'] for k, v in ap_tails(par_m, cals_m, w_cal_m, LEVELS).items()}
say('  FY2010-16 cohorts: %s; cells %d; tails %s' % (AP_N, len(AP_CELLS), {k: float(round(v['tail'], 4)) for k, v in AP.items()}))
say('  subsets at 2023-26 %s' % {k: float(round(v, 4)) for k, v in AP_SUB.items()})
say('  reference calendar year %s; with it merged into the next year: %s' % (AP_CAL0, {k: float(round(v, 4)) for k, v in AP_MERGED.items()}))
# along each window's own calendar path: the model's age-specific calendar effects averaged over that window's exposure.
# A path gap that matches the realized difference between windows is consistent with a calendar explanation of the
# recent vintages' excess, but does not show it: with free age and calendar effects and no cohort term, any linear
# cohort trend is absorbed into the age and calendar effects, so a cohort drift would be reproduced the same way.
def ap_tail_path(par, cals, fy_set):
    G = AP_CELLS[AP_CELLS.fy.isin(fy_set)]
    ce = {k: [] for k in ['co', 'pif']}
    for a in range(10):
        g = G[G.age == a].groupby('cal').expo.sum()
        for k in ['co', 'pif']:
            eff = np.array([0.0 if c == cals[0] else par[k].get('c%d' % c, 0.0) for c in g.index])
            ce[k].append(float((eff * g.values).sum() / g.values.sum()))
    num = den = 0.0
    for (b, t), n in W_CELLS.items():
        S = 1.0; F = 0.0; F96 = None
        for a in range(10):
            lam = {}
            for k in ['co', 'pif']:
                p_ = par[k]
                x = p_.get('a%d_%s' % (a, t), np.nan)
                if b != BLAB[0]:
                    x += p_.get('a%d_%s' % (a, b), 0.0)
                    if t != 'short':
                        x += p_.get('%s_%s' % (b, t), 0.0)
                lam[k] = np.exp(x + ce[k][a])
            tot = lam['co'] + lam['pif']
            F += S * lam['co'] / tot * (1 - np.exp(-tot)); S *= np.exp(-tot)
            if a == 7:
                F96 = F
        num += n * F; den += n * F96
    return num / den


AP_PATH = {'FY2010-15': ap_tail_path(par, cals, list(range(2010, 2016))), 'FY2013-16': ap_tail_path(par, cals, list(range(2013, 2017))),
           'FY2010-12': ap_tail_path(par, cals, [2010, 2011, 2012]), 'FY2016': ap_tail_path(par, cals, [2016])}
AP_PATH['FY2013-16 minus FY2010-15'] = AP_PATH['FY2013-16'] - AP_PATH['FY2010-15']
say('  tails along each window\'s own calendar path (age-period model, CHOW band x term3 weights): %s' % {k: float(round(v, 4)) for k, v in AP_PATH.items()})
rng = np.random.default_rng(SEED_AP)
fys = sorted(AP_CELLS.fy.unique())
boot = {k: [] for k in LEVELS}
by_fy = {f: AP_CELLS[AP_CELLS.fy == f] for f in fys}
AP_BOOT_FAIL = 0
for i in range(B_AP):
    pick = rng.choice(fys, len(fys), replace=True)
    cl = pd.concat([by_fy[f] for f in pick], ignore_index=True)
    try:
        p2, c2, w2, _ = ap_fit(cl)
        t2 = ap_tails(p2, c2, w2, LEVELS)
        for k in LEVELS:
            boot[k].append(t2[k]['tail'])
    except Exception as e:                       # a draw without some cell; recorded, not silently dropped
        AP_BOOT_FAIL += 1
        for k in LEVELS:
            boot[k].append(float('nan'))
AP_SE = {k: float(np.nanstd(np.array(v, float), ddof=1)) for k, v in boot.items()}
AP_CI = {k: [float(np.nanpercentile(np.array(v, float), 2.5)), float(np.nanpercentile(np.array(v, float), 97.5))] for k, v in boot.items()}
say('  cluster bootstrap over approval years (B=%d): SE %s; 95%% %s' % (B_AP, {k: float(round(v, 4)) for k, v in AP_SE.items()},
                                                                        {k: [round(x, 4) for x in v] for k, v in AP_CI.items()}))
del by_fy
# rejected: FY2005-16 cohorts (no cohort term; crisis cohorts load their excess onto the late ages)
_A05 = prep_mature(2005, 2016); _A05 = _A05[_A05.bage != 'startup']
_p05, _c05, _w05, _ = ap_fit(ap_cells(_A05))
AP_FY05 = {k: v['tail'] for k, v in ap_tails(_p05, _c05, _w05, LEVELS).items()}
AP_FY05_N = int(len(_A05))
say('  rejected FY2005-16 version (n %d): %s' % (AP_FY05_N, {k: float(round(v, 4)) for k, v in AP_FY05.items()}))
del _A05, _p05


# ---------------------------------------------------------------------------------------------------------------
# 5. decomposition and transport (decomp.py, summarize.py)
# ---------------------------------------------------------------------------------------------------------------
say('\n== 5. decomposition 1 + S96 q / CIF96 and q transport')


def parts(h, grid=(60, 84, 96, 120)):
    T = h['T'].values; ev = h.ev.values; w = np.ones(len(h))
    c = waj(T, ev, w, list(grid))
    p = waj(T, np.where(ev == 2, 1, np.where(ev == 1, 2, 0)), w, list(grid))
    out = {'n': int(len(h))}
    for t in grid:
        out['cif%d' % t] = c[t]; out['pif%d' % t] = p[t]
    out['S96'] = 1 - c[96] - p[96]
    if 120 in grid and np.isfinite(c[120]):
        out['q'] = (c[120] - c[96]) / out['S96'] if out['S96'] > 0 else float('nan')
        out['ratio'] = c[120] / c[96]
    return out


POPS_M = [('all', None), ('business-length', 'BL'), ('120-month T2', 'T2'), ('short <=96', 'SH'), ('long', 'LONG')]
M10['LONG'] = ~M10.BL.values
DEC = {}
for b in BLAB + ['all bands']:
    g = M10 if b == 'all bands' else M10[M10.band == b]
    row = {}
    for pn, col in POPS_M:
        h = g if col is None else g[g[col].values]
        x = parts(h)
        _, se_q, _ = jackknife(h, lambda z: parts(z, (96, 120))['q'])
        x['q_se_jk'] = se_q
        row[pn] = x
    DEC[b] = row
d['T2c'] = np.where(d.ev == 1, d.TermInMonths <= 120, d.TermInMonths.between(97, 120))
DECC = {}
for b in BLAB + ['all bands']:
    g = d if b == 'all bands' else d[d.band == b]
    row = {}
    for pn, h in [('all', g), ('business-length', g[g.BL]), ('120-month', g[g.T2c]), ('long', g[~g.BL])]:
        x = parts(h, (60, 84, 96))
        x['at_risk_96'] = int((h['T'] >= 96).sum()); x['at_risk_84'] = int((h['T'] >= 84).sum())
        row[pn] = x
    DECC[b] = row
QT = {}
for cm, cc in [('all', 'all'), ('business-length', 'business-length'), ('120-month T2', '120-month'), ('long', 'long')]:
    num = den = numr = 0.0; per = {}
    for b in BLAB:
        m = DEC[b][cm]; c = DECC[b][cc]; wb = c['n']
        inc = c['S96'] * m['q']
        num += wb * inc; den += wb * c['cif96']; numr += wb * c['cif96'] * m['ratio']
        per[b] = {'chow_cif96': c['cif96'], 'chow_S96': c['S96'], 'mature_q': m['q'], 'mature_ratio': m['ratio'],
                  'band_tail_q_transport': 1 + inc / c['cif96']}
    QT[cc] = {'tail_q_transport': 1 + num / den, 'tail_ratio_transport_same_weights': numr / den, 'by_band': per}
say('  q transport: %s' % {k: (float(round(v['tail_q_transport'], 4)), float(round(v['tail_ratio_transport_same_weights'], 4))) for k, v in QT.items()})
say('  CHOW at month 96: CIF %.4f, S96 %.3f, at risk %d; 120-month notes CIF96 %.4f' % (
    DECC['all bands']['all']['cif96'], DECC['all bands']['all']['S96'], DECC['all bands']['all']['at_risk_96'], DECC['all bands']['120-month']['cif96']))


# ---------------------------------------------------------------------------------------------------------------
# 6. SE build-up
# ---------------------------------------------------------------------------------------------------------------
REC_MID = WIN['FY2013-16']['midpoint']
SE_PARTS = {'estimation': MID_SE, 'term_bracket': abs(S3['ratio'] - S2['ratio']) / 2,
            'transport': abs(QT['all']['tail_q_transport'] - QT['all']['tail_ratio_transport_same_weights']),
            'drift': abs(REC_MID - MID)}
SE_TOTAL = math.sqrt(sum(v ** 2 for v in SE_PARTS.values()))
SE_RESEARCH_ROUNDED = math.sqrt(0.025 ** 2 + 0.01 ** 2 + 0.02 ** 2 + 0.04 ** 2)
# the SE without the drift part is a lower bound, not an alternative: the jackknife carries part of the vintage spread,
# and the age-period calendar path is only consistent with a calendar explanation of the drift (see section 4)
NO_DRIFT = 'no drift part (lower bound: the jackknife carries part of the vintage spread)'
SE_LOWER = math.sqrt(SE_PARTS['estimation'] ** 2 + SE_PARTS['term_bracket'] ** 2 + SE_PARTS['transport'] ** 2)
SE_ALT = {'estimation = age-period bootstrap': math.sqrt(AP_SE['2023-26'] ** 2 + SE_PARTS['term_bracket'] ** 2 + SE_PARTS['transport'] ** 2 + SE_PARTS['drift'] ** 2),
          'drift = lower recent match minus the midpoint': math.sqrt(SE_PARTS['estimation'] ** 2 + SE_PARTS['term_bracket'] ** 2 + SE_PARTS['transport'] ** 2
                                                                      + (WIN['FY2013-16']['2-class + sector + Express + franchise']['ratio'] - MID) ** 2),
          'drift = recent midpoint minus the age-period estimate': math.sqrt(SE_PARTS['estimation'] ** 2 + SE_PARTS['term_bracket'] ** 2 + SE_PARTS['transport'] ** 2
                                                                              + (REC_MID - AP['2023-26']['tail']) ** 2),
          'research rounded parts (0.025, 0.01, 0.02, 0.04)': SE_RESEARCH_ROUNDED,
          NO_DRIFT: SE_LOWER}
FACTOR_SE = half_up(SE_TOTAL)                   # shipped: the like-for-like sum of the measured parts, rounded
assert FACTOR_SE == DECISION['factor_se'], 'the measured parts round to %.2f, not the decided %.2f' % (FACTOR_SE, DECISION['factor_se'])
say('\n== 6. SE build-up: %s -> %.4f, shipped %.2f (research rounded parts %.4f); lower bound without the drift part %.4f; alternatives %s' % (
    {k: round(v, 4) for k, v in SE_PARTS.items()}, SE_TOTAL, FACTOR_SE, SE_RESEARCH_ROUNDED, SE_LOWER, {k: round(v, 4) for k, v in SE_ALT.items()}))


# ---------------------------------------------------------------------------------------------------------------
# 7. band-specific tails, and band-specific against single out of sample
# ---------------------------------------------------------------------------------------------------------------
say('\n== 7. band-specific tails')
BT_MIX = {b: shares(d[d.band == b], 't3') for b in BLAB}


def band_ratio_t3(g, b):
    return ratio(g, poststrat(g, 't3', BT_MIX[b]))


# the research's table (FY2010-15, all ages, CHOW within-band term3 mix only): round 2 shipped it; kept as a cross-check
BAND = {}
for b in BLAB:
    g = M10[M10.band == b]
    est, se, loo = jackknife(g, lambda x, b=b: band_ratio_t3(x, b)[0])
    r, c96, c120 = band_ratio_t3(g, b)
    byv = {int(v): band_ratio_t3(g[g.ApprovalFY == v], b)[0] for v in sorted(g.ApprovalFY.unique())}
    BAND[b] = {'ratio': r, 'se_jk': se, 'cif96': c96, 'cif120': c120, 'n': int(len(g)), 'chgoff': int((g.ev == 1).sum()),
               'by_vintage': byv, 'chow_t3_mix': BT_MIX[b], 'unmatched_ratio': ratio(g, np.ones(len(g)))[0]}
# the shipped table: the factor's own estimator in each band (startups excluded; class + sector + Express + franchise
# raked within band to the CHOW book's margins; midpoint of the two- and three-class matches)
MARGB = {}
for b in BLAB:
    db = d[d.band == b]
    MARGB[b] = ([('k_bs', shares(db, 'k_bs')), ('k_be', shares(db, 'k_be')), ('k_bf', shares(db, 'k_bf')), ('k_bc', shares(db, 'k_bc'))],
                [('k_bt', shares(db, 'k_bt')), ('k_bs', shares(db, 'k_bs')), ('k_be', shares(db, 'k_be')), ('k_bf', shares(db, 'k_bf'))])


def band_main(g, b):
    """the main estimator in one band: midpoint of the two- and three-class ratios, with the mean of their CIF96 and CIF120"""
    r2, a2, c2 = ratio(g, rake(g, MARGB[b][0]))
    r3, a3, c3 = ratio(g, rake(g, MARGB[b][1]))
    return 0.5 * (r2 + r3), 0.5 * (a2 + a3), 0.5 * (c2 + c3)


BAND_MAIN = {}
for b in BLAB:
    g = M10x[M10x.band == b]
    f2 = lambda x, b=b: ratio(x, rake(x, MARGB[b][0]))[0]
    f3 = lambda x, b=b: ratio(x, rake(x, MARGB[b][1]))[0]
    e2, s2, _ = jackknife(g, f2); e3, s3, _ = jackknife(g, f3)
    _, smid, _ = jackknife(g, lambda x, f2=f2, f3=f3: 0.5 * (f2(x) + f3(x)))
    _m, c96, c120 = band_main(g, b)
    BAND_MAIN[b] = {'two_class': e2, 'two_class_se': s2, 'three_class': e3, 'three_class_se': s3, 'midpoint': 0.5 * (e2 + e3), 'midpoint_se': smid,
                    'term_bracket': abs(e3 - e2) / 2, 'cif96': c96, 'cif120': c120, 'n': int(len(g)), 'chgoff': int((g.ev == 1).sum()),
                    'chgoff_96_120': int(((g.ev == 1) & (g['T'] > 96) & (g['T'] <= 120)).sum())}
    assert abs(_m - BAND_MAIN[b]['midpoint']) < 1e-12
for b in BLAB:
    say('  %-10s shipped (main estimator) 2-class %.4f, 3-class %.4f, midpoint %.4f (jk %.4f; CIF96 %.4f) | research table %.4f (jk %.4f; unmatched %.4f; CHOW t3 mix %s)' % (
        b, BAND_MAIN[b]['two_class'], BAND_MAIN[b]['three_class'], BAND_MAIN[b]['midpoint'], BAND_MAIN[b]['midpoint_se'], BAND_MAIN[b]['cif96'],
        BAND[b]['ratio'], BAND[b]['se_jk'], BAND[b]['unmatched_ratio'], {k: round(v, 3) for k, v in BAND[b]['chow_t3_mix'].items()}))
CENTRES = [CHOW_PROFILE['centre_geomean'][b] for b in BLAB]
CENTRES_R = [float(round(c, -3)) for c in CENTRES]
BAND_R = [half_up(BAND_MAIN[b]['midpoint'], 3) for b in BLAB]
BAND_SE_R = [half_up(BAND_MAIN[b]['midpoint_se'], 3) for b in BLAB]
# se_total: the band's own jackknife plus the factor SE's term-bracket, transport and drift parts, so the bands carry the
# same drift treatment as the factor
COMMON_SE = math.sqrt(SE_PARTS['term_bracket'] ** 2 + SE_PARTS['transport'] ** 2 + SE_PARTS['drift'] ** 2)
BAND_SE_TOTAL = [half_up(math.sqrt(BAND_MAIN[b]['midpoint_se'] ** 2 + COMMON_SE ** 2), 3) for b in BLAB]


def band_diff(hi, lo):
    """band hi minus band lo (main estimator) with its delete-one-vintage jackknife SE (the two bands share vintages)"""
    G = M10x[M10x.band.isin([hi, lo])]
    est, se, _ = jackknife(G, lambda x: band_main(x[x.band == hi], hi)[0] - band_main(x[x.band == lo], lo)[0])
    return est, se


GRAD, GRAD_SE = band_diff(BLAB[-1], BLAB[0])
GRAD_Z = GRAD / GRAD_SE
TOP_DIP, TOP_DIP_SE = band_diff(BLAB[-1], BLAB[-2])
GRAD_RT = BAND[BLAB[-1]]['ratio'] - BAND[BLAB[0]]['ratio']
GRAD_RT_Z = GRAD_RT / math.sqrt(BAND[BLAB[-1]]['se_jk'] ** 2 + BAND[BLAB[0]]['se_jk'] ** 2)


def tail_interp(loan, centres, vals):
    return float(np.interp(np.log(loan), np.log(centres), vals))


# out of sample: held-out vintage band ratios against (a) the other vintages' band ratios and (b) their single factor
# (the same estimator aggregated over bands with CHOW band shares). Each band carries its share of the CHOW book's
# 8-year charge-offs (band share x CHOW CIF96 of the band). Run on the shipped construction (startups excluded, main
# estimator; FY2016 out of time likewise) and on the research table (all ages).
OMEGA = np.array([CHOW_PROFILE['band_share'][b] * DECC[b]['all']['cif96'] for b in BLAB]); OMEGA = OMEGA / OMEGA.sum()
_sh = np.array([CHOW_PROFILE['band_share'][b] for b in BLAB])


def band_and_single(G):
    """research construction: band ratios (CHOW term3 mix within band) and their CHOW-mix aggregate"""
    v = np.array([band_ratio_t3(G[G.band == b], b) for b in BLAB])
    rb, c96, c120 = v[:, 0], v[:, 1], v[:, 2]
    return rb, float((_sh * c120).sum() / (_sh * c96).sum())


def band_and_single_main(G):
    """shipped construction: band ratios (main estimator) and their aggregate on the CHOW band mix with the sample's own
    matched CIF96 (that sample's single factor)"""
    v = np.array([band_main(G[G.band == b], b) for b in BLAB])
    rb, c96 = v[:, 0], v[:, 1]
    return rb, float((_sh * c96 * rb).sum() / (_sh * c96).sum())


LNC = np.log(CENTRES)


def wslope(y, x=LNC, w=OMEGA):
    xm = (w * x).sum() / w.sum(); ym = (w * y).sum() / w.sum()
    return float((w * (x - xm) * (y - ym)).sum() / (w * (x - xm) ** 2).sum())


def oos_tests(Mtr, Moot, fn, seed):
    """the size-profile tests of one construction: leave-one-vintage-out on levels and on the profile (band ratio over the
    vintage's own aggregate, which removes the vintage-level shift both predictions share), FY2016 out of time, and the
    slope of the band ratio on ln loan by vintage (t across vintages; FY2016 with a loan-bootstrap SE)"""
    vints = sorted(int(v) for v in Mtr.ApprovalFY.unique())
    byv = {v: fn(Mtr[Mtr.ApprovalFY == v]) for v in vints}
    lovo, prof = [], []
    for v in vints:
        rb_tr, s_tr = fn(Mtr[Mtr.ApprovalFY != v]); rb_te, s_te = byv[v]
        lb = float((OMEGA * (rb_te - rb_tr) ** 2).sum()); ls = float((OMEGA * (rb_te - s_tr) ** 2).sum())
        lovo.append({'held_out': v, 'loss_band': lb, 'loss_single': ls, 'band_better': lb < ls, 'single_train': s_tr, 'held_out_band_ratios': rb_te.tolist()})
        lb = float((OMEGA * (rb_te / s_te - rb_tr / s_tr) ** 2).sum()); ls = float((OMEGA * (rb_te / s_te - 1) ** 2).sum())
        prof.append({'held_out': v, 'loss_band': lb, 'loss_single': ls, 'band_better': lb < ls})
    rb_all, s_all = fn(Mtr); rb16, s16 = fn(Moot)
    oot = {'band_pred': rb_all.tolist(), 'single_pred': s_all, 'fy2016_band_ratios': rb16.tolist(), 'fy2016_single': s16,
           'loss_band': float((OMEGA * (rb16 - rb_all) ** 2).sum()), 'loss_single': float((OMEGA * (rb16 - s_all) ** 2).sum()),
           'at_risk_120': int((Moot['T'] >= 120).sum())}
    lovo_sum = {'vintages_band_better': int(sum(x['band_better'] for x in lovo)), 'vintages': len(lovo),
                'rmse_band': math.sqrt(float(np.mean([x['loss_band'] for x in lovo]))), 'rmse_single': math.sqrt(float(np.mean([x['loss_single'] for x in lovo]))),
                'fy2016_rmse_band': math.sqrt(oot['loss_band']), 'fy2016_rmse_single': math.sqrt(oot['loss_single'])}
    prof_sum = {'vintages_band_better': int(sum(x['band_better'] for x in prof)), 'vintages': len(prof),
                'rmse_band': math.sqrt(float(np.mean([x['loss_band'] for x in prof]))), 'rmse_single': math.sqrt(float(np.mean([x['loss_single'] for x in prof]))),
                'fy2016_rmse_band': math.sqrt(float((OMEGA * (rb16 / s16 - rb_all / s_all) ** 2).sum())),
                'fy2016_rmse_single': math.sqrt(float((OMEGA * (rb16 / s16 - 1) ** 2).sum()))}
    slopes = {v: wslope(byv[v][0]) for v in vints}
    sv = np.array(list(slopes.values()))
    slope = {'pooled': wslope(rb_all), 'by_vintage': slopes, 'mean': float(sv.mean()), 'se_between_vintages': float(sv.std(ddof=1) / math.sqrt(len(sv))),
             'positive_vintages': int((sv > 0).sum()), 'vintages': len(sv)}
    slope['t'] = slope['mean'] / slope['se_between_vintages']
    slope['p_two_sided_t'] = float(2 * stats.t.sf(abs(slope['t']), len(sv) - 1))
    rng_ = np.random.default_rng(seed)
    gb = {b: Moot[Moot.band == b] for b in BLAB}
    boot = []
    for _ in range(B_LAND):
        sub = pd.concat([gb[b].iloc[rng_.integers(0, len(gb[b]), len(gb[b]))] for b in BLAB])
        boot.append(fn(sub)[0])
    boot = np.array(boot)
    slope['fy2016'] = wslope(rb16)
    slope['fy2016_se_boot'] = float(np.nanstd([wslope(r) for r in boot], ddof=1))
    oot['band_se_boot'] = np.nanstd(boot, axis=0, ddof=1).tolist()
    return {'band_ratios': rb_all.tolist(), 'single': s_all, 'by_vintage': {v: x[0].tolist() for v, x in byv.items()},
            'single_by_vintage': {v: x[1] for v, x in byv.items()}, 'lovo': lovo, 'lovo_summary': lovo_sum, 'profile': prof,
            'profile_summary': prof_sum, 'fy2016_out_of_time': oot, 'slope': slope}


M16 = prep_mature(2016, 2016)
M16x = M16[M16.bage != 'startup']
OOS = oos_tests(M10x, M16x, band_and_single_main, SEED_LAND)       # the shipped construction
OOS_RT = oos_tests(M10, M16, band_and_single, SEED_LAND)           # the research table (round 2's construction)
for nm, o in [('shipped (main estimator, startups excluded)', OOS), ('research table (all ages, term mix only)', OOS_RT)]:
    s_, p_, l_, t_ = o['slope'], o['profile_summary'], o['lovo_summary'], o['fy2016_out_of_time']
    say('  %s: slope per ln loan pooled %.4f, by vintage %s (positive %d of %d; t %.2f, p %.4f); FY2016 %.4f (boot SE %.4f)' % (
        nm, s_['pooled'], {k: round(v, 3) for k, v in s_['by_vintage'].items()}, s_['positive_vintages'], s_['vintages'], s_['t'], s_['p_two_sided_t'],
        s_['fy2016'], s_['fy2016_se_boot']))
    say('    size profile, leave-one-vintage-out: band better in %d of %d, RMSE %.4f vs %.4f; FY2016 %.4f vs %.4f | levels: %d of %d, RMSE %.4f vs %.4f; FY2016 %.4f vs %.4f; FY2016 band ratios %s (boot SE %s)' % (
        p_['vintages_band_better'], p_['vintages'], p_['rmse_band'], p_['rmse_single'], p_['fy2016_rmse_band'], p_['fy2016_rmse_single'],
        l_['vintages_band_better'], l_['vintages'], l_['rmse_band'], l_['rmse_single'], l_['fy2016_rmse_band'], l_['fy2016_rmse_single'],
        np.round(t_['fy2016_band_ratios'], 3).tolist(), np.round(t_['band_se_boot'], 3).tolist()))
say('  shipped construction: top minus bottom %.4f (jackknife SE %.4f, z %.1f); top minus next %.4f (SE %.4f) | research table: top minus bottom %.3f (z %.1f)' % (
    GRAD, GRAD_SE, GRAD_Z, TOP_DIP, TOP_DIP_SE, GRAD_RT, GRAD_RT_Z))
# the tables aggregated on the CHOW FY2018-26 band mix three ways: with the main estimator's matched mature CIF96 (the factor's own
# population: the band composition of the raked estimator the factor is), with the research table's all-ages CIF96 (round 2's
# scale used it) and with the CHOW book's own Aalen-Johansen CIF96
_wl = _sh * np.array([BAND_MAIN[b]['cif96'] for b in BLAB])
_wm = _sh * np.array([BAND[b]['cif96'] for b in BLAB])
_wc = _sh * np.array([DECC[b]['all']['cif96'] for b in BLAB])
_agg = lambda w, t: float((w * np.asarray(t, float)).sum() / w.sum())
BAND_AGG = {nm: {'factor_population': _agg(_wl, t), 'research_cif96_weights': _agg(_wm, t), 'chow_aj_cif96_weights': _agg(_wc, t)}
            for nm, t in [('shipped table (3 dp)', BAND_R), ('main estimator per band (unrounded)', [BAND_MAIN[b]['midpoint'] for b in BLAB]),
                          ('research table', [BAND[b]['ratio'] for b in BLAB])]}
# scale: the shipped table times KAPPA aggregates to the shipped factor on the factor's own population, so the band profile carries
# no level of its own. The unrounded table composes there to (about) the factor's unrounded midpoint, so KAPPA mostly carries the
# rounding of the factor to 0.01 and of the table to 0.001.
KAPPA = half_up(DECISION['factor'] / BAND_AGG['shipped table (3 dp)']['factor_population'], 4)
say('  band tables aggregated (factor population / research CIF96 / CHOW CIF96 weights): %s; factor midpoint %.4f; scale for the shipped table %.4f' % (
    {k: {kk: float(round(vv, 4)) for kk, vv in v.items()} for k, v in BAND_AGG.items()}, MID, KAPPA))


# ---------------------------------------------------------------------------------------------------------------
# 8. clean window: late hazard by term class (clean_landmark.py); unknown terms allocated by the known-term split
# ---------------------------------------------------------------------------------------------------------------
say('\n== 8. clean window (loans started 2015-10..2016-12; years 9-10 run 2023-10..2026-12, observed through 2026-06)')
CW = prep_mature(2015, 2017)
CW = CW[(CW.start >= '2015-10-01') & (CW.start <= '2016-12-31')].copy()
alive = CW[CW['T'] > 96].copy()
co_ = (alive.ev == 1).values
std23 = (alive.TermInMonths_23.isin(STD) & (alive.LoanStatus_23 == 'EXEMPT')).values
Rx = np.where(alive.TermInMonths_23.notna(), alive.TermInMonths_23, alive.R)
N_co = np.where(std23, alive.TermInMonths_23, np.nan)
alive['N'] = np.where(co_, N_co, alive.R)
fin = np.isfinite(alive.N.values)
alive['ccls'] = np.where(fin, np.where(alive.N <= 120, 'BL', np.where(alive.N >= 240, 'RE', 'MID')), np.where(Rx > 120, 'long?', 'BL?'))
alive['bl'] = np.where(fin, alive.N <= 120, Rx <= 120)
alive['n120c'] = np.where(fin, (alive.N >= 97) & (alive.N <= 120), Rx <= 120)
alive['T2l'] = alive['T'] - 96
CLEAN = {'cohort_n': int(len(CW)), 'alive_at_96': int(len(alive)), 'late_co': int(co_.sum()),
         'late_co_class_known_exactly': int((co_ & std23).sum()),
         'late_co_by_class': {str(k): int(v) for k, v in sorted(alive[co_].ccls.value_counts().items())}}


def q_late(h, horizon=24):
    return waj(h['T2l'].values, h.ev.values, np.ones(len(h)), [horizon])[horizon]


# rule-A classes as they stand (round 2): a late charge-off whose original term is unknown is classed by its rewritten
# term alone, so all of them with a rewritten term of 120 months or less fall in the 120-month class
CROWS = {}
for b in BLAB + ['all']:
    g = alive if b == 'all' else alive[alive.band == b]
    a = CW if b == 'all' else CW[CW.band == b]
    full = waj(a['T'].values, a.ev.values, np.ones(len(a)), [96])
    row = {'n_alive': int(len(g)), 'cif96_cohort': full[96], 'share_alive_96': len(g) / max(len(a), 1)}
    for cn, sel in [('all', np.ones(len(g), bool)), ('business-length (N<=120)', g.bl.values), ('long (N>120)', ~g.bl.values.astype(bool)),
                    ('120-month (N 97-120)', g.n120c.values.astype(bool) & g.bl.values.astype(bool)), ('real-estate (N>=240, exact)', (g.ccls == 'RE').values)]:
        h = g[sel]
        if len(h) < 30:
            continue
        rng_l = np.random.default_rng(SEED_LAND)
        qs = [q_late(h.iloc[rng_l.integers(0, len(h), len(h))]) for _ in range(B_LAND)]
        row[cn] = {'n': int(len(h)), 'late_co': int((h.ev == 1).sum()), 'q': q_late(h), 'q_se': float(np.nanstd(qs))}
    CROWS[b] = row
CLEAN['by_band'] = CROWS

# 8b. allocation of late charge-offs whose original term is unknown (the reviewer's asymmetry: they all went to the 120-month
# class while the short notes still on the books at month 96 were left out of it). Rule A errs both ways this late in a loan's
# life (some long notes show a rewritten term of 120 or less; some 120-month notes show one over 120), so each unknown-term
# charge-off is spread over short / 120-month / long by the split of late charge-offs whose original term is known, given
# their rule-A class: FY2001-16 term loans charged off after month 96 and after 2023-09-30 whose 2023 term was still a standard
# term (rule A read off the rewritten 2026 term). Both classes are allocated; allocating only the business-length one would
# leave the 120-month notes among the rule-A long charge-offs out of the 120-month class.
P01 = prep_mature(2001, 2016)                   # FY2001-16 term loans: the known-term split here, section 9 and rule A (10b)
_v = P01[(P01.ev == 1).values]
_v = _v[np.isfinite(_v.E) & np.isfinite(_v.R)]
_kl = ((_v.ChargeOffDate > ASOF23) & (_v.LoanStatus_23 == 'EXEMPT') & _v.TermInMonths_23.isin(STD) & (_v.E > 96)).values
_t23 = _v.TermInMonths_23.values[_kl]
SPLIT_TRUE = np.where(_t23 <= 96, 0, np.where(_t23 <= 120, 1, 2))     # original term: short (<= 96) / 120-month (97-120) / long (> 120)
SPLIT_A = (_v.R.values[_kl] > 120).astype(int)                        # rule A on the rewritten term: 0 business-length, 1 long
SPLIT_N = {'n': int(_kl.sum()), 'by_approval_fy': {int(k): int(c) for k, c in pd.Series(_v.ApprovalFY.values[_kl]).value_counts().sort_index().items()},
           'in_clean_window': int(np.isin(_v.index.values[_kl], CW.index.values).sum())}
del _v, _t23
TCLS = ['short', '120-month', 'long']


def split_of(a, t):
    """P(original-term class | rule-A class): rows business-length (rewritten term <= 120), long; columns short, 120-month, long"""
    cnt = np.array([[((a == k) & (t == c)).sum() for c in range(3)] for k in range(2)], float)
    return cnt / np.maximum(cnt.sum(1, keepdims=True), 1), cnt


SPLIT, SPLIT_CNT = split_of(SPLIT_A, SPLIT_TRUE)
_Nv = alive.N.values.astype(float)
_known = np.isfinite(_Nv)
with np.errstate(invalid='ignore'):
    _onehot = np.stack([_Nv <= 96, (_Nv > 96) & (_Nv <= 120), _Nv > 120], axis=1).astype(float)
_unk = co_ & ~_known                                # late charge-offs whose original term is unknown
_unkA = (np.asarray(Rx, float) > 120).astype(int)   # their rule-A class (the 2023 term when matched, else the 2026 term)
N_UNCLASSED = int((~_known & ~co_).sum())           # loans not charged off without a term (none expected)
_m23 = alive.TermInMonths_23.notna().values
UNK_KIND = {'rewritten_by_2023_09_30': int((_unk & _m23 & (alive.LoanStatus_23 == 'EXEMPT').values).sum()),
            'other_2023_status': int((_unk & _m23 & (alive.LoanStatus_23 != 'EXEMPT').values).sum()),
            'not_matched_to_2023': int((_unk & ~_m23).sum())}


def class_weights(S):
    W = np.where(_known[:, None], _onehot, 0.0)
    W[_unk] = S[_unkA[_unk]]
    return W


ALLOC_CLASSES = [('120-month', lambda W: W[:, 1]), ('long', lambda W: W[:, 2]), ('short', lambda W: W[:, 0]),
                 ('business-length', lambda W: W[:, 0] + W[:, 1])]


def q_w(h, w, horizon=24):
    return waj(h['T2l'].values, h.ev.values, w, [horizon])[horizon]


W_ALLOC = class_weights(SPLIT)
_bm = {b: (np.ones(len(alive), bool) if b == 'all' else alive.band.values == b) for b in BLAB + ['all']}
_bh = {b: alive[_bm[b]] for b in BLAB + ['all']}
ALLOC = {b: {} for b in BLAB + ['all']}
for b in BLAB + ['all']:
    h = _bh[b]; Wb = W_ALLOC[_bm[b]]; coh = (h.ev == 1).values
    for cn, f in ALLOC_CLASSES:
        w = f(Wb)
        rng_l = np.random.default_rng(SEED_LAND)
        qs = []
        for _ in range(B_LAND):
            ix = rng_l.integers(0, len(h), len(h))
            qs.append(q_w(h.iloc[ix], w[ix]))
        ALLOC[b][cn] = {'n_eff': float(w.sum()), 'late_co_eff': float(w[coh].sum()), 'q': q_w(h, w), 'se_loans': float(np.nanstd(qs))}
# the split's own uncertainty: bootstrap the known-term charge-offs, loans fixed; the two parts add in quadrature
rng_s = np.random.default_rng(SEED_SPLIT)
_sq = {(b, cn): [] for b in BLAB + ['all'] for cn, _ in ALLOC_CLASSES}
for _ in range(B_LAND):
    ix = rng_s.integers(0, len(SPLIT_A), len(SPLIT_A))
    Wj = class_weights(split_of(SPLIT_A[ix], SPLIT_TRUE[ix])[0])
    for b in BLAB + ['all']:
        Wb = Wj[_bm[b]]
        for cn, f in ALLOC_CLASSES:
            _sq[(b, cn)].append(q_w(_bh[b], f(Wb)))
for b in BLAB + ['all']:
    for cn, _ in ALLOC_CLASSES:
        x = ALLOC[b][cn]
        x['se_split'] = float(np.nanstd(_sq[(b, cn)]))
        x['q_se'] = math.sqrt(x['se_loans'] ** 2 + x['se_split'] ** 2)
# sensitivities: the rule-A classes as they stand (round 2; must reproduce CROWS) and the business-length unknowns only (spread by
# the known split among rule-A business-length charge-offs whose original term is 120 months or less; rule-A long ones stay long)
_sbl = SPLIT_CNT[0, :2] / SPLIT_CNT[0, :2].sum()
S_NONE = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
S_BLONLY = np.array([[_sbl[0], _sbl[1], 0.0], [0.0, 0.0, 1.0]])
ALLOC_SENS = {}
for nm, S in [('rule-A classes as they stand (round 2)', S_NONE), ('business-length unknowns only', S_BLONLY), ('both rule-A classes (shipped)', SPLIT)]:
    W = class_weights(S)
    ALLOC_SENS[nm] = {cn: {b: q_w(_bh[b], f(W[_bm[b]])) for b in BLAB + ['all']} for cn, f in ALLOC_CLASSES[:2]}
ALLOC_ROUND2_DIFF = max(max(abs(ALLOC_SENS['rule-A classes as they stand (round 2)']['120-month'][b] - CROWS[b]['120-month (N 97-120)']['q']) for b in BLAB + ['all']),
                        max(abs(ALLOC_SENS['rule-A classes as they stand (round 2)']['long'][b] - CROWS[b]['long (N>120)']['q']) for b in BLAB + ['all']))
del _bh
n120q = np.array([ALLOC[b]['120-month']['q'] for b in BLAB]); n120s = np.array([ALLOC[b]['120-month']['q_se'] for b in BLAB])
lngq = np.array([ALLOC[b]['long']['q'] for b in BLAB]); lngs = np.array([ALLOC[b]['long']['q_se'] for b in BLAB])
_wq = 1 / n120s ** 2; _qbar = float((_wq * n120q).sum() / _wq.sum())
FLAT = {'q_pooled_ivw': _qbar, 'chi2': float((_wq * (n120q - _qbar) ** 2).sum()), 'df': len(BLAB) - 1}
FLAT['p'] = float(stats.chi2.sf(FLAT['chi2'], FLAT['df']))
_x = np.log([CHOW_PROFILE['centre_geomean'][b] for b in BLAB])
_sl = np.polyfit(_x, n120q, 1, w=1 / n120s)
FLAT['slope_per_ln_loan'] = float(_sl[0])
CLEAN['allocation'] = {'known_late_chgoff': SPLIT_N, 'split_counts': {k: dict(zip(TCLS, SPLIT_CNT[i].tolist())) for i, k in enumerate(['rule A business-length', 'rule A long'])},
                       'split': {k: dict(zip(TCLS, SPLIT[i].tolist())) for i, k in enumerate(['rule A business-length', 'rule A long'])},
                       'unknown_in_window': {'rule A business-length': int((_unk & (_unkA == 0)).sum()), 'rule A long': int((_unk & (_unkA == 1)).sum())},
                       'unknown_kind': UNK_KIND, 'unclassed_not_charged_off': N_UNCLASSED, 'by_band': ALLOC, 'sensitivity': ALLOC_SENS, 'round2_reproduced_max_abs_diff': ALLOC_ROUND2_DIFF}
say('  alive %d, late charge-offs %d (%d with the exact term; unknown: %d rule-A business-length, %d rule-A long; %d unclassed loans not charged off)' % (
    CLEAN['alive_at_96'], CLEAN['late_co'], CLEAN['late_co_class_known_exactly'], (_unk & (_unkA == 0)).sum(), (_unk & (_unkA == 1)).sum(), N_UNCLASSED))
say('  known-term split of %d late charge-offs (FY2001-16, after month 96 and 2023-09-30) given rule A: business-length %s, long %s' % (
    SPLIT_N['n'], dict(zip(TCLS, SPLIT_CNT[0].astype(int).tolist())), dict(zip(TCLS, SPLIT_CNT[1].astype(int).tolist()))))
say('  120-month q allocated %s (SE %s: loans %s, split %s); as rule A stands %s; business-length unknowns only %s' % (
    np.round(n120q, 4).tolist(), np.round(n120s, 4).tolist(), np.round([ALLOC[b]['120-month']['se_loans'] for b in BLAB], 4).tolist(),
    np.round([ALLOC[b]['120-month']['se_split'] for b in BLAB], 4).tolist(),
    np.round([CROWS[b]['120-month (N 97-120)']['q'] for b in BLAB], 4).tolist(), np.round([ALLOC_SENS['business-length unknowns only']['120-month'][b] for b in BLAB], 4).tolist()))
say('  long q allocated %s (SE %s); as rule A stands %s; business-length class %s; flat-across-size chi2 %.2f on %d df (p %.2f); round 2 reproduced to %.1e' % (
    np.round(lngq, 4).tolist(), np.round(lngs, 4).tolist(), np.round([CROWS[b]['long (N>120)']['q'] for b in BLAB], 4).tolist(),
    np.round([ALLOC[b]['business-length']['q'] for b in BLAB], 4).tolist(), FLAT['chi2'], FLAT['df'], FLAT['p'], ALLOC_ROUND2_DIFF))


# ---------------------------------------------------------------------------------------------------------------
# 9. proportionality across vintages (proportionality.py)
# ---------------------------------------------------------------------------------------------------------------
say('\n== 9. proportionality: ln q on ln CIF96')
# P01 (FY2001-16 term loans) was built in section 8b


def lparts(h):
    T = h['T'].values; ev = h.ev.values; w = np.ones(len(h))
    c = waj(T, ev, w, [96, 120]); p = waj(T, np.where(ev == 2, 1, np.where(ev == 1, 2, 0)), w, [96])
    S96 = 1 - c[96] - p[96]
    return c[96], S96, ((c[120] - c[96]) / S96 if S96 > 0 else float('nan')), c[120] / c[96]


PROP = {}
for pop, sel in [('all terms, >=150k', lambda g: g[g.GrossApproval >= 1.5e5]), ('120-month T2, >=150k', lambda g: g[(g.GrossApproval >= 1.5e5) & g.T2]),
                 ('all terms, all sizes', lambda g: g)]:
    rows = []
    for fy, g in sel(P01).groupby('ApprovalFY'):
        c96, S96, q, r = lparts(g)
        rows.append(dict(fy=int(fy), n=len(g), cif96=c96, S96=S96, q=q, ratio=r))
    t = pd.DataFrame(rows)
    ok = t[(t.q > 0) & (t.cif96 > 0) & np.isfinite(t.q)]
    fit = sm.OLS(np.log(ok.q.values), sm.add_constant(np.log(ok.cif96.values))).fit()
    PROP[pop] = {'slope': float(fit.params[1]), 'se': float(fit.bse[1]), 'n_vintages': int(len(ok)),
                 'corr_q_cif96': float(np.corrcoef(ok.q, ok.cif96)[0, 1]), 'by_vintage': t.to_dict(orient='records')}
for pop, flag in [('cells all terms, band effects', None), ('cells 120-month T2, band effects', 'T2')]:
    rows = []
    for (b, fy), g in P01[P01.GrossApproval >= 1.5e5].groupby(['band', 'ApprovalFY']):
        h = g if flag is None else g[g[flag]]
        if len(h) < 400:
            continue
        c96, S96, q, r = lparts(h)
        rows.append(dict(band=b, fy=int(fy), n=len(h), cif96=c96, q=q))
    t = pd.DataFrame(rows)
    ok = t[(t.q > 0) & (t.cif96 > 0)]
    X = pd.get_dummies(ok.band, drop_first=True, dtype=float); X['lncif96'] = np.log(ok.cif96.values); X = sm.add_constant(X)
    fit = sm.WLS(np.log(ok.q.values), X, weights=ok.n.values).fit(cov_type='cluster', cov_kwds={'groups': ok.fy.values})
    PROP[pop] = {'slope': float(fit.params['lncif96']), 'se': float(fit.bse['lncif96']), 'n_cells': int(len(ok)), 'se_type': 'clustered by vintage'}
for k, v in PROP.items():
    say('  %-36s slope %.3f (SE %.3f)' % (k, v['slope'], v['se']))
# through the cycle: the snapshot's table (all 7(a) term loans >= $150k, any business age)
CYC = {}
for fy, g in P01[P01.GrossApproval >= 1.5e5].groupby('ApprovalFY'):
    c = waj(g['T'].values, g.ev.values, np.ones(len(g)), [96, 120])
    CYC[int(fy)] = {'n': int(len(g)), 'cif96': c[96], 'cif120': c[120], 'r120_96': c[120] / c[96]}
_P00 = prep_mature(2000, 2000); _P00 = _P00[_P00.GrossApproval >= 1.5e5]
_c = waj(_P00['T'].values, _P00.ev.values, np.ones(len(_P00)), [96, 120])
CYC[2000] = {'n': int(len(_P00)), 'cif96': _c[96], 'cif120': _c[120], 'r120_96': _c[120] / _c[96]}
CYC = dict(sorted(CYC.items()))


# ---------------------------------------------------------------------------------------------------------------
# 10. checks: the console's current construction, rule A, the rewrite, the 1990s vintages; real-estate notes
# ---------------------------------------------------------------------------------------------------------------
say('\n== 10. checks')
# 10a. the shipped 1.1989: sum_b acq_share_b CIF120_b / sum_b acq_share_b CIF96_b (by-band Aalen-Johansen), sba_risk_refresh.py 3f
SHIP_BANDS = {}
for b in BLAB:
    g = M10[M10.band == b]; v = waj(g['T'].values, g.ev.values, np.ones(len(g)), [96, 120])
    SHIP_BANDS[b] = {'n': int(len(g)), 'cif96': v[96], 'cif120': v[120], 'ratio': v[120] / v[96], 'acq_share': CHOW_PROFILE['band_share'][b]}
# the snapshot computes it from 4-decimal intermediates (tail_band values pass through r4 before the sum)
SHIP_REBUILT = (sum(round(SHIP_BANDS[b]['acq_share'], 4) * round(SHIP_BANDS[b]['cif120'], 4) for b in BLAB)
                / sum(round(SHIP_BANDS[b]['acq_share'], 4) * round(SHIP_BANDS[b]['cif96'], 4) for b in BLAB))
SHIP_REBUILT_EXACT = (sum(SHIP_BANDS[b]['acq_share'] * SHIP_BANDS[b]['cif120'] for b in BLAB) / sum(SHIP_BANDS[b]['acq_share'] * SHIP_BANDS[b]['cif96'] for b in BLAB))
say('  current construction rebuilt: %.4f with the snapshot\'s 4-decimal intermediates (console 1.1989), %.4f exact; band ratios %s' % (
    SHIP_REBUILT, SHIP_REBUILT_EXACT, {b: round(SHIP_BANDS[b]['ratio'], 4) for b in BLAB}))
# 10b. rule-A validation on charged-off loans whose original term is known from the 2023 snapshot (run_termem.py part 1)
V = P01
vco = V[V.ev == 1]
vco = vco[np.isfinite(vco.E) & np.isfinite(vco.R)]
kn = ((vco.ChargeOffDate > ASOF23) & (vco.LoanStatus_23 == 'EXEMPT') & vco.TermInMonths_23.isin(STD)).values
truth_long = vco.TermInMonths_23.values[kn] > 120
predA = vco.R.values[kn] > 120
RULEA = {'n': int(kn.sum()), 'accuracy': float((predA == truth_long).mean()), 'pred_long': float(predA.mean()), 'true_long': float(truth_long.mean()),
         'false_long': int((predA & ~truth_long).sum()), 'missed_long': int((~predA & truth_long).sum()),
         'missed_long_true_terms': {str(int(k)): int(v) for k, v in pd.Series(vco.TermInMonths_23.values[kn][~predA & truth_long]).value_counts().sort_index().items()}}
say('  rule A on %d known-term charge-offs: accuracy %.4f, predicted long %.4f vs true %.4f' % (RULEA['n'], RULEA['accuracy'], RULEA['pred_long'], RULEA['true_long']))
del V, vco, P01
# 10c. the rewrite (overwrite_timing.py, transition_check.py)
co_all = L[L.LoanStatus == 'CHGOFF'].copy()
co_all['coy'] = co_all.ChargeOffDate.dt.year
co_all['std'] = co_all.TermInMonths.isin(STD)
REWRITE = {'std_share_chgoff_by_year': {int(k): float(v) for k, v in co_all.groupby('coy')['std'].mean().items() if np.isfinite(k)},
           'chgoff_by_year_n': {int(k): int(v) for k, v in co_all.groupby('coy').size().items() if np.isfinite(k)}}
_pif = L[(L.LoanStatus == 'PIF') & L.ApprovalFY.between(2000, 2016)]
REWRITE['std_share_pif_fy2000_16'] = float(_pif.TermInMonths.isin(STD).mean())
tr = L[(L.LoanStatus == 'CHGOFF') & (L.ChargeOffDate > ASOF23) & (L.LoanStatus_23 == 'EXEMPT')].copy()
tr['nonstd23'] = ~tr.TermInMonths_23.isin(STD)
tr['q'] = tr.ChargeOffDate.dt.to_period('Q').astype(str)
REWRITE['open_2023_chgoff_later'] = {'n': int(len(tr)), 'term_unchanged_share': float((tr.TermInMonths == tr.TermInMonths_23).mean()),
                                    'nonstandard_2023_term_by_chgoff_quarter': {k: float(v) for k, v in tr.groupby('q').nonstd23.mean().items()},
                                    'n_by_quarter': {k: int(v) for k, v in tr.groupby('q').size().items()}}
_pv = L[(L.LoanStatus == 'PIF') & L.ApprovalFY.isin(tr.ApprovalFY.unique())]
REWRITE['nonstandard_share_pif_same_vintages'] = float(1 - _pv.TermInMonths.isin(STD).mean())
_y = [v for k, v in REWRITE['std_share_chgoff_by_year'].items() if 2001 <= k <= 2025]
say('  standard-term share of charge-offs 2001-25: %.3f-%.3f (PIF FY2000-16 %.3f); 2026: %.3f' % (
    min(_y), max(_y), REWRITE['std_share_pif_fy2000_16'], REWRITE['std_share_chgoff_by_year'].get(2026, float('nan'))))
say('  open at 2023-09-30, charged off later (%d): non-standard 2023 term by quarter %s; PIF benchmark %.3f' % (
    len(tr), {k: round(v, 2) for k, v in REWRITE['open_2023_chgoff_later']['nonstandard_2023_term_by_chgoff_quarter'].items()},
    REWRITE['nonstandard_share_pif_same_vintages']))
del co_all, tr, _pif, _pv
# 10d. FY1991-99 vintages from the 2023-09-30 snapshot (the critic's missed source; local, small)
z = zipfile.ZipFile(SBA23_DIR + SBA23_90S)
with z.open(z.namelist()[0]) as fh:
    N9 = pd.read_csv(fh, usecols=['ApprovalFiscalYear', 'ApprovalDate', 'FirstDisbursementDate', 'LoanStatus', 'PaidInFullDate', 'ChargeOffDate',
                                  'GrossApproval', 'RevolverStatus'], encoding='latin-1', low_memory=False, dtype={'LoanStatus': str, 'RevolverStatus': str})
N90_ROWS = int(len(N9))
N9['LoanStatus'] = N9.LoanStatus.astype(str).str.replace(' ', '')
N9['rev'] = N9.RevolverStatus.astype(str).str.upper().map({'Y': 1, 'N': 0, '1': 1, '0': 0})
for c in DATES:
    N9[c] = pd.to_datetime(N9[c], format='%m/%d/%Y', errors='coerce')
N9 = N9[N9.LoanStatus.isin(['PIF', 'CHGOFF', 'EXEMPT']) & (N9.rev == 0)].copy()
N9['start'] = N9.FirstDisbursementDate.fillna(N9.ApprovalDate)
_e = N9.PaidInFullDate.where(N9.LoanStatus == 'PIF', N9.ChargeOffDate.where(N9.LoanStatus == 'CHGOFF', ASOF23))
N9['T'] = (_e - N9.start).dt.days / MPD
N9 = N9[N9['T'] >= 0]
N9['ev'] = N9.LoanStatus.map({'EXEMPT': 0, 'CHGOFF': 1, 'PIF': 2}).astype(int)
CYC90 = {}
for fy, g in N9[N9.GrossApproval >= 1.5e5].groupby('ApprovalFiscalYear'):
    c = waj(g['T'].values, g.ev.values, np.ones(len(g)), [96, 120])
    CYC90[int(fy)] = {'n': int(len(g)), 'cif96': c[96], 'cif120': c[120], 'r120_96': c[120] / c[96],
                      'disbursement_date_share': float(g.FirstDisbursementDate.notna().mean())}
say('  FY1991-99 (2023 snapshot, >= $150k): %s' % {k: float(round(v['r120_96'], 3)) for k, v in CYC90.items()})
del N9
# 10e. real-estate notes (MODELS.risk.real_estate, display only). Its note says the business-only case cannot be separated
# because SBA does not keep the contractual term of charged-off loans; rule A (10b) now separates long notes. Rebuilt here:
# sba_risk_refresh.py's shares (terms over 120 months among paid-off and open CHOW loans, its loan bands) and its
# standard-term shares, then the CHOW book's Aalen-Johansen charge-off within 8 years by rule-A term class (a charged-off
# loan is long if its rewritten term is over 120 months), with loan-bootstrap SEs of the ratios to the band's average.
_nc = d.ev.values != 1
RE_SHARE = {nm: float((d.TermInMonths.values[_nc & (d.GrossApproval.values >= lo) & (d.GrossApproval.values < hi)] > 120).mean()) for nm, lo, hi in LBANDS}
RE_STD = {'chargeoffs': float(np.isin(d.TermInMonths.values[~_nc], STD_RE).mean()), 'others': float(np.isin(d.TermInMonths.values[_nc], STD_RE).mean())}
REAL = {}
rng_re = np.random.default_rng(SEED_RE)
for nm, lo, hi in LBANDS + [('all', 0, 1e12)]:
    gb = d[(d.GrossApproval >= lo) & (d.GrossApproval < hi)]
    Tg, eg, blg = gb['T'].values, gb.ev.values, gb.BL.values
    row = {}
    for cn, sel in [('all', np.ones(len(gb), bool)), ('business_length', blg), ('long', ~blg)]:
        c = waj(Tg[sel], eg[sel], np.ones(int(sel.sum())), [60, 96])
        row[cn] = {'n': int(sel.sum()), 'chgoff': int((eg[sel] == 1).sum()), 'cif60': c[60], 'cif96': c[96], 'at_risk_96': int((Tg[sel] >= 96).sum())}
    row['bl_over_all'] = row['business_length']['cif96'] / row['all']['cif96']
    row['long_over_all'] = row['long']['cif96'] / row['all']['cif96']
    row['bl_over_long'] = row['business_length']['cif96'] / row['long']['cif96']
    bs = []
    for _ in range(B_LAND):
        ix = rng_re.integers(0, len(gb), len(gb))
        T_, e_, b_ = Tg[ix], eg[ix], blg[ix]
        ca = waj(T_, e_, np.ones(len(ix)), [96])[96]
        bs.append([waj(T_[b_], e_[b_], np.ones(int(b_.sum())), [96])[96] / ca, waj(T_[~b_], e_[~b_], np.ones(int((~b_).sum())), [96])[96] / ca])
    bs = np.array(bs)
    row['bl_over_all_se'] = float(np.nanstd(bs[:, 0], ddof=1)); row['long_over_all_se'] = float(np.nanstd(bs[:, 1], ddof=1))
    REAL[nm] = row
say('  real-estate notes: share over 120 months (paid-off and open) %s; standard terms %s on charged-off loans against %s on others' % (
    {k: round(v, 4) for k, v in RE_SHARE.items()}, round(RE_STD['chargeoffs'], 4), round(RE_STD['others'], 4)))
say('  CHOW 8-year charge-off by rule-A term class: %s' % {k: '%.4f all, %.4f business-length (x%.2f, SE %.2f), %.4f long (x%.2f, SE %.2f)' % (
    v['all']['cif96'], v['business_length']['cif96'], v['bl_over_all'], v['bl_over_all_se'], v['long']['cif96'], v['long_over_all'], v['long_over_all_se'])
    for k, v in REAL.items()})


# ---------------------------------------------------------------------------------------------------------------
# 11. the console: p8 and the 10-year figure under each tail (node, the snapshot's model through the harness)
# ---------------------------------------------------------------------------------------------------------------
say('\n== 11. console effect (harness)')
PROBE = r"""/* written by sba_tail_factor.py: evaluates the snapshot's fitRisk under alternative tails, and runs the shipped tailAt (read-only) */
const fs=require('fs');
const H=require(process.argv[2]); const cfg=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const A=H.load(); const R=A.MODELS.risk;
const BK=JSON.parse(fs.readFileSync(cfg.book,'utf8'));
const tailAt=new Function('MODELS','loan',cfg.js_code), JM={risk:{tail:{by_band:cfg.js_by_band}}};
const avg=fn=>{const a=R.industry_effects,b=R.pif.sector;R.industry_effects={};R.pif.sector={};try{return fn();}finally{R.industry_effects=a;R.pif.sector=b;}};
const interp=(L,c,v)=>{const x=Math.log(L),lc=c.map(Math.log);if(x<=lc[0])return v[0];if(x>=lc[lc.length-1])return v[v.length-1];
  for(let j=1;j<lc.length;j++) if(x<=lc[j]) return v[j-1]+(v[j]-v[j-1])*(x-lc[j-1])/(lc[j]-lc[j-1]);};
const out={tail_factor:R.tail_factor,tail_factor_se:R.tail_factor_se,base_cif:{h60:R.base_cif.h60,h96:R.base_cif.h96,term:R.base_cif.term},
  loan_share:R.loan_share,loan_range:R.loan_range,real_estate:R.real_estate,loans:[],book:{}};
for(const L of cfg.loans){ const r=avg(()=>A.fitRisk(L/R.loan_share,'zzz',null,null,false,null));
  const row={loan:L,console_loan:r.loan,p5:r.p5,p8:r.p8,pTerm:r.pTerm,rel:r.rel,tail_js:tailAt(JM,r.loan),tails:{}};
  for(const k in cfg.tables) row.tails[k]=interp(r.loan,cfg.tables[k].centres,cfg.tables[k].ratio);
  out.loans.push(row); }
const ie=R.industry_effects, ps=R.pif.sector, n=BK.loan.length; let s8=0, sj=0; const st={}, sb={};
for(const k in cfg.tables){ st[k]=0; }
for(const b of cfg.bands) sb[b]={n:0,p8:0};
try{ for(let i=0;i<n;i++){ R.industry_effects={"81":BK.sec_co[BK.sec[i]]+BK.n6[i]/1e4}; R.pif.sector={"81":BK.sec_pif[BK.sec[i]]};
    const r=A.fitRisk(BK.loan[i]/R.loan_share,"zzz",null,null,BK.fr[i]===1,BK.st_keys[BK.st[i]]); s8+=r.p8; sj+=r.p8*tailAt(JM,r.loan);
    for(const k in cfg.tables) st[k]+=r.p8*interp(r.loan,cfg.tables[k].centres,cfg.tables[k].ratio);
    let j=0; while(j+1<cfg.edges.length&&r.loan>=cfg.edges[j+1]) j++; sb[cfg.bands[j]].n++; sb[cfg.bands[j]].p8+=r.p8; } }
finally{ R.industry_effects=ie; R.pif.sector=ps; }
out.book={n:n,mean_p8:s8/n,effective_tail:{},effective_tail_js:sj/s8,by_band:sb};
for(const k in cfg.tables) out.book.effective_tail[k]=st[k]/s8;
console.log(JSON.stringify(out));
"""
PROBE_LOANS = [5e4, 1e5, 1.5e5, 2e5, 3.5e5, 5e5, 7e5, 1e6, 1.5e6, 2e6, 3e6, 5e6]
# the round-2 shipped table (sba_tail_factor.v2.py: the research construction at 2 dp, scale 0.988, book tail 1.2224), for comparison
ROUND2 = {'ratio': [1.11, 1.13, 1.21, 1.30, 1.35], 'scale': 0.988, 'book_tail': 1.2224}
SHIP = 'shipped table (like-for-like, 3 dp)'
R2K = 'round-2 shipped table (research construction, 2 dp)'
TABLES = {SHIP: {'centres': CENTRES_R, 'ratio': BAND_R},
          'main estimator per band (unrounded)': {'centres': CENTRES, 'ratio': [BAND_MAIN[b]['midpoint'] for b in BLAB]},
          'research table (unrounded)': {'centres': CENTRES, 'ratio': [BAND[b]['ratio'] for b in BLAB]},
          R2K: {'centres': CENTRES_R, 'ratio': ROUND2['ratio']},
          'current unmatched band ratios': {'centres': CENTRES, 'ratio': [CURRENT['tail_by_band'][b] for b in BLAB]}}
JS_BY_BAND = {'centres': CENTRES_R, 'ratio': BAND_R, 'scale': KAPPA}      # what tailAt reads from MODELS.risk.tail.by_band
cfg = {'book': BOOK, 'loans': PROBE_LOANS, 'tables': TABLES, 'bands': BLAB, 'edges': BANDS[:-1], 'js_code': JS_CODE, 'js_by_band': JS_BY_BAND}
open(OUT + 'probe.js', 'w').write(PROBE)
json.dump(cfg, open(OUT + 'probe_cfg.json', 'w'), indent=1)
pr_ = subprocess.run(['node', OUT + 'probe.js', HARNESS, OUT + 'probe_cfg.json'], capture_output=True, text=True, timeout=600)
if pr_.returncode != 0:
    raise RuntimeError('node probe failed: ' + pr_.stderr[-2000:])
CON = json.loads(pr_.stdout)
assert abs(CON['tail_factor'] - CURRENT['tail_factor']) < 1e-12 and abs(CON['tail_factor_se'] - CURRENT['tail_factor_se']) < 1e-12
F_SHIP = DECISION['factor']
H96 = CON['base_cif']['h96']
EFF_TAIL = CON['book']['effective_tail']
EFF_SCALED = KAPPA * EFF_TAIL[SHIP]                 # p8-weighted mean of tailAt over the FY2024-26 book
BOOK_TAIL = r4(EFF_SCALED)
BASE_NEW = H96 * BOOK_TAIL                          # base_cif.term with band tails
# the shipped js_code, run in node against the shipped by_band, against scale x the table's interpolation
JS_DIFF = {'loans_max_abs': max(abs(row['tail_js'] - KAPPA * tail_interp(row['console_loan'], CENTRES_R, BAND_R)) for row in CON['loans']),
           'book_abs': abs(CON['book']['effective_tail_js'] - EFF_SCALED)}
REL_MEAN = CON['book']['mean_p8'] * CON['book']['effective_tail_js'] / BASE_NEW   # the book mean of rel = p8 x tailAt / base_cif.term
EFFECT = []
for row in CON['loans']:
    tb = row['tails'][SHIP]; ts = row['tail_js']; p8 = row['p8']
    assert abs(tb - tail_interp(row['console_loan'], CENTRES_R, BAND_R)) < 1e-12
    t2 = ROUND2['scale'] * row['tails'][R2K]
    EFFECT.append({'loan': row['loan'], 'console_loan': row['console_loan'], 'p8': p8, 'pTerm_current': row['pTerm'], 'rel_current': row['rel'],
                   'pTerm_single_1_21': p8 * F_SHIP, 'tail_band': tb, 'tail_band_scaled': ts, 'pTerm_band_scaled': p8 * ts, 'rel_band': p8 * ts / BASE_NEW,
                   'change_pp_band_vs_single': 100 * p8 * (ts - F_SHIP), 'change_pp_band_vs_current': 100 * (p8 * ts - row['pTerm']),
                   'change_pp_single_vs_current': 100 * p8 * (F_SHIP - CURRENT['tail_factor']), 'change_rel_band_vs_single': ts / F_SHIP - 1,
                   'tail_main_estimator_unrounded': row['tails']['main estimator per band (unrounded)'], 'tail_round2_scaled': t2,
                   'change_pp_round2_vs_single': 100 * p8 * (t2 - F_SHIP)})
BASE_TERM = {'current (h96 x 1.1989)': CON['base_cif']['term'], 'single 1.21': H96 * F_SHIP, 'band tails (h96 x book_tail)': BASE_NEW,
             'round-2 band table (h96 x 1.2224)': H96 * ROUND2['book_tail']}
# why the book's tail differs from the factor: the FY2024-26 book's band mix against the FY2018-26 CHOW mix, and the
# console's p8 by band against the CHOW book's Aalen-Johansen CIF96 by band (band-level approximation)
_bn = np.array([CON['book']['by_band'][b]['n'] for b in BLAB], float); _bp = np.array([CON['book']['by_band'][b]['p8'] for b in BLAB], float)
_bsh = _bn / _bn.sum(); _cp8 = _bp / _bn
_aj = np.array([DECC[b]['all']['cif96'] for b in BLAB])
BOOKMIX = {'book_band_share': _bsh.tolist(), 'chow_band_share': [CHOW_PROFILE['band_share'][b] for b in BLAB], 'console_mean_p8_by_band': _cp8.tolist(),
           'chow_aj_cif96_by_band': _aj.tolist()}
for nm, t in [('shipped table (3 dp)', np.array(BAND_R)), ('research table', np.array([BAND[b]['ratio'] for b in BLAB]))]:
    BOOKMIX[nm] = {'chow_mix_x_chow_aj': _agg(_sh * _aj, t), 'chow_mix_x_console_p8': _agg(_sh * _cp8, t),
                   'book_mix_x_chow_aj': _agg(_bsh * _aj, t), 'book_mix_x_console_p8': _agg(_bsh * _cp8, t)}
say('  book-mix decomposition: %s' % {k: ({kk: float(round(vv, 4)) for kk, vv in v.items()} if isinstance(v, dict) else [float(round(x, 4)) for x in v])
                                      for k, v in BOOKMIX.items()})
for e in EFFECT:
    if e['loan'] in (2e5, 7e5, 2e6):
        say('  $%-9s p8 %.4f | 10-yr: current %.4f, single 1.21 %.4f, tailAt (x%.4f) %.4f -> %+.2f pp vs single, %+.2f pp vs current (round 2: %+.2f pp vs single); rel %.3f -> %.3f' % (
            '{:,.0f}'.format(e['loan']), e['p8'], e['pTerm_current'], e['pTerm_single_1_21'], e['tail_band_scaled'], e['pTerm_band_scaled'],
            e['change_pp_band_vs_single'], e['change_pp_band_vs_current'], e['change_pp_round2_vs_single'], e['rel_current'], e['rel_band']))
say('  effective tail over the FY2024-26 book (p8-weighted): %s; tailAt %.6f (scale x table %.6f); book_tail %.4f, base_cif.term %.5f; rel mean %.4f; js max |diff| %.1e' % (
    {k: float(round(v, 4)) for k, v in EFF_TAIL.items()}, CON['book']['effective_tail_js'], EFF_SCALED, BOOK_TAIL, BASE_NEW, REL_MEAN, JS_DIFF['loans_max_abs']))


# ---------------------------------------------------------------------------------------------------------------
# 12. assemble: js_table, shipped values, checks, sources, not_shipped
# ---------------------------------------------------------------------------------------------------------------
FACTOR_FITTED = half_up(MID)
FACTOR = DECISION['factor']                     # shipped as decided; a disagreement is reported in open_issues
q120_lo, q120_hi = float(n120q.min()), float(n120q.max())
qlong_lo, qlong_hi = float(lngq.min()), float(lngq.max())
vint_all = list(S2['by_vintage'].values()) + list(S3['by_vintage'].values())
SCALED = [KAPPA * x for x in BAND_R]            # what tailAt applies at the band centres
_le96 = ['%.0f%%' % (100 * CHOW_PROFILE['term_le96_nonCO'][b]) for b in BLAB]
if half_up(SCALED[-1]) < half_up(SCALED[-2]):
    SIZE_TXT = 'from x%.2f under $150k to x%.2f at $0.75-1.5M (x%.2f at $1.5M and up)' % (SCALED[0], SCALED[-2], SCALED[-1])
else:
    SIZE_TXT = 'from x%.2f under $150k to x%.2f at $1.5M and up' % (SCALED[0], SCALED[-1])
NOTE = ('Years 9-10 are borrowed from SBA 7(a) term loans approved FY2010-15 (no acquisition loan is older than 8.5 years), startups excluded '
        'and matched to the acquisition book on loan size, term, sector, SBA Express and franchise: CIF(120)/CIF(96) = x%.2f (SE %.2f). '
        'Late charge-offs come from 10-year notes: in 2023-26 (observed through 2026-06), a 120-month note still on the books at month 96 had a '
        '%.1f-%.1f%% chance of charge-off by month 120 %s, a note longer than 10 years %.1f-%.1f%%. The ratio rises with loan size, %s, because '
        'small acquisition notes are far more often 5-7-year notes, which mature by month 96 (notes of 96 months or less: %s and %s, from '
        'under $150k to $1.5M and up), and because early charge-off risk falls with size; 25-year terms do not explain it. Single post-crisis vintages ran '
        'x%.2f-%.2f, vintages FY2013-16 x%.2f-%.2f, a crisis path (FY2005-15) x%.2f.'
        % (FACTOR, FACTOR_SE, 100 * q120_lo, 100 * q120_hi, 'at every loan size' if FLAT['p'] > 0.05 else 'by loan size', 100 * qlong_lo, 100 * qlong_hi,
           SIZE_TXT, ', '.join(_le96[:-1]), _le96[-1], min(vint_all), max(vint_all), WIN['FY2013-16']['2-class + sector + Express + franchise']['ratio'],
           WIN['FY2013-16']['3-class + sector + Express + franchise']['ratio'], WIN['FY2005-15']['2-class + sector + Express + franchise']['ratio']))
AP_SHIP = {}
for k in LEVELS:
    if k == '2009-11 (post-crisis)':
        AP_SHIP['2009-11 (post-crisis; calendar 2009 merged into 2010)'] = r4(AP_MERGED[k])
    else:
        AP_SHIP[k] = r4(AP[k]['tail'])
ALLOC_NOTE = ('late charge-offs whose original term is unknown (%d of %d) are spread over the term classes by the split of %d late charge-offs '
              'with known terms given their rule-A class (FY2001-16 loans charged off after month 96 and after 2023-09-30): a rewritten term of '
              '120 months or less %.0f%% short / %.0f%% 120-month / %.0f%% long, over 120 months %.0f%% / %.0f%% / %.0f%%; se adds a bootstrap of the split'
              % (int(_unk.sum()), CLEAN['late_co'], SPLIT_N['n'], *(100 * SPLIT[0]), *(100 * SPLIT[1])))
JS = {
    'factor': FACTOR, 'factor_se': FACTOR_SE,
    'by_band': {'bands': BLAB, 'centres': CENTRES_R, 'ratio': BAND_R, 'se': BAND_SE_R, 'se_total': BAND_SE_TOTAL,
                'interp': 'linear in ln loan between centres, flat beyond the outer centres',
                'scale': KAPPA,
                'scale_note': ('tail(loan) = scale x ratio interpolated. ratio is the factor\'s own estimator in each loan band (FY2010-15 term loans, '
                               'startups excluded, raked within band to the acquisition book\'s sector, SBA Express, franchise and term-class margins; '
                               'midpoint of the two- and three-class matches). On the factor\'s population (FY2018-26 change-of-ownership band mix, '
                               'matched mature CIF96) the table aggregates to %.4f, so scale only carries the rounding of the factor to %.2f'
                               % (BAND_AGG['shipped table (3 dp)']['factor_population'], FACTOR)),
                'book_tail': BOOK_TAIL,
                'book_note': 'p8-weighted mean of scale x ratio over the FY2024-26 acquisition book (base_cif\'s population, larger loans than FY2018-26): base_cif.term = h96 x book_tail',
                'se_note': ('se: delete-one-vintage jackknife of the band estimate; se_total adds the factor SE\'s term-bracket, transport and drift parts '
                            'in quadrature (%.3f)' % COMMON_SE)},
    'estimates': {
        'two_class': {'ratio': r4(S2['ratio']), 'se': r4(S2['se_jk'])},
        'three_class': {'ratio': r4(S3['ratio']), 'se': r4(S3['se_jk'])},
        'midpoint': r4(MID), 'midpoint_se': r4(MID_SE),
        'age_period_2023_26': {'ratio': r4(AP['2023-26']['tail']), 'se': r4(AP_SE['2023-26']), 'ci95': [r4(x) for x in AP_CI['2023-26']]},
        'odds_weights': r4(SPEC['excl. startups | odds weights']['ratio']),
        'band_only': r4(SPEC['all ages | band only (the console\'s current construction)']['ratio']),
        'se_parts': {k: r4(v) for k, v in SE_PARTS.items()}, 'se_total_measured': r4(SE_TOTAL), 'se_lower_no_drift': r4(SE_LOWER),
        'n_loans': S2['n'], 'n_chgoff': S2['chgoff'], 'n_chgoff_96_120': S2['chgoff_96_120']},
    'spread': {
        'single_vintages': [r4(min(vint_all)), r4(max(vint_all))],
        'recent_FY2013_16': [r4(WIN['FY2013-16']['2-class + sector + Express + franchise']['ratio']), r4(WIN['FY2013-16']['3-class + sector + Express + franchise']['ratio'])],
        'FY2016_out_of_time': [r4(WIN['FY2016']['2-class + sector + Express + franchise']['ratio']), r4(WIN['FY2016']['3-class + sector + Express + franchise']['ratio'])],
        'crisis_FY2005_15': r4(WIN['FY2005-15']['2-class + sector + Express + franchise']['ratio']),
        'crisis_FY2005_15_vintage_max': r4(WIN['FY2005-15']['2-class + sector + Express + franchise']['vintage_max']),
        'through_cycle_FY2000_16': [r4(min(v['r120_96'] for v in CYC.values())), r4(max(v['r120_96'] for v in CYC.values()))],
        'through_cycle_FY1991_99': [r4(min(v['r120_96'] for v in CYC90.values())), r4(max(v['r120_96'] for v in CYC90.values()))],
        'age_period_by_conditions': AP_SHIP,
        'q_transport': r4(QT['all']['tail_q_transport']),
        'predictive_se_new_vintage': r4(max(S2['se_predictive'], S3['se_predictive']))},
    'late_hazard_by_term': {
        'window': 'loans started 2015-10..2016-12 still on the books at month 96; years 9-10 run 2023-10..2026-12, observed through 2026-06',
        'bands': BLAB, 'n_alive': CLEAN['alive_at_96'], 'late_chgoff': CLEAN['late_co'],
        'n120': {'q': [r4(x) for x in n120q], 'se': [r4(x) for x in n120s]},
        'long': {'q': [r4(x) for x in lngq], 'se': [r4(x) for x in lngs]},
        'all': {'q': [r4(CROWS[b]['all']['q']) for b in BLAB]},
        'share_alive_96': [r4(CROWS[b]['share_alive_96']) for b in BLAB],
        'cif96': [r4(CROWS[b]['cif96_cohort']) for b in BLAB],
        'flat_p': r4(FLAT['p']),
        'allocation': ALLOC_NOTE},
    'note_facts': NOTE,
    'source': ('SBA 7(a) FOIA as of 2026-06-30 (data.sba.gov), term loans approved FY2010-15 (%s, startups excluded; %s charge-offs, %s in months '
               '96-120), terms of later charge-offs recovered from the 2023-09-30 snapshot (CSIS mirror); target: SBA change-of-ownership loans '
               'FY2018-26 (%s); fit/sba_tail_factor.py' % ('{:,}'.format(S2['n']), '{:,}'.format(S2['chgoff']), '{:,}'.format(S2['chgoff_96_120']), '{:,}'.format(N_CHOW))),
    'method': ('Aalen-Johansen CIF(120)/CIF(96) (payoff competing), mature loans (startups excluded) raked to the acquisition book (band, and band x '
               'sector, SBA Express, franchise and term class); charged-off loans classed by their rewritten term (long if over 120 months, '
               '%.1f%% accurate on known terms); midpoint of the two-class (x%.3f, leans low) and three-class (x%.3f, leans high) matches; '
               'cross-check: age-period hazards at constant 2023-26 conditions x%.3f. SE %.2f: estimation %.3f, term bracket %.3f, transport %.3f '
               'and drift %.3f in quadrature (%.3f; %.3f without the drift part, a lower bound). by_band: the same estimator in each loan band.'
               % (100 * RULEA['accuracy'], S2['ratio'], S3['ratio'], AP['2023-26']['tail'], FACTOR_SE, SE_PARTS['estimation'], SE_PARTS['term_bracket'],
                  SE_PARTS['transport'], SE_PARTS['drift'], SE_TOTAL, SE_LOWER))}
JS = clean(JS, 6)
JS_LINE = json.dumps(JS, separators=(',', ':'))
assert json.loads(JS_LINE) == JS
assert all(JS['by_band'][k] == JS_BY_BAND[k] for k in JS_BY_BAND), 'the shipped by_band must be what the probe ran tailAt against'


def chk(name, ok, detail):
    return {'name': name, 'outcome': ('pass' if ok else 'fail') if ok is not None else 'info', 'detail': detail}


AP_IN = all(AP_CI['2023-26'][0] <= AP[k]['tail'] <= AP_CI['2023-26'][1] for k in ['2023-26', '2017-19', '2020-22 (CARES relief)', '2012-16'])
_ps, _pl, _po, _sl_ = OOS['profile_summary'], OOS['lovo_summary'], OOS['fy2016_out_of_time'], OOS['slope']
_rts, _rtp = OOS_RT['slope'], OOS_RT['profile_summary']
_snap_re = CON['real_estate']['share_term_over_120m']
_bl = {k: REAL[k]['bl_over_all'] for k, _, _ in LBANDS}; _lg = {k: REAL[k]['long_over_all'] for k, _, _ in LBANDS}
_blmin, _blmax = min(_bl, key=_bl.get), max(_bl, key=_bl.get)
CHECKS = [
    chk('the console\'s current construction rebuilt', abs(SHIP_REBUILT - CURRENT['tail_factor']) < 5e-5,
        'sum_b acq_share x CIF120 / sum_b acq_share x CIF96 by band, FY2010-15 term loans, from 4-decimal intermediates as sba_risk_refresh.py 3f '
        'computes it: %.5f against the console\'s 1.1989 (exact arithmetic %.4f)' % (SHIP_REBUILT, SHIP_REBUILT_EXACT)),
    chk('research two-class match reproduced (1.1992)', abs(S2['ratio'] - 1.1992) < 0.003, '%.4f (jackknife SE %.4f)' % (S2['ratio'], S2['se_jk'])),
    chk('research three-class match reproduced (1.2198)', abs(S3['ratio'] - 1.2198) < 0.003, '%.4f (jackknife SE %.4f)' % (S3['ratio'], S3['se_jk'])),
    chk('research age-period estimate reproduced (1.2148)', abs(AP['2023-26']['tail'] - 1.2148) < 0.003,
        '%.4f (bootstrap SE %.4f, 95%% %.4f-%.4f)' % (AP['2023-26']['tail'], AP_SE['2023-26'], AP_CI['2023-26'][0], AP_CI['2023-26'][1])),
    chk('raking reproduces every CHOW margin', max(v['max_abs_margin_dev'] for v in RAKE_DIAG.values()) < 1e-6,
        '; '.join('%s: max |dev| %.1e, Kish n %.0f of %d, largest weight %.0f x mean' % (k, v['max_abs_margin_dev'], v['kish_n'], v['n'], v['max_weight_over_mean'])
                  for k, v in RAKE_DIAG.items())),
    chk('rule A on known terms', RULEA['accuracy'] >= 0.9,
        'charged-off FY2001-16 loans whose original term is a standard 2023 term (n %d): %.1f%% classed right; %.1f%% predicted long against %.1f%% true'
        % (RULEA['n'], 100 * RULEA['accuracy'], 100 * RULEA['pred_long'], 100 * RULEA['true_long'])),
    chk('the rewrite is near-universal and happens before charge-off', max(_y) < 0.1 and REWRITE['std_share_pif_fy2000_16'] > 0.6,
        'standard terms on %.1f-%.1f%% of charged-off loans by charge-off year 2001-25 against %.1f%% of paid-off loans; of loans open at 2023-09-30 and charged off by 2026-06-30, %s already carried a non-standard 2023 term (paid-off benchmark %.0f%%)'
        % (100 * min(_y), 100 * max(_y), 100 * REWRITE['std_share_pif_fy2000_16'],
           ', '.join('%s %.0f%%' % (k, 100 * v) for k, v in list(REWRITE['open_2023_chgoff_later']['nonstandard_2023_term_by_chgoff_quarter'].items())[:3]),
           100 * REWRITE['nonstandard_share_pif_same_vintages'])),
    chk('age-period estimate inside the two/three-class bracket', min(S2['ratio'], S3['ratio']) <= AP['2023-26']['tail'] <= max(S2['ratio'], S3['ratio']),
        '%.4f in [%.4f, %.4f]' % (AP['2023-26']['tail'], S2['ratio'], S3['ratio'])),
    chk('both estimators round to the shipped factor', half_up(AP['2023-26']['tail']) == FACTOR == half_up(MID),
        'midpoint %.4f, age-period %.4f -> %.2f' % (MID, AP['2023-26']['tail'], FACTOR)),
    chk('factor SE = the like-for-like measured parts, rounded', half_up(SE_TOTAL) == FACTOR_SE and SE_LOWER < FACTOR_SE,
        'estimation %.4f (jackknife of the midpoint), term bracket %.4f, transport %.4f, drift %.4f (the same midpoint on FY2013-16, %.4f, against FY2010-15, %.4f) '
        '-> %.4f -> %.2f shipped (round 2 shipped %.2f; the research\'s rounded parts gave %.4f). Without the drift part %.4f, a lower bound. Along each window\'s '
        'own calendar path the age-period model (no cohort terms) gives FY2013-16 %.4f and FY2010-15 %.4f, a gap of %.4f against the realized %.4f: consistent '
        'with a calendar explanation of the drift, but free age and calendar effects absorb any linear cohort trend, so the comparison cannot rule a '
        'cohort drift out, and the drift part stays in the SE' % (
            SE_PARTS['estimation'], SE_PARTS['term_bracket'], SE_PARTS['transport'], SE_PARTS['drift'], REC_MID, MID, SE_TOTAL, FACTOR_SE, 0.05,
            SE_RESEARCH_ROUNDED, SE_LOWER, AP_PATH['FY2013-16'], AP_PATH['FY2010-15'], AP_PATH['FY2013-16 minus FY2010-15'], REC_MID - MID)),
    chk('age-period tail at other calendar levels inside the 2023-26 bootstrap interval', AP_IN,
        ', '.join('%s %.3f' % (k, v['tail']) for k, v in AP.items() if k != '2009-11 (post-crisis)')
        + '; 2009-11 with calendar 2009 merged into 2010 %.3f (shipped; post-crisis conditions, not required)' % AP_MERGED['2009-11 (post-crisis)']),
    chk('2009-11 level: calendar 2009 merged into 2010', abs(AP_MERGED['2023-26'] - AP['2023-26']['tail']) < 1e-3,
        'calendar 2009 holds %.0f loan-years and %.0f charge-offs, so its own charge-off effect is not identified (the other years sit %.1f above it on the log '
        'scale) and the 2009-11 average with it is %.4f; merged into 2010: %s. The 2023-26 level is unaffected (%.4f against %.4f)' % (
            AP_CAL0['exposure_loan_years'], AP_CAL0['chgoff'], AP_CAL0['co_effect_other_years_mean'], AP['2009-11 (post-crisis)']['tail'],
            ', '.join('%s %.4f' % (k, v) for k, v in AP_MERGED.items()), AP_MERGED['2023-26'], AP['2023-26']['tail'])),
    chk('out of time: FY2016 within 2 SE of FY2010-15', abs(WIN['FY2016']['midpoint'] - MID) < 2 * MID_SE,
        'FY2016 alone %.4f / %.4f (two/three-class; %d loans reach month 120) against %.4f / %.4f' % (
            WIN['FY2016']['2-class + sector + Express + franchise']['ratio'], WIN['FY2016']['3-class + sector + Express + franchise']['ratio'],
            WIN['FY2016']['at_risk_120'], S2['ratio'], S3['ratio'])),
    chk('late risk scales with early risk across vintages (ratio transport)', all(abs(PROP[k]['slope'] - 1) < 2 * PROP[k]['se'] for k in
                                                                                  ['all terms, >=150k', '120-month T2, >=150k', 'cells all terms, band effects', 'cells 120-month T2, band effects']),
        '; '.join('%s %.2f (SE %.2f)' % (k, v['slope'], v['se']) for k, v in PROP.items())),
    chk('clean window: unknown-term late charge-offs allocated by the known-term split', ALLOC_ROUND2_DIFF < 1e-12 and N_UNCLASSED == 0,
        'of %d late charge-offs, %d have an unknown original term (%d with a rewritten term of 120 months or less, %d over). Known-term split of %d late charge-offs '
        '(FY2001-16, after month 96 and after 2023-09-30; %d of them in the window) given rule A: 120 months or less -> %s; over 120 -> %s. '
        '120-month q %s (as rule A stands, round 2: %s; business-length unknowns only: %s); long q %s (as rule A stands %s). The split with no allocation '
        'reproduces round 2 to %.1e' % (
            CLEAN['late_co'], int(_unk.sum()), int((_unk & (_unkA == 0)).sum()), int((_unk & (_unkA == 1)).sum()), SPLIT_N['n'], SPLIT_N['in_clean_window'],
            ' / '.join('%s %d' % (TCLS[i], SPLIT_CNT[0, i]) for i in range(3)), ' / '.join('%s %d' % (TCLS[i], SPLIT_CNT[1, i]) for i in range(3)),
            ' / '.join('%.1f%%' % (100 * x) for x in n120q), ' / '.join('%.1f%%' % (100 * CROWS[b]['120-month (N 97-120)']['q']) for b in BLAB),
            ' / '.join('%.1f%%' % (100 * ALLOC_SENS['business-length unknowns only']['120-month'][b]) for b in BLAB),
            ' / '.join('%.1f%%' % (100 * x) for x in lngq), ' / '.join('%.1f%%' % (100 * CROWS[b]['long (N>120)']['q']) for b in BLAB), ALLOC_ROUND2_DIFF)),
    chk('years 9-10 risk of 10-year notes flat across loan size (2023-26)', FLAT['p'] > 0.05,
        '120-month notes alive at month 96 (allocated): q %s; inverse-variance chi2 %.2f on %d df, p %.2f; slope per ln loan %.4f' % (
            ' / '.join('%.1f%%' % (100 * x) for x in n120q), FLAT['chi2'], FLAT['df'], FLAT['p'], FLAT['slope_per_ln_loan'])),
    chk('long notes carry less years 9-10 risk than 10-year notes in every band', bool(np.all(lngq < n120q)),
        'long %s against 120-month %s (allocated)' % (' / '.join('%.1f%%' % (100 * x) for x in lngq), ' / '.join('%.1f%%' % (100 * x) for x in n120q))),
    chk('shipped band table rises with loan size to $1.5M; the top band is within its SE of the next', bool(np.all(np.diff(BAND_R[:4]) > 0)) and GRAD_Z > 2 and abs(TOP_DIP) < 2 * TOP_DIP_SE,
        '%s (main estimator per band, jackknife SE %s); top minus bottom %.3f (jackknife SE %.3f, z %.1f); top minus next %+.3f (SE %.3f)' % (
            ' / '.join('%.3f' % x for x in BAND_R), ' / '.join('%.3f' % x for x in BAND_SE_R), GRAD, GRAD_SE, GRAD_Z, TOP_DIP, TOP_DIP_SE)),
    chk('band gradient in every vintage (shipped construction)', _sl_['p_two_sided_t'] < 0.05,
        'slope of the band ratio per ln loan (bands weighted by their share of CHOW 8-year charge-offs): pooled %.3f; FY2010-15 vintages %s '
        '(positive in %d of %d; mean %.3f, SE %.3f, t %.1f on %d df, p %.4f); FY2016 out of time %.3f (loan bootstrap SE %.3f)' % (
            _sl_['pooled'], ' / '.join('%.3f' % v for v in _sl_['by_vintage'].values()), _sl_['positive_vintages'], _sl_['vintages'],
            _sl_['mean'], _sl_['se_between_vintages'], _sl_['t'], _sl_['vintages'] - 1, _sl_['p_two_sided_t'], _sl_['fy2016'], _sl_['fy2016_se_boot'])),
    chk('size profile holds out of sample (shipped construction)', _ps['vintages_band_better'] >= 4 and _ps['rmse_band'] < _ps['rmse_single'] and _ps['fy2016_rmse_band'] < _ps['fy2016_rmse_single'],
        'held-out band ratios over their own vintage aggregate, predicted by the other vintages\' profile or by 1 (single factor): '
        'band better in %d of %d, RMSE %.4f against %.4f; FY2016 %.4f against %.4f (FY2016 band ratios %s, boot SE %s)' % (
            _ps['vintages_band_better'], _ps['vintages'], _ps['rmse_band'], _ps['rmse_single'], _ps['fy2016_rmse_band'], _ps['fy2016_rmse_single'],
            ' / '.join('%.3f' % x for x in _po['fy2016_band_ratios']), ' / '.join('%.3f' % x for x in _po['band_se_boot']))),
    chk('band-specific against single, levels (shipped construction; vintage shifts included)', None,
        'leave-one-vintage-out FY2010-15: band better in %d of %d, RMSE %.4f against %.4f; FY2016: %.4f against %.4f' % (
            _pl['vintages_band_better'], _pl['vintages'], _pl['rmse_band'], _pl['rmse_single'], _pl['fy2016_rmse_band'], _pl['fy2016_rmse_single'])),
    chk('research table (round 2\'s construction: all ages, term mix only), cross-check', None,
        '%s (jackknife SE %s; top minus bottom %.3f, z %.1f); slope positive in %d of %d vintages (t %.1f); profile better in %d of %d held-out vintages '
        '(RMSE %.4f against %.4f), FY2016 %.4f against %.4f. Shipped minus research: %s' % (
            ' / '.join('%.3f' % BAND[b]['ratio'] for b in BLAB), ' / '.join('%.3f' % BAND[b]['se_jk'] for b in BLAB), GRAD_RT, GRAD_RT_Z,
            _rts['positive_vintages'], _rts['vintages'], _rts['t'], _rtp['vintages_band_better'], _rtp['vintages'], _rtp['rmse_band'], _rtp['rmse_single'],
            _rtp['fy2016_rmse_band'], _rtp['fy2016_rmse_single'], ' / '.join('%+.3f' % (BAND_MAIN[b]['midpoint'] - BAND[b]['ratio']) for b in BLAB))),
    chk('shipped table level on the factor\'s population', abs(KAPPA * BAND_AGG['shipped table (3 dp)']['factor_population'] - FACTOR) < 5e-4
        and abs(BAND_AGG['main estimator per band (unrounded)']['factor_population'] - MID) < 1e-3,
        'shipped table aggregated on the FY2018-26 CHOW band mix with the main estimator\'s matched mature CIF96: %.4f (unrounded %.4f against the factor\'s '
        'unrounded midpoint %.4f); x scale %.4f -> %.4f against %.2f. With the research table\'s all-ages CIF96 it would be %.4f, with the CHOW book\'s '
        'own CIF96 %.4f. Over the FY2024-26 book (larger loans) the scaled table gives %.4f (book_tail)' % (
            BAND_AGG['shipped table (3 dp)']['factor_population'], BAND_AGG['main estimator per band (unrounded)']['factor_population'], MID, KAPPA,
            KAPPA * BAND_AGG['shipped table (3 dp)']['factor_population'], FACTOR, BAND_AGG['shipped table (3 dp)']['research_cif96_weights'],
            BAND_AGG['shipped table (3 dp)']['chow_aj_cif96_weights'], EFF_SCALED)),
    chk('book tail above the factor is the book\'s size mix, not the console\'s p8 shape',
        abs(BOOKMIX['shipped table (3 dp)']['chow_mix_x_console_p8'] - BOOKMIX['shipped table (3 dp)']['chow_mix_x_chow_aj']) < 0.003,
        'shipped table aggregated by band: FY2018-26 mix x CHOW CIF96 %.4f, FY2018-26 mix x console p8 %.4f, FY2024-26 mix x CHOW CIF96 %.4f, FY2024-26 mix x console p8 %.4f; '
        '$1.5M+ share %.3f in the FY2024-26 book against %.3f' % (
            BOOKMIX['shipped table (3 dp)']['chow_mix_x_chow_aj'], BOOKMIX['shipped table (3 dp)']['chow_mix_x_console_p8'],
            BOOKMIX['shipped table (3 dp)']['book_mix_x_chow_aj'], BOOKMIX['shipped table (3 dp)']['book_mix_x_console_p8'],
            BOOKMIX['book_band_share'][-1], BOOKMIX['chow_band_share'][-1])),
    chk('tailAt (js_code) reproduces the table, and rel still averages 1 over the book', JS_DIFF['loans_max_abs'] < 1e-12 and JS_DIFF['book_abs'] < 1e-12 and abs(REL_MEAN - 1) < 0.005,
        'js_code run in node against the shipped by_band at %d loans ($50k-$5M; flat beyond the outer centres: tailAt %.4f at $50k, %.4f at $5M): max |tailAt - scale x '
        'interpolation| %.1e; p8-weighted over the FY2024-26 book %.6f against %.6f; with base_cif.term = h96 x book_tail = %.5f the book mean of rel is %.4f '
        '(h96 is rounded to %.3f; the book mean of p8 is %.5f)' % (
            len(CON['loans']), CON['loans'][0]['tail_js'], CON['loans'][-1]['tail_js'], JS_DIFF['loans_max_abs'], CON['book']['effective_tail_js'], EFF_SCALED,
            BASE_NEW, REL_MEAN, H96, CON['book']['mean_p8'])),
    chk('through-the-cycle range matches the snapshot note (x1.12-1.51)', abs(min(v['r120_96'] for v in CYC.values()) - 1.12) < 0.01 and abs(max(v['r120_96'] for v in CYC.values()) - 1.51) < 0.01,
        'FY2000-16 vintages >= $150k: %.3f-%.3f' % (min(v['r120_96'] for v in CYC.values()), max(v['r120_96'] for v in CYC.values()))),
    chk('1990s vintages (2023-09-30 snapshot)', None,
        'FY1991-99 >= $150k: ' + ', '.join('%d %.2f' % (k, v['r120_96']) for k, v in CYC90.items())),
    chk('real-estate note: shares rebuilt as the snapshot ships them', max(abs(RE_SHARE[k] - _snap_re[k]) for k, _, _ in LBANDS) < 1e-4
        and half_up(100 * RE_STD['chargeoffs'], 0) == 11 and half_up(100 * RE_STD['others'], 0) == 86,
        'terms over 120 months (paid-off and open): %s against the snapshot\'s %s; standard terms (%s) on %.1f%% of charged-off loans against %.1f%% of others' % (
            ', '.join('%s %.4f' % (k, RE_SHARE[k]) for k, _, _ in LBANDS), ', '.join('%s %.4f' % (k, _snap_re[k]) for k, _, _ in LBANDS),
            '/'.join(str(x) for x in STD_RE), 100 * RE_STD['chargeoffs'], 100 * RE_STD['others'])),
    chk('business-only acquisition notes are riskier than their size average', all(_bl[k] > 1 for k in _bl) and all(_lg[k] < 1 for k in _lg),
        'CHOW Aalen-Johansen charge-off within 8 years, notes of 10 years or less / all notes of the band (rule A on charged-off loans): %s; notes longer '
        'than 10 years / all: %s' % (', '.join('%s x%.2f (SE %.2f)' % (k, REAL[k]['bl_over_all'], REAL[k]['bl_over_all_se']) for k, _, _ in LBANDS),
                                     ', '.join('%s x%.2f (SE %.2f)' % (k, REAL[k]['long_over_all'], REAL[k]['long_over_all_se']) for k, _, _ in LBANDS))),
    chk('js_table parses back', json.loads(JS_LINE) == JS, 'compact line %d characters' % len(JS_LINE)),
]
for c in CHECKS:
    say('  [%s] %s: %s' % (c['outcome'], c['name'], c['detail']))

SHIPPED = [
    {'param': 'MODELS.risk.tail_factor (tail.factor)', 'current': CURRENT['tail_factor'], 'new': FACTOR, 'unrounded': MID,
     'se': FACTOR_SE, 'se_measured': SE_TOTAL, 'se_lower_no_drift': SE_LOWER, 'current_se': CURRENT['tail_factor_se'], 'tier': 'fitted',
     'estimator': 'midpoint of the two- and three-class CHOW-matched ratios, FY2010-15, startups excluded; age-period cross-check %.4f' % AP['2023-26']['tail']},
    {'param': 'MODELS.risk.tail_factor_se (tail.factor_se)', 'current': CURRENT['tail_factor_se'], 'new': FACTOR_SE, 'measured': SE_TOTAL,
     'lower_bound_no_drift': SE_LOWER, 'round2_shipped': 0.05, 'parts': SE_PARTS, 'tier': 'fitted (measured parts)'}]
for i, b in enumerate(BLAB):
    SHIPPED.append({'param': 'tail.by_band %s' % b, 'current': CURRENT['tail_by_band'][b], 'current_definition': 'unmatched all-terms band ratio (tail_by_band, display only)',
                    'new': BAND_R[i], 'applied': KAPPA * BAND_R[i], 'unrounded': BAND_MAIN[b]['midpoint'], 'se': BAND_SE_R[i], 'se_unrounded': BAND_MAIN[b]['midpoint_se'],
                    'se_total': BAND_SE_TOTAL[i], 'centre': CENTRES_R[i], 'round2_shipped': ROUND2['ratio'][i], 'research_table': BAND[b]['ratio'], 'tier': 'fitted'})
SHIPPED += [
    {'param': 'tail.by_band.scale', 'new': KAPPA, 'round2_shipped': ROUND2['scale'],
     'definition': 'factor / the shipped table aggregated on the factor\'s own population (%.4f)' % BAND_AGG['shipped table (3 dp)']['factor_population']},
    {'param': 'tail.by_band.book_tail', 'new': BOOK_TAIL, 'round2_shipped': ROUND2['book_tail'], 'base_cif_term': BASE_NEW, 'current_base_cif_term': CON['base_cif']['term'],
     'definition': 'p8-weighted mean of tailAt over the FY2024-26 book fixture (n %d)' % CON['book']['n']},
    {'param': 'tail.spread.age_period_by_conditions 2009-11', 'new': AP_MERGED['2009-11 (post-crisis)'], 'round2_shipped': AP['2009-11 (post-crisis)']['tail'],
     'label': '2009-11 (post-crisis; calendar 2009 merged into 2010)'},
    {'param': 'tail.late_hazard_by_term.n120 / long', 'new': {'n120': n120q.tolist(), 'long': lngq.tolist()},
     'round2_shipped': {'n120': [CROWS[b]['120-month (N 97-120)']['q'] for b in BLAB], 'long': [CROWS[b]['long (N>120)']['q'] for b in BLAB]},
     'change': 'unknown-term late charge-offs allocated by the known-term split given their rule-A class'}]

REC_BAND = (_sl_['p_two_sided_t'] < 0.05 and _ps['vintages_band_better'] >= 4 and _ps['rmse_band'] < _ps['rmse_single'])
eff = {int(e['loan']): e for e in EFFECT}


def _eff_line(key_tail, base_key='pTerm_single_1_21'):
    return ', '.join('$%s %.2f%% -> %.2f%% (%+.2f pp)' % (lab, 100 * eff[k][base_key], 100 * eff[k]['p8'] * eff[k][key_tail],
                                                         100 * (eff[k]['p8'] * eff[k][key_tail] - eff[k][base_key])) for k, lab in [(200000, '200k'), (700000, '700k'), (2000000, '2M')])


_effect_txt = ('Effect of tailAt on the 10-year figure (average sector, no state, table rate, variable note): against the single %.2f %s; against the '
               'current console (x%.4f) %s; round 2\'s table would have given %s against the single factor.' % (
                   FACTOR, _eff_line('tail_band_scaled'), CURRENT['tail_factor'], _eff_line('tail_band_scaled', 'pTerm_current'), _eff_line('tail_round2_scaled')))
_TOPW = '%.3f %s the next (SE %.3f)' % (abs(TOP_DIP), 'below' if TOP_DIP < 0 else 'above', TOP_DIP_SE)
_caveat = ('FY2016, out of time with month 120 partly censored, runs %s on this construction (slope %.3f, SE %.3f, against %.3f pooled); the top band\'s '
           'estimate (%.3f) sits %s%s' % (
               ' / '.join('%.2f' % x for x in _po['fy2016_band_ratios']), _sl_['fy2016'], _sl_['fy2016_se_boot'], _sl_['pooled'], BAND_R[-1], _TOPW,
               ', so the table is flat above $1M within its SE.' if abs(TOP_DIP) < 2 * TOP_DIP_SE else '.'))
_rec_txt = ('Band-specific tails (decided): tail(loan) = scale x the like-for-like band ratio interpolated linearly in ln loan size between the band '
            'centres (%s), flat beyond the outer centres, and pTerm = p8 x tail(loan) (js_code tailAt). scale (%.4f) ties the table to tail.factor '
            '(%.2f) on the factor\'s own population (the FY2018-26 change-of-ownership mix with the matched mature CIF96, where the unrounded table '
            'composes to %.4f against the factor\'s unrounded %.4f). Set base_cif.term = base_cif.h96 x by_band.book_tail = %.5f (book_tail %.4f) '
            'against %.5f with the single factor and %.4f today, so rel still averages 1 over the FY2024-26 book; the book\'s tail is above the factor '
            'because its loans are larger (%.0f%% at $1.5M and up against %.0f%%). Evidence on the shipped construction: the slope of the band ratio per '
            'ln loan is positive in %d of %d FY2010-15 vintages (t %.1f, p %.3f); the size profile predicts held-out vintages better than a flat one in '
            '%d of %d (RMSE %.4f against %.4f) and FY2016 out of time (%.4f against %.4f); late-hazard transport gives the same gradient (by band %s). ' % (
                ', '.join('$%s' % '{:,.0f}'.format(c) for c in CENTRES_R), KAPPA, FACTOR, BAND_AGG['main estimator per band (unrounded)']['factor_population'],
                MID, BASE_NEW, BOOK_TAIL, BASE_TERM['single 1.21'], CON['base_cif']['term'], 100 * BOOKMIX['book_band_share'][-1],
                100 * BOOKMIX['chow_band_share'][-1], _sl_['positive_vintages'], _sl_['vintages'], _sl_['t'], _sl_['p_two_sided_t'],
                _ps['vintages_band_better'], _ps['vintages'], _ps['rmse_band'], _ps['rmse_single'], _ps['fy2016_rmse_band'], _ps['fy2016_rmse_single'],
                ' / '.join('%.2f' % QT['all']['by_band'][b]['band_tail_q_transport'] for b in BLAB)))
if not REC_BAND:
    _rec_txt += ('Flag: on the shipped construction the size profile did not pass every held-out test (gradient t %.1f, p %.3f; profile better in %d of %d '
                 'held-out vintages, RMSE %.4f against %.4f). ' % (_sl_['t'], _sl_['p_two_sided_t'], _ps['vintages_band_better'], _ps['vintages'],
                                                                   _ps['rmse_band'], _ps['rmse_single']))

# replacement texts for the page (6): MODELS.risk.real_estate.note and the Data tab sentences that say the term of charged-off
# loans cannot be separated, the tail note and the Data tab's trap 4 (both still say "25-year terms")
_bl_txt = 'x%.2f (%s) to x%.2f (%s)' % (_bl[_blmin], 'under $250K' if _blmin == '<250K' else '$' + _blmin, _bl[_blmax], 'under $250K' if _blmax == '<250K' else '$' + _blmax)
_lg_txt = 'x%.2f-%.2f' % (min(_lg.values()), max(_lg.values()))
RE_NOTE_NEW = ('share of SBA acquisition notes with a term over 10 years (real-estate notes), paid-off and open loans: %s. A business-only '
               'acquisition of the same size is riskier, and probably more severe, than shown. SBA rewrites the recorded term of a charged-off loan '
               '(standard terms on %.0f%% of charged-off loans against %.0f%% of others), but a rewritten term over 120 months still marks a note longer '
               'than 10 years (%.1f%% right on %d charged-off 7(a) loans whose original term the 2023-09-30 snapshot kept). By that rule, acquisition '
               'notes of 10 years or less were charged off within 8 years at %s the rate of all notes their size, notes longer than 10 years at %s '
               '(Aalen-Johansen, FY2018-26 book; fit/sba_tail_factor.py). The charge-off model does not read the term, so it prices the average note of '
               'each size.' % (', '.join('%s %.0f%%' % (k, 100 * RE_SHARE[k]) for k, _, _ in LBANDS), 100 * RE_STD['chargeoffs'], 100 * RE_STD['others'],
                               100 * RULEA['accuracy'], RULEA['n'], _bl_txt, _lg_txt))
RE_DATA_TAB = ('A business-only acquisition of the same size is riskier than shown: a charged-off loan whose rewritten term is over 120 months is a note '
               'longer than 10 years (%.1f%% right where the original term is known), and by that rule acquisition notes of 10 years or less were charged '
               'off within 8 years at %s the rate of all notes their size.' % (100 * RULEA['accuracy'], _bl_txt))
_low2 = sorted(MID_BYV, key=MID_BYV.get)[:2]
TRAP4 = ('4. The last two years are borrowed. No acquisition loan here is older than 8.5 years. The curve is fitted to 8 years; years 9-10 are borrowed '
         'from mature 7(a) loans approved 2010-15, startups excluded and matched to acquisition loans on size, term, sector, SBA Express and franchise: '
         'x%.2f on average (SE %.2f, fitted), %s. Late charge-offs come from 10-year notes, and small acquisition notes are more often 5-7-year notes '
         'that mature before year 9; 25-year notes add little.%s'
         % (FACTOR, FACTOR_SE, SIZE_TXT, ' The 2011-12 vintages, whose years 9-10 overlapped CARES relief, are the lowest.' if sorted(_low2) == [2011, 2012] else ''))
REPLACEMENT_TEXT = {
    'MODELS.risk.real_estate.note': RE_NOTE_NEW,
    'Data tab, the sentence after "Real-estate notes: ..." (now "A business-only acquisition ... SBA does not keep the contractual term of charged-off loans, so this cannot be separated.")': RE_DATA_TAB,
    'MODELS.risk.tail_note': NOTE,
    'Data tab, trap 4 ("The last two years are borrowed", which reads tail_by_band and says "partly because larger mature loans more often carry 25-year terms")': TRAP4}

RECOMMEND = {
    'apply_band_specific': True, 'decided': True, 'evidence_passes': bool(REC_BAND),
    'text': _rec_txt + _effect_txt + ' ' + _caveat,
    'scale': KAPPA, 'book_tail': BOOK_TAIL, 'book_tail_unrounded': EFF_SCALED, 'book_mix': BOOKMIX,
    'effect': {('$%s' % '{:,.0f}'.format(k)): {kk: v[kk] for kk in ['loan', 'console_loan', 'p8', 'pTerm_current', 'rel_current', 'pTerm_single_1_21', 'tail_band',
                                                                  'tail_band_scaled', 'pTerm_band_scaled', 'rel_band', 'change_pp_band_vs_single',
                                                                  'change_pp_band_vs_current', 'change_pp_single_vs_current', 'change_rel_band_vs_single',
                                                                  'tail_round2_scaled', 'change_pp_round2_vs_single']}
               for k, v in eff.items() if k in (200000, 700000, 2000000)},
    'base_cif_term': BASE_TERM, 'effective_tail_book': EFF_TAIL,
    'integration_notes': [
        'MODELS.risk.tail = js_table (js_key "tail"). MODELS.risk.tail_factor 1.1989 -> tail.factor %.2f and tail_factor_se 0.0822 -> tail.factor_se %.2f (or read '
        'them from MODELS.risk.tail); the SBA tail factor leaves the judgment ledger (its "SBA tail factor" row and the "+ 1 /* the SBA tail factor" count) and is fitted.' % (FACTOR, FACTOR_SE),
        'fitRisk: pTerm = p8 * tailAt(loan) (js_code; loan is fitRisk\'s clamped note amount); expLoss keeps (pTerm - p8) at the years 9-10 severity.',
        'base_cif.term = base_cif.h96 x tail.by_band.book_tail = %.5f (today %.4f), so rel = pTerm / base_cif.term still averages 1 over the FY2024-26 book (%.4f).' % (BASE_NEW, CON['base_cif']['term'], REL_MEAN),
        'tests/model.test.js: "tail factor SE covers the loan-band range (>= 0.07)" fails at %.2f (test instead that factor_se = estimates.se_total_measured rounded '
        'and >= estimates.se_lower_no_drift); "tail factor between the small- and large-loan ratios" reads tail_by_band (use scale x by_band.ratio[0] < factor < '
        'scale x by_band.ratio[4]: %.3f < %.2f < %.3f); "population term = 8-year x tail factor" becomes base_cif.term = h96 x by_band.book_tail; "headline is the '
        'term" (pTerm = p8 x tail_factor) becomes pTerm = p8 x tailAt(loan); "tail factor inside the 1.1-1.3 range" still holds.' % (
            FACTOR_SE, KAPPA * BAND_R[0], FACTOR, KAPPA * BAND_R[-1]),
        'tail_note -> tail.note_facts; the Data tab\'s trap 4 and the real-estate sentence -> replacement_text; the Data tab rows that read tail_by_band -> '
        'tail.by_band (scale x ratio, centres).',
        'MODELS.risk.real_estate.note -> replacement_text["MODELS.risk.real_estate.note"] (its claim that the term of charged-off loans cannot be separated no '
        'longer holds: rule A separates long notes, %.1f%% right on known terms).' % (100 * RULEA['accuracy']),
        'README "Tried and not usable": the latent-term EM (AUC 0.966 for long notes, but 26% predicted long against 13% true).']}

NOT_SHIPPED = {
    'q_transport': {'value': QT['all']['tail_q_transport'], 'ratio_transport_same_weights': QT['all']['tail_ratio_transport_same_weights'],
                    'by_class': {k: [v['tail_q_transport'], v['tail_ratio_transport_same_weights']] for k, v in QT.items()},
                    'why': 'upper sensitivity: right only if acquisition loans\' lower early risk does not carry into years 9-10, which the vintage slopes argue against; enters the SE as the transport part'},
    'structural_form': {'formula': 'pTerm = p8 + S8 x q (S8 from the app\'s payoff hazards; q about %.3f for 10-year notes and %.3f for long notes in 2023-26)' % (_qbar, float(np.mean(lngq))),
                        'why': 'assumes late-hazard transport; not recommended now'},
    'recent_vintages': {k: {'two_class': WIN[k]['2-class + sector + Express + franchise']['ratio'], 'three_class': WIN[k]['3-class + sector + Express + franchise']['ratio'],
                            'two_class_se': WIN[k]['2-class + sector + Express + franchise']['se_jk'], 'three_class_se': WIN[k]['3-class + sector + Express + franchise']['se_jk']}
                        for k in ['FY2013-16', 'FY2014-16', 'FY2016']},
    'crisis_windows': {k: {kk: vv['ratio'] for kk, vv in WIN[k].items()} for k in ['FY2005-15', 'FY2001-15']},
    'subsets': {k: SPEC[k]['ratio'] for k in SPEC},
    'age_period_FY2005_16': {'tails': AP_FY05, 'n': AP_FY05_N, 'why': 'rejected: far above every observed vintage; without a cohort term the crisis cohorts load their excess onto the late ages, and with one the linear age slope is not identified'},
    'age_period_2009_11_reference_year': {'value': AP['2009-11 (post-crisis)']['tail'], 'why': 'biased by the reference year (calendar 2009: no charge-offs, effect not identified); the merged value ships'},
    'latent_term_EM': {'why': 'rejected by the research round (work/G-mechanics-tail/v2/run_termem.py, out3/termem.json; not re-run here): AUC 0.966 for long notes on 331 masked known terms but 26% predicted long against 13% true',
                       'reported': {'auc_long': 0.9658, 'mean_pred_long': 0.2633, 'obs_long': 0.1299}},
    'band_table_research': {'table': {b: {'ratio': BAND[b]['ratio'], 'se_jk': BAND[b]['se_jk']} for b in BLAB}, 'round2_shipped': ROUND2,
                            'why': 'round 2\'s shipped construction (all ages, CHOW term mix only), not the factor\'s estimator; it leans high like the three-class '
                                   'match (on the CHOW mix with its own CIF96 it aggregates to %.4f against the factor\'s %.4f) and keeps rising at the top band; kept '
                                   'as a cross-check' % (BAND_AGG['research table']['research_cif96_weights'], MID)},
    'late_hazard_rule_A_as_it_stands': {'n120': [CROWS[b]['120-month (N 97-120)']['q'] for b in BLAB], 'long': [CROWS[b]['long (N>120)']['q'] for b in BLAB],
                                        'why': 'round 2: every unknown-term late charge-off with a rewritten term of 120 months or less went to the 120-month class (short notes '
                                               'among them, without their denominator), and the 120-month notes among those with a rewritten term over 120 stayed in the long class'}}

OPEN = []
if FACTOR_FITTED != DECISION['factor']:
    OPEN.append('Factor: the fitted midpoint %.4f rounds to %.2f, not the shipped %.2f (two-class %.4f, three-class %.4f, age-period %.4f).' % (
        MID, FACTOR_FITTED, DECISION['factor'], S2['ratio'], S3['ratio'], AP['2023-26']['tail']))
if AP_BOOT_FAIL:
    OPEN.append('Age-period bootstrap: %d of %d draws failed to fit and are left out of the SE.' % (AP_BOOT_FAIL, B_AP))
if not REC_BAND:
    OPEN.append('Band tails: on the shipped construction the size profile did not pass every held-out test (see the recommendation).')
OPEN.append('SE (%.2f shipped): the drift part (%.4f, the same midpoint on FY2013-16 against FY2010-15) is the largest. Along each window\'s own calendar path the '
            'age-period model gives a gap of %.4f, consistent with the calendar path explaining it, but a model with free age and calendar effects absorbs any '
            'linear cohort trend, so calendar and cohort drift cannot be told apart here; the drift part stays in, and %.4f (without it) is a lower bound.' % (
                FACTOR_SE, SE_PARTS['drift'], AP_PATH['FY2013-16 minus FY2010-15'], SE_LOWER))
OPEN.append('Band table shape: the like-for-like table %s above $1M, the top band (%.3f) sitting %s, while the research table (all ages, '
            'term mix only) kept rising to %.3f. FY2016, out of time with month 120 partly censored, runs %s on the shipped construction (slope %.3f, SE %.3f, against %.3f '
            'pooled). No acquisition loan reaches month 120, so the CHOW late risk is transported, not observed.' % (
                'is flat' if abs(TOP_DIP) < 2 * TOP_DIP_SE else 'moves', BAND_R[-1], _TOPW, BAND[BLAB[-1]]['ratio'], ' / '.join('%.2f' % x for x in _po['fy2016_band_ratios']), _sl_['fy2016'],
                _sl_['fy2016_se_boot'], _sl_['pooled']))
OPEN.append('Population of the factor: tail.factor is matched to the FY2018-26 change-of-ownership book, while base_cif (and rel) use the FY2024-26 book, whose loans '
            'are larger (%.1f%% at $1.5M and up against %.1f%%). With tailAt that book\'s tail is %.4f (book_tail), so a single %.2f would understate the current '
            'book\'s 10-year level by about %.1f%%. The console\'s p8 weights the bands like the observed CHOW CIF96 (%.4f against %.4f on the same mix), so the gap '
            'is the mix, not the model.' % (
                100 * BOOKMIX['book_band_share'][-1], 100 * BOOKMIX['chow_band_share'][-1], EFF_SCALED, FACTOR, 100 * (EFF_SCALED / FACTOR - 1),
                BOOKMIX['shipped table (3 dp)']['chow_mix_x_console_p8'], BOOKMIX['shipped table (3 dp)']['chow_mix_x_chow_aj']))
OPEN.append('Clean-window allocation: the known-term split comes from late charge-offs that still carried their original term on 2023-09-30 (rewritten later). '
            'Of the %d unknown-term ones, %d already carried a rewritten term on 2023-09-30, %d could not be matched to that snapshot and %d had another '
            '2023 status. If the term mix differs between the known and unknown groups the allocation is off; the shipped SE carries only the split\'s '
            'sampling error. Allocating both rule-A classes moves the 120-month q by %+.1f%% (all bands) against '
            'round 2; allocating only the business-length unknowns (the review\'s suggestion) would move it by %+.1f%%, because the 120-month notes among the '
            'rule-A long charge-offs (%d of %d known) would stay in the long class.' % (
                int(_unk.sum()), UNK_KIND['rewritten_by_2023_09_30'], UNK_KIND['not_matched_to_2023'], UNK_KIND['other_2023_status'],
                100 * (ALLOC['all']['120-month']['q'] / CROWS['all']['120-month (N 97-120)']['q'] - 1),
                100 * (ALLOC_SENS['business-length unknowns only']['120-month']['all'] / CROWS['all']['120-month (N 97-120)']['q'] - 1),
                int(SPLIT_CNT[1, 1]), int(SPLIT_CNT[1].sum())))
OPEN.append('Real-estate text: the business-length/long split of CHOW charge-offs uses rule A, which classes some 121-239-month notes charged off late as '
            'business-length (FY2001-16 known terms: %d of %d late charge-offs with a rewritten term of 120 months or less were long notes); CHOW charge-offs are '
            'earlier (median %.0f months), where the rewritten term of a long note stays above 120, so the contrast is little affected. The 8-year Aalen-Johansen '
            'figures rest on %d-%d business-length loans at risk at month 96 per band.' % (
                int(SPLIT_CNT[0, 2]), int(SPLIT_CNT[0].sum()), float(np.median(d['T'].values[d.ev.values == 1])), min(REAL[k]['business_length']['at_risk_96'] for k, _, _ in LBANDS),
                max(REAL[k]['business_length']['at_risk_96'] for k, _, _ in LBANDS)))
OPEN.append('CHOW charge-offs are classed by their recorded (rewritten) TermInMonths in the three-class target (%d of %d loans): a 120-month CHOW note charged off at '
            'month 30 shows R about 90 and counts as short, while mature charge-offs use R + E >= 117. This shifts a little CHOW mass from the 120-month to the short '
            'cell in the three-class target (kept as the research coded it).' % (int((d.ev == 1).sum()), N_CHOW))
OPEN.append('Recent vintages run higher (FY2013-16 %.3f-%.3f) and a crisis path higher still (FY2005-15 %.3f, single vintages up to %.2f).' % (
    WIN['FY2013-16']['2-class + sector + Express + franchise']['ratio'], WIN['FY2013-16']['3-class + sector + Express + franchise']['ratio'],
    WIN['FY2005-15']['2-class + sector + Express + franchise']['ratio'], WIN['FY2005-15']['2-class + sector + Express + franchise']['vintage_max']))

SOURCES = []
for f in SBA26:
    SOURCES.append({'name': 'SBA 7(a) FOIA loan data as of 2026-06-30', 'url': SBA26_URL + f, 'file': SBA26_DIR + f, 'sha256': SHA[SBA26_DIR + f][:16],
                    'years': f.replace('FOIA_7a_', '').replace('_asof_260630.csv', ''), 'n': LMETA['rows_2026'][f],
                    'used': 'term loans FY2000-17 (mature samples, clean window, through the cycle); charge-off records for the rewrite timing'})
for f in SBA23:
    SOURCES.append({'name': 'SBA 7(a) FOIA loan data as of 2023-09-30 (CSISdefense/Vendor mirror)', 'url': SBA23_URL + f, 'file': SBA23_DIR + f,
                    'sha256': SHA[SBA23_DIR + f][:16], 'years': f.replace('foia-7a', '').replace('-asof-230930.zip', '').replace('-asof-230930.csv', ''),
                    'n': LMETA['rows_2023'][f], 'used': 'TermInMonths and LoanStatus at 2023-09-30, matched loan by loan (name|ZIP|approval date|amount)'})
SOURCES.append({'name': 'SBA 7(a) FOIA loan data as of 2023-09-30, FY1991-99 (CSISdefense/Vendor mirror)', 'url': SBA23_URL + SBA23_90S, 'file': SBA23_DIR + SBA23_90S,
                'sha256': SHA[SBA23_DIR + SBA23_90S][:16], 'years': 'FY1991-1999', 'n': N90_ROWS, 'used': 'through-the-cycle check only'})
SOURCES.append({'name': 'SBA 7(a) change-of-ownership loans FY2018-26 (clean extract of the 2026-06-30 FOIA files)', 'url': 'built by /tmp/claude-0/data5/sba_foia/_scripts/02_extract.py',
                'file': CHOW, 'sha256': SHA[CHOW][:16], 'years': 'approved 2017-12-08 to 2026-06-30', 'n': '%d rows; %d in the hazard sample' % (CHOW_ROWS, N_CHOW),
                'used': 'target margins (band, sector, Express, franchise, term class), CHOW CIF96 and S96, band centres, term mix, real-estate note'})
SOURCES.append({'name': 'Fed H.15 bank prime, daily', 'url': 'https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip', 'file': PRIME,
                'sha256': SHA[PRIME][:16], 'years': 'to 2026-10-02', 'n': int(len(pr)), 'used': 'month-start prime of the CHOW filter (13 CFR 120.214(c))'})
SOURCES.append({'name': 'Snapshot index.html (HEAD 56ba230) and the FY2024-26 book fixture', 'url': 'local read-only snapshot', 'file': SNAP_HTML + ' ; ' + BOOK,
                'sha256': SHA[SNAP_HTML][:16] + ' ; ' + SHA[BOOK][:16], 'years': 'FY2024-26 book', 'n': CON['book']['n'],
                'used': 'MODELS.risk (current values) and fitRisk through ' + HARNESS + ' (sha256 ' + SHA[HARNESS][:16] + ')'})

README_ROW = ('| `risk.tail` (`tail_factor` 1.1989 -> **%.2f**, SE 0.0822 (judgment) -> **%.2f** (the measured parts in quadrature, %.3f; %.3f without the drift '
              'part, a lower bound): CIF(120)/CIF(96) of FY2010-15 7(a) term loans raked to the change-of-ownership book on band, sector, SBA Express, franchise '
              'and term class, startups excluded; charged-off loans classed by their rewritten term (long if over 120 months, %.1f%% right on known terms); '
              'midpoint of the two-class (%.3f) and three-class (%.3f) matches; age-period hazards at constant 2023-26 conditions %.3f. Band table: the same '
              'estimator per loan band, %s at centres $%s-$%s, x scale %.4f, applied by tailAt(loan) in fitRisk (base_cif.term = h96 x book_tail %.4f); late-hazard '
              'table by term class (2023-26: 10-year notes %.1f-%.1f%%, notes longer than 10 years %.1f-%.1f%%) replaces the "25-year terms" note; replacement '
              'text for the real-estate note (business-only notes of 10 years or less: %s the 8-year charge-off of all notes their size)) '
              '| `sba_tail_factor.py` (writes `RESULT.json`, tables and a cache of the matched loan table to `/tmp/claude-0/fit6/out/sba_tail_factor/`; '
              'runs the model and tailAt through the harness) | SBA 7(a) FOIA as of 2026-06-30 (FY2000-present files) matched loan by loan to the 2023-09-30 snapshot '
              '(CSIS mirror); the change-of-ownership extract `sba7a_chow_loans_fy2018_2026.csv` | as `sba_risk_refresh.py`, plus '
              '`curl -LO https://raw.githubusercontent.com/CSISdefense/Vendor/HEAD/Data_Raw/Assistance/SBA/foia-7afy2020-present-asof-230930.csv` '
              '(likewise `foia-7afy2010-fy2019-asof-230930.zip`, `foia-7afy2000-fy2009-asof-230930.zip`, `foia-7afy1991-fy1999-asof-230930.zip`) |' % (
                  FACTOR, FACTOR_SE, SE_TOTAL, SE_LOWER, 100 * RULEA['accuracy'], S2['ratio'], S3['ratio'], AP['2023-26']['tail'],
                  ' / '.join('%.3f' % x for x in BAND_R), '{:,.0f}'.format(CENTRES_R[0] / 1e3) + 'k', '{:,.2f}'.format(CENTRES_R[-1] / 1e6) + 'M', KAPPA,
                  BOOK_TAIL, 100 * q120_lo, 100 * q120_hi, 100 * qlong_lo, 100 * qlong_hi, _bl_txt))

RES = {
    'name': 'sba_tail_factor', 'js_key': 'tail', 'js_target': 'MODELS.risk.tail', 'script': SCRIPT, 'asof': '2026-10-14', 'tier': 'fitted', 'round': 3,
    'js_table': JS, 'js_line': 'MODELS.risk.tail=' + JS_LINE + ';', 'js_code': JS_CODE,
    'shipped': SHIPPED, 'recommendation': RECOMMEND, 'replacement_text': REPLACEMENT_TEXT, 'checks': CHECKS, 'sources': SOURCES, 'not_shipped': NOT_SHIPPED,
    'open_issues': OPEN,
    'parameters': {'bands': BLAB, 'band_edges': BANDS[1:-1], 'standard_terms': STD, 'sectors': SECT_KEEP + ['mfg', 'retail', 'transp', 'oth'],
                   'b_age_period': B_AP, 'b_clean_window': B_LAND, 'seeds': [SEED_AP, SEED_LAND, SEED_SPLIT, SEED_RE], 'decision': DECISION,
                   'real_estate_bands': [x[0] for x in LBANDS], 'real_estate_standard_terms': STD_RE,
                   'rounding': 'factor and its SE half away from zero to 0.01; band ratios, SEs and se_total to 0.001; scale to 0.0001; centres to $1,000; '
                               'book_tail to 0.0001; RESULT floats to 6 decimals'},
    'data': {'loan_table': {'rows_2026': LMETA['rows_2026'], 'rows_2023': LMETA['rows_2023'], 'duplicate_key_share': [LMETA['dup_share_2026'], LMETA['dup_share_2023']],
                            'match_rate_by_fy': LMETA['match_rate_by_fy'], 'term_loans_resolved_or_open': LMETA['n_term_loans_resolved_or_open']},
             'chow': CHOW_PROFILE, 'chow_n_with_approval_date_prime': N_CHOW_APPROVAL_DATE_PRIME,
             'cache': 'the matched term-loan table (2026 FOIA loans with their 2023 term and status) is cached at %sloans_matched.pkl with a meta file holding the sha256 of the six raw inputs; it is rebuilt when any input changes or with --rebuild' % CACHE},
    'estimates': {'specs': {k: {kk: vv for kk, vv in v.items() if kk != 'jk_leave_out'} for k, v in SPEC.items()},
                  'midpoint': {'ratio': MID, 'se_jk': MID_SE, 'by_vintage': MID_BYV},
                  'windows': WIN, 'raking': RAKE_DIAG,
                  'age_period': {'n': AP_N, 'tails': {k: v['tail'] for k, v in AP.items()}, 'cells_2023_26': AP['2023-26']['cells'], 'subsets_2023_26': AP_SUB,
                                 'boot_se': AP_SE, 'boot_ci95': AP_CI, 'n_boot': B_AP, 'boot_failures': AP_BOOT_FAIL, 'reference_year': AP_CAL0, 'merged_first_year': AP_MERGED,
                                 'own_calendar_path': AP_PATH,
                                 'calendar_effects': {k: {str(c): float(par[k].get('c%d' % c, 0.0)) for c in cals} for k in ['co', 'pif']}},
                  'se_build_up': {'parts': SE_PARTS, 'total': SE_TOTAL, 'shipped': FACTOR_SE, 'lower_bound_no_drift': SE_LOWER, 'alternatives': SE_ALT,
                                  'recent_midpoint_FY2013_16': REC_MID}},
    'band': {'shipped_main_estimator': BAND_MAIN, 'research_table': BAND, 'centres_geomean': CENTRES, 'centres_median': [CHOW_PROFILE['centre_median'][b] for b in BLAB],
             'gradient': {'top_minus_bottom': GRAD, 'se': GRAD_SE, 'z': GRAD_Z, 'top_minus_next': TOP_DIP, 'top_minus_next_se': TOP_DIP_SE,
                          'research_table_top_minus_bottom': GRAD_RT, 'research_table_z': GRAD_RT_Z},
             'oos_shipped': OOS, 'oos_research_table': OOS_RT, 'omega_band_weights': OMEGA.tolist(), 'aggregates': BAND_AGG, 'scale': KAPPA,
             'current_construction_rebuilt': {'value': SHIP_REBUILT, 'by_band': SHIP_BANDS}},
    'transport': {'decomposition_mature_FY2010_15': DEC, 'chow': DECC, 'q_vs_ratio': QT, 'proportionality': PROP},
    'clean_window': CLEAN, 'clean_window_flatness': FLAT, 'rule_a_validation': RULEA, 'rewrite': REWRITE,
    'real_estate': {'share_term_over_120m': RE_SHARE, 'standard_term_share': RE_STD, 'by_term_class': REAL},
    'through_cycle': {'FY2000_16_ge150k': CYC, 'FY1991_99_ge150k_2023_snapshot': CYC90},
    'console': CON, 'console_effect': EFFECT, 'js_check': {'diff': JS_DIFF, 'rel_mean_book': REL_MEAN},
    'readme_row': README_ROW,
    'reproducibility': 'python3 -I %s twice: RESULT.json byte-identical (seeds %d, %d, %d and %d; floats rounded to 6 decimals; no timestamps)' % (
        SCRIPT, SEED_AP, SEED_LAND, SEED_SPLIT, SEED_RE)}
RES = clean(RES, 6)
open(OUT + 'RESULT.json', 'w').write(json.dumps(RES, indent=1))
open(OUT + 'js_table.json', 'w').write(json.dumps(JS, indent=1))

# tables
pd.DataFrame([{'spec': k, **{kk: vv for kk, vv in v.items() if kk not in ('by_vintage', 'jk_leave_out')}} for k, v in SPEC.items()]).round(6).to_csv(OUT + 'specs_FY2010_15.csv', index=False)
pd.DataFrame([{'band': b, 'centre': CENTRES_R[i], 'shipped': BAND_R[i], 'applied': KAPPA * BAND_R[i], 'se': BAND_SE_R[i], 'se_total': BAND_SE_TOTAL[i],
               'main_two_class': BAND_MAIN[b]['two_class'], 'main_three_class': BAND_MAIN[b]['three_class'], 'main_midpoint': BAND_MAIN[b]['midpoint'],
               'main_midpoint_se': BAND_MAIN[b]['midpoint_se'], 'main_cif96': BAND_MAIN[b]['cif96'], 'research': BAND[b]['ratio'], 'research_se_jk': BAND[b]['se_jk'],
               'unmatched': BAND[b]['unmatched_ratio'], 'q_transport': QT['all']['by_band'][b]['band_tail_q_transport'],
               **{'main_v%d' % v: OOS['by_vintage'][v][i] for v in OOS['by_vintage']}, **{'research_v%d' % k: v for k, v in BAND[b]['by_vintage'].items()}}
              for i, b in enumerate(BLAB)]).round(6).to_csv(OUT + 'band_tails.csv', index=False)
_cw_rows = [{'band': b, 'class': c, 'allocated': False, **{k: v for k, v in CROWS[b][c].items()}} for b in BLAB + ['all'] for c in CROWS[b] if isinstance(CROWS[b][c], dict)]
_cw_rows += [{'band': b, 'class': c, 'allocated': True, 'n': v['n_eff'], 'late_co': v['late_co_eff'], 'q': v['q'], 'q_se': v['q_se'], 'se_loans': v['se_loans'],
              'se_split': v['se_split']} for b in BLAB + ['all'] for c, v in ALLOC[b].items()]
pd.DataFrame(_cw_rows).round(6).to_csv(OUT + 'clean_window_q.csv', index=False)
pd.DataFrame([{'band': b, 'class': c, **v} for b in BLAB + ['all bands'] for c, v in DEC[b].items()]).round(6).to_csv(OUT + 'decomposition_mature.csv', index=False)
pd.DataFrame(EFFECT).round(6).to_csv(OUT + 'console_effect.csv', index=False)
pd.DataFrame([{'fy': k, **v} for k, v in list(CYC90.items()) + list(CYC.items())]).round(6).to_csv(OUT + 'through_cycle.csv', index=False)
pd.DataFrame([{'band': k, 'share_term_over_120m': RE_SHARE.get(k), **{'%s_%s' % (cn, kk): vv for cn in ['all', 'business_length', 'long'] for kk, vv in v[cn].items()},
               'bl_over_all': v['bl_over_all'], 'bl_over_all_se': v['bl_over_all_se'], 'long_over_all': v['long_over_all'], 'long_over_all_se': v['long_over_all_se']}
              for k, v in REAL.items()]).round(6).to_csv(OUT + 'real_estate_by_term.csv', index=False)
say('\nwrote %sRESULT.json (%d bytes); %.0f s' % (OUT, os.path.getsize(OUT + 'RESULT.json'), time.time() - T0))
