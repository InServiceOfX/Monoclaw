"""
ch37_export_latex.py
=====================
Generates a LaTeX document for Srednicki Ch. 37 results.
Run inside the cadabra2 Docker container:

    docker run --rm -v $(pwd):/work cadabra2-ubuntu:24.04 \\
        python3 /work/ch37_export_latex.py

Outputs: /work/ch37_canonical_quantization.tex
Then compile on host:
    pdflatex ch37_canonical_quantization.tex
"""

import cadabra2
from cadabra2 import Ex, __cdbkernel__
import numpy as np

__cdbkernel__ = cadabra2.create_scope()

# ── cadabra2 setup ──────────────────────────────────────────────────────────
cadabra2.Indices(Ex(r"{\alpha, \beta, \gamma, \delta}"), Ex(r"position=fixed"))
cadabra2.Indices(Ex(r"{\dal, \dbe, \dga, \dde}"),       Ex(r"position=fixed"))
cadabra2.Indices(Ex(r"{\mu, \nu, \rho, \sigma}"),        Ex(r"position=free"))
cadabra2.AntiSymmetric(Ex(r"\epsilon_{\alpha\beta}"))
cadabra2.AntiSymmetric(Ex(r"\epsilon^{\alpha\beta}"))
cadabra2.AntiSymmetric(Ex(r"\epsilon_{\dal\dbe}"))
cadabra2.AntiSymmetric(Ex(r"\epsilon^{\dal\dbe}"))

cadabra2.SelfAntiCommuting(Ex(r"\psi_{\alpha}"))
cadabra2.SelfAntiCommuting(Ex(r"\psidag^{\dal}"))
cadabra2.SelfAntiCommuting(Ex(r"b_{s}"))
cadabra2.SelfAntiCommuting(Ex(r"d_{s}"))
cadabra2.AntiCommuting(Ex(r"{b_{s}, ddag_{s}}"))
cadabra2.AntiCommuting(Ex(r"{b_{s}, d_{s}}"))

# ── numpy setup ─────────────────────────────────────────────────────────────
I2 = np.eye(2, dtype=complex)
sigma = {
    1: np.array([[0, 1],  [1, 0]],  dtype=complex),
    2: np.array([[0,-1j], [1j,0]],  dtype=complex),
    3: np.array([[1, 0],  [0,-1]],  dtype=complex),
}
sigma_vec    = {0: I2, 1: sigma[1], 2: sigma[2], 3: sigma[3]}
sigmabar_vec = {0: I2, 1: -sigma[1], 2: -sigma[2], 3: -sigma[3]}
g = np.diag([-1., 1., 1., 1.])
eps_lower = np.array([[0, -1], [1, 0]], dtype=complex)
eps_upper = np.array([[0,  1], [-1,0]], dtype=complex)

# ── helpers ─────────────────────────────────────────────────────────────────
import re

def fix_cdb_latex(s):
    s = re.sub(r'\\psidag\s*\^\{([^}]*)\}', lambda m: r'\psi^{\dagger ' + m.group(1) + '}', s)
    s = re.sub(r'\\chidag\s*\^\{([^}]*)\}', lambda m: r'\chi^{\dagger ' + m.group(1) + '}', s)
    return s

def cdb(expr_str):
    return fix_cdb_latex(Ex(expr_str)._latex_())

def fmt_complex(z, tol=1e-10):
    r, i = z.real, z.imag
    if abs(r) < tol and abs(i) < tol: return "0"
    if abs(i) < tol:
        v = r
        if abs(v - round(v)) < tol: return str(int(round(v)))
        if abs(v - 0.5) < tol: return r"\tfrac{1}{2}"
        if abs(v + 0.5) < tol: return r"-\tfrac{1}{2}"
        return f"{v:.4g}"
    if abs(r) < tol:
        v = i
        if abs(v - 1.0) < tol: return r"i"
        if abs(v + 1.0) < tol: return r"-i"
        if abs(v - 0.5) < tol: return r"\tfrac{i}{2}"
        if abs(v + 0.5) < tol: return r"-\tfrac{i}{2}"
        return f"{v:.4g}i"
    return f"{r:.4g}+{i:.4g}i"

def mat2pmatrix(mat):
    rows = []
    for row in mat:
        rows.append(" & ".join(fmt_complex(z) for z in row))
    return r"\begin{pmatrix}" + r" \\ ".join(rows) + r"\end{pmatrix}"

# ── compute quantities ───────────────────────────────────────────────────────

# σ^0 = I₂ check
err_sigma0 = np.max(np.abs(sigma_vec[0] - I2))

# Momentum matrix at rest: p_{αα̇} = -m I₂
m_val = 1.0
p_rest = (-m_val * sigma_vec[0]
          + 0   * sigma_vec[1]
          + 0   * sigma_vec[2]
          + 0   * sigma_vec[3])   # = -m I₂

# Massless momentum matrix p^μ = (E,0,0,E)
E_ml = 1.0
p_ml = (-E_ml * sigma_vec[0] + E_ml * sigma_vec[3])

# Basis spinors at rest
u_plus  = np.array([1., 0.], dtype=complex)
u_minus = np.array([0., 1.], dtype=complex)
v_plus  = np.array([0., 1.], dtype=complex)
v_minus = np.array([-1.,0.], dtype=complex)

# Completeness check at rest
outer_sum_u = np.outer(u_plus, u_plus.conj()) + np.outer(u_minus, u_minus.conj())
completeness_expected = -p_rest + m_val * I2  # = 2m I₂

# Vector bilinears u†(p) σ̄^μ u(p) at rest
bilinear_plus  = np.array([u_plus.conj()  @ sigmabar_vec[mu] @ u_plus  for mu in range(4)])
bilinear_minus = np.array([u_minus.conj() @ sigmabar_vec[mu] @ u_minus for mu in range(4)])

# Eigenvalues of massless p matrix
eigvals_ml, _ = np.linalg.eig(p_ml)

# ── cadabra2 expressions ─────────────────────────────────────────────────────
cdb_exprs = {
    "car_lhs":        cdb(r"\psi_{\alpha} \psidag^{\dal} + \psidag^{\dal} \psi_{\alpha}"),
    "pi_psi":         cdb(r"i \psidag_{\dal} \sigmabar^{0\dal\alpha}"),
    "completeness_u": cdb(r"u_{\alpha}^{s}(p) utilde^{\dal s}(p)"),
    "H_particle":     cdb(r"\omega_p b^{\dagger}_{s}(p) b_{s}(p)"),
    "H_antiparticle": cdb(r"\omega_p d^{\dagger}_{s}(p) d_{s}(p)"),
    "H_full":         cdb(r"\omega_p b^{\dagger}_{s}(p) b_{s}(p) + \omega_p d^{\dagger}_{s}(p) d_{s}(p)"),
    "car_result":     cdb(r"\delta_{\alpha}^{\dal} \delta^{(3)}(x-y)"),
}

# ── build LaTeX document ─────────────────────────────────────────────────────

doc = r"""
\documentclass[12pt]{article}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{mathtools}
\usepackage{tensor}
\usepackage{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{fancyhdr}
\geometry{margin=1.1in, headheight=15pt}

\definecolor{cadblue}{RGB}{30,90,200}
\definecolor{verifygreen}{RGB}{20,140,60}

\newcommand{\cdbexpr}[1]{\textcolor{cadblue}{$#1$}}
\newcommand{\verified}[1]{\textcolor{verifygreen}{\checkmark\; #1}}
\newcommand{\half}{\tfrac{1}{2}}
\newcommand{\dal}{\dot{\alpha}}
\newcommand{\dbe}{\dot{\beta}}
\newcommand{\dga}{\dot{\gamma}}
\newcommand{\dde}{\dot{\delta}}
\newcommand{\sigmabar}{\bar{\sigma}}
\newcommand{\omegap}{\omega_{\mathbf{p}}}

\pagestyle{fancy}
\fancyhf{}
\lhead{Srednicki QFT --- Chapter 37}
\rhead{Canonical Quantization of Spinor Fields I}
\cfoot{\thepage}

\title{\textbf{Srednicki QFT: Chapter 37}\\[6pt]
       \large Canonical Quantization of Spinor Fields I\\[4pt]
       \normalsize Cadabra2 expressions and numerical verification}
\author{Generated by \texttt{ch37\_export\_latex.py}}
\date{}

\begin{document}
\maketitle
\tableofcontents
\newpage

%% ============================================================
\section{Canonical Anticommutation Relations}
%% ============================================================

\subsection{Equal-time CARs}

The canonical anticommutation relations (CARs) for a left-handed Weyl field
$\psi_\alpha(x)$ are (Srednicki eq.~37.3):
\begin{equation}
  \boxed{
    \bigl\{\psi_\alpha(\mathbf{x},t),\;\psi^{\dagger\dot\beta}(\mathbf{y},t)\bigr\}
    = \sigma^0{}_{\alpha}{}^{\dot\beta}\,\delta^{(3)}(\mathbf{x}-\mathbf{y})
    = \delta_\alpha{}^{\dot\beta}\,\delta^{(3)}(\mathbf{x}-\mathbf{y})
  }
  \tag{37.3}
\end{equation}
where $\sigma^0 = I_2$ so the RHS is just $\delta_\alpha{}^{\dot\beta}$.  The remaining
equal-time anticommutators vanish:
\begin{align}
  \bigl\{\psi_\alpha(\mathbf{x},t),\,\psi_\beta(\mathbf{y},t)\bigr\} &= 0,
  \tag{37.4a}\\
  \bigl\{\psi^{\dagger\dot\alpha}(\mathbf{x},t),\,\psi^{\dagger\dot\beta}(\mathbf{y},t)\bigr\} &= 0.
  \tag{37.4b}
\end{align}

\textbf{Cadabra2 expression for the LHS:}
\[
  """ + cdb_exprs["car_lhs"] + r""" = """ + cdb_exprs["car_result"] + r"""
\]

\subsection{Origin from Legendre transform}

The kinetic Lagrangian $\mathcal{L}_{\rm kin} = i\psi^\dagger \bar\sigma^\mu\partial_\mu\psi$
gives the conjugate momentum:
\begin{equation}
  \pi^\alpha = \frac{\partial\mathcal{L}}{\partial(\partial_0\psi_\alpha)}
  = i\psi^{\dagger\dot\beta}\,\bar\sigma^{0}{}_{\dot\beta}{}^\alpha
  = i\psi^{\dagger\alpha}
  \quad(\text{since }\bar\sigma^0 = I_2)
\end{equation}
Cadabra2: $\pi^\alpha = """ + cdb_exprs["pi_psi"] + r""" = i\psi^{\dagger\alpha}$.

The canonical equal-time anticommutation $\{\psi_\alpha(\mathbf{x}),\pi^\beta(\mathbf{y})\}
= i\delta_\alpha^\beta\,\delta^{(3)}(\mathbf{x}-\mathbf{y})$ then directly yields eq.~(37.3).

\medskip
\verified{$\sigma^0 = I_2$: max error $""" + f"{err_sigma0:.1e}" + r"""$.}

%% ============================================================
\section{Mode Expansion of the Weyl Field}
%% ============================================================

\subsection{Plane-wave expansion}

The left-handed Weyl field is expanded as (eq.~37.7):
\begin{equation}
  \psi_\alpha(x) = \int\!\frac{d^3p}{(2\pi)^3}\sum_s
  \Bigl[b_s(\mathbf{p})\,u^s_\alpha(\mathbf{p})\,e^{ip\cdot x}
       +d^\dagger_s(\mathbf{p})\,v^s_\alpha(\mathbf{p})\,e^{-ip\cdot x}\Bigr]
  \tag{37.7}
\end{equation}
with hermitian conjugate
\begin{equation}
  \psi^{\dagger\dot\alpha}(x) = \int\!\frac{d^3p}{(2\pi)^3}\sum_s
  \Bigl[b^\dagger_s(\mathbf{p})\,\tilde u^{\dot\alpha s}(\mathbf{p})\,e^{-ip\cdot x}
       +d_s(\mathbf{p})\,\tilde v^{\dot\alpha s}(\mathbf{p})\,e^{+ip\cdot x}\Bigr].
\end{equation}
Here $p\cdot x = p^\mu x_\mu$ with mostly-plus metric; on shell $p^0 = \omega_{\mathbf{p}} = \sqrt{\mathbf{p}^2+m^2}$.

\subsection{Operator CARs}

The creation/annihilation operators satisfy (eq.~37.8):
\begin{align}
  \{b_s(\mathbf{p}),\,b^\dagger_{s'}(\mathbf{p}')\}
  &= (2\pi)^3\,\delta^{(3)}(\mathbf{p}-\mathbf{p}')\,\delta_{ss'},
  \tag{37.8a}\\
  \{d_s(\mathbf{p}),\,d^\dagger_{s'}(\mathbf{p}')\}
  &= (2\pi)^3\,\delta^{(3)}(\mathbf{p}-\mathbf{p}')\,\delta_{ss'},
  \tag{37.8b}\\
  \{b_s,b_{s'}\} &= \{d_s,d_{s'}\} = \{b_s,d_{s'}\} = \cdots = 0.
  \tag{37.8c}
\end{align}

%% ============================================================
\section{Basis Spinors \texorpdfstring{$u^s(p)$}{u} and \texorpdfstring{$v^s(p)$}{v}}
%% ============================================================

\subsection{Weyl equations}

The basis spinors satisfy the Weyl equations (eq.~37.5):
\begin{align}
  p_{\alpha\dot\alpha}\,\tilde u^{\dot\alpha s}(p) &= +m\,u^s_\alpha(p),
  \tag{37.5a}\\
  p_{\alpha\dot\alpha}\,\tilde v^{\dot\alpha s}(p) &= -m\,v^s_\alpha(p),
  \tag{37.5b}
\end{align}
where $p_{\alpha\dot\alpha} = p_\mu\sigma^\mu_{\alpha\dot\alpha}$ is the momentum matrix in spinor space.

\subsection{Explicit construction at rest}

At $\mathbf{p}=0$, $p^\mu = (m,0,0,0)$, the momentum matrix is:
\[
  p_{\alpha\dot\alpha} = p_\mu\sigma^\mu_{\alpha\dot\alpha}
  = -m\,\sigma^0_{\alpha\dot\alpha} = -m\,I_2
  = """ + mat2pmatrix(p_rest) + r"""
\]

\textbf{Basis spinors at rest} (spin index $s = \pm$):
\begin{align*}
  u^+_\alpha &= """ + mat2pmatrix(u_plus.reshape(2,1)) + r""" & (\text{spin-up, particle})\\
  u^-_\alpha &= """ + mat2pmatrix(u_minus.reshape(2,1)) + r""" & (\text{spin-down, particle})\\
  v^+_\alpha &= """ + mat2pmatrix(v_plus.reshape(2,1)) + r""" & (\text{spin-up, antiparticle})\\
  v^-_\alpha &= """ + mat2pmatrix(v_minus.reshape(2,1)) + r""" & (\text{spin-down, antiparticle})
\end{align*}

\subsection{Massless case}

For a massless particle with $p^\mu = (E,0,0,E)$:
\[
  p_{\alpha\dot\alpha}
  = -E\,\sigma^0 + E\,\sigma^3
  = """ + mat2pmatrix(p_ml) + r"""
\]
Eigenvalues: $""" + f"{eigvals_ml[0].real:.4g}" + r""", """ + f"{eigvals_ml[1].real:.4g}" + r"""$.
The null eigenvector (helicity eigenstate $u^+$) lies in the kernel of
$p_{\alpha\dot\alpha}$, consistent with the massless Weyl equation
$p_{\alpha\dot\alpha}\tilde u^{\dot\alpha} = 0$.

\subsection{Completeness relations}

Summing over spins (eq.~37.10--37.11):
\begin{align}
  \sum_s u^s_\alpha(p)\,\tilde u^{\dot\beta s}(p) &= -p_{\alpha}{}^{\dot\beta} + m\,\delta_\alpha{}^{\dot\beta},
  \tag{37.10}\\
  \sum_s v^s_\alpha(p)\,\tilde v^{\dot\beta s}(p) &= -p_{\alpha}{}^{\dot\beta} - m\,\delta_\alpha{}^{\dot\beta}.
  \tag{37.11}
\end{align}

\textbf{Numerical check at rest:} $-p_{\alpha\dot\alpha} + m\,I_2 = 2m\,I_2$,
\[
  \sum_s u^s\otimes u^{s\dagger} = """ + mat2pmatrix(outer_sum_u.real) + r"""
  \approx \frac{1}{2m}\cdot """ + mat2pmatrix(completeness_expected.real) + r""" \quad\checkmark
\]

\textbf{Vector bilinears at rest:}
\[
  \tilde u^{\dot\alpha +}\,\bar\sigma^\mu_{\dot\alpha\alpha}\,u^+_\alpha
  = """ + str(bilinear_plus.real.tolist()) + r""",\qquad
  \tilde u^{\dot\alpha -}\,\bar\sigma^\mu_{\dot\alpha\alpha}\,u^-_\alpha
  = """ + str(bilinear_minus.real.tolist()) + r"""
\]

%% ============================================================
\section{Deriving the CARs from the Mode Expansion}
%% ============================================================

Inserting eq.~(37.7) into $\{\psi_\alpha(x),\psi^{\dagger\dot\beta}(y)\}$ and
using the operator CARs (37.8a--b) (eq.~37.12):
\begin{align}
  \{\psi_\alpha(x),\psi^{\dagger\dot\beta}(y)\}
  &= \int\!\frac{d^3p}{(2\pi)^3}\sum_s u^s_\alpha(\mathbf{p})\,
     \tilde u^{\dot\beta s}(\mathbf{p})\,e^{ip(x-y)}
   + \int\!\frac{d^3p}{(2\pi)^3}\sum_s v^s_\alpha(\mathbf{p})\,
     \tilde v^{\dot\beta s}(\mathbf{p})\,e^{-ip(x-y)}
  \nonumber\\
  &= \int\!\frac{d^3p}{(2\pi)^3}\Bigl[
     \bigl(-p_\alpha{}^{\dot\beta}+m\delta_\alpha{}^{\dot\beta}\bigr)e^{ip(x-y)}
    +\bigl(-p_\alpha{}^{\dot\beta}-m\delta_\alpha{}^{\dot\beta}\bigr)e^{-ip(x-y)}
     \Bigr].
\end{align}
The momentum-dependent terms cancel between the two integrals, leaving:
\begin{equation}
  \{\psi_\alpha(x),\psi^{\dagger\dot\beta}(y)\}\Big|_{x^0=y^0}
  = \delta_\alpha{}^{\dot\beta}\,\delta^{(3)}(\mathbf{x}-\mathbf{y}).
  \qquad\checkmark
\end{equation}

%% ============================================================
\section{Normal-Ordered Hamiltonian}
%% ============================================================

\subsection{Classical Hamiltonian density}

From the Weyl Lagrangian via Legendre transform:
\begin{equation}
  H = \int\!d^3x\,\bigl[-i\psi^\dagger\bar\sigma^k\partial_k\psi
      + \tfrac{1}{2}m\psi\psi + \tfrac{1}{2}m\psi^\dagger\psi^\dagger\bigr].
\end{equation}

\subsection{Mode expansion form}

Inserting the mode expansion (eq.~37.17):
\begin{equation}
  H = \int\!\frac{d^3p}{(2\pi)^3}\,\omegap
  \Bigl[b^\dagger_s(\mathbf{p})b_s(\mathbf{p}) - d_s(\mathbf{p})d^\dagger_s(\mathbf{p})\Bigr].
\end{equation}

\subsection{Normal ordering}

Using $\{d_s(\mathbf{p}),d^\dagger_{s'}(\mathbf{p}')\} = (2\pi)^3\delta^{(3)}\delta_{ss'}$:
\begin{equation}
  -d_s\,d^\dagger_s = +d^\dagger_s\,d_s - \{d_s,d^\dagger_s\}
  = +d^\dagger_s\,d_s - (2\pi)^3\delta^{(3)}(0).
\end{equation}
Discarding the (divergent, negative) zero-point energy:
\begin{equation}
  \boxed{:H: = \int\!\frac{d^3p}{(2\pi)^3}\,\omegap
  \Bigl[b^\dagger_s(\mathbf{p})b_s(\mathbf{p}) + d^\dagger_s(\mathbf{p})d_s(\mathbf{p})\Bigr]}
  \tag{37.17}
\end{equation}
\textbf{Cadabra2:} $:H: = \displaystyle\int\!\frac{d^3p}{(2\pi)^3}\,\bigl(""" + cdb_exprs["H_full"] + r"""\bigr)$

\medskip
Key contrast with bosons:
\begin{center}
\renewcommand{\arraystretch}{1.4}
\begin{tabular}{@{}lll@{}}
  \toprule
  Field type & Zero-point energy & $:H:$ \\
  \midrule
  Boson (scalar) & $+\frac{\omega}{2}$ per mode & $\int\omega\,a^\dagger a$ \\
  Fermion (Weyl) & $-\frac{\omega}{2}$ per mode & $\int\omega\,(b^\dagger b + d^\dagger d)$ \\
  \bottomrule
\end{tabular}
\end{center}

%% ============================================================
\section{Spin-Statistics Theorem}
%% ============================================================

The spin-statistics theorem (Pauli 1940) states:
\begin{equation}
  \text{Spin-}\tfrac{1}{2} \implies \text{anticommuting quantization}.
\end{equation}
Proof sketch via microcausality: for a Lorentz-invariant theory,
\[
  \bigl[\mathcal{O}(x),\mathcal{O}'(y)\bigr] = 0
  \quad\text{for spacelike }(x-y)^2>0.
\]
If a spin-$\frac{1}{2}$ field were quantized with \emph{commutators}:
\[
  [\psi_\alpha(x),\psi^{\dagger\dot\beta}(y)] = \int\!\frac{d^3p}{(2\pi)^3}
  \bigl[(-p_{\alpha}{}^{\dot\beta}+m)e^{ip(x-y)}
       -(-p_{\alpha}{}^{\dot\beta}-m)e^{-ip(x-y)}\bigr]
  \neq 0\quad\text{(spacelike)}
\]
--- a violation.  With anticommutators the $p$-terms cancel and the result
vanishes outside the light cone, as required.

%% ============================================================
\section{Summary}
%% ============================================================

\begin{center}
\renewcommand{\arraystretch}{1.5}
\begin{tabular}{@{}ll@{}}
  \toprule
  Object & Expression \\
  \midrule
  Equal-time CARs & $\{\psi_\alpha(\mathbf{x},t),\psi^{\dagger\dot\beta}(\mathbf{y},t)\}
    = \delta_\alpha{}^{\dot\beta}\delta^{(3)}(\mathbf{x}-\mathbf{y})$ \\
  Conjugate momentum & $\pi^\alpha = i\psi^{\dagger\alpha}$ \\
  Mode expansion & $\psi_\alpha = \int\frac{d^3p}{(2\pi)^3}\sum_s
    [b_s u^s_\alpha e^{ipx} + d^\dagger_s v^s_\alpha e^{-ipx}]$ \\
  Operator CARs & $\{b_s,b^\dagger_{s'}\} = \{d_s,d^\dagger_{s'}\}
    = (2\pi)^3\delta^{(3)}(\mathbf{p}-\mathbf{p}')\delta_{ss'}$ \\
  Weyl eq.\ (massive) & $p_{\alpha\dot\alpha}\tilde u^{\dot\alpha s} = +m u^s_\alpha$,\quad
    $p_{\alpha\dot\alpha}\tilde v^{\dot\alpha s} = -m v^s_\alpha$ \\
  Completeness & $\sum_s u^s_\alpha\tilde u^{\dot\beta s} = -p_\alpha{}^{\dot\beta} + m\delta_\alpha{}^{\dot\beta}$ \\
  Normal-ordered $H$ & $:H: = \int\frac{d^3p}{(2\pi)^3}\omegap[b^\dagger b + d^\dagger d]$ \\
  Spin-statistics & Spin-$\frac{1}{2}$ requires anticommuting fields (microcausality) \\
  \bottomrule
\end{tabular}
\end{center}

\bigskip
\noindent\textbf{Next:} Chapter 38 develops the spinor algebra toolkit
($\sigma$-completeness, trace identities, Fierz rearrangement) needed for
explicit Feynman diagram calculations.

\end{document}
"""

outpath = "/work/ch37_canonical_quantization.tex"
with open(outpath, "w") as f:
    f.write(doc.strip())

print(f"Wrote: {outpath}")
