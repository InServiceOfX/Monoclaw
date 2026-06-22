# AGENTS.md — working conventions for AvionicsHIL

**Read this before touching anything.** These are the user's standing rules. A lower-cost model
picking up this project will not have the user's memory context — this file is that context.
Violating these wastes the user's time and money.

---

## Git
- **Never commit or push to `master` or `main`.** The user merges manually.
- You may create and push **feature branches** (`feat/avionics-hil-...`).
- Commit messages end with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (or your model's tag).
- Do not commit unless the user asks. Default to leaving changes uncommitted on a feature branch.

## Python
- **Use `uv` virtual environments only. Never system `pip`/`pip3`. The user despises conda — never suggest it.**
- Pattern: `uv venv .venv --python 3.13 && source .venv/bin/activate && uv pip install <pkg>`.
- A reusable venv with `pdfplumber`/`pandas`/`openpyxl`/`pypdfium2`/`pillow` already exists at
  `Embedded/JetsonOrinNano/.venv` — reuse it for doc-parsing/vision-crop work.
- For BBB/Jetson on-target Python, create a venv on that board (don't pollute system Python).

## Filesystem / repo
- `workspace2` is a **symlink** to `/media/propdev/Expansion/openclaw/.openclaw/workspace`.
  `workspace2/...` and `/media/propdev/Expansion/...` are the **same files**. Editing one edits both.
- This project lives at `repos/Monoclaw/Embedded/AvionicsHIL/`.
- Reference data is under `Data/Public/...`. **`Data/Private/...` paths must NEVER appear in public
  repos, commits, examples, or tests** — the word "Private" in a path is the signal. Use generic
  placeholders. (Everything this project needs is in `Data/Public/`.)

## Hardware safety
- See [HARDWARE.md](HARDWARE.md) §7. In short: **3.3 V logic only**, common ground first,
  power down before rewiring, one I²C master, verify pins from the CSV/SRM — don't guess.

## Style
- **snake_case** for members/functions; **spell out names** — no C-style abbreviations like
  `numel`/`nbytes`/`buf` where a full word reads better.
- Match the surrounding code's idiom, comment density, and naming.
- Write **explicit, pin-by-pin** hardware instructions (the user asked for this; they are newer
  to bench hardware). Same for any UI steps.
- **Verify file contents before asserting their role** — open a file, don't infer from its name.

## Isaac Sim specifics (the physics stack you depend on)
- Stack: `repos/Monoclaw/Deployments/Stacks/IsaacSim/`. Read its `STATUS_ZUP_PHYSICS.md` first.
- GPU pinning in Docker: **RTX 3060 = GPU 1** for physics (the GTX 980 Ti = GPU 0 is display).
  This is reversed from CUDA enumeration. The compose file sets `GPU_ID=1`.
- Run physics-only headless (`ISAAC_PHYSICS_ONLY=1`, default) — boots in ~15 s; full render hangs on GeForce.
- **Do NOT call `/scene/load` or `/starship/create-stage` at runtime** in physics-only mode — it
  re-inits GLFW and crashes. Scene auto-loads at boot; change USD on disk + restart instead.
- Coordinate frame is **Z-up** (z = altitude). Do not reintroduce Y-up.

## How to work in this project
1. Pick a task from `tasks/` whose dependencies (per ORCHESTRATION.md) are met and that is
   `NOT STARTED` in STATUS.md.
2. Set it `IN PROGRESS` in STATUS.md with your model/session name and the date.
3. Build to the **acceptance criteria** in the brief. Honor [INTERFACES.md](INTERFACES.md) exactly.
4. When you hit a `VERIFY` unknown, resolve it on hardware and **record the answer in STATUS.md**
   (and `config.yaml`) so the next session doesn't re-derive it.
5. When done, set the task `DONE`, append a dated line to the STATUS.md changelog, and note any
   new follow-up tasks.
6. Report honestly: if a test fails, say so with the output. Don't claim done-and-verified unless it is.

## Honesty & scope
- If a planned approach is blocked (e.g., I²C-slave unsupported), say so plainly and fall back to
  the documented alternative (UART). Don't burn days on a yak-shave the plan already flagged.
- Confirming outward/irreversible actions (pushing, deleting, anything touching real hardware in a
  way that could damage it) before proceeding.
