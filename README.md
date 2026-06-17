# GenomeLens

GenomeLens 是面向 Windows 的比较基因组学与共线性分析命令行产品。项目的完整目标是：从 2 到任意多个物种的 GFF/GTF(注释文件) 与 FASTA(基因组序列) 出发，经过统一参数预设、输入预处理、JCVI 分析与 JCVI 绘图，最终生成可发表、可美化的多物种共线性图。

## 当前集成状态

当前版本已经实现双物种真实 JCVI 端到端链路，以及以目标基因为中心的局部共线性分析：

- `GFF+FASTA` 或 `BED+CDS/PEP` 输入（支持 `.pep`、`.faa`）。
- GFF/GTF 与 FASTA 预处理为 JCVI 所需的 BED/CDS，按最长 CDS、无内部终止密码子、最多 CDS 片段、mRNA ID 选择代表转录本。
- BLAST+ / LAST / Diamond 比对后端可选。
- BLAST+ 与 JCVI MCscan(共线性扫描)。
- `jcvi.graphics.dotplot` 点图。
- `jcvi.graphics.synteny` 共线性图，支持 `--glyphstyle`、`--glyphcolor`、`--shadestyle`、`--figsize`、`--dpi` 样式参数。
- `jcvi.graphics.karyotype` 独立核型共线性图 workflow(工作流)。
- `jcvi.compara.catalog.ortholog --full` 双向 ortholog(同源基因) 结果。
- 以参考物种目标基因为中心的 `local_synteny` 工作流，支持 `--target-genes`、`--up`/`--down`、`--split-targets`、`--label-targets`。
- 多物种 all-vs-all pairwise 编排，并把各对共线性边聚合成一张全局核型总图(`graphics_karyotype_global`)。
- shell(外壳)、engine(引擎)、HAIant plugin(智然体插件) 分层交付。

全局总图当前使用默认 layout/seqids 与默认配色。尚未完成的是其美化层：全局 layout/seqids 自动优化、多物种区块合并/排序/过滤，以及机器学习评分与候选优先级排序。

## 模块边界

目录布局朝《最终架构目标》演进：`platform/`（平台核心雏形）、`engines/`（引擎层）、`integrations/`（平台集成层），并预留 `gui/`、`agents/` 路线图位置。

- `platform/`：面向用户的 GenomeLens 平台核心雏形（包名仍为 `genomelens`），负责 CLI(命令行接口)、输入校验、预处理、工具链定位、manifest(清单) 写入、engine 调用和结果归档。
- `engines/jcvi/`：当前唯一正式 engine(引擎)，独立 JCVI-backed，持有 vendored JCVI(随包 JCVI) 源码，只暴露 `probe` 和 `run` 两个稳定入口。后续新增引擎与它平级置于 `engines/` 下。
- `integrations/haiant_plugin/`：HAIant adapter(智然体适配器)，读取 `params.json` 并转换为 GenomeLens CLI 参数。
- `gui/`、`agents/`：路线图预留位置，当前仅含说明，不含实现。

平台核心不直接 `import(导入)` 上游 `jcvi`。跨层通信只通过 `jcvi_engine_manifest.json` 与 `engine_run_summary.json`。

## 开发

开发环境统一使用 `genomelens` conda 环境，解释器版本为 Python 3.12。

```powershell
conda activate genomelens
python -m genomelens.cli.main check
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

最终交付包写入 `app/`。运行时工具链缓存放在 `toolchains/`，下载缓存放在 `references/downloads/toolchains/`；这些生成物和离线 payload(载荷) 不进入 Git 跟踪。

## 许可

GenomeLens 自有代码以 MIT License 授权，全文见 `LICENSE`。

仓库还内置了 vendored JCVI(随包上游源码，`engines/jcvi/src/jcvi/`)，它保留自己的 BSD 风格许可（见 `engines/jcvi/licenses/JCVI-LICENSE.txt`），**不受 MIT 覆盖**。运行时工具链（BLAST+、ImageMagick）与 Python 运行期依赖各自适用其上游许可。第三方组件与许可边界详见 `NOTICE.md`。
