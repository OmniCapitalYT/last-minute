/* Drives index.html in headless Chromium: every select through every option and every
   slider through five positions, checking for page errors, KaTeX failures, NaN /
   Infinity / undefined in the rendered text, and horizontal scroll.
   Run: node tests/browser.sweep.js  (needs playwright) */
const path=require("path");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{
  const b=await pw.chromium.launch();
  const issues=[];
  for(const width of [1440,390]){
    const p=await b.newPage({viewport:{width,height:900}});
    p.on("pageerror",e=>issues.push(`[${width}] page error: ${e.message}`));
    p.on("console",m=>{ if(m.type()==="error") issues.push(`[${width}] console: ${m.text()}`); });
    await p.goto("file://"+path.join(__dirname,"..","index.html"));
    await p.waitForTimeout(600);
    const check=async tag=>{
      await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
      const r=await p.evaluate(()=>{
        const t=document.getElementById("view-console").innerText;
        return {bad:(t.match(/NaN|Infinity|undefined/g)||[]).length,
                katex:document.querySelectorAll(".katex-error").length,
                hscroll:document.documentElement.scrollWidth>innerWidth+1};
      });
      if(r.bad) issues.push(`[${width}] ${tag}: ${r.bad} NaN/Infinity/undefined in text`);
      if(r.katex) issues.push(`[${width}] ${tag}: ${r.katex} KaTeX errors`);
      if(r.hscroll) issues.push(`[${width}] ${tag}: horizontal scroll`);
    };
    let n=0;
    const selects=await p.$$eval("#view-console select",els=>els.map(e=>({id:e.id,v:[...e.options].map(o=>o.value)})));
    for(const sel of selects){ const step=sel.id==="i_st"?7:1;
      for(let i=0;i<sel.v.length;i+=step){ await p.selectOption("#"+sel.id,sel.v[i]); await check(`${sel.id}=${sel.v[i]}`); n++; }
      await p.click("#reset"); }
    const ranges=await p.$$eval("#view-console input[type=range]",els=>els.map(e=>({id:e.id,min:+e.min,max:+e.max})));
    for(const r of ranges){
      for(const f of [0,.25,.5,.75,1]){
        await p.$eval("#"+r.id,(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));},r.min+(r.max-r.min)*f);
        await check(`${r.id}@${f}`); n++; }
      await p.click("#reset"); }
    await p.click("#i_fr"); await check("franchise on"); await p.click("#i_fr"); n+=2;
    await p.click(".tab[data-v=data]"); await p.waitForTimeout(300);
    const dt=await p.evaluate(()=>document.getElementById("view-data").innerText);
    if(/NaN|Infinity|undefined/.test(dt)) issues.push(`[${width}] data tab shows NaN/undefined`);
    console.log(`width ${width}: ${n} input states checked`);
    await p.close();
  }
  await b.close();
  console.log(issues.length?issues.join("\n"):"no issues");
  process.exit(issues.length?1:0);
})();
