#!/usr/bin/env python3
"""Intervention costs (MODELS.fitted.interventions): the sell-side quality-of-earnings cost, the hire-a-GM employer-cost
loading and one-time hire cost, and the add-sales-capacity cost floor by industry. October 2026, third round.

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/intervention_costs.py          (about 1.5 min; needs node and pdftotext)
Out:  /tmp/claude-0/fit6/out/intervention_costs/RESULT.json (key js_table = MODELS.fitted.interventions; js_line = the
      exact line to embed; js_code = the page code that reads the table, run in node on the snapshot), js_line.txt,
      qoe_tiers.csv, qoe_loso.csv, qoe_sensitivity.csv, ecec_cells.csv, growth_floor.csv, console_checks.csv,
      console_costs.csv, quotes.csv
      Scratch (the node probes, their configs and their outputs): /tmp/claude-0/fit6/work/fit3-intervention_costs/
      The snapshot and the downloads are only read; nothing in the repo or the snapshot is written.
      The second round is kept as intervention_costs.v2.py and /tmp/claude-0/fit6/out/intervention_costs.v2/.

Third round: the analyst's decisions on the round-2 review
  1. Loadings (blocking). ECEC is a cost per hour WORKED: its wages and salaries leave out pay for leave, which ECEC
     counts as a benefit (paid leave). gmSalary and the OEWS wages are annual salaries (hourly x 2080) that already
     include leave pay, so an employer's annual cost is salary x TC/(W + PL), not salary x TC/W: round 2 counted paid
     leave twice. Every loading, its size scaling, range, alternatives and SE are recomputed on that basis (GM 1.38 ->
     1.24, sales 1.328 -> 1.232), and the paid-leave and supplemental-pay cells are stored in the table.
  2. GM use. The console's structure is kept: one year's salary as the cost, now loaded, plus the one-time hire
     (cost = hire_cost + loading x gmSalary; earnings charge = -loading x gmSalary). The research round's pre-sale
     payroll alternative (210 days less SHRM's 45-day executive time-to-fill = 165 days) is recorded as a check.
  3. Growth floor: tier AGGREGATE (a measured wage through a stated judgment bridge). One sales hire at the OEWS
     MEDIAN wage of the industry's sales occupations (not the mean) x ECI x the corrected sales loading x the payroll
     days 270 - 44 (SHRM non-executive time-to-fill) = 226, + the $1,200 hire. The SE covers the bridge choices (mean
     against median, payroll days) and the proxy cells; vet and rest are flagged as weak proxies.
  4. QoE ships unchanged (floor, share, cluster-bootstrap SEs). No tier's revenue midpoint is below $1.43M, so the
     floor's level for the smallest businesses is the form's extrapolation; the table says so. The livmo $5M-$100M
     tier is coded generic (the page gives both its tiers as generic pricing); the side-dependent results (sell-only
     and sell + generic subsets, side-dummy power curve, sell-side days) are rerun; the pooled fit and its SEs do not
     depend on the side and are unchanged (tested). Replication checks keep the research round's coding.

Why
  INTERV (index.html) prices the pre-sale interventions by hand (AUDIT.md, "What remains judgment"). Three of its costs
  have a measured counterpart (research round: /tmp/claude-0/fit6/research/H-interv-cats-conf.md):
  - qoe, "Commission a sell-side quality of earnings": cost max(22000, .0045 x revenue). QoE providers and M&A advisors
    publish fee schedules by deal size; 33 tiers from 15 independent sources identify both the floor and the share.
    They are list prices, a published benchmark, not invoices: tier AGGREGATE.
  - gm, "Hire or promote a general manager": cost and earnings charge = gmSalary(s), the OEWS wage, which is wages and
    salaries only (gmSalary's own comment; fit/README lists an ECEC-based employer-cost loading as an open follow-up).
    BLS ECEC June 2026 measures the employer's total cost per dollar of annual salary (wages plus paid leave): FITTED
    (official data on the same quantity). An outside hire also costs a search: SHRM's 2025 median executive
    cost-per-hire (AGGREGATE).
  - growth, "Add sales capacity to lift growth": cost max(55000, .022 x revenue). The floor is the cost of one added
    salesperson for the programme's 270 days through a stated judgment bridge (one hire, at the industry's median
    sales-rep wage, on payroll once hired): measured wages, loading, time-to-fill and hire cost, AGGREGATE, per
    industry. The .022 share would need rep productivity in small businesses, which is unpublished: it stays judgment.
  Everything else in INTERV stays judgment; what the research round found on it is recorded as checks.

What it does
  0. Sources. sha256 of every input. The fee tiers and the SHRM, Firmex, Bridge Group, GF Data, SBA, ContractsCounsel
     and SOP figures are documented constants below (source, file, page); step 0 confirms each one against its saved
     page (visible text, html.parser) or the PDF's text layer (pdftotext -layout, the system poppler tool; nothing
     from a download is run or imported) and writes the outcome to quotes.csv. The ECEC cells are parsed from the
     saved BLS tables. The snapshot's index.html is read for the current INTERV values and MODELS.fitted.gm_wage.
  1. QoE cost. Each tier has a size basis (revenue, enterprise value or EBITDA) with bounds, a fee range and a side
     (sell / buy / generic, as the page presents the price). EV and EBITDA bounds are converted to revenue with the
     console's own maps (node, the harness, the frozen snapshot): for a peer-median business (soft inputs at their size
     medians, gm/grw/rec/ret at the IND values, cc .16, plt .40) at revenue SDE / typMargin, model value V and
     EBITDA = SDE / sdeEbitdaWedge, each the median over the 16 industries on log10 SDE 4.3 ... 7.0, interpolated in
     logs (linear in logs past the ends). Open tiers: "under $X" starts at X/10 (at least $250k), "over $X" ends at
     3X, "from $F" means F to 1.5F. Each tier enters at its geometric midpoints of revenue and fee; tiers outside
     $250k-$60M of revenue are dropped. Fit: log fee = log max(F, s x revenue), weighted least squares with each
     source weighing 1 in total, solved exactly (for a given kink the loss is a quadratic in log kink; the minimum is
     taken interval by interval). SE: cluster bootstrap over sources (B = 2000): each draw of a source is its own
     cluster of weight 1, so a source drawn twice weighs 2. The research round's bootstrap re-weighted every resampled
     source back to 1 whatever its multiplicity, which understates the spread; it is reproduced as a check, not
     shipped. Leave one source out; constant conversions (EV/revenue 0.5-1.0, EBITDA/revenue 0.12-0.25); sell-side
     tiers only; sell + generic; tiers with revenue midpoints $1M-$20M; buy-side fees x1.2 (BD Emerson: sell-side work
     runs 10-30% above buy-side). Functional form: a power curve log fee = a + b log(rev/$5M) (+ side dummies), and
     the leave-one-source-out prediction error of each form. Days (60): report turnaround per source (one vote each,
     sell-side preferred). Shipped: F to $100, s to 0.0001 (the analyst's rounding).
  2. GM. ECEC June 2026 (news-release tables 4 and 6; relative standard errors from the RSE tables of the same release).
     Per cell, the annual-salary loading TC/(W + PL): total compensation over wages and salaries plus paid leave, all
     per hour worked. Loading = that of management, professional and related occupations x the ratio of
     establishments of 1-49 workers to all private establishments (ECEC publishes no occupation-by-size cell):
     78.88/(54.06+7.37) x [37.64/(27.88+2.34)] / [46.89/(32.82+3.54)] = 1.284 x 0.966 = 1.24. Range 1.18-1.28: the
     management ratio without supplemental pay (overtime, nonproduction bonuses, which OEWS wages exclude) with the same
     size scaling, and the management ratio at all sizes; management, business and financial occupations (the GM's own
     group) give 1.25. Sampling SE from the RSEs: per cell L = 1 + B'/D with D = W + PL and B' = B - PL (supplemental
     pay, insurance, retirement, legally required), so d ln L = (B'/TC)(d ln B' - d ln D); W, PL and B' are taken as
     independent, so SE(D)^2 = SE(W)^2 + SE(PL)^2 and SE(B')^2 = SE(B)^2 - SE(PL)^2 (published SEs only), and so are
     the three cells (an upper bound when they correlate positively, as overlapping cells do). One-time hire: SHRM
     2025 median executive cost-per-hire $10,625 (no SE published; the 2022-25 change, $1,875, is stored as a judgment
     SE). Use: cost = hire + loading x gmSalary (one year's salary, the console's structure); earnings charge =
     -loading x gmSalary. Checks: the console's GM value effect with the earnings charge scaled by L = 1 (as shipped),
     the range ends, the GM's own group, round 2's 1.38 and the research round's 1.35 and 1.48, for peer-median
     businesses at SDE $300k / $700k / $2.5M and the framework example (node, the research round's override of the gm
     line); the GM's cost now, as shipped and under the 165-payroll-day alternative.
  3. Growth floor. Per console industry, the OEWS May 2025 national industry cell (SALES_CELL; the proxies for vet,
     rest, wash, medical and ecom are stated in SALES_NOTE): sales representatives SOC 41-3091, 41-4011 and 41-4012,
     pooled by employment (a suppressed employment, '**', enters with weight 50: judgment). Wage: the MEDIAN of the
     pooled distribution. Each occupation's CDF runs through its published 10th-90th percentiles, linear in log wage
     (extended linearly past the ends, held to 0..1), and the employment-weighted mixture is solved for 1/2. Cost =
     median x the ECI factor to 2026Q2 (MODELS.fitted.gm_wage.wage_growth_alt_all_private, read from the snapshot) x
     the ECEC loading of sales and related occupations 35.85/(26.99+2.11) x (270 - 44)/365 + SHRM's non-executive
     cost-per-hire ($1,200). SE, the root sum of squares of: sampling (OEWS publishes no percentile SEs: the median's
     relative SE is sqrt(sum_k (omega_k r_k)^2), omega_k = occupation k's share of the pooled density at the median,
     r_k = sqrt(pi/2) x its MEAN_PRSE, sqrt(pi/2) being the large-sample ratio of a median's to a mean's sampling
     error under normality: judgment); the two bridge choices, each half the gap to its alternative (the project's
     rule): the employment-weighted MEAN wage, and 270 payroll days (no time to fill); the proxy, half the gap to the
     alternative cell in SALES_ALT; and the common relative error of the loading and the ECI. Shipped to $100, SEs to
     $10, components stored. Sensitivities: round 2's basis (mean, TC/W, 270 days), no supplemental pay, the loading
     scaled to small establishments as the GM's is, suppressed rows dropped, the employment-weighted mean of the
     occupation medians in place of the pooled median.
  4. Checks that stay judgment (js_table.checks): QoE days; the GF Data effect check beside the console's own QoE value
     effect (node, peer-median businesses); the SBA SOP 50 10 8.1 lender-QoE rule; outreach cost (Firmex); SOP cost;
     contracts (legal drafting only); GM days (SHRM time-to-fill); the GM pre-sale payroll alternative; growth days
     (SHRM + Bridge Group ramp).
  5. Replication of the research round when its files are present (/tmp/claude-0/fit6/work/H-interv-cats-conf): the
     EV/EBITDA map, the QoE fit, its bootstrap, leave-one-out and sensitivities (with the research round's side coding),
     the sales-cost table (its mean-wage, TC/W, 270-day basis) and the console effect tables.
  6. The page code (JS_CODE, stored in RESULT.json) runs in node on the snapshot with the table attached; its costs at
     peer-median businesses must equal this script's. Assertions are stored in RESULT.json (tests); the script exits 1
     after writing if any fails.

Data and fetch (each download in its own new directory; read with python3 -I; the paths are constants below)
  QoE price pages: /tmp/claude-0/fit6/data/H-interv-cats-conf/<dir>/page.html, one directory per page (the URL of each
     tier is in TIERS), fetched with curl and a browser User-Agent in October 2026.
  BLS ECEC June 2026 (2026 Q02 results), private industry:
     H-interv-cats-conf/bls_ecec/ecec.t04.htm   https://www.bls.gov/news.release/ecec.t04.htm
     H-interv-cats-conf/bls_ecec/ecec.t06.htm   https://www.bls.gov/news.release/ecec.t06.htm
     fit2-intervention_costs/bls_ecec_rse/ecec-rse.htm  https://www.bls.gov/web/ecec/ecec-rse.htm
     fit2-intervention_costs/bls_ecec_tn/ecec.tn.htm    https://www.bls.gov/news.release/ecec.tn.htm (sample size)
     These URLs serve the latest quarter; after the next release take the June 2026 tables from the release archive
     (https://www.bls.gov/bls/news-release/ecec.htm). BLS answers 403 without a descriptive User-Agent:
     curl -A 'your-project/1.0 (contact)' -H 'Accept: */*' -H 'Accept-Language: en-US' -H 'Accept-Encoding: gzip, deflate, br' --compressed -O <url>
  BLS OEWS May 2025, national industry-specific: /tmp/claude-0/data5/bls_oews/raw/oesm25in4/{natsector,nat3d,nat4d,
     nat5d_6d}_M2025_dl.xlsx from https://www.bls.gov/oes/special-requests/oesm25in4.zip (same headers)
  SHRM 2025 Recruiting Executives Benchmarking (data brief): H-interv-cats-conf/shrm_2025_recruiting/report.pdf
     https://www.shrm.org/content/dam/en/shrm/research/2025-recruiting-benchmarking-report.pdf
  Firmex M&A Fee Guide 2023-24, US: H-interv-cats-conf/firmex_us_2024_pdf/guide.pdf
     https://www.firmex.com/wp-content/uploads/2024/07/Firmex-MAFeeGuide-US.pdf
  Bridge Group SaaS AE Metrics v8.3 (2022): H-interv-cats-conf/bridgegroup_ae_report/report.pdf (bridgegroupinc.com;
     the research round did not record the download URL)
  GF Data via ACG Middle Market Growth (fall 2025): H-interv-cats-conf/gfdata_mmg_qoe_fall2025/page.html
     https://middlemarketgrowth.org/fall-2025-gf-data-quality-of-earnings-reports/
  SBA SOP 50 10 8.1 QoE rule, ContractsCounsel MSA cost, SOP and EOS prices: pages and URLs in SBA_PAGES and CHECK_PAGES.
  Snapshot /tmp/claude-0/fit6snap/index.html (read only); harness /tmp/claude-0/fit6/harness.js (loads the snapshot).
"""
import csv, hashlib, json, math, os, re, subprocess, sys
from html.parser import HTMLParser
import numpy as np
import pandas as pd

OUT = '/tmp/claude-0/fit6/out/intervention_costs'
WORK = '/tmp/claude-0/fit6/work/fit3-intervention_costs'   # round 2's scratch (fit2-...) is left as it was
for _d in (OUT, WORK):
    os.makedirs(_d, exist_ok=True)
SNAP = '/tmp/claude-0/fit6snap/index.html'                 # frozen snapshot, read only
HARNESS = '/tmp/claude-0/fit6/harness.js'                  # loads the snapshot's model section into a sandbox
DH = '/tmp/claude-0/fit6/data/H-interv-cats-conf'          # research-round downloads
DF = '/tmp/claude-0/fit6/data/fit2-intervention_costs'     # this script's downloads (ECEC RSEs and technical note)
ECEC_T04 = DH + '/bls_ecec/ecec.t04.htm'
ECEC_T06 = DH + '/bls_ecec/ecec.t06.htm'
ECEC_RSE = DF + '/bls_ecec_rse/ecec-rse.htm'
ECEC_TN = DF + '/bls_ecec_tn/ecec.tn.htm'
SHRM_PDF = DH + '/shrm_2025_recruiting/report.pdf'
FIRMEX_PDF = DH + '/firmex_us_2024_pdf/guide.pdf'
BRIDGE_PDF = DH + '/bridgegroup_ae_report/report.pdf'
OEWS_DIR = '/tmp/claude-0/data5/bls_oews/raw/oesm25in4'
OEWS_FILES = ['natsector_M2025_dl.xlsx', 'nat3d_M2025_dl.xlsx', 'nat4d_M2025_dl.xlsx', 'nat5d_6d_M2025_dl.xlsx']
OEWS_ZIP = '/tmp/claude-0/data5/bls_oews/raw/oesm25in4.zip'    # provenance only (sha256)
RESEARCH = '/tmp/claude-0/fit6/work/H-interv-cats-conf'     # research outputs: replication checks only (optional)
R_MAP = RESEARCH + '/out/ev_rev_map.json'
R_QOE = RESEARCH + '/v2/out/qoe_fit_v2.json'
R_SALES = RESEARCH + '/v2/out/sales_cost_v2.json'

# ------------------------------------------------------------------------------------------------------------------
# Decisions and judgment constants
# ------------------------------------------------------------------------------------------------------------------
B_BOOT = 2000                    # cluster bootstrap draws (QoE)
SEED = 20261014
QOE_WINDOW = (2.5e5, 6e7)        # tiers whose revenue midpoint falls outside are dropped (research rule)
STEP_FLOOR, STEP_SHARE = 100, 0.0001   # the analyst's rounding of the shipped QoE floor and share
BUY_PREMIUM = 1.2                # sensitivity only: BD Emerson "Expect 10 to 30 percent more than the buy-side"
SUPPRESSED_EMP_WEIGHT = 50.0     # judgment: OEWS employment '**' (not published) enters the wage pool with weight 50
HIRE_SE_JUDGMENT = 10625 - 8750  # judgment SE of the hire cost: SHRM's 2022 -> 2025 change (no SE published)
ECI_REL_SE = 0.0086              # MODELS.fitted.gm_wage.wage_growth_se (economy-wide factor): part of the common error
MEDIAN_SE_FACTOR = math.sqrt(math.pi / 2)   # judgment: a median's sampling SE / a mean's (large sample, normal); OEWS
#                                             publishes MEAN_PRSE only
LOADING_RESEARCH = (1, 1.35, 1.48)          # loadings of the research round's GM value-effect table (replication)
LOADING_ROUND2 = 1.38                       # round 2's shipped GM loading (TC/W), probed for comparison
INDS = ['home', 'medical', 'vet', 'msp', 'saas', 'prof', 'mfg', 'dist', 'ecom', 'staff', 'land', 'wash', 'auto',
        'constr', 'fit', 'rest']

# ------------------------------------------------------------------------------------------------------------------
# QoE price tiers (practitioner list prices). One row per published tier or untiered range ('note': not fitted).
# (source, url, saved page under DH, basis, tier_lo, tier_hi, fee_lo, fee_hi, side, weeks_lo, weeks_hi, quote)
# basis: size measure of the tier bounds; None = open. Labels with a suffix (_b, _sell, ...) belong to the source
# before the underscore. Step 0 checks every quote against the saved page.
# ------------------------------------------------------------------------------------------------------------------
TIERS = [
    ('bdemerson', 'https://www.bdemerson.com/article/quality-of-earnings-report-cost', 'qoe_bdemerson/page.html', 'ev', 0, 5e6, 20000, 35000, 'buy', 4, 6,
     'Under $5M enterprise value. $20,000 to $35,000, usually a limited-scope review rather than a full QoE.'),
    ('bdemerson', 'https://www.bdemerson.com/article/quality-of-earnings-report-cost', 'qoe_bdemerson/page.html', 'ev', 5e6, 15e6, 25000, 50000, 'buy', 4, 6,
     '$5M to $15M. $25,000 to $50,000. One entity, one revenue stream, accrual books.'),
    ('bdemerson', 'https://www.bdemerson.com/article/quality-of-earnings-report-cost', 'qoe_bdemerson/page.html', 'ev', 15e6, 75e6, 45000, 90000, 'buy', 4, 6,
     '$15M to $75M. $45,000 to $90,000.'),
    ('bdemerson_sell', 'https://www.bdemerson.com/article/quality-of-earnings-report-cost', 'qoe_bdemerson/page.html', 'note', None, None, None, None, 'sell', 5, 8,
     'sell-side ... typically five to eight weeks. Expect 10 to 30 percent more than the buy-side'),
    ('etonvs', 'https://etonvs.com/transaction-valuation-advisory/quality-of-earnings-report-cost/', 'qoe_etonvs/page.html', 'rev', 0, 10e6, 25000, 35000, 'generic', 4, 8,
     'small businesses with less than $10 million in revenue typically costs between $25,000 and $35,000. For larger businesses, prices often start at $60,000'),
    ('etonvs', 'https://etonvs.com/transaction-valuation-advisory/quality-of-earnings-report-cost/', 'qoe_etonvs/page.html', 'rev', 10e6, None, 60000, None, 'generic', 4, 8,
     'For larger businesses, prices often start at $60,000 and can reach six figures'),
    ('webacquisition', 'https://webacquisition.com/quality-of-earnings-qoe-report-cost/', 'qoe_webacquisition/page.html', 'ev', 0, 5e6, 5000, 15000, 'buy', 2, 4,
     'For businesses valued under $5 million, most buyers pay somewhere in the $5,000 to $15,000 range when working with boutique firms'),
    ('webacquisition_b', 'https://webacquisition.com/why-qoe-is-needed/', 'qoe_webacq_why/page.html', 'ev', 1e5, 10e6, 10000, 35000, 'buy', 2, 4,
     'For small business acquisitions in the $100,000 to $10 million range, most providers charge between $10,000 and $35,000 for a full QoE report'),
    ('livmo', 'https://livmo.com/blog/how-appraisals-bovs-audits-and-quality-of-earnings-reports-affect-your-business-valuations/', 'qoe_livmo_appraisals/page.html', 'ev', 1e6, 5e6, 5000, 15000, 'generic', 4.3, 6.4,
     'For SMB transactions ($1M-$5M enterprise value), a QoE typically costs $5,000 to $15,000.'),
    ('livmo', 'https://livmo.com/blog/how-appraisals-bovs-audits-and-quality-of-earnings-reports-affect-your-business-valuations/', 'qoe_livmo_appraisals/page.html', 'ev', 5e6, 100e6, 20000, 50000, 'generic', 4.3, 6.4,
     'For lower middle market deals ($5M-$100M), expect $20,000 to $50,000 from a boutique firm and $50,000+ from national firms.'),
    ('livmo_b', 'https://livmo.com/blog/quality-of-earnings-report-business-sale/', 'qoe_livmo/page.html', 'rev', 0, 10e6, 20000, 35000, 'generic', 4.3, 6.4,
     'Small businesses under $10M revenue: $20K-$35K. Companies above $25M revenue: $40K-$100K+ ... take 30 to 45 days'),
    ('livmo_b', 'https://livmo.com/blog/quality-of-earnings-report-business-sale/', 'qoe_livmo/page.html', 'rev', 25e6, None, 40000, 100000, 'generic', 4.3, 6.4,
     'Companies above $25M revenue: $40K-$100K+'),
    ('clearlyacquired', 'https://www.clearlyacquired.com/quality-of-earnings', 'qoe_clearlyacquired/page.html', 'rev', 0, 5e6, 15000, 40000, 'generic', 2, 4,
     'Main Street | Under $5M revenue | $15,000 - $40,000'),
    ('clearlyacquired', 'https://www.clearlyacquired.com/quality-of-earnings', 'qoe_clearlyacquired/page.html', 'rev', 5e6, 50e6, 35000, 75000, 'generic', 2, 4,
     'Lower Middle Market | $5M - $50M revenue | $35,000 - $75,000'),
    ('clearlyacquired', 'https://www.clearlyacquired.com/quality-of-earnings', 'qoe_clearlyacquired/page.html', 'rev', 50e6, 250e6, 75000, 150000, 'generic', 2, 4,
     'Middle Market | $50M - $250M revenue | $75,000 - $150,000'),
    ('ctacq', 'https://ctacquisitions.com/?p=1636', 'qoe_ctacq_sellside/page.html', 'ebitda', 0, 1e6, 10000, 15000, 'sell', 8, 12,
     'EBITDA below $1M ... an Agreed-Upon Procedures (AUP) engagement at $10,000 to $15,000'),
    ('ctacq', 'https://ctacquisitions.com/?p=1636', 'qoe_ctacq_sellside/page.html', 'ebitda', 5e6, 25e6, 25000, 75000, 'sell', 8, 12,
     'For a $5M to $25M EBITDA business, a sell-side QoE costs roughly $25,000 to $75,000 ... median engagement landing near $45,000'),
    ('eightx', 'https://eightx.co/blog/qofe-what-buyers-scrutinize', 'qoe_eightx/page.html', 'rev', 10e6, None, 15000, 40000, 'sell', None, None,
     'At roughly $10M-plus ... A streamlined review runs around $15K to $40K'),
    ('buyxbuild', 'https://buyxbuild.beehiiv.com/p/quality-earnings-report-get-one', 'qoe_buyxbuild/page.html', 'ev', 5e5, 5e6, 15000, 30000, 'buy', None, None,
     "For SMB acquisitions, I've seen it run in the range of $15-30k"),
    ('peakbv', 'https://peakbusinessvaluation.com/?p=34748', 'qoe_peakbv/page.html', 'note', None, None, 10000, None, 'generic', 2, 6,
     'generally costs between $10,000 for smaller businesses to several hundred thousand dollars'),
    ('burkland', 'https://burklandassociates.com/?p=9465', 'qoe_burkland/page.html', 'note', None, None, 30000, 50000, 'sell', None, None,
     "many of the sell-side QoEs we've seen are in the $30-$50K range"),
    ('aegislaw', 'https://aegislaw.com/quality-of-earnings-report-ma/', 'qoe_aegislaw/page.html', 'note', None, None, 40000, 150000, 'generic', 4, 8,
     'typically runs from forty thousand to one hundred fifty thousand dollars'),
    ('searchfunder', 'https://searchfunder.com/post/quality-of-earnings-qoe-for-small-medium-deals', 'qoe_searchfunder/page.html', 'ev', 10e6, 50e6, 40000, None, 'generic', None, None,
     "full scope QoE's for deals between $10-50M ... without paying a $40K+ price tag"),
    ('breakwater', 'https://www.breakwaterma.com/blog/quality-of-earnings-report-cost', 'qoe2_breakwater/page.html', 'ebitda', 0, 1e6, 10000, 25000, 'generic', None, None,
     'Sub-$1M EBITDA businesses: $10,000-$25,000'),
    ('breakwater', 'https://www.breakwaterma.com/blog/quality-of-earnings-report-cost', 'qoe2_breakwater/page.html', 'ebitda', 1e6, 3e6, 15000, 40000, 'generic', None, None,
     '$1M-$3M EBITDA businesses: $15,000-$40,000'),
    ('breakwater', 'https://www.breakwaterma.com/blog/quality-of-earnings-report-cost', 'qoe2_breakwater/page.html', 'ebitda', 3e6, 10e6, 25000, 75000, 'generic', None, None,
     '$3M-$10M EBITDA businesses: $25,000-$75,000'),
    ('breakwater', 'https://www.breakwaterma.com/blog/quality-of-earnings-report-cost', 'qoe2_breakwater/page.html', 'ebitda', 10e6, 25e6, 50000, 150000, 'generic', None, None,
     '$10M-$25M EBITDA businesses: $50,000-$150,000'),
    ('breakwater_sell', 'https://www.breakwaterma.com/blog/quality-of-earnings-report-cost', 'qoe2_breakwater/page.html', 'rev', 5e6, 50e6, 15000, 35000, 'sell', None, None,
     'For businesses in the $5M-$50M revenue range, a sell-side QoE typically runs $15,000-$35,000'),
    ('investmentbank', 'https://investmentbank.com/insights/sell-side-vs-buy-side-quality-of-earnings-timing', 'qoe2_investmentbank/page.html', 'ebitda', 0, 3e6, 15000, 25000, 'sell', 4, 6,
     '2026 QoE fees typically run $15,000 to $25,000 for businesses under $3 million of EBITDA'),
    ('investmentbank', 'https://investmentbank.com/insights/sell-side-vs-buy-side-quality-of-earnings-timing', 'qoe2_investmentbank/page.html', 'ebitda', 3e6, 10e6, 25000, 50000, 'sell', 4, 6,
     '$25,000 to $50,000 for the $3–10 million band'),
    ('investmentbank', 'https://investmentbank.com/insights/sell-side-vs-buy-side-quality-of-earnings-timing', 'qoe2_investmentbank/page.html', 'ebitda', 10e6, None, 50000, 75000, 'sell', 4, 6,
     '$50,000 to $75,000-plus above $10 million, with a standard four-to-six-week turnaround'),
    ('icon', 'https://iconbusinessadvisors.com/quality-of-earnings-report/', 'qoe2_icon/page.html', 'ev', 5e6, 50e6, 25000, 50000, 'sell', None, None,
     'For lower middle market businesses ($5M-$50M in enterprise value), sell-side QoE reports typically cost $25K-$50K'),
    ('greenwich', 'https://greenwichgp.com/2022/01/11/is-a-sell-side-quality-of-earnings-worth-it/', 'qoe2_greenwich/page.html', 'note', None, None, 40000, 200000, 'sell', None, None,
     'Sellers in the lower middle market can typically expect to spend roughly $40,000 to $200,000 on this analysis'),
    ('systemsix', 'https://systemsix.com/what-does-a-quality-of-earnings-report-cost-pricing-by-deal-size/', 'qoe2_systemsix/page.html', 'ev', 0, 5e6, 10000, 20000, 'generic', None, None,
     'Typically $10,000–$20,000 for a QoE Lite scope on deals under $5M'),
    ('systemsix_full', 'https://systemsix.com/what-does-a-quality-of-earnings-report-cost-pricing-by-deal-size/', 'qoe2_systemsix/page.html', 'note', None, None, 25000, 50000, 'generic', None, None,
     '$25,000–$50,000 for a full-scope report from a boutique firm on typical lower-middle-market deals'),
    ('bedrock', 'https://www.bedrockqoe.com/insights/quality-of-earnings-report-cost', 'qoe2_bedrock/page.html', 'ev', 1e6, 3e6, 5000, 8000, 'buy', 2, 2,
     '$1M - $3M | $5,000 - $8,000 | 2 weeks'),
    ('bedrock', 'https://www.bedrockqoe.com/insights/quality-of-earnings-report-cost', 'qoe2_bedrock/page.html', 'ev', 3e6, 5e6, 6000, 10000, 'buy', 2, 3,
     '$3M - $5M | $6,000 - $10,000 | 2-3 weeks'),
    ('bedrock', 'https://www.bedrockqoe.com/insights/quality-of-earnings-report-cost', 'qoe2_bedrock/page.html', 'ev', 5e6, 10e6, 8000, 15000, 'buy', 2, 3,
     '$5M - $10M | $8,000 - $15,000 | 2-3 weeks'),
    ('bedrock', 'https://www.bedrockqoe.com/insights/quality-of-earnings-report-cost', 'qoe2_bedrock/page.html', 'ev', 10e6, 30e6, 12000, 25000, 'buy', 3, 4,
     '$10M - $30M | $12,000 - $25,000 | 3-4 weeks'),
    ('bedrock_regional', 'https://www.bedrockqoe.com/insights/quality-of-earnings-report-cost', 'qoe2_bedrock/page.html', 'ev', 3e6, 10e6, 20000, 35000, 'buy', None, None,
     'you are still looking at $20,000 to $35,000 for a deal in the $3M to $10M range'),
    ('tnma', 'https://www.tnma.com/blog/sell-side-quality-of-earnings-report-guide/', 'qoe2_tnma/page.html', 'note', None, None, 25000, 75000, 'sell', None, None,
     'A QoE for lower middle market companies usually ranges from $25,000 to over $75,000'),
    ('morganwestfield', 'https://morganandwestfield.com/knowledge/quality-of-earnings-in-ma/', 'qoe2_morganwestfield/page.html', 'rev', 0, 10e6, 10000, 20000, 'generic', None, None,
     'If you own a company with less than $10 million in revenue and relatively simple operations, you can probably spend as little as $10,000 to $20,000'),
    ('papermark', 'https://www.papermark.com/blog/quality-of-earnings', 'qoe2_papermark/page.html', 'note', None, None, 25000, 50000, 'sell', 3, 5,
     '$25,000 to $50,000 | 3 to 5 weeks'),
    ('papermark_large', 'https://www.papermark.com/blog/quality-of-earnings', 'qoe2_papermark/page.html', 'note', None, None, 30000, 100000, 'sell', 4, 8,
     '$30,000 to $100,000 | 4 to 8 weeks'),
]
# The research round (and round 2) coded livmo's $5M-$100M tier 'sell'. The page gives both livmo tiers as generic pricing
# (an FAQ answer, followed by "The buyer almost always commissions their own QoE"), so TIERS codes it generic; this
# override restores the research coding for the replication checks only. (label, tier_lo, tier_hi) -> side
RESEARCH_SIDE = {('livmo', 5e6, 100e6): 'sell'}

# ------------------------------------------------------------------------------------------------------------------
# ECEC cells (parsed from the saved tables; the names are BLS row labels, first occurrence in the private-industry block).
# ECEC costs are per hour WORKED: wages and salaries (W) leave out pay for leave, which is the paid-leave benefit (PL).
# An annual salary (gmSalary, OEWS: hourly x 2080) includes leave pay, so the annual-salary loading is TC/(W + PL).
# ------------------------------------------------------------------------------------------------------------------
ECEC_CELLS = {'private': (4, 'Private industry workers'), 'mgmt_prof': (4, 'Management, professional, and related occupations'),
              'mgmt_bus_fin': (4, 'Management, business, and financial occupations'), 'sales': (4, 'Sales and related occupations'),
              'all_sizes': (6, 'All workers'), 'est_1_49': (6, '1-49 workers'), 'est_50_99': (6, '50-99 workers'),
              'est_1_99': (6, '1-99 workers'), 'est_100_499': (6, '100-499 workers'), 'est_500_plus': (6, '500 workers or more')}
# (total compensation, wages and salaries, paid leave) as the decisions quote them; step 2 asserts the parsed cells equal them
ECEC_DECIDED = {'mgmt_prof': (78.88, 54.06, 7.37), 'est_1_49': (37.64, 27.88, 2.34), 'private': (46.89, 32.82, 3.54),
                'sales': (35.85, 26.99, 2.11)}

# ------------------------------------------------------------------------------------------------------------------
# SHRM 2025 Recruiting Executives Benchmarking data brief (12 pages; PDF page = printed page). Medians.
# ------------------------------------------------------------------------------------------------------------------
SHRM = {'exec_cph_2025': 10625, 'exec_cph_2022': 8750, 'exec_cph_2017': 5000,      # p.6 chart "Executive and
        'nonexec_cph_2025': 1200, 'nonexec_cph_2022': 1244, 'nonexec_cph_2017': 1633,  #  Nonexecutive Cost-per-Hire"
        'exec_ttf_2025': 45, 'exec_ttf_2022': 60, 'nonexec_ttf_2025': 44, 'nonexec_ttf_2022': 44,   # p.8 chart, days
        'n_respondents': 2371, 'small_org_exec_external_pct': 100}                 # p.4 methodology; p.9 chart
# Bridge Group SaaS AE Metrics v8.3 (2022; 47 pages; PDF page index): p.2 253 companies, p.24 ramp 5.3 months,
# p.31 median ACV quota $740K, p.33 66% of reps at quota, p.35 median OTE $167K.
BRIDGE = {'n_companies': 253, 'ramp_months': 5.3, 'quota_acv': 740000, 'reps_at_quota': 0.66, 'median_ote': 167000}
# Firmex M&A Fee Guide 2023-24, US edition (survey December 2023, 189 US respondents; p.4). Shares (%) of respondents,
# first the 2023 survey then 2022, read from the bar labels of p.15 (most common monthly engagement/work/retainer fee)
# and p.16 (most common fixed (lump-sum) fee); step 0 checks both sequences in the page's text layer.
FIRMEX_N = 189
FIRMEX_MONTHLY = [('<$5K', 0, 5000, 17, 17), ('$5K-10K', 5000, 10000, 64, 51), ('$11K-15K', 11000, 15000, 13, 23),
                  ('$16K-25K', 16000, 25000, 2, 5), ('>$25K', 25000, None, 4, 4)]
FIRMEX_FIXED = [('<$5K', 0, 5000, 13, 13), ('$5K-10K', 5000, 10000, 30, 22), ('$11K-15K', 11000, 15000, 10, 15),
                ('$16K-25K', 16000, 25000, 10, 11), ('$26K-50K', 26000, 50000, 25, 22), ('$51K-100K', 51000, 100000, 6, 9),
                ('>$100K', 100000, None, 2, 6), ('Other', None, None, 4, 2)]
# GF Data via ACG Middle Market Growth, fall 2025: average TEV/EBITDA with and without a sell-side QoE.
GFDATA = {'with': 7.4, 'without': 7.0, 'n': 360, 'since': 'Q3 2024'}

PDF_QUOTES = [  # (pdf, page, kind, expected): 'text' = whitespace-normalised substring; 'pcts' = % sequence in order
    (SHRM_PDF, 4, 'text', 'In total, 2,371 members responded to the survey.'),
    (SHRM_PDF, 6, 'text', 'per-hire for executive roles reached $10,625'),
    (SHRM_PDF, 6, 'text', 'for nonexecutive roles was $1,200'),
    (SHRM_PDF, 6, 'text', 'from $1,244 in 2022'),
    (SHRM_PDF, 6, 'text', '$8,750'),
    (SHRM_PDF, 6, 'text', '$5,000'),
    (SHRM_PDF, 6, 'text', '$1,633'),
    (SHRM_PDF, 8, 'text', 'dropped significantly (from 60 days to 45'),
    (SHRM_PDF, 8, 'text', 'Time-to-Fill Executive and Nonexecutive Positions'),
    (SHRM_PDF, 9, 'text', 'Small (<100) 100%'),
    (FIRMEX_PDF, 4, 'text', 'The 189 US respondents'),
    (FIRMEX_PDF, 15, 'text', 'For monthly fees, two-thirds of the advisors said they charged an upfront fee between $5,000 and $10,000.'),
    (FIRMEX_PDF, 15, 'text', 'employees typically charged $15,000 or less.'),
    (FIRMEX_PDF, 15, 'text', 'upfront retainers of $25,000 or more.'),
    (FIRMEX_PDF, 15, 'pcts', [v for r in FIRMEX_MONTHLY for v in r[3:5]]),
    (FIRMEX_PDF, 16, 'pcts', [v for r in FIRMEX_FIXED for v in r[3:5]]),
    (BRIDGE_PDF, 2, 'text', '253 B2B SaaS companies participated'),
    (BRIDGE_PDF, 24, 'text', 'Average ramp times sits at 5.3 months.'),
    (BRIDGE_PDF, 31, 'text', 'Median annual ACV quota is now $740K.'),
    (BRIDGE_PDF, 33, 'text', 'On average, 66% of reps in a given'),
    (BRIDGE_PDF, 35, 'text', 'Median on-target earnings are $167K'),
]
GF_PAGE = (DH + '/gfdata_mmg_qoe_fall2025/page.html', 'https://middlemarketgrowth.org/fall-2025-gf-data-quality-of-earnings-reports/')
IB_PAGE = (DH + '/qoe2_investmentbank/page.html', 'https://investmentbank.com/insights/sell-side-vs-buy-side-quality-of-earnings-timing')
SBA_PAGES = {
    'EisnerAmper': (DH + '/qoe_eisneramper_sba/page.html', 'https://www.eisneramper.com/insights/financial-services/sba-quality-of-earnings-requirement-0826/'),
    'HoganTaylor': (DH + '/qoe2_hogantaylor_sba/page.html', 'https://blog.hogantaylor.com/thought-leadership/what-do-sba-lenders-need-to-know-about-the-new-quality-of-earnings-requirement'),
    'CohnReznick': (DH + '/qoe2_cohnreznick_sba/page.html', 'https://www.cohnreznick.com/insights/new-sba-quality-of-earnings-requirement/'),
    'CLA': (DH + '/qoe2_cla_sba/page.html', 'https://www.claconnect.com/en/resources/blogs/private-equity/the-sba-now-requires-a-quality-of-earnings-on-larger-acquisition-loans'),
}
CHECK_PAGES = {
    'ContractsCounsel': (DH + '/contractscounsel_msa_cost/page.html', 'https://www.contractscounsel.com/b/master-services-agreement-cost'),
    'Franchise Law Solutions': (DH + '/sop_franchiselawsolutions/page.html', 'https://www.franchiselawsolutions.com/learn/franchise-your-business/franchise-operations-manual'),
    'Wethos': (DH + '/sop_wethos/page.html', 'https://www.wethos.co/scope-of-work-templates/standard-operating-procedure-development'),
    'Strety (EOS)': (DH + '/sop_eos_strety/page.html', 'https://strety.com/blog/eos-implementer-cost/'),
}
PAGE_QUOTES = [  # (page key, quote): visible text of the saved page, whitespace and dashes normalised
    ('GF Data', 'GF Data recently analyzed 360 transactions completed since Q3 2024'),
    ('GF Data', 'sellers that used a sell-side QoE saw TEV/EBITDA multiples of 7.4x on average'),
    ('GF Data', "7.0x for those that didn't undertake a QoE process"),
    ('GF Data', 'most notable for deals with enterprise values above $50 million, while smaller deals tended not to experience a valuation boost'),
    ('GF Data', 'three to six months ahead of a sales process is a good time to start'),
    ('investmentbank.com', 'Below $25 million enterprise value, the multiple lift narrows and can disappear entirely'),
    ('CT Acquisitions', 'Plan a realistic engagement at 8 to 12 weeks from kickoff to final report'),
    ('EisnerAmper', 'Starting October 1, 2026, the SBA will require an independent quality of earnings report on 7(a) change-of-ownership loans for initial acquisitions and business expansions priced at $3 million in enterprise value or more'),
    ('EisnerAmper', 'a seller-side report supplied through a broker does not satisfy the requirement'),
    ('HoganTaylor', 'Beginning October 1, 2026, the SBA will require an independent Quality of Earnings (QoE) report for certain business acquisitions with a business purchase price of $3 million or more'),
    ('HoganTaylor', 'A buyer- or seller-commissioned report does not satisfy the requirement'),
    ('HoganTaylor', 'Owner-occupied real estate is excluded when determining the threshold'),
    ('CohnReznick', 'Beginning Oct. 1, 2026, lenders financing certain change-of-ownership transactions are now required to obtain an independent Quality of Earnings (QoE) report for acquisitions with purchase prices of $3 million or more'),
    ('CLA', 'for business expansion and initial acquisition transactions where the business purchase price is $3 million or greater'),
    ('ContractsCounsel', 'Avg cost to draft a Master Services Agreement : $980.00'),
    ('ContractsCounsel', 'Avg cost to review a Master Services Agreement : $580.00'),
    ('ContractsCounsel', 'Clients helped: 326 recent master services agreement projects'),
    ('Franchise Law Solutions', 'Professionally developed, franchise operations manuals typically run $9,000 to $20,000'),
    ('Wethos', 'Freelancers might charge a flat rate ranging from $3,000 to $10,000 for smaller projects'),
    ('Wethos', 'potentially exceeding $20,000'),
    ('Wethos', 'might extend from 1 to 3 months'),
    ('Strety (EOS)', 'expect $20,000-$45,000 per year, typically for two years'),
    ('ECEC technical note', 'approximately 28,300 occupational observations selected from a sample of about 6,600 private industry establishments'),
]

# ------------------------------------------------------------------------------------------------------------------
# Growth floor: OEWS industry cells (NAICS 2022) and occupations
# ------------------------------------------------------------------------------------------------------------------
OCC_SALES = ['41-3091', '41-4011', '41-4012']   # sales reps of services; wholesale and manufacturing (technical; other)
SALES_CELL = {'home': '238220', 'medical': '621100', 'vet': '541900', 'msp': '541500', 'saas': '513200', 'prof': '541200',
              'mfg': '339900', 'dist': '423000', 'ecom': '44-45', 'staff': '561320', 'land': '561730', 'wash': '811190',
              'auto': '811110', 'constr': '238900', 'fit': '713940', 'rest': '72'}
SALES_NOTE = {'vet': 'proxy: 541900 Other professional, scientific and technical services (contains 541940; the 6-digit row has no sales occupations)',
              'rest': 'proxy: sector 72 Accommodation and food services (722500 has 41-3091 at PRSE 17.8%; 722511 has no services-sales row)',
              'ecom': 'proxy: retail trade sector 44-45 (NAICS 2022 has no e-commerce row)',
              'wash': 'proxy: 811190 Other automotive repair and maintenance (contains 811192 car washes)',
              'medical': 'proxy: 621100 Offices of physicians (dentists not included)'}
# The alternative cell of each proxy (same three occupations, pooled the same way); half the gap between the two floors
# joins the floor's SE (judgment: the project's rule for a bridge choice). ind -> (cells, label, why)
SALES_ALT = {'medical': (['621200'], '621200', 'offices of dentists: the console industry is medical or dental practice'),
             'vet': (['621100'], '621100', 'offices of physicians: the clinical-practice analog with sales-rep rows'),
             'rest': (['722500'], '722500', 'restaurants and other eating places: the most detailed restaurant cell with a services-sales row'),
             'wash': (['811100'], '811100', 'automotive repair and maintenance: the parent of 811190 (811192 has no sales rows)'),
             'ecom': (['449000', '455000', '456000', '458000', '459000'], '449+455+456+458+459',
                      'the consumer-goods retail subsectors, where NAICS 2022 classifies online sellers by product line')}
WEAK_PROXY = ['vet', 'rest']     # the analyst's flags; their texts are written from the data in step 3
VET_CELL, VET_OCCS = '541940', ['00-0000', '41-0000', '41-2000', '13-1161']   # veterinary services: all, sales and related,
#                                                                                 retail sales workers, marketing specialists
REST_CONTEXT = ['721000', '722511']                                # accommodation; full-service restaurants

PROBE_JS = r"""/* intervention_costs probe (written by intervention_costs.py): evaluates the console's model on the frozen
   snapshot through the harness. usage: node probe.js HARNESS CFG.json  ->  JSON on stdout */
const H=require(process.argv[2]); const cfg=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const A=H.load();
const IND=Object.keys(A.IND);
function median(B,ind,ern){ const I=B.IND[ind],RF=B.sizeRefs(ern),rev=ern/B.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,
          gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40,budget:1e5,lamT:900,theta:.75}; }
const med=a=>{const s=[...a].sort((x,y)=>x-y);const n=s.length;return n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;};
const out={industries:IND};
/* 1. EV -> revenue and EBITDA -> revenue, peer-median business, median over the 16 industries, on the research
      round's grid (log10 SDE 4.3 ... 7.0 by 0.1: the same floating-point loop, so the grid points are identical) */
out.map=[];
for(let l=4.3;l<=7.01;l+=0.1){ const ern=10**l; const evs=[],revs=[],ebs=[];
  for(const ind of IND){ const m=median(A,ind,ern); const r=A.model({...m,ask:1}); const V=A.model({...m,ask:r.V}).V;
    const w=A.sdeEbitdaWedge(A.naicsFor(ind),m.rev)||1.5; evs.push(V); revs.push(m.rev); ebs.push(ern/w); }
  out.map.push({sde:ern,ev:med(evs),rev:med(revs),ebitda:med(ebs)}); }
/* 2. the console's value effect of the QoE intervention as shipped (fin floor .93), peer-median businesses */
function prep(B,s){ s={...s}; s.rhoSell=B.bestRatio(s,0,0); s.optRho=B.bestRatio(s,s.theta,s.lamT); return s; }
out.qoe=[];
for(const ern of cfg.sde_qoe) for(const ind of IND){
  const m=median(A,ind,ern); const s=prep(A,{...m,ask:A.model({...m,ask:1}).V*1.05}); const r0=A.model(s);
  const r1=A.model(A.applyAll(s,r0,["qoe"]));
  out.qoe.push({ind,ern,rev:m.rev,V:r0.V,dV:r1.V/r0.V-1,fin:m.fin}); }
/* 3. the GM intervention's value effect with the earnings charge scaled by a loading L (the research round's override
      of the gm line; L = 1 is the console as shipped) */
const GM0='eff:s=>({ceilAt:{own:.30},floorAt:{mgt:.72},add:{ern:-gmSalary(s)}})';
const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,
          buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
out.gm=[];
for(const L of cfg.loadings){
  const B=(L===1)?A:H.load([[GM0,GM0.replace('-gmSalary(s)','-'+L+'*gmSalary(s)')]]);
  const dV=s0=>{ const s={...s0,ask:B.model({...s0,ask:1}).V*1.05}; s.rhoSell=B.bestRatio(s,0,0); const r0=B.model(s);
    const r1=B.model(B.applyAll(s,r0,["gm"])); return {dV:r1.V/r0.V-1,wage:B.gmSalary(s)}; };
  const ex=dV(EX); out.gm.push({L,ind:"framework",ern:EX.ern,rev:EX.rev,dV:ex.dV,wage:ex.wage});
  for(const ern of cfg.sde_gm) for(const ind of IND){ const m=median(B,ind,ern); const d=dV(m);
    out.gm.push({L,ind,ern,rev:m.rev,dV:d.dV,wage:d.wage}); } }
/* 4. the console's current intervention costs and days at peer-median businesses */
out.costs=[];
for(const ern of cfg.sde_cost) for(const ind of IND){ const m=median(A,ind,ern); const c={};
  for(const it of A.INTERV) c[it.k]=it.cost(m);
  out.costs.push({ind,ern,rev:m.rev,wage:A.gmSalary(m),cost:c}); }
out.days=Object.fromEntries(A.INTERV.map(it=>[it.k,it.days]));
process.stdout.write(JSON.stringify(out));
"""

# The page code that reads the table (shipped in RESULT.json as js_code). Step 6 runs it verbatim in node on the snapshot.
JS_CODE = r"""const IV=MODELS.fitted.interventions, GF=IV.growth_floor;
// qoe: the console's form max(floor, share x revenue) with the fitted floor and share (Aggregate)
const qoeCost=s=>Math.max(IV.qoe.floor, IV.qoe.share*s.rev);
// gm: the console's structure (one year's salary as the cost), now loaded, plus the one-time hire
const gmCost=s=>IV.gm.hire_cost + IV.gm.loading*gmSalary(s);
const gmCharge=s=>-IV.gm.loading*gmSalary(s);        // permanent earnings charge (the gm effect's add.ern)
// growth: the floor per industry (Aggregate; unknown industry -> prof); the .022 share stays judgment
const growthCost=s=>Math.max((GF.by_industry[s.ind]!==undefined?GF.by_industry[s.ind]:GF.by_industry.prof), GF.share*s.rev);
return {qoeCost, gmCost, gmCharge, growthCost};"""

JSCHECK_JS = r"""/* intervention_costs js check (written by intervention_costs.py): runs the page code shipped with the table on the
   frozen snapshot through the harness. usage: node jscheck.js HARNESS CFG.json  ->  JSON on stdout */
const H=require(process.argv[2]); const cfg=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const A=H.load(); A.MODELS.fitted.interventions=cfg.table;
const F=(new Function('MODELS','gmSalary',cfg.js_code))(A.MODELS,A.gmSalary);
const IND=Object.keys(A.IND);
function median(B,ind,ern){ const I=B.IND[ind],RF=B.sizeRefs(ern),rev=ern/B.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,
          gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40,budget:1e5,lamT:900,theta:.75}; }
const out={rows:[]};
for(const ern of cfg.sde) for(const ind of IND){ const m=median(A,ind,ern);
  out.rows.push({ind,ern,rev:m.rev,wage:A.gmSalary(m),qoe:F.qoeCost(m),gm:F.gmCost(m),charge:F.gmCharge(m),growth:F.growthCost(m)}); }
out.unknown_growth=F.growthCost({ind:"not_an_industry",rev:1e6});
process.stdout.write(JSON.stringify(out));
"""


# ------------------------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------------------------
def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:n]


def rnd(x, step):
    """half-up rounding to a multiple of step (an int for step >= 1)"""
    v = math.floor(x / step + 0.5) * step
    return int(round(v)) if step >= 1 else round(v, max(0, -int(math.floor(math.log10(step)))))


def py(o):
    if isinstance(o, dict):
        return {str(k): py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [py(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def norm(s):
    for a, b in (('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('–', '-'), ('—', '-'),
                 ('−', '-'), ('‐', '-'), ('‑', '-'), ('\xa0', ' '), ('­', ''), ('​', '')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


class _Text(HTMLParser):
    """visible text of a saved page (data only)"""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.skip = 0

    def handle_starttag(self, t, a):
        if t in ('script', 'style', 'noscript', 'svg'): self.skip += 1

    def handle_endtag(self, t):
        if t in ('script', 'style', 'noscript', 'svg') and self.skip: self.skip -= 1

    def handle_data(self, d):
        if not self.skip: self.out.append(d)


class _Tables(HTMLParser):
    """every <table>: its caption and its rows (lists of cell texts)"""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.tables = []; self._t = None; self._row = None; self._cell = None; self._cap = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._t = {'caption': '', 'rows': []}; self.tables.append(self._t)
        elif self._t is None:
            return
        elif tag == 'caption':
            self._cap = []
        elif tag == 'tr':
            self._row = []
        elif tag in ('th', 'td') and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if self._t is None:
            return
        if tag == 'caption' and self._cap is not None:
            self._t['caption'] = norm(' '.join(self._cap)); self._cap = None
        elif tag in ('th', 'td') and self._cell is not None:
            self._row.append(norm(' '.join(self._cell))); self._cell = None
        elif tag == 'tr' and self._row is not None:
            self._t['rows'].append(self._row); self._row = None
        elif tag == 'table':
            self._t = None

    def handle_data(self, d):
        if self._cap is not None: self._cap.append(d)
        if self._cell is not None: self._cell.append(d)


_TXT = {}


def page_text(path):
    if path not in _TXT:
        p = _Text(); p.feed(open(path, 'rb').read().decode('utf-8', 'replace')); _TXT[path] = norm(' '.join(p.out))
    return _TXT[path]


def html_tables(path):
    p = _Tables(); p.feed(open(path, 'rb').read().decode('utf-8', 'replace')); return p.tables


def have_pdftotext():
    try:
        return subprocess.run(['pdftotext', '-v'], capture_output=True, timeout=30).returncode in (0, 99)
    except (OSError, subprocess.TimeoutExpired):
        return False


def pdf_page(pdf, page):
    r = subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), pdf, '-'], capture_output=True, timeout=300)
    return r.stdout.decode('utf-8', 'replace')


def quote_check(text, quote):
    """every number in the quote is on the page, and the quote itself: verbatim (each '...' fragment), or for a
    transcribed table row ('a | b | c') each cell in order, at most 200 characters apart"""
    q = norm(quote)
    nums = re.findall(r'\d[\d,]*(?:\.\d+)?', q)
    nums_ok = all(n in text for n in nums)
    if '|' in q:
        cells = [c.strip() for c in q.split('|') if c.strip()]
        start = 0
        while True:
            i = text.find(cells[0], start)
            if i < 0:
                return False, 'cells'
            pos, good = i + len(cells[0]), True
            for c in cells[1:]:
                j = text.find(c, pos)
                if j < 0 or j - pos > 200:
                    good = False; break
                pos = j + len(c)
            if good:
                return nums_ok, 'cells'
            start = i + 1
    frags = [f.strip() for f in re.split(r'\.\.\.|…', q) if f.strip()]
    return nums_ok and all(f in text for f in frags), 'verbatim'


def num(v):
    try:
        x = float(str(v).replace(',', '').strip())
        return x if np.isfinite(x) else None
    except ValueError:
        return None


# ------------------------------------------------------------------------------------------------------------------
# QoE: estimators
# ------------------------------------------------------------------------------------------------------------------
def fit_max(x, y, w):
    """exact weighted LS of y = log max(F, s x). For a kink K = F/s, pred = a + A_i (log x_i - log K) with A_i = 1 above
    the kink; with a profiled out the loss is a quadratic in u = log K inside each interval between sorted log x, so the
    minimum is found interval by interval (clipped to the interval). Returns F, s, loss."""
    lx = np.log(x); W = w.sum(); best = None
    bounds = np.r_[-np.inf, np.unique(lx), np.inf]
    for j in range(len(bounds) - 1):
        lo, hi = bounds[j], bounds[j + 1]
        A = (lx >= hi).astype(float)
        p = y - A * lx; c = np.sum(w * p) / W; q = A - np.sum(w * A) / W; r0 = p - c
        den = np.sum(w * q * q)
        u = -np.sum(w * r0 * q) / den if den > 0 else (hi if np.isfinite(hi) else lo)
        u = min(max(u, lo), hi)
        L = float(np.sum(w * (r0 + u * q) ** 2))
        if best is None or L < best[0] - 1e-15:
            best = (L, u, c + u * np.sum(w * A) / W)
    L, u, a = best
    return float(np.exp(a)), float(np.exp(a - u)), L


def design_pow(x, sides, with_sides):
    cols = [np.ones(len(x)), np.log(x / 5e6)]
    if with_sides:
        cols += [(sides == 'sell').astype(float), (sides == 'buy').astype(float)]
    return np.column_stack(cols)


def fit_pow(x, y, w, sides, with_sides=True):
    X = design_pow(x, sides, with_sides); Wd = X.T * w
    return np.linalg.solve(Wd @ X + 1e-9 * np.eye(X.shape[1]), Wd @ y)


def pow_pred(b, rev, side='generic'):
    v = b[0] + b[1] * np.log(rev / 5e6)
    if len(b) == 4:
        v = v + (b[2] if side == 'sell' else b[3] if side == 'buy' else 0.0)
    return float(np.exp(v))


def src_weights(T):
    return T.src.map(T.src.value_counts()).rdiv(1.0).values


def to_rev(x, basis, G):
    if basis == 'rev':
        return float(x)
    src, lr = G['ev' if basis == 'ev' else 'ebitda'], G['rev']; lx = math.log(x)
    if lx > src[-1]:
        return float(np.exp(lr[-1] + (lx - src[-1]) * (lr[-1] - lr[-2]) / (src[-1] - src[-2])))
    if lx < src[0]:
        return float(np.exp(lr[0] + (lx - src[0]) * (lr[1] - lr[0]) / (src[1] - src[0])))
    return float(np.exp(np.interp(lx, src, lr)))


def build(G, conv='map', evr=.75, ebr=.15, sides=('sell', 'buy', 'generic'), lo_rev=QOE_WINDOW[0], hi_rev=QOE_WINDOW[1], buy_mult=1.0,
          coding='shipped'):
    """the fitted tiers; coding='research' restores the research round's side coding (RESEARCH_SIDE) for replication"""
    rows = []
    for (label, url, lf, basis, tlo, thi, flo, fhi, side, wlo, whi, quote) in TIERS:
        if coding == 'research':
            side = RESEARCH_SIDE.get((label, tlo, thi), side)
        if basis == 'note' or flo is None or side not in sides:
            continue
        if conv == 'map':
            f = lambda v, b=basis: to_rev(v, b, G)
        else:
            f = lambda v, b=basis: v * {'rev': 1.0, 'ev': 1 / evr, 'ebitda': 1 / ebr}[b]
        lo = f(tlo) if (tlo is not None and tlo > 0) else None
        hi = f(thi) if thi is not None else None
        if lo is None:
            lo = max(lo_rev, hi / 10 if hi else lo_rev)           # "under $X": from a tenth of X (at least the window floor)
        if hi is None:
            hi = 3 * lo                                           # "over $X": up to 3X
        fh = fhi if fhi is not None else 1.5 * flo                # "from $F": F to 1.5F
        m = buy_mult if side == 'buy' else 1.0
        rows.append(dict(src=label.split('_')[0], label=label, side=side, basis=basis, tier_lo=tlo, tier_hi=thi,
                         rev_lo=lo, rev_hi=hi, rev=math.sqrt(lo * hi), fee_lo=flo * m, fee_hi=fh * m,
                         fee=math.sqrt(flo * fh) * m, url=url, file=lf))
    T = pd.DataFrame(rows)
    return T[(T.rev >= lo_rev) & (T.rev <= hi_rev)].reset_index(drop=True)


def fit_T(T):
    return fit_max(T.rev.values, np.log(T.fee.values), src_weights(T))


def cluster_boot(T, B, rng):
    """cluster bootstrap over sources: each draw is its own cluster of weight 1 (a source drawn k times weighs k)"""
    srcs = list(dict.fromkeys(T.src)); idx = {s: np.flatnonzero(T.src.values == s) for s in srcs}
    x = T.rev.values; y = np.log(T.fee.values); sd = T.side.values
    bm, bp, skipped = [], [], 0
    for _ in range(B):
        pick = rng.integers(0, len(srcs), len(srcs))
        rows = np.concatenate([idx[srcs[i]] for i in pick])
        w = np.concatenate([np.full(len(idx[srcs[i]]), 1.0 / len(idx[srcs[i]])) for i in pick])
        bm.append(fit_max(x[rows], y[rows], w)[:2])
        if len(np.unique(sd[rows])) == 3:
            bp.append(fit_pow(x[rows], y[rows], w, sd[rows]))
        else:
            skipped += 1
    return np.array(bm), np.array(bp), skipped


def research_boot(T, B=2000, seed=7):
    """the research round's bootstrap, reproduced: weights 1/(rows of the label in the resample), so a source drawn
    k times keeps total weight 1; draws without all three sides skipped; SD with ddof 0"""
    rng = np.random.default_rng(seed); srcs = T.src.unique(); out = []
    for _ in range(B):
        pick = rng.choice(srcs, len(srcs), replace=True)
        Tb = pd.concat([T[T.src == s] for s in pick], ignore_index=True)
        if Tb.side.nunique() < 3:
            continue
        out.append(fit_max(Tb.rev.values, np.log(Tb.fee.values), src_weights(Tb))[:2])
    out = np.array(out)
    return dict(floor_se=round(float(out[:, 0].std())), share_se=round(float(out[:, 1].std()), 5),
                floor_p5_p95=[round(float(np.percentile(out[:, 0], q))) for q in (5, 95)],
                share_p5_p95=[round(float(np.percentile(out[:, 1], q)), 5) for q in (5, 95)], draws=len(out))


def cv_forms(T):
    """leave-one-source-out prediction error (mean squared log error of the held-out source's tiers, sources equal)"""
    srcs = list(dict.fromkeys(T.src)); err = {'max_form': [], 'power_pooled': [], 'power_sides': [], 'constant': []}
    for s in srcs:
        tr, te = T[T.src != s], T[T.src == s]
        w = src_weights(tr); x, y = tr.rev.values, np.log(tr.fee.values); yt = np.log(te.fee.values)
        F, sh, _ = fit_max(x, y, w)
        err['max_form'].append(np.mean((yt - np.log(np.maximum(F, sh * te.rev.values))) ** 2))
        b0 = fit_pow(x, y, w, tr.side.values, False)
        err['power_pooled'].append(np.mean((yt - np.log([pow_pred(b0, r) for r in te.rev.values])) ** 2))
        b1 = fit_pow(x, y, w, tr.side.values, True)
        err['power_sides'].append(np.mean((yt - np.log([pow_pred(b1, r, sd) for r, sd in zip(te.rev.values, te.side.values)])) ** 2))
        err['constant'].append(np.mean((yt - np.sum(w * y) / w.sum()) ** 2))
    return {k: dict(msle=round(float(np.mean(v)), 4), rmsle=round(float(np.sqrt(np.mean(v))), 4)) for k, v in err.items()}


# ------------------------------------------------------------------------------------------------------------------
# ECEC
# ------------------------------------------------------------------------------------------------------------------
ECEC_KEYS = ['tc', 'w', 'b', 'paid_leave', 'supp', 'insurance', 'retirement', 'legal']


def ecec_cell(tables, table_no, name):
    """first row with this label in 'Table <n>.'; returns (costs, second column of each pair: percent or RSE)"""
    t = [t for t in tables if t['caption'].startswith('Table %d.' % table_no)]
    assert len(t) == 1, (table_no, len(t))
    for r in t[0]['rows']:
        if r and re.sub(r'\s*\(\s*\d+\s*\)\s*$', '', r[0]) == name and len(r) >= 17:
            v = [num(c) for c in r[1:17]]
            return {k: v[2 * i] for i, k in enumerate(ECEC_KEYS)}, {k: v[2 * i + 1] for i, k in enumerate(ECEC_KEYS)}
    raise KeyError((table_no, name))


def annual_loading(c, supp=True):
    """the annual-salary loading of one ECEC cell, TC/(W + PL); without supplemental pay, (TC - supp)/(W + PL)"""
    return (c['tc'] - (0.0 if supp else c['supp'])) / (c['w'] + c['paid_leave'])


def loading_rel_se(c, rse):
    """relative SE of L = TC/(W + PL) = 1 + B'/D from the published RSEs, with D = W + PL and B' = B - PL: W, PL and B'
    taken as independent, so SE(D)^2 = SE(W)^2 + SE(PL)^2 and SE(B')^2 = SE(B)^2 - SE(PL)^2; d ln L = (B'/TC)(d ln B' - d ln D)"""
    se_w, se_b, se_pl = (c[k] * rse[k] / 100.0 for k in ('w', 'b', 'paid_leave'))
    D, Bp = c['w'] + c['paid_leave'], c['b'] - c['paid_leave']
    var_bp = se_b ** 2 - se_pl ** 2
    assert var_bp > 0, ('paid-leave SE exceeds the benefit SE', c, rse)
    return (Bp / c['tc']) * math.hypot(math.sqrt(var_bp) / Bp, math.hypot(se_w, se_pl) / D)


def loading_rel_se_tcw(c, rse):
    """round 2's relative SE of TC/W: d ln L = (B/TC)(d ln B - d ln W), errors independent (kept for the comparison)"""
    return (c['b'] / c['tc']) * math.hypot(rse['b'], rse['w']) / 100.0


# ------------------------------------------------------------------------------------------------------------------
# OEWS: pooled sales-rep wages
# ------------------------------------------------------------------------------------------------------------------
Q_PCT = (.10, .25, .50, .75, .90)
PCT_COLS = ('A_PCT10', 'A_PCT25', 'A_MEDIAN', 'A_PCT75', 'A_PCT90')


def wage_cdf(lp, x):
    """an occupation's wage CDF at log wage x: linear in log wage through its published 10th-90th percentiles (log knots
    lp), extended linearly past the end knots, held to 0..1"""
    if x <= lp[0]:
        v = Q_PCT[0] + (x - lp[0]) * (Q_PCT[1] - Q_PCT[0]) / (lp[1] - lp[0])
    elif x >= lp[-1]:
        v = Q_PCT[-1] + (x - lp[-1]) * (Q_PCT[-1] - Q_PCT[-2]) / (lp[-1] - lp[-2])
    else:
        v = float(np.interp(x, lp, Q_PCT))
    return min(1.0, max(0.0, v))


def wage_density(lp, x):
    """the slope of wage_cdf in log wage at x (0 where the CDF is held at 0 or 1)"""
    v = wage_cdf(lp, x)
    if v <= 0.0 or v >= 1.0:
        return 0.0
    if x <= lp[0]:
        return (Q_PCT[1] - Q_PCT[0]) / (lp[1] - lp[0])
    if x >= lp[-1]:
        return (Q_PCT[-1] - Q_PCT[-2]) / (lp[-1] - lp[-2])
    j = min(max(int(np.searchsorted(lp, x, side='right')) - 1, 0), len(lp) - 2)
    return (Q_PCT[j + 1] - Q_PCT[j]) / (lp[j + 1] - lp[j])


def pooled_wage(D, cells, drop_suppressed=False):
    """the sales occupations of one or more OEWS cells pooled by employment. Returns the employment-weighted mean wage
    (SE from MEAN_PRSE, round 2's estimator), the MEDIAN of the pooled distribution (the employment-weighted mixture of
    the occupations' CDFs solved for 1/2 by bisection) with its SE (delta method: relative SE sqrt(sum_k (omega_k r_k)^2),
    omega_k = occupation k's share of the pooled density at the median, r_k = MEDIAN_SE_FACTOR x MEAN_PRSE_k), and the
    employment-weighted mean of the occupation medians (a check)"""
    S = D[D.NAICS.isin(cells)]
    occs, emps, means, prses, meds, lps, notes = [], [], [], [], [], [], []
    for _, r_ in S.sort_values(['NAICS', 'OCC_CODE']).iterrows():
        tag = r_.OCC_CODE if len(cells) == 1 else '%s %s' % (r_.NAICS, r_.OCC_CODE)
        mean = num(r_.A_MEAN)
        if mean is None:
            notes.append('%s excluded (mean wage not published: %s)' % (tag, r_.A_MEAN)); continue
        emp = num(r_.TOT_EMP)
        if emp is None:
            if drop_suppressed:
                notes.append('%s dropped (employment %s)' % (tag, r_.TOT_EMP)); continue
            emp = SUPPRESSED_EMP_WEIGHT; notes.append('%s employment %s -> weight %d' % (tag, r_.TOT_EMP, SUPPRESSED_EMP_WEIGHT))
        prse = num(r_.MEAN_PRSE)
        pct = [num(r_[c]) for c in PCT_COLS]
        assert prse is not None and all(p is not None for p in pct), (cells, tag)
        lp = np.log(pct)
        for i in range(1, len(lp)):          # equal published percentiles: a steep step instead of a flat knot
            if lp[i] <= lp[i - 1]:
                lp[i] = lp[i - 1] + 1e-6
        occs.append(tag); emps.append(emp); means.append(mean); prses.append(prse); meds.append(pct[2]); lps.append(lp)
    emps, means, prses, meds = (np.array(v, dtype=float) for v in (emps, means, prses, meds))
    wt = emps / emps.sum()
    mean = float(np.sum(wt * means)); se_mean = float(np.sqrt(np.sum((wt * means * prses / 100) ** 2)))
    f = lambda x: sum(w_ * wage_cdf(lp, x) for w_, lp in zip(wt, lps)) - 0.5
    a, b = min(lp[0] for lp in lps), max(lp[-1] for lp in lps)
    assert f(a) < 0 < f(b), cells
    for _ in range(100):
        m = 0.5 * (a + b)
        if f(m) < 0:
            a = m
        else:
            b = m
    xm = 0.5 * (a + b); med = float(np.exp(xm))
    dens = np.array([w_ * wage_density(lp, xm) for w_, lp in zip(wt, lps)])
    omega = dens / dens.sum()
    rel_med = float(np.sqrt(np.sum((omega * MEDIAN_SE_FACTOR * prses / 100) ** 2)))
    titles = list(dict.fromkeys(str(t) for t in S.NAICS_TITLE)); files = list(dict.fromkeys(str(t) for t in S.FILE))
    return dict(cells=list(cells), title=' + '.join(titles), file=' + '.join(files), occs=occs, employment=int(round(emps.sum())),
                mean=mean, se_mean=se_mean, median=med, rel_se_median=rel_med, se_median=rel_med * med,
                wmean_of_medians=float(np.sum(wt * meds)), occ_median_range=[float(meds.min()), float(meds.max())],
                by_occ={o: dict(emp=float(e), mean=float(mn), median=float(md), prse=float(p), density_share=round(float(om), 4))
                        for o, e, mn, md, p, om in zip(occs, emps, means, meds, prses, omega)}, notes=notes)


# ------------------------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------------------------
def main():
    checks, tests, sources = [], {}, []

    def check(name, ok, detail, test=True):
        checks.append(dict(name=name, outcome=('pass' if ok else 'fail') if test else 'info', detail=detail))
        if test:
            tests[name] = bool(ok)

    # ---------------------------------------------------------------- 0. snapshot: current values
    html = open(SNAP, encoding='utf-8').read()
    blk = html[html.index('const INTERV=['):]
    blk = blk[:blk.index('\n];')]
    cur = {}
    for m in re.finditer(r'\{k:"(\w+)", n:"([^"]*)", days:(\d+),\s*cost:s=>(.*?),\s*eff:', blk, flags=re.S):
        k, name, days, cost = m.group(1), m.group(2), int(m.group(3)), m.group(4).strip()
        mm = re.fullmatch(r'Math\.max\((\d+),(\.\d+)\*s\.rev\)', cost)
        cur[k] = dict(name=name, days=days, cost=cost, floor=int(mm.group(1)) if mm else None, share=float(mm.group(2)) if mm else None)
    qoe_fin = float(re.search(r'k:"qoe".*?floorAt:\{fin:(\.\d+)\}', blk, flags=re.S).group(1))
    fitted_line = next(l for l in html.split('\n') if l.startswith('MODELS.fitted={'))
    MF = json.loads(fitted_line[len('MODELS.fitted='):].rstrip().rstrip(';'))
    G_ECI = MF['gm_wage']['wage_growth_alt_all_private']
    check('snapshot: INTERV parsed (11 interventions; qoe, gm and growth as the brief states)',
          len(cur) == 11 and (cur['qoe']['floor'], cur['qoe']['share'], cur['qoe']['days']) == (22000, .0045, 60)
          and cur['gm']['cost'] == 'gmSalary(s)' and cur['gm']['days'] == 210
          and (cur['growth']['floor'], cur['growth']['share'], cur['growth']['days']) == (55000, .022, 270) and qoe_fin == .93,
          'qoe max(%d,%s*rev) %d d, fin floor %s; gm %s %d d; growth max(%d,%s*rev) %d d; outreach %s %d d' % (
              cur['qoe']['floor'], cur['qoe']['share'], cur['qoe']['days'], qoe_fin, cur['gm']['cost'], cur['gm']['days'],
              cur['growth']['floor'], cur['growth']['share'], cur['growth']['days'], cur['outreach']['cost'], cur['outreach']['days']))
    check('snapshot: ECI factor to 2026Q2 (all private wages and salaries) is 1.0353', abs(G_ECI - 1.0353) < 1e-12,
          'MODELS.fitted.gm_wage.wage_growth_alt_all_private = %s (gmSalary uses wage_growth = %s, management series %s)' % (
              G_ECI, MF['gm_wage']['wage_growth'], MF['gm_wage'].get('eci_series')))

    # ---------------------------------------------------------------- 2a. ECEC: cells and loadings (parsed before the node
    #                                                                       probe, whose GM value-effect checks use them)
    t_nr = html_tables(ECEC_T04) + html_tables(ECEC_T06)
    t_rse = html_tables(ECEC_RSE)
    cells = {}
    for key, (tn, name) in ECEC_CELLS.items():
        c, pct = ecec_cell(t_nr, tn, name)
        c2, rse = ecec_cell(t_rse, tn, name)
        cells[key] = dict(table=tn, name=name, cost=c, pct=pct, rse=rse, rse_cost_match=all(abs(c[k] - c2[k]) < 1e-9 for k in ECEC_KEYS if c[k] is not None))
    for key, (tc, w_, pl) in ECEC_DECIDED.items():
        assert (cells[key]['cost']['tc'], cells[key]['cost']['w'], cells[key]['cost']['paid_leave']) == (tc, w_, pl), (key, cells[key]['cost'])
    check('ECEC: parsed cells equal the decision\'s numbers (TC/W/PL 78.88/54.06/7.37, 37.64/27.88/2.34, 46.89/32.82/3.54, 35.85/26.99/2.11)',
          True, 'tables 4 and 6, June 2026: management, professional and related; 1-49 workers; all private; sales and related')
    check('ECEC: table 4 private industry = table 6 all workers; the RSE tables carry the same cost levels',
          cells['private']['cost'] == cells['all_sizes']['cost'] and all(c['rse_cost_match'] for c in cells.values()),
          'all %d cells' % len(cells))
    gap_b = max(abs(c['cost']['tc'] - c['cost']['w'] - c['cost']['b']) for c in cells.values())
    gap_parts = max(abs(c['cost']['b'] - sum(c['cost'][k] for k in ('paid_leave', 'supp', 'insurance', 'retirement', 'legal'))) for c in cells.values())
    check('ECEC: total compensation = wages + benefits, and benefits = paid leave + supplemental pay + insurance + retirement + legally required, in every cell (to the cent)',
          gap_b <= 0.011 and gap_parts <= 0.011, 'largest gaps $%.3f and $%.3f per hour (rounding)' % (gap_b, gap_parts))
    ratio = {k: annual_loading(c['cost']) for k, c in cells.items()}                 # TC/(W + PL): the annual-salary loading
    ratio_ns = {k: annual_loading(c['cost'], supp=False) for k, c in cells.items()}  # (TC - supplemental pay)/(W + PL)
    ratio_tcw = {k: c['cost']['tc'] / c['cost']['w'] for k, c in cells.items()}     # round 2's TC/W (leave counted twice)
    rel = {k: loading_rel_se(c['cost'], c['rse']) for k, c in cells.items()}
    rel_tcw = {k: loading_rel_se_tcw(c['cost'], c['rse']) for k, c in cells.items()}
    size_adj = ratio['est_1_49'] / ratio['private']
    L = ratio['mgmt_prof'] * size_adj
    L_lo = ratio_ns['mgmt_prof'] * size_adj
    L_hi = ratio['mgmt_prof']
    L_rel = math.sqrt(rel['mgmt_prof'] ** 2 + rel['est_1_49'] ** 2 + rel['private'] ** 2)
    L_se = L * L_rel
    L_ship, L_se_ship, L_range = round(L, 2), round(L_se, 3), [round(L_lo, 2), round(L_hi, 2)]
    L_alt = dict(mgmt_business_financial=ratio['mgmt_bus_fin'] * size_adj, mgmt_business_financial_all_sizes=ratio['mgmt_bus_fin'],
                 no_supplemental_consistent=ratio_ns['mgmt_prof'] * ratio_ns['est_1_49'] / ratio_ns['private'],
                 establishments_1_49_all_occupations=ratio['est_1_49'], establishments_50_99_scaling=ratio['mgmt_prof'] * ratio['est_50_99'] / ratio['private'],
                 establishments_1_99_scaling=ratio['mgmt_prof'] * ratio['est_1_99'] / ratio['private'],
                 establishments_100_499_scaling=ratio['mgmt_prof'] * ratio['est_100_499'] / ratio['private'],
                 establishments_500_plus_scaling=ratio['mgmt_prof'] * ratio['est_500_plus'] / ratio['private'])
    L_mbf = L_alt['mgmt_business_financial']
    L_tcw = ratio_tcw['mgmt_prof'] * ratio_tcw['est_1_49'] / ratio_tcw['private']
    L_tcw_se = L_tcw * math.sqrt(rel_tcw['mgmt_prof'] ** 2 + rel_tcw['est_1_49'] ** 2 + rel_tcw['private'] ** 2)
    L_sales, L_sales_ns, L_sales_small = ratio['sales'], ratio_ns['sales'], ratio['sales'] * size_adj
    check('GM: loading = 78.88/(54.06+7.37) x [37.64/(27.88+2.34)]/[46.89/(32.82+3.54)] rounds to 1.24, range 1.18-1.28; management, business and financial 1.25',
          (L_ship, L_range, round(L_mbf, 2)) == (1.24, [1.18, 1.28], 1.25),
          'L %.4f = %.4f x %.4f (sampling SE %.4f); low %.4f (management without supplemental pay, same size scaling); high %.4f (management, all sizes); '
          'management, business and financial %.4f' % (L, ratio['mgmt_prof'], size_adj, L_se, L_lo, L_hi, L_mbf))
    check('GM: loading sampling SE below the bridge half-range', L_se < (L_hi - L_lo) / 2,
          'SE %.4f (relative %.2f%%: management %.2f%%, 1-49 workers %.2f%%, all private %.2f%%)' % (
              L_se, 100 * L_rel, 100 * rel['mgmt_prof'], 100 * rel['est_1_49'], 100 * rel['private']))
    check('GM: round 2\'s TC/W loading (paid leave counted twice) is %.4f, %.1f sampling SEs above the corrected one' % (L_tcw, (L_tcw - L) / L_se),
          round(L_tcw, 4) == 1.3788, 'TC/W: management %.4f, 1-49 workers %.4f, all private %.4f; TC/(W+PL): %.4f, %.4f, %.4f' % (
              ratio_tcw['mgmt_prof'], ratio_tcw['est_1_49'], ratio_tcw['private'], ratio['mgmt_prof'], ratio['est_1_49'], ratio['private']), test=False)
    check('growth: sales loading TC/(W+PL) = 35.85/(26.99+2.11) rounds to 1.232 (round 2: TC/W 1.328)', round(L_sales, 3) == 1.232,
          '%.4f (sampling SE %.4f); without supplemental pay %.4f; scaled to 1-49-worker establishments as the GM\'s %.4f' % (
              L_sales, L_sales * rel['sales'], L_sales_ns, L_sales_small))
    with open(os.path.join(OUT, 'ecec_cells.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['key', 'table', 'series', 'total_comp', 'wages', 'benefits', 'paid_leave', 'supplemental_pay', 'rse_total', 'rse_wages',
                     'rse_benefits', 'rse_paid_leave', 'rse_supplemental', 'tc_over_w_plus_pl', 'tc_over_w_plus_pl_no_supp', 'rel_se_ratio',
                     'tc_over_w_round2', 'rel_se_tc_over_w_round2'])
        for k, c in cells.items():
            wr.writerow([k, c['table'], c['name'], c['cost']['tc'], c['cost']['w'], c['cost']['b'], c['cost']['paid_leave'], c['cost']['supp'],
                         c['rse']['tc'], c['rse']['w'], c['rse']['b'], c['rse']['paid_leave'], c['rse']['supp'], round(ratio[k], 5),
                         round(ratio_ns[k], 5), round(rel[k], 5), round(ratio_tcw[k], 5), round(rel_tcw[k], 5)])

    # ---------------------------------------------------------------- 0. node probe (the console's own maps and effects)
    loadings = sorted(set([1, L_range[0], L_ship, round(L_mbf, 2), L_range[1], LOADING_ROUND2] + list(LOADING_RESEARCH)))
    cfg = dict(sde_qoe=[1.5e5, 7e5, 2.5e6], sde_gm=[3e5, 7e5, 2.5e6], sde_cost=[1.5e5, 3e5, 7e5, 2.5e6], loadings=loadings)
    jpath, cpath = os.path.join(WORK, 'probe.js'), os.path.join(WORK, 'probe_cfg.json')
    open(jpath, 'w').write(PROBE_JS)
    json.dump(cfg, open(cpath, 'w'), sort_keys=True)
    r = subprocess.run(['node', jpath, HARNESS, cpath], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    open(os.path.join(WORK, 'probe_out.json'), 'w').write(r.stdout)
    PR = json.loads(r.stdout)
    assert PR['industries'] == INDS, PR['industries']
    MAP = PR['map']
    G = {k: np.log([m[k] for m in MAP]) for k in ('sde', 'ev', 'rev', 'ebitda')}
    check('EV/EBITDA -> revenue maps increase with size', all(np.all(np.diff(G[k]) > 0) for k in ('ev', 'rev', 'ebitda')),
          '%d grid points, SDE $%.0fk-$%.0fM; EV/revenue %.2f-%.2f, EBITDA/revenue %.3f-%.3f' % (
              len(MAP), MAP[0]['sde'] / 1e3, MAP[-1]['sde'] / 1e6, min(m['ev'] / m['rev'] for m in MAP), max(m['ev'] / m['rev'] for m in MAP),
              min(m['ebitda'] / m['rev'] for m in MAP), max(m['ebitda'] / m['rev'] for m in MAP)))
    if os.path.exists(R_MAP):
        RM = json.load(open(R_MAP))
        d = max(abs(a[k] / b[k] - 1) for a, b in zip(MAP, RM) for k in ('sde', 'ev', 'rev', 'ebitda')) if len(RM) == len(MAP) else float('inf')
        check('replication: EV/EBITDA map equals the research round\'s ev_rev_map.json', d < 1e-12, 'max relative difference %.1e' % d)

    # ---------------------------------------------------------------- 0. quotes: QoE tiers
    qrows = []
    for t in TIERS:
        f = os.path.join(DH, t[2])
        if not os.path.exists(f):
            qrows.append(dict(kind='qoe tier', source=t[0], file=t[2], page='', quote=t[11], found='missing file', mode='')); continue
        ok, mode = quote_check(page_text(f), t[11])
        qrows.append(dict(kind='qoe tier', source=t[0], file=t[2], page='', quote=t[11], found=ok, mode=mode))
    nq = sum(1 for q in qrows if q['found'] is True)
    check('every QoE tier quote found on its saved page (numbers and text)', nq == len(TIERS),
          '%d of %d (%d verbatim, %d table rows cell by cell)' % (nq, len(TIERS), sum(1 for q in qrows if q['found'] is True and q['mode'] == 'verbatim'),
                                                                 sum(1 for q in qrows if q['found'] is True and q['mode'] == 'cells')))
    # pages of the checks
    PAGES = dict(SBA_PAGES); PAGES.update(CHECK_PAGES)
    PAGES['GF Data'] = GF_PAGE; PAGES['investmentbank.com'] = IB_PAGE; PAGES['ECEC technical note'] = (ECEC_TN, 'https://www.bls.gov/news.release/ecec.tn.htm')
    PAGES['CT Acquisitions'] = (DH + '/qoe_ctacq_sellside/page.html', 'https://ctacquisitions.com/?p=1636')
    for key, qt in PAGE_QUOTES:
        f = PAGES[key][0]
        ok = quote_check(page_text(f), qt)[0] if os.path.exists(f) else 'missing file'
        qrows.append(dict(kind='check page', source=key, file=f.replace(DH + '/', '').replace(DF + '/', ''), page='', quote=qt, found=ok, mode='verbatim'))
    npq = sum(1 for q in qrows if q['kind'] == 'check page' and q['found'] is True)
    check('every quote of the check pages found (GF Data, investmentbank.com, CT Acquisitions, SBA rule x4, ContractsCounsel, SOP x3, ECEC note)',
          npq == len(PAGE_QUOTES), '%d of %d' % (npq, len(PAGE_QUOTES)))
    # PDFs
    if have_pdftotext():
        npdf = 0
        for pdf, pg, kind, exp in PDF_QUOTES:
            raw = pdf_page(pdf, pg)
            if kind == 'text':
                ok = norm(exp) in norm(raw)
            else:
                seq = [int(v) for v in re.findall(r'(?<![\d.])(\d+)\s*%', raw)]
                ok = seq[:len(exp)] == exp
            npdf += bool(ok)
            qrows.append(dict(kind='pdf', source=os.path.basename(os.path.dirname(pdf)), file=pdf.replace(DH + '/', ''), page=pg,
                              quote=exp if kind == 'text' else 'bar labels in order: ' + ' '.join(map(str, exp)), found=bool(ok), mode=kind))
        check('every transcribed PDF number found on its page (SHRM, Firmex, Bridge Group; pdftotext -layout)', npdf == len(PDF_QUOTES),
              '%d of %d' % (npdf, len(PDF_QUOTES)))
    else:
        check('PDF numbers (pdftotext not installed: not checked)', True, 'skipped', test=False)
    with open(os.path.join(OUT, 'quotes.csv'), 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['kind', 'source', 'file', 'page', 'found', 'mode', 'quote']); wr.writeheader(); wr.writerows(qrows)

    # ---------------------------------------------------------------- 1. QoE cost
    T = build(G)
    T_r = build(G, coding='research')            # the research round's side coding: replication only
    x, y, w = T.rev.values, np.log(T.fee.values), src_weights(T)
    F, s, loss = fit_max(x, y, w)
    kink = F / s
    rng = np.random.default_rng(SEED)
    bm, bp, skipped = cluster_boot(T, B_BOOT, rng)
    bm_r, bp_r, skipped_r = cluster_boot(T_r, B_BOOT, np.random.default_rng(SEED))
    F_se, s_se = float(bm[:, 0].std(ddof=1)), float(bm[:, 1].std(ddof=1))
    F_ship, s_ship = rnd(F, STEP_FLOOR), rnd(s, STEP_SHARE)
    F_se_ship, s_se_ship = rnd(F_se, 10), rnd(s_se, 1e-5)
    n_below = int((x < kink).sum()); src_below = int(T[T.rev < kink].src.nunique())
    min_rev = float(x.min())
    recoded = [(r_.label, r_.side, T_r.side[i]) for i, r_ in T.iterrows() if r_.side != T_r.side[i]]
    check('QoE: livmo $5M-$100M tier coded generic, as the page presents it (research coding: sell); the pooled fit and the cluster-bootstrap '
          'draws do not depend on the side', recoded == [('livmo', 'generic', 'sell')] and fit_T(T_r) == (F, s, loss) and np.array_equal(bm, bm_r),
          'recoded %s; max-form fit and %d bootstrap draws identical under both codings; the side-dummy power curve keeps %d of %d draws (research '
          'coding %d)' % (recoded, B_BOOT, len(bp), B_BOOT, len(bp_r)))
    check('QoE: 33 tiers from 15 independent sources inside $250k-$60M of revenue', len(T) == 33 and T.src.nunique() == 15,
          '%d tiers, %d sources; revenue midpoints $%.2fM-$%.1fM; %d tiers (%d sources) below the kink' % (
              len(T), T.src.nunique(), x.min() / 1e6, x.max() / 1e6, n_below, src_below))
    bp_pow = fit_pow(x, y, w, T.side.values, True); bp_pool = fit_pow(x, y, w, T.side.values, False)
    loso = []
    for src in list(dict.fromkeys(T.src)):
        Tl = T[T.src != src]; f_, s_, _ = fit_T(Tl)
        b_ = fit_pow(Tl.rev.values, np.log(Tl.fee.values), src_weights(Tl), Tl.side.values, True)
        loso.append(dict(left_out=src, tiers=int((T.src == src).sum()), floor=round(f_), share=round(s_, 6), share_5=round(s_, 5),
                         kink_revenue=round(f_ / s_), power_sell_at_5M=round(pow_pred(b_, 5e6, 'sell')), elasticity=round(float(b_[1]), 3)))
    pd.DataFrame(loso).to_csv(os.path.join(OUT, 'qoe_loso.csv'), index=False)
    sens_specs = [('map conversion (shipped)', dict()),
                  ('constant EV/rev .5, EBITDA/rev .12', dict(conv='const', evr=.5, ebr=.12)),
                  ('constant EV/rev .75, EBITDA/rev .15', dict(conv='const', evr=.75, ebr=.15)),
                  ('constant EV/rev 1.0, EBITDA/rev .25', dict(conv='const', evr=1.0, ebr=.25)),
                  ('sell-side tiers only', dict(sides=('sell',))),
                  ('sell + generic tiers', dict(sides=('sell', 'generic'))),
                  ('revenue $1M-$20M tiers only', dict(lo_rev=1e6, hi_rev=2e7)),
                  ('buy-side fees x1.2 (sell-side premium)', dict(buy_mult=BUY_PREMIUM))]
    sens, sens_r = [], []
    for coding, out_ in (('shipped', sens), ('research', sens_r)):
        for lab, kw in sens_specs:
            Ts = build(G, coding=coding, **kw); f_, s_, _ = fit_T(Ts)
            sides_ok = Ts.side.nunique() == 3
            b_ = fit_pow(Ts.rev.values, np.log(Ts.fee.values), src_weights(Ts), Ts.side.values, sides_ok)
            out_.append(dict(spec=lab, coding=coding, tiers=len(Ts), sources=int(Ts.src.nunique()), floor=round(f_), share=round(s_, 6),
                             share_5=round(s_, 5), fee_at_2M=round(max(f_, s_ * 2e6)), fee_at_10M=round(max(f_, s_ * 1e7)),
                             fee_at_20M=round(max(f_, s_ * 2e7)), power_level_5M=round(pow_pred(b_, 5e6, 'sell') if sides_ok else pow_pred(b_, 5e6)),
                             elasticity=round(float(b_[1]), 3)))
    S = {r['spec']: r for r in sens}
    S_r = {r['spec']: r for r in sens_r}
    side_specs = [k for k in S if (S[k]['tiers'], S[k]['floor'], S[k]['share']) != (S_r[k]['tiers'], S_r[k]['floor'], S_r[k]['share'])]
    pd.DataFrame(sens + [dict(r, spec=r['spec'] + ' (research coding: livmo $5M-$100M sell)') for r in sens_r if r['spec'] in side_specs]).to_csv(
        os.path.join(OUT, 'qoe_sensitivity.csv'), index=False)
    check('QoE: the recoding moves only the side subsets: sell-side only %d -> %d tiers, floor $%s -> $%s, share %.3f%% -> %.3f%%' % (
        S_r['sell-side tiers only']['tiers'], S['sell-side tiers only']['tiers'], f'{S_r["sell-side tiers only"]["floor"]:,}',
        f'{S["sell-side tiers only"]["floor"]:,}', 100 * S_r['sell-side tiers only']['share'], 100 * S['sell-side tiers only']['share']),
          side_specs == ['sell-side tiers only'], 'specs that changed: %s; sell + generic unchanged (livmo was in it either way)' % side_specs)
    SENS_KEY = {'constant EV/rev .5, EBITDA/rev .12': 'const_low', 'constant EV/rev .75, EBITDA/rev .15': 'const_mid',
                'constant EV/rev 1.0, EBITDA/rev .25': 'const_high', 'sell-side tiers only': 'sell_only', 'sell + generic tiers': 'sell_generic',
                'revenue $1M-$20M tiers only': 'rev_1m_20m', 'buy-side fees x1.2 (sell-side premium)': 'buy_x1_2'}
    conv_rows = [r for r in sens if r['spec'].startswith('constant')]
    cvf = cv_forms(T)
    revs = [5e5, 1e6, 2e6, 5e6, 1e7, 2e7]
    pred = []
    for rv in revs:
        ps = [pow_pred(b, rv, 'sell') for b in bp]; pg = [pow_pred(b, rv, 'generic') for b in bp]
        pred.append(dict(revenue=rv, console=max(cur['qoe']['floor'], cur['qoe']['share'] * rv), shipped=max(F_ship, s_ship * rv),
                         max_form=max(F, s * rv), power_pooled=pow_pred(bp_pool, rv), power_generic=pow_pred(bp_pow, rv, 'generic'),
                         power_sell=pow_pred(bp_pow, rv, 'sell'), power_sell_p5_p95=[float(np.percentile(ps, 5)), float(np.percentile(ps, 95))],
                         power_generic_p5_p95=[float(np.percentile(pg, 5)), float(np.percentile(pg, 95))]))
    # tiers table
    T_out = T.copy(); T_out['weight'] = w; T_out['fit_max_form'] = np.maximum(F, s * x)
    T_out[['src', 'label', 'side', 'basis', 'tier_lo', 'tier_hi', 'rev_lo', 'rev_hi', 'rev', 'fee_lo', 'fee_hi', 'fee', 'weight', 'fit_max_form', 'url', 'file']].round(2).to_csv(
        os.path.join(OUT, 'qoe_tiers.csv'), index=False)
    # days: one vote per source, sell-side preferred
    wk = {}
    for (label, url, lf, basis, tlo, thi, flo, fhi, side, wlo, whi, quote) in TIERS:
        if wlo is None:
            continue
        srcn = label.split('_')[0]; mid = (wlo + (whi if whi is not None else wlo)) / 2
        rank = {'sell': 0, 'generic': 1, 'buy': 2}[side]
        wk.setdefault(srcn, []).append((rank, mid))
    per = {k: min(v)[0] for k, v in wk.items()}
    mids = {k: float(np.mean([m for r_, m in v if r_ == per[k]])) for k, v in wk.items()}
    wk_all = np.array(sorted(mids.values())); wk_sell = np.array(sorted(m for k, m in mids.items() if per[k] == 0))
    mids_r = {k: float(np.mean([m for r_, m in v])) for k, v in wk.items()}     # research definition: all of a source's rows
    weeks = dict(n_sources=len(mids), median_weeks=float(np.median(wk_all)), p25_p75=[float(np.percentile(wk_all, 25)), float(np.percentile(wk_all, 75))],
                 research_definition_median_weeks=float(np.median(list(mids_r.values()))),
                 sell_side_sources=int(len(wk_sell)), sell_side_median_weeks=float(np.median(wk_sell)),
                 by_source={k: dict(weeks=round(mids[k], 2), side=['sell', 'generic', 'buy'][per[k]]) for k in sorted(mids)})
    # tests
    check('QoE: exact solver; the console form refit is F $%s, s %.4f%%' % (f'{F:,.0f}', 100 * s), loss >= 0 and 1e4 < F < 3e4 and 1e-3 < s < 4e-3,
          'loss %.6f; kink at $%.2fM of revenue' % (loss, kink / 1e6))
    check('QoE: shipped values are the analyst\'s rounding of the refit (F to $100, s to 0.0001)',
          (F_ship, s_ship) == (16400, 0.0019), 'F %.1f -> %d; s %.6f -> %.4f' % (F, F_ship, s, s_ship))
    lo_f, hi_f = min(r['floor'] for r in loso), max(r['floor'] for r in loso)
    lo_s, hi_s = min(r['share'] for r in loso), max(r['share'] for r in loso)
    check('QoE: leave one source out keeps the floor within $15.7k-$17.3k and the share within 0.17%-0.20%',
          15700 <= lo_f and hi_f <= 17300 and 0.0017 <= lo_s and hi_s <= 0.0020,
          'floor $%s-$%s, share %.3f%%-%.3f%% (15 fits)' % (f'{lo_f:,}', f'{hi_f:,}', 100 * lo_s, 100 * hi_s))
    check('QoE: floor robust to the size conversion (constant maps within 5% of the map-based floor)',
          all(abs(r['floor'] / F - 1) < .05 for r in conv_rows),
          'floors %s; shares %s' % ([r['floor'] for r in conv_rows], [round(100 * r['share'], 3) for r in conv_rows]))
    rb = research_boot(T_r)                   # its skip rule (all three sides drawn) depends on the side coding
    check('QoE: the cluster bootstrap is wider than the research round\'s label-weighted resampling (which keeps a source drawn k times at weight 1)',
          F_se > rb['floor_se'] and s_se > rb['share_se'],
          'cluster SE: floor $%.0f, share %.4f%%; label-weighted: $%d, %.4f%% (B = %d each)' % (F_se, 100 * s_se, rb['floor_se'], 100 * rb['share_se'], B_BOOT))
    check('QoE: max form predicts held-out sources about as well as the pooled power curve (leave-one-source-out MSLE within 10%)',
          cvf['max_form']['msle'] <= cvf['power_pooled']['msle'] * 1.10,
          ', '.join('%s %.3f' % (k, v['rmsle']) for k, v in cvf.items()))
    check('QoE days: median report turnaround %.1f weeks over %d sources (sell-side %.1f); the console\'s 60 days is kept' % (
        weeks['median_weeks'], weeks['n_sources'], weeks['sell_side_median_weeks']),
          weeks['n_sources'] == 11 and 7 * weeks['median_weeks'] <= cur['qoe']['days'], 'IQR %.1f-%.1f weeks' % tuple(weeks['p25_p75']))
    # research replication
    rep = {}
    if os.path.exists(R_QOE):
        RQ = json.load(open(R_QOE))
        rep['qoe'] = dict(research=dict(floor=RQ['base']['maxform']['floor'], share=RQ['base']['maxform']['share'],
                                        floor_se=RQ['base']['maxform']['floor_se'], share_se=RQ['base']['maxform']['share_se']),
                          reproduced=dict(floor=round(F), share=round(s, 5), **{k: rb[k] for k in ('floor_se', 'share_se', 'floor_p5_p95', 'share_p5_p95')}))
        ok = (round(F) == RQ['base']['maxform']['floor'] and round(s, 5) == RQ['base']['maxform']['share']
              and rb['floor_se'] == RQ['base']['maxform']['floor_se'] and abs(rb['share_se'] - RQ['base']['maxform']['share_se']) < 1.5e-5)
        check('replication: research QoE fit and its (label-weighted) bootstrap SEs reproduced', ok,
              'F %d (research %d), s %.5f (%.5f), SE %d (%d) and %.5f (%.5f)' % (
                  round(F), RQ['base']['maxform']['floor'], s, RQ['base']['maxform']['share'], rb['floor_se'],
                  RQ['base']['maxform']['floor_se'], rb['share_se'], RQ['base']['maxform']['share_se']))
        okl = all(RQ['leave_one_source_out'][r['left_out']]['floor'] == r['floor'] and
                  RQ['leave_one_source_out'][r['left_out']]['share'] == r['share_5'] for r in loso)
        check('replication: research leave-one-source-out fits reproduced (15 of 15)', okl, 'floors and shares to the research rounding')
        rs = RQ['sensitivity']; keymap = {'constant EV/rev .5, EBITDA/rev .12': 'EV/rev .5, EBITDA/rev .12',
                                          'constant EV/rev .75, EBITDA/rev .15': 'EV/rev .75, EBITDA/rev .15',
                                          'constant EV/rev 1.0, EBITDA/rev .25': 'EV/rev 1.0, EBITDA/rev .25',
                                          'sell-side tiers only': 'sell-side tiers only', 'sell + generic tiers': 'sell + generic only',
                                          'revenue $1M-$20M tiers only': 'revenue $1M-$20M tiers only'}
        oks = all(rs[v]['floor'] == S_r[k]['floor'] and rs[v]['share'] == S_r[k]['share_5'] and rs[v]['n'] == S_r[k]['tiers'] for k, v in keymap.items())
        check('replication: research conversion and subset sensitivities reproduced (6 of 6, research side coding)', oks, 'floor, share and tier counts')

    # ---------------------------------------------------------------- 2. GM: value effect by loading (node) and hire cost
    #                                                                     (the ECEC loadings are computed in step 2a)
    hire = SHRM['exec_cph_2025']
    gm_days, gm_payroll_alt = cur['gm']['days'], cur['gm']['days'] - SHRM['exec_ttf_2025']
    gm = pd.DataFrame(PR['gm'])
    gm_tab = []
    for Lv in cfg['loadings']:
        row = dict(L=Lv, framework=float(gm[(gm.L == Lv) & (gm.ind == 'framework')].dV.iloc[0]))
        for e in cfg['sde_gm']:
            d = np.sort(gm[(gm.L == Lv) & (gm.ern == e) & (gm.ind != 'framework')].dV.values)
            row['sde_%dk' % (e / 1e3)] = dict(median=float(np.median(d)), upper_median=float(d[8]), min=float(d[0]), max=float(d[-1]), negative=int((d < 0).sum()))
        gm_tab.append(row)
    G1 = {r['L']: r for r in gm_tab}
    if os.path.exists(RESEARCH + '/out/gm_loading.txt'):
        okg = (round(100 * G1[1]['framework'], 1), round(100 * G1[1.35]['framework'], 1), round(100 * G1[1.48]['framework'], 1)) == (4.6, 2.7, 2.0) and \
              [round(100 * G1[Lv]['sde_300k']['upper_median'], 1) for Lv in (1, 1.35, 1.48)] == [1.1, -5.7, -8.3] and \
              [G1[Lv]['sde_300k']['negative'] for Lv in (1, 1.35, 1.48)] == [8, 15, 16] and \
              [G1[Lv]['sde_700k']['negative'] for Lv in (1, 1.35, 1.48)] == [0, 1, 3]
        check('replication: research GM loading table reproduced (framework +4.6/+2.7/+2.0%; $300k median +1.1/-5.7/-8.3%, negative 8/15/16 of 16)',
              okg, 'L = 1, 1.35, 1.48')
    mono = all(all(G1[a][k]['median'] > G1[b][k]['median'] for k in ('sde_300k', 'sde_700k', 'sde_2500k')) and G1[a]['framework'] > G1[b]['framework']
               for a, b in zip(cfg['loadings'][:-1], cfg['loadings'][1:]))
    check('GM: the value effect falls with the loading at every size (the earnings charge scales with L)', mono,
          'medians at $300k: ' + ', '.join('L %s %+.1f%%' % (Lv, 100 * G1[Lv]['sde_300k']['median']) for Lv in cfg['loadings']))

    def gm_line(Lv):
        g_ = G1[Lv]
        return 'L %s: $300k median %+.1f%% (negative in %d of 16); $700k %+.1f%% (%d); $2.5M %+.1f%% (%d); framework example %+.1f%%' % (
            Lv, 100 * g_['sde_300k']['median'], g_['sde_300k']['negative'], 100 * g_['sde_700k']['median'], g_['sde_700k']['negative'],
            100 * g_['sde_2500k']['median'], g_['sde_2500k']['negative'], 100 * g_['framework'])
    check('GM: value effect at the shipped loading %.2f, against round 2\'s %.2f and the console\'s 1' % (L_ship, LOADING_ROUND2), True,
          '%s. Round 2: %s. Console: %s' % (gm_line(L_ship), gm_line(LOADING_ROUND2), gm_line(1)), test=False)

    # ---------------------------------------------------------------- 3. growth floor
    alt_cells = [c for v in SALES_ALT.values() for c in v[0]]
    frames, vet_frames = [], []
    for fn in OEWS_FILES:
        X = pd.read_excel(os.path.join(OEWS_DIR, fn), dtype=str); X.columns = [c.upper() for c in X.columns]
        V = X[(X.NAICS == VET_CELL) & X.OCC_CODE.isin(VET_OCCS + OCC_SALES)].copy(); V['FILE'] = fn; vet_frames.append(V)
        X = X[X.OCC_CODE.isin(OCC_SALES) & X.NAICS.isin(list(SALES_CELL.values()) + alt_cells + REST_CONTEXT)].copy(); X['FILE'] = fn
        frames.append(X)
    D = pd.concat(frames).drop_duplicates(['NAICS', 'OCC_CODE']).reset_index(drop=True)
    VR = pd.concat(vet_frames).drop_duplicates(['NAICS', 'OCC_CODE']).set_index('OCC_CODE')
    assert sorted(VR.index) == sorted(VET_OCCS), ('veterinary services (541940): expected no sales-rep rows', sorted(VR.index))
    rel_common = math.hypot(rel['sales'], ECI_REL_SE)
    hire_ne = SHRM['nonexec_cph_2025']; days_g = cur['growth']['days']
    ttf_ne = SHRM['nonexec_ttf_2025']; pay_days = days_g - ttf_ne

    def cost(wage, loading=L_sales, days=pay_days):
        """one sales hire: annual wage x ECI x loading x payroll days / 365 + the non-executive cost-per-hire"""
        return wage * G_ECI * loading * days / 365 + hire_ne

    SE_KEYS = ('sampling', 'wage_statistic', 'payroll_days', 'proxy', 'common')
    gf, gf_rows = {}, []
    for ind in INDS:
        pw = pooled_wage(D, [SALES_CELL[ind]])
        c = cost(pw['median'])
        comp = dict(sampling=pw['rel_se_median'] * (c - hire_ne),                    # OEWS sampling of the median
                    wage_statistic=abs(cost(pw['mean']) - c) / 2,                     # half the gap to the mean-wage floor
                    payroll_days=abs(cost(pw['median'], days=days_g) - c) / 2,        # half the gap to 270 payroll days
                    proxy=0.0, common=(c - hire_ne) * rel_common)                     # loading and ECI (every industry)
        alt_cell = None
        if ind in SALES_ALT:
            pa = pooled_wage(D, SALES_ALT[ind][0])
            alt_cell = dict(cells=SALES_ALT[ind][1], why=SALES_ALT[ind][2], title=pa['title'], median=pa['median'], mean=pa['mean'],
                            employment=pa['employment'], rel_se_median=pa['rel_se_median'], cost=cost(pa['median']), notes=pa['notes'])
            comp['proxy'] = abs(alt_cell['cost'] - c) / 2                              # half the gap to the alternative cell
        se = math.sqrt(sum(comp[k] ** 2 for k in SE_KEYS))
        r2 = dict(cost=pw['mean'] * G_ECI * ratio_tcw['sales'] * days_g / 365 + hire_ne,     # round 2 and the research round:
                  cost_se=pw['se_mean'] * G_ECI * ratio_tcw['sales'] * days_g / 365)         # mean, TC/W, 270 days
        alt = dict(mean_wage=cost(pw['mean']), payroll_270_days=cost(pw['median'], days=days_g),
                   no_supplemental=cost(pw['median'], L_sales_ns), loading_small_establishments=cost(pw['median'], L_sales_small),
                   suppressed_dropped=cost(pooled_wage(D, [SALES_CELL[ind]], True)['median']), wmean_of_medians=cost(pw['wmean_of_medians']))
        gf[ind] = dict(pw, cost=c, se=se, comp=comp, alt=alt, alt_cell=alt_cell, round2=r2)
        gf_rows.append(dict(ind=ind, naics=SALES_CELL[ind], title=pw['title'], file=pw['file'], occupations=' '.join(pw['occs']),
                            employment=pw['employment'], median_may2025=round(pw['median']), rel_se_median=round(pw['rel_se_median'], 4),
                            mean_may2025=round(pw['mean']), median_over_mean=round(pw['median'] / pw['mean'], 3),
                            wmean_of_occ_medians=round(pw['wmean_of_medians']), loaded_annual_2026q2=round(pw['median'] * G_ECI * L_sales),
                            payroll_days=pay_days, cost=round(c), se=round(se), shipped=rnd(c, 100), shipped_se=rnd(se, 10),
                            **{'se_' + k: round(comp[k]) for k in SE_KEYS},
                            alt_mean_wage=round(alt['mean_wage']), alt_payroll_270=round(alt['payroll_270_days']),
                            alt_no_supplemental=round(alt['no_supplemental']), alt_loading_small_est=round(alt['loading_small_establishments']),
                            alt_suppressed_dropped=round(alt['suppressed_dropped']), alt_wmean_of_medians=round(alt['wmean_of_medians']),
                            proxy_alt_cell=alt_cell['cells'] if alt_cell else '', proxy_alt_cost=round(alt_cell['cost']) if alt_cell else '',
                            round2_shipped=rnd(r2['cost'], 100), round2_cost=round(r2['cost']), current=cur['growth']['floor'],
                            weak_proxy=ind in WEAK_PROXY, proxy=SALES_NOTE.get(ind, ''), notes='; '.join(pw['notes'])))
    pd.DataFrame(gf_rows).to_csv(os.path.join(OUT, 'growth_floor.csv'), index=False)
    gvals = np.array([gf[i]['cost'] for i in INDS])
    ok_med = all(gf[i]['occ_median_range'][0] - 1e-6 <= gf[i]['median'] <= gf[i]['occ_median_range'][1] + 1e-6 for i in INDS)
    check('growth floor: 16 industries; every cell has a sales occupation; each pooled median lies between its occupations\' medians',
          len(gf) == 16 and all(gf[i]['occs'] and gf[i]['se'] > 0 for i in INDS) and ok_med,
          'one hire for %d payroll days: $%s (fit) to $%s (saas), median $%s; round 2 $%s-$%s; the console has $%s for every industry' % (
              pay_days, f'{gvals.min():,.0f}', f'{gvals.max():,.0f}', f'{np.median(gvals):,.0f}', f'{min(gf[i]["round2"]["cost"] for i in INDS):,.0f}',
              f'{max(gf[i]["round2"]["cost"] for i in INDS):,.0f}', f'{cur["growth"]["floor"]:,}'))
    cover = {i: max(abs(gf[i]['alt']['mean_wage'] - gf[i]['cost']), abs(gf[i]['alt']['payroll_270_days'] - gf[i]['cost']),
                    abs(gf[i]['alt_cell']['cost'] - gf[i]['cost']) if gf[i]['alt_cell'] else 0.0) / gf[i]['se'] for i in INDS}
    check('growth floor: the SE covers the bridge choices: the mean-wage floor, the 270-payroll-day floor and the proxy alternative lie within 2 SE',
          max(cover.values()) <= 2 + 1e-9, 'largest distance %.2f SE (%s); relative SE %.1f%%-%.1f%%' % (
              max(cover.values()), max(cover, key=cover.get), 100 * min(gf[i]['se'] / gf[i]['cost'] for i in INDS),
              100 * max(gf[i]['se'] / gf[i]['cost'] for i in INDS)))
    mm = {i: gf[i]['median'] / gf[i]['mean'] for i in INDS}
    dmed = {i: gf[i]['wmean_of_medians'] / gf[i]['median'] - 1 for i in INDS}
    check('growth floor: pooled median / mean wage %.3f (median over the 16 cells; range %.3f-%.3f); the employment-weighted mean of the occupation '
          'medians is within %.1f%% of the pooled median' % (float(np.median(list(mm.values()))), min(mm.values()), max(mm.values()), 100 * max(abs(v) for v in dmed.values())),
          True, 'largest gap %s; the bridge term for mean against median is %.1f%%-%.1f%% of the floor' % (
              max(dmed, key=lambda k: abs(dmed[k])), 100 * min(gf[i]['comp']['wage_statistic'] / gf[i]['cost'] for i in INDS),
              100 * max(gf[i]['comp']['wage_statistic'] / gf[i]['cost'] for i in INDS)), test=False)
    if os.path.exists(R_SALES):
        RS = json.load(open(R_SALES))['by_industry']
        oks = all(RS[i]['cost_270d'] == round(gf[i]['round2']['cost']) and RS[i]['cost_270d_se'] == round(gf[i]['round2']['cost_se']) and
                  RS[i]['mean_wage_may2025'] == round(gf[i]['mean']) and RS[i]['employment'] == gf[i]['employment'] for i in INDS)
        check('replication: research sales-cost table reproduced on its basis (mean wage, TC/W, 270 days; 16 of 16: wage, employment, cost and SE)',
              oks, 'sales_cost_v2.json')
    n_supp = sum(1 for i in INDS for n_ in gf[i]['notes'] if '-> weight' in n_)
    max_supp = max(abs(gf[i]['alt']['suppressed_dropped'] / gf[i]['cost'] - 1) for i in INDS)
    check('growth floor: suppressed OEWS employments (weight 50) move no floor by more than 1%', max_supp < .01,
          '%d suppressed rows; largest change if dropped %.2f%%' % (n_supp, 100 * max_supp))
    # the analyst's flags, written from the data
    vt = {k: dict(emp=num(VR.loc[k, 'TOT_EMP']), median=num(VR.loc[k, 'A_MEDIAN'])) for k in VET_OCCS}
    acc = D[D.NAICS == '721000']; fsr = D[D.NAICS == '722511']; r725 = D[(D.NAICS == '722500') & (D.OCC_CODE == '41-3091')].iloc[0]
    n_acc = int(sum(num(v) or 0 for v in acc.TOT_EMP)); n_fsr = int(sum(num(v) or 0 for v in fsr.TOT_EMP))
    flags = {
        'vet': 'weak proxy: %s %s contains veterinary services (541940), but its %s pooled sales reps work almost entirely outside it: '
               '541940 employs %s sales and related workers in all among %s (median $%s; %s of them retail sales workers) and %s marketing '
               'specialists (13-1161, median $%s). The alternative, %s offices of physicians (the clinical-practice analog), gives $%s against $%s; '
               'half the gap ($%s) is in the SE' % (
                   SALES_CELL['vet'], gf['vet']['title'], f'{gf["vet"]["employment"]:,}', f'{vt["41-0000"]["emp"]:,.0f}', f'{vt["00-0000"]["emp"]:,.0f}',
                   f'{vt["41-0000"]["median"]:,.0f}',
                   f'{vt["41-2000"]["emp"]:,.0f}', f'{vt["13-1161"]["emp"]:,.0f}', f'{vt["13-1161"]["median"]:,.0f}', SALES_ALT['vet'][1],
                   f'{rnd(gf["vet"]["alt_cell"]["cost"], 100):,}',
                   f'{rnd(gf["vet"]["cost"], 100):,}', f'{rnd(gf["vet"]["comp"]["proxy"], 10):,}'),
        'rest': 'weak proxy: sector 72 includes hotels, which employ %s of its %s sales reps (721000); restaurants and other eating places (722500) '
                'employ %s, their services-sales row at a mean-wage PRSE of %s%%, and full-service restaurants (722511) %s wholesale-type reps only. '
                'On medians the restaurant cell is close: $%s against $%s; half the gap ($%s) is in the SE' % (
                    f'{n_acc:,}', f'{gf["rest"]["employment"]:,}', f'{gf["rest"]["alt_cell"]["employment"]:,}', r725.MEAN_PRSE, f'{n_fsr:,}',
                    f'{rnd(gf["rest"]["alt_cell"]["cost"], 100):,}', f'{rnd(gf["rest"]["cost"], 100):,}', f'{rnd(gf["rest"]["comp"]["proxy"], 10):,}')}
    check('growth floor: vet and rest flagged as weak proxies (the analyst\'s decision); every proxy cell carries an alternative-cell term in its SE',
          sorted(flags) == sorted(WEAK_PROXY) and all(gf[i]['comp']['proxy'] > 0 for i in SALES_ALT) and set(SALES_ALT) == set(SALES_NOTE),
          '; '.join('%s: %s $%s vs $%s (proxy SE $%s)' % (i, SALES_ALT[i][1], f'{gf[i]["alt_cell"]["cost"]:,.0f}', f'{gf[i]["cost"]:,.0f}',
                                                           f'{gf[i]["comp"]["proxy"]:,.0f}') for i in sorted(SALES_ALT)))

    # ---------------------------------------------------------------- 4. checks that stay judgment
    qoe_df = pd.DataFrame(PR['qoe'])
    qoe_eff = {}
    for e in cfg['sde_qoe']:
        d = qoe_df[qoe_df.ern == e]
        qoe_eff['sde_%dk' % (e / 1e3)] = dict(dV_median=float(d.dV.median()), dV_min=float(d.dV.min()), dV_max=float(d.dV.max()),
                                              value_median=float(d.V.median()), revenue_median=float(d.rev.median()), fin=float(d.fin.median()))
    check('replication: console QoE value effect +13.3% / +10.2% / +7.5% at SDE $150k / $700k / $2.5M (every industry)',
          [round(100 * qoe_eff[k]['dV_min'], 1) for k in ('sde_150k', 'sde_700k', 'sde_2500k')] == [13.3, 10.2, 7.5] and
          [round(100 * qoe_eff[k]['dV_max'], 1) for k in ('sde_150k', 'sde_700k', 'sde_2500k')] == [13.3, 10.2, 7.5],
          'research interv_effects.txt')
    lift = GFDATA['with'] / GFDATA['without'] - 1
    ev3 = float(np.exp(np.interp(math.log(3e6), G['ev'], G['sde'])))    # SDE at which the median peer business is worth $3M
    # outreach (Firmex)
    days_out = cur['outreach']['days']
    mon = [(a, b) for (_, a, b, p23, p22) in FIRMEX_MONTHLY if a is not None]
    modal = max(FIRMEX_MONTHLY, key=lambda r: r[3])
    cum, fixed_med = 0.0, None
    tot = sum(r[3] for r in FIRMEX_FIXED if r[0] != 'Other')
    for lab, a, b, p23, p22 in FIRMEX_FIXED:
        if lab == 'Other':
            continue
        cum += p23
        if fixed_med is None and cum >= tot / 2:
            fixed_med = lab
    out_months = days_out / 30.44
    out_modal = out_months * (modal[1] + modal[2]) / 2
    js_checks = {
        'qoe_days': dict(console=cur['qoe']['days'], report_weeks_median=weeks['median_weeks'], report_weeks_p25_p75=weeks['p25_p75'],
                         sources=weeks['n_sources'], sell_side_weeks_median=weeks['sell_side_median_weeks'], sell_side_sources=weeks['sell_side_sources'],
                         note='report turnaround; CT Acquisitions plans 8-12 weeks from kickoff to final report for sell-side work, and two advisors quoted '
                              'by Middle Market Growth recommend starting three to six months ahead of a sale process. 60 days = report time plus kickoff and '
                              'document gathering: kept (judgment)'),
        'qoe_effect': dict(console_fin_floor=qoe_fin, console_value_effect={k: round(v['dV_median'], 4) for k, v in qoe_eff.items()},
                           console_value_at={k: rnd(v['value_median'], 1000) for k, v in qoe_eff.items()},
                           gfdata_tev_ebitda_with=GFDATA['with'], gfdata_tev_ebitda_without=GFDATA['without'], gfdata_lift=round(lift, 4),
                           gfdata_n=GFDATA['n'], gfdata_period='deals closed since Q3 2024 (published fall 2025)',
                           gfdata_population='PE-sponsored deals in GF Data (TEV about $10M-$500M); no SE published',
                           size_note='lift most notable above $50M EV; smaller deals tended not to see a valuation boost (investmentbank.com: below $25M EV the lift narrows and can disappear)',
                           note='uncontrolled comparison (selection into QoE, PE population); the console effect looks too large at the sizes it serves; stays judgment'),
        'sba_qoe_rule': dict(rule='SBA SOP 50 10 8.1', effective='2026-10-01', purchase_price_threshold=3000000,
                             applies_to='7(a) change-of-ownership loans for initial acquisitions and business expansions; owner buyouts and ESOP/co-op deals exempt; owner-occupied real estate excluded from the threshold',
                             report='independent QoE engaged by and for the lender; a buyer- or seller-commissioned report does not satisfy it; QoE-adjusted earnings feed the debt-service coverage',
                             console_sde_at_3M_value=rnd(ev3, 1000),
                             implication='for SBA-financed buyers at $3M and up a sell-side QoE cannot replace the lender\'s report, which argues for a smaller fin effect there; not modelled',
                             sources=sorted(SBA_PAGES)),
        'outreach_cost': dict(console_cost=int(re.sub(r'\D', '', cur['outreach']['cost'])), console_days=days_out, firmex_n=FIRMEX_N,
                              monthly_fee_shares_2023={r[0]: r[3] for r in FIRMEX_MONTHLY}, fixed_fee_shares_2023={r[0]: r[3] for r in FIRMEX_FIXED},
                              modal_monthly_fee=modal[0], cost_at_modal_monthly_fee=rnd(out_modal, 100), median_fixed_fee_bracket=fixed_med,
                              small_firm_note='firms with 20 or fewer employees typically charged $15,000 or less upfront; larger firms most commonly $25,000 or more',
                              note='inside the published fee range: benchmark check, kept (judgment); the x2.2 buyer multiplier has no source'),
        'sops_cost': dict(console=dict(floor=cur['sops']['floor'], share=cur['sops']['share'], days=cur['sops']['days']),
                          franchise_operations_manual=[9000, 20000], freelance_sop_project=[3000, 10000], complex_sop_project_over=20000,
                          sop_project_months=[1, 3], eos_implementation_per_year=[20000, 45000], eos_years=2,
                          note='the floor and the days are inside these ranges; projects are priced by scope, so the 0.6% share is not identified; kept (judgment)'),
        'contracts_cost': dict(console=dict(floor=cur['contracts']['floor'], share=cur['contracts']['share'], days=cur['contracts']['days']),
                               msa_draft_avg=980, msa_review_avg=580, projects=326,
                               legal_share_of_floor=round(980 / cur['contracts']['floor'], 3),
                               note='legal drafting is a small part; the commercial cost of converting customers to contracts is unpublished; kept (judgment)'),
        'gm_days': dict(console=cur['gm']['days'], shrm_exec_time_to_fill_days=SHRM['exec_ttf_2025'], shrm_exec_time_to_fill_days_2022=SHRM['exec_ttf_2022'],
                        remainder_days=cur['gm']['days'] - SHRM['exec_ttf_2025'],
                        note='time-to-fill runs from requisition to accepted offer; the remaining notice and transition time has no source; kept (judgment)'),
        'growth_days': dict(console=days_g, shrm_nonexec_time_to_fill_days=SHRM['nonexec_ttf_2025'], bridge_group_ramp_months=BRIDGE['ramp_months'],
                            days_to_full_productivity=round(SHRM['nonexec_ttf_2025'] + BRIDGE['ramp_months'] * 30.44), floor_payroll_days=pay_days,
                            note='SaaS account executives (Bridge Group, 253 companies) as the only measured ramp; 270 days leaves about two productive months '
                                 'before the sale; the floor prices the %d payroll days after the time-to-fill; kept (judgment)' % pay_days),
    }
    check('checks: GF Data lift +%.1f%% against the console\'s QoE value effect %+.1f%% / %+.1f%% / %+.1f%% (SDE $150k / $700k / $2.5M)' % (
        100 * lift, 100 * qoe_eff['sde_150k']['dV_median'], 100 * qoe_eff['sde_700k']['dV_median'], 100 * qoe_eff['sde_2500k']['dV_median']), True,
          'console values at those sizes $%.2fM / $%.2fM / $%.2fM, below GF Data\'s population (TEV about $10M+); judgment kept' % (
              qoe_eff['sde_150k']['value_median'] / 1e6, qoe_eff['sde_700k']['value_median'] / 1e6, qoe_eff['sde_2500k']['value_median'] / 1e6), test=False)
    check('checks: outreach $%s for %d days against Firmex (modal monthly fee %s: $%s for %.1f months; median fixed fee %s)' % (
        f'{js_checks["outreach_cost"]["console_cost"]:,}', days_out, modal[0], f'{out_modal:,.0f}', out_months, fixed_med),
          out_months * modal[1] <= js_checks['outreach_cost']['console_cost'] <= 50000, 'inside the published fee range')
    check('checks: SOP floor $%s inside the published $9k-$20k operations-manual range' % f'{cur["sops"]["floor"]:,}',
          9000 <= cur['sops']['floor'] <= 20000, '%d days against 1-3 months for complex SOP projects' % cur['sops']['days'])
    check('checks: GM days %d >= SHRM executive time-to-fill %d' % (cur['gm']['days'], SHRM['exec_ttf_2025']), cur['gm']['days'] >= SHRM['exec_ttf_2025'],
          '%d days left for notice and transition (no source)' % (cur['gm']['days'] - SHRM['exec_ttf_2025']))
    check('checks: growth days %d >= time-to-fill + ramp %d' % (days_g, js_checks['growth_days']['days_to_full_productivity']),
          days_g >= js_checks['growth_days']['days_to_full_productivity'], 'SHRM non-executive 44 days + Bridge Group 5.3 months')

    # ---------------------------------------------------------------- costs now and shipped (node: peer-median businesses)
    cst = pd.DataFrame(PR['costs'])
    cost_rows = []
    for _, r_ in cst.iterrows():
        cost_rows.append(dict(ind=r_.ind, sde=r_.ern, revenue=round(r_.rev), qoe_now=round(r_.cost['qoe']), qoe_shipped=round(max(F_ship, s_ship * r_.rev)),
                              gm_wage=round(r_.wage), gm_cost_now=round(r_.cost['gm']), gm_cost_shipped=round(hire + L_ship * r_.wage),
                              gm_cost_alt_payroll=round(hire + L_ship * r_.wage * gm_payroll_alt / 365),
                              gm_cost_round2_proposal=round(hire + L_ship * r_.wage * gm_days / 365),
                              gm_earnings_charge_now=round(r_.wage), gm_earnings_charge_shipped=round(L_ship * r_.wage),
                              growth_now=round(r_.cost['growth']), growth_shipped=round(max(rnd(gf[r_.ind]['cost'], 100), cur['growth']['share'] * r_.rev)),
                              growth_round2=round(max(rnd(gf[r_.ind]['round2']['cost'], 100), cur['growth']['share'] * r_.rev))))
    CR = pd.DataFrame(cost_rows)
    cost_summary = {}
    for e in cfg['sde_cost']:
        d = CR[CR.sde == e]
        cost_summary['sde_%dk' % (e / 1e3)] = {c: float(d[c].median()) for c in (
            'revenue', 'qoe_now', 'qoe_shipped', 'gm_wage', 'gm_cost_now', 'gm_cost_shipped', 'gm_cost_alt_payroll', 'gm_cost_round2_proposal',
            'gm_earnings_charge_now', 'gm_earnings_charge_shipped', 'growth_now', 'growth_shipped', 'growth_round2')}
    js_checks['gm_cost'] = dict(
        shipped='hire_cost + loading*gmSalary(s): one year of loaded salary plus the hire (the console\'s structure)',
        alternative='hire_cost + loading*gmSalary(s)*%d/365: loaded salary for the pre-sale payroll days only (INTERV gm days %d less SHRM\'s '
                    'executive time-to-fill %d)' % (gm_payroll_alt, gm_days, SHRM['exec_ttf_2025']),
        payroll_days=gm_payroll_alt,
        at_peer_median={k: dict(gm_wage=rnd(v['gm_wage'], 10), cost=rnd(v['gm_cost_shipped'], 10), cost_alternative=rnd(v['gm_cost_alt_payroll'], 10),
                                earnings_charge=rnd(v['gm_earnings_charge_shipped'], 10), cost_now=rnd(v['gm_cost_now'], 10))
                        for k, v in cost_summary.items()},
        note='the research round proposed the loaded salary for the %d programme days (cost %d/365 of a year); the review: the GM is on payroll at '
             'most %d of them; the analyst kept the console\'s one-year cost; the earnings charge after the sale is the same either way; judgment' % (
                 gm_days, gm_days, gm_payroll_alt))
    check('checks: GM cost at peer-median businesses (median of 16): $%s one year + hire, against $%s for %d payroll days (the alternative) and $%s now' % (
        f'{cost_summary["sde_700k"]["gm_cost_shipped"]:,.0f}', f'{cost_summary["sde_700k"]["gm_cost_alt_payroll"]:,.0f}', gm_payroll_alt,
        f'{cost_summary["sde_700k"]["gm_cost_now"]:,.0f}'), True,
          'at $700k SDE; at $150k: $%s, $%s, $%s; the earnings charge is $%s at $700k (now $%s)' % (
              f'{cost_summary["sde_150k"]["gm_cost_shipped"]:,.0f}', f'{cost_summary["sde_150k"]["gm_cost_alt_payroll"]:,.0f}',
              f'{cost_summary["sde_150k"]["gm_cost_now"]:,.0f}', f'{cost_summary["sde_700k"]["gm_earnings_charge_shipped"]:,.0f}',
              f'{cost_summary["sde_700k"]["gm_earnings_charge_now"]:,.0f}'), test=False)
    # console_checks.csv: QoE effect, GM effect by loading, costs
    rows_cc = []
    for _, r_ in qoe_df.iterrows():
        rows_cc.append(dict(table='qoe_value_effect', ind=r_.ind, sde=r_.ern, L='', revenue=round(r_.rev), value=round(r_.V), dV=round(r_.dV, 5)))
    for _, r_ in gm.iterrows():
        rows_cc.append(dict(table='gm_value_effect', ind=r_.ind, sde=r_.ern, L=r_.L, revenue=round(r_.rev), value='', dV=round(r_.dV, 5)))
    pd.DataFrame(rows_cc).to_csv(os.path.join(OUT, 'console_checks.csv'), index=False)
    CR.to_csv(os.path.join(OUT, 'console_costs.csv'), index=False)

    # ---------------------------------------------------------------- 5. the table to embed
    ecec_cols = ['total_compensation', 'wages_and_salaries', 'paid_leave', 'supplemental_pay']
    ecec_row = lambda k: [cells[k]['cost'][c] for c in ('tc', 'w', 'paid_leave', 'supp')]
    qoe_note = ('no tier\'s revenue midpoint is below $%.2fM, so the floor\'s level for the smallest businesses is the max form\'s extrapolation, not a '
                'measurement; a pooled power curve, which predicts held-out sources about as well, gives $%.1fk at $0.5M and $%.1fk at $1M of revenue' % (
                    min_rev / 1e6, pow_pred(bp_pool, 5e5) / 1e3, pow_pred(bp_pool, 1e6) / 1e3))
    bridge = ('one added sales rep for the programme\'s %d days, on payroll after SHRM\'s median non-executive time-to-fill (%d days), so for %d days; '
              'paid the OEWS May 2025 median wage of the industry\'s sales representatives (41-3091, 41-4011, 41-4012 pooled by employment) carried to '
              'June 2026 by the ECI; loaded by ECEC\'s employer-cost ratio for sales and related occupations, TC/(W+PL); plus SHRM\'s median non-executive '
              'cost-per-hire. Judgment: one hire, the median wage, the payroll days and the proxy cells; each alternative\'s half-gap is in the SE' % (
                  days_g, ttf_ne, pay_days))
    js_table = {
        'qoe': dict(floor=F_ship, share=s_ship, floor_se=F_se_ship, share_se=s_se_ship,
                    floor_unrounded=round(F, 1), share_unrounded=round(s, 6), kink_revenue=rnd(F_ship / s_ship, 1000),
                    floor_p5_p95=[rnd(float(np.percentile(bm[:, 0], 5)), 10), rnd(float(np.percentile(bm[:, 0], 95)), 10)],
                    share_p5_p95=[rnd(float(np.percentile(bm[:, 1], 5)), 1e-5), rnd(float(np.percentile(bm[:, 1], 95)), 1e-5)],
                    loso=dict(floor=[lo_f, hi_f], share=[round(lo_s, 5), round(hi_s, 5)]),
                    sensitivity={SENS_KEY[k]: dict(floor=S[k]['floor'], share=S[k]['share_5'], tiers=S[k]['tiers'], label=k) for k in S if k in SENS_KEY},
                    n_tiers=int(len(T)), n_sources=int(T.src.nunique()), revenue_window=[int(QOE_WINDOW[0]), int(QOE_WINDOW[1])],
                    min_tier_revenue=rnd(min_rev, 10000), extrapolation_note=qoe_note,
                    form='max(floor, share*revenue)', days=cur['qoe']['days'], current=dict(floor=cur['qoe']['floor'], share=cur['qoe']['share']),
                    basis='published QoE fee schedules (QoE providers, CPA firms, M&A advisors, publishers): list prices, sell/buy/generic pooled (each tier '
                          'coded as its page presents the price); tiers on EV or EBITDA converted to revenue with the console\'s own maps',
                    tier='aggregate'),
        'gm': dict(loading=L_ship, loading_se=L_se_ship, loading_range=L_range, loading_unrounded=round(L, 4),
                   loading_alternatives=dict(management_business_financial=round(L_mbf, 4)),
                   formula='TC/(W+PL) of management, professional and related occupations x [TC/(W+PL) of establishments with 1-49 workers / '
                           'TC/(W+PL) of all private industry]',
                   range_basis='low: management without supplemental pay, (TC - supplemental pay)/(W+PL), same size scaling; high: management at all sizes',
                   ecec=dict(columns=ecec_cols, management_professional=ecec_row('mgmt_prof'), management_business_financial=ecec_row('mgmt_bus_fin'),
                             establishments_1_49=ecec_row('est_1_49'), all_private=ecec_row('private'), period='June 2026', unit='$ per hour worked',
                             note='ECEC wages and salaries leave out pay for leave, which ECEC counts as the paid-leave benefit; gmSalary and OEWS wages are '
                                  'annual salaries that include it, so the loading divides total compensation by wages plus paid leave'),
                   hire_cost=hire, hire_cost_se=HIRE_SE_JUDGMENT,
                   hire_cost_note='SHRM 2025 median executive cost-per-hire (2,371 SHRM members; $8,750 in 2022); no SE published, the SE is the 2022-25 change (judgment)',
                   use=dict(cost='hire_cost + loading*gmSalary(s)', earnings_charge='-loading*gmSalary(s)',
                            note='the console\'s structure: one year\'s salary as the cost, now loaded, plus the one-time hire; the pre-sale payroll '
                                 'alternative is in checks.gm_cost'),
                   days=gm_days, current=dict(loading=1, hire_cost=0, cost='gmSalary(s)', earnings_charge='-gmSalary(s)'),
                   tier=dict(loading='fitted', hire_cost='aggregate')),
        'growth_floor': dict(by_industry={i: rnd(gf[i]['cost'], 100) for i in INDS}, se={i: rnd(gf[i]['se'], 10) for i in INDS},
                             se_components={k: {i: rnd(gf[i]['comp'][k], 10) for i in INDS} for k in SE_KEYS},
                             tier='aggregate', bridge=bridge, formula='median x eci x loading x payroll_days/365 + hire_cost',
                             wage='OEWS May 2025 median annual wage of sales representatives (SOC 41-3091, 41-4011, 41-4012) pooled by employment, '
                                  'national industry cell',
                             eci=G_ECI, loading=round(L_sales, 4), ecec_sales=ecec_row('sales'), ecec_columns=ecec_cols,
                             days=days_g, time_to_fill_days=ttf_ne, payroll_days=pay_days, hire_cost=hire_ne,
                             naics={i: SALES_CELL[i] for i in INDS}, proxy=sorted(SALES_NOTE),
                             proxy_alternative={i: SALES_ALT[i][1] for i in sorted(SALES_ALT)}, proxy_flag=flags,
                             se_basis='root sum of squares of: OEWS sampling of the median (MEAN_PRSE x sqrt(pi/2), weighted by each occupation\'s share '
                                      'of the density at the median); half the gap to the mean-wage floor; half the gap to %d payroll days; for proxy '
                                      'cells, half the gap to the alternative cell (proxy_alternative); the common error of the loading and the ECI '
                                      '(relative %.4f)' % (days_g, rel_common),
                             share=cur['growth']['share'], share_tier='judgment', current=cur['growth']['floor']),
        'checks': js_checks,
        'tiers': {'qoe.floor': 'aggregate', 'qoe.share': 'aggregate', 'gm.loading': 'fitted', 'gm.hire_cost': 'aggregate',
                  'growth_floor.by_industry': 'aggregate', 'growth.share': 'judgment', 'checks': 'judgment'},
        'asof': '2026-10',
        'source': 'fit/intervention_costs.py: 33 published QoE fee tiers from 15 sources (fetched Oct 2026); BLS ECEC June 2026 tables 4 and 6 and their RSEs; '
                  'BLS OEWS May 2025 national industry-specific (sales representatives: medians, percentiles and means); SHRM 2025 Recruiting Executives '
                  'Benchmarking; checks: GF Data via ACG Middle Market Growth (fall 2025), SBA SOP 50 10 8.1 summaries (EisnerAmper, HoganTaylor, '
                  'CohnReznick, CLA), Firmex US M&A Fee Guide 2023-24, ContractsCounsel, Franchise Law Solutions, Wethos, Strety, Bridge Group SaaS AE '
                  'Metrics v8.3',
        'method': 'qoe: weighted least squares of log fee on log max(floor, share x revenue) at tier midpoints, each source weight 1, EV/EBITDA tiers mapped to '
                  'revenue with the console\'s value and SDE-EBITDA maps; source-cluster bootstrap SEs (B = 2000). gm: annual-salary loading TC/(W+PL) '
                  '(ECEC costs are per hour worked, so its wages leave out leave pay, which annual salaries include) of management, professional and related '
                  'occupations x the 1-49-worker / all-private ratio of TC/(W+PL); sampling SE from the published RSEs; range: management without '
                  'supplemental pay (same size scaling) to management at all sizes; hire cost: SHRM median executive cost-per-hire; use: one year of loaded '
                  'salary plus the hire. growth: one sales hire = OEWS industry median sales-rep wage x ECI to 2026Q2 x ECEC sales loading TC/(W+PL) x '
                  '(%d - %d)/365 + SHRM non-executive cost-per-hire; SE: sampling, the mean-against-median and payroll-days bridge choices and the proxy '
                  'cell (each alternative\'s half-gap) and the common loading and ECI error, in quadrature.' % (days_g, ttf_ne),
    }
    js_line = 'MODELS.fitted.interventions=' + json.dumps(py(js_table), sort_keys=True, separators=(',', ':')) + ';'
    open(os.path.join(OUT, 'js_line.txt'), 'w').write(js_line + '\n')

    # ---------------------------------------------------------------- 6. the page code, run verbatim in node on the snapshot
    jc_path, jc_cfg = os.path.join(WORK, 'jscheck.js'), os.path.join(WORK, 'jscheck_cfg.json')
    open(jc_path, 'w').write(JSCHECK_JS)
    json.dump(dict(table=py(js_table), js_code=JS_CODE, sde=cfg['sde_cost']), open(jc_cfg, 'w'), sort_keys=True)
    r = subprocess.run(['node', jc_path, HARNESS, jc_cfg], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    open(os.path.join(WORK, 'jscheck_out.json'), 'w').write(r.stdout)
    JC = json.loads(r.stdout)
    wage_of = {(r_.ind, r_.ern): r_.wage for _, r_ in cst.iterrows()}
    dev, wdev = 0.0, 0.0
    for row in JC['rows']:
        exp = dict(qoe=max(F_ship, s_ship * row['rev']), gm=hire + L_ship * row['wage'], charge=-L_ship * row['wage'],
                   growth=max(js_table['growth_floor']['by_industry'][row['ind']], cur['growth']['share'] * row['rev']))
        dev = max(dev, max(abs(row[k] - v) / abs(v) for k, v in exp.items()))
        wdev = max(wdev, abs(row['wage'] / wage_of[(row['ind'], row['ern'])] - 1))
    unk = max(js_table['growth_floor']['by_industry']['prof'], cur['growth']['share'] * 1e6)
    jrow = [row_ for row_ in JC['rows'] if row_['ern'] == 7e5]
    check('js: the page code runs verbatim in node on the snapshot with the table attached; its QoE, GM and growth costs equal this script\'s at %d '
          'peer-median businesses' % len(JC['rows']), dev < 1e-12 and wdev < 1e-12 and abs(JC['unknown_growth'] - unk) < 1e-9,
          'largest relative difference %.1e (gmSalary %.1e); an unknown industry takes the prof floor ($%s); at $700k SDE (median of 16) GM cost $%s, '
          'charge $%s, growth cost $%s' % (dev, wdev, f'{JC["unknown_growth"]:,.0f}', f'{np.median([q["gm"] for q in jrow]):,.0f}',
                                         f'{-np.median([q["charge"] for q in jrow]):,.0f}', f'{np.median([q["growth"] for q in jrow]):,.0f}'))

    # ---------------------------------------------------------------- shipped values with SEs against the console
    shipped = [dict(param='qoe.floor', value=F_ship, se=F_se_ship, current=cur['qoe']['floor'], unrounded=round(F, 1), unit='USD', tier='aggregate',
                    se_research=rep.get('qoe', {}).get('reproduced', {}).get('floor_se')),
               dict(param='qoe.share', value=s_ship, se=s_se_ship, current=cur['qoe']['share'], unrounded=round(s, 6), unit='share of revenue', tier='aggregate',
                    se_research=rep.get('qoe', {}).get('reproduced', {}).get('share_se')),
               dict(param='gm.loading', value=L_ship, se=L_se_ship, range=L_range, current=1.0, unrounded=round(L, 4), round2=LOADING_ROUND2,
                    management_business_financial=round(L_mbf, 4), unit='employer cost per $ of annual salary (wages plus paid leave)',
                    tier='fitted', note='current: gmSalary is wages and salaries only; round 2 divided by wages without paid leave'),
               dict(param='gm.hire_cost', value=hire, se=HIRE_SE_JUDGMENT, current=0, unit='USD, once', tier='aggregate', note='SE: judgment (2022-25 change)')]
    for i in INDS:
        shipped.append(dict(param='growth_floor.' + i, value=rnd(gf[i]['cost'], 100), se=rnd(gf[i]['se'], 10), current=cur['growth']['floor'],
                            unrounded=round(gf[i]['cost'], 1), se_components={k: round(gf[i]['comp'][k]) for k in SE_KEYS},
                            round2=rnd(gf[i]['round2']['cost'], 100), unit='USD (one hire, %d payroll days)' % pay_days, tier='aggregate',
                            naics=SALES_CELL[i], proxy=SALES_NOTE.get(i, ''), proxy_alternative=SALES_ALT[i][1] if i in SALES_ALT else '',
                            weak_proxy=i in WEAK_PROXY))

    # ---------------------------------------------------------------- sources
    def src_entry(name, url, path, years, n, used):
        return dict(name=name, url=url, file=path, sha256=sha(path) if os.path.exists(path) else 'missing', years=years, n=n, used=used)
    seen = {}
    for t in TIERS:
        seen.setdefault(t[2], (t[0].split('_')[0], t[1]))
    for lf, (srcn, url) in seen.items():
        ntier = int((T.file == lf).sum())
        sources.append(src_entry('QoE price page: ' + srcn, url, os.path.join(DH, lf), 'fetched 2026-10', '%d fitted tier(s)' % ntier,
                                 'QoE fee tiers' if ntier else 'untiered range or weeks (not fitted)'))
    sources += [
        src_entry('BLS ECEC June 2026, table 4 (private industry by occupational group)', 'https://www.bls.gov/news.release/ecec.t04.htm', ECEC_T04, 'June 2026',
                  'about 28,300 occupational observations from about 6,600 private establishments', 'management, all private, sales loadings'),
        src_entry('BLS ECEC June 2026, table 6 (private industry by establishment size)', 'https://www.bls.gov/news.release/ecec.t06.htm', ECEC_T06, 'June 2026',
                  'as table 4', '1-49-worker establishment ratio'),
        src_entry('BLS ECEC relative standard errors (June 2026)', 'https://www.bls.gov/web/ecec/ecec-rse.htm', ECEC_RSE, 'June 2026', 'tables 1-7', 'loading sampling SEs'),
        src_entry('BLS ECEC technical note', 'https://www.bls.gov/news.release/ecec.tn.htm', ECEC_TN, 'June 2026', 'sample size', 'sample size'),
        src_entry('SHRM 2025 Recruiting Executives Benchmarking (data brief)', 'https://www.shrm.org/content/dam/en/shrm/research/2025-recruiting-benchmarking-report.pdf',
                  SHRM_PDF, '2025 (survey Jan 9 - Mar 3, 2025)', '2,371 respondents (per-metric n not published)', 'executive and non-executive cost-per-hire; time-to-fill'),
    ]
    for fn in OEWS_FILES:
        sources.append(src_entry('BLS OEWS May 2025 national industry-specific: ' + fn, 'https://www.bls.gov/oes/special-requests/oesm25in4.zip',
                                 os.path.join(OEWS_DIR, fn), 'May 2025 (3-year panel)',
                                 '%d sales-rep rows read%s' % (int((D.FILE == fn).sum()), ' (+ %d veterinary-services context rows)' % int((VR.FILE == fn).sum()) if (VR.FILE == fn).any() else ''),
                                 'sales-rep percentiles (median), means and PRSEs'))
    if os.path.exists(OEWS_ZIP):
        sources.append(src_entry('BLS OEWS May 2025 national industry-specific (the official zip the xlsx files come from)',
                                 'https://www.bls.gov/oes/special-requests/oesm25in4.zip', OEWS_ZIP, 'May 2025', '-', 'provenance of the xlsx files'))
    sources += [
        src_entry('Firmex M&A Fee Guide 2023-24, US edition', 'https://www.firmex.com/wp-content/uploads/2024/07/Firmex-MAFeeGuide-US.pdf', FIRMEX_PDF,
                  'survey December 2023', '189 US respondents', 'outreach check'),
        src_entry('Bridge Group SaaS AE Metrics v8.3', 'bridgegroupinc.com (download URL not recorded)', BRIDGE_PDF, '2022', '253 B2B SaaS companies', 'growth days check (ramp)'),
        src_entry('GF Data via ACG Middle Market Growth, fall 2025', GF_PAGE[1], GF_PAGE[0], 'deals closed since Q3 2024', '360 deals', 'QoE effect check'),
        src_entry('investmentbank.com on GF Data by deal size', IB_PAGE[1], IB_PAGE[0], '2026', '-', 'QoE effect check (size)'),
    ]
    for k, (pth, url) in SBA_PAGES.items():
        sources.append(src_entry('SBA SOP 50 10 8.1 QoE rule: ' + k, url, pth, '2026', '-', 'SBA rule check'))
    for k, (pth, url) in CHECK_PAGES.items():
        sources.append(src_entry(k, url, pth, '2026 page', '326 MSA projects' if k == 'ContractsCounsel' else '-', 'contracts check' if k == 'ContractsCounsel' else 'SOP check'))
    sources.append(src_entry('Snapshot index.html (HEAD 56ba230)', 'local', SNAP, '-', '-', 'current INTERV values, gm_wage ECI factor; the harness model'))
    sources.append(src_entry('Model harness (loads the snapshot\'s model section)', 'local', HARNESS, '-', '-', 'node probe and the page-code check'))
    missing = [s_['file'] for s_ in sources if s_['sha256'] == 'missing']
    check('every input file present', not missing, 'missing: %s' % missing if missing else '%d files hashed' % len(sources))

    # ---------------------------------------------------------------- not shipped (evidence that stays a check)
    n_sell_small = int(((T.side == 'sell') & (T.rev < 3e6)).sum())
    not_shipped = dict(
        qoe_power_form=dict(note='power curve log fee = a + b log(rev/$5M) + side dummies; the sell dummy is confounded with which sources publish '
                                 'sell-side prices (%d sell-side tier(s) below $3M of revenue)' % n_sell_small,
                            elasticity=round(float(bp_pow[1]), 3), elasticity_se=round(float(bp[:, 1].std(ddof=1)), 3),
                            sell_vs_generic=round(float(np.exp(bp_pow[2])), 3), buy_vs_generic=round(float(np.exp(bp_pow[3])), 3),
                            pooled_elasticity=round(float(bp_pool[1]), 3),
                            predictions=[{k: (round(v) if isinstance(v, float) else [round(z) for z in v] if isinstance(v, list) else v) for k, v in p.items()} for p in pred],
                            leave_one_source_out_rmsle={k: v['rmsle'] for k, v in cvf.items()}, bootstrap_draws=len(bp), bootstrap_skipped=skipped,
                            research_coding=dict(bootstrap_draws=len(bp_r), sell_vs_generic=round(float(np.exp(fit_pow(T_r.rev.values, np.log(T_r.fee.values),
                                                 src_weights(T_r), T_r.side.values, True)[2])), 3), leave_one_source_out_rmsle_sides=cv_forms(T_r)['power_sides']['rmsle'])),
        qoe_side_coding=dict(recoded=[dict(label=a, shipped=b, research=c) for a, b, c in recoded],
                             why='the page gives both livmo tiers as generic pricing in an FAQ answer, followed by "The buyer almost always commissions their own QoE"',
                             research_coding_sensitivity=[r for r in sens_r if r['spec'] in side_specs]),
        qoe_sensitivity=sens, qoe_loso=loso, qoe_days=weeks,
        qoe_bootstrap_research=rep.get('qoe'),
        gm_loading_alternatives={k: round(v, 4) for k, v in L_alt.items()},
        gm_loading_round2=dict(tc_over_w=round(L_tcw, 4), se=round(L_tcw_se, 4), cells_tc_over_w={k: round(ratio_tcw[k], 4) for k in ('mgmt_prof', 'est_1_49', 'private', 'sales')},
                               note='round 2 divided total compensation by wages per hour worked, which leave out leave pay, and applied it to annual salaries that '
                                    'include it, so paid leave was counted twice'),
        gm_loading_note='GM (SOC 11-1021) belongs to management, business and financial occupations (%.2f), the group whose ECI carries gmSalary; the '
                        'decision uses the broader management, professional and related group (%.2f)' % (L_mbf, L),
        gm_value_effect_by_loading=gm_tab,
        gm_retained_search='retained executive search 25-35% of first-year cash compensation (secondary pages seen by the research round, not saved; not verified)',
        growth_alternatives=dict(mean_wage={i: round(gf[i]['alt']['mean_wage']) for i in INDS},
                                 payroll_270_days={i: round(gf[i]['alt']['payroll_270_days']) for i in INDS},
                                 no_supplemental_pay={i: round(gf[i]['alt']['no_supplemental']) for i in INDS},
                                 loading_scaled_to_small_establishments={i: round(gf[i]['alt']['loading_small_establishments']) for i in INDS},
                                 suppressed_employment_dropped={i: round(gf[i]['alt']['suppressed_dropped']) for i in INDS},
                                 wmean_of_occupation_medians={i: round(gf[i]['alt']['wmean_of_medians']) for i in INDS},
                                 round2_basis=dict(note='mean wage, TC/W loading %.4f, 270 days (round 2 and the research round)' % ratio_tcw['sales'],
                                                   cost={i: round(gf[i]['round2']['cost']) for i in INDS}, se={i: round(gf[i]['round2']['cost_se']) for i in INDS}),
                                 proxy_cells={i: dict(cells=gf[i]['alt_cell']['cells'], why=gf[i]['alt_cell']['why'], title=gf[i]['alt_cell']['title'],
                                                      median=round(gf[i]['alt_cell']['median']), mean=round(gf[i]['alt_cell']['mean']),
                                                      employment=gf[i]['alt_cell']['employment'], rel_se_median=round(gf[i]['alt_cell']['rel_se_median'], 4),
                                                      cost=round(gf[i]['alt_cell']['cost']), notes=gf[i]['alt_cell']['notes']) for i in sorted(SALES_ALT)},
                                 vet_541940=dict({k: dict(occupation=str(VR.loc[k, 'OCC_TITLE']), employment=vt[k]['emp'], median=vt[k]['median'])
                                                  for k in VET_OCCS}, note='veterinary services: no sales-rep rows; the sales and related major group and marketing specialists'),
                                 loadings=dict(shipped=round(L_sales, 4), no_supplemental=round(L_sales_ns, 4), small_establishments=round(L_sales_small, 4),
                                               round2_tc_over_w=round(ratio_tcw['sales'], 4))),
        growth_share=dict(console=cur['growth']['share'], bridge_group=BRIDGE,
                          note='rep productivity in small businesses is unpublished; the SaaS quota/OTE ratio (%.1f) is the only measured analog; the .022 share stays judgment' % (
                              BRIDGE['quota_acv'] / BRIDGE['median_ote'])),
        costs_now_and_shipped=cost_summary,
    )

    # ---------------------------------------------------------------- RESULT.json
    res = dict(name='intervention_costs', js_key='interventions', tier='mixed', js_table=py(js_table), js_line=js_line, js_code=JS_CODE, shipped=py(shipped),
               checks=checks, tests=tests, all_tests_pass=all(tests.values()), not_shipped=py(not_shipped), sources=sources,
               parameters=dict(B_BOOT=B_BOOT, SEED=SEED, QOE_WINDOW=list(QOE_WINDOW), BUY_PREMIUM=BUY_PREMIUM,
                               SUPPRESSED_EMP_WEIGHT=SUPPRESSED_EMP_WEIGHT, HIRE_SE_JUDGMENT=HIRE_SE_JUDGMENT, ECI_REL_SE=ECI_REL_SE,
                               MEDIAN_SE_FACTOR=round(MEDIAN_SE_FACTOR, 6), LOADING_ROUND2=LOADING_ROUND2, LOADING_RESEARCH=list(LOADING_RESEARCH),
                               RESEARCH_SIDE={'%s %g-%g' % k: v for k, v in RESEARCH_SIDE.items()}, growth_payroll_days=pay_days, gm_payroll_days_alternative=gm_payroll_alt,
                               rounding='qoe floor to $100, share to 0.0001, SEs to $10 and 0.00001; loading to 0.01 (SE 0.001); growth floors to $100, SEs and '
                                        'SE components to $10'),
               ecec=py({k: dict(table=c['table'], series=c['name'], cost=c['cost'], rse=c['rse'], tc_over_w_plus_pl=round(ratio[k], 5),
                                tc_over_w_plus_pl_no_supp=round(ratio_ns[k], 5), rel_se=round(rel[k], 5), tc_over_w_round2=round(ratio_tcw[k], 5))
                        for k, c in cells.items()}),
               growth=py({i: dict(naics=SALES_CELL[i], title=gf[i]['title'], occs=gf[i]['occs'], employment=gf[i]['employment'],
                                  median_wage=round(gf[i]['median'], 1), rel_se_median=round(gf[i]['rel_se_median'], 5), mean_wage=round(gf[i]['mean'], 1),
                                  se_mean=round(gf[i]['se_mean'], 1), by_occ=gf[i]['by_occ'], cost=round(gf[i]['cost'], 1), se=round(gf[i]['se'], 1),
                                  se_components={k: round(gf[i]['comp'][k], 1) for k in SE_KEYS}, notes=gf[i]['notes'], proxy=SALES_NOTE.get(i, ''))
                          for i in INDS}),
               current_interv=cur, replication=py(rep))
    open(os.path.join(OUT, 'RESULT.json'), 'w').write(json.dumps(py(res), indent=1, sort_keys=True) + '\n')

    # ---------------------------------------------------------------- console summary
    print('QoE: F $%.0f (SE %.0f; research-style %s), s %.5f%% (SE %.5f%%), kink $%.2fM; shipped max(%d, %.4f x rev); %d tiers / %d sources' % (
        F, F_se, rep.get('qoe', {}).get('reproduced', {}).get('floor_se'), 100 * s, 100 * s_se, kink / 1e6, F_ship, s_ship, len(T), T.src.nunique()))
    print('    LOSO floor %s-%s, share %.4f-%.4f%%; LOSO RMSLE %s' % (lo_f, hi_f, 100 * lo_s, 100 * hi_s, {k: v['rmsle'] for k, v in cvf.items()}))
    print('GM: loading %.4f (SE %.4f) -> %.2f, range %s; hire $%d; alternatives %s' % (L, L_se, L_ship, L_range, hire, {k: round(v, 3) for k, v in L_alt.items()}))
    print('Growth floors (%d payroll days, median wage, loading %.4f): ' % (pay_days, L_sales) +
          ', '.join('%s %s (%s)' % (i, f'{rnd(gf[i]["cost"], 100):,}', f'{rnd(gf[i]["se"], 10):,}') for i in INDS))
    for c in checks:
        print('  [%s] %s -- %s' % (c['outcome'], c['name'], c['detail']))
    print('wrote', os.path.join(OUT, 'RESULT.json'))
    if not all(tests.values()):
        print('FAILED:', [k for k, v in tests.items() if not v])
        sys.exit(1)


if __name__ == '__main__':
    main()
