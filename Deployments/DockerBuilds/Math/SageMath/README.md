# SageMath — Docker Deployment

**Image:** `sagemath/sagemath:latest` (10.8, Dec 2025)  
**No build from source. No environment headaches. Just pull and run.**

---

## Quick Pull (one-time)

```bash
docker pull sagemath/sagemath:latest
```

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
docker compose run --rm cli python3 /work/myscript.py
```

### Interactive Python3 REPL (with full SageMath available)
```bash
docker compose run --rm python
# → drops you into Python3 with SageMath on PYTHONPATH
# Inside: from sage.all import *; then use sage objects normally
```

### Run a Python script
```bash
docker compose run --rm python python3 /work/myscript.py
```

### Jupyter Notebook server (persistent)
```bash
docker compose up -d jupyter
# Open: http://localhost:8889
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
| Python scripting with Sage objects | `make python` — then `from sage.all import *` |
| Running a `.py` file | `docker compose run --rm python python3 /work/file.py` |
| Running a `.sage` file | `docker compose run --rm cli sage /work/file.sage` |
| Notebook / interactive exploration | `make jupyter` → http://localhost:8889 |

**Note:** In Python3 mode, Sage is NOT auto-imported. You must do `from sage.all import *` manually.
In Sage REPL (`sage:` prompt), everything is pre-imported.

---

## Calling sage non-interactively from host scripts

```bash
# Evaluate an expression and get stdout
docker run --rm -v $(pwd):/work sagemath/sagemath:latest sage -c "
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
- No token/password on Jupyter — local use only, don't expose externally
- `restart: unless-stopped` on jupyter service — survives reboots
- Image is ~3GB, no rebuild ever needed; update with `docker pull sagemath/sagemath:latest`
