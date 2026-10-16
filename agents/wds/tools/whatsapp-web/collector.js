// whatsapp-web collector: reads one WhatsApp Web chat in order. Read-only — sends and changes nothing.
// Run in the web.whatsapp.com tab (javascript_exec) with the chat open. See whatsapp-web.md for the steps:
// install (paste this file), await __wa.list('<contact name>'), await __wa.collect() until missing is 0,
// await __wa.voice() until voice equals of, await __wa.export('<prefix>') downloads two files.
// Each call stays under ~38 s so it fits the browser tool's timeout.
(() => {
  const open = n => new Promise((res, rej) => { const r = indexedDB.open(n); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const all = async (db, s) => new Promise(r => { const q = db.transaction(s).objectStore(s).getAll(); q.onsuccess = () => r(q.result); });
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const fmt = t => new Date(t * 1000).toLocaleString('sv-SE', { timeZone: 'Europe/Stockholm' }).slice(0, 16);
  const pane = () => { const main = document.querySelector('#main'); return [...main.querySelectorAll('div')].find(d => d.scrollHeight > d.clientHeight + 300 && getComputedStyle(d).overflowY.match(/auto|scroll/)); };
  const W = window.__wa = window.__wa || { got: {}, blobs: [], plays: [], map: {} };

  if (!W.hooked) {
    W.hooked = true;
    const cou = URL.createObjectURL;
    URL.createObjectURL = function (o) { const u = cou.call(this, o); try { if (o instanceof Blob && /audio|ogg|opus/.test(o.type)) W.blobs.push({ u, b: o }); } catch (e) {} return u; };
    const op = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () { this.muted = true; this.volume = 0; W.plays.push(this.currentSrc || this.src); const p = op.call(this); setTimeout(() => { try { this.pause(); } catch (e) {} }, 300); return p; };
  }

  // 1. Ground truth: every message id in the chat, in time order, from WhatsApp's local store (bodies there are encrypted).
  W.list = async (contactName) => {
    const db = await open('model-storage');
    const contacts = await all(db, 'contact'); const msgs = await all(db, 'message');
    const ids = contacts.filter(c => (c.name || c.pushname) === contactName).map(c => String(c.id).split('@')[0]);
    const mine = msgs.filter(m => ids.some(i => m.id.includes(i))).sort((a, b) => a.t - b.t);
    W.ml = mine.map((m, i) => ({ n: i + 1, k: m.id.split('_').at(-1), t: m.t, type: m.type, me: m.id.startsWith('true_') }));
    return { total: W.ml.length, first: fmt(W.ml[0].t), last: fmt(W.ml.at(-1).t) };
  };

  const idx = () => new Map(W.ml.map((m, i) => [m.k, i]));
  const renderTo = async (m, budget = 20000) => {
    const t0 = Date.now(); const main = document.querySelector('#main'); const ix = idx(); const target = ix.get(m.k); const p = pane();
    while (Date.now() - t0 < budget) {
      if (main.querySelector(`[data-id="${m.k}"]`)) return true;
      const r = [...main.querySelectorAll('[data-id]')].map(e => ix.get(e.getAttribute('data-id'))).filter(x => x !== undefined);
      if (target < Math.min(...r)) p.scrollTop = Math.max(0, p.scrollTop - p.clientHeight * 0.6); else p.scrollTop += p.clientHeight * 0.6;
      await sleep(700);
    }
    return false;
  };

  // 2. Text: scrolls toward the first missing message and keeps what is rendered. Empty rows do not count.
  W.collect = async (budget = 35000) => {
    const t0 = Date.now(); const main = document.querySelector('#main'); const ix = idx(); const p = pane();
    const grab = () => main.querySelectorAll('[data-id]').forEach(el => {
      const k = el.getAttribute('data-id'); if (!ix.has(k)) return;
      const txt = el.innerText.replace(/\s+\n/g, '\n').trim(); if (!txt) return;
      if (!W.got[k] || txt.length > W.got[k].length) W.got[k] = txt;
    });
    const missing = () => W.ml.filter(m => !W.got[m.k]);
    grab();
    while (Date.now() - t0 < budget && missing().length) {
      const r = [...main.querySelectorAll('[data-id]')].map(e => ix.get(e.getAttribute('data-id'))).filter(x => x !== undefined);
      if (ix.get(missing()[0].k) < Math.min(...r)) p.scrollTop = Math.max(0, p.scrollTop - p.clientHeight * 0.6); else p.scrollTop += p.clientHeight * 0.5;
      await sleep(900); grab();
    }
    return { got: Object.keys(W.got).length, missing: missing().length };
  };

  // 3. Voice: plays each voice note muted for a moment and records which audio blob played.
  W.voice = async (budget = 38000) => {
    const t0 = Date.now();
    for (const m of W.ml.filter(x => x.type === 'ptt' && !W.map[x.n])) {
      if (Date.now() - t0 > budget) break;
      if (!await renderTo(m)) continue;
      const el = document.querySelector(`#main [data-id="${m.k}"]`); el.scrollIntoView({ block: 'center' }); await sleep(500);
      const before = W.plays.length; const b = el.querySelector('button[aria-label="Spela upp röstmeddelande"], button[aria-label="Play voice message"]'); if (!b) continue;
      b.click(); for (let i = 0; i < 40 && W.plays.length === before; i++) await sleep(250);
      if (W.plays.length > before) W.map[m.n] = W.plays.at(-1);
      const pb = el.querySelector('button[aria-label*="Pausa"], button[aria-label*="Pause"]'); if (pb) pb.click();
    }
    return { voice: Object.keys(W.map).length, of: W.ml.filter(x => x.type === 'ptt').length };
  };

  // 4. Export: one file with all messages (jsonl) and one with the voice notes (json, base64).
  //    Chrome must allow multiple downloads from web.whatsapp.com.
  W.export = async (prefix = 'whatsapp') => {
    const dl = (blob, name) => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); };
    const rows = W.ml.map(m => JSON.stringify({ n: m.n, id: m.k, time: fmt(m.t), t: m.t, from: m.me ? 'me' : 'them', type: m.type, text: (W.got[m.k] || '').replace(/\n?(Redigerades|Edited)?\d{1,2}:\d{2}$/, '').trim() }));
    dl(new Blob([rows.join('\n')], { type: 'application/x-ndjson' }), `${prefix}-messages.jsonl`);
    const b64 = async b => { const u = new Uint8Array(await b.arrayBuffer()); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
    const pack = {};
    for (const [n, src] of Object.entries(W.map)) { const m = W.ml[n - 1]; const x = W.blobs.find(b => b.u === src); if (x) pack[m.k] = await b64(x.b); }
    await sleep(600); dl(new Blob([JSON.stringify(pack)], { type: 'application/json' }), `${prefix}-voice.json`);
    return { messages: rows.length, voice: Object.keys(pack).length };
  };
  return 'installed';
})();
