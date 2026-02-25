# Task: Cadabra2 Docker + Spinor Physics Examples

## Context

This is the Monoclaw repo (`git@github.com:InServiceOfX/Monoclaw.git`), Ernest Yeung's
personal sandbox. Current branch: `feat/cadabra2-docker-and-spinors`.

**Reference repos (read-only, DO NOT PUSH to these):**

- `/home/propdev/.openclaw/workspace/workspace2/repos/InServiceOfX/RustLibraries/docker_builder/` — Rust docker build tool
- `/home/propdev/.openclaw/workspace/workspace2/repos/InServiceOfX/RustLibraries/docker_runner/` — Rust docker run tool (richer RunConfiguration)
- `/home/propdev/.openclaw/workspace/workspace2/repos/InServiceOfX/Deployments/DockerContainers/Builds/` — YAML config examples

**All new work goes in this repo (Monoclaw).**

Cargo is at `~/.cargo/bin/cargo` — source `~/.cargo/env` or use full path.

---

## Task 1: Port + Improve docker_builder to Monoclaw

### What to do

Create `Rust/docker_builder/` in this repo by porting the docker_builder crate from InServiceOfX, BUT with the following improvements:

1. **Richer RunConfiguration** — the `docker_runner` crate (InServiceOfX) has a much better `RunConfiguration` with fields: `gpus`, `shm_size`, `ports`, `volumes`, `env`, `ipc`, `command`. Merge this into the `run_docker_configuration.rs` of the new docker_builder (replace the old minimal one with the richer version). Adapt the run command builder accordingly.

2. **Keep all existing features** from docker_builder: build subcommand (YAML-driven Dockerfile assembly from components), run subcommand (volumes, ports, GPU, X11/gui, audio, interactive, detached, entrypoint, network).

3. **Compile and pass all tests**: `cargo build` and `cargo test` must succeed.

Structure:
```
Rust/docker_builder/
  Cargo.toml
  src/
    main.rs
    lib.rs
    configuration.rs
    configuration/
      build_docker_configuration.rs
      run_docker_configuration.rs    ← use docker_runner's richer version
    build_docker.rs
    build_docker/
      build_docker.rs
      build_docker_command.rs
      create_dockerfile.rs
    run_docker.rs
    run_docker/
      run_docker.rs
      build_docker_run_command.rs
```

**Important**: Make the run command builder read `gpus`, `shm_size`, `ipc`, `env`, `command` from the YAML run_configuration.yml (using the docker_runner RunConfiguration fields). So the run subcommand can now be configured entirely from YAML (like docker_runner) OR from CLI flags (like the old docker_builder). CLI flags override YAML where both exist.

---

## Task 2: Cadabra2 Docker Build

### Build instructions research

Check the official Cadabra2 build instructions. The GitHub repo is: https://github.com/kpeeters/cadabra2

For Ubuntu 24.04, the dependencies are typically (from their INSTALL.md on GitHub or cadabra.science):
```
apt-get install -y cmake python3-dev g++ libpcre3-dev libgmp-dev libgtk-3-dev
  libboost-all-dev libgmp-dev uuid-dev python3-pip git
  libmicrohttpd-dev libwebsocketpp-dev
  python3-matplotlib python3-sympy
  libsqlite3-dev libboost-python-dev
  qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools
  libgl1-mesa-dev
```

Actually, check the ACTUAL dependencies by reading their GitHub README or CMakeLists.txt. The key point: we want the FULL build including the graphical notebook UI (NOT just Jupyter/CLI).

### What to create

Create `Deployments/DockerBuilds/Physics/Cadabra2/` with:

1. **Dockerfile** — Ubuntu 24.04 base. Install all build dependencies. Clone cadabra2 from https://github.com/kpeeters/cadabra2. Build from source with cmake. Install. The notebook UI requires GTK3 and display support. Keep the image lean but complete.

2. **build_configuration.yml** — following the InServiceOfX pattern:
   ```yaml
   docker_image_name: cadabra2-ubuntu:24.04
   base_image: ubuntu:24.04
   dockerfile_components:
     - label: "Dockerfile"
       path: "Dockerfile"
   ```

3. **run_configuration.yml** — for running with X11:
   ```yaml
   docker_image_name: cadabra2-ubuntu:24.04
   volumes:
     - host_path: /tmp/.X11-unix
       container_path: /tmp/.X11-unix
   env:
     DISPLAY: ":0"
   ```

4. **run_gui.sh** — convenience script that:
   - Runs `xhost +local:docker` 
   - Runs docker with X11 and correct display env

### Dockerfile requirements for Cadabra2 GUI

The Cadabra2 notebook interface needs:
- GTK3 (`libgtk-3-dev`, `libgtk-3-0`)
- Display/X11 access at runtime (NOT at build time — no Xvfb needed in image)
- The `cadabra2` binary and `cadabra2-gtk` (or whatever the GUI binary is called post-install)

### Build it!

After creating the Dockerfile and configs, BUILD the Docker image. Use docker directly:
```bash
cd Deployments/DockerBuilds/Physics/Cadabra2/
docker build -t cadabra2-ubuntu:24.04 -f Dockerfile .
```

If it fails, debug and fix. Keep trying until it succeeds. Read the build output carefully. Common issues:
- Missing apt package names (they change between Ubuntu versions)
- CMake find_package failures (install the missing -dev package)
- Python binding issues (ensure libboost-python3-dev or equivalent)

**This step is critical — the build must succeed before moving on.**

Once built, test that the cadabra2 binary exists:
```bash
docker run --rm cadabra2-ubuntu:24.04 which cadabra2
docker run --rm cadabra2-ubuntu:24.04 cadabra2 --version
```

---

## Task 3: Cadabra2 Examples — Spinor Technology (Srednicki Ch.34-38)

### Background

Cadabra is a computer algebra system designed for quantum field theory. It supports:
- Tensor algebra with index manipulation
- Spinor indices (dotted and undotted)
- Gamma matrices / Clifford algebras
- Fierz identities
- Python-based scripting (`.py` files that import `cadabra2`) and the notebook format (`.cnb`)

### What to create

Create `Python/Cadabra2/spinors/` with:

1. **`01_weyl_spinors.py`** — Introduction to 2-component (Weyl) spinors in cadabra2:
   - Define undotted spinor indices α, β, γ, δ (SL(2,C) fundamental rep)
   - Define dotted spinor indices α̇, β̇, γ̇, δ̇ (SL(2,C) conjugate rep)
   - Define the ε (epsilon) tensors ε_αβ, ε^αβ for raising/lowering
   - Show index raising/lowering with ε
   - Define 2-component Weyl spinors ψ_α, χ^α
   - Compute spinor products: ⟨ψ χ⟩ = ε^αβ ψ_α χ_β and [ψ χ] = ε_α̇β̇ ψ̄^α̇ χ̄^β̇
   - Verify antisymmetry: ⟨ψ χ⟩ = -⟨χ ψ⟩

2. **`02_sigma_matrices.py`** — σ^μ and σ̄^μ matrices (Srednicki's notation):
   - Define σ^μ_αα̇ and σ̄^{μ α̇α}
   - σ^μ = (1, σ^i), σ̄^μ = (1, -σ^i) 
   - Verify: σ^μ_αα̇ σ̄_μ^{β̇β} = -2 δ_α^β δ^β̇_α̇
   - Momentum spinors: p_αα̇ = p_μ σ^μ_αα̇

3. **`03_spinor_helicity.py`** — Spinor-helicity formalism:
   - For massless momentum p^μ, define angle spinor λ_α and square spinor λ̃_α̇
   - p^μ p_μ = 0 ↔ det(p_αα̇) = 0 ↔ p_αα̇ = λ_α λ̃_α̇
   - Define ⟨ij⟩ = ε^αβ λ_α^i λ_β^j and [ij] = ε_α̇β̇ λ̃^α̇i λ̃^β̇j
   - Mandelstam variables: s_ij = ⟨ij⟩[ji]
   - Show momentum conservation: Σ p_i = 0 implies Σ_i ⟨ji⟩[ik] = 0

4. **`04_mhv_amplitudes.py`** — MHV (Maximally Helicity Violating) amplitudes:
   - The Parke-Taylor formula: A_n(1^-, 2^-, 3^+, ..., n^+) = ⟨12⟩^4 / (⟨12⟩⟨23⟩...⟨n1⟩)
   - Implement for n=4: A_4(1^-, 2^-, 3^+, 4^+) = ⟨12⟩^4 / (⟨12⟩⟨23⟩⟨34⟩⟨41⟩)
   - Verify crossing symmetry and cyclic invariance
   - Comment/document the connection to Srednicki Ch.38

5. **`05_fierz_identities.py`** — Fierz rearrangement (Srednicki uses these in loop calculations):
   - σ^μ_αα̇ σ_μ^{ββ̇} = -2 δ_α^β δ^β̇_α̇
   - (σ^μ σ̄^ν + σ^ν σ̄^μ)_α^{β} = -2 η^{μν} δ_α^β
   - Fierz identity for 4-spinor products

6. **`README.md`** in `Python/Cadabra2/spinors/`:
   - Explain what these files demonstrate
   - Reference Srednicki QFT chapters 34-38 (2-component spinors) 
   - Reference the MHV literature (see Task 4 below)
   - How to run: `docker run --rm -v $(pwd):/work cadabra2-ubuntu:24.04 python3 /work/04_mhv_amplitudes.py`

**Note on cadabra2 Python API**: When running `.py` files with cadabra2, you import the `cadabra2` module. The core class is `Ex` (expression). Declarations use `__cdbkernel__`. Look at the cadabra2 source in the Docker image for examples, or check https://cadabra.science/notebooks.html for notebook examples.

---

## Task 4: MHV Amplitudes — References & Connection

### Research

Search the web and arxiv for:
1. A good introductory/tutorial reference on MHV amplitudes and spinor-helicity formalism
2. The Parke-Taylor formula original paper
3. Connection between MHV amplitudes and twistor theory (Witten, 2004)
4. The BCFW recursion relation (Britto-Cachazo-Feng-Witten)

Save a `Python/Cadabra2/spinors/REFERENCES.md` with:
- Full citations (arxiv IDs where available)
- 1-2 sentence summary of each reference
- Which is most accessible for a physics grad student who knows Srednicki QFT

---

## Task 5: Commit Everything

When all the above is done, commit to branch `feat/cadabra2-docker-and-spinors`:

```bash
git add -A
git commit -m "feat(cadabra2): docker build from source + spinor-helicity cadabra2 examples

- Port improved docker_builder from InServiceOfX to Rust/docker_builder/
  (richer RunConfiguration: gpu, shm_size, env, ipc, command from YAML)
- Deployments/DockerBuilds/Physics/Cadabra2/: Ubuntu 24.04 Dockerfile
  building cadabra2 from source with GTK3 notebook UI support
- Python/Cadabra2/spinors/: Weyl spinors, σ-matrices, spinor-helicity,
  MHV/Parke-Taylor amplitudes, Fierz identities in cadabra2 Python API
- REFERENCES.md: key MHV amplitude papers with summaries"
```

Then push:
```bash
git push -u origin feat/cadabra2-docker-and-spinors
```

---

## Completion Notification

When completely finished (ALL tasks done, pushed), run:
```bash
openclaw system event --text "Done: cadabra2 docker build + spinor examples complete on feat/cadabra2-docker-and-spinors. Docker image built successfully, Parke-Taylor + Fierz examples written, MHV refs saved." --mode now
```

If the Docker build fails after multiple attempts and you're stuck, run:
```bash
openclaw system event --text "BLOCKED: cadabra2 docker build failing — need Ernest's help. Issue: [brief description of the error]. Everything else (Rust port, YAML configs, Python examples) is done and committed." --mode now
```
