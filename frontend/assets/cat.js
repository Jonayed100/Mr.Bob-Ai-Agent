/* Mr. Bob, the 3D cat. Exposes window.MrBobCat = {state, hop(n), mount(el), onTap}. */
(function(){
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
const api={state:"idle",hop(){},mount(){},onTap:null,fallback:false};
window.MrBobCat=api;
const stage=document.getElementById("stage"),vstage=document.getElementById("vstage");
let renderer=null,mx=0,my=0,jumpT=-1;
if(window.THREE){
 const T=THREE;
 renderer=new T.WebGLRenderer({antialias:true,alpha:true});
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
 renderer.outputEncoding=T.sRGBEncoding;
 stage.appendChild(renderer.domElement);
 const scene=new T.Scene();
 const cam=new T.PerspectiveCamera(30,1,.1,100);
 scene.add(new T.HemisphereLight(0xffffff,0xd9c6cc,.75));
 const key=new T.DirectionalLight(0xffffff,.55);key.position.set(2,4,5);scene.add(key);
 const fill=new T.DirectionalLight(0xffe6ea,.25);fill.position.set(-3,1,2);scene.add(fill);
 const M=(c,o)=>new T.MeshStandardMaterial(Object.assign({color:c,roughness:.92,metalness:0},o||{}));
 const furW=M(0xfffaf6),peach=M(0xc78d55),tabby=M(0xc08a52),stripe=M(0x8d5c30),green=M(0x86b84a,{emissive:0x1e3308,roughness:.25}),pink=M(0xffb3c1),eyeM=M(0x1b1416,{roughness:.22}),glow=M(0xffffff,{emissive:0xffffff}),red=M(0xe0142f,{roughness:.55}),lip=M(0x6a4a50);
 const S=(r,m,x,y,z,sx,sy,sz,p)=>{const o=new T.Mesh(new T.SphereGeometry(r,48,36),m);o.position.set(x,y,z);o.scale.set(sx||1,sy||1,sz||1);p.add(o);return o};
 const cat=new T.Group();scene.add(cat);
 const bodyG=new T.Group();cat.add(bodyG);
 S(.62,furW,0,-1.02,0,1.05,.95,.95,bodyG);
 S(.36,tabby,.22,-.74,-.3,1.15,.7,.95,bodyG);S(.33,tabby,-.3,-1.12,-.38,1.1,.85,.9,bodyG);S(.31,tabby,.48,-1.39,.03,1.02,.77,1.22,bodyG);
 [-1,1].forEach(s=>{S(.3,furW,s*.48,-1.4,.05,1,.75,1.2,bodyG);S(.2,furW,s*.24,-1.52,.42,1,.62,1.15,bodyG);S(.05,pink,s*.24,-1.58,.62,1.2,.5,.5,bodyG)});
 const head=new T.Group();head.position.set(0,.1,0);cat.add(head);
 S(1,furW,0,0,0,1.18,.95,1,head);
 [-1,1].forEach(s=>S(.42,furW,s*.42,-.32,.5,1.05,.85,.8,head));
 S(1,tabby,0,.17,-.06,1.2,.86,.98,head);[-.2,0,.2].forEach((x,i)=>{const st=S(.05,stripe,x,.6-(i===1?.02:0),.79,1,2.6,.45,head);st.rotation.z=-x*.9});[-1,1].forEach(s=>[.18,.32].forEach(y=>{const st=S(.045,stripe,s*.98,y,.5,.6,1,2.4,head);st.rotation.y=s*.9}));
 const ear=s=>{const g=new T.Group();g.position.set(s*.68,.62,-.05);g.rotation.z=-s*.5;head.add(g);const o=new T.Mesh(new T.ConeGeometry(.34,.52,40),tabby);o.position.y=.24;o.scale.z=.72;g.add(o);const tip=new T.Mesh(new T.SphereGeometry(.06,16,12),tabby);tip.position.y=.49;g.add(tip);const i=new T.Mesh(new T.ConeGeometry(.2,.34,32),pink);i.position.set(0,.2,.1);i.scale.z=.45;g.add(i);return g};
 const earL=ear(-1),earR=ear(1);
 const eyes=[-1,1].map(s=>{const g=new T.Group();g.position.set(s*.4,-.06,.9);head.add(g);S(.21,eyeM,0,0,0,1,1.3,.5,g);S(.165,green,0,-.03,.05,1,1.25,.42,g);S(.095,eyeM,0,-.01,.09,.78,1.45,.4,g);S(.07,glow,.07,.1,.115,1,1,1,g);S(.033,glow,-.06,-.1,.12,1,1,1,g);return g});
 const blushM=new T.MeshBasicMaterial({color:0xff8fa6,transparent:true,opacity:.5,depthWrite:false});
 [-1,1].forEach(s=>{const b=new T.Mesh(new T.CircleGeometry(.11,32),blushM);b.position.set(s*.62,-.28,.8);b.rotation.y=s*.7;b.scale.y=.62;head.add(b)});
 S(.05,pink,0,-.26,.985,1.45,1,.8,head);
 [-1,1].forEach(s=>{const a=new T.Mesh(new T.TorusGeometry(.05,.012,8,20,Math.PI),lip);a.rotation.z=Math.PI;a.position.set(s*.05,-.33,.985);head.add(a)});
 const mouth=S(.07,M(0xe8768c),0,-.4,.96,1,.01,.4,head);
 const bow=new T.Group();bow.position.set(0,-.8,.6);bow.rotation.x=-.3;bow.scale.setScalar(.8);cat.add(bow);
 [-1,1].forEach(s=>{const c=new T.Mesh(new T.ConeGeometry(.17,.32,32),red);c.rotation.z=s*Math.PI/2;c.position.x=s*.16;c.scale.z=.55;bow.add(c)});
 S(.07,red,0,0,.02,1,1,.8,bow);
 const tail=[];for(let i=0;i<13;i++)tail.push(S(.13-i*.004,i%3===2?stripe:tabby,0,0,0,1,1,1,cat));
 const sc=document.createElement("canvas");sc.width=sc.height=128;const sx=sc.getContext("2d");const gr=sx.createRadialGradient(64,64,0,64,64,64);gr.addColorStop(0,"rgba(60,20,30,.32)");gr.addColorStop(1,"rgba(60,20,30,0)");sx.fillStyle=gr;sx.fillRect(0,0,128,128);
 const shadow=new T.Mesh(new T.PlaneGeometry(2.8,1.3),new T.MeshBasicMaterial({map:new T.CanvasTexture(sc),transparent:true,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=-1.72;scene.add(shadow);
 const hs=new T.Shape();hs.moveTo(0,.25);hs.bezierCurveTo(0,.3,-.05,.4,-.2,.4);hs.bezierCurveTo(-.45,.4,-.45,.12,-.45,.12);hs.bezierCurveTo(-.45,-.05,-.27,-.22,0,-.4);hs.bezierCurveTo(.27,-.22,.45,-.05,.45,.12);hs.bezierCurveTo(.45,.12,.45,.4,.2,.4);hs.bezierCurveTo(.05,.4,0,.3,0,.25);
 const hg=new T.ExtrudeGeometry(hs,{depth:.1,bevelEnabled:true,bevelSize:.04,bevelThickness:.04,bevelSegments:3});hg.center();hg.rotateZ(Math.PI);
 const hearts=[];
 api.hop=(n)=>{jumpT=0;for(let i=0;i<(n||0);i++){const h=new T.Mesh(hg,new T.MeshStandardMaterial({color:0xff4d6d,transparent:true,roughness:.5}));h.position.set((Math.random()-.5)*1.2,.9,.5);h.scale.setScalar(.18+Math.random()*.1);h.userData={vy:1+Math.random()*.6,vx:(Math.random()-.5)*.6,life:0};scene.add(h);hearts.push(h)}};
 const ray=new T.Raycaster(),pv=new T.Vector2();
 renderer.domElement.addEventListener("pointerdown",e=>{const r=renderer.domElement.getBoundingClientRect();pv.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pv,cam);if(ray.intersectObject(cat,true).length){api.hop(3);const lines=["Meow! Ami Mr. Bob.","Hehe, sursuri lage!","Ki khobor, Jonayed?","Purr… always here for you."];if(api.onTap)api.onTap(lines[Math.floor(Math.random()*lines.length)])}});
 const fit=()=>{const p=renderer.domElement.parentNode;if(!p)return;const w=p.clientWidth,h=p.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);cam.aspect=w/h;cam.position.set(0,.05,Math.max(7.2,5.4/cam.aspect));cam.lookAt(0,-.35,0);cam.updateProjectionMatrix()};
 const ro=new ResizeObserver(fit);ro.observe(stage);ro.observe(vstage);
 addEventListener("pointermove",e=>{mx=e.clientX/innerWidth*2-1;my=e.clientY/innerHeight*2-1});
 let nextBlink=2,blinkT=-1,nextTwitch=3,twitchT=-1;const clock=new T.Clock();
 const loop=()=>{
  const dt=Math.min(clock.getDelta(),.05),t=clock.elapsedTime,k=reduce?.3:1;
  let jy=0,sq=1;if(jumpT>=0){jumpT+=dt;const p=jumpT/.6;if(p>=1)jumpT=-1;else{jy=Math.sin(p*Math.PI)*.45;sq=p<.15?1-p:p>.85?1-(1-p):1.05}}
  const br=1+Math.sin(t*2.2)*.012*k;
  cat.position.y=Math.sin(t*1.5)*.035*k+jy;bodyG.scale.set(1/Math.sqrt(sq),sq*br,1/Math.sqrt(sq));
  shadow.scale.setScalar(1-jy*.5);shadow.material.opacity=1-jy;
  const ty=api.state==="thinking"?Math.sin(t*1.2)*.3:mx*.4,tx=api.state==="thinking"?-.15:my*.2;
  head.rotation.y+=(ty-head.rotation.y)*.07;head.rotation.x+=(tx-head.rotation.x)*.07;
  const tz=api.state==="listening"?-.18:api.state==="thinking"?.15:Math.sin(t*.6)*.07*k;head.rotation.z+=(tz-head.rotation.z)*.06;
  if(t>nextBlink){blinkT=0;nextBlink=t+2.2+Math.random()*3}
  let ey=1;if(blinkT>=0){blinkT+=dt;ey=blinkT<.07?1-blinkT/.07*.92:blinkT<.15?.08+(blinkT-.07)/.08*.92:1;if(blinkT>.15)blinkT=-1}
  if(jumpT>=0)ey=.15;
  eyes.forEach(g=>g.scale.y=ey);
  if(t>nextTwitch){twitchT=0;nextTwitch=t+3+Math.random()*4}
  let tw=0;if(twitchT>=0){twitchT+=dt;tw=Math.sin(twitchT*30)*.14;if(twitchT>.3)twitchT=-1}
  const perk=api.state==="listening"?.25:0;
  earL.rotation.x+=(-perk-earL.rotation.x)*.1;earR.rotation.x+=(-perk-earR.rotation.x)*.1;earL.rotation.z=.5+tw;earR.rotation.z=-.5;
  const mo=api.state==="speaking"?.15+Math.abs(Math.sin(t*13))*.85:jumpT>=0?.8:.01;mouth.scale.y+=(mo-mouth.scale.y)*.35;
  let x=.45,y=-1.35,z=-.45;tail.forEach((s,i)=>{const a=Math.sin(t*2.2*k-i*.4)*.5*(i/12)+.35-(i>8?(i-8)*.3:0);x+=Math.sin(a)*.11;y+=Math.cos(a)*.11;z-=.03;s.position.set(x,y,z)});
  for(let i=hearts.length-1;i>=0;i--){const h=hearts[i],u=h.userData;u.life+=dt;h.position.y+=u.vy*dt;h.position.x+=u.vx*dt;h.material.opacity=Math.max(0,1-u.life/1.4);if(u.life>1.4){scene.remove(h);h.material.dispose();hearts.splice(i,1)}}
  renderer.render(scene,cam);requestAnimationFrame(loop)};
 api.mount=el=>{el.appendChild(renderer.domElement);fit()};
 fit();loop();
}else{stage.insertAdjacentHTML("beforeend",'<div class="fallback"></div>');api.fallback=true}

})();
