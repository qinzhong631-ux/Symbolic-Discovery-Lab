# Experimental design and interpretation

## Research question

When does an interpretable symbolic model recover the generating law, and when
does a flexible predictor achieve low interpolation error without discovering
that law? The project compares model families rather than presenting PySR as a
guaranteed winner. Its contribution is experimental engineering, leakage control,
and analysis; the evolutionary symbolic search itself is upstream PySR.

## Generating laws and distributions

| Dataset | Latent law | Distinct challenge |
| --- | --- | --- |
| A | `2*x0**2 - 3*x1 + 1` | Low-degree polynomial, exactly representable by the baseline |
| B | `sin(x0) + 0.5*x1**2` | Trigonometric structure versus local polynomial approximation |
| C | `x0/(1+x1**2)` | Rational structure and denominator-dependent extrapolation |

Every split has independently sampled inputs and independent Gaussian label
noise. ID inputs are uniform in `[-2,2]^2`. OOD inputs follow the uniform square
`[-4,4]^2` conditioned on at least one coordinate outside `[-2,2]`. Thus every
OOD point lies outside the entire ID support. This tests support shift rather
than just a wider mixture containing training-domain points.

SeedSequence spawns separate streams for each split's features and noise.
Across noise levels features stay identical. Across sample sizes, training data
are nested prefixes, and validation/test/OOD arrays remain fixed. Models in a
condition receive exactly the same observed targets. The true law is retained
only by generation/evaluation modules; no law string, coefficient guess,
template or dataset identity enters the model adapters.

## Methods and selection

- **PySR:** common grammar `+`, `-`, `*`, `/`, `sin` for all datasets; no power
  operator and no nested sine; maxsize=20 by default. This grammar makes every
  target representable without exposing its structure. The search uses serial,
  deterministic mode and Float64. It returns a training-loss complexity front;
  the candidate with smallest observed validation RMSE is selected. Validation
  never enters the evolutionary search. Complexity breaks exact RMSE ties.
- **Polynomial:** degree 3 fixed a priori across all datasets, feature expansion,
  train-only StandardScaler, ordinary least squares. A simpler hypothesis class
  provides a strong and intentionally well-specified baseline on A.
- **MLP:** two width-64 Tanh layers, scalar output, train-only feature/target
  standardization, CPU Float32 full-batch Adam, learning rate 0.003, no weight
  decay. Patience stops training; the lowest validation-MSE checkpoint is restored.

The same validation split informs both symbolic candidate selection and MLP
early stopping. Test/OOD scores and recovery are computed after model selection.
No hyperparameter sweep is conducted on test data.

## Four experiments

1. **Formula recovery:** zero-noise reference sample count; report unrounded
   selected expressions, PySR tree complexity, SymPy nodes and predictive error.
2. **Noise robustness:** reference sample count at each absolute Gaussian SD;
   compare observed RMSE and latent-law RMSE separately. Observed-target error
   has irreducible label noise, so it cannot alone diagnose law recovery.
3. **Data efficiency:** zero-noise nested sizes, fixed held-out sets; use paired
   seeds across model families and train sizes.
4. **Extrapolation:** evaluate each fitted model on both ID and OOD; use clean
   targets for the headline support-shift comparison. OOD is never used for fitting,
   early stopping or equation selection.

The runner evaluates the union of these conditions once, sharing the zero-noise
reference condition. It does not claim an exhaustive noise-by-size factorial study.

## Metrics and formula-recovery accuracy

RMSE, MAE and R² are from scikit-learn. Group statistics use seed-level metric
means and **sample** SD (ddof=1); single-seed SD is unavailable, never reported as
zero. Each group records the number of successful seeds. Failed fits remain in
the manifest with error traces and are excluded from metric means.

Algebraic equivalence is recorded when SymPy simplifies `candidate - truth` to
exactly zero. The symbolic recovery rate additionally requires finite evaluation
of the unsimplified expression on all numeric probes. Coefficients are neither
rounded nor rationalized. A failure of simplification is labeled “not proven”.
This is a conservative operational check, not a complete theorem prover or a
proof of equality of full mathematical domains. Arithmetic-tree parsing preserves
removable holes such as `x0*x1/x1` at `x1=0`, which eager simplification would hide.

Numerical recovery uses 512 fresh ID points, 512 points in the wider square and
six special points, including zeros, at atol=rtol=1e-5. All predictions must be
finite. This criterion is a finite probe of approximate functional agreement,
**not strict symbolic equivalence** or proof across the full real domain.
Recovery probes are independent of training/validation/test samples and have a
fixed, recorded probe seed. They never select or refine a discovered expression.

Formula recovery is meaningful for PySR and the polynomial expression. MLP has
no discovered formula; its recovery field is not applicable rather than zero.
PySR expression complexity, SymPy node count, polynomial coefficients and MLP
trainable parameters measure different objects; the Pareto chart uses PySR
complexity only. All candidate validation errors are preserved.

Training time records the actual adapter fit duration. PySR includes import,
search and validation selection, including initialization/JIT when incurred.
MLP includes initialization, preprocessing, training and checkpoint restoration.
These budgets are deliberately practical, **not compute-matched**. Wall-clock
search termination can affect repeated trajectories even in deterministic serial
mode; exact bitwise search reproduction is not promised across CPUs.

## Recorded evidence

- [CPU smoke run](../results/smoke/REPORT.md): one seed, short training; functional
  evidence only, unsuitable for algorithm ranking.
- [Paired baseline study](../results/baselines/REPORT.md): 90 successful fits,
  three datasets × five unique conditions × three seeds × two models.
- [Three-model study](../results/quick/REPORT.md): 135 successful fits, the same
  paired conditions with PySR added; PySR 2.7.0 / Julia 1.11.9.

The zero-noise n=512 baseline results already show why there is no universal
ranking: polynomial regression represents A exactly to numerical precision,
while the MLP better approximates C, particularly outside the training square.
The three-model study also shows a budget-dependent failure to recover C in two
of three zero-noise n=512 searches. MLP's mean C OOD RMSE is 0.2044 ± 0.02631,
versus PySR's 1.593 ± 1.673 and polynomial regression's 2.567 ± 0.08786.
These are descriptive results from three paired seeds, not significance claims.

PySR's reference-condition symbolic recovery rates with finite domain probes are
100% for A, 66.7% for B and 33.3% for C. Numerical recovery rates are 100%, 100%
and 33.3%, respectively. B's remaining seed has a near-exact fitted coefficient,
which meets numeric tolerance but is not strict algebraic equivalence. All
unrounded expressions and individual seed scores are retained.

### Evaluation audit

The first evaluation eagerly parsed exported expressions, which could cancel
removable domain holes. Tests demonstrated the error with `x0*x1/x1` versus `x0`.
The corrected evaluator parses arithmetic without cancellation for numeric probes.
Saved expressions were reevaluated without refitting or selecting new models.
`formula_recovery.initial.csv` retains the initial output and
`evaluation_revision.json` records the correction and source hashes. Prediction
RMSE/MAE/R² values were not altered. The current CSVs/reports use the corrected
evaluation. The final source additionally initializes Julia before importing
PyTorch to follow JuliaCall's interoperability guidance; the final integrated
smoke test verifies that path.

The final review also found that default-precision SymPy Float printing could
lose the last digits of polynomial coefficients. The exporter now retains raw
binary64 coefficients and prints 17 significant decimal digits. Historical
polynomial expressions were reconstructed deterministically from the original
saved training arrays; their predictions were checked against the saved CSVs.
Only expression exports/recovery evaluation changed, not measured metric records.
`polynomial_export_revision.json` and per-model `model.before_precision_fix.json`
preserve this audit. PySR and MLP were not refitted for this correction. No reported
polynomial symbolic-recovery success was affected.

## Scope, limitations and next experiments

This is an exploratory, controlled study of three two-variable synthetic laws,
not a claim of algorithmic novelty or a substitute for a broad symbolic-regression
benchmark. Three seeds give descriptive variability rather than strong inference.
No significance tests or confidence intervals are asserted. Degree-3 polynomial
regression is particularly favorable on A; fixed Tanh MLPs can saturate outside
their training domain. A short common PySR grammar may waste search on operators
that a domain-informed scientist would exclude.

`configs/reference.json` expands to five seeds and longer searches. It is a
reproduction option, not evidence of an executed study. Useful next steps are
evaluation-count-matched budgets, larger multi-seed runs, domain-informed grammar
ablations declared before testing, wider OOD shells, correlated features, real
measurement datasets, uncertainty estimates and controlled coefficient rounding
reported separately from strict recovery.
