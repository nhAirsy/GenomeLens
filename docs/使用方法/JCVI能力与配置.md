# JCVI 能力与配置

## 当前可调度 workflow(工作流)

GenomeLens engine(引擎) 当前可调度的 workflow(工作流) 包括：

- `mcscan_pairwise`：执行 BLAST+ 与 JCVI MCscan(共线性扫描)，输出 anchors(锚点)、simple blocks(简化区块) 和 blocks(区块轨道)。
- `graphics_synteny`：默认主链路，输出 dotplot(点图) 与 synteny figure(共线性图)。
- `graphics_dotplot`：单独输出 dotplot(点图)。
- `graphics_karyotype`：单独输出 karyotype(核型共线性图)。
- `catalog_ortholog`：调用 `jcvi.compara.catalog.ortholog --full` 输出双向 ortholog(同源基因) 结果。
- `graphics_karyotype_global`：跨全部物种的全局核型总图。它不重算共线性，而是把已算好的各对 `.simple` 边渲染成一张多轨总图；由多物种运行自动调度，不需要用户手动通过 `--jcvi-workflow` 选择。

兼容别名 `dotplot` 和 `karyotype` 会被规范化为 `graphics_dotplot` 和 `graphics_karyotype`。

## 一站式流程：多物种局部共线性分析

HAIant/Tauri 侧如果只开放一个入口，建议把它命名为“GenomeLens 一站式 JCVI 多物种局部共线性分析”。这个入口不是单个 JCVI 命令，而是由 shell(外壳) 编排多个 pairwise worker(成对工作单元)，再由 engine(引擎) 调用真实 BLAST+ 与 JCVI 完成计算和绘图。

用户视角只需要提供：

- `input_dir`：一个输入文件夹，放入所有物种文件。
- `output_dir`：一个输出目录。
- `reference`：参考物种，默认第一个物种。
- `target_genes`：参考物种中的目标基因 ID。
- `up` / `down`：目标基因上下游窗口大小。

主流程内部包含以下阶段：

1. 输入目录发现

   GenomeLens 会扫描 `input_dir`，按同名 basename(基础文件名) 自动识别物种。当前支持两类输入：

   - `BED + CDS/PEP`：例如 `speciesA.bed` + `speciesA.cds`，也支持 `.pep`、`.pep.fa`、`.faa`。
   - `GFF/GTF + genome FASTA`：例如 `speciesA.gff3` + `speciesA.fa`。

   同一目录允许不同物种使用不同输入模式；同一个物种同时存在两类输入时，优先使用 `BED + CDS/PEP`。

   这一阶段的目标是把用户的一整个输入文件夹转换成稳定的 `species[]` 列表，而不是要求用户手工填写 query/subject。

2. 参数归一化与参考物种选择

   shell 会合并 CLI、配置文件和平台参数，确定参考物种、目标物种列表、线程数、比对后端、共线性参数和绘图参数。多物种局部共线性采用 `reference_vs_targets` 策略：固定一个参考物种，分别与每个目标物种运行局部共线性子任务。

3. 输入校验与工作区创建

   GenomeLens 会校验至少存在两个物种、参考物种索引合法、输入文件存在、输出目录可创建，并写出顶层 manifest(清单)。顶层 manifest 只描述编排关系；每个 pairwise 子任务会拥有自己的 engine manifest。

4. 注释预处理

   如果某个物种输入是 `GFF/GTF + FASTA`，平台会先转换为 JCVI 所需的 `BED + CDS`。当前预处理会按代表转录本策略抽取基因模型，尽量统一不同注释来源中的 ID、CDS 和基因坐标。若某个物种已经提供 `BED + CDS/PEP`，则跳过这一步，直接进入 JCVI 链路。

5. 工具链定位

   平台会定位 `jcvi-genomelens` engine、BLAST+ 的 `blastn` 与 `makeblastdb`，以及按需使用的 LAST / Diamond / ImageMagick 等工具。显式配置优先，其次才回退到环境变量、系统 `PATH`、打包资源或本地缓存。

6. 参考物种对目标物种的 pairwise 编排

   对于 `reference + N 个目标物种`，shell 会创建 N 个 pairwise 子任务：

   ```text
   reference vs target1
   reference vs target2
   reference vs target3
   ...
   ```

   每个子任务独立运行、独立产出 summary，并在顶层 `run_summary.json` 中汇总。单个目标物种失败时，顶层 summary 会记录失败原因，便于用户定位是哪一对物种出了问题。

7. 全基因组同源搜索与 MCscan

   每个 pairwise 子任务会先运行完整的全基因组同源搜索和 JCVI MCscan：

   - `makeblastdb`：为目标物种序列建库。
   - `blastn` 或其他配置的比对后端：搜索同源匹配。
   - `jcvi.compara.synteny.scan`：从比对结果生成 anchors(锚点)。
   - `jcvi.compara.synteny.simple`：生成 `.anchors.simple` 简化区块。
   - `jcvi.compara.synteny.mcscan`：生成 `.blocks` 区块轨道。
   - `jcvi.formats.bed.merge`：合并双物种 BED，供后续绘图使用。

   因此，局部共线性并不是只算目标基因附近；它先得到全局 pairwise 共线性基础结果，再从全局结果中截取目标区域。

8. 目标基因窗口截取

   `local_synteny` 会读取参考物种 BED 顺序，定位 `target_genes` 在参考物种中的基因坐标，并按 `up/down` 截取上下游窗口。随后从完整 `.blocks` 中筛出窗口内仍有目标物种同源关系的区块，形成局部 `.local.blocks`。

   如果启用 `split_targets`，多个目标基因会分别生成局部窗口；否则会合并为一个窗口。`label_targets` 会把目标基因列表传入绘图参数，用于图中标注。

9. 局部 layout 与 JCVI 绘图

   每个局部窗口会生成自己的：

   - `.local.blocks`
   - `.local.bed`
   - `.local.layout`
   - `.local.png` / `.local.pdf` 等图件

   绘图阶段调用真实 `jcvi.graphics.synteny`。图件样式参数包括 `figsize`、`dpi`、`glyphstyle`、`glyphcolor`、`shadestyle` 和输出格式。

10. 结果归档与汇总

    顶层结果会写入：

    - `report/run_summary.json`：平台侧摘要。
    - `inputs/analysis_request.json`：归一化请求快照。
    - `results/figures/`：用户可直接查看的归档图件。
    - `intermediate/pairwise/`：每一对 reference-vs-target 子任务的完整中间结果。
    - `intermediate/local/`：局部共线性图件、局部 blocks、局部 bed 和局部 layout。

    一站式入口可以默认把这些结果全部输出，用户后续按需取用；界面不必把每一种中间产物都做成开关。

需要注意：这个主流程的核心产物是“以参考物种目标基因为中心的多物种局部共线性结果”。它会顺带产出 anchors、simple、blocks 等全基因组 pairwise 中间结果，但当前仍不等同于“全局多物种最终美化版共线性图”。全局 layout/seqids 自动优化、跨物种区块合并排序和候选评分仍属于后续能力。

## 能力边界

shell(外壳) 入口已经支持 2 到 n 个物种的 `species[]` 输入，并会把 3 个以上物种自动拆成 all-vs-all pairwise(全组合两两比较) 子任务。所有 pairwise 子任务完成后，会把成功对的共线性边自动聚合成一张全局核型总图（`graphics_karyotype_global`），随 `run_summary.json` 的 `global_figures` 字段一并输出。

engine(引擎) 当前仍以 pairwise query/subject(成对查询/目标) manifest(清单) 为执行单元。这是 JCVI 真实调用链的 worker(工作单元)，不是废弃概念。多物种顶层编排由 shell 负责汇总。

尚未完成：

- 跨全部物种的一张最终美化版总图。
- 全局 layout/seqids 自动生成和优化。
- 多物种区块合并、排序和过滤。
- 机器学习评分与候选优先级排序。

## 配置文件

GenomeLens 把配置拆成两类：

- `genomelens.config.json`：工具本身设置，例如 workspace(工作区)、默认输出目录、日志级别。
- `jcvi.config.json`：JCVI engine、BLAST+、ImageMagick、workflow、绘图等与子工具相关的设置。

完整字段说明、默认值、配置示例和环境变量用法见 [`配置文件说明.md`](配置文件说明.md)。下文只保留与 JCVI 能力直接相关的要点。

`analyze mcscan` 与 `check` 支持 `--config` 和 `--jcvi-config`，也支持通过 `GENOMELENS_CONFIG` 与 `GENOMELENS_JCVI_CONFIG` 指向配置文件。配置优先级固定为：

1. CLI(命令行接口) 显式参数
2. 配置文件
3. 环境变量
4. 系统 `PATH`
5. 打包资源
6. `toolchains/` 本地缓存

JCVI 配置文件中的 `jcvi_engine_path`、`blastn_path`、`makeblastdb_path`、`magick_path`、`default_threads`、`default_min_block_size`、`default_formats` 和 `default_workflow` 会参与真实运行。

## 降级策略

`allow_simplified_fallback` 是保留协议字段。当前版本不实现简化算法；用户显式开启时会直接报错，避免把非真实 JCVI 结果冒充为正式分析结果。
