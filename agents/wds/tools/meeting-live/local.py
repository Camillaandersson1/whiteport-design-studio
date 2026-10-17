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

    python local.py --dir <mapp> [--screen] [--them "De andra"] [--me "Mårten Angner"]   # en inspelning, allt i mappen
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


class AudioFile:
    """Ljudet från en källa som WAV (16 kHz, mono). Tystnad fylls i efter klockan, eftersom Windows inte
    levererar något från högtalarutgången när inget spelas; då har ljud, utskrift och skärm samma tid."""

    def __init__(self, path):
        import wave
        self.w = wave.open(str(path), "wb")
        self.w.setnchannels(1)
        self.w.setsampwidth(2)
        self.w.setframerate(RATE)
        self.written = 0

    def add(self, x, now):
        gap = int(now * RATE) - len(x) - self.written
        if gap > RATE // 5:  # mer än 0,2 s som saknas: fyll med tystnad
            self.w.writeframes(np.zeros(gap, dtype=np.int16).tobytes())
            self.written += gap
        self.w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        self.written += len(x)

    def close(self, now):
        rest = int(now * RATE) - self.written  # tystnad fram till stoppet, så att filen är lika lång som inspelningen
        if rest > 0:
            self.w.writeframes(np.zeros(rest, dtype=np.int16).tobytes())
        self.w.close()


def frames_loop(folder, write, t0, stop, every=5.0, change=4.0):
    """En bild av skärmen när den har ändrats, kontrollerat var femte sekund. Raden i utskriften pekar på bilden."""
    from PIL import Image, ImageGrab
    folder.mkdir(exist_ok=True)
    last = None
    while not stop.wait(every):
        try:
            img = ImageGrab.grab()
        except Exception:
            continue
        small = np.asarray(img.convert("L").resize((96, 54)), dtype=np.float32)
        if last is None or np.mean(np.abs(small - last)) > change:
            last = small
            now = time.time() - t0
            name = f"{int(now) // 60:02d}-{int(now) % 60:02d}.jpg"
            if img.width > 1600:
                img = img.resize((1600, round(img.height * 1600 / img.width)), Image.LANCZOS)
            img.convert("RGB").save(folder / name, quality=82)
            write({"event": "frame", "start": round(now, 1), "file": str(folder / name)})


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", help="utskriftens jsonl-fil; med --dir blir den <dir>/transcript.jsonl")
    ap.add_argument("--dir", help="inspelningens mapp: utskrift, ljud per kanal, skärmvideo och bilder")
    ap.add_argument("--screen", action="store_true", help="spela in skärmen som video och spara en bild när den ändras")
    ap.add_argument("--them", default="De andra")
    ap.add_argument("--me", default="Jag")
    ap.add_argument("--lang", default="sv", help="sv, en … eller auto: språket upptäcks för varje yttrande")
    ap.add_argument("--no-mic", action="store_true", help="bara datorns ljud, till exempel en video eller ett webbinarium")
    ap.add_argument("--pause", type=float, default=0.5, help="sekunder tystnad som avslutar ett yttrande")
    ap.add_argument("--max", type=float, default=8.0, help="längsta yttrande innan det klipps")
    ap.add_argument("--threshold", type=float, default=0.006, help="ljudnivå som räknas som tal")
    ap.add_argument("--model", default=None, help="standard: KBLab/kb-whisper-small för svenska, annars small")
    a = ap.parse_args()
    from pathlib import Path
    folder = Path(a.dir) if a.dir else None
    if folder:
        folder.mkdir(parents=True, exist_ok=True)
        a.out = str(folder / "transcript.jsonl")
    if not a.out:
        ap.error("ange en utfil eller --dir")

    try:
        import pyaudiowpatch as pyaudio
        from faster_whisper import WhisperModel
    except ImportError:
        print("Paket saknas: python -m pip install pyaudiowpatch faster-whisper numpy")
        sys.exit(1)

    model_name = a.model or ("KBLab/kb-whisper-small" if a.lang == "sv" else "small")
    pa = pyaudio.PyAudio()
    sources = [(a.them, "them", pa.get_default_wasapi_loopback())]
    if not a.no_mic:
        sources.append((a.me, "me", pa.get_default_input_device_info()))
    incoming = {name: [] for name, _, _ in sources}
    segmenters = {name: Segmenter(a.threshold, a.pause, a.max) for name, _, _ in sources}
    audio = {name: AudioFile(folder / f"{role}.wav") for name, role, _ in sources} if folder else {}
    lock = threading.Lock()
    streams = []
    for name, _, dev in sources:
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
    wlock = threading.Lock()

    def write(row):
        with wlock, open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    write({"event": "joined", "title": f"Lokal utskrift ({model_name})", "participants": [s for s, _, _ in sources],
           "channels": {role: name for name, role, _ in sources}, "at": datetime.datetime.now().isoformat(timespec="seconds")})

    # Datorn får inte somna medan inspelningen pågår, även om ingen rör den. Skärmen får släckas.
    keep_awake = None
    if sys.platform == "win32":
        import ctypes
        keep_awake = ctypes.windll.kernel32.SetThreadExecutionState
        keep_awake(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

    stop = threading.Event()
    screen = None
    if folder and a.screen:
        import subprocess
        screen = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "gdigrab", "-framerate", "5", "-i", "desktop",
                                   "-vf", "scale=-2:1080", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                                   "-pix_fmt", "yuv420p", str(folder / "screen.mp4")], stdin=subprocess.PIPE)
        threading.Thread(target=frames_loop, args=(folder / "frames", write, t0, stop), daemon=True).start()
        print("Skärmen spelas in: screen.mp4, och en bild i frames/ när skärmen ändras.")
    print(f"Fil: {a.out}. Skriver ut när talaren pausar. Stoppa med en fil som heter STOP i mappen, eller Ctrl+C.")

    def transcribe(name, segments):
        nonlocal n
        for start, x in segments:
            segs, info = model.transcribe(x, language=None if a.lang == "auto" else a.lang, vad_filter=True, beam_size=1)
            text = " ".join(s.text.strip() for s in segs if is_speech(s))
            if text:
                n += 1
                write({"n": n, "start": round(start, 1), "speaker": name, "text": text, "lang": info.language})

    stopfile = (folder / "STOP") if folder else None
    try:
        while not (stopfile and stopfile.exists()):
            time.sleep(0.2)
            with lock:
                taken = {k: v for k, v in incoming.items()}
                for k in incoming:
                    incoming[k] = []
            now = time.time() - t0
            for name, parts in taken.items():
                if parts:
                    x = np.concatenate(parts)
                    if name in audio:
                        audio[name].add(x, now)
                    transcribe(name, segmenters[name].feed(x, now))
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for s in streams:
            s.stop_stream()
            s.close()
        pa.terminate()
        for name, seg in segmenters.items():
            transcribe(name, seg.flush(time.time() - t0))
        for f in audio.values():
            f.close(time.time() - t0)
        if screen:
            try:
                screen.communicate(b"q", timeout=20)  # ffmpeg avslutar videon ordentligt
            except Exception:
                screen.kill()
        if stopfile and stopfile.exists():
            stopfile.unlink()
        if keep_awake:
            keep_awake(0x80000000)  # tillbaka till vanligt: datorn får somna igen
        write({"event": "ended", "reason": "stoppad", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        print("Inspelningen är stoppad.")


if __name__ == "__main__":
    main()
