/* Load the model half of a frozen copy of index.html into a sandbox, so a fitting script can evaluate the
   model at candidate parameter values without touching the repo.
   const H=require('/tmp/claude-0/fit6/harness.js');
   const A=H.load();                                         // the snapshot as shipped (HEAD 56ba230)
   const B=H.load([['vet:    {n:"Veterinary practice",                        anchor:4.40, buyers:50, gm:.58',
                    'vet:    {n:"Veterinary practice",                        anchor:4.40, buyers:50, gm:.61']]);
   // each pair: exact substring -> replacement; every substring must occur
   H.load(overrides, '/path/to/other/index.html')            // a patched page instead of the snapshot
   Exports: the same API as tests/load.js.
   Shipped in fit/ so the second round's node probes can be re-run (fit/README.md): set SNAP to a copy of index.html as of
   commit 56ba230, the page before that round, and point each script's HARNESS constant at this file. */
const fs=require("fs"),vm=require("vm");
const SNAP="/tmp/claude-0/fit6snap/index.html";
function load(overrides,file){
  const html=fs.readFileSync(file||SNAP,"utf8");
  let src=html.slice(html.lastIndexOf("<script>")+8);
  const cut=src.indexOf("/* ============ bar helpers");
  if(cut<0) throw new Error("could not find the end of the model section");
  src=src.slice(0,cut);
  for(const [a,b] of (overrides||[])){ if(!src.includes(a)) throw new Error("override target not found: "+a.slice(0,80)); src=src.split(a).join(b); }
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN};
  vm.createContext(ctx);
  vm.runInContext(src+`;this.API={model,omniScore,fitValue,fitRisk,fitClose,
  fitTiming,bestRatio,optimize,applyAll,interventionTable,sensitivity,MODELS,IND,REF_RATIO,
  RHO_MAX,AMAX,fanRatio,fanNodes,softMin,gapPenalty,sizeRefs,sbaRate,jobsFor,typMargin,QW,buyerMix,INTERV,costOf,daysOf,IND2NAICS,gmSalary,
  timeMult,T_ELAST,T_SMOOTH,optNote,optCardNote,businessScore,sdeEbitdaWedge,naicsFor,PEN_MAX,GAP_TAIL_K,money,ENG_SHARE,COMP_K,COMP_H,THIN_W,capOne,BUYERS,PHI,FAN_S,qualityZ,jobsKnots,moneyIn,refDistAt,nqnt};`,ctx);
  return ctx.API;
}
module.exports={load,SNAP};
