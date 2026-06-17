# GenomeLens HAIant plugin(智然体插件)

这一 integration layer(集成层) 会把 HAIant `params.json` 转换为 GenomeLens runtime command(运行时命令)。它不实现分析算法，也不直接调用 JCVI。

## 当前范围

当前插件参数面向 2 到 n 个物种的 GenomeLens 分析：

- BED+CDS 输入。
- GFF+FASTA 输入。
- `species[]` 物种列表（至少两个物种）。
- `graphics_synteny`、`graphics_dotplot`、`graphics_karyotype`、`mcscan_pairwise` 和 `catalog_ortholog` workflow(工作流)。
- `allow_simplified_fallback` 字段保留，但正式流程不启用简化算法。

完整目标中的插件表单美化、参数自动推荐、全局总图调参与机器学习评分尚未接入。

## 入口

```powershell
GenomeLens.exe
GenomeLens.exe params.json
```

打包插件期望运行时位于：

```text
runtime/GenomeLens/GenomeLens-runtime.exe
```
