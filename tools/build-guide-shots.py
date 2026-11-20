#!/usr/bin/env python3
"""Capture the learner's screen for every slide or page that a facilitator guide
covers, from the classroom edition the learners actually see.

Deck courses: facilitator/img/<slide-id>.jpg, one per slide in facilitator/notes.json
(taken from the classroom deck; facilitator-only slides come from the facilitator deck
with the notes rail hidden).
AI-enabled Education Series courses: <course>-class/facilitator/img/<page-key>.jpg, one
per NOTES entry (taken from the classroom edition; the prep page from the facilitator
edition).

Run from the repo root: python3 tools/build-guide-shots.py [course-dir ...]
Needs Playwright for Python and a Chromium (PW_CHROME env var or the Playwright default)."""
import json, os, re, sys, glob, subprocess, time
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from playwright.sync_api import sync_playwright

PORT = 8894
CHROME = os.environ.get('PW_CHROME') or next(iter(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')), None)
W, H = 1440, 900
LIVE = 'https://me5231979.github.io/Course_Library/'   # the welcome QR encodes the published learner edition

QR = """(url) => { const box = document.getElementById('qrBox'); if (!box || typeof qrcode !== 'function') return;
  const q = qrcode(0, 'M'); q.addData(url); q.make(); box.innerHTML = q.createSvgTag({ scalable: true, margin: 2 });
  const u = document.getElementById('qrUrl'); if (u) u.textContent = url.replace(/^https?:\\/\\//, '').replace(/\\/$/, ''); }"""

DECKS = sorted(glob.glob('courses/*/facilitator/notes.json') + glob.glob('*/facilitator/notes.json'))
LEARN = [('learn/classroom', 'learn/classroom/facilitator')] + \
        [(d[:-len('/facilitator')], d) for d in sorted(glob.glob('learn/*-class/facilitator'))]
only = set(a.rstrip('/') for a in sys.argv[1:])

REVEAL = """() => { document.querySelectorAll('[data-reveal]').forEach(e => e.classList.add('in'));
  document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'));
  document.querySelectorAll('.manifesto .w').forEach(e => e.classList.add('lit'));
  document.querySelectorAll('.facnote').forEach(e => e.style.display = 'none');
  document.querySelectorAll('video').forEach(v => { try { v.pause(); } catch (e) {} }); }"""

def notes_js(path):
    """NOTES is a JS object literal inside the facilitator page; let node turn it into JSON."""
    t = open(path, encoding='utf-8').read()
    i = t.find('var NOTES = {')
    j = t.find('\n};', i)
    src = t[i + len('var NOTES = '):j + 2]
    out = subprocess.run(['node', '-e', 'const N=' + src + '; process.stdout.write(JSON.stringify(N));'],
                         capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f'could not parse NOTES in {path}: {out.stderr[:300]}')
    return json.loads(out.stdout)

def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    shots = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
            ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1, reduced_motion='reduce')
            # ---------- deck courses ----------
            for nf in DECKS:
                course = nf[:-len('/facilitator/notes.json')]
                if only and course not in only: continue
                ids = [s['id'] for s in json.load(open(nf, encoding='utf-8'))['sections']]
                out = f'{course}/facilitator/img'; os.makedirs(out, exist_ok=True)
                learner = open(f'{course}/index.html', encoding='utf-8').read()
                for edition in ('index.html', 'facilitator/index.html'):
                    want = [i for i in ids if (f'id="{i}"' in learner) == (edition == 'index.html')]
                    if not want: continue
                    pg = ctx.new_page()
                    pg.goto(f'http://localhost:{PORT}/{course}/{edition}', wait_until='load')
                    pg.wait_for_timeout(600)
                    pg.evaluate(QR, LIVE + course + '/')
                    for sid in want:
                        pg.evaluate(f"""() => {{ const s = document.getElementById('{sid}'); const d = document.querySelector('.deck');
                            if (s && d) d.scrollTo({{left: s.offsetLeft, behavior: 'instant'}}); if (s) s.scrollTop = 0; }}""")
                        pg.wait_for_timeout(250)
                        pg.evaluate(REVEAL)
                        pg.wait_for_timeout(350)
                        pg.screenshot(path=f'{out}/{sid}.jpg', type='jpeg', quality=82)
                        shots += 1
                    pg.close()
                print(f'{course:42} {len(ids)} slides')
            # ---------- AI-enabled Education Series courses ----------
            for classroom, fac in LEARN:
                if only and classroom not in only and fac not in only: continue
                notes = notes_js(f'{fac}/index.html')
                out = f'{fac}/img'; os.makedirs(out, exist_ok=True)
                keys = list(notes.keys())
                for edition, want in ((f'{classroom}/index.html', [k for k in keys if k not in ('prep', 'run')]),
                                      (f'{fac}/index.html', [k for k in keys if k in ('prep', 'run')])):
                    if not want: continue
                    pg = ctx.new_page()
                    pg.goto(f'http://localhost:{PORT}/{edition}#p/{want[0]}/1', wait_until='load')
                    pg.wait_for_timeout(900)
                    pg.evaluate(QR, LIVE + classroom + '/')
                    for key in want:
                        pg.evaluate(f"location.hash = '#p/{key}/1'")
                        pg.wait_for_timeout(500)
                        pg.evaluate(REVEAL)
                        pg.evaluate("() => { const c = document.querySelector('.page.cur'); if (c) c.scrollTop = 0; }")
                        pg.wait_for_timeout(300)
                        cur = pg.evaluate("() => { const c = document.querySelector('.page.cur'); return c ? c.getAttribute('data-sec') : null; }")
                        if cur != key:
                            print(f'  WARN {edition} #{key}: pager landed on {cur}')
                        pg.screenshot(path=f'{out}/{key}.jpg', type='jpeg', quality=82)
                        shots += 1
                    pg.close()
                print(f'{fac:42} {len(keys)} pages')
            b.close()
    finally:
        srv.terminate()
    print('screens captured:', shots)

if __name__ == '__main__':
    main()
