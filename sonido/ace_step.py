"""ACE-Step 1.5 (T23b, la candidata B de la música), en su propio entorno:
`python -I sonido/ace_step.py <trabajo.json>`, desde la carpeta del repositorio de ACE-Step.

Lo llama nudos/musica.py por medio de nudos/ia.py; no importa nada del proyecto. Cada tarea pide
una pieza instrumental (descripción, pulso, tono, compás, duración y semilla) y deja su WAV en
`salida` y, al lado, un JSON con los pulsos y los comienzos de compás que mide librosa: el pulso
con `beat_track`, y el compás por la fase de cuatro pulsos con más energía grave al empezar.

Los dos modelos (el DiT turbo y el LM de 1.7B, con el backend de PyTorch) se cargan una vez, con
lo que no se usa descargado a la CPU, para que quepan en 12 GB.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf


def compases(y: np.ndarray, sr: int, bpm: float) -> tuple[float, list[float], list[float]]:
    import librosa
    tempo, pulsos = librosa.beat.beat_track(y=y, sr=sr, start_bpm=bpm, tightness=400, units="time")
    pulsos = np.asarray(pulsos, float)
    tempo = float(np.atleast_1d(tempo)[0])
    # Una pieza a medio tiempo da la mitad del pulso pedido (o el doble): se corrige al pedido.
    if len(pulsos) > 2 and tempo < 0.75 * bpm:
        medios = (pulsos[:-1] + pulsos[1:]) / 2
        pulsos = np.sort(np.concatenate([pulsos, medios]))
        tempo *= 2
    elif len(pulsos) > 2 and tempo > 1.5 * bpm:
        pulsos = pulsos[::2]
        tempo /= 2
    if len(pulsos) < 8:
        return tempo, pulsos.tolist(), pulsos[:1].tolist()
    grave = librosa.onset.onset_strength(y=y, sr=sr, fmax=250, n_mels=32)
    cuadros = librosa.time_to_frames(pulsos, sr=sr)
    cuadros = np.clip(cuadros, 0, len(grave) - 1)
    fase = int(np.argmax([grave[cuadros[p::4]].mean() for p in range(4)]))
    return tempo, pulsos.tolist(), pulsos[fase::4].tolist()


def analizar(t: dict) -> None:
    """Los pulsos y compases de una pieza ya generada, en el JSON de al lado."""
    x, sr = sf.read(t["salida"], dtype="float32", always_2d=True)
    bpm, pulsos, inicio_compases = compases(x.mean(axis=1), sr, float(t["bpm"]))
    info = {"sr": sr, "segundos": round(len(x) / sr, 3), "bpm_medido": round(bpm, 2), "pulsos": pulsos,
            "compases": inicio_compases, "medida": t.get("medida"),
            "pedido": {k: t[k] for k in ("caption", "bpm", "keyscale", "duration", "seed")}}
    Path(t["salida"]).with_suffix(".json").write_text(json.dumps(info), encoding="utf-8")
    print(f"· {Path(t['salida']).name}: {len(x) / sr:.0f} s, {bpm:.1f} pulsos por minuto, "
          f"{len(inicio_compases)} compases", flush=True)


def main(ruta: str) -> int:
    trabajo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    for t in [t for t in trabajo["tareas"] if Path(t["salida"]).exists()]:
        analizar(t)
    trabajo["tareas"] = [t for t in trabajo["tareas"] if not Path(t["salida"]).exists()]
    if not trabajo["tareas"]:
        Path(trabajo["resultado"]).write_text(json.dumps({"hechas": []}), encoding="utf-8")
        return 0
    repo = trabajo["repo"]
    sys.path.insert(0, repo)
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler
    t0 = time.time()
    dit = AceStepHandler()
    msg, ok = dit.initialize_service(project_root=repo, config_path="acestep-v15-turbo", device="cuda",
                                     offload_to_cpu=True)
    if not ok:
        raise RuntimeError(f"el DiT no cargó: {msg}")
    lm = LLMHandler()
    msg, ok = lm.initialize(checkpoint_dir=str(Path(repo) / "checkpoints"), lm_model_path="acestep-5Hz-lm-1.7B",
                            backend="pt", device="cuda", offload_to_cpu=True)
    if not ok:
        raise RuntimeError(f"el LM no cargó: {msg}")
    print(f"· ACE-Step cargado en {time.time() - t0:.0f} s", flush=True)
    hechas = []
    for i, t in enumerate(trabajo["tareas"], 1):
        t1 = time.time()
        params = GenerationParams(caption=t["caption"], lyrics="[Instrumental]", instrumental=True, bpm=int(t["bpm"]),
                                  keyscale=t["keyscale"], timesignature=str(t["timesignature"]),
                                  duration=float(t["duration"]), seed=int(t["seed"]), inference_steps=8, shift=3.0,
                                  infer_method="ode", thinking=True, vocal_language="unknown")
        config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[int(t["seed"])], audio_format="wav")
        with tempfile.TemporaryDirectory(prefix="ace-") as tmp:
            res = generate_music(dit, lm, params, config, save_dir=tmp)
        if not res.success or not res.audios:
            raise RuntimeError(f"ACE-Step falló: {res.error}")
        a = res.audios[0]
        x = np.asarray(a["tensor"], np.float32)
        x = x.T if x.ndim == 2 and x.shape[0] <= 2 else x
        sr = int(a.get("sample_rate", 48000))
        salida = Path(t["salida"])
        salida.parent.mkdir(parents=True, exist_ok=True)
        sf.write(salida, x, sr, subtype="FLOAT")
        print(f"· pieza {i}/{len(trabajo['tareas'])} generada en {time.time() - t1:.0f} s", flush=True)
        analizar(t)
        hechas.append(str(salida))
    Path(trabajo["resultado"]).write_text(json.dumps({"hechas": hechas}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
