/* Identities, bounds, units and reconciliations across the Omni Method model API (and the page that shows it).
   Usage: node tests/invariants/identities.js [appRoot=the repository] [--model-only] [--n=<random states>] [--verbose]
   Prints one line per invariant: "PASS <name> cases=<n>" or "FAIL <name> cases=<n> fails=<k> first=<counterexample>".
   Seeded, so every failure reproduces. Model-only part runs in about 1-2 minutes. */
"use strict";
const path=require("path");
const ROOT=path.resolve(process.argv.slice(2).find(a=>!a.startsWith("--"))||path.join(__dirname,"..",".."));
const MODEL_ONLY=process.argv.includes("--model-only");
const NARG=process.argv.find(a=>a.startsWith("--n="));
const N=NARG?+NARG.slice(4):600;
const A=require(path.join(ROOT,"tests","load.js"));
/* the same model with a few internals exported (no behaviour change): refDistAt for the score recount, ncdf/nqnt, pc/pp,
   lerpKnots, the gap CDF, SENS and FIELD_RANGE */
const X=A.loadWith([["function drawStars(r){",
  "MODELS.__x=()=>({refDistAt,lerpKnots,ncdf,nqnt,pc,pp,GAP_CDF,GAP_F,SENS,FIELD_RANGE,MIX_MAX,BUYER_GROUP,BAND_KNOTS,bandInterp,anchorAt});function drawStars(r){"]]);
const XI=X.MODELS.__x();
const M=A.MODELS;

/* ---------------- harness ---------------- */
let seed=20261013; const rnd=()=>{ seed=(seed*16807)%2147483647; return (seed-1)/2147483646; };
const pick=a=>a[Math.floor(rnd()*a.length)];
const logU=(lo,hi)=>Math.exp(Math.log(lo)+rnd()*(Math.log(hi)-Math.log(lo)));
const fin=x=>typeof x==="number"&&isFinite(x);
const REG=new Map();   /* name -> {statement, source, cases, fails, first} */
function inv(name,statement,source){ if(!REG.has(name)) REG.set(name,{name,statement,source,cases:0,fails:0,first:null}); }
const VERBOSE=process.argv.includes("--verbose");
function chk(name,cond,ctx){ const r=REG.get(name); if(!r) throw new Error("unregistered invariant "+name); r.cases++;
  if(!cond){ r.fails++; if(!r.first) r.first=typeof ctx==="function"?ctx():ctx;
    if(VERBOSE&&(r.more=r.more||[]).length<5&&r.fails>1) r.more.push(typeof ctx==="function"?ctx():ctx); } }
const cx=o=>JSON.stringify(o,(k,v)=>typeof v==="number"?+v.toPrecision(6):v);
const rel=(a,b)=>Math.abs(a-b)/Math.max(1e-300,Math.abs(b));

const INDS=Object.keys(A.IND), STS=[null,...Object.keys(M.risk.state_effects)];
const DEF={ind:"medical",rev:6e6,ern:1.45e6,ask:3.24e6,buyers:65,budget:1e5,lamT:900,theta:.75,grw:.14,gm:.64,rec:.72,
  cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,st:null,franchise:false};
/* a random state over the whole reachable input space (rail sliders, selects and typed values), with corners */
function sample(){
  const corner=rnd()<.15;
  const rev=corner?pick([1e4,1e5,2.5e5,1e6,2e8,5e9]):logU(1e4,5e9);
  let ern=rev*(corner?pick([.002,.02,.85,.92]):(.005+rnd()*.915)); ern=Math.max(1e3,Math.min(ern,rev*.92));
  const s={ind:pick(INDS),st:pick(STS),franchise:rnd()<.2,rev,ern,
    grw:rnd()<.1?pick([-.25,.7,-.6,1.5]):-.25+rnd()*.95, gm:rnd()<.1?pick([.12,.97,.02,.5]):.12+rnd()*.85,
    rec:rnd()<.1?pick([0,1]):rnd(), cc:rnd()<.1?pick([.01,.7,.005,.95]):.01+rnd()*.69,
    ret:rnd()<.1?pick([.05,.99,.05]):.05+rnd()*.94, plt:rnd()<.1?pick([.05,.95,.02,.999]):.05+rnd()*.9,
    own:rnd()<.8?pick([.95,.72,.42,.14]):.02+rnd()*.97, mgt:rnd()<.8?pick([.08,.36,.66,.92]):.02+rnd()*.97,
    fin:rnd()<.8?pick([.14,.45,.74,.96]):.02+rnd()*.98,
    yrs:1+Math.floor(rnd()*12), buyers:rnd()<.2?pick([5,600,480,485,40,41,42,50,52,58,59,65]):5*(1+Math.floor(rnd()*120)),
    budget:rnd()<.15?pick([0,5e3,1e9]):rev*.15*rnd(), lamT:rnd()<.2?pick([0,4000]):50*Math.floor(rnd()*81),
    theta:rnd()<.15?pick([0,1]):Math.round(rnd()*100)/100};
  const V=A.model({...s,ask:1}).V;
  const rho=rnd()<.25?pick([.4,.8,1,1.05,1.2,1.5,1.5*(1-1e-6),1.5*(1+1e-6),2,2.5,10,40]):logU(.25,40);
  s.ask=Math.max(1e3,V*rho);
  return s;
}
const STATES=[]; for(let i=0;i<N;i++) STATES.push(sample());
STATES.unshift({...DEF});
const T0=Date.now();

/* =============================== HELPER FUNCTIONS =============================== */
inv("money-format","money(v,dp): '$'+digits+unit with '−' exactly when v<0 (the sign is kept on a figure that rounds to zero: '−$0' for a loss under fifty cents, a convention the stress test kept as immaterial); the shown figure is |v| rounded to the shown unit (k: nearest $1k, M/B: dp decimals, 2 when dp is 0/undefined); non-finite gives '—'",
  "money() comment (index.html FORMATTING: 'dp sets the decimals in millions and billions...'); economics: zero has no sign");
inv("money-monotone","the magnitude money() shows never falls as |v| rises (no rollover at the k/M/B thresholds)","money() thresholds 999.5, 999.5e3, 999.5e6");
{ const vals=[0,-0,1e-9,-1e-9,.3,-.3,.49,-.49,.5,-.5,999.4,999.5,-999.5,1499,1500,999499,999500,1234567,1.995e6,999.4999e6,999.5e6,1e12,-1e12];
  for(let e=-3;e<=13;e+=.01) vals.push(Math.pow(10,e),-Math.pow(10,e));
  const parse=t=>{ const m=t.match(/^(−)?\$(\d+(?:\.\d+)?)([kMB]?)$/); if(!m) return null;
    return {neg:!!m[1],v:+m[2]*({"":1,k:1e3,M:1e6,B:1e9}[m[3]]),u:m[3],dec:(m[2].split(".")[1]||"").length}; };
  for(const v of vals) for(const dp of [undefined,0,1,2]){
    const t=A.money(v,dp), p=parse(t), a=Math.abs(v);
    let ok=!!p;
    if(ok){ const unit={"":1,k:1e3,M:1e6,B:1e9}[p.u], want=p.u==="M"||p.u==="B"?((dp===undefined||dp===0)?2:dp):0;
      const half=.5*unit*Math.pow(10,-p.dec);
      ok=p.dec===want&&Math.abs(p.v-a)<=half*(1+1e-9)&&(p.neg===(v<0)); }
    chk("money-format",ok,()=>cx({v,dp,shown:t}));
  }
  for(const f of [Infinity,-Infinity,NaN]) chk("money-format",A.money(f)==="—",()=>cx({v:String(f),shown:A.money(f)}));
  let prev=-1, pv=null; for(let e=-3;e<=13;e+=.0005){ const v=Math.pow(10,e), p=parse(A.money(v)); chk("money-monotone",p&&p.v>=prev,()=>cx({v,shown:A.money(v),prev:pv})); if(p){prev=p.v; pv=A.money(v);} }
}

inv("buyerMix-shares","buyerMix(v): individual, strategic and financial shares each in (0,1), summing to 1, continuous in v; MIX_MAX is each share's maximum over $100k-$50M to 1e-4 (it is read off a 201-point grid that can miss a knot by ~1e-5; sizeFit is min(1, share/MIX_MAX), so the excess is clipped)",
  "buyerMix() and MIX_MAX comments (IBBA buyer-type mix, 'each group's share relative to the most it reaches')");
{ let prev=null;
  for(let e=0;e<=12;e+=.001){ const v=Math.pow(10,e), g=A.buyerMix(v), s=g.individual+g.strategic+g.financial;
    chk("buyerMix-shares",[g.individual,g.strategic,g.financial].every(x=>x>0&&x<1)&&Math.abs(s-1)<1e-12&&(!prev||Math.abs(g.strategic-prev.strategic)<.01&&Math.abs(g.financial-prev.financial)<.01),()=>cx({v,g}));
    if(v>=1e5&&v<=5e7) for(const k of ["individual","strategic","financial"]) chk("buyerMix-shares",g[k]<=XI.MIX_MAX[k]*(1+1e-4),()=>cx({v,k,g:g[k],max:XI.MIX_MAX[k]}));
    prev=g; } }

inv("sbaRate-knots","sbaRate(price) = prime + the fitted spread at each knot (loan = 85% of price), flat beyond the outer knots, continuous, non-increasing in price, finite for price <= 0",
  "sbaRate() comment and MODELS.fitted.sba_rate (spread_knots by ln loan)");
{ const R=M.fitted.sba_rate, K=R.spread_knots;
  for(const k of K){ const price=Math.exp(k[0])/.85; chk("sbaRate-knots",Math.abs(A.sbaRate(price)-(R.prime+k[1]))<1e-9,()=>cx({price,rate:A.sbaRate(price),want:R.prime+k[1]})); }
  chk("sbaRate-knots",A.sbaRate(1)===R.prime+K[0][1]&&A.sbaRate(1e12)===R.prime+K[K.length-1][1]&&fin(A.sbaRate(0))&&fin(A.sbaRate(-5)),()=>cx({lo:A.sbaRate(1),hi:A.sbaRate(1e12),z:A.sbaRate(0)}));
  let prev=null; for(let e=3;e<=10;e+=.0005){ const p=Math.pow(10,e), r=A.sbaRate(p); chk("sbaRate-knots",prev===null||(r<=prev+1e-12&&Math.abs(r-prev)<.02),()=>cx({p,r,prev})); prev=r; } }

inv("jobs-knots-sorted","every Census knot table as jobsFor and gmSalary read it (jobsKnots pools size classes whose receipts per firm fall out of order; stress test S-2) has strictly increasing ln-revenue x, as lerpKnots requires, and a non-decreasing employment rank",
  "lerpKnots() comment: 'K = [[x,y],...] sorted; flat beyond'");
for(const k of INDS){ const K=A.jobsKnots(k);
  for(let i=1;i<K.length;i++) chk("jobs-knots-sorted",K[i][0]>K[i-1][0]&&K[i][3]>=K[i-1][3],()=>cx({ind:k,naics:M.fitted.jobs.by_industry[k].naics,i,x_prev:K[i-1][0],x:K[i][0],rev_prev:Math.round(Math.exp(K[i-1][0])),rev:Math.round(Math.exp(K[i][0]))})); }

inv("gmSalary-continuous","gmSalary is continuous in revenue: a 0.05% revenue step never moves the GM salary by more than 0.1% (it reads the employment-share rank by lerpKnots), and it never falls as revenue rises",
  "gmSalary() comment (BLS percentiles read at the firm's Census size rank) + the console's no-cliff rule (fitTiming/bandInterp comments: a $1 input change must not jump a figure)");
for(const k of INDS){ let prev=null, pr=null;
  for(let lr=Math.log(1e4);lr<=Math.log(5e9);lr+=.0005){ const rev=Math.exp(lr), g=A.gmSalary({ind:k,rev});
    chk("gmSalary-continuous",prev===null||(g>=prev-1e-9&&Math.abs(g/prev-1)<1e-3),()=>cx({ind:k,rev_from:Math.round(pr),rev_to:Math.round(rev),salary_from:Math.round(prev),salary_to:Math.round(g)})); prev=g; pr=rev; } }

inv("jobsFor-monotone","jobsFor(rev,ind) is an integer >= 1 and grows with revenue over every tenfold step ('the head count follows revenue ... keeps growing with revenue'); Census receipts per employee vary by size class, so it can dip between neighbouring classes, and it reaches no figure (stress test)",
  "jobsFor() comment ('paid employees for this revenue'); Data tab Model V staffing row ('the head count follows revenue ... the head count keeps growing with revenue')");
for(const k of INDS){ let prev=0, pr=0;
  for(let lr=Math.log(1e4);lr<=Math.log(5e9);lr+=.002){ const rev=Math.exp(lr), j=A.jobsFor(rev,k);
    chk("jobsFor-monotone",Number.isInteger(j)&&j>=1&&(rev>5e8||A.jobsFor(10*rev,k)>=j),()=>cx({ind:k,rev_from:Math.round(pr),jobs_from:prev,rev_to:Math.round(rev),jobs_to:j})); prev=j; pr=rev; } }

inv("typMargin-props","typMargin(ind,ern) is in (0,1), continuous, flat outside the fitted SDE range and non-decreasing in earnings (fitted slope > 0)",
  "typMargin() comment and MODELS.fitted.sde_margin (slope, sde_range)");
{ const SM=M.fitted.sde_margin;
  for(const k of [...INDS,"zzz"]){ let prev=null;
    for(let e=2;e<=10;e+=.002){ const ern=Math.pow(10,e), m=A.typMargin(k,ern);
      chk("typMargin-props",m>0&&m<1&&(prev===null||(m>=prev-1e-15&&Math.abs(m/prev-1)<1e-3)),()=>cx({ind:k,ern,m,prev})); prev=m; }
    chk("typMargin-props",A.typMargin(k,1)===A.typMargin(k,Math.exp(SM.sde_range[0])*.5)&&A.typMargin(k,1e12)===A.typMargin(k,Math.exp(SM.sde_range[1])*2),()=>cx({ind:k})); } }

inv("timeMult-props","timeMult(ask,V) = 1 at or below value and for invalid inputs, >= 1 above, continuous with a continuous slope at value and at T_SMOOTH, and exactly exp(T_ELAST(ln(ask/V) - T_SMOOTH/2)) beyond T_SMOOTH",
  "timeMult() comment (Huber-rounded log-linear stretch, T_ELAST/T_SMOOTH)");
{ const tm=A.timeMult, E=A.T_ELAST, S=A.T_SMOOTH;
  for(const [a,v] of [[0,1],[1,0],[-1,1],[NaN,1],[1,NaN],[.5,1],[1,1]]) chk("timeMult-props",tm(a,v)===1,()=>cx({a,v,t:tm(a,v)}));
  for(let x=-1;x<=5;x+=.001){ const t=tm(Math.exp(x)*1e6,1e6); const want=x<=0?1:x<S?Math.exp(E*x*x/(2*S)):Math.exp(E*(x-S/2));
    chk("timeMult-props",t>=1&&Math.abs(t/want-1)<1e-12,()=>cx({x,t,want})); }
  for(const x0 of [1e-9,S]){ const h=1e-7, f=x=>Math.log(tm(Math.exp(x)*1e6,1e6)), dl=(f(x0)-f(x0-h))/h, dr=(f(x0+h)-f(x0))/h;
    chk("timeMult-props",Math.abs(dl-dr)<1e-5,()=>cx({x0,dl,dr})); } }

inv("gapPenalty-props","gapPenalty(g%) is 0 for g <= 0, in [0,1), non-decreasing, continuous (including the join at the open bucket's knot, 200% over value), equals PEN_MAX x the cumulative price-killed share at each Pepperdine bucket edge (read as shares of the ask), and tends to 1",
  "gapPenalty()/GAP_CDF/GAP_TAIL_K comments; eq_p");
{ const G=XI.GAP_CDF; let prev=0;
  for(let g=-50;g<=3000;g+=.05){ const p=A.gapPenalty(g);
    chk("gapPenalty-props",p>=0&&p<1&&p>=prev-1e-15&&(g<=0?p===0:true)&&Math.abs(p-prev)<.01,()=>cx({g,p,prev})); prev=p; }
  for(let i=0;i<G.g.length;i++) chk("gapPenalty-props",Math.abs(A.gapPenalty(G.g[i])-(G.g[i]>0?A.PEN_MAX*G.f[i]:0))<1e-12,()=>cx({g:G.g[i],p:A.gapPenalty(G.g[i]),want:A.PEN_MAX*G.f[i]}));
  chk("gapPenalty-props",A.gapPenalty(1e5)>.999,()=>cx({p:A.gapPenalty(1e5)})); }

inv("softMin-props","softMin(x,y) for x,y >= 1: never above min(x,y), never below min(x,y) x 2^-0.012, symmetric, non-decreasing in each argument, scale-equivariant",
  "softMin() comment ('smooth minimum in logs: within K of the kink it rounds the corner, elsewhere it is min()')");
for(let i=0;i<4000;i++){ const x=logU(1,1e10), y=rnd()<.3?x*(1+(rnd()-.5)*.05):logU(1,1e10), m=Math.min(x,y), s=A.softMin(x,y), k=logU(1,100);
  chk("softMin-props",s<=m*(1+1e-12)&&s>=m*Math.pow(2,-.012)*(1-1e-12)&&Math.abs(A.softMin(y,x)/s-1)<1e-12&&A.softMin(x*1.01,y)>=s*(1-1e-12)&&Math.abs(A.softMin(x*k,y*k)/(s*k)-1)<1e-9,()=>cx({x,y,s,m})); }

inv("capOne-props","capOne(x): x itself up to 1-THIN_W, exactly 1 from 1 up, monotone and never above 1 or below x in between",
  "capOne() comment");
{ let prev=-1; for(let x=-.5;x<=2;x+=1e-4){ const c=A.capOne(x);
    chk("capOne-props",c<=1&&c>=prev-1e-15&&(x>=1?c===1:x<=1-A.THIN_W?c===x:c>=x-1e-15),()=>cx({x,c})); prev=c; } }

inv("fan-props","fanRatio is increasing in p with fanRatio(.5) = 1 and equals the measured fan quantile at each knot; fanNodes() returns 48 strictly increasing slice means with the median between nodes 24 and 25 and their mean equal to the integral of fanRatio(p)^FAN_S",
  "FAN/fanRatio/fanNodes comments ('Each node is the exact MEAN of its slice ... median kept')");
{ const Q=M.value.fan_quantiles; let prev=0;
  for(let p=1e-5;p<1;p+=1e-4){ const r=A.fanRatio(p); chk("fan-props",r>prev,()=>cx({p,r,prev})); prev=r; }
  chk("fan-props",Math.abs(A.fanRatio(.5)-1)<1e-12,()=>cx({r:A.fanRatio(.5)}));
  for(const k in Q){ const p=+k.slice(1)/100; chk("fan-props",Math.abs(A.fanRatio(p)/Q[k]-1)<1e-6,()=>cx({k,r:A.fanRatio(p),q:Q[k]})); }
  const nd=A.fanNodes(); chk("fan-props",nd.length===48&&nd.every((v,i)=>i===0||v>nd[i-1])&&nd[23]<1&&nd[24]>1,()=>cx({n:nd.length,n23:nd[23],n24:nd[24]}));
  let S=0; const K=200000; for(let j=0;j<K;j++) S+=Math.pow(A.fanRatio((j+.5)/K),A.FAN_S); S/=K;
  const mean=nd.reduce((a,b)=>a+b,0)/48; chk("fan-props",Math.abs(mean/S-1)<5e-4,()=>cx({nodeMean:mean,integral:S})); }

inv("wedge-props","sdeEbitdaWedge(naics2,rev) is null or in [1.02,2.75], and continuous in revenue",
  "sdeEbitdaWedge() comment (clamp 1.02-2.75; SOI size profile interpolated in ln revenue)");
for(const n2 of [...new Set(INDS.map(A.naicsFor)),"99"]){ let prev=null;
  for(let e=3;e<=10;e+=.002){ const w=A.sdeEbitdaWedge(n2,Math.pow(10,e));
    chk("wedge-props",w===null||(w>=1.02-1e-12&&w<=2.75+1e-12&&(prev===null||Math.abs(w/prev-1)<.01)),()=>cx({n2,rev:Math.pow(10,e),w,prev})); prev=w; } }

inv("naicsFor-coverage","every industry key maps to a NAICS-2 sector that has both a fitted value effect and a fitted risk effect; an unknown key falls back to '81'",
  "IND2NAICS comment ('Every key in IND must appear here')");
for(const k of INDS){ const n=A.naicsFor(k); chk("naicsFor-coverage",M.value.industry_effects[n]!==undefined&&M.risk.industry_effects[n]!==undefined,()=>cx({k,n})); }
chk("naicsFor-coverage",A.naicsFor("nope")==="81",()=>cx({n:A.naicsFor("nope")}));

inv("ncdf-nqnt","ncdf and nqnt are inverse to 1e-6 over (1e-6, 1-1e-6), ncdf(0) = 0.5 to 2e-7 (the Abramowitz-Stegun constants are carried to 7 digits, which leaves ncdf(0) at 0.49999985), ncdf monotone",
  "ncdf (Abramowitz-Stegun) and nqnt (Acklam) comments");
{ let prev=0; for(let p=1e-6;p<1-1e-6;p+=1e-4){ const z=XI.nqnt(p), q=XI.ncdf(z); chk("ncdf-nqnt",Math.abs(q-p)<1e-6&&q>=prev,()=>cx({p,z,q})); prev=q; }
  chk("ncdf-nqnt",Math.abs(XI.ncdf(0)-.5)<2e-7,()=>cx({c:XI.ncdf(0)})); }

inv("costOf-daysOf","costOf(s,keys) is the sum of each action's cost (>= 0, additive over disjoint sets); daysOf(s,keys) is the longest action's days (0 for none): actions run in parallel",
  "optimize()/interventionTable() bookkeeping; tests/model.test.js #11");
for(let i=0;i<300;i++){ const s=STATES[i%STATES.length], ks=A.INTERV.map(x=>x.k).filter(()=>rnd()<.5), a=ks.filter((_,j)=>j%2===0), b=ks.filter((_,j)=>j%2===1);
  chk("costOf-daysOf",A.costOf(s,ks)>=0&&Math.abs(A.costOf(s,ks)-A.costOf(s,a)-A.costOf(s,b))<1e-6&&A.daysOf(s,ks)===(ks.length?Math.max(...ks.map(k=>A.INTERV.find(x=>x.k===k).days)):0),()=>cx({ks})); }

console.error(`helpers done ${(Date.now()-T0)/1000}s`);

/* =============================== MODEL OUTPUTS =============================== */
inv("probabilities-in-unit","every probability the model returns is in [0,1]: P_C, the judgment P_C and its parts, the gap penalty, the size-ramp share, thinF, the ceiling share, the cash share, the quality percentile, F(t) and t90/t180/t365, every risk horizon, expected loss and severity, the observed band rate, each buyer's engagement, close rate and size fit, every z percentile, confidence and the scale percentile",
  "definitions in model(), fitClose(), fitRisk() and the buyer block");
inv("money-fields-positive","every money figure is finite and of the right sign: value, base value, prices (median, mean, uncapped median, every quantile), expected proceeds, cash and deferred parts, ceiling, effective ask, judgment value, fitted point and interval, risk loan > 0; buyer V_j, P_j > 0; buyer EV, synergy, strategic premium, synergy pool >= 0",
  "economics: a price, value or loan is positive; an expectation of non-negative amounts is non-negative");
inv("time-fields","time to close: tMed, tMean, the band median (days and months) and the LOI leg are positive and finite, the LOI-to-close leg is shorter than listing-to-close, tMult >= 1, beta > 1, t90 <= t180 <= t365 and tQ(.25) < tMed < tQ(.75)",
  "Model III comments (band medians; LOI leg 'about 40% of it'); log-logistic definitions");
inv("risk-loan-within-price","the SBA note behind the survival risk is 85% of the model value held inside the 7(a) range [$25k, $5M] (below about $29.4k of value the documented $25k floor sets it; the stress test kept the floor)",
  "fitRisk()/Model V comment ('The note is 85% of the price ... held inside the 7(a) range'); Data tab Model V table; economics");
inv("cash-split","EVcash = EVp x cashShare and deferred = EVp - EVcash, both >= 0 (the realisation panel's 'Cash at close' and 'Deferred' rows add to the expected proceeds)",
  "model() cash-at-close comment; realisation panel rows");
inv("value-identities","V = M x SDE; V = rawPoint x calib x qFactor (eq_vs); Vbase = fitted point; qFactor in [QB.lo, QB.hi] and monotone in qPct with qFactor(0.5)=1; qPct = ncdf(clamp(qz,-3,3)); ebitdaMult = fitted multiple x wedge",
  "model() quality-positioning comments; eq_vs; fitValue()");
inv("gap-and-ratio","priceRatio = ask/V; fc.gap = 100 (ask/V - 1) (eq_ps 'g'); askEff = softMin(ask, 1.5 V) <= min(ask, 1.5V); ceil = askEff x max(1, pctAskSize)",
  "model() §5-7 and §8b comments; eq_p, eq_a");
inv("PC-decomposition","P_C = b(V) x (1 - pi(g)) x tau(n) as eq_p prints it: b = broker + (intermediated - broker) u, u = clamp(ln(Vbase/$1M)/ln 5, 0, 1), pi = gapPenalty(g), tau = thinF; and P_C <= 0.95",
  "eq_p/eq_ps; fitClose() comment");
inv("pool-identities","nPool/nEngRef = buyers / typical pool; nEng = buyers x mean(PE) x ENG_SHARE; thinF = capOne(Poisson ratio); compPrem in [-0.08, 0.14]",
  "§20 competition comments");
inv("buyer-structure","out.best is the buyer with the largest EV; out.top has the largest V_j among buyers with size fit >= .05; stratPrem = max(0, top.V_j - V); PHI x S_j <= 40% of V (eq_b: 'a buyer pays away at most 40% of value'); P_j = softMin(V_j, ceiling)",
  "model() buyer block comments; eq_b");
inv("scenario-quantiles","the scenario bands are the stated percentiles of the realised price: bear = [q.08,q.22], base = [q.38,q.62], bull = [q.80,q.94], range = [q.30,q.70], ordered; the capped median never exceeds the uncapped median",
  "model() §23 (out.scen, out.range); scenario captions '8th-22nd percentile of closings' etc.");
inv("askBinds-vs-capShare","the ask binds at the median (askBinds: uncapped median above the ceiling) exactly when more than half of closings land at the ceiling (capShare > 0.5): both read the same log-linear interpolation of the slices",
  "model() comments on capShare ('read log-linearly between slice centres') and askBinds ('the ceiling binds at the median'); the realisation row 'most closings land at the ceiling' (capShare >= .5) and #sensflat (askBinds)");
inv("risk-labels","risk tier matches rel's documented cut-offs; the observed size band matches the loan; lgd = expLoss/pTerm; rel = pTerm/base",
  "fitRisk() return block");
inv("cats-conf","catMean is the mean of the nine category scores; conf in (0,1) with the High/Moderate/Low label at the fitted quartile cut-offs (.49/.43), Low outside the fitted data",
  "model() §21/§24");
for(const s of STATES){
  const r=A.model(s), k=r.risk, I=A.IND[s.ind];
  const probs={PC:r.PC,PCjudg:r.PCjudg,Pq:r.Pq,gate:r.gate,fcp:r.fc.p,pen:r.fc.pen,chan:r.fc.chanShare,base:r.fc.base,thinF:r.thinF,capShare:r.capShare,
    cashShare:r.cashShare,qPct:r.qPct,t90:r.t90,t180:r.t180,t365:r.t365,p:k.p,p5:k.p5,p8:k.p8,pTerm:k.pTerm,expLoss:k.expLoss,lgd:k.lgd,
    empBand:k.empBand===null?0:k.empBand,conf:r.conf,mpct:r.mpct,F0:r.F(0),F1e4:r.F(1e4)};
  for(const b of r.buyers){ probs["PE_"+b.k]=b.PE; probs["PCj_"+b.k]=b.PCj; probs["fit_"+b.k]=b.sizeFit; }
  for(const z in r.pctile) probs["pct_"+z]=r.pctile[z];
  const badP=Object.entries(probs).filter(([n,v])=>!(fin(v)&&v>=0&&v<=1));
  chk("probabilities-in-unit",!badP.length,()=>cx({s,bad:badP}));
  const pos={V:r.V,Vbase:r.Vbase,Vreal:r.Vreal,Vmean:r.Vmean,VrealFree:r.VrealFree,EVp:r.EVp,EVcash:r.EVcash,ceil:r.ceil,askEff:r.askEff,Vjudg:r.Vjudg,
    fvp:r.fv.point,p10:r.fv.p10,p90:r.fv.p90,loan:k.loan,q02:r.q(.02),q98:r.q(.98)};
  const nn={deferred:r.deferred,stratPrem:r.stratPrem,synE:r.synE};
  for(const b of r.buyers){ pos["Vj_"+b.k]=b.Vj; pos["Pj_"+b.k]=b.Pj; nn["EV_"+b.k]=b.EV; nn["S_"+b.k]=b.S; }
  const badM=[...Object.entries(pos).filter(([n,v])=>!(fin(v)&&v>0)),...Object.entries(nn).filter(([n,v])=>!(fin(v)&&v>=-1e-9*r.V))];
  chk("money-fields-positive",!badM.length,()=>cx({s,bad:badM}));
  chk("time-fields",[r.tMed,r.tMean,r.ft.days,r.ft.months,r.ft.loi].every(x=>fin(x)&&x>0)&&r.ft.loi<r.ft.months&&r.tMult>=1&&r.betaT>1
    &&r.t90<=r.t180&&r.t180<=r.t365&&r.tQ(.25)<r.tMed&&r.tMed<r.tQ(.75),()=>cx({s,tMed:r.tMed,loi:r.ft.loi,months:r.ft.months}));
  chk("risk-loan-within-price",Math.abs(k.loan-Math.min(M.risk.loan_range[1],Math.max(M.risk.loan_range[0],M.risk.loan_share*Math.max(r.V,1))))<=1e-9*k.loan,()=>cx({ind:s.ind,ern:s.ern,rev:s.rev,V:r.V,loan:k.loan,loanOverV:k.loan/r.V,p:k.p}));
  chk("cash-split",Math.abs(r.EVcash-r.EVp*r.cashShare)<=1e-9*r.EVp&&Math.abs(r.EVcash+r.deferred-r.EVp)<=1e-9*r.EVp&&r.deferred>=-1e-9,()=>cx({s}));
  { const QB=M.value.quality_band, qf=r.qPct<=.5?Math.exp(Math.log(QB.lo)*(1-r.qPct*2)):Math.exp(Math.log(QB.hi)*((r.qPct-.5)*2));
    chk("value-identities",rel(r.V,r.M*Math.max(s.ern,1))<1e-12&&rel(r.V,r.fv.rawPoint*r.fv.calib*r.qFactor)<1e-12&&r.Vbase===r.fv.point
      &&r.qFactor>=QB.lo-1e-12&&r.qFactor<=QB.hi+1e-12&&rel(r.qFactor,qf)<1e-12&&Math.abs(r.qPct-XI.ncdf(Math.max(-3,Math.min(3,r.qz))))<1e-12
      &&(r.fv.wedge?rel(r.fv.ebitdaMult,r.fv.mult*r.fv.wedge)<1e-12:r.fv.ebitdaMult===null),()=>cx({s,V:r.V,M:r.M})); }
  chk("gap-and-ratio",rel(r.priceRatio,s.ask/r.V)<1e-12&&Math.abs(r.fc.gap-100*(s.ask/r.V-1))<1e-9*Math.max(1,Math.abs(r.fc.gap))
    &&r.askEff<=Math.min(s.ask,1.5*r.V)*(1+1e-12)&&rel(r.ceil,r.askEff*Math.max(1,r.ft.pctAskSize))<1e-12,()=>cx({s,gap:r.fc.gap,ratio:r.priceRatio}));
  { const CP=M.close_and_timing.close_probability, bB=CP.broker_listing_base_recent, bI=CP.intermediated_base_recent,
      u=Math.max(0,Math.min(1,Math.log(r.Vbase/1e6)/Math.log(5))), b=bB+(bI-bB)*u, pc=b*(1-A.gapPenalty(100*(s.ask/r.V-1)))*r.thinF;
    chk("PC-decomposition",Math.abs(r.PC-Math.min(.95,pc))<1e-12&&Math.abs(r.fc.base-b)<1e-12&&Math.abs(r.fc.chanShare-u)<1e-12&&r.PC<=.95,()=>cx({s,PC:r.PC,want:pc,base:r.fc.base,b})); }
  { const avg=r.buyers.reduce((a,b)=>a+b.PE,0)/r.buyers.length, typ=I.buyers||50;
    chk("pool-identities",rel(r.nPool/r.nEngRef,s.buyers/typ)<1e-12&&rel(r.nEng,s.buyers*avg*A.ENG_SHARE)<1e-12||(r.nEng===0&&avg===0),()=>cx({s,nPool:r.nPool,nEngRef:r.nEngRef}));
    chk("pool-identities",Math.abs(r.thinF-A.capOne((1-Math.exp(-r.nPool))/Math.max(1e-9,1-Math.exp(-r.nEngRef))))<1e-15&&r.compPrem>=-.08&&r.compPrem<=.14,()=>cx({s,thinF:r.thinF})); }
  { const best=r.buyers.reduce((a,b)=>b.EV>a.EV?b:a), look=r.buyers.filter(b=>b.sizeFit>=.05), top=(look.length?look:r.buyers).reduce((a,b)=>b.Vj>a.Vj?b:a);
    chk("buyer-structure",r.best.EV===best.EV&&r.top.Vj===top.Vj&&Math.abs(r.stratPrem-Math.max(0,r.top.Vj-r.V))<1e-9*r.V
      &&r.buyers.every(b=>A.PHI*b.S<=.40*r.V*(1+1e-9)&&Math.abs(b.Pj-A.softMin(b.Vj,r.ceil))<=1e-12*b.Pj),()=>cx({s,best:r.best.k,top:r.top.k})); }
  { const q=r.q, S=r.scen;
    chk("scenario-quantiles",S.bear[0]===q(.08)&&S.bear[1]===q(.22)&&S.base[0]===q(.38)&&S.base[1]===q(.62)&&S.bull[0]===q(.80)&&S.bull[1]===q(.94)
      &&r.range[0]===q(.30)&&r.range[1]===q(.70)&&S.bear[1]<=S.base[0]*(1+1e-12)&&S.base[1]<=S.bull[0]*(1+1e-12)&&r.Vreal<=r.VrealFree*(1+1e-12),()=>cx({s})); }
  chk("askBinds-vs-capShare",r.askBinds===(r.capShare>.5)||Math.abs(r.capShare-.5)<1e-9,()=>cx({s,askBinds:r.askBinds,capShare:r.capShare,VrealFree:r.VrealFree,ceil:r.ceil}));
  { const tier=k.rel<.75?"low":k.rel<.95?"below average":k.rel<1.25?"average":k.rel<1.75?"elevated":"high",
      L=k.loan, band=L<250e3?"<250K":L<500e3?"250-500K":L<1e6?"500K-1M":L<2e6?"1-2M":"2-5M";
    chk("risk-labels",k.tier===tier&&k.empBandKey===band&&rel(k.lgd,k.expLoss/k.pTerm)<1e-12&&rel(k.rel,k.pTerm/k.base)<1e-12
      &&k.loan===Math.max(M.risk.loan_range[0],Math.min(M.risk.loan_range[1],M.risk.loan_share*r.V)),()=>cx({s,tier:k.tier,rel:k.rel})); }
  { const cm=Object.values(r.cats).reduce((a,b)=>a+b,0)/9;
    chk("cats-conf",Math.abs(r.catMean-cm)<1e-12&&r.conf>0&&r.conf<1&&r.confLabel===(r.confOutside?"Low":r.conf>=A.MODELS.fitted.confidence.cut_high?"High":r.conf>=A.MODELS.fitted.confidence.cut_moderate?"Moderate":"Low"),()=>cx({s})); }
}
console.error(`model outputs done ${(Date.now()-T0)/1000}s`);

/* =============================== SENSITIVITY =============================== */
inv("sens-quality-diff","each quality row of sensitivity() is the difference it describes: (y(x+h) - y(x-h)) over the clamped span, scaled to one peer sd (2h), sign-flipped for the inverted levers, for y = V, expected proceeds and P_C; 'oneSided' exactly when the span is not 2h; 'pinned' exactly when there is no span",
  "sensitivity() comments; eq_d ('reported = dy/dx x sigma_i')");
inv("sens-step-rows","the ask row is y(0.95 ask) - y(ask) and the buyer row y(1.25 n) - y(n) (or y(n) - y(n/1.25) flagged 'back' when 1.25 n > 600), for y = V, expected proceeds and P_C; both rows have dV = 0 (neither moves what the business supports)",
  "sensitivity() comment (AUDIT_FINDINGS R5-2); eq_d second line; Sensitivity lede ('The ask and the buyer pool cannot change what a business supports')");
inv("sens-units","each quality row's step 2h equals the peer sd its z-score uses in model() and the '(NN pts)' its unit label prints",
  "SENS comment ('Every quality lever moves by ONE PEER STANDARD DEVIATION (the same sd the z-scores use)'); unit labels");
{ const SD={own:.25,mgt:.28,rec:.28,cc:.18,fin:.28,grw:.16,gm:.13,ret:.13,plt:.22};   /* cc and grw measured since the third round */
  for(const v of XI.SENS){ if(v.h===null) continue; const m=v.unit.match(/\((\d+) pts\)/);
    chk("sens-units",Math.abs(2*v.h-SD[v.k])<1e-12&&m&&+m[1]===Math.round(200*v.h),()=>cx({k:v.k,h:v.h,unit:v.unit,sd:SD[v.k]})); } }
for(let i=0;i<Math.min(STATES.length,300);i++){ const s=STATES[i], sn=A.sensitivity(s), r0=A.model(s);
  for(const v of sn){ const D=XI.SENS.find(x=>x.k===v.k);
    if(v.k==="ask"||v.k==="buyers"){
      let s1={...s}, sg=1, back=false;
      if(v.k==="ask") s1.ask=s.ask*.95; else if(s.buyers*1.25<=600) s1.buyers=s.buyers*1.25; else { back=true; sg=-1; s1.buyers=s.buyers/1.25; }
      const r1=A.model(s1);
      chk("sens-step-rows",Math.abs(v.dE-sg*(r1.EVp-r0.EVp))<=1e-9*Math.max(1,r0.EVp)&&Math.abs(v.dP-sg*(r1.PC-r0.PC))<1e-12&&v.dV===0&&!!v.back===back,()=>cx({s,k:v.k,dE:v.dE,want:sg*(r1.EVp-r0.EVp),dV:v.dV}));
      continue; }
    const lo=D.lo, hi=D.hi, xp=Math.max(lo,Math.min(hi,s[v.k]+D.h)), xm=Math.max(lo,Math.min(hi,s[v.k]-D.h)), span=xp-xm;
    if(Math.abs(span)<1e-9){ chk("sens-quality-diff",v.pinned===true&&v.dV===0&&v.dE===0,()=>cx({s,k:v.k})); continue; }
    const rp=A.model({...s,[v.k]:xp}), rm=A.model({...s,[v.k]:xm}), f=(D.inv?-1:1)*2*D.h/span;
    const want={dV:(rp.V-rm.V)*f,dE:(rp.EVp-rm.EVp)*f,dP:(rp.PC-rm.PC)*f};
    chk("sens-quality-diff",Math.abs(v.dV-want.dV)<=1e-9*Math.max(1,r0.V)&&Math.abs(v.dE-want.dE)<=1e-9*Math.max(1,r0.EVp)&&Math.abs(v.dP-want.dP)<1e-12
      &&v.oneSided===(Math.abs(span-2*D.h)>1e-9)&&!v.pinned,()=>cx({s,k:v.k,got:{dV:v.dV,dE:v.dE,dP:v.dP},want,span}));
  } }
console.error(`sensitivity done ${(Date.now()-T0)/1000}s`);

/* =============================== INTERVENTIONS AND OPTIMISER =============================== */
inv("applyAll-ranges","applyAll keeps every field it changes inside FIELD_RANGE, earnings at or below 92% of revenue, buyers an integer in [5,600], and reprices to exactly ratio x the new value",
  "applyAll() comments; FIELD_RANGE");
inv("interv-columns","interventionTable rows: cost = the action's cost (costOf of that one action), ROI = (dE - cost)/cost (null exactly when the action is free), net = dE - cost, Net days = execution days + dT; rows sorted by net, descending",
  "interventionTable() comments; intbl columns; eq_r/eq_rs");
inv("interv-recompute","each row's dV, dE, dP and dT recomputed through applyAll + model on the documented bases: reprice against today, every other row as {reprice, k} against {reprice}; dT on the MEAN time to close",
  "interventionTable() comments; intbl note ('measured on top of a free reprice'); AUDIT_FINDINGS R1-13");
inv("interv-vs-optimizer","the table and the optimiser agree on each single change: the proceeds optimiser's net for the programme {reprice, k} equals EVp({reprice}) + the table's net for k",
  "optimize() and interventionTable() compose actions the same way ('which is also how the optimiser composes them')");
inv("interv-netdays-vs-optimizer","the table's Net days is the change's own execution days plus the change in mean time to close over its baseline; against the optimiser's 'Expected days' (programme execution days + mean time to close) that is ExpectedDays({reprice,k}) - ExpectedDays({reprice}) + 14 for every row but the reprice (whose 14 days run inside the change's own), and ExpectedDays({reprice}) - ExpectedDays({}) for the reprice row",
  "intbl note: 'Net days are execution days plus the change in the expected (mean) time to close, the basis of the optimizer's expected days'; interventionTable() comments (corrected from 'equal to the optimiser's change': the documented definition counts each change's full execution time)");
inv("optimize-budget","both optimiser programmes cost no more than the budget",
  "eq_o ('s.t. C(a) <= B'); optimize()");
inv("optimize-bookkeeping","each programme's c and days equal costOf and daysOf of its keys; its PC, t (mean), tMed, V (median price), proceeds, net and U are those of model(applyAll(...)) at the documented ratio (rhoSell for the proceeds card, optRho for a repriced utility card)",
  "optimize() comments; optimiser cards; eq_os/eq_us");
inv("optimize-dominance","the proceeds programme's net is at least that of doing nothing and of every affordable single change on top of a reprice; the utility programme's U is at least that of every admissible single-change programme",
  "optimize() ('Exhaustive search over every combination of interventions that fits the budget')");
inv("optimize-card-gain","the proceeds card's 'Lifts expected proceeds $X over today's $Y, before the $C spent': X = proceeds - today's EVp is at least the spend C >= 0",
  "optimiser card text (render); optimize() objective");
let nOpt=0;
for(let i=0;i<STATES.length&&i<150;i++){
  const s0={...STATES[i]}; s0.rhoSell=A.bestRatio(s0,0,0); s0.optRho=A.bestRatio(s0,s0.theta,s0.lamT);
  const r0=A.model(s0), it=A.interventionTable(s0,r0), rRep=A.model(A.applyAll(s0,r0,["reprice"]));
  /* applyAll ranges */
  for(const ks of [["reprice"],A.INTERV.map(x=>x.k),A.INTERV.map(x=>x.k).filter(()=>rnd()<.5)]){
    const s1=A.applyAll(s0,r0,ks); let ok=s1.ern<=s1.rev*.92*(1+1e-12)&&Number.isInteger(s1.buyers)&&s1.buyers>=5&&s1.buyers<=600;
    for(const f in XI.FIELD_RANGE) if(s1[f]!==s0[f]&&f!=="ern") ok=ok&&s1[f]>=XI.FIELD_RANGE[f][0]&&s1[f]<=XI.FIELD_RANGE[f][1];
    if(ks.includes("reprice")){ const sNo={...s1}; delete sNo.ask; ok=ok&&rel(s1.ask,A.model(s1).V*(s0.rhoSell))<1e-12; }
    chk("applyAll-ranges",ok,()=>cx({s0,ks,s1}));
  }
  /* table columns */
  for(let j=0;j<it.length;j++){ const o=it[j], c=A.costOf(s0,[o.k]);
    chk("interv-columns",Math.abs(o.c-c)<1e-9&&(c>0?Math.abs(o.roi-(o.dE-c)/c)<1e-12:o.roi===null)&&Math.abs(o.net-(o.dE-c))<1e-9&&Math.abs(o.dTnet-(o.days+o.dT))<1e-9
      &&(j===0||it[j-1].net>=o.net),()=>cx({s0,k:o.k,o:{c:o.c,roi:o.roi,net:o.net,dTnet:o.dTnet}}));
    const solo=o.k==="reprice", r1=A.model(A.applyAll(s0,r0,solo?["reprice"]:["reprice",o.k])), rb=solo?r0:rRep;
    chk("interv-recompute",Math.abs(o.dV-(r1.V-r0.V))<=1e-9*r0.V&&Math.abs(o.dE-(r1.EVp-rb.EVp))<=1e-9*Math.max(1,r0.EVp)&&Math.abs(o.dP-(r1.PC-rb.PC))<1e-12&&Math.abs(o.dT-(r1.tMean-rb.tMean))<1e-9,()=>cx({s0,k:o.k}));
    /* optimiser bookkeeping for the same single change */
    const ks=solo?["reprice"]:["reprice",o.k], rO=A.model(A.applyAll(s0,r0,ks,s0.rhoSell)), netO=rO.EVp-A.costOf(s0,ks);
    chk("interv-vs-optimizer",Math.abs(netO-(solo?r0.EVp+o.net:rRep.EVp+o.net))<=1e-9*Math.max(1,r0.EVp),()=>cx({s0,k:o.k,netO,table:o.net}));
    const base=solo?{t:r0.tMean,d:0}:{t:rRep.tMean,d:A.daysOf(s0,["reprice"])}, prog={t:rO.tMean,d:A.daysOf(s0,ks)};
    chk("interv-netdays-vs-optimizer",Math.abs(o.dTnet-((prog.t+prog.d)-(base.t+base.d))-(solo?0:base.d))<1e-9,()=>cx({ind:s0.ind,rev:s0.rev,ern:s0.ern,ask:s0.ask,k:o.k,tableNetDays:o.dTnet,optimiserChange:(prog.t+prog.d)-(base.t+base.d),execDays:o.days,bundleExecDays:prog.d,baseExecDays:base.d}));
  }
  /* optimiser: every 3rd state (each call is ~0.5 s) */
  if(i%3) continue; nOpt++;
  const best=A.optimize(s0,r0,s0.budget,s0.lamT,s0.theta);
  for(const key of ["V","U"]){ const b=best[key];
    chk("optimize-budget",b.c<=s0.budget+1e-9,()=>cx({s0,key,c:b.c,budget:s0.budget}));
    const rho=key==="V"?s0.rhoSell:(b.keys.includes("reprice")?s0.optRho:s0.rhoSell), rr=A.model(A.applyAll(s0,r0,b.keys,rho)), d=A.daysOf(s0,b.keys), c=A.costOf(s0,b.keys);
    const U=rr.EVp+(1-rr.PC)*s0.theta*rr.V-s0.lamT*(rr.tMean+d)-c;
    chk("optimize-bookkeeping",Math.abs(b.c-c)<1e-6&&b.days===d&&Math.abs(b.PC-rr.PC)<1e-12&&Math.abs(b.t-rr.tMean)<1e-9&&Math.abs(b.tMed-rr.tMed)<1e-9
      &&Math.abs(b.V-rr.Vreal)<1e-9*rr.Vreal&&Math.abs(b.proceeds-rr.EVp)<1e-9*Math.max(1,rr.EVp)&&Math.abs(b.net-(rr.EVp-c))<1e-6&&Math.abs(b.U-U)<1e-6*Math.max(1,Math.abs(U)),
      ()=>cx({s0,key,keys:b.keys,U:b.U,want:U}));
  }
  chk("optimize-card-gain",best.V.proceeds-r0.EVp>=best.V.c-1e-6&&best.V.c>=0,()=>cx({s0,gain:best.V.proceeds-r0.EVp,c:best.V.c}));
  { let ok=best.V.net>=r0.EVp-1e-6, first=null;
    for(const o of A.INTERV){ const ks=o.k==="reprice"?["reprice"]:["reprice",o.k], c=A.costOf(s0,ks); if(c>s0.budget) continue;
      const rv=A.model(A.applyAll(s0,r0,ks,s0.rhoSell)); if(rv.EVp-c>best.V.net+1e-6){ ok=false; first=first||{ks,net:rv.EVp-c,best:best.V.net}; }
      const ru=A.model(A.applyAll(s0,r0,ks,s0.optRho)), d=A.daysOf(s0,ks), U=ru.EVp+(1-ru.PC)*s0.theta*ru.V-s0.lamT*(ru.tMean+d)-c;
      if(U>best.U.U+1e-6){ ok=false; first=first||{ks,U,best:best.U.U}; } }
    chk("optimize-dominance",ok,()=>cx({s0,first})); }
}
console.error(`interventions/optimiser done ${(Date.now()-T0)/1000}s (${nOpt} optimiser runs)`);

inv("walkaway-no-delay","with no cost of delay the walk-away ask is never below the proceeds-maximising ask (the retained-value term only rewards a higher ask: for m below the proceeds optimum both EVp and 1-P_C are lower), so optNote never says 'The cost of delay pulls the second figure below'",
  "optNote() 'lower' branch text; bestRatio() objective U = EVp + (1-P_C) theta V - lambda E[T]");
inv("value-gap-pruning","the value-gap set (render's prune loop) keeps only changes that earn their place: dropping any remaining non-reprice change lowers V by more than max($1, 1e-6 V); the gap it reports is >= 0; its cost is costOf of the set",
  "render() value-gap comments ('repeat until every remaining change earns its place'; 'only the changes that add value'); #o_gap, #o_gapnote");
inv("realisation-factors","the realisation panel's 'Market average' row multiplies out: pctAsk = pctAskSize x the industry factor (its .55-1.12 clamp never binds), and the ask ceiling's headroom is max(1, pctAskSize)",
  "fitTiming() (pctAsk = clamp(pas x f, .55, 1.12)); realisation panel row text 'IBBA size curve at $X: Y%, x f'");
inv("score-order-vs-proceeds","for one business (one reference population) at different asks, a higher expected proceeds never gets a lower Omni score: the score is the percentile of ln EVp in that population",
  "omniScore() comment ('Count the reference population that this deal beats')");
for(let i=0;i<Math.min(STATES.length,120);i++){
  const s={...STATES[i]};
  /* no cost of delay */
  if(i<60){ const t={...s,lamT:0}; t.rhoSell=A.bestRatio(t,0,0); t.optRho=A.bestRatio(t,t.theta,0); const V=A.model({...t,ask:1}).V;
    const n=A.optNote(t,V,A.model({...t,ask:V*t.rhoSell}),A.model({...t,ask:V*t.optRho}));
    chk("walkaway-no-delay",t.optRho>=t.rhoSell-1e-9&&n.kind!=="lower",()=>cx({t,rhoSell:t.rhoSell,optRho:t.optRho,kind:n.kind})); }
  /* value-gap pruning, replicated from render() */
  if(i<40){ const t={...s}; t.rhoSell=A.bestRatio(t,0,0); const r=A.model(t);
    let all=A.INTERV.map(o=>o.k);
    for(let pass=0;pass<A.INTERV.length;pass++){ const vAll=A.model(A.applyAll(t,r,all)).V; let drop=null, bestV=vAll-Math.max(1,vAll*1e-6);
      for(const k of all){ if(k==="reprice") continue; const v=A.model(A.applyAll(t,r,all.filter(x=>x!==k))).V; if(v>=bestV){ bestV=v; drop=k; } }
      if(!drop) break; all=all.filter(x=>x!==drop); }
    const vAll=A.model(A.applyAll(t,r,all)).V, earn=all.filter(k=>k!=="reprice").every(k=>A.model(A.applyAll(t,r,all.filter(x=>x!==k))).V<vAll-Math.max(1,vAll*1e-6));
    chk("value-gap-pruning",earn&&vAll-r.V>=-1e-9*r.V&&all.includes("reprice"),()=>cx({t,all,gap:vAll-r.V})); }
  /* realisation factors */
  { const r=A.model(s), f=r.ft;
    chk("realisation-factors",Math.abs(f.pctAsk-f.pctAskSize*f.indFactor)<1e-12&&r.askCeil===Math.max(1,f.pctAskSize),()=>cx({s,pctAsk:f.pctAsk,pas:f.pctAskSize,f:f.indFactor})); }
  /* score order vs proceeds at several asks */
  if(i<40){ const V=A.model({...s,ask:1}).V, pts=[.6,.9,1,1.1,1.25,1.5,2,4].map(m=>{ const r=A.model({...s,ask:V*m}); return {m,EVp:r.EVp,sc:A.omniScore(r)}; });
    let ok=true, ex=null; for(const a of pts) for(const b of pts) if(a.EVp<b.EVp&&a.sc>b.sc){ ok=false; ex=ex||{a,b}; }
    chk("score-order-vs-proceeds",ok,()=>cx({s,ex})); }
}
console.error(`extra model invariants done ${(Date.now()-T0)/1000}s`);

/* =============================== SCORES =============================== */
inv("omniScore-count","omniScore(r) = clamp(round(100 x #{reference draws below ln EVp} / 128), 1, 99), an integer: the percentile it reports is the count of the 128-draw reference population this deal beats",
  "omniScore() comment ('Count the reference population that this deal beats'); refDistAt()");
inv("businessScore-def","businessScore: score = max(omniScore(rq), omniScore(r)); rA is the business at V x rhoSell; below a typical pool rq is at the typical pool and its own proceeds optimum, otherwise rq = rA; never below the Omni score",
  "businessScore() comment; hero score captions");
inv("score-caption-points","the hero caption's points split adds up: points lost to the ask + points lost to the pool = business score - Omni score, each >= 0",
  "render() hero caption ('the points the Omni score loses, split between the ask (at this pool) and the pool (at the optimal ask)')");
for(let i=0;i<Math.min(STATES.length,90);i++){ const s={...STATES[i]}; const r=A.model(s), sc=A.omniScore(r);
  const R=XI.refDistAt(s), x=Math.log(Math.max(r.EVp,1)); let n=0; for(const v of R.xs) if(v<x) n++;
  const sx=X.omniScore(X.model(s));
  chk("omniScore-count",Number.isInteger(sc)&&sc===Math.max(1,Math.min(99,Math.round(100*n/R.xs.length)))&&R.xs.length===128&&sx===sc,()=>cx({s,sc,n,sx}));
  const rs=A.bestRatio(s,0,0), bs=A.businessScore(s,r,rs), typ=A.IND[s.ind].buyers||50;
  const rA=A.model({...s,ask:r.V*rs});
  let ok=Math.abs(bs.rA.EVp-rA.EVp)<=1e-9*rA.EVp&&bs.score===Math.max(A.omniScore(bs.rq),sc)&&bs.score>=sc;
  if(s.buyers<typ){ const rb=A.bestRatio({...s,buyers:typ},0,0), rq=A.model({...s,buyers:typ,ask:r.V*rb}); ok=ok&&Math.abs(bs.rq.EVp-rq.EVp)<=1e-9*rq.EVp&&bs.thin; }
  else ok=ok&&bs.rq===bs.rA&&!bs.thin;
  chk("businessScore-def",ok,()=>cx({s,score:bs.score,sc}));
  const sA=Math.max(sc,Math.min(bs.score,A.omniScore(bs.rA))), askPts=sA-sc, poolPts=bs.score-sA;
  chk("score-caption-points",askPts>=0&&poolPts>=0&&askPts+poolPts===bs.score-sc,()=>cx({s,askPts,poolPts}));
}
inv("refdist-composite-exact","every one of the 128 reference draws sits at its stated quality composite: refDistAt solves each draw whose fields clamp for the scale that restores it (stress test S-1), so the score's population is standard normal in quality",
  "refDistAt() comments: 'Setting dimension k to z = Z*w_k/|w| puts the weighted composite at exactly Z (where a field's range clamps a dimension, the draw is re-solved so that it still is; see atZ)'");
{ const cl=(v,a,b)=>Math.max(a,Math.min(b,v));
  for(const ind of INDS) for(const ern of [3e4,1e5,3e5,1e6,5e6,2e7]){ const rev=ern/A.typMargin(ind,ern), zq=A.refDistAt({ind,ern,rev}).zq;
    for(let i=1;i<=128;i++){ const Z=XI.nqnt(cl((i-.5)/128,.004,.996)), q=zq[i-1];
      chk("refdist-composite-exact",Math.abs(q-Z)<1e-9,()=>cx({ind,ern,rev,draw:i,Zc:Z,qz:q})); } } }
inv("ceiling-share-consistent","the share of closings at the ceiling agrees with the price quantiles: above the crossing (p >= 1 - capShare + 0.02) the realised price is at the ceiling to softMin's rounding (>= 99% of it), and below it (p <= 1 - capShare - 0.02) it is under the ceiling",
  "model() §23 comments on capShare ('share of closed outcomes at the ceiling') and the quantile function; o_val / scenario captions ('X% of closings at the ask ceiling')");
for(const s of STATES){ const r=A.model(s), c=r.capShare; let ok=true, ex=null;
  for(let p=.01;p<=.99;p+=.01){ const q=r.q(p);
    if(p>=1-c+.02&&q<.99*r.ceil){ ok=false; ex=ex||{p,q,ceil:r.ceil,capShare:c}; }
    if(p<=1-c-.02&&q>=r.ceil*(1+1e-12)){ ok=false; ex=ex||{p,q,ceil:r.ceil,capShare:c}; } }
  chk("ceiling-share-consistent",ok,()=>cx({s,ex})); }
console.error(`scores done ${(Date.now()-T0)/1000}s`);

/* =============================== REPORT (model) =============================== */
function report(){ for(const r of REG.values()){ console.log(r.fails?`FAIL ${r.name} cases=${r.cases} fails=${r.fails} first=${r.first}`:`PASS ${r.name} cases=${r.cases}`);
  if(VERBOSE&&r.more) for(const m of r.more) console.log("     also: "+m); } }

/* =============================== BROWSER =============================== */
async function browser(){
  let pw; try{ pw=require("playwright"); }catch(e){ try{ pw=require("/opt/node-tools/node_modules/playwright"); }catch(e2){ console.log("SKIP browser checks: playwright not found"); return; } }
  inv("page-hero-figures","the hero tiles print the model's own figures: expected proceeds and its cash part, P_C, model value, multiple (SDE and EBITDA), median days, both scores",
    "render() hero block");
  inv("page-intbl-matches","the intervention table rows are interventionTable(s,r) in order, each cell formatted from it (cost, dV, dE, dP_C, Net days, ROI)",
    "render() intbl block");
  inv("page-signed-zero","a displayed zero carries the sign of its value: '−$0', '−0', '−0%' or '−0.0 pts' only for a negative change, '+' only for a non-negative one (a change keeps its sign when it rounds to zero, a convention the stress test kept)","stress test: signed zeros refuted as immaterial; economics: a sign must be the true one");
  inv("page-opt-cards","each optimiser card: the listed costs add up to 'Total committed' (to rounding), which is within the budget; 'Expected proceeds', 'Median price', 'Closes' and 'Expected days' are the programme's figures",
    "render() optimiser cards");
  inv("page-sens-order","the sensitivity bars are sorted by absolute size, descending, and each prints money(value,2) of its row",
    "render() sensV/sensP (sorted by |dV| and |dE|)");
  inv("page-buyer-ev","each buyer-table row: Engages x Closes x the price at this ask rebuilds its Expected value (to display rounding)",
    "render() buytbl; eq_b (AUDIT_FINDINGS R2-1)");
  inv("page-risk-clamp-note","when the SBA note behind the survival-risk tile is held at the $5M 7(a) cap, the tile names the cap (the $25k floor is documented on the Data tab and kept unflagged by the stress test)","R1-6 fix (cap note); stress test (floor refuted as documented and immaterial)");
  inv("page-datatab-tallies","the Data tab's headline counts equal the section badges, the judgment ledger rows add up to the judgment count, the inert + live note adds up to it, the fitted and aggregate counts equal an independent recount from MODELS, and the transactions total is BIZCOMPS + SBA rows",
    "renderData() tally comments");
  const b=await pw.chromium.launch(); const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); const p=await ctx.newPage();
  const errs=[]; p.on("pageerror",e=>errs.push(e.message));
  await p.goto("file://"+path.join(ROOT,"index.html"));
  await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:120000});
  const settle=()=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())),80)));
  const type=async(id,txt)=>{ await p.fill("#"+id,String(txt)); await p.press("#"+id,"Enter"); await settle(); };
  /* states: the default, then typed variations (money fields by text, others by their exact boxes, selects by option) */
  const plans=[[],[["v_ask","5.5M"]],[["v_ask","2M"],["v_buy","10"]],[["v_rev","800k"],["v_ern","150k"],["v_ask","400k"]],[["v_rev","40M"],["v_ern","6M"],["v_ask","30M"],["v_buy","600"]],
    [["v_ern","2M"],["v_ask","9M"],["v_lam","4000"],["v_th","100"]],[["v_rev","120k"],["v_ern","3k"],["v_ask","40k"],["v_bud","none"]],[["v_rev","16M"],["v_ern","2.4M"],["v_ask","8M"],["sel:i_ind","wash"]],
    [["v_ask","4.05M"],["v_th","0"],["v_lam","0"]],[["v_rev","3M"],["v_ern","1.2M"],["v_ask","1.4M"],["v_buy","25"],["sel:i_own","0.95"],["sel:i_fin","0.14"]],
    [["v_ask","6.62M"]],[["sel:i_ind","rest"],["v_rev","100k"],["v_ern","2k"],["v_ask","30k"],["sel:i_own","0.95"],["sel:i_mgt","0.08"],["sel:i_fin","0.14"]],
    [["v_rev","100k"],["v_ern","4k"],["v_ask","40k"]],[["v_rev","60M"],["v_ern","12M"],["v_ask","50M"]]];
  for(const plan of plans){
    await p.click("#reset"); await p.waitForTimeout(400); await settle();
    for(const [id,v] of plan){ if(id.startsWith("sel:")){ await p.selectOption("#"+id.slice(4),v); await settle(); } else await type(id,v); }
    await p.waitForTimeout(250); await settle();
    const res=await p.evaluate(()=>{
      const s=STATE.s, r=STATE.r, T=id=>{ const e=document.getElementById(id); return e?e.textContent.replace(/\s+/g," ").trim():null; };
      const out={plan:{rev:s.rev,ern:s.ern,ask:s.ask,buyers:s.buyers,ind:s.ind}, issues:[]};
      /* hero */
      const ev=T("o_ev"), hero=[[ev&&ev.startsWith(money(r.EVp)),"o_ev",ev,money(r.EVp)],[T("o_pc")===pc(r.PC),"o_pc",T("o_pc"),pc(r.PC)],[T("o_msv")===money(r.V),"o_msv",T("o_msv"),money(r.V)],
        [T("o_mult").startsWith(xx(r.M)),"o_mult",T("o_mult"),xx(r.M)],[T("o_t").startsWith(String(Math.round(r.tMed))),"o_t",T("o_t"),Math.round(r.tMed)],
        [+T("o_score")===omniScore(r),"o_score",T("o_score"),omniScore(r)],[+T("o_score_biz")===r.scoreQ,"o_score_biz",T("o_score_biz"),r.scoreQ]];
      if(r.cashShare<1) hero.push([ev.includes(money(r.EVcash)+" cash at close"),"o_ev cash",ev,money(r.EVcash)]);
      if(r.fv.wedge) hero.push([T("o_mult").includes(xx(r.M*r.fv.wedge)+" EBITDA"),"o_mult ebitda",T("o_mult"),xx(r.M*r.fv.wedge)]);
      out.hero=hero.filter(h=>!h[0]).map(h=>h.slice(1));
      /* intervention table */
      const cellTxt=td=>{ const c=td.cloneNode(true); c.querySelectorAll(".cl,.tags").forEach(x=>x.remove()); return c.textContent.replace(/\s+/g," ").trim(); };
      const it=interventionTable(s,r), rows=[...document.querySelectorAll("#intbl tr")].slice(1).map(tr=>[...tr.children].map(cellTxt));
      out.intbl=[]; out.signed=[];
      it.forEach((o,i)=>{ const row=rows[i]||[];
        const want=[o.n,o.c?moneyIn(o.c):"no capital",Math.abs(o.dV)<r.V*1e-4?"—":(o.dV>=0?"+":"−")+money(Math.abs(o.dV),2),(o.dE>=0?"+":"−")+money(Math.abs(o.dE),2),
          Math.abs(o.dP)<5e-4?"—":pp(o.dP),(o.dTnet>=0?"+":"−")+Math.abs(o.dTnet).toFixed(0),o.roi===null?"—":(o.roi<0?"−":"")+Math.abs(o.roi*100).toFixed(0)+"%"];
        if(JSON.stringify(row)!==JSON.stringify(want)) out.intbl.push({i,row,want});
        const vals=[null,null,o.dV,o.dE,o.dP,o.dTnet,o.roi];
        row.forEach((cell,ci)=>{ if(ci<2) return; const neg=/^−(\$0|0|0%|0\.0 pts)$/.test(cell), pos=/^\+(\$0|0|0\.0 pts)$/.test(cell);
          if((neg&&!(vals[ci]<0))||(pos&&vals[ci]<0)) out.signed.push({where:"intbl "+o.k,cell,dE:o.dE,dTnet:o.dTnet,roi:o.roi,dP:o.dP}); });
      });
      /* sensitivity bars */
      const bars=id=>[...document.querySelectorAll("#"+id+" .bar-row")].map(b=>({n:b.children[0].textContent.trim(),v:b.querySelector(".bar-val").textContent.trim()}));
      const sn=sensitivity(s), sv=bars("sensV"), sp=bars("sensP");
      const wantV=sn.filter(o=>o.k!=="ask"&&o.k!=="buyers").map(o=>({n:o.n,v:o.dV})).sort((a,b)=>Math.abs(b.v)-Math.abs(a.v));
      const wantP=sn.map(o=>({n:o.n,v:o.dE})).sort((a,b)=>Math.abs(b.v)-Math.abs(a.v));
      out.sens=[];
      const shown=v=>(v>0?"+":"")+money(v,2);   /* the v8-charts bar redraw: 'sensitivity values carry their sign ... zero stays bare' */
      wantV.forEach((w,i)=>{ if(!sv[i]||sv[i].n!==w.n||sv[i].v!==shown(w.v)) out.sens.push({col:"V",i,got:sv[i],want:{n:w.n,v:shown(w.v)}}); });
      wantP.forEach((w,i)=>{ if(!sp[i]||sp[i].n!==w.n||sp[i].v!==shown(w.v)) out.sens.push({col:"P",i,got:sp[i],want:{n:w.n,v:shown(w.v)}}); });
      /* the bars carry the sign of their value (checked exactly against shown() above), so a signed zero there is a true sign */
      /* optimiser cards */
      out.cards=[];
      document.querySelectorAll("#optout .opt").forEach((card,ci)=>{
        const trs=[...card.querySelectorAll("table tr")].slice(1), items=trs.slice(0,-1).map(tr=>tr.children[1].textContent.trim()), tot=trs[trs.length-1].children[1].textContent.trim();
        const best=optimize(s,r,s.budget,s.lamT,s.theta)[ci===0?"V":"U"];
        const costs=best.keys.map(k=>INTERV.find(x=>x.k===k).cost(s)), sum=costs.reduce((a,b)=>a+b,0);
        const bigs=[...card.querySelectorAll(".big .n")].map(e=>e.textContent.trim());
        const ok=tot.startsWith(moneyIn(sum)+" of "+moneyIn(s.budget))&&Math.abs(sum-best.c)<1e-6&&best.c<=s.budget+1e-9
          &&bigs[0]===money(best.proceeds)&&bigs[1]===money(best.V)&&bigs[2]===pc(best.PC)&&bigs[3]===String(Math.round(best.t+best.days))
          &&items.every((t,i)=>best.keys.length?t===moneyIn(costs[i]):t==="—");
        if(!ok) out.cards.push({ci,tot,items,bigs,want:{sum:moneyIn(sum),budget:moneyIn(s.budget),proceeds:money(best.proceeds),V:money(best.V),PC:pc(best.PC),days:Math.round(best.t+best.days)}});
      });
      /* buyer table: EV = engages x closes x price at this ask, at display precision */
      out.buy=[];
      [...document.querySelectorAll("#buytbl tr")].slice(1).forEach((tr,i)=>{ const b=r.buyers[i], td=[...tr.children].map(cellTxt);
        if(td[1]!==pc(b.PE)||td[2]!==pc(b.PCj)||td[5]!==money(b.EV)||Math.abs(b.EV-b.PE*b.PCj*b.Pj)>1e-6*Math.max(1,b.EV)) out.buy.push({i,td,PE:b.PE,PCj:b.PCj,Pj:b.Pj,EV:b.EV}); });
      /* risk tile: a clamped note is named */
      { const R=MODELS.risk, raw=R.loan_share*r.V, rt=document.getElementById("o_risk").textContent;
        out.riskClamp=raw>R.loan_range[1]?(/cap at \$5M/.test(rt)?null:{side:"cap",rt}):raw<R.loan_range[0]?{side:"floor",V:r.V,loan:r.risk.loan,raw,named:/\$25k|25,000|7\(a\)/.test(rt),rt:rt.slice(0,160)}:null;
        /* the $25k floor is documented on the Data tab and calibrated into the fit; the stress test kept it unflagged on the tile */
        if(out.riskClamp&&out.riskClamp.side==="floor") out.riskClamp=null; }
      /* whole-console signed zeros in plain text */
      /* (whole-console scan of single text nodes, outside the typeset equations whose operator minus precedes '$0' in 'C(a) = $0': done after the animations settle, below) */
      return out;
    });
    { await p.waitForTimeout(2500);   /* count-up animations can pass through zero: read single text nodes once they have settled */
      const hits=await p.evaluate(()=>{ const out=[], w=document.createTreeWalker(document.getElementById("view-console"),NodeFilter.SHOW_TEXT); let n;
        while((n=w.nextNode())){ if(n.parentElement.closest(".katex,.eq,#intbl,#sensV,#sensP")) continue;
          const t=n.textContent.trim(); if(/^[−+-]\$0$|[−-]\$0(?![\d.,kMB])|[−-]0\.0 pts|(^|\s)[−-]0%/.test(t)) out.push(t.slice(0,120)); }
        return out; });
      if(hits.length) res.signed.push({where:"console text",cell:hits.slice(0,5)}); }
    const tag=JSON.stringify(res.plan);
    chk("page-hero-figures",!res.hero.length,()=>tag+" "+JSON.stringify(res.hero));
    chk("page-intbl-matches",!res.intbl.length,()=>tag+" "+JSON.stringify(res.intbl.slice(0,2)));
    chk("page-signed-zero",!res.signed.length,()=>tag+" "+JSON.stringify(res.signed.slice(0,3)));
    chk("page-opt-cards",!res.cards.length,()=>tag+" "+JSON.stringify(res.cards));
    chk("page-sens-order",!res.sens.length,()=>tag+" "+JSON.stringify(res.sens.slice(0,3)));
    chk("page-buyer-ev",!res.buy.length,()=>tag+" "+JSON.stringify(res.buy.slice(0,2)));
    chk("page-risk-clamp-note",!res.riskClamp,()=>tag+" "+JSON.stringify(res.riskClamp));
  }
  /* Data tab tallies */
  await p.click("#reset"); await p.waitForTimeout(400); await settle();
  const dt=await p.evaluate(()=>{
    const root=document.getElementById("dataviews")||document.getElementById("view-data"); const t=root.textContent.replace(/\s+/g," ");
    const tally=[...root.querySelectorAll(".tally > div")].map(d=>({n:(d.querySelector(".n")||{}).textContent,k:(d.querySelector(".k")||{}).textContent}));
    const badge=re=>{ const h=[...root.querySelectorAll("h2")].find(h=>re.test(h.textContent)); return h?+(h.textContent.match(/(\d+) parameters/)||[])[1]:null; };
    const ledgerTbl=[...root.querySelectorAll("table")].find(tb=>/Reaches which reported number/.test(tb.textContent));
    const ledger=ledgerTbl?[...ledgerTbl.querySelectorAll("tbody tr")].map(tr=>+tr.children[1].textContent.trim()):[];
    const note=(t.match(/made (\d+) of these (\d+) numbers inert.*?The other (\d+) are live/)||[]).slice(1).map(Number);
    /* independent recount from MODELS of the fitted and aggregate tallies, by the rules the tab states */
    const V=MODELS.value, R=MODELS.risk, C=MODELS.close_and_timing, F=MODELS.fitted;
    const fit=1+Object.keys(V.coefficients).length+Object.keys(V.industry_effects).length+Object.keys(V.industry_effects_naics6).length
      +R.co.log_base.filter(x=>x!==null).length+R.pif.log_base.length+Object.keys(R.co.coef).length+Object.keys(R.co.age_coef).length+Object.keys(R.pif.coef).length
      +2+Object.keys(R.co.sector).length+Object.keys(R.naics6_effects).length+Object.keys(R.state_effects).length+F.sba_rate.spread_knots.length
      +2+Object.keys(F.sde_margin.ln_at_ref).length+F.quality_weights.fitted.length+F.buyer_mix.knots.length*2
      +Object.entries(V.fan_quantiles).filter(([k])=>k!=="p50").length+V.calibration.log_correction.length+new Set(Object.values(R.pif.sector)).size+3
      +new Set(F.ttc_shape.beta).size+F.ttc_medians.listing.length
      /* October 2026, second round: the size slopes and the size z-score's width, comparables depth per industry, e-commerce's
         margin (a median of sold listings), the tail's band ratios, and confidence's two gradients and depth variance (its
         scale K and fan approximation s_eq are calibrated: no tally) */
      +2+1+Object.keys(IND).length+Object.values(F.peer_gm.by_industry).filter(g=>g.tier==="listing-level").length
      +R.tail.by_band.ratio.length+["b_size","b_em","tau2"].filter(k=>typeof F.confidence[k]==="number").length;
    const agg=2+Object.keys(C.close_probability.valuation_gap_distribution).length+C.time_to_close.bands.length+Object.keys(V.price_realisation_by_industry.factor).length
      +C.ibba_cash_at_close.by_band.length+4+2
      /* second round: the bridged margin curves' knots, growth, the benchmarked retention cells, the tailwind, the QoE fee's
         floor and share, the GM's employer-cost loading and hire, the sales hire's floor by industry */
      +Object.values(F.peer_gm.by_industry).filter(g=>g.tier!=="listing-level").reduce((a,g)=>a+new Set(g.gm).size,0)
      +Object.keys(F.peer_grw.by_industry).length+Object.keys(F.peer_rec_ret.rec).length+Object.keys(F.peer_rec_ret.ret).length
      +Object.keys(F.tailwind.by_industry).length+2+2+Object.keys(F.interventions.growth_floor.by_industry).length
      /* third round: the largest customer's median (cross-industry and manufacturing) and the two measured peer spreads;
         a flat margin curve (car washes) is one number */
      +1+Object.keys(F.peer_cc.by_industry).length+["grw","cc"].filter(k=>F.peer_sd[k]&&typeof F.peer_sd[k].v==="number").length;
    return {tally,fitB:badge(/^Fitted/),aggB:badge(/^Aggregate/),judB:badge(/^Judgment/),ledger,note,fit,agg,tx:V.n_fit+R.n_fit};
  });
  { const n=dt.tally.map(x=>+String(x.n).replace(/[^\d]/g,"")), sum=dt.ledger.reduce((a,b)=>a+b,0);
    chk("page-datatab-tallies",n[0]===dt.fitB&&n[1]===dt.aggB&&n[2]===dt.judB,()=>cx({tally:n,badges:[dt.fitB,dt.aggB,dt.judB]}));
    chk("page-datatab-tallies",sum===dt.judB,()=>cx({ledgerSum:sum,judgment:dt.judB,rows:dt.ledger}));
    chk("page-datatab-tallies",dt.note.length===3&&dt.note[1]===dt.judB&&dt.note[0]+dt.note[2]===dt.judB,()=>cx({note:dt.note,judgment:dt.judB}));
    chk("page-datatab-tallies",dt.fit===dt.fitB&&dt.agg===dt.aggB,()=>cx({recountFit:dt.fit,shownFit:dt.fitB,recountAgg:dt.agg,shownAgg:dt.aggB}));
    chk("page-datatab-tallies",n[3]===dt.tx,()=>cx({shown:n[3],want:dt.tx})); }
  chk("page-hero-figures",errs.length===0,()=>"page errors: "+errs.join(" | "));
  await b.close();
}

(async()=>{
  if(!MODEL_ONLY){ try{ await browser(); }catch(e){ console.log("browser checks errored: "+e.message); } }
  report();
  const nf=[...REG.values()].filter(r=>r.fails).length;
  console.log(`${REG.size} invariants, ${[...REG.values()].reduce((a,r)=>a+r.cases,0)} cases, ${nf} failing; ${((Date.now()-T0)/1000).toFixed(0)} s`);
  process.exit(nf?1:0);
})();
