"""Wire the repo's vendored bidi agent into the installed strands package.

This repository vendors the newest Strands bidirectional (bidi) agent under
``strands-py/src/strands/experimental/bidi``. We must USE that code — not the
older copy bundled with the pip release. The pip ``strands-agents`` package
still provides the core (types, tools, hooks); we simply make Python resolve
``strands.experimental.bidi`` (and its hook events) from the vendored tree
first by prepending the vendored directory to ``strands.experimental.__path__``.

Import this module BEFORE importing anything from ``strands.experimental.bidi``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VENDORED_EXPERIMENTAL = REPO_ROOT / "strands-py" / "src" / "strands" / "experimental"

if not (VENDORED_EXPERIMENTAL / "bidi").is_dir():
    raise RuntimeError(
        f"vendored bidi agent not found at {VENDORED_EXPERIMENTAL / 'bidi'} — "
        "the backend must run from within the RandD repository"
    )

import strands.experimental  # noqa: E402

# Prepend so the vendored bidi subpackage shadows the pip copy.
_vendored = str(VENDORED_EXPERIMENTAL)
if _vendored not in strands.experimental.__path__:
    strands.experimental.__path__.insert(0, _vendored)

# Drop any already-imported pip copies so the vendored tree wins.
for _name in list(sys.modules):
    if _name.startswith("strands.experimental.bidi"):
        del sys.modules[_name]
