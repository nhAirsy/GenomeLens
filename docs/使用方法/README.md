# 使用方法

本文说明当前版本可用的共线性分析入口。`analyze mcscan` 可以接收 2 到 n 个物种：传入 2 个物种时运行双物种真实 JCVI 流程，传入 3 个以上物种时自动拆成所有 pairwise(两两比较) 子任务并汇总结果。

## 环境检查

开发环境：

```powershell
conda activate genomelens
python -m genomelens.cli.main check
```

打包运行时：

```powershell
GenomeLens.exe check
```

需要机器读取时使用 JSON(JSON 数据) 输出：

```powershell
GenomeLens.exe check -j
```

## 一步自动运行

新手优先使用自动目录发现：把所有物种文件放到一个输入目录，并让同一物种的文件使用同一个 basename(基础文件名)。

BED+CDS 示例：

```text
input/
  speciesA.bed
  speciesA.cds
  speciesB.bed
  speciesB.cds
  speciesC.bed
  speciesC.cds
```

也支持蛋白序列作为 CDS 输入：`.pep`、`.pep.fa`、`.faa`。

GFF+FASTA 示例：

```text
input/
  speciesA.gff3
  speciesA.fa
  speciesB.gff3
  speciesB.fa
```

同一个输入目录可以按物种混用两类输入。例如 `speciesA.bed + speciesA.cds` 与 `speciesB.gff3 + speciesB.fa` 可以放在同一目录；GenomeLens 会只预处理 GFF/GTF + FASTA 物种，并把所有物种统一交给 JCVI 链路。若同一个物种同时提供两类文件，自动发现会优先使用已准备好的 `BED + CDS/PEP`。

一键运行：

```powershell
GenomeLens.exe analyze mcscan input output --force
```

默认会打印人类可读的整合摘要（状态、物种、图件、关键中间结果、摘要路径）。需要原始 JSON 时加上 `-j` / `--json`：

```powershell
GenomeLens.exe analyze mcscan input output --force -j
```

`-j` 只向 stdout 输出 JSON，日志写入 stderr，方便管道化处理。

## 使用 GFF+FASTA 输入运行

输入是 GFF3/GTF(annotation，注释文件) 和 genome FASTA(基因组序列) 时，GenomeLens 会先抽取 BED 和 CDS，再进入 JCVI 分析：

```powershell
GenomeLens.exe analyze mcscan input output --min-block-size 1 --force
```

## 使用 BED+CDS 输入运行

如果已经准备好 JCVI 可用的 BED 与 CDS FASTA，同样放入输入目录并保持同名：

```powershell
GenomeLens.exe analyze mcscan input output --min-block-size 1 --force
```

## workflow(工作流)

默认 `graphics_synteny` 会执行真实 BLAST+ 与 JCVI MCscan，并输出：

- `dotplot.png`
- `synteny.png`
- anchors(锚点)
- simple blocks(简化区块)
- blocks(区块轨道)

也可以通过 `--jcvi-workflow graphics_dotplot` 单独生成 dotplot(点图)，或通过 `--jcvi-workflow graphics_karyotype` 生成 karyotype(核型) 共线性图。

当指定 `--target-genes` 时，工作流会自动切换为 `local_synteny`，以目标基因为中心截取上下游区域并绘制局部共线性图。

如果需要了解“一站式 JCVI 多物种局部共线性分析”内部到底包含哪些阶段，见 [`JCVI能力与配置.md`](JCVI能力与配置.md) 的“主一站式流程”章节。

## 比对后端与同源性参数

- `--align-soft {blast,last,diamond_blastp}`：选择比对后端。`blast` 默认；`last` 适合大多数核酸/蛋白场景；`diamond_blastp` 用于远距离蛋白比对。
- `--dbtype {nucl,prot}`：序列类型。
- `--cscore`：同源匹配过滤强度（默认 0.7）。
- `--dist`：共线性锚点间最大基因距离（默认 20）。
- `--iter`：Block 过滤迭代次数（默认 1）。

## 目标基因局部共线性

- `--target-genes AT1G01010,AT1G01020`：指定参考物种目标基因 ID。
- `--up 20 --down 20`：上下游窗口大小。
- `--split-targets`：多个目标基因各自单独出图。
- `--label-targets`：标注目标基因名称。
- `--reference <name|index>`：指定参考物种；默认第一个物种。多物种且带 `--target-genes` 时，只运行参考物种与每个目标物种的局部共线性。

示例：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference subject --target-genes AT1G01010 --up 20 --down 20 --force
```

多物种局部共线性（固定 `query` 为参考，分别与每个目标物种比较）：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference query --target-genes AT1G01010 --up 20 --down 20 --force
```

## 图件样式

- `--glyphstyle {box,arrow}`：基因形状。
- `--glyphcolor {orientation,orthogroup}`：着色方案。
- `--shadestyle {curve,line}`：连线样式。
- `--figsize 10x5`：画布尺寸。
- `--dpi 300`：分辨率。
- `--formats pdf,png`：输出格式。

## 配置文件

`config init` 会写出两个配置文件：

- `genomelens.config.json`：GenomeLens 工具本身配置，例如 workspace(工作区)、默认输出目录、日志级别。
- `jcvi.config.json`：JCVI 子工具/引擎配置，例如 engine(引擎) 路径、BLAST+ 路径、ImageMagick 路径、线程数、最小 block size、默认 workflow(工作流) 和输出格式。

第 2 版 `jcvi.config.json` 采用分组结构（`toolchain`、`runtime`、`mcscan`、`local_synteny`），仅支持第 2 版分组结构。详见 [`配置文件说明.md`](配置文件说明.md)。

### 指定 jcvi 配置文件

`analyze mcscan` 支持三种方式指定 `jcvi.config.json`，优先级从高到低：

1. CLI 显式 `--jcvi-config`：

   ```powershell
   GenomeLens.exe analyze mcscan input output `
     --jcvi-config workspace\jcvi.config.json `
     --force
   ```

2. 位置参数（放在 `output_dir` 之后）：

   ```powershell
   GenomeLens.exe analyze mcscan input output workspace\jcvi.config.json --force
   ```

3. 输入目录下的 `jcvi.config.json`（`input\jcvi.config.json`）
4. 当前工作目录下的 `jcvi.config.json`（`./jcvi.config.json`）

主配置文件仍通过 `-c, --config` 指定：

```powershell
GenomeLens.exe analyze mcscan `
  -c workspace\genomelens.config.json `
  --jcvi-config workspace\jcvi.config.json `
  input output `
  --force
```

完整字段说明、示例和优先级详见 [`配置文件说明.md`](配置文件说明.md)。

## 帮助

查看总帮助：

```powershell
GenomeLens.exe --help
```

查看指定命令参数：

```powershell
GenomeLens.exe help analyze mcscan
```

## JSON request(请求)

> 当前版本暂时只开放 `analyze mcscan`；`analyze run` 与 `analyze template` 已注销，后续版本会重新开放稳定的 JSON request 入口。

需要让 GUI、插件、Agent 或批处理系统稳定调用时，可先通过 `analyze mcscan` 配合 `--jcvi-config` 或输入目录下的 `jcvi.config.json` 完成参数配置。`analyze mcscan` 内部仍会归一化为同一种 request(JSON 请求) 并保存到 `output\inputs\analysis_request.json`。

## 结果位置

- `output\report\run_summary.json`：shell summary(外壳摘要)。
- `output\inputs\analysis_request.json`：本次运行的归一化 request(JSON 请求) 快照。
- `output\results\figures\`：归档后的图件。
- `output\intermediate\jcvi\engine_run_summary.json`：双物种流程的 engine summary(引擎摘要)。
- `output\intermediate\jcvi\`：双物种流程的 JCVI 中间文件（blocks、anchors、blast table 等）。
- `output\intermediate\local\`：指定 `--target-genes` 运行 `local_synteny` 时，局部共线性图件与可回流精修的 `.blocks`、`.bed`、`.layout`。
- `output\intermediate\pairwise\`：多物种流程下的 pairwise 子任务目录。
- `output\inputs\prepared\`：GFF+FASTA 预处理输出。

多物种流程的顶层 summary(摘要) 会包含 `pairwise_jobs`，每个条目对应一组物种两两比较，并记录该子任务的 summary、anchors、simple、blocks 和图件。

## 当前限制

当前已实现 2 到 n 个物种的自动 pairwise(两两比较) 编排。全局多物种 layout(布局) 自动优化、跨全部物种的一张最终美化版总图、物种排序推荐和机器学习评分仍属于后续能力。
