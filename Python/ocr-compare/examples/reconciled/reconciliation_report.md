# OCR Reconciliation Report

- Nougat equations (tagged): 55
- Marker equations (tagged): 33
- **Agree (both match): 14**
- **Conflict (need review): 8**
- Marker-only (Nougat dropped): 11
- Nougat-only (Marker missed numbering): 16
- ⚠️ **Nougat tag-sequence gaps (likely dropped pages): 20-32, 36-38**
- ⚠️ **Nougat repeated equations: (10)×4, (11)×3, (12)×4, (13)×4, (14)×4, (15)×2, (16)×2, (17)×2**

## Conflicts to resolve (check against the PDF)

### eq (2)
- **nougat:** `|i\rangle=\lambda_{i}=(1,z_{i}),\qquad|i]=\tilde{\lambda}_{i}=\omega_{i}(1, \tilde{z}_{i}), \tag{2}`
- **marker:** `|i\rangle = \lambda_i = (1, z_i), \qquad |i\rangle = \tilde{\lambda}_i = \omega_i(1, \tilde{z}_i), \qquad (2)`

### eq (3)
- **nougat:** `\langle ij\rangle =\langle\lambda_{i}\lambda_{j}\rangle=\epsilon_{\alpha\beta} \lambda_{i}^{\alpha}\lambda_{j}^{\beta}, \tag{3}`
- **marker:** `\langle ij\rangle = \langle \lambda_i \lambda_j \rangle = \epsilon_{\alpha\beta} \lambda_i^{\alpha} \lambda_i^{\beta}, \tag{3}`

### eq (5)
- **nougat:** `\langle ij\rangle=z_{ij},\qquad[ij]=\omega_{i}\omega_{j}\tilde{z}_{ij}, \tag{5}`
- **marker:** `\langle ij \rangle = z_{ii}, \qquad [ij] = \omega_i \omega_i \tilde{z}_{ii}, \qquad (5)`

### eq (14)
- **nougat:** `\epsilon_{1}^{-}=\sqrt{2}\frac{|r\rangle\langle 1|}{[r1]},\qquad\epsilon_{a}^{+} =\sqrt{2}\frac{|r\rangle[a]}{\langle ra\rangle}\qquad\text{for $a\geq 2$}, \tag{14}`
- **marker:** `\epsilon_1^- = \sqrt{2} \frac{|r]\langle 1|}{[r1]}, \qquad \epsilon_a^+ = \sqrt{2} \frac{|r\rangle[a|}{\langle ra\rangle} \qquad \text{for } a \ge 2, \quad (14)`

### eq (16)
- **nougat:** `\mathcal{A}_{n}=i^{2-n}\Big{|}\frac{\omega_{1}}{\omega_{2}\omega_{3}\cdots \omega_{n}}\Big{|}A_{1\cdots n}\prod_{a=2}^{n}\delta(z_{1a})\,\delta^{2} \Biggl{(}\sum_{i=1}^{n}\sqrt{|\omega_{i}|}\tilde{\lambda}_{i}\Biggr{)}. \tag{16}`
- **marker:** `\mathcal{A}_n = i^{2-n} A_{1\cdots n} \prod_{a=2}^n \delta(z_{1a}) \, \delta^2 \left( \sum_{i=1}^n \tilde{\lambda}_i \right). \tag{16}`

### eq (40)
- **nougat:** `V_{\bar{\lambda}_{2}\cdots\bar{\lambda}_{n}}\Big{|}_{\mathcal{R}_{1}}=0, \tag{40}`
- **marker:** `V_{\tilde{\lambda}_2 \cdots \tilde{\lambda}_n} \Big|_{\mathcal{R}_1} = 0, \tag{40}`

### eq (47)
- **nougat:** `V_{\tilde{\lambda}_{S_{1}}\cdots\tilde{\lambda}_{S_{k}}}=0. \tag{47}`
- **marker:** `V_{\tilde{\lambda}_{S_*} \cdots \tilde{\lambda}_{S_*}} = 0. \tag{47}`

### eq (48)
- **nougat:** `\left.\bar{A}_{S}\right|_{\mathcal{R}_{1}}=0, \tag{48}`
- **marker:** `\bar{A}_S \Big|_{\mathcal{R}_1} = 0, \tag{48}`


## Marker-only equations (Nougat lost these)

- (20) `V_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} = \prod_{k=1}^{n-1} \operatorname{sg}_{k,k+1} \Theta\left(-\frac{\left[\tilde{\lambda}_1 \dots_k \tilde{\lambda}_{k+1} \dots_m\right]}{\left[\tilde{\lambda}_k \tilde{\lambda}_{k+1}\right]}\right), \quad (20)`
- (21) `A_{1\cdots n} = -\sum_{\text{o.p.}} \widehat{PT}_{\tilde{\lambda}_{S_1}\cdots\tilde{\lambda}_{S_A}} \prod_{a=1}^A \bar{A}_{S_a}, \qquad (21)`
- (22) `\widehat{\text{PT}}_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} = V_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n} - \bar{V}_{\tilde{\lambda}_1 \dots \tilde{\lambda}_n}, \tag{22}`
- (23) `= \sum_{j=1}^{n-1} \frac{\left[\tilde{\lambda}_{1\cdots j}\tilde{\lambda}_{j+1\cdots n}\right]}{p_{1\cdots n}^2 + i\epsilon} PT_{1\cdots j} PT_{j+1\cdots n}, \qquad (23)`
- (24) `A_{12\cdots n} = A_{2\cdots n1}. (24)`
- (25) `A_{12\cdots n} = (-1)^n A_{n\cdots 21}. (25)`
- (26) `A_{12\cdots n} + A_{13\cdots n2} + A_{14\cdots 23} + \dots = 0. \tag{26}`
- (27) `A_{12345} + A_{12354} + A_{12435} + A_{14235} = 0. (27)`
- (28) `\lim_{\omega_n \to 0} A_{1\cdots n} = \frac{1}{2} (\operatorname{sg}_{n-1,n} + \operatorname{sg}_{n1}) A_{1\cdots n-1}. \tag{28}`
- (29) `A_{123} = sg_{12}, (29)`
- (30) `A_{1234} = \frac{1}{2} (sg_{23} sg_{41} + sg_{12} sg_{34}); \tag{30}`