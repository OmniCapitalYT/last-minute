#!/usr/bin/env python3
"""Fit the realised-price block of index.html (revision 4: the fanNodes() slice means are exact).

Revision 4 changes: an independent review found that fanNodes() read a 4,000-point grid in 48 slices of
k = M/N = 83.33 points: each slice summed 84 points (j < k), overlapped the next and divided by 83.33, so
every node ran ~0.8% high (the top one 4.9%; nodes' mean 1.104 against the fan's 1.092). The nodes are now
exact slice means: ln R is linear in z = probit(p) between knots and beyond them, so E[R^s; a<z<b] has a
closed form per piece. The fix is part of the patched page, the grid and the optimiser pages, and the
'current' (whole spread, s = 1) baseline is the page with that fix alone (fixonly/, fanNodes_fix.diff);
the shipped page is reported beside it. FAN_S is recalibrated on the fixed nodes.

Revision 3 changes: FAN_S is labelled a CALIBRATION (mechanism not identified), not a fit; the source
structure is carried in the model average (IBBA's two sub-$1M bands as two sources or as one; DealStats
in or out: four structures, equal weights); premium dispersion across listings is run out to sd 0.4 and
the interval is stated as conditional on the informative-ask reading; the EF analog is refit under
reading G; BizBuySell's leave-one-out uses a D from other periods; the optimiser flip is located on a
fine grid of s and theta and the default patient-seller answer is shown as a range in the UI when the
two utility peaks are within 1% of value; the test no longer pins it; BizBuySell sectors are
harmonised before clustering and IBBA quarters are block-resampled on the calendar (no wrap-around);
the DealLedger error rule and every hard-coded statement are computed or cited.

Run:  python3 -I /home/user/last-minute/fit/anchoring_realization.py
Outputs go to /tmp/claude-0/fit5/anchoring_realization/ (RESULT.json, tables, run.log, a patched
copy of index.html, AUDIT.md and fit/README.md with the repo's tests run against it). The repo is
not modified.

What is fitted. In model() ("§23 realised price") each of 48 equal-probability slices of the
BIZCOMPS out-of-fold fan R(p) is a scenario W for what the market pays:
    W_p  = V * R(p)^s                         (s = FAN_S; the shipped model has s = 1)
    P(W) = softMin( W * A(ask/W) * (1+comp), ceiling ),  A(r) = 1+(AMAX-1)tanh(ALPHA ln r/(AMAX-1))
Below about $9M of value (ceiling = ask, comp = 0 for a typical pool) P/ask has the same
distribution at every size; it depends only on (s, rho = ask/V, ALPHA, AMAX). The script runs the
model itself on a grid of those four, through the harness with source overrides.

THE MODEL'S ASK IS THE FIRST LISTING PRICE. The console's "Asking price" is the price the seller
lists at, bestRatio() recommends a listing price, the gap penalty and the timing fits
(fit/overpricing_time.py) use the first ask, and the model has no price cuts. The market targets
(BizBuySell closed-deal "asking price", IBBA / Pepperdine "asking/benchmark price") do not say
which ask they use; BizBuySell's is the listing record's price when the deal is reported sold, so
most likely the LAST ask. The fit therefore carries d = E[ln(first ask / last ask)] among sold
deals explicitly: model ask = data ask * e^d, so targets on the model's basis are r * e^-d and the
premium is m * e^d. d is measured for Main Street from the DealLedger broker-listing panel (net
drift of asking prices per listing-year x IBBA's mean months from listing to LOI), and for Empire
Flippers from its reconstructed first asks (an analog that re-prices mechanically as P&L arrives).

THE TYPICAL PREMIUM m = ask/V has three readings, all carried:
  G  (geometric, primary): V is the BIZCOMPS conditional MEDIAN and the fan's E[ln R] = -0.039, so
     over closed deals E ln(ask/V) = E ln(ask/sale) + E ln(sale/V) = ln(median ask/median sale) - 0.039.
  M  (median-centred): a deal at the typical premium has median closed price V: m * median(r) = 1,
     solved inside the model at each s (no market data needed for m).
  R  (ratio of medians, revision 1): m = median ask / median sale, i.e. V read as the geometric
     mean of closed prices. It contradicts the fan's location by 0.039 and gets the lowest weight.

Steps: per source, s solves model E[P|close]/ask = target (IBBA binned by sale price); sources are
pooled by a Bayesian random-effects model (prior on the mean N(1, 0.5^2) = the current value,
weakly held; half-normal(0.5) prior on the between-source sd), with DerSimonian-Laird and
Hartung-Knapp-Sidik-Jonkman (t, k-1 df) reported beside it; the posterior is averaged over the ask
reading (d) and the m reading with stated weights. Validation: leave-one-source-out with tau from
the training sources only, held-out bands and years, a temporal holdout with naive baselines, the
EF per-deal analog on both the last and the first ask, the downside quantiles against EF's tail,
and a selection-on-closing alternative that explains the same level. The optimiser's response is
checked on this page and on the pending fits' patched pages.
All inputs are read by absolute path and treated as untrusted data (parsed, never executed).
"""
import json, os, sys, shutil, subprocess, hashlib, time, math, glob, difflib
import numpy as np
import pandas as pd
from scipy import stats, optimize
import statsmodels.api as sm

T0 = time.time()
OUT = "/tmp/claude-0/fit5/anchoring_realization"
FIT5 = "/tmp/claude-0/fit5"
HARNESS = "/tmp/claude-0/fit5/harness.js"
REPO = "/home/user/last-minute"
INDEX = f"{REPO}/index.html"
TESTS = f"{REPO}/tests"
D5 = "/tmp/claude-0/data5"
DLSNAP = "/tmp/claude-0/dl/jeffsosville_dealledger/data/snapshots"
SEED = 20261010
B_BOOT = 1000          # target bootstrap replicates (primary spec)
B_SPEC = 300           # replicates per non-primary specification
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "run.log"), "w")
rng = np.random.default_rng(SEED)


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")
    LOG.flush()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def wmean(x, w):
    return float(np.sum(np.asarray(x) * np.asarray(w)) / np.sum(w))


log("anchoring_realization.py (revision 4)  run", time.strftime("%Y-%m-%d %H:%M:%S"))
log("index.html sha256[:16] =", sha(INDEX))

# =====================================================================================
# 1. DATA
# =====================================================================================
P_IBBA = f"{D5}/aggregates_research/clean/ibba_mp_realized_to_ask_panel.csv"
P_IBBA_TTC = f"{D5}/aggregates_research/clean/ibba_mp_time_to_close_fits.csv"
P_PEP = f"{D5}/aggregates_research/clean/pepperdine_pcm_figures.csv"
P_DVI = f"{D5}/aggregates_research/clean/dealstats_ask_vs_sale_medians.csv"
P_BBS_CELLS = f"{D5}/extra_wayback_retry_aggregates/clean/bbs_closed_tables.csv"
P_BBS_HEAD = f"{D5}/extra_wayback_retry_aggregates/clean/bbs_insight_headline_metrics.csv"
P_BBS_LONG = f"{D5}/marketplaces_sold/clean/bizbuysell_insight_long.csv"
P_BROKER = f"{D5}/marketplaces_sold/clean/broker_marketplace_aggregate_stats.csv"
P_EF = f"{D5}/extra_ef_sale_ask_reconstruction/clean/ef_sale_ask_reconstructed.csv"
P_EF_FV = f"{D5}/extra_ef_sale_ask_reconstruction/clean/_fit_internal_fair_values.csv"
P_EF_FIRST = f"{D5}/extra_ef_sale_ask_reconstruction/clean/ef_first_ask_reconstructed.csv"
P_EF_LIST = f"{D5}/empireflippers/clean/ef_listings.csv"
P_EF_BIN = f"{D5}/extra_wayback_retry_aggregates/clean/ef_binning_selection_effect.csv"
P_EF_PAR = f"{D5}/extra_ef_sale_ask_reconstruction/clean/fit_parameters.csv"
for p in [P_IBBA, P_IBBA_TTC, P_PEP, P_DVI, P_BBS_CELLS, P_BBS_HEAD, P_BBS_LONG, P_BROKER, P_EF, P_EF_FV,
          P_EF_FIRST, P_EF_LIST, P_EF_BIN, P_EF_PAR]:
    log("input", p, sha(p))
DL_FILES = sorted(glob.glob(f"{DLSNAP}/*/listings.csv"))
_h = hashlib.sha256()
for p in DL_FILES:
    _h.update(open(p, "rb").read())
log(f"input DealLedger snapshots: {len(DL_FILES)} files {DL_FILES[0].split('/')[-2]}..{DL_FILES[-1].split('/')[-2]} combined sha {_h.hexdigest()[:16]}")

BANDS = ["<500K", "500K-1M", "1M-2M", "2M-5M", "5M-50M"]
EDGES = {"<500K": (1.0, 5e5), "500K-1M": (5e5, 1e6), "1M-2M": (1e6, 2e6), "2M-5M": (2e6, 5e6), "5M-50M": (5e6, 5e7)}

# ---- IBBA Market Pulse: average realised / ask (or benchmark) by band, 27 quarters ----
ib = pd.read_csv(P_IBBA)
ib = ib[ib.stat.eq("average") & ib.band.isin(BANDS)].copy()
ib["r"] = pd.to_numeric(ib.pct_of_ask_or_benchmark, errors="coerce") / 100.0
ib = ib.dropna(subset=["r"])
assert ib.groupby(["period", "band"]).size().max() == 1
IBW = ib.pivot(index="period", columns="band", values="r")[BANDS].sort_index()
IBN = ib.pivot(index="period", columns="band", values="n_closed")[BANDS].sort_index()
IBC = IBN.dropna()
log(f"IBBA panel: {IBW.shape[0]} quarters x {IBW.shape[1]} bands; quarters with counts: {IBC.shape[0]}")
log("IBBA band means:", {b: round(float(IBW[b].mean()), 4) for b in BANDS})
IB_AR1 = {b: float(pd.Series(IBW[b].values).autocorr(1)) for b in BANDS}


def qidx(p):
    return int(str(p)[:4]) * 4 + int(str(p)[-1]) - 1


IBW_T = np.array([qidx(p) for p in IBW.index])
IBC_T = np.array([qidx(p) for p in IBC.index])
IB_MISSING = [f"{t // 4}Q{t % 4 + 1}" for t in range(IBW_T.min(), IBW_T.max() + 1) if t not in set(IBW_T)]
IB_XCORR = {f"{a}/{b}": float(IBW[a].corr(IBW[b])) for a, b in [("<500K", "500K-1M"), ("500K-1M", "1M-2M"), ("<500K", "1M-2M")]}
log("IBBA lag-1 autocorrelation of the quarterly series (observed quarters in order):", {b: round(v, 2) for b, v in IB_AR1.items()},
    f"; quarters missing inside the span: {IB_MISSING} -> non-circular block bootstrap on the CALENDAR (blocks of 4 calendar quarters, "
    "missing quarters stay missing, no wrap from 2026Q2 to 2017Q4)")
log("IBBA cross-band correlation of the quarterly series:", {k: round(v, 2) for k, v in IB_XCORR.items()})
IB_INTEGER = bool(np.all(np.abs(IBW.values[~np.isnan(IBW.values)] * 100 - np.round(IBW.values[~np.isnan(IBW.values)] * 100)) < 1e-9))
log(f"IBBA values are whole percentages read off chart labels: {IB_INTEGER}")
log("IBBA denominator: <$1M listed with an ask; $1-2M ask or benchmark; $2M+ mostly an advisor benchmark set before going to market")

# ---- IBBA months from listing to LOI (mean), Main Street bands: the time an ask can be cut ----
ttc = pd.read_csv(P_IBBA_TTC)
_lc = ttc[ttc.measure.eq("listing_to_close_months")].set_index("band")
_li = ttc[ttc.measure.eq("loi_to_close_months")].set_index("band")
T_ROWS = []
for b in ["<500K", "500K-1M"]:
    mlc = float(_lc.loc[b, "gamma_shape"] * _lc.loc[b, "gamma_scale"])
    mli = float(_li.loc[b, "gamma_shape"] * _li.loc[b, "gamma_scale"])
    medlc = float(stats.gamma.median(_lc.loc[b, "gamma_shape"], scale=_lc.loc[b, "gamma_scale"]))
    T_ROWS.append((b, mlc, mli, mlc - mli, float(_lc.loc[b, "n_deals_approx"]), medlc))
T_LIST = sum(r[3] * r[4] for r in T_ROWS) / sum(r[4] for r in T_ROWS) / 12.0
MED_LC_DAYS = sum(r[5] * r[4] for r in T_ROWS) / sum(r[4] for r in T_ROWS) * 365.25 / 12
log("IBBA mean months listing->close / LOI->close / listing->LOI (gamma fits):",
    [(r[0], round(r[1], 2), round(r[2], 2), round(r[3], 2), int(r[4])) for r in T_ROWS],
    f"-> deal-weighted listing->LOI {T_LIST:.3f} years")

# ---- Pepperdine 2016 (2015 deals), MEDIAN realised / ask-or-benchmark by band (respondent n not reported) ----
pep = pd.read_csv(P_PEP, header=None)
pep = pep[pep[2].astype(str).str.contains("Fig 98")]
PEP16 = {str(r[4]).strip(): float(r[5]) / 100 for _, r in pep.iterrows()}
PEP_PAGE = int(float(pep[1].iloc[0]))
log(f"Pepperdine 2016 Fig 98 (PDF p.{PEP_PAGE}; respondent count not reported) medians:", PEP16)

# ---- DealStats: ratio of medians, private targets (check only) ----
dvi = pd.read_csv(P_DVI)
DVI_L = np.log(dvi.median_ask_usd / dvi.median_sale_usd).values
DVI_RM = float(DVI_L.mean())
log(f"DealStats ln(median ask/median sale) mean over {len(dvi)} half-years = {DVI_RM:.4f}")

# ---- BizBuySell closed-deal cells 2016-2018 (sector partition; market partition as check) ----
bc = pd.read_csv(P_BBS_CELLS).drop_duplicates(["data_year", "data_quarter", "dimension", "label1", "label2"])
bc = bc[bc.n_sales.ge(10) & bc.median_sale_price.notna() & bc.median_asking_price.notna() & bc.sale_to_ask_avg.notna()].copy()
sw_ = (bc.data_year == 2018) & (bc.dimension == "market")
frac_bad = float((bc.loc[sw_, "median_sale_price"] > bc.loc[sw_, "median_asking_price"]).mean())
bc.loc[sw_, ["median_sale_price", "median_asking_price"]] = bc.loc[sw_, ["median_asking_price", "median_sale_price"]].values
log(f"BizBuySell 2018 market table: {frac_bad:.0%} of cells had sale > ask as parsed (impossible with an average sale/ask of 0.92) -> columns swapped")
bc["lrm"] = np.log(bc.median_asking_price / bc.median_sale_price)
SEC = bc[bc.dimension != "market"].reset_index(drop=True)
MKT = bc[bc.dimension == "market"].reset_index(drop=True)
# Sector names change across the three annual tables ('Communications' / 'Communication and Media', 'Internet' /
# 'Online and Technology', ...) and the 2016 table misaligns label1 for two construction rows. Harmonise before
# clustering, so the bootstrap and the gradient SEs cluster on true sectors, not on table spellings.
SECTOR_MAP = {"Agriculture": "Agriculture", "Construction": "Construction", "Manufacturing": "Manufacturing", "Mining": "Mining",
              "Retail": "Retail", "Communications": "Communications and media", "Communication and Media": "Communications and media",
              "Internet": "Online and technology", "Online and Technology": "Online and technology", "Service": "Services",
              "Service Businesses": "Services", "Wholesale": "Wholesale", "Wholesale and Distributors": "Wholesale",
              "Non-classifiable Establishments": "Other", "Other": "Other", "Electric, Gas, Water, Sanitary Svcs": "Utilities"}
SEC["sector_h"] = SEC.label1.map(SECTOR_MAP)
_fix = SEC.label2.astype(str).str.startswith("Construction")
N_RELABEL = int((_fix & (SEC.sector_h != "Construction")).sum())
SEC.loc[_fix, "sector_h"] = "Construction"
assert SEC.sector_h.notna().all(), SEC[SEC.sector_h.isna()].label1.unique()
log(f"BizBuySell cells: sector {len(SEC)} cells / {int(SEC.n_sales.sum())} sales ({SEC.label1.nunique()} table spellings -> "
    f"{SEC.sector_h.nunique()} harmonised sectors; {N_RELABEL} misaligned 2016 construction rows re-assigned); "
    f"market {len(MKT)} / {int(MKT.n_sales.sum())}")
BBS_R = wmean(SEC.sale_to_ask_avg, SEC.n_sales)
BBS_D = wmean(SEC.lrm, SEC.n_sales)
log(f"BizBuySell sector cells: mean sale/ask {BBS_R:.4f}; D = ln(median ask/median sale) {BBS_D:.4f}")
log(f"  market partition: mean sale/ask {wmean(MKT.sale_to_ask_avg, MKT.n_sales):.4f}; D {wmean(MKT.lrm, MKT.n_sales):.4f}")

# size gradient of sale/ask across cells (both partitions), per doubling of the median sale price
GRAD = {}
for nm, d_, cl in [("sector", SEC, "sector_h"), ("market", MKT, "label1")]:
    X = sm.add_constant(np.log2(d_.median_sale_price.values))
    fit_ = sm.WLS(d_.sale_to_ask_avg.values, X, weights=d_.n_sales.values).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d_[cl])[0]})
    GRAD[nm] = (float(fit_.params[1]), float(fit_.bse[1]), float(fit_.pvalues[1]), len(d_))
log("BizBuySell cell-level size gradient of sale/ask per doubling of median sale price (WLS by n, SE clustered by harmonised sector / market):",
    {k: f"{v[0]:+.4f} (SE {v[1]:.4f}, p {v[2]:.3f}, {v[3]} cells)" for k, v in GRAD.items()})

# ---- BizBuySell national headline series ----
bh = pd.read_csv(P_BBS_HEAD)
bl = pd.read_csv(P_BBS_LONG)
GE1M = bh[(bh.segment == "sale price >= $1M") & (bh.metric == "sale_to_ask_avg")][["period", "value"]]
BBS25 = float(bl[(bl.segment == "all") & (bl.metric == "avg_sale_to_ask_ratio") & (bl.period.astype(str) == "2025")].value.iloc[0])
log("BizBuySell >= $1M (sale-binned):", GE1M.values.tolist(), "| 2025 all-deal mean:", BBS25)


def pkey(p):
    p = str(p).strip()
    if p.startswith("FY"):
        return p[2:]
    if p.startswith("Q") and " " in p:
        q, y = p.split()
        return f"{y}{q}"
    return p


# closed-deal size distribution in the periods of the $1M+ series (read from the files, not typed in)
GE_KEYS = {pkey(p) for p in GE1M.period}
ms_rows = {}
for _, r in bh[(bh.segment == "all sold") & (bh.metric == "median_sale_price")].iterrows():
    ms_rows[pkey(r.period)] = float(r.value)
for _, r in bl[(bl.segment == "all") & (bl.metric == "median_sale_price")].iterrows():
    ms_rows.setdefault(pkey(r.period), float(r.value))
MED_SALE = [ms_rows[k] for k in sorted(GE_KEYS) if k in ms_rows]
sh_rows = {}
nn = bh[bh.metric == "n_sales"].pivot_table(index="period", columns="segment", values="value", aggfunc="first")
for per, r in nn.iterrows():
    if "sale price >= $1M" in r and "all sold" in r and pd.notna(r["sale price >= $1M"]):
        sh_rows[pkey(per)] = float(r["sale price >= $1M"] / r["all sold"])
for _, r in bh[(bh.segment == "sale price >= $1M") & (bh.metric == "share_of_sales")].iterrows():
    sh_rows.setdefault(pkey(r.period), float(r.value))
SH_GE1M = [v for k, v in sorted(sh_rows.items()) if k[:4] in ("2018", "2019")]
BBS_MED, BBS_SH = float(np.exp(np.mean(np.log(MED_SALE)))), float(np.mean(SH_GE1M))
log(f"BizBuySell closed-deal size (read from files): median sale {[int(x) for x in MED_SALE]} -> geometric mean ${BBS_MED:,.0f}; "
    f"share >= $1M {[round(x, 3) for x in SH_GE1M]} -> {BBS_SH:.3f}")
DOM = bl[(bl.segment == "all") & (bl.metric == "median_days_on_market")].value.astype(float)
log(f"BizBuySell median days on market of sold businesses (listing to CLOSE, per DATA_DICTIONARY), {len(DOM)} periods 2020-2025: median "
    f"{DOM.median():.0f} days, vs IBBA's gamma-fit MEDIAN listing->close {MED_LC_DAYS:.0f} days (<$1M bands, deal-weighted). This compares "
    f"like with like; it does NOT validate the {T_LIST * 365.25:.0f}-day mean listing->LOI used for d, which rests on IBBA's own split")
# headline ratio-of-medians pairs (cross-check on D)
pairs = []
for per in ["FY2016", "Q1 2017", "Q1 2018", "Q2 2019"]:
    g = bh[(bh.period == per) & (bh.segment == "all sold")]
    ms, ma = g[g.metric == "median_sale_price"].value, g[g.metric == "median_asking_price"].value
    if len(ms) and len(ma):
        pairs.append((per, float(ma.iloc[0]) / float(ms.iloc[0])))
for per in ["2018", "2022Q2", "2023Q3"]:
    g = bl[(bl.period.astype(str) == per) & (bl.segment == "all")]
    ms, ma = g[g.metric == "median_sale_price"].value, g[g.metric == "median_asking_price_sold"].value
    if len(ms) and len(ma):
        pairs.append((per, float(ma.iloc[0]) / float(ms.iloc[0])))
br = pd.read_csv(P_BROKER)
g12 = br[(br.period.astype(str) == "2012") & br.source_org.str.contains("BizBuySell")]
try:
    pairs.append(("2012", float(g12[g12.metric == "median_asking_price_sold"].value.iloc[0]) / float(g12[g12.metric == "median_sale_price"].value.iloc[0])))
except IndexError:
    pass
HEAD_M = np.array([p[1] for p in pairs])
log("BizBuySell headline median ask / median sale:", [(p[0], round(p[1], 3)) for p in pairs],
    f"mean {HEAD_M.mean():.3f} sd {HEAD_M.std(ddof=1):.3f}")

# ---- DealLedger broker listings (Main Street): how far asks move between first and last sighting ----
fr = []
for f in DL_FILES:
    d_ = pd.read_csv(f, low_memory=False, usecols=lambda c: c in ["url", "source_url", "asking_price", "broker_name", "title"])
    d_["snap"] = f.split("/")[-2]
    fr.append(d_)
DLA = pd.concat(fr, ignore_index=True)
DLA["key"] = DLA["url"].fillna(DLA["source_url"])
DLA["asking_price"] = pd.to_numeric(DLA["asking_price"], errors="coerce")
DLA["snap"] = pd.to_datetime(DLA["snap"])
DLA = DLA[DLA.asking_price > 1e4].dropna(subset=["key"]).sort_values(["key", "snap"]).drop_duplicates(["key", "snap"])
g_ = DLA.groupby("key")
DLP = pd.DataFrame({"n": g_.snap.count(), "d0": g_.snap.min(), "d1": g_.snap.max(), "a0": g_.asking_price.first(),
                    "a1": g_.asking_price.last(), "broker": g_.broker_name.last(), "t0": g_.title.first(), "t1": g_.title.last()})
DLP = DLP[(DLP.n >= 2) & (DLP.d1 > DLP.d0)].copy()
DLP["yrs"] = (DLP.d1 - DLP.d0).dt.days / 365.25
DLP["lchg"] = np.log(DLP.a1 / DLP.a0)
DLP["broker"] = DLP.broker.fillna("unknown")
log(f"DealLedger: {DLA.key.nunique():,} listings, {len(DLP):,} seen twice or more, {DLP.yrs.sum():,.0f} listing-years of exposure, "
    f"{DLP.broker.nunique()} brokers; share with any change {(DLP.lchg.abs() > .005).mean():.3f}, "
    f"|change| > 0.5 log (treated as data errors) {(DLP.lchg.abs() > .5).mean():.3f}")


def dl_drift(d_, trim=0.5, cuts_only=False):
    x = d_.lchg.where(d_.lchg.abs() <= trim, 0.0)          # an implausible jump counts as no change
    if cuts_only:
        x = x.clip(upper=0.0)
    return float(x.sum() / d_.yrs.sum())


DRIFT = {"net, |chg|<=0.5": dl_drift(DLP), "net, |chg|<=0.35": dl_drift(DLP, .35), "net, |chg|<=0.7": dl_drift(DLP, .7),
         "cuts only, |chg|<=0.5": dl_drift(DLP, .5, True)}
# The error rule matters: describe what it discards (reviewer: about half of all observed changes)
_chg = DLP[DLP.lchg.abs() > .005]
_big = _chg[_chg.lchg.abs() > .5]
_small = _chg[_chg.lchg.abs() <= .5]
_ratio = np.exp(_big.lchg.abs())
DL_RULE = {"n_changed": len(_chg), "n_big": len(_big), "share_big": len(_big) / len(_chg),
           "q10_q90_big": (float(_big.lchg.quantile(.1)), float(_big.lchg.quantile(.9))),
           "median_abs_big": float(_big.lchg.abs().median()),
           "title_changed_big": float((_big.t0 != _big.t1).mean()), "title_changed_small": float((_small.t0 != _small.t1).mean()),
           "factor10_big": float(((_ratio > 9) & (_ratio < 11)).mean()),
           "drift_untrimmed": float(DLP.lchg.sum() / DLP.yrs.sum()),
           "drift_exclude": float(DLP.lchg[DLP.lchg.abs() <= .5].sum() / DLP.yrs[DLP.lchg.abs() <= .5].sum())}
log(f"DealLedger error rule: of {DL_RULE['n_changed']:,} listings whose ask changed, {DL_RULE['n_big']:,} ({DL_RULE['share_big']:.0%}) moved by more than "
    f"0.5 in logs (10%/90% of those {DL_RULE['q10_q90_big'][0]:+.2f}/{DL_RULE['q10_q90_big'][1]:+.2f}; median |change| {DL_RULE['median_abs_big']:.2f}, a factor of "
    f"{math.exp(DL_RULE['median_abs_big']):.1f}); {DL_RULE['title_changed_big']:.0%} of them changed title (vs {DL_RULE['title_changed_small']:.0%} of the smaller "
    f"changes), {DL_RULE['factor10_big']:.0%} are a factor of ten; keys include broker index pages. They are set to no change. Untrimmed drift "
    f"{DL_RULE['drift_untrimmed']:+.4f}/yr (the SIGN flips); excluding those listings instead of zeroing them {DL_RULE['drift_exclude']:+.4f}/yr")
brokers = DLP.broker.unique()
bidx = {b: np.where(DLP.broker.values == b)[0] for b in brokers}
dr_b = []
for _ in range(B_BOOT):
    pick = rng.choice(brokers, len(brokers))
    dr_b.append(dl_drift(DLP.iloc[np.concatenate([bidx[b] for b in pick])]))
SE_DRIFT = float(np.std(dr_b, ddof=1))
D_MS = -DRIFT["net, |chg|<=0.5"] * T_LIST
D_MS_CUTS = -DRIFT["cuts only, |chg|<=0.5"] * T_LIST
# sd of d for the last-ask reading: sampling (broker-cluster bootstrap), +-20% on the time, and half
# the distance to the cuts-only figure (raises may be data noise)
SD_D = math.sqrt((SE_DRIFT * T_LIST) ** 2 + (0.2 * D_MS) ** 2 + ((D_MS_CUTS - D_MS) / 2) ** 2)
log("DealLedger ask drift per listing-year:", {k: round(v, 4) for k, v in DRIFT.items()}, f"(broker-cluster SE {SE_DRIFT:.4f})")
D_UNTRIM = -DL_RULE["drift_untrimmed"] * T_LIST
D_EXCL = -DL_RULE["drift_exclude"] * T_LIST
log(f"Main Street first-to-last ask gap among sold deals d = -drift x listing->LOI time = {D_MS:.4f} "
    f"(cuts only {D_MS_CUTS:.4f}; excluding jumps {D_EXCL:.4f}; untrimmed {D_UNTRIM:+.4f}); sd used for the last-ask reading {SD_D:.4f} "
    "(sampling, time and cuts-only gap; the error rule is shown as a sensitivity, not in the sd)")

# ---- Empire Flippers per-deal reconstruction (analog) ----
ef = pd.read_csv(P_EF)
ef = ef[ef.group_rule.isin(["anchor", "between_1step_by_annual_order"]) & ~ef.flag_no_ask.astype(bool)].copy()
ef["r"] = ef.ratio_mean.astype(float)
ef["at"] = ef.r >= 0.9999
ef["month"] = pd.to_datetime(ef.sold_date_est).dt.to_period("M").astype(str)
ef["askband"] = pd.cut(ef.listing_price, [0, 1e5, 2.5e5, 1e6, 1e12], right=False, labels=["<$100K", "$100-250K", "$250K-1M", "$1M+"])
fv = pd.read_csv(P_EF_FV)
ef = ef.merge(fv[["listing_number", "rhoW"]], on="listing_number", how="left")
EF_RHOW = float(ef.rhoW.mean())
log(f"EF analysis sample n={len(ef)}; mean r {ef.r.mean():.4f}; P(r>=1) {ef['at'].mean():.4f}; P(r exactly 1) {ef.sold_at_ask.astype(bool).mean():.4f}; "
    f"below-ask mean {ef.r[~ef['at']].mean():.4f}; E[ln r] {np.log(ef.r).mean():.4f}; mean ln(ask/hedonic fair sale) {EF_RHOW:.4f}")
fa = pd.read_csv(P_EF_FIRST)
efl = pd.read_csv(P_EF_LIST, low_memory=False, usecols=["listing_number", "first_listed_at", "metrics_last_month"])
EF1 = ef.merge(fa[["listing_number", "first_ask_est", "log_ask_change_first_to_last"]], on="listing_number").merge(efl, on="listing_number", how="left")
EF1 = EF1[EF1.first_ask_est.notna() & EF1.rhoW.notna()].copy()
EF1["dl"] = EF1.log_ask_change_first_to_last                       # ln(last ask / first ask)
EF1["r1"] = EF1.r * np.exp(EF1.dl)                                   # sale / FIRST ask
EF1["rebased"] = (pd.to_datetime(EF1.first_listed_at, utc=True).dt.tz_localize(None) - pd.to_datetime(EF1.metrics_last_month)).dt.days < 15
log(f"EF first ask reconstructed for {len(EF1)} sold deals: mean ln(first/last) {-EF1.dl.mean():+.4f}; "
    f"not re-based (profit base unchanged since listing, {(~EF1.rebased).mean():.0%}) {-EF1.dl[~EF1.rebased].mean():+.4f}; "
    f"re-based {-EF1.dl[EF1.rebased].mean():+.4f}")
efb = pd.read_csv(P_EF_BIN)
# EF anchoring estimates made by the reconstruction's own fit (_scripts/09_fit.py), cited, not re-estimated here
efp = pd.read_csv(P_EF_PAR).set_index("parameter")
EF_PAR = {"tobit": (float(efp.loc["alpha (pass-through), Tobit right-censored at ask: all years", "estimate"]),
                    float(efp.loc["alpha (pass-through), Tobit right-censored at ask: all years", "se"])),
          "ols": (float(efp.loc["alpha (pass-through of log ask to log sale), OLS: all years", "estimate"]),
                  float(efp.loc["alpha (pass-through of log ask to log sale), OLS: all years", "se"])),
          "app_alpha": (float(efp.loc["app form: alpha (ALPHA_ANCHOR analog)", "estimate"]), float(efp.loc["app form: alpha (ALPHA_ANCHOR analog)", "se"])),
          "app_amax": (float(efp.loc["app form: A_max (AMAX analog)", "estimate"]), float(efp.loc["app form: A_max (AMAX analog)", "se"])),
          "sd_rel_ask": float(efp.loc["sd of relative ask rho = log a - log a_hat", "estimate"])}
EF_SD_RHOW = float(ef.rhoW.std())
log(f"EF reconstruction's own anchoring fits ({P_EF_PAR}): pass-through of ln ask to ln sale given the hedonic value, Tobit "
    f"{EF_PAR['tobit'][0]:.3f} (SE {EF_PAR['tobit'][1]:.3f}), OLS {EF_PAR['ols'][0]:.3f} (SE {EF_PAR['ols'][1]:.3f}); the app's own A() form fitted "
    f"by censored MLE: alpha {EF_PAR['app_alpha'][0]:.3f} (SE {EF_PAR['app_alpha'][1]:.3f}), A_max {EF_PAR['app_amax'][0]:.3f} (SE {EF_PAR['app_amax'][1]:.3f}); "
    f"sd of ln(ask / hedonic fair sale) across sold deals {EF_SD_RHOW:.3f}")

# =====================================================================================
# 2. THE MODEL ITSELF ON A GRID (harness + source overrides)
# =====================================================================================
# Overrides: ALPHA, FAN_S and AMAX become settable; the fan nodes become EXACT slice means of R(p)^s (the
# form recommended for index.html, including the fanNodes fix); the 48 capped prices, the at-ceiling flags and each slice's own
# chance of closing relative to the base (1 - gapPenalty at the slice's gap; used only for the
# selection alternative) are exported. Evaluated at a median 'prof' business with $400k of earnings
# (V ~ $1.0M, comp = 0, ceiling = ask); scale-freeness is verified across 16 industries x 4 sizes.
# fanNodes(): the shipped page reads a 4,000-point grid in 48 slices of k = M/N = 83.33 points; each slice sums 84
# points (j < k), overlaps the next and divides by 83.33, so every node runs ~0.8% high. FAN_FIX_BLOCK replaces it with
# exact slice means (closed form per piece of the piecewise-linear-in-z log fan); FAN_S_BLOCK is the same with
# R(p)^FAN_S (ln R^s = s c + s B z, the same form). FAN_FIX alone is the 'current' baseline (whole spread, s = 1).
FAN_OLD_BLOCK = r"""/* The price distribution is carried on 48 equal-probability slices of the measured
   fan. Each node is the MEAN of its slice (from a 4,000-point grid), not its midpoint,
   so the nodes reproduce the fan's mean to 0.15% (1.092 vs the measured 1.0907)
   where midpoints lose the right tail and fall to 1.085. */
let FAN_NODES=null;
function fanNodes(){
  if(FAN_NODES) return FAN_NODES;
  const N=48,M=4000,out=[];
  for(let i=0;i<N;i++){ let s=0; const k=M/N;
    for(let j=0;j<k;j++) s+=fanRatio((i*k+j+.5)/M); out.push(s/k); }
  return FAN_NODES=out;
}
"""
FAN_FIX_BLOCK = r"""/* The price distribution is carried on 48 equal-probability slices of the measured
   fan. Each node is the exact MEAN of its slice, not its midpoint. ln R is linear in
   z = probit(p) between knots and continues at the end slopes beyond them (fanRatio),
   so on a piece where ln R = c + B z, E[R; a<z<b] = exp(c+B^2/2) (Phi(b-B) - Phi(a-B)),
   and a slice's mean is 48 times the sum over its pieces: no grid, and the open-ended
   outer slices keep their whole tails. The nodes reproduce the fan's mean, 1.0924 vs
   the measured 1.0907 (0.15%), to within the normal CDF's approximation (< 5e-5 per
   node); midpoints lose the right tail and fall to 1.085. This replaced a 4,000-point
   grid cut into 48 slices of 83.3 points: each summed 84 points and overlapped the
   next, so every node ran ~0.8% high (the top one 4.9%) and their mean was 1.104. */
let FAN_NODES=null;
function fanNodes(){
  if(FAN_NODES) return FAN_NODES;
  const N=48,Z=FAN.z,Y=FAN.y,n=Z.length,out=[];
  if(n<2){ for(let i=0;i<N;i++) out.push(1); return FAN_NODES=out; }
  const seg=[];                    /* ln R = c + B z on [L,U]; the end pieces are open */
  for(let j=0;j<=n;j++){
    const i0=Math.min(Math.max(j-1,0),n-2), B=(Y[i0+1]-Y[i0])/(Z[i0+1]-Z[i0]);
    seg.push({L:j===0?-Infinity:Z[j-1],U:j===n?Infinity:Z[j],c:Y[i0]-B*Z[i0],B});
  }
  for(let i=0;i<N;i++){
    const lo=i===0?-Infinity:nqnt(i/N), hi=i===N-1?Infinity:nqnt((i+1)/N);
    let s=0;
    for(const g of seg){ const a=Math.max(lo,g.L), b=Math.min(hi,g.U);
      if(a<b) s+=Math.exp(g.c+g.B*g.B/2)*(ncdf(b-g.B)-ncdf(a-g.B)); }
    out.push(N*s);
  }
  return FAN_NODES=out;
}
"""
FAN_S_BLOCK = FAN_FIX_BLOCK
for _o, _n in [
        ("   next, so every node ran ~0.8% high (the top one 4.9%) and their mean was 1.104. */\n",
         "   next, so every node ran ~0.8% high (the top one 4.9%) and their mean was 1.104.\n"
         "   Each node is the slice mean of R(p)^FAN_S: the realised-price fan keeps FAN_S of the\n"
         "   value spread, in logs (median kept); ln R^FAN_S = FAN_S c + FAN_S B z has the same form,\n"
         "   and the fan's mean above is the FAN_S = 1 case. */\n"),
        ("    for(const g of seg){ const a=Math.max(lo,g.L), b=Math.min(hi,g.U);\n"
         "      if(a<b) s+=Math.exp(g.c+g.B*g.B/2)*(ncdf(b-g.B)-ncdf(a-g.B)); }\n",
         "    for(const g of seg){ const a=Math.max(lo,g.L), b=Math.min(hi,g.U), c=FAN_S*g.c, B=FAN_S*g.B;\n"
         "      if(a<b) s+=Math.exp(c+B*B/2)*(ncdf(b-B)-ncdf(a-B)); }\n")]:
    assert FAN_S_BLOCK.count(_o) == 1, _o[:60]
    FAN_S_BLOCK = FAN_S_BLOCK.replace(_o, _n)
FAN_FIX = [[FAN_OLD_BLOCK, FAN_FIX_BLOCK]]
S_GRID = np.round(np.arange(0.05, 1.6001, 0.025), 4)
M_GRID = np.round(np.exp(np.arange(math.log(0.30), math.log(4.50) + 1e-9, 0.01)), 6)   # wide, for premium dispersion up to sd 0.4
AL_GRID = [0.30, 0.45, 0.55, 0.70, 0.85]
AM_GRID = [1.30, 1.66]
OVR = [
    ["const ALPHA_ANCHOR=.55;", "let ALPHA_ANCHOR=.55; let FAN_S=1; MODELS.__set=function(a,s,am){ALPHA_ANCHOR=a;FAN_S=s;AMAX=am;FAN_NODES=null;};"],
    ["const AMAX=1.30;", "let AMAX=1.30;"],
    [FAN_OLD_BLOCK, FAN_S_BLOCK],
    ["const wt=1;", "const wt=(MODELS.__sel?Math.max(1e-12,1-gapPenalty((s.ask/W-1)*100)):1);"],
    ["out.Vmean=sp/sw;", "out.Vmean=sp/sw; out.__Pc=Pc.slice(); out.__Pf=Pf.slice(); out.__G=RN.map(x=>1-gapPenalty((s.ask/(out.V*x)-1)*100));"]]
JS_GRID = r"""
const H=require(__HARNESS__), fs=require("fs");
const spec=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const A=H.load(spec.ovr), B=H.load(spec.fix), B0=H.load([]);
function median(ind,ern){const I=A.IND[ind],R=A.sizeRefs(ern);
  return{ind,ern,rev:ern/A.typMargin(ind,ern),yrs:6,buyers:I.buyers,franchise:false,st:null,
         rec:I.rec,cc:.16,own:R.own,mgt:R.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:R.fin,plt:.40};}
const out={check:[],scale:[],bug:[]};
/* 1. with the defaults the overridden model reproduces the model with the fanNodes fix alone exactly;
      the shipped page (fanNodes overlap bug) is compared with it */
A.MODELS.__set(.55,1,1.30);
for(const ind of Object.keys(A.IND)) for(const ern of [1.2e5,4e5,1.5e6]) for(const m of [.8,1,1.1,1.4]){
  const t=median(ind,ern), V=B.model({...t,ask:1}).V, a=A.model({...t,ask:V*m}), b=B.model({...t,ask:V*m}), b0=B0.model({...t,ask:V*m});
  out.check.push(Math.max(Math.abs(a.Vmean/b.Vmean-1),Math.abs(a.capShare-b.capShare),Math.abs(a.Vreal/b.Vreal-1),Math.abs(a.EVp/b.EVp-1),
                          Math.abs(a.q(.08)/b.q(.08)-1)));
  out.bug.push([b0.Vmean/b.Vmean-1, b0.q(.08)/b.q(.08)-1, b0.VrealFree/b.VrealFree-1]);}
/* the nodes: shipped vs exact, and a brute-force check of the exact ones (200,000 midpoints per slice) */
{ const n0=B0.fanNodes(), n1=B.fanNodes(), mean=a=>a.reduce((x,y)=>x+y,0)/a.length, K=200000; let worst=0;
  for(let i=1;i<47;i++){ let s=0; for(let j=0;j<K;j++) s+=B.fanRatio((i+(j+.5)/K)/48); worst=Math.max(worst,Math.abs(n1[i]/(s/K)-1)); }
  const rel=n0.map((x,i)=>x/n1[i]-1);
  out.nodes={shipped_mean:mean(n0),exact_mean:mean(n1),midpoint_mean:mean(Array.from({length:48},(_,i)=>B.fanRatio((i+.5)/48))),
             interior_bias_min:Math.min(...rel.slice(1,47)),interior_bias_max:Math.max(...rel.slice(1,47)),bias_top:rel[47],bias_bottom:rel[0],
             exact_vs_brute_interior:worst,shipped:n0,exact:n1}; }
/* the fan's own location: E[ln R] and E[R] (the fan median is 1 by construction) */
let sl=0,sr=0; const NF=400000; for(let i=0;i<NF;i++){const x=A.fanRatio((i+.5)/NF); sl+=Math.log(x); sr+=x;}
out.ElnR=sl/NF; out.ER=sr/NF; out.p50=A.fanRatio(.5);
/* 2. the grid */
const t=median(spec.ind,spec.ern), nS=spec.s.length, nM=spec.m.length, NN=48;
const tot=spec.alpha.length*spec.amax.length*nS*nM;
const R=new Float64Array(tot*NN), C=new Uint8Array(tot*NN), G=new Float64Array(nS*nM*NN);
let g=0, gg=0;
for(const al of spec.alpha) for(const am of spec.amax) for(const s of spec.s){
  A.MODELS.__set(al,s,am); const V=A.model({...t,ask:1}).V;
  for(const m of spec.m){ const ask=V*m, r=A.model({...t,ask});
    for(let i=0;i<NN;i++){ R[g*NN+i]=r.__Pc[i]/ask; C[g*NN+i]=r.__Pf[i]>=r.ceil?1:0; }
    if(al===.55&&am===1.30){ for(let i=0;i<NN;i++) G[gg*NN+i]=r.__G[i]; gg++; }
    g++; }}
/* 3. scale-freeness: the ratio distribution is the same at other sizes and industries (V < $8.5M) */
for(const [al,s,m] of [[.55,1,1.1],[.55,.6,1.07],[.3,.8,1.0],[.85,1.5,1.2]]){
  A.MODELS.__set(al,s,1.30); let worst=0; const t0=median(spec.ind,spec.ern), V0=A.model({...t0,ask:1}).V, r0=A.model({...t0,ask:V0*m});
  for(const ind of Object.keys(A.IND)) for(const ern of [1.2e5,4e5,1.5e6,2.2e6]){
    const t1=median(ind,ern), V1=A.model({...t1,ask:1}).V; if(V1>8.5e6) continue;
    const r1=A.model({...t1,ask:V1*m});
    for(let i=0;i<NN;i++) worst=Math.max(worst,Math.abs(r1.__Pc[i]/r1.inputs.ask-r0.__Pc[i]/r0.inputs.ask)); }
  out.scale.push([al,s,m,worst]); }
fs.writeFileSync(spec.out+"/grid_R.f64",Buffer.from(R.buffer));
fs.writeFileSync(spec.out+"/grid_C.u8",Buffer.from(C.buffer));
fs.writeFileSync(spec.out+"/grid_G.f64",Buffer.from(G.buffer));
out.n=g; out.maxCheck=Math.max(...out.check);
console.log(JSON.stringify(out));
""".replace("__HARNESS__", json.dumps(HARNESS))
GDIR = os.path.join(OUT, "grid")
if os.path.isdir(GDIR):
    shutil.rmtree(GDIR)
os.makedirs(GDIR)
with open(os.path.join(GDIR, "grid_driver.js"), "w") as f:
    f.write(JS_GRID)
spec = {"alpha": AL_GRID, "amax": AM_GRID, "s": S_GRID.tolist(), "m": M_GRID.tolist(), "ind": "prof", "ern": 4e5, "out": GDIR, "ovr": OVR, "fix": FAN_FIX}
with open(os.path.join(GDIR, "grid_spec.json"), "w") as f:
    json.dump(spec, f)
t_g = time.time()
res = subprocess.run(["node", os.path.join(GDIR, "grid_driver.js"), os.path.join(GDIR, "grid_spec.json")],
                     capture_output=True, text=True, timeout=3600)
if res.returncode != 0:
    log(res.stderr)
    raise SystemExit("grid driver failed")
ginfo = json.loads(res.stdout.strip().splitlines()[-1])
nA, nAM, nS, nM, NN = len(AL_GRID), len(AM_GRID), len(S_GRID), len(M_GRID), 48
GR = np.fromfile(os.path.join(GDIR, "grid_R.f64"), dtype=np.float64).reshape(nA, nAM, nS, nM, NN)
GC = np.fromfile(os.path.join(GDIR, "grid_C.u8"), dtype=np.uint8).reshape(nA, nAM, nS, nM, NN).astype(float)
GG = np.fromfile(os.path.join(GDIR, "grid_G.f64"), dtype=np.float64).reshape(nS, nM, NN)
ELNR = float(ginfo["ElnR"])
log(f"harness grid: {ginfo['n']} model evaluations in {time.time() - t_g:.1f}s (s {S_GRID[0]}-{S_GRID[-1]}, rho {M_GRID[0]}-{M_GRID[-1]:.2f}, "
    f"ALPHA {AL_GRID}, AMAX {AM_GRID}); overridden model at defaults vs the page with the fanNodes fix alone, max rel diff = {ginfo['maxCheck']:.2e}")
NODES = ginfo["nodes"]
BUG = np.array(ginfo["bug"])
log(f"fanNodes: shipped nodes' mean {NODES['shipped_mean']:.4f}, exact {NODES['exact_mean']:.4f} (slice midpoints {NODES['midpoint_mean']:.4f}; measured mean/median "
    f"1.0907); shipped/exact per node: interior {100 * NODES['interior_bias_min']:+.2f}% to {100 * NODES['interior_bias_max']:+.2f}%, top {100 * NODES['bias_top']:+.2f}%, bottom "
    f"{100 * NODES['bias_bottom']:+.2f}%; exact vs brute force (200,000 midpoints per slice), interior: {NODES['exact_vs_brute_interior']:.1e}")
log(f"fanNodes bug effect on the model (shipped / fixed - 1, 16 industries x 3 sizes x ask 0.8-1.4 V): E[P|close] {100 * BUG[:, 0].min():+.2f}% to {100 * BUG[:, 0].max():+.2f}%, "
    f"q(.08) {100 * BUG[:, 1].min():+.2f}% to {100 * BUG[:, 1].max():+.2f}%, uncapped median {100 * BUG[:, 2].min():+.2f}% to {100 * BUG[:, 2].max():+.2f}%")
assert NODES["exact_vs_brute_interior"] < 1e-4
log(f"fan location: median R = {ginfo['p50']:.4f}, E[ln R] = {ELNR:.4f}, E[R] = {ginfo['ER']:.4f}")
log("scale-freeness (alpha, s, rho, worst |dP/ask| across 16 industries x 4 sizes):", ginfo["scale"])
assert ginfo["maxCheck"] < 1e-9
assert max(x[3] for x in ginfo["scale"]) < 5e-4
IA55, IAM130 = AL_GRID.index(0.55), AM_GRID.index(1.30)
LM = np.log(M_GRID)

# =====================================================================================
# 3. MOMENTS OF THE MODEL'S SALE/ASK DISTRIBUTION
# =====================================================================================
def _interp_rows(arr, lnm):
    """arr (nS, nM, K): value at ln-premium lnm, a scalar or one per s-row."""
    lnm = np.broadcast_to(np.asarray(lnm, float), (arr.shape[0],))
    assert lnm.min() >= LM[0] - 1e-9 and lnm.max() <= LM[-1] + 1e-9, ("premium outside the grid", np.exp(lnm.min()), np.exp(lnm.max()))
    j = np.clip(np.searchsorted(LM, lnm) - 1, 0, nM - 2)
    w = np.clip((lnm - LM[j]) / (LM[j + 1] - LM[j]), 0, 1)[:, None]
    rows = np.arange(arr.shape[0])
    return (1 - w) * arr[rows, j, :] + w * arr[rows, j + 1, :]


def atoms(m, ia=IA55, iam=IAM130, sd=0.0, sel=False, nq=11):
    """Sale/ask atoms r (nS, K), at-ceiling flags c (nS, K) and weights Q (nS, K; rows sum to 1) for
    listings at premium m (scalar or per s-row), or with ln premium ~ N(ln m, sd^2) across listings.
    sel=True weights each slice by its own chance of closing (selection alternative, ALPHA .55 only)."""
    lnm = np.log(np.broadcast_to(np.asarray(m, float), (nS,)))
    if sd == 0:
        nodes, wts = [0.0], [1.0]
    else:
        x, w = np.polynomial.hermite_e.hermegauss(nq)
        nodes, wts = list(sd * x), list(w / w.sum())
    rs, cs, qs = [], [], []
    for x, wk in zip(nodes, wts):
        lx = np.clip(lnm + x, LM[0], LM[-1])
        rs.append(_interp_rows(GR[ia, iam], lx))
        cs.append(_interp_rows(GC[ia, iam], lx))
        q = np.full((nS, NN), wk / NN)
        if sel:
            q = q * _interp_rows(GG, lx)
        qs.append(q)
    r, c, Q = np.concatenate(rs, 1), np.concatenate(cs, 1), np.concatenate(qs, 1)
    if sel:
        Q = Q / Q.sum(1, keepdims=True) * 1.0
    return r, c, Q


def binned(r, Q, muP, sgP, lo, hi, stat="mean"):
    """Mean (or median) of sale/ask among closed deals whose SALE price is in [lo, hi), when ln(sale) ~
    N(muP, sgP) across closed deals and sale = ask * r, r independent of size (verified above)."""
    lr = np.log(r)
    El = (lr * Q).sum(1, keepdims=True)
    Vl = (((lr - El) ** 2) * Q).sum(1, keepdims=True)
    mua, sga = muP - El, np.sqrt(np.maximum(sgP ** 2 - Vl, 1e-6))
    w = Q * (stats.norm.cdf((np.log(hi) - lr - mua) / sga) - stats.norm.cdf((np.log(lo) - lr - mua) / sga))
    if stat == "mean":
        return (r * w).sum(1) / w.sum(1)
    return wquant(r, w, 0.5)


def wquant(r, Q, p):
    """weighted quantile of the atoms, row by row (mid-point CDF, linear between atoms)"""
    out = np.empty(r.shape[0])
    for i in range(r.shape[0]):
        o = np.argsort(r[i])
        x, w = r[i][o], Q[i][o]
        F = (np.cumsum(w) - w / 2) / w.sum()
        out[i] = np.interp(p, F, x)
    return out


def rom(r, Q, sga=1.1):
    """ln(median ask) - ln(median sale) over closed deals with ln(ask) ~ N(0, sga) (BizBuySell-like spread)."""
    lr = np.log(r)
    lo, hi = np.full(r.shape[0], -3.0), np.full(r.shape[0], 3.0)
    for _ in range(32):                                 # 6 / 2^32: far below the grid's own resolution
        mid = (lo + hi) / 2
        F = (stats.norm.cdf((mid[:, None] - lr) / sga) * Q).sum(1)
        lo, hi = np.where(F < 0.5, mid, lo), np.where(F < 0.5, hi, mid)
    return -(lo + hi) / 2


def basic(r, c, Q):
    o = {"Er": (r * Q).sum(1), "Elnr": (np.log(r) * Q).sum(1), "pi": (c * Q).sum(1)}
    o["below"] = (r * Q * (1 - c)).sum(1) / np.maximum((Q * (1 - c)).sum(1), 1e-12)
    return o


def solve_s(curve, target):
    """s on the grid where a moment curve (decreasing in s) equals target; linear interpolation.
    Returns (s, censored flag)."""
    v = np.asarray(curve) - target
    k = np.where(np.sign(v[:-1]) != np.sign(v[1:]))[0]
    if len(k) == 0:
        return (float(S_GRID[0]), True) if target > curve[0] else (float(S_GRID[-1]), True)
    k = k[0]
    return float(S_GRID[k] + (S_GRID[k + 1] - S_GRID[k]) * v[k] / (v[k] - v[k + 1])), False


def at_s(curve, s):
    return float(np.interp(s, S_GRID, curve))


# median-centred premium (reading M): m(s) with m * median(r(s, m)) = 1, by bisection on the grid
def mstar(ia=IA55, iam=IAM130, sd=0.0):
    lo, hi = np.full(nS, math.log(0.85)), np.full(nS, math.log(1.6))
    for _ in range(40):
        mid = (lo + hi) / 2
        r, c, Q = atoms(np.exp(mid), ia, iam, sd)
        f = mid + np.log(wquant(r, Q, 0.5))                # ln m + ln median(r): increasing in m
        lo, hi = np.where(f < 0, mid, lo), np.where(f < 0, hi, mid)
    return np.exp((lo + hi) / 2)


MSTAR = {(IA55, IAM130, 0.0): mstar()}
log("median-centred premium m(s) (reading M):", {float(s): round(float(m), 4) for s, m in zip(S_GRID[::8], MSTAR[(IA55, IAM130, 0.0)][::8])})

# ---- size distribution of CLOSED deals (sale price) ----
IB_EDGES = np.array([1.0, 5e5, 1e6, 2e6, 5e6, 5e7])


def fit_ibba_size(counts):
    def nll(p):
        cdf = stats.norm.cdf((np.log(IB_EDGES) - p[0]) / math.exp(p[1]))
        pr = np.diff(cdf)
        pr = pr / pr.sum()
        return -float(np.sum(counts * np.log(pr)))
    o = optimize.minimize(nll, [13.3, 0.4], method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-9})
    return float(o.x[0]), float(math.exp(o.x[1]))


SIZE_BBS = (math.log(BBS_MED), math.log(1e6 / BBS_MED) / stats.norm.ppf(1 - BBS_SH))
SIZE_IB = fit_ibba_size(IBC.mean().values)
log(f"IBBA closed-deal size: lognormal median ${math.exp(SIZE_IB[0]):,.0f}, sd(ln) {SIZE_IB[1]:.3f} (fitted to {len(IBC)} quarters of band counts); "
    f"BizBuySell: median ${BBS_MED:,.0f}, sd(ln) {SIZE_BBS[1]:.3f}")

# =====================================================================================
# 4. TARGETS, SPECIFICATIONS AND PER-SOURCE s
# =====================================================================================
Y_GE1M = float(GE1M.value.mean())
SE_GE1M = float(max(GE1M.value.std(ddof=1) / math.sqrt(len(GE1M)), 0.006))
SRC = [("bbs", "BizBuySell closed-deal cells 2016-18, deal-level mean sale/ask"),
       ("ib1", "IBBA Market Pulse under $500K, 27 quarters (binned by sale price)"),
       ("ib2", "IBBA Market Pulse $500K-1M, 27 quarters (binned by sale price)"),
       ("ibc", "IBBA Market Pulse under $1M as ONE source (bands weighted by closed deals, binned by sale price)"),
       ("ds", "DealStats ln(median ask / median sale), 12 half-years 2H2018-1H2024 (consistency: the model's ratio of medians at the source's own premium)")]
ALLKEYS = [k for k, _ in SRC]
KEYS = ["bbs", "ib1", "ib2"]                       # the primary structure (revision 2's k = 3)
LAB = dict(SRC + [("ge1m", "BizBuySell sales of $1M+, FY2018-Q2 2019 (binned by sale price; check)")])
# Source structures, carried in the model average with equal weights (the data cannot choose among them):
#   IBBA's two sub-$1M bands as two sources, or as one (their gap may be a size gradient, not between-source
#   heterogeneity); DealStats out, or in (Main-Street-sized private deals; its moment is a ratio of medians).
STRUCTS = {"S3: BizBuySell + IBBA two bands": ["bbs", "ib1", "ib2"],
           "S2: BizBuySell + IBBA under $1M as one": ["bbs", "ibc"],
           "S4: S3 + DealStats": ["bbs", "ib1", "ib2", "ds"],
           "S3b: S2 + DealStats": ["bbs", "ibc", "ds"]}
W_STRUCT = {k: 0.25 for k in STRUCTS}
PRIMARY_STRUCT = "S3: BizBuySell + IBBA two bands"


def targets(sec, ibw, ibc, ge1m, dvil=DVI_L):
    n1, n2 = float(ibc["<500K"].mean()), float(ibc["500K-1M"].mean())
    i1, i2 = float(ibw["<500K"].mean()), float(ibw["500K-1M"].mean())
    return {"bbs": wmean(sec.sale_to_ask_avg, sec.n_sales), "D": wmean(sec.lrm, sec.n_sales),
            "ib1": i1, "ib2": i2, "ib3": float(ibw["1M-2M"].mean()), "ibc": (i1 * n1 + i2 * n2) / (n1 + n2), "w_ib1": n1 / (n1 + n2),
            "ds": float(np.mean(dvil)), "ge1m": ge1m, "size_ib": fit_ibba_size(ibc.mean().values)}


T_HAT = targets(SEC, IBW, IBC, Y_GE1M)
log(f"IBBA under $1M as one source: {T_HAT['ibc']:.4f} (weight on the under-$500K band {T_HAT['w_ib1']:.3f}, from mean closed-deal counts)")


def cal_block_rows(T, L=4):
    """non-circular moving-block bootstrap on the calendar: each block is L consecutive calendar quarters (a
    missing quarter stays missing, so blocks next to a gap carry fewer rows), starts uniform over the span,
    no wrap-around; blocks are drawn until n rows are filled"""
    n = len(T)
    lo, hi = int(T.min()), int(T.max()) - L + 1
    out = []
    while len(out) < n:
        s0 = int(rng.integers(lo, hi + 1))
        out.extend(np.where((T >= s0) & (T < s0 + L))[0].tolist())
    return np.array(out[:n])


def boot_targets(B, sec=SEC, ibw=IBW, ibc=IBC, ibw_t=None, ibc_t=None):
    ibw_t = IBW_T if ibw_t is None else ibw_t
    ibc_t = IBC_T if ibc_t is None else ibc_t
    secs = sec.sector_h.unique()
    six = {s0: np.where(sec.sector_h.values == s0)[0] for s0 in secs}
    out = []
    for _ in range(B):
        pick = rng.choice(secs, len(secs))
        sec_b = sec.iloc[np.concatenate([six[s0] for s0 in pick])]
        ibw_b = ibw.iloc[cal_block_rows(ibw_t)]
        ibc_b = ibc.iloc[cal_block_rows(ibc_t)]
        dvi_b = rng.choice(DVI_L, len(DVI_L))
        out.append(targets(sec_b, ibw_b, ibc_b, float(rng.normal(Y_GE1M, SE_GE1M)), dvi_b))
    return out


TB = boot_targets(B_BOOT)
SE_T = {k: float(np.std([t[k] for t in TB], ddof=1)) for k in ["bbs", "D", "ib1", "ib2", "ib3", "ibc", "ds"]}
log(f"target bootstrap ({B_BOOT}: BizBuySell clustered by {SEC.sector_h.nunique()} harmonised sectors, IBBA quarters in calendar blocks of 4, "
    f"DealStats half-years iid): SE", {k: round(v, 4) for k, v in SE_T.items()})


def premium(T, read, d, ia=IA55, iam=IAM130, sd=0.0):
    """the model's (first-ask) premium for reading G / R / M: scalar, or one per s-row for M"""
    if read == "G":
        return math.exp(T["D"] + d + ELNR)
    if read == "R":
        return math.exp(T["D"] + d)
    key = (ia, iam, sd)
    if key not in MSTAR:
        MSTAR[key] = mstar(ia, iam, sd)
    return MSTAR[key]


def curves(T, read, d, ia=IA55, iam=IAM130, sd=0.0, sel=False, extra=False, ds=True):
    m = premium(T, read, d, ia, iam, sd)
    r, c, Q = atoms(m, ia, iam, sd, sel)
    o = basic(r, c, Q)
    mu, sg = T["size_ib"]
    o["ib1"] = binned(r, Q, mu, sg, *EDGES["<500K"])
    o["ib2"] = binned(r, Q, mu, sg, *EDGES["500K-1M"])
    o["ibc"] = binned(r, Q, mu, sg, 1.0, 1e6)
    o["bbs"] = o["Er"]
    if ds:
        # DealStats: the model's ln(median ask/median sale) at DealStats' OWN premium (its own D under readings G/R)
        r_d, c_d, Q_d = atoms(premium(dict(T, D=T["ds"]), read, d, ia, iam, sd), ia, iam, sd, sel)
        o["ds"] = rom(r_d, Q_d)
    if extra:
        for b in BANDS[2:]:
            o["ib_" + b] = binned(r, Q, mu, sg, *EDGES[b])
        o["ge1m"] = binned(r, Q, *SIZE_BBS, 1e6, 1e12)
        o["rom"] = rom(r, Q)
        o["q05"], o["q08"], o["q22"], o["q50"] = (wquant(r, Q, p) for p in (.05, .08, .22, .5))
        for b in ["<500K", "500K-1M", "1M-2M"]:
            o["pepmed_" + b] = binned(r, Q, mu, sg, *EDGES[b], stat="median")
    o["m"] = np.broadcast_to(np.asarray(m, float), (nS,)).copy()
    o["_atoms"] = (r, c, Q)
    return o


def fit_spec(T, read, d, ia=IA55, iam=IAM130, sd=0.0, sel=False, extra=False, keys=None):
    """per-source s on the model's (first-ask) basis: target * e^-d (sale/ask means) or D + d (ratio of medians)"""
    keys = keys or ALLKEYS
    o = curves(T, read, d, ia, iam, sd, sel, extra, ds=("ds" in keys))
    s = {}
    for k in keys:
        if k == "ds":                        # increasing in s: solve on the negated curve
            s[k] = solve_s(-o["ds"], -(T["ds"] + d))
        else:
            s[k] = solve_s(o[k], T[k] * math.exp(-d))
    if extra:
        s["ge1m"] = solve_s(o["ge1m"], T["ge1m"] * math.exp(-d))
    return s, o


ROM_FIT = {}
for read in ["G", "R", "M"]:
    for d in [0.0, D_MS]:
        s_, o_ = fit_spec(T_HAT, read, d, extra=True)
        sb = s_["bbs"][0]
        ROM_FIT[(read, d)] = at_s(o_["rom"], sb) - (T_HAT["D"] + d)
        log(f"  reading {read}, d={d:.4f}: m={o_['m'][0]:.4f}; s by source " + ", ".join(f"{k} {s_[k][0]:.3f}{'*' if s_[k][1] else ''}" for k in ALLKEYS)
            + f"; at s_bbs model ln(median ask/median sale) {at_s(o_['rom'], sb):.4f} vs data D+d {T_HAT['D'] + d:.4f} (miss {ROM_FIT[(read, d)]:+.4f})")
ROM_MISS_D0 = max(abs(ROM_FIT[(r_, 0.0)]) for r_ in "GRM")
ROM_MISS_DMS = max(abs(ROM_FIT[(r_, D_MS)]) for r_ in "GRM")

# =====================================================================================
# 5. POOLING ACROSS SOURCES (k = 2-4 by structure): DerSimonian-Laird, HKSJ, and a Bayesian random-effects model
# =====================================================================================
PRIOR_MU, PRIOR_SD = 1.0, 0.5          # the current model (s = 1), weakly held: it was a default, not a fit
TAU_PRIOR = ("half-normal", 0.5)


def dl_pool(est, var):
    est, var = np.asarray(est, float), np.asarray(var, float)
    w = 1 / var
    mu_f = np.sum(w * est) / np.sum(w)
    Q = float(np.sum(w * (est - mu_f) ** 2))
    k = len(est)
    tau2 = max(0.0, (Q - (k - 1)) / (np.sum(w) - np.sum(w ** 2) / np.sum(w)))
    ws = 1 / (var + tau2)
    mu = float(np.sum(ws * est) / np.sum(ws))
    se = float(math.sqrt(1 / np.sum(ws)))
    se_h = float(math.sqrt(np.sum(ws * (est - mu) ** 2) / ((k - 1) * np.sum(ws)))) if k > 1 else float("nan")
    tq = stats.t.ppf(0.975, k - 1) if k > 1 else float("nan")
    return {"mu": mu, "se": se, "tau": float(math.sqrt(tau2)), "Q": Q, "se_hksj": se_h,
            "ci95_hksj": (mu - tq * se_h, mu + tq * se_h), "ci90_hksj": (mu - stats.t.ppf(.95, k - 1) * se_h, mu + stats.t.ppf(.95, k - 1) * se_h),
            "p_s1_hksj": float(2 * stats.t.sf(abs(1 - mu) / se_h, k - 1)), "z_s1_dl": (1 - mu) / se}


MU_G = np.arange(-0.5, 2.5 + 1e-9, 0.0025)
TAU_G = np.arange(0.0, 1.5 + 1e-9, 0.0025)


def tau_logprior(kind=TAU_PRIOR):
    name, sc = kind
    if name == "half-normal":
        return -0.5 * (TAU_G / sc) ** 2
    if name == "half-cauchy":
        return -np.log1p((TAU_G / sc) ** 2)
    return np.zeros_like(TAU_G)                       # uniform on [0, 1.5]


def bayes_re(est, var, prior_mu=PRIOR_MU, prior_sd=PRIOR_SD, tau_prior=TAU_PRIOR):
    """posterior over (mu, tau) on a grid; returns the marginal density of mu and the joint for prediction"""
    est, var = np.asarray(est, float), np.asarray(var, float)
    V = var[None, :] + TAU_G[:, None] ** 2                          # (nT, k)
    ll = -0.5 * (np.log(V)[:, None, :] + (est[None, None, :] - MU_G[None, :, None]) ** 2 / V[:, None, :]).sum(2)   # (nT, nMu)
    lp = ll + tau_logprior(tau_prior)[:, None] - 0.5 * ((MU_G - prior_mu) / prior_sd) ** 2 if prior_sd else ll + tau_logprior(tau_prior)[:, None]
    P = np.exp(lp - lp.max())
    P /= P.sum()
    return {"joint": P, "mu": P.sum(0), "tau": P.sum(1)}


def summ(dens):
    dens = dens / dens.sum()
    mu = float((MU_G * dens).sum())
    sd = float(math.sqrt(((MU_G - mu) ** 2 * dens).sum()))
    cdf = np.cumsum(dens)
    q = lambda p: float(np.interp(p, cdf, MU_G))
    return {"mean": mu, "sd": sd, "q05": q(.05), "q50": q(.5), "q95": q(.95), "q025": q(.025), "q975": q(.975),
            "p_lt1": float(dens[MU_G < 1].sum())}


def pool(est, var):
    dl = dl_pool(est, var)
    by = bayes_re(est, var)
    return {"dl": dl, "bayes": by, "post": summ(by["mu"])}


def spec_run(read, d, sd=0.0, B=B_SPEC, ia=IA55, iam=IAM130, tb=None, T=None, keys=None):
    """per-source s and their bootstrap variances, then DL / HKSJ / Bayes pooling for every source structure.
    est/var/dl/bayes/post refer to the primary structure (k = 3); 'pool' holds every structure."""
    T = T or T_HAT
    keys = keys or ALLKEYS
    tb = tb if tb is not None else TB[:B]
    s0, o0 = fit_spec(T, read, d, ia, iam, sd, keys=keys)
    sb = np.array([[fit_spec(t, read, d, ia, iam, sd, keys=keys)[0][k][0] for k in keys] for t in tb])
    var_all = dict(zip(keys, sb.var(0, ddof=1)))
    est_all = {k: s0[k][0] for k in keys}
    cens_all = {k: s0[k][1] for k in keys}
    pools = {nm: pool([est_all[k] for k in ks], [var_all[k] for k in ks]) for nm, ks in STRUCTS.items() if all(k in keys for k in ks)}
    pr = pools[PRIMARY_STRUCT]
    return {"read": read, "d": d, "sd": sd, "est": np.array([est_all[k] for k in KEYS]), "var": np.array([var_all[k] for k in KEYS]),
            "cens": [cens_all[k] for k in KEYS], "est_all": est_all, "var_all": var_all, "cens_all": cens_all,
            "dl": pr["dl"], "bayes": pr["bayes"], "post": pr["post"], "pool": pools,
            "m": float(np.median(o0["m"])), "curves": o0, "boot": sb}


t_s = time.time()
PRIMARY = spec_run("G", D_MS, B=B_BOOT)
log(f"\n=== Main-street fit, primary specification (reading G, d = {D_MS:.4f}, ALPHA .55, AMAX 1.30, first-ask premium m = {PRIMARY['m']:.4f}) ===")
for k, e, v in zip(KEYS, PRIMARY["est"], PRIMARY["var"]):
    log(f"  s from {LAB[k]}: {e:.3f} (bootstrap SE {math.sqrt(v):.3f}); target {T_HAT[k]:.4f} on the data's ask, {T_HAT[k] * math.exp(-D_MS):.4f} on the first ask")
pdl, ppo = PRIMARY["dl"], PRIMARY["post"]
log(f"  DerSimonian-Laird: {pdl['mu']:.3f} (SE {pdl['se']:.3f}, tau {pdl['tau']:.3f}, Q {pdl['Q']:.1f} on 2 df; z for s=1 {pdl['z_s1_dl']:.2f})")
log(f"  HKSJ: SE {pdl['se_hksj']:.3f}; t(2) 95% CI {pdl['ci95_hksj'][0]:.2f} to {pdl['ci95_hksj'][1]:.2f}; 90% {pdl['ci90_hksj'][0]:.2f} to {pdl['ci90_hksj'][1]:.2f}; p(s=1) {pdl['p_s1_hksj']:.3f}")
log(f"  Bayesian RE (mu ~ N(1, 0.5^2), tau ~ {TAU_PRIOR}): posterior mean {ppo['mean']:.3f} sd {ppo['sd']:.3f}; 90% {ppo['q05']:.2f}-{ppo['q95']:.2f}; P(s<1) {ppo['p_lt1']:.3f}")
TAU_SENS = {}
for tp in [("half-normal", 0.25), ("half-cauchy", 0.25), ("uniform", 1.5)]:
    b_ = summ(bayes_re(PRIMARY["est"], PRIMARY["var"], tau_prior=tp)["mu"])
    TAU_SENS[tp] = b_
    log(f"    tau prior {tp}: mean {b_['mean']:.3f} sd {b_['sd']:.3f} 90% {b_['q05']:.2f}-{b_['q95']:.2f}")
b_ = summ(bayes_re(PRIMARY["est"], PRIMARY["var"], prior_sd=None)["mu"])
log(f"    flat prior on the mean: mean {b_['mean']:.3f} sd {b_['sd']:.3f} 90% {b_['q05']:.2f}-{b_['q95']:.2f}")
for k in ["ibc", "ds"]:
    tgt = f"target {T_HAT[k]:.4f} on the data's ask, {T_HAT[k] * math.exp(-D_MS):.4f} on the first ask" if k != "ds" else f"target D {T_HAT['ds']:.4f} + d"
    log(f"  s from {LAB[k]}: {PRIMARY['est_all'][k]:.3f}{'*' if PRIMARY['cens_all'][k] else ''} (bootstrap SE {math.sqrt(PRIMARY['var_all'][k]):.3f}); {tgt}")
log("  by source structure (primary readings):")
for nm, pp_ in PRIMARY["pool"].items():
    log(f"    {nm:42s}: DL {pp_['dl']['mu']:.3f} (tau {pp_['dl']['tau']:.3f}; HKSJ 95% {pp_['dl']['ci95_hksj'][0]:.2f} to {pp_['dl']['ci95_hksj'][1]:.2f}); "
        f"Bayes {pp_['post']['mean']:.3f} sd {pp_['post']['sd']:.3f}, 90% {pp_['post']['q05']:.2f}-{pp_['post']['q95']:.2f}, P(s<1) {pp_['post']['p_lt1']:.3f}")

# ---- specification table: ask reading (d) x premium reading, every source and structure ----
D_SENS = sorted({0.0, round(D_MS, 4), round(D_MS_CUTS, 4), round(D_EXCL, 4), round(D_UNTRIM, 4), 0.03, 0.05, round(-EF1.dl.mean(), 4)})
SPEC = {}
for read in ["G", "M", "R"]:
    for d in D_SENS:
        SPEC[(read, d)] = PRIMARY if (read == "G" and abs(d - D_MS) < 1e-4) else spec_run(read, d)
SNAME = {nm: nm.split(":")[0] for nm in STRUCTS}
rows = []
for (read, d), r_ in SPEC.items():
    row = {"reading": read, "d": d, "m_first_ask": r_["m"], **{f"s_{k}": r_["est_all"][k] for k in ALLKEYS},
           **{f"se_{k}": math.sqrt(r_["var_all"][k]) for k in ALLKEYS},
           "dl_mu": r_["dl"]["mu"], "dl_se": r_["dl"]["se"], "tau": r_["dl"]["tau"], "hksj_se": r_["dl"]["se_hksj"],
           "hksj_ci95_lo": r_["dl"]["ci95_hksj"][0], "hksj_ci95_hi": r_["dl"]["ci95_hksj"][1],
           "post_mean": r_["post"]["mean"], "post_sd": r_["post"]["sd"], "post_q05": r_["post"]["q05"], "post_q95": r_["post"]["q95"],
           "P_s_lt_1": r_["post"]["p_lt1"]}
    for nm, pp_ in r_["pool"].items():
        row[f"post_{SNAME[nm]}"] = pp_["post"]["mean"]
        row[f"P_lt1_{SNAME[nm]}"] = pp_["post"]["p_lt1"]
    rows.append(row)
SPECT = pd.DataFrame(rows).sort_values(["reading", "d"])
SPECT.to_csv(os.path.join(OUT, "spec_table.csv"), index=False)
log("\n=== FAN_S by ask reading d (model ask = data ask x e^d), premium reading and source structure (Bayesian RE posterior means) ===")
log(f"    d values: 0 (first-ask reading), {D_MS:.4f} (Main Street, |chg|<=0.5 zeroed), {D_EXCL:.4f} (jumps excluded), {D_MS_CUTS:.4f} (cuts only), "
    f"{D_UNTRIM:+.4f} (untrimmed: every recorded jump taken as real), 0.03, 0.05, {-EF1.dl.mean():.4f} (EF)")
with pd.option_context("display.width", 300, "display.max_columns", 40):
    log(SPECT[["reading", "d", "m_first_ask", "s_bbs", "s_ib1", "s_ib2", "s_ibc", "s_ds", "tau", "hksj_ci95_lo", "hksj_ci95_hi"]
              + [f"post_{v}" for v in SNAME.values()] + ["P_s_lt_1"]].round(3).to_string(index=False))

# ---- model average: source structure x premium reading x ask reading ----
W_READ = {"G": 0.4, "M": 0.4, "R": 0.2}          # R contradicts the fan's location (E ln(sale/V) = 0, not -0.039)
W_LAST = 0.75                                     # BizBuySell's ask is the listing record's (last) price; surveys unstated
gh_x, gh_w = np.polynomial.hermite_e.hermegauss(5)
gh_w = gh_w / gh_w.sum()
D_NODES = [(0.0, 1 - W_LAST)] + [(max(0.0, D_MS + SD_D * x), W_LAST * w) for x, w in zip(gh_x, gh_w)]
MIX = np.zeros_like(MU_G)
MIX_S = {nm: np.zeros_like(MU_G) for nm in STRUCTS}
MIX_EQ = np.zeros_like(MU_G)                      # equal premium-reading weights (sensitivity)
MIXROWS = []
for read, wr in W_READ.items():
    for d, wd in D_NODES:
        key = (read, round(d, 6))
        if key not in SPEC:
            SPEC[key] = spec_run(read, d)
        for nm, ws in W_STRUCT.items():
            dens = SPEC[key]["pool"][nm]["bayes"]["mu"]
            dens = dens / dens.sum()
            MIX += ws * wr * wd * dens
            MIX_S[nm] += wr * wd * dens
            MIX_EQ += ws * wd * dens / 3.0
            MIXROWS.append((nm, read, d, ws * wr * wd, SPEC[key]["pool"][nm]["post"]["mean"]))
POST = summ(MIX)
POST_S = {nm: summ(v) for nm, v in MIX_S.items()}
POST_EQ = summ(MIX_EQ)
POST_PRIMARY_STRUCT = POST_S[PRIMARY_STRUCT]


def wavg(pred):
    sel_ = [(w, m) for nm, r_, d, w, m in MIXROWS if pred(nm, r_, d)]
    return sum(w * m for w, m in sel_) / sum(w for w, m in sel_)


by_read = {rd: wavg(lambda nm, r_, d, rd=rd: r_ == rd) for rd in W_READ}
by_ask = {"first-ask reading (d=0)": wavg(lambda nm, r_, d: d == 0), "last-ask reading": wavg(lambda nm, r_, d: d > 0)}
by_struct = {nm: wavg(lambda nm_, r_, d, nm=nm: nm_ == nm) for nm in STRUCTS}
log(f"\nmodel-averaged posterior of FAN_S (structures {list(W_STRUCT.values())}; premium readings {W_READ}; last-ask reading weight {W_LAST} with "
    f"d ~ N({D_MS:.4f}, {SD_D:.4f}^2), first-ask reading weight {1 - W_LAST:.2f}): mean {POST['mean']:.3f} sd {POST['sd']:.3f}; "
    f"90% {POST['q05']:.2f}-{POST['q95']:.2f}; 95% {POST['q025']:.2f}-{POST['q975']:.2f}; P(s<1) {POST['p_lt1']:.3f} (under the narrowing reading)")
for nm, ps_ in POST_S.items():
    log(f"  structure {nm:42s}: mean {ps_['mean']:.3f} sd {ps_['sd']:.3f}, 90% {ps_['q05']:.2f}-{ps_['q95']:.2f}, P(s<1) {ps_['p_lt1']:.3f}")
log("  component means by premium reading:", {k: round(v, 3) for k, v in by_read.items()}, "| by ask reading:", {k: round(v, 3) for k, v in by_ask.items()})
log(f"  equal premium-reading weights: mean {POST_EQ['mean']:.3f} (sd {POST_EQ['sd']:.3f}); revision 2's structure alone {POST_PRIMARY_STRUCT['mean']:.3f}")
log(f"  spec runs took {time.time() - t_s:.0f}s")

R05 = lambda x: round(round(x / 0.05) * 0.05, 2)
FAN_S_REC = R05(POST["mean"])       # rounded to 0.05: the data do not support two decimals
ALT_VALUES = {**{f"structure {SNAME[nm]}": ps_["mean"] for nm, ps_ in POST_S.items()}, "equal reading weights": POST_EQ["mean"],
              **{f"reading {k} only": v for k, v in by_read.items()}}
SPEC_LO = min(R05(v) for k, v in ALT_VALUES.items() if not k.startswith("reading"))
SPEC_HI = max(R05(v) for k, v in ALT_VALUES.items() if not k.startswith("reading"))
P_LT1_RANGE = (min(ps_["p_lt1"] for ps_ in POST_S.values()), max(ps_["p_lt1"] for ps_ in POST_S.values()))
CUT_DIST = min(abs(POST["mean"] - (FAN_S_REC - 0.025)), abs(POST["mean"] - (FAN_S_REC + 0.025)))
log(f"  recommended FAN_S = {FAN_S_REC:.2f} (posterior mean {POST['mean']:.3f} rounded to 0.05; {CUT_DIST:.3f} from the nearest rounding cut); "
    f"specification range {SPEC_LO:.2f}-{SPEC_HI:.2f} (structures and reading weights, each rounded); P(s<1) by structure "
    f"{P_LT1_RANGE[0]:.2f}-{P_LT1_RANGE[1]:.2f}")

# ---- sensitivity: premiums spread across sold listings as PRICING NOISE (ln premium ~ N(ln m, sd^2), independent of W) ----
HET = {}
for sd_ in [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]:
    rr_ = spec_run("G", D_MS, sd=sd_, B=200, keys=KEYS)
    HET[sd_] = (rr_["post"]["mean"], [round(float(x), 3) for x in rr_["est"]], any(rr_["cens"]), rr_["post"]["sd"])
log("  premium dispersion across listings as pricing noise (primary spec): posterior mean of s by sd of ln premium:",
    {k: (round(v[0], 3), v[1], "censored" if v[2] else "") for k, v in HET.items()}, f"vs {PRIMARY['post']['mean']:.3f} at sd 0")
# How much of the premium dispersion is noise? EF analog: pass-through b of ln ask into ln sale given the hedonic value. With
# information passing through at 1 and noise at the model's ALPHA, the noise share of the premium variance is (1-b)/(1-ALPHA).
_b, _se = EF_PAR["tobit"]
NOISE_F = float(np.clip((1 - _b) / (1 - 0.55), 0, 1))
NOISE_F_HI = float(np.clip((1 - (_b - 1.96 * _se)) / (1 - 0.55), 0, 1))
NOISE_SD, NOISE_SD_HI = math.sqrt(NOISE_F) * EF_SD_RHOW, math.sqrt(NOISE_F_HI) * EF_SD_RHOW
log(f"  EF analog: pass-through {_b:.3f} (SE {_se:.3f}) -> noise share of the premium variance {NOISE_F:.3f} (95% upper {NOISE_F_HI:.3f}) -> noise sd "
    f"{NOISE_SD:.3f} (upper {NOISE_SD_HI:.3f}) of EF's {EF_SD_RHOW:.3f}; Main-Street asks may be noisier, so the dispersion row is a conditional, not a weight")
CENS_SD = min([k for k, v in HET.items() if v[2]] or [float("nan")])
S_AT_SD = lambda sd_: float(np.interp(sd_, [0.0] + list(HET), [PRIMARY["post"]["mean"]] + [v[0] for v in HET.values()]))
# sensitivity: IBBA bands defined by the ASK rather than the sale price (no binning on the outcome)
o_u = PRIMARY["curves"]
S_UNB = [PRIMARY["est"][0], solve_s(o_u["Er"], T_HAT["ib1"] * math.exp(-D_MS))[0], solve_s(o_u["Er"], T_HAT["ib2"] * math.exp(-D_MS))[0]]
UNB = summ(bayes_re(S_UNB, PRIMARY["var"])["mu"])
log(f"  IBBA bands read as ask-defined (unbinned): s = {S_UNB[1]:.3f} / {S_UNB[2]:.3f}; posterior mean {UNB['mean']:.3f} vs {PRIMARY['post']['mean']:.3f} binned")
# sensitivity: IBBA band means weighted by each quarter's closed deals (the 16 quarters with counts)
_ibw16 = IBW.loc[IBC.index]
T_DW = dict(T_HAT, ib1=float(np.average(_ibw16["<500K"], weights=IBC["<500K"])), ib2=float(np.average(_ibw16["500K-1M"], weights=IBC["500K-1M"])))
_s_dw, _ = fit_spec(T_DW, "G", D_MS, keys=KEYS)
DW = summ(bayes_re([_s_dw[k][0] for k in KEYS], PRIMARY["var"])["mu"])
log(f"  IBBA quarters deal-weighted ({len(IBC)} quarters with counts): targets {T_DW['ib1']:.4f} / {T_DW['ib2']:.4f}; s {_s_dw['ib1'][0]:.3f} / {_s_dw['ib2'][0]:.3f}; "
    f"posterior mean {DW['mean']:.3f}")
# sensitivity: calibrate to the 2022+ market level instead of the 2016-2026 average
TE22 = [p for p in IBW.index if p >= "2022Q1"]
IBC22 = IBC.loc[[q for q in IBC.index if q >= "2022Q1"]]
_h22 = [x for x in pairs if x[0] in ("2022Q2", "2023Q3")]
D22 = float(np.mean([math.log(x[1]) for x in _h22]))
SEC22 = SEC.copy()
T22 = targets(SEC22, IBW.loc[TE22], IBC22, Y_GE1M)
T22.update(bbs=BBS25, D=D22)
TB22 = boot_targets(200, SEC22, IBW.loc[TE22], IBC22, np.array([qidx(p) for p in TE22]), np.array([qidx(p) for p in IBC22.index]))
for t_ in TB22:
    t_["bbs"] = t_["bbs"] - T_HAT["bbs"] + BBS25                  # BizBuySell 2025 is one national figure: keep the 2016-18 cell spread
    t_["D"] = t_["D"] - T_HAT["D"] + D22
RUN22 = spec_run("G", D_MS, T=T22, tb=TB22, keys=KEYS)
log(f"  calibrated to the 2022+ level (IBBA {len(TE22)} quarters 2022Q1-2026Q2: {T22['ib1']:.4f} / {T22['ib2']:.4f}; BizBuySell 2025 {BBS25:.3f}; "
    f"D from the 2022Q2/2023Q3 headline pairs {D22:.4f}): s by source {', '.join(f'{x:.3f}' for x in RUN22['est'])}; posterior mean "
    f"{RUN22['post']['mean']:.3f} (sd {RUN22['post']['sd']:.3f}) vs {PRIMARY['post']['mean']:.3f} for 2016-2026")

# =====================================================================================
# 6. OUT-OF-SAMPLE VALIDATION (primary specification: reading G, d = D_MS)
# =====================================================================================
log("\n=== Validation (primary specification; model predictions put back on the data's ask by e^d) ===")
ED = math.exp(D_MS)
S_P, MO = fit_spec(T_HAT, "G", D_MS, extra=True)
M_TYP = float(MO["m"][0])                                   # the typical FIRST-ask premium over V
ROWS = []

# ---- 6a. leave one source out: tau from the two training sources only ----
LOSO = {}
for i, k in enumerate(KEYS):
    tr = [j for j in range(3) if j != i]
    est, var = PRIMARY["est"][tr], PRIMARY["var"][tr]
    dl = dl_pool(est, var)
    cur = MO[k]
    obs = T_HAT[k] * math.exp(-D_MS)
    pred = at_s(cur, dl["mu"])
    slope = (at_s(cur, dl["mu"] + 0.01) - at_s(cur, dl["mu"] - 0.01)) / 0.02
    z_train = (pred - obs) / (abs(slope) * math.sqrt(dl["se"] ** 2 + dl["tau"] ** 2 + PRIMARY["var"][i]))
    z_full = (pred - obs) / (abs(slope) * math.sqrt(dl["se"] ** 2 + PRIMARY["dl"]["tau"] ** 2 + PRIMARY["var"][i]))
    # Bayesian posterior predictive from the two training sources (same priors)
    by = bayes_re(est, var)
    J = by["joint"].ravel()
    idx = rng.choice(J.size, 20000, p=J / J.sum())
    mu_d, tau_d = MU_G[idx % len(MU_G)], TAU_G[idx // len(MU_G)]
    s_new = mu_d + rng.normal(0, 1, len(idx)) * np.sqrt(tau_d ** 2 + PRIMARY["var"][i])
    y_new = np.interp(np.clip(s_new, S_GRID[0], S_GRID[-1]), S_GRID, cur)
    z_b = (float(y_new.mean()) - obs) / float(y_new.std())
    p_tail = float(min((y_new <= obs).mean(), (y_new >= obs).mean()))
    LOSO[k] = {"pred_dl": pred * ED, "obs": T_HAT[k], "z_train_tau": z_train, "z_full_tau": z_full, "s_train": dl["mu"], "tau_train": dl["tau"],
               "pred_bayes": float(y_new.mean()) * ED, "sd_bayes": float(y_new.std()) * ED, "z_bayes": z_b, "p_tail_bayes": p_tail}
    ROWS.append({"check": "leave-one-source-out", "target": LAB[k], "observed": T_HAT[k], "model_fitted": pred * ED,
                 "model_current_s1": at_s(cur, 1.0) * ED, "s_used": dl["mu"], "error": pred * ED - T_HAT[k], "z": z_train,
                 "note": f"tau from the training sources {dl['tau']:.3f}; z with the full-sample tau {z_full:+.2f}; Bayesian predictive "
                         f"{y_new.mean() * ED:.4f} sd {y_new.std() * ED:.4f}, z {z_b:+.2f}, one-sided tail p {p_tail:.3f}"})
    log(f"  LOSO {k}: s from the others {dl['mu']:.3f} (training tau {dl['tau']:.3f}) -> predicts {pred * ED:.4f} vs {T_HAT[k]:.4f}; "
        f"z {z_train:+.2f} (with full-sample tau {z_full:+.2f}); Bayesian predictive {y_new.mean() * ED:.4f} +- {y_new.std() * ED:.4f}, "
        f"z {z_b:+.2f}, tail p {p_tail:.3f}; current s=1 {at_s(cur, 1.0) * ED:.4f}")

# ---- 6a'. BizBuySell left out WITHOUT its own D: the shared premium comes from BizBuySell's headline ratio of
#      medians in OTHER periods (2012, 2019, 2022-23), so the held-out mean is not coupled to the training premium ----
_oth = [x for x in pairs if x[0] not in ("FY2016", "Q1 2017", "Q1 2018", "2018")]
D_OTHER = float(np.mean([math.log(x[1]) for x in _oth]))
T_OTH = dict(T_HAT, D=D_OTHER)
RUN_OTH = spec_run("G", D_MS, T=T_OTH, tb=[dict(t, D=t["D"] - T_HAT["D"] + D_OTHER) for t in TB[:200]], keys=KEYS)
_dl_o = dl_pool(RUN_OTH["est"][1:], RUN_OTH["var"][1:])
_cur_o = RUN_OTH["curves"]["Er"]
_pred_o = at_s(_cur_o, _dl_o["mu"])
_slope_o = (at_s(_cur_o, _dl_o["mu"] + 0.01) - at_s(_cur_o, _dl_o["mu"] - 0.01)) / 0.02
_obs_o = T_HAT["bbs"] * math.exp(-D_MS)
Z_OTH = (_pred_o - _obs_o) / (abs(_slope_o) * math.sqrt(_dl_o["se"] ** 2 + _dl_o["tau"] ** 2 + RUN_OTH["var"][0]))
LOSO["bbs_otherD"] = {"pred_dl": _pred_o * ED, "obs": T_HAT["bbs"], "z_train_tau": Z_OTH, "s_train": _dl_o["mu"], "D_other": D_OTHER,
                      "periods": [x[0] for x in _oth], "m": RUN_OTH["m"]}
ROWS.append({"check": "leave-one-source-out", "target": LAB["bbs"] + " (premium from BizBuySell's other-period D)", "observed": T_HAT["bbs"],
             "model_fitted": _pred_o * ED, "model_current_s1": at_s(_cur_o, 1.0) * ED, "s_used": _dl_o["mu"], "error": _pred_o * ED - T_HAT["bbs"],
             "z": Z_OTH, "note": f"D {D_OTHER:.4f} from {[x[0] for x in _oth]} (same platform, other periods): partly independent"})
log(f"  LOSO bbs with the premium from BizBuySell's OTHER-period D ({D_OTHER:.4f}, {[x[0] for x in _oth]}; m {RUN_OTH['m']:.4f}): IBBA s "
    f"{RUN_OTH['est'][1]:.3f} / {RUN_OTH['est'][2]:.3f} -> pooled {_dl_o['mu']:.3f} (tau {_dl_o['tau']:.3f}) -> predicts {_pred_o * ED:.4f} vs {T_HAT['bbs']:.4f}, "
    f"z {Z_OTH:+.2f} (the cell-D version above shares BizBuySell's own D and is not independent)")
# ---- 6a''. DealStats left out: predict its ratio of medians from the three sale/ask sources (structure S4) ----
_cur_ds = PRIMARY["curves"]["ds"]
_mu3 = PRIMARY["dl"]["mu"]
_pred_ds = at_s(_cur_ds, _mu3) - D_MS
_slope_ds = (at_s(_cur_ds, _mu3 + 0.01) - at_s(_cur_ds, _mu3 - 0.01)) / 0.02
Z_DS = (_pred_ds - T_HAT["ds"]) / (abs(_slope_ds) * math.sqrt(PRIMARY["dl"]["se"] ** 2 + PRIMARY["dl"]["tau"] ** 2 + PRIMARY["var_all"]["ds"]))
LOSO["ds"] = {"pred": _pred_ds, "obs": T_HAT["ds"], "z": Z_DS, "s_train": _mu3, "s_own": PRIMARY["est_all"]["ds"]}
ROWS.append({"check": "leave-one-source-out", "target": LAB["ds"], "observed": T_HAT["ds"], "model_fitted": _pred_ds,
             "model_current_s1": at_s(_cur_ds, 1.0) - D_MS, "s_used": _mu3, "error": _pred_ds - T_HAT["ds"], "z": Z_DS,
             "note": f"ratio of medians at DealStats' own premium; its own s {PRIMARY['est_all']['ds']:.3f}"})
log(f"  LOSO DealStats: s from the three sale/ask sources {_mu3:.3f} -> ln(median ask/median sale) {_pred_ds:.4f} vs {T_HAT['ds']:.4f}, z {Z_DS:+.2f} "
    f"(DealStats' own s {PRIMARY['est_all']['ds']:.3f}, SE {math.sqrt(PRIMARY['var_all']['ds']):.3f})")

# ---- 6b. held-out targets never used in the fit (at FAN_S_REC, typical premium) ----
HELD = []
for b, note in [("1M-2M", "held out: ask or benchmark"), ("2M-5M", "BENCHMARK, not ask (reference only)"),
                ("5M-50M", "BENCHMARK, not ask (reference only)")]:
    HELD.append(("IBBA " + b + " mean, 27 quarters", float(IBW[b].mean()), MO["ib_" + b] * ED, note))
HELD.append(("BizBuySell $1M+ mean (sale-binned)", Y_GE1M, MO["ge1m"] * ED, "check: needs a size effect"))
for b in ["<500K", "500K-1M", "1M-2M"]:
    HELD.append((f"Pepperdine 2016 band MEDIAN read literally, {b}", PEP16[b], MO["pepmed_" + b] * ED, f"held out; 2015 deals; Fig 98, PDF p.{PEP_PAGE}; respondent n not reported"))
for b, kk in [("<500K", "ib1"), ("500K-1M", "ib2"), ("1M-2M", "ib_1M-2M")]:
    HELD.append((f"Pepperdine 2016 respondent median read as a band mean, {b}", PEP16[b], MO[kk] * ED, "held out; respondents' answers are their own averages"))
HELD.append(("BizBuySell 2025 national mean", BBS25, MO["Er"] * ED, "held out (later year)"))
HELD.append(("DealStats ln(median ask/median sale), 2H2018-1H2024, at the Main-Street premium", DVI_RM, MO["rom"] - D_MS, "check: at BizBuySell's premium; DealStats' own premium is used where it is a source (S4, S3b)"))
for lab, obs, curve, note in HELD:
    f_, c1 = at_s(curve, FAN_S_REC), at_s(curve, 1.0)
    ROWS.append({"check": "held-out", "target": lab, "observed": obs, "model_fitted": f_, "model_current_s1": c1,
                 "s_used": FAN_S_REC, "error": f_ - obs, "z": np.nan, "note": note})
    log(f"  held-out {lab}: observed {obs:.4f}  model at FAN_S {f_:.4f}  current model {c1:.4f}   [{note}]")
HV = {r["target"]: r for r in ROWS if r["check"] == "held-out"}
pep_lit = [HV[f"Pepperdine 2016 band MEDIAN read literally, {b}"] for b in ["<500K", "500K-1M", "1M-2M"]]
pep_mean = [HV[f"Pepperdine 2016 respondent median read as a band mean, {b}"] for b in ["<500K", "500K-1M", "1M-2M"]]
PEP_RMSE = {nm: (math.sqrt(np.mean([(r["model_fitted"] - r["observed"]) ** 2 for r in rr])),
                 math.sqrt(np.mean([(r["model_current_s1"] - r["observed"]) ** 2 for r in rr]))) for nm, rr in [("literal medians", pep_lit), ("as means", pep_mean)]}
log("  Pepperdine RMSE (fitted, current):", {k: (round(v[0], 4), round(v[1], 4)) for k, v in PEP_RMSE.items()})

# ---- 6c. temporal holdout: fit on data to 2021 (variances from the training data), predict 2022-2026 ----
TR = [p for p in IBW.index if p <= "2021Q4"]
TE = [p for p in IBW.index if p >= "2022Q1"]
IBC_TR = IBC.loc[[q for q in IBC.index if q <= "2021Q4"]] if sum(q <= "2021Q4" for q in IBC.index) >= 3 else IBC
T_tr = targets(SEC, IBW.loc[TR], IBC_TR, Y_GE1M)
TB_tr = boot_targets(B_SPEC, SEC, IBW.loc[TR], IBC_TR, np.array([qidx(p) for p in TR]), np.array([qidx(p) for p in IBC_TR.index]))
RUN_TR = spec_run("G", D_MS, T=T_tr, tb=TB_tr, keys=KEYS)
mu_tr = RUN_TR["post"]["mean"]
mo_tr = RUN_TR["curves"]
_, mo_tr_x = fit_spec(T_tr, "G", D_MS, extra=True)
test = [("IBBA <500K 2022-26", float(IBW.loc[TE, "<500K"].mean()), "ib1", float(IBW.loc[TR, "<500K"].mean())),
        ("IBBA 500K-1M 2022-26", float(IBW.loc[TE, "500K-1M"].mean()), "ib2", float(IBW.loc[TR, "500K-1M"].mean())),
        ("IBBA 1M-2M 2022-26", float(IBW.loc[TE, "1M-2M"].mean()), "ib_1M-2M", float(IBW.loc[TR, "1M-2M"].mean())),
        ("BizBuySell 2025 mean", BBS25, "Er", T_tr["bbs"])]
one_level = float(np.mean([T_tr["bbs"], T_tr["ib1"], T_tr["ib2"]]))
err = {"fitted model (1 parameter, s)": [], "current model (s=1)": [], "naive: one pooled level": [], "naive: per-target training mean": []}
for lab, obs, key, trmean in test:
    f_, c1 = at_s(mo_tr_x[key], mu_tr) * ED, at_s(mo_tr_x[key], 1.0) * ED
    err["fitted model (1 parameter, s)"].append(f_ - obs)
    err["current model (s=1)"].append(c1 - obs)
    err["naive: one pooled level"].append(one_level - obs)
    err["naive: per-target training mean"].append(trmean - obs)
    ROWS.append({"check": "temporal holdout (fit <=2021)", "target": lab, "observed": obs, "model_fitted": f_, "model_current_s1": c1,
                 "s_used": mu_tr, "error": f_ - obs, "z": np.nan, "note": f"naive per-target {trmean:.4f}; one level {one_level:.4f}"})
TEMP_RMSE = {k: float(np.sqrt(np.mean(np.square(v)))) for k, v in err.items()}
qerr = {"fitted": [], "current": [], "naive per band": [], "naive one level": []}
for q in TE:
    for b, key in [("<500K", "ib1"), ("500K-1M", "ib2"), ("1M-2M", "ib_1M-2M")]:
        o = IBW.loc[q, b]
        qerr["fitted"].append(at_s(mo_tr_x[key], mu_tr) * ED - o)
        qerr["current"].append(at_s(mo_tr_x[key], 1.0) * ED - o)
        qerr["naive per band"].append(IBW.loc[TR, b].mean() - o)
        qerr["naive one level"].append(one_level - o)
TEMP_Q = {k: float(np.sqrt(np.mean(np.square(v)))) for k, v in qerr.items()}
log(f"  temporal holdout: trained on {len(TR)} IBBA quarters to 2021Q4 + BizBuySell 2016-18 (variances from {B_SPEC} training-only replicates) "
    f"-> s = {mu_tr:.3f} (per source {', '.join(f'{x:.2f}' for x in RUN_TR['est'])}); tested on {len(TE)} quarters 2022Q1-2026Q2 and BizBuySell 2025")
log("    RMSE of the four test means:", {k: round(v, 4) for k, v in TEMP_RMSE.items()})
log(f"    RMSE over {len(qerr['fitted'])} test quarter-bands:", {k: round(v, 4) for k, v in TEMP_Q.items()})

# ---- 6d. DealStats as a source (reading G: m from its own D; the same estimate enters structures S4 and S3b) ----
D_DS = DVI_RM
s_ds, SE_S_DS = PRIMARY["est_all"]["ds"], math.sqrt(PRIMARY["var_all"]["ds"])
DS_BY_READ = {rd: (SPEC[(rd, round(D_MS, 4))] if (rd, round(D_MS, 4)) in SPEC else PRIMARY)["est_all"]["ds"] for rd in "GMR"}
log(f"  DealStats estimate (reading G): D = {D_DS:.4f} -> premium {math.exp(D_DS + D_MS + ELNR):.3f}, s = {s_ds:.3f} (SE {SE_S_DS:.3f}); by premium reading "
    f"{ {k: round(v, 3) for k, v in DS_BY_READ.items()} }; at the Main Street premium the model at FAN_S gives D = {at_s(MO['rom'], FAN_S_REC) - D_MS:.4f} "
    f"vs DealStats {D_DS:.4f} (current model {at_s(MO['rom'], 1.0) - D_MS:.4f})")

# =====================================================================================
# 7. EMPIRE FLIPPERS PER-DEAL ANALOG (online businesses; last ask AND reconstructed first ask)
# =====================================================================================
log("\n=== Empire Flippers analog ===")
QS = [0.05, 0.08, 0.10, 0.25, 0.50, 0.75, 0.90]


def ef_stats(rr):
    rr = np.asarray(rr, float)
    at = rr >= 0.9999
    o = {"n": len(rr), "Er": float(rr.mean()), "Elnr": float(np.log(rr).mean()), "pi": float(at.mean()), "below": float(rr[~at].mean())}
    for q in QS:
        o[f"q{int(q * 100):02d}"] = float(np.quantile(rr, q))
    return o


def model_at(m, s, sel=False):
    r, c, Q = atoms(m, sel=sel)
    o = basic(r, c, Q)
    out = {k: at_s(v, s) for k, v in o.items()}
    for q in QS:
        out[f"q{int(q * 100):02d}"] = at_s(wquant(r, Q, q), s)
    return out


def ef_fit(st, m):
    r, c, Q = atoms(m)
    s = solve_s(np.log(r).__mul__(Q).sum(1), st["Elnr"])[0]
    return s, model_at(m, s)


EF_ALL = ef_stats(ef.r)
M_EF = math.exp(EF_RHOW)                 # = exp(-E[ln r]): EF's hedonic is OLS, so its V is the geometric mean: READING R by construction
S_EF, PRED_EF = ef_fit(EF_ALL, M_EF)
AT_FAN_EF = model_at(M_EF, FAN_S_REC)
AT_1_EF = model_at(M_EF, 1.0)
# READING G (comparable with the Main-Street primary): V is the fan median, so ln V = ln(geometric mean) - E[ln R]
M_EF_G = math.exp(EF_RHOW + ELNR)
S_EF_G, PRED_EF_G = ef_fit(EF_ALL, M_EF_G)
AT_FAN_EF_G = model_at(M_EF_G, FAN_S_REC)
AT_1_EF_G = model_at(M_EF_G, 1.0)
months = ef.month.unique()
midx = {mm: np.where(ef.month.values == mm)[0] for mm in months}
efb = []
for _ in range(300):
    ii = np.concatenate([midx[mm] for mm in rng.choice(months, len(months))])
    st = ef_stats(ef.r.values[ii])
    sb_, pb_ = ef_fit(st, math.exp(-st["Elnr"]))
    sg_, _ = ef_fit(st, math.exp(-st["Elnr"] + ELNR))
    efb.append({"s": sb_, "s_G": sg_, "pi": st["pi"], "below": st["below"], "Er": st["Er"], "q05": st["q05"], "q08": st["q08"],
                "dpi": pb_["pi"] - st["pi"], "dbelow": pb_["below"] - st["below"]})
efb = pd.DataFrame(efb)
SE_EF = efb.std(ddof=1).to_dict()
log(f"  last ask (n={EF_ALL['n']}): reading R (EF's hedonic V is a geometric mean) premium {M_EF:.4f}, s fitted on E[ln r] alone {S_EF:.3f} "
    f"(month-cluster SE {SE_EF['s']:.3f}); reading G premium {M_EF_G:.4f}, s {S_EF_G:.3f} (SE {SE_EF['s_G']:.3f}) <- comparable with the Main-Street primary")
log(f"  reading G at s_EF_G: E r {PRED_EF_G['Er']:.4f}, point mass {PRED_EF_G['pi']:.4f}, below-ask mean {PRED_EF_G['below']:.4f}, q05 {PRED_EF_G['q05']:.4f}, "
    f"q08 {PRED_EF_G['q08']:.4f}; at FAN_S: {AT_FAN_EF_G['Er']:.4f} / {AT_FAN_EF_G['pi']:.4f} / {AT_FAN_EF_G['below']:.4f} / q08 {AT_FAN_EF_G['q08']:.4f}; "
    f"s=1: {AT_1_EF_G['Er']:.4f} / {AT_1_EF_G['pi']:.4f} / {AT_1_EF_G['below']:.4f} / q08 {AT_1_EF_G['q08']:.4f}")
log(f"  {'stat':6s} {'observed':>9s} {'(SE)':>7s} {'s_EF':>7s} {'FAN_S':>7s} {'s=1':>7s}")
for k in ["Er", "pi", "below", "q05", "q08", "q10", "q50"]:
    log(f"  {k:6s} {EF_ALL[k]:9.4f} {('(%.4f)' % SE_EF[k]) if k in SE_EF else '':>7s} {PRED_EF[k]:7.4f} {AT_FAN_EF[k]:7.4f} {AT_1_EF[k]:7.4f}")
log(f"  at s_EF: point mass {PRED_EF['pi'] - EF_ALL['pi']:+.3f} (SE {SE_EF['dpi']:.3f}), below-ask mean {PRED_EF['below'] - EF_ALL['below']:+.4f} "
    f"(SE {SE_EF['dbelow']:.4f}, z {(PRED_EF['below'] - EF_ALL['below']) / SE_EF['dbelow']:+.1f}); the model's point mass moves in steps of 1/48 = 0.021")

# first ask: the same 1,754 deals on the last and on the first ask
EFS = {}
for nm, sub in [("all with a first ask", EF1), ("not re-based", EF1[~EF1.rebased]), ("re-based", EF1[EF1.rebased])]:
    st_l, st_f = ef_stats(sub.r), ef_stats(sub.r1)
    m_l, m_f = math.exp(sub.rhoW.mean()), math.exp((sub.rhoW - sub.dl).mean())
    s_l, p_l = ef_fit(st_l, m_l)
    s_f, p_f = ef_fit(st_f, m_f)
    s_lG, _ = ef_fit(st_l, m_l * math.exp(ELNR))
    s_fG, _ = ef_fit(st_f, m_f * math.exp(ELNR))
    EFS[nm] = {"n": len(sub), "d": float(-sub.dl.mean()), "m_last": m_l, "m_first": m_f, "s_last": s_l, "s_first": s_f, "s_last_G": s_lG, "s_first_G": s_fG,
               "obs_last": st_l, "obs_first": st_f, "pred_last": p_l, "pred_first": p_f, "fan_first": model_at(m_f, FAN_S_REC),
               "cut_share": float((sub.dl < -0.03).mean()), "raise_share": float((sub.dl > 0.03).mean())}
    log(f"  {nm} (n={len(sub)}): d = mean ln(first/last) {EFS[nm]['d']:+.4f} (cut {EFS[nm]['cut_share']:.0%}, raised {EFS[nm]['raise_share']:.0%}); "
        f"LAST ask: premium {m_l:.3f}, s {s_l:.3f}, E r {st_l['Er']:.3f}, point mass {st_l['pi']:.3f} (model {p_l['pi']:.3f}); "
        f"FIRST ask: premium {m_f:.3f}, s {s_f:.3f}, E r {st_f['Er']:.3f}, point mass {st_f['pi']:.3f} (model {p_f['pi']:.3f}), "
        f"below-ask mean {st_f['below']:.3f} (model {p_f['below']:.3f}), q05 {st_f['q05']:.3f} (model {p_f['q05']:.3f}) [reading R]; reading G: s last {s_lG:.3f}, first {s_fG:.3f}")
E_ALL1 = EFS["all with a first ask"]
DS_DD_EF = (E_ALL1["s_first"] - E_ALL1["s_last"]) / E_ALL1["d"]
log(f"  EF: s rises {DS_DD_EF:.2f} per unit of d (first vs last ask on the same deals); Main Street d {D_MS:.4f} would move s by {DS_DD_EF * D_MS:+.3f} "
    f"on EF's scale; the Main-Street spec table gives {float(SPECT[(SPECT.reading == 'G') & (SPECT.d == round(D_MS, 4))].post_mean.iloc[0]) - float(SPECT[(SPECT.reading == 'G') & (SPECT.d == 0)].post_mean.iloc[0]):+.3f}")

# by ask band and by period: s refit on each group's own mean (stated), premium from the hedonic
EFROWS = []
for k in ["Er", "pi", "below"] + [f"q{int(q * 100):02d}" for q in QS]:
    EFROWS.append({"sample": "all years, last ask", "stat": k, "observed": EF_ALL[k], "model_s_EF": PRED_EF[k], "model_FAN_S": AT_FAN_EF[k], "model_s1": AT_1_EF[k], "s": S_EF})
for nm, e_ in EFS.items():
    for k in ["Er", "pi", "below", "q05", "q08"]:
        EFROWS.append({"sample": f"{nm}, FIRST ask", "stat": k, "observed": e_["obs_first"][k], "model_s_EF": e_["pred_first"][k],
                       "model_FAN_S": e_["fan_first"][k], "s": e_["s_first"], "m": e_["m_first"], "n": e_["n"]})
ef["period"] = pd.cut(ef.sold_year, [2013, 2018, 2021, 2027], labels=["2014-2018", "2019-2021", "2022-2026"])
for col, groups in [("askband", ["<$100K", "$100-250K", "$250K-1M", "$1M+"]), ("period", ["2014-2018", "2019-2021", "2022-2026"])]:
    for g in groups:
        d_ = ef[ef[col] == g]
        st = ef_stats(d_.r)
        mg = math.exp(float(d_.rhoW.mean()))
        r, c, Q = atoms(mg)
        sg = solve_s((r * Q).sum(1), st["Er"])[0]
        pg = model_at(mg, sg)
        pf = model_at(mg, FAN_S_REC)
        for k in ["pi", "below"]:
            EFROWS.append({"sample": f"{col}={g} (s refit on the group's mean)", "stat": k, "observed": st[k], "model_s_EF": pg[k], "model_FAN_S": pf[k], "s": sg, "m": mg, "n": st["n"]})
        log(f"  EF {col}={g:10s} n={st['n']:4d} premium {mg:.3f}: s refit {sg:.3f} | point mass {st['pi']:.3f} vs model {pg['pi']:.3f} (at FAN_S {pf['pi']:.3f}) "
            f"| below-ask mean {st['below']:.3f} vs {pg['below']:.3f}")
tr_, te_ = ef[ef.sold_year <= 2022], ef[ef.sold_year >= 2023]
st_tr, st_te = ef_stats(tr_.r), ef_stats(te_.r)
s_tr_ef, p_tr_ef = ef_fit(st_tr, math.exp(float(tr_.rhoW.mean())))
EF_TEMP = {k: (st_te[k], p_tr_ef[k], st_tr[k]) for k in ["Er", "pi", "below"]}
log(f"  EF temporal holdout (fit <=2022, s={s_tr_ef:.3f}; test 2023-26 n={st_te['n']}):",
    {k: f"obs {v[0]:.3f} model {v[1]:.3f} naive {v[2]:.3f}" for k, v in EF_TEMP.items()})
pd.DataFrame(EFROWS).to_csv(os.path.join(OUT, "ef_analog.csv"), index=False)

# =====================================================================================
# 8. ALPHA AND AMAX: what the data can say (primary specification)
# =====================================================================================
log("\n=== ALPHA / AMAX profile (reading G, d = D_MS) ===")
PROF = []
for iam, am in enumerate(AM_GRID):
    for ia, al in enumerate(AL_GRID):
        run = spec_run("G", D_MS, ia=ia, iam=iam, B=200, keys=KEYS)
        s_, o_ = fit_spec(T_HAT, "G", D_MS, ia, iam, extra=True, keys=KEYS)
        s_b = s_["bbs"][0]
        gap = at_s(o_["rom"], s_b) - (T_HAT["D"] + D_MS)
        gaps = []
        for t in TB[:200]:
            sb2, ob2 = fit_spec(t, "G", D_MS, ia, iam, keys=KEYS)
            r2, c2, Q2 = ob2["_atoms"]
            gaps.append(at_s(rom(r2, Q2), sb2["bbs"][0]) - (t["D"] + D_MS))
        se_gap = float(np.std(gaps, ddof=1))
        r, c, Q = atoms(M_EF_G, ia, iam)                     # EF under reading G (comparable with the primary)
        s_e = solve_s((np.log(r) * Q).sum(1), EF_ALL["Elnr"])[0]
        pi_e = at_s((c * Q).sum(1), s_e)
        Ar = 1 + (am - 1) * math.tanh(al * math.log(1.5) / (am - 1))
        PROF.append({"alpha": al, "amax": am, "s_bbs": s_b, "jensen_gap": gap, "gap_se": se_gap, "gap_z": gap / se_gap,
                     "s_pooled_post": run["post"]["mean"], "s_pooled_post_sd": run["post"]["sd"], "s_dl": run["dl"]["mu"],
                     "Er_at_post": at_s(o_["Er"], run["post"]["mean"]) * ED, "pi_at_post": at_s(o_["pi"], run["post"]["mean"]),
                     "s_ef": s_e, "ef_pi_pred": pi_e, "ef_pi_obs": EF_ALL["pi"], "A_at_rho_max": Ar})
PROF = pd.DataFrame(PROF)
PROF.to_csv(os.path.join(OUT, "alpha_amax_profile.csv"), index=False)
log(PROF.round(4).to_string(index=False))
P13 = PROF[PROF.amax == 1.30]
p55, p55h = PROF[(PROF.alpha == .55) & (PROF.amax == 1.30)].iloc[0], PROF[(PROF.alpha == .55) & (PROF.amax == 1.66)].iloc[0]

# =====================================================================================
# 9. A SECOND READING OF THE SAME LEVEL: SELECTION ON CLOSING WITH THE FULL FAN
# =====================================================================================
# Weight each slice of the FULL fan (s = 1) by its own chance of closing relative to the base
# (1 - gapPenalty at the slice's gap). Low-W slices sit at large gaps and rarely close, so the price
# given close rises. It needs no narrowing, and P_C stays the calibrated point figure.
SELROWS = []
for rho in [M_TYP, 1.0987, 1.2, 1.3, 1.4, 1.5]:
    a_sel = model_at(rho, 1.0, sel=True)
    a_fan = model_at(rho, FAN_S_REC)
    a_cur = model_at(rho, 1.0)
    SELROWS.append({"rho": rho, "Er_selection_full_fan": a_sel["Er"], "Er_narrowed_FAN_S": a_fan["Er"], "Er_current": a_cur["Er"],
                    "q08_selection": a_sel["q08"], "q08_narrowed": a_fan["q08"], "q08_current": a_cur["q08"],
                    "pi_selection": a_sel["pi"], "pi_narrowed": a_fan["pi"]})
SELT = pd.DataFrame(SELROWS)
SELT.to_csv(os.path.join(OUT, "selection_vs_narrowing.csv"), index=False)
SEP_HI = tuple(float(SELT.loc[SELT.rho == r_, "Er_selection_full_fan"].iloc[0] - SELT.loc[SELT.rho == r_, "Er_narrowed_FAN_S"].iloc[0]) for r_ in (1.4, 1.5))
log("\n=== Selection on closing (full fan) vs narrowing (FAN_S) ===")
log(SELT.round(4).to_string(index=False))
s_sel, o_sel = fit_spec(T_HAT, "G", D_MS, sel=True, keys=["bbs", "ib1", "ib2", "ibc"])
SEL_S = {k: (s_sel[k][0], s_sel[k][1]) for k in ["bbs", "ib1", "ib2", "ibc"]}
log("  with selection weighting, the s each source needs (* = at the grid edge, censored):", {k: f"{v[0]:.3f}{'*' if v[1] else ''}" for k, v in SEL_S.items()})

# =====================================================================================
# 10. THE OPTIMISER: recommended ask vs s, the patient seller's jump, and the pending fits' pages
# =====================================================================================
log("\n=== Optimiser (bestRatio, lamT = 900) ===")
STK = os.path.join(OUT, "pending_stack")
if os.path.isdir(STK):
    shutil.rmtree(STK)
os.makedirs(STK)
stack_note, stack_fail = [], []
base_stack = f"{FIT5}/time_to_close_shape/patched_after_overpricing/index.html"
PAGES = [("this repo page", INDEX)]
if os.path.exists(base_stack):
    shutil.copy(base_stack, os.path.join(STK, "index.html"))
    stack_note.append("overpricing_time + time_to_close_shape (time_to_close_shape/patched_after_overpricing)")
    cands = [("quality_weights_v2", f"{FIT5}/quality_weights_v2/index.html.diff", None),
             ("sba_risk_refresh", f"{FIT5}/sba_risk_refresh/index.html.diff", None),
             ("competition_buyers", None, f"{FIT5}/competition_buyers/patched_copy/index.html")]
    for nm, diffp, page in cands:
        if diffp is None and page and os.path.exists(page):
            diffp = os.path.join(STK, nm + ".diff")
            with open(diffp, "w") as f:
                subprocess.run(["diff", "-u", INDEX, page], stdout=f)
        if not diffp or not os.path.exists(diffp):
            stack_fail.append(f"{nm} (no patched page found)")
            continue
        p_ = subprocess.run(["patch", "--dry-run", "-s", "-p1", os.path.join(STK, "index.html"), diffp], capture_output=True, text=True)
        if p_.returncode == 0:
            subprocess.run(["patch", "-s", "-p1", os.path.join(STK, "index.html"), diffp], capture_output=True, text=True, check=True)
            stack_note.append(nm)
        else:
            import re
            hk = re.findall(r"(\d+) out of (\d+) hunks? FAILED", p_.stdout + p_.stderr)
            nrej = ", ".join(f"{a} of {b} hunks" for a, b in hk) or "some hunks"
            stack_fail.append(f"{nm} ({nrej} conflict with the stack; checked on its own page)")
    PAGES.append(("stack: " + " + ".join(stack_note), os.path.join(STK, "index.html")))
for nm, p_ in [("overpricing_time alone", f"{FIT5}/overpricing_time/patched/index.html"),
               ("time_to_close_shape alone", f"{FIT5}/time_to_close_shape/patched/index.html"),
               ("competition_buyers alone", f"{FIT5}/competition_buyers/patched_copy/index.html"),
               ("quality_weights_v2 alone", f"{FIT5}/quality_weights_v2/index.patched.html"),
               ("sba_risk_refresh alone", f"{FIT5}/sba_risk_refresh/patched/index.html")]:
    if os.path.exists(p_):
        PAGES.append((nm, p_))
for nm, p_ in PAGES:
    log(f"  page {nm[:110]}: sha {sha(p_)}")
log("  pending-fit stack:", "; ".join(stack_note), "| not stacked:", "; ".join(stack_fail) or "none")
OPT_JS = r"""
const fs=require("fs"),vm=require("vm");
const spec=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
function load(file,ovr){ let html=fs.readFileSync(file,"utf8"); let src=html.slice(html.lastIndexOf("<script>")+8);
  src=src.slice(0,src.indexOf("/* ============ bar helpers"));
  for(const [a,b] of ovr){ if(!src.includes(a)) throw new Error("override target not found: "+a.slice(0,60)); src=src.split(a).join(b); }
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN}; vm.createContext(ctx);
  vm.runInContext(src+";this.API={model,bestRatio,IND,sizeRefs,typMargin,MODELS};",ctx); return ctx.API; }
const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
const med=(A,ind,ern)=>{const I=A.IND[ind],RF=A.sizeRefs(ern);return {ind,ern,rev:ern/A.typMargin(ind,ern),yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40};};
/* the two peaks of bestRatio's own utility (EVp + (1-P_C) theta V - lamT tMed): best interior ask (< 1.35x) and the cap region */
function peaks(A,b,th){ const V=A.model({...b,ask:1}).V; let bi={u:-Infinity},bc={u:-Infinity};
  for(let k=0;k<=140;k++){ const m=.80+k*.005, r=A.model({...b,ask:V*m}); const u=r.EVp+(1-r.PC)*th*r.V-900*r.tMed;
    if(m<1.35){ if(u>bi.u) bi={u,m}; } else { if(u>bc.u) bc={u,m}; } }
  return {V,bi,bc}; }
const out={grid:[],sweep:[],util:[],margin:[],err:[]};
spec.pages.forEach((pg,pi)=>{ let A; try{A=load(pg[1],spec.ovr);}catch(e){out.err.push([pg[0],String(e)]); return;}
  const cases=[["framework example",EX],["prof median $160k",med(A,"prof",1.6e5)],["mfg median $1.5M",med(A,"mfg",1.5e6)]];
  const fine=pi<=1, sList=fine?[...new Set([...spec.s,...spec.s_fine])].sort((a,b)=>a-b):spec.s;
  for(const s of sList){ A.MODELS.__set(.55,s,1.3); A.MODELS.__sel=false;
    for(const [lab,b] of cases) for(const th of [0,.75]){ if(th===0&&!spec.s.includes(s)) continue;
      out.grid.push({page:pg[0],case:lab,s,theta:th,rho:A.bestRatio(b,th,900)}); }
    if(fine){ const P=peaks(A,EX,.75); out.margin.push({page:pg[0],s,interior_rho:P.bi.m,interior_U_over_V:P.bi.u/P.V,corner_rho:P.bc.m,corner_U_over_V:P.bc.u/P.V}); } }
  for(const [mode,s,sel] of [["current (s=1)",1,false],["narrowed (FAN_S)",spec.fan,false],["selection, full fan",1,true]]){
    A.MODELS.__set(.55,s,1.3); A.MODELS.__sel=sel;
    if(pi===0) for(let k=0;k<=100;k++) out.sweep.push({page:pg[0],mode,theta:k/100,rho:A.bestRatio(EX,k/100,900)});
    const P=peaks(A,EX,.75);
    out.util.push({page:pg[0],mode,interior_rho:P.bi.m,interior_U_over_V:P.bi.u/P.V,corner_rho:P.bc.m,corner_U_over_V:P.bc.u/P.V}); }
  A.MODELS.__sel=false; });
console.log(JSON.stringify(out));
"""
with open(os.path.join(OUT, "optimiser.js"), "w") as f:
    f.write(OPT_JS)
S_OPT = [1.0, 0.95, 0.9, 0.875, 0.85, 0.825, 0.8, 0.775, 0.75, 0.7, 0.6, 0.5]
S_FINE = [round(x, 3) for x in np.arange(0.70, 0.9601, 0.005)]
with open(os.path.join(OUT, "optimiser_spec.json"), "w") as f:
    json.dump({"pages": PAGES, "ovr": OVR, "s": S_OPT, "s_fine": S_FINE, "fan": FAN_S_REC}, f)
t_o = time.time()
p = subprocess.run(["node", os.path.join(OUT, "optimiser.js"), os.path.join(OUT, "optimiser_spec.json")], capture_output=True, text=True, timeout=5400)
if p.returncode != 0:
    log(p.stderr[-2000:])
    raise SystemExit("optimiser driver failed")
OPT = json.loads(p.stdout.strip().splitlines()[-1])
log(f"  optimiser driver: {time.time() - t_o:.0f}s")
for e in OPT["err"]:
    log("  page not evaluated:", e)
OG = pd.DataFrame(OPT["grid"])
OG.to_csv(os.path.join(OUT, "optimum_vs_s.csv"), index=False)
OSW = pd.DataFrame(OPT["sweep"])
OSW.to_csv(os.path.join(OUT, "optimum_vs_theta.csv"), index=False)
OU = pd.DataFrame(OPT["util"])
OU.to_csv(os.path.join(OUT, "utility_interior_vs_corner.csv"), index=False)
OM = pd.DataFrame(OPT["margin"])
OM["margin_interior_minus_corner"] = OM.interior_U_over_V - OM.corner_U_over_V
OM.to_csv(os.path.join(OUT, "utility_margin_vs_s.csv"), index=False)
FLIP = {}
for (pg, cs), g in OG[OG.theta == .75].groupby(["page", "case"], sort=False):
    g = g.sort_values("s")
    lo = g[g.rho < 1.4].s.max()
    hi = g[(g.rho >= 1.4) & (g.s > (lo if pd.notna(lo) else -1))].s.min()
    FLIP[(pg, cs)] = (float(lo) if pd.notna(lo) else None, float(hi) if pd.notna(hi) else None,
                      float(g[g.s == FAN_S_REC].rho.iloc[0]), float(g[g.s == 1.0].rho.iloc[0]))
log("  theta=.75: (largest s with an interior optimum, smallest s above it with the corner, rho at FAN_S, rho at s=1):")
for k_, v in FLIP.items():
    log(f"    {k_[0][:70]:70s} | {k_[1]:18s} | {v}")
log("  theta=0 recommended ask at FAN_S vs s=1:", {f"{pg[:30]}|{cs}": (round(float(g[g.s == FAN_S_REC].rho.iloc[0]), 3), round(float(g[g.s == 1.0].rho.iloc[0]), 3))
                                                  for (pg, cs), g in OG[OG.theta == 0].groupby(["page", "case"], sort=False) if pg == PAGES[0][0]})
JUMP = {}
for mode, g in OSW.groupby("mode", sort=False):
    g = g.sort_values("theta")
    j = g[g.rho >= 1.4].theta.min()
    JUMP[mode] = float(j) if pd.notna(j) else None
log("  framework example: smallest theta (step 0.01) at which the recommendation jumps to the 1.5x corner:", JUMP)
log("  utility at the best interior ask vs the corner (U/V, framework example, theta=.75):")
log(OU.round(4).to_string(index=False))
log("  margin (interior - corner, share of value) vs s, framework example, theta=.75:")
with pd.option_context("display.width", 250):
    log(OM[["page", "s", "interior_rho", "interior_U_over_V", "corner_U_over_V", "margin_interior_minus_corner"]].round(5).to_string(index=False))
EXF = FLIP[(PAGES[0][0], "framework example")]
S_FLIP_LO, S_FLIP_HI = EXF[0], EXF[1]
P_ABOVE_FLIP = float(MIX[MU_G >= S_FLIP_HI].sum() / MIX.sum()) if S_FLIP_HI else float("nan")
P_ABOVE_FLIP_LO = float(MIX[MU_G >= S_FLIP_LO].sum() / MIX.sum()) if S_FLIP_LO else float("nan")
OM0 = OM[OM.page == PAGES[0][0]].set_index("s")
MARGIN = {sv: float(OM0.loc[sv, "margin_interior_minus_corner"]) for sv in [0.75, 0.8, 0.825, 0.85, 0.875, 0.9, 1.0] if sv in OM0.index}
MARGIN_FAN = float(OM0.loc[FAN_S_REC, "margin_interior_minus_corner"])
MAX_ABS_MARGIN_RANGE = max([abs(MARGIN[sv]) for sv in MARGIN if SPEC_LO - 1e-9 <= sv <= SPEC_HI + 1e-9] or [abs(MARGIN_FAN)])
log(f"  flip on this page between s {S_FLIP_LO} and {S_FLIP_HI}; P(s >= {S_FLIP_HI}) = {P_ABOVE_FLIP:.2f} (P(s >= {S_FLIP_LO}) = {P_ABOVE_FLIP_LO:.2f}); "
    f"margin at FAN_S {MARGIN_FAN:+.4f} of value; largest |margin| across the specification range {SPEC_LO:.2f}-{SPEC_HI:.2f}: {MAX_ABS_MARGIN_RANGE:.4f}")

# =====================================================================================
# 11. RECOMMENDATION, THE PATCH (applied to a COPY), TESTS, BEFORE / AFTER
# =====================================================================================
log("\n=== Recommendation ===")
rP, cP, QP = MO["_atoms"]
AT = {k: at_s(v, FAN_S_REC) for k, v in basic(rP, cP, QP).items()}
AT1 = {k: at_s(v, 1.0) for k, v in basic(rP, cP, QP).items()}
AT_Q = {p_: at_s(MO[k], FAN_S_REC) for p_, k in [(.05, "q05"), (.08, "q08"), (.22, "q22"), (.5, "q50")]}
AT1_Q = {p_: at_s(MO[k], 1.0) for p_, k in [(.05, "q05"), (.08, "q08"), (.22, "q22"), (.5, "q50")]}
READ_ER = {}
for rd in ["G", "M", "R"]:
    o_ = curves(T_HAT, rd, D_MS)
    READ_ER[rd] = (float(np.median(o_["m"])), at_s(o_["Er"], FAN_S_REC) * ED, at_s(o_["Er"], 1.0) * ED)
pdl = PRIMARY["dl"]
log(f"  FAN_S = {FAN_S_REC:.2f}; typical FIRST-ask premium M_TYP = {M_TYP:.4f} (reading G, d = {D_MS:.4f})")
log(f"  at FAN_S, M_TYP: E[P|close]/first ask {AT['Er']:.4f} (current {AT1['Er']:.4f}); on the data's ask {AT['Er'] * ED:.4f} (current {AT1['Er'] * ED:.4f}); "
    f"share at the ask {AT['pi']:.3f} (current {AT1['pi']:.3f}); below-ask mean {AT['below']:.4f} (current {AT1['below']:.4f}); "
    f"q05 {AT_Q[.05]:.3f} (current {AT1_Q[.05]:.3f}), q08 {AT_Q[.08]:.3f} ({AT1_Q[.08]:.3f}), q22 {AT_Q[.22]:.3f} ({AT1_Q[.22]:.3f})")
log("  E[P|close]/(data's) ask at FAN_S and at s=1, by premium reading:", {k: tuple(round(x, 4) for x in v) for k, v in READ_ER.items()})
# THE ROBUST FINDING: like for like (first-ask basis, each source's own binning), the whole spread undershoots every
# sale/ask target; narrowing (FAN_S) and selection on closing (full fan) both raise the level.
ROBUST = {k: {"target": T_HAT[k] * math.exp(-D_MS), "current": at_s(MO[k], 1.0), "narrowed": at_s(MO[k], FAN_S_REC),
              "selection": at_s(o_sel[k], 1.0)} for k in ["bbs", "ibc", "ib1", "ib2"]}
log("  like-for-like E[P|close]/first ask at the typical premium (target | whole spread | narrowed at FAN_S | selection, full fan):")
for k, v in ROBUST.items():
    log(f"    {k:4s} {v['target']:.4f} | {v['current']:.4f} | {v['narrowed']:.4f} | {v['selection']:.4f}")
SRC_TABLE = pd.DataFrame([{"source": LAB[k], "target_data_ask": T_HAT[k], "target_first_ask": T_HAT[k] * math.exp(-D_MS),
                           "s_k": e, "se_s_k": math.sqrt(v), "model_at_FAN_S_data_ask": at_s(MO[k], FAN_S_REC) * ED,
                           "model_current_data_ask": at_s(MO[k], 1.0) * ED} for k, e, v in zip(KEYS, PRIMARY["est"], PRIMARY["var"])])
SRC_TABLE.to_csv(os.path.join(OUT, "sources_s.csv"), index=False)
pd.DataFrame(ROWS).to_csv(os.path.join(OUT, "validation.csv"), index=False)

html = open(INDEX, encoding="utf-8").read()
pct = lambda x: f"{100 * x:.0f}"
MS_YEARS = f"{T_LIST * 12:.1f}"
RB = ROBUST
EST = PRIMARY["est_all"]
SEL_TXT = (f"BizBuySell {SEL_S['bbs'][0]:.2f}, IBBA under $500K {'at least ' if SEL_S['ib1'][1] else ''}{SEL_S['ib1'][0]:.2f}, "
           f"$500K-1M {SEL_S['ib2'][0]:.2f} (under $1M as one {SEL_S['ibc'][0]:.2f})")
NOISE_TXT = f"{S_AT_SD(0.2):.2f}, {S_AT_SD(0.3):.2f} and {S_AT_SD(0.4):.2f} at noise sd 0.2, 0.3 and 0.4"
JUMP_FAN = JUMP.get("narrowed (FAN_S)")
FAN_COMMENT = (
    "/* FAN_S: the share of the value model's residual spread (in logs) kept in the realised-price fan once a\n"
    "   business is listed. CALIBRATED, not fitted: a reduced form whose mechanism the data do not identify\n"
    "   (fit/anchoring_realization.py, Oct 2026). What the data show robustly: at the typical first ask (M_TYP x\n"
    f"   value) the whole spread gives E[P|close]/ask {RB['bbs']['current']:.3f}, short of every like-for-like market average\n"
    f"   (BizBuySell deal-level {RB['bbs']['target']:.3f} on the first ask; IBBA under $1M, binned by sale price, {RB['ibc']['target']:.3f}\n"
    f"   against the model's {RB['ibc']['current']:.3f}). Narrowing the fan (information in the ask) and weighting each scenario by\n"
    "   its own chance of closing (selection, whole spread) both raise it; this implements narrowing because it\n"
    f"   keeps P_C and the price independent. Per source s: BizBuySell {EST['bbs']:.2f}, IBBA under $500K {EST['ib1']:.2f} and\n"
    f"   $500K-1M {EST['ib2']:.2f} (or {EST['ibc']:.2f} as one source), DealStats {EST['ds']:.2f}; averaged over the source structure,\n"
    f"   which ask the sources report (the ask at sale, ~{100 * D_MS:.1f}% below the first) and how the typical premium is\n"
    f"   read: {POST['mean']:.2f} (sd {POST['sd']:.2f}), rounded to {FAN_S_REC:.2f}; {SPEC_LO:.2f}-{SPEC_HI:.2f} are equally defensible. That interval\n"
    "   is conditional: selection needs s >= 1, and if the premium's spread across listings were pricing noise\n"
    f"   rather than information s would be lower ({NOISE_TXT}). Calibrated near 1.07x value;\n"
    "   at 1.4-1.5x, where bestRatio's patient seller is decided, it is an extrapolation. Refit if ALPHA changes. */\n")
MTYP_COMMENT = (
    "/* M_TYP: the typical FIRST-ask premium over V among sold Main-Street deals:\n"
    f"   exp( ln(median ask / median sale) + d + E[ln R] ) = exp({T_HAT['D']:.3f} + {D_MS:.3f} {ELNR:+.3f}) (BizBuySell 2016-18;\n"
    "   DealLedger; the value fan's own location, since V is its median). Read by the self-audit and the tests only;\n"
    "   model() does not use it. */\n")
REALISED_CAPTION = (
    "      +'DealStats consideration series. At the market&rsquo;s typical listing premium (a first ask about "
    f"{pct(M_TYP - 1)}% above the '\n"
    f"      +'value) the model closes at about {pct(AT['Er'])}% of that ask at every size below $9M, about {pct(AT['Er'] * ED)}% of the ask '\n"
    f"      +'still standing at sale. The market averages are BizBuySell&rsquo;s {pct(T_HAT['bbs'])}% and IBBA&rsquo;s {pct(T_HAT['ib1'])}% under $500K and '\n"
    f"      +'{pct(T_HAT['ib2'])}% from $500K to $1M, all on the ask at sale, which runs about {100 * D_MS:.1f}% below the first ask. With the '\n"
    "      +'value model&rsquo;s whole spread the model fell short of all of them; to reach them the price fan keeps '\n"
    f"      +'{pct(FAN_S_REC)}% of that spread (in logs), so the downside scenarios are narrower than the value range in '\n"
    "      +'the Data tab. That share is calibrated, not measured: "
    f"{SPEC_LO:.2f}&ndash;{SPEC_HI:.2f} fit equally well, and the data cannot say '\n"
    "      +'whether a listed price is less uncertain because the ask carries information or because low offers '\n"
    "      +'rarely close. It is calibrated near the typical premium; at asks of 1.4&times; value and up it is an '\n"
    "      +'extrapolation. IBBA groups deals by sale price, which pulls its under-$500K figure down; from $2M up its '\n"
    "      +'ratio is to the advisor&rsquo;s benchmark, not an ask, so it is a benchmark comparison only. Deals above '\n"
    "      +'$1M realise a few points more of the ask than the model gives them. The price is never allowed above the '\n"
    "      +'ask, except where the IBBA size curve itself closes above 100% (about $9M of value and up; that ratio is '\n"
    "      +'to a benchmark, not an ask, a known inconsistency).</p></div>';")
DATA_ROW_FAN = (
    "      <tr><td>Realised-price fan: share of the value spread kept once a business is listed (FAN_S; drives the price-if-it-closes scenarios)\n"
    "        &nbsp;<span class=\"st adj\">calibrated</span></td>\n"
    "        <td>1.00 (the value model&rsquo;s whole out-of-fold spread)</td>\n"
    "        <td>${FAN_S.toFixed(2)} of it, in logs (with &alpha; = ${ALPHA_ANCHOR}): calibrated to market sale-to-ask averages; the mechanism is not\n"
    f"        identified, and {SPEC_LO:.2f}&ndash;{SPEC_HI:.2f} are equally defensible</td>\n"
    "        <td>What the data show robustly: at the typical first ask (${M_TYP.toFixed(2)}&times; value) the whole spread gave\n"
    f"        {100 * RB['bbs']['current']:.1f}% of the ask if it closes, short of BizBuySell&rsquo;s {100 * RB['bbs']['target']:.1f}% (deal-level mean, 2016&ndash;18,\n"
    f"        {int(SEC.n_sales.sum()):,} sales, on the same first-ask basis) and of IBBA&rsquo;s under-$1M deals ({len(IBW)} quarters, binned by sale price:\n"
    f"        {100 * RB['ibc']['target']:.1f}% against the model&rsquo;s {100 * RB['ibc']['current']:.1f}%). Two explanations raise it alike: the ask carries information\n"
    "        (a narrower fan, implemented here) or low offers rarely close (selection). Per source s: BizBuySell\n"
    f"        {EST['bbs']:.2f}, IBBA under $500K {EST['ib1']:.2f} and $500K&ndash;1M {EST['ib2']:.2f} (or {EST['ibc']:.2f} as one source), DealStats {EST['ds']:.2f};\n"
    f"        averaged over the source structure, which ask the sources report (the ask at sale, {100 * D_MS:.1f}% below the first ask on\n"
    f"        Main Street: DealLedger, {len(DLP):,} listings) and how the typical premium is read, {POST['mean']:.2f} (sd {POST['sd']:.2f}). That is\n"
    f"        conditional: selection needs s &ge; 1, and if the spread of asks across listings were pricing noise s would fall to\n"
    f"        {S_AT_SD(0.2):.2f}&ndash;{S_AT_SD(0.3):.2f}. Calibrated near 1.07&times; value; at 1.4&ndash;1.5&times;, where the patient-seller recommendation is\n"
    f"        decided, it is an extrapolation. Calibrated to 2022+ alone it would be lower ({RUN22['post']['mean']:.2f}). Out of sample IBBA&rsquo;s\n"
    f"        under-$500K level is missed by {100 * (LOSO['ib1']['pred_dl'] - LOSO['ib1']['obs']):.0f} points, and on 2022&ndash;26 quarters per-band averages beat\n"
    f"        the model ({100 * TEMP_Q['naive per band']:.1f} vs {100 * TEMP_Q['fitted']:.1f} points; whole spread {100 * TEMP_Q['current']:.1f}). Effect: at the typical\n"
    f"        premium the bear scenario&rsquo;s low end rises from {AT1_Q[.08]:.2f} to {AT_Q[.08]:.2f} of the ask.</td></tr>\n")
DATA_ROW_ALPHA = (
    "      <tr><td>Anchoring strength (&alpha; = ${ALPHA_ANCHOR}) and its ceiling (A<sub>max</sub> = ${AMAX.toFixed(2)})</td>\n"
    "          <td>deal-level ask and sale pairs where the ask varies for reasons unrelated to the business (a pricing experiment)</td>\n"
    "          <td><span class=\"st free\">not identified: sale-to-ask data fix (1&minus;&alpha;)&middot;s, not &alpha;. With s refitted, every &alpha;\n"
    f"          from 0.30 to 0.85 gives the same realisation level ({P13.Er_at_post.min():.3f}&ndash;{P13.Er_at_post.max():.3f}); BizBuySell&rsquo;s mean and\n"
    "          median ratios lean to a low &alpha; under one reading of the typical premium and not under another. A<sub>max</sub>\n"
    f"          moves the price at the 1.5&times; cap by under 3%. Empire Flippers&rsquo; pass-through of the ask into the sale price,\n"
    f"          {EF_PAR['tobit'][0]:.2f} (SE {EF_PAR['tobit'][1]:.2f}), mixes anchoring with information in the ask, so it is only an upper bound</span></td></tr>")
SPREAD_NEW = (
    "    <div class=\"chk\"><div>Value uncertainty: residual spread of the value model<div class=\"muted\" style=\"font-size:11.8px\">15 measured out-of-fold quantiles; replaced a judgement value of 0.18&ndash;0.34</div></div>\n"
    "      <span class=\"n\" style=\"color:#5ee0a8\">${SIGMA_DISPLAY.toFixed(3)}</span><span class=\"n muted\">lognormal sigma implied by p10/p90 (display only)</span><span class=\"st pub\">fitted</span></div>\n"
    "    <div class=\"chk\"><div>Realised-price fan at a typical ask (drives the price-if-it-closes scenarios)<div class=\"muted\" style=\"font-size:11.8px\">FAN_S = ${FAN_S.toFixed(2)} of the value spread, in logs; calibrated to sale-to-ask averages, mechanism not identified (see Fitted from public data)</div></div>\n"
    "      <span class=\"n\" style=\"color:var(--bright)\">${(FAN_S*SIGMA_DISPLAY).toFixed(3)}</span><span class=\"n muted\">FAN_S &times; sigma (display only)</span><span class=\"st adj\">calibrated</span></div>\n"
    "    <p class=\"note\">The value model&rsquo;s 80% interval spans ${V.fan_quantiles.p10.toFixed(2)}&times;&ndash;${V.fan_quantiles.p90.toFixed(2)}&times; the point estimate. That is the honest\n"
    "    width of small-business valuation; a single number implies precision this data cannot support. The realised-price scenarios\n"
    "    use ${FAN_S.toFixed(2)} of that spread in logs (${Math.pow(V.fan_quantiles.p10,FAN_S).toFixed(2)}&times;&ndash;${Math.pow(V.fan_quantiles.p90,FAN_S).toFixed(2)}&times; before anchoring and the ask cap):\n"
    "    with the whole spread the model realised less of the ask than any market average. That share is calibrated, not measured.</p>\n")
SPREAD_OLD = (
    "    <div class=\"chk\"><div>Residual spread driving the scenario bands<div class=\"muted\" style=\"font-size:11.8px\">15 measured out-of-fold quantiles; replaced a judgement value of 0.18&ndash;0.34</div></div>\n"
    "      <span class=\"n\" style=\"color:#5ee0a8\">${SIGMA_DISPLAY.toFixed(3)}</span><span class=\"n muted\">lognormal sigma implied by p10/p90 (display only)</span><span class=\"st pub\">fitted</span></div>\n"
    "    <p class=\"note\">The 80% interval spans ${V.fan_quantiles.p10.toFixed(2)}&times;&ndash;${V.fan_quantiles.p90.toFixed(2)}&times; the point estimate. That is the honest\n"
    "    width of small-business valuation; a single number implies precision this data cannot support.</p>\n")
INT_RHO = float(OU[(OU.page == PAGES[0][0]) & (OU["mode"] == "narrowed (FAN_S)")].interior_rho.iloc[0])   # the interior peak at FAN_S
INT_TXT = f"{INT_RHO:.2f}x"
BEST_OLD = ("   worth to the owner: ~1.05x when a failed sale is a total loss, ~1.4x when the\n"
            "   owner is content to keep it. Solved once per render and reused, so the 2^11\n")
BEST_NEW = ("   worth to the owner: ~1.1x when a failed sale is a total loss. For an owner content to\n"
            f"   keep it (theta = .75) the utility has two near-equal peaks, an interior one near {INT_TXT}\n"
            f"   and the 1.5x cap. At FAN_S = {FAN_S_REC:.2f} the {'interior one' if MARGIN_FAN > 0 else 'cap'} wins by {100 * abs(MARGIN_FAN):.2f}% of value (framework example); the\n"
            f"   cap wins for FAN_S above about {S_FLIP_LO:.3f}-{S_FLIP_HI:.3f} or theta above {(JUMP_FAN if JUMP_FAN is not None else 1):.2f}. That knife-edge is set by how\n"
            "   widely prices scatter at asks of 1.4-1.5x, where FAN_S (calibrated near 1.07x) is\n"
            "   extrapolated; the whole fan, or selection on closing, keep the cap. The render shows\n"
            "   both ends as a range when they are within 1% of value (AUDIT.md, Oct 2026). Solved once\n"
            "   per render and reused, so the 2^11\n")
UI_OLD = ("  const uGain=Uat(rKeep)-Uat(rSell), atEdge=s.optRho>RHO_MAX-.02;\n")
UI_NEW = ("  const uGain=Uat(rKeep)-Uat(rSell), atEdge=s.optRho>RHO_MAX-.02;\n"
          "  /* A patient seller's utility often has two near-equal peaks, an interior ask near " + INT_TXT + " and the\n"
          "     RHO_MAX cap. Which one wins turns on how widely prices scatter at high asks (FAN_S is calibrated\n"
          "     near 1.07x and extrapolated there), so when the other peak is within 1% of value the note gives\n"
          "     the range instead of presenting one end as the answer. */\n"
          "  const Uf=x=>Uat(x)-s.lamT*x.tMed;\n"
          "  let alt=null;\n"
          "  if(!sameAsk&&s.theta>0){\n"
          "    if(atEdge){ for(let m=1.0;m<=1.35+1e-9;m+=.025){ const x=model({...s,ask:r.V*m}); if(!alt||Uf(x)>alt.u) alt={u:Uf(x),m}; } }\n"
          "    else { const x=model({...s,ask:r.V*RHO_MAX}); alt={u:Uf(x),m:RHO_MAX}; }\n"
          "    if(Uf(rKeep)-alt.u>.01*r.V) alt=null;\n"
          "  }\n")
UI_NOTE_OLD = ("      +(atEdge?`It sits at ${RHO_MAX.toFixed(1)}× value, the highest ask the closing data resolve, so read it as \"test the market\", not as a measured optimum. `:\"\")\n")
UI_NOTE_NEW = (UI_NOTE_OLD +
               "      +(alt?`Asking ${alt.m.toFixed(2)}× value instead is worth within ${pc(Math.max(0,Uf(rKeep)-alt.u)/r.V,2)} of value to this owner, close to a tie, so read the patient-seller price as a range, `\n"
               "        +`${Math.min(alt.m,s.optRho).toFixed(2)}–${Math.max(alt.m,s.optRho).toFixed(2)}× value: which end wins turns on how widely prices scatter at high asks, which the data do not settle. `:\"\")\n")
# On the pending overpricing_time stack the note lives in optNote(s,V,rSell,rKeep): the same logic, rebased there.
PATCH_STACK_ALT = {
    UI_OLD: ("  const atEdge=s.optRho>RHO_MAX-.02, days=Math.round(Math.abs(rSell.tMed-rKeep.tMed));\n",
             "  const atEdge=s.optRho>RHO_MAX-.02, days=Math.round(Math.abs(rSell.tMed-rKeep.tMed));\n"
             "  /* two near-equal peaks (an interior ask near " + INT_TXT + " and the RHO_MAX cap): when the other one is within\n"
             "     1% of value, give the range instead of one end (FAN_S is extrapolated at high asks; AUDIT.md, Oct 2026) */\n"
             "  let alt=null;\n"
             "  if(s.theta>0&&money(V*s.optRho)!==money(V*s.rhoSell)){\n"
             "    if(atEdge){ for(let m=1.0;m<=1.35+1e-9;m+=.025){ const x=model({...s,ask:V*m}); if(!alt||U(x)>alt.u) alt={u:U(x),m}; } }\n"
             "    else { const x=model({...s,ask:V*RHO_MAX}); alt={u:U(x),m:RHO_MAX}; }\n"
             "    if(U(rKeep)-alt.u>.01*V) alt=null;\n"
             "  }\n"
             "  const rangeTxt=alt?`Asking ${alt.m.toFixed(2)}× value instead is worth within ${pc(Math.max(0,U(rKeep)-alt.u)/V,2)} of value to this owner, close to a tie, so read the patient-seller price as a range, `\n"
             "    +`${Math.min(alt.m,s.optRho).toFixed(2)}–${Math.max(alt.m,s.optRho).toFixed(2)}× value: which end wins turns on how widely prices scatter at high asks, which the data do not settle. `:\"\";\n"),
    UI_NOTE_OLD: ("    +(atEdge?`It sits at ${RHO_MAX.toFixed(1)}× value, the highest ask the closing data resolve, so read it as \"test the market\", not as a measured optimum. `:\"\")\n",
                  "    +(atEdge?`It sits at ${RHO_MAX.toFixed(1)}× value, the highest ask the closing data resolve, so read it as \"test the market\", not as a measured optimum. `:\"\")\n"
                  "    +rangeTxt\n"),
}
PATCH = [
    ("title=\"The fitted value's measured spread, moved by anchoring and competition (both judgment), and capped at the ask\"",
     "title=\"The fitted value's measured spread, narrowed to the share that remains once a business is listed (calibrated), moved by anchoring and competition (both judgment), and capped at the ask\""),
    (FAN_OLD_BLOCK, FAN_S_BLOCK),
    ("const ALPHA_ANCHOR=.55;\n",
     "const ALPHA_ANCHOR=.55;\n" + FAN_COMMENT + f"const FAN_S={FAN_S_REC:.2f};\n" + MTYP_COMMENT + f"const M_TYP={M_TYP:.3f};\n"),
    ("  out.ALPHA=ALPHA_ANCHOR;\n", "  out.ALPHA=ALPHA_ANCHOR; out.fanS=FAN_S; out.mTyp=M_TYP;\n"),
    ("     of the fan is one scenario for what the market will pay, W. In that scenario",
     "     of the fan, kept at FAN_S of its log spread (calibrated to sale-to-ask averages; information in\n"
     "     the ask and selection on closing explain them alike), is one scenario for what the market\n"
     "     will pay, W. In that scenario"),
    (r"\\quad W=E[V\\mid X]\\cdot R(p)\\\\[3pt]",
     r"\\quad W=E[V\\mid X]\\cdot R(p)^{s},\\;s=${FAN_S.toFixed(2)}\\\\[3pt]"),
    (r"W=E[V\\mid X]\\cdot R\\quad\\text{(}R=\\text{measured out-of-fold price spread, 48 equal-probability slices)}",
     r"W=E[V\\mid X]\\cdot R^{s}\\quad\\text{(}R=\\text{measured out-of-fold value spread, 48 equal-probability slices; }s=${FAN_S.toFixed(2)}\\text{, the share kept once listed)}"),
    (r"R(0.10)=${MODELS.value.fan_quantiles.p10.toFixed(2)},\\;R(0.50)=1.00,\\;R(0.90)=${MODELS.value.fan_quantiles.p90.toFixed(2)}",
     r"R(0.10)^{s}=${Math.pow(MODELS.value.fan_quantiles.p10,FAN_S).toFixed(2)},\\;R(0.50)^{s}=1.00,\\;R(0.90)^{s}=${Math.pow(MODELS.value.fan_quantiles.p90,FAN_S).toFixed(2)}"),
    ("<div class=\"lbl\">Scenario quantiles from the measured out-of-fold price distribution</div>",
     "<div class=\"lbl\">Scenario quantiles from the measured out-of-fold value spread, narrowed once listed (FAN_S, calibrated)</div>"),
    ("+row('Market average: sale price as a share of the ask', pc(r.ft.pctAsk,1),",
     "+row(r.Vbase>=2e6?'Market benchmark: sale price as a share of the advisor&rsquo;s benchmark (IBBA; deals this size usually list without an ask)':'Market average: sale price as a share of the ask', pc(r.ft.pctAsk,1),"),
    ("      +'DealStats consideration series. The typical ratio is a market average across every '\n"
     "      +'closed listing; the model does not reproduce it above about $1M of value, where its expected '\n"
     "      +'price runs 8 to 14 points lower. Its price spread is the regression&rsquo;s, which includes '\n"
     "      +'things a buyer can see and the model cannot; deal-level pairs of asking and sale prices would '\n"
     "      +'calibrate this, and no public source of them was reachable. The price is never allowed above '\n"
     "      +'the ask, except where the IBBA size curve itself closes above 100% (about $9M of value and up).</p></div>';",
     REALISED_CAPTION),
    ("      <tr><td>Anchoring of the sale price on the ask (&alpha;, A<sub>max</sub>), and the model&rsquo;s shortfall against\n"
     "          IBBA&rsquo;s sale-to-ask ratio above $1M</td>\n"
     "          <td>deal-level asking and sale price pairs</td>\n"
     "          <td><span class=\"st free\">BIZCOMPS and DealStats record both (paid); Empire Flippers&rsquo; public API and Flippa\n"
     "          sold listings are blocked from this environment</span></td></tr>",
     DATA_ROW_ALPHA),
    ("disagrees with it, as listing copy uses it loosely. Phrase flags are noisy, so both effects are understated.</td></tr>\n",
     "disagrees with it, as listing copy uses it loosely. Phrase flags are noisy, so both effects are understated.</td></tr>\n" + DATA_ROW_FAN),
    (SPREAD_OLD, SPREAD_NEW),
    (BEST_OLD, BEST_NEW),
    (UI_OLD, UI_NEW),
    (UI_NOTE_OLD, UI_NOTE_NEW),
    ("  let lo=1,hi=1.6,mid=0;\n  for(let i=0;i<60;i++){mid=(lo+hi)/2;\n"
     "    const A=1+(AMAX-1)*Math.tanh(.55*Math.log(mid)/(AMAX-1));\n    if(A/mid>0.94) lo=mid; else hi=mid;}\n",
     "  /* fit-consistency check: the typical first-ask premium M_TYP (see its definition) */\n"
     "  const msTyp=at(\"prof\",158950,703000,model({...prof(\"prof\",158950,703000),ask:1}).V*M_TYP), eTyp=msTyp.Vmean/msTyp.inputs.ask;\n"),
    ("   [\"Listing premium implied by α and the 94% sale-to-ask ratio\",mid.toFixed(2)+\"× value\",\"1.05–1.30×\",\n"
     "    \"sellers list above supportable value\",mid>1.05&&mid<1.30],\n",
     "   [\"Fit-consistency check, not an external benchmark: expected price if it closes, as a share of the first ask, at the typical premium (\"+M_TYP.toFixed(2)+\"× value)\",pc(eTyp,1),\"87.5–92.5%\",\n"
     f"    \"the fit's own target: BizBuySell deal-level {100 * T_HAT['bbs']:.1f}% on the ask at sale = {100 * T_HAT['bbs'] * math.exp(-D_MS):.1f}% on the first ask\",eTyp>=.875&&eTyp<=.925],\n"),
]

patched = html
for old, new in PATCH:
    n = patched.count(old)
    assert n == 1, ("patch target not unique/found", n, old[:90])
    patched = patched.replace(old, new)
PDIR = os.path.join(OUT, "patched")
if os.path.isdir(PDIR):
    shutil.rmtree(PDIR)
shutil.copytree(TESTS, os.path.join(PDIR, "tests"))
with open(os.path.join(PDIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(patched)
diff = "".join(difflib.unified_diff(html.splitlines(True), patched.splitlines(True), "a/index.html", "b/index.html", n=1))
with open(os.path.join(OUT, "index.html.diff"), "w", encoding="utf-8") as f:
    f.write(diff)
log(f"  patched copy written ({len(PATCH)} replacements); diff {len(diff.splitlines())} lines -> {OUT}/index.html.diff")
# the fanNodes fix alone (the 'current' whole-spread baseline; separable from FAN_S)
assert html.count(FAN_OLD_BLOCK) == 1
fixonly = html.replace(FAN_OLD_BLOCK, FAN_FIX_BLOCK)
FIXDIR = os.path.join(OUT, "fixonly")
if os.path.isdir(FIXDIR):
    shutil.rmtree(FIXDIR)
shutil.copytree(TESTS, os.path.join(FIXDIR, "tests"))
with open(os.path.join(FIXDIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(fixonly)
with open(os.path.join(OUT, "fanNodes_fix.diff"), "w", encoding="utf-8") as f:
    f.write("".join(difflib.unified_diff(html.splitlines(True), fixonly.splitlines(True), "a/index.html", "b/index.html", n=1)))
log(f"  fanNodes fix alone -> {FIXDIR}/index.html (diff {OUT}/fanNodes_fix.diff)")

# ---------------- before / after through both versions of the model ----------------
BA_JS = r"""
const fs=require("fs"),vm=require("vm");
function load(file){ let html=fs.readFileSync(file,"utf8"); let src=html.slice(html.lastIndexOf("<script>")+8);
  src=src.slice(0,src.indexOf("/* ============ bar helpers"));
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN}; vm.createContext(ctx);
  vm.runInContext(src+";this.API={model,bestRatio,IND,sizeRefs,typMargin,fitClose};",ctx); return ctx.API; }
const V0=load(process.argv[2]), V1=load(process.argv[3]), V2=load(process.argv[4]), M=+process.argv[5];
const median=(A,ind,ern)=>{const I=A.IND[ind],RF=A.sizeRefs(ern);return {ind,ern,rev:ern/A.typMargin(ind,ern),yrs:6,buyers:I.buyers,
  franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40};};
const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
const out=[];
function row(lab,A,s){ const r=A.model(s), a=s.ask; return {case:lab,V:r.V,ask:a,rho:a/r.V,E_P:r.Vmean,E_P_over_ask:r.Vmean/a,
  median_P:r.Vreal,share_at_ask:r.capShare,ceil:r.ceil,below_ask_mean:(r.Vmean-r.capShare*r.ceil)/(a*(1-r.capShare)),PC:r.PC,EVp:r.EVp,
  q05:r.q(.05)/a,bear_lo:r.scen.bear[0]/a,bear_hi:r.scen.bear[1]/a,
  base_lo:r.scen.base[0]/a,base_hi:r.scen.base[1]/a,bull_lo:r.scen.bull[0]/a,bull_hi:r.scen.bull[1]/a,range_lo:r.range[0]/a,range_hi:r.range[1]/a,
  bear_lo_usd:r.scen.bear[0],bear_hi_usd:r.scen.bear[1]}; }
for(const [ver,A] of [["shipped",V0],["current",V1],["patched",V2]]){
  out.push({ver,...row("framework example (ask 0.79x value)",A,EX)});
  for(const [ind,ern] of [["prof",1.2e5],["prof",4e5],["home",4e5],["mfg",1.5e6]]){
    const t=median(A,ind,ern), V=A.model({...t,ask:1}).V;
    out.push({ver,...row(`${ind} median, $${ern/1e3}k earnings, typical premium`,A,{...t,ask:V*M})});
    out.push({ver,...row(`${ind} median, $${ern/1e3}k earnings, ask = value`,A,{...t,ask:V})});
    out.push({ver,...row(`${ind} median, $${ern/1e3}k earnings, ask 1.4x value`,A,{...t,ask:V*1.4})});
  }
  const t=median(A,"prof",158950); t.rev=703000;
  out.push({ver,...row("live self-audit: BizBuySell median profile at ask $350k/0.94",A,{...t,ask:350000/.94})});
  for(const [lab,s] of [["framework example",EX],["prof median $160k",median(A,"prof",1.6e5)],["mfg median $1.5M",median(A,"mfg",1.5e6)]])
    for(const th of [0,.75]){ const V=A.model({...s,ask:1}).V, b=A.bestRatio(s,th,900), r=A.model({...s,ask:V*b});
      out.push({ver,case:`optimal ask, ${lab}, theta=${th}`,rho:b,E_P_over_ask:r.Vmean/r.inputs.ask,PC:r.PC,EVp:r.EVp,share_at_ask:r.capShare}); }
}
console.log(JSON.stringify(out));
"""
with open(os.path.join(OUT, "before_after.js"), "w") as f:
    f.write(BA_JS)
p = subprocess.run(["node", os.path.join(OUT, "before_after.js"), INDEX, os.path.join(FIXDIR, "index.html"), os.path.join(PDIR, "index.html"), f"{M_TYP:.3f}"],
                   capture_output=True, text=True, timeout=900)
if p.returncode != 0:
    log(p.stderr[-3000:])
    raise SystemExit("before/after failed")
BA = pd.DataFrame(json.loads(p.stdout.strip().splitlines()[-1]))
BA.to_csv(os.path.join(OUT, "before_after.csv"), index=False)


def ba(case, ver, col):
    v = BA[(BA.case == case) & (BA.ver == ver)][col]
    return float(v.iloc[0]) if len(v) else float("nan")


log("\n=== Before / after (shipped page | current = fanNodes fix alone, whole spread | patched = fix + FAN_S) ===")
piv = BA.pivot_table(index="case", columns="ver", values=["rho", "E_P_over_ask", "share_at_ask", "below_ask_mean", "bear_lo", "bear_hi", "q05", "median_P", "EVp"],
                     aggfunc="first", sort=False)
with pd.option_context("display.width", 320, "display.max_columns", 30, "display.float_format", "{:,.4f}".format):
    log(piv.to_string())
CQ = "prof median, $400k earnings, typical premium"
Q8 = ba(CQ, "patched", "bear_lo")
Q8_LO, Q8_HI = math.floor((Q8 - 0.04) * 100) / 100, math.ceil((Q8 + 0.04) * 100) / 100
BL = ba(CQ, "patched", "below_ask_mean")
BL_LO, BL_HI = math.floor((BL - 0.04) * 100) / 100, math.ceil((BL + 0.04) * 100) / 100
R75 = ba("optimal ask, framework example, theta=0.75", "patched", "rho")
R75_CUR = ba("optimal ask, framework example, theta=0.75", "current", "rho")
R75_SHIP = ba("optimal ask, framework example, theta=0.75", "shipped", "rho")
R0_SHIP, R0_CUR = ba("optimal ask, framework example, theta=0", "shipped", "rho"), ba("optimal ask, framework example, theta=0", "current", "rho")
DER = {v: {k: ba(CQ, v, k) for k in ["E_P_over_ask", "share_at_ask", "below_ask_mean", "q05", "bear_lo", "bear_hi"]} for v in ["shipped", "current", "patched"]}
log(f"  test bands: q(.08)/ask [{Q8_LO}, {Q8_HI}] (patched {Q8:.3f}, current {ba(CQ, 'current', 'bear_lo'):.3f}); below-ask mean [{BL_LO}, {BL_HI}] (patched {BL:.3f}); "
    f"bestRatio(EX,.75) patched {R75:.3f} (current {R75_CUR:.3f})")

# ---------------- proposed new test file, run against the patched copy ----------------
NEW_TEST = r"""/* Realised-price block: FAN_S (calibrated) and M_TYP from fit/anchoring_realization.py (Oct 2026).
   Run: node tests/anchoring_realization.test.js */
const A=require("./load.js");
let pass=0,fail=0;
const ok=(c,msg)=>{ if(c) pass++; else { fail++; console.log("FAIL:",msg); } };
const median=(ind,ern)=>{const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/A.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,rec:I.rec,cc:.16,own:RF.own,
          mgt:RF.mgt,grw:I.grw,gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40};};
const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,
          fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
const r0=A.model(EX), FAN_S=r0.fanS, M_TYP=r0.mTyp;
ok(FAN_S>0&&FAN_S<=1&&Math.abs(FAN_S-__S__)<1e-9,`FAN_S is exposed and equals the calibrated __S__ (got ${FAN_S})`);
ok(M_TYP>1&&M_TYP<1.2&&Math.abs(M_TYP-__M__)<1e-9,`M_TYP is exposed and equals the fitted __M__ (got ${M_TYP})`);
for(const ind of Object.keys(A.IND)) for(const ern of [1.2e5,4e5,1.5e6]){
  const t=median(ind,ern), V=A.model({...t,ask:1}).V; if(V>8.5e6) continue;
  const r=A.model({...t,ask:V*(M_TYP||1.071)}), e=r.Vmean/r.inputs.ask;
  /* 1. at the typical first-ask premium the model closes where Main-Street averages do, on the first ask
        (BizBuySell 0.917 on the ask at sale = 0.905 on the first ask). Larger deals realise a few points more
        in the data, which the model does not have, so above Main Street only a floor is checked. */
  if(ern<1e6) ok(e>=.875&&e<=.925,`${ind} ${ern}: E[P|close]/ask ${e.toFixed(4)} at the typical premium`);
  else ok(e>=.875,`${ind} ${ern}: E[P|close]/ask ${e.toFixed(4)} below the Main-Street floor`);
  /* 2. a point mass at the ask, and the below-ask mean, in the calibrated range */
  ok(r.capShare>=.30&&r.capShare<=.55,`${ind} ${ern}: share closing at the ask ${r.capShare.toFixed(3)}`);
  const below=(r.Vmean-r.capShare*r.ceil)/(r.inputs.ask*(1-r.capShare));
  ok(below>=__BL_LO__&&below<=__BL_HI__,`${ind} ${ern}: below-ask mean ${below.toFixed(4)}`);
  /* 3. the downside narrows by the documented amount: the bear scenario's low end, q(.08)/ask
        (was __Q8_CUR__ with the whole value spread; Empire Flippers' analog q08 of sale/ask is 0.63) */
  const q8=r.q(.08)/r.inputs.ask;
  ok(q8>=__Q8_LO__&&q8<=__Q8_HI__,`${ind} ${ern}: bear low end q(.08)/ask ${q8.toFixed(4)}`);
  /* 4. narrowing keeps the centre: the uncapped median is V*A(rho)*(1+comp) */
  ok(Math.abs(r.VrealFree/(V*r.anchorF*(1+r.compPrem))-1)<.01,`${ind} ${ern}: uncapped median moved`);
  /* 5. the closing probability does not read the realised-price block */
  ok(Math.abs(r.PC-A.fitClose(r.inputs.ask,r.V,undefined,r.Vbase).p*Math.min(1,r.thinF))<1e-9||r.PC<=.02,`${ind} ${ern}: P_C changed`);
  ok(Math.abs(r.EVp-r.PC*r.Vmean)<=1e-9*r.EVp,`${ind} ${ern}: EVp = P_C x E[P|close]`);
}
/* 6. price rises with the ask, its share of the ask falls, everywhere */
for(const t of [EX,median("prof",1.6e5),median("mfg",1.5e6)]){
  const V=A.model({...t,ask:1}).V; let pv=-Infinity, pr=Infinity;
  for(let rho=.4;rho<=3.0001;rho+=.02){ const r=A.model({...t,ask:V*rho});
    ok(r.Vmean>=pv*(1-1e-9),`${t.ind} rho=${rho.toFixed(2)}: E[P|close] fell as the ask rose`);
    ok(r.Vmean/r.inputs.ask<=pr*(1+1e-9),`${t.ind} rho=${rho.toFixed(2)}: E[P|close]/ask rose with the ask`);
    pv=r.Vmean; pr=r.Vmean/r.inputs.ask; }
}
/* 7. the optimiser. theta=0 does not move. At theta=.75 (the default) bestRatio's utility has two near-equal
      peaks, an interior ask near __INT__ and the 1.5x cap. Which wins is a knife-edge in FAN_S (flip near
      __FLIP__) and in theta, so the WINNER is not pinned: the answer must be one of the two peaks, and the
      peaks must lie within 1% of value of each other (the page then shows the range; AUDIT.md, Oct 2026). */
const b0=A.bestRatio(EX,0,900), b75=A.bestRatio(EX,.75,900);
ok(b0>=1.08&&b0<=1.13,`bestRatio(EX,0) ${b0.toFixed(3)}`);
ok((b75>=1.08&&b75<=1.25)||b75>=1.45,`bestRatio(EX,.75) ${b75.toFixed(3)} is neither the interior peak nor the cap`);
{ const V=A.model({...EX,ask:1}).V; let ui=-Infinity, uc=-Infinity;
  for(let k=0;k<=140;k++){ const m=.80+k*.005, r=A.model({...EX,ask:V*m}), u=r.EVp+(1-r.PC)*.75*r.V-900*r.tMed;
    if(m<1.35) ui=Math.max(ui,u); else uc=Math.max(uc,u); }
  ok(Math.abs(ui-uc)<.01*V,`theta=.75: the two peaks differ by ${(100*(ui-uc)/V).toFixed(2)}% of value (expected a near-tie)`); }
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
""".replace("__S__", f"{FAN_S_REC:.2f}").replace("__M__", f"{M_TYP:.3f}").replace("__BL_LO__", f"{BL_LO:.2f}").replace("__BL_HI__", f"{BL_HI:.2f}") \
   .replace("__Q8_LO__", f"{Q8_LO:.2f}").replace("__Q8_HI__", f"{Q8_HI:.2f}").replace("__FLIP__", f"s = {S_FLIP_LO:.3f}-{S_FLIP_HI:.3f} on this page").replace("__INT__", INT_TXT) \
   .replace("__Q8_CUR__", f"{DER['current']['bear_lo']:.2f}")
with open(os.path.join(PDIR, "tests", "anchoring_realization.test.js"), "w") as f:
    f.write(NEW_TEST)
with open(os.path.join(OUT, "anchoring_realization.test.js"), "w") as f:
    f.write(NEW_TEST)


def run_test(path, label, cwd=None, timeout=900):
    t = time.time()
    try:
        p = subprocess.run(["node", path], capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        log(f"  {label}: TIMEOUT after {timeout}s")
        return {"label": label, "rc": -9, "summary": "timeout", "fails": []}
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    tail = lines[-1] if lines else (p.stderr.strip().splitlines() or [""])[-1]
    fails = [l for l in p.stdout.splitlines() if l.startswith("FAIL")]
    log(f"  {label}: rc={p.returncode} '{tail[:200]}' ({time.time() - t:.0f}s)" + (f"; first fails: {fails[:4]}" if fails else ""))
    return {"label": label, "rc": p.returncode, "summary": tail[:300], "fails": fails[:20]}


log("\n=== Tests ===")
TESTRES = [run_test(os.path.join(TESTS, "model.test.js"), "repo model.test.js on the CURRENT index.html"),
           run_test(os.path.join(PDIR, "tests", "model.test.js"), "model.test.js on the PATCHED copy"),
           run_test(os.path.join(PDIR, "tests", "fuzz.test.js"), "fuzz.test.js on the PATCHED copy"),
           run_test(os.path.join(PDIR, "tests", "anchoring_realization.test.js"), "new anchoring_realization.test.js on the PATCHED copy")]
cur_dir = os.path.join(OUT, "current_copy")
if os.path.isdir(cur_dir):
    shutil.rmtree(cur_dir)
shutil.copytree(TESTS, os.path.join(cur_dir, "tests"))
shutil.copy(INDEX, os.path.join(cur_dir, "index.html"))
shutil.copy(os.path.join(OUT, "anchoring_realization.test.js"), os.path.join(cur_dir, "tests", "anchoring_realization.test.js"))
TESTRES.append(run_test(os.path.join(cur_dir, "tests", "anchoring_realization.test.js"), "new test against the CURRENT model (should fail)"))
# the pending fits' own tests must keep passing with FAN_S on top: the stack page with the patch applied
STK_P = os.path.join(OUT, "pending_stack_with_fan")
if os.path.isdir(STK_P):
    shutil.rmtree(STK_P)
STACK_SKIPPED, STACK_REBASED = [], []
if len(PAGES) > 1 and PAGES[1][0].startswith("stack"):
    os.makedirs(STK_P)
    sp = open(PAGES[1][1], encoding="utf-8").read()
    STACK_REBASED = []
    for old, new in PATCH:
        if sp.count(old) == 1:
            sp = sp.replace(old, new)
        elif old in PATCH_STACK_ALT and sp.count(PATCH_STACK_ALT[old][0]) == 1:
            sp = sp.replace(*PATCH_STACK_ALT[old])
            STACK_REBASED.append(old.strip().splitlines()[0][:70])
        else:
            STACK_SKIPPED.append(old.strip().splitlines()[0][:70])
    shutil.copytree(TESTS, os.path.join(STK_P, "tests"))
    with open(os.path.join(STK_P, "index.html"), "w", encoding="utf-8") as f:
        f.write(sp)
    log(f"  stack + this patch: {len(PATCH) - len(STACK_SKIPPED) - len(STACK_REBASED)} of {len(PATCH)} replacements applied verbatim, {len(STACK_REBASED)} rebased onto "
        f"the pending optNote() ({STACK_REBASED}); skipped: {STACK_SKIPPED}")
    TESTRES.append(run_test(os.path.join(STK_P, "tests", "model.test.js"), "model.test.js on the pending stack + this patch"))
    shutil.copy(os.path.join(OUT, "anchoring_realization.test.js"), os.path.join(STK_P, "tests", "anchoring_realization.test.js"))
    TESTRES.append(run_test(os.path.join(STK_P, "tests", "anchoring_realization.test.js"), "new test on the pending stack + this patch"))

# rendered page: errors, unrendered templates, the new rows, the optimiser note, the self-audit row (headless Chromium)
UI_JS = r"""
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{
  const b=await pw.chromium.launch(); const res={};
  for(const f of process.argv.slice(2)){
    const p=await b.newPage({viewport:{width:1440,height:900}}); const errs=[];
    p.on("pageerror",e=>errs.push(e.message)); p.on("console",m=>{ if(m.type()==="error") errs.push("console: "+m.text()); });
    await p.goto("file://"+f); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000}); await p.waitForTimeout(1500);
    res[f]=await p.evaluate(()=>{ const T=document.body.innerText, g=id=>(document.getElementById(id)||{innerText:""}).innerText;
      return {calib:[...document.querySelectorAll("#calib .chk")].map(x=>x.innerText.replace(/\s+/g," ")).filter(x=>/premium|Realized price/.test(x)),
              rows:[...document.querySelectorAll("tr")].map(r=>r.innerText.replace(/\s+/g," ").slice(0,200)).filter(x=>/value spread kept|Anchoring strength/.test(x)),
              spread:[...document.querySelectorAll(".chk")].map(x=>x.innerText.replace(/\s+/g," ").slice(0,160)).filter(x=>/Value uncertainty|Realised-price fan/.test(x)),
              optimiser:{list:g("o_list"),listp:g("o_listp"),list2:g("o_list2"),listp2:g("o_listp2"),note:g("o_listnote")},
              eq_s:g("eq_s").replace(/\s+/g," ").slice(0,200), eq_ss:g("eq_ss").replace(/\s+/g," ").slice(0,200),
              rz:(document.querySelector(".rzf")||{innerText:""}).innerText.slice(0,300),
              unrendered_visible:(T.match(/\$\{[^}]{0,60}\}/g)||[]).length, katex:document.querySelectorAll(".katex-error").length,
              nan:(T.match(/NaN|Infinity|undefined/g)||[]).length}; });
    res[f].errors=errs; await p.close(); }
  await b.close(); console.log(JSON.stringify(res)); })();
"""
with open(os.path.join(OUT, "ui_check.js"), "w") as f:
    f.write(UI_JS)
UI = {}
try:
    _pages = [INDEX, os.path.join(PDIR, "index.html")] + ([os.path.join(STK_P, "index.html")] if os.path.exists(os.path.join(STK_P, "index.html")) else [])
    p = subprocess.run(["node", os.path.join(OUT, "ui_check.js")] + _pages, capture_output=True, text=True, timeout=900)
    UI = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 else {"error": p.stderr[-500:]}
except Exception as e:
    UI = {"error": str(e)}
log("  rendered pages (headless Chromium):", json.dumps(UI, ensure_ascii=False)[:5000])
UIP = UI.get(os.path.join(PDIR, "index.html"), {})
UIC = UI.get(INDEX, {})
UI_NOTE_SHOWN = "close to a tie, so read the patient-seller price as a range" in UIP.get("optimiser", {}).get("note", "")
UIS = UI.get(os.path.join(STK_P, "index.html"), {})
UI_NOTE_SHOWN_STACK = "close to a tie, so read the patient-seller price as a range" in UIS.get("optimiser", {}).get("note", "")
log(f"  optimiser range note on the default inputs: patched page {UI_NOTE_SHOWN}; stack + patch {UI_NOTE_SHOWN_STACK} ({len(UIS.get('errors', []))} page errors on the stack page)")
TESTRES.append(run_test(os.path.join(PDIR, "tests", "browser.sweep.js"), "browser.sweep.js on the PATCHED copy", timeout=2400))
TESTRES.append(run_test(os.path.join(PDIR, "tests", "browser.inputs.js"), "browser.inputs.js on the PATCHED copy", timeout=1200))
TESTRES.append(run_test(os.path.join(FIXDIR, "tests", "model.test.js"), "model.test.js on the fanNodes fix alone"))
TESTRES.append(run_test(os.path.join(FIXDIR, "tests", "fuzz.test.js"), "fuzz.test.js on the fanNodes fix alone"))
TESTRES.append(run_test(os.path.join(FIXDIR, "tests", "browser.inputs.js"), "browser.inputs.js on the fanNodes fix alone", timeout=1200))
tests_ok = all(t["rc"] == 0 for t in TESTRES[1:4]) and TESTRES[4]["rc"] != 0 and all(t["rc"] == 0 for t in TESTRES if "fix alone" in t["label"])

# ---------------- AUDIT.md and fit/README.md (patched copies) ----------------
HEADROOM = 100 * (float(IBW["5M-50M"].mean()) - 1)
stk_name = PAGES[1][0] if len(PAGES) > 1 and PAGES[1][0].startswith("stack") else None
FL_STK = FLIP.get((stk_name, "framework example")) if stk_name else None
OM_STK = OM[OM.page == stk_name].set_index("s") if stk_name else None
MARGIN_STK = float(OM_STK.loc[FAN_S_REC, "margin_interior_minus_corner"]) if stk_name is not None and FAN_S_REC in OM_STK.index else float("nan")
uP = OU[(OU.page == PAGES[0][0])].set_index("mode")
EXC = "framework example (ask 0.79x value)"
P_GE_STK = float(MIX[MU_G >= FL_STK[1]].sum() / MIX.sum()) if FL_STK and FL_STK[1] else float("nan")
FLIP_TXT = f"{S_FLIP_LO:.3f}-{S_FLIP_HI:.3f}"
STK_FLIP_TXT = (f"{FL_STK[0]:.3f}-{FL_STK[1]:.3f}" if FL_STK and FL_STK[0] is not None and FL_STK[1] is not None
                else ("above 1.0 (never in the grid)" if FL_STK and FL_STK[1] is None else "n/a"))
WIN_TXT = "interior one" if MARGIN_FAN > 0 else "cap"
OPTION_B = ("Option B (if sign-off keeps the 1.5x answer): ship FAN_S for the realised-price display only and give bestRatio's candidate asks "
            "the whole fan, since an ask set as a multiple of V carries no information: `let FAN_NODES={}; function fanNodes(sh){ sh=(sh===undefined?FAN_S:sh); "
            "if(FAN_NODES[sh]) return FAN_NODES[sh]; ... c=sh*g.c, B=sh*g.B ... return FAN_NODES[sh]=out; }`, `const RN=fanNodes(s.fanShare);` in model(), "
            "and `model({...s0,ask:V*m,fanShare:1})` inside bestRatio's U(). The default patient-seller answer then stays at the cap "
            f"({R75_CUR:.2f}x) and theta=0 is unchanged; the displayed price at that ask is still the calibrated one.")
AUDIT_NOTE = f"""
## Realised-price fan (FAN_S), October 2026

`fit/anchoring_realization.py` (revision 3). The earlier note that "no anchoring setting closes the gap" with IBBA was a
fan-width problem, not an anchoring one: sale-to-ask data fix (1 - alpha) * s, and with the value model's whole
spread (s = 1) no alpha brings E[P|close]/ask up to the market averages.

- **fanNodes() fixed (revision 4).** The 48 fan nodes were read off a 4,000-point grid in slices of k = M/N = 83.33
  points: each slice summed 84 points, overlapped the next and divided by 83.33, so every node ran
  {100 * NODES['interior_bias_min']:.1f}-{100 * NODES['interior_bias_max']:.1f}% high (the top one {100 * NODES['bias_top']:.1f}%) and their mean was {NODES['shipped_mean']:.4f} against the fan's {NODES['exact_mean']:.4f}
  (measured mean/median 1.0907). They are now exact slice means (closed form per piece of the piecewise-linear log fan;
  {NODES['exact_vs_brute_interior']:.0e} from brute force). With the whole spread this lowers E[P|close] by up to {-100 * BUG[:, 0].min():.2f}% and, at the typical premium,
  E[P|close]/first ask from {DER['shipped']['E_P_over_ask']:.3f} to {DER['current']['E_P_over_ask']:.3f}. Every 'current' figure below is the fixed page with the whole spread.
- **What the data show (robust).** At the typical first-ask premium ({M_TYP:.3f}x value) the whole spread gives E[P|close]/ask
  {RB['bbs']['current']:.3f}, short of every like-for-like market average: BizBuySell's deal-level {RB['bbs']['target']:.3f} on the first ask, and IBBA's
  under-$1M deals (binned by sale price) {RB['ibc']['target']:.3f} against the model's {RB['ibc']['current']:.3f}. Narrowing the realised-price fan and
  selection on closing (whole fan, each scenario weighted by its own chance of closing; {RB['bbs']['selection']:.3f}) both close the gap.
- **What changed.** The realised-price fan keeps FAN_S = {FAN_S_REC:.2f} of the value model's log spread (fan nodes are slice means of
  R(p)^FAN_S; the median, P_C and everything else are unchanged). E[P|close]/ask at the typical premium goes from {AT1['Er']:.3f} to
  {AT['Er']:.3f} of the first ask ({AT1['Er'] * ED:.3f} to {AT['Er'] * ED:.3f} of the ask at sale). FAN_S is **calibrated, not fitted**: the
  mechanism is not identified, and it is labelled that way in the Data tab.
- **How sure.** Per source s (premium reading G, Main-Street d): BizBuySell {EST['bbs']:.2f}, IBBA under $500K {EST['ib1']:.2f}, $500K-1M
  {EST['ib2']:.2f} (under $1M as one source {EST['ibc']:.2f}), DealStats {EST['ds']:.2f}. Averaged over four source structures (IBBA's bands as two
  sources or one; DealStats in or out), three readings of the typical premium and two of the ask: {POST['mean']:.3f} (sd {POST['sd']:.2f},
  90% {POST['q05']:.2f}-{POST['q95']:.2f}), rounded to {FAN_S_REC:.2f}, which is {CUT_DIST:.3f} from the rounding cut: {SPEC_LO:.2f}-{SPEC_HI:.2f} are equally
  defensible. P(s < 1) is {P_LT1_RANGE[0]:.2f}-{P_LT1_RANGE[1]:.2f} by structure, but only under narrowing: under selection the sources need
  s of {SEL_TXT}. If the spread of asks across listings were pricing noise rather than information, s would be {NOISE_TXT}
  (Empire Flippers' pass-through {EF_PAR['tobit'][0]:.2f} implies a noise sd near {NOISE_SD:.2f}; an analog). Calibrated to 2022+ alone: {RUN22['post']['mean']:.2f}.
- **Which ask.** The model's ask is the first listing price. The market sources report the ask standing at sale, about
  {100 * D_MS:.1f}% below the first on Main Street (DealLedger net asking-price drift x IBBA months listed to LOI). That figure rests on
  an error rule: {DL_RULE['share_big']:.0%} of the observed ask changes move by more than 0.5 in logs (median factor {math.exp(DL_RULE['median_abs_big']):.1f}; many with a
  changed title, index-page keys or a factor of ten) and are treated as no change; taken at face value the drift is
  {DL_RULE['drift_untrimmed']:+.3f} a year (the sign flips), excluding them gives {DL_RULE['drift_exclude']:+.3f}. Empire Flippers' {100 * E_ALL1['d']:.1f}% gap comes
  mostly from re-pricing as monthly profit arrives and does not transfer.
- **Downside.** The bear scenario narrows: at the typical premium its low end q(.08) goes from {DER['current']['bear_lo']:.2f} to {DER['patched']['bear_lo']:.2f}
  of the ask (Empire Flippers' analog q08 of sale/last ask: {EF_ALL['q08']:.2f}); for the framework example the bear band goes
  from ${ba(EXC, 'current', 'bear_lo_usd') / 1e6:.2f}M-${ba(EXC, 'current', 'bear_hi_usd') / 1e6:.2f}M to ${ba(EXC, 'patched', 'bear_lo_usd') / 1e6:.2f}M-${ba(EXC, 'patched', 'bear_hi_usd') / 1e6:.2f}M.
  The Data tab now separates value uncertainty (the whole spread) from the realised-price fan; the scenario equations show R^s.
- **Calibrated near 1.07x, extrapolated above.** FAN_S is set at the typical premium. At asks of 1.4-1.5x value, where the
  patient seller's recommendation is decided, it is an extrapolation, and the two mechanisms part by {100 * SEP_HI[0]:.1f}-{100 * SEP_HI[1]:.1f} points of
  E[P|close]/ask. The extrapolation, not the fit, sets the patient-seller answer.
- **Optimiser (needs sign-off before merge).** For a patient seller (theta = .75, the default) bestRatio's utility has two
  near-equal peaks, ~{INT_TXT} and the 1.5x cap. At FAN_S = {FAN_S_REC:.2f} the {WIN_TXT} wins by {100 * abs(MARGIN_FAN):.2f}% of value (framework
  example), so the default recommendation moves from {R75_CUR:.2f}x to {R75:.2f}x. On this page the cap returns for s between {FLIP_TXT}
  (P(s >= {S_FLIP_HI:.3f}) = {P_ABOVE_FLIP:.2f}) and, at FAN_S = {FAN_S_REC:.2f}, for theta from {(JUMP_FAN if JUMP_FAN is not None else float('nan')):.2f}; across {SPEC_LO:.2f}-{SPEC_HI:.2f} the two peaks
  never differ by more than {100 * MAX_ABS_MARGIN_RANGE:.2f}% of value. With the pending overpricing_time stack the flip is at s {STK_FLIP_TXT}.
  This is a coin-flip, and the {INT_TXT} end follows from choosing narrowing and applying it to an ask the console sets as a
  multiple of V, which carries no information: under the information reading such an ask faces the whole fan, and the
  whole fan or selection keep the cap. The whole fan, though, misses realisation at typical asks, so neither end is a data
  result. The page therefore shows the patient-seller price as a range whenever the other peak is within 1% of value, and
  the test checks the near-tie, not the winner. {OPTION_B} This replaces the "about 1.57x" note under "Left as documented judgment".
- **Known inconsistency.** The ask ceiling still takes headroom from IBBA's $5M+ ratio (up to {HEADROOM:.1f}% above the ask),
  which is a ratio to an advisor's benchmark, not to an ask.
- **Data notes.** BizBuySell sector names were harmonised across the 2016-18 tables ({SEC.label1.nunique()} spellings -> {SEC.sector_h.nunique()} sectors) before
  clustering; IBBA quarters are resampled in calendar blocks ({len(IB_MISSING)} quarters are missing inside {IBW.index[0]}-{IBW.index[-1]}, no wrap-around);
  IBBA values are whole percentages read off chart labels; the BizBuySell 2018 market table had its price columns swapped
  (a check only).
"""
aud = open(f"{REPO}/AUDIT.md", encoding="utf-8").read()
OLD_AUD = "a patient seller (θ = 0.75) is told to ask\n  about 1.57×, with a 34% chance of closing."
AUD_REPLACED = OLD_AUD in aud
if AUD_REPLACED:
    aud = aud.replace(OLD_AUD, f"a patient seller (θ = 0.75) was told to ask\n  about 1.57×, with a 34% chance of closing (superseded: see \"Realised-price fan\" below; now a near-tie, shown as a range).")
with open(os.path.join(PDIR, "AUDIT.md"), "w", encoding="utf-8") as f:
    f.write(aud.rstrip("\n") + "\n" + AUDIT_NOTE)
rd = open(f"{REPO}/fit/README.md", encoding="utf-8").read()
ROW_README = ("| `FAN_S` (realised-price fan share, calibrated) and `M_TYP` | `anchoring_realization.py` | BizBuySell closed-deal cells 2016-18; IBBA Market Pulse "
              "realised/ask 2017-2026 and months to close; DealStats ask/sale medians; DealLedger asking-price panel (ask drift); Empire Flippers per-deal "
              "reconstruction and first asks (analog check) | as for the IBBA and DealLedger rows; EF via its public API |\n")
anchor = "| `buyer_mix` "
rd = rd.replace(anchor, ROW_README + anchor, 1) if anchor in rd else rd + "\n" + ROW_README
rd = rd.replace("- Anchoring of sale price on ask. No reachable dataset has both prices for small private\n  deals.",
                "- Anchoring of sale price on ask (alpha, A_max). Sale-to-ask data fix (1 - alpha) * s, not alpha;\n  `anchoring_realization.py` calibrates s and leaves alpha as judgment.")
os.makedirs(os.path.join(PDIR, "fit"), exist_ok=True)
with open(os.path.join(PDIR, "fit", "README.md"), "w", encoding="utf-8") as f:
    f.write(rd)
for nm in ["AUDIT.md", "fit/README.md"]:
    a_ = open(f"{REPO}/{nm}", encoding="utf-8").read().splitlines(True)
    b_ = open(os.path.join(PDIR, nm), encoding="utf-8").read().splitlines(True)
    with open(os.path.join(OUT, nm.replace("/", "_") + ".diff"), "w", encoding="utf-8") as f:
        f.writelines(difflib.unified_diff(a_, b_, f"a/{nm}", f"b/{nm}", n=1))

# =====================================================================================
# 12. RESULT.json (same content as the structured return)
# =====================================================================================
SE_LNM = math.sqrt(float(np.var([t["D"] for t in TB], ddof=1)) + SD_D ** 2)
lo_ = LOSO
P_GE95 = float(MIX[MU_G >= 0.95].sum() / MIX.sum())
tr_ = {t["label"]: t["summary"] for t in TESTRES}
DSPEC = SPECT.set_index(["reading", "d"])
g0, gD, g88 = DSPEC.loc[("G", 0.0)], DSPEC.loc[("G", round(D_MS, 4))], DSPEC.loc[("G", round(E_ALL1["d"], 4))]
gU = DSPEC.loc[("G", round(D_UNTRIM, 4))]
PEP_LIT_TXT = '/'.join(f"{r_['model_fitted']:.3f}" for r_ in pep_lit)
PEP_MEAN_TXT = '/'.join(f"{r_['model_fitted']:.3f}" for r_ in pep_mean)
PERIOD22 = [r_ for r_ in EFROWS if r_['sample'].startswith('period=2022') and r_['stat'] == 'pi'][0]
PERIOD14 = [r_ for r_ in EFROWS if r_['sample'].startswith('period=2014') and r_['stat'] == 'pi'][0]
HV_DS = HV['DealStats ln(median ask/median sale), 2H2018-1H2024, at the Main-Street premium']
STRUCT_ROUND_TXT = ", ".join(f"{SNAME[nm]} {R05(ps_['mean']):.2f}" for nm, ps_ in POST_S.items())
STRUCT_TXT = "; ".join(f"{SNAME[nm]} {ps_['mean']:.3f} (sd {ps_['sd']:.2f}, P(s<1) {ps_['p_lt1']:.2f})" for nm, ps_ in POST_S.items())
GRID_N = int(ginfo["n"])
ALONE_FLIP_TXT = "; ".join(f"{k_[0].replace(' alone', '')} {v[0]}-{v[1]}" for k_, v in FLIP.items() if k_[0].endswith("alone") and k_[1] == "framework example")
STACK_TXT = ("; ".join(stack_note) + (" | not stacked: " + "; ".join(stack_fail) if stack_fail else ""))
VALID_TXT = (
    f"LEAVE-ONE-SOURCE-OUT (primary structure S3, tau from the two training sources only): IBBA <$500K predicted {lo_['ib1']['pred_dl']:.3f} vs {lo_['ib1']['obs']:.3f} "
    f"(z {lo_['ib1']['z_train_tau']:+.2f}: FAILS, a source-level disagreement one s cannot absorb; Bayesian predictive with the tau prior {lo_['ib1']['pred_bayes']:.3f} +- "
    f"{lo_['ib1']['sd_bayes']:.3f}, z {lo_['ib1']['z_bayes']:+.2f}); IBBA $500K-1M {lo_['ib2']['pred_dl']:.3f} vs {lo_['ib2']['obs']:.3f} (z {lo_['ib2']['z_train_tau']:+.2f}); "
    f"BizBuySell {lo_['bbs']['pred_dl']:.3f} vs {lo_['bbs']['obs']:.3f} (z {lo_['bbs']['z_train_tau']:+.2f}) is NOT independent (the shared premium uses BizBuySell's own D); "
    f"rerun with the premium from BizBuySell's OTHER-period headline ratio of medians (D {lo_['bbs_otherD']['D_other']:.4f}, {', '.join(lo_['bbs_otherD']['periods'])}): "
    f"{lo_['bbs_otherD']['pred_dl']:.3f} vs {lo_['bbs_otherD']['obs']:.3f} (z {lo_['bbs_otherD']['z_train_tau']:+.2f}; same platform, so only partly independent; the prediction "
    f"barely moves because the training s and the held-out curve both shift with the premium). "
    f"DealStats left out of S4: the three sale/ask sources (s {lo_['ds']['s_train']:.3f}) predict its ln(median ask/median sale) {lo_['ds']['pred']:.3f} vs {lo_['ds']['obs']:.3f} "
    f"(z {lo_['ds']['z']:+.2f}). HELD OUT (model at FAN_S={FAN_S_REC:.2f} vs whole spread, on the data's ask): IBBA $1-2M {HV['IBBA 1M-2M mean, 27 quarters']['observed']:.3f} vs "
    f"{HV['IBBA 1M-2M mean, 27 quarters']['model_fitted']:.3f} (whole spread {HV['IBBA 1M-2M mean, 27 quarters']['model_current_s1']:.3f}); BizBuySell 2025 {BBS25:.2f} vs "
    f"{HV['BizBuySell 2025 national mean']['model_fitted']:.3f} ({HV['BizBuySell 2025 national mean']['model_current_s1']:.3f}); BizBuySell $1M+ {Y_GE1M:.3f} vs "
    f"{HV['BizBuySell $1M+ mean (sale-binned)']['model_fitted']:.3f} (missing size effect); Pepperdine 2016 Fig 98 (PDF p.{PEP_PAGE}, respondent n not reported) read literally "
    f"as band MEDIANS .90/.93/.90 vs {PEP_LIT_TXT} (RMSE {PEP_RMSE['literal medians'][0]:.3f}, whole spread {PEP_RMSE['literal medians'][1]:.3f}: no better), read as band means "
    f"vs {PEP_MEAN_TXT} (RMSE {PEP_RMSE['as means'][0]:.3f} vs {PEP_RMSE['as means'][1]:.3f}). These held-out levels sit above both the narrowed and the whole-spread model, so they "
    f"show that the level must rise, not that narrowing (rather than selection) is the mechanism. "
    f"TEMPORAL (fit on IBBA to 2021Q4 + BizBuySell 2016-18 with training-only variances, s={mu_tr:.2f}; test IBBA 2022Q1-2026Q2 three bands + BizBuySell 2025): RMSE of the "
    f"4 test means {TEMP_RMSE['fitted model (1 parameter, s)']:.3f} vs whole spread {TEMP_RMSE['current model (s=1)']:.3f}, one-level naive {TEMP_RMSE['naive: one pooled level']:.3f}, "
    f"per-target naive {TEMP_RMSE['naive: per-target training mean']:.3f} (BEATS the model); over {len(qerr['fitted'])} test quarter-bands {TEMP_Q['fitted']:.3f} vs whole spread "
    f"{TEMP_Q['current']:.3f}, naive per band {TEMP_Q['naive per band']:.3f} (BEATS the model), naive one level {TEMP_Q['naive one level']:.3f}. "
    f"EMPIRE FLIPPERS (analog; online; 2,644 deals): under premium reading G (comparable with the Main-Street primary; premium {M_EF_G:.3f}) s_EF = {S_EF_G:.2f} "
    f"(month-cluster SE {SE_EF['s_G']:.3f}), giving share at the ask {PRED_EF_G['pi']:.3f} vs {EF_ALL['pi']:.3f} (SE {SE_EF['pi']:.3f}), below-ask mean {PRED_EF_G['below']:.3f} vs "
    f"{EF_ALL['below']:.3f}, q05/q08 {PRED_EF_G['q05']:.3f}/{PRED_EF_G['q08']:.3f} vs {EF_ALL['q05']:.3f}/{EF_ALL['q08']:.3f}; at FAN_S {AT_FAN_EF_G['pi']:.3f} / {AT_FAN_EF_G['below']:.3f} / "
    f"q08 {AT_FAN_EF_G['q08']:.3f}; whole spread {AT_1_EF_G['pi']:.3f} / {AT_1_EF_G['below']:.3f} / q08 {AT_1_EF_G['q08']:.3f} (the whole spread's tail is far too fat). Under reading R "
    f"(EF's hedonic V is a geometric mean, premium {M_EF:.3f}) s_EF = {S_EF:.2f}. FIRST ask (1,754 deals): s {E_ALL1['s_first_G']:.2f} vs {E_ALL1['s_last_G']:.2f} on the last ask "
    f"(reading G; R {E_ALL1['s_first']:.2f} vs {E_ALL1['s_last']:.2f}). The point mass moves in steps of 1/48 and does not discriminate; EF 2022-26 is missed (observed "
    f"{PERIOD22['observed']:.2f} vs model {PERIOD22['model_s_EF']:.2f}). "
    f"TESTS on the patched copy: model.test.js {tr_['model.test.js on the PATCHED copy']}; fuzz.test.js {tr_['fuzz.test.js on the PATCHED copy']}; new test "
    f"{tr_['new anchoring_realization.test.js on the PATCHED copy']} (fails on the current model: {tr_['new test against the CURRENT model (should fail)']}); "
    f"browser.sweep.js {tr_.get('browser.sweep.js on the PATCHED copy', 'n/a')}; browser.inputs.js {tr_.get('browser.inputs.js on the PATCHED copy', 'n/a')}; "
    f"headless render: {len(UIP.get('errors', []))} page errors, {UIP.get('katex', 'n/a')} KaTeX errors, {UIP.get('unrendered_visible', 'n/a')} unrendered templates, optimiser range note shown "
    f"on the default inputs: {UI_NOTE_SHOWN} (stack + patch: {UI_NOTE_SHOWN_STACK}); on the pending-fit stack + this patch: model.test.js {tr_.get('model.test.js on the pending stack + this patch', 'n/a')}, new test "
    f"{tr_.get('new test on the pending stack + this patch', 'n/a')}. The fanNodes fix ALONE (fixonly/): model.test.js {tr_.get('model.test.js on the fanNodes fix alone', 'n/a')}; "
    f"fuzz.test.js {tr_.get('fuzz.test.js on the fanNodes fix alone', 'n/a')}; browser.inputs.js {tr_.get('browser.inputs.js on the fanNodes fix alone', 'n/a')}.")

PARAMS = [
    {"param": "FAN_S (new constant): share of the value model's out-of-fold log residual spread kept in the realised-price fan once a business is listed; fan nodes become slice means "
              "of R(p)^FAN_S. CALIBRATED (reduced form; the mechanism is not identified), not fitted",
     "current_value": "1 (implicit: W = V*R(p), the whole out-of-fold fan)",
     "fitted_value": (f"ROBUST FINDING: at the typical first ask (M_TYP = {M_TYP:.3f} x V) the whole spread gives E[P|close]/first ask {RB['bbs']['current']:.3f}, short of every "
                      f"like-for-like market average: BizBuySell {RB['bbs']['target']:.3f}; IBBA under $1M, binned by sale price, {RB['ibc']['target']:.3f} vs the model's {RB['ibc']['current']:.3f}; "
                      f"IBBA $500K-1M {RB['ib2']['target']:.3f} vs {RB['ib2']['current']:.3f}. Both readings raise it: narrowing to FAN_S gives {RB['bbs']['narrowed']:.3f} (BizBuySell basis), selection "
                      f"on closing with the whole fan {RB['bbs']['selection']:.3f}. CALIBRATION (conditional on narrowing and on an informative premium): model-averaged posterior mean "
                      f"{POST['mean']:.3f} (sd {POST['sd']:.3f}; 90% {POST['q05']:.2f}-{POST['q95']:.2f}; 95% {POST['q025']:.2f}-{POST['q975']:.2f}). By source structure: {STRUCT_TXT}. "
                      f"By premium reading G/M/R {by_read['G']:.2f}/{by_read['M']:.2f}/{by_read['R']:.2f}; equal reading weights {POST_EQ['mean']:.3f}; first-ask reading (d=0) "
                      f"{by_ask['first-ask reading (d=0)']:.2f}, last-ask reading {by_ask['last-ask reading']:.2f}. Per source (reading G, d={D_MS:.4f}, ALPHA .55, AMAX 1.30): BizBuySell "
                      f"{EST['bbs']:.3f}, IBBA <$500K {EST['ib1']:.3f}, IBBA $500K-1M {EST['ib2']:.3f}, IBBA under $1M as one {EST['ibc']:.3f}, DealStats {EST['ds']:.3f} (DealStats by reading "
                      f"G/M/R {DS_BY_READ['G']:.2f}/{DS_BY_READ['M']:.2f}/{DS_BY_READ['R']:.2f}). Under SELECTION the sources need s of {SEL_TXT}: s >= 1. Under PRICING NOISE in the premium "
                      f"(ln ask/V ~ N(ln M_TYP, sd^2) independent of W) the primary structure gives {', '.join(f'{v[0]:.2f}' for v in HET.values())} at sd {', '.join(str(k) for k in HET)} "
                      f"(vs {PRIMARY['post']['mean']:.2f} at 0; from sd {CENS_SD} the IBBA $500K-1M level cannot be reached at any s >= 0.05, which argues against noise that large). Other sensitivities (primary structure, reading G): d=0 "
                      f"{g0.post_mean:.2f}; d untrimmed ({D_UNTRIM:+.3f}) {gU.post_mean:.2f}; EF's d={E_ALL1['d']:.3f} {g88.post_mean:.2f}; IBBA quarters deal-weighted {DW['mean']:.2f}; "
                      f"IBBA bands read as ask-defined {UNB['mean']:.2f}; calibrated to 2022+ only {RUN22['post']['mean']:.2f}. Analogs, not pooled: EF reading G last ask {S_EF_G:.2f}, "
                      f"first ask {E_ALL1['s_first_G']:.2f}"),
     "se": (f"posterior sd {POST['sd']:.3f}: Bayesian random effects per structure (k = 2-4 sources; mu ~ N(1, 0.5^2), the current value weakly held; tau ~ half-normal(0.5), "
            f"so tau's uncertainty is carried), mixed over four source structures (equal weights), the premium reading (G {W_READ['G']}, M {W_READ['M']}, R {W_READ['R']}) and the ask "
            f"reading ({W_LAST} last ask with d ~ N({D_MS:.4f}, {SD_D:.4f}^2), {1 - W_LAST:.2f} first ask). P(s<1) {POST['p_lt1']:.2f} overall, {P_LT1_RANGE[0]:.2f}-{P_LT1_RANGE[1]:.2f} by "
            f"structure, all CONDITIONAL on the narrowing reading (selection puts s >= 1) and on the premium's spread across listings being informative (pricing noise of sd "
            f"0.2-0.3 would give {S_AT_SD(0.2):.2f}-{S_AT_SD(0.3):.2f}; the EF analog's pass-through {EF_PAR['tobit'][0]:.3f} (SE {EF_PAR['tobit'][1]:.3f}) implies a noise sd of "
            f"{NOISE_SD:.3f}, 95% upper {NOISE_SD_HI:.3f}, i.e. s {S_AT_SD(NOISE_SD):.2f}-{S_AT_SD(NOISE_SD_HI):.2f}, but Main-Street asks may be noisier). Structural range of what the data "
            f"allow: about {S_AT_SD(0.3):.2f} (noise) to {min(SEL_S['bbs'][0], 1.6):.2f}+ (selection). Primary structure: HKSJ SE {pdl['se_hksj']:.3f}, t(2) 95% CI {pdl['ci95_hksj'][0]:.2f} to "
            f"{pdl['ci95_hksj'][1]:.2f}; DL tau {pdl['tau']:.3f} (Q {pdl['Q']:.1f} on 2 df); per-source bootstrap SE " + ", ".join(f"{k} {math.sqrt(PRIMARY['var_all'][k]):.3f}" for k in ALLKEYS) +
            f" (BizBuySell cells clustered by {SEC.sector_h.nunique()} harmonised sectors, IBBA quarters in calendar blocks of 4 without wrap-around, DealStats half-years iid; "
            f"{B_BOOT} replicates primary, {B_SPEC} elsewhere). Tau-prior sensitivity (primary structure): half-normal(0.25) / half-Cauchy(0.25) / uniform give "
            + "/".join(f"{v['mean']:.2f}" for v in TAU_SENS.values()) + f" (sd " + "/".join(f"{v['sd']:.2f}" for v in TAU_SENS.values()) + ")"),
     "n": (f"BizBuySell {len(SEC)} sector cells / {int(SEC.n_sales.sum()):,} closed sales 2016-18 ({SEC.sector_h.nunique()} harmonised sectors); IBBA {len(IBW)} quarters 2017Q4-2026Q2 "
           f"({len(IB_MISSING)} missing inside the span; about {IBC['<500K'].mean():.0f} and {IBC['500K-1M'].mean():.0f} closed deals a quarter in the two bands); DealStats 12 half-years 2H2018-1H2024; "
           f"DealLedger {len(DLP):,} listings seen twice or more, {DLP.yrs.sum():,.0f} listing-years, {DLP.broker.nunique()} brokers (ask drift); IBBA time-to-close fits "
           f"({int(sum(r[4] for r in T_ROWS)):,} deals); EF {EF_ALL['n']:,} deals (last ask) and {E_ALL1['n']:,} with a reconstructed first ask (analog, not pooled)"),
     "method": (f"Harness grid of the model itself ({GRID_N:,} evaluations: s 0.05-1.60, ask/V {M_GRID[0]:.2f}-{M_GRID[-1]:.2f} in 1% log steps, ALPHA 5 values, AMAX 1.30/1.66), fan nodes as "
                "slice means of R^s, plus each slice's own closing weight for the selection alternative; P/ask verified scale-free across 16 industries x 4 sizes (<= 1.04e-4). The model's ask "
                "is the FIRST listing price, so each target r becomes r*e^-d and the premium m*e^d, with d the first-to-last ask gap among sold deals (DealLedger net asking-price drift per "
                "listing-year, |change| > 0.5 log treated as no change, x IBBA mean months listing->LOI). Typical premium readings: G = exp(D + d + E ln R) (V is the fan median, E ln R = "
                f"{ELNR:.4f}), M = the premium at which the model's median closed price is V, R = exp(D + d). Per source s solves E[P|close]/first ask = target*e^-d (IBBA binned by sale price "
                "through a lognormal closed-deal size fitted to IBBA band counts; IBBA under $1M as one source = band means weighted by closed deals); DealStats: the model's ln(median "
                "ask/median sale) at DealStats' own premium = its D + d. Pooled per structure by Bayesian RE on a (mu, tau) grid (DL and HKSJ reported); posteriors mixed over structure, "
                "premium reading and d; rounded to 0.05."),
     "validation": VALID_TXT,
     "recommended_value": (f"{FAN_S_REC:.2f}: the model-averaged posterior mean {POST['mean']:.3f} rounded to 0.05, calibrated on the EXACT fan nodes (revision 3, on the "
                           f"shipped nodes that ran ~0.8% high, gave 0.832 (sd 0.202) -> 0.85). It lies {CUT_DIST:.3f} from the rounding cut, so "
                           f"{SPEC_LO:.2f}-{SPEC_HI:.2f} are equally defensible (by structure {STRUCT_ROUND_TXT}; "
                           f"equal reading weights {R05(POST_EQ['mean']):.2f}). Label it 'calibrated to market sale-to-ask averages; mechanism not identified' (badge 'calibrated', not "
                           f"'fitted'). Ship only with explicit sign-off on the patient-seller consequence (a coin-flip; see the optimiser row) and with the range note in the UI. Refit if "
                           f"ALPHA changes (ALPHA .30/.45/.55/.70/.85 -> {', '.join(f'{x:.2f}' for x in P13.s_pooled_post)}, primary structure)")},
    {"param": "fanNodes(): the 48 equal-probability slice means of the realised-price fan (BUG FIX found by an independent review; not a parameter)",
     "current_value": (f"shipped: a 4,000-point grid read in slices of k = M/N = 83.33 points; each slice sums 84 points (j < k), overlaps the next and divides by 83.33. Nodes' mean "
                       f"{NODES['shipped_mean']:.4f}; shipped/exact per node {100 * NODES['interior_bias_min']:+.2f}% to {100 * NODES['interior_bias_max']:+.2f}% inside, top {100 * NODES['bias_top']:+.2f}%, "
                       f"bottom {100 * NODES['bias_bottom']:+.2f}%"),
     "fitted_value": (f"exact slice means: nodes' mean {NODES['exact_mean']:.4f} = the fan's own mean (measured mean/median 1.0907; slice midpoints {NODES['midpoint_mean']:.4f}); "
                      f"exact to {NODES['exact_vs_brute_interior']:.1e} against 200,000 midpoints per slice (the page's A-S normal CDF sets that floor)"),
     "se": "n/a (numerical)",
     "n": "48 slices; 15 measured fan quantiles",
     "method": ("ln R is linear in z = probit(p) between the knots and continues at the end slopes beyond them (fanRatio), so on each piece ln R = c + B z and "
                "E[R; a<z<b] = exp(c + B^2/2) (Phi(b-B) - Phi(a-B)); a slice's mean is 48 x the sum over the pieces inside its probit bounds (open at the two ends). "
                "With FAN_S: c -> FAN_S c, B -> FAN_S B"),
     "validation": (f"effect on the model (shipped / fixed - 1; 16 industries x 3 sizes x ask 0.8-1.4 V): E[P|close] {100 * BUG[:, 0].min():+.2f}% to {100 * BUG[:, 0].max():+.2f}%, "
                    f"q(.08) {100 * BUG[:, 1].min():+.2f}% to {100 * BUG[:, 1].max():+.2f}%, uncapped median {100 * BUG[:, 2].min():+.2f}% to {100 * BUG[:, 2].max():+.2f}%. At the typical premium "
                    f"(prof $400k) E[P|close]/first ask with the whole spread {DER['shipped']['E_P_over_ask']:.4f} -> {DER['current']['E_P_over_ask']:.4f}, q(.08)/ask "
                    f"{DER['shipped']['bear_lo']:.3f} -> {DER['current']['bear_lo']:.3f}; bestRatio(EX, 0) {R0_SHIP:.3f} -> {R0_CUR:.3f}x, bestRatio(EX, .75) {R75_SHIP:.2f} -> {R75_CUR:.2f}x. "
                    f"Tests on the fix alone: model.test.js {tr_.get('model.test.js on the fanNodes fix alone', 'n/a')}; fuzz.test.js {tr_.get('fuzz.test.js on the fanNodes fix alone', 'n/a')}; "
                    f"browser.inputs.js {tr_.get('browser.inputs.js on the fanNodes fix alone', 'n/a')}"),
     "recommended_value": (f"ship it with or without FAN_S ({OUT}/fanNodes_fix.diff; the patched page carries it with FAN_S). FAN_S above is calibrated on the fixed nodes. The other "
                           "pending fits were run on the shipped nodes; anything they read from E[P|close] or the price quantiles moves by the amounts above")},
    {"param": "d: mean ln(first ask / ask at sale) among sold deals (puts the market targets on the model's first-ask basis). Not a model constant",
     "current_value": "not modelled (revision 1 implicitly 0)",
     "fitted_value": (f"Main Street {D_MS:.4f} = -(net asking-price drift {DRIFT['net, |chg|<=0.5']:+.4f} per listing-year, DealLedger) x {T_LIST:.3f} years (IBBA mean listing->LOI, <$1M bands); "
                      f"cuts only {D_MS_CUTS:.4f}; trims 0.35/0.7: {-DRIFT['net, |chg|<=0.35'] * T_LIST:.4f}/{-DRIFT['net, |chg|<=0.7'] * T_LIST:.4f}; jumps excluded rather than zeroed "
                      f"{D_EXCL:.4f}; every recorded jump taken as real {D_UNTRIM:+.4f}. ERROR RULE: of {DL_RULE['n_changed']:,} listings whose ask changed, {DL_RULE['n_big']:,} "
                      f"({DL_RULE['share_big']:.0%}) moved by more than 0.5 in logs (10%/90% {DL_RULE['q10_q90_big'][0]:+.2f}/{DL_RULE['q10_q90_big'][1]:+.2f}, median factor "
                      f"{math.exp(DL_RULE['median_abs_big']):.1f}; {DL_RULE['title_changed_big']:.0%} with a changed title vs {DL_RULE['title_changed_small']:.0%} for smaller changes; "
                      f"{DL_RULE['factor10_big']:.0%} a factor of ten; keys include broker index pages) and are set to no change; the SIGN of the drift depends on that rule "
                      f"(untrimmed {DL_RULE['drift_untrimmed']:+.4f}/yr). EF analog {E_ALL1['d']:.4f} (cut {E_ALL1['cut_share']:.0%}, raised {E_ALL1['raise_share']:.0%}; not re-based "
                      f"{EFS['not re-based']['d']:+.4f}, re-based {EFS['re-based']['d']:+.4f}: EF re-prices as monthly profit arrives)"),
     "se": (f"sd {SD_D:.4f} used (broker-cluster bootstrap SE of the drift {SE_DRIFT:.4f} x time, +-20% on the time, half the gap to the cuts-only figure). It does NOT include "
            f"the error rule; the rule's effect is shown as a sensitivity (FAN_S {gU.post_mean:.2f} at the untrimmed d vs {gD.post_mean:.2f}, primary structure) and is bounded by the "
            f"0.25 weight on d = 0"),
     "n": f"{len(DLP):,} DealLedger listings, {DLP.yrs.sum():,.0f} listing-years, {DLP.broker.nunique()} brokers, Feb-Oct 2026; IBBA {int(sum(r[4] for r in T_ROWS)):,} deals",
     "method": "stock-sampled listing panel: net log change between first and last sighting / exposure; times the mean months an ask stands before an LOI",
     "validation": (f"No direct check of the listing->LOI time exists here. BizBuySell's median days on market of sold businesses ({DOM.median():.0f}) is listing to CLOSE; IBBA's "
                    f"gamma-fit median listing->close for the same bands is {MED_LC_DAYS:.0f} days (like for like; the earlier comparison with the {T_LIST * 365.25:.0f}-day mean "
                    "listing->LOI compared unlike quantities and is dropped). Which ask the sources report is undocumented: BizBuySell's is the listing record's (last) price; "
                    "IBBA/Pepperdine survey wording is 'asking/benchmark price'"),
     "recommended_value": f"carried as uncertainty (weight {W_LAST} on the last-ask reading); not a constant in index.html"},
    {"param": "M_TYP (new constant, self-audit and tests only): the typical FIRST-ask premium over V among sold Main-Street deals",
     "current_value": "not in the model; the self-audit backed a 1.05-1.30x premium out of a hard-coded alpha .55 and a 94% ratio",
     "fitted_value": f"{M_TYP:.4f} = exp(ln(median ask/median sale) {T_HAT['D']:.4f} + d {D_MS:.4f} + E ln R {ELNR:.4f}) (reading G). Readings M {READ_ER['M'][0]:.4f} and R {READ_ER['R'][0]:.4f}",
     "se": f"{M_TYP * SE_LNM:.4f} (D's bootstrap SE and d's sd); the reading spread {READ_ER['M'][0]:.3f}-{READ_ER['R'][0]:.3f} is larger and is carried in FAN_S",
     "n": f"{len(SEC)} cells / {int(SEC.n_sales.sum()):,} sales; DealLedger as above",
     "method": f"V is the BIZCOMPS fan median, whose E ln R = {ELNR:.4f}, so E ln(ask/V) = E ln(ask/sale) + E ln(sale/V); ln(median ask/median sale) ~ -E ln(sale/ask) over a wide size distribution (simulated inside the fit)",
     "validation": (f"At their fitted BizBuySell s the three readings reproduce BizBuySell's ratio of medians to within {ROM_MISS_D0:.4f} in logs at d = 0 and {ROM_MISS_DMS:.4f} at the "
                    f"Main-Street d (G {ROM_FIT[('G', D_MS)]:+.4f}, R {ROM_FIT[('R', D_MS)]:+.4f}, M {ROM_FIT[('M', D_MS)]:+.4f}), against a bootstrap SE of D of {SE_T['D']:.4f}, "
                    f"so the data cannot choose among them; BizBuySell headline series 2012-2023 median ask/median sale mean {HEAD_M.mean():.3f} (sd {HEAD_M.std(ddof=1):.3f})"),
     "recommended_value": f"{M_TYP:.3f}"},
    {"param": "ALPHA_ANCHOR (anchoring elasticity)",
     "current_value": "0.55 (spec judgment)",
     "fitted_value": (f"not identified. With s refitted, E[P|close]/ask at the typical premium is {P13.Er_at_post.min():.3f}-{P13.Er_at_post.max():.3f} for every ALPHA 0.30-0.85. The "
                      f"only handle, the Jensen gap between BizBuySell's E[r] and its ratio of medians, gives z = {', '.join(f'{a:.2f}: {z:+.1f}' for a, z in P13[['alpha', 'gap_z']].values)} "
                      f"under premium reading G with d={D_MS:.3f}, but its size moves with the unidentified premium reading (gap at ALPHA .55 and BizBuySell's s: R {ROM_FIT[('R', 0.0)]:+.4f} "
                      f"at d=0, M {ROM_FIT[('M', 0.0)]:+.4f} at d=0, G {ROM_FIT[('G', D_MS)]:+.4f} at the Main-Street d) and with the lognormal ask-size approximation behind the ratio of "
                      f"medians, so it cannot pin ALPHA. EF (analog, reading G) matches its point mass {EF_ALL['pi']:.3f} at ALPHA "
                      f"{', '.join(f'{a:.2f}: {pi_:.3f}' for a, pi_ in P13[['alpha', 'ef_pi_pred']].values)}. The EF reconstruction's own fits ({P_EF_PAR}): Tobit pass-through of ln ask "
                      f"into ln sale given its hedonic value {EF_PAR['tobit'][0]:.3f} (SE {EF_PAR['tobit'][1]:.3f}), OLS {EF_PAR['ols'][0]:.3f} (SE {EF_PAR['ols'][1]:.3f}); the app's A() form "
                      f"by censored MLE alpha {EF_PAR['app_alpha'][0]:.3f} (SE {EF_PAR['app_alpha'][1]:.3f}). These mix causal anchoring with information in EF's formula asks, so they bound "
                      "ALPHA from above only"),
     "se": "n/a: flat in the realisation level; the Jensen-gap profile is specification-dependent",
     "n": "as for FAN_S",
     "method": "profile over ALPHA with s refitted (alpha_amax_profile.csv)",
     "validation": f"FAN_S refits to {'/'.join(f'{x:.2f}' for x in P13.s_pooled_post)} for ALPHA .30/.45/.55/.70/.85 (primary structure): sale-to-ask data fix (1-ALPHA)*s",
     "recommended_value": "0.55 unchanged, labelled judgment"},
    {"param": "AMAX (saturation of anchoring)",
     "current_value": "1.30",
     "fitted_value": (f"not identified; at AMAX 1.66 FAN_S refits to {p55h.s_pooled_post:.3f} vs {p55.s_pooled_post:.3f} (primary structure), and A at the 1.5x cap is {p55h.A_at_rho_max:.3f} "
                      f"vs {p55.A_at_rho_max:.3f}. The 1.66 comes from the EF reconstruction's fit of the app's A() form ({P_EF_PAR}: A_max {EF_PAR['app_amax'][0]:.3f}, SE "
                      f"{EF_PAR['app_amax'][1]:.3f}, jointly with alpha {EF_PAR['app_alpha'][0]:.3f}); with alpha above 1 it describes EF's formula asks, not Main-Street anchoring"),
     "se": "n/a", "n": "as for FAN_S", "method": "refit at AMAX 1.66",
     "validation": f"realisation level changes by under 1 point ({p55.Er_at_post:.4f} vs {p55h.Er_at_post:.4f})",
     "recommended_value": "1.30 unchanged (judgment, bounded 1.2-1.7)"},
    {"param": "Derived: E[P|close]/ask, share closing at the ask, below-ask mean and downside quantiles at the typical first-ask premium (every size below ~$9M of value)",
     "current_value": (f"whole spread, fixed fanNodes: E/first ask {DER['current']['E_P_over_ask']:.3f} ({DER['current']['E_P_over_ask'] * ED:.3f} on the ask at sale); at the ask {DER['current']['share_at_ask']:.4f} "
                       f"({int(round(DER['current']['share_at_ask'] * 48))}/48 slices); below-ask mean {DER['current']['below_ask_mean']:.3f}; q05/q08 {DER['current']['q05']:.3f}/{DER['current']['bear_lo']:.3f}. "
                       f"Shipped page (fanNodes bug): E/first ask {DER['shipped']['E_P_over_ask']:.3f}; at the ask {DER['shipped']['share_at_ask']:.4f}; below-ask mean {DER['shipped']['below_ask_mean']:.3f}; "
                       f"q05/q08 {DER['shipped']['q05']:.3f}/{DER['shipped']['bear_lo']:.3f}"),
     "fitted_value": (f"E/first ask {DER['patched']['E_P_over_ask']:.3f} ({DER['patched']['E_P_over_ask'] * ED:.3f} on the ask at sale); at the ask {DER['patched']['share_at_ask']:.4f} "
                      f"({int(round(DER['patched']['share_at_ask'] * 48))}/48); below-ask mean {DER['patched']['below_ask_mean']:.3f}; q05/q08 {DER['patched']['q05']:.3f}/{DER['patched']['bear_lo']:.3f}"),
     "se": (f"E[P|close]/ask {abs(at_s(MO['Er'], min(FAN_S_REC + POST['sd'], 1.6)) - at_s(MO['Er'], FAN_S_REC - POST['sd'])) / 2:.3f} per posterior sd of s; across premium readings "
            f"{min(v[1] for v in READ_ER.values()):.3f}-{max(v[1] for v in READ_ER.values()):.3f} on the ask at sale"),
     "n": "as for FAN_S",
     "method": f"the patched model through the harness at ask = {M_TYP:.3f} V (prof median, $400k of earnings; identical at every size below ~$9M of value)",
     "validation": (f"framework example (ask 0.79x value): E[P|close]/ask {ba(EXC, 'current', 'E_P_over_ask'):.3f} -> {ba(EXC, 'patched', 'E_P_over_ask'):.3f}, share at the ask "
                    f"{ba(EXC, 'current', 'share_at_ask'):.3f} -> {ba(EXC, 'patched', 'share_at_ask'):.3f}, bear band ${ba(EXC, 'current', 'bear_lo_usd') / 1e6:.2f}M-${ba(EXC, 'current', 'bear_hi_usd') / 1e6:.2f}M -> "
                    f"${ba(EXC, 'patched', 'bear_lo_usd') / 1e6:.2f}M-${ba(EXC, 'patched', 'bear_hi_usd') / 1e6:.2f}M, expected proceeds ${ba(EXC, 'current', 'EVp') / 1e6:.3f}M -> ${ba(EXC, 'patched', 'EVp') / 1e6:.3f}M. "
                    f"Prof $400k median at the typical premium: bear [{DER['current']['bear_lo']:.2f}, {DER['current']['bear_hi']:.2f}] -> [{DER['patched']['bear_lo']:.2f}, {DER['patched']['bear_hi']:.2f}] x ask. "
                    f"EF analog q08 of sale/last ask {EF_ALL['q08']:.2f} (model at EF's reading-G premium {AT_FAN_EF_G['q08']:.2f} at FAN_S, {AT_1_EF_G['q08']:.2f} with the whole spread). "
                    f"The live 'Realized price at the observed market ask' (a median) reads ${ba('live self-audit: BizBuySell median profile at ask $350k/0.94', 'current', 'median_P') / 1e3:.1f}k before and "
                    f"${ba('live self-audit: BizBuySell median profile at ask $350k/0.94', 'patched', 'median_P') / 1e3:.1f}k after"),
     "recommended_value": "follows from FAN_S; disclosed in the Data tab"},
    {"param": "Optimiser consequence: bestRatio(EX, theta=.75, lamT=900), the default patient-seller recommendation",
     "current_value": (f"{R75_CUR:.2f}x on the fixed page with the whole spread (shipped page {R75_SHIP:.2f}x) ({'the cap' if R75_CUR >= 1.45 else 'interior'}; U/V {uP.loc['current (s=1)', 'corner_U_over_V']:.4f} cap vs interior {uP.loc['current (s=1)', 'interior_U_over_V']:.4f} at "
                       f"{uP.loc['current (s=1)', 'interior_rho']:.2f}x: the two peaks already differ by only {100 * abs(uP.loc['current (s=1)', 'corner_U_over_V'] - uP.loc['current (s=1)', 'interior_U_over_V']):.2f}% of value)"),
     "fitted_value": (f"{R75:.2f}x at FAN_S={FAN_S_REC:.2f}: the {WIN_TXT} wins by {100 * abs(MARGIN_FAN):.2f}% of value (U/V {OM0.loc[FAN_S_REC, 'interior_U_over_V']:.4f} interior vs "
                      f"{OM0.loc[FAN_S_REC, 'corner_U_over_V']:.4f} cap). Margin interior - cap by s: " + ", ".join(f"{k:g}: {100 * v:+.2f}%" for k, v in MARGIN.items()) +
                      f". The flip is between s {FLIP_TXT} on this page (fine grid, step 0.005); on each pending page alone (coarse grid): {ALONE_FLIP_TXT}; on the pending stack "
                      f"{STK_FLIP_TXT} ({STACK_TXT}). At FAN_S={FAN_S_REC:.2f} the cap returns from theta {JUMP_FAN}; whole spread from theta "
                      f"{JUMP.get('current (s=1)')}; selection from {JUMP.get('selection, full fan')}. Under the selection reading the cap stays (U/V "
                      f"{uP.loc['selection, full fan', 'corner_U_over_V']:.4f} vs {uP.loc['selection, full fan', 'interior_U_over_V']:.4f}). theta=0 unchanged at "
                      f"{ba('optimal ask, framework example, theta=0', 'patched', 'rho'):.3f}x"),
     "se": (f"P(s >= {S_FLIP_HI:.3f}) = {P_ABOVE_FLIP:.2f} under the model average; P(s >= 0.95) = {P_GE95:.2f}; across the specification range {SPEC_LO:.2f}-{SPEC_HI:.2f} the "
            f"two peaks differ by at most {100 * MAX_ABS_MARGIN_RANGE:.2f}% of value: a coin-flip"),
     "n": "framework example, prof $160k and mfg $1.5M medians; this page, the pending stack and 5 pending-fit pages alone",
     "method": f"bestRatio on a coarse grid of s on every page and a fine grid ({S_FINE[0]:.2f}-{S_FINE[-1]:.2f}, step 0.005) on this page and the stack; a theta sweep 0-1 in steps of 0.01; the utility at the best interior ask vs the 1.5x cap on a 0.005 grid",
     "validation": (f"The {INT_TXT} end follows from choosing narrowing and applying it to an ask the console sets as a multiple of V, which carries no information; under the information "
                    "reading such an ask faces the whole fan, and the whole fan or selection keep the cap. The whole fan, however, misses realisation at typical asks, so neither end is a "
                    f"data result. UI: the patched page shows the range on the default inputs (rendered note: '{UIP.get('optimiser', {}).get('note', '')[-260:]}')"),
     "recommended_value": (f"Needs explicit sign-off as a product choice before FAN_S merges: the default patient-seller answer moves {R75_CUR:.2f}x -> {R75:.2f}x by "
                           f"{100 * abs(MARGIN_FAN):.2f}% of value, and the page now shows it as a range ({min(R75, R75_CUR):.2f}-{max(R75, R75_CUR):.2f}x) whenever the other peak is within "
                           f"1% of value. The test no longer pins the winner; it checks that the answer is one of the two peaks and that they lie within 1% of value. {OPTION_B}")},
    {"param": "Ask ceiling headroom (askCeil = max(1, IBBA band realised/ask)) and the IBBA comparison for $2M+",
     "current_value": f"headroom up to {HEADROOM:.1f}% above the ask from about $9M of value; IBBA's $2M+ ratios shown as 'share of the ask'",
     "fitted_value": (f"not refitted. Binned by sale price the model at FAN_S gives {HV['IBBA 2M-5M mean, 27 quarters']['model_fitted']:.3f} and {HV['IBBA 5M-50M mean, 27 quarters']['model_fitted']:.3f} in IBBA's $2-5M and $5M+ bands vs "
                      f"{float(IBW['2M-5M'].mean()):.3f} and {float(IBW['5M-50M'].mean()):.3f}; IBBA says those deals usually go to market without an ask (a pre-market advisor benchmark)"),
     "se": f"IBBA band SE {float(IBW['2M-5M'].std(ddof=1) / math.sqrt(len(IBW))):.3f} / {float(IBW['5M-50M'].std(ddof=1) / math.sqrt(len(IBW))):.3f} (iid quarters)",
     "n": f"{len(IBW)} quarters", "method": "comparison only", "validation": "n/a",
     "recommended_value": "formula unchanged; the $2M+ market row relabelled as a benchmark ratio; the headroom's source is listed as a known inconsistency (caption and AUDIT note)"},
]
NOT_ID = [
    (f"The MECHANISM behind the realised level, and so whether s < 1 at all. Narrowing (information in the ask) and selection on closing (whole fan, low-W scenarios rarely close) "
     f"both reproduce the sale-to-ask level at the typical premium; P(s<1) = {P_LT1_RANGE[0]:.2f}-{P_LT1_RANGE[1]:.2f} holds only under narrowing (selection needs s of {SEL_TXT}). "
     f"They part by {100 * SEP_HI[0]:.1f}-{100 * SEP_HI[1]:.1f} points of E[P|close]/ask at 1.4-1.5x and in the downside quantiles, which decides the patient seller's optimum. Deal-level asks and outcomes for listings that did NOT sell would separate them."),
    (f"The SIZE of FAN_S under narrowing: {SPEC_LO:.2f}-{SPEC_HI:.2f} are equally defensible across source structures and reading weights (posterior mean {POST['mean']:.3f}, {CUT_DIST:.3f} from "
     f"the rounding cut); the primary structure's small-sample 95% interval is {pdl['ci95_hksj'][0]:.2f}-{pdl['ci95_hksj'][1]:.2f}."),
    (f"Whether the spread of asks across listings is information or pricing noise. The calibration assumes the former; noise of sd 0.2/0.3/0.4 would give s "
     f"{S_AT_SD(0.2):.2f}/{S_AT_SD(0.3):.2f}/{S_AT_SD(0.4):.2f} (from sd {CENS_SD} one source cannot be matched at any s, a weak argument against noise that large). Only the "
     f"EF analog speaks to it directly (noise sd ~{NOISE_SD:.2f} from its pass-through)."),
    "Which ask the market sources report. BizBuySell's closed-deal 'asking price' is the listing record's price at sale (most likely the last ask); IBBA and Pepperdine say 'asking/benchmark price'. Carried as a 0.75/0.25 mixture of last-ask and first-ask readings.",
    (f"The typical premium over V. The data fix the ratio of medians (D = {T_HAT['D']:.3f}) but not ask/V: readings G {READ_ER['G'][0]:.3f}, M {READ_ER['M'][0]:.3f}, R {READ_ER['R'][0]:.3f} all "
     "reproduce D at their fitted s within its sampling error. Needs the value model run on the listings that later sold (BIZCOMPS has both prices)."),
    (f"ALPHA_ANCHOR: sale-to-ask aggregates identify (1-ALPHA)*s, not ALPHA; the realisation level is ALPHA-invariant once s is refitted, and the Jensen-gap handle changes size with the "
     f"premium reading. EF's pass-through ({EF_PAR['tobit'][0]:.2f}, the reconstruction's Tobit fit) mixes causal anchoring with information in the ask, so it bounds ALPHA from above only. "
     "Needs asks that vary for reasons unrelated to the business. Keep 0.55 as labelled judgment."),
    (f"AMAX: matters only near the 1.5x cap (A(1.5) = {p55.A_at_rho_max:.3f} at 1.30 vs {p55h.A_at_rho_max:.3f} at 1.66). The EF app-form estimate of {EF_PAR['app_amax'][0]:.2f} comes with alpha "
     f"{EF_PAR['app_alpha'][0]:.2f} and does not transfer. Keep 1.30, bounded 1.2-1.7."),
    (f"A size gradient in realisation: IBBA steps from {T_HAT['ib1']:.3f} to {T_HAT['ib2']:.3f} between its two smallest bands; BizBuySell's $1M+ series sits {100 * (Y_GE1M - T_HAT['bbs']):.0f} points above its all-deal mean. "
     f"Cell-level gradient per doubling of the median sale price: sector partition {GRAD['sector'][0]:+.4f} (SE {GRAD['sector'][1]:.4f}, p {GRAD['sector'][2]:.2f}), market partition "
     f"{GRAD['market'][0]:+.4f} (SE {GRAD['market'][1]:.4f}, p {GRAD['market'][2]:.3f}). Direction up with size, magnitude not identified; FAN_S is one number, and treating IBBA's two bands "
     "as one source or two is the structural question this raises (carried in the model average)."),
    f"The IBBA under-$500K level: it fails leave-one-source-out (z {LOSO['ib1']['z_train_tau']:+.1f} with the training tau). Carried as between-source sd, not resolved.",
    "The Main-Street point mass at the ask: no national figure exists (Muradian's 67% is one broker who screens out overpriced listings). The model's value is implied by FAN_S and the premium.",
    (f"Time drift: EF's point mass fell from {PERIOD14['observed']:.2f} (2014-18) to {PERIOD22['observed']:.2f} (2022-26), BizBuySell's mean rose to {BBS25:.2f} in 2025, and the naive per-band mean beats the model on 2022-26 quarters. "
     f"Calibrated to 2022+ alone, s would be {RUN22['post']['mean']:.2f}; the recommendation is a 2016-2026 average."),
]
IMPL = (
    f"index.html, model half. (1) After `const ALPHA_ANCHOR=.55;` add the FAN_S provenance comment (labelled CALIBRATED) and `const FAN_S={FAN_S_REC:.2f};`, then the M_TYP comment and "
    f"`const M_TYP={M_TYP:.3f};` (M_TYP is read only by renderCalib and the tests). (2) fanNodes() BUG FIX, separable and wanted with or without FAN_S: the 4,000-point grid "
    "read in slices of k = M/N = 83.33 points summed 84 per slice (j < k), overlapped the next and divided by 83.33 (every node "
    f"{100 * NODES['interior_bias_min']:+.1f}% to {100 * NODES['interior_bias_max']:+.1f}%, the top one {100 * NODES['bias_top']:+.1f}%; nodes' mean {NODES['shipped_mean']:.4f} vs the fan's {NODES['exact_mean']:.4f}). "
    "Replace the body by exact slice means: ln R = c + B z on each piece between knots (and beyond them, as in fanRatio), so a slice's mean is "
    "48 * sum over pieces of exp(c+B^2/2) (ncdf(b-B) - ncdf(a-B)) with the slice's probit bounds (open at the ends); "
    f"exact to {NODES['exact_vs_brute_interior']:.0e} against brute force (the A-S normal CDF's error). The fix alone is {OUT}/fanNodes_fix.diff ({OUT}/fixonly/index.html). "
    "With FAN_S, the pieces use c=FAN_S*g.c, B=FAN_S*g.B (slice means of R(p)^FAN_S, median kept), and the comment above fanNodes says so. (3) `out.ALPHA=ALPHA_ANCHOR;` -> `out.ALPHA=ALPHA_ANCHOR; out.fanS=FAN_S; out.mTyp=M_TYP;`. (4) §23 comment: "
    "the fan slice is 'kept at FAN_S of its log spread (calibrated to sale-to-ask averages; information in the ask and selection on closing explain them alike)'. (5) bestRatio's comment: replace "
    "'~1.05x when a failed sale is a total loss, ~1.4x when the owner is content to keep it' with the two-peak statement (computed margin, flip location in s and theta, extrapolation, range in "
    "the render). P_C, fitClose, the gap penalty, the ceiling, RHO_MAX, ALPHA and AMAX are untouched; price stays independent of closing, so EVp = P_C x E[P|close]. UI: (6) the 'Price if it "
    "closes' tooltip adds 'narrowed to the share that remains once a business is listed (calibrated)'. (7) eq_a: `W=E[V|X]*R(p)` -> `R(p)^{s}, s=${FAN_S.toFixed(2)}`. (8) eq_s: `W=E[V|X]*R` -> "
    "`R^{s}` with R the measured value spread and s the share kept once listed; eq_ss shows R(0.10)^s and R(0.90)^s (the quantiles that actually drive P_0.08/P_0.94); the panel label reads "
    "'Scenario quantiles from the measured out-of-fold value spread, narrowed once listed (FAN_S, calibrated)'. (9) Realisation block: the first row reads 'Market benchmark: sale price as a "
    "share of the advisor's benchmark (IBBA; deals this size usually list without an ask)' when Vbase >= $2M, and the caption from 'The typical ratio is a market average...' is replaced "
    "(first-ask vs ask-at-sale levels, the market averages, the shortfall with the whole spread, calibrated share with its equally defensible range, information-or-selection, calibrated near "
    "1.07x and extrapolated above 1.4x, IBBA binning, $2M+ benchmark, larger deals realise more, ceiling headroom as a known inconsistency). (10) Data tab, Model II panel: 'Residual spread "
    "driving the scenario bands' becomes 'Value uncertainty: residual spread of the value model' (badge fitted), a new row 'Realised-price fan at a typical ask' shows FAN_S x sigma with "
    "the badge 'calibrated' (class st adj, number not green), and the note gives the narrowed 80% band. (11) Data tab, 'Fitted from public data': new FAN_S row badged 'calibrated' (robust "
    "finding first, per-source values, model average, conditionality on mechanism and on informative premiums, extrapolation, 2022+ value, LOSO failure, naive baseline, downside effect). "
    "(12) 'Still judgement': the anchoring row rewritten for ALPHA/AMAX as not identified, citing EF's pass-through from the reconstruction's own fit. (13) renderCalib(): delete the lo/hi/mid "
    "bisection (it hard-coded .55); the row becomes 'Fit-consistency check, not an external benchmark: expected price if it closes, as a share of the first ask, at the typical premium "
    "(M_TYP x value)', band 87.5-92.5%. (14) Optimiser card: after `const uGain=...atEdge=...;` compute the other peak (the RHO_MAX cap when the answer is interior; the best ask in 1.00-1.35x "
    "on a 0.025 grid when it is at the cap) with the same utility including lamT*tMed, and when it is within 1% of value append 'Asking Xx value instead is worth within Y% of value to this "
    "owner, close to a tie, so read the patient-seller price as a range, a-bx value: which end wins turns on how widely prices scatter at high asks, which the data do not settle.' "
    "The pending overpricing_time fit moves this note into optNote(s,V,rSell,rKeep); the same logic, rebased there, is in the script (PATCH_STACK_ALT) and is applied and rendered in "
    "pending_stack_with_fan. "
    f"All {len(PATCH)} replacements are applied verbatim in {PDIR}/index.html (diff {OUT}/index.html.diff). (15) Add tests/anchoring_realization.test.js "
    f"({OUT}/anchoring_realization.test.js). (16) fit/README.md: new table row and the 'Tried and not usable' anchoring line updated ({PDIR}/fit/README.md). (17) AUDIT.md: new section "
    f"'Realised-price fan (FAN_S), October 2026' and the stale 'about 1.57x' bullet marked superseded ({PDIR}/AUDIT.md). GATE: merge only after explicit sign-off that the default "
    f"patient-seller answer is a coin-flip shown as a range and that its winning end moves from {R75_CUR:.2f}x to {R75:.2f}x for a mechanism reason, not a data one; if the cap is "
    "preferred, ship FAN_S with Option B (bestRatio on the whole fan; see the optimiser row) rather than dropping it. Re-run bestRatio and the new test after the other pending fits merge "
    f"(the overpricing_time stack moves the flip to s {STK_FLIP_TXT}).")
DATA_TAB = (
    f"Fitted-table row 'Realised-price fan: share of the value spread kept once a business is listed (FAN_S)' with the badge 'calibrated': was 1.00; now {FAN_S_REC:.2f} of it in logs (with "
    f"alpha = 0.55), calibrated to market sale-to-ask averages; the mechanism is not identified and {SPEC_LO:.2f}-{SPEC_HI:.2f} are equally defensible. Data: what the data show robustly: "
    f"at the typical first ask ({M_TYP:.2f}x value) the whole spread gave {100 * RB['bbs']['current']:.1f}% of the ask if it closes, short of BizBuySell's {100 * RB['bbs']['target']:.1f}% "
    f"(deal-level mean, 2016-18, {int(SEC.n_sales.sum()):,} sales, on the same first-ask basis) and of IBBA's under-$1M deals ({len(IBW)} quarters, binned by sale price: "
    f"{100 * RB['ibc']['target']:.1f}% against the model's {100 * RB['ibc']['current']:.1f}%). Information in the ask (a narrower fan, implemented) or selection on which deals close raise "
    f"it alike. Per source s: BizBuySell {EST['bbs']:.2f}, IBBA under $500K {EST['ib1']:.2f} and $500K-1M {EST['ib2']:.2f} (or {EST['ibc']:.2f} as one source), DealStats {EST['ds']:.2f}; "
    f"averaged over source structure, which ask the sources report (the ask at sale, {100 * D_MS:.1f}% below the first ask: DealLedger, {len(DLP):,} listings) and how the typical premium is "
    f"read, {POST['mean']:.2f} (sd {POST['sd']:.2f}). Conditional: selection needs s >= 1, and pricing noise in the asks would put s at {S_AT_SD(0.2):.2f}-{S_AT_SD(0.3):.2f}. Calibrated near "
    f"1.07x value; at 1.4-1.5x, where the patient-seller recommendation is decided, it is an extrapolation. Calibrated to 2022+ alone it would be lower ({RUN22['post']['mean']:.2f}). Out of "
    f"sample IBBA's under-$500K level is missed by {100 * (LOSO['ib1']['pred_dl'] - LOSO['ib1']['obs']):.0f} points and per-band averages beat the model on 2022-26 quarters "
    f"({100 * TEMP_Q['naive per band']:.1f} vs {100 * TEMP_Q['fitted']:.1f} points; whole spread {100 * TEMP_Q['current']:.1f}). Effect: the bear scenario's low end at the typical premium "
    f"rises from {AT1_Q[.08]:.2f} to {AT_Q[.08]:.2f} of the ask. Model II panel: 'Value uncertainty' (the whole spread, badge fitted) and 'Realised-price fan at a typical ask' (FAN_S x sigma, "
    "badge calibrated), with the note giving the narrowed 80% band. Judgement row 'Anchoring strength (alpha = 0.55) and its ceiling (A_max = 1.30)': not identified; sale-to-ask data fix "
    f"(1-alpha)*s; with s refitted every alpha 0.30-0.85 gives the same level; A_max moves the price at the 1.5x cap by under 3%; EF's pass-through of {EF_PAR['tobit'][0]:.2f} "
    f"(SE {EF_PAR['tobit'][1]:.2f}) is only an upper bound. Realisation block: under $2M 'sale price as a share of the ask'; from $2M 'Market benchmark: sale price as a share of the advisor's "
    "benchmark (IBBA; deals this size usually list without an ask)'. Self-audit: 'Fit-consistency check, not an external benchmark' (87.5-92.5%). Optimiser card: when the other utility "
    "peak is within 1% of value the note gives the patient-seller price as a range.")
INVARIANTS = [
    f"model().fanS === FAN_S === {FAN_S_REC:.2f} and 0 < FAN_S <= 1; model().mTyp === M_TYP === {M_TYP:.3f}.",
    "At ask = M_TYP x V, E[P|close]/ask lies in [0.875, 0.925] for every industry at median profiles with $120k and $400k of earnings (the Main-Street sizes the targets cover), and is >= 0.875 at $1.5M (data say larger deals realise more; only a floor).",
    "At ask = M_TYP x V the share closing at the ask (capShare) is in [0.30, 0.55], and the below-ask mean (Vmean - capShare*ceil)/(ask*(1-capShare)) is in the calibrated band (" + f"{BL_LO:.2f}-{BL_HI:.2f}).",
    f"Downside disclosure: at ask = M_TYP x V, the bear scenario's low end q(.08)/ask is in [{Q8_LO:.2f}, {Q8_HI:.2f}] (was {DER['current']['bear_lo']:.2f}; EF analog q08 of sale/last ask {EF_ALL['q08']:.2f}).",
    "Narrowing keeps the centre: VrealFree / (V * anchorF * (1+compPrem)) is within 1% of 1.",
    "P_C does not read the realised-price block: P_C equals fitClose(ask, V, chan, Vbase).p x min(1, thinF), and EVp = P_C x Vmean to 1e-9.",
    "E[P|close] is non-decreasing in the ask for ask/V from 0.4 to 3, and E[P|close]/ask is non-increasing (framework example and two median profiles).",
    ("Optimiser: bestRatio(EX, 0, 900) in [1.08, 1.13]. At theta=.75 the WINNER is not pinned (a knife-edge in s and theta): bestRatio(EX, .75, 900) must be one of the two peaks "
     "(in [1.08, 1.25] or >= 1.45), and the best interior utility (ask < 1.35x) and the best cap-region utility, EVp + (1-P_C)*.75*V - 900*tMed on a 0.005 grid, must lie within 1% of V."),
    "Every existing invariant still holds (model.test.js, fuzz.test.js, browser.sweep.js, browser.inputs.js): Vmean <= ceiling, q(.99) <= ask*max(1, pctAskSize), proceeds peak below RHO_MAX, 8b's (0.80, 1.03] at ask = value.",
    "The live self-audit row 'Fit-consistency check ... at the typical premium' reads 'in range' (87.5-92.5%); it is labelled as the fit's own target, not an external benchmark.",
    "Rendered page (default inputs = framework example, theta .75): the optimiser note contains the range sentence; eq_s shows R^{s}; no KaTeX errors, no unrendered ${...}, no NaN/undefined.",
    f"The new test FAILS on the pre-change model ({tr_['new test against the CURRENT model (should fail)']}), so a revert is caught.",
    "Documented property, not tested: below ~$9M of value the realisation block is scale-free (P/ask depends only on ask/V); a future size effect would intentionally break it.",
]
CAVEATS = (
    f"WHAT CHANGED IN REVISION 4. fanNodes() fixed: the shipped nodes summed 84 grid points per slice over 83.33 and overlapped, running "
    f"{100 * NODES['interior_bias_min']:.1f}-{100 * NODES['interior_bias_max']:.1f}% high (top {100 * NODES['bias_top']:.1f}%); they are now exact slice means. The grid, the optimiser pages, the "
    f"'current' baseline (fixonly/: the fix alone, whole spread) and the patched page all use the exact nodes; the shipped page is reported beside them. Recalibrated on the exact nodes "
    f"FAN_S's posterior mean is {POST['mean']:.3f} (sd {POST['sd']:.3f}) against revision 3's 0.832 (sd 0.202), recommendation {FAN_S_REC:.2f} (was 0.85); the patient-seller flip sits "
    f"at s {FLIP_TXT} (was 0.855-0.860). "
    f"WHAT CHANGED FROM REVISION 2 (revision 3). (1) FAN_S is presented as a CALIBRATION, not a fit: the robust finding is that the whole spread realises {RB['bbs']['current']:.3f} of the first ask at the "
    f"typical premium against {RB['bbs']['target']:.3f} at BizBuySell, and both narrowing and selection raise it; P(s<1) is reported as conditional on narrowing; the Data tab drops 'the data "
    f"say s < 1' and uses a 'calibrated' badge (st adj), including in the Model II panel. (2) The source structure is carried in the model average: IBBA's sub-$1M bands as two sources or one, "
    f"DealStats out or in (equal weights). That moves the posterior mean from {POST_PRIMARY_STRUCT['mean']:.3f} (revision 2's structure) to {POST['mean']:.3f} and the recommendation to "
    f"{FAN_S_REC:.2f}, {CUT_DIST:.3f} from the rounding cut; {SPEC_LO:.2f}-{SPEC_HI:.2f} are equally defensible and that is how it is labelled. (3) Premium dispersion run to sd 0.4 and the "
    f"interval stated as conditional on informative premiums ({NOISE_TXT}). (4) The optimiser flip located on a fine grid: s {FLIP_TXT} (not 0.875) and theta {JUMP_FAN} at FAN_S; the margin "
    f"at FAN_S is {100 * abs(MARGIN_FAN):.2f}% of value; the patient-seller answer is shown as a range in the UI when the other peak is within 1% of value, and the test checks the near-tie "
    "instead of pinning 1.15x. (5) eq_s, eq_ss and the scenario label now show R^s. (6) EF refit under reading G; BizBuySell leave-one-out rerun with an other-period D; DealStats left out "
    "and predicted; the days-on-market cross-check replaced by a like-for-like one; the DealLedger error rule documented with its sign flip; EF pass-through and app-form values read from "
    "and cited to the reconstruction's fit_parameters.csv; the share at the ask now read from the model (" + f"{int(round(DER['current']['share_at_ask'] * 48))}/48 before, {int(round(DER['patched']['share_at_ask'] * 48))}/48 after" + "), not interpolated. "
    "DISAGREEMENT, PARTLY. Review 2 argues the coherent counterfactual for optimiser-set asks is the whole fan or selection, both of which keep the cap. Agreed as far as it goes, and stated "
    f"in the sign-off note; but the whole fan also misses realisation at typical asks by {100 * (RB['bbs']['target'] - RB['bbs']['current']):.1f} points, and selection needs a P_C rebuilt from "
    "the same weights that the model does not have, so neither end of the patient-seller range is a data result. Hence the range in the UI and Option B rather than a reversal. "
    "TRANSFERABILITY. BizBuySell, IBBA, Pepperdine and DealStats are the target market but aggregate; no deal-level Main-Street ask/sale pairs were available. DealLedger is Main-Street broker "
    "listings (2026, stock-sampled, noisy prices). DealStats' moment is a ratio of medians, which identifies s only through the assumed lognormal size spread (sd 1.1), and its s swings "
    f"with the premium reading (G {DS_BY_READ['G']:.2f}, M {DS_BY_READ['M']:.2f}, R {DS_BY_READ['R']:.2f}); that is why it enters as a structural alternative, not by default. Empire Flippers is online "
    "businesses whose asks are set by EF and re-based on trailing profit; it transfers the shape (a point mass at the ask, a below-ask mean near 0.8, a point mass falling with the premium) "
    "and the direction of the first-vs-last effect, not the level, the size of d, the premium dispersion or ALPHA; it was not pooled. Flippa auctions and TRANBI (no prices) do not transfer and "
    "were not used. "
    "VALIDATION, HONESTLY. IBBA under $500K fails leave-one-source-out (z " + f"{LOSO['ib1']['z_train_tau']:+.1f}" + "); naive per-band means beat the model on the 2022-26 holdout; "
    "Pepperdine read literally as band medians is not matched by either model; at BizBuySell's premium the calibrated model misses DealStats' ratio of medians by more than the whole spread "
    "does (at DealStats' own premium the three sale/ask sources predict it within z " + f"{LOSO['ds']['z']:+.2f}" + "); the held-out levels that improve sit above both models, so they "
    "support a higher level, not narrowing in particular. "
    "DOWNSIDE. FAN_S narrows every displayed price-if-closes quantile (bear/base/bull, the 30-70 range, q()), not only the mean; the Data tab separates value uncertainty from the realised-price fan. "
    "STRUCTURE. Anchoring is uncentred (A(1) = 1 at ask = value), so under reading G a listing at the typical premium has a median closed price slightly above V; reading M is exactly the premium "
    "that removes this. KNOWN INCONSISTENCY. askCeil still takes up to " + f"{HEADROOM:.1f}" + "% headroom above the ask from IBBA's $5M+ ratio, which is to a benchmark, not an ask; left for a separate change. "
    f"PENDING STACK. Stacked automatically: {STACK_TXT}. "
    f"DATA QUALITY. BizBuySell sector names harmonised before clustering ({SEC.label1.nunique()} spellings -> {SEC.sector_h.nunique()} sectors; {N_RELABEL} misaligned 2016 construction row); "
    "the 2018 market table had its price columns swapped (" + f"{frac_bad:.0%}" + " of cells read sale > ask; a check only). IBBA values are whole percentages read off chart labels; " + f"{len(IB_MISSING)}" + " quarters are missing inside "
    "2017Q4-2026Q2 and are now respected by a non-circular calendar-block bootstrap (cross-band correlation of the quarterly series " + f"{min(IB_XCORR.values()):.2f}-{max(IB_XCORR.values()):.2f}"
    + ", so the bands are treated as independent). Medians are of rounded prices. DealLedger changes above 0.5 in logs are treated as errors (see the d row). Bootstrap SEs are sampling-only; "
    "the posterior sd is the one to quote, and it is conditional as stated.")
RESULT = {"name": "anchoring_realization", "script": "/home/user/last-minute/fit/anchoring_realization.py", "parameters": PARAMS,
          "not_identified": NOT_ID, "implementation": IMPL, "data_tab_text": DATA_TAB, "test_invariants": INVARIANTS, "caveats": CAVEATS}
with open(os.path.join(OUT, "RESULT.json"), "w") as f:
    json.dump(RESULT, f, indent=1)
log(f"\nRESULT.json written; tests on the patched copy pass and the new test fails on the current model: {tests_ok}; UI range note shown: {UI_NOTE_SHOWN}")
log(f"done in {time.time() - T0:.0f}s")
