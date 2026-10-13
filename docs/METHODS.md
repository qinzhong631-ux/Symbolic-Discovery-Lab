# Mathematical and algorithmic notes

## Symbolic regression and model selection

A candidate is an expression tree whose leaves are variables/constants and whose
internal nodes are operators. PySR searches tree structures with a multi-population
evolutionary algorithm, mutation/selection, simplification and numerical constant
optimization. That algorithm is upstream software, not original code in this lab.
The loss on observed training labels is mean squared error:

`L(f) = (1/N) * sum_i (f(x_i) - y_i)^2`.

Complexity discourages unnecessary structure and produces an accuracy-complexity
front. Neither smaller complexity nor lower training loss alone identifies the
true law. This project's adapter selects the candidate minimizing observed
validation RMSE, with complexity only breaking exact ties. It does not select
by test error or closeness to the known formula.

For the plotting frontier, candidate j dominates i when j has both no greater
complexity and no greater validation error, with at least one strict inequality.
The plotted nondominated set is recomputed from the preserved validation scores;
it can differ from PySR's training-loss front.

The common grammar makes all targets representable: squaring is multiplication,
not an oracle-specific square template. Its division/sine operators can also
produce misleading families or singular arithmetic. A minimal grammar declared
before data analysis reduces search burden; changing it after seeing test scores
would invalidate an unqualified comparison.

## Polynomial least squares

For two inputs and degree 3, the basis has `binomial(2+3,3)-1 = 9` nonconstant
monomials, plus an intercept. These include x0, x1, x0², x0*x1, x1² and degree-3
terms. Least squares optimizes coefficients in this fixed basis; it does not
search for arbitrary functional forms such as sine or a denominator.

Each expanded feature is standardized using training mean and scale. If fitted
standardized coefficients are beta_j and intercept b, the original-coordinate
coefficient is `a_j = beta_j / scale_j`, and the original intercept is
`b - sum_j(a_j * mean_j)`. Those parameters define the exported formula.
Binary64 coefficients are retained in model.json and exported with 17 significant
decimal digits for round-trip safety. This avoids changing 1.0000000000000002
into exactly 1 through low-precision expression printing.

A lies inside this hypothesis class, so very small error there is expected.
B can be locally approximated by a polynomial but is not exactly representable
over all real inputs. C requires a rational structure and is likewise outside
this fixed polynomial class. This asymmetry is part of the experiment design.

## Neural baseline and early stopping

The standard MLP is `2 → 64 → 64 → 1`, with Tanh after each hidden layer and a
linear output. It has 4,417 trainable parameters. The demo uses smaller widths.
Inputs and targets are standardized using only training statistics. Training uses
full-batch Adam to minimize standardized MSE; validation MSE is converted back to
original target units for recording.

Every new validation minimum preserves a copy of the weights. Patience limits
epochs without sufficiently large improvement; completion restores the lowest
validation-MSE checkpoint rather than returning the last optimization step.
This is predictive model selection, not symbolic law discovery. A smooth neural
interpolant can fit the training domain and behave differently on an OOD shell;
Tanh representations do not guarantee polynomial growth outside that domain.

## Recovery is stronger than fit

Three questions must be kept separate:

1. Does the model predict held-out observations well?
2. Does its expression simplify algebraically to the oracle?
3. Does its original arithmetic evaluate finitely and correctly on independent probes?

For example, `x0*x1/x1` simplifies to x0 where x1 is nonzero, but raw floating-point
evaluation at x1=0 is NaN. A coefficient differing by 2e-16 can be numerically
indistinguishable at the selected tolerance and still fail exact algebraic equality.
Neither result should be hidden through eager cancellation or coefficient rounding.
Finite probes are useful witnesses of failure, not a proof of full-domain equality.

## Engineering boundaries

The benchmark keeps one process alive across searches to amortize Julia startup.
It initializes Julia before importing Torch and records startup separately. Each
web request instead runs in a fresh worker process: switching MLP → PySR cannot
reverse DLL initialization order in a persistent server, and finished requests
release the runtime. This costs extra startup time in the demo, deliberately
favoring stability. CPU CLI suites are the preferred workflow for actual studies.

Source basis: [PySR paper](https://arxiv.org/abs/2305.01582),
[official PySR Agent guide](https://github.com/astroautomata/PySR/blob/master/skills/pysr/SKILL.md),
and installed package APIs recorded in the run manifests.
