# Frontend Design Skills

Everything an AI agent or harness needs to make web UI that does not look
AI-generated: two open-source skill sets vendored with pinned commits, an
installer for every local harness, and a cheap eval loop for telling whether a
skill actually helped.

Origin: three links shown to Ernest during an Inversion Space onsite
(2026-09-19, see `docs/RawNotes.md`). Analysis of each is in
[§ Source links](#source-links).

```
docs/frontend-design-skills/
├── README.md            this file
├── EVAL.md              whichai.dev-style eval loop (the self-improvement angle)
├── install.sh           copy skills into claude / hermes / openclaw / codex / grok
└── skills/
    ├── UPSTREAM.md      pinned commits + licenses
    ├── frontend-design/ Anthropic's skill (Apache-2.0)
    └── taste-skill/     Leonxlnx's Taste Skill, 13 variants (MIT)
```

## TL;DR for an agent

1. Building or restyling a web page, component, landing page, dashboard,
   poster, or artifact? Load **one** design skill before writing code:
   - `frontend-design` (Anthropic) — plan palette / type pairing / layout /
     one signature element first, then build. Best general default. Explicitly
     lists the current "AI tells" (cream + serif + terracotta, near-black +
     acid green, single accented headline word, all-caps labels, 01/02/03
     markers, fade-up-on-every-section) so you can avoid them.
   - `design-taste-frontend` (Taste Skill v2) — reads the brief, infers a
     design language, then tunes three 1–10 dials: `DESIGN_VARIANCE`,
     `MOTION_INTENSITY`, `VISUAL_DENSITY`. Ships GSAP skeletons and a hard
     pre-flight checklist. Stronger opinions, more "agency landing page".
2. Restyling something that already exists? `redesign-existing-projects`
   (audit first, then fix).
3. Want a specific register? `minimalist-ui` (Linear/Notion editorial),
   `high-end-visual-design` (soft, expensive, whitespace),
   `industrial-brutalist-ui` (Swiss type, hard contrast).
4. Model truncating or leaving `// ...rest of component` placeholders?
   `full-output-enforcement`.
5. On Codex/GPT specifically: `gpt-taste` (stricter variant written for it)
   and `image-to-code` (generate a reference image first, then implement).
6. Don't stack `frontend-design` and `design-taste-frontend` in one run; they
   disagree on process. Pick one, or A/B them per [`EVAL.md`](EVAL.md).

Every SKILL.md is self-contained; if a harness has no skill loader, paste the
file into the system prompt or the first turn.

## Install

```bash
docs/frontend-design-skills/install.sh            # curated set, every harness present
docs/frontend-design-skills/install.sh --all      # all 13 Taste Skill variants
docs/frontend-design-skills/install.sh --only hermes
docs/frontend-design-skills/install.sh --dry-run
```

Idempotent (rsync per skill). Target dir name is the `name:` in each
SKILL.md's frontmatter, which is the key every harness below dedups on.

| Harness | Where it lands | Notes |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/<name>/` + plugin `frontend-design@claude-plugins-official` | Plugin is the official channel for Anthropic's skill (`claude plugin update` tracks it), so the raw copy is skipped there. |
| Hermes | `~/.hermes/skills/frontend-design/<name>/` | Category dir with a `DESCRIPTION.md`; shows as source `local` in `hermes skills list`. |
| OpenClaw | `~/.openclaw/workspace/skills/<name>/` | Workspace skills dir. |
| Codex | `~/.codex/skills/<name>/` | Also gets `gpt-taste` and `image-to-code`. |
| Grok | `~/.grok/skills/<name>/` | Grok also scans `~/.claude/skills/` (`[compat.claude] skills = true`) and dedups by name, higher tier wins. |

Curated set = the six code-generating Taste variants that need no image tool:
`design-taste-frontend`, `redesign-existing-projects`, `high-end-visual-design`,
`minimalist-ui`, `industrial-brutalist-ui`, `full-output-enforcement`.
`--all` adds `design-taste-frontend-v1`, `gpt-taste`, `image-to-code`,
`stitch-design-taste`, `imagegen-frontend-web`, `imagegen-frontend-mobile`,
`brandkit`. The imagegen/brandkit ones only produce images and need an
image-generation tool in the harness.

Upstream one-liners, if you'd rather not use the vendored copies:

```bash
npx skills add https://github.com/anthropics/skills --skill frontend-design
npx skills add https://github.com/Leonxlnx/taste-skill                     # all
npx skills add https://github.com/Leonxlnx/taste-skill --skill design-taste-frontend
claude plugin install frontend-design@claude-plugins-official
hermes skills install https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/taste-skill/SKILL.md --category frontend-design
```

## Source links

### 1. WebDev Arena — https://arena.ai/blog/webdev-arena

Crowd-voted leaderboard for LLM web-dev. Two models build the same Next.js app
from a user prompt inside E2B Firecracker microVMs; users vote; Bradley-Terry
produces the ranking. Launched Dec 2024, ~80k votes at time of the post.

Worth keeping:
- Prompt mix: Website Design 15.3 %, Game Dev 12.1 %, Clones 11.6 % — i.e.
  "make it look good" is the single largest category of what people ask
  coding models for.
- **Unstructured output beat structured JSON output by +13 to +89 Arena
  points** across every model tested. If you are forcing a JSON schema around
  code generation, you are paying for it.
- 26 % tie rate, mostly "both bad" from dependency failures / compile errors:
  build-breaks dominate design quality in voter perception.

Leaderboard itself is stale (Claude 3.7 Sonnet era). Methodology is the value.

### 2. Agent Arena — https://arena.ai/leaderboard/agent/overall

Agentic-coding leaderboard: 46 models, 1.85 M sessions, scored on confirmed
task success, user-satisfaction ratio, steerability, bash-command recovery,
tool-hallucination rate. Snapshot 2026-09-19: Fable 5.1 (Max) 13.7 %,
GPT 6 Astra (Max) 11.5 %, Opus 5 (High) 10.3 %, Opus 5 (Max) 10.2 %,
Fable 5 (High) 8.8 %, Opus 4.8 (High) 8.2 %, GPT 5.6 Sol 7.1 %, Kimi K3 6.2 %,
Sonnet 5 (High) 6.0 %, GPT 5.5 5.0 %.

Use: periodic reference when choosing a model for a harness, particularly the
non-obvious signals (bash recovery, tool hallucination) that matter more for
long autonomous loops than raw benchmark scores. Nothing to download.

### 3. whichai.dev — https://www.whichai.dev

By Dara A. (@daradoescode). One fixed brief ("design the landing page for a
note-taking application, N iterations reachable from `pages/`, a button to
switch between them") run across ~15 models in four groups:
`without-design-skill`, `with-design-skill` (Anthropic), `with-taste-skill`,
`with-ui-sh-skill`. Side-by-side compare view, a "guess which model" game, and
a rankings page the author labels "taste, not a formal benchmark" (Fable 5.1 >
Opus 5 > Kimi K3 > GLM 5.3 Flash > Gemini 3.8 Flash > Grok 4.6 > GPT-5.6 Sol >
Sonnet 5).

The three skills it compares, and why only two are here:

| Skill | Author | License | Vendored |
| --- | --- | --- | --- |
| `frontend-design` | Anthropic ([anthropics/skills](https://github.com/anthropics/skills)) | Apache-2.0 | yes |
| Taste Skill ([tasteskill.dev](https://www.tasteskill.dev/)) | Leonxlnx ([Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), ~88k stars) | MIT | yes |
| [ui.sh](https://ui.sh/) | Adam Wathan & Steve Schoger (Tailwind / Refactoring UI) | paid, invite-only, token-gated `npx` install | no |

ui.sh's nine skills (Design, Ideas, Brand Kit, Componentize, Canonicalize
Tailwind, Add Dark Mode, Dark Mode Image, Make Responsive, Markup From Image)
are a useful checklist of *tasks* a design skill set should cover even if you
don't buy it; the free `redesign-existing-projects` + `image-to-code` cover
about half.

The real takeaway from whichai.dev is the **method**, not the ranking:
fixed brief × models × skill variants × human taste vote is a complete,
cheap eval harness for prompt/skill changes. That's [`EVAL.md`](EVAL.md).

## Updating the vendored copies

```bash
cd "$(mktemp -d)"
git clone --depth 1 https://github.com/Leonxlnx/taste-skill
git clone --depth 1 --filter=blob:none --sparse https://github.com/anthropics/skills anthropic-skills
git -C anthropic-skills sparse-checkout set skills/frontend-design
D=<monoclaw>/docs/frontend-design-skills/skills
cp anthropic-skills/skills/frontend-design/{SKILL.md,LICENSE.txt} $D/frontend-design/
rsync -a --delete taste-skill/skills/ $D/taste-skill/skills/
rsync -a --delete taste-skill/research/ $D/taste-skill/research/
cp taste-skill/{LICENSE,README.md,CHANGELOG.md} $D/taste-skill/
```

Then update the commit hashes in `skills/UPSTREAM.md`, re-run `install.sh`,
and (Claude) `claude plugin update frontend-design@claude-plugins-official`.
