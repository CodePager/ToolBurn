#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${TOOLBURN_BIN_DIR:-/usr/local/bin}"
TARGET="$BIN_DIR/toolburn"

mkdir -p "$BIN_DIR"
cat >"$TARGET" <<SH
#!/usr/bin/env bash
set -euo pipefail
exec "$ROOT/toolburn" "\$@"
SH
chmod 755 "$TARGET"

printf 'installed %s -> %s/toolburn\n' "$TARGET" "$ROOT"
"$TARGET" --help >/dev/null
