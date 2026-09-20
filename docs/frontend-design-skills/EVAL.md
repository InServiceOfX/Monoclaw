# Design-Skill Eval Loop (the whichai.dev method)

whichai.dev is a one-person eval harness: **one fixed brief × every model ×
every skill variant → side-by-side → a human votes**. It is the same shape as
WebDev Arena (pairwise vote, Bradley-Terry) collapsed to what one person can
run in an afternoon. This doc turns it into a repeatable loop so that changing
a design skill, a CLAUDE.md rule, or a model is a measured decision instead of
a vibe.

It plugs into the 5-layer self-improving loop in
[`../self-improving-agents/`](../self-improving-agents/QUICKSTART.md): the
"measure" layer for anything visual, which is otherwise the hardest thing to
put a number on.

## The matrix

```
axes:
  brief:    B1..Bk   (fixed prompts, checked into the repo)
  model:    M1..Mm   (whatever the harnesses on this machine can drive)
  skill:    none | frontend-design | design-taste-frontend | <candidate>
  iteration: 1..n    (same cell re-run; measures variance, not skill)
cell = one generated page, stored as a self-contained HTML file
```

Keep `k` small (2–3 briefs), `m` to what you actually run day to day, and
skill to 3–4 variants. That's 20–40 pages, which one person can rank in an
hour.

## Briefs

whichai.dev's single brief, reproduced so results are comparable:

> Design the landing page for a note-taking application. Produce N
> iterations, each reachable from a `pages/` directory, with a button to
> switch between them.

Add briefs that look like *your* work, or you are measuring the wrong thing.
For this workspace the obvious ones are:

- **Portfolio** — a personal site for a physicist-turned-engineer with a
  projects grid, a writing index, and a contact block (`repos/claw-portfolio`).
- **Dashboard** — dense, data-heavy internal tool: a table of runs, a
  detail pane, a status strip (`repos/claw-dj` control surface, any
  `llm-dashboard`-style page).
- **Short-form deck** — a 9:16 title card + three body cards for a video
  (`docs/shortform/`).

Store briefs as `eval/briefs/<slug>.md`. A brief is frozen once it has
results against it; write a new one rather than editing.

## Generating cells

Each harness can run headless. The skill is injected by having the harness's
user-level skills dir contain only the variant under test, or (simpler and
more reproducible) by pasting the SKILL.md into the prompt. Prompt-paste is
what whichai.dev does and it removes "did the harness actually load the skill"
as a confound.

```bash
# claude code, one cell
claude -p "$(cat skills/frontend-design/SKILL.md)

$(cat eval/briefs/portfolio.md)

Write the result as a single self-contained index.html." \
  --output-format text > eval/out/portfolio/claude-opus-5/frontend-design/1/index.html

# codex
codex exec "<same prompt>"
# hermes
hermes chat -Q --query-file eval/prompts/portfolio+frontend-design.md
# grok
grok -p "<same prompt>"   # or --prompt-file
```

Naming: `eval/out/<brief>/<model>/<skill>/<iteration>/index.html`. Screenshot
each with Playwright or `chromium --headless --screenshot` at 1440×900 and
390×844 so you can rank from thumbnails and check responsive behaviour in the
same pass.

## Ranking

Do not score cells in isolation; pairwise is faster and more consistent. For
each brief, show two cells (blind: hide the model/skill path), pick the
better one or "tie", log it as one row:

```
brief,left,right,winner,voter,ts
portfolio,claude-opus-5/frontend-design/1,claude-opus-5/none/1,left,ernest,2026-09-20T...
```

Roughly `3 × cells` random pairs per brief is enough to get a stable
Bradley-Terry ordering; `pip install choix` and `choix.ilsr_pairwise` gives
you scores in five lines. Report per-brief, then pooled.

Rubric for the vote, borrowed from whichai.dev and Anthropic's skill, so
"better" means the same thing across sessions:

1. Distinct — could you tell this apart from the default model output?
2. Coherent — one palette, one type system, one layout idea carried through.
3. Not a tell — none of the listed AI-generated tropes (cream + serif +
   terracotta; near-black + acid accent; single accented headline word;
   all-caps eyebrows; 01/02/03 markers on non-sequences; fade-up on every
   section; hover transition on every card).
4. Copy — placeholder text reads like a person wrote it for this product.
5. Works — builds, no console errors, usable at 390 px.

`5` is a gate, not a score: a page that doesn't build loses every pair
(WebDev Arena's 26 % "both bad" ties were mostly this).

## Reading the result

- **Skill vs none, same model**: this is the number that decides whether a
  skill stays installed. If `frontend-design` doesn't beat `none` on your
  briefs for your daily model, uninstall it; it's costing context.
- **frontend-design vs design-taste-frontend**: they disagree on process
  (plan-then-build vs dial-tuning). Expect the winner to depend on the brief:
  Taste tends to win landing pages, Anthropic's tends to win dashboards and
  anything with real content. Record which, and route by brief type.
- **Iteration variance**: if `iteration 1` vs `iteration 2` of the same cell
  flips the result, the skill isn't doing anything; the model is.
- **Model vs model**: sanity-check against Agent Arena. If your ordering is
  wildly different from theirs, suspect your briefs before suspecting them.

## Closing the loop

Once a matrix exists, any change to a design skill is a new column, not a
rewrite. Concretely:

1. Fork `skills/taste-skill/skills/taste-skill/SKILL.md` to a candidate name
   (`design-taste-frontend-ernest`), edit.
2. Run the matrix with `skill = candidate` only (reuse the existing cells for
   the other columns).
3. Vote. Promote if it wins; otherwise keep the diff in `eval/rejected/` with
   the score so the same idea isn't re-tried next month.

This is the monitoring-agent pattern from
[`../self-improving-agents/`](../self-improving-agents/) applied to taste:
the agent can generate and screenshot every cell overnight; only the vote
needs a human, and a vote is ~2 s per pair.

## What is *not* worth automating

- LLM-as-judge for the vote. Every model in whichai.dev's rankings is also a
  plausible judge, and they share the same tells; you'll get the same trope
  scored highly by the model that produces it. Keep the human in the vote,
  automate everything around it.
- More than ~4 skill columns at once. The ranking noise grows faster than the
  information.
