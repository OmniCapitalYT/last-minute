/* The broker tools in a real browser: the financing check redraws on its own inputs, the worksheet sets SDE and
   revenue, the seller report prints on one page and downloads as a self-contained file, and saved deals survive a
   reload, export, import, edits and opening back into the console. Run: node tests/browser.broker.js  (needs playwright) */
const fs=require("fs"), os=require("os"), path=require("path");
let pw; try{ pw=require("playwright"); }catch(e){ pw=require("/opt/node-tools/node_modules/playwright"); }
const URL="file://"+path.join(__dirname,"..","index.html");
(async()=>{
  const b=await pw.chromium.launch();
  let fail=0; const ok=(c,m)=>{ console.log((c?"ok   ":"FAIL ")+m); if(!c) fail++; };
  const open=async(ctx)=>{ const p=await ctx.newPage(), errs=[]; p.on("pageerror",e=>errs.push(e.message));
    await p.goto(URL); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300); return {p,errs}; };
  const settle=p=>p.evaluate(()=>new Promise(r=>setTimeout(()=>requestAnimationFrame(()=>r()),80)));
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"omni-broker-"));

  const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce",acceptDownloads:true});
  let {p,errs}=await open(ctx);
  ok(await p.evaluate(()=>getComputedStyle(document.getElementById("tl_saveas")).display==="none"&&/Unsaved/.test(document.getElementById("tl_deal").textContent)),
     "a fresh console is an unsaved valuation, with no 'Save as new'");

  /* ---- the financing check ---- */
  const fin=await p.evaluate(()=>{ const s=STATE.s, r=STATE.r, f=debtCheck(s,s.ask,OMNI_BROKER.state().fin,r.V);
    const cells=[...document.querySelectorAll("#fintbl tbody tr:last-child td")].map(td=>td.querySelector("b").textContent);
    return {want:f.dscr.toFixed(2)+"×",cells,cols:document.querySelectorAll("#fintbl thead th").length-1,head:document.querySelector("#fintbl thead").textContent}; });
  ok(fin.cells.includes(fin.want)&&fin.cols>=1&&fin.cols<=3&&/Your ask/.test(fin.head),`the coverage row reads the model's coverage at your ask (${fin.want}; ${fin.cols} asks)`);
  await p.evaluate(()=>{ window.__renders=0; const r0=window.render; window.render=function(){ window.__renders++; return r0.apply(this,arguments); }; });
  await p.click("#f_cash"); await p.keyboard.press("Control+A"); await p.keyboard.type("20",{delay:10}); await p.keyboard.press("Enter"); await settle(p);
  let st=await p.evaluate(()=>({cash:OMNI_BROKER.state().fin.cash,box:document.getElementById("f_cash").value,renders:window.__renders,
    pref:JSON.parse(localStorage.getItem("omni.prefs.v1")).fin.cash,head:document.querySelector("#fintbl tbody tr:nth-child(4) td").textContent}));
  ok(Math.abs(st.cash-.2)<1e-12&&st.box==="20%"&&st.pref===.2&&/20%/.test(st.head),`20 in buyer cash reads as 20%, redraws the table and is remembered (${st.box})`);
  ok(st.renders===0,`typing in the financing check does not re-run the console (${st.renders} renders)`);
  await p.click("#f_note"); await p.keyboard.press("Control+A"); await p.keyboard.type("abc"); await p.keyboard.press("Tab"); await settle(p);
  st=await p.evaluate(()=>({note:OMNI_BROKER.state().fin.note,box:document.getElementById("f_note").value,bad:document.getElementById("f_note").classList.contains("bad")}));
  ok(Math.abs(st.note-.05)<1e-12&&st.box==="5%"&&st.bad,"a rejected entry restores the previous value and stays marked");
  await p.selectOption("#f_type","expansion"); await settle(p);
  ok(await p.evaluate(()=>/1\.15×/.test(document.getElementById("fin_max").textContent)||/meets 1\.15×|below 1\.15×/.test(document.getElementById("fintbl").textContent)),"an expansion is tested at 1.15x");
  await p.selectOption("#f_type","initial"); await p.click("#f_cash"); await p.keyboard.press("Control+A"); await p.keyboard.type("10%"); await p.keyboard.press("Enter"); await settle(p);

  /* ---- the worksheet ---- */
  await p.click("#tl_recast"); await settle(p);
  ok(await p.evaluate(()=>!document.getElementById("recast").hidden&&document.activeElement.id==="rc_ent"&&document.documentElement.classList.contains("dlg-open")),"the worksheet opens as a dialog with focus inside");
  await p.keyboard.press("Escape"); await settle(p);
  ok(await p.evaluate(()=>document.getElementById("recast").hidden&&document.activeElement.id==="tl_recast"),"Escape closes it and returns focus to its button");
  await p.click("#tl_recast"); await settle(p);
  const put=async(k,y,v)=>{ const sel=`.rc-in[data-k="${k}"][data-y="${y}"]`; await p.click(sel); await p.keyboard.press("Control+A"); await p.keyboard.type(v,{delay:5}); await p.keyboard.press("Tab"); };
  await put("rev",0,"6,200,000"); await put("ni",0,"512,000"); await put("owner",0,"180000"); await put("dep",0,"96k"); await put("int",0,"$41,000");
  await put("once",0,"35,000"); await put("nonop",0,"(12,000)"); await put("rev",1,"5.7m"); await put("ni",1,"470k"); await put("owner",1,"175k"); await settle(p);
  st=await p.evaluate(()=>({s0:document.getElementById("rc_s0").textContent,s1:document.getElementById("rc_s1").textContent,
    nonop:document.querySelector('.rc-in[data-k="nonop"][data-y="0"]').value,sum:document.getElementById("rc_sum").textContent,dis:document.getElementById("rc_use").disabled}));
  ok(st.s0==="$852k"&&st.s1==="$645k"&&st.nonop==="$12,000"&&/fell|grew 8\.8%/.test(st.sum)&&!st.dis,`the worksheet sums each year and a deduction typed as (12,000) deducts (${st.s0}, ${st.s1})`);
  await p.click("#rc_use"); await settle(p); await p.waitForTimeout(300);
  st=await p.evaluate(()=>({ern:STATE.s.ern,rev:STATE.s.rev,grw:STATE.s.grw,ask:STATE.s.ask,msg:document.getElementById("tl_msg").textContent,closed:document.getElementById("recast").hidden}));
  ok(st.ern===852000&&st.rev===6.2e6&&Math.abs(st.grw-(6.2/5.7-1))<1e-9&&st.ask===3.24e6&&st.closed&&/From the worksheet/.test(st.msg),
     `'Use in the console' sets SDE, revenue and growth and leaves the ask (SDE ${st.ern}, growth ${(st.grw*100).toFixed(1)}%)`);

  /* ---- saving the deal ---- */
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>({n:JSON.parse(localStorage.getItem("omni.deals.v1")).length,deal:document.getElementById("tl_deal").textContent,
    saveas:getComputedStyle(document.getElementById("tl_saveas")).display,ws:!!JSON.parse(localStorage.getItem("omni.deals.v1"))[0].ws}));
  ok(st.n===1&&/Medical or dental practice, \$852k SDE/.test(st.deal)&&st.saveas!=="none"&&st.ws,`Save deal stores it with its worksheet and names it (${st.deal.trim()})`);
  await p.evaluate(()=>{ const g=document.getElementById("i_gm"); g.value=70; g.dispatchEvent(new Event("input",{bubbles:true})); }); await p.waitForTimeout(500);
  ok(/unsaved changes/.test(await p.evaluate(()=>document.getElementById("tl_deal").textContent)),"changing an input marks unsaved changes");
  await p.click("#tl_save"); await settle(p);
  st=await p.evaluate(()=>({deal:document.getElementById("tl_deal").textContent,gm:JSON.parse(localStorage.getItem("omni.deals.v1"))[0].inputs.gm}));
  ok(!/unsaved/.test(st.deal)&&Math.abs(st.gm-.7)<1e-12,"updating saves the change");

  /* ---- the seller report ---- */
  await p.click("#tl_report"); await settle(p);
  await p.fill("#rp_biz","Lakeside <b>Dental</b>"); await p.fill("#rp_broker","Pat Lee"); await p.fill("#rp_firm","Main Street Advisors"); await p.locator("#rp_firm").blur(); await settle(p);
  st=await p.evaluate(()=>({t:document.getElementById("rp_paper").textContent,html:document.getElementById("rp_paper").innerHTML,on:document.documentElement.classList.contains("rp-on")}));
  ok(st.on&&st.t.includes("Lakeside <b>Dental</b>")&&!st.html.includes("<b>Dental</b>")&&/Earnings basis/.test(st.t)&&/\$852k/.test(st.t)&&/not an appraisal/.test(st.t),
     "the report shows what was typed as text, and the worksheet's earnings basis");
  await p.emulateMedia({media:"print"}); const pdf=await p.pdf({format:"Letter"}); await p.emulateMedia({media:"screen"});
  const pages=(pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g)||[]).length;
  ok(pages===1,`printed, the report is one Letter page (${pages})`);
  const [dl]=await Promise.all([p.waitForEvent("download"),p.click("#rp_dl")]);
  const fpath=path.join(tmp,dl.suggestedFilename()); await dl.saveAs(fpath); const file=fs.readFileSync(fpath,"utf8");
  ok(/^valuation-lakeside-b-dental-b-\d{4}-\d{2}-\d{2}\.html$/.test(dl.suggestedFilename())&&file.startsWith("<!DOCTYPE html>")&&file.includes("all:revert")
     &&file.includes("Lakeside &lt;b&gt;Dental&lt;/b&gt;")&&!/<script|https?:\/\//i.test(file),`the download is one self-contained page with no script or link (${dl.suggestedFilename()})`);
  await p.click("#rp_close"); await settle(p);
  ok(await p.evaluate(()=>{ const P=JSON.parse(localStorage.getItem("omni.prefs.v1")); return P.broker==="Pat Lee"&&P.firm==="Main Street Advisors"&&!document.documentElement.classList.contains("rp-on"); }),
     "the broker and firm are remembered for the next report");

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
  ok(st.d.status==="closed"&&st.d.listPrice===3.4e6&&st.d.listDate==="2025-09-02"&&st.d.salePrice===null&&st.bad&&/salePrice/.test(st.msg)&&/sale price/.test(st.msg),
     "a bad sale price is refused and marked; the rest saves, with a note on what the record still needs");
  await p.fill('#dl_form input[name="salePrice"]',"3.1M"); await p.fill('#dl_form input[name="name"]',"=HYPERLINK(\"x\")"); await p.click('#dl_form button[type="submit"]'); await settle(p);
  st=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1"))[0]; const P=dealPredict(d);
    return {sale:d.salePrice,row:document.querySelector("#dl_tbl tbody tr").textContent,ratio:(d.salePrice/P.priceMed).toFixed(2)+"×"}; });
  ok(st.sale===3.1e6&&st.row.includes(st.ratio),`the table shows the sale against the model's median at the listing price (${st.ratio})`);
  /* duplicates for the record, then the two-press delete */
  await p.click('#dl_form button[data-act="dup"]'); await settle(p); await p.click('#dl_form button[data-act="dup"]'); await settle(p);
  ok(await p.evaluate(()=>document.querySelectorAll("#dl_tbl tbody tr[data-id]").length===3&&/Sale price ÷ the model's median\s*\d\.\d\d×/.test(document.getElementById("dl_track").textContent)),
     "with three closed deals the price record appears");
  await p.check("#dl_calib"); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.prefs.v1")).calib===true),"the track-record opt-in is remembered");
  await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(()=>document.querySelectorAll("#dl_tbl tbody tr[data-id]").length===3&&/Press again/.test(document.querySelector('#dl_form button[data-act="del"]').textContent)),"delete asks for a second press");
  await p.click('#dl_form button[data-act="del"]'); await settle(p);
  ok(await p.evaluate(()=>JSON.parse(localStorage.getItem("omni.deals.v1")).length===2),"the second press deletes");
  /* exports */
  const [dj]=await Promise.all([p.waitForEvent("download"),p.click("#dl_json")]); const jp=path.join(tmp,"deals.json"); await dj.saveAs(jp);
  const J=JSON.parse(fs.readFileSync(jp,"utf8"));
  ok(J.format==="omni.deals"&&J.version===1&&J.deals.length===2&&J.deals.every(d=>d.inputs&&d.inputs.ind==="medical"),"Export (JSON) writes every deal with its inputs");
  const [dc]=await Promise.all([p.waitForEvent("download"),p.click("#dl_csv")]); const cp=path.join(tmp,"deals.csv"); await dc.saveAs(cp);
  const csv=fs.readFileSync(cp,"utf8").split("\r\n");
  ok(csv[0].startsWith("id,name,status,industry")&&csv.length===4&&csv.slice(1,3).every(l=>/^d[0-9a-z]+,"?'=HYPERLINK/.test(l)||/,Medical or dental/.test(l)),"Export (CSV) writes a row a deal and defuses a formula-like name");
  ok(csv.slice(1,3).some(l=>l.includes("'=HYPERLINK")),"a name that starts with = is written as text in the CSV");
  /* import: one new, one newer copy of an existing deal, one older copy, one invalid */
  const ex=J.deals[0], newer={...ex,name:"Imported update",updated:new Date(Date.now()+864e5).toISOString()}, older={...J.deals[1],name:"Stale",updated:"2020-01-01T00:00:00.000Z"};
  const fresh={...ex,id:"dimported1",name:"Imported new deal"}, bad={id:"x",inputs:{ind:"nope"}};
  const ip=path.join(tmp,"import.json"); fs.writeFileSync(ip,JSON.stringify({format:"omni.deals",version:1,deals:[newer,older,fresh,bad]}));
  await p.setInputFiles("#dl_file",ip); await p.waitForTimeout(600);
  st=await p.evaluate(()=>({names:JSON.parse(localStorage.getItem("omni.deals.v1")).map(d=>d.name),msg:document.getElementById("dl_msg").textContent}));
  ok(st.names.length===3&&st.names.includes("Imported update")&&st.names.includes("Imported new deal")&&!st.names.includes("Stale")&&/1 new deal and updated 1; 2 skipped/.test(st.msg),
     `import adds new deals, takes newer copies and skips older or invalid ones (${st.msg})`);
  /* open a deal into the console */
  await p.click('.tab[data-v="console"]'); await p.waitForTimeout(1500);
  await p.evaluate(()=>{ IN.ern=5e5; render(); }); await settle(p);
  await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  const want=await p.evaluate(()=>{ const d=JSON.parse(localStorage.getItem("omni.deals.v1")).find(x=>x.name==="Imported new deal"); return d.inputs; });
  await p.click('#dl_tbl tr:has(.dl-name:text("Imported new deal")) button[data-act="open"]'); await p.waitForTimeout(1800);
  st=await p.evaluate(()=>({ern:STATE.s.ern,gm:STATE.s.gm,vis:!document.getElementById("view-console").hidden,deal:document.getElementById("tl_deal").textContent}));
  ok(st.vis&&st.ern===want.ern&&Math.abs(st.gm-want.gm)<1e-12&&/Imported new deal/.test(st.deal)&&!/unsaved/.test(st.deal),
     `opening a deal puts its inputs in the console, with nothing unsaved (SDE ${st.ern} for ${want.ern}; ${st.deal.trim()})`);
  ok(await p.evaluate(()=>!document.getElementById("tl_cal").hidden&&/Your record/.test(document.getElementById("tl_cal").textContent)),"the opted-in price record shows beside the console");
  ok(errs.length===0,"no page errors: "+errs.slice(0,3).join(" | "));
  /* a reload keeps the deals and the settings */
  await p.reload(); await p.waitForFunction(()=>!document.getElementById("boot"),null,{timeout:90000}); await p.waitForTimeout(300);
  ok(await p.evaluate(()=>OMNI_BROKER.state().deals.length===3&&OMNI_BROKER.state().prefs.broker==="Pat Lee"&&document.getElementById("f_cash").value==="10%"),"a reload keeps the deals and preferences");
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

  /* ---- a phone: no sideways scrolling on any of it ---- */
  const c3=await b.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});
  ({p,errs}=await open(c3));
  const wide=async()=>p.evaluate(()=>document.documentElement.scrollWidth);
  ok(await wide()<=390,"390px console with the toolbar and financing check: no sideways scroll");
  await p.click("#tl_recast"); await settle(p);
  ok(await wide()<=390&&await p.evaluate(()=>{ const t=document.querySelector("#recast .tw"); return t.scrollWidth<=t.clientWidth+1; }),"390px worksheet: three years fit without scrolling");
  await p.keyboard.press("Escape"); await p.click("#tl_report"); await settle(p);
  ok(await wide()<=390,"390px report: no sideways scroll");
  await p.keyboard.press("Escape"); await p.click("#tl_save"); await p.click('.tab[data-v="deals"]'); await p.waitForTimeout(1500);
  ok(await wide()<=390&&await p.evaluate(()=>getComputedStyle(document.querySelector("#dl_tbl tbody tr")).display==="block"),"390px Deals tab: each deal is a card");
  ok(errs.length===0,"no page errors on a phone: "+errs.slice(0,3).join(" | "));
  await c3.close();

  await b.close(); fs.rmSync(tmp,{recursive:true,force:true});
  console.log(fail?`${fail} failed`:"all passed"); process.exit(fail?1:0);
})().catch(e=>{ console.error(e); process.exit(1); });
