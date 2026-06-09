# Conflict Resolutions (vision pass)

Model: claude-code (opus-4.8, vision)

| eq | page | winner | conf | corrected LaTeX |
|----|------|--------|------|-----------------|
| (2) | 2 | **nougat** | high | `\|i\rangle=\lambda_{i}=(1,z_{i}),\qquad\|i]=\tilde{\lambda}_{i}=\omega_{i}(1,\tilde{z}_{i})` |
| (3) | 2 | **nougat** | high | `\langle ij\rangle=\langle\lambda_{i}\lambda_{j}\rangle=\epsilon_{\alpha\beta}\lambda_{i}^{\alpha}\lambda_{j}^{\beta}` |
| (5) | 2 | **nougat** | high | `\langle ij\rangle=z_{ij},\qquad[ij]=\omega_{i}\omega_{j}\tilde{z}_{ij}` |
| (6) | 2 | **marker** | high | `\epsilon_j^-=\sqrt{2}\,\frac{\|r]\langle j\|}{[rj]},\qquad\epsilon_k^+=\sqrt{2}\,\frac{\|k]\langle r\|}{\langle rk\rangle}` |
| (14) | 3 | **both_wrong** | high | `\epsilon_1^-=\sqrt{2}\,\frac{\|r]\langle 1\|}{[r1]},\qquad\epsilon_a^+=\sqrt{2}\,\frac{\|r\rangle[a]}{\langle ra\rangle}\qquad\text{for }a\ge2` |
| (16) | 3 | **marker** | high | `\mathcal{A}_n=i^{2-n}A_{1\cdots n}\prod_{a=2}^{n}\delta(z_{1a})\,\delta^{2}\!\left(\sum_{i=1}^{n}\tilde{\lambda}_{i}\right)` |
| (40) | 5 | **marker** | high | `V_{\tilde{\lambda}_2\cdots\tilde{\lambda}_n}\Big\|_{\mathcal{R}_1}=0` |
| (41) | 5 | **marker** | high | `A_{1\cdots n}\big\|_{\mathcal{R}_1}=\bar{V}_{\tilde{\lambda}_2\cdots\tilde{\lambda}_n}\Big\|_{\mathcal{R}_1}` |
| (47) | 6 | **nougat** | high | `V_{\tilde{\lambda}_{S_1}\cdots\tilde{\lambda}_{S_k}}=0` |
| (48) | 6 | **both_correct** | high | `\bar{A}_S\big\|_{\mathcal{R}_1}=0` |