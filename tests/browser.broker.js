/* The broker tools in a real browser: the financing check redraws on its own inputs, the worksheet sets SDE and
   revenue, the seller report prints on one page and downloads as a self-contained file, and saved deals survive a
   reload, export, import, edits and opening back into the console. Run: node tests/browser.broker.js  (needs playwright) */
const fs=require("fs"), os=require("os"), path=require("path");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
const URL="file://"+path.join(__dirname,"..","index.html");
(async()=>{
  const b=await pw.chromium.launch();
  let fail=0; const ok=(c,m)=>{ console.log((c?"ok   ":"FAIL ")+m); if(!c) fail++; };
  const open=async(ctx,q)=>{ const p=await ctx.newPage(), errs=[]; p.on("pageerror",e=>errs.push(e.message));
    await p.goto(URL+(q||"")); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300); return {p,errs}; };
  const settle=p=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>r()),80)));
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"omni-broker-"));
  /* the paper as laid out: every computed property of every element, less custom properties, motion and font smoothing
     (they move no line), and each element's height; papers() lists what differs between two such dumps */
  const pages=pdf=>(pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g)||[]).length;
  const paperDump=root=>{ const out=[]; const walk=(e,at)=>{ const cs=getComputedStyle(e), o={at,h:+e.getBoundingClientRect().height.toFixed(2)};
      for(let i=0;i<cs.length;i++){ const k=cs[i]; if(!/^(--|transition|animation|-webkit-font-smoothing)/.test(k)) o[k]=cs.getPropertyValue(k); }
      out.push(o); [...e.children].forEach((c,i)=>walk(c,at+">"+c.tagName.toLowerCase()+i)); }; walk(root,"rp"); return out; };
  const papers=(A,B,skip)=>{ const d=[]; if(A.length!==B.length) return [`${A.length} elements against ${B.length}`];
    A.forEach((a,i)=>{ for(const k in a) if(a[k]!==B[i][k]&&!(i===0&&skip&&skip.test(k))) d.push(`${a.at} ${k}: ${a[k]} | ${B[i][k]}`); }); return d; };
  const fileDump=async(html,w,media)=>{ if(!html) return {dump:[{at:"no file",h:NaN}],pa:0,pc:0}; const q=await ctx.newPage(); await q.setViewportSize({width:w,height:998}); await q.setContent(html); await q.emulateMedia({media});
    const r={dump:await q.evaluate(f=>eval(f)(document.querySelector(".rp")),paperDump.toString())};
    if(media==="print"){ r.pa=pages(await q.pdf({format:"Letter"})); r.pc=pages(await q.pdf({preferCSSPageSize:true})); } await q.close(); return r; };

  const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true});
  let {p,errs}=await open(ctx);
  ok(await p.evaluate(()=>getComputedStyle(document.getElementById("tl_saveas")).display==="none"&&/Unsaved/.test(document.getElementById("tl_deal").textContent)),
     "a fresh console is an unsaved valuation, with no 'Save as new'");
  const typeIn=async(sel,v,key)=>{ await p.click(sel); await p.keyboard.press("Control+A"); await p.keyboard.type(v,{delay:5}); await p.keyboard.press(key||"Enter"); await settle(p); };

  /* ---- the financing check ---- */
  let st=await p.evaluate(()=>{ const s=STATE.s, r=STATE.r, f=debtCheck(s,s.ask,OMNI_BROKER.state().fin,r.V), mf=maxFinanced(s,OMNI_BROKER.state().fin,r.V);
    const rows=[...document.querySelectorAll("#fintbl tbody tr")], cov=rows[rows.length-1], debt=rows.find(tr=>/Acquisition debt/.test(tr.textContent));
    return {want:covFmt(f),cells:[...cov.querySelectorAll("td b")].map(b=>b.textContent),cols:document.querySelectorAll("#fintbl thead th").length-1,head:document.querySelector("#fintbl thead").textContent,
      debt:debt?debt.textContent:"",max:document.getElementById("fin_max").textContent,price:money(mf.price),bind:mf.bind,who:document.getElementById("fin_who").textContent,
      pay:document.getElementById("fin_note").textContent}; });
  ok(st.cells.includes(st.want)&&st.cols>=1&&st.cols<=3&&/Your ask/.test(st.head),`the coverage row reads the model's coverage at your ask (${st.want}; ${st.cols} asks)`);
  ok(st.bind==="value"&&st.max.includes(st.price)&&/reaches the model value/.test(st.max)&&/over value/.test(st.debt),
     `the highest financed price keeps the debt within the model value (${st.price}), and an ask whose debt is above it is flagged`);
  ok(/^Individual buyers, about \d+% of the buyers of a business this size/.test(st.who)&&/payroll taxes and benefits/.test(st.pay)&&/rank by firm size is judgment/.test(st.pay),
     "the lede reads the buyer mix at this size; the pay note names the employer's costs and the judgment in the rank");
  await p.evaluate(()=>{ window.__renders=0; const r0=window.render; window.render=function(){ window.__renders++; return r0.apply(this,arguments); }; });
  await typeIn("#f_cash","20");
  st=await p.evaluate(()=>({cash:OMNI_BROKER.state().fin.cash,box:document.getElementById("f_cash").value,renders:window.__renders,
    pref:JSON.parse(localStorage.getItem("omni.prefs.v1")).fin.cash,head:[...document.querySelectorAll("#fintbl tbody tr")].find(tr=>/Buyer cash/.test(tr.textContent)).textContent}));
  ok(Math.abs(st.cash-.2)<1e-12&&st.box==="20%"&&st.pref===.2&&/20%/.test(st.head),`20 in buyer cash reads as 20%, redraws the table and is remembered (${st.box})`);
  ok(st.renders===0,`typing in the financing check does not re-run the console (${st.renders} renders)`);
  await typeIn("#f_cash","1");
  ok(await p.evaluate(()=>Math.abs(OMNI_BROKER.state().fin.cash-.01)<1e-12&&document.getElementById("f_cash").value==="1%"),"a 1 in a share box is 1%, as 2 is 2%");
  await typeIn("#f_note","abc","Tab");
  st=await p.evaluate(()=>({note:OMNI_BROKER.state().fin.note,box:document.getElementById("f_note").value,bad:document.getElementById("f_note").classList.contains("bad")}));
  ok(Math.abs(st.note-.05)<1e-12&&st.box==="5%"&&st.bad,"a rejected entry restores the previous value and stays marked");
  ok(await p.evaluate(()=>/<b>Equity:<\/b>/.test(document.getElementById("fin_note").innerHTML)&&/none/.test(document.getElementById("fin_max").textContent)
     &&/cannot be waived/.test(document.getElementById("fin_max").textContent)),"at 1% buyer cash the highest price is none: an initial acquisition's 10% equity cannot be waived");
  await typeIn("#f_cash","$5");
  ok(await p.evaluate(()=>document.getElementById("f_cash").classList.contains("bad")&&document.getElementById("f_cash").value==="1%"),"a dollar sign in a share box is refused, not read as 5%");
  ok(await p.evaluate(()=>document.getElementById("fintbl").classList.contains("wide")&&[...document.querySelectorAll(".rc-in")].every(e=>!e.hasAttribute("inputmode"))),
     "the financing table reserves the phone's scroll-chip strip; the worksheet's cells keep the full keyboard, with its minus sign");
  await p.selectOption("#f_type","expansion"); await settle(p);
  ok(await p.evaluate(()=>/meets 1\.15×|below 1\.15×/.test(document.getElementById("fintbl").textContent)&&/may reduce or eliminate it only when/.test(document.getElementById("fin_max").textContent)),
     "an expansion is tested at 1.15x, and its equity may be waived on SBA's conditions");
  await p.selectOption("#f_type","initial"); await typeIn("#f_cash","10%");
  await p.evaluate(()=>{ IN.ern=5e4; render(); }); await settle(p);
  ok(await p.evaluate(()=>{ const t=[...document.querySelectorAll("#fintbl tbody tr")].pop().textContent; return /none\s*nothing left after the new owner.s pay/.test(t)&&!/−\d/.test(t); }),
     "with nothing left after the new owner's pay, coverage reads none, not a negative ratio");
  await p.evaluate(()=>{ IN.ern=1.45e6; render(); }); await settle(p);
  await typeIn("#f_cash","90%"); await typeIn("#f_note","30%");
  st=await p.evaluate(()=>({note:document.getElementById("fin_note").textContent,max:document.getElementById("fin_max").textContent}));
  ok(/the note is cut/.test(st.note)&&/no loan/.test(st.max),"cash and a note set to more than the price: the note is cut, and no loan is needed");
  await typeIn("#f_note","90%"); await p.check("#f_standby"); await settle(p);
  ok(await p.evaluate(()=>{ const t=[...document.querySelectorAll("#fintbl tbody tr")].pop().textContent, n=document.getElementById("fin_note").textContent;
    return /\d\.\d\d×/.test(t)&&/no SBA minimum/.test(t)&&!/below|meets/.test(t)&&/paid on its own terms/.test(n); }),
     "a note marked standby with no SBA loan to stand behind is paid on its own terms, and its coverage is not graded against SBA's minimum");
  await typeIn("#f_cash","100%"); await typeIn("#f_note","0");
  ok(await p.evaluate(()=>{ const j=EQ.pending.get("eq_fs"), t=j?j[1]:EQ.last.get("eq_fs"); return /no debt/.test(t)&&!/infty|Infinity/.test(t); }),"with no payments the equation says so instead of printing infinity");
  await p.uncheck("#f_standby"); await typeIn("#f_cash","10%"); await typeIn("#f_note","5%");
  await p.evaluate(()=>{ IN.ask=STATE.r.V*STATE.s.rhoSell*1.003; render(); }); await settle(p);
  ok(await p.evaluate(()=>{ const h=[...document.querySelectorAll("#fintbl thead th")].map(t=>t.textContent); const i=h.indexOf("Your ask");
    return i>0&&document.querySelectorAll("#fintbl tbody tr:first-child td")[i-1].textContent.startsWith(money(IN.ask)); }),"an ask within 0.5% of the optimizer's keeps its own column, read at its own price");
  { const keepIN=await p.evaluate(()=>({...IN}));
    await p.evaluate(()=>{ IN.ern=5e6; IN.rev=2e7; IN.ask=2e7; render(); }); await typeIn("#f_cash","5%"); await typeIn("#f_note","0");
    st=await p.evaluate(()=>({max:document.getElementById("fin_max").textContent,cash:[...document.querySelectorAll("#fintbl tbody tr")].find(tr=>/Buyer cash/.test(tr.textContent)).textContent}));
    ok(/none/.test(st.max)&&/at every price below \$5\.56M\. Past \$5\.26M the SBA loan stays at the 7\(a\) maximum/.test(st.max)&&/rest of the price is buyer cash/.test(st.max)&&/which reaches 10% there/.test(st.max)&&!/under SBA/.test(st.cash),
       `past the 7(a) maximum the asks meet the equity minimum with buyer cash, and the box bounds the 5% structure's shortfall where buyer cash reaches 10% (${st.max.slice(36,160)})`);
    await p.evaluate(k=>{ Object.assign(IN,k); render(); },keepIN); await typeIn("#f_cash","10%"); await typeIn("#f_note","5%"); }
  /* r3-core-4: working capital financed in the loan whose payments alone break coverage is named, not the new owner's pay */
  { const keepIN=await p.evaluate(()=>({...IN}));
    await p.evaluate(()=>{ IN.ern=3e5; IN.rev=1.2e6; IN.ask=9e5; render(); }); await typeIn("#f_extra","1.5m");
    st=await p.evaluate(()=>({max:document.getElementById("fin_max").textContent,mf:maxFinanced(STATE.s,OMNI_BROKER.state().fin,STATE.r.V)}));
    ok(st.mf.price===0&&st.mf.bind==="coverage"&&/The working capital and closing costs financed in the loan, \$[\d.]+M, already take \$[\d.]+k a year of payments before any price/.test(st.max)
       &&/under SBA’s 1\.25× minimum/.test(st.max)&&!/does not cover a loan/.test(st.max),`working capital whose payments alone break coverage is named as what leaves no price (${st.max.slice(36,150)})`);
    await typeIn("#f_extra","none"); await p.evaluate(k=>{ Object.assign(IN,k); render(); },keepIN); }
  /* round 3: the share box echoes what the check reads; a sub-dollar amount is refused; the type's conditions under it;
     the equation without SBA's minimum when there is no loan, and entered amounts as their boxes show them */
  await typeIn("#f_cash","9.96");
  ok(await p.evaluate(()=>document.getElementById("f_cash").value==="9.96%"),"a share of 9.96% echoes as 9.96%, not the 10% it fails");
  await typeIn("#f_extra","0.40");
  ok(await p.evaluate(()=>document.getElementById("f_extra").classList.contains("bad")&&OMNI_BROKER.state().fin.extra===0),"an amount under a dollar is refused, not echoed as $0 and used");
  await typeIn("#f_cash","10%"); await typeIn("#f_extra","none");
  st=await p.evaluate(()=>({h:(document.getElementById("f_type_h")||{}).textContent||"",opts:[...document.querySelectorAll("#f_type option")].map(o=>o.textContent)}));
  ok(/under 24 months/.test(st.h)&&st.opts.join("|")==="Initial acquisition|Business expansion|Owner buyout","the transaction select shows short names, with the chosen type's conditions under it");
  await p.selectOption("#f_type","buyout"); await settle(p);
  ok(/for the last 24 months/.test(await p.evaluate(()=>(document.getElementById("f_type_h")||{}).textContent||"")),"choosing a type shows its conditions");
  await p.selectOption("#f_type","initial"); await typeIn("#f_draw","$91,450"); await typeIn("#f_capex","$1,450");
  /* the equation is typeset when it scrolls near or in idle time: read the formula the page set for it */
  ok(await p.evaluate(()=>{ const j=EQ.pending.get("eq_fs"), t=j?j[1]:EQ.last.get("eq_fs"); return /91\.5k/.test(t)&&/1\.45k/.test(t); }),"the equation echoes the entered pay and capital spending as their boxes do");
  await typeIn("#f_draw",""); await typeIn("#f_capex","none");
  await typeIn("#f_cash","60%"); await typeIn("#f_note","40%");
  ok(await p.evaluate(()=>{ const j=EQ.pending.get("eq_f"), t=j?j[1]:EQ.last.get("eq_f"); return /no SBA minimum/.test(t)&&!/\\ge/.test(t); }),"with no SBA loan the equation states no SBA minimum");
  /* an initial acquisition whose standby credit grows with the price: the box names the price it works from */
  await typeIn("#f_cash","6%"); await typeIn("#f_note","10%"); await p.check("#f_standby"); await typeIn("#f_extra","400k");
  st=await p.evaluate(()=>document.getElementById("fin_max").textContent);
  ok(/the structure works only from that price up/.test(st)&&/with the standby note’s credit/.test(st),`with working capital and a standby note the box names the price the structure works from (${st.slice(0,90)})`);
  await p.uncheck("#f_standby"); await typeIn("#f_cash","10%"); await typeIn("#f_note","5%"); await typeIn("#f_extra","none");
  /* the highest price shown passes when typed as the ask */
  st=await p.evaluate(()=>document.querySelector("#fin_max .fin-big").textContent);
  await p.evaluate(t=>{ IN.ask=parseAmount(t); render(); },st); await settle(p);
  ok(await p.evaluate(()=>{ const h=[...document.querySelectorAll("#fintbl thead th")].map(t=>t.textContent), i=h.findIndex(t=>/Your ask/.test(t)), rows=[...document.querySelectorAll("#fintbl tbody tr")];
    const debt=rows.find(tr=>/Acquisition debt/.test(tr.textContent)).querySelectorAll("td")[i-1].textContent, cov=rows[rows.length-1].querySelectorAll("td")[i-1].textContent;
    return i>0&&!/over value/.test(debt)&&/meets/.test(cov); }),`the highest price the box shows (${st}) passes when typed as the ask`);
  await p.evaluate(()=>{ IN.ask=3.24e6; render(); }); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("rp-page").media==="not all"),"the report's Letter page size is off while the report is closed: printing the console keeps the reader's paper");

  /* ---- the worksheet ---- */
  await p.click("#tl_recast"); await settle(p);
  ok(await p.evaluate(()=>!document.getElementById("recast").hidden&&document.activeElement.id==="rc_ent"&&document.documentElement.classList.contains("dlg-open")),"the worksheet opens as a dialog with focus inside");
  await p.keyboard.press("Escape"); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("recast").hidden&&document.activeElement.id==="tl_recast"),"Escape closes it and returns focus to its button");
  await p.click("#tl_recast"); await settle(p);
  const put=async(k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await p.click(sel); await p.keyboard.press("Control+A"); await p.keyboard.type(v,{delay:5}); await p.keyboard.press("Tab"); };
  ok(await p.evaluate(()=>{ const e=document.querySelector('.rc-in[data-k="owner"][data-y="0"]'), d=document.getElementById(e.getAttribute("aria-describedby")||"x");
    return e.getAttribute("aria-label")==="Add: One working owner's salary or wages, most recent year"&&!!d&&/Compensation of officers/.test(d.textContent)
      &&document.querySelector('.rc-in[data-k="nonop"][data-y="1"]').getAttribute("aria-label").startsWith("Less: "); }),
     "each cell's name says whether it adds or deducts, and points to the source's line");
  /* the reason Use is off, and Clear keeping the growth box */
  await put("rev",0,"1,000,000"); await put("ni",0,"500"); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("rc_use").disabled&&/needs SDE of at least \$1k/.test(document.getElementById("rc_sum").textContent)),"'Use in the console' says why it is off");
  await p.uncheck("#rc_grw"); await p.click("#rc_clear"); await settle(p);
  ok(await p.evaluate(()=>!document.getElementById("rc_grw").checked&&!document.querySelector('.rc-in[data-k="rev"][data-y="0"]').value),"Clear empties the years and keeps the growth box as set");
  await p.check("#rc_grw");
  { const card=await p.locator("#recast .ovl-card").boundingBox(); await p.mouse.move(card.x-8,card.y+40); await p.mouse.down(); await p.mouse.move(card.x+60,card.y+60,{steps:3}); await p.mouse.up(); await settle(p); }
  ok(await p.evaluate(()=>!document.getElementById("recast").hidden),"a press on the backdrop that ends on the card leaves the worksheet open");
  await put("rev",0,"6,200,000"); await put("ni",0,"512,000"); await put("owner",0,"180000"); await put("dep",0,"96k"); await put("int",0,"$41,000");
  await put("once",0,"35,000"); await put("nonop",0,"(12,000)"); await put("rev",1,"5.7m"); await put("ni",1,"470k"); await put("owner",1,"175k"); await settle(p);
  st=await p.evaluate(()=>({s0:document.getElementById("rc_s0").textContent,s1:document.getElementById("rc_s1").textContent,
    nonop:document.querySelector('.rc-in[data-k="nonop"][data-y="0"]').value,sum:document.getElementById("rc_sum").textContent,dis:document.getElementById("rc_use").disabled}));
  ok(st.s0==="$852,000"&&st.s1==="$645,000"&&st.nonop==="−$12,000"&&/still deducted/.test(st.sum)&&/grew 8\.8%/.test(st.sum)&&!st.dis,
     `the worksheet sums each year; a deduction typed as (12,000) deducts and says so (${st.s0}, ${st.s1})`);
  /* a rejected entry goes back to what the cell held when focused */
  await put("owner",1,"9x"); await settle(p);
  st=await p.evaluate(()=>{ const e=document.querySelector('.rc-in[data-k="owner"][data-y="1"]'); return {v:e.value,bad:e.classList.contains("bad"),ws:OMNI_BROKER.state().ws.years[1].owner,s1:document.getElementById("rc_s1").textContent}; });
  ok(st.v==="$175,000"&&st.bad&&st.ws===175000&&st.s1==="$645,000",`a rejected entry restores the value it replaced, not a keystroke's prefix (${st.v})`);
  await put("dep",2,"12/day"); await settle(p);
  ok(await p.evaluate(()=>{ const e=document.querySelector('.rc-in[data-k="dep"][data-y="2"]'); return e.value===""&&e.classList.contains("bad")&&OMNI_BROKER.state().ws.years[2].dep===undefined; }),"a unit the worksheet does not take is refused");
  await p.focus('.rc-in[data-k="xowner"][data-y="2"]'); await p.keyboard.press("Enter");
  const nx1=await p.evaluate(()=>document.activeElement.dataset.k+document.activeElement.dataset.y);
  await p.focus('.rc-in[data-k="xowner"][data-y="0"]'); await p.keyboard.press("Enter");
  const nx2=await p.evaluate(()=>document.activeElement.dataset.k+document.activeElement.dataset.y);
  ok(nx1==="rev0"&&nx2==="rev1",`Enter at the foot of a column goes to the top of the next, and from the last column back to the first (${nx1}, ${nx2})`);
  await p.click("#rc_use"); await settle(p); await p.waitForTimeout(300);
  st=await p.evaluate(()=>({ern:STATE.s.ern,rev:STATE.s.rev,grw:STATE.s.grw,ask:STATE.s.ask,msg:document.getElementById("tl_msg").textContent,closed:document.getElementById("recast").hidden}));
  ok(st.ern===852000&&st.rev===6.2e6&&Math.abs(st.grw-(6.2/5.7-1))<1e-9&&st.ask===3.24e6&&st.closed&&/From the worksheet/.test(st.msg),
     `'Use in the console' sets SDE, revenue and growth and leaves the ask (SDE ${st.ern}, growth ${(st.grw*100).toFixed(1)}%)`);

  /* ---- the report before saving: what is typed there goes with the deal saved next ---- */
  await p.click("#tl_report"); await settle(p);
  await p.fill("#rp_biz","Lakeside <b>Dental</b>"); await p.fill("#rp_for","Dr. Ortiz"); await p.locator("#rp_for").blur(); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("rp-page").media==="print"),"while the report is open its page size applies to printing");
  await p.click("#rp_close"); await settle(p);

  /* ---- saving the deal ---- */
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; return {n:JSON.parse(localStorage.getItem("omni.deals.v1")).length,deal:document.getElementById("tl_deal").textContent,
    saveas:getComputedStyle(document.getElementById("tl_saveas")).display,ws:!!d.ws,biz:d.business,pf:d.preparedFor,auto:d.autoName}; });
  ok(st.n===1&&/Medical or dental practice, \$852k SDE/.test(st.deal)&&st.saveas!=="none"&&st.ws&&st.auto,`Save deal stores it with its worksheet and names it (${st.deal.trim()})`);
  ok(st.biz==="Lakeside <b>Dental</b>"&&st.pf==="Dr. Ortiz","the business and recipient typed in the report before saving go with the new deal");
  /* the change renders on the next frame, a full console render: wait for the mark rather than a fixed time */
  await p.evaluate(()=>{ const g=document.getElementById("i_gm"); g.value=70; g.dispatchEvent(new Event("input",{bubbles:true})); });
  await p.waitForFunction(()=>/unsaved changes/.test(document.getElementById("tl_deal").textContent),null,{timeout:8000}).catch(()=>{});
  ok(/unsaved changes/.test(await p.evaluate(()=>document.getElementById("tl_deal").textContent)),"changing an input marks unsaved changes");
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>({deal:document.getElementById("tl_deal").textContent,gm:JSON.parse(localStorage.getItem("omni.deals.v1"))[0].inputs.gm}));
  ok(!/unsaved/.test(st.deal)&&Math.abs(st.gm-.7)<1e-12,"updating saves the change");
  await typeIn("#f_note","6%");
  ok(/unsaved changes/.test(await p.evaluate(()=>document.getElementById("tl_deal").textContent)),"changing the financing structure marks unsaved changes too");
  await p.click("#tl_save"); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1"))[0].fin.note===.06&&!/unsaved/.test(document.getElementById("tl_deal").textContent)),"and 'Save changes' keeps the structure");
  await typeIn("#f_note","5%"); await p.click("#tl_save"); await settle(p);
  await p.click("#tl_recast"); await settle(p); await put("ni",0,"530,000"); await settle(p); await p.keyboard.press("Escape"); await settle(p);
  ok(/unsaved changes/.test(await p.evaluate(()=>document.getElementById("tl_deal").textContent)),"editing the deal's own worksheet marks unsaved changes");
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; return {ni:d.ws&&d.ws.years[0].ni,ern:STATE.s.ern,deal:document.getElementById("tl_deal").textContent}; });
  ok(st.ni===530000&&st.ern===852000&&!/unsaved/.test(st.deal),"'Save changes' keeps the deal's own worksheet, edited without Use, and leaves the console's SDE");
  await p.click("#tl_recast"); await settle(p); await put("ni",0,"512,000"); await settle(p); await p.keyboard.press("Escape"); await settle(p);
  await p.click("#tl_save"); await settle(p);

  /* ---- the seller report ---- */
  await p.click("#tl_report"); await settle(p);
  await p.fill("#rp_broker","Pat Lee"); await p.fill("#rp_firm","Main Street Advisors"); await p.locator("#rp_firm").blur(); await settle(p);
  st=await p.evaluate(()=>({t:document.getElementById("rp_paper").textContent,html:document.getElementById("rp_paper").innerHTML,on:document.documentElement.classList.contains("rp-on"),biz:document.getElementById("rp_biz").value}));
  ok(st.on&&st.biz==="Lakeside <b>Dental</b>"&&st.t.includes("Lakeside <b>Dental</b>")&&!st.html.includes("<b>Dental</b>")&&/Earnings basis/.test(st.t)&&/\$852k/.test(st.t)&&/not an appraisal/.test(st.t)
     &&/fitted\s*× judgment/.test(st.t)&&/published data\s*× judgment/.test(st.t),"the report shows what was typed as text, the worksheet's earnings basis and the console's compound badges");
  await p.emulateMedia({media:"print"}); let pdf=await p.pdf({format:"Letter"}); await p.emulateMedia({media:"screen"});
  ok(pages(pdf)===1,`printed, the report is one Letter page (${pages(pdf)})`);
  /* the tallest report the reviewers found (round 2): three asks, every optional line, the market pay, all six earnings
     notes, an extrapolated value, an equity shortfall with working capital and four near-limit names */
  await p.evaluate(()=>{ const s={ind:"prof",rev:1008677.65,ern:882463.28,ask:2929000,grw:.02,gm:.48,rec:.54,cc:.18,ret:.54,plt:.52,own:.42,mgt:.36,fin:.14,yrs:6,buyers:95,
      st:"CA",franchise:false,budget:1e5,lamT:2950,theta:.72};
    const R=recastSDE({entity:"schc",weight:"w321",years:[{rev:1068011.63,ni:356003.88,owner:35600.39,ptax:5340.06,tax:17800.19,once:160201.74,pers:53400.58,oth:219418.38,nonop:-8900.1},
      {rev:979010.66,ni:1077588.76},{rev:890009.69,ni:623006.78}]});
    const D=reportData(s,{fin:{type:"expansion",cash:0,note:.1,extra:264739,capex:12345,draw:null},recast:R,calib:sampleSummary([1.04,.97,1.1,1.02,.99,1.06],false,.04),date:"September 30, 2026"});
    const N=["Lakeside Family Dental Group of Northern Westchester County, a professional corporation doing business as Lakeside Smile",
      "Dr. Jonathan Vanderbilt-Montgomery and Dr. Maria Rodriguez-Castillo, co-owners, together with their trustees and counsel",
      "Patricia Lee-Vanderwaal, Certified Business Intermediary and Mergers and Acquisitions Master Intermediary, Sr. Advisor",
      "Main Street Business Advisors and Transaction Services of the Greater Hudson Valley and Southern Connecticut Region LLC"];
    document.getElementById("rp_paper").innerHTML=reportHTML(D,{business:N[0],preparedFor:N[1],broker:N[2],firm:N[3]}); window.__worst=D; });
  st=await p.evaluate(()=>{ const D=window.__worst, t=document.getElementById("rp_paper").textContent, a=document.querySelector("#rp_paper .rp");
    return {rows:document.querySelectorAll("#rp_paper .rp-t tbody tr:not(.rp-sub)").length,ext:/Extrapolated/.test(t),cal:/Track record/.test(t),eq:/Equity:/.test(t),
      notes:["documentation","fell more than 15%","counts it twice","payroll tax on the owner","income tax that","still deducted"].filter(x=>t.includes(x)).length,
      mkt:/market pay/.test(t),wide:a.scrollWidth<=a.clientWidth+1}; });
  { const vp=p.viewportSize(); await p.setViewportSize({width:739,height:998}); await p.emulateMedia({media:"print"}); await settle(p);
    st.h=await p.evaluate(()=>document.querySelector("#rp_paper .rp").getBoundingClientRect().height);
    st.pa=pages(await p.pdf({format:"Letter"})); st.pc=pages(await p.pdf({preferCSSPageSize:true}));
    await p.emulateMedia({media:"screen"}); await p.setViewportSize(vp); await settle(p); }
  ok(st.rows===3&&st.ext&&st.cal&&st.eq&&st.notes===6&&st.mkt&&st.wide&&st.pa===1&&st.pc===1&&st.h<=965,
     `the tallest report (three asks, every optional line, all six notes, 120-character names) prints on one Letter page with room to spare (${st.pa}/${st.pc} pages; ${Math.round(st.h)} of 998 px)`);
  /* r3-report-4: the page's own rules stop at the paper, so the preview and the print are the downloaded file */
  { const fileW=await p.evaluate(()=>typeof reportFileHTML!=="function"?"":reportFileHTML(window.__worst,{business:"Lakeside Family Dental Group of Northern Westchester County, a professional corporation doing business as Lakeside Smile",
      preparedFor:"Dr. Jonathan Vanderbilt-Montgomery and Dr. Maria Rodriguez-Castillo, co-owners, together with their trustees and counsel",
      broker:"Patricia Lee-Vanderwaal, Certified Business Intermediary and Mergers and Acquisitions Master Intermediary, Sr. Advisor",
      firm:"Main Street Business Advisors and Transaction Services of the Greater Hudson Valley and Southern Connecticut Region LLC"}));
    const vp=p.viewportSize(); const diff={};
    for(const [w,media] of [[739,"print"],[1440,"screen"]]){
      await p.setViewportSize({width:w,height:998}); await p.emulateMedia({media}); await settle(p);
      const A=await p.evaluate(f=>eval(f)(document.querySelector("#rp_paper .rp")),paperDump.toString()), F=await fileDump(fileW,w,media);
      /* on screen the paper is centred in its column, the overlay's 8.5in or the file's window: its own side margins differ */
      diff[media]={d:papers(A,F.dump,media==="screen"?/^margin-(left|right|inline-start|inline-end)$/:null),h:F.dump[0].h,pa:F.pa,pc:F.pc}; }
    await p.emulateMedia({media:"screen"}); await p.setViewportSize(vp); await settle(p);
    ok(!diff.print.d.length&&!diff.screen.d.length,`the preview and the print lay out the paper exactly as the downloaded file does: every property of every element, in print and on screen (${diff.print.d.length+diff.screen.d.length} differ${diff.print.d.length?"; "+diff.print.d.slice(0,3).join("; "):""}${diff.screen.d.length?"; "+diff.screen.d.slice(0,3).join("; "):""})`);
    ok(diff.print.pa===1&&diff.print.pc===1&&diff.print.h<=965,`the tallest report's downloaded file prints on one Letter page with room to spare (${diff.print.pa}/${diff.print.pc} pages; ${Math.round(diff.print.h)} of 998 px)`); }
  await p.click("#rp_close"); await settle(p);
  /* a report opened straight from a money box reads the value just typed there */
  await p.click("#v_ask"); await p.keyboard.press("Control+A"); await p.keyboard.type("3.3M"); await p.click("#tl_report"); await settle(p);
  ok(await p.evaluate(()=>/Your ask\s*\$3\.30M/.test(document.getElementById("rp_paper").textContent)),"a report opened straight from a money box is built on the value just typed");
  const [dl]=await Promise.all([p.waitForEvent("download"),p.click("#rp_dl")]);
  const fpath=path.join(tmp,dl.suggestedFilename()); await dl.saveAs(fpath); const file=fs.readFileSync(fpath,"utf8");
  ok(file===await p.evaluate(()=>typeof OMNI_BROKER.reportFile==="function"?OMNI_BROKER.reportFile():null)&&file.includes(await p.evaluate(()=>RP_CSS))&&!file.includes("#rp_paper"),
     "the download is reportFileHTML of the report showing, with the paper's sheet as written (the layout comparison above reads that function)");
  ok(/^valuation-lakeside-b-dental-b-\d{4}-\d{2}-\d{2}\.html$/.test(dl.suggestedFilename())&&file.startsWith("<!DOCTYPE html>")&&file.includes("all:revert")&&/@media print\{body\{background:#fff\}@page\{size:letter/.test(file)
     &&file.includes("Lakeside &lt;b&gt;Dental&lt;/b&gt;")&&!/<script|https?:\/\//i.test(file),`the download is one self-contained page that prints on Letter, with no script or link (${dl.suggestedFilename()})`);
  await p.click("#rp_close"); await settle(p);
  ok(await p.evaluate(()=>{ const P=JSON.parse(localStorage.getItem("omni.prefs.v1")); return P.broker==="Pat Lee"&&P.firm==="Main Street Advisors"&&!document.documentElement.classList.contains("rp-on")&&document.getElementById("rp-page").media==="not all"; }),
     "the broker and firm are remembered for the next report");
  await p.evaluate(()=>{ IN.ask=3.24e6; render(); }); await settle(p); await p.click("#tl_save"); await settle(p);

  /* ---- the Deals tab ---- */
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>!document.getElementById("view-deals").hidden&&document.getElementById("view-console").hidden&&document.documentElement.dataset.tab==="deals"
     &&document.querySelectorAll("#dl_tbl tbody tr[data-id]").length===1),"the Deals tab lists the saved deal");
  await p.click("#dl_tbl .dl-name"); await settle(p);
  await p.selectOption('#dl_form select[name="status"]',"closed");
  await p.fill('#dl_form input[name="listPrice"]',"3.4M"); await p.fill('#dl_form input[name="listDate"]',"2025-09-02");
  await p.fill('#dl_form input[name="salePrice"]',"abc"); await p.fill('#dl_form input[name="closeDate"]',"2026-05-15");
  await p.click('#dl_form button[type="submit"]'); await settle(p);
  st=await p.evaluate(()=>({d:JSON.parse(localStorage.getItem("omni.deals.v1"))[0],msg:document.getElementById("dl_form_msg").textContent,
    bad:document.querySelector('#dl_form input[name="salePrice"]').classList.contains("bad")}));
  ok(st.d.status==="closed"&&st.d.listPrice===3.4e6&&st.d.listDate==="2025-09-02"&&st.d.salePrice===null&&st.bad&&/marked fields: Sale price\./.test(st.msg)&&/sale price/.test(st.msg),
     `a bad sale price is refused and named as the form names it; the rest saves, with a note on what the record still needs (${st.msg.slice(0,60)})`);
  await p.fill('#dl_form input[name="salePrice"]',"3.1M"); await p.fill('#dl_form input[name="name"]',"=HYPERLINK(\"x\")"); await p.click('#dl_form button[type="submit"]'); await settle(p);
  st=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; const P=dealPredict(d);
    return {sale:d.salePrice,auto:d.autoName,row:document.querySelector("#dl_tbl tbody tr").textContent,ratio:(d.salePrice/P.pExp).toFixed(2)+"×"}; });
  ok(st.sale===3.1e6&&st.auto===false&&st.row.includes(st.ratio),`the table shows the sale against the model's expected price at the listing (${st.ratio}); a typed name stays`);
  /* a duplicate is a new valuation, so no outcome is counted twice */
  await p.click('#dl_form button[data-act="dup"]'); await settle(p);
  st=await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")); return {n:D.length,c:D[0],track:document.getElementById("dl_track").textContent}; });
  ok(st.n===2&&st.c.status==="valuing"&&st.c.salePrice===null&&st.c.listPrice===null&&st.c.listDate===null&&/ \(copy\)$/.test(st.c.name)&&/1 closed with a sale price/.test(st.track),
     "a duplicate starts as a new valuation: its listing and outcome are empty and the record still counts one sale");
  /* the two-press delete; a redraw in between disarms it */
  await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(()=>/Press again/.test(document.querySelector('#dl_form button[data-act="del"]').textContent)),"delete asks for a second press");
  await p.click('#dl_form button[type="submit"]'); await settle(p); await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).length===2&&/Press again/.test(document.querySelector('#dl_form button[data-act="del"]').textContent)),
     "after the form redraws, one press only arms delete again");
  await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).length===1),"the second press deletes");
  /* exports */
  const [dj]=await Promise.all([p.waitForEvent("download"),p.click("#dl_json")]); const jp=path.join(tmp,"deals.json"); await dj.saveAs(jp);
  const J=JSON.parse(fs.readFileSync(jp,"utf8"));
  ok(J.format==="omni.deals"&&J.version===1&&J.deals.length===1&&J.deals.every(d=>d.inputs&&d.inputs.ind==="medical"),"Export (JSON) writes every deal with its inputs");
  const [dc]=await Promise.all([p.waitForEvent("download"),p.click("#dl_csv")]); const cp=path.join(tmp,"deals.csv"); await dc.saveAs(cp);
  const csv=fs.readFileSync(cp,"utf8").split("\r\n");
  ok(csv[0].startsWith("id,name,status,industry")&&csv[0].includes("cash_at_close_share")&&csv[0].includes("model_expected_price_at_list_or_ask")&&csv.length===3
     &&/^d[0-9a-z]+,"?'=HYPERLINK/.test(csv[1])&&/,Medical or dental/.test(csv[1]),"Export (CSV) writes a row a deal, names what each model column was read at, and defuses a formula-like name");
  /* import: a newer and an older copy of the deal here, three new closed deals (one without a sale price, one with an impossible
     date), an invalid record, inherited keys, and stray types */
  const ex=J.deals[0], future=new Date(Date.now()+864e5).toISOString(), tdy=new Date().toISOString().slice(0,10);
  const newer={...ex,name:"Imported update",updated:future}, older={...ex,name:"Stale",updated:"2020-01-01T00:00:00.000Z"};
  const fresh={...ex,id:"dimported1",name:"Imported new deal",listDate:"2025-03-03",closeDate:"2025-12-01"}, fresh2={...ex,id:"dimported2",name:"Second import",salePrice:ex.salePrice*1.05,listDate:"2026-02-31"};
  const fresh3={...ex,id:"dimported3",name:"Closed, no price",salePrice:null,listDate:"2025-01-10",closeDate:"2025-11-20"};
  const bad={id:"x",inputs:{ind:"nope"}}, proto={...ex,id:"dproto",inputs:{...ex.inputs,ind:"constructor"}};
  const odd={...ex,id:"dodd",name:"Odd keys",status:"__proto__",fin:{...ex.fin,type:"constructor"},ws:null,inputs:{...ex.inputs,st:"toString",ind:"medical"},buyers:true,offers:2.5};
  const ip=path.join(tmp,"import.json"); fs.writeFileSync(ip,JSON.stringify({format:"omni.deals",version:1,deals:[newer,older,fresh,fresh2,fresh3,bad,proto,odd]}));
  await p.setInputFiles("#dl_file",ip); await p.waitForTimeout(900);
  st=await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")), o=D.find(d=>d.id==="dodd"), f2=D.find(d=>d.id==="dimported2");
    return {names:D.map(d=>d.name),msg:document.getElementById("dl_msg").textContent,odd:o?[o.status,o.fin.type,o.inputs.st,o.buyers,o.offers].join():null,f2date:f2?f2.listDate:"missing",
      track:document.getElementById("dl_track").textContent}; });
  ok(st.names.length===5&&st.names.includes("Imported update")&&st.names.includes("Imported new deal")&&!st.names.includes("Stale")&&/4 new deals and updated 1; 3 skipped/.test(st.msg),
     `import adds new deals, takes newer copies and skips older, invalid and hostile ones (${st.msg})`);
  ok(st.odd==="valuing,initial,,,"&&st.f2date===null,`inherited keys, a stray true, a fractional count and an impossible date are cleaned away (${st.odd}; ${st.f2date})`);
  ok(/Sale price ÷ the model’s expected price\s*\d\.\d\d×/.test(st.track)&&/3 closed deals; 90% interval/.test(st.track)&&/Listing to close ÷ the model’s median\s*\d\.\d\d×/.test(st.track)
     &&/3 closed deals with both dates/.test(st.track),"with three closed deals the price record appears; the time record counts a closed deal without a sale price");
  await p.check("#dl_calib"); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.prefs.v1")).calib===true),"the track-record opt-in is remembered");
  /* a date in an implausible year is refused by name */
  await p.click('#dl_tbl tr:has(.dl-name:text("Imported new deal")) .dl-name'); await settle(p);
  await p.fill('#dl_form input[name="listDate"]',"1900-01-01"); await p.click('#dl_form button[type="submit"]'); await settle(p);
  ok(await p.evaluate(()=>/Listing date/.test(document.getElementById("dl_form_msg").textContent)&&JSON.parse(localStorage.getItem("omni.deals.v1")).find(d=>d.id==="dimported1")?.listDate==="2025-03-03"),
     "a listing date in 1900 is refused by name and the saved date kept");
  /* open a deal into the console */
  await p.click('.tab[data-v="console"]'); await p.waitForTimeout(1500);
  await p.evaluate(()=>{ IN.ern=5e5; render(); }); await settle(p);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  const want=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")).find(x=>x.name==="Imported new deal"); return d.inputs; });
  await p.click('#dl_tbl tr:has(.dl-name:text("Imported new deal")) button[data-act="open"]'); await p.waitForTimeout(1800);
  st=await p.evaluate(()=>({ern:STATE.s.ern,gm:STATE.s.gm,vis:!document.getElementById("view-console").hidden,deal:document.getElementById("tl_deal").textContent}));
  ok(st.vis&&st.ern===want.ern&&Math.abs(st.gm-want.gm)<1e-12&&/Imported new deal/.test(st.deal)&&!/unsaved/.test(st.deal),
     `opening a deal puts its inputs in the console, with nothing unsaved (SDE ${st.ern} for ${want.ern}; ${st.deal.trim()})`);
  ok(await p.evaluate(()=>!document.getElementById("tl_cal").hidden&&/Your record/.test(document.getElementById("tl_cal").textContent)&&/expected price/.test(document.getElementById("tl_cal").textContent)),
     "the opted-in price record shows beside the console");
  /* a deal without a worksheet opens with an empty one, not the last deal's */
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  await p.click('#dl_tbl tr:has(.dl-name:text("Odd keys")) button[data-act="open"]'); await p.waitForTimeout(1800);
  ok(await p.evaluate(()=>OMNI_BROKER.state().ws.years.every(y=>!Object.keys(y).length)&&document.getElementById("f_type").value==="initial"&&!window.__brokerErr&&!/unsaved/.test(document.getElementById("tl_deal").textContent)),
     "a deal saved without a worksheet opens with an empty one, and its cleaned type draws the financing check");
  /* an automatic name follows the deal's SDE; reset leaves the deal as saved */
  await p.evaluate(()=>{ IN.ern=9e5; render(); }); await settle(p); await p.click("#tl_save"); await settle(p);
  ok(await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")).find(x=>x.id==="dodd"); return d.name==="Odd keys"&&d.inputs.ern===9e5; }),"a typed name stays when the deal's SDE changes");
  await p.click("#reset"); await p.waitForTimeout(800);
  st=await p.evaluate(()=>({deal:document.getElementById("tl_deal").textContent,msg:document.getElementById("tl_msg").textContent,cur:OMNI_BROKER.state().cur,draft:OMNI_BROKER.state().draft}));
  ok(st.cur===null&&/Unsaved valuation/.test(st.deal)&&/unchanged in the Deals tab/.test(st.msg)&&st.draft.business==="","reset leaves the deal as saved, out of reach of a later save, and starts the report fields empty");
  await p.click("#tl_save"); await settle(p);
  ok(await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; return d.autoName&&/, \$\d/.test(d.name)&&d.business===""; }),"a new deal after reset is named for its own SDE");
  /* the Data tab: the broker section is last and has its own place; Still judgment keeps its own */
  await p.click('.tab[data-v="data"]'); await p.waitForTimeout(2500);
  st=await p.evaluate(()=>{ const S=[...document.querySelectorAll("#dataviews>section.sec")], last=S[S.length-1], still=S.find(s=>/^Still judg/.test(s.querySelector("h2").textContent));
    const idx=[...document.querySelectorAll("a[data-to]")].map(a=>a.getAttribute("data-to"));
    return {n:S.length,last:last.id+"|"+last.getAttribute("data-v8d")+"|"+/^Broker tools/.test(last.querySelector("h2").textContent),still:still&&still.id,
      hue:getComputedStyle(last).getPropertyValue("--hue").trim(),stillHue:still&&getComputedStyle(still).getPropertyValue("--hue").trim(),idx}; });
  ok(st.n===8&&st.last==="d-broker|broker|true"&&st.still==="d-still"&&/111 242 220/.test(st.hue)&&/255 142 122/.test(st.stillHue)
     &&(st.idx.length===0||st.idx.includes("d-broker")&&st.idx.includes("d-still")),
     `the Data tab's broker section comes last with its own id and hue; Still judgment keeps d-still and its coral (${st.last}; ${st.still}; ${st.hue}; ${st.stillHue})`);
  ok(errs.length===0,"no page errors: "+errs.slice(0,3).join(" | "));
  /* a stored record this page cannot read is kept and written back; a repeated id gets a new one */
  await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")); D.push({format:"from a later version",inputs:{ind:"nope"}}); D.push({...D[0]}); localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  st=await p.evaluate(()=>{ const S=OMNI_BROKER.state(), ids=S.deals.map(d=>d.id); return {n:S.deals.length,kept:S.kept.length,uniq:new Set(ids).size===ids.length,broker:S.prefs.broker,cash:document.getElementById("f_cash").value}; });
  ok(st.n===7&&st.kept===1&&st.uniq&&st.broker==="Pat Lee"&&st.cash==="10%",`a reload keeps the deals and preferences, gives a repeated id a new one and keeps an unreadable record (${st.n} deals, ${st.kept} kept)`);
  await p.click("#tl_save"); await settle(p); await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).some(d=>d.format==="from a later version")&&/cannot read/.test(document.getElementById("dl_store").textContent)),
     "the unreadable record survives the next save, and the Deals tab says so");
  /* r3-core-1: two stored deals that share an id both survive the next save: the first keeps the id, the second its own */
  const dupId=await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")), a=D.find(d=>d.inputs&&d.id);
    a.name="Alpha Dental (first)"; a.updated="2025-03-01T00:00:00.000Z";
    D.push({...a,name:"Beta Vet (second)",status:"listed",updated:"2025-04-01T00:00:00.000Z"}); localStorage.setItem("omni.deals.v1",JSON.stringify(D)); return a.id; });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")); return {a:D.filter(d=>d.name==="Alpha Dental (first)").map(d=>d.id),b:D.filter(d=>d.name==="Beta Vet (second)").map(d=>d.id)}; });
  ok(st.a.length===1&&st.b.length===1&&st.a[0]===dupId&&st.b[0]!==dupId,`two stored deals that share an id both survive the next save, the newer no longer read as a copy of the older (${JSON.stringify(st)})`);
  await p.evaluate(()=>localStorage.setItem("omni.deals.v1","{not json"));
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>localStorage.getItem("omni.deals.v1.unreadable")==="{not json"&&/could not be read/.test(document.getElementById("dl_store").textContent)),"a stored list that is not JSON is copied aside before anything replaces it");
  await p.close();

  /* ---- storage blocked (a private window): the page works and says so ---- */
  const c2=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  await c2.addInitScript(()=>{ Storage.prototype.setItem=function(){ throw new Error("QuotaExceededError"); }; });
  ({p,errs}=await open(c2));
  await p.click("#tl_save"); await settle(p);
  ok(/not keeping data/.test(await p.evaluate(()=>document.getElementById("tl_msg").textContent))&&errs.length===0,"with storage blocked, saving says it will not last, and nothing breaks");
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(/not keeping data/.test(await p.evaluate(()=>document.getElementById("dl_store").textContent)),"the Deals tab says so too");
  await c2.close();

  /* ---- a phone: no sideways scrolling on any of it, long names wrap ---- */
  const c3=await b.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});
  ({p,errs}=await open(c3));
  const wide=async()=>p.evaluate(()=>document.documentElement.scrollWidth);
  ok(await wide()<=390,"390px console with the toolbar and financing check: no sideways scroll");
  await p.click("#tl_recast"); await settle(p);
  ok(await wide()<=390&&await p.evaluate(()=>{ const t=document.querySelector("#recast .tw"); return t.scrollWidth<=t.clientWidth+1; }),"390px worksheet: three years fit without scrolling");
  await p.keyboard.press("Escape"); await p.click("#tl_report"); await settle(p);
  ok(await wide()<=390,"390px report: no sideways scroll");
  await p.keyboard.press("Escape"); await p.click("#tl_save"); await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  await p.click("#dl_tbl .dl-name"); await settle(p); await p.fill('#dl_form input[name="name"]',"N".repeat(120)); await p.click('#dl_form button[type="submit"]'); await settle(p);
  st=await p.evaluate(()=>{ const r=e=>e.getBoundingClientRect().right; return {page:document.documentElement.scrollWidth,card:r(document.querySelector("#dl_tbl tbody tr")),
    name:r(document.querySelector("#dl_tbl .dl-name")),head:r(document.getElementById("dl_edit_t")),cards:getComputedStyle(document.querySelector("#dl_tbl tbody tr")).display}; });
  ok(st.page<=390&&st.card<=390&&st.name<=390&&st.head<=390&&st.cards==="block",`390px Deals tab: each deal is a card, and a 120-letter name wraps inside it (${Math.round(st.card)}, ${Math.round(st.head)})`);
  await p.click('.tab[data-v="console"]'); await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>{ const e=document.querySelector(".tools-deal .tl-n"); return !e||e.getBoundingClientRect().right<=390; })&&await wide()<=390,"the toolbar wraps the long name too");
  ok(errs.length===0,"no page errors on a phone: "+errs.slice(0,3).join(" | "));
  await c3.close();
  await b.close();

  /* ---- real scrollbars (Playwright hides them by default): a press on the dialog's scrollbar does not close it ---- */
  const b2=await pw.chromium.launch({ignoreDefaultArgs:["--hide-scrollbars"]});
  const c4=await b2.newContext({viewport:{width:1280,height:640},reducedMotion:"reduce"});
  ({p,errs}=await open(c4));
  await p.click("#r_recast"); await settle(p);
  st=await p.evaluate(()=>{ const o=document.getElementById("recast"), r=o.getBoundingClientRect(); return {sb:o.offsetWidth-o.clientWidth,x:r.left+o.clientWidth+Math.max(1,(o.offsetWidth-o.clientWidth)/2),y:r.top+200}; });
  await p.mouse.move(st.x,st.y); await p.mouse.down(); await p.mouse.move(st.x,st.y+120,{steps:4}); await p.mouse.up(); await settle(p);
  ok(st.sb>0&&await p.evaluate(()=>!document.getElementById("recast").hidden),`dragging the worksheet's scrollbar leaves it open (scrollbar ${st.sb}px)`);
  await p.mouse.click(6,6); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("recast").hidden),"a click on the backdrop closes it");
  /* growth past the rail's range is held to it, marked, and said where the dialog was opened from */
  await p.click("#r_recast"); await settle(p);
  const put4=async(k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await p.click(sel); await p.keyboard.press("Control+A"); await p.keyboard.type(v,{delay:5}); await p.keyboard.press("Tab"); };
  await put4("rev",0,"2,000,000"); await put4("ni",0,"300,000"); await put4("rev",1,"1,000,000"); await put4("ni",1,"200,000"); await settle(p);
  await p.click("#rc_use"); await settle(p); await p.waitForTimeout(300);
  st=await p.evaluate(()=>({grw:STATE.s.grw,bad:document.getElementById("v_grw").classList.contains("bad"),msg:document.getElementById("r_msg").textContent,top:document.getElementById("tl_msg").textContent}));
  ok(Math.abs(st.grw-.7)<1e-9&&st.bad&&/growth 70\.0%/.test(st.msg)&&/Held to the console.s range: the worksheet.s growth of 100\.0%/.test(st.msg)&&!st.top,
     `growth of 100% is held to the rail's 70%, marked, and the message shows beside the link it was opened from (${st.msg.slice(0,80)})`);
  await p.click("#r_recast"); await settle(p); await p.uncheck("#rc_grw"); await p.click("#rc_use"); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("v_grw").classList.contains("bad")),"'Use' without growth leaves the rail's held-to-range mark on growth");
  await p.click("#r_recast"); await settle(p); await p.click("#rc_clear"); await settle(p);
  await put4("rev",0,"500,000"); await put4("ni",0,"30,000"); await put4("owner",0,"15,500"); await settle(p);
  st=await p.evaluate(()=>({tot:document.getElementById("rc_s0").textContent,big:document.querySelector("#rc_sum .rc-big").textContent}));
  await p.click("#rc_use"); await settle(p); await p.waitForTimeout(300);
  st.msg=await p.evaluate(()=>document.getElementById("r_msg").textContent); st.box=await p.evaluate(()=>document.getElementById("v_ern").value);
  /* round 3: the worksheet applies a cell as it is typed and Escape closes it as Close does, so an amount typed in full and
     left with Escape is kept (r3-worksheet-6, refuted: a revert would drop it); a negative revenue and two amounts are refused */
  await p.click("#r_recast"); await settle(p);
  await p.click('.rc-in[data-k="ni"][data-y="0"]'); await p.keyboard.press("Control+A"); await p.keyboard.type("498,000"); await p.keyboard.press("Escape"); await settle(p);
  const esc=await p.evaluate(()=>({ni:OMNI_BROKER.state().ws.years[0].ni,closed:document.getElementById("recast").hidden}));
  await p.click("#r_recast"); await settle(p); await put4("ni",0,"30,000");
  await put4("rev",1,"-500,000"); await put4("dep",1,"512,000 470,000"); await settle(p);
  const neg=await p.evaluate(()=>({rev:OMNI_BROKER.state().ws.years[1].rev,revBad:document.querySelector('.rc-in[data-k="rev"][data-y="1"]').classList.contains("bad"),
    dep:OMNI_BROKER.state().ws.years[1].dep,depBad:document.querySelector('.rc-in[data-k="dep"][data-y="1"]').classList.contains("bad")}));
  await p.keyboard.press("Escape"); await settle(p);
  ok(esc.ni===498000&&esc.closed,"Escape closes the worksheet and keeps an amount just typed in a cell, as Close does");
  ok(neg.rev===undefined&&neg.revBad&&neg.dep===undefined&&neg.depBad,"a negative revenue and two amounts in one cell are refused and marked");
  await p.click("#v_ern"); await p.keyboard.press("Control+A"); await p.keyboard.type("512,000 470,000"); await p.keyboard.press("Enter"); await settle(p);
  ok(await p.evaluate(()=>STATE.s.ern===45500),"the rail's SDE box refuses two amounts too");
  ok(st.tot==="$45,500"&&st.big==="$45.5k"&&/From the worksheet: SDE \$45\.5k, revenue \$500k/.test(st.msg)&&st.box==="$45.5k",
     `the worksheet's totals and its message echo SDE as the box shows it, not rounded to $46k (${st.tot}, ${st.big}; ${st.msg.slice(0,48)})`);
  ok(errs.length===0,"no page errors with real scrollbars: "+errs.slice(0,3).join(" | "));
  await b2.close();

  /* ---- round 2: two tabs of the page, a half-typed date, the report's draft, imports, duplicates, the penalty card ---- */
  const b3=await pw.chromium.launch();
  const c5=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true});
  /* a tab opened with ?deaf never hears another tab's storage event: its page's listener is dropped before it is added */
  await c5.addInitScript(()=>{ if(location.search.indexOf("deaf")>=0){ const add=window.addEventListener;
    window.addEventListener=function(t,f,o){ if(t==="storage") return; return add.call(this,t,f,o); }; } });
  const oA=await open(c5,"?deaf"), A=oA.p;
  await A.click("#tl_save"); await settle(A);
  const xId=await A.evaluate(()=>OMNI_BROKER.state().cur);
  const oB=await open(c5), B=oB.p;
  await B.click('.tab[data-v="deals"]'); await B.waitForTimeout(1500);
  await B.click("#dl_tbl .dl-name"); await settle(B);
  await B.selectOption('#dl_form select[name="status"]',"closed"); await B.fill('#dl_form input[name="listPrice"]',"3.3M");
  await B.fill('#dl_form input[name="salePrice"]',"3.05M"); await B.click('#dl_form button[type="submit"]'); await settle(B);
  /* tab A misses the storage event: its save must still merge, not revert the outcome recorded in tab B */
  ok(await A.evaluate(id=>OMNI_BROKER.state().deals.find(d=>d.id===id)?.status==="valuing",xId),"the deaf tab did not hear the other tab's save");
  await A.evaluate(()=>{ IN.ern=1.5e6; render(); }); await settle(A); await A.click("#tl_save"); await settle(A);
  st=await A.evaluate(id=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")).find(x=>x.id===id); return d?{st:d.status,sale:d.salePrice,ern:d.inputs.ern}:null; },xId);
  ok(st&&st.st==="closed"&&st.sale===3.05e6&&st.ern===1.5e6,`a save in an older tab keeps the outcome recorded in a newer one, and adds its own change (${JSON.stringify(st)})`);
  const xRec=await A.evaluate(id=>JSON.parse(localStorage.getItem("omni.deals.v1")).find(d=>d.id===id),xId);
  await B.evaluate(()=>{ IN.ern=7e5; render(); }); await settle(B);
  await B.click('.tab[data-v="console"]'); await B.waitForTimeout(1200); await B.evaluate(()=>{ IN.ern=7e5; render(); }); await settle(B);
  await B.evaluate(()=>document.getElementById("dl_new").click()); await settle(B);
  st=await A.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).length);
  ok(st===2,`a deal saved in one tab is kept when another saves (${st} deals stored)`);
  /* a live tab hears another's save and shows its deals */
  const oC=await open(c5), C=oC.p; await C.click('.tab[data-v="deals"]'); await C.waitForTimeout(1500);
  await B.click('.tab[data-v="deals"]'); await B.waitForTimeout(1500);
  /* a setup deletion in a tab that hears others: its two presses go in one task, so no storage event lands between them */
  await B.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`)?.click(); const b=()=>document.querySelector('#dl_form button[data-act="del"]'); b().click(); b().click(); },xId); await settle(B);
  await C.waitForTimeout(400);
  st=await C.evaluate(id=>({rows:document.querySelectorAll("#dl_tbl tbody tr[data-id]").length,has:!!document.querySelector(`#dl_tbl tr[data-id="${id}"]`)}),xId);
  ok(st.rows===1&&!st.has,`a tab showing the Deals tab drops a deal deleted in another at once (${st.rows} left)`);
  /* tab A, still deaf, saves again: the deal deleted in tab B stays deleted */
  await A.evaluate(()=>{ IN.ern=1.6e6; render(); }); await settle(A); await A.click("#tl_save"); await settle(A);
  st=await A.evaluate(id=>JSON.parse(localStorage.getItem("omni.deals.v1")).map(d=>d.id).includes(id),xId);
  ok(!st,"a deletion in one tab is not undone by an older tab's save");
  /* importing the deleted deal again restores it, and the tabs that saw its deletion keep it when they save */
  const ip4=path.join(tmp,"restore.json"); fs.writeFileSync(ip4,JSON.stringify({format:"omni.deals",version:1,deals:[xRec]}));
  await B.setInputFiles("#dl_file",ip4); await B.waitForTimeout(900);
  st={msg:await B.evaluate(()=>document.getElementById("dl_msg").textContent)}; await C.waitForTimeout(400);
  await C.click("#dl_tbl .dl-name"); await settle(C); await C.fill('#dl_form textarea[name="notes"]',"a note"); await C.click('#dl_form button[type="submit"]'); await settle(C);
  await A.evaluate(()=>{ IN.ern=1.7e6; render(); }); await settle(A); await A.click("#tl_save"); await settle(A);
  st.has=await A.evaluate(id=>JSON.parse(localStorage.getItem("omni.deals.v1")).some(d=>d.id===id),xId);
  ok(/Imported 1 new deal/.test(st.msg)&&st.has,`a deleted deal imported again stays, though tabs that saw its deletion save after (${st.msg.slice(0,30)})`);
  /* round 3: a deaf tab's deletion keeps another tab's, and its form keeps another tab's outcome */
  const zId=await A.evaluate(()=>OMNI_BROKER.state().cur), ids=await A.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).map(d=>d.id)), yId=ids.find(i=>i!==xId&&i!==zId);
  await B.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`)?.click(); const b=()=>document.querySelector('#dl_form button[data-act="del"]'); b().click(); b().click(); },yId); await settle(B);
  await A.click('.tab[data-v="deals"]'); await A.waitForTimeout(1500);
  await A.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`)?.click(); const b=()=>document.querySelector('#dl_form button[data-act="del"]'); b().click(); b().click(); },zId); await settle(A);
  st=await A.evaluate(([y,z])=>({ids:JSON.parse(localStorage.getItem("omni.deals.v1")).map(d=>d.id),gone:Object.keys(JSON.parse(localStorage.getItem("omni.deals.v1.deleted")||"{}"))}),[yId,zId]);
  ok(!st.ids.includes(yId)&&!st.ids.includes(zId)&&st.gone.includes(yId)&&st.gone.includes(zId),`a deaf tab's deletion keeps the deletion another tab made, and neither deal comes back (${st.ids.join(",")})`);
  await A.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`)?.click(); },xId); await settle(A);
  await B.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`)?.click(); },xId); await settle(B);
  await B.fill('#dl_form input[name="salePrice"]',"3.2M"); await B.click('#dl_form button[type="submit"]'); await settle(B);
  await A.fill('#dl_form textarea[name="notes"]',"seller wants a quick close"); await A.click('#dl_form button[type="submit"]'); await settle(A);
  st=await A.evaluate(id=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")).find(x=>x.id===id)||{}; return {sale:d.salePrice,notes:d.notes,status:d.status}; },xId);
  ok(st.sale===3.2e6&&st.notes==="seller wants a quick close"&&st.status==="closed",`a deaf tab's form saves only what was typed in it, keeping another tab's sale price (${JSON.stringify(st)})`);
  /* a date left half-typed is refused, and the stored date kept */
  await C.click("#dl_tbl .dl-name"); await settle(C);
  await C.fill('#dl_form input[name="listDate"]',"2025-03-03"); await C.click('#dl_form button[type="submit"]'); await settle(C);
  await C.focus('#dl_form input[name="listDate"]'); await C.keyboard.press("ArrowRight"); await C.keyboard.press("ArrowRight"); await C.keyboard.press("Backspace");
  st=await C.evaluate(()=>{ const e=document.querySelector('#dl_form input[name="listDate"]'); return {v:e.value,bad:e.validity.badInput}; });
  await C.click('#dl_form button[type="submit"]'); await settle(C);
  st.msg=await C.evaluate(()=>document.getElementById("dl_form_msg").textContent);
  st.kept=await C.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1"))[0].listDate);
  ok(st.v===""&&st.bad&&/marked fields: Listing date/.test(st.msg)&&st.kept==="2025-03-03",`a half-typed date is marked and the stored date kept, not erased (${st.msg.slice(0,60)})`);
  /* a sale far from its listing price is questioned */
  await C.fill('#dl_form input[name="listPrice"]',"700k"); await C.selectOption('#dl_form select[name="status"]',"closed"); await C.fill('#dl_form input[name="salePrice"]',"7M");
  await C.fill('#dl_form input[name="listDate"]',"2025-03-03"); await C.click('#dl_form button[type="submit"]'); await settle(C);
  ok(/10\.00× the listing price: check it/.test(await C.evaluate(()=>document.getElementById("dl_form_msg").textContent)),"a sale price ten times the listing price saves with a note to check it");
  /* the report's names typed for an unsaved valuation do not follow into another deal */
  await A.reload(); await A.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await A.waitForTimeout(300);
  await A.click("#tl_report"); await settle(A); await A.fill("#rp_biz","Acme Plumbing"); await A.locator("#rp_biz").blur(); await settle(A); await A.click("#rp_close"); await settle(A);
  ok(await A.evaluate(()=>OMNI_BROKER.state().draft.business==="Acme Plumbing"),"the report's business typed before saving is held as a draft");
  await A.click('.tab[data-v="deals"]'); await A.waitForTimeout(1500);
  await A.click('#dl_tbl button[data-act="open"]'); await A.waitForTimeout(1800);
  ok(await A.evaluate(()=>OMNI_BROKER.state().draft.business===""),"opening another deal discards that draft");
  /* the report's names move the deal's time, so an export carries them */
  const u0=await A.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1"))[0].updated);
  await A.waitForTimeout(20); await A.click("#tl_report"); await settle(A); await A.fill("#rp_biz","Northside Dental"); await A.locator("#rp_biz").blur(); await settle(A); await A.click("#rp_close"); await settle(A);
  st=await A.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; return {b:d.business,u:d.updated}; });
  ok(st.b==="Northside Dental"&&Date.parse(st.u)>Date.parse(u0),"a business typed in the report moves the deal's updated time");
  /* a duplicate of an automatically named deal keeps an automatic name */
  await A.click('.tab[data-v="deals"]'); await A.waitForTimeout(1500);
  await A.click("#dl_tbl .dl-name"); await settle(A);
  const auto0=await A.evaluate(()=>{ const d=OMNI_BROKER.state().deals[0]; return d.autoName; });
  if(!auto0){ await A.fill('#dl_form input[name="name"]',""); }
  await A.evaluate(()=>{ const d=OMNI_BROKER.state().deals.find(x=>x.id===document.querySelector("#dl_tbl tbody tr").dataset.id); if(d) d.autoName=true; });
  await A.click('#dl_form button[data-act="dup"]'); await settle(A);
  await A.click('#dl_form button[data-act="open"]'); await A.waitForTimeout(1800);
  await A.evaluate(()=>{ IN.ern=6e5; render(); }); await settle(A); await A.click("#tl_save"); await settle(A);
  st=await A.evaluate(()=>{ const c=OMNI_BROKER.state().deals.find(d=>d.id===OMNI_BROKER.state().cur)||{}; return {n:c.name,a:c.autoName,bar:document.getElementById("tl_deal").textContent}; });
  ok(st.a&&/, \$600k SDE \(copy\)$/.test(st.n)&&/\$600k SDE \(copy\)/.test(st.bar),`a duplicate's automatic name follows its own SDE and still says it is a copy (${st.n})`);
  /* import: a record without a time of its own does not replace a dated copy here */
  const ex2=await A.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1"))[0]);
  const noTime={...ex2,name:"Old copy, no time"}; delete noTime.updated;
  const ip2=path.join(tmp,"notime.json"); fs.writeFileSync(ip2,JSON.stringify({format:"omni.deals",version:1,deals:[noTime]}));
  await A.click('.tab[data-v="deals"]'); await A.waitForTimeout(1500);
  await A.setInputFiles("#dl_file",ip2); await A.waitForTimeout(900);
  st=await A.evaluate(id=>({msg:document.getElementById("dl_msg").textContent,name:JSON.parse(localStorage.getItem("omni.deals.v1")).find(d=>d.id===id)?.name}),ex2.id);
  ok(/updated 0; 1 skipped/.test(st.msg)&&st.name===ex2.name,`a record with no time of its own never replaces a dated copy (${st.msg.slice(0,40)})`);
  /* the penalty card: a count past its minimum reads 'enough'; inputs that are not numbers are set aside */
  await A.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[];
    for(let i=0;i<12;i++) D.push({id:"pen"+i,name:"Listing "+i,status:i%3?"expired":"closed",inputs:I,listPrice:V*(i<7?1.25:.95),salePrice:i%3?null:V*.9,updated:"2026-01-01T00:00:00.000Z"});
    D.push({id:"dbad",name:"Blank SDE",status:"closed",inputs:{...I,ern:""},listPrice:V,salePrice:V,updated:"2026-01-01T00:00:00.000Z"});
    D.push({id:"dfr",name:"String franchise",status:"valuing",inputs:{...I,franchise:"false"},updated:"2026-01-01T00:00:00.000Z"});
    localStorage.setItem("omni.deals.v1",JSON.stringify(D)); localStorage.removeItem("omni.deals.v1.deleted"); });
  await A.reload(); await A.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await A.waitForTimeout(300);
  await A.click('.tab[data-v="deals"]'); await A.waitForTimeout(1500);
  st=await A.evaluate(()=>({fit:document.getElementById("dl_fit").textContent,S:OMNI_BROKER.state(),store:document.getElementById("dl_store").textContent}));
  ok(/12 of the 20 finished listings it needs; 7 listed at least 10% above value, enough/.test(st.fit),"the penalty card says a count past its minimum is enough, not '7 of the 5'");
  ok(st.S.kept.length===1&&st.S.kept[0].id==="dbad"&&!st.S.deals.some(d=>d.id==="dbad")&&st.S.deals.find(d=>d.id==="dfr")?.inputs?.franchise===false&&/cannot read/.test(st.store),
     "a stored deal whose SDE is blank is set aside, not read as $1k, and franchise \"false\" is not a franchise");
  /* r3-report-10: a deaf tab's preference save writes only what it changed, so the broker and firm another tab typed stay */
  await B.click('.tab[data-v="console"]'); await B.waitForTimeout(1200);
  await B.click("#tl_report"); await settle(B); await B.fill("#rp_broker","Robin Ortiz"); await B.fill("#rp_firm","Ortiz & Co"); await B.locator("#rp_firm").blur(); await settle(B); await B.click("#rp_close"); await settle(B);
  await A.click('.tab[data-v="console"]'); await A.waitForTimeout(1200);
  await A.click("#f_cash"); await A.keyboard.press("Control+A"); await A.keyboard.type("15"); await A.keyboard.press("Enter"); await settle(A);
  st=await A.evaluate(()=>({p:JSON.parse(localStorage.getItem("omni.prefs.v1")),b:OMNI_BROKER.state().prefs.broker}));
  ok(st.p.broker==="Robin Ortiz"&&st.p.firm==="Ortiz & Co"&&Math.abs(st.p.fin.cash-.15)<1e-12&&st.b!=="Robin Ortiz",
     `a tab that missed the storage event saves its buyer cash without erasing the broker and firm another tab typed (${st.p.broker}, ${st.p.firm})`);
  await C.evaluate(()=>dispatchEvent(new StorageEvent("storage",{key:"omni.prefs.v1"})));
  await C.click('.tab[data-v="console"]'); await C.waitForTimeout(1200); await C.click("#tl_report"); await settle(C);
  st=await C.evaluate(()=>({b:document.getElementById("rp_broker").value,f:document.getElementById("rp_firm").value,t:document.getElementById("rp_paper").textContent}));
  ok(st.b==="Robin Ortiz"&&st.f==="Ortiz & Co"&&st.t.includes("Robin Ortiz, Ortiz & Co"),`a tab that heard it opens its report with those names (${st.b}, ${st.f})`);
  await C.click("#rp_close"); await settle(C);
  ok(oA.errs.concat(oB.errs,oC.errs).length===0,"no page errors across three tabs: "+oA.errs.concat(oB.errs,oC.errs).slice(0,3).join(" | "));
  await c5.close();

  /* round 3: times ahead of this clock, records with no time or no id, hostile ids, typed entries across a tab switch,
     the penalty card at its bounds */
  const c9=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true});
  ({p}=await open(c9));
  await p.evaluate(()=>{ const I=OMNI_BROKER.snap(), fut=new Date(Date.now()+864e5).toISOString();
    localStorage.setItem("omni.deals.v1",JSON.stringify([{id:"dfut",name:"Future deal",status:"valuing",inputs:I,updated:fut},{id:"dfut2",name:"Future two",status:"valuing",inputs:I,updated:fut},
      {id:"dnotime",name:"No time",status:"valuing",inputs:I},{id:"__proto__",name:"Hostile id",status:"valuing",inputs:I},{name:"No id",status:"closed",inputs:I,listPrice:I.ask,salePrice:I.ask*.9}])); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  const editNote=async(id,note)=>{ await p.evaluate(i=>{ document.querySelector(`#dl_tbl tr[data-id="${i}"] .dl-name`)?.click(); },id); await settle(p);
    await p.fill('#dl_form textarea[name="notes"]',note); await p.click('#dl_form button[type="submit"]'); await settle(p);
    return p.evaluate(i=>(JSON.parse(localStorage.getItem("omni.deals.v1")).find(d=>d.id===i)||{}).notes,id); };
  ok(await editNote("dfut","edited")==="edited","an edit to a deal stamped later than this clock is kept");
  ok(await editNote("dnotime","first edit")==="first edit","the first edit to a stored deal with no time is kept");
  await p.evaluate(()=>{ document.querySelector('#dl_tbl tr[data-id="dfut2"] .dl-name').click(); }); await settle(p);
  await p.click('#dl_form button[data-act="del"]'); await settle(p); await p.click('#dl_form button[data-act="del"]'); await settle(p);
  st=await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")); return {fut2:D.some(d=>d.id==="dfut2"),proto:D.some(d=>d.id==="__proto__"),noid:D.filter(d=>d.name==="No id").map(d=>d.id)}; });
  ok(!st.fut2&&!st.proto&&st.noid.length===1&&/^h[0-9a-z]+$/.test(st.noid[0]),`a deal stamped later than this clock deletes; a "__proto__" id is replaced; a record with no id gets one from its content (${st.noid})`);
  const hId=st.noid[0];
  await p.evaluate(i=>{ document.querySelector(`#dl_tbl tr[data-id="${i}"] .dl-name`)?.click(); },hId); await settle(p);
  await p.click('#dl_form button[data-act="del"]'); await settle(p); await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(i=>!JSON.parse(localStorage.getItem("omni.deals.v1")).some(d=>d.id===i)&&/^h/.test(i),hId),"a deal whose id was replaced or derived deletes like any other");
  /* the same id-less record imported twice is recognised the second time */
  const noid={name:"Hand-made",status:"closed",inputs:await p.evaluate(()=>OMNI_BROKER.snap()),listPrice:2e6,salePrice:1.8e6};
  const ip5=path.join(tmp,"noid.json"); fs.writeFileSync(ip5,JSON.stringify([noid]));
  await p.setInputFiles("#dl_file",ip5); await p.waitForTimeout(800); const m1=await p.evaluate(()=>document.getElementById("dl_msg").textContent);
  await p.setInputFiles("#dl_file",ip5); await p.waitForTimeout(800); const m2=await p.evaluate(()=>document.getElementById("dl_msg").textContent);
  ok(/Imported 1 new deal/.test(m1)&&/Imported 0 new deals and updated 0; 1 skipped/.test(m2)&&await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).filter(d=>d.name==="Hand-made").length===1),
     "a record with no id imported twice is added once");
  /* a form being typed in keeps its entries when the tab is left and shown again */
  await p.evaluate(()=>{ document.querySelector("#dl_tbl .dl-name").click(); }); await settle(p);
  await p.fill('#dl_form textarea[name="notes"]',"half-written note");
  await p.click('.tab[data-v="console"]'); await p.waitForTimeout(1200); await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(await p.evaluate(()=>{ const t=document.querySelector('#dl_form textarea[name="notes"]'); return !!t&&t.value==="half-written note"; }),"entries typed in the edit form survive a look at the console");
  /* the penalty card at its bounds: no listing at value closed, and listings above value that never close */
  await p.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[];
    for(let i=0;i<24;i++) D.push({id:"b"+i,name:"B "+i,status:"expired",inputs:I,listPrice:V*(i<8?1.3:.95),updated:"2026-01-01T00:00:00.000Z"});
    localStorage.setItem("omni.deals.v1",JSON.stringify(D)); localStorage.removeItem("omni.deals.v1.deleted"); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(/Not fitted: of your 24 finished listings/.test(await p.evaluate(()=>document.getElementById("dl_fit").textContent)),"with no listing at value closing, the penalty card says the scale is not fitted rather than quote search limits");
  await p.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[];
    for(let i=0;i<24;i++) D.push({id:"c"+i,name:"C "+i,status:i<8?"expired":"closed",inputs:I,listPrice:V*(i<8?1.6:.95),salePrice:i<8?null:V*.9,updated:"2026-01-01T00:00:00.000Z"});
    localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  st=await p.evaluate(()=>document.getElementById("dl_fit").textContent);
  ok(/0\.99, the top of its range/.test(st),`listings above value that never close put the scale at the top of its range, and the card says so (${(st.match(/Fitted on[^.]*\./)||[""])[0].slice(0,120)})`);
  await c9.close();

  /* round 3: a new deal saved from the deal in the console keeps the worksheet that deal would save */
  const c8=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  ({p}=await open(c8));
  await p.click("#tl_recast"); await settle(p);
  const put8=async(k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await p.click(sel); await p.keyboard.press("Control+A"); await p.keyboard.type(v,{delay:5}); await p.keyboard.press("Tab"); };
  await put8("rev",0,"6,000,000"); await put8("ni",0,"1,000,000"); await put8("owner",0,"450,000"); await settle(p);
  await p.click("#rc_use"); await settle(p); await p.click("#tl_save"); await settle(p);
  await p.click("#tl_recast"); await settle(p); await put8("dep",0,"40,000"); await settle(p); await p.keyboard.press("Escape"); await settle(p);
  await p.click("#tl_saveas"); await settle(p);
  st=await p.evaluate(()=>{ const S=OMNI_BROKER.state(), c=S.deals.find(d=>d.id===S.cur); return {dep:c&&c.ws&&c.ws.years[0].dep,n:S.deals.length,mark:/unsaved/.test(document.getElementById("tl_deal").textContent)}; });
  ok(st.n===2&&st.dep===40000&&!st.mark,`'Save as new' keeps the deal's own worksheet as edited (${JSON.stringify(st)})`);
  await p.click("#tl_recast"); await settle(p); await put8("dep",0,"55,000"); await settle(p); await p.keyboard.press("Escape"); await settle(p);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500); await p.click("#dl_new"); await settle(p);
  st=await p.evaluate(()=>{ const S=OMNI_BROKER.state(), c=S.deals.find(d=>d.id===S.cur); return {dep:c&&c.ws&&c.ws.years[0].dep,n:S.deals.length}; });
  ok(st.n===3&&st.dep===55000,`'Save the console as a new deal' keeps it too (${JSON.stringify(st)})`);
  await p.evaluate(()=>{ const D=JSON.parse(localStorage.getItem("omni.deals.v1")); D.push({...D[0],id:"dempty",name:"Empty worksheet",ws:{entity:"scorp",weight:"latest",grw:true,years:[{},{},{}]}});
    localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  await p.click('#dl_tbl tr[data-id="dempty"] button[data-act="open"]'); await p.waitForTimeout(1800);
  ok(await p.evaluate(()=>!/unsaved/.test(document.getElementById("tl_deal").textContent)&&OMNI_BROKER.state().deals.find(d=>d.id==="dempty")?.ws===null),
     "a stored worksheet with no entries is read as none, so opening its deal shows nothing unsaved");
  await c8.close();

  /* a full store: the page names the cause, and refuses an import it cannot keep */
  const c6=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  await c6.addInitScript(()=>{ const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(String(v).length>200000) throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
  ({p}=await open(c6));
  await p.click("#tl_save"); await settle(p);
  const big=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0], L=[]; for(let i=0;i<120;i++) L.push({...d,id:"big"+i,notes:"n".repeat(2000)}); return L; });
  const ip3=path.join(tmp,"big.json"); fs.writeFileSync(ip3,JSON.stringify({format:"omni.deals",version:1,deals:big}));
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  await p.setInputFiles("#dl_file",ip3); await p.waitForTimeout(900);
  st=await p.evaluate(()=>({msg:document.getElementById("dl_msg").textContent,n:OMNI_BROKER.state().deals.length,stored:JSON.parse(localStorage.getItem("omni.deals.v1")).length,store:document.getElementById("dl_store").textContent}));
  ok(/Nothing imported/.test(st.msg)&&st.n===1&&st.stored===1&&!/private window/.test(st.store),`an import past the browser's quota is refused whole, and nothing blames a private window (${st.msg.slice(0,40)})`);
  await p.evaluate(()=>{ const d=OMNI_BROKER.state().deals[0]; d.notes="n".repeat(4990); });
  await p.click("#dl_tbl .dl-name"); await settle(p);
  await p.evaluate(()=>{ const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(k==="omni.deals.v1") throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
  await p.click('#dl_form button[type="submit"]'); await settle(p);
  st=await p.evaluate(()=>({msg:document.getElementById("dl_form_msg").textContent,store:document.getElementById("dl_store").textContent}));
  ok(!/^Saved/.test(st.msg)&&/storage for this page is full/.test(st.msg)&&/storage for this page is full/.test(st.store),`a save that does not fit says the store is full, and not "Saved." (${st.msg.slice(0,50)})`);
  await p.click("#dl_new"); await settle(p);
  ok(/is in this tab only/.test(await p.evaluate(()=>document.getElementById("dl_msg").textContent)),"the Deals tab's new deal says it is in this tab only when the store is full");
  await c6.close();
  /* the list of deletions cannot be written: the page says the deal may come back in another tab */
  const c10=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  await c10.addInitScript(()=>{ const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(k==="omni.deals.v1.deleted") throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
  ({p}=await open(c10)); await p.click("#tl_save"); await settle(p);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500); await p.click("#dl_tbl .dl-name"); await settle(p);
  await p.click('#dl_form button[data-act="del"]'); await settle(p); await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(/too full to record the deletion/.test(await p.evaluate(()=>document.getElementById("dl_msg").textContent)),"a deletion the full store cannot record is said, with what it means for other tabs");
  await c10.close();
  /* r3-core-7: a tab showing the console merges another tab's save and redraws its toolbar, but runs the Deals tab's fits only
     when that tab is opened */
  { const c11=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
    /* 24 finished listings, enough for the penalty fit, stored once by a first page before the two tabs open */
    { const o=await open(c11); await o.p.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[];
        for(let i=0;i<24;i++) D.push({id:"fit"+i,name:"Listing "+i,status:i%3?"expired":"closed",inputs:I,listPrice:V*(i<8?1.25:.95),salePrice:i%3?null:V*.9,updated:"2026-01-01T00:00:00.000Z"});
        localStorage.setItem("omni.deals.v1",JSON.stringify(D)); }); await o.p.close(); }
    const A=(await open(c11)).p, B=(await open(c11)).p;
    await B.evaluate(()=>{ window.__fits=0; const f0=window.fitPenaltyScale; window.fitPenaltyScale=function(){ window.__fits++; return f0.apply(this,arguments); }; });
    await A.click("#tl_save"); await settle(A);
    /* headless Chromium delivers the storage event between two pages only some of the time: B is sent the one the browser
       sends, so the check does not depend on that */
    await B.waitForFunction(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).length===25,null,{timeout:15000}).catch(()=>{});
    await B.evaluate(()=>dispatchEvent(new StorageEvent("storage",{key:"omni.deals.v1"})));
    await B.waitForFunction(()=>OMNI_BROKER.state().deals.length===25,null,{timeout:15000}).catch(()=>{}); await B.waitForTimeout(300);
    st=await B.evaluate(()=>({fits:window.__fits,n:OMNI_BROKER.state().deals.length,deals:document.getElementById("view-deals").hidden}));
    await B.click('.tab[data-v="deals"]'); await B.waitForTimeout(1500);
    st.after=await B.evaluate(()=>({fits:window.__fits,card:document.getElementById("dl_fit").textContent}));
    ok(st.deals&&st.n===25&&st.fits===0&&st.after.fits>0&&/listings/.test(st.after.card),
       `a tab showing the console merges another tab's save without running the fits (${st.fits} runs, ${st.n} deals); opening the Deals tab runs them (${st.after.fits})`);
    await c11.close(); }

  /* ---- round 4 ---- */
  { const reload=async q=>{ await q.reload(); await q.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await q.waitForTimeout(300); };
    const cell=async(q,k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await q.click(sel); await q.keyboard.press("Control+A"); await q.keyboard.type(v,{delay:5}); await q.keyboard.press("Tab"); };
    const box=async(q,sel,v)=>{ await q.click(sel); await q.keyboard.press("Control+A"); await q.keyboard.type(v,{delay:5}); await q.keyboard.press("Enter"); await settle(q); };
    const stored=(q,id)=>q.evaluate(id=>JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").find(d=>d.id===id)||null,id);
    const hear=async q=>{ await q.evaluate(()=>{ dispatchEvent(new StorageEvent("storage",{key:"omni.deals.v1"})); dispatchEvent(new StorageEvent("storage",{key:"omni.prefs.v1"})); }); await settle(q); };
    const toDeals=async q=>{ await q.click('.tab[data-v="deals"]'); await q.waitForTimeout(1500); };
    const openIn=async(q,id)=>{ await toDeals(q); await q.click(`#dl_tbl tr[data-id="${id}"] button[data-act="open"]`); await q.waitForTimeout(1800); };
    const sees=(q,f,arg)=>q.waitForFunction(f,arg,{timeout:15000}).catch(()=>{});
    const has=(q,id,f)=>sees(q,([id,f])=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").find(x=>x.id===id); return !!d&&new Function("d","return "+f)(d); },[id,f]);
    const deafInit=()=>{ if(location.search.indexOf("deaf")>=0){ const add=window.addEventListener; window.addEventListener=function(t,f,o){ if(t==="storage") return; return add.call(this,t,f,o); }; } };

    /* the financing boxes, the equation, the labels, the amount parser and the hero */
    const c12=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); const o12=await open(c12), q=o12.p;
    await box(q,"#f_cash","9.996"); await box(q,"#f_nrate","6.005");
    st=await q.evaluate(()=>({cash:OMNI_BROKER.state().fin.cash,box:document.getElementById("f_cash").value,rate:OMNI_BROKER.state().fin.noteRate,rbox:document.getElementById("f_nrate").value}));
    ok(st.cash===.1&&st.box==="10%"&&st.rate===6.01&&st.rbox==="6.01%",`a share or rate typed past two decimals is kept as its box shows it (${JSON.stringify(st)}; r4-financing-3)`);
    await q.evaluate(()=>localStorage.setItem("omni.prefs.v1",JSON.stringify({fin:{type:"initial",cash:.09996,note:.05,noteRate:6.004,noteYears:10,standby:false,extra:.4,capex:0,draw:null}})));
    await reload(q);
    st=await q.evaluate(()=>({f:OMNI_BROKER.state().fin,box:document.getElementById("f_cash").value,ex:document.getElementById("f_extra").value}));
    ok(st.f.cash===.1&&st.box==="10%"&&st.f.noteRate===6&&st.f.extra===0&&st.ex==="none",`a stored structure is held to what its boxes take: shares to 0.01%, no amount under a dollar (${JSON.stringify(st.f)}; r4-deals-10)`);
    await q.evaluate(()=>{ IN.ern=5e4; render(); }); await settle(q);
    st=await q.evaluate(()=>{ const j=EQ.pending.get("eq_fs"); return j?j[1]:EQ.last.get("eq_fs"); });
    ok(/\\le 0/.test(st)&&!/=\s*\\le/.test(st),`with nothing left after the pay the equation reads '≤ 0', not '= ≤ 0' (r4-financing-6)`);
    await q.evaluate(()=>{ IN.ern=1.45e6; render(); }); await settle(q);
    st=await q.evaluate(()=>{ const L=id=>{ const e=document.getElementById(id), h=document.getElementById(e.getAttribute("aria-describedby")||"x");
        return {lab:e.labels&&e.labels[0]?e.labels[0].textContent.trim():"",d:h?h.textContent:"",vis:!!h&&h.getBoundingClientRect().height>0&&!e.labels[0].contains(h)}; };
      return {t:L("f_type"),c:L("f_cash"),n:L("f_note")}; });
    ok(st.t.lab==="Transaction"&&/24 months/.test(st.t.d)&&st.c.lab==="Buyer cash"&&/working capital/.test(st.c.d)&&st.n.lab==="Seller note"&&st.n.d==="of the price"&&st.t.vis&&st.c.vis&&st.n.vis,
       `each box's label is its name alone, and its conditions or basis a visible description outside it (${JSON.stringify(st)}; r4-financing-7)`);
    st=await q.evaluate(()=>["o_val","o_pc","o_mult","o_t"].map(id=>getComputedStyle(document.getElementById(id)).letterSpacing));
    ok(st.every(v=>v!=="normal"&&parseFloat(v)<0),`the hero figures keep their -0.01em tracking beside the paper's guards (${st.join(", ")}; r4-core-3)`);
    const NB=String.fromCharCode(160);
    await box(q,"#v_rev","$45,000 $50,000"); st={rev:await q.evaluate(()=>STATE.s.rev),bad:await q.evaluate(()=>document.getElementById("v_rev").classList.contains("bad"))};
    await box(q,"#v_rev","6"+NB+"200"+NB+"000"); st.nb=await q.evaluate(()=>STATE.s.rev);
    await box(q,"#v_rev","$ 6 300 000"); st.sp=await q.evaluate(()=>STATE.s.rev);
    await box(q,"#f_extra","$45,000 $50,000"); st.ex=await q.evaluate(()=>({v:OMNI_BROKER.state().fin.extra,bad:document.getElementById("f_extra").classList.contains("bad")}));
    await q.click("#tl_recast"); await settle(q); await cell(q,"ni",0,"$512,000 $470,000"); await cell(q,"dep",0,"512,000, 470,000"); await settle(q);
    st.ws=await q.evaluate(()=>({ni:OMNI_BROKER.state().ws.years[0].ni,bad:document.querySelector('.rc-in[data-k="ni"][data-y="0"]').classList.contains("bad"),dep:OMNI_BROKER.state().ws.years[0].dep}));
    await q.keyboard.press("Escape"); await settle(q);
    ok(st.rev===6e6&&st.bad&&st.nb===6.2e6&&st.sp===6.3e6&&st.ex.v===0&&st.ex.bad&&st.ws.ni===undefined&&st.ws.bad&&st.ws.dep===undefined,
       `two amounts are refused in the rail, the financing boxes and the worksheet whatever separates them; a number grouped with no-break spaces, or "$ 6 300 000", is one (${JSON.stringify(st)}; r4-worksheet-2, r4-core-2, r4-core-6)`);
    /* the tallest report with every name at its 120-character limit in the widest letter still prints on one page */
    await q.evaluate(()=>{ IN.rev=6e6; IN.ern=1.45e6; render(); }); await settle(q); await q.click("#tl_report"); await settle(q);
    /* two states: the tallest found in round 3, and the reviewer's in round 4 (an owner buyout past the 7(a) maximum with an 89.67% note), which printed on two pages */
    const worstW=(i)=>{ const T=[{rev:1068011.63,ni:356003.88,owner:35600.39,ptax:5340.06,tax:17800.19,once:160201.74,pers:53400.58,oth:219418.38,nonop:-8900.1},{rev:979010.66,ni:1077588.76},{rev:890009.69,ni:623006.78}];
      let s,fin,R=recastSDE({entity:"schc",weight:"w321",years:T});
      if(i===0){ s={ind:"prof",rev:1008677.65,ern:882463.28,ask:2929000,grw:.02,gm:.48,rec:.54,cc:.18,ret:.54,plt:.52,own:.42,mgt:.36,fin:.14,yrs:6,buyers:95,st:"CA",franchise:false,budget:1e5,lamT:2950,theta:.72};
        fin={type:"expansion",cash:0,note:.1,extra:264739,capex:12345,draw:null}; }
      else if(i===2){ const ern=36879980.31490267, k=ern/R.sde;
        s={ind:"staff",st:"FL",franchise:true,yrs:4,buyers:305,budget:39344.17,lamT:3413,theta:.8814132492989302,ern,rev:480315083.5536389,grw:-.25,gm:.36,rec:.03,cc:.47,ret:.19,plt:.94,own:.14,mgt:.36,fin:.45,ask:173057519.56978077};
        fin={type:"buyout",cash:.05,note:.8967,noteRate:11.93,noteYears:30,standby:false,extra:882464,capex:0,draw:null};
        R=recastSDE({entity:"schc",weight:"w321",years:T.map(y=>Object.fromEntries(Object.entries(y).map(([a,v])=>[a,v*k])))}); }
      else { const ern=Math.pow(10,7.033312350511551), k=ern/R.sde;
        s={ind:"constr",rev:ern/.9155983090400696,ern,ask:Math.pow(10,7.705748653411865),grw:.1402517423033714,gm:.42974957495927807,rec:.5326518416404724,cc:.488709807395935,ret:.23703826189041138,plt:.15384440422058104,
          own:.14,mgt:.66,fin:.14,yrs:5,buyers:20,st:null,franchise:false,budget:1e5,lamT:1300,theta:.360756516456604};
        fin={type:"buyout",cash:.05,note:.8967,noteRate:30,noteYears:30,standby:false,extra:882464,capex:0,draw:null};
        R=recastSDE({entity:"schc",weight:"w321",years:T.map(y=>Object.fromEntries(Object.entries(y).map(([a,v])=>[a,v*k])))}); }
      const D=reportData(s,{fin,recast:R,calib:sampleSummary([1.04,.97,1.1,1.02,.99,1.06],false,.04),date:"September 30, 2026"});
      const W="W".repeat(120), M=i===2?{business:"Lakeside Family Dental Group of Northern Westchester County, a professional corporation doing business as Lakeside Smile",
          preparedFor:"Dr. Jonathan Vanderbilt-Montgomery and Dr. Maria Rodriguez-Castillo, co-owners, together with their trustees and counsel",
          broker:"Patricia Lee-Vanderwaal, Certified Business Intermediary and Mergers and Acquisitions Master Intermediary, Sr. Advisor",
          firm:"Main Street Business Advisors and Transaction Services of the Greater Hudson Valley and Southern Connecticut Region LLC"}:{business:W,preparedFor:W,broker:W,firm:W};
      document.getElementById("rp_paper").innerHTML=reportHTML(D,M); return reportFileHTML(D,M); };
    /* the third, round 5's: the tallest a search on its report reached, past the bottom of the quality range at the ask cap,
       with realistic names at the fields' limit (r5-report-5). The page count decides: the paper measures a few px over the
       page's 998 and still prints on one */
    for(const i of [0,1,2]){
      const fileW=await q.evaluate(worstW,i);
      { const vp=q.viewportSize(); await q.setViewportSize({width:739,height:998}); await q.emulateMedia({media:"print"}); await settle(q);
        st={h:await q.evaluate(()=>document.querySelector("#rp_paper .rp").getBoundingClientRect().height),pa:pages(await q.pdf({format:"Letter"}))};
        await q.emulateMedia({media:"screen"}); await q.setViewportSize(vp); await settle(q);
        const f=await c12.newPage(); await f.setViewportSize({width:739,height:998}); await f.setContent(fileW); await f.emulateMedia({media:"print"});
        st.fh=await f.evaluate(()=>document.querySelector(".rp").getBoundingClientRect().height); st.fa=pages(await f.pdf({format:"Letter"})); st.fc=pages(await f.pdf({preferCSSPageSize:true}));
        await f.close(); }
      ok(st.pa===1&&st.fa===1&&st.fc===1,`${["with all four names at 120 W's the tallest report of round 3","with all four names at 120 W's the round-4 reviewer's tallest report (an owner buyout with an 89.67% note past the 7(a) maximum)",
        "with realistic names at the 120-character limit the tallest report round 5's search reached (past the bottom of the quality range, at the ask cap)"][i]} prints on one page from the page and from the file (${Math.round(st.h)} and ${Math.round(st.fh)} px; ${i<2?"r4-report-6":"r5-report-5"})`);
    }
    await q.click("#rp_close"); await settle(q);
    ok(o12.errs.length===0,"no page errors in round 4's financing and report checks: "+o12.errs.slice(0,3).join(" | "));
    await c12.close();

    /* r4-worksheet-1: a worksheet typed for a deal after it was saved is the deal's own */
    const c13=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
    await c13.addInitScript(()=>{ if(!sessionStorage.getItem("seeded")){ sessionStorage.setItem("seeded","1");
      localStorage.setItem("omni.prefs.v1",JSON.stringify({ws:{entity:"scorp",weight:"latest",grw:true,years:[{rev:5e6,ni:7e5},{},{}]}})); } });
    const o13=await open(c13), w=o13.p;
    await w.click("#tl_save"); await settle(w); const wId=await w.evaluate(()=>OMNI_BROKER.state().cur);
    st={first:(await stored(w,wId)).ws};
    await w.click("#tl_recast"); await settle(w); await cell(w,"dep",0,"40,000"); await settle(w); await w.click("#rc_close"); await settle(w);
    st.mark=await w.evaluate(()=>/unsaved/.test(document.getElementById("tl_deal").textContent)&&document.getElementById("tl_save").textContent==="Save changes");
    await w.click("#tl_save"); await settle(w); st.saved=(await stored(w,wId)).ws;
    await openIn(w,wId); st.back=await w.evaluate(()=>OMNI_BROKER.state().ws.years[0]);
    ok(st.first===null&&st.mark&&st.saved&&st.saved.years[0].dep===40000&&st.saved.years[0].rev===5e6&&st.back.dep===40000,
       `a worksheet edited once its deal is in the console is that deal's own: marked unsaved, saved with it, back when it is opened (${JSON.stringify({first:st.first,mark:st.mark,dep:st.back.dep})}; r4-worksheet-1)`);
    /* a deal saved with no worksheet: Save as new, then typing, keeps the worksheet for the copy */
    await w.click("#reset"); await settle(w); await w.click("#tl_recast"); await settle(w); await w.click("#rc_clear"); await settle(w); await w.click("#rc_close"); await settle(w);
    await w.click("#tl_save"); await settle(w); const plain=await w.evaluate(()=>OMNI_BROKER.state().cur);
    await w.click("#tl_saveas"); await settle(w); const cp=await w.evaluate(()=>OMNI_BROKER.state().cur);
    await w.click("#tl_recast"); await settle(w); await cell(w,"rev",0,"4,000,000"); await cell(w,"ni",0,"500,000"); await settle(w); await w.click("#rc_close"); await settle(w);
    st={mark:await w.evaluate(()=>/unsaved/.test(document.getElementById("tl_deal").textContent))}; await w.click("#tl_save"); await settle(w);
    st.copy=(await stored(w,cp)).ws; st.plain=(await stored(w,plain)).ws;
    ok(cp!==plain&&st.mark&&st.copy&&st.copy.years[0].rev===4e6&&st.plain===null,`a copy saved from a deal with no worksheet takes the worksheet typed for it, and the original keeps none (r4-worksheet-1)`);
    /* a form being typed in stays when its deal changes in the console, and says so; its save keeps that change */
    await toDeals(w); await w.click(`#dl_tbl tr[data-id="${wId}"] .dl-name`); await settle(w);
    await w.fill('#dl_form textarea[name="notes"]',"typed in the form"); await w.dispatchEvent('#dl_form textarea[name="notes"]',"input");
    await w.click('#dl_form button[data-act="open"]'); await w.waitForTimeout(1800);
    await w.evaluate(()=>{ IN.ern=1.3e6; render(); }); await settle(w); await w.click("#tl_save"); await settle(w);
    await toDeals(w);
    st=await w.evaluate(()=>({notes:(document.querySelector('#dl_form textarea[name="notes"]')||{}).value,msg:(document.getElementById("dl_form_msg")||{}).textContent||""}));
    await w.click('#dl_form button[type="submit"]'); await settle(w); st.s=await stored(w,wId);
    ok(st.notes==="typed in the form"&&/changed since this form opened/.test(st.msg)&&st.s.notes==="typed in the form"&&st.s.inputs.ern===1.3e6,
       `an edit form being typed in stays when its deal changes elsewhere, says so, and its save keeps the other change (${JSON.stringify({notes:st.notes,msg:st.msg.slice(0,40)})}; r4-deals-1)`);
    /* an arming of Delete is undone only by its own timer: pressed, closed and reopened, then pressed twice, the first arming's
       timer runs between the two presses (the presses are timed in the page: Playwright's clicks here take seconds) */
    await w.click(`#dl_tbl tr[data-id="${plain}"] .dl-name`); await settle(w);
    const armT=await w.evaluate(async id=>{ const q=s=>document.querySelector(s), wait=ms=>new Promise(r=>setTimeout(r,ms)), t0=performance.now(), T=[];
      q('#dl_form button[data-act="del"]').click(); q('#dl_form button[data-act="close"]').click(); q(`#dl_tbl tr[data-id="${id}"] .dl-name`).click();
      const shown=q('#dl_form button[data-act="del"]').textContent;
      await wait(2000); T.push(performance.now()-t0); q('#dl_form button[data-act="del"]').click();
      await wait(3000); T.push(performance.now()-t0); q('#dl_form button[data-act="del"]').click(); return {T,shown}; },plain); await settle(w);
    ok(armT.shown==="Delete"&&armT.T[0]<4000&&armT.T[1]>4000&&armT.T[1]-armT.T[0]<4000&&/^Deleted/.test(await w.evaluate(()=>document.getElementById("dl_msg").textContent))&&!(await stored(w,plain)),
       `a second press within four seconds deletes, though an earlier arming's timer runs between the two (presses at 0, ${armT.T.map(Math.round).join(" and ")} ms; found in round 4)`);
    ok(o13.errs.length===0,"no page errors in round 4's worksheet and form checks: "+o13.errs.slice(0,3).join(" | "));
    await c13.close();

    /* r4-worksheet-7: two tabs on one deal: the parts another tab saved are taken up, and a save writes only its own */
    const c14=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); await c14.addInitScript(deafInit);
    const oA=await open(c14), A4=oA.p;
    await A4.click("#tl_recast"); await settle(A4); await cell(A4,"rev",0,"6,000,000"); await cell(A4,"ni",0,"900,000"); await cell(A4,"owner",0,"300,000"); await settle(A4);
    await A4.click("#rc_use"); await settle(A4); await A4.click("#tl_save"); await settle(A4); const xId=await A4.evaluate(()=>OMNI_BROKER.state().cur);
    const oB=await open(c14), B4=oB.p; await openIn(B4,xId);
    await B4.click("#tl_recast"); await settle(B4); await cell(B4,"dep",0,"80,000"); await cell(B4,"int",0,"41,000"); await settle(B4); await B4.click("#rc_close"); await settle(B4);
    await B4.click("#tl_save"); await settle(B4); await has(A4,xId,"d.ws&&d.ws.years[0].dep===80000"); await hear(A4);
    st=await A4.evaluate(()=>({mark:/unsaved/.test(document.getElementById("tl_deal").textContent),dep:OMNI_BROKER.state().ws.years[0].dep}));
    await A4.evaluate(()=>{ const e=document.getElementById("i_gm"); e.value=70; e.dispatchEvent(new Event("input",{bubbles:true})); render(); }); await settle(A4); await A4.click("#tl_save"); await settle(A4);
    st.s=await stored(A4,xId);
    ok(!st.mark&&st.dep===80000&&st.s.ws.years[0].dep===80000&&st.s.ws.years[0].int===41000&&Math.abs(st.s.inputs.gm-.7)<1e-9,
       `a tab that hears another's worksheet save takes it up, shows nothing unsaved, and its own save keeps it (${JSON.stringify({mark:st.mark,dep:st.dep,gm:st.s.inputs.gm})}; r4-worksheet-7)`);
    /* the same from a tab that missed the event: its save writes only its own change, and the console takes up the rest */
    const oD=await open(c14,"?deaf"), D4=oD.p; await openIn(D4,xId);
    await openIn(B4,xId); await B4.click("#tl_recast"); await settle(B4); await cell(B4,"once",0,"25,000"); await settle(B4); await B4.click("#rc_close"); await settle(B4); await B4.click("#tl_save"); await settle(B4);
    await has(D4,xId,"d.ws&&d.ws.years[0].once===25000");
    await D4.evaluate(()=>{ const e=document.getElementById("i_rec"); e.value=40; e.dispatchEvent(new Event("input",{bubbles:true})); render(); }); await settle(D4); await D4.click("#tl_save"); await settle(D4);
    st=await D4.evaluate(()=>({msg:document.getElementById("tl_msg").textContent,once:OMNI_BROKER.state().ws.years[0].once,mark:/unsaved/.test(document.getElementById("tl_deal").textContent)})); st.s=await stored(D4,xId);
    ok(st.s.ws.years[0].once===25000&&Math.abs(st.s.inputs.rec-.4)<1e-9&&st.once===25000&&!st.mark&&/Another tab had saved changes to its worksheet, which the console now shows/.test(st.msg),
       `a tab that missed another's worksheet save writes only its own change and then shows the other's (${JSON.stringify({once:st.s.ws.years[0].once,rec:st.s.inputs.rec,msg:st.msg.slice(0,60)})}; r4-worksheet-7)`);
    /* the report's fields: a change writes that field alone, and the business another tab typed shows here */
    await openIn(A4,xId); await A4.click("#tl_report"); await settle(A4);
    await openIn(B4,xId); await B4.click("#tl_report"); await settle(B4);
    await B4.fill("#rp_biz","Lakeside Family Dental"); await B4.dispatchEvent("#rp_biz","change"); await settle(B4);
    await B4.fill("#rp_broker","Robin Ortiz"); await B4.dispatchEvent("#rp_broker","change"); await B4.fill("#rp_firm","Ortiz & Co"); await B4.dispatchEvent("#rp_firm","change"); await settle(B4);
    await has(A4,xId,"d.business==='Lakeside Family Dental'"); await sees(A4,()=>{ const p=JSON.parse(localStorage.getItem("omni.prefs.v1")||"{}"); return p.firm==="Ortiz & Co"; });
    await hear(A4); st={biz:await A4.evaluate(()=>document.getElementById("rp_biz").value)};
    await A4.fill("#rp_for","Dr. Ortiz"); await A4.dispatchEvent("#rp_for","change"); await settle(A4); st.s=await stored(A4,xId);
    await has(D4,xId,"d.preparedFor==='Dr. Ortiz'"); await sees(D4,()=>{ const p=JSON.parse(localStorage.getItem("omni.prefs.v1")||"{}"); return p.firm==="Ortiz & Co"; });
    await openIn(D4,xId); await D4.click("#tl_report"); await settle(D4);
    await D4.fill("#rp_biz","Lakeside Family Dental"); await D4.dispatchEvent("#rp_biz","change"); await settle(D4);
    st.prefs=await D4.evaluate(()=>{ const p=JSON.parse(localStorage.getItem("omni.prefs.v1")); return [p.broker,p.firm]; });
    ok(st.biz==="Lakeside Family Dental"&&st.s.business==="Lakeside Family Dental"&&st.s.preparedFor==="Dr. Ortiz"&&st.prefs[0]==="Robin Ortiz"&&st.prefs[1]==="Ortiz & Co",
       `a report field's change writes that field alone, so another tab's business, broker and firm stand (${JSON.stringify({biz:st.s.business,pf:st.s.preparedFor,prefs:st.prefs})}; r4-deals-3, r4-deals-4)`);
    /* r4-deals-7, r4-deals-8: a tab that missed the deletion of the deal in its console says so when it saves; one that
       missed other tabs' saves lists and exports what is stored */
    for(const q of [D4,B4,A4]){ await q.click("#rp_close"); await settle(q); }
    /* the deletion is this check's setup: its two presses go in one task, so no storage event lands between them */
    await toDeals(B4); await B4.waitForTimeout(500);
    for(let i=0;i<3&&await B4.evaluate(id=>OMNI_BROKER.state().deals.some(d=>d.id===id),xId);i++){
      await B4.evaluate(id=>{ document.querySelector(`#dl_tbl tr[data-id="${id}"] .dl-name`).click(); const b=()=>document.querySelector('#dl_form button[data-act="del"]'); b().click(); b().click(); },xId); await settle(B4); }
    await sees(D4,id=>!JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").some(x=>x.id===id)&&(localStorage.getItem("omni.deals.v1.deleted")||"").includes(id),xId);
    await D4.click("#tl_save"); await settle(D4);
    st=await D4.evaluate(()=>({msg:document.getElementById("tl_msg").textContent,cur:OMNI_BROKER.state().cur})); st.s=await stored(D4,st.cur);
    ok(/was deleted in another tab, so this valuation is saved as a new deal/.test(st.msg)&&st.cur!==xId&&st.s&&st.s.business==="Lakeside Family Dental",
       `saving a deal deleted in another tab says so, and the new deal keeps its business (${st.msg.slice(0,80)}; r4-deals-7)`);
    await B4.click('.tab[data-v="console"]'); await B4.waitForTimeout(1200); await B4.click("#reset"); await settle(B4); await B4.click("#tl_save"); await settle(B4);
    const yId=await B4.evaluate(()=>OMNI_BROKER.state().cur); await has(D4,yId,"true");
    await toDeals(D4); st={listed:await D4.evaluate(id=>!!document.querySelector(`#dl_tbl tr[data-id="${id}"]`),yId)};
    ok(st.listed,"a tab that missed another tab's save lists the stored deals when the Deals tab opens (r4-deals-8)");
    ok(oA.errs.length===0&&oB.errs.length===0&&oD.errs.length===0,"no page errors in round 4's two-tab checks: "+oA.errs.concat(oB.errs,oD.errs).slice(0,3).join(" | "));
    await c14.close();

    /* r4-deals-2, -5, -6: a stored deal with no time is deleted at the first press; a deletion the store cannot take is not
       recorded; a far-future time neither stops an edit nor a deletion */
    const c15=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
    await c15.addInitScript(()=>{ const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(window.__full&&k==="omni.deals.v1") throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
    const o15=await open(c15), z=o15.p;
    await z.evaluate(()=>{ const I=OMNI_BROKER.snap(), D=[]; for(let i=0;i<50;i++) D.push({id:"n"+i,name:"Deal "+i,inputs:I,updated:"2026-01-01T00:00:00.000Z"});
      D.push({id:"dnotime",name:"No time",inputs:I},{id:"dmax",name:"Max time",inputs:I,updated:"+275760-09-13T00:00:00.000Z"},{id:"d9999",name:"Year 9999",inputs:I,updated:"9999-12-31T23:59:59.999Z"});
      localStorage.setItem("omni.deals.v1",JSON.stringify(D)); localStorage.removeItem("omni.deals.v1.deleted"); });
    await reload(z); await toDeals(z);
    const del=async id=>{ await z.click(`#dl_tbl tr[data-id="${id}"] .dl-name`); await settle(z); await z.click('#dl_form button[data-act="del"]'); await settle(z); await z.click('#dl_form button[data-act="del"]'); await settle(z); };
    await del("dnotime"); st={nt:!(await stored(z,"dnotime")),ntRow:await z.evaluate(()=>!!document.querySelector('#dl_tbl tr[data-id="dnotime"]'))};
    for(const id of ["dmax","d9999"]){ await z.click(`#dl_tbl tr[data-id="${id}"] .dl-name`); await settle(z); await z.fill('#dl_form textarea[name="notes"]',"edited "+id); await z.click('#dl_form button[type="submit"]'); await settle(z); }
    st.ed=[(await stored(z,"dmax")).notes,(await stored(z,"d9999")).notes]; await del("dmax"); st.dmax=!(await stored(z,"dmax"));
    ok(st.nt&&!st.ntRow&&st.ed[0]==="edited dmax"&&st.ed[1]==="edited d9999"&&st.dmax&&o15.errs.length===0,
       `a stored deal with no time is deleted at the first press among 50 others, and deals stamped at the end of time can be edited and deleted (${JSON.stringify(st)}; r4-deals-2, r4-deals-6, r4-core-8)`);
    await z.evaluate(()=>{ window.__full=true; }); await del("n3");
    st={msg:await z.evaluate(()=>document.getElementById("dl_msg").textContent),row:await z.evaluate(()=>!!document.querySelector('#dl_tbl tr[data-id="n3"]')),
      gone:await z.evaluate(()=>Object.keys(JSON.parse(localStorage.getItem("omni.deals.v1.deleted")||"{}")))};
    await z.evaluate(()=>{ window.__full=false; }); await reload(z); await toDeals(z);
    st.after=await z.evaluate(()=>!!document.querySelector('#dl_tbl tr[data-id="n3"]'));
    await z.click('#dl_tbl tr[data-id="n3"] .dl-name'); await settle(z); await z.fill('#dl_form textarea[name="notes"]',"still here"); await z.click('#dl_form button[type="submit"]'); await settle(z);
    st.edit=await z.evaluate(()=>document.getElementById("dl_form_msg").textContent);
    ok(/is not deleted/.test(st.msg)&&st.row&&!st.gone.includes("n3")&&st.after&&/^Saved/.test(st.edit),
       `a deletion the full store cannot take is not recorded either: the deal stays, here and after a reload, and can be edited (${JSON.stringify({msg:st.msg.slice(0,50),gone:st.gone})}; r4-deals-5)`);
    /* r4-deals-9: with no listing at or below value the penalty card says what it still needs */
    await z.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[]; for(let i=0;i<20;i++) D.push({id:"a"+i,name:"A "+i,status:i%2?"closed":"expired",inputs:I,listPrice:V*1.3,salePrice:i%2?V:null,updated:"2026-01-01T00:00:00.000Z"});
      localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
    await reload(z); await toDeals(z);
    st=await z.evaluate(()=>document.getElementById("dl_fit").textContent);
    ok(/0 of the 5 listed at or below value it needs/.test(st)&&!/Fitted on/.test(st),"with every listing above value the penalty card waits for 5 at or below value instead of quoting a scale it cannot tell apart (r4-deals-9)");
    ok(o15.errs.length===0,"no page errors in round 4's deletion checks: "+o15.errs.slice(0,3).join(" | "));
    await c15.close(); }

  /* ---- round 5 ---- */
  { const reload=async q=>{ await q.reload(); await q.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await q.waitForTimeout(300); };
    const cell=async(q,k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await q.click(sel); await q.keyboard.press("Control+A"); await q.keyboard.type(v,{delay:5}); await q.keyboard.press("Tab"); };
    const box=async(q,sel,v)=>{ await q.click(sel); await q.keyboard.press("Control+A"); await q.keyboard.type(v,{delay:5}); await q.keyboard.press("Enter"); await settle(q); };
    const stored=(q,id)=>q.evaluate(id=>JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").find(d=>d.id===id)||null,id);
    const hear=async q=>{ await q.evaluate(()=>{ dispatchEvent(new StorageEvent("storage",{key:"omni.deals.v1"})); dispatchEvent(new StorageEvent("storage",{key:"omni.prefs.v1"})); }); await settle(q); };
    const toDeals=async q=>{ await q.click('.tab[data-v="deals"]'); await q.waitForTimeout(1500); };
    const toConsole=async q=>{ await q.click('.tab[data-v="console"]'); await q.waitForTimeout(1200); };
    const openIn=async(q,id)=>{ await toDeals(q); await q.click(`#dl_tbl tr[data-id="${id}"] button[data-act="open"]`); await q.waitForTimeout(1800); };
    const sees=(q,f,arg)=>q.waitForFunction(f,arg,{timeout:15000}).catch(()=>{});
    const has=(q,id,f)=>sees(q,([id,f])=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").find(x=>x.id===id); return !!d&&new Function("d","return "+f)(d); },[id,f]);
    const gone=(q,id)=>sees(q,id=>!JSON.parse(localStorage.getItem("omni.deals.v1")||"[]").some(x=>x.id===id),id);
    const deafInit=()=>{ if(location.search.indexOf("deaf")>=0){ const add=window.addEventListener; window.addEventListener=function(t,f,o){ if(t==="storage") return; return add.call(this,t,f,o); }; } };
    const slider=async(q,id,v)=>{ await q.evaluate(([id,v])=>{ const e=document.getElementById(id); e.value=v; e.dispatchEvent(new Event("input",{bubbles:true})); render(); },[id,v]); await settle(q); };
    const cur=q=>q.evaluate(()=>OMNI_BROKER.state().cur);
    const msg=(q,id)=>q.evaluate(id=>{ const e=document.getElementById(id); return e?e.textContent:""; },id);
    const del2=async(q,id)=>{ await q.click(`#dl_tbl tr[data-id="${id}"] .dl-name`); await settle(q); await q.evaluate(()=>{ const b=document.querySelector('#dl_form button[data-act="del"]'); b.click(); b.click(); }); await settle(q); };

    /* the financing box and the buyer cash row, the paste guard, a long name in a message */
    const c16=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); const o16=await open(c16), q=o16.p;
    await q.evaluate(()=>{ IN.ask=1.6e6; render(); }); await settle(q);
    await q.selectOption("#f_type","buyout"); await settle(q); await box(q,"#f_cash","8"); await box(q,"#f_extra","300000");
    st=await q.evaluate(()=>{ const tr=[...document.querySelectorAll("#fintbl tr")].find(r=>r.querySelector("th")&&r.querySelector("th").textContent.trim()==="Buyer cash");
      return tr?[...tr.querySelectorAll("td")].map(td=>td.textContent.replace(/\s+/g," ").trim()):[]; });
    ok(st.some(t=>/9\.5% of the price: under SBA’s 10%/.test(t))&&!st.some(t=>/\d%: under SBA/.test(t)),`an owner buyout's failing buyer cash names its basis, the price, beside cells that give the project's (${st.join(" | ")}; r5-financing-3)`);
    await q.selectOption("#f_type","initial"); await settle(q); await box(q,"#f_cash","9.95"); await box(q,"#f_note","90"); await box(q,"#f_extra","none");
    st={i:(await msg(q,"fin_max")).replace(/\s+/g," ")}; await q.selectOption("#f_type","expansion"); await settle(q); st.e=(await msg(q,"fin_max")).replace(/\s+/g," ");
    ok(/at every price this structure finances\./.test(st.i)&&!/Above \$|reduce or eliminate/.test(st.i)&&!/Above \$/.test(st.e),
       `at 9.95% buyer cash and a 90% note no equity edge is named where the loan passes a dollar, and an initial acquisition is not told its equity can be waived (${st.i.slice(0,140)}; r5-financing-1)`);
    await q.selectOption("#f_type","initial"); await settle(q); await box(q,"#f_cash","10"); await box(q,"#f_note","5");
    /* r5-core-1, r5-worksheet-5: a pasted column or row of cells is refused in a money box and a worksheet cell; one cell is not */
    await q.click("#tl_recast"); await settle(q);
    st=await q.evaluate(()=>{ const paste=(el,t)=>{ const dt=new DataTransfer(); dt.setData("text/plain",t); const e=new ClipboardEvent("paste",{clipboardData:dt,bubbles:true,cancelable:true});
        el.dispatchEvent(e); const r=e.defaultPrevented&&el.classList.contains("bad"); el.classList.remove("bad"); return r; };
      const NN=String.fromCharCode(0x202f);
      return {rail:paste(document.getElementById("v_rev"),"512\n470"),fin:paste(document.getElementById("f_extra"),"45"+NN+"000\r\n500"),
        cell:paste(document.querySelector('.rc-in[data-k="dep"][data-y="0"]'),"45\t500"),one:!paste(document.getElementById("v_ern"),"1,450,000\r\n")}; });
    await q.click("#rc_close"); await settle(q);
    ok(st.rail&&st.fin&&st.cell&&st.one,`a column or row of cells pasted into a money box or a worksheet cell is refused and marked, a single cell is not (${JSON.stringify(st)}; r5-core-1, r5-worksheet-5)`);
    /* r5-deals-12: a message quoting a long one-word name wraps inside a phone's page */
    await q.setViewportSize({width:390,height:844}); await q.click("#tl_save"); await settle(q); const wid=await cur(q);
    await toDeals(q); await q.click(`#dl_tbl tr[data-id="${wid}"] .dl-name`); await settle(q); await q.fill('#dl_form input[name="name"]',"W".repeat(60)); await q.click('#dl_form button[type="submit"]'); await settle(q);
    await q.click('#dl_form button[data-act="dup"]'); await settle(q);
    st=await q.evaluate(()=>{ const e=document.getElementById("dl_msg"), r=e.getBoundingClientRect(); return {right:Math.round(r.right),sw:e.scrollWidth,cw:e.clientWidth,t:e.textContent.slice(0,14)}; });
    ok(st.right<=390&&st.sw<=st.cw+1&&/^Duplicated as/.test(st.t),`a message quoting a long one-word name wraps inside a 390px page (${JSON.stringify(st)}; r5-deals-12)`);
    ok(o16.errs.length===0,"no page errors in round 5's financing, paste and message checks: "+o16.errs.slice(0,3).join(" | "));
    await c16.close();

    /* r5-worksheet-1, r5-deals-2: two tabs on one deal, field by field */
    const c17=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); const o17a=await open(c17), A5=o17a.p;
    await A5.click("#tl_recast"); await settle(A5); await cell(A5,"rev",0,"6,000,000"); await cell(A5,"ni",0,"900,000"); await cell(A5,"owner",0,"300,000"); await settle(A5);
    await A5.click("#rc_use"); await settle(A5); await A5.click("#tl_save"); await settle(A5); const id5=await cur(A5);
    const o17b=await open(c17), B5=o17b.p; await openIn(B5,id5);
    await A5.click("#tl_recast"); await settle(A5); await cell(A5,"dep",0,"80,000"); await settle(A5); await A5.click("#rc_close"); await settle(A5); await slider(A5,"i_gm",70);
    await B5.click("#tl_recast"); await settle(B5); await cell(B5,"int",0,"41,000"); await settle(B5); await B5.click("#rc_close"); await settle(B5); await slider(B5,"i_rec",40);
    await B5.click("#tl_save"); await settle(B5); await has(A5,id5,"d.ws&&d.ws.years[0].int===41000"); await hear(A5);
    st={a:await A5.evaluate(()=>({int:OMNI_BROKER.state().ws.years[0].int,dep:OMNI_BROKER.state().ws.years[0].dep,rec:STATE.s.rec,gm:STATE.s.gm,mark:/unsaved/.test(document.getElementById("tl_deal").textContent)}))};
    await A5.click("#tl_save"); await settle(A5); st.s=await stored(A5,id5);
    ok(st.a.int===41000&&st.a.dep===80000&&Math.abs(st.a.rec-.4)<1e-9&&Math.abs(st.a.gm-.7)<1e-9&&st.a.mark&&st.s.ws?.years[0].dep===80000&&st.s.ws?.years[0].int===41000
       &&Math.abs(st.s.inputs.rec-.4)<1e-9&&Math.abs(st.s.inputs.gm-.7)<1e-9,
       `two tabs that change different cells and inputs of one deal keep both: the tab that hears takes the other's up field by field, and its save writes its own (${JSON.stringify({a:st.a,ws:st.s.ws?.years[0]})}; r5-worksheet-1, r5-deals-2)`);
    await has(B5,id5,"Math.abs(d.inputs.gm-.7)<1e-9"); await hear(B5);
    await slider(A5,"i_gm",72); await slider(B5,"i_gm",60); await B5.click("#tl_save"); await settle(B5); await has(A5,id5,"Math.abs(d.inputs.gm-.6)<1e-9"); await hear(A5);
    st={heard:await msg(A5,"tl_msg"),gm:await A5.evaluate(()=>STATE.s.gm)};
    await A5.click("#tl_save"); await settle(A5); st.saved=await msg(A5,"tl_msg"); st.s=(await stored(A5,id5)).inputs.gm;
    ok(/^Another tab saved changes to fields of this deal’s inputs that this tab has also changed: this tab keeps its own/.test(st.heard)&&Math.abs(st.gm-.72)<1e-9&&/Where both tabs changed its inputs, this tab’s values replaced the other’s/.test(st.saved)&&Math.abs(st.s-.72)<1e-9,
       `where both tabs change one field, the tab that hears keeps its own and says so, and its save says it replaced the other's (${JSON.stringify({heard:st.heard.slice(0,50),saved:st.saved.slice(0,70),gm:st.s})}; r5-worksheet-1, r5-deals-2)`);
    ok(o17a.errs.length===0&&o17b.errs.length===0,"no page errors in round 5's two-tab field checks: "+o17a.errs.concat(o17b.errs).slice(0,3).join(" | "));
    await c17.close();

    /* r5-worksheet-2, r5-deals-3: a tab that hears the deal in its console deleted; r5-worksheet-3, r5-deals-1: an import of it */
    const c18=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true}); const o18=await open(c18), A6=o18.p;
    await A6.click("#tl_recast"); await settle(A6); await cell(A6,"rev",0,"5,800,000"); await cell(A6,"ni",0,"700,000"); await settle(A6); await A6.click("#rc_use"); await settle(A6);
    await A6.click("#tl_save"); await settle(A6); const id6=await cur(A6);
    await A6.click("#tl_report"); await settle(A6); await A6.fill("#rp_biz","Smith Dental LLC"); await A6.press("#rp_biz","Tab"); await settle(A6); await A6.click("#rp_close"); await settle(A6);
    await toDeals(A6); await A6.click(`#dl_tbl tr[data-id="${id6}"] .dl-name`); await settle(A6); await A6.fill('#dl_form input[name="name"]',"Smith Dental"); await A6.click('#dl_form button[type="submit"]'); await settle(A6);
    await toConsole(A6); await A6.click("#tl_recast"); await settle(A6); await cell(A6,"dep",0,"60,000"); await settle(A6); await A6.click("#rc_close"); await settle(A6);
    const o18d=await open(c18), D6=o18d.p; await toDeals(D6); await del2(D6,id6); await gone(A6,id6); await hear(A6);
    st={msg:await msg(A6,"tl_msg"),bar:await msg(A6,"tl_deal")};
    await A6.click("#tl_save"); await settle(A6); const nid=await cur(A6); st.d=await stored(A6,nid); st.saved=await msg(A6,"tl_msg");
    ok(/“Smith Dental” was deleted in another tab/.test(st.msg)&&/Unsaved valuation/.test(st.bar)&&!!st.d&&st.d.name==="Smith Dental"&&st.d.business==="Smith Dental LLC"&&!!st.d.ws&&st.d.ws?.years[0].dep===60000
       &&/was deleted in another tab, so this valuation is saved as a new deal/.test(st.saved),
       `a tab that hears the deal in its console deleted says so, and its next save keeps the deal's name, business and worksheet, edits included (${JSON.stringify({msg:st.msg.slice(0,40),name:st.d&&st.d.name,biz:st.d&&st.d.business,dep:st.d&&st.d.ws&&st.d.ws?.years[0].dep})}; r5-worksheet-2, r5-deals-3)`);
    await toDeals(A6); const [dj]=await Promise.all([A6.waitForEvent("download"),A6.click("#dl_json")]); const jp=path.join(tmp,"r5imp.json"); await dj.saveAs(jp);
    { const J=JSON.parse(fs.readFileSync(jp,"utf8")), x=J.deals.find(d=>d.id===nid); x.inputs.ern=1.6e6; x.ws=x.ws||{entity:"scorp",weight:"latest",grw:true,years:[{},{},{}]}; x.ws.years[0].dep=80000; x.notes="valued again at the office"; x.updated=new Date(Date.now()+60000).toISOString(); fs.writeFileSync(jp,JSON.stringify(J)); }
    await A6.setInputFiles("#dl_file",jp); await A6.waitForTimeout(900); await toConsole(A6);
    st=await A6.evaluate(()=>({ern:STATE.s.ern,dep:OMNI_BROKER.state().ws.years[0].dep,bar:document.getElementById("tl_deal").textContent,msg:document.getElementById("tl_msg").textContent}));
    await A6.evaluate(()=>{ IN.ask=3.5e6; render(); }); await settle(A6); await A6.click("#tl_save"); await settle(A6); st.s=await stored(A6,nid); st.saved=await msg(A6,"tl_msg");
    ok(st.ern===1.6e6&&st.dep===80000&&!/unsaved/.test(st.bar)&&/The import saved changes to this deal’s inputs and worksheet/.test(st.msg)&&st.s.inputs.ern===1.6e6&&st.s.inputs.ask===3.5e6
       &&st.s.ws?.years[0].dep===80000&&st.s.notes==="valued again at the office"&&!/Another tab/.test(st.saved),
       `an import that updates the deal in the console is taken up: nothing unsaved, the message names the import, and the next save keeps it (${JSON.stringify({ern:st.ern,dep:st.dep,msg:st.msg.slice(0,50),saved:st.saved.slice(0,30)})}; r5-worksheet-3, r5-deals-1)`);
    ok(o18.errs.length===0&&o18d.errs.length===0,"no page errors in round 5's deletion and import checks: "+o18.errs.concat(o18d.errs).slice(0,3).join(" | "));
    await c18.close();

    /* r5-deals-4: a change the full store refused stays in this tab; r5-report-4, r5-deals-7: the report's fields say so */
    const c19=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
    await c19.addInitScript(()=>{ const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(window.__full&&(k==="omni.deals.v1"||k==="omni.prefs.v1")) throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
    const o19a=await open(c19), A7=o19a.p; await A7.click("#tl_save"); await settle(A7); const id7=await cur(A7);
    const o19b=await open(c19), B7=o19b.p; await openIn(B7,id7);
    await A7.evaluate(()=>{ window.__full=true; IN.ern=9.1e5; render(); }); await settle(A7); await A7.click("#tl_save"); await settle(A7);
    st={msg:await msg(A7,"tl_msg")};
    await slider(B7,"i_rec",30); await B7.click("#tl_save"); await settle(B7); await has(A7,id7,"Math.abs(d.inputs.rec-.3)<1e-9"); await hear(A7);
    st.a=await A7.evaluate(id=>({ern:STATE.s.ern,rec:STATE.s.rec,mem:OMNI_BROKER.state().deals.find(d=>d.id===id).inputs.ern,bar:document.getElementById("tl_deal").textContent}),id7);
    ok(/Updated in this tab only/.test(st.msg)&&st.a.ern===9.1e5&&Math.abs(st.a.rec-.3)<1e-9&&st.a.mem===9.1e5&&/kept in this tab only/.test(st.a.bar),
       `a change the full store refused stays in this tab when another tab saves the deal: the console and the copy an export writes keep it, with the other tab's change (${JSON.stringify(st.a)}; r5-deals-4)`);
    await A7.click("#tl_report"); await settle(A7);
    await A7.fill("#rp_biz","Lakeside Dental"); await A7.press("#rp_biz","Tab"); await settle(A7); st={biz:await msg(A7,"rp_msg")};
    await A7.evaluate(()=>{ const e=document.getElementById("rp_msg"); if(e) e.textContent=""; }); await A7.fill("#rp_broker","Pat Lee"); await A7.press("#rp_broker","Tab"); await settle(A7); st.broker=await msg(A7,"rp_msg");
    await A7.click("#rp_close"); await settle(A7); await A7.evaluate(()=>{ window.__full=false; });
    ok(/storage for this page is full/.test(st.biz)&&/storage for this page is full/.test(st.broker),`a report field the full store refuses says so in the report (${JSON.stringify({biz:st.biz.slice(0,40),broker:st.broker.slice(0,40)})}; r5-report-4, r5-deals-7)`);
    ok(o19a.errs.length===0&&o19b.errs.length===0,"no page errors in round 5's full-store checks: "+o19a.errs.concat(o19b.errs).slice(0,3).join(" | "));
    await c19.close();

    /* r5-deals-5, -6, -11: a tab that missed other tabs' saves duplicates and reports what is stored, and its form says why it closed */
    const c20=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"}); await c20.addInitScript(deafInit);
    const o20a=await open(c20,"?deaf"), A8=o20a.p; await A8.click("#tl_save"); await settle(A8); const x8=await cur(A8);
    await A8.evaluate(()=>{ IN.ern=1.1e6; render(); }); await settle(A8); await A8.click("#tl_saveas"); await settle(A8); const y8=await cur(A8);
    await toDeals(A8); await A8.click(`#dl_tbl tr[data-id="${x8}"] .dl-name`); await settle(A8);
    const o20b=await open(c20), B8=o20b.p; await openIn(B8,x8); await B8.evaluate(()=>{ IN.ern=1.62e6; render(); }); await settle(B8); await B8.click("#tl_save"); await settle(B8);
    await A8.click('#dl_form button[data-act="dup"]'); await settle(A8);
    st={x:await A8.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).filter(d=>/\(copy\)$/.test(d.name)).map(d=>d.inputs.ern))};
    await A8.click(`#dl_tbl tr[data-id="${y8}"] .dl-name`); await settle(A8);
    await toDeals(B8); await del2(B8,y8);
    await A8.click('#dl_form button[data-act="dup"]'); await settle(A8);
    st.y=await msg(A8,"dl_msg"); st.copies=await A8.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).filter(d=>/\(copy\)$/.test(d.name)).length);
    ok(st.x.length===1&&st.x[0]===1.62e6&&/deleted in another tab/.test(st.y)&&st.copies===1,`a tab that missed other tabs' saves duplicates a deal as stored, and refuses one deleted elsewhere (${JSON.stringify(st)}; r5-deals-5)`);
    await openIn(A8,x8); await toConsole(B8); await B8.click("#tl_report"); await settle(B8);
    for(const [id,v] of [["rp_biz","Lakeside Family Dental, PLLC"],["rp_broker","Pat Lee, CBI"],["rp_firm","Sunbelt Springfield"]]){ await B8.fill("#"+id,v); await B8.press("#"+id,"Tab"); await settle(B8); }
    await B8.click("#rp_close"); await settle(B8); await has(A8,x8,"d.business==='Lakeside Family Dental, PLLC'");
    await A8.click("#tl_report"); await settle(A8); st=await A8.evaluate(()=>["rp_biz","rp_broker","rp_firm"].map(id=>document.getElementById(id).value)); await A8.click("#rp_close"); await settle(A8);
    ok(st[0]==="Lakeside Family Dental, PLLC"&&st[1]==="Pat Lee, CBI"&&st[2]==="Sunbelt Springfield",`a tab that missed another's save opens the report with the names stored (${st.join(" | ")}; r5-deals-6)`);
    await toDeals(A8); await A8.click(`#dl_tbl tr[data-id="${x8}"] .dl-name`); await settle(A8); await A8.fill('#dl_form textarea[name="notes"]',"seller agreed to a 90-day transition"); await toConsole(A8);
    await toDeals(B8); await del2(B8,x8); await toDeals(A8);
    st=await A8.evaluate(()=>({shown:!document.getElementById("dl_edit_sec").hidden,msg:document.getElementById("dl_msg").textContent}));
    ok(!st.shown&&/The deal being edited was deleted in another tab/.test(st.msg),`an edit form whose deal was deleted in a tab this one missed says why it closed (${JSON.stringify(st)}; r5-deals-11)`);
    ok(o20a.errs.length===0&&o20b.errs.length===0,"no page errors in round 5's missed-save checks: "+o20a.errs.concat(o20b.errs).slice(0,3).join(" | "));
    await c20.close();

    /* r5-deals-8: unreadable deals with no room for a copy */
    const c21=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true});
    await c21.addInitScript(()=>{ if(!sessionStorage.getItem("seed")){ sessionStorage.setItem("seed","1"); localStorage.setItem("omni.deals.v1","{not json"); }
      const set=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(k==="omni.deals.v1.unreadable") throw new DOMException("The quota has been exceeded.","QuotaExceededError"); return set.call(this,k,v); }; });
    const o21=await open(c21), u=o21.p; await toDeals(u);
    st={store:await msg(u,"dl_store"),btn:await u.evaluate(()=>!!document.getElementById("dl_unread"))};
    await toConsole(u); await u.click("#tl_save"); await settle(u); st.kept=await u.evaluate(()=>localStorage.getItem("omni.deals.v1")); st.msg=await msg(u,"tl_msg");
    await toDeals(u); let fileTxt=null;
    if(st.btn){ const [dl]=await Promise.all([u.waitForEvent("download"),u.click("#dl_unread")]); const fp=path.join(tmp,"unread.txt"); await dl.saveAs(fp); fileTxt=fs.readFileSync(fp,"utf8"); }
    st.after=await u.evaluate(()=>{ try{ return JSON.parse(localStorage.getItem("omni.deals.v1")).length; }catch(e){ return -1; } });
    ok(/no room to copy them aside/.test(st.store)&&st.btn&&st.kept==="{not json"&&/could not be read/.test(st.msg)&&fileTxt==="{not json"&&st.after===1,
       `unreadable deals with no room for a copy are not said to be copied, nothing is saved over them, and they download as a file before saving goes on (${JSON.stringify({kept:st.kept,after:st.after,store:st.store.slice(0,50)})}; r5-deals-8)`);
    ok(o21.errs.length===0,"no page errors in round 5's unreadable-store check: "+o21.errs.slice(0,3).join(" | "));
    await c21.close();

    /* r5-deals-9: a deal stamped at the end of the year 9999; r5-deals-10: the penalty card names the listings it leaves out */
    const c22=await b3.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true}); const o22=await open(c22), y=o22.p;
    await y.evaluate(()=>{ const I=OMNI_BROKER.snap(); localStorage.setItem("omni.deals.v1",JSON.stringify([{id:"dend",name:"End of time",inputs:I,updated:"9999-12-31T23:59:59.999Z"}])); localStorage.removeItem("omni.deals.v1.deleted"); });
    await reload(y); const o22b=await open(c22), y2=o22b.p; await toDeals(y); await toDeals(y2);
    await y.click('#dl_tbl tr[data-id="dend"] .dl-name'); await settle(y); await y.fill('#dl_form input[name="listPrice"]',"3,300,000"); await y.click('#dl_form button[type="submit"]'); await settle(y);
    await has(y2,"dend","d.listPrice===3300000"); await hear(y2);
    await y2.click('#dl_tbl tr[data-id="dend"] .dl-name'); await settle(y2); await y2.fill('#dl_form textarea[name="notes"]',"buyer call on Friday"); await y2.click('#dl_form button[type="submit"]'); await settle(y2);
    await has(y,"dend","d.notes==='buyer call on Friday'"); st={s:await stored(y,"dend")}; await hear(y);
    const [dj2]=await Promise.all([y.waitForEvent("download"),y.click("#dl_json")]); const jp2=path.join(tmp,"dend.json"); await dj2.saveAs(jp2);
    await del2(y,"dend"); await y.setInputFiles("#dl_file",jp2); await y.waitForTimeout(900);
    st.msg=await msg(y,"dl_msg"); st.back=!!(await stored(y,"dend"));
    ok(st.s.listPrice===3300000&&st.s.notes==="buyer call on Friday"&&/^Imported 1 new deal/.test(st.msg)&&st.back,
       `a deal stamped at the end of the year 9999 orders its edits, two tabs' both kept, and a backup restores it after its deletion (${JSON.stringify({lp:st.s.listPrice,notes:st.s.notes,msg:st.msg.slice(0,30),back:st.back})}; r5-deals-9)`);
    await y.evaluate(()=>{ const I=OMNI_BROKER.snap(), V=STATE.r.V, D=[], L=(n,x,p)=>{ for(let i=0;i<n;i++) D.push({id:p+i,name:p+i,status:i%2?"closed":"expired",inputs:I,listPrice:V*x,salePrice:i%2?V:null,updated:"2026-01-01T00:00:00.000Z"}); };
      L(10,1.25,"a"); L(5,3.2,"f"); L(5,.95,"v"); localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
    await reload(y); await toDeals(y); st=(await msg(y,"dl_fit")).replace(/\s+/g," ");
    ok(/5 finished listings priced more than 200% above value, past the survey’s range, are left out/.test(st),`the penalty card says which finished listings it leaves out, those past the survey's range (r5-deals-10)`);
    ok(o22.errs.length===0&&o22b.errs.length===0,"no page errors in round 5's time and penalty checks: "+o22.errs.concat(o22b.errs).slice(0,3).join(" | "));
    await c22.close(); }

  /* a phone with the quality fit showing: the fits panel stays inside its box, its table scrolls */
  const c7=await b3.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});
  ({p,errs}=await open(c7));
  await p.evaluate(()=>{ const I=OMNI_BROKER.snap(), D=[]; let t=7; const r=()=>{ t=(t+0x6D2B79F5)|0; let x=Math.imul(t^(t>>>15),1|t); x=(x+Math.imul(x^(x>>>7),61|x))^x; return ((x^(x>>>14))>>>0)/4294967296; };
    for(let i=0;i<70;i++){ const inp={...I,gm:.2+.6*r(),ret:.5+.45*r(),rec:r(),cc:.05+.5*r(),plt:.05+.5*r(),grw:-.1+.4*r(),own:[.14,.42,.66,.95][Math.floor(r()*4)],mgt:[.08,.36,.66,.92][Math.floor(r()*4)],fin:[.14,.45,.7,.96][Math.floor(r()*4)]};
      const P=dealPredict({inputs:inp,listPrice:inp.ask}); D.push({id:"q"+i,name:"Deal "+i,status:"closed",inputs:inp,listPrice:inp.ask,salePrice:Math.round(P.pExp*(.85+.3*r())),updated:"2026-01-01T00:00:00.000Z"}); }
    localStorage.setItem("omni.deals.v1",JSON.stringify(D)); });
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  st=await p.evaluate(()=>{ const g=document.querySelector(".dl-fits"), gr=g.getBoundingClientRect().right, kids=[...g.querySelectorAll("h3,p,.tw")];
    const tw=g.querySelector(".tw"); return {ready:/Effect on price per peer step/.test(g.textContent),over:Math.max(...kids.map(e=>e.getBoundingClientRect().right))-gr,
      page:document.documentElement.scrollWidth,scroll:tw?tw.scrollWidth>tw.clientWidth:false}; });
  ok(st.ready&&st.over<=1&&st.page<=390,`390px with the quality fit showing: the fits panel's text and table stay inside it (${st.over.toFixed(0)}px over; table scrolls ${st.scroll})`);
  ok(errs.length===0,"no page errors in round 2's deal checks: "+errs.slice(0,3).join(" | "));
  await b3.close();

  fs.rmSync(tmp,{recursive:true,force:true});
  console.log(fail?`${fail} failed`:"all passed"); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
