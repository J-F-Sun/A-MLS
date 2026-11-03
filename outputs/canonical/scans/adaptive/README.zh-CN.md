# 自适应 A-MLS 参数扫描

[English](README.md)

标准场景距离为 5、13、34 μm，参数取值为 1, 5, 10, 25, 50, 100, 150, 200。`parameter` 为自适应 A-MLS 的 k-worst 淘汰参数，不是预设层数。所选分数处的并列副本会一并淘汰，因此实际淘汰数可能大于 k。每个配置使用 20 批 × 每批 32 次独立估计，初始副本数为 250。

`experiments.csv` 包含 480 条逐批相对 L2 误差、误差平方和墙钟耗时记录；`seeds.csv` 包含 15360 个独立估计种子，通过参数和距离列标识配置。完整网格误差无量纲，墙钟时间单位为秒。绘图指标 S 为平均墙钟时间与平均相对 L2 误差之积，最后一列为三个距离下 S 的算术平均。

95% bootstrap 区间使用 20,000 次抽样，各自适应扫描配置独立重采样。在仓库根目录执行 `bash run_simulations.sh --study adaptive-scan`。

本扫描归档仅保留逐批汇总与随机种子。重跑还会按批次保存曲线、逐次估计记录和命中时刻，格式见[根目录说明](../../../../README.zh-CN.md#归档数据与重跑格式)。两组扫描全部完成后，可用 `python tools/plot_parameters.py --data-root outputs/rerun` 合并绘图；`tools/analyze.py` 只处理主对照。
