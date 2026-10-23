#!/usr/bin/env python3
"""
refine.py: den grundliga utskriften efter en inspelning. Del av WDS (agents/wds/tools/meeting-live.md).

Liveutskriften gör avvägningar för att hinna med: liten modell, korta bitar, snabb sökning. Efteråt finns
tid. refine tar inspelningens ljud per kanal (them.wav, me.wav) och skriver ut det i ett svep med en
större modell och grundligare sökning, tar bort ekot (det mikrofonen hörde från högtalarna) och skriver
final.jsonl i samma format som liveutskriften, så att `live.py archive` tar den.

    python refine.py <inspelningens mapp> [--model KBLab/kb-whisper-medium] [--lang sv] [--device auto|gpu|cpu]

Kräver: faster-whisper. KB-Whisper medium laddas ned första gången (cirka 1,5 GB).
På processorn tar medium ungefär halva samtalets längd per kanal.

Grafikkortet (--device gpu, eller auto när ett finns): Intel-grafik via OpenVINO (paketen openvino-genai och,
en gång för konverteringen, optimum-intel[openvino]). Modellen konverteras första gången till
~/.venvs/models/<modell>-int8-ov (en befintlig <modell>-ov används först). faster-whisper hittar fortfarande var det finns tal (VAD), så att
tystnaden aldrig skrivs ut; talet skrivs ut på grafikkortet i bitar om högst 28 sekunder. Utan grafikkort,
eller om något går fel där, används processorn.
"""

import argparse
import difflib
import io
import json
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent))
from local import RATE, is_speech  # noqa: E402  samma filter mot påhittad text som live


def read_wav(path):
    import wave
    import numpy as np
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def sounding(x):
    """Sekunder med något ljud alls. Ifylld tystnad är exakt noll; en mikrofon brusar alltid lite."""
    secs = len(x) // RATE
    return int((x[:secs * RATE].reshape(secs, RATE) != 0).any(axis=1).sum()) if secs else 0


def clock(sec):
    s = int(sec)
    return f"{s // 60}:{s % 60:02d}"


def norm(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def echo(mine, theirs):
    """En replik från mikrofonen som nästan ordagrant är något som just kom från datorn är eko från högtalarna."""
    a = norm(mine["text"])
    for t in theirs:
        if abs(t["start"] - mine["start"]) <= 4 and difflib.SequenceMatcher(None, a, norm(t["text"])).ratio() >= 0.6:
            return True
    return False


def ov_model_dir(model):
    """Modellen i OpenVINO-format, i ~/.venvs/models där KB-Whisper small redan låg (2026-10-14).
    Finns <namn>-ov (fp16) används den, annars <namn>-int8-ov, som konverteras en gång med optimum-intel."""
    import subprocess
    root = Path.home() / ".venvs" / "models"
    name = model.split("/")[-1]
    for d in (root / f"{name}-ov", root / f"{name}-int8-ov"):
        if (d / "openvino_tokenizer.xml").exists():
            return d
    out = root / f"{name}-int8-ov"
    print(f"Konverterar {model} till OpenVINO (en gång, några minuter) …")
    subprocess.run([sys.executable, "-m", "optimum.commands.optimum_cli", "export", "openvino",
                    "--model", model, "--weight-format", "int8", str(out)], check=True)
    return out


def gpu_available():
    try:
        import openvino
        import openvino_genai  # noqa: F401
        return "GPU" in openvino.Core().available_devices
    except Exception:
        return False


def speech_chunks(x, max_len=28.0, gap=1.5):
    """Var det finns tal (faster-whispers VAD), sammanslaget till bitar om högst max_len sekunder."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    chunks = []
    for s in get_speech_timestamps(x, VadOptions()):
        if chunks and s["end"] - chunks[-1][0] <= max_len * RATE and s["start"] - chunks[-1][1] <= gap * RATE:
            chunks[-1][1] = s["end"]
        else:
            chunks.append([s["start"], s["end"]])
    return chunks


def transcribe_gpu(pipe, x, lang):
    """Talet skrivs ut bit för bit på grafikkortet. Ger (start, text) i sekunder från filens början."""
    from types import SimpleNamespace
    cfg = pipe.get_generation_config()
    cfg.task = "transcribe"
    cfg.return_timestamps = True
    if lang != "auto":
        cfg.language = f"<|{lang}|>"
    pad = int(0.2 * RATE)
    for a, b in speech_chunks(x):
        a0 = max(0, a - pad)
        res = pipe.generate(x[a0:b + pad].tolist(), cfg)
        parts = res.chunks or [SimpleNamespace(start_ts=0.0, text=res.texts[0])]
        for c in parts:
            seg = SimpleNamespace(text=c.text)
            if is_speech(seg):
                yield a0 / RATE + max(0.0, c.start_ts), c.text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--model", default="KBLab/kb-whisper-medium")
    ap.add_argument("--lang", default="sv", help="sv, en … eller auto")
    ap.add_argument("--device", default="auto", choices=["auto", "gpu", "cpu"],
                    help="auto: Intel-grafik via OpenVINO när den finns, annars processorn")
    ap.add_argument("--first", type=float, help="bara de första N sekunderna (för att mäta)")
    ap.add_argument("--out", default="final.jsonl", help="filnamn i mappen (standard final.jsonl)")
    a = ap.parse_args()
    folder = Path(a.dir)
    live = folder / "transcript.jsonl"
    head = {}
    if live.exists():
        head = next((json.loads(l) for l in live.read_text(encoding="utf-8").splitlines() if '"joined"' in l), {})
    channels = head.get("channels") or {"them": "De andra", "me": "Jag"}
    end = {}
    if live.exists():
        end = next((json.loads(l) for l in live.read_text(encoding="utf-8").splitlines() if '"ended"' in l), {})

    pipe, model, device = None, None, "cpu"
    if a.device == "gpu" or (a.device == "auto" and gpu_available()):
        try:
            import openvino_genai
            md = ov_model_dir(a.model)
            pipe = openvino_genai.WhisperPipeline(str(md), "GPU", CACHE_DIR=str(md / "cache"))  # kompilerade kärnor sparas, snabbare start
            device = "gpu"
        except Exception as e:
            print(f"Grafikkortet gick inte att använda ({e}); kör på processorn.")
    if pipe is None:
        from faster_whisper import WhisperModel
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
    print(f"Enhet: {'Intel-grafik (OpenVINO)' if device == 'gpu' else 'processorn (faster-whisper)'}")
    rows = {}
    for role in ("them", "me"):
        wav = folder / f"{role}.wav"
        if not wav.exists():
            continue
        x = read_wav(wav)
        if a.first:
            x = x[:int(a.first * RATE)]
        print(f"{wav.name}: {clock(len(x) / RATE)} lång, ljud i {clock(sounding(x))} av den (resten är tystnad som fyllts i)")
        t = time.time()
        speaker = channels.get(role, role)
        if pipe is not None:
            rows[role] = [{"start": round(st, 1), "speaker": speaker, "text": tx, "lang": a.lang}
                          for st, tx in transcribe_gpu(pipe, x, a.lang)]
        else:
            segs, info = model.transcribe(x, language=None if a.lang == "auto" else a.lang,
                                          vad_filter=True, beam_size=5, condition_on_previous_text=True)
            rows[role] = [{"start": round(s.start, 1), "speaker": speaker, "text": s.text.strip(), "lang": info.language}
                          for s in segs if is_speech(s)]
        took = time.time() - t
        print(f"{wav.name}: {len(rows[role])} repliker på {took:.0f} s ({len(x) / RATE / max(took, 1):.1f}x realtid)")

    theirs = rows.get("them", [])
    mine = [r for r in rows.get("me", []) if not echo(r, theirs)]
    removed = len(rows.get("me", [])) - len(mine)
    merged = sorted(theirs + mine, key=lambda r: r["start"])
    out = folder / a.out
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"event": "joined", "title": f"Grundlig utskrift ({a.model}, {device})", "participants": list(channels.values()),
                             "at": head.get("at", "")}, ensure_ascii=False) + "\n")
        for i, r in enumerate(merged, 1):
            fh.write(json.dumps({"n": i, **r}, ensure_ascii=False) + "\n")
        # Sluttid och längd från inspelningen, så att archive får rätt tid och längd.
        fh.write(json.dumps({"event": "ended", "reason": "grundlig utskrift",
                             **{k: end[k] for k in ("at", "duration") if k in end}}) + "\n")
    print(f"{out}: {len(merged)} repliker, {removed} eko borttagna")


if __name__ == "__main__":
    main()
