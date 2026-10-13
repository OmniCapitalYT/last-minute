/* Loads the model half of index.html's main script into a sandbox, so the same
   code the page runs can be tested without a browser. */
const fs=require("fs"),path=require("path"),vm=require("vm");
const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const src=html.slice(html.lastIndexOf("<script>")+8);
const cut=src.indexOf("/* ============ bar helpers");
if(cut<0) throw new Error("could not find the end of the model section");
/* overrides: [[exact substring, replacement], ...] applied to the model source, for
   sensitivity pins that change a judgment table (each substring must occur) */
function load(overrides){
  let code=src.slice(0,cut);
  for(const [a,b] of (overrides||[])){ if(!code.includes(a)) throw new Error("override target not found: "+a.slice(0,80)); code=code.split(a).join(b); }
  const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN};
  vm.createContext(ctx);
  vm.runInContext(code+`;this.API={model,omniScore,fitValue,fitRisk,fitClose,
  fitTiming,bestRatio,optimize,applyAll,interventionTable,sensitivity,MODELS,IND,REF_RATIO,
  RHO_MAX,AMAX,fanRatio,fanNodes,softMin,gapPenalty,sizeRefs,sbaRate,jobsFor,typMargin,QW,buyerMix,INTERV,costOf,daysOf,IND2NAICS,gmSalary,
  timeMult,T_ELAST,T_SMOOTH,optNote,optCardNote,businessScore,sdeEbitdaWedge,naicsFor,PEN_MAX,GAP_TAIL_K,money,ENG_SHARE,COMP_K,COMP_H,THIN_W,capOne,BUYERS,PHI,FAN_S,qualityZ,jobsKnots,moneyIn,refDistAt,nqnt};`,ctx);
  return ctx.API;
}
module.exports=load();
module.exports.loadWith=load;
