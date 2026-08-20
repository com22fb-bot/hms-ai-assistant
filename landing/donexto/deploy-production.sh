#!/usr/bin/env bash
# Landing pública = Cloudflare Pages Production branch `main`.
# Un deploy sin --branch main queda en Preview y www.donexto.com no cambia.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -a \
  "$ROOT/index.html" "$ROOT/app.js" "$ROOT/styles.css" "$ROOT/favicon.svg" \
  "$ROOT/cookies.html" "$ROOT/privacidad.html" "$ROOT/terminos.html" \
  "$ROOT/brand-escritorio.jpg" "$ROOT/brand-logo-3d.jpg" "$ROOT/brand-youtube.jpg" \
  "$ROOT/brand" "$ROOT/_headers" \
  "$STAGE/"
npx wrangler pages deploy "$STAGE" --project-name=donexto --commit-dirty=true --branch main
