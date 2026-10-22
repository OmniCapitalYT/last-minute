/* foruse.html, the version without equation documentation, provenance labels or the Data tab: it is what
   tools/build_foruse.js makes of index.html today; it loads and runs without errors; none of what it leaves out is
   on the page or in the seller report; and through a walk of inputs it shows the same figures as index.html.
   Run: node tests/browser.foruse.js  (needs playwright) */
const path=require("path"), cp=require("child_process");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
let fail=0; const ok=(c,m)=>{ console.log((c?"ok   ":"FAIL ")+m); if(!c) fail++; };
(async()=>{
  const chk=cp.spawnSync(process.execPath,[path.join(__dirname,"..","tools","build_foruse.js"),"--check"],{encoding:"utf8"});
  ok(chk.status===0,"foruse.html is what tools/build_foruse.js builds from index.html: "+(chk.stdout||chk.stderr).trim());

  const b=await pw.chromium.launch();
  const open=async f=>{ const p=await b.newPage({viewport:{width:1440,height:900}}), errs=[];
    p.on("pageerror",e=>errs.push(e.message)); p.on("console",m=>{ if(m.type()==="error") errs.push(m.text()); });
    await p.goto("file://"+path.join(__dirname,"..",f)); await p.waitForTimeout(1500); await p.keyboard.press("Escape");
    await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(1500);
    return {p,errs}; };
  const A=await open("index.html"), F=await open("foruse.html");
  const settle=p=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())),80)));

  /* ---- what is left out ---- */
  const gone=await F.p.evaluate(()=>{ const vis=e=>!!(e.offsetParent||e.getClientRects().length);
    const n=s=>[...document.querySelectorAll(s)].filter(vis).length;
    return {tabs:[...document.querySelectorAll(".tab")].map(t=>t.dataset.v).join(","), data:document.getElementById("dataviews").children.length,
      eq:n(".eq"), katex:n(".katex"), pv:n(".pv,.pvkey"), refs:[...document.querySelectorAll(".sec-head .ref")].filter(e=>/§/.test(e.textContent)).length,
      method:[...document.querySelectorAll(".sec h2")].some(h=>/Method and provenance|Toward fitting/.test(h.textContent)),
      chips:[...document.querySelectorAll(".st")].filter(e=>vis(e)&&/^(judgment|fitted|aggregate|published|calibrated)$/i.test(e.textContent.trim())).length,
      text:document.body.innerText }; });
  ok(gone.tabs==="console,deals","two tabs, Console and Deals: "+gone.tabs);
  ok(gone.data===0,"the Data tab is never built");
  ok(gone.eq===0&&gone.katex===0,`no equation on the page (${gone.eq} cards, ${gone.katex} typeset)`);
  ok(gone.pv===0&&gone.chips===0,`no provenance badge, key or tier chip (${gone.pv} badges, ${gone.chips} chips)`);
  ok(gone.refs===0&&!gone.method,"no framework section references, no method-and-provenance or model-fitting section");
  ok(!/Data tab|Data & parameters|badge/i.test(gone.text),"no text points at the Data tab or the badges");
  const mark=await A.p.evaluate(()=>({tabs:[...document.querySelectorAll(".tab")].map(t=>t.dataset.v).join(","),eq:document.querySelectorAll(".eq").length,pv:document.querySelectorAll(".pv").length}));
  ok(mark.tabs==="console,data,deals"&&mark.eq>10&&mark.pv>5,"index.html keeps all three tabs, its equation cards and its badges");

  /* ---- the same figures through a walk of inputs ---- */
  const nums=p=>p.evaluate(()=>{ const t=s=>[...document.querySelectorAll(s)].map(e=>e.innerText).join(" | ");
    const txt=[t(".hero-stats .big .n"),t("#o_listp"),t("#o_listp2"),t("#intbl"),t("#buytbl"),t("#multbl"),t("#fintbl"),t("#o_risk"),t("#o_t")].join(" || ");
    return {n:txt.match(/[−+-]?\$?\d[\d,.]*[kKMB%×]?/g)||[], bad:/NaN|Infinity|undefined/.test(document.getElementById("view-console").innerText)}; });
  const both=async fn=>{ for(const P of [A.p,F.p]){ await P.evaluate(fn[0],fn[1]); await settle(P); } };
  const steps=[["start",null]];
  const sel=await A.p.$$eval("#view-console select",els=>els.map(e=>({id:e.id,v:[...e.options].map(o=>o.value)})));
  for(const s of sel) for(const v of s.v.filter((_,i)=>i%Math.max(1,Math.ceil(s.v.length/4))===0)) steps.push(["select "+s.id+"="+v,[(a)=>{ const e=document.getElementById(a[0]); e.value=a[1]; e.dispatchEvent(new Event("change",{bubbles:true})); },[s.id,v]]]);
  const ranges=await A.p.$$eval("#view-console input[type=range]",els=>els.map(e=>e.id).filter(Boolean));
  for(const id of ranges) for(const f of [0,.5,1])
    steps.push([id+"@"+f,[(a)=>{ const e=document.getElementById(a[0]); if(!e) return; e.value=+e.min+(+e.max-+e.min)*a[1]; e.dispatchEvent(new Event("input",{bubbles:true})); },[id,f]]]);
  steps.push(["franchise",[()=>{ const e=document.getElementById("i_fr"); if(e) e.click(); },null]]);
  let same=0, diff=[];
  for(const [name,op] of steps){
    if(op) await both(op);
    const x=await nums(A.p), y=await nums(F.p);
    if(x.n.join(" ")===y.n.join(" ")&&!y.bad) same++; else diff.push(name+(y.bad?" (NaN in foruse)":"")+": "+x.n.filter((v,i)=>v!==y.n[i]).slice(0,3).join(","));
  }
  ok(!diff.length,`${same} of ${steps.length} input states show the same figures in both versions`+(diff.length?": "+diff.slice(0,4).join("; "):""));

  /* ---- the seller report ---- */
  await F.p.click("#tl_report"); await settle(F.p); await F.p.waitForTimeout(600);
  const rp=await F.p.evaluate(()=>{ const e=document.getElementById("rp_paper"); return {b:e.querySelectorAll(".rp-b,.rp-bx").length,t:e.innerText,on:document.documentElement.classList.contains("rp-on")}; });
  ok(rp.on&&rp.t.length>500,"the seller report opens");
  ok(rp.b===0&&!/× judgment|published data\b/.test(rp.t),`the report carries no tier badge (${rp.b})`);
  await F.p.keyboard.press("Escape"); await settle(F.p);
  await F.p.click('.tab[data-v="deals"]');   /* the views swap at the tab warp's flash */
  ok(await F.p.waitForFunction(()=>!document.getElementById("view-deals").hidden&&document.getElementById("view-console").hidden,null,{timeout:8000}).then(()=>true,()=>false),"the Deals tab opens");

  ok(!F.errs.length,"no page or console errors in foruse.html"+(F.errs.length?": "+F.errs.slice(0,3).join(" / "):""));
  ok(!A.errs.length,"no page or console errors in index.html"+(A.errs.length?": "+A.errs.slice(0,3).join(" / "):""));
  await b.close();
  console.log(fail?`\n${fail} FAILED`:"\nall foruse checks pass");
  process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
