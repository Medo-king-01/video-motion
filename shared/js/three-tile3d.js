// Optional Three.js r187 PBR 3D extruded tile scene builder for engines K and R.
// Plugs directly into `createThreeLayer` (`three-layer.js`) with synchronous `update(t)`
// and deterministic disposal through `resources.defer(...)`.
// Pure relative import of `./tile3d.js` so engines K and R share this file byte for byte.
import { TILE3D_PALETTE, TILE3D_ROLES, sampleTilePose } from './tile3d.js';

const DEG2RAD = Math.PI / 180;

function makeRoundedShape(THREE, width, height, radius) {
  const s = new THREE.Shape();
  const x = -width / 2, y = -height / 2;
  const r = Math.min(width * 0.48, height * 0.48, Math.max(0.01, radius));
  s.moveTo(x + r, y);
  s.lineTo(x + width - r, y);
  s.quadraticCurveTo(x + width, y, x + width, y + r);
  s.lineTo(x + width, y + height - r);
  s.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  s.lineTo(x + r, y + height);
  s.quadraticCurveTo(x, y + height, x, y + height - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

function makeCanvas(size, canvasFactory) {
  if (typeof canvasFactory === 'function') return canvasFactory(size, size);
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  return c;
}

/**
 * Build a `{ scene, camera, update(t), dispose() }` rig of 3D extruded explainer tiles
 * ready for `createThreeLayer({ THREE, width, height, scene, camera, update, resources })`.
 */
export function buildThreeTileScene({
  THREE,
  width = 1080,
  height = 1920,
  fov = 30,
  tiles = [],
  rimColor = TILE3D_PALETTE.salmon,
  resources = null,
  canvasFactory = null,
} = {}) {
  if (!THREE || typeof THREE.Scene !== 'function') throw new Error('THREE namespace is required');
  const scene = new THREE.Scene();
  const dist = 8;
  const camera = new THREE.PerspectiveCamera(fov, width / height, 0.1, 100);
  camera.position.set(0, 0, dist);
  camera.lookAt(0, 0, 0);

  const visibleH = 2 * dist * Math.tan((fov * Math.PI) / 360);
  const pxToWorld = visibleH / height;

  const keyLight = new THREE.DirectionalLight(TILE3D_PALETTE.paper, 2.2);
  keyLight.position.set(3, 5, 7);
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(rimColor, 1.15);
  rimLight.position.set(-6, 3, -4);
  scene.add(rimLight);

  scene.add(new THREE.AmbientLight(TILE3D_PALETTE.paper, 0.35));

  const disposables = [];
  const entries = tiles.map(spec => {
    const role = TILE3D_ROLES[spec.role || 'paper'] || TILE3D_ROLES.paper;
    const rad = spec.radiusRatio ?? 0.22;
    const depth = spec.depthRatio ?? 0.18;
    const bevel = Math.min(0.035, depth * 0.22);

    const shape = makeRoundedShape(THREE, 1 - bevel * 2, 1 - bevel * 2, rad);
    const bodyGeo = new THREE.ExtrudeGeometry(shape, {
      depth: Math.max(0.02, depth - bevel * 2),
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: bevel,
      bevelThickness: bevel,
    });
    bodyGeo.center();
    const sideMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(role.side),
      roughness: 0.36,
      metalness: 0.08,
    });
    const group = new THREE.Group();
    group.add(new THREE.Mesh(bodyGeo, sideMat));

    // Crisp un-tonemapped front face canvas texture
    const faceCanvas = makeCanvas(512, canvasFactory);
    const fx = faceCanvas.getContext('2d');
    const fr = 512 * rad;
    fx.beginPath();
    fx.roundRect(0, 0, 512, 512, fr);
    fx.fillStyle = role.face;
    fx.fill();
    if (typeof spec.drawSymbol === 'function') {
      fx.save();
      fx.translate(256, 256);
      spec.drawSymbol(fx, 512, role.fg);
      fx.restore();
    }
    const faceTex = new THREE.CanvasTexture(faceCanvas);
    if (THREE.SRGBColorSpace) faceTex.colorSpace = THREE.SRGBColorSpace;
    const planeGeo = new THREE.PlaneGeometry(1, 1);
    const frontMat = new THREE.MeshBasicMaterial({ map: faceTex, transparent: true, toneMapped: false });
    const frontMesh = new THREE.Mesh(planeGeo, frontMat);
    frontMesh.position.z = depth / 2 + 0.002;
    group.add(frontMesh);

    // Animated diagonal specular gloss canvas
    const glossCanvas = makeCanvas(256, canvasFactory);
    const glossTex = new THREE.CanvasTexture(glossCanvas);
    if (THREE.SRGBColorSpace) glossTex.colorSpace = THREE.SRGBColorSpace;
    const glossMat = new THREE.MeshBasicMaterial({
      map: glossTex,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      toneMapped: false,
    });
    const glossMesh = new THREE.Mesh(planeGeo, glossMat);
    glossMesh.position.z = depth / 2 + 0.004;
    group.add(glossMesh);

    scene.add(group);
    disposables.push(bodyGeo, planeGeo, sideMat, frontMat, glossMat, faceTex, glossTex);
    return { spec, group, glossCanvas, glossTex, mats: [sideMat, frontMat, glossMat], rad };
  });

  function updateGloss(entry, shineCenter) {
    const gx = entry.glossCanvas.getContext('2d');
    const n = 256;
    gx.clearRect(0, 0, n, n);
    const shineAlpha = entry.spec.shine ?? 0.22;
    if (shineAlpha <= 0) return;
    gx.save();
    gx.beginPath();
    gx.roundRect(0, 0, n, n, n * entry.rad);
    gx.clip();
    const grad = gx.createLinearGradient(n * (shineCenter - 0.25), 0, n * (shineCenter + 0.25), n);
    grad.addColorStop(0, 'rgba(243,242,241,0)');
    grad.addColorStop(0.5, `rgba(243,242,241,${shineAlpha})`);
    grad.addColorStop(1, 'rgba(243,242,241,0)');
    gx.fillStyle = grad;
    gx.fillRect(0, 0, n, n);
    gx.restore();
    entry.glossTex.needsUpdate = true;
  }

  function update(t) {
    for (const entry of entries) {
      const pose = sampleTilePose(entry.spec, t);
      updateGloss(entry, pose.shineCenter);
      const worldScale = Math.max(1e-3, pose.size * pose.scale * pxToWorld);
      const wx = (pose.x - width / 2) * pxToWorld;
      const wy = -(pose.y - height / 2) * pxToWorld;
      const wz = pose.z * pxToWorld;
      entry.group.position.set(wx, wy, wz);
      entry.group.rotation.set(pose.rx * DEG2RAD, pose.ry * DEG2RAD, pose.rz * DEG2RAD);
      entry.group.scale.setScalar(worldScale);
      entry.group.visible = pose.opacity > 0.003;
      for (const m of entry.mats) {
        m.transparent = true;
        m.opacity = pose.opacity;
      }
    }
  }

  let disposed = false;
  function dispose() {
    if (disposed) return;
    disposed = true;
    for (const d of disposables) d?.dispose?.();
  }
  if (typeof resources?.defer === 'function') resources.defer(dispose);

  return { scene, camera, update, dispose };
}
