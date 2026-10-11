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
    const g=F.gm_wage.by_industry[k], w=F.gm_wage.wage_growth;
    for(const rev of [3e5,5e6,2e8]){ const s=A.gmSalary({ind:k,rev});
      ok(s>=g.p10*w-1&&s<=g.p90*w+1,`${k}: GM salary ${Math.round(s)} inside the BLS p10-p90`); }
    const m=A.typMargin(k,5e5); ok(m>.1&&m<.5,`${k}: typical SDE margin ${m.toFixed(3)}`); }
  let s2=0; for(const k in A.QW.w) s2+=(A.QW.w[k]/A.QW.norm)**2;
  ok(near(s2,1,1e-12),"quality weights keep the composite standard normal");
  const t=median("medical",1e6), V=A.model({...t,ask:1}).V;
  const typ=A.model({...t,ask:V}), thin=A.model({...t,ask:V,buyers:5}), deep=A.model({...t,ask:V,buyers:600});
  ok(thin.PC<typ.PC,`a thin pool closes less often: ${thin.PC} vs ${typ.PC}`);
  ok(near(deep.PC,typ.PC,1e-12),"a deeper pool earns the competition premium, not a higher P_C");
  ok(thin.thinF>0&&thin.thinF<1&&typ.thinF===1,"thin-pool factor is 1 at a typical pool");
  const poor={...t,own:.95,mgt:.05,fin:.1,rec:0,cc:.6}, Vp=A.model({...poor,ask:1}).V;
  ok(near(A.model({...poor,ask:Vp}).PC,typ.PC,1e-12),"closing probability at a fair ask does not depend on quality"); }
/* 20. fitted buyer-type mix: shares sum to one; individuals fade and financial buyers rise with size */
{ const m=v=>A.model({...median("prof",v),ask:1});
  const small=m(8e4), big=m(8e6);
  const ind=r=>r.buyers.find(b=>b.k==="ind").sizeFit, pep=r=>r.buyers.find(b=>b.k==="pep").sizeFit;
  ok(ind(small)>ind(big)&&pep(big)>pep(small),"individuals at small deals, private equity at large ones");
  for(const r of [small,big]) ok(r.buyers.every(b=>b.sizeFit>=0&&b.sizeFit<=1),"buyer presence in [0,1]"); }

/* 21. GM wage table (OEWS May 2025, oews_refresh): shape, SEs, no top-code, no 2021 growth field */
{ const W=A.MODELS.fitted.gm_wage, BI=W.by_industry, P=["p10","p25","p50","p75","p90"];
  const naics21={home:"238220",medical:"621100",vet:"541940",msp:"541500",prof:"541200",mfg:"339900",dist:"423000",
    staff:"561320",land:"561730",wash:"811190",auto:"811110",constr:"238900",fit:"713940",rest:"722511"};
  ok(W.base==="OEWS May 2025","GM wages are the May 2025 OEWS release");
  ok(typeof W.wage_growth==="number"&&W.wage_growth>=1&&W.wage_growth<=1.08,`wage growth to June 2026 ${W.wage_growth}`);
  ok(W.wage_growth_2021_2026===undefined&&W.topcode===null,"no May-2021 growth factor and no top-code left");
  ok(W.wage_growth_se>0&&W.wage_growth_se<=.03,`economy-wide growth SE ${W.wage_growth_se}`);
  ok(Array.isArray(W.wage_growth_se_pct)&&W.wage_growth_se_pct.length===5
     &&W.wage_growth_se_pct.every(v=>typeof v==="number"&&v>=W.wage_growth_se&&v<=.08)
     &&W.wage_growth_se_pct[0]===Math.max(...W.wage_growth_se_pct),"percentile growth SEs, p10 the largest");
  ok(W.noise&&W.noise.kappa2>=1&&W.noise.kappa2<=6,`noise kappa^2 ${W.noise&&W.noise.kappa2}`);
  ok(typeof W.se_note==="string"&&W.se_note.length>0&&typeof W.wage_growth_se_note==="string"&&W.wage_growth_se_note.length>0,"SE notes present");
  ok(/wages (and salaries )?only/i.test(W.source),"source says the figures are wages only");
  for(const k of Object.keys(A.IND)){ const g=BI[k];
    ok(g&&P.every(p=>typeof g[p]==="number")&&P.every((p,i)=>i===0||g[p]>g[P[i-1]])&&g.p10>25000&&g.p90<5e5,
       `${k}: GM wage percentiles strictly increasing, inside $25k-$500k`);
    if(!g) continue;
    ok(P.every(p=>g[p]!==208000),`${k}: no percentile pinned at the old 2021 top-code`);
    ok(g.se===undefined&&[g.se_sampling,g.se_total].every(a=>Array.isArray(a)&&a.length===5)
       &&g.se_sampling.every((v,i)=>v>0&&v<=g.se_total[i]&&g.se_total[i]<=.35),`${k}: se_sampling <= se_total <= 0.35`);
    if(k!=="ecom") ok(g.se_sampling.every(v=>v>=.005)&&g.se_total.every(v=>v>=.03),`${k}: SEs not implausibly small`);
    if(naics21[k]) ok(g.naics===naics21[k],`${k}: keeps NAICS ${naics21[k]}`);
    let prev=0, mono=true;
    for(let e=5;e<=9;e+=.25){ const v=A.gmSalary({ind:k,rev:10**e}); if(!isFinite(v)||v<prev*(1-1e-12)) mono=false; prev=v; }
    ok(mono,`${k}: GM salary finite and non-decreasing in revenue`); }
  ok(BI.saas.naics==="513200","saas reads NAICS 2022 513200 (Software publishers)");
  ok(BI.ecom.naics==="44-45"&&/p75 [\d,]+-[\d,]+/.test(BI.ecom.bridge||"")&&/p90 [\d,]+-[\d,]+/.test(BI.ecom.bridge||""),
     "e-commerce is a labelled bridge with its p75/p90 range");
  const gm=A.gmSalary({ind:"medical",rev:6e6});
  ok(gm>8e4&&gm<1e5,`example medical practice GM salary ${Math.round(gm)} in $80k-$100k`); }

/* 22. time-to-close curve (fit/time_to_close_shape.py): log-logistic pinned to the band median,
       shape beta by size band (two levels), keyed on Vbase only */
{ const S=A.MODELS.fitted.ttc_shape, T=A.MODELS.close_and_timing.time_to_close;
  const CENT=[2.5e5,Math.sqrt(5e5*1e6),Math.sqrt(1e6*2e6),Math.sqrt(2e6*5e6),Math.sqrt(5e6*5e7)];
  /* table */
  ok(JSON.stringify(S.bands)===JSON.stringify(T.bands),"ttc_shape bands are the time-to-close bands");
  ok(["beta","beta_se","n","hist_median_listing","hist_median_listing_se","hist_median_loi","hist_median_loi_se"]
     .every(k=>Array.isArray(S[k])&&S[k].length===5),"ttc_shape arrays have 5 entries");
  ok(S.family==="loglogistic"&&S.beta.every(b=>b>1)&&S.beta_se.every(v=>v>0),"log-logistic, beta > 1, beta_se > 0");
  ok(JSON.stringify(S.beta)===JSON.stringify([2.20,2.64,2.64,2.64,2.64]),`beta is the fitted two-level table: ${S.beta}`);
  ok(S.beta.every((b,i)=>i===0||b>=S.beta[i-1]),"beta non-decreasing across bands");
  /* interpolated in ln(value), flat beyond the outer centres, continuous at the edges, no industry */
  const bt=p=>A.fitTiming(p,"medical").beta, bmin=Math.min(...S.beta), bmax=Math.max(...S.beta);
  CENT.forEach((c,i)=>ok(Math.abs(bt(c)-S.beta[i])<1e-12,`beta at the ${S.bands[i]} centre`));
  for(const p of [1,1e3,1e5,2.5e5]) ok(bt(p)===S.beta[0],`beta flat below $250k (${p})`);
  for(const p of [1.5812e7,3e7,1e9]) ok(Math.abs(bt(p)-S.beta[4])<1e-9,`beta flat above $15.8M (${p})`);
  for(const e of [5e5,1e6,2e6,5e6]) ok(Math.abs(bt(e*(1+1e-9))-bt(e*(1-1e-9)))<1e-3,`beta continuous at ${e}`);
  for(const k of Object.keys(A.IND)) ok(A.fitTiming(1.3e6,k).beta===bt(1.3e6),`beta independent of industry (${k})`);
  ok(bt(3.1623e6)>bt(2.5e5),"steeper with size: beta($3.16M) > beta($250k)");
  { let pb=-Infinity, mono=true, inR=true;
    for(let i=0;i<=600;i++){ const b=bt(Math.exp(Math.log(1e4)+(Math.log(1e9)-Math.log(1e4))*i/600));
      if(b<pb-1e-12) mono=false; if(b<bmin-1e-12||b>bmax+1e-12) inR=false; pb=b; }
    ok(mono&&inR,"beta non-decreasing in value and inside [min, max] on $10k-$1B"); }
  /* size order of the curve at a fair price: strict at 90/180 days, small named tolerances at 365/540 */
  const Fat=(p,t)=>{ const ft=A.fitTiming(p,"medical"); return 1/(1+Math.pow(t/ft.days,-ft.beta)); };
  for(const [t,tol] of [[90,0],[180,0],[365,.1],[540,1.4]]){
    let prev=null, rises=0, runMin=Infinity, maxRise=0;
    for(let i=0;i<=6000;i++){ const p=Math.exp(Math.log(1e5)+(Math.log(3e7)-Math.log(1e5))*i/6000), f=Fat(p,t);
      if(prev!==null&&f>prev+1e-12) rises++; runMin=Math.min(runMin,f); maxRise=Math.max(maxRise,f-runMin); prev=f; }
    if(tol===0) ok(rises===0,`F(${t} d) non-increasing in deal value (${rises} rises)`);
    else ok(100*maxRise<=tol,`F(${t} d) rises at most ${tol} pts with deal value (${(100*maxRise).toFixed(2)})`); }
  /* calibration guard at the band centres against the 2020-25 IBBA histograms (shares closed, %) */
  const HIST={90:[17.01,8.06,8.88,5.39,2.85],180:[43.26,32.07,30.68,21.67,17.53],365:[79.82,75.89,73.41,67.89,65.60]};
  const EXC={180:{"500K-1M":6,"2-5M":11},365:{"2-5M":8,"5-50M":8}};
  for(const d of [90,180,365]) CENT.forEach((c,i)=>{ const f=100*Fat(c,d), tol=(EXC[d]&&EXC[d][S.bands[i]])||4;
    ok(Math.abs(f-HIST[d][i])<=tol+.01,`F(${d} d) at the ${S.bands[i]} centre ${f.toFixed(1)}% within ${tol} pts of the histogram ${HIST[d][i]}%`); });
  /* per business: median exact, closed-form quantile, proper CDF, shape never reads the ask or quality */
  for(const ind of Object.keys(A.IND)) for(const ern of [6e4,3e5,1e6,2.5e6,1.2e7]) for(const rho of [.8,1,1.7]){
    const s0=median(ind,ern), V0=A.model({...s0,ask:ern*3}).V, s={...s0,ask:rho*V0}, r=A.model(s), tag=`${ind} ${ern} rho ${rho}`;
    ok(Math.abs(r.F(r.tMed)-.5)<1e-12&&Math.abs(r.tQ(.5)/r.tMed-1)<1e-9,`median exact: ${tag}`);
    ok([.1,.25,.75,.9].every(p=>Math.abs(r.F(r.tQ(p))-p)<1e-9),`quantile inverts F: ${tag}`);
    ok(r.tMed===(r.tMult===undefined?r.ft.days:r.ft.days*r.tMult),`median is the band median: ${tag}`);
    ok(r.betaT===r.ft.beta&&r.ft.beta===A.fitTiming(r.Vbase,ind).beta&&r.lamE===r.tMed,`shape keyed on Vbase: ${tag}`);
    ok(r.F(0)===0&&r.F(20*r.tMed)>.99,`F(0) = 0 and F(20 t_med) > 0.99: ${tag}`);
    let prev=-1, cdf=true; for(let t=0;t<=3000;t+=5){ const f=r.F(t); if(!(isFinite(f)&&f>=prev&&f>=0&&f<=1)) cdf=false; prev=f; }
    ok(cdf,`F a proper CDF on 0..3000 days: ${tag}`);
    ok(r.t90===r.F(90)&&r.t180===r.F(180)&&r.t365===r.F(365),`t90/t180/t365 read the drawn curve: ${tag}`);
    const ra=A.model({...s,ask:s.ask*1.7}), rq=A.model({...s,own:.2,mgt:.9,fin:.2});
    ok(ra.betaT===r.betaT&&rq.betaT===r.betaT,`shape independent of the ask and quality: ${tag}`);
    ok(Math.abs(ra.F(ra.tMed)-.5)<1e-12,`median exact after an ask change: ${tag}`);
    if(r.tMult===undefined) ok([30,90,180,365,540].every(t=>ra.F(t)===r.F(t)&&rq.F(t)===r.F(t)),`curve independent of the ask and quality: ${tag}`); }
  /* the worked example ($3.49M fitted value): the upper level, quartiles 9^(1/beta) = 2.30x apart */
  { const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,
      yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6}, r=A.model(ex);
    ok(r.betaT===2.64&&Math.abs(r.tQ(.75)/r.tQ(.25)-Math.pow(9,1/2.64))<1e-9,
       `worked example: beta ${r.betaT}, quartiles ${r.tQ(.25).toFixed(0)}-${r.tQ(.75).toFixed(0)} d`); } }

/* 23. SBA risk refresh (fit/sba_risk_refresh.py; RESULT test_invariants): competing-risk hazard, charged off
   within 5 / 8 / 10 years if 2023-26 conditions hold; H.15 prime and FY2025-26 spread table; staffing not used */
{ const fs=require("fs"), path=require("path");
  const HTML=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
  const R=A.MODELS.risk, F=A.MODELS.fitted, PR=F.sba_rate.prime;
  const PINS=[{"args": [1000000.0, "medical", null, 10, false, null], "p5": 0.013185443385233407, "p8": 0.034686887718461956, "pTerm": 0.04158610968566404, "lgd": 0.6008056544102781, "expLoss": 0.02498516984407299, "rel": 0.7373423703131923}, {"args": [300000.0, "rest", 10.5, 12, true, "TX"], "p5": 0.0648660194374464, "p8": 0.12852339606860294, "pTerm": 0.15408669954664808, "lgd": 0.6243882819012078, "expLoss": 0.09620992959375921, "rel": 2.7320336799051077}, {"args": [5000000.0, "home", null, 30, false, "CA"], "p5": 0.008145831324026047, "p8": 0.02969939541600232, "pTerm": 0.035606605164245186, "lgd": 0.5824328970421608, "expLoss": 0.02073845819964769, "rel": 0.631322786600092}, {"args": [40000000.0, "ecom", 9.0, 60, false, "NY"], "p5": 0.008755474177616511, "p8": 0.0330519726517333, "pTerm": 0.03962601001216305, "lgd": 0.5808520292789736, "expLoss": 0.023016848327793833, "rel": 0.702588830002891}, {"args": [764705.8823529412, "fit", null, 8, false, null], "p5": 0.029182196281486647, "p8": 0.07207561419593358, "pTerm": 0.08641145385950479, "lgd": 0.6054283974620153, "expLoss": 0.052315948032522853, "rel": 1.5321179762323545}, {"args": [150000.0, "auto", 12.0, 4, false, "FL"], "p5": 0.06543029305563433, "p8": 0.12369183373613088, "pTerm": 0.1482941394662473, "lgd": 0.6278803980961786, "expLoss": 0.0931109833233976, "rel": 2.6293287139405552}];
  /* the average sector: fitRisk with every sector table emptied ("zzz" maps to 81, which then carries no effect) */
  const avgSector=fn=>{ const a=R.industry_effects,b=R.pif.sector; R.industry_effects={}; R.pif.sector={};
    try{ return fn(); } finally { R.industry_effects=a; R.pif.sector=b; } };
  /* 1. the console reproduces the fitted model exactly (Python mirror on the shipped, rounded tables) */
  for(const c of PINS){ const r=A.fitRisk(...c.args);
    for(const k of ["p5","p8","pTerm","lgd","expLoss","rel"]) ok(Math.abs(r[k]-c[k])<=1e-9*Math.max(1,Math.abs(c[k])),`pin ${JSON.stringify(c.args)} ${k}: ${r[k]} vs ${c[k]}`); }
  /* 2. horizons: 0 < p5 < p8 < pTerm < 1, headline is the term, and the term uses the stated tail factor */
  for(const k of Object.keys(A.IND)) for(const v of [2e5,1e6,4e6]){ const r=A.fitRisk(v,k,null,10,false,null);
    ok(r.p5>0&&r.p5<r.p8&&r.p8<r.pTerm&&r.pTerm<0.5,`${k} ${v}: horizons ordered ${r.p5} ${r.p8} ${r.pTerm}`);
    ok(r.p===r.pTerm&&Math.abs(r.pTerm-r.p8*R.tail_factor)<1e-12,`${k}: headline is the term`); }
  ok(R.horizon_months===60&&R.observed_months===96&&R.term_months===120,"horizons are 5 / 8 / 10 years");
  /* the tail factor is a labelled transfer judgment: inside the loan-band range of mature vintages, with an SE that covers it */
  ok(R.tail_factor>=1.1&&R.tail_factor<=1.3,"tail factor inside the 1.1-1.3 range mature vintages show");
  ok(R.tail_factor_se>=0.07,"tail factor SE covers the loan-band range (>= 0.07)");
  ok(R.tail_by_band["<150k"].ratio<R.tail_factor&&R.tail_factor<R.tail_by_band[">=1.5M"].ratio,"tail factor between the small- and large-loan ratios");
  /* 3. larger loans are no riskier at the table rate over 5 years; flat beyond the 7(a) cap */
  for(const k of Object.keys(A.IND)){ let prev=1;
    for(const v of [5e4,1e5,3e5,1e6,3e6,5.8e6]){ const p=A.fitRisk(v,k,null,10,false,null).p5; ok(p<=prev+1e-12,`${k}: 5-year risk falls with size at ${v}`); prev=p; }
    ok(Math.abs(A.fitRisk(6e6,k,null,10,false,null).p5-A.fitRisk(6e8,k,null,10,false,null).p5)<1e-12,`${k}: flat above the $5M loan cap`); }
  /* 3b. the size effect fades with time on book: the large/small ratio is closer to 1 over 8 years than over 5 */
  { const s=A.fitRisk(2e5,"prof",null,10,false,null), b=A.fitRisk(5e6,"prof",null,10,false,null);
    ok(R.co.age_coef.lnamt>0&&R.co.coef.lnamt<0,"size lowers risk, less so with time on book");
    ok(b.p8/s.p8>b.p5/s.p5,"size gradient flatter at 8 years than at 5"); }
  /* 4. a higher spread raises risk up to prime+3, and is flat above (the fitted hinge) */
  { let prev=0; for(const s of [0,1,2,2.5,3]){ const p=A.fitRisk(1e6,"rest",PR+s,10,false,null).p5; ok(p>prev,`spread ${s}: risk rises`); prev=p; }
    ok(A.fitRisk(1e6,"rest",PR+3,10,false,null).p5===A.fitRisk(1e6,"rest",PR+6,10,false,null).p5,"flat above prime+3"); }
  /* 4b. risk depends on the spread, not the rate level: moving prime and the rate together changes nothing */
  { const p0=A.fitRisk(9e5,"auto",PR+2,6,false,null).p; F.sba_rate.prime=PR+1.5; const p1=A.fitRisk(9e5,"auto",PR+3.5,6,false,null).p; F.sba_rate.prime=PR;
    ok(Math.abs(p0-p1)<1e-15,"rate level not applied (spread only)"); }
  /* 5. rate omitted = rate from sbaRate */
  ok(A.fitRisk(8e5,"auto",undefined,6,false,null).p5===A.fitRisk(8e5,"auto",A.sbaRate(8e5),6,false,null).p5,"default rate is sbaRate");
  /* 6. population anchors: base and observed 5-year rate are the same order; reference loan near the base */
  ok(R.base_cif.h60>0.01&&R.base_cif.h60<0.035,"population 5-year charge-off between 1% and 3.5%");
  ok(Math.abs(R.base_cif.h60-R.aj_pooled.cif60)<3*R.aj_pooled.cif60_se+0.003,"model population average near the Aalen-Johansen 5-year rate");
  ok(Math.abs(R.base_cif.term-R.base_cif.h96*R.tail_factor)<1e-3,"population term = 8-year x tail factor");
  ok(R.base_cif.spec_range.h96[0]<=R.base_cif.h96+1e-4&&R.base_cif.h96<=R.base_cif.spec_range.h96[1]+1e-4,"shipped 8-year level inside its specification range");
  /* the stated level uncertainty includes the reference period: 2025-26 ran below 2023-24, and the range brackets the shipped level */
  ok(R.base_cif.conditions.ratio<1&&R.base_cif.conditions_range.h96[0]<R.base_cif.h96&&R.base_cif.h96<R.base_cif.conditions_range.h96[1],"reference-period range brackets the shipped 8-year level");
  ok(R.base_cif.level_range.h96[0]<=Math.min(R.base_cif.spec_range.h96[0],R.base_cif.conditions_range.h96[0])+1e-9&&R.base_cif.level_range.h96[1]>=Math.max(R.base_cif.spec_range.h96[1],R.base_cif.conditions_range.h96[1])-1e-9,"level range = specifications and reference periods");
  ok((R.base_cif.level_range.h96[1]-R.base_cif.level_range.h96[0])/R.base_cif.h96>0.2,"stated level range is not the narrow specification range alone");
  /* the reference loan ($650k note, table rate, average sector, no state) sits near the average loan */
  { const r=avgSector(()=>A.fitRisk(6.5e5/0.85,"zzz",null,8,false,null)); ok(r.rel>0.8&&r.rel<1.2,`reference loan rel ${r.rel}`);
    ok(Math.abs(r.rel-r.pTerm/R.base_cif.term)<1e-12,"rel = pTerm / base_cif.term"); }
  /* 6d. base_cif is what fitRisk prices: fitRisk applied to every FY2024-26 acquisition loan (its own size, sector and 6-digit
         effect, state and franchise flag; table rate, variable note) averages base_cif.h60 / h96 within 2%, and rel averages 1 */
  { const BK=JSON.parse(fs.readFileSync(path.join(__dirname,"sba_book_fy2024_26.json"),"utf8"));
    const ie=R.industry_effects, ps=R.pif.sector; let s5=0,s8=0,sr=0; const n=BK.loan.length;
    try{ for(let i=0;i<n;i++){ R.industry_effects={"81":BK.sec_co[BK.sec[i]]+BK.n6[i]/1e4}; R.pif.sector={"81":BK.sec_pif[BK.sec[i]]};
        const r=A.fitRisk(BK.loan[i]/R.loan_share,"zzz",null,null,BK.fr[i]===1,BK.st_keys[BK.st[i]]); s5+=r.p5; s8+=r.p8; sr+=r.rel; } }
    finally { R.industry_effects=ie; R.pif.sector=ps; }
    ok(n===BK.n&&n>10000,`book fixture has ${n} loans`);
    ok(Math.abs(s5/n/R.base_cif.h60-1)<0.02,`console-priced book 5-yr mean ${s5/n} vs base_cif.h60 ${R.base_cif.h60}`);
    ok(Math.abs(s8/n/R.base_cif.h96-1)<0.02,`console-priced book 8-yr mean ${s8/n} vs base_cif.h96 ${R.base_cif.h96}`);
    ok(Math.abs(sr/n-1)<0.02,`rel averages 1 over the book: ${sr/n}`); }
  /* 6b. by loan band: the fitted model (own spreads and rate type, realised calendar) matches the observed 5-year rate within
         2 SE; the console (table spreads, variable note, current conditions, shrunk) within 1.5 SE and 0.90-1.25x */
  for(const b of Object.keys(R.size_band_cif)){ const B=R.size_band_cif[b];
    ok(B.cif60>0.003&&B.cif60<0.06,`band ${b} observed 5-yr rate`);
    ok(Math.abs(B.model60_insample-B.cif60)<=2*B.cif60_se,`band ${b}: fitted model (own spreads, realised calendar) ${B.model60_insample} vs observed ${B.cif60} (SE ${B.cif60_se})`);
    ok(Math.abs(B.model60_table_spread-B.cif60)<=1.5*B.cif60_se&&B.model60_table_spread/B.cif60>0.90&&B.model60_table_spread/B.cif60<1.25,
       `band ${b}: console at table spreads ${B.model60_table_spread} vs observed ${B.cif60}`);
    const r=avgSector(()=>A.fitRisk(B.loan_median/R.loan_share,"zzz",null,null,false,null));
    ok(Math.abs(r.p5-B.cif60)<=3*B.cif60_se+0.004,`band ${b}: fitRisk at the band median (average sector) ${r.p5} vs observed ${B.cif60}`); }
  /* 6c. multiples stay in a believable range for realistic console inputs (table rate, any industry, $200k-$10M, 2-50 staff) */
  for(const k of Object.keys(A.IND)) for(const v of [2e5,6e5,2e6,1e7]) for(const j of [2,8,50]){ const r=A.fitRisk(v,k,null,j,false,null);
    ok(r.rel>0.2&&r.rel<3.5,`${k} ${v} ${j} staff: rel ${r.rel}`); }
  /* 6e. staffing does not enter: SBA's jobs count is not the console's head count */
  for(const k of ["staff","rest","medical"]) ok(A.fitRisk(2e6,k,null,2,false,"TX").p===A.fitRisk(2e6,k,null,90,false,"TX").p,`${k}: risk does not move with staffing`);
  ok(R.co.coef.lnjobs===undefined&&R.pif.coef.lnjobs===undefined&&R.staffing.applied===false,"no staffing coefficient shipped");
  /* 7. effects: unknown state/industry = 0; shrunk effects bounded; out-of-time shrink in (0,1] */
  ok(A.fitRisk(1e6,"medical",null,10,false,"ZZ").p5===A.fitRisk(1e6,"medical",null,10,false,null).p5,"unknown state is national");
  for(const k in R.state_effects) ok(Math.abs(R.state_effects[k])<0.6,`state ${k} bounded`);
  for(const k in R.naics6_effects) ok(Math.abs(R.naics6_effects[k])<0.6,`naics6 ${k} bounded`);
  for(const k of Object.keys(A.IND)){ ok(R.industry_effects[A.IND2NAICS[k]]!==undefined,`${k} has a charge-off sector effect`);
    ok(R.pif.sector[A.IND2NAICS[k]]!==undefined,`${k} has a payoff sector effect`); }
  ok(R.co.log_base[0]===null,"no charge-off in the first six months on book");
  ok(R.co.lp_shrink>0.5&&R.co.lp_shrink<=1,"out-of-time shrink in (0.5, 1]");
  /* 7b. shipped SEs are clustered (lender / two-way), never below the Hessian SEs */
  for(const k in R.co.se) ok(R.co.se[k]>=R.co.se_hessian[k]-1e-4,`co.se ${k} clustered >= Hessian`);
  ok(R.co.se.lnamt>=1.2*R.co.se_hessian.lnamt,"size SE inflated by clustering");
  /* 8. severity: timing-weighted mean LGD in a sane band, falling with age at charge-off and not rising with size;
        expected loss below the term probability */
  ok(R.lgd.b_age<0,"severity falls the later a loan fails (amortisation)");
  { let prev=1; for(const v of [3e4,2e5,1e6,3e6,6e6]){ const r=A.fitRisk(v,"prof",null,10,false,null);
    ok(r.lgd>0.4&&r.lgd<0.95,`lgd at ${v}: ${r.lgd}`);
    if(R.lgd.b_size<=0) ok(r.lgd<=prev+0.01,`lgd does not rise with size at ${v}`); prev=r.lgd;
    ok(r.expLoss>0&&r.expLoss<r.pTerm&&Math.abs(r.expLoss-r.pTerm*r.lgd)<1e-12,"expected loss = term probability x mean severity"); } }
  /* 9. rate table: H.15 prime and date; spreads non-increasing in size and inside SBA's maximum; knot uncertainty >= 0.05 */
  ok(PR===7.00&&F.sba_rate.prime_asof==="2026-09-17","prime 7.00% since 2026-09-17 (H.15)");
  { let prev=99; for(const v of [5e4,2e5,6e5,1.5e6,4e6,1e7]){ const s=A.sbaRate(v)-PR; ok(s<=prev+1e-12&&s>=1.3&&s<=2.6,`spread at ${v}: ${s}`); prev=s; } }
  ok(F.sba_rate.spread_knots_se.every(v=>v>=0.0)&&Math.max(...F.sba_rate.spread_knots_se)>=0.05,"knot uncertainty reflects sample choice, not the heaped bootstrap");
  ok(/cancelled/.test(F.sba_rate.source),"rate source says the sample includes cancelled and undisbursed approvals");
  /* 10. the full model carries it through; headline risk never rises with revenue at a fixed margin (within 1%), and is flat once
         the note hits the $5M cap */
  { const EX={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
    const r=A.model(EX);
    ok(isFinite(r.risk.p)&&r.risk.p>0&&r.risk.p<0.3&&r.risk.p5<r.risk.p,"model() risk finite and ordered");
    for(const k of Object.keys(A.IND)){ let prev=Infinity, bad=0;
      for(let i=0;i<=48;i++){ const rev=3e5*Math.pow(4e7/3e5,i/48); const o=A.model({...EX,ind:k,rev,ern:rev*1.45/6,ask:rev*.54});
        if(o.risk.p>prev*1.01) bad++; prev=o.risk.p; }
      ok(bad===0,`${k}: headline risk rises with revenue in ${bad} steps`); } }
  /* 11. labels: the 10-year figure is conditional on current conditions; checks the Data tab must show; state label */
  ok(R.conditions==="2023-26","conditions label");
  { const i=HTML.indexOf('const e=$("o_risk")'), j=HTML.indexOf('e.innerHTML=h;})();',i), H=HTML.slice(i,j);
    ok(i>0&&j>i&&/conditions hold/.test(H),"hero says 'if 2023-26 conditions hold'");
    ok(!/-yr term/.test(H)&&/charged off within /.test(H),"hero says 'within 10 yrs', not 'the 10-yr term'");
    ok(/conditions_range/.test(H),"hero tooltip shows the reference-period range"); }
  for(const f of ["vintage_oe","cal_holdout_slope","lp_shrink","spec_range","conditions_range","level_range","through_cycle","rate_level.uplift_range","tail_by_band","real_estate","spread_channel","staffing"])
    ok(HTML.indexOf("R."+f)>=0||HTML.indexOf("R.validation."+f)>=0||HTML.indexOf("R.co."+f)>=0||HTML.indexOf("R.base_cif."+f)>=0,`Data tab shows ${f}`);
  ok(HTML.indexOf("pts default risk")<0&&HTML.indexOf("pts charge-off risk, 10 yr")>=0,"state dropdown labels the 10-year charge-off risk");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
