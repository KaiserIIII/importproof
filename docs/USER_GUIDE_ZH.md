# ImportProof 中文说明

ImportProof 在本机对比导入前后的 CSV、TSV、XLSX，保留原始值、比较规则和证据。它能确认“按本次规则观察到的差异”，不能仅凭两份文件断定是 Excel、LibreOffice 或其他软件造成，也不能恢复已损坏的数据。

## 安装和启动

需要 **Python 3.13**。Python 3.12 的 CSV 引号空字符串读取有已知缺陷，本版不支持。在源码根目录打开 PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps .
.\.venv\Scripts\python.exe -m importproof serve
```

Linux 使用 `python3.13 -m venv .venv`，之后把 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`。首次安装下载锁定依赖，运行时不访问外部网络。打开 **http://127.0.0.1:8766**；终端保持打开，Ctrl+C 停止。源码修改后需重新安装；卸载用该环境的 `python -m pip uninstall importproof`，独立虚拟环境可随后删除。

## 页面操作

1. 将原始文件放入 Before，接收或转换后的文件放入 After。可选择文件，或在两个区域分别拖入一个文件。
2. Primary key columns 填已确认稳定的主键，如 `id` 或 `id,region`。空白时按行位置比较，这是一个明确假设，不是自动证明身份。
3. Allow order changes 允许行/列排序变化。无主键时只能按精确值/声明语义的多重集合匹配，未匹配的更改仍为 UNKNOWN。
4. 展开 Advanced policy 修改 JSON。可指定 `text_columns` 必须保留文本、`numeric_columns` 使用精确十进制、`date_columns` 使用指定日期格式，或设置编码/分隔符、Sheet 对、显式列名映射、允许忽略的列/空白/Unicode规范化。
5. Compare files 后查看概览，按四种判决筛选。Before/After 显示原始值、类型、行列和来源位置，展开完整证据查看详细内容。
6. JSON/HTML/CSV 按钮导出实际报告。报告含原始数据，请私密保存。CSV 是差异索引，完整政策和元数据以 JSON 为准。界面当前为英文，本说明与其功能一致。

## 判决含义

| 判决 | 使用方式 |
| --- | --- |
| CONFIRMED_LOSS | 按记录的身份/对齐假设和规则，可以确认缺失或不允许的表示、类型、数值变化；不证明业务意图或具体软件原因。 |
| SUSPECTED_CONVERSION | 变化符合去前导零、科学计数法、日期转换等特征，原因仅为怀疑，不能给某个软件归因。 |
| EQUIVALENT | 在支持范围和明确规则下等价；不是文件字节相同，也不代表完整工作簿视觉保真。 |
| UNKNOWN | 主键重复/缺失、匹配歧义、公式/错误、不支持内容或截断，无法可靠判断，不算通过。 |

总判决优先 UNKNOWN，其次确定差异、怀疑转换、等价。统计是 finding 数，不是独立损坏单元格数；同一变化可能有“确定差异”和“怀疑原因”两条。不要相加推导错误率。

## 命令行和规则

```powershell
.\.venv\Scripts\python.exe -m importproof compare examples/before.csv examples/after-controlled.tsv --policy examples/strict-policy.json --output output-demo
```

输出目录必须不存在，父目录须存在，避免覆盖旧报告。stdout 是一个完整 JSON，stderr 是错误或保存位置。退出码 0=规则下等价，2=差异/UNKNOWN，1=输入/处理/输出失败；参数语法错误使用 argparse 的2。自动化应同时检查 JSON 和退出码。

`--keys id,region` 是联合键，`--ignore-order` 允许排序不同。主键按原始值+类型匹配，不受数值/日期等价规则影响；键变化表现为失去/新增身份。重复键或缺失键不随意配对。列名重复时可用 `#1`、`#2` 指位置，但重复表头本身仍需人工复核。列改名只有 `column_map` 明确对应才能视作允许的改名，不用模糊匹配冒充相同。

完整 JSON 示例见 [英文 README](../README.md)。`before`、`after` 可设 `encoding` 和 `delimiter`（`,`、`\t`、`;`、`|`）及 `quotechar`；XLSX 不接收文本解析选项。`date_formats` 用 strptime 格式，如 `%Y-%m-%d`、`%d/%m/%Y`；两种解释同时成立则 UNKNOWN。文本/数值/日期列不能重叠。`null_tokens` 明确声明哪些文本按缺失值解释，默认不猜。

## 支持边界

UTF-8/BOM、UTF-16 BOM自动读取，CP1252、GB18030 等须明确指定；解码错误拒绝，不静默替换。默认 CSV逗号、TSV制表符；其他分隔/歧义要求明确选择。原始空字段、引号空字符串、缺失单元格不同，不能自动当数据库NULL。空白记录、不同宽度和重复列名保留问题。

XLSX 默认比较所有工作表。可用 `before_sheet`/`after_sheet` 限定一对，其他Sheet被明确排除。公式只读取文字/缓存，不计算。宏、二进制和外部链接拒绝；合并单元格、隐藏/未知结构、丰富格式等可能 UNKNOWN。原始数字 XML 保留精确文本，数值比较不经浮点取整。数字显示格式改变但未指定数值语义时需要人工复核；不完整模拟表格显示效果。

每文件5MiB，解压XLSX50MiB、1000个ZIP成员、20个Sheet、50000行含表头、256列、300000个矩形单元格、每格65536字符、2000条差异、子进程30秒、结果16MiB。不是无限大文件流处理。超限不判相等；截断为UNKNOWN。

Linux 有512MiB子进程地址空间上限；**Windows 无硬内存配额**。localhost 服务是单请求、有限队列及上传/响应大小限制，不是完整OS沙箱，不应开放到公网。报告哈希只标识输入字节，不证明来源真实性。

样例全部非私人数据：SQLite样例是实际运行的受控 REAL字段导入导出，其余变化是明确构造；**没有验证真实 Excel/LibreOffice 转换或生产迁移**。实际测试、浏览器及跨平台记录见 [验收](ACCEPTANCE.md)，竞品实测见 [对照](COMPETITORS.md)。MIT源码，第三方依赖保留各自许可证。本地交付不自动公开仓库、推送、发布包或部署。
