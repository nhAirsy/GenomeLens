# Runtime toolchains(运行时工具链)

本目录只放已经解压的 runtime tools(运行时工具)。它是 local cache(本地缓存) 或 full-package inputs(完整包输入)，不进入 Git 跟踪。

## 目录

- `blast/`：BLAST+ runtime(BLAST+ 运行时)。
- `imagemagick/`：ImageMagick runtime(ImageMagick 运行时)，当前为可选工具链。
- `jcvi-genomelens/current/jcvi-genomelens.exe`：打包后的 GenomeLens engine runtime(引擎运行时)。

`scripts/build_split_packages.ps1` 会重新构建 engine(引擎)，并把当前 engine executable(引擎可执行文件) 同步到 `toolchains/jcvi-genomelens/current/`。

## 定位策略

GenomeLens 对 BLAST+ 和 ImageMagick 会先检查 CLI 显式路径、配置文件、环境变量和系统 `PATH`，再检查打包资源和本地工具链缓存。分析过程中缺少 BLAST+ 时可自动安装；`genomelens check --install-missing` 会尝试安装缺失的 BLAST+ 和 ImageMagick。

下载得到的 archives(归档包) 放在：

```text
references/downloads/toolchains/
```

## 当前范围

当前工具链服务于双物种真实 JCVI 链路。多物种任意数量流程完成后，可能需要进一步扩展缓存结构、工具链版本记录和离线包清单。
