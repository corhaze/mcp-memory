#!/bin/bash
# Install git hooks from scripts/hooks to .git/hooks

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)/hooks"
GIT_HOOKS_DIR="$(git rev-parse --git-dir)/hooks"

if [ ! -d "$GIT_HOOKS_DIR" ]; then
  echo "❌ Error: Not in a git repository"
  exit 1
fi

echo "📦 Installing git hooks..."

for hook in "$HOOKS_DIR"/*; do
  if [ -f "$hook" ]; then
    hook_name=$(basename "$hook")
    target="$GIT_HOOKS_DIR/$hook_name"
    cp "$hook" "$target"
    chmod +x "$target"
    echo "✅ Installed $hook_name"
  fi
done

echo "🎉 All hooks installed successfully!"
