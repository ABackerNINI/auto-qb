# 仓库存量文件 CRLF/LF 混行尾: 补丁按统一行尾假设必失配

> 摘要: 仓库存量文件 CRLF/LF 混行尾: 补丁按统一行尾假设必失配
> 触发: 行尾不同, CRLF, LF, 批量替换未命中, count=0, edit 匹配失败, 补丁失配, here-string 转义
**Refs:**

### 仓库存量文件 CRLF/LF 混行尾: 按「统一行尾」假设写补丁必然一半失配

- **触发**: 用 edit/apply_patch/脚本批量替换改仓库存量文件(`scripts/`、`.commands/` 下的机检脚本尤其如此)。
  本仓文件**逐文件混合**: 同一批改动里 `check_command_drift.py` 与 `.my-commit-flow.toml` 是 CRLF,
  而 `_pipeline.py` / `check_context_caps.py` / `check_kb_structure.py` 是 LF —— 按「仓库都是 X」假设写的补丁,
  一半匹配不上。伴生坑: 用 PowerShell here-string 直传 Python 三引号补丁时, `\'`/`\\n` 等要按
  「here-string 逐字直传 → 非原始三引号再解一层转义 → 落盘字节」逐层数, 多转一层就是语法损坏。
- **判别**: ①edit 工具报「内容完全一致, 只有行尾不同: 磁盘是 CRLF」—— 这是在告诉你该文件是 CRLF,
  换个 LF 文件时**不会报**而是静默失配; ②批量替换程序报 `count=0` 或 `count=2`(锚点不唯一); ③py_compile
  在补丁后报 unexpected character / IndentationError —— 先查转义层, 再查行尾。
- **处置**: ①批量替换程序**逐文件探测 NL**(`"\\r\\n" if "\\r\\n" in s else "\\n"`), old/new 按 LF 书写、
  落盘前按该文件的 NL 转换, 每处替换断言 `count == 1`, 写入用 `open(..., newline="")` 保住行尾;
  ②锚点选**无全角标点/无引号的 ASCII 行**(run 行、match 行), 注释行含全角引号/破折号逐字匹配不可靠,
  改用前缀定位 + 行级插入; ③转义复杂(嵌套引号/f-string)时不要硬拼 here-string —— 用 write 工具落
  精确块到临时文件再拼接, 完事删除; ④替换后立即 `py_compile` 全部改动文件。
- **守阵**: 无专门机检 —— 三类症状(行尾报错 / count≠1 / compile 红)都在补丁程序自身的断言层拦; 新增测试文件用 LF, 存量不回改。
- **复发**: 1 (2026-11-01, 提交闸门收窄实施轮: 首个补丁按 CRLF 假设对 LF 文件失配一次、here-string 多层转义写坏测试文件一次 —— 两处都靠「compile + count 断言」当轮兜住, 未入库; 当时不知道有这条坑, 路由未到)
