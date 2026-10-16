#!/usr/bin/env node
/* In-app invariants for The Omni Method (the "app" lens).
   Drives <root>/index.html in headless Chromium, enters stress states through the UI controls (exact-value
   fields + Enter, selects, the franchise checkbox, keyboard on sliders), and asserts that every figure and
   every directional word the page shows agrees with a fresh evaluation of the same state through
   <root>/tests/load.js, and that the page's own components agree with each other.
   Part A (node, fast) fine-scans the display rules that render() applies to the model's numbers to find
   adversarial states; Part B (browser) asserts in the live page on designed corners, random states and the
   adversarial states Part A found.
   Usage: node invariants.js [root] [--random N] [--no-browser] [--json out.json]
          [--no-scan] [--no-states] [--only a,b] [--no-seq] [--no-sweep] [--no-phone] [--no-motion]
   Runtime: part A (node scans) about 80 s; part B (browser) about 15 min with --random 16 (about 7 s per state).
   Prints one line per invariant: PASS <name> cases=<n> | FAIL <name> cases=<n> fails=<k> first=<counterexample>. */
"use strict";
const path=require("path"), fs=require("fs");
const argv=process.argv.slice(2);
const ROOT=path.resolve(argv[0]&&!argv[0].startsWith("--")?argv[0]:path.join(__dirname,"..",".."));
const opt=(k,d)=>{ const i=argv.indexOf(k); return i>=0?(argv[i+1]===undefined?true:argv[i+1]):d; };
const NRAND=+opt("--random",8), NOBROWSER=argv.includes("--no-browser"), JSONOUT=opt("--json",null), NOSCAN=argv.includes("--no-scan"), ONLY=opt("--only",null), NOSEQ=argv.includes("--no-seq"), NOPHONE=argv.includes("--no-phone"), NOMOTION=argv.includes("--no-motion"), NOSTATES=argv.includes("--no-states"), NOSWEEP=argv.includes("--no-sweep");
const A=require(path.join(ROOT,"tests","load.js"));
/* sizeAnchor and M_TYP are not exported by load.js; the Data tab's live self-audit reads them */
const AX=A.loadWith([["const M_TYP=1.071;","const M_TYP=1.071; MODELS.__x={sizeAnchor:function(e){return sizeAnchor(e);},M_TYP:M_TYP};"]]);
const sizeAnchor=AX.MODELS.__x.sizeAnchor, M_TYP=AX.MODELS.__x.M_TYP;

/* ------------------------------------------------------------------ registry */
const INV={}, ORDER=[];
function def(name,statement,source){ INV[name]={name,statement,source,cases:0,fails:0,first:null,all:[],note:""}; ORDER.push(name); }
function ok(name,cond,ctx){ const v=INV[name]; if(!v) throw new Error("undefined invariant "+name); v.cases++;
  if(!cond){ v.fails++; let c; try{ c=typeof ctx==="function"?ctx():ctx; }catch(e){ c="(ctx error "+e.message+")"; } if(v.first===null) v.first=c; if(v.all.length<25) v.all.push(c); } }
const J=o=>JSON.stringify(o,(k,v)=>typeof v==="number"&&isFinite(v)?+v.toPrecision(7):v);

/* ------------------------------------------------------------------ the page's formatters (copied verbatim) */
const money=A.money;
const pc=(v,d)=>isFinite(v)?(v*100).toFixed(d===undefined?0:d)+"%":"—";
const pp=v=>isFinite(v)?(v>=0?"+":"−")+Math.abs(v*100).toFixed(1)+" pts":"—";
const xx=v=>v.toFixed(2)+"×";
const tn=v=>Math.round(v).toLocaleString("en-US");
const ordn=n=>{ const a=n%10,b=n%100; return n+((a===1&&b!==11)?"st":(a===2&&b!==12)?"nd":(a===3&&b!==13)?"rd":"th"); };
const p1=v=>{ const x=Math.round(v*1000)/10; return (Number.isInteger(x)?x.toFixed(0):x.toFixed(1))+"%"; };
function parseAmount(t){   /* index.html parseAmount, verbatim */
  t=String(t).trim().toLowerCase();
  if(/,\d{1,2}(?!\d)/.test(t)||/,\d{4}/.test(t)) return NaN;
  t=t.replace(/[$,\s]/g,"").replace(/\u2212/g,"-");
  if(t==="none") return 0;
  t=t.replace(/(\/day|years?|ofvalue)$/,"");
  const m=t.match(/^(-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)([kmb%])?$/); if(!m) return NaN;
  const v=Number(m[1])*({k:1e3,m:1e6,b:1e9}[m[2]]||1);
  return isFinite(v)?v:NaN;
}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
/* ------------------------------------------------------------------ parsing of displayed text */
const MRE=/([−-]?)\$(\d+(?:\.\d+)?)([kMB]?)/;
const MREG=/([−-]?)\$(\d+(?:\.\d+)?)([kMB]?)/g;
function pm(s){ const m=MRE.exec(String(s||"")); if(!m) return NaN; return (m[1]?-1:1)*parseFloat(m[2])*({k:1e3,M:1e6,B:1e9}[m[3]]||1); }
function pmAll(s){ return [...String(s||"").matchAll(MREG)].map(m=>(m[1]?-1:1)*parseFloat(m[2])*({k:1e3,M:1e6,B:1e9}[m[3]]||1)); }
function ppc(s){ const m=/([−-]?\d+(?:\.\d+)?)%/.exec(String(s||"")); return m?parseFloat(m[1].replace("−","-"))/100:NaN; }
/* half a display unit of money(v) */
function mtol(v){ const a=Math.abs(v); return a>=999.5e6?5e6:a>=999.5e3?5e3:a>=999.5?500:0.5; }
function texNorm(t){ if(t==null) return null; let x=String(t);
  for(let i=0;i<5;i++) x=x.replace(/\\text\{([^{}]*)\}/g,"$1");
  return x.replace(/\{,\}/g,",").replace(/\\\$/g,"$").replace(/\\%/g,"%").replace(/\\[,;:!]/g," ").replace(/\{:\}/g,":")
          .replace(/\\(?:qquad|quad)/g," ").replace(/\\begin\{aligned\}|\\end\{aligned\}/g," ").replace(/\\\\(\[[^\]]*\])?/g," ").replace(/&/g,"")
          .replace(/\u2212/g,"-").replace(/\s+/g," "); }
const dm=s=>String(s).replace(/\u2212/g,"-");
function seqIn(str,tokens){ let pos=0; for(const t of tokens){ const i=str.indexOf(dm(t),pos); if(i<0) return {ok:false,missing:t,at:pos}; pos=i+String(t).length; } return {ok:true}; }

/* ------------------------------------------------------------------ fresh evaluation of a state (node) */
function expect(s0){
  const s={...s0}; delete s.optRho; delete s.rhoSell;
  const r=A.model(s); r.score=A.omniScore(r);
  const optRho=A.bestRatio(s,s.theta,s.lamT), rhoSell=A.bestRatio(s,0,0);
  const t={...s,optRho,rhoSell};
  const bs=A.businessScore(t,r,rhoSell), rA=bs.rA, rq=bs.rq, askOpt=bs.askOpt;
  const sA=Math.max(r.score,Math.min(bs.score,A.omniScore(rA))), askPts=sA-r.score, poolPts=bs.score-sA;
  const loss=1-r.EVp/Math.max(rA.EVp,1), poolLoss=bs.thin?1-rA.EVp/Math.max(rq.EVp,1):0;
  const rSell=A.model({...t,ask:r.V*rhoSell}), rKeep=A.model({...t,ask:r.V*optRho});
  const note=A.optNote(t,r.V,rSell,rKeep);
  const best=A.optimize(t,r,t.budget,t.lamT,t.theta);
  const uRho=best.U.keys.includes("reprice")?optRho:rhoSell;
  const cnote=A.optCardNote(t,best,rhoSell,uRho);
  const sn=A.sensitivity(t), it=A.interventionTable(t,r);
  let allKeys=A.INTERV.map(o=>o.k);                        /* render(): the value-gap set, pruned */
  for(let pass=0;pass<A.INTERV.length;pass++){
    const vAll=A.model(A.applyAll(t,r,allKeys)).V; let drop=null, bestV=vAll-Math.max(1,vAll*1e-6);
    for(const k of allKeys){ if(k==="reprice") continue; const v=A.model(A.applyAll(t,r,allKeys.filter(x=>x!==k))).V; if(v>=bestV){ bestV=v; drop=k; } }
    if(!drop) break; allKeys=allKeys.filter(x=>x!==drop); }
  const rAll=A.model(A.applyAll(t,r,allKeys)), cAll=A.costOf(t,allKeys), gap=rAll.V-r.V;
  const rRep=A.model(A.applyAll(t,r,["reprice"]));
  return {s,t,r,optRho,rhoSell,bs,rA,rq,askOpt,sA,askPts,poolPts,loss,poolLoss,rSell,rKeep,note,best,uRho,cnote,sn,it,allKeys,rAll,cAll,gap,rRep};
}
const intRow=(o,V)=>({c:o.c?A.moneyIn(o.c):"no capital",
  dV:Math.abs(o.dV)<V*1e-4?"—":(o.dV>=0?"+":"−")+money(Math.abs(o.dV),2),
  dE:(o.dE>=0?"+":"−")+money(Math.abs(o.dE),2),
  dP:Math.abs(o.dP)<5e-4?"—":pp(o.dP),
  net:(o.dTnet>=0?"+":"−")+Math.abs(o.dTnet).toFixed(0),
  roi:o.roi===null?"—":(o.roi<0?"−":"")+Math.abs(o.roi*100).toFixed(0)+"%"});
const SIGNED_ZERO=/(^|[^\d.,\w])[−-]\$0(?![\d.])|(^|[^\d.,\w])[−-]0(?:\.0+)?(?=%|σ|×|\s*pts|\s*$)/;

/* ================================================================== invariants */
def("ui-typed-values-reach-state","Every value entered through an exact-value field (then Enter), a select or the franchise checkbox reaches STATE.s exactly as the field's own parser reads it, held to the documented hard range (money) or the slider's range (the rest); earnings above 92% of revenue are held at 92%.","index.html wireInputs()/commit() and readState() comments");
def("ui-clamped-entry-marked","A typed value that had to be held to its range is outlined (.bad); one that was taken as typed is not.","commit(): 'held to the slider's range: say so'");
def("ui-boxes-echo-state","After the render every exact-value box shows the state in the canonical format (money, one-decimal percent, years, buyers, budget, $/day).","labels(); 'the next render rewrites the box in the canonical format'");
def("ui-ask-ratio-caption","The caption under the ask reads ask/V to two decimals and money(V).","render(): vx_ask");
def("page-equals-fresh-model","STATE.r (V, P_C, E[proceeds], median days) and the two optimal ratios on STATE.s equal a fresh tests/load.js evaluation of STATE.s: no figure depends on what was rendered before.","refDistAt/omniScore comments (a pure function of the state); economics");
def("scores-history-independent","The displayed Omni and business scores equal omniScore/businessScore evaluated fresh on STATE.s.","refDistAt comment: 'the same business could score differently depending on what had been rendered before it' (fixed)");
def("hero-tiles-equal-model","Model value, chance of closing, expected proceeds (+cash at close), price if it closes, multiple (SDE and EBITDA), median days and 'Pursue first' equal the model's figures in the page's formats.","render() hero block");
def("focal-planet-equals-tile","The focal planet's canvas percentage equals the 'Chance of closing' tile and its target equals P_C.","v3 focal(): 'the reading: always the model's figure, the same one the tile shows'");
def("focal-legend-equals-scenarios","Bear / Median / Bull sale equal the 8th, 50th and 94th percentiles of the price if it closes, which are also eq_ss's P_0.08/P_0.50/P_0.94 and the scenario cards' outer ends.","drawOrbit(): 'prices if it closes, like the scenario cards'");
def("price-tile-subline-rules","The price tile's sub-line: 'nearly every closing at the ask ceiling' iff the 80% range is under 0.5% wide, otherwise '80% between q10 and q90'; '· X% at the ask ceiling' iff the ceiling share is at least 30% (X = that share), with 'of $ceiling' iff the ceiling sits more than 1% under the ask.","render(): o_val comment");
def("risk-tile-consistent","The risk tile shows p (1 dp), the ratio to the average loan unless the 7(a) cap binds, the 5-year figure, and the cap note iff 85% of value exceeds $5M; displayed p / displayed ratio equals the displayed average-loan rate within rounding.","render() risk block; economics (rel = p/base)");
def("badges-follow-rules","Provenance badges follow their rules: closing 'aggregate × judgment' iff thin pool or a gap penalty; value and multiple 'fitted × judgment' iff the quality factor is off 1 by >0.5%; time 'fitted × judgment' iff the time multiplier >1.0005; risk 'fitted' with the note's tail in its tooltip; their tooltip figures equal the model's.","render() badge comments (AUDIT_FINDINGS R1-1, R1-3)");
def("time-stretch-note","The time note appears iff the ask stretches the median; its 'N% above model value', band days and multiplier equal the model's, and band days x multiplier gives the tile's days.","render() o_tstretch; T_ELAST comment");
def("scores-and-captions","Score captions name the ask and pool actually used: 'at your ask of money(ask)' (+ buyers when thin); 'at the optimal ask of money(V x rho)' (+ the typical pool when thin).","render() hero scores");
def("business-score-not-below-omni","On the page the business score is never below the Omni score.","businessScore(): 'the business score still never falls below the Omni score'");
def("hero-caption-band-word","The caption's verdict on the business is the business-score band (90 top decile, 62 above most, 38 middle, 10 below most, else bottom decile).","render() band()");
def("hero-caption-ask-direction","The caption says 'close to optimal' iff the ask costs under 2% of proceeds; otherwise its cost %, 'N% above/below' (direction of ask vs optimal ask, N = |ask/opt - 1|) and the optimal ask equal the model, and that optimal ask is the 'If you need to sell' price.","render() o_cap");
def("hero-caption-points-add-up","When the caption prints both the ask's and the pool's points they add up to business score minus Omni score; the pool sentence appears iff the pool costs at least 0.5% of expected proceeds.","render() o_cap split (sA, askPts, poolPts)");
def("kf-strips-mirror-sources","The key-figure strips repeat their sources exactly (value, median, mean, chance of closing, median time, pursue first, sensitivity lead).","v8-console-js: 'copy text the section already shows'");
def("quality-band-panel","The quality panel's percentile, ordinal, '% on the fitted value' and end values equal the model; the multiple table's quality row shows the same percentile.","render() o_qband and multbl");
def("eq-value-substitution","eq_vs prints the model's h, m, e_i, P-hat, calibration and quality factors and boxes money(V) = money(SDE) x M; P-hat x calib x q reproduces V.","render() eq_vs (AUDIT_FINDINGS R1-20, R2-5)");
def("eq-anchoring-substitution","eq_as prints rho, a-bar/V, rho-tilde, A, c_ask, the median, the boxed E[P|close], the ceiling share and P_C x E[P|close] = expected proceeds with the model's numbers.","render() eq_as (AUDIT_FINDINGS R3-8)");
def("eq-closing-substitution","eq_ps prints the model's gap, base rate, u, penalty, thin-pool factor (iff < 0.9995), boxed P_C and P_C^judg, and the printed product equals the boxed P_C within rounding.","render() eq_ps");
def("eq-time-substitution","eq_ts prints band days x multiplier = median days, beta, the quartiles and E[T] = median x ratio with the model's numbers.","render() eq_ts");
def("eq-buyer-substitution","eq_bs names the pursue-first buyer with its EV and the pays-most buyer with its price and premium over model value; the cap line appears iff that buyer's price is capped.","render() eq_bs (AUDIT_FINDINGS R2-1)");
def("eq-competition-substitution","eq_comps and the multiple table's competition row print the model's kappa, offers, buyers, typical offers and premium; 'no effect at the point estimate' iff the ceiling absorbs all but 2%.","render() eq_comps (AUDIT_FINDINGS R5-3, R6-3)");
def("eq-sensitivity-headline","eq_ds names the quality lever with the largest |dV| and prints its dV, dE and dP, the same figures as that lever's two bars.","render() eq_ds");
def("eq-gap-substitution","eq_gs, the value-gap figure and its 'from ... to ...' line show the same two values and their difference.","render() value gap");
def("eq-roi-substitution","eq_rs shows the first costed row of the intervention table, and its ROI equals that row's ROI and (dE - C)/C of the printed figures.","render() eq_rs");
def("eq-optimizer-substitution","eq_os prints the budget, 2^11 combinations and the proceeds card's spend and proceeds; eq_us prints the overall-outcome card's P_C, mean price, value, theta, delay cost, days and spend, and its boxed U equals the model's U.","render() eq_os/eq_us");
def("eq-scenario-substitution","eq_ss's three prices and eq_cs's 80% interval and fitted band equal the scenario cards and the price tile's '80% between' figures; eq_cs's confidence equals the model's.","render() eq_ss/eq_cs (AUDIT_FINDINGS R1-17)");
def("eq-zscore-and-nonlinear","eq_zs's recurring-revenue z and percentile and eq_nls's six terms equal the z bar and the judgment logistic's contribution bars.","render() eq_zs/eq_nls");
def("multbl-equals-model","The multiple table shows the model's anchor, industry factor, stack rows, fitted multiple, quality factor, model value, anchoring, competition, ceiling, median and mean price; its value, median and mean equal the hero figures.","render() multbl");
def("buyer-table-consistent","Buyer rows equal the model, are sorted by expected value with 'pursue first' on the top row and 'pays most' on the highest-paying buyer that looks at this size; Engages x Closes x the price at this ask rebuilds the EV within display rounding; the star tooltips repeat the rows.","render() buytbl (AUDIT_FINDINGS R2-1); drawStars tooltip (R3-7)");
def("intervention-table-equals-model","The intervention table equals interventionTable() in its formats, sorted by net gain.","render() intbl");
def("reprice-row-equals-tiles","The reprice row's dE equals the 'If you need to sell' proceeds minus today's proceeds (display rounding), and the footnote's ratio equals that tile's ratio.","interventionTable() and the decision tiles both reprice to rhoSell");
def("bars-equal-model","The z, contribution and two sensitivity bar charts show the model's values in the page's formats, ordered by |value|.","render() divBars calls; sensitivity()");
def("categories-equal-model","The nine category scores and their mean equal the model.","render() cats");
def("decision-tiles-equal-model","'If you need to sell' / 'If you can walk away' show money(V x rho), rho, P_C and expected proceeds at the two optimal ratios.","render() o_list/o_list2");
def("optimizer-cards-equal-model","Both optimiser cards list optimize()'s programme with its costs, total, budget, expected proceeds, median price, closing chance and expected days.","render() card()");
def("card1-lift-sentence","'Lifts expected proceeds $X over today's $Y, before the $Z spent': Y is the hero's expected proceeds, X is the card's proceeds minus Y, Z is the card's total.","render() first card subtitle (AUDIT.md item 5)");
def("card-costs-add-up-and-fit-budget","Each card's listed costs add up to its total (display rounding), the total is within the budget, and 'of $B' is the budget.","optimize(): c > budget skipped");
def("card2-note-directions","The overall-outcome card's subtitle equals optCardNote(), and its spend / closing-chance / time / price directions agree with the two cards' own figures.","optCardNote() comment (AUDIT_FINDINGS #14/#15/R1-10)");
def("optnote-directions","The note under the two asks equals optNote() and agrees with the tiles: 'below'/'higher'/'same' follows the two prices, the proceeds and points given up match the tiles, the time value equals delay cost x days, and the coin-toss caveat appears iff the gain is under 1% of value.","optNote() comments (AUDIT_FINDINGS #11/#14/#18, R1-11)");
def("optimizer-dominates-each-row","The proceeds card's net (proceeds - spend) is at least today's proceeds and at least the net of every single-change programme in the intervention table that fits the budget.","optimize(): exhaustive search of all 2^11 subsets");
def("do-nothing-claim-true","A card that reads 'Do nothing — no combination clears its cost' appears only when no change, on top of the free reprice, clears its own cost (otherwise the binding reason is the budget).","render() card(): the label's own claim; economics");
def("biz-score-ask-equals-sell-tile","The optimal ask named by the business score (typical pool or deeper) and by the caption equals the 'If you need to sell' price.","render(): both use V x rhoSell");
def("sensflat-consistent","The sensitivity note's branch follows its rule, and its '% under/over model value', ceiling share, pass-through share and quoted 5%-cut effect equal the model and the 'Asking price, 5% lower' bar.","render() sensflat (AUDIT_FINDINGS R1-12, R4-8)");
def("gapnote-consistent","The value-gap note's cost, months, 'from' proceeds and closing chance equal the model and the hero tiles; the trajectory rises iff the gap is positive.","render() o_gapnote; v8-console gapTraj()");
def("scenario-cards","Bear <= Base <= Bull; 'X% chance of no sale' is 1 - P_C; the '(the ask ceiling)' label and the bull card's ceiling share follow their rules.","render() scen (AUDIT_FINDINGS R1-2)");
def("realisation-block","The realisation rows equal the model (market ratio, Vmean/ask, cash share, deferred) and their proceeds equal the hero's.","drawCurve() o_real");
def("time-curve-labels","The curve's 90/180/365-day labels are F(t), its median label is round(t_med) iff t_med < 540, and its caption and aria-label quote the model's P_C and shares.","drawCurve()/v8 curveSVG()");
def("state-option-labels","Every state option's '(+/-x pts charge-off risk, 10 yr)' equals that state's 10-year risk minus the national one for this deal, and the selected state's figure equals the risk tile minus the national risk.","OMNI_STLAB: 'the label is the model's own difference'");
def("sensnote-one-sided","The note under the sensitivity panel names exactly the rows measured one-sided, and the back-step note appears iff 1.25 x buyers > 600.","render() sensnote");
def("star-map-labels","Each star's label reads money(V_j) · pc(engagement) engage beside the buyer's name, and the model-value line is labelled money(V).","v8-charts starSVG(): 'Same encodings'");
def("extrapolation-notice","The extrapolation notice lists exactly the inputs past the fitted data's 1st/99th percentiles, with the model's own sentences, and says 'a long way out' iff one is 5x or more past its edge.","model() support check; render() o_xwarn");
def("phone-width-figures","At 390px width (narrow layouts that re-flow every equation) the hero, the equations' substituted figures and the tables still carry the model's figures.","v8-console-js: 'the same terms, the same figures'");
def("motion-on-figures","With motion on (focal planet easing, warp hops on tab switch and reset) every per-state check still holds and a tab round trip changes nothing.","v3/v4/v5 decoration comments: 'Decoration only - nothing here computes a model figure'");
def("slider-sweep-directions","Swept with the keyboard, the displayed figures move the way the model says: as the ask slider moves right the chance of closing never rises, the median days and the price if it closes never fall; as the share kept rises the walk-away price never falls and the proceeds-maximising price does not move; as more buyers are contacted the chance of closing, expected proceeds and both scores never fall; as earnings rise at fixed revenue the model value never falls.","fuzz.test.js properties carried to the displayed figures; bestRatio comment ('reads neither theta nor the cost of delay'); monotone comparative statics of U in theta");
def("dom-no-nan-undefined-infinity","No NaN, undefined or Infinity in any text, tooltip or aria-label of the console or the Data tab.","tests/browser.sweep.js (extended to attributes and the Data tab)");
def("dom-no-signed-zero","No signed zero on a figure that is not a change: card figures, scenario ranges, realisation rows and buyer cells never read '−$0'. Changes (the intervention table, sensitivity bars, panel deltas) keep their sign when they round to zero, a convention the stress test kept.","stress test: signed zeros refuted as immaterial for changes; economics for levels");
def("dom-no-negative-money-where-nonnegative","Prices, values, proceeds, costs, budgets, synergies and buyer EVs are never shown negative.","economics");
def("dom-no-empty-figures","No output figure is empty or the '—' placeholder after a render.","render(): every tile is written on each render");
def("tab-roundtrip-stable","Console -> Data -> Console changes no console text, equation, tooltip or aria-label.","tab handler re-renders nothing; economics");
def("reset-restores-defaults","Reset restores STATE.s to the framework example exactly and the console's full text to what the page showed on load.","reset(): 'Reset to the framework example'");
def("no-page-errors","No page errors and no console errors (WebGL driver warnings excluded).","tests/browser.inputs.js");
def("data-tab-state-independent","The Data tab's text is the same in every state (it is built once, from the model and the framework example).","renderData() is called once; its live figures are computed at the framework example");
def("data-tab-live-figures","The Data tab's live self-audit rows, the time-stretch sentence (277/.../...) and the quality-sweep sentence equal a fresh node recomputation.","renderCalib(); renderData() Model III and quality-sweep blocks (AUDIT_FINDINGS R5-4, R6-1)");
def("yrs-moves-only-judgment-panels","Changing years of clean history moves only the category bars and the unused judgment panels; every other figure stays, the confidence figure, its label and its band included (it no longer reads years since October 2026).","Data tab: 'Years of clean history feeds only the category bars and the judgment panels that are not used.'");
def("pc-quality-free-at-same-ratio","At the same ask relative to model value, changing a quality input leaves the chance of closing, its base rate and its gap penalty unchanged.","Console #srcs: 'At the same ask relative to its model value, the closing probability does not depend on quality'");
def("quality-keeps-size-band","Changing a quality input leaves the fitted multiple, the fitted band median days, the base close rate and the cash share unchanged (with the ask below value, the median days too).","Data tab: 'They do not move the size band: the base close rate, the time to close and the cash share are read at the fitted value before quality positioning'; R6-1 'the fitted F, which the sliders do not touch'");
/* node fine scans of render()'s display rules (Part A) */
def("scan-reprice-row-no-signed-zero","Fine scan: with the ask typed in whole dollars near the proceeds optimum, the reprice row's dE reads '−$0' only when it is negative (a change keeps its sign when it rounds to zero, a convention the stress test kept).","render() intbl formatting + task hygiene list");
def("scan-net-days-no-signed-zero","Fine scan over the ask: an intervention row's 'Net days' reads '−0' only when the change saves time.","render() intbl formatting");
def("scan-roi-no-signed-zero","Fine scan over revenue and buyers: an intervention row's ROI reads '−0%' only when the change loses money (red), against '0%' when it gains (green).","render() intbl formatting");
def("scan-bear-card-matches-legend","Fine scan over typed asks and earnings ($10k steps): the Bear card prints the 8th percentile the hero legend shows, or, when its 8th-22nd range is under 0.5% wide (the documented collapse to 'the ask ceiling'), a figure within 0.5% of it.","render() scenario cards (b23deb3: collapse rule); stress test: kept as documented");
def("scan-do-nothing-claim","Fine scan over budget x ask: an empty programme says 'no combination clears its cost' only when the budget covers every change and none does; when changes that clear their cost are over the budget, it names one (stress test S-5).","render() card(); economics");

/* ================================================================== Part A: node fine scans */
const DEF={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,buyers:65,budget:1e5,lamT:900,theta:.75,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,st:null,franchise:false};
let seed=20261013; const rnd=()=>{ seed=(seed*16807)%2147483647; return (seed-1)/2147483646; };
const pick=a=>a[Math.floor(rnd()*a.length)];
const INDS=Object.keys(A.IND);
const ADV={};   /* adversarial states found by the scans, entered in the browser in Part B */
function withRatios(s){ const t={...s}; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,t.theta,t.lamT); return t; }
function partA(){
  const t0=Date.now();
  /* A1: ask typed in whole dollars across +/- $3,000 of V x rhoSell, on several businesses */
  const bizA=[DEF,{...DEF,ind:"prof",rev:1.2e6,ern:1.8e5},{...DEF,ind:"mfg",rev:2.5e7,ern:4e6,buyers:30},{...DEF,ind:"saas",rev:3e6,ern:9e5,buyers:120}];
  for(const b of bizA){ const V=A.model({...b,ask:1}).V, rs=A.bestRatio(b,0,0), a0=Math.round(V*rs);
    for(let dx=-3000;dx<=3000;dx+=100){ const s=withRatios({...b,ask:a0+dx}), r=A.model(s), rep=A.interventionTable(s,r).find(o=>o.k==="reprice"), txt=intRow(rep,r.V).dE;
      ok("scan-reprice-row-no-signed-zero",!/^[−-]\$0$/.test(txt)||rep.dE<0,()=>J({ind:s.ind,rev:s.rev,ern:s.ern,buyers:s.buyers,ask:s.ask,optAsk:V*rs,dE:rep.dE,shown:txt}));
      if(/^[−-]\$0$/.test(txt)&&!ADV.repriceZero) ADV.repriceZero={base:b,ask:s.ask,dE:rep.dE}; } }
  /* A2: net days, over the ask ratio 1.00-3.00 in 0.002 steps */
  for(const b of [DEF,{...DEF,ind:"rest",rev:8e5,ern:1.6e5,buyers:20}]){ const V=A.model({...b,ask:1}).V;
    for(let m=1.0;m<=3.0+1e-9;m+=(b===DEF?.003:.008)){ const s=withRatios({...b,ask:Math.round(V*m)}), r=A.model(s), it=A.interventionTable(s,r);
      for(const o of it){ const txt=intRow(o,r.V).net; ok("scan-net-days-no-signed-zero",txt!=="−0"||o.dTnet<0,()=>J({ind:s.ind,ask:s.ask,ratio:m,row:o.k,dTnet:o.dTnet,shown:txt}));
        if(txt==="−0"&&!ADV.netZero) ADV.netZero={base:b,ask:s.ask,row:o.k,dTnet:o.dTnet}; } } }
  /* A3: ROI over revenue (cost scales with revenue) at fixed margin, and over buyers */
  for(let k=0;k<=300;k++){ const rev=4e6*Math.pow(2,k/150), s=withRatios({...DEF,rev,ern:rev*.2417}), r=A.model(s), it=A.interventionTable(s,r);
    for(const o of it){ const txt=intRow(o,r.V).roi; ok("scan-roi-no-signed-zero",txt!=="−0%"||o.roi<0,()=>J({rev,ern:s.ern,row:o.k,roi:o.roi,shown:txt}));
      if(txt==="−0%"&&!ADV.roiZero) ADV.roiZero={base:{...DEF,rev,ern:rev*.2417},row:o.k,roi:o.roi}; } }
  for(let b=5;b<=600;b+=2){ const s=withRatios({...DEF,buyers:b}), r=A.model(s), o=A.interventionTable(s,r).find(x=>x.k==="outreach"), txt=intRow(o,r.V).roi;
    ok("scan-roi-no-signed-zero",txt!=="−0%"||o.roi<0,()=>J({buyers:b,roi:o.roi,shown:txt}));
    if(txt==="−0%"&&!ADV.roiZero) ADV.roiZero={base:{...DEF,buyers:b},row:"outreach",roi:o.roi}; }
  /* A4: the do-nothing label, over budget x ask */
  for(const bud of [0,5e3,1.7e4,4e4,1e5]) for(const m of [.6,.9,1.0,1.05,1.1007,1.2,1.5]){ const V=A.model({...DEF,ask:1}).V;
    const s=withRatios({...DEF,budget:bud,ask:Math.round(V*(m===1.1007?A.bestRatio(DEF,0,0):m))}), r=A.model(s), best=A.optimize(s,r,s.budget,s.lamT,s.theta);
    if(best.V.keys.length) { ok("scan-do-nothing-claim",true); continue; }
    const rRep=A.model(A.applyAll(s,r,["reprice"])), it=A.interventionTable(s,r);
    const clears=it.filter(o=>o.k!=="reprice"&&rRep.EVp+o.dE-o.c>r.EVp+1);
    ok("scan-do-nothing-claim",best.allIn?!clears.length:(!clears.length||!!best.V.blocked),()=>J({budget:bud,ask:s.ask,askOverV:s.ask/r.V,clears:clears.map(o=>o.k+" net "+Math.round(rRep.EVp+o.dE-o.c-r.EVp)+" cost "+Math.round(o.c))}));
    if(clears.length&&!ADV.doNothing) ADV.doNothing={base:{...DEF,budget:bud},ask:s.ask}; }
  /* A5: the Bear card's collapse rule against the hero legend, over typed asks and earnings in $10k steps */
  const card=(r,a,b)=>Math.abs(b-a)<.005*Math.abs(b)?money(b):money(a);
  for(let ask=1.5e6;ask<=4.5e6;ask+=1e4){ const r=A.model({...DEF,ask}); ok("scan-bear-card-matches-legend",card(r,r.scen.bear[0],r.scen.bear[1])===money(r.scen.bear[0])||Math.abs(r.scen.bear[1]-r.scen.bear[0])<.005*Math.abs(r.scen.bear[1]),()=>J({ask,legend:money(r.scen.bear[0]),card:money(r.scen.bear[1]),q08:r.scen.bear[0],q22:r.scen.bear[1]})); }
  for(let ern=8e5;ern<=4e6;ern+=1e4){ const r=A.model({...DEF,ern}); ok("scan-bear-card-matches-legend",card(r,r.scen.bear[0],r.scen.bear[1])===money(r.scen.bear[0])||Math.abs(r.scen.bear[1]-r.scen.bear[0])<.005*Math.abs(r.scen.bear[1]),()=>J({ern,legend:money(r.scen.bear[0]),card:money(r.scen.bear[1])})); }
  return Date.now()-t0;
}

/* ================================================================== Part B: the live page */
let pw=null; try{ pw=require("playwright"); }catch(e){ try{ pw=require("/opt/node-tools/node_modules/playwright"); }catch(e2){} }
const OUTPUT_IDS=["o_score","o_score_biz","o_score_biz_n","o_score_n","o_cap","o_val","o_pc","o_ev","o_msv","o_mult","o_risk","o_t","o_tstretch",
  "o_bb","focal_legend","vx_ask","o_list","o_listp","o_list2","o_listp2","o_listnote","o_gap","o_gapu","o_gapnote","intnote","sensflat","sensnote",
  "scen_t","o_conf","o_qband","o_xwarn"];
/* page-side snapshot: everything the checks read, in one evaluate */
function pageSnap(){
  const $=id=>document.getElementById(id), T=e=>e?e.textContent:null;
  const clean=el=>{ if(!el) return null; const c=el.cloneNode(true); c.querySelectorAll(".cl,svg").forEach(x=>x.remove()); return c.textContent.replace(/\s+/g," ").trim(); };
  const out={txt:{},html:{},eq:{},titles:{}};
  for(const i of window.__OUT_IDS) out.txt[i]=T($(i));
  for(const i of ["o_val","o_ev","o_mult","o_t","o_risk"]) out.html[i]=$(i).innerHTML;
  out.kfig={}; for(const i of ["o_val","o_ev"]){ const k=$(i).querySelector(".kfig"), s=$(i).querySelector(".sub2"); out.kfig[i]=[k?k.textContent:null,s?s.textContent:null]; }
  out.multSub=[...$("o_mult").querySelectorAll(".sub2")].map(e=>e.textContent);
  out.riskSub=[...$("o_risk").querySelectorAll(".sub2")].map(e=>e.textContent);
  document.querySelectorAll("#view-console .eq [id^='eq_']").forEach(e=>{ const a=e.querySelector("annotation"); out.eq[e.id]=a?a.textContent:null; });
  for(const i of ["o_pc_pv","o_msv_pv","o_mult_pv","o_t_pv","o_risk_pv","o_risk"]){ const e=$(i); out.titles[i]=e?[e.textContent,e.title,e.className]:null; }
  const rows=id=>[...$(id).querySelectorAll("tr")].map(tr=>[...tr.cells].map(clean));
  out.multbl=rows("multbl"); out.intbl=rows("intbl");
  out.buytbl=[...$("buytbl").querySelectorAll("tr")].slice(1).map(tr=>({tags:[...tr.cells[0].querySelectorAll(".tag")].map(t=>t.textContent),
    name:(()=>{ const c=tr.cells[0].cloneNode(true); c.querySelectorAll(".tags,.tag,.muted,.cl").forEach(x=>x.remove()); return c.textContent.trim(); })(),
    cells:[...tr.cells].slice(1).map(c=>{ const k=c.cloneNode(true); k.querySelectorAll(".cl").forEach(x=>x.remove()); const m=k.querySelector(".muted"); const sub=m?m.textContent:null; if(m) m.remove(); return [k.textContent.trim(),sub]; })}));
  out.cards=[...document.querySelectorAll("#optout .opt")].map(c=>({title:T(c.querySelector(".grp-title")),
    rows:[...c.querySelectorAll("table tr")].map(tr=>[...tr.cells].map(clean)),
    bigs:[...c.querySelectorAll(".big")].map(b=>[T(b.querySelector(".k")),T(b.querySelector(".n"))]), note:T(c.querySelector("p.note"))}));
  const bars=id=>[...$(id).querySelectorAll(".bar-row")].map(r=>[T(r.querySelector(".bar-n")||r.firstElementChild).trim(),T(r.querySelector(".bar-val")).trim()]);
  out.bars={zbars:bars("zbars"),pcbars:bars("pcbars"),sensV:bars("sensV"),sensP:bars("sensP")};
  out.cats=[...$("cats").querySelectorAll(".cat-row")].map(r=>[r.children[0].textContent.trim(),T(r.querySelector(".cat-n")).trim()]);
  out.focal=(window.__ft&&window.__ft.focal||[]).filter(x=>/%$/.test(x)).slice(-1)[0]||null;
  out.focalTarget=window.FOCAL_TARGET?window.FOCAL_TARGET.pc:null;
  out.tcurve={texts:[...$("tcurve").querySelectorAll("text")].map(t=>t.textContent),cap:T($("tcurve_cap")),aria:$("tcurve").getAttribute("aria-label")};
  out.stars=[...$("starmap").querySelectorAll("g.bstar title")].map(t=>t.textContent);
  out.starLabels=[...$("starmap").querySelectorAll("text.sm-n,text.sm-s")].map(t=>t.textContent);
  out.starMV=[...$("starmap").querySelectorAll(".sm-mv")].map(t=>t.textContent).join(" ");
  out.xwarn={text:$("o_xwarn").textContent,items:[...$("o_xwarn").querySelectorAll("li")].map(l=>l.textContent),far:/a long way out/.test($("o_xwarn").textContent)};
  const p1=$("gap_traj").querySelector("circle.p1"), p0=$("gap_traj").querySelector("circle.p0");
  out.traj={p1:p1?+p1.getAttribute("cy"):null,p0:p0?+p0.getAttribute("cy"):null,texts:[...$("gap_traj").querySelectorAll("text")].map(t=>t.textContent)};
  out.scen=[...$("scen").children].filter(c=>c.tagName==="DIV").map(c=>({lab:T(c.querySelector(".lab")),rng:T(c.querySelector(".rng")),pct:T(c.querySelector(".pct"))}));
  out.kf={}; document.querySelectorAll(".kf[data-k]").forEach(k=>{ out.kf[k.dataset.k]=[k.textContent,k.hidden]; });
  out.real=[...$("o_real").querySelectorAll(".rzrow")].map(r=>[T(r.querySelector(".rzk")),T(r.querySelector(".rzv")),T(r.querySelector(".rzn"))]);
  out.stOpts=[...$("i_st").options].map(o=>[o.value,o.textContent]); out.stSel=$("i_st").value;
  out.boxes={}; out.bad={}; document.querySelectorAll("input.v").forEach(b=>{ out.boxes[b.id]=b.value; out.bad[b.id]=b.classList.contains("bad"); });
  out.consoleText=$("view-console").textContent;
  out.attrs=[...document.querySelectorAll("#view-console [title],#view-console [aria-label]")].map(e=>(e.getAttribute("title")||"")+" | "+(e.getAttribute("aria-label")||""));
  out.attrs=out.attrs.concat([...$("i_st").options].map(o=>o.textContent));
  const dv=$("view-data").textContent; let h=0; for(let i=0;i<dv.length;i++) h=(h*31+dv.charCodeAt(i))|0; out.dataHash=dv.length+":"+h;
  out.s=JSON.parse(JSON.stringify(STATE.s)); out.r={V:STATE.r.V,PC:STATE.r.PC,EVp:STATE.r.EVp,tMed:STATE.r.tMed};
  out.pending=EQ.pending.size; out.sky=window.OMNI_SKY_PAUSE;
  return out;
}

/* ---------------------------------------------------------------- designed states
   typed: exact-value text (Enter); sel: select values; fr: franchise; keys: [slider id, key]; ask: a ratio of the page's
   model value (number), 'sell' (V x rhoSell), or a string typed as is */
const STATES=[
  {name:"defaults"},
  {name:"tiny-restaurant",sel:{i_ind:"rest"},typed:{rev:"10000",ern:"2000",buy:"5",bud:"none",lam:"none",th:"0"},ask:.5},
  {name:"huge-saas-CA-franchise",sel:{i_ind:"saas",i_st:"CA"},fr:true,typed:{rev:"5B",ern:"1B",buy:"600",bud:"1B",lam:"4000",th:"100"},ask:1.0},
  {name:"ask-0.05V",ask:.05},
  {name:"ask-at-V",ask:1.0},
  {name:"ask-1.01V",ask:1.01},
  {name:"ask-at-sell-optimum",ask:"sell"},
  {name:"ask-at-optimum-budget0",typed:{bud:"0"},ask:"sell"},
  {name:"ask-1.5V",ask:1.5},
  {name:"ask-2V",ask:2},
  {name:"ask-10V",ask:10},
  {name:"ask-100V",ask:100},
  {name:"ask-hard-max",ask:"100B"},
  {name:"thin-pool-5",typed:{buy:"5"},ask:1.05},
  {name:"deep-pool-600",typed:{buy:"600"},ask:1.2},
  {name:"forced-seller",typed:{lam:"$4,000/day",th:"0%"},ask:1.3},
  {name:"patient-seller",typed:{lam:"none",th:"100"},ask:1.15},
  {name:"knife-edge-theta",typed:{th:"78.5"}},
  {name:"worst-quality",sel:{i_own:"0.95",i_mgt:"0.08",i_fin:"0.14"},typed:{rec:"0",cc:"70",ret:"5",plt:"95",grw:"-25",gm:"12",yrs:"1"},ask:1.1},
  {name:"best-quality",sel:{i_own:"0.14",i_mgt:"0.92",i_fin:"0.96"},typed:{rec:"100",cc:"1",ret:"99",plt:"5",grw:"70",gm:"97",yrs:"12"},ask:.9},
  {name:"earnings-above-92pct",typed:{rev:"1M",ern:"5M"},ask:1.0},
  {name:"half-percent-margin",typed:{rev:"200M",ern:"1M"},ask:1.1},
  {name:"sde-above-3M-cap",sel:{i_ind:"mfg"},typed:{rev:"60M",ern:"20M",bud:"2.5M"},ask:1.25},
  {name:"near-500k-band",sel:{i_ind:"prof"},typed:{rev:"1.2M",ern:"180k"},ask:1.0},
  {name:"ecom-TX-franchise",sel:{i_ind:"ecom",i_st:"TX"},fr:true,ask:1.15},
  {name:"risk-capped-dist",sel:{i_ind:"dist"},typed:{rev:"40M",ern:"4M"},ask:1.1},
  {name:"typed-out-of-range",typed:{grw:"200%",cc:"0%",ret:"120",buy:"1000",yrs:"40",th:"150",lam:"9000"},ask:1.2},
  {name:"keyboard-sliders",keys:[["i_grw","End"],["i_rec","Home"],["i_buy","End"],["i_th","Home"],["i_lam","End"],["i_gm","Home"]],ask:1.1},
  {name:"wash-PR-small",sel:{i_ind:"wash",i_st:"PR"},typed:{rev:"900k",ern:"300k",buy:"20"},ask:.8},
  {name:"fitness-thin-patient",sel:{i_ind:"fit"},typed:{buy:"10",th:"90"},ask:1.4},
  {name:"auto-budget0",sel:{i_ind:"auto"},typed:{bud:"none"},ask:1.3},
  {name:"construction-small",sel:{i_ind:"constr"},typed:{rev:"3M",ern:"450k",buy:"30"},ask:1.05},
  {name:"home-no-delay-forced",sel:{i_ind:"home"},typed:{lam:"none",th:"0"},ask:1.1},
  {name:"staffing-1yr",sel:{i_ind:"staff"},typed:{yrs:"1"},ask:.95},
  {name:"landscaping-1.2",sel:{i_ind:"land"},ask:1.2},
  {name:"vet-big-thin",sel:{i_ind:"vet",i_st:"NY"},typed:{rev:"15M",ern:"3.2M",buy:"15",bud:"500k"},ask:1.15},
  {name:"msp-tiny-ask",sel:{i_ind:"msp"},typed:{rev:"2M",ern:"500k"},ask:"1000"},
  {name:"buyers-slider-400",keys:[["i_buy","End"]].concat(Array(40).fill(["i_buy","ArrowLeft"]))},
  {name:"ask-typed-6.65M",ask:"6.65M"},
  {name:"revenue-5.8M",typed:{rev:"5.8M"}},
  {name:"channel-40.1",typed:{plt:"40.1"}},
  {name:"channel-39.9",typed:{plt:"39.9"}},
  {name:"ask-typed-2.15M",ask:"2.15M"},
  {name:"earnings-typed-2.40M",typed:{ern:"2.40M"}},
  {name:"quality-near-median",sel:{i_own:"0.95",i_mgt:"0.08",i_fin:"0.45"},typed:{grw:"19.4"}}
];
function randomStates(n){
  const out=[], STS=["","CA","TX","FL","NY","OH","WA","GA","PR","DC"];
  for(let i=0;i<n;i++){
    const rev=Math.exp(Math.log(2e5)+rnd()*(Math.log(2e8)-Math.log(2e5))), ern=rev*(.03+rnd()*.5);
    out.push({name:"random-"+i,sel:{i_ind:pick(INDS),i_st:pick(STS),i_own:pick(["0.95","0.72","0.42","0.14"]),i_mgt:pick(["0.08","0.36","0.66","0.92"]),i_fin:pick(["0.14","0.45","0.74","0.96"])},
      fr:rnd()<.25,typed:{rev:String(Math.round(rev)),ern:String(Math.round(ern)),grw:String(Math.round(-25+rnd()*95)),gm:String(Math.round(12+rnd()*80)),
        rec:String(Math.round(rnd()*100)),cc:String(Math.round(1+rnd()*69)),ret:String(Math.round(5+rnd()*94)),plt:String(Math.round(5+rnd()*90)),
        yrs:String(1+Math.floor(rnd()*12)),buy:String(5+Math.floor(rnd()*596)),bud:rnd()<.15?"none":String(Math.round(rev*.15*rnd())),
        lam:String(Math.floor(rnd()*81)*50),th:String(Math.round(rnd()*100))},ask:+(Math.exp(Math.log(.3)+rnd()*Math.log(10))).toFixed(4)});
  }
  return out;
}
const BOXES={rev:{money:1,hard:[1e4,5e9]},ern:{money:1,hard:[1e3,1e10]},ask:{money:1,hard:[1e3,1e11]},bud:{money:1,hard:[0,1e9]},
  grw:{sl:[-25,70],f:"grw",div:100},gm:{sl:[12,97],f:"gm",div:100},rec:{sl:[0,100],f:"rec",div:100},cc:{sl:[1,70],f:"cc",div:100},ret:{sl:[5,99],f:"ret",div:100},
  plt:{sl:[5,95],f:"plt",div:100},yrs:{sl:[1,12],f:"yrs",div:1},buy:{sl:[5,600],f:"buyers",div:1},lam:{sl:[0,4000],f:"lamT",div:1},th:{sl:[0,100],f:"theta",div:100}};
const KEYSL={i_grw:["grw",-25,70,100],i_gm:["gm",12,97,100],i_rec:["rec",0,100,100],i_cc:["cc",1,70,100],i_ret:["ret",5,99,100],i_plt:["plt",5,95,100],
  i_yrs:["yrs",1,12,1],i_buy:["buyers",5,600,1],i_lam:["lamT",0,4000,1],i_th:["theta",0,100,100]};
const DEF_UI={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,budget:1e5,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,lamT:900,theta:.75};
/* what the page should hold after the entry, by its own rules */
function intended(st,askTyped){
  const s={...DEF_UI}, IN={rev:6e6,ern:1.45e6,ask:3.24e6,bud:1e5}, bad={};
  if(st.sel){ if(st.sel.i_ind) s.ind=st.sel.i_ind; if(st.sel.i_st!==undefined) s.st=st.sel.i_st||null;
    for(const k of ["own","mgt","fin"]) if(st.sel["i_"+k]) s[k]=parseFloat(st.sel["i_"+k]); }
  if(st.fr) s.franchise=true;
  const typed={...(st.typed||{})}; if(askTyped!==undefined) typed.ask=askTyped;
  for(const k of ["rev","ern","bud","grw","gm","rec","cc","ret","plt","yrs","buy","lam","th","ask"]){ if(typed[k]===undefined) continue; const B=BOXES[k], txt=typed[k], v=parseAmount(txt);
    if(B.money){ if(!isFinite(v)||/%|ofvalue/.test(txt.toLowerCase().replace(/\s/g,""))||v<0){ bad["v_"+k]=true; continue; }
      IN[k]=clamp(v,B.hard[0],B.hard[1]); if(k==="ern"&&IN.ern>IN.rev*.92) IN.ern=IN.rev*.92; bad["v_"+k]=IN[k]!==v; }
    else { if(!isFinite(v)){ bad["v_"+k]=true; continue; } const x=clamp(v,B.sl[0],B.sl[1]); s[B.f]=x/B.div; bad["v_"+k]=x!==v; } }
  const cur={}; for(const [id,key] of (st.keys||[])){ const K=KEYSL[id], step=id==="i_buy"?5:id==="i_lam"?50:1;
    let v=cur[id]!==undefined?cur[id]:Math.round(DEF_UI[K[0]]*K[3]*1e6)/1e6;
    v=key==="End"?K[2]:key==="Home"?K[1]:key==="ArrowLeft"?Math.max(K[1],v-step):key==="ArrowRight"?Math.min(K[2],v+step):v;
    cur[id]=v; s[K[0]]=v/K[3]; }
  s.rev=IN.rev; s.ern=Math.min(IN.ern,IN.rev*.92); s.ask=IN.ask; s.budget=IN.bud;
  return {s,bad};
}
const settle=async(p,full)=>{
  await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  await p.waitForFunction(()=>typeof _rq!=="undefined"&&_rq===0,null,{timeout:60000});
  if(full){
    try{ await p.waitForFunction(()=>EQ.pending.size===0,null,{timeout:6000}); }
    catch(e){ await p.evaluate(()=>{ for(const id of [...EQ.pending.keys()]) eqSet(id); }); }
    await p.evaluate(()=>{ window.scrollTo(0,0); });
    await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(r,60)))));
  }
};
async function typeBox(p,id,txt){ await p.fill("#"+id,String(txt)); await p.press("#"+id,"Enter"); }
async function enter(p,st){
  await p.click("#reset"); await settle(p);
  if(st.sel){ for(const id of ["i_ind","i_st","i_own","i_mgt","i_fin"]) if(st.sel[id]!==undefined) await p.selectOption("#"+id,st.sel[id]); }
  if(st.fr) await p.check("#i_fr");
  const ty=st.typed||{};
  for(const k of ["rev","ern","bud","grw","gm","rec","cc","ret","plt","yrs","buy","lam","th"]) if(ty[k]!==undefined) await typeBox(p,"v_"+k,ty[k]);
  for(const [id,key] of (st.keys||[])){ await p.focus("#"+id); await p.keyboard.press(key); }
  await settle(p);
  let askTyped;
  if(st.ask!==undefined){
    const pg=await p.evaluate(()=>({V:STATE.r.V,rs:STATE.s.rhoSell}));
    askTyped=typeof st.ask==="string"?(st.ask==="sell"?String(Math.round(pg.V*pg.rs)):st.ask):String(Math.round(pg.V*st.ask));
    await typeBox(p,"v_ask",askTyped);
  }
  await p.evaluate(()=>{ if(document.activeElement&&document.activeElement.blur) document.activeElement.blur(); });
  await settle(p,true);
  return askTyped;
}

/* ---------------------------------------------------------------- per-state checks */
function checkState(name,st,askTyped,S,E){
  const r=E.r, s=E.s, ctx=(o)=>()=>J({state:name,...o});
  const tx=S.txt, eq={}; for(const k in S.eq) eq[k]=texNorm(S.eq[k]);
  /* ---- input path */
  if(st){ const I=intended(st,askTyped);
    const diffs=[]; for(const k of Object.keys(DEF_UI)){ const a=I.s[k], b=S.s[k];
      if(typeof a==="number"?!(Math.abs(a-b)<=1e-12*Math.max(1,Math.abs(a))):a!==b) diffs.push(k+": intended "+a+" page "+b); }
    ok("ui-typed-values-reach-state",!diffs.length,ctx({diffs}));
    const bd=[]; for(const id in S.bad){ const want=!!I.bad[id]; if(S.bad[id]!==want) bd.push(id+" bad="+S.bad[id]+" want "+want); }
    ok("ui-clamped-entry-marked",!bd.length,ctx({bd}));
  }
  { const want={v_rev:A.moneyIn(s.rev),v_ern:A.moneyIn(s.ern),v_ask:A.moneyIn(s.ask),v_grw:p1(s.grw),v_gm:p1(s.gm),v_rec:p1(s.rec),v_cc:p1(s.cc),v_ret:p1(s.ret),v_plt:p1(s.plt),
      v_yrs:s.yrs+(s.yrs===1?" year":" years"),v_buy:String(s.buyers),v_bud:s.budget?A.moneyIn(s.budget):"none",v_lam:s.lamT?"$"+s.lamT.toLocaleString("en-US")+"/day":"none",v_th:p1(s.theta)};
    const d=Object.keys(want).filter(k=>S.boxes[k]!==want[k]).map(k=>k+": "+S.boxes[k]+" want "+want[k]);
    ok("ui-boxes-echo-state",!d.length,ctx({d})); }
  ok("ui-ask-ratio-caption",tx.vx_ask===r.priceRatio.toFixed(2)+"× model value of "+money(r.V),ctx({shown:tx.vx_ask}));
  /* ---- determinism */
  ok("page-equals-fresh-model",S.r.V===r.V&&S.r.PC===r.PC&&S.r.EVp===r.EVp&&S.r.tMed===r.tMed&&S.s.rhoSell===E.rhoSell&&S.s.optRho===E.optRho,
     ctx({page:{...S.r,rhoSell:S.s.rhoSell,optRho:S.s.optRho},node:{V:r.V,PC:r.PC,EVp:r.EVp,tMed:r.tMed,rhoSell:E.rhoSell,optRho:E.optRho}}));
  ok("scores-history-independent",+tx.o_score===r.score&&+tx.o_score_biz===E.bs.score,ctx({page:[tx.o_score,tx.o_score_biz],node:[r.score,E.bs.score]}));
  /* ---- hero */
  { const bb=r.best.n.replace("Private equity","PE").replace("Individual owner-operator","Owner-operator").replace(" / ","\u00a0/ ");
    const evOk=S.kfig.o_ev[0]===money(r.EVp)&&(r.cashShare<1?S.kfig.o_ev[1]===money(r.EVcash)+" cash at close":S.kfig.o_ev[1]===null);
    const mult=xx(r.M)+" SDE"+(r.fv.wedge?xx(r.M*r.fv.wedge)+" EBITDA":"");
    const bad=[]; if(tx.o_msv!==money(r.V)) bad.push("o_msv "+tx.o_msv); if(tx.o_pc!==pc(r.PC)) bad.push("o_pc "+tx.o_pc); if(!evOk) bad.push("o_ev "+tx.o_ev);
    if(S.kfig.o_val[0]!==money(r.Vmean)) bad.push("o_val "+S.kfig.o_val[0]); if(tx.o_mult!==mult) bad.push("o_mult "+tx.o_mult+" want "+mult);
    if(tx.o_t!==Math.round(r.tMed)+" days") bad.push("o_t "+tx.o_t); if(tx.o_bb!==bb) bad.push("o_bb "+tx.o_bb);
    ok("hero-tiles-equal-model",!bad.length,ctx({bad})); }
  ok("focal-planet-equals-tile",S.focal===tx.o_pc&&S.focal===Math.round(clamp(r.PC,0,1)*100)+"%"&&S.focalTarget===clamp(r.PC,0,1),ctx({focal:S.focal,tile:tx.o_pc,target:S.focalTarget,PC:r.PC}));
  { const L=tx.focal_legend, want="Bear sale"+money(r.scen.bear[0])+"Median sale"+money(r.q(.5))+"Bull sale"+money(r.scen.bull[1]);
    const ss=eq.eq_ss||"", m=/P_\{0\.08\}=(\S+?), *P_\{0\.50\}=(\S+?), *P_\{0\.94\}=(\S+)/.exec(ss.replace(/\s/g," "));
    const sc=S.scen, bearLo=sc[0]?pmAll(sc[0].rng)[0]:NaN, bullHi=sc[2]?pmAll(sc[2].rng).slice(-1)[0]:NaN;
    ok("focal-legend-equals-scenarios",L===want&&m&&pm(m[1])===pm(money(r.scen.bear[0]))&&pm(m[2])===pm(money(r.q(.5)))&&pm(m[3].replace(/\}$/,""))===pm(money(r.scen.bull[1]))
      &&(bearLo===pm(money(r.scen.bear[0]))||(Math.abs(r.scen.bear[1]-r.scen.bear[0])<.005*Math.abs(r.scen.bear[1])&&bearLo===pm(money(r.scen.bear[1]))))&&bullHi===pm(money(r.scen.bull[1])),ctx({legend:L,want,eq_ss:ss.slice(-90),scen:sc.map(x=>x.rng)})); }
  { const lo=r.q(.10), hi=r.q(.90), sub=S.kfig.o_val[1]||"";
    const want=(hi-lo<.005*hi?"nearly every closing at the ask ceiling":"80% between "+money(lo)+" and "+money(hi)+(r.capShare>=.3?" · "+pc(r.capShare)+" at the ask ceiling"+(r.ceil<.99*s.ask?" of "+money(r.ceil):""):""));
    ok("price-tile-subline-rules",sub===want,ctx({sub,want})); }
  { const k=r.risk, R=A.MODELS.risk, capped=R.loan_share*r.V>R.loan_range[1], t=tx.o_risk, sub=S.riskSub;
    let good=t.startsWith(pc(k.p,1))&&(capped?!/average acquisition loan\)/.test(t.split("charged off")[0]):t.includes("("+k.rel.toFixed(2)+"× the average acquisition loan)"))
      &&sub[0]==="charged off within 10 years if 2023–26 conditions hold; "+pc(k.p5,1)+" within 5 years"&&(capped===/SBA 7\(a\) notes cap at \$5M/.test(t));
    if(!capped){ const ti=S.titles.o_risk[1]||"", bm=/average acquisition loan, ([\d.]+)% over the same horizon/.exec(ti);
      const pD=+pc(k.p,1).replace("%",""), rD=+k.rel.toFixed(2), bD=bm?+bm[1]:NaN;
      good=good&&isFinite(bD)&&Math.abs(pD/rD-bD)<=.05/rD+.005*pD/(rD*rD)+.05+1e-9; }
    ok("risk-tile-consistent",good,ctx({tile:t.slice(0,160),capped,p:k.p,rel:k.rel})); }
  { const thin=r.thinF<.9995, gap=r.fc.pen>0, j=thin||gap, bad=[];
    const [pcT,pcTitle]=S.titles.o_pc_pv;
    if(pcT!==(j?"aggregate × judgment":"aggregate")) bad.push("pc badge "+pcT);
    if(gap&&!pcTitle.includes(`× (1 − ${r.fc.pen.toFixed(3)}) for a ${r.fc.gap.toFixed(0)}% price gap`)) bad.push("pc title gap");
    if(thin&&!pcTitle.includes(`× ${r.thinF.toFixed(3)} for a thin pool: ${s.buyers} buyers contacted against a typical ${A.IND[s.ind].buyers}`)) bad.push("pc title thin");
    const qj=Math.abs(r.qFactor-1)>.005;
    for(const id of ["o_msv_pv","o_mult_pv"]){ if(S.titles[id][0]!==(qj?"fitted × judgment":"fitted")) bad.push(id); if(qj&&!S.titles[id][1].includes("× "+r.qFactor.toFixed(3)+" for the quality position")) bad.push(id+" title"); }
    if(qj&&!S.titles.o_msv_pv[1].includes("("+money(r.Vbase)+")")) bad.push("msv title Vbase");
    const tj=r.tMult>1.0005; if(S.titles.o_t_pv[0]!==(tj?"fitted × judgment":"fitted")) bad.push("t badge");
    if(tj&&!S.titles.o_t_pv[1].includes(`Fitted band median ${Math.round(r.ft.days)} days × ${r.tMult.toFixed(3)}`)) bad.push("t title");
    if(S.titles.o_risk_pv[0]!=="fitted"||!S.titles.o_risk_pv[1].includes("× "+r.risk.tail.toFixed(2)+" for years 9-10")) bad.push("risk badge");
    ok("badges-follow-rules",!bad.length,ctx({bad,pcTitle})); }
  { const tj=r.tMult>1.0005, t=tx.o_tstretch||"", m=/^Your ask is (\d+)% above model value, so the median here is the band's (\d+) days × ([\d.]+) /.exec(t);
    let good=tj?!!m:t==="";
    if(m) good=good&&+m[1]===Math.round((s.ask/r.V-1)*100)&&+m[1]>0&&+m[2]===Math.round(r.ft.days)&&m[3]===r.tMult.toFixed(3)&&Math.abs(+m[2]*+m[3]-parseFloat(tx.o_t))<=1+.5*+m[3]+.0005*+m[2];
    ok("time-stretch-note",good,ctx({note:t,o_t:tx.o_t,tMult:r.tMult})); }
  { const bs=E.bs, want1=bs.thin?"at the optimal ask of "+money(r.V*bs.rhoB)+" and a typical "+bs.typ+" buyers":"at the optimal ask of "+money(E.askOpt);
    const want2="at your ask of "+money(s.ask)+(bs.thin?" and "+s.buyers+" buyers":"");
    ok("scores-and-captions",tx.o_score_biz_n===want1&&tx.o_score_n===want2,ctx({biz:tx.o_score_biz_n,want1,omni:tx.o_score_n,want2})); }
  ok("business-score-not-below-omni",+tx.o_score_biz>=+tx.o_score,ctx({biz:tx.o_score_biz,omni:tx.o_score}));
  { const v=+tx.o_score_biz, band=v>=90?"a top-decile exit profile for its size":v>=62?"above most peers of its size":v>=38?"in the middle of its peer group":v>=10?"below most peers of its size, and the gaps will be priced in":"in the bottom decile for its size: buyers will price the gaps hard";
    ok("hero-caption-band-word",tx.o_cap.startsWith("The business is "+band),ctx({cap:tx.o_cap.slice(0,120),score:v})); }
  { const c=tx.o_cap, close=/the ask is close to optimal: within ([\d.]+)% of the best expected proceeds at this pool\./.exec(c);
    const far=/The ask costs (\d+)% of expected proceeds(?: and (\d+) points?)?: ([−-]?\$[\d.]+[kMB]?) is (\d+)% (above|below) the optimal ask of ([−-]?\$[\d.]+[kMB]?)\./.exec(c);
    let good;
    if(E.loss<.02) good=!!close&&close[1]===Math.max(0,E.loss*100).toFixed(1)&&!far;
    else { good=!!far&&+far[1]===+(E.loss*100).toFixed(0)&&far[3]===money(s.ask)&&far[6]===money(E.askOpt)&&+far[4]===+Math.abs((s.ask/E.askOpt-1)*100).toFixed(0)
      &&far[5]===(s.ask>=E.askOpt?"above":"below")&&(far[2]===undefined?E.askPts<1:+far[2]===E.askPts);
      /* the words agree with the two printed prices */
      if(far){ const a=pm(far[3]), o=pm(far[6]); if(far[5]==="above") good=good&&a>=o-mtol(a)-mtol(o); else good=good&&a<=o+mtol(a)+mtol(o); } }
    good=good&&c.includes("optimal ask of "+tx.o_list)===(E.loss>=.02);
    ok("hero-caption-ask-direction",good,ctx({cap:c,loss:E.loss,ask:s.ask,askOpt:E.askOpt,o_list:tx.o_list})); }
  { const c=tx.o_cap, pool=/ Contacting (\d+) buyers against a typical (\d+) costs a further (\d+)% of expected proceeds(?: and (\d+) points?)?\./.exec(c);
    const far=/The ask costs \d+% of expected proceeds(?: and (\d+) points?)?:/.exec(c);
    let good=(E.poolLoss>=.005)===!!pool;
    if(pool) good=good&&+pool[1]===s.buyers&&+pool[2]===E.bs.typ&&+pool[3]===+(E.poolLoss*100).toFixed(0)&&(pool[4]===undefined?E.poolPts<1:+pool[4]===E.poolPts);
    if(pool&&far&&far[1]!==undefined&&pool[4]!==undefined) good=good&&(+far[1]+ +pool[4]===+tx.o_score_biz-+tx.o_score);
    ok("hero-caption-points-add-up",good,ctx({cap:c,poolLoss:E.poolLoss,askPts:E.askPts,poolPts:E.poolPts,scores:[tx.o_score,tx.o_score_biz]})); }
  { const kf=S.kf, bad=[];
    if(kf.value&&kf.value[0]!=="Model-supported value"+S.titles.o_msv_pv[0]+money(r.V)+"Median price if it closes"+money(r.Vreal)+"Expected price if it closes"+money(r.Vmean)) bad.push("value: "+kf.value[0]);
    if(kf.pc&&kf.pc[0]!=="Chance of closing"+S.titles.o_pc_pv[0]+tx.o_pc) bad.push("pc: "+kf.pc[0]);
    if(kf.time&&kf.time[0]!=="Median time to close"+S.titles.o_t_pv[0]+tx.o_t) bad.push("time: "+kf.time[0]);
    if(kf.buy&&kf.buy[0]!=="Pursue firstjudgment"+tx.o_bb) bad.push("buy: "+kf.buy[0]);
    const lead=(/^(.*?\.)/.exec(tx.sensflat||"")||[])[1]||"";
    if(kf.sens&&(kf.sens[1]?lead!=="" :kf.sens[0]!==lead)) bad.push("sens: "+kf.sens[0]+" | "+lead);
    ok("kf-strips-mirror-sources",!bad.length,ctx({bad})); }
  { const p=r.qPct, pn=Math.min(99,Math.max(1,Math.round(p*100))), QB=A.MODELS.value.quality_band;
    const lab=p<.15?"bottom of the range":p<.38?"lower part of the range":p<.62?"middle of the range":p<.85?"upper part of the range":"top of the range";
    const q=tx.o_qband, want="Quality position"+ordn(pn)+" percentile · "+(r.qFactor>=1?"+":"\u2212")+Math.abs((r.qFactor-1)*100).toFixed(1)+"% on the fitted value"+money(r.Vbase*QB.lo)+money(r.Vbase)+money(r.Vbase*QB.hi);
    const row=(S.multbl.find(x=>/^Quality position:/.test(x[0]||""))||[""])[0];
    ok("quality-band-panel",q.startsWith(want)&&q.includes("here, the "+lab+" —")&&row.startsWith("Quality position: "+ordn(pn)+" percentile among peers"),ctx({q:q.slice(0,140),want,row})); }
  /* ---- equations */
  { const e=eq.eq_vs||"", HZ=A.MODELS.value.size_hinge;
    const toks=["h="+r.fv.hinge.toFixed(3),"m="+Math.min(1,Math.max(0,s.ern/Math.max(s.rev,1))).toFixed(3),"e_i="+dm(r.fv.indEff.toFixed(4)),r.fv.indEffSrc,"P=",money(r.fv.rawPoint),money(r.fv.rawPoint),r.fv.calib.toFixed(3),r.qFactor.toFixed(3),"\\boxed{"+dm(money(r.V))+"}",dm(money(s.ern)),r.M.toFixed(2)];
    const sq=seqIn(e,toks), arith=Math.abs(r.fv.rawPoint*r.fv.calib*r.qFactor/r.V-1)<1e-9, shown=Math.abs(s.ern*+r.M.toFixed(2)-r.V)<=s.ern*.005+mtol(r.V)+1;
    ok("eq-value-substitution",sq.ok&&arith&&shown&&(s.ern/1e3>HZ.cap_sde_thousands)===/slope [\d.]+ above the cap/.test(e),ctx({missing:sq.missing,eq:e.slice(0,260)})); }
  { const e=eq.eq_as||"", toks=["="+r.priceRatio.toFixed(2),(r.askEff/r.V).toFixed(3),r.rho.toFixed(3),"A="+r.anchorF.toFixed(3),r.askCeil.toFixed(3),"median "+dm(money(r.Vreal)),"\\boxed{"+dm(money(r.Vmean))+"}",pc(r.capShare)+" of closings at the ceiling",pc(r.PC,1),dm(money(r.Vmean)),"="+dm(money(r.EVp))];
    const sq=seqIn(e,toks); ok("eq-anchoring-substitution",sq.ok,ctx({missing:sq.missing,eq:e})); }
  { const e=eq.eq_ps||"", thin=r.thinF<.9995;
    const toks=["g="+(r.fc.gap>=0?"+":"")+r.fc.gap.toFixed(1)+"%",pc(r.fc.base,1),"u="+r.fc.chanShare.toFixed(2),r.fc.pen.toFixed(3)].concat(thin?[r.thinF.toFixed(3)]:[]).concat(["\\boxed{"+pc(r.PC,1)+"}","P_C^{judg}="+pc(r.PCjudg,1)]);
    const sq=seqIn(e.replace(/\^\{\\text\{judg\}\}|\^\{judg\}/g,"^{judg}"),toks);
    const prod=+(r.fc.base*100).toFixed(1)/100*(1-+r.fc.pen.toFixed(3))*(thin?+r.thinF.toFixed(3):1);
    const shown=+pc(r.PC,1).replace("%","")/100, tol=.0005+.0005*(1)+.0005*r.fc.base+(thin?.0005*r.fc.base:0)+1e-9;
    ok("eq-closing-substitution",sq.ok&&e.includes("thin pool")===thin&&Math.abs(prod-shown)<=tol,ctx({missing:sq.missing,eq:e,prod,shown})); }
  { const e=eq.eq_ts||"", toks=[tn(r.ft.days),r.tMult.toFixed(3),tn(r.tMed),"\\beta="+r.betaT.toFixed(2),tn(r.tQ(.25)),tn(r.tQ(.75)),tn(r.tMed),(r.tMean/r.tMed).toFixed(3),tn(r.tMean)];
    const sq=seqIn(e,toks);
    ok("eq-time-substitution",sq.ok&&Math.abs(r.ft.days*r.tMult-r.tMed)<1e-6&&Math.abs(Math.round(r.ft.days)*+r.tMult.toFixed(3)-Math.round(r.tMed))<=1+.0005*r.ft.days,ctx({missing:sq.missing,eq:e})); }
  { const e=eq.eq_bs||"", capped=r.top.Pj<r.top.Vj*.995;
    const toks=["pursue first: "+r.best.n,"EV="+dm(money(r.best.EV)),"pays most: "+r.top.n,dm(money(r.top.Vj)),"+"+dm(money(r.stratPrem)),"+"+pc(r.stratPrem/r.V,1)+" over model value"].concat(capped?["caps what it pays at "+dm(money(r.top.Pj))]:[]);
    const sq=seqIn(e,toks);
    ok("eq-buyer-substitution",sq.ok&&e.includes("caps what it pays")===capped&&tx.o_bb.replace(/\u00a0/g," ").length>0,ctx({missing:sq.missing,eq:e})); }
  { const e=eq.eq_comps||"", compAt=A.softMin(r.V*r.anchorF*(1+r.compPrem),r.ceil)-A.softMin(r.V*r.anchorF,r.ceil), nil=Math.abs(compAt)<.02*Math.abs(r.V*r.anchorF*r.compPrem);
    const toks=["\\kappa="+r.compK.toFixed(2),r.nEng.toFixed(2)+" of "+s.buyers+" contacted, against "+r.nEngRef.toFixed(2)+" typical",(r.compPrem>=0?"+":"-")+pc(Math.abs(r.compPrem),1)+" before the ceiling",
      nil?"(no effect at the point estimate: the ask caps the price)":(compAt>=0?"+":"-")+dm(money(Math.abs(compAt)))+" at the point estimate after it"];
    const sq=seqIn(e,toks), row=(S.multbl.find(x=>/^Competition:/.test(x[0]||""))||[]);
    const rowOk=row[0]&&row[0].startsWith("Competition: "+r.nEng.toFixed(1)+" expected offer"+(Math.abs(r.nEng-1)<.05?"":"s")+" against a typical "+r.nEngRef.toFixed(1))&&row[1]==="×"+(1+r.compPrem).toFixed(3);
    ok("eq-competition-substitution",sq.ok&&rowOk,ctx({missing:sq.missing,eq:e,row})); }
  { const qs=E.sn.filter(o=>o.k!=="ask"&&o.k!=="buyers"), top=qs.slice().sort((a,b)=>Math.abs(b.dV)-Math.abs(a.dV))[0], e=eq.eq_ds||"";
    const toks=["largest lever: "+top.n+", "+top.unit,"\\Delta V="+dm(money(top.dV,2)),dm(money(top.dE,2)),"\\Delta P_C="+dm(pp(top.dP)).replace(" pts","")];
    const sq=seqIn(e,toks), bv=S.bars.sensV.find(x=>x[0]===top.n), bp=S.bars.sensP.find(x=>x[0]===top.n);
    const barOk=bv&&bp&&pm(bv[1])===pm(money(top.dV,2))&&pm(bp[1])===pm(money(top.dE,2));
    ok("eq-sensitivity-headline",sq.ok&&barOk,ctx({missing:sq.missing,eq:e,bv,bp})); }
  { const e=eq.eq_gs||"", g=E.gap, want=(g>=0?"+":"−")+money(Math.abs(g));
    const m=/=\s*(-?\$[\d.]+[kMB]?)\s*-\s*(-?\$[\d.]+[kMB]?)\s*=\s*\\boxed\{(-?\$[\d.]+[kMB]?)\}/.exec(e);
    ok("eq-gap-substitution",!!m&&m[1]===dm(money(E.rAll.V))&&m[2]===dm(money(r.V))&&m[3]===dm(money(g))&&tx.o_gap===want&&tx.o_gapu==="from "+money(r.V)+" to "+money(E.rAll.V)
      &&tx.o_gapu.startsWith("from "+tx.o_msv),ctx({eq:e,o_gap:tx.o_gap,o_gapu:tx.o_gapu,gap:g})); }
  { const bi=E.it.find(o=>o.c>0), e=eq.eq_rs||"", row=S.intbl.find(x=>x[0]===bi.n)||[];
    const want=(bi.roi<0?"-":"")+Math.abs(bi.roi*100).toFixed(0)+"%";
    const sq=seqIn(e,[bi.n,dm(money(bi.dE,2)),dm(A.moneyIn(bi.c)),dm(A.moneyIn(bi.c)),"="+want]);
    ok("eq-roi-substitution",sq.ok&&dm(row[6]||"")===want&&E.it.filter(o=>o.c>0)[0]===bi,ctx({missing:sq.missing,eq:e,row})); }
  { const eo=eq.eq_os||"", eu=eq.eq_us||"", bV=E.best.V, bU=E.best.U, c1=S.cards[0], c2=S.cards[1];
    const sqo=seqIn(eo,["B="+dm(A.moneyIn(s.budget)),"2^{11}=2,048","commits "+dm(A.moneyIn(bV.c)),"proceeds "+dm(money(bV.proceeds))]);
    const sqU=seqIn(eu,["U="+pc(bU.PC,1),dm(money(bU.r.Vmean)),pc(1-bU.PC,1),pc(s.theta),dm(money(bU.r.V)),"$"+s.lamT.toLocaleString("en-US"),String(Math.round(bU.t+bU.days)),dm(A.moneyIn(bU.c)),"\\boxed{"+dm(money(bU.U))+"}"]);
    const Ufresh=bU.r.EVp+(1-bU.PC)*s.theta*bU.r.V-s.lamT*(bU.r.tMean+bU.days)-bU.c;
    const card=c2&&c2.bigs.find(b=>b[0]==="Closes")&&c2.bigs.find(b=>b[0]==="Closes")[1]===pc(bU.PC)&&c2.bigs.find(b=>b[0]==="Expected days")[1]===String(Math.round(bU.t+bU.days));
    ok("eq-optimizer-substitution",sqo.ok&&sqU.ok&&Math.abs(Ufresh-bU.U)<1e-6*Math.max(1,Math.abs(bU.U))&&!!card,ctx({mo:sqo.missing,mu:sqU.missing,eo,eu})); }
  { const ss=eq.eq_ss||"", cs=eq.eq_cs||"", P=A.MODELS.value.fan_quantiles;
    const sq1=seqIn(ss,["R(0.08)^{s}="+Math.pow(A.fanRatio(.08),A.FAN_S).toFixed(2),"R(0.94)^{s}="+Math.pow(A.fanRatio(.94),A.FAN_S).toFixed(2),dm(money(r.scen.bear[0])),dm(money(r.q(.5))),dm(money(r.scen.bull[1]))]);
    const sq2=seqIn(cs,["c="+r.conf.toFixed(3),r.confLabel,r.confNote,dm(money(r.q(.10))),dm(money(r.q(.90))),dm(money(r.fv.point*r.confBand80[0])),dm(money(r.fv.point*r.confBand80[1]))]);
    const sub=S.kfig.o_val[1]||"", inSub=/80% between/.test(sub)?(sub.includes(money(r.q(.10)))&&sub.includes(money(r.q(.90)))):true;
    ok("eq-scenario-substitution",sq1.ok&&sq2.ok&&inSub,ctx({m1:sq1.missing,m2:sq2.missing,ss,cs})); }
  { const zs=eq.eq_zs||"", nls=eq.eq_nls||"", zRaw=(s.rec-r.ind.rec)/A.PEER_SD.rec;
    const sq1=seqIn(zs,[s.rec.toFixed(3),r.ind.rec.toFixed(3),Math.abs(zRaw-r.z.rec)>1e-9?zRaw.toFixed(2):r.z.rec.toFixed(2),pc(r.pctile.rec)+" of peers"]);
    const C=r.contrib, sq2=seqIn(nls,["f_r="+r.fRec.toFixed(3),"f_c="+r.fCc.toFixed(3),"f_m("+r.emRaw.toFixed(2)+")="+(C["EBITDA margin (nonlinear)"]||0).toFixed(3),"f_z("+r.z.size.toFixed(2)+")="+(C["Earnings scale (saturating)"]||0).toFixed(3),"f_u="+r.fUnder.toFixed(3),"f_y="+(C["Years of clean history"]||0).toFixed(3)]);
    const zb=S.bars.zbars.find(x=>x[0]==="Recurring revenue"), pcb=n=>(S.bars.pcbars.find(x=>x[0]===n)||[])[1];
    const f3=v=>(v>=0?"+":"−")+Math.abs(v).toFixed(3);
    ok("eq-zscore-and-nonlinear",sq1.ok&&sq2.ok&&zb&&zb[1]===(r.z.rec>=0?"+":"−")+Math.abs(r.z.rec).toFixed(2)+"σ"&&pcb("Recurring revenue (nonlinear)")===f3(r.fRec)&&pcb("Customer concentration (nonlinear)")===f3(r.fCc),ctx({m1:sq1.missing,m2:sq2.missing,zs,nls})); }
  /* ---- tables */
  { const T=S.multbl, rowOf=re=>T.find(x=>re.test(x[0]||""))||[], bad=[];
    if(rowOf(/^Size-band anchor/)[2]!==(sizeAnchor(s.ern)).toFixed(2)+"×") bad.push("anchor");
    if(rowOf(/^Industry factor/)[1]!=="×"+r.fInd.toFixed(3)||rowOf(/^Industry factor/)[2]!==r.base.toFixed(2)+"×") bad.push("industry");
    if(rowOf(/^Fitted multiple/)[2]!==xx(r.fv.mult)) bad.push("fitted");
    if(rowOf(/^Quality position/)[1]!=="×"+r.qFactor.toFixed(3)||rowOf(/^Quality position/)[2]!==xx(r.M)) bad.push("quality");
    const mv=rowOf(/^Model-supported value/); if(mv[2]!==money(r.V)||mv[2]!==tx.o_msv||!mv[0].includes(money(s.ern)+" × "+xx(r.M))) bad.push("value");
    if(rowOf(/^Anchoring on an ask of/)[1]!=="×"+r.anchorF.toFixed(3)||!rowOf(/^Anchoring on an ask of/)[0].startsWith("Anchoring on an ask of "+r.priceRatio.toFixed(2)+"×")) bad.push("anchoring");
    const ce=rowOf(/^Ceiling:/); if(ce[2]!==money(r.ceil)||!ce[0].includes(pc(r.capShare)+" of closings")) bad.push("ceiling");
    const md=rowOf(/^Median price if it closes/), mn=rowOf(/^Expected price if it closes/);
    if(md[2]!==money(r.Vreal)||md[2]!==(/Median sale(\S+?)Bull/.exec(tx.focal_legend)||[])[1]) bad.push("median");
    if(mn[2]!==money(r.Vmean)||mn[2]!==S.kfig.o_val[0]) bad.push("mean");
    const dn={rec:"Recurring revenue",own:"Owner dependence",mgt:"Management depth",cc:"Customer concentration",em:"EBITDA margin",grw:"Revenue growth",gm:"Gross margin",ret:"Customer retention",fin:"Financial reporting",plt:"Channel concentration",buy:"Buyer pool depth",tail:"Industry tailwind",yrs:"Years of clean history"};
    for(const k in dn){ const row=T.find(x=>x[0]===dn[k]); if(!row){ bad.push("row "+k); continue; } const d=r.d[k], tu=r.base*d;
      if(row[1]!==(d>=0?"+":"−")+Math.abs(d*100).toFixed(1)+"%"||row[2]!==(tu>=0?"+":"−")+Math.abs(tu).toFixed(2)+"×") bad.push("stack "+k+" "+row.join("|")); }
    ok("multbl-equals-model",!bad.length,ctx({bad})); }
  { const B=S.buytbl, bad=[];
    r.buyers.forEach((b,i)=>{ const row=B[i]; if(!row){ bad.push("missing "+b.k); return; }
      if(row.name!==b.n) bad.push("order "+i+" "+row.name+" vs "+b.n);
      const cap=b.Pj<b.Vj*.995, c=row.cells;
      if(c[0][0]!==pc(b.PE)||c[1][0]!==pc(b.PCj)||c[2][0]!==(b.S>0?money(A.PHI*b.S):"—")||c[3][0]!==money(b.Vj)||(cap?c[3][1]!==money(b.Pj)+" at this ask":c[3][1]!==null)||c[4][0]!==money(b.EV)) bad.push("cells "+b.k+" "+J(c));
      const tagsWant=(b===r.best?["pursue first"]:[]).concat(b===r.top?["pays most"]:[]); if(J(row.tags)!==J(tagsWant)) bad.push("tags "+b.k+" "+J(row.tags));
      /* the row rebuilds its EV from its own printed figures (pc to 1%, money to its unit) */
      const PE=ppc(c[0][0]), PCj=ppc(c[1][0]), P=pm(cap?c[3][1]:c[3][0]), EV=pm(c[4][0]);
      const tol=(.005*PCj+.005*PE+.000025)*P+PE*PCj*mtol(P)+mtol(EV)+1;
      if(!(Math.abs(PE*PCj*P-EV)<=tol)) bad.push("EV "+b.k+" "+PE+"x"+PCj+"x"+P+" vs "+EV);
      const tip=S.stars.find(t=>t.split("\n")[0]===b.n);
      const tipWant=b.n+"\nprice it would pay "+money(b.Vj)+(cap?" ("+money(b.Pj)+" at this ask)":"")+"\nengages "+pc(b.PE)+" · closes "+pc(b.PCj)+"\nexpected value "+money(b.EV);
      if(tip!==tipWant) bad.push("tooltip "+b.k);
    });
    for(let i=1;i<B.length;i++) if(pm(B[i].cells[4][0])>pm(B[i-1].cells[4][0])) bad.push("EV order at row "+i);
    const looking=r.buyers.filter(b=>b.sizeFit>=.05), topV=Math.max(...looking.map(b=>b.Vj)); if(looking.length&&r.top.Vj!==topV) bad.push("pays most not max");
    ok("buyer-table-consistent",!bad.length,ctx({bad:bad.slice(0,4)})); }
  { const rows=S.intbl.slice(1), bad=[];
    E.it.forEach((o,i)=>{ const row=rows[i], w=intRow(o,r.V); if(!row){ bad.push("missing "+o.k); return; }
      const got={n:row[0],c:row[1],dV:row[2],dE:row[3],dP:row[4],net:row[5],roi:row[6]};
      if(got.n!==o.n||got.c!==w.c||got.dV!==w.dV||got.dE!==w.dE||got.dP!==w.dP||got.net!==w.net||got.roi!==w.roi) bad.push(J(got)+" want "+J(w)); });
    for(let i=1;i<E.it.length;i++) if(E.it[i].net>E.it[i-1].net) bad.push("sort");
    ok("intervention-table-equals-model",!bad.length,ctx({bad:bad.slice(0,3)})); }
  { const rep=(S.intbl.find(x=>/^Reprice into/.test(x[0]||""))||[])[3], dE=pm(rep), sellEV=pm(tx.o_listp.split(" · ")[2]), hero=pm(S.kfig.o_ev[0]);
    const tolr=mtol(dE)+mtol(sellEV)+mtol(hero)+1, rho=/reprice to ([\d.]+)× its new value/.exec(tx.intnote), tileRho=/^([\d.]+)× value/.exec(tx.o_listp);
    ok("reprice-row-equals-tiles",Math.abs(dE-(sellEV-hero))<=tolr&&rho&&tileRho&&rho[1]===tileRho[1]&&rho[1]===E.rhoSell.toFixed(2),ctx({rep,listp:tx.o_listp,hero:S.kfig.o_ev[0],intnote:tx.intnote.slice(0,60)})); }
  { const bad=[], zn={size:"Earnings scale",rec:"Recurring revenue",cc:"Customer concentration",own:"Owner dependence",mgt:"Management depth",grw:"Revenue growth",gm:"Gross margin",ret:"Customer retention",fin:"Financial reporting",plt:"Channel concentration",buy:"Buyer pool depth"};
    const zf=v=>(v>=0?"+":"−")+Math.abs(v).toFixed(2)+"σ", f3=v=>(v>=0?"+":"−")+Math.abs(v).toFixed(3), sf=v=>(v>0?"+":"")+money(v,2);
    Object.keys(zn).forEach((k,i)=>{ const b=S.bars.zbars[i]; if(!b||b[0]!==zn[k]||b[1]!==zf(r.z[k])) bad.push("z "+k+" "+J(b)); });
    const want=(list,fmt)=>list.map(o=>[o.n,fmt(o.v)]);
    const cmp=(got,exp,lab)=>{ if(got.length!==exp.length){ bad.push(lab+" length"); return; } const g=new Map(got), e2=new Map(exp);
      for(const [n,v] of e2) if(g.get(n)!==v) bad.push(lab+" "+n+" "+g.get(n)+" want "+v);
      for(let i=1;i<got.length;i++){ const a=Math.abs(pm(got[i][1])||parseFloat(dm(got[i][1]).replace(/[^\d.-]/g,""))), b=Math.abs(pm(got[i-1][1])||parseFloat(dm(got[i-1][1]).replace(/[^\d.-]/g,"")));
        if(a>b*(1+1e-9)+(lab==="pcbars"?.0005:mtol(b))*2) bad.push(lab+" order at "+i); } };
    cmp(S.bars.pcbars,want(Object.keys(r.contrib).map(k=>({n:k,v:r.contrib[k]})),f3),"pcbars");
    cmp(S.bars.sensV,want(E.sn.filter(o=>o.k!=="ask"&&o.k!=="buyers").map(o=>({n:o.n,v:o.dV})),sf),"sensV");
    cmp(S.bars.sensP,want(E.sn.map(o=>({n:o.n,v:o.dE})),sf),"sensP");
    ok("bars-equal-model",!bad.length,ctx({bad:bad.slice(0,4)})); }
  { const c=S.cats, ks=Object.keys(r.cats), bad=[];
    ks.forEach((k,i)=>{ if(!c[i]||c[i][0]!==k||+c[i][1]!==r.cats[k]) bad.push(k+" "+J(c[i])); });
    const mean=c[ks.length]; const vals=ks.map(k=>r.cats[k]); const m=vals.reduce((a,b)=>a+b,0)/9;
    if(!mean||mean[1]!==r.catMean.toFixed(0)||Math.abs(m-r.catMean)>1e-9) bad.push("mean "+J(mean));
    ok("categories-equal-model",!bad.length,ctx({bad})); }
  /* ---- optimiser */
  { const w1=E.rhoSell.toFixed(2)+"× value · "+pc(E.rSell.PC)+" to close · "+money(E.rSell.EVp)+" expected proceeds", w2=E.optRho.toFixed(2)+"× value · "+pc(E.rKeep.PC)+" to close · "+money(E.rKeep.EVp)+" expected proceeds";
    ok("decision-tiles-equal-model",tx.o_list===money(r.V*E.rhoSell)&&tx.o_list2===money(r.V*E.optRho)&&tx.o_listp===w1&&tx.o_listp2===w2,ctx({got:[tx.o_list,tx.o_listp,tx.o_list2,tx.o_listp2],want:[money(r.V*E.rhoSell),w1,money(r.V*E.optRho),w2]})); }
  const cardWant=(sel,rho)=>{ const names=sel.keys.length?sel.keys.map(k=>k==="reprice"?`Reprice to ${rho.toFixed(2)}× the new model value`:A.INTERV.find(i=>i.k===k).n):[sel.blocked?`Do nothing — nothing within the budget clears its cost; ${A.INTERV.find(i=>i.k===sel.blocked.k).n} would, for ${A.moneyIn(sel.blocked.c)}`
      :E.best.allIn?"Do nothing — no combination clears its cost":"Do nothing — nothing within the budget clears its cost"];
    return {rows:names.map((n,i)=>[n,sel.keys[i]?A.moneyIn(A.INTERV.find(x=>x.k===sel.keys[i]).cost(E.t)):"—"]),total:A.moneyIn(sel.c)+" of "+A.moneyIn(s.budget),
      bigs:[["Expected proceeds",money(sel.proceeds)],["Median price if it closes",money(sel.V)],["Closes",pc(sel.PC)],["Expected days",String(Math.round(sel.t+sel.days))]]}; };
  { const bad=[];
    [[S.cards[0],E.best.V,E.rhoSell,"Maximizing expected proceeds"],[S.cards[1],E.best.U,E.uRho,"Maximizing the seller's overall outcome"]].forEach(([c,sel,rho,title],ci)=>{
      if(!c){ bad.push("card "+ci+" missing"); return; } const w=cardWant(sel,rho);
      if(c.title!==title) bad.push("title "+ci);
      const body=c.rows.slice(1,-1); if(J(body)!==J(w.rows)) bad.push("rows "+ci+" "+J(body)+" want "+J(w.rows));
      const tot=c.rows[c.rows.length-1]; if(!tot||tot[0]!=="Total committed"||tot[1]!==w.total) bad.push("total "+ci+" "+J(tot));
      if(J(c.bigs)!==J(w.bigs)) bad.push("bigs "+ci+" "+J(c.bigs)+" want "+J(w.bigs)); });
    ok("optimizer-cards-equal-model",!bad.length,ctx({bad})); }
  { const c1=S.cards[0], m=/^Lifts expected proceeds (\$[\d.]+[kMB]?) over today's (\$[\d.]+[kMB]?), before the (\$[\d.]+[kMB]?) spent\.$/.exec(c1?c1.note:"");
    const cp=c1?pm(c1.bigs[0][1]):NaN, tot=c1?pm((c1.rows[c1.rows.length-1]||[])[1]):NaN;
    ok("card1-lift-sentence",!!m&&m[1]===money(E.best.V.proceeds-r.EVp)&&m[2]===S.kfig.o_ev[0]&&pm(m[3])===tot&&Math.abs(pm(m[1])-(cp-pm(m[2])))<=mtol(pm(m[1]))+mtol(cp)+mtol(pm(m[2]))+1,ctx({note:c1&&c1.note,card:c1&&c1.bigs})); }
  { const bad=[];
    S.cards.forEach((c,ci)=>{ const body=c.rows.slice(1,-1), tot=c.rows[c.rows.length-1]||[], m=/^(\$[\d.]+[kMB]?) of (\$[\d.]+[kMB]?)$/.exec(tot[1]||"");
      if(!m){ bad.push("total format "+ci); return; }
      const sum=body.reduce((a,x)=>a+(x[1]==="—"?0:pm(x[1])),0), T=pm(m[1]), B=pm(m[2]);
      if(Math.abs(sum-T)>body.length*mtol(Math.max(1,T))+mtol(T)+1) bad.push("sum "+ci+" "+sum+" vs "+T);
      if(T>B+mtol(T)+mtol(B)) bad.push("over budget "+ci);
      if(m[2]!==A.moneyIn(s.budget)||m[2]!==(s.budget?S.boxes.v_bud:"$0")) bad.push("budget echo "+ci+" "+m[2]+" box "+S.boxes.v_bud); });
    ok("card-costs-add-up-and-fit-budget",!bad.length,ctx({bad})); }
  { const c=S.cards, n=c[1]?c[1].note:"", bad=[];
    if(n!==E.cnote.text) bad.push("text differs");
    const g=(ci,k)=>{ const b=c[ci].bigs.find(x=>x[0]===k); return b?b[1]:null; };
    const tot=ci=>pm((c[ci].rows[c[ci].rows.length-1]||[])[1]);
    const sp=/spends (\$[\d.]+[kMB]?) (less|more)/.exec(n); if(sp){ const d=tot(1)-tot(0); if(sp[2]==="less"?d>mtol(tot(1))+mtol(tot(0)):d<-mtol(tot(1))-mtol(tot(0))) bad.push("spend "+sp[0]+" totals "+tot(0)+"/"+tot(1)); }
    const pcm=/is ([\d.]+) pts (less|more) likely to close/.exec(n); if(pcm){ const a=ppc(g(0,"Closes")), b=ppc(g(1,"Closes")); if(pcm[2]==="less"?b>a+.01:b<a-.01) bad.push("close "+pcm[0]+" "+a+"/"+b);
      if(Math.abs(+pcm[1]/100-Math.abs(b-a))>.01+.0005) bad.push("pts "+pcm[1]+" vs cards "+a+"/"+b); }
    const tm=/takes about (a day|\d+ days) (longer|less) from start to close/.exec(n); if(tm){ const a=+g(0,"Expected days"), b=+g(1,"Expected days"), d=tm[1]==="a day"?1:parseInt(tm[1]);
      if(tm[2]==="longer"?b<a:b>a) bad.push("time "+tm[0]+" "+a+"/"+b); if(Math.abs(Math.abs(b-a)-d)>1) bad.push("days "+d+" vs "+a+"/"+b); }
    const pr=/for a (higher|lower) price if it closes/.exec(n); if(pr){ const a=pm(g(0,"Median price if it closes")), b=pm(g(1,"Median price if it closes"));
      if(pr[1]==="higher"?b<a-mtol(a)-mtol(b):b>a+mtol(a)+mtol(b)) bad.push("price "+pr[0]+" medians "+a+"/"+b);
      const mE=E.best.U.r.Vmean-E.best.V.r.Vmean; if(pr[1]==="higher"?mE<-1e-6*E.best.V.r.Vmean:mE>1e-6*E.best.V.r.Vmean) bad.push("mean price direction "+mE); }
    const pd=/(gives up|adds) (\$[\d.]+[kMB]?) of expected proceeds/.exec(n); if(pd){ const a=pm(g(0,"Expected proceeds")), b=pm(g(1,"Expected proceeds"));
      if(pd[1]==="gives up"?b>a+mtol(a)+mtol(b):b<a-mtol(a)-mtol(b)) bad.push("proceeds "+pd[0]+" "+a+"/"+b); }
    ok("card2-note-directions",!bad.length,ctx({bad,note:n,cards:c.map(x=>x.bigs)})); }
  { const n=tx.o_listnote, bad=[], L1=pm(tx.o_list), L2=pm(tx.o_list2);
    if(n!==E.note.text) bad.push("text differs");
    const t1=tx.o_listp.split(" · "), t2=tx.o_listp2.split(" · "), pc1=ppc(t1[1]), pc2=ppc(t2[1]), ev1=pm(t1[2]), ev2=pm(t2[2]);
    if(/^With \d+% of value retained if the sale fails.*both objectives agree on the same price/.test(n)){ if(tx.o_list!==tx.o_list2) bad.push("same but tiles differ"); }
    else if(/^The cost of delay pulls the second figure below/.test(n)){
      if(!(L2<L1)) bad.push("lower but tiles "+L1+"/"+L2);
      const m=/Listing at (\$[\d.]+[kMB]?) gives up (\$[\d.]+[kMB]?) of expected proceeds, but it is ([\d.]+) pts more likely to close and closes (?:about (a day|\d+ days)|slightly) sooner on average, worth (\$[\d.]+[kMB]?) at \$([\d,]+) a day\./.exec(n);
      if(!m) bad.push("lower format"); else { if(m[1]!==tx.o_list2) bad.push("listing price");
        if(Math.abs(pm(m[2])-(ev1-ev2))>mtol(pm(m[2]))+mtol(ev1)+mtol(ev2)+1) bad.push("gives up "+m[2]+" tiles "+ev1+"/"+ev2);
        if(Math.abs(+m[3]/100-(pc2-pc1))>.01+.0005) bad.push("pts "+m[3]+" tiles "+pc1+"/"+pc2);
        const dt=E.rSell.tMean-E.rKeep.tMean; if(!(dt>0)) bad.push("says sooner but dt="+dt);
        if(m[4]===undefined&&Math.round(dt)>=1) bad.push("slightly vs "+dt); } }
    else if(/^The gap between these is the real decision\. The higher price gives up/.test(n)){
      if(!(L2>L1)) bad.push("higher but tiles "+L1+"/"+L2);
      const m=/The higher price gives up ([\d.]+) pts of closing probability and (\$[\d.]+[kMB]?) of expected proceeds for a bigger cheque if it does close(?:, takes about (a day|\d+ days) longer to close on average,)?/.exec(n);
      if(!m) bad.push("higher format"); else {
        if(Math.abs(+m[1]/100-(pc1-pc2))>.01+.0005) bad.push("pts "+m[1]+" tiles "+pc1+"/"+pc2);
        if(Math.abs(pm(m[2])-(ev1-ev2))>mtol(pm(m[2]))+mtol(ev1)+mtol(ev2)+1) bad.push("gives up "+m[2]+" tiles "+ev1+"/"+ev2);
        if(!(E.rKeep.Vmean>E.rSell.Vmean)) bad.push("bigger cheque false "+E.rSell.Vmean+"/"+E.rKeep.Vmean);
        const dt=E.rKeep.tMean-E.rSell.tMean; if(m[3]!==undefined&&!(dt>0)) bad.push("longer but dt="+dt); if(m[3]===undefined&&Math.round(Math.abs(dt))>=1) bad.push("time clause missing"); } }
    else bad.push("unknown branch");
    const coin=/close to a coin toss/.test(n); if(coin!==!!E.note.coin||(E.note.coin!==(E.note.kind!=="same"&&E.note.gain<.01*r.V))) bad.push("coin");
    const rg=/read the patient-seller price as a range, ([\d.]+)–([\d.]+)× value/.exec(n);
    if(rg&&!(rg[1]===Math.min(E.note.alt.m,E.optRho).toFixed(2)&&rg[2]===Math.max(E.note.alt.m,E.optRho).toFixed(2)&&tx.o_listp2.startsWith(E.optRho.toFixed(2)))) bad.push("range ends");
    ok("optnote-directions",!bad.length,ctx({bad,note:n.slice(0,300),tiles:[tx.o_list,tx.o_listp,tx.o_list2,tx.o_listp2]})); }
  { const bV=E.best.V, rRep=E.rRep, bad=[];
    if(bV.net<r.EVp-1e-6) bad.push("below today");
    for(const o of E.it){ if(o.k==="reprice"||o.c>s.budget) continue; const net=rRep.EVp+o.dE-o.c; if(bV.net<net-1e-6*Math.max(1,net)) bad.push(o.k+" "+net+" > "+bV.net); }
    ok("optimizer-dominates-each-row",!bad.length,ctx({bad,budget:s.budget})); }
  { const bad=[];
    S.cards.forEach((c,ci)=>{ if(!c.rows.some(x=>x[0]==="Do nothing — no combination clears its cost")) return;
      const clears=E.it.filter(o=>o.k!=="reprice"&&(ci===0?E.rRep.EVp+o.dE-o.c>r.EVp+1:true)&&o.net>0);
      if(ci===0&&clears.length) bad.push("card "+(ci+1)+" says no combination clears its cost, but "+clears.map(o=>o.k+" (net +"+money(E.rRep.EVp+o.dE-o.c-r.EVp)+", cost "+money(o.c,0)+")").join(", ")+" clear it; budget "+money(s.budget,0)); });
    ok("do-nothing-claim-true",!bad.length,ctx({bad})); }
  { const bs=E.bs, m1=/^at the optimal ask of (\$[\d.]+[kMB]?)$/.exec(tx.o_score_biz_n), good=bs.thin?true:(!!m1&&m1[1]===tx.o_list);
    ok("biz-score-ask-equals-sell-tile",good&&money(E.askOpt)===tx.o_list,ctx({biz:tx.o_score_biz_n,o_list:tx.o_list})); }
  /* ---- notes */
  { const f=tx.sensflat||"", over=(s.ask/r.V-1)*100, qs=E.sn.filter(o=>o.k!=="ask"&&o.k!=="buyers"), top=qs.slice().sort((a,b)=>Math.abs(b.dE)-Math.abs(a.dE))[0];
    const askRow=E.sn.find(o=>o.k==="ask"), share=top&&Math.abs(top.dV)>0?Math.abs(top.dE)/(r.PC*Math.abs(top.dV)):1, bad=[];
    const branch=r.askBinds&&share<.25?"bind":E.sn.every(o=>Math.abs(o.dP)<1e-9)&&over<=0?"flat":E.sn.every(o=>Math.abs(o.dP)<1e-9)?"zero":"none";
    if(branch==="bind"){ const m=/^The ask is the binding constraint\. At (\$[\d.]+[kMB]?), (?:about the model value of (\$[\d.]+[kMB]?)|(\d+)% (under|over) the model value of (\$[\d.]+[kMB]?)), (\d+)% of closings land at the ask, .* \((.+?)\) passes through (?:almost none \(under 1%\)|only about (\d+)%) of its effect on value\. Repricing is the lever: (?:a 5% higher ask changes expected proceeds by ([+−-]?\$[\d.]+[kMB]?), and a 5% lower one by|a 5% lower ask changes expected proceeds by) ([−-]?\$[\d.]+[kMB]?)\.$/.exec(f);
      if(!m) bad.push("bind format");
      else { if(m[1]!==money(s.ask)) bad.push("ask"); if(m[3]!==undefined&&(+m[3]!==+Math.abs(over).toFixed(0)||m[4]!==(over<0?"under":"over"))) bad.push("over/under");
        if(m[6]+"%"!==pc(r.capShare)) bad.push("cap share");
        if(m[7]!==top.n.toLowerCase()) bad.push("lever");
        const bar=(S.bars.sensP.find(x=>x[0]==="Asking price, 5% lower")||[])[1]; if(dm(m[10])!==dm(money(askRow.dE,2))||pm(bar)!==pm(m[10])) bad.push("5% cut "+m[10]+" bar "+bar);
        /* under value the note leads with the raise that helps (skeptic review, D8) */
        if(over<0){ const up=A.model({...s,ask:s.ask*1.05}).EVp-r.EVp; if(m[9]===undefined||dm(m[9].replace(/^\+/,""))!==dm(money(up,2))) bad.push("5% raise "+m[9]); }
        else if(m[9]!==undefined) bad.push("raise quoted over value");
        const bull=(S.scen[2]||{}).pct||""; if(r.capShare>=.06&&!bull.includes(pc(r.capShare)+" of closings at the ask ceiling")) bad.push("bull share"); } }
    else if(branch==="flat"){ if(!/^Closing probability is flat here\./.test(f)) bad.push("flat"); }
    else if(branch==="zero"){ if(!f.startsWith("Closing probability is effectively zero here. At "+over.toFixed(0)+"% over model value")) bad.push("zero"); }
    else if(f!=="") bad.push("should be empty");
    ok("sensflat-consistent",!bad.length,ctx({bad,branch,f:f.slice(0,240)})); }
  { const g=tx.o_gapnote, m=/^Executing everything costs (\$[\d.]+[kMB]?) and takes about (\d+) months\. Repriced to match, expected proceeds would move from (\$[\d.]+[kMB]?) to (\$[\d.]+[kMB]?) and the closing probability from (\d+)% to (\d+)%\./.exec(g);
    const up=E.rAll.V>r.V, tr=S.traj, trajOk=tr.p1===null?true:(tr.texts[0]==="from "+money(r.V)&&tr.texts[1]==="to "+money(E.rAll.V)&&(money(E.rAll.V)===money(r.V)||(up?tr.p1<tr.p0:tr.p1>=tr.p0)));
    ok("gapnote-consistent",!!m&&m[1]===money(E.cAll)&&+m[2]===Math.round(A.daysOf(E.t,E.allKeys)/30)&&m[3]===S.kfig.o_ev[0]&&m[4]===money(E.rAll.EVp)&&m[5]+"%"===tx.o_pc&&m[6]+"%"===pc(E.rAll.PC)&&trajOk,
      ctx({g,traj:tr,cAll:E.cAll,keys:E.allKeys})); }
  { const sc=S.scen, bad=[];
    const rngs=sc.map(x=>pmAll(x.rng)); for(let i=1;i<3;i++){ const prevHi=rngs[i-1].slice(-1)[0], lo=rngs[i][0]; if(lo<prevHi-1e-9&&!(lo===prevHi)) {} if(rngs[i][0]<rngs[i-1][0]-1e-9||rngs[i].slice(-1)[0]<rngs[i-1].slice(-1)[0]-1e-9) bad.push("order "+i); }
    if(tx.scen_t!=="Price if it closes · "+pc(1-r.PC)+" chance of no sale") bad.push("scen_t "+tx.scen_t);
    const sP=ppc(tx.scen_t.split("·")[1]), hP=ppc(tx.o_pc); if(Math.abs(sP+hP-1)>.01+1e-9) bad.push("no-sale + close != 100%: "+tx.scen_t+" / "+tx.o_pc);
    const rg=(a,b)=>Math.abs(b-a)<.005*Math.abs(b)?money(b)+(r.capShare>.3&&Math.abs(b-r.ceil)<.005*r.ceil?" (the ask ceiling)":""):money(a)+"–"+money(b);
    const want=[rg(r.scen.bear[0],r.scen.bear[1]),rg(r.scen.base[0],r.scen.base[1]),rg(r.scen.bull[0],r.scen.bull[1])];
    sc.forEach((x,i)=>{ if(x.rng!==want[i]) bad.push("rng "+i+" "+x.rng+" want "+want[i]); });
    const bullPct="80th–94th percentile of closings"+(r.capShare>=.06?" · "+pc(r.capShare)+" of closings at the ask ceiling":""); if(sc[2]&&sc[2].pct!==bullPct) bad.push("bull pct");
    ok("scenario-cards",!bad.length,ctx({bad})); }
  { const R=S.real, PRn=r.ft.indN, bad=[];
    const want0=[r.Vbase>=2e6?"Market benchmark: sale price as a share of the advisor’s benchmark (IBBA; deals this size usually list without an ask)":"Market average: sale price as a share of the ask",pc(r.ft.pctAsk,1)];
    if(!R[0]||R[0][0]!==want0[0]||R[0][1]!==want0[1]||!R[0][2].startsWith("IBBA size curve at "+money(r.Vbase)+": "+pc(r.ft.pctAskSize,1))) bad.push("row0 "+J(R[0]));
    if(!R[1]||R[1][1]!==pc(r.Vmean/s.ask,1)||!R[1][2].startsWith(money(r.Vmean)+" on an ask of "+money(s.ask)+" (median "+money(r.Vreal)+")")||R[1][2].includes("most closings land at the ceiling")!==(r.capShare>=.5)) bad.push("row1 "+J(R[1]));
    if(!R[2]||R[2][1]!==pc(r.cashShare,1)||R[2][2]!==money(r.EVcash)+" of "+money(r.EVp)+" expected proceeds"||money(r.EVp)!==S.kfig.o_ev[0]) bad.push("row2 "+J(R[2]));
    if(!R[3]||R[3][1]!==pc(1-r.cashShare,1)||R[3][2]!==money(r.deferred)+" carried by the seller") bad.push("row3 "+J(R[3]));
    ok("realisation-block",!bad.length,ctx({bad})); }
  { const T=S.tcurve, bad=[], tt=T.texts.join(" ; ");
    for(const t of [90,180,365]){ const v=pc(r.F(t)); if(!new RegExp("(^|; )"+v.replace("%","\\%")+" ; "+t+"\u2009d").test(tt)) bad.push("label "+t+" "+v); }
    const med=r.tMed<540&&isFinite(r.tMed)&&r.tMed>0; if(tt.includes("median "+Math.round(r.tMed)+"\u2009d")!==med) bad.push("median label");
    if(T.cap!=="Share of the deals that close, closed by day t ("+pc(r.PC)+" of listings close)"||!T.cap.includes(tx.o_pc)) bad.push("cap");
    const ar="Share of closing deals closed by each day, conditional on closing (median "+Math.round(r.tMed)+" days); "+pc(r.PC)+" of listings like this one close at all; of the deals that close, "+pc(r.t90)+" close within 90 days, "+pc(r.t180)+" within 180 and "+pc(r.t365)+" within 365";
    if(T.aria!==ar) bad.push("aria");
    ok("time-curve-labels",!bad.length,ctx({bad,tt:tt.slice(-120)})); }
  { const bad=[], p0=A.fitRisk(r.V,s.ind,r.rate,r.jobs,!!s.franchise,null).p;
    for(const [k,lab] of S.stOpts){ if(!k) continue; const d=(A.fitRisk(r.V,s.ind,r.rate,r.jobs,!!s.franchise,k).p-p0)*100, a=Math.abs(d).toFixed(2), sg=a==="0.00"?"":(d>=0?"+":"\u2212");
      const m=/\(([+\u2212]?)(\d+\.\d\d) pts charge-off risk, 10 yr\)$/.exec(lab); if(!m||m[1]!==sg||m[2]!==a) bad.push(k+" "+lab+" want "+sg+a); }
    if(S.stSel){ const lab=(S.stOpts.find(x=>x[0]===S.stSel)||[])[1]||"", m=/\(([+\u2212]?)(\d+\.\d\d) pts/.exec(lab), d=m?(m[1]==="\u2212"?-1:1)*+m[2]:NaN;
      if(!(Math.abs(d-(r.risk.p-p0)*100)<.005+1e-9)) bad.push("selected "+lab+" vs tile delta "+(r.risk.p-p0)*100); }
    ok("state-option-labels",!bad.length,ctx({bad:bad.slice(0,3)})); }
  { const os=E.sn.filter(o=>o.oneSided).map(o=>o.n), bk=E.sn.some(o=>o.back), n=tx.sensnote||"";
    const want=(os.length?os.join(" and ")+(os.length>1?" are at or near the ends of their ranges, so those rows are uneven differences rather than central ones.":" is at or near the end of its range, so that row is an uneven difference rather than a central one."):"")
      +(bk?(os.length?" ":"")+"Within 25% of the 600-buyer cap the pool cannot grow by a quarter, so its row shows what the last quarter of buyers added.":"");
    ok("sensnote-one-sided",n===want&&bk===(s.buyers*1.25>600),ctx({n,want})); }
  { const bad=[], lab=S.starLabels||[];
    for(const b of r.buyers){ const i=lab.indexOf(b.n); if(i<0||lab[i+1]!==money(b.Vj)+" · "+pc(b.PE)+" engage") bad.push(b.k+" "+(i<0?"missing":lab[i+1])); }
    if(!S.starMV.includes(money(r.V))) bad.push("model value label "+J(S.starMV));
    ok("star-map-labels",!bad.length,ctx({bad:bad.slice(0,3)})); }
  { const w=r.extrap||[], X=S.xwarn;
    const good=w.length?(X.items.length===w.length&&w.every((x,i)=>X.items[i]===x.txt)&&X.far===(r.extrapMax>=5)):X.items.length===0&&!X.text;
    ok("extrapolation-notice",good,ctx({items:X.items,want:w.map(x=>x.txt),extrapMax:r.extrapMax})); }
  /* ---- hygiene */
  { const all=S.consoleText+" "+S.attrs.join(" "); const m=/NaN|undefined|Infinity/.exec(all);
    ok("dom-no-nan-undefined-infinity",!m,ctx({at:m?all.slice(Math.max(0,m.index-80),m.index+40):null})); }
  { const hits=[]; const scan=(lab,t)=>{ if(t&&/[−-]\$0(?![\d.])/.test(t)) hits.push(lab+": "+t.slice(0,120)); };
    S.cards.forEach(c=>c.bigs.forEach(b=>scan("card "+b[0],b[1]))); S.real.forEach(x=>scan("real",x.join(" "))); S.scen.forEach(x=>scan("scen",x.rng));
    S.buytbl.forEach(b=>b.cells.forEach(c=>scan("buytbl "+b.name,c[0])));
    ok("dom-no-signed-zero",!hits.length,ctx({hits:hits.slice(0,4)})); }
  { const neg=[]; const chk=(lab,t)=>{ if(t&&/[−-]\$/.test(t)) neg.push(lab+": "+t); };
    for(const k of ["o_msv","o_pc","o_ev","o_list","o_list2","o_listp","o_listp2","focal_legend","o_score_biz_n","o_score_n"]) chk(k,tx[k]); chk("o_val",S.kfig.o_val.join(" "));
    S.cards.forEach(c=>{ c.rows.forEach(x=>chk("card cost",x[1])); c.bigs.forEach(b=>chk("card "+b[0],b[1])); });
    S.buytbl.forEach(b=>b.cells.forEach(c=>chk("buyer "+b.name,c.join(" ")))); S.intbl.slice(1).forEach(x=>chk("int cost",x[1]));
    S.scen.forEach(x=>chk("scen",x.rng)); S.real.forEach(x=>chk("real",x[2])); chk("multbl",S.multbl.map(x=>x[2]).join(" "));
    ok("dom-no-negative-money-where-nonnegative",!neg.length,ctx({neg:neg.slice(0,3)})); }
  { const empty=["o_score","o_score_biz","o_pc","o_msv","o_mult","o_risk","o_t","o_bb","o_list","o_list2","o_listp","o_listp2","o_gap","o_gapu","o_gapnote","o_cap","vx_ask","o_conf","scen_t","o_listnote","intnote"]
      .filter(k=>!tx[k]||!tx[k].trim()||tx[k].trim()==="—"); if(!S.kfig.o_val[0]||S.kfig.o_val[0]==="—") empty.push("o_val"); if(!S.kfig.o_ev[0]||S.kfig.o_ev[0]==="—") empty.push("o_ev");
    if(S.pending) empty.push("equations pending "+S.pending); for(const k in S.eq) if(!S.eq[k]) empty.push(k);
    ok("dom-no-empty-figures",!empty.length,ctx({empty})); }
}

/* the parts of the console a years-of-history change may touch (Data tab claim) */
function yrsAllowedDiff(a,b){
  const diffs=[];
  const cmp=(lab,x,y)=>{ if(J(x)!==J(y)) diffs.push(lab); };
  for(const k in a.txt) cmp("txt."+k,a.txt[k],b.txt[k]);
  for(const k in a.eq) if(!["eq_nls","eq_ps"].includes(k)) cmp("eq."+k,a.eq[k],b.eq[k]);
  /* eq_ps: only the unused P_C^judg may move */
  cmp("eq_ps (used part)",(a.eq.eq_ps||"").split("P_C^")[0],(b.eq.eq_ps||"").split("P_C^")[0]);
  cmp("eq_cs interval",(a.eq.eq_cs||"").split("\\\\")[1],(b.eq.eq_cs||"").split("\\\\")[1]);
  for(const k of ["intbl","buytbl","cards","scen","real","tcurve","stars","focal","kf","traj"]) cmp(k,a[k],b[k]);
  cmp("bars.sensV",a.bars.sensV,b.bars.sensV); cmp("bars.sensP",a.bars.sensP,b.bars.sensP); cmp("bars.zbars",a.bars.zbars,b.bars.zbars);
  cmp("multbl (fitted rows)",a.multbl.filter(x=>!/^(Years of clean history|Judgment multiple|Bounds on the stack|Recurring revenue|Owner dependence|Management depth|Customer concentration|EBITDA margin|Revenue growth|Gross margin|Customer retention|Financial reporting|Channel concentration|Buyer pool depth|Industry tailwind)/.test(x[0]||"")),
    b.multbl.filter(x=>!/^(Years of clean history|Judgment multiple|Bounds on the stack|Recurring revenue|Owner dependence|Management depth|Customer concentration|EBITDA margin|Revenue growth|Gross margin|Customer retention|Financial reporting|Channel concentration|Buyer pool depth|Industry tailwind)/.test(x[0]||"")));
  return diffs;
}
/* figures in a snapshot, for round-trip comparisons */
const fig=S=>({txt:S.txt,eq:S.eq,multbl:S.multbl,intbl:S.intbl,buytbl:S.buytbl,cards:S.cards,bars:S.bars,cats:S.cats,focal:S.focal,tcurve:S.tcurve,stars:S.stars,scen:S.scen,kf:S.kf,real:S.real,stOpts:S.stOpts,titles:S.titles,attrs:S.attrs,consoleText:S.consoleText,s:S.s});
function firstDiff(a,b){ for(const k in a){ const x=J(a[k]), y=J(b[k]); if(x!==y){ let i=0; while(i<x.length&&x[i]===y[i]) i++; return k+" @"+i+": "+x.slice(Math.max(0,i-60),i+60)+" || "+y.slice(Math.max(0,i-60),i+60); } } return null; }

/* ---------------------------------------------------------------- the Data tab's live figures */
function dataTabChecks(dataText,calibRows){
  const prof=(k,ern,rev)=>{ const I=A.IND[k], r=rev||ern/A.typMargin(k,ern); return {ind:k,rev:r,ern,ask:0,...A.peerMedians(k,ern,r),yrs:6,buyers:(I.buyers||50)}; };
  const at=(k,e,rv,ask)=>{ const s=prof(k,e,rv); const V=A.model({...s,ask:1}).V; return A.model({...s,ask:ask||V}); };
  const mMed=at("prof",158950);
  const e2s=(k,e)=>{ let x=e; for(let i=0;i<20;i++){ const w=A.sdeEbitdaWedge(A.naicsFor(k),x/A.typMargin(k,x)); x=e*(w||1); } return x; };
  const lmmS=e2s("mfg",1.5e6), ulmmS=e2s("mfg",3.5e6);
  const ms=at("prof",158950,703000), lmm=A.model({...prof("mfg",lmmS),chan:"intermediary",ask:A.model({...prof("mfg",lmmS),ask:1}).V}), ulmm=at("mfg",ulmmS);
  const msMkt=at("prof",158950,703000,350000/0.94);
  const msTyp=at("prof",158950,703000,A.model({...prof("prof",158950,703000),ask:1}).V*M_TYP), eTyp=msTyp.Vmean/msTyp.inputs.ask;
  const q=e=>{ const I=A.IND.medical, rv=e/A.typMargin("medical",e), P=A.peerMedians("medical",e,rv);
    /* one standard deviation better than the peers in composite: each dimension its weight's share of its own peer spread */
    const t={ind:"medical",rev:rv,ern:e,ask:1,yrs:6,buyers:(I.buyers||50)+10};
    for(const k of A.MODELS.value.quality_band.dimensions) t[k]=P[k]+(k==="own"||k==="cc"||k==="plt"?-1:1)*A.QW.w[k]/A.QW.norm*A.PEER_SD[k];
    const V=A.model(t).V; return A.omniScore(A.model({...t,ask:V*1.05})); };
  const want=[mMed.dsum.toFixed(3),xx(ms.M),money(msMkt.Vreal,2),Math.round(ms.tMed)+" days",pc(lmm.PC),pc(ulmm.PC),pc(eTyp,1),sizeAnchor(2e7).toFixed(2)+"×",sizeAnchor(1.4e6).toFixed(2)+"×",sizeAnchor(3.5e6).toFixed(2)+"×",q(1e5)+" → "+q(2e7)];
  const got=calibRows.map(x=>dm(x));
  ok("data-tab-live-figures",J(got)===J(want.map(dm)),()=>J({got,want}));
  const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false}, Vx=A.model({...ex,ask:1}).V,
    t=[1,1.2,1.5,2].map(m=>Math.round(A.model({...ex,ask:Vx*m}).tMed));
  const sent=`For the framework example (model value ${money(Vx)}) the median is ${t[0]} days at value, ${t[1]} at 1.2×, ${t[2]} at 1.5× and ${t[3]} at 2×.`;
  ok("data-tab-live-figures",dataText.replace(/\s+/g," ").includes(sent),()=>J({want:sent}));
  const D={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75}, lo={...D}, hi={...D};
  const ends={rec:[0,1],own:[.14,.95],mgt:[.08,.92],cc:[.01,.70],fin:[.14,.96],grw:[-.25,.70],gm:[.12,.97],ret:[.05,.99],plt:[.05,.95]};
  for(const k in ends){ const inv=k==="own"||k==="cc"||k==="plt"; lo[k]=inv?ends[k][1]:ends[k][0]; hi[k]=inv?ends[k][0]:ends[k][1]; }
  const rl=A.model(lo), rh=A.model(hi);
  const sw=`multiple from ${xx(rl.Mjudg)} to ${xx(rh.Mjudg)} on coefficients nobody had estimated; here the same sweep moves the console’s multiple from ${xx(rl.M)} to ${xx(rh.M)}: the fitted ${xx(rl.fv.mult)}, which the sliders do not touch, times a quality position of ×${rl.qFactor.toFixed(2)} to ×${rh.qFactor.toFixed(2)}`;
  ok("data-tab-live-figures",dataText.replace(/\s+/g," ").includes(sw)&&rl.fv.mult===rh.fv.mult,()=>J({want:sw}));
  /* the owner-pay share of SDE in the wedge (R5-5) and the fitted margin range at $200k SDE */
  const share=sde=>Object.keys(A.IND).map(k=>A.sdeEbitdaWedge(A.naicsFor(k),sde/A.typMargin(k,sde))).filter(w=>w).map(w=>1-1/w), pr=v=>Math.round(v*100)+"%";
  const a=share(2e5), c=share(3e6), ws=`In the wedge the console uses it is ${pr(Math.min(...a))}–${pr(Math.max(...a))} of SDE at $200k across its industries and ${pr(Math.min(...c))}–${pr(Math.max(...c))} at $3M`;
  ok("data-tab-live-figures",dataText.replace(/\s+/g," ").includes(ws),()=>J({want:ws}));
  const mm=Object.keys(A.IND).map(k=>A.typMargin(k,2e5)), ms2=`fitted medians ${Math.round(Math.min(...mm)*100)}–${Math.round(Math.max(...mm)*100)}% at $200k SDE`;
  ok("data-tab-live-figures",dataText.replace(/\s+/g," ").includes(ms2),()=>J({want:ms2}));
}

/* ---------------------------------------------------------------- driver */
async function partB(){
  if(!pw){ console.log("SKIP browser: playwright not found"); return; }
  const b=await pw.chromium.launch();
  const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  const p=await ctx.newPage(); const errs=[];
  p.on("pageerror",e=>errs.push("pageerror: "+e.message));
  p.on("console",m=>{ if(m.type()==="error") errs.push("console: "+m.text()); });
  await p.addInitScript(ids=>{ window.__OUT_IDS=ids; window.__ft={}; const o=CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText=function(t){ try{ const id=this.canvas&&this.canvas.id; if(id){ const a=(window.__ft[id]=window.__ft[id]||[]); a.push(String(t)); if(a.length>40) a.shift(); } }catch(e){} return o.apply(this,arguments); }; },OUTPUT_IDS);
  await p.goto("file://"+path.join(ROOT,"index.html"));
  await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
  await settle(p,true);
  const snap=async()=>p.evaluate(pageSnap);
  const S0=await snap();                                    /* the page as loaded */
  /* $4.05M since the third round's peer medians and spreads (the largest customer's median .14, its spread .18): $4.09M before */
  ok("reset-restores-defaults",Object.keys(DEF_UI).every(k=>S0.s[k]===DEF_UI[k])&&money(S0.r.V)==="$4.05M",()=>J({s:S0.s,V:S0.r.V}));
  /* the Data tab's live figures, once */
  { const d=await p.evaluate(()=>({text:document.getElementById("view-data").textContent,attrs:[...document.querySelectorAll("#view-data [title],#view-data [aria-label]")].map(e=>(e.getAttribute("title")||"")+(e.getAttribute("aria-label")||"")).join(" | "),
      calib:[...document.querySelectorAll("#calib .chk")].map(r=>{ const v=r.querySelector(":scope>span.n:not(.muted)"); return v?v.textContent.trim():null; })}));
    const m=/NaN|undefined|Infinity/.exec(d.text+" "+d.attrs); ok("dom-no-nan-undefined-infinity",!m,()=>J({dataTab:m?(d.text+" "+d.attrs).slice(m.index-80,m.index+40):null}));
    dataTabChecks(d.text,d.calib);
    const L=await p.evaluate(()=>{ const sec=[...document.querySelectorAll("#dataviews section.sec")].find(x=>/^Judg(e)?ment/.test(x.querySelector("h2").textContent.trim()));
      const rows=sec?[...sec.querySelectorAll("table tbody tr")].map(tr=>tr.cells[1]?tr.cells[1].textContent.trim():null):[];
      const head=sec?(/(\d+)\s*parameters/.exec(sec.querySelector("h2").textContent)||[])[1]:null;
      const tally=[...document.querySelectorAll("#dataviews .tally > div")].filter(x=>x.querySelector(".n")&&x.querySelector(".k")).map(x=>[x.querySelector(".n").textContent.replace(/[^\d]/g,""),x.querySelector(".k").textContent]);
      return {rows,head,tally}; });
    const sum=L.rows.reduce((x,y)=>x+(+y||0),0), tj=(L.tally.find(x=>/judgment/.test(x[1]))||[])[0];
    ok("data-tab-live-figures",sum>0&&String(sum)===L.head&&L.head===tj,()=>J({rowsSum:sum,head:L.head,tally:tj,rows:L.rows})); }
  let states=NOSTATES?[]:STATES.concat(randomStates(NRAND));
  if(ONLY) states=states.filter(x=>ONLY.split(",").includes(x.name));
  /* adversarial states from Part A */
  if(ONLY&&!ONLY.split(",").some(x=>x.startsWith("adv-"))){} else if(ADV.repriceZero){ const a=ADV.repriceZero, b=a.base; states.push({name:"adv-reprice-signed-zero",sel:{i_ind:b.ind},typed:{rev:String(b.rev),ern:String(b.ern),buy:String(b.buyers)},ask:String(a.ask)}); }
  if(ADV.netZero){ const a=ADV.netZero, b=a.base; states.push({name:"adv-net-days-signed-zero",sel:{i_ind:b.ind},typed:{rev:String(b.rev),ern:String(b.ern),buy:String(b.buyers)},ask:String(a.ask)}); }
  if(ADV.roiZero){ const a=ADV.roiZero, b=a.base; states.push({name:"adv-roi-signed-zero",typed:{rev:String(Math.round(b.rev)),ern:String(Math.round(b.ern)),buy:String(b.buyers)}}); }
  if(ADV.doNothing){ const a=ADV.doNothing; states.push({name:"adv-do-nothing",typed:{bud:a.base.budget?String(a.base.budget):"none"},ask:String(a.ask)}); }
  let dataHash0=null, n=0;
  for(const st of states){
    const t0=Date.now(); let askTyped, S;
    try{ askTyped=await enter(p,st); S=await snap(); }
    catch(e){ console.log("ERROR entering "+st.name+": "+e.message); continue; }
    const E=expect(S.s);
    checkState(st.name,st,askTyped,S,E);
    /* tab round trip */
    await p.click('.tab[data-v="data"]'); await p.waitForFunction(()=>!document.getElementById("view-data").hidden);
    await p.evaluate(()=>new Promise(r=>setTimeout(r,80)));
    await p.click('.tab[data-v="console"]'); await p.waitForFunction(()=>!document.getElementById("view-console").hidden);
    await settle(p,true);
    const S2=await snap(); const fd=firstDiff(fig(S),fig(S2));
    /* the Data tab is decorated once on its first view (v8-data typesets Model II), so the reference is its text after a view */
    if(dataHash0===null) dataHash0=S2.dataHash; else ok("data-tab-state-independent",S2.dataHash===dataHash0,()=>J({state:st.name,hash:S2.dataHash,first:dataHash0}));
    ok("tab-roundtrip-stable",fd===null,()=>J({state:st.name,diff:fd}));
    n++; process.stdout.write(`  state ${n}/${states.length} ${st.name} (${Date.now()-t0} ms)\n`);
  }
  if(!NOSEQ){
  /* reset after the stress states: exact defaults, same page as loaded */
  for(const pre of [{name:"pre-huge",sel:{i_ind:"saas",i_st:"WY"},fr:true,typed:{rev:"5B",ern:"1B",buy:"600",bud:"1B",yrs:"40"},ask:50},{name:"pre-tiny",sel:{i_ind:"rest"},typed:{rev:"10000",ern:"1000",buy:"5",bud:"none",lam:"none",th:"0"},ask:"1000"}]){
    await enter(p,pre); await p.click("#reset"); await settle(p,true);
    const S=await snap(); const fd=firstDiff(fig(S0),fig(S)), bad=Object.keys(S.bad).filter(k=>S.bad[k]);
    ok("reset-restores-defaults",fd===null&&!bad.length,()=>J({after:pre.name,diff:fd,bad}));
  }
  /* years of clean history: only the confidence figure, categories and unused judgment panels may move */
  for(const ys of ["1","2","12"]){ await enter(p,{name:"y-base"}); const a=await snap(); await typeBox(p,"v_yrs",ys); await p.evaluate(()=>document.activeElement&&document.activeElement.blur()); await settle(p,true);
    const b2=await snap(); const d=yrsAllowedDiff(a,b2); ok("yrs-moves-only-judgment-panels",!d.length,()=>J({yrs:ys,moved:d})); }
  for(const st of [{name:"y-thin",typed:{buy:"10"},ask:1.3},{name:"y-small",sel:{i_ind:"auto"},typed:{rev:"700k",ern:"150k"},ask:1.1}]) for(const ys of ["1","12"]){
    await enter(p,st); const a=await snap(); await typeBox(p,"v_yrs",ys); await p.evaluate(()=>document.activeElement&&document.activeElement.blur()); await settle(p,true);
    const b2=await snap(); const d=yrsAllowedDiff(a,b2); ok("yrs-moves-only-judgment-panels",!d.length,()=>J({state:st.name,yrs:ys,moved:d})); }
  /* P_C at the same ask/value ratio does not read quality; quality never moves the size band */
  const qMoves=[["i_own","0.42"],["i_mgt","0.92"],["i_fin","0.14"],["v_rec","10"],["v_cc","45"],["v_grw","-10"]];
  for(const rho of [.85,1.0,1.2,1.6]) for(const [id,val] of qMoves){
    await enter(p,{name:"q-base",ask:rho}); const a=await snap();
    if(id.startsWith("i_")) await p.selectOption("#"+id,val); else await typeBox(p,id,val);
    await settle(p); const V=await p.evaluate(()=>STATE.r.V); await typeBox(p,"v_ask",String(Math.round(V*rho))); await p.evaluate(()=>document.activeElement&&document.activeElement.blur()); await settle(p,true);
    const b2=await snap();
    const eps=x=>texNorm(x.eq.eq_ps||""), base=x=>(/P_C=\\underbrace\{([\d.]+%)\}_\{base rate, u=([\d.]+)\}/.exec(eps(x))||[]).slice(1).join("|"), pen=x=>(/\(1-\\underbrace\{([\d.]+)\}_\{gap penalty\}/.exec(eps(x))||[])[1];
    ok("pc-quality-free-at-same-ratio",a.txt.o_pc===b2.txt.o_pc&&base(a)===base(b2)&&base(a)!==""&&Math.abs(+pen(a)-+pen(b2))<=.0011,()=>J({rho,move:id+"="+val,pc:[a.txt.o_pc,b2.txt.o_pc],base:[base(a),base(b2)],pen:[pen(a),pen(b2)],ratio:[a.r.V?a.s.ask/a.r.V:0,b2.s.ask/b2.r.V]}));
    const fm=x=>(x.multbl.find(y=>/^Fitted multiple/.test(y[0]||""))||[])[2], band=x=>(/t_\{med\}=t_\{band\} e\^\{0\.10 g\}=([\d,]+)/.exec(texNorm(x.eq.eq_ts||"").replace(/\\text\{med\}/g,"med").replace(/\\text\{band\}/g,"band"))||[])[1];
    const cash=x=>(x.real[2]||[])[1];
    const below=a.s.ask<=a.r.V&&b2.s.ask<=b2.r.V;
    ok("quality-keeps-size-band",fm(a)===fm(b2)&&band(a)===band(b2)&&band(a)!==undefined&&cash(a)===cash(b2)&&base(a)===base(b2)&&(!below||a.txt.o_t===b2.txt.o_t),
       ()=>J({rho,move:id+"="+val,fm:[fm(a),fm(b2)],band:[band(a),band(b2)],cash:[cash(a),cash(b2)],t:[a.txt.o_t,b2.txt.o_t]}));
  }
  }
  /* keyboard sweeps of four sliders: every stop gets the full per-state check, and the stops are compared */
  if(!NOSWEEP){
    const sweep=async(name,id,setup,keys,steps)=>{ await enter(p,{name:"sweep-"+name,...setup}); await p.focus("#"+id); await p.keyboard.press(keys[0]); await settle(p,true);
      const out=[];
      for(let i=0;i<=steps;i++){ const S=await p.evaluate(pageSnap); checkState("sweep-"+name+"#"+i,null,undefined,S,expect(S.s)); out.push(S);
        if(i<steps){ await p.focus("#"+id); for(const k of keys.slice(1)) await p.keyboard.press(k); await p.evaluate(()=>document.activeElement&&document.activeElement.blur()); await settle(p,true); } }
      /* the keyboard must have moved the slider: a stuck sweep would pass every directional check vacuously */
      const field={i_ask:"ask",i_th:"theta",i_buy:"buyers",i_ern:"ern"}[id], vals=out.map(S=>S.s[field]);
      ok("slider-sweep-directions",vals.every((v,i)=>i===0||v>vals[i-1]||(i===vals.length-1&&v===vals[i-1])),()=>J({sweep:name,stuck:vals}));
      return out; };
    const num=t=>parseFloat(String(t).replace(/[^\d.]/g,"")), pcOf=S=>ppc(S.txt.o_pc), dir=(arr,f,up,tol)=>{ for(let i=1;i<arr.length;i++){ const a=f(arr[i-1]), b=f(arr[i]); if(up?b<a-tol(a):b>a+tol(a)) return i; } return -1; };
    const A1=await sweep("ask","i_ask",{},["Home","PageUp"],10);
    let k=dir(A1,pcOf,false,()=>1e-9); ok("slider-sweep-directions",k<0,()=>J({sweep:"ask",at:k,pc:A1.map(x=>x.txt.o_pc)}));
    k=dir(A1,S=>num(S.txt.o_t),true,()=>0); ok("slider-sweep-directions",k<0,()=>J({sweep:"ask",at:k,days:A1.map(x=>x.txt.o_t)}));
    k=dir(A1,S=>pm(S.kfig.o_val[0]),true,v=>mtol(v)); ok("slider-sweep-directions",k<0,()=>J({sweep:"ask",at:k,price:A1.map(x=>x.kfig.o_val[0])}));
    const T1=await sweep("theta","i_th",{typed:{th:"60"}},["ArrowRight","ArrowRight","ArrowRight","ArrowRight","ArrowRight","ArrowRight"],8);
    k=dir(T1,S=>pm(S.txt.o_list2),true,v=>mtol(v)); ok("slider-sweep-directions",k<0,()=>J({sweep:"theta",at:k,walk:T1.map(x=>[x.s.theta,x.txt.o_list2])}));
    ok("slider-sweep-directions",T1.every(S=>S.txt.o_list===T1[0].txt.o_list),()=>J({sweep:"theta",sell:T1.map(x=>x.txt.o_list)}));
    const B1=await sweep("buyers","i_buy",{},["Home","PageUp"],10);
    for(const [lab,f] of [["pc",pcOf],["proceeds",S=>pm(S.kfig.o_ev[0])],["omni",S=>+S.txt.o_score],["business",S=>+S.txt.o_score_biz]]){
      k=dir(B1,f,true,v=>lab==="proceeds"?mtol(v):1e-9); ok("slider-sweep-directions",k<0,()=>J({sweep:"buyers",fig:lab,at:k,vals:B1.map(x=>[x.s.buyers,lab==="pc"?x.txt.o_pc:lab==="proceeds"?x.kfig.o_ev[0]:lab==="omni"?x.txt.o_score:x.txt.o_score_biz])})); }
    const E1=await sweep("earnings","i_ern",{},["Home","PageUp","PageUp"],5);
    k=dir(E1,S=>pm(S.txt.o_msv),true,v=>mtol(v)); ok("slider-sweep-directions",k<0,()=>J({sweep:"earnings",at:k,vals:E1.map(x=>[x.s.ern,x.txt.o_msv])}));
  }
  /* phone width: the narrow layouts re-flow every equation and chart; the figures must survive */
  if(!NOPHONE){ const pctx=await b.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"}), pp2=await pctx.newPage();
    pp2.on("pageerror",e=>errs.push("phone pageerror: "+e.message)); pp2.on("console",m=>{ if(m.type()==="error") errs.push("phone console: "+m.text()); });
    await pp2.addInitScript(ids=>{ window.__OUT_IDS=ids; window.__ft={}; const o=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(t){ try{ const id=this.canvas&&this.canvas.id; if(id){ const a=(window.__ft[id]=window.__ft[id]||[]); a.push(String(t)); if(a.length>40) a.shift(); } }catch(e){} return o.apply(this,arguments); }; },OUTPUT_IDS);
    await pp2.goto("file://"+path.join(ROOT,"index.html"));
    await pp2.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
    await settle(pp2,true);
    const before=ORDER.reduce((a,k)=>a+INV[k].fails,0);
    for(const nm of ["defaults","ask-2V","thin-pool-5","sde-above-3M-cap","huge-saas-CA-franchise","worst-quality","ask-0.05V","risk-capped-dist","ask-hard-max","tiny-restaurant"]){
      const st=STATES.find(x=>x.name===nm); if(!st) continue;
      const b0=ORDER.reduce((a,k)=>a+INV[k].fails,0);
      try{ const at=await enter(pp2,st); const S=await pp2.evaluate(pageSnap); checkState("phone:"+nm,st,at,S,expect(S.s)); }
      catch(e){ console.log("ERROR phone "+nm+": "+e.message); }
      const b1=ORDER.reduce((a,k)=>a+INV[k].fails,0);
      /* a phone state may only fail where the same desktop state fails (a defect of the state, not of the narrow layout) */
      const deskFails=ORDER.filter(k=>INV[k].all.some(c=>J(c).includes('"state":"'+nm+'"'))).length;
      ok("phone-width-figures",b1-b0<=deskFails,()=>J({state:nm,newFails:b1-b0,desktopFails:deskFails,see:ORDER.filter(k=>INV[k].all.some(c=>J(c).includes("phone:"+nm)))}));
    }
    await pctx.close(); }
  /* motion on (the default experience): the opening film is skipped with Escape, the focal planet animates, tab switches
     and reset run through the warp hop; the figures must be the same */
  if(!NOMOTION){ const mctx=await b.newContext({viewport:{width:1440,height:900}}), mp=await mctx.newPage();
    mp.on("pageerror",e=>errs.push("motion pageerror: "+e.message)); mp.on("console",m=>{ if(m.type()==="error") errs.push("motion console: "+m.text()); });
    await mp.addInitScript(ids=>{ window.__OUT_IDS=ids; window.__ft={}; const o=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(t){ try{ const id=this.canvas&&this.canvas.id; if(id){ const a=(window.__ft[id]=window.__ft[id]||[]); a.push(String(t)); if(a.length>40) a.shift(); } }catch(e){} return o.apply(this,arguments); }; },OUTPUT_IDS);
    await mp.goto("file://"+path.join(ROOT,"index.html"));
    for(let i=0;i<40;i++){ if(await mp.evaluate(()=>!document.getElementById("boot"))) break; await mp.keyboard.press("Escape").catch(()=>{}); await mp.waitForTimeout(500); }
    await mp.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
    await settle(mp,true); await mp.waitForTimeout(400);
    for(const nm of ["defaults","ask-2V","thin-pool-5","ask-at-V"]){ const b0=ORDER.reduce((a,k)=>a+INV[k].fails,0);
      const st=STATES.find(x=>x.name===nm);
      try{ const at=await enter(mp,st); await mp.waitForTimeout(1200); const S=await mp.evaluate(pageSnap); checkState("motion:"+nm,st,at,S,expect(S.s));
        await mp.click('.tab[data-v="data"]'); await mp.waitForFunction(()=>!document.getElementById("view-data").hidden,null,{timeout:10000});
        await mp.waitForTimeout(900); await mp.click('.tab[data-v="console"]'); await mp.waitForFunction(()=>!document.getElementById("view-console").hidden,null,{timeout:10000});
        await mp.waitForTimeout(900); await settle(mp,true);
        const S2=await mp.evaluate(pageSnap); const fd=firstDiff(fig(S),fig(S2)); ok("tab-roundtrip-stable",fd===null,()=>J({state:"motion:"+nm,diff:fd})); }
      catch(e){ console.log("ERROR motion "+nm+": "+e.message); }
      ok("motion-on-figures",ORDER.reduce((a,k)=>a+INV[k].fails,0)===b0,()=>J({state:nm,see:ORDER.filter(k=>INV[k].all.some(c=>J(c).includes("motion:"+nm)))}));
    }
    await mctx.close(); }
  ok("no-page-errors",!errs.length,()=>J({errs:errs.slice(0,3)}));
  await b.close();
}

(async()=>{
  const ta=NOSCAN?0:partA(); console.log(`# part A (node fine scans) ${ta} ms; adversarial states found: ${Object.keys(ADV).join(", ")||"none"}`);
  if(!NOBROWSER){ const t0=Date.now(); await partB(); console.log(`# part B (browser) ${Date.now()-t0} ms`); }
  let nf=0;
  for(const k of ORDER){ const v=INV[k]; if(!v.cases&&NOBROWSER) continue;
    if(v.fails){ nf++; console.log(`FAIL ${k} cases=${v.cases} fails=${v.fails} first=${typeof v.first==="string"?v.first:J(v.first)}`); }
    else console.log(`PASS ${k} cases=${v.cases}`); }
  if(JSONOUT) fs.writeFileSync(JSONOUT,JSON.stringify(ORDER.map(k=>INV[k]),null,1));
  console.log(`# ${ORDER.length} invariants, ${nf} failing`);
  process.exit(nf?1:0);
})().catch(e=>{ console.error(e); process.exit(2); });
