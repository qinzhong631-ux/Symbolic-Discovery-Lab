# Figure evidence contract

Backend: Python / Matplotlib. Export: PNG at 220 dpi and SVG with editable text,
white background, consistent method colors, 11 x 3.6 inch three-dataset panels.
Every figure reads saved results. No illustrative data are presented as measurements.

1. Truth vs prediction: assess held-out calibration, per-model test scatter and
   identity line. Seed, noise and sample count are named in the title.
2. Noise robustness: show how observed test RMSE changes with absolute Gaussian
   noise. Points are seed means; bars are sample SD, omitted when n=1.
3. Data efficiency: paired nested train prefixes, fixed held-out sets; RMSE vs n.
4. ID vs OOD: paired means and SD from the same fitted model at the reference
   sample count and zero noise. OOD lies outside the full training square.
5. Accuracy-complexity: validation RMSE against PySR tree complexity. Show all
   candidates and the empirical nondominated subset; test data do not select models.

Review risks: log axes cannot represent exact zero, so displayed values use a
1e-12 floor only for plotting. Raw values are unchanged. Missing/failed models
must be absent with status disclosed, never plotted at zero. Small budgets do
not support universal algorithm rankings. PySR complexity, SymPy node count
and MLP parameter count are different quantities and must never be conflated.
