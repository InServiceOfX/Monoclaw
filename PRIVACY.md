# Privacy Policy for Public Repo Work

Monoclaw is intended to be a public demonstration repo for local, semi-autonomous
software work. Code in this repo may read private data from Ernest's local
workspace at runtime, but private data must not be committed or described with
exact values.

## Public Boundary

Public and commit-safe:

- Source code
- Configuration that contains no secrets or private values
- Documentation describing architecture, commands, and data flow
- Generic examples that do not come from private files
- Statements such as "validated against local Schwab exports"

Private and not commit-safe:

- Files under `/Users/ernestyeung/.openclaw/workspace/Data/Private/`
- Brokerage CSV or JSON rows
- Account identifiers, including masked suffixes
- Exact portfolio values, cash balances, position sizes, cost basis, gain/loss
  amounts, tax-lot details, transaction rows, or portfolio weights
- Screenshots or terminal output that show private financial values
- Commit messages, PR descriptions, or docs that quote exact private values

## Agent Rule

Agents may read private local files when the task requires it, but they must keep
private values out of durable artifacts:

- Do not commit private data.
- Do not paste private values into docs.
- Do not mention exact private numbers in commit messages.
- Do not summarize a change by quoting before/after financial values.
- Do not include raw private rows in tests or fixtures.

Describe behavior instead of values. For example:

- Use: "Added a balances endpoint that reads local Schwab exports at runtime."
- Avoid: "The endpoint reports a cash balance of $X."

## Safer Demo Strategy

For public demos, prefer one of these patterns:

- Keep the real-data dashboard local-only and publish only the source code.
- Add a small synthetic data adapter or fixture set that exercises the same UI
  without representing Ernest's real holdings.
- Make screenshots and videos using synthetic data, not local private data.

The goal is to show that OpenClaw can build useful local software without
turning private local context into public repo history.
