"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const esc = x => String(x ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const S = {data:null, manifest:null, image:0, threshold:0.15, selected:null};
  const colors={yoloe:"#f5b977",owlv2:"#8bc6ff"};
  const short = x => String(x).slice(0,18)+"…";
  const sha = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)), b=>b.toString(16).padStart(2,"0")).join("");
  async function get(url) {
    const r=await fetch(url,{cache:"no-store"});
    if(!r.ok) throw Error("HTTP "+r.status+" "+url);
    return r.arrayBuffer();
  }
  function allVisible(){
    const ph=S.data.images[S.image];
    return ph.model_predictions.filter(p=>$("show-"+p.model).checked && p.confidence>=S.threshold);
  }
  function sourceUrl(path) {
    return "https://github.com/biobitworks/baebugs/blob/"+S.data.source_commit+"/"+path.split("/").map(encodeURIComponent).join("/");
  }
  function render(){
    const photo=S.data.images[S.image], boxes=allVisible();
    $("photo-select").value=String(S.image);
    $("resolution").textContent=photo.width+" × "+photo.height;
    $("source-photo").src=photo.image_path;
    $("source-photo").alt=photo.photo.includes("two_on_floor")?
      "Two printed PA12 insect toys on rough pavement":"Printed PA12 insect toys inside a container";
    $("photo-hash").textContent=photo.source_photo.sha256;
    $("results-hash").textContent=S.data.results_atom.sha256;
    $("graph-root").textContent=S.data.source_evidence_root;
    $("rights").textContent=photo.source_photo.claim+" · "+photo.source_photo.licence+" (repository declaration)";
    $("source-link").href=sourceUrl(photo.source_photo.path);
    $("leaf-link").href="../#leaf:"+encodeURIComponent(photo.source_photo.path);
    $("verify-result").textContent="";
    $("visible-count").textContent=boxes.length+" of "+photo.model_predictions.length+" recorded boxes visible · no new inference";
    if(!boxes.some(p=>p.content_sha256===S.selected))S.selected=null;
    const svg=$("boxes");
    svg.setAttribute("viewBox","0 0 "+photo.width+" "+photo.height);
    svg.setAttribute("preserveAspectRatio","xMidYMid meet");
    svg.innerHTML=boxes.map(p=>{
      const [x,y,x1,y1]=p.bbox_xyxy_pixels, name=p.model.toUpperCase()+" "+Number(p.confidence).toFixed(3);
      const w=Math.max(165,30+name.length*18), capX=Math.min(x,photo.width-w), capY=y>50?y-47:y1+5;
      return '<g><rect class="detbox'+(S.selected===p.content_sha256?' selected':'')+
        '" x="'+x+'" y="'+y+'" width="'+(x1-x)+'" height="'+(y1-y)+'" stroke="'+colors[p.model]+
        '"/><g class="box-label"><rect x="'+capX+'" y="'+capY+'" width="'+w+'" height="41" rx="7"/>'+
        '<text x="'+(capX+10)+'" y="'+(capY+29)+'">'+esc(name)+'</text></g></g>';
    }).join("");
    $("prediction-list").innerHTML=boxes.length?boxes.map((p,i)=>{
      const order=p.order_inference;
      return '<button class="prediction-item" type="button" aria-pressed="'+(S.selected===p.content_sha256)+
        '" data-proposal="'+p.content_sha256+'"><span class="marker" style="color:'+colors[p.model]+
        ';border-color:'+colors[p.model]+'">'+(i+1)+'</span><span><strong>'+esc(p.model.toUpperCase())+
        ' · '+esc(p.label)+'</strong><small>confidence '+Number(p.confidence).toFixed(3)+
        ' · '+esc(order?order.label+" (ORDER guess)":"toy candidate")+'</small></span></button>';
    }).join(""):'<p class="selected-detail">No predictions match the active filters.</p>';
    const p=boxes.find(b=>b.content_sha256===S.selected);
    $("selected-detail").innerHTML=p?
      '<strong>Selected '+esc(p.model.toUpperCase())+' box</strong><dl>'+
      '<dt>Label</dt><dd>'+esc(p.label)+'</dd>'+
      '<dt>Score</dt><dd>'+Number(p.confidence).toFixed(3)+' (model output)</dd>'+
      '<dt>Bounds (XYXY)</dt><dd><code>['+p.bbox_xyxy_pixels.join(", ")+'] px</code></dd>'+
      '<dt>ORDER guess</dt><dd>'+(p.order_inference?esc(p.order_inference.label)+
      ' ('+p.order_inference.conf+')':'NOT_COMPUTED')+'</dd>'+
      '<dt>Content SHA</dt><dd><code>'+short(p.content_sha256)+'</code></dd>'+
      '<dt>Context SHA</dt><dd><code>'+short(p.context_sha256)+'</code></dd>'+
      '<dt>Ground truth</dt><dd>NOT_VERIFIED</dd>'+
      '<dt>Recovery</dt><dd>NOT_TESTED</dd></dl>':
      '<strong>Select a bounding box</strong><p>Each prediction is independently addressable. Boxes may overlap one toy, miss targets, or have incorrect order guesses.</p>';
  }
  async function verify(){
    $("verify-button").disabled=true;
    $("verify-result").textContent="Verifying public bytes…";
    try{
      const photo=S.data.images[S.image], ref=S.data.source_commit;
      const src="https://raw.githubusercontent.com/biobitworks/baebugs/"+ref+"/"+photo.source_photo.path;
      const [pubImage,catalog,sourceImage]=await Promise.all([
        get(photo.image_path),get("detections.json"),get(src)
      ]);
      const [hi,hc,hs]=await Promise.all([sha(pubImage),sha(catalog),sha(sourceImage)]);
      const m=S.manifest.files;
      const ok=hi===photo.web_image_sha256 && hi===m["detection/"+photo.image_path]?.sha256 &&
        hc===m["detection/detections.json"]?.sha256 && hs===photo.source_photo.sha256;
      $("verify-result").textContent=ok?
        "PASS: original source photo, public photo derivative and prediction catalog matched exact SHA-256. Scientific accuracy remains unverified.":
        "FAILED: digest mismatch; viewer cannot be admitted as verified evidence.";
    }catch(e){
      $("verify-result").textContent="NOT_VERIFIED: "+e.message+"; source or network readback incomplete.";
    }finally{$("verify-button").disabled=false;}
  }
  async function init(){
    try{
      const [raw,manifestBytes]=await Promise.all([get("detections.json"),get("../deployment-manifest.json")]);
      const data=JSON.parse(new TextDecoder().decode(raw));
      const manifest=JSON.parse(new TextDecoder().decode(manifestBytes));
      if(data.schema!=="baebugs.RecordedBoundingBoxGallery.v1" || data.images?.length!==2) throw Error("Wrong catalog schema");
      if(await sha(raw)!==manifest.files["detection/detections.json"]?.sha256) throw Error("Catalog hash mismatch");
      if(data.source_evidence_root!==manifest.evidence_pack_root || data.source_commit!==manifest.source_ref) throw Error("Source pack identity drift");
      S.data=data;S.manifest=manifest;
      $("photo-select").innerHTML=data.images.map((v,i)=>'<option value="'+i+'">'+esc(v.photo.includes("two_on_floor")?
        "Two PA12 toys · pavement":"PA12 toy collection · box")+'</option>').join("");
      render();
      $("visible-count").setAttribute("data-admitted","true");
    }catch(e){
      $("visible-count").textContent="FAILED — evidence catalog not admitted";
      $("prediction-list").textContent=e.message;
      $("verify-result").textContent="Source identity requires repair before interpreting predictions.";
    }
  }
  $("photo-select").addEventListener("change",e=>{S.image=Number(e.target.value);S.selected=null;render()});
  ["show-yoloe","show-owlv2"].forEach(id=>$(id).addEventListener("change",render));
  $("confidence").addEventListener("input",e=>{S.threshold=Number(e.target.value);$("threshold-value").textContent=S.threshold.toFixed(2);render()});
  $("reset").addEventListener("click",()=>{S.selected=null;S.threshold=0.15;$("show-yoloe").checked=true;$("show-owlv2").checked=true;$("confidence").value=".15";$("threshold-value").textContent="0.15";render()});
  $("verify-button").addEventListener("click",verify);
  $("prediction-list").addEventListener("click",e=>{const button=e.target.closest("[data-proposal]");if(button){S.selected=button.dataset.proposal;render()}});
  init();
})();