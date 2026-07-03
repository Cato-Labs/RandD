#!/usr/bin/env bash
# Sync vendored AI Elements components (and the shadcn/ui primitives they need)
# from the upstream vercel/ai-elements repository — or from a fork.
#
# Usage:
#   ./scripts/sync-ai-elements.sh
#   AI_ELEMENTS_REPO=ImRonAI/ai-elements ./scripts/sync-ai-elements.sh   # sync from fork
#   AI_ELEMENTS_REF=main ./scripts/sync-ai-elements.sh                   # pin a branch/tag
#
# The script downloads the repo tarball, copies the elements we consume into
# frontend/src/components/ai-elements/, copies the required shadcn/ui primitives
# into frontend/src/components/ui/, and rewrites the monorepo import aliases so
# upstream updates land with zero manual edits. See DESIGN.md §1.
set -euo pipefail

REPO="${AI_ELEMENTS_REPO:-vercel/ai-elements}"
REF="${AI_ELEMENTS_REF:-main}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend/src"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# AI Elements components used by this app (chat + voice), incl. internal deps.
ELEMENTS=(
  chain-of-thought task tool web-preview image attachments agent
  canvas node edge connection controls panel toolbar
  plan queue prompt-input conversation message artifact sandbox
  persona audio-player mic-selector speech-input transcription
  jsx-preview voice-selector
  shimmer code-block
)

# shadcn/ui primitives the components above import.
UI=(
  accordion badge button button-group card collapsible command dialog
  dropdown-menu hover-card input input-group popover scroll-area select
  separator spinner tabs textarea tooltip kbd label
)

echo "Syncing AI Elements from $REPO@$REF ..."
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$REF" | tar xz -C "$TMP"
SRC="$TMP/$(ls "$TMP")"

mkdir -p "$FRONTEND/components/ai-elements" "$FRONTEND/components/ui" "$FRONTEND/hooks" "$FRONTEND/lib"

rewrite() {
  sed -i \
    -e 's#@repo/shadcn-ui/components/ui/#@/components/ui/#g' \
    -e 's#@repo/shadcn-ui/lib/utils#@/lib/utils#g' \
    -e 's#@repo/shadcn-ui/hooks/#@/hooks/#g' \
    "$1"
}

for c in "${ELEMENTS[@]}"; do
  f="$SRC/packages/elements/src/$c.tsx"
  if [[ -f "$f" ]]; then
    cp "$f" "$FRONTEND/components/ai-elements/$c.tsx"
    rewrite "$FRONTEND/components/ai-elements/$c.tsx"
  else
    echo "WARN: upstream missing element '$c' (renamed upstream?)" >&2
  fi
done

for c in "${UI[@]}"; do
  f="$SRC/packages/shadcn-ui/components/ui/$c.tsx"
  if [[ -f "$f" ]]; then
    cp "$f" "$FRONTEND/components/ui/$c.tsx"
    rewrite "$FRONTEND/components/ui/$c.tsx"
  else
    echo "WARN: upstream missing ui primitive '$c'" >&2
  fi
done

cp "$SRC/packages/shadcn-ui/lib/utils.ts" "$FRONTEND/lib/utils.ts"
if [[ -f "$SRC/packages/shadcn-ui/hooks/use-mobile.ts" ]]; then
  cp "$SRC/packages/shadcn-ui/hooks/use-mobile.ts" "$FRONTEND/hooks/use-mobile.ts"
fi

echo "Done. Review 'git diff frontend/src/components' and run 'npm run build' in frontend/."
