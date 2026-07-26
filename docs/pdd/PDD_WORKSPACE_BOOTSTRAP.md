# Bootstrapping PDD Rules into an AI Workspace

This document defines how an AI agent or harness discovers Ernest's PDD
operating rules.

## Assumed workspace

Every agent session is opened at or inside:

```text
/Users/ernestyeung/.openclaw/workspace
```

That workspace contains:

```text
workspace/
├── AGENTS.md
├── CLAUDE.md
├── PDD.md
└── repos/
    ├── Monoclaw/
    │   └── docs/pdd/
    │       ├── PDD_WORKSPACE_BOOTSTRAP.md
    │       ├── PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md
    │       ├── PDD_WITH_ANY_AGENT_HARNESS.md
    │       ├── PDD_START_HERE.md
    │       └── PDD_CONCEPTS_AND_USER_STORIES.md
    └── PromptDrivenDevelopment/
        └── pdd/
```

The globally available `pdd` executable is built/installed from Ernest's PDD
fork under `repos/PromptDrivenDevelopment/pdd`.

## Separation of responsibilities

The two repositories have different jobs:

```text
Monoclaw docs                 PDD fork
--------------------------    -------------------------
agent operating policy        CLI implementation
natural-language intake       commands and libraries
workflow and safety rules     PDD runtime behavior
human explanations            tests and package source
portable/versioned guidance   executable installed tool
```

The PDD source checkout does not control how an arbitrary AI harness behaves.
An agent does not need to read policy from the PDD fork merely because that
fork produced the `pdd` executable.

Monoclaw is the canonical, Git-versioned home for Ernest's agent-facing PDD
rules. Workspace-root instruction files are small bootstrap shims that point
agents to those Monoclaw documents.

## The required discovery chain

```text
AI harness starts in workspace
        |
        v
harness loads a root instruction file
        |
        v
root instruction requires workspace/PDD.md
        |
        v
PDD.md requires the Monoclaw agent playbooks
        |
        v
agent interprets ordinary product intent and invokes pdd
```

The required agent read order is:

1. `/Users/ernestyeung/.openclaw/workspace/PDD.md`
2. `repos/Monoclaw/docs/pdd/PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md`
3. `repos/Monoclaw/docs/pdd/PDD_WITH_ANY_AGENT_HARNESS.md`
4. installed `pdd <relevant-command> --help`

Read as needed:

- `PDD_START_HERE.md` — human-facing explanation;
- `PDD_CONCEPTS_AND_USER_STORIES.md` — deeper concepts and source walkthrough.

`PDD_START_HERE.md` is not sufficient by itself as an agent policy. It explains
the experience but does not contain every execution, safety, failure, and
evidence rule.

## Root instruction invariant

Every supported harness bootstrap must communicate this invariant:

```text
Before product-intent or coding work, inspect the target repository for PDD
ownership (.pddrc, architecture.json, prompts, matching .prompt files, or
explicit instructions). If PDD applies, read workspace/PDD.md and the mandatory
Monoclaw playbooks it names before acting.

In a PDD-managed project, ordinary product requests, corrections, removals,
examples, and constraints are sufficient intent input. No PDD trigger phrase
is required. Preserve accepted intent durably, discover internal targets and
commands automatically, and report human meaning, semantic validation, and
executable evidence separately. Do not require the user to learn PDD terms,
commands, flags, or filenames.
```

## Harness adapters

No Markdown file can control a harness that never loads it. The bootstrap step
is therefore harness-specific, while the detailed policy remains shared.

### Codex and AGENTS-aware harnesses

Keep the invariant in:

```text
/Users/ernestyeung/.openclaw/workspace/AGENTS.md
```

Codex discovers applicable `AGENTS.md` files by directory scope. More specific
repository/directory instructions may add rules but must not silently discard
the workspace PDD invariant.

### Claude Code

Keep a short equivalent pointer in:

```text
/Users/ernestyeung/.openclaw/workspace/CLAUDE.md
```

It should require `AGENTS.md` and `PDD.md`, then let the Monoclaw playbooks own
the detail.

### Gemini/Antigravity

Use a workspace-root `GEMINI.md` containing the same pointer when the harness
loads that filename.

### Cursor

Use an always-applied project rule under:

```text
/Users/ernestyeung/.openclaw/workspace/.cursor/rules/
```

The rule should point to `PDD.md`, not duplicate the full PDD policy.

### Grok Build or another harness

Configure its workspace/project instruction surface to load `AGENTS.md` or
`PDD.md`. If it has no automatic instruction-file convention, include one
bootstrap instruction in its session/system configuration:

```text
Read and follow /Users/ernestyeung/.openclaw/workspace/AGENTS.md before acting.
```

Opening a shell in the workspace is not by itself proof that a harness reads
workspace Markdown.

## Why pointers are better than duplicated rules

Root harness files should be small:

- easier to verify that the harness loaded them;
- less likely to diverge across Claude, Codex, Cursor, and other tools;
- detailed rules remain Git-versioned in Monoclaw;
- updating Monoclaw updates every harness on the machine without reinstalling
  the PDD CLI.

Do not copy the full natural-language playbook into every harness file. Point
all harnesses at the same canonical document.

## Porting to another computer

1. Recreate the all-encompassing workspace path or update the root pointers.
2. Clone Ernest's Monoclaw repository.
3. Clone Ernest's PDD fork.
4. Install the fork's `pdd` command globally/editably.
5. Install or copy the small workspace-root harness bootstrap files.
6. Verify each harness actually loads its root instruction surface.

The Monoclaw commits preserve the canonical policy. The bootstrap shims are the
small machine-local integration layer.

## Verification

For each harness, start a fresh session at the workspace root and ask:

> In a PDD-managed project, what must I say before describing a correction, and
> which workspace documents govern your behavior?

A correctly bootstrapped agent should answer:

- no recurring PDD trigger phrase is required;
- ordinary corrections/removals/etc. are intent input;
- `workspace/PDD.md` is the workspace router;
- the natural-language and agent-harness playbooks in Monoclaw are mandatory;
- the PDD fork supplies the executable, not the harness policy.

If the answer relies only on general model knowledge or only on
`PDD_START_HERE.md`, the bootstrap is incomplete.
