# jcvi-genomelens

`jcvi-genomelens/` 是独立的 GenomeLens analysis engine(分析引擎)。它在 `src/jcvi/` 下持有 vendored JCVI(随包 JCVI) 源码，并暴露稳定入口：

```powershell
python -m jcvi_genomelens.cli probe --json
python -m jcvi_genomelens.cli run --manifest jcvi_engine_manifest.json --outdir output
```

engine(引擎) 写出 `engine_run_summary.json`，不读取 shell configuration files(外壳配置文件)。

## 当前 workflow(工作流)

- `mcscan_pairwise`
- `graphics_synteny`
- `graphics_dotplot`
- `graphics_karyotype`
- `catalog_ortholog`
- `local_synteny`
- `graphics_karyotype_global`（由 shell(外壳) 在多物种汇总阶段调度）

这些 workflow 当前是 pairwise worker(两两比较工作单元)，manifest(清单) 内部仍使用 query/subject(查询/目标) 字段来适配 JCVI 的成对调用模型。多物种 `species[]` 入口、all-vs-all pairwise(全组合两两比较) 调度和顶层汇总由 `python/` shell(外壳) 负责。

engine 当前不负责跨全部物种的一张最终美化版总图，也不负责全局 layout/seqids 自动优化。

## probe(探测)

`capabilities` 表示真实可调度 workflow(工作流)。`bundled_jcvi_modules` 表示随包 JCVI 中存在、可作为后续接入基础的模块。
