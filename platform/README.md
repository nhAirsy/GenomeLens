# GenomeLens shell(外壳)

`platform/` 包含面向用户的 GenomeLens shell(外壳)。它负责 CLI(命令行接口)、输入校验、预处理、工作区布局、外部工具发现、engine manifest(引擎清单) 生成和最终 run summary(运行摘要)。

shell 不直接 import(导入) 上游 `jcvi`。允许使用的 engine interface(引擎接口) 只有：

```text
jcvi-genomelens probe --json
jcvi-genomelens run --manifest <path> --outdir <path>
```

## 当前范围

当前 shell 支持 2 到 n 个物种输入：

- 普通用户入口：`analyze mcscan <input-dir> <output-dir>`，从目录自动发现同名 BED+CDS/PEP 或 GFF+FASTA 文件对，并允许不同物种混用两类输入。
- 2 个物种时自动运行双物种真实 JCVI 流程。
- 3 个以上物种时自动拆成 all-vs-all pairwise(全组合两两比较) 子任务。
- 带 `--target-genes` 时，以参考物种为中心与每个目标物种运行 `local_synteny`。
- 配置文件可预设工具链路径、线程数、block size 和输出格式。
- 默认 `graphics_synteny` 会为每个 pairwise 子任务生成 dotplot(点图) 与 synteny figure(共线性图)。

`analyze run` 与 `analyze template` 已在当前版本移除，GUI、插件、Agent 可先通过 `analyze mcscan` 配合 `--jcvi-config` 或输入目录下的 `jcvi.config.json` 完成参数配置。

尚未完成的是跨全部物种的一张全局美化总图、全局 layout/seqids 自动优化和机器学习评分。

## 常用开发命令

```powershell
python -m genomelens.cli.main --help
python -m genomelens.cli.main config init --workspace .work --force
python -m pytest platform/tests
```
