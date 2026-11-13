#!/bin/sh
set -e

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -z "$PREFIX" ]; then PREFIX="$HOME/.local"; fi
BIN_DIR="$PREFIX/bin"
LIB_DIR="$PREFIX/lib/machelper"

mkdir -p "$BIN_DIR" "$LIB_DIR"
cp "$ROOT/machelper.py" "$LIB_DIR/machelper.py"
cp "$ROOT/machelper" "$BIN_DIR/machelper"
rm -rf "$LIB_DIR/machelperlib"
cp -R "$ROOT/machelperlib" "$LIB_DIR/machelperlib"
chmod +x "$BIN_DIR/machelper"

echo "Installed MacHelper to $PREFIX"
echo "Add $BIN_DIR to PATH if the machelper command is not found."
echo "Try: machelper doctor"
