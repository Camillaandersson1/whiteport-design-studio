#!/usr/bin/env python3
"""
local.py: det som hörs på datorn, utskrivet lokalt med Whisper medan det pågår. Del av WDS
(agents/wds/tools/meeting-live.md). Ljudet lämnar aldrig datorn.

Lyssnar på datorns ljud ut (loopback, det du hör) och mikrofonen (du). Ingen bot går med i mötet,
så det fungerar oavsett vem som bjudit in och på vilken plattform. Med --no-mic bara datorns ljud,
för videor, webbinarier och poddar.

Ljudet klipps vid naturliga pauser, när någon har pratat klart, och skrivs ut direkt. Fördröjningen
blir ungefär yttrandets längd plus en sekund. Ett långt yttrande klipps senast efter --max sekunder.
Raderna hamnar i samma jsonl-format som live.py, så `live.py watch` och `live.py archive` fungerar.

    python local.py <utfil.jsonl> [--them "De andra"] [--me "Mårten Angner"] [--lang sv | auto]
    python local.py <utfil.jsonl> --no-mic --them "Videon"   # bara datorns ljud

Windows (WASAPI loopback). Kräver: python -m pip install pyaudiowpatch faster-whisper numpy
Svenska använder KB-Whisper (KBLab/kb-whisper-small), som laddas ned första gången.
Först använd i welqora-analysis 2026-10-14, när Fireflies transkriberade ett svenskt möte på engelska.
"""

import argparse
import datetime
import io
import json
import re
import sys
import threading
import time

import numpy as np

RATE = 16000


def to16k(rate, x):
    if rate == RATE or len(x) == 0:
        return x.astype(np.float32)
    m = int(len(x) * RATE / rate)
    return np.interp(np.linspace(0, len(x) - 1, m), np.arange(len(x)), x).astype(np.float32)


def is_speech(seg, no_speech=0.6, logprob=-1.0):
    """Whisper hittar ibland på text i brus och korta ljud. Släpp bara igenom det modellen själv tror är tal.

    Bort: tomma rader och skiljetecken ("."), Whispers interna märken ("<|nospeech|>"), rader utan
    bokstäver ("000"), och det modellen bedömer som troligen inte tal eller som osäkra ord."""
    text = seg.text.strip()
    if not text or "<|" in text or not re.search(r"[^\W\d_]", text):
        return False
    if getattr(seg, "no_speech_prob", 0) > no_speech:
        return False
    return getattr(seg, "avg_logprob", 0) > logprob


class Segmenter:
    """Samlar ljud från en källa och lämnar ifrån sig ett yttrande när talaren pausar.

    feed(x, now) tar emot nya sampel (16 kHz) och ger tillbaka färdiga yttranden som (starttid, ljud).
    now är sekunder sedan starten enligt klockan när x kom in. Starttiden räknas bakåt från den, eftersom
    Windows inte levererar något från högtalarutgången när inget spelas och ljudet därför inte är en klocka.
    I ett test med en inspelning är now inspelningens egen tid."""

    FRAME = 0.1  # sekunder per analysruta

    def __init__(self, threshold=0.006, pause=0.5, max_len=8.0, min_len=0.6):
        self.threshold, self.pause, self.max_len, self.min_len = threshold, pause, max_len, min_len
        self.buf = np.zeros(0, dtype=np.float32)
        self.speech = False    # har bufferten tal
        self.silence = 0.0     # sekunder tystnad sedan senaste tal
        self.pending = np.zeros(0, dtype=np.float32)

    def feed(self, x, now):
        out = []
        backlog = len(self.pending) + len(x)  # sampel som ännu inte analyserats när x kom in
        self.pending = np.concatenate([self.pending, x])
        step = int(self.FRAME * RATE)
        while len(self.pending) >= step:
            frame, self.pending = self.pending[:step], self.pending[step:]
            self.buf = np.concatenate([self.buf, frame])
            backlog -= step
            if np.sqrt(np.mean(frame ** 2)) > self.threshold:
                self.speech, self.silence = True, 0.0
            else:
                self.silence += self.FRAME
            dur = len(self.buf) / RATE
            if self.speech and (self.silence >= self.pause or dur >= self.max_len):
                if dur - self.silence >= self.min_len:
                    out.append((now - (len(self.buf) + max(backlog, 0)) / RATE, self.buf))
                self._reset()
            elif not self.speech and dur > 1.0:
                # Bara tystnad: behåll de sista 0,3 sekunderna, så att början på nästa ord kommer med.
                keep = int(0.3 * RATE)
                self.buf = self.buf[-keep:]
        return out

    def flush(self, now):
        out = []
        dur = len(self.buf) / RATE
        if self.speech and dur >= self.min_len:
            out.append((now - dur, self.buf))
        self._reset()
        return out

    def _reset(self):
        self.buf = np.zeros(0, dtype=np.float32)
        self.speech, self.silence = False, 0.0


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--them", default="De andra")
    ap.add_argument("--me", default="Jag")
    ap.add_argument("--lang", default="sv", help="sv, en … eller auto: språket upptäcks för varje yttrande")
    ap.add_argument("--no-mic", action="store_true", help="bara datorns ljud, till exempel en video eller ett webbinarium")
    ap.add_argument("--pause", type=float, default=0.5, help="sekunder tystnad som avslutar ett yttrande")
    ap.add_argument("--max", type=float, default=8.0, help="längsta yttrande innan det klipps")
    ap.add_argument("--threshold", type=float, default=0.006, help="ljudnivå som räknas som tal")
    ap.add_argument("--model", default=None, help="standard: KBLab/kb-whisper-small för svenska, annars small")
    a = ap.parse_args()

    try:
        import pyaudiowpatch as pyaudio
        from faster_whisper import WhisperModel
    except ImportError:
        print("Paket saknas: python -m pip install pyaudiowpatch faster-whisper numpy")
        sys.exit(1)

    model_name = a.model or ("KBLab/kb-whisper-small" if a.lang == "sv" else "small")
    pa = pyaudio.PyAudio()
    sources = [(a.them, pa.get_default_wasapi_loopback())] + ([] if a.no_mic else [(a.me, pa.get_default_input_device_info())])
    incoming = {name: [] for name, _ in sources}
    segmenters = {name: Segmenter(a.threshold, a.pause, a.max) for name, _ in sources}
    lock = threading.Lock()
    streams = []
    for name, dev in sources:
        rate, ch = int(dev["defaultSampleRate"]), max(1, min(2, dev["maxInputChannels"]))

        def cb(data, frames, info, status, name=name, ch=ch, rate=rate):
            x = np.frombuffer(data, dtype=np.int16).reshape(-1, ch).mean(axis=1) / 32768.0
            with lock:
                incoming[name].append(to16k(rate, x))
            return (None, pyaudio.paContinue)

        streams.append(pa.open(format=pyaudio.paInt16, channels=ch, rate=rate, input=True,
                               input_device_index=dev["index"], frames_per_buffer=1024, stream_callback=cb))
        print(f"Lyssnar: {name} <- {dev['name']} ({rate} Hz)")

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    n, t0 = 0, time.time()

    def write(row):
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    write({"event": "joined", "title": f"Lokal utskrift ({model_name})", "participants": [s for s, _ in sources],
           "at": datetime.datetime.now().isoformat(timespec="seconds")})
    print(f"Fil: {a.out}. Skriver ut när talaren pausar. Ctrl+C avslutar.")

    def transcribe(name, segments):
        nonlocal n
        for start, audio in segments:
            segs, info = model.transcribe(audio, language=None if a.lang == "auto" else a.lang, vad_filter=True, beam_size=1)
            text = " ".join(s.text.strip() for s in segs if is_speech(s))
            if text:
                n += 1
                write({"n": n, "start": round(start, 1), "speaker": name, "text": text, "lang": info.language})

    try:
        while True:
            time.sleep(0.2)
            with lock:
                taken = {k: v for k, v in incoming.items()}
                for k in incoming:
                    incoming[k] = []
            for name, parts in taken.items():
                if parts:
                    transcribe(name, segmenters[name].feed(np.concatenate(parts), time.time() - t0))
    except KeyboardInterrupt:
        pass
    finally:
        for s in streams:
            s.stop_stream()
            s.close()
        pa.terminate()
        for name, seg in segmenters.items():
            transcribe(name, seg.flush(time.time() - t0))
        write({"event": "ended", "reason": "stoppad", "at": datetime.datetime.now().isoformat(timespec="seconds")})


if __name__ == "__main__":
    main()
