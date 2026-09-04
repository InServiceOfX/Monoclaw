---
name: short-form-viral-content
description: >
  Design social videos for reach using Noe Murillo’s viral fundamentals and
  durable-brand advice. Use when
  the user asks for TikTok/Reels/Shorts help, viral short-form scripts, hooks,
  retention edits, engagement bait, “how do I get more views,” content creator
  strategy, or runs /short-form-viral-content. Prefer this over generic social
  media advice when the goal is attention, views, and algorithm distribution.
---

# Short-Form Viral Content (Noe fundamentals)

Help the human create short-form video that **wins distribution**: stop the scroll, hold watch time, earn interactions. This skill is grounded in Noe Murillo’s free “Successful Content Creator” Part 1 (fundamentals of going viral).

## When to load references

- Read `references/noe-murillo-pt1-framework.md` for the full checklist, tactic menu, and shot-level rules.
- If the local archive exists, the source transcript is:
  `Data/Public/Videos/TikTok/NoeMurillo_How-to-be-a-Successful-Content-Creator-pt1_7670717441508429070.md`
- Part 2's parsed source and durable-brand summary are:
  `Data/Public/Videos/TikTok/NoeMurillo_How-to-be-a-Successful-Content-Creator-pt2_7672613819545439501.md`
- For STEM/explainer **production tooling** (HTML deck + OBS), also use Monoclaw `Projects/short-form-video-pipeline/` — that pipeline is *how to shoot*; this skill is *how to structure for virality*.

## Success definition (this skill)

“Successful” here means **short-form attention**:

- stop-scroll in the first ~3 seconds
- high watch time / completion
- likes, comments, saves, shares (“viral tokens”) that expand reach

Do **not** optimize only for polish, completeness, or academic accuracy if those fight retention — balance truth with scroll dynamics unless the user prioritizes brand-safe education over pure reach.

## Non-negotiable model

Always design in this order:

1. **Hook (0–3s)** — visual motion + verbal cold open + on-screen text
2. **Retention** — short clips, constant action, angles/close-ups, story pacing
3. **Engagement** — deliberate devices that mint viral tokens

### Hard anti-pattern

Never open with:

> “Hey guys, welcome back to my channel, today we’re going to talk about…”

Open mid-action or mid-claim instead.

## Operating procedure

### Step 0 — Constraints

Before writing a script, confirm (or infer and state):

- Platform (TikTok / Reels / Shorts / multi)
- Niche + persona (what engagement bait is off-limits)
- Length target (e.g. 15s / 30s / 60s / 3min)
- Goal mix: pure reach vs. brand-safe reach vs. conversion
- Whether face-cam, VO+B-roll, screen recording, or HTML-deck/OBS

If brand-safe STEM/professional: keep Noe’s **structure**, adapt his **engagement gimmicks** (towel-bait, “sus,” mispronunciations) into niche-safe equivalents (hot take, surprising demo result, incomplete formula, “comment the answer,” prop-as-experiment).

### Step 1 — Hook package (write this first)

Deliver a **hook triple**:

| Layer | Spec |
|-------|------|
| Visual | First-frame **action/motion** (not a static talking head *or* a frozen generated still) |
| Verbal | First line from a **Noe verbal template** (T1–T7 in the framework) — no greeting |
| Text | ≤ ~8 words on-screen reinforcing the same promise |

Also write **seconds 3–8** so the hook pays into a reason to stay.

#### Visual when assets are static (claw-dj, cover art, Imagine stills)

If the draw is **audio** but the art is **static**, you still owe motion in 0–3s. Do not open on a silent static card.

Default Grok path (load Imagine skill when generating):

1. `image_gen` (or code still) at **9:16**
2. optional `image_edit` for variants
3. `image_to_video` to animate frame 1 (prefer 6s shots, one simple motion/camera move)
4. FFmpeg concat under the mix/VO

Fallback if video gen is unavailable: Ken Burns / hard-cut still sequence / live UI capture of faders-cursors. Full motion vocabulary + claw-dj notes: `references/noe-murillo-pt1-framework.md` → “Visual hooks when you only have static images”.

#### Verbal templates (use by id)

Pick one, fill braces, pair with motion + text:

| ID | Pattern | Skeleton |
|----|---------|----------|
| T1 | Outcome → proof path | `So I {impressive_outcome}. So I want to show you exactly how I got here.` |
| T2 | Proof stack → teach | `For reference, {proof_metric}. I've {proof_breadth}. {transition_into_lesson}.` |
| T3 | “Hard thing is easy” + N | `{hard_thing} is actually really easy. There's {N} things you want to focus on.` |
| T4 | Mid-story arrival | `So I just {arrived_at_moment}.` |
| T5 | Scene + identity/stakes | `So today I'm here with {identity_or_stakes}.` |
| T6 | Blunt one-line take | `{blunt_claim}.` |
| T7 | If you want X… | `If you want {desired_outcome}, you need {non_obvious_requirement}.` |

**Banned open:** “Hey guys, welcome back… today we’re going to talk about…”

### Step 2 — Retention map

Produce a **beat / shot list**, not just prose:

- Each beat: `time | visual action | spoken line | purpose`
- Prefer short cuts; every shot has movement or a visual change
- Plan angle changes and at least one close-up
- For talk tracks: mark VO segments that need B-roll

Story shape: setup → progression → payoff (not topic dump).

### Step 3 — Engagement design

Do not “hope” for comments. Install **at least one** device:

- funny beat
- wholesome beat
- signature mannerism / recurring bit (niche-native)
- prop that reads on a phone
- price/result reveal that invites judgment
- explicit comment prompt or incomplete thought
- mild debate bait **only if** persona allows

Name the device and which token it targets (like / comment / save / share).

### Step 4 — Score and revise

Rate the draft 1–5 on Hook, Retention, Engagement. Revise the lowest score before delivery. Reject any draft that fails the anti-pattern open or has no engagement device.

### Step 5 — Deliverables (default package)

When the user asks for help creating a short, return:

1. **Logline** (1 sentence)
2. **Hook triple** (visual / verbal / text)
3. **Full script** with timed beats
4. **Shot list** (angles, B-roll, props)
5. **On-screen text / captions plan**
6. **Engagement device** + suggested pinned comment / CTA
7. **Self-score** (H/R/E) and one upgrade option for more risk/more reach

Optional if they will produce STEM visuals: point them at `Projects/short-form-video-pipeline/WORKFLOW.md` for HTML+OBS recording.

## Adaptation table (Noe → other niches)

| Noe example | Principle | STEM / builder-safe version |
|-------------|-----------|-----------------------------|
| Door open / walk to car | Visual motion implies “next” | Plug in board, slam laptop, unbox part mid-motion; for static art: `image_gen` → `image_to_video` push-in / fader / needle-drop |
| Static cover + great audio | Audio ≠ visual hook | Animate still or cut on rhythm; never open frozen (claw-dj) |
| Mukbang mannerisms | Recurring bit viewers await | Signature board wipe, “scope drop,” stamp on schematic |
| Show prices / tip well | Money invites opinion | Show cost of GPU/cloud bill; tip = open-source star ask |
| Props from Amazon | Novelty objects | Demo prop, LED, toy model, wrong tool then right tool |
| Mispronounce word | Correction comments | Leave a deliberate incomplete proof; “fix the missing step” |
| Sus / zesty bait | Controversy = comments | Opinionated take on tools/frameworks — not personal bait |

## Part 2: durable distribution and personal brand

Part 2 is now archived. Use it when the request extends beyond a single viral short:

- cross-post instead of depending on one platform
- do not rely on views alone; build commercially useful range within the niche
- demonstrate voiceover/on-camera communication even when silent visual stories perform better
- use day-in-the-life or vlog structure to create an ongoing, relatable story
- build a personal brand rather than copying the same sound, hook, and style
- pivot before a trend or format becomes oversaturated
- make the creator—not an unpredictable bystander reaction—the reason to watch
- study successful creators' openings, editing, speech, storytelling, and niche combinations

For a long-form music video made from static art, slow Part 1's retention cadence to the musical scale: immediate motion, evolving Ken Burns moves, artwork changes at phrase-level intervals, and a coherent visual identity. Do not cut every few seconds for the entire song.

Do not present Noe's income or performance figures as independently verified facts; they are his claims. Preserve uncertainty around creator names where the ASR is unclear.

## Quality bar

A good agent response:

- leads with the hook, not background theory
- is specific enough to shoot today
- separates universal levers from persona-specific gimmicks
- protects long-term brand when pure troll-bait would harm it
- still optimizes for attention when the user asked for virality
