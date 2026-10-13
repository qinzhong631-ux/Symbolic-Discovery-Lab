# Acknowledgements and upstream software

This repository implements experiment orchestration, data generation, model
adapters, evaluation, plotting and a demo. Symbolic search is provided by
upstream PySR / SymbolicRegression.jl; no internal search code is copied here.

- [PySR](https://github.com/astroautomata/PySR) and
  [SymbolicRegression.jl](https://github.com/MilesCranmer/SymbolicRegression.jl):
  symbolic regression implementation. Follow the upstream repository's citation
  instructions; see Miles Cranmer, *Interpretable Machine Learning for Science
  with PySR and SymbolicRegression.jl* (2023), [arXiv:2305.01582](https://arxiv.org/abs/2305.01582).
- [scikit-learn](https://scikit-learn.org/stable/about.html): polynomial features,
  scaling, least squares and evaluation. Pedregosa et al., *Scikit-learn: Machine
  Learning in Python*, JMLR 12, 2825–2830 (2011).
- [PyTorch](https://pytorch.org/): neural baseline and automatic differentiation.
  Paszke et al., *PyTorch: An Imperative Style, High-Performance Deep Learning
  Library*, NeurIPS (2019).
- [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/),
  [SciPy](https://scipy.org/), [SymPy](https://www.sympy.org/),
  [Matplotlib](https://matplotlib.org/), [Gradio](https://www.gradio.app/) and
  [pytest](https://docs.pytest.org/) supply numerical, symbolic, visualization,
  interaction and testing infrastructure.
- [MiniGPT Lab](https://github.com/qinzhong631-ux/minigpt-lab) inspired the
  presentation structure: method explanation, quick start, evidence, reproducibility
  and limitations. It is an independent project; its repository was not modified.

- [GraphMeta](https://github.com/NoWall-572/GraphMeta_for_MAS) inspired the public
  README layout: centered title, badges, capability table, navigation and visual
  section markers. Its scientific content, code and images are not copied.

Dependencies retain their upstream licenses. The MIT license in this repository
covers this project's original code/documentation and synthetic output artifacts,
not a relicensing of third-party packages. Packages are installed separately.
