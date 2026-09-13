# Run SageMath without building it

The preferred entry point is `sage.py` (host Python standard library + Docker).
It works from any directory. No host Sage installation, provider key, or
persistent notebook server is needed for calculations.

From this directory:

```sh
python3 -B sage.py doctor
python3 -B sage.py eval 'print(factor(2^64 - 1))'
python3 -B sage.py run examples/exact_checks.py
python3 -B sage.py repl
```

Batch commands are noninteractive, have networking disabled, preserve the
program's exit status, and default to a 180-second deadline. `doctor` prints
JSON with Sage's actual version and an exact determinant check. `run` streams
the script's stdout unchanged; the launcher reports the resolved image ID on
stderr. Every invocation uses a fresh named container and removes it on exit.
Timeout/interrupt cleanup stops only that invocation's container.

## Your own Python or Sage files

```sh
python3 /absolute/path/to/sage.py --workdir /absolute/path/to/study run check.py
python3 /absolute/path/to/sage.py --workdir /absolute/path/to/study run derivation.sage
```

The script must lie beneath the selected workdir, including after resolving
symlinks. Python uses `sage -python`: write `from sage.all import ...` and use
`**` for powers. `.sage` and `eval` use the Sage preparser (`^` means power).
Do not substitute the image's bare `python3` for `sage -python`.

Only this workdir is mounted, read-only by default. Use a small study directory,
not your entire home or workspace. For intentional result files, choose scratch
storage outside Git and add `--write`. Files are owned by your host UID/GID.
Add `--timeout 600` before `run` for longer calculations. Arguments after the
script filename are passed to it. `--dry-run` prints the Docker command without
contacting Docker or starting anything.

## Jupyter for human exploration

Choose writable scratch storage outside the checkout, then:

```sh
mkdir -p /tmp/sage-notebooks
python3 -B sage.py --workdir /tmp/sage-notebooks --write jupyter
```

For durable notebooks replace `/tmp/sage-notebooks` with a persistent directory.
Keep the terminal open. Copy the token printed by Jupyter and use it at
`http://127.0.0.1:8889`; container URLs may show internal port 8888, so replace
that port with 8889. Ctrl+C stops this session. A conflicting port fails rather
than stopping someone else's server; choose `--port 18889` if needed.

Authentication stays enabled and Docker publishes only on loopback. Jupyter
containers retain ordinary outbound networking for interactive use; batch
containers do not. Neither mode mounts credentials or the Docker socket.
Do not disable authentication or expose ports to the LAN as an agent workaround.

## For another AI agent

Read AGENTS.md; use `doctor` followed by `run`, not a notebook UI, for automated
work. Check exit status, parse the script's JSON if it supplies it, and record
the image ID, Sage version, inputs, exact identities and numerical tolerances.
Never treat a transport/exit success as general mathematical proof or physical
validation. The included example checks polynomial factorization and a matrix
inverse over the rationals.

Propulsion's Reading Room has its own consumer helpers:
`Studies/verify.py` records symbolic/numerical evidence and
`ReadingRoom/sage_session.py` mounts its study sources read-only beside scratch
notebooks. Both reuse the same prebuilt image; neither builds another Sage.

## Image and Compose

The host's existing `sagemath/sagemath:latest` resolved to Sage 10.8 in testing.
Use `--image sha256:...` for reproducibility. If absent, the launcher fails;
it never pulls or builds. Installing/updating a prebuilt image is a separate,
explicit action. There is no need to touch a running llama.cpp server or GPU.

The retained Compose interface now also uses `pull_policy: never`, token
authentication and `127.0.0.1:8889`. For background Jupyter:

```sh
mkdir -p /tmp/sage-compose-notebooks
export NOTEBOOKS=/tmp/sage-compose-notebooks
docker compose up -d jupyter
docker compose logs jupyter
docker compose stop jupyter
```

Compose uses the image's user rather than host UID/GID; ensure NOTEBOOKS is
writable by that user, or prefer `sage.py`. Compose is a separate lifecycle:
`sage.py` never stops its services. Do not start both on port 8889.

## Deployment inventory (2026-09-06)

Tracked configuration searches found this as the standalone Sage Docker setup
in Monoclaw, with Sage usage notes under Python/SageMath. No equivalent tracked
deployment was found in InServiceOfX. Propulsion's new consumer launchers
are not independent image builds. Untracked/inaccessible
directories are not covered by that inventory.

Work lives in the original Monoclaw repository under
`Deployments/DockerBuilds/Math/SageMath`, on `feat/sage-agent-launcher`.
The temporary clone was unnecessary: the read-only restriction was the agent's
sandbox view, not the host drive. No merge to master has been performed.
