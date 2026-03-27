export type ChapterStatus = "done" | "in-progress" | "not-started";

export interface Equation {
  label: string;
  latex: string;
  description?: string;
}

export interface Chapter {
  id: string;
  number: number | string;
  title: string;
  status: ChapterStatus;
  scriptFile: string;
  description: string;
  equations: Equation[];
  dockerCmd: string;
}

const DOCKER_BASE = `docker run --rm -it \\
  -v /home/propdev/.openclaw/workspace/repos/Monoclaw:/Monoclaw \\
  cadabra2-ubuntu:24.04 \\
  python3 /Monoclaw/Python/Cadabra2/Srednicki`;

function dockerCmd(script: string): string {
  return `${DOCKER_BASE}/${script}`;
}

export const chapters: Chapter[] = [
  {
    id: "ch34",
    number: 34,
    title: "Left/Right Weyl Spinors",
    status: "done",
    scriptFile: "ch34_left_right_spinors.py",
    description:
      "Introduces the two-component Weyl spinor formalism for massless fermions. Defines undotted (left-handed) and dotted (right-handed) spinor indices, the epsilon tensor for raising/lowering, and the van der Waerden notation. Establishes the mostly-plus metric g_{μν}=diag(-1,+1,+1,+1) (Srednicki Eq. 1.8) and sign conventions used throughout.",
    equations: [
      {
        label: "Metric",
        latex: "g_{\\mu\\nu} = \\mathrm{diag}(-1,+1,+1,+1)",
        description: "Mostly-plus metric signature (Srednicki Eq. 1.8 / 2.4)",
      },
      {
        label: "Epsilon tensor (undotted)",
        latex: "\\varepsilon^{12} = \\varepsilon_{21} = +1, \\quad \\varepsilon^{\\alpha\\beta}\\varepsilon_{\\beta\\gamma} = \\delta^\\alpha_{\\;\\gamma}",
      },
      {
        label: "Weyl kinetic Lagrangian",
        latex: "\\mathcal{L} = i\\psi^\\dagger\\bar{\\sigma}^\\mu\\partial_\\mu\\psi",
        description: "Massless left-handed Weyl fermion",
      },
      {
        label: "Spinor inner product",
        latex: "\\langle\\psi\\chi\\rangle = \\varepsilon^{\\alpha\\beta}\\psi_\\alpha\\chi_\\beta = \\psi^\\alpha\\chi_\\alpha",
      },
      {
        label: "Sigma matrices",
        latex: "\\sigma^\\mu_{\\alpha\\dot\\alpha} = (\\mathbf{1},\\boldsymbol{\\sigma}),\\quad \\bar{\\sigma}^{\\mu\\,\\dot\\alpha\\alpha} = (\\mathbf{1},-\\boldsymbol{\\sigma})",
      },
    ],
    dockerCmd: dockerCmd("ch34_left_right_spinors.py"),
  },
  {
    id: "ch35",
    number: 35,
    title: "Majorana and Dirac Spinors",
    status: "done",
    scriptFile: "ch35_majorana_dirac.py",
    description:
      "Combines two Weyl spinors into a four-component Dirac spinor and derives the Dirac equation from the Weyl formalism. Introduces the Majorana condition (self-conjugate spinor) and the 4×4 gamma matrices in the Weyl representation. Shows the equivalence between Dirac and Weyl descriptions.",
    equations: [
      {
        label: "Dirac spinor",
        latex: "\\Psi = \\begin{pmatrix} \\psi_\\alpha \\\\ \\bar\\chi^{\\dot\\alpha} \\end{pmatrix}",
      },
      {
        label: "Gamma matrices (Weyl rep)",
        latex: "\\gamma^\\mu = \\begin{pmatrix} 0 & \\sigma^\\mu \\\\ \\bar\\sigma^\\mu & 0 \\end{pmatrix}",
      },
      {
        label: "Dirac equation",
        latex: "(i\\gamma^\\mu\\partial_\\mu - m)\\Psi = 0",
      },
      {
        label: "Majorana condition",
        latex: "\\Psi^c = C\\bar\\Psi^T = \\Psi \\implies \\chi_\\alpha = \\psi_\\alpha",
      },
      {
        label: "Dirac Lagrangian",
        latex: "\\mathcal{L} = \\bar\\Psi(i\\gamma^\\mu\\partial_\\mu - m)\\Psi",
      },
    ],
    dockerCmd: dockerCmd("ch35_majorana_dirac.py"),
  },
  {
    id: "ch36",
    number: 36,
    title: "Weyl Lagrangian & Symmetries",
    status: "done",
    scriptFile: "ch36_weyl_lagrangian.py",
    description:
      "Studies the symmetries of the Weyl Lagrangian: U(1) phase invariance leading to fermion number conservation, and the discrete symmetries C, P, T. Derives the Noether current for fermion number and analyzes how spinors transform under parity and charge conjugation.",
    equations: [
      {
        label: "Weyl Lagrangian",
        latex: "\\mathcal{L} = i\\psi^\\dagger\\bar\\sigma^\\mu\\partial_\\mu\\psi - \\tfrac{1}{2}m(\\psi\\psi + \\psi^\\dagger\\psi^\\dagger)",
      },
      {
        label: "Fermion number current",
        latex: "j^\\mu = \\psi^\\dagger\\bar\\sigma^\\mu\\psi, \\quad \\partial_\\mu j^\\mu = 0",
      },
      {
        label: "Parity transformation",
        latex: "P\\,\\psi_\\alpha(t,\\mathbf{x})\\,P^{-1} = \\bar\\psi^{\\dot\\alpha}(t,-\\mathbf{x})",
      },
      {
        label: "Mass term",
        latex: "\\mathcal{L}_{\\rm mass} = -\\tfrac{1}{2}m\\,\\varepsilon^{\\alpha\\beta}\\psi_\\alpha\\psi_\\beta + \\mathrm{h.c.}",
      },
    ],
    dockerCmd: dockerCmd("ch36_weyl_lagrangian.py"),
  },
  {
    id: "ch37",
    number: 37,
    title: "Canonical Quantization of Weyl Fields",
    status: "in-progress",
    scriptFile: "ch37_canonical_quantization.py",
    description:
      "Promotes the Weyl field to a quantum operator via canonical anti-commutation relations. Introduces creation/annihilation operators for left-handed particles and their anti-particles, builds the Fock space, and derives the fermion propagator in momentum space.",
    equations: [
      {
        label: "Anti-commutation relations",
        latex: "\\{\\psi_\\alpha(\\mathbf{x}),\\psi^\\dagger_{\\dot\\alpha}(\\mathbf{y})\\} = \\sigma^0_{\\alpha\\dot\\alpha}\\,\\delta^3(\\mathbf{x}-\\mathbf{y})",
      },
      {
        label: "Mode expansion",
        latex: "\\psi_\\alpha(x) = \\int\\!\\widetilde{dk}\\,\\bigl[b(k,s)\\,u_\\alpha(k,s)\\,e^{ikx} + d^\\dagger(k,s)\\,v_\\alpha(k,s)\\,e^{-ikx}\\bigr]",
      },
      {
        label: "Weyl propagator",
        latex: "S_F^{\\alpha\\dot\\alpha}(k) = \\frac{-\\sigma^{\\mu\\,\\alpha\\dot\\alpha}k_\\mu}{k^2+m^2-i\\varepsilon}",
      },
      {
        label: "Number operator",
        latex: "N = \\int\\!\\widetilde{dk}\\,\\bigl[b^\\dagger(k,s)b(k,s) - d^\\dagger(k,s)d(k,s)\\bigr]",
      },
    ],
    dockerCmd: dockerCmd("ch37_canonical_quantization.py"),
  },
  {
    id: "ch38",
    number: 38,
    title: "LSZ for Spinors & Feynman Rules",
    status: "in-progress",
    scriptFile: "ch38_lsz_feynman_rules.py",
    description:
      "Extends the LSZ reduction formula to Weyl spinors to extract S-matrix elements from time-ordered correlators. Derives the Feynman rules for spinor QED/Yukawa theory including fermion propagators, vertex factors, and external state spinors. Introduces the helicity spinor basis.",
    equations: [
      {
        label: "LSZ (spinor)",
        latex: "\\langle f|i\\rangle = \\prod_j \\int d^4x_j\\,u^\\alpha(k_j)\\frac{\\delta}{i\\delta J^\\alpha(x_j)}\\,e^{iW[J]}\\Bigr|_{J=0}",
      },
      {
        label: "Fermion propagator (position space)",
        latex: "\\langle 0|T\\psi_\\alpha(x)\\psi^\\dagger_{\\dot\\alpha}(y)|0\\rangle = \\int\\!\\frac{d^4k}{(2\\pi)^4}\\,\\frac{-\\sigma^\\mu_{\\alpha\\dot\\alpha}k_\\mu}{k^2+m^2-i\\varepsilon}\\,e^{ik(x-y)}",
      },
      {
        label: "Yukawa vertex",
        latex: "\\mathcal{L}_{\\rm Yuk} = -y\\,\\phi\\,\\psi\\psi - y^*\\phi^\\dagger\\psi^\\dagger\\psi^\\dagger",
      },
      {
        label: "Helicity spinor",
        latex: "u_+(k) = \\begin{pmatrix}\\sqrt{E+p_z}\\\\\\sqrt{E-p_z}\\,e^{i\\phi}\\end{pmatrix}",
      },
    ],
    dockerCmd: dockerCmd("ch38_lsz_feynman_rules.py"),
  },
  {
    id: "ch48",
    number: 48,
    title: "Massless Particles & Spinor-Helicity",
    status: "not-started",
    scriptFile: "ch48_massless_spinor_helicity.py",
    description:
      "Specializes to massless particles where the spinor-helicity formalism is most powerful. Introduces the angle and square spinors λ, λ̃ for massless momenta, defines angle/square brackets, and shows how polarization vectors are written as spinor bilinears. Sets up the machinery for computing tree-level gluon amplitudes.",
    equations: [
      {
        label: "Massless momentum spinor",
        latex: "p_{\\alpha\\dot\\alpha} = \\lambda_\\alpha\\tilde\\lambda_{\\dot\\alpha},\\quad p^2 = 0",
      },
      {
        label: "Angle bracket",
        latex: "\\langle ij\\rangle = \\varepsilon^{\\alpha\\beta}\\lambda_\\alpha^i\\lambda_\\beta^j",
      },
      {
        label: "Square bracket",
        latex: "[ij] = \\varepsilon_{\\dot\\alpha\\dot\\beta}\\tilde\\lambda^{\\dot\\alpha}_i\\tilde\\lambda^{\\dot\\beta}_j",
      },
      {
        label: "Mandelstam from spinors",
        latex: "s_{ij} = (p_i+p_j)^2 = \\langle ij\\rangle[ji]",
      },
      {
        label: "Gluon polarization vector",
        latex: "\\varepsilon^+_{\\alpha\\dot\\alpha}(k;q) = \\frac{\\tilde\\lambda_{\\dot\\alpha}(k)\\,\\lambda_\\alpha(q)}{\\langle q|k]},\\quad \\varepsilon^-_{\\alpha\\dot\\alpha} = \\frac{\\lambda_\\alpha(k)\\,\\tilde\\lambda_{\\dot\\alpha}(q)}{[q\\,k\\rangle}",
      },
    ],
    dockerCmd: dockerCmd("ch48_massless_spinor_helicity.py"),
  },
  {
    id: "ch60",
    number: 60,
    title: "MHV Amplitudes (Parke-Taylor)",
    status: "done",
    scriptFile: "ch60_mhv_amplitudes.py",
    description:
      "Derives the famous Parke-Taylor formula for Maximally Helicity Violating (MHV) gluon scattering amplitudes. These are the simplest non-zero tree-level amplitudes with exactly two negative-helicity gluons. The remarkably compact formula encodes all colour-ordered partial amplitudes.",
    equations: [
      {
        label: "Parke-Taylor formula",
        latex: "A_n(1^-,2^-,3^+,\\ldots,n^+) = \\frac{\\langle 12\\rangle^4}{\\langle 12\\rangle\\langle 23\\rangle\\cdots\\langle n1\\rangle}",
        description: "MHV amplitude, all gluons, colour-ordered",
      },
      {
        label: "Momentum spinor decomposition",
        latex: "p_{\\alpha\\dot\\alpha} = \\lambda_\\alpha\\tilde\\lambda_{\\dot\\alpha}",
      },
      {
        label: "Angle bracket",
        latex: "\\langle ij\\rangle = \\varepsilon^{\\alpha\\beta}\\lambda^i_\\alpha\\lambda^j_\\beta",
      },
      {
        label: "Square bracket",
        latex: "[ij] = \\varepsilon_{\\dot\\alpha\\dot\\beta}\\tilde\\lambda^{\\dot\\alpha}_i\\tilde\\lambda^{\\dot\\beta}_j",
      },
      {
        label: "Amplitude vanishing condition",
        latex: "A_n(1^+,2^+,\\ldots,n^+) = 0,\\quad A_n(1^-,2^+,\\ldots,n^+) = 0",
        description: "All-plus and single-minus amplitudes vanish at tree level",
      },
    ],
    dockerCmd: dockerCmd("ch60_mhv_amplitudes.py"),
  },
  {
    id: "bcfw",
    number: "BCFW",
    title: "BCFW Recursion Relations",
    status: "not-started",
    scriptFile: "bcfw_recursion.py",
    description:
      "The Britto-Cachazo-Feng-Witten recursion relations express tree-level scattering amplitudes recursively in terms of lower-point amplitudes via complex momentum shifts. Combined with MHV amplitudes as seeds, BCFW generates all tree-level gluon amplitudes efficiently without Feynman diagrams.",
    equations: [
      {
        label: "Complex momentum shift",
        latex: "\\hat\\lambda_i(z) = \\lambda_i + z\\lambda_j,\\quad \\hat{\\tilde\\lambda}_j(z) = \\tilde\\lambda_j - z\\tilde\\lambda_i",
      },
      {
        label: "BCFW recursion",
        latex: "A_n = \\sum_{\\text{diagrams}}A_L(z_P)\\,\\frac{1}{P^2}\\,A_R(z_P)",
      },
      {
        label: "Pole condition",
        latex: "\\hat P^2(z_P) = 0 \\implies z_P = -\\frac{P^2}{\\langle i|P|j]}",
      },
      {
        label: "Cauchy theorem",
        latex: "A_n = -\\sum_{\\text{poles}}\\mathrm{Res}_{z=z_P}\\frac{A_n(z)}{z}",
      },
    ],
    dockerCmd: dockerCmd("bcfw_recursion.py"),
  },
  {
    id: "adscft",
    number: "AdS/CFT",
    title: "AdS/CFT Correspondence (coming soon)",
    status: "not-started",
    scriptFile: "adscft_intro.py",
    description:
      "The AdS/CFT correspondence (Maldacena duality) equates type IIB string theory on AdS₅×S⁵ with 𝒩=4 super Yang-Mills CFT on the boundary. This section will cover the dictionary between bulk fields and boundary operators, holographic renormalization, and connections to amplitudes via the amplituhedron.",
    equations: [
      {
        label: "AdS₅ metric",
        latex: "ds^2 = \\frac{R^2}{z^2}\\bigl(dz^2 + \\eta_{\\mu\\nu}dx^\\mu dx^\\nu\\bigr)",
      },
      {
        label: "Holographic dictionary",
        latex: "\\langle\\mathcal{O}(x)\\rangle_{\\rm CFT} = \\frac{\\delta S_{\\rm bulk}}{\\delta\\phi_0(x)}",
      },
      {
        label: "GKPW relation",
        latex: "Z_{\\rm CFT}[\\phi_0] = Z_{\\rm string}\\!\\left[\\phi\\big|_{\\partial}=\\phi_0\\right]",
      },
      {
        label: "Conformal dimension",
        latex: "\\Delta(\\Delta-4) = m^2 R^2",
        description: "Bulk mass–boundary operator dimension relation",
      },
    ],
    dockerCmd: dockerCmd("adscft_intro.py"),
  },
];

export const roadmap: string[] = [
  "ch34", "ch35", "ch36", "ch37", "ch38", "ch48", "ch60", "bcfw", "adscft",
];
