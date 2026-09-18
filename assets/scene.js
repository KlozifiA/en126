import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

/* body[data-scene="lite"] — облегчённый город для внутренних страниц */
const LITE=document.body.dataset.scene==='lite';

const canvas=document.getElementById('scene');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(LITE?1:Math.min(devicePixelRatio,1.75));
renderer.setSize(innerWidth,innerHeight);
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.1;

const scene=new THREE.Scene();
scene.background=new THREE.Color(0x05070d);
scene.fog=new THREE.FogExp2(0x070b18,0.018);

const camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,.1,400);

scene.add(new THREE.HemisphereLight(0x3a5aa8,0x0a0612,.55));
const moon=new THREE.DirectionalLight(0x8fb4ff,.6); moon.position.set(-30,50,-20); scene.add(moon);

/* seeded rng */
let seed=126; const rnd=()=>((seed=(seed*16807)%2147483647)/2147483647);

/* window texture */
function windowTex(){
  const c=document.createElement('canvas'); c.width=64; c.height=128;
  const x=c.getContext('2d'); x.fillStyle='#000'; x.fillRect(0,0,64,128);
  for(let r=0;r<16;r++) for(let k=0;k<4;k++){
    const p=rnd(); if(p<.55) continue;
    x.fillStyle=p>.93?'#3de0ff':p>.75?'#ffcf7a':'#ff9a3a';
    x.globalAlpha=.35+rnd()*.65; x.fillRect(4+k*15,3+r*8,9,4);
  }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.magFilter=THREE.NearestFilter; return t;
}
const texs=Array.from({length:6},windowTex);

/* city blocks */
const city=new THREE.Group(); scene.add(city);
const box=new THREE.BoxGeometry(1,1,1); box.translate(0,.5,0);
const roofMat=new THREE.MeshStandardMaterial({color:0x0b1020,roughness:.9});
for(let gx=-14;gx<=14;gx++) for(let gz=-14;gz<=6;gz++){
  if(gx%4===0||gz%4===0) continue;           // streets
  if(Math.abs(gx)<2&&gz>-2) continue;          // plaza in front of camera
  if(rnd()<(LITE?.45:.18)) continue;
  const d=Math.hypot(gx,gz+4);
  const h=.6+Math.pow(rnd(),2.2)*(10-d*.35)+rnd()*1.5;
  const w=.7+rnd()*.25, dd=.7+rnd()*.25;
  const t=texs[Math.floor(rnd()*texs.length)].clone(); t.needsUpdate=true;
  t.wrapS=t.wrapT=THREE.RepeatWrapping; t.repeat.set(Math.max(1,Math.round(w*2))/2,Math.max(.25,h/8));
  const side=new THREE.MeshStandardMaterial({color:0x0d1428,roughness:.6,metalness:.2,emissive:0xffffff,emissiveMap:t,emissiveIntensity:1.05});
  const m=new THREE.Mesh(box,[side,side,roofMat,roofMat,side,side]);
  m.scale.set(w*1.6,Math.max(.4,h),dd*1.6); m.position.set(gx*1.6,0,gz*1.6);
  city.add(m);
  if(!LITE&&h>6&&rnd()>.5){ // antenna blink
    const b=new THREE.Mesh(new THREE.SphereGeometry(.07,8,8),new THREE.MeshBasicMaterial({color:0xff3355}));
    b.position.set(gx*1.6,h+.3,gz*1.6); b.userData.blink=rnd()*6; city.add(b);
  }
}

/* ground + grid */
const ground=new THREE.Mesh(new THREE.PlaneGeometry(300,300),new THREE.MeshStandardMaterial({color:0x04060c,roughness:.35,metalness:.6}));
ground.rotation.x=-Math.PI/2; scene.add(ground);
const grid=new THREE.GridHelper(120,75,0x1c3a66,0x0f1d38); grid.position.y=.01; grid.material.transparent=true; grid.material.opacity=.45; scene.add(grid);

/* mountains — Beshtau / Mashuk wireframe silhouette */
function mountains(){
  const g=new THREE.PlaneGeometry(260,70,120,30);
  const p=g.attributes.position;
  for(let i=0;i<p.count;i++){
    const x=p.getX(i),y=p.getY(i);
    const peak=(cx,w,h)=>h*Math.exp(-((x-cx)**2)/(2*w*w));
    let z=peak(-40,14,26)+peak(-18,9,18)+peak(22,16,20)+peak(60,20,14)+peak(-80,18,12)+peak(95,14,16);
    z+=Math.sin(x*.3)*1.2+Math.sin(x*.11+1)*2+Math.cos(x*.7)*.5;
    z*= (y+35)/70;
    p.setZ(i,Math.max(0,z));
  }
  g.computeVertexNormals();
  const grp=new THREE.Group();
  const solid=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:0x060a16,roughness:1}));
  const wire=new THREE.Mesh(g,new THREE.MeshBasicMaterial({color:0x2a5fb0,wireframe:true,transparent:true,opacity:.18}));
  grp.add(solid,wire); grp.rotation.x=-Math.PI/2; grp.position.set(0,-.2,-95);
  return grp;
}
scene.add(mountains());

/* moon disc */
const moonDisc=new THREE.Mesh(new THREE.CircleGeometry(6,48),new THREE.MeshBasicMaterial({color:0xffe2b0,fog:false}));
moonDisc.position.set(48,40,-150); scene.add(moonDisc);
const halo=new THREE.Mesh(new THREE.CircleGeometry(16,48),new THREE.MeshBasicMaterial({color:0xffb23f,transparent:true,opacity:.08,fog:false}));
halo.position.copy(moonDisc.position).add(new THREE.Vector3(0,0,-.1)); scene.add(halo);

/* game route through streets — the "Точки" path */
const pts=[[-19.2,6],[-19.2,-6.4],[-6.4,-6.4],[-6.4,-19.2],[6.4,-19.2],[6.4,-6.4],[12.8,-6.4],[12.8,6.4],[19.2,6.4]].map(([x,z])=>new THREE.Vector3(x,.12,z));
const curve=new THREE.CatmullRomCurve3(pts,false,'catmullrom',.02);
const tubeG=new THREE.TubeGeometry(curve,400,.09,8,false);
const routeMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{t:{value:0}},
  vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader:`uniform float t;varying vec2 vUv;void main(){float d=fract(vUv.x*14.-t);float a=smoothstep(0.,.1,d)*smoothstep(.6,.3,d);
    gl_FragColor=vec4(mix(vec3(1.,.55,.1),vec3(1.,.8,.4),a),.25+a*.9);}`});
scene.add(new THREE.Mesh(tubeG,routeMat));
/* checkpoints */
const cps=[];
pts.forEach((p,i)=>{ if(i===0) return;
  const g=new THREE.Group(); g.position.copy(p);
  const ring=new THREE.Mesh(new THREE.RingGeometry(.45,.6,40),new THREE.MeshBasicMaterial({color:0x3de0ff,side:THREE.DoubleSide,transparent:true,opacity:.9}));
  ring.rotation.x=-Math.PI/2; g.add(ring);
  const beam=new THREE.Mesh(new THREE.CylinderGeometry(.05,.3,18,12,1,true),new THREE.MeshBasicMaterial({color:0x3de0ff,transparent:true,opacity:.12,side:THREE.DoubleSide,depthWrite:false}));
  beam.position.y=9; g.add(beam);
  scene.add(g); cps.push({g,ring,beam,o:i});
});
/* car = moving light */
const car=new THREE.Group();
car.add(new THREE.Mesh(new THREE.SphereGeometry(.22,16,16),new THREE.MeshBasicMaterial({color:0xfff1c8})));
const carLight=new THREE.PointLight(0xffa640,18,9,1.6); car.add(carLight); scene.add(car);

/* fireflies / data dust */
const N=LITE?300:900, pos=new Float32Array(N*3);
for(let i=0;i<N;i++){pos[i*3]=(rnd()-.5)*90;pos[i*3+1]=rnd()*22;pos[i*3+2]=(rnd()-.5)*70-8;}
const dustG=new THREE.BufferGeometry(); dustG.setAttribute('position',new THREE.BufferAttribute(pos,3));
const dust=new THREE.Points(dustG,new THREE.PointsMaterial({color:0xffc27a,size:.09,transparent:true,opacity:.7,depthWrite:false,blending:THREE.AdditiveBlending}));
scene.add(dust);

/* camera rig */
let mx=0,my=0,sy=0;
addEventListener('pointermove',e=>{mx=e.clientX/innerWidth-.5;my=e.clientY/innerHeight-.5});
addEventListener('scroll',()=>{sy=scrollY/Math.max(1,document.body.scrollHeight-innerHeight)},{passive:true});
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});

const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const clock=new THREE.Clock(); let cx=0,cy=0,cs=0;
function frame(){
  const t=clock.getElapsedTime();
  cx+=(mx-cx)*.04; cy+=(my-cy)*.04; cs+=(sy-cs)*.06;
  const ang=(reduce?0:t*(LITE?.02:.035))+cx*(LITE?.25:.6) + cs*(LITE?.5:1.6);
  const rad=LITE?40:34-cs*14, h=LITE?22-cy*3:14+cs*16-cy*5;
  camera.position.set(Math.sin(ang)*rad,h,Math.cos(ang)*rad);
  camera.lookAt(0,2+cs*-1,-6);

  routeMat.uniforms.t.value=t*.8;
  const u=(t*.035)%1; car.position.copy(curve.getPointAt(u)); car.position.y=.3;
  cps.forEach(c=>{const p=1+.25*Math.sin(t*3+c.o); c.ring.scale.setScalar(p); c.beam.material.opacity=.08+.07*Math.sin(t*2+c.o)});
  city.children.forEach(o=>{ if(o.userData.blink!==undefined) o.visible=Math.sin(t*2.5+o.userData.blink)>.3; });
  dust.rotation.y=t*.01; dust.position.y=Math.sin(t*.4)*.4;
  renderer.render(scene,camera);
  requestAnimationFrame(frame);
}
frame();
