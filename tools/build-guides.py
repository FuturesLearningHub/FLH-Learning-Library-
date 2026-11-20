#!/usr/bin/env python3
"""Build the printable facilitator guides: the learner's screen beside the facilitation
notes, one card per slide or page, for all 28 courses.

Deck courses: facilitator/guide.html is regenerated from facilitator/notes.json. The front
matter (run of show, audience, room setup, materials, prep, contingencies, tough questions,
templates, after the session) is kept from the existing guide; the run-of-show table and
every per-slide card are rebuilt, each card showing facilitator/img/<slide>.jpg.

AI-enabled Education Series courses: <course>-class/facilitator/guide.html is generated from
the NOTES object in the facilitator edition and the prep cards on its first page, each card
showing facilitator/img/<page>.jpg.

Run tools/build-guide-shots.py first so the images are current. Run from the repo root."""
import json, os, re, glob, subprocess, html

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def esc(s):
    return html.escape(s, quote=False) if s else ''

def q(s):  # a scripted line in curly quotes
    return '&ldquo;' + esc(s) + '&rdquo;'

# ---------------------------------------------------------------- shared page frame
CSS = """  * { box-sizing: border-box; }
  body { margin: 0; font-family: 'Inter', Arial, sans-serif; color: #1C1C1C; background: #fff;
    font-size: 12.5px; line-height: 1.5; }
  .sheet { max-width: 860px; margin: 0 auto; padding: 28px 32px; }
  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
    border-bottom: 2px solid #CFAE70; padding-bottom: 14px; margin-bottom: 16px; }
  header img { width: 150px; }
  h1 { font-family: 'Libre Caslon Display', serif; font-weight: 400; font-size: 26px; margin: 0; }
  h1 em { font-style: italic; color: #8C6822; }
  .eyebrow { font-family: 'Antonio', Impact, sans-serif; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; font-size: 10px; color: #8C6822; margin: 0 0 6px; }
  h2 { font-family: 'Libre Caslon Display', serif; font-weight: 400; font-size: 18px;
    margin: 0 0 4px; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
  h3 { font-family: 'Antonio', Impact, sans-serif; font-weight: 700; text-transform: uppercase;
    letter-spacing: .06em; font-size: 12px; color: #8C6822; margin: 14px 0 4px; }
  .mins { font-family: 'Antonio', Impact, sans-serif; font-size: 11px; color: #8C6822;
    letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; }
  .sec { border: 1px solid #E4E4E4; border-left: 3px solid #CFAE70; border-radius: 4px;
    padding: 12px 16px; margin-bottom: 12px; break-inside: avoid;
    display: grid; grid-template-columns: 290px 1fr; gap: 16px; align-items: start; }
  .sec.noimg { grid-template-columns: 1fr; }
  .sec.noimg .sec__shot { display: none; }
  .sec__shot { position: sticky; top: 12px; }
  .sec__shot img { width: 100%; border: 1px solid #E4E4E4; border-radius: 3px; display: block; }
  .sec__shot figcaption { font-family: 'Antonio', Impact, sans-serif; text-transform: uppercase; letter-spacing: .06em;
    font-size: 9px; color: #8C6822; margin-top: 4px; }
  .sec__notes { min-width: 0; }
  @media (max-width: 700px) { .sec { grid-template-columns: 1fr; } .sec__shot { position: static; max-width: 340px; } }
  @media print { .sec { grid-template-columns: 240px 1fr; } .sec__shot { position: static; }
    .sec__shot img { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  .purpose { font-weight: 600; margin: 2px 0 8px; }
  .tagline { font-family: 'Antonio', Impact, sans-serif; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; font-size: 10px; margin: 10px 0 2px; color: #1C1C1C;
    background: #CFAE70; display: inline-block; padding: 2px 7px; border-radius: 2px; }
  .tagline.ask { background: #8BA18E; }
  .script { font-family: 'Libre Caslon Display', serif; font-style: italic; font-size: 13.5px;
    margin: 4px 0 6px; }
  .mini { margin: 4px 0; color: #444; }
  .mini.core { border-top: 1px dashed #CFAE70; padding-top: 6px; }
  ol, ul { margin: 2px 0 8px; padding-left: 20px; }
  li { margin-bottom: 3px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; }
  th, td { border: 1px solid #E4E4E4; padding: 5px 9px; text-align: left; }
  th { font-family: 'Antonio', Impact, sans-serif; text-transform: uppercase; letter-spacing: .06em;
    font-size: 10px; color: #8C6822; }
  .front { border: 1px solid #E4E4E4; border-radius: 4px; padding: 12px 16px; margin-bottom: 12px;
    break-inside: avoid; }
  .printbtn { position: fixed; right: 18px; top: 18px; background: #CFAE70; border: 0; border-radius: 4px;
    padding: 9px 16px; font-family: Inter, Arial, sans-serif; font-weight: 600; font-size: 13px; cursor: pointer; }
  @media print { .printbtn { display: none; } body { font-size: 11px; } .sheet { padding: 0; max-width: none; } }
"""

def fonts(prefix):
    return f"""  @font-face {{ font-family: 'Libre Caslon Display'; font-weight: 400;
    src: url('{prefix}libre-caslon-display-latin-400-normal.woff2') format('woff2'); }}
  @font-face {{ font-family: 'Inter'; font-weight: 400;
    src: url('{prefix}inter-latin-400-normal.woff2') format('woff2'); }}
  @font-face {{ font-family: 'Inter'; font-weight: 600;
    src: url('{prefix}inter-latin-600-normal.woff2') format('woff2'); }}
  @font-face {{ font-family: 'Antonio'; font-weight: 700;
    src: url('{prefix}antonio-latin-700-normal.woff2') format('woff2'); }}
"""

ANALYTICS = """<!-- Vercel Web Analytics (vercel-analytics): served only by Vercel, so it is skipped on GitHub Pages -->
<script>
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  if (!/(^|\\.)github\\.io$/.test(location.hostname)) {
    var vaScript = document.createElement('script');
    vaScript.defer = true;
    vaScript.src = '/_vercel/insights/script.js';
    document.head.appendChild(vaScript);
  }
</script>"""

def shot(img, alt, caption):
    return (f'<figure class="sec__shot"><img src="{img}" alt="{esc(alt)}" loading="eager" '
            f'onerror="this.closest(\'.sec\').classList.add(\'noimg\')"><figcaption>{esc(caption)}</figcaption></figure>')

# ---------------------------------------------------------------- deck courses
def core_label(s):
    core = s.get('coreMinutes')
    if core in (0, None): return 'skip'
    return str(core)

def core_num(s):
    core = s.get('coreMinutes')
    return core if isinstance(core, int) else 0

def deck_card(s):
    core_s = core_label(s)
    mins = f'Full {s["minutes"]} min' + (f' · Core {core_s}' if core_s else '')
    out = ['  <div class="sec">',
           '    ' + shot(f'img/{s["id"]}.jpg', f'Slide: {s["title"]}', 'What learners see'),
           '    <div class="sec__notes">',
           f'    <h2>{esc(s["title"])} <span class="mins">{esc(mins)}</span></h2>']
    if s.get('purpose'): out.append(f'    <p class="purpose">{esc(s["purpose"])}</p>')
    if s.get('say'): out.append(f'    <p class="tagline say">Say</p><p class="script">{q(s["say"])}</p>')
    if s.get('facilitate'):
        out.append('    <p class="tagline">Do</p><ol>' + ''.join(f'<li>{esc(x)}</li>' for x in s['facilitate']) + '</ol>')
    a = s.get('ask')
    if a:
        line = f"    <p class='tagline ask'>Ask</p><p class='script'>{q(a.get('q', ''))}</p>"
        if a.get('expect'):
            line += "<p class='mini'><b>Expect:</b></p><ul>" + ''.join(f'<li>{esc(x)}</li>' for x in a['expect']) + '</ul>'
        if a.get('respond'):
            line += f"<p class='mini'><b>Respond:</b> {esc(a['respond'])}</p>"
        out.append(line)
    if s.get('debrief'): out.append(f'    <p class="mini"><b>Debrief:</b> {esc(s["debrief"])}</p>')
    if s.get('validate'): out.append(f'    <p class="mini"><b>Validate:</b> {esc(s["validate"])}</p>')
    if s.get('watchFor'): out.append(f'    <p class="mini"><b>Watch for:</b> {esc(s["watchFor"])}</p>')
    if s.get('transition'): out.append(f'    <p class="mini"><b>Transition:</b> {q(s["transition"])}</p>')
    if s.get('coreNote'): out.append(f'    <p class="mini core"><b>Core path:</b> {esc(s["coreNote"])}</p>')
    out += ['    </div>', '  </div>']
    return '\n'.join(out)

def build_deck(course):
    nf = f'{course}/facilitator/notes.json'; gf = f'{course}/facilitator/guide.html'
    d = json.load(open(nf, encoding='utf-8')); secs = d['sections']
    old = open(gf, encoding='utf-8').read()
    head = old[:old.find('  <div class="sec">')]
    # the run of show follows the sections as they stand now
    rows = ''.join(f'<tr><td>{esc(s["title"])}</td><td>{s["minutes"]}</td><td>{esc(core_label(s))}</td></tr>' for s in secs)
    full = sum(s['minutes'] for s in secs); core = sum(core_num(s) for s in secs)
    head = re.sub(r'(<h3>Run of show</h3>\s*<table>).*?(</table>)',
                  lambda m: m.group(1) + '<tr><th>Screen</th><th>Full (min)</th><th>Core (min)</th></tr>' + rows +
                            f'\n    <tr><th>Total</th><th>{full}</th><th>{core}</th></tr>' + m.group(2), head, count=1, flags=re.S)
    # the same frame CSS on every guide (adds the figure caption and the print colour rule)
    head = re.sub(r'  \* \{ box-sizing: border-box; \}.*?(?=</style>)', CSS, head, count=1, flags=re.S)
    cards = '\n'.join(deck_card(s) for s in secs)
    tail = ('\n  <p class="mini" style="margin-top:14px;color:#777">Generated from facilitator/notes.json and the learner edition on screen. '
            'The on-screen facilitator edition lives at ./ alongside this guide.</p>\n</main>\n</body>\n</html>\n')
    open(gf, 'w', encoding='utf-8').write(head + cards + tail)
    return len(secs)

# ---------------------------------------------------------------- AI-enabled Education Series
def notes_js(path):
    t = open(path, encoding='utf-8').read()
    i = t.find('var NOTES = {'); j = t.find('\n};', i)
    out = subprocess.run(['node', '-e', 'const N=' + t[i + 12:j + 2] + '; process.stdout.write(JSON.stringify(N));'],
                         capture_output=True, text=True)
    if out.returncode: raise SystemExit(f'NOTES parse failed for {path}: {out.stderr[:200]}')
    return json.loads(out.stdout), t

def plan_labels(t):
    i = t.find('var PLAN = [')
    return dict(re.findall(r"key:\s*'([^']+)',\s*label:\s*'([^']+)'", t[i:i + 4000]))

def text_of(fragment):
    s = re.sub(r'<svg.*?</svg>', '', fragment, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def learn_time(n):
    if n.get('time'): return n['time']
    if n.get('full') is not None: return f'Full {n["full"]} min · Core {n.get("core", "")}'
    return ''

def learn_card(key, n, label):
    out = ['  <div class="sec">',
           '    ' + shot(f'img/{key}.jpg', f'Page: {label}', 'What learners see'),
           '    <div class="sec__notes">',
           f'    <h2>{esc(label)} <span class="mins">{esc(learn_time(n))}</span></h2>']
    if n.get('purpose'): out.append(f'    <p class="purpose">{esc(n["purpose"])}</p>')
    if n.get('invite'):
        out.append(f'    <p class="mini">{esc(n.get("inviteLead", ""))} The invite text is on the first page of the facilitator edition and in the printed packet below.</p>')
    if n.get('say'): out.append(f'    <p class="tagline say">Say</p><p class="script">{q(n["say"])}</p>')
    if n.get('doList'):
        out.append('    <p class="tagline">Do</p><ol>' + ''.join(f'<li>{esc(x)}</li>' for x in n['doList']) + '</ol>')
    if n.get('validate'): out.append(f'    <p class="mini"><b>Validate:</b> {esc(n["validate"])}</p>')
    if n.get('watch'): out.append(f'    <p class="mini"><b>Watch for:</b> {esc(n["watch"])}</p>')
    if n.get('transition'): out.append(f'    <p class="mini"><b>Transition:</b> {q(n["transition"])}</p>')
    core = n.get('core') if isinstance(n.get('core'), str) else n.get('coreNote')
    if core: out.append(f'    <p class="mini core"><b>Core path:</b> {esc(core)}</p>')
    out += ['    </div>', '  </div>']
    return '\n'.join(out)

def build_learn(classroom, fac):
    page = f'{fac}/index.html'
    N, t = notes_js(page)
    labels = plan_labels(t)
    title = html.unescape(re.search(r'<title>(.*?)</title>', t).group(1))
    course_name = re.split(r'\s[·|]\s|\(', title)[0].strip()
    depth = fac.count('/') + 1
    fontpath = '../' * depth + 'assets/fonts/'
    logo = '../' * depth + 'assets/img/vu-lockup-black.png'
    # the prep cards on the facilitator edition's first page
    prep_html = ''
    m = re.search(r'<section id="(?:prep|run)".*?</section>', t, re.S)
    if m:
        steps = re.split(r'<div class="rstep[^"]*">', m.group(0))[1:]
        for st in steps:
            no = re.search(r'class="rno"[^>]*>(.*?)</span>', st, re.S); h = re.search(r'<h5[^>]*>(.*?)</h5>', st, re.S)
            items = [text_of(li) for li in re.findall(r'<li[^>]*>(.*?)</li>', st, re.S)]
            if h:
                prep_html += (f'<h3>{esc(text_of(no.group(1)) if no else "")} · {esc(text_of(h.group(1)))}</h3><ul>'
                              + ''.join(f'<li>{esc(i)}</li>' for i in items) + '</ul>')
    invite = ''
    ii = t.find('var INVITE = '); ij = t.find(';\n', ii)
    if ii > -1:
        out = subprocess.run(['node', '-e', 'const I=' + t[ii + 13:ij] + '; process.stdout.write(JSON.stringify(I));'],
                             capture_output=True, text=True)
        if out.returncode == 0:
            invite = ('<h3>Pre-work invite (copy and paste)</h3><p style="white-space:pre-line">'
                      + esc(json.loads(out.stdout)) + '</p>')
    full = sum((n.get('full') or (int(re.search(r'Full (\d+)', n.get('time', '')).group(1)) if re.search(r'Full (\d+)', n.get('time', '')) else 0)) for n in N.values())
    core = sum((n.get('core') if isinstance(n.get('core'), int) else (int(re.search(r'Core (\d+)', n.get('time', '')).group(1)) if re.search(r'Core (\d+)', n.get('time', '')) else 0)) for n in N.values())
    rows = ''.join(f'<tr><td>{esc(labels.get(k, k))}</td><td>{esc(learn_time(n))}</td></tr>' for k, n in N.items())
    cards = '\n'.join(learn_card(k, n, labels.get(k, k)) for k, n in N.items())
    series = 'Working Smarter' if 'classroom' in fac else 'The AI-enabled Education Series'
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Facilitator Guide (printable) · {esc(course_name)} · Vanderbilt Learning Series</title>
<meta name="robots" content="noindex">
<style>
{fonts(fontpath)}{CSS}</style>
{ANALYTICS}
</head>
<body>
<button class="printbtn" onclick="window.print()">Print / Save as PDF</button>
<main class="sheet">
  <header>
    <div>
      <p class="eyebrow">Vanderbilt · {esc(series)} · facilitator guide · print edition</p>
      <h1>{esc(course_name)}, the <em>facilitator guide</em></h1>
    </div>
    <img src="{logo}" alt="Vanderbilt University">
  </header>

  <div class="front">
    <h3>Run of show</h3>
    <table><tr><th>Page</th><th>Time</th></tr>{rows}
    <tr><th>Total</th><th>Full {full} min · Core {core} min</th></tr></table>
    {prep_html}{invite}
  </div>

{cards}
  <p class="mini" style="margin-top:14px;color:#777">Generated from the facilitator edition's page scripts and the learner edition on screen. The on-screen facilitator edition lives at ./ alongside this guide.</p>
</main>
</body>
</html>
"""
    open(f'{fac}/guide.html', 'w', encoding='utf-8').write(doc)
    return len(N)

if __name__ == '__main__':
    for nf in sorted(glob.glob('courses/*/facilitator/notes.json') + glob.glob('*/facilitator/notes.json')):
        c = nf[:-len('/facilitator/notes.json')]
        print(f'{c:42} {build_deck(c)} cards')
    for classroom, fac in [('learn/classroom', 'learn/classroom/facilitator')] + \
            [(d[:-len('/facilitator')], d) for d in sorted(glob.glob('learn/*-class/facilitator'))]:
        print(f'{fac:42} {build_learn(classroom, fac)} cards')
