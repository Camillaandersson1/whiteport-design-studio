#!/usr/bin/env python3
"""
refine.py: den grundliga utskriften efter en inspelning. Del av WDS (agents/wds/tools/meeting-live.md).

Liveutskriften gör avvägningar för att hinna med: liten modell, korta bitar, snabb sökning. Efteråt finns
tid. refine tar inspelningens ljud per kanal (them.wav, me.wav) och skriver ut det i ett svep med en
större modell och grundligare sökning, tar bort ekot (det mikrofonen hörde från högtalarna) och skriver
final.jsonl i samma format som liveutskriften, så att `live.py archive` tar den.

    python refine.py <inspelningens mapp> [--model KBLab/kb-whisper-medium] [--lang sv]

Kräver: faster-whisper. KB-Whisper medium laddas ned första gången (cirka 1,5 GB).
På en dator utan grafikkort-acceleration tar medium ungefär halva samtalets längd per kanal.
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
from local import is_speech  # noqa: E402  samma filter mot påhittad text som live


def norm(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def echo(mine, theirs):
    """En replik från mikrofonen som nästan ordagrant är något som just kom från datorn är eko från högtalarna."""
    a = norm(mine["text"])
    for t in theirs:
        if abs(t["start"] - mine["start"]) <= 4 and difflib.SequenceMatcher(None, a, norm(t["text"])).ratio() >= 0.6:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--model", default="KBLab/kb-whisper-medium")
    ap.add_argument("--lang", default="sv", help="sv, en … eller auto")
    a = ap.parse_args()
    folder = Path(a.dir)
    live = folder / "transcript.jsonl"
    head = {}
    if live.exists():
        head = next((json.loads(l) for l in live.read_text(encoding="utf-8").splitlines() if '"joined"' in l), {})
    channels = head.get("channels") or {"them": "De andra", "me": "Jag"}

    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    rows = {}
    for role in ("them", "me"):
        wav = folder / f"{role}.wav"
        if not wav.exists():
            continue
        t = time.time()
        segs, info = model.transcribe(str(wav), language=None if a.lang == "auto" else a.lang,
                                      vad_filter=True, beam_size=5, condition_on_previous_text=True)
        rows[role] = [{"start": round(s.start, 1), "speaker": channels.get(role, role), "text": s.text.strip(), "lang": info.language}
                      for s in segs if is_speech(s)]
        print(f"{wav.name}: {len(rows[role])} repliker på {time.time() - t:.0f} s")

    theirs = rows.get("them", [])
    mine = [r for r in rows.get("me", []) if not echo(r, theirs)]
    removed = len(rows.get("me", [])) - len(mine)
    merged = sorted(theirs + mine, key=lambda r: r["start"])
    out = folder / "final.jsonl"
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"event": "joined", "title": f"Grundlig utskrift ({a.model})", "participants": list(channels.values()),
                             "at": head.get("at", "")}, ensure_ascii=False) + "\n")
        for i, r in enumerate(merged, 1):
            fh.write(json.dumps({"n": i, **r}, ensure_ascii=False) + "\n")
        fh.write(json.dumps({"event": "ended", "reason": "grundlig utskrift"}) + "\n")
    print(f"{out}: {len(merged)} repliker, {removed} eko borttagna")


if __name__ == "__main__":
    main()
