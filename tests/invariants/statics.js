#!/usr/bin/env node
/* Comparative-statics invariants for The Omni Method console (the "statics" lens).

   For every input and every headline output, the direction the model's own logic (code comments, MODELS notes, the
   Data tab, AUDIT.md) or unambiguous business logic says the output must move, tested by one-input-at-a-time
   perturbations from seeded random base states (page-reachable: the rail's slider ranges and select values, typed money
   from $10k to $5B of revenue, every ask from 0.1x to 20x value; plus the continuous transferability values the
   interventions produce), corners, adversarial states near every threshold, and fine scans. It goes beyond
   tests/fuzz.test.js: that suite checks value and proceeds against quality, P_C and proceeds against the ask and the
   pool; this one checks the scores, the categories, time, risk, the price distribution, the optimisers, the
   intervention and sensitivity rows, the inputs that must NOT move an output, and size.

   Usage: node tests/invariants/statics.js [appRoot=the repository] [--n=300] [--seed=20261013] [--browser] [--browser-only]
   Prints one line per invariant: "PASS <name> cases=<n>" or "FAIL <name> cases=<n> fails=<k> first=<counterexample>".
   --json=<file> also writes every invariant (statement, source, cases, fails, first) as JSON.
   Exit code 1 if any invariant fails. Model-only run at the defaults: about 3 minutes (--n=900: about 9);
   --browser adds about 3 minutes (Playwright, chromium, reduced motion, 1440x900).
   Expectations corrected during the audit are recorded in each declaration's source string (scale with the ask held at
   a fixed multiple of value; earnings vs P_C only from a typical pool; walk-away vs pool only at theta = 0; the two
   optimiser cards compared to 0.01% of value). */
"use strict";
const path=require("path"), fs=require("fs");
const args=process.argv.slice(2);
const ROOT=path.resolve(args.find(a=>!a.startsWith("--"))||path.join(__dirname,"..",".."));
const opt={}; for(const a of args.filter(a=>a.startsWith("--"))){ const i=a.indexOf("="); opt[i<0?a.slice(2):a.slice(2,i)]=i<0?true:a.slice(i+1); }
const N=+(opt.n||300);
const A=require(path.join(ROOT,"tests","load.js"));
const T0=Date.now();

/* ---------------- registry ---------------- */
const INV=new Map(); let nState=0; const TIME={}; const timed=(k,f)=>{ const t=Date.now(); try{ return f(); } finally { TIME[k]=(TIME[k]||0)+Date.now()-t; } };
function def(name,statement,source){ INV.set(name,{name,statement,source,cases:0,fails:0,first:null}); }
function ok(name,cond,ctx){ const o=INV.get(name); if(!o) throw new Error("undeclared invariant "+name);
  o.cases++; if(!cond){ o.fails++; if(o.first===null) o.first=typeof ctx==="function"?ctx():ctx; } }
const fmt=v=>JSON.stringify(v,(k,x)=>typeof x==="number"?(isFinite(x)?+x.toPrecision(6):String(x)):x);
const cx=(s,extra)=>fmt({ind:s.ind,rev:s.rev,ern:s.ern,ask:s.ask,buyers:s.buyers,grw:s.grw,gm:s.gm,rec:s.rec,cc:s.cc,ret:s.ret,plt:s.plt,
  own:s.own,mgt:s.mgt,fin:s.fin,yrs:s.yrs,st:s.st,franchise:s.franchise,budget:s.budget,lamT:s.lamT,theta:s.theta,...(extra||{})});

/* ---------------- seeded sampler of page-reachable states ---------------- */
let seed=(+(opt.seed||20261013))%2147483647||1;
const rnd=()=>{ seed=(seed*16807)%2147483647; return (seed-1)/2147483646; };
const pick=a=>a[Math.floor(rnd()*a.length)];
const U=(a,b)=>a+rnd()*(b-a);
const logU=(lo,hi)=>Math.exp(Math.log(lo)+rnd()*(Math.log(hi)-Math.log(lo)));
const INDS=Object.keys(A.IND), STS=[null,...Object.keys(A.MODELS.risk.state_effects)];
const SEL={own:[.95,.72,.42,.14],mgt:[.08,.36,.66,.92],fin:[.14,.45,.74,.96]};          /* the rail's select options */
const SL={grw:[-.25,.70],gm:[.12,.97],rec:[0,1],cc:[.01,.70],ret:[.45,.99],plt:[.05,.95]};   /* slider ranges; typed values are held to them */
const FR={own:[.02,.99],mgt:[.02,.99],fin:[.02,1]};                                        /* FIELD_RANGE: what interventions can produce */
const sl=k=>{ const [a,b]=SL[k], u=rnd(); return u<.06?a:u<.12?b:U(a,b); };
const typOf=s=>A.IND[s.ind].buyers||50;
function sample(){
  const ind=pick(INDS), typ=A.IND[ind].buyers;
  const rev=rnd()<.88?logU(1e5,2e8):logU(1e4,5e9);
  const u=rnd(); let ern=u<.05?Math.max(1e3,.02*rev):u<.10?.92*rev:rev*U(.02,.85);
  ern=Math.max(1e3,Math.min(ern,.92*rev));
  const tr=k=>rnd()<.75?pick(SEL[k]):U(FR[k][0],FR[k][1]);
  const b=rnd(), buyers=b<.55?5*(1+Math.floor(rnd()*120)):b<.75?Math.max(5,Math.min(600,typ+Math.round(U(-6,6))))
    :b<.85?5:b<.92?600:Math.max(5,Math.round(U(5,typ)));
  const s={ind,st:pick(STS),franchise:rnd()<.25,rev,ern,grw:sl("grw"),gm:sl("gm"),rec:sl("rec"),cc:sl("cc"),ret:sl("ret"),plt:sl("plt"),
    own:tr("own"),mgt:tr("mgt"),fin:tr("fin"),yrs:1+Math.floor(rnd()*12),buyers,
    budget:rnd()<.15?0:rnd()<.85?U(0,Math.max(2e5,.15*rev)):logU(1e3,1e9),
    lamT:rnd()<.2?0:50*Math.floor(rnd()*81),theta:rnd()<.1?0:rnd()<.1?1:Math.round(rnd()*100)/100};
  const V=A.model({...s,ask:1}).V, a=rnd();
  const rho=a<.6?logU(.4,2.5):a<.7?U(.97,1.03):a<.8?U(1.45,1.55):a<.9?logU(.1,.4):logU(2.5,20);
  s.ask=Math.min(1e11,Math.max(1e3,V*rho));
  return s;
}
/* adversarial states: every threshold the model has (hinge knot and cap, the search-fund window edges, the size-ref
   clamps, the channel ramp ends, the 7(a) loan cap, a typical pool, the value and RHO_MAX asks) */
function adversarial(i){
  const s=sample(), kind=i%8;
  if(kind===0) s.ern=pick([1.5e5,3e6,3.2e6,8.32e6,1.12e7,1.8e5,6e5]);
  if(kind===1){ const T=pick([1e6,5e6,5.9e6]); const V=A.model({...s,ask:1}).V; s.ern*=T/V; }
  s.ern=Math.max(1e3,s.ern); if(s.ern>.92*s.rev) s.rev=s.ern/U(.1,.9);
  if(kind===2) s.buyers=Math.max(5,typOf(s)+pick([-1,0,1,-3,3]));
  const V=A.model({...s,ask:1}).V;
  if(kind===3) s.ask=V*pick([1,1+1e-6,1-1e-6,1.5,1.2,1.1]);
  if(kind>=4) s.ask=V*logU(.4,2.5);
  return s;
}
const BETTER={rec:s=>Math.min(1,s.rec+.08),cc:s=>Math.max(.005,s.cc-.04),ret:s=>Math.min(.99,s.ret+.03),plt:s=>Math.max(.02,s.plt-.07),
  grw:s=>Math.min(1.5,s.grw+.04),gm:s=>Math.min(.97,s.gm+.04),own:s=>Math.max(.02,s.own-.1),mgt:s=>Math.min(.99,s.mgt+.1),fin:s=>Math.min(1,s.fin+.1)};
const QK=Object.keys(BETTER);
const PS=[.02,.1,.25,.5,.75,.9,.98];
const CATS=Object.keys(A.model({ind:"prof",rev:1e6,ern:2e5,ask:6e5,grw:.07,gm:.55,rec:.45,cc:.16,ret:.84,plt:.4,own:.62,mgt:.42,fin:.55,yrs:6,buyers:52}).cats);
const ge=(b,a,rel)=>b>=a-(rel||1e-12)*Math.max(1,Math.abs(a));
const le=(b,a,rel)=>b<=a+(rel||1e-12)*Math.max(1,Math.abs(a));
const same=(b,a)=>b===a||Math.abs(b-a)<=1e-12*Math.max(1,Math.abs(a));
const prep=s=>{ const t={...s}; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,t.theta,t.lamT); return t; };

/* ================= declarations ================= */
/* R: what each output must NOT read */
def("value-reads-no-process-or-preference-input","Model value, the fitted value, the quality percentile and the multiple are unchanged by the buyers contacted, years of history, state, franchise, cost of delay, share kept and budget",
  "model(): 'E[V|X] is what the business supports; it cannot depend on what is asked'; sensitivity(): 'the ask and the buyer pool cannot move it'; Data tab: years feed only the category bars and the unused judgment panels; z.buy is not a quality_band dimension");
def("sale-outputs-read-no-preference-or-risk-input","P_C, the price distribution, expected proceeds, cash share, both time figures and the Omni score are unchanged by years of history, state, franchise, cost of delay, share kept and budget",
  "Model I/III/§23 read only size, the ask, the pool and the quality position; Data tab: 'Years of clean history feeds only the category bars and the judgment panels that are not used'");
def("time-reads-only-size-and-ask","Median and mean time to close are unchanged by the buyers contacted, and by quality at an ask at or below value",
  "Model III comment: 'nothing here has covariates beyond deal size. (The ask enters only in model(), through timeMult)'");
def("risk-reads-only-value-industry-state-franchise","Survival risk (10-year, 5-year, expected loss) is unchanged by the ask, buyers, years, cost of delay, share kept and budget, and equals fitRisk at model value",
  "fitRisk(price,naicsKey,rate,jobs,franchise,st); Model V: 'Staffing is not used'; fuzz checks only the ask and jobs");
def("cash-share-reads-only-deal-size","The cash-at-close share reads only the fitted value before quality positioning: unchanged by quality, the ask, buyers or preferences",
  "model(): out.cashShare=bandInterp(out.Vbase, ibba_cash_at_close.by_band)");
def("categories-read-only-their-inputs","No category reads cost of delay, share kept, budget, state or franchise; of the ask only Risk profile (never rising with it); of the pool only Buyer attractiveness (never falling with it)",
  "§21 category formulas (xPrice only in Risk profile, z.buy only in Buyer attractiveness)");
def("business-score-reads-no-ask-or-preference","The business score's own figure (the profile at the proceeds-optimal ask and at least a typical pool) is unchanged by the entered ask, cost of delay, share kept and budget",
  "businessScore(): 'it takes the seller's process decisions out: the ask (priced at the proceeds optimum) AND the buyer pool'; render: s.rhoSell 'reads neither theta nor the cost of delay'");
def("proceeds-card-reads-no-preference","The 'Maximizing expected proceeds' card (selected changes and net) is unchanged by the cost of delay and the share kept",
  "optimize(): the proceeds objective reprices to s0.rhoSell = bestRatio(s,0,0); model.test #13 checks this only at the framework example");
/* Q: quality inputs, one at a time in the 'better' direction */
def("omni-score-monotone-in-quality","Improving any one of the nine quality inputs never lowers the Omni score at the same ask",
  "omniScore = percentile of expected proceeds in a population keyed on industry, earnings and revenue only (refDistAt); expected proceeds never fall with quality");
def("category-scores-monotone-in-quality","Improving any one quality input, or adding a year of clean history, never lowers any of the nine category scores or their mean",
  "§21: every z enters each category formula with the sign of 'better' (own, cc, plt negated)");
def("business-score-monotone-in-quality","Improving any one quality input never lowers the business score",
  "businessScore: the percentile of expected proceeds at the proceeds optimum (an envelope of a function non-decreasing in quality)");
def("pc-monotone-in-quality-at-fixed-ask","Improving any one quality input never lowers the closing probability at the same ask",
  "fitClose: base(deal size before quality) x (1 - penalty(gap to the quality-positioned value)) x thin-pool factor (no quality input); AUDIT_FINDINGS R2-11");
def("pc-reads-no-quality-at-fair-ask","At an ask at or below model value (before and after), quality does not move the closing probability",
  "gapPenalty: 'pricing at or below model value carries no price penalty'; Data tab R2-11 wording");
def("time-monotone-in-quality-at-fixed-ask","Improving any one quality input never lengthens the median or mean time to close, and never lowers the share closed by 90, 180 or 365 days, at the same ask",
  "fuzz comment 'a better business is never slower at a fixed ask' (fuzz tests only rec+mgt above 1.2x); timeMult reads ask/V");
def("price-distribution-monotone-in-quality","At the same ask, improving any one quality input never lowers any quantile of the price if it closes, its median or its mean",
  "model() §23: P(W) increasing in W ('A's elasticity is < 1'), the ceiling reads softMin(ask,1.5V), the premium never falls with engagement");
def("risk-never-rises-with-quality","Improving any one quality input never raises the 5-year or 8-year charge-off risk; the 10-year risk and the expected loss rise only where the fitted tail for years 9-10 rises with the note's size, and the 10-year risk by no more than the tail does (page path: no rate entered)",
  "economics: a better-run business is not a worse credit; in the model quality reaches risk only through a larger loan at a lower table spread. Since October 2026 years 9-10 are fitted by note size (fit/sba_tail_factor.py: larger acquisition notes are more often 10-year notes still open at year 8), so the 10-year figure is p8 x tail(note) and may rise where the tail rises faster than p8 falls (on the page path, notes from about $0.60M to the $1.05M band centre)");
def("competition-premium-monotone","The competition premium never falls with more buyers contacted or with any one better quality input",
  "§20: 'deeper than usual earns a premium'; offers = buyers x engagement x ENG_SHARE, and every archetype's fit is non-decreasing in quality");
def("confidence-monotone-in-reporting-and-history","The analysis confidence does not move with financial reporting or years of clean history (since October 2026 it is the fitted chance of landing within 25% of the fitted value, which reads neither)",
  "confidenceOf (fit/confidence_accuracy.py): p reads size, the margin's distance from typical, comparables depth and the extrapolation; the hand-set index it replaced weighted reporting and years");
def("walkaway-monotone-in-quality","Improving any one quality input never lowers the walk-away (utility-optimal) ask, as a ratio to value or in dollars, beyond bestRatio's resolution (2e-4 of value)",
  "U/V = P_C E[P]/V + (1-P_C) theta - lambda E[T]/V: quality scales V (shrinking the delay term) and raises the premium; economics: a better business can ask more");
def("proceeds-optimum-flat-in-quality","The proceeds-optimal ask ratio moves by under 0.005 between the worst and the best quality profile, and never falls as quality rises",
  "refDistAt: 'The optimum depends on the gap curve and the ceiling, not on quality, so one ratio solved on the median profile serves the whole population'");
/* S: size */
def("value-monotone-in-scale","At a fixed margin, model value and the fitted value never fall as revenue and earnings grow together (fine scans over $10k-$5B of revenue)",
  "economics: same margin and quality, bigger business; fitValue hinge comment: the multiple goes flat above the cap rather than falling");
def("value-monotone-in-revenue-at-fixed-earnings","At fixed earnings, model value never falls as revenue rises",
  "fitted coefficients: ln_gross 0.471 exceeds margin_c 0.410 x margin (refDistAt: 'the fitted value prices revenue (+0.47 on its log)')");
def("scale-at-fixed-ask-ratio-raises-proceeds","Scaling revenue and earnings up 5% with the ask held at the same multiple of value never lowers value, the price if it closes or expected proceeds",
  "economics. Corrected from 'ask scaled with earnings': below $150k of SDE value scales by about 0.7 (the Data tab's documented U-shaped multiple), so a proportional ask becomes relatively more overpriced");
def("time-at-fair-ask-monotone-in-size","At an ask at or below value, the median and the mean time to close never fall as the business scales up",
  "fitTiming: band medians rise with deal size; E[T]/t_med falls with the shape beta, but not fast enough to reverse it (Data tab model III)");
def("base-close-rate-monotone-in-size","At a fair ask and a typical or deeper pool, the closing probability never falls as the business scales up",
  "fitClose: base interpolated in ln(size) from the broker 0.608 at $1M to the intermediated 0.697 at $5M");
def("earnings-raise-pc-and-proceeds-deep-pool","At fixed revenue and ask, with a typical or deeper pool, more earnings never lower the closing probability, the price if it closes or expected proceeds",
  "economics: same ask, more profit. Corrected scope: below a typical pool the thin-pool factor reads the typical pool's size-dependent engagement (search-fund window, SDE $3.2M-$8.3M), which the BUYERS ledger row documents");
def("risk-non-increasing-in-size","Along fine scale paths (fixed margin, $10k-$5B of revenue, every industry) the 5-year and 8-year charge-off risk never rise as the business grows; the 10-year risk and the expected loss never rise except where the fitted tail for years 9-10 rises with the note's size, and the 10-year risk then by no more than the tail does",
  "Model V: larger loans are charged off less often through month 72; the table spread never rises with loan size; severity barely moves with size (b_size +0.0104, se 0.0397; Data tab: 'Size matters little'); the month-72 size reversal never overturns the 8-year figure. Since October 2026 the tail is fitted by note size (MODELS.risk.tail.by_band), so the 10-year figure may rise slightly from a note of about $0.60M, where the table spread stops falling, to the $1.05M band centre. tests/model.test.js allows 1% per ~10% step");
def("franchise-never-raises-risk","A franchise never raises the 10-year or 5-year charge-off risk or the expected loss, and moves nothing else",
  "MODELS.risk: franchise lowers the charge-off hazard (-0.0167) and raises the payoff hazard (+0.1256), so both lower the cumulative charge-off");
def("state-label-sign-matches-effect","Each state dropdown label's sign is the sign of that state's fitted charge-off effect",
  "OMNI_STLAB labels each state with fitRisk(...,state).p - fitRisk(...,null).p; state_effects multiply the charge-off hazard");
/* A: the ask and the pool */
def("quantiles-monotone-in-ask","A higher ask never lowers any quantile of the price if it closes",
  "§23 comment: 'the distribution is monotone in the ask' (fuzz checks only the mean)");
def("cap-share-non-increasing-in-ask","A higher ask never raises the share of closings at the ask ceiling",
  "§23: P(W)/ceiling falls with the effective ask because A's elasticity is < 1");
def("prices-monotone-in-buyers","More buyers contacted never lower any quantile of the price if it closes or its mean",
  "§20: the competition premium never falls with the pool (fuzz checks only P_C, thinF and proceeds)");
def("proceeds-unimodal-in-ask","Expected proceeds have a single peak in the ask (0.4x-2.5x value), so the Omni score never rises moving away from the proceeds optimum",
  "hero caption: the ask 'costs' proceeds on either side of the optimal ask; bestRatio's scan assumes one peak");
def("business-score-monotone-in-buyers","The business score never falls as more buyers are contacted, across the whole 5-600 range",
  "businessScore comment: 'the thin-pool factor and the competition premium never fall as buyers rise' (fuzz checks only below a typical pool)");
/* O: optimisers */
def("walkaway-monotone-in-theta","The walk-away ask never falls as the share of value kept on failure rises (theta in 5% steps)",
  "U = E[proceeds] + (1-P_C) theta V - lambda E[T] has increasing differences in (ask, theta) because P_C never rises with the ask");
def("walkaway-monotone-in-delay-cost","The walk-away ask never rises with the cost of delay",
  "optNote: 'a cost of delay can pull the walk-away ask BELOW'; E[T] never falls with the ask");
def("walkaway-not-below-proceeds-optimum-without-delay","With no cost of delay the walk-away ask is never below the proceeds-optimal ask, and the note never blames a cost of delay",
  "optNote 'lower' branch: 'The cost of delay pulls the second figure below the proceeds-maximising price'");
def("proceeds-optimum-monotone-in-buyers","The proceeds-optimal ask ratio never falls as more buyers are contacted",
  "economics; the thin-pool factor multiplies P_C (cancels in the argmax) and the premium raises the share of slices at the ceiling");
def("walkaway-monotone-in-buyers","With no value kept on failure (theta = 0), the walk-away ask ratio never falls as more buyers are contacted, whatever the cost of delay",
  "U = P_C E[P] - lambda E[T]: more buyers raise both the level and the ask-elasticity of P_C E[P], so the delay charge weighs less. Corrected from all theta: with theta > 0 a deeper pool also raises what a failed sale forfeits (E[P] - theta V), which can favour a lower ask (home, $175k SDE, theta 0.96, 215 -> 225 buyers: 1.2168 -> 1.2165)");
def("optimizer-monotone-in-budget","A larger budget never lowers the optimised programme: proceeds-card net and expected proceeds, utility-card U",
  "optimize(): the feasible set only grows with the budget");
def("optimizer-cards-optimal-on-own-objective","Each optimiser card is at least as good as the other card on its own objective, to 0.01% of value: the proceeds card on net proceeds, the utility card on U; and the proceeds-optimal listing card never shows lower expected proceeds than the walk-away card",
  "card titles 'Maximizing expected proceeds' / 'Maximizing the seller's overall outcome'. Tolerance note: exactly, either card can trail the other by up to about 1e-5 of value, because both reprice to a ratio solved for the business before the changes (immaterial, below display rounding)");
def("optimizer-lift-at-least-spend","The proceeds card's lift over today's expected proceeds is at least what it spends",
  "card: 'Lifts expected proceeds X over today's Y, before the C spent'; doing nothing is always feasible (AUDIT #5)");
def("optimizer-utility-monotone-in-theta-and-delay","The utility card's U never falls with the share kept and never rises with the cost of delay",
  "eq_u: U = P_C E[P] + (1-P_C) theta V - lambda (E[T]+T_exec) - C");
def("walkaway-note-directions","The note under the listing cards: a 'higher' walk-away ask is never more likely to close, never faster and never a smaller cheque; a 'lower' one is never less likely to close and never slower",
  "optNote texts ('gives up ... closing probability ... takes about N days longer ... for a bigger cheque' / 'more likely to close and closes ... sooner')");
def("hero-caption-losses-non-negative","The hero caption's ask loss and pool loss (and their points) are never negative",
  "render o_cap: 'The ask costs X% of expected proceeds and N points'; 'Contacting n buyers ... costs a further X%'");
/* I: interventions and sensitivity */
def("intervention-quality-rows","Each pure-quality intervention (QoE, SOPs, contracts, diversification, retention, channels) never lowers value or expected proceeds, leaves P_C unchanged and has Net days equal to its execution days",
  "intnote: 'the price gap is the same in every row; the closing probability still moves with the buyer pool ... and with deal size (changes to earnings)'");
def("intervention-outreach-row","Buyer outreach never moves value and never lowers expected proceeds or P_C",
  "intnote; value reads no pool");
def("intervention-earnings-rows-raise-value","The pricing/COGS and sales-capacity rows (gross margin or growth up, earnings x1.06 / x1.04) never lower value",
  "INTERV effects are improvements; fuzz: more earnings never lowers value");
def("intervention-reprice-row","The reprice row never moves value and never lowers expected proceeds",
  "INTERV reprice: eff {}; it reprices to the proceeds optimum");
def("intervention-gain-monotone-in-own-size","A stronger intervention never gains less (contracts x2, deeper diversification, wider outreach), a dearer GM never adds more value, a costlier change never nets more, a slower one adds exactly its extra days, and the optimiser is never worse off when a change gets stronger or cheaper",
  "INTERV typed effects compose deterministically; ROI = (dE - C)/C; Net days = execution days + change in E[T]");
def("sensitivity-quality-rows-non-negative","Every quality row of the sensitivity panel (each labelled as an improvement) shows a non-negative change in value, expected proceeds and P_C",
  "SENS labels ('Less customer concentration', 'Owner independence' ...) with inv flags; eq_d");
def("sensitivity-process-rows","The ask row (5% lower) never moves value and never lowers P_C; the buyer row never moves value and never lowers proceeds or P_C",
  "sensitivity(): 'the ask and the buyer pool cannot move it [V]'; R5-2 step rows");
def("value-gap-non-negative","The value gap tile (the pruned set of changes) is never negative",
  "render: 'only the changes that add value'; pruning keeps a change only if removing it lowers value");
/* F: fine scans */
def("fine-scan-quality","Scanning each quality input across its whole range in 1% steps: value, P_C, expected proceeds and the Omni score never fall, and time never rises, at a fixed ask",
  "as the quality invariants above, at every step instead of one");
def("fine-scan-earnings","Scanning earnings at fixed revenue from 0.5% to 92% margin in 0.5% steps: value and the fitted value never fall",
  "fuzz 'more earnings never lowers value' (5% steps only)");

function runModel(){
/* ================= main random loop ================= */
const PROC=s=>{ const st2=STS.filter(x=>x!==s.st); return {
  yrs:{...s,yrs:s.yrs===12?1:12}, st:{...s,st:pick(st2)}, franchise:{...s,franchise:!s.franchise},
  lamT:{...s,lamT:s.lamT===4000?0:4000}, theta:{...s,theta:s.theta>.5?0:1}, budget:{...s,budget:s.budget>1e6?0:5e6}}; };
const states=[]; for(let i=0;i<N;i++) states.push(i%5===4?adversarial(i):sample());
for(let i=0;i<states.length;i++){
  const s=states[i], r=A.model(s), sc=A.omniScore(r), typ=typOf(s);
  nState++;
  let _t=Date.now(); const lap=k=>{ const n=Date.now(); TIME[k]=(TIME[k]||0)+n-_t; _t=n; };
  /* ---- R ---- */
  const pv=PROC(s);
  for(const k in pv){ const r2=A.model(pv[k]);
    ok("value-reads-no-process-or-preference-input",same(r2.V,r.V)&&same(r2.Vbase,r.Vbase)&&r2.qPct===r.qPct&&same(r2.M,r.M),()=>cx(s,{k,a:r.V,b:r2.V}));
    const outs=["PC","Vreal","Vmean","EVp","cashShare","tMed","tMean","capShare","thinF"];
    ok("sale-outputs-read-no-preference-or-risk-input",outs.every(o=>same(r2[o],r[o]))&&A.omniScore(r2)===sc,()=>cx(s,{k,diff:outs.filter(o=>!same(r2[o],r[o]))}));
    if(k!=="st"&&k!=="franchise") ok("risk-reads-only-value-industry-state-franchise",r2.risk.p===r.risk.p&&r2.risk.p5===r.risk.p5&&r2.risk.expLoss===r.risk.expLoss,()=>cx(s,{k,a:r.risk.p,b:r2.risk.p}));
    if(k==="lamT"||k==="theta"||k==="budget"||k==="st"||k==="franchise") ok("categories-read-only-their-inputs",CATS.every(c=>r2.cats[c]===r.cats[c]),()=>cx(s,{k}));
  }
  { const rb=A.model({...s,buyers:s.buyers===600?5:600}), ra=A.model({...s,ask:s.ask*1.37});
    ok("value-reads-no-process-or-preference-input",same(rb.V,r.V)&&rb.qPct===r.qPct,()=>cx(s,{k:"buyers",a:r.V,b:rb.V}));
    ok("time-reads-only-size-and-ask",same(rb.tMed,r.tMed)&&same(rb.tMean,r.tMean),()=>cx(s,{k:"buyers",a:r.tMed,b:rb.tMed}));
    for(const [k,x] of [["ask",ra],["buyers",rb]]) ok("risk-reads-only-value-industry-state-franchise",x.risk.p===r.risk.p&&x.risk.expLoss===r.risk.expLoss,()=>cx(s,{k}));
    const fr=A.fitRisk(r.V,s.ind,A.sbaRate(r.V),null,!!s.franchise,s.st||null);
    ok("risk-reads-only-value-industry-state-franchise",fr.p===r.risk.p&&r.rate===A.sbaRate(r.V),()=>cx(s,{a:r.risk.p,b:fr.p}));
    for(const [k,x] of [["ask",ra],["buyers",rb]]) ok("cash-share-reads-only-deal-size",x.cashShare===r.cashShare,()=>cx(s,{k}));
    /* only Risk profile reads the ask, never rising with it; only Buyer attractiveness reads the pool, never falling with it */
    ok("categories-read-only-their-inputs",CATS.every(c=>c==="Risk profile"?ra.cats[c]<=r.cats[c]:ra.cats[c]===r.cats[c]),()=>cx(s,{k:"ask",a:r.cats,b:ra.cats}));
    const up=s.buyers<600, rbu=up?A.model({...s,buyers:Math.min(600,s.buyers*2)}):null;
    if(up) ok("categories-read-only-their-inputs",CATS.every(c=>c==="Buyer attractiveness"?rbu.cats[c]>=r.cats[c]:rbu.cats[c]===r.cats[c]),()=>cx(s,{k:"buyers",a:r.cats,b:rbu.cats}));
  }
  lap('base+R');
  /* ---- Q: one quality input at a time ---- */
  for(const k of QK){ const v=BETTER[k](s); if(v===s[k]) continue;
    const s2={...s,[k]:v}, r2=A.model(s2);
    ok("omni-score-monotone-in-quality",A.omniScore(r2)>=sc,()=>cx(s,{k,v,a:sc,b:A.omniScore(r2)}));
    ok("category-scores-monotone-in-quality",CATS.every(c=>r2.cats[c]>=r.cats[c])&&r2.catMean>=r.catMean-1e-12,()=>cx(s,{k,v,a:r.cats,b:r2.cats}));
    ok("pc-monotone-in-quality-at-fixed-ask",r2.PC>=r.PC-1e-15,()=>cx(s,{k,v,a:r.PC,b:r2.PC}));
    if(s.ask<=Math.min(r.V,r2.V)) ok("pc-reads-no-quality-at-fair-ask",Math.abs(r2.PC-r.PC)<1e-15,()=>cx(s,{k,v,a:r.PC,b:r2.PC}));
    if(s.ask<=Math.min(r.V,r2.V)) ok("time-reads-only-size-and-ask",same(r2.tMed,r.tMed)&&same(r2.tMean,r.tMean),()=>cx(s,{k,v,a:r.tMed,b:r2.tMed}));
    ok("time-monotone-in-quality-at-fixed-ask",le(r2.tMed,r.tMed)&&le(r2.tMean,r.tMean)&&r2.t90>=r.t90-1e-12&&r2.t180>=r.t180-1e-12&&r2.t365>=r.t365-1e-12,()=>cx(s,{k,v,a:r.tMed,b:r2.tMed}));
    ok("price-distribution-monotone-in-quality",PS.every(p=>ge(r2.q(p),r.q(p)))&&ge(r2.Vreal,r.Vreal)&&ge(r2.Vmean,r.Vmean),()=>cx(s,{k,v,a:r.Vmean,b:r2.Vmean}));
    ok("risk-never-rises-with-quality",le(r2.risk.p5,r.risk.p5)&&le(r2.risk.p8,r.risk.p8)
       &&(r2.risk.tail>r.risk.tail?r2.risk.p<=r.risk.p*(r2.risk.tail/r.risk.tail)*(1+1e-12):le(r2.risk.p,r.risk.p)&&le(r2.risk.expLoss,r.risk.expLoss)),
       ()=>cx(s,{k,v,a:r.risk.p,b:r2.risk.p,tail:[r.risk.tail,r2.risk.tail]}));
    ok("competition-premium-monotone",r2.compPrem>=r.compPrem-1e-15,()=>cx(s,{k,v,a:r.compPrem,b:r2.compPrem}));
    ok("cash-share-reads-only-deal-size",r2.cashShare===r.cashShare,()=>cx(s,{k}));
  }
  { if(s.yrs<12){ const ry=A.model({...s,yrs:s.yrs+1});
      ok("category-scores-monotone-in-quality",CATS.every(c=>ry.cats[c]>=r.cats[c]),()=>cx(s,{k:"yrs",a:r.cats,b:ry.cats}));
      ok("confidence-monotone-in-reporting-and-history",ry.conf===r.conf,()=>cx(s,{k:"yrs",a:r.conf,b:ry.conf})); }
    if(s.fin<1){ const rf=A.model({...s,fin:Math.min(1,s.fin+.1)}); ok("confidence-monotone-in-reporting-and-history",rf.conf===r.conf,()=>cx(s,{k:"fin",a:r.conf,b:rf.conf})); }
    if(s.buyers<600){ const rb=A.model({...s,buyers:Math.min(600,s.buyers+Math.max(5,Math.round(s.buyers*.25)))});
      ok("competition-premium-monotone",rb.compPrem>=r.compPrem-1e-15,()=>cx(s,{k:"buyers",a:r.compPrem,b:rb.compPrem}));
      ok("prices-monotone-in-buyers",PS.every(p=>ge(rb.q(p),r.q(p)))&&ge(rb.Vmean,r.Vmean)&&ge(rb.Vreal,r.Vreal),()=>cx(s,{a:r.Vmean,b:rb.Vmean})); } }
  lap('Q');
  /* ---- A: the ask ---- */
  { const ra=A.model({...s,ask:s.ask*1.03});
    ok("quantiles-monotone-in-ask",PS.every(p=>ge(ra.q(p),r.q(p))),()=>cx(s,{a:PS.map(r.q),b:PS.map(ra.q)}));
    ok("cap-share-non-increasing-in-ask",ra.capShare<=r.capShare+1e-12,()=>cx(s,{rho:s.ask/r.V,a:r.capShare,b:ra.capShare})); }
  /* ---- S: size ---- */
  { const r2=A.model({...s,rev:s.rev*1.05}); ok("value-monotone-in-revenue-at-fixed-earnings",ge(r2.V,r.V)&&ge(r2.Vbase,r.Vbase),()=>cx(s,{a:r.V,b:r2.V}));
    const k=1.05, rho=s.ask/r.V, sk={...s,rev:s.rev*k,ern:s.ern*k}, Vk=A.model({...sk,ask:1}).V, rk=A.model({...sk,ask:Vk*rho});
    ok("scale-at-fixed-ask-ratio-raises-proceeds",ge(rk.V,r.V)&&ge(rk.Vmean,r.Vmean,1e-9)&&ge(rk.EVp,r.EVp,1e-9),()=>cx(s,{rho,V:[r.V,rk.V],EVp:[r.EVp,rk.EVp],PC:[r.PC,rk.PC]}));
    if(rho<=.95){ ok("time-at-fair-ask-monotone-in-size",ge(rk.tMed,r.tMed)&&ge(rk.tMean,r.tMean),()=>cx(s,{rho,a:r.tMean,b:rk.tMean}));
      if(s.buyers>=typ) ok("base-close-rate-monotone-in-size",rk.PC>=r.PC-1e-15,()=>cx(s,{rho,a:r.PC,b:rk.PC})); }
    if(s.buyers>=typ&&s.ern*1.03<=.92*s.rev){ const re=A.model({...s,ern:s.ern*1.03});
      ok("earnings-raise-pc-and-proceeds-deep-pool",re.PC>=r.PC-1e-15&&ge(re.Vmean,r.Vmean)&&ge(re.EVp,r.EVp),()=>cx(s,{a:[r.PC,r.EVp],b:[re.PC,re.EVp]})); }
    const rf=A.model({...s,franchise:!s.franchise}), [on,off]=s.franchise?[r,rf]:[rf,r];
    ok("franchise-never-raises-risk",on.risk.p<=off.risk.p&&on.risk.p5<=off.risk.p5&&on.risk.expLoss<=off.risk.expLoss&&same(on.EVp,off.EVp)&&same(on.V,off.V)&&CATS.every(c=>on.cats[c]===off.cats[c]),()=>cx(s,{on:on.risk.p,off:off.risk.p}));
  }
  lap('A+S');
  /* ---- sensitivity rows ---- */
  { const sn=A.sensitivity(s), tolV=1e-9*r.V, tolE=1e-9*Math.max(1,r.EVp);
    for(const o of sn){
      if(o.k==="ask") ok("sensitivity-process-rows",Math.abs(o.dV)<=tolV&&o.dP>=-1e-12,()=>cx(s,{row:o.k,dV:o.dV,dP:o.dP}));
      else if(o.k==="buyers") ok("sensitivity-process-rows",Math.abs(o.dV)<=tolV&&o.dE>=-tolE&&o.dP>=-1e-12,()=>cx(s,{row:o.k,dV:o.dV,dE:o.dE,dP:o.dP}));
      else ok("sensitivity-quality-rows-non-negative",o.dV>=-tolV&&o.dE>=-tolE&&o.dP>=-1e-12,()=>cx(s,{row:o.k,dV:o.dV,dE:o.dE,dP:o.dP}));
    } }
  lap('sensitivity');
  /* ---- the expensive ones on subsets ---- */
  const t=(i%2===0||i%5===4)?prep(s):null;
  if(t){
    const it=A.interventionTable(t,r), row=k=>it.find(x=>x.k===k);
    for(const k of ["qoe","sops","contracts","divers","retain","channel"]){ const o=row(k);
      ok("intervention-quality-rows",o.dV>=-1e-9*r.V&&o.dE>=-1e-9*Math.max(1,r.EVp)&&Math.abs(o.dP)<1e-12&&Math.abs(o.dTnet-o.days)<1e-9,()=>cx(s,{row:k,dV:o.dV,dE:o.dE,dP:o.dP,dTnet:o.dTnet,days:o.days})); }
    { const o=row("outreach"); ok("intervention-outreach-row",Math.abs(o.dV)<=1e-9*r.V&&o.dE>=-1e-9*Math.max(1,r.EVp)&&o.dP>=-1e-12,()=>cx(s,{dV:o.dV,dE:o.dE,dP:o.dP})); }
    for(const k of ["margin","growth"]){ const o=row(k); ok("intervention-earnings-rows-raise-value",o.dV>=-1e-9*r.V,()=>cx(s,{row:k,dV:o.dV})); }
    { const o=row("reprice"); ok("intervention-reprice-row",Math.abs(o.dV)<=1e-9*r.V&&o.dE>=-1e-6*Math.max(1,r.EVp),()=>cx(s,{rho:s.ask/r.V,rhoSell:t.rhoSell,dV:o.dV,dE:o.dE})); }
    /* the hero caption, as render() builds it */
    const bs=A.businessScore(t,r,t.rhoSell), loss=1-r.EVp/Math.max(bs.rA.EVp,1), poolLoss=bs.thin?1-bs.rA.EVp/Math.max(bs.rq.EVp,1):0;
    const sA=Math.max(sc,Math.min(bs.score,A.omniScore(bs.rA)));
    ok("hero-caption-losses-non-negative",loss>=-1e-6&&poolLoss>=-1e-6&&sA-sc>=0&&bs.score-sA>=0,()=>cx(s,{loss,poolLoss,score:sc,biz:bs.score}));
    /* the note under the listing cards */
    const V=r.V, rSell=A.model({...t,ask:V*t.rhoSell}), rKeep=A.model({...t,ask:V*t.optRho}), n=A.optNote(t,V,rSell,rKeep);
    ok("optimizer-cards-optimal-on-own-objective",rSell.EVp>=rKeep.EVp*(1-1e-9),()=>cx(s,{rhoSell:t.rhoSell,optRho:t.optRho,a:rSell.EVp,b:rKeep.EVp}));
    if(n.kind==="higher") ok("walkaway-note-directions",rKeep.PC<=rSell.PC+1e-12&&rKeep.tMean>=rSell.tMean-1e-9&&rKeep.Vmean>=rSell.Vmean*(1-1e-9),()=>cx(s,{kind:n.kind,rhoSell:t.rhoSell,optRho:t.optRho}));
    if(n.kind==="lower") ok("walkaway-note-directions",rKeep.PC>=rSell.PC-1e-12&&rKeep.tMean<=rSell.tMean+1e-9,()=>cx(s,{kind:n.kind,rhoSell:t.rhoSell,optRho:t.optRho}));
    if(t.lamT===0) ok("walkaway-not-below-proceeds-optimum-without-delay",t.optRho>=t.rhoSell-2e-4&&n.kind!=="lower",()=>cx(s,{rhoSell:t.rhoSell,optRho:t.optRho,kind:n.kind}));
    /* the business score never reads the ask or the preferences */
    if(i%4===0){ const t2=prep({...s,ask:s.ask*pick([.6,1.7]),lamT:s.lamT===0?2000:0,theta:1-s.theta,budget:s.budget+3e5});
      const b1=A.omniScore(bs.rq), b2=A.omniScore(A.businessScore(t2,A.model(t2),t2.rhoSell).rq);
      ok("business-score-reads-no-ask-or-preference",b1===b2&&Math.abs(t2.rhoSell-t.rhoSell)<1e-12,()=>cx(s,{b1,b2,rs1:t.rhoSell,rs2:t2.rhoSell})); }
    /* business score and walk-away against each quality input */
    if(i%6===0) for(const k of QK){ const v=BETTER[k](s); if(v===s[k]) continue;
      const t2=prep({...s,[k]:v}), r2=A.model(t2), b2=A.businessScore(t2,r2,t2.rhoSell);
      ok("business-score-monotone-in-quality",b2.score>=bs.score,()=>cx(s,{k,v,a:bs.score,b:b2.score,rs:[t.rhoSell,t2.rhoSell]}));
      ok("walkaway-monotone-in-quality",t2.optRho>=t.optRho-2e-4&&r2.V*t2.optRho>=V*(t.optRho-2e-4),()=>cx(s,{k,v,a:t.optRho,b:t2.optRho,V:[V,r2.V]})); }
  }
  lap('prep+interv+caption+bizQ');
  if(i%10===0){ /* proceeds unimodal in the ask, and the Omni score with it */
    const V=r.V, ev=[], scs=[]; for(let m=.4;m<=2.5+1e-9;m+=.01){ const x=A.model({...s,ask:V*m}); ev.push(x.EVp); scs.push(A.omniScore(x)); }
    let dir=0, ch=0; for(let j=1;j<ev.length;j++){ const d=ev[j]-ev[j-1], nd=d>1e-9*ev[j]?1:d<-1e-9*ev[j]?-1:0; if(nd&&dir&&nd!==dir) ch++; if(nd) dir=nd; }
    const jm=ev.indexOf(Math.max(...ev)); let scOk=true; for(let j=1;j<scs.length;j++){ if(j<=jm&&scs[j]<scs[j-1]) scOk=false; if(j>jm&&scs[j]>scs[j-1]) scOk=false; }
    ok("proceeds-unimodal-in-ask",ch<=1&&scOk,()=>cx(s,{changes:ch,peakAt:.4+.01*jm,scOk}));
  }
  lap('unimodal');
  if(i%15===5){ /* walk-away against theta, the cost of delay and the pool; the proceeds optimum against the pool */
    const th=[]; for(let k=0;k<=20;k++) th.push(A.bestRatio(s,k/20,s.lamT));
    let okT=true, at=null; for(let k=1;k<=20;k++) if(th[k]<th[k-1]-2e-4){ okT=false; at=at||{theta:k/20,from:th[k-1],to:th[k]}; }
    ok("walkaway-monotone-in-theta",okT,()=>cx(s,at));
    const lams=[0,100,300,600,900,1500,2500,4000], lr=lams.map(l=>A.bestRatio(s,s.theta,l));
    let okL=true, atL=null; for(let k=1;k<lams.length;k++) if(lr[k]>lr[k-1]+2e-4){ okL=false; atL=atL||{lam:lams[k],from:lr[k-1],to:lr[k]}; }
    ok("walkaway-monotone-in-delay-cost",okL,()=>cx(s,atL));
    { const r00=A.bestRatio(s,0,0), th0=[.25,.5,.75,1].map(x=>A.bestRatio(s,x,0));
      ok("walkaway-not-below-proceeds-optimum-without-delay",th0.every(x=>x>=r00-2e-4),()=>cx(s,{r00,th0})); }
    const typ2=typOf(s), pools=[...new Set([5,10,20,35,Math.max(5,typ2-5),typ2,typ2+5,2*typ2,150,300,600])].sort((a,b)=>a-b);
    const ps=pools.map(b=>A.bestRatio({...s,buyers:b},0,0)), pw=pools.map(b=>A.bestRatio({...s,buyers:b},0,s.lamT||900));
    let ok1=true,ok2=true,a1=null,a2=null; for(let k=1;k<pools.length;k++){ if(ps[k]<ps[k-1]-2e-4){ok1=false; a1=a1||{b:pools[k],from:ps[k-1],to:ps[k]};} if(pw[k]<pw[k-1]-2e-4){ok2=false; a2=a2||{b:pools[k],from:pw[k-1],to:pw[k]};} }
    ok("proceeds-optimum-monotone-in-buyers",ok1,()=>cx(s,a1)); ok("walkaway-monotone-in-buyers",ok2,()=>cx(s,a2));
    /* the business score against the pool, across the whole range */
    let prev=-1, okB=true, atB=null; for(const b of pools){ const tb=prep({...s,buyers:b}), sb=A.businessScore(tb,A.model(tb),tb.rhoSell).score; if(sb<prev){okB=false; atB=atB||{b,prev,sb};} prev=sb; }
    ok("business-score-monotone-in-buyers",okB,()=>cx(s,atB));
    /* the proceeds optimum against the whole quality range */
    const lo={...s,rec:0,cc:.7,ret:.45,plt:.95,grw:-.25,gm:.12,own:.95,mgt:.08,fin:.14}, hi={...s,rec:1,cc:.01,ret:.99,plt:.05,grw:.7,gm:.97,own:.14,mgt:.92,fin:.96};
    const qa=A.bestRatio(lo,0,0), qb=A.bestRatio(s,0,0), qc=A.bestRatio(hi,0,0);
    ok("proceeds-optimum-flat-in-quality",Math.abs(qc-qa)<.005&&qa<=qb+2e-4&&qb<=qc+2e-4,()=>cx(s,{worst:qa,actual:qb,best:qc}));
  }
  lap('theta/lam/pool');
  if(i%25===7){ /* the optimiser: budget, the proceeds card's preferences, the lift, theta and the cost of delay */
    const t=prep(s), r0=A.model(t), all=A.costOf(t,A.INTERV.map(x=>x.k));
    let pV=null, okB=true, atB=null;
    for(const B of [0,2e4,6e4,.1*all,.3*all,all].sort((a,b)=>a-b)){ const b=A.optimize(t,r0,B,t.lamT,t.theta);
      if(pV&&!(b.V.net>=pV.V.net-1e-6&&b.V.proceeds>=pV.V.proceeds-1e-6&&b.U.U>=pV.U.U-1e-6)){ okB=false; atB=atB||{B,net:[pV.V.net,b.V.net],proc:[pV.V.proceeds,b.V.proceeds],U:[pV.U.U,b.U.U]}; }
      ok("optimizer-lift-at-least-spend",b.V.proceeds-r0.EVp>=b.V.c-1e-6*Math.max(1,r0.EVp),()=>cx(s,{B,lift:b.V.proceeds-r0.EVp,c:b.V.c}));
      pV=b; }
    ok("optimizer-monotone-in-budget",okB,()=>cx(s,atB));
    const b0=A.optimize(t,r0,t.budget,t.lamT,t.theta);
    const tq={...t,theta:Math.min(1,t.theta+.15)}; tq.optRho=A.bestRatio(tq,tq.theta,tq.lamT); const bq=A.optimize(tq,r0,t.budget,tq.lamT,tq.theta);
    const tl={...t,lamT:t.lamT+500}; tl.optRho=A.bestRatio(tl,tl.theta,tl.lamT); const bl=A.optimize(tl,r0,t.budget,tl.lamT,tl.theta);
    const ks=x=>JSON.stringify(x.keys.slice().sort());
    ok("proceeds-card-reads-no-preference",ks(bq.V)===ks(b0.V)&&ks(bl.V)===ks(b0.V)&&same(bq.V.net,b0.V.net)&&same(bl.V.net,b0.V.net),()=>cx(s,{a:b0.V.keys,b:bq.V.keys,c:bl.V.keys}));
    ok("optimizer-cards-optimal-on-own-objective",b0.V.net>=b0.U.net-1e-4*r0.V&&b0.U.U>=b0.V.U-1e-4*r0.V,()=>cx(s,{netV:b0.V.net,netU:b0.U.net,UV:b0.V.U,UU:b0.U.U}));
    ok("optimizer-utility-monotone-in-theta-and-delay",bq.U.U>=b0.U.U-1e-4*r0.V&&bl.U.U<=b0.U.U+1e-4*r0.V,()=>cx(s,{U:b0.U.U,Utheta:bq.U.U,Ulam:bl.U.U}));
  }
  lap('optimizer');
  if(i%3===1){ /* the value gap, pruned exactly as render() prunes it */
    let keys=A.INTERV.map(o=>o.k);
    for(let pass=0;pass<A.INTERV.length;pass++){ const vAll=A.model(A.applyAll(s,r,keys)).V; let drop=null, bestV=vAll-Math.max(1,vAll*1e-6);
      for(const k of keys){ if(k==="reprice") continue; const v=A.model(A.applyAll(s,r,keys.filter(x=>x!==k))).V; if(v>=bestV){ bestV=v; drop=k; } }
      if(!drop) break; keys=keys.filter(x=>x!==drop); }
    const gap=A.model(A.applyAll(s,r,keys)).V-r.V;
    ok("value-gap-non-negative",gap>=-1e-9*r.V,()=>cx(s,{gap,keys}));
  }
  lap('valuegap');
  if(i%25===0) process.stderr.write(`  ${i+1}/${states.length} states, ${((Date.now()-T0)/1000).toFixed(0)} s\n`);
}

{ const _t0=Date.now();
/* ================= state labels ================= */
for(let i=0;i<60;i++){ const s=sample(), r=A.model(s), p0=A.fitRisk(r.V,s.ind,r.rate,r.jobs,!!s.franchise,null).p;
  for(const k of Object.keys(A.MODELS.risk.state_effects)){ const e=A.MODELS.risk.state_effects[k], d=A.fitRisk(r.V,s.ind,r.rate,r.jobs,!!s.franchise,k).p-p0;
    ok("state-label-sign-matches-effect",e===0?Math.abs(d)<1e-15:Math.sign(d)===Math.sign(e),()=>cx(s,{state:k,effect:e,d})); } }

TIME.stateLabels=Date.now()-_t0; }
{ const _t1=Date.now();
/* ================= interventions against their own size, cost and days ================= */
{ const VAR={
    contracts2x:[["eff:{add:{rec:.13,ret:.03}}","eff:{add:{rec:.26,ret:.06}}"]],
    diversDeeper:[["eff:{mul:{cc:.62}}","eff:{mul:{cc:.40}}"]],
    outreachWider:[["eff:{mul:{buyers:2.2}}","eff:{mul:{buyers:3.5}}"]],
    gmDearer:[["add:{ern:-IVC.gm.loading*gmSalary(s)}","add:{ern:-1.5*IVC.gm.loading*gmSalary(s)}"]],
    contractsCostlier:[["cost:s=>Math.max(28000,.010*s.rev)","cost:s=>2*Math.max(28000,.010*s.rev)"]],
    contractsSlower:[['k:"contracts", n:"Convert customers to contracts and retainers", days:240','k:"contracts", n:"Convert customers to contracts and retainers", days:400']]};
  const AV={}; for(const k in VAR) AV[k]=A.loadWith(VAR[k]);
  for(let i=0;i<30;i++){ const s=prep(sample()), r=A.model(s), it=A.interventionTable(s,r), row=(T,k)=>T.find(x=>x.k===k), tE=1e-9*Math.max(1,r.EVp), tV=1e-9*r.V;
    const I=k=>AV[k].interventionTable(s,AV[k].model(s));
    { const a=row(it,"contracts"), b=row(I("contracts2x"),"contracts"); ok("intervention-gain-monotone-in-own-size",b.dV>=a.dV-tV&&b.dE>=a.dE-tE,()=>cx(s,{v:"contracts2x",a,b})); }
    { const a=row(it,"divers"), b=row(I("diversDeeper"),"divers"); ok("intervention-gain-monotone-in-own-size",b.dV>=a.dV-tV&&b.dE>=a.dE-tE,()=>cx(s,{v:"diversDeeper",dE:[a.dE,b.dE]})); }
    { const a=row(it,"outreach"), b=row(I("outreachWider"),"outreach"); ok("intervention-gain-monotone-in-own-size",b.dE>=a.dE-tE&&b.dP>=a.dP-1e-12,()=>cx(s,{v:"outreachWider",dE:[a.dE,b.dE]})); }
    { const a=row(it,"gm"), b=row(I("gmDearer"),"gm"); ok("intervention-gain-monotone-in-own-size",b.dV<=a.dV+tV,()=>cx(s,{v:"gmDearer",dV:[a.dV,b.dV]})); }
    { const a=row(it,"contracts"), b=row(I("contractsCostlier"),"contracts"); ok("intervention-gain-monotone-in-own-size",same(b.dE,a.dE)&&b.net<=a.net&&(b.roi===null||a.roi===null||b.roi<=a.roi),()=>cx(s,{v:"contractsCostlier",net:[a.net,b.net]})); }
    { const a=row(it,"contracts"), b=row(I("contractsSlower"),"contracts"); ok("intervention-gain-monotone-in-own-size",same(b.dE,a.dE)&&Math.abs(b.dTnet-a.dTnet-160)<1e-9,()=>cx(s,{v:"contractsSlower",dTnet:[a.dTnet,b.dTnet]})); }
    if(i%5===0){ const o=A.optimize(s,r,s.budget,s.lamT,s.theta), o2=AV.contracts2x.optimize(s,r,s.budget,s.lamT,s.theta), o3=AV.contractsCostlier.optimize(s,r,s.budget,s.lamT,s.theta);
      ok("intervention-gain-monotone-in-own-size",o2.V.net>=o.V.net-tE&&o3.V.net<=o.V.net+tE&&o2.U.U>=o.U.U-1e-6*r.V&&o3.U.U<=o.U.U+1e-6*r.V,()=>cx(s,{v:"optimizer",net:[o.V.net,o2.V.net,o3.V.net]})); }
  } }

TIME.intervSize=Date.now()-_t1; }
const _t2=Date.now();
/* ================= fine scans ================= */
{ /* value against scale at fixed margins, value against revenue at fixed earnings, risk against size */
  const prof={grw:.08,gm:.5,rec:.4,cc:.16,ret:.8,plt:.4,own:.72,mgt:.36,fin:.74,yrs:6,buyers:50,st:null,franchise:false};
  for(const ind of INDS) for(const m of [.03,.15,.45,.9]){ let pv=null, mn=Infinity, okV=true, okR=true, atV=null, atR=null;
    for(let j=0;j<=240;j++){ const rev=1e4*Math.pow(5e9/1e4,j/240), ern=Math.max(1e3,m*rev), x=A.model({...prof,ind,rev,ern,ask:rev*m*2});
      if(pv&&!(x.V>=pv.V*(1-1e-12)&&x.Vbase>=pv.Vbase*(1-1e-12))){ okV=false; atV=atV||{ind,m,rev,a:pv.V,b:x.V}; }
      if(pv&&!(x.risk.p5<=pv.risk.p5*(1+1e-12)&&x.risk.p8<=pv.risk.p8*(1+1e-12)
            &&(x.risk.tail>pv.risk.tail?x.risk.p<=pv.risk.p*(x.risk.tail/pv.risk.tail)*(1+1e-12):x.risk.p<=pv.risk.p*(1+1e-12)&&x.risk.expLoss<=pv.risk.expLoss*(1+1e-12)))){
        okR=false; atR=atR||{ind,m,rev,V:x.V,p:[pv.risk.p,x.risk.p],p8:[pv.risk.p8,x.risk.p8],tail:[pv.risk.tail,x.risk.tail],p5:[pv.risk.p5,x.risk.p5],el:[pv.risk.expLoss,x.risk.expLoss]}; }
      mn=Math.min(mn,x.risk.p); pv=x; }
    ok("value-monotone-in-scale",okV,()=>fmt(atV)); ok("risk-non-increasing-in-size",okR,()=>fmt(atR)); }
  for(const ind of INDS) for(const ern of [5e3,1.5e5,3e6,2e7]){ let pv=null, okV=true, at=null;
    for(let j=0;j<=120;j++){ const rev=ern/.92*Math.pow(.92/.002,j/120), x=A.model({...prof,ind,rev,ern,ask:ern*3});
      if(pv&&!(x.V>=pv.V*(1-1e-12))){ okV=false; at=at||{ind,ern,rev,a:pv.V,b:x.V}; } pv=x; }
    ok("value-monotone-in-revenue-at-fixed-earnings",okV,()=>fmt(at)); }
  for(const ind of INDS) for(const rev of [2e4,1e6,3e7,3e9]){ let pv=null, okV=true, at=null;
    for(let j=0;j<=184;j++){ const ern=Math.max(1e3,rev*(.005+j*.005)); if(ern>.92*rev) break; const x=A.model({...prof,ind,rev,ern,ask:rev});
      if(pv&&!(x.V>=pv.V*(1-1e-12)&&x.Vbase>=pv.Vbase*(1-1e-12))){ okV=false; at=at||{ind,rev,ern,a:pv.V,b:x.V}; } pv=x; }
    ok("fine-scan-earnings",okV,()=>fmt(at)); }
  /* each quality input across its whole range, at a fixed ask */
  const RNG={rec:[0,1,1],cc:[.95,.005,-1],ret:[.05,.99,1],plt:[.999,.02,-1],grw:[-.6,1.5,1],gm:[.02,.97,1],own:[.99,.02,-1],mgt:[.02,.99,1],fin:[.02,1,1]};
  for(let i=0;i<18;i++){ const s=sample(), V=A.model({...s,ask:1}).V; s.ask=V*pick([.8,1.05,1.3,1.6,2.2]);
    for(const k of QK){ const [a,b]=RNG[k]; let pv=null, okQ=true, at=null;
      for(let j=0;j<=100;j++){ const x=A.model({...s,[k]:a+(b-a)*j/100}), scx=A.omniScore(x);
        if(pv&&!(x.V>=pv.V*(1-1e-12)&&x.PC>=pv.PC-1e-15&&x.EVp>=pv.EVp*(1-1e-9)&&scx>=pv.sc&&x.tMed<=pv.tMed*(1+1e-12))){ okQ=false; at=at||{k,at:a+(b-a)*j/100,V:[pv.V,x.V],EVp:[pv.EVp,x.EVp],sc:[pv.sc,scx]}; }
        pv={V:x.V,PC:x.PC,EVp:x.EVp,tMed:x.tMed,sc:scx}; }
      ok("fine-scan-quality",okQ,()=>cx(s,at)); } }
}

TIME.fineScans=Date.now()-_t2;
}
/* ================= browser: the same directions on the page ================= */
async function browser(){
  def("app-directions-from-default","In the app, from the framework example at its own ask, the same at an overpriced $6.2M ask, and a small restaurant on a thin pool above value: one notch better on each quality control never lowers the shown Omni score, business score, model value, chance of closing, expected proceeds or any category bar, and never raises the median time to close or the survival risk",
    "the model invariants above, read off the rendered page (o_score, o_score_biz, o_msv, o_pc, o_ev, o_t, o_risk, cats)");
  def("app-process-controls","In the app: more buyers never lower the shown chance of closing, expected proceeds or Omni score and leave model value unchanged; a higher share kept never lowers the walk-away ask; a higher cost of delay never raises it; neither moves the proceeds-optimal ask or the scores; a larger budget never lowers the proceeds card's expected proceeds; a franchise never raises the shown risk and moves nothing else",
    "render(): o_list = V x bestRatio(s,0,0), o_list2 = V x bestRatio(s,theta,lambda), optimiser cards");
  let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
  const b=await pw.chromium.launch(), ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}), p=await ctx.newPage();
  const errs=[]; p.on("pageerror",e=>errs.push(e.message));
  await p.goto("file://"+path.join(ROOT,"index.html"));
  await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
  const settle=async()=>{ await p.waitForFunction(()=>typeof _rq==="undefined"||_rq===0,null,{timeout:30000}); await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))); await p.waitForTimeout(40); };
  const money=t=>{ const m=String(t).replace(/,/g,"").match(/(−|-)?\$([\d.]+)([kMB])?/); if(!m) return NaN; return (m[1]?-1:1)*(+m[2])*({k:1e3,M:1e6,B:1e9}[m[3]]||1); };
  const read=()=>p.evaluate(()=>{ const $=id=>document.getElementById(id), tx=id=>($(id)?$(id).textContent:"");
    const cats={}; document.querySelectorAll("#cats .cat-row").forEach(r=>{ const k=r.children[0].textContent.trim(), v=r.querySelector(".cat-n"); if(v) cats[k]=+v.textContent; });
    const cards=[...document.querySelectorAll("#optout .opt")].map(c=>[...c.querySelectorAll(".big .n")].map(e=>e.textContent));
    return {score:+tx("o_score"),biz:+tx("o_score_biz"),msv:tx("o_msv"),pc:parseFloat(tx("o_pc")),ev:($("o_ev").querySelector(".kfig")||$("o_ev")).textContent,
      t:parseFloat(tx("o_t")),risk:parseFloat(tx("o_risk")),list:tx("o_list"),list2:tx("o_list2"),cats,card1:cards[0]?cards[0][0]:"",s:STATE.s,rV:STATE.r.V}; });
  const fig=async()=>{ const x=await read(); return {...x,msv:money(x.msv),ev:money(x.ev),list:money(x.list),list2:money(x.list2),card1:money(x.card1)}; };
  const reset=async()=>{ await p.click("#reset"); await settle(); await p.waitForTimeout(300); await settle(); };
  const typeBox=async(id,v)=>{ await p.fill("#"+id,String(v)); await p.press("#"+id,"Enter"); await settle(); };
  const sel=async(id,v)=>{ await p.selectOption("#"+id,String(v)); await settle(); };
  const geq=(b,a)=>b>=a-1e-9, leq=(b,a)=>b<=a+1e-9;
  const STEPS=[["i_own","sel","0.42","own",.42],["i_mgt","sel","0.66","mgt",.66],["i_fin","sel","0.96","fin",.96],["v_rec","box","82%","rec",.82],["v_gm","box","70%","gm",.70],
               ["v_grw","box","20%","grw",.20],["v_ret","box","95%","ret",.95],["v_cc","box","10%","cc",.10],["v_plt","box","28%","plt",.28],["v_yrs","box","9","yrs",9]];
  /* three starting points: the framework example (ask 0.79x value), the same overpriced at $6.2M (1.52x), and a small
     restaurant marketed to a thin pool above value ($150k SDE on $600k, ask $350k = 1.29x, 20 buyers against 41) */
  const STARTS=[["default",[]],["overpriced",[["v_ask","box","6.2M"]]],
    ["small-thin",[["i_ind","sel","rest"],["v_rev","box","600k"],["v_ern","box","150k"],["v_ask","box","350k"],["v_buy","box","20"]]]];
  const apply=async list=>{ for(const [id,how,v] of list){ if(how==="sel") await sel(id,v); else await typeBox(id,v); } };
  for(const [askTxt,start] of STARTS){
    await reset(); await apply(start); const a=await fig();
    for(const [id,how,v,field,target] of STEPS){ await reset(); await apply(start);
      if(how==="sel") await sel(id,v); else await typeBox(id,v); const x=await fig();
      const catOk=Object.keys(a.cats).filter(k=>!/^Mean/.test(k)).length===9&&Object.keys(a.cats).every(k=>geq(x.cats[k],a.cats[k]));
      const yrs=id==="v_yrs", applied=Math.abs(x.s[field]-target)<1e-9&&x.s.ask===a.s.ask&&x.s.ind===a.s.ind&&x.s.buyers===a.s.buyers&&x.s.rev===a.s.rev;
      ok("app-directions-from-default",applied&&(yrs?x.rV===a.rV:x.rV>=a.rV)&&geq(x.score,a.score)&&geq(x.biz,a.biz)&&geq(x.msv,a.msv)&&geq(x.pc,a.pc)&&geq(x.ev,a.ev)&&leq(x.t,a.t)&&leq(x.risk,a.risk)&&catOk
        &&(!yrs||(x.score===a.score&&x.msv===a.msv&&x.pc===a.pc&&x.ev===a.ev)),
        ()=>fmt({start:askTxt,control:id,to:v,before:{score:a.score,biz:a.biz,msv:a.msv,pc:a.pc,ev:a.ev,t:a.t,risk:a.risk},after:{score:x.score,biz:x.biz,msv:x.msv,pc:x.pc,ev:x.ev,t:x.t,risk:x.risk},cats:catOk}));
    }
  }
  await reset(); const d=await fig();
  { await typeBox("v_buy","150"); const x=await fig(); ok("app-process-controls",x.s.buyers===150&&geq(x.pc,d.pc)&&geq(x.ev,d.ev)&&geq(x.score,d.score)&&x.msv===d.msv,()=>fmt({control:"buyers 65->150",d,x})); }
  { await reset(); await typeBox("v_buy","20"); const x=await fig(); ok("app-process-controls",x.s.buyers===20&&leq(x.pc,d.pc)&&leq(x.ev,d.ev)&&leq(x.score,d.score)&&x.msv===d.msv,()=>fmt({control:"buyers 65->20",pc:[d.pc,x.pc],ev:[d.ev,x.ev]})); }
  for(const th of ["40%","90%","100%"]){ await reset(); await typeBox("v_th",th); const x=await fig();
    const up=parseFloat(th)>75; ok("app-process-controls",Math.abs(x.s.theta-parseFloat(th)/100)<1e-9&&(up?geq(x.list2,d.list2):leq(x.list2,d.list2))&&x.list===d.list&&x.score===d.score&&x.biz===d.biz,()=>fmt({control:"theta "+th,list2:[d.list2,x.list2],list:[d.list,x.list]})); }
  for(const lam of ["0","2500","4000"]){ await reset(); await typeBox("v_lam",lam); const x=await fig();
    const up=+lam>900; ok("app-process-controls",x.s.lamT===+lam&&(up?leq(x.list2,d.list2):geq(x.list2,d.list2))&&x.list===d.list&&x.score===d.score&&x.biz===d.biz,()=>fmt({control:"lamT "+lam,list2:[d.list2,x.list2]})); }
  { let prev=null; for(const bud of ["none","50k","100k","400k","2M"]){ await reset(); await typeBox("v_bud",bud); const x=await fig();
      if(prev) ok("app-process-controls",geq(x.card1,prev.card1),()=>fmt({control:"budget "+bud,card1:[prev.card1,x.card1]})); prev=x; } }
  { await reset(); await p.click("#i_fr"); await settle(); const x=await fig();
    ok("app-process-controls",x.s.franchise===true&&leq(x.risk,d.risk)&&x.score===d.score&&x.msv===d.msv&&x.pc===d.pc&&x.ev===d.ev&&x.biz===d.biz,()=>fmt({control:"franchise",risk:[d.risk,x.risk]})); }
  ok("app-process-controls",errs.length===0,()=>"page errors: "+errs.join(" | "));
  await b.close();
}

(async()=>{
  if(opt["browser-only"]) for(const k of [...INV.keys()]) INV.delete(k); else runModel();
  if(opt.browser||opt["browser-only"]) await browser();
  let nf=0;
  for(const o of INV.values()){
    if(o.fails){ nf++; console.log(`FAIL ${o.name} cases=${o.cases} fails=${o.fails} first=${typeof o.first==="string"?o.first:fmt(o.first)}`); }
    else console.log(`PASS ${o.name} cases=${o.cases}`);
  }
  console.log(`${INV.size} invariants, ${nf} failing; ${nState} random base states; ${((Date.now()-T0)/1000).toFixed(0)} s`);
  if(opt.timing) console.error('timing (ms): '+JSON.stringify(TIME));
  if(opt.json) fs.writeFileSync(opt.json,JSON.stringify([...INV.values()],null,1));
  process.exit(nf?1:0);
})();
