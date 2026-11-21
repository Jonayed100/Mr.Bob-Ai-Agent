/* Mr. Bob website: friend, manager and voice assistant. Talks to the FastAPI backend. */
(function(){
"use strict";
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const cat=window.MrBobCat;
if(/Chrome\//.test(navigator.userAgent))document.documentElement.classList.add("chrome");

let data=null,lang="auto",busy=false,loggedIn=true,wake=null,handsFree=false,wakeOn=false;
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
try{lang=localStorage.getItem("mrbob-lang")||"auto";wakeOn=!!localStorage.getItem("mrbob-wake")&&!!SR}catch(e){}

/* ================= api ================= */
async function api(path,opts={}){
  const isForm=opts.body instanceof FormData;
  const res=await fetch("/api"+path,{credentials:"same-origin",...opts,headers:{...(opts.body&&!isForm?{"Content-Type":"application/json"}:{}),...(opts.headers||{})}});
  if(res.status===401){showLogin();throw new Error("login")}
  const body=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(body.detail||("Error "+res.status));
  return body;
}
const post=(p,b)=>api(p,{method:"POST",body:JSON.stringify(b||{})});
const patch=(p,b)=>api(p,{method:"PATCH",body:JSON.stringify(b||{})});
const del=p=>api(p,{method:"DELETE"});
function toast(t){const el=$("#toast");el.textContent=t;el.hidden=false;clearTimeout(toast.t);toast.t=setTimeout(()=>el.hidden=true,3400)}

/* ================= login ================= */
function showLogin(){loggedIn=false;$("#login").hidden=false;setTimeout(()=>$("#pw").focus(),50)}
$("#loginForm").addEventListener("submit",async e=>{
  e.preventDefault();$("#loginErr").textContent="";
  try{await post("/login",{password:$("#pw").value});$("#login").hidden=true;$("#pw").value="";loggedIn=true;load();route()}
  catch(err){$("#loginErr").textContent=err.message==="login"?"Wrong password":err.message}
});
$("#logout").addEventListener("click",async()=>{await post("/logout").catch(()=>{});location.hash="";location.reload()});

/* ================= pages (hash routing) ================= */
const VIEWS=["home","reminders","reports","memory","chat","settings"];
const tabs=$$("#tabs a"),drop=$("#drop");
function moveDrop(name){const btn=tabs.find(b=>b.dataset.t===name);tabs.forEach(b=>b.classList.toggle("on",b===btn));if(!btn){drop.style.opacity="0";return}
  drop.style.opacity="1";const r=btn.getBoundingClientRect(),p=$("#tabs").getBoundingClientRect();drop.classList.add("stretch");drop.style.left=(r.left-p.left)+"px";drop.style.width=r.width+"px";clearTimeout(moveDrop.t);moveDrop.t=setTimeout(()=>drop.classList.remove("stretch"),260)}
function current(){const h=location.hash.replace("#","");return VIEWS.includes(h)?h:"home"}
function route(){
  const v=current();
  if(!$("#voice").hidden)closeVoice();
  $$(".view").forEach(s=>s.hidden=s.dataset.view!==v);
  moveDrop(v);scrollTo({top:0});
  if(cat&&v==="home")cat.mount($("#stage"));
  if(!loggedIn)return;
  if(v==="reminders")loadReminders();
  if(v==="reports")loadReports();
  if(v==="memory")loadMemories();
  if(v==="chat")loadMessages();
  if(v==="settings"||v==="home")load();
  requestAnimationFrame(()=>{setSeg($("#seg"),lang,"l");setSeg($("#remFilter"),remFilter,"f")});
}
addEventListener("hashchange",route);
addEventListener("resize",()=>moveDrop(current()));

/* glass shine follows the pointer */
addEventListener("pointermove",e=>{const g=e.target.closest&&e.target.closest(".glass");if(!g)return;const r=g.getBoundingClientRect();g.style.setProperty("--mx",(e.clientX-r.left)+"px");g.style.setProperty("--my",(e.clientY-r.top)+"px")},{passive:true});
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}}),{threshold:.05});
$$(".fade").forEach(el=>io.observe(el));

/* liquid segmented controls */
function setSeg(seg,val,key){if(!seg)return;seg.querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",b.dataset[key]===val));const b=seg.querySelector("[aria-pressed=true]"),d=seg.querySelector(".drop");if(b&&d&&b.offsetWidth){d.style.left=b.offsetLeft+"px";d.style.width=b.offsetWidth+"px"}}
$("#seg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;lang=b.dataset.l;try{localStorage.setItem("mrbob-lang",lang)}catch(_){}setSeg($("#seg"),lang,"l")});

/* ================= home + settings ================= */
const ICON={gmail:["#e0142f","M"],calendar:["#ff3b30","C"],weather:["#0a84ff","W"]};
const CONN={gmail:"#e0142f",calendar:"#ff3b30",weather:"#0a84ff",telegram:"#2aabee",whatsapp:"#25d366",bkash:"#e2136e",app:"#1d1d1f"};
const tk=x=>x==null?"—":"৳"+Number(x).toLocaleString(undefined,{maximumFractionDigits:2});
function render(d){
  data=d;
  $("#hello").textContent=`Hi ${d.owner}, I'm Mr. Bob.`;
  const w=d.weather;
  if(w){$("#wxCity").textContent=w.city;$("#temp").textContent=w.temp_c+"°";$("#wx").innerHTML=`${esc(w.condition)}${w.aqi!=null?` · AQI ${w.aqi}, ${esc(w.aqi_label)}`:""}<br>${w.rain_at?`Rain likely around ${esc(w.rain_at)}`:"No rain expected"}`}
  $("#dayName").textContent=d.now.day;$("#dayNum").textContent=d.now.date;
  $("#events").innerHTML=d.events.length?d.events.map(e=>`<div class="ev"><i></i><div><b>${esc(e.title)}</b><span>${esc(e.time)}${e.where?" · "+esc(e.where):""}</span></div></div>`).join(""):`<p class="empty">${d.google.connected?"Nothing on your calendar today.":"Connect Google in Settings to see your calendar."}</p>`;
  const open=d.reminders.filter(r=>!r.done).slice(0,4);
  $("#homeRems").innerHTML=open.length?open.map(r=>`<div class="rem" data-id="${r.id}"><i></i><span>${esc(r.text)}</span><small>${esc(r.when)}</small></div>`).join(""):`<p class="empty">Nothing pending. <a href="#reminders">Add a reminder</a></p>`;
  $("#alerts").innerHTML=d.alerts.length?d.alerts.map(a=>{const[c,l]=ICON[a.source]||["#8e8e93","•"];return`<div class="item"><span class="app" style="background:${a.level==="high"?"#e0142f":c}">${l}</span><div><b>${esc(a.title)}</b><span>${esc(a.sender||a.detail)} · ${esc(a.when)}</span></div>${a.level==="high"?'<span class="tag">Important</span>':""}</div>`}).join(""):`<p class="empty">Nothing important right now. Purr.</p>`;
  $("#sugs").innerHTML=d.suggestions.length?d.suggestions.map(s=>`<div class="card glass"><p>${esc(s.text)}</p><div class="acts"><button class="chip ${s.feedback==="up"?"chosen":""}" data-id="${s.id}" data-v="up">Useful</button><button class="chip ${s.feedback==="down"?"chosen":""}" data-id="${s.id}" data-v="down">Not useful</button></div></div>`).join(""):`<div class="card glass"><p class="empty">No tips yet. Tap Refresh.</p></div>`;
  const b=d.bkash;$("#bkIn").textContent=tk(b.in);$("#bkOut").textContent=tk(b.out);$("#bkBal").textContent=tk(b.balance);
  $("#bkList").innerHTML=b.recent.length?b.recent.slice(0,4).map(r=>`<div class="item"><span class="app" style="background:#e2136e">৳</span><div><b>${esc(r.label)}${r.party?" · "+esc(r.party):""}</b><span>${esc(r.when)}</span></div><span class="amt ${r.direction}">${r.direction==="in"?"+":"−"}${tk(r.amount)}</span></div>`).join(""):`<p class="empty">No bKash messages yet.</p>`;
  const lr=d.latest_report;
  $("#latestReport").innerHTML=lr?`<div style="color:var(--red);font-weight:700;font-size:13px">${esc(lr.created)}</div><b style="font-size:18px">${esc(lr.title)}</b><p class="empty">${esc(lr.summary)}</p><div class="acts"><a class="chip linkbtn" href="#reports">Read</a><span class="tagp red">${lr.important_count} important</span></div>`:`<p class="empty">No reports yet. Tonight Mr. Bob will make your first one, or tap “Tonight's report”.</p>`;
  // settings
  $("#conns").innerHTML=d.connections.map(c=>`<div class="srow"><span class="app" style="background:${CONN[c.name]||"#8e8e93"}">${esc(c.label[0])}</span><div><b>${esc(c.label)}</b><span>${esc(c.detail)}</span></div><button class="sw" role="switch" aria-label="${esc(c.label)}" aria-checked="${c.enabled}" data-name="${c.name}"></button></div>`).join("");
  const perm=("Notification" in window)?Notification.permission:"unsupported";
  $("#accounts").innerHTML=
    `<div class="srow"><span class="app" style="background:#4285f4">G</span><div><b>Gmail &amp; Calendar</b><span>${d.google.connected?"Connected":d.google.ready?"Not connected":"Add Google keys to .env first"}</span></div>${d.google.ready?(d.google.connected?`<button class="chip" id="gOff">Disconnect</button>`:`<a class="chip linkbtn" href="/api/google/connect">Connect</a>`):""}</div>`+
    `<div class="srow"><span class="app" style="background:#25d366">W</span><div><b>WhatsApp</b><span>${[d.whatsapp.alerts&&"Alerts on",d.whatsapp.chat&&"Two-way chat on"].filter(Boolean).join(" · ")||"Add CALLMEBOT_APIKEY to .env"}</span></div></div>`+
    `<div class="srow"><span class="app" style="background:#2aabee">T</span><div><b>Telegram</b><span>${d.telegram.ready?(d.telegram.chat_set?"Linked to your account":"Send /start to your bot and share your number"):"Add TELEGRAM_BOT_TOKEN to .env"}</span></div></div>`+
    `<div class="srow"><span class="app" style="background:#ff9500">N</span><div><b>Browser notifications</b><span>${perm==="granted"?"On for this browser":perm==="denied"?"Blocked in browser settings":"Pop-up reminders even when this tab is in the background"}</span></div>${perm==="default"?`<button class="chip" id="notifOn">Turn on</button>`:""}</div>`+
    `<div class="srow"><span class="app" style="background:#e0142f">B</span><div><b>“Hey Mr. Bob” hands-free</b><span>${SR?"Say “Hey Mr. Bob” while this page is open":"Needs Chrome, Edge or Safari"}</span></div><button class="sw" role="switch" id="wakeSw" aria-label="Hey Mr. Bob hands-free" aria-checked="${wakeOn}"></button></div>`+
    `<div class="srow"><span class="app" style="background:#af52de">V</span><div><b>Voice</b><span>Natural voice · replies in English or বাংলা, like you speak</span></div></div>`+
    `<div class="srow"><span class="app" style="background:#d97757">AI</span><div><b>Brain</b><span>${d.brain.claude?"Claude":"Claude key missing"}${d.brain.backup?" · Groq backup ready":""} · remembers ${d.counts.memories} things</span></div></div>`;
  $("#log").innerHTML=d.activity.length?d.activity.map(a=>`<div class="item"><span style="width:70px;flex:none;font-variant-numeric:tabular-nums">${esc(a.time)}</span><b>${esc(a.text)}</b></div>`).join(""):`<p class="empty">Nothing yet.</p>`;
  const c=d.cost;
  $("#money").innerHTML=`৳${c.total.toLocaleString()} <small>this month</small>`;
  $("#stack").innerHTML=c.items.filter(i=>i.bdt).map(i=>`<i style="width:${Math.min(100,i.bdt/c.budget*100)}%;background:${i.color}"></i>`).join("");
  $("#budget").textContent=c.left>=0?`৳${c.left.toLocaleString()} left of your ৳${c.budget.toLocaleString()} budget`:`৳${(-c.left).toLocaleString()} over your ৳${c.budget.toLocaleString()} budget`;
  $("#legend").innerHTML=c.items.map(i=>`<span><em style="background:${i.color}"></em>${esc(i.label)}</span><span>৳${i.bdt.toLocaleString()}</span>`).join("");
  const on=d.connections.filter(x=>x.enabled).length;
  $("#status").innerHTML=`<i></i>Online · watching ${on} source${on===1?"":"s"} · ${d.counts.reminders_open} reminder${d.counts.reminders_open===1?"":"s"}`;
  const badge=$("#remBadge"),overdue=d.reminders.filter(r=>!r.done&&r.overdue).length;badge.hidden=!overdue;badge.textContent=overdue;
  if(!busy&&!$("#say").dataset.locked){const hi=d.alerts.find(a=>a.level==="high");const nx=open[0];$("#say").textContent=nx&&nx.when?`Next: ${nx.text}, ${nx.when}.`:hi?`Heads up: ${hi.title}`:"All calm today. Purr."}
  if(d.language&&d.language!==lang){lang=d.language;setSeg($("#seg"),lang,"l")}
}
async function load(){try{render(await api("/dashboard"))}catch(e){if(e.message!=="login")$("#status").innerHTML=`<i style="background:#ff9500"></i>Can't reach Mr. Bob`}}
$("#homeRems").addEventListener("click",async e=>{const r=e.target.closest(".rem");if(!r)return;await patch(`/reminders/${r.dataset.id}`,{done:true}).catch(()=>{});toast("Marked done");load()});
$("#sugs").addEventListener("click",async e=>{const b=e.target.closest("button[data-v]");if(!b)return;await post(`/suggestions/${b.dataset.id}/feedback`,{value:b.dataset.v});b.parentNode.querySelectorAll("button").forEach(x=>x.classList.toggle("chosen",x===b));toast("Thanks, I'll learn from that")});
$("#newTips").addEventListener("click",async()=>{toast("Thinking of tips…");await post("/suggestions/refresh").catch(e=>toast(e.message));load()});
$("#conns").addEventListener("click",async e=>{const b=e.target.closest(".sw");if(!b)return;const on=b.getAttribute("aria-checked")!=="true";b.setAttribute("aria-checked",on);await post(`/connections/${b.dataset.name}`,{enabled:on});load()});
$("#accounts").addEventListener("click",async e=>{
  if(e.target.id==="gOff"){await post("/google/disconnect");load()}
  if(e.target.id==="wakeSw"){setWake(!wakeOn);e.target.setAttribute("aria-checked",wakeOn)}
  if(e.target.id==="notifOn"){const p=await Notification.requestPermission();toast(p==="granted"?"Notifications on":"Notifications not allowed");load()}
});
$("#briefNow").addEventListener("click",async()=>{toast("Sending your morning briefing…");const r=await post("/briefing/morning").catch(()=>({text:""}));toast(r.text?"Briefing sent to Telegram / WhatsApp":"Couldn't make the briefing")});

/* ================= reminders ================= */
let reminders=[],remFilter="open",editing=null;
const pad=n=>String(n).padStart(2,"0");
const ymd=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const hm=d=>`${pad(d.getHours())}:${pad(d.getMinutes())}`;
async function loadReminders(){try{reminders=await api("/reminders");renderReminders()}catch(e){}}
function dayDiff(iso){const d=new Date(iso),a=new Date();a.setHours(0,0,0,0);const b=new Date(d);b.setHours(0,0,0,0);return Math.round((b-a)/864e5)}
function remHTML(r){
  const rep={daily:"Every day",weekly:"Every week",monthly:"Every month"}[r.repeat];
  return `<div class="ritem glass ${r.done?"done":""} ${r.priority==="important"?"important":""}" data-id="${r.id}">
   <button class="tick" data-act="done" aria-label="${r.done?"Mark not done":"Mark done"}"></button>
   <div class="rbody"><div class="rtext">${esc(r.text)}</div>
    <div class="rmeta">${r.when?`<span class="tagp ${r.overdue?"over":""}">⏰ ${esc(r.when)}${r.overdue?" · overdue":""}</span>`:`<span class="tagp">No time</span>`}${r.priority==="important"?'<span class="tagp red">⭐ Important</span>':""}${rep?`<span class="tagp">↻ ${rep}</span>`:""}</div>
    ${r.notes?`<div class="rnotes">${esc(r.notes)}</div>`:""}</div>
   <div class="racts"><button class="icon" data-act="edit" aria-label="Edit"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></button><button class="icon" data-act="del" aria-label="Delete"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button></div></div>`;
}
function renderReminders(){
  let list=reminders;
  if(remFilter==="open")list=list.filter(r=>!r.done);
  if(remFilter==="important")list=list.filter(r=>!r.done&&r.priority==="important");
  if(remFilter==="done")list=list.filter(r=>r.done);
  if(!list.length){$("#remList").innerHTML=`<p class="empty big">${remFilter==="done"?"Nothing finished yet.":"No reminders. Add one above, or just tell Mr. Bob: “Remind me to call Ammu tomorrow at 8 PM”."}</p>`;return}
  if(remFilter==="done"){$("#remList").innerHTML=list.map(remHTML).join("");return}
  const groups=[["Overdue",r=>r.overdue,"red"],["Today",r=>!r.overdue&&r.due_at&&dayDiff(r.due_at)===0],["Tomorrow",r=>r.due_at&&dayDiff(r.due_at)===1],["Later",r=>r.due_at&&dayDiff(r.due_at)>1],["No time set",r=>!r.due_at]];
  $("#remList").innerHTML=groups.map(([name,fn,cls])=>{const g=list.filter(fn);return g.length?`<div class="group ${cls||""}">${name} · ${g.length}</div>`+g.map(remHTML).join(""):""}).join("");
}
$("#remFilter").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;remFilter=b.dataset.f;setSeg($("#remFilter"),remFilter,"f");renderReminders()});
$("#quickTimes").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;const q=b.dataset.q,d=new Date();
  if(q==="clear"){$("#rDate").value="";$("#rTime").value="";return}
  if(q==="60")d.setMinutes(d.getMinutes()+60);
  if(q==="tonight"){d.setHours(21,0,0,0)}
  if(q==="tomorrow"){d.setDate(d.getDate()+1);d.setHours(9,0,0,0)}
  $("#rDate").value=ymd(d);$("#rTime").value=hm(d)});
function formDue(){
  let dt=$("#rDate").value;const t=$("#rTime").value;
  if(!dt&&!t)return null;
  if(!dt){const d=new Date();dt=ymd(d);if(t<=hm(d)){d.setDate(d.getDate()+1);dt=ymd(d)}}
  return `${dt}T${t||"09:00"}:00`;
}
function resetForm(){editing=null;$("#remForm").reset();$("#rSave").lastChild.textContent="Add reminder";$("#rCancel").hidden=true}
$("#rCancel").addEventListener("click",resetForm);
$("#remForm").addEventListener("submit",async e=>{
  e.preventDefault();const text=$("#rText").value.trim();if(!text)return;
  const due=formDue(),body={text,notes:$("#rNotes").value.trim(),priority:$("#rImp").checked?"important":"normal",repeat:$("#rRepeat").value};
  try{
    if(editing){await patch(`/reminders/${editing}`,due?{...body,due_at:due}:{...body,clear_time:true});toast("Reminder updated")}
    else{const r=await post("/reminders",{...body,due_at:due});toast(r.when?`Got it. I'll remind you ${r.when}.`:"Saved (no time set)")}
    resetForm();loadReminders();load();
  }catch(err){toast(err.message)}
});
$("#remList").addEventListener("click",async e=>{
  const b=e.target.closest("[data-act]");if(!b)return;const id=+b.closest(".ritem").dataset.id,r=reminders.find(x=>x.id===id);if(!r)return;
  if(b.dataset.act==="done"){await patch(`/reminders/${id}`,{done:!r.done});toast(r.done?"Back on the list":"Done! Nice work.");loadReminders();load()}
  if(b.dataset.act==="del"){if(b.dataset.confirm!=="1"){b.dataset.confirm="1";b.style.color="var(--red)";toast("Tap delete again to remove");setTimeout(()=>{delete b.dataset.confirm;b.style.color=""},3000);return}await del(`/reminders/${id}`);toast("Deleted");loadReminders();load()}
  if(b.dataset.act==="edit"){editing=id;$("#rText").value=r.text;$("#rNotes").value=r.notes||"";$("#rImp").checked=r.priority==="important";$("#rRepeat").value=r.repeat||"none";
    if(r.due_at){const d=new Date(r.due_at);$("#rDate").value=ymd(d);$("#rTime").value=hm(d)}else{$("#rDate").value="";$("#rTime").value=""}
    $("#rSave").lastChild.textContent="Save changes";$("#rCancel").hidden=false;scrollTo({top:0,behavior:reduce?"auto":"smooth"});$("#rText").focus()}
});

/* ================= reports ================= */
let reports=[],openReport=null;
async function loadReports(){try{reports=await api("/reports");renderReports()}catch(e){}}
function renderReports(){
  $("#repList").innerHTML=reports.length?reports.map(r=>`<button class="rcard glass ${openReport&&openReport.id===r.id?"on":""}" data-id="${r.id}"><span class="rdate">${esc(r.created)}</span><b>${esc(r.title)}</b><p>${esc(r.summary)}</p><p style="margin-top:6px"><span class="tagp red">${r.important_count} important</span> <span class="tagp">${r.parts.length} parts</span></p></button>`).join(""):`<p class="empty big">No reports yet. Tap “Get tonight's report now”, or ask Mr. Bob about your important tasks.</p>`;
  if(!openReport&&reports[0]&&innerWidth>820)showReport(reports[0]);
}
function showReport(r){
  openReport=r;$("#repDetail").hidden=false;
  $("#repDetail").innerHTML=`<div style="color:var(--red);font-weight:700;font-size:13px">${esc(r.created)}</div><h2>${esc(r.title)}</h2><p class="empty">${esc(r.summary)}</p>
   <div class="acts" style="margin:10px 0 6px"><button class="pill glass lens small" id="repPlay"><span class="orbi"></span>Listen</button><button class="chip" id="repDel">Delete</button></div>
   ${r.parts.map((p,i)=>`<div class="rpart ${p.important?"important":""}" data-i="${i}"><h4>${p.important?"⭐ ":""}${i+1}. ${esc(p.title)}</h4><p>${esc(p.text)}</p></div>`).join("")}`;
  $$(".rcard").forEach(c=>c.classList.toggle("on",+c.dataset.id===r.id));
  if(innerWidth<=820)$("#repDetail").scrollIntoView({behavior:reduce?"auto":"smooth"});
}
$("#repList").addEventListener("click",e=>{const c=e.target.closest(".rcard");if(!c)return;const r=reports.find(x=>x.id===+c.dataset.id);if(r)showReport(r)});
$("#repDetail").addEventListener("click",async e=>{
  if(e.target.closest("#repDel")&&openReport){await del(`/reports/${openReport.id}`);openReport=null;$("#repDetail").hidden=true;loadReports();return}
  if(e.target.closest("#repPlay")&&openReport){
    const btn=$("#repPlay");if(btn.dataset.playing){delete btn.dataset.playing;stopAudio();btn.lastChild.textContent="Listen";return}
    btn.dataset.playing="1";btn.lastChild.textContent="Stop";
    for(const el of $$(".rpart")){if(!btn.dataset.playing)break;const p=openReport.parts[+el.dataset.i];$$(".rpart").forEach(x=>x.classList.toggle("playing",x===el));el.scrollIntoView({block:"nearest",behavior:reduce?"auto":"smooth"});
      try{const a=await post("/tts",{text:`${p.title}. ${p.text}`,language:openReport.language});if(a.audio&&btn.dataset.playing)await play(a.audio,false)}catch(_){break}}
    $$(".rpart").forEach(x=>x.classList.remove("playing"));delete btn.dataset.playing;if(document.contains(btn))btn.lastChild.textContent="Listen";
  }
});
$("#makeReport").addEventListener("click",()=>openBriefing());
$("#tonightBtn").addEventListener("click",()=>openBriefing());

/* ================= memory ================= */
let memories=[];
const KIND={fact:"Fact",person:"Person",preference:"Likes",goal:"Goal",routine:"Routine"};
async function loadMemories(){try{memories=await api("/memories");renderMemories()}catch(e){}}
function renderMemories(){
  const q=$("#mSearch").value.trim().toLowerCase(),list=memories.filter(m=>!q||m.text.toLowerCase().includes(q));
  $("#memList").innerHTML=list.length?list.map(m=>`<div class="mitem glass" data-id="${m.id}"><span class="kind">${esc(KIND[m.kind]||m.kind)}</span><p>${esc(m.text)}</p><button class="icon" data-act="forget" aria-label="Forget"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button></div>`).join(""):`<p class="empty big">${q?"Nothing matches.":"Nothing yet. Talk to Mr. Bob, or add something above. He'll remember people, dates, plans and what you like."}</p>`;
}
$("#mSearch").addEventListener("input",renderMemories);
$("#memForm").addEventListener("submit",async e=>{e.preventDefault();const text=$("#mText").value.trim();if(!text)return;try{await post("/memories",{text,kind:$("#mKind").value});$("#mText").value="";toast("I'll remember that");loadMemories()}catch(err){toast(err.message)}});
$("#memList").addEventListener("click",async e=>{const b=e.target.closest("[data-act=forget]");if(!b)return;await del(`/memories/${b.closest(".mitem").dataset.id}`);toast("Forgotten");loadMemories()});

/* ================= chat ================= */
const chat=$("#chat");
function bubble(who,text){const d=document.createElement("div");d.className="msg "+who;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
async function loadMessages(){try{const ms=await api("/messages");chat.innerHTML="";ms.forEach(m=>bubble(m.role==="user"?"me":"bob",m.text));if(!ms.length)bubble("bob","Assalamu alaikum! Ami Mr. Bob, your friend and manager. Tell me anything, ask me to remind you, or ask about your important tasks.")}catch(e){}}
function say(text){const s=$("#say");s.textContent=text.length>110?text.slice(0,107)+"…":text;s.dataset.locked="1";clearTimeout(say.t);say.t=setTimeout(()=>delete s.dataset.locked,60000)}
if(cat)cat.onTap=line=>say(line);
async function sendText(text,{speak=false}={}){
  if(busy||!text.trim())return;busy=true;bubble("me",text);const b=bubble("bob","…");setState("thinking");
  try{const r=await post("/chat",{text,language:lang,speak});
    busy=false;
    if(r.mode==="briefing"){b.textContent=r.reply||"Here is your report.";await runBriefing(r);return}
    b.textContent=r.reply;say(r.reply);$("#vreply").textContent=r.reply;if(cat)cat.hop(0);
    if(speak&&r.audio)await play(r.audio);else setState("idle");load();
    if(handsFree)setTimeout(()=>{if(!busy)closeVoice()},1800)}
  catch(e){b.textContent=e.message==="login"?"Please log in again.":"Sorry, something went wrong: "+e.message;busy=false;setState("idle")}
}
$("#form").addEventListener("submit",e=>{e.preventDefault();const v=$("#inp").value;$("#inp").value="";sendText(v)});
$("#chips").addEventListener("click",e=>{const b=e.target.closest("button");if(b)sendText(b.textContent)});

/* ================= audio ================= */
let player=null,playDone=null;
function play(b64,setSpeaking=true){return new Promise(res=>{stopAudio();player=new Audio("data:audio/mpeg;base64,"+b64);playDone=res;if(setSpeaking)setState("speaking");
  const end=()=>{if(playDone===res){playDone=null;if(setSpeaking&&!brief)setState("idle");res()}};player.onended=player.onerror=end;player.play().catch(end)})}
function stopAudio(){if(player){player.pause();player=null}if(playDone){const r=playDone;playDone=null;r()}}

/* ================= voice screen ================= */
const voice=$("#voice"),stateText={idle:"Tap and speak",listening:"Listening…",thinking:"Thinking…",speaking:"Mr. Bob is speaking"};
function setState(s){if(cat)cat.state=s;$("#vstate").textContent=brief&&s==="thinking"?"Preparing your report…":stateText[s];voice.classList.remove("listening","thinking","speaking");if(s!=="idle")voice.classList.add(s)}
let rec=null,stream=null,chunks=[],startedAt=0,vadRaf=0,actx=null;
const canRecord=!!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia&&window.MediaRecorder);
if(!canRecord){voice.classList.add("nomic");$("#vhint").textContent="This browser can't use the microphone here (it needs HTTPS). Type instead."}

async function listen(){
  if(!canRecord||busy||brief)return;
  if(rec&&rec.state==="recording"){rec.stop();return}
  stopAudio();$("#vsaid").textContent="";$("#vreply").textContent="";
  try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}})}
  catch(e){toast("Microphone permission was blocked");voice.classList.add("nomic");return}
  const type=["audio/webm;codecs=opus","audio/webm","audio/mp4","audio/ogg"].find(t=>MediaRecorder.isTypeSupported&&MediaRecorder.isTypeSupported(t))||"";
  rec=new MediaRecorder(stream,type?{mimeType:type}:undefined);chunks=[];startedAt=performance.now();
  rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
  rec.onstop=onRecorded;rec.start(250);setState("listening");$("#vsaid").textContent="…";
  watchSilence(stream);
  setTimeout(()=>{if(rec&&rec.state==="recording")rec.stop()},30000);
}
function watchSilence(s){
  try{actx=new (window.AudioContext||window.webkitAudioContext)();const src=actx.createMediaStreamSource(s),an=actx.createAnalyser();an.fftSize=1024;src.connect(an);
    const buf=new Uint8Array(an.fftSize);let spoke=false,quietSince=0;
    const tick=()=>{if(!rec||rec.state!=="recording")return;an.getByteTimeDomainData(buf);let sum=0;for(const v of buf){const x=(v-128)/128;sum+=x*x}const rms=Math.sqrt(sum/buf.length),t=performance.now();
      if(rms>.035){spoke=true;quietSince=0}else if(spoke){quietSince=quietSince||t;if(t-quietSince>1500){rec.stop();return}}
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
  try{const r=await api("/voice",{method:"POST",body:fd});$("#vsaid").textContent=r.heard||"";busy=false;
    if(r.heard)bubble("me",r.heard);
    if(r.mode==="briefing"){bubble("bob",r.reply||"Here is your report.");await runBriefing(r);return}
    $("#vreply").textContent=r.reply;bubble("bob",r.reply);say(r.reply);if(cat)cat.hop(0);
    if(r.audio)await play(r.audio);else setState("idle");load();
    if(handsFree)setTimeout(()=>{if(!busy&&!(rec&&rec.state==="recording"))closeVoice()},1800)}
  catch(e){busy=false;setState("idle");$("#vreply").textContent=e.message==="login"?"Please log in again.":"Sorry: "+e.message}
}
function showVoice(){stopWake();voice.hidden=false;document.body.style.overflow="hidden";if(cat)cat.mount($("#vstage"))}
function openVoice(){showVoice();endBriefingUI();if(canRecord)listen();else setTimeout(()=>$("#vinp").focus(),50)}
function closeVoice(){if(rec&&rec.state==="recording"){rec.onstop=null;rec.stop();stream&&stream.getTracks().forEach(t=>t.stop());rec=null}
  if(brief)brief.stopped=true;brief=null;stopAudio();endBriefingUI();voice.hidden=true;document.body.style.overflow="";if(cat)cat.mount($("#stage"));if(!busy)setState("idle");handsFree=false;setTimeout(startWake,500)}
$("#talk").addEventListener("click",openVoice);$("#fab").addEventListener("click",openVoice);
$("#vclose").addEventListener("click",closeVoice);$("#vmic").addEventListener("click",listen);
addEventListener("keydown",e=>{if(e.key==="Escape"&&!voice.hidden)closeVoice()});
$("#vform").addEventListener("submit",e=>{e.preventDefault();const v=$("#vinp").value;$("#vinp").value="";if(v.trim()){$("#vsaid").textContent=v;sendText(v,{speak:true})}});

/* ================= night briefing: part by part ================= */
let brief=null;
function endBriefingUI(){voice.classList.remove("briefing");$("#brief").hidden=true;$("#bPause").textContent="Pause"}
async function openBriefing(){
  showVoice();voice.classList.add("briefing");$("#brief").hidden=false;
  brief={parts:[],idx:-1,stopped:false,paused:false};$("#bprog").innerHTML="";$("#bnum").textContent="";$("#btitle").textContent="One moment…";$("#btext").textContent="I'm going through your day: reminders, emails, calendar and money.";$("#bpart").classList.remove("important");
  busy=true;setState("thinking");
  try{const r=await post("/briefing/tonight",{language:lang});busy=false;if(brief&&!brief.stopped)await runBriefing(r)}
  catch(e){busy=false;$("#btitle").textContent="Sorry";$("#btext").textContent=e.message==="login"?"Please log in again.":e.message;setState("idle")}
}
async function runBriefing(r){
  const rep=r.report;if(!rep)return;
  if(voice.hidden)showVoice();
  voice.classList.add("briefing");$("#brief").hidden=false;
  const b={parts:rep.parts,idx:-1,stopped:false,paused:false,report:rep};brief=b;
  $("#bprog").innerHTML=rep.parts.map(p=>`<i class="${p.important?"bimp":""}"></i>`).join("");
  $("#bnum").textContent=rep.created||"Tonight";$("#btitle").textContent=rep.title;$("#btext").textContent=rep.summary;$("#bpart").classList.remove("important");
  if(r.audio)await play(r.audio);else await wait(1500);
  while(brief===b&&!b.stopped&&b.idx<b.parts.length-1){
    b.idx++;showPart(b);const p=b.parts[b.idx];
    if(p.audio)await play(p.audio);else await wait(Math.min(9000,1200+p.text.length*45));
    while(brief===b&&b.paused&&!b.stopped)await wait(200);
  }
  if(brief===b&&!b.stopped){setState("idle");toast("Saved to Reports");$("#bnum").textContent="Finished · saved to Reports";load()}
}
function showPart(b){const p=b.parts[b.idx];
  $$("#bprog i").forEach((el,i)=>{el.classList.toggle("on",i===b.idx);el.classList.toggle("past",i<b.idx)});
  $("#bnum").textContent=`Part ${b.idx+1} of ${b.parts.length}${p.important?" · Important":""}`;$("#btitle").textContent=p.title;$("#btext").textContent=p.text;
  $("#bpart").classList.toggle("important",!!p.important);if(cat)cat.hop(p.important?1:0)}
$("#bNext").addEventListener("click",()=>{if(!brief)return;brief.paused=false;$("#bPause").textContent="Pause";stopAudio()});
$("#bPause").addEventListener("click",()=>{if(!brief)return;brief.paused=!brief.paused;$("#bPause").textContent=brief.paused?"Resume":"Pause";
  if(player){brief.paused?player.pause():player.play().catch(()=>{})}setState(brief.paused?"idle":"speaking")});

/* ================= reminder alerts (website) ================= */
const shown=new Set();let dueQueue=[],dueOpen=null;
async function checkDue(){if(!loggedIn)return;
  try{const list=await api("/due");for(const r of list){const key=r.id+"@"+r.due_at;if(shown.has(key))continue;shown.add(key);dueQueue.push(r);
    if("Notification" in window&&Notification.permission==="granted"&&document.hidden){try{new Notification("⏰ "+r.text,{body:r.notes||"Reminder from Mr. Bob",icon:"/assets/icon-192.png",tag:"bob-"+r.id})}catch(_){}}}
    if(!dueOpen)nextDue()}catch(e){}}
async function nextDue(){
  dueOpen=dueQueue.shift()||null;if(!dueOpen){$("#due").hidden=true;return}
  const r=dueOpen;$("#dueText").textContent=r.text;$("#dueNotes").textContent=r.notes||"";$("#dueWhen").textContent=(r.priority==="important"?"⭐ Important · ":"")+(r.when||"now");$("#due").hidden=false;
  if(cat)cat.hop(2);
  try{const a=await post("/tts",{text:`Reminder. ${r.text}. ${r.notes||""}`,language:"auto"});if(a.audio&&dueOpen===r)await play(a.audio,false)}catch(_){}
}
async function dueAction(kind){const r=dueOpen;if(!r)return;dueOpen=null;stopAudio();
  try{if(kind==="done")await patch(`/reminders/${r.id}`,{done:true});else if(kind==="snooze")await post(`/reminders/${r.id}/snooze`,{minutes:10});else await post(`/reminders/${r.id}/seen`);}catch(_){}
  toast(kind==="done"?"Done! Nice work.":kind==="snooze"?"I'll remind you again in 10 minutes":"Dismissed");nextDue();load();if(current()==="reminders")loadReminders()}
$("#dueDone").addEventListener("click",()=>dueAction("done"));$("#dueSnooze").addEventListener("click",()=>dueAction("snooze"));$("#dueLater").addEventListener("click",()=>dueAction("seen"));

/* ================= "Hey Mr. Bob" hands-free ================= */
function startWake(){
  if(!SR||!wakeOn||!voice.hidden||busy)return;
  try{wake=new SR();wake.continuous=true;wake.interimResults=true;wake.lang="en-US";
    wake.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0].transcript.toLowerCase();
      if(/\b(hey|hi|hay|ok|okay)[ ,]*(mr\.?|mister)?[ ,]*(bob|bub|bobby)\b|হেই ?বব|হে ?বব/.test(t)){wake.onend=null;try{wake.stop()}catch(_){}wake=null;handsFree=true;
        if(/important|task|report|brief/.test(t))setTimeout(openBriefing,250);else setTimeout(openVoice,250);return}}};
    wake.onend=()=>{wake=null;setTimeout(startWake,400)};
    wake.onerror=ev=>{if(ev.error==="not-allowed"){setWake(false);toast("Microphone permission was blocked")}};
    wake.start()}
  catch(e){}
}
function stopWake(){if(wake){wake.onend=null;try{wake.stop()}catch(e){}wake=null}}
function setWake(on){wakeOn=on;try{localStorage.setItem("mrbob-wake",on?"1":"")}catch(e){}if(on){startWake();toast("Say “Hey Mr. Bob” any time")}else stopWake()}

/* installable app */
if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));

/* ================= start ================= */
route();
if(document.fonts)document.fonts.ready.then(()=>{moveDrop(current());setSeg($("#seg"),lang,"l")});
load();
if(wakeOn)startWake();
setInterval(()=>{if(!document.hidden&&loggedIn&&$("#login").hidden&&["home","settings"].includes(current()))load()},45000);
setInterval(checkDue,20000);setTimeout(checkDue,3000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkDue()});
})();
