/* Invariants of the Omni Method model. Run: node tests/model.test.js */
const A=require("./load.js");
let pass=0,fail=0;
const ok=(c,msg)=>{ if(c) pass++; else { fail++; console.log("FAIL:",msg); } };
const near=(a,b,tol)=>Math.abs(a-b)<=tol;

const EX={ind:"medical",rev:10**6.778,ern:10**6.161,ask:10**6.508,grw:.14,gm:.64,rec:.72,cc:.18,
  ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,buyers:65,st:null,franchise:false,
  budget:10**(4+2.778*.36),lamT:900,theta:.75,chan:"broker",rate:10.5};
EX.jobs=Math.max(2,Math.round(EX.rev/150000));
const finiteDeep=(o,seen=new Set())=>{
  if(typeof o==="number") return isFinite(o);
  if(!o||typeof o!=="object"||seen.has(o)) return true; seen.add(o);
  return Object.values(o).every(v=>typeof v==="function"||finiteDeep(v,seen));
};
const median=(ind,ern)=>{
  const I=A.IND[ind],RF=A.sizeRefs(ern),rev=ern/(I.em*RF.emk);
  return {ind,ern,rev,yrs:6,buyers:I.buyers,chan:"broker",rate:10.5,franchise:false,st:null,
    jobs:Math.max(2,Math.round(rev/150000)),rec:I.rec,cc:.16,own:RF.own,mgt:RF.mgt,grw:I.grw,
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
  ok(r.Vreal<=r.inputs.ask*r.askCeil*(1+1e-9),`${ind} rho=${rho}: realised ${r.Vreal} above ask ceiling`);
}

/* 5. expected proceeds rise to one peak and then never rise again */
for(const ind of Object.keys(A.IND)) for(const ern of [1.5e5,6e5,1.5e6,5e6]){
  const b={...EX,ind,ern,rev:ern*4}, V=A.model({...b,ask:1}).V;
  let peaked=false, prev=-Infinity, bad=null;
  for(let rho=.5;rho<=4;rho+=.01){
    const e=A.model({...b,ask:V*rho}).EVp;
    if(e<prev-1e-6) peaked=true; else if(peaked&&e>prev+V*1e-6) bad=rho;
    prev=e;
  }
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

/* 8. expected proceeds are P_C times the MEAN price */
{ const r=A.model(EX);
  ok(near(r.EVp,r.PC*r.Vreal*A.MODELS.value.mean_over_median,1e-6),"EVp = P_C x mean price"); }

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

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
