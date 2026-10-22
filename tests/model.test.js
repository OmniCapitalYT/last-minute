/* Invariants of the Omni Method model. Run: node tests/model.test.js */
const A=require("./load.js");
/* the page without SBA's guaranty fee: tests built before round 9 added it keep the structures they test (round 10 made
   "waived" the FY2027 waiver itself, a loan of $700k or less, so it no longer removes the fee from a larger loan) */
const NF=A.loadWith([["  if(!(loan>0)) return 0;\n  if(loan<=15e4)","  return 0;\n  if(loan<=15e4)"]]);
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
  const I=A.IND[ind],rev=ern/A.typMargin(ind,ern);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,franchise:false,st:null,...A.peerMedians(ind,ern,rev)};
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

/* 6. both scores rank against ONE population, peers priced at their proceeds optimum: a business on every
      peer median scores 50 at its proceeds optimum and 48 at a market ask of REF_RATIO (what that ask costs),
      and the same ask gives the same score whichever card shows it */
for(const ind of Object.keys(A.IND)) for(const ern of [1e5,3e5,1e6,3e6,1e7]){
  const t=median(ind,ern), V=A.model({...t,ask:1}).V, opt=A.model({...t,ask:V*A.bestRatio(t,0,0)});
  ok(A.omniScore(opt)===50,`median ${ind} ${ern} scores 50 at its proceeds optimum`);
  ok(A.omniScore(A.model({...t,ask:V*A.REF_RATIO}))===48,`median ${ind} ${ern} scores 48 at REF_RATIO`);
}
/* 6b. the business score (the profile at its proceeds optimum) is never below the Omni score (the profile at its
       ask): random businesses across the reachable inputs, any ask from 0.5x to 3x value */
{ let sd=11, viol=[]; const rn=()=>{ sd=(sd*16807)%2147483647; return (sd-1)/2147483646; }, inds=Object.keys(A.IND);
  for(let i=0;i<60;i++){ const ind=inds[Math.floor(rn()*inds.length)], ern=Math.exp(Math.log(3e4)+rn()*Math.log(500)), mg=.05+rn()*.4;
    const s={ind,ern,rev:ern/mg,grw:-.3+rn()*.8,gm:.1+rn()*.8,rec:rn(),cc:.01+rn()*.8,ret:.1+rn()*.85,plt:.02+rn()*.95,own:.05+rn()*.9,
      mgt:.05+rn()*.9,fin:.1+rn()*.85,yrs:6,buyers:5+Math.floor(rn()*595),st:null,franchise:false};
    const V=A.model({...s,ask:1}).V, sa={...s,ask:V*(.5+rn()*2.5)}, r=A.model(sa), omni=A.omniScore(r);
    const biz0=A.omniScore(A.model({...s,ask:V*A.bestRatio(s,0,0)})), biz=A.businessScore(sa,r,A.bestRatio(s,0,0)).score;
    if(omni>biz0||omni>biz||biz<biz0) viol.push(`${ind} ${Math.round(ern)} (${s.buyers} buyers): omni ${omni}, at the optimal ask ${biz0}, business ${biz}`); }
  ok(viol.length===0,`business score never below the Omni score, nor below the score at the optimal ask (${viol.join("; ")})`);
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  ok(/r\.score=omniScore\(r\);/.test(HTML)&&/const bs=businessScore\(s,r,s\.rhoSell\)/.test(HTML)&&/r\.scoreQ=bs\.score;/.test(HTML)
     &&/return \{score:Math\.max\(omniScore\(rq\),omniScore\(r\)\)/.test(HTML)&&!/omniScore\([^)]*,\s*"opt"\)/.test(HTML),
     "render scores both cards on one population (no 'opt' mode), the business score held at or above the Omni score"); }

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

/* 10. a general manager's loaded salary comes off earnings (BLS ECEC loading, fit/intervention_costs.py) */
{ const r0=A.model(EX), s1=A.applyAll(EX,r0,["gm"]), G=A.MODELS.fitted.interventions.gm;
  ok(near(s1.ern,EX.ern-G.loading*A.gmSalary(EX),1e-6),"GM's loaded salary deducted from normalized earnings"); }

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
{ const r0=A.model(EX), base={...EX,rhoSell:A.bestRatio(EX,0,0)};
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
{ const biz=s=>{ const V=A.model({...s,ask:1}).V; return A.omniScore(A.model({...s,ask:V*A.bestRatio(s,0,0)})); };
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
    /* overpricing_time: the ask (and, above value, quality through the gap) only rescales the curve with the median */
    ok([30,90,180,365,540].every(t=>Math.abs(ra.F(t*ra.tMult/r.tMult)-r.F(t))<1e-12&&Math.abs(rq.F(t*rq.tMult/r.tMult)-r.F(t))<1e-12),
       `curve rescaled exactly with the median: ${tag}`);
    if(rho<=1&&rq.inputs.ask<=rq.V) ok([30,90,180,365,540].every(t=>rq.F(t)===r.F(t)),`curve independent of quality at or below value: ${tag}`); }
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
  /* p5 and p8 are the Python mirror's (fit/sba_risk_refresh.py, on the shipped, rounded tables); pTerm, lgd, expLoss and
     rel were re-pinned in October 2026, when years 9-10 became the fitted table read by loan size (fit/sba_tail_factor.py) */
  const PINS=[{"args": [1000000, "medical", null, 10, false, null], "p5": 0.013185443385233407, "p8": 0.034686887718461956, "pTerm": 0.04401401309971775, "lgd": 0.5922204141277481, "expLoss": 0.026065997065338974, "rel": 0.7681328638694198}, {"args": [300000, "rest", 10.5, 12, true, "TX"], "p5": 0.0648660194374464, "p8": 0.12852339606860294, "pTerm": 0.14606022115553777, "lgd": 0.6344067939188496, "expLoss": 0.09266159662236284, "rel": 2.549043999224045}, {"args": [5000000, "home", null, 30, false, "CA"], "p5": 0.008145831324026047, "p8": 0.02969939541600232, "pTerm": 0.038412838668372876, "lgd": 0.5727074320950822, "expLoss": 0.021999318193246506, "rel": 0.6703811285928949}, {"args": [40000000, "ecom", 9, 60, false, "NY"], "p5": 0.008755474177616511, "p8": 0.0330519726517333, "pTerm": 0.04274902149888276, "lgd": 0.5712726084040274, "expLoss": 0.0244213450183866, "rel": 0.7460562216209906}, {"args": [764705.8823529412, "fit", null, 8, false, null], "p5": 0.029182196281486647, "p8": 0.07207561419593358, "pTerm": 0.08864061719953954, "lgd": 0.6013808133330445, "expLoss": 0.05330676646580214, "rel": 1.5469566701490323}, {"args": [150000, "auto", 12, 4, false, "FL"], "p5": 0.06543029305563433, "p8": 0.12369183373613088, "pTerm": 0.13618725561363315, "lgd": 0.6445559656203544, "expLoss": 0.08778030804723135, "rel": 2.3767409356655}];
  /* the average sector: fitRisk with every sector table emptied ("zzz" maps to 81, which then carries no effect) */
  const avgSector=fn=>{ const a=R.industry_effects,b=R.pif.sector; R.industry_effects={}; R.pif.sector={};
    try{ return fn(); } finally { R.industry_effects=a; R.pif.sector=b; } };
  /* the representative cell alone: since round 10 the console reads each label's pooled cells (naics6_pools); the
     Python mirror's pins are at the representative codes, so they are checked with the pools set aside */
  const noPools=fn=>{ const p=R.naics6_pools; delete R.naics6_pools; try{ return fn(); } finally { R.naics6_pools=p; } };
  /* 1. the console reproduces the fitted model exactly (Python mirror on the shipped, rounded tables) */
  for(const c of PINS){ const r=noPools(()=>A.fitRisk(...c.args));
    for(const k of ["p5","p8","pTerm","lgd","expLoss","rel"]) ok(Math.abs(r[k]-c[k])<=1e-9*Math.max(1,Math.abs(c[k])),`pin ${JSON.stringify(c.args)} ${k}: ${r[k]} vs ${c[k]}`); }
  /* 2. horizons: 0 < p5 < p8 < pTerm < 1, headline is the term, and the term is p8 times the fitted tail at the note's size */
  const TB=R.tail.by_band, tailRef=loan=>{ const x=Math.log(Math.max(loan,1)), c=TB.centres.map(Math.log), n=c.length;
    if(x<=c[0]) return TB.scale*TB.ratio[0]; if(x>=c[n-1]) return TB.scale*TB.ratio[n-1];
    let j=0; while(!(x>=c[j]&&x<=c[j+1])) j++; return TB.scale*(TB.ratio[j]+(TB.ratio[j+1]-TB.ratio[j])*(x-c[j])/(c[j+1]-c[j])); };
  for(const k of Object.keys(A.IND)) for(const v of [2e5,1e6,4e6]){ const r=A.fitRisk(v,k,null,10,false,null);
    ok(r.p5>0&&r.p5<r.p8&&r.p8<r.pTerm&&r.pTerm<0.5,`${k} ${v}: horizons ordered ${r.p5} ${r.p8} ${r.pTerm}`);
    ok(r.p===r.pTerm&&Math.abs(r.pTerm-r.p8*r.tail)<1e-12&&Math.abs(r.tail-tailRef(r.loan))<1e-12,`${k}: headline is the term, p8 x the tail at the note's size`); }
  for(const c of PINS){ const r=noPools(()=>A.fitRisk(...c.args)); ok(Math.abs(r.pTerm-c.p8*tailRef(r.loan))<1e-12,`pin ${JSON.stringify(c.args)}: pTerm = pinned p8 x the tail`); }
  ok(R.horizon_months===60&&R.observed_months===96&&R.term_months===120,"horizons are 5 / 8 / 10 years");
  /* years 9-10 are FITTED (fit/sba_tail_factor.py): the pooled factor and its SE, the size table and its scale */
  { const T=R.tail, E=T.estimates, r=TB.ratio.map(v=>v*TB.scale);
    ok(R.tail_factor===undefined&&R.tail_by_band===undefined&&R.tail_note===undefined,"the judgment tail fields are gone");
    ok(T.factor===1.21&&T.factor>=1.1&&T.factor<=1.3,"tail factor 1.21, inside the 1.1-1.3 range mature vintages show");
    ok(near(T.factor_se,Math.round(E.se_total_measured*100)/100,1e-12)&&T.factor_se>=E.se_lower_no_drift,"tail SE = the measured parts in quadrature, rounded, above the no-drift lower bound");
    ok(near(E.se_total_measured,Math.hypot(E.se_parts.estimation,E.se_parts.term_bracket,E.se_parts.transport,E.se_parts.drift),2e-4),"tail SE parts add in quadrature");
    ok(Math.abs(E.midpoint-(E.two_class.ratio+E.three_class.ratio)/2)<1e-3&&Math.abs(T.factor-E.midpoint)<=0.005,"tail factor = the two- and three-class midpoint, rounded");
    ok(r[0]<T.factor&&T.factor<Math.max(...r),"tail factor between the small- and large-loan ratios");
    ok(TB.centres.every((v,i)=>i===0||v>TB.centres[i-1])&&r[0]===Math.min(...r),"band centres increasing, smallest loans lowest");
    ok(Math.abs(TB.scale-1)<0.01,"the scale only carries the rounding of the factor");
    ok(near(A.tailAt(1),r[0],1e-12)&&near(A.tailAt(1e8),r[r.length-1],1e-12),"flat beyond the outer band centres");
    let mono=true; for(let i=0;i<=60;i++){ const L=5e4*Math.pow(2e8/5e4,i/60); if(!(A.tailAt(L)>=Math.min(...r)-1e-12&&A.tailAt(L)<=Math.max(...r)+1e-12)) mono=false; }
    ok(mono,"the tail stays inside its band table");
    ok(T.late_hazard_by_term.n120.q.every((q,i)=>q>T.late_hazard_by_term.long.q[i]),"late charge-offs: 10-year notes above longer notes in every band"); }
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
  ok(Math.abs(R.base_cif.term-R.base_cif.h96*R.tail.by_band.book_tail)<1e-4,"population term = 8-year x the book's tail");
  ok(Math.abs(R.base_cif.se.term-Math.hypot(R.base_cif.se.h96*R.tail.by_band.book_tail,R.base_cif.h96*R.tail.factor_se))<1e-4
     &&Math.abs(R.base_cif.level_range.term[0]-R.base_cif.level_range.h96[0]*R.tail.by_band.book_tail)<1e-4
     &&Math.abs(R.base_cif.level_range.term[1]-R.base_cif.level_range.h96[1]*R.tail.by_band.book_tail)<1e-4,"term SE and range follow the 8-year level and the tail");
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
  for(const f of ["vintage_oe","cal_holdout_slope","lp_shrink","spec_range","conditions_range","level_range","through_cycle","rate_level.uplift_range","tail.factor","tail.by_band","real_estate","real_estate.business_only","spread_channel","staffing"])
    ok(HTML.indexOf("R."+f)>=0||HTML.indexOf("R.validation."+f)>=0||HTML.indexOf("R.co."+f)>=0||HTML.indexOf("R.base_cif."+f)>=0,`Data tab shows ${f}`);
  ok(HTML.indexOf("pts default risk")<0&&HTML.indexOf("pts charge-off risk, 10 yr")>=0,"state dropdown labels the 10-year charge-off risk");
}

/* 24. realised-price fan (fit/anchoring_realization.py; RESULT test_invariants): FAN_S = 0.80 of the value model's log
   spread is kept once a business is listed (CALIBRATED, mechanism not identified); M_TYP = 1.071 is the typical
   first-ask premium (self-audit and tests only); fanNodes() are exact slice means; ALPHA and AMAX unchanged */
{ const fs=require("fs"), path=require("path");
  const HTML=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
  const EXF={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,
             fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
  const r0=A.model(EXF), FAN_S=r0.fanS, M_TYP=r0.mTyp;
  ok(FAN_S>0&&FAN_S<=1&&near(FAN_S,0.80,1e-12),`FAN_S is exposed and equals the calibrated 0.80 (got ${FAN_S})`);
  ok(near(M_TYP,1.071,1e-12),`M_TYP is exposed and equals 1.071 (got ${M_TYP})`);
  ok(r0.ALPHA===.55&&A.AMAX===1.30,"anchoring alpha 0.55 and A_max 1.30 unchanged (judgment)");
  /* 24a. fanNodes(): 48 exact slice means of R(p)^FAN_S (the old 4,000-point grid overlapped its slices and ran
          0.8-0.9% high, 4.9% at the top); brute force with 20,000 midpoints per slice agrees to ~2e-5 */
  { const nodes=A.fanNodes(), N=48, M=20000; let worst=0;
    ok(nodes.length===N&&nodes.every((v,i)=>i===0||v>=nodes[i-1]),"48 fan nodes, increasing");
    for(let i=0;i<N;i++){ let t=0; for(let j=0;j<M;j++) t+=Math.pow(A.fanRatio((i+(j+.5)/M)/N),FAN_S);
      worst=Math.max(worst,Math.abs(nodes[i]/(t/M)-1)); }
    ok(worst<2e-4,`fan nodes are the slice means of R^FAN_S (worst relative gap ${worst.toExponential(2)})`); }
  for(const ind of Object.keys(A.IND)) for(const ern of [1.2e5,4e5,1.5e6]){
    const t=median(ind,ern), V=A.model({...t,ask:1}).V; if(V>8.5e6) continue;
    const r=A.model({...t,ask:V*M_TYP}), e=r.Vmean/r.inputs.ask;
    /* 24b. at the typical first-ask premium the model closes where Main-Street averages do on the first ask
            (BizBuySell 0.917 on the ask at sale = 0.905 on the first); larger deals realise more in the data,
            which the model does not have, so at $1.5M only a floor */
    if(ern<1e6) ok(e>=.875&&e<=.925,`${ind} ${ern}: E[P|close]/ask ${e.toFixed(4)} at the typical premium`);
    else ok(e>=.875,`${ind} ${ern}: E[P|close]/ask ${e.toFixed(4)} below the Main-Street floor`);
    /* 24c. a point mass at the ask, and the below-ask mean, in the calibrated range */
    ok(r.capShare>=.30&&r.capShare<=.55,`${ind} ${ern}: share closing at the ask ${r.capShare.toFixed(3)}`);
    const below=(r.Vmean-r.capShare*r.ceil)/(r.inputs.ask*(1-r.capShare));
    ok(below>=.77&&below<=.86,`${ind} ${ern}: below-ask mean ${below.toFixed(4)}`);
    /* 24d. downside disclosure: the bear scenario's low end q(.08)/ask (0.52 with the whole spread; EF analog 0.63) */
    const q8=r.q(.08)/r.inputs.ask;
    ok(q8>=.56&&q8<=.65,`${ind} ${ern}: bear low end q(.08)/ask ${q8.toFixed(4)}`);
    /* 24e. narrowing keeps the centre: the uncapped median is V x A(rho) x (1+comp) */
    ok(Math.abs(r.VrealFree/(V*r.anchorF*(1+r.compPrem))-1)<.01,`${ind} ${ern}: uncapped median moved`);
    /* 24f. the closing probability does not read the realised-price block; EVp = P_C x E[P|close] */
    const fp=A.fitClose(r.inputs.ask,r.V,undefined,r.Vbase).p;
    ok(near(r.PC,r.thinF<1?Math.min(.95,Math.max(0,fp*r.thinF)):fp,1e-9),`${ind} ${ern}: P_C changed`);
    ok(Math.abs(r.EVp-r.PC*r.Vmean)<=1e-9*r.EVp,`${ind} ${ern}: EVp = P_C x E[P|close]`);
  }
  /* 24g. price rises with the ask and its share of the ask falls, from 0.4x to 3x value */
  for(const t of [EXF,median("prof",1.6e5),median("mfg",1.5e6)]){
    const V=A.model({...t,ask:1}).V; let pv=-Infinity, pr=Infinity;
    for(let rho=.4;rho<=3.0001;rho+=.02){ const r=A.model({...t,ask:V*rho});
      ok(r.Vmean>=pv*(1-1e-9),`${t.ind} rho=${rho.toFixed(2)}: E[P|close] fell as the ask rose`);
      ok(r.Vmean/r.inputs.ask<=pr*(1+1e-9),`${t.ind} rho=${rho.toFixed(2)}: E[P|close]/ask rose with the ask`);
      pv=r.Vmean; pr=r.Vmean/r.inputs.ask; } }
  /* 24h. optimiser: theta = 0 does not move. At theta = .75 (the default) the utility has two near-equal peaks, near
          1.26x and the 1.5x cap; which wins is a knife-edge in FAN_S (flip near 0.95 at $900/day, 0.89 with no delay
          cost) and theta (0.785 at $900/day, 0.772 with no delay cost; pinned in 28; figures since the gap axis was read
          as Pepperdine states it, October 2026), so the
          WINNER is not pinned: it must be one of the two peaks, and the peaks must lie within 1% of value (the page
          then shows the patient-seller price as a range) */
  { const b0=A.bestRatio(EXF,0,900), b75=A.bestRatio(EXF,.75,900);
    ok(b0>=1.08&&b0<=1.13,`bestRatio(EX,0) ${b0.toFixed(3)}`);
    ok((b75>=1.08&&b75<=1.30)||b75>=1.45,`bestRatio(EX,.75) ${b75.toFixed(3)} is neither the interior peak nor the cap`);
    const V=A.model({...EXF,ask:1}).V; let ui=-Infinity, uc=-Infinity;
    for(let k=0;k<=140;k++){ const m=.80+k*.005, r=A.model({...EXF,ask:V*m}), u=r.EVp+(1-r.PC)*.75*r.V-900*r.tMean;
      if(m<1.35) ui=Math.max(ui,u); else uc=Math.max(uc,u); }
    ok(Math.abs(ui-uc)<.01*V,`theta=.75: the two peaks differ by ${(100*(ui-uc)/V).toFixed(2)}% of value (expected a near-tie)`); }
  /* 24i. the self-audit's fit-consistency row (renderCalib's own profile) reads 'in range' */
  { const I=A.IND.prof;
    const p={ind:"prof",rev:703000,ern:158950,ask:0,...A.peerMedians("prof",158950,703000),yrs:6,buyers:(I.buyers||50)};
    const V=A.model({...p,ask:1}).V, r=A.model({...p,ask:V*M_TYP}), e=r.Vmean/r.inputs.ask;
    ok(e>=.875&&e<=.925,`self-audit fit-consistency row ${e.toFixed(4)} in 87.5-92.5%`); }
  /* 24j. the page says what it does: R^s in the scenario equations, the calibrated badge, the benchmark label from $2M,
          the range note in the optimiser card, the self-audit row labelled as the fit's own target */
  ok(HTML.includes("cdot R^{s}")&&HTML.includes("R(0.08)^{s}=${Math.pow(")&&HTML.includes("R(p)^{s},")&&HTML.includes("s=${FAN_S.toFixed(2)}"),"eq_s / eq_ss / eq_a show R^s");
  ok(/share of the value spread kept once a business is listed \(FAN_S;[\s\S]{0,120}<span class="st adj">calibrated<\/span>/.test(HTML),"Data tab: FAN_S row badged calibrated");
  ok(/r\.Vbase>=2e6\?'Market benchmark: sale price as a share of the advisor&rsquo;s benchmark/.test(HTML),"realisation block: $2M+ IBBA ratio is a benchmark");
  ok(HTML.indexOf("close to a tie, so read the patient-seller price as a range")>0,"optimiser card: range note");
  ok(HTML.indexOf("Fit-consistency check, not an external benchmark")>0&&HTML.indexOf("Listing premium implied by")<0,"self-audit row replaced");
  ok(HTML.indexOf("const M=4000")<0&&HTML.indexOf("M=4000,out=[]")<0,"old overlapping-grid fanNodes gone");
}

/* 25. overpricing costs time (fit/overpricing_time.py; RESULT test_invariants). T_ELAST = 0.10 is a LABELLED JUDGMENT,
   set between the two documented conversions of the analogs (about 0.09 time-given-sale, 0.15 sale clock); stated
   range 0.05-0.26. The band median is exact at or below model value and stretched by timeMult above it; the
   proceeds optimum (and with it the business score) reads neither theta nor the cost of delay; the note under
   the listing cards is written from the optimiser's own delay-inclusive objective */
{ const fs=require("fs"), path=require("path");
  const HTML=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
  const T=A.T_ELAST, TS=A.T_SMOOTH;
  ok(T===0.10&&T>=0.05&&T<=0.26,`T_ELAST ${T} is the 0.10 judgment, inside the stated range 0.05-0.26`);
  ok(TS===0.1,`T_SMOOTH ${TS}`);
  ok([[1,1],[.5,1],[0,1],[-1,1],[NaN,1],[2,0],[2,-1],[2,NaN],[1e-300,1]].every(([a,v])=>A.timeMult(a,v)===1),
     "timeMult is exactly 1 at or below value and for invalid inputs");
  ok(Math.abs(Math.log(A.timeMult(Math.E,1))-T*(1-TS/2))<1e-12,"timeMult = e^{T_ELAST (x - T_SMOOTH/2)} past the rounding zone");
  ok(Math.abs(Math.log(A.timeMult(Math.exp(TS/2),1))-T*TS/8)<1e-12,"timeMult = e^{T_ELAST x^2/(2 T_SMOOTH)} inside it");
  /* the page: rhoSell does not read the cost of delay; the note comes from optNote and keeps the range wording */
  ok(/s\.rhoSell=bestRatio\(s,0,0\);/.test(HTML)&&!/rhoSell=bestRatio\(s,0,s\.lamT\)/.test(HTML),"render computes rhoSell as bestRatio(s,0,0)");
  ok(/\$\("o_listnote"\)\.textContent=optNote\(s,r\.V,rSell,rKeep\)\.text;/.test(HTML),"the optimiser note is written by optNote");
  ok(HTML.indexOf("time to close depends on deal size, not on the ask")<0,"the old 'delay cost does not move either' note is gone");
  ok(/const tMedA=FT\.days\*out\.tMult;/.test(HTML)&&(HTML.match(/FT\.days/g)||[]).length===1,"FT.days is read exactly once in model() (the tMedA line)");
  ok(HTML.includes('id="o_t_pv"')&&HTML.includes('id="o_tstretch"')&&HTML.includes("fitted × judgment"),"tile tag and live stretch note present");
  ok(/b = \$\{T_ELAST\.toFixed\(2\)\}<\/b>, set by judgment/.test(HTML)&&/about 0\.09 on the time-given-sale scale \(about \$\{mktTxt\} if only the marketing leg\s+were stretched\) and 0\.15 on the sale-clock scale/.test(HTML)
     &&HTML.includes("const mktTxt=`${(0.09*(1-loiMed)).toFixed(2)}&ndash;${(0.10*(1-loiMed)).toFixed(2)}`;")&&!HTML.includes("36% of it), which the analogs")
     &&!/0\.07 on the time-given-sale scale|0\.07 \(time-given-sale scale\)/.test(HTML),
     "Data tab states b as a labelled judgment between the two conversions");
  ok(/Overpricing time multiplier[\s\S]{0,200}<td class="n" style="padding-right:18px">2<\/td>/.test(HTML)&&/\+ nDelta \+ nCat \+ nConf \+ nPeer \+ nPeerX \+ 11 \+ 2 \+ 1\s+\+ 4;/.test(HTML)&&!HTML.includes("the SBA tail factor (years 9-10"),"judgment inventory counts T_ELAST and T_SMOOTH (and THIN_W, competition_buyers; the SBA tail is fitted since October 2026)");
  /* a median business priced at the proceeds optimum scores 50 at every cost of delay */
  for(const ind of ["medical","rest","msp","mfg"]) for(const ern of [2e5,1e6,5e6]) for(const lamT of [0,900,4000]){
    const s={...median(ind,ern),lamT}, V=A.model({...s,ask:1}).V;
    ok(A.omniScore(A.model({...s,ask:V*A.bestRatio(s,0,0)}))===50,`median ${ind} ${ern}: business score 50 at $${lamT}/day`); }
  /* why rhoSell must not take lamT: once time reads the ask, a cost of delay lowers the delay-aware ask */
  { const s=median("rest",1.5e5); ok(A.bestRatio(s,0,4000)<A.bestRatio(s,0,0)-1e-3,"a cost of delay lowers the delay-aware ask"); }
  const EXO={grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false};
  /* the walk-away asks the Data tab quotes (75% kept, delay charged on the mean time to close): $900/day 1.17, 1.19, 1.26,
     1.20; $4,000/day 1.09, 1.16, 1.19, 1.20 for earnings $150k/$400k/$1.45M/$5M (1.15 at $400k and $4,000/day before
     round 9 pooled the medical industry's physicians' and dentists' cells; they were 1.13, 1.14, 1.15, 1.15 and
     1.08, 1.12, 1.14, 1.14 before the gap axis was read as Pepperdine states it, October 2026, third round). If another
     change moves them, update the Data-tab paragraph. */
  { const Q={900:["1.17","1.19","1.26","1.20"],4000:["1.09","1.16","1.19","1.20"]};
    [1.5e5,4e5,1.45e6,5e6].forEach((ern,i)=>{ const s={...EXO,ind:"medical",ern,rev:ern/0.24};
      for(const lam of [900,4000]){ const b=A.bestRatio(s,.75,lam);
        ok(b.toFixed(2)===Q[lam][i],`Data tab: walk-away ask at $${ern} and $${lam}/day ${b.toFixed(3)} (text says ${Q[lam][i]})`); } }); }
  /* the knife edge the Data tab quotes for the framework example: the cap wins from about 77% kept with no delay cost,
     78% at $900/day, 83% at $4,000/day (77.2 / 78.4 / 82.53 since round 10 added 621112 to the medical pool; 77.2 / 78.4 / 82.5
     since round 9 pooled the medical cells; 77.2 / 78.5 / 82.8
     since the gap axis was read as Pepperdine states it; 76.6 / 77.6 / 81.0 before) */
  { const ex={...EXO,ind:"medical",rev:6e6,ern:1.45e6};
    for(const [lam,pct] of [[0,77],[900,78],[4000,83]]){ let lo=.70,hi=.88;
      for(let k=0;k<12;k++){ const m=(lo+hi)/2; A.bestRatio(ex,m,lam)>1.45?hi=m:lo=m; }
      ok(Math.round(50*(lo+hi))===pct,`Data tab: patient-seller cap from ${(50*(lo+hi)).toFixed(1)}% kept at $${lam}/day (text says ${pct}%)`); } }
  /* small deals leave the cap at $900/day at theta .75 */
  ok(A.bestRatio({...EXO,ind:"medical",ern:1.5e5,rev:1.5e5/0.24},.75,900)<1.25,"small deal: the walk-away ask is interior");
  /* reference for the note under the listing cards, on a 0.005 grid (4x finer than bestRatio's): the local maxima of the
     objective at this share kept AND one 1% step of it either side (the cap counts if the objective rises into it), each
     valued at this share, with its distance from the walk-away ask and its dip toward it. The margins (0.95% vs 1%, 0.06
     vs 0.02, dip 3e-4 vs 1e-4 of value) absorb the coarse grid's resolution; inside them the note must agree exactly. */
  const noteRef=ss=>{
    const V=A.model({...ss,ask:1}).V, th=ss.theta, lam=ss.lamT, ms=[], xs=[];
    for(let k=0;k<=140;k++){ const m=.80+k*.005; ms.push(m); xs.push(A.model({...ss,ask:V*m})); }
    const Ut=t=>xs.map(x=>x.EVp+(1-x.PC)*t*x.V-lam*x.tMean), u=Ut(th), L=ms.length-1, jo=Math.round((ss.optRho-.80)/.005);
    const isMax=(v,j)=>j>0&&v[j]>=v[j-1]&&(j===L||v[j]>=v[j+1]), pk=[];
    for(const t of [th,th-.01,th+.01]) if(t>=0&&t<=1){ const v=t===th?u:Ut(t);
      for(let j=1;j<=L;j++) if(isMax(v,j)){ let lo=u[j], lv=v[j]; for(let q=Math.min(j,jo);q<=Math.max(j,jo);q++){ lo=Math.min(lo,u[q]); lv=Math.min(lv,v[q]); }
        /* vdepth: the dip toward the walk-away ask on the curve where it is a peak (the page's rule for a range) */
        pk.push({m:ms[j],u:u[j],here:t===th,depth:(u[j]-lo)/V,vdepth:(v[j]-lv)/V,d:Math.abs(ms[j]-ss.optRho)}); } }
    const U=m=>{ const x=A.model({...ss,ask:V*m}); return x.EVp+(1-x.PC)*th*x.V-lam*x.tMean; };
    return {V,pk,U,ms,u,uK:U(ss.optRho)};
  };
  const checkNote=(ss,n,tag)=>{
    const R=noteRef(ss), V=R.V, uK=R.uK;
    /* the range: shown exactly when another peak (here or one 1% step of theta away) is within 1% of value */
    /* "real": a dip of 0.01% of value toward the walk-away ask on the curve where it is a peak (the page reads it on its
       .02 grid, this reference on .005, so the two tests leave a margin either side of the rule) */
    /* ... or the walk-away ask one 1% step of the share kept away sits at it (it jumps there, however shallow the dip) */
    const jumps=m=>[ss.theta-.01,ss.theta+.01].some(t=>t>=0&&t<=1&&Math.abs(A.bestRatio(ss,t,ss.lamT)-m)<=.03);
    if(n.alt) ok(n.text.includes("close to a tie, so read the patient-seller price as a range")&&uK-n.alt.u<=.01*V*(1+1e-9)&&Math.abs(n.alt.m-ss.optRho)>.02
      &&R.pk.some(p=>Math.abs(p.m-n.alt.m)<=.025&&p.d>.015&&(p.vdepth>=.5e-4||jumps(p.m))),`range end ${n.alt.m.toFixed(3)} is a real peak within 1% ${tag}`);
    else ok(!/as a range/.test(n.text)&&!R.pk.some(p=>p.d>.06&&uK-p.u<=.0095*V&&p.vdepth>=2e-4),`no range only when no other real peak is within 1% ${tag}: ${n.text}`);
    /* and every real peak within 1% of value is inside the printed range, not only the best one (r6-core-1: the
       framework example's 1.20-1.26x left out the cap, 0.38% of value away) */
    { const g=/as a range, (\d\.\d\d)–(\d\.\d\d)× value/.exec(n.text), lo=g?+g[1]:ss.optRho, hi=g?+g[2]:ss.optRho;
      ok(R.pk.filter(p=>p.d>.06&&uK-p.u<=.0095*V&&p.vdepth>=2e-4).every(p=>p.m>=lo-.03&&p.m<=hi+.03),`every real peak within 1% of value is in the range ${tag}: ${n.text}`); }
    /* the flat top: only at the cap, printed rounded UP, and the printed ask and every fine-grid ask above it within 1% */
    if(n.flat!==null&&n.flat!==undefined){
      const above=R.ms.map((m,j)=>[m,R.u[j]]).filter(v=>v[0]>=n.flat-1e-9);
      ok(!n.alt&&A.capSet(ss.optRho)&&Math.abs(n.flat*100-Math.round(n.flat*100))<1e-9
        &&n.text.includes(`every ask from ${n.flat.toFixed(2)}× value up comes within 1% of value of the cap`)
        &&uK-R.U(n.flat)<=.01*V&&above.every(v=>uK-v[1]<=.01*V),`flat-top ask ${n.flat}: it and every ask above it within 1% ${tag}`);
      if(/There is no second peak/.test(n.text)) ok(!n.peak&&!R.pk.some(p=>p.here&&p.d>.03&&p.depth>3e-4),`'no second peak' only when there is none ${tag}`);
      else ok(!!n.peak&&n.text.includes(`another peak, at ${n.peak.m.toFixed(2)}× value`)&&uK-n.peak.u>.01*V
        &&R.pk.some(p=>p.here&&Math.abs(p.m-n.peak.m)<=.025&&p.depth>=.99e-4),`the other peak named beyond a tie is real ${tag}: ${n.text}`); }
    else ok(!/no second peak|another peak, at/.test(n.text),`no flat-top wording without a flat top ${tag}`);
  };
  for(const [ind,ern] of [["medical",1.45e6],["rest",1.5e5],["mfg",5e6],["msp",4e5],["prof",5e4]]){
    const s={...EXO,ind,ern,rev:ern/0.24}, V=A.model({...s,ask:1}).V, r1=A.model({...s,ask:V});
    const base=A.fitTiming(r1.Vbase,ind).days;
    for(const m of [0,0.3,0.6,0.9,0.999,1]){ const rm=A.model({...s,ask:V*m});
      ok(rm.tMed===base&&rm.tMult===1,`time unchanged at ${m}x value (${ind})`); }
    /* scan rho 0.5..3 in 0.001 steps: non-decreasing, small steps, t90/t180/t365 never rise */
    let prev=-Infinity,maxStep=0,mono=true,pq=[Infinity,Infinity,Infinity],monoQ=true;
    for(let k=0;k<=2500;k++){ const m=0.5+k*0.001, r=A.model({...s,ask:V*m});
      if(r.tMed<prev-1e-9) mono=false; if(prev>-Infinity) maxStep=Math.max(maxStep,r.tMed-prev); prev=r.tMed;
      const q=[r.t90,r.t180,r.t365]; if(q.some((v,j)=>v>pq[j]+1e-12)) monoQ=false; pq=q; }
    ok(mono,`tMed non-decreasing in the ask (${ind})`); ok(maxStep<0.5,`tMed steps under half a day per 0.001 of rho (${ind}): ${maxStep}`);
    ok(monoQ,`t90/t180/t365 non-increasing in the ask (${ind})`);
    ok(A.model({...s,ask:V*1.01}).tMed>base,`time strictly longer above value (${ind})`);
    const d=1e-6, dR=(A.model({...s,ask:V*(1+d)}).tMed-r1.tMed)/d, dL=(r1.tMed-A.model({...s,ask:V*(1-d)}).tMed)/d;
    ok(Math.abs(dR)<1&&Math.abs(dL)<1,`slope of tMed continuous (zero) at value (${ind}): ${dL} / ${dR}`);
    const el=Math.log(A.model({...s,ask:V*3}).tMed/A.model({...s,ask:V*1.5}).tMed)/Math.log(2);
    ok(Math.abs(el-T)<1e-9,`elasticity above the rounding zone is T_ELAST (${ind}): ${el}`);
    { const r2=A.model({...s,ask:V*2});
      ok(Math.abs(r2.tMed-r2.ft.days*A.timeMult(2*V,r2.V))<1e-9*r2.tMed,`tMed = band median x timeMult (${ind})`);
      ok(r2.ft.days===base&&r2.ft.loi===r1.ft.loi&&r2.betaT===r1.betaT,`band median, LOI leg and shape unchanged by the ask (${ind})`);
      /* the price block does not read the multiplier: same P_C, prices and value as the band-only curve */
      ok(r2.V===r1.V&&r2.Vbase===r1.Vbase&&Math.abs(r2.PC-A.fitClose(2*V,r2.V,undefined,r2.Vbase).p*(r2.thinF<1?r2.thinF:1))<1e-9,`P_C and value do not read the time multiplier (${ind})`); }
    for(const a of [1e-6,1,1e3,1e9,1e12]) ok(isFinite(A.model({...s,ask:a}).tMed),`finite at ask ${a} (${ind})`);
    /* a better business at the same ask is never slower: a higher model value narrows the gap */
    const better={rec:Math.min(1,s.rec+.1),cc:Math.max(.005,s.cc-.05),ret:Math.min(.99,s.ret+.03),plt:Math.max(.02,s.plt-.08),
      grw:Math.min(1.5,s.grw+.05),gm:Math.min(.97,s.gm+.03),own:Math.max(.02,s.own-.1),mgt:Math.min(.99,s.mgt+.1),fin:Math.min(1,s.fin+.1)};
    for(const k in better){ const a0=A.model({...s,ask:1.4*V}), a1=A.model({...s,[k]:better[k],ask:1.4*V});
      ok(a1.tMed<=a0.tMed+1e-9,`better ${k} never lengthens the time to close at a fixed ask (${ind})`); }
    for(const lam of [0,900,4000]) for(const th of [0,.2,.75]){
      const tag=`(${ind}, theta ${th}, $${lam}/day)`, ru=A.bestRatio(s,th,lam);
      ok(ru<=A.RHO_MAX+1e-9,`utility optimum within RHO_MAX ${tag}`);
      ok(ru<=A.bestRatio(s,th,0)+1e-9,`a cost of delay never raises the recommended ask ${tag}`);
      /* the note under the two listing cards describes the cards actually shown */
      const ss={...s,theta:th,lamT:lam}; ss.rhoSell=A.bestRatio(ss,0,0); ss.optRho=ru;
      const rSell=A.model({...ss,ask:V*ss.rhoSell}), rKeep=A.model({...ss,ask:V*ss.optRho});
      const n=A.optNote(ss,V,rSell,rKeep), U=x=>x.EVp+(1-x.PC)*th*x.V-lam*x.tMean;
      ok(U(rKeep)>=U(rSell)-1e-6*Math.abs(U(rSell)),`walk-away card at least as good on the optimiser's objective ${tag}`);
      ok(!/[−-]\$/.test(n.text)&&!/NaN|undefined|Infinity|(?<![\d.])1 days/.test(n.text),`no negative money, NaN or '1 days' in the note ${tag}: ${n.text}`);
      const same=A.money(V*ss.optRho)===A.money(V*ss.rhoSell);
      if(same) ok(n.kind==="same",`same figure: 'agree' note ${tag}`);
      else if(ss.optRho<ss.rhoSell) ok(n.kind==="lower"&&n.text.includes(A.money(V*ss.optRho))&&!n.text.includes("higher price")&&rKeep.tMean<=rSell.tMean&&/sooner/.test(n.text),
        `a lower walk-away ask is described as lower and faster ${tag}: ${n.text}`);
      else ok(n.kind==="higher"&&n.text.includes("higher price"),`a higher walk-away ask is described as higher ${tag}`);
      ok(n.coin===(!same&&U(rKeep)-U(rSell)<.01*V)&&(!n.coin||/coin toss/.test(n.text)),`coin-toss wording on the delay-inclusive gain ${tag}`);
      /* the patient-seller range (anchoring_realization) is shown exactly when ANOTHER PEAK (a local maximum of the
         objective, here or one 1% step of theta away, apart from the walk-away ask's own; the cap counts if the objective
         rises into it) is within 1% of value - never because a scan stopped somewhere, and also when both cards agree */
      if(th>0) checkNote(ss,n,tag);
    }
  }
  /* the default state (framework example, 75% kept, $900/day): one step of the share kept away (74%) the walk-away ask is
     1.20x, a real peak within 0.04% of value of the 1.26x walk-away ask, and the cap is another, 0.37% of value below it
     (0.38% before round 9 pooled the medical cells)
     with a real dip between: the range runs 1.20-1.50x (it read 1.20-1.26x, leaving out the cap, until the sixth skeptic
     round, r6-core-1). Before the gap axis was read as Pepperdine states it the range ran 1.1x-1.50x */
  { const ex={...EXO,ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,theta:.75,lamT:900}, V=A.model({...ex,ask:1}).V;
    ex.rhoSell=A.bestRatio(ex,0,0); ex.optRho=A.bestRatio(ex,.75,900);
    const n=A.optNote(ex,V,A.model({...ex,ask:V*ex.rhoSell}),A.model({...ex,ask:V*ex.optRho}));
    ok(n.kind==="higher"&&!!n.alt&&/as a range, 1\.20–1\.50× value/.test(n.text)&&/1\.50× value \(the cap the console puts on the ask\) within 0\.37%/.test(n.text),
       `framework example: patient-seller range shown, from the 1.20x peak to the cap (${n.text})`);
    checkNote(ex,n,"(framework example)"); }
  /* a walk-away ask at the cap with an objective that climbs all the way there: no range (there is no second peak, and
     1.35x was only where the old scan stopped); the note says how flat the top is instead. (Home services at $300k and
     its peer medians, 100% kept; the manufacturing case this used peaks at 1.48x since the gap axis was read as
     Pepperdine states it.) */
  { const P=A.peerMedians("home",3e5,3e5/.24), ex={...EXO,ind:"home",ern:3e5,rev:3e5/.24,grw:P.grw,gm:P.gm,rec:P.rec,ret:P.ret,theta:1,lamT:900}, V=A.model({...ex,ask:1}).V;
    ex.rhoSell=A.bestRatio(ex,0,0); ex.optRho=A.bestRatio(ex,1,900);
    const n=A.optNote(ex,V,A.model({...ex,ask:V*ex.rhoSell}),A.model({...ex,ask:V*ex.optRho}));
    ok(ex.optRho>A.RHO_MAX-.02&&!n.alt&&!/as a range/.test(n.text)&&n.flat>1.28&&n.flat<1.38&&/every ask from 1\.3\d× value up comes within 1% of value of the cap/.test(n.text),
       `home services $300k, 100% kept: no false range, flat top from ${n.flat} (${n.text})`);
    /* and the converse: at 90% kept the framework example's asks of 1.40-1.50x are within 1%, but there is no second peak */
    const e9={...EXO,ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,theta:.9,lamT:900}, V9=A.model({...e9,ask:1}).V;
    e9.rhoSell=A.bestRatio(e9,0,0); e9.optRho=A.bestRatio(e9,.9,900);
    const n9=A.optNote(e9,V9,A.model({...e9,ask:V9*e9.rhoSell}),A.model({...e9,ask:V9*e9.optRho}));
    ok(!n9.alt&&n9.flat>1.3&&n9.flat<1.42,`framework example at 90% kept: flat top from ${n9.flat}, no range`); }
  const noteAt=(s0,th,lam)=>{ const t={...s0,theta:th,lamT:lam}, V=A.model({...t,ask:1}).V; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,th,lam);
    return {t,o:t.optRho,n:A.optNote(t,V,A.model({...t,ask:V*t.rhoSell}),A.model({...t,ask:V*t.optRho}))}; };
  /* a walk-away flip between ~1.31x and ~1.47x on one 1% step of theta, NEITHER end at the cap (the second peak is not
     assumed to be the cap): the range covers both peaks on both sides of the flip (the thetas and the cost of delay moved,
     and the lower peak rose from about 1.22x, when the gap axis was read as Pepperdine states it; both flips moved one
     step of theta down when round 9 pooled home services' two cells) */
  for(const [s0,ths,lam] of [[{ind:"home",rev:4e5,ern:9e4,grw:.06,gm:.5,rec:.3,cc:.16,ret:.82,plt:.40,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5},[.88,.89],500],
                             [{ind:"home",rev:326000,ern:55000,grw:.66,gm:.77,rec:.59,cc:.07,ret:.70,plt:.24,own:.95,mgt:.36,fin:.14,yrs:6,buyers:440},[.91,.92],500]]){
    const out=ths.map(th=>noteAt(s0,th,lam));
    ok(Math.abs(out[1].o-out[0].o)>.15&&out.every(({o,n})=>o<A.RHO_MAX-.02&&n.alt&&Math.min(o,n.alt.m)<1.33&&Math.max(o,n.alt.m)>1.44&&/as a range/.test(n.text)),
       `walk-away flip ${out.map(v=>v.o.toFixed(3)).join(" -> ")} below the cap: the range on both sides`);
    for(const v of out) checkNote(v.t,v.n,`(flip at theta ${v.t.theta})`); }
  /* at the cap, the flat-top ask is rounded up and checked (framework example at 85% kept; auto repair $1.2M/$300k at
     90%). Both named an interior peak more than 1% below the cap until the gap axis was read as Pepperdine states it;
     since then no profile scanned (16 industries x 6 sizes x 2 quality profiles x 5 shares kept x 5 costs of delay, and
     variants of FAN_S and PEN_MAX) has a real interior peak beyond a tie at the cap, so both now read 'no second peak',
     and checkNote still checks the naming wherever it occurs */
  { const f=noteAt({...EXO,ind:"medical",rev:6e6,ern:1.45e6},.85,900), a=noteAt({...EXO,ind:"auto",rev:1.2e6,ern:3e5},.9,900);
    for(const [v,fl] of [[f,1.24],[a,1.24]]){ const n=v.n, V=A.model({...v.t,ask:1}).V;
      const U=m=>{ const x=A.model({...v.t,ask:V*m}); return x.EVp+(1-x.PC)*v.t.theta*x.V-v.t.lamT*x.tMean; };
      ok(v.o>A.RHO_MAX-.02&&!n.alt&&!n.peak&&/There is no second peak/.test(n.text)
         &&n.flat===fl&&U(v.o)-U(fl)<=.01*V&&U(v.o)-U(fl-.01)>.01*V,`${v.t.ind} at ${v.t.theta}: no second peak, flat from ${n.flat} (${n.text})`);
      checkNote(v.t,n,`(${v.t.ind} at ${v.t.theta})`); } }
  /* a walk-away ask that jumps between 1% steps of the share kept to a peak barely separated from the plateau (a dip
     under 0.01% of value): the range shows on both sides of the jump (fuzz, third round: an MSP at 98% and 99% kept) */
  { const s0={ind:"msp",st:"AL",franchise:false,rev:1052100,ern:264500,grw:0.61955,gm:0.66279,rec:0.44291,cc:0.67859,ret:0.58744,plt:0.38511,
      own:0.14,mgt:0.92,fin:0.96,yrs:12,buyers:55,budget:69039,lamT:3100}, out=[.98,.99].map(th=>noteAt(s0,th,3100));
    ok(out[1].o-out[0].o>.1&&out.every(v=>v.n.alt&&/as a range/.test(v.n.text)),
       `walk-away jump ${out.map(v=>v.o.toFixed(3)).join(" -> ")} over a shallow dip: the range on both sides`);
    for(const v of out) checkNote(v.t,v.n,`(shallow jump at theta ${v.t.theta})`); }
  /* every industry near the knife edge: the note's three readings (range, named peak, no second peak) against the reference */
  for(const ind of Object.keys(A.IND)) for(const [th,lam] of [[.85,900],[.9,4000],[.95,900]]){
    const P=A.peerMedians(ind,4e5,4e5/.24), v=noteAt({...EXO,ind,ern:4e5,rev:4e5/.24,grw:P.grw,gm:P.gm,rec:P.rec,ret:P.ret},th,lam);
    checkNote(v.t,v.n,`(${ind}, theta ${th}, $${lam}/day)`); }
}

/* 26. competition (fit/competition_buyers.py, integrated in part): ENG_SHARE replaces the 0.34 engaged share and is
   calibrated to IBBA offers per closed deal; the premium is unchanged (COMP_H re-expressed); the thin-pool factor keeps
   its Poisson shape with a smooth cap at 1 (the fit's negative-binomial factor is not adopted); BUYERS unchanged */
{ const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const F=A.MODELS.fitted.competition, SRC=HTML.slice(HTML.lastIndexOf("<script>"));
  const MOD=SRC.slice(0,SRC.indexOf("/* ============ bar helpers")).replace(/MODELS\.fitted\.competition=\{.*\};\n/,"");
  ok(F.eng_share>=.13&&F.eng_share<=.23&&F.eng_share>=F.eng_share_spec_range[0]&&F.eng_share<=F.eng_share_spec_range[1],"eng_share fitted and inside its NB specification range");
  ok(F.nb_r>0&&F.nb_r>=F.nb_r_spec_range[0]&&F.nb_r<=F.nb_r_spec_range[1]&&F.kappa>=0&&F.kappa<=.1,"nb_r and kappa metadata in range");
  ok(["eng_share_se","eng_share_ci95","eng_share_pln","refit_when","source","calibration","nb_thin_pool","strategic_premium","kappa_ci95_ibba","score_effect_at_integration"].every(k=>F[k]!==undefined),"competition metadata fields present");
  ok(A.ENG_SHARE===F.eng_share&&A.COMP_K===F.kappa&&near(A.COMP_H,3*A.ENG_SHARE/.34,1e-15),"ENG_SHARE read from the fit; COMP_K the judgment 0.03; COMP_H re-expressed");
  ok(!/nb_r|eng_share_pln|NB_R|pAnyOffer/.test(MOD),"the model reads neither the NB dispersion nor the PLN scale (NB thin-pool factor not adopted)");
  ok(!/\*\s*0\.34\s*;/.test(MOD)&&(MOD.match(/\*ENG_SHARE;/g)||[]).length===3,"nEng, nEngRef and nPool all use ENG_SHARE");
  /* the smooth cap */
  { let mono=true, prev=-1, maxLift=0, kink=0;
    for(let x=0;x<=1.2+1e-12;x+=1e-4){ const g=A.capOne(x); if(g<prev-1e-15||g>1||g<x-1e-15&&x<=1) mono=false; prev=g; if(x<=1) maxLift=Math.max(maxLift,g-x); }
    for(const x0 of [1-A.THIN_W,1]){ const h=1e-6, dl=(A.capOne(x0)-A.capOne(x0-h))/h, dr=(A.capOne(x0+h)-A.capOne(x0))/h; kink=Math.max(kink,Math.abs(dl-dr)); }
    ok(mono,"capOne monotone, never above 1, never below the ratio");
    ok(A.capOne(1)===1&&A.capOne(1.7)===1&&A.capOne(1-A.THIN_W)===1-A.THIN_W&&A.capOne(.3)===.3,"capOne exactly 1 at and above 1, the ratio itself below 1-THIN_W");
    ok(kink<1e-4,`capOne has no kink at either end of the blend (${kink})`);
    ok(near(maxLift,F.thin_cap_max_lift,5e-4)&&F.thin_cap_w===A.THIN_W,`capOne lifts the ratio by at most ${maxLift.toFixed(4)} (stored ${F.thin_cap_max_lift})`); }
  /* band centres: median businesses at Vbase = 250k .. 15.8M, every industry */
  const medB=(ind,ern)=>{ const I=A.IND[ind],m=A.typMargin(ind,ern);
    return {ind,rev:ern/m,ern,...A.peerMedians(ind,ern,ern/m),yrs:6,buyers:I.buyers,st:null,franchise:false,ask:1e6}; };
  const atV=(ind,V)=>{ let lo=Math.log(2e3),hi=Math.log(2e8);
    for(let i=0;i<50;i++){ const m=(lo+hi)/2; if(A.model(medB(ind,Math.exp(m))).Vbase<V) lo=m; else hi=m; }
    const t=medB(ind,Math.exp((lo+hi)/2)); t.ask=A.REF_RATIO*A.model(t).V; return t; };
  const BK=["<500K","500K-1M","1M-2M","2M-5M","5M-50M"], R=F.nb_r, inds=Object.keys(A.IND);
  const ztNB=mu=>mu/(1-Math.pow(R/(R+mu),R));
  const half=[1,0], quarter=[1,0], mm=(a,v)=>{a[0]=Math.min(a[0],v);a[1]=Math.max(a[1],v);};
  const byInd={}; let p1ok=true, s1ok=true, cmp=0, thinOK=true;
  F.band_centres.forEach((V,b)=>{ let zt=0, mu=0, zp=0;
    for(const ind of inds){ const t=atV(ind,V), r=A.model(t);
      zt+=ztNB(r.nEngRef); mu+=r.nEngRef; zp+=r.nEngRef/(1-Math.exp(-r.nEngRef)); (byInd[ind]=byInd[ind]||[]).push(ztNB(r.nEngRef));
      const p=R/(R+r.nEngRef), p0=Math.pow(p,R), pAny=1-p0, share1=R*p0*(1-p)/(1-p0);
      if(!(pAny>=.36&&pAny<=.82)) p1ok=false; if(!(share1>=.19&&share1<=.65)) s1ok=false;
      cmp=Math.max(cmp,Math.abs(r.compPrem)); if(r.thinF!==1) thinOK=false;
      mm(half,A.model({...t,buyers:t.buyers*.5}).thinF); mm(quarter,A.model({...t,buyers:t.buyers*.25}).thinF); }
    zt/=inds.length; mu/=inds.length; zp/=inds.length; const k=BK[b];
    ok(Math.abs(zt-F.offers_per_closed_deal_lower_bound[k])<=.40,`CALIBRATION ${k}: NB-implied offers per closed deal ${zt.toFixed(3)} within 0.40 of IBBA's ${F.offers_per_closed_deal_lower_bound[k]}`);
    ok(Math.abs(zt-F.offers_per_closed_deal_bandfree_fit[k])<=2*F.offers_per_closed_deal_bandfree_se[k],`CALIBRATION ${k}: within 2 se of the band-free fit`);
    ok(near(zt,F.offers_per_closed_deal_model[k],.01)&&near(zp,F.offers_per_closed_deal_poisson_shape[k],.01),`stored offers per closed deal ${k} match the live build (${zt.toFixed(3)}, Poisson ${zp.toFixed(3)})`);
    if(b===0) ok(near(mu,F.expected_offers_typical_pool[0],.01),`typical pool under $500K expects ${mu.toFixed(3)} offers`);
    if(b===4) ok(near(mu,F.expected_offers_typical_pool[1],.01),`typical pool at $5M+ expects ${mu.toFixed(3)} offers`); });
  ok(inds.every(k=>byInd[k].every((v,j)=>j===0||v>byInd[k][j-1])),"implied offers per closed deal rise with deal size in every industry");
  ok(p1ok&&s1ok,"at a typical pool the NB chance of any offer is in [0.36,0.82] and the one-offer share in [0.19,0.65] (IBBA 0.26-0.48)");
  /* exactly zero since the engagement floor went: this business's offers and the typical pool's are on one basis */
  ok(cmp<1e-12&&thinOK,`median business at a typical pool: |compPrem| ${cmp.toExponential(2)} is zero and thinF exactly 1`);
  ok(near(half[0],F.thin_half_pool[0],.006)&&near(half[1],F.thin_half_pool[1],.006)&&near(quarter[0],F.thin_quarter_pool[0],.006)&&near(quarter[1],F.thin_quarter_pool[1],.006),
     `stored thin-pool ranges match the live build: half ${half.map(v=>v.toFixed(3))}, quarter ${quarter.map(v=>v.toFixed(3))}`);
  ok(half[0]>=.55&&half[1]<=.88&&quarter[0]>=.28&&quarter[1]<=.63,"half the typical pool keeps 0.55-0.88 of P_C, a quarter 0.28-0.63");
  /* the premium is exactly the pre-change formula; nEngRef reads neither the pool nor quality; thinF reads no quality input */
  { let sd=7; const rn=()=>{ sd=(sd*16807)%2147483647; return (sd-1)/2147483646; }; let worst=0, refOK=true, qOK=true;
    for(let i=0;i<60;i++){ const ind=inds[Math.floor(rn()*inds.length)], ern=Math.exp(Math.log(5e4)+rn()*Math.log(400)), t=medB(ind,ern);
      for(const k of ["rec","ret","gm","own","mgt","fin","plt"]) t[k]=Math.min(.98,Math.max(.02,t[k]+(rn()-.5)*.6));
      t.buyers=5+Math.floor(rn()*595); const r=A.model(t), X=r.nEng/A.ENG_SHARE, Xr=r.nEngRef/A.ENG_SHARE;
      const old=Math.min(.14,Math.max(-.08,.030*Math.log((3+X*.34)/(3+Xr*.34)))); worst=Math.max(worst,Math.abs(r.compPrem-old));
      if(Math.abs(A.model({...t,buyers:t.buyers*2+3}).nEngRef-r.nEngRef)>1e-12) refOK=false;
      const q1=A.model({...t,own:.1,mgt:.9,rec:.9,fin:.95}), q2=A.model({...t,own:.9,mgt:.1,rec:.1,fin:.1});
      if(Math.abs(q1.nEngRef-q2.nEngRef)>1e-12||Math.abs(q1.thinF-q2.thinF)>1e-12) qOK=false; }
    ok(worst<1e-12,`competition premium equals the pre-change formula (max diff ${worst.toExponential(2)})`);
    ok(refOK&&qOK,"typical pool reads neither the pool nor quality; thinF reads no quality input"); }
  /* SCORE PINS (regenerate from the live build when P_C, E[price] or the Omni score change) */
  { const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:25,st:null,franchise:false,ask:3.24e6};
    const at=(API,b)=>{ const s={...ex,buyers:b}, r=API.model(s); r.inputs=s; return {r,sc:API.omniScore(r)}; };
    const a25=at(A,25), a40=at(A,40), a65=at(A,65), a50=at(A,50);
    /* regenerated in round 9, when pooling the medical industry's physicians' and dentists' cells raised the example's
       value to $4.31M and so put the $3.24M ask further below it (0.7695, 0.5209, 2; 31 and 41; 41/10 and 25/1 before), and
       in round 10, when the mental health specialists' cell (621112) joined the pool and the value became $4.28M
       (0.7724, 0.5255 in round 9) */
    ok(near(a25.r.thinF,.7721,1e-4)&&near(a25.r.PC,.5250,1e-4)&&Math.abs(a25.sc-1)<=1,`example at 25 buyers: thinF ${a25.r.thinF.toFixed(4)}, PC ${a25.r.PC.toFixed(4)}, score ${a25.sc} (pinned 0.7721, 0.5250, 1)`);
    ok(Math.abs(a40.sc-22)<=1&&Math.abs(a65.sc-32)<=1&&a65.r.thinF===1&&a50.r.thinF===1,`example at 40 and 65 buyers scores ${a40.sc} and ${a65.sc} (pinned 22, 32 against optimum-priced peers); thinF 1 from the typical 50 up`);
    /* IND.buyers sensitivity: the judgment typical pool the thin-pool factor is measured against */
    const sens=[40,60].map(tb=>{ const B=A.loadWith([["anchor:3.10, buyers:50,","anchor:3.10, buyers:"+tb+","]]); return [at(B,25).sc,at(B,40).sc]; });
    ok(Math.abs(sens[0][1]-32)<=1&&Math.abs(sens[1][1]-16)<=1&&Math.abs(sens[0][0]-1)<=1&&Math.abs(sens[1][0]-1)<=1,
       `IND.buyers sensitivity: example at 40/25 buyers scores ${sens[0][1]}/${sens[0][0]} at a typical pool of 40, ${sens[1][1]}/${sens[1][0]} at 60 (pinned 32/1, 16/1)`);
    /* median businesses at half and three quarters of the typical pool */
    const SE=F.score_effect_at_integration, rng={.5:[99,0],.75:[99,0],1:[99,0]};
    for(const ind of inds) for(const ern of [2e5,1e6,4e6]){ const t=median(ind,ern), V=A.model({...t,ask:1}).V;
      for(const f of [.5,.75,1]){ const s={...t,ask:A.REF_RATIO*V,buyers:Math.max(1,Math.round(t.buyers*f))}, r=A.model(s); r.inputs=s; const sc=A.omniScore(r);
        rng[f][0]=Math.min(rng[f][0],sc); rng[f][1]=Math.max(rng[f][1],sc); } }
    /* the stored figures are the record at integration (the Data tab says later model changes move them); the live pins
       were regenerated when the gap axis was read as Pepperdine states it (third round): half pool 1-23 and three quarters
       16-41 (1-25 and 19-43 before) */
    ok(SE.median_half_pool.join()==="1,25"&&SE.median_three_quarter_pool.join()==="19,43","the integration record is kept as it was");
    ok(Math.abs(rng[.5][0]-1)<=2&&Math.abs(rng[.5][1]-23)<=2&&Math.abs(rng[.75][0]-16)<=2&&Math.abs(rng[.75][1]-41)<=2,
       `MEDIAN-BUSINESS PIN: half pool ${rng[.5]}, three quarters ${rng[.75]} (pinned 1,23 and 16,41)`);
    /* priced at REF_RATIO against optimum-priced peers a median business scores 48 (test 6): at a typical pool the thin-pool factor changes nothing */
    ok(rng[1][0]===48&&rng[1][1]===48,`median businesses at a typical pool score 48 at REF_RATIO, as without a pool effect (${rng[1]})`); }
  /* the sensitivity panel's buyer-pool row: no negative effect anywhere, smooth through the typical pool */
  { const ex={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,st:null,franchise:false,ask:3.24e6};
    const row=b=>A.sensitivity({...ex,buyers:b}).find(v=>v.k==="buyers"); let okAll=true; const dps=[];
    for(const b of [5,10,20,30,40,44,46,48,50,52,54,56,60,65,80,120,300,600]){ const v=row(b); if(!(v.dP>=-1e-12&&v.dE>=-1e-6&&isFinite(v.dE))) okAll=false; if(b>=44&&b<=56) dps.push(v.dP); }
    ok(okAll,"buyer-pool sensitivity row: more buyers never lower P_C or proceeds");
    /* the row is the step it names, 25% more buyers (R5-2): monotone and continuous through the typical pool, and zero for
       P_C once the pool is typical or deeper */
    const cont=[44,46,48,49.5,50,52].every(b=>Math.abs(row(b+.01).dP-row(b).dP)<1e-3);
    ok(dps.every((v,j)=>j===0||v<=dps[j-1]+1e-12)&&cont&&row(52).dP<1e-9,`buyer-pool row changes smoothly through the typical pool (${dps.map(v=>v.toFixed(4))})`);
    const t=A.model({...ex,buyers:50}), h=1e-4, f=b=>A.model({...ex,buyers:b}).thinF;
    ok(Math.abs((f(50)-f(50-h))/h-(f(50+h)-f(50))/h)<1e-3,"thinF has no kink at the typical pool"); }
  /* BUYERS unchanged (judgment) but for the individual's factor, calibrated in October 2026 (fit/buyer_factors.py); the
     strategic-over-financial premium with both present stays inside Pepperdine/GF's range */
  { const mf={}; for(const b of A.BUYERS) mf[b.k]=b.mf;
    ok(mf.str===1.18&&mf.adj===1.14&&mf.add===1.12&&mf.pep===1.06&&mf.fo===1.02&&mf.eta===.98&&mf.ind===A.MODELS.fitted.buyers.mf_ind&&mf.ind===.97&&mf.mbo===.86&&A.PHI===.38,"buyer multiple factors and PHI unchanged; the individual's calibrated (0.97)");
    const syn={}; for(const b of A.BUYERS) syn[b.k]=b.syn; let sum=0,n=0;
    for(const V of [5e6,8e6,1.5811e7,3e7]) for(const ind of inds){ const t=atV(ind,V), r=A.model(t), x=r.synE/t.ern;
      const full=k=>mf[k]+Math.min(A.PHI*syn[k]*x,.40);
      sum+=.5*(full("str")+full("adj"))/(.64*full("pep")+.36*full("add"))-1; n++; }
    const prem=sum/n;
    ok(prem>=.08&&prem<=.18&&near(prem,F.strategic_premium.model_full_presence,.01),`strategic-over-financial premium with both present ${prem.toFixed(3)} (stored ${F.strategic_premium.model_full_presence})`); }
  /* Data tab */
  ok(HTML.includes("Buyer pool: expected offers, and how a thin pool lowers the closing probability")&&HTML.includes("calibrated scale, judgment shape"),"Data tab: fitted row for the buyer pool");
  ok(HTML.includes("Not adopted: the fit&rsquo;s negative-binomial thin-pool factor"),"Data tab: the NB thin-pool factor is listed as not adopted");
  ok(HTML.includes("<code>IND</code> buyers is also the typical pool that the thin-pool factor"),"Data tab: the IND row names the typical pool");
  /* ENG_SHARE is CALIBRATED everywhere: its row badge, the ledger, and (like FAN_S) no tally */
  { const i=HTML.indexOf("const nFit = "), j=HTML.indexOf('let h="";',i), NF=HTML.slice(i,j);
    ok(i>0&&j>i&&!/ENG_SHARE|eng_share|mf_ind|FAN_S/.test(NF.split("/* the CALIBRATED constants")[0])
       &&/\/\* the CALIBRATED constants, FAN_S, ENG_SHARE \(offers per closed deal, IBBA\), the individual buyer's multiple/.test(NF),"nFit does not count ENG_SHARE (calibrated, like FAN_S and the individual buyer's factor)"); }
  ok(/Buyer pool: expected offers, and how a thin pool lowers the closing probability\s*&nbsp;<span class="st adj">calibrated<\/span>/.test(HTML)
     &&HTML.includes("(the offer share that sets its scale is now calibrated to IBBA)")&&!HTML.includes("sets its scale is now fitted"),"ENG_SHARE badged calibrated in its row and in the ledger");
  ok(/Thin-pool cap<div class="muted"[^>]*>THIN_W/.test(HTML),"Data tab counts THIN_W as judgment");
  ok(HTML.includes("Pepperdine 2016, se")&&HTML.includes("GF Data&rsquo;s add-on/platform"),"Data tab: buyer-factor consistency check");
}

/* 27. quality weights (fit/quality_weights.py; rec and grw checked by fit/quality_weights_v2.py, RESULT test_invariants):
   metadata and text only. own and mgt keep their fitted weights (mgt flagged weak), the other seven keep weight 1;
   the stored evidence must keep agreeing with what the Data tab says about it */
{ const fs=require("fs"), path=require("path");
  const HTML=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
  const W=A.MODELS.fitted.quality_weights, D=A.MODELS.value.quality_band.dimensions, C=W.checked, zs=v=>v[0]/v[1];
  let s2=0,ss=0; for(const k in A.QW.w){ s2+=(A.QW.w[k]/A.QW.norm)**2; ss+=A.QW.w[k]**2; }
  ok(near(s2,1,1e-12)&&near(A.QW.norm,Math.sqrt(ss),1e-12),"QW: composite standard normal, norm = root sum of squared weights");
  ok(D.length===9&&D.every(k=>A.QW.w[k]>0&&A.QW.w[k]<=2),"QW: every weight in (0, 2]");
  ok(W.fitted.length+W.judgment.length===9&&D.every(k=>W.fitted.includes(k)!==W.judgment.includes(k)),"QW: fitted and judgment partition the nine dimensions");
  ok(D.filter(k=>W[k]!==undefined).sort().join()===W.fitted.slice().sort().join(),"QW: fitted = exactly the dimensions with a stored weight");
  ok(Array.isArray(W.weak)&&W.weak.every(k=>W.fitted.includes(k))&&W.weak.includes("mgt")&&!W.weak.includes("own")&&typeof W.weak_note==="string","QW: management depth flagged weak, owner dependence not");
  for(const k of W.judgment) ok(A.QW.w[k]===1&&W[k]===undefined,`QW: ${k} is judgment and keeps weight 1`);
  for(const k of W.fitted) ok(A.QW.w[k]===W[k]&&W.se[k]>0&&W.se[k]<0.5,`QW: ${k} uses its fitted weight, se below the prior sd`);
  ok(W.judgment.includes("rec")&&W.judgment.includes("grw"),"QW: recurring revenue and growth stay judgment (relative weight not identified)");
  /* growth: positive direction in EF sale prices, mainly a discount on declining businesses; level not identified */
  ok(C.grw.ef_range[0]<1&&C.grw.ef_range[1]>1&&C.grw.ratio[1]<1&&C.grw.ratio[2]>1,"growth: EF range and the ratio interval both include an equal share");
  ok(C.grw.oos===true&&C.grw.ef_all_specs_positive===true&&zs(C.grw.ef_12m)>1.96&&C.grw.ef_12m_own_sd[0]>0,"growth: positive in every EF specification, significant on twelve-month windows, adds out of sample");
  { const Q=C.grw.ef_quintiles.effect, S=C.grw.ef_quintiles.se, mid=Q[2]-Q[0], top=Math.max(Math.abs(Q[3]-Q[2]),Math.abs(Q[4]-Q[2]));
    ok(Q.length===5&&Q[0]===0&&Q[1]<Q[2]&&Q[2]/S[2]>1.96&&top<mid/3,`growth: the shrinking fifths are discounted (${mid}), the fastest-growing fifths add little (${top})`);
    ok(zs(C.grw.ef_report_decreasing_vs_stable.window)<-1.96&&Math.abs(zs(C.grw.ef_report_increasing_vs_stable.window))<1.96,"growth: EF's own tables discount declining businesses, no significant premium for growing ones, on listed earnings"); }
  /* recurring revenue: ask premium significant, sale premium not, difference not significant either */
  ok(C.rec.oos===false&&C.rec.ratio[1]<1&&C.rec.ratio[2]>1,"recurring revenue: no out-of-sample value, ratio interval includes an equal share");
  ok(Math.abs(zs(C.rec.ef))<1.96&&Math.abs(zs(C.rec.flippa_auctions))<1.96,"recurring revenue: sale-price premium not significant (EF sales, Flippa auctions)");
  ok(zs(C.rec.ef_ask)>1.96&&zs(C.rec.flippa_asks)>1.96,"recurring revenue: asking-price premium significant (EF last ask, Flippa final asks)");
  ok(Math.abs(zs(C.rec.ef_sale_minus_ask))<1.96,"recurring revenue: the sale-minus-ask difference is not significant either");
  ok(C.mgt.oos===false&&C.mgt.ratio[1]<1&&C.mgt.ratio[2]>1,"management depth: weak (no out-of-sample value, ratio includes an equal share)");
  ok(C.q[2]>0.05,"equal relative weights across the nine measured dimensions are not rejected");
  /* the model: a business at every peer median sits at the band midpoint; one sd moves qz by sign*w/norm */
  const I=A.IND.medical;
  const med={ind:"medical",rev:6e6,ern:1.45e6,yrs:6,buyers:I.buyers,franchise:false,st:null,...A.peerMedians("medical",1.45e6,6e6),ask:3.24e6};
  const r0=A.model(med);
  ok(near(r0.qz,0,1e-12)&&near(r0.qFactor,1,1e-6),"QW: a business at every peer median sits at the band midpoint");
  const dz={rec:A.PEER_SD.rec,grw:A.PEER_SD.grw,gm:A.PEER_SD.gm,ret:A.PEER_SD.ret,cc:A.PEER_SD.cc,plt:A.PEER_SD.plt};
  for(const k of Object.keys(dz)){ const sg=(k==="cc"||k==="plt")?-1:1, r1=A.model({...med,[k]:med[k]+dz[k]});
    ok(near(r1.qz-r0.qz,sg*A.QW.w[k]/A.QW.norm,1e-9),`QW: one sd of ${k} moves the composite by w/norm`); }
  ok(A.model({...med,rec:med.rec+.2}).V>r0.V&&A.model({...med,grw:med.grw+.1}).V>r0.V,"QW: more recurring revenue or growth raises value (growth: direction confirmed; recurring revenue: judgment)");
  const jw=W.judgment.map(k=>A.QW.w[k]/A.QW.norm); ok(jw.every(x=>near(x,jw[0],1e-15)),"QW: the seven judgment dimensions share one per-sd effect");
  /* Data tab: the reviewers' corrected wording, and the evidence template renders the stored numbers */
  for(const bad of ["asking prices only","none in sale prices","partly lost in negotiation","no reachable data prices them","not identifiable there"])
    ok(!HTML.includes(bad),`Data tab / comments no longer say "${bad}"`);
  ok(HTML.includes("not significant either")&&HTML.includes("driven mainly by declining businesses being discounted")&&HTML.includes("growth above zero adds little"),"Data tab: corrected recurring-revenue and growth wording");
  ok(HTML.includes("Management depth is <b>weakly supported</b>")&&HTML.includes("<b>Management depth is weakly supported</b>"),"Data tab: management depth marked weak in Quality positioning and in Fitted from public data");
  { const a=HTML.indexOf("${QWC ? (C=>{ const Q=C.grw.ef_quintiles.effect"), b=HTML.indexOf("})(QWC) : `",a);
    ok(a>0&&b>a,"Data tab: evidence template found");
    if(a>0&&b>a){ const txt=new Function("C","return ("+HTML.slice(a+9,b+1)+")(C)")(C);
      ok(!/NaN|undefined|Infinity/.test(txt),"Data tab: evidence template renders no NaN/undefined");
      ok(txt.includes("2,644 online-business sales")&&txt.includes("419 of them final asks")&&txt.includes("multiples 13% and 6% lower")&&txt.includes("within\n        3% of it")
         &&txt.includes("10% less than")&&txt.includes("2% less, not significant")&&txt.includes("0.60&ndash;0.94")&&txt.includes("0.09 to 2.59")
         &&txt.includes("0.42 of an equal share")&&txt.includes("-1.92, se 2.13")&&txt.includes("-0.25, se 0.17"),"Data tab: evidence template quotes the stored numbers"); } }
}

/* 28. review fixes (Oct 2026) */
{ const EXF={ind:"medical",rev:6e6,ern:1.45e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,ask:3.24e6};
  /* 28a. the figures bestRatio's comment quotes: interior-peak margin over the cap (share of value) and the flips */
  const margin=(API,th,lam)=>{ const V=API.model({...EXF,ask:1}).V, U=m=>{ const r=API.model({...EXF,ask:V*m}); return r.EVp+(1-r.PC)*th*r.V-lam*r.tMean; };
    let b=-Infinity; for(let m=1.0;m<=1.40+1e-9;m+=.002) b=Math.max(b,U(m)); return (b-U(A.RHO_MAX))/V; };
  const m9=margin(A,.75,900), m0=margin(A,.75,0);
  ok(Math.abs(m9-.0038)<.0003&&Math.abs(m0-.0024)<.0003,`interior peak wins by ${(m9*100).toFixed(2)}% of value at $900/day, ${(m0*100).toFixed(2)}% with no delay cost (comment: 0.38%, 0.24%)`);
  ok(margin(A,.781,900)>0&&margin(A,.788,900)<0&&margin(A,.769,0)>0&&margin(A,.775,0)<0,"theta flip near 0.785 at $900/day and 0.772 with no delay cost");
  const S=f=>A.loadWith([["const FAN_S=0.80;","const FAN_S="+f+";"]]);
  ok(margin(S(.94),.75,900)>0&&margin(S(.955),.75,900)<0&&margin(S(.886),.75,0)>0&&margin(S(.899),.75,0)<0,"FAN_S flip near 0.95 at $900/day and 0.89 with no delay cost");
  /* 28b. the share of closings at the ceiling is continuous: no 1/48 steps on a 0.05% change in the ask */
  { let worst=0, prev=null; for(let a=2e6;a<9e6;a*=1.0005){ const c=A.model({...EXF,ask:a}).capShare; if(prev!==null) worst=Math.max(worst,Math.abs(c-prev)); prev=c; }
    ok(worst<.002,`capShare moves at most ${worst.toFixed(5)} per 0.05% of ask (was 1/48 = 0.0208)`);
    const r1=A.model({...EXF,ask:4110942}), r2=A.model({...EXF,ask:4112998});
    ok(Math.abs(r1.capShare-r2.capShare)<.002,`capShare ${r1.capShare.toFixed(4)} -> ${r2.capShare.toFixed(4)} on +0.05% ask`);
    let sd=5, jumps=0; const rn=()=>{ sd=(sd*16807)%2147483647; return (sd-1)/2147483646; }, inds=Object.keys(A.IND);
    for(let i=0;i<300;i++){ const ind=inds[Math.floor(rn()*inds.length)], ern=Math.exp(Math.log(3e4)+rn()*Math.log(1000)), mg=.05+rn()*.45;
      const s={ind,ern,rev:ern/mg,grw:-.3+rn()*.8,gm:.1+rn()*.8,rec:rn(),cc:.01+rn()*.8,ret:.1+rn()*.85,plt:.02+rn()*.95,own:.05+rn()*.9,
        mgt:.05+rn()*.9,fin:.1+rn()*.85,yrs:6,buyers:5+Math.floor(rn()*595),st:null,franchise:false};
      const V=A.model({...s,ask:1}).V; s.ask=V*(.6+rn()*1.6);
      for(const k of ["ask","ern","buyers","own"]){ const t={...s,[k]:s[k]*1.001}; if(Math.abs(A.model(t).capShare-A.model(s).capShare)>.01) jumps++; } }
    ok(jumps===0,`capShare never jumps by more than 1 point on a 0.1% input change (${jumps} jumps)`);
    const hi=A.model({...EXF,ask:1e12}).capShare;
    ok(A.model({...EXF,ask:1e3}).capShare===1&&hi>0&&hi<.5&&near(hi,A.model({...EXF,ask:1e9}).capShare,1e-9),`capShare is 1 at a token ask and settles at ${hi.toFixed(3)} once the 1.5x-value ceiling binds`); }
  /* 28c. expected offers are continuous through the search-fund and MBO earnings windows and the upper edge */
  { const s0={ind:"rest",rev:360e3,buyers:600,grw:-.25,gm:.12,rec:0,cc:.70,ret:.45,plt:.95,own:.95,mgt:.08,fin:.14,yrs:6,st:null,franchise:false};
    for(const e of [45000,90000,8.32e6]){ let worst=0;
      for(const f of [.9998,.9999,1,1.0001]){ const at=x=>{ const s={...s0,ern:x}, V=A.model({...s,ask:1}).V; return A.model({...s,ask:1.1*V}).nEng; };
        worst=Math.max(worst,Math.abs(at(e*f*1.0002)/at(e*f)-1)); }
      ok(worst<1e-3,`expected offers move ${(worst*100).toFixed(3)}% on a 0.02% earnings change near $${e}`); } }
  /* 28d. category scores held to 1..99, like the Omni score */
  { const c1=A.model({ind:"staff",rev:72778,ern:10303,own:.14,mgt:.92,fin:.74,grw:.50,gm:.14,rec:.07,cc:.67,ret:.72,plt:.63,yrs:6,buyers:175,st:null,franchise:false,ask:116917}).cats;
    const c2=A.model({ind:"prof",rev:84.7e6,ern:49.8e6,own:.95,mgt:.08,fin:.14,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,yrs:6,buyers:445,st:null,franchise:false,ask:256e6}).cats;
    ok(c1["Operational transferability"]===99&&c2["Operational transferability"]===1,`transferability held at 99 and 1 (${c1["Operational transferability"]}, ${c2["Operational transferability"]})`);
    let sd=9, bad=0; const rn=()=>{ sd=(sd*16807)%2147483647; return (sd-1)/2147483646; }, inds=Object.keys(A.IND);
    for(let i=0;i<400;i++){ const ind=inds[Math.floor(rn()*inds.length)], ern=Math.exp(Math.log(5e3)+rn()*Math.log(1e4));
      const s={ind,ern,rev:ern/(.05+rn()*.6),grw:-.6+rn()*2.1,gm:.02+rn()*.95,rec:rn(),cc:.005+rn()*.9,ret:.05+rn()*.94,plt:.02+rn()*.97,
        own:[.95,.72,.42,.14][Math.floor(rn()*4)],mgt:[.08,.36,.66,.92][Math.floor(rn()*4)],fin:[.14,.45,.74,.96][Math.floor(rn()*4)],yrs:1+Math.floor(rn()*12),
        buyers:5+Math.floor(rn()*595),st:null,franchise:false,ask:ern*(1+rn()*8)};
      for(const v of Object.values(A.model(s).cats)) if(!(v>=1&&v<=99&&Number.isInteger(v))) bad++; }
    ok(bad===0,`category scores in 1..99 across 400 random businesses (${bad} outside)`); }
  /* 28e. the price tile names the ceiling, not "the ask" */
  { const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
    ok(HTML.includes("pc(r.capShare)+' at the ask ceiling'")&&!HTML.includes("pc(r.capShare)+' at the ask':''"),"o_val says 'at the ask ceiling'"); }
}

/* 29. the 25 confirmed logic-audit defects (AUDIT_FINDINGS.md), one pin each */
{ const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,
            buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  const prep=o=>{ const s={...FX,...o}, V=A.model({...s,ask:1}).V; s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,s.theta,s.lamT); return {s,V}; };
  /* #6/#13/#19: the delay cost is charged on the MEAN time to close, everywhere the utility is computed */
  ok(/lamT\*r\.tMean;\};/.test(HTML)&&/const U=x=>x\.EVp\+\(1-x\.PC\)\*s\.theta\*x\.V-s\.lamT\*x\.tMean;/.test(HTML)
     &&/recV\.U=r\.EVp\+\(1-r\.PC\)\*theta\*r\.V-lamT\*\(r\.tMean\+days\)-c;/.test(HTML)&&/lamT\*\(ru\.tMean\+days\)-c\}/.test(HTML)
     &&!/lamT\*\(?\w+\.tMed\b/.test(HTML),"#6: bestRatio, optNote and optimize charge lambda x E[T]");
  { const {s,V}=prep({}), r=A.model(s), b=A.optimize(s,r,s.budget,s.lamT,s.theta);
    ok(b.U.t===b.U.r.tMean&&b.V.t===b.V.r.tMean&&near(b.U.U,b.U.proceeds+(1-b.U.PC)*s.theta*b.U.r.V-s.lamT*(b.U.r.tMean+b.U.days)-b.U.c,1e-6),"#6: optimiser records carry E[T] and U uses it");
    ok(/E\[T\]=t_\{\\\\text\{med\}\}\\\\,\\\\frac\{\\\\pi\/\\\\beta\}\{\\\\sin\(\\\\pi\/\\\\beta\)\}/.test(HTML)&&HTML.includes(">Expected days<")&&!HTML.includes(">Total days<"),"#6: E[T] typeset in eq_t; the card tile is 'Expected days'"); }
  /* #9: the business score takes the pool out like the ask: a median business at half the typical pool still scores 50,
     and the framework example keeps its business score however few buyers are contacted below the typical pool */
  for(const ind of ["medical","rest","saas","home"]) for(const ern of [1.5e5,1.45e6]){
    const t=median(ind,ern), typ=A.IND[ind].buyers||50, s={...t,buyers:Math.max(5,Math.round(typ/2))}, V=A.model({...s,ask:1}).V, r=A.model({...s,ask:V*A.REF_RATIO});
    ok(A.businessScore(s,r,A.bestRatio(s,0,0)).score===50,`#9: median ${ind} ${ern} at half the typical pool keeps business score 50`); }
  { const sc=b=>{ const s={...FX,buyers:b}, r=A.model(s); return A.businessScore(s,r,A.bestRatio(s,0,0)).score; }, s65=sc(65);
    ok([10,20,30,40,50].every(b=>sc(b)===s65),`#9: framework example business score ${s65} at 10-65 buyers`); }
  /* #3/#12/#17: the reprice equalises the gap, not P_C; the table shows dP_C and says why it moves */
  { const go=b=>{ const {s}=prep({buyers:b}), r=A.model(s); return A.interventionTable(s,r).find(x=>x.k==="outreach").dP; };
    const d25=go(25), d65=go(65);
    ok(d25>.10&&Math.abs(d65)<1e-12,`#3: outreach moves P_C ${(d25*100).toFixed(1)} pts at 25 buyers, 0 at 65`);
    ok(HTML.includes('<th class="n">ΔP<sub>C</sub></th>')&&HTML.includes("the closing probability still moves with the buyer pool")
       &&!HTML.includes("and with it the closing probability, is the same in every row")&&HTML.includes("is not zero by construction"),"#3: dP_C column restored, footnote and caption corrected"); }
  /* #11/#15: the second card's subtitle at the defaults: the same changes repriced, never 'less elapsed time and spend' */
  { const {s}=prep({}), r=A.model(s), b=A.optimize(s,r,s.budget,s.lamT,s.theta), uRho=b.U.keys.includes("reprice")?s.optRho:s.rhoSell, n=A.optCardNote(s,b,s.rhoSell,uRho);
    ok(n.kind==="reprice"&&n.text.startsWith(`The same changes, repriced to ${uRho.toFixed(2)}× instead of ${s.rhoSell.toFixed(2)}×`)
       &&/less likely to close for a higher price if it closes/.test(n.text)&&/takes (a day|\d+ days) longer from start to close/.test(n.text)&&!/less elapsed time|spends/.test(n.text)
       &&n.text.includes("value retained if the process fails"),`#11: default card subtitle (${n.text})`);
    ok(HTML.includes("optCardNote(s,best,rhoSell,uRho).text")&&!HTML.includes("in exchange for ${dProc<0"),"#11: the card uses optCardNote"); }
  /* #14/#18: the lower note prints the time value and the net separately */
  { const {s,V}=prep({theta:0,lamT:4000,rev:8e5,ern:1.5e5,ask:4.5e5}), rS=A.model({...s,ask:V*s.rhoSell}), rK=A.model({...s,ask:V*s.optRho}), n=A.optNote(s,V,rS,rK);
    const tv=s.lamT*(rS.tMean-rK.tMean);
    ok(n.kind==="lower"&&n.text.includes(`worth ${A.money(tv)} at $4,000 a day`)&&n.text.includes(`Net of the proceeds given up, that is worth ${A.money(n.gain)} to this owner`)
       &&tv>n.gain,`#14: lower note: time value ${A.money(tv)}, net ${A.money(n.gain)} (${n.text})`); }
  /* #5/#25: no 2% floor; the equation carries the tail, the size-interpolated base and the thin-pool factor */
  { const V=A.model({...FX,ask:1}).V, p=[28,30,50,100].map(m=>A.model({...FX,ask:V*m}));
    /* the tail decays from the open bucket's knot (200% over value) since the gap axis was read as Pepperdine states it, so
       P_C reaches 2% further out than 30x */
    ok(p[0].PC>p[1].PC&&p[1].PC>p[2].PC&&p[2].PC>p[3].PC&&p[3].PC<.02&&p[1].EVp>p[2].EVp,`#5: P_C keeps falling past 28x (${p.map(x=>x.PC.toExponential(2)).join(", ")})`);
    ok(HTML.includes("1-${(1-PEN_MAX).toFixed(2)}\\\\,e^{-k(g-${GAP_CDF.g[GAP_CDF.g.length-1]})}")&&HTML.includes("\\\\tau(n)&=\\\\operatorname{cap}_1")&&HTML.includes("b(V)&=${tp(bB,1)}")
       &&!HTML.includes("pinned at its floor")&&!/clamp\(base\*\(1-pen\),\.02/.test(HTML),"#5/#25: eq_p typesets tail, base and thin pool; floor gone"); }
  /* #16: the P_C badge and captions name the thin-pool factor */
  ok(HTML.includes('id="o_pc_pv"')&&/pv\.innerHTML="<i><\/i>"\+\(j\?"aggregate × judgment":"aggregate"\)/.test(HTML)&&!HTML.includes("conditions on deal size and asking gap only")
     &&!HTML.includes("conditioning on deal size and price\ngap alone"),"#16: P_C badge and captions mention the thin pool");
  /* #1/#2: quality row says 'among peers'; the price rows name the realised-price fan */
  ok(HTML.includes("percentile among peers, placed inside the measured")&&!HTML.includes("percentile of the measured spread")
     &&!HTML.includes("across the measured spread of value")&&HTML.includes("across the realised-price fan"),"#1/#2: multiple-table labels");
  /* #4: the Data tab no longer claims quality-independence at a fixed dollar ask, which is false */
  { const a=A.model({...FX,own:.95,ask:4.5e6}), b=A.model({...FX,own:.10,ask:4.5e6});
    ok(b.PC>a.PC&&HTML.includes("At the same ask relative to its model value, the closing probability does not depend on")&&!HTML.includes("wildly different owner dependence receive the same number"),"#4: Data tab P_C claim"); }
  /* #7: the curve's accessible name is conditional on closing */
  ok(!HTML.includes('aria-label="Cumulative probability of closing over time"')&&HTML.includes('$("tcurve").setAttribute("aria-label"'),"#7: tcurve aria-label");
  /* #8: every fitted state effect can be selected */
  { const m=HTML.match(/const STNAMES=(\{[^}]*\});/), S=JSON.parse(m[1]), E=Object.keys(A.MODELS.risk.state_effects);
    ok(E.every(k=>k in S)&&Object.keys(S).every(k=>E.includes(k)),`#8: STNAMES covers all ${E.length} state effects`); }
  /* #10: model value is not a financial-buyer baseline */
  ok(!HTML.includes("over the financial baseline")&&!HTML.includes("above this line is strategic premium")&&HTML.includes("over model value}")
     &&!HTML.includes("relative to the financial-buyer baseline\n"),"#10: buyer labels");
  /* #20: the SDE margin range is read live (20-30% at $200k SDE) */
  { const m=Object.keys(A.IND).map(k=>A.typMargin(k,2e5)); ok(!HTML.includes("18&ndash;35%")&&Math.round(Math.min(...m)*100)===20&&Math.round(Math.max(...m)*100)===30,"#20: margin range live, 20-30%"); }
  /* #21: one aggregate count for the tally and the badge; the tail is fitted (October 2026), so it is counted with the
     fitted tables and has no judgment row */
  ok((HTML.match(/\$\{nAgg\}/g)||[]).length===2&&!HTML.includes("17 parameters</span>")&&/\+ 2   \/\* the size x age interaction/.test(HTML)
     &&!/\+ 1    \/\* the SBA tail factor/.test(HTML)&&/\+ 4;   \/\* the price-gap penalty scale PEN_MAX/.test(HTML)&&!HTML.includes("<tr><td>SBA tail factor<div")
     &&HTML.includes("+ MODELS.risk.tail.by_band.ratio.length"),"#21: tallies agree");
  /* #22: the centring row at a business actually at its peer medians reads in range */
  { const I=A.IND.prof, rv=158950/A.typMargin("prof",158950), p={ind:"prof",rev:rv,ern:158950,...A.peerMedians("prof",158950,rv),
      yrs:6,buyers:(I.buyers||50)}, V=A.model({...p,ask:1}).V, d=A.model({...p,ask:V}).dsum;
    ok(Math.abs(d)<.03&&HTML.includes("mMed.dsum.toFixed(3)"),`#22: judgment stack at the peer medians ${d.toFixed(4)}`); }
  /* #23: the 15 quarters named correctly */
  ok(!/2020Q1(&ndash;|-|–)2023Q3/.test(HTML)&&A.MODELS.fitted.ttc_shape.source.includes("2020Q1-2021Q4, 2022Q2-2023Q3 and 2025Q4"),"#23: quarter labels");
  /* #24: the value equation states its units */
  ok(HTML.includes("\\\\ln\\\\hat P_{\\\\$000}")&&HTML.includes("ln(price, $000)"),"#24: eq_v in thousands");
}

/* 30. round-1 logic-audit fixes (AUDIT_FINDINGS.md, R1-n), one pin each */
{ const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,
            buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  const V=A.model({...FX,ask:1}).V;
  /* R1-1: PEN_MAX is labelled judgment where it acts, and it is load-bearing: the walk-away flip sits near 0.42 */
  ok(/thin=r\.thinF<\.9995, gap=r\.fc\.pen>0, j=thin\|\|gap;/.test(HTML)&&HTML.includes("<b>The ${PEN_MAX} scale is a judgment</b>")
     &&HTML.includes("<tr><td>Price-gap penalty and base-rate ramp")&&HTML.includes("Size of the price-gap penalty (PEN_MAX = ${PEN_MAX})")
     &&HTML.includes("and on the size of the price-gap penalty (a judgment scale)"),"R1-1: PEN_MAX and the size ramp labelled judgment");
  { const at=pm=>A.loadWith([["const PEN_MAX=.45;","const PEN_MAX="+pm+";"]]).bestRatio(FX,.75,900);
    ok(at(.414)>1.45&&at(.422)<1.30&&A.PEN_MAX===.45,"R1-1: the walk-away ask flips to the cap near PEN_MAX 0.418 (text: about 0.42)"); }
  /* R1-2: scenarios are prices if it closes, with the no-sale chance beside them */
  ok(HTML.includes("Price if it closes · ${pc(1-r.PC)} chance of no sale")&&(HTML.match(/percentile of closings/g)||[]).length===3
     &&HTML.includes('row("Bear sale"')&&!HTML.includes("Outcome distribution"),"R1-2: scenario labels");
  /* R1-3, R1-18: badges say when judgment enters the value, the multiple and the risk */
  ok(/const j=Math\.abs\(r\.qFactor-1\)>\.005/.test(HTML)&&HTML.includes('id="o_msv_pv"')&&HTML.includes('id="o_mult_pv"')
     &&HTML.includes('pv.className="pv f"; pv.innerHTML="<i></i>fitted";')&&HTML.includes("× the average acquisition loan"),"R1-3/R1-18: dynamic provenance badges (the risk tile's tail is fitted)");
  /* R1-4, R1-5: buyers paid at most the ask ceiling and closing on the gap to their own value */
  { const r=A.model(FX);
    ok(r.buyers.every(b=>b.Pj<=Math.min(b.Vj,r.ceil)*(1+1e-9))&&r.best.k==="eta"&&r.top.k==="str","R1-4/R1-5: the search fund is pursued first at the default (the strategic premium sits above the ask)"); }
  /* R1-6: the 7(a) cap is named above $5M / 0.85 of model value */
  ok(HTML.includes("const capped=R.loan_share*r.V>R.loan_range[1];")&&HTML.includes("the risk shown is for that note, not for financing the whole price"),"R1-6: capped SBA note named");
  /* R1-7: the prime level moves no risk figure, and the page says so */
  { const B=A.loadWith([['"prime":7.0,','"prime":9.0,']]);
    ok(B.model(FX).risk.p===A.model(FX).risk.p&&HTML.includes("so the prime level moves no model figure; it sets the loan rate in the broker tools"),"R1-7: prime cancels and the Data tab says so"); }
  /* R1-8, R1-30: the level's position and the loan-size reversal are generated, not asserted */
  ok(!/upper part of the combined|shipped level is in the upper part/.test(HTML)&&HTML.includes("starts=R.age_edges.filter(m=>m<=capM)")
     &&!HTML.includes("the hazard gap closes by year 6"),"R1-8/R1-30: SBA level and size-gap wording");
  /* R1-9: the corpus AUC is labelled as the admin-window metric */
  ok(HTML.includes("admin-window CV AUC 0.820 &rarr; 0.828 with 6-digit and state effects together"),"R1-9: admin-window AUC labelled");
  /* R1-10: the default-off case where the retained value works against the walk-away programme */
  { const s={...FX,theta:.3,lamT:4000}; s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,.3,4000);
    const r=A.model(s), b=A.optimize(s,r,s.budget,s.lamT,s.theta), u=b.U.keys.includes("reprice")?s.optRho:s.rhoSell, n=A.optCardNote(s,b,s.rhoSell,u);
    const ret=x=>(1-x.PC)*s.theta*x.r.V, dRet=ret(b.U)-ret(b.V);
    ok(dRet<0?(/works against it/.test(n.text)&&!/pays only through the 30% of value retained/.test(n.text)):true,`R1-10: retained value named in its true direction (dRet ${Math.round(dRet)}): ${n.text}`); }
  /* R1-11: the coin-toss rule is 1% of value, not of |U| */
  { const s={ind:"prof",rev:6e5,ern:1.5e5,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,theta:.5};
    const Vp=A.model({...s,ask:1}).V;
    ok([1000,1200,1400].every(l=>{ const t={...s,lamT:l}; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,.5,l);
      const n=A.optNote(t,Vp,A.model({...t,ask:Vp*t.rhoSell}),A.model({...t,ask:Vp*t.optRho})); return n.coin===(n.kind!=="same"&&n.gain<.01*Vp); }),"R1-11: coin flag follows 1% of value at $1,000-$1,400 a day"); }
  /* R1-12: the binding-ask note is quantitative and keyed on the ceiling, not the sign of the gap */
  ok(HTML.includes("if(r.askBinds&&share<.25){")&&HTML.includes("passes through '+(share<.005?'almost none (under 1%)':'only about '+pc(share))")&&!HTML.includes("if(r.askBinds&&over<0){"),"R1-12: binding-ask note");
  /* R1-13: net days on the mean time to close */
  { const s={...FX,rhoSell:A.bestRatio(FX,0,0)}, r=A.model(s), it=A.interventionTable(s,r), rep=it.find(o=>o.k==="reprice"), r1=A.model(A.applyAll(s,r,["reprice"]));
    ok(Math.abs(rep.dTnet-(rep.days+r1.tMean-r.tMean))<1e-9,"R1-13: the reprice row's net days use E[T]"); }
  /* R1-14: inverted sensitivity rows named for their direction */
  ok(A.sensitivity(FX).map(o=>o.n).filter(n=>/Less customer concentration|Less channel concentration|Asking price, 5% lower/.test(n)).length===3,"R1-14: sensitivity row names");
  /* R1-15: the earnings input is SDE; EBITDA benchmarks are converted */
  ok(HTML.includes(">Normalized earnings (SDE)</label>")&&!HTML.includes("SDE / EBITDA")&&HTML.includes('const lmmS=e2s("mfg",1.5e6), ulmmS=e2s("mfg",3.5e6);'),"R1-15: SDE input and converted benchmarks");
  /* R1-16, R1-17, R1-19, R1-20: accessible shares, honest interval label, precise k, valued terms */
  ok(HTML.includes("${pc(r.t90)} close within 90 days")&&HTML.includes("fitted band here, 80")&&HTML.includes("k=${GAP_TAIL_K.toPrecision(3)}")
     &&HTML.includes("e_i=${r.fv.indEff.toFixed(4)}")&&HTML.includes("A_{\\\\max}=${AMAX.toFixed(2)}")&&HTML.includes("\\\\kappa=${r.compK.toFixed(2)}"),"R1-16/17/19/20: equation and label precision");
  { const r=A.model(FX), co=A.MODELS.value.coefficients, m=FX.ern/FX.rev;
    const lp=A.MODELS.value.intercept+co.ln_sde*Math.log(FX.ern/1e3)+co.hinge_sde*r.fv.hinge+co.ln_gross*Math.log(FX.rev/1e3)+co.margin_c*m+co.yr_c*(2026-2015)+co.ind_eff*r.fv.indEff;
    ok(Math.abs(Math.exp(lp)*1e3/r.fv.rawPoint-1)<1e-9,"R1-20: eq_v with the printed h, m, e_i and y reproduces the raw point"); }
  /* R1-21/24: the stack-bounds row names the floor that binds */
  ok(HTML.includes("multiple held to max(0.90×, 0.42× base)–1.85× base"),"R1-21/24: stack-bounds row");
  /* R1-22/29: no 'risen every year'; the trend is generated from the series */
  ok(!/risen every year/.test(HTML)&&HTML.includes("const dips=ys.filter((y,i)=>i>0&&+y>2021&&TS[y]<TS[ys[i-1]]);"),"R1-22/29: termination trend from the series");
  /* R1-25, R1-26, R1-27, R1-28, R1-33, R1-34 */
  ok(!HTML.includes('"below the middle"')&&HTML.includes('"lower part of the range"'),"R1-25: quality-band grammar");
  ok(!HTML.includes("Conditions on deal size and price gap only")&&!HTML.includes("conditions on price gap and nothing else"),"R1-26: P_C conditioning claims");
  ok(!HTML.includes("28% above the median from $500K"),"R1-27: E[T] premium is interpolated");
  ok(HTML.includes("the hinge alone improved both cross-validated fit and error")&&HTML.includes("${V.v2_comparison.cv_r2_log}"),"R1-28: hinge credited with its own gain");
  ok(HTML.includes("one of the calibration's sources: BizBuySell")&&!HTML.includes("the fit's own target"),"R1-33: self-audit target label");
  ok(!HTML.includes("The two agree: <b>r = +0.887</b>")&&HTML.includes("const D={23:2.30,42:3.00,51:2.70,54:2.30,62:2.20,71:2.00,72:1.80,81:2.10}"),"R1-34: cross-check computed live");
  /* R1-31, R1-32: tallies */
  ok(HTML.includes("Object.values(V.fan_quantiles||{}).filter(v=>v!==1).length")&&HTML.includes("new Set(Object.values(R.pif.sector||{})).size")
     &&HTML.includes('filter(v=>typeof v==="number").length')&&HTML.includes("estimated from data: transactions, plus listing and survey tables"),"R1-31/32: tallies");
}

/* ---- 31. time-to-close band medians fitted to the IBBA histograms (fit/time_to_close_medians.py) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const TM=A.MODELS.fitted.ttc_medians, K=[2.5e5,Math.sqrt(5e5*1e6),Math.sqrt(1e6*2e6),Math.sqrt(2e6*5e6),Math.sqrt(5e6*5e7)];
  ok(TM&&TM.bands.join()===A.MODELS.close_and_timing.time_to_close.bands.join()&&TM.listing.length===5&&TM.loi.length===5,"ttc medians: one per IBBA band, same order");
  ok(K.every((v,i)=>Math.abs(A.fitTiming(v,"medical").months-TM.listing[i])<1e-9&&Math.abs(A.fitTiming(v,"medical").loi-TM.loi[i])<1e-9),"ttc medians: fitTiming reads the fitted listing and LOI medians at each band centre");
  ok(TM.listing.every((v,i)=>i===0||v>TM.listing[i-1])&&TM.loi.every((v,i)=>i===0||v>TM.loi[i-1]),"ttc medians: larger deals take longer, band by band");
  ok(TM.listing.every((v,i)=>Math.abs(v-TM.published_listing[i])<=4*TM.listing_se[i]+.5)
     &&TM.published_listing.join()===A.MODELS.fitted.ttc_medians.bands.map(b=>A.MODELS.close_and_timing.time_to_close.median_months_listing_to_close_recent[b]).join(),
     "ttc medians: within reach of IBBA's published figures, which stay in MODELS for comparison");
  ok(TM.loqo_gain_per_deal.listing[0]>0&&TM.loqo_gain_per_deal.loi[0]>0&&TM.temporal_gain_per_deal.listing[1]===TM.temporal_gain_per_deal.listing[2],"ttc medians: adopted only on an out-of-sample gain");
  /* the size-order quirk the Data tab quantifies: the share closed by day t may rise with size only past ~18 months,
     by at most 0.7 pts (1.4 with the published medians) */
  const rise=B=>{ let worst=0, wt=0, first=Infinity;
    for(let t=30;t<=2000;t+=10){ let lo=Infinity;
      for(let lv=Math.log(5e4);lv<=Math.log(3e7);lv+=.01){ const ft=B.fitTiming(Math.exp(lv),"medical"), F=1/(1+Math.pow(t/ft.days,-ft.beta));
        lo=Math.min(lo,F); if(F-lo>worst){worst=F-lo; wt=t;} if(F-lo>1e-4) first=Math.min(first,t); } }
    return {worst:worst*100,wt,first}; };
  const now=rise(A), pub=rise(A.loadWith([["const TM=MODELS.fitted.ttc_medians;","const TM=null;"]]));
  ok(now.worst<.7&&now.worst>.6&&now.wt>=800&&now.wt<=1000&&now.first>=500&&pub.worst>1.3&&pub.worst<1.45,
     `ttc medians: residual size-order rise ${now.worst.toFixed(2)} pts near ${now.wt} d from day ${now.first}; published ${pub.worst.toFixed(2)}`);
  ok(HTML.includes("at most 0.7 pts, near 900 days, against 1.4 pts with the published")&&HTML.includes("by under one point"),"ttc medians: the quirk is described as computed");
  /* texts no longer call the median a published lookup */
  ok(!HTML.includes("published size-band lookup")&&!HTML.includes("the median is still the IBBA band median")&&!HTML.includes("Median pinned to the band median")
     &&!HTML.includes("The median is the IBBA band median")&&!HTML.includes("Median is a size-band lookup")&&!HTML.includes("The median stays on the band figure"),"ttc medians: no stale 'lookup' claims");
  ok(HTML.includes('<span class="pv f" id="o_t_pv"><i></i>fitted</span>')&&HTML.includes('pv.innerHTML="<i></i>"+(j?"fitted × judgment":"fitted");'),"ttc medians: the tile badge says fitted");
  { const i=HTML.indexOf("const nFit = "), j=HTML.indexOf('let h="";',i);
    ok(HTML.slice(i,j).includes("((MODELS.fitted.ttc_medians||{}).listing||[]).length")&&HTML.includes("const nAgg = 2 + Object.keys(C.close_probability.valuation_gap_distribution).length"),"ttc medians: counted as fitted; the aggregate count is read from the tables"); }
  ok(Math.abs(A.fitTiming(4e5,"medical").days-A.fitTiming(4e5,"medical").months*30.44)<1e-9,"ttc medians: days = months x 30.44");
}

/* ---- 32. round-2 audit fixes (AUDIT_FINDINGS round 2, verified at 0f1fa9b) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  const V0=A.model({...FX,ask:1}).V;
  /* R2-1: each buyer's EV is P_E x P_C,j x softmin(V_j, ceiling), and the page prints that formula and the capped price */
  { const r=A.model(FX);
    ok(r.buyers.every(b=>Math.abs(b.Pj-A.softMin(b.Vj,r.ceil))<1e-6&&Math.abs(b.EV-b.PE*b.PCj*b.Pj)<1e-6),"R2-1: EV_j = P_E P_C softmin(V_j, ceiling)");
    ok(HTML.includes("EV_j=P_{E,j}\\\\,P_{C,j}\\\\,\\\\operatorname{softmin}\\\\big(V_j,\\\\;\\\\bar a\\\\,c_{\\\\text{ask}}\\\\big)")&&HTML.includes("at this ask</span>")
       &&HTML.includes("this ask caps what it pays at }")&&HTML.includes("A(\\\\tfrac{\\\\bar a}{W})"),"R2-1: eq_b, eq_a, the table and 'pays most' show the cap"); }
  /* R2-2: the fan's anchoring reads the effective ask, so past RHO_MAX x value the price if it closes is flat; asks below
     about 1.4x value are untouched; the optimiser never keeps an ask above RHO_MAX x its value */
  { const at=m=>A.model({...FX,ask:V0*m});
    ok([2,3,5].every(m=>Math.abs(at(m).Vmean/at(2).Vmean-1)<1e-9&&Math.abs(at(m).Vreal/at(2).Vreal-1)<1e-9)&&Math.abs(at(1.7).Vmean/at(2).Vmean-1)<1e-5,"R2-2: E[P | close] and the median price flat from 2x value (within 1e-5 from 1.7x: the soft minimum saturates exponentially)");
    ok([.6,.9,1.05,1.2].every(m=>Math.abs(at(m).askEff/(V0*m)-1)<1e-9)&&Math.abs(at(1.35).askEff/(V0*1.35)-1)<1e-5,"R2-2: the effective ask is the ask to 1e-9 below 1.2x, 1e-5 at 1.35x");
    ok(at(2).PC<at(1.6).PC&&at(2).tMed>at(1.6).tMed,"R2-2: past the cap a higher ask still costs closing probability and time");
    const s={...FX,ask:2*V0,theta:.95}; s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,s.theta,s.lamT);
    const b=A.optimize(s,A.model(s),s.budget,s.lamT,s.theta);
    ok(b.U.keys.includes("reprice")&&b.V.keys.includes("reprice"),"R2-2: an ask at 2x value is repriced by both programmes"); }
  /* R2-3: the held-out Poisson benchmark is labelled for what it is, and the console's own pairing is reported */
  { const H=A.MODELS.fitted.competition.heldout_loglik_per_deal;
    ok(!("poisson_same_scale" in H)&&H.poisson_own_scale>H.poisson_console_pairing&&H.nb>H.poisson_own_scale&&Math.abs(H.poisson_console_pairing-H.poisson_old_034)<.01
       &&HTML.includes("for what the thin-pool factor uses, the Poisson shape at the negative"),"R2-3: held-out benchmarks named and the console pairing shown"); }
  /* R2-4: the days-on-market self-audit row explains why it reads off; 213 days now, 207 with the published medians */
  { const prof=(B)=>{ const I=B.IND.prof; const s={ind:"prof",rev:703000,ern:158950,...B.peerMedians("prof",158950,703000),yrs:6,buyers:I.buyers||50};
      return B.model({...s,ask:B.model({...s,ask:1}).V}).tMed; };
    const now=prof(A), pub=prof(A.loadWith([["const TM=MODELS.fitted.ttc_medians;","const TM=null;"]]));
    ok(Math.round(now)===213&&Math.round(pub)===207&&Math.abs(now-170)>=40&&Math.abs(pub-170)<40&&HTML.includes("reads off on a disagreement between the two sources (207 days with IBBA&rsquo;s published medians"),
       `R2-4: self-audit days row ${now.toFixed(1)} (published medians ${pub.toFixed(1)}) explained`); }
  /* R2-5: eq_vs's definition of h reproduces the hinge above the $3M SDE cap too */
  { const H=A.MODELS.value.size_hinge;
    ok([1e5,1.45e6,3e6,5e6,8e6,2e7].every(ern=>{ const r=A.model({...FX,ern,rev:Math.max(ern/.25,1e6)}), sk=ern/1e3;
      const def=sk>H.cap_sde_thousands?Math.log(H.cap_sde_thousands/H.knot_sde_thousands)+H.slope_beyond_cap*Math.log(sk/H.cap_sde_thousands):Math.max(0,Math.log(sk/H.knot_sde_thousands));
      return Math.abs(def-r.fv.hinge)<1e-9; })&&HTML.includes("hCap=s.ern/1e3>HZ.cap_sde_thousands"),"R2-5: the printed hinge definition reproduces h at every SDE"); }
  /* R2-6: the LOI leg's share is read from the medians in use: about 40%, 32-43% by band */
  { const TM=A.MODELS.fitted.ttc_medians, sh=TM.loi.map((v,i)=>v/TM.listing[i]), med=sh.slice().sort((a,b)=>a-b)[2];
    ok(Math.round(med*100)===40&&Math.round(Math.min(...sh)*100)===32&&Math.round(Math.max(...sh)*100)===43&&HTML.includes("(${loiTxt})")&&!HTML.includes("about 36% of it)"),"R2-6: LOI share computed"); }
  /* R2-7: the medians' SE includes half the rounded-vs-truncated gap, in quadrature */
  { const TM=A.MODELS.fitted.ttc_medians;
    ok(["listing","loi"].every(k=>TM[k+"_se"].every((v,i)=>v>=TM[k+"_se_sampling"][i]&&Math.abs(v-Math.hypot(TM[k+"_se_sampling"][i],TM.convention_shift[k][i]/2))<=.011))
       &&HTML.includes("half the rounded-against-truncated gap added"),"R2-7: median SEs carry the convention term"); }
  /* R2-8, R2-9: tallies counted from the tables */
  { const C=A.MODELS.close_and_timing, V=A.MODELS.value;
    const nAgg=2+Object.keys(C.close_probability.valuation_gap_distribution).length+C.time_to_close.bands.length+Object.keys(V.price_realisation_by_industry.factor).length
              +C.ibba_cash_at_close.by_band.length+(C.dvi_consideration?4:0)+2;
    ok(nAgg===38&&HTML.includes("+ ((C.ibba_cash_at_close||{}).by_band||[]).length"),"R2-8, R3-2: the aggregate tally counts cash at close and deal structure, not the prime (38)");
    const numLits=f=>{ const t=String(f).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g,""); return (t.match(/(?<![\w.$])(\d+\.\d*|\.\d+|\d+)(?![\w.])/g)||[]).filter(v=>+v!==0).length-(t.match(/\(1-/g)||[]).length; };
    const numLeaves=o=>typeof o==="function"?numLits(o):typeof o==="number"?1:o&&typeof o==="object"?Object.values(o).reduce((a,v)=>a+numLeaves(v),0):0;
    const grp={ind:1,str:1,adj:1,pep:1,add:1,fo:1};
    /* October 2026: the individual's multiple factor is calibrated (no tally); the QoE fee and the sales hire's floor read
       published tables, so INTERV lost three typed numbers (43 -> 40) */
    const nBuy=A.BUYERS.length*2-A.BUYERS.filter(b=>b.k==="ind"&&b.mf===A.MODELS.fitted.buyers.mf_ind).length
              +A.BUYERS.filter(b=>!grp[b.k]).length*2+A.BUYERS.reduce((a,b)=>a+numLits(b.fit),0)+12;
    const nInt=A.INTERV.length+A.INTERV.reduce((a,v)=>a+numLits(v.cost)+numLeaves(v.eff),0);
    ok(nBuy===53&&nInt===40&&HTML.includes("${nBuy}</td>")&&HTML.includes("${nInt}</td>")&&!HTML.includes("BUYERS.length*4"),`R2-9: BUYERS ${nBuy} and INTERV ${nInt} counted from their definitions`); }
  /* R2-10, R2-11: provenance wording */
  ok(HTML.includes("and time to close to IBBA&rsquo;s per-band histograms of closed deals")&&!HTML.includes("closing probability and timing are market aggregates"),"R2-10: footer");
  ok(!HTML.includes("never on business quality")&&!HTML.includes("&mdash; not on business quality")&&HTML.includes("It has no quality term"),"R2-11: P_C's quality claims");
}

/* ---- 33. round-3 audit fixes (AUDIT_FINDINGS round 3, verified at 3d53b6f) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  const V0=A.model({...FX,ask:1}).V;
  /* R3-1: no provenance label files timing as an aggregate. The masthead status row that carried these labels and a typed
     transaction total was removed at the owner's request, so nothing on the page may bring back the old label or the
     typed total */
  ok(!HTML.includes("<dt>Close and timing</dt>")&&!HTML.includes('class="mast-status"')
     &&!HTML.includes("<dd>"+(A.MODELS.value.n_fit+A.MODELS.risk.n_fit).toLocaleString("en-US")+"</dd>"),"R3-1: masthead provenance (status row removed)");
  /* R3-2: the prime moves no figure, is not said to set a shown rate, and is not counted */
  ok(!HTML.includes("sets the SBA note rate shown beside the survival risk")&&HTML.includes("SBA spread over prime by loan size (the survival risk reads only the spread)")
     &&/\+ \(C\.dvi_consideration\?4:0\)\s+\/\*[^*]*\*\/\s+\+ 2\s/.test(HTML),"R3-2: prime wording and count");
  { const B=A.loadWith([['"prime":7.0,','"prime":3.0,']]), a=A.model(FX), b=B.model(FX);
    ok(a.V===b.V&&a.PC===b.PC&&a.EVp===b.EVp&&Math.abs(a.risk.p-b.risk.p)<1e-12,"R3-2: the prime level moves no figure"); }
  /* R3-3: the employee count is described as reaching no figure (it still exists for fitRisk's signature) */
  { const B=A.loadWith([["function jobsFor(rev,ind){ const K","function jobsFor(rev,ind){ return 1e9; const K"]]), a=A.model({...FX,jobs:undefined}), b=B.model({...FX,jobs:undefined});
    ok(a.V===b.V&&a.PC===b.PC&&a.EVp===b.EVp&&a.risk.p===b.risk.p&&A.gmSalary(FX)===B.gmSalary(FX)&&HTML.includes("so the count reaches no figure")&&!HTML.includes("Employees for this revenue")&&!HTML.includes("<tr><td>Firm-size rank behind the GM salary</td>"),"R3-3 (+ round 4): the head count reaches no figure, and no public-data row claims it"); }
  /* R3-4: the ledger counts the category formulas (37 since Market position reads the fitted comparables depth against
     its own mean, not a typed .65), the confidence label (3: two cut-offs and the extrapolation rule; the figure is fitted
     since October 2026) and the peer scales (14 + 2 since the third round: PEER_SD's seven typed spreads, the channel
     median and sizeRefs' typed numbers less its clamp; the buyer-pool scale and the size centre) */
  { const src=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
    const sl=(a,b)=>{ const i=src.indexOf(a); return src.slice(i,src.indexOf(b,i)); };
    const mults=t=>(t.match(/(?<![\w.])(\d+\.\d*|\.\d+|\d+)\*/g)||[]).length;
    const numLits=f=>{ const t=String(f).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g,""); return (t.match(/(?<![\w.$])(\d+\.\d*|\.\d+|\d+)(?![\w.])/g)||[]).filter(v=>+v!==0).length-(t.match(/\(1-/g)||[]).length; };
    const cat=sl("out.cats={","const catMean"), z=sl("const z={","const emRaw");
    const nCat=mults(cat)+(cat.match(/-\.\d+\)/g)||[]).length+4, C=A.MODELS.fitted.confidence, nConf=["cut_high","cut_moderate","extrap_x"].filter(k=>typeof C[k]==="number").length;
    const SDF=A.MODELS.fitted.peer_sd, typed=Object.keys(A.PEER_SD).filter(k=>!(SDF[k]&&SDF[k].v===A.PEER_SD[k]));
    const nPeer=typed.length+1+numLits(String(A.sizeRefs).replace(/Math\.max\(ern,1e4\)/,""))-2, nPeerX=(z.match(/\/\.\d+,?\s*$/gm)||[]).length+1;
    ok(nCat===37&&nConf===3&&nPeer===14&&typed.join()==="rec,own,mgt,gm,ret,fin,plt"&&nPeerX===2&&!src.includes('slice("const conf="')&&HTML.includes("+ nBuy + nInt + nDelta + nCat + nConf + nPeer + nPeerX + 11 + 2 + 1")
       &&HTML.includes("${nCat}</td>")&&HTML.includes("${nConf}</td>")&&HTML.includes("${nPeer}</td>")&&HTML.includes("${nPeerX}</td>"),
       `R3-4: ledger counts ${nCat}/${nConf}/${nPeer}+${nPeerX}`); }
  /* R3-5: the loan-size gap is read at the hazard pieces' start ages: x0.26 per tenfold at month 6, rising to x0.89 in
     months 60-72, and x1.16 from month 72 (R5-7) */
  { const R=A.MODELS.risk, c=R.co.coef.lnamt, a=R.co.age_coef.lnamt, hr=m=>Math.exp(R.co.lp_shrink*(c+a*(Math.min(m,R.co.age_cap_months)/12-R.co.age_center_years))*Math.LN10);
    const starts=R.age_edges.filter(m=>m<=R.co.age_cap_months), flip=starts.find(m=>hr(m)>=1);
    ok(flip===72&&hr(60).toFixed(2)==="0.89"&&hr(72).toFixed(2)==="1.16"&&!HTML.includes("the gap closes at about")&&!HTML.includes("hazard gap closes at about 5.4"),"R3-5: size gap flips at month 72"); }
  /* R3-6: money(x,0) keeps two decimals in millions */
  ok(A.money(1296559,0)==="$1.30M"&&A.money(1.5e6,0)==="$1.50M"&&A.money(255000,0)==="$255k"&&A.money(1.5e6,1)==="$1.5M","R3-6: money() in millions");
  /* R3-7: the star tooltip shows the capped price beside V_j */
  ok(HTML.includes("price it would pay ${money(b.Vj)}${b.Pj<b.Vj*.995?` (${money(b.Pj)} at this ask)`")&&!HTML.includes("value to buyer ${money(b.Vj)}"),"R3-7: star tooltip");
  /* R3-8: the printed point-estimate anchoring is the W = E[V|X] slice's factor */
  ok([1,1.3,1.5,2,5].every(m=>{ const r=A.model({...FX,ask:V0*m}); return Math.abs(r.rho-Math.min(Math.max(r.askEff/r.V,.35),1e9))<.02&&r.askEff<=1.5*r.V*(1+1e-9); })
     &&Math.abs(A.model({...FX,ask:V0*2}).anchorF-A.model({...FX,ask:V0*5}).anchorF)<1e-9,"R3-8: point-estimate anchoring reads the effective ask");
  /* R3-9: the TermInMonths leak is quoted from the shipped population */
  { const T=A.MODELS.risk.term_trap;
    ok(T&&T.n>41000&&T.by_status.PIF.standard_term_share>.8&&T.by_status.CHGOFF.standard_term_share<.15&&!HTML.includes("<b>86.9%</b>")&&!HTML.includes("86.9% of paid-in-full")&&!HTML.includes("AUC <b>0.957</b>")&&!HTML.includes("42, 49, 50, 53"),"R3-9: trap statistics from the hazard population"); }
  /* R3-10: Pepperdine's resolved termination range is read from the series */
  { const S=A.MODELS.close_and_timing.close_probability.broker_resolved_by_year, t=Object.values(S).map(v=>1-v);
    ok(Math.round(Math.min(...t)*100)===33&&Math.round(Math.max(...t)*100)===41&&!HTML.includes("gives 32&ndash;39%"),"R3-10: termination range computed"); }
}

/* ---- 34. round-4 findings, verified by hand (the subagent verifiers were unavailable): AUDIT_FINDINGS round 4 ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  /* R4-1: TermInMonths is not the time to charge-off; the page no longer says SBA overwrites it */
  { const T=A.MODELS.risk.term_trap;
    ok(!/overwrites/.test(HTML)&&T.chgoff_term_within3_of_elapsed<.05&&Math.abs(T.chgoff_corr_term_elapsed)<.2&&T.chgoff_median_months_to_chargeoff<T.chgoff_median_term,"R4-1: TermInMonths mechanism"); }
  /* R4-2: the size and buyer-pool scales reach only the categories and confidence; the quality-dimension scales reach value */
  { const pk=r=>[r.V,r.PC,r.EVp].join(), base=A.model(FX);
    const sz=A.loadWith([["const SIZE_SD=MODELS.fitted.size_refs.size_sd_log10;","const SIZE_SD=2*MODELS.fitted.size_refs.size_sd_log10;"]]).model(FX), by=A.loadWith([["Math.log(I.buyers||50))/.9","Math.log(I.buyers||50))/1.8"]]).model(FX),
          rc=A.loadWith([["const PEER_SD={rec:.28,","const PEER_SD={rec:.20,"]]).model(FX);
    ok(pk(sz)===pk(base)&&pk(by)===pk(base)&&sz.conf===base.conf&&by.conf===base.conf&&rc.conf===base.conf&&JSON.stringify(sz.cats)!==JSON.stringify(base.cats)&&rc.V!==base.V
       &&HTML.includes("Only the category sub-scores: the quality position and the confidence figure do not read them."),"R4-2: peer scales split by reach (17 + 2); none reaches the fitted confidence"); }
  /* R4-3: the staffing row states the measured relation, not 'several times fewer' */
  ok(!HTML.includes("several times fewer than the firm's Census employees")&&!HTML.includes("runs from about a third of SBA's figure to several times it")
     &&HTML.includes("so the head count can be a fraction of SBA's figure for a small firm or many times it for a low-margin or lower-quality one, and past the $${(R.loan_range[1]/1e6).toFixed(0)}M 7(a) limit SBA's band median stays at")
     &&!A.MODELS.risk.staffing.note.includes("several times it"),"R4-3/R5-6: staffing wording");
  /* over the console's whole size range (revenue $100k-$200M, each industry at its typical margin), split at the 7(a) limit */
  { const R=A.MODELS.risk, med=R.staffing.sba_jobs_median_by_loan_band, un=[], ca=[];
    for(const ind of Object.keys(A.IND)) for(let i=0;i<=40;i++){ const rev=1e5*Math.pow(2000,i/40); let ern=rev*.2;
      for(let k=0;k<30;k++) ern=rev*A.typMargin(ind,ern);
      const r=A.model({...FX,ind,rev,ern:Math.min(ern,rev*.85),ask:1e6}), m=med[r.risk.empBandKey]; if(!m) continue;
      (R.loan_share*r.V>R.loan_range[1]?ca:un).push(r.jobs/m); }
    /* R7-1: 'a fraction ... for a small firm', 'many times it' for a low-margin or lower-quality one (a typical-margin restaurant at
       the worse quality ends, inside the limit), and growing past the limit (at $11M of revenue since round 9 pooled the
       restaurant cells, which put the $12.48M one past the limit) */
    const wq=A.model({...FX,ind:"rest",rev:11e6,ern:11e6*A.typMargin("rest",3.36e6),rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.05,plt:.95});
    un.push(wq.jobs/med[wq.risk.empBandKey]);
    ok(Math.min(...un)>.15&&Math.min(...un)<.3&&R.loan_share*wq.V<=R.loan_range[1]&&wq.jobs/med[wq.risk.empBandKey]>9&&Math.max(...ca)>50&&Math.max(...Object.values(med))===14&&R.loan_share===.85,
       `R4-3/R5-6/R7-1: Census/SBA ratio ${Math.min(...un).toFixed(2)}-${Math.max(...un).toFixed(2)} within the limit, up to ${Math.max(...ca).toFixed(0)} past it`); }
  /* R4-4: the ledger note is computed from the rows; round 5 adds the IND anchors and PMIN, PMAX, LAM0, KW (124 inert of 432
     at round 5; 123 of 353 since the second round) */
  ok(HTML.includes("const inert=nDelta+Object.keys(IND).length+Object.keys(B).length+Object.keys(NL).length+2+Object.keys(G).length+2;")&&!HTML.includes("made most of this table inert")
     &&HTML.includes("Superseded by the fitted time-to-close curve."),"R4-4/R5-1: ledger note from the counts");
  /* R4-5: the GM salary row names its size rank as judgment */
  ok(HTML.includes("the rank is Census&rsquo;s share of the industry&rsquo;s employment in smaller firms at this revenue (SUSB 2022), a labelled"),"R4-5: GM rank labelled judgment");
  /* R4-6: the budget box shows two decimals in millions, as the optimiser cards echo it */
  ok(HTML.includes('setBox("v_bud",s.budget?moneyIn(s.budget):"none");')&&HTML.includes("of ${moneyIn(s.budget)}</td>")&&A.moneyIn(1.25e6)===A.money(1.25e6,0),
     "R4-6: budget box matches the echo (both at moneyIn's precision since the stress test, S-4)");
  /* R4-7: the delta stack is counted from its source, comments stripped: 51 + 6 + 5 + 5 = 67 (the second round removed the
     tailwind's .30 offset; a comment that still named it was counted until the second-round review, DT-1) */
  { const src=String(A.model), i=src.indexOf("const d={"), dsrc=src.slice(i,src.indexOf("let sum=0",i));
    const numLits=f=>{ const t=String(f).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g,""); return (t.match(/(?<![\w.$])(\d+\.\d*|\.\d+|\d+)(?![\w.])/g)||[]).filter(v=>+v!==0).length-(t.match(/\(1-/g)||[]).length; };
    ok(numLits(dsrc)===51&&HTML.includes("${nDelta}</td>")&&HTML.includes('const numLits=f=>{ const t=String(f).replace(/\\/\\*[\\s\\S]*?\\*\\/|\\/\\/[^\\n]*/g,"");'),
       "R4-7: delta stack counted (67), comments stripped"); }
  /* R4-8 (hand-run numbers pass): the binding-ask note names the measure it ranks by, so it cannot read as contradicting
     eq_ds's 'largest lever' (ranked by value) */
  ok(HTML.includes("the quality lever that moves expected proceeds most (")&&!HTML.includes("the largest quality response (")
     &&HTML.includes("top=qs.slice().sort((a,b)=>Math.abs(b.dE)-Math.abs(a.dE))[0]"),"R4-8: sensitivity note names its ranking measure");
}

/* ---- 35. round-5 findings: AUDIT_FINDINGS round 5 ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  /* R5-1: the IND anchors and the judgment bounds have their own 'Nothing' rows; the Bounds row keeps ALPHA, AMAX, PHI, clamps */
  { const dsrc=String(A.model).match(/const d=\{[\s\S]*?let sum=0/);
    ok(HTML.includes("<code>IND</code> anchors<div")&&HTML.includes("one judgment multiple per industry</div></td>\n            <td class=\"n\" style=\"padding-right:18px\">${Object.keys(IND).length}</td>")
       &&HTML.includes("ALPHA, AMAX, PHI, clamps</div></td>\n            <td class=\"n\" style=\"padding-right:18px\">7</td>")
       &&HTML.includes("and their bounds PMIN, PMAX")&&HTML.includes("scale LAM0 and shape KW")&&!!dsrc,"R5-1: inert rows split out"); }
  /* R5-1: the 20 numbers really are inert: scaling the IND anchors and moving PMIN/PMAX/LAM0/KW changes no reported figure */
  { const B=A.loadWith([["const fInd=1+(I.anchor/2.65-1)*w;","const fInd=1+(I.anchor*1.8/2.65-1)*w;"],["const PMIN=.05, PMAX=.93;","const PMIN=.20, PMAX=.70;"],["const LAM0=250, KW=1.42,","const LAM0=600, KW=3.0,"]]);
    let same=true, judg=false;
    for(const ind of ["medical","saas","rest","constr"]) for(const k of [.8,1,1.3]){ const s={...FX,ind}; s.ask=A.model(s).V*k;
      const a=A.model(s), b=B.model(s);
      for(const f of ["V","M","PC","EVp","tMed","tMean","Vreal","Vmean","conf"]) if(Math.abs(a[f]-b[f])>1e-9*Math.max(1,Math.abs(a[f]))) same=false;
      if(a.risk.p!==b.risk.p||A.omniScore(a)!==B.omniScore(b)) same=false;
      if(Math.abs(a.Mjudg-b.Mjudg)>1e-3&&Math.abs(a.PCjudg-b.PCjudg)>1e-3) judg=true; }
    ok(same&&judg,"R5-1: the IND anchors, PMIN, PMAX, LAM0 and KW move only the judgment panels"); }
  /* R5-2: the ask and buyer-pool rows are the steps they name, so a cut at the recommended ask shows as a loss */
  { const V=A.model(FX).V, s={...FX,ask:V*A.bestRatio(FX,0,0)}, sn=A.sensitivity(s), ask=sn.find(o=>o.k==="ask"), buy=sn.find(o=>o.k==="buyers");
    const e0=A.model(s).EVp, eA=A.model({...s,ask:s.ask*.95}).EVp, eB=A.model({...s,buyers:s.buyers*1.25}).EVp;
    const s5={...s,buyers:500}, b5=A.sensitivity(s5).find(o=>o.k==="buyers");
    ok(Math.abs(ask.dE-(eA-e0))<1e-6&&ask.dE<0&&Math.abs(buy.dE-(eB-e0))<1e-6&&!buy.back&&b5.back
       &&Math.abs(b5.dE-(A.model(s5).EVp-A.model({...s5,buyers:400}).EVp))<1e-6&&HTML.includes("How each row is measured"),
       `R5-2: the ask and pool rows are the named steps (a 5% cut at the best ask: ${ask.dE.toFixed(0)})`); }
  /* R5-3: the competition premium's dollar effect goes through the ceiling, as P(W) does */
  { const s={...FX,buyers:5}; s.ask=A.model(s).V*.95; const r=A.model(s);
    const capped=A.softMin(r.V*r.anchorF*(1+r.compPrem),r.ceil)-A.softMin(r.V*r.anchorF,r.ceil), raw=r.V*r.anchorF*r.compPrem;
    const Z=A.loadWith([["out.compPrem=clamp(","out.compPrem=0*clamp("]]).model(s);
    ok(HTML.includes("const compAt=softMin(r.V*r.anchorF*(1+r.compPrem),r.ceil)-softMin(r.V*r.anchorF,r.ceil),")&&!r.askBinds
       &&Math.abs(capped)<.5*Math.abs(raw)&&Math.abs((r.Vreal-Z.Vreal)/capped-1)<.25,
       `R5-3: capped premium ${capped.toFixed(0)} against uncapped ${raw.toFixed(0)}; median moves ${(r.Vreal-Z.Vreal).toFixed(0)}`); }
  /* R5-4: the old build's swing is computed: the nine inputs from the worse to the better end of their controls */
  { const lo={...FX,rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.05,plt:.95}, hi={...FX,rec:1,own:.14,mgt:.92,cc:.01,fin:.96,grw:.70,gm:.97,ret:.99,plt:.05};
    const a=A.model(lo), b=A.model(hi);
    ok(!HTML.includes("2.38&times; to 3.02&times;")&&HTML.includes("swings the old judgement build&rsquo;s multiple from ${xx(rl.Mjudg)} to ${xx(rh.Mjudg)}")
       &&b.Mjudg/a.Mjudg>b.M/a.M&&b.M>a.M,`R5-4: judgement build ${a.Mjudg.toFixed(2)}-${b.Mjudg.toFixed(2)}, console multiple ${a.M.toFixed(2)}-${b.M.toFixed(2)}`); }
  /* R5-5: owner pay is read from the wedge the console uses: smaller at $3M of SDE than at $200K, and not negligible */
  { const share=sde=>Object.keys(A.IND).map(k=>A.sdeEbitdaWedge(A.naicsFor(k),sde/A.typMargin(k,sde))).filter(w=>w).map(w=>1-1/w);
    const a=share(2e5), b=share(3e6);
    ok(!HTML.includes("it is a rounding error")&&HTML.includes("In the wedge the console uses it is")&&Math.min(...b)>.1&&Math.max(...b)<Math.max(...a)&&Math.min(...b)<Math.min(...a),
       `R5-5: owner pay ${Math.round(Math.min(...a)*100)}-${Math.round(Math.max(...a)*100)}% of SDE at $200K, ${Math.round(Math.min(...b)*100)}-${Math.round(Math.max(...b)*100)}% at $3M`); }
  /* R5-7: AUDIT.md states the size gap by piece and the head-count relation the right way round */
  { const AM=require("fs").readFileSync(require("path").join(__dirname,"..","AUDIT.md"),"utf8");
    ok(AM.includes("×0.26 per tenfold at 6 months, rising to ×0.89 in months 60–72")&&!AM.includes("×0.89 per tenfold before month 72")
       &&AM.includes("The Census head count runs from about a fifth of SBA's jobs count")&&!AM.includes("SBA's jobs count runs from about a third of the Census head count"),"R5-7: AUDIT.md record lines"); }
}

/* ---- 36. round-6 findings: AUDIT_FINDINGS round 6 ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  /* R6-1: the quality sweep moves the console's multiple through the judgment quality position; the fitted multiple stays */
  { const a=A.model({...FX,rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.05,plt:.95}), b=A.model({...FX,rec:1,own:.14,mgt:.92,cc:.01,fin:.96,grw:.70,gm:.97,ret:.99,plt:.05});
    ok(!HTML.includes("here the same sweep moves the fitted multiple from")&&HTML.includes("here the same sweep moves the console&rsquo;s multiple from ${xx(rl.M)} to ${xx(rh.M)}: the fitted")
       &&Math.abs(a.fv.mult-b.fv.mult)<1e-12&&Math.abs(b.M/a.M-b.qFactor/a.qFactor)<1e-9,
       `R6-1: fitted ${a.fv.mult.toFixed(2)} at both ends; quality position x${a.qFactor.toFixed(2)}-x${b.qFactor.toFixed(2)}`); }
  /* R6-2: the staffing range is stated at the typical margin it was measured at, and is larger at lower margins */
  { const R=A.MODELS.risk, med=R.staffing.sba_jobs_median_by_loan_band, r=A.model({...FX,ind:"staff",rev:1e7,ern:1e6}), m=med[r.risk.empBandKey];
    ok(HTML.includes("many times it for a low-margin or lower-quality one")&&R.staffing.note.includes("many times it for a low-margin or lower-quality one")&&!R.staffing.note.includes("about six times")
       &&R.loan_share*r.V<=R.loan_range[1]&&r.jobs/m>8,`R6-2: a $10M staffing firm at a 10% margin, inside the limit: ${r.jobs}/${m} = ${(r.jobs/m).toFixed(1)}x`); }
  /* R6-3: eq_comp's general form is the capped price, as in eq_a; the substituted line says which side of the ceiling each figure is */
  { const line=HTML.split("\n").find(l=>l.includes('eq("eq_comp",'))||"", i=HTML.indexOf('eq("eq_comps",'), sub=HTML.slice(i,i+700);
    ok(line.includes("operatorname{softmin}")&&line.includes("bar a")&&!line.includes("propto(1+")&&sub.includes("text{ before the ceiling}")&&sub.includes("text{ at the point estimate after it}"),
       "R6-3: eq_comp states the capped relation"); }
}

/* ---- 37. the stress test with invariants: AUDIT_FINDINGS "Stress test" (S-1..S-5) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const FX={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75};
  let sd=97; const rn=()=>{ sd=(sd*16807)%2147483647; return (sd-1)/2147483646; };
  /* S-1: every reference draw sits at its stated composite, as model() computes it, in every industry and size */
  { let worst=0,n=0;
    for(const ind of Object.keys(A.IND)) for(const e of [3e4,5e4,1e5,3e5,1e6,5e6]){ const R=A.refDistAt({ind,ern:e,rev:e/A.typMargin(ind,e)});
      R.zq.forEach((z,i)=>{ worst=Math.max(worst,Math.abs(z-A.nqnt(Math.min(.996,Math.max(.004,(i+.5)/128))))); n++; }); }
    let wq=0; const INDS=Object.keys(A.IND);
    for(let i=0;i<400;i++){ const ern=1e4*Math.exp(rn()*7.5), t={ind:INDS[i%INDS.length],ern,rev:ern/(.05+rn()*.6),rec:rn(),cc:.005+rn()*.9,own:.02+rn()*.97,mgt:.02+rn()*.97,
      grw:-.6+rn()*2.1,gm:.02+rn()*.95,ret:.05+rn()*.94,fin:.02+rn()*.98,plt:.02+rn()*.97,yrs:6,buyers:50,st:null,franchise:false,ask:1};
      wq=Math.max(wq,Math.abs(A.qualityZ(t)-A.model(t).qz)); }
    const w={ind:"rest",rev:1.5e6,ern:3e5,own:.95,mgt:.08,fin:.14,rec:.05,cc:.18,grw:-.05,gm:.62,ret:.45,plt:.40,yrs:6,buyers:41,st:null,franchise:false};
    const V=A.model({...w,ask:1}).V, r=A.model({...w,ask:V*A.bestRatio(w,0,0)});
    /* the weak restaurant scored 10 until October 2026: the fitted size slopes put its owner dependence and management depth
       further from its peers' at $300k of SDE, and the restaurant medians moved (7). The third round's retention median for
       restaurants (.27 by customer count, was .45) puts its .45 above its peers', and the concentration median and spread
       (.14, .18) moved: 16 */
    ok(n===12288&&worst<1e-9&&wq<1e-12&&A.omniScore(r)===16,
       `S-1: ${n} reference draws at their composite (worst ${worst.toExponential(1)}), qualityZ = model qz (${wq}); the weak restaurant scores ${A.omniScore(r)}`); }
  /* S-2: the Census tables are read on an increasing receipts scale, so the GM salary has no jump */
  { let sorted=true; for(const ind of Object.keys(A.IND)){ const K=A.jobsKnots(ind); if(!K) continue;
      for(let i=1;i<K.length;i++) if(!(K[i][0]>K[i-1][0])||K[i][3]<K[i-1][3]) sorted=false; }
    let jump=0, fall=0; for(const ind of Object.keys(A.IND)) for(let x=Math.log(1e5);x<Math.log(2e8);x+=1e-4){
      const a=A.gmSalary({ind,rev:Math.exp(x)}), b=A.gmSalary({ind,rev:Math.exp(x+1e-4)}); jump=Math.max(jump,Math.abs(b/a-1)); fall=Math.max(fall,a-b); }
    ok(sorted&&jump<1e-3&&fall<=1e-9&&Math.abs(A.gmSalary({ind:"wash",rev:18652673})-A.gmSalary({ind:"wash",rev:18652672}))<1
       &&Math.abs(A.gmSalary({ind:"fit",rev:27023030})-A.gmSalary({ind:"fit",rev:27023029}))<1,
       `S-2: knots in order in every industry; the GM salary moves at most ${(jump*100).toFixed(3)}% per 0.01% of revenue and never falls`); }
  /* S-3: the score reads no history: a neighbouring size built first does not stand in for this one */
  { const B=A.loadWith([]), C=A.loadWith([]), s={...FX,ern:1450003.37}, s2={...FX,ern:1450000};
    const fresh=JSON.stringify(B.refDistAt(s).xs); C.refDistAt(s2); const after=JSON.stringify(C.refDistAt(s).xs);
    ok(fresh===after&&fresh!==JSON.stringify(C.refDistAt(s2).xs)&&HTML.includes('const key=(s.ind||"prof")+"|"+ern+"|"+rev;'),"S-3: the reference population is keyed on the exact size"); }
  /* S-4: the exact-value boxes and the SDE x multiple echoes re-read within half a percent at every size */
  { const parse=t=>{ const m=/^(\u2212?)\$([\d.]+)([kMB]?)$/.exec(t); return m?(m[1]?-1:1)*Number(m[2])*({k:1e3,M:1e6,B:1e9}[m[3]]||1):NaN; };
    let worst=0; for(let x=Math.log(1e3);x<Math.log(2e9);x+=.003){ const v=Math.exp(x); worst=Math.max(worst,Math.abs(parse(A.moneyIn(v))/v-1)); }
    ok(worst<=.005&&A.moneyIn(1499)==="$1.5k"&&A.moneyIn(2324)==="$2.32k"&&A.moneyIn(999499)==="$999k"&&A.moneyIn(1.25e6)===A.money(1.25e6)&&A.moneyIn(-2324)==="\u2212$2.32k"
       &&HTML.includes('setBox("v_ern",moneyIn(s.ern))')&&HTML.includes("${tsub(`${moneyIn(s.ern)} × ${xx(r.M)}`)}")&&HTML.includes("=${tmi(s.ern)}"),
       `S-4: boxes and echoes re-read within ${(worst*100).toFixed(2)}%`); }
  /* S-5: an empty programme says what binds; a change the budget blocks is named, and it does beat doing nothing */
  { const prep=s=>{ s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,s.lamT,s.theta); return s; };
    /* the quality-of-earnings fee is the cheapest change: a budget just under it blocks it, one just over it buys it */
    const cq=A.INTERV.find(i=>i.k==="qoe").cost(FX);
    /* at $5M, 1.16x the value as $4.7M was before round 9 pooled the medical cells */
    const s=prep({...FX,ask:5e6,budget:cq-400}), b=A.optimize(s,A.model(s),s.budget,s.lamT,s.theta);
    const s2=prep({...FX,ask:5e6,budget:cq+600}), b2=A.optimize(s2,A.model(s2),s2.budget,s2.lamT,s2.theta);
    const bl=b.U.blocked, ru=bl&&A.model(A.applyAll(s,A.model(s),[bl.k],s.optRho)), uBl=bl&&ru.EVp+(1-ru.PC)*s.theta*ru.V-s.lamT*(ru.tMean+A.daysOf(s,[bl.k]))-bl.c;
    ok(!b.U.keys.length&&bl&&bl.k==="qoe"&&bl.c>s.budget&&uBl>b.U.U&&b2.U.keys.includes("qoe")&&!b.allIn
       &&HTML.includes("Do nothing — nothing within the budget clears its cost; ${INTERV.find(i=>i.k===sel.blocked.k).n} would${sel.blocked.withReprice?\", with a reprice to match\":\"\"}, for ${moneyIn(sel.blocked.c)}"),
       `S-5: the budget-bound programme names ${bl&&bl.k} at $${bl&&Math.round(bl.c)}`); }
}

/* ---- 38. second round, October 2026: the peer table and the remaining judgment parameters, fitted where public data
   allows (fit/peer_gross_margin.py, peer_growth.py, peer_recurring_retention.py, industry_tailwind_and_comps.py,
   size_refs.py, buyer_factors.py, sba_tail_factor.py, intervention_costs.py, confidence_accuracy.py, peer_checks.py) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const F=A.MODELS.fitted, IND=A.IND, INDS=Object.keys(IND);
  /* 38a. peer gross margin: a curve in log10 revenue, flat beyond its knots, on a stated definition */
  { const G=F.peer_gm, K=G.knots_log10_rev; let knots=true, flat=true, defs=true;
    for(const k of INDS){ const B=G.by_industry[k];
      if(!B){ if(A.peerGm(k,1e6)!==IND[k].gm) knots=false; continue; }
      K.forEach((x,i)=>{ if(Math.abs(A.peerGm(k,Math.pow(10,x))-B.gm[i])>1e-12) knots=false; });
      if(A.peerGm(k,Math.pow(10,K[0]-1))!==B.gm[0]||A.peerGm(k,Math.pow(10,K[K.length-1]+1))!==B.gm[B.gm.length-1]) flat=false;
      if(!(B.se.length===B.gm.length&&B.gm.every(v=>v>0&&v<1)&&B.se.every(v=>v>0))) knots=false; }
    for(const k of INDS) if(A.gmDefinition(k)!==(G.definition[k]||G.definition.default)||!(A.gmDefinition(k).length>20)) defs=false;
    if(A.gmDefinition("wash")!==G.definition.wash) defs=false;
    for(const k of INDS){ const B=G.by_industry[k]; if(!B) continue;   /* halfway between the first two knots, in log10 revenue */
      if(Math.abs(A.peerGm(k,Math.pow(10,(K[0]+K[1])/2))-(B.gm[0]+B.gm[1])/2)>1e-12) knots=false; }
    ok(knots&&flat&&defs,"38a: peerGm reads the knots, holds the end values, and every industry states its definition");
    ok(Object.keys(G.by_industry).length===16&&INDS.every(k=>IND[k].gm===undefined)&&!("wash" in G.not_identified)
       &&G.by_industry.ecom.tier==="listing-level"&&G.by_industry.ecom.gm.every(v=>v===G.by_industry.ecom.gm[0])
       &&G.by_industry.wash.tier==="franchise disclosure"&&G.by_industry.wash.gm.every(v=>v===.80)&&G.by_industry.wash.slope===0,
       "38a: no margin is hand-set: car washes read a flat .80 from a franchisor's disclosed costs (third round); e-commerce's is flat");
    const m=median("home",7e5); ok(A.model({...m,ask:1}).peer.gm===A.peerGm("home",m.rev),"38a: model() compares gross margin with the curve at its revenue");
    ok(HTML.includes('gl.title="Gross margin: "+gmDefinition(s.ind)'),"38a: the slider's label states the definition");
    /* second-round review: an unlisted industry reads prof's curve (it read IND.prof.gm, which the round removed: NaN z.gm) */
    const zq={ern:5e5,rev:2e6,grw:.06,gm:.5,rec:.3,cc:.16,ret:.82,plt:.4,own:.6,mgt:.4,fin:.6,yrs:6,buyers:65};
    ok(A.peerGm("zzz",2e6)===A.peerGm("prof",2e6)&&A.peerGm(undefined,2e6)===A.peerGm("prof",2e6)&&A.gmDefinition("zzz")===G.definition.default
       &&A.peerMedians("zzz",5e5,2e6).gm===A.peerGm("prof",2e6)&&isFinite(A.qualityZ(zq))&&isFinite(A.qualityZ({...zq,ind:"zzz"}))
       &&A.gmDefinition("wash")===G.definition.wash&&A.gmDefinition("rest")===G.definition.rest,"38a: an unlisted industry reads professional services' margin curve and the default definition");
    const sl=/<input type="range" id="i_gm" min="(\d+)" max="(\d+)"/.exec(HTML), top=Math.max(...INDS.filter(k=>G.by_industry[k]).flatMap(k=>G.by_industry[k].gm));
    ok(sl&&+sl[2]/100>=top&&+sl[2]/100<=.97,`38a: the gross-margin slider reaches every peer median (to ${sl&&sl[2]}%, highest median ${(top*100).toFixed(1)}%) and no further than FIELD_RANGE`); }
  /* 38b. growth, retention, tailwind and comparables depth are written into IND at load (FITTED_CELLS) */
  { let good=true;
    for(const k of INDS){ if(k in F.peer_grw.by_industry){ if(IND[k].grw!==F.peer_grw.by_industry[k]) good=false; } else if(k!=="saas") good=false;
      if(IND[k].tail!==F.tailwind.by_industry[k]||Math.abs(IND[k].comps-A.compsFor(k))>1e-15||!(IND[k].tail>=-1&&IND[k].tail<=1)) good=false; }
    ok(good&&IND.saas.grw===.25&&["land","fit","ecom","auto","rest"].every(k=>IND[k].ret===F.peer_rec_ret.ret[k].v)
       &&Object.keys(F.peer_rec_ret.rec).join()==="msp"&&IND.msp.rec===F.peer_rec_ret.rec.msp.v,
       "38b: the fitted cells are written in; software's growth and every recurring share but the MSPs' (third round) stay hand-set");
    const want=[...Object.keys(F.peer_grw.by_industry).map(k=>k+".grw"),...INDS.map(k=>k+".tail"),...INDS.map(k=>k+".comps"),"land.ret","fit.ret",
      "ecom.ret","auto.ret","rest.ret","msp.rec"].sort();
    ok(JSON.stringify(A.FITTED_CELLS.slice().sort())===JSON.stringify(want),"38b: FITTED_CELLS lists exactly what was written");
    ok(Math.abs(IND.saas.comps-7/(7+A.MODELS.value.industry_shrinkage.k_naics6))<1e-15&&Math.abs(A.COMPS_MEAN-INDS.reduce((a,k)=>a+IND[k].comps,0)/INDS.length)<1e-15,
       "38b: software's comparables depth from its 7 sales; Market position reads depth against the industries' mean"); }
  /* 38c. size slopes fitted, levels judgment; the size z-score's width fitted */
  { const S=F.size_refs; let good=true;
    for(const e of [1e4,4.5e4,1.5e5,7.08e5,3e6,1.1e7,5e7]){ const R=A.sizeRefs(e), z=Math.max(-1,Math.min(1,(Math.log10(Math.max(e,1e4))-5.85)/1.2));
      if(Math.abs(R.own-(.62+S.own.b*z))>1e-12||Math.abs(R.mgt-(.42+S.mgt.b*z))>1e-12||Math.abs(R.fin-(.55+.22*z))>1e-12) good=false; }
    ok(good&&S.own.b===-.15&&S.mgt.b===.17&&A.SIZE_SD===S.size_sd_log10&&S.size_sd_log10===.48,"38c: sizeRefs reads the fitted slopes at the hand-set levels; SIZE_SD is fitted"); }
  /* 38d. intervention costs: the QoE fee, the GM's loading and hire, the sales hire's floor */
  { const I=F.interventions, c=k=>A.INTERV.find(v=>v.k===k); let good=true;
    for(const k of INDS) for(const rev of [2e5,1e6,8e6,4e7]){ const s={...median(k,rev*.2),rev};
      if(Math.abs(c("qoe").cost(s)-Math.max(I.qoe.floor,I.qoe.share*rev))>1e-9) good=false;
      if(Math.abs(c("gm").cost(s)-(I.gm.hire_cost+I.gm.loading*A.gmSalary(s)))>1e-9) good=false;
      if(Math.abs(c("growth").cost(s)-Math.max(I.growth_floor.by_industry[k],.022*rev))>1e-9) good=false;
      if(Math.abs(c("gm").eff(s).add.ern+I.gm.loading*A.gmSalary(s))>1e-9) good=false; }
    ok(good&&I.qoe.floor===16400&&I.qoe.share===.0019&&I.gm.loading===1.24&&I.gm.hire_cost===10625&&Object.keys(I.growth_floor.by_industry).length===16,
       "38d: the three costs read the published benchmarks");
    ok(c("growth").cost({ind:"zzz",rev:1e5})===I.growth_floor.by_industry.prof,"38d: an industry without a cell reads professional services' sales hire"); }
  /* 38e. confidence: the fitted chance of landing within 25% of the fitted value. The fit's vectors were made on one
     representative 6-digit cell per industry; since round 9 values each industry on the cells its label names, pooled, the
     comparables weight reads the pooled count, so the vectors are checked on a build reading the representative cell
     (the formula), and the live build's weight against the pool (r9-valuation-1) */
  { const C=F.confidence, B=A.loadWith([["  const cs=IND_CELLS[k], V=MODELS.value,","  const cs=IND2NAICS6[k]?[IND2NAICS6[k]]:null, V=MODELS.value,"]]);
    ok(typeof A.cellOf==="function"&&INDS.every(k=>{ const c=A.cellOf(k), K=A.MODELS.value.industry_shrinkage.k_naics6, r=A.confidenceOf({ind:k,ern:7e5,rev:3.5e6},{z:{em:0},extrapMax:0});
         return k==="saas"?r.comps===0:Math.abs(r.comps-c.n/(c.n+K))<1e-12; })&&A.cellOf("medical").n>B.cellOf("medical").n,
       "38e: the live comparables weight is the pooled cells' n/(n+k)");
    /* the fit's own test vectors (a Python port with the console's ncdf): ind, SDE, revenue, z.em, extrapMax -> p, label, sigma */
    const TV=[["home",7e5,3.5e6,0,0,.548252,"High",.776195],["rest",1.5e5,1.2e6,-.5,0,.474165,"Moderate",.928972],
      ["saas",2.5e6,8e6,1,1.5,.471778,"Moderate",.934489],["vet",3e5,1e6,2,0,.407037,"Low",1.105286],["medical",1.45e6,5e6,.1,0,.561768,"High",.752234],
      ["msp",5e4,4e5,-1.5,0,.386356,"Low",1.169986],["dist",2e7,1.3e8,0,11.9,.55152,"Low",.770307],["auto",5.1e6,2e7,0,3,.578304,"High",.724247],
      ["fit",1e5,1.1e5,3.2,1.1,.336469,"Low",1.356324],["land",2e4,1.5e6,-3.2,1.7,.298868,"Low",1.535456]];
    ok(TV.every(([ind,ern,rev,zem,ex,p,l,sg])=>{ const r=B.confidenceOf({ind,ern,rev},{z:{em:zem},extrapMax:ex}); return Math.abs(r.p-p)<2e-6&&r.label===l&&Math.abs(r.sigma-sg)<2e-6; }),
       "38e: the fit's ten test vectors");
    /* second-round review: the fitted 80% band (eq_cs prints fv.point times it), the comparables weight and the note, against
       the same ten vectors (fit/confidence_accuracy.py RESULT test_vectors, 6 significant digits) */
    const TVB=[["home",700000.0,3500000.0,0.0,0.0,0.59313,1.505502,0.946352,"more predictable than three quarters of listed businesses"],["rest",150000.0,1200000.0,-0.5,0.0,0.535179,1.631752,0.980159,"in the middle half of listed businesses"],["saas",2500000.0,8000000.0,1.0,1.5,0.533196,1.636504,0.0,"in the middle half of listed businesses"],["vet",300000.0,1000000.0,2.0,0.0,0.475302,1.790667,0.537037,"less predictable than three quarters of listed businesses"],["medical",1450000.0,5000000.0,0.1,0.0,0.602771,1.486608,0.875622,"more predictable than three quarters of listed businesses"],["msp",50000.0,400000.0,-1.5,0.0,0.455051,1.852787,0.766355,"less predictable than three quarters of listed businesses"],["dist",20000000.0,130000000.0,0.0,11.9,0.595485,1.500837,0.621212,"outside the fitted data"],["auto",5100000.0,20000000.0,0.0,3.0,0.614231,1.464839,0.944444,"more predictable than three quarters of listed businesses"],["fit",100000.0,110000.0,3.2,1.1,0.401422,2.043999,0.882629,"outside the fitted data"],["land",20000.0,1500000.0,-3.2,1.7,0.355835,2.246397,0.959936,"outside the fitted data"]];
    ok(TVB.every(([ind,ern,rev,zem,ex,b0,b1,cp,note])=>{ const r=B.confidenceOf({ind,ern,rev},{z:{em:zem},extrapMax:ex});
         return Math.abs(r.band80[0]-b0)<2e-6&&Math.abs(r.band80[1]-b1)<2e-6&&Math.abs(r.comps-cp)<2e-6&&r.note===note; }),
       "38e: the fitted band, the comparables weight and the note match the fit's vectors");
    let same=true, rule=true, rng=true, mono=true;
    for(const k of INDS) for(const ern of [5e4,3e5,1.5e6]){ const s={...median(k,ern),ask:1}, r=A.model(s), c=A.confidenceOf(s,r);
      if(r.conf!==c.p||r.confLabel!==c.label||r.confNote!==c.note||r.confOutside!==c.outside) same=false;
      if(!(r.conf>0&&r.conf<1)) rng=false;
      if(r.confLabel!==(r.confOutside?"Low":r.conf>=C.cut_high?"High":r.conf>=C.cut_moderate?"Moderate":"Low")) rule=false;
      if(A.model({...s,yrs:s.yrs+5}).conf!==r.conf||A.model({...s,fin:Math.min(1,s.fin+.2)}).conf!==r.conf) same=false; }
    for(const k of INDS){ let prev=Infinity; for(const zem of [0,.5,1,2,3]){ const p=A.confidenceOf({ind:k,ern:3e5,rev:1.5e6},{z:{em:zem},extrapMax:0}).p; if(p>prev+1e-12) mono=false; prev=p; }
      prev=-Infinity; for(const e of [2e4,5e4,1.5e5,5e5,1.5e6]){ const p=A.confidenceOf({ind:k,ern:e,rev:e*4},{z:{em:0},extrapMax:0}).p; if(p<prev-1e-12) mono=false; prev=p; } }
    ok(same&&rule&&rng&&mono,"38e: model() reads confidenceOf; the label follows the quartile cut-offs; years and reporting do not move it; it falls with the margin's distance from typical and rises with size");
    const at=(ind,ex)=>A.confidenceOf({ind,ern:7e5,rev:3.5e6},{z:{em:0},extrapMax:ex});
    ok(at("saas",0).p<at("home",0).p&&at("home",3.01).label==="Low"&&at("home",3.01).note===C.notes.outside&&at("home",3).label==="High"
       &&Math.abs(at("home",0).p-C.reference.p)<.01,"38e: no comparables cell lowers it; past 3x the fitted data it reads Low, outside the fitted data; the reference business reads the table's p");
    ok(/const nConf = \["cut_high","cut_moderate","extrap_x"\]/.test(HTML)&&/\+ 3;\s+\/\* confidence: the size and margin gradients/.test(HTML),"38e: the ledger counts the label's three choices; the fitted gradients count as fitted");
    ok(HTML.includes('eq("eq_c",`c=P')&&HTML.includes("fitted band here, 80")&&HTML.includes("r.fv.point*r.confBand80[0]"),"38e: eq_c is the fitted formula; eq_cs prints this business's fitted band");
    /* second-round review: the printed formula reproduces c past the support (SDE held, as confidenceOf holds it), around V/q */
    ok(HTML.includes("\\\\tfrac{\\\\text{price}}{V/q}")&&HTML.includes("\\\\ln(\\\\text{SDE}^{*}/\\\\$700\\\\text{k})")
       &&HTML.includes("\\\\text{SDE}^{*}=\\\\text{SDE held between the value model's 1st and 99th percentiles, }${tmi(E.p1)}\\\\text{ and }${tmi(E.p99)}")
       &&HTML.includes('if(id==="eq_c"){ var q=cut(t,R`,\\quad \\text{SDE}^{*}=`);')
       &&HTML.includes('pc(k.p8,2)+" within 8 years × "+k.tail.toFixed(3)'),"38e: eq_c prints the fitted value before the quality position and the SDE clamp; the risk tile's product carries enough digits");
    { const E=A.MODELS.value.support.ern; let same=true;
      for(const [ind,ern,rev] of [["home",5e6,2e7],["auto",5e6,2e7],["prof",3e6,1e7],["home",8e3,4e4],["medical",1.45e6,6e6]]){
        const s={...median(ind,ern),rev,ask:1}, r=A.model(s), c=A.confidenceOf(s,r), lx=Math.log(Math.min(Math.max(ern,E.p1),E.p99)/700000);
        /* a pooled label's industry term is each cell's distance from the pool and its own depth (r10-valuation-2) */
        const P=A.cellOf(ind), MV=A.MODELS.value, K6=MV.industry_shrinkage.k_naics6, dv=P&&P.cells.length>1
          ?P.cells.reduce((a,x)=>a+MV.industry_n6[x]/P.n*((MV.coefficients.ind_eff*(MV.industry_effects_naics6[x]-P.e))**2+C.tau2*K6/(MV.industry_n6[x]+K6)),0)
          :C.tau2*(1-c.comps);
        const sh=C.K*Math.exp(C.b_size*lx+C.b_em*Math.abs(r.z.em)), sg=Math.sqrt(sh*sh+dv/(C.s_eq*C.s_eq));
        if(Math.abs(sg-r.confSigma)>1e-12||Math.abs(r.V/r.qFactor-r.fv.point)>1e-6*r.V||Math.abs(r.z.em)>3.2) same=false; }
      ok(same,"38e: the printed sigma (SDE held at the support, z_em as displayed) is the one computed, and V/q is the fitted point"); } }
  /* 38f. the Data tab: a row for every second-round fit, and no stale wording */
  ok(["Peer median gross margin, by industry and revenue","Peer median revenue growth by industry","Customer retention: landscaping and fitness",
      "How owner dependence and management depth change with size","Width of the size z-score","<tr><td>Industry tailwind","Depth of comparable sales (Market position)",
      "The individual buyer&rsquo;s multiple factor","Survival risk: years 9&ndash;10 of the 10-year figure","Quality-of-earnings report: cost",
      "Hire a general manager: cost and the charge on earnings","Add sales capacity: the cost floor","<tr><td>Analysis confidence &nbsp;",
      "Typical buyer pools and strategic interest by industry"].every(t=>HTML.includes(t)),"38f: a row for every second-round fit, and a judgment row for buyer pools and strategic interest");
  ok(!/(?<!sba_)tail_factor/.test(HTML)&&!HTML.includes("tail_by_band")&&!HTML.includes("more often carry 25-year terms")&&!HTML.includes("four weights, two scales, two label cut-offs")
     &&!HTML.includes("PLACEHOLDER")&&!/\blead\b|fit6|\/tmp\//.test(HTML.slice(HTML.indexOf("/* October 2026, second round: the peer table"),HTML.indexOf("MODELS.fitted.peer_checks="))),"38f: no stale or workflow wording");
}

/* ---- 39. recurring motion (v10): tasteful by construction. Every loop moves only opacity, a transform or a background
   strip; every loop but the tab indicator's runs only while its block is on screen; the figure glow is a Web Animation, so
   the script writes no attribute a test or a reader sees except the blocks' m-on class ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const i=HTML.indexOf('<style id="v10-motion-css">'), css=i<0?"":HTML.slice(i,HTML.indexOf("</style>",i));
  const k=HTML.indexOf('<script id="v10-motion-js">'), js=k<0?"":HTML.slice(k,HTML.indexOf("</script>",k));
  const frames=[...css.matchAll(/@keyframes\s+([\w-]+)\{([\s\S]*?)\}\}/g)];
  const props=[...new Set(frames.flatMap(m=>[...m[2].matchAll(/([a-z-]+)\s*:/g)].map(x=>x[1])))];
  ok(i>0&&k>0&&frames.length>=5&&props.every(q=>["opacity","transform","background-position"].includes(q)),
     `39: the motion layer's ${frames.length} keyframes move only ${props.join(", ")}`);
  const loops=[...css.matchAll(/animation:m-[\w-]+[^;}]*infinite/g)].length, gated=[...css.matchAll(/\.m-on[^{]*\{[^}]*animation:m-/g)].length;
  ok(loops>=8&&gated===loops-1&&/nav-ind::after\{[^}]*animation:m-breathe/.test(css),`39: ${gated} of ${loops} loops run only while their block is on screen; the other is the tab indicator`);
  ok(/el\.animate\(/.test(js)&&!/setAttribute|\.style\.|className\s*=|innerHTML/.test(js)&&/classList\.toggle\("m-on"/.test(js)
     &&/getElementById\("boot"\)/.test(js),"39: the figure glow is a Web Animation; the script writes no attribute but m-on, and waits for the film");
  ok(/@media\(prefers-reduced-motion:reduce\)\{\*\{animation:none!important;transition:none!important\}\}/.test(HTML)&&/mq\.matches/.test(js),
     "39: reduced motion stops every loop (the page's global rule) and the glow (the script checks the preference)");
}

/* ---- 40. the skeptic review (October 2026): each confirmed fix, pinned. MODEL-1 is checked on the skeptic's own
   profile; the display, layout and interface fixes by the code that makes them ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  /* MODEL-1 (the dip under a peak read off the .02 grid beside a kinked bottom) on the skeptic's own profile, under the gap
     axis it was found on: the third round read Pepperdine's gap as a share of the ask, which removed this profile's second
     peak, so the fix is pinned on a build with the old axis (bucket edges at 10-50% and the open bucket at 100% over
     value) and the old peer comparison (concentration median .16, its spread and growth's .13), and the live note is
     checked against a fine grid */
  { const s0={ind:"vet",rev:3878320.238970697,ern:776822.4617297485,grw:0.03709924817085264,gm:0.6877818477153778,rec:0.39787375926971436,
      cc:0.6583209502696991,ret:0.8690899014472961,plt:0.10440324544906616,own:0.72,mgt:0.66,fin:0.45,yrs:6,buyers:530,st:null,franchise:false,
      budget:100000,lamT:3350,theta:0.9155685663223266,ask:3681742.1258855304};
    const noteOf=API=>{ const s={...s0}, r=API.model(s); s.optRho=API.bestRatio(s,s.theta,s.lamT); s.rhoSell=API.bestRatio(s,0,0);
      return {s,V:r.V,nt:API.optNote(s,r.V,API.model({...s,ask:r.V*s.rhoSell}),API.model({...s,ask:r.V*s.optRho}))}; };
    const OLD=A.loadWith([['const K=A.knots_pct_over_value, seq=[["1-10",K[0]],["11-20",K[1]],["21-30",K[2]],["31-40",K[3]],["41-50",K[4]],[">50",A.open_knot]];',
      'const seq=[["1-10",10],["11-20",20],["21-30",30],["31-40",40],["41-50",50],[">50",100]];'],
      ["const PEER_SD={rec:.28,cc:MODELS.fitted.peer_sd.cc.v,own:.25,mgt:.28,grw:MODELS.fitted.peer_sd.grw.v,","const PEER_SD={rec:.28,cc:.13,own:.25,mgt:.28,grw:.13,"],
      ['cc=(C.by_industry[IND[ind]?ind:"prof"]||C).v;','cc=.16;']]);
    const o=noteOf(OLD), hit=o.nt.text.match(/another peak, at [\d.]+× value/);
    ok(OLD.GAP_CDF.g.join()==="0,10,20,30,40,50,100"&&OLD.GAP_TAIL_K>.00113&&!/There is no second peak/.test(o.nt.text)&&!!hit&&/1\.2\d×/.test(hit[0]),
       `40: MODEL-1 a dip deeper than 0.01% of value makes a real second peak, named in the note (old gap axis: ${hit?hit[0]:"none"})`);
    /* the live note: the fine-grid curve (.0025 steps, 8x the note's) has no other peak with a dip of 0.03% of value
       when the note says there is none, and the note names any that has one */
    const L=noteOf(A), th=L.s.theta, U=m=>{ const x=A.model({...L.s,ask:L.V*m}); return x.EVp+(1-x.PC)*th*x.V-L.s.lamT*x.tMean; };
    const ms=[], us=[]; for(let k=0;k<=280;k++){ ms.push(.80+k*.0025); us.push(U(ms[k])); }
    const jo=Math.round((L.s.optRho-.80)/.0025), deep=[];
    for(let j=1;j<us.length-1;j++) if(us[j]>=us[j-1]&&us[j]>=us[j+1]&&Math.abs(ms[j]-L.s.optRho)>.03){ let lo=us[j];
      for(let q=Math.min(j,jo);q<=Math.max(j,jo);q++) lo=Math.min(lo,us[q]); if(us[j]-lo>=3e-4*L.V) deep.push(ms[j]); }
    ok(L.s.optRho>A.RHO_MAX-.02&&(/There is no second peak/.test(L.nt.text)?!deep.length:deep.some(m=>L.nt.peak&&Math.abs(m-L.nt.peak.m)<=.025)),
       `40: MODEL-1 on the live gap axis the note agrees with the fine grid (${deep.length?"peaks at "+deep.map(m=>m.toFixed(3)):"no other peak"}): ${L.nt.text.slice(0,90)}`); }
  ok(/1\.87 at \$100-250k of revenue and 1\.90 at \$250-500k/.test(A.MODELS.value.soi_size_wedge.why)&&!/falls monotonically from 1\.90/.test(HTML)
     &&HTML.includes("that band implies 0.468"),"40: MODEL-2/3 the SOI wedge and the BIZCOMPS sigma are described as the tables have them");
  ok(HTML.includes("e^{${T_ELAST.toFixed(2)}\\\\,g}")&&HTML.includes("R(0.08)^{s}=${Math.pow(fanRatio(.08),FAN_S)")
     &&HTML.includes('row("Normalized earnings",S.ern,mny)')&&HTML.includes("raised only where IBBA&rsquo;s size band closes above the ask")
     &&HTML.includes("Math.abs((f-1)*100).toFixed(1)+'% on the fitted value")&&HTML.includes("a 5% higher ask changes expected proceeds by ")
     &&HTML.includes("(s.lamT>0?` Above model value"),"40: D1-D3, D5, D7-D9 the equations, the extrapolation table and the notes say what the model does");
  ok(HTML.includes("money(PHI*b.S)")&&HTML.includes("U=${tp(best.U.PC,1)}")&&HTML.includes("${r.nEng.toFixed(2)}\\\\text{ of }")
     &&HTML.includes(" is at or near the end of its range, so that row is an uneven difference")&&HTML.includes("return ` Left out: ${t.join(\"; \")}.`;"),
     "40: DISP-1/2/3/5 the captured synergy, the uneven sensitivity rows, the equations' precision and the pruned changes");
  ok(HTML.includes("if(!it.C.length) it.C=all.map(")&&HTML.includes("(grow||0)<(nar?4:2)")&&HTML.includes("var pick=spots[0], pk=Infinity;")
     &&HTML.includes("@media(max-width:359px){ .hero-stats .big .k .pv{white-space:normal} }")&&HTML.includes("#view-console .rail select{text-overflow:ellipsis")
     &&/@media print\{[\s\S]{0,400}-webkit-text-fill-color:#1b2335!important/.test(HTML),
     "40: VIS-1 to VIS-5 phone labels kept and clear, the badge wraps, dropdowns end in an ellipsis, gradient figures print in ink");
  /* ui-2 (a typed fractional buyer count) was refuted: the stress test keeps it by design, and invariant
     buyer-count-kept-as-typed pins it */
  ok(HTML.includes("if(tkw+13>L){ L=Math.ceil(tkw+13); IW=Wd-L-R; }"),"40: ui-1 the phone star map fits its money ticks");
}

/* ---- 41. the opening film's camera does not swing. The owner: "during the solar system the camera goes to the left
   then back to the right ... dont have it shake like that". The camera's path, run outside the browser: no channel
   overshoots a keyframe, the Sun closes on the centre of the frame monotonically during the dive and stays there ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8"), L=HTML.split("\n");
  const at=re=>L.findIndex(l=>re.test(l)), i0=at(/^\/\* ---- vectors/), i1=at(/^function project\(cam,p\)/);
  const tl=L.find(l=>/^var TL=\{P0:/.test(l)), hl=L.filter(l=>/^function (sm|cl|mix)\(/.test(l)).slice(0,3);
  let F=null;
  try{ F=new Function("var innerWidth=1440, innerHeight=900;\n"+tl+"\n"+hl.join("\n")+"\n"+L.slice(i0,i1+2).join("\n")
    +"\nreturn {camera:camera,project:project,track:track,SUN:SUN,KF:KF};")(); }catch(e){ F=null; }
  const C1=F?F.KF[8][0]:8.45;   /* the camera reaches the Sun: the keyframe whose target is the Sun */
  ok(!!F&&i0>0&&i1>i0,"41: the film's camera path evaluates outside the browser");
  if(F){
    const K=F.KF; let over=0, hit=0;
    for(let i=0;i+1<K.length;i++){
      for(let j=1;j<K[i].length;j++) if(Math.abs(F.track(K[i][0])[j-1]-K[i][j])>1e-12) hit++;
      for(let c=K[i][0];c<=K[i+1][0];c+=.005){ const k=F.track(c);
        for(let j=1;j<K[i].length;j++){ const lo=Math.min(K[i][j],K[i+1][j]), hi=Math.max(K[i][j],K[i+1][j]); if(k[j-1]<lo-1e-12||k[j-1]>hi+1e-12) over++; } } }
    ok(!over&&!hit,`41: the path passes through every keyframe and no channel overshoots one (${over} overshoots)`);
    const pos=c=>F.project(F.camera(c),F.SUN), rad=c=>{ const q=pos(c); return Math.hypot(q.x*1.6,q.y); };
    let off=0, worst=0; for(let c=C1;c<=13.6;c+=.01){ const r=rad(c); if(r>1e-6) off++; worst=Math.max(worst,r); }
    ok(!off,`41: once the camera arrives (c ${C1}) the Sun holds the centre of the frame until the jump (worst ${worst.toExponential(1)})`);
    let up=0, prev=Infinity; for(let c=6.9;c<=C1;c+=.005){ const r=rad(c); if(r>prev+1e-9) up++; prev=r; }
    ok(!up,`41: during the dive the Sun's offset from the centre only shrinks (${up} steps outward)`);
  }
}

/* ---- 42. third round, October 2026: definitions. Pepperdine states its valuation gap as a share of the seller's asking
   price (fit/round3_gap_axis.py): the penalty reads the buckets at p/(1-p) over value, the open bucket at 200% (judgment) ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const F=A.MODELS.fitted, GA=F.gap_axis, D=A.MODELS.close_and_timing.close_probability.valuation_gap_distribution, G=A.GAP_CDF;
  const B=["1-10","11-20","21-30","31-40","41-50",">50"], tot=B.reduce((a,k)=>a+D[k],0);
  ok(GA.edges_pct_of_ask.join()==="10,20,30,40,50"&&GA.edges_pct_of_ask.every((p,i)=>Math.abs(GA.knots_pct_over_value[i]-100*p/(100-p))<1e-3)
     &&GA.open_knot===200&&GA.was.knots_pct_over_value.join()==="10,20,30,40,50"&&GA.was.open_knot===100,
     "42: the bucket edges (10-50% of the ask) sit at p/(1-p) over value; the open bucket at 200% (was 10-50 and 100)");
  let c=0; const fOK=B.every((k,i)=>{ c+=D[k]; return Math.abs(G.f[i+1]-c/tot)<1e-12; });
  ok(G.g.join()===[0,...GA.knots_pct_over_value,GA.open_knot].join()&&G.f[0]===0&&fOK,"42: the penalty's distribution reads the knots and the shipped shares");
  ok(B.every(k=>Math.abs(GA.pool.shares[k]-D[k]/tot)<=GA.shares_check.max_abs_diff_vs_shipped+1e-9)&&GA.shares_check.max_abs_diff_vs_shipped<=.015,
     `42: the 2017-2026 pool stays within ${GA.shares_check.max_abs_diff_vs_shipped} of the shipped shares, which are kept`);
  /* the penalty: rising, and smooth through the last knot (the tail's rate is set from the slope there) */
  const P=A.gapPenalty, L=GA.open_knot, h=1e-3; let rise=true, prev=-1;
  for(let g=0;g<=600;g+=.25){ const v=P(g); if(v<prev-1e-12) rise=false; prev=v; }
  ok(rise&&P(600)<1&&Math.abs(P(L+h)-P(L-h))<1e-5&&Math.abs((P(L+h)-P(L))-(P(L)-P(L-h)))/h<2e-5,"42: the penalty rises and is smooth through the open bucket's knot");
  ok(Math.abs(A.GAP_TAIL_K-.000571)<5e-6,`42: the tail's rate halves with the wider axis (k ${A.GAP_TAIL_K.toPrecision(3)}, was 0.00114)`);
  /* what it changes: the share of the base closing rate an ask keeps, on the stated axis and on the old one */
  const OLD=A.loadWith([['const K=A.knots_pct_over_value, seq=[["1-10",K[0]],["11-20",K[1]],["21-30",K[2]],["31-40",K[3]],["41-50",K[4]],[">50",A.open_knot]];',
    'const seq=[["1-10",10],["11-20",20],["21-30",30],["31-40",40],["41-50",50],[">50",100]];']]);
  const kp=(API,r)=>Math.round(100*(1-API.gapPenalty((r-1)*100)));
  ok(kp(A,1.3)===75&&kp(OLD,1.3)===64&&kp(A,1.5)===62&&kp(OLD,1.5)===58,`42: an ask of 1.3x keeps ${kp(A,1.3)}% of the base rate (${kp(OLD,1.3)}% before), 1.5x ${kp(A,1.5)}% (${kp(OLD,1.5)}%)`);
  const ex={...{grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false},ind:"medical",rev:6e6,ern:1.45e6};
  const wa=API=>API.bestRatio(ex,.75,900);
  ok(Math.abs(wa(OLD)-1.15)<.01&&Math.abs(wa(A)-1.26)<.01,`42: the framework example's walk-away ask moves from ${wa(OLD).toFixed(3)} to ${wa(A).toFixed(3)} (the Data tab: about 1.15x to 1.26x)`);
  /* the page says so */
  ok(HTML.includes("Third round: definitions")&&HTML.includes("Where Pepperdine&rsquo;s price gaps sit against value")
     &&HTML.includes("walk-away ask moves from about 1.15&times; to 1.26&times;")&&HTML.includes("11&ndash;30% of the ask</b> (12&ndash;43% over value)")
     &&!/up to a\s+100% gap/.test(HTML),"42: the Data tab states the axis, the kill zone on both axes, and the third round's row");
  /* the peer table, third round (fit/round3_peer.py): retention by customer count, three retention medians and the MSPs'
     recurring share written into IND, car washes' margin, the largest customer's median and two peer spreads */
  const IND=A.IND, T=F.peer_rec_ret, INDS=Object.keys(IND);
  ok(T.ret.ecom.v===.25&&T.ret.auto.v===.45&&T.ret.rest.v===.27&&T.rec.msp.v===.42&&T.ret.ecom.was===.40&&T.ret.auto.was===.58&&T.ret.rest.was===.45&&T.rec.msp.was===.72
     &&IND.ecom.ret===.25&&IND.auto.ret===.45&&IND.rest.ret===.27&&IND.msp.rec===.42&&["ecom.ret","auto.ret","rest.ret","msp.rec"].every(c=>A.FITTED_CELLS.includes(c))
     &&!/ecom:[^\n]*ret:\.40|auto:[^\n]*ret:\.58|rest:[^\n]*ret:\.45|msp:[^\n]*rec:\.72|wash:[^\n]*gm:\.70/.test(HTML.slice(HTML.indexOf("const IND = {"),HTML.indexOf("const BANDS"))),
     "42: retention .25/.45/.27 (e-commerce, auto repair, restaurants) and the MSPs' recurring share .42 are written in; the typed cells are gone");
  const rp=T.ret.rest.parts;
  ok(Math.abs(T.ret.rest.v-Math.round(100*(rp.bloom_2025.retention+rp.steady_state_bridge.central)/2)/100)<1e-12&&rp.steady_state_bridge.r[1]===rp.steady_state_bridge.central&&T.ret.rest.se===.1,
     `42: restaurants read the middle of their source's range: (${rp.bloom_2025.retention} + ${rp.steady_state_bridge.central}) / 2, SE .10`);
  ok(/customers who bought/.test(T.definitions.ret)&&/not revenue/.test(T.definitions.ret)&&HTML.includes('<input type="range" id="i_ret" min="5" max="99"')
     &&HTML.includes("rl.title=MODELS.fitted.peer_rec_ret.definitions.ret")&&INDS.every(k=>IND[k].ret>=.05),
     "42: retention is counted in customers, the label says so, and the slider reaches every median (from 5%)");
  const W=F.peer_gm.by_industry.wash, K=F.peer_gm.knots_log10_rev;
  ok(IND.wash.gm===undefined&&K.every(x=>A.peerGm("wash",Math.pow(10,x))===.80)&&A.peerGm("wash",1e4)===.80&&A.peerGm("wash",1e9)===.80
     &&W.se[0]>W.se[1]&&W.se[3]>W.se[2]&&Math.min(...W.se)>=F.peer_gm.surveys.wash.detail.se&&A.gmDefinition("wash")===F.peer_gm.definition.wash
     &&!("wash" in F.peer_gm.not_identified),`42: car washes read a flat .80 (SE ${W.se.join("/")}, wider away from the measured sites' revenue)`);
  ok(INDS.every(k=>A.peerMedians(k,5e5,2e6).cc===(k==="mfg"?.19:.14))&&A.peerMedians("zzz",5e5,2e6).cc===.14&&F.peer_cc.was===.16,
     "42: the largest customer's median is .14, manufacturing .19 (was .16 everywhere)");
  const SENS=A.sensitivity({ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false});
  ok(A.PEER_SD.cc===F.peer_sd.cc.v&&A.PEER_SD.cc===.18&&A.PEER_SD.grw===F.peer_sd.grw.v&&A.PEER_SD.grw===.16&&F.peer_sd.cc.was===.13&&F.peer_sd.grw.was===.13
     &&["rec","own","mgt","gm","ret","fin","plt"].every(k=>A.PEER_SD[k]===({rec:.28,own:.25,mgt:.28,gm:.13,ret:.13,fin:.28,plt:.22})[k])
     &&SENS.some(v=>v.k==="cc"&&/\(18 pts\)/.test(v.unit))&&SENS.some(v=>v.k==="grw"&&/\(16 pts\)/.test(v.unit)),
     "42: growth's and the largest customer's peer spreads are .16 and .18 (were .13), and the sensitivity rows step by them");
  /* what it moves: a business at its industry's medians keeps its value; one typed at the old medians moves */
  { const at=(ind,ern,extra)=>{ const rev=ern/A.typMargin(ind,ern), P=A.peerMedians(ind,ern,rev);
      return A.model({ind,ern,rev,yrs:6,buyers:IND[ind].buyers||50,st:null,franchise:false,ask:1,...P,...extra}); };
    const z=at("rest",3e5,{}), o=at("rest",3e5,{ret:.45});
    ok(Math.abs(z.qz)<1e-12&&o.V>z.V&&at("wash",3e5,{gm:.70}).V<at("wash",3e5,{}).V,"42: at the medians the quality position is neutral; the old medians now read above (retention) or below (car-wash margin) them"); }
  ok(["Customer retention, by count, and three industries&rsquo; medians","Recurring revenue: IT services and MSPs","Peer median gross margin: car washes",
      "The largest customer&rsquo;s share: peer median and spread","The peer spread of revenue growth"].every(t=>HTML.includes(t))
     &&!/verifier|\blane\b|fit6|fit8|\/tmp\//.test(HTML.slice(HTML.indexOf("MODELS.fitted.peer_rec_ret="),HTML.indexOf("\n",HTML.indexOf("MODELS.fitted.peer_rec_ret="))))
     &&!/verifier|\blane\b|fit6|fit8|\/tmp\//.test(HTML.slice(HTML.indexOf("MODELS.fitted.peer_cc="),HTML.indexOf("/* Industry tailwind (fit/"))),
     "42: a Data tab row for every third-round fit, and no process notes in the embedded tables");
}

/* ---- 43. broker tools, October 2026: the debt-coverage check on SBA's change-of-ownership rules (SOP 50 10 8.1,
   Appendix 15), the add-back worksheet, a broker's deals against the model, and the seller report ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
  const S=A.SBA_COO, s0={...EX}, r0=A.model(s0), V=r0.V;
  ok(S.dsc.initial===1.25&&S.dsc.expansion===1.15&&S.dsc.buyout===1.25&&S.equity===.10&&S.standbyShare===.5&&S.amortYears===10
     &&S.maxLoan===5e6&&S.ownValuationMax===350000&&S.qoeMin===3e6&&/50 10 8\.1/.test(S.sop),"43: SBA's change-of-ownership rules as published (SOP 50 10 8.1)");
  /* the annuity */
  { const P=1e6, m=10/1200, want=12*P*m/(1-Math.pow(1+m,-120));
    ok(Math.abs(A.annualPayment(P,10,10)-want)<1e-6&&Math.abs(want-158580.88)<.01,`43: a year of payments on $1M at 10% over 10 years is $${want.toFixed(2)}`);
    ok(Math.abs(A.annualPayment(1.2e6,0,10)-1.2e5)<1e-9&&A.annualPayment(0,8,10)===0&&A.annualPayment(-5,8,10)===0,"43: at 0% the payment is the principal over the years; no loan, no payment"); }
  ok([2e5,8e5,2.55e6,4.25e6].every(L=>Math.abs(A.sbaRateLoan(L)-A.sbaRate(L/.85))<1e-12),"43: the loan's rate reads the same fitted spread table as the risk model's 85% loan");
  /* the coverage identities */
  { const f=A.debtCheck(s0,s0.ask,{},V), g=A.gmSalary(s0), mp=A.marketPay(s0);
    /* since round 9 the SBA guaranty fee is financed in the loan by default, a project cost in the structure's shares */
    ok(Math.abs(f.loan+f.cash+f.note-f.project)<1e-6&&f.fee>0&&Math.abs(f.fee-A.guarantyFee(f.loan))<1e-6&&Math.abs(f.project-(s0.ask+f.fee))<1e-6
       &&Math.abs(f.cash-.1*f.project)<1e-6&&Math.abs(f.note-.05*s0.ask)<1e-6,
       "43: the loan, buyer cash and seller note add up to the project, the price and the SBA fee (85/10/5 by default, the fee in the loan)");
    ok(Math.abs(mp-g*A.IVC.gm.loading)<1e-9&&A.IVC.gm.loading>1.1&&Math.abs(f.draw-mp)<1e-9&&f.drawMarket&&Math.abs(f.cf-(s0.ern-mp))<1e-6&&Math.abs(f.ds-f.sbaPay-f.notePay)<1e-9
       &&Math.abs(f.dscr-f.cf/f.ds)<1e-12&&Math.abs(f.sbaPay-A.annualPayment(f.loan,A.sbaRateLoan(f.loan),10))<1e-9&&Math.abs(f.notePay-A.annualPayment(f.note,6,10))<1e-9
       &&f.min===1.25&&f.ok===(f.dscr>=1.25)&&A.debtCheck(s0,s0.ask,{draw:1e5},V).draw===1e5&&!A.debtCheck(s0,s0.ask,{draw:1e5},V).drawMarket,
       `43: coverage is SDE less a GM's market pay with the employer's costs (x${A.IVC.gm.loading}) over the SBA and note payments (${f.dscr.toFixed(2)}x at the framework example)`);
    const sb=A.debtCheck(s0,s0.ask,{standby:true},V);
    ok(sb.notePay===0&&sb.debt===sb.loan&&Math.abs(sb.equityIn-(sb.cash+Math.min(sb.note,.5*sb.equityNeed)))<1e-6&&sb.dscr>f.dscr,
       "43: a note on full standby has no payments, leaves the debt, and counts toward equity for at most half of it");
    const lo=A.debtCheck(s0,s0.ask,{cash:.05},V), hi=A.debtCheck(s0,s0.ask,{cash:.2},V);
    ok(!lo.equityOK&&hi.equityOK&&hi.dscr>f.dscr,"43: 5% buyer cash fails SBA's 10% equity; 20% passes and lowers the payments");
    const ex=A.debtCheck(s0,2e6,{extra:3e5,type:"buyout"},V), ex2=A.debtCheck(s0,2e6,{extra:3e5},V);
    ok(Math.abs(ex.equityNeed-2e5)<1e-6&&Math.abs(ex2.equityNeed-.1*ex2.project)<1e-6&&Math.abs(ex2.project-(2.3e6+ex2.fee))<1e-6&&Math.abs(ex.project-(2.3e6+ex.fee))<1e-6,"43: an owner buyout's equity is 10% of the price, other types' 10% of the project");
    const big=A.debtCheck(s0,9e6,{},V);
    ok(big.loan===5e6&&big.over>0&&Math.abs(big.loan+big.cash+big.note-big.project)<1e-6&&big.qoe&&!A.debtCheck(s0,9e6,{type:"buyout"},V).qoe&&!A.debtCheck(s0,2.9e6,{},V).qoe,
       "43: above the 7(a) maximum the rest is buyer cash; a QoE from $3M except for an owner buyout");
    ok(A.debtCheck(s0,V*1.3,{},V).debtOverValue&&!A.debtCheck(s0,V*.9,{},V).debtOverValue&&!A.debtCheck(s0,V*3,{cash:.6,note:.4},V).debtOverValue,
       "43: debt above the value is flagged (SBA caps it at the business valuation), and only for a structure with an SBA loan");
    ok(A.debtCheck(s0,3e5,{},V).ownValuation&&!A.debtCheck(s0,4e5,{},V).ownValuation&&A.debtCheck(s0,3e5,{type:"buyout"},V).ownValuation
       &&HTML.includes("an owner buyout between existing owners is one)")&&!HTML.includes("the console takes an owner buyout as such"),
       "43: the lender may value a $350k business itself unless the parties are closely related, which an owner buyout is only between existing owners (r4-financing-9)");
    ok(A.debtCheck(s0,s0.ask,{type:"expansion"},V).min===1.15&&A.debtCheck({...s0,ern:5e4},s0.ask,{},V).dscr<0&&A.debtCheck(s0,1e6,{cash:1,note:0},V).dscr===Infinity,
       "43: 1.15x for an expansion; coverage goes negative when SDE is below the new owner's pay, and is infinite with no debt"); }
  /* shares that overrun the price, coverage with nothing left, inherited keys */
  { const over=A.debtCheck(s0,2e6,{cash:.9,note:.3},V), whole=A.debtCheck(s0,2e6,{cash:.9,note:.1},V), sb=A.debtCheck(s0,2e6,{cash:.9,note:.1,standby:true},V);
    ok(over.noteCut&&Math.abs(over.note-2e5)<1e-6&&over.loan===0&&Math.abs(over.cash+over.note+over.loan-over.project)<1e-6&&!A.debtCheck(s0,2e6,{},V).noteCut,
       "43: cash and a note typed to more than the price: the note is cut to what the cash leaves, and the parts still add up to the price");
    ok(whole.loan===0&&whole.sbaPay===0&&!sb.standby&&Math.abs(sb.notePay-A.annualPayment(sb.note,6,10))<1e-9&&sb.debt===sb.note&&sb.ds===sb.notePay&&/^\d+\.\d\d×$/.test(A.covFmt(sb)),
       "43: cash and a note that pay the whole price leave no loan; a note marked standby with no loan to stand behind is paid on its own terms");
    ok(A.debtCheck(s0,s0.ask,{},V).noteConv&&!A.debtCheck(s0,s0.ask,{note:.07,noteRate:7,noteYears:7},V).noteConv&&A.debtCheck(s0,s0.ask,{standby:true},V).noteConv&&!A.debtCheck(s0,s0.ask,{standby:true,note:.07},V).noteConv&&!A.debtCheck(s0,s0.ask,{note:0},V).noteConv,
       "43: a paid note on the starting structure's terms, or a standby note at its share, rests on that convention; the broker's own terms or no note do not (r5-financing-5)");
    const t=A.debtCheck(s0,2e6,{type:"constructor"},V), m=A.maxFinanced(s0,{type:"__proto__"},V);
    ok(t.min===1.25&&t.type==="initial"&&m.target===1.25&&m.type==="initial"&&A.recastSDE({weight:"constructor",years:[{rev:1e6,ni:1e5},{rev:9e5,ni:3e5}]}).sde===1e5
       &&A.dealsStats([{inputs:{...s0,ind:"constructor"},status:"closed",salePrice:1e6}]).n===0&&A.ownKey(A.IND,"medical")&&!A.ownKey(A.IND,"toString"),
       "43: inherited keys (constructor, __proto__) are not a transaction type, a basis or an industry"); }
  /* coverage as printed */
  ok(A.covFmt({ds:1,cf:1.1499,dscr:1.1499,min:1.15,ok:false})==="1.14×"&&A.covFmt({ds:1,cf:1.15,dscr:1.15,min:1.15,ok:true})==="1.15×"
     &&A.covFmt({ds:1,cf:1.24999,dscr:1.24999,min:1.25,ok:false})==="1.24×"&&A.covFmt({ds:1,cf:2.257,dscr:2.257,min:1.25,ok:true})==="2.25×"
     &&A.covFmt({ds:0,cf:5,note:0,loan:0,dscr:Infinity})==="no debt"&&A.covFmt({ds:5,cf:-3,dscr:-.6,min:1.25,ok:false})==="none",
     "43: coverage prints rounded down, never as a minimum it fails; 'none' with nothing left after the owner's pay");
  /* the highest price this structure finances */
  { const m=A.maxFinanced(s0,{},V), cm=A.debtCheck(s0,m.price,{},V), up=A.debtCheck(s0,m.price*1.0001,{},V);
    /* the debt is 90% of the price and of the fee financed (round 9) */
    ok(m.bind==="value"&&!cm.debtOverValue&&up.debtOverValue&&cm.dscr>=1.25&&Math.abs(cm.debt-V)/V<1e-6&&Math.abs(cm.debt-.9*(m.price+cm.fee))<1e-6&&Math.abs(m.covPrice-m.capAt)<1e-6,
       `43: at the framework example the valuation binds: the debt (90% of the price and the fee) reaches the model value at $${(m.price/1e6).toFixed(3)}M, where coverage would allow more`);
    const m0=A.maxFinanced(s0,{}), c0=A.debtCheck(s0,m0.price,{}), u0=A.debtCheck(s0,m0.price*1.0001,{});
    ok(m0.bind==="cap"&&m0.capped&&Math.abs(m0.price-m0.capAt)<1e-6&&Math.abs(c0.loan-5e6)<1e-3&&c0.over===0&&c0.dscr>=1.25&&u0.over>0,
       `43: with no valuation the search stops where the loan reaches the 7(a) maximum ($${(m0.price/1e6).toFixed(2)}M): past it the typed shares no longer hold`);
    const sL={...s0,ern:3e6,rev:1.5e7}, VL=A.model(sL).V, mL=A.maxFinanced(sL,{},VL);
    ok(VL>8e6&&mL.bind==="cap"&&Math.abs(mL.price-mL.capAt)<1e-6&&mL.price<VL,`43: a business worth $${(VL/1e6).toFixed(1)}M is not quoted ${(1/.05).toFixed(0)} times its value: the cap, not the valuation, sets the structure's limit ($${(mL.price/1e6).toFixed(2)}M)`);
    /* every structure: the price passes both tests, and a hair above it the named one fails */
    let edge=0, N=0;
    for(const f of [{},{cash:.2},{cash:.05},{standby:true},{note:.2},{extra:3e5},{capex:2e5},{draw:4e5},{type:"expansion"},{note:.3,noteRate:0,noteYears:30}])
      for(const s of [s0,{...s0,ern:4e5,rev:3e6},{...s0,ern:1.2e5,rev:9e5},{...s0,ern:4e6,rev:2e7}]){ const Vx=A.model(s).V, mx=A.maxFinanced(s,f,Vx); N++;
        if(!(mx.price>0&&isFinite(mx.price))){ edge++; continue; }
        const a=A.debtCheck(s,mx.price,f,Vx), b=A.debtCheck(s,mx.price*1.0001,f,Vx);
        if(a.dscr>=mx.target&&!a.debtOverValue&&a.over===0&&(mx.bind==="coverage"?b.dscr<mx.target:mx.bind==="value"?b.debtOverValue:b.over>0)) edge++; }
    ok(edge===N,`43: across ${N} businesses and structures the highest price passes coverage and the valuation, and the named test fails just above it (${edge})`);
    const sm={...s0,ern:4e5,rev:3e6}, m2=A.maxFinanced(sm,{});
    let mono=true, prev=Infinity; for(let p=2e5;p<m2.price*1.5;p*=1.07){ const c=A.debtCheck(sm,p,{}).dscr; if(c>prev+1e-12) mono=false; prev=c; }
    ok(mono,"43: coverage falls as the price rises");
    ok(A.maxFinanced(sm,{cash:.2}).price>m2.price&&A.maxFinanced(sm,{standby:true}).price>m2.price&&A.maxFinanced(sm,{type:"expansion"}).price>m2.price
       &&A.maxFinanced(sm,{capex:5e4}).price<m2.price&&A.maxFinanced(sm,{draw:2.5e5}).price<m2.price,
       "43: on coverage, more cash, a standby note or the 1.15x expansion floor finance more; capital spending or higher pay finance less");
    const eq=A.maxFinanced(s0,{cash:.05},V), eqx=A.maxFinanced(s0,{cash:.05,type:"expansion"},V);
    ok(eq.equityShort&&!eq.equityWaivable&&eqx.equityShort&&eqx.equityWaivable&&!m.equityShort,"43: under 10% buyer cash the equity minimum fails, waivable for an expansion but not an initial acquisition");
    const wc=A.maxFinanced(s0,{cash:.5,note:.5,extra:2e5},V), sbo=A.maxFinanced(s0,{cash:.1,note:.9,standby:true},V);
    ok(A.maxFinanced({...s0,ern:5e4,rev:5e5},{},V).price===0&&A.maxFinanced(s0,{cash:.6,note:.4},V).noLoan&&A.maxFinanced(s0,{cash:.6,note:.4},V).price===Infinity&&!wc.noLoan&&wc.price>0&&sbo.noLoan&&sbo.price===Infinity
       &&A.maxFinanced(s0,{extra:6e6}).price===0&&A.maxFinanced(s0,{extra:6e6}).bind==="cap",
       "43: no price when SDE does not cover the pay; no loan only when none is needed at any price (working capital still borrows); working capital past the cap is named, not a '$1k' answer");
    /* cash and a note over 100% with working capital: the note is cut to the price's share the cash leaves, so the loan never falls as the price rises */
    const cut=A.debtCheck(s0,2e6,{cash:.5,note:.6,extra:2e5},V);
    let rising=true, pl=-1; for(let p=1e5;p<2e7;p*=1.2){ const l=A.debtCheck(s0,p,{cash:.5,note:.6,extra:2e5},V).loan; if(l<pl-1e-6) rising=false; pl=l; }
    ok(cut.noteCut&&Math.abs(cut.note-1e6)<1e-6&&Math.abs(cut.loan-(1e5+.5*cut.fee))<1e-6&&cut.fee>0&&rising,"43: a note cut to fit leaves the working capital's loan, and the loan never falls as the price rises");
    ok(A.pctDown(.0996)==="9.9%"&&A.pctDown(.05)==="5%"&&A.pctDown(.1)==="10%"&&/net worth/.test(A.EQUITY_WAIVER)&&/active in the business for the last 24 months/.test(A.DSC_HINT.buyout)
       &&/under 24 months/.test(A.DSC_HINT.initial)&&!/new to/.test(A.DSC_HINT.initial)&&Object.values(A.DSC_TYPES).every(t=>t.length<=20),
       "43: a failing share prints rounded down; the waiver states SBA's conditions; each type's conditions sit under its short name");
    /* round 3: with working capital and a standby note an initial acquisition's equity passes only from some price up */
    const fE={cash:.06,note:.1,standby:true,extra:4e5}, mE=A.maxFinanced(s0,fE,V);
    ok(mE.price>0&&mE.equityFrom>0&&mE.equityFrom<mE.price&&!A.debtCheck(s0,mE.equityFrom*.99,fE,V).equityOK&&A.debtCheck(s0,mE.equityFrom*1.0001,fE,V).equityOK&&!mE.equityShort
       &&/Below about \$[\d.]+[kM] <span class="rp-b rp-a">published data<\/span> the buyer&rsquo;s equity, with the standby note&rsquo;s credit, is under SBA&rsquo;s 10% minimum, which cannot be waived for an initial acquisition, so the structure works only from that price up/.test(A.reportHTML(A.reportData(s0,{fin:fE}),{})),
       `43: an initial acquisition whose standby credit grows with the price works only from $${(mE.equityFrom/1e6).toFixed(2)}M up, and the report says so`);
    const fB={type:"buyout",cash:.07,note:0,extra:8e5}, mB=A.maxFinanced(s0,fB,V);
    ok(mB.equityTo>0&&mB.equityTo<mB.price&&A.debtCheck(s0,mB.equityTo*.99,fB,V).equityOK&&!A.debtCheck(s0,mB.equityTo*1.01,fB,V).equityOK,
       "43: an owner buyout's cash, measured against 10% of the price, passes only up to some price, which the check finds");
    /* the highest price is shown rounded down, so the figure shown passes */
    ok(A.moneyDown(1296951)==="$1.29M"&&A.moneyDown(1.3e6)==="$1.30M"&&A.moneyDown(398618)==="$398k"&&A.moneyDown(999700)==="$990k"&&A.moneyDown(99951)==="$99k",
       "43: the highest financed price prints rounded down at money's precision");
    /* no equity at all: eliminating the requirement bars working capital from the loan */
    const h0=A.reportHTML(A.reportData(s0,{fin:{type:"expansion",cash:0,note:.05,extra:3e5}}),{});
    ok(/if the lender eliminates the 10% equity/.test(h0)&&!/waives part of/.test(h0)&&(h0.match(/SBA then bars working capital from the loan/g)||[]).length===1&&/with none it must be eliminated/.test(h0),
       "43: with no equity the report says the lender would eliminate it, and that SBA then bars working capital from the loan");
    ok(/except for an owner buyout \(owners or employees active in the business for the last 24 months buying out an owner, or anyone else taking under half and not becoming the largest owner\) or an ESOP or cooperative purchase/.test(A.reportHTML(A.reportData({...s0,ask:3.5e6},{}),{})),
       "43: the Quality of Earnings exemption is SBA's owner buyout, as SBA defines it (a minority sale to anyone else included), and an ESOP or cooperative purchase (r6-financing-6), not any partner or employee");
    const hq=A.reportHTML(A.reportData({...s0,ern:2e5,rev:1.2e6,ask:9e5},{fin:{cash:.5,note:.5,noteYears:2}}),{});
    ok(/are covered only \d\.\d\d×/.test(hq)&&!/are covered 0\./.test(hq),"43: with no loan, a note's payments the cash left cannot meet are 'covered only'");
    ok(!/standby note/.test(A.reportHTML(A.reportData(s0,{fin:{cash:.05,note:0,standby:true}}),{}))&&!A.maxFinanced(s0,{cash:.05,note:0,standby:true},V).standby,
       "43: with no note, nothing speaks of a standby note"); }
  /* the add-back worksheet */
  { const ws={entity:"scorp",years:[{rev:6e6,ni:5e5,owner:2e5,ptax:15e3,perks:2e4,dep:8e4,int:3e4,once:2e4,pers:1e4},{rev:5.5e6,ni:4.5e5,owner:2e5,dep:7e4},{rev:5e6,ni:4e5,owner:1.9e5}]};
    const L=A.recastSDE({...ws,weight:"latest"}), W=A.recastSDE({...ws,weight:"w321"}), G=A.recastSDE({...ws,weight:"avg"});
    ok(L.sde===875000&&W.years[1].sde===720000&&W.years[2].sde===590000&&Math.abs(W.sde-4655000/6)<1e-6&&Math.abs(G.sde-2185000/3)<1e-6
       &&Math.abs(W.rev-34e6/6)<1e-6&&L.n===3&&Math.abs(L.grw-(6/5.5-1))<1e-12&&L.ni===5e5&&L.disc===3e4&&L.add===375e3&&L.less===0&&Math.abs(L.margin-875000/6e6)<1e-12,
       "43: SDE is income before taxes plus the owner's pay, perks, depreciation, interest and discretionary items; three bases and the growth");
    const neg=A.recastSDE({years:[{rev:1e6,ni:2e5,nonop:-12000}]}), pos=A.recastSDE({years:[{rev:1e6,ni:2e5,nonop:12000}]}), dep=A.recastSDE({years:[{rev:1e6,ni:2e5,dep:-8e4}]});
    ok(neg.sde===188000&&pos.sde===188000&&neg.flags.includes("neg_less")&&!pos.flags.includes("neg_less")&&A.recastSDE({years:[{rev:1e6,ni:2e5,rent:-6000}]}).sde===194000
       &&dep.sde===28e4&&dep.flags.includes("neg_add"),"43: a 'Less' line deducts whatever its sign and says so; an expense typed in parentheses is added back; below-market rent is a negative add-back");
    ok(A.recastSDE({entity:"ccorp",years:[{rev:1e6,ni:2e5,tax:3e4}]}).sde===23e4&&A.recastSDE({entity:"schc",years:[{rev:1e6,ni:2e5,tax:3e4}]}).flags.includes("tax_none"),
       "43: income taxes deducted above the income line are added back; Schedule C deducts none");
    const ro=A.recastSDE({weight:"avg",years:[{rev:2e6,ni:3e5},{rev:1.8e6}]}), rm=A.recastSDE({weight:"avg",years:[{rev:2e6,ni:3e5},{ni:2e5}]});
    ok(ro.n===1&&ro.sde===3e5&&Math.abs(ro.grw-(2/1.8-1))<1e-12&&ro.flags.includes("rev_only")&&rm.n===2&&rm.rev===2e6&&rm.sde===25e4&&rm.flags.includes("rev_missing"),
       "43: a year with revenue alone sets the growth and stays out of SDE; revenue is read on the years that have it");
    const two=A.recastSDE({weight:"avg",years:[{},{rev:2e6,ni:3e5},{rev:1.8e6,ni:2e5}]});
    ok(two.n===2&&two.sde===25e4&&A.recastSDE({weight:"latest",years:[{},{rev:2e6,ni:3e5}]}).sde===3e5&&two.grw===null,"43: blank years are left out; 'latest' reads the most recent year entered");
    const sc=e=>A.recastSDE({entity:e.ent,years:[{rev:1e6,ni:2e5,...e.y}]}).flags;
    ok(sc({ent:"schc",y:{owner:5e4}}).includes("schc_owner_pay")&&!sc({ent:"schc",y:{perks:5e3}}).includes("schc_owner_pay")&&sc({ent:"schc",y:{ptax:5e3}}).includes("ptax_none")
       &&sc({ent:"partnership",y:{ptax:5e3}}).includes("ptax_none")&&!sc({ent:"scorp",y:{ptax:5e3}}).includes("ptax_none"),
       "43: Schedule C flags an owner's pay (not a perk) counted twice; Schedule C and partnership flag payroll taxes nobody deducted");
    const rent=A.recastSDE({years:[{rev:1e6,ni:1e5,once:3e4,rent:-2.5e4}]});
    ok(rent.flags.includes("heavy_discretionary")&&Math.abs(rent.discShare-3e4/105e3)<1e-12,"43: below-market rent does not hide one-time add-backs from the 15% warning");
    const fall=A.recastSDE({years:[{rev:1e6,ni:1e5},{},{rev:1e6,ni:2e5}]});
    ok(fall.flags.includes("sde_falling")&&fall.cmp.join()==="0,2"&&A.recastNotes(fall).some(o=>/from two years before to the most recent year/.test(o.t)),"43: a falling year names the years it compared");
    ok(A.recastSDE({years:[{rev:1e6,ni:1e5,once:5e4}]}).flags.includes("heavy_discretionary")&&A.recastSDE({years:[{rev:1e6,ni:-3e5}]}).flags.includes("sde_nonpositive")
       &&A.recastSDE(ws).flags.length===0,"43: the worksheet flags heavy add-backs and no earnings, and nothing on clean entries");
    ok(A.recastSDE({}).n===0&&A.recastSDE({}).sde===0&&A.recastSDE(null).n===0,"43: an empty worksheet is no SDE, not an error");
    const rn=A.recastSDE({years:[{rev:1e6,ni:2e5,once:1e4,rent:-3e4}]});
    ok(rn.add===1e4&&rn.less===-3e4&&rn.sde===18e4,"43: a below-market rent counts with the deductions, so add-backs never read negative");
    const r2=A.recastSDE({years:[{rev:1e6,ni:2e5},{rev:9e5},{rev:8e5}]}), n2=A.recastNotes(r2).map(o=>o.t).join(" ");
    ok(r2.flags.includes("rev_only")&&r2.flags.includes("rev_unused")&&/The year before has revenue alone: it sets the growth/.test(n2)&&/Two years before has revenue alone, which counts for nothing/.test(n2),
       "43: a revenue-only year is named, and told apart from one that sets nothing");
    const E=A.RECAST_ENTITY;
    ok(/retirement contributions are not deducted/.test(E.partnership.perks)&&/^Dividends/.test(E.ccorp.nonop),"43: a partnership deducts no partner's retirement; a C corporation's dividends are inside its starting line");
    ok(/cost of goods sold \(Form 1125-E/.test(E.scorp.owner)&&/cost of goods sold \(Form 1125-E/.test(E.ccorp.owner)&&/^Charitable contributions, deducted inside the starting line/.test(E.ccorp.pers),
       "43: officer pay counted in cost of goods sold is part of the owner's pay; a C corporation's charitable gifts are inside its starting line");
    /* round 3: the report's notes and the revenue note cover only the years the basis reads */
    const lt=A.recastSDE({entity:"schc",weight:"latest",years:[{rev:1e6,ni:2e5,dep:1e4},{rev:9e5,ni:2e5,owner:5e4,nonop:-2e4}]}), w3=A.recastSDE({entity:"schc",weight:"w321",years:[{rev:1e6,ni:2e5,dep:1e4},{rev:9e5,ni:2e5,owner:5e4,nonop:-2e4}]});
    ok(lt.flags.includes("schc_owner_pay")&&!(lt.sdeFlags||[]).includes("schc_owner_pay")&&!(lt.sdeFlags||[]).includes("neg_less")&&(w3.sdeFlags||[]).includes("schc_owner_pay")
       &&!A.recastSDE({weight:"latest",years:[{rev:1e6,ni:2e5},{ni:1.5e5}]}).flags.includes("rev_missing")&&A.recastSDE({weight:"avg",years:[{rev:1e6,ni:2e5},{ni:1.5e5}]}).flags.includes("rev_missing"),
       "43: on the latest basis the report's notes and the missing-revenue note leave out years the SDE does not read");
    const nr=A.recastSDE({weight:"avg",years:[{rev:-1e6,ni:2e5},{rev:1e6,ni:3e5}]});
    ok(nr.rev===1e6&&!nr.years[0].hasRev,"43: a negative revenue is no revenue");
    ok(/^The most recent year and the year before have revenue alone: they set the growth and stay out of SDE\.$/.test(A.recastNotes(A.recastSDE({years:[{rev:1e6},{rev:9e5},{rev:8e5,ni:1e5}]})).find(o=>o.k==="rev_only").t),
       "43: two revenue-only years take a plural verb");
    ok(Object.values(E).every(e=>e.ni&&e.n&&e.src)&&/Leave blank/.test(E.schc.ptax)&&/Leave blank/.test(E.schc.tax)&&/Leave blank/.test(E.partnership.ptax)&&/2% shareholder/.test(E.scorp.perks)
       &&/Schedule K/.test(E.scorp.nonop)&&/cost of goods sold/.test(E.ccorp.dep)&&A.RECAST_ROWS.some(R=>R.k==="tax"&&R.pos),"43: each source's hints name its lines and what the form already leaves out"); }
  /* a broker's deals against the model */
  { const d0={inputs:{...s0},listPrice:3.6e6}, P=A.dealPredict(d0), rA=A.model({...s0,ask:3.6e6});
    ok(P.pc===rA.PC&&P.priceMed===rA.Vreal&&P.pExp===rA.Vmean&&P.tMed===rA.tMed&&P.V===rA.V&&Math.abs(P.gap-(3.6e6/rA.V-1)*100)<1e-9&&P.pVar>0
       &&Math.abs(P.tVar-Math.PI*Math.PI/(3*rA.betaT*rA.betaT))<1e-12&&Math.abs(P.F-A.gapPenalty(P.gap)/A.PEN_MAX)<1e-12
       &&A.dealPredict({inputs:{...s0},listPrice:.8*V}).F===0&&A.dealPredict({inputs:{...s0},listPrice:3.5*V}).F===null,
       "43: a deal is predicted by today's model at its listing price: its expected price, median, spread and F");
    ok(P.z.own===-Math.max(-3.2,Math.min(3.2,rA.z.own))&&P.z.mgt===Math.max(-3.2,Math.min(3.2,rA.z.mgt)),"43: the quality factors are signed so that higher is better");
    const ls=A.sampleSummary([1.2,1.2,1.2],false), lv=A.sampleSummary([1.2,1.1,1.3],false,.04), lw=A.sampleSummary([1.2,1.1,1.3],false);
    ok(Math.abs(ls.factor-1.2)<1e-12&&ls.n===3&&Math.abs(ls.shrunk-(1+.2*3/13))<1e-12&&A.CALIB_K===10&&A.sampleSummary([]).n===0&&lv.df===12&&lw.df===2
       &&Math.abs(lv.se-Math.sqrt((10*.04+.02)/12/3))<1e-12&&lv.hi-lv.lo>lw.hi-lw.lo&&Math.abs(A.sampleSummary([Math.log(2)],true).factor-2)<1e-12,
       "43: the record's factor, its read with the weight of ten deals, and an interval that pools the model's spread as ten deals");
    ok(A.t95(2)===2.92&&A.t95(30)===1.697&&Math.abs(A.t95(31)-1.6955)<5e-4&&Math.abs(A.t95(1e6)-1.6449)<1e-3&&A.t95(0)===null,"43: Student's t at 95% by degrees of freedom");
    const day=(t,n)=>new Date(Date.parse(t)+n*864e5).toISOString().slice(0,10);
    const deals=[2.8e6,3.2e6,3.6e6].map(L=>{ const d={inputs:{...s0},listPrice:L,status:"closed",listDate:"2025-01-06"}, p=A.dealPredict(d);
      return {...d,salePrice:p.pExp*1.1,closeDate:day("2025-01-06",Math.round(2*p.tMed))}; });
    deals.push({inputs:{...s0},listPrice:4.2e6,status:"withdrawn"},{inputs:{...s0},listPrice:3e6,status:"expired"},{inputs:{...s0},status:"valuing"},{inputs:{ind:"nope"}});
    const D=A.dealsStats(deals), D2=A.dealsStats([...deals,{inputs:{...s0},listPrice:3e6,status:"closed",listDate:"2025-01-06",closeDate:"2025-09-01"}]);
    ok(D.n===6&&D.closed===3&&D.done===5&&Math.abs(D.price.factor-1.1)<1e-12&&D.price.lo<1.1&&D.price.hi>1.1&&Math.abs(D.time.factor-2)<.005
       &&Math.abs(D.close.obs-.6)<1e-12&&Math.abs(D.close.pred-[...deals.slice(0,5)].reduce((a,d)=>a+A.dealPredict(d).pc,0)/5)<1e-12&&!D.pen.ready&&!D.quality.ready
       &&D2.time.n===4&&D2.price.n===3,"43: on synthetic deals the record reads back what was put in (1.1x the expected price, 2x the median time, 3 of 5 closed); a closed deal without a sale price still counts its days");
    ok(A.daysBetween("2025-01-01","2025-03-02")===60&&A.daysBetween("x","2025-01-01")===null,"43: days between two dates");
    ok(typeof Object.getOwnPropertyDescriptor(D,"pen").get==="function"&&typeof Object.getOwnPropertyDescriptor(D,"quality").get==="function"&&D.pen===D.pen,
       "43: the two fits are computed when first read, once: the records beside the console need neither");
    /* deals that sell as the model says read 1: sales drawn from each deal's own price distribution */
    const mk=[], inds=Object.keys(A.IND); let sd=3; const rnd=()=>{ sd=(sd*1664525+1013904223)>>>0; return (sd+.5)/4294967296; };
    for(let i=0;i<60;i++){ const s={...s0,ind:inds[i%inds.length],ern:2e5*Math.pow(10,rnd())}; s.rev=s.ern/(.1+.15*rnd());
      const Vx=A.model({...s,ask:1e6}).V, d={inputs:{...s,ask:Vx},listPrice:Vx*(.8+.7*rnd()),status:"closed"}, p=A.dealPredict(d), r=A.model(p.s);
      mk.push({p,r}); }
    let sum=0, M=0; for(const o of mk) for(let j=0;j<40;j++){ sum+=o.r.q((j+.5)/40)/o.p.pExp; M++; }
    ok(Math.abs(sum/M-1)<.003,`43: sales drawn from the model's own price distributions read ${(sum/M).toFixed(4)}x its expected price (a mean of logs against the median read 0.90)`);
    let cov=0, B=0; for(let b=0;b<300;b++){ const k=[0,1,2].map(()=>mk[Math.floor(rnd()*mk.length)]), x=k.map(o=>o.r.q(rnd())/o.p.pExp);
      const S=A.sampleSummary(x,false,k.reduce((a,o)=>a+o.p.pVar,0)/3); B++; if(S.lo<=1&&1<=S.hi) cov++; }
    ok(cov/B>=.86,`43: with three deals drawn from the model, the 90% price interval covers 1 in ${(100*cov/B).toFixed(0)}% of 300 brokers`);
    /* the penalty scale and the broker's own close rate, fitted together from simulated listings: P(close) = min(.95, c b)(1 - pen F) */
    /* mulberry32: a linear congruential stream's successive draws are correlated enough to bias a simulation like this one */
    const mul=a=>()=>{ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
    const sim=(rn,c,pen)=>{ const o=[]; for(let i=0;i<2500;i++){ const b=.5+.3*rn(), up=rn()<.4, gap=up?5+45*rn():-10*rn(), F=up?A.gapPenalty(gap)/A.PEN_MAX:0;
      o.push({b,F,gap,y:rn()<Math.min(.95,c*b)*(1-pen*F)?1:0}); } return o; };
    const fp=A.fitPenaltyScale(sim(mul(11),1.2,.3)), fq=A.fitPenaltyScale(sim(mul(12),.85,.45)), se=f=>(f.hi-f.lo)/3.29;
    ok(Math.abs(fp.pen-.3)<3*se(fp)&&Math.abs(fp.c-1.2)<.08&&Math.abs(fq.pen-.45)<3*se(fq)&&Math.abs(fq.c-.85)<.08&&fp.hi-fp.lo<.25&&fp.lo<fp.pen&&fp.pen<fp.hi&&fp.n===2500&&fp.nAbove>0,
       `43: the penalty scale is recovered beside the broker's own close rate: ${fp.pen.toFixed(3)} (${fp.lo.toFixed(2)}-${fp.hi.toFixed(2)}) for .30 at c ${fp.c.toFixed(2)}; ${fq.pen.toFixed(3)} for .45 at c ${fq.c.toFixed(2)}`);
    const X=[[1,0,1],[1,1,0],[1,2,1],[1,3,3],[1,4,2]], ols=A.olsFit(X,X.map(r=>1+1.5*r[1]-.5*r[2]));
    ok(ols&&Math.abs(ols.beta[0]-1)<1e-9&&Math.abs(ols.beta[1]-1.5)<1e-9&&Math.abs(ols.beta[2]+.5)<1e-9&&A.olsFit([[1,1],[1,1],[1,1]],[1,2,3])===null,
       "43: least squares recovers an exact fit and refuses a singular design");
    /* a factor that never varies is left out of the quality fit and named, so the fit still runs */
    const qd=[]; for(let i=0;i<64;i++){ const s={...s0,rec:.2+.7*rnd(),cc:.05+.5*rnd(),gm:.3+.6*rnd(),ret:.5+.45*rnd(),plt:.1+.8*rnd(),grw:-.1+.4*rnd(),
        mgt:[.08,.36,.66,.92][i%4],fin:[.14,.45,.74,.96][(i>>2)%4]}; const d={inputs:s,listPrice:s.ask,status:"closed"}; d.salePrice=A.dealPredict(d).pExp*(.9+.2*rnd()); qd.push(d); }
    const Q=A.dealsStats(qd).quality;
    ok(Q.enough&&Q.ready&&Q.dropped.includes("own")&&!Q.dims.includes("own")&&Q.beta.length===Q.dims.length,`43: the quality fit runs without a factor that never varies (${Q.dropped.join(", ")} left out)`);
    ok(A.DEAL_MIN.pen===20&&A.DEAL_MIN.penAbove===5&&A.DEAL_MIN.penGap===10&&A.DEAL_MIN.quality===60&&A.DEAL_DONE.join()==="closed,withdrawn,expired",
       "43: the fits wait for 20 finished listings (5 at least 10% above value) and 60 closed deals"); }
  /* the seller report */
  { const s={...s0}, D=A.reportData(s,{date:"October 16, 2026"}), rs=A.bestRatio(s,0,0), rw=A.bestRatio(s,s.theta,s.lamT), mS=A.model({...s,ask:V*rs});
    ok(Math.abs(D.sell.ask-V*rs)<1e-6&&Math.abs(D.walk.ask-V*rw)<1e-6&&D.sell.pc===mS.PC&&D.sell.ev===mS.EVp&&D.sell.tMed===mS.tMed&&D.sell.price===mS.Vreal&&D.sell.mean===mS.Vmean
       &&D.cur.ask===s.ask&&D.V===V&&D.same===(Math.abs(rs-rw)<.005)&&D.maxFin.price===A.maxFinanced(s,undefined,V).price,"43: the report's asks are the optimizer's, each read off the model at that ask");
    ok(D.fixes.every(t=>t.net>0&&t.k!=="reprice")&&D.fixes.length<=3&&D.sens.length>0&&D.sens.length<=3&&D.sens.every((g,i)=>g.gain>V*.001&&(i===0||D.sens[i-1].gain>=g.gain)),
       "43: the report lists only fixes that pay and the largest value levers, largest first");
    const RB=A.RAIL_BEST, sl=id=>{ const m=HTML.match(new RegExp('id="'+id+'" min="(-?\\d+)" max="(-?\\d+)"')); return m&&[+m[1]/100,+m[2]/100]; };
    const opt=id=>{ const i=HTML.indexOf('<select id="'+id+'">'), j=HTML.indexOf("</select>",i); return [...HTML.slice(i,j).matchAll(/value="([\d.]+)"/g)].map(m=>+m[1]); };
    ok(RB.rec===sl("i_rec")[1]&&RB.gm===sl("i_gm")[1]&&RB.ret===sl("i_ret")[1]&&RB.grw===sl("i_grw")[1]&&RB.cc===sl("i_cc")[0]&&RB.plt===sl("i_plt")[0]
       &&RB.own===Math.min(...opt("i_own"))&&RB.mgt===Math.max(...opt("i_mgt"))&&RB.fin===Math.max(...opt("i_fin")),"43: the levers' best settings are the rail's own ends and options");
    const keys=x=>A.reportData(x,{}).sens.flatMap(g=>g.keys);
    ok(["rec","cc","gm","ret","plt","fin"].every(k=>!keys({...s,[k]:RB[k]}).includes(k)),"43: a lever already at its best on the rail is not offered as a gain");
    const all={...s,...RB}, Dall=A.reportData(all,{}), hall=A.reportHTML(Dall,{});
    ok(Dall.sens.length===0&&/no single factor, even at its best, moves the value/.test(hall),"43: with every factor at its best the report says no single factor moves the value");
    const tie=D.sens.find(g=>g.n>1);
    ok(!!tie&&tie.keys.every((k,i)=>i===0||["own","mgt","rec","cc","fin","grw","gm","ret","plt"].indexOf(tie.keys[i-1])<["own","mgt","rec","cc","fin","grw","gm","ret","plt"].indexOf(k)),
       "43: levers worth the same (the seven weighted equally) are one line, in the console's order, not ranked by rounding");
    const D2=A.reportData({...s,rhoSell:rs,optRho:rw},{});
    ok(D2.sell.ask===D.sell.ask&&D2.walk.ask===D.walk.ask,"43: the render's own optima give the same asks");
    const h=A.reportHTML(D,{business:"Lakeside <script>alert(1)</script> & Co",broker:"Pat Lee",firm:"Main Street Advisors",preparedFor:"Dr. Ortiz"});
    ok(!/NaN|undefined|Infinity/.test(h)&&h.includes("Lakeside &lt;script&gt;alert(1)&lt;/script&gt; &amp; Co")&&!h.includes("<script>")&&h.includes(A.money(V))
       &&h.includes("SOP 50 10 8.1")&&["rp-f","rp-a","rp-j"].every(c=>h.includes(c))&&h.includes("not an appraisal")&&h.includes("Pat Lee, Main Street Advisors")&&/closely related/.test(h),
       "43: the report escapes what is typed into it, states the value, cites its sources and badges every figure");
    const bx=(t,c,w)=>new RegExp(t+'<span class="rp-bx"><span class="rp-b rp-'+c+'">'+w+'</span><span class="rp-b rp-j rp-x">× judgment</span></span>').test(h);
    ok(Math.abs(D.qFactor-1)>.005&&bx("Model value ","f","fitted")&&bx("Chance it sells<br>","a","published data")&&bx("Median time to close if it sells<br>","f","fitted")&&bx("Lender coverage<br>","f","fitted"),
       "43: the report gives each figure the console's tier: judgment enters the value, the odds and the time above value, and coverage");
    ok(h.includes("before the quality position, "+A.money(D.point))&&/\$900 a day/.test(h)&&/an initial acquisition/.test(h),"43: accuracy names the fitted value it is about; the cost of delay is exact; the minimum names the transaction type");
    const X=A.reportHTML(A.reportData({...s,ern:4e7,rev:1.2e8,ask:1e8},{}),{});
    ok(/Extrapolated, outside the fitted data/.test(X)&&/past the 99th percentile/.test(X)&&/Low: outside the fitted data/.test(X),"43: an extrapolated value says so, as the console does");
    const he=A.reportHTML(A.reportData(s,{fin:{cash:.05,extra:3e5,capex:1450}}),{});
    ok(/<b>Equity:<\/b>/.test(he)&&/cannot be waived/.test(he)&&/working capital and closing costs/.test(he)&&/\$1\.45k of capital spending/.test(he)&&/Lender: [^<]*buyer equity under SBA&rsquo;s 10%/.test(he),
       "43: the lender section reports a failed equity minimum, names the costs it finances and echoes an entered amount exactly");
    const hn=A.reportHTML(A.reportData(s,{fin:{cash:.6,note:.4}}),{});
    ok(/no SBA loan is needed/.test(hn)&&!/SBA loan of \$0/.test(hn)&&!/minimum for an/.test(hn),"43: with no SBA loan the lender section says so instead of testing a $0 loan");
    ok(/Lender: debt \$[\d.]+[kM] (<span class="rp-bx">.*?<\/span><\/span>|<span class="rp-b rp-f">fitted<\/span>) over value/.test(h)&&D.sell.fin.debtOverValue,"43: an ask whose acquisition debt is above the value is flagged in the asks table, with its badge (r6-financing-2)");
    const hx=A.reportHTML({...A.reportData({...s,lamT:1450},{}),s:{...s,lamT:1450}},{});
    ok(/\$1,450 a day/.test(hx),"43: a $1,450-a-day cost of delay prints as itself, not $1k");
    const neg=A.reportHTML({...A.reportData({...s,ern:5e4},{}),s:{...s,ern:5e4}},{});
    ok(/nothing is left to pay acquisition debt/i.test(neg)&&!/−\d\.\d\d×|-\d\.\d\d×/.test(neg),"43: with nothing left after the new owner's pay the report says so instead of printing a negative coverage");
    /* r3-core-4: working capital financed in the loan whose payments alone break coverage is what leaves no price */
    const fWC={extra:1.5e6}, sWC={...s0,ern:3e5,rev:1.2e6,ask:9e5}, DWC=A.reportData(sWC,{fin:fWC}), hWC=A.reportHTML(DWC,{}), zWC=A.noPriceWC(sWC,fWC,DWC.V);
    ok(DWC.maxFin.price===0&&DWC.maxFin.bind==="coverage"&&!!zWC&&zWC.cf>0&&zWC.dscr<zWC.min&&Math.abs(zWC.loan-.9*(1.5e6+zWC.fee))<1&&zWC.fee>0
       &&hWC.includes(`The working capital and closing costs financed in the loan, with the SBA fee, ${A.money(zWC.loan)}, already take ${A.money(zWC.ds)} a year of payments before any price`)&&!/does not cover any loan/.test(hWC)
       &&A.noPriceWC({...s0,ern:5e4},{},V)===null&&/After the new owner&rsquo;s pay the business does not cover any loan/.test(neg)&&A.maxFinanced(sWC,{},DWC.V).price>0,
       `43: when the working capital in the loan alone breaks coverage (${zWC?A.covFmt(zWC)+" on "+A.money(zWC.loan):"not found"}) the report names it; with nothing left after the pay it still says so`);
    const C=A.sampleSummary([1.05,1.1,1,1.08],false,.04), hc=A.reportHTML({...D,calib:C},{});
    ok(hc.includes("Track record <span class=\"rp-b rp-j\">judgment")&&!h.includes("Track record")&&hc.includes(C.shrunk.toFixed(2)+"×")&&hc.includes(A.money(D.sell.mean*C.shrunk))&&/expected price/.test(hc),
       "43: the track-record line appears only when the broker opts in, against the expected price, badged as judgment");
    const Rh=A.recastSDE({years:[{rev:6e6,ni:5e5,once:2e5}]}), hh=A.reportHTML({...D,recast:Rh},{});
    ok(Rh.flags.includes("heavy_discretionary")&&(hh.match(/one-time and discretionary add-backs are/gi)||[]).length===1,"43: the earnings basis states the add-back share once");
    const hL=A.reportHTML(A.reportData({...s0,ern:3e6,rev:1.5e7},{}),{});
    const hL0=A.reportHTML(A.reportData({...s0,ern:3e6,rev:1.5e7},{fin:{note:0}}),{}), hLs=A.reportHTML(A.reportData({...s0,ern:3e6,rev:1.5e7},{fin:{standby:true}}),{});
    ok(/reaches the 7\(a\) maximum of \$5\.00M at about <b>\$[\d.]+M<\/b> <span class="rp-bx"><span class="rp-b rp-a">published data<\/span><span class="rp-b rp-j rp-x">× judgment<\/span><\/span>/.test(hL)
       &&/reaches the 7\(a\) maximum of \$5\.00M at about <b>\$[\d.]+M<\/b> <span class="rp-b rp-a">published data<\/span>/.test(hL0)&&/a higher price takes more buyer cash/.test(hL)
       &&/× judgment<\/span><\/span>, with coverage/.test(hLs)&&/the seller-note convention \(the highest financed price\)/.test(hL)&&!/the seller-note convention \(the highest financed price\)/.test(hL0),
       "43: where the loan's cap sets the limit the report says so: the published rule, and at the starting 5% note (paid or on standby) the note convention too, named in the footer (r4-financing-11)");
    const R=A.recastSDE({years:[{rev:6e6,ni:5e5,owner:2e5,once:2e5,nonop:5e4}]}), hr=A.reportHTML({...D,recast:R},{});
    ok(hr.includes("Earnings basis")&&hr.includes(A.money(R.sde))&&hr.includes("documentation")&&hr.includes("add-backs "+A.money(4e5))&&hr.includes("less "+A.money(5e4))&&!h.includes("Earnings basis"),
       "43: the earnings basis appears when the worksheet set the SDE, with add-backs and deductions apart");
    const Rs=A.recastSDE({entity:"schc",years:[{rev:1e6,ni:2e5,owner:5e4}]});
    ok(A.reportHTML({...D,recast:Rs},{}).includes("counts it twice"),"43: the report repeats the Schedule C double count");
    /* round 3: entered amounts at three figures; a small share with a decimal; no basis phrase for one year */
    const Rx=A.recastSDE({years:[{rev:5e5,ni:3e4,owner:15500,pers:300}]}), hx2=A.reportHTML({...A.reportData({...s0,ern:45500,rev:5e5,ask:1.4e5},{}),recast:Rx},{});
    ok(/SDE of \$45\.8k, built by the broker from 1 year of Form 1120-S returns:/.test(hx2)&&/income before taxes \$30k, add-backs \$15\.8k/.test(hx2)&&/SDE \$45\.5k/.test(hx2)&&/are 0\.7% of SDE/.test(hx2),
       "43: the report echoes entered amounts as their boxes do, a small add-back share with a decimal, and no weighting for one year");
    const hr2=A.reportHTML({...A.reportData(s0,{}),recast:{...A.recastSDE({years:[{rev:6e6,ni:5e5},{rev:5e6,ni:4e5}]}),entity:"toString",weight:"constructor"}},{});
    ok(/of financial statements and read on the most recent year/.test(hr2)&&!/function|native code/.test(hr2),"43: the report's earnings basis ignores an inherited source or basis key");
    ok(/all:revert/.test(A.RP_CSS)&&!/@page/.test(A.RP_CSS)&&/^@page\{size:letter;margin:\.3in \.4in\}/.test(A.RP_PAGE)&&/break-inside:avoid/.test(A.RP_CSS)&&/overflow-wrap:anywhere/.test(A.RP_CSS)
       &&A.hEsc('<a href="x">&')==="&lt;a href=&quot;x&quot;&gt;&amp;","43: the paper's stylesheet stands alone, wraps long names and keeps the page size apart, for the report alone");
    /* round 2. Past the 7(a) maximum the asks meet the equity minimum with buyer cash: the equity sentence is bounded by the cap */
    const sB={...s0,ern:5e6,rev:2e7,ask:2e7}, DB=A.reportData(sB,{fin:{cash:.05,note:0}}), hB=A.reportHTML(DB,{});
    const mB=DB.maxFin, eqAt=p=>A.debtCheck(sB,p,{cash:.05,note:0},DB.V).equityOK;
    ok(mB.capped&&mB.equityShort&&DB.cur.fin.equityOK&&DB.cur.fin.over>0&&mB.equityAbove>mB.capAt*1.01&&!eqAt(mB.equityAbove*.999)&&eqAt(mB.equityAbove*1.001)&&!eqAt((mB.capAt+mB.equityAbove)/2)
       &&hB.includes(`at every price below about ${A.moneyUp(mB.equityAbove)} <span class="rp-b rp-a">published data</span>: past ${A.moneyDown(mB.capAt)} <span class="rp-b rp-a">published data</span> the SBA loan stays at the 7(a) maximum and the rest of the price is buyer cash`)&&!/no price meets/.test(hB),
       `43: past the 7(a) maximum the report does not say no price meets the equity minimum, and bounds the shortfall where buyer cash reaches 10% (${A.money(mB.equityAbove||0)}), not at the cap (${A.money(mB.capAt||0)})`);
    /* a lever is quoted at the model's own forward step, one peer sd toward its best (the unit the console's sensitivity ranks
       every lever in, selects included: r3-report-6, refuted), at its best when that is nearer, or at its best when one step
       does not register (past the -3.2 z limit, r3-report-7); a factor past the +3.2 limit has nothing to give */
    const to=(x,k,kind)=>{ const v=A.sensitivity(x).find(r=>r.k===k), best=A.RAIL_BEST[k]; return kind==="room"||kind==="far"?best:x[k]+(v.inv?-2*v.h:2*v.h); };
    const rng=k=>opt("i_"+k).length?[Math.min(...opt("i_"+k)),Math.max(...opt("i_"+k))]:[Math.min(...sl("i_"+k)),Math.max(...sl("i_"+k))];
    const fwd=(x,k,kind)=>A.model({...x,[k]:to(x,k,kind)}).V-A.model(x).V, onRail=(k,y)=>y>=rng(k)[0]-1e-9&&y<=rng(k)[1]+1e-9;
    const sG={...s0,ind:"dist",rev:6e6,ern:1.45e6,gm:.733}, DG=A.reportData(sG,{});
    const sF={...s0,...RB,gm:sl("i_gm")[0],ret:sl("i_ret")[0]}, DF=A.reportData(sF,{}), hF=A.reportHTML(DF,{}), VF=A.model(sF).V;
    const pool=[sG,s0,{...s0,ret:.368},sF,{...s0,own:.95,mgt:.08,fin:.14},{...s0,own:.42,mgt:.66,fin:.74}];
    ok(Math.abs(fwd(sG,"gm","step"))<1&&A.sensitivity(sG).find(r=>r.k==="gm").dV>1e4&&!DG.sens.some(g=>g.keys.includes("gm"))&&DG.sens.length>0
       &&pool.every(x=>A.reportData(x,{}).sens.every(g=>g.keys.every(k=>Math.abs(fwd(x,k,g.kind)/g.gain-1)<.006&&onRail(k,to(x,k,g.kind))
         &&["step","room","far"].includes(g.kind)))),
       "43: a factor past the upper z limit is not offered (its central slope is not a step it has); every lever quoted is the model's own value, within the lever's range");
    const gO=D.sens.find(g=>g.keys.includes("own")), hO=A.sensitivity(s0).find(r=>r.k==="own").h;
    ok(s0.own===.72&&gO&&gO.full&&Math.abs(gO.gain-(A.model({...s0,own:.72-2*hO}).V-V))<1e-6&&h.includes("<b>Owner independence</b>: one peer step better is worth about "+A.money(gO.gain)),
       `43: a select lever moves one peer step, as the console's sensitivity ranks every lever (owner independence .72 to ${(.72-2*hO).toFixed(2)}: ${A.money(gO&&gO.gain)})`);
    const fF=DF.sens.filter(g=>g.kind==="far");
    ok(fF.length>0&&fF.every(g=>g.keys.every(k=>A.model({...sF,[k]:to(sF,k,"step")}).V-VF<=VF*.001))&&fF.some(g=>g.keys.includes("ret"))&&DF.sens.some(g=>g.kind==="step"&&g.keys.includes("gm"))
       &&/too far below its peers for one step to register; at its best it would add about/.test(hF)&&!/already at its best/.test(hF),
       "43: gross margin and retention at the rail's worst, the rest at their best: the report quotes gross margin's step and what retention, too far below its peers for a step, adds at its best; not that every factor is at its best");
    /* the reviewer's own state: a SaaS business with both at the rail's worst, at the 85th percentile */
    const sS={...s0,...RB,ind:"saas",ern:3.7e6,rev:9.6e6,gm:.12,ret:.05}, DS=A.reportData(sS,{}), hS=A.reportHTML(DS,{});
    ok(["gm","ret"].every(k=>DS.sens.some(g=>g.kind==="far"&&g.keys.includes(k)))&&!/already at its best/.test(hS)&&DS.qPct>.5,
       `43: a SaaS business with gross margin and retention at the rail's worst names both as too far below their peers for a step (${DS.sens.map(g=>g.keys.join("+")+":"+g.kind).join(", ")})`);
    ok(pool.concat([s]).every(x=>A.reportData(x,{}).sens.every(g=>g.n===1||(g.kind==="step"&&g.keys.every(k=>A.QW.w[k]===A.QW.w[g.keys[0]]))))
       &&pool.concat([s]).every(x=>{ const Dx=A.reportData(x,{}), hx=A.reportHTML(Dx,{}); return (hx.match(/weighted equally/g)||[]).length===Dx.sens.filter(g=>g.n>1).length; }),
       "43: a lever line groups only steps the model weights alike, and says 'weighted equally' only then");
    /* the bottom of the quality range */
    const sW={...s0,ind:"rest",own:.95,mgt:.08,fin:.14,rev:8e5,ern:1.2e5,ask:4e5,grw:-.25,gm:.12,rec:0,cc:.7,ret:.05,plt:.95,yrs:1}, DW=A.reportData(sW,{}), hW=A.reportHTML(DW,{});
    ok(DW.sens.length===0&&DW.qPct<.01&&DW.allBest>0&&/bottom of the quality range/.test(hW)&&hW.includes(A.money(DW.allBest))&&!/already at its best/.test(hW)&&/already at its best/.test(hall),
       "43: at the bottom of the quality range the report says so and names what all nine factors at their best would add; at the top it says they are at their best");
    const q1=A.reportData({...s0,rec:.09},{}), hq=A.reportHTML(q1,{});
    ok(q1.qFactor>.995&&q1.qFactor<1&&/−0\.\d% for quality/.test(hq)&&!/[−+]0% for quality/.test(hq)&&/\+\d+\.\d% for quality/.test(h),"43: the quality step prints with a decimal, as the console's, never '−0%'");
    ok(/buyer cash pays for it all/.test(A.reportHTML(A.reportData(s0,{fin:{cash:1,note:0}}),{}))&&/buyer cash and a \$[\d.]+[kM] seller note pay for it all/.test(hn),"43: the verb agrees with what pays");
    const Rn=A.recastSDE({years:[{rev:1e6,ni:2e5,nonop:-1e4}]}), hN=A.reportHTML({...D,recast:Rn},{});
    ok(Rn.flags.includes("neg_less")&&/if it was a one-time loss, or another owner.s pay above market, it is an add-back instead/.test(hN)&&!/enter it under/i.test(hN),
       "43: the report says what a negative deduction means for the SDE, not how to type it");
    const hN1=A.reportHTML(A.reportData(s0,{fin:{cash:.6,note:.4,noteYears:1}}),{});
    ok(!/below 1\.25×/.test(hN1)&&/no SBA loan<\/span>/.test(hN1)&&!/on full standby pay/.test(A.reportHTML(A.reportData(s0,{fin:{cash:.6,note:.4,standby:true}}),{})),
       "43: with no SBA loan the asks table does not grade the note against SBA's minimum, and no note is 'on full standby' behind nothing");
    const hP=A.reportHTML(A.reportData(s0,{fin:{draw:1.5e5,note:0}}),{}), hP2=A.reportHTML(A.reportData(s0,{fin:{cash:.6,note:.4,draw:1.5e5,noteRate:7,noteYears:5}}),{});
    ok(/coverage<\/b> <span class="rp-b rp-f">fitted<\/span>,/.test(hP)&&!/\(coverage\)/.test(hP)&&/covered \d+\.\d\d× by the/.test(hP2)&&/\(coverage\)/.test(h),
       "43: coverage's badge follows what moves it: the fitted rate alone with a typed pay and no note, nothing from entries alone; the footer names its judgment only when used");
    /* round 3. A failing equity test prints the amounts apart; a passing share with its decimal (r3-report-2) */
    const hE=A.reportHTML(A.reportData(s0,{fin:{cash:.0996,note:0}}),{}), mE=hE.match(/the buyer brings (\$[\d.]+[kM]) against SBA&rsquo;s 10% minimum of (\$[\d.]+[kM])/), fE=A.debtCheck(s0,s0.ask,{cash:.0996,note:0},V);
    ok(!!mE&&mE[1]!==mE[2]&&mE[1]===A.moneyDown(fE.equityIn)&&mE[2]===A.moneyUp(fE.equityNeed)&&/9\.9% buyer cash/.test(hE),`43: a failing equity test prints the buyer's amount rounded down and the minimum rounded up (${mE&&mE[1]} against ${mE&&mE[2]}), and the share as 9.9%`);
    ok(/9\.5% buyer cash/.test(A.reportHTML(A.reportData(s0,{fin:{cash:.095,note:.05,standby:true}}),{})),"43: a passing 9.5% buyer cash prints as 9.5%, not 10%");
    /* the track record names the expected price it scales (r3-report-3) */
    ok(hc.includes("against the model&rsquo;s expected "+A.money(D.sell.mean)+".")&&hc.includes("about "+A.money(D.sell.mean*C.shrunk)+" if it sells at the recommended ask"),
       "43: the track record states the model's expected price beside the figure it scales, so a 1.00× record reads as the model");
    /* 'Your ask' keeps its row unless it is an optimizer's ask (r3-report-9) */
    const near=A.reportHTML(A.reportData({...s0,ask:D.sell.ask*1.003},{}),{}), same=A.reportHTML(A.reportData({...s0,ask:D.sell.ask},{}),{});
    ok(near.includes("Your ask")&&!same.includes("Your ask"),"43: an ask 0.3% from the recommended one keeps its own row; only the recommended ask itself merges");
    /* the earnings notes name the amounts the SDE added back (r3-report-11) */
    const Rt=A.recastSDE({entity:"schc",years:[{rev:1e6,ni:2e5,owner:47800,ptax:7170,tax:23900}]}), ht=A.reportHTML({...D,recast:Rt},{});
    ok(Rt.ownerIn===47800&&Rt.ptaxIn===7170&&Rt.taxIn===23900&&ht.includes("The add-backs include "+A.moneyIn(47800)+" of the owner&#39;s pay".replace("&#39;","'"))
       &&ht.includes("The add-backs include "+A.moneyIn(7170)+" of payroll tax on the owner's own pay, which a Schedule C return never deducts, so this SDE is that much too high.")
       &&ht.includes("The add-backs include "+A.moneyIn(23900)+" of income tax that a Schedule C return never deducts")&&!/none to add back/.test(ht),
       "43: the earnings basis names the owner's pay, payroll tax and income tax a Schedule C SDE added back, not that there are none");
    const Rp=A.recastSDE({entity:"partnership",years:[{rev:1e6,ni:2e5,ptax:5000}]});
    ok(Rp.flags.includes("ptax_none")&&A.reportHTML({...D,recast:Rp},{}).includes("of payroll tax on a partner's own pay, which a partnership return never deducts")
       &&!/payroll tax that a (partnership|Schedule C) return never deducts/.test(A.reportHTML({...D,recast:Rp},{})+ht),
       "43: the payroll tax a partnership or Schedule C return never deducts is the one on the owner's or a partner's own pay, not every payroll tax (r4-worksheet-4, r4-report-3)");
    ok(HTML.includes("SBA&rsquo;s fourth category, a purchase")&&HTML.includes("judgment where the table says so")&&HTML.includes("Your price and time records")&&!HTML.includes("each editable or opt-in"),
       "43: the Data tab names SBA's fourth transaction category and says which conventions are editable or opt-in"); }
  /* round 2: the penalty fit's close rate when every listing at value closed, and its search against a fine grid */
  { const mul=a=>()=>{ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
    const allc=[]; { const rn=mul(21); for(let i=0;i<20;i++){ const up=i<5, gap=up?25:-5; allc.push({b:.4+.4*rn(),F:up?A.gapPenalty(gap)/A.PEN_MAX:0,gap,y:up?(i<3?1:0):1}); } }
    const fb=A.fitPenaltyScale(allc), bmin=Math.min(...allc.map(o=>o.b));
    ok(fb.cBound&&Math.abs(fb.c-.95/bmin)<1e-9,`43: when every listing at value closed, the close rate is reported as the bound where all are capped (${fb.c.toFixed(2)}, at least)`);
    let worse=0, gapMax=0;
    for(let t=0;t<30;t++){ const rn=mul(100+t), o=[], n=20+Math.floor(20*rn()), c0=.6+1.4*rn(), p0=.9*rn();
      for(let i=0;i<n;i++){ const b=.1+.7*rn(), up=rn()<.5, gap=up?10+40*rn():-10*rn(), F=up?A.gapPenalty(gap)/A.PEN_MAX:0; o.push({b,F,gap,y:rn()<Math.min(.95,c0*b)*(1-p0*F)?1:0}); }
      const f=A.fitPenaltyScale(o), bm=Math.min(...o.map(x=>x.b)), l0=Math.log(.05), l1=Math.log(.95/bm)+.01;
      const ll=(c,pen)=>{ let a=0; for(const x of o){ let p=Math.min(.95,c*x.b)*(1-pen*x.F); p=Math.min(1-1e-9,Math.max(1e-9,p)); a+=x.y?Math.log(p):Math.log(1-p); } return a; };
      let g=-Infinity; for(let i=0;i<=99;i++) for(let j=0;j<=200;j++) g=Math.max(g,ll(Math.exp(l0+(l1-l0)*j/200),.99*i/99));
      const sh=g-ll(f.c,f.pen); gapMax=Math.max(gapMax,sh); if(sh>1e-6) worse++; }
    ok(worse===0,`43: the penalty fit reaches the likelihood's maximum found by a fine grid in each of 30 simulated broker histories (largest shortfall ${gapMax.toExponential(1)})`); }
  /* ---- round 4 ---- */
  { const mul=a=>()=>{ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
    const amt=t=>{ const m=String(t).match(/\$([\d.]+)([kMB])?/); return m?parseFloat(m[1])*({k:1e3,M:1e6,B:1e9}[m[2]]||1):NaN; };
    /* r4-financing-1: an equity edge prints on its passing side, the floor rounded up and the ceiling down */
    const fA={cash:.06,note:.045,standby:true,extra:150300}, mA=A.maxFinanced(s0,fA,V), hA=A.reportHTML(A.reportData({...s0,ask:1.2e6},{fin:fA}),{});
    const fB={type:"buyout",cash:.08,note:0,extra:299900}, mB=A.maxFinanced(s0,fB,V), hB=A.reportHTML(A.reportData({...s0,ask:1.2e6},{fin:fB}),{});
    ok(mA.equityFrom>0&&!A.debtCheck(s0,amt(A.money(mA.equityFrom)),fA,V).equityOK&&A.debtCheck(s0,amt(A.moneyUp(mA.equityFrom)),fA,V).equityOK
       &&hA.includes("Below about "+A.moneyUp(mA.equityFrom)+' <span class="rp-b rp-a">published data</span> the buyer&rsquo;s equity')
       &&mB.equityTo>0&&!A.debtCheck(s0,amt(A.money(mB.equityTo)),fB,V).equityOK&&A.debtCheck(s0,amt(A.moneyDown(mB.equityTo)),fB,V).equityOK
       &&hB.includes(`about ${A.moneyDown(mB.equityTo)} <span class="rp-b rp-a">published data</span>${mB.equityAbove?" and "+A.moneyUp(mB.equityAbove)+' <span class="rp-b rp-a">published data</span>':""} the buyer&rsquo;s equity is under`),
       `43: the price where the equity starts passing prints rounded up (${A.moneyUp(mA.equityFrom)}, not ${A.money(mA.equityFrom)}) and where it stops rounded down (${A.moneyDown(mB.equityTo)}), so each passes as printed (r4-financing-1)`);
    /* r4-financing-2: past the 7(a) maximum an owner buyout's short equity comes back where buyer cash reaches 10% */
    /* built before round 9 added SBA's guaranty fee, financed by default: the no-fee build (NF) keeps the structure it tests */
    const sC={...s0,ern:2e6,rev:8e6,ask:4.5e6}, VC=NF.model(sC).V, fC={type:"buyout",cash:.08,note:0,extra:1e6,fee:"waived"}, mC=NF.maxFinanced(sC,fC,VC), hC=NF.reportHTML(NF.reportData(sC,{fin:fC}),{});
    let fails=true; for(let i=1;i<40;i++){ const p=mC.equityTo*Math.pow(mC.equityAbove/mC.equityTo,i/40); if(NF.debtCheck(sC,p,fC,VC).equityOK) fails=false; }
    ok(mC.capped&&mC.equityTo>0&&mC.equityAbove>mC.capAt&&fails&&[1.001,1.5,5].every(x=>NF.debtCheck(sC,mC.equityAbove*x,fC,VC).equityOK)
       &&hC.includes(`Between about ${A.moneyDown(mC.equityTo)} <span class="rp-b rp-a">published data</span> and ${A.moneyUp(mC.equityAbove)} <span class="rp-b rp-a">published data</span> the buyer&rsquo;s equity is under SBA&rsquo;s 10% minimum of the price`)
       &&hC.includes(`which brings it back to 10% from ${A.moneyUp(mC.equityAbove)} <span class="rp-b rp-a">published data</span>`)&&!/Above about/.test(hC)&&["4.5e6","6.48e6"].every(p=>NF.debtCheck(sC,+p,fC,VC).equityOK),
       `43: an owner buyout's equity, short from ${A.moneyDown(mC.equityTo)}, is bounded where buyer cash past the 7(a) maximum brings it back to 10% (${A.moneyUp(mC.equityAbove)}), as the asks show (r4-financing-2)`);
    /* r4-report-2: with a 90% paid note buyer cash past the cap never reaches 10%: no bound is named */
    const sD={...s0,ern:2e7,rev:8e7,ask:5.5e7}, VD=NF.model(sD).V, fD={cash:0,note:.9,fee:"waived"}, mD=NF.maxFinanced(sD,fD,VD), hD=NF.reportHTML(NF.reportData(sD,{fin:fD}),{});
    ok(mD.capped&&mD.equityShort&&mD.equityAbove===null&&[5.5e7,1e9,1e11].every(p=>!NF.debtCheck(sD,p,fD,VD).equityOK)
       &&/at every price: past \$50\.00M <span class="rp-b rp-a">published data<\/span> the SBA loan stays at the 7\(a\) maximum and the rest of the price is buyer cash, but with this seller note that never reaches 10%\./.test(hD)&&!/at every price below/.test(hD),
       "43: with a 90% paid note buyer cash past the 7(a) maximum never reaches 10%, so the report says the equity is short at every price (r4-report-2)");
    /* r4-financing-5, r4-core-5: the optimizer's two asks are one row when they print as one price */
    let rowsOK=0, rowsN=0; { const rn=mul(404), inds=Object.keys(A.IND);
      for(let t=0;t<40;t++){ const s={...s0,ind:inds[t%inds.length],ern:1e5*Math.pow(10,1.6*rn()),theta:rn(),lamT:3000*rn()}; s.rev=s.ern/(.08+.25*rn());
        const D=A.reportData(s,{}); rowsN++; if(D.same===(A.money(D.sell.ask)===A.money(D.walk.ask))) rowsOK++; } }
    ok(rowsOK===rowsN,`43: the report merges the two optimizer asks exactly when they print as the same price, the console's rule (${rowsOK} of ${rowsN}; r4-financing-5, r4-core-5)`);
    /* r4-financing-7: the transaction's conditions and the shares' basis describe their boxes from outside the label */
    ok(HTML.includes('<div class="fin-f wide"><label for="f_type">Transaction</label><select id="f_type" aria-describedby="f_type_h"></select><span class="fin-h" id="f_type_h"></span></div>')
       &&/id="f_cash"[^>]*aria-describedby="f_cash_h"/.test(HTML)&&/id="f_note"[^>]*aria-describedby="f_note_h"/.test(HTML)&&HTML.includes('<span class="fin-h" id="f_note_h">of the price</span>')
       &&HTML.includes('<span class="fin-h" id="f_cash_h">of the price, working capital and closing costs</span>')&&!/<label class="fin-f"[^>]* title=/.test(HTML),
       "43: the transaction's conditions and the shares' basis are visible, and described once from outside each label (r4-financing-7)");
    /* r4-worksheet-2, r4-core-2, r4-core-6: two amounts are refused whatever separates them; a number grouped with no-break
       or thin spaces is one */
    const src=HTML.slice(HTML.indexOf("function parseAmount(t){")), pa=new Function(src.slice(0,src.indexOf("\n}\n")+2)+";return parseAmount;")();
    const nb=String.fromCharCode(160), nn=String.fromCharCode(0x202f), th=String.fromCharCode(0x2009), mi=String.fromCharCode(0x2212);
    const two=["$45,000 $50,000","$512,000 $470,000","512,000, 470,000","512,000 ,470,000","512,000,,470,000","45000$50000","5$ 6$","$$5","$5$6",
      "512,000\t470,000","512,000 470,000","1 450 000 2","1"+nb+"450"+nb+"000 2"];
    const one=[["1 450 000",1450000],["1"+nb+"450"+nb+"000",1450000],["1"+nn+"450"+nn+"000",1450000],["1"+th+"450"+th+"000",1450000],["$ 1 450 000",1450000],
      ["$1,450,000",1450000],["1,450,000.50",1450000.5],["500$",500],["- $5k",-5000],[mi+"$1.2m",-1.2e6],["$1.45M",1.45e6],["6 years",6],["$900/day",900],["none",0]];
    const bad2=two.filter(t=>!Number.isNaN(pa(t))), bad1=one.filter(([t,v])=>!(Math.abs(pa(t)-v)<1e-6));
    ok(!bad2.length&&!bad1.length,`43: two amounts in one box are refused whatever separates them, and a number grouped with no-break or thin spaces, or "$ 1 450 000", is one (r4-worksheet-2, r4-core-2, r4-core-6)${bad2.length||bad1.length?": "+JSON.stringify([bad2,bad1.map(x=>x[0])]):""}`);
    /* r4-worksheet-3: the report states the weights the SDE applies */
    const ws3=y=>A.recastSDE({entity:"scorp",weight:"w321",years:y}), D0=A.reportData(s0,{});
    const Ra=ws3([{rev:7e6},{rev:6e6,ni:9e5,owner:3e5},{rev:5.5e6,ni:6.9e5,owner:3e5}]), Rb=ws3([{rev:7e6,ni:1e6,owner:3e5},{},{rev:5.5e6,ni:6.9e5,owner:3e5}]);
    const Rc=ws3([{rev:7e6,ni:1e6},{rev:6e6,ni:9e5},{rev:5.5e6,ni:6.9e5}]), hb=R=>A.reportHTML({...D0,recast:R},{});
    ok(A.recastWeighting(Ra)==="weighted 2:1 toward the year before"&&Math.abs(Ra.sde-(2*1.2e6+.99e6)/3)<1e-6&&A.recastWeighting(Rb)==="weighted 3:1 toward the most recent year"
       &&Math.abs(Rb.sde-(3*1.3e6+.99e6)/4)<1e-6&&A.recastWeighting(Rc)==="weighted 3:2:1 toward the most recent year"&&hb(Ra).includes("returns and weighted 2:1 toward the year before:")
       &&hb(Rb).includes("returns and weighted 3:1 toward the most recent year:")&&hb(Rc).includes("returns and weighted 3:2:1 toward the most recent year:"),
       "43: the report states the weights the SDE applies: 2:1 when the most recent year has revenue alone, 3:1 with the middle year blank (r4-worksheet-3)");
    /* r4-worksheet-5, -6: the hints name another partnership's income among the non-operating lines, and the energy
       efficient commercial buildings deduction among the depreciation add-backs */
    const E=A.RECAST_ENTITY;
    ok(["scorp","ccorp","partnership","schc"].every(k=>/the energy efficient commercial buildings deduction \(Form 7205\)/.test(E[k].dep))
       &&/ordinary income from a partnership, estate or trust inside Other income \(a loss is an add-back\)/.test(E.scorp.nonop)
       &&/^Ordinary income from other partnerships, estates and trusts \(a loss is an add-back\)/.test(E.partnership.nonop)
       &&/ordinary income from a partnership inside Other income \(a loss, among Other deductions, is an add-back\)/.test(E.ccorp.nonop),
       "43: the hints name another partnership's ordinary income among the non-operating lines and the energy efficient commercial buildings deduction among the depreciation add-backs (r4-worksheet-5, -6)");
    /* r4-report-1: past the bottom of the quality range a factor near its peers is not 'too far below' them, and the
       report still says what all nine at their best would add */
    const sR={...s0,ind:"rest",own:.95,mgt:.08,fin:.14,rev:8e5,ern:1.2e5,ask:4e5,grw:-.25,gm:.12,rec:0,cc:.14,ret:.05,plt:.95,yrs:1}, DR=A.reportData(sR,{}), hR=A.reportHTML(DR,{}), rR=A.model(sR);
    const step=(s,k)=>{ const v=A.sensitivity(s).find(r=>r.k===k); return s[k]+(v.inv?-2*v.h:2*v.h); };
    const lim=k=>A.sensitivity(sR).find(r=>r.k===k).inv?rR.z[k]>=3.2:rR.z[k]<=-3.2;
    ok(DR.qz===rR.qz&&rR.qz<-3&&DR.sens.length>0&&DR.sens.every(g=>g.kind==="bottom"||g.kind==="far")&&DR.sens.some(g=>g.kind==="bottom")
       /* "far": the factor's own z at its limit before the step, which the step leaves there or lifts a sliver (r5-report-1) */
       &&DR.sens.filter(g=>g.kind==="far").every(g=>g.keys.every(k=>lim(k)))&&DR.sens.filter(g=>g.kind==="bottom").every(g=>g.keys.every(k=>!lim(k)&&A.model({...sR,[k]:step(sR,k)}).z[k]!==rR.z[k]))
       &&/one step does not register past the bottom of the quality range; at its best it would add about/.test(hR)
       &&hR.includes(`The business sits past the bottom of the quality range: all nine quality factors at their best would add about ${A.money(DR.allBest)} together.`)
       &&DR.sens.every(g=>/too far below its peers/.test(hR.split(`<li><b>${g.names}</b>`)[1].split("</li>")[0])===(g.kind==="far")),
       `43: a restaurant past the bottom of the quality range (composite ${rR.qz.toFixed(2)}): each line gives the true reason a step does not register, and the report adds what all nine at their best would add (r4-report-1)`);
    /* r4-report-6: in print the business holds to two lines and the date-first block after it to three */
    const W=n=>"W".repeat(n), hN=A.reportHTML(A.reportData(s0,{date:"October 20, 2026"}),{business:W(120),preparedFor:W(120),broker:W(120),firm:W(120)});
    ok(A.RP_CSS.includes(".rp h1,.rp-prep{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.rp-prep{-webkit-line-clamp:3}")
       &&A.RP_CSS.indexOf("-webkit-line-clamp")>A.RP_CSS.indexOf("@media print")&&/<h1 class="rp-long rp-pl">W+<\/h1>/.test(hN)&&/<div class="rp-prep rp-pl"><span>October 20, 2026<\/span><span>Prepared for W+<\/span><span>by W+, W+<\/span><\/div>/.test(hN),
       "43: in print the business name holds to two lines and the block after it, the date first, to three (r4-report-6)");
    /* r4-deals-9: the penalty fit waits for listings at or below value, which fix the close rate fitted with it */
    const L=(n,m)=>Array.from({length:n},(_,i)=>({inputs:{...s0},listPrice:V*m,status:i%2?"closed":"expired",salePrice:i%2?V:null}));
    const Dp=A.dealsStats(L(20,1.25)), Dq=A.dealsStats(L(15,1.25).concat(L(5,.95)));
    ok(A.DEAL_MIN.penAt===5&&!Dp.pen.ready&&Dp.pen.nAt===0&&Dp.pen.nAbove===20&&Dq.pen.ready&&Dq.pen.nAt===5&&Dq.pen.nAbove===15,
       "43: the penalty fit waits for 5 listings at or below value: with none, every scale fits as well as any beside some close rate (r4-deals-9)");
    /* r4-core-1: with both cards at the empty programme, the proceeds card names its own over-budget change */
    let seen=0, wrong=0, named=0; { const rn=mul(2468), inds=Object.keys(A.IND);
      for(let t=0;t<120;t++){ const s={...s0,ind:inds[t%inds.length],ern:1e5*Math.pow(10,1.5*rn()),budget:5e3*rn()}; s.rev=s.ern/(.08+.25*rn());
        const r1=A.model(s); s.rhoSell=A.bestRatio(s,0,0); s.ask=r1.V*s.rhoSell; s.optRho=A.bestRatio(s,s.theta,s.lamT); s.rhoSell=A.bestRatio(s,0,0);
        const r=A.model(s), b=A.optimize(s,r,s.budget,s.lamT,s.theta); if(!b.V||b.V.keys.length||!b.U||b.U.keys.length) continue; seen++;
        let out=null; for(const it of A.INTERV){ if(it.k==="reprice") continue; const c=A.costOf(s,[it.k]); if(c<=s.budget||(out&&c>=out.c)) continue;
          for(const keys of [[it.k],["reprice",it.k]]){ const x=A.model(A.applyAll(s,r,keys,s.rhoSell)); if(x.EVp-c>b.V.net){ out={k:it.k,c,withReprice:keys.length>1,days:Math.round(A.daysOf(s,[it.k]))}; break; } } }
        if(out) named++; if(b.U===b.V||JSON.stringify(out)!==JSON.stringify(b.V.blocked)) wrong++; } }
    ok(seen>=20&&named>=5&&wrong===0,`43: when both cards keep the empty programme, the proceeds card names the change its own search finds, not the utility card's (${seen} businesses, ${named} with a change, ${wrong} wrong; r4-core-1)`); }
  /* ---- round 5 ---- */
  { const EX={ind:"medical",rev:10**6.778,ern:10**6.161,ask:10**6.508,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:10**(4+2.778*.36),lamT:900,theta:.75,rate:10.5};
    const VX=A.model(EX).V, txt=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/\s+/g," ");
    /* r5-report-1: a factor at its z limit whose step lifts its z only a sliver is named at its best, with the reason */
    const lev=(s,k)=>A.reportData(s,{}).sens.find(g=>g.keys.includes(k));
    const l1=lev({...EX,ind:"saas",ret:.34},"ret"), l2=lev({...EX,ind:"saas",gm:.21},"gm");
    const sT={...EX,...A.RAIL_BEST,ind:"saas",gm:.25}, DT=A.reportData(sT,{}), hT=A.reportHTML(DT,{}), VT=A.model(sT).V;
    ok(!!l1&&l1.kind==="far"&&l1.gain>5e5&&!!l2&&l2.kind==="far"&&l2.gain>1e6&&A.model({...sT,gm:.97}).V-VT>VT*.001&&DT.sens.some(g=>g.keys.includes("gm"))
       &&!/no single factor, even at its best, moves the value/.test(hT),
       `43: a factor at its z limit whose step lifts its z only a sliver is named at its best (retention ${l1?A.money(l1.gain):"missing"}, gross margin ${l2?A.money(l2.gain):"missing"}), and near the top of the range the report does not say no factor moves the value (r5-report-1)`);
    /* r5-report-2: the patient-seller ask carries the console's qualifiers */
    const hC=txt(A.reportHTML(A.reportData({...EX,theta:.95,lamT:0},{}),{})), h0=txt(A.reportHTML(A.reportData(EX,{}),{}));
    ok(/If you can walk away \$[\d.]+M 1\.50× value.*1\.50× value is the console’s cap on the ask \(a judgment\), not an optimum: asks from 1\.\d\d× up come within 1% of value of it\./.test(hC)
       &&/If you can walk away .*Close to a tie with other asks: read it as 1\.20–1\.50× value; 1\.50× is the console’s cap on the ask \(a judgment\)\./.test(h0),
       "43: the patient-seller ask carries the console's qualifiers: at the 1.5x cap a judgment, not an optimum, with the asks within 1% of value of it; a range where another ask is close to a tie (r5-report-2)");
    /* r5-report-3: the improvements are measured, and say they are, with the ask reset to the recommended ratio of the value after them */
    const D3=A.reportData(EX,{}), h3=txt(A.reportHTML(D3,{})), rs=A.bestRatio(EX,0,0), t3=A.interventionTable({...EX,rhoSell:rs},A.model(EX)).filter(t=>t.k!=="reprice"&&t.net>0).slice(0,3);
    ok(D3.fixes.length===3&&D3.fixes.every((t,i)=>t.k===t3[i].k&&Math.abs(t.dE-t3[i].dE)<1e-6)&&h3.includes(`Each gain assumes the ask reset to ${rs.toFixed(2)}× the new value.`),
       `43: the improvements are measured, and say they are, with the ask reset to ${rs.toFixed(2)}x the business's value after the change (r5-report-3)`);
    /* r5-financing-1: a loan under a dollar at small prices names no equity edge */
    const mz=["initial","expansion","buyout"].map(type=>A.maxFinanced(EX,{type,cash:.0995,note:.9},VX));
    const hz=txt(A.reportHTML(A.reportData(EX,{fin:{type:"initial",cash:.0995,note:.9}}),{}));
    ok(mz.every(m=>m.equityTo===null&&m.equityFrom===null)&&/at every price this structure finances\./.test(hz)&&!/Above about \$/.test(hz),
       "43: 9.95% buyer cash beside a 90% note names no equity edge where the loan passes a dollar: an initial acquisition is short at every price it finances (r5-financing-1)");
    /* r5-financing-2: the highest price and the equity floor print so they never cross */
    { const f={type:"initial",cash:.06,note:.1,standby:true,extra:4e5,draw:1e5,fee:"waived"}; let hit=null;
      for(let ern=1.5e5;ern<6e5&&!hit;ern*=1.0005){ const s={...EX,ern,rev:ern/.25,ask:1e6}, V2=A.model(s).V, m=A.maxFinanced(s,f,V2);
        if(m.price>0&&isFinite(m.price)&&m.equityFrom&&A.moneyVal(A.moneyUp(m.equityFrom))>A.moneyVal(A.moneyDown(m.price))) hit={s,V2,m}; }
      const E=hit?A.finEdges(hit.m):{}, top=A.moneyVal(E.top), from=A.moneyVal(E.from);
      ok(!!hit&&from<=top&&A.debtCheck(hit.s,top,f,hit.V2).equityOK&&!A.debtCheck(hit.s,from,f,hit.V2).debtOverValue&&E.top==="$"+Math.floor(hit.m.price).toLocaleString("en-US"),
         `43: where the equity floor rounded up would print above the highest price rounded down, both print in whole dollars and both pass (${E.from} to ${E.top}; r5-financing-2)`); }
    /* r5-financing-5: a seller note on full standby at the starting share sizes the loan */
    const fS={standby:true}, DS=A.reportData(EX,{fin:fS}), hS=A.reportHTML(DS,{});
    ok(A.debtCheck(EX,EX.ask,fS,VX).noteConv&&!A.debtCheck(EX,EX.ask,{standby:true,note:.07},VX).noteConv&&DS.maxFin.bind==="value"&&hS.includes("the seller-note convention (the highest financed price"),
       "43: a seller note on full standby at the starting 5% share moves the highest financed price and coverage, so they carry x judgment and the footer names the convention (r5-financing-5)");
    /* r5-deals-10: listings past the survey's range are left out of the penalty fit and counted */
    const LP=(n,x)=>Array.from({length:n},(_,i)=>({inputs:{...s0},listPrice:V*x,status:i%2?"closed":"expired",salePrice:i%2?V:null}));
    const Df=A.dealsStats(LP(10,1.25).concat(LP(5,3.2),LP(5,.95)));
    ok(Df.pen.nFar===5&&Df.pen.n===15&&Df.pen.nAbove===10&&!Df.pen.ready,"43: a finished listing more than 200% above value is left out of the penalty fit and counted, so its card can say so (r5-deals-10)");
    /* r5-worksheet-5, r5-core-1: a number grouped with spaces uses one kind throughout */
    { const src=HTML.slice(HTML.indexOf("function parseAmount(t){")), pa=new Function(src.slice(0,src.indexOf("\n}\n")+2)+";return parseAmount;")();
      const NB=String.fromCharCode(160), NN=String.fromCharCode(0x202f), TH=String.fromCharCode(0x2009);
      const two=["512"+NN+"000 470"+NN+"000","45"+NN+"000 500","1"+NB+"450 000","512"+NB+"000 470"+NB+"000","1"+TH+"450"+NN+"000"], one=["1 450 000","1"+NB+"450"+NB+"000","1"+NN+"450"+NN+"000","$ 1 450 000","6"+TH+"200"+TH+"000"];
      ok(two.every(t=>isNaN(pa(t)))&&one.every(t=>pa(t)>1e6),"43: a number grouped with spaces uses one kind throughout, so a pasted column of cells grouped with no-break spaces is two amounts (r5-worksheet-5, r5-core-1)"); }
    /* found while testing round 5: a loan share of 0.05% (9.95% cash beside a 90% note) puts the 7(a) maximum at a $10B
       price, where a rounding error read as a loan past it; and a 90% note on full standby, paid below the price where an
       SBA loan first appears, read "no price" though every financed price passed */
    { const sF={...EX,ind:"fit",rev:49868000,ern:17035000,ask:12469000}, fF={type:"initial",cash:.0995,note:.9,noteRate:4,noteYears:25,standby:true}, VF=A.model(sF).V, mF=A.maxFinanced(sF,fF,VF);
      const sA={...EX,ind:"auto",rev:11549,ern:4371.9,ask:9455.4}, fA={type:"initial",cash:.0995,note:.9,noteRate:30,noteYears:1,standby:true,draw:3800}, VA=A.model(sA).V, mA=A.maxFinanced(sA,fA,VA), dA=A.debtCheck(sA,mA.price,fA,VA);
      ok(mF.bind==="cap"&&A.debtCheck(sF,mF.price,fF,VF).over===0&&mA.price>2e3&&dA.loan>0&&dA.ok&&!dA.debtOverValue,
         `43: at the 7(a) maximum a rounding error is no loan past it, and a standby note paid below the first SBA loan does not stop the search for the highest price (${A.money(mA.price)}; found in round 5)`); } }
  /* ---- round 6 ---- */
  { const txt=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/\s+/g," ");
    const FW={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75,rate:10.5};
    /* r6-core-1: the report's range is the console note's, over every near-tie peak: at the framework example it runs to the cap */
    { const D=A.reportData(FW,{}), h=txt(A.reportHTML(D,{}));
      ok(D.walkQ.range&&D.walkQ.range[0].toFixed(2)==="1.20"&&D.walkQ.range[1].toFixed(2)==="1.50"&&D.walkQ.others===2&&/Close to a tie with other asks: read it as 1\.20–1\.50× value; 1\.50× is the console’s cap on the ask \(a judgment\)\./.test(h),
         `43: the framework example's report reads the patient-seller ask as 1.20-1.50x, the 1.20x peak to the cap, as the console note does (r6-core-1)`); }
    /* r6-report-1: a factor at its z limit whose step lifts its z most of a step is held by the composite, not "too far below" */
    { const sW={ind:"wash",st:"KY",franchise:true,rev:11273538.33,ern:9552731.864,grw:-.25,gm:.44,rec:.24,cc:.42,ret:.18,plt:.34,own:.72,mgt:.36,fin:.45,yrs:9,buyers:180,budget:629278.78,lamT:1350,theta:.71,ask:7862633.36};
      const D=A.reportData(sW,{}), h=txt(A.reportHTML(D,{})), g=D.sens.find(x=>x.keys.includes("ret")), r0=A.model(sW), r1=A.model({...sW,ret:sW.ret+2*A.sensitivity(sW).find(v=>v.k==="ret").h});
      ok(!!g&&g.kind==="bottom"&&r0.z.ret<=-3.2&&r1.z.ret-r0.z.ret>.9&&r1.qz<-3&&/Customer retention : one step does not register past the bottom of the quality range/.test(h)&&!/too far below its peers/.test(h),
         `43: a car wash whose retention sits at its z limit, and whose step lifts it ${(r1.z.ret-r0.z.ret).toFixed(2)} sd while the composite stays past -3, gets the composite's reason, not "too far below its peers" (r6-report-1)`); }
    /* r6-financing-3: where no whole dollar passes the equity, an expansion's whole-dollar top is short only of a 10% the
       lender may waive: the box and the report give it with the waiver; an initial acquisition's has none */
    { const f={type:"expansion",cash:.06,note:.1,standby:true,extra:4e5,draw:1e5,fee:"waived"}; let hit=null;
      /* near $264,577 of SDE since round 10 added the mental health specialists' cell to the medical pool ($262,953 after
         round 9 pooled the medical cells, $277,183 before) */
      for(let ern=264576;ern<264578&&!hit;ern+=.002){ const s={...FW,ern,rev:4*ern,ask:1e6}, V=NF.model(s).V, m=NF.maxFinanced(s,f,V);
        if(m.price>0&&isFinite(m.price)&&m.equityFrom&&Math.ceil(m.equityFrom-1e-9)>Math.floor(m.price+1e-9)) hit={s,V,m}; }
      const E=hit?A.finEdges(hit.m):{}, mi=hit?NF.maxFinanced(hit.s,{...f,type:"initial"},hit.V):{}, Ei=hit?A.finEdges(mi):{}, h=hit?txt(NF.reportHTML(NF.reportData(hit.s,{fin:f}),{})):"";
      const top=A.moneyVal(E.top||"0"), dTop=hit?NF.debtCheck(hit.s,top,f,hit.V):{};
      ok(!!hit&&!E.none&&E.top==="$266,666"&&dTop.ok&&!dTop.debtOverValue&&!dTop.equityOK&&/is about \$266,666/.test(h)&&/Below about \$266,667 published data the buyer’s equity, with the standby note’s credit, is under SBA’s 10% minimum: the lender may reduce or eliminate it only when/.test(h)
         &&!/No whole-dollar price passes/.test(h)&&Ei.none,
         `43: where the equity floor and the highest price share one whole dollar, an expansion's top passes all but a waivable equity, so it is given with the waiver; an initial acquisition's reads none (r6-financing-3)`); }
    /* r6-financing-2: with the note on full standby at the starting share, the debt above value carries x judgment, in the
       lender paragraph and the asks table, and the footer names it */
    { const P=A.peerMedians("medical",1.2e6,5e6), s0={...FW,...P,ern:1.2e6,rev:5e6}, V=A.model(s0).V, s={...s0,ask:1.3*V};
      const h5=A.reportHTML(A.reportData(s,{fin:{standby:true,note:.05}}),{}), h6=A.reportHTML(A.reportData(s,{fin:{standby:true,note:.06}}),{});
      const bx='<span class="rp-bx"><span class="rp-b rp-f">fitted</span><span class="rp-b rp-j rp-x">× judgment</span></span>', pl='<span class="rp-b rp-f">fitted</span>';
      ok(Math.abs(A.model(s).qFactor-1)<.005&&h5.includes(`above the model value, here standing in`)&&new RegExp("is \\$[\\d.]+[kM] "+bx.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+" above the model value").test(h5)
         &&new RegExp("Lender: debt \\$[\\d.]+[kM] "+bx.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+" over value").test(h5)&&txt(h5).includes("the seller-note convention (the highest financed price, the debt above value)")
         &&new RegExp("is \\$[\\d.]+[kM] "+pl+" above the model value").test(h6)&&!txt(h6).includes("the debt above value)"),
         "43: a note on full standby at the starting 5% share sizes the loan, so the debt above value carries x judgment in the paragraph and the asks table, and the footer names it; at 6% it is plain fitted (r6-financing-2)"); }
    /* r6-financing-4: a waiver the paper relies on states SBA's conditions */
    { const h=txt(A.reportHTML(A.reportData({...FW,ern:2.5e6,rev:1e7,ask:9e6},{fin:{type:"expansion",cash:.08,note:.05}}),{}));
      ok(/if the lender waives part of the 10% equity/.test(h)&&/SBA lets the lender reduce the 10% equity only when the business keeps the liquidity and working capital to run, with no negative net worth\./.test(h),
         "43: an expansion's highest price that relies on a waiver states SBA's conditions when no other sentence on the paper does (r6-financing-4)"); }
    /* r6-report-4: the one row both asks share says it serves both sellers, with the walk-away seller's terms */
    { const s={ind:"land",st:"MT",franchise:true,rev:152162.728,ern:109377.553,grw:.26,gm:.96,rec:.74,cc:.29,ret:.2,plt:.45,own:.72,mgt:.92,fin:.14,yrs:2,buyers:225,budget:20630.39,lamT:1650,theta:.78,ask:160679.45};
      const D=A.reportData(s,{}), h=A.reportHTML(D,{}), t=txt(h);
      ok(D.same&&h.includes(`<th scope="row">If you need to sell<br>or can walk away</th>`)&&/A seller who can walk away gets the same ask, counting the business, if it doesn't sell, as worth 78% of its value and charging \$1,650 a day of delay\./.test(t),
         "43: when both optimizer asks print alike, the report's one row is labelled for both sellers and gives the walk-away seller's share kept and cost of delay (r6-report-4)"); }
    /* r6-report-7: an initial acquisition short of equity at every price prints no highest price; the prices past the 7(a)
       maximum that the note's starting share sets carry the badge, and the footer names them, not a highest financed price */
    { const D=A.reportData({...FW,ern:3e6,rev:1.2e7},{fin:{type:"initial",cash:0,note:.05}}), h=A.reportHTML(D,{}), t=txt(h);
      ok(D.maxFin.equityShort&&!D.maxFin.equityWaivable&&D.maxFin.capped&&/at every price below about \$[\d.]+M published data × judgment : past \$[\d.]+M published data × judgment the SBA loan stays at the 7\(a\) maximum/.test(t)
         &&t.includes("the seller-note convention (the prices past the 7(a) maximum)")&&!t.includes("(the highest financed price)"),
         "43: where the report prints no highest financed price, the footer does not name one; the prices past the 7(a) maximum it prints carry the convention's badge (r6-report-7)"); }
    /* r6-report-2: in print a name that could wrap at the larger size takes the smaller one */
    { const W=n=>"W".repeat(n), cls=m=>{ const h=A.reportHTML(A.reportData(FW,{date:"October 21, 2026"}),m); return [(/<h1( class="([^"]*)")?>/.exec(h)||[])[2]||"",(/<div class="rp-prep( [^"]*)?">/.exec(h)||[])[1]||""]; };
      const a=cls({business:W(28)}), b=cls({business:W(29)}), c=cls({business:W(56),preparedFor:W(50),broker:W(50),firm:W(50)}), d=cls({business:"Acme",preparedFor:W(40),broker:W(30),firm:W(17)});
      const len="October 21, 2026 · Prepared for "+W(40)+" · by "+W(30)+", "+W(17);
      ok(a[0]===""&&b[0]==="rp-pl"&&c[0]==="rp-pl"&&c[1]===" rp-pl"&&len.length>120&&d[1]===" rp-pl"&&cls({business:"Acme",preparedFor:W(30)})[1]===""
         &&A.RP_CSS.includes(".rp h1.rp-long,.rp h1.rp-pl{font-size:14px}")&&A.RP_CSS.includes(".rp-prep.rp-pl{font-size:8.5px}"),
         "43: in print a business over 28 characters, or a prepared-for block over 120, takes the smaller size, so a shorter name never prints taller than the clamped longest (r6-report-2)"); }
  }
  /* ---- round 7 ---- */
  { const txt=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/\s+/g," ");
    const FW={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75,rate:10.5};
    const peer=(ern,rev)=>{ const s={...FW,...A.peerMedians("medical",ern,rev),ern,rev}; return {...s,ask:A.model(s).V}; };
    /* r7-financing-1: past the 7(a) maximum the loan stays at the maximum, so a paid note's starting share moves the debt
       above value (x judgment, and the footer names it) and a standby note's moves neither the debt nor coverage */
    /* built before round 9 added SBA's guaranty fee, financed by default: the no-fee build (NF) keeps the structure it tests */
    { const s=peer(2e6,8e6), V=s.ask, a={...s,ask:1.45*V}, tA=txt(A.reportHTML(A.reportData(a,{fin:{fee:"waived"}}),{}));
      const dA=[.04,.05,.06].map(note=>A.debtCheck(a,a.ask,{note,fee:"waived"},V).debt);
      const b0=peer(1.75e6,7e6), Vb=b0.ask, b={...b0,ask:1.45*Vb}, fS={standby:true,draw:2e5,fee:"waived"}, DB=A.reportData(b,{fin:fS}), tB=txt(A.reportHTML(DB,{}));
      const cB=[.04,.05,.06].map(note=>A.debtCheck(b,b.ask,{...fS,note},Vb));
      ok(A.debtCheck(a,a.ask,{fee:"waived"},V).over>0&&dA[0]<dA[1]-1e3&&dA[1]<dA[2]-1e3&&/is \$[\d.]+[kM] fitted × judgment above the model value/.test(tA)
         &&/Lender: debt \$[\d.]+[kM] fitted × judgment over value \| Your ask|Your ask .*Lender: debt \$[\d.]+[kM] fitted × judgment over value/.test(tA)&&/the seller-note convention \([^)]*the debt above value\)/.test(tA)
         &&DB.cur.fin.over>0&&cB.every(c=>Math.abs(c.debt-cB[1].debt)<1&&Math.abs(c.dscr-cB[1].dscr)<1e-9)&&!DB.cur.fin.noteConv
         &&/is \$[\d.]+[kM] fitted above the model value/.test(tB)&&/\d\.\d\d× coverage fitted , meeting/.test(tB),
         "43: past the 7(a) maximum a paid starting note's share moves the debt above value, which carries x judgment and the footer names; a standby note's moves neither the debt nor coverage, which print plain fitted (r7-financing-1)"); }
    /* r7-financing-2, r7-report-2: the prices the report derives from the 7(a) maximum and SBA's 10% rule carry that badge,
       with x judgment where the note's starting share sets them, and the footer names them */
    /* built before round 9 added SBA's guaranty fee, financed by default: the no-fee build (NF) keeps the structure it tests */
    { const s=peer(3e6,12e6), y=peer(1.2e6,5e6), fB={type:"buyout",cash:.08,note:.05,extra:1e6,fee:"waived"}, fF={type:"initial",cash:.07,note:.05,standby:true,extra:5e5,fee:"waived"};
      const tB=txt(NF.reportHTML(NF.reportData(s,{fin:fB}),{})), tF=txt(NF.reportHTML(NF.reportData(y,{fin:fF}),{})), t6=txt(NF.reportHTML(NF.reportData(s,{fin:{type:"initial",cash:0,note:.06,fee:"waived"}}),{}));
      const ab=[.04,.05,.06].map(note=>NF.maxFinanced(s,{...fB,note},s.ask).equityAbove), fl=[.04,.05,.06].map(note=>NF.maxFinanced(y,{...fF,note},y.ask).equityFrom);
      ok(ab[0]<ab[1]&&ab[1]<ab[2]&&fl[0]>fl[1]&&fl[1]>fl[2]
         &&/Between about \$[\d.]+M published data and \$[\d.]+M published data × judgment the buyer’s equity is under/.test(tB)&&/brings it back to 10% from \$[\d.]+M published data × judgment ?\./.test(tB)
         &&tB.includes("the seller-note convention (the highest financed price, the prices past the 7(a) maximum)")
         &&/Below about \$750k published data × judgment the buyer’s equity, with the standby note’s credit/.test(tF)&&tF.includes("the equity’s 10% edge")
         &&/at every price below about \$[\d.]+M published data : past \$[\d.]+M published data the SBA loan stays/.test(t6),
         "43: an owner buyout's price where buyer cash past the 7(a) maximum brings the equity back to 10%, and the floor a standby note at the starting share sets, carry published data x judgment and the footer names them; with a typed share the prices past the maximum carry published data (r7-financing-2, r7-report-2)"); }
    /* r7-report-4, r7-core-1: a range whose top is the ask cap says so on the paper; a peak just under the cap is where the
       cap binds, and only 1.50x is called the cap */
    { const s={...FW,lamT:4000}, D=A.reportData(s,{}), t=txt(A.reportHTML(D,{}));
      let named=0, wrong=0;
      for(let th=.74;th<=.801;th+=.01) for(let lam=2000;lam<=4000;lam+=250){ const x={...FW,theta:th,lamT:lam}, V=A.model(x).V, rs=A.bestRatio(x,0,0), rw=A.bestRatio(x,th,lam);
        const n=A.optNote({...x,rhoSell:rs,optRho:rw},V,A.model({...x,ask:V*rs}),A.model({...x,ask:V*rw})).text;
        if(/cap on the ask binds/.test(n)) named++; if(/1\.4\d× (value )?\(the cap the console puts on the ask\)/.test(n)) wrong++; }
      ok(/read it as 1\.19–1\.48× value; 1\.48× is where the console’s 1\.50× cap on the ask binds \(a judgment\)\./.test(t)&&named>=5&&wrong===0,
         `43: the report says a range's top is where the ask cap binds, and the console's note calls only 1.50x the cap (${named} framework states name a peak just under it as where the cap binds, ${wrong} call it the cap; r7-report-4, r7-core-1)`); }
    /* r7-deals-10: a closing date after today is no time to close yet */
    { const d=(n,list,close)=>({inputs:{...FW},status:"closed",listPrice:3e6,salePrice:3e6,listDate:list,closeDate:close});
      const yr=new Date().getFullYear(), past=[d(1,"2025-01-06","2025-09-01"),d(2,"2025-02-03","2025-10-01"),d(3,"2025-03-03","2025-11-03")];
      const S0=A.dealsStats(past), S1=A.dealsStats(past.concat([d(4,"2026-03-02",(yr+1)+"-11-30")]));
      ok(S0.time.n===3&&S1.time.n===3&&S1.price.n===4,"43: a closed deal whose closing date is after today is left out of the time record until the date is corrected (r7-deals-10)"); }
  }
  /* ---- round 8 ---- */
  { const txt=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/\s+/g," ");
    const FW={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75,rate:10.5};
    const capSet=typeof A.capSet==="function"?A.capSet:()=>false;
    /* r8-core-1: the soft cap's rounded corner sets every walk-away ask and range peak from the printed 1.44x: such a peak
       moves with the cap, so the note says it is where the cap binds and gives the flat top, the report's row says the cap
       is a judgment, and a range top there is labelled, whatever its unprinted third decimal */
    { const one=lam=>{ const s={...FW,ind:"auto",rev:1333110,ern:551076,theta:1,lamT:lam}, V=A.model({...s,ask:1}).V; s.ask=V;
        s.rhoSell=A.bestRatio(s,0,0); s.optRho=A.bestRatio(s,1,lam);
        const n=A.optNote(s,V,A.model({...s,ask:V*s.rhoSell}),A.model({...s,ask:V*s.optRho})), t=txt(A.reportHTML(A.reportData(s,{}),{}));
        return {m:s.optRho,n,t}; };
      /* $3,800 and $3,900 a day since round 9 pooled auto repair's cells ($3,900 and $4,000 before) */
      const a=one(3800), b=one(3900), cs=/It sits where the 1\.50× cap the console puts on the ask binds \(a judgment\), so read it as "test the market", not as a measured optimum\./;
      const row=/If you can walk away \$[\d.]+M 1\.48× value .*?1\.50× value is the console’s cap on the ask \(a judgment\), not an optimum: asks from 1\.2\d× up come within 1% of value of it\./;
      const EXO={grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,rate:10.5};
      const P=A.peerMedians("medical",1.45e6,1.45e6/.24), r={...EXO,ind:"medical",ern:1.45e6,rev:1.45e6/.24,grw:P.grw,gm:P.gm,rec:P.rec,ret:P.ret,theta:.76,lamT:4250,jobs:40};
      /* $4,250 a day since round 9 pooled the medical cells ($4,000 before, where the peak now falls on 1.48 itself) */
      const Vr=A.model({...r,ask:1}).V; r.ask=Vr; r.rhoSell=A.bestRatio(r,0,0); r.optRho=A.bestRatio(r,.76,4250);
      const nr=A.optNote(r,Vr,A.model({...r,ask:Vr*r.rhoSell}),A.model({...r,ask:Vr*r.optRho})), tr=txt(A.reportHTML(A.reportData(r,{}),{})), pk=(nr.alts||[]).map(x=>x.m);
      ok(A.RHO_BIND===1.44&&a.m>1.48&&b.m<1.48&&b.m.toFixed(2)==="1.48"&&capSet(a.m)&&capSet(b.m)&&cs.test(a.n.text)&&cs.test(b.n.text)&&b.n.flat>1.2&&b.n.flat<1.3
         &&row.test(a.t)&&row.test(b.t)&&pk.some(x=>x<1.48&&x.toFixed(2)==="1.48")
         &&nr.text.includes("Asking 1.48× value (where the console’s 1.50× cap on the ask binds) instead")&&tr.includes("read it as 1.19–1.48× value; 1.48× is where the console’s 1.50× cap on the ask binds (a judgment).")
         &&!capSet(1.4349)&&capSet(1.4351),
         "43: a walk-away ask or range peak the soft cap sets from the printed 1.44x says so, with its flat top, on the console and the report, whatever its unprinted third decimal (r8-core-1)"); }
    const s={...FW,ern:3e6,rev:1.2e7,ask:9e6};
    /* r8-financing-1, r8-report-2: a coverage-bound highest price keeps x judgment from a standby note's starting share,
       and the footer names the convention, though every ask is past the 7(a) maximum */
    { const fin={type:"initial",cash:.1,note:.05,standby:true,draw:2.2e6}, D=A.reportData(s,{fin}), t=txt(A.reportHTML(D,{}));
      const mv=[.04,.06].map(note=>A.maxFinanced(s,{...fin,note},D.V).price);
      ok([D.sell,D.walk,D.cur].every(a=>a.fin.over>0&&!a.fin.noteConv)&&D.mfAt&&D.mfAt.noteConv&&D.maxFin.bind==="coverage"&&mv[0]<D.maxFin.price-1e3&&mv[1]>D.maxFin.price+1e3
         &&/the highest price that meets 1\.25× is about \$[\d.]+M fitted × judgment/.test(t)&&/× judgment: a judgment input also moves it, here [^.]*the seller-note convention \(coverage\)/.test(t),
         "43: a coverage-bound highest price badged x judgment by a standby note's starting share has the convention named in the footer when every ask is past the 7(a) maximum (r8-financing-1, r8-report-2)"); }
    /* r8-financing-2, r8-report-1: past the 7(a) maximum a standby note's share does not move the price where buyer cash
       brings an initial acquisition's equity to 10%, which prints plain published data; a paid note's moves it */
    /* built before round 9 added SBA's guaranty fee, financed by default: the no-fee build (NF) keeps the structure it tests */
    { const fS={type:"initial",cash:.03,note:.05,standby:true,extra:1e6,fee:"waived"}, DS=NF.reportData(s,{fin:fS}), tS=txt(NF.reportHTML(DS,{}));
      const fP={...fS,standby:false}, DP=NF.reportData(s,{fin:fP}), tP=txt(NF.reportHTML(DP,{}));
      const eS=[0,.04,.05,.06].map(note=>NF.maxFinanced(s,{...fS,note},DS.V).equityAbove);
      ok(eS.every(x=>Math.abs(x-eS[2])<1e-6)&&/at every price below about \$4\.56M published data : past \$[\d.]+M published data × judgment the SBA loan stays/.test(tS)
         &&tS.includes("the seller-note convention (the prices past the 7(a) maximum)")&&DS.aboveMoves===false&&DP.aboveMoves===true
         &&/at every price below about \$[\d.]+M published data × judgment : past \$[\d.]+M published data × judgment the SBA loan stays/.test(tP),
         "43: the price where buyer cash past the 7(a) maximum brings an initial acquisition's equity to 10% carries x judgment only where the note's starting share moves it (r8-financing-2, r8-report-1)"); }
    /* r8-financing-3: the working capital's own coverage, where no price works, carries its badge */
    { const t=txt(NF.reportHTML(NF.reportData({...FW},{fin:{extra:2e6,draw:1.2e6,fee:"waived"}}),{}));
      ok(/the \$250k left after the new owner’s pay covers them 0\.91× fitted , under SBA’s 1\.25× minimum/.test(t),
         "43: the report's coverage of the working capital financed in the loan, where no price works, carries the badge every other coverage figure does (r8-financing-3)"); }
    /* r8-core-2: the page prints counts and amounts in en-US in every browser, not only on the report */
    { const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8"), bare=(HTML.match(/\.toLocaleString\(\)/g)||[]).length;
      ok(bare===0&&(HTML.match(/\.toLocaleString\("en-US"\)/g)||[]).length>=40,`43: every count and amount the page formats is en-US, on the console and the Data tab as on the report (${bare} bare toLocaleString calls; r8-core-2)`); }
  }
  /* ---- round 9: the final review's findings, each checked against the code before it ---- */
  { const txt=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/\s+/g," ");
    const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
    const FW={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75,rate:10.5};
    const has=f=>typeof A[f]==="function";
    /* r9-financing-1: SBA's upfront guaranty fee (FY2027, notice 5000-881797), financed in the loan by default */
    { const gf=has("guarantyFee")?A.guarantyFee:()=>NaN;
      ok(Math.abs(gf(1e5)-1700)<1e-6&&Math.abs(gf(5e6)-138125)<1e-6&&Math.abs(gf(7e5)-15750)<1e-6&&Math.abs(gf(1e6)-26250)<1e-6&&gf(0)===0,
         "r9-financing-1: the guaranty fee is 2% to $150k, 3% to $700k, then 3.5% and 3.75% of the 75% guaranteed share ($1,700 on $100k, $138,125 on $5M)");
      const s={...FW,ind:"medical",rev:6e6,ern:3e5,ask:1.11e6}, V=A.model(s).V, f=A.debtCheck(s,1.11e6,{},V), w=NF.debtCheck(s,1.11e6,{},V), c=A.debtCheck(s,1.11e6,{fee:"cash"},V);
      ok(f.fee>0&&Math.abs(f.fee-gf(f.loan))<1e-6&&Math.abs(f.loan+f.cash+f.note-f.project)<1e-6&&Math.abs(f.project-(1.11e6+f.fee))<1e-6&&!f.ok&&w.ok&&w.fee===0
         &&Math.abs(c.loan-w.loan)<1e-6&&Math.abs(c.dscr-w.dscr)<1e-12&&Math.abs(c.cash-(w.cash+c.fee))<1e-6,
         `r9-financing-1: an ask that meets 1.25x without the fee (${A.covFmt(w)}) fails with it financed (${A.covFmt(f)}); paid in cash it leaves the loan and coverage and adds to the buyer cash`);
      const mf=A.maxFinanced(s,{},V), mw=NF.maxFinanced(s,{},V), top=A.debtCheck(s,mf.price,{},V);
      ok(mf.price<mw.price*.99&&top.ok&&!A.debtCheck(s,mf.price*1.001,{},V).ok&&Math.abs(mf.capAt-(5e6-gf(5e6)*.9)/.85)/mf.capAt<1e-9,
         `r9-financing-1: the highest financed price carries the fee (${A.money(mf.price)} against ${A.money(mw.price)} without it), and the 7(a) maximum includes it`);
      const m6=A.debtCheck({...s,ind:"mfg"},6e5,{},V), m9=A.debtCheck({...s,ind:"mfg"},9e5,{},V);
      ok(m6.fee===0&&m6.loan<=7e5&&m9.fee>0&&m9.loan>7e5&&A.debtCheck(s,6e5,{},V).fee>0,"r9-financing-1: FY2027 waives the fee on a manufacturer's loan of $700k or less, and only there");
      ok(HTML.includes('row("SBA guaranty fee"')&&HTML.includes("SBA’s upfront guaranty fee at your ask is")&&HTML.includes("<tr><td>SBA guaranty fee</td><td>upfront")&&HTML.includes('<label for="f_fee">SBA guaranty fee</label>'),
         "r9-financing-1: the table, its notes, the financing box and the Data tab name the fee"); }
    /* r9-valuation-1: an industry is valued on every cell its label names, pooled; a one-cell industry is unchanged */
    { const B=A.loadWith([["  const cs=IND_CELLS[k], V=MODELS.value,","  const cs=IND2NAICS6[k]?[IND2NAICS6[k]]:null, V=MODELS.value,"]]);
      const cm=has("cellOf")?A.cellOf("medical"):{cells:[]}, rM=A.model(FW).V/B.model(FW).V, rV=A.model({...FW,ind:"vet"}).V/B.model({...FW,ind:"vet"}).V;
      const E=A.MODELS.value.industry_effects_naics6, K=A.MODELS.value.industry_shrinkage.k_naics6, N=A.MODELS.value.industry_n6, P=A.MODELS.value.industry_effects;
      /* round 10 added the mental health specialists' cell (621112) to the pool */
      const raw=c=>{ const p=P[c.slice(0,2)], m=N[c]; return p+(E[c]-p)*(m+K)/m; }, MC=["621111","621112","621210"], n2=MC.reduce((a,c)=>a+N[c],0), p2=P["62"];
      const want=p2+(MC.reduce((a,c)=>a+N[c]*raw(c),0)/n2-p2)*n2/(n2+K);
      ok(cm.cells.includes("621111")&&cm.cells.includes("621210")&&Math.abs(cm.e-want)<1e-12&&rM>1.03&&rM<1.09&&rV===1&&has("cellOf")&&A.cellOf("vet").e===E["541940"]
         &&A.cellOf("mfg").cells.length>30&&A.cellOf("mfg").cells.every(c=>/^3[123]/.test(c)),
         `r9-valuation-1: a medical or dental practice is valued on physicians and dentists pooled (${((rM-1)*100).toFixed(1)}% above physicians alone at the framework example), manufacturing on every manufacturing cell; a veterinary practice is unchanged`);
      ok(HTML.includes("Where an industry's name covers more than one cell, it is\n    valued on all of them, pooled as one cell")&&HTML.includes("cellOf(k).src}, ${cellOf(k).n.toLocaleString(\"en-US\")} sales)"),
         "r9-valuation-1: the Data tab says which cells each pooled industry is valued on, with its sales"); }
    /* r9-console-1: the overall-outcome card names the relisting delay, not the budget, when the delay blocks the free reprice */
    { const s={...FW,lamT:4000}, V=A.model({...s,ask:1}).V; s.ask=1.4*V; s.optRho=A.bestRatio(s,s.theta,s.lamT); s.rhoSell=A.bestRatio(s,0,0);
      const b=A.optimize(s,A.model(s),s.budget,s.lamT,s.theta), R=b.U.relist;
      ok(!b.U.keys.length&&!!R&&R.days===14&&R.delay===4000*14&&R.gain>0&&R.gain<R.delay&&Math.abs(R.ask-V*s.optRho)<1e-6
         &&HTML.includes("relisting at the walk-away ask, ${money(sel.relist.ask)}, adds ${money(sel.relist.gain)} but its ${sel.relist.days} days cost"),
         `r9-console-1: with the walk-away card at ${A.money(V*s.optRho)} and the overall-outcome card doing nothing, the card says relisting adds ${R?A.money(R.gain):"?"} but its 14 days cost ${R?A.money(R.delay):"?"}`); }
    /* r9-sale-1/report-1, r9-report-2, r9-report-3, r9-report-5: the asks table's caption, header, cash at closing, accuracy label */
    { const D=A.reportData(FW,{}), h=A.reportHTML(D,{}), t=txt(h);
      ok(t.includes("Maximizes expected proceeds: the chance it sells times its average price if it does, "+A.money(D.sell.mean)+".")&&!/the price times the chance of getting it/.test(t),
         "r9-sale-1: the caption says expected proceeds is the chance it sells times the average price if it does, and gives that price");
      ok(h.includes("Median time to close if it sells<br>"),"r9-report-2: the time column says it is among deals that sell");
      ok(D.sell.cash<1&&h.includes(`${A.money(D.sell.ev)}<br><span>${A.pc(D.sell.cash)} at closing</span></td>`)&&h.includes(`${A.money(D.cur.ev)}<br><span>${A.pc(D.cur.cash)} at closing</span></td>`),
         `r9-report-3: each ask's expected proceeds says how much is paid at closing (${A.pc(D.sell.cash)} at the recommended ask; the rest comes later, in notes and earnouts)`);
      ok(t.includes(`(${D.confLabel}: ${A.MODELS.fitted.confidence.notes[D.confLabel]})`),`r9-report-5: the accuracy label says what it means (${D.confLabel})`); }
    /* r9-report-6: the track record never quotes a price above the ask it names */
    { const D=A.reportData(FW,{}), C=A.sampleSummary(Array(30).fill(1.6),false,.04), t=txt(A.reportHTML({...D,calib:C},{}));
      ok(D.sell.mean*C.shrunk>D.sell.ask&&t.includes(`about ${A.money(D.sell.ask)}, the ask itself`),`r9-report-6: a record reading ${A.money(D.sell.mean*C.shrunk)} above the ${A.money(D.sell.ask)} ask quotes the ask`); }
    /* r9-console-5: the hero's EBITDA multiple takes a manager's market pay off this business's SDE */
    ok(HTML.includes("const pay=marketPay(s), eb=s.ern-pay;")&&HTML.includes("EBITDA after a manager&rsquo;s pay")&&!HTML.includes("xx(r.M*r.fv.wedge)"),
       "r9-console-5: the hero's EBITDA multiple is the value over SDE less a manager's market pay, and says so");
    /* r9-financing-2: financed working capital counts against the valuation, and the paper says so, with the remedy */
    { const V=A.model(FW).V, s={...FW,ask:.95*V}, fin={extra:.15*V}, f=A.debtCheck(s,s.ask,fin,V), t=txt(A.reportHTML(A.reportData(s,{fin}),{}));
      ok(f.debtOverValue&&f.price<V&&t.includes("with the working capital and SBA fee in the loan, is")&&/The price is within it: financing less working capital in the loan \(a line of credit sits outside it\) or paying the SBA fee in cash at closing also lowers the debt/.test(t),
         "r9-financing-2: an ask below value flagged by the working capital financed in the loan says that is why, and that financing less of it fixes it"); }
    /* r9-financing-3: an owner buyout can buy part of the business, priced and capped pro rata */
    { const V=A.model(FW).V, f=A.debtCheck(FW,2e6,{type:"buyout",stake:.4},V), g=A.debtCheck(FW,2e6,{type:"initial",stake:.4},V);
      ok(Math.abs(f.bought-8e5)<1e-6&&Math.abs(f.value-.4*V)<1e-6&&Math.abs(f.equityNeed-8e4)<1e-6&&Math.abs(f.project-(8e5+f.fee))<1e-6&&g.bought===2e6&&g.stake===1,
         "r9-financing-3: a 40% stake at a $2M price is an $800k purchase, its debt capped at 40% of the value; other types buy the whole business"); }
    /* r9-console-2: the equation panels plug in figures at the input boxes' precision */
    ok(HTML.includes("{${tmd(fc.sbaPay)}+${tmd(fc.notePay)}}")&&HTML.includes("\\\\frac{${tmi(bi.dE)}-${tmi(bi.c)}}{${tmi(bi.c)}}"),"r9-console-2: eq_fs and eq_rs print their figures at moneyIn's precision");
    /* r9-worksheet-1: the earnings basis adds up as printed */
    { let bad=0, n=0; const rn=(i=>()=>(i=(i*16807)%2147483647)/2147483647)(97);
      for(let i=0;i<400;i++){ const y=()=>({rev:2e6+4e6*rn(),ni:4e4+4e5*rn(),owner:5e4+2.5e5*rn(),dep:3e4*rn(),int:2e4*rn(),nonop:rn()<.3?5e3*rn():0});
        const R=A.recastSDE({entity:"scorp",weight:["latest","w321","avg"][i%3],years:[y(),y(),y()]}); if(!(R.sde>0)) continue; n++;
        const t=txt(A.reportHTML({...A.reportData(FW,{}),recast:R},{})), m=t.match(/SDE of (\S+), built.*?income before taxes (\S+), add-backs (\S+?)(?:, less (\S+) of deductions)?[.;]/);
        const v=x=>x?A.moneyVal(x)*(x.startsWith("−")?-1:1):0;
        if(!m||Math.abs(v(m[2])+v(m[3])-v(m[4])-v(m[1]))>1e-6*Math.max(1,v(m[1]))) bad++; }
      ok(n>300&&bad===0,`r9-worksheet-1: the report's earnings basis adds up as printed in ${n-bad} of ${n} worksheets`); }
    /* r9-datatab-1: the kill zone is stated on the axis the console uses, and the flag reads it there */
    { const V=A.model(FW).V;
      ok(A.model({...FW,ask:1.4*V}).fc.kill===true&&A.model({...FW,ask:1.11*V}).fc.kill===false&&HTML.includes("of price-killed deals die on a gap of only <b>11&ndash;30% of the asking price</b>"),
         "r9-datatab-1: 11-30% of the ask is 12-43% over value: the console's sentence names the axis and the flag reads the gap over value on it"); }
    /* r9-datatab-2, r9-datatab-3: the Refused table points nowhere false; the hedonic effects print as percentages */
    ok(!HTML.includes("Held as reference")&&!HTML.includes("deal-break evidence above")&&HTML.includes("const HP=(c,bare)=>")&&!HTML.includes("(Fv.quality_weights.hedonic.owner_operated[0]*100).toFixed(0)"),
       "r9-datatab-2/3: no reference to a table not shown or to evidence above; the listing hedonic is printed as e^b - 1");
    /* r9-valuation-3: each change the value gap leaves out has its own reason */
    ok(!HTML.includes("Left out because ")&&HTML.includes("the proceeds, not the value")&&HTML.includes("less on its own)"),"r9-valuation-3: the value-gap note gives outreach and a change that lowers value alone their own reasons");
    /* r9-console-4: the peer bars are coloured by better or worse than peers */
    ok(HTML.includes('good:["cc","own","plt"].includes(k)?r.z[k]<=0:r.z[k]>=0')&&HTML.includes("var v=+r.v||0, p=v>=0, g=r.good!==undefined?!!r.good:p"),"r9-console-4: more concentration or owner dependence than peers is coloured as worse");
    /* r9-sale-3: the lede names the first objective */
    ok(HTML.includes("maximizing expected proceeds is not always the same as maximizing the seller's overall outcome")&&!HTML.includes("maximizing price is not always"),"r9-sale-3: the optimizer's lede says expected proceeds, not price");
    /* r9-sale-4: the days the cards' note gives are the difference of the tiles as printed */
    { let n=0, bad=0; const inds=["medical","home","rest","prof","auto","msp"];
      for(const ind of inds) for(const ern of [1.5e5,4e5,1.45e6]) for(const lamT of [0,900,3000]){ const s={...FW,ind,ern,rev:ern/.22,lamT}, V=A.model({...s,ask:1}).V;
        for(const k of [1,1.3]){ const x={...s,ask:k*V}; x.optRho=A.bestRatio(x,x.theta,x.lamT); x.rhoSell=A.bestRatio(x,0,0); const r=A.model(x), b=A.optimize(x,r,x.budget,x.lamT,x.theta);
          const uRho=b.U.keys.includes("reprice")?x.optRho:x.rhoSell, t=A.optCardNote(x,b,x.rhoSell,uRho).text, m=t.match(/takes (?:about )?(a day|\d+ days) (longer|less) from start to close/);
          const d=Math.round(b.U.t+b.U.days)-Math.round(b.V.t+b.V.days); if(!m) { if(Math.abs(d)>=1&&!/Both objectives select/.test(t)) bad++; continue; } n++;
          const nd=m[1]==="a day"?1:parseInt(m[1]); if(nd!==Math.abs(d)||(m[2]==="longer")!==(d>0)) bad++; } }
      ok(n>10&&bad===0,`r9-sale-4: the cards' note gives the tiles' own day difference (${n} notes, ${bad} off)`); }
    /* r9-inputs-5: the growth box takes a minus sign on a phone */
    ok(/<input class="v" id="v_grw" type="text"(?![^>]*inputmode)[^>]*>/.test(HTML),"r9-inputs-5: the growth box asks for the full keyboard, which has a minus sign");
  }
  /* ---- round 10: the last review's findings, each checked against the code before it ---- */
  { const FW={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5,lamT:900,theta:.75,rate:10.5};
    const T=h=>h.replace(/<[^>]+>/g," ").replace(/&rsquo;/g,"’").replace(/&ndash;/g,"–").replace(/\s+/g," ");
    const mul=a=>()=>{ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; };
    /* r10-financing-2 (medium): FY2027's waiver covers a loan of $700k or less only; set as waived, a larger loan pays the
       whole fee, financed in the loan, and the page says why */
    { const s={...FW,ern:3e5,rev:1.5e6}, V=A.model(s).V, gf=A.guarantyFee, lo=A.debtCheck(s,6e5,{fee:"waived"},V), hi=A.debtCheck(s,1.2e6,{fee:"waived"},V), fi=A.debtCheck(s,1.2e6,{},V);
      const m=A.debtCheck({...s,ind:"mfg"},1.2e6,{fee:"waived"},V), mw=A.maxFinanced(s,{fee:"waived"},V), mf=A.maxFinanced(s,{},V);
      const t=T(A.reportHTML(A.reportData({...s,ask:1.2e6},{fin:{fee:"waived"}}),{}));
      ok(lo.loan<=7e5&&lo.fee===0&&hi.loan>7e5&&Math.abs(hi.fee-gf(hi.loan))<1e-6&&hi.feeIn===hi.fee&&Math.abs(hi.loan-fi.loan)<1e-6&&Math.abs(m.fee-gf(m.loan))<1e-6
         &&Math.abs(mw.capAt-mf.capAt)<1e-6&&/SBA fee in the loan, which is above the waiver’s \$700k/.test(t)
         &&A.SBA_FEE.modes.waived.includes("$700k")&&HTML.includes("in the loan: above the waiver’s $700k")&&HTML.includes("The waiver covers only a loan of $700k or less, so this one pays it"),
         `r10-financing-2: set as waived, a $1.04M loan pays its ${A.money(hi.fee)} fee, financed as usual, and a $510k loan none; the option, table, note and report say the waiver ends at $700k`); }
    /* r10-financing-3: the fee's steps make the equity pass, fail and pass again; every failing range is named, and each
       printed bound passes */
    { const E={...FW,ind:"mfg",ern:1e6,rev:4e6,ask:7e5}, fE={type:"initial",cash:.0572,note:.05,standby:true,extra:1e5}, VE=A.model(E).V, mE=A.maxFinanced(E,fE,VE);
      const gE=(mE.equityGaps||[])[0]||{}, at=p=>A.debtCheck(E,p,fE,VE).equityOK, tE=T(A.reportHTML(A.reportData(E,{fin:fE}),{}));
      const K={...E}, fK={type:"initial",cash:.05,note:.05,standby:true,extra:5e4,fee:"cash"}, VK=A.model(K).V, mK=A.maxFinanced(K,fK,VK), eK=A.finEdges(mK);
      const B={...FW}, fB={type:"buyout",cash:.076,note:.05,extra:1e4,fee:"cash"}, VB=A.model(B).V, mB=A.maxFinanced(B,fB,VB), tB=T(A.reportHTML(A.reportData(B,{fin:fB}),{}));
      const inside=g=>[.2,.5,.8].every(x=>!A.debtCheck(B,g.last+(g.pass-g.last)*x,fB,VB).equityOK);
      ok(mE.equityFrom>0&&(mE.equityGaps||[]).length===1&&at(A.moneyVal(A.moneyDown(gE.last)))&&at(A.moneyVal(A.moneyUp(gE.pass)))&&!at(7e5)&&!at(6.9e5)&&at(A.moneyVal(A.moneyUp(mE.equityFrom)))
         &&tE.includes(`is also under SBA’s 10% minimum between about ${A.moneyDown(gE.last)} and ${A.moneyUp(gE.pass)}`)&&tE.includes("which cannot be waived for an initial acquisition"),
         `r10-financing-3: a manufacturer's initial acquisition passes from ${A.moneyUp(mE.equityFrom)}, fails again between ${A.moneyDown(gE.last)} and ${A.moneyUp(gE.pass)} as the fee starts past a $700k loan, and the report names that range`);
      ok(eK.from&&A.debtCheck(K,A.moneyVal(eK.from),fK,VK).equityOK&&!A.debtCheck(K,725000,fK,VK).equityOK,
         `r10-financing-3: an equity floor whose loan is exactly $700k prints a price that passes (${eK.from}; $725,000 itself is still under the waiver and fails)`);
      ok((mB.equityGaps||[]).length===3&&mB.equityGaps.every(g=>inside(g)&&A.debtCheck(B,A.moneyVal(A.moneyDown(g.last)),fB,VB).equityOK&&A.debtCheck(B,A.moneyVal(A.moneyUp(g.pass)),fB,VB).equityOK)
         &&/under SBA’s 10% minimum between about \$[\d.]+k and \$[\d.]+k, between \$[\d.]+k and \$[\d.]+k and between \$[\d.]+k and \$[\d.]+M/.test(tB),
         `r10-financing-3: an owner buyout whose equity fails in three ranges below its highest price has all three named (${(mB.equityGaps||[]).map(g=>A.moneyDown(g.last)+"-"+A.moneyUp(g.pass)).join(", ")})`); }
    /* r10-financing-2: past the waiver's $700k the fee starts, which can set an equity floor with no standby note: the floor
       does not name a note's credit there */
    { const s={...FW,ind:"mfg",rev:7429900,ern:6205900,ask:47872000}, f={type:"buyout",cash:.0995,note:0,standby:true,extra:0,draw:3075000,capex:304260,fee:"waived"};
      const D=A.reportData(s,{fin:f}), t=T(A.reportHTML(D,{}));
      ok(D.maxFin.equityFrom>0&&/Below about \$[\d.]+k published data the buyer’s equity is under SBA’s 10% minimum/.test(t)&&!/standby note/.test(t),
         `r10-financing-2: an owner buyout at 9.95% cash with no note passes SBA's 10% only once the fee starts past a $700k loan, and the floor (${A.moneyUp(D.maxFin.equityFrom||0)}) names no note's credit`); }
    /* r10-financing-3: at a fee tier's edge the loan is solved with the fee it carries, on both sides of the edge */
    { const s={...FW,ind:"fit",ern:1.477e7,rev:2.425e8}, f={type:"expansion",cash:.0995,note:.1,noteRate:0,noteYears:25,capex:1.4295e6}, V=A.model(s).V; let bad=0;
      for(const e of [15e4,7e5]){ let a=1e4,b=5e6; for(let i=0;i<90;i++){ const m=(a+b)/2; if(A.debtCheck(s,m,f,V).loan>e) b=m; else a=m; }
        for(const p of [a,b]){ const d=A.debtCheck(s,p,f,V), base=d.bought*(1-f.cash)-d.note; if(Math.abs(d.loan-(base+(1-f.cash)*d.fee))>1e-6||d.equityOK) bad++; } }
      ok(bad===0,`r10-financing-3: on both sides of the $150k and $700k fee edges the loan carries the fee it was solved with, so a 9.95% cash share never reads as 10% there (${bad} off)`); }
    /* r10-financing-4: with SBA's fee financed, a paid note's starting share moves the value-bound highest price and an owner
       buyout's equity edge, which carry x judgment; paid in cash, the price does not move and prints fitted */
    { const s0={...FW,gm:.348}, V=A.model(s0).V, s={...s0,ask:1.2*V}, D=A.reportData(s,{}), t=T(A.reportHTML(D,{})), tc=T(A.reportHTML(A.reportData(s,{fin:{fee:"cash"}}),{}));
      const b0={...FW,ern:3e5,rev:1.5e6}, Vb=A.model(b0).V, DB=A.reportData({...b0,ask:Vb},{fin:{type:"buyout",cash:.08,extra:4e4}}), tb=T(A.reportHTML(DB,{}));
      ok(Math.abs(A.model(s).qFactor-1)<=.005&&D.maxFin.bind==="value"&&/finance is about \$[\d.]+M fitted × judgment , where the acquisition debt reaches the model value/.test(t)
         &&/finance is about \$[\d.]+M fitted , where the acquisition debt reaches the model value/.test(tc)&&/the seller-note convention \(the highest financed price/.test(t)
         &&/Between about \$177k published data × judgment and/.test(tb),
         "r10-financing-4: the value-bound highest price and a buyout's equity edge, both moved by a paid note's share through the financed fee, carry x judgment; with the fee paid in cash the price prints fitted"); }
    /* r10-financing-1: debt above value from the financed fee alone gets the fee's remedy, not the working capital's */
    { const V=A.model(FW).V, s={...FW,ask:.995*V}, fin={type:"buyout",cash:.02,note:0}, f=A.debtCheck(s,s.ask,fin,V), t=T(A.reportHTML(A.reportData(s,{fin}),{}));
      ok(f.debtOverValue&&f.extra===0&&f.feeIn>0&&t.includes("The price is within it: paying the SBA fee in cash at closing also lowers the debt")&&!/financing less working capital/.test(t)
         &&HTML.includes('${fe?"pay the SBA fee in cash at closing, ":""}or add equity.'),
         "r10-financing-1: an ask within value whose debt is over it only through the financed fee is told to pay the fee in cash, in the report and the table's note"); }
    /* r10-financing-5: SBA's $350k valuation test reads the price of the stake an owner buyout buys */
    ok(HTML.includes("notes.push(fc.ownValuation?(FIN.type===\"buyout\"?`At ${money(fc.bought)}")&&A.debtCheck({...FW,ern:3e5,rev:1.5e6},1.2e6,{type:"buyout",stake:.25},1e7).ownValuation===true,
       "r10-financing-5: the console's valuation note tests the stake's price ($300k of a $1.2M business), as debtCheck's ownValuation does");
    /* r10-financing-6: the sentences that size the loan name the financed fee in it */
    { const t1=T(A.reportHTML(A.reportData(FW,{fin:{cash:.1,note:.9,standby:true,extra:3e5}}),{})), t2=T(A.reportHTML(A.reportData(FW,{fin:{cash:.1,extra:5.45e6}}),{}));
      ok(/the SBA loan, \$276k for working capital and closing costs with the SBA fee, does not grow with it/.test(t1)&&t2.includes("The working capital and closing costs, with the SBA fee financed in the loan, take the 7(a) maximum loan")
         &&HTML.includes('for working capital and closing costs${fw.feeIn>0?" with the SBA fee":""},'),
         "r10-financing-6: the no-limit and 7(a)-maximum sentences say the loan carries the financed SBA fee, on the page and the report"); }
    /* r10-report-5: a stake's value-bound highest price names the stake's value */
    { const V=A.model(FW).V, D=A.reportData({...FW,ask:.97*V},{fin:{type:"buyout",stake:.4,cash:.01,note:.05,standby:true,extra:1.95e5}}), t=T(A.reportHTML(D,{}));
      ok(D.maxFin.bind==="value"&&t.includes(`where the acquisition debt reaches the model value of the stake, ${A.money(D.mfAt.value)}`)&&Math.abs(D.mfAt.value-.4*V)<1e-6,
         `r10-report-5: for a 40% stake the highest price is where the debt reaches the stake's value, ${A.money(.4*V)}, not the ${A.money(V)} printed at the top`); }
    /* r10-report-6: outside the fitted data the in-support accuracy is not printed */
    { const dm=A.reportData({...FW,rev:1.6e6},{}), ds=A.reportData({...FW,ern:2e7,rev:8e7},{}), tm=T(A.reportHTML(dm,{})), ts=T(A.reportHTML(ds,{}));
      ok(dm.confOutside&&ds.confOutside&&/Accuracy fitted about 11–16% Low: outside the fitted data/.test(tm)&&/Accuracy not measured Low: outside the fitted data/.test(ts)
         &&!tm.includes(A.pc(dm.conf)+" chance the price")&&!ts.includes(A.pc(ds.conf)+" chance the price")&&HTML.includes("c\\\\text{ not measured: "),
         "r10-report-6: past the fitted margin the report gives the 11-16% the fit measured there, past 3x size 'not measured', not the in-support chance; eq_cs says so"); }
    /* r10-valuation-1: the risk tile pools the label's cells by the fit's own rule */
    { const R=A.MODELS.risk, P=R.naics6_pools||{}, a=R.naics6_gamma_shape, med=P.medical||{cells:[]}, r=A.fitRisk(1e6,"medical",null,10,false,null);
      ok(med.cells.includes("621111")&&med.cells.includes("621210")&&Math.abs(med.log_rr-Math.log((a+med.O)/(a+med.E)))<1e-4&&r.naics6Eff===med.log_rr
         &&Object.keys(R.naics6_pools||{}).length===14&&!("ecom" in (R.naics6_pools||{}))&&A.fitRisk(1e6,"vet",null,10,false,null).naics6Eff===R.naics6_effects["541940"]
         &&Object.entries(R.naics6_pools||{}).every(([k,v])=>v.cells.every(c=>A.IND_CELLS[k].includes(c))),
         `r10-valuation-1: a medical practice is risked on its pooled cells (log RR ${r.naics6Eff}, physicians alone ${R.naics6_effects["621111"]}); a one-cell label is unchanged`); }
    /* r10-valuation-2: a pooled label's accuracy counts each business's cell's distance from the pool */
    { const C=A.MODELS.fitted.confidence, MV=A.MODELS.value, k=MV.industry_shrinkage.k_naics6, c=A.confidenceOf({ind:"mfg",ern:7e5,rev:3.5e6},{z:{em:0},extrapMax:0});
      const v=A.confidenceOf({ind:"vet",ern:7e5,rev:3.5e6},{z:{em:0},extrapMax:0}), n=A.cellOf("vet").n;
      ok(c.depthVar>C.tau2*(1-c.comps)*10&&c.p<.52&&Math.abs(v.depthVar-C.tau2*k/(n+k))<1e-15,
         `r10-valuation-2: manufacturing's industry term is ${c.depthVar&&c.depthVar.toFixed(4)} (the pooled count alone gave ${(C.tau2*(1-c.comps)).toFixed(5)}), its accuracy ${c.p.toFixed(3)}; a one-cell industry keeps tau2 k/(n+k)`); }
    /* r10-datatab-1: the pools take the cells their labels name */
    ok(["621111","621112","621210"].every(c=>A.IND_CELLS.medical.includes(c))&&A.IND_CELLS.ecom.includes("454111")&&A.IND_CELLS.auto.includes("811198")&&!A.IND_CELLS.auto.includes("811191")
       &&HTML.includes("oil change shops\n    (811191) are maintenance, not auto repair"),
       "r10-datatab-1: medical pools mental health physicians, e-commerce electronic shopping, auto repair its all-other cell; the Data tab names the edges judged");
    /* r10-sale-2: an over-budget change that clears its cost only with the reprice says so */
    { const s={...FW,lamT:2500,budget:2000}, V=A.model({...s,ask:1}).V; s.ask=1.4*V; s.optRho=A.bestRatio(s,s.theta,s.lamT); s.rhoSell=A.bestRatio(s,0,0);
      const b=A.optimize(s,A.model(s),s.budget,s.lamT,s.theta), bl=b.U.blocked||{}, r=A.model(s), solo=A.model(A.applyAll(s,r,["qoe"],s.optRho));
      const uSolo=solo.EVp+(1-solo.PC)*s.theta*solo.V-s.lamT*(solo.tMean+A.daysOf(s,["qoe"]))-bl.c;
      ok(!b.U.keys.length&&!!b.U.relist&&bl.k==="qoe"&&bl.withReprice===true&&uSolo<b.U.U&&HTML.includes("relisting at the walk-away ask within its ${sel.blocked.days} days,"),
         "r10-sale-2: the relist card's over-budget QoE clears its cost only with the relisting, and the card says so"); }
    /* r10-sale-1, r10-console-1: a left-out change that moves neither the value nor the proceeds has no effect */
    ok(HTML.includes('has"} no effect at these inputs')&&HTML.includes("z.filter(o=>!(Math.abs(o.dE)<1))"),"r10-sale-1: the value-gap note names a change that moves nothing as having no effect, by the table's own proceeds");
    /* r10-sale-3, r10-console-5: the console's time tile states the sale condition */
    ok(HTML.includes('Median time to close if it sells <span class="pv f" id="o_t_pv">')&&HTML.includes("<span>Median time to close if it sells</span>"),"r10-console-5: the hero tile and the key-figure strip say the median is among deals that close");
    /* r10-console-3: the coverage fraction's printed operands reproduce the verdict */
    { let n=0, bad=0; const rn=mul(1010), inds=Object.keys(A.IND), dl=v=>Math.round(v);
      for(let i=0;i<4000;i++){ const ern=6e4*Math.pow(40,rn()), s={...FW,ind:inds[i%inds.length],ern,rev:ern/(.12+.3*rn())}, V=A.model({...s,ask:1}).V, f=A.debtCheck(s,V*(.6+.8*rn()),{},V);
        if(!(f.loan>0&&f.ds>0&&f.cf>0)) continue; n++; const x=(dl(s.ern)-dl(f.draw)-dl(f.capex))/(dl(f.sbaPay)+dl(f.notePay));
        if((x>=f.min)!==f.ok&&Math.abs(x-f.min)>1e-6) bad++; }
      ok(n>2000&&bad===0&&HTML.includes("\\frac{${tmd(s.ern)}-${tmd(fc.draw)}-${tmd(fc.capex)}}{${tmd(fc.sbaPay)}+${tmd(fc.notePay)}}"),
         `r10-console-3: eq_fs prints its operands to the dollar, which put the fraction on the verdict's side of the minimum in ${n-bad} of ${n} states`); }
    /* r10-console-4: the hero multiple's badge covers the manager's pay its EBITDA figure rests on */
    ok(HTML.includes('const jj=j||what==="multiple"&&ebJ;')&&HTML.includes("the EBITDA multiple beside it also rests on a general manager’s market pay"),"r10-console-4: the EBITDA multiple's badge carries x judgment for the market pay's rank");
    /* r10-worksheet-1: the Deals tab's quality fit prints e^b - 1 per peer step */
    ok(HTML.includes("const e=(Math.exp(q.beta[i])-1)*100")&&HTML.includes("(Math.exp(q.beta[i])*q.se[i]*100).toFixed(1)")&&!HTML.includes("Math.abs(q.beta[i]*100).toFixed(1)"),
       "r10-worksheet-1: the Deals tab's quality effects print as percentages of price, e^b - 1, with SE e^b se");
    /* r10-datatab-2: the notice number keeps SBA's hyphen; the examples cite the SOP */
    ok(HTML.includes('.replace(/\\bNotice (\\d+)-(\\d+)/g,"Notice $1\\u0001$2")')&&HTML.includes("SBA&rsquo;s own examples, SOP 50 10 8.1, Section A, Ch. 4)"),
       "r10-datatab-2: the Data tab's formatter leaves 'Notice 5000-881797' as SBA prints it, and the fee examples cite the SOP");
  }
  /* the page wiring */
  ok(HTML.includes('<button class="tab" data-v="deals">Deals</button>')&&HTML.includes('<section class="sec" id="sec_fin" data-norender>')
     &&HTML.includes('<div id="view-deals" hidden data-norender>')&&HTML.includes('if(el.closest("[data-norender]")) return;')
     &&HTML.includes('$("view-deals").hidden=v!=="deals";')&&HTML.includes('localStorage')&&HTML.includes('"omni.deals.v1"'),
     "43: the Deals tab, the financing section and the dialogs are wired; their inputs redraw only their own part");
  { const a=HTML.indexOf("<h2>Live self-audit</h2>"), b=HTML.indexOf("<h2>Broker tools: the rules and conventions behind them</h2>"), c=HTML.indexOf('$("dataviews").innerHTML=h;');
    ok(a>0&&b>a&&c>b&&HTML.includes('{k:"broker",   id:"d-broker",   re:/^Broker tools/')&&HTML.includes('var ORDER=["badges","fitted","aggregate","judgement","public","still","audit","broker"];')
       &&/\n  broker:SVG\+'/.test(HTML)&&HTML.includes("#view-data .sec:nth-of-type(8)"),
       "43: the Data tab's broker section comes last, after the self-audit, with its own id, index star, emblem and hue (the seven before it keep theirs)"); }
}

/* ---- 44. October 2026, the owner: "remove the first light step", "make the wormhole far cooler", "reduce lag", and a
   second version without the equation documentation, the provenance labels or the Data tab ---- */
{
  const HTML=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8"), L=HTML.split("\n");
  /* the film's clock rushes over the span first light filled: continuous, rising, and undone exactly by unwarp */
  const pick=re=>L.find(l=>re.test(l))||"";
  const src=[pick(/^var SKIP=\{/),pick(/^function warp\(x\)/),pick(/^function unwarp\(c\)/),L[L.findIndex(l=>/^function unwarp\(c\)/.test(l))+1]||""].join("\n");
  let W=null; try{ W=new Function(src+"\nreturn {SKIP:SKIP,warp:warp,unwarp:unwarp};")(); }catch(e){ W=null; }
  ok(!!W,"44: the film's clock (SKIP, warp, unwarp) evaluates outside the browser");
  if(W){ const K=W.SKIP; let jump=0, down=0, inv=0, prev=W.warp(-1);
    for(let x=-1;x<=14;x+=.001){ const y=W.warp(x); jump=Math.max(jump,Math.abs(y-prev)); if(y<prev-1e-12) down++; prev=y;
      inv=Math.max(inv,Math.abs(W.unwarp(y)-x)); }
    ok(down===0&&jump<.006&&inv<1e-6&&Math.abs(W.warp(K.A)-K.A)<1e-12&&Math.abs(W.warp(K.A+K.W)-(K.A+K.W+K.S))<1e-12,
       `44: the clock skips ${K.S} film seconds over ${K.W} of its own, rising and continuous (at most ${(jump*1000).toFixed(2)}x film speed), and unwarp undoes it (${inv.toExponential(1)})`); }
  ok(!/first light/.test(pick(/^var CAPS=/))&&!/"first light"/.test(pick(/^function phaseOf/))&&!HTML.includes("u_cmb")&&!/LIGHT:/.test(pick(/^var TL=\{P0:/))
     &&HTML.includes("var fire=.9*sm(.06,.3,c)*(1-sm(1,1.55,unwarp(c)))")&&HTML.includes("T:TL.P0+(TL.JUMP-SKIP.S)/SPEED+TL.REVEAL"),
     "44: no first-light caption, phase, plasma or microwave background; the fireball fades on the clock's own time; the reveal time counts the skip");
  ok(HTML.includes("vec3 disk(float q,float ph)")&&HTML.includes("float al=A/re, ey=e.y/re, Z=e.y/(SN+al*ey);")&&!/arcs crawling on its rim/.test(HTML)
     &&HTML.includes("gl.copyTexImage2D(gl.TEXTURE_2D,0,gl.RGB,x0,y0,w,h,0);"),"44: the gate is a lensed accretion disk round a photon ring, in a box wide enough for it");
  /* lag: no sibling :has() (it made every render restyle ~11,000 elements), the star map keeps an unchanged drawing,
     the ink bars repaint only the tables a render touched */
  ok(!/:has\(\s*\+/.test(HTML)&&HTML.includes(".rp-t tr.rp-hs>*{border-bottom:0;padding-bottom:2px}")&&HTML.includes("<tr${sub?' class=\"rp-hs\"':\"\"}><th scope=\"row\">"),
     "44: the report's note rows are marked by a class, not tr:has(+ tr.rp-sub)");
  ok(HTML.includes("if(key!==null&&svg.__key===key&&svg.__mark&&svg.__mark===svg.lastChild) return true;")&&HTML.includes("deb = setTimeout(run, 90);")
     &&!HTML.includes("document.querySelectorAll('table').forEach(function(t){ t.removeAttribute('data-inked'); });"),
     "44: the star map skips an unchanged redraw; the ink bars repaint only touched tables");
  /* the second version is what the build makes of this page */
  const r=require("child_process").spawnSync(process.execPath,[require("path").join(__dirname,"..","tools","build_foruse.js"),"--check"],{encoding:"utf8"});
  ok(r.status===0,"44: foruse.html is what tools/build_foruse.js builds from index.html ("+((r.stdout||r.stderr||"").trim())+")");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
