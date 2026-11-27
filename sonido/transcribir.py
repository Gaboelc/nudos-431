"""El reconocimiento de voz (T23), en el entorno del alineador: `python -I sonido/transcribir.py <trabajo.json>`.

Qwen3-ASR-1.7B (Apache-2.0) escribe lo que dice una grabación. Sirve para las grabaciones de
Gabriel: para clonar su voz hace falta el texto exacto de la muestra, y los subtítulos piden el
tiempo de cada palabra, que después da el alineador (sonido/alinear.py) con este texto. Van por
separado para que cada modelo quepa en la tarjeta junto a un render de Blender. Lo llama
nudos/voz.py por medio de nudos/ia.py; no importa nada del proyecto.

Cada tarea trae `audio` (la ruta de un WAV), `idioma` y `contexto`: palabras que el modelo debería
reconocer, como los nombres de los nudos. Devuelve el texto de cada una. Las líneas que empiezan
con «·» son el avance que muestra la orden.
"""
import json
import sys
import time
from pathlib import Path

import torch

MODELO = "Qwen/Qwen3-ASR-1.7B"
REVISION = "7278e1e70fe206f11671096ffdd38061171dd6e5"      # la que se bajó el 26 nov


def cargar():
    from huggingface_hub import snapshot_download
    from qwen_asr import Qwen3ASRModel
    # Desde la carpeta local, como en alinear.py: aquí no hay red (HF_HUB_OFFLINE=1).
    local = snapshot_download(MODELO, revision=REVISION, local_files_only=True)
    dispositivo = "cuda:0" if torch.cuda.is_available() else "cpu"
    return Qwen3ASRModel.from_pretrained(local, dtype=torch.bfloat16, device_map=dispositivo,
                                         max_new_tokens=1024, max_inference_batch_size=1)


def main(ruta: str) -> int:
    trabajo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    tareas = trabajo["tareas"]
    t0 = time.time()
    modelo = cargar()
    print(f"· {MODELO} cargado en {time.time() - t0:.0f} s", flush=True)
    hechas = []
    for i, t in enumerate(tareas, 1):
        t1 = time.time()
        res = modelo.transcribe(audio=t["audio"], context=t.get("contexto", ""),
                                language=t.get("idioma", "Spanish"))[0]
        hechas.append({"texto": res.text, "idioma": res.language})
        print(f"· transcrita {i} de {len(tareas)}: {len(res.text.split())} palabras en {time.time() - t1:.0f} s",
              flush=True)
    Path(trabajo["resultado"]).write_text(json.dumps({"hechas": hechas}, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
