# 工具链说明

GenomeLens 依赖外部 runtime toolchain(运行时工具链)，但不把大型二进制提交进 Git。

## 定位优先级

工具链解析顺序固定为：

1. CLI(命令行接口) 显式路径
2. 配置文件
3. 环境变量
4. 系统 `PATH`
5. 打包资源
6. `toolchains/` 本地缓存

支持的显式配置包括 `jcvi_engine_path`、`blastn_path`、`makeblastdb_path` 和 `magick_path`。

## 当前工具链

- BLAST+：用于 `makeblastdb` 和 `blastn`，是当前双物种 JCVI 主链路必需工具。
- jcvi-genomelens：独立 engine(引擎)，随包包含 vendored JCVI(随包 JCVI)。
- ImageMagick：当前作为 optional runtime toolchain(可选运行时工具链)，主要用于后续图像格式转换或验证；默认 JCVI 绘图链路不要求它参与每次分析。

## 下载与缓存

`analyze mcscan` 缺少 BLAST+ 时会尝试自动下载；`genomelens check --install-missing` 会尝试安装缺失的 BLAST+ 和 ImageMagick。

下载缓存目录：

```text
references/downloads/toolchains/
```

解压后的运行时缓存目录：

```text
toolchains/
  blast/current/
  imagemagick/current/
  jcvi-genomelens/current/
```

自动下载的 archive(归档文件) 会写入 SHA256 manifest(哈希清单)，复用缓存时会校验记录。tar/zip 解压会拒绝路径穿越和链接项，避免归档内容写出目标目录。
