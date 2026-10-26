import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import URDFLoader from 'urdf-loader';
import { JOINTS, HOME, samplePlan } from './motion.js';

export function createViewer(viewport, onStatus) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#111c27');
  scene.fog = new THREE.Fog('#111c27', 2.3, 5);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.001, 20);
  camera.up.set(0, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  viewport.append(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minDistance = 0.18;
  controls.maxDistance = 3;
  scene.add(new THREE.HemisphereLight(0xe1f5ff, 0x375061, 2.5));
  const key = new THREE.DirectionalLight(0xffffff, 3.2);
  key.position.set(1, -2, 3);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x7bdcca, 1.5);
  rim.position.set(-1, 1, 1);
  scene.add(rim);
  const grid = new THREE.GridHelper(3, 60, 0x3e5b69, 0x233745);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.003;
  scene.add(grid);
  const axes = new THREE.AxesHelper(0.065);
  axes.position.set(-0.2, -0.2, 0);
  scene.add(axes);
  const pathRoot = new THREE.Group();
  scene.add(pathRoot);
  let robot, ghost, livePose = HOME, ghostPose = null, queuedPlan = null, failed = false;
  const manager = new THREE.LoadingManager();
  manager.onError = url => { failed = true; onStatus(`Model unavailable: ${url}`); };
  manager.onLoad = () => {
    if (!robot || failed) return;
    ghost = robot.clone(true);
    // URDFJoint.copy resets ignoreLimits; the preview must use the same
    // calibrated joint values as the live arm and server-planned trajectory.
    for (const joint of Object.values(ghost.joints)) joint.ignoreLimits = true;
    ghost.traverse(object => {
      if (object.isMesh) {
        object.material = new THREE.MeshStandardMaterial({ color: 0x70e7cc, transparent: true, opacity: 0.34, depthWrite: false, metalness: 0.05, roughness: 0.6 });
        object.renderOrder = 1;
      }
    });
    scene.add(ghost);
    setLive(livePose);
    showGhost(ghostPose);
    setPlan(queuedPlan);
    fit();
    onStatus('SO-101 · fitted v3 wrist mount · 6 joints', true);
  };
  new URDFLoader(manager).load('/robots/so101/so101_new_calib.urdf', loaded => {
    robot = loaded;
    // Hardware calibration can legitimately extend beyond nominal model limits.
    // Sliders/planner/driver enforce their own limits; display actual feedback.
    for (const joint of Object.values(robot.joints)) joint.ignoreLimits = true;
    // Studio-only appearance: retain the physical gripper joints and TCP for
    // feedback/planning, but replace the stock motor, bracket and jaw visuals.
    for (const name of ['gripper_link', 'moving_jaw_so101_v1_link']) {
      for (const child of robot.links[name].children) {
        if (child.isURDFVisual) child.visible = false;
      }
    }
    // Share the loading manager so the preview is cloned only after the fitted
    // mesh is attached. The design STL is in mm; the robot is in metres.
    new STLLoader(manager).load('/robots/so101/assets/male_v3_SO101_fitted.stl', geometry => {
      const mount = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0x5686b3, metalness: 0.05, roughness: 0.6 }));
      mount.name = 'male_v3_SO101_fitted';
      mount.scale.setScalar(0.001);
      // Use the stock wrist flange origin. STL +Z points away from its rear
      // horn recess, along gripper_link -Z toward the tool.
      mount.position.set(0, -0.000218214, 0.000949706);
      mount.rotation.x = Math.PI;
      robot.links.gripper_link.add(mount);
    });
    scene.add(robot);
  }, undefined, error => onStatus(`Model unavailable: ${error.message}`));

  function apply(model, pose) {
    if (!model || !pose) return;
    for (const j of JOINTS) {
      // Gripper uses an illustrative 0–100° opening; hardware stores 0–100%.
      model.joints[j].setJointValue(THREE.MathUtils.degToRad(pose[j]));
    }
    model.updateMatrixWorld(true);
  }
  function setLive(pose) { livePose = pose; apply(robot, pose); }
  function showGhost(pose) {
    ghostPose = pose;
    if (ghost) { ghost.visible = Boolean(pose); apply(ghost, pose); }
  }
  function tcp(pose) {
    apply(ghost, pose);
    return ghost.links.gripper_frame_link.getWorldPosition(new THREE.Vector3());
  }
  function setPlan(plan) {
    queuedPlan = plan;
    for (const child of [...pathRoot.children]) {
      child.geometry.dispose();
      child.material.dispose();
      pathRoot.remove(child);
    }
    if (!ghost || !plan) return;
    const count = Math.min(2400, Math.max(60, Math.ceil(plan.duration * 30)));
    const points = Array.from({ length: count + 1 }, (_, i) => tcp(samplePlan(plan, plan.duration * i / count).pose));
    pathRoot.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color: 0x7ce6cc, transparent: true, opacity: 0.8 })));
    for (const segment of plan.segments) {
      const marker = new THREE.Mesh(new THREE.SphereGeometry(0.004, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffd39e }));
      marker.position.copy(tcp(segment.to));
      pathRoot.add(marker);
    }
    showGhost(ghostPose);
  }
  function fit() {
    if (!robot) return;
    robot.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(robot);
    const center = box.getCenter(new THREE.Vector3());
    const radius = box.getSize(new THREE.Vector3()).length() / 2;
    const distance = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) / Math.min(camera.aspect, 1) * 1.25;
    controls.target.copy(center);
    camera.position.copy(center).add(new THREE.Vector3(0.75, -1, 0.55).normalize().multiplyScalar(distance));
    controls.update();
  }
  new ResizeObserver(() => {
    const { clientWidth: width, clientHeight: height } = viewport;
    if (!width || !height) return;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }).observe(viewport);
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
  return { setLive, showGhost, setPlan, fit, setGrid: value => { grid.visible = value; }, setPath: value => { pathRoot.visible = value; } };
}
