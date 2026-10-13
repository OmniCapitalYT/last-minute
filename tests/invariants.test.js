/* The stress test's invariants (October 2026): about 250 assertions written by four independent
   stress testers, each a different lens on whether the model is logical. They were kept as a suite
   so that every one of them keeps holding:
     tests/invariants/statics.js     comparative statics: which way every input moves every output
     tests/invariants/identities.js  identities, bounds, units and reconciliations across the model API
     tests/invariants/extremes.js    the corners of the input space, jumps at every threshold, determinism
     tests/invariants/app.js         the live page: every figure and every directional word against the model
   Each file prints one line per invariant, "PASS <name> cases=<n>" or "FAIL <name> cases=<n> fails=<k>
   first=<counterexample>", and states where each expectation comes from (a code comment, a MODELS
   note, the Data tab, AUDIT.md or economics). This runner runs the model parts in parallel and fails
   if any invariant fails.
   Run: node tests/invariants.test.js            (model parts, about 3 minutes)
        node tests/invariants.test.js --browser  (adds the in-page checks and app.js, about 10 minutes) */
const {spawn}=require("child_process"), path=require("path");
const browser=process.argv.includes("--browser");
const dir=path.join(__dirname,"invariants");
const runs=[
  ["statics.js",   browser?["--browser"]:[]],
  ["identities.js",browser?[]:["--model-only"]],
  ["extremes.js",  browser?[]:["--no-browser"]],
];
if(browser) runs.push(["app.js",[]]);
const one=([file,args])=>new Promise(res=>{
  const p=spawn(process.execPath,[path.join(dir,file),...args],{cwd:path.join(__dirname,"..")});
  let out=""; p.stdout.on("data",d=>out+=d); p.stderr.on("data",d=>out+=d);
  p.on("close",code=>res({file,code,out}));
});
Promise.all(runs.map(one)).then(rs=>{
  let pass=0, fail=0, bad=false;
  for(const r of rs){
    const lines=r.out.split("\n"), P=lines.filter(l=>l.startsWith("PASS ")).length, F=lines.filter(l=>l.startsWith("FAIL "));
    pass+=P; fail+=F.length;
    console.log(`${r.file.padEnd(15)} ${P} pass, ${F.length} fail${r.code?` (exit ${r.code})`:""}`);
    for(const l of F) console.log("  "+l.slice(0,400));
    if(r.code||!P) bad=true;
    if(r.code&&!F.length) console.log(r.out.split("\n").slice(-15).join("\n"));
  }
  console.log(`${pass} invariants passed, ${fail} failed`);
  process.exit(bad||fail?1:0);
});
