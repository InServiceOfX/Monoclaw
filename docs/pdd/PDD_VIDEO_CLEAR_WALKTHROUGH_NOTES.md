# Notes on “Prompt Driven Development: A Clear Walkthrough”

Source video:
[`Prompt Driven Development: A Clear Walkthrough`](https://youtu.be/esZhNrUrul8)
by the Prompt Driven Development channel.

The captions were archived on 2026-07-26 at:

```text
/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/
Prompt_Driven_Development_Prompt_Driven_Development_A_Clear_Walkthrough.json
```

The archive contains a 9:31 transcript with 137 timestamped segments and is
indexed in `Data/Public/youtube-transcripts/index.json`.

## The video's model

The video makes PDD's core idea unusually clear:

- The video describes a prompt as a complete mini-specification and repeatedly
  recommends one prompt per generated code file.
- Tests are guardrails that preserve the required behavior.
- The prompt and tests are the durable “mold.”
- Generated code is the replaceable part produced by that mold.
- “Prompt space” is the layer where maintainers work primarily in prompts and
  tests rather than accumulating direct code patches.
- Chat is a useful interface but a poor source file.
- PDD is best suited to long-lived behavior that must survive future changes;
  short-lived experiments and one-off fixes may still be better handled
  conventionally.

The video also says PDD does not replace architecture, performance budgets, or
security review. It works best at the level of a bounded module rather than as
a substitute for whole-system engineering.

## What this confirms

The video confirms the central correction in
[`PDD_AFTER_SETUP.md`](PDD_AFTER_SETUP.md):

1. Ordinary conversation is valid intake, but it is not the final PDD source.
2. A PRD or Product Intent document can organize the whole product, but it is
   not the artifact PDD compiles for an individual code file.
3. Versioned `.prompt` files and tests are the core maintained PDD layer.
4. User stories help express and independently check desired behavior; they do
   not replace the component prompt.
5. A completed PDD change must move durable discoveries out of chat or code
   patches and back into the prompt/test mold.

## What it changes in our guidance

### Product Intent is helpful, not a PDD requirement

The video does not introduce a PRD as part of the day-to-day PDD mold. Our
`docs/PRODUCT_INTENT.md` convention is therefore an agent-harness aid for
consolidating whole-product meaning, especially during greenfield work or large
changes. It should not become mandatory paperwork for every small request.

For a small change to an established PDD-managed file, the affected `.prompt`
and tests may be the only current-truth artifacts that need modification.

### “One prompt per file” is a convention, not our universal boundary

The video presents “one prompt per code file” as a rule. We do not adopt that
as a universal software-design boundary. C and C++ header/source pairs are an
obvious counterexample: several physical files may implement one coherent
contract and need to regenerate together.

The project-level source is the collective PDD program: its prompt graph,
includes, tests, architecture, and configuration. Within that graph, use the
smallest coherent regeneration and verification boundary. That may be one file
or a multi-file artifact bundle. Avoid both arbitrary per-file fragmentation
and whole-project mega-prompts.

Current PDD implements singular primary outputs, so native atomic bundles would
require a fork enhancement. The current compatibility pattern is a shared
canonical contract included by linked per-output prompts. See
[`PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md).

### User stories are not the main compiler input

At about 4:55, the video says prompts capture items such as contracts, user
stories, and example usage. The current PDD CLI also maintains separate
human-story and generated-contract files. These ideas are compatible:

- user-story intent should influence the relevant prompt;
- the separately authored human story remains an independent oracle that can
  detect prompt drift;
- `pdd story add` is selective acceptance coverage, not the command for every
  change.

This is why “humans control prompts and tests” does not make stories
contradictory. Prompts and tests form the core technical mold. A story is a
small, independently derived check that the mold still represents the original
human request. Human control means authority over the behavioral meaning and
proof, not a requirement to hand-edit every artifact. See
[`PDD_INTENT_FIRST_WORKFLOW.md`](PDD_INTENT_FIRST_WORKFLOW.md) for the simplified
human workflow and proposed CLI facade.

### The “five times smaller” statement is not a universal guarantee

The video illustrates a 4,000-line codebase with 800 lines of mini-spec
prompts. This is a useful example of conceptual compression, not a ratio every
project should promise. PDD's own doctrine describes the exact context-window
magnitudes as a research hypothesis to measure rather than settled data.

## Who writes versus who reviews

An artifact being drafted by an AI does not mean a human can safely ignore it.
PDD moves the human-maintained source layer upward from code to prompts and
tests.

| Artifact | Usually drafted or produced by | Required human relationship |
|---|---|---|
| Ordinary intent message | Human | Say what should happen, change, or stop |
| Product Intent (PRD) | Agent with human input | Product/domain owner reviews current meaning for product-level changes |
| PDD `.prompt` | Developer or AI agent; sometimes bootstrapped by PDD | Accountable human approves its behavioral meaning; technical owner reviews interfaces, dependencies, and critical constraints |
| Human user story | Agent/PDD drafts from independent intent | Human reads and confirms or edits the short story |
| Generated story contract | PDD | Do not hand-edit; agent inspects it and human may review its acceptance meaning |
| Tests | Developer, agent, or PDD | Technical reviewer checks that important behavior and every critical `MUST NOT` are actually covered |
| Generated source code | PDD/LLM | Review and testing are proportional to risk; safety-, security-, and performance-sensitive code still needs direct expert review |
| `.pddrc` and `architecture.json` | PDD/agent | Human approves important architecture and ownership decisions, not necessarily the JSON syntax |
| Evidence and logs | PDD/tooling | Agent summarizes exact results; human evaluates failures, uncertainty, and consequential tradeoffs |

## What the product/domain human should review

The shortest answer is:

> Yes, the human should check the human user story. But the story is not
> enough. The human must also approve the meaning of consequential prompt
> changes because the `.prompt` is the source that will regenerate the code.

The human does not need to write prompt-file syntax. For each meaningful prompt
change, the agent should present a **prompt review card**:

```text
Affected part:
Purpose:
Inputs and outputs:
Behavior added, changed, or removed:
MUST rules:
MUST NOT rules:
Important examples and edge cases:
Dependencies or architectural effects:
Unresolved assumptions:
Tests that prove the change:
```

For routine, low-risk changes, a product/domain human can approve this
plain-language card while a technical agent or reviewer inspects the actual
`.prompt` diff. For consequential behavior, the human should also read the
relevant prompt section directly. Because prompts are natural-language
mini-specifications, that review should be much more approachable than
reviewing generated code.

## What can normally remain mechanical

A product/domain user normally does not need to:

- author `.prompt` syntax;
- select PDD commands or flags;
- hand-edit `.pddrc` or `architecture.json`;
- hand-edit generated story contracts;
- read every line of generated source code;
- read every test implementation;
- inspect raw generation logs.

The AI agent still has to inspect those artifacts. It must translate important
decisions and evidence into ordinary language instead of silently asking the
human to trust generated files.

## Revised post-setup loop

```text
human states or corrects intent
             |
             v
agent drafts the prompt-level change
             |
             v
human approves meaning
             |
             v
agent/PDD regenerates and runs tests
             |
             v
human receives behavioral evidence and remaining uncertainty
```

Product Intent and user stories are added when they improve understanding or
independence. The always-central mold for a PDD-managed generated file is its
prompt plus tests.
