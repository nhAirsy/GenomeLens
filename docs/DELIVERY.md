# 交付说明

## 交付包

构建脚本会把 release zip(发布压缩包) 写入 `app/`：

- `GenomeLens-1.0.0-windows-core.zip`
- `GenomeLens-1.0.0-windows-with-toolchains.zip`
- `GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip`
- `GenomeLens-HAIant-plugin-1.0.0.zip`

这些 zip 是构建产物，不进入 Git 跟踪。

## 当前交付能力

当前交付包面向真实 JCVI 共线性分析：

- 从两个或多个物种的 GFF+FASTA 或 BED+CDS 输入开始，并可按物种混用两类输入。
- 自动调用 BLAST+ 与 jcvi-genomelens engine(引擎)。
- 2 个物种时运行双物种真实流程；3 个及以上物种时自动拆分为 all-vs-all pairwise(全组合两两比较) 并汇总结果。
- 输出 anchors(锚点)、blocks(区块)、dotplot(点图)、synteny figure(共线性图)、可选 ortholog(同源基因) 结果，以及多物种全局核型总图(global karyotype)。
- HAIant plugin(智然体插件) 可通过 `params.json` 驱动相同流程。

## 完整目标差距

完整目标中的“跨全部物种的一张最终美化版总图、全局 layout/seqids 自动优化、多物种区块合并/排序/过滤、机器学习评分”尚未完成，因此当前 full/offline package(完整/离线包) 不能宣称支持最终美化版共线性图。

## 构建命令

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -Command "Push-Location integrations\haiant_plugin; python -m PyInstaller pyinstaller\genomelens_haiant.spec --clean --noconfirm; Pop-Location; .\scripts\build_haiant_plugin.ps1"
```

构建和 smoke 应使用 `genomelens` conda 环境，解释器版本为 Python 3.12。
