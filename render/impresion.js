/* Dibuja una imagen de impresión con la misma escena del visor. nudos/imprimir.py llama a
   window.dibujar(trabajo) y toma la captura cuando la promesa se cumple.
   trabajo: { modelo, paso, vista, resaltar, nombres: ["firme", "chicote"] } */
import { crearEscena } from "./recursos/escena.js";

const stage = document.getElementById("stage");
const tags = {
  firme: [document.getElementById("tagFirme"), document.getElementById("lineFirme")],
  chicote: [document.getElementById("tagChicote"), document.getElementById("lineChicote")],
};

function medir(el) {
  const oculto = el.hidden;
  if (oculto) { el.style.visibility = "hidden"; el.hidden = false; }
  const m = { w: el.offsetWidth, h: el.offsetHeight };
  if (oculto) { el.hidden = true; el.style.visibility = ""; }
  return m;
}

/* Igual que en el visor: la etiqueta en su lugar y una línea hasta el punto que nombra.
   Un nombre cuyo punto queda fuera de la imagen no se pone. */
function colocar(escena, usar) {
  const anclas = escena.anclas();
  for (const [clave, [el, linea]] of Object.entries(tags)) {
    const a = anclas && usar.includes(clave) ? anclas[clave] : null;
    const p = a ? escena.proyectar(a.punto) : null;
    const q = a ? escena.proyectar(a.etiqueta) : null;
    if (!p || !q || !p.visible || !q.visible) { el.hidden = true; linea.setAttribute("visibility", "hidden"); continue; }
    el.hidden = false;
    el.style.transform = `translate(${q.x}px, ${q.y}px) translate(-50%, -50%)`;
    linea.setAttribute("x1", p.x); linea.setAttribute("y1", p.y);
    linea.setAttribute("x2", q.x); linea.setAttribute("y2", q.y);
    linea.setAttribute("visibility", "visible");
  }
}

const cuadro = () => new Promise((listo) => requestAnimationFrame(() => requestAnimationFrame(listo)));

window.dibujar = async function (trabajo) {
  await document.fonts.load('400 10px "IBM Plex Mono"');
  const usar = trabajo.nombres || [];
  let escena = null;
  escena = crearEscena(stage, trabajo.modelo, {
    interactiva: false,
    movimientoReducido: true,
    alRenderizar: () => escena && colocar(escena, usar),
    medidasNombres: () => Object.fromEntries(
      Object.entries(tags).map(([k, [el]]) => [k, usar.includes(k) ? medir(el) : { w: 0, h: 0 }])),
  });
  escena.mostrarPaso(trabajo.paso);
  escena.vista(trabajo.vista, true);
  escena.resaltar(trabajo.resaltar);
  escena.colocarNombres();
  escena.renderizar();
  await cuadro();
  escena.renderizar();
  await cuadro();
  return true;
};
window.impresionLista = true;
