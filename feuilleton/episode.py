#!/usr/bin/env python3
"""Le feuilleton de Novabene : découpe De la démocratie en Amérique en épisodes.

Usage (depuis la racine du dépôt) :
    python3 feuilleton/episode.py prochain          # affiche l'épisode à publier (JSON), sans rien modifier
    python3 feuilleton/episode.py avancer "résumé"  # marque cet épisode comme publié et enregistre le résumé cumulé
    python3 feuilleton/episode.py etat              # affiche l'état

Le texte vient de Project Gutenberg (domaine public), 12e édition, 1848.
Chaque épisode fait environ 1 200 à 1 800 mots et s'arrête en fin de paragraphe,
de préférence juste avant un nouveau chapitre.
"""
import json
import pathlib
import re
import sys

ICI = pathlib.Path(__file__).resolve().parent
ETAT = ICI / "etat.json"
SOURCES = [ICI / "sources" / f"pg{n}.txt" for n in (30513, 30514, 30515, 30516)]
TOMES = ["Tome premier", "Tome deuxième", "Tome troisième", "Tome quatrième"]
MIN_MOTS, CIBLE_MOTS, MAX_MOTS = 900, 1200, 1800
IGNORER = {"DE LA", "DÉMOCRATIE", "EN AMÉRIQUE.", "EN AMÉRIQUE", "DE LA DÉMOCRATIE EN AMÉRIQUE.", "DE LA DÉMOCRATIE EN AMÉRIQUE"}


def corps(texte: str) -> str:
    debut = texte.index("\n", texte.index("*** START OF")) + 1
    fin = texte.index("*** END OF")
    t = texte[debut:fin]
    note = t.find("[Notes au lecteur de ce fichier")
    return t[:note] if note != -1 else t


def est_titre(p: str) -> bool:
    lettres = [c for c in p if c.isalpha()]
    return bool(lettres) and len(p) < 160 and sum(c.isupper() for c in lettres) / len(lettres) > 0.85


def blocs():
    """Liste ordonnée des blocs de l'œuvre : (tome, type, texte)."""
    sortie = []
    commence = False
    for i, src in enumerate(SOURCES):
        brut = corps(src.read_text(encoding="utf-8"))
        brut = re.sub(r"\n[ \t]*\[Note [^\]]*\]", "\n", brut, flags=re.S)  # notes de bas de page
        dans_notes = False
        for para in re.split(r"\n\s*\n", brut):
            lignes = [l for l in para.split("\n") if l.strip()]
            if not lignes:
                continue
            retrait = all(l.startswith("     ") for l in lignes)
            texte = re.sub(r"\s+", " ", " ".join(l.strip() for l in lignes)).strip()
            texte = re.sub(r"\[\d+\]", "", texte).replace("--", "—")
            if not commence:
                if texte.startswith("INTRODUCTION"):
                    commence = True
                else:
                    continue
            if texte in IGNORER:
                continue
            if texte.startswith("NOTES") and est_titre(texte):
                dans_notes = True
                continue
            if texte.startswith("CHAPITRE") or texte.startswith("INTRODUCTION") or texte.startswith("PARTIE") or "PARTIE" in texte[:20]:
                dans_notes = False
            if dans_notes:
                continue
            if texte.startswith("CHAPITRE"):
                kind = "chapitre"
            elif est_titre(texte):
                kind = "titre"
            elif retrait and "—" in texte:
                kind = "sommaire"
            else:
                kind = "p"
            sortie.append({"tome": TOMES[i], "type": kind, "texte": texte})
    return sortie


def lire_etat():
    if ETAT.exists():
        return json.loads(ETAT.read_text(encoding="utf-8"))
    return {"oeuvre": "De la démocratie en Amérique", "auteur": "Alexis de Tocqueville",
            "edition": "12e édition, Pagnerre, 1848 (Project Gutenberg, domaine public)",
            "position": 0, "episode": 0, "resume": "", "fini": False}


def prochain(b, etat):
    i = etat["position"]
    if i >= len(b):
        return None
    pris, mots = [], 0
    # Repère du chapitre en cours (pour l'en-tête), pris en remontant.
    chapitre, titre = "", ""
    for j in range(i - 1, -1, -1):
        if not titre and b[j]["type"] == "titre":
            titre = b[j]["texte"]
        if b[j]["type"] == "chapitre":
            chapitre = b[j]["texte"]
            break
    while i < len(b):
        blk = b[i]
        if blk["type"] == "chapitre" and mots >= MIN_MOTS:
            break
        pris.append(blk)
        if blk["type"] == "p":
            mots += len(blk["texte"].split())
            if mots >= CIBLE_MOTS and (i + 1 >= len(b) or b[i + 1]["type"] != "p" or mots >= MAX_MOTS):
                i += 1
                break
            if mots >= MAX_MOTS:
                i += 1
                break
        i += 1
    else:
        i = len(b)
    return {
        "oeuvre": etat["oeuvre"], "auteur": etat["auteur"], "edition": etat["edition"],
        "episode": etat["episode"] + 1, "tome": pris[0]["tome"] if pris else "",
        "chapitre_en_cours": chapitre, "titre_en_cours": titre,
        "resume_des_episodes_precedents": etat["resume"],
        "mots": mots, "blocs": pris, "position_suivante": i,
        "progression": f"{round(100 * i / len(b))} %", "dernier": i >= len(b),
    }


def main():
    b = blocs()
    etat = lire_etat()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prochain"
    if cmd == "etat":
        print(json.dumps({k: v for k, v in etat.items()}, ensure_ascii=False, indent=1))
        print(f"blocs : {etat['position']} / {len(b)}")
    elif cmd == "prochain":
        ep = prochain(b, etat)
        print(json.dumps(ep, ensure_ascii=False, indent=1) if ep else '{"fini": true}')
    elif cmd == "avancer":
        ep = prochain(b, etat)
        if not ep:
            sys.exit("Le feuilleton est terminé.")
        etat.update(position=ep["position_suivante"], episode=ep["episode"], fini=ep["dernier"])
        if len(sys.argv) > 2:
            etat["resume"] = sys.argv[2]
        ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Épisode {ep['episode']} enregistré ({ep['progression']}).")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
