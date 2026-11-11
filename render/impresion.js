/* Dibuja una imagen de impresión con la misma escena del visor. nudos/imprimir.py llama a
   window.dibujar(trabajo) y toma la captura cuando la promesa se cumple.
   trabajo: { modelo, paso, vista, resaltar, nombres: ["firme", "chicote"], reservado: [ancho, alto], mejoras: [] }
   «nombres» son claves de nombresDe (escena.js). «reservado» es la esquina superior
   izquierda, en px, que la ficha tapa con el número del paso o un sello: ahí no se ponen
   los nombres. «mejoras» son las de T7b (nudos/imprimir.py, MEJORAS); el supermuestreo no
   llega aquí: lo hace nudos/imprimir.py dibujando al doble y reduciendo. */
import { crearEscena, nombresDe } from "./recursos/escena.js";

const PT = 300 / 72;          // px por punto de impresión (impresion.html)
const CONTORNO_PT = 0.7;      // el borde de tinta mide 0,7 pt, 0,25 mm

/* Las mejoras de la lista, como las recibe crearEscena. Sin ninguna, la escena de siempre. */
function opcionesMejoras(lista) {
  const m = {};
  if (lista.includes("contorno")) m.contorno = CONTORNO_PT * PT;
  if (lista.includes("contacto")) m.contacto = true;
  if (lista.includes("sombras-suaves")) m.sombrasSuaves = true;
  return m;
}

const stage = document.getElementById("stage");
const tags = {
  firme: [document.getElementById("tagFirme"), document.getElementById("lineFirme")],
  chicote: [document.getElementById("tagChicote"), document.getElementById("lineChicote")],
};

/* Con varias cuerdas, una etiqueta más por cuerda, con su nombre. */
function agregarNombres(modelo) {
  const lineas = document.querySelector(".lineas"), caja = document.querySelector(".tags");
  for (const { clave, texto } of nombresDe(modelo)) {
    if (tags[clave]) continue;
    const el = document.createElement("span");
    el.className = "tag"; el.hidden = true; el.textContent = texto;
    const linea = document.createElementNS("http://www.w3.org/2000/svg", "line");
    linea.setAttribute("visibility", "hidden");
    lineas.append(linea); caja.append(el);
    tags[clave] = [el, linea];
  }
}

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
  const [rw, rh] = trabajo.reservado || [0, 0];
  agregarNombres(trabajo.modelo);
  let escena = null;
  escena = crearEscena(stage, trabajo.modelo, {
    interactiva: false,
    movimientoReducido: true,
    reservado: rw && rh ? [{ x0: 0, y0: 0, x1: rw, y1: rh }] : [],
    mejoras: opcionesMejoras(trabajo.mejoras || []),
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
