/* The path from the console to AI Vince: the toolbar button stores a snapshot of the console's outputs, ai-vince.html
   reads it and shows the same figures, asks the server (mock replies) for the analysis, streams it, takes follow-ups, and
   never parses what the model writes as HTML.
   Run: node tests/browser.vince.js  (needs playwright and server/node_modules) */
const path=require("path"), cp=require("child_process");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
let fail=0; const ok=(c,m)=>{ console.log((c?"ok   ":"FAIL ")+m); if(!c) fail++; };
const start=()=>new Promise((res,rej)=>{ const c=cp.spawn(process.execPath,[path.join(__dirname,"..","server","vince-server.mjs")],{env:{...process.env,VINCE_MOCK:"1",PORT:"0",HOST:"127.0.0.1"}});
  let b=""; c.stdout.on("data",d=>{ b+=d; const m=b.match(/:(\d+)\s/); if(m) res({c,port:+m[1]}); }); c.on("error",rej); });
(async()=>{
  const S=await start(), base=`http://127.0.0.1:${S.port}`, br=await pw.chromium.launch(), errs=[];
  try{
    const p=await br.newPage({viewport:{width:1440,height:900}});
    p.on("pageerror",e=>errs.push(e.message)); p.on("console",m=>{ if(m.type()==="error") errs.push(m.text()); });
    const settle=()=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())),80)));

    /* with nothing stored */
    await p.goto(base+"/ai-vince.html"); await p.waitForTimeout(400);
    ok(await p.evaluate(()=>!document.getElementById("none").hidden&&document.getElementById("have").hidden),"with no snapshot the page says there is nothing to read and offers the console");

    /* the console */
    await p.goto(base+"/"); await p.waitForTimeout(1200); await p.keyboard.press("Escape");
    await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(1200);
    ok(await p.evaluate(()=>!!document.getElementById("tl_vince")&&document.getElementById("tl_vince").textContent.trim()==="AI Vince"),"the console's toolbar has an AI Vince button");
    /* across inputs (every industry, thin and thick pools, a franchise, a lender-hostile ask) it builds without error, with no NaN */
    const sweep=await p.evaluate(async()=>{ const out=[], set=(id,v,ev)=>{ const e=document.getElementById(id); e.value=v; e.dispatchEvent(new Event(ev||"input",{bubbles:true})); };
      const wait=()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())),60));
      const inds=[...document.getElementById("i_ind").options].map(o=>o.value);
      for(const [k,ind] of inds.entries()){ set("i_ind",ind,"change"); if(k%3===0) set("i_buy",k%2?3:120); if(k%4===0) set("i_gm",k%8?15:90); await wait();
        let snap=null, err=null; try{ snap=OMNI_BROKER.vinceSnapshot(); }catch(e){ err=String(e); }
        const bad=[]; (function w(o,p){ if(typeof o==="number"&&!isFinite(o)) bad.push(p); else if(o&&typeof o==="object") for(const x in o) w(o[x],p+"."+x); })(snap,"");
        out.push({ind,err,ok:!!snap&&snap.version===1,bad:bad.length,size:snap?JSON.stringify(snap).length:0}); }
      return out; });
    ok(sweep.length>10&&sweep.every(r=>!r.err&&r.ok&&!r.bad&&r.size<100000),`the snapshot builds for all ${sweep.length} industries across thin and thick pools and margins (largest ${Math.max(...sweep.map(r=>r.size))} bytes)${sweep.filter(r=>r.err||!r.ok||r.bad).map(r=>" ["+r.ind+": "+(r.err||r.bad+" NaN")+"]").join("")}`);
    await p.click("#reset"); await p.waitForTimeout(900);
    await p.click("#tl_vince"); await p.waitForURL("**/ai-vince.html"); await p.waitForTimeout(500);
    const snap=await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.vince.v1")));
    const bad=[]; (function w(o,k){ if(typeof o==="number"&&!isFinite(o)) bad.push(k); else if(o&&typeof o==="object") for(const x in o) w(o[x],k+"."+x); })(snap,"");
    ok(snap&&snap.version===1&&!bad.length&&JSON.stringify(snap).length<60000,"the snapshot is JSON-safe and well under the server's 120 KB limit ("+JSON.stringify(snap).length+" bytes)");
    ok(["inputs","value","closing","timing","price_if_it_closes","survival_risk","quality","buyers","asks","levers","financing","console_displays"].every(k=>snap&&snap[k]!=null),"it carries inputs, value, closing, timing, price, risk, quality, buyers, asks, levers, financing and the printed figures");
    const D=snap.console_displays, pc=Math.round(snap.closing.chance*100), days=Math.round(snap.timing.median_days);
    ok(D.o_pc===pc+"%"&&D.o_t===days+" days"&&Math.abs(snap.value.model_value-(+D.o_msv.replace(/[$M]/g,"")*1e6))<=5e3,`its numbers are the console's own (value ${D.o_msv}, closing ${D.o_pc}, time ${D.o_t})`);

    /* the page shows them */
    const shown=await p.evaluate(()=>[...document.querySelectorAll(".kpi")].map(k=>k.textContent));
    ok(shown.some(t=>t.includes(D.o_msv))&&shown.some(t=>t.includes(D.o_pc))&&shown.some(t=>t.includes(D.o_t.replace(" days",""))),"the page shows the value, chance of closing and time to close that the console printed");

    /* the analysis */
    await p.click("#go"); await p.waitForSelector(".msg.md h3",{timeout:15000}); await p.waitForFunction(()=>!document.getElementById("go").disabled,null,{timeout:15000});
    ok(await p.evaluate((v)=>document.getElementById("out").textContent.includes(v),D.o_msv),"the analysis streams in and quotes the console's value");
    ok(await p.evaluate(()=>!document.getElementById("follow").hidden&&document.querySelectorAll(".chip").length>=4),"follow-up questions open, with suggestions");
    await p.fill("#q","What is the biggest risk?"); await p.keyboard.press("Enter");
    await p.waitForFunction(()=>document.querySelectorAll(".msg.me").length===1&&document.querySelectorAll(".msg.md").length>=2&&!document.getElementById("send").disabled,null,{timeout:15000});
    ok(await p.evaluate(()=>document.getElementById("out").textContent.includes("What is the biggest risk?")),"a typed follow-up is sent and answered");
    await p.click(".chip"); await p.waitForFunction(()=>document.querySelectorAll(".msg.me").length===2&&!document.getElementById("send").disabled,null,{timeout:15000});
    ok(true,"a suggested question works");

    /* it survives a reload of this tab, then starts over on request */
    await p.reload(); await p.waitForTimeout(600);
    ok(await p.evaluate(()=>document.querySelectorAll(".msg").length>=5&&!document.getElementById("follow").hidden),"after a reload the conversation is still there");

    /* nothing the model writes is parsed as HTML */
    await p.fill("#q","xss-test"); await p.keyboard.press("Enter");
    await p.waitForFunction(()=>document.getElementById("out").textContent.includes("Escaping")&&!document.getElementById("send").disabled,null,{timeout:15000});
    const x=await p.evaluate(()=>({fired:!!window.__xss,imgs:document.querySelectorAll("#out img,#out script").length,text:document.getElementById("out").textContent.includes("<img src=x")}));
    ok(!x.fired&&x.imgs===0&&x.text,"markup in a reply is shown as text: no element is created and no script runs");
    await p.click("#redo"); ok(await p.evaluate(()=>document.getElementById("follow").hidden&&document.querySelectorAll(".msg").length===0),"'Start over' clears the conversation");

    /* a failure is shown plainly */
    await p.route("**/api/vince",r=>r.fulfill({status:503,contentType:"application/json",body:JSON.stringify({error:"AI Vince is busy. Try again in a moment."})}));
    await p.click("#go"); await p.waitForSelector(".err",{timeout:8000});
    ok(await p.evaluate(()=>document.querySelector(".err").textContent.includes("busy")&&!document.getElementById("go").disabled),"a server error appears as a plain message and the button works again");

    /* a phone */
    await p.setViewportSize({width:390,height:800}); await p.unroute("**/api/vince"); await p.waitForTimeout(300);
    ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),"no sideways scroll at 390 px");
    const real=errs.filter(e=>!/status of 503/.test(e));   /* the 503 is the stub above */
    ok(!real.length,"no page or console errors"+(real.length?": "+real.slice(0,3).join(" / "):""));
  } finally { await br.close(); S.c.kill(); }
  console.log(fail?`\n${fail} FAILED`:"\nall AI Vince browser checks pass"); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
