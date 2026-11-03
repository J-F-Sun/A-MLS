# 吸收感知多级分裂（A-MLS）

[English](README.md)

本仓库为论文 *Absorption-Aware Multilevel Splitting for Efficient Rare-Event Simulation in Molecular Communication* 提供仿真程序与数值数据。该论文已投稿至 IEEE ICC 2027。

A-MLS 的全称为 **Absorption-Aware Multilevel Splitting（吸收感知多级分裂）**，均匀距离阈值与自适应阈值是它的两种分层策略。程序在标准场景及四个扩展场景中比较直接蒙特卡洛（MonC）、均匀 A-MLS 和自适应 A-MLS。

## 目录结构

```text
config/                 物理参数与五个场景的定义
src/                    Julia 仿真内核与实验运行程序
tools/                  统计分析与四幅论文图的绘图程序
outputs/
  canonical/            标准场景：主对照、单次实验 CDF 与参数扫描
  ob_complete/          Ext1：完全遮挡目标接收球的反射球
  ob_half/              Ext2：部分遮挡目标接收球的反射球
  rx2_competitive/      Ext3：不遮挡目标接收球的竞争吸收球
  rx2_half/             Ext4：部分遮挡目标接收球的竞争吸收球
  analysis/             论文指标汇总与扩展场景表格
  figures/              论文采用的四幅数值结果 PDF 图
run_simulations.sh      仿真运行入口
reproduce_figures.sh    统计与图表重建入口
```

每个场景提供中英文数据说明，入口见 [outputs/README.zh-CN.md](outputs/README.zh-CN.md)。物理参数与几何输入位于 `config/`；已记录的随机种子、仿真结果和 FEM 参考曲线位于 `outputs/`。

## 环境安装

- **Julia 1.11.8** 为所附数据记录的仿真版本，建议用它重放随机种子；运行程序要求 Julia 1.11 及以上版本。仿真仅使用 `Project.toml` 列出的 Julia 标准库依赖。
- Linux、macOS 的 Bash，或 Windows 的 WSL。
- 统计和绘图使用 Python 3.11 及以上版本。`requirements.txt` 固定了 [NumPy 2.4.6](https://pypi.org/project/numpy/2.4.6/) 和 [Matplotlib 3.11.0](https://pypi.org/project/matplotlib/3.11.0/)；单独运行统计程序只需 Python 标准库。
- 需要提供 `latex`、`pdflatex`、`dvipng`、`amsmath` 和 Computer Modern 字体的 TeX 安装，并包含 Matplotlib [LaTeX 文字渲染](https://matplotlib.org/stable/users/explain/text/usetex.html)所需的宏包。文字尺寸测量采用 Agg 后端与 LaTeX，矢量 PDF 导出采用 PGF 后端与 `pdflatex`。

在仓库根目录执行：

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

FEM 参考曲线已随数据提供，可直接使用。运行粒子仿真无需安装 PDE 求解器或 Python。仓库不包含 FEM 网格、求解器工程或参考曲线生成脚本；所覆盖的流程为粒子仿真及其相对所附参考曲线的分析，未包含 FEM 解的重新生成。

## 运行仿真

```bash
# 列出完整论文实验计划，不生成实验结果。
bash run_simulations.sh --dry-run

# 运行全部论文实验，包括 CDF 和参数扫描。
THREADS=32 JOBS=2 bash run_simulations.sh

# 只运行 50 批主对照实验。
THREADS=32 JOBS=2 bash run_simulations.sh --study main

# 运行标准场景在一个距离下的三方法对照。
THREADS=32 JOBS=2 bash run_simulations.sh \
  --study main --scenes canonical --distances 34

# 分别运行两组参数扫描。
bash run_simulations.sh --study uniform-scan
bash run_simulations.sh --study adaptive-scan

# 运行所附 CDF 单次实验对应的种子配置。
bash run_simulations.sh --study cdf
```

可用 `JULIA_BIN=/path/to/julia` 指定 Julia。`THREADS` 表示每个工作进程的线程数；`JOBS` 表示 A-MLS 工作进程的最大并发数，MonC 使用一个工作进程。每批平均 32 次独立种子对应的估计，独立估计次数与线程数无关。默认每进程 32 线程、两个 A-MLS 并发进程。

新结果默认写入 `outputs/rerun/`，可通过 `--output-root PATH` 指定其他位置。重复执行完全相同的命令可继续运行并跳过已完成的批次。每批记录设置、随机种子和数值输出；修改代码、配置、Julia 版本、线程数或其他运行设置后，应使用新的输出目录。

即使指定其他输出根目录，运行程序仍从仓库自带的 `outputs/` 读取随机种子和扩展场景参考曲线，请保留这些输入文件。该入口用于重放所附论文配置，不生成新种子集或任意几何场景的参考曲线。

仅有相同种子不保证跨 Julia 版本或实现修改后的结果逐位相同。

还可通过 `--methods monc,mls_lb,ams_mod`、`--scenes`、`--distances` 选择任务，用 `--parameters` 选择扫描参数。`--experiments` 和 `--repeats` 选取已记录的前若干批及批内估计；`--steps` 在保持 0.8 s 时域的条件下修改时间网格。默认值对应论文实验协议。完整计划包含 **138 个配置、5,445 批实验、174,240 次估计运行**。

## 归档数据与重跑格式

所附归档使用 `experiments.csv`、`seeds.csv`、`inner_estimates.csv.gz` 和压缩后的展示曲线。参数扫描保留逐批汇总与随机种子。文件格式见[数据索引](outputs/README.zh-CN.md)及各场景 README。

新仿真的每批结果保存在 `<output-root>/<scene>/<study>/runs/<method>/dXXR/p<parameter>/eXX/` 下，其中 `<study>` 为 `main`、`cdf`、`scans/uniform` 或 `scans/adaptive`。每个完整批次包含：

- `experiment.csv`：一条批次汇总，含完整网格误差和墙钟耗时。
- `curves.csv`：展示网格上的参考值、均值、标准差、置信区间及各次估计曲线。
- `repeats.csv`：逐次估计的种子、误差、计算量及耗时。
- `taus.csv`：目标吸收时刻，每次估计的每个已记录命中对应一行。
- `run.toml`：续跑校验所用的源码与设置指纹、输出文件校验和。

所选任务完成后，程序汇总生成 `<scene>/<study>/experiments.csv`，不会重新打包归档中的合并 `inner_estimates.csv.gz` 或主对照压缩曲线。统计与绘图程序支持重跑格式，CDF 图直接读取对应批次的 `curves.csv`。进程被强制终止后可能遗留的 `.batch-*` 临时目录不会进入汇总。

## 重建统计结果和图表

```bash
# 从随仓库提供的论文数据重新计算指标和表格。
python tools/analyze.py

# 从随仓库提供的数据重建四幅图及其统计结果。
PYTHON_BIN=python bash reproduce_figures.sh

# 完整重跑仿真后，从新结果重建图表。
PYTHON_BIN=python bash reproduce_figures.sh outputs/rerun outputs/rerun/figures
```

图表默认写入 `outputs/reproduced/`。绘图脚本的第一个可选参数为输入数据根目录，第二个为输出目录。重建全部四幅图需要五个主场景在五个距离、三种方法下各 50 批、每批 32 次估计的结果，两组完整参数扫描，以及标准场景在全部五个距离下的 CDF 实验。部分主对照结果可单独汇总：

```bash
python tools/analyze.py --data-root outputs/rerun
```

`analyze.py` 只汇总 `main/experiments.csv`，不汇总仅含参数扫描或 CDF 的重跑结果。例如，完整扫描重跑后可执行 `python tools/plot_parameters.py --data-root outputs/rerun`；完整 CDF 重跑后可执行 `python tools/plot_cdf.py --data-root outputs/rerun`。这些独立绘图命令默认写入 `outputs/reproduced/`，可用 `--output PATH.pdf` 更改位置。

| 论文内容 | 数据位置 | 图文件 |
|---|---|---|
| 参数敏感性 | `outputs/canonical/scans/` | `parameter_search_S.pdf` |
| 单次实验 CDF | `outputs/canonical/cdf/` | `01_canonical_CDF.pdf` |
| 标准场景性能 | `outputs/canonical/main/` | `02_canonical_metrics_2x2.pdf` |
| 扩展场景性能表与增益 | 四个扩展场景的 `main/` | `03_extended_gain_2x2.pdf` |

绘图脚本保留了论文使用的坐标轴范围和标注位置。重跑所得耗时或估计值可能超出这些范围并触发绘图检查，此时需要调整坐标轴或标注后再绘图。

## 实验与统计定义

所有场景使用 `R=1 μm`、`D=79.4 μm²/s`、`Δt=4 μs`、200,000 个时间步，观测时域为 `T=0.8 s`。距离为 5、8、13、21、34 μm。MonC 每次估计使用 1,000 个分子，A-MLS 使用 250 个初始副本。主对照每种方法、每个距离运行 **50 批 × 每批 32 次估计**；均匀 A-MLS 使用 32 个阈值点（`L=31`），自适应 A-MLS 使用 `k=5`。

均匀阈值参数扫描每个配置使用 **50 × 32** 次估计，自适应参数扫描使用 **20 × 32** 次估计，均覆盖标准场景的 5、13、34 μm。CDF 图在每个距离、每种方法下展示一个 **32 次估计构成的单次实验**，对应种子及点态置信区间均已提供，绘图读取 `canonical/cdf/`。

每批相对 L2 误差均由该批平均估计曲线在完整的 **200,001 点**时间网格上计算；扩展场景的 FEM 样本经线性插值映射到该网格。论文使用 50 批主对照误差的算术平均，主指标为 `S = mean(wall_seconds) × mean(relative_l2)`，相对增益为 `G = 100 × (S_MonC / S_A-MLS − 1)`。参数扫描阴影区间，以及标准场景误差、墙钟时间和 S 的误差棒，使用 95% 百分位 bootstrap 区间；增益面板展示点估计。CDF 图中 MonC 使用合并分子样本的 Wilson 区间，A-MLS 使用 32 次独立估计的 Student-t 区间。

保存的展示曲线包含 1,001 个时间点。表格直接采用已保存的完整网格误差统计；绘图网格用于展示曲线。十六进制随机种子用于在完整时间网格上重新计算。CSV 中时间单位均为秒，概率与相对误差均无量纲。

所附墙钟时间使用 Julia 1.11.8，在 Intel Xeon Gold 6430 上以每个工作进程 32 线程测得；MonC 单进程，A-MLS 两进程并发。计时范围为预热后的并行估计批次。新运行的耗时随硬件、Julia 版本、并发数和调度方式变化；重建论文中涉及耗时的表格和图时，使用仓库内所附结果。

## 数值实现

三种方法共用高斯扩散步进。吸收在时间步端点判定；反射球通过直线步进段与球面的交点，将剩余位移按镜面规则反射。这是连续扩散模型的有限步长近似。自适应实现会淘汰所选分数处的全部并列副本、按实际存活比例更新权重，并重放父轨迹随机流以恢复分支检查点，再生成独立后续轨迹。已被目标吸收的副本保留原始命中时刻。

Julia 物理配置与内核采用 SI 单位（米、秒、m²/s）。场景距离、球半径及横向偏移以 R 的倍数给出。历史配置键 `obstacle_offset_x_R` 与 `competitor_offset_x_R` 表示发射点到目标球心距离 d 的比例，`0.5` 对应附加球位于 x=d/2。README 中的距离及图中坐标采用微米。
