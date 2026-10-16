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
  /* 1. the console reproduces the fitted model exactly (Python mirror on the shipped, rounded tables) */
  for(const c of PINS){ const r=A.fitRisk(...c.args);
    for(const k of ["p5","p8","pTerm","lgd","expLoss","rel"]) ok(Math.abs(r[k]-c[k])<=1e-9*Math.max(1,Math.abs(c[k])),`pin ${JSON.stringify(c.args)} ${k}: ${r[k]} vs ${c[k]}`); }
  /* 2. horizons: 0 < p5 < p8 < pTerm < 1, headline is the term, and the term is p8 times the fitted tail at the note's size */
  const TB=R.tail.by_band, tailRef=loan=>{ const x=Math.log(Math.max(loan,1)), c=TB.centres.map(Math.log), n=c.length;
    if(x<=c[0]) return TB.scale*TB.ratio[0]; if(x>=c[n-1]) return TB.scale*TB.ratio[n-1];
    let j=0; while(!(x>=c[j]&&x<=c[j+1])) j++; return TB.scale*(TB.ratio[j]+(TB.ratio[j+1]-TB.ratio[j])*(x-c[j])/(c[j+1]-c[j])); };
  for(const k of Object.keys(A.IND)) for(const v of [2e5,1e6,4e6]){ const r=A.fitRisk(v,k,null,10,false,null);
    ok(r.p5>0&&r.p5<r.p8&&r.p8<r.pTerm&&r.pTerm<0.5,`${k} ${v}: horizons ordered ${r.p5} ${r.p8} ${r.pTerm}`);
    ok(r.p===r.pTerm&&Math.abs(r.pTerm-r.p8*r.tail)<1e-12&&Math.abs(r.tail-tailRef(r.loan))<1e-12,`${k}: headline is the term, p8 x the tail at the note's size`); }
  for(const c of PINS){ const r=A.fitRisk(...c.args); ok(Math.abs(r.pTerm-c.p8*tailRef(r.loan))<1e-12,`pin ${JSON.stringify(c.args)}: pTerm = pinned p8 x the tail`); }
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
          1.15x and the 1.5x cap; which wins is a knife-edge in FAN_S (flip near 0.94 at $900/day, 0.88 with no delay
          cost) and theta (0.776 at $900/day, 0.766 with no delay cost; pinned in 28), so the
          WINNER is not pinned: it must be one of the two peaks, and the peaks must lie within 1% of value (the page
          then shows the patient-seller price as a range) */
  { const b0=A.bestRatio(EXF,0,900), b75=A.bestRatio(EXF,.75,900);
    ok(b0>=1.08&&b0<=1.13,`bestRatio(EX,0) ${b0.toFixed(3)}`);
    ok((b75>=1.08&&b75<=1.25)||b75>=1.45,`bestRatio(EX,.75) ${b75.toFixed(3)} is neither the interior peak nor the cap`);
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
  /* the walk-away asks the Data tab quotes (75% kept, delay charged on the mean time to close): $900/day 1.13, 1.14, 1.15,
     1.15; $4,000/day 1.08, 1.12, 1.14, 1.14 for earnings $150k/$400k/$1.45M/$5M (the $150k figure at $4,000/day moved from
     1.09 when the peer medians were fitted, October 2026). If another change moves them, update the Data-tab paragraph. */
  { const Q={900:["1.13","1.14","1.15","1.15"],4000:["1.08","1.12","1.14","1.14"]};
    [1.5e5,4e5,1.45e6,5e6].forEach((ern,i)=>{ const s={...EXO,ind:"medical",ern,rev:ern/0.24};
      for(const lam of [900,4000]){ const b=A.bestRatio(s,.75,lam);
        ok(b.toFixed(2)===Q[lam][i],`Data tab: walk-away ask at $${ern} and $${lam}/day ${b.toFixed(3)} (text says ${Q[lam][i]})`); } }); }
  /* the knife edge the Data tab quotes for the framework example: the cap wins from about 77% kept with no delay cost,
     78% at $900/day, 81% at $4,000/day (76.6 / 77.6 / 81.0 since the R2-2 anchoring fix) */
  { const ex={...EXO,ind:"medical",rev:6e6,ern:1.45e6};
    for(const [lam,pct] of [[0,77],[900,78],[4000,81]]){ let lo=.70,hi=.86;
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
      for(let j=1;j<=L;j++) if(isMax(v,j)){ let lo=u[j]; for(let q=Math.min(j,jo);q<=Math.max(j,jo);q++) lo=Math.min(lo,u[q]);
        pk.push({m:ms[j],u:u[j],here:t===th,depth:(u[j]-lo)/V,d:Math.abs(ms[j]-ss.optRho)}); } }
    const U=m=>{ const x=A.model({...ss,ask:V*m}); return x.EVp+(1-x.PC)*th*x.V-lam*x.tMean; };
    return {V,pk,U,ms,u,uK:U(ss.optRho)};
  };
  const checkNote=(ss,n,tag)=>{
    const R=noteRef(ss), V=R.V, uK=R.uK;
    /* the range: shown exactly when another peak (here or one 1% step of theta away) is within 1% of value */
    if(n.alt) ok(n.text.includes("close to a tie, so read the patient-seller price as a range")&&uK-n.alt.u<=.01*V*(1+1e-9)&&Math.abs(n.alt.m-ss.optRho)>.02
      &&R.pk.some(p=>Math.abs(p.m-n.alt.m)<=.025&&p.d>.015),`range end ${n.alt.m.toFixed(3)} is a real peak within 1% ${tag}`);
    else ok(!/as a range/.test(n.text)&&!R.pk.some(p=>p.d>.06&&uK-p.u<=.0095*V),`no range only when no other peak is within 1% ${tag}: ${n.text}`);
    /* the flat top: only at the cap, printed rounded UP, and the printed ask and every fine-grid ask above it within 1% */
    if(n.flat!==null&&n.flat!==undefined){
      const above=R.ms.map((m,j)=>[m,R.u[j]]).filter(v=>v[0]>=n.flat-1e-9);
      ok(!n.alt&&ss.optRho>A.RHO_MAX-.02&&Math.abs(n.flat*100-Math.round(n.flat*100))<1e-9
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
      ok(!/[−-]\$/.test(n.text)&&!/NaN|undefined|Infinity|1 days/.test(n.text),`no negative money, NaN or '1 days' in the note ${tag}: ${n.text}`);
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
  /* the default state (framework example, 75% kept, $900/day): the two peaks tie and the note shows the range */
  { const ex={...EXO,ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,theta:.75,lamT:900}, V=A.model({...ex,ask:1}).V;
    ex.rhoSell=A.bestRatio(ex,0,0); ex.optRho=A.bestRatio(ex,.75,900);
    const n=A.optNote(ex,V,A.model({...ex,ask:V*ex.rhoSell}),A.model({...ex,ask:V*ex.optRho}));
    ok(n.kind==="higher"&&!!n.alt&&/1\.1\d–1\.50× value/.test(n.text),`framework example: patient-seller range shown (${n.text})`); }
  /* a walk-away ask at the cap with an objective that climbs all the way there: no range (there is no second peak, and
     1.35x was only where the old scan stopped); the note says how flat the top is instead */
  { const ex={...EXO,ind:"mfg",rev:5e5,ern:1.2e5,ask:4.5e5,theta:1,lamT:900}, V=A.model({...ex,ask:1}).V;
    ex.rhoSell=A.bestRatio(ex,0,0); ex.optRho=A.bestRatio(ex,1,900);
    const n=A.optNote(ex,V,A.model({...ex,ask:V*ex.rhoSell}),A.model({...ex,ask:V*ex.optRho}));
    ok(ex.optRho>A.RHO_MAX-.02&&!n.alt&&!/as a range/.test(n.text)&&n.flat>1.2&&n.flat<1.28&&/every ask from 1\.2\d× value up comes within 1% of value of the cap/.test(n.text),
       `manufacturing $120k, 100% kept: no false range, flat top from ${n.flat} (${n.text})`);
    /* and the converse: at 90% kept the framework example's asks of 1.40-1.50x are within 1%, but there is no second peak */
    const e9={...EXO,ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,theta:.9,lamT:900}, V9=A.model({...e9,ask:1}).V;
    e9.rhoSell=A.bestRatio(e9,0,0); e9.optRho=A.bestRatio(e9,.9,900);
    const n9=A.optNote(e9,V9,A.model({...e9,ask:V9*e9.rhoSell}),A.model({...e9,ask:V9*e9.optRho}));
    ok(!n9.alt&&n9.flat>1.3&&n9.flat<1.42,`framework example at 90% kept: flat top from ${n9.flat}, no range`); }
  const noteAt=(s0,th,lam)=>{ const t={...s0,theta:th,lamT:lam}, V=A.model({...t,ask:1}).V; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,th,lam);
    return {t,o:t.optRho,n:A.optNote(t,V,A.model({...t,ask:V*t.rhoSell}),A.model({...t,ask:V*t.optRho}))}; };
  /* a walk-away flip between ~1.22x and ~1.45x on one 1% step of theta, NEITHER end at the cap (the second peak is not
     assumed to be the cap): the range covers both peaks on both sides of the flip */
  for(const [s0,ths,lam] of [[{ind:"home",rev:4e5,ern:9e4,grw:.06,gm:.5,rec:.3,cc:.16,ret:.82,plt:.40,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,budget:1e5},[.92,.93],750],
                             [{ind:"home",rev:326000,ern:55000,grw:.66,gm:.77,rec:.59,cc:.07,ret:.70,plt:.24,own:.95,mgt:.36,fin:.14,yrs:6,buyers:440},[.94,.95],700]]){
    const out=ths.map(th=>noteAt(s0,th,lam));
    ok(Math.abs(out[1].o-out[0].o)>.2&&out.every(({o,n})=>o<A.RHO_MAX-.02&&n.alt&&Math.min(o,n.alt.m)<1.25&&Math.max(o,n.alt.m)>1.44&&/as a range/.test(n.text)),
       `walk-away flip ${out.map(v=>v.o.toFixed(3)).join(" -> ")} below the cap: the range on both sides`);
    for(const v of out) checkNote(v.t,v.n,`(flip at theta ${v.t.theta})`); }
  /* at the cap with an interior peak more than 1% below it, the note names that peak instead of claiming none, and the
     flat-top ask is rounded up (framework example at 85% kept; auto repair $1.2M/$300k at 90%) */
  { const f=noteAt({...EXO,ind:"medical",rev:6e6,ern:1.45e6},.85,900), a=noteAt({...EXO,ind:"auto",rev:1.2e6,ern:3e5},.9,900);
    for(const [v,pm,lo,hi,fl] of [[f,1.22,1.15,1.25,1.36],[a,1.24,1.04,1.13,1.31]]){ const n=v.n, V=A.model({...v.t,ask:1}).V;
      const U=m=>{ const x=A.model({...v.t,ask:V*m}); return x.EVp+(1-x.PC)*v.t.theta*x.V-v.t.lamT*x.tMean; }, gap=n.peak?(U(v.o)-n.peak.u)/V*100:NaN;
      ok(v.o>A.RHO_MAX-.02&&!n.alt&&n.peak&&Math.abs(n.peak.m-pm)<.015&&gap>lo&&gap<hi&&!/no second peak|rises all the way/.test(n.text)
         &&n.text.includes(`another peak, at ${n.peak.m.toFixed(2)}× value, but to this owner it is worth ${gap.toFixed(2)}% of value less than the cap, beyond a tie`)
         &&n.flat===fl&&U(v.o)-U(fl)<=.01*V&&U(v.o)-U(fl-.01)>.01*V,`${v.t.ind} at ${v.t.theta}: other peak at ${n.peak?n.peak.m.toFixed(3):"none"} ${gap.toFixed(3)}% below, flat from ${n.flat} (${n.text})`);
      checkNote(v.t,n,`(${v.t.ind} at ${v.t.theta})`); } }
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
    ok(near(a25.r.thinF,.7695,1e-4)&&near(a25.r.PC,.5209,1e-4)&&Math.abs(a25.sc-2)<=1,`example at 25 buyers: thinF ${a25.r.thinF.toFixed(4)}, PC ${a25.r.PC.toFixed(4)}, score ${a25.sc} (pinned 0.7695, 0.5209, 2)`);
    ok(Math.abs(a40.sc-31)<=1&&Math.abs(a65.sc-41)<=1&&a65.r.thinF===1&&a50.r.thinF===1,`example at 40 and 65 buyers scores ${a40.sc} and ${a65.sc} (pinned 31, 41 against optimum-priced peers); thinF 1 from the typical 50 up`);
    /* IND.buyers sensitivity: the judgment typical pool the thin-pool factor is measured against */
    const sens=[40,60].map(tb=>{ const B=A.loadWith([["anchor:3.10, buyers:50,","anchor:3.10, buyers:"+tb+","]]); return [at(B,25).sc,at(B,40).sc]; });
    ok(Math.abs(sens[0][1]-41)<=1&&Math.abs(sens[1][1]-25)<=1&&Math.abs(sens[0][0]-10)<=1&&Math.abs(sens[1][0]-1)<=1,
       `IND.buyers sensitivity: example at 40/25 buyers scores ${sens[0][1]}/${sens[0][0]} at a typical pool of 40, ${sens[1][1]}/${sens[1][0]} at 60 (pinned 41/10, 25/1)`);
    /* median businesses at half and three quarters of the typical pool */
    const SE=F.score_effect_at_integration, rng={.5:[99,0],.75:[99,0],1:[99,0]};
    for(const ind of inds) for(const ern of [2e5,1e6,4e6]){ const t=median(ind,ern), V=A.model({...t,ask:1}).V;
      for(const f of [.5,.75,1]){ const s={...t,ask:A.REF_RATIO*V,buyers:Math.max(1,Math.round(t.buyers*f))}, r=A.model(s); r.inputs=s; const sc=A.omniScore(r);
        rng[f][0]=Math.min(rng[f][0],sc); rng[f][1]=Math.max(rng[f][1],sc); } }
    ok(Math.abs(rng[.5][0]-SE.median_half_pool[0])<=2&&Math.abs(rng[.5][1]-SE.median_half_pool[1])<=2&&Math.abs(rng[.75][0]-SE.median_three_quarter_pool[0])<=2&&Math.abs(rng[.75][1]-SE.median_three_quarter_pool[1])<=2,
       `MEDIAN-BUSINESS PIN: half pool ${rng[.5]}, three quarters ${rng[.75]} (stored ${SE.median_half_pool}, ${SE.median_three_quarter_pool})`);
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
  ok(Math.abs(m9-.0055)<.0003&&Math.abs(m0-.0034)<.0003,`interior peak wins by ${(m9*100).toFixed(2)}% of value at $900/day, ${(m0*100).toFixed(2)}% with no delay cost (comment: 0.55%, 0.34%)`);
  ok(margin(A,.772,900)>0&&margin(A,.779,900)<0&&margin(A,.763,0)>0&&margin(A,.769,0)<0,"theta flip near 0.776 at $900/day and 0.766 with no delay cost");
  const S=f=>A.loadWith([["const FAN_S=0.80;","const FAN_S="+f+";"]]);
  ok(margin(S(.93),.75,900)>0&&margin(S(.945),.75,900)<0&&margin(S(.876),.75,0)>0&&margin(S(.889),.75,0)<0,"FAN_S flip near 0.94 at $900/day and 0.88 with no delay cost");
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
       &&/less likely to close for a higher price if it closes/.test(n.text)&&/takes about (a day|\d+ days) longer from start to close/.test(n.text)&&!/less elapsed time|spends/.test(n.text)
       &&n.text.includes("value retained if the process fails"),`#11: default card subtitle (${n.text})`);
    ok(HTML.includes("optCardNote(s,best,rhoSell,uRho).text")&&!HTML.includes("in exchange for ${dProc<0"),"#11: the card uses optCardNote"); }
  /* #14/#18: the lower note prints the time value and the net separately */
  { const {s,V}=prep({theta:0,lamT:4000,rev:8e5,ern:1.5e5,ask:4.5e5}), rS=A.model({...s,ask:V*s.rhoSell}), rK=A.model({...s,ask:V*s.optRho}), n=A.optNote(s,V,rS,rK);
    const tv=s.lamT*(rS.tMean-rK.tMean);
    ok(n.kind==="lower"&&n.text.includes(`worth ${A.money(tv)} at $4,000 a day`)&&n.text.includes(`Net of the proceeds given up, that is worth ${A.money(n.gain)} to this owner`)
       &&tv>n.gain,`#14: lower note: time value ${A.money(tv)}, net ${A.money(n.gain)} (${n.text})`); }
  /* #5/#25: no 2% floor; the equation carries the tail, the size-interpolated base and the thin-pool factor */
  { const V=A.model({...FX,ask:1}).V, p=[28,30,50,100].map(m=>A.model({...FX,ask:V*m}));
    ok(p[0].PC>p[1].PC&&p[1].PC>p[2].PC&&p[2].PC>p[3].PC&&p[1].PC<.02&&p[1].EVp>p[2].EVp,`#5: P_C keeps falling past 28x (${p.map(x=>x.PC.toExponential(2)).join(", ")})`);
    ok(HTML.includes("1-${(1-PEN_MAX).toFixed(2)}\\\\,e^{-k(g-100)}")&&HTML.includes("\\\\tau(n)&=\\\\operatorname{cap}_1")&&HTML.includes("b(V)&=${tp(bB,1)}")
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
    ok(at(.418)>1.45&&at(.428)<1.25&&A.PEN_MAX===.45,"R1-1: the walk-away ask flips to the cap near PEN_MAX 0.423 (text: about 0.42)"); }
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
    ok(B.model(FX).risk.p===A.model(FX).risk.p&&HTML.includes("so the prime level moves no figure"),"R1-7: prime cancels and the Data tab says so"); }
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
     since October 2026) and the peer scales (17 + 2: PEER_SD, the two typed medians and sizeRefs' typed numbers less its
     clamp; the buyer-pool scale and the size centre) */
  { const src=require("fs").readFileSync(require("path").join(__dirname,"..","index.html"),"utf8");
    const sl=(a,b)=>{ const i=src.indexOf(a); return src.slice(i,src.indexOf(b,i)); };
    const mults=t=>(t.match(/(?<![\w.])(\d+\.\d*|\.\d+|\d+)\*/g)||[]).length;
    const numLits=f=>{ const t=String(f).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g,""); return (t.match(/(?<![\w.$])(\d+\.\d*|\.\d+|\d+)(?![\w.])/g)||[]).filter(v=>+v!==0).length-(t.match(/\(1-/g)||[]).length; };
    const cat=sl("out.cats={","const catMean"), z=sl("const z={","const emRaw");
    const nCat=mults(cat)+(cat.match(/-\.\d+\)/g)||[]).length+4, C=A.MODELS.fitted.confidence, nConf=["cut_high","cut_moderate","extrap_x"].filter(k=>typeof C[k]==="number").length;
    const nPeer=Object.keys(A.PEER_SD).length+2+numLits(String(A.sizeRefs).replace(/Math\.max\(ern,1e4\)/,""))-2, nPeerX=(z.match(/\/\.\d+,?\s*$/gm)||[]).length+1;
    ok(nCat===37&&nConf===3&&nPeer===17&&nPeerX===2&&!src.includes('slice("const conf="')&&HTML.includes("+ nBuy + nInt + nDelta + nCat + nConf + nPeer + nPeerX + 11 + 2 + 1")
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
       the worse quality ends, inside the limit), and growing past the limit */
    const wq=A.model({...FX,ind:"rest",rev:12.48e6,ern:12.48e6*A.typMargin("rest",3.36e6),rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.45,plt:.95});
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
  { const lo={...FX,rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.45,plt:.95}, hi={...FX,rec:1,own:.14,mgt:.92,cc:.01,fin:.96,grw:.70,gm:.97,ret:.99,plt:.05};
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
  { const a=A.model({...FX,rec:0,own:.95,mgt:.08,cc:.70,fin:.14,grw:-.25,gm:.12,ret:.45,plt:.95}), b=A.model({...FX,rec:1,own:.14,mgt:.92,cc:.01,fin:.96,grw:.70,gm:.97,ret:.99,plt:.05});
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
       further from its peers' at $300k of SDE, and the restaurant medians moved */
    ok(n===12288&&worst<1e-9&&wq<1e-12&&A.omniScore(r)===7,
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
    const s=prep({...FX,ask:4.7e6,budget:cq-400}), b=A.optimize(s,A.model(s),s.budget,s.lamT,s.theta);
    const s2=prep({...FX,ask:4.7e6,budget:cq+600}), b2=A.optimize(s2,A.model(s2),s2.budget,s2.lamT,s2.theta);
    const bl=b.U.blocked, ru=bl&&A.model(A.applyAll(s,A.model(s),[bl.k],s.optRho)), uBl=bl&&ru.EVp+(1-ru.PC)*s.theta*ru.V-s.lamT*(ru.tMean+A.daysOf(s,[bl.k]))-bl.c;
    ok(!b.U.keys.length&&bl&&bl.k==="qoe"&&bl.c>s.budget&&uBl>b.U.U&&b2.U.keys.includes("qoe")&&!b.allIn
       &&HTML.includes("Do nothing — nothing within the budget clears its cost; ${INTERV.find(i=>i.k===sel.blocked.k).n} would, for ${moneyIn(sel.blocked.c)}"),
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
    ok(Object.keys(G.by_industry).length===15&&!G.by_industry.wash&&IND.wash.gm===.70&&IND.ecom.gm===undefined
       &&G.by_industry.ecom.tier==="listing-level"&&G.by_industry.ecom.gm.every(v=>v===G.by_industry.ecom.gm[0]),"38a: car washes alone keep a hand-set margin; e-commerce's is flat");
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
    ok(good&&IND.saas.grw===.25&&IND.land.ret===F.peer_rec_ret.ret.land.v&&IND.fit.ret===F.peer_rec_ret.ret.fit.v&&!Object.keys(F.peer_rec_ret.rec).length,
       "38b: the fitted cells are written in; software's growth and every recurring share stay hand-set");
    const want=[...Object.keys(F.peer_grw.by_industry).map(k=>k+".grw"),...INDS.map(k=>k+".tail"),...INDS.map(k=>k+".comps"),"land.ret","fit.ret"].sort();
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
  /* 38e. confidence: the fitted chance of landing within 25% of the fitted value */
  { const C=F.confidence;
    /* the fit's own test vectors (a Python port with the console's ncdf): ind, SDE, revenue, z.em, extrapMax -> p, label, sigma */
    const TV=[["home",7e5,3.5e6,0,0,.548252,"High",.776195],["rest",1.5e5,1.2e6,-.5,0,.474165,"Moderate",.928972],
      ["saas",2.5e6,8e6,1,1.5,.471778,"Moderate",.934489],["vet",3e5,1e6,2,0,.407037,"Low",1.105286],["medical",1.45e6,5e6,.1,0,.561768,"High",.752234],
      ["msp",5e4,4e5,-1.5,0,.386356,"Low",1.169986],["dist",2e7,1.3e8,0,11.9,.55152,"Low",.770307],["auto",5.1e6,2e7,0,3,.578304,"High",.724247],
      ["fit",1e5,1.1e5,3.2,1.1,.336469,"Low",1.356324],["land",2e4,1.5e6,-3.2,1.7,.298868,"Low",1.535456]];
    ok(TV.every(([ind,ern,rev,zem,ex,p,l,sg])=>{ const r=A.confidenceOf({ind,ern,rev},{z:{em:zem},extrapMax:ex}); return Math.abs(r.p-p)<2e-6&&r.label===l&&Math.abs(r.sigma-sg)<2e-6; }),
       "38e: the fit's ten test vectors");
    /* second-round review: the fitted 80% band (eq_cs prints fv.point times it), the comparables weight and the note, against
       the same ten vectors (fit/confidence_accuracy.py RESULT test_vectors, 6 significant digits) */
    const TVB=[["home",700000.0,3500000.0,0.0,0.0,0.59313,1.505502,0.946352,"more predictable than three quarters of listed businesses"],["rest",150000.0,1200000.0,-0.5,0.0,0.535179,1.631752,0.980159,"in the middle half of listed businesses"],["saas",2500000.0,8000000.0,1.0,1.5,0.533196,1.636504,0.0,"in the middle half of listed businesses"],["vet",300000.0,1000000.0,2.0,0.0,0.475302,1.790667,0.537037,"less predictable than three quarters of listed businesses"],["medical",1450000.0,5000000.0,0.1,0.0,0.602771,1.486608,0.875622,"more predictable than three quarters of listed businesses"],["msp",50000.0,400000.0,-1.5,0.0,0.455051,1.852787,0.766355,"less predictable than three quarters of listed businesses"],["dist",20000000.0,130000000.0,0.0,11.9,0.595485,1.500837,0.621212,"outside the fitted data"],["auto",5100000.0,20000000.0,0.0,3.0,0.614231,1.464839,0.944444,"more predictable than three quarters of listed businesses"],["fit",100000.0,110000.0,3.2,1.1,0.401422,2.043999,0.882629,"outside the fitted data"],["land",20000.0,1500000.0,-3.2,1.7,0.355835,2.246397,0.959936,"outside the fitted data"]];
    ok(TVB.every(([ind,ern,rev,zem,ex,b0,b1,cp,note])=>{ const r=A.confidenceOf({ind,ern,rev},{z:{em:zem},extrapMax:ex});
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
        const sh=C.K*Math.exp(C.b_size*lx+C.b_em*Math.abs(r.z.em)), sg=Math.sqrt(sh*sh+C.tau2*(1-c.comps)/(C.s_eq*C.s_eq));
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
  { const s={ind:"vet",rev:3878320.238970697,ern:776822.4617297485,grw:0.03709924817085264,gm:0.6877818477153778,rec:0.39787375926971436,
      cc:0.6583209502696991,ret:0.8690899014472961,plt:0.10440324544906616,own:0.72,mgt:0.66,fin:0.45,yrs:6,buyers:530,st:null,franchise:false,
      budget:100000,lamT:3350,theta:0.9155685663223266,ask:3681742.1258855304};
    const r=A.model(s); s.optRho=A.bestRatio(s,s.theta,s.lamT); s.rhoSell=A.bestRatio(s,0,0);
    const nt=A.optNote(s,r.V,A.model({...s,ask:r.V*s.rhoSell}),A.model({...s,ask:r.V*s.optRho})), hit=nt.text.match(/another peak, at [\d.]+× value/);
    ok(!/There is no second peak/.test(nt.text)&&!!hit&&/1\.2\d×/.test(hit[0]),
       `40: MODEL-1 a dip deeper than 0.01% of value makes a real second peak, named in the note (${hit?hit[0]:"none"})`); }
  ok(/1\.87 at \$100-250k of revenue and 1\.90 at \$250-500k/.test(A.MODELS.value.soi_size_wedge.why)&&!/falls monotonically from 1\.90/.test(HTML)
     &&HTML.includes("that band implies 0.468"),"40: MODEL-2/3 the SOI wedge and the BIZCOMPS sigma are described as the tables have them");
  ok(HTML.includes("e^{${T_ELAST.toFixed(2)}\\\\,g}")&&HTML.includes("R(0.08)^{s}=${Math.pow(fanRatio(.08),FAN_S)")
     &&HTML.includes('row("Normalized earnings",S.ern,mny)')&&HTML.includes("raised only where IBBA&rsquo;s size band closes above the ask")
     &&HTML.includes("Math.abs((f-1)*100).toFixed(1)+'% on the fitted value")&&HTML.includes("a 5% higher ask changes expected proceeds by ")
     &&HTML.includes("(s.lamT>0?` Above model value"),"40: D1-D3, D5, D7-D9 the equations, the extrapolation table and the notes say what the model does");
  ok(HTML.includes("money(PHI*b.S)")&&HTML.includes("U=${tp(best.U.PC,1)}")&&HTML.includes("${r.nEng.toFixed(2)}\\\\text{ of }")
     &&HTML.includes(" is at or near the end of its range, so that row is an uneven difference")&&HTML.includes("Left out because "),
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

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
