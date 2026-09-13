# SageMath deployment progress

## Completed

- 2026-09-06: added no-pull batch/Jupyter launcher, correct Python invocation,
  authenticated localhost Compose, and executable mathematical smoke checks.
- Branch: `feat/sage-agent-launcher` in the original Monoclaw repository.
  Ernest requested consolidation and removal of the temporary clone. The
  earlier read-only diagnosis was a sandbox-view mistake: host writes work.
  No merge, commit, push, image pull/build, or llama.cpp restart.

## Verification

- Six offline command-policy tests pass; Compose configuration validates.
- Actual `doctor` and Python example pass exact determinant, inverse and
  polynomial checks on Sage 10.8 with installed image
  `sha256:aeef59a8c17212357aeb83bd7f1cfac43bb1c789ae3fa2d887227c763bdfcac3`.
- Live Jupyter smoke returns 403 for unauthenticated API access, stops its
  ephemeral session and verifies the port is closed. Tokens are not printed
  by the smoke test. Its startup polling tolerates transient connection resets.
- The legacy Compose exposed unauthenticated Jupyter on all interfaces;
  the receiving checkout now keeps authentication and binds 127.0.0.1 only.
  Compose was statically validated; the live test exercised the Python launcher.

## Last worked on

2026-09-06. Consolidated into the original repository at
`/media/propdev/Expansion/openclaw/.openclaw/workspace/repos/Monoclaw`.
Transfer manifests and verification are in the main workspace under
`reviews/repository-consolidation-2026-09-06/`. No image was downloaded,
built, or changed. The existing llama.cpp server was left running and untouched.
