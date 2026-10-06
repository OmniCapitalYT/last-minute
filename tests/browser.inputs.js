/* Real-keystroke checks on the rail and navigation: typed money waits for Enter, rejected
   input restores the previous value and stays marked, earnings survive a revenue drag,
   quick tab clicks land on the last one clicked, and reset does not eat a later change.
   Run: node tests/browser.inputs.js  (needs playwright) */
const path=require("path");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
(async()=>{
  const b=await pw.chromium.launch(), p=await b.newPage({viewport:{width:1440,height:900}});
  const errs=[]; p.on("pageerror",e=>errs.push(e.message));
  await p.goto("file://"+path.join(__dirname,"..","index.html"));
  await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000});
  let fail=0; const ok=(c,m)=>{ console.log((c?"ok   ":"FAIL ")+m); if(!c) fail++; };
  const settle=()=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>r()),60)));
  const st=()=>p.evaluate(()=>({rev:STATE.s.rev,ern:STATE.s.ern,ask:STATE.s.ask,gm:STATE.s.gm,buy:STATE.s.buyers}));
  const type=async(id,txt,key)=>{ await p.click("#"+id); await p.keyboard.press("Control+A");
    await p.keyboard.type(txt,{delay:15}); if(key) await p.keyboard.press(key); await settle(); };

  await type("v_rev","8M","Enter"); let s=await st();
  ok(Math.abs(s.rev-8e6)<1&&Math.abs(s.ern-1.45e6)<1,`typing 8M keeps earnings: rev ${s.rev} ern ${s.ern}`);
  await type("v_ask","14%","Enter"); s=await st();
  ok(Math.abs(s.ask-3.24e6)<1,`rejected ask restores the previous one: ${s.ask}`);
  ok(await p.evaluate(()=>document.getElementById("v_ask").classList.contains("bad")),"rejected ask is outlined");
  await type("v_ask","12.3.4m","Tab"); s=await st(); ok(Math.abs(s.ask-3.24e6)<1,`malformed ask restores: ${s.ask}`);
  await type("v_buy","120"); await p.keyboard.press("Control+A"); await p.keyboard.press("Backspace"); await p.keyboard.press("Tab"); await settle();
  s=await st(); ok(s.buy===65,`abandoned buyer entry restores 65: ${s.buy}`);
  await type("v_rev","2M"); await p.keyboard.press("Escape"); await settle(); s=await st();
  ok(Math.abs(s.rev-8e6)<1,`Escape reverts: ${s.rev}`);
  await p.evaluate(()=>{ const r=document.getElementById("i_rev"); r.value=0; r.dispatchEvent(new Event("input",{bubbles:true})); });
  await settle();
  await p.evaluate(()=>{ IN.rev=8e6; scheduleRender(); }); await settle(); s=await st();
  ok(Math.abs(s.ern-1.45e6)<1,`earnings survive a revenue drag to the minimum and back: ${s.ern}`);

  await p.click('.tab[data-v="data"]'); await p.waitForTimeout(120); await p.click('.tab[data-v="console"]');
  await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>!document.getElementById("view-console").hidden),"quick Data-then-Console lands on Console");

  await p.click("#reset"); await p.waitForTimeout(100);
  await p.evaluate(()=>{ const g=document.getElementById("i_gm"); g.value=80; g.dispatchEvent(new Event("input",{bubbles:true})); });
  await p.waitForTimeout(1200); s=await st();
  ok(Math.abs(s.gm-.80)<1e-9,`a change straight after reset survives: gm ${s.gm}`);
  ok(errs.length===0,"no page errors"+(errs.length?": "+errs.join(" | "):""));
  await b.close(); process.exit(fail?1:0);
})();
