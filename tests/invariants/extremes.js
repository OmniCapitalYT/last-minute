#!/usr/bin/env node
/* Stress invariants for the "extremes" lens: the corners and edges of the reachable input space and beyond what the
   sliders allow but the exact-value fields accept.

   Run:  node tests/invariants/extremes.js [appRoot=the repository] [--no-browser] [--browser-only] [--list]
   Prints one line per invariant: "PASS <name> cases=<n>" or "FAIL <name> cases=<n> fails=<k> first=<counterexample>".
   Seeded, so every failure reproduces. The model part runs in about 3 minutes; the browser part in about 2. */
"use strict";
const path=require("path");
const ARGS=process.argv.slice(2), FLAGS=new Set(ARGS.filter(a=>a.startsWith("--")));
const ROOT=path.resolve(ARGS.find(a=>!a.startsWith("--"))||path.join(__dirname,"..",".."));
const L=require(path.join(ROOT,"tests","load.js")), A=L;

/* ---------------------------------------------------------------- registry and reporting */
const INV=[], RES={};
function inv(name,statement,source){ INV.push({name,statement,source}); RES[name]={cases:0,fails:0,first:null}; }
const fmt=v=>JSON.stringify(v,(k,x)=>typeof x==="number"?(isFinite(x)?+x.toPrecision(7):String(x)):x);
function ok(name,cond,ctx){ const o=RES[name]; if(!o) throw new Error("unregistered invariant "+name); o.cases++;
  if(!cond){ o.fails++; if(o.first===null) o.first=typeof ctx==="function"?ctx():ctx; } return cond; }
function guard(name,fn,ctx){ try{ return fn(); }catch(e){ ok(name,false,()=>({...(typeof ctx==="function"?ctx():ctx),threw:String(e&&e.message||e).slice(0,160)})); return undefined; } }

/* ---------------------------------------------------------------- seeded RNG and state helpers */
let seed=20261013; const rnd=()=>{ seed=(seed*16807)%2147483647; return (seed-1)/2147483646; };
const pick=a=>a[Math.floor(rnd()*a.length)];
const logU=(lo,hi)=>Math.exp(Math.log(lo)+rnd()*(Math.log(hi)-Math.log(lo)));
const INDS=Object.keys(A.IND), STS=[null,...Object.keys(A.MODELS.risk.state_effects)];
const DEF={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,buyers:65,budget:1e5,lamT:900,theta:.75,grw:.14,gm:.64,rec:.72,cc:.18,
  ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,st:null,franchise:false};
const short=s=>{ const o={}; for(const k of ["ind","rev","ern","ask","buyers","yrs","st","franchise","budget","lamT","theta","grw","gm","rec","cc","ret","plt","own","mgt","fin"]) if(s[k]!==undefined&&s[k]!==DEF[k]) o[k]=s[k]; return o; };
const fin=x=>typeof x==="number"&&isFinite(x);
const ORDER_CASES=[];   /* (industry, earnings, ask) where the score depends on which state built the cached population */
const Vof=s=>A.model({...s,ask:1}).V;

/* quality corners: the console's control ends, and the model's own domain ends (FIELD_RANGE) */
const Q_UI_WORST={grw:-.25,gm:.12,rec:0,cc:.70,ret:.45,plt:.95,own:.95,mgt:.08,fin:.14};
const Q_UI_BEST ={grw:.70,gm:.92,rec:1,cc:.01,ret:.99,plt:.05,own:.14,mgt:.92,fin:.96};
const Q_DOM_WORST={grw:-.6,gm:.02,rec:0,cc:.95,ret:.05,plt:.999,own:.99,mgt:.02,fin:.02};
const Q_DOM_BEST ={grw:1.5,gm:.97,rec:1,cc:.005,ret:.99,plt:.02,own:.02,mgt:.99,fin:1};
const Q_MIX1={grw:1.5,gm:.02,rec:1,cc:.95,ret:.99,plt:.02,own:.99,mgt:.99,fin:.02};
const Q_MIX2={grw:-.6,gm:.97,rec:0,cc:.005,ret:.05,plt:.999,own:.02,mgt:.02,fin:1};
const QSETS=[{},Q_UI_WORST,Q_UI_BEST,Q_DOM_WORST,Q_DOM_BEST,Q_MIX1,Q_MIX2];
/* size corners: revenue from $1k to $100B, earnings from $1 to 92% of revenue */
const SIZES=[[1e3,1],[1e3,920],[1e4,1e3],[1e4,9.2e3],[1e5,2e3],[1e5,9.2e4],[6e6,1.45e6],[2e8,4e6],[1e8,1e3],[1e8,9.2e7],[5e9,1e3],[5e9,4.6e9],[1e11,1e3],[1e11,9.2e10]];
const ASKR=[1e-6,1e-3,.35,.4,.8,1,1.05,Math.exp(.1),1.1,1.25,1.5,2,10,1e3,1e6];
function corner(){
  const s={...DEF,ind:pick(INDS),st:pick(STS),franchise:rnd()<.5};
  const [rev,ern]=rnd()<.85?pick(SIZES):(()=>{ const r=logU(1e3,1e11); return [r,r*logU(Math.max(1e-8,1/r),.92)]; })();   /* earnings >= $1: the model floors money at $1 (softMin, fitValue's multiple); the UI floor is $1k */
  s.rev=rev; s.ern=ern; Object.assign(s,pick(QSETS));
  if(rnd()<.25){ for(const k of Object.keys(Q_DOM_BEST)) if(rnd()<.5) s[k]=rnd()<.5?Q_DOM_WORST[k]:Q_DOM_BEST[k]; }
  const typ=A.IND[s.ind].buyers;
  s.buyers=rnd()<.8?pick([0,1,5,typ-1,typ,typ+1,600,5000]):logU(.01,1e5);
  s.yrs=rnd()<.8?pick([0,1,3,12,50]):rnd()*30;
  s.budget=pick([0,1,1e4,1e5,1e6,1e9,1e12]); s.lamT=pick([0,50,900,4000,1e6]); s.theta=pick([0,.01,.5,.75,.99,1]);
  const V=Vof(s); s.ask=rnd()<.15?pick([1,1e3,1e11,1e14]):V*(rnd()<.85?pick(ASKR):logU(1e-6,1e6));
  return s;
}
function deepEq(a,b,seen){ if(a===b) return true; if(typeof a==="number"&&typeof b==="number") return (a!==a&&b!==b)||a===b;
  if(typeof a!==typeof b||a===null||b===null||typeof a!=="object") return typeof a==="function"&&typeof b==="function"?true:a===b;
  if(Array.isArray(a)!==Array.isArray(b)) return false; const ka=Object.keys(a), kb=Object.keys(b); if(ka.length!==kb.length) return false;
  for(const k of ka){ if(k==="inputs"||k==="ind"||k==="RF") continue; if(!deepEq(a[k],b[k])) return false; } return true; }

/* ================================================================ invariant definitions */
/* --- robustness at corners --- */
inv("corner-no-throw","model(), omniScore(), businessScore(), sensitivity(), interventionTable(), bestRatio(), optimize(), optNote() and optCardNote() never throw at any corner state (16 industries, 54 states + national, franchise on/off, revenue $1k-$100B, earnings $1 to 92% of revenue, asks $1 to 1e14 and 1e-6x-1e6x value, 0-5,000 buyers, 0-50 years, every quality input at both ends of the model's domain).","model() comment: 'model() is also called directly by refDist, bestRatio and the optimiser' (the log10(0) guard); economics: a tool must answer every input it accepts");
inv("corner-finite","Every numeric output of model() (V, Vbase, Vreal, Vmean, EVp, EVcash, PC, tMed, tMean, t90-t365, ceil, askEff, capShare, cashShare, compPrem, thinF, nEng, nEngRef, conf, qz, qFactor, M, rate, risk.*, every buyer's PE/PCj/Pj/EV/Vj/S) is finite at every corner.","fuzz.test.js 'finite' extended to the corners; model() guard comments");
inv("corner-probabilities-in-range","PC, risk p/p5/p8/pTerm/expLoss/lgd, capShare, cashShare, qPct, t90/t180/t365, conf and every buyer's PE, PCj and sizeFit lie in [0,1] at every corner.","economics: probabilities and shares");
inv("corner-money-nonnegative","V > 0 and every money output (Vbase, Vreal, Vmean, EVp, EVcash, deferred, ceil, askEff, stratPrem, each buyer's Vj, Pj, EV, S) is >= 0 at every corner.","economics: prices and proceeds are never negative");
inv("corner-ceiling-holds","At every corner the median, mean and 99th-percentile price if it closes are at or below the ceiling, and the ceiling is at or below ask x max(1, IBBA size-band ratio).","model() comment 'The ask is a ceiling ... Headroom above the ask only where IBBA's own size band closes above it'");
inv("corner-quantiles-ordered","At every corner the price quantiles q(p) never fall as p rises, q(.5) is the median Vreal, and q(.02) <= E[P|close] <= ceiling.","model() 'weighted quantile' comment; fuzz 'quantiles monotone' extended to the corners");
inv("corner-proceeds-identities","At every corner EVp = P_C x E[P|close], EVcash = EVp x cashShare <= EVp and deferred = EVp - EVcash >= 0.","model(): 'expected proceeds = P(close) x E[price | close]' and the cash-at-close block");
inv("corner-risk-horizons-ordered","At every corner 0 < p5 < p8 < pTerm < 1, the headline p is pTerm (= p8 x tail factor), and 0 < expLoss < pTerm with lgd in (0,1).","fitRisk comment (charged off within 5 < 8 < 10 years; expected loss is a share of the loan)");
inv("corner-time-curve-sane","At every corner tMed > 0 is finite, tMean = tMed (pi/beta)/sin(pi/beta) > tMed, F(tMed) = 1/2, and F is a CDF on [0, 50 x tMed].","model() Model III comments (log-logistic pinned to the median; closed-form mean)");
inv("corner-buyers-sane","At every corner each buyer's PE and PCj lie in [0,0.95], its price Pj <= min(Vj, ceiling), EV = PE x PCj x Pj, and the list is sorted by EV.","model() buyer block comments (AUDIT_FINDINGS R1-4/R1-5)");
inv("corner-quality-factor-in-band","At every corner the quality factor lies inside the measured band [QB.lo, QB.hi] and the percentile in [0,1]: quality only places the business inside the measured spread.","MODELS.value.quality_band ('The BAND is fitted ... Where a business sits INSIDE it is judgment')");
inv("corner-scores-in-1-99","At every corner omniScore, businessScore and the nine category scores are integers in 1..99, and the business score is never below the Omni score.","omniScore/§21 comments ('held to 1..99'); businessScore comment");
/* --- determinism and order independence --- */
inv("model-repeatable","The same state evaluated twice, with other states evaluated in between, gives bit-identical outputs (value, prices, quantiles, P_C, time, risk, buyers, categories).","economics: a valuation must be a function of its inputs; fuzz.test.js assumes it");
inv("model-does-not-mutate-input","model() leaves the state it is given unchanged.","refDistAt comment ('Built from scratch rather than spread from the subject's own state')");
inv("applyAll-order-independent","applyAll gives the identical post-programme state for every ordering of the same intervention keys.","INTERV comment: 'Effects now compose deterministically - multipliers, then additions, then caps - so any subset yields one answer'");
inv("applyAll-does-not-mutate-input","applyAll leaves the state it is given unchanged.","INTERV comment ('declare TYPED effects rather than mutating state')");
inv("optimizer-repeatable","bestRatio and optimize return identical answers on a repeat call and in a fresh model instance.","bestRatio/optimize comments ('Solved once per render and reused')");
inv("score-history-independent","omniScore of a state is the same whatever was scored before it: scoring a state whose earnings differ by a few dollars first does not change it.","refDistAt comments: 'Keyed on the exact size, not a size bucket ... being 10% off in size moved the score by six points and the direction depended on what had been rendered before' and 'the same business could score differently depending on what had been rendered before it'");
/* --- limits --- */
inv("limit-ask-up-pc-to-zero","As the ask grows from value to 1e12 x value, P_C never rises, and at 1e6 x value P_C < 1e-12 and expected proceeds < 1e-9 x value.","fitClose comment: 'The tail decays toward a certain loss, so P_C does too'");
inv("limit-ask-up-price-flat","From 2x to 1e12 x value the effective ask, the ceiling, the median and the mean price if it closes are flat to 1e-9.","model() comment (AUDIT_FINDINGS R2-2): the effective ask 'is flat to 1e-9 from about 2x value'");
inv("limit-ask-down-pc-flat","For every ask from 1e-9 x value up to value, P_C is identical, timeMult is exactly 1 and the median time is the band median.","gapPenalty: 'pricing at or below model value carries no price penalty'; timeMult: 'exactly 1 at or below value'");
inv("limit-ask-up-time-finite-rising","Above value the median time to close rises strictly with the ask and stays finite up to 1e12 x value.","timeMult comment ('log-linear above'); overpricing costs time");
inv("limit-pool-empty-pc-zero","With no buyers contacted P_C, the thin-pool factor and expected proceeds are 0, and P_C never falls as buyers rise from 0 to 1e5.","competition comment: 'A sale needs at least one offer'");
inv("limit-pool-deep-saturates","From the typical pool up to 1e6 buyers the thin-pool factor is exactly 1 and P_C constant, while the competition premium never falls, stays <= 0.14 and reaches 0.14.","capOne/thinF comments ('exactly 1 at a typical pool or deeper'); compPrem clamp [-0.08, 0.14]");
inv("limit-gap-penalty-shape","gapPenalty is 0 at or below a 0% gap, never falls from 0% to 1e7%, is continuous at every bucket knot and at 100%, and tends to 1.","gapPenalty/GAP_TAIL_K comments ('Continuous, monotone'; 'the join is smooth')");
inv("limit-multiple-flat-above-cap","Above $3M of SDE at a fixed margin the fitted multiple (Vbase / SDE) is constant: the scale elasticity is exactly 1.","fitValue comment: 'the hinge continues at the slope that makes the total scale elasticity exactly 1.0 - i.e. the multiple goes FLAT'");
inv("limit-helpers-bounded","Over price/revenue $1-$1e13: sbaRate stays inside prime + [1.42, 2.5] and never rises with size; buyerMix shares lie in (0,1) and sum to 1; gmSalary stays inside the industry's p10-p90 x wage growth; typMargin is positive; sdeEbitdaWedge is null or in [1.02, 2.75]; capOne <= 1 and non-decreasing; softMin <= min.","helper comments (sbaRate, buyerMix, gmSalary 'held to the 10th-90th percentiles', sdeEbitdaWedge clamp, capOne 'Monotone, never above 1', softMin)");
/* --- continuity --- */
inv("continuous-in-earnings","Along fine earnings scans from $1k to 92% of revenue (16 industries, revenue $10k-$5B, ask held at 0.9x and 1.25x value) no output jumps: every jump flagged by a 20x-neighbour test is refined 4 times and must shrink with the step.","BAND_KNOTS comment ('Read off a band they jump at every edge ... interpolate'); hinge, calibration and capOne 'continuous' comments; fuzz §7");
inv("continuous-in-revenue","Along fine revenue scans from SDE/0.92 to $1e11 (16 industries, earnings $1k and $1.45M, ask held at 0.9x or 1.25x value) no output jumps.","as above");
inv("continuous-in-ask","Along fine ask scans from 1e-4x to 1e4x value (16 industries, three sizes: $100k/$2k, $6M/$1.45M, $5B/$4B) no output jumps (P_C, prices, ceiling share, time, buyers).","gapPenalty/timeMult/softMin comments ('no optimiser sits on a kink'; 'continuous in every input')");
inv("continuous-in-buyers","Along fine buyer-pool scans from 0.01 to 1e5 buyers no output jumps.","capOne comment ('a quintic (C2) blend ... no kink')");
inv("continuous-in-quality","Along scans of each quality input and years across the model's whole domain (4 industries, the smallest and a $5B business) no output jumps.","quality-band comment ('a jump at the median would make the slider feel broken')");
inv("continuous-at-named-thresholds","At each named threshold (SDE $150k knot and $3M cap; Vbase at the five band centres and the $1M/$5M channel-ramp ends; model value at the 7(a) loan bounds; ask/value at 1, e^0.1, 1.1-1.5 and 2; the typical pool and the capOne edge) a +-1e-9 bracket moves no output by more than 1e-3 of its +-1e-4 change.","same comments; each threshold's own code");
inv("ceiling-share-continuous","The share of closings at the ceiling never moves by more than 0.01 for a 0.1% change in the ask, at asks from 1e-4x to 1e4x value (including where every slice or no slice is capped).","capAt comment: 'so it is continuous in every input. A hard count of slices moved it in 1/48 steps'");
/* --- monotone and invariant at the extremes --- */
inv("value-nondecreasing-in-earnings-extremes","At revenue $10k, $100k, $5B and $100B, model value never falls as earnings rise from $1k to 92% of revenue (fine grid).","fuzz 'more earnings never lowers value', extended to the extremes");
inv("best-quality-beats-worst","At seven size corners ($1k-$100B revenue) in all 16 industries, every quality input at its best end gives a model value above that of every input at its worst end, and (for revenue $10k-$5B in five industries) a business score at least as high.","Data tab: the nine quality inputs decide where in the measured spread the business sits; economics");
inv("value-reads-only-business-inputs","Model value, the fitted value and the multiple do not move with the ask, buyers, budget, cost of delay, share kept, years, state or franchise.","model(): 'E[V|X] is what the business supports; it cannot depend on what is asked'; Data tab");
inv("years-move-only-confidence-and-categories","Changing years of history (0-50) moves only confidence, the category bars and the unused judgment panels: value, P_C, prices, proceeds, time, risk and buyers are unchanged.","Data tab: 'Years of clean history feeds only the confidence figure, the category bars and the judgment panels that are not used.'");
inv("quality-never-moves-size-band","At a fixed ask at or below both values, changing every quality input leaves the time to close, the curve shape, the cash share and the base close rate unchanged.","Data tab: 'They do not move the size band: the base close rate, the time to close and the cash share are read at the fitted value before quality positioning'");
inv("state-and-franchise-move-only-risk","State and franchise change only the survival-risk outputs, and a state's effect on the 10-year risk has the sign of its fitted state effect (every industry, size and franchise setting).","fitRisk (state and franchise enter only the charge-off hazard); OMNI_STLAB comment 'the label is the model's own difference'");
/* --- optimiser termination at corners --- */
inv("bestRatio-finite-in-domain","At every corner bestRatio returns a finite ratio in [0.80, RHO_MAX] for share kept 0, 0.5 and 1 and cost of delay 0, $4,000 and $1M a day.","bestRatio comment ('searched up to RHO_MAX, not past it')");
inv("bestRatio-beats-its-grid","At every corner the objective at bestRatio's answer is at least the best value on its own 0.02 grid.","bestRatio: 'return U(m)>=best.u ? m : best.m'");
inv("optimize-terminates-feasible","At every corner optimize returns both programmes with finite proceeds, P_C, time and utility, cost <= budget, and at a zero budget only zero-cost programmes.","optimize comment (the reprice 'costs nothing, so a repriced programme is always available')");
inv("optimize-monotone-in-budget","A larger budget never lowers the best proceeds-net programme's net or the best utility programme's utility (budget $0 -> $1B).","economics: a larger budget only adds options to the same maximisation");
inv("optimizer-texts-clean-at-corners","At every corner optNote and optCardNote print no NaN, undefined or Infinity and no negative money, and the stated gain is >= 0.","optNote comment ('a gain is never printed below zero'); fuzz card-subtitle checks extended to corners");
inv("sensitivity-finite-and-flags-edges","At every corner every sensitivity row is finite, and a lever whose +-h step leaves its domain is flagged one-sided (and only then).","sensitivity comments ('mark the rows where that is no longer true')");
inv("intervention-table-finite-and-sorted","At every corner every intervention row is finite, net = dE - cost, ROI = (dE - cost)/cost, net days = execution days + dT, and rows are sorted by net.","interventionTable comments");
/* --- browser --- */
inv("typed-money-parses","Typed money in every supported form ('$1.45M', '1,450,000', '1.45m', '450k', '2.5b', '1e6', '.5m', '1 000 000', '$1,234,567.89', ' 450 K ') lands in STATE.s exactly.","parseAmount comment ('\"$1.45M\", \"1,450,000\", \"1.45m\", \"450k\" ...')");
inv("typed-money-clamps-and-flags","Typed money outside the hard range is clamped to it and the box is flagged; earnings above 92% of revenue are stored at 92% and flagged.","MONEY hard ranges and commit(): 'typed earnings above 92% of revenue are impossible: store the clamp here'");
inv("typed-junk-restores-and-flags","Malformed or forbidden text ('abc', '1,5m', '12.3.4m', '-5', '14%' in money, 'Infinity', '1e999', '') restores the previous value and flags the box.","parseAmount: 'anything else is rejected rather than silently truncated'");
inv("typed-plain-clamps-to-slider","Typed plain values are held to their slider's range and flagged (growth -90 -> -25%, margin 100 -> 92%, buyers 1000 -> 600 and 2 -> 5, years 0 -> 1 and 50 -> 12, delay 10000 -> $4,000, share kept 150 -> 100%); supported suffixes ('%', '/day', 'years', 'of value', 'none', unicode minus) parse.","commit(): 'held to the slider's range: say so'");
inv("box-shows-state","After every Enter each exact-value box shows the canonical formatting of what STATE.s holds.","labels(): 'the next render rewrites the box in the canonical format'");
inv("state-result-is-model-of-state","After every typed change STATE.r equals model(STATE.s) (value, P_C, proceeds, time, risk).","render(): r=model(readState())");
inv("extreme-states-render-clean","At extreme typed states (smallest and largest business, $1k and $100B asks, 5 and 600 buyers, 0 and 100% kept, $0 and $4,000 a day, $0 and $1B budget) the console text carries no NaN, Infinity or undefined once every equation is typeset, and no page error is thrown.","browser.sweep.js criterion extended to the typed extremes");
inv("typed-values-survive-rerender","Exact typed values (money to the cent, percentages and years with decimals) stay exactly in STATE.s through unrelated changes (industry, state, franchise) and re-renders.","INPUTS comment: 'A typed value outside that range is kept exactly; the slider simply rests at the end of its travel'; EXACT: 'typed values for stepped sliders, kept exactly until the slider is dragged'");
inv("earnings-clamp-follows-revenue","Typing a revenue below earnings/0.92 makes the model use 92% of revenue without storing it, and typing the revenue back restores the typed earnings.","readState comment: 'earnings cannot exceed 92% of revenue. Applied here without storing it'");
inv("exact-box-echo-within-2pct","An exact-value money box re-parses to within 2% of the value the model uses, typed or set by its slider (the millions format is already within 0.5%).","INPUTS comment: 'Money fields hold an exact value in IN'; aria-label '..., exact value'; precedent R3-6/R4-6 (KNOWN_FINDINGS: the budget echoed up to about 5% off was a confirmed defect)");
inv("buyer-count-kept-as-typed","A typed number of buyers to contact is kept exactly as typed, fractions included, and echoed as typed: EXACT keeps typed values by design and the model is continuous in the pool (an expected-offer count), so the stress test kept it.","EXACT comment ('typed values for stepped sliders, kept exactly'); stress test (fractional count refuted as intended)");
inv("score-independent-of-entry-order","The same final inputs give the same Omni score whatever order they were entered in.","refDistAt comments (see score-history-independent)");
inv("risk-tile-states-binding-loan-bound","Whenever the loan behind the survival risk is held at the $5M 7(a) cap, the risk tile says so (the $25k floor is documented on the Data tab and kept unflagged by the stress test).","R1-6 fix: the tile says 'SBA 7(a) notes cap at $5M ... the risk shown is for that note'; stress test (floor refuted)");

if(FLAGS.has("--list")){ for(const i of INV) console.log(`${i.name}\n  ${i.statement}\n  source: ${i.source}`); process.exit(0); }

/* ================================================================ model checks */
function outputsOK(r,s){
  const ctx=()=>({s:short(s)});
  const top=["V","Vbase","Vreal","Vmean","EVp","EVcash","deferred","PC","tMed","tMean","t90","t180","t365","ceil","askEff","capShare","cashShare",
    "compPrem","thinF","nEng","nEngRef","conf","qz","qPct","qFactor","M","rate","stratPrem","priceRatio","catMean","anchorF","rho"];
  const bad=[]; for(const k of top) if(!fin(r[k])) bad.push(k+"="+r[k]);
  for(const k of ["p","p5","p8","pTerm","rel","lgd","expLoss","loan","spread"]) if(!fin(r.risk[k])) bad.push("risk."+k+"="+r.risk[k]);
  for(const b of r.buyers) for(const k of ["PE","PCj","Pj","EV","Vj","S","sizeFit","fit"]) if(!fin(b[k])) bad.push(b.k+"."+k+"="+b[k]);
  for(const p of [.02,.1,.5,.9,.98]) if(!fin(r.q(p))) bad.push("q"+p);
  ok("corner-finite",bad.length===0,()=>({...ctx(),bad:bad.slice(0,6)}));
  const in01=x=>x>=0&&x<=1;
  const pr=[r.PC,r.risk.p,r.risk.p5,r.risk.p8,r.risk.pTerm,r.risk.expLoss,r.risk.lgd,r.capShare,r.cashShare,r.qPct,r.t90,r.t180,r.t365,r.conf];
  ok("corner-probabilities-in-range",pr.every(in01)&&r.buyers.every(b=>in01(b.PE)&&in01(b.PCj)&&in01(b.sizeFit)),()=>({...ctx(),pr}));
  const money=[r.Vbase,r.Vreal,r.Vmean,r.EVp,r.EVcash,r.deferred,r.ceil,r.askEff,r.stratPrem];
  ok("corner-money-nonnegative",r.V>0&&money.every(x=>x>=0)&&r.buyers.every(b=>b.Vj>=0&&b.Pj>=0&&b.EV>=0&&b.S>=0),()=>({...ctx(),money,V:r.V}));
  const capAsk=Math.max(s.ask,1)*Math.max(1,r.ft.pctAskSize)*(1+1e-9);
  ok("corner-ceiling-holds",r.Vreal<=r.ceil*(1+1e-9)&&r.Vmean<=r.ceil*(1+1e-9)&&r.q(.99)<=r.ceil*(1+1e-9)&&r.ceil<=capAsk,()=>({...ctx(),Vreal:r.Vreal,Vmean:r.Vmean,ceil:r.ceil,capAsk}));
  const qs=[.01,.02,.1,.25,.5,.75,.9,.98,.99].map(r.q);
  ok("corner-quantiles-ordered",qs.every((v,j)=>j===0||v>=qs[j-1]*(1-1e-12))&&Math.abs(r.q(.5)-r.Vreal)<=1e-9*r.Vreal&&r.Vmean>=r.q(.02)*(1-1e-9)&&r.Vmean<=r.ceil*(1+1e-9),()=>({...ctx(),qs}));
  ok("corner-proceeds-identities",Math.abs(r.EVp-r.PC*r.Vmean)<=1e-9*Math.max(1,r.EVp)&&Math.abs(r.EVcash-r.EVp*r.cashShare)<=1e-9*Math.max(1,r.EVp)&&r.EVcash<=r.EVp*(1+1e-12)&&r.deferred>=-1e-9,()=>({...ctx(),EVp:r.EVp,PC:r.PC,Vmean:r.Vmean}));
  const k=r.risk;
  ok("corner-risk-horizons-ordered",k.p5>0&&k.p5<k.p8&&k.p8<k.pTerm&&k.pTerm<1&&k.p===k.pTerm&&Math.abs(k.pTerm-k.p8*k.tail)<1e-12&&k.tail===A.tailAt(k.loan)&&k.expLoss>0&&k.expLoss<k.pTerm&&k.lgd>0&&k.lgd<1,()=>({...ctx(),p5:k.p5,p8:k.p8,p:k.pTerm,el:k.expLoss}));
  const kk=(Math.PI/r.betaT)/Math.sin(Math.PI/r.betaT); let cdf=r.F(0)===0, prev=-1;
  for(const f of [.01,.1,.3,.5,.8,1,1.5,2,3,5,10,20,50]){ const v=r.F(f*r.tMed); if(!(v>=prev&&v<=1)) cdf=false; prev=v; }
  ok("corner-time-curve-sane",fin(r.tMed)&&r.tMed>0&&Math.abs(r.tMean/(r.tMed*kk)-1)<1e-12&&r.tMean>r.tMed&&Math.abs(r.F(r.tMed)-.5)<1e-12&&cdf,()=>({...ctx(),tMed:r.tMed,tMean:r.tMean}));
  let sorted=true; for(let i=1;i<r.buyers.length;i++) if(r.buyers[i].EV>r.buyers[i-1].EV) sorted=false;
  ok("corner-buyers-sane",sorted&&r.buyers.every(b=>b.PE>=0&&b.PE<=.95&&b.PCj>=0&&b.PCj<=.95&&b.Pj<=Math.min(b.Vj,r.ceil)*(1+1e-9)&&Math.abs(b.EV-b.PE*b.PCj*b.Pj)<=1e-9*Math.max(1,b.EV)),()=>({...ctx(),b:r.buyers.map(b=>[b.k,b.PE,b.PCj,b.Pj,b.Vj])}));
  const QB=A.MODELS.value.quality_band;
  ok("corner-quality-factor-in-band",r.qFactor>=QB.lo*(1-1e-12)&&r.qFactor<=QB.hi*(1+1e-12)&&r.qPct>=0&&r.qPct<=1,()=>({...ctx(),qF:r.qFactor}));
}
const KEYOUT=r=>[r.V,r.Vbase,r.Vreal,r.Vmean,r.EVp,r.PC,r.tMed,r.tMean,r.ceil,r.capShare,r.compPrem,r.thinF,r.risk.p,r.risk.p5,r.risk.expLoss,r.conf,r.catMean,r.q(.1),r.q(.9),
  ...r.buyers.map(b=>b.EV),...Object.values(r.cats)];

function modelPart(){
  const t0=Date.now();
  /* ---- 1. random corner states ---- */
  const NC=+(process.env.NCORNER||1500);
  const corners=[];
  for(let i=0;i<NC;i++){
    const s=corner(); corners.push(s); const ctx=()=>({s:short(s)});
    const snap=JSON.stringify(s);
    const r=guard("corner-no-throw",()=>A.model(s),ctx); if(!r) continue; ok("corner-no-throw",true,ctx);
    outputsOK(r,s);
    ok("model-does-not-mutate-input",JSON.stringify(s)===snap,ctx);
    /* repeat with something else in between */
    A.model(corner()); const r2=A.model({...s});
    ok("model-repeatable",deepEq(KEYOUT(r),KEYOUT(r2)),ctx);
    /* value reads only business inputs */
    { const alt={...s,ask:s.ask*7.3+11,buyers:(s.buyers+17)*3,budget:s.budget+5e5,lamT:s.lamT+333,theta:1-s.theta,yrs:s.yrs+4.5,st:pick(STS),franchise:!s.franchise};
      const ra=A.model(alt); ok("value-reads-only-business-inputs",ra.V===r.V&&ra.Vbase===r.Vbase&&ra.M===r.M,()=>({...ctx(),V:r.V,Va:ra.V})); }
    /* years move only confidence and categories */
    { const ry=A.model({...s,yrs:s.yrs>=10?s.yrs-9.5:s.yrs+9.5});
      const same=["V","Vreal","Vmean","EVp","PC","tMed","tMean","ceil","capShare","compPrem","thinF"].every(k=>ry[k]===r[k])&&ry.risk.p===r.risk.p&&ry.buyers.every((b,j)=>b.EV===r.buyers[j].EV);
      ok("years-move-only-confidence-and-categories",same,()=>({...ctx(),EVp:[r.EVp,ry.EVp]})); }
    /* state and franchise move only risk */
    { const st2=pick(STS), rs=A.model({...s,st:st2,franchise:!s.franchise});
      const same=["V","Vreal","Vmean","EVp","PC","tMed","tMean","conf"].every(k=>rs[k]===r[k]);
      ok("state-and-franchise-move-only-risk",same,()=>({...ctx(),st2})); }
    /* quality never moves the size band, at a fixed ask at or below both values */
    if(i%3===0){ const sq={...s,...(s.own>.5?Q_DOM_BEST:Q_DOM_WORST)}; const Vq=Vof(sq), a=Math.min(r.V,Vq)*.9;
      const r1=A.model({...s,ask:a}), r2b=A.model({...sq,ask:a});
      ok("quality-never-moves-size-band",r1.Vbase!==r2b.Vbase||(r1.tMed===r2b.tMed&&r1.betaT===r2b.betaT&&r1.cashShare===r2b.cashShare&&r1.fc.base===r2b.fc.base),()=>({...ctx(),t:[r1.tMed,r2b.tMed]})); }
    /* heavier calls on a subsample */
    if(i%10===0){
      const sc=guard("corner-no-throw",()=>A.omniScore(r),ctx);
      const rs=guard("corner-no-throw",()=>A.bestRatio(s,0,0),ctx);
      if(sc!==undefined&&rs!==undefined){
        const bs=guard("corner-no-throw",()=>A.businessScore(s,r,rs),ctx);
        ok("corner-no-throw",true,ctx);
        if(bs) ok("corner-scores-in-1-99",[sc,bs.score,...Object.values(r.cats)].every(v=>Number.isInteger(v)&&v>=1&&v<=99)&&bs.score>=sc,()=>({...ctx(),sc,bs:bs.score,cats:r.cats}));
      }
    }
    if(i%5===0){
      const sn=guard("corner-no-throw",()=>A.sensitivity(s),ctx);
      if(sn){ let good=true, why=null;
        for(const row of sn){ if(![row.dV,row.dE,row.dP].every(fin)){ good=false; why=row.k+" not finite"; }
          if(row.h){ const outside=(s[row.k]+row.h>row.hi)||(s[row.k]-row.h<row.lo); if(!!row.oneSided!==outside&&!row.pinned){ good=false; why=row.k+" oneSided="+row.oneSided+" outside="+outside; } } }
        ok("sensitivity-finite-and-flags-edges",good,()=>({...ctx(),why})); }
      const s1={...s,rhoSell:A.bestRatio(s,0,0)};
      const it=guard("corner-no-throw",()=>A.interventionTable(s1,r),ctx);
      if(it){ let good=true, why=null;
        for(let j=0;j<it.length;j++){ const o=it[j];
          if(![o.dV,o.dE,o.dP,o.dT,o.dTnet,o.net].every(fin)){ good=false; why=o.k+" not finite"; }
          if(Math.abs(o.net-(o.dE-o.c))>1e-6*Math.max(1,Math.abs(o.net))){ good=false; why=o.k+" net"; }
          if(o.c>0&&Math.abs(o.roi-(o.dE-o.c)/o.c)>1e-9*Math.max(1,Math.abs(o.roi))){ good=false; why=o.k+" roi"; }
          if(Math.abs(o.dTnet-(o.days+o.dT))>1e-9*Math.max(1,o.dTnet)){ good=false; why=o.k+" dTnet"; }
          if(j>0&&o.net>it[j-1].net){ good=false; why="not sorted at "+o.k; } }
        ok("intervention-table-finite-and-sorted",good,()=>({...ctx(),why})); }
    }
    if(i%5===1){
      for(const [th,lam] of [[0,0],[.5,4000],[1,0],[1,1e6],[s.theta,s.lamT]]){
        const m=guard("corner-no-throw",()=>A.bestRatio(s,th,lam),ctx); if(m===undefined) continue;
        ok("bestRatio-finite-in-domain",fin(m)&&m>=.8-1e-9&&m<=A.RHO_MAX+1e-9,()=>({...ctx(),th,lam,m}));
        if(th===s.theta&&lam===s.lamT){ const V=Vof(s), U=x=>{ const q=A.model({...s,ask:V*x}); return q.EVp+(1-q.PC)*th*q.V-lam*q.tMean; };
          let g=-Infinity; for(let x=.80;x<=A.RHO_MAX+1e-9;x+=.02) g=Math.max(g,U(x));
          const um=U(m); ok("bestRatio-beats-its-grid",um>=g-1e-9*Math.max(1,Math.abs(g)),()=>({...ctx(),m,um,g})); }
      }
    }
    if(i%15===2){
      const t={...s}; t.rhoSell=A.bestRatio(s,0,0); t.optRho=A.bestRatio(s,s.theta,s.lamT); const V=Vof(s);
      const rS=A.model({...t,ask:V*t.rhoSell}), rK=A.model({...t,ask:V*t.optRho});
      const n=guard("corner-no-throw",()=>A.optNote(t,V,rS,rK),ctx);
      const bud=Math.min(s.budget,2e5);   /* the full 2^11 search is timed separately below */
      const best=guard("corner-no-throw",()=>A.optimize(t,r,bud,s.lamT,s.theta),ctx);
      if(best){
        const good=["V","U"].every(k=>best[k]&&[best[k].proceeds,best[k].PC,best[k].t,best[k].U,best[k].net].every(fin)&&best[k].c<=bud+1e-9)&&(bud>0||(best.V.c===0&&best.U.c===0));
        ok("optimize-terminates-feasible",good,()=>({...ctx(),bud,V:best.V&&best.V.keys,U:best.U&&best.U.keys}));
        const uRho=best.U.keys.includes("reprice")?t.optRho:t.rhoSell;
        const c=guard("corner-no-throw",()=>A.optCardNote(t,best,t.rhoSell,uRho),ctx);
        if(n&&c){ const txt=n.text+" "+c.text;
          ok("optimizer-texts-clean-at-corners",!/NaN|undefined|Infinity|[−-]\$/.test(txt)&&n.gain>=0,()=>({...ctx(),txt:txt.slice(0,240)})); }
      }
    }
  }
  /* corner-no-throw also counts the clean model calls */
  /* ---- 2. every industry x state x franchise at three sizes ---- */
  for(const ind of INDS) for(const st of STS) for(const franchise of [false,true]) for(const [rev,ern] of [[1e5,2e3],[6e6,1.45e6],[5e9,4.6e9]]){
    const s={...DEF,ind,st,franchise,rev,ern}; s.ask=Vof(s)*1.1; const ctx=()=>({s:short(s)});
    const r=guard("corner-no-throw",()=>A.model(s),ctx); if(!r) continue; ok("corner-no-throw",true,ctx); outputsOK(r,s);
    if(st){ const r0=A.model({...s,st:null}), se=A.MODELS.risk.state_effects[st], d=r.risk.p-r0.risk.p;
      ok("state-and-franchise-move-only-risk",(se>0?d>0:se<0?d<0:d===0)&&r.V===r0.V&&r.PC===r0.PC&&r.EVp===r0.EVp,()=>({...ctx(),se,d})); }
  }
  /* ---- 3. optimiser: repeatable, budget-monotone, full search at a few corners ---- */
  { const F=L.loadWith([]);
    for(let i=0;i<8;i++){ const s=i===0?{...DEF}:corner(); s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,s.theta,s.lamT);
      const ctx=()=>({s:short(s)}), r=A.model(s);
      const m2=A.bestRatio(s,s.theta,s.lamT), m3=F.bestRatio(s,s.theta,s.lamT);
      const budgets=i<4?[0,1e4,3e4,1e5,3e5,1e9]:[0,1e4,3e4,1e5,3e5];
      let pv=null, mono=true, why=null;
      for(const bud of budgets){ const b1=A.optimize(s,r,bud,s.lamT,s.theta);
        if(pv&&(b1.V.net<pv.V.net-1e-6*Math.max(1,Math.abs(pv.V.net))||b1.U.U<pv.U.U-1e-6*Math.max(1,Math.abs(pv.U.U)))){ mono=false; why={bud,net:[pv.V.net,b1.V.net],U:[pv.U.U,b1.U.U]}; }
        ok("optimize-terminates-feasible",["V","U"].every(k=>b1[k]&&[b1[k].proceeds,b1[k].PC,b1[k].t,b1[k].U].every(fin)&&b1[k].c<=bud+1e-9),()=>({...ctx(),bud}));
        if(bud===1e5){ const b2=A.optimize(s,r,bud,s.lamT,s.theta), b3=F.optimize(s,F.model(s),bud,s.lamT,s.theta);
          ok("optimizer-repeatable",m2===s.optRho&&m3===s.optRho&&b2.U.U===b1.U.U&&b3.U.U===b1.U.U&&JSON.stringify(b2.V.keys)===JSON.stringify(b1.V.keys)&&JSON.stringify(b3.U.keys)===JSON.stringify(b1.U.keys),ctx); }
        pv=b1; }
      ok("optimize-monotone-in-budget",mono,()=>({...ctx(),why}));
    } }
  /* ---- 4. applyAll order independence ---- */
  const KEYS=A.INTERV.map(x=>x.k);
  for(let i=0;i<300;i++){
    const s=i<150?corner():{...DEF,...pick(QSETS)}; s.rhoSell=1+rnd()*.4; const r=A.model(s), snap=JSON.stringify(s);
    const ks=KEYS.filter(()=>rnd()<.5); const base=A.applyAll(s,r,ks,s.rhoSell);
    let same=true, which=null;
    for(let p=0;p<6;p++){ const perm=ks.slice().sort(()=>rnd()-.5); const o=A.applyAll(s,r,perm,s.rhoSell);
      if(JSON.stringify(o)!==JSON.stringify(base)){ same=false; which=perm; } }
    const rev=A.applyAll(s,r,ks.slice().reverse(),s.rhoSell); if(JSON.stringify(rev)!==JSON.stringify(base)){ same=false; which=ks.slice().reverse(); }
    ok("applyAll-order-independent",same,()=>({s:short(s),keys:ks,perm:which}));
    ok("applyAll-does-not-mutate-input",JSON.stringify(s)===snap,()=>({s:short(s),keys:ks}));
  }
  /* ---- 5. limits ---- */
  for(let i=0;i<120;i++){
    const s=i<16?{...DEF,ind:INDS[i]}:corner(); const V=Vof(s), typ=A.IND[s.ind].buyers; const ctx=()=>({s:short(s)});
    if(s.buyers<1) s.buyers=typ;   /* limits in the ask are read on a pool that can close */
    /* ask up */
    let pv=null, mono=true, tmono=true, tfin=true;
    for(let e=0;e<=12;e+=.25){ const x=A.model({...s,ask:V*Math.pow(10,e)});
      if(pv&&x.PC>pv.PC+1e-15) mono=false; if(pv&&e>0.25&&!(x.tMed>pv.tMed)) tmono=false; if(!fin(x.tMed)) tfin=false; pv=x; }
    const r6=A.model({...s,ask:V*1e6});
    ok("limit-ask-up-pc-to-zero",mono&&r6.PC<1e-12&&r6.EVp<1e-9*V,()=>({...ctx(),PC6:r6.PC,EVp6:r6.EVp,mono}));
    ok("limit-ask-up-time-finite-rising",tmono&&tfin,()=>({...ctx(),tmono,tfin}));
    { const r2=A.model({...s,ask:V*2.2}); let flat=true, w=null;
      for(const m of [3,10,1e3,1e6,1e9,1e12]){ const x=A.model({...s,ask:V*m});
        for(const k of ["askEff","ceil","Vreal","Vmean"]) if(Math.abs(x[k]/r2[k]-1)>1e-9){ flat=false; w={m,k,a:r2[k],b:x[k]}; } }
      ok("limit-ask-up-price-flat",flat,()=>({...ctx(),w})); }
    { const ref=A.model({...s,ask:V}); let flat=true, w=null;
      for(const m of [1e-9,1e-6,1e-3,.1,.5,.9,.999999]){ const x=A.model({...s,ask:V*m});
        if(x.PC!==ref.PC||x.tMult!==1||x.tMed!==x.ft.days){ flat=false; w={m,PC:[ref.PC,x.PC],tMult:x.tMult}; } }
      ok("limit-ask-down-pc-flat",flat&&ref.tMult===1,()=>({...ctx(),w})); }
    /* buyers */
    { const a=V*1.1, r0=A.model({...s,buyers:0,ask:a}); let pv2=null, mono2=true;
      for(const b of [0,1e-6,.01,.1,.5,1,2,3,5,8,13,20,30,50,80,130,200,330,600,1e3,1e4,1e5]){ const x=A.model({...s,buyers:b,ask:a}); if(pv2&&x.PC<pv2.PC-1e-15) mono2=false; pv2=x; }
      ok("limit-pool-empty-pc-zero",r0.PC===0&&r0.thinF===0&&r0.EVp===0&&mono2,()=>({...ctx(),PC0:r0.PC,thinF0:r0.thinF,mono2}));
      const rt=A.model({...s,buyers:typ,ask:a}); let deep=true, cmono=true, pc=-Infinity, w=null;
      for(const b of [typ,typ+.5,typ*1.5,typ*3,600,1e3,1e4,1e5,1e6]){ const x=A.model({...s,buyers:b,ask:a});
        if(x.thinF!==1||x.PC!==rt.PC){ deep=false; w={b,thinF:x.thinF}; } if(x.compPrem<pc-1e-15||x.compPrem>.14+1e-15) cmono=false; pc=x.compPrem; }
      const r1e6=A.model({...s,buyers:1e6,ask:a});
      ok("limit-pool-deep-saturates",deep&&cmono&&Math.abs(r1e6.compPrem-.14)<1e-12,()=>({...ctx(),w,cmono,comp:r1e6.compPrem})); }
  }
  /* gap penalty shape */
  { let pv=-1, mono=true; const G=[0,1e-9,.5,1,5,10,15,20,25,30,35,40,45,50,60,75,99,99.999,100,100.001,101,150,200,500,1e3,1e4,1e5,1e6,1e7];
    for(const g of G){ const p=A.gapPenalty(g); if(!(p>=pv-1e-15&&p>=0&&p<=1)) mono=false; pv=p; }
    ok("limit-gap-penalty-shape",A.gapPenalty(0)===0&&A.gapPenalty(-5)===0&&mono&&A.gapPenalty(1e7)>1-1e-12,()=>({mono,p7:A.gapPenalty(1e7)}));
    for(const k of [10,20,30,40,50,100]){ const a=A.gapPenalty(k*(1-1e-9)), b=A.gapPenalty(k*(1+1e-9)), wa=A.gapPenalty(k*(1-1e-4)), wb=A.gapPenalty(k*(1+1e-4));
      ok("limit-gap-penalty-shape",Math.abs(b-a)<=1e-3*Math.abs(wb-wa)+1e-12,()=>({knot:k,a,b,wa,wb})); } }
  /* multiple flat above the $3M SDE cap */
  for(const ind of INDS) for(const m of [.02,.2,.6,.92]){
    const mult=e=>{ const f=A.fitValue(e,e/m,ind,2026); return f.point/e; };
    const m0=mult(3.05e6); let flat=true, w=null;
    for(const e of [3.5e6,1e7,1e8,1e9,1e10]){ const x=mult(e); if(Math.abs(x/m0-1)>1e-5){ flat=false; w={e,m0,x}; } }
    ok("limit-multiple-flat-above-cap",flat,()=>({ind,margin:m,w}));
  }
  /* helpers over $1-$1e13 */
  { const F=A.MODELS.fitted, sp=F.sba_rate.spread_knots.map(k=>k[1]); let pr=Infinity;
    for(let e=0;e<=13;e+=.05){ const x=Math.pow(10,e);
      const rt=A.sbaRate(x); ok("limit-helpers-bounded",rt>=F.sba_rate.prime+Math.min(...sp)-1e-12&&rt<=F.sba_rate.prime+Math.max(...sp)+1e-12&&rt<=pr+1e-12,()=>({fn:"sbaRate",x,rt})); pr=rt;
      const bm=A.buyerMix(x); ok("limit-helpers-bounded",[bm.individual,bm.strategic,bm.financial].every(v=>v>0&&v<1)&&Math.abs(bm.individual+bm.strategic+bm.financial-1)<1e-12,()=>({fn:"buyerMix",x,bm}));
      for(const ind of INDS){ const W=F.gm_wage, g=W.by_industry[ind], gs=A.gmSalary({ind,rev:x});
        ok("limit-helpers-bounded",fin(gs)&&gs>=g.p10*W.wage_growth-1e-6&&gs<=g.p90*W.wage_growth+1e-6,()=>({fn:"gmSalary",ind,x,gs}));
        const tm=A.typMargin(ind,x); ok("limit-helpers-bounded",fin(tm)&&tm>0,()=>({fn:"typMargin",ind,x,tm}));
        const wg=A.sdeEbitdaWedge(A.naicsFor(ind),x); ok("limit-helpers-bounded",wg===null||(wg>=1.02-1e-12&&wg<=2.75+1e-12),()=>({fn:"sdeEbitdaWedge",ind,x,wg})); } }
    let pc=-1; for(let x=-1;x<=2;x+=.001){ const c=A.capOne(x); ok("limit-helpers-bounded",c<=1&&c>=pc-1e-15,()=>({fn:"capOne",x,c})); pc=c; }
    for(let i=0;i<500;i++){ const a=logU(1,1e12), b=logU(1,1e12), m=A.softMin(a,b); ok("limit-helpers-bounded",m<=Math.min(a,b)*(1+1e-12)&&m>=Math.min(a,b)*Math.exp(-.012*Math.LN2)*(1-1e-12),()=>({fn:"softMin",a,b,m})); } }

  /* ---- 6. continuity scans (jump test with zoom confirmation) ---- */
  const OUT={V:[r=>r.V,"m"],Vbase:[r=>r.Vbase,"m"],Vreal:[r=>r.Vreal,"m"],Vmean:[r=>r.Vmean,"m"],EVp:[r=>r.EVp,"m"],EVcash:[r=>r.EVcash,"m"],
    PC:[r=>r.PC,"p"],tMed:[r=>r.tMed,"d"],tMean:[r=>r.tMean,"d"],t180:[r=>r.t180,"p"],riskp:[r=>r.risk.p,"p"],expLoss:[r=>r.risk.expLoss,"p"],
    cash:[r=>r.cashShare,"p"],comp:[r=>r.compPrem,"p"],thinF:[r=>r.thinF,"p"],capShare:[r=>r.capShare,"p"],ceil:[r=>r.ceil,"m"],askEff:[r=>r.askEff,"m"],
    rate:[r=>r.rate,"p"],nEng:[r=>r.nEng,"p"],qF:[r=>r.qFactor,"p"],conf:[r=>r.conf,"p"],strat:[r=>r.stratPrem,"m"],topVj:[r=>r.top.Vj,"m"],
    bestEV:[r=>r.buyers[0].EV,"m"],M:[r=>r.M,"p"],base:[r=>r.fc.base,"p"],pen:[r=>r.fc.pen,"p"],betaT:[r=>r.betaT,"p"],q10:[r=>r.q(.1),"m"],q90:[r=>r.q(.9),"m"],
    ebitdaMult:[r=>r.fv.ebitdaMult||0,"p"]};
  for(const k of ["ind","eta","pep","add","str","adj","fo","mbo"]){ OUT["PCj_"+k]=[r=>r.buyers.find(b=>b.k===k).PCj,"p"]; OUT["EV_"+k]=[r=>r.buyers.find(b=>b.k===k).EV,"m"]; }
  const tolOf=(kind,a,b,Vs)=>kind==="m"?1e-9*Vs+1e-6:kind==="d"?1e-9*Math.max(a,b):1e-10;
  function confirm(mk,o,x0,x1){   /* zoom into [x0,x1] 4 times; a real jump keeps its size as the step shrinks */
    const [f,kind]=OUT[o]; let a=x0,b=x1; const J0=Math.abs(f(A.model(mk(b)))-f(A.model(mk(a))));
    for(let lv=0;lv<4;lv++){ let bi=0,bd=-1; const xs=[]; for(let j=0;j<=20;j++) xs.push(a+(b-a)*j/20); const v=xs.map(x=>f(A.model(mk(x))));
      for(let j=0;j<20;j++){ const d=Math.abs(v[j+1]-v[j]); if(d>bd){ bd=d; bi=j; } } a=xs[bi]; b=xs[bi+1]; }
    const ra=A.model(mk(a)), rb=A.model(mk(b)), J=Math.abs(f(rb)-f(ra));
    return J>.5*J0&&J>tolOf(kind,Math.abs(f(ra)),Math.abs(f(rb)),Math.max(ra.V,rb.V))?{x:a,x2:b,a:f(ra),b:f(rb)}:null;
  }
  function scan(name,mk,xs,ctx){
    const rs=xs.map(x=>A.model(mk(x)));
    for(const o in OUT){ const [f,kind]=OUT[o]; const v=rs.map(f), d=[];
      for(let i=0;i<v.length-1;i++) d.push(Math.abs(v[i+1]-v[i]));
      let flagged=null;
      for(let i=0;i<d.length&&!flagged;i++){ const nb=[d[i-2],d[i-1],d[i+1],d[i+2]].filter(x=>x!==undefined), m=nb.length?Math.max(...nb):0;
        if(d[i]>20*m+tolOf(kind,v[i],v[i+1],Math.max(rs[i].V,rs[i+1].V))){ const c=confirm(mk,o,xs[i],xs[i+1]); if(c) flagged={o,...c}; } }
      ok(name,!flagged,()=>({...ctx,jump:flagged}));
      if(name==="continuous-in-ask"&&o==="capShare"){ /* the claim's own 0.1% test, at every scan point */
        let w=null; for(let i=0;i<xs.length;i+=7){ const c2=A.model(mk(xs[i]*1.001)).capShare; if(Math.abs(c2-v[i])>=.01){ w={x:xs[i],a:v[i],b:c2}; break; } }
        ok("ceiling-share-continuous",!w,()=>({...ctx,w})); }
    } }
  const geo=(lo,hi,N)=>{ const a=[]; for(let i=0;i<=N;i++) a.push(lo*Math.pow(hi/lo,i/N)); return a; };
  const lin=(lo,hi,N)=>{ const a=[]; for(let i=0;i<=N;i++) a.push(lo+(hi-lo)*i/N); return a; };
  for(const ind of INDS) for(const rev of [1e4,3e6,5e9]){ const rho=pick([.9,1.25]), b={...DEF,ind,rev};
    scan("continuous-in-earnings",x=>{ const s={...b,ern:x}; s.ask=rho*Vof(s); return s; },geo(1e3,rev*.92,500),{ind,rev,rho,scan:"ern"}); }
  for(const ind of INDS) for(const ern of [1e3,1.45e6]){ const rho=pick([.9,1.25]), b={...DEF,ind,ern};
    scan("continuous-in-revenue",x=>{ const s={...b,rev:x}; s.ask=rho*Vof(s); return s; },geo(ern/.92,1e11,500),{ind,ern,rho,scan:"rev"}); }
  for(const ind of INDS) for(const [rev,ern] of [[1e5,2e3],[6e6,1.45e6],[5e9,4e9]]){ const b={...DEF,ind,rev,ern}, V=Vof(b);
    scan("continuous-in-ask",x=>({...b,ask:V*x}),geo(1e-4,1e4,700),{ind,rev,ern,scan:"ask/V"}); }
  for(const ind of INDS) for(const [rev,ern,rho] of [[1e5,2e3,1],[5e9,4e9,.9]]){ const b={...DEF,ind,rev,ern}; b.ask=Vof(b)*rho;
    scan("continuous-in-buyers",x=>({...b,buyers:x}),geo(.01,1e5,600),{ind,rev,ern,scan:"buyers"}); }
  { const DOM={rec:[0,1],cc:[.005,.95],ret:[.05,.999],plt:[.02,.999],grw:[-.6,1.5],gm:[.02,.97],own:[.02,.99],mgt:[.02,.99],fin:[.02,1],yrs:[0,30]};
    for(const ind of ["medical","rest","saas","dist"]) for(const [rev,ern,rho] of [[1e5,2e3,1.3],[5e9,4e9,1.0]]) for(const k in DOM){ const b={...DEF,ind,rev,ern}, V=Vof(b);
      scan("continuous-in-quality",x=>({...b,[k]:x,ask:V*rho}),lin(DOM[k][0],DOM[k][1],300),{ind,rev,ern,rho,scan:k}); } }
  /* named thresholds: a +-1e-9 bracket */
  function bracket(mk,t,ctx){ const a=A.model(mk(t*(1-1e-9))), b=A.model(mk(t*(1+1e-9))), wa=A.model(mk(t*(1-1e-4))), wb=A.model(mk(t*(1+1e-4)));
    let w=null; for(const o in OUT){ const [f,kind]=OUT[o]; const d=Math.abs(f(b)-f(a)), dw=Math.abs(f(wb)-f(wa));
      if(d>1e-3*dw+tolOf(kind,Math.abs(f(a)),Math.abs(f(b)),Math.max(a.V,b.V))*10){ w={o,a:f(a),b:f(b),wide:dw}; break; } }
    ok("continuous-at-named-thresholds",!w,()=>({...ctx,t,w})); }
  const solveErn=(b,target,key)=>{ let lo=1e3, hi=b.rev*.92; const g=e=>A.model({...b,ern:e,ask:1})[key];
    if(g(lo)>target||g(hi)<target) return null; for(let k=0;k<80;k++){ const m=Math.sqrt(lo*hi); if(g(m)<target) lo=m; else hi=m; } return Math.sqrt(lo*hi); };
  const LR=A.MODELS.risk.loan_range, LS=A.MODELS.risk.loan_share;
  const vbKnots=[2.5e5,Math.sqrt(5e5*1e6),Math.sqrt(1e6*2e6),Math.sqrt(2e6*5e6),Math.sqrt(5e6*5e7),1e6,5e6];
  for(const ind of INDS){ const b={...DEF,ind,rev:5e8};
    for(const t of [1.5e5,3e6]) bracket(e=>{ const s={...b,ern:e}; s.ask=1.15*Vof({...b,ern:t}); return s; },t,{ind,threshold:"SDE "+t});
    const solveAny=(target,key)=>{ for(const rev of [1e4,1e5,1e6,2e7,5e8]){ const bb={...DEF,ind,rev}, e=solveErn(bb,target,key); if(e) return [bb,e]; } return null; };
    for(const [vt,key] of [...vbKnots.map(v=>[v,"Vbase"]),[LR[0]/LS,"V"],[LR[1]/LS,"V"]]){ const f=solveAny(vt,key);
      if(!f) continue;   /* this value is out of reach for the industry at its default quality */
      const [bb,e]=f; bracket(x=>{ const s={...bb,ern:x}; s.ask=1.15*vt; return s; },e,{ind,threshold:key+" "+vt.toFixed(0),rev:bb.rev}); }
    const s0={...DEF,ind}, V=Vof(s0);
    for(const k of [1,Math.exp(.1),1.1,1.2,1.3,1.4,1.5,2]) bracket(x=>({...s0,ask:x}),V*k,{ind,threshold:"ask/V "+k.toFixed(4)});
    const typ=A.IND[ind].buyers; bracket(x=>({...s0,buyers:x}),typ,{ind,threshold:"typical pool"});
    /* the capOne edge: the pool where the Poisson ratio reaches 1-THIN_W */
    { let lo=.01, hi=typ; const g=x=>{ const r=A.model({...s0,buyers:x}); return (1-Math.exp(-r.nPool))/(1-Math.exp(-r.nEngRef)); };
      for(let k=0;k<100;k++){ const m=(lo+hi)/2; if(g(m)<1-A.THIN_W) lo=m; else hi=m; } bracket(x=>({...s0,buyers:x}),(lo+hi)/2,{ind,threshold:"capOne edge"}); }
  }
  /* ---- 7. value never falls with earnings at the extremes; best beats worst ---- */
  for(const ind of INDS) for(const rev of [1e4,1e5,5e9,1e11]){ let pv=-1, mono=true, w=null;
    for(const e of geo(1e3,rev*.92,400)){ const v=Vof({...DEF,ind,rev,ern:e}); if(v<pv*(1-1e-12)){ mono=false; w={e,pv,v}; } pv=v; }
    ok("value-nondecreasing-in-earnings-extremes",mono,()=>({ind,rev,w})); }
  for(const ind of INDS) for(const [rev,ern] of SIZES.filter((x,j)=>j%2===0)){ const sb={...DEF,ind,rev,ern,...Q_UI_BEST}, sw={...DEF,ind,rev,ern,...Q_UI_WORST};
    const rb=A.model({...sb,ask:1}), rw=A.model({...sw,ask:1});
    let good=rb.V>rw.V;
    if(rev>=1e4&&rev<=5e9&&ind.length%3===0){ const ab=A.bestRatio(sb,0,0), aw=A.bestRatio(sw,0,0);
      const rb2=A.model({...sb,ask:rb.V*ab}), rw2=A.model({...sw,ask:rw.V*aw});
      good=good&&A.businessScore(sb,rb2,ab).score>=A.businessScore(sw,rw2,aw).score; }
    ok("best-quality-beats-worst",good,()=>({ind,rev,ern,Vb:rb.V,Vw:rw.V})); }
  /* ---- 8. the score's reference population is keyed on 6 significant digits: score a neighbour first ---- */
  { let inst=null; try{ inst=L.loadWith([["const REFC=new Map();","const REFC=new Map(); MODELS.__ref=s=>refDistAt(s);"]]); }catch(e){ inst=null; }
    const bases=[{...DEF},{...DEF,ind:"vet"},{...DEF,ind:"saas"},{...DEF,ind:"rest",rev:8e5,ern:1.9e5,buyers:41}];
    for(const B of bases){ const N2={...B,ern:B.ern*(1+2.5e-6)}; let tried=false;
      if(inst){ const I1=L.loadWith([["const REFC=new Map();","const REFC=new Map(); MODELS.__ref=s=>refDistAt(s);"]]);
        const Pold=inst.MODELS.__ref(B), Pown=I1.MODELS.__ref(N2); const sc=n=>Math.max(1,Math.min(99,Math.round(100*n/128)));
        const cand=[]; for(let i=0;i<128;i++) if(Pold.xs[i]!==Pown.xs[i]&&sc(i)!==sc(i+1)) cand.push(i); cand.sort((a,b)=>Math.abs(a-64)-Math.abs(b-64));
        const V=Vof(N2), lnE=ask=>Math.log(Math.max(A.model({...N2,ask}).EVp,1));
        for(const i of cand.slice(0,6)){ const lo=Math.min(Pold.xs[i],Pown.xs[i]), hi=Math.max(Pold.xs[i],Pown.xs[i]), tgt=(lo+hi)/2;
          let a1=V*1.15, a2=V*20; if(!(lnE(a1)>=tgt&&lnE(a2)<=tgt)) continue;
          for(let k=0;k<200;k++){ const m=(a1+a2)/2; if(lnE(m)>tgt) a1=m; else a2=m; }
          const ask=Math.round((a1+a2)/2*100)/100; if(!(lnE(ask)>lo&&lnE(ask)<hi)) continue;
          const F1=L.loadWith([]), F2=L.loadWith([]), S={...N2,ask};
          F1.omniScore(F1.model({...B,ask}));
          const stale=F1.omniScore(F1.model(S)), own=F2.omniScore(F2.model(S));
          ok("score-history-independent",stale===own,()=>({s:short(S),ern:String(S.ern),ask:String(S.ask),scoreAfterScoringNeighbourFirst:stale,neighbourErn:B.ern,scoreFresh:own}));
          if(stale!==own&&B.rev===DEF.rev&&B.ern===DEF.ern&&B.ind!==DEF.ind) ORDER_CASES.push({ind:B.ind,ern:N2.ern,ask});
          tried=true; break; } }
      if(!tried){ /* the instrumented search is unavailable (the cache was rewritten): check a plain neighbour pair */
        const F1=L.loadWith([]), F2=L.loadWith([]), S={...N2,ask:Vof(N2)*1.3}; F1.omniScore(F1.model({...B,ask:S.ask}));
        ok("score-history-independent",F1.omniScore(F1.model(S))===F2.omniScore(F2.model(S)),()=>({s:short(S)})); }
    }
    /* plus random near-neighbour pairs (rarely informative, but cheap) */
    for(let i=0;i<6;i++){ const s=corner(); if(s.ern<1e3||s.rev<1e4||s.buyers<1) continue; const F1=L.loadWith([]), F2=L.loadWith([]);
      F1.omniScore(F1.model({...s,ern:s.ern*(1+3e-6)})); ok("score-history-independent",F1.omniScore(F1.model(s))===F2.omniScore(F2.model(s)),()=>({s:short(s)})); }
  }
  return (Date.now()-t0)/1000;
}

/* ================================================================ browser checks */
async function browserPart(){
  let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
  const URL="file://"+path.join(ROOT,"index.html");
  const b=await pw.chromium.launch();
  const open=async()=>{ const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); const p=await ctx.newPage();
    const errs=[]; p.on("pageerror",e=>errs.push(e.message)); await p.goto(URL); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
    return {ctx,p,errs}; };
  const settle=p=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())),60)));
  const P1=s=>{ const x=Math.round(s*1000)/10; return (Number.isInteger(x)?x.toFixed(0):x.toFixed(1))+"%"; };
  const t0=Date.now();
  const {ctx,p,errs}=await open();
  const state=()=>p.evaluate(()=>({s:{...STATE.s},box:Object.fromEntries([...document.querySelectorAll("input.v")].map(e=>[e.id,{v:e.value,bad:e.classList.contains("bad")}])),
    same:(()=>{ const r=model(STATE.s); return r.V===STATE.r.V&&r.PC===STATE.r.PC&&r.EVp===STATE.r.EVp&&r.tMed===STATE.r.tMed&&r.risk.p===STATE.r.risk.p; })(),
    canon:{v_rev:moneyIn(STATE.s.rev),v_ern:moneyIn(STATE.s.ern),v_ask:moneyIn(STATE.s.ask),v_bud:STATE.s.budget?moneyIn(STATE.s.budget):"none",
      v_buy:String(STATE.s.buyers),v_yrs:STATE.s.yrs+(STATE.s.yrs===1?" year":" years"),v_lam:STATE.s.lamT?"$"+STATE.s.lamT.toLocaleString("en-US")+"/day":"none"}}));
  const type=async(id,txt)=>{ await p.click("#"+id); await p.keyboard.press("Control+A"); if(txt==="") await p.keyboard.press("Backspace"); else await p.keyboard.type(txt); await p.keyboard.press("Enter"); await settle(p); };
  const check=async(tag)=>{ const x=await state(); const s=x.s;
    const want={...x.canon,v_grw:P1(s.grw),v_gm:P1(s.gm),v_rec:P1(s.rec),v_cc:P1(s.cc),v_ret:P1(s.ret),v_plt:P1(s.plt),v_th:P1(s.theta)};
    const diff=Object.keys(want).filter(k=>x.box[k].v!==want[k]).map(k=>[k,x.box[k].v,want[k]]);
    ok("box-shows-state",diff.length===0,()=>({tag,diff}));
    ok("state-result-is-model-of-state",x.same,()=>({tag})); return x; };
  const MK={v_rev:"rev",v_ern:"ern",v_ask:"ask",v_bud:"budget"};
  /* money forms */
  for(const [id,txt,want] of [["v_rev","$1.45M",1.45e6],["v_rev","1,450,000",1.45e6],["v_rev","1.45m",1.45e6],["v_ask","450k",4.5e5],["v_ask","2.5b",2.5e9],
      ["v_rev","1e6",1e6],["v_ask",".5m",5e5],["v_rev","1 000 000",1e6],["v_ask","$1,234,567.89",1234567.89],["v_ask"," 450 K ",4.5e5],["v_bud","none",0],["v_bud","2.5M",2.5e6]]){
    await p.click("#reset"); await settle(p); await type(id,txt); const x=await check(id+"="+txt);
    ok("typed-money-parses",x.s[MK[id]]===want&&!x.box[id].bad,()=>({id,txt,got:x.s[MK[id]],want,bad:x.box[id].bad})); }
  /* money clamps */
  for(const [id,txt,want] of [["v_rev","1k",1e4],["v_rev","9b",5e9],["v_ask","1",1e3],["v_ask","1e12",1e11],["v_bud","2b",1e9],["v_ern","1",1e3],["v_ern","20m",.92*6e6]]){
    await p.click("#reset"); await settle(p); await type(id,txt); const x=await check(id+"="+txt);
    ok("typed-money-clamps-and-flags",Math.abs(x.s[MK[id]]-want)<=1e-6*want&&x.box[id].bad,()=>({id,txt,got:x.s[MK[id]],want,bad:x.box[id].bad})); }
  /* junk */
  for(const [id,txt] of [["v_rev","abc"],["v_ask","1,5m"],["v_ask","12.3.4m"],["v_ern","-5"],["v_ask","14%"],["v_rev","Infinity"],["v_rev","1e999"],["v_ern",""],["v_buy","lots"],["v_th","NaN"]]){
    await p.click("#reset"); await settle(p); const x0=await state(); await type(id,txt); const x=await check(id+"="+txt);
    const sameState=JSON.stringify({...x.s,optRho:0,rhoSell:0})===JSON.stringify({...x0.s,optRho:0,rhoSell:0});
    ok("typed-junk-restores-and-flags",sameState&&x.box[id].bad,()=>({id,txt,bad:x.box[id].bad,sameState})); }
  /* plain fields: clamps and suffixes */
  for(const [id,txt,key,want,bad] of [["v_grw","-90","grw",-.25,true],["v_gm","100","gm",.92,true],["v_buy","1000","buyers",600,true],["v_buy","2","buyers",5,true],
      ["v_yrs","0","yrs",1,true],["v_yrs","50","yrs",12,true],["v_lam","10000","lamT",4000,true],["v_th","150","theta",1,true],
      ["v_grw","−5%","grw",-.05,false],["v_lam","$1.2k/day","lamT",1200,false],["v_yrs","3 years","yrs",3,false],["v_th","60% of value","theta",.6,false],["v_lam","none","lamT",0,false],["v_cc","2.5","cc",.025,false]]){
    await p.click("#reset"); await settle(p); await type(id,txt); const x=await check(id+"="+txt);
    ok("typed-plain-clamps-to-slider",Math.abs(x.s[key]-want)<1e-12&&x.box[id].bad===bad,()=>({id,txt,got:x.s[key],want,bad:x.box[id].bad})); }
  /* typed exact values survive unrelated changes */
  { await p.click("#reset"); await settle(p);
    for(const [id,v] of [["v_ern","1,234,567.89"],["v_ask","4,976,071.77"],["v_bud","12,345"],["v_grw","14.25"],["v_th","62.5"],["v_yrs","2.5"],["v_lam","1234.5"]]) await type(id,v);
    const want={ern:1234567.89,ask:4976071.77,budget:12345,grw:.1425,theta:.625,yrs:2.5,lamT:1234.5};
    const read=async()=>p.evaluate(()=>({ern:STATE.s.ern,ask:STATE.s.ask,budget:STATE.s.budget,grw:STATE.s.grw,theta:STATE.s.theta,yrs:STATE.s.yrs,lamT:STATE.s.lamT}));
    for(const step of [["i_ind","saas"],["i_st","TX"],["fr"],["i_ind","medical"],["i_st",""]]){
      if(step[0]==="fr") await p.click("#i_fr"); else await p.selectOption("#"+step[0],step[1]); await settle(p);
      const got=await read(); const diff=Object.keys(want).filter(k=>Math.abs(got[k]-want[k])>1e-12*Math.max(1,Math.abs(want[k])));
      ok("typed-values-survive-rerender",diff.length===0,()=>({after:step.join("="),diff:diff.map(k=>[k,got[k],want[k]])})); await check("survive "+step.join("=")); }
    await p.click("#i_fr"); await settle(p); }
  /* the earnings clamp follows typed revenue and is not stored */
  { await p.click("#reset"); await settle(p); await type("v_rev","1m");
    let x=await p.evaluate(()=>({ern:STATE.s.ern,IN:IN.ern,rev:STATE.s.rev}));
    ok("earnings-clamp-follows-revenue",Math.abs(x.ern-.92e6)<1e-6&&x.IN===1.45e6,()=>({step:"rev 1m",...x}));
    await type("v_rev","6m"); x=await p.evaluate(()=>({ern:STATE.s.ern,IN:IN.ern,rev:STATE.s.rev}));
    ok("earnings-clamp-follows-revenue",x.ern===1.45e6,()=>({step:"rev back to 6m",...x})); await check("ern clamp"); }
  /* the exact-value money boxes echo what the model uses */
  for(const [id,key,txt] of [["v_ern","ern","1,499"],["v_ern","ern","2,499"],["v_ask","ask","1,499"],["v_bud","budget","5,499"],["v_rev","rev","10,499"],["v_ern","ern","49,499"],["v_rev","rev","1,234,567"],["v_ask","ask","987,654,321"]]){
    await p.click("#reset"); await settle(p); if(id!=="v_rev") await type("v_rev","100k"); await type(id,txt);
    const x=await p.evaluate(([id,key])=>({box:document.getElementById(id).value,v:STATE.s[key],back:parseAmount(document.getElementById(id).value)}),[id,key]);
    ok("exact-box-echo-within-2pct",Math.abs(x.back/x.v-1)<=.02,()=>({typed:txt,box:x.box,model_uses:x.v,off:+((x.back/x.v-1)*100).toFixed(1)+"%"})); }
  { await p.click("#reset"); await settle(p); await type("v_rev","100k");
    for(const pos of [40,150,400]){ await p.$eval("#i_ern",(e,v)=>{ e.value=v; e.dispatchEvent(new Event("input",{bubbles:true})); },pos); await settle(p);
      const x=await p.evaluate(()=>({box:document.getElementById("v_ern").value,v:STATE.s.ern,back:parseAmount(document.getElementById("v_ern").value)}));
      ok("exact-box-echo-within-2pct",Math.abs(x.back/x.v-1)<=.02,()=>({earningsSliderPos:pos,box:x.box,model_uses:+x.v.toFixed(2),off:+((x.back/x.v-1)*100).toFixed(1)+"%"})); } }
  /* a count of buyers */
  { await p.click("#reset"); await settle(p); await type("v_buy","63.7"); const x=await check("v_buy=63.7"); await type("v_buy","12.5"); const y=await check("v_buy=12.5");
    const capt=await p.evaluate(()=>document.getElementById("o_cap").textContent);
    ok("buyer-count-kept-as-typed",x.s.buyers===63.7&&x.box.v_buy.v==="63.7"&&!x.box.v_buy.bad,()=>({typed:"63.7",STATE_buyers:x.s.buyers,box:x.box.v_buy.v}));
    ok("buyer-count-kept-as-typed",y.s.buyers===12.5&&capt.includes("Contacting 12.5 buyers"),()=>({typed:"12.5",STATE_buyers:y.s.buyers,caption:capt.slice(capt.indexOf("Contacting"))})); }
  /* extreme states render clean */
  const EXT=[
    {name:"smallest-worst",fill:[["v_rev","10k"],["v_ern","9.2k"],["v_ask","1k"],["v_buy","5"],["v_grw","-25"],["v_gm","12"],["v_rec","0"],["v_cc","70"],["v_ret","45"],["v_plt","95"],["v_yrs","1"],["v_lam","4000"],["v_th","0"],["v_bud","0"]],sel:{i_own:"0.95",i_mgt:"0.08",i_fin:"0.14",i_ind:"rest"}},
    {name:"smallest-ask-100B",fill:[["v_ask","100b"]]},
    {name:"slider-min-worst",fill:[["v_rev","100k"],["v_ern","2k"],["v_ask","15k"]]},
    {name:"largest-best",fill:[["v_rev","5b"],["v_ern","4.6b"],["v_ask","1k"],["v_buy","600"],["v_grw","70"],["v_gm","92"],["v_rec","100"],["v_cc","1"],["v_ret","99"],["v_plt","5"],["v_yrs","12"],["v_lam","0"],["v_th","100"],["v_bud","1b"]],sel:{i_own:"0.14",i_mgt:"0.92",i_fin:"0.96",i_ind:"saas",i_st:"CA"},fr:true},
    {name:"largest-ask-100B",fill:[["v_ask","100b"],["v_bud","100k"]]},
    {name:"5B-revenue-1k-earnings",fill:[["v_ern","1k"],["v_ask","4m"]]}];
  for(const st of EXT){
    for(const [id,v] of st.fill) await type(id,v);
    for(const k in st.sel||{}){ await p.selectOption("#"+k,st.sel[k]); await settle(p); }
    if(st.fr){ await p.click("#i_fr"); await settle(p); }
    await p.waitForTimeout(250);
    const res=await p.evaluate(()=>{ for(const id of [...EQ.pending.keys()]) eqSet(id);
      const t=document.getElementById("view-console").innerText, m=t.match(/.{0,60}(NaN|Infinity|undefined).{0,30}/);
      const k=STATE.r.risk, R=MODELS.risk, V=STATE.r.V, tile=document.getElementById("o_risk").innerText;
      return {bad:m?m[0].replace(/\s+/g," "):null, V, loan:k.loan, loanShare:R.loan_share, lo:R.loan_range[0], hi:R.loan_range[1], tile:tile.replace(/\s+/g," ").slice(0,260)}; });
    await check(st.name);
    ok("extreme-states-render-clean",!res.bad&&errs.length===0,()=>({state:st.name,bad:res.bad,errs:errs.slice(0,2)}));
    const bound=res.loanShare*res.V>res.hi;   /* the $5M cap; the $25k floor is documented on the Data tab (stress test) */
    if(bound) ok("risk-tile-states-binding-loan-bound",/cap|7\(a\)/i.test(res.tile),()=>({state:st.name,V:+res.V.toFixed(0),loan:res.loan,loanPctOfValue:+(res.loan/res.V*100).toFixed(0),tile:res.tile}));
  }
  await ctx.close();
  /* the same final inputs entered in two orders */
  { const run=async(order)=>{ const o=await open();
      for(const st of order){ if(st[0]==="sel"){ await o.p.selectOption("#"+st[1],st[2]); await settle(o.p); } else { await o.p.fill("#"+st[0],st[1]); await o.p.press("#"+st[0],"Enter"); await settle(o.p); } }
      await o.p.waitForTimeout(250);
      const x=await o.p.evaluate(()=>({s:{ind:STATE.s.ind,rev:STATE.s.rev,ern:STATE.s.ern,ask:STATE.s.ask},EVp:STATE.r.EVp,score:+document.getElementById("o_score").textContent}));
      await o.ctx.close(); return x; };
    const cases=ORDER_CASES.length?ORDER_CASES.slice(0,2).map(c=>[c.ind,String(c.ern),String(c.ask)]):[["vet","1,450,004","8,255,153.78"]];
    for(const [ind,ern,ask] of cases){
      const a=await run([["sel","i_ind",ind],["v_ern",ern],["v_ask",ask]]), c=await run([["v_ern",ern],["sel","i_ind",ind],["v_ask",ask]]);
      const sameIn=JSON.stringify(a.s)===JSON.stringify(c.s)&&a.EVp===c.EVp;
      ok("score-independent-of-entry-order",!sameIn||a.score===c.score,()=>({inputs:a.s,EVp:a.EVp,scoreIndustryFirst:a.score,scoreEarningsFirst:c.score})); } }
  await b.close();
  return (Date.now()-t0)/1000;
}

/* ================================================================ main */
const BROWSER_INV=new Set(["exact-box-echo-within-2pct","typed-values-survive-rerender","earnings-clamp-follows-revenue","typed-money-parses","typed-money-clamps-and-flags","typed-junk-restores-and-flags","typed-plain-clamps-to-slider","box-shows-state",
  "state-result-is-model-of-state","extreme-states-render-clean","buyer-count-kept-as-typed","score-independent-of-entry-order","risk-tile-states-binding-loan-bound"]);
(async()=>{
  let tm=0, tb=0;
  if(!FLAGS.has("--browser-only")) tm=modelPart();
  if(!FLAGS.has("--no-browser")) tb=await browserPart();
  let nf=0;
  for(const i of INV){ const o=RES[i.name]; if(!o.cases&&((FLAGS.has("--no-browser")&&BROWSER_INV.has(i.name))||(FLAGS.has("--browser-only")&&!BROWSER_INV.has(i.name)))) continue;
    if(o.fails){ nf++; console.log(`FAIL ${i.name} cases=${o.cases} fails=${o.fails} first=${fmt(o.first)}`); }
    else console.log(`PASS ${i.name} cases=${o.cases}`); }
  console.log(`# ${INV.length} invariants, ${nf} failing; model ${tm.toFixed(0)} s, browser ${tb.toFixed(0)} s; root ${ROOT}`);
  process.exit(nf?1:0);
})();
