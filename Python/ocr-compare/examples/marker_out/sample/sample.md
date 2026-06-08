# Single-minus gluon tree amplitudes are nonzero

Alfredo Guevara,<sup>1</sup> Alexandru Lupsasca,2,3 David Skinner,<sup>4</sup> Andrew Strominger,<sup>5</sup> and Kevin Weil<sup>2</sup> on behalf of OpenAI

Single-minus tree-level n-gluon scattering amplitudes are reconsidered. Often presumed to vanish, they are shown here to be nonvanishing for certain "half-collinear" configurations existing in Klein space or for complexified momenta. We derive a piecewise-constant closed-form expression for the decay of a single minus-helicity gluon into n−1 plus-helicity gluons as a function of their momenta. This formula nontrivially satisfies multiple consistency conditions including Weinberg's soft theorem.

The laws of physics are succinctly encoded in scattering amplitudes, which give the quantum probabilities for any given collection of incoming particles to collide and produce any given collection of outgoing particles. These amplitudes may be systematically derived from the Feynman diagram expansion, which perturbatively sums over all possible quantum processes. Theoretical results from the Feynman diagram expansion of the Standard Model agree with experiment to an unprecedented 14 decimal places [\[1](#page-8-0)[–3\]](#page-8-1).

In practice, the computation of scattering amplitudes can be extremely difficult.[1](#page-0-0) Among other obstacles, the growth in the number of Feynman diagrams for an nparticle amplitude is faster than exponential in n. However, despite this apparent complexity, cancellations lead in a variety of contexts to a very simple final answer. This indicates that our present understanding of the quantum laws of physics is seriously incomplete and that a more efficient formulation is needed. The last few decades have seen much effort in this direction and delivered promising insights; see, e.g., [\[4–](#page-8-2)[10\]](#page-8-3).

A prominent example of this phenomenon arises in the tree-level color-ordered scattering of gluons—the particles that mediate the strong force and comprise Yang– Mills theory. Naively, the n-gluon scattering amplitude involves order n! terms. Famously, for the special case of MHV (maximally helicity violating) tree amplitudes, Parke and Taylor [\[11\]](#page-8-4) gave a simple and beautiful, closedform, single-term expression for all n.

By definition, n-gluon MHV amplitudes have 2 minushelicity particles and n − 2 plus-helicity gluons, which for generic (complexified) kinematics at tree level is the maximally allowed number [\[4,](#page-8-2) [11](#page-8-4)[–14\]](#page-9-0). This gives them a privileged role in the theory, enabling their use as efficient building blocks for the full Yang–Mills theory.

In general, n−2 is actually not the maximally allowed number of plus gluons. In this paper, we show that n−1 plus (or "single-minus") amplitudes are in fact allowed[2](#page-0-1) with restricted "half-collinear" kinematics.[3](#page-0-2) The amplitude is divided into chambers whose walls are regions where sums of various subsets of the half-collinear momenta are orthogonal as described below. The (stripped) amplitudes are piecewise-constant integers in each chamber. The assignment of its value to each chamber is determined from the perturbative Berends–Giele recursion [\[15\]](#page-9-1), which is equivalent to Feynman diagrams.

Moreover, for the special kinematic region corresponding to single-minus decay into n−1 plus, we give a simple formula for all n. In this special region, the stripped amplitude only takes the values of +1, −1, or 0.

The key formula [\(39\)](#page-4-0) for the amplitude in this region was first conjectured by GPT-5.2 Pro and then proved by a new internal OpenAI model. The solution was checked by hand using the Berends–Giele recursion and was moreover shown to nontrivially obey the soft theorem, cyclicity, Kleiss–Kuijf, and U(1) decoupling identities—none of which are evident from direct inspection.

The structural role of these single-minus amplitudes in Yang–Mills theory remains to be understood. We note that, while our expression is a dramatic simplification of the direct Feynman-diagram expression, it is entirely possible that a yet simpler expression may be obtained with a clever choice of analytic continuation, variables or basis, even outside the single-minus decay channel. We suspect that there are more interesting insights to come with our methodology and hope that this paper is a step on the road to a more complete understanding of the inner structure of scattering amplitudes.

Single-minus amplitudes also arise in self-dual Yang– Mills theory (SDYM) [\[16\]](#page-9-2), a restricted sector of Yang– Mills, and potentially resolve a puzzle therein. In general, the tree amplitudes of the Feynman expansion are thought to be equivalent to the fully nonlinear classical theory. However, on the one hand the classical solution space of SDYM is extremely nontrivial [\[17–](#page-9-3)[19\]](#page-9-4), while the tree diagrams were previously supposed to yield trivial two-point and three-point expressions. The latter seem insufficient to reproduce the former. Potentially, the single-minus tree amplitudes in SDYM found here resolve this tension.

Institute for Advanced Study <sup>2</sup>OpenAI <sup>3</sup>Vanderbilt University <sup>4</sup>Cambridge University <sup>5</sup>Harvard University

<span id="page-0-0"></span><sup>1</sup> The aforementioned agreement between theory and experiment required over a half century of analytic and numerical work.

<span id="page-0-1"></span><sup>2</sup> Witten [\[5\]](#page-8-5) notes that single-minus amplitudes are supported at a point in twistor space; see also [\[6\]](#page-8-6).

<span id="page-0-2"></span><sup>3</sup> The half-collinear condition can be viewed as restricting the in-

going and outgoing momenta to a one-dimensional null circle on the celestial torus at the boundary of Klein space.

This paper is organized as follows. In Sec. I, we set up notation, describe the standard MHV amplitudes, explain how half-collinear single-minus amplitudes evade the usual no-go condition, and then derive the general Berends–Giele recursion relation. The solution passes various consistency checks, including the soft theorem, and we provide explicit formulas up to n = 6 points, where there are already 32 terms. In Sec. II, we restrict to a special kinematic channel denoted  $\mathcal{R}_1$  with one ingoing minus and n-1 outgoing plus gluons. There, using various identities through n=6, we find the answer can be expressed as a signed product of n-2 projection operators. This motivates a guess for the all-n formula, which we verify directly via the Berends-Giele recursion. We derive a multi- $\delta$ -function identity in App. A and give more details of the single-minus specialization of the Berends–Giele recursion in App. B.

Further details of our analysis, including a longer general formula for the single-minus amplitude outside of  $\mathcal{R}_1$ , will appear elsewhere. Our main result immediately leads to a number of extensions. The construction generalizes directly from gluon to graviton amplitudes and has a simple supersymmetrization. The results should transform under the S-algebra, the  $\mathcal{L}w_{1+\infty}$  algebra [20, 21], and their supersymmetric extensions. In the context of celestial holography, the Mellin transform of the amplitudes in some sectors is given by Lauricella functions. These results will be reported elsewhere.

# A. Notation and useful identities

This subsection defines our notation<sup>4</sup> and presents several useful identities. We use spinor-helicity variables for massless momenta [13]

$$p_{\alpha\dot{\alpha}} = \lambda_{\alpha}\tilde{\lambda}_{\dot{\alpha}},\tag{1}$$

where  $(\lambda, \tilde{\lambda})$  are *real* spinors in (2,2) Klein signature. As usual in the description of scattering, it is convenient to fix a suitable Lorentz and helicity frame to perform the calculation, which can be restored at the end. With the benefit of hindsight, we write

$$|i\rangle = \lambda_i = (1, z_i), \qquad |i\rangle = \tilde{\lambda}_i = \omega_i(1, \tilde{z}_i), \qquad (2)$$

with  $z_i$  and  $\tilde{z}_i$  real and independent. We use standard brackets for contracting helicity spinors,

$$\langle ij\rangle = \langle \lambda_i \lambda_j \rangle = \epsilon_{\alpha\beta} \lambda_i^{\alpha} \lambda_i^{\beta}, \tag{3}$$

$$[ij] = \left[\tilde{\lambda}_i \tilde{\lambda}_j\right] = \epsilon_{\dot{\alpha}\dot{\beta}} \tilde{\lambda}_i^{\dot{\alpha}} \tilde{\lambda}_j^{\dot{\beta}}, \tag{4}$$

with  $p_{ij}^2 = (p_i + p_j)^2 = \langle ij \rangle [ij]$ . In our parameterization,

$$\langle ij \rangle = z_{ii}, \qquad [ij] = \omega_i \omega_i \tilde{z}_{ii}, \qquad (5)$$

where  $z_{ij} \equiv z_i - z_j$  and  $\tilde{z}_{ij} \equiv \tilde{z}_i - \tilde{z}_j$ . We take our polarization vectors to be

<span id="page-1-6"></span><span id="page-1-5"></span>
$$\epsilon_j^- = \sqrt{2} \frac{|r]\langle j|}{[rj]}, \qquad \epsilon_k^+ = \sqrt{2} \frac{|k]\langle r|}{\langle rk \rangle},$$
 (6)

where  $|r\rangle$  and |r| are arbitrary reference spinors. We note that with our conventions (2) for fixing the little group frame,  $\epsilon^{\pm}$  has mass dimension  $\pm 1$ , which will affect the mass dimensions of the amplitudes given below. To avoid proliferation of factors of  $2\pi$ , we normalize all  $\delta$ -functions such that

$$\int \delta(x) \, \mathrm{d}x = 2\pi, \qquad \frac{1}{x + i\epsilon} - \frac{1}{x - i\epsilon} \stackrel{\epsilon \to 0}{=} -i \, \delta(x). \quad (7)$$

Throughout this paper, we use the standard Feynman propagator  $1/(p^2 + i\epsilon)$ . Other prescriptions have been considered in Klein signature [22].

To clarify our conventions, with our normalization, the n-point MHV (double-minus) color-ordered tree amplitude  $\mathcal{A}_n^{\mathrm{MHV}}(1^+,\ldots r^-,\ldots s^-,\ldots,n^+)$  is

$$\mathcal{A}_n^{\text{MHV}} = i \frac{\langle rs \rangle^4}{\langle 12 \rangle \langle 23 \rangle \cdots \langle n1 \rangle} \, \delta^4 \Biggl( \sum_{k=1}^n p_k \Biggr). \tag{8}$$

In fact, for full generality, we will need to be careful about the  $i\epsilon$  prescription. We therefore introduce the regularized Parke-Taylor factor

$$PT_{cyc} = \prod_{k=1}^{n} \frac{[k, k+1]}{p_{k,k+1}^2 + i\epsilon} = \prod_{k=1}^{n} \frac{1}{z_{k,k+1} + i\epsilon \operatorname{sg}_{k,k+1}}, \quad (9)$$

with  $n+1 \equiv 1$ , and where we have defined

<span id="page-1-4"></span><span id="page-1-3"></span>
$$sg_{ij} = sg([\tilde{\lambda}_i \tilde{\lambda}_j])$$
 (10)

in the frame (2).<sup>5</sup> Here,  $sg(x) = 2\Theta(x) - 1$  denotes the sign function and  $\Theta(x)$  is the step function. The MHV tree amplitude can then be written using  $PT_{cyc}$  as

<span id="page-1-7"></span>
$$\mathcal{A}_n^{\text{MHV}} = i \langle rs \rangle^4 \operatorname{PT}_{\text{cyc}} \delta^4 \left( \sum_{k=1}^n p_k \right).$$
 (11)

Away from walls where  $\langle k | k+1 \rangle = 0$ , we may ignore the  $i\epsilon$  prescription and (11) reduces to (8).

<span id="page-1-1"></span>It will also be useful to define an "incomplete" or "open chain" Parke-Taylor factor as

$$PT_{1\cdots n} = \prod_{k=1}^{n-1} \frac{[k, k+1]}{p_{k,k+1}^2 + i\epsilon} = \prod_{k=1}^{n-1} \frac{1}{z_{k,k+1} + i\epsilon \operatorname{sg}_{k,k+1}}.$$
(12)

This incomplete factor  $\operatorname{PT}_{1\cdots n}$  is what naturally appears in App. B inside the Berends–Giele recursion as the denominator of the off-shell current with momentum  $p_{1\cdots n}$ : the cyclic factor is "opened" because one leg is off-shell.

<span id="page-1-0"></span><sup>&</sup>lt;sup>4</sup> Our conventions are close to those of [5], except for a factor of 2 on the LHS of (2.7) therein.

<span id="page-1-2"></span><sup>&</sup>lt;sup>5</sup> Without fixing a frame, we would take  $\mathrm{sg}_{ij} = \mathrm{sg}([ij]\langle ir \rangle \langle jr \rangle)$ , where  $|r\rangle$  is any fixed reference spinor. In  $\mathcal{A}_n^{\mathrm{MHV}}$ , the difference in choices of  $|r\rangle$  can be absorbed by  $\epsilon$ .

# <span id="page-2-0"></span>I. SINGLE-MINUS AMPLITUDES

In this section, we first explain why the standard argument that the single-minus n-particle tree amplitudes vanish in fact fails when all the external particles become collinear. We then present a recursion relation, derived in App. B, that determines these amplitudes for all n.

# A. The half-collinear regime

The kinematic locus we call the *half-collinear regime* is defined by

$$\langle ij \rangle = 0 \qquad \forall i, j \in \{1, \dots, n\}.$$
 (13)

In (2,2) signature, this is compatible with nonzero [ij], unlike in Minkowski space.<sup>6</sup> In the frame (2), this locus implies all  $z_{ij} = 0$  but does not restrict the  $\omega_i$  or  $\tilde{z}_i$ .

We will now show that single-minus tree amplitudes can be nonzero in the half-collinear regime. This can be demonstrated by exposing the "loophole" in the power-counting argument that single-minus amplitudes vanish. We choose polarization vectors for the n gluons as in (6)

$$\epsilon_1^- = \sqrt{2} \frac{|r]\langle 1|}{[r1]}, \qquad \epsilon_a^+ = \sqrt{2} \frac{|r\rangle[a|}{\langle ra\rangle} \qquad \text{for } a \ge 2, \quad (14)$$

where |r| and  $|r\rangle$  are arbitrary reference spinors. Now, for generic kinematics, if we choose  $|r\rangle = |1\rangle$ , then we find that all the polarization vectors are orthogonal. As such, the amplitude can be nonzero only if they are contracted with momenta in the numerator. Powers of momenta in the numerator appear only from vertices, and there are at most n-2. These are insufficent to contract with all the polarization vectors. Hence, single-minus amplitudes vanish for generic kinematics.

The loophole in the argument is that we cannot choose  $|r\rangle=|1\rangle$  if  $\langle 1a\rangle=0$  for any  $|a\rangle$ , as the polarization vectors  $\epsilon_a^+$  would become singular. Therefore, we cannot conclude that the amplitude vanishes on the locus where  $\langle 1a\rangle=0$ . In fact, the single-minus 3-point amplitude (also anti-MHV) is known to have a factor  $\delta(\langle 12\rangle)\delta(\langle 13\rangle)$  restricting to this locus. Moreover, it can be shown by induction that the n-point amplitude may only be supported when  $all\ \langle ij\rangle=0$ .

To express the fact that it is supported in the halfcollinear regime, the single-minus tree-level n-gluon amplitude  $A_n(1^-, 2^+, \dots, n^+)$  can be written as

$$\mathcal{A}_{n} = i^{2-n} \frac{\langle r1 \rangle^{n+1}}{\langle r2 \rangle \langle r3 \rangle \cdots \langle rn \rangle} A_{1 \cdots n} \prod_{a=2}^{n} \delta(\langle 1a \rangle)$$
$$\times \delta^{2} \left( \sum_{i=1}^{n} \langle ri \rangle \tilde{\lambda}_{i} \right). \tag{15}$$

Here, we introduced the stripped amplitude  $A_{1\cdots n}$ . The  $\delta$ -functions imposing  $\langle 1a \rangle = 0$  simply ensure the full amplitude is supported only in the half-collinear regime, while the  $\delta$ -functions in  $\tilde{\lambda}$  enforce the remaining components of momentum conservation. The prefactor ensures that  $\mathcal{A}_n$  has the correct little-group scaling for a single-minus amplitude. The collinear  $\delta$ -functions ensure that this prefactor and the  $\tilde{\lambda}$   $\delta$ -functions are independent of the reference spinor  $|r\rangle$ , as long as it is chosen so that  $\langle r1 \rangle \neq 0$ .

The interest is in the stripped amplitude  $A_{1\cdots n}$ , which carries no helicity weight and depends only on kinematics. In the frame (2) and picking  $|r\rangle = (0,1)$ ,  $A_{1\cdots n}$  is a function only of  $\{\tilde{\lambda}_i\}$ , and (15) becomes<sup>7</sup>

$$\mathcal{A}_n = i^{2-n} A_{1\cdots n} \prod_{a=2}^n \delta(z_{1a}) \, \delta^2 \left( \sum_{i=1}^n \tilde{\lambda}_i \right). \tag{16}$$

We will sometimes use the shorthand

<span id="page-2-6"></span>
$$\delta_{1\cdots n} = i^{1-n} \prod_{k=1}^{n-1} \delta(z_{k,k+1})$$
 (17)

<span id="page-2-5"></span>to denote these half-collinear  $\delta$ -functions.

## B. The recursion relation

The first main result of this paper is the recursion relation presented in (21) below. This relation determines all n-particle single-minus tree amplitudes. Solving it is equivalent to, but slightly simpler than, summing the Feynman diagrams for these amplitudes.

For any ordered list S = (q, ..., p), we first define the list momentum  $\tilde{\lambda}_S = \sum_{i \in S} \tilde{\lambda}_i$  using the frame (2).<sup>8</sup> We then define the *preamplitude*  $\bar{A}_S$  by taking

<span id="page-2-7"></span>
$$\bar{A}_q = 1, \qquad \bar{A}_{qp} = 0, \tag{18}$$

when |S|=1 and |S|=2, and extending recursively to  $|S|\geq 3$  via

$$\bar{A}_{q\cdots p} = -\sum_{\text{o.p.}} V_{\tilde{\lambda}_{S_1}\cdots\tilde{\lambda}_{S_A}} \prod_{a=1}^A \bar{A}_{S_a}, \tag{19}$$

where the sum is over all ordered partitions of  $(q \cdots p) = (S_1 | S_2 | \cdots | S_A)$  into  $A \geq 3$  parts.

$$\mathcal{A}_n \to i^{2-n} \left| \frac{\omega_1}{\omega_2 \omega_3 \cdots \omega_n} \right| A_{1 \cdots n} \prod_{a=2}^n \delta(z_{1a}) \, \delta^2 \left( \sum_{i=1}^n \sqrt{|\omega_i|} \tilde{\lambda}_i \right).$$

<span id="page-2-1"></span><sup>&</sup>lt;sup>6</sup> The half-collinear regime also makes sense for complex momenta. We believe single-minus amplitudes also exist with complex momenta; it would be interesting to understand their continuation.

<span id="page-2-3"></span><span id="page-2-2"></span><sup>&</sup>lt;sup>7</sup> Some readers may find more intuitive an alternative expression, obtained in the frame  $\tilde{\lambda} \to \frac{1}{\sqrt{|\omega|}} \tilde{\lambda}$ ,  $\lambda \to \sqrt{|\omega|} \lambda$ , which renders the polarizations (14) dimensionless and gives  $\mathcal{A}_n$  scaling as  $\omega^{-n}$ :

<span id="page-2-4"></span><sup>&</sup>lt;sup>8</sup> In a generic frame,  $\tilde{\lambda}_S = \sum_{i \in S} \tilde{\lambda}_i \langle ir \rangle$  for any reference spinor  $|r\rangle$ . The dependence of both this expression and the sign functions on  $|r\rangle$  drops out on the support of the collinear  $\delta$ -functions.

Here, the vertex term  $V_{\tilde{\lambda}_{S_1}...\tilde{\lambda}_{S_L}}$  is defined by

$$V_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} = \prod_{k=1}^{n-1} \operatorname{sg}_{k,k+1} \Theta\left(-\frac{\left[\tilde{\lambda}_1 \dots_k \tilde{\lambda}_{k+1} \dots_m\right]}{\left[\tilde{\lambda}_k \tilde{\lambda}_{k+1}\right]}\right), \quad (20)$$

in the case where each block  $S_a$  contains only one element. We also take  $V_{\tilde{\lambda}_1} = 1$ . Having determined  $\bar{A}_S$ , the stripped amplitude  $A_{1\cdots n}$  itself is then given by

$$A_{1\cdots n} = -\sum_{\text{o.p.}} \widehat{PT}_{\tilde{\lambda}_{S_1}\cdots\tilde{\lambda}_{S_A}} \prod_{a=1}^A \bar{A}_{S_a}, \qquad (21)$$

where the ordered partition now has  $A \geq 1$  parts, while

$$\widehat{\text{PT}}_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} = V_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} - \bar{V}_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n}, \tag{22}$$

where  $\bar{V}_{\tilde{\lambda}_1...\tilde{\lambda}_n}$  is given by (20) with a + sign within the argument of  $\Theta$ . We may refer to this object as *on-shell Parke-Taylor*, as it is related to  $PT_{1...n}$  by a standard LSZ reduction procedure fleshed out in App. B.

It is also useful to note that the incomplete Parke-Taylor factor  $\operatorname{PT}_{1\cdots n}$ , the collinear  $\delta$ -functions and the vertex function  $V_{\tilde{\lambda}_1\cdots\tilde{\lambda}_n}$  are related via the useful identity

$$PT_{1\cdots n} - \delta_{1\cdots n} V_{\tilde{\lambda}_1\cdots\tilde{\lambda}_n}$$

$$= \sum_{j=1}^{n-1} \frac{\left[\tilde{\lambda}_{1\cdots j}\tilde{\lambda}_{j+1\cdots n}\right]}{p_{1\cdots n}^2 + i\epsilon} PT_{1\cdots j} PT_{j+1\cdots n}, \qquad (23)$$

which follows from a master identity given in App. A.

# C. Consistency checks

It follows from the definition (15) that the stripped amplitudes  $A_{12\cdots n}$  satisfy the following properties:

1. Cyclicity:

$$A_{12\cdots n} = A_{2\cdots n1}. (24)$$

2. Reflection symmetry:

$$A_{12\cdots n} = (-1)^n A_{n\cdots 21}. (25)$$

<span id="page-3-1"></span>3. U(1) decoupling:

$$A_{12\cdots n} + A_{13\cdots n2} + A_{14\cdots 23} + \dots = 0. \tag{26}$$

<span id="page-3-0"></span>4. Kleiss-Kuijf (KK) relations. For instance, at n = 5,

$$A_{12345} + A_{12354} + A_{12435} + A_{14235} = 0. (27)$$

(The general form of these relations can be found, e.g., in [13]).

5. Weinberg's soft theorem:

$$\lim_{\omega_n \to 0} A_{1\cdots n} = \frac{1}{2} (\operatorname{sg}_{n-1,n} + \operatorname{sg}_{n1}) A_{1\cdots n-1}. \tag{28}$$
 It is far from evident that all these properties are

It is far from evident that all these properties are obeyed by the solution of the recursion relation (21). Nonetheless, we have verified by explicit calculation that they do indeed hold. Details of this calculation will appear elsewhere.

### <span id="page-3-3"></span>D. Concrete examples

<span id="page-3-4"></span>From (21), the 3-point to 6-point single-minus stripped amplitudes are, using  $\operatorname{sg}_{i,jk} = \operatorname{sg}\left(\left[\tilde{\lambda}_i, \tilde{\lambda}_j + \tilde{\lambda}_k\right]\right)$ , etc.,

$$A_{123} = sg_{12}, (29)$$

$$A_{1234} = \frac{1}{2} (sg_{23} sg_{41} + sg_{12} sg_{34}); \tag{30}$$

<span id="page-3-2"></span>
$$A_{12345} = \frac{1}{4} \left[ sg_{51} sg_{34} sg_{2,34} + sg_{51} sg_{23} sg_{23,4} - sg_{51} sg_{2,34} sg_{23,4} + sg_{45} sg_{23} sg_{1,23} + sg_{45} sg_{12} sg_{12,3} - sg_{45} sg_{1,23} sg_{12,3} + sg_{51} sg_{45} sg_{12,34} + sg_{12} sg_{34} sg_{12,34} \right],$$
(31)

$$A_{123456} = \frac{1}{8} \left[ -\operatorname{sg}_{1,23} \operatorname{sg}_{12,3} \operatorname{sg}_{123,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,23} \operatorname{sg}_{123,4} \operatorname{sg}_{23} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{12,34} \operatorname{sg}_{23,4} \operatorname{sg}_{56} - \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} - \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{23,4} \operatorname{sg}_{56} + \operatorname{sg}_{1,234} \operatorname{sg}_{34,5} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{12,34} \operatorname{sg}_{34} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{12,34} \operatorname{sg}_{34} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{12,34} \operatorname{sg}_{34} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} \operatorname{sg}_{56} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{45,6} + \operatorname{sg}_{12} \operatorname{sg}_{345,6} \operatorname{sg}_{234,5} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} + \operatorname{sg}_{234,5} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_{345,6} \operatorname{sg}_$$

Clearly a more concise formula is needed!

## <span id="page-4-1"></span>II. AMPLITUDES IN THE FIRST REGION

This section presents the next main result of this paper: a simple formula for the n-point single-minus amplitudes (21) with partially restricted kinematics within the half-collinear regime.

# A. Restricted kinematics within the half-collinear regime $\mathbf{r}$

We define the kinematic region  $\mathcal{R}_1$  by the condition that, with  $\tilde{\lambda}_{\dot{\alpha}} = \omega(1, \tilde{z})$ , there exists at least one SO(2, 2) frame in which

$$\omega_1 < 0, \qquad \omega_a > 0, \qquad a \in \{2, \dots, n\}.$$
 (33)

This region is fully consistent with the half-collinear regime where all  $\langle ij \rangle = 0$  and further restricts the kinematics within that regime. Unlike in Minkowski signature, we note that in Klein signature, there is no invariant meaning to a particle having positive frequency. Nonetheless,  $\mathcal{R}_1$  is  $\mathsf{SO}(2,2)$ -invariant because we only ask that there exists some frame in which (33) holds. Geometrically, it amounts to requiring that there exists some straight line through the origin in  $\mathbb{R}^2$  such that  $\tilde{\lambda}_1$  lies on one side and all other  $\tilde{\lambda}_a$  lie on the other.  $\mathcal{R}_1$  describes a single ingoing self-dual gluon decaying to n-1 outgoing anti-self-dual gluons, where ingoing/outgoing refers to the frame in which the inequalities (33) hold.

Interestingly, we will see that the amplitudes dramatically simplify in  $\mathcal{R}_1$ , where certain sign functions become independent of the frequencies  $\omega_k$ . In particular,

$$\operatorname{sg}_{ij} = \operatorname{sg} \tilde{z}_{ij}, \quad \operatorname{sg}_{1j} = \operatorname{sg} \tilde{z}_{j1} \quad \forall i, j \ge 2.$$
 (34)

Note however that the  $\omega_k$  cannot be eliminated from expressions such as  $\mathrm{sg}_{2,34}$ .

# B. Concrete examples

In region  $\mathcal{R}_1$ , using (34), momentum conservation and spinor identities, one may show that the long expressions

of the previous section dramatically simplify to

<span id="page-4-5"></span>
$$A_{123}|_{\mathcal{R}_1} = \frac{1}{2}(\mathrm{sg}_{12} + \mathrm{sg}_{23}),$$
 (35)

$$A_{1234}|_{\mathcal{R}_1} = \frac{1}{4}(\mathrm{sg}_{12} + \mathrm{sg}_{23})(\mathrm{sg}_{34} + \mathrm{sg}_{41}),$$
 (36)

$$A_{12345}|_{\mathcal{R}_1} = \frac{1}{8} (sg_{12} + sg_{23}) (sg_{34} + sg_{1,23})$$

$$(sg_{45} + sg_{54}).$$
(37)

$$A_{123456}|_{\mathcal{R}_1} = \frac{1}{16} (sg_{12} + sg_{23}) (sg_{34} + sg_{1,23})$$
 (38)  
 
$$(sg_{45} + sg_{1,234}) (sg_{56} + sg_{61}).$$

This suggests the possibility that there may exist a shorter formula for all n.

#### <span id="page-4-6"></span><span id="page-4-0"></span>C. General formula

<span id="page-4-3"></span>A conjecture that extends the pattern (35)–(38) to all n-particle amplitudes in region  $\mathcal{R}_1$  is

$$A_{1\cdots n}\big|_{\mathcal{R}_1} = \frac{1}{2^{n-2}} \prod_{m=2}^{n-1} (\operatorname{sg}_{m,m+1} + \operatorname{sg}_{1,2\cdots m}).$$
 (39)

How sensible is this guess? Regarding requirements (24)–(28), the region  $\mathcal{R}_1$  is clearly not cyclically invariant, as it singles out particle 1. However, we can trivially construct a cyclically invariant answer by using cyclicity to extend (39) to other regions  $\mathcal{R}_k$  where only particle k has  $\omega_k < 0$ . The remaining four conditions, when combined with cyclicity, do impose quite nontrivial constraints within  $\mathcal{R}_1$ . These constraints are all obeyed by our solution (39). In fact, in this form, it is direct to check the soft theorem (28) in the last label, and with some more work, in any other label but 1.

<span id="page-4-4"></span>The simplified form (21) has a simple interpretation: in  $\mathcal{R}_1$ , each factor is  $\frac{1}{2}(\pm 1 \pm 1) \in \{-1,0,1\}$ , so  $A_{1\cdots n}|_{\mathcal{R}_1}$  is piecewise-constant and jumps across codimension-one walls where the relevant brackets change sign. The product form simply makes those walls explicit.

The rest of this work is devoted to proving that the conjecture (39) is correct. The proof uses ideas from time-ordered perturbation theory and proceeds in three parts. First, one shows that in  $\mathcal{R}_1$ ,

<span id="page-4-8"></span><span id="page-4-7"></span>
$$V_{\tilde{\lambda}_2 \cdots \tilde{\lambda}_n} \Big|_{\mathcal{R}_1} = 0, \tag{40}$$

whilst  $\bar{V}_{\tilde{\lambda}_2 \cdots \tilde{\lambda}_n}$  remains nonzero. Second, one must show that with (40), the recursion (21) collapses to become

$$A_{1\cdots n}\big|_{\mathcal{R}_1} = \bar{V}_{\tilde{\lambda}_2\cdots\tilde{\lambda}_n}\Big|_{\mathcal{R}_1}.$$
 (41)

Finally, one must show that in  $\mathcal{R}_1$ ,  $V_{\tilde{\lambda}_2...\tilde{\lambda}_n}$  reduces to our final formula (39). We briefly sketch each step below.

<span id="page-4-2"></span><sup>&</sup>lt;sup>9</sup> Through (16), this is seen to follow from the conventional form  $\mathcal{A}_n \to \left(\frac{\langle 1r \rangle}{\langle nr \rangle} \frac{[n,1]}{p_{n,1}^2 + i\epsilon} - \frac{\langle n-1,r \rangle}{\langle nr \rangle} \frac{[n,n-1]}{p_{n,n-1}^2 + i\epsilon}\right) \mathcal{A}_{n-1}.$ 

# 1. Vanishing of V

We wish to show that within  $\mathcal{R}_1$ ,

$$V_{\tilde{\lambda}_2 \cdots \tilde{\lambda}_n} = 0 \tag{42}$$

for  $n \geq 3$ . This can be interpreted as a causality condition<sup>10</sup> in  $\mathcal{R}_1$  in the frame in which (33) holds. Importantly, all the  $\omega$ 's appearing in this expression are positive. This will force at least one of the arguments of the  $\Theta$ -functions to be negative, implying (42). For each cut j, write left- and right-partial sums as

$$\tilde{\lambda}_L = \sum_{a=2}^{j} \tilde{\lambda}_a = \Omega_L(1, \tilde{z}_L), \tag{43}$$

$$\tilde{\lambda}_R = \sum_{a=j+1}^n \tilde{\lambda}_a = \Omega_R(1, \tilde{z}_R), \tag{44}$$

with  $\Omega_{L,R} > 0$  and  $\tilde{z}_{L,R}$  weighted averages of the  $\tilde{z}$ 's on each side. Then

$$\left[\tilde{\lambda}_R \tilde{\lambda}_L\right] = \Omega_L \Omega_R \tilde{z}_{R,L},\tag{45}$$

$$\left[\tilde{\lambda}_{j+1}\tilde{\lambda}_{j}\right] = \omega_{j}\omega_{j+1}\tilde{z}_{j+1,j}.\tag{46}$$

Since  $\Omega_L\Omega_R > 0$  and  $\omega_j\omega_{j+1} > 0$ , the sign of the ratio in the  $\Theta$ -factor in (20) is the sign of  $\tilde{z}_{R,L}/\tilde{z}_{j+1,j}$ . A weighted-variance identity implies that as j runs from 2 to n, there must be at least one cut  $j^*$  for which  $\tilde{z}_{R,L}$  has the same sign as the adjacent increment  $\tilde{z}_{j+1,j}$ . For that  $j^*$ , the ratio is positive, so the corresponding factor  $\Theta(-\text{positive}) = 0$ , and thus the whole product in (20) vanishes.

## 2. Collapsing the recursion

We have in fact shown something slightly more general: for *every* consecutive  $S \subset \{2, ..., n\}$  with  $|S| \ge 2$ ,

$$V_{\tilde{\lambda}_{S_*} \cdots \tilde{\lambda}_{S_*}} = 0. \tag{47}$$

Then, from (19), we find that on  $\mathcal{R}_1$ ,

$$\bar{A}_S \Big|_{\mathcal{R}_1} = 0, \tag{48}$$

while singletons remain,  $\bar{A}_i = 1$ . This collapses the recursion. Using the cyclicity of the color-ordered amplitude, we may write

$$A_{1\cdots n} = A_{2\cdots n1}. (49)$$

Now apply the recursion (21) to  $A_{2\cdots n1}$ , *i.e.*, partition the ordered set  $(2,3,\ldots,n)$ . By (48), the only nonzero contribution is the all-singleton partition  $(2|3|\cdots|n)$ , so

$$A_{2\cdots n1}\Big|_{\mathcal{R}_1} = -\widehat{PT}_{\tilde{\lambda}_2\tilde{\lambda}_3\cdots\tilde{\lambda}_n}\Big|_{\mathcal{R}_1}.$$
 (50)

<span id="page-5-1"></span>But since  $V_{\tilde{\lambda}_2\cdots\tilde{\lambda}_n}=0$ , we have  $\widehat{\text{PT}}=V-\bar{V}=-\bar{V}$  for this list. Therefore,

$$A_{1\cdots n}\Big|_{\mathcal{R}_1} = A_{2\cdots n1}\Big|_{\mathcal{R}_1} = \bar{V}_{\tilde{\lambda}_2\cdots\tilde{\lambda}_n}.$$
 (51)

This proves the collapse of the recursion (21) to (41).

<span id="page-5-4"></span><span id="page-5-3"></span>3. Evaluating 
$$\bar{V}_{\tilde{\lambda}_2 \cdots \tilde{\lambda}_n}$$

Last but not least, we reorganize the vertex in terms of sign functions. Recall that  $\bar{V}_{\tilde{\lambda}_2...\tilde{\lambda}_n}$  is defined as

$$\bar{V}_{\tilde{\lambda}_2 \dots \tilde{\lambda}_n} = \prod_{n=2}^n \operatorname{sg}_{m,m+1} \Theta\left(\frac{\left[\tilde{\lambda}_2 \dots m \tilde{\lambda}_{m+1 \dots n}\right]}{\left[\tilde{\lambda}_m \tilde{\lambda}_{m+1}\right]}\right).$$
 (52)

By momentum conservation,  $\tilde{\lambda}_{m+1\cdots n} = -\tilde{\lambda}_1 - \tilde{\lambda}_{2\cdots m}$ , and using the antisymmetry of the bracket, (52) becomes

$$\bar{V}_{\tilde{\lambda}_{2}\cdots\tilde{\lambda}_{n}} = \prod_{m=2}^{n-1} \operatorname{sg}_{m,m+1} \Theta\left(\frac{\left[\tilde{\lambda}_{1}\tilde{\lambda}_{2}\cdots m\right]}{\left[\tilde{\lambda}_{m}\tilde{\lambda}_{m+1}\right]}\right).$$
 (53)

Using the relation between the sg and  $\Theta$  functions, one readily finds that

$$\bar{V}_{\tilde{\lambda}_2 \dots \tilde{\lambda}_n} = \frac{1}{2^{n-2}} \prod_{m=2}^{n-1} \left( \operatorname{sg}_{m,m+1} + \operatorname{sg}\left( \left[ \tilde{\lambda}_1 \tilde{\lambda}_2 \dots m \right] \right) \right).$$
 (54)

Combining (51) with (54) recovers exactly our final result (39).

# <span id="page-5-5"></span>ACKNOWLEDGMENTS

<span id="page-5-2"></span>We are grateful to Nima Arkani-Hamed, Freddy Cachazo, Juan Maldacena, Mark Spradlin and Anastasia Volovich for useful discussions. AL was supported in part by NSF grant AST-2307888, the NSF CAREER award PHY-2340457, and the Simons Foundation grant SFI-MPS-BH-00012593-09. AG acknowledges the Roger Dashen membership at the IAS, and additional support from DOE grant DE-SC0009988. AS & DS are supported in part by the Simons Collaboration for Celestial Holography. DS is also supported by the STFC (UK) grant ST/X000664/1. AS is supported by the Black Hole Initiative and DOE grant DE-SC/0007870, and is grateful for the hospitality of OpenAI where this project was completed.

<span id="page-5-0"></span><sup>&</sup>lt;sup>10</sup> It is very reminiscent of the largest-time equation in time-ordered perturbation theory [23].

# <span id="page-6-3"></span><span id="page-6-2"></span><span id="page-6-0"></span>Appendix A: The master identity

Consider the well-known identity

$$\left[\frac{a_1}{(b_2 + i\epsilon)} + \frac{a_2}{(b_1 + i\epsilon)}\right] \delta(a_1b_1 + a_2b_2) = -\frac{i}{2}[sg(a_1) + sg(a_2)]\delta(b_1)\delta(b_2), \tag{A1}$$

which readily follows from writing  $\frac{1}{b+i\epsilon} = \text{PV}\frac{1}{b} - \frac{i}{2}\delta(b)$ , where the  $\delta$ -function is normalized as in (7). In this appendix, we use manipulations from time-ordered perturbation theory to derive a powerful generalization of this identity:

$$\delta\left(\sum_{k=1}^{n} a_{k} b_{k}\right) \sum_{i=1}^{n} \frac{a_{i}}{\prod_{j \neq i} (b_{j} + i\epsilon)}$$

$$= \frac{1}{(2i)^{n-1}} \left[\sum_{i_{1}} \operatorname{sg}(a_{i_{1}}) + \sum_{i_{1} < i_{2} < i_{3}} \operatorname{sg}(a_{i_{1}} a_{i_{2}} a_{i_{3}}) + \sum_{i_{1} < \dots < i_{5}} \operatorname{sg}(a_{i_{1}} a_{i_{2}} a_{i_{3}} a_{i_{4}} a_{i_{5}}) + \dots\right] \prod_{i=1}^{n} \delta(b_{i}). \tag{A2}$$

For example, when n = 3, this generalizes the identity (A1) to

LHS = 
$$\delta \left( \sum_{i=1}^{3} a_i b_i \right) \left[ \frac{a_1}{(b_2 + i\epsilon)(b_3 + i\epsilon)} + \frac{a_2}{(b_1 + i\epsilon)(b_3 + i\epsilon)} + \frac{a_3}{(b_1 + i\epsilon)(b_2 + i\epsilon)} \right]$$
 (A3)

$$= RHS = -\frac{1}{4}[sg(a_1) + sg(a_2) + sg(a_3) + sg(a_1)sg(a_2)sg(a_3)]\delta(b_1)\delta(b_2)\delta(b_3). \tag{A4}$$

To establish the generalized identity (A2), we prove its Fourier transform, that is, the corresponding identity in the time domain where we may think of the  $b_i$  as energies. We then have the following:

$$\int d^n b \, e^{i \sum t_k b_k} \delta\left(\sum_{k=1}^n a_k b_k\right) \sum_{i=1}^n \frac{a_i}{\prod_{j \neq i} (b_j + i\epsilon)}$$

$$= \sum_{i=1}^n \int d\gamma \int d^n b \, e^{i \sum (t_k - \gamma a_k) b_k} \frac{a_i}{\prod_{j \neq i} (b_j + i\epsilon)} = (-2\pi i)^{n-1} \sum_{i=1}^n \int_{-\infty}^{\infty} d\gamma \, \delta(t_i - \gamma a_i) a_i \prod_{j \neq i} \Theta(-t_j + \gamma a_j)$$
(A5)

$$= (-2\pi i)^{n-1} (2\pi) \int_{-\infty}^{\infty} d\gamma \sum_{i=1}^{n} \frac{\partial}{\partial \gamma} \Theta(-t_i + \gamma a_i) \prod_{j \neq i} \Theta(-t_j + \gamma a_j) = (-2\pi i)^{n-1} (2\pi) \left[ \prod_{i=1}^{n} \Theta(-t_i + \gamma a_i) \right]_{\gamma = -\infty}^{\gamma = \infty}$$
(A6)

$$= (-2\pi i)^{n-1} (2\pi) \left[ \prod_{i=1}^{n} \Theta(a_i) - \prod_{i=1}^{n} \Theta(-a_i) \right]. \tag{A7}$$

Finally, Fourier transforming in  $t_i$  yields

$$\delta\left(\sum_{k=1}^{n} a_{k} b_{k}\right) \sum_{i=1}^{n} \frac{a_{i}}{\prod_{j \neq i} (b_{j} + i\epsilon)} = i^{1-n} \prod_{i=1}^{n} \Theta(a_{i}) \delta(b_{i}) - i^{1-n} \prod_{i=1}^{n} \Theta(-a_{i}) \delta(b_{i}), \tag{A8}$$

which recovers the master identity after using  $\Theta(x) = \frac{1+\operatorname{sg}(x)}{2}$ .

# <span id="page-6-1"></span>Appendix B: Derivation of recursion relation

This appendix derives the Berends–Giele recursion relation [15] for the off-shell currents in Yang–Mills theory. In turn, this implies a recursion formula for the planar form factors of the theory.

## 1. Berends-Giele Recursion

In QFT, n-point scattering amplitudes can be computed from form factors  $\mathcal{F}_S$  with one leg off-shell and n-1 legs on-shell. For a color-ordered gluon amplitude, the ordering is inherited from the corresponding form factor.

To avoid notational clutter, we have here taken the last particle to be negative helicity (as opposed to the first one in the main text). The final on-shell formula is insensitive to this choice. We thus write

$$\mathcal{A}_{1\cdots n} = \lim_{p_n^2 \to 0} -ip_n^2 \mathcal{F}_{1\cdots n-1} \, \delta^4 \left( \sum_{i=1}^n p_i \right), \qquad p_n = -\sum_{i=1}^{n-1} p_i.$$
 (B1)

These planar coefficients satisfy the Berends–Giele (BG) recursion, equivalent to summing over Feynman diagrams with one leg off-shell. When the rest of the (on-shell) legs are plus-helicity gluons, it is known that this recursion is equal to the one in Self-Dual Yang–Mills theory (SDYM) [16, 24], which reads

$$\mathcal{F}_{1\cdots m} = \frac{1}{p_{1\cdots m}^2 + i\epsilon} \sum_{j=1}^{m-1} \left[ \tilde{\lambda}_{1\cdots j} \tilde{\lambda}_{j+1\cdots m} \right] \mathcal{F}_{1\cdots j} \mathcal{F}_{j+1\cdots m}, \tag{B2}$$

where  $p_{1\cdots m} = \sum_{i=1}^{m} p_i$  and  $\tilde{\lambda}_{1\cdots m} = \sum_{i=1}^{m} \tilde{\lambda}_i$ . This is essentially the equation of motion of the theory and determines its classical solutions.

#### <span id="page-7-3"></span><span id="page-7-2"></span><span id="page-7-0"></span>2. General form factor

The form factor recursion (B2) is solved by means of our two-dimensional preamplitudes  $\bar{A}_S$  in (19), by "replacing one vertex by PT" where PT refers to the incomplete Parke-Taylor factor (12). Let  $(S_1|\cdots|S_A)$  be an ordered partition of the word  $(1\cdots m)$ , and write the block momenta  $K_a = \sum_{i \in S_a} \tilde{\lambda}_i$ . We claim the solution to the recursion (B2) is

<span id="page-7-1"></span>
$$\mathcal{F}_{1\cdots m} = \sum_{\alpha \cdot \mathbf{p}} \operatorname{PT}_{K_1 \cdots K_A} \prod_{a=1}^{A} \left( \bar{A}_{S_a} \, \delta_{S_a} \right), \tag{B3}$$

where the sum is over all possible ordered partitions of  $(1 \cdots m)$  into A blocks  $S_a$ , as well as over the number  $A = 1, \ldots, m$  of blocks. As in the main text,  $\delta_{S_a}$  denotes the product of  $\delta(z_{i,i+1})$  internal to the block  $S_a$ . To see this, we first establish (23), which we quote again here for the benefit of the reader:

$$PT_{1\cdots n} - \delta_{1\cdots n} V_{\tilde{\lambda}_1\cdots\tilde{\lambda}_n} = \sum_{j=1}^{n-1} \frac{\left[\tilde{\lambda}_{1\cdots j}\tilde{\lambda}_{j+1\cdots n}\right]}{p_{1\cdots n}^2 + i\epsilon} PT_{1\cdots j} PT_{j+1\cdots n}.$$
(B4)

Away from the half-collinear regime, we have  $\delta_{1\cdots n}=0$ , the  $i\epsilon$ 's on the RHS may be neglected, and this identity is a standard algebraic identity for Parke-Taylor factors. The  $i\epsilon$ 's are important in the half-collinear limit and the general identity (B4) follows from (A2) with the values

$$a_r = -\left[\tilde{\lambda}_{1\cdots r}\tilde{\lambda}_{r+1\cdots n}\right] \prod_{\ell \neq r} \left[\tilde{\lambda}_{\ell}\tilde{\lambda}_{\ell+1}\right], \qquad b_r = p_{r,r+1}^2, \tag{B5}$$

for  $r = 1, \ldots, n-1$ , while  $a_n = \prod_{\ell} [\ell, \ell+1]$  and  $b_n = p_{1...n}^2$ .

Next, we will verify (B3) is a solution by inserting it into the RHS of (B2). For each term in the sum over j in (B2), we now have sums over all ordered partitions  $(1 \cdots j) = (L_1 | \cdots | L_B)$  and  $(j + 1 \cdots m) = (R_1 | \cdots | R_C)$ :

$$\mathcal{F}_{1\cdots m} = \sum_{j=1}^{m-1} \sum_{\text{o.p.}} \frac{\left[\tilde{\lambda}_{1\cdots j} \tilde{\lambda}_{j+1\cdots m}\right]}{p_{1\cdots m}^2 + i\epsilon} \operatorname{PT}_{L_1 L_2 \cdots L_B} \operatorname{PT}_{R_1 R_2 \cdots R_C} \times \bar{A}_{L_1} \cdots \bar{A}_{L_B} \bar{A}_{R_1} \cdots \bar{A}_{R_C} \delta_{L_1} \cdots \delta_{L_B} \delta_{R_1} \cdots \delta_{R_C} , \tag{B6}$$

where we have abused notation slightly, denoting both the set and its block momentum by the same letter  $L_a$  or  $R_b$ . Note that  $\tilde{\lambda}_{1\cdots j} = \sum_k \tilde{\lambda}_{L_k}$  and  $\tilde{\lambda}_{j+1\cdots m} = \sum_k \tilde{\lambda}_{R_k}$ . The second line depends only on the total partition  $(S_1|\cdots|S_A) = (L_1|\cdots|L_B|R_1|\cdots|R_C)$ , with A = B + C, and does not know about the separation into "left" and "right". For a fixed such partition, the j-sum is exactly the PT recursion (B4): it produces (i) a PT for the combined partition, and (ii) a contact term  $\delta V$ .

In equations, we have

$$\mathcal{F}_{1\cdots m} = \sum_{\text{n.t.p.}} \bar{A}_{S_1} \cdots \bar{A}_{S_A} \delta_{S_1} \cdots \delta_{S_A} \left( \sum_{B+C=A} \frac{\left[\tilde{\lambda}_{1\cdots j} \tilde{\lambda}_{j+1\cdots m}\right]}{p_{1\cdots m}^2 + i\epsilon} \operatorname{PT}_{L_1\cdots L_B} \operatorname{PT}_{R_1\cdots R_C} \right)$$
(B7)

$$= \sum_{\text{n.t.p.}} \bar{A}_{S_1} \cdots \bar{A}_{S_A} \delta_{S_1} \cdots \delta_{S_A} \text{PT}_{S_1 S_2 \cdots S_A} - \delta_{1 \cdots m} \sum_{\text{n.t.p.}} \bar{A}_{S_1} \cdots \bar{A}_{S_A} V_{S_1 S_2 \cdots S_A}$$
(B8)

$$= \sum_{\mathbf{n.t.p.}} \bar{A}_{S_1} \cdots \bar{A}_{S_A} \delta_{S_1} \cdots \delta_{S_A} \operatorname{PT}_{S_1 S_2 \cdots S_A} + \delta_{1 \cdots m} \bar{A}_{1 \cdots m}, \tag{B9}$$

where n.t.p. denotes nontrivial partitions (having more than one block). The PT piece reproduces the nontrivial A-block contribution on the LHS of (B3). The contact piece  $\delta V$  precisely stitches blocks together by a V-vertex, and the resulting sum over nontrivial partitions is the recursion (19) for the preamplitudes. The final term in the third line is the missing 1-term partition, thus recovering (B3).

#### <span id="page-8-7"></span>3. LSZ Reduction

The single-minus amplitude is obtained by putting the "last" leg on-shell, as in (B1). On the support of the collinear  $\delta$ -functions inside each block of the form factor (B3), every block momentum  $K_a$  is null. The only remaining singular factor is the PT term associated to adjacent channels. The on-shell limit of a PT factor is evaluated using the master identity in App. A, resulting in

$$\lim_{p_n^2 \to 0} p_n^2 \operatorname{PT}_{K_1 \dots K_k} \delta^4 \left( \sum_{a=1}^k K_a + p_n \right) = \widehat{\operatorname{PT}}_{K_1 \dots K_k} \delta_{1 \dots k, n} \delta^2 \left( \sum_j \tilde{\lambda}_j \right) = (V_{K_1 \dots K_k} - \bar{V}_{K_1 \dots K_k}) \delta_{1 \dots k, n} \delta^2 \left( \sum_j \tilde{\lambda}_j \right). \tag{B10}$$

After stripping off the universal momentum-conservation support (here,  $\sum_{i=1}^{n} \tilde{\lambda}_i = 0$ , so  $\tilde{\lambda}_n = -\sum_{i=1}^{n-1} \tilde{\lambda}_i$ ), (B3) and (B10) yield, after some algebra, the final result (21):

$$A_{1\cdots n} = -\sum_{\substack{(1\cdots n-1)=S_1|\dots|S_k\\k\geq 1}} \widehat{PT}_{\tilde{\lambda}_{S_1}\cdots\tilde{\lambda}_{S_k}} \prod_{a=1}^k \bar{A}_{S_a}.$$
(B11)

- <span id="page-8-3"></span>[10] N. Arkani-Hamed and J. Trnka, "The Amplituhedron," JHEP 10 (2014) 030, arXiv:1312.2007 [hep-th].
- <span id="page-8-4"></span>[11] S. J. Parke and T. R. Taylor, "An amplitude for n-gluon scattering," Phys. Rev. Lett. 56 (1986) 2459–2460.
- [12] M. T. Grisaru and H. N. Pendleton, "Some Properties of Scattering Amplitudes in Supersymmetric Theories," *Nucl. Phys. B* **124** (1977) 81–92.

<span id="page-8-0"></span><sup>[1]</sup> T. Aoyama, T. Kinoshita, and M. Nio, "Revised and Improved Value of the QED Tenth-Order Electron Anomalous Magnetic Moment," *Phys. Rev. D* **97** no. 3, (2018) 036001, arXiv:1712.06060 [hep-ph].

<sup>[2]</sup> L. Morel, Z. Yao, P. Cladé, and S. Guellati-Khélifa, "Determination of the fine-structure constant with an accuracy of 81 parts per trillion," *Nature* 588 no. 7836, (2020) 61–65.

<span id="page-8-1"></span><sup>[3]</sup> X. Fan, T. G. Myers, B. A. D. Sukra, and G. Gabrielse, "Measurement of the Electron Magnetic Moment," *Phys. Rev. Lett.* 130 no. 7, (2023) 071801, arXiv:2209.13084 [physics.atom-ph].

<span id="page-8-2"></span><sup>[4]</sup> L. J. Dixon, "Calculating scattering amplitudes efficiently," in *Theoretical Advanced Study Institute in Elementary Particle Physics (TASI 95): QCD and Beyond*, pp. 539–584. 1, 1996. arXiv:hep-ph/9601359.

<span id="page-8-5"></span><sup>[5]</sup> E. Witten, "Perturbative gauge theory as a string theory in twistor space," Commun. Math. Phys. 252 (2004) 189–258, arXiv:hep-th/0312171.

<span id="page-8-6"></span><sup>[6]</sup> R. Roiban, M. Spradlin, and A. Volovich, "On the tree level S matrix of Yang-Mills theory," Phys. Rev. D 70 (2004) 026009, arXiv:hep-th/0403190.

<sup>[7]</sup> Z. Bern, L. J. Dixon, and V. A. Smirnov, "Iteration of planar amplitudes in maximally supersymmetric Yang-Mills theory at three loops and beyond," *Phys. Rev. D* 72 (2005) 085001, arXiv:hep-th/0505205.

<sup>[8]</sup> R. Britto, F. Cachazo, B. Feng, and E. Witten, "Direct proof of tree-level recursion relation in Yang-Mills theory," *Phys. Rev. Lett.* **94** (2005) 181602, arXiv:hep-th/0501052.

<sup>[9]</sup> N. Arkani-Hamed, J. L. Bourjaily, F. Cachazo, A. B. Goncharov, A. Postnikov, and J. Trnka, Grassmannian Geometry of Scattering Amplitudes. Cambridge University Press, 4, 2016. arXiv:1212.5605 [hep-th].

- <span id="page-9-7"></span>[13] H. Elvang and Y.-t. Huang, "Scattering Amplitudes," [arXiv:1308.1697 \[hep-th\]](http://arxiv.org/abs/1308.1697).
- <span id="page-9-0"></span>[14] Z. Bern, L. J. Dixon, D. C. Dunbar, and D. A. Kosower, "One loop n point gauge theory amplitudes, unitarity and collinear limits," Nucl. Phys. B 425 [\(1994\) 217–260,](http://dx.doi.org/10.1016/0550-3213(94)90179-1) [arXiv:hep-ph/9403226](http://arxiv.org/abs/hep-ph/9403226).
- <span id="page-9-1"></span>[15] F. A. Berends and W. T. Giele, "Recursive Calculations for Processes with n Gluons," Nucl. Phys. B 306 [\(1988\) 759–808.](http://dx.doi.org/10.1016/0550-3213(88)90442-7)
- <span id="page-9-2"></span>[16] D. Cangemi, "Selfdual Yang-Mills theory and one loop like - helicity QCD multi - gluon amplitudes," [Nucl. Phys. B](http://dx.doi.org/10.1016/S0550-3213(96)00586-X) 484 [\(1997\) 521–537,](http://dx.doi.org/10.1016/S0550-3213(96)00586-X) [arXiv:hep-th/9605208](http://arxiv.org/abs/hep-th/9605208).
- <span id="page-9-3"></span>[17] R. S. Ward and R. O. Wells, Twistor Geometry and Field Theory. Cambridge University Press, Cambridge, 1990.
- [18] R. S. Ward, "On self-dual gauge fields," Physics Letters A 61 [no. 2, \(1977\) 81–82.](http://dx.doi.org/10.1016/0375-9601(77)90842-8)
- <span id="page-9-4"></span>[19] M. F. Atiyah, N. J. Hitchin, V. G. Drinfeld, and Y. I. Manin, "Construction of instantons," [Physics Letters A](http://dx.doi.org/10.1016/0375-9601(78)90141-X) 65 no. 3, [\(1978\) 185–187.](http://dx.doi.org/10.1016/0375-9601(78)90141-X)
- <span id="page-9-5"></span>[20] A. Guevara, E. Himwich, M. Pate, and A. Strominger, "Holographic symmetry algebras for gauge theory and gravity," JHEP 11 [\(2021\) 152,](http://dx.doi.org/10.1007/JHEP11(2021)152) [arXiv:2103.03961 \[hep-th\]](http://arxiv.org/abs/2103.03961).
- <span id="page-9-6"></span>[21] A. Strominger, "w1+<sup>∞</sup> Algebra and the Celestial Sphere: Infinite Towers of Soft Graviton, Photon, and Gluon Symmetries," Phys. Rev. Lett. 127 [no. 22, \(2021\) 221601,](http://dx.doi.org/10.1103/PhysRevLett.127.221601) [arXiv:2105.14346 \[hep-th\]](http://arxiv.org/abs/2105.14346).
- <span id="page-9-8"></span>[22] N. Arkani-Hamed, F. Cachazo, C. Cheung, and J. Kaplan, "The S-Matrix in Twistor Space," JHEP 03 [\(2010\) 110,](http://dx.doi.org/10.1007/JHEP03(2010)110) [arXiv:0903.2110 \[hep-th\]](http://arxiv.org/abs/0903.2110).
- <span id="page-9-9"></span>[23] S. Caron-Huot, "Loops and trees," JHEP 05 [\(2011\) 080,](http://dx.doi.org/10.1007/JHEP05(2011)080) [arXiv:1007.3224 \[hep-ph\]](http://arxiv.org/abs/1007.3224).
- <span id="page-9-10"></span>[24] W. A. Bardeen, "Self-dual yang-mills theory, integrability and multiparton amplitudes," [Progress of Theoretical Physics](http://dx.doi.org/10.1143/PTPS.123.1) Supplement 123 [\(02, 1996\) 1–8.](http://dx.doi.org/10.1143/PTPS.123.1) <https://doi.org/10.1143/PTPS.123.1>.