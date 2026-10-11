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
  ok([r.V,r.Vreal,r.Vmean,r.EVp,r.PC,r.tMed,r.risk.p,r.cashShare,r.M].every(fin),"finite",ctx(s));
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
    for(const o of ["V","Vreal","Vmean","EVp","PC","tMed","cashShare"])
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
    if(r.tMult===undefined) ok(ra.F(180)===r.F(180)&&ra.F(365)===r.F(365),"curve independent of the ask",ctx(s)); }

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

  /* 8. the proceeds optimum beats the entered ask, and does not depend on theta */
  if(i%5===0){ const rs=A.bestRatio(s,0,s.lamT), ro=A.model({...s,ask:V0*rs});
    ok(ro.EVp>=r.EVp*(1-1e-6),"proceeds optimum at least as good as the entered ask",ctx(s,{rs}));
    ok(Math.abs(A.bestRatio({...s,theta:.9},0,s.lamT)-rs)<1e-9,"proceeds optimum independent of theta",ctx(s));
    const ru=A.bestRatio(s,s.theta,s.lamT);
    ok(ru<=A.RHO_MAX+1e-9&&rs<=A.RHO_MAX+1e-9,"recommended asks stay where the closing data reach",ctx(s,{rs,ru})); }
}

const names=Object.keys(fails);
for(const n of names) console.log(`FAIL ${n}: ${fails[n].length} cases, e.g. ${fails[n][0]}`);
console.log(`${N} random businesses, ${checks} checks, ${names.length?names.reduce((a,n)=>a+fails[n].length,0)+" failed":"all passed"}`);
process.exit(names.length?1:0);
