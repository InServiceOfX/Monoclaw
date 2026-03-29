"""
ch41_gamma_technology.py
=========================
Srednicki QFT — Chapter 41: Gamma Matrix Technology

What this file covers:
  §41.A  Weyl representation gamma matrices
  §41.B  Completeness relations
  §41.C  Trace identities (independent set)
  §41.D  Chiral representation and gamma^5 properties
  §41.E  Fierz identities for fermion bilinears

Run with:
    python3 ch41_gamma_technology.py
"""

import cadabra2
from cadabra2 import Ex, __cdbkernel__
import numpy as np

__cdbkernel__ = cadabra2.create_scope()

SEP = "=" * 70


def sec(s):
    print(f"\n{SEP}\n  {s}\n{SEP}")


# =============================================================================
# §41.A  Weyl representation gamma matrices
# =============================================================================
sec("§41.A — Weyl (chiral) representation of gamma^mu")

cadabra2.Indices(Ex(r"{\alpha, \beta, \gamma, \delta}"), Ex(r"position=fixed"))
cadabra2.Indices(Ex(r"{\dal, \dbe, \dga, \dde}"), Ex(r"position=fixed"))
cadabra2.Indices(Ex(r"{\mu, \nu, \rho, \sigma}"), Ex(r"position=free"))

print("Weyl (chiral) representation:")
print("  gamma^0 = [[0, 1],[1, 0]]   (block-off-diagonal)")
print("  gamma^i = [[0, -sigma_i],[-sigma_i, 0]]  (i=1,2,3)")
print()
print("gamma^5 = i gamma^0 gamma^1 gamma^2 gamma^3 = [[-1,0],[0,+1]]")
print("  (chiral projector: P_L = (1-gamma^5)/2, P_R = (1+gamma^5)/2)")
print()
print("Properties:")
print("  {gamma^mu, gamma^nu} = 2 eta^{mu nu} I_4   (Clifford algebra)")
print("  (gamma^0)^2 = I_4,    (gamma^i)^2 = -I_4")
print("  Tr[gamma^mu gamma^nu] = 4 eta^{mu nu}")

# =============================================================================
# §41.B  Completeness relations
# =============================================================================
sec("§41.B — Completeness relations for projectors")

print("Fermion projectors:")
print("  Lambda_+(p) = (p-slash + m)/(2m)  ->  positive-energy")
print("  Lambda_-(p) = (-p-slash + m)/(2m) ->  negative-energy")
print()
print("Spin sums (Ch.40):")
print("  Sum_s u_s(p) u-bar_s(p) = p-slash + m = 2m Lambda_+(p)")
print("  Sum_s v_s(p) v-bar_s(p) = p-slash - m = -2m Lambda_-(p)")
print()
print("Photon polarization sum:")
print("  Sum_lambda epsilon_mu(k,lambda) epsilon*_nu(k,lambda) = -eta_munu  (Feynman gauge)")

# =============================================================================
# §41.C  Independent trace identities
# =============================================================================
sec("§41.C — Independent trace identities")

print("Independent trace basis (for up to 4 gamma matrices):")
print()
print("  Tr[1]                    = 4")
print("  Tr[gamma^mu gamma^nu]   = 4 eta^{mu nu}")
print("  Tr[gamma^mu gamma^nu gamma^rho gamma^sigma] =")
print("    4 (eta^{mu nu} eta^{rho sigma} - eta^{mu rho} eta^{nu sigma} + eta^{mu sigma} eta^{nu rho})")
print()
print("Note: Tr[gamma^mu gamma^nu gamma^rho] = 0  (odd number)")
print("      Tr[gamma^5 gamma^mu gamma^nu] = 0  (odd)")
print("      Tr[gamma^5 gamma^mu gamma^nu gamma^rho gamma^sigma] = -4i epsilon^{mu nu rho sigma}")

# =============================================================================
# §41.D  Chiral properties and gamma^5
# =============================================================================
sec("§41.D — Chiral properties and gamma^5")

print("Chiral projectors:")
print("  P_L = (1 - gamma^5)/2,   P_R = (1 + gamma^5)/2")
print()
print("  psi_L = P_L psi   (left-handed Weyl field)")
print("  psi_R = P_R psi   (right-handed Weyl field)")
print()
print("  psi-bar_L = psi-bar P_R,    psi-bar_R = psi-bar P_L  (note reversal)")
print()
print("QED chiral anomaly (Adler-Bell-Jackiw):")
print("  partial_mu j^5mu = (e^2/16pi^2) Tr[gamma^5 F_mu_nu F^{mu nu}]")
print("  = (e^2/8pi^2) F_{mu nu} tilde{F}^{mu nu}  (topological charge density)")

# =============================================================================
# §41.E  Fierz identities
# =============================================================================
sec("§41.E — Fierz identities for fermion bilinears")

print("Fierz rearrangement (for 4-fermion operators):")
print()
print("  [psi-bar_A gamma^mu (1+-gamma^5) psi_B][psi-bar_C gamma_mu (1-+gamma^5) psi_D]")
print("  = [psi-bar_A gamma^mu (1+-gamma^5) psi_D][psi-bar_C gamma_mu (1-+gamma^5) psi_B]")
print()
print("Spin-0 (scalar) Fierz:")
print("  (psi-bar psi)(psi-bar psi) = -(psi-bar gamma^5 psi)(psi-bar gamma^5 psi)")
print("  + 1/2 Sum_{mu nu} (psi-bar sigma^{mu nu} psi)(psi-bar sigma_{mu nu} psi)")
print()
print("Useful for: Yukawa theory, Majorana mass terms, effective 4-fermion operators")

print(f"\n{SEP}")
print("  ch41 — Gamma Matrix Technology — COMPLETE")
print(f"{SEP}")
