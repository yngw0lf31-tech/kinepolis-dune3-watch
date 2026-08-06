#!/bin/zsh
# Déploie la veille Kinepolis sur GitHub Actions (2 prérequis : gh installé
# + connecté). Usage :
#   ./setup.sh            → repo PUBLIC  (cron 5 min, minutes illimitées)
#   ./setup.sh --private  → repo PRIVÉ   (pense à passer le cron à 30 min,
#                            sinon dépassement des 2000 min/mois gratuites)
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"

VIS="${1:---public}"
REPO="kinepolis-dune3-watch"

command -v gh >/dev/null 2>&1 || {
  echo "❌ GitHub CLI absent. Installe-le d'abord :  brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || {
  echo "❌ Pas connecté. Lance d'abord :  gh auth login"; exit 1; }

[ -d .git ] || git init -q -b main
git config user.name  >/dev/null 2>&1 || git config user.name  "veille-bot"
git config user.email >/dev/null 2>&1 || git config user.email "veille-bot@users.noreply.github.com"
git add -A
git commit -q -m "Veille Kinepolis Dune 3 IMAX 70mm" 2>/dev/null || true

# Le sujet ntfy est lu dans ../config.py et rangé dans un secret GitHub :
# il n'apparaît jamais dans les fichiers commités.
TOPIC=$(cd .. && python3 -c "import config; print(config.NTFY_TOPIC)")
[ -n "$TOPIC" ] || { echo "❌ NTFY_TOPIC introuvable dans ../config.py"; exit 1; }

gh repo create "$REPO" "$VIS" --source . --push
gh secret set NTFY_TOPIC --body "$TOPIC"

echo "⏳ Lancement d'un run de test (notification « Veille cloud OK (GitHub) »)…"
for i in 1 2 3 4 5; do
  sleep 5
  gh workflow run watch.yml -f hello=true 2>/dev/null && break
  echo "   (le workflow n'est pas encore enregistré, nouvel essai…)"
done
echo "✅ Fini. Vérifie ton iPhone d'ici ~2 min, puis suis les runs avec :"
echo "   gh run list --workflow watch.yml"
