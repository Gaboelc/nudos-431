#!/usr/bin/env bash
# Publica el sitio en la rama gh-pages, que es la que sirve GitHub Pages.
# Uso: scripts/publicar.sh [-m "línea extra del mensaje"]...
# Los argumentos se pasan tal cual a «git commit», por ejemplo para agregar coautores.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
  echo "Publica desde main." >&2; exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "Hay cambios sin commit. Haz commit antes de publicar: el sitio tiene que salir de un estado guardado." >&2
  exit 1
fi
# Se compara con GitHub directamente: un clon superficial puede no tener origin/main.
if [ "$(git rev-parse HEAD)" != "$(git ls-remote origin refs/heads/main | cut -f1)" ]; then
  echo "main no coincide con el main de GitHub. Sube main antes de publicar." >&2; exit 1
fi

python -m nudos sitio --salida build/sitio
version=$(git rev-parse --short HEAD)

wt=$(mktemp -d)
trap 'git worktree remove --force "$wt" 2>/dev/null || true; git worktree prune' EXIT
if git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
  git fetch -q --depth 1 origin gh-pages
  git worktree add -q -B gh-pages "$wt" FETCH_HEAD
else
  git worktree add -q --orphan -b gh-pages "$wt"
fi
find "$wt" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a build/sitio/. "$wt"/
git -C "$wt" add -A
if git -C "$wt" diff --cached --quiet; then
  echo "El sitio publicado ya está al día."
  exit 0
fi
git -C "$wt" commit -q -m "Sitio construido desde $version" "$@"
git -C "$wt" push -q origin gh-pages
echo "Publicado el sitio construido desde $version."
