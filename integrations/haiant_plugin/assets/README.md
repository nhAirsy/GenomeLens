# HAIant assets(智然体资源)

- `config.json`：智然体平台表单 metadata(元数据)，包含 2 到 n 个物种的 `species[]` 参数。
- `params.json`：可运行的双物种示例参数文件；需要多物种时继续向 `species[]` 追加条目。
- `README.md`：供插件包维护者查看的资源说明。

插件不会直接拼接旧版 `analyze mcscan` 手动参数。当前 CLI 已移除 `analyze run`，插件会先把平台参数中的物种文件拷贝到临时输入目录，再调用 `analyze mcscan` 目录发现模式运行。
