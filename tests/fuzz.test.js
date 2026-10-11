/* Property-based checks: thousands of random businesses across the whole reachable
   input space, each checked against invariants that must hold for ANY input. Hand
   cases catch one bug; an invariant catches the whole class.
   Run: node tests/fuzz.test.js [samples]   (seeded, so failures reproduce) */
const A=require("./load.js");
const N=+(process.argv[2]||1500);
let seed=20261006; const rnd=()=>{ seed=(seed*16807)%2147483647; return (seed-1)/2147483646; };
const pick=a=>a[Math.floor(rnd()*a.length)];
const logU=(lo,hi)=>Math.exp(Math.log(lo)+rnd()*(Math.log(hi)-Math.log(lo)));
const INDS=Object.keys(A.IND), STS=[null,...Object.keys(A.MODELS.risk.state_effects)];
const fails={}; let checks=0;
const ok=(c,name,ctx)=>{ checks++; if(!c){ (fails[name]=fails[name]||[]).push(ctx); } };

function sample(){
  const rev=logU(1e4,5e9), ern=rev*(.005+rnd()*.915);
  const s={ind:pick(INDS),st:pick(STS),franchise:rnd()<.2,rev,ern,
    grw:-.25+rnd()*.95, gm:.12+rnd()*.8, rec:rnd(), cc:.01+rnd()*.69, ret:.45+rnd()*.54, plt:.05+rnd()*.9,
    own:pick([.95,.72,.42,.14]), mgt:pick([.08,.36,.66,.92]), fin:pick([.14,.45,.74,.96]),
    yrs:1+Math.floor(rnd()*12), buyers:5+Math.floor(rnd()*596), budget:rnd()<.15?0:rev*.15*rnd(),
    lamT:Math.floor(rnd()*81)*50, theta:rnd(), rate:10.5};
  s.jobs=Math.max(2,Math.round(s.rev/150000));
  return s;
}
const fin=x=>typeof x==="number"&&isFinite(x);
const ctx=(s,extra)=>JSON.stringify({...s,...extra},(k,v)=>typeof v==="number"?+v.toPrecision(5):v);

for(let i=0;i<N;i++){
  const s0=sample(), V0=A.model({...s0,ask:1}).V;
  const rho=logU(.3,3), s={...s0,ask:V0*rho}, r=A.model(s);

  /* 1. everything finite and in range */
  ok([r.V,r.Vreal,r.Vmean,r.EVp,r.PC,r.tMed,r.tMean,r.risk.p,r.cashShare,r.M].every(fin),"finite",ctx(s));
  ok(r.PC>=0&&r.PC<=1&&r.risk.p>=0&&r.risk.p<=1&&r.cashShare>0&&r.cashShare<=1,"probabilities in [0,1]",ctx(s));
  ok(r.V>0&&r.Vreal>0&&r.EVp>0,"positive values",ctx(s));
  /* 2. value does not depend on the ask */
  ok(Math.abs(r.V/V0-1)<1e-9,"value independent of ask",ctx(s));
  /* 3. the ceiling holds across the whole distribution */
  const capAsk=s.ask*Math.max(1,r.ft.pctAskSize)*(1+1e-9);
  ok(r.Vreal<=capAsk&&r.q(.99)<=capAsk&&r.Vmean<=capAsk,"realised price within ask headroom",ctx(s,{pa:r.ft.pctAskSize}));
  /* 4. quantiles monotone, median is Vreal, expected proceeds = P_C x mean */
  const qs=[.02,.1,.25,.5,.75,.9,.98].map(r.q);
  ok(qs.every((v,j)=>j===0||v>=qs[j-1]*(1-1e-9)),"quantiles monotone",ctx(s));
  ok(Math.abs(r.q(.5)/r.Vreal-1)<1e-9,"q(.5) = median",ctx(s));
  ok(Math.abs(r.EVp/(r.PC*r.Vmean)-1)<1e-9,"EVp = P_C x mean",ctx(s));
  ok(r.Vmean>=r.q(.02)*(1-1e-9)&&r.Vmean<=r.ceil*(1+1e-9),"mean inside the price distribution",ctx(s));
  ok(r.capShare>=0&&r.capShare<=1,"ceiling share in [0,1]",ctx(s));
  /* 5. scores in range */
  const sc=A.omniScore(r); ok(sc>=1&&sc<=99&&Number.isInteger(sc),"score in 1..99",ctx(s,{sc}));
  ok(Object.values(r.cats).every(v=>v>=1&&v<=99&&Number.isInteger(v)),"category scores in 1..99",ctx(s,{cats:r.cats}));
  /* the business score (this profile at its proceeds optimum, same reference population) is never below the Omni score */
  { const scQ=A.omniScore(A.model({...s,ask:V0*A.bestRatio(s,0,0)})); ok(scQ>=sc,"business score not below the Omni score",ctx(s,{sc,scQ})); }
  /* the ceiling share is continuous in the ask: no 1/48 steps */
  ok(Math.abs(A.model({...s,ask:s.ask*1.001}).capShare-r.capShare)<.01,"ceiling share continuous in the ask",ctx(s));

  /* 6. monotone in every quality input: improving one never lowers value or proceeds */
  const better={rec:Math.min(1,s.rec+.1),cc:Math.max(.005,s.cc-.05),ret:Math.min(.99,s.ret+.03),
    plt:Math.max(.02,s.plt-.08),grw:Math.min(1.5,s.grw+.05),gm:Math.min(.97,s.gm+.03),
    own:Math.max(.02,s.own-.1),mgt:Math.min(.99,s.mgt+.1),fin:Math.min(1,s.fin+.1)};
  for(const k in better){ const rb=A.model({...s,[k]:better[k]});
    ok(rb.V>=r.V*(1-1e-9),`better ${k} never lowers value`,ctx(s));
    ok(rb.EVp>=r.EVp*(1-1e-6),`better ${k} never lowers expected proceeds`,ctx(s)); }
  /* earnings up at fixed revenue never lowers value; more buyers never lowers proceeds */
  if(s.ern*1.05<=s.rev*.92) ok(A.model({...s,ern:s.ern*1.05}).V>=r.V*(1-1e-9),"more earnings never lowers value",ctx(s));
  ok(A.model({...s,buyers:Math.min(600,s.buyers+25)}).EVp>=r.EVp*(1-1e-6),"more buyers never lowers proceeds",ctx(s));

  /* 7. continuity: a 0.1% change in earnings, revenue or ask moves no output by more than 1% */
  for(const k of ["ern","rev","ask"]){ const r2=A.model({...s,[k]:s[k]*1.001});
    if(k==="ern"&&r2.inputs.ern>s.rev*.92) continue;
    for(const o of ["V","Vreal","Vmean","EVp","PC","tMed","tMean","cashShare"])
      ok(Math.abs(r2[o]/r[o]-1)<.01,`continuous: ${o} in ${k}`,ctx(s,{k,o,a:r[o],b:r2[o]})); }

  /* 7b. GM salary (the hire-a-GM cost): inside the industry's p10-p90 band, never falling with revenue */
  { const W=A.MODELS.fitted.gm_wage, g=W.by_industry[s.ind], gs=A.gmSalary(s), gs2=A.gmSalary({...s,rev:s.rev*1.5});
    ok(fin(gs)&&gs>=g.p10*W.wage_growth-1&&gs<=g.p90*W.wage_growth+1,"GM salary inside the BLS p10-p90",ctx(s,{gs}));
    ok(gs2>=gs*(1-1e-12),"GM salary non-decreasing in revenue",ctx(s,{gs,gs2})); }

  /* 7c. time-to-close curve: log-logistic pinned to the median, shape by size band (Vbase), never the ask */
  { const S=A.MODELS.fitted.ttc_shape, bmin=Math.min(...S.beta), bmax=Math.max(...S.beta);
    ok(Math.abs(r.F(r.tMed)-.5)<1e-12&&Math.abs(r.tQ(.5)/r.tMed-1)<1e-9,"curve median exact",ctx(s,{tMed:r.tMed}));
    ok([.1,.25,.75,.9].every(p=>Math.abs(r.F(r.tQ(p))-p)<1e-9),"curve quantile inverts F",ctx(s));
    ok(r.betaT>=bmin-1e-12&&r.betaT<=bmax+1e-12&&r.betaT===A.fitTiming(r.Vbase,s.ind).beta,"curve shape from the size band",ctx(s,{b:r.betaT}));
    let prev=-1, cdf=r.F(0)===0;
    for(const t of [1,10,30,60,90,180,270,365,540,730,1095,2000,3000]){ const f=r.F(t); if(!(fin(f)&&f>=prev&&f<=1)) cdf=false; prev=f; }
    ok(cdf&&r.F(20*r.tMed)>.99,"curve a proper CDF",ctx(s));
    const ra=A.model({...s,ask:s.ask*1.7});
    ok(ra.betaT===r.betaT&&Math.abs(ra.F(ra.tMed)-.5)<1e-12,"curve shape independent of the ask",ctx(s));
    /* overpricing_time: a different ask only rescales the curve with the median, F_a(t) = F(t x tMult_a / tMult) */
    ok([90,180,365].every(t=>Math.abs(ra.F(t*ra.tMult/r.tMult)-r.F(t))<1e-12),"curve rescaled exactly with the median",ctx(s,{a:r.tMult,b:ra.tMult})); }

  /* 7d. survival risk (fit/sba_risk_refresh.py): charged off within 5 < 8 < 10 years, headline = 10-year term
     (8-year x tail factor), rel against base_cif.term, expected loss below the probability; it reads the value,
     not the ask, and ignores staffing; with no rate entered it prices at sbaRate(V) */
  { const k=r.risk, R=A.MODELS.risk;
    ok([k.p5,k.p8,k.pTerm,k.rel,k.lgd,k.expLoss].every(fin)&&k.p5>0&&k.p5<k.p8&&k.p8<k.pTerm&&k.pTerm<.5,"risk horizons ordered",ctx(s,{p5:k.p5,p8:k.p8,p:k.pTerm}));
    ok(k.p===k.pTerm&&Math.abs(k.pTerm-k.p8*R.tail_factor)<1e-12&&Math.abs(k.rel-k.pTerm/R.base_cif.term)<1e-12,"risk headline is the 10-year term",ctx(s));
    ok(k.expLoss>0&&k.expLoss<k.pTerm&&k.lgd>.4&&k.lgd<.95,"expected loss below the charge-off probability",ctx(s,{lgd:k.lgd}));
    ok(A.model({...s,ask:s.ask*1.7}).risk.p===k.p,"risk independent of the ask",ctx(s));
    ok(A.model({...s,jobs:s.jobs*7+3}).risk.p===k.p,"risk ignores staffing",ctx(s));
    const rt=A.model({...s,rate:undefined});
    ok(rt.rate===A.sbaRate(rt.V)&&rt.risk.p===A.fitRisk(rt.V,s.ind,A.sbaRate(rt.V),null,!!s.franchise,s.st||null).p,"no rate entered prices at the table rate",ctx(s)); }

  /* 7e. realised-price fan (fit/anchoring_realization.py): the closing probability never reads the price block
     (P_C = fitClose x thin-pool factor), the expected price rises with the ask while its share of the ask falls,
     and the narrowed fan keeps the uncapped centre at V x A(rho) x (1+comp) */
  { const fp=A.fitClose(s.ask,r.V,s.chan,r.Vbase).p;
    ok(Math.abs(r.PC-(r.thinF<1?Math.min(.95,Math.max(0,fp*r.thinF)):fp))<1e-9,"P_C independent of the price block",ctx(s,{PC:r.PC,fp}));
    ok(r.fanS===.80&&Math.abs(r.VrealFree/(r.V*r.anchorF*(1+r.compPrem))-1)<.01,"narrowed fan keeps the centre",ctx(s));
    const rh=A.model({...s,ask:s.ask*1.05});
    ok(rh.Vmean>=r.Vmean*(1-1e-9),"E[P|close] non-decreasing in the ask",ctx(s,{a:r.Vmean,b:rh.Vmean}));
    ok(rh.Vmean/rh.inputs.ask<=r.Vmean/r.inputs.ask*(1+1e-9),"E[P|close]/ask non-increasing in the ask",ctx(s)); }

  /* 7f. overpricing costs time (fit/overpricing_time.py; T_ELAST a labelled judgment): the band median is exact at
     or below model value, stretched by timeMult above it; band, LOI leg and shape never read the ask; a longer ask
     never shortens the time to close or raises the share closed by day 180; a better business is never slower at a
     fixed ask; the price block (P_C, prices, value) does not read the multiplier */
  { const fT=A.fitTiming(r.Vbase,s.ind), Vv=r.V;
    ok(r.ft.days===fT.days&&r.ft.loi===fT.loi&&r.tMed===fT.days*r.tMult,"tMed = band median x timeMult",ctx(s,{tMult:r.tMult}));
    ok(s.ask>Vv?r.tMult>1-1e-15:r.tMult===1,"timeMult exactly 1 at or below value, at least 1 above",ctx(s,{rho:s.ask/Vv,tMult:r.tMult}));
    const rl=A.model({...s,ask:Vv*.97}); ok(rl.tMed===A.fitTiming(rl.Vbase,s.ind).days,"band median exact below value",ctx(s));
    const rh=A.model({...s,ask:s.ask*1.25});
    ok(rh.ft.days===r.ft.days&&rh.ft.loi===r.ft.loi&&rh.betaT===r.betaT,"band, LOI leg and shape independent of the ask",ctx(s));
    ok(rh.tMed>=r.tMed*(1-1e-12)&&rh.t180<=r.t180+1e-12,"higher ask never faster",ctx(s,{a:r.tMed,b:rh.tMed}));
    if(s.ask>Vv*1.2){ const rq=A.model({...s,rec:Math.min(1,s.rec+.1),mgt:Math.min(.99,s.mgt+.1)});
      if(rq.Vbase===r.Vbase&&rq.V>=r.V) ok(rq.tMed<=r.tMed+1e-9,"better business never slower at a fixed ask",ctx(s)); } }

  /* 7g. competition (fit/competition_buyers.py): ENG_SHARE sets the expected offers, the thin-pool factor is the
     Poisson ratio under a smooth cap (0 < thinF <= 1, exactly 1 from the typical pool up, non-decreasing in the pool,
     no quality input), the premium is the pre-change formula, and more buyers never lower P_C or expected proceeds */
  { const I=A.IND[s.ind], X=r.nEng/A.ENG_SHARE, Xr=r.nEngRef/A.ENG_SHARE;
    ok(Math.abs(r.compPrem-Math.min(.14,Math.max(-.08,.030*Math.log((3+X*.34)/(3+Xr*.34)))))<1e-12,"premium equals the pre-change formula",ctx(s,{c:r.compPrem}));
    ok(r.thinF>0&&r.thinF<=1&&(s.buyers>=I.buyers?r.thinF===1:true),"thinF in (0,1], exactly 1 from a typical pool",ctx(s,{thinF:r.thinF}));
    const raw=(1-Math.exp(-r.nPool))/Math.max(1e-9,1-Math.exp(-r.nEngRef));
    ok(r.thinF>=Math.min(1,raw)-1e-15&&r.thinF<=Math.min(1,raw)+.014,"thinF within the cap's lift of the Poisson ratio",ctx(s,{thinF:r.thinF,raw}));
    const rq=A.model({...s,own:1-s.own,mgt:1-s.mgt,rec:1-s.rec});
    /* to rounding: peRef sums the buyers in EV order, which quality changes */
    ok(Math.abs(rq.thinF-r.thinF)<1e-12&&Math.abs(rq.nEngRef/r.nEngRef-1)<1e-12,"thin-pool factor and typical pool read no quality input",ctx(s,{a:r.thinF,b:rq.thinF}));
    let pv=null, mono=true, ref=true;
    for(const b of [5,8,12,18,25,35,50,70,100,150,220,330,480,600]){ const rb=A.model({...s,buyers:b});
      if(pv&&(rb.EVp<pv.EVp*(1-1e-9)||rb.PC<pv.PC-1e-12||rb.thinF<pv.thinF-1e-15)) mono=false;
      if(Math.abs(rb.nEngRef-r.nEngRef)>1e-12*Math.max(1,r.nEngRef)) ref=false; pv=rb; }
    ok(mono,"more buyers never lower P_C, thinF or expected proceeds",ctx(s));
    ok(ref,"typical pool independent of the buyers contacted",ctx(s)); }
  /* 7h. quality composite (fit/quality_weights.py, quality_weights_v2.py: metadata only): qz is the weighted sum of the
     signed z-scores over the weights' norm (own, cc and plt count against), judgment dimensions weigh 1, fitted ones
     their stored weight, and the composite moves by exactly sign*w/norm per unit of z */
  { let q=0; const Wq=A.MODELS.fitted.quality_weights;
    for(const k of A.MODELS.value.quality_band.dimensions) q+=A.QW.w[k]*((k==="own"||k==="cc"||k==="plt")?-r.z[k]:r.z[k]);
    ok(Math.abs(r.qz-q/A.QW.norm)<1e-12*Math.max(1,Math.abs(q)),"qz = signed weighted z over the norm",ctx(s,{qz:r.qz,q:q/A.QW.norm}));
    ok(Wq.judgment.every(k=>A.QW.w[k]===1)&&Wq.fitted.every(k=>A.QW.w[k]===Wq[k]),"QW reads only the fitted weights",ctx(s));
    const rg=A.model({...s,grw:s.grw+.013});
    ok(Math.abs((rg.qz-r.qz)-(rg.z.grw-r.z.grw)*A.QW.w.grw/A.QW.norm)<1e-12,"growth moves qz by w/norm per unit of z",ctx(s,{d:rg.qz-r.qz})); }

  /* 7i. mean time to close (the delay cost's expectation, AUDIT_FINDINGS #6/#13/#19): the closed-form log-logistic
     mean, above the median by a factor that depends only on the size band's shape (never on the ask or quality),
     non-decreasing in the ask; on a subsample it matches the integral of S(t) */
  { const k=(Math.PI/r.betaT)/Math.sin(Math.PI/r.betaT);
    ok(r.betaT>1&&Math.abs(r.tMean/(r.tMed*k)-1)<1e-12&&r.tMean>r.tMed,"tMean = t_med (pi/beta)/sin(pi/beta) > t_med",ctx(s,{tMean:r.tMean,tMed:r.tMed}));
    const ra=A.model({...s,ask:s.ask*1.3}), rq=A.model({...s,own:1-s.own,fin:1-s.fin});
    ok(Math.abs(ra.tMean/ra.tMed-r.tMean/r.tMed)<1e-12,"mean/median ratio independent of the ask",ctx(s));
    if(rq.Vbase===r.Vbase) ok(Math.abs(rq.tMean/rq.tMed-r.tMean/r.tMed)<1e-12,"mean/median ratio reads no quality input",ctx(s));
    ok(ra.tMean>=r.tMean*(1-1e-12),"higher ask never lowers the mean time to close",ctx(s,{a:r.tMean,b:ra.tMean}));
    if(i%25===0){ let S=0; const h=r.tMed/400; for(let t=h/2;t<r.tMed*4e4;t+=h*Math.max(1,t/r.tMed)) S+=(1-r.F(t))*h*Math.max(1,t/r.tMed);
      ok(Math.abs(S/r.tMean-1)<.01,"tMean matches the integral of S(t)",ctx(s,{S,tMean:r.tMean})); } }

  /* 7j. closing probability: never rises with the ask, and keeps falling far above value (no 2% floor freezing the
     probability, proceeds and score from about 28x value, AUDIT_FINDINGS #5); P_C x E[P|close] = expected proceeds at
     every ask; each buyer's closing probability is the deal's, scaled, and its expected value is P_E x P_C x V */
  { let prev=null, mono=true, cons=true;
    for(const m of [.5,1,1.1,1.5,2,3,5,10,30,100]){ const x=A.model({...s,ask:V0*m});
      if(prev&&x.PC>prev.PC+1e-15) mono=false; if(Math.abs(x.EVp-x.PC*x.Vmean)>1e-9*Math.max(1,x.EVp)) cons=false; prev=x; }
    ok(mono,"P_C non-increasing in the ask",ctx(s)); ok(cons,"EVp = P_C x E[P|close] at every ask",ctx(s));
    const r30=A.model({...s,ask:V0*30}), r60=A.model({...s,ask:V0*60});
    ok(r30.PC===0||r60.PC<r30.PC,"no floor: P_C still falls between 30x and 60x value",ctx(s,{a:r30.PC,b:r60.PC}));
    ok(r.buyers.every(b=>b.PCj>=0&&b.PCj<=.95&&Math.abs(b.EV-b.PE*b.PCj*b.Vj)<1e-9*Math.max(1,b.EV)),"buyer EV = P_E x P_C,j x V_j",ctx(s)); }

  /* 7k. SBA note rate (fit/sba_risk_refresh.py): prime plus a spread that never rises with the loan size, inside the
     fitted knots, continuous; the charge-off risk never falls as the rate rises and is continuous in earnings */
  { const F=A.MODELS.fitted.sba_rate, sp=F.spread_knots.map(k=>k[1]), rt=A.sbaRate(r.V), rt2=A.sbaRate(r.V*1.5);
    ok(rt>=F.prime+Math.min(...sp)-1e-12&&rt<=F.prime+Math.max(...sp)+1e-12,"SBA rate inside prime + fitted spreads",ctx(s,{rt}));
    ok(rt2<=rt+1e-12,"SBA rate non-increasing in the loan size",ctx(s,{rt,rt2}));
    ok(Math.abs(A.sbaRate(r.V*1.001)-rt)<.01,"SBA rate continuous",ctx(s));
    const pa=A.model({...s,rate:9}).risk.p, pb=A.model({...s,rate:11}).risk.p;
    ok(pb>=pa*(1-1e-12),"risk non-decreasing in the note rate",ctx(s,{pa,pb}));
    if(s.ern*1.001<=s.rev*.92){ const p2=A.model({...s,ern:s.ern*1.001}).risk.p; ok(Math.abs(p2/r.risk.p-1)<.01,"risk continuous in earnings",ctx(s,{a:r.risk.p,b:p2})); } }

  /* 7l. intervention table (AUDIT_FINDINGS #3/#12/#17): the reprice equalises the gap but not P_C. Outreach never
     lowers P_C, raises it below a typical pool (thin-pool factor), and leaves it exactly unchanged from a typical pool */
  if(i%5===0){ const rr=r, ss={...s,rhoSell:A.bestRatio(s,0,0)}, it=A.interventionTable(ss,rr), o=it.find(x=>x.k==="outreach");
    if(o){ const typ=A.IND[s.ind].buyers||50, base=A.model(A.applyAll(ss,rr,["reprice"]));
      ok(o.dP>=-1e-12,"outreach never lowers P_C",ctx(s,{dP:o.dP}));
      if(s.buyers>=typ) ok(Math.abs(o.dP)<1e-12,"outreach leaves P_C unchanged from a typical pool",ctx(s,{dP:o.dP}));
      else if(base.PC>1e-9&&base.thinF<.98) ok(o.dP>0,"outreach raises P_C below a typical pool",ctx(s,{dP:o.dP,thinF:base.thinF})); } }

  /* 7m. business score (AUDIT_FINDINGS #9): priced at the optimal ask AND at least a typical pool, so it never reads
     how many buyers were contacted below the typical pool, never falls as the pool deepens, and stays at or above both
     the Omni score and the score at the optimal ask on this pool */
  if(i%10===0){ const typ=A.IND[s.ind].buyers||50, rs=A.bestRatio(s,0,0), bs=A.businessScore(s,r,rs);
    const sA=A.omniScore(A.model({...s,ask:V0*rs}));
    ok(bs.score>=sc&&bs.score>=sA,"business score at or above the Omni score and the score at the optimal ask",ctx(s,{biz:bs.score,sc,sA}));
    if(s.buyers<typ){ const t={...s,buyers:Math.max(5,Math.floor(s.buyers/2))}, rt=A.model(t), bt=A.businessScore(t,rt,A.bestRatio(t,0,0));
      ok(Math.abs(bt.rq.EVp/bs.rq.EVp-1)<1e-12,"business score reads no pool below the typical one",ctx(s,{a:bs.rq.EVp,b:bt.rq.EVp}));
      ok(bt.score<=bs.score,"business score never falls as the pool deepens",ctx(s,{a:bt.score,b:bs.score})); } }

  /* 7n. the two optimiser texts describe the numbers they sit beside (AUDIT_FINDINGS #11/#14/#15/#18). optNote's lower
     branch prints the time value and the net separately, and the net decomposes into them; the second card's subtitle
     names only differences that move, in the direction they move */
  if(i%10===0&&s.lamT>0){ const t={...s,rhoSell:A.bestRatio(s,0,0)}; t.optRho=A.bestRatio(s,s.theta,s.lamT);
    const rS=A.model({...t,ask:V0*t.rhoSell}), rK=A.model({...t,ask:V0*t.optRho}), n=A.optNote(t,V0,rS,rK);
    if(n.kind==="lower"){ const tv=s.lamT*Math.max(0,rS.tMean-rK.tMean), U=x=>x.EVp+(1-x.PC)*s.theta*x.V-s.lamT*x.tMean;
      ok(n.text.includes("worth "+A.money(tv)+" at ")&&n.text.includes("that is worth "+A.money(n.gain)),"lower note prints the time value and the net",ctx(s,{text:n.text}));
      ok(Math.abs((U(rK)-U(rS))-(tv-(rS.EVp-rK.EVp)-s.theta*V0*(rK.PC-rS.PC)))<1e-6*V0,"net = time value - proceeds given up - value kept lost",ctx(s)); } }
  if(i%50===0){ const t={...s,rhoSell:A.bestRatio(s,0,0)}; t.optRho=A.bestRatio(s,s.theta,s.lamT);
    const rr=A.model(t), best=A.optimize(t,rr,t.budget,t.lamT,t.theta), uRho=best.U.keys.includes("reprice")?t.optRho:t.rhoSell;
    const c=A.optCardNote(t,best,t.rhoSell,uRho), dC=best.U.c-best.V.c, dT=(best.U.t+best.U.days)-(best.V.t+best.V.days);
    const sameK=JSON.stringify(best.V.keys.slice().sort())===JSON.stringify(best.U.keys.slice().sort());
    ok(!/NaN|undefined|Infinity|[−-]\$/.test(c.text),"card subtitle has no NaN or negative money",ctx(s,{text:c.text}));
    ok((c.kind==="same")===(sameK&&(!best.U.keys.includes("reprice")||uRho.toFixed(2)===t.rhoSell.toFixed(2))),"card subtitle 'same' exactly when the programmes match",ctx(s,{text:c.text}));
    ok(!(/spends \S+ less/.test(c.text)&&dC>=0)&&!(/spends \S+ more/.test(c.text)&&dC<=0),"card subtitle spend direction",ctx(s,{text:c.text,dC}));
    ok(!(/less from start to close/.test(c.text)&&dT>0)&&!(/longer from start to close/.test(c.text)&&dT<0),"card subtitle time direction",ctx(s,{text:c.text,dT}));
    ok(!/less elapsed time and spend/.test(c.text),"card subtitle never asserts less time and spend unchecked",ctx(s)); }

  /* 8. the proceeds optimum beats the entered ask, and reads neither theta nor the cost of delay
     (overpricing_time: render prices the business score at bestRatio(s,0,0)); a cost of delay never raises
     the walk-away ask */
  if(i%5===0){ const rs=A.bestRatio(s,0,0), ro=A.model({...s,ask:V0*rs});
    ok(ro.EVp>=r.EVp*(1-1e-6),"proceeds optimum at least as good as the entered ask",ctx(s,{rs}));
    ok(Math.abs(A.bestRatio({...s,theta:.9},0,0)-rs)<1e-9,"proceeds optimum independent of theta",ctx(s));
    const ru=A.bestRatio(s,s.theta,s.lamT);
    ok(ru<=A.RHO_MAX+1e-9&&rs<=A.RHO_MAX+1e-9,"recommended asks stay where the closing data reach",ctx(s,{rs,ru}));
    if(s.lamT>0){ const u0=A.bestRatio(s,s.theta,0), U=m=>{ const x=A.model({...s,ask:V0*m}); return x.EVp+(1-x.PC)*s.theta*x.V-s.lamT*x.tMean; };
      ok(U(ru)>=U(u0)-1e-6*Math.abs(U(u0)),"walk-away ask optimal on the delay-inclusive objective",ctx(s,{ru,u0})); } }

  /* 9. the walk-away ask can jump between two peaks of its objective as the share kept moves one 1% step (the slider's
     step). Wherever bestRatio jumps by more than 0.1 between adjacent steps, the note under the listing cards must show
     the range (or, at the cap, how flat the top is) on BOTH sides, so the jump is never silent. Theta is scanned in 5%
     steps and every 1% step inside an interval that moved by more than 0.1 is checked. */
  if(i%10===0){ const rs=A.bestRatio(s,0,0), memo={}, br=k=>memo[k]!==undefined?memo[k]:(memo[k]=A.bestRatio(s,k/100,s.lamT));
    const note=k=>{ const t={...s,theta:k/100,rhoSell:rs,optRho:br(k)}; return A.optNote(t,V0,A.model({...t,ask:V0*rs}),A.model({...t,ask:V0*t.optRho})); };
    const shown=n=>!!n.alt||(n.flat!==null&&n.flat!==undefined);
    for(let c=0;c<100;c+=5) if(Math.abs(br(c+5)-br(c))>.1) for(let k=c;k<c+5;k++) if(Math.abs(br(k+1)-br(k))>.1)
      ok(shown(note(k))&&shown(note(k+1)),"a walk-away jump between 1% steps of theta shows the range on both sides",ctx(s,{theta:k/100,from:br(k),to:br(k+1)})); }
}

const names=Object.keys(fails);
for(const n of names) console.log(`FAIL ${n}: ${fails[n].length} cases, e.g. ${fails[n][0]}`);
console.log(`${N} random businesses, ${checks} checks, ${names.length?names.reduce((a,n)=>a+fails[n].length,0)+" failed":"all passed"}`);
process.exit(names.length?1:0);
