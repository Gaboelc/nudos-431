/* El visor con material físico, luz de entorno y postprocesado (T24). Solo lo usa el visor
   (visor.js): las imágenes de impresión siguen con la escena de siempre, porque escena.js sin
   «fisico» no cambia en nada.

   - La trenza: MeshPhysicalMaterial con pelusa (sheen) y brillo de filamento (anisotropía a lo
     largo de cada hilo, con un mapa que dice la dirección del hilo en cada punto), y un relieve
     fino de fibras con el ruido simplex de lygia. El tramado de lygia quita las bandas del
     degradé.
   - La luz: un entorno para los reflejos (RoomEnvironment) y el tonemap AgX.
   - El postprocesado, solo con la cámara quieta y si el equipo aguanta: oclusión ambiental
     (GTAOPass), dibujando con MSAA ×4. Mientras la cámara se mueve se dibuja directo, sin
     postprocesado. Si un cuadro con postprocesado tarda más de LENTO ms, o el navegador no tiene
     WebGL 2, el visor se queda sin él. (El SMAA dejaba un filo claro en el borde de la cuerda y
     de los palos, porque el fondo del visor es transparente; el MSAA del cuadro ya suaviza los
     bordes.) */
import * as THREE from "./vendor/three/three.module.min.js";
import { RoomEnvironment } from "./vendor/three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "./vendor/three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "./vendor/three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "./vendor/three/addons/postprocessing/GTAOPass.js";
import { OutputPass } from "./vendor/three/addons/postprocessing/OutputPass.js";
import { glsl } from "./vendor/lygia/lygia.js";

const LENTO = 90;            // ms: más que esto en el primer cuadro con postprocesado y se apaga
const LADO_HILOS = 256;      // px del mapa de la dirección de los hilos (un mosaico de la trenza)

/* La dirección de los hilos para la anisotropía: en el mosaico de la trenza (el de
   texturasTrenza de escena.js), los hilos A suben con u y los B bajan. Rojo y verde son la
   dirección en el espacio tangente (de -1 a 1, guardada de 0 a 1) y azul, la fuerza: más en
   lo alto de cada hilo y nada en el surco. */
function texturaHilos() {
  const S = LADO_HILOS;
  const datos = new Uint8Array(S * S * 4);
  const a = [Math.SQRT1_2, -Math.SQRT1_2], b = [Math.SQRT1_2, Math.SQRT1_2];
  for (let py = 0; py < S; py++) {
    const v = (py + 0.5) / S;
    for (let px = 0; px < S; px++) {
      const u = (px + 0.5) / S;
      const pa = 8 * v + 8 * u, pb = 8 * v - 8 * u;
      const i = Math.floor(pa), j = Math.floor(pb);
      const m = (((i + j) % 4) + 4) % 4;
      const esA = m < 2;
      const ancho = esA ? pa - i : pb - j;
      const fuerza = Math.sqrt(Math.max(0, 1 - (2 * ancho - 1) ** 2));
      const d = esA ? a : b;
      const o = (py * S + px) * 4;
      datos[o] = Math.round(255 * (0.5 + 0.5 * d[0]));
      datos[o + 1] = Math.round(255 * (0.5 + 0.5 * d[1]));
      datos[o + 2] = Math.round(255 * fuerza);
      datos[o + 3] = 255;
    }
  }
  const t = new THREE.DataTexture(datos, S, S, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.magFilter = THREE.LinearFilter;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

/* AgX con un «look» de contraste y saturación, como el «AgX - Base Contrast» de Blender que se
   eligió en T20a: el AgX de three.js, solo, aplana el azul de la cuerda. Se cambia el código del
   tonemap una vez, al cargar este módulo, que solo carga el visor: el material de la trenza, el
   del anfitrión y el OutputPass lo usan igual. */
const LOOK = { potencia: 1.22, saturacion: 1.3 };
THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment
  .replace("vec3 AgXToneMapping( vec3 color ) {", `vec3 agxLook( vec3 v ) {
	float luma = dot( v, vec3( 0.2126, 0.7152, 0.0722 ) );
	v = pow( max( v, vec3( 0.0 ) ), vec3( ${LOOK.potencia.toFixed(3)} ) );
	return luma + ${LOOK.saturacion.toFixed(3)} * ( v - luma );
}
vec3 AgXToneMapping( vec3 color ) {`)
  .replace("color = agxDefaultContrastApprox( color );", `color = agxDefaultContrastApprox( color );
	color = agxLook( color );`);

const SNOISE = glsl("generative/snoise.glsl");
const TRAMADO = glsl("color/dither/interleavedGradientNoise.glsl");

export function crearFisico() {
  let renderer = null, escena = null, camara = null;
  let composer = null, calidad = true, medido = false, msPrimero = null;
  const hilos = texturaHilos();
  const tramado = { value: 1 };     // 1 al dibujar directo; 0 con el postprocesado, que va después del tonemap

  function preparar(r, s, c) {
    renderer = r; escena = s; camara = c;
    renderer.toneMapping = THREE.AgXToneMapping;
    renderer.toneMappingExposure = 0.85;
    const pmrem = new THREE.PMREMGenerator(renderer);
    escena.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;
    pmrem.dispose();
    calidad = renderer.capabilities.isWebGL2;
  }

  /* El material de la trenza: `t` son las texturas de texturasTrenza (color y relieve) y
     `cols`, los colores de esa cuerda (claro, medio, oscuro y trazador). */
  function materialCuerda(t, cols, { vertexColors = false } = {}) {
    const medio = new THREE.Color(...cols[1].map((x) => x / 255)).convertSRGBToLinear();
    const mapaHilos = hilos.clone();
    mapaHilos.needsUpdate = true;
    const m = new THREE.MeshPhysicalMaterial({
      map: t.map, bumpMap: t.bump, bumpScale: 2.2, roughness: 0.6, metalness: 0, vertexColors,
      sheen: 0.45, sheenRoughness: 0.5, sheenColor: medio,
      anisotropy: 0.55, anisotropyMap: mapaHilos,
      specularIntensity: 0.45, envMapIntensity: 0.35,
    });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uTramado = tramado;
      sh.fragmentShader = sh.fragmentShader
        .replace("#include <common>", `#include <common>\nuniform float uTramado;\n${SNOISE}\n${TRAMADO}`)
        // El relieve fino: las fibras de cada hilo, un ruido estirado a lo largo de la cuerda.
        .replace("#include <normal_fragment_maps>", `#include <normal_fragment_maps>
          #ifdef USE_MAP
            float fibra = snoise(vec2(vMapUv.x * 260.0, vMapUv.y * 70.0)) * 0.6
                        + snoise(vec2(vMapUv.x * 520.0, vMapUv.y * 150.0)) * 0.4;
            vec2 dFibra = vec2(dFdx(fibra), dFdy(fibra)) * 0.012;
            normal = perturbNormalArb(-vViewPosition, normal, dFibra, faceDirection);
          #endif`)
        .replace("#include <dithering_fragment>", `#include <dithering_fragment>
          if (uTramado > 0.5) gl_FragColor.rgb = ditherInterleavedGradientNoise(gl_FragColor.rgb);`);
    };
    m.customProgramCacheKey = () => "trenza-fisica";
    return m;
  }

  function armarComposer() {
    const tam = renderer.getDrawingBufferSize(new THREE.Vector2());
    const rt = new THREE.WebGLRenderTarget(tam.x, tam.y, { type: THREE.HalfFloatType, samples: 4 });
    composer = new EffectComposer(renderer, rt);
    composer.addPass(new RenderPass(escena, camara));
    const gtao = new GTAOPass(escena, camara, tam.x, tam.y);
    gtao.output = GTAOPass.OUTPUT.Default;
    gtao.blendIntensity = 0.85;
    gtao.updateGtaoMaterial({ radius: 0.7, distanceExponent: 1.5, thickness: 1.0, scale: 1.0, samples: 16,
      distanceFallOff: 1.0, screenSpaceRadius: false });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    composer.addPass(gtao);
    // El fondo del visor es transparente, así que el borde de la cuerda y de los palos tiene
    // píxeles a medias, con el color ya multiplicado por su alfa. El tonemap y el paso a sRGB
    // no son lineales: aplicados así, aclaran el borde (un filo blanco). Se divide por el alfa
    // antes y se vuelve a multiplicar después.
    const salida = new OutputPass();
    salida.material.fragmentShader = salida.material.fragmentShader
      .replace("gl_FragColor = texture2D( tDiffuse, vUv );",
        "gl_FragColor = texture2D( tDiffuse, vUv );\n\t\t\tfloat alfa = gl_FragColor.a;\n\t\t\tif ( alfa > 0.0 ) gl_FragColor.rgb /= alfa;")
      .replace(/}\s*$/, "\tgl_FragColor.rgb *= alfa;\n\t\t}");
    composer.addPass(salida);
  }

  /* Dibuja un cuadro: con la cámara quieta y si el equipo aguanta, con el postprocesado. */
  function renderizar(quieto) {
    if (!(quieto && calidad)) {
      tramado.value = 1;
      renderer.render(escena, camara);
      return;
    }
    if (!composer) armarComposer();
    tramado.value = 0;
    composer.render();
    if (!medido) {
      // La primera vez, el cuadro compila los programas del postprocesado: se mide el segundo.
      // Leer un píxel obliga a esperar hasta que la tarjeta termina (gl.finish no espera).
      const gl = renderer.getContext();
      const pixel = new Uint8Array(4);
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
      const t0 = performance.now();
      composer.render();
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
      medido = true;
      msPrimero = performance.now() - t0;
      if (msPrimero > LENTO) {
        calidad = false;
        tramado.value = 1;
        renderer.render(escena, camara);
      }
    }
  }

  function redimensionar() {
    if (!composer) return;
    const tam = renderer.getDrawingBufferSize(new THREE.Vector2());
    composer.setPixelRatio(1);
    composer.setSize(tam.x, tam.y);
  }

  return {
    preparar, materialCuerda, renderizar, redimensionar,
    // Las luces de escena.js, con el entorno: menos cielo, que ya lo da el entorno.
    luz: { cielo: 0.9, sol: 2.4, relleno: 0.5 },
    get conPostprocesado() { return calidad; },
    get msPrimerCuadro() { return msPrimero; },     // lo que tarda un cuadro con postprocesado (medido una vez)
  };
}
