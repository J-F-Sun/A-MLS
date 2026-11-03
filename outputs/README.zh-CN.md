# 论文数据集

[English](README.md)

所附归档包含五个场景的数据、标准场景的两组参数扫描，以及单次实验 CDF 数据，共同提供重建论文数值比较所需的输入。

| 数据位置 | 论文用途 | 说明 |
|---|---|---|
| `canonical/main/` | 标准场景三方法对照 | [标准场景](canonical/README.zh-CN.md) |
| `canonical/cdf/` | 单次实验 CDF 图 | [CDF 数据集](canonical/cdf/README.zh-CN.md) |
| `canonical/scans/uniform/` | 均匀阈值点数扫描 | [均匀扫描](canonical/scans/uniform/README.zh-CN.md) |
| `canonical/scans/adaptive/` | 自适应淘汰参数扫描 | [自适应扫描](canonical/scans/adaptive/README.zh-CN.md) |
| `ob_complete/main/` | Ext1：完全遮挡反射球 | [Ext1](ob_complete/README.zh-CN.md) |
| `ob_half/main/` | Ext2：部分遮挡反射球 | [Ext2](ob_half/README.zh-CN.md) |
| `rx2_competitive/main/` | Ext3：无遮挡竞争吸收球 | [Ext3](rx2_competitive/README.zh-CN.md) |
| `rx2_half/main/` | Ext4：部分遮挡竞争吸收球 | [Ext4](rx2_half/README.zh-CN.md) |

四个扩展场景分别在 `reference/` 下提供五个 FEM 参考 CSV，列名为 `t,q`，各含 1,001 个时间样本。仿真程序将其线性插值到误差计算网格；标准场景的参考值直接由解析公式计算。仓库不包含 FEM 生成工程。

## 归档公共字段

- `experiments.csv`：每批一行。主对照与 CDF 含 `scene`、`distance_R`、`algorithm`、`experiment`、`inner_repeats`、`relative_l2`、`relative_mse`、`wall_seconds`、终点概率及计算量。扫描记录含 `parameter`，保留的批次字段较少。
- `seeds.csv`：每次估计一行，由方法、距离、实验批次和批内序号标识；扫描额外包含 `parameter`。`seed_hex` 为十六进制随机种子。将结果写入其他输出目录时，仍需保留这些输入文件。
- `inner_estimates.csv.gz`：五组主对照与 CDF 的逐次估计记录，含 `P_hat`、`relative_mse`、计算量、完成状态及 `elapsed_seconds`。扫描归档不提供此文件。
- `curves/<method>/dXXR.csv.gz`：主对照列为 `t,q_ref,q_mean,outer_curve_sd,q_experiment_1,...,q_experiment_50`；CDF 列为 `t,q_ref,q_mean,q_std,ci95_lower,ci95_upper,q_repeat_1,...,q_repeat_32`。两者均使用 1,001 个展示时间点。主对照的 `outer_curve_sd` 为批次曲线间的样本标准差，不是置信区间。

方法标识 `monc`、`mls_lb`、`ams_mod` 分别代表 MonC、均匀 A-MLS、自适应 A-MLS。`distance_R` 为发射点到目标球心的距离除以 R；`experiment` 标识实验批次，`repeat` 标识批内估计序号。本数据中 R=1 μm。`relative_mse` 为相对 L2 误差的平方，无量纲。时间单位为秒。批次 `wall_seconds` 为并行批次的墙钟耗时，不等于各次估计 `elapsed_seconds` 之和。

## 论文派生结果

- `analysis/outer_experiments.csv`：五场景主对照共 3,750 条批次记录。
- `analysis/metrics.csv`：75 个方法—场景—距离组合的指标，采用平均相对 L2 误差、平均墙钟时间、S 及相对增益 G。
- `analysis/extended_performance.tex`：包含 20 个场景—距离组合的扩展场景表格，采用独立 tabular 布局；论文另行设置表格样式。
- `figures/`：论文采用的四幅数值结果 PDF 图。

`rerun/` 和 `reproduced/` 分别为新仿真和重建图表的默认输出位置。重跑保存独立批次目录并汇总 `experiments.csv`，不重新生成归档的打包格式。具体格式与运行命令见[根目录说明](../README.zh-CN.md#归档数据与重跑格式)。
