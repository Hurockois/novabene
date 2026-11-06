"""Télécharge depuis Project Gutenberg (via gutendex.com) une petite bibliothèque
d'œuvres françaises du domaine public, pour la « page choisie » du week-end."""
import json, pathlib, re, urllib.parse, urllib.request

OEUVRES = [
    ("montaigne-essais", "Essais Montaigne"),
    ("pascal-pensees", "Pensées Pascal"),
    ("la-rochefoucauld-maximes", "Réflexions Maximes La Rochefoucauld"),
    ("la-bruyere-caracteres", "Caractères La Bruyère"),
    ("marc-aurele-pensees", "Pensées Marc-Aurèle"),
    ("montesquieu-romains", "Considérations grandeur Romains Montesquieu"),
    ("montesquieu-esprit-des-lois", "Esprit des lois Montesquieu"),
    ("tocqueville-ancien-regime", "Ancien Régime et la Révolution Tocqueville"),
    ("descartes-methode", "Discours de la méthode Descartes"),
    ("chateaubriand-memoires", "Mémoires d'outre-tombe Chateaubriand"),
    ("renan-souvenirs", "Souvenirs d'enfance et de jeunesse Renan"),
    ("vauvenargues", "Vauvenargues"),
    ("joubert-pensees", "Joubert Pensées"),
    ("bastiat-sophismes", "Sophismes économiques Bastiat"),
    ("bastiat-harmonies", "Harmonies économiques Bastiat"),
    ("seneque", "Sénèque"),
]
DOSSIER = pathlib.Path("feuilleton/bibliotheque")
DOSSIER.mkdir(parents=True, exist_ok=True)
catalogue = []

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Novabene/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

for slug, q in OEUVRES:
    try:
        data = json.loads(get("https://gutendex.com/books/?languages=fr&search=" + urllib.parse.quote(q)))
        livres = [b for b in data.get("results", []) if any(k.startswith("text/plain") for k in b["formats"])]
        if not livres:
            print("introuvable :", q); continue
        b = livres[0]
        url = next(v for k, v in b["formats"].items() if k.startswith("text/plain"))
        texte = get(url).decode("utf-8", errors="replace")
        (DOSSIER / f"{slug}.txt").write_text(texte, encoding="utf-8")
        auteurs = ", ".join(a["name"] for a in b.get("authors", []))
        catalogue.append({"fichier": f"{slug}.txt", "titre": b["title"], "auteurs": auteurs,
                          "gutenberg": f"https://www.gutenberg.org/ebooks/{b['id']}", "mots": len(texte.split())})
        print("ok :", slug, "→", b["title"], "/", auteurs)
    except Exception as e:
        print("échec :", q, e)

(DOSSIER / "catalogue.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
