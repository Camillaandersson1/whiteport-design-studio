#!/usr/bin/env python3
"""
local.py: ett pågående samtal utskrivet lokalt med Whisper, som reserv när Fireflies inte klarar
språket eller inte spelar in. Ljudet lämnar aldrig datorn. Del av WDS (agents/wds/tools/meeting-live.md).

Lyssnar på två källor samtidigt: datorns ljud ut (loopback, det du hör) och mikrofonen (du).
Ingen bot går med i mötet, så det fungerar oavsett vem som bjudit in och på vilken plattform.
Med --no-mic bara datorns ljud, för videor, webbinarier och poddar.
Var 15:e sekund skrivs det som sagts ut och läggs i en jsonl-fil i samma format som live.py,
så att `live.py watch <fil>` bevakar den och `live.py archive` tar med den.

    python local.py <utfil.jsonl> [--them "De andra"] [--me "Mårten Angner"] [--lang sv | auto] [--chunk 15]
    python local.py <utfil.jsonl> --no-mic --them "Videon"   # bara datorns ljud: video, webbinarium, podd

Windows (WASAPI loopback). Kräver: python -m pip install pyaudiowpatch faster-whisper numpy
Svenska använder KB-Whisper (KBLab/kb-whisper-small), som laddas ned första gången.
Först använd i welqora-analysis 2026-10-14, när Fireflies transkriberade ett svenskt möte på engelska.
"""

import argparse
import datetime
import io
import json
import sys
import threading
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--them", default="De andra")
ap.add_argument("--me", default="Jag")
ap.add_argument("--lang", default="sv", help="sv, en … eller auto: språket upptäcks för varje bit")
ap.add_argument("--chunk", type=float, default=15)
ap.add_argument("--no-mic", action="store_true", help="bara datorns ljud, till exempel en video eller ett webbinarium")
ap.add_argument("--model", default=None, help="standard: KBLab/kb-whisper-small för svenska, annars small")
a = ap.parse_args()

try:
    import numpy as np
    import pyaudiowpatch as pyaudio
    from faster_whisper import WhisperModel
except ImportError:
    print("Paket saknas: python -m pip install pyaudiowpatch faster-whisper numpy")
    sys.exit(1)

model_name = a.model or ("KBLab/kb-whisper-small" if a.lang == "sv" else "small")
pa = pyaudio.PyAudio()
sources = [(a.them, pa.get_default_wasapi_loopback())] + ([] if a.no_mic else [(a.me, pa.get_default_input_device_info())])
buffers = {name: [] for name, _ in sources}
lock = threading.Lock()
streams = []
for name, dev in sources:
    rate, ch = int(dev["defaultSampleRate"]), max(1, min(2, dev["maxInputChannels"]))

    def cb(data, frames, info, status, name=name, ch=ch, rate=rate):
        x = np.frombuffer(data, dtype=np.int16).reshape(-1, ch).mean(axis=1) / 32768.0
        with lock:
            buffers[name].append((rate, x))
        return (None, pyaudio.paContinue)

    streams.append(pa.open(format=pyaudio.paInt16, channels=ch, rate=rate, input=True,
                           input_device_index=dev["index"], frames_per_buffer=1024, stream_callback=cb))
    print(f"Lyssnar: {name} <- {dev['name']} ({rate} Hz)")

model = WhisperModel(model_name, device="cpu", compute_type="int8")
t0, n = time.time(), 0
with open(a.out, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"event": "joined", "title": f"Lokal utskrift ({model_name})", "participants": [n for n, _ in sources],
                         "at": datetime.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
print(f"Fil: {a.out}. Skriver ut var {a.chunk:.0f}:e sekund. Ctrl+C avslutar.")


def to16k(parts):
    if not parts:
        return np.zeros(0, dtype=np.float32)
    rate = parts[0][0]
    x = np.concatenate([p[1] for p in parts])
    m = int(len(x) * 16000 / rate)
    return np.interp(np.linspace(0, len(x) - 1, m), np.arange(len(x)), x).astype(np.float32)


try:
    while True:
        time.sleep(a.chunk)
        start = time.time() - t0 - a.chunk
        with lock:
            taken = dict(buffers)
            for k in buffers:
                buffers[k] = []
        rows = []
        for name, parts in taken.items():
            audio = to16k(parts)
            if len(audio) == 0 or np.sqrt(np.mean(audio ** 2)) < 0.003:  # tystnad
                continue
            # auto: språket upptäcks för varje bit, för möten som byter språk.
            segs, info = model.transcribe(audio, language=None if a.lang == "auto" else a.lang, vad_filter=True, beam_size=1)
            rows += [(start + s.start, name, s.text.strip(), info.language) for s in segs if s.text.strip()]
        rows.sort()
        with open(a.out, "a", encoding="utf-8") as fh:
            for st, name, text, lang in rows:
                n += 1
                fh.write(json.dumps({"n": n, "start": round(st, 1), "speaker": name, "text": text, "lang": lang},
                                    ensure_ascii=False) + "\n")
except KeyboardInterrupt:
    pass
finally:
    for s in streams:
        s.stop_stream()
        s.close()
    pa.terminate()
    with open(a.out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "ended", "reason": "stoppad", "at": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
