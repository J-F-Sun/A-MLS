# 单次实验 CDF 数据集

[English](README.md)

本数据集对应论文标准场景 CDF 图实际展示的单次实验：3 种方法 × 5 个距离 × 32 次估计，共 480 条估计记录。

- `experiments.csv`：15 条批次记录，实验编号均为 1。
- `seeds.csv`：480 个独立估计随机种子。
- `inner_estimates.csv.gz`：480 条独立估计记录。
- `curves/<method>/dXXR.csv.gz`：15 个曲线文件，各含 1,001 个时间点、解析参考、批次平均值、样本标准差、95% 点态置信区间和 32 条独立估计曲线。

MonC 置信区间为 32,000 个独立分子对应的 Wilson 区间，A-MLS 为 32 次独立估计对应的 Student-t 区间。A-MLS 区间为空时表示退化区间未定义。MonC 使用主对照的第 1 批，A-MLS 曲线使用随本数据集提供的 CDF 专用种子。主性能统计位于 `../main/`。

在仓库根目录执行 `bash run_simulations.sh --study cdf`。时间单位为秒，概率及相对误差无量纲。

以上文件为所附归档格式。CDF 重跑保存 `runs/<method>/dXXR/p0/e01/curves.csv`，CDF 绘图同样支持该格式，详见[根目录说明](../../../README.zh-CN.md#归档数据与重跑格式)。五个距离、三种方法全部完成后，在仓库根目录执行 `python tools/plot_cdf.py --data-root outputs/rerun`；`tools/analyze.py` 只处理主对照。
