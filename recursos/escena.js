/* Escena 3D de un nudo. La usan el visor del sitio y, desde T3, las imágenes de impresión.
   Unidades: diámetros de cuerda. La mesa es el plano z = 0 y la cámara mira hacia abajo.
   Este archivo corre desde el sitio construido: las rutas a three.js son las de recursos/. */
import * as THREE from "./vendor/three/three.module.min.js";
import { OrbitControls } from "./vendor/three/OrbitControls.js";

export const VISTAS = {
  arriba: { polar: 0.001, az: 0 },
  "3d": { polar: 0.68, az: -0.32 },
};

const RADIO = 0.5;        // la cuerda mide un diámetro
const REMATE = 0.8;       // largo del remate en el chicote
const ALTO = 1.6;         // alto que se considera al encuadrar: una cuerda sobre otra
const MARGEN = 1.0;       // margen alrededor de la cuerda al encuadrar

/* Trenza de 16 hilos, 2 sobre 2. Un mosaico es una vuelta completa de cada hilo (π·d de largo). */
function texturasTrenza(renderer, top, mid, low, tracer) {
  const S = 512;
  const col = document.createElement("canvas"); col.width = col.height = S;
  const hgt = document.createElement("canvas"); hgt.width = hgt.height = S;
  const ci = col.getContext("2d").createImageData(S, S);
  const hi = hgt.getContext("2d").createImageData(S, S);
  const c = ci.data, h = hi.data;
  const T = top.map((v) => v / 255), M = mid.map((v) => v / 255), L = low.map((v) => v / 255), R = tracer.map((v) => v / 255);
  for (let py = 0; py < S; py++) {
    const v = (py + 0.5) / S;
    for (let px = 0; px < S; px++) {
      const u = (px + 0.5) / S;
      const pa = 8 * v + 8 * u, pb = 8 * v - 8 * u;
      const i = Math.floor(pa), j = Math.floor(pb);
      const fa = pa - i, fb = pb - j;
      const m = (((i + j) % 4) + 4) % 4;
      const isA = m < 2;
      const across = isA ? fa : fb;
      const along = isA ? (m + fb) / 2 : (m - 2 + fa) / 2;
      const prof = Math.sqrt(Math.max(0, 1 - (2 * across - 1) ** 2));
      const ends = Math.pow(Math.sin(Math.PI * along), 0.55);
      const yarn = 0.9 + 0.1 * Math.cos(across * Math.PI * 12);
      const k = prof * (0.3 + 0.7 * ends);
      let base = M, hiC = T;
      const tr = isA && ((i % 8) + 8) % 8 === 0 && Math.abs(across - 0.5) < 0.2 && ((Math.floor(j / 4) % 2) + 2) % 2 === 0;
      if (tr) { base = R; hiC = R.map((x) => Math.min(1, x * 1.25)); }
      const kk = k * yarn;
      const t1 = Math.min(1, kk / 0.55), t2 = Math.max(0, (kk - 0.55) / 0.45);
      const o = (py * S + px) * 4;
      for (let ch = 0; ch < 3; ch++) {
        const a = L[ch] + (base[ch] - L[ch]) * t1;
        c[o + ch] = Math.round(255 * (a + (hiC[ch] - a) * t2 * 0.6));
      }
      c[o + 3] = 255;
      const hv = Math.round(255 * Math.min(1, kk));
      h[o] = h[o + 1] = h[o + 2] = hv; h[o + 3] = 255;
    }
  }
  col.getContext("2d").putImageData(ci, 0, 0);
  hgt.getContext("2d").putImageData(hi, 0, 0);
  const mk = (cv, srgb) => {
    const t = new THREE.CanvasTexture(cv);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  };
  return { map: mk(col, true), bump: mk(hgt, false) };
}

function texturaRemate() {
  const cv = document.createElement("canvas"); cv.width = 64; cv.height = 8;
  const g = cv.getContext("2d");
  for (let x = 0; x < 64; x++) {
    const k = 0.5 + 0.5 * Math.cos((x / 64) * Math.PI * 2 * 4);
    const r = Math.round(70 + 60 * k), gg = Math.round(14 + 12 * k), b = Math.round(16 + 12 * k);
    g.fillStyle = `rgb(${r},${gg},${b})`; g.fillRect(x, 0, 1, 8);
  }
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function puntos(paso) {
  const pts = [];
  for (let k = 0; k < paso.p.length; k += 3) pts.push(new THREE.Vector3(paso.p[k], paso.p[k + 1], paso.p[k + 2]));
  return pts;
}

/* La caja que se encuadra: la parte de la cuerda que queda dentro del encuadre de la
   especificación, en todos los pasos, con un margen. Sin encuadre, toda la cuerda. */
function cajaDeEncuadre(modelo) {
  const e = modelo.encuadre;
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const s of modelo.pasos) {
    for (let k = 0; k < s.p.length; k += 3) {
      const x = s.p[k], y = s.p[k + 1];
      if (e && (x < e.x[0] || x > e.x[1] || y < e.y[0] || y > e.y[1])) continue;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  return { x0: x0 - MARGEN, x1: x1 + MARGEN, y0: y0 - MARGEN, y1: y1 + MARGEN };
}

export function crearEscena(contenedor, modelo, { interactiva = true, movimientoReducido = false, alRenderizar = null, medidasNombres = null } = {}) {
  // Si el navegador no tiene WebGL, esto lanza una excepción y quien llama muestra el aviso.
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: !interactiva });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  contenedor.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 500);
  camera.up.set(0, 0, 1);

  const B = cajaDeEncuadre(modelo);
  const cx = (B.x0 + B.x1) / 2, cy = (B.y0 + B.y1) / 2;
  const esquinas = [];
  for (const x of [B.x0, B.x1]) for (const y of [B.y0, B.y1]) for (const z of [0, ALTO]) esquinas.push(new THREE.Vector3(x, y, z));
  const centroFit = new THREE.Vector3(cx, cy, 0.5);
  // Donde la cuerda entra al encuadre se pone el nombre «Firme».
  const e = modelo.encuadre;
  const interior = e ? { x0: e.x[0] + 1, x1: e.x[1] - 1, y0: e.y[0] + 1, y1: e.y[1] - 1 }
    : { x0: B.x0 + 2, x1: B.x1 - 2, y0: B.y0 + 2, y1: B.y1 - 2 };
  const dentro = (p) => p.x >= interior.x0 && p.x <= interior.x1 && p.y >= interior.y0 && p.y <= interior.y1;

  // Luces
  scene.add(new THREE.HemisphereLight(0xf4f7ff, 0x8a8f99, 1.5));
  const sol = new THREE.DirectionalLight(0xffffff, 2.4);
  sol.position.set(cx - 10, cy + 12, 26);
  sol.target.position.set(cx, cy, 0);
  sol.castShadow = true;
  sol.shadow.mapSize.set(2048, 2048);
  const ext = Math.max(B.x1 - B.x0, B.y1 - B.y0) / 2 + 10;
  Object.assign(sol.shadow.camera, { left: -ext, right: ext, top: ext, bottom: -ext, near: 1, far: 90 });
  sol.shadow.camera.updateProjectionMatrix();
  sol.shadow.bias = -0.0003;
  sol.shadow.normalBias = 0.02;
  scene.add(sol, sol.target);
  const relleno = new THREE.DirectionalLight(0xdfe8ff, 0.6);
  relleno.position.set(cx + 14, cy - 16, 10);
  scene.add(relleno);

  const matSombra = new THREE.ShadowMaterial({ opacity: 0.26 });
  const mesa = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), matSombra);
  mesa.receiveShadow = true;
  scene.add(mesa);

  // Materiales: azul, ámbar para lo que se mueve en el paso y el remate del chicote.
  const azul = texturasTrenza(renderer, [118, 156, 238], [42, 88, 200], [12, 30, 86], [196, 36, 44]);
  const ambar = texturasTrenza(renderer, [255, 214, 140], [222, 140, 34], [92, 46, 6], [150, 30, 30]);
  const matAzul = new THREE.MeshStandardMaterial({ map: azul.map, bumpMap: azul.bump, bumpScale: 2.2, roughness: 0.78, metalness: 0 });
  const matAmbar = new THREE.MeshStandardMaterial({ map: ambar.map, bumpMap: ambar.bump, bumpScale: 2.2, roughness: 0.78, metalness: 0 });
  const matRemate = new THREE.MeshStandardMaterial({ map: texturaRemate(), roughness: 0.6, metalness: 0 });
  const matPunta = new THREE.MeshStandardMaterial({ color: 0x1b1517, roughness: 0.45, metalness: 0 });
  const geoTapa = new THREE.SphereGeometry(RADIO, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2);
  const mats = [matAzul, matAmbar, matRemate];

  let controls = null;
  if (interactiva) {
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.09;
    controls.minDistance = 7;
    controls.maxDistance = 160;
    controls.maxPolarAngle = Math.PI * 0.46;
    controls.target.copy(centroFit);
  }

  const construidos = new Map();
  let activo = null;
  let vistaActual = "3d";
  let anim = null;
  let movidoPorUsuario = false;
  let pendiente = true;
  const pedirCuadro = () => { pendiente = true; };
  if (controls) {
    controls.addEventListener("change", pedirCuadro);
    controls.addEventListener("start", () => { movidoPorUsuario = true; anim = null; });
  }

  function construirPaso(paso) {
    const pts = puntos(paso);
    let L = 0;
    for (let k = 1; k < pts.length; k++) L += pts[k].distanceTo(pts[k - 1]);
    const curva = new THREE.CatmullRomCurve3(pts, false, "centripetal");
    curva.arcLengthDivisions = Math.max(200, pts.length * 4);
    const T = Math.ceil(L / 0.08);
    const RS = 20;
    const geo = new THREE.TubeGeometry(curva, T, RADIO, RS, false);
    const porSegmento = RS * 6;
    const w = Math.max(1, Math.round(((L - REMATE) / L) * T));
    const a = paso.hl ? Math.min(w, Math.round(paso.hl[0] * T)) : w;
    const b = paso.hl ? Math.min(w, Math.round(paso.hl[1] * T)) : w;
    geo.clearGroups();
    [[0, a, 0], [a, b, 1], [b, w, 0], [w, T, 2]].forEach(([s0, s1, m]) => {
      if (s1 > s0) geo.addGroup(s0 * porSegmento, (s1 - s0) * porSegmento, m);
    });
    const cuerda = new THREE.Mesh(geo, mats);
    cuerda.castShadow = true; cuerda.receiveShadow = true;
    const grupo = new THREE.Group();
    grupo.add(cuerda);
    const tapa = (t, mat) => {
      const p = curva.getPointAt(t);
      const tan = curva.getTangentAt(t).normalize();
      if (t === 0) tan.negate();
      const m = new THREE.Mesh(geoTapa, mat);
      m.position.copy(p);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tan);
      m.scale.set(1, 0.3, 1);
      m.castShadow = true;
      return m;
    };
    grupo.add(tapa(0, matAzul), tapa(1, matPunta));
    // Nombres: «Firme» junto a donde la cuerda entra al encuadre y «Chicote» junto al extremo.
    // Aquí solo se preparan los lugares posibles, de cerca hacia afuera. Cuál se usa se decide
    // en pantalla (colocarNombres), porque depende del tamaño del nombre y de la cámara.
    const plano = (v) => { v.setZ(0); return v.lengthSq() > 1e-12 ? v.normalize() : v.set(1, 0, 0); };
    const giro = (v, g) => {
      const a = (g * Math.PI) / 180;
      return new THREE.Vector3(v.x * Math.cos(a) - v.y * Math.sin(a), v.x * Math.sin(a) + v.y * Math.cos(a), 0);
    };
    const alrededor = (p, dir, radios, angulos) => radios.flatMap((r) => angulos.map((g) => {
      const c = p.clone().addScaledVector(giro(dir, g), r);
      c.z = p.z + 0.6;
      return c;
    }));
    let k = 0;
    while (k < pts.length - 2 && !dentro(pts[k])) k++;
    const t = plano(pts[k + 1].clone().sub(pts[k]));
    const firme = { punto: pts[k].clone(), candidatos: alrededor(pts[k], t, [1.9, 2.8, 3.8, 5.0], [90, -90, 135, -135, 45, -45]) };
    const fin = curva.getPointAt(1), tanFin = plano(curva.getTangentAt(1));
    const chicote = { punto: fin.clone(), candidatos: alrededor(fin, tanFin, [2.2, 3.2, 4.4, 5.6, 7.0], [0, 45, -45, 90, -90, 135, -135, 180]) };
    firme.etiqueta = firme.candidatos[0];
    chicote.etiqueta = chicote.candidatos[0];
    return { grupo, L, pts, nombres: { firme, chicote } };
  }

  function mostrarPaso(n) {
    const paso = modelo.pasos[n - 1];
    if (!construidos.has(n)) construidos.set(n, construirPaso(paso));
    const c = construidos.get(n);
    if (activo) scene.remove(activo.grupo);
    activo = c;
    scene.add(c.grupo);
    const rep = c.L / Math.PI;
    for (const m of [matAzul, matAmbar]) { m.map.repeat.set(rep, 1); m.bumpMap.repeat.set(rep, 1); }
    matRemate.map.repeat.set(c.L / 0.5, 1);
    colocarNombres();
    pedirCuadro();
  }

  function resaltar(si) {
    mats[1] = si ? matAmbar : matAzul;
    construidos.forEach((c) => { c.grupo.children[0].material = mats; });
    pedirCuadro();
  }

  function opacidadSombra(a) {
    matSombra.opacity = a;
    pedirCuadro();
  }

  /* Encuadre: se ajusta con la proyección real de la cámara para que el lado cercano no se corte. */
  const tmp = new THREE.Vector3();
  function pose(polar, az) {
    const cam = camera.clone();
    cam.updateProjectionMatrix();
    const t = centroFit.clone();
    let dist = 60;
    const right = new THREE.Vector3(), up = new THREE.Vector3(), fwd = new THREE.Vector3();
    const colocar = () => {
      cam.position.set(t.x + dist * Math.sin(polar) * Math.sin(az), t.y - dist * Math.sin(polar) * Math.cos(az), t.z + dist * Math.cos(polar));
      cam.lookAt(t);
      cam.updateMatrixWorld();
    };
    for (let it = 0; it < 8; it++) {
      colocar();
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const c of esquinas) {
        tmp.copy(c).project(cam);
        x0 = Math.min(x0, tmp.x); x1 = Math.max(x1, tmp.x); y0 = Math.min(y0, tmp.y); y1 = Math.max(y1, tmp.y);
      }
      const hh = dist * Math.tan((cam.fov * Math.PI) / 360), hw = hh * cam.aspect;
      cam.matrixWorld.extractBasis(right, up, fwd);
      t.addScaledVector(right, ((x0 + x1) / 2) * hw).addScaledVector(up, ((y0 + y1) / 2) * hh);
      dist *= Math.max((x1 - x0) / 2, (y1 - y0) / 2) / 0.94;
    }
    colocar();
    return { pos: cam.position.clone(), target: t.clone() };
  }

  function vista(nombre, instantanea = false) {
    vistaActual = nombre;
    movidoPorUsuario = false;
    const V = VISTAS[nombre];
    const p = pose(V.polar, V.az);
    if (instantanea || movimientoReducido || !controls) {
      camera.position.copy(p.pos);
      camera.lookAt(p.target);
      if (controls) { controls.target.copy(p.target); controls.update(); }
      anim = null;
      colocarNombres();
      pedirCuadro();
      return;
    }
    anim = { t0: performance.now(), dur: 650, p0: camera.position.clone(), p1: p.pos, q0: controls.target.clone(), q1: p.target };
  }

  function proyectar(p) {
    tmp.copy(p).project(camera);
    const w = contenedor.clientWidth, h = contenedor.clientHeight;
    const visible = tmp.z <= 1 && Math.abs(tmp.x) <= 1.05 && Math.abs(tmp.y) <= 1.05;
    return { x: ((tmp.x + 1) / 2) * w, y: ((1 - tmp.y) / 2) * h, visible };
  }

  /* Para cada nombre: el punto de la cuerda que nombra y dónde va la etiqueta. */
  function anclas() {
    return activo ? activo.nombres : null;
  }

  /* Elige en pantalla dónde va cada nombre: el primer lugar, de cerca hacia afuera, donde la
     etiqueta entra completa en el escenario sin tapar ningún tramo. Si no hay ninguno, el
     menos tapado. Se recalcula cuando la cámara se queda quieta, no mientras se mueve, para
     que los nombres no salten. «medidasNombres» devuelve el tamaño de cada etiqueta en px. */
  function colocarNombres() {
    if (!activo || !medidasNombres) return;
    const medidas = medidasNombres();
    const w = contenedor.clientWidth, h = contenedor.clientHeight;
    if (!w || !h) return;
    camera.updateMatrixWorld();
    const pantalla = (v) => {
      tmp.copy(v).project(camera);
      return { x: ((tmp.x + 1) / 2) * w, y: ((1 - tmp.y) / 2) * h, z: tmp.z };
    };
    const P = activo.pts.map(pantalla).filter((p) => p.z <= 1);
    const derecha = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    const a = pantalla(centroFit), b = pantalla(centroFit.clone().addScaledVector(derecha, RADIO));
    const r = Math.hypot(b.x - a.x, b.y - a.y);   // radio de la cuerda en px
    const puestos = [];   // etiquetas ya colocadas: tampoco se pueden tapar entre sí
    for (const [clave, nom] of Object.entries(activo.nombres)) {
      const m = medidas[clave];
      if (!m || !m.w) continue;
      const hw = m.w / 2 + 3, hh = m.h / 2 + 3;
      let mejor = null, mejorD = -Infinity, mejorQ = null;
      for (const c of nom.candidatos) {
        const q = pantalla(c);
        if (q.z > 1 || q.x - hw < 0 || q.x + hw > w || q.y - hh < 0 || q.y + hh > h) continue;
        let d = Infinity;
        for (const o of puestos) {
          const dx = Math.max(Math.abs(o.x - q.x) - hw - o.hw, 0), dy = Math.max(Math.abs(o.y - q.y) - hh - o.hh, 0);
          d = Math.min(d, Math.hypot(dx, dy) - 2);
        }
        for (const p of P) {
          if (d < mejorD) break;   // ya no puede ganar
          const dx = Math.max(Math.abs(p.x - q.x) - hw, 0), dy = Math.max(Math.abs(p.y - q.y) - hh, 0);
          d = Math.min(d, Math.hypot(dx, dy) - r);
        }
        if (d >= 0) { mejor = c; mejorQ = q; break; }
        if (d > mejorD) { mejor = c; mejorD = d; mejorQ = q; }
      }
      nom.etiqueta = mejor || nom.candidatos[0];
      if (mejorQ) puestos.push({ x: mejorQ.x, y: mejorQ.y, hw, hh });
    }
    pedirCuadro();
  }

  function renderizar() {
    renderer.render(scene, camera);
    pendiente = false;
    if (alRenderizar) alRenderizar();
  }

  function redimensionar() {
    const w = contenedor.clientWidth, h = contenedor.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (!movidoPorUsuario && !anim) vista(vistaActual, true);
    else colocarNombres();
    pedirCuadro();
  }

  let enMovimiento = false;
  function cuadro(ahora) {
    requestAnimationFrame(cuadro);
    if (anim) {
      const t = Math.min(1, (ahora - anim.t0) / anim.dur);
      const s = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      camera.position.lerpVectors(anim.p0, anim.p1, s);
      controls.target.lerpVectors(anim.q0, anim.q1, s);
      if (t >= 1) anim = null;
      pendiente = true;
    }
    const movio = controls ? controls.update() : false;
    // Cuando la cámara se queda quieta, los nombres buscan su lugar.
    if (anim || movio) enMovimiento = true;
    else if (enMovimiento) { enMovimiento = false; colocarNombres(); }
    if (pendiente || movio) renderizar();
  }

  new ResizeObserver(redimensionar).observe(contenedor);
  redimensionar();
  requestAnimationFrame(cuadro);

  return { lienzo: renderer.domElement, mostrarPaso, vista, resaltar, opacidadSombra, proyectar, anclas, colocarNombres, renderizar, pedirCuadro };
}
