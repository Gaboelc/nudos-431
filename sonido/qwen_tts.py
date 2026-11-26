"""Qwen3-TTS (T23a), en su propio entorno: `python -I sonido/qwen_tts.py <trabajo.json>`.

Lo llama nudos/voz.py por medio de nudos/ia.py; no importa nada del proyecto. El trabajo trae una
lista de tareas, que se hacen en orden:

- «disenar»: VoiceDesign crea una voz a partir de una descripción y dice `texto` con ella.
- «clonar»: Base dice `texto` con la voz de una muestra (`referencia`, con su `texto_referencia`).

Cada tarea escribe su WAV (float32, mono, a la frecuencia del modelo) en `salida`. Cada modelo se
carga una sola vez, y el de diseño se descarga antes de cargar el de clonar, para que los dos
quepan en 12 GB. Las líneas que empiezan con «·» son el avance que muestra la orden.
"""
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

MODELOS = {"disenar": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "clonar": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"}


def cargar(tipo: str):
    from huggingface_hub import snapshot_download
    from qwen_tts import Qwen3TTSModel
    # Desde la carpeta local: con el nombre del repositorio, transformers 4.57 consulta la red al
    # cargar el tokenizador, y aquí no hay red (HF_HUB_OFFLINE=1).
    local = snapshot_download(MODELOS[tipo], local_files_only=True)
    return Qwen3TTSModel.from_pretrained(local, device_map="cuda:0", dtype=torch.bfloat16,
                                         attn_implementation="sdpa")


def semilla(n: int) -> None:
    torch.manual_seed(n)
    torch.cuda.manual_seed_all(n)
    np.random.seed(n % (2 ** 32))


def main(ruta: str) -> int:
    trabajo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    tareas = trabajo["tareas"]
    hechas = []
    modelo, tipo_cargado = None, None
    prompts = {}
    for tipo in ("disenar", "clonar"):
        mias = [t for t in tareas if t["tipo"] == tipo]
        if not mias:
            continue
        if modelo is not None:
            del modelo
            gc.collect()
            torch.cuda.empty_cache()
        t0 = time.time()
        modelo = cargar(tipo)
        print(f"· {MODELOS[tipo]} cargado en {time.time() - t0:.0f} s", flush=True)
        for i, t in enumerate(mias, 1):
            t1 = time.time()
            semilla(int(t.get("semilla", 431)))
            ajustes = dict(t.get("ajustes", {}))
            if tipo == "disenar":
                wavs, sr = modelo.generate_voice_design(text=t["texto"], instruct=t["instruccion"],
                                                        language=t.get("idioma", "spanish"), **ajustes)
            else:
                clave = (t["referencia"], t["texto_referencia"])
                if clave not in prompts:
                    prompts[clave] = modelo.create_voice_clone_prompt(
                        ref_audio=t["referencia"], ref_text=t["texto_referencia"])
                wavs, sr = modelo.generate_voice_clone(text=t["texto"], language=t.get("idioma", "spanish"),
                                                       voice_clone_prompt=prompts[clave], **ajustes)
            x = np.asarray(wavs[0], np.float32).reshape(-1)
            Path(t["salida"]).parent.mkdir(parents=True, exist_ok=True)
            sf.write(t["salida"], x, sr, subtype="FLOAT")
            hechas.append({"salida": t["salida"], "sr": int(sr), "segundos": round(len(x) / sr, 3)})
            print(f"· {tipo} {i}/{len(mias)}: {len(x) / sr:.1f} s de voz en {time.time() - t1:.0f} s",
                  flush=True)
    Path(trabajo["resultado"]).write_text(json.dumps({"hechas": hechas}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
