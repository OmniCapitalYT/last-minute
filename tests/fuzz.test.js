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
    grw:-.25+rnd()*.95, gm:.12+rnd()*.8, rec:rnd(), cc:.01+rnd()*.69, ret:.05+rnd()*.94, plt:.05+rnd()*.9,
    own:pick([.95,.72,.42,.14]), mgt:pick([.08,.36,.66,.92]), fin:pick([.14,.45,.74,.96]),
    yrs:1+Math.floor(rnd()*12), buyers:5+Math.floor(rnd()*596), budget:rnd()<.15?0:rev*.15*rnd(),
    lamT:Math.floor(rnd()*81)*50, theta:rnd(), rate:10.5};
  s.jobs=Math.max(2,Math.round(s.rev/150000));
  return s;
}
const fin=x=>typeof x==="number"&&isFinite(x);
/* the model with IBBA's published band medians instead of the fitted ones (7o) */
const PUB=A.loadWith([["const TM=MODELS.fitted.ttc_medians;","const TM=null;"]]);
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
     (8-year x the fitted tail at the note's size, fit/sba_tail_factor.py), rel against base_cif.term, expected loss
     below the probability; it reads the value,
     not the ask, and ignores staffing; with no rate entered it prices at sbaRate(V) */
  { const k=r.risk, R=A.MODELS.risk;
    ok([k.p5,k.p8,k.pTerm,k.rel,k.lgd,k.expLoss].every(fin)&&k.p5>0&&k.p5<k.p8&&k.p8<k.pTerm&&k.pTerm<.5,"risk horizons ordered",ctx(s,{p5:k.p5,p8:k.p8,p:k.pTerm}));
    ok(k.p===k.pTerm&&Math.abs(k.pTerm-k.p8*k.tail)<1e-12&&k.tail===A.tailAt(k.loan)&&Math.abs(k.rel-k.pTerm/R.base_cif.term)<1e-12,"risk headline is the 10-year term",ctx(s));
    { const B=R.tail.by_band, lo=Math.min(...B.ratio)*B.scale, hi=Math.max(...B.ratio)*B.scale;
      ok(k.tail>=lo-1e-12&&k.tail<=hi+1e-12,"tail inside its band table",ctx(s,{tail:k.tail})); }
    ok(k.expLoss>0&&k.expLoss<k.pTerm&&k.lgd>.4&&k.lgd<.95,"expected loss below the charge-off probability",ctx(s,{lgd:k.lgd}));
    ok(A.model({...s,ask:s.ask*1.7}).risk.p===k.p,"risk independent of the ask",ctx(s));
    ok(A.model({...s,jobs:s.jobs*7+3}).risk.p===k.p,"risk ignores staffing",ctx(s));
    const rt=A.model({...s,rate:undefined});
    ok(rt.rate===A.sbaRate(rt.V)&&rt.risk.p===A.fitRisk(rt.V,s.ind,A.sbaRate(rt.V),null,!!s.franchise,s.st||null).p,"no rate entered prices at the table rate",ctx(s)); }

  /* 7d2. analysis confidence (fit/confidence_accuracy.py): the fitted chance of landing within 25% of the fitted value;
     the label follows the quartile cut-offs, Low outside the fitted data; it reads neither the ask, the years of history
     nor reporting */
  { const C=A.MODELS.fitted.confidence, c=A.confidenceOf(s,r);
    ok(fin(r.conf)&&r.conf>0&&r.conf<1&&r.conf===c.p&&r.confLabel===c.label,"confidence is confidenceOf, inside (0,1)",ctx(s,{conf:r.conf}));
    ok(r.confLabel===(r.confOutside?"Low":r.conf>=C.cut_high?"High":r.conf>=C.cut_moderate?"Moderate":"Low"),"confidence label follows its cut-offs",ctx(s,{conf:r.conf,l:r.confLabel}));
    ok(r.confOutside===(r.extrapMax>C.extrap_x||s.ern/s.rev<A.MODELS.value.support.margin.p1||s.ern/s.rev>A.MODELS.value.support.margin.p99),"outside the fitted data exactly past 3x or with the margin outside",ctx(s));
    if(i%4===0){ const ry=A.model({...s,yrs:s.yrs+3,fin:Math.min(1,s.fin+.1),ask:s.ask*1.3});
      ok(ry.conf===r.conf,"confidence reads neither the years, reporting nor the ask",ctx(s)); } }

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
    ok(r.buyers.every(b=>b.PCj>=0&&b.PCj<=.95&&Math.abs(b.EV-b.PE*b.PCj*b.Pj)<1e-9*Math.max(1,b.EV)),"buyer EV = P_E x P_C,j x price_j",ctx(s));
    /* AUDIT_FINDINGS R1-4/R1-5: a buyer is paid at most what this listing can realise (its own value, under the ask
       ceiling) and closes on the gap to its OWN value: the same close rate as the deal's base x penalty read at V_j */
    ok(r.buyers.every(b=>b.Pj<=Math.min(b.Vj,r.ceil)*(1+1e-9)&&b.Pj>0),"buyer price never above its value or the ask ceiling",ctx(s));
    ok(r.buyers.every(b=>Math.abs(b.PCj-Math.min(.95,Math.max(0,A.fitClose(s.ask,b.Vj,s.chan,r.Vbase).p*r.thinF*(.8+.42*b.PE))))<1e-12),"buyer close rate reads the gap to its own value",ctx(s));
    { const rh=A.model({...s,ask:s.ask*1.1}); ok(r.buyers.every(b=>{ const h=rh.buyers.find(x=>x.k===b.k); return h.PCj<=b.PCj+1e-12; }),"no buyer closes more often at a higher ask",ctx(s)); } }

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
    ok(n.coin===(n.kind!=="same"&&n.gain<.01*V0),"coin-toss flag is the 1%-of-value rule",ctx(s,{gain:n.gain,V0}));
    if(n.kind==="lower"){ const tv=s.lamT*Math.max(0,rS.tMean-rK.tMean), U=x=>x.EVp+(1-x.PC)*s.theta*x.V-s.lamT*x.tMean;
      ok(n.text.includes("worth "+A.money(tv)+" at ")&&n.text.includes("that is worth "+A.money(n.gain)),"lower note prints the time value and the net",ctx(s,{text:n.text}));
      ok(Math.abs((U(rK)-U(rS))-(tv-(rS.EVp-rK.EVp)-s.theta*V0*(rK.PC-rS.PC)))<1e-6*V0,"net = time value - proceeds given up - value kept lost",ctx(s)); } }
  if(i%50===0){ const t={...s,rhoSell:A.bestRatio(s,0,0)}; t.optRho=A.bestRatio(s,s.theta,s.lamT);
    const rr=A.model(t), best=A.optimize(t,rr,t.budget,t.lamT,t.theta), uRho=best.U.keys.includes("reprice")?t.optRho:t.rhoSell;
    /* AUDIT_FINDINGS R2-2: neither programme keeps an ask above RHO_MAX x its own value */
    ok(["V","U"].every(k=>best[k].keys.includes("reprice")||t.ask<=A.RHO_MAX*best[k].r.V*(1+1e-9)),"optimiser never keeps an over-cap ask",ctx(s));
    const c=A.optCardNote(t,best,t.rhoSell,uRho), dC=best.U.c-best.V.c, dT=(best.U.t+best.U.days)-(best.V.t+best.V.days);
    const sameK=JSON.stringify(best.V.keys.slice().sort())===JSON.stringify(best.U.keys.slice().sort());
    ok(!/NaN|undefined|Infinity|[−-]\$/.test(c.text),"card subtitle has no NaN or negative money",ctx(s,{text:c.text}));
    ok((c.kind==="same")===(sameK&&(!best.U.keys.includes("reprice")||uRho.toFixed(2)===t.rhoSell.toFixed(2))),"card subtitle 'same' exactly when the programmes match",ctx(s,{text:c.text}));
    ok(!(/spends \S+ less/.test(c.text)&&dC>=0)&&!(/spends \S+ more/.test(c.text)&&dC<=0),"card subtitle spend direction",ctx(s,{text:c.text,dC}));
    ok(!(/less from start to close/.test(c.text)&&dT>0)&&!(/longer from start to close/.test(c.text)&&dT<0),"card subtitle time direction",ctx(s,{text:c.text,dT}));
    ok(!/less elapsed time and spend/.test(c.text),"card subtitle never asserts less time and spend unchecked",ctx(s));
    /* AUDIT_FINDINGS R1-10: every term named after "pays only through" really adds to U; one named after "while" works against it */
    { const ret=x=>(1-x.PC)*t.theta*x.r.V, dRet=ret(best.U)-ret(best.V), dDel=-t.lamT*dT;
      const m=c.text.match(/pays only through (.*?)(, while (.*))?\.$/), named=m?m[1]:"", against=m&&m[3]?m[3]:"";
      ok(!(named.includes("value retained")&&dRet<=0)&&!(named.includes("cost of delay")&&dDel<=0)
         &&!(against.includes("value retained")&&dRet>=0)&&!(against.includes("cost of delay")&&dDel>=0),"card subtitle names each term in its true direction",ctx(s,{text:c.text,dRet,dDel})); } }

  /* 7o. band medians fitted to the IBBA histograms (fit/time_to_close_medians.py): the median reads deal size (Vbase)
     alone, rises with it, has no jump at the band knots, sits between its neighbouring fitted medians, and is exactly
     the curve's median at a fair ask. Swapping the published medians back in moves only the time outputs: value,
     prices, P_C and risk are untouched */
  { const TM=A.MODELS.fitted.ttc_medians, ft=A.fitTiming(r.Vbase,s.ind), lo=Math.min(...TM.listing), hi=Math.max(...TM.listing);
    ok(ft.months>=lo-1e-12&&ft.months<=hi+1e-12&&Math.abs(ft.days-ft.months*30.44)<1e-9,"fitted median inside the fitted band range",ctx(s,{m:ft.months}));
    ok(A.fitTiming(r.Vbase,pick(INDS)).months===ft.months,"fitted median reads no industry",ctx(s));
    ok(A.fitTiming(r.Vbase*1.07,s.ind).months>=ft.months-1e-12,"fitted median never falls with deal size",ctx(s));
    ok(Math.abs(A.fitTiming(r.Vbase*(1+1e-7),s.ind).months-ft.months)<1e-5,"fitted median continuous in deal size",ctx(s));
    const rf=A.model({...s,ask:Math.min(r.V,r.Vbase)*.8});
    ok(rf.tMult===1&&Math.abs(rf.tMed-A.fitTiming(rf.Vbase,s.ind).days)<1e-9,"at a fair ask the median is the fitted band median",ctx(s,{tMed:rf.tMed}));
    const rq=A.model({...s,own:1-s.own,fin:1-s.fin,mgt:1-s.mgt,ask:Math.min(r.V,r.Vbase)*.8}), rq0=A.model({...s,ask:Math.min(r.V,r.Vbase)*.8});
    if(rq.Vbase===rq0.Vbase&&rq.tMult===1&&rq0.tMult===1) ok(rq.tMed===rq0.tMed,"fitted median reads no quality input at a fair ask",ctx(s));
    if(i%3===0){ const rp=PUB.model(s);
      ok(rp.V===r.V&&rp.Vmean===r.Vmean&&rp.PC===r.PC&&rp.EVp===r.EVp&&rp.risk.p===r.risk.p&&rp.risk.expLoss===r.risk.expLoss&&rp.betaT===r.betaT,"medians move only the time outputs",ctx(s,{dPC:rp.PC-r.PC}));
      ok(Math.abs(rp.tMed/r.tMed-PUB.fitTiming(r.Vbase,s.ind).months/ft.months)<1e-9,"published and fitted curves differ only by the median",ctx(s)); } }

  /* 7p. past RHO_MAX x value the ask stops moving the price (AUDIT_FINDINGS R2-2): the effective ask saturates (fully by
     2x value: the soft minimum's 0.012 log-width), so the price if it closes, the median price and the ceiling are flat,
     while the closing probability keeps falling */
  if(rho>2){ const rb=A.model({...s,ask:s.ask*1.4});
    ok(Math.abs(rb.Vmean/r.Vmean-1)<1e-9&&Math.abs(rb.Vreal/r.Vreal-1)<1e-9&&Math.abs(rb.ceil/r.ceil-1)<1e-9,"price flat past the cap",ctx(s,{a:r.Vmean,b:rb.Vmean}));
    ok(rb.PC<=r.PC+1e-12,"closing probability still falls past the cap",ctx(s)); }
  if(rho<1.2) ok(Math.abs(r.askEff/s.ask-1)<1e-9,"below 1.2x the effective ask is the ask to 1e-9",ctx(s,{e:r.askEff}));

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
  /* 10. the broker tools, on the same random businesses (AUDIT.md, "Broker tools"): the financing check's identities and
     monotonicity, the highest financeable price, coverage as printed, the worksheet's arithmetic, a deal's prediction and
     the report's figures */
  { const V=r.V, f={type:pick(["initial","expansion","buyout"]),cash:pick([0,.05,.1,.2,.5,.9]),note:pick([0,.05,.1,.3]),noteRate:pick([0,4,6,9]),
      noteYears:pick([1,5,10,25]),standby:rnd()<.3,extra:rnd()<.5?0:V*.2*rnd(),capex:rnd()<.5?0:s.ern*.3*rnd(),draw:rnd()<.5?null:s.ern*rnd()};
    const p=s.ask, c=A.debtCheck(s,p,f,V), S=A.SBA_COO, share=1-f.cash-f.note;
    ok([c.loan,c.cash,c.note,c.ds,c.cf,c.rate,c.draw,c.equityNeed,c.equityIn,c.debt].every(fin)&&(fin(c.dscr)||c.dscr===Infinity),"broker: debt check finite",ctx(s,f));
    ok(Math.abs(c.loan+c.cash+c.note-c.project)<=1e-6*c.project+1e-6&&c.loan<=S.maxLoan&&c.loan>=0&&c.over>=0&&c.note<=f.note*p+1e-6
       &&c.cash>=Math.max(0,f.cash)*c.project*(1-1e-9)&&c.noteCut===(c.note<f.note*p-1e-6),"broker: the loan, cash and note make up the project, the loan within the 7(a) cap, the note cut only to fit",ctx(s,f));
    ok(Math.abs(c.ds-c.sbaPay-c.notePay)<1e-6&&(c.ds>0?Math.abs(c.dscr-c.cf/c.ds)<1e-9*Math.max(1,Math.abs(c.dscr)):c.dscr===Infinity)
       &&Math.abs(c.cf-(s.ern-c.draw-c.capex))<1e-6&&(f.draw!==null||Math.abs(c.draw-A.gmSalary(s)*A.IVC.gm.loading)<1e-6),"broker: coverage is cash available, after the loaded market pay, over the payments",ctx(s,f));
    ok(!f.standby||c.loan===0||(c.notePay===0&&c.debt===c.loan&&c.equityIn<=c.cash+S.standbyShare*c.equityNeed+1e-6),"broker: a standby note is no payment, no debt, at most half the equity",ctx(s,f));
    ok(!(c.loan===0&&c.note>0)||(!c.standby&&Math.abs(c.notePay-A.annualPayment(c.note,f.noteRate,f.noteYears))<1e-6),"broker: with no SBA loan a note is paid on its own terms, standby or not",ctx(s,f));
    ok(Math.abs(c.equityNeed-.1*(f.type==="buyout"?p:c.project))<1e-6&&c.min===S.dsc[f.type]&&c.ownValuation===(p<=S.ownValuationMax&&f.type!=="buyout"),"broker: equity, coverage floor and valuation rule by transaction type",ctx(s,f));
    ok(c.debtOverValue===(c.loan>0&&c.debt>V*(1+1e-9)),"broker: debt above value is flagged exactly when an SBA-financed structure's debt exceeds it",ctx(s,f));
    /* coverage as printed: rounded down, never the minimum it fails */
    { const t=A.covFmt(c), x=parseFloat(t);
      ok(!(c.ds>0)?/^no (payments|debt)$/.test(t):!(c.cf>0)?t==="none":(/^\d+\.\d\d×$/.test(t)&&x<=c.dscr+1e-9&&(c.ok?x>=c.min-1e-9:x<c.min-1e-9)),"broker: coverage prints rounded down, below the minimum when it fails",ctx(s,f,{t})); }
    /* coverage never rises with the price below the cap, for shares that leave the loan to the price */
    if(share>=0){ let prev=Infinity, mono=true; for(let k=0;k<12;k++){ const q=p*Math.pow(1.35,k-6), d=A.debtCheck(s,q,f,V);
        if(d.over>0||!(d.cf>0)) break; if(d.dscr>prev*(1+1e-9)+1e-12) mono=false; prev=d.dscr; }
      ok(mono,"broker: coverage falls as the price rises",ctx(s,f)); }
    /* the highest financeable price: every price below it passes coverage and the valuation, the named test fails just above */
    const m=A.maxFinanced(s,f,V), t=S.dsc[f.type], pass=d=>d.dscr>=t&&!d.debtOverValue;
    if(m.noLoan) ok(m.price===Infinity&&!m.equityShort&&share<=1e-9&&(f.extra||0)*(1-f.cash)<1&&[1e4,p,1e9].every(q=>A.debtCheck(s,q,f,V).loan===0),"broker: no loan only when none is needed at any price",ctx(s,f));
    else if(m.price===0) ok(m.bind==="cap"?A.debtCheck(s,1e3,f,V).over>0:!pass(A.debtCheck(s,1e3,f,V)),"broker: no financeable price only when even $1,000 fails, or the working capital alone takes the 7(a) maximum",ctx(s,f));
    else if(m.price===Infinity) ok(m.capAt===null&&pass(A.debtCheck(s,1e11,f,V))&&pass(A.debtCheck(s,1e7,f,V)),"broker: no limit only when no loan grows with the price and the largest price passes",ctx(s,f));
    else { const a=A.debtCheck(s,m.price,f,V), b=A.debtCheck(s,m.price*(1+1e-9),f,V);
      ok(pass(a)&&a.over===0&&pass(A.debtCheck(s,m.price*.9,f,V))&&(m.bind==="coverage"?b.dscr<t:m.bind==="value"?b.debtOverValue:b.over>0)&&m.equityShort===!a.equityOK
         &&(m.bind!=="value"||m.covPrice>=m.price*(1-1e-9)),"broker: the highest financeable price passes both tests within the 7(a) maximum, and the named limit binds just above",ctx(s,f,{mp:m.price,bind:m.bind})); }
    /* equity across the prices below the one found: a named edge is where it turns, and an initial acquisition that shows
       a price either passes at every lower price or names its floor; the price shown, rounded down, never exceeds it */
    if(m.equityFrom) ok(!A.debtCheck(s,m.equityFrom*.995,f,V).equityOK&&A.debtCheck(s,m.equityFrom*1.0001,f,V).equityOK&&m.equityFrom<=Math.min(m.price,1e11)*(1+1e-9),"broker: equity passes from the edge named, not below it",ctx(s,f,{ef:m.equityFrom}));
    if(m.equityTo) ok(A.debtCheck(s,m.equityTo*.9999,f,V).equityOK&&!A.debtCheck(s,m.equityTo*1.005,f,V).equityOK,"broker: equity passes up to the edge named, not above it",ctx(s,f,{et:m.equityTo}));
    if(f.type==="initial"&&m.price>0&&!m.equityShort&&!m.noLoan) ok(A.debtCheck(s,1e3,f,V).equityOK||m.equityFrom>0,"broker: an initial acquisition's price stands only with its equity floor named",ctx(s,f));
    if(m.price>0&&isFinite(m.price)){ const t=A.moneyDown(m.price), u=t.slice(-1), x=parseFloat(t.replace(/[^0-9.]/g,""))*({B:1e9,M:1e6,k:1e3}[u]||1);
      const st={B:1e7,M:1e4,k:1e3}[A.money(m.price).slice(-1)]||1;
      ok(x<=m.price*(1+1e-12)&&m.price-x<st*(1+1e-9),"broker: the highest price is shown rounded down, by less than one unit of money's precision",ctx(s,f,{t,mp:m.price})); }
    if(!m.noLoan&&share>=.1&&f.cash<.85){ const more=A.maxFinanced(s,{...f,cash:f.cash+.1},V), cap=A.maxFinanced(s,{...f,capex:(f.capex||0)+s.ern*.05},V);
      ok(more.price>=m.price*(1-1e-9)&&cap.price<=m.price*(1+1e-9),"broker: more buyer cash finances more, capital spending less",ctx(s,f)); }
    /* the worksheet: linear in every line, expense lines add back their size, deductions always deduct, every basis inside the years' range */
    const yr=()=>({rev:s.rev*(.8+.4*rnd()),ni:s.ern*(rnd()-.2),owner:s.ern*.3*rnd(),ptax:s.ern*.02*(rnd()-.2),dep:s.ern*.1*(rnd()-.1),int:s.ern*.05*rnd(),
      tax:s.ern*.02*rnd(),once:s.ern*.1*rnd(),rent:s.ern*.03*(rnd()-.5),nonop:s.ern*.05*(rnd()-.5)});
    const ws={entity:pick(Object.keys(A.RECAST_ENTITY)),years:[yr(),rnd()<.7?yr():{},rnd()<.5?yr():{rev:s.rev*rnd()}]};
    const L=A.recastSDE({...ws,weight:"latest"}), y0=ws.years[0], ab=Math.abs;
    ok(Math.abs(L.sde-(y0.ni+ab(y0.owner)+ab(y0.ptax)+ab(y0.dep)+ab(y0.int)+ab(y0.tax)+y0.once+y0.rent-ab(y0.nonop)))<1e-6&&Math.abs(L.sde-(L.ni+L.add+L.less))<1e-6&&L.less<=0,
       "broker: SDE is income plus add-backs less deductions",ctx(s,{y0}));
    const bump=A.recastSDE({...ws,weight:"latest",years:[{...y0,perks:(y0.perks||0)+1000,xowner:5000},ws.years[1],ws.years[2]]});
    ok(Math.abs(bump.sde-L.sde-(1000-5000))<1e-6,"broker: each line moves SDE by its amount, a deduction down",ctx(s));
    const used=L.years.filter(y=>y.has), sdes=used.map(y=>y.sde);
    for(const w of ["w321","avg"]){ const R=A.recastSDE({...ws,weight:w}); ok(R.n===used.length&&R.sde>=Math.min(...sdes)-1e-6&&R.sde<=Math.max(...sdes)+1e-6,"broker: every basis lies within the years entered",ctx(s,{w})); }
    ok(L.years.every(y=>y.has||y.sde===y.ni+y.add+y.less)&&(!L.years[2].hasRev||L.years[2].has||L.flags.includes("rev_only")||L.flags.includes("rev_unused"))&&(L.discShare===null||L.discShare>=0)
       &&L.flags.every(k=>A.recastNotes(L).some(o=>o.k===k)||k==="sde_falling"&&!L.cmp),"broker: a year with revenue alone is flagged and left out; every flag has its note",ctx(s));
    /* a deal is predicted by the model at its listing price */
    const d=A.dealPredict({inputs:s,listPrice:p*1.1}), rl=A.model({...s,ask:p*1.1});
    ok(d.pc===rl.PC&&d.priceMed===rl.Vreal&&d.pExp===rl.Vmean&&d.tMed===rl.tMed&&d.pVar>=0&&d.tVar>0&&(d.F===null||(d.F>=0&&d.F<=1+1e-12)),"broker: a deal's prediction is the model at its listing price",ctx(s));
    { const x=[1+.3*(rnd()-.5),1+.3*(rnd()-.5),1+.3*(rnd()-.5)], Q=A.sampleSummary(x,false,d.pVar);
      ok(Q.lo<=Q.factor+1e-12&&Q.factor<=Q.hi+1e-12&&Math.min(1,Q.factor)-1e-12<=Q.shrunk&&Q.shrunk<=Math.max(1,Q.factor)+1e-12,"broker: a record's interval holds its factor, and the read toward the model lies between",ctx(s,{x})); }
    /* the report's figures are the model's at the optimizer's asks (every tenth business: it runs the optimizer) */
    if(i%10===0){ const D=A.reportData(s,{fin:f}), rs=A.bestRatio(s,0,0), mS=A.model({...s,ask:V*rs});
      ok(Math.abs(D.sell.ask/(V*rs)-1)<1e-12&&D.sell.pc===mS.PC&&D.sell.tMed===mS.tMed&&D.sell.ev===mS.EVp&&D.sell.mean===mS.Vmean&&D.cur.ask===s.ask
         &&D.cur.fin.dscr===A.debtCheck(s,s.ask,f,V).dscr&&D.maxFin.price===m.price,"broker: the report reads the model at the optimizer's asks",ctx(s,f));
      ok(D.sens.length<=3&&D.sens.every((g,j)=>g.gain>V*.001&&(j===0||D.sens[j-1].gain>=g.gain)&&g.keys.every(k=>A.RAIL_BEST[k]!==undefined&&(k==="own"||k==="cc"||k==="plt"?s[k]>A.RAIL_BEST[k]:s[k]<A.RAIL_BEST[k]))),
         "broker: the report names only levers with room left on the rail, largest first",ctx(s));
      /* each lever's gain is the model's own: one peer step toward its best, its best when nearer, or its best when the step
         moves the value by less than 0.1% (past the -3.2 z limit); never a central slope. A line groups only steps the model
         weights alike */
      { const SE=A.sensitivity(s), at=(k,kind)=>{ const v=SE.find(r=>r.k===k), best=A.RAIL_BEST[k], room=v.inv?s[k]-best:best-s[k], st=2*v.h, near=s[k]+(v.inv?-st:st);
          const okKind=kind==="step"?room>=st-1e-9:kind==="room"?room<st-1e-9:kind==="far"?room>=st-1e-9&&A.model({...s,[k]:near}).V-V<=V*.001:false;
          return {okKind,g:A.model({...s,[k]:kind==="step"?near:best}).V-V}; };
        ok(D.sens.every(g=>g.full===(g.kind==="step")&&g.keys.every(k=>{ const o=at(k,g.kind); return o.okKind&&Math.abs(o.g/g.gain-1)<.006; })),"broker: every lever's gain is the model's own step, room or best",ctx(s));
        ok(D.sens.every(g=>g.n===1||(g.kind==="step"&&g.keys.every(k=>A.QW.w[k]===A.QW.w[g.keys[0]]))),"broker: a lever line groups only steps the model weights alike",ctx(s)); }
      const h=A.reportHTML(D,{business:"<b>x</b>",broker:"y",firm:"z"});
      ok(!/NaN|undefined|Infinity|−\d\.\d\d×|-\d\.\d\d×/.test(h)&&!h.includes("<b>x</b>")&&h.includes(A.covFmt(D.cur.fin)),"broker: the report is finite, escapes what is typed and prints coverage as the console does",ctx(s,f));
      ok((Math.abs(D.qFactor-1)>.005)===/Model value <span class="rp-bx">/.test(h)&&(D.extrap.length>0)===/Extrapolated/.test(h),"broker: the report's value badge and extrapolation note follow the console's rules",ctx(s));
      /* SBA's minimum grades only the asks with an SBA loan; no claim that no price meets the equity minimum; the empty-lever
         text follows the business's place in the quality range; the quality step never reads "−0%" */
      { const showCur=Math.abs(D.cur.ask/D.sell.ask-1)>.005&&Math.abs(D.cur.ask/D.walk.ask-1)>.005, shown=[D.sell].concat(D.same?[]:[D.walk],showCur?[D.cur]:[]);
        const want=shown.filter(a=>a.fin.loan>0&&a.fin.ds>0&&!a.fin.ok).length, got=(h.match(/<span class="rp-warn">below \d\.\d\d×<\/span>/g)||[]).length;
        ok(want===got&&!/no price meets/.test(h)&&(!/at every price up to about/.test(h)||m.capped)&&!/[−+]0% for quality/.test(h)&&(f.note>0||!/standby note/.test(h))
           &&!(D.mfAt&&D.mfAt.equityIn<=0&&/waives part of/.test(h))
           &&(D.sens.length>0||(D.qPct<.5?/bottom of the quality range/:/already at its best/).test(h)),"broker: the report grades, bounds and words its lender and lever lines by what holds",ctx(s,f,{want,got})); } } }
}

const names=Object.keys(fails);
for(const n of names) console.log(`FAIL ${n}: ${fails[n].length} cases, e.g. ${fails[n][0]}`);
console.log(`${N} random businesses, ${checks} checks, ${names.length?names.reduce((a,n)=>a+fails[n].length,0)+" failed":"all passed"}`);
process.exit(names.length?1:0);
