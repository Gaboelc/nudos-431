"""Los programas que corren aparte (T23), como Blender: la voz (Qwen3-TTS) y la música generada
(ACE-Step 1.5) piden PyTorch con CUDA y Python 3.12, así que cada uno vive en su propio entorno,
fuera de A: y del venv del proyecto, y se llama con un script de `sonido/` y un archivo de trabajo
en JSON.

Dónde viven: `NUDOS_IA` o, por omisión, `D:\\nudos\\ia` (si existe D:) o `%LOCALAPPDATA%\\nudos\\ia`.

    <NUDOS_IA>/
      uv/uv.exe                     uv 0.13.10, que crea los entornos
      python/, uv-cache/            el Python 3.12 y los paquetes que bajó uv
      hf/                           los modelos de Hugging Face (HF_HOME)
      qwen-tts/.venv/               Qwen3-TTS: qwen-tts 0.1.1 con torch 2.7.1+cu128
      ace-step/ACE-Step-1.5/        ACE-Step 1.5 (commit ca1e85f), su .venv y checkpoints/
      musica/fluidsynth/            FluidSynth 2.6.3 para Windows x64
      musica/bancos/                GeneralUser GS 2.0 y las muestras del VCSL (CC0)

Cómo se instaló (26 nov, con permiso de Gabriel para cada descarga):

    uv venv --python 3.12 qwen-tts/.venv
    uv pip install --python qwen-tts/.venv/Scripts/python.exe torch==2.7.1 torchaudio==2.7.1 \\
        --index-url https://download.pytorch.org/whl/cu128
    uv pip install --python qwen-tts/.venv/Scripts/python.exe qwen-tts==0.1.1 (con torch fijo)
    huggingface_hub.snapshot_download("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign" y "...-Base")
    git clone https://github.com/ace-step/ACE-Step-1.5 ace-step/ACE-Step-1.5 && uv sync --python 3.12
    uv pip install librosa; python -m acestep.model_downloader

Al correr, nada se baja: `HF_HUB_OFFLINE=1`. Un modelo que falta es un error que dice qué bajar.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from . import RAIZ

SCRIPTS = RAIZ / "sonido"


class IAError(RuntimeError):
    """Un programa aparte falta o falló."""


def carpeta() -> Path:
    if os.environ.get("NUDOS_IA"):
        return Path(os.environ["NUDOS_IA"])
    if Path("D:/").exists():
        return Path("D:/nudos/ia")
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "nudos" / "ia"


ENTORNOS = {
    "qwen-tts": Path("qwen-tts") / ".venv" / "Scripts" / "python.exe",
    "ace-step": Path("ace-step") / "ACE-Step-1.5" / ".venv" / "Scripts" / "python.exe",
}


def python_de(entorno: str) -> Path:
    ruta = carpeta() / ENTORNOS[entorno]
    if not ruta.exists():
        raise IAError(f"no está el entorno «{entorno}» en {ruta}. Se instala como dice nudos/ia.py "
                      "(con permiso de Gabriel para cada descarga).")
    return ruta


def variables(entorno: str) -> dict:
    env = dict(os.environ)
    base = carpeta()
    env.update({"HF_HOME": str(base / "hf"), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                "TOKENIZERS_PARALLELISM": "false"})
    # El script no tiene que ver el venv del proyecto ni sus paquetes.
    for k in ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME"):
        env.pop(k, None)
    return env


def correr(entorno: str, script: str, trabajo: dict, aviso=print, cwd: Path | None = None,
           tiempo: float | None = None) -> dict:
    """Corre sonido/<script> con el Python del entorno y el trabajo en un JSON; devuelve el JSON
    que el script deja en trabajo["resultado"]. Lo que el script imprime pasa a `aviso`."""
    py = python_de(entorno)
    with tempfile.TemporaryDirectory(prefix="nudos-ia-") as tmp:
        ruta = Path(tmp) / "trabajo.json"
        res = Path(tmp) / "resultado.json"
        ruta.write_text(json.dumps({**trabajo, "resultado": str(res)}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        # -I aísla el script del venv del proyecto (e ignora las variables PYTHON*); -X utf8 hace
        # que su salida llegue en UTF-8 aunque -I no lea PYTHONIOENCODING.
        p = subprocess.Popen([str(py), "-I", "-X", "utf8", str(SCRIPTS / script), str(ruta)], env=variables(entorno),
                             cwd=str(cwd or Path(tmp)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        cola = []
        for linea in p.stdout:
            linea = linea.rstrip()
            cola = (cola + [linea])[-40:]
            if linea.startswith("·"):
                aviso("  " + linea[1:].strip())
        p.wait(timeout=tiempo)
        if p.returncode != 0 or not res.exists():
            raise IAError(f"sonido/{script} falló ({p.returncode}):\n  " + "\n  ".join(cola))
        return json.loads(res.read_text(encoding="utf-8"))
