/* Builds foruse.html from index.html: the same app without the equation documentation,
   without the fitted / aggregate / judgment provenance labels, and without the Data & parameters tab.
   index.html is the source of truth and is not changed. Every edit below names text that must occur exactly
   once (or, for the repeated blocks, at least once), so a change to index.html that moves one of them stops
   the build instead of shipping a half-stripped page.
   Run: node tools/build_foruse.js            (writes foruse.html next to index.html)
        node tools/build_foruse.js --check    (exit 1 if foruse.html is stale) */
"use strict";
const fs=require("fs"), path=require("path");
const ROOT=path.join(__dirname,".."), SRC=path.join(ROOT,"index.html"), OUT=path.join(ROOT,"foruse.html");
let s=fs.readFileSync(SRC,"utf8");
const done=[];

function once(a,b,what){ const n=s.split(a).length-1; if(n!==1) throw new Error(`${what}: expected 1 match, found ${n}`); s=s.replace(a,()=>b); done.push(what); }
/* the page's markup: from the tab bar to the footer (the three views). Block cuts stay inside it, so a template
   string in a script that happens to hold the same text is never touched */
function markup(){ const a=s.indexOf(`<button class="tab on" data-v="console">`), b=s.indexOf(`<footer id="foot"></footer>`);
  if(a<0||b<0||b<a) throw new Error("markup anchors not found"); return [a,b]; }
/* the element that opens at i, through its matching close tag (same tag name, nesting counted) */
function blockEnd(i,tag){
  const re=new RegExp(`<${tag}\\b|</${tag}>`,"g"); re.lastIndex=i; let depth=0, m;
  while((m=re.exec(s))){ depth+=m[0][1]==="/"?-1:1; if(depth===0) return m.index+m[0].length; }
  throw new Error(`unclosed <${tag}> at ${i}`);
}
/* remove (or replace) every element that opens with the text open, inside the markup; the search resumes after each
   cut, so a replacement that holds the same text is not cut again */
function cutBlocks(open,tag,what,min,repl){ let n=0, from=markup()[0];
  for(;;){ const end=markup()[1], i=s.indexOf(open,from); if(i<0||i>=end) break;
    const e=blockEnd(i,tag), r=repl||""; s=s.slice(0,i)+r+s.slice(e); from=i+r.length; n++; }
  if(n<(min||1)) throw new Error(`${what}: expected at least ${min||1} blocks, found ${n}`); done.push(`${what} (${n})`); }

/* ---- 1. the Data & parameters tab: no button; an inert, pre-filled stub keeps the tab code's lookups valid and stops
        the data tab from ever being built */
once(`\n  <button class="tab" data-v="data">Data &amp; parameters</button>`,"","Data tab button");
cutBlocks(`<div id="view-data" hidden>`,"div","Data tab view",1,`<div id="view-data" hidden><div id="dataviews"><!-- not in this version --></div></div>`);

/* ---- 2. the method and provenance section (its equations and the sources list with its badges) */
cutBlocks(`<!-- methodology -->\n    <section class="sec">`,"section","method and provenance section",1,"");
once(`$("srcs").innerHTML=\``,`if($("srcs")) $("srcs").innerHTML=\``,"sources list guard");

/* ---- 3. every equation card in the console; the value gap's figure, whose column partner was its equation, takes the
        panel's width */
once(`<div class="split">\n          <div>\n            <div class="k gap-k">`,`<div class="gap-solo">\n          <div>\n            <div class="k gap-k">`,"value gap column");
cutBlocks(`<div class="eq"><div class="lbl">`,"div","equation cards",10,"");
cutBlocks(`<div class="eq" style="margin-top:0"><div class="lbl">`,"div","equation cards (first in a panel)",1,"");
{ const [a,b]=markup(), mid=s.slice(a,b), re=/\n[ \t]*<div>\s*<\/div>/g, n=(mid.match(re)||[]).length;
  if(n<1) throw new Error("emptied equation columns: found none"); s=s.slice(0,a)+mid.replace(re,"")+s.slice(b); done.push(`emptied columns (${n})`); }

/* the Deals tab's "Toward fitting the judgment numbers" section, which documents how the deals would fit the model's
   judgment parameters, and the lede's sentence that announces it */
cutBlocks(`<section class="sec"><div class="sec-head"><h2>Toward fitting the judgment numbers</h2></div>`,"section","Deals tab fitting section",1,"");
once("$(\"dl_fit\").innerHTML=`","if($(\"dl_fit\")) $(\"dl_fit\").innerHTML=`","fitting section guard");
once(` With enough deals the same records fit
    the two judgment numbers that move its advice most: how hard pricing above value cuts the chance of a sale, and how much
    each quality factor is worth.`,"","Deals lede's fitting sentence");

/* ---- 4. the provenance badges written into the page (the console's KPI labels); the ones scripts write later are
        hidden by the style block below */
{ const re=/ ?<span class="pv [faj]"[^>]*>(?:<i><\/i>)?[^<]*<\/span>/g; const n=(s.match(re)||[]).length; if(n<8) throw new Error(`KPI badges: found ${n}`);
  s=s.replace(re,""); done.push(`badges in the markup (${n})`); }

/* the time tile's badge is updated without a null check: it gets a detached stand-in */
once(`{ const pv=$("o_t_pv"), j=r.tMult>1.0005;`,`{ const pv=$("o_t_pv")||document.createElement("span"), j=r.tMult>1.0005;`,"time badge stand-in");

/* ---- 5. references to the framework's equation sections in the section heads */
{ const re=/<span class="ref">framework §[^<]*<\/span>/g; const n=(s.match(re)||[]).length; if(n<8) throw new Error(`framework refs: found ${n}`);
  s=s.replace(re,""); done.push(`framework references (${n})`); }

/* ---- 6. the report: no tier badges on its figures (on screen, in print and in the downloaded copy) */
once("const B=(c,t)=>`<span class=\"rp-b rp-${c}\">${t}</span>`, BX=(c,t)=>`<span class=\"rp-bx\">${B(c,t)}<span class=\"rp-b rp-j rp-x\">× judgment</span></span>`;",
     "const B=(c,t)=>\"\", BX=(c,t)=>\"\";   /* foruse: no provenance badges */","report badges");

/* its sources line keeps the sources, drops the badge legend; and with the badges empty, a header cell loses the line
   break that held one and no word is left standing before a stop or a colon */
once(` Labels: \${fit} estimated from data; \${agg} read from published figures or
    rules; \${jdg} set by reasoning where no data measure the number; × judgment: a judgment input also moves it, here \${how.join("; ")}.</p>`,
     `</p>`,"report badge legend");
once("return `<article class=\"rp\">${head}${value}${asks}${finance}${drivers}${earnP}${foot}</article>`;",
     "return `<article class=\"rp\">${head}${value}${asks}${finance}${drivers}${earnP}${foot}</article>`.replace(/<br><\\/th>/g,\"</th>\").replace(/ +([.,;:])(?=[\\s<]|$)/g,\"$1\");",
     "report spacing without badges");

/* ---- 7. text that points at what is gone */
once(`. Value and survival risk are fitted to
\${MODELS.value.n_fit.toLocaleString("en-US")} closed sales and \${MODELS.risk.n_fit.toLocaleString("en-US")} SBA
acquisition loans, and time to close to IBBA&rsquo;s per-band histograms of closed deals; closing probability is a
market aggregate conditioning on deal size and price gap, with labelled judgment for a buyer pool thinner than typical
(calibrated scale, judgment shape) and for time above value; the score,
buyer model and optimizer remain judgment. Badges on every output say which.
Report ranges`,`. Value and survival risk are estimated from
\${MODELS.value.n_fit.toLocaleString("en-US")} closed sales and \${MODELS.risk.n_fit.toLocaleString("en-US")} SBA
acquisition loans, time to close from IBBA&rsquo;s histograms of closed deals, and closing probability from market
surveys by deal size and price gap.
Report ranges`,"footer provenance");
once(`on the size of the price-gap penalty (a judgment scale), which the data do not settle.`,`on the size of the price-gap penalty, which the data do not settle.`,"optimizer note's tag");
once(`in wages (BLS, aggregate; its rank by firm size is judgment)`,`in wages (BLS)`,"owner pay note's tag");
once("binds`} (a judgment), so read it as","binds`}, so read it as","optimizer cap tag");
once("cap on the ask (a judgment), not an optimum","cap on the ask, not an optimum","report cap tag");
once("cap on the ask binds`} (a judgment)`","cap on the ask binds`}`","report walk-away cap tag");
once(" (overpricing costs time: a labelled judgment, see the Data tab).`"," (overpricing costs time).`","time note's Data tab pointer");
once(`so the downside scenarios are narrower than the value range in '\n      +'the Data tab. That share`,
     `so the downside scenarios are narrower than the value model&rsquo;s '\n      +'own range. That share`,"realisation note's Data tab pointer");

/* ---- 8. tier chips and tags the console writes as it renders: the multiple build's rows are named for what they are,
        not for how they were estimated */
{ const chip=` <span class="st free">judgment</span>`, n=s.split(chip).length-1; if(n<3) throw new Error(`judgment chips: found ${n}`);
  s=s.split(chip).join(""); done.push(`judgment chips (${n})`); }
once("<tr class=\"lg\"><td>Judgment multiple <span class=\"st free\">not used</span></td>","<tr class=\"lg\"><td>Factor-stack multiple <span class=\"st free\">not used</span></td>","factor-stack row name");
once("<tr class=\"sum\"><td><b>Fitted multiple</b> <span class=\"st pub\">BIZCOMPS</span>","<tr class=\"sum\"><td><b>Market multiple</b> <span class=\"st pub\">BIZCOMPS</span>","market multiple row name");
once("plus the spread lenders charge on a loan this size (fitted).`","plus the spread lenders charge on a loan this size.`","SBA spread tag");

once(`Every model in the framework runs
        and shows the working behind each number.</p>`,`Every model in the framework runs
        live, and every number updates as you go.</p>`,"masthead line about the working");

/* ---- 9. what scripts add later: hidden, and no badge, key, equation card or tier chip takes space */
once(`<title>The Omni Method</title>`,`<title>The Omni Method</title>
<style id="foruse">
/* foruse: no equation documentation, no provenance labels, no Data tab */
.pv,.pvkey,.eq,.rp-b,.rp-bx,.v8d-ref,.tab[data-v="data"],#view-data{display:none!important}
</style>
<meta name="omni-version" content="foruse">`,"foruse style block");

/* --check: fail when foruse.html is not what index.html builds (the tests run it, so the two never drift apart) */
if(process.argv.includes("--check")){
  const cur=fs.existsSync(OUT)?fs.readFileSync(OUT,"utf8"):"";
  if(cur!==s){ console.error("foruse.html is out of date: run node tools/build_foruse.js"); process.exit(1); }
  console.log("foruse.html is up to date ("+done.length+" edits)");
} else {
  fs.writeFileSync(OUT,s);
  console.log("foruse.html written ("+(s.length/1e6).toFixed(2)+" MB):\n  "+done.join("\n  "));
}
