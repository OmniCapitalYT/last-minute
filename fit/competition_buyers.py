#!/usr/bin/env python3
"""Competition and buyer effects: engaged-buyer scale, thin-pool factor, competition premium (kappa)
and buyer-type multiple factors for The Omni Method console (index.html).

Run:  python3 -I /home/user/last-minute/fit/competition_buyers.py
Needs: numpy, pandas, scipy, statsmodels; node (evaluates the console's model through
/tmp/claude-0/fit5/harness.js, which loads index.html with source-text overrides).
Inputs (read-only, absolute paths): /tmp/claude-0/data5/aggregates_research/clean/*,
/tmp/claude-0/data5/aggregates_research/raw/ibba/ibba_q4_2025.txt (2025Q4 average-offers table only),
/tmp/claude-0/data5/flippa/clean/*, /tmp/claude-0/data5/kaggle/clean/flippa_reapx_open_listings_2026-08-03.csv,
/tmp/claude-0/data5/extra_japan_platform_closed_deals/clean/*.
Outputs: /tmp/claude-0/fit5/competition_buyers/ (tables, probe JSON, RESULT.json).

What it fits
  (b) offers per closed deal by IBBA size band -> zero-truncated negative binomial (ZTNB).
      "Engaged buyer" is defined as a buyer who makes an offer, so the model's typical pool
      nEngRef = I.buyers * peRef * ENG_SHARE is fitted by maximum likelihood to IBBA's
      offer-count histograms (ENG_SHARE and the NB dispersion NB_R). The thin-pool factor
      becomes the NB chance of at least one offer relative to a typical pool.
      Sensitivities (revision 2): tail-cell and quarter specifications, an industry-mixture
      likelihood, a Poisson-lognormal mixing family, closing that depends on the number of
      offers (P(close|k) = 1-(1-q)^k, q not identified), offers that grow less than in
      proportion to buyers contacted (exponent beta, not identified), a strictly temporal
      holdout (2023 histograms only), and the score impact on the patched console.
  (a) kappa: within-band quarter-to-quarter IBBA panel of realized/ask on average offers,
      mapped through the model's own pass-through of the premium into E[price|close]/ask,
      with an errors-in-variables (regression calibration) correction and a quarter-cluster
      bootstrap; plus a band+quarter two-way FE and a Main-Street-only check. Flippa
      auctions reported as a non-transferable analog.
      Revision 3 (independent review): 2023Q4 disclosed as inconsistent with its own report's averages in all five
      bands; specifications deduplicated and extended (drop 2023Q4 + the 2025Q4 $5M+ cell; 2023Q1-Q3 only;
      rounding-consistent n weights); NB-only specification range with the Poisson-lognormal scale reported apart;
      quasi-likelihood versions of the LR statistics (quarter dependence); the sampling SE of thinF itself; the
      2025Q4 average table compared with its histogram; the IND.buyers sensitivity of the score; the cap at 1, the
      conditional offer count in compPrem and a Flippa watchers analog for beta stated.
  (c) buyer-type multiple factors: Pepperdine 2016 strategic-vs-financial premium
      distribution (interval-censored hurdle lognormal), GF Data add-on vs platform,
      Stanford 2024 search funds vs GF Data, compared with the premia the model implies.
      Revision 2: a CONSISTENCY CHECK only. str/adj mf stay at 1.18/1.14 (judgment): theta
      is within 1 SE of 1 and the two Pepperdine vintages straddle the current values.
"""
import json, os, re, subprocess, sys, math, warnings
import numpy as np, pandas as pd
from scipy import optimize, stats, special
import statsmodels.api as sm

warnings.filterwarnings("ignore")
OUT = os.environ.get("CB_OUT", "/tmp/claude-0/fit5/competition_buyers")   # CB_OUT only for scratch re-runs
AGG = "/tmp/claude-0/data5/aggregates_research/clean"
FLIPPA = "/tmp/claude-0/data5/flippa/clean"
TRANBI = "/tmp/claude-0/data5/extra_japan_platform_closed_deals/clean"
HARNESS = "/tmp/claude-0/fit5/harness.js"
RAW_Q4_2025 = "/tmp/claude-0/data5/aggregates_research/raw/ibba/ibba_q4_2025.txt"     # 2025Q4 average-offers table (text layer)
FLIPPA_OPEN = "/tmp/claude-0/data5/kaggle/clean/flippa_reapx_open_listings_2026-08-03.csv"  # weak analog: offers vs watchers
RNG3 = np.random.default_rng(20261011)          # revision 3 draws (separate stream, so revision-2 numbers reproduce)
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(20261010)
BANDS = ["<500K", "500K-1M", "1M-2M", "2M-5M", "5M-50M"]
# band centres exactly as index.html's BAND_KNOTS (geometric centres; $250k for the open bottom band)
VC = np.array([2.5e5, math.sqrt(5e5 * 1e6), math.sqrt(1e6 * 2e6), math.sqrt(2e6 * 5e6), math.sqrt(5e6 * 5e7)])
LNV = np.log(VC / 1e6)
CUR = dict(ENG_SHARE=0.34, COMP_K=0.030, COMP_H=3.0)
L_D23 = "drop 2023Q4 (line-chart read; its lowest possible means exceed its own report's averages in all 5 bands)"
L_D25 = "drop 2025Q4 (= 2023 histograms only = the strictly temporal training set)"
B_BOOT = int(os.environ.get("CB_BOOT", "400"))
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


# ----------------------------------------------------------------------------------------------
# 0. Model probe (node + harness). Evaluates the console at median businesses whose pre-quality
#    fitted value (Vbase) sits at chosen deal values, for every industry.
# ----------------------------------------------------------------------------------------------
PROBE_JS = r"""
const H=require(process.argv[2]); const cfg=JSON.parse(require('fs').readFileSync(process.argv[3],'utf8'));
const base=[["out.compPrem=clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);",
             "out.compPrem=(MODELS.__comp!=null)?MODELS.__comp:clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);"]];
const A=H.load((cfg.overrides||[]).concat(cfg.overrides&&cfg.overrides.length?[]:base));
function med(ind,ern){ const I=A.IND[ind], RF=A.sizeRefs(ern), m=A.typMargin(ind,ern);
  return {ind,rev:ern/m,ern,grw:I.grw,gm:I.gm,rec:I.rec,cc:.16,ret:I.ret,plt:.40,own:RF.own,mgt:RF.mgt,fin:RF.fin,
          yrs:6,buyers:I.buyers,st:null,franchise:false,ask:1e6}; }
function atV(ind,V){ let lo=Math.log(2e3),hi=Math.log(2e8);
  for(let i=0;i<70;i++){const m=(lo+hi)/2; const r=A.model(med(ind,Math.exp(m))); if(r.Vbase<V) lo=m; else hi=m;}
  const s=med(ind,Math.exp((lo+hi)/2)); s.ask=A.REF_RATIO*A.model(s).V; return s; }
const out={};
if(cfg.mode==="probe"){
  out.REF_RATIO=A.REF_RATIO; out.IND={}; for(const k in A.IND) out.IND[k]={buyers:A.IND[k].buyers,strat:A.IND[k].strat};
  out.rows=[];
  for(const V of cfg.V) for(const ind of Object.keys(A.IND)){
    const s=atV(ind,V); A.MODELS.__comp=null; const r=A.model(s);
    A.MODELS.__comp=-0.02; const rm=A.model(s); A.MODELS.__comp=0.02; const rp=A.model(s); A.MODELS.__comp=0; const r0=A.model(s); A.MODELS.__comp=null;
    out.rows.push({V,ind,ern:s.ern,rev:s.rev,ask:s.ask,Vbase:r.Vbase,Vm:r.V,nEngRef:r.nEngRef,nEng:r.nEng,avgPE:r.avgPE,
      peRef:r.nEngRef/(A.IND[ind].buyers*0.34),compPrem:r.compPrem,thinF:r.thinF,PC:r.PC,Vmean:r.Vmean,
      Vmean0:r0.Vmean,capShare0:r0.capShare,pass:(rp.Vmean-rm.Vmean)/0.04/s.ask,synE:r.synE,M:r.M,
      buyers:r.buyers.map(b=>({k:b.k,sizeFit:b.sizeFit,PE:b.PE,Vj:b.Vj,mf:b.mf,syn:b.syn,S:b.S}))});
  }
}
if(cfg.mode==="check"){
  /* deterministic LCG so the fuzz is reproducible */
  let seed=12345; const rnd=()=>{seed=(seed*1103515245+12345)%2147483648; return seed/2147483648;};
  const inds=Object.keys(A.IND); const res={n:0,mono_fail:0,thin_fail:0,ref_fail:0,qual_fail:0,median_fail:0,worst:[]};
  for(let i=0;i<cfg.n;i++){
    const ind=inds[Math.floor(rnd()*inds.length)], ern=Math.exp(Math.log(5e4)+rnd()*Math.log(400));
    const s=med(ind,ern); s.rev=ern/(A.typMargin(ind,ern)*Math.exp((rnd()-.5)*1.2));
    for(const k of ["rec","ret","gm","own","mgt","fin","plt"]) s[k]=Math.min(.98,Math.max(.02,s[k]+(rnd()-.5)*.6));
    s.cc=.02+rnd()*.6; s.grw=-.1+rnd()*.5; s.yrs=1+Math.floor(rnd()*12);
    const V0=A.model({...s,ask:1e6}).V; s.ask=V0*(.6+rnd()*1.3);
    let prev=-1, prevThin=-1; const refs=[];
    for(const nb of [1,2,4,8,15,30,60,120,240,480,960]){
      const r=A.model({...s,buyers:nb}); refs.push(r.nEngRef); (res.comp=res.comp||[]).push(r.compPrem);
      if(r.EVp<prev*(1-1e-9)){res.mono_fail++; res.worst.push({ind,ern,nb,EVp:r.EVp,prev});}
      if(r.thinF<prevThin-1e-12||r.thinF>1+1e-12||!(r.thinF>0)) res.thin_fail++;
      prev=r.EVp; prevThin=r.thinF; }
    if(Math.max(...refs)-Math.min(...refs)>1e-9) res.ref_fail++;
    /* typical pool must not depend on quality */
    const rq1=A.model({...s,own:.1,mgt:.9,rec:.9}), rq2=A.model({...s,own:.9,mgt:.1,rec:.1});
    if(Math.abs(rq1.nEngRef-rq2.nEngRef)>1e-9||Math.abs(rq1.thinF-rq2.thinF)>1e-9) res.qual_fail++;
    res.n++;
  }
  /* a median business marketed to its industry's typical pool earns no premium and loses no P_C */
  res.median_max_abs_comp=0; res.median_max_thin_gap=0; res.share1=[];
  for(const ind of inds) for(const V of [2.5e5,7.07e5,1.414e6,3.162e6,1.581e7]){ const s=atV(ind,V); const r=A.model(s);
    res.median_max_abs_comp=Math.max(res.median_max_abs_comp,Math.abs(r.compPrem));
    res.median_max_thin_gap=Math.max(res.median_max_thin_gap,Math.abs(1-r.thinF));
    if(Math.abs(r.compPrem)>5e-4||Math.abs(r.thinF-1)>1e-9) res.median_fail++;
    const R=cfg.nb_r||1e6, mu=r.nEngRef, p=R/(R+mu), p0=Math.pow(p,R);
    res.share1.push({ind,V,nEngRef:mu,share1:R*p0*(mu/(R+mu))/(1-p0),ztmean:mu/(1-p0)}); }
  res.worst=res.worst.slice(0,5);
  /* example business before/after */
  const ex=cfg.example; const r=A.model(ex);
  res.example={nEng:r.nEng,nEngRef:r.nEngRef,nPool:r.nPool,compPrem:r.compPrem,thinF:r.thinF,PC:r.PC,Vmean:r.Vmean,EVp:r.EVp,V:r.V,
    stratPremPct:r.stratPrem/r.V,top:r.top.k,strVjPct:r.buyers.find(b=>b.k==="str").Vj/r.V,adjVjPct:r.buyers.find(b=>b.k==="adj").Vj/r.V};
  const exThin=A.model({...ex,buyers:12}); res.example_thin12={nEng:exThin.nEng,nEngRef:exThin.nEngRef,thinF:exThin.thinF,PC:exThin.PC,EVp:exThin.EVp,compPrem:exThin.compPrem};
  const exOut=A.model({...ex,buyers:ex.buyers*2.2}); res.example_outreach={compPrem:exOut.compPrem,thinF:exOut.thinF,EVp:exOut.EVp,PC:exOut.PC};
  /* pool-ratio grid at a median business, $1.5M value */
  res.grid=[]; for(const ind of ["medical","home","rest"]){ const s=atV(ind,1.5e6);
    for(const f of [.1,.25,.5,1,2,4]){ const r2=A.model({...s,buyers:s.buyers*f});
      res.grid.push({ind,f,nPool:r2.nPool,nEngRef:r2.nEngRef,thinF:r2.thinF,compPrem:r2.compPrem,PC:r2.PC,EVp:r2.EVp}); } }
  /* revision 2: the headline Omni score (percentile against peers marketed to a typical pool) */
  res.scores=[];
  for(const ind of inds) for(const ern of [2e5,1e6,4e6]){ const s0=med(ind,ern); s0.ask=A.REF_RATIO*A.model(s0).V;
    for(const f of [.25,.5,.75,.9,1]){ const s={...s0,buyers:Math.max(1,Math.round(s0.buyers*f))}; const r=A.model(s); r.inputs=s;
      res.scores.push({ind,ern,f,buyers:s.buyers,score:A.omniScore(r),thinF:r.thinF,PC:r.PC,EVp:r.EVp}); } }
  res.ex_scores=exScores(cfg.example);
  out.check=res;
}
/* revision 3: the worked example by buyers contacted, alone (used for the IND.buyers sensitivity) */
function exScores(ex){ const o=[]; for(const b of [5,12,25,40,50,65]){ const s={...ex,buyers:b}; const r=A.model(s); r.inputs=s;
    o.push({buyers:b,score:A.omniScore(r),thinF:r.thinF,PC:r.PC,EVp:r.EVp,nEng:r.nEng,nEngRef:r.nEngRef,nPool:r.nPool,compPrem:r.compPrem}); } return o; }
if(cfg.mode==="exscores"){ out.ex_scores=exScores(cfg.example); }
process.stdout.write(JSON.stringify(out));
"""


def run_probe(cfg):
    jpath = os.path.join(OUT, "probe.js")
    with open(jpath, "w") as f:
        f.write(PROBE_JS)
    cpath = os.path.join(OUT, "probe_cfg_%s.json" % cfg["mode"])
    with open(cpath, "w") as f:
        json.dump(cfg, f)
    r = subprocess.run(["node", jpath, HARNESS, cpath], capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    return json.loads(r.stdout)


# ----------------------------------------------------------------------------------------------
# 1. IBBA offers per closed deal: zero-truncated negative binomial
# ----------------------------------------------------------------------------------------------
def rounding_consistent_n(pct, n0):
    """Largest n <= n0 for which every published integer percentage (zeros included) can come from an
    integer count c with |100c/n - pct| <= 0.5 and the counts sum to n. None if no n fits (e.g. a chart read)."""
    p = np.asarray(pct, float)
    for n in range(int(n0), 0, -1):
        lo = np.ceil(np.maximum(0, (p - 0.5) * n / 100 - 1e-9)); hi = np.floor((p + 0.5) * n / 100 + 1e-9)
        if np.all(lo <= hi) and lo.sum() <= n <= hi.sum():
            return n
    return None


def load_offer_hist():
    d = pd.read_csv(os.path.join(AGG, "ibba_mp_band_histograms_long.csv"))
    o = d[d.measure == "offers"].copy()
    o["open"] = o.cat_hi.isna()
    o["k"] = o.cat_lo.astype(int)
    g = o.groupby(["period", "band"])
    o["share"] = o.pct / g.pct.transform("sum")             # row sums are 97-104%: renormalise
    o["n"] = o.n_closed.astype(float)
    o["w"] = o.share * o.n
    o["b"] = o.band.map({b: i for i, b in enumerate(BANDS)})
    # revision 3: n_closed counts every closed-deal respondent, but IBBA does not report how many answered the
    # offers item. The largest n consistent with the published (rounded) percentages is a tighter count.
    nrc = {k_: rounding_consistent_n(x.pct.values, x.n_closed.iloc[0]) for k_, x in g}
    o["n_rc"] = [float(nrc[(p_, b_)] or n_) for p_, b_, n_ in zip(o.period, o.band, o.n)]
    o["n_rc_feasible"] = [nrc[(p_, b_)] is not None for p_, b_ in zip(o.period, o.band)]
    return o[o.pct > 0].reset_index(drop=True)


def nb_p(mu, r):
    return r / (r + mu)


def cell_logp(k, op, mu, r):
    """log P(cell | N>=1) for NB(mean mu, size r); open cells are N>=k."""
    p = nb_p(mu, r)
    lp0 = r * np.log(p)
    den = np.log(-np.expm1(lp0))
    lpm = stats.nbinom.logpmf(k, r, p)
    lsf = stats.nbinom.logsf(k - 1, r, p)
    return np.where(op, lsf, lpm) - den


def cell_logp_pois(k, op, lam):
    den = np.log(-np.expm1(-lam))
    return np.where(op, stats.poisson.logsf(k - 1, lam), stats.poisson.logpmf(k, lam)) - den


def zt_mean(mu, r):
    return mu / (1 - nb_p(mu, r) ** r)


def zt_var(mu, r):
    p0 = nb_p(mu, r) ** r
    ex2 = (mu + mu * mu * (1 + 1 / r)) / (1 - p0)
    return ex2 - zt_mean(mu, r) ** 2


def zt_share1(mu, r):
    p = nb_p(mu, r)
    return np.exp(stats.nbinom.logpmf(1, r, p)) / (1 - p ** r)


def p_any(mu, r):
    return 1 - nb_p(mu, r) ** r


def mu_from_ztmean(m, r):
    if m <= 1.0 + 1e-9:
        return 1e-6
    return optimize.brentq(lambda u: zt_mean(u, r) - m, 1e-8, 200)


# ---- revision 2: alternative likelihoods -------------------------------------------------------
def cell_logp_sel(k, op, mu, r, q):
    """log P(cell | closed) when each offer independently leads to a close with prob q, so
    P(close | k offers) = 1-(1-q)^k. q=1 is the zero truncation used by the console.
    Uses sum_j NB(j; p)(1-q)^j over j>=k = (p/p')^r * sf_NB(k-1; p'), p' = 1-(1-p)(1-q)."""
    if q >= 1:
        return cell_logp(k, op, mu, r)
    p = nb_p(mu, r)
    pp = 1 - (1 - p) * (1 - q)
    lratio = r * (np.log(p) - np.log(pp))                    # log PGF(1-q) = log (r/(r+q mu))^r
    den = np.log(-np.expm1(lratio))
    lpm = stats.nbinom.logpmf(k, r, p) + np.log(-np.expm1(k * np.log(1 - q)))
    sf1 = stats.nbinom.sf(k - 1, r, p)
    sf2 = np.exp(lratio) * stats.nbinom.sf(k - 1, r, pp)
    lop = np.log(np.maximum(sf1 - sf2, 1e-300))
    return np.where(op, lop, lpm) - den


XG, WG = np.polynomial.hermite_e.hermegauss(60)
WG = WG / WG.sum()


def pln_table(mu, s, kmax):
    """Poisson-lognormal pmf (mean mu, log-sd s) for k = 0..kmax, Gauss-Hermite (60 nodes)."""
    lam = np.asarray(mu, float)[:, None] * np.exp(s * XG[None, :] - s * s / 2)
    ks = np.arange(kmax + 1)
    lp = ks[None, None, :] * np.log(lam[:, :, None]) - lam[:, :, None] - special.gammaln(ks + 1)[None, None, :]
    return (np.exp(lp) * WG[None, :, None]).sum(1)


def cell_logp_pln(k, op, mu, s):
    T = pln_table(mu, s, int(k.max()))
    C = np.cumsum(T, 1)
    idx = np.arange(len(k))
    pm = T[idx, k]
    sf = 1 - C[idx, k - 1]
    return np.log(np.maximum(np.where(op, sf, pm), 1e-300)) - np.log(1 - T[:, 0])


def cell_logp_pln_sel(k, op, mu, s, q):
    """Poisson-lognormal with the closing selection P(close|k) = 1-(1-q)^k.
    sum_{j>=k} Pois(j; lam)(1-q)^j = exp(-lam q) * sf_Pois(k-1; lam(1-q)), integrated over the nodes."""
    if q >= 1:
        return cell_logp_pln(k, op, mu, s)
    lam = np.asarray(mu, float)[:, None] * np.exp(s * XG[None, :] - s * s / 2)
    T = pln_table(mu, s, int(k.max()))
    C = np.cumsum(T, 1)
    idx = np.arange(len(k))
    pm = T[idx, k] * (1 - (1 - q) ** k)
    sf = 1 - C[idx, k - 1]
    sf2 = (np.exp(-lam * q) * stats.poisson.sf(k[:, None] - 1, lam * (1 - q)) * WG[None, :]).sum(1)
    den = 1 - (np.exp(-lam * q) * WG[None, :]).sum(1)
    return np.log(np.maximum(np.where(op, sf - sf2, pm), 1e-300)) - np.log(den)


def p_any_pln(mu, s):
    mu = np.atleast_1d(np.asarray(mu, float))
    shp = mu.shape
    mu = mu.ravel()
    lam = mu[:, None] * np.exp(s * XG[None, :] - s * s / 2)
    return (1 - (np.exp(-lam) * WG[None, :]).sum(1)).reshape(shp)


def zt_mean_pln(mu, s):
    return np.asarray(mu, float) / p_any_pln(mu, s)


def zt_share1_pln(mu, s):
    T = pln_table(np.atleast_1d(mu), s, 1)
    return T[:, 1] / (1 - T[:, 0])


def fit_alt(o, g, mode="nb", q=1.0, G=None, start=None):
    """Two-parameter fits with mu_b = c*g_b. mode: 'nb' (console ZTNB), 'sel' (NB with closing
    selection q), 'pln' (Poisson-lognormal, second parameter = log-sd), 'mix' (equal-weight
    mixture over the 16 industries' own g, ZTNB). Returns (c, second, nll)."""
    k = o.k.values; op = o.open.values; w = o.w.values; b = o.b.values

    def nll(th):
        c, s2 = np.exp(th)
        if mode == "nb":
            lp = cell_logp(k, op, c * g[b], s2)
        elif mode == "sel":
            lp = cell_logp_sel(k, op, c * g[b], s2, q)
        elif mode == "pln":
            lp = cell_logp_pln(k, op, c * g[b], s2)
        elif mode == "plnsel":
            lp = cell_logp_pln_sel(k, op, c * g[b], s2, q)
        elif mode == "mix":
            num = np.zeros(len(k)); den = np.zeros(len(k))
            for j in range(G.shape[1]):
                mu = c * G[b, j]; p = nb_p(mu, s2)
                num += np.where(op, stats.nbinom.sf(k - 1, s2, p), stats.nbinom.pmf(k, s2, p))
                den += 1 - p ** s2
            lp = np.log(np.maximum(num / den, 1e-300))
        v = -np.sum(w * lp)
        return v if np.isfinite(v) else 1e12
    best = None
    starts = [start] if start is not None else [[math.log(.18), 0.0], [math.log(.25), math.log(1.5)], [math.log(.12), math.log(.6)],
                                                [math.log(.06), math.log(.25)]]
    for x0 in starts:
        f = optimize.minimize(nll, np.asarray(x0, float), method="Nelder-Mead", options=dict(xatol=1e-8, fatol=1e-9, maxiter=6000))
        if best is None or f.fun < best.fun:
            best = f
    c, s2 = np.exp(best.x)
    return c, s2, best.fun


def fit_model(o, kind, g=None, start=None, polish=True):
    """kind: 'M1' band mu and band r; 'M2' band mu, common r; 'M3' log-linear mu in ln V, common r;
    'M5' mu_b = c * g_b (the console's own size gradient, g_b = mean over industries of I.buyers*peRef), common r;
    'ZTP' band-specific Poisson; 'M5P' console size gradient with Poisson offers (fitted scale)."""
    k = o.k.values; op = o.open.values; w = o.w.values; b = o.b.values

    def unpack(th):
        if kind == "M1":
            return np.exp(th[:5])[b], np.exp(th[5:10])[b]
        if kind == "M2":
            return np.exp(th[:5])[b], np.exp(th[5]) * np.ones(len(b))
        if kind == "M3":
            return np.exp(th[0] + th[1] * LNV)[b], np.exp(th[2]) * np.ones(len(b))
        if kind == "M5":
            return (np.exp(th[0]) * g)[b], np.exp(th[1]) * np.ones(len(b))
        if kind == "ZTP":
            return np.exp(th[:5])[b], None
        if kind == "M5P":
            return (np.exp(th[0]) * g)[b], None

    def nll(th):
        mu, r = unpack(th)
        lp = cell_logp_pois(k, op, mu) if kind in ("ZTP", "M5P") else cell_logp(k, op, mu, r)
        v = -np.sum(w * lp)
        return v if np.isfinite(v) else 1e12

    x0 = {"M1": np.r_[np.log([1, 1.5, 2, 2.2, 3]), np.zeros(5)],
          "M2": np.r_[np.log([1, 1.5, 2, 2.2, 3]), 0.0],
          "M3": np.array([np.log(1.7), 0.2, 0.0]),
          "M5": np.array([np.log(0.17), 0.0]),
          "M5P": np.array([np.log(0.25)]),
          "ZTP": np.log([1.6, 2, 2.6, 2.6, 3.8])}[kind] if start is None else start
    f = optimize.minimize(nll, x0, method="L-BFGS-B", bounds=[(-8, 8)] * len(x0))
    th = f.x
    if polish:
        f2 = optimize.minimize(nll, f.x, method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-9, maxiter=20000))
        th = f2.x if f2.fun <= f.fun else f.x
    return th, nll(th), nll


def band_params(kind, th, g=None):
    if kind == "M1":
        return np.exp(th[:5]), np.exp(th[5:10])
    if kind == "M2":
        return np.exp(th[:5]), np.exp(th[5]) * np.ones(5)
    if kind == "M3":
        return np.exp(th[0] + th[1] * LNV), np.exp(th[2]) * np.ones(5)
    if kind == "M5":
        return np.exp(th[0]) * g, np.exp(th[1]) * np.ones(5)
    if kind == "ZTP":
        return np.exp(th[:5]), np.full(5, np.inf)
    if kind == "M5P":
        return np.exp(th[0]) * g, np.full(5, np.inf)


def resample(o, rng, cluster=True):
    """two-stage bootstrap: quarters with replacement, then deals within each band-quarter
    (multinomial on the observed shares with n = n_closed)."""
    qs = sorted(o.period.unique())
    pick = rng.choice(qs, size=len(qs), replace=True) if cluster else qs
    parts = []
    for j, q in enumerate(pick):
        x = o[o.period == q]
        for bnd, xb in x.groupby("band"):
            n = int(round(xb.n.iloc[0]))
            cnt = rng.multinomial(n, (xb.share / xb.share.sum()).values)
            y = xb.copy(); y["w"] = cnt; y["period"] = "%s_%d" % (q, j)
            parts.append(y)
    return pd.concat(parts, ignore_index=True)


# ----------------------------------------------------------------------------------------------
def main():
    res = {}
    ex = {"ind": "medical", "rev": 6e6, "ern": 1.45e6, "grw": .14, "gm": .64, "rec": .72, "cc": .18, "ret": .91, "plt": .38,
          "own": .72, "mgt": .36, "fin": .74, "yrs": 6, "buyers": 65, "st": None, "franchise": False, "ask": 3.24e6}

    # ---------------- probe the current model -----------------------------------------------
    LMM_V = [5e6, 8e6, 1.5811e7, 3e7]
    pr = run_probe({"mode": "probe", "V": list(VC) + LMM_V})
    P = pd.DataFrame(pr["rows"])
    IB = pd.Series({k: v["buyers"] for k, v in pr["IND"].items()})
    P["Ibuy"] = P.ind.map(IB)
    P["g"] = P.Ibuy * P.peRef                       # nEngRef / ENG_SHARE
    PB = P[P.V.isin(list(VC))].copy()
    PB["b"] = PB.V.map({v: i for i, v in enumerate(VC)})
    gb = PB.groupby("b").g.mean().values             # cross-industry mean of I.buyers*peRef at each band centre
    nref_cur = gb * CUR["ENG_SHARE"]
    pass_b = PB.groupby("b")["pass"].mean().values
    log("model probe: g_b (I.buyers*peRef, industry mean) =", np.round(gb, 3), " current nEngRef =", np.round(nref_cur, 2))
    log("model pass-through dE[P|close]/ask per unit premium at REF_RATIO ask =", np.round(pass_b, 3))
    PB.to_csv(os.path.join(OUT, "probe_band_centres.csv"), index=False)

    # ---------------- (b) offers per closed deal ----------------------------------------------
    o = load_offer_hist()
    nb_tot = o.groupby("band").w.sum().reindex(BANDS)
    log("\n(b) IBBA offers histograms: band-quarters =", o.groupby(["period", "band"]).ngroups,
        " deals (approx) by band =", nb_tot.round(0).to_dict())
    fits = {}
    for kind in ["ZTP", "M5P", "M1", "M2", "M3", "M5"]:
        th, nll, _ = fit_model(o, kind, g=gb)
        fits[kind] = (th, nll)
    npar = {"ZTP": 5, "M5P": 1, "M1": 10, "M2": 6, "M3": 3, "M5": 2}
    ntot = o.w.sum()
    comp = []
    for kind, (th, nll) in fits.items():
        mu, r = band_params(kind, th, gb)
        comp.append(dict(model=kind, k=npar[kind], nll=nll, aic=2 * nll + 2 * npar[kind], bic=2 * nll + npar[kind] * np.log(ntot),
                         **{"mu_" + b: mu[i] for i, b in enumerate(BANDS)}, **{"r_" + b: r[i] for i, b in enumerate(BANDS)}))
    comp = pd.DataFrame(comp)
    comp.to_csv(os.path.join(OUT, "offers_model_comparison.csv"), index=False)
    log(comp[["model", "k", "nll", "aic", "bic"]].round(1).to_string(index=False))
    lr = lambda a, b_: 2 * (fits[a][1] - fits[b_][1])
    tests = {"Poisson_vs_M2(NB) LR": lr("ZTP", "M2"), "M5P_vs_M5 (Poisson at the fitted console scale) LR, df1": lr("M5P", "M5"),
             "M2_vs_M1 (common r) LR, df4": lr("M2", "M1"),
             "M3_vs_M2 (log-linear size) LR, df3": lr("M3", "M2"), "M5_vs_M2 (console size gradient) LR, df4": lr("M5", "M2")}
    tests_p = {"M2_vs_M1": stats.chi2.sf(lr("M2", "M1"), 4), "M3_vs_M2": stats.chi2.sf(lr("M3", "M2"), 3),
               "M5_vs_M2": stats.chi2.sf(lr("M5", "M2"), 4)}
    log("LR tests:", {k: round(v, 2) for k, v in tests.items()}, " p:", {k: round(v, 4) for k, v in tests_p.items()})

    # bootstrap (two-stage: quarters, then deals) for M2 and M5
    boot2, boot5 = [], []
    for i in range(B_BOOT):
        ob = resample(o, RNG, cluster=True)
        th2, _, _ = fit_model(ob, "M2", start=fits["M2"][0], polish=False)
        th5, _, _ = fit_model(ob, "M5", g=gb, start=fits["M5"][0], polish=False)
        boot2.append(th2); boot5.append(th5)
    boot2 = np.array(boot2); boot5 = np.array(boot5)
    # within-quarter-only bootstrap (sampling error) for comparison
    boot5w = np.array([fit_model(resample(o, RNG, cluster=False), "M5", g=gb, start=fits["M5"][0], polish=False)[0] for _ in range(150)])
    th2 = fits["M2"][0]; th5 = fits["M5"][0]
    mu2, r2 = band_params("M2", th2)
    mu2_se_log = boot2[:, :5].std(0)
    r2_se_log = boot2[:, 5].std()
    c_hat, r_hat = np.exp(th5)
    c_se_log, r_se_log = boot5[:, 0].std(), boot5[:, 1].std()
    c_ci = np.exp(np.percentile(boot5[:, 0], [2.5, 97.5])); r_ci = np.exp(np.percentile(boot5[:, 1], [2.5, 97.5]))
    log("M2 (band mu, common r): mu_b =", np.round(mu2, 3), "SE(log) =", np.round(mu2_se_log, 3), " r =", round(r2[0], 3), "SE(log)", round(r2_se_log, 3))
    log("M5 (mu_b = c*g_b): c = %.4f (SE %.4f, 95%% %s) r = %.3f (SE %.3f, 95%% %s); within-quarter-only SE(log c)=%.3f vs two-stage %.3f"
        % (c_hat, c_hat * c_se_log, np.round(c_ci, 4), r_hat, r_hat * r_se_log, np.round(r_ci, 3), boot5w[:, 0].std(), c_se_log))

    # quarter jackknife for M5
    qs = sorted(o.period.unique())
    jk = np.array([fit_model(o[o.period != q], "M5", g=gb, start=th5)[0] for q in qs])
    jk_se = np.sqrt((len(qs) - 1) / len(qs) * ((jk - jk.mean(0)) ** 2).sum(0))
    log("M5 quarter-jackknife SE(log c, log r) =", np.round(jk_se, 3))

    # ---- revision 3: quarter dependence. The likelihood treats deals as independent, but the tail-driven parameters
    # vary across quarters more than deal sampling allows. Quasi-likelihood: divide LR statistics by a dispersion phi.
    # phi_lo = Pearson X2/df on cells collapsed to 1,2,3,4,5+ (all excess variation at the cell level);
    # phi_hi = (quarter-jackknife SE / deal-sampling-only SE)^2 for log ENG_SHARE (the design effect of the scale).
    sq_th = np.array([fit_model(o[o.period == q], "M5", g=gb, start=th5)[0] for q in qs])
    oc5 = o.copy(); oc5.loc[oc5.k >= 5, "open"] = True; oc5.loc[oc5.k >= 5, "k"] = 5
    oc5 = oc5.groupby(["period", "band", "b", "k", "open"], as_index=False).w.sum()
    pear = []
    for (q_, bnd_), x_ in oc5.groupby(["period", "band"]):
        bi_ = int(x_.b.iloc[0]); n_ = x_.w.sum()
        for k_ in range(1, 6):
            E_ = n_ * float(np.exp(cell_logp(np.array([k_]), np.array([k_ == 5]), c_hat * gb[bi_], r_hat))[0])
            pear.append((x_[x_.k == k_].w.sum() - E_) ** 2 / E_)
    n_bq = o.groupby(["period", "band"]).ngroups
    phi_lo = float(np.sum(pear) / (len(pear) - n_bq - 2))
    phi_hi = float((jk_se[0] / boot5w[:, 0].std()) ** 2)
    phi_boot = float((c_se_log / boot5w[:, 0].std()) ** 2)
    # heterogeneity of the single-quarter ENG_SHAREs against their own deal-sampling SEs (60-draw deal bootstrap per quarter;
    # a single quarter barely separates ENG_SHARE from NB_R, so these SEs are wide)
    # robust scale (half the 16-84 percentile range): single-quarter draws occasionally run off along the ENG_SHARE-NB_R ridge
    sq_se = np.array([np.diff(np.percentile([fit_model(resample(o[o.period == q], RNG3, cluster=False), "M5", g=gb, start=th5, polish=False)[0][0]
                                             for _ in range(100)], [16, 84]))[0] / 2 for q in qs])
    w_sq = 1 / sq_se ** 2; m_sq = np.sum(w_sq * sq_th[:, 0]) / w_sq.sum()
    sq_Q = float(np.sum(w_sq * (sq_th[:, 0] - m_sq) ** 2)); sq_Q_p = float(stats.chi2.sf(sq_Q, len(qs) - 1))

    def qlr(stat, df_):
        stat = max(float(stat), 0.0)
        return dict(lr=stat, p=float(stats.chi2.sf(stat, df_)), lr_lo=stat / phi_hi, p_lo=float(stats.chi2.sf(stat / phi_hi, df_)),
                    lr_hi=stat / phi_lo, p_hi=float(stats.chi2.sf(stat / phi_lo, df_)), df=df_)

    def qtxt(d_):
        fp_ = lambda v_: ("p=%.3f" % v_) if v_ >= 1e-3 else "p<0.001"
        if d_["p_lo"] < 1e-3:
            pr_ = "p<0.001"
        elif d_["p_hi"] < 1e-3:
            pr_ = "p<0.001-%.3f" % d_["p_lo"]
        else:
            pr_ = "p=%.3f-%.3f" % (d_["p_hi"], d_["p_lo"])
        return "LR %.1f (naive %s; with quarter dependence %.1f-%.1f, %s)" % (d_["lr"], fp_(d_["p"]), d_["lr_lo"], d_["lr_hi"], pr_)
    log("revision 3: single-quarter fits c =", np.round(np.exp(sq_th[:, 0]), 3).tolist(), " r =", np.round(np.exp(sq_th[:, 1]), 2).tolist(),
        " SD(log c) across quarters %.3f vs deal-sampling SE(log c) of the pooled fit %.3f" % (sq_th[:, 0].std(ddof=1), boot5w[:, 0].std()))
    log("quasi-likelihood dispersion: Pearson X2/df (cells 1-5+) %.2f; (jackknife/deal-sampling SE)^2 for log c %.2f; (two-stage/deal-sampling)^2 %.2f"
        % (phi_lo, phi_hi, phi_boot))
    log("single-quarter deal-sampling SE(log c) %s; heterogeneity Q %.2f (df %d, p=%.3f)" % (np.round(sq_se, 3).tolist(), sq_Q, len(qs) - 1, sq_Q_p))
    QL = {"Poisson_vs_NB_free_bands": qlr(tests["Poisson_vs_M2(NB) LR"], 5), "Poisson_vs_NB_console_scale": qlr(tests["M5P_vs_M5 (Poisson at the fitted console scale) LR, df1"], 1),
          "common_r": qlr(tests["M2_vs_M1 (common r) LR, df4"], 4), "console_gradient_vs_free_bands": qlr(tests["M5_vs_M2 (console size gradient) LR, df4"], 4)}

    # band-level c_b (M2 mu / g) and empirical-Bayes shrinkage toward the pooled c (M5)
    cb = mu2 / gb
    cb_se = mu2_se_log                                  # SE of log c_b
    resid = np.log(cb) - np.log(c_hat)
    Q = np.sum(resid ** 2 / cb_se ** 2)
    wts = 1 / cb_se ** 2
    tau2 = max(0.0, (Q - (len(cb) - 1)) / (wts.sum() - (wts ** 2).sum() / wts.sum()))
    shrink = tau2 / (tau2 + cb_se ** 2)
    cb_eb = np.exp(np.log(c_hat) + shrink * resid)
    log("band c_b =", np.round(cb, 4), " SE(log) =", np.round(cb_se, 3), " Cochran Q =", round(Q, 2), "(df 4, p=%.3f)" % stats.chi2.sf(Q, 4),
        " tau2 =", round(tau2, 4), " EB-shrunk c_b =", np.round(cb_eb, 4),
        " [approximate: the band SEs come from one bootstrap that resamples the same quarters for all bands, so they are correlated, "
        "and the pooled c is fitted to the same data]")

    # implied conditional means / one-offer shares
    mu5, r5 = band_params("M5", th5, gb)
    obs = o.groupby("band").apply(lambda x: pd.Series({
        "share1": x[x.k == 1].w.sum() / x.w.sum(),
        "mean_lb": (x.k * x.w).sum() / x.w.sum()})).reindex(BANDS)
    btab = pd.DataFrame({"band": BANDS, "V_centre": VC, "deals": nb_tot.values, "obs_share1": obs.share1.values, "obs_mean_lowerbound": obs.mean_lb.values,
                         "M2_mu": mu2, "M2_mu_se_log": mu2_se_log, "M2_ztmean": zt_mean(mu2, r2), "M2_share1": zt_share1(mu2, r2),
                         "g_model": gb, "nEngRef_current": nref_cur,
                         "current_poisson_share1": nref_cur * np.exp(-nref_cur) / (1 - np.exp(-nref_cur)),
                         "current_poisson_ztmean": nref_cur / (1 - np.exp(-nref_cur)),
                         "rec_mu": mu5, "rec_ztmean": zt_mean(mu5, r5), "rec_share1": zt_share1(mu5, r5), "rec_p_any": p_any(mu5, r5),
                         "c_band": cb, "c_band_se_log": cb_se, "c_band_EB": cb_eb})
    btab.to_csv(os.path.join(OUT, "offers_by_band.csv"), index=False)
    log(btab[["band", "obs_share1", "current_poisson_share1", "rec_share1", "obs_mean_lowerbound", "current_poisson_ztmean", "rec_ztmean", "nEngRef_current", "rec_mu", "rec_p_any"]].round(3).to_string(index=False))

    # ---- validation 1: leave-one-quarter-out held-out log-likelihood per deal
    rows = []
    for q in qs:
        tr, te = o[o.period != q], o[o.period == q]
        k_, op_, w_, b_ = te.k.values, te.open.values, te.w.values, te.b.values
        t5, _, _ = fit_model(tr, "M5", g=gb, start=th5)
        t2, _, _ = fit_model(tr, "M2", start=th2)
        tp, _, _ = fit_model(tr, "ZTP", start=fits["ZTP"][0])
        t5p, _, _ = fit_model(tr, "M5P", g=gb, start=fits["M5P"][0])
        m5, rr5 = band_params("M5", t5, gb); m2_, rr2 = band_params("M2", t2)
        lam = np.exp(tp); lam5p = np.exp(t5p[0]) * gb
        ll = {"recommended_M5": np.sum(w_ * cell_logp(k_, op_, m5[b_], rr5[b_])),
              "poisson_fitted_scale_M5P": np.sum(w_ * cell_logp_pois(k_, op_, lam5p[b_])),
              "band_free_M2": np.sum(w_ * cell_logp(k_, op_, m2_[b_], rr2[b_])),
              "zt_poisson_band_free": np.sum(w_ * cell_logp_pois(k_, op_, lam[b_])),
              "current_model_poisson": np.sum(w_ * cell_logp_pois(k_, op_, nref_cur[b_]))}
        s1 = te[te.k == 1].groupby("b").w.sum() / te.groupby("b").w.sum()
        for kk, v in ll.items():
            rows.append(dict(heldout=q, model=kk, ll_per_deal=v / w_.sum(), n=w_.sum()))
        rows.append(dict(heldout=q, model="share1_abs_err_recommended", ll_per_deal=np.mean(np.abs(s1.values - zt_share1(m5, rr5)[s1.index])), n=w_.sum()))
        rows.append(dict(heldout=q, model="share1_abs_err_current", ll_per_deal=np.mean(np.abs(s1.values - (nref_cur * np.exp(-nref_cur) / (1 - np.exp(-nref_cur)))[s1.index])), n=w_.sum()))
    cv = pd.DataFrame(rows)
    cv.to_csv(os.path.join(OUT, "offers_loqo_cv.csv"), index=False)
    cvs = cv.groupby("model").apply(lambda x: np.average(x.ll_per_deal, weights=x.n))
    log("LOQO held-out log-lik per deal (and mean |share1 error|):", cvs.round(4).to_dict())

    # ---- validation 2: temporal holdout against the separate 'average offers per deal' series 2024Q1-2026Q2
    av = pd.read_csv(os.path.join(AGG, "ibba_mp_offers_avg_panel.csv"))
    av = av[av.period.str.contains("Q") & (av.period >= "2024Q1")]
    av["pred_rec"] = av.band.map(dict(zip(BANDS, zt_mean(mu5, r5))))
    av["pred_M2"] = av.band.map(dict(zip(BANDS, zt_mean(mu2, r2))))
    av["pred_current"] = av.band.map(dict(zip(BANDS, nref_cur / (1 - np.exp(-nref_cur)))))
    lam5p_full = np.exp(fits["M5P"][0][0]) * gb
    av["pred_M5P"] = av.band.map(dict(zip(BANDS, lam5p_full / (1 - np.exp(-lam5p_full)))))
    # strictly temporal: train on the 2023 histograms only (2025Q4 sits inside the 2024Q1-2026Q2 test window)
    th23, _, _ = fit_model(o[o.period < "2024"], "M5", g=gb, start=fits["M5"][0])
    mu23, r23 = band_params("M5", th23, gb)
    av["pred_rec_train2023"] = av.band.map(dict(zip(BANDS, zt_mean(mu23, r23))))
    th_rows = []
    for bnd, x in av.groupby("band"):
        th_rows.append(dict(band=bnd, n_q=len(x), obs_mean=x.avg_offers_per_deal.mean(), obs_sd=x.avg_offers_per_deal.std(),
                            pred_rec=x.pred_rec.iloc[0], pred_M2=x.pred_M2.iloc[0], pred_current=x.pred_current.iloc[0],
                            pred_M5P=x.pred_M5P.iloc[0], pred_rec_train2023=x.pred_rec_train2023.iloc[0],
                            n_q_above_rec=int((x.avg_offers_per_deal > x.pred_rec.iloc[0]).sum())))
    thd = pd.DataFrame(th_rows).set_index("band").reindex(BANDS).reset_index()
    rmse = lambda c: float(np.sqrt(np.mean((av.avg_offers_per_deal - av[c]) ** 2)))
    bias = lambda c: float(np.mean(av.avg_offers_per_deal - av[c]))
    thd.to_csv(os.path.join(OUT, "offers_temporal_holdout_avgpanel.csv"), index=False)
    hold = {c: dict(rmse=rmse(c), bias=bias(c)) for c in ["pred_rec", "pred_M2", "pred_current", "pred_M5P", "pred_rec_train2023"]}
    hold["train2023_params"] = dict(c=float(np.exp(th23[0])), r=float(np.exp(th23[1])))
    hold["band_5M_bias_rec"] = float((av[av.band == "5M-50M"].avg_offers_per_deal - av[av.band == "5M-50M"].pred_rec).mean())
    hold["band_5M_obs_mean"] = float(av[av.band == "5M-50M"].avg_offers_per_deal.mean())
    log("holdout on a DIFFERENT IBBA question (average-offers bars 2024Q1-2026Q2, n=%d band-quarters):" % len(av),
        {k: ({a: round(b, 3) for a, b in v.items()} if isinstance(v, dict) else v) for k, v in hold.items()})
    log("strictly temporal version (train on the 2023 histograms only): c=%.4f r=%.3f, RMSE %.3f (bias %+.3f) vs current %.3f"
        % (np.exp(th23[0]), np.exp(th23[1]), hold["pred_rec_train2023"]["rmse"], hold["pred_rec_train2023"]["bias"], hold["pred_current"]["rmse"]))
    log(thd.round(3).to_string(index=False))

    # ---- revision 3: the two IBBA offer series disagree with each other wherever both exist (2023Q4, 2025Q4).
    # Histogram lower-bound mean (open cells at their lower edge) against the same report's average-offers table/bars.
    avall = pd.read_csv(os.path.join(AGG, "ibba_mp_offers_avg_panel.csv"))
    t25 = None
    with open(RAW_Q4_2025, encoding="utf-8", errors="replace") as f_:
        for line_ in f_:
            if line_.strip().startswith("Average # of Offers per deal"):
                vv = [float(v_) for v_ in re.findall(r"\d+\.\d+", line_)]
                if len(vv) >= 5:
                    t25 = dict(zip(BANDS, vv[:5]))
    assert t25 is not None, "2025Q4 average-offers table not found in the raw report text"
    lbq = o.groupby(["period", "band"]).apply(lambda x: float((x.k * x.share).sum() / x.share.sum())).rename("hist_lower_bound_mean").reset_index()
    scons = lbq[lbq.period.isin(["2023Q4", "2025Q4"])].copy()
    a23 = avall[avall.period == "2023Q4"].set_index("band").avg_offers_per_deal
    scons["series_average"] = [float(a23[b_]) if p_ == "2023Q4" else t25[b_] for p_, b_ in zip(scons.period, scons.band)]
    scons["series_source"] = ["exec report Figure 11 bars" if p_ == "2023Q4" else "full report average-offers table (raw text)" for p_ in scons.period]
    scons["average_minus_lower_bound"] = scons.series_average - scons.hist_lower_bound_mean
    scons["consistent"] = scons.average_minus_lower_bound >= -1e-9
    scons["b"] = scons.band.map({b_: i for i, b_ in enumerate(BANDS)})
    scons = scons.sort_values(["period", "b"])
    scons["model_offers_per_closed_deal"] = scons.b.map(dict(enumerate(zt_mean(mu5, r5))))
    scons.drop(columns="b").to_csv(os.path.join(OUT, "offers_series_consistency.csv"), index=False)
    r23 = o[o.period == "2023Q4"]
    p1max = float(r23[r23.k == 1].pct.max()) / 100; p2max = float(r23[r23.k == 2].pct.max()) / 100
    min_feasible_23 = p1max + 2 * p2max + 3 * (1 - p1max - p2max)
    c23 = scons[scons.period == "2023Q4"]; c25 = scons[scons.period == "2025Q4"]
    SER = dict(n_incons_2023=int((~c23.consistent).sum()), gap_2023=[float(-c23.average_minus_lower_bound.max()), float(-c23.average_minus_lower_bound.min())],
               min_feasible_2023=min_feasible_23, p1max=p1max, p2max=p2max, min_bar_2023=float(c23.series_average.min()),
               t25=t25, diff_2025=c25.average_minus_lower_bound.round(2).tolist(), n_incons_2025=int((~c25.consistent).sum()),
               lb_2023=c23.hist_lower_bound_mean.round(3).tolist(), bars_2023=c23.series_average.tolist(), lb_2025=c25.hist_lower_bound_mean.round(2).tolist())
    log("two IBBA offer series where both exist (histogram lower-bound mean vs the same report's averages):\n" + scons.round(3).to_string(index=False))
    log("2023Q4: Figure 11 bars sit BELOW the Figure 10 histogram's lowest possible mean in %d of 5 bands (by %.2f-%.2f). Even with the chart's largest "
        "shares at 1 and 2 offers (%.0f%%, %.0f%%) in one band, the lowest feasible mean is %.2f > the smallest bar %.2f, for any assignment of chart series to bands. "
        "2025Q4: the table sits above the histogram lower bound in %d of 5 bands (%s) and below it in $2M-5M."
        % (SER["n_incons_2023"], SER["gap_2023"][0], SER["gap_2023"][1], 100 * p1max, 100 * p2max, min_feasible_23, SER["min_bar_2023"],
           5 - SER["n_incons_2025"], "/".join("%+.2f" % x for x in SER["diff_2025"])))

    # ---- validation 3: Q4-2022 share of closed deals with an offer from a different buyer
    # INCONCLUSIVE check: the singular and plural wordings are not nested (plural exceeds singular in 3 bands)
    ad0 = pd.read_csv(os.path.join(AGG, "ibba_mp_additional_offers_2022q4.csv"))
    ad0 = ad0[ad0.band.isin(BANDS)]
    ad = ad0[ad0.listing_status == "closed"].pivot_table(index="band", columns="question", values="pct").reindex(BANDS)
    ad.columns = ["plural_offers_from_different_buyers" if "plural" in c_ else "singular_offer_from_a_different_buyer" for c_ in ad.columns]
    adt = ad0[ad0.listing_status == "terminated"].pivot_table(index="band", columns="question", values="pct").reindex(BANDS)
    ad["terminated_singular"] = adt[[c_ for c_ in adt.columns if "plural" not in c_][0]].values
    ad["pred_rec_ge2"] = 1 - zt_share1(mu5, r5)
    ad["pred_cur_ge2"] = 1 - nref_cur * np.exp(-nref_cur) / (1 - np.exp(-nref_cur))
    ad = ad.reset_index()
    ad.to_csv(os.path.join(OUT, "offers_check_2022q4.csv"), index=False)
    log("2022Q4 closed deals, 'an offer from a different buyer' (singular) and 'offers from different buyers' (plural), %, vs predicted P(>=2 | closed); "
        "terminated listings (singular) for reference - INCONCLUSIVE, wording ambiguous:\n" + ad.round(3).to_string(index=False))

    # ---- consistency: chance of >=1 offer vs Pepperdine base close rates (broker .608 -> intermediated .697)
    base_close = np.array([0.608, 0.608, 0.608 + (0.6967 - 0.608) * np.clip(np.log(VC[2] / 1e6) / np.log(5), 0, 1),
                           0.608 + (0.6967 - 0.608) * np.clip(np.log(VC[3] / 1e6) / np.log(5), 0, 1), 0.6967])
    log("P(>=1 offer) at the typical pool (recommended) =", np.round(p_any(mu5, r5), 3), " Pepperdine base close =", np.round(base_close, 3))

    kk_, op_, w_, b_ = o.k.values, o.open.values, o.w.values, o.b.values
    def nll5(th):
        mu, rr = np.exp(th[0]) * gb, np.exp(th[1])
        v = -np.sum(w_ * cell_logp(kk_, op_, mu[b_], rr))
        return v if np.isfinite(v) else 1e12
    cons = [{"type": "ineq", "fun": (lambda th, i=i: p_any(np.exp(th[0]) * gb[i], np.exp(th[1])) - base_close[i])} for i in range(5)]
    fc_ = optimize.minimize(nll5, th5 + np.array([0.2, 0.5]), method="SLSQP", constraints=cons, options=dict(maxiter=500, ftol=1e-10))
    c_con, r_con = np.exp(fc_.x)
    lr_con = 2 * (fc_.fun - fits["M5"][1])
    # thin-pool factor at half and a quarter of the typical pool, unconstrained vs constrained vs current Poisson
    def thin(f, mu, rr):
        return p_any(f * mu, rr) / p_any(mu, rr)
    thin_tab = pd.DataFrame([dict(band=BANDS[i], f=f, current_poisson=(1 - np.exp(-f * nref_cur[i])) / (1 - np.exp(-nref_cur[i])),
                                  recommended=thin(f, c_hat * gb[i], r_hat), constrained=thin(f, c_con * gb[i], r_con),
                                  zt_poisson_scale=(1 - np.exp(-f * np.exp(fits["ZTP"][0][i]))) / (1 - np.exp(-np.exp(fits["ZTP"][0][i]))),
                                  r_lo=thin(f, c_hat * gb[i], r_ci[0]), r_hi=thin(f, c_hat * gb[i], r_ci[1]))
                             for i in range(5) for f in (0.25, 0.5)])
    thin_tab.to_csv(os.path.join(OUT, "thin_factor_sensitivity.csv"), index=False)
    log("constrained fit (P(>=1 offer) >= Pepperdine base close in every band): c=%.4f r=%.3f, LR cost %.2f (chi2 p~%.3f)" % (c_con, r_con, lr_con, stats.chi2.sf(max(lr_con, 0), 1)))
    log("thin-pool factor sensitivity:\n" + thin_tab.round(3).to_string(index=False))

    # ---- TRANBI analog: dispersion of buyer applications
    tr_app = pd.read_csv(os.path.join(TRANBI, "fit_applications_distribution.csv"))
    log("TRANBI applications ZTNB r (analog, top-of-funnel interest):", tr_app[["binning", "nb_size_r", "nb_r_se"]].round(3).values.tolist())

    # ---------------- revision 2: how far ENG_SHARE, NB_R and thinF move -------------------------
    # thinF is evaluated per industry x band centre (the console's own nEngRef), not at band means
    G = PB.pivot_table(index="b", columns="ind", values="g").sort_index().values      # 5 bands x 16 industries
    fgrid = np.linspace(0.05, 1.0, 20)

    def pa_fn(fam, s2):
        return (lambda m: p_any(m, s2)) if fam == "nb" else (lambda m: p_any_pln(m, s2))

    def thin_cells(c, s2, fam="nb", q=1.0, beta=1.0, f=0.5):
        pa = pa_fn(fam, s2); nr = c * G
        return pa(q * (f ** beta) * nr) / pa(q * nr)

    def max_thin_diff(c, s2, fam="nb", q=1.0):
        return float(max(np.abs(thin_cells(c, s2, fam, q, f=f) - thin_cells(c_hat, r_hat, f=f)).max() for f in fgrid))

    rec_half, rec_quart = thin_cells(c_hat, r_hat, f=0.5), thin_cells(c_hat, r_hat, f=0.25)
    rngf = lambda a: "%.2f-%.2f" % (np.min(a), np.max(a))
    log("\nrevision 2. thinF across industries x band centres (recommended): half pool %s, quarter %s" % (rngf(rec_half), rngf(rec_quart)))

    # (i) specifications: tail cells, quarters, weights, industry mixture, mixing family
    def collapse5(df):
        s_ = df.copy(); s_.loc[s_.k >= 5, "open"] = True; s_.loc[s_.k >= 5, "k"] = 5
        return s_.groupby(["period", "band", "b", "k", "open"], as_index=False).w.sum()
    oa = o.copy(); oa["w"] = oa.approx_count.astype(float)
    av_s = pd.read_csv(os.path.join(AGG, "ibba_mp_offers_avg_panel.csv"))
    av_s = av_s[av_s.period.str.contains("Q") & (av_s.period >= "2024Q1")]
    orc = o.copy(); orc["w"] = orc.share * orc.n_rc
    cell25_5m = (o.period == "2025Q4") & (o.band == "5M-50M")
    # revision 3: 'drop 2025Q4' IS the 2023-histograms-only fit and the strictly temporal training set (the histograms
    # cover 2023Q1-Q4 and 2025Q4 only), so it appears once; both flagged quarters are dropped together as well.
    specs = [("baseline (recommended)", o, "nb"),
             (L_D23, o[o.period != "2023Q4"], "nb"),
             (L_D25, o[o.period != "2025Q4"], "nb"),
             ("drop 2025Q4 5M-50M cell (35% at 10+, n=26)", o[~cell25_5m], "nb"),
             ("drop 2023Q4 and the 2025Q4 5M-50M cell", o[(o.period != "2023Q4") & ~cell25_5m], "nb"),
             ("2023Q1-Q3 only (both flagged quarters dropped)", o[o.period < "2023Q4"], "nb"),
             ("tail collapsed to 1,2,3,4,5+", collapse5(o), "nb"),
             ("approx_count weights (not renormalised)", oa, "nb"),
             ("rounding-consistent n weights (largest n that reproduces the published percentages)", orc, "nb"),
             ("industry-mixture likelihood", o, "mix"),
             ("Poisson-lognormal mixing family", o, "pln")]
    spec_rows = []
    for lab, df_, mode in specs:
        c_, s_, nl_ = fit_alt(df_, gb, mode, G=G)
        fam = "pln" if mode == "pln" else "nb"
        pa = pa_fn(fam, s_)
        ztm = (c_ * G) / pa(c_ * G)
        zt_b = ztm.mean(1)
        pred = av_s.band.map(dict(zip(BANDS, zt_b)))
        e_ = av_s.avg_offers_per_deal - pred
        th_h, th_q = thin_cells(c_, s_, fam, f=0.5), thin_cells(c_, s_, fam, f=0.25)
        spec_rows.append(dict(spec=lab, family=fam, c=c_, dispersion=s_, nll=nl_, n_deals=float(df_.w.sum()),
                              aic=2 * nl_ + 4 if df_ is o else np.nan,
                              p_any_typ_min=float(pa(c_ * G).min()), p_any_typ_max=float(pa(c_ * G).max()),
                              p_any_typ_lt500k_mean=float(pa(c_ * G[0]).mean()),
                              thin_half_min=th_h.min(), thin_half_max=th_h.max(), thin_quart_min=th_q.min(), thin_quart_max=th_q.max(),
                              max_abs_thin_diff_vs_rec=max_thin_diff(c_, s_, fam), bars_rmse=float(np.sqrt((e_ ** 2).mean())), bars_bias=float(e_.mean()),
                              **{"ztmean_" + b_: zt_b[i] for i, b_ in enumerate(BANDS)}))
    SPEC = pd.DataFrame(spec_rows)
    SPEC.to_csv(os.path.join(OUT, "offers_spec_sensitivity.csv"), index=False)
    log("specification sensitivity (c = ENG_SHARE; dispersion = NB r or PLN log-sd):\n" +
        SPEC[["spec", "family", "c", "dispersion", "nll", "thin_half_min", "thin_half_max", "thin_quart_min", "thin_quart_max",
              "max_abs_thin_diff_vs_rec", "bars_rmse", "p_any_typ_min", "p_any_typ_max"]].round(3).to_string(index=False))
    nbspec = SPEC[SPEC.family == "nb"]
    pln_row = SPEC[SPEC.family == "pln"].iloc[0]
    # PLN: quarter jackknife SE and LOQO held-out log-lik per deal (same folds as the NB)
    pln_jk, pln_ll, nb_ll, wsum = [], 0.0, 0.0, 0.0
    for q_ in qs:
        tr_, te_ = o[o.period != q_], o[o.period == q_]
        cj, sj, _ = fit_alt(tr_, gb, "pln", start=[math.log(pln_row.c), math.log(pln_row.dispersion)])
        pln_jk.append(math.log(cj))
        pln_ll += np.sum(te_.w.values * cell_logp_pln(te_.k.values, te_.open.values, cj * gb[te_.b.values], sj))
        wsum += te_.w.sum()
    pln_jk = np.array(pln_jk)
    pln_c_se = pln_row.c * math.sqrt((len(qs) - 1) / len(qs) * ((pln_jk - pln_jk.mean()) ** 2).sum())
    pln_loqo = pln_ll / wsum
    log("Poisson-lognormal: c=%.4f (quarter-jackknife SE %.4f), log-sd %.3f, NLL %.2f vs NB %.2f (dAIC %.1f); LOQO held-out log-lik per deal %.4f"
        % (pln_row.c, pln_c_se, pln_row.dispersion, pln_row.nll, fits["M5"][1], 2 * (fits["M5"][1] - pln_row.nll), pln_loqo))
    # revision 3: distinct NB specifications (ENG_SHARE must stay paired with the NB r it was fitted with; the PLN is reported apart)
    nb_alt = nbspec[~nbspec.spec.str.startswith("baseline")]
    n_spec_nb = int(len(nb_alt))
    QL["pln_vs_nb (same parameter count, not nested; LR = dAIC)"] = qlr(2 * (fits["M5"][1] - pln_row.nll), 1)
    QL["pepperdine_constrained"] = qlr(lr_con, 1)
    log("NB specifications other than the baseline: %d distinct; ENG_SHARE %.3f-%.3f, NB_R %.2f-%.2f. Quasi-likelihood: PLN vs NB %s; Pepperdine-constrained fit %s"
        % (n_spec_nb, nbspec.c.min(), nbspec.c.max(), nbspec.dispersion.min(), nbspec.dispersion.max(),
           qtxt(QL["pln_vs_nb (same parameter count, not nested; LR = dAIC)"]), qtxt(QL["pepperdine_constrained"])))

    # (ii) closing that depends on the number of offers: P(close|k) = 1-(1-q)^k. Not identified by the
    # histograms; bounded (model-dependently) by Pepperdine's base close rate if P(close) <= P(a successful offer)
    sel_rows = []
    for fam, mode in (("nb", "sel"), ("pln", "plnsel")):
        for q_ in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4):
            c_, s_, nl_ = fit_alt(o, gb, mode if q_ < 1 else fam, q=q_)
            pa = pa_fn(fam, s_)
            pcl = pa(q_ * c_ * G).mean(1)                       # P(close from offers | typical pool), industry mean by band
            th_h = thin_cells(c_, s_, fam, q_, f=0.5); th_q = thin_cells(c_, s_, fam, q_, f=0.25)
            sel_rows.append(dict(family=fam, q=q_, c=c_, dispersion=s_, nll=nl_, thin_half_min=th_h.min(), thin_half_max=th_h.max(),
                                 thin_quart_min=th_q.min(), thin_quart_max=th_q.max(),
                                 drop_half_vs_rec_min=float((rec_half - th_h).min()), drop_half_vs_rec_max=float((rec_half - th_h).max()),
                                 drop_quart_vs_rec_min=float((rec_quart - th_q).min()), drop_quart_vs_rec_max=float((rec_quart - th_q).max()),
                                 pepperdine_ok_bands=int(np.sum(pcl >= base_close - 1e-9)), pepperdine_ok_ge1M=bool(np.all(pcl[2:] >= base_close[2:] - 0.005)),
                                 **{"p_close_typ_" + b_: pcl[i] for i, b_ in enumerate(BANDS)}))
    SEL = pd.DataFrame(sel_rows)
    for fam in ("nb", "pln"):
        m_ = SEL.family == fam
        SEL.loc[m_, "lr_vs_q1"] = 2 * (SEL[m_ & (SEL.q == 1)].nll.iloc[0] - SEL[m_].nll)
    SEL.to_csv(os.path.join(OUT, "thin_factor_selection_q.csv"), index=False)
    log("closing selection q (P(close|k)=1-(1-q)^k), refit at each q:\n" +
        SEL[["family", "q", "c", "dispersion", "nll", "lr_vs_q1", "thin_half_min", "thin_half_max", "drop_half_vs_rec_min", "drop_half_vs_rec_max",
             "pepperdine_ok_bands", "pepperdine_ok_ge1M"] + ["p_close_typ_" + b_ for b_ in BANDS]].round(3).to_string(index=False))
    log("Pepperdine base close by band:", np.round(base_close, 3))
    sel_nb = SEL[SEL.family == "nb"].set_index("q"); sel_pln = SEL[SEL.family == "pln"].set_index("q")
    q_min_pln = float(SEL[(SEL.family == "pln") & SEL.pepperdine_ok_ge1M].q.min())
    q_opt_nb = float(SEL[SEL.family == "nb"].sort_values("lr_vs_q1").q.iloc[-1]); q_opt_pln = float(SEL[SEL.family == "pln"].sort_values("lr_vs_q1").q.iloc[-1])
    QL["selection_q_nb"] = qlr(SEL[SEL.family == "nb"].lr_vs_q1.max(), 1); QL["selection_q_pln"] = qlr(SEL[SEL.family == "pln"].lr_vs_q1.max(), 1)
    log("selection q: the histograms LEAN toward q<1 (NB profile optimum q=%.1f, %s; PLN optimum q=%.1f, %s)"
        % (q_opt_nb, qtxt(QL["selection_q_nb"]), q_opt_pln, qtxt(QL["selection_q_pln"])))

    # (iii) offers growing less than in proportion to buyers contacted: n_offers ~ buyers^beta (not identified)
    beta_rows = []
    for beta in (1.0, 0.75, 0.5):
        th_h = thin_cells(c_hat, r_hat, beta=beta, f=0.5); th_q = thin_cells(c_hat, r_hat, beta=beta, f=0.25)
        beta_rows.append(dict(beta=beta, thin_half_min=th_h.min(), thin_half_max=th_h.max(), thin_quart_min=th_q.min(), thin_quart_max=th_q.max(),
                              rise_half_vs_rec_min=float((th_h - rec_half).min()), rise_half_vs_rec_max=float((th_h - rec_half).max())))
    BETA = pd.DataFrame(beta_rows)
    BETA.to_csv(os.path.join(OUT, "thin_factor_proportionality_beta.csv"), index=False)
    log("offers ~ buyers^beta (beta=1 in the console):\n" + BETA.round(3).to_string(index=False))

    # revision 3: a weak, non-transferable analog for beta. Flippa open listings (one snapshot): offers on watchers.
    # Watchers are not buyers contacted, durations are censored and both respond to listing quality, so this only
    # indicates a direction. Poisson (HC1) and NB, with and without a log-ask control; 10-fold CV of the Poisson
    # log-likelihood with vs without watchers.
    fo_ = pd.read_csv(FLIPPA_OPEN)
    fo_ = fo_[fo_.offer_count.notna() & (fo_.asking_price_usd > 0) & ~fo_.flag_price_placeholder.astype(bool) & ~fo_.flag_price_extreme.astype(bool)].copy()
    fo_["lw"] = np.log1p(fo_.watchers); fo_["la"] = np.log(fo_.asking_price_usd)
    WAT = {}
    for lab_, cols_ in (("no control", ["lw"]), ("log-ask control", ["lw", "la"])):
        X_ = sm.add_constant(fo_[cols_])
        fp_ = sm.GLM(fo_.offer_count, X_, family=sm.families.Poisson()).fit(cov_type="HC1")
        fn_ = sm.NegativeBinomial(fo_.offer_count, X_).fit(start_params=np.r_[fp_.params.values, 1.0], method="bfgs", maxiter=2000, disp=0, cov_type="HC1")
        WAT[lab_] = dict(poisson=float(fp_.params["lw"]), poisson_se=float(fp_.bse["lw"]), nb=float(fn_.params["lw"]), nb_se=float(fn_.bse["lw"]))
    idx_ = RNG3.permutation(len(fo_)); ll1 = ll0 = 0.0
    for fold_ in np.array_split(idx_, 10):
        trn_ = np.setdiff1d(idx_, fold_)
        for cols_, acc in ((["lw", "la"], 1), (["la"], 0)):
            X_ = sm.add_constant(fo_[cols_]).values
            f_ = sm.GLM(fo_.offer_count.values[trn_], X_[trn_], family=sm.families.Poisson()).fit()
            ll_ = float(np.sum(stats.poisson.logpmf(fo_.offer_count.values[fold_], f_.predict(X_[fold_]))))
            if acc:
                ll1 += ll_
            else:
                ll0 += ll_
    WAT["n"] = int(len(fo_)); WAT["cv_ll_per_listing_with"] = ll1 / len(fo_); WAT["cv_ll_per_listing_without"] = ll0 / len(fo_)
    wat_vals = [WAT[k_][m_] for k_ in ("no control", "log-ask control") for m_ in ("poisson", "nb")]
    WAT["range"] = [float(min(wat_vals)), float(max(wat_vals))]; WAT["n_below1"] = int(sum(v_ < 1 for v_ in wat_vals)); WAT["n_est"] = len(wat_vals)
    log("Flippa open listings (analog for beta, n=%d): elasticity of offers to (1+watchers): %s; 10-fold CV Poisson log-lik per listing %.3f with watchers vs %.3f without"
        % (WAT["n"], {k_: {a_: round(b_, 3) for a_, b_ in v_.items()} for k_, v_ in WAT.items() if isinstance(v_, dict)}, WAT["cv_ll_per_listing_with"], WAT["cv_ll_per_listing_without"]))

    # (iv) the $5M+ band: IBBA's 2024-26 bars average more offers than the console gradient gives
    mu_bar5 = mu_from_ztmean(hold["band_5M_obs_mean"], r_hat)
    thin5_rec = p_any(0.5 * mu5[4], r_hat) / p_any(mu5[4], r_hat)
    thin5_bar = p_any(0.5 * mu_bar5, r_hat) / p_any(mu_bar5, r_hat)
    mu_m2_5 = mu2[4]
    thin5_m2 = p_any(0.5 * mu_m2_5, r_hat) / p_any(mu_m2_5, r_hat)
    log("$5M+ band: bars mean %.2f vs console %.2f (bias %+.2f; %d of 9 holdout quarters above). Half-pool thinF at the band centre: %.3f (console) vs %.3f if the band "
        "matched the bars and %.3f at the band-free histogram fit"
        % (hold["band_5M_obs_mean"], zt_mean(mu5[4], r_hat), hold["band_5M_bias_rec"], int(thd.set_index("band").loc["5M-50M", "n_q_above_rec"]), thin5_rec, thin5_bar, thin5_m2))

    # (v) calibration numbers for a test: industry-mean implied offers per closed deal at the band centres,
    # against the band-free histogram fit (M2, tails imputed by the NB) and its two-stage bootstrap SE
    zt_ind_mean = ((c_hat * G) / p_any(c_hat * G, r_hat)).mean(1)
    m2_zt_boot = np.array([zt_mean(np.exp(th_[:5]), np.exp(th_[5])) for th_ in boot2])
    m2_zt = zt_mean(mu2, r2); m2_zt_se = m2_zt_boot.std(0)
    log("calibration: industry-mean implied offers per closed deal %s; band-free histogram fit %s (bootstrap SE %s); lower-bound means %s"
        % (np.round(zt_ind_mean, 2), np.round(m2_zt, 2), np.round(m2_zt_se, 2), np.round(obs.mean_lb.values, 2)))

    # (vi) revision 3: the uncertainty of what the console uses. thinF at half / a quarter of the typical pool, per industry x
    # band centre, over the two-stage bootstrap draws (quarters, then deals); and over single-quarter fits.
    th_bs_half = np.array([thin_cells(math.exp(t_[0]), math.exp(t_[1]), f=0.5) for t_ in boot5])
    th_bs_quart = np.array([thin_cells(math.exp(t_[0]), math.exp(t_[1]), f=0.25) for t_ in boot5])
    thin_se_half = th_bs_half.std(0); thin_se_quart = th_bs_quart.std(0)
    th_bm = np.array([p_any(0.5 * math.exp(t_[0]) * gb, math.exp(t_[1])) / p_any(math.exp(t_[0]) * gb, math.exp(t_[1])) for t_ in boot5])
    th_sq = np.array([p_any(0.5 * math.exp(t_[0]) * gb, math.exp(t_[1])) / p_any(math.exp(t_[0]) * gb, math.exp(t_[1])) for t_ in sq_th])
    pany_sq_lt500 = np.array([p_any(math.exp(t_[0]) * gb[0], math.exp(t_[1])) for t_ in sq_th])
    log("thinF sampling uncertainty (two-stage bootstrap, B=%d): SE at half the pool %.3f-%.3f over industries x band centres (band means %s; 95%% at <500K %s, "
        "at $5M+ %s); at a quarter %.3f-%.3f. Single-quarter fits: half-pool thinF at band means <500K %.3f-%.3f, $5M+ %.3f-%.3f, while P(any offer | typical, <500K) "
        "ranges %.2f-%.2f: the zero class is not identified, the ratio is."
        % (B_BOOT, thin_se_half.min(), thin_se_half.max(), np.round(th_bm.std(0), 3).tolist(), np.round(np.percentile(th_bm[:, 0], [2.5, 97.5]), 3).tolist(),
           np.round(np.percentile(th_bm[:, 4], [2.5, 97.5]), 3).tolist(), thin_se_quart.min(), thin_se_quart.max(), th_sq[:, 0].min(), th_sq[:, 0].max(),
           th_sq[:, 4].min(), th_sq[:, 4].max(), pany_sq_lt500.min(), pany_sq_lt500.max()))
    # the cap at 1: the fitted NB alone would keep raising P(any offer) above a typical pool
    cap2 = p_any(2 * c_hat * G, r_hat) / p_any(c_hat * G, r_hat)
    el_new = (c_hat * G) * (1 + c_hat * G / r_hat) ** (-r_hat - 1) / p_any(c_hat * G, r_hat)
    n_old_ = 0.34 * G; el_old = n_old_ * np.exp(-n_old_) / (1 - np.exp(-n_old_))
    log("cap at 1: the fitted NB alone implies P(any offer) at twice the typical pool is %.2f-%.2f x the typical pool's; elasticity of thinF to buyers just "
        "below typical %.2f-%.2f (old Poisson %.2f-%.2f); above typical 0 in both" % (cap2.min(), cap2.max(), el_new.min(), el_new.max(), el_old.min(), el_old.max()))
    REV3 = dict(sq_c=np.exp(sq_th[:, 0]).tolist(), sq_r=np.exp(sq_th[:, 1]).tolist(), sq_se=sq_se.tolist(), sq_Q=sq_Q, sq_Q_p=sq_Q_p, phi_lo=phi_lo, phi_hi=phi_hi, phi_boot=phi_boot,
                QL=QL, ser=SER, wat=WAT, thin_se_half=[float(thin_se_half.min()), float(thin_se_half.max())],
                thin_se_quart=[float(thin_se_quart.min()), float(thin_se_quart.max())], thin_se_half_bandmeans=th_bm.std(0).tolist(),
                thin_sq_half_bandmeans=[[float(th_sq[:, i].min()), float(th_sq[:, i].max())] for i in range(5)], pany_sq_lt500=[float(pany_sq_lt500.min()), float(pany_sq_lt500.max())],
                cap2=[float(cap2.min()), float(cap2.max())], el_new=[float(el_new.min()), float(el_new.max())], el_old=[float(el_old.min()), float(el_old.max())],
                n_rc_total=float(o.groupby(["period", "band"]).n_rc.first().sum()), n_closed_total=float(o.groupby(["period", "band"]).n.first().sum()),
                n_rc_consistent=int(((o.groupby(["period", "band"]).n_rc.first() == o.groupby(["period", "band"]).n.first()) & o.groupby(["period", "band"]).n_rc_feasible.first()).sum()),
                n_rc_infeasible=int((~o.groupby(["period", "band"]).n_rc_feasible.first()).sum()), n_spec_nb=n_spec_nb, q_opt_nb=q_opt_nb, q_opt_pln=q_opt_pln)
    res["b_rev2"] = dict(spec=SPEC.to_dict("list"), selection=SEL.to_dict("list"), beta=BETA.to_dict("list"), pln=dict(c=float(pln_row.c), c_se=pln_c_se,
                         s=float(pln_row.dispersion), nll=float(pln_row.nll), loqo=pln_loqo), q_min_pln_pepperdine=q_min_pln,
                         thin5=dict(rec=thin5_rec, bars=thin5_bar, m2=thin5_m2), calib=dict(model=zt_ind_mean.tolist(), m2=m2_zt.tolist(), m2_se=m2_zt_se.tolist()))
    res["b_rev3"] = REV3

    res["b"] = dict(constrained=dict(c=c_con, r=r_con, lr=lr_con), c=c_hat, c_se=c_hat * c_se_log, c_ci=list(c_ci), r=r_hat, r_se=r_hat * r_se_log, r_ci=list(r_ci),
                    jackknife_se_log=list(jk_se), tests=tests, tests_p=tests_p, band=btab.to_dict("list"), loqo=cvs.to_dict(),
                    temporal_holdout=hold, tau2=tau2, cochranQ=Q)

    # ---------------- (a) kappa ------------------------------------------------------------------
    ENG = round(c_hat, 3)
    H_NEW = CUR["COMP_H"] * ENG / CUR["ENG_SHARE"]          # offset rescaled with the engaged count (see header)
    rp = pd.read_csv(os.path.join(AGG, "ibba_mp_realized_to_ask_panel.csv"))
    rp["y"] = rp.pct_of_ask_or_benchmark / 100
    avq = pd.read_csv(os.path.join(AGG, "ibba_mp_offers_avg_panel.csv"))
    avq = avq[avq.period.str.contains("Q")]
    pan = rp.merge(avq[["period", "band", "avg_offers_per_deal"]], on=["period", "band"]).rename(columns={"avg_offers_per_deal": "m"})
    pan["src"] = "avg"
    # sensitivity panel: add histogram-implied means for quarters with realized/ask but no average-offers bar
    hm = o.groupby(["period", "band"]).apply(lambda x: (np.where(x.open, np.nan, x.k) * x.w).sum() / x.w.sum()).rename("m_closed_cells")
    hq = []
    for (q, bnd), x in o.groupby(["period", "band"]):
        if ((pan.period == q) & (pan.band == bnd)).any():
            continue
        bi = BANDS.index(bnd)
        mu_c, r_c = mu2[bi], r2[bi]
        # conditional mean of the open cell under the band's ZTNB
        kk = int(x[x.open].k.iloc[0]) if x.open.any() else None
        if kk is not None:
            ks = np.arange(kk, 400); pk = stats.nbinom.pmf(ks, r_c, nb_p(mu_c, r_c)); open_mean = (ks * pk).sum() / pk.sum()
        else:
            open_mean = 0
        m = ((np.where(x.open, open_mean, x.k)) * x.w).sum() / x.w.sum()
        yv = rp[(rp.period == q) & (rp.band == bnd)].y
        if len(yv):
            hq.append(dict(period=q, band=bnd, y=float(yv.iloc[0]), m=m, src="hist"))
    pan_s = pd.concat([pan[["period", "band", "y", "m", "src"]], pd.DataFrame(hq)], ignore_index=True)
    ncl = pd.read_csv(os.path.join(AGG, "ibba_mp_band_n_closed.csv"))
    nbar = ncl.groupby("band").n_closed.mean()
    ncl_map = {(r_.period, r_.band): r_.n_closed for r_ in ncl.itertuples()}

    def build(df):
        df = df.copy()
        bi = df.band.map({b: i for i, b in enumerate(BANDS)}).values
        df["bi"] = bi
        df["n"] = [ncl_map.get((p, b), nbar[b]) for p, b in zip(df.period, df.band)]
        df["mu"] = [mu_from_ztmean(m, r2[i]) for m, i in zip(df.m, bi)]
        df["mu_bar"] = df.groupby(["band", "src"]).mu.transform("mean")
        df["s"] = pass_b[bi]
        df["x"] = df.s * np.log((H_NEW + df.mu) / (H_NEW + df.mu_bar))
        # sampling variance of x from the sampling variance of the band-quarter mean of offers
        dmu_dm = np.array([1 / ((zt_mean(u * 1.001, r2[i]) - zt_mean(u * 0.999, r2[i])) / (0.002 * u)) for u, i in zip(df.mu, bi)])
        var_m = np.array([zt_var(mu2[i], r2[i]) for i in bi]) / df.n.values
        df["var_x"] = (df.s / (H_NEW + df.mu)) ** 2 * dmu_dm ** 2 * var_m
        df["y_dm"] = df.y - df.groupby(["band", "src"]).y.transform("mean")
        df["x_dm"] = df.x - df.groupby(["band", "src"]).x.transform("mean")
        df["m_dm"] = df.m - df.groupby(["band", "src"]).m.transform("mean")
        return df

    def kappa_fit(df):
        xd, yd = df.x_dm.values, df.y_dm.values
        ols = np.sum(xd * yd) / np.sum(xd * xd)
        # reliability of the within-band regressor: 1 - E[sampling var] / var_within (pooled over bands)
        dof = len(df) - df.groupby(["band", "src"]).ngroups
        var_within = np.sum(xd * xd) / max(dof, 1)
        R = max(0.05, 1 - df.var_x.mean() / var_within)
        return ols, ols / R, R

    def slope_offer(df):
        return np.sum(df.m_dm * df.y_dm) / np.sum(df.m_dm ** 2)

    out_k = {}
    for name, df0 in [("main_avg_series_8q", pan[["period", "band", "y", "m", "src"]]), ("plus_histogram_quarters", pan_s)]:
        df = build(df0)
        k_ols, k_rc, R = kappa_fit(df)
        b_off = slope_offer(df)
        qlist = sorted(df.period.unique())
        bk = []
        for _ in range(2000):
            pick = RNG.choice(qlist, len(qlist), replace=True)
            dd = pd.concat([df[df.period == q].assign(period="%s_%d" % (q, j)) for j, q in enumerate(pick)], ignore_index=True)
            dd["y_dm"] = dd.y - dd.groupby(["band", "src"]).y.transform("mean")
            dd["x_dm"] = dd.x - dd.groupby(["band", "src"]).x.transform("mean")
            dd["m_dm"] = dd.m - dd.groupby(["band", "src"]).m.transform("mean")
            if np.sum(dd.x_dm ** 2) < 1e-12:
                continue
            a1, a2, _ = kappa_fit(dd)
            bk.append((a1, a2, slope_offer(dd)))
        bk = np.array(bk)
        # analytic cluster-robust SE for the OLS within estimator (quarters as clusters)
        X = df.x_dm.values; Y = df.y_dm.values; e = Y - k_ols * X
        meat = sum((np.sum(X[df.period.values == q] * e[df.period.values == q])) ** 2 for q in qlist)
        se_cl = math.sqrt(meat) / np.sum(X * X) * math.sqrt(len(qlist) / (len(qlist) - 1))
        se_ols = max(se_cl, bk[:, 0].std())
        ci_ols = np.percentile(bk[:, 0], [2.5, 97.5])
        out_k[name] = dict(n=len(df), quarters=len(qlist), slope_per_offer=b_off, slope_per_offer_se_boot=bk[:, 2].std(),
                           kappa_ols=k_ols, kappa_ols_se_cluster=se_cl, kappa_ols_se_boot=bk[:, 0].std(), kappa_ols_ci95_boot=list(ci_ols),
                           reliability=R, kappa_eiv=k_rc, kappa_eiv_se=se_ols / R,
                           kappa_eiv_ci95=[k_rc - 1.96 * se_ols / R, k_rc + 1.96 * se_ols / R],
                           kappa_eiv_boot_median=float(np.median(bk[:, 1])), kappa_eiv_boot_iqr=list(np.percentile(bk[:, 1], [25, 75])),
                           kappa_eiv_if_R_0p3=k_ols / 0.3, kappa_eiv_se_if_R_0p3=se_ols / 0.3)
        df.to_csv(os.path.join(OUT, "kappa_panel_%s.csv" % name), index=False)
        log("\n(a) kappa [%s]: n=%d (%d quarters); slope per offer %.4f (boot SE %.4f); kappa OLS-within %.3f (cluster SE %.3f, boot SE %.3f, boot 95%% %s); reliability %.2f; EIV kappa %.3f (SE %.3f, 95%% %s); if reliability were 0.3: %.3f (SE %.3f)"
            % (name, len(df), len(qlist), b_off, bk[:, 2].std(), k_ols, se_cl, bk[:, 0].std(), np.round(ci_ols, 3), R, k_rc, se_ols / R,
               np.round([k_rc - 1.96 * se_ols / R, k_rc + 1.96 * se_ols / R], 3), k_ols / 0.3, se_ols / 0.3))

    # revision 2: disclosure and robustness of the within-band slope
    dfk = build(pan[["period", "band", "y", "m", "src"]])
    n_imp = int(sum((p_, b_) not in ncl_map for p_, b_ in zip(dfk.period, dfk.band)))
    imp_periods = sorted({p_ for p_, b_ in zip(dfk.period, dfk.band) if (p_, b_) not in ncl_map})
    grp = pd.factorize(dfk.period)[0]

    def fe_slope(df_, var, quarter_fe):
        cols = ["band", "period"] if quarter_fe else ["band"]
        X_ = pd.concat([df_[[var]].reset_index(drop=True), pd.get_dummies(df_[cols].reset_index(drop=True), drop_first=True, dtype=float)], axis=1)
        f_ = sm.OLS(df_.y.reset_index(drop=True), sm.add_constant(X_)).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df_.period)[0]})
        return float(f_.params[var]), float(f_.bse[var])
    kfe = {"band_fe_per_offer": fe_slope(dfk, "m", False), "two_way_fe_per_offer": fe_slope(dfk, "m", True),
           "band_fe_kappa_units": fe_slope(dfk, "x", False), "two_way_fe_kappa_units": fe_slope(dfk, "x", True),
           "main_street_bands_band_fe_per_offer": fe_slope(dfk[dfk.band.isin(BANDS[:3])], "m", False),
           "main_street_bands_band_fe_kappa_units": fe_slope(dfk[dfk.band.isin(BANDS[:3])], "x", False)}
    kfe["two_way_fe_kappa_units_eiv"] = (kfe["two_way_fe_kappa_units"][0] / out_k["main_avg_series_8q"]["reliability"],
                                         kfe["two_way_fe_kappa_units"][1] / out_k["main_avg_series_8q"]["reliability"])
    log("kappa robustness (quarter-cluster SEs, %d clusters): %s" % (len(set(grp)), {k_: (round(v[0], 4), round(v[1], 4)) for k_, v in kfe.items()}))
    log("kappa EIV: n_closed missing for %d of %d band-quarters (%s); each imputed with its band's mean n_closed over %s"
        % (n_imp, len(dfk), ", ".join(imp_periods), "-".join([str(ncl.period.min()), str(ncl.period.max())])))
    # how much the imputed sample sizes matter: reliability and EIV kappa if every n were half or double
    xd_ = dfk.x_dm.values; dof_ = len(dfk) - dfk.band.nunique(); vw_ = np.sum(xd_ * xd_) / dof_
    k_ols8 = out_k["main_avg_series_8q"]["kappa_ols"]; se_ols8 = out_k["main_avg_series_8q"]["kappa_eiv_se"] * out_k["main_avg_series_8q"]["reliability"]
    n_sens = {}
    for sc in (0.5, 1.0, 2.0):
        R_ = max(0.05, 1 - dfk.var_x.mean() / sc / vw_)
        n_sens[sc] = dict(reliability=R_, kappa_eiv=k_ols8 / R_, se=se_ols8 / R_)
    log("kappa EIV if every band-quarter n were x0.5 / x1 / x2:", {k_: {a: round(b, 3) for a, b in v.items()} for k_, v in n_sens.items()})
    kfe["n_sensitivity"] = n_sens
    kfe["n_imputed"] = n_imp; kfe["n_rows"] = len(dfk); kfe["imputed_periods"] = imp_periods

    # validation: leave-one-quarter-out and temporal holdout prediction of within-band deviations
    df = build(pan[["period", "band", "y", "m", "src"]])
    qlist = sorted(df.period.unique())
    mse = {"kappa_hat": [], "kappa_ols": [], "kappa_0": [], "kappa_0.03": []}
    for q in qlist:
        tr = df[df.period != q].copy(); te = df[df.period == q].copy()
        for d_ in (tr,):
            d_["y_dm"] = d_.y - d_.groupby("band").y.transform("mean"); d_["x_dm"] = d_.x - d_.groupby("band").x.transform("mean")
        k_o, k_tr, _ = kappa_fit(tr)
        ybar = tr.groupby("band").y.mean(); xbar = tr.groupby("band").x.mean()
        for nm, kk in [("kappa_hat", k_tr), ("kappa_ols", k_o), ("kappa_0", 0.0), ("kappa_0.03", 0.03)]:
            pred = te.band.map(ybar) + kk * (te.x - te.band.map(xbar))
            mse[nm].append(np.mean((te.y - pred) ** 2))
    loqo_k = {k: float(np.mean(v)) for k, v in mse.items()}
    tr = df[df.period <= "2024Q4"].copy(); te = df[df.period > "2024Q4"].copy()
    tr["y_dm"] = tr.y - tr.groupby("band").y.transform("mean"); tr["x_dm"] = tr.x - tr.groupby("band").x.transform("mean")
    k_tro, k_tr, _ = kappa_fit(tr)
    ybar = tr.groupby("band").y.mean(); xbar = tr.groupby("band").x.mean()
    tho = {}
    for nm, kk in [("kappa_hat_train", k_tr), ("kappa_ols_train", k_tro), ("kappa_0", 0.0), ("kappa_0.03", 0.03)]:
        pred = te.band.map(ybar) + kk * (te.x - te.band.map(xbar))
        tho[nm] = float(np.mean((te.y - pred) ** 2))
    log("kappa LOQO MSE x1e4:", {k: round(v * 1e4, 3) for k, v in loqo_k.items()}, " temporal holdout (train<=2024Q4, test 2025-26) MSE x1e4:",
        {k: round(v * 1e4, 3) for k, v in tho.items()}, " kappa trained<=2024Q4 = %.3f" % k_tr)

    # pooled cross-band slope (confounded upper bound) mapped to kappa units
    xg = df.s * np.log((H_NEW + df.mu) / (H_NEW + df.mu.mean()))
    Xp = sm.add_constant(xg.values); fp = sm.OLS(df.y.values, Xp).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.period)[0]})
    log("pooled cross-band (no FE) kappa-units slope %.3f (cluster SE %.3f) - confounded with size and the ask/benchmark denominator: upper bound only" % (fp.params[1], fp.bse[1]))
    # what a kappa would have to be to explain the whole cross-band realised/ask gradient
    # Flippa analogs
    fl = pd.read_csv(os.path.join(FLIPPA, "flippa2026_recently_sold.csv"))
    a = fl[(fl.sale_method == "auction") & (fl.bid_count > 0) & (fl.final_bid_usd > 0) & (fl.monthly_profit_usd_card > 0) & (fl.monthly_revenue_usd_card > 0)].copy()
    a["lp"] = np.log(a.final_bid_usd); a["lb"] = np.log(a.bid_count); a["lpr"] = np.log(12 * a.monthly_profit_usd_card)
    a["lrv"] = np.log(12 * a.monthly_revenue_usd_card); a["lage"] = np.log(a.age_years)
    a["typ"] = a.type.where(a.type.map(a.type.value_counts()) >= 10, "other")
    Xf = pd.get_dummies(a[["lb", "lpr", "lrv", "lage", "verified_listing", "typ"]], columns=["typ"], drop_first=True, dtype=float)
    Xf = sm.add_constant(Xf); mf_ = sm.OLS(a.lp, Xf).fit(cov_type="HC1")
    # 10-fold CV: out-of-sample R2 with vs without log bids
    idx = RNG.permutation(len(a)); folds = np.array_split(idx, 10); sse1 = sse0 = sst = 0.0
    for fo in folds:
        trn = np.setdiff1d(idx, fo)
        m1 = sm.OLS(a.lp.values[trn], Xf.values[trn]).fit(); m0 = sm.OLS(a.lp.values[trn], Xf.drop(columns="lb").values[trn]).fit()
        sse1 += np.sum((a.lp.values[fo] - m1.predict(Xf.values[fo])) ** 2)
        sse0 += np.sum((a.lp.values[fo] - m0.predict(Xf.drop(columns="lb").values[fo])) ** 2)
        sst += np.sum((a.lp.values[fo] - a.lp.values[trn].mean()) ** 2)
    f19 = pd.read_csv(os.path.join(FLIPPA, "flippa2019_ended_auctions.csv"))
    f19 = f19[(f19.sold == 1) & (f19.bid_count > 0) & (f19.bin_price_usd > 0)].copy()
    m19 = sm.OLS(np.log(f19.current_price_usd / f19.bin_price_usd), sm.add_constant(np.c_[np.log(f19.bid_count), np.log(f19.bin_price_usd)])).fit(cov_type="HC1")
    flip = dict(n_2026=len(a), median_price_2026=float(a.final_bid_usd.median()), coef_log_bids=float(mf_.params["lb"]), se=float(mf_.bse["lb"]),
                cv_r2_with_bids=1 - sse1 / sst, cv_r2_without=1 - sse0 / sst,
                n_2019=len(f19), coef_log_bids_price_over_BIN_2019=float(np.asarray(m19.params)[1]), se_2019=float(np.asarray(m19.bse)[1]))
    log("Flippa auctions 2026: ln(price) on ln(bids) + fundamentals: %.3f (HC1 SE %.3f), n=%d, median price $%.0f; 10-fold CV R2 %.3f with vs %.3f without bids; 2019 ln(price/BIN) on ln(bids): %.3f (SE %.3f), n=%d"
        % (flip["coef_log_bids"], flip["se"], flip["n_2026"], flip["median_price_2026"], flip["cv_r2_with_bids"], flip["cv_r2_without"], flip["coef_log_bids_price_over_BIN_2019"], flip["se_2019"], flip["n_2019"]))

    # posterior for kappa: prior N(0.03, 0.03^2) (the current judgment, 'small, positive, could be zero'),
    # IBBA EIV likelihood N(kappa_eiv, se^2), truncated at 0 (more buyers may never lower proceeds)
    km = out_k["main_avg_series_8q"]
    pm, ps = CUR["COMP_K"], 0.03
    lm, ls = km["kappa_eiv"], km["kappa_eiv_se"]
    post_v = 1 / (1 / ps ** 2 + 1 / ls ** 2); post_m = post_v * (pm / ps ** 2 + lm / ls ** 2); post_s = math.sqrt(post_v)
    a_ = (0 - post_m) / post_s
    tmean = post_m + post_s * stats.norm.pdf(a_) / stats.norm.sf(a_)
    tq = [post_m + post_s * stats.norm.ppf(stats.norm.cdf(a_) + p * stats.norm.sf(a_)) for p in (0.025, 0.5, 0.975)]
    log("kappa posterior (prior N(.03,.03^2), IBBA EIV likelihood, truncated at 0): mean %.4f, median %.4f, 95%% [%.4f, %.4f]; data weight %.3f"
        % (tmean, tq[1], tq[0], tq[2], post_v / ls ** 2))
    res["a"] = dict(panels=out_k, robustness=kfe, loqo_mse=loqo_k, temporal_holdout_mse=tho, kappa_train_le_2024=k_tr, pooled_crossband_kappa_units=float(fp.params[1]),
                    pooled_crossband_se=float(fp.bse[1]), flippa=flip, posterior=dict(mean=tmean, median=tq[1], lo=tq[0], hi=tq[2], data_weight=post_v / ls ** 2),
                    H_NEW=H_NEW)

    # ---------------- (c) buyer-type multiples ---------------------------------------------------
    pp = pd.read_csv(os.path.join(AGG, "pepperdine_pcm_figures.csv"))
    f13 = pp[pp.figure.str.startswith("Fig 13")].value.values.astype(float)       # none,0-10,11-20,21-30,31-40,41-50,>50 (% of 120)
    N13 = 120
    cnt = f13 / f13.sum() * N13
    edges = np.array([0, 10.5, 20.5, 30.5, 40.5, 50.5, np.inf])

    def hurdle_probs(th):
        p0 = special.expit(th[0]); m, s = th[1], math.exp(th[2])
        cdf = stats.norm.cdf((np.log(edges[1:-1]) - m) / s)
        cells = np.diff(np.r_[0, cdf, 1])
        return np.r_[p0, (1 - p0) * cells]

    def hurdle_fit(c):
        f = optimize.minimize(lambda th: -np.sum(c * np.log(np.clip(hurdle_probs(th), 1e-300, 1))), [-1, math.log(15), 0], method="Nelder-Mead",
                              options=dict(xatol=1e-8, fatol=1e-10, maxiter=20000))
        return f.x

    def premia(th, cap=100):
        p0 = special.expit(th[0]); m, s = th[1], math.exp(th[2])
        # E[min(X, cap)] for lognormal X
        lc = math.log(cap)
        e_cap = math.exp(m + s * s / 2) * stats.norm.cdf((lc - m - s * s) / s) + cap * stats.norm.sf((lc - m) / s)
        mean_cap = (1 - p0) * e_cap
        # median of the mixture
        tgt = 0.5
        med = 0.0 if p0 >= tgt else math.exp(m + s * stats.norm.ppf((tgt - p0) / (1 - p0)))
        return dict(p0=p0, mean_cap100=mean_cap, median=med, mean_uncapped=(1 - p0) * math.exp(m + s * s / 2))

    th13 = hurdle_fit(cnt); pr13 = premia(th13)
    g2_13 = float(2 * np.sum(cnt * np.log((cnt / cnt.sum()) / hurdle_probs(th13))))
    pr13["G2"] = g2_13; pr13["G2_p"] = float(stats.chi2.sf(g2_13, 3))
    log("Pepperdine 2016 hurdle-lognormal goodness of fit: G2 = %.2f on 3 df (p = %.3f); fitted cells %s vs observed %s"
        % (g2_13, pr13["G2_p"], np.round(100 * hurdle_probs(th13), 1).tolist(), np.round(100 * cnt / cnt.sum(), 1).tolist()))
    bt = []
    for _ in range(2000):
        cb_ = RNG.multinomial(N13, hurdle_probs(th13))
        bt.append(premia(hurdle_fit(cb_)))
    bt = pd.DataFrame(bt)
    # sensitivity: the open top bucket placed at exactly 50% / 75% / 100% (bucket midpoints elsewhere)
    mids = np.array([0, 5, 15.5, 25.5, 35.5, 45.5])
    sens = {tb: float(np.sum(f13 / f13.sum() * np.r_[mids, tb])) for tb in (50, 75, 100)}
    log("\n(c) Pepperdine 2016 strategic premium over financial (n=120 IB respondents): P(none)=%.3f, capped mean %.2f%% (SE %.2f), median %.2f%% (SE %.2f), uncapped mean %.1f%%; bucket-midpoint means %s"
        % (pr13["p0"], pr13["mean_cap100"], bt.mean_cap100.std(), pr13["median"], bt["median"].std(), pr13["mean_uncapped"], {k: round(v, 2) for k, v in sens.items()}))
    # Pepperdine 2025 (secondary quote, n unknown; assume 100 for an indicative SE): 51% none, 33% 1-20%, 16% >20%
    edges25 = np.array([0, 20.5, np.inf])
    c25 = np.array([51, 33, 16.0])

    def h25(th):
        p0 = special.expit(th[0]); m, s = th[1], 0.8           # shape fixed at a lognormal sd of 0.8 (only two positive cells)
        c = stats.norm.cdf((math.log(20.5) - m) / s)
        return np.array([p0, (1 - p0) * c, (1 - p0) * (1 - c)])

    f25 = optimize.minimize(lambda th: -np.sum(c25 * np.log(np.clip(h25(th), 1e-300, 1))), [0, math.log(12)], method="Nelder-Mead").x
    p0_25 = special.expit(f25[0]); mean25 = (1 - p0_25) * math.exp(f25[1] + 0.32)
    log("Pepperdine 2025 (secondary quote): P(none)=%.2f, implied mean premium ~%.1f%% (shape assumed; indicative only)" % (p0_25, mean25))

    # GF Data add-on vs platform (log ratios), random effects over the reported periods
    gf = pd.read_csv(os.path.join(AGG, "gfdata_size_buyer_type_multiples.csv"))
    lr_ = [math.log(5.7 / 4.5),                             # 2024Q1-Q3, TEV $1-10M: add-on 5.7x vs platform 4.5x
           math.log((7.1 + 0.15) / (7.1 - 0.15)),           # 2025H1 all TEV: add-on minus platform +0.3 turns around ~7.1x
           math.log((7.1 - 0.55) / (7.1 + 0.55)),           # 2026Q1: platform minus add-on 1.1 turns
           math.log((7.1 + 0.6) / (7.1 - 0.6))]             # 2026Q2: add-on minus platform 1.2 turns
    lr_ = np.array(lr_)
    gf_mean, gf_se = lr_.mean(), lr_.std(ddof=1) / math.sqrt(len(lr_))
    log("GF Data add-on/platform multiple: exp(mean log ratio) = %.3f (SE of log %.3f, t3 95%% %s), periods=%d"
        % (math.exp(gf_mean), gf_se, np.round(np.exp(gf_mean + np.array([-1, 1]) * stats.t.ppf(.975, 3) * gf_se), 3), len(lr_)))
    # Stanford 2024 search funds (median 7.0x, 2022-23, median price $14.4M) vs GF Data $10-25M TEV (6.0x 2023, 6.4x 2024Q1-Q3)
    # quality-adjusted with GF's above-average-performer premium (2023: +27%, share 48%; 2024: +15%, share 39%)
    gfq = [6.0 * 1.27 / (1 + 0.27 * 0.48), 6.4 * 1.15 / (1 + 0.15 * 0.39)]
    sf_ratio = [7.0 / x for x in gfq]
    log("Stanford search-fund median multiple vs GF Data same-size AAFP-adjusted mean: ratios %s (median vs mean: indicative, SE ~0.10 by assumption)" % np.round(sf_ratio, 3))

    # the model's implied premia at lower-middle-market values (sizeFit ~ 1 for strategic and financial buyers)
    L = P[P.V.isin(LMM_V)].copy()
    rows = []
    for r_ in L.itertuples():
        B = {b["k"]: b for b in r_.buyers}
        Vbase_q = r_.Vm                                        # quality-positioned value (median business: qf=1)
        S = 0.5 * (B["str"]["Vj"] + B["adj"]["Vj"])
        F = 0.64 * B["pep"]["Vj"] + 0.36 * B["add"]["Vj"]       # Pepperdine 2016 Fig 14: 64% platforms, 36% follow-ons
        rows.append(dict(V=r_.V, ind=r_.ind, prem_strat_vs_fin=S / F - 1, add_vs_pep=B["add"]["Vj"] / B["pep"]["Vj"],
                         eta_vs_pep=B["eta"]["Vj"] / B["pep"]["Vj"], ind_vs_pep=B["ind"]["Vj"] / B["pep"]["Vj"],
                         sizefit_str=B["str"]["sizeFit"], sizefit_pep=B["pep"]["sizeFit"], sizefit_add=B["add"]["sizeFit"],
                         syn_part_str=0.38 * B["str"]["S"] / Vbase_q, syn_part_pep=0.38 * B["pep"]["S"] / Vbase_q))
    LM = pd.DataFrame(rows)
    LM.to_csv(os.path.join(OUT, "model_buyer_premia_lmm.csv"), index=False)
    mp = LM.groupby("V").mean(numeric_only=True)
    log("model-implied premia at LMM values (mean over 16 industries):")
    log(mp[["prem_strat_vs_fin", "add_vs_pep", "eta_vs_pep", "ind_vs_pep", "sizefit_str", "sizefit_pep", "syn_part_str"]].round(3).to_string())
    # full-presence premia (sizeFit = 1 for both groups): what a strategic buyer pays relative to a financial
    # buyer when both bid, which is what Pepperdine's respondents report. Vj/(ern*M) = mf + min(PHI*syn*synE/ern, .40)
    PHI = 0.38
    MF = {"str": 1.18, "adj": 1.14, "pep": 1.06, "add": 1.12, "eta": 0.98, "ind": 0.90, "fo": 1.02, "mbo": 0.86}
    SYN = {"str": 1.00, "adj": 0.70, "pep": 0.10, "add": 0.62, "eta": 0.04, "ind": 0.0, "fo": 0.09, "mbo": 0.0}
    Lf = L[["V", "ind", "ern", "synE"]].copy(); Lf["x"] = Lf.synE / Lf.ern

    def full(k, x, theta=1.0):
        mf = 1 + theta * (MF[k] - 1) if k in ("str", "adj") else MF[k]
        return mf + np.minimum(PHI * SYN[k] * x, 0.40)

    def prem_full(theta=1.0):
        S = 0.5 * (full("str", Lf.x, theta) + full("adj", Lf.x, theta))
        F = 0.64 * full("pep", Lf.x) + 0.36 * full("add", Lf.x)
        return float(np.mean(S / F - 1))
    pf1 = prem_full(1.0)
    addpep_full = float(np.mean(full("add", Lf.x) / full("pep", Lf.x)))
    etapep_full = float(np.mean(full("eta", Lf.x) / full("pep", Lf.x)))
    indpep_full = float(np.mean(full("ind", Lf.x) / full("pep", Lf.x)))
    syn_str = float(np.mean(np.minimum(PHI * Lf.x, .4)))
    log("full-presence (sizeFit=1) model ratios at LMM values: strategic/financial premium %.3f (of which synergy for 'str' %.3f of value), add-on/platform %.3f, search fund/platform %.3f, individual/platform %.3f"
        % (pf1, syn_str, addpep_full, etapep_full, indpep_full))
    # Pepperdine 2025 secondary quote: indicative SE by parametric bootstrap at an assumed n=100 and shape sd in {0.5,0.8,1.2}
    m25 = []
    for sh_ in (0.5, 0.8, 1.2):
        def h25s(th, sh_=sh_):
            p0 = special.expit(th[0]); c = stats.norm.cdf((math.log(20.5) - th[1]) / sh_)
            return np.array([p0, (1 - p0) * c, (1 - p0) * (1 - c)])
        for _ in range(300):
            cc = RNG.multinomial(100, c25 / c25.sum())
            ff = optimize.minimize(lambda th: -np.sum(cc * np.log(np.clip(h25s(th), 1e-300, 1))), [0, math.log(12)], method="Nelder-Mead").x
            pz = special.expit(ff[0]); m25.append((1 - pz) * min(math.exp(ff[1] + sh_ ** 2 / 2), 100))
    se25 = float(np.std(m25)); mean25b = float(np.mean(m25))
    # random-effects pooling (DerSimonian-Laird) of the two vintages, in premium points
    yv = np.array([pr13["mean_cap100"], mean25b]); sv = np.array([bt.mean_cap100.std(), se25])
    wv = 1 / sv ** 2; ybar = np.sum(wv * yv) / wv.sum(); Qv = np.sum(wv * (yv - ybar) ** 2)
    tau2v = max(0.0, (Qv - 1) / (wv.sum() - (wv ** 2).sum() / wv.sum()))
    wr = 1 / (sv ** 2 + tau2v); re_mean = np.sum(wr * yv) / wr.sum(); re_se = math.sqrt(1 / wr.sum())
    log("Pepperdine vintages: 2016 %.2f (SE %.2f), 2025 secondary %.2f (SE %.2f, assumed n=100 and shape); DL tau=%.2f; RE pooled %.2f (SE %.2f)"
        % (yv[0], sv[0], yv[1], sv[1], math.sqrt(tau2v), re_mean, re_se))
    # shrink toward the model's full-presence premium: prior N(pf1, (0.5*pf1)^2)
    pvv = 1 / (1 / (0.5 * pf1) ** 2 + 1 / (re_se / 100) ** 2)
    tgt = pvv * (pf1 / (0.5 * pf1) ** 2 + (re_mean / 100) / (re_se / 100) ** 2); tgt_se = math.sqrt(pvv)
    theta = optimize.brentq(lambda t: prem_full(t) - tgt, 0.0, 5.0)
    dth = (optimize.brentq(lambda t: prem_full(t) - (tgt + 1e-4), 0, 5) - theta) / 1e-4
    theta_2016 = optimize.brentq(lambda t: prem_full(t) - pr13["mean_cap100"] / 100, 0.0, 5.0)
    theta_2025 = optimize.brentq(lambda t: prem_full(t) - mean25b / 100, 0.0, 5.0)
    theta_re = optimize.brentq(lambda t: prem_full(t) - re_mean / 100, 0.0, 5.0)
    log("strategic premium target (RE pooled, shrunk to model): %.4f (SE %.4f) vs model %.4f -> scale on strategic (mf-1): theta=%.3f (SE %.3f); "
        "2016-only theta=%.3f (str/adj %.2f/%.2f); 2025-only theta=%.3f (str/adj %.2f/%.2f); RE-pooled unshrunk theta=%.3f. CONSISTENCY CHECK ONLY: mf unchanged"
        % (tgt, tgt_se, pf1, theta, abs(dth) * tgt_se, theta_2016, 1 + .18 * theta_2016, 1 + .14 * theta_2016, theta_2025, 1 + .18 * theta_2025,
           1 + .14 * theta_2025, theta_re))
    model_prem = float(LM[LM.V >= 8e6].prem_strat_vs_fin.mean())
    model_prem_sd_ind = float(LM[LM.V >= 8e6].groupby("ind").prem_strat_vs_fin.mean().std())
    # shrink the data toward the model: prior N(model, (0.5*model)^2); data N(capped mean, SE) - both in premium points
    dmean, dse = pr13["mean_cap100"] / 100, bt.mean_cap100.std() / 100
    pv = 1 / (1 / (0.5 * model_prem) ** 2 + 1 / dse ** 2)
    target = pv * (model_prem / (0.5 * model_prem) ** 2 + dmean / dse ** 2)
    log("[display premium, sizeFit-weighted; not used for the fit] strategic-vs-financial premium: model %.3f (sd over industries %.3f) vs Pepperdine capped mean %.3f (SE %.3f): z=%.2f; shrunk target %.3f"
        % (model_prem, model_prem_sd_ind, dmean, dse, (model_prem - dmean) / math.sqrt(dse ** 2), target))
    res["c"] = dict(pepperdine2016=dict(G2=pr13["G2"], G2_p=pr13["G2_p"], p0=pr13["p0"], mean_cap100=pr13["mean_cap100"], mean_cap100_se=bt.mean_cap100.std(), median=pr13["median"],
                                        median_se=bt["median"].std(), mean_uncapped=pr13["mean_uncapped"], bucket_midpoint_means=sens),
                    pepperdine2025_secondary=dict(p0=p0_25, mean=mean25), gf_addon_over_platform=dict(ratio=math.exp(gf_mean), se_log=gf_se),
                    stanford_vs_gf=sf_ratio, model=dict(prem_strat_vs_fin=model_prem, sd_over_industries=model_prem_sd_ind,
                                                        add_vs_pep=float(LM[LM.V >= 8e6].add_vs_pep.mean()), eta_vs_pep=float(LM[LM.V >= 8e6].eta_vs_pep.mean())),
                    shrunk_target=target, full_presence=dict(prem=pf1, add_vs_pep=addpep_full, eta_vs_pep=etapep_full, ind_vs_pep=indpep_full,
                    syn_part_str=syn_str), pepperdine2025_boot=dict(mean=mean25b, se=se25), re_pooled=dict(mean=re_mean, se=re_se, tau=math.sqrt(tau2v)),
                    target_full=tgt, target_full_se=tgt_se, theta=theta, theta_se=abs(dth) * tgt_se, theta_2016_only=theta_2016,
                    theta_2025_only=theta_2025, theta_re_unshrunk=theta_re, display_premium_z=(model_prem - dmean) / dse)

    # ---------------- recommended change, applied through the harness as exact source edits -----
    # Revision 2: BUYERS str/adj mf are NOT changed (theta within 1 SE of 1; vintages straddle 1.18/1.14).
    R_NB = round(r_hat, 2)
    KAPPA = CUR["COMP_K"]
    bt_ = btab.set_index("band")
    A_ = res["a"]; K8 = A_["panels"]["main_avg_series_8q"]; K12 = A_["panels"]["plus_histogram_quarters"]; C_ = res["c"]; KF = A_["robustness"]
    f2 = lambda x: "%.2f" % x
    f3 = lambda x: "%.3f" % x
    nb_c_rng = (float(nbspec.c.min()), float(nbspec.c.max())); nb_r_rng = (float(nbspec.dispersion.min()), float(nbspec.dispersion.max()))
    spec_maxdiff = float(SPEC.max_abs_thin_diff_vs_rec.max())
    old_half = (1 - np.exp(-0.5 * 0.34 * G)) / (1 - np.exp(-0.34 * G)); old_quart = (1 - np.exp(-0.25 * 0.34 * G)) / (1 - np.exp(-0.34 * G))
    s09, s08, s06 = sel_nb.loc[0.9], sel_nb.loc[0.8], sel_nb.loc[0.6]
    p09 = sel_pln.loc[0.9]
    b075, b05 = BETA.set_index("beta").loc[0.75], BETA.set_index("beta").loc[0.5]
    two_way = KF["two_way_fe_per_offer"]; two_way_k = KF["two_way_fe_kappa_units_eiv"]; msb = KF["main_street_bands_band_fe_per_offer"]
    SPI = SPEC.set_index("spec")
    sp = lambda lab_: (float(SPI.loc[lab_, "c"]), float(SPI.loc[lab_, "dispersion"]))
    sp_d25 = sp(L_D25); sp_d23 = sp(L_D23); sp_d23c = sp("drop 2023Q4 and the 2025Q4 5M-50M cell"); sp_q13 = sp("2023Q1-Q3 only (both flagged quarters dropped)")
    sp_rc = sp("rounding-consistent n weights (largest n that reproduces the published percentages)")
    QLs = REV3["QL"]; qn = QLs["selection_q_nb"]; qp = QLs["selection_q_pln"]

    def build_comp_json(extra):
        cj_ = {
            "eng_share": ENG, "eng_share_se": round(c_hat * c_se_log, 3), "eng_share_ci95": [round(float(c_ci[0]), 3), round(float(c_ci[1]), 3)],
            "eng_share_spec_range": [round(nb_c_rng[0], 3), round(nb_c_rng[1], 3)], "eng_share_spec_n": n_spec_nb,
            "eng_share_pln": {"c": round(float(pln_row.c), 3), "se": round(float(pln_c_se), 3), "log_sd": round(float(pln_row.dispersion), 2),
                              "note": "Poisson-lognormal scale, which fits better; it pairs with its own log-sd, not with nb_r, so it is not a range for eng_share"},
            "nb_r": R_NB, "nb_r_se": round(r_hat * r_se_log, 2), "nb_r_ci95": [round(float(r_ci[0]), 2), round(float(r_ci[1]), 2)],
            "nb_r_spec_range": [round(nb_r_rng[0], 2), round(nb_r_rng[1], 2)],
            "thin_half_pool": [round(float(rec_half.min()), 2), round(float(rec_half.max()), 2)],
            "thin_half_pool_se": [round(REV3["thin_se_half"][0], 3), round(REV3["thin_se_half"][1], 3)],
            "thin_quarter_pool": [round(float(rec_quart.min()), 2), round(float(rec_quart.max()), 2)],
            "thin_quarter_pool_se": [round(REV3["thin_se_quart"][0], 3), round(REV3["thin_se_quart"][1], 3)],
            "thin_shape": ("fitted scale, judgment shape: closing assumed not to depend on the number of offers once there is one (the histograms lean "
                           "toward it does, which would lower the factor); offers assumed proportional to buyers contacted (a weak analog leans toward "
                           "less than proportional, which would raise it); capped at 1 (judgment)"),
            "thin_selection_drop_half": [round(float(s09.drop_half_vs_rec_min), 2), round(float(s06.drop_half_vs_rec_max), 2)],
            "thin_beta_rise_half": [round(float(b075.rise_half_vs_rec_min), 2), round(float(b05.rise_half_vs_rec_max), 2)],
            "cap_forgone_2x": [round(REV3["cap2"][0], 2), round(REV3["cap2"][1], 2)],
            "quasi_dispersion": [round(REV3["phi_lo"], 1), round(REV3["phi_hi"], 1)],
            "n_deals": int(round(ntot)), "n_deals_rounding_consistent": int(round(REV3["n_rc_total"])),
            "band_quarters": int(o.groupby(["period", "band"]).ngroups), "quarters": "2023Q1-2023Q4, 2025Q4", "quarter_clusters": len(qs),
            "offers_per_closed_deal_lower_bound": {b: round(float(bt_.loc[b, "obs_mean_lowerbound"]), 2) for b in BANDS},
            "offers_per_closed_deal_bandfree_fit": {b: round(float(m2_zt[i]), 2) for i, b in enumerate(BANDS)},
            "offers_per_closed_deal_model": {b: round(float(zt_ind_mean[i]), 3) for i, b in enumerate(BANDS)},
            "avg_offers_bars_2024_2026": {b: round(float(thd.set_index("band").loc[b, "obs_mean"]), 3) for b in BANDS},
            "series_disagreement": {"2023Q4_bars_minus_histogram_lower_bound": [round(-x_, 2) for x_ in
                                                                                 (np.array(SER["lb_2023"]) - np.array(SER["bars_2023"])).tolist()],
                                    "2025Q4_table_minus_histogram_lower_bound": SER["diff_2025"]},
            "share_one_offer": {b: round(float(bt_.loc[b, "obs_share1"]), 3) for b in BANDS},
            "kappa": KAPPA, "kappa_ibba_within_band": [round(K8["kappa_eiv"], 3), round(K8["kappa_eiv_se"], 3)],
            "kappa_ci95_ibba": [round(x, 2) for x in K8["kappa_eiv_ci95"]],
            "kappa_two_way_fe_eiv": [round(two_way_k[0], 3), round(two_way_k[1], 3)],
            "kappa_crossband_upper": round(A_["pooled_crossband_kappa_units"], 2), "kappa_n_band_quarters": K8["n"],
            "strategic_premium": {"status": "consistency check only; BUYERS mf unchanged (judgment)",
                                  "pepperdine_2016": [round(C_["pepperdine2016"]["mean_cap100"] / 100, 3), round(C_["pepperdine2016"]["mean_cap100_se"] / 100, 3)],
                                  "pepperdine_2025_secondary": [round(C_["pepperdine2025_boot"]["mean"] / 100, 3), round(C_["pepperdine2025_boot"]["se"] / 100, 3)],
                                  "re_pooled": [round(C_["re_pooled"]["mean"] / 100, 3), round(C_["re_pooled"]["se"] / 100, 3)],
                                  "model_full_presence": round(C_["full_presence"]["prem"], 3),
                                  "theta": [round(C_["theta"], 3), round(C_["theta_se"], 3)],
                                  "implied_str_adj_2016_only": [round(1 + .18 * C_["theta_2016_only"], 2), round(1 + .14 * C_["theta_2016_only"], 2)],
                                  "implied_str_adj_2025_only": [round(1 + .18 * C_["theta_2025_only"], 2), round(1 + .14 * C_["theta_2025_only"], 2)]},
            "addon_over_platform_gf": [round(C_["gf_addon_over_platform"]["ratio"], 3), round(C_["gf_addon_over_platform"]["se_log"], 3)],
            "refit_when": ("refit ENG_SHARE and NB_R (fit/competition_buyers.py) whenever IND buyers, the BUYERS fit functions, peRef or buyerMix change: "
                           "ENG_SHARE is calibrated against this console's own typical pool. Re-run it as well after any change to P_C, E[price] or the "
                           "Omni score, so the score effects quoted on the Data tab and the score pins in the tests are regenerated"),
            "source": ("IBBA/M&A Source Market Pulse offers-per-closed-deal histograms by deal-size band, zero-truncated negative binomial "
                       "(fit/competition_buyers.py). Both flagged quarters are kept. 2023Q4 (read from a multi-series line chart, executive report "
                       "Figure 10) is inconsistent with the same report's average-offers bars (Figure 11) in all five bands: its lowest possible means "
                       "exceed the bars by %.2f-%.2f. 2025Q4 is inconsistent in one band (the $2M-5M histogram implies at least %.2f offers per deal, its "
                       "own table %.2f) and its $5M+ cell has 35%% at 10+ (n=26). Dropping 2025Q4 gives eng_share %.3f, nb_r %.2f; dropping 2023Q4 and "
                       "that cell %.3f, %.2f; 2023Q1-Q3 only %.3f, %.2f. The histograms and IBBA's average-offers bars and tables disagree with each other "
                       "wherever both exist, in opposite directions, so no band-specific adjustment is based on the bars. Kappa: IBBA realized/ask x "
                       "average offers, within band. Buyer factors: Pepperdine PCM 2016/2025, GF Data, Stanford 2024, as a consistency check")
                      % (SER["gap_2023"][0], SER["gap_2023"][1], SER["lb_2025"][3], SER["t25"]["2M-5M"], sp_d25[0], sp_d25[1], sp_d23c[0], sp_d23c[1],
                         sp_q13[0], sp_q13[1])}
        cj_.update(extra)
        return cj_

    def build_ovr(cj_, cond_txt, cap_txt):
        CONST_BLOCK_ = ("/* Competition (fit/competition_buyers.py). An engaged buyer is one who makes an offer: ENG_SHARE turns buyers\n"
                        "   contacted x engagement into expected offers so a typical pool reproduces IBBA's offers per closed deal by size,\n"
                        "   and offers are negative-binomial across deals (dispersion NB_R). Pool size is measured relative to the\n"
                        "   industry's typical pool, IND buyers (judgment): ENG_SHARE absorbs its level, not the user's ratio to it.\n"
                        "   ENG_SHARE is calibrated against this console's own typical pool: refit it whenever IND buyers, the BUYERS fit\n"
                        "   functions, peRef or buyerMix change. COMP_K stays judgment: IBBA's within-band panel bounds it only loosely.\n"
                        "   COMP_H is the old half-saturation of 3 engaged buyers at a 0.34 share, re-expressed in offers, so the premium\n"
                        "   is unchanged. */\n"
                        "const ENG_SHARE=MODELS.fitted.competition.eng_share, NB_R=MODELS.fitted.competition.nb_r;\n"
                        "const COMP_K=MODELS.fitted.competition.kappa, COMP_H=3*ENG_SHARE/.34;\n"
                        "const pAnyOffer=n=>1-Math.pow(1+Math.max(n,0)/NB_R,-NB_R);")
        THIN_NEW_ = ("  /* A sale needs at least one offer. Pepperdine's base rate describes deals marketed to a\n"
                     "     typical pool, and offers per deal are negative binomial across deals (IBBA offer-count\n"
                     "     histograms, NB_R), so a pool thinner than typical scales P_C by P(any offer | pool) /\n"
                     "     P(any offer | typical pool). Fitted scale, judgment shape: this assumes closing does\n"
                     "     not depend on how many offers arrive once there is one, and that offers grow in\n"
                     "     proportion to buyers contacted; neither is measured. The cap at 1 is judgment too: a\n"
                     "     deeper pool earns the competition premium, not a higher P_C, although the fitted NB\n"
                     "     alone would keep raising P(any offer) (" + cap_txt + " at twice the typical pool).\n"
                     "     Without this, 5 buyers contacted closed as often as 600, and the optimiser dropped\n"
                     "     outreach exactly where the pool was too thin to produce a buyer. */")
        COMP_LINE_ = ("/* The premium uses the unconditional expected offer count. Conditioning on a sale (at least\n"
                      "     one offer) would shrink thin-pool discounts " + cond_txt + ";\n"
                      "     kept, because COMP_K is judgment and this keeps the premium exactly as before. */\n"
                      "  out.compPrem=clamp(out.compK*Math.log((COMP_H+out.nEng)/(COMP_H+out.nEngRef)),-.08,.14);")
        return [
            ['\nconst VBANDS=[["<500K",0,5e5]', "\nMODELS.fitted.competition=" + json.dumps(cj_, separators=(",", ":")) + ';\nconst VBANDS=[["<500K",0,5e5]'],
            ["const LAM0=250, KW=1.42, PHI=.38;", "const LAM0=250, KW=1.42, PHI=.38;\n" + CONST_BLOCK_],
            ["  out.nEng=s.buyers*avgPE*0.34;", "  out.nEng=s.buyers*avgPE*ENG_SHARE;"],
            ["  out.nEngRef=(I.buyers||50)*peRef*0.34;", "  out.nEngRef=(I.buyers||50)*peRef*ENG_SHARE;"],
            ["  out.compK=.030;", "  out.compK=COMP_K;"],
            ["out.compPrem=clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);", COMP_LINE_],
            [THIN_OLD, THIN_NEW_],
            ["  out.nPool=s.buyers*peRef*0.34;", "  out.nPool=s.buyers*peRef*ENG_SHARE;"],
            ["  out.thinF=Math.min(1,(1-Math.exp(-out.nPool))/Math.max(1e-9,1-Math.exp(-out.nEngRef)));",
             "  out.thinF=Math.min(1,pAnyOffer(out.nPool)/Math.max(1e-9,pAnyOffer(out.nEngRef)));"],
        ], CONST_BLOCK_, THIN_NEW_, COMP_LINE_

    THIN_OLD = ("  /* A sale needs at least one engaged buyer. Pepperdine's base rate describes deals\n"
                "     marketed to a typical pool, so a pool thinner than typical scales P_C by the chance\n"
                "     of engaging anyone (Poisson) relative to a typical pool's; a deeper pool earns\n"
                "     nothing extra here (it earns the competition premium instead). Without this, 5\n"
                "     buyers contacted closed as often as 600, and the optimiser dropped outreach exactly\n"
                "     where the pool was too thin to produce a buyer. */")
    cap_txt = "x%.2f-%.2f" % (REV3["cap2"][0], REV3["cap2"][1])
    # pass 1 (model-identical; the comment and stored text are finalised after the probes below)
    ovr, _, _, _ = build_ovr(build_comp_json({}), "...", cap_txt)
    DISPLAY = [
        ['Competition: ${r.nEng.toFixed(1)} engaged buyer${Math.abs(r.nEng-1)<.05?"":"s"} against a typical ${r.nEngRef.toFixed(1)}',
         'Competition: ${r.nEng.toFixed(1)} expected offer${Math.abs(r.nEng-1)<.05?"":"s"} against a typical ${r.nEngRef.toFixed(1)}'],
        [r'\\text{comp}=\\kappa\\ln\\frac{3+n_{\\text{engaged}}}{3+n_{\\text{typical}}}',
         r'\\text{comp}=\\kappa\\ln\\frac{${COMP_H.toFixed(2)}+n_{\\text{offers}}}{${COMP_H.toFixed(2)}+n_{\\text{typical}}}'],
        [r'eq("eq_comps",`n_{\\text{engaged}}\\approx', r'eq("eq_comps",`n_{\\text{offers}}\\approx'],
    ]

    # score impact (needed for the Data-tab caveat), run on the patched and the current model
    chk_new = run_probe({"mode": "check", "n": 400, "example": ex, "overrides": ovr, "nb_r": R_NB})["check"]
    chk_old = run_probe({"mode": "check", "n": 400, "example": ex, "overrides": [["/* ---- §20 competition", "/* ---- §20 competition"]]})["check"]
    SC = pd.DataFrame(chk_old["scores"]).merge(pd.DataFrame(chk_new["scores"]), on=["ind", "ern", "f", "buyers"], suffixes=("_old", "_new"))
    SC.to_csv(os.path.join(OUT, "score_impact_median_businesses.csv"), index=False)
    EXS = pd.DataFrame(chk_old["ex_scores"]).merge(pd.DataFrame(chk_new["ex_scores"]), on="buyers", suffixes=("_old", "_new"))
    sc_rng = {f_: (int(SC[SC.f == f_].score_old.min()), int(SC[SC.f == f_].score_old.max()), int(SC[SC.f == f_].score_new.min()), int(SC[SC.f == f_].score_new.max()),
                   float((SC[SC.f == f_].score_old - SC[SC.f == f_].score_new).median()))
              for f_ in (0.25, 0.5, 0.75, 0.9, 1.0)}
    log("\nOmni score of median businesses (16 industries x SDE $0.2M/$1M/$4M) at a fraction f of the typical pool, old -> new (min-max; median drop):",
        {f_: "%d-%d -> %d-%d (median drop %.0f)" % v for f_, v in sc_rng.items()})
    log("example business, score by buyers contacted (old -> new):", EXS[["buyers", "score_old", "score_new", "thinF_old", "thinF_new", "PC_old", "PC_new"]].round(4).values.tolist())
    ex25 = EXS.set_index("buyers").loc[25]
    h50 = sc_rng[0.5]; h75 = sc_rng[0.75]; h90 = sc_rng[0.9]

    # revision 3: the premium with the conditional (given at least one offer) expected count, worked example
    def cond_prem(n_, nref_):
        return float(np.clip(KAPPA * math.log((H_NEW + n_ / p_any(n_, R_NB)) / (H_NEW + nref_ / p_any(nref_, R_NB))), -.08, .14))
    EXS["compPrem_conditional"] = [cond_prem(a_, b_) for a_, b_ in zip(EXS.nEng_new, EXS.nEngRef_new)]
    EXS["cond_shrink_pp"] = 100 * (EXS.compPrem_conditional - EXS.compPrem_new)
    EXS.to_csv(os.path.join(OUT, "score_impact_example.csv"), index=False)
    ex_thin = EXS[EXS.buyers <= 12]
    cond_txt = "by %.1f-%.1f percentage points (worked example, %d-%d buyers)" % (ex_thin.cond_shrink_pp.min(), ex_thin.cond_shrink_pp.max(),
                                                                                        int(ex_thin.buyers.min()), int(ex_thin.buyers.max()))
    log("conditional vs unconditional offers in compPrem (example):", EXS[["buyers", "nEng_new", "nEngRef_new", "compPrem_new", "compPrem_conditional", "cond_shrink_pp"]].round(4).values.tolist())
    # revision 3: the example's own numbers for the cap and the kink at the typical pool
    nref_ex = float(chk_new["example"]["nEngRef"])
    cap_ex = float(p_any(2 * nref_ex, R_NB) / p_any(nref_ex, R_NB))
    el_ex_new = float(nref_ex * (1 + nref_ex / R_NB) ** (-R_NB - 1) / p_any(nref_ex, R_NB))
    nref_ex_old = float(chk_old["example"]["nEngRef"]); el_ex_old = float(nref_ex_old * math.exp(-nref_ex_old) / (1 - math.exp(-nref_ex_old)))
    log("example cap: P(any offer) at twice the typical pool = %.3f x typical (forgone by the cap); thinF elasticity just below typical %.2f (old %.2f)" % (cap_ex, el_ex_new, el_ex_old))

    # revision 3: IND.buyers is a judgment table, and the thin-pool factor is measured against it. Example scores with the
    # medical typical pool set to 40 / 50 (as now) / 60, ENG_SHARE held at its fit (as the console would be until refit).
    IND_A = "anchor:3.10, buyers:50,"
    assert open("/home/user/last-minute/index.html").read().count(IND_A) == 1
    INDS = []
    for ib_ in (40, 50, 60):
        o_ind = [[IND_A, "anchor:3.10, buyers:%d," % ib_]] if ib_ != 50 else []
        r_old_ = run_probe({"mode": "exscores", "example": ex, "overrides": o_ind or [["/* ---- §20 competition", "/* ---- §20 competition"]]})["ex_scores"]
        r_new_ = run_probe({"mode": "exscores", "example": ex, "overrides": ovr + o_ind})["ex_scores"]
        for a_, b_ in zip(r_old_, r_new_):
            INDS.append(dict(ind_buyers=ib_, buyers=a_["buyers"], score_old=a_["score"], score_new=b_["score"], thinF_old=a_["thinF"], thinF_new=b_["thinF"],
                             PC_old=a_["PC"], PC_new=b_["PC"]))
    INDS = pd.DataFrame(INDS); INDS.to_csv(os.path.join(OUT, "ind_buyers_sensitivity_example.csv"), index=False)
    isx = INDS.set_index(["ind_buyers", "buyers"])
    ind_sw = {b_: dict(new=[int(isx.loc[(i_, b_), "score_new"]) for i_ in (40, 50, 60)], old=[int(isx.loc[(i_, b_), "score_old"]) for i_ in (40, 50, 60)]) for b_ in (25, 40)}
    sens_ratio = (ind_sw[40]["new"][0] - ind_sw[40]["new"][2]) / max(1, ind_sw[40]["old"][0] - ind_sw[40]["old"][2])
    log("IND.medical.buyers 40/50/60, example score at 40 buyers contacted: new %s, old %s; at 25: new %s, old %s (score swing new/old = %.1fx)"
        % (ind_sw[40]["new"], ind_sw[40]["old"], ind_sw[25]["new"], ind_sw[25]["old"], sens_ratio))

    # pass 2: the final text (identical model)
    cj = build_comp_json({})
    COMP_JSON = json.dumps(cj, separators=(",", ":"))
    ovr, CONST_BLOCK, THIN_NEW, COMP_LINE = build_ovr(cj, cond_txt, cap_txt)
    comp_json = cj

    # ---------------- Data tab (renderData): exact edits ----------------------------------------
    fp3 = lambda p_: ("%.3f" % p_) if p_ >= 0.001 else "&lt;0.001"
    ROW_FIT = (
        "\n      <tr><td>Buyer pool: expected offers, and how a thin pool lowers the closing probability</td>"
        "<td>0.34 of engaged-fit buyers counted as engaged; Poisson chance of engaging anyone</td>\n"
        "        <td>${Fv.competition.eng_share.toFixed(3)} of engaged-fit buyers make an offer (se ${Fv.competition.eng_share_se.toFixed(3)}; "
        "${Fv.competition.eng_share_spec_range[0].toFixed(2)}&ndash;${Fv.competition.eng_share_spec_range[1].toFixed(2)} across "
        "${Fv.competition.eng_share_spec_n} alternative specifications). "
        "Offers vary across deals as a negative binomial, r = ${Fv.competition.nb_r.toFixed(2)} (se ${Fv.competition.nb_r_se.toFixed(2)}; "
        "${Fv.competition.nb_r_spec_range[0].toFixed(1)}&ndash;${Fv.competition.nb_r_spec_range[1].toFixed(1)} across specifications: weakly identified). "
        "A typical pool gives ${Fv.competition.offers_per_closed_deal_model[\"<500K\"].toFixed(1)} offers per closed deal under $500K, rising to "
        "${Fv.competition.offers_per_closed_deal_model[\"5M-50M\"].toFixed(1)} at $5M+. Half the typical pool scales the closing probability by "
        "${Fv.competition.thin_half_pool[0].toFixed(2)}&ndash;${Fv.competition.thin_half_pool[1].toFixed(2)} (was %s; sampling se "
        "${Fv.competition.thin_half_pool_se[0].toFixed(3)}&ndash;${Fv.competition.thin_half_pool_se[1].toFixed(3)}), a quarter by "
        "${Fv.competition.thin_quarter_pool[0].toFixed(2)}&ndash;${Fv.competition.thin_quarter_pool[1].toFixed(2)} (was %s). "
        "Pool size is measured relative to the industry&rsquo;s typical pool (<code>IND</code> buyers, judgment); the offer share absorbs its level but not "
        "the user&rsquo;s ratio to it. <b>Fitted scale, judgment shape.</b></td>\n"
        "        <td>IBBA Market Pulse offers per closed deal by size band: ${Fv.competition.band_quarters} band-quarter histograms "
        "(${Fv.competition.quarters}, ${Fv.competition.quarter_clusters} quarters, so the standard errors rest on few clusters), about "
        "${Fv.competition.n_deals.toLocaleString()} closed deals (the published percentages fit about "
        "${Fv.competition.n_deals_rounding_consistent.toLocaleString()} answering the offers question). Held-out quarters: log-likelihood %.3f per deal, "
        "against %.3f for a Poisson at the fitted scale. The 2023Q4 histogram, read off a line chart, sits above the same report&rsquo;s average-offers bars "
        "in all five bands (by %.2f&ndash;%.2f), and 2025Q4&rsquo;s $2M&ndash;5M histogram sits above its own table; both are kept, and dropping them gives "
        "%.2f&ndash;%.2f. On IBBA&rsquo;s 2024&ndash;26 average-offers bars the RMSE is %.2f (free band levels %.2f; the old scale %.2f), but the bars and "
        "the histograms disagree wherever both exist, so that check is indicative only.\n"
        "        <div class=\"muted\" style=\"font-size:11.5px;margin-top:4px\">Zero-offer listings are never observed, so the chance of no offer is an "
        "extrapolation (the negative binomial puts it below Pepperdine&rsquo;s base close rate under $500K); only the ratio is used, and sampling pins that "
        "to within a standard error of %.2f&ndash;%.2f. Three assumptions matter more and are not measured. If more offers make a close likelier, the factor at half the pool is "
        "%.2f&ndash;%.2f lower; the histograms lean that way (p = %s treating deals as independent, %s&ndash;%s allowing for quarter-to-quarter "
        "variation), and only Pepperdine&rsquo;s base close rate argues against it. If offers grow less than in proportion to buyers contacted, it is "
        "%.2f&ndash;%.2f higher; a snapshot of Flippa listings (online, not transferable) mostly leans that way (offers rise %.1f&ndash;%.1f%% per 1%% more "
        "watchers; %d of %d estimates below 1%%). The cap at 1 is judgment: the fitted distribution alone would raise the chance of an offer &times;"
        "${Fv.competition.cap_forgone_2x[0].toFixed(2)}&ndash;${Fv.competition.cap_forgone_2x[1].toFixed(2)} at twice the typical pool; a deeper pool earns "
        "the competition premium instead. At the time of fitting, a median business marketed to half its typical pool scored %d&ndash;%d instead of "
        "%d&ndash;%d on the Omni score (median drop %.0f points), because its peers are all marketed to a typical pool; other model changes move these "
        "numbers (re-run fit/competition_buyers.py).</div></td></tr>"
    ) % (rngf(old_half).replace("-", "&ndash;"), rngf(old_quart).replace("-", "&ndash;"), cvs["recommended_M5"], cvs["poisson_fitted_scale_M5P"],
         SER["gap_2023"][0], SER["gap_2023"][1], min(sp_d23c[0], sp_q13[0], sp_d23[0], sp_d25[0]), max(sp_d23c[0], sp_q13[0], sp_d23[0], sp_d25[0]),
         hold["pred_rec"]["rmse"], hold["pred_M2"]["rmse"], hold["pred_current"]["rmse"], REV3["thin_se_half"][0], REV3["thin_se_half"][1],
         float(s09.drop_half_vs_rec_min), float(s06.drop_half_vs_rec_max), fp3(qn["p"]), fp3(qn["p_hi"]), "%.2f" % qn["p_lo"],
         float(b075.rise_half_vs_rec_min), float(b05.rise_half_vs_rec_max), WAT["range"][0], WAT["range"][1], WAT["n_below1"], WAT["n_est"],
         h50[2], h50[3], h50[0], h50[1], h50[4])
    LEDGER_K_OLD = ("      <tr><td>Competition premium (&kappa;), engaged-buyer share, thin-pool closing factor</td>\n"
                    "          <td>buyer-level outreach rows: contacted, NDA, LOI, bids, closed</td>\n"
                    "          <td><span class=\"st free\">own records only; no public bidder-count data for private targets</span></td></tr>")
    LEDGER_K_NEW = ("      <tr><td>Competition premium (&kappa; = ${COMP_K.toFixed(2)}) and its half-saturation; the shape of the thin-pool factor</td>\n"
                    "          <td>deal-level offer counts with ask and sale prices; buyer-level outreach rows (contacted, offers, closed)</td>\n"
                    "          <td><span class=\"st free\">IBBA&rsquo;s quarterly band averages bound &kappa; only to %s to %s (%d band-quarters within size band, "
                    "corrected for sampling noise; band sizes imputed for %d of them); with quarter effects the slope is %s per offer (se %.3f). Neither 0 nor 0.03 "
                    "predicts held-out quarters better. The cross-band pattern caps &kappa; near %.2f but is confounded with size; Flippa auction bids are not "
                    "comparable. Whether more offers make a close likelier (the offer histograms lean that way), whether offers grow in proportion to buyers "
                    "contacted (a Flippa watchers snapshot leans toward less), and whether a deeper pool raises the closing probability are not measured</span></td></tr>"
                    ) % (("%+.2f" % K8["kappa_eiv_ci95"][0]).replace("-", "&minus;"), ("%+.2f" % K8["kappa_eiv_ci95"][1]).replace("-", "&minus;"), K8["n"], KF["n_imputed"],
                         ("%+.3f" % two_way[0]).replace("-", "&minus;"), two_way[1], A_["pooled_crossband_kappa_units"])
    LEDGER_B_OLD = ("      <tr><td>Buyer archetypes: fit functions, synergy shares, multiple factors, seller share &phi;</td>\n"
                    "          <td>who bought what, at what premium</td>\n"
                    "          <td><span class=\"st free\">premiums only exist for $100M+ public targets; the size mix is now fitted</span></td></tr>")
    LEDGER_B_NEW = ("      <tr><td>Buyer archetypes: fit functions, synergy shares, multiple factors, seller share &phi;</td>\n"
                    "          <td>who bought what, at what premium</td>\n"
                    "          <td><span class=\"st free\">the size mix is fitted; the multiple factors are checked, not fitted. Bankers report strategic buyers paying "
                    "%.1f%% over financial buyers (Pepperdine 2016, se %.1f, n=120) and about %.0f%% (2025, secondary quote); pooled %.1f%% (se %.1f), against "
                    "the model&rsquo;s %.1f%% with both present (consistent within 1 se), so the factors stay: 2025 alone implies the current %.2f/%.2f, 2016 alone %.2f/%.2f. GF Data&rsquo;s "
                    "add-on/platform ratio %.2f (se of log %.2f) matches the model&rsquo;s %.2f; search funds pay about PE multiples at equal quality (Stanford 2024). "
                    "Synergy shares, &phi; and the individual, MBO and family-office factors have no data</span></td></tr>"
                    ) % (C_["pepperdine2016"]["mean_cap100"], C_["pepperdine2016"]["mean_cap100_se"], C_["pepperdine2025_boot"]["mean"], C_["re_pooled"]["mean"],
                         C_["re_pooled"]["se"], 100 * C_["full_presence"]["prem"], 1 + .18 * C_["theta_2025_only"], 1 + .14 * C_["theta_2025_only"],
                         1 + .18 * C_["theta_2016_only"], 1 + .14 * C_["theta_2016_only"], C_["gf_addon_over_platform"]["ratio"], C_["gf_addon_over_platform"]["se_log"],
                         C_["full_presence"]["add_vs_pep"])
    IND_ROW_OLD = "the quality position of the value. The industry level of the value comes from the fitted NAICS table.</td></tr>"
    IND_ROW_NEW = ("the quality position of the value. <code>IND</code> buyers is also the typical pool that the thin-pool factor and the competition "
                   "premium are measured against, so below a typical pool it moves the closing probability, expected proceeds and the Omni score (the "
                   "fitted offer share absorbs its level, not the user&rsquo;s ratio to it). The industry level of the value comes from the fitted NAICS table.</td></tr>")
    NFIT_OLD = "             + MODELS.fitted.buyer_mix.knots.length*2;                 /* buyer-mix log-ratios by band */"
    NFIT_NEW = ("             + MODELS.fitted.buyer_mix.knots.length*2                  /* buyer-mix log-ratios by band */\n"
                "             + 2;                                                      /* ENG_SHARE and NB_R: offers per closed deal (IBBA) */")
    ROW_ANCHOR = "Phrase flags are noisy, so both effects are understated.</td></tr>"
    DATA = [[NFIT_OLD, NFIT_NEW], [ROW_ANCHOR, ROW_ANCHOR + ROW_FIT], [LEDGER_K_OLD, LEDGER_K_NEW], [LEDGER_B_OLD, LEDGER_B_NEW], [IND_ROW_OLD, IND_ROW_NEW]]
    html = open("/home/user/last-minute/index.html").read()
    for a_, _ in ovr + DISPLAY + DATA:
        assert html.count(a_) == 1, "anchor not unique/absent in index.html: " + a_[:60]
    for _, b_ in DATA:
        assert "`" not in b_, "a backtick would end renderData's template literal"

    log("\nimplementation check (400 random businesses x 11 pool sizes): new", {k: chk_new[k] for k in ["n", "mono_fail", "thin_fail", "ref_fail", "qual_fail", "median_fail"]},
        " old", {k: chk_old[k] for k in ["n", "mono_fail", "thin_fail", "ref_fail", "qual_fail", "median_fail"]})
    log("median-business max |compPrem| new %.2e old %.2e (PE floor of .01 vs 0 in peRef); max |1-thinF| new %.1e"
        % (chk_new["median_max_abs_comp"], chk_old["median_max_abs_comp"], chk_new["median_max_thin_gap"]))
    sh = pd.DataFrame(chk_new["share1"]); sh.to_csv(os.path.join(OUT, "implied_share1_typical_pool_new.csv"), index=False)
    sho = pd.DataFrame(chk_old["share1"])
    log("implied share of one-offer closings at the typical pool, by band centre (min-max over industries): new",
        sh.groupby("V").share1.agg(["min", "max"]).round(3).values.tolist(), " old (Poisson)", sho.groupby("V").share1.agg(["min", "max"]).round(3).values.tolist())
    log("example business old:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in chk_old["example"].items()})
    log("example business new:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in chk_new["example"].items()})
    comp_diff = float(np.max(np.abs(np.array(chk_new["comp"]) - np.array(chk_old["comp"]))))
    log("max |compPrem(new) - compPrem(old)| over %d business x pool cases = %.2e (COMP_H rescale keeps the premium identical)" % (len(chk_new["comp"]), comp_diff))
    log("example at 12 buyers old:", {k: round(v, 4) for k, v in chk_old["example_thin12"].items()}, " new:", {k: round(v, 4) for k, v in chk_new["example_thin12"].items()})
    log("example outreach x2.2 old:", {k: round(v, 4) for k, v in chk_old["example_outreach"].items()}, " new:", {k: round(v, 4) for k, v in chk_new["example_outreach"].items()})
    g_old = pd.DataFrame(chk_old["grid"]); g_new = pd.DataFrame(chk_new["grid"])
    gg = g_old[["ind", "f", "nEngRef", "thinF", "compPrem"]].merge(g_new[["ind", "f", "nEngRef", "thinF", "compPrem"]], on=["ind", "f"], suffixes=("_old", "_new"))
    gg.to_csv(os.path.join(OUT, "thin_pool_grid_old_vs_new.csv"), index=False)
    log(gg.round(4).to_string(index=False))
    res["check"] = dict(new=chk_new, old=chk_old, overrides=ovr, display=DISPLAY, data_tab=DATA, ENG_SHARE=ENG, NB_R=R_NB, COMP_K=KAPPA)

    # ---------------- the repo's own test suites on a patched COPY (index.html itself is untouched) ---------
    import shutil
    pc = os.path.join(OUT, "patched_copy"); os.makedirs(os.path.join(pc, "tests"), exist_ok=True)
    html_p = html
    for a_, b_ in ovr + DISPLAY + DATA:
        html_p = html_p.replace(a_, b_)
    with open(os.path.join(pc, "index.html"), "w") as f:
        f.write(html_p)
    for fn in os.listdir("/home/user/last-minute/tests"):
        if fn.endswith(".js"):
            shutil.copy(os.path.join("/home/user/last-minute/tests", fn), os.path.join(pc, "tests", fn))
    t1 = subprocess.run(["node", os.path.join(pc, "tests", "model.test.js")], capture_output=True, text=True, timeout=1800)
    t2 = subprocess.run(["node", os.path.join(pc, "tests", "fuzz.test.js"), "600"], capture_output=True, text=True, timeout=3000)
    t3 = subprocess.run(["node", os.path.join(pc, "tests", "browser.sweep.js")], capture_output=True, text=True, timeout=3000)
    # render the patched Data tab in headless Chromium and read back the new and replaced rows
    DT_JS = r"""
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{ const b=await pw.chromium.launch(); const p=await b.newPage({viewport:{width:1440,height:900}});
  const errs=[]; p.on("pageerror",e=>errs.push(e.message));
  await p.goto("file://"+process.argv[2]); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000});
  await p.click(".tab[data-v=data]"); await p.waitForTimeout(600);
  const out=await p.evaluate(()=>{ const t=document.getElementById("view-data").innerText;
    const rows=[...document.querySelectorAll("#view-data tr")].map(r=>r.innerText);
    const pick=s=>rows.filter(r=>r.includes(s));
    const comp=document.getElementById("view-console").innerText.match(/Competition:[^\n]*/);
    return {bad:/NaN|Infinity|undefined/.test(t), fit_row:pick("Buyer pool: expected offers"), kappa_row:pick("half-saturation"),
            buyer_row:pick("Buyer archetypes"), ind_row:pick("typical pool that the thin-pool factor"), tally:[...document.querySelectorAll("#view-data .tally .n")].map(e=>e.textContent),
            comp_label:comp?comp[0]:null}; });
  out.errors=errs; console.log(JSON.stringify(out)); await b.close(); })().catch(e=>{console.log(JSON.stringify({fatal:e.message})); process.exit(1);});
"""
    with open(os.path.join(OUT, "datatab_check.js"), "w") as f:
        f.write(DT_JS)
    t4 = subprocess.run(["node", os.path.join(OUT, "datatab_check.js"), os.path.join(pc, "index.html")], capture_output=True, text=True, timeout=600)
    t4o = subprocess.run(["node", os.path.join(OUT, "datatab_check.js"), "/home/user/last-minute/index.html"], capture_output=True, text=True, timeout=600)
    dt_new = json.loads(t4.stdout.strip().splitlines()[-1]); dt_old = json.loads(t4o.stdout.strip().splitlines()[-1])
    with open(os.path.join(OUT, "datatab_render_check.json"), "w") as f:
        json.dump(dict(patched=dt_new, current=dt_old), f, indent=1)
    last = lambda t: (t.stdout.strip().splitlines() or ["no output"])[-1]
    tests_summary = ("tests/model.test.js: %s; tests/fuzz.test.js 600: %s; tests/browser.sweep.js (headless Chromium, every select and slider, Data tab "
                     "NaN check): %s; Data tab render: new row present %s, replaced ledger rows present %s, IND row extended %s, NaN/undefined %s, page errors %d, tally %s -> %s"
                     % (last(t1), last(t2), (last(t3) + " (exit %d)" % t3.returncode), bool(dt_new.get("fit_row")), bool(dt_new.get("kappa_row")), bool(dt_new.get("ind_row")),
                        dt_new.get("bad"), len(dt_new.get("errors", [])), dt_old.get("tally"), dt_new.get("tally")))
    log("repo test suites on the patched copy:", tests_summary)
    log("patched Data tab, new fitted row:", dt_new.get("fit_row")); log("patched competition label:", dt_new.get("comp_label"), " current:", dt_old.get("comp_label"))
    res["tests_on_patched_copy"] = tests_summary

    # ---------------- RESULT.json -----------------------------------------------------------------
    k_up = res["a"]["pooled_crossband_kappa_units"]
    f_bind = np.array([(math.exp(0.14 / k_up) * (3 * ENG / 0.34 + n_) - 3 * ENG / 0.34) / n_ for n_ in btab.rec_mu.values])
    half = thin_tab[thin_tab.f == 0.5]
    rng_ = lambda s_: "%.2f-%.2f" % (np.min(s_), np.max(s_))
    s1n = sh.share1; s1o = sho.share1
    ex_o, ex_n = chk_old["example"], chk_new["example"]
    t12o, t12n = chk_old["example_thin12"], chk_new["example_thin12"]
    spec_c_txt = "; ".join("%s c=%.3f r=%.2f" % (r_.spec, r_.c, r_.dispersion) for r_ in nbspec.itertuples() if not r_.spec.startswith("baseline"))
    sel_txt = ("q=0.9: %.2f-%.2f lower; q=0.8: %.2f-%.2f; q=0.6 (the NB profile optimum): %.2f-%.2f"
               % (s09.drop_half_vs_rec_min, s09.drop_half_vs_rec_max, s08.drop_half_vs_rec_min, s08.drop_half_vs_rec_max, s06.drop_half_vs_rec_min, s06.drop_half_vs_rec_max))
    QLp = REV3["QL"]
    ql_pois = QLp["Poisson_vs_NB_free_bands"]; ql_pois5 = QLp["Poisson_vs_NB_console_scale"]; ql_cr = QLp["common_r"]; ql_grad = QLp["console_gradient_vs_free_bands"]
    ql_pln = QLp["pln_vs_nb (same parameter count, not nested; LR = dAIC)"]; ql_con = QLp["pepperdine_constrained"]
    phi_txt = ("deals are not independent across quarters: single-quarter fits give ENG_SHARE %s and NB_R %s, and the quarter-jackknife SE of log ENG_SHARE is "
               "%.1fx its deal-sampling SE; every deal-level LR statistic in this result is therefore quoted raw and divided by a quasi-likelihood "
               "dispersion of %.1f (Pearson X2/df on cells 1-5+) to %.1f (the squared SE ratio)"
               % ("/".join("%.3f" % x for x in REV3["sq_c"]), "/".join("%.2f" % x for x in REV3["sq_r"]), math.sqrt(REV3["phi_hi"]), REV3["phi_lo"], REV3["phi_hi"]))
    ser_txt = ("The two IBBA offer series disagree with each other wherever both exist: 2023Q4's Figure 11 bars sit below its Figure 10 histogram's lowest "
               "possible means in %d of 5 bands (by %.2f-%.2f), and 2025Q4's table sits above its histogram's lower bound by %s (the $2M-5M band below). "
               "So the bars comparison mixes definition or measurement differences with model error, and no band-specific adjustment is based on it."
               % (SER["n_incons_2023"], SER["gap_2023"][0], SER["gap_2023"][1], "/".join("%+.2f" % x for x in SER["diff_2025"])))
    params = [
        dict(param="ENG_SHARE: engaged-buyer share (the literal 0.34 in out.nEng, out.nEngRef and out.nPool)",
             current_value="0.34 (judgment). Typical pool at the five IBBA band centres: %s 'engaged' buyers (industry mean)" % rng_(btab.nEngRef_current),
             fitted_value=("%s. 'Engaged' now means 'makes an offer'. Typical pool %s expected offers (band means), which is %s offers per closed deal by band "
                           "(industry means; IBBA histogram lower bounds %s, band-free fit with tails imputed %s)")
                          % (f3(c_hat), rng_(btab.rec_mu), "/".join("%.2f" % x for x in zt_ind_mean), "/".join("%.2f" % x for x in obs.mean_lb.values),
                             "/".join("%.2f" % x for x in m2_zt)),
             se=("%s from a two-stage bootstrap (quarters, then deals within band-quarter; B=%d); 95%% CI %s-%s. Only %d quarter clusters, so treat the SE as "
                 "approximate: quarter-jackknife SE %s; deal sampling alone %s (this assumes every closed-deal respondent answered the offers item; the "
                 "published percentages are consistent with n_closed in only %d of %d band-quarters, the largest consistent n totals %d rather than %d, and "
                 "refitting with those weights gives %.3f / r %.2f). Specification range over %d distinct NB specifications: %.3f-%.3f (drop 2023Q4 %.3f; "
                 "drop 2025Q4, which is the same fit as 2023-only and the strictly temporal training set, %.3f; drop 2023Q4 and the 2025Q4 $5M+ cell %.3f; "
                 "2023Q1-Q3 only %.3f). The Poisson-lognormal family has its own scale, c=%.3f (jackknife SE %.3f) with log-sd %.2f; it pairs with that "
                 "log-sd, not with NB_R, so it is reported apart and is not part of the range.")
                % (f3(c_hat * c_se_log), B_BOOT, f3(c_ci[0]), f3(c_ci[1]), len(qs), f3(c_hat * jk_se[0]), f3(c_hat * boot5w[:, 0].std()),
                   REV3["n_rc_consistent"], n_bq, round(REV3["n_rc_total"]), round(REV3["n_closed_total"]), sp_rc[0], sp_rc[1], n_spec_nb,
                   nb_c_rng[0], nb_c_rng[1], sp_d23[0], sp_d25[0], sp_d23c[0], sp_q13[0], pln_row.c, pln_c_se, pln_row.dispersion),
             n="About %d closed deals in %d band-quarter histograms of offers per closed deal (IBBA Market Pulse 2023Q1-Q4 and 2025Q4; %d quarters); about %d answering the offers item by the rounding check"
               % (round(ntot), n_bq, len(qs), round(REV3["n_rc_total"])),
             method=("Maximum likelihood, zero-truncated negative binomial for offers per closed deal. Each band's mean is mu_b = ENG_SHARE x (industry-mean "
                     "I.buyers x peRef at the band centre, read from the console), with a common dispersion. Band-level shares %s: homogeneity is not rejected "
                     "(approximate test: Cochran Q %.2f, df 4, p=%.2f, with band SEs from one bootstrap that resamples the same quarters for every band, so "
                     "they are correlated, against a pooled value fitted to the same data); the method-of-moments tau^2 is 0, so the pooled value is used in "
                     "every band. Shrinkage: none toward 0.34 (IBBA is the target population and 0.34 had no data behind it). The console's size gradient "
                     "against five free band levels: %s. Quasi-likelihood note: %s.")
                    % (np.round(btab.c_band.values, 3).tolist(), Q, stats.chi2.sf(Q, 4), qtxt(ql_grad), phi_txt),
             validation=("Leave-one-quarter-out held-out log-likelihood per deal: %.3f, against %.3f for a Poisson at the fitted console scale, %.3f with free band "
                         "levels, %.3f for a free zero-truncated Poisson, %.3f for the Poisson-lognormal and %.3f at the old 0.34 Poisson scale. Mean held-out "
                         "error in the one-offer share: %.3f, against %.3f now. Strictly temporal (fit on the 2023 histograms only, i.e. the 'drop 2025Q4' "
                         "specification, c=%.3f, r=%.2f) against IBBA's 2024Q1-2026Q2 average-offers bars (45 band-quarters): RMSE %.2f (bias %+.2f). With "
                         "2025Q4 in training: RMSE %.2f (bias %+.2f); free band levels %.2f; Poisson at the fitted scale %.2f; old scale %.2f (bias %+.2f). "
                         "INDICATIVE ONLY: %s The bars average %.2f at $5M+ against the model's %.2f (%d of 9 quarters above), and 2025Q4's own table says %.2f "
                         "there against a histogram lower bound of %.2f. The Q4-2022 'offer from a different buyer' item is INCONCLUSIVE: singular wording %s%% "
                         "vs plural %s%% (not nested), predicted P(>=2|closed) %s.")
                        % (cvs["recommended_M5"], cvs["poisson_fitted_scale_M5P"], cvs["band_free_M2"], cvs["zt_poisson_band_free"], pln_loqo, cvs["current_model_poisson"],
                           cvs["share1_abs_err_recommended"], cvs["share1_abs_err_current"], hold["train2023_params"]["c"], hold["train2023_params"]["r"],
                           hold["pred_rec_train2023"]["rmse"], hold["pred_rec_train2023"]["bias"], hold["pred_rec"]["rmse"], hold["pred_rec"]["bias"], hold["pred_M2"]["rmse"],
                           hold["pred_M5P"]["rmse"], hold["pred_current"]["rmse"], hold["pred_current"]["bias"], ser_txt, hold["band_5M_obs_mean"], zt_mean(mu5[4], r_hat),
                           int(thd.set_index("band").loc["5M-50M", "n_q_above_rec"]), SER["t25"]["5M-50M"], SER["lb_2025"][4],
                           "/".join("%.0f" % x for x in ad.singular_offer_from_a_different_buyer), "/".join("%.0f" % x for x in ad.plural_offers_from_different_buyers),
                           "/".join("%.2f" % x for x in ad.pred_rec_ge2)),
             recommended_value="%s, read from MODELS.fitted.competition.eng_share (store the SE, CI, the NB-only specification range and the PLN scale apart)" % f3(ENG)),
        dict(param="NB_R: dispersion of offers across deals (new constant)",
             current_value="Infinity: the thin-pool factor (1-e^-nPool)/(1-e^-nEngRef) assumes Poisson offers",
             fitted_value="%s (weakly identified)" % f2(r_hat),
             se=("%s (bootstrap, %d quarter clusters); 95%% CI %s-%s; quarter-jackknife SE(log r) %.2f. Single-quarter fits %s. Specification range %.2f-%.2f "
                 "over %d distinct NB specifications (%s).")
                % (f2(r_hat * r_se_log), len(qs), f2(r_ci[0]), f2(r_ci[1]), jk_se[1], "/".join("%.2f" % x for x in REV3["sq_r"]), nb_r_rng[0], nb_r_rng[1],
                   n_spec_nb, spec_c_txt),
             n="Same as ENG_SHARE",
             method=("The same zero-truncated NB fit. Poisson is rejected: against the NB with free band means %s; against a Poisson at the fitted console scale "
                     "%s. A common r is not rejected against band-specific r (%s). r measures MARGINAL heterogeneity across deals within a band (size within "
                     "the band, industry mix, marketing breadth, quality), part of which the console conditions on; the industry-mixture likelihood raises it "
                     "to %.2f. The NB is not the best mixing family: a Poisson-lognormal fits better (dAIC %.1f; %s).")
                    % (qtxt(ql_pois), qtxt(ql_pois5), qtxt(ql_cr), float(SPI.loc["industry-mixture likelihood", "dispersion"]), 2 * (fits["M5"][1] - pln_row.nll),
                       "as a quasi-likelihood difference %.1f-%.1f, so the preference is modest" % (ql_pln["lr_lo"], ql_pln["lr_hi"])),
             validation=("What the console uses (thinF) hardly moves with r: across all %d specifications and both mixing families the factor changes by at most "
                         "%.3f over pool fractions 0.05-1 (per industry and band centre). At half a typical pool (band means) it runs %s for r=%.2f and %s for "
                         "r=%.2f, against %s at the fit. TRANBI buyer applications (analog, top of funnel) give r = 1.4-2.1, the same order.")
                        % (len(SPEC) - 1, spec_maxdiff, rng_(half.r_lo), r_ci[0], rng_(half.r_hi), r_ci[1], rng_(half.recommended)),
             recommended_value="%s, read from MODELS.fitted.competition.nb_r; store nb_r_spec_range and label it weakly identified" % f2(R_NB)),
        dict(param="thinF: thin-pool closing factor (formula)",
             current_value="min(1, (1-exp(-nPool))/(1-exp(-nEngRef))) on the 0.34 scale",
             fitted_value="min(1, pAnyOffer(nPool)/pAnyOffer(nEngRef)), where pAnyOffer(n) = 1-(1+n/NB_R)^(-NB_R). Fitted scale, judgment shape",
             se=("Sampling: the quantity the console uses is pinned much more tightly than ENG_SHARE or NB_R separately. Two-stage bootstrap SE of thinF at half "
                 "the pool %.3f-%.3f over industries x band centres (at a quarter %.3f-%.3f); single-quarter fits give %.2f-%.2f at <500K and %.2f-%.2f at $5M+ "
                 "(band means), while P(any offer | typical pool) under $500K ranges %.2f-%.2f across the same quarters: the zero class is not identified, "
                 "the ratio is. Specifications and families: at most %.3f. Shape, NOT identified and NOT in those ranges: (a) if more offers make a close "
                 "likelier, P(close|k) = 1-(1-q)^k, thinF at half the pool falls by %s. The histograms LEAN toward q<1: within the adopted NB the profile "
                 "optimum is q=%.1f and q=1 has %s; under the Poisson-lognormal (optimum q=%.1f) %s. Read as P(close) <= P(a successful offer), Pepperdine's "
                 "base close rate allows q down to about %.1f under the Poisson-lognormal (%.2f-%.2f lower) and no q<1 under the NB; that bound, the only "
                 "evidence for q=1, rests on the extrapolated zero class. q=1 is kept as labelled judgment. (b) If offers grow as buyers^beta with beta<1, "
                 "thinF at half the pool rises by %.2f-%.2f (beta 0.75) or %.2f-%.2f (beta 0.5); a Flippa open-listings snapshot (n=%d, online, watchers "
                 "not buyers contacted, censored durations: not transferable) gives an elasticity of offers to watchers of %.2f-%.2f (%d of %d estimates "
                 "below 1), leaning toward beta<1. (a) and (b) push in opposite directions. The constrained fit respecting Pepperdine in every band (c=%.3f, r=%.2f; %s) moves the "
                 "factor by at most %.2f.")
                % (REV3["thin_se_half"][0], REV3["thin_se_half"][1], REV3["thin_se_quart"][0], REV3["thin_se_quart"][1],
                   REV3["thin_sq_half_bandmeans"][0][0], REV3["thin_sq_half_bandmeans"][0][1], REV3["thin_sq_half_bandmeans"][4][0], REV3["thin_sq_half_bandmeans"][4][1],
                   REV3["pany_sq_lt500"][0], REV3["pany_sq_lt500"][1], spec_maxdiff, sel_txt, REV3["q_opt_nb"], qtxt(qn), REV3["q_opt_pln"], qtxt(qp), q_min_pln,
                   float(p09.drop_half_vs_rec_min), float(p09.drop_half_vs_rec_max), float(b075.rise_half_vs_rec_min), float(b075.rise_half_vs_rec_max),
                   float(b05.rise_half_vs_rec_min), float(b05.rise_half_vs_rec_max), WAT["n"], WAT["range"][0], WAT["range"][1], WAT["n_below1"], WAT["n_est"], c_con, r_con, qtxt(ql_con),
                   float((thin_tab.constrained - thin_tab.recommended).abs().max())),
             n="Same as ENG_SHARE (scale and dispersion); 0 target-population rows for the shape (Flippa watchers snapshot, n=%d, as a non-transferable analog)" % WAT["n"],
             method=("P(at least one offer) under the fitted NB, relative to a typical pool. The fit identifies how many offers a typical pool produces and how "
                     "unevenly they fall across deals; it does not identify how closing depends on the offer count, or how offers scale with outreach. Both "
                     "are kept at the simplest assumption (zero truncation; proportional), as labelled judgment. Capped at 1 as now, also judgment: the fitted NB "
                     "alone implies P(any offer) keeps rising above a typical pool (x%.2f-%.2f at twice the pool over industries x band centres; x%.3f in the "
                     "worked example), which the cap forgoes; a deeper pool earns the competition premium instead, and the cap keeps 'more buyers never lower "
                     "proceeds'. The kink at the typical pool is sharper than before: the elasticity of thinF to buyers just below typical is %.2f-%.2f (old "
                     "Poisson %.2f-%.2f; worked example %.2f vs %.2f), and 0 above. Pool size is measured relative to IND buyers (judgment, 29-59 per "
                     "industry); ENG_SHARE absorbs its level but not the user's ratio to it, so the score below a typical pool is now about %.0fx more "
                     "sensitive to that table (worked example at 40 buyers contacted, typical pool 40/50/60: score %s new against %s old; at 25 buyers %s "
                     "against %s).")
                    % (REV3["cap2"][0], REV3["cap2"][1], cap_ex, REV3["el_new"][0], REV3["el_new"][1], REV3["el_old"][0], REV3["el_old"][1], el_ex_new, el_ex_old,
                       sens_ratio, "/".join(str(x) for x in ind_sw[40]["new"]), "/".join(str(x) for x in ind_sw[40]["old"]),
                       "/".join(str(x) for x in ind_sw[25]["new"]), "/".join(str(x) for x in ind_sw[25]["old"])),
             validation=("At the typical pool the implied share of closings with exactly one offer is %s across industries and band centres (band means %s); "
                         "IBBA observes %s. The current Poisson implies %s. Fuzz, 400 businesses x 11 pool sizes: expected proceeds never fall as buyers are "
                         "added, and the typical pool and thinF do not depend on quality. (Indicative only, because the bars and histograms disagree: if the $5M+ "
                         "band matched the 2024-26 bars, half-pool thinF at that band centre would move from %.3f to %.3f; at the band-free histogram fit %.3f.)")
                        % (rng_(s1n), rng_(btab.rec_share1), rng_(btab.obs_share1), rng_(s1o), thin5_rec, thin5_bar, thin5_m2),
             recommended_value=("Adopt the formula. Across industries and band centres, half a typical pool now scales P_C by %s (was %s; sampling SE about %.2f) "
                                "and a quarter by %s (was %s). Label it 'fitted scale, judgment shape' and show the selection, proportionality and cap caveats.")
                               % (rngf(rec_half), rngf(old_half), REV3["thin_se_half"][1], rngf(rec_quart), rngf(old_quart))),
        dict(param="kappa: competition premium per log pool (out.compK, now COMP_K)",
             current_value="0.030 (judgment)",
             fitted_value=("%+.3f from IBBA's within-band quarterly panel, corrected for errors in variables (OLS within estimate %+.3f). With band AND quarter fixed "
                           "effects: %+.4f per offer (cluster SE %.4f), %+.3f in kappa units after the same correction. Main Street bands only (<$2M): %+.4f per offer "
                           "(SE %.4f). With the histogram-derived quarters added: %+.3f")
                          % (K8["kappa_eiv"], K8["kappa_ols"], two_way[0], two_way[1], two_way_k[0], msb[0], msb[1], K12["kappa_eiv"]),
             se=("%.3f; 95%% CI %+.2f to %+.2f (OLS cluster SE %.3f, %d quarter clusters; reliability of the offer averages %.2f). The reliability uses band-quarter "
                 "sample sizes, and n_closed is missing for %d of the %d band-quarters (%s), each imputed with its band's 2020-2025 mean: if every n were half or "
                 "double, the reliability would be %.2f or %.2f and the SE %.3f or %.3f. With the histogram quarters: SE %.3f")
                % (K8["kappa_eiv_se"], K8["kappa_eiv_ci95"][0], K8["kappa_eiv_ci95"][1], K8["kappa_ols_se_cluster"], K8["quarters"], K8["reliability"], KF["n_imputed"],
                   KF["n_rows"], ", ".join(KF["imputed_periods"]), KF["n_sensitivity"][0.5]["reliability"], KF["n_sensitivity"][2.0]["reliability"],
                   KF["n_sensitivity"][0.5]["se"], KF["n_sensitivity"][2.0]["se"], K12["kappa_eiv_se"]),
             n="%d band-quarters (%d quarters x 5 bands, 2023Q4-2026Q2), each a survey average over roughly 15-220 closed deals; sensitivity run on %d band-quarters"
               % (K8["n"], K8["quarters"], K12["n"]),
             method=("Regress realized/ask on x = s_b*ln((COMP_H+mu_bq)/(COMP_H+mu_b)) with band fixed effects. mu_bq inverts the zero-truncated NB mean for that "
                     "band-quarter's average offers. s_b = %s is the console's own pass-through of the premium into E[price|close]/ask at the reference ask. "
                     "Regression calibration corrects for the sampling noise in the band-quarter offer averages. Quarter-cluster bootstrap, B=2000. Raw slope: %+.4f "
                     "per offer (SE %.4f). It is not stable: adding quarter effects moves it to %+.4f (SE %.4f), and the Main Street bands alone give %+.4f (SE %.4f).")
                    % (rng_(pd.Series(pass_b)), K8["slope_per_offer"], K8["slope_per_offer_se_boot"], two_way[0], two_way[1], msb[0], msb[1]),
             validation=("Leave-one-quarter-out MSE x1e4: kappa=0 gives %.2f, 0.03 gives %.2f, refit gives %.2f (OLS refit %.2f). Temporal holdout (train <=2024Q4, "
                         "test 2025-26): %.2f / %.2f / %.2f. The data cannot tell 0 from 0.03. The pooled cross-band slope is %.2f (SE %.3f), confounded with size and "
                         "with the ask-versus-benchmark denominator, so it is an upper bound only. Flippa auctions give %+.2f per log bid (SE %.2f, median price $%.0f): "
                         "not transferable.")
                        % (A_["loqo_mse"]["kappa_0"] * 1e4, A_["loqo_mse"]["kappa_0.03"] * 1e4, A_["loqo_mse"]["kappa_hat"] * 1e4, A_["loqo_mse"]["kappa_ols"] * 1e4,
                           A_["temporal_holdout_mse"]["kappa_0"] * 1e4, A_["temporal_holdout_mse"]["kappa_0.03"] * 1e4, A_["temporal_holdout_mse"]["kappa_hat_train"] * 1e4,
                           A_["pooled_crossband_kappa_units"], A_["pooled_crossband_se"], A_["flippa"]["coef_log_bids"], A_["flippa"]["se"], A_["flippa"]["median_price_2026"]),
             recommended_value=("0.030, unchanged and still labelled judgment (MODELS.fitted.competition.kappa). Posterior with prior N(0.03, 0.03^2), truncated at 0 so "
                                "that more buyers never lower proceeds: mean %.3f, 95%% %.3f-%.3f; the data carry %.0f%% of the weight. Show the IBBA CI beside it.")
                               % (A_["posterior"]["mean"], A_["posterior"]["lo"], A_["posterior"]["hi"], 100 * A_["posterior"]["data_weight"])),
        dict(param="COMP_H: half-saturation offset in compPrem (the literal 3)",
             current_value="3 engaged buyers, at the 0.34 share",
             fitted_value="Not identified: IBBA's within-band quarterly range of offers is too narrow",
             se="n/a", n="n/a",
             method="Re-expressed in offer units, COMP_H = 3*ENG_SHARE/0.34 = %.2f, so compPrem as a function of buyers contacted and engagement is exactly unchanged" % (3 * ENG / 0.34),
             validation="Largest |compPrem(new) - compPrem(old)| over %d business x pool cases: %.1e" % (len(chk_new["comp"]), comp_diff),
             recommended_value="COMP_H=3*ENG_SHARE/.34 (judgment, kept)"),
        dict(param="compPrem clamp [-0.08, 0.14]",
             current_value="[-0.08, 0.14]",
             fitted_value=("Not binding at kappa=0.03: at most %+.1f%% at 4x the typical pool (median businesses). At the cross-band upper bound kappa = %.2f, the 0.14 cap "
                           "would bind from about %.1f-%.1fx the typical pool")
                          % (100 * gg.compPrem_new.max(), k_up, f_bind.min(), f_bind.max()),
             se="n/a", n="n/a", method="Bound check", validation="n/a", recommended_value="Unchanged"),
        dict(param="BUYERS str.mf / adj.mf (direct and adjacent strategic buyers)",
             current_value="1.18 / 1.14",
             fitted_value=("Not identified; consistency check only. A common scale theta on (mf-1) that matches a strategic-over-financial premium target gives theta "
                           "%.3f (SE %.3f), i.e. %.2f/%.2f, but 2025 alone gives theta %.2f (%.2f/%.2f, the current values) and 2016 alone %.2f (%.2f/%.2f)")
                          % (C_["theta"], C_["theta_se"], 1 + .18 * C_["theta"], 1 + .14 * C_["theta"], C_["theta_2025_only"], 1 + .18 * C_["theta_2025_only"],
                             1 + .14 * C_["theta_2025_only"], C_["theta_2016_only"], 1 + .18 * C_["theta_2016_only"], 1 + .14 * C_["theta_2016_only"]),
             se=("theta SE %.3f, 95%% CI about %.2f-%.2f, which covers 1. The SE rests on an assumed n=100 and shape for the 2025 secondary quote, a DerSimonian-Laird "
                 "tau from 2 studies (tau=%.2f points) and a judgment prior SD of 50%% of the model value")
                % (C_["theta_se"], C_["theta"] - 1.96 * C_["theta_se"], C_["theta"] + 1.96 * C_["theta_se"], C_["re_pooled"]["tau"]),
             n="Pepperdine PCM 2016 Fig 13: 120 investment-banker respondents in total (the number answering this item is not reported). Pepperdine 2025 as a secondary quote (n unknown; 100 assumed)",
             method=("An interval-censored hurdle lognormal on the 2016 premium buckets gives P(no premium) %.2f, a mean capped at 100%% of %.1f%% (SE %.1f) and a median of "
                     "%.1f%% (SE %.1f); it fits the buckets only roughly (G2 %.1f, 3 df, p=%.3f), but bucket-midpoint means with the open >50%% bucket at 50/75/100%% give "
                     "%.1f/%.1f/%.1f%%. Random-effects pooling with the 2025 figure (%.1f%%, SE %.1f) gives %.1f%% (SE %.1f); shrunk toward the model's full-presence "
                     "premium (%.1f%%; prior SD 50%%) it is %.1f%% (SE %.1f). theta solves model premium = target, averaged over 16 industries at $5-30M, holding syn "
                     "and PHI fixed; financial = 64%% platform + 36%% add-on (Pepperdine 2016 Fig 14).")
                    % (C_["pepperdine2016"]["p0"], C_["pepperdine2016"]["mean_cap100"], C_["pepperdine2016"]["mean_cap100_se"], C_["pepperdine2016"]["median"],
                       C_["pepperdine2016"]["median_se"], C_["pepperdine2016"]["G2"], C_["pepperdine2016"]["G2_p"],
                       C_["pepperdine2016"]["bucket_midpoint_means"][50], C_["pepperdine2016"]["bucket_midpoint_means"][75], C_["pepperdine2016"]["bucket_midpoint_means"][100],
                       C_["pepperdine2025_boot"]["mean"], C_["pepperdine2025_boot"]["se"], C_["re_pooled"]["mean"], C_["re_pooled"]["se"],
                       100 * C_["full_presence"]["prem"], 100 * C_["target_full"], 100 * C_["target_full_se"]),
             validation=("The model's full-presence premium (%.1f%%) is within 1 SE of the data-only pooled %.1f%% (SE %.1f). The comparator matters: the premium the "
                         "console actually displays (weighted by buyer presence, sizeFit) is %.1f%%, z=%.2f against Pepperdine 2016, which would imply a much larger "
                         "theta. Since the comparator choice moves the answer more than the data do, the factors are not changed. Display only either way (Vj, "
                         "stratPrem, buyer table, star map; not EVp).")
                        % (100 * C_["full_presence"]["prem"], C_["re_pooled"]["mean"], C_["re_pooled"]["se"], 100 * C_["model"]["prem_strat_vs_fin"], C_["display_premium_z"]),
             recommended_value="Unchanged (1.18 / 1.14), labelled judgment; store theta and the Pepperdine/GF comparison in MODELS.fitted.competition.strategic_premium as a consistency check"),
        dict(param="BUYERS pep.mf / add.mf (PE platform / add-on)", current_value="1.06 / 1.12",
             fitted_value="Add-on over platform %.3f from GF Data (4 reported periods, 2024-2026). The model gives %.3f at full presence"
                          % (C_["gf_addon_over_platform"]["ratio"], C_["full_presence"]["add_vs_pep"]),
             se="SE(log ratio) %.3f (t3 95%% 0.82-1.42)" % C_["gf_addon_over_platform"]["se_log"],
             n="GF Data PE deals TEV $1-25M+ as quoted by ACG articles (81 deals at $1-10M in 2024Q1-Q3; other n not published)",
             method="Random-effects mean of the log add-on/platform ratios",
             validation="The model sits inside the data CI (difference %.3f in ratio)" % (C_["full_presence"]["add_vs_pep"] - C_["gf_addon_over_platform"]["ratio"]),
             recommended_value="Unchanged (1.06 / 1.12)"),
        dict(param="BUYERS eta.mf (search fund)", current_value="0.98",
             fitted_value="Search fund over PE at equal size and quality: %s (Stanford 2024 median 7.0x, 2022-23; GF Data $10-25M, AAFP-adjusted). The model gives %.3f at full presence"
                          % ("/".join("%.2f" % x for x in C_["stanford_vs_gf"]), C_["full_presence"]["eta_vs_pep"]),
             se="About 0.10 by assumption (median against mean, and the quality adjustment). No deal-level SDs are published",
             n="Stanford 2024: 268-324 search-fund acquisitions; GF Data averages",
             method="Ratio of the published median and the quality-adjusted mean", validation="The model is about 1 assumed SE low; not significant",
             recommended_value="Unchanged (0.98); labelled judgment, consistent within 1 SE"),
        dict(param="BUYERS ind.mf / mbo.mf / fo.mf; syn shares; PHI", current_value="0.90 / 0.86 / 1.02; syn 0-1.00; PHI 0.38",
             fitted_value="Not identified", se="n/a", n="0 usable rows",
             method="No public data separates an individual buyer's or an MBO's multiple from deal size; the split of a premium between mf and synergy is not observable",
             validation="n/a", recommended_value="Unchanged; labelled judgment"),
    ]
    not_identified = [
        "kappa (premium per log pool). IBBA's within-band panel bounds it only to %+.2f..%+.2f; the slope moves from %+.4f to %+.4f per offer with quarter effects and "
        "to %+.4f on the Main Street bands alone; the errors-in-variables correction rests on band sizes imputed for %d of %d band-quarters; and neither 0 nor 0.03 "
        "predicts held-out quarters better. Keep 0.03 as judgment." % (K8["kappa_eiv_ci95"][0], K8["kappa_eiv_ci95"][1], K8["slope_per_offer"], two_way[0], msb[0],
                                                                       KF["n_imputed"], KF["n_rows"]),
        "COMP_H (half-saturation of the premium). Kept, re-expressed in offers so the premium is unchanged.",
        ("The shape of the thin-pool factor, part 1: whether closing depends on the number of offers once there is one (selection q). Not identified, but the "
         "histograms LEAN toward q<1 (NB optimum q=%.1f, q=1 at naive p=%s, %s-%s allowing for quarter dependence; PLN p=%s naive), which would make thinF at half "
         "the pool %.2f-%.2f lower (q 0.9 to 0.6). Only Pepperdine's base close rate, read through the extrapolated zero class, argues for q=1, which is kept as "
         "labelled judgment.")
        % (REV3["q_opt_nb"], fp3(qn["p"]), fp3(qn["p_hi"]), "%.2f" % qn["p_lo"], "%.3f" % qp["p"], float(s09.drop_half_vs_rec_min), float(s06.drop_half_vs_rec_max)),
        ("The shape of the thin-pool factor, part 2: whether expected offers grow in proportion to buyers contacted (the old model assumed this too). If they grow as "
         "buyers^0.5-0.75, thinF at half the pool is %.2f-%.2f higher. The only data are a non-transferable analog leaning toward beta<1: Flippa open listings "
         "(one snapshot, n=%d, watchers rather than buyers contacted, censored durations) give an elasticity of offers to (1+watchers) of %.2f-%.2f across Poisson/NB "
         "and with/without a log-ask control (%d of %d below 1). The recommended formula sits at the steep end for beta, while selection (q<1) pushes the other way.")
        % (float(b075.rise_half_vs_rec_min), float(b05.rise_half_vs_rec_max), WAT["n"], WAT["range"][0], WAT["range"][1], WAT["n_below1"], WAT["n_est"]),
        ("Whether a pool deeper than typical raises P_C (thinF is capped at 1, judgment). The fitted NB alone says it would: P(any offer) is still rising at the "
         "typical pool (%.2f-%.2f) and would be x%.2f-%.2f higher at twice the pool (x%.3f in the worked example). Nothing measures the cap; it is conservative and "
         "keeps 'more buyers never lower proceeds'.")
        % (spec_rows[0]["p_any_typ_min"], spec_rows[0]["p_any_typ_max"], REV3["cap2"][0], REV3["cap2"][1], cap_ex),
        "The level of P(no offer) for a listing: the zero class is never observed, so the level is an extrapolation of the mixing family. Under the NB it sits below "
        "Pepperdine's base close rate under $500K (%.2f vs 0.61); under the better-fitting Poisson-lognormal %.2f; across single-quarter NB fits %.2f-%.2f. Only the "
        "ratio enters the console, and its sampling SE is %.3f-%.3f at half the pool." % (btab.rec_p_any.iloc[0], float(pln_row.p_any_typ_lt500k_mean), REV3["pany_sq_lt500"][0],
                                                                         REV3["pany_sq_lt500"][1], REV3["thin_se_half"][0], REV3["thin_se_half"][1]),
        "IND buyers (the typical pool per industry, 29-59): judgment, and the user's pool is measured against it. ENG_SHARE absorbs its level, not the ratio.",
        "Strategic multiple factors str.mf/adj.mf (theta %.2f, SE %.2f, CI covers 1; vintages straddle the current values); synergy shares (syn), the seller's share "
        "of synergy (PHI), and the split of the strategic premium between mf and synergy" % (C_["theta"], C_["theta_se"]),
        "Multiple factors for individual buyers (0.90), MBOs (0.86) and family offices (1.02)",
        "The compPrem clamp bounds [-0.08, 0.14] (never binding at kappa=0.03)",
    ]
    data_tab_text = (
        "Five exact edits in renderData() (each anchor occurs once in index.html; all five were applied to the patched copy, rendered in headless Chromium and checked "
        "by tests/browser.sweep.js). The fitted-table row lives inside renderData's template literal h+=`...`, where Fv = MODELS.fitted; it reads its numbers from "
        "MODELS.fitted.competition, so they stay live, except the score effect, which is labelled 'at the time of fitting'.\n"
        "D1. nFit: replace\n" + NFIT_OLD + "\nwith\n" + NFIT_NEW + "\n"
        "nJudg is unchanged: its '+13+9+11' counts the d{} deltas, the category weights and the eleven named bounds and constants (ALPHA, AMAX, PMIN, PMAX, LAM0, "
        "KW, PHI, clamps); the retired 0.34 literal was never among them, and kappa and COMP_H stay judgment.\n"
        "D2. FITTED TABLE, new row: directly after\n" + ROW_ANCHOR + "\ninsert\n" + ROW_FIT.lstrip("\n") + "\n"
        "D3. LEDGER (still judgement): replace\n" + LEDGER_K_OLD + "\nwith\n" + LEDGER_K_NEW + "\n"
        "D4. LEDGER: replace\n" + LEDGER_B_OLD + "\nwith\n" + LEDGER_B_NEW + "\n"
        "D5. JUDGEMENT TABLE, IND row (count unchanged): replace\n" + IND_ROW_OLD + "\nwith\n" + IND_ROW_NEW + "\n"
        "Rendered (patched copy): " + " | ".join(dt_new.get("fit_row", [])[:1]).replace("\n", " ") + "\n"
        "Plain-text summary: source IBBA Market Pulse offer-count histograms (%d band-quarters, ~%d closed deals, ~%d answering the offers item, %d quarters; 2023Q4 "
        "is a line-chart read inconsistent with its own report's averages in all five bands, and 2025Q4 in one band, both kept); ENG_SHARE %.3f (SE %.3f; %.3f-%.3f "
        "over %d NB specifications; the Poisson-lognormal's own scale %.3f is reported apart); NB_R %.2f (SE %.2f, weakly identified, range %.2f-%.2f); thinF "
        "fitted scale, judgment shape (sampling SE about %.2f at half the pool; selection would lower it %.2f-%.2f, the histograms lean that way; less-than-"
        "proportional offers would raise it %.2f-%.2f; the cap at 1 is judgment); pool measured against IND buyers (judgment); kappa 0.03 judgment with the IBBA "
        "bound %+.2f..%+.2f; buyer factors unchanged and checked against Pepperdine/GF Data/Stanford."
        % (n_bq, round(ntot), round(REV3["n_rc_total"]), len(qs), c_hat, c_hat * c_se_log, nb_c_rng[0], nb_c_rng[1], n_spec_nb, pln_row.c, r_hat, r_hat * r_se_log,
           nb_r_rng[0], nb_r_rng[1], REV3["thin_se_half"][1], float(s09.drop_half_vs_rec_min), float(s06.drop_half_vs_rec_max), float(b075.rise_half_vs_rec_min),
           float(b05.rise_half_vs_rec_max), K8["kappa_eiv_ci95"][0], K8["kappa_eiv_ci95"][1]))
    implementation = (
        "index.html, last <script> and renderData(). Model edits 1-5 and Data-tab edit 6; every anchor occurs exactly once (fit/competition_buyers.py asserts this, "
        "applies all edits to a patched copy and runs the test suites and a headless render). BUYERS is NOT changed.\n"
        "ORDER: apply this after the pending fits in fit/ (anchoring_realization, overpricing_time, quality_weights_v2, sba_risk_refresh, time_to_close_shape, "
        "oews_refresh), or re-run fit/competition_buyers.py after they land. None of them touches IND buyers, BUYERS, peRef or buyerMix, so ENG_SHARE and NB_R stay "
        "valid, but several change P_C, E[price] or the Omni score, so the score pins in the invariants and the 'at the time of fitting' score effect on the Data "
        "tab must be regenerated from the final build (the script reads index.html live and rewrites every number).\n"
        "1. Before the line `const VBANDS=[[\"<500K\",0,5e5],...` insert:\nMODELS.fitted.competition=" + COMP_JSON.replace("%", "%%") + ";\n"
        "2. Directly after `const LAM0=250, KW=1.42, PHI=.38;` insert:\n" + CONST_BLOCK.replace("%", "%%") + "\n"
        "3. In model() section §20:\n"
        "   `out.nEng=s.buyers*avgPE*0.34;` -> `out.nEng=s.buyers*avgPE*ENG_SHARE;`\n"
        "   `out.nEngRef=(I.buyers||50)*peRef*0.34;` -> `out.nEngRef=(I.buyers||50)*peRef*ENG_SHARE;`\n"
        "   `out.compK=.030;` -> `out.compK=COMP_K;`\n"
        "   `out.compPrem=clamp(out.compK*Math.log((3+out.nEng)/(3+out.nEngRef)),-.08,.14);` -> (comment, then the line)\n" + COMP_LINE.replace("%", "%%") + "\n"
        "   `out.nPool=s.buyers*peRef*0.34;` -> `out.nPool=s.buyers*peRef*ENG_SHARE;`\n"
        "   `out.thinF=Math.min(1,(1-Math.exp(-out.nPool))/Math.max(1e-9,1-Math.exp(-out.nEngRef)));` -> `out.thinF=Math.min(1,pAnyOffer(out.nPool)/Math.max(1e-9,pAnyOffer(out.nEngRef)));`\n"
        "4. Replace the comment above out.nPool, exactly\n" + THIN_OLD + "\nwith\n" + THIN_NEW.replace("%", "%%") + "\n"
        "5. Labels: `Competition: ${r.nEng.toFixed(1)} engaged buyer${...}` -> `... expected offer${...}`; in eq_comp, `\\\\frac{3+n_{\\\\text{engaged}}}{3+n_{\\\\text{typical}}}` -> "
        "`\\\\frac{${COMP_H.toFixed(2)}+n_{\\\\text{offers}}}{${COMP_H.toFixed(2)}+n_{\\\\text{typical}}}`; in eq_comps, `n_{\\\\text{engaged}}` -> `n_{\\\\text{offers}}`.\n"
        "6. renderData(): the five exact edits D1-D5 in data_tab_text (nFit +2; the new fitted-table row; the two replaced ledger rows; the IND judgement row "
        "extended; nJudg unchanged).\n"
        "Verified on a patched copy with all six steps (" + pc + "): " + tests_summary.replace("%", "%%") + ".\n"
        "Effect: compPrem is identical everywhere (max |diff| %.1e). BUYERS and the buyer table are unchanged. Expected proceeds are unchanged whenever the pool is at "
        "or above typical (the worked example at 65 buyers: EVp $%.0f, PC %.4f, Omni score %d before and after). Below typical, P_C falls further. In the example at "
        "12 buyers thinF goes %.3f -> %.3f, PC %.3f -> %.3f and EVp $%.0f -> $%.0f. THE HEADLINE OMNI SCORE MOVES MUCH MORE THAN P_C SUGGESTS, because it is a "
        "percentile against peers marketed to a typical pool and that population is tight: median businesses (16 industries x SDE $0.2M/$1M/$4M) at half the typical "
        "pool go from %d-%d to %d-%d (median drop %.0f points); at 75%% from %d-%d to %d-%d; at 90%% from %d-%d to %d-%d; at a quarter from %d-%d to %d-%d. The example "
        "scores %s (old -> new, by buyers contacted %s). That score shift rests on the unidentified shape assumptions (selection would lower it further; less-than-"
        "proportional offers would raise it) and on the judgment typical pool IND buyers: with the medical typical pool at 40/50/60 the example at 40 buyers "
        "contacted scores %s (old build %s). The outreach intervention is worth more exactly where the pool is thin."
    ) % (comp_diff, ex_n["EVp"], ex_n["PC"], int(EXS.set_index("buyers").loc[65].score_new), t12o["thinF"], t12n["thinF"], t12o["PC"], t12n["PC"], t12o["EVp"], t12n["EVp"],
         h50[0], h50[1], h50[2], h50[3], h50[4], h75[0], h75[1], h75[2], h75[3], h90[0], h90[1], h90[2], h90[3],
         sc_rng[0.25][0], sc_rng[0.25][1], sc_rng[0.25][2], sc_rng[0.25][3],
         ", ".join("%d->%d" % (r_.score_old, r_.score_new) for r_ in EXS.itertuples()), "/".join(str(int(x)) for x in EXS.buyers),
         "/".join(str(x) for x in ind_sw[40]["new"]), "/".join(str(x) for x in ind_sw[40]["old"]))
    nr = sh.nEngRef.values
    pa_ = p_any(nr, R_NB); zm_ = nr / pa_; th_h = p_any(0.5 * nr, R_NB) / pa_; th_q = p_any(0.25 * nr, R_NB) / pa_
    lo_ = lambda v, d: math.floor((np.min(v) - d) * 100) / 100
    hi_ = lambda v, d: math.ceil((np.max(v) + d) * 100) / 100
    log("typical-pool ranges over industries x band centres: pAny %s, share1 %s, offers/closed deal %s, thinF(1/2) %s, thinF(1/4) %s"
        % (rng_(pd.Series(pa_)), rng_(sh.share1), rng_(pd.Series(zm_)), rng_(pd.Series(th_h)), rng_(pd.Series(th_q))))
    calib_tol = 0.40
    calib_ok = bool(np.all(np.abs(zt_ind_mean - obs.mean_lb.values) <= calib_tol) and np.all(np.abs(zt_ind_mean - m2_zt) <= 2 * m2_zt_se))
    sc1 = SC[SC.f == 1.0]
    same_at_typ = bool((sc1.score_old == sc1.score_new).all())
    test_invariants = [
        "Expected proceeds EVp never fall as s.buyers rises (fuzz: 400+ random businesses x pool sizes 1..960, relative tolerance 1e-9).",
        "0 < thinF <= 1. thinF is non-decreasing in s.buyers, and thinF === 1 whenever s.buyers >= I.buyers.",
        "nEngRef depends on neither s.buyers nor the quality inputs. thinF depends on no quality input (own/mgt/rec/fin/...).",
        "A median business (all quality inputs at peer medians) with s.buyers = I.buyers: |compPrem| < 5e-4 (exactly 0 at $1M earnings, existing test 7) and thinF === 1.",
        "compPrem equals the pre-change formula kappa*ln((3+X*0.34)/(3+Xref*0.34)) to 1e-12 for random businesses (COMP_H re-expression).",
        "COMP_K >= 0, and deeper pool => compPrem > 0, thin pool => compPrem < 0 (existing test 7).",
        ("CALIBRATION (catches a silent break when IND buyers, BUYERS fit functions, peRef or buyerMix change): at the five band centres "
         "(250k, 707k, 1.414M, 3.162M, 15.81M of Vbase, median businesses), the industry-mean implied offers per closed deal, mean over industries of "
         "nEngRef/pAnyOffer(nEngRef), is within +/-%.2f of IBBA's histogram means %s (now %s; %s), and within 2 bootstrap SE of the band-free fit %s (SE %s).")
        % (calib_tol, "/".join("%.2f" % x for x in obs.mean_lb.values), "/".join("%.2f" % x for x in zt_ind_mean), "passes" if calib_ok else "FAILS",
           "/".join("%.2f" % x for x in m2_zt), "/".join("%.2f" % x for x in m2_zt_se)),
        ("At a typical pool, at the five band centres and for every industry: pAnyOffer(nEngRef) is in [%.2f, %.2f]. The implied one-offer share, "
         "NB_R*p^NB_R*(1-p)/(1-p^NB_R) with p = NB_R/(NB_R+nEngRef), is in [%.2f, %.2f] (IBBA 0.26-0.48). Implied offers per closed deal rise with deal size within each industry.")
        % (lo_(pa_, .03), hi_(pa_, .03), lo_(sh.share1.values, .03), hi_(sh.share1.values, .03)),
        ("MODELS.fitted.competition has eng_share in [0.13, 0.23] and inside eng_share_spec_range (NB specifications only, now [%.3f, %.3f]), nb_r > 0 inside "
         "nb_r_spec_range, kappa in [0, 0.1], thin_half_pool_se[1] < 0.05, and the fields eng_share_se, eng_share_pln, cap_forgone_2x, refit_when, source; ENG_SHARE "
         "and NB_R are read from it, and eng_share_pln is never read by the model." % (nb_c_rng[0], nb_c_rng[1])),
        "A median business with half the typical pool gives thinF in [%.2f, %.2f] at every band centre and industry; a quarter gives [%.2f, %.2f]."
        % (lo_(th_h, .02), hi_(th_h, .02), lo_(th_q, .02), hi_(th_q, .02)),
        ("SCORE PIN (regression test so later edits to thinF are noticed; regenerate from the FINAL build by re-running fit/competition_buyers.py after the pending "
         "fits): the worked example {ind:'medical',rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:25,st:null,"
         "franchise:false,ask:3.24e6} gives thinF = %.4f (+/-1e-4), PC = %.4f (+/-1e-4) and omniScore = %d (+/-1) at the time of fitting; the old build gave thinF "
         "%.4f, score %d. At buyers:65 the score is %d in both builds.")
        % (ex25.thinF_new, ex25.PC_new, int(ex25.score_new), ex25.thinF_old, int(ex25.score_old), int(EXS.set_index("buyers").loc[65].score_new)),
        ("MEDIAN-BUSINESS PIN (regenerate with the score pin): median businesses (16 industries x SDE $0.2M/$1M/$4M, ask = REF_RATIO x V, buyers = round(f x "
         "I.buyers)) score %d-%d at f=0.5 (median drop %.0f vs the old build, +/-2) and %d-%d at f=0.75; at f=1 every one scores the same as the old build (%s now)."
         % (h50[2], h50[3], h50[4], h75[2], h75[3], "holds" if same_at_typ else "FAILS")),
        ("IND.buyers SENSITIVITY PIN (so a change to the judgment table is noticed): with the source override 'anchor:3.10, buyers:50,' -> 'anchor:3.10, buyers:40,' "
         "(and -> 60), the worked example at 40 buyers contacted scores %d (and %d), +/-1, against %d at the current 50; at 25 buyers %d / %d / %d. Regenerate with "
         "the score pin." % (ind_sw[40]["new"][0], ind_sw[40]["new"][2], ind_sw[40]["new"][1], ind_sw[25]["new"][0], ind_sw[25]["new"][1], ind_sw[25]["new"][2])),
        "Buyer table unchanged: str.mf 1.18 > adj.mf 1.14 > add.mf 1.12 > pep.mf 1.06 > fo.mf 1.02 > eta.mf 0.98 > ind.mf 0.90 > mbo.mf 0.86. With sizeFit = 1, the "
        "strategic-over-financial premium at $5-30M (the str/adj average against 0.64*pep + 0.36*add) is in [0.08, 0.18] (now %.3f)." % C_["full_presence"]["prem"],
        ("Data tab: renders with no NaN/Infinity/undefined (tests/browser.sweep.js); the fitted table contains the 'Buyer pool: expected offers' row; the IND "
         "judgement row mentions the typical pool for the thin-pool factor; nFit rises by exactly 2 and nJudg is unchanged."),
        "Existing test: a deeper pool does not raise P_C, and a thin pool closes less often (tests/model.test.js block 19).",
    ]
    caveats = (
        "REVISION 3 CHANGES (independent review). (1) 2023Q4 is now disclosed as the more inconsistent training quarter: its histogram, read from a multi-series "
        "line chart, has lowest possible means above the same report's average bars in all %d bands (by %.2f-%.2f; under $500K even the chart's largest shares at 1 "
        "and 2 offers give at least %.2f against a bar of %.2f). It is stated in MODELS.fitted.competition.source, here and on the Data tab. Added specifications: "
        "drop 2023Q4 and the 2025Q4 $5M+ cell (%.3f / r %.2f) and 2023Q1-Q3 only (%.3f / r %.2f); eng_share_spec_range widens to %.3f-%.3f. The recommended "
        "%.3f / %.2f stay (thinF moves at most %.3f across all specifications). (2) The bars comparison is caveated: the two IBBA series disagree wherever both exist "
        "(2023Q4 bars below the histogram bounds; the 2025Q4 table, now read from the raw report, above them in %d of 5 bands), and nothing band-specific rests on it. "
        "(3) The duplicate specification is removed: 'drop 2025Q4', '2023 histograms only' and the strictly temporal training set are one fit. %d distinct NB "
        "specifications remain. (4) eng_share_spec_range is NB-only; the Poisson-lognormal scale (%.3f with log-sd %.2f) is stored apart as eng_share_pln. (5) The "
        "thinF text now says the histograms lean toward q<1 (lower thinF) and that only the Pepperdine conflict argues for q=1. (6) Band homogeneity is called 'not "
        "rejected (approximate test)'; the n_closed weighting assumption is stated beside the deal-sampling SE, with a rounding-consistency check (largest n that "
        "reproduces the published percentages: %d of %d deals; %d of %d band-quarters consistent with n_closed; the 2023Q4 $5M+ chart read fits no n) and a refit on "
        "those weights (%.4f / r %.3f). (7) The judgment typical pool IND buyers is disclosed as what the penalty is measured against: the IND row of the judgement "
        "table (edit D5), a sentence in D2, the code comment, and a sensitivity pin (example at 40 buyers: %s for a typical pool of 40/50/60, against %s in the old "
        "build). (8) Quarter dependence: LR, AIC and BIC statements now carry quasi-likelihood versions with a dispersion of %.1f-%.1f. (9) The thinF sampling SE is "
        "reported and stored (thin_half_pool_se %.3f-%.3f). (10) The cap at 1 is labelled judgment in D2, the code comment and the method, with the NB-implied "
        "forgone rise (x%.2f-%.2f at twice the pool). (11) The Flippa watchers snapshot is cited as a non-transferable analog for beta. (12) The unconditional offer "
        "count in compPrem is noted in a §20 comment (conditioning on a sale would shrink thin-pool discounts %s). (13) The D2 score effect is labelled 'at the time of fitting', the median-business range and the IND "
        "sensitivity are pinned, and the implementation says to apply this after (or re-run it after) the pending fits.\n"
        "QUARTER DEPENDENCE, partly disputed. Reviewer 2 deflates every LR by a design effect of about 4.6 (the squared ratio of the quarter-jackknife to the "
        "deal-sampling SE of log ENG_SHARE; %.1f in this run). That is the upper end here: the Pearson X2/df on the band-quarter cells (1-5+) is only %.1f. The "
        "single-quarter ENG_SHAREs (%s) %s against their own deal-sampling SEs (robust bootstrap scale; Q %.1f, df %d, p=%.3f), so quarter dependence is real. "
        "The quasi-likelihood statements are therefore ranges: Poisson is rejected at either end (%s); the Pepperdine-constrained fit is %s; q=1 has %s. The "
        "ENG_SHARE SE (two-stage bootstrap over quarters) already allows for quarter dependence and is unchanged.\n"
        "REVISION 2 (kept). BUYERS str/adj mf are not changed: theta %.2f (SE %.2f) is within 1 SE of 1, the Pepperdine vintages straddle the current values, and the "
        "comparator choice (full presence vs the sizeFit-weighted displayed premium, z=%.1f) moves theta more than the data do. thinF is 'fitted scale, judgment shape'.\n"
        "DISAGREEMENTS, with evidence. (a) A calibration tolerance of +/-0.35 is too tight: the $2M-5M band sits %.2f above IBBA's lower-bound mean, so the invariant "
        "uses +/-%.2f plus 2 bootstrap SE of the band-free fit. (b) The Poisson-lognormal fits better (dAIC %.1f; quasi %.1f-%.1f; held-out log-lik %.3f vs %.3f) but "
        "is not adopted in the JS: it needs quadrature, its thinF differs by at most %.3f, and ENG_SHARE must stay paired with the NB r it was fitted with. (c) q: "
        "the revision-2 caveat argued the NB's q-gain was shape misfit. Both families now point the same way (NB optimum q=%.1f, PLN optimum q=%.1f), so the lean "
        "toward q<1 is reported as such; q=1 stays judgment because the evidence for q<1 is not robust to quarter dependence at the upper dispersion and conflicts with "
        "Pepperdine's base close rate under the NB. (d) The n_closed weights are kept as the baseline rather than replaced by the rounding-consistent n: the latter "
        "changes ENG_SHARE by %.4f, rests on a rounding rule, and cannot be computed for the line-chart quarter.\n"
        "TRANSFERABILITY. IBBA Market Pulse is the target population (brokered Main Street and lower-middle-market deals), so ENG_SHARE and NB_R need no shrinkage "
        "toward the judgment 0.34, which had no data behind it. What changes is a definition: an 'engaged' buyer is now one who makes an offer, and the displayed counts "
        "roughly halve. Flippa (watchers, auctions) and TRANBI are online or Japanese analogs: direction only (beta<1; r of the same order), zero weight. The tail cells "
        "(open 6+ / 10+, the 2023Q4 line-chart read) drive most of NB_R's specification range (%.2f-%.2f). The bootstrap clusters on only %d quarters (kappa on %d), "
        "so all SEs are approximate.\n"
        "ZERO CLASS AND DISPERSION. A listing with no offer never appears in closed-deal data, so P(no offer) is an extrapolation of the mixing family; under the NB it "
        "sits below Pepperdine's base close rate under $500K, which is incompatible with 'a sale needs at least one offer' read literally, so only the ratio P(any | "
        "pool)/P(any | typical) is used. NB_R is marginal heterogeneity across deals in a band (size, industry, marketing, quality), part of which the console already "
        "conditions on.\n"
        "KAPPA. The only within-market evidence is ecological: band-quarter averages, 8 quarters, asks that may move with demand (biasing toward 0), sample sizes imputed "
        "for %d of %d band-quarters (at half the imputed sizes the reliability falls to %.2f), and a slope that moves with quarter effects and band subsets. Flippa "
        "auctions (median ~$500, bids not bidders, unobserved start prices) get zero weight; TRANBI has no prices. kappa stays judgment with a stated bound.\n"
        "BUYER FACTORS. Pepperdine's premium item is a banker perception survey, not deal data; the 2016 figure is a decade old and the 2025 figure a secondary quote with "
        "an assumed n. GF Data and Stanford are averages or medians without dispersions. All display only (buyer table, 'pays most', star map), not EVp.\n"
        "SCOPE. No repo file other than fit/competition_buyers.py was modified. The script reads the console through /tmp/claude-0/fit5/harness.js and reproduces every "
        "number here (seeded; revision-3 draws use a separate seed so revision-2 numbers are unchanged)."
    ) % (5, SER["gap_2023"][0], SER["gap_2023"][1], SER["min_feasible_2023"], SER["min_bar_2023"], sp_d23c[0], sp_d23c[1], sp_q13[0], sp_q13[1],
         nb_c_rng[0], nb_c_rng[1], ENG, R_NB, spec_maxdiff, 5 - SER["n_incons_2025"], n_spec_nb, pln_row.c, pln_row.dispersion,
         round(REV3["n_rc_total"]), round(REV3["n_closed_total"]), REV3["n_rc_consistent"], n_bq, sp_rc[0], sp_rc[1],
         "/".join(str(x) for x in ind_sw[40]["new"]), "/".join(str(x) for x in ind_sw[40]["old"]), REV3["phi_lo"], REV3["phi_hi"],
         REV3["thin_se_half"][0], REV3["thin_se_half"][1], REV3["cap2"][0], REV3["cap2"][1], cond_txt,
         REV3["phi_hi"], REV3["phi_lo"], "/".join("%.3f" % x for x in REV3["sq_c"]), "differ more than sampling allows" if REV3["sq_Q_p"] < 0.05 else "do not differ significantly",
         REV3["sq_Q"], len(qs) - 1, REV3["sq_Q_p"], qtxt(ql_pois5), qtxt(ql_con), qtxt(qn),
         C_["theta"], C_["theta_se"], C_["display_premium_z"], float(zt_ind_mean[3] - obs.mean_lb.values[3]), calib_tol, 2 * (fits["M5"][1] - pln_row.nll),
         ql_pln["lr_lo"], ql_pln["lr_hi"], pln_loqo, cvs["recommended_M5"], float(SPI.loc["Poisson-lognormal mixing family", "max_abs_thin_diff_vs_rec"]),
         REV3["q_opt_nb"], REV3["q_opt_pln"], abs(sp_rc[0] - c_hat),
         nb_r_rng[0], nb_r_rng[1], len(qs), K8["quarters"], KF["n_imputed"], KF["n_rows"], KF["n_sensitivity"][0.5]["reliability"])
    result = dict(name="competition_buyers", script="/home/user/last-minute/fit/competition_buyers.py", parameters=params, not_identified=not_identified,
                  implementation=implementation, data_tab_text=data_tab_text, test_invariants=test_invariants, caveats=caveats)
    with open(os.path.join(OUT, "RESULT.json"), "w") as f:
        json.dump(result, f, indent=1)
    log("\nwrote", os.path.join(OUT, "RESULT.json"))

    with open(os.path.join(OUT, "fit_summary.json"), "w") as f:
        json.dump(res, f, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    with open(os.path.join(OUT, "run_log.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    return res


if __name__ == "__main__":
    main()
