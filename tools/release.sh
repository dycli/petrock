#!/usr/bin/env bash
# Make a release: rebuild both boards stamped with VERSION, regenerate the plates,
# order files and renders, commit them, and tag that exact commit VERSION, so the
# version printed on a board always names the commit holding that board.
#   usage: release.sh VERSION      (e.g. release.sh v3.11)
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=${1:?usage: release.sh VERSION}
if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
  echo "tag $VERSION already exists" >&2; exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "commit or stash your changes first: the release builds from committed sources" >&2; exit 1
fi
export PETROCK_VERSION=$VERSION
for v in single dual; do tools/build.sh $v; tools/fab.sh $v; done
tools/demo.sh
# The stamp read back from both boards must name this release.
for f in pcb/petrock-41.kicad_pcb pcb/dual/petrock-40.kicad_pcb; do
  grep -q "PETROCK-4[01] $VERSION\"" "$f" || { echo "$f: stamp isn't $VERSION" >&2; exit 1; }
done
git add -A
git commit -q -m "Release $VERSION"
git tag "$VERSION"
git push && git push origin "$VERSION"
echo "released $VERSION: the boards in tag $VERSION say $VERSION"
