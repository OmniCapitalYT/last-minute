/* Builds landing.html from tools/landing.src.html: the page's design with the app's own fonts (read from index.html, so the
   two stay in step). Run: node tools/build_landing.js */
const fs=require("fs"), path=require("path"), R=path.join(__dirname,"..");
const L=fs.readFileSync(path.join(R,"index.html"),"utf8").split("\n");
const want=[["Bricolage Grotesque","600"],["Bricolage Grotesque","700"],["Bricolage Grotesque","800"],["Schibsted Grotesk","400"],["Schibsted Grotesk","500"]];
const faces=want.map(([f,w])=>L.find(l=>l.startsWith("@font-face{font-family:'"+f+"';font-style:normal;font-weight:"+w+";")));
if(faces.some(x=>!x)) throw new Error("a font face was not found in index.html");
fs.writeFileSync(path.join(R,"landing.html"),fs.readFileSync(path.join(__dirname,"landing.src.html"),"utf8").replace("/*FONTS*/",()=>faces.join("\n")));
console.log("landing.html written");
