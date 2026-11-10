/* Builds landing.html and ai-vince.html from their sources in tools/ (landing.src.html, ai-vince.src.html): each page's
   design with the app's own fonts, read from index.html so the pages stay in step with it.
   Run: node tools/build_landing.js */
const fs=require("fs"), path=require("path"), R=path.join(__dirname,"..");
const L=fs.readFileSync(path.join(R,"index.html"),"utf8").split("\n");
const want=[["Bricolage Grotesque","600"],["Bricolage Grotesque","700"],["Bricolage Grotesque","800"],["Schibsted Grotesk","400"],["Schibsted Grotesk","500"]];
const faces=want.map(([f,w])=>L.find(l=>l.startsWith("@font-face{font-family:'"+f+"';font-style:normal;font-weight:"+w+";")));
if(faces.some(x=>!x)) throw new Error("a font face was not found in index.html");
for(const [src,out] of [["landing.src.html","landing.html"],["ai-vince.src.html","ai-vince.html"]]){
  fs.writeFileSync(path.join(R,out),fs.readFileSync(path.join(__dirname,src),"utf8").replace("/*FONTS*/",()=>faces.join("\n")));
  console.log(out+" written");
}
