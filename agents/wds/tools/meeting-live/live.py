#!/usr/bin/env python3
"""
live.py: ett Fireflies-möte live till en lokal fil. Del av WDS (agents/wds/tools/meeting-live.md).

Ingen server, ingen MCP. Fireflies realtid (socket.io) skrivs rad för rad till en jsonl-fil,
och agenten bevakar filen med watch.

    python live.py list                          # pågående möten
    python live.py join [--number 1 | --id ID]   # strömma till .wds/live/<tid>-<titel>.jsonl (körs i bakgrunden)
    python live.py watch <fil> [--every 30]      # skriv ut nya repliker i klumpar, slutar när mötet är slut
    python live.py transcript <fil>              # hela mötet som läsbar text

Nyckeln: miljövariabeln FIREFLIES_API_KEY, hämtad ur Bitwarden vid körning. Den skrivs aldrig till fil.
Kräver: pip install "python-socketio[client]"
"""

import io
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib import request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

GRAPHQL = "https://api.fireflies.ai/graphql"
REALTIME = "wss://api.fireflies.ai"
IDLE_FLUSH = 3.0      # sekunder utan uppdatering innan en replik räknas som klar
POLL_ACTIVE = 60      # hur ofta join kollar att mötet fortfarande pågår
FIRST_BATCH = 40      # watch visar högst så många rader första gången


def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def key():
    k = os.environ.get("FIREFLIES_API_KEY")
    if not k:
        print('FIREFLIES_API_KEY saknas. Hämta den ur Bitwarden: export FIREFLIES_API_KEY="$(bw get password \'Fireflies API Key\')"')
        sys.exit(1)
    return k


def graphql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = request.Request(GRAPHQL, data=body, headers={
        "Authorization": f"Bearer {key()}", "Content-Type": "application/json", "User-Agent": "wds-meeting-live"})
    with request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    if data.get("errors"):
        raise RuntimeError(f"Fireflies: {json.dumps(data['errors'], ensure_ascii=False)}")
    return data["data"]


def active_meetings():
    q = """query($states: [MeetingState!]) { active_meetings(input: { states: $states }) {
             id title organizer_email start_time state } }"""
    ms = graphql(q, {"states": ["active", "paused"]})["active_meetings"] or []
    return sorted(ms, key=lambda m: m.get("start_time") or "", reverse=True)


def transcript(meeting_id):
    q = """query($id: String!) { transcript(id: $id) { id title date participants
             sentences { speaker_name text start_time end_time } } }"""
    return graphql(q, {"id": meeting_id})["transcript"]


def clock(sec):
    try:
        s = int(float(sec))
    except (TypeError, ValueError):
        return "--:--"
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def slug(text):
    t = text.lower().translate(str.maketrans("åäö", "aao"))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50] or "mote"


# ── list ────────────────────────────────────────────────────────────────

def cmd_list():
    ms = active_meetings()
    if not ms:
        print("Inga pågående möten. Starta inspelningen i Fireflies och försök igen om 30 sekunder.")
    for i, m in enumerate(ms, 1):
        print(f"{i}. {m['title']} | {m['id']} | {m.get('start_time') or '?'} | {m.get('state') or 'active'}")


# ── join ────────────────────────────────────────────────────────────────

class Writer:
    def __init__(self, path):
        self.path, self.n, self.lock = path, 0, threading.Lock()

    def write(self, row):
        with self.lock:
            if "text" in row:
                self.n += 1
                row = {"n": self.n, **row}
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_join():
    try:
        import socketio
    except ImportError:
        print('Paketet saknas: python -m pip install "python-socketio[client]"')
        sys.exit(1)

    meeting_id = arg("--id")
    if not meeting_id:
        ms = active_meetings()
        pick = int(arg("--number", "1"))
        if len(ms) < pick:
            print("Inget pågående möte på den platsen. Starta inspelningen i Fireflies och försök igen om 30 sekunder.")
            sys.exit(1)
        meeting_id = ms[pick - 1]["id"]

    t = transcript(meeting_id)
    out = Path(arg("--out", ".wds/live"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now():%Y-%m-%d_%H-%M}-{slug(t['title'])}.jsonl"
    w = Writer(path)
    w.write({"event": "joined", "title": t["title"], "meeting_id": meeting_id,
             "participants": t.get("participants") or [], "at": datetime.now().isoformat(timespec="seconds")})
    for s in t.get("sentences") or []:
        w.write({"start": s.get("start_time"), "speaker": s.get("speaker_name"), "text": s.get("text"), "seed": True})
    print(f'Ansluten till "{t["title"]}"')
    print(f"Fil: {path.resolve()}")
    print(f"{w.n} tidigare repliker inskrivna. Strömmar live. Ctrl+C avslutar.")

    pending, plock, done = {}, threading.Lock(), threading.Event()

    def flush(older_than=None):
        now = time.time()
        with plock:
            ready = [cid for cid, (ev, ts) in pending.items() if older_than is None or now - ts >= older_than]
            for cid in ready:
                ev, _ = pending.pop(cid)
                w.write({"start": ev.get("start_time"), "speaker": ev.get("speaker_name"), "text": ev.get("text"), "id": cid})

    def finish(reason):
        if done.is_set():
            return
        flush()
        w.write({"event": "ended", "reason": reason, "at": datetime.now().isoformat(timespec="seconds")})
        print(f"Mötet är slut ({reason}). Fil: {path.resolve()}")
        done.set()

    sio = socketio.Client(reconnection=True, reconnection_attempts=0)

    @sio.on("auth.success")
    def _auth():
        print("Fireflies: inloggad.")

    @sio.on("connection.established")
    def _connected():
        w.write({"event": "connected", "at": datetime.now().isoformat(timespec="seconds")})
        print("Fireflies: realtid ansluten.")

    @sio.on("transcription.broadcast")
    def _segment(event):
        ev = event.get("payload", event) if isinstance(event, dict) else {}
        cid = str(ev.get("chunk_id") or ev.get("start_time"))
        # A new chunk means the earlier ones are finished. The same chunk can arrive several times as it grows.
        with plock:
            for c in [c for c in pending if c != cid]:
                e, _ = pending.pop(c)
                w.write({"start": e.get("start_time"), "speaker": e.get("speaker_name"), "text": e.get("text"), "id": c})
            pending[cid] = (ev, time.time())

    @sio.on("auth.failed")
    def _auth_failed(payload=None):
        w.write({"event": "error", "message": f"auth failed: {payload}"})
        finish("auth-failed")

    @sio.on("connection.error")
    def _conn_error(payload=None):
        w.write({"event": "error", "message": f"connection error: {payload}"})

    @sio.event
    def disconnect(*_):
        if not done.is_set():
            w.write({"event": "disconnected", "at": datetime.now().isoformat(timespec="seconds")})

    def idle_flusher():
        while not done.wait(1):
            flush(older_than=IDLE_FLUSH)

    def still_live():
        misses = 0
        while not done.wait(POLL_ACTIVE):
            try:
                ids = {m["id"] for m in active_meetings()}
                misses = 0 if meeting_id in ids else misses + 1
            except Exception as e:
                w.write({"event": "error", "message": f"active_meetings: {e}"})
            if misses >= 2:
                finish("mötet pågår inte längre i Fireflies")

    threading.Thread(target=idle_flusher, daemon=True).start()
    threading.Thread(target=still_live, daemon=True).start()

    try:
        sio.connect(REALTIME, socketio_path="/ws/realtime", transports=["websocket"],
                    auth={"token": f"Bearer {key()}", "transcriptId": meeting_id}, wait_timeout=20)
        while not done.wait(1):
            pass
    except KeyboardInterrupt:
        finish("avbrutet")
    except Exception as e:
        w.write({"event": "error", "message": str(e)})
        finish("fel vid anslutning")
        raise
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass


# ── watch ───────────────────────────────────────────────────────────────

def line_text(row):
    if "text" in row:
        return f"[{clock(row.get('start'))}] {row.get('speaker') or '?'}: {row['text']}"
    ev = row.get("event")
    if ev == "joined":
        return f"== Ansluten: {row.get('title')} =="
    if ev == "ended":
        return f"== MÖTET ÄR SLUT: {row.get('reason')} =="
    if ev == "error":
        return f"== FEL: {row.get('message')} =="
    return f"== {ev} =="


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def cmd_watch():
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if not path or not path.exists():
        print(f"== FEL: filen finns inte: {path} ==")
        sys.exit(1)
    every = float(arg("--every", "30"))
    seen_file = path.with_suffix(".seen")
    seen = int(seen_file.read_text()) if seen_file.exists() else 0
    while True:
        rows = read_rows(path)
        new = rows[seen:]
        if new:
            if seen == 0 and len(new) > FIRST_BATCH:
                print(f"({len(new) - FIRST_BATCH} tidigare rader finns i filen)\n" + "\n".join(map(line_text, new[-FIRST_BATCH:])))
            else:
                print("\n".join(map(line_text, new)))
            seen = len(rows)
            seen_file.write_text(str(seen))
            if any(r.get("event") == "ended" for r in new):
                return
        time.sleep(every)


# ── transcript ──────────────────────────────────────────────────────────

def cmd_transcript():
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if not path or not path.exists():
        print(f"Filen finns inte: {path}")
        sys.exit(1)
    print("\n".join(line_text(r) for r in read_rows(path)))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"list": cmd_list, "join": cmd_join, "watch": cmd_watch, "transcript": cmd_transcript}.get(cmd, lambda: print(__doc__))()
