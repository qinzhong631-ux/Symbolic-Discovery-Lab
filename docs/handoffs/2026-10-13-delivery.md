# Symbolic Discovery Lab — 项目交付与移交

## 1. 当前任务与最终目标

交付独立、可运行、可复现的 Python 科研实验项目，用于符号回归、算法比较和
数学公式发现，并适合 AI 科研实习申请展示。仓库拟用名 symbolic-discovery-lab。

## 2. 当前状态与本轮结论

三阶段开发完成。本地 Windows CPU 已运行 PySR/Julia、Polynomial、PyTorch MLP、
四类实验、五组图表及 Gradio。最终含 Julia 测试 27 项通过；默认测试 26 项通过、
1 项明确跳过。完整比较 135 次拟合成功。已完成独立代码审查及真实网页连续模型切换。
尚未创建或推送 GitHub 远端仓库；本地源代码目录和交付 ZIP 保留完整结果。

## 3. 已完成工作

- 三个真实合成规律，独立随机流和 OOD 外壳；训练数量为嵌套前缀。
- PySR 验证集选式、固定阶多项式基线、MLP 验证早停与最佳权重恢复。
- 135 次三模型比较，90 次单独基线比较，6 次 CPU smoke，9 次整合 smoke。
- RMSE/MAE/R²、时间、复杂度、代数等价、定义域探针与数值恢复率。
- PNG/SVG 图表、英文 README、方法/实验/安装/验证/审查文档。
- Gradio 采用每请求独立工作进程；真实 HTTP 顺序 polynomial→mlp→pysr→all 成功。
- 已修复失败记录/绘图泄漏、提前完成标记、导出精度和 Julia/Torch 初始化顺序。

## 4. 创建或修改的文件

项目所有新增文件位于 `E:\AI\symbolic-discovery-lab`。完整结构见
`docs/DIRECTORY_TREE.md`，逐文件哈希见 `results/artifact_inventory.csv`。
MiniGPT 仓库仅作呈现参考，未修改。`.venv/`、`.julia/`、`runs/` 为本地环境/缓存，
不进入交付 ZIP。交付归档位于 `E:\AI\symbolic-discovery-lab.zip`。

## 5. 命令、测试与验证结果

命令都在项目根目录使用 `.venv\Scripts\python.exe` 执行；详见 docs/VALIDATION.md。

- `python -m pytest -q --basetemp=runs/pytest-release`：26 passed，1 skipped。
- 设置 RUN_PYSR_TESTS=1 后 `python -m pytest -q --basetemp=runs/pytest-release-julia`：
  27 passed，1 条有意设置单线程导致的提示；67.27 秒。
- `python -m symbolic_discovery run --config configs/quick.json --output results/quick`：
  135 fits，0 failed。
- `python -m symbolic_discovery run --config configs/smoke.json --models polynomial mlp pysr
  --output results/smoke_all`：9 fits，0 failed。
- `python scripts/verify_results.py --results results/quick`：45 组数据、135 模型、
  540 指标记录、5 图对核验成功。
- `python scripts/verify_demo.py --include-symbolic`：连续真实 HTTP 请求成功。
- Ruff lint/format、pip check、wheel 构建通过。

## 6. 阻碍与尚存问题

无阻碍本地运行的已知问题。Julia 首次自动下载安装及编译实际耗时约 23.5 分钟。
reference 大预算配置、WSL2、Python 3.11、远端 CI 和完全隔离重装尚未验证。
实际开发复用已有 NumPy/PyTorch 环境，依赖版本均已记录。

## 7. 已确认约束、决定与证据边界

真实公式不能进入搜索或选式。PySR 内部算法不属于本项目原创。三模型同一划分。
三种子 SD 不是置信区间；预算未做严格算力匹配；不能推断普遍算法排名。
A/B 的 PySR 恢复好，C 在零噪声 n=512 下只 1/3 种子恢复，MLP 平均外推误差更低。
数值近似不等于严格符号等价；有限探针不证明全部定义域相等。

## 8. 坑点与不得重复的操作

- 禁止伪造结果或把真实公式作 guesses/template 输入。
- 禁止覆盖已有非空结果目录；新研究使用 runs/ 下的新目录。
- 不要用字符串匹配、系数四舍五入或 eager 化简制造恢复成功。
- 多项式表达式必须保留 17 位有效数字和原始系数。
- CLI 初始化 Julia 后再导入 Torch；持续 Web 服务使用独立 worker。
- 初始恢复 CSV 和精度修订前元数据是审计记录；当前结果 CSV 才是最终评价。
- 失败模型不能进入均值或预测图；图表/报告失败必须保留实际状态。
- 不要反复重装 Julia 或删除仍被活动进程使用的锁。

## 9. 下一项最小任务

当前开发任务已完成。后续可先授权发布 GitHub；科研扩展优先执行
configs/reference.json 或预先声明搜索语法/算力匹配消融，不改已有结果。

## 10. 下一会话启动指令

先读 README.md、docs/EXPERIMENTS.md、docs/VALIDATION.md 与本文件。
运行 `python app.py` 启动 Demo，或使用 `python -m symbolic_discovery run --config
configs/quick.json --output runs/new-study`。若扩展算法先阅读数据泄漏及恢复判据测试。
论文/个人主页仅引用真实结果，明确这是一项受控合成数据的探索性研究。
