#!/usr/bin/env python3
"""Peer medians of recurring revenue (IND.rec) and customer retention (IND.ret), revision 3 (October 2026): two of the 32
move to data (land.ret, fit.ret); fit.rec and saas.rec stay judgment with their evidence recorded; the other 28 stay
judgment with the research's flags (nine flags in revision 3).

Run:  python3 -I /tmp/claude-0/fit6/fitscripts/peer_recurring_retention.py          (about 2 min, most of it reading the
      103 DealLedger snapshot files)
Out:  /tmp/claude-0/fit6/out/peer_recurring_retention/RESULT.json (key js_table = MODELS.fitted.peer_rec_ret; js_line =
      the exact line to embed; shipped, not_shipped, checks, sources, open_issues), js_line.txt, estimates.csv,
      census_lines.csv, fit_rec_median_grid.csv, ef_subscription.csv, dl_rec_statements.csv, dl_mention_rates.csv,
      land_ret_2026_hist.csv, spread_checks.csv
      Round 1 (four moves) is kept beside it as peer_recurring_retention.v1.py and out/peer_recurring_retention.v1/,
      revision 2 as peer_recurring_retention.v2.py and out/peer_recurring_retention.v2/.

Revision 3 (the round-2 review's minor items, all applied; no shipped value moves except fit.ret's SE)
  - fit.ret: the source says what HFA's 66.4% is, an average across 175 companies (114 US), mostly multi-club operators
    (more than 17,000 facilities, about 97 per company). The SE's upper segment is IHRSA's own figure for independent
    clubs, .732, so SE = (.732 - .584)/4 = .037 (revision 2: .044 from Health Club Management's .758; both are cited).
  - land.ret: the note no longer calls the mean-median gap a measured selection effect. It reads ".88 = the survey means;
    a judgment shade below the survey medians (.93 / .92) for self-selected US and Canadian respondents; the size of the
    shade is not measured". The .04-.05 gap is the left skew of the answers (the 2026 histogram reproduces both).
  - flags: a land.rec flag (Census 2022 NAICS 561730: the landscaping care and maintenance lines are .86 of revenue, an
    upper bound because contract status is not recorded, against .48); wash.rec names MarQ's market estimate (about 35%
    of US car-wash revenue from memberships across formats; not opened); msp.rec's Census shares are marked
    revenue-weighted (shares of industry revenue, not establishment medians).
  - spread checks: the two-point Census mixture SDs are labelled lower bounds and kept apart from the ordinary SDs;
    fitness's lower bound (.41) exceeds the kept .28, so ".28 sits inside the measured spreads" is no longer claimed.
  - open issues: the critique's follow-ups 3 (establishment-level medians for 561730, 541513, 541940) and 6 (ChartMogul,
    Kaseya 2025, MarQ) are listed as open.

Why
  The console z-scores the user's recurring share and retention against per-industry peer medians,
  z.rec = (rec - IND.rec)/.28 and z.ret = (ret - IND.ret)/.13 (index.html model(), z block). The z-scores feed the
  quality composite (and through it value, price, closing odds and both scores), the category sub-scores and the buyer
  fit functions. All 32 medians are hand-set. Round 1 moved four of them; the completeness critic
  (research/results_all.json, "critique") found that two of the four were not peer medians on the console's population:
  fit.rec's .66 is a revenue-weighted Census aggregate in which 35% of establishments sit at zero, and saas.rec's .90
  pooled loosely matched definitions (an MRR ratio that exceeds 1 for growing listings, listings that are not software).
  It also asked that land.ret use the survey mean, because respondents are self-selected. The analyst's decisions, which
  this revision implements:
    land.ret .74 -> .88, SE .04. The 2025 and 2026 Lawn & Landscape survey means (.88, .89; n-weighted .884) on the
             console's exact question. The medians (.93; .92 from the 2026 histogram) sit about one SE higher; shipping
             the mean is a judgment shade below them for self-selected US and Canadian trade-magazine respondents (the
             size of the shade is not measured: the gap is the left skew of the answers), and the SE (.04, against a
             sampling SE of the mean of about .008) is likewise judgment.
    fit.ret  .62 -> .66, SE .037. HFA 2025 member retention averaged 66.4% across 175 companies (114 US), mostly
             multi-club operators; SE = IHRSA 2018 segment range / 4, fitness-only clubs .584 to independent clubs .732
             (IHRSA's page; Health Club Management reports .758 for the same segment, which would give .044).
    fit.rec  stays .70 (judgment). Check recorded: the establishment-level median implied by the Census line (22,604 of
             34,828 taxable establishments report membership revenue; reporters get 86% of revenue from it) under a
             stated grid of distributions among reporters.
    saas.rec stays .85 (judgment). Check recorded: the cleaned pool (Empire Flippers SaaS-primary listings plus the 4
             DealLedger statements that are software businesses) is .89 (SE .056), 0.75 SE from .85: within noise.
  The flags for eight of the other 28 medians are kept and a ninth (land.rec) is added. The z-scales .28 and .13 are
  kept (judgment): retention's measured spreads bracket .13; for the recurring share the ordinary SDs (.11-.23) sit
  below .28 and the two-point lower bounds run .08-.41, fitness's above it.
  js_table.rec is {} (nothing in rec ships); js_table.ret holds land and fit; js_table.not_shipped holds the two checks.

What it does
  0. Reads the snapshot's index.html (read only) for the current IND.rec / IND.ret, the z-scales and the slider ranges.
  1. Census lines. Reads EC2200NAPCSINDPRD.dat from inside the downloaded zip (in memory; nothing is extracted or run):
     NAICS 713940, US (GEOTYPE 01), all operations (TYPOP 00), taxable establishments (TAXSTAT T), NAPCS 7001900003
     'Fitness and recreational sports center memberships' over the industry total (NAPCS 0000000000), both in $1,000
     (NAPCSDOL); checked against the published LINEALL_PCT (66.0). Kept beside it: the establishments reporting the line
     (ESTAB, ESTAB_PCT), the line's share among them (LINE_PCT), all and tax-exempt establishments. The same pass reads
     the Census lines the flags quote (NAICS 541513 managed services, 561320 temporary staffing, 811192 car washes, and
     561730 landscaping: residential, exterior commercial and interior commercial landscaping services, the care and
     maintenance lines, all establishments since the file has no taxable split for 561730) and the two-point spreads
     used in the z-scale check. All these shares are revenue-weighted (line revenue over industry revenue).
  2. saas.rec (not shipped). (a) Empire Flippers listings with MRR whose first monetization is SaaS, Subscription,
     Application, Agency or Service (n = 29, 22 sold and 7 for sale): MRR x 12 / trailing revenue, capped at 1; median and
     bootstrap SE; subsets (SaaS-primary n = 20, sold only, growth-neutral ratio). (b) DealLedger broker listings: the
     research round's text mining re-run from the raw snapshots (logic copied from work/C-rec-ret/dl_text_mine2.py and
     summaries.py); stated recurring shares of listings classified 'saas' (n = 11), each read by hand
     (SAAS_STATEMENT_REVIEW): 4 are software businesses. (c) The cleaned pool, inverse-variance: EF SaaS-primary median
     with its bootstrap SE, and the 4 software statements' median carrying the n = 11 median's SE (an n = 4 bootstrap SE
     is not credible); round 1's pool as decided then (EF 29 + DL 11) and the KBCM 2021 attach-implied share are kept as
     context. Recorded against the kept .85 as z = (pool - .85)/SE.
  3. fit.rec (not shipped). The Census line read at the establishment level: non-reporters (35.1%) at zero, reporters
     distributed with establishment-level mean mu_e and SD sd_e, so the median establishment is the reporters'
     ((.5 - p0)/(1 - p0)) = .230 quantile. Grid (stated before computing): mu_e in {.80, .83, .86, .90} (the 86% is
     revenue-weighted; the establishment mean is lower if big gyms rely on memberships more than studios do),
     sd_e in {.05, .08, .10, .12, .15, .20, .25}, two families (Beta; logit-normal matched to the same mean and SD).
     Central case: mu_e = .86 and sd_e = the SD of the 16 DealLedger fitness listings that state a recurring share.
     Variant: the 1,093 skating-rink establishments removed from the base (if none of them sells memberships).
  4. land.ret (shipped .88). The 2025 report (p. 6: mean .88, median .93, n = 433) and the 2026 report (p. 5: mean .89,
     n = 320; p. 7 answer histogram, a chart image read by eye: constants below, grouped median, mean and spread computed
     here). Ships the analyst's .88 = the n-weighted mean of the two survey means rounded; tests check it against both
     means and records how far the medians sit from it. The histogram reproduces both the mean and the median, so the
     mean-median gap is the answers' left skew; the shade below the medians is judgment, not a measured selection effect.
  5. fit.ret (shipped .66). HFA 2025 member retention averaged 66.4% (175 companies, 114 US, more than 17,000 facilities,
     2024 data), parsed from the HFA pages. SE = IHRSA 2018 segment range / 4: fitness-only clubs .584 (Health Club
     Management) to independent clubs .732 (IHRSA's own page); Health Club Management's .758 for independent clubs is
     cited beside it. IHRSA One Million Strong is a check.
  6. Flags (kept). The research's flags for eight of the 28 judgment values and the critique's land.rec flag, each quoted
     number confirmed in the downloaded page, PDF text or Census file ('quotes'); MarQ's car-wash estimate is named in
     wash.rec as not opened.
  7. Ordering check. DealLedger share of listings mentioning recurring, subscription, membership, maintenance-agreement,
     retainer or contract terms, per industry; Spearman against IND.rec (with Quiet Light's menu removed as a variant).
  8. Spread checks (record only): within-industry SDs of the recurring share and of retention against .28 and .13. The
     Census two-point mixtures (non-reporters at 0, reporters at their mean share) are LOWER BOUNDS on the SD: they
     ignore the spread among reporters. They are reported apart from the ordinary SDs.
  9. Materiality. Value of a business that enters today's hand-set medians ($708k SDE), before and after each shipped
     move, and for the two judgment values at their check values (not shipped), through /tmp/claude-0/fit6/harness.js
     (node); skipped with a note if node is missing.
 10. Output. Values rounded to 0.01 (half up), SEs to 0.001 (half up), Spearman to 0.01, mention rates to 0.001.
     Bootstrap: B = 4000, numpy default_rng([20261014, k]) with a fixed k per estimate. Checks and their outcomes are
     printed and stored (RESULT.json 'checks'; pass/fail tests also under 'tests').

Data and fetch (each download in its own directory under /tmp/claude-0/fit6/data/C-rec-ret/; read with python3 -I;
no new downloads in revisions 2 and 3; MarQ, ChartMogul and Kaseya 2025 are named, not downloaded)
  census_ec22_napcs/EC2200NAPCSINDPRD.zip
      curl -LO https://www2.census.gov/programs-surveys/economic-census/data/2022/sector00/EC2200NAPCSINDPRD.zip
  lawnlandscape_pdf/0325_benchmarking_report.pdf
      curl -LO https://giecdn.blob.core.windows.net/fileuploads/document/2025/03/10/0325_benchmarking_report.pdf
  lawnlandscape_pdf/0326_benchmarking_full.pdf
      curl -LO https://giecdn.blob.core.windows.net/fileuploads/document/2026/03/03/0326_benchmarking_full.pdf
      (linked from lawnandlandscape.com/page/benchmarking-your-business; the live page is an Incapsula stub, the Wayback
      copy links the PDFs)
  hfa2025/*.html      https://www.healthandfitness.org/2025-fitness-industry-benchmarking-report/ and
                      https://www.healthandfitness.org/hfa-releases-2025-fitness-industry-benchmarking-report/
  hfa_ihrsa/*.html    https://www.healthandfitness.org/ihrsa-2019-profiles-of-success/ ;
                      http://www.healthclubmanagement.co.uk/health-club-management-features/The-numbers-are-in/34259 ;
                      http://www.healthclubmanagement.co.uk/health-club-management-features/IHRSA-update-One-million-strong/30115
  kbcm_2021/2021-KBCM-SaaS-Survey.pdf
      curl -LO https://www.forentrepreneurs.com/wp-content/uploads/2021/10/2021-KBCM-SaaS-Survey.pdf
  flag sources: servicetitan/, rowriter/, shopify_blog/, datto_itpro/, rcpmag/, mcw_sec/, nbb_wp444/, nber_w31231/
      (URLs in SOURCES below)
  local: /tmp/claude-0/data5/empireflippers/clean/ef_listings.csv and ef_monthly_metrics.csv (Empire Flippers public
         marketplace API, retrieved 2026-10-10); /tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots/*/listings.csv
         (git clone --depth 1 https://github.com/jeffsosville/dealledger ; CC0 broker listings, 103 snapshot files)
  PDFs are read with poppler's pdftotext; numbers that are only in chart images are constants below with file, page and
  figure. When pdftotext is missing, the PDF quote checks are recorded as not run and the constants are used.
"""
import glob, hashlib, html.parser, io, json, os, re, shutil, subprocess, zipfile
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
from scipy import optimize, stats

NAME = 'peer_recurring_retention'
JS_KEY = 'peer_rec_ret'
ASOF = '2026-10-14'
OUT = '/tmp/claude-0/fit6/out/peer_recurring_retention'
DATA = '/tmp/claude-0/fit6/data/C-rec-ret'
CENSUS_ZIP = DATA + '/census_ec22_napcs/EC2200NAPCSINDPRD.zip'
CENSUS_DAT_COPY = DATA + '/census_ec22_napcs/EC2200NAPCSINDPRD.dat'     # the research round's extracted copy: hash-compared only
LL25_PDF = DATA + '/lawnlandscape_pdf/0325_benchmarking_report.pdf'
LL26_PDF = DATA + '/lawnlandscape_pdf/0326_benchmarking_full.pdf'
HFA_REPORT = DATA + '/hfa2025/www.healthandfitness.org_2025-fitness-industry-benchmarking-report_.html'
HFA_RELEASE = DATA + '/hfa2025/www.healthandfitness.org_hfa-releases-2025-fitness-industry-benchmarking-report_.html'
IHRSA_POS = DATA + '/hfa_ihrsa/www.healthandfitness.org_ihrsa-2019-profiles-of-success_.html'
HCM_NUMBERS = DATA + '/hfa_ihrsa/www.healthclubmanagement.co.uk_health-club-management-features_IHRSA-Update-The-numbers-are-in_34259.html'
HCM_OMS = DATA + '/hfa_ihrsa/www.healthclubmanagement.co.uk_health-club-management-features_One-million-strong_30115.html'
KBCM_PDF = DATA + '/kbcm_2021/2021-KBCM-SaaS-Survey.pdf'
SERVICETITAN = DATA + '/servicetitan/www.servicetitan.com_press_industry-trends-residential-services.html'
ROWRITER = DATA + '/rowriter/info.rowriter.com_blog_customer-attrition-auto-repair_.html'
SHOPIFY = DATA + '/shopify_blog/avg_ret_by_industry.html'
DATTO = DATA + '/datto_itpro/www.itpro.com_business-operations_managed-service-provider-msp_365496_recurring-services-key-to-msp-success-da.html'
RCPMAG = DATA + '/rcpmag/rcpmag.com_articles_2017_02_01_road-to-recurring-revenue.aspx.html'
MCW = DATA + '/mcw_sec/mcw_q2_2025_ex99_1.htm'
NBB_PDF = DATA + '/nbb_wp444/wp444en.pdf'
NBER_PDF = DATA + '/nber_w31231/w31231.pdf'
EF_LISTINGS = '/tmp/claude-0/data5/empireflippers/clean/ef_listings.csv'
EF_MONTHLY = '/tmp/claude-0/data5/empireflippers/clean/ef_monthly_metrics.csv'
DL_SNAPS = '/tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots'
INDEX = '/tmp/claude-0/fit6snap/index.html'                 # frozen snapshot, read only
HARNESS = '/tmp/claude-0/fit6/harness.js'                    # loads the snapshot's model into a sandbox (node)
RESEARCH_DL_HITS = '/tmp/claude-0/fit6/work/C-rec-ret/out/dl2_hits.csv'   # research output, compared in a test only

# ---------------------------------------------------------------- the analyst's decisions (documented constants)
# Revision 2: land.ret = the survey means (.88 in 2025, .89 in 2026; n-weighted .884), SE .04 because respondents are
# self-selected trade-magazine readers (round 1 shipped .90, SE .03, between the means and the medians).
LAND_RET, LAND_RET_SE = Decimal('0.88'), Decimal('0.040')
# Revision 3: IHRSA 2018 data, fitness-only clubs .584 (Health Club Management) to independent clubs .732 (IHRSA's own
# product page); Health Club Management gives independent clubs .758 (revision 2's upper end, SE .044), cited beside it.
FIT_RET_RANGE = (Decimal('0.584'), Decimal('0.732'))
FIT_RET_HCM_INDEPENDENT = Decimal('0.758')
RANGE_TO_SE = Decimal(4)                                    # se = range / 4: the segment range read as a 95% interval
# land.rec flag (revision 3): Census 2022 NAICS 561730, the care and maintenance lines (residential landscaping services,
# exterior and interior commercial landscaping services); landscape construction, snow removal and grass cutting alone
# (a sub-line of exterior commercial services) for context. The file has only all-establishment rows for 561730.
LAND_CARE_NAPCS = {'residential landscaping services': '7000645000', 'exterior commercial landscaping services': '7006750000',
                   'interior commercial landscaping services': '7006725000'}
LAND_OTHER_NAPCS = {'installation_construction': ['3000525000', '3000550000', '3000575000'], 'snow_removal': ['7008700000'],
                    'grass_cutting_alone': ['7006750006']}
# Named in the flags and open issues, not downloaded (the critique's missed sources and follow-up 6)
MARQ = dict(share=0.35, url='https://marqstats.com/reports/united-states-car-wash-services-market/', opened=False,
            what='MarQ market estimate: unlimited memberships about 35% of 2025 US car-wash revenue across formats (as quoted by the '
                 'completeness critique; not opened)')
FOLLOWUP6 = {'ChartMogul SaaS Retention Report (saas.ret size gradient)': 'https://chartmogul.com/reports/saas-retention-report/',
             'Kaseya 2025 Global MSP Benchmark Report (msp.rec, behind a download form)': 'https://www.kaseya.com/resource/2025-msp-benchmark-report',
             'MarQ car-wash membership share (wash.rec)': MARQ['url']}
KEPT = {'fit.rec': 0.70, 'saas.rec': 0.85}                  # stay judgment (revision 2); compared with the snapshot below
EF_MONETIZATIONS = ['SaaS', 'Subscription', 'Application', 'Agency', 'Service']   # the research's 'subscription listings'
B_BOOT, SEED = 4000, 20261014
SDE_REF = 708000                                            # the console's centre ($708k SDE) for the materiality check
# fit.rec check: the grid of distributions stated for the establishment-level membership share among the establishments
# that report the line (set before computing). mu_e = establishment-level mean among reporters (Census's 86% is
# revenue-weighted), sd_e = SD among reporters; families: Beta, and logit-normal matched to the same mean and SD.
FITREC_MU = [0.80, 0.83, 0.86, 0.90]
FITREC_SD = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25]
FITREC_MU_CENTRAL = 0.86                                    # the revenue-weighted 86% read as the establishment mean
RINK_NAPCS = ['7001925000', '7001950000']                   # roller and ice skating rink services (variant: out of the base)

# ---------------------------------------------------------------- read by eye or quoted (verified in the text where possible)
# L&L 2025 (0325_benchmarking_report.pdf, 9 pp): p. 6 (magazine S10-S11), "Of your location's customers 12 months ago,
# what percentage are still customers today?" 88% mean, 93% median. p. 3: "results are based on 433 landscapers and lawn
# care operators" (printed "closed for tabulation on Jan. 27, 2024"; its salary questions are "As of Nov. 1, 2024", so
# the data year is 2024 and the printed year is probably a misprint for 2025). All in the text layer (checked below).
LL25 = dict(mean=0.88, median=0.93, n=433, data_year=2024)
# L&L 2026 (0326_benchmarking_full.pdf, 16 pp): p. 5 (S5) "customer retention is up a tad from an average of 88% in 2024 to
# 89% in 2025"; "results are based on 320 total respondents from the United States and Canada" (fielded Jan. 20 - Feb. 9,
# 2026). Text layer, checked below. p. 7 (S7): bar chart "Of your service location's customers 12 months ago, what
# percentage are still customers today?" read by eye at 200 dpi (the chart is an image, not in the text layer):
# % of respondents per answer band; the labels sum to 99 (rounding).
LL26 = dict(mean=0.89, n=320, data_year=2025)
LL26_HIST = [('100%', 100, 100, 15), ('90-99%', 90, 99, 47), ('80-89%', 80, 89, 23), ('70-79%', 70, 79, 8),
             ('60-69%', 60, 69, 1), ('50-59%', 50, 59, 1), ('40-49%', 40, 49, 1), ('30-39%', 30, 39, 1),
             ('20-29%', 20, 29, 1), ('10-19%', 10, 19, 1), ('<10%', 0, 9, 0)]
# KBCM 2021 Private SaaS Company Survey (companies with $5M+ 2020 ending ARR), counts of companies per bin, transcribed
# from the PDF text layer (pp. 23, 26, 28; re-parsed and compared below). Open top bins are closed at 'top'.
KBCM_GDC = dict(page=23, n=173, top=0.55, median_printed=0.126,
                bins=[('<3%', 0, .03, 11), ('3-5%', .03, .05, 13), ('5-8%', .05, .08, 20), ('8-10%', .08, .10, 19),
                      ('10-13%', .10, .13, 26), ('13-15%', .13, .15, 17), ('15-20%', .15, .20, 24), ('20-25%', .20, .25, 7),
                      ('25-30%', .25, .30, 10), ('30-35%', .30, .35, 9), ('35-40%', .35, .40, 3), ('40-45%', .40, .45, 5),
                      ('45%+', .45, .55, 9)])
KBCM_LOGO = dict(page=26, n=166, top=0.50, median_printed=0.134,
                 bins=[('0%', 0, 0, 4), ('0-5%', 0, .05, 20), ('5-10%', .05, .10, 39), ('10-15%', .10, .15, 29),
                       ('15-20%', .15, .20, 32), ('20-25%', .20, .25, 15), ('25-30%', .25, .30, 13), ('30-35%', .30, .35, 6),
                       ('35-40%', .35, .40, 6), ('40%+', .40, .50, 2)])
KBCM_ATTACH = dict(page=28, n=152, bins=[('0% (no professional services)', 0, 0, 41), ('1-10%', .01, .10, 59),
                                          ('11-25%', .11, .25, 30), ('26-50%', .26, .50, 14), ('Over 50%', .51, 1.00, 8)])
# NBB Working Paper 444 (2023), PDF p. 18 (printed p. 13), Figure 8 "Transaction survival rate on a short-run horizon",
# read by eye: unweighted one-year link survival .55-.61 (about .60 from 2009 on), value-weighted .82-.92 (about .90 from
# 2010 on), 2002-2019.
NBB_FIG8 = dict(count=(0.55, 0.61), count_recent=0.60, value=(0.82, 0.92), value_recent=0.90, years='2002-2019')
# Quiet Light's site navigation, which the DealLedger scrape kept at the top of every Quiet Light description (lower case).
QLNAV = ('sell buy learn about success stories free valuation all amazon ecommerce saas content membership articles '
         'podcasts videos guides about us partners free valuation')
# The 11 DealLedger statements the research classified 'saas', reviewed by reading each listing's title and text
# (2026-10-14). The classifier matched 'software' or 'saas' anywhere in the text, including Quiet Light's menu.
SAAS_STATEMENT_REVIEW = {
    'https://gillagency.co/business/high-retention-tech-staffing-services-company-with-federal-market-access/': (False, 'tech staffing services'),
    'https://quietlight.com/listings/11589256/': (True, '25-year-old social services SaaS'),
    'https://quietlight.com/listings/18763734/': (False, 'Amazon FBA supplement brand'),
    'https://quietlight.com/listings/18828391/': (False, 'single-supplement e-commerce business'),
    'https://quietlight.com/listings/18828827/': (True, 'managed WordPress platform for agencies, $105K MRR'),
    'https://quietlight.com/listings/18828905/': (False, 'Shopify CRO agency'),
    'https://quietlight.com/listings/18829355/': (False, 'pediatric supplement e-commerce brand'),
    'https://theveldgroup.com/listing/saas-opportunity-serving-the-restaurant-industry-with-98-recurring-revenues/': (True, 'restaurant-industry SaaS'),
    'https://www.businessesforsale.ie/irish/specialist-it-recruitment-agency-1.aspx': (False, 'IT recruitment agency'),
    'https://www.websiteclosers.com/businesses/military-news-media-company-60-recurring-revenue-50m-annual-visitors-multiple-revenue-streams-680-000-news-subscribers-12-year-business/112197/': (False, 'news media company'),
    'https://www.websiteclosers.com/businesses/sba-pre-qualified-saas-business-digital-comment-card-customer-feedback-platform-17-year-company-95-recurring-revenue/118750/': (True, 'customer-feedback SaaS'),
}
# The research report's numbers, compared with this run's (diff_vs_research).
RESEARCH = {'fit.rec': 0.660, 'fit.rec_se': 0.006, 'ef_median': 0.894, 'ef_se': 0.060, 'ef_n': 29, 'dl_median': 0.90,
            'dl_se': 0.084, 'dl_n': 11, 'spearman_rec_mentions': 0.65, 'spearman_ret_mentions': -0.07, 'saas_mention_rate': 0.53,
            'fit_dl_median': 0.80, 'fit_dl_n': 16, 'ef_ret_median': 0.398, 'kbcm_gdc_sd': 0.125, 'kbcm_gdc_iqr_sd': 0.089}

SOURCES = [
    dict(key='census', name='Census 2022 Economic Census, product lines by industry (EC2200NAPCSINDPRD)', file=CENSUS_ZIP,
         url='https://www2.census.gov/programs-surveys/economic-census/data/2022/sector00/EC2200NAPCSINDPRD.zip', years='2022'),
    dict(key='ef', name='Empire Flippers public marketplace API, listings (cleaned extract)', file=EF_LISTINGS,
         url='https://api.empireflippers.com/api/v1/listings/list (retrieved 2026-10-10)', years='2022-2026 listings'),
    dict(key='ef_monthly', name='Empire Flippers monthly P&L metrics (cleaned extract)', file=EF_MONTHLY,
         url='https://api.empireflippers.com/api/v1/listings/list (retrieved 2026-10-10)', years='monthly, to 2026-09'),
    dict(key='dl', name='DealLedger CC0 broker listings, 103 snapshot files', file=DL_SNAPS + '/*/listings.csv',
         url='https://github.com/jeffsosville/dealledger', years='2026-02-18 to 2026-10-06'),
    dict(key='ll25', name='Lawn & Landscape, Benchmarking Your Business 2025 report (March 2025)', file=LL25_PDF,
         url='https://giecdn.blob.core.windows.net/fileuploads/document/2025/03/10/0325_benchmarking_report.pdf', years='2024 data'),
    dict(key='ll26', name='Lawn & Landscape, Benchmarking Your Business 2026 report (March 2026)', file=LL26_PDF,
         url='https://giecdn.blob.core.windows.net/fileuploads/document/2026/03/03/0326_benchmarking_full.pdf', years='2025 data'),
    dict(key='hfa_report', name='HFA 2025 Fitness Industry Benchmarking Report, product page', file=HFA_REPORT,
         url='https://www.healthandfitness.org/2025-fitness-industry-benchmarking-report/', years='2024 data'),
    dict(key='hfa_release', name='HFA press release on the 2025 benchmarking report', file=HFA_RELEASE,
         url='https://www.healthandfitness.org/hfa-releases-2025-fitness-industry-benchmarking-report/', years='2024 data'),
    dict(key='ihrsa_pos', name='IHRSA 2019 Profiles of Success, product page', file=IHRSA_POS,
         url='https://www.healthandfitness.org/ihrsa-2019-profiles-of-success/', years='2018 data'),
    dict(key='hcm_numbers', name='Health Club Management: IHRSA update, the numbers are in (2019 Profiles of Success)', file=HCM_NUMBERS,
         url='http://www.healthclubmanagement.co.uk/health-club-management-features/The-numbers-are-in/34259', years='2018 data'),
    dict(key='hcm_oms', name='Health Club Management: IHRSA One Million Strong', file=HCM_OMS,
         url='http://www.healthclubmanagement.co.uk/health-club-management-features/IHRSA-update-One-million-strong/30115', years='2012-2015'),
    dict(key='kbcm', name='2021 KBCM (KeyBanc) Private SaaS Company Survey', file=KBCM_PDF,
         url='https://www.forentrepreneurs.com/wp-content/uploads/2021/10/2021-KBCM-SaaS-Survey.pdf', years='2020 data'),
    dict(key='servicetitan', name='ServiceTitan Residential Services Report press release (Thrive Analytics survey)', file=SERVICETITAN,
         url='https://www.servicetitan.com/press/industry-trends-residential-services', years='2023 (release of Nov. 30, 2023)'),
    dict(key='rowriter', name='R.O. Writer blog citing Auto Apps shop data', file=ROWRITER,
         url='https://info.rowriter.com/blog/customer-attrition-auto-repair/', years='seven years to the post'),
    dict(key='shopify', name='Shopify blog citing Bluecore 2025 Customer Growth Benchmarks', file=SHOPIFY,
         url='https://www.shopify.com/blog/average-customer-retention-rate-by-industry', years='2025'),
    dict(key='datto', name='ITPro on Datto State of the MSP 2019', file=DATTO,
         url='https://www.itpro.com/business-operations/managed-service-provider-msp/365496/recurring-services-key-to-msp-success-datto', years='2019'),
    dict(key='rcpmag', name='Redmond Channel Partner on the Kaseya 2016/17 MSP Global Pricing Survey', file=RCPMAG,
         url='https://rcpmag.com/articles/2017/02/01/road-to-recurring-revenue.aspx', years='2016'),
    dict(key='mcw', name='Mister Car Wash Q2 2025 earnings release (8-K EX-99.1)', file=MCW,
         url='https://www.sec.gov/Archives/edgar/data/0001853513/000095017025100216/mcw-ex99_1.htm', years='Q2 2025'),
    dict(key='nbb', name='National Bank of Belgium Working Paper 444 (2023), Belgian B2B network', file=NBB_PDF,
         url='https://www.nbb.be/doc/ts/publications/wp/wp444en.pdf', years='2002-2021'),
    dict(key='nber', name='Baqaee, Burstein, Duprez, Farhi, NBER WP 31231', file=NBER_PDF,
         url='https://www.nber.org/system/files/working_papers/w31231/w31231.pdf', years='Belgian firms'),
]


# ---------------------------------------------------------------- helpers
def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def rnd(x, nd):
    """round half up to nd decimals (Decimal on the shortest repr, so 0.0435 -> 0.044)"""
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def boot_median_se(x, k, B=B_BOOT):
    x = np.asarray(x, float)
    rng = np.random.default_rng([SEED, k])
    idx = rng.integers(0, len(x), size=(B, len(x)))
    return float(np.median(x[idx], axis=1).std(ddof=1))


def html_text(path):
    """the research round's html2txt.py (standard library parser): visible text, one block per line"""
    class P(html.parser.HTMLParser):
        def __init__(s):
            super().__init__(); s.out = []; s.skip = 0

        def handle_starttag(s, t, a):
            if t in ('script', 'style', 'noscript', 'svg'): s.skip += 1
            if t in ('p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'td', 'th', 'section', 'table'): s.out.append('\n')

        def handle_endtag(s, t):
            if t in ('script', 'style', 'noscript', 'svg') and s.skip: s.skip -= 1
            if t in ('td', 'th'): s.out.append(' | ')

        def handle_data(s, d):
            if not s.skip: s.out.append(d)
    p = P(); p.feed(open(path, encoding='utf-8', errors='replace').read())
    t = ''.join(p.out); t = re.sub(r'[ \t]+', ' ', t); return re.sub(r'\n\s*\n+', '\n', t)


PDFTOTEXT = shutil.which('pdftotext')


def pdf_text(path, page, layout=False):
    if not PDFTOTEXT:
        return None
    cmd = [PDFTOTEXT] + (['-layout'] if layout else []) + ['-f', str(page), '-l', str(page), path, '-']
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return r.stdout


def d2(x):
    """0.43 -> '.43' (the console's style for shares)"""
    t = '%.2f' % x
    return t[1:] if t.startswith('0.') else t


def d3(x):
    t = '%.3f' % x
    return t[1:] if t.startswith('0.') else t


def norm(t):
    return re.sub(r'\s+', ' ', t.replace('’', "'").replace('–', '-').replace('—', '-'))


QUOTES = {}


def quote(src, label, text, pattern):
    """record whether a quoted number is in the downloaded text; None when the text could not be produced"""
    found = None if text is None else bool(re.search(pattern, norm(text), re.I | re.S))
    QUOTES.setdefault(src, {})[label] = found
    return found


def grouped(bins):
    """bins: (label, lo, hi, weight) on a 0-1 scale, uniform within a bin, lo == hi a point mass"""
    lab = [b[0] for b in bins]; lo = np.array([b[1] for b in bins], float); hi = np.array([b[2] for b in bins], float)
    w = np.array([b[3] for b in bins], float); W = w.sum(); mid = (lo + hi) / 2
    mean = float((w * mid).sum() / W)
    sd_mid = float(np.sqrt((w * (mid - mean) ** 2).sum() / W))
    sd_unif = float(np.sqrt((w * ((mid - mean) ** 2 + (hi - lo) ** 2 / 12)).sum() / W))
    o = np.lexsort((hi, lo)); lo, hi, w = lo[o], hi[o], w[o]; cum = np.cumsum(w) / W

    def q(p):
        j = int(np.searchsorted(cum, p - 1e-12)); prev = cum[j - 1] if j else 0.0
        return float(lo[j]) if hi[j] == lo[j] else float(lo[j] + (hi[j] - lo[j]) * (p - prev) / (cum[j] - prev))
    jm = int(np.searchsorted(cum, 0.5 - 1e-12))
    dens = float(w[jm] / W / (hi[jm] - lo[jm])) if hi[jm] > lo[jm] else float('nan')
    p25, p50, p75 = q(.25), q(.5), q(.75)
    return dict(n_bins=len(lab), weight_sum=float(W), mean=mean, sd_midpoints=sd_mid, sd_uniform=sd_unif, p25=p25, median=p50,
                p75=p75, iqr_sd=(p75 - p25) / 1.349, density_at_median=dens)


os.makedirs(OUT, exist_ok=True)
TESTS = {}
OPEN = []

# ================================================================ 0. the snapshot (read only)
html_src = open(INDEX, encoding='utf-8').read()
blk = re.search(r'const IND = \{(.*?)\n\};', html_src, re.S).group(1)
IND = {}
for m in re.finditer(r'(\w+):\s*\{n:"([^"]*)",\s*anchor:([-.\d]+),\s*buyers:(\d+),\s*gm:([-.\d]+),\s*grw:([-.\d]+),\s*rec:([-.\d]+),\s*ret:([-.\d]+)', blk):
    IND[m.group(1)] = dict(label=m.group(2), rec=float(m.group(7)), ret=float(m.group(8)))
KEYS = list(IND)
Z_REC = float(re.search(r'rec\s*:\(s\.rec-I\.rec\)/(\.\d+)', html_src).group(1))
Z_RET = float(re.search(r'ret\s*:\(s\.ret-I\.ret\)/(\.\d+)', html_src).group(1))
SLIDER = {k: tuple(int(v) / 100 for v in re.search(r'id="i_%s" min="(-?\d+)" max="(\d+)"' % k, html_src).groups()) for k in ('rec', 'ret')}
TESTS['snapshot: 16 industries, z-scales .28 and .13 read from model()'] = len(IND) == 16 and Z_REC == 0.28 and Z_RET == 0.13
TESTS['snapshot: the values kept as judgment are the snapshot\'s (fit.rec .70, saas.rec .85)'] = (
    IND['fit']['rec'] == KEPT['fit.rec'] and IND['saas']['rec'] == KEPT['saas.rec'])
print('snapshot: %d industries; z.rec /%.2f, z.ret /%.2f; sliders rec %s ret %s' % (len(IND), Z_REC, Z_RET, SLIDER['rec'], SLIDER['ret']))

# ================================================================ 1. Census 2022 product lines (fit.rec, flags, spreads)
CEN_NAICS = {'713940', '541513', '541519', '561320', '541940', '811192', '561730'}
cen_rows = []
hz = hashlib.sha256()
with zipfile.ZipFile(CENSUS_ZIP) as z:
    with z.open('EC2200NAPCSINDPRD.dat') as f:
        hdr_raw = f.readline(); hz.update(hdr_raw)
        hdr = hdr_raw.decode('latin-1').lstrip('#').rstrip('\r\n').split('|'); ix = {h: i for i, h in enumerate(hdr)}
        n_lines = 0
        for raw in f:
            hz.update(raw); n_lines += 1
            r = raw.decode('latin-1').rstrip('\r\n').split('|')
            if r[ix['GEOTYPE']] == '01' and r[ix['TYPOP']] == '00' and r[ix['NAICS2022']] in CEN_NAICS:
                cen_rows.append(r)
dat_sha = hz.hexdigest()
C = pd.DataFrame(cen_rows, columns=hdr)
for c in ['ESTAB', 'NAPCSDOL', 'LINEALL_PCT', 'LINEALL_PCT_SE', 'LINE_PCT', 'LINE_PCT_SE', 'ESTAB_PCT', 'NAPCSDOL_CV']:
    C[c] = pd.to_numeric(C[c], errors='coerce')
copy_sha = sha256_file(CENSUS_DAT_COPY) if os.path.exists(CENSUS_DAT_COPY) else None


def cline(naics, tax, napcs):
    x = C[(C.NAICS2022 == naics) & (C.TAXSTAT == tax) & (C.NAPCS2022 == napcs)]
    assert len(x) == 1, (naics, tax, napcs, len(x))
    return x.iloc[0]


def cshare(naics, tax, codes):
    tot = cline(naics, tax, '0000000000').NAPCSDOL
    return float(sum(cline(naics, tax, c).NAPCSDOL for c in codes) / tot)


def two_point(naics, tax, napcs):
    r = cline(naics, tax, napcs); p = r.ESTAB_PCT / 100; m = r.LINE_PCT / 100
    return float(m * np.sqrt(p * (1 - p)))


MEM = '7001900003'
mem = {t: cline('713940', t, MEM) for t in ('T', '00', 'Y')}
tot = {t: cline('713940', t, '0000000000') for t in ('T', '00', 'Y')}
fit_rec = float(mem['T'].NAPCSDOL / tot['T'].NAPCSDOL)
fit_rec_se = fit_rec * float(mem['T'].NAPCSDOL_CV) / 100
census = dict(
    naics='713940', taxstat='T', napcs=MEM, label=mem['T'].NAPCS2022_LABEL,
    line_k=int(mem['T'].NAPCSDOL), industry_k=int(tot['T'].NAPCSDOL), share=fit_rec, se=fit_rec_se,
    published_lineall_pct=float(mem['T'].LINEALL_PCT), published_lineall_pct_se=float(mem['T'].LINEALL_PCT_SE),
    cv_pct=float(mem['T'].NAPCSDOL_CV), establishments=int(tot['T'].ESTAB), establishments_reporting=int(mem['T'].ESTAB),
    estab_pct_reporting=float(mem['T'].ESTAB_PCT) / 100, line_pct_among_reporters=float(mem['T'].LINE_PCT) / 100,
    line_pct_among_reporters_se=float(mem['T'].LINE_PCT_SE) / 100, sd_two_point=two_point('713940', 'T', MEM),
    share_all_establishments=float(mem['00'].NAPCSDOL / tot['00'].NAPCSDOL),
    share_tax_exempt=float(mem['Y'].NAPCSDOL / tot['Y'].NAPCSDOL),
    personal_training=cshare('713940', 'T', ['7002100000']), admissions=cshare('713940', 'T', ['7001900006']),
    skating_rinks=cshare('713940', 'T', ['7001925000', '7001950000']),
    all_other_recreation=cshare('713940', 'T', ['7002025000']),
    rink_establishments=int(sum(cline('713940', 'T', c).ESTAB for c in RINK_NAPCS)),
    admissions_establishments=int(cline('713940', 'T', '7001900006').ESTAB),
    fitness_services_establishments=int(cline('713940', 'T', '7001900000').ESTAB),
    personal_training_establishments=int(cline('713940', 'T', '7002100000').ESTAB),
    personal_training_line_pct=float(cline('713940', 'T', '7002100000').LINE_PCT) / 100,
    zip_sha256=sha256_file(CENSUS_ZIP), dat_member_sha256=dat_sha, dat_rows=n_lines,
    extracted_copy_matches=(copy_sha == dat_sha) if copy_sha else None)
MSP_INFRA = ['7014450000']
MSP_HOST = ['7014250000', '7014325000', '7014350000', '7014375000', '7014410000', '7014275000']
census['msp_541513'] = dict(managed_infra=cshare('541513', 'T', MSP_INFRA),
                            with_hosting_bpm=cshare('541513', 'T', MSP_INFRA + MSP_HOST + ['7014300000']),
                            with_it_support=cshare('541513', 'T', MSP_INFRA + MSP_HOST + ['7014300000', '7014475000']),
                            establishments=int(cline('541513', 'T', '0000000000').ESTAB))
census['staff_561320'] = dict(temp_staffing=cshare('561320', '00', ['7010350000']), perm_placement=cshare('561320', '00', ['7010300000']),
                              establishments=int(cline('561320', '00', '0000000000').ESTAB))
census['wash_811192'] = dict(automatic=cshare('811192', 'T', ['7002650006']), note='no membership or club line in NAPCS')
# landscaping (revision 3): 561730 has no taxable split in the file, so all establishments (TAXSTAT 00)
assert set(C[C.NAICS2022 == '561730'].TAXSTAT) == {'00'}, 'NAICS 561730 now has a taxable split: revisit the land.rec flag'
_lc = {k: cline('561730', '00', c) for k, c in LAND_CARE_NAPCS.items()}
census['land_561730'] = dict(
    care_maintenance=cshare('561730', '00', list(LAND_CARE_NAPCS.values())),
    lines={k: dict(napcs=LAND_CARE_NAPCS[k], share=float(r.NAPCSDOL / cline('561730', '00', '0000000000').NAPCSDOL),
                   published_lineall_pct=float(r.LINEALL_PCT), estab_pct_reporting=float(r.ESTAB_PCT) / 100,
                   line_pct_among_reporters=float(r.LINE_PCT) / 100) for k, r in _lc.items()},
    **{k: cshare('561730', '00', v) for k, v in LAND_OTHER_NAPCS.items()},
    establishments=int(cline('561730', '00', '0000000000').ESTAB), taxstat='00 (all establishments; no taxable split for 561730)',
    note=('revenue-weighted (line revenue over industry revenue). An upper bound for the recurring or contracted share: the lines '
          'cover all care and maintenance work, contracted or one-off (cleanups, tree work), and do not record contract status. '
          'The lines overlap across establishments (many report both residential and commercial), so an establishment-level '
          'median cannot be read from them'))
census['sd_two_point'] = {
    'fit_713940_memberships': census['sd_two_point'],
    'msp_541513_managed_infrastructure': two_point('541513', 'T', '7014450000'),
    'msp_541519_it_support': two_point('541519', 'T', '7014475000'),
    'staff_561320_temporary_staffing': two_point('561320', '00', '7010350000'),
    'vet_541940_routine_exams': two_point('541940', 'T', '7002575003')}
C[C.NAICS2022 == '713940'][['TAXSTAT', 'NAPCS2022', 'NAPCS2022_LABEL', 'ESTAB', 'NAPCSDOL', 'LINEALL_PCT', 'LINEALL_PCT_SE', 'LINE_PCT',
                            'LINE_PCT_SE', 'ESTAB_PCT', 'NAPCSDOL_CV']].to_csv(OUT + '/census_lines.csv', index=False)
TESTS['census: share recomputed from NAPCSDOL matches the published LINEALL_PCT (66.0) to rounding'] = abs(100 * fit_rec - census['published_lineall_pct']) < 0.05 + 1e-9
TESTS['census: the .dat inside the zip is byte-identical to the research copy'] = census['extracted_copy_matches'] is not False
TESTS['census: 561730 care and maintenance lines reproduce the research (.860 of revenue; 116,787 establishments)'] = (
    abs(census['land_561730']['care_maintenance'] - 0.860) < 0.0005 and census['land_561730']['establishments'] == 116787)
TESTS['census: 561730 line shares recomputed from NAPCSDOL match the published LINEALL_PCT to rounding'] = all(
    abs(100 * v['share'] - v['published_lineall_pct']) < 0.05 + 1e-9 for v in census['land_561730']['lines'].values())
print('fit.rec: memberships %.4f of taxable 713940 revenue (published %.1f%%), SE %.4f (CV %.1f%%); %d establishments, %.1f%% report the line, %.2f among them'
      % (fit_rec, census['published_lineall_pct'], fit_rec_se, census['cv_pct'], census['establishments'], 100 * census['estab_pct_reporting'],
         census['line_pct_among_reporters']))

# ================================================================ 2a. Empire Flippers subscription listings (saas.rec)
E = pd.read_csv(EF_LISTINGS, low_memory=False)
S = E[E.mrr.notna() & E.monetization_primary.isin(EF_MONETIZATIONS)].copy().sort_values('listing_number')
S['rec_share_raw'] = S.mrr * 12 / S.average_annual_gross_revenue
S['rec_share'] = S.rec_share_raw.clip(upper=1.0)
S['ret_annual'] = (1 - S.churn_percent / 100) ** 12
MM = pd.read_csv(EF_MONTHLY)
last3 = (MM.sort_values(['listing_number', 'month']).groupby('listing_number').tail(3).groupby('listing_number').gross_revenue.mean())
S['rec_share_last3'] = (S.mrr / S.listing_number.map(last3)).clip(upper=1.0)
S['software_tag'] = S.monetizations.fillna('').str.contains(r'\bSaaS\b|\bApplication\b', regex=True)
x_ef = S.rec_share.dropna()
ef = dict(n=int(len(x_ef)), n_sold=int((S.listing_status == 'Sold').sum()), n_for_sale=int((S.listing_status == 'For Sale').sum()),
          median=float(x_ef.median()), se=boot_median_se(x_ef, 1), sd=float(x_ef.std(ddof=1)), n_capped=int((S.rec_share_raw >= 1).sum()),
          median_revenue=float(S.average_annual_gross_revenue.median()),
          by_monetization={k: int(v) for k, v in S.monetization_primary.value_counts().sort_index().items()})


def ef_sub(mask, k):
    x = S.loc[mask, 'rec_share'].dropna()
    return dict(n=int(len(x)), median=float(x.median()), se=boot_median_se(x, k))


ef['subsets'] = {
    'saas_primary': ef_sub(S.monetization_primary == 'SaaS', 2),
    'software_tagged (SaaS or Application anywhere in monetizations)': ef_sub(S.software_tag, 3),
    'without agency and service': ef_sub(~S.monetization_primary.isin(['Agency', 'Service']), 4),
    'sold only': ef_sub(S.listing_status == 'Sold', 5),
    'uncapped ratio': dict(n=int(S.rec_share_raw.notna().sum()), median=float(S.rec_share_raw.median())),
    'growth-neutral (MRR / mean of the last 3 months of revenue, capped)': dict(n=int(S.rec_share_last3.notna().sum()), median=float(S.rec_share_last3.median())),
}
y_ef = S.ret_annual.dropna()
ef['retention_from_monthly_churn'] = dict(n=int(len(y_ef)), median=float(y_ef.median()), se=boot_median_se(y_ef, 6), sd=float(y_ef.std(ddof=1)),
                                          p25=float(y_ef.quantile(.25)), p75=float(y_ef.quantile(.75)),
                                          median_monthly_churn_pct=float(S.churn_percent.median()))
S[['listing_number', 'listing_status', 'monetization_primary', 'monetizations', 'mrr', 'average_annual_gross_revenue', 'pricing_period_months',
   'rec_share_raw', 'rec_share', 'rec_share_last3', 'churn_percent', 'ret_annual', 'gross_revenue_trend_percent']].to_csv(OUT + '/ef_subscription.csv', index=False)
print('saas.rec EF: n %d (%d sold) median %.4f SE %.4f sd %.3f; SaaS-primary %.3f (n %d)' % (ef['n'], ef['n_sold'], ef['median'], ef['se'], ef['sd'],
      ef['subsets']['saas_primary']['median'], ef['subsets']['saas_primary']['n']))

# ================================================================ 2b. DealLedger listings (saas.rec statements, ordering check, spreads)
# Copied from the research round's dl_text_mine2.py (listing build, classifier, statement patterns, mention flags) and
# summaries.py (exclusions). Only the 'rec' statement patterns are run: the de-duplication works within a kind, so the
# 'rec' rows are the same as the research's.
snap_files = sorted(glob.glob(os.path.join(DL_SNAPS, '*', 'listings.csv')))
fr = []
for fpath in snap_files:
    d = pd.read_csv(fpath, low_memory=False, dtype=str)
    d['snap'] = fpath.split('/')[-2]
    fr.append(d)
A = pd.concat(fr, ignore_index=True)
A['key'] = A['url'].fillna(A.get('source_url'))
A['desc'] = A['description'].fillna(A.get('raw_text')).fillna('')
CUT = re.compile(r'other businesses for sale|featured listings|similar listings|more listings|related listings|recently viewed|you may also like|businesses for sale (?:available|pending)', re.I)
NAV = re.compile(r'←?\s*back to listings\s*(?:print listing\s*→?)?', re.I)


def clean(t):
    t = t or ''
    m = CUT.search(t)
    if m: t = t[:m.start()]
    return NAV.sub(' ', t)


A['cdesc'] = A['desc'].map(clean)
A['dlen'] = A['cdesc'].str.len()
A = A.sort_values(['key', 'dlen', 'snap'], kind='mergesort')
L = A.groupby('key').tail(1).copy()
L = L[L['key'].notna()]
L['text'] = (L['title'].fillna('') + ' . ' + L['cdesc']).str.lower()
L = L.drop_duplicates(subset=['text']).copy()
del A, fr
IND_RX = [
    ('insur', r'insurance agency|policies in force|policies-in-force|written premium|book of business|allstate|state farm|farmers insurance|loss ratio'),
    ('agency', r'marketing agency|digital agency|seo agency|advertising agency|web design agency|lead generation agency|creative agency|media agency|branding agency|development agency'),
    ('wash', r'car ?wash|auto ?wash|express wash|tunnel wash|wash club|unlimited wash|auto spa\b'),
    ('vet', r'veterinar|animal hospital|vet clinic|pet clinic|\bdvm\b'),
    ('msp', r'managed service|managed it|it services|it support|\bmsp\b|cybersecurity|network services|it consulting|computer services'),
    ('saas', r'\bsaas\b|software|subscription platform|platform as a service'),
    ('medical', r'dental|dentist|medical practice|medical clinic|physician|chiropract|physical therap|optometr|med ?spa|orthodont|urgent care|primary care|dermatolog|home health|audiolog'),
    ('fit', r'fitness|\bgym\b|yoga|pilates|martial arts|crossfit|boxing|barre|cycling studio|personal training|health club|stretchlab|f45'),
    ('land', r'landscap|lawn|tree service|irrigation|snow removal|grounds maintenance|turf'),
    ('staff', r'staffing|recruit|employment agency|temp agency|placement agency'),
    ('prof', r'accounting|\bcpa\b|bookkeeping|tax practice|tax preparation|payroll service|law firm|legal practice|consulting firm|engineering firm|architect'),
    ('ecom', r'e-?commerce|amazon|shopify|online store|\bfba\b|online retailer|dropship'),
    ('rest', r'restaurant|pizza|cafe\b|coffee|bakery|\bbar\b|\bpub\b|tavern|grill|diner|sushi|taco|food truck|catering|brewery|ice cream|yogurt|\bdeli\b|bistro'),
    ('home', r'hvac|plumb|electrical contractor|electrician|heating|air condition|roofing|pest control|garage door|handyman|home service|septic|water heater|pool service'),
    ('auto', r'auto repair|automotive repair|collision|body shop|\btire|oil change|transmission|mechanic|auto service'),
    ('constr', r'construction|contractor|concrete|excavat|paving|drywall|framing|remodel'),
    ('mfg', r'manufactur|machine shop|fabricat|\bcnc\b|plastics|printing company'),
    ('dist', r'distribut|wholesale'),
]
IND_C = [(k, re.compile(p)) for k, p in IND_RX]


def cls(t):
    for k, p in IND_C:
        if p.search(t):
            return k
    return 'other'


L['ind'] = L['text'].map(cls)
L['text_noql'] = L['text'].str.replace(QLNAV, ' ', regex=False)
L['ind_noql'] = L['text_noql'].map(cls)
L['quietlight'] = L['key'].str.contains('quietlight.com', regex=False, na=False)
L['qlnav'] = L['text'].str.contains(QLNAV, regex=False)
NUM = r'(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)'
RANGE = r'(?:\d{1,3}\s*(?:%|percent)?\s*(?:-|–|to)\s*)?'
APPROX = r'(?:(?:over|nearly|approximately|approx\.?|about|almost|roughly|more than|greater than|in excess of|above|~|at least|close to|exceeding|exceeds|exceed|an estimated|estimated)\s*)?'
REC_NOUN = r'(?:recurring|contracted|contract[- ]based|contract[- ]led|under (?:long[- ]term )?contracts?|contractual|subscriptions?|subscription[- ]based|memberships?|membership[- ]based|maintenance (?:agreements?|contracts?|plans?)|service (?:agreements?|contracts?|plans?)|retainers?|retainer[- ]based)'
OF_REV = r'(?:of\s+(?:the\s+)?(?:company\'?s\s+|total\s+|gross\s+|annual\s+|overall\s+|business\s+)?(?:revenue|revenues|sales|income|billings|receipts|gross revenues|business)\s+)'
VERB = r'(?:(?:is|are|comes?|derived|generated|tied)\s+)?(?:(?:from|through|by|via|in)\s+)?(?:the\s+)?'
pat_rec_a = re.compile(APPROX + RANGE + NUM + r'\s*\+?\s*' + OF_REV + r'?' + VERB + REC_NOUN + r'(?!\s+(?:order|customers?\b|clients?\b|rate|members?\b))')
pat_rec_b = re.compile(r'(?:recurring|contracted|subscription|membership|maintenance[- ]contract|service[- ]agreement)\s+(?:revenue|revenues|income|billings|sales)\s+(?:represents|representing|accounts? for|accounting for|comprises|comprising|makes? up|making up|of|is|at|totals?|totaling|:|-)\s*' + APPROX + RANGE + NUM + r'\s*\+?\s*(?:of\s+(?:total\s+|gross\s+|annual\s+)?(?:revenue|revenues|sales|income|billings|business)|$|[\s,.;|)])')
EXCL = re.compile(r'coverage|loss ratio|gross margin|net margin|profit margin|increase|occupancy|conversion|commission|royalt|rent\b|interest|financing|down payment|of the purchase|equity|discount|off\b|growth|yoy|cagr|open rate|click', re.I)
rows = []
for key, t, ind, title, rev in zip(L['key'], L['text'], L['ind'], L['title'], L['revenue']):
    for pat in (pat_rec_a, pat_rec_b):
        for m in pat.finditer(t):
            v = float(m.group(1))
            if not (0 < v <= 100):
                continue
            s0, s1 = max(0, m.start() - 100), min(len(t), m.end() + 60)
            ctx = t[s0:s1].replace('\n', ' ')
            near = t[max(0, m.start() - 25):min(len(t), m.end() + 25)]
            if EXCL.search(near):
                continue
            rows.append(dict(kind='rec', val=v, ctx=ctx, key=key, ind=ind, title=str(title)[:90], rev=rev, start=m.start()))
H = pd.DataFrame(rows)
H['sig'] = [f"{k}|{v}|" + re.sub(r'\s+', ' ', c[max(0, 100 - 40):100 + 40]) for k, v, c in zip(H.kind, H.val, H.ctx)]
H = H.sort_values(['key', 'start'], kind='mergesort').drop_duplicates(subset=['sig'])
H = H.drop_duplicates(subset=['key', 'kind', 'val'])
BAD_CTX = ['lash studio', 'massage and skincare', 'massage & sk', 'skincare studio', 'no customer represents more than 5%', 'hormone therapy']
H['bad'] = H.ctx.str.contains('|'.join(BAD_CTX), regex=True)
R = H[~H.bad].copy()
R['ind_noql'] = R.key.map(dict(zip(L.key, L.ind_noql)))
R['software_review'] = R.key.map(lambda k: SAAS_STATEMENT_REVIEW.get(k, (None, ''))[0])
R['review_note'] = R.key.map(lambda k: SAAS_STATEMENT_REVIEW.get(k, (None, ''))[1])
R.sort_values(['ind', 'key', 'start'])[['ind', 'ind_noql', 'val', 'key', 'title', 'rev', 'software_review', 'review_note', 'ctx']].to_csv(OUT + '/dl_rec_statements.csv', index=False)


def dl_stated(ind, k):
    x = R[R.ind == ind].val.to_numpy() / 100
    return dict(n=int(len(x)), median=float(np.median(x)), se=boot_median_se(x, k) if len(x) >= 3 else None,
                sd=float(np.std(x, ddof=1)) if len(x) > 1 else None)


dl = {k: dl_stated(k, 10 + i) for i, k in enumerate(['saas', 'fit', 'land'])}
sw = R[(R.ind == 'saas') & (R.software_review == True)].val.to_numpy() / 100     # noqa: E712
dl['saas_software_only'] = dict(n=int(len(sw)), median=float(np.median(sw)), se=boot_median_se(sw, 20), values=sorted(sw.round(2).tolist()))
saas_rows = R[R.ind == 'saas']
dl['saas_review'] = dict(n_reviewed=int(saas_rows.key.isin(list(SAAS_STATEMENT_REVIEW)).sum()), n_software=int(len(sw)),
                         not_software=sorted('%s %.2f' % (SAAS_STATEMENT_REVIEW[k][1], v / 100) for k, v in zip(saas_rows.key, saas_rows.val)
                                             if k in SAAS_STATEMENT_REVIEW and not SAAS_STATEMENT_REVIEW[k][0]),
                         from_quietlight=int(saas_rows.key.str.contains('quietlight.com', regex=False).sum()))
TESTS['dealledger: all saas statements are in the documented review'] = dl['saas_review']['n_reviewed'] == dl['saas']['n']
print('saas.rec DealLedger: n %d median %.3f SE %.4f; software-only n %d median %.3f' % (dl['saas']['n'], dl['saas']['median'], dl['saas']['se'],
      dl['saas_software_only']['n'], dl['saas_software_only']['median']))

# mention rates and the ordering check
REC_WORD = r'recurring|subscription|membership|maintenance (?:agreements?|contracts?|plans?)|service (?:agreements?|contracts?|plans?)|retainer|contracted revenue|under contract'
RET_WORD = r'retention|repeat customers|repeat clients|returning customers|loyal customer|long[- ]term (?:clients|customers)|churn'
L['has_desc'] = L.cdesc.str.len() > 200


def mention_rates(text_col, ind_col):
    D = pd.DataFrame(dict(ind=L[ind_col], rec=L[text_col].str.contains(REC_WORD, regex=True),
                          ret=L[text_col].str.contains(RET_WORD, regex=True), has=L.has_desc, ql=L.quietlight))
    D = D[D.has]
    M = D.groupby('ind').agg(n=('rec', 'size'), rec_rate=('rec', 'mean'), ret_rate=('ret', 'mean'), quietlight=('ql', 'sum'))
    return M.reindex(KEYS)


M_res = mention_rates('text', 'ind')
M_noql = mention_rates('text_noql', 'ind_noql')
SHIPPED_REC = {k: IND[k]['rec'] for k in KEYS}        # revision 2: no rec median ships, so the shipped ranks are the current ones


def spear(a, b):
    r = stats.spearmanr(a, b)
    return float(r.correlation), float(r.pvalue)


# ================================================================ 2c. saas.rec stays judgment: the cleaned pool, round 1's pool, KBCM
# round 1's pool as decided then (EF 29 + DealLedger 11 as classified): context only, not shipped
w = np.array([1 / ef['se'] ** 2, 1 / dl['saas']['se'] ** 2])
mm = np.array([ef['median'], dl['saas']['median']])
pool = float((w * mm).sum() / w.sum()); pool_se = float(1 / np.sqrt(w.sum()))
Q = float((w * (mm - pool) ** 2).sum())


def ivpool(parts):
    ww = np.array([1 / s ** 2 for _, s in parts]); xx = np.array([m for m, _ in parts])
    return dict(value=float((ww * xx).sum() / ww.sum()), se=float(1 / np.sqrt(ww.sum())))


EF_SW = ef['subsets']['software_tagged (SaaS or Application anywhere in monetizations)']
sens = {
    'EF saas-primary + DL software-only (their own n=4 bootstrap SE)': ivpool([(ef['subsets']['saas_primary']['median'], ef['subsets']['saas_primary']['se']),
                                                                              (dl['saas_software_only']['median'], dl['saas_software_only']['se'])]),
    'EF saas-primary + DL software-only (SE of the n=11 median)': ivpool([(ef['subsets']['saas_primary']['median'], ef['subsets']['saas_primary']['se']),
                                                                         (dl['saas_software_only']['median'], dl['saas']['se'])]),
    'EF software-tagged + DL software-only (SE of the n=11 median)': ivpool([(EF_SW['median'], EF_SW['se']),
                                                                            (dl['saas_software_only']['median'], dl['saas']['se'])]),
    'EF saas-primary + DL as decided (n=11)': ivpool([(ef['subsets']['saas_primary']['median'], ef['subsets']['saas_primary']['se']),
                                                      (dl['saas']['median'], dl['saas']['se'])]),
    'EF sold only + DL as decided (n=11)': ivpool([(ef['subsets']['sold only']['median'], ef['subsets']['sold only']['se']),
                                                   (dl['saas']['median'], dl['saas']['se'])]),
}
# KBCM check (pages read from the PDF text layer when pdftotext is installed)
kb_txt = {p: pdf_text(KBCM_PDF, p, layout=True) for p in (23, 26, 28)}


def parse_bins(text, spec, attach=False):
    if text is None:
        return None
    t = norm(text)
    out = []
    for lab, lo, hi, cnt in spec['bins']:
        if attach:
            m = re.search(re.escape(lab) + r':\s*(\d+)', t)
        else:
            m = re.search(r'(?<![\d.\-])' + re.escape(lab) + r'\s+(\d+)', t)
        out.append(int(m.group(1)) if m else None)
    return out


kbcm_parsed = {'gross_dollar_churn': parse_bins(kb_txt[23], KBCM_GDC), 'logo_churn': parse_bins(kb_txt[26], KBCM_LOGO),
               'ps_attach': parse_bins(kb_txt[28], KBCM_ATTACH, attach=True)}
kbcm_const = {'gross_dollar_churn': [b[3] for b in KBCM_GDC['bins']], 'logo_churn': [b[3] for b in KBCM_LOGO['bins']],
              'ps_attach': [b[3] for b in KBCM_ATTACH['bins']]}
for k in kbcm_parsed:
    QUOTES.setdefault('kbcm', {})[k + ' bin counts'] = None if kbcm_parsed[k] is None else kbcm_parsed[k] == kbcm_const[k]
quote('kbcm', 'gross dollar churn: Respondents: 173', kb_txt[23], r'Respondents:\s*173')
quote('kbcm', 'gross dollar churn median 12.6%', kb_txt[23], r'12\.6%')
quote('kbcm', 'logo churn: Respondents: 166', kb_txt[26], r'Respondents:\s*166')
quote('kbcm', 'logo churn median 13.4%', kb_txt[26], r'13\.4%')
quote('kbcm', 'attach: Respondents: 152', kb_txt[28], r'Respondents:\s*152')
att = grouped(KBCM_ATTACH['bins'])
mids = [(lo + hi) / 2 for _, lo, hi, _ in KBCM_ATTACH['bins']]
share_bins = [(lab, 1 / (1 + m), 1 / (1 + m), c) for (lab, lo, hi, c), m in zip(KBCM_ATTACH['bins'], mids)]
kb_share = grouped(share_bins)
kbcm_check = dict(n=KBCM_ATTACH['n'], attach_median=att['median'], subscription_share_at_median_attach=1 / (1 + att['median']),
                  share_at_10pct_attach=1 / 1.10,
                  share_of_firms_attach_le_10pct=sum(b[3] for b in KBCM_ATTACH['bins'][:2]) / KBCM_ATTACH['n'],
                  subscription_share_sd_bin_midpoints=kb_share['sd_midpoints'],
                  note='subscription share of new contract value = 1/(1 + professional-services attach); firms with $5M+ ARR, 2020; not pooled')
TESTS['kbcm: bin counts re-parsed from the PDF text equal the transcribed constants'] = all(v is not False for v in QUOTES['kbcm'].values())
CLEAN_KEY = 'EF saas-primary + DL software-only (SE of the n=11 median)'
clean_pool = sens[CLEAN_KEY]
saas_z = (clean_pool['value'] - KEPT['saas.rec']) / clean_pool['se']
saas_check = dict(
    kept=KEPT['saas.rec'], judgment=True,
    cleaned_pool=dict(value=clean_pool['value'], se=clean_pool['se'],
                      parts=dict(ef_saas_primary=dict(ef['subsets']['saas_primary'], what='Empire Flippers listings whose first monetization is SaaS'),
                                 dl_software=dict(n=dl['saas_software_only']['n'], median=dl['saas_software_only']['median'],
                                                  se_used=dl['saas']['se'], se_own_n4_bootstrap=dl['saas_software_only']['se'],
                                                  values=dl['saas_software_only']['values'],
                                                  what='DealLedger statements from listings read as software businesses; SE of the n=11 median carried'))),
    z_vs_kept=saas_z, within_one_se=bool(abs(saas_z) < 1), ci95=[clean_pool['value'] - 1.96 * clean_pool['se'], clean_pool['value'] + 1.96 * clean_pool['se']],
    round1_pool_as_decided=dict(value=pool, se=pool_se, Q=Q, n='EF 29 + DealLedger 11'),
    ef_saas_primary_alone=ef['subsets']['saas_primary'], ef_ratio_at_or_above_one=dict(n=ef['n_capped'], of=ef['n'], max_raw=float(S.rec_share_raw.max())),
    ef_growth_neutral_median=ef['subsets']['growth-neutral (MRR / mean of the last 3 months of revenue, capped)']['median'],
    kbcm_attach_implied=kbcm_check['subscription_share_at_median_attach'],
    sensitivities={k: v for k, v in sens.items()})
TESTS['saas.rec check: the cleaned pool lies within one SE of the kept .85 (the move is inside the noise)'] = abs(saas_z) < 1
print('saas.rec (kept %.2f): cleaned pool %.4f (SE %.4f), z %.2f; round 1 pool %.4f (SE %.4f), Q %.3f; EF SaaS-primary %.3f; KBCM %.3f'
      % (KEPT['saas.rec'], clean_pool['value'], clean_pool['se'], saas_z, pool, pool_se, Q, ef['subsets']['saas_primary']['median'],
         kbcm_check['subscription_share_at_median_attach']))

# ================================================================ 2d. fit.rec stays judgment: the establishment-level median implied by the Census line
_GX = np.linspace(-8, 8, 4001)
_GW = stats.norm.pdf(_GX) / stats.norm.pdf(_GX).sum()


def beta_quantile(mu, sd, q):
    k = mu * (1 - mu) / sd ** 2 - 1
    return None if k <= 0 else float(stats.beta.ppf(q, mu * k, (1 - mu) * k))


def logitnormal_quantile(mu, sd, q):
    """quantile q of a logit-normal whose mean and SD are mu and sd (moments on a fixed 4,001-point normal grid)"""
    def gap(p):
        y = 1 / (1 + np.exp(-(p[0] + np.exp(p[1]) * _GX)))
        m_ = float((_GW * y).sum())
        return np.array([m_ - mu, float(np.sqrt((_GW * (y - m_) ** 2).sum())) - sd])
    sol = optimize.least_squares(gap, [np.log(mu / (1 - mu)), 0.0], xtol=1e-14, ftol=1e-14, gtol=1e-14)
    if np.max(np.abs(gap(sol.x))) > 1e-7:
        return None
    return float(1 / (1 + np.exp(-(sol.x[0] + np.exp(sol.x[1]) * stats.norm.ppf(q)))))


def fitrec_grid(n_all, n_rep):
    p0 = 1 - n_rep / n_all; q = (0.5 - p0) / (1 - p0); rows = []
    for mu in FITREC_MU:
        for sd in FITREC_SD:
            for fam, fn in (('beta', beta_quantile), ('logit-normal', logitnormal_quantile)):
                v = fn(mu, sd, q)
                rows.append(dict(family=fam, mu_e=mu, sd_e=sd, median=v, mean_all_establishments=(1 - p0) * mu))
    return p0, q, rows


fr_p0, fr_q, fr_rows = fitrec_grid(census['establishments'], census['establishments_reporting'])
FG = pd.DataFrame(fr_rows)
FG.to_csv(OUT + '/fit_rec_median_grid.csv', index=False, float_format='%.5f')
fg = FG.dropna(subset=['median'])
sd_central = dl['fit']['sd']
fr_central = {fam: fn(FITREC_MU_CENTRAL, sd_central, fr_q) for fam, fn in (('beta', beta_quantile), ('logit-normal', logitnormal_quantile))}
_, q_nr, rows_nr = fitrec_grid(census['establishments'] - census['rink_establishments'],
                               census['establishments_reporting'])
fg_nr = pd.DataFrame(rows_nr).dropna(subset=['median'])
fr_central_nr = beta_quantile(FITREC_MU_CENTRAL, sd_central, q_nr)
# the establishment mean among reporters that puts the median at the kept .70 (Beta, central SD)
mu_for_kept = float(optimize.brentq(lambda mu: beta_quantile(mu, sd_central, fr_q) - KEPT['fit.rec'], 0.72, 0.90))
fitrec_check = dict(
    kept=KEPT['fit.rec'], judgment=True,
    census=dict(establishments=census['establishments'], reporting=census['establishments_reporting'], share_at_zero=fr_p0,
                reporters_line_pct=census['line_pct_among_reporters'], revenue_weighted_share=census['share'],
                median_is_reporters_quantile=fr_q),
    grid=dict(mu_e=FITREC_MU, sd_e=FITREC_SD, families=['beta', 'logit-normal'], cells=int(len(fg)),
              cells_infeasible=int(FG['median'].isna().sum())),
    central=dict(mu_e=FITREC_MU_CENTRAL, sd_e=sd_central, sd_source='SD of the %d DealLedger fitness listings that state a recurring share' % dl['fit']['n'],
                 median_beta=fr_central['beta'], median_logitnormal=fr_central['logit-normal']),
    range_all=[float(fg['median'].min()), float(fg['median'].max())],
    range_at_central_mu={'sd .10-.15': [float(fg[(fg.mu_e == FITREC_MU_CENTRAL) & fg.sd_e.between(0.10, 0.15)]['median'].min()),
                                        float(fg[(fg.mu_e == FITREC_MU_CENTRAL) & fg.sd_e.between(0.10, 0.15)]['median'].max())]},
    by_mu={str(mu): [float(fg[fg.mu_e == mu]['median'].min()), float(fg[fg.mu_e == mu]['median'].max())] for mu in FITREC_MU},
    share_of_cells_at_or_above_kept=float((fg['median'] >= KEPT['fit.rec']).mean()),
    mu_e_that_gives_kept_at_central_sd=mu_for_kept,
    variant_rinks_out=dict(base=census['establishments'] - census['rink_establishments'], median_is_reporters_quantile=q_nr,
                           central_beta=fr_central_nr, range_all=[float(fg_nr['median'].min()), float(fg_nr['median'].max())]),
    dealledger_stated=dict(n=dl['fit']['n'], median=dl['fit']['median'], sd=dl['fit']['sd'], note='listings that state a share; selected upward'),
    note=('non-reporters of the membership line at zero; the line is the recurring proxy (personal training packages and '
          'admissions are not counted); establishments, not firms; all taxable NAICS 713940 establishments, not businesses being sold'))
TESTS['fit.rec check: the kept .70 lies inside the range of establishment medians the stated grid implies'] = (
    fitrec_check['range_all'][0] <= KEPT['fit.rec'] <= fitrec_check['range_all'][1])
print('fit.rec (kept %.2f): %.1f%% of establishments at zero, median = reporters\' %.3f quantile; central (mu .86, sd %.3f) beta %.3f, '
      'logit-normal %.3f; grid range %.3f-%.3f; mu_e for .70 at the central sd %.3f; rinks out: central %.3f'
      % (KEPT['fit.rec'], 100 * fr_p0, fr_q, sd_central, fr_central['beta'], fr_central['logit-normal'], fitrec_check['range_all'][0],
         fitrec_check['range_all'][1], mu_for_kept, fr_central_nr))

# ================================================================ 3. land.ret (Lawn & Landscape 2025 and 2026)
ll25_p3, ll25_p6 = pdf_text(LL25_PDF, 3), pdf_text(LL25_PDF, 6)
ll26_p5, ll26_p7 = pdf_text(LL26_PDF, 5), pdf_text(LL26_PDF, 7)
quote('ll25', 'n = 433 landscapers and lawn care operators', ll25_p3, r'results are based on 433 landscapers and lawn care operators')
quote('ll25', 'printed tabulation date Jan. 27, 2024', ll25_p3, r'closed for tabulation on Jan\. 27, 2024')
quote('ll25', 'question and 88% mean, 93% median', ll25_p6, r"12 months ago, what percentage.{0,60}are still customers today\?\s*88%\s*93%\s*mean")
quote('ll25', 'median label', ll25_p6, r'\bmedian\b')
quote('ll26', 'average 88% in 2024 to 89% in 2025', ll26_p5, r'customer retention is up a tad from an average of 88% in 2024 to 89% in 2025')
quote('ll26', 'n = 320 respondents', ll26_p5, r'results are based on 320 total respondents')
QUOTES['ll26']['p. 7 histogram in the text layer (expected false: chart image, read by eye)'] = (None if ll26_p7 is None else
                                                                                                 bool(re.search(r'47%', norm(ll26_p7))))
hist_c = [(lab, max(lo - 0.5, 0) / 100, min(hi + 0.5, 100) / 100, p) if lo != hi else (lab, lo / 100, hi / 100, p) for lab, lo, hi, p in LL26_HIST]
hist_f = [(lab, lo / 100, min(hi + 1, 100) / 100, p) if lo != hi else (lab, lo / 100, hi / 100, p) for lab, lo, hi, p in LL26_HIST]
g26 = grouped(hist_c); g26f = grouped(hist_f)
g26['median_se_sampling'] = 1 / (2 * g26['density_at_median'] * np.sqrt(LL26['n']))
g26['convention'] = 'integer answers, k -> [k-0.5, k+0.5); 100% a point mass'
g26['median_bins_from_k'] = g26f['median']; g26['mean_bins_from_k'] = g26f['mean']
pd.DataFrame([dict(band=lab, lo=lo, hi=hi, pct_respondents=p) for lab, lo, hi, p in LL26_HIST]).to_csv(OUT + '/land_ret_2026_hist.csv', index=False)
# 2025: mean and median only; the research's lognormal-churn reading of the gap (spread check only)
c_mean, c_med = 1 - LL25['mean'], 1 - LL25['median']
s2 = 2 * np.log(c_mean / c_med); ll25_sd = float(c_mean * np.sqrt(np.exp(s2) - 1))
land = dict(value=float(LAND_RET), se=float(LAND_RET_SE), ll2025=dict(LL25, sd_lognormal_churn=ll25_sd, median_se_sampling=1.2533 * ll25_sd / np.sqrt(LL25['n'])),
            ll2026=dict(LL26, hist=g26, hist_sum=sum(p for *_, p in LL26_HIST)))
# the shipped value: the two survey means, n-weighted (the simple average is .885)
land_wmean = (LL25['mean'] * LL25['n'] + LL26['mean'] * LL26['n']) / (LL25['n'] + LL26['n'])
land['survey_means'] = dict(y2025=LL25['mean'], y2026=LL26['mean'], n_weighted=land_wmean, simple=(LL25['mean'] + LL26['mean']) / 2,
                            hist_2026_grouped_mean=g26['mean'])
land['medians'] = dict(y2025=LL25['median'], y2026_grouped=g26['median'])
land['median_gap_in_se'] = {k: (v - float(LAND_RET)) / float(LAND_RET_SE) for k, v in land['medians'].items()}
land['sampling_se_of_mean_2026'] = g26['sd_uniform'] / np.sqrt(LL26['n'])
land['se_note'] = ('SE .04 (analyst): respondents are self-selected trade-magazine readers who report on themselves (median revenue about '
                   '$920k); the sampling SE of the mean is about %.3f, so the SE is mostly selection' % land['sampling_se_of_mean_2026'])
TESTS['land.ret: 0.88 is the n-weighted mean of the 2025 and 2026 survey means, rounded half up'] = rnd(land_wmean, 2) == float(LAND_RET)
TESTS['land.ret: 0.88 within 0.01 of each survey mean (.88, .89) and of the 2026 histogram mean'] = all(
    abs(v - float(LAND_RET)) <= 0.01 + 1e-9 for v in (LL25['mean'], LL26['mean'], g26['mean']))
TESTS['land.ret: both medians (.93; 2026 grouped) lie within 1.5 shipped SEs above 0.88'] = all(
    0 <= v - float(LAND_RET) <= 1.5 * float(LAND_RET_SE) for v in land['medians'].values())
TESTS['land.ret: 2026 grouped mean within 0.015 of the printed 89%'] = abs(g26['mean'] - LL26['mean']) <= 0.015
TESTS['land.ret: 2026 histogram labels sum to 100 +- 2'] = abs(land['ll2026']['hist_sum'] - 100) <= 2
print('land.ret: 2025 mean %.2f median %.2f (n %d); 2026 mean %.2f (n %d), histogram median %.3f mean %.3f sd %.3f (IQR sd %.3f); '
      'n-weighted mean %.4f; ship %.2f SE %.3f (medians %.1f / %.1f SE above)'
      % (LL25['mean'], LL25['median'], LL25['n'], LL26['mean'], LL26['n'], g26['median'], g26['mean'], g26['sd_uniform'], g26['iqr_sd'],
         land_wmean, float(LAND_RET), float(LAND_RET_SE), land['median_gap_in_se']['y2025'], land['median_gap_in_se']['y2026_grouped']))

# ================================================================ 4. fit.ret (HFA 2025; IHRSA segments and One Million Strong)
t_rep, t_rel = norm(html_text(HFA_REPORT)), norm(html_text(HFA_RELEASE))          # norm: &nbsp; and line breaks -> one space
t_pos, t_num, t_oms = norm(html_text(IHRSA_POS)), norm(html_text(HCM_NUMBERS)), norm(html_text(HCM_OMS))
m = re.search(r'Member retention averaged (\d+\.\d)% for the year', t_rel)
hfa_ret = float(m.group(1)) / 100
hfa_n = int(re.search(r'data from (\d+) companies', t_rel).group(1))
hfa_us = int(re.search(r'including (\d+) US respondents', t_rep).group(1))
quote('hfa', 'member retention rate of 66.4% (product page)', t_rep, r'member retention rate of 66\.4%')
quote('hfa', '175 companies, 27 countries, 114 US respondents, over 8,000 locations', t_rep,
      r'175 companies representing more than 17,000 fitness facilities across 27 countries, including 114 US respondents, representing over 8,000 locations')
quote('hfa', 'surveyed April-June 2025', t_rel, r'surveyed between April and June 2025')
seg = {}
m = re.search(r'\(([\d.]+) per cent, versus ([\d.]+) per cent\) and independent clubs.*?\(([\d.]+) per cent, versus ([\d.]+) per cent\)', t_num, re.S)
seg['multipurpose'], seg['fitness_only'], seg['independent'], seg['chain'] = (float(v) / 100 for v in m.groups())
seg['clubs_60k_sqft_plus'] = float(re.search(r'60,000sq ft or more reported the highest member retention rate at ([\d.]+) per cent', t_num).group(1)) / 100
seg['independent_ihrsa_page'] = float(re.search(r'independent facilities posted a retention rate of ([\d.]+)%', t_pos).group(1)) / 100
seg['chain_ihrsa_page'] = float(re.search(r'clubs part of a chain indicated a retention rate of ([\d.]+)%', t_pos).group(1)) / 100
quote('ihrsa', 'all clubs: nearly seven out of 10 members retained in 2018', t_num, r'retain nearly seven out of 10 members in 2018')
quote('ihrsa', '98 firms, 10,859 clubs', t_pos, r'98 firms, representing 10,859 clubs')
oms_rate = float(re.search(r'rate of ([\d.]+) cancellations per 1,000 members per month', t_oms).group(1)) / 1000
oms_12 = float(re.search(r'([\d.]+) per cent of members retain their membership for at least 12 months', t_oms).group(1)) / 100
hfa_fac = int(re.search(r'more than ([\d,]+) fitness facilities', t_rep).group(1).replace(',', ''))
hfa_us_loc = int(re.search(r'representing over ([\d,]+) locations', t_rep).group(1).replace(',', ''))
quote('hfa', '"Member retention averaged 66.4%" (release: an average across the companies)', t_rel, r'Member retention averaged 66\.4% for the year')
quote('hfa', 'supplemented by open-source data from publicly listed companies', t_rep, r'supplemented by some open-source data from publicly listed companies')
fit_ret = rnd(hfa_ret, 2)
fit_ret_se = float((FIT_RET_RANGE[1] - FIT_RET_RANGE[0]) / RANGE_TO_SE)
fit_ret_se = rnd(fit_ret_se, 3)
fit_ret_se_hcm = rnd(float((FIT_RET_HCM_INDEPENDENT - FIT_RET_RANGE[0]) / RANGE_TO_SE), 3)     # revision 2's SE (HCM's .758)
fitret = dict(hfa=dict(retention=hfa_ret, statistic='average ("Member retention averaged 66.4% for the year")', companies=hfa_n,
                       us_respondents=hfa_us, non_us_respondents=hfa_n - hfa_us, facilities=hfa_fac, us_locations=hfa_us_loc,
                       facilities_per_company=hfa_fac / hfa_n, countries=27, data_year=2024,
                       population=('mostly multi-club operators: more than %s facilities over %d companies (about %.0f each; the %d US '
                                   'respondents run over %s locations), supplemented by public-company data; not a US small-studio median'
                                   % (f'{hfa_fac:,}', hfa_n, hfa_fac / hfa_n, hfa_us, f'{hfa_us_loc:,}'))),
              segments_ihrsa_2018=seg, range=[float(FIT_RET_RANGE[0]), float(FIT_RET_RANGE[1])],
              range_sources=dict(fitness_only='Health Club Management (IHRSA 2019 Profiles of Success, 2018 data)',
                                 independent="IHRSA's own product page for the same report (.732)",
                                 independent_hcm='Health Club Management reports .758 for independent clubs (revision 2\'s upper end; SE %.3f)' % fit_ret_se_hcm),
              se_rule='range / 4 (range read as a 95% interval)', se_with_hcm_independent=fit_ret_se_hcm,
              one_million_strong=dict(cancellations_per_member_month=oms_rate, annualised=(1 - oms_rate) ** 12, kept_12_months=oms_12,
                                      members='about 1.5 million', years='2012-2015'))
TESTS['fit.ret: range ends match the parsed segments (.584 fitness-only, HCM; .732 independent, IHRSA page; .758 independent, HCM, cited)'] = (
    abs(seg['fitness_only'] - float(FIT_RET_RANGE[0])) < 1e-9 and abs(seg['independent_ihrsa_page'] - float(FIT_RET_RANGE[1])) < 1e-9
    and abs(seg['independent'] - float(FIT_RET_HCM_INDEPENDENT)) < 1e-9)
TESTS['fit.ret: One Million Strong (annualised and 12-month survival) within one SE of 0.66'] = (
    abs((1 - oms_rate) ** 12 - fit_ret) <= fit_ret_se and abs(oms_12 - fit_ret) <= fit_ret_se)
TESTS['fit.ret: HFA respondents parsed (175 companies, 114 US, more than 17,000 facilities)'] = (hfa_n, hfa_us, hfa_fac) == (175, 114, 17000)
print('fit.ret: HFA average %.3f (%d companies, %d US, %s facilities) -> %.2f; segments %.3f (fitness-only) - %.3f (independent, IHRSA page) '
      '-> SE %.3f (HCM .758: %.3f); One Million Strong %.3f / %.3f'
      % (hfa_ret, hfa_n, hfa_us, f'{hfa_fac:,}', fit_ret, seg['fitness_only'], seg['independent_ihrsa_page'], fit_ret_se, fit_ret_se_hcm,
         (1 - oms_rate) ** 12, oms_12))

# ================================================================ 5. flags (quotes confirmed in the downloads)
t_st, t_ro, t_sh = html_text(SERVICETITAN), html_text(ROWRITER), html_text(SHOPIFY)
t_da, t_rc, t_mc = html_text(DATTO), html_text(RCPMAG), html_text(MCW)
nbb_p18 = pdf_text(NBB_PDF, 18)
quote('servicetitan', 'repeat customers 39% of annual revenue', t_st, r'Repeat customers accounted for 39% of contractors. annual revenue')
quote('servicetitan', 'more than 1,000 residential service contractors (release of Nov. 30, 2023)', t_st,
      r'November 30, 2023.*survey responses from more than 1,000 residential service contractors')
quote('rowriter', '50% to 60% do not return the following calendar year', t_ro, r'50% to 60% of the total customers serviced will not return the following calendar year')
quote('shopify', 'Bluecore: total rate 27.4% across seven retail verticals', t_sh, r'seven retail verticals and found the total rate to be 27\.4%')
quote('shopify', 'vertical range 19.1% to 41.2%', t_sh, r'19\.1%.*41\.2%')
quote('datto', 'more than 1,600 MSPs surveyed (May 2019)', t_da, r'Surveying more than 1,600 MSPs around the globe')
quote('datto', '44% of MSPs: more than 50% of revenue recurring', t_da, r'44% of survey respondents revealed that more than 50% of their overall revenue now comes from recurring services')
quote('rcpmag', 'Kaseya: on average 33 percent from managed services', t_rc, r'on average, only 33 percent of their revenues came from managed services')
quote('rcpmag', 'Kaseya: 920 respondents', t_rc, r'920 from around the world')
quote('rcpmag', 'Kaseya: about 20 percent get half or more', t_rc, r'About 20 percent of respondents claimed to get half or more of their revenues from managed services')
quote('mcw', 'UWC 76% of wash sales (72% a year earlier)', t_mc, r'UWC sales represented 76% of total wash sales compared to 72% in the second quarter of 2024')
quote('mcw', '522 car wash locations at June 30, 2025', t_mc, r'car wash locations operated to 522 as of June 30, 2025')
quote('nbb', 'Figure 8 title on PDF p. 18', nbb_p18, r'Figure 8\. Transaction survival rate on a short-run horizon')
nber_txt = None
if PDFTOTEXT:
    full = subprocess.run([PDFTOTEXT, '-layout', NBER_PDF, '-'], capture_output=True, text=True, check=True).stdout


    def table_row(table, row):
        seg_ = full[full.index(table):]
        line = next(l for l in seg_.splitlines() if l.strip().startswith(row))
        return line.split()
    a5 = table_row('Table A5: Descriptive statistics: Prodcom sample', 'p50'); a5m = table_row('Table A5: Descriptive statistics: Prodcom sample', 'mean')
    a5n = table_row('Table A5: Descriptive statistics: Prodcom sample', 'count')
    a8 = table_row('Table A8: Descriptive statistics: growth-accounting sample', 'p50')
    nber = dict(prodcom_separation_p50=float(a5[7]), prodcom_separation_mean=float(a5m[7]), prodcom_n=int(a5n[7].replace(',', '')),
                sales_weighted_separation_p50=float(a8[7]))
    QUOTES.setdefault('nber', {})['Table A5/A8 separations column parsed'] = (nber['prodcom_separation_p50'] == 0.040 and nber['prodcom_separation_mean'] == 0.057
                                                                              and nber['prodcom_n'] == 41980 and nber['sales_weighted_separation_p50'] == 0.053)
else:
    nber = dict(prodcom_separation_p50=0.040, prodcom_separation_mean=0.057, prodcom_n=41980, sales_weighted_separation_p50=0.053)
    QUOTES.setdefault('nber', {})['Table A5/A8 separations column parsed'] = None
msp = census['msp_541513']
FLAGS = {
    'home.ret': ('ServiceTitan / Thrive Analytics survey of 1,000+ US residential contractors (2023): repeat customers are 39%% of annual revenue, so '
                 'last-year revenue retention is at most about .39 x (1 + g) = %s at g = .09, against .70; only maintenance-agreement '
                 'renewal (vendor claims .58-.80, unverified) comes near .70. Settle count versus revenue first.' % d2(0.39 * 1.09)),
    'auto.ret': ('Auto Apps shop data (via R.O. Writer; US and Canada): 50-60% of customers serviced do not return the following '
                 'calendar year, so .40-.50 by customer count, against .58.'),
    'ecom.ret': ('Repeat-purchase rates run about .20-.30 (Bluecore 2025: 27.4% across seven retail verticals, 19.1-41.2% by vertical), '
                 'against .40, which is also below the slider minimum of 45%: a typical e-commerce seller cannot enter a typical value.'),
    'msp.rec': ('MSP surveys put the median near .45-.55 (Datto 2019, 1,600+ MSPs: 44%% earn more than half of revenue from recurring services; '
                'Kaseya 2016: mean managed-services share .33, n=920, 20%% at .50 or more), against .72. Only Census NAICS 541513\'s '
                'revenue-weighted shares reach it, with hosting and IT support counted (shares of industry revenue, which large firms '
                'dominate, not establishment medians: managed infrastructure %s, with hosting and BPM %s, with IT support %s). No '
                '2024-26 distribution was opened.' % (d2(msp['managed_infra']), d2(msp['with_hosting_bpm']), d2(msp['with_it_support']))),
    'wash.rec': ('No Census membership line for car washes (NAICS 811192: automatic washing %s of revenue, no club split); Mister Car Wash '
                 'club (UWC) sales were 76%% of wash sales in Q2 2025 (72%% a year earlier). MarQ\'s market estimate puts memberships at '
                 'about %.0f%% of US car-wash revenue across formats, the only industry-wide figure and at the hand-set .35 (not '
                 'opened). Express tunnels are probably well above .35; the mix of formats among sellers is unknown.'
                 % (d2(census['wash_811192']['automatic']), 100 * MARQ['share'])),
    'land.rec': ('Census 2022 NAICS 561730: the care and maintenance lines (residential %s, exterior commercial %s and interior commercial '
                 '%s landscaping services) are %s of revenue (revenue-weighted, all establishments), against .48. An upper bound: the '
                 'lines do not record contract status, so one-off cleanups and tree work count; landscape construction is %s, snow '
                 'removal %s, grass cutting alone %s. The lines overlap across establishments, so no establishment median follows.'
                 % (d3(census['land_561730']['lines']['residential landscaping services']['share']),
                    d3(census['land_561730']['lines']['exterior commercial landscaping services']['share']),
                    d3(census['land_561730']['lines']['interior commercial landscaping services']['share']),
                    d2(census['land_561730']['care_maintenance']), d3(census['land_561730']['installation_construction']),
                    d3(census['land_561730']['snow_removal']), d3(census['land_561730']['grass_cutting_alone']))),
    'dist.ret': ('Belgian VAT data (NBB WP 444, Fig. 8): one-year survival of firm-to-firm links about %s by count and %s by value '
                 '(2010-19). .80 sits between the two readings, so the definition (customers or revenue) decides.' % (d2(NBB_FIG8['count_recent']), d2(NBB_FIG8['value_recent']))),
    'mfg.ret': ('As for dist: link survival about %s by count and %s by value (NBB WP 444, Fig. 8); Belgian manufacturers drop '
                'suppliers worth a median %.1f%% of input spending a year (mean %.1f%%, %s firm-years; Baqaee et al., NBER WP 31231, '
                'Table A5), so about %s by value. .78 is between the count and value readings.'
                % (d2(NBB_FIG8['count_recent']), d2(NBB_FIG8['value_recent']), 100 * nber['prodcom_separation_p50'], 100 * nber['prodcom_separation_mean'],
                   f"{nber['prodcom_n']:,}", d2(1 - nber['prodcom_separation_p50']))),
    'staff.rec': ('definition: temporary staffing is %.0f%% of NAICS 561320 revenue (Census 2022; permanent placement %.1f%%), billed '
                  'continuously under client contracts, so a literal "contracted" reading gives about .95; .30 implies that work '
                  'cancellable at will is not recurring. The slider needs a one-line definition before this moves.'
                  % (100 * census['staff_561320']['temp_staffing'], 100 * census['staff_561320']['perm_placement'])),
}
TESTS['flags: every quoted number found in its downloaded page or PDF text'] = all(
    v is not False for src in ('servicetitan', 'rowriter', 'shopify', 'datto', 'rcpmag', 'mcw', 'nbb', 'nber') for v in QUOTES[src].values())
TESTS['flags (revision 3): land.rec added from the Census file (.86, an upper bound, against the hand-set .48)'] = (
    'land.rec' in FLAGS and '.86 of revenue' in FLAGS['land.rec'] and 'upper bound' in FLAGS['land.rec'] and IND['land']['rec'] == 0.48)
TESTS['flags (revision 3): wash.rec names MarQ (about 35%, not opened); msp.rec\'s Census shares marked revenue-weighted'] = (
    'MarQ' in FLAGS['wash.rec'] and 'not opened' in FLAGS['wash.rec'] and 'revenue-weighted' in FLAGS['msp.rec']
    and 'not establishment medians' in FLAGS['msp.rec'])

# ================================================================ 6. ordering check (rec mention rates against IND.rec)
cur_rec = [IND[k]['rec'] for k in KEYS]; cur_ret = [IND[k]['ret'] for k in KEYS]
shp_rec = [SHIPPED_REC[k] for k in KEYS]
r_cur, p_cur = spear(M_res.rec_rate, cur_rec); r_shp, p_shp = spear(M_res.rec_rate, shp_rec)
r_ret, p_ret = spear(M_res.ret_rate, cur_ret)
r_nq, p_nq = spear(M_noql.rec_rate, cur_rec)
ordering = dict(n=len(KEYS), listings_with_description=int(L.has_desc.sum()), listings=int(len(L)),
                spearman_vs_current=r_cur, p_current=p_cur, spearman_vs_shipped=r_shp, p_shipped=p_shp,
                spearman_ret_mentions_vs_current_ret=r_ret, p_ret=p_ret,
                quietlight_nav_removed=dict(spearman_vs_current=r_nq, p=p_nq, saas_rate=float(M_noql.loc['saas', 'rec_rate']),
                                            saas_n=int(M_noql.loc['saas', 'n']), ecom_rate=float(M_noql.loc['ecom', 'rec_rate']),
                                            ecom_n=int(M_noql.loc['ecom', 'n'])),
                quietlight=dict(listings=int(L.quietlight.sum()), with_nav_text=int(L.qlnav.sum()),
                                in_saas_class_with_description=int(M_res.loc['saas', 'quietlight'])),
                rates=M_res.round(4).reset_index().to_dict(orient='records'))
MR = M_res.rename(columns=lambda c: c + '_research_logic').join(M_noql.rename(columns=lambda c: c + '_ql_nav_removed'))
MR['current_rec'] = cur_rec; MR['shipped_rec'] = shp_rec; MR['current_ret'] = cur_ret
MR.reset_index().rename(columns={'index': 'ind'}).to_csv(OUT + '/dl_mention_rates.csv', index=False)
TESTS['ordering: Spearman(rec mention rate, hand-set IND.rec) >= 0.5'] = r_cur >= 0.5
TESTS['ordering: Spearman unchanged (no rec median ships)'] = abs(r_cur - r_shp) < 1e-12
print('ordering: Spearman %.3f (p %.4f) vs current, %.3f vs shipped; ret %.3f; Quiet Light menu removed %.3f (saas rate %.3f -> %.3f)'
      % (r_cur, p_cur, r_shp, r_ret, r_nq, M_res.loc['saas', 'rec_rate'], M_noql.loc['saas', 'rec_rate']))

# ================================================================ 7. spread checks (z-scales; record only)
gdc = grouped(KBCM_GDC['bins']); logo = grouped(KBCM_LOGO['bins'])
# revision 3: a two-point mixture (non-reporters at 0, reporters at their mean share) ignores the spread among reporters, so
# its SD is a LOWER BOUND on the within-industry SD; these rows are kept apart from the ordinary SDs
LB = 'lower bound (two-point mixture: ignores the spread among reporters)'
SPREAD = [
    ('rec', 'fit: Census 713940 memberships, two-point mixture', census['sd_two_point']['fit_713940_memberships'], 'establishments', LB),
    ('rec', 'msp: Census 541513 managed infrastructure, two-point', census['sd_two_point']['msp_541513_managed_infrastructure'], 'establishments', LB),
    ('rec', 'msp: Census 541519 IT support, two-point', census['sd_two_point']['msp_541519_it_support'], 'establishments', LB),
    ('rec', 'staff: Census 561320 temporary staffing, two-point', census['sd_two_point']['staff_561320_temporary_staffing'], 'establishments', LB),
    ('rec', 'vet: Census 541940 routine exams, two-point', census['sd_two_point']['vet_541940_routine_exams'], 'establishments', LB),
    ('rec', 'saas: Empire Flippers MRR share (n=%d)' % ef['n'], ef['sd'], 'sold-business listings', 'sd'),
    ('rec', 'saas: KBCM attach-implied subscription share (n=152)', kbcm_check['subscription_share_sd_bin_midpoints'], '$5M+ ARR firms', 'sd (bin midpoints, >50% bin at 75%)'),
    ('rec', 'saas: DealLedger stated (n=%d)' % dl['saas']['n'], dl['saas']['sd'], 'listings, selected', 'sd'),
    ('rec', 'fit: DealLedger stated (n=%d)' % dl['fit']['n'], dl['fit']['sd'], 'listings, selected', 'sd'),
    ('rec', 'land: DealLedger stated (n=%d)' % dl['land']['n'], dl['land']['sd'], 'listings, selected', 'sd'),
    ('rec', 'msp: Kaseya 2016, normal through mean .33 and 20% at .50+ (n=920)', (0.50 - 0.33) / stats.norm.ppf(0.80), 'MSPs worldwide', 'normal-implied sd'),
    ('ret', 'saas: KBCM gross dollar churn (n=173)', gdc['sd_midpoints'], '$5M+ ARR firms', 'sd (bin midpoints)'),
    ('ret', 'saas: KBCM gross dollar churn, IQR-based', gdc['iqr_sd'], '$5M+ ARR firms', 'IQR/1.349'),
    ('ret', 'saas: KBCM logo churn (n=166)', logo['sd_midpoints'], '$5M+ ARR firms', 'sd (bin midpoints)'),
    ('ret', 'saas: KBCM logo churn, IQR-based', logo['iqr_sd'], '$5M+ ARR firms', 'IQR/1.349'),
    ('ret', 'land: L&L 2026 histogram (n=320)', g26['sd_uniform'], 'landscapers', 'sd (uniform within bands)'),
    ('ret', 'land: L&L 2026 histogram, IQR-based', g26['iqr_sd'], 'landscapers', 'IQR/1.349'),
    ('ret', 'land: L&L 2025 mean .88 / median .93, lognormal churn (n=433)', ll25_sd, 'landscapers', 'model-implied sd'),
    ('ret', 'saas: Empire Flippers (1 - monthly churn)^12 (n=%d)' % ef['retention_from_monthly_churn']['n'], ef['retention_from_monthly_churn']['sd'], 'micro SaaS listings', 'sd'),
]
SP = pd.DataFrame(SPREAD, columns=['scale', 'source', 'sd', 'population', 'kind'])
SP['lower_bound'] = SP.kind == LB
SP.to_csv(OUT + '/spread_checks.csv', index=False)
SP_REC_SD, SP_REC_LB = SP[(SP.scale == 'rec') & ~SP.lower_bound], SP[(SP.scale == 'rec') & SP.lower_bound]
rng_rec = [float(SP_REC_SD.sd.min()), float(SP_REC_SD.sd.max())]                 # ordinary SDs of the recurring share
rng_rec_lb = [float(SP_REC_LB.sd.min()), float(SP_REC_LB.sd.max())]              # two-point lower bounds
fit_lb = census['sd_two_point']['fit_713940_memberships']
rng_ret = [float(SP[SP.scale == 'ret'].sd.min()), float(SP[SP.scale == 'ret'].sd.max())]
TESTS['z-scale rec: the five two-point mixture SDs are labelled lower bounds and kept apart from the ordinary SDs'] = (
    len(SP_REC_LB) == 5 and SP_REC_LB.source.str.contains('two-point').all() and not SP_REC_SD.source.str.contains('two-point').any())
TESTS['z-scale rec: fitness\'s lower bound exceeds the kept .28, as the js_table states (so .28 is not called inside the spreads)'] = fit_lb > Z_REC
TESTS['z-scale: .13 inside the measured within-industry SDs of retention'] = rng_ret[0] <= Z_RET <= rng_ret[1]
print('spreads: rec ordinary SDs %.3f-%.3f, two-point lower bounds %.3f-%.3f (fitness %.3f > kept %.2f); ret %.3f-%.3f (kept %.2f)'
      % (rng_rec[0], rng_rec[1], rng_rec_lb[0], rng_rec_lb[1], fit_lb, Z_REC, rng_ret[0], rng_ret[1], Z_RET))

# ================================================================ 8. materiality through the harness (node)
fit_rec_central_v = rnd(fitrec_check['central']['median_beta'], 2)
saas_clean_v = rnd(clean_pool['value'], 2)
MOVES = [('land.ret (shipped)', 'land', [['ret', float(LAND_RET)]]), ('fit.ret (shipped)', 'fit', [['ret', fit_ret]]),
         ('land.ret at round 1\'s .90 (not shipped)', 'land', [['ret', 0.90]]), ('land.ret at the 2025 median .93 (not shipped)', 'land', [['ret', LL25['median']]]),
         ('fit.rec at the check\'s central median %s (not shipped)' % d2(fit_rec_central_v), 'fit', [['rec', fit_rec_central_v]]),
         ('fit.rec at round 1\'s .66 (not shipped)', 'fit', [['rec', rnd(fit_rec, 2)]]),
         ('saas.rec at the cleaned pool %s (not shipped)' % d2(saas_clean_v), 'saas', [['rec', saas_clean_v]])]
MAT_JS = r"""
const H=require(%s);const fs=require('fs');const SNAP=fs.readFileSync(H.SNAP,'utf8');const A=H.load();
const spec=JSON.parse(process.argv[process.argv.length-1]);
function biz(API,ind,ern){const I=API.IND[ind],RF=API.sizeRefs(ern),rev=ern/API.typMargin(ind,ern);
 return {ind,ern,rev,ask:3*ern,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,
  grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40,budget:1e5,lamT:900,theta:.75};}
function ov(ind,moves){const m=SNAP.match(new RegExp(ind+':\\s*\\{[^}]*\\}'));if(!m)throw new Error('no IND row '+ind);
 let row=m[0];for(const [f,v] of moves){const re=new RegExp('(\\b'+f+':)([-.0-9]+)');if(!re.test(row))throw new Error('no field');
 row=row.replace(re,'$1'+String(v));}return [m[0],row];}
const out=[];for(const g of spec.groups){const s=biz(A,g.ind,spec.ern);const b=A.model(s);const B=H.load([ov(g.ind,g.moves)]);
 const a=B.model(s);const r={label:g.label,ind:g.ind,value_before:b.V,value_after:a.V,pct:a.V/b.V-1,z_after:{},peer_after:{}};
 for(const [f] of g.moves){r.z_after[f]=a.z[f];r.peer_after[f]=B.IND[g.ind][f];}out.push(r);}
process.stdout.write(JSON.stringify(out));
""" % json.dumps(HARNESS)
NODE = shutil.which('node')
if NODE and os.path.exists(HARNESS):
    spec = json.dumps(dict(ern=SDE_REF, groups=[dict(label=a, ind=b, moves=c) for a, b, c in MOVES]))
    mat = json.loads(subprocess.run([NODE, '-e', MAT_JS, spec], capture_output=True, text=True, check=True).stdout)
    for r in mat:
        r['pct'] = rnd(r['pct'], 4); r['value_before'] = round(r['value_before']); r['value_after'] = round(r['value_after'])
        r['z_after'] = {k: rnd(v, 3) for k, v in r['z_after'].items()}
    materiality = dict(sde=SDE_REF, note="value of a business that enters today's hand-set peer medians, before and after the move", rows=mat)
    signs = {r['label']: r['pct'] for r in mat}
    TESTS['materiality: each shipped move lowers the value of a business at the old median (both medians rise)'] = (
        signs['land.ret (shipped)'] < 0 and signs['fit.ret (shipped)'] < 0)
    TESTS['materiality: the moved peer medians are the values requested'] = all(abs(r['peer_after'][f] - v) < 1e-12 for r, (_, _, mv) in zip(mat, MOVES) for f, v in mv)
    print('materiality at $708k SDE: ' + '; '.join('%s %+.1f%%' % (r['label'], 100 * r['pct']) for r in mat))
else:
    materiality = dict(skipped='node or the harness is not available')

# ================================================================ 9. the shipped table, tests and output
fit_rec_v, fit_rec_se_v = rnd(fit_rec, 2), rnd(fit_rec_se, 3)
for k, v in (('land.ret', float(LAND_RET)), ('fit.ret', fit_ret)):
    TESTS['slider: %s inside the ret slider %s' % (k, SLIDER['ret'])] = SLIDER['ret'][0] <= v <= SLIDER['ret'][1]
TESTS['decision: fit.ret rounds to 0.66 (HFA 66.4%) and its range/4 SE to 0.037 (0.044 with HCM\'s .758)'] = (
    fit_ret == 0.66 and fit_ret_se == 0.037 and fit_ret_se_hcm == 0.044)
TESTS['reproduces round 1: Census membership share 0.66 (CV-based SE 0.006), saas pool as decided then 0.90'] = (
    fit_rec_v == 0.66 and fit_rec_se_v == 0.006 and rnd(pool, 2) == 0.90)
TESTS['reproduces round 1: the cleaned saas pool .892 (SE .056)'] = rnd(clean_pool['value'], 3) == 0.892 and rnd(clean_pool['se'], 3) == 0.056
TESTS['reproduces the research: EF n=29 median .894, DealLedger n=11 median .90, fitness stated n=16 median .80'] = (
    ef['n'] == 29 and abs(ef['median'] - 0.894) < 0.0005 and dl['saas']['n'] == 11 and dl['saas']['median'] == 0.90
    and dl['fit']['n'] == 16 and dl['fit']['median'] == 0.80)
if os.path.exists(RESEARCH_DL_HITS):
    RH = pd.read_csv(RESEARCH_DL_HITS)
    RH = RH[RH.kind == 'rec']
    TESTS['reproduces the research: DealLedger rec statements (key, value, industry) identical to dl2_hits.csv'] = (
        sorted(zip(RH.key, RH.val, RH.ind)) == sorted(zip(H.key, H.val, H.ind)))
TESTS['every PDF and page quote found (None = pdftotext missing)'] = all(v is not False for src, d in QUOTES.items() for lab, v in d.items()
                                                                       if 'expected false' not in lab)

fc = fitrec_check
not_shipped_js = {
    'fit.rec': {'v': KEPT['fit.rec'], 'judgment': True,
                'census_revenue_weighted': {'v': fit_rec_v, 'se': fit_rec_se_v},
                'establishments': census['establishments'], 'reporting': census['establishments_reporting'],
                'reporters_line_pct': census['line_pct_among_reporters'],
                'median_central': rnd(fc['central']['median_beta'], 3), 'median_central_logitnormal': rnd(fc['central']['median_logitnormal'], 3),
                'median_range': [rnd(fc['range_all'][0], 3), rnd(fc['range_all'][1], 3)],
                'median_by_mu_e': {k: [rnd(a, 3), rnd(b, 3)] for k, (a, b) in fc['by_mu'].items()},
                'mu_e_for_kept': rnd(fc['mu_e_that_gives_kept_at_central_sd'], 3),
                'dealledger_stated': {'median': dl['fit']['median'], 'n': dl['fit']['n']},
                'note': ('establishment-level median implied by the Census line: %.1f%% of taxable NAICS 713940 establishments report no '
                         'membership revenue (at zero), reporters get %.0f%% of revenue from memberships, so the median establishment is '
                         'the reporters\' %.3f quantile. Under Beta or logit-normal shares among reporters with establishment mean '
                         '.80-.90 and SD .05-.25 it runs %s-%s (%s-%s at mean .86, %s-%s at mean .80); central (mean .86, SD %s from '
                         'the DealLedger fitness statements) %s. .70 stays (judgment): it needs a reporters\' establishment mean of '
                         'about %s.'
                         % (100 * fc['census']['share_at_zero'], 100 * census['line_pct_among_reporters'], fc['census']['median_is_reporters_quantile'],
                            d2(fc['range_all'][0]), d2(fc['range_all'][1]), d2(fc['by_mu']['0.86'][0]), d2(fc['by_mu']['0.86'][1]),
                            d2(fc['by_mu']['0.8'][0]), d2(fc['by_mu']['0.8'][1]), d2(sd_central), d2(fc['central']['median_beta']),
                            d2(fc['mu_e_that_gives_kept_at_central_sd'])))},
    'saas.rec': {'v': KEPT['saas.rec'], 'judgment': True,
                 'cleaned_pool': {'v': rnd(clean_pool['value'], 3), 'se': rnd(clean_pool['se'], 3),
                                  'parts': {'ef_saas_primary': {'v': rnd(ef['subsets']['saas_primary']['median'], 3),
                                                                'se': rnd(ef['subsets']['saas_primary']['se'], 3), 'n': ef['subsets']['saas_primary']['n']},
                                            'dl_software': {'v': rnd(dl['saas_software_only']['median'], 3), 'se': rnd(dl['saas']['se'], 3),
                                                            'n': dl['saas_software_only']['n']}}},
                 'z_vs_kept': rnd(saas_z, 2), 'round1_pool': {'v': rnd(pool, 3), 'se': rnd(pool_se, 3)},
                 'check_kbcm': rnd(kbcm_check['subscription_share_at_median_attach'], 2),
                 'note': ('cleaned pool %s (SE %s) = Empire Flippers SaaS-primary listings (MRR x 12 / trailing revenue, median %s, n=%d) '
                          'with the %d DealLedger statements from software businesses (median %s, carrying the n=11 SE); %s SE from .85, '
                          'inside the noise. The ratio exceeds 1 for %d of the %d EF listings (growth, capped at 1); KBCM (%s) is a '
                          'bookings mix of $5M+ ARR firms; the 11 DealLedger statements include 7 that are not software. .85 stays.'
                          % (d3(clean_pool['value']), d3(clean_pool['se']), d3(ef['subsets']['saas_primary']['median']),
                             ef['subsets']['saas_primary']['n'], dl['saas_software_only']['n'], d3(dl['saas_software_only']['median']),
                             '%.2f' % saas_z, ef['n_capped'], ef['n'], d2(kbcm_check['subscription_share_at_median_attach'])))},
}
js_table = {
    'rec': {},
    'ret': {
        'land': {'v': float(LAND_RET), 'se': float(LAND_RET_SE), 'was': IND['land']['ret'], 'tier': 'aggregate',
                 'parts': {'2025': {'mean': LL25['mean'], 'median': LL25['median'], 'n': LL25['n']},
                           '2026': {'mean': LL26['mean'], 'median_grouped': rnd(g26['median'], 3), 'n': LL26['n']}},
                 'source': 'Lawn & Landscape, Benchmarking Your Business 2025 and 2026 (landscapers and lawn-care operators, US and '
                           'Canada): "Of your location\'s customers 12 months ago, what percentage are still customers today?"',
                 'note': '%s = the survey means; a judgment shade below the survey medians (%s / %s) for self-selected US and Canadian '
                         'respondents; the size of the shade is not measured'
                         % (d2(float(LAND_RET)), d2(LL25['median']), d2(g26['median'])),
                 'se_note': 'SE .04 is judgment (it carries the unmeasured selection); the sampling SE of the mean is about %s. The '
                            'mean-median gap is the left skew of the answers: the 2026 histogram gives mean %s and median %s; the '
                            'n-weighted mean of the two survey means is %s'
                            % (d3(land['sampling_se_of_mean_2026']), d3(g26['mean']), d3(g26['median']), d3(land_wmean))},
        'fit': {'v': fit_ret, 'se': fit_ret_se, 'range': [float(FIT_RET_RANGE[0]), float(FIT_RET_RANGE[1])], 'was': IND['fit']['ret'],
                'tier': 'aggregate',
                'source': 'Health & Fitness Association 2025 Fitness Industry Benchmarking Report: member retention averaged %.1f%% in '
                          '2024, an average across %d companies (%d US), mostly multi-club operators (more than %s facilities)'
                          % (100 * hfa_ret, hfa_n, hfa_us, f'{hfa_fac:,}'),
                'note': 'range = IHRSA 2018 segments, fitness-only clubs %s (Health Club Management) to independent clubs %s (IHRSA\'s '
                        'own page); Health Club Management gives independent clubs %s, which would make the SE %s; se = range/4 = %s. '
                        'Check: IHRSA One Million Strong, 33.6 cancellations per 1,000 members a month = %s a year'
                        % (d3(seg['fitness_only']), d3(seg['independent_ihrsa_page']), d3(seg['independent']), d3(fit_ret_se_hcm),
                           d3(fit_ret_se), d2((1 - oms_rate) ** 12))},
    },
    'not_shipped': not_shipped_js,
    'flags': FLAGS,
    'ordering_check': {'spearman_rec_vs_mentions': rnd(r_cur, 2), 'p': rnd(p_cur, 3), 'n': len(KEYS),
                       'spearman_ret_vs_mentions': rnd(r_ret, 2),
                       'spearman_quietlight_menu_removed': rnd(r_nq, 2),
                       'mention_rate': {k: rnd(M_res.loc[k, 'rec_rate'], 3) for k in KEYS},
                       'note': 'share of DealLedger listings (%s with descriptions) mentioning recurring, subscription, membership, '
                               'maintenance-agreement, retainer or contract terms; ordering only, not a level. Out of line with the '
                               'hand-set rec: %s' % (f"{int(L.has_desc.sum()):,}", ', '.join('%s (%s against %s)' % (k, d3(M_res.loc[k, 'rec_rate']), d2(IND[k]['rec']))
                                                                  for k in ('wash', 'prof', 'dist')))},
    'spread_checks': {
        'rec': {'kept': Z_REC,
                'sd': {'saas_ef': rnd(ef['sd'], 2), 'saas_kbcm_attach': rnd(kbcm_check['subscription_share_sd_bin_midpoints'], 2),
                       'saas_dl_stated': rnd(dl['saas']['sd'], 2), 'fit_dl_stated': rnd(dl['fit']['sd'], 2),
                       'land_dl_stated': rnd(dl['land']['sd'], 2), 'msp_kaseya_normal': rnd((0.50 - 0.33) / stats.norm.ppf(0.80), 2)},
                'sd_range': [rnd(rng_rec[0], 2), rnd(rng_rec[1], 2)],
                'lower_bounds': {'fit_census_two_point': rnd(census['sd_two_point']['fit_713940_memberships'], 2),
                                 'msp_census_541513_two_point': rnd(census['sd_two_point']['msp_541513_managed_infrastructure'], 2),
                                 'msp_census_541519_two_point': rnd(census['sd_two_point']['msp_541519_it_support'], 2),
                                 'staff_census_561320_two_point': rnd(census['sd_two_point']['staff_561320_temporary_staffing'], 2),
                                 'vet_census_541940_two_point': rnd(census['sd_two_point']['vet_541940_routine_exams'], 2)},
                'lower_bound_range': [rnd(rng_rec_lb[0], 2), rnd(rng_rec_lb[1], 2)],
                'note': ('lower_bounds are Census two-point mixtures (non-reporters at 0, reporters at their mean share): they ignore '
                         'the spread among reporters, so each is a LOWER BOUND on that industry\'s SD. Fitness\'s lower bound (%s) '
                         'already exceeds the kept %s; the ordinary SDs (%s-%s) come from SaaS listings and stated shares and sit '
                         'below it' % (d2(fit_lb), d2(Z_REC), d2(rng_rec[0]), d2(rng_rec[1])))},
        'ret': {'kept': Z_RET, 'range': [rnd(rng_ret[0], 2), rnd(rng_ret[1], 2)],
                'sd': {'saas_kbcm_gross_dollar': rnd(gdc['sd_midpoints'], 3), 'saas_kbcm_gross_dollar_iqr': rnd(gdc['iqr_sd'], 3),
                       'saas_kbcm_logo': rnd(logo['sd_midpoints'], 3), 'land_ll2026_hist': rnd(g26['sd_uniform'], 3),
                       'land_ll2026_hist_iqr': rnd(g26['iqr_sd'], 3), 'land_ll2025_lognormal': rnd(ll25_sd, 3),
                       'saas_ef_micro': rnd(ef['retention_from_monthly_churn']['sd'], 3)}},
        'note': ('record only: both scales are kept (judgment). Retention\'s measured SDs (%s-%s) bracket %s. For the recurring share '
                 'no single scale fits: the ordinary SDs (%s-%s) are below %s and fitness\'s lower bound (%s) is above it. The data '
                 'argue for industry-specific (SaaS about .10, MSP and fitness .30-.40) or logit-scale rec spreads.'
                 % (d3(rng_ret[0]), d3(rng_ret[1]), d2(Z_RET), d2(rng_rec[0]), d2(rng_rec[1]), d2(Z_REC), d2(fit_lb)))},
    'source': 'Lawn & Landscape Benchmarking Your Business 2025 and 2026; Health & Fitness Association 2025 Fitness Industry '
              'Benchmarking Report; IHRSA 2019 Profiles of Success and One Million Strong. Checks (not shipped): Census 2022 Economic '
              'Census product lines (EC2200NAPCSINDPRD), Empire Flippers listings, DealLedger broker listings (CC0), 2021 KBCM Private '
              'SaaS Company Survey. fit/peer_recurring_retention.py (revision 3), %s' % ASOF,
    'method': 'land.ret: the analyst\'s .88 = the 2025 and 2026 survey means (n-weighted %s), a judgment shade below the medians; SE .04 '
              '(judgment) for self-selected respondents. fit.ret: HFA average across 175 companies; SE = IHRSA segment range/4 '
              '(fitness-only .584 to independent .732). Values rounded half up to 0.01, SEs to 0.001. rec ships nothing: fit.rec (.70) '
              'and saas.rec (.85) stay judgment with their checks in not_shipped; the other 28 rec/ret medians stay judgment; the '
              'flags give the data that disagree with nine of them.' % d3(land_wmean),
}
js_line = 'MODELS.fitted.%s=%s;' % (JS_KEY, json.dumps(js_table, separators=(',', ':'), ensure_ascii=False))
open(OUT + '/js_line.txt', 'w', encoding='utf-8').write(js_line + '\n')
TESTS['js_table: rec is empty; ret holds exactly land and fit'] = js_table['rec'] == {} and sorted(js_table['ret']) == ['fit', 'land']
TESTS['js_line parses back to the js_table'] = json.loads(js_line[len('MODELS.fitted.%s=' % JS_KEY):-1]) == json.loads(json.dumps(js_table))

shipped = {
    'land.ret': dict(value=float(LAND_RET), se=float(LAND_RET_SE), current=IND['land']['ret'], change=rnd(float(LAND_RET) - IND['land']['ret'], 2),
                     tier='aggregate', unrounded=land_wmean, n='433 (2025) and 320 (2026) respondents',
                     basis='analyst decision: the two survey means (n-weighted %.4f); SE .04 for self-selection' % land_wmean),
    'fit.ret': dict(value=fit_ret, se=fit_ret_se, current=IND['fit']['ret'], change=rnd(fit_ret - IND['fit']['ret'], 2), tier='aggregate',
                    unrounded=hfa_ret, range=[float(FIT_RET_RANGE[0]), float(FIT_RET_RANGE[1])], n='%d companies (%d US)' % (hfa_n, hfa_us),
                    statistic='average across companies, mostly multi-club operators', se_revision2=fit_ret_se_hcm,
                    basis='SE = (.732 - .584)/4 with IHRSA\'s own independent-club figure; Health Club Management\'s .758 gives %.3f' % fit_ret_se_hcm),
}
not_shipped = {
    'fit.rec': dict(fitrec_check, census_line=dict(share=fit_rec, se=fit_rec_se, cv_pct=census['cv_pct'],
                                                   share_all_establishments=census['share_all_establishments'],
                                                   share_tax_exempt=census['share_tax_exempt'],
                                                   personal_training=dict(share=census['personal_training'],
                                                                          establishments=census['personal_training_establishments'],
                                                                          line_pct_among_reporters=census['personal_training_line_pct']),
                                                   admissions=dict(share=census['admissions'], establishments=census['admissions_establishments']),
                                                   skating_rinks=census['skating_rinks'], all_other_recreation=census['all_other_recreation']),
                    why='stays judgment (analyst): the Census .66 is a revenue-weighted aggregate, not a peer median; the establishment-level '
                        'median depends on an unmeasured distribution among reporters'),
    'saas.rec': dict(saas_check, why='stays judgment (analyst): the cleaned pool is within one SE of .85 and its definitions are loosely '
                                     'matched (an MRR ratio that mixes growth with share; a bookings mix of large firms)'),
    'other_28': dict(flags=FLAGS, why='no source measures these medians on the console\'s definitions and population; nine carry flags',
                     land_rec_census=census['land_561730'], wash_rec_marq=MARQ),
}
est_rows = [dict(param=k, value=v['value'], se=v['se'], current=v['current'], tier=v['tier'], n=v['n']) for k, v in shipped.items()]
est_rows += [dict(param='fit.rec (judgment, kept)', value=KEPT['fit.rec'], se=None, current=IND['fit']['rec'], tier='judgment',
                  n='check: establishment median %.3f (central), %.3f-%.3f (grid)' % (fc['central']['median_beta'], fc['range_all'][0], fc['range_all'][1])),
             dict(param='saas.rec (judgment, kept)', value=KEPT['saas.rec'], se=None, current=IND['saas']['rec'], tier='judgment',
                  n='check: cleaned pool %.3f (SE %.3f)' % (clean_pool['value'], clean_pool['se']))]
est_rows += [dict(param='saas.rec alt: ' + k, value=rnd(v['value'], 3), se=rnd(v['se'], 3), current=IND['saas']['rec'], tier='sensitivity', n='')
             for k, v in sens.items()]
est_rows += [dict(param='saas.rec EF subset: ' + k, value=rnd(v['median'], 3), se=rnd(v['se'], 3) if v.get('se') else None,
                  current=IND['saas']['rec'], tier='sensitivity', n=v['n']) for k, v in ef['subsets'].items()]
pd.DataFrame(est_rows).to_csv(OUT + '/estimates.csv', index=False)

# sources with hashes and sample sizes
snap_digest = hashlib.sha256('\n'.join('%s %s' % (p.split('/')[-2], sha256_file(p)) for p in snap_files).encode()).hexdigest()
N_BY_SRC = {'census': '%d taxable establishments in NAICS 713940 (%d in 561730, all establishments); %d rows in the .dat' % (
                census['establishments'], census['land_561730']['establishments'], census['dat_rows']),
            'ef': '%d listings with MRR (subscription, SaaS, app, agency, service)' % ef['n'], 'ef_monthly': 'last 3 months per listing',
            'dl': '%d snapshot files, %d unique listings, %d with descriptions; %d saas statements' % (len(snap_files), len(L), int(L.has_desc.sum()), dl['saas']['n']),
            'll25': '433 respondents', 'll26': '320 respondents', 'hfa_report': '175 companies (114 US)', 'hfa_release': '175 companies',
            'ihrsa_pos': '98 firms, 10,859 clubs', 'hcm_numbers': 'IHRSA IDS 2019', 'hcm_oms': 'about 1.5 million members',
            'kbcm': '173 / 166 / 152 respondents', 'servicetitan': '1,000+ contractors', 'rowriter': 'shop analyses (US and Canada)',
            'shopify': 'Bluecore, seven retail verticals', 'datto': 'more than 1,600 MSPs', 'rcpmag': '920 respondents',
            'mcw': '522 locations at June 30, 2025 (the research report said 548)',
            'nbb': 'all Belgian domestic B2B links', 'nber': '41,980 firm-years (Prodcom)'}
sources = []
for s in SOURCES:
    d = dict(s)
    if s['key'] == 'dl':
        d['sha256'] = snap_digest[:16]; d['sha256_note'] = 'sha256 of the sorted list of per-file sha256s'
    else:
        d['sha256'] = sha256_file(s['file'])[:16]
    if s['key'] == 'census':
        d['dat_member_sha256'] = census['dat_member_sha256'][:16]
    d['n'] = N_BY_SRC[s['key']]
    sources.append(d)

diff = {'fit.rec': [RESEARCH['fit.rec'], rnd(fit_rec, 4)], 'fit.rec_se': [RESEARCH['fit.rec_se'], rnd(fit_rec_se, 4)],
        'ef_median': [RESEARCH['ef_median'], rnd(ef['median'], 4)], 'ef_se': [RESEARCH['ef_se'], rnd(ef['se'], 4)],
        'dl_median': [RESEARCH['dl_median'], rnd(dl['saas']['median'], 4)], 'dl_se': [RESEARCH['dl_se'], rnd(dl['saas']['se'], 4)],
        'spearman_rec_mentions': [RESEARCH['spearman_rec_mentions'], rnd(r_cur, 3)], 'spearman_ret_mentions': [RESEARCH['spearman_ret_mentions'], rnd(r_ret, 3)],
        'saas_mention_rate': [RESEARCH['saas_mention_rate'], rnd(M_res.loc['saas', 'rec_rate'], 3)],
        'fit_dl_median': [RESEARCH['fit_dl_median'], dl['fit']['median']], 'ef_ret_median': [RESEARCH['ef_ret_median'], rnd(ef['retention_from_monthly_churn']['median'], 4)],
        'kbcm_gdc_sd': [RESEARCH['kbcm_gdc_sd'], rnd(gdc['sd_midpoints'], 4)], 'kbcm_gdc_iqr_sd': [RESEARCH['kbcm_gdc_iqr_sd'], rnd(gdc['iqr_sd'], 4)],
        'kbcm_attach_implied_saas_sd (research about .08)': [0.08, rnd(kbcm_check['subscription_share_sd_bin_midpoints'], 3)]}

sw_pool4 = sens['EF saas-primary + DL software-only (their own n=4 bootstrap SE)']
mat_rows = {r['label']: r for r in materiality.get('rows', [])}
mat_txt = lambda lab: ('%+.1f%%' % (100 * mat_rows[lab]['pct'])) if lab in mat_rows else 'n/a'
fc_lab = 'fit.rec at the check\'s central median %s (not shipped)' % d2(fit_rec_central_v)
OPEN += [
    'fit.rec (kept .70 as judgment, as decided; the check leans higher). The Census line read at the establishment level puts the '
    'median at the reporters\' %.3f quantile (%.1f%% of establishments at zero). With the reporters\' establishment mean equal to '
    'the revenue-weighted .86 and their SD %.3f (the 16 DealLedger fitness statements), the median is %.3f (Beta) or %.3f '
    '(logit-normal); over the whole stated grid (mean .80-.90, SD .05-.25) it runs %.3f-%.3f, and %.0f%% of the grid cells sit at or '
    'above .70. The kept .70 needs a reporters\' establishment mean of about %.3f, i.e. the typical reporting studio relying on '
    'memberships %.0f points less than the revenue-weighted figure. With the 1,093 skating-rink establishments out of the base the central median '
    'is %.3f. DealLedger fitness listings that state a share give %.2f (n=%d, selected upward). Not changed; if the analyst wants the '
    'check\'s central value, .79 would move a fitness business at the old median by %s at $708k SDE.'
    % (fc['census']['median_is_reporters_quantile'], 100 * fc['census']['share_at_zero'], sd_central, fc['central']['median_beta'],
       fc['central']['median_logitnormal'], fc['range_all'][0], fc['range_all'][1], 100 * fc['share_of_cells_at_or_above_kept'],
       fc['mu_e_that_gives_kept_at_central_sd'], 100 * (FITREC_MU_CENTRAL - fc['mu_e_that_gives_kept_at_central_sd']), fr_central_nr,
       dl['fit']['median'], dl['fit']['n'], mat_txt(fc_lab)),
    'saas.rec (kept .85 as judgment): the cleaned pool is %.3f (SE %.3f), %.2f SE above .85, so the move is inside the noise. EF '
    'SaaS-primary alone gives %.3f (n=%d); the 4 DealLedger software statements %.3f (n=4; their own bootstrap SE %.3f is not credible, '
    'so the n=11 SE %.3f is carried); round 1\'s pool as decided then was %.3f (SE %.3f). Of the 11 DealLedger statements classified '
    'saas, 7 are not software (%s); %d of the 11 are Quiet Light listings whose site menu matched the classifier.'
    % (clean_pool['value'], clean_pool['se'], saas_z, ef['subsets']['saas_primary']['median'], ef['subsets']['saas_primary']['n'],
       dl['saas_software_only']['median'], dl['saas_software_only']['se'], dl['saas']['se'], pool, pool_se,
       '; '.join(dl['saas_review']['not_software']), dl['saas_review']['from_quietlight']),
    'land.ret ships .88, the survey means, against a console field described as a peer median. The medians are .93 (2025) and %.3f '
    '(2026 histogram), %.1f and %.1f SE above .88. Shipping the mean is a judgment shade below the medians for self-selected US and '
    'Canadian respondents (median revenue about $920k, 15%% at $7M or more); the size of the shade is not measured: the mean-median '
    'gap is the left skew of the answers, which the 2026 histogram reproduces (mean %.3f, median %.3f). The simple average of the two '
    'means is .885, which would round half up to .89; the n-weighted mean %.4f rounds to .88 (immaterial against SE .04). Value '
    'effect for a landscaping business at the old median ($708k SDE): %s (round 1\'s .90: %s; the median .93: %s).'
    % (g26['median'], land['median_gap_in_se']['y2025'], land['median_gap_in_se']['y2026_grouped'], g26['mean'], g26['median'], land_wmean,
       mat_txt('land.ret (shipped)'), mat_txt('land.ret at round 1\'s .90 (not shipped)'), mat_txt('land.ret at the 2025 median .93 (not shipped)')),
    'fit.ret (revision 3): HFA\'s 66.4%% is an average ("member retention averaged 66.4%%") across 175 companies in 27 countries '
    '(%d outside the US) running more than %s facilities, so mostly multi-club operators, not a US small-studio median; the US-only '
    'figure is in the gated report. The SE now uses IHRSA\'s own independent-club figure, %.3f, against fitness-only clubs %.3f: '
    'SE %.3f (revision 2 used Health Club Management\'s %.3f for the same segment, SE %.3f; chains %.3f in both). Value effect at '
    '$708k SDE: %s.'
    % (hfa_n - hfa_us, f'{hfa_fac:,}', seg['independent_ihrsa_page'], seg['fitness_only'], fit_ret_se, seg['independent'], fit_ret_se_hcm,
       seg['chain'], mat_txt('fit.ret (shipped)')),
    'Ordering check: Quiet Light\'s menu also sets the mention flag (\'membership\') and puts most Quiet Light listings in saas: '
    'the saas mention rate is %.3f with it and %.3f without (%d listings move, mostly to ecom). The Spearman is %.3f either way.'
    % (M_res.loc['saas', 'rec_rate'], M_noql.loc['saas', 'rec_rate'], int(M_res.loc['saas', 'n']) - int(M_noql.loc['saas', 'n']), r_cur),
    'Research details corrected in the flags (no shipped value depends on them): Mister Car Wash operated 522 locations at June 30, '
    '2025 (the report said 548); the ServiceTitan release is dated Nov. 30, 2023 and its 39%% is for that year (the report said 2022 '
    'data); .39 x 1.09 = .425, which rounds to .43 (the report wrote .42).' % (),
    'z-scales (kept as judgment). The research\'s KBCM-implied SaaS spread of about .08 is %.3f here (bin midpoints, the >50%% attach '
    'bin closed at 100%%). Retention spreads run %.3f-%.3f and bracket .13. For the recurring share the ordinary SDs run %.2f-%.2f, all '
    'below .28, while the Census two-point mixtures are lower bounds (%.2f-%.2f) and fitness\'s (%.2f) already exceeds .28: one scale '
    'cannot serve both, so .28 is not inside the measured spreads for fitness (revision 2 pooled the two kinds into one range and '
    'said it was). Industry-specific or logit-scale rec spreads would follow the data better.'
    % (kbcm_check['subscription_share_sd_bin_midpoints'], rng_ret[0], rng_ret[1], rng_rec[0], rng_rec[1], rng_rec_lb[0], rng_rec_lb[1], fit_lb),
    'Flags added or sharpened in revision 3 (no value moves): land.rec, Census 561730\'s care and maintenance lines are %.3f of revenue, '
    'an upper bound for the recurring share against the hand-set .48 (residential %.3f of revenue, reported by %.0f%% of establishments '
    'at %.0f%% of their revenue; exterior commercial %.3f, %.0f%% at %.0f%%); wash.rec names MarQ\'s estimate (about %.0f%% of US car-wash '
    'revenue from memberships across formats, at the hand-set .35; not opened); msp.rec\'s Census figures are marked revenue-weighted.'
    % (census['land_561730']['care_maintenance'], census['land_561730']['lines']['residential landscaping services']['share'],
       100 * census['land_561730']['lines']['residential landscaping services']['estab_pct_reporting'],
       100 * census['land_561730']['lines']['residential landscaping services']['line_pct_among_reporters'],
       census['land_561730']['lines']['exterior commercial landscaping services']['share'],
       100 * census['land_561730']['lines']['exterior commercial landscaping services']['estab_pct_reporting'],
       100 * census['land_561730']['lines']['exterior commercial landscaping services']['line_pct_among_reporters'], 100 * MARQ['share']),
    'Open (critique follow-up 3): establishment-level medians of the recurring share were computed for fitness only (713940, the '
    'fit.rec check). For 561730 (landscaping), 541513 (MSP) and 541940 (vet) they were not: 561730\'s care lines overlap across '
    'establishments (residential and commercial are reported separately by %.0f%% and %.0f%% of establishments), so the share at zero '
    'is not identified from the line table, and 541513 / 541940 need a stated spread among reporters as for fitness. The rec slider '
    'definition (contracted vs recurring) that would settle staffing and landscaping is also still unwritten.'
    % (100 * census['land_561730']['lines']['residential landscaping services']['estab_pct_reporting'],
       100 * census['land_561730']['lines']['exterior commercial landscaping services']['estab_pct_reporting']),
    'Open (critique follow-up 6): %s were not opened, so saas.ret has no size gradient, msp.rec no current distribution and '
    'wash.rec only MarQ\'s quoted 35%%.' % '; '.join('%s (%s)' % (k, v) for k, v in FOLLOWUP6.items()),
    'Integration: only land.ret (.74 -> .88) and fit.ret (.62 -> .66, SE .037; revision 2 said .044) change; js_table.rec is {}. Test baselines for landscaping '
    'and fitness businesses that enter the old medians will move (%s and %s at $708k SDE).'
    % (mat_txt('land.ret (shipped)'), mat_txt('fit.ret (shipped)')),
]
CHECKS = [dict(check=k, outcome='PASS' if v else 'FAIL') for k, v in TESTS.items()]
CHECKS += [
    dict(check='fit.rec (judgment .70): establishment-level median implied by the Census line', outcome='RECORDED',
         detail='central %.3f (Beta) / %.3f (logit-normal); grid %.3f-%.3f; .70 needs mu_e %.3f' % (
             fc['central']['median_beta'], fc['central']['median_logitnormal'], fc['range_all'][0], fc['range_all'][1],
             fc['mu_e_that_gives_kept_at_central_sd'])),
    dict(check='saas.rec (judgment .85): cleaned pool', outcome='RECORDED',
         detail='%.3f (SE %.3f), z %.2f from .85' % (clean_pool['value'], clean_pool['se'], saas_z)),
    dict(check='land.ret: the medians against the shipped mean', outcome='RECORDED',
         detail='2025 median .93 and 2026 grouped median %.3f are %.2f and %.2f SE above .88' % (
             g26['median'], land['median_gap_in_se']['y2025'], land['median_gap_in_se']['y2026_grouped'])),
    dict(check='ordering: Spearman of DealLedger mention rates against the hand-set rec', outcome='RECORDED',
         detail='%.3f (p %.4f, n 16); Quiet Light menu removed %.3f' % (r_cur, p_cur, r_nq)),
    dict(check='z-scales .28 and .13 against the measured spreads (kept as judgment)', outcome='RECORDED',
         detail='ret %.3f-%.3f brackets .13; rec ordinary SDs %.2f-%.2f below .28, two-point lower bounds %.2f-%.2f, fitness %.2f above .28'
                % (rng_ret[0], rng_ret[1], rng_rec[0], rng_rec[1], rng_rec_lb[0], rng_rec_lb[1], fit_lb)),
    dict(check='land.rec flag: Census 561730 care and maintenance lines (upper bound)', outcome='RECORDED',
         detail='%.3f of revenue (residential %.3f, exterior commercial %.3f, interior %.3f) against .48' % (
             census['land_561730']['care_maintenance'], census['land_561730']['lines']['residential landscaping services']['share'],
             census['land_561730']['lines']['exterior commercial landscaping services']['share'],
             census['land_561730']['lines']['interior commercial landscaping services']['share'])),
]
if materiality.get('rows'):
    CHECKS.append(dict(check='materiality at $708k SDE (business entering the old median)', outcome='RECORDED',
                       detail='; '.join('%s %+.1f%%' % (r['label'], 100 * r['pct']) for r in materiality['rows'])))

RESULT = dict(
    name=NAME, js_key=JS_KEY, tier='aggregate', revision=3, asof=ASOF, js_table=js_table, js_line=js_line, shipped=shipped,
    not_shipped=not_shipped, checks=CHECKS,
    rounding='values half up to 0.01; SEs half up to 0.001; Spearman to 0.01; mention rates to 0.001',
    decisions=dict(land_ret=float(LAND_RET), land_ret_se=float(LAND_RET_SE), fit_ret_range=[float(FIT_RET_RANGE[0]), float(FIT_RET_RANGE[1])],
                   fit_ret_hcm_independent=float(FIT_RET_HCM_INDEPENDENT),
                   range_to_se=float(RANGE_TO_SE), kept_judgment=KEPT, ef_monetizations=EF_MONETIZATIONS,
                   fit_rec_grid=dict(mu_e=FITREC_MU, sd_e=FITREC_SD, central_mu_e=FITREC_MU_CENTRAL),
                   kbcm='check only, not pooled', round1='peer_recurring_retention.v1.py; out/peer_recurring_retention.v1/',
                   revision2='peer_recurring_retention.v2.py; out/peer_recurring_retention.v2/',
                   revision3=['fit.ret source: an average across 175 companies (114 US), mostly multi-club operators; SE from IHRSA\'s .732 (.037), '
                              'Health Club Management\'s .758 cited',
                              'land.ret note: a judgment shade below the survey medians; the size of the shade is not measured',
                              'flags: land.rec added (Census 561730, .86, an upper bound); MarQ in wash.rec (not opened); msp.rec revenue-weighted',
                              'spread checks: two-point mixtures labelled lower bounds; fitness\'s lower bound exceeds .28',
                              'open issues: critique follow-ups 3 and 6']),
    census=census, saas_rec=dict(ef=ef, dl=dl, round1_pool=dict(value=pool, se=pool_se, Q=Q, weights=(w / w.sum()).tolist()),
                                 cleaned_pool=clean_pool, sensitivities=sens, kbcm=kbcm_check),
    fit_rec_grid=FG.to_dict(orient='records'),
    land_ret=land, fit_ret=fitret, flags=FLAGS, nber=nber, nbb_fig8=NBB_FIG8, ordering_check=ordering,
    spread_checks=dict(rows=SP.to_dict(orient='records'), rec_range_ordinary_sd=rng_rec, rec_range_lower_bounds=rng_rec_lb, fit_lower_bound=fit_lb,
                       ret_range=rng_ret, kept=dict(rec=Z_REC, ret=Z_RET),
                       kbcm_gross_dollar_churn=gdc, kbcm_logo_churn=logo),
    materiality=materiality, current=dict(rec={k: IND[k]['rec'] for k in KEYS}, ret={k: IND[k]['ret'] for k in KEYS}),
    sliders=dict(rec=list(SLIDER['rec']), ret=list(SLIDER['ret'])), quotes=QUOTES, tests=TESTS, diff_vs_research=diff,
    sources=sources, open_issues=OPEN)
with open(OUT + '/RESULT.json', 'w', encoding='utf-8') as f:
    json.dump(RESULT, f, indent=1, sort_keys=True, ensure_ascii=False)
    f.write('\n')

print('\nshipped:')
for k, v in shipped.items():
    print('  %-9s %.2f (SE %.3f), was %.2f, %s' % (k, v['value'], v['se'], v['current'], v['tier']))
print('not shipped (judgment kept): fit.rec %.2f, saas.rec %.2f' % (KEPT['fit.rec'], KEPT['saas.rec']))
print('checks:')
for c in CHECKS:
    print('  %-8s %s%s' % (c['outcome'], c['check'], (': ' + c['detail']) if c.get('detail') else ''))
print('wrote', OUT + '/RESULT.json')
