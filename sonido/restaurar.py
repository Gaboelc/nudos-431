"""La restauración de voz (T23), en el entorno del alineador: `python -I sonido/restaurar.py <trabajo.json>`.

Sidon v0.1 (sarulab-speech, MIT) vuelve una grabación casera, con el eco del cuarto, el ruido y el
sonido del celular, una voz como de estudio a 48 kHz: un w2v-BERT 2.0 afinado limpia los rasgos
de la voz y un vocoder la vuelve a dibujar. Sirve para la muestra de la voz de Gabriel, que el clon
copia tal como suena. Lo llama nudos/voz.py por medio de nudos/ia.py; no importa nada del proyecto.
La inferencia sigue la demo oficial (el Space sarulab-speech/sidon_demo_beta).

Cada tarea trae `audio` (la ruta de un WAV) y `salida`, donde deja la voz restaurada (float32,
mono, a 48 kHz, del mismo largo). Las líneas que empiezan con «·» son el avance que muestra la orden.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio

MODELO = "sarulab-speech/sidon-v0.1"
REVISION = "b3b02d8bbd55fdbc410e6e46e76ef95ace4fbf52"      # la que se bajó el 26 nov
PREPROCESADOR = "facebook/w2v-bert-2.0"
REVISION_PREPROCESADOR = "da985ba0987f70aaeb84a80f2851cfac8c697a7b"
SR = 48000
TROZO = 16000 * 96          # muestras a 16 kHz por pasada, como en la demo


def cargar():
    import transformers
    from huggingface_hub import snapshot_download
    # Desde las carpetas locales: aquí no hay red (HF_HUB_OFFLINE=1).
    local = Path(snapshot_download(MODELO, revision=REVISION, local_files_only=True))
    pre = snapshot_download(PREPROCESADOR, revision=REVISION_PREPROCESADOR, local_files_only=True)
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    sufijo = "cuda" if dispositivo == "cuda" else "cpu"
    fe = torch.jit.load(str(local / f"feature_extractor_{sufijo}.pt"), map_location=dispositivo).to(dispositivo)
    decoder = torch.jit.load(str(local / f"decoder_{sufijo}.pt"), map_location=dispositivo).to(dispositivo)
    preprocesador = transformers.SeamlessM4TFeatureExtractor.from_pretrained(pre)
    return fe, decoder, preprocesador, dispositivo


@torch.inference_mode()
def restaurar(x: np.ndarray, sr: int, fe, decoder, preprocesador, dispositivo) -> np.ndarray:
    pico = float(np.abs(x).max()) or 1.0
    n = int(round(SR / sr * len(x)))
    wav = torch.tensor(0.9 * x / pico, dtype=torch.float32).view(1, -1)
    wav = torchaudio.functional.highpass_biquad(wav, sr, 50)
    wav16 = torchaudio.functional.resample(wav, sr, 16000)
    wav16 = torch.nn.functional.pad(wav16, (0, 24000))
    partes, cache = [], None
    for trozo in wav16.view(-1).split(TROZO):
        entrada = preprocesador(torch.nn.functional.pad(trozo, (160, 160)).numpy(), sampling_rate=16000,
                                return_tensors="pt")
        rasgos = fe(entrada["input_features"].to(dispositivo))["last_hidden_state"]
        if cache is not None:
            rasgos = torch.cat([cache, rasgos], dim=1)
        partes.append(decoder(rasgos.transpose(1, 2)).view(-1)[:-960])
        cache = rasgos[:, -1:]
    y = torch.cat(partes).cpu().numpy()[:n]
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    return (y * pico / 0.9).astype(np.float32)


def main(ruta: str) -> int:
    trabajo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    tareas = trabajo["tareas"]
    t0 = time.time()
    modelos = cargar()
    print(f"· {MODELO} cargado en {time.time() - t0:.0f} s", flush=True)
    for i, t in enumerate(tareas, 1):
        t1 = time.time()
        x, sr = sf.read(t["audio"], dtype="float32", always_2d=True)
        y = restaurar(x.mean(axis=1), sr, *modelos)
        Path(t["salida"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(t["salida"], y, SR, subtype="FLOAT")
        print(f"· restaurada {i} de {len(tareas)}: {len(y) / SR:.1f} s en {time.time() - t1:.1f} s", flush=True)
    Path(trabajo["resultado"]).write_text(json.dumps({"hechas": len(tareas)}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
