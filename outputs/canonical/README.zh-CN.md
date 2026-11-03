# 标准点到球场景

[English](README.md)

原点处放置一个完全吸收球。 TX=(d,0,0)，目标 RX=(0,0,0)，所有球半径均为 R=1 μm。距离为 5、8、13、21、34 μm；D=79.4 μm²/s，Δt=4 μs，T=0.8 s。

## 数据构成

- `main/experiments.csv`：750 行，即 3 种方法 × 5 个距离 × 50 批独立实验，每批平均 32 次估计。
- `main/seeds.csv`：24,000 行，每次独立估计对应一个十六进制随机种子。
- `main/inner_estimates.csv.gz`：24,000 条批内估计记录，含概率、误差、计算量及耗时。
- `main/curves/<method>/dXXR.csv.gz`：15 个曲线文件，每个包含 1,001 个时间点上的参考值、总平均曲线和 50 条批次平均曲线。

- `cdf/`：CDF 图采用的单次实验，每组 32 次估计。
- `scans/uniform/`：阈值点数 2、4、6、8、12、16、24、32，三个距离，每组 50 批。
- `scans/adaptive/`：k=1、5、10、25、50、100、150、200，三个距离，每组 20 批。

标准场景采用解析参考：p(t) = (R/d) erfc((d−R)/sqrt(4Dt))。

`monc`、`mls_lb`、`ams_mod` 分别表示 MonC、均匀 A-MLS（32 个阈值点）和自适应 A-MLS（k=5）。主对照误差在完整的 200,001 点网格上计算，统计时直接读取已保存误差。时间及墙钟耗时均以秒计。概率、`relative_l2`、`relative_mse` 无量纲，且 `relative_mse = relative_l2²`。S 为平均墙钟耗时与平均相对 L2 误差之积。

在仓库根目录运行：

```bash
bash run_simulations.sh --study main --scenes canonical
```

以上描述为所附归档格式。新仿真采用[根目录说明](../../README.zh-CN.md#归档数据与重跑格式)中的批次目录格式；字段含义见[数据索引](../README.zh-CN.md#归档公共字段)。
