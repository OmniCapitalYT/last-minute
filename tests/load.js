/* Loads the model half of index.html's main script into a sandbox, so the same
   code the page runs can be tested without a browser. */
const fs=require("fs"),path=require("path"),vm=require("vm");
const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const src=html.slice(html.lastIndexOf("<script>")+8);
const cut=src.indexOf("/* ============ bar helpers");
if(cut<0) throw new Error("could not find the end of the model section");
const ctx={console,Math,Map,JSON,Object,Array,Number,String,isFinite,Set,Infinity,NaN};
vm.createContext(ctx);
vm.runInContext(src.slice(0,cut)+`;this.API={model,omniScore,fitValue,fitRisk,fitClose,
  fitTiming,bestRatio,optimize,applyAll,interventionTable,sensitivity,MODELS,IND,REF_RATIO,
  RHO_MAX,AMAX,fanRatio,softMin,gapPenalty,sizeRefs,sbaRate,jobsFor,typMargin,QW,INTERV,costOf,daysOf,IND2NAICS,gmSalary};`,ctx);
module.exports=ctx.API;
