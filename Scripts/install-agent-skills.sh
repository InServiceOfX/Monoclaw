#!/usr/bin/env bash
# Install canonical agent skills (shared/openclaw/skills/*) into local AI
# harness skill directories: Claude Code, Grok, hermes-agent.
#
# Idempotent: re-run after every pull. Installed copies are always
# overwritten from the canonical, Git-versioned source — edit the canonical
# SKILL.md, never the installed copy.
#
# Override target locations with:
#   CLAUDE_SKILLS_DIR (default: ~/.claude/skills)
#   GROK_SKILLS_DIR   (default: ~/.grok/skills)
#   HERMES_SKILLS_DIR (default: ~/.hermes/skills/media — hermes groups by category)
# Set a variable to an empty string to skip that harness.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANONICAL="$REPO_ROOT/shared/openclaw/skills"

CLAUDE_DIR="${CLAUDE_SKILLS_DIR-$HOME/.claude/skills}"
GROK_DIR="${GROK_SKILLS_DIR-$HOME/.grok/skills}"
HERMES_DIR="${HERMES_SKILLS_DIR-$HOME/.hermes/skills/media}"

install_skill() {
  local src="$1" dest_parent="$2"
  local name dest
  name="$(basename "$src")"
  dest="$dest_parent/$name"
  mkdir -p "$dest_parent"
  rm -rf "${dest:?}"
  cp -R "$src" "$dest"
  printf '\n> Installed copy. Canonical source: `Monoclaw/shared/openclaw/skills/%s/SKILL.md` — edit there and re-run `Scripts/install-agent-skills.sh`.\n' \
    "$name" >> "$dest/SKILL.md"
  echo "installed: $name -> $dest"
}

found=0
for skill in "$CANONICAL"/*/; do
  skill="${skill%/}"
  [ -f "$skill/SKILL.md" ] || continue
  found=1
  for target in "$CLAUDE_DIR" "$GROK_DIR" "$HERMES_DIR"; do
    [ -n "$target" ] && install_skill "$skill" "$target"
  done
done

if [ "$found" -eq 0 ]; then
  echo "no skills found under $CANONICAL" >&2
  exit 1
fi

echo
echo "Done. Codex and other AGENTS.md-driven harnesses read skills directly"
echo "from $CANONICAL (see Monoclaw AGENTS.md, 'Shared Agent Skills')."
