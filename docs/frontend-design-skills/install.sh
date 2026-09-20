#!/usr/bin/env bash
# Install the vendored frontend-design skills into every local AI harness.
#
#   ./install.sh                  # curated set -> all harnesses found on this machine
#   ./install.sh --all            # every Taste Skill variant, not just the curated set
#   ./install.sh --only claude    # one harness: claude | hermes | openclaw | codex | grok
#   ./install.sh --dry-run        # print what would be copied
#
# Idempotent: re-running overwrites the same target dirs (rsync --delete per skill).
# Skill dir name == `name:` in SKILL.md frontmatter, which is what every harness
# here keys on (Claude Code, Grok, Codex, Hermes, OpenClaw all discover
# <skills-dir>/<name>/SKILL.md).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/skills"

ALL=0; DRY=0; ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) ALL=1 ;;
    --dry-run) DRY=1 ;;
    --only) ONLY="$2"; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

# Upstream folder names under skills/taste-skill/skills/. Curated = the ones
# that generate code and don't need an image-gen tool.
CURATED=(taste-skill redesign-skill soft-skill minimalist-skill brutalist-skill output-skill)
EVERYTHING=(taste-skill taste-skill-v1 gpt-tasteskill image-to-code-skill redesign-skill
            soft-skill output-skill minimalist-skill brutalist-skill stitch-skill
            imagegen-frontend-web imagegen-frontend-mobile brandkit)
# Codex gets the two variants Leonxlnx wrote for GPT/Codex on top of the curated set.
CODEX_EXTRA=(gpt-tasteskill image-to-code-skill)

skill_name() {  # frontmatter `name:` of a SKILL.md
  awk '/^---$/{c++; next} c==1 && /^name:/{sub(/^name:[ \t]*/,""); print; exit}' "$1"
}

# Harness -> user-level skills directory. Only ones that exist get installed to.
declare -a HARNESSES=()
h_dir() {
  case "$1" in
    claude)   echo "$HOME/.claude/skills" ;;
    hermes)   echo "$HOME/.hermes/skills/frontend-design" ;;   # Hermes groups by category dir
    openclaw) echo "$HOME/.openclaw/workspace/skills" ;;
    codex)    echo "$HOME/.codex/skills" ;;
    grok)     echo "$HOME/.grok/skills" ;;
  esac
}
h_present() {
  case "$1" in
    claude)   [[ -d "$HOME/.claude" ]] ;;
    hermes)   [[ -d "$HOME/.hermes/skills" ]] ;;
    openclaw) [[ -d "$HOME/.openclaw/workspace" ]] ;;
    codex)    [[ -d "$HOME/.codex" ]] ;;
    grok)     [[ -d "$HOME/.grok" ]] ;;
  esac
}
for h in claude hermes openclaw codex grok; do
  [[ -n "$ONLY" && "$ONLY" != "$h" ]] && continue
  h_present "$h" && HARNESSES+=("$h") || echo "skip $h (not set up here)"
done

copy_skill() {  # copy_skill <src-dir-with-SKILL.md> <dest-skills-dir>
  local src="$1" dest_root="$2" name
  name="$(skill_name "$src/SKILL.md")"
  [[ -z "$name" ]] && { echo "  !! no name: in $src/SKILL.md" >&2; return 1; }
  local dest="$dest_root/$name"
  if (( DRY )); then echo "  $src -> $dest"; return; fi
  mkdir -p "$dest"
  rsync -a --delete "$src/" "$dest/"
  echo "  $name"
}

for h in "${HARNESSES[@]}"; do
  root="$(h_dir "$h")"
  echo "== $h -> $root"
  mkdir -p "$root" 2>/dev/null || true
  if [[ "$h" == hermes && ! -f "$root/DESCRIPTION.md" && $DRY -eq 0 ]]; then
    printf -- '---\ndescription: Frontend / web-UI design skills (Anthropic frontend-design, Leonxlnx Taste Skill). Vendored from Monoclaw docs/frontend-design-skills.\n---\n' > "$root/DESCRIPTION.md"
  fi
  # Anthropic frontend-design: Claude Code gets it as the official plugin instead (see below),
  # so skip the raw copy there to avoid a duplicate skill name.
  if [[ "$h" != claude ]]; then
    copy_skill "$VENDOR/frontend-design" "$root"
  fi
  set_="${CURATED[*]}"; (( ALL )) && set_="${EVERYTHING[*]}"
  [[ "$h" == codex && $ALL -eq 0 ]] && set_="$set_ ${CODEX_EXTRA[*]}"
  for folder in $set_; do
    copy_skill "$VENDOR/taste-skill/skills/$folder" "$root"
  done
done

# Claude Code: the official plugin (same SKILL.md, but tracked/updated by `claude plugin`).
if printf '%s\n' "${HARNESSES[@]}" | grep -qx claude && command -v claude >/dev/null; then
  echo "== claude plugin: frontend-design@claude-plugins-official"
  if (( DRY )); then echo "  claude plugin install frontend-design@claude-plugins-official"
  elif claude plugin list 2>/dev/null | grep -q 'frontend-design@claude-plugins-official'; then echo "  already installed"
  else claude plugin install frontend-design@claude-plugins-official; fi
fi

echo "done. Hermes: run 'hermes skills list' to confirm; Grok/Codex/Claude pick up on next launch."
