/* Mr. Bob on screen: his photo, with a little life.
   Exposes window.MrBobCat = {state, hop(n), mount(el), onTap}. */
(function(){
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
const pic=document.createElement("div");
pic.className="bobpic";pic.dataset.state="idle";
pic.innerHTML='<div class="bobglow"></div><div class="bobcard glass"><img src="/assets/bob.jpg" alt="Mr. Bob, a white and brown tabby cat, napping happily in the sun" draggable="false"></div>';

let state="idle";
const api={
  get state(){return state},
  set state(s){state=s;pic.dataset.state=s},
  hop(n){pic.classList.remove("hop");void pic.offsetWidth;pic.classList.add("hop");for(let i=0;i<(n||0);i++)heart(i)},
  mount(el){if(el)el.appendChild(pic)},
  onTap:null,
};
window.MrBobCat=api;

function heart(i){
  const h=document.createElement("span");h.className="heart";h.textContent="♥";
  h.style.left=(38+Math.random()*24)+"%";h.style.animationDelay=(i*.12)+"s";
  pic.appendChild(h);setTimeout(()=>h.remove(),2000);
}

const lines=["Meow! Ami Mr. Bob.","Hehe, sursuri lage!","Ki khobor, Jonayed?","Purr… always here for you.","Shh… roder moddhe ghumacchilam."];
pic.addEventListener("click",()=>{api.hop(3);if(api.onTap)api.onTap(lines[Math.floor(Math.random()*lines.length)])});

// the photo tilts toward your pointer, like a card in your hand
if(!reduce)addEventListener("pointermove",e=>{
  const r=pic.getBoundingClientRect();if(!r.width)return;
  const x=(e.clientX-(r.left+r.width/2))/innerWidth,y=(e.clientY-(r.top+r.height/2))/innerHeight;
  pic.style.setProperty("--rx",(-y*16).toFixed(2)+"deg");pic.style.setProperty("--ry",(x*20).toFixed(2)+"deg");
},{passive:true});

api.mount(document.getElementById("stage"));
})();
