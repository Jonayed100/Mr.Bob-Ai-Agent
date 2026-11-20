/* Mr. Bob dashboard: talks to the FastAPI backend. */
(function(){
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
const cat=window.MrBobCat;
if(/Chrome\//.test(navigator.userAgent))document.documentElement.classList.add("chrome");

let data=null,lang="auto",busy=false,wake=null,handsFree=false,wakeOn=false;
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
try{wakeOn=!!localStorage.getItem("mrbob-wake")&&!!SR}catch(e){}
try{lang=localStorage.getItem("mrbob-lang")||"auto"}catch(e){}

/* ---------- api ---------- */
async function api(path,opts={}){
  const res=await fetch("/api"+path,{credentials:"same-origin",...opts,headers:{...(opts.body&&!(opts.body instanceof FormData)?{"Content-Type":"application/json"}:{}),...(opts.headers||{})}});
  if(res.status===401){showLogin();throw new Error("login")}
  const body=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(body.detail||("Error "+res.status));
  return body;
}
const post=(p,b)=>api(p,{method:"POST",body:JSON.stringify(b||{})});
function toast(t){const el=$("#toast");el.textContent=t;el.hidden=false;clearTimeout(toast.t);toast.t=setTimeout(()=>el.hidden=true,3200)}

/* ---------- login ---------- */
function showLogin(){$("#login").hidden=false;setTimeout(()=>$("#pw").focus(),50)}
$("#loginForm").addEventListener("submit",async e=>{
  e.preventDefault();$("#loginErr").textContent="";
  try{await post("/login",{password:$("#pw").value});$("#login").hidden=true;$("#pw").value="";load()}
  catch(err){$("#loginErr").textContent=err.message==="login"?"Wrong password":err.message}
});
$("#logout").addEventListener("click",async()=>{await post("/logout").catch(()=>{});location.reload()});

/* ---------- render ---------- */
function render(d){
  data=d;
  $("#hello").textContent=`Hi ${d.owner}, I'm Mr. Bob.`;
  const w=d.weather;
  if(w){$("#wxCity").textContent=w.city;$("#temp").textContent=w.temp_c+"°";
    $("#wx").innerHTML=`${esc(w.condition)}${w.aqi!=null?` · AQI ${w.aqi}, ${esc(w.aqi_label)}`:""}<br>${w.rain_at?`Rain likely around ${esc(w.rain_at)}`:"No rain expected"}`}
  $("#dayName").textContent=d.now.day;$("#dayNum").textContent=d.now.date;
  $("#events").innerHTML=d.events.length?d.events.map(e=>`<div class="ev"><i></i><div><b>${esc(e.title)}</b><span>${esc(e.time)}${e.where?" · "+esc(e.where):""}</span></div></div>`).join(""):`<p class="empty">${d.google.connected?"Nothing on your calendar today.":"Connect Google in Settings to see your calendar."}</p>`;
  $("#rems").innerHTML=d.reminders.length?d.reminders.map(r=>`<div class="rem ${r.done?"done":""}" data-id="${r.id}" data-done="${r.done}" role="checkbox" aria-checked="${r.done}" tabindex="0"><i></i><span>${esc(r.text)}</span><small>${esc(r.when)}</small></div>`).join(""):`<p class="empty">No reminders. Ask me to add one!</p>`;
  const icon={gmail:["#e0142f","M"],calendar:["#ff3b30","C"],weather:["#0a84ff","W"]};
  $("#alerts").innerHTML=d.alerts.length?d.alerts.map(a=>{const[c,l]=icon[a.source]||["#8e8e93","•"];return`<div class="item"><span class="app" style="background:${a.level==="high"?"#e0142f":c}">${l}</span><div><b>${esc(a.title)}</b><span>${esc(a.sender||a.detail)} · ${esc(a.when)}</span></div>${a.level==="high"?'<span class="tag">Important</span>':""}</div>`}).join(""):`<p class="empty">Nothing important right now. Purr.</p>`;
  $("#sugs").innerHTML=d.suggestions.length?d.suggestions.map(s=>`<div class="card glass"><p>${esc(s.text)}</p><div class="acts"><button class="chip ${s.feedback==="up"?"chosen":""}" data-id="${s.id}" data-v="up">Useful</button><button class="chip ${s.feedback==="down"?"chosen":""}" data-id="${s.id}" data-v="down">Not useful</button></div></div>`).join(""):`<div class="card glass"><p class="empty">No tips yet. Tap Refresh.</p></div>`;
  const colors={gmail:"#e0142f",calendar:"#ff3b30",weather:"#0a84ff",telegram:"#2aabee"};
  $("#conns").innerHTML=d.connections.map(c=>`<div class="srow"><span class="app" style="background:${colors[c.name]||"#8e8e93"}">${esc(c.label[0])}</span><div><b>${esc(c.label)}</b><span>${esc(c.detail)}</span></div><button class="sw" role="switch" aria-label="${esc(c.label)}" aria-checked="${c.enabled}" data-name="${c.name}"></button></div>`).join("");
  $("#accounts").innerHTML=
    `<div class="srow"><span class="app" style="background:#4285f4">G</span><div><b>Google account</b><span>${d.google.connected?"Gmail and Calendar connected":d.google.ready?"Not connected":"Add Google keys to .env first"}</span></div>${d.google.ready?(d.google.connected?`<button class="chip" id="gOff">Disconnect</button>`:`<a class="chip linkbtn" href="/api/google/connect">Connect</a>`):""}</div>`+
    `<div class="srow"><span class="app" style="background:#2aabee">T</span><div><b>Telegram</b><span>${d.telegram.ready?(d.telegram.chat_set?"Linked to your account":"Open your bot, send /start and tap “Share my number”"):"Add TELEGRAM_BOT_TOKEN to .env"}</span></div></div>`+
    `<div class="srow"><span class="app" style="background:#25d366">W</span><div><b>WhatsApp</b><span>${d.whatsapp.alerts||d.whatsapp.chat?[d.whatsapp.alerts?"Alerts on":"",d.whatsapp.chat?"Two-way chat on":""].filter(Boolean).join(" · "):"Add CALLMEBOT_APIKEY to .env for alerts"}</span></div></div>`+
    `<div class="srow"><span class="app" style="background:#e0142f">B</span><div><b>“Hey Bob” hands-free</b><span>${SR?"Say “Hey Bob” while this page is open":"Needs Chrome, Edge or Safari"}</span></div><button class="sw" role="switch" id="wakeSw" aria-label="Hey Bob hands-free" aria-checked="${wakeOn}"></button></div>`+
    `<div class="srow"><span class="app" style="background:#d97757">AI</span><div><b>Brain</b><span>${d.brain.claude?"Claude":"Claude key missing"}${d.brain.backup?" · Groq backup ready":""}</span></div></div>`;
  $("#log").innerHTML=d.activity.length?d.activity.map(a=>`<div class="item"><span style="width:44px;flex:none;font-variant-numeric:tabular-nums">${esc(a.time)}</span><b>${esc(a.text)}</b></div>`).join(""):`<p class="empty">Nothing yet.</p>`;
  const b=d.bkash,tk=x=>x==null?"—":"৳"+Number(x).toLocaleString(undefined,{maximumFractionDigits:2});
  $("#bkIn").textContent=tk(b.in);$("#bkOut").textContent=tk(b.out);$("#bkBal").textContent=tk(b.balance);
  $("#bkList").innerHTML=b.recent.length?b.recent.map(r=>`<div class="item"><span class="app" style="background:#e2136e">৳</span><div><b>${esc(r.label)}${r.party?" · "+esc(r.party):""}</b><span>${esc(r.when)}</span></div><span class="amt ${r.direction}">${r.direction==="in"?"+":"−"}${tk(r.amount)}</span></div>`).join(""):`<p class="empty">No bKash messages yet. Set up SMS forwarding (see README).</p>`;
  const c=d.cost;
  $("#money").innerHTML=`৳${c.total.toLocaleString()} <small>this month</small>`;
  $("#stack").innerHTML=c.items.filter(i=>i.bdt).map(i=>`<i style="width:${Math.min(100,i.bdt/c.budget*100)}%;background:${i.color}"></i>`).join("");
  $("#budget").textContent=c.left>=0?`৳${c.left.toLocaleString()} left of your ৳${c.budget.toLocaleString()} budget`:`৳${(-c.left).toLocaleString()} over your ৳${c.budget.toLocaleString()} budget`;
  $("#legend").innerHTML=c.items.map(i=>`<span><em style="background:${i.color}"></em>${esc(i.label)}</span><span>৳${i.bdt.toLocaleString()}</span>`).join("");
  const on=d.connections.filter(x=>x.enabled).length;
  $("#status").innerHTML=`<i></i>Online · watching ${on} source${on===1?"":"s"}`;
  if(!busy&&!$("#say").dataset.locked){const hi=d.alerts.find(a=>a.level==="high");$("#say").textContent=hi?`Heads up: ${hi.title}`:(d.events[0]?`Next up: ${d.events[0].title} at ${d.events[0].time}.`:"All calm today. Purr.")}
  if(d.language&&d.language!==lang){lang=d.language;setSeg()}
}
async function load(){try{render(await api("/dashboard"))}catch(e){if(e.message!=="login")$("#status").innerHTML=`<i style="background:#ff9500"></i>Can't reach Mr. Bob`}}
async function loadMessages(){try{const ms=await api("/messages");$("#chat").innerHTML="";ms.forEach(m=>bubble(m.role==="user"?"me":"bob",m.text));if(!ms.length)bubble("bob","Assalamu alaikum! Ami Mr. Bob. Ki jante chao?")}catch(e){}}

/* ---------- interactions ---------- */
$("#rems").addEventListener("click",async e=>{const r=e.target.closest(".rem");if(!r)return;await api(`/reminders/${r.dataset.id}`,{method:"PATCH",body:JSON.stringify({done:r.dataset.done!=="true"})});load()});
$("#remForm").addEventListener("submit",async e=>{e.preventDefault();const text=$("#remText").value.trim();if(!text)return;const t=$("#remTime").value;await post("/reminders",{text,due_at:t||null});$("#remText").value="";$("#remTime").value="";toast("Reminder added");load()});
$("#sugs").addEventListener("click",async e=>{const b=e.target.closest("button[data-v]");if(!b)return;await post(`/suggestions/${b.dataset.id}/feedback`,{value:b.dataset.v});b.parentNode.querySelectorAll("button").forEach(x=>x.classList.toggle("chosen",x===b));toast("Thanks, I'll learn from that")});
$("#newTips").addEventListener("click",async()=>{toast("Thinking of tips…");await post("/suggestions/refresh").catch(e=>toast(e.message));load()});
$("#conns").addEventListener("click",async e=>{const b=e.target.closest(".sw");if(!b)return;const on=b.getAttribute("aria-checked")!=="true";b.setAttribute("aria-checked",on);await post(`/connections/${b.dataset.name}`,{enabled:on});load()});
$("#accounts").addEventListener("click",async e=>{if(e.target.id==="gOff"){await post("/google/disconnect");load()}if(e.target.id==="wakeSw"){setWake(!wakeOn);e.target.setAttribute("aria-checked",wakeOn)}});
$("#briefNow").addEventListener("click",async()=>{toast("Sending your briefing to Telegram…");const r=await post("/briefing/morning").catch(e=>({text:""}));if(r.text){bubble("bob",r.text)}toast(r.text?"Briefing sent":"Couldn't make the briefing")});

/* glass shine follows the pointer */
addEventListener("pointermove",e=>{const g=e.target.closest&&e.target.closest(".glass");if(!g)return;const r=g.getBoundingClientRect();g.style.setProperty("--mx",(e.clientX-r.left)+"px");g.style.setProperty("--my",(e.clientY-r.top)+"px")},{passive:true});
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}}),{threshold:.08});
document.querySelectorAll(".fade").forEach(el=>io.observe(el));

/* liquid tab bar + segmented control */
const go=id=>{if(id==="top")scrollTo({top:0,behavior:reduce?"auto":"smooth"});else document.getElementById(id).scrollIntoView({behavior:reduce?"auto":"smooth"})};
const tabs=[...document.querySelectorAll("#tabs button")],drop=$("#drop");
function moveDrop(btn){const r=btn.getBoundingClientRect(),p=$("#tabs").getBoundingClientRect();drop.classList.add("stretch");drop.style.left=(r.left-p.left)+"px";drop.style.width=r.width+"px";clearTimeout(moveDrop.t);moveDrop.t=setTimeout(()=>drop.classList.remove("stretch"),260);tabs.forEach(b=>b.classList.toggle("on",b===btn))}
tabs.forEach(b=>b.addEventListener("click",()=>{moveDrop(b);go(b.dataset.t)}));
const secs=["top","today","chatSec","setSec"];
addEventListener("scroll",()=>{let cur=0;secs.forEach((id,i)=>{if(i&&document.getElementById(id).getBoundingClientRect().top<innerHeight*.45)cur=i});if(!tabs[cur].classList.contains("on"))moveDrop(tabs[cur])},{passive:true});
addEventListener("resize",()=>moveDrop(tabs.find(b=>b.classList.contains("on"))));
const seg=$("#seg"),sdrop=seg.querySelector(".drop");
function setSeg(){seg.querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.l===lang));const b=seg.querySelector("[aria-pressed=true]");if(b){sdrop.style.left=b.offsetLeft+"px";sdrop.style.width=b.offsetWidth+"px"}}
seg.querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{lang=b.dataset.l;try{localStorage.setItem("mrbob-lang",lang)}catch(e){}setSeg()}));
requestAnimationFrame(setSeg);
if(document.fonts)document.fonts.ready.then(()=>{setSeg();moveDrop(tabs.find(b=>b.classList.contains("on")))});
$("#typeBtn").addEventListener("click",()=>{go("chatSec");setTimeout(()=>$("#inp").focus({preventScroll:true}),450)});
if(location.hash==="#settings")setTimeout(()=>go("setSec"),300);

/* ---------- chat ---------- */
const chat=$("#chat");
function bubble(who,text){const d=document.createElement("div");d.className="msg "+who;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
function say(text){const s=$("#say");s.textContent=text.length>110?text.slice(0,107)+"…":text;s.dataset.locked="1";clearTimeout(say.t);say.t=setTimeout(()=>delete s.dataset.locked,60000)}
if(cat)cat.onTap=line=>say(line);
async function sendText(text,{speak=false}={}){
  if(busy||!text.trim())return;busy=true;bubble("me",text);const b=bubble("bob","…");setState("thinking");
  try{const r=await post("/chat",{text,language:lang,speak});b.textContent=r.reply;say(r.reply);$("#vreply").textContent=r.reply;if(cat)cat.hop(0);
    busy=false;if(speak&&r.audio)await play(r.audio);else setState("idle");load()}
  catch(e){b.textContent=e.message==="login"?"Please log in again.":"Sorry, something went wrong: "+e.message;busy=false;setState("idle")}
}
$("#form").addEventListener("submit",e=>{e.preventDefault();const v=$("#inp").value;$("#inp").value="";sendText(v)});
$("#chips").addEventListener("click",e=>{const b=e.target.closest("button");if(b)sendText(b.textContent)});

/* ---------- voice (Siri-style) ---------- */
const voice=$("#voice"),stateText={idle:"Tap and speak",listening:"Listening…",thinking:"Thinking…",speaking:"Mr. Bob is speaking"};
function setState(s){if(cat)cat.state=s;$("#vstate").textContent=stateText[s];voice.classList.remove("listening","thinking","speaking");if(s!=="idle")voice.classList.add(s)}
let rec=null,stream=null,chunks=[],startedAt=0,player=null,vadRaf=0,actx=null;
const canRecord=!!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia&&window.MediaRecorder);
if(!canRecord){voice.classList.add("nomic");$("#vhint").textContent="This browser can't use the microphone here (it needs HTTPS). Type instead."}

function play(b64){return new Promise(res=>{stopAudio();player=new Audio("data:audio/mpeg;base64,"+b64);setState("speaking");player.onended=player.onerror=()=>{setState("idle");res()};player.play().catch(()=>{setState("idle");res()})})}
function stopAudio(){if(player){player.pause();player=null}}

async function listen(){
  if(!canRecord||busy)return;
  if(rec&&rec.state==="recording"){rec.stop();return}
  stopAudio();$("#vsaid").textContent="";$("#vreply").textContent="";
  try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})}
  catch(e){toast("Microphone permission was blocked");voice.classList.add("nomic");return}
  const type=["audio/webm;codecs=opus","audio/webm","audio/mp4","audio/ogg"].find(t=>MediaRecorder.isTypeSupported&&MediaRecorder.isTypeSupported(t))||"";
  rec=new MediaRecorder(stream,type?{mimeType:type}:undefined);chunks=[];startedAt=performance.now();
  rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
  rec.onstop=onRecorded;rec.start(250);setState("listening");$("#vsaid").textContent="…";
  watchSilence(stream);
  setTimeout(()=>{if(rec&&rec.state==="recording")rec.stop()},20000);
}
function watchSilence(s){
  try{actx=new (window.AudioContext||window.webkitAudioContext)();const src=actx.createMediaStreamSource(s),an=actx.createAnalyser();an.fftSize=1024;src.connect(an);
    const buf=new Uint8Array(an.fftSize);let spoke=false,quietSince=0;
    const tick=()=>{if(!rec||rec.state!=="recording")return;an.getByteTimeDomainData(buf);let sum=0;for(const v of buf){const x=(v-128)/128;sum+=x*x}const rms=Math.sqrt(sum/buf.length),t=performance.now();
      if(rms>.04){spoke=true;quietSince=0}else if(spoke){quietSince=quietSince||t;if(t-quietSince>1400){rec.stop();return}}
      vadRaf=requestAnimationFrame(tick)};tick()}catch(e){}
}
async function onRecorded(){
  cancelAnimationFrame(vadRaf);try{actx&&actx.close()}catch(e){}
  stream&&stream.getTracks().forEach(t=>t.stop());
  const seconds=(performance.now()-startedAt)/1000,blob=new Blob(chunks,{type:rec.mimeType||"audio/webm"});rec=null;
  if(blob.size<800){setState("idle");$("#vsaid").textContent="";return}
  busy=true;setState("thinking");
  const fd=new FormData(),ext=(blob.type.includes("mp4")?"m4a":blob.type.includes("ogg")?"ogg":"webm");
  fd.append("audio",blob,"voice."+ext);fd.append("seconds",seconds.toFixed(1));fd.append("language",lang);
  try{const r=await api("/voice",{method:"POST",body:fd});$("#vsaid").textContent=r.heard||"";$("#vreply").textContent=r.reply;
    if(r.heard){bubble("me",r.heard)}bubble("bob",r.reply);say(r.reply);if(cat)cat.hop(0);busy=false;
    if(r.audio)await play(r.audio);else setState("idle");load();
    if(handsFree)setTimeout(()=>{if(!busy&&!(rec&&rec.state==="recording"))closeVoice()},1800)}
  catch(e){busy=false;setState("idle");$("#vreply").textContent=e.message==="login"?"Please log in again.":"Sorry: "+e.message}
}
function openVoice(){stopWake();voice.hidden=false;document.body.style.overflow="hidden";if(cat)cat.mount($("#vstage"));if(canRecord)listen();else setTimeout(()=>$("#vinp").focus(),50)}
function closeVoice(){if(rec&&rec.state==="recording"){rec.onstop=null;rec.stop();stream&&stream.getTracks().forEach(t=>t.stop());rec=null}stopAudio();voice.hidden=true;document.body.style.overflow="";if(cat)cat.mount($("#stage"));if(!busy)setState("idle");handsFree=false;setTimeout(startWake,500)}
$("#talk").addEventListener("click",openVoice);$("#fab").addEventListener("click",openVoice);
$("#vclose").addEventListener("click",closeVoice);$("#vmic").addEventListener("click",listen);
addEventListener("keydown",e=>{if(e.key==="Escape"&&!voice.hidden)closeVoice()});
$("#vform").addEventListener("submit",e=>{e.preventDefault();const v=$("#vinp").value;$("#vinp").value="";if(v.trim()){$("#vsaid").textContent=v;sendText(v,{speak:true})}});

/* ---------- "Hey Bob" hands-free ---------- */
function startWake(){
  if(!SR||!wakeOn||!voice.hidden||busy)return;
  try{wake=new SR();wake.continuous=true;wake.interimResults=true;wake.lang="en-US";
    wake.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0].transcript.toLowerCase();
      if(/\b(hey|hi|hay|ok|okay)[ ,]*(bob|bub|bobby|mr\.? bob)\b|হেই বব|হে বব/.test(t)){wake.onend=null;try{wake.stop()}catch(_){}wake=null;handsFree=true;setTimeout(openVoice,250);return}}};
    wake.onend=()=>{wake=null;setTimeout(startWake,400)};
    wake.onerror=ev=>{if(ev.error==="not-allowed"){setWake(false);toast("Microphone permission was blocked")}};
    wake.start();$("#status").dataset.wake="1"}
  catch(e){}
}
function stopWake(){if(wake){wake.onend=null;try{wake.stop()}catch(e){}wake=null}}
function setWake(on){wakeOn=on;try{localStorage.setItem("mrbob-wake",on?"1":"")}catch(e){}if(on){startWake();toast("Say “Hey Bob” any time")}else stopWake()}

/* installable app */
if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));

/* ---------- start ---------- */
load().then(loadMessages);
if(wakeOn)startWake();
setInterval(()=>{if(!document.hidden&&$("#login").hidden)load()},30000);
})();
