import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import URDFLoader from 'urdf-loader';
const $ = s => document.querySelector(s);
const viewport = $('#viewport');
const scene = new THREE.Scene(); scene.background = new THREE.Color('#101b25');
const camera = new THREE.PerspectiveCamera(38,1,0.001,100); camera.up.set(0,0,1);
const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.outputColorSpace=THREE.SRGBColorSpace; viewport.append(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement); controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xe2f4ff,0x405064,3));
const light = new THREE.DirectionalLight(0xffffff,3);light.position.set(1,-2,3);scene.add(light);
const grid = new THREE.GridHelper(2,40,0x426474,0x243b4a);grid.rotation.x=Math.PI/2;grid.position.z=-0.001;scene.add(grid);
let robot, joints=[], frames=[], playing=false, generation=0, ready=false;
function fit(){if(!robot)return;robot.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(robot);const center=box.getCenter(new THREE.Vector3());const size=box.getSize(new THREE.Vector3()).length();controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(1,-1.4,.85).normalize().multiplyScalar(size * 0.65 / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / Math.min(camera.aspect, 1)));controls.update();}
function update(){for(const {joint,input,output} of joints){const deg=THREE.MathUtils.radToDeg(joint.angle); input.value=deg;output.value=`${deg.toFixed(1)}°`;}}
function stop(){playing=false;$('#demo').textContent='Play motion';}
function display(){if(!robot)return;robot.traverse(o=>{if(o.isMesh){for(const m of (Array.isArray(o.material)?o.material:[o.material]))m.wireframe=$('#wire').checked;}});frames.forEach(f=>f.visible=$('#axes').checked);}
function load(){const version=++generation;ready=false;stop();if(robot)scene.remove(robot);robot=null;joints=[];frames=[];$('#joints').replaceChildren();$('#status').textContent='Loading robot meshes…';const path='/robots/so101/'+$('#model').value;$('#download').href=path;
 const manager=new THREE.LoadingManager();let failed=false;
 manager.onError=url=>{failed=true;$('#status').textContent='Failed to load: '+url;};
 manager.onLoad=()=>{if(version!==generation||failed||!robot)return;ready=true;display();fit();$('#status').textContent='● Ready · 6 joints';};
 const loader=new URDFLoader(manager);
 loader.load(path,r=>{if(version!==generation)return;robot=r;scene.add(r);Object.values(r.joints).forEach(joint=>{if(joint.jointType==='fixed')return;const row=document.createElement('div');row.className='joint';const min=THREE.MathUtils.radToDeg(joint.limit.lower),max=THREE.MathUtils.radToDeg(joint.limit.upper);row.innerHTML=`<div class="joint-title"><span>${joint.name.replaceAll('_',' ')}</span><output>0.0°</output></div><input aria-label="${joint.name}" type="range" min="${min}" max="${max}" step="0.1" value="0"><div class="limits"><span>${min.toFixed(0)}°</span><span>${max.toFixed(0)}°</span></div>`;$('#joints').append(row);const input=row.querySelector('input'),output=row.querySelector('output');input.oninput=()=>{stop();joint.setJointValue(THREE.MathUtils.degToRad(+input.value));update();};joints.push({joint,input,output});});Object.values(r.links).forEach(link=>{const frame=new THREE.AxesHelper(.035);link.add(frame);frames.push(frame);});update();},undefined,error=>{$('#status').textContent='Unable to load robot. '+error;});
}
$('#model').onchange=load;$('#fit').onclick=fit;$('#reset').onclick=()=>{stop();joints.forEach(({joint})=>joint.setJointValue(0));update();};$('#demo').onclick=()=>{playing=!playing;$('#demo').textContent=playing?'Pause motion':'Play motion';};$('#wire').onchange=display;$('#axes').onchange=display;$('#grid').onchange=()=>grid.visible=$('#grid').checked;
new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(viewport);
renderer.setAnimationLoop(t=>{if(playing&&ready){joints.forEach(({joint},i)=>{const lo=joint.limit.lower,hi=joint.limit.upper; joint.setJointValue((lo+hi)/2+Math.sin(t/1800+i*.7)*(hi-lo)*.28);});update();}controls.update();renderer.render(scene,camera);});
load();
