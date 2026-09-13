# SageMath — Docker Deployment

Start with [RUNNING.md](RUNNING.md) for the tested no-pull launcher, correct
Python invocation, and agent instructions. `python3 sage.py doctor` checks the
installed image; `python3 sage.py --help` lists all modes. These instructions
supersede the old unauthenticated Compose setup.

**Image:** `sagemath/sagemath:latest` (10.8, Dec 2025)  
**Use the installed prebuilt image. Never build Sage from source.**

---

## Optional explicit installation on a new machine

```bash
docker pull sagemath/sagemath:latest
```

Only do this if the image is absent and downloading it is approved. The tested
launcher and Compose configuration never pull automatically. Tags can change;
`sage.py` resolves and reports the installed immutable image ID.

---

## Usage

### Interactive REPL (one-off)
```bash
docker compose run --rm cli
# → drops you into sage: prompt
```

### One-shot command
```bash
docker compose run --rm cli sage -c "from sage.all import *; print(factor(2^64-1))"
```

### Run a .sage or .py file
Put your script in `notebooks/` (mounted as `/work` inside container):
```bash
docker compose run --rm cli sage /work/myscript.sage
docker compose run --rm cli sage -python /work/myscript.py
```

### Interactive IPython REPL (Sage-aware, Python style)
```bash
docker compose run --rm python
# → drops you into IPython with ALL Sage objects already imported
# No `from sage.all import *` needed — it's already done
# Use factor(), matrix(), var(), etc. directly
# Full Python syntax, tab completion, ?, ??
```

> **Implementation note:** Uses `sage -ipython` internally. SageMath ships its
> own Python venv at a non-standard path — there is no `python3` on the system
> PATH that has access to Sage packages. `sage -ipython` sets up the full
> environment correctly. Running the bare venv python3 without `sage` fails on
> Singular and other native libs.

### Jupyter Notebook server (persistent)
```bash
docker compose up -d jupyter
docker compose logs jupyter  # get token; open it on http://localhost:8889
# Stop:
docker compose down
```

### Using the Makefile (convenience wrappers)
```bash
make jupyter      # start jupyter + prints "→ http://localhost:8889"
make jupyter-logs # tail jupyter logs
make cli          # interactive Sage REPL
make python       # interactive Python3 REPL
make down         # stop all services
```

---

## Two ways to use it

### 1. `docker compose run` (CLI / scripts) — best for scripting
- Spins up a fresh container, runs your command, exits
- No persistent state between runs (unless you mount a volume)
- Use this for one-off computations or running `.sage` scripts
- No port needed

### 2. `docker compose up jupyter` (server) — best for exploration
- Persistent Jupyter server, keep it running
- Use browser at http://localhost:8889
- Supports Sage worksheets + Python notebooks
- Port 8889 (not 8888, to avoid conflict with Cadabra)

---

## Python3 vs Sage REPL — which to use?

| Use case | Command |
|---|---|
| Sage-native syntax (`factor()`, `matrix()`, symbolic math) | `make cli` or `docker compose run --rm cli` |
| Python/IPython REPL with Sage objects (all preloaded) | `make python` — everything already imported, Python syntax |
| Running a `.py` file | `docker compose run --rm python sage -python /work/file.py` |
| Running a `.sage` file | `docker compose run --rm cli sage /work/file.sage` |
| Notebook / interactive exploration | `make jupyter` → http://localhost:8889 |

**Note:** Both `make cli` (Sage REPL) and `make python` (IPython) have all Sage objects preloaded.
The difference is prompt style: `sage:` vs IPython `In [1]:`. IPython gives you tab-completion, `?`/`??` help, and cleaner Python syntax.

---

## Calling sage non-interactively from host scripts

```bash
# Evaluate an expression and get stdout
docker run --rm --pull=never --network=none sagemath/sagemath:latest sage -c "
from sage.all import *
print(factor(x^4 - 1))
"

# Or via docker compose:
docker compose run --rm cli sage -c "from sage.all import *; print(matrix([[1,2],[3,4]]).eigenvalues())"
```

---

## Notes
- `notebooks/` dir is auto-created by docker compose as a bind mount → `/work`
- Jupyter port is **8889** (8888 reserved for Cadabra2)
- Jupyter uses its generated authentication token and publishes only on 127.0.0.1
- `restart: unless-stopped` on jupyter service — survives reboots
- Image is ~3GB, no rebuild ever needed; update with `docker pull sagemath/sagemath:latest`
