/* Invariants of the Omni Method model. Run: node tests/model.test.js */
const A=require("./load.js");
let pass=0,fail=0;
const ok=(c,msg)=>{ if(c) pass++; else { fail++; console.log("FAIL:",msg); } };
const near=(a,b,tol)=>Math.abs(a-b)<=tol;

const EX={ind:"medical",rev:10**6.778,ern:10**6.161,ask:10**6.508,grw:.14,gm:.64,rec:.72,cc:.18,
  ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,
  budget:10**(4+2.778*.36),lamT:900,theta:.75,rate:10.5};
EX.jobs=Math.max(2,Math.round(EX.rev/150000));
const finiteDeep=(o,seen=new Set())=>{
  if(typeof o==="number") return isFinite(o);
  if(!o||typeof o!=="object"||seen.has(o)) return true; seen.add(o);
  return Object.values(o).every(v=>typeof v==="function"||finiteDeep(v,seen));
};
const median=(ind,ern)=>{
  const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/A.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,
    rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,
    gm:I.gm,ret:I.ret,fin:RF.fin,plt:.40};
};

/* 1. structure */
for(const k of Object.keys(A.IND)){
  ok(A.IND2NAICS[k]!==undefined,`industry ${k} has a NAICS sector`);
  ok(A.MODELS.risk.industry_effects[A.IND2NAICS[k]]!==undefined,`industry ${k} has a risk effect`);
}
{ const V=A.MODELS.value,co=V.coefficients;
  ok(near(co.ln_sde+co.ln_gross+co.hinge_sde*V.size_hinge.slope_beyond_cap,1,1e-4),
     "scale elasticity above the cap is exactly 1"); }

/* 2. degenerate inputs never produce NaN or Infinity */
for(const ind of Object.keys(A.IND)) for(const [ern,rev,ask] of
    [[1,1,1],[1e3,1e3,1],[1e9,1e9,1e9],[2e7,2e8,1e12],[5e4,5e4,5e4]]){
  const s={...EX,ind,ern,rev,ask,jobs:5};
  for(const q of ["rec","cc","own","mgt","fin","plt","ret","gm"]) for(const v of [0,1]){
    const r=A.model({...s,[q]:v});
    ok(isFinite(r.V)&&isFinite(r.Vreal)&&isFinite(r.EVp)&&isFinite(r.PC)&&isFinite(r.risk.p),
       `finite output ${ind} ern=${ern} ${q}=${v}`);
  }
}

/* 3. what a business supports cannot depend on what is asked */
for(const ask of [1e5,1e6,3e6,1e7,1e8])
  ok(near(A.model({...EX,ask}).V,A.model(EX).V,1e-6),`model value independent of ask=${ask}`);

/* 4. the realised price never exceeds the ask (beyond the IBBA band headroom) */
for(const ind of Object.keys(A.IND)) for(const rho of [.3,.6,.8,.95,1,1.05,1.2,2,4]){
  const V=A.model({...EX,ind,ask:1}).V, r=A.model({...EX,ind,ask:V*rho});
  ok(r.Vreal<=r.inputs.ask*r.askCeil*(1+1e-9)&&r.q(.99)<=r.inputs.ask*r.askCeil*(1+1e-9),`${ind} rho=${rho}: realised ${r.Vreal} above ask ceiling`);
}

/* 5. past the largest gap the data resolves, a higher ask never pays: expected
      proceeds peak below RHO_MAX and never rise again beyond it */
for(const ind of Object.keys(A.IND)) for(const ern of [1.5e5,6e5,1.5e6,5e6]){
  const b={...EX,ind,ern,rev:ern*4}, V=A.model({...b,ask:1}).V;
  let best=-Infinity,arg=0,prev=Infinity,bad=null;
  for(let rho=.5;rho<=4;rho+=.01){
    const e=A.model({...b,ask:V*rho}).EVp;
    if(e>best){best=e;arg=rho;}
    if(rho>=A.RHO_MAX*1.12){ if(e>prev+V*1e-6) bad=rho; prev=e; }
  }
  ok(arg<A.RHO_MAX,`${ind} ern=${ern}: proceeds peak at rho=${arg.toFixed(2)}, past the data`);
  ok(bad===null,`${ind} ern=${ern}: expected proceeds rise again at rho=${bad&&bad.toFixed(2)}`);
}

/* 6. a business on every peer median, priced at the reference ratio, scores 50 */
for(const ind of Object.keys(A.IND)) for(const ern of [1e5,3e5,1e6,3e6,1e7]){
  const t=median(ind,ern), V=A.model({...t,ask:1}).V;
  ok(A.omniScore(A.model({...t,ask:V*A.REF_RATIO}))===50,`median ${ind} ${ern} scores 50`);
}

/* 7. a typical buyer pool earns no competition premium */
for(const ind of Object.keys(A.IND)){
  const t=median(ind,1e6), r=A.model({...t,ask:1e6});
  ok(near(r.compPrem,0,1e-12),`${ind}: typical pool premium is zero`);
  ok(A.model({...t,ask:1e6,buyers:t.buyers*3}).compPrem>0,`${ind}: deeper pool earns a premium`);
  ok(A.model({...t,ask:1e6,buyers:5}).compPrem<0,`${ind}: thin pool costs a discount`);
}

/* 8. expected proceeds are P_C times the MEAN price, and the cap reaches the tails */
{ const r=A.model(EX);
  ok(near(r.EVp,r.PC*r.Vmean,1e-6),"EVp = P_C x mean price");
  for(const p of [.5,.8,.94,.99]) ok(r.q(p)<=r.inputs.ask*r.askCeil*(1+1e-9),`quantile ${p} within the ask ceiling`);
  ok(near(r.q(.5),r.Vreal,1e-6),"q(.5) is the median realised price");
  ok(r.Vmean<=r.ceil*(1+1e-9)&&r.Vmean>=r.q(.02),"mean price inside the distribution"); }
/* 8b. priced at value, the closed price lands where IBBA measures it (85-102% of ask),
   and a bull case is a real outcome, not the ceiling repeated */
for(const ind of Object.keys(A.IND)) for(const ern of [3e5,1.5e6]){
  const t=median(ind,ern), V=A.model({...t,ask:1}).V, r=A.model({...t,ask:V});
  ok(r.Vmean/V>.80&&r.Vmean/V<=1.03,`${ind} ${ern}: E[price|close]/ask ${(r.Vmean/V).toFixed(3)} at the value`);
  ok(r.q(.80)<r.q(.94)*(1-1e-3)||r.capShare>.2,`${ind} ${ern}: bull case spread`); }

/* 9. interventions compose independently of order */
{ const r0=A.model(EX), ks=["sops","gm","qoe","margin","divers"];
  const ref=JSON.stringify(A.applyAll(EX,r0,ks));
  for(const perm of [[4,3,2,1,0],[1,0,3,2,4],[2,4,0,3,1]])
    ok(JSON.stringify(A.applyAll(EX,r0,perm.map(i=>ks[i])))===ref,"intervention order independence"); }

/* 10. a general manager's salary comes off earnings */
{ const r0=A.model(EX), s1=A.applyAll(EX,r0,["gm"]);
  ok(near(s1.ern,EX.ern-A.gmSalary(EX),1e-6),"GM salary deducted from normalized earnings"); }

/* 11. optimiser bookkeeping, and more budget is never worse */
{ const r0=A.model(EX); let prev=-Infinity;
  for(const B of [0,5e4,1.5e5,4e5,1e6]){
    const o=A.optimize({...EX,optRho:1.1},r0,B,900,.75);
    ok(near(o.V.c,A.costOf(EX,o.V.keys),1e-6),"reported cost equals the sum of its actions");
    ok(o.V.days===A.daysOf(EX,o.V.keys),"reported days equal the longest action");
    ok(o.V.c<=B+1e-9,"optimum within budget");
    ok(o.V.net>=prev-1e-6,`budget ${B} not worse than a smaller one`); prev=o.V.net;
  } }

/* 12. no output is undefined, NaN or infinite at the framework example */
{ const r=A.model(EX); r.score=A.omniScore(r);
  ok(finiteDeep({V:r.V,Vreal:r.Vreal,EVp:r.EVp,PC:r.PC,tMed:r.tMed,score:r.score,risk:r.risk,fv:r.fv}),
     "framework example is finite everywhere"); }

/* 13. the expected-proceeds optimum must not depend on how much the owner values
       keeping the business (theta); only the utility optimum may */
{ const r0=A.model(EX), base={...EX,rhoSell:A.bestRatio(EX,0,900)};
  const a=A.optimize({...base,optRho:A.bestRatio(EX,.75,900)},r0,1e5,900,.75);
  const b=A.optimize({...base,optRho:A.bestRatio(EX,0,900)},r0,1e5,900,0);
  ok(near(a.V.net,b.V.net,1e-6),`proceeds optimum independent of theta: ${a.V.net} vs ${b.V.net}`);
  ok(a.U.U>=a.V.U-1e-6,"the utility optimum is at least as good on utility as the proceeds optimum"); }

/* 14. typed amounts: the whole string is one number with an optional unit */
{ const fs=require("fs"),path=require("path");
  const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
  const src=html.slice(html.indexOf("function parseAmount(t){")); const body=src.slice(0,src.indexOf("\n}\n")+2);
  const parseAmount=new Function(body+";return parseAmount;")();
  const cases=[["$1.45M",1.45e6],["1,450,000",1450000],["450k",450000],["1e6",1e6],["2.5b",2.5e9],["14%",14],
    ["$900/day",900],["6 years",6],["none",0],[".5m",5e5],["-5",-5],
    ["12.3.4m",NaN],["1k5",NaN],["",NaN],["$",NaN],["abc",NaN],["1e999",NaN]];
  for(const [inp,exp] of cases){ const v=parseAmount(inp);
    ok(Number.isNaN(exp)?Number.isNaN(v):near(v,exp,1e-6),`parseAmount(${JSON.stringify(inp)}) = ${v}, expected ${exp}`); } }

/* 15. the business score: a median business priced at its proceeds optimum scores 50,
       and the score does not move with earnings once transferability sits at the
       size-adjusted peer medians (size lives in the model value, not the score) */
{ const biz=s=>{ const V=A.model({...s,ask:1}).V; return A.omniScore(A.model({...s,ask:V*A.bestRatio(s,0,900)}),"opt"); };
  for(const ind of ["medical","rest","msp","mfg"]) for(const ern of [2e5,1e6,5e6]){
    ok(biz(median(ind,ern))===50,`median ${ind} ${ern}: business score 50`); }
  const sc=[.6e6,1e6,1.45e6,2e6,3e6].map(e=>{ const R=A.sizeRefs(e); return biz({...EX,ern:e,own:R.own,mgt:R.mgt,fin:R.fin}); });
  ok(Math.max(...sc)-Math.min(...sc)<=2,`business score flat in earnings at fixed revenue: ${sc}`); }

/* 16. no cliffs at the published size-band edges */
for(const edge of [5e5,1e6,2e6,5e6]){
  const s={...EX,ask:edge}; let lo=1e3,hi=1e8;
  for(let i=0;i<90;i++){ const m=Math.sqrt(lo*hi); A.model({...s,ern:m,rev:Math.max(m*3,1e5)}).V<edge?lo=m:hi=m; }
  const a=A.model({...s,ern:lo,rev:Math.max(lo*3,1e5)}), b=A.model({...s,ern:hi,rev:Math.max(hi*3,1e5)});
  ok(Math.abs(b.tMed-a.tMed)<.5,`time to close continuous at ${edge}: ${a.tMed} vs ${b.tMed}`);
  ok(Math.abs(b.EVp/a.EVp-1)<1e-3,`expected proceeds continuous at ${edge}`);
  ok(Math.abs(b.cashShare-a.cashShare)<1e-4,`cash share continuous at ${edge}`); }

/* 17. strategic premium bounded; capped mean never above the ceiling */
for(const [ind,rev,ern] of [["vet",1e8,2e6],["wash",5e9,1e8],["medical",6e6,1.45e6]]){
  const r=A.model({...EX,ind,rev,ern,ask:ern*3});
  ok(r.stratPrem/r.V<=.40+.25,`${ind} rev ${rev}: strategic premium ${(r.stratPrem/r.V*100).toFixed(0)}% of value`); }
{ const r=A.model({...EX,ind:"wash",rev:5e9,ern:4.6e9,ask:1e3});
  ok(r.Vmean<=r.ceil*(1+1e-9),`capped mean ${r.Vmean} within ceiling ${r.ceil}`); }

/* 18. headroom above the ask is IBBA's band level only, never the industry factor */
for(const ind of Object.keys(A.IND)) for(const ern of [3e5,1.5e6,4e6]){
  const s={...EX,ind,ern,rev:ern*7.5,buyers:150}, V=A.model({...s,ask:1}).V, r=A.model({...s,ask:V*.95});
  ok(r.q(.99)<=r.inputs.ask*Math.max(1,r.ft.pctAskSize)*(1+1e-9)&&r.q(.99)<=r.inputs.ask*1.0201,
     `${ind} ${ern}: realised price ${(r.q(.99)/r.inputs.ask*100).toFixed(1)}% of ask`); }

/* 19. fitted v4 tables: rate, employees, GM salary, margins, quality weights, thin pools */
{ const F=A.MODELS.fitted;
  for(const p of [1e5,5e5,2e6,1e7,1e8]){ const r=A.sbaRate(p);
    ok(r>=F.sba_rate.prime+1&&r<=F.sba_rate.prime+3,`SBA rate at ${p}: ${r}`); }
  ok(A.sbaRate(1e7)<=A.sbaRate(3e5),"larger loans price no higher");
  for(const k of Object.keys(A.IND)){
    ok(A.jobsFor(2e6,k)>=1&&A.jobsFor(2e7,k)>A.jobsFor(2e6,k),`${k}: employees grow with revenue`);
    const g=F.gm_wage.by_industry[k], w=F.gm_wage.wage_growth_2021_2026;
    for(const rev of [3e5,5e6,2e8]){ const s=A.gmSalary({ind:k,rev});
      ok(s>=g.p10*w-1&&s<=g.p90*w+1,`${k}: GM salary ${Math.round(s)} inside the BLS p10-p90`); }
    const m=A.typMargin(k,5e5); ok(m>.1&&m<.5,`${k}: typical SDE margin ${m.toFixed(3)}`); }
  let s2=0; for(const k in A.QW.w) s2+=(A.QW.w[k]/A.QW.norm)**2;
  ok(near(s2,1,1e-12),"quality weights keep the composite standard normal");
  const t=median("medical",1e6), V=A.model({...t,ask:1}).V;
  const typ=A.model({...t,ask:V}), thin=A.model({...t,ask:V,buyers:5}), deep=A.model({...t,ask:V,buyers:600});
  ok(thin.PC<typ.PC,`a thin pool closes less often: ${thin.PC} vs ${typ.PC}`);
  ok(near(deep.PC,typ.PC,1e-12),"a deeper pool earns the competition premium, not a higher P_C");
  ok(thin.thinF>0&&thin.thinF<1&&typ.thinF===1,"thin-pool factor is 1 at a typical pool"); }

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
