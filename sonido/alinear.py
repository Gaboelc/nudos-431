"""El alineador forzado (T23a), en su propio entorno: `python -I sonido/alinear.py <trabajo.json>`.

Qwen3-ForcedAligner-0.6B (Apache-2.0) dice cuándo empieza y termina cada palabra de un texto que ya
se sabe, en un audio que lo dice. Lo llama nudos/voz.py por medio de nudos/ia.py; no importa nada del
proyecto. Cada tarea trae `audio` (la ruta de un WAV), `texto` (lo que dice, tal como se le pidió a
la voz) e `idioma`. El alineador parte el texto por los espacios y deja de cada trozo solo las letras,
los números y los apóstrofos; por cada trozo que queda devuelve su inicio y su fin en segundos.
Las líneas que empiezan con «·» son el avance que muestra la orden.
"""
import json
import sys
import time
from pathlib import Path

import torch

MODELO = "Qwen/Qwen3-ForcedAligner-0.6B"
REVISION = "c7cbfc2048c462b0d63a45797104fc9db3ad62b7"     # la que se bajó el 26 nov


def cargar():
    from huggingface_hub import snapshot_download
    from qwen_asr import Qwen3ForcedAligner
    # Desde la carpeta local, como en qwen_tts.py: aquí no hay red (HF_HUB_OFFLINE=1).
    local = snapshot_download(MODELO, revision=REVISION, local_files_only=True)
    dispositivo = "cuda:0" if torch.cuda.is_available() else "cpu"
    return Qwen3ForcedAligner.from_pretrained(local, device_map=dispositivo, dtype=torch.bfloat16)


def main(ruta: str) -> int:
    trabajo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    tareas = trabajo["tareas"]
    t0 = time.time()
    alineador = cargar()
    print(f"· {MODELO} cargado en {time.time() - t0:.0f} s", flush=True)
    alineadas = []
    for i, t in enumerate(tareas, 1):
        res = alineador.align(audio=t["audio"], text=t["texto"], language=t.get("idioma", "Spanish"))[0]
        alineadas.append([{"texto": it.text, "inicio": float(it.start_time), "fin": float(it.end_time)}
                          for it in res])
        if i % 10 == 0 or i == len(tareas):
            print(f"· alineadas {i} de {len(tareas)}", flush=True)
    Path(trabajo["resultado"]).write_text(json.dumps({"alineadas": alineadas}, ensure_ascii=False),
                                          encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
