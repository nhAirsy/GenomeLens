# App release artifacts(发布制品)

构建脚本会把 release zip(发布压缩包) 写入本目录。这些文件是生成物，不进入 Git 跟踪。

当前交付包面向真实 JCVI 共线性分析：

- `GenomeLens-1.0.0-windows-core.zip`
- `GenomeLens-1.0.0-windows-with-toolchains.zip`
- `GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip`
- `GenomeLens-HAIant-plugin-1.0.0.zip`

能力范围：

- 从 2 到 n 个物种的 GFF+FASTA 或 BED+CDS 输入开始，并可按物种混用两类输入。
- 自动调用 BLAST+ 与 jcvi-genomelens engine(引擎)。
- 2 个物种时运行双物种真实流程；3 个及以上物种时自动拆分为 all-vs-all pairwise(全组合两两比较) 并汇总结果。
- 支持以参考物种目标基因为中心的 `local_synteny` 局部共线性分析。
- 输出 anchors(锚点)、blocks(区块)、dotplot(点图)、synteny figure(共线性图)、karyotype(核型图)、可选 ortholog(同源基因) 结果，以及多物种全局核型总图(global karyotype)。
- 公开 CLI 入口仅为 `analyze mcscan`；HAIant plugin(智然体插件) 通过临时输入目录转换后调用 `analyze mcscan` 驱动相同流程。

完整目标中的“跨全部物种的一张最终美化版总图、全局 layout/seqids 自动优化、多物种区块合并/排序/过滤、机器学习评分”尚未完成，因此当前 full/offline package(完整/离线包) 不能宣称支持最终美化版共线性图。

构建命令：

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
```

发布时应使用 release attachments(发布附件)、Git LFS 或独立 artifact store(制品库) 承载大型 zip。
