# SageMath deployment

Read README.md and PROGRESS.md. This directory is maintained Python/configuration,
not PDD-generated code. Work in the original Monoclaw repository on a feature
branch; do not merge/push without Ernest's direction. A read-only sandbox view
does not establish that the host drive is read-only: request authorized access
before diagnosing a filesystem fault or making another checkout.

- Prefer `python3 sage.py doctor`, then `eval` or `run` for agent computations.
- Use only an already installed prebuilt Sage image. No source build, implicit
  pull, package installation, provider call, or persistent server is required.
- Batch containers have no network and mount only the selected work directory,
  read-only unless `--write` was explicitly requested. Never mount the Docker
  socket, entire home/workspace, credentials, or unrelated private data.
- `.py` files use `sage -python`; `.sage` and `eval` use Sage preprocessing.
  Python powers are `**`; Sage-preparsed powers may use `^`.
- Keep generated notebooks/results in a user-selected scratch directory outside
  Git. Use authenticated, loopback-only `jupyter` for human exploration only.
  Do not disable its token or paste the token into durable logs/docs.
- Run `python3 -B -m unittest discover -s tests -v` for command-policy tests.
  Run `doctor` and `run examples/exact_checks.py` for actual Sage verification.
  Update PROGRESS.md with the tested image/version and real limitations.

See the sibling README for commands callable from any agent harness. A Sage
kernel is a computation tool, not an autonomous agent or proof of physical validity.
