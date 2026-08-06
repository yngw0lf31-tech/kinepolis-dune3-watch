#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veille Kinepolis Dune 3 — version GitHub Actions (sans Mac).
Lancée toutes les ~5 min par .github/workflows/watch.yml ; l'état
(state.json) est commité dans le repo entre deux exécutions, donc les
alertes sont dédupliquées pour de vrai (pas de fenêtre 12 h).

Alerte ntfy (iPhone) :
  🚨 urgente  — nouvelles séances IMAX 70MM, ou places 70mm libérées ;
  ℹ️ info     — premières séances tout court, nouvelle fiche « Dune 3 ».
"""
import json
import os
import re
import sys
import unicodedata

from curl_cffi import requests

NTFY = "https://ntfy.sh"
# Le sujet ntfy vient du secret GitHub NTFY_TOPIC (jamais commité en clair
# — le repo peut être public sans exposer tes notifications).
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
if not TOPIC:
    sys.exit("NTFY_TOPIC manquant : configure le secret GitHub (voir SETUP.md)")
API = "https://kinepolisweb-programmation.kinepolis.com/api/"
CID = 36318
URL_FILM = "https://kinepolis.be/nl/movies/detail/36318/HO00013472/0/dune-part-three/"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
DISCOVER_RE = re.compile(r"dune.*(three|3\b|iii\b|deel\s*3|partie\s*3)", re.I)

s = requests.Session(impersonate="chrome")

def get(path):
    r = s.get(API + path, timeout=25,
              headers={"Accept": "application/json",
                       "Origin": "https://kinepolis.be",
                       "Referer": "https://kinepolis.be/"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} sur {path}")
    return r.json()

def ascii_safe(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()

def push(title, msg, click, urgent):
    r = s.post(f"{NTFY}/{TOPIC}", data=msg.encode("utf-8"), headers={
        "Title": ascii_safe(title),
        "Priority": "urgent" if urgent else "default",
        "Tags": "rotating_light,clapper" if urgent else "information_source",
        "Click": click}, timeout=20)
    print(f"ntfy {r.status_code} ← {title}")

def norm(x):
    fmt = ((x.get("film") or {}).get("format") or {})
    return (str(fmt.get("name") or "") + ","
            + str(x.get("rawSessionAttributes") or "")).lower().replace(" ", "")

def key(x):
    return str(x.get("id") or f"{x.get('complexOperator')}-{x.get('vistaSessionId')}")

def summarize(xs):
    cines = sorted({x.get("cinemaLabel") or x.get("complexOperator") or "?" for x in xs})
    times = sorted((x.get("showtime") or "")[:16] for x in xs)
    free = sum(1 for x in xs if not x.get("isSoldOut"))
    return (f"{len(xs)} séance(s) à {', '.join(cines)}, "
            f"de {times[0]} à {times[-1]} — {free} dispo")

# ── état ──────────────────────────────────────────────────────────────────
try:
    with open(STATE_FILE, encoding="utf-8") as f:
        st = json.load(f)
except (OSError, ValueError):
    st = {}
st.setdefault("known", [])
st.setdefault("soldout", {})
st.setdefault("had_any", False)
st.setdefault("checked_hos", [])

# ── séances ───────────────────────────────────────────────────────────────
sessions = get(f"Sessions/BE/NL/{CID}/WWW/Cinema/KinepolisBelgium") or []
known = set(st["known"])
s70 = [x for x in sessions if "70mm" in norm(x)]
new70 = [x for x in s70 if key(x) not in known]
freed = [x for x in s70
         if st["soldout"].get(key(x)) and not x.get("isSoldOut")]

if new70:
    push("IMAX 70MM — Dune 3 (GitHub)",
         f"Séances IMAX 70MM en vente : {summarize(new70)}. Fonce !",
         URL_FILM, True)
elif freed:
    push("Places liberees — Dune 3 (GitHub)",
         f"Des places 70MM se libèrent : {summarize(freed)}. Fonce !",
         URL_FILM, True)
if sessions and not st["had_any"] and not new70:
    push("Vente ouverte — Dune 3 (GitHub)",
         f"Premières séances en vente (pas encore de 70MM) : "
         f"{summarize(sessions)}. Le 70MM peut suivre de très près.",
         URL_FILM, False)

st["had_any"] = st["had_any"] or bool(sessions)
st["known"] = sorted(known | {key(x) for x in sessions})
st["soldout"] = {key(x): bool(x.get("isSoldOut")) for x in s70}

# ── découverte de nouvelles fiches ────────────────────────────────────────
checked = set(st["checked_hos"])
if not checked:
    # Premier passage : on marque l'existant sans alerter.
    checked = set(get("search/BE/NL/WWW?search=dune"))
else:
    try:
        for ho in [h for h in get("search/BE/NL/WWW?search=dune")
                   if h not in checked][:10]:
            checked.add(ho)
            try:
                ti = (get(f"Details/BE/NL/{ho}/WWW").get("title") or "")
            except Exception:
                checked.discard(ho)
                continue
            print(f"nouvelle fiche {ho} : {ti}")
            if DISCOVER_RE.search(ti):
                push("Nouvelle fiche Dune 3 (GitHub)",
                     f"Kinepolis a créé une fiche « {ti} » ({ho}) — vérifie "
                     "le site, vente spéciale possible.",
                     "https://kinepolis.be/nl", False)
    except Exception as e:
        print(f"découverte KO : {e}")
st["checked_hos"] = sorted(checked)

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(st, f, indent=1)

if "--hello" in sys.argv:
    push("Veille cloud OK (GitHub)",
         f"Test réussi : GitHub Actions atteint l'API Kinepolis "
         f"({len(sessions)} séance(s) Dune 3 actuellement) et ntfy. "
         "Vérification toutes les ~5 min, Mac allumé ou pas.",
         URL_FILM, False)

print(f"OK — {len(sessions)} séances, {len(s70)} en 70mm "
      f"({len(new70)} nouvelles), {len(freed)} libérées")
