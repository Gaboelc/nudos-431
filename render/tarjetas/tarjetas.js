/* Las tarjetas del video (T22), dibujadas en función del tiempo.

   Tarjetas.montar(escenario, datos) arma las tarjetas de `datos.tarjetas` dentro de un
   .escenario (tarjetas.css) y da {pintar(t), duracion}. pintar(t) deja todo como se ve en el
   instante t, sin estado: la maqueta lo llama en cada cuadro de la pantalla, y T22b lo llamará en
   Edge una vez por cada cuadro del video, sobre fondo transparente.

   Cada tarjeta es {tipo, desde, hasta, ...}: «nombre», «materiales», «paso», «capitulo»,
   «revisa» (la ✓ junto a lo que se revisa), «error» (la ✗ o, con si: true, la ✓ del correcto),
   «seguridad», «cierre» y «subtitulos» (el reel, palabra por palabra). Entran con un rebote suave
   (un resorte con un 5 % de sobrepaso) y salen rápido. El fondo de las tarjetas de capítulo es
   ruido simplex de lygia (generative/snoise.glsl, MIT), en WebGL. */
(function () {
  "use strict";

  // ---------------------------------------------------------------- el tiempo
  const ENTRADA = 0.7;      // s: lo que tarda en asentarse el rebote
  const SALIDA = 0.22;      // s: salen rápido

  const limitar = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const suave = (x) => { const u = limitar(x); return u * u * (3 - 2 * u); };
  const fuera = (x) => { const u = limitar(x); return 1 - Math.pow(1 - u, 3); };   // frena al llegar
  const dentro = (x) => { const u = limitar(x); return u * u * u; };                // arranca lento

  // La respuesta de un resorte amortiguado: de 0 a 1, con un sobrepaso suave.
  function resorte(t, f = 2.0, z = 0.68) {
    if (t <= 0) return 0;
    const w = 2 * Math.PI * f, wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
  }

  // Cómo está una tarjeta en t: null si no se ve; si no, la entrada (con rebote) y la salida.
  function momento(t, desde, hasta, salida = SALIDA) {
    if (t < desde || t > hasta) return null;
    const a = t - desde, b = hasta - t;
    return { a, b, e: resorte(a), s: b < salida ? dentro(1 - b / salida) : 0, o: fuera(a / 0.16) * (1 - (b < salida ? dentro(1 - b / salida) : 0)) };
  }

  function poner(el, m, desplazar = 46, escala = 0.06) {
    if (!m) { el.style.opacity = 0; el.style.visibility = "hidden"; return; }
    el.style.visibility = "visible";
    el.style.opacity = m.o.toFixed(3);
    const y = (1 - m.e) * desplazar + m.s * m.s * 28;
    const k = 1 - escala + escala * m.e - 0.02 * m.s;
    el.style.transform = `translate3d(0, ${y.toFixed(2)}px, 0) scale(${k.toFixed(4)})`;
  }

  // ---------------------------------------------------------------- lo que se dibuja
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function nodo(html) { const d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

  const ICONOS = {
    cuerda: '<path d="M4 15.5c0-4.2 3.6-7.5 8-7.5s8 3.3 8 7.5c0 2.6-2.3 4.5-5.3 4.5-2.5 0-4.2-1.4-4.2-3.1 0-1.8 1.7-3.1 3.9-3.1 1.6 0 2.8.7 3.3 1.8"/><path d="M12 8V3.5"/>',
    pasos: '<path d="M9.5 6.5h10M9.5 12h10M9.5 17.5h10"/><path d="M4.5 6.5h1.5M4.5 12h1.5M4.5 17.5h1.5"/>',
    si: '<path d="M5 12.6l4.6 4.6L19.2 7.6"/>',
    no: '<path d="M7.2 7.2l9.6 9.6M16.8 7.2l-9.6 9.6"/>',
    tienda: '<path d="M2.8 20h18.4"/><path d="M12 4.2L4.4 20M12 4.2L19.6 20"/><path d="M9.3 20l2.7-5.6 2.7 5.6"/>',
    escudo: '<path d="M12 3l7.2 3v5.2c0 4.9-3.1 8.4-7.2 9.8-4.1-1.4-7.2-4.9-7.2-9.8V6z"/><path d="M12 8.2v4.6M12 16.2v.3"/>',
  };
  const icono = (nombre, tam = 56, grueso = 2.2) =>
    `<svg width="${tam}" height="${tam}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${grueso}" stroke-linecap="round" stroke-linejoin="round">${ICONOS[nombre]}</svg>`;

  function marca(si) {
    return `<div class="marca ${si ? "si" : "no"}"><div class="onda"></div><div class="circulo"></div>
      <svg viewBox="0 0 100 100"><path d="${si ? "M27 52 L43 68 L74 35" : "M32 32 L68 68 M68 32 L32 68"}"/></svg></div>`;
  }

  // La ✓ o la ✗ se dibuja de un trazo después de que el cuadro rebota, con una onda que se abre.
  function pintarMarca(el, a) {
    const p = el.querySelector("path");
    if (!p._largo) { p._largo = p.getTotalLength(); p.style.strokeDasharray = p._largo; }
    p.style.strokeDashoffset = (p._largo * (1 - fuera((a - 0.14) / 0.34))).toFixed(2);
    const c = el.querySelector(".circulo");
    const k = 0.5 + 0.5 * resorte(a, 2.6, 0.5);
    c.style.transform = `scale(${k.toFixed(4)})`;
    const onda = el.querySelector(".onda");
    const u = limitar((a - 0.18) / 0.6);
    onda.style.opacity = (u > 0 && u < 1 ? 0.85 * (1 - u) : 0).toFixed(3);
    onda.style.transform = `scale(${(1 + 0.7 * fuera(u)).toFixed(4)})`;
  }

  // ---------------------------------------------------------------- el fondo de lygia
  const SOMBREADOR = `
precision highp float;
uniform vec2 u_res;
uniform float u_t;
uniform float u_entrada;
uniform vec3 u_a;
uniform vec3 u_b;
__SNOISE__
float azar(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float mancha(vec2 p, vec2 c, float r, float semilla) {
  float d = length(p - c) - r;
  return d + snoise(vec3(p * 2.4 + semilla, u_t * 0.45 + semilla)) * 0.07;
}
void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;
  float n = snoise(vec3(uv * vec2(1.6, 0.9), u_t * 0.18));
  vec3 col = mix(u_a, u_b, smoothstep(-0.35, 1.15, uv.x * 0.85 + uv.y * 0.35 + 0.28 * n));
  // Las formas: manchas de ruido que crecen al entrar y se mueven despacio.
  float r = 0.36 * u_entrada;
  vec2 c1 = vec2(0.95 + 0.06 * sin(u_t * 0.4), 0.22 + 0.05 * cos(u_t * 0.33));
  vec2 c2 = vec2(1.30 + 0.05 * cos(u_t * 0.27), -0.30 + 0.06 * sin(u_t * 0.31));
  vec2 c3 = vec2(-1.05 + 0.05 * sin(u_t * 0.23), -0.42);
  float d1 = mancha(p, c1, r, 3.1);
  float d2 = mancha(p, c2, r * 0.9, 7.7);
  float d3 = mancha(p, c3, r * 0.75, 1.3);
  vec3 claro = mix(u_b, vec3(1.0), 0.35);
  col = mix(col, claro, (1.0 - smoothstep(-0.004, 0.004, d1)) * 0.32);
  col = mix(col, claro, (1.0 - smoothstep(-0.004, 0.004, d2)) * 0.22);
  col = mix(col, mix(u_a, vec3(0.0), 0.15), (1.0 - smoothstep(-0.004, 0.004, d3)) * 0.35);
  // El borde de la primera, como un anillo.
  col = mix(col, vec3(1.0), (1.0 - smoothstep(0.0, 0.006, abs(d1 - 0.06))) * 0.28 * u_entrada);
  col += (azar(gl_FragCoord.xy + fract(u_t)) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}`;

  function hexa(c) { const n = parseInt(c.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }

  function Fondo(canvas) {
    const gl = canvas.getContext("webgl", { preserveDrawingBuffer: true, premultipliedAlpha: false });
    if (!gl || !window.lygia) return { pintar() {} };
    const compilar = (tipo, fuente) => {
      const s = gl.createShader(tipo); gl.shaderSource(s, fuente); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, compilar(gl.VERTEX_SHADER, "attribute vec2 a; void main(){ gl_Position = vec4(a, 0.0, 1.0); }"));
    gl.attachShader(prog, compilar(gl.FRAGMENT_SHADER, SOMBREADOR.replace("__SNOISE__", window.lygia.glsl("generative/snoise.glsl"))));
    gl.linkProgram(prog);
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const u = (n) => gl.getUniformLocation(prog, n);
    const U = { res: u("u_res"), t: u("u_t"), entrada: u("u_entrada"), a: u("u_a"), b: u("u_b") };
    return {
      pintar(t, entrada, a, b) {
        const w = canvas.width, h = canvas.height;
        gl.viewport(0, 0, w, h);
        gl.uniform2f(U.res, w, h);
        gl.uniform1f(U.t, t);
        gl.uniform1f(U.entrada, entrada);
        gl.uniform3fv(U.a, hexa(a));
        gl.uniform3fv(U.b, hexa(b));
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      },
    };
  }

  // ---------------------------------------------------------------- cada tipo
  const TIPOS = {};

  TIPOS.nombre = {
    crear: (d) => nodo(`<div class="t t-nombre vidrio"><div class="grande">${esc(d.nombre)}</div><div class="raya"></div>
      <div class="mono">${esc(d.sub || "")}</div></div>`),
    pintar(el, d, t) {
      const m = momento(t, d.desde, d.hasta, 0.3);
      poner(el, m);
      if (m) el.querySelector(".raya").style.transform = `scaleX(${fuera((m.a - 0.25) / 0.6).toFixed(4)})`;
    },
  };

  TIPOS.materiales = {
    crear: (d) => nodo(`<div class="t t-materiales vidrio"><div class="icono" style="color:#fff">${icono("cuerda", 58)}</div>
      <div><div class="mono">Lo que necesitas</div><div class="texto">${esc(d.texto)}</div></div></div>`),
    pintar: (el, d, t) => poner(el, momento(t, d.desde, d.hasta)),
  };

  // Los pasos seguidos comparten una tarjeta: con «sale», sale y vuelve a entrar en cada paso; con
  // «queda», entra con el primero y en cada cambio solo rueda el número y cambia el título.
  TIPOS.pasos = {
    crear(d) {
      const el = nodo(`<div class="t t-paso vidrio"><div class="insignia"><span class="n0"></span><span class="n1"></span></div>
        <div><div class="mono de"></div><div class="titulo"></div><div class="avance"></div></div></div>`);
      const avance = el.querySelector(".avance");
      for (let i = 1; i <= d.total; i++) {
        if (i > 1) avance.appendChild(document.createElement("b"));
        avance.appendChild(document.createElement("i"));
      }
      return el;
    },
    pintar(el, d, t, opciones) {
      const lista = d.pasos;
      let k = lista.findIndex((p) => t >= p.desde && t <= p.hasta);
      const queda = opciones.pasos === "queda";
      if (k < 0) { poner(el, null); return; }
      const p = lista[k];
      // El sobre de la tarjeta: de cada paso, o del primero al último si se queda.
      const m = queda ? momento(t, lista[0].desde, lista[lista.length - 1].hasta) : momento(t, p.desde, p.hasta);
      poner(el, m);
      if (!m) return;
      const previo = k > 0 ? lista[k - 1] : null;
      const cambio = queda && previo ? limitar((t - p.desde) / 0.45) : 1;
      el.querySelector(".de").textContent = `Paso ${p.n} de ${d.total}`;
      const titulo = el.querySelector(".titulo");
      if (titulo.textContent !== p.titulo) titulo.textContent = p.titulo;
      titulo.style.opacity = queda && previo ? fuera((t - p.desde - 0.08) / 0.3).toFixed(3) : 1;
      // El número rueda hacia arriba.
      const [n0, n1] = el.querySelectorAll(".insignia span");
      n1.textContent = p.n;
      n0.textContent = previo ? previo.n : "";
      const r = queda && previo ? resorte(t - p.desde, 2.4, 0.72) : 1;
      n0.style.transform = `translateY(${(-130 * r).toFixed(2)}px)`;
      n0.style.opacity = (1 - limitar(r)).toFixed(3);
      n1.style.transform = `translateY(${(130 * (1 - r)).toFixed(2)}px)`;
      // El avance: los pasos hechos, la raya que se llena hasta el de ahora y su pulso.
      const puntos = el.querySelectorAll(".avance i"), rayas = el.querySelectorAll(".avance b");
      const a = queda && previo ? t - p.desde : m.a;
      puntos.forEach((q, i) => { q.className = i + 1 < p.n ? "hecho" : i + 1 === p.n ? "ahora" : ""; });
      rayas.forEach((q, i) => q.style.setProperty("--lleno", i + 2 < p.n ? 1 : i + 2 === p.n ? fuera((a - 0.15) / 0.45).toFixed(3) : 0));
      const pul = puntos[p.n - 1];
      const u = ((a - 0.5) % 1.6) / 1.6;
      pul.style.setProperty("--pulso", a > 0.5 ? (0.7 * (1 - u)).toFixed(3) : 0);
      pul.style.setProperty("--pulso-escala", (0.6 + 0.8 * fuera(u)).toFixed(3));
      void cambio;
    },
  };

  TIPOS.capitulo = {
    crear(d) {
      const el = nodo(`<div class="t t-capitulo"><div class="panel"><canvas></canvas><div class="contenido">
        <div class="icono"></div><div class="grande"></div><div class="sub"></div></div></div></div>`);
      return el;
    },
    pintar(el, d, t) {
      const c = d.lista.find((x) => t >= x.desde && t <= x.hasta);
      if (!c) { el.style.opacity = 0; el.style.visibility = "hidden"; return; }
      el.style.visibility = "visible";
      el.style.opacity = 1;
      el.classList.toggle("oscuro", !!c.oscuro);
      const a = t - c.desde, b = c.hasta - t;
      const panel = el.querySelector(".panel");
      const s = b < SALIDA ? dentro(1 - b / SALIDA) : 0;
      // Entra abriéndose desde la izquierda, con rebote; sale rápido hacia la izquierda.
      const r = resorte(a, 1.7, 0.7);
      panel.style.clipPath = `circle(${(1050 * limitar(r, 0, 1.2)).toFixed(1)}px at 0% 50%)`;
      panel.style.transform = `translate(${(-80 * s).toFixed(2)}px, -50%) scale(${(0.94 + 0.06 * r).toFixed(4)})`;
      panel.style.opacity = (1 - s).toFixed(3);
      const [ic, gr, mo] = el.querySelectorAll(".icono, .grande, .sub");
      if (gr.textContent !== c.titulo) { ic.innerHTML = icono(c.icono, 54, 2.4); gr.textContent = c.titulo; mo.textContent = c.sub || ""; }
      [ic, gr, mo].forEach((x, i) => {
        const e = resorte(a - 0.08 - 0.07 * i, 2.0, 0.7);
        x.style.transform = `translateX(${(-60 * (1 - e)).toFixed(2)}px)`;
        x.style.opacity = fuera((a - 0.08 - 0.07 * i) / 0.25).toFixed(3);
      });
      // El fondo, del tamaño del panel (cambia con el título).
      const canvas = el.querySelector("canvas");
      const k = window.devicePixelRatio || 1;
      const w = Math.round(panel.offsetWidth * k), h = Math.round(panel.offsetHeight * k);
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      if (!el._fondo) el._fondo = Fondo(canvas);
      el._fondo.pintar(t, fuera(a / 0.9), c.colores[0], c.colores[1]);
    },
  };

  TIPOS.revisa = {
    crear: (d) => nodo(`<div class="t t-revisa" style="left:${d.x - 36}px; top:${d.y - 36}px">${marca(true)}
      <div class="etiqueta vidrio">${esc(d.etiqueta)}</div></div>`),
    pintar(el, d, t) {
      const m = momento(t, d.desde, d.hasta);
      if (!m) { el.style.opacity = 0; el.style.visibility = "hidden"; return; }
      el.style.visibility = "visible";
      el.style.opacity = (1 - m.s).toFixed(3);
      pintarMarca(el.querySelector(".marca"), m.a);
      const et = el.querySelector(".etiqueta");
      const e = resorte(m.a - 0.3, 2.0, 0.7);
      et.style.opacity = fuera((m.a - 0.3) / 0.2).toFixed(3);
      et.style.transform = `translateX(${(-24 * (1 - e)).toFixed(2)}px) scale(${(0.9 + 0.1 * e).toFixed(4)})`;
    },
  };

  TIPOS.error = {
    crear: (d) => nodo(`<div class="t t-error vidrio ${d.si ? "si" : "no"}">${marca(!!d.si)}
      <div><div class="mono">${esc(d.mono || (d.si ? "Correcto" : "Error común"))}</div><div class="titulo">${esc(d.titulo)}</div></div></div>`),
    pintar(el, d, t) {
      const m = momento(t, d.desde, d.hasta);
      poner(el, m);
      if (m) pintarMarca(el.querySelector(".marca"), m.a);
    },
  };

  TIPOS.seguridad = {
    crear: (d) => nodo(`<div class="t t-seguridad vidrio"><div class="escudo" style="color:#3b2a00">${icono("escudo", 60, 2.3)}</div>
      <div><div class="mono">Seguridad</div><div class="frase"></div></div></div>`),
    pintar(el, d, t) {
      const m = momento(t, d.desde, d.hasta);
      poner(el, m);
      if (!m) return;
      const f = d.frases.find((x) => t >= x.desde && t < x.hasta) || d.frases[d.frases.length - 1];
      const fr = el.querySelector(".frase");
      if (fr.textContent !== f.texto) fr.textContent = f.texto;
      fr.style.opacity = (fuera((t - f.desde) / 0.2) * (f.hasta - t < 0.12 ? limitar((f.hasta - t) / 0.12) : 1)).toFixed(3);
    },
  };

  TIPOS.cierre = {
    crear(d) {
      const el = nodo(`<div class="t t-cierre"><div class="grande">${esc(d.nombre)}</div>
        <div class="url vidrio">${esc(d.url)}</div>${d.grupo ? `<div class="grupo mono">${esc(d.grupo)}</div>` : ""}</div>`);
      return el;
    },
    pintar(el, d, t, opciones, escenario) {
      const m = momento(t, d.golpe, d.hasta, 0.3);
      if (!m) { el.style.opacity = 0; el.style.visibility = "hidden"; }
      else {
        el.style.visibility = "visible";
        el.style.opacity = (fuera(m.a / 0.08) * (1 - m.s)).toFixed(3);
        // El golpe: el nombre llega grande y se asienta de un rebote seco.
        const k = 1 + 0.32 * (1 - resorte(m.a, 3.2, 0.48));
        const y = escenario.classList.contains("vertical") ? 0 : -el.offsetHeight / 2;
        el.style.transform = `translateY(${y.toFixed(1)}px) scale(${k.toFixed(4)})`;
        const [url, grupo] = el.querySelectorAll(".url, .grupo");
        [url, grupo].forEach((x, i) => {
          if (!x) return;
          const e = resorte(m.a - 0.45 - 0.12 * i, 2.0, 0.7);
          x.style.opacity = fuera((m.a - 0.45 - 0.12 * i) / 0.2).toFixed(3);
          x.style.transform = `translateY(${(24 * (1 - e)).toFixed(2)}px)`;
        });
      }
      (el._finales || []).forEach((f) => { f.style.opacity = opciones.finales && t >= d.final && t <= d.hasta ? 1 : 0; });
    },
  };

  TIPOS.subtitulos = {
    crear: () => nodo(`<div class="t t-subtitulos"></div>`),
    pintar(el, d, t) {
      const ps = d.palabras;
      const k = ps.findIndex((p) => t >= p.desde && t < p.hasta);
      const vivo = t >= d.desde && t <= d.hasta && ps.length;
      if (!vivo) { el.style.visibility = "hidden"; return; }
      el.style.visibility = "visible";
      // La palabra de ahora o la última dicha; entre frases, después de 0,7 s, nada.
      const sig = ps.findIndex((p) => p.desde > t);
      const i = k >= 0 ? k : (sig < 0 ? ps.length : sig) - 1;
      if (i < 0 || (k < 0 && t - ps[i].hasta > 0.7)) { el.style.visibility = "hidden"; return; }
      // El trozo de la palabra (de a cuatro como mucho; cada frase empieza uno).
      const n = ps[i].trozo;
      const ini = ps.findIndex((p) => p.trozo === n);
      const clave = `${n}`;
      if (el._trozo !== clave) {
        el._trozo = clave;
        const trozo = ps.filter((p) => p.trozo === n);
        const mitad = trozo.length > 2 ? Math.ceil(trozo.length / 2) : trozo.length;
        const linea = (xs, base) => `<span class="linea">${xs.map((p, q) => `<span class="p" data-i="${base + q}">${esc(p.texto)}</span>`).join("")}</span>`;
        el.innerHTML = linea(trozo.slice(0, mitad), ini) + (trozo.length > mitad ? linea(trozo.slice(mitad), ini + mitad) : "");
        el._desde = trozo[0].desde;
      }
      el.querySelectorAll(".p").forEach((s) => {
        const q = +s.dataset.i;
        s.classList.toggle("ahora", q === k);
        const e = resorte(t - ps[q].desde + 0.05, 2.6, 0.6);
        const visto = t >= ps[q].desde - 0.05;
        s.style.opacity = visto ? 1 : 0.0;
        s.style.transform = `translateY(${(visto ? 14 * (1 - e) : 14).toFixed(2)}px) scale(${(q === k ? 1.04 : 1).toFixed(3)})`;
      });
    },
  };

  // ---------------------------------------------------------------- montar
  function montar(escenario, datos, opciones = {}) {
    opciones = Object.assign({ pasos: "sale", finales: true }, opciones);
    escenario.classList.add("escenario");
    escenario.classList.toggle("vertical", datos.formato === "vertical");
    escenario.innerHTML = '<div class="fondo"></div><div class="tinte"></div><div class="capa"></div>';
    if (datos.fondo) escenario.querySelector(".fondo").style.backgroundImage = `url(${datos.fondo})`;
    const capa = escenario.querySelector(".capa"), tinte = escenario.querySelector(".tinte");
    const piezas = [];
    const pasos = datos.tarjetas.filter((d) => d.tipo === "paso");
    const capitulos = datos.tarjetas.filter((d) => d.tipo === "capitulo");
    const total = pasos.length ? pasos[0].total : 0;
    if (pasos.length) piezas.push({ d: { pasos, total }, tipo: TIPOS.pasos });
    if (capitulos.length) piezas.push({ d: { lista: capitulos }, tipo: TIPOS.capitulo });
    for (const d of datos.tarjetas) {
      if (d.tipo === "paso" || d.tipo === "capitulo") continue;
      piezas.push({ d, tipo: TIPOS[d.tipo] });
    }
    for (const p of piezas) {
      p.el = p.tipo.crear(p.d);
      capa.appendChild(p.el);
      if (p.d.tipo === "cierre") {
        p.el._finales = (p.d.finales || []).map((f) => {
          const x = nodo(`<div class="final" style="left:${f.x}px; top:${f.y}px; width:${f.w}px; height:${f.h}px">${esc(f.texto)}</div>`);
          capa.appendChild(x);
          return x;
        });
      }
    }
    const errores = datos.tarjetas.filter((d) => d.tipo === "error" && !d.mono);
    const duracion = Math.max(0, ...datos.tarjetas.map((d) => d.hasta));
    return {
      duracion,
      opciones,
      pintar(t) {
        for (const p of piezas) p.tipo.pintar(p.el, p.d, t, opciones, escenario);
        // El tinte del cuadro: rojo con el error, verde con el correcto.
        const e = errores.find((d) => t >= d.desde && t <= d.hasta);
        if (e) {
          const m = momento(t, e.desde, e.hasta);
          tinte.className = `tinte ${e.si ? "si" : "no"}`;
          tinte.style.opacity = (m.o * (0.55 + 0.45 * Math.exp(-2.5 * m.a))).toFixed(3);
        } else tinte.style.opacity = 0;
      },
    };
  }

  window.Tarjetas = { montar, resorte };
})();
