# Recorded experiment report

Status: **complete**. Successful fits: 90/90.

Paired seeds: `[11, 22, 33]`; train sizes: `[32, 128, 512]`; absolute noise SD: `[0.0, 0.1, 0.5]`. Reference n=512.

All values below are read from saved CSV/JSON files. Sample SD uses ddof=1; a single seed has no SD. Failures do not enter metric means.

## Protocol

ID inputs are uniform on [-2,2]². OOD inputs are uniform on the part of [-4,4]² outside that square. Independent streams generate each split. Train sizes are nested prefixes; held-out sets stay fixed. Observed targets include independent Gaussian noise; clean targets evaluate the latent law.

Polynomial degree is fixed before evaluation. Feature and target scaling use training data only. MLP restores its best validation checkpoint. PySR searches training data with one common operator grammar across datasets; validation RMSE selects its candidate. True formulas are never search inputs.

## Reference-condition results

| Dataset | Model | Split | Seeds | RMSE mean ± SD | MAE mean | R² mean | Fit seconds mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | mlp | ood | 3 | 7.656 ± 0.1421 | 5.322 | 0.5988 | 1.2 |
| A | mlp | test | 3 | 0.04967 ± 0.01181 | 0.03137 | 0.9998 | 1.2 |
| A | polynomial | ood | 3 | 3.319e-14 ± 1.856e-14 | 2.612e-14 | 1 | 0.00683 |
| A | polynomial | test | 3 | 3.763e-15 ± 1.466e-15 | 2.775e-15 | 1 | 0.00683 |
| B | mlp | ood | 3 | 2.101 ± 0.102 | 1.543 | 0.2966 | 1.03 |
| B | mlp | test | 3 | 0.01752 ± 0.0008377 | 0.01298 | 0.9997 | 1.03 |
| B | polynomial | ood | 3 | 1.317 ± 0.09554 | 0.82 | 0.7239 | 0.00669 |
| B | polynomial | test | 3 | 0.008745 ± 0.0004429 | 0.00742 | 0.9999 | 0.00669 |
| C | mlp | ood | 3 | 0.2044 ± 0.02631 | 0.09192 | 0.9656 | 1.36 |
| C | mlp | test | 3 | 0.01914 ± 0.003842 | 0.01094 | 0.9992 | 1.36 |
| C | polynomial | ood | 3 | 2.567 ± 0.08786 | 1.714 | -4.37 | 0.00819 |
| C | polynomial | test | 3 | 0.114 ± 0.001262 | 0.08664 | 0.9718 | 0.00819 |

## Formula recovery

Symbolic recovery requires SymPy to simplify the unrounded expression difference to exactly zero AND finite unsimplified evaluation on the probes. Algebraic equality alone can conceal removable domain holes; it is saved separately as symbolic_equivalent. Failure to prove zero is recorded as not proven, not mathematical inequivalence. Numerical recovery uses 1,030 independent ID/OOD/special-point probes, atol=rtol=1e-5; it is finite evidence of approximation and is **not** symbolic equivalence.

| Dataset | Model | Successful expressions | Symbolic + domain rate | Numerical rate |
| --- | --- | --- | --- | --- |
| A | polynomial | 3 | 0.0% | 100.0% |
| B | polynomial | 3 | 0.0% | 0.0% |
| C | polynomial | 3 | 0.0% | 0.0% |

### Selected expressions (first recorded seed)

- A / polynomial: `1.3993943785212546e-16*x0**3 - 3.0293544569515486e-16*x0**2*x1 + 1.9999999999999993*x0**2 - 3.9619842725252886e-16*x0*x1**2 - 6.826874622471235e-16*x0*x1 + 8.891639703451893e-16*x0 - 3.8259719010084646e-16*x1**3 + 1.5469359281483098e-16*x1**2 - 2.999999999999998*x1 + 1.0000000000000004` (PySR complexity: nan; SymPy nodes: 44)
- B / polynomial: `-0.13285377425359537*x0**3 - 4.328767448997366e-5*x0**2*x1 + 0.0005660801900727072*x0**2 + 0.0004147272770973939*x0*x1**2 - 3.060588365233004e-5*x0*x1 + 0.9713185772423192*x0 + 0.00011207295777825316*x1**3 + 0.49993805924844104*x1**2 - 0.00031517103138451125*x1 - 0.0005116658907701188` (PySR complexity: nan; SymPy nodes: 44)
- C / polynomial: `0.012659934403198136*x0**3 + 0.0011198603498092962*x0**2*x1 + 0.003616556218896112*x0**2 - 0.20313553302733414*x0*x1**2 - 0.005696401070446813*x0*x1 + 0.8006430212997978*x0 - 0.003357726212634277*x1**3 - 0.004081331982397508*x1**2 + 0.009394228668194398*x1 + 0.006795655133092063` (PySR complexity: nan; SymPy nodes: 44)

## Figures

![truth_prediction](figures/truth_prediction.png)
![noise_robustness](figures/noise_robustness.png)
![data_efficiency](figures/data_efficiency.png)
![id_ood](figures/id_ood.png)
![pareto_frontier](figures/pareto_frontier.png)

## Limitations and evidence boundaries

- These are synthetic two-variable laws, not a real-data benchmark.
- Search is budget limited and stochastic. No algorithm is assumed superior.
- Seed SD is not a confidence interval or a significance test.
- Time budgets, epoch budgets and degree constraints are not compute matched.
- PySR timing includes first-use initialization/JIT where incurred; other fits reuse the process. Per-fit timing scopes are saved in model.json.
- Wall-clock stopping can change search trajectories even in serial mode.
- PySR tree complexity, SymPy node count and MLP parameter count differ.
- Finite numeric probes cannot prove equality of full mathematical domains.
- Saved CSVs preserve measured predictions. Reruns reproduce the protocol; wall-clock search limits and hardware can change selected equations.

## Failed fits

None.

## Reproduction

The complete config, environment versions, source SHA256 hashes, data SHA256 hashes and per-fit parameters are in manifest.json and fits/. metrics.csv is the raw metric source; summary.csv contains group means/SD. Regenerate figures with `python -m symbolic_discovery plot --results PATH`.
