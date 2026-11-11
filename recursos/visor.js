/* Página del visor: navegación entre pasos, vistas y nombres. La escena está en escena.js.
   Los pasos escritos están en el HTML, así que se pueden leer aunque el 3D no cargue. */
import { crearEscena, nombresDe } from "./escena.js";

const datos = JSON.parse(document.getElementById("modelo").textContent);
const N = datos.pasos.length;
const movimientoReducido = matchMedia("(prefers-reduced-motion: reduce)").matches;
// Las mejoras del render que van también en la impresión (nudos/imprimir.py, MEJORAS_ACTIVAS).
// El supermuestreo es solo de la impresión: en pantalla, el lienzo ya sigue la densidad de px.
const MEJORAS = { contacto: true, sombrasSuaves: true };

const stage = document.getElementById("stage");
const msg = document.getElementById("stageMsg");
// Cada nombre con su etiqueta y su línea. «Firme» y «Chicote» están en el HTML; con varias
// cuerdas se agrega una etiqueta con el nombre de cada una.
const tags = {
  firme: [document.getElementById("tagFirme"), document.getElementById("lineFirme")],
  chicote: [document.getElementById("tagChicote"), document.getElementById("lineChicote")],
};
for (const { clave, texto } of nombresDe(datos)) {
  if (tags[clave]) continue;
  const el = document.createElement("span");
  el.className = "tag"; el.hidden = true; el.textContent = texto;
  const linea = document.createElementNS("http://www.w3.org/2000/svg", "line");
  linea.setAttribute("visibility", "hidden");
  document.querySelector("#tags .lineas").append(linea);
  document.getElementById("tags").append(el);
  tags[clave] = [el, linea];
}
const countEl = document.getElementById("count");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const viewTop = document.getElementById("viewTop");
const view3d = document.getElementById("view3d");
const optHl = document.getElementById("optHl");
const optTags = document.getElementById("optTags");
const stepButtons = [...document.querySelectorAll(".step")];

let current = 1;
let view = "3d";
let escena = null;

function stepFromHash() {
  const m = /^#paso-(\d+)$/.exec(location.hash);
  const n = m ? Number(m[1]) : 1;
  return n >= 1 && n <= N ? n : 1;
}

function syncUi() {
  stepButtons.forEach((b) => {
    if (Number(b.dataset.n) === current) b.setAttribute("aria-current", "step");
    else b.removeAttribute("aria-current");
  });
  countEl.textContent = `Paso ${current} de ${N}`;
  prevBtn.disabled = current === 1;
  nextBtn.disabled = current === N;
  try { history.replaceState(null, "", `#paso-${current}`); } catch (e) { /* sin historial */ }
}

function go(n) {
  n = Math.max(1, Math.min(N, n));
  if (n === current && escena) return;
  current = n;
  syncUi();
  if (escena) escena.mostrarPaso(n);
}

function setView(v) {
  view = v;
  viewTop.setAttribute("aria-pressed", String(v === "arriba"));
  view3d.setAttribute("aria-pressed", String(v === "3d"));
  if (escena) escena.vista(v);
}

function placeTag(el, linea, a) {
  const q = optTags.checked && a ? escena.proyectar(a.etiqueta) : null;
  if (!q || !q.visible) { el.hidden = true; linea.setAttribute("visibility", "hidden"); return; }
  const p = escena.proyectar(a.punto);
  el.hidden = false;
  el.style.transform = `translate(${q.x}px, ${q.y}px) translate(-50%, -50%)`;
  linea.setAttribute("x1", p.x); linea.setAttribute("y1", p.y);
  linea.setAttribute("x2", q.x); linea.setAttribute("y2", q.y);
  linea.setAttribute("visibility", "visible");
}

function placeTags() {
  const a = escena && escena.anclas();
  for (const [clave, [el, linea]] of Object.entries(tags)) placeTag(el, linea, a && a[clave]);
}

function themeShadow() {
  if (!escena) return;
  const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--shadow-alpha"));
  escena.opacidadSombra(Number.isFinite(v) ? v : 0.3);
}

stepButtons.forEach((b) => b.addEventListener("click", () => go(Number(b.dataset.n))));
prevBtn.addEventListener("click", () => go(current - 1));
nextBtn.addEventListener("click", () => go(current + 1));
window.addEventListener("keydown", (e) => {
  if (e.target.closest && e.target.closest("input, textarea, select")) return;
  if (e.key === "ArrowRight") { go(current + 1); e.preventDefault(); }
  if (e.key === "ArrowLeft") { go(current - 1); e.preventDefault(); }
});
window.addEventListener("hashchange", () => go(stepFromHash()));
viewTop.addEventListener("click", () => setView("arriba"));
view3d.addEventListener("click", () => setView("3d"));
optHl.addEventListener("change", () => escena && escena.resaltar(optHl.checked));
optTags.addEventListener("change", () => escena && escena.pedirCuadro());

current = stepFromHash();
syncUi();

/* Tamaño de cada etiqueta en px. Si está oculta, se muestra un instante sin pintarla para medirla. */
function medir(el) {
  const oculto = el.hidden;
  if (oculto) { el.style.visibility = "hidden"; el.hidden = false; }
  const m = { w: el.offsetWidth, h: el.offsetHeight };
  if (oculto) { el.hidden = true; el.style.visibility = ""; }
  return m;
}
const medidasNombres = () => Object.fromEntries(Object.entries(tags).map(([clave, [el]]) => [clave, medir(el)]));

try {
  escena = crearEscena(stage, datos, { movimientoReducido, alRenderizar: placeTags, medidasNombres, mejoras: MEJORAS });
} catch (e) {
  msg.textContent = "Este visor necesita WebGL. Ábrelo en un navegador con aceleración gráfica; los pasos escritos siguen abajo.";
}

if (escena) {
  const lienzo = escena.lienzo;
  lienzo.setAttribute("tabindex", "0");
  lienzo.setAttribute("aria-label", "Modelo 3D del paso. Arrastra para girar.");
  escena.mostrarPaso(current);
  escena.vista(view, true);
  escena.resaltar(optHl.checked);
  themeShadow();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeShadow);
  // Con las fuentes cargadas cambia el ancho de las etiquetas.
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => escena.colocarNombres());
  msg.hidden = true;
  window.visorListo = true;
}
