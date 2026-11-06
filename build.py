#!/usr/bin/env python3
"""Novabene — assemble une édition en page d'application (PWA).

Usage :
    python3 build.py matin chemin/vers/edition.html
    python3 build.py soir  chemin/vers/edition.html

L'édition est le fichier HTML publié dans Claude (fragment commençant par
<title>, ou page complète : l'enveloppe <html>/<body> est retirée).
Le script écrit index.html (matin) ou soir.html (soir), archive l'édition
dans archives/AAAA-MM-JJ-<edition>.html, régénère archives/index.html et
met à jour la version du cache hors connexion (sw.js).
"""
import datetime as dt
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PAGES = {"matin": "index.html", "soir": "soir.html"}
LABELS = {"matin": "Édition du matin", "soir": "Édition du soir"}

HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Novabene">
<meta name="theme-color" content="#EEEAE0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#17150F" media="(prefers-color-scheme: dark)">
<meta name="robots" content="noindex,nofollow">
<link rel="manifest" href="{base}manifest.webmanifest">
<link rel="icon" href="{base}icons/icon-192.png">
<link rel="apple-touch-icon" href="{base}icons/icon-180.png">
<style>
:root{{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
*,*::before,*::after{{box-sizing:inherit}}
body{{margin:0}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
.nb-nav{{display:flex;justify-content:center;gap:4px 22px;flex-wrap:wrap;padding:10px 0 2px;font-family:"Old Standard TT","Didot",Georgia,serif;font-size:12px;letter-spacing:.18em;text-transform:uppercase}}
.nb-nav a{{color:var(--gray,#5E584D);text-decoration:none;padding:6px 2px;border-bottom:1px solid transparent}}
.nb-nav a[aria-current="page"]{{color:var(--ink,#1B1915);border-bottom-color:var(--ink,#1B1915)}}
.nb-nav a:focus-visible{{outline:2px solid var(--red,#7A2418);outline-offset:3px}}
</style>
"""

TAIL = """
<script>
(function(){{
  if('serviceWorker' in navigator){{navigator.serviceWorker.register('{base}sw.js').catch(function(){{}});}}
  // En mode application, iOS reprend la page telle qu'on l'a laissée :
  // on recharge si elle a plus d'une heure, pour afficher la dernière édition.
  // La pastille de l'icône disparaît dès qu'on ouvre le journal.
  function effacer(){{ if(navigator.clearAppBadge){{ navigator.clearAppBadge().catch(function(){{}}); }} }}
  effacer();
  var loaded=Date.now();
  document.addEventListener('visibilitychange',function(){{
    if(document.visibilityState!=='visible') return;
    effacer();
    if(Date.now()-loaded>3600000){{location.reload();}}
  }});
}})();
</script>
</body>
</html>
"""


def nav(current: str, base: str) -> str:
    items = [("matin", "index.html", "Le matin"), ("soir", "soir.html", "Le soir"), ("archives", "archives/", "Archives")]
    links = []
    for key, href, label in items:
        cur = ' aria-current="page"' if key == current else ""
        links.append(f'<a href="{base}{href}"{cur}>{label}</a>')
    return '<nav class="nb-nav" aria-label="Éditions">' + "".join(links) + "</nav>\n"


def strip_wrapper(src: str) -> str:
    """Retire l'enveloppe <html>/<head>/<body> ajoutée par Claude, si présente."""
    m = re.search(r"<body[^>]*>", src, re.I)
    if m:
        src = src[m.end():]
        end = src.lower().rfind("</body>")
        if end != -1:
            src = src[:end]
    return src.strip()


def split(fragment: str):
    """Sépare l'en-tête (title, meta, link, style) du corps (à partir de .sheet)."""
    m = re.search(r'<div class="sheet"', fragment)
    if not m:
        return "", fragment
    return fragment[: m.start()], fragment[m.start():]


def page(fragment: str, current: str, base: str) -> str:
    head_part, body_part = split(fragment)
    head_part = re.sub(r'<meta name="claude:[^"]*"[^>]*>\s*', "", head_part)
    return (
        HEAD.format(base=base)
        + head_part
        + "\n</head>\n<body>\n"
        + nav(current, base)
        + body_part
        + TAIL.format(base=base)
    )


def edition_date(fragment: str) -> str:
    m = re.search(r'<div class="dateline"><span>([^<]+)</span>', fragment)
    return html.unescape(m.group(1)).strip() if m else ""


def rebuild_archive_index() -> None:
    rows = []
    for f in sorted((ROOT / "archives").glob("????-??-??-*.html"), reverse=True):
        day, kind = f.stem[:10], f.stem[11:]
        try:
            d = dt.date.fromisoformat(day)
            mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                    "septembre", "octobre", "novembre", "décembre"][d.month - 1]
            jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            label = f"{jours[d.weekday()]} {d.day} {mois} {d.year}"
        except ValueError:
            label = day
        rows.append(f'<li><a href="{f.name}">{label}</a><span>{LABELS.get(kind, kind)}</span></li>')
    body = f"""<title>Archives · Novabene</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@900&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap">
<style>
:root{{--paper:#EEEAE0;--ink:#1B1915;--gray:#5E584D;--hair:#BDB5A4;--red:#7A2418}}
@media (prefers-color-scheme: dark){{:root{{--paper:#17150F;--ink:#E9E3D3;--gray:#A49C8A;--hair:#4A4436;--red:#D98A74;color-scheme:dark}}}}
body{{background:var(--paper);color:var(--ink);font-family:"Old Standard TT",Georgia,serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
.sheet{{max-width:640px;margin:0 auto;padding-block:18px 60px}}
h1{{font-family:"Playfair Display",Georgia,serif;font-weight:900;font-size:clamp(34px,9vw,60px);text-align:center;margin:8px 0 6px}}
.motto{{text-align:center;font-style:italic;color:var(--gray);margin:0 0 14px}}
ul{{list-style:none;margin:0;padding:0;border-top:3px double var(--ink)}}
li{{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px dotted var(--gray)}}
li a{{color:var(--ink);text-decoration:none;font-size:17px}}
li span{{color:var(--gray);font-style:italic;font-size:14px}}
.avis{{text-align:center;margin:22px 0 0;font-style:italic}}
.avis a{{color:var(--ink)}}
</style>
<div class="sheet">
<h1>Novabene</h1>
<p class="motto">Les éditions passées</p>
<ul>
{chr(10).join(rows) or '<li>Aucune édition archivée pour l’instant.</li>'}
</ul>
<p class="avis"><a href="../avis.html">Être prévenu de chaque parution</a></p>
</div>
"""
    (ROOT / "archives" / "index.html").write_text(page(body, "archives", "../"), encoding="utf-8")


def bump_cache() -> None:
    sw = ROOT / "sw.js"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    text = sw.read_text(encoding="utf-8")
    text = re.sub(r"const VERSION = '[^']*';", f"const VERSION = '{stamp}';", text, count=1)
    sw.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in PAGES:
        sys.exit(__doc__)
    kind, src = sys.argv[1], pathlib.Path(sys.argv[2])
    fragment = strip_wrapper(src.read_text(encoding="utf-8"))
    if '<div class="sheet"' not in fragment:
        sys.exit("Édition invalide : bloc <div class=\"sheet\"> introuvable.")

    (ROOT / PAGES[kind]).write_text(page(fragment, kind, ""), encoding="utf-8")

    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).date().isoformat()
    archive = ROOT / "archives" / f"{today}-{kind}.html"
    archive.write_text(page(fragment, kind, "../"), encoding="utf-8")

    rebuild_archive_index()
    bump_cache()
    print(f"OK : {PAGES[kind]} et archives/{archive.name} ({edition_date(fragment)})")


if __name__ == "__main__":
    main()
