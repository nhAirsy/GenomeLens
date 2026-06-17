# GenomeLens CLI(命令行接口)

## 当前命令

```powershell
GenomeLens.exe --help
GenomeLens.exe --version
GenomeLens.exe check [-j] [-c <path>] [--jcvi-config <path>] [--install-missing]
GenomeLens.exe config init --workspace <path> [--config-path <path>] [--jcvi-config-path <path>] [--force]
GenomeLens.exe analyze mcscan <input-dir> <outdir> [jcvi-config.json] [options] [-j]
GenomeLens.exe help [command...]
GenomeLens.exe workbench
GenomeLens.exe clean [--cache] [--all] [--yes]
```

## 共线性分析入口

公开分析入口当前仅保留 `analyze mcscan`。它只要求指定输入目录和输出目录；需要显式物种清单或更复杂配置时，通过 `--jcvi-config` 或输入目录下的 `jcvi.config.json` 覆盖默认参数。

自动模式要求输入目录中每个物种文件同名成对：

- `speciesA.bed` + `speciesA.cds`（或 `.cds.fa`、`.pep`、`.faa`）
- 或 `speciesA.gff3` + `speciesA.fa`

```powershell
GenomeLens.exe analyze mcscan input output --force
```

传入 2 个物种时自动运行双物种流程，传 3 个以上物种时自动运行全组合 pairwise(两两比较) 编排。

- `-c, --config <path>`：读取 GenomeLens 主配置文件。
- `--jcvi-config <path>`：读取 JCVI 子配置文件；优先级高于位置参数 `jcvi-config.json`。
- `jcvi-config.json`（位置参数，可选）：放在 `output_dir` 后的 JCVI 配置文件路径，与 `--jcvi-config` 二选一即可。
- `--reference <name|index>`：参考物种名称或 1-based 索引；默认第一个物种。多物种且带 `--target-genes` 时，只运行参考物种与每个目标物种的局部共线性。
- `--threads <n>`：覆盖默认线程数。
- `--min-block-size <n>`：覆盖最小 block(区块) 大小。
- `--formats png,pdf`：设置图件格式。
- `--jcvi-workflow <name>`：选择 engine workflow(引擎工作流)。
- `--jcvi-layout <path>`：双物种流程中传入 JCVI layout(布局) 文件。
- `--jcvi-seqids <path>`：双物种流程中传入 JCVI seqids(序列编号) 文件。
- `--blastn <path>` 与 `--makeblastdb <path>`：显式指定 BLAST+ executable(可执行文件)。
- `--align-soft {blast,last,diamond_blastp}`：选择比对后端，默认 `blast`。
- `--dbtype {nucl,prot}`：序列类型，默认 `nucl`。
- `--cscore <float>`：同源匹配过滤强度，默认 `0.7`。
- `--dist <int>`：共线性锚点间最大基因距离，默认 `20`。
- `--iter <int>`：Block 过滤迭代次数，默认 `1`。

## 目标基因局部共线性选项

当只关注参考物种中某些目标基因的局部邻域时，使用以下参数：

- `--target-genes <id1,id2,...>`：参考物种中的目标基因 ID。
- `--up <int>`：目标基因上游取多少个基因，默认 `20`。
- `--down <int>`：目标基因下游取多少个基因，默认 `20`。
- `--split-targets`：多个目标基因时各自单独出图；否则合并为同一区域。
- `--label-targets`：在图中标注目标基因名称。
- `--reference <name|index>`：指定参考物种；目标基因 ID 必须来自该物种。

示例：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference subject --target-genes AT1G01010,AT1G01020 --up 20 --down 20 --force
```

多物种示例（固定 `query` 为参考，分别与 `subject`、`third` 运行局部共线性）：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference query --target-genes AT1G01010 --up 20 --down 20 --force
```

## 图件样式选项

- `--glyphstyle {box,arrow}`：基因形状。
- `--glyphcolor {orientation,orthogroup}`：基因着色方案。
- `--shadestyle {curve,line}`：共线性连线样式。
- `--figsize <WxH>`：画布尺寸，例如 `10x5`。
- `--dpi <int>`：分辨率，默认 `300`。

示例：

```powershell
GenomeLens.exe analyze mcscan input output `
  --formats pdf --dpi 300 --glyphstyle arrow --shadestyle curve --force
```

当前支持的 workflow(工作流)：`mcscan_pairwise`、`graphics_synteny`、`graphics_dotplot`、`graphics_karyotype`、`catalog_ortholog`、`local_synteny`。兼容别名 `dotplot`、`karyotype`、`local` 会被规范化。

`graphics_karyotype_global` 是多物种运行时自动调度的内部聚合 workflow(工作流)，把各对 pairwise 共线性边渲染成一张全局核型总图，不通过 `--jcvi-workflow` 直接选择。

## 帮助

总帮助：

```powershell
GenomeLens.exe --help
```

查看指定命令参数：

```powershell
GenomeLens.exe help analyze mcscan
GenomeLens.exe help -c "analyze mcscan"
```

## JSON request(请求)

> 当前版本已暂时注销 `analyze run` 与 `analyze template` 入口。GUI、插件、Agent 或批处理系统可先通过 `analyze mcscan` 验证参数与输出；后续版本会重新开放稳定的 JSON request 入口。

`analyze mcscan` 内部仍会归一化为同一种 `analysis_request`，再交给 dispatcher(调度器) 执行。

## 配置文件

`config init` 会写出两个配置文件：

- `genomelens.config.json`：工具本身设置，例如 workspace(工作区)、默认输出目录、日志级别。
- `jcvi.config.json`：JCVI 子工具/引擎设置，例如 `jcvi_engine_path`、BLAST+ 路径、默认线程数、默认 workflow(工作流)、输出格式。

第 2 版 `jcvi.config.json` 采用分组结构（`toolchain`、`runtime`、`mcscan`、`local_synteny`），仅支持第 2 版分组结构。详见 [`配置文件说明.md`](../使用方法/配置文件说明.md)。

## 输出

双物种流程会把 `run_summary.json` 写入 `<outdir>/report/`，把 engine manifest(引擎清单) 与 engine summary(引擎摘要) 保存到 `<outdir>/intermediate/jcvi/`。默认 `graphics_synteny` 会归档 `dotplot.png` 和 `synteny.png`。当指定 `--target-genes` 时，引擎会运行 `local_synteny`，局部图件与可回流精修的 `.blocks`、`.bed`、`.layout` 会放入 `<outdir>/intermediate/local/`。

多物种流程会在顶层写出汇总摘要，并新增三段式中间目录：

```text
<outdir>/report/run_summary.json
<outdir>/inputs/analysis_request.json
<outdir>/results/figures/
<outdir>/intermediate/ortholog/          # 同源搜索与数据准备结果
<outdir>/intermediate/mcscan/             # 全基因组共线性区块
<outdir>/intermediate/local/              # 局部共线性绘图结果（最终图片与精修文件）
<outdir>/intermediate/pairwise/<speciesA>__<speciesB>/
```

`analysis_request.json` 是本次运行的归一化请求快照，便于 GUI、插件、Agent 和发表图件追溯。顶层 summary(摘要) 中的 `pairwise_jobs` 会列出每一对物种的子任务、子任务 summary、anchors、simple、blocks 和最终图件。顶层 `results/figures/` 中的图件会带 pairwise 前缀，避免不同子任务的 `dotplot.png` 或 `synteny.png` 互相覆盖。

## 终端输出

默认情况下，`analyze mcscan` 会在终端打印一份人类可读的整合摘要，包含：

- 运行状态（`SUCCEEDED` / `FAILED`）
- 工作流名称与任务类型
- 物种数量与名称
- 多物种流程的 pairwise 子任务成功数 / 总数
- 全局总图数量（多物种流程）
- 最终图件列表
- 关键中间结果（anchors、simple、blocks、blast table）
- 运行摘要 `run_summary.json` 的路径

需要机器读取或与其他工具管道连接时，使用 `-j` / `--json` 输出原始 JSON 摘要：

```powershell
GenomeLens.exe analyze mcscan input output --force -j
```

`-j` 只向 **stdout(标准输出)** 写入 JSON；日志与进度信息写入 **stderr(标准错误)**，不会污染 JSON 输出。

## 当前边界

当前已实现 2 到 n 个物种的自动 pairwise(两两比较) 编排，并复用真实 BLAST+ 与 JCVI 工作流。全局多物种 layout(布局) 自动优化、跨全部物种的一张最终美化版总图、物种顺序自动推荐和机器学习评分尚未接入。
