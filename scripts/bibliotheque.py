"""Télécharge depuis Project Gutenberg une petite bibliothèque d'œuvres françaises
du domaine public, pour la « page choisie » du week-end.

Recherche dans le catalogue officiel (pg_catalog.csv) par auteur et mots du titre,
en français, puis télécharge le texte brut de chaque œuvre trouvée."""
import csv, io, json, pathlib, unicodedata, urllib.request

# (fichier, mot de l'auteur, mots devant figurer dans le titre)
OEUVRES = [
    ("montaigne-essais", "Montaigne", ["essais"]),
    ("pascal-pensees", "Pascal", ["pensées"]),
    ("la-rochefoucauld-maximes", "La Rochefoucauld", ["maximes"]),
    ("la-bruyere-caracteres", "La Bruyère", ["caractères"]),
    ("marc-aurele-pensees", "Marcus Aurelius", ["pensées"]),
    ("montesquieu-romains", "Montesquieu", ["romains"]),
    ("montesquieu-esprit-des-lois", "Montesquieu", ["esprit", "lois"]),
    ("montesquieu-lettres-persanes", "Montesquieu", ["lettres persanes"]),
    ("tocqueville-ancien-regime", "Tocqueville", ["ancien régime"]),
    ("descartes-methode", "Descartes", ["discours"]),
    ("chateaubriand-memoires", "Chateaubriand", ["mémoires d'outre-tombe"]),
    ("renan-souvenirs", "Renan", ["souvenirs"]),
    ("vauvenargues", "Vauvenargues", [""]),
    ("bastiat-sophismes", "Bastiat", ["sophismes"]),
    ("bastiat-harmonies", "Bastiat", ["harmonies"]),
    ("seneque", "Seneca", [""]),
    ("chamfort", "Chamfort", [""]),
    ("rivarol", "Rivarol", [""]),
]
DOSSIER = pathlib.Path("feuilleton/bibliotheque")
DOSSIER.mkdir(parents=True, exist_ok=True)


def get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "Novabene/1.0 (lecture personnelle)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).replace("’", "'")


rows = list(csv.DictReader(io.StringIO(get("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv").decode("utf-8"))))
fr = [r for r in rows if r.get("Type") == "Text" and "fr" in r.get("Language", "").split("; ")]
print(f"{len(fr)} livres en français au catalogue")

catalogue = []
for slug, auteur, mots in OEUVRES:
    cands = [r for r in fr if norm(auteur) in norm(r["Authors"]) and all(norm(m) in norm(r["Title"]) for m in mots)]
    if not cands:
        print("introuvable :", auteur, mots)
        continue
    cands.sort(key=lambda r: int(r["Text#"]))
    r = cands[0]
    n = r["Text#"]
    try:
        texte = get(f"https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt").decode("utf-8", errors="replace")
    except Exception as e:
        print("échec :", slug, e)
        continue
    (DOSSIER / f"{slug}.txt").write_text(texte, encoding="utf-8")
    titre = " ".join(r["Title"].split())
    catalogue.append({"fichier": f"{slug}.txt", "titre": titre, "auteurs": r["Authors"],
                      "gutenberg": f"https://www.gutenberg.org/ebooks/{n}", "mots": len(texte.split()),
                      "autres_volumes": [c["Text#"] for c in cands[1:6]]})
    print("ok :", slug, "→", titre, "/", r["Authors"])

(DOSSIER / "catalogue.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
