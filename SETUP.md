# Veille cloud via GitHub Actions (Mac éteint ⇒ toujours alerté)

Vérifie l'API Kinepolis **toutes les ~5 min** depuis les serveurs GitHub
(gratuit) et pousse les alertes ntfy sur ton iPhone. Totalement
indépendant de ton Mac. Mêmes alertes que le bot local, dédupliquées via
`state.json` commité dans le repo.

## Mise en route (~5 min, une seule fois)

```bash
brew install gh
```

```bash
gh auth login
```
(choisis GitHub.com → HTTPS → Login with a web browser, et suis le lien)

```bash
cd ~/CLAUDE/kinepolis-bot/cloud-github && ./setup.sh
```

`setup.sh` crée le repo **public** `kinepolis-dune3-watch` (rien de
sensible dedans : le script + un état anonyme ; le nom du sujet ntfy est
lu dans `../config.py` et rangé dans un *secret* GitHub, jamais commité),
pousse le code, et déclenche un run de test → tu reçois
« **Veille cloud OK (GitHub)** » sur l'iPhone.

Pourquoi public ? Les minutes GitHub Actions sont **illimitées et
gratuites** sur les repos publics → cron à 5 min. Si tu préfères un repo
privé : `./setup.sh --private`, et passe le cron de `*/5` à `*/30` dans
[.github/workflows/watch.yml](.github/workflows/watch.yml) (quota privé
gratuit : 2000 min/mois).

## Suivi / entretien

```bash
gh run list --workflow watch.yml --limit 5
```

- Test manuel : `gh workflow run watch.yml -f hello=true`
- Stop : `gh workflow disable watch.yml` (ou supprime le repo)
- ⚠️ Repo public : GitHub coupe les crons après **60 jours sans
  activité** ; le bot committant `state.json` à chaque changement, le
  plus sûr est de vérifier `gh run list` une fois par mois (ou n'importe
  quel petit commit relance le compteur).

## Latence des couches (toutes en parallèle, même sujet ntfy)

| Couche | Fréquence | Tourne où | Condition |
|---|---|---|---|
| Bot local (`watcher.py`) | ~60 s | ton Mac | Mac allumé, capot ouvert |
| GitHub Actions (ce dossier) | ~5 min (souvent 5–15 min réels) | GitHub | rien |
| Routine cloud Claude | 1 h | cloud Anthropic | rien |
