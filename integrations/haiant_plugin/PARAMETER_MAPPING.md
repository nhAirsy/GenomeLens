# HAIant parameter mapping(参数映射)

插件把 HAIant 平台的 `params.json` 转换为 GenomeLens CLI(命令行接口) 参数，再调用 `GenomeLens-runtime.exe analyze mcscan <input-dir> <output-dir> [options]`。

由于当前版本 CLI 已移除 `analyze run` 与 `analyze template`，插件会先把平台显式物种清单拷贝到一个临时输入目录，然后通过 `analyze mcscan` 的自动目录发现模式运行。所有相对路径都按 `params.json` 所在目录解析。

## 推荐字段

| Platform field(平台字段) | Type(类型) | Request field(请求字段) | Required(是否必填) | Default(默认值) |
|---|---|---|---|---|
| `input_mode` | enum | `input.mode` 与每个物种的 `input_mode` | yes | `bed_cds` |
| `species` | array | `input.species[]` | yes | |
| `output_dir` | path | `output.directory` | yes | `output` |
| `workflow` | enum | `options.workflow` | no | `graphics_synteny` |
| `threads` | integer | `options.threads` | no | `4` |
| `min_block_size` | integer | `options.min_block_size` | no | `5` |
| `formats` | csv/list | `output.formats` | no | `png` |
| `jcvi_layout` | path | `options.jcvi_layout` | no | |
| `jcvi_seqids` | path | `options.jcvi_seqids` | no | |
| `allow_simplified_fallback` | boolean | `options.allow_simplified_fallback` | no | `false` |

`species` 在 `bed_cds` 模式下使用：

```json
[
  {"name": "speciesA", "bed": "input/a.bed", "cds": "input/a.cds"},
  {"name": "speciesB", "bed": "input/b.bed", "cds": "input/b.cds"}
]
```

`species` 在 `gff_genome` 模式下使用：

```json
[
  {"name": "speciesA", "gff": "input/a.gff3", "genome": "input/a.fa"},
  {"name": "speciesB", "gff": "input/b.gff3", "genome": "input/b.fa"}
]
```

## workflow(工作流)

`workflow` 可选值包括 `graphics_synteny`、`graphics_dotplot`、`graphics_karyotype`、`mcscan_pairwise` 和 `catalog_ortholog`。兼容别名 `dotplot`、`karyotype` 会由 engine(引擎) 规范化。

插件会在输出目录写入：

```text
genomelens_request.json
```

该文件仅作为运行轨迹保留，当前 CLI 不再读取它。实际运行命令形如：

```text
GenomeLens-runtime.exe analyze mcscan .genomelens_plugin_input output --force --threads 2 --min-block-size 1 --jcvi-workflow graphics_synteny --formats png
```
