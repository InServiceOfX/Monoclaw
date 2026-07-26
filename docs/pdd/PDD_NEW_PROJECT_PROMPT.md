# Start PDD on a New Project

Paste this once into the AI agent working on the new project:

```text
Set this project up to use Prompt-Driven Development. I’ll describe the product
in ordinary language; preserve my requests and handle the PDD mechanics for me.
```

Then describe what you want:

```text
I want the product to ...
```

That is enough to begin. You do not need to write a PRD, user-story syntax,
`.prompt` files, `.pddrc`, `architecture.json`, command flags, internal
component names, or test filenames.

The agent should:

1. Read the workspace and repository instructions.
2. Read [`PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md`](PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md)
   and [`PDD_WITH_ANY_AGENT_HARNESS.md`](PDD_WITH_ANY_AGENT_HARNESS.md).
3. Inspect the project and installed `pdd` command.
4. Preserve your ordinary-language request as durable, human-readable intent.
5. Draft `docs/PRODUCT_INTENT.md` (or use the repository's equivalent) and
   explain its interpretation for review.
6. Create and maintain versioned PDD `.prompt` files as the operative source
   for each PDD-generated part. Present their purpose, behavior, `MUST` and
   `MUST NOT` rules, assumptions, and tests for human review. Do not stop after
   writing a PRD or stories.
7. Handle PDD configuration, architecture, stories, contracts, code, and tests
   internally.
8. Ask before external actions such as posting a GitHub issue.
9. Report what changed in prompt source, what was generated, what was tested,
   and what remains uncertain.

After the project is configured for PDD, do not repeat the setup prompt.
Continue talking normally:

```text
Add ...
```

```text
Actually, change ...
```

```text
Remove ...
```

```text
Never allow ...
```

The agent should treat those later messages as additions, corrections,
removals, and constraints; preserve the accepted changes; update the affected
versioned `.prompt` source; and route them through PDD without requiring
another magic phrase. See [`PDD_AFTER_SETUP.md`](PDD_AFTER_SETUP.md) for this
ongoing loop.
