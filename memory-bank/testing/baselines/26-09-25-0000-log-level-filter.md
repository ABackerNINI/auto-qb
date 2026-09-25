# 1377 → 1384 (+7) —— 运行日志按等级查看修复

> 摘要: /api/log 等级过滤按字面量锚死默认格式 ⇒ 生产 format 恒空; filter_log_lines 按配置 format 反推; 与 M2/M3 并行开发, 合流前旧基实测; 时分不可考; 当日序位第 1
> 基线时间: 2026-09-25 00:00
> 档案: 26-09-25-webui-log-level-filter

- ↑ 收集数 **1377 → 1384**(**+7**; 2026-09-25 **运行日志按等级查看修复**); ⚠ 与 M2/M3 两批**并行开发**, 本条在合流前旧基上实测(未含 M2/M3 用例), 合流后总账以 baseline.md 顶部为准):
  用户报"新版设置里运行日志选 WARNING 显示『日志文件暂无内容』"。根因: `/api/log` 的等级过滤按
  **字面量** `f"[{lv}" in ln` 捞, 锚死默认格式的方括号; 生产 `config.yml` 的 `log.format` 是
  `%(asctime)s - %(levelname)s - %(message)s`(无方括号)⇒ 选任何等级恒空, 且与"确实没有该等级日志"
  完全同形(不报错、不返回 None)。修法: 新增 `infra/logging.py::filter_log_lines()` —— 按**配置的
  format 反推** `%(levelname)s` 位置编正则(字面量空格**不放宽**成 `\s*`: 放宽会让前一个纯字母字段把
  等级名吃掉, 实测 `%(name)s %(levelname)s` 下 `core` 被当成等级; **要吸收**字段宽度补的空格:
  `%(levelname)-8s` 在等级名后补空格, 漏了则该格式一行都对不上), 多行记录(traceback)折行跟随上一条的
  取舍; 两种"筛不了"(格式无等级字段 / 已存行与当前格式不符)回**全部行 + `note` 提示语**, 前端两套 UI
  两处日志章节成对加提示条。用例: `test_logging.py` +4(格式形状矩阵 / 多行记录 / 提示语 / 字段宽度与
  `%%` 变体) + `test_web.py` +3(生产格式 / 多行 traceback / note); **旧 `test_api_log_endpoint` 重写** ——
  它手写 `[INFO]` 语料而替身 format 是 `%(message)s` ⇒ **配置没被读到, 摆设断言**(旧实现下绿、真机恒空
  它也绿)。**红验**: 临时还原旧字面量实现 ⇒ 7 条新用例全红。端到端(真机 `setup_logging` + 真实
  `exc_info` traceback, 生产 format): 全部 8 行 / INFO 2 / WARNING 1 / ERROR 5(整段栈保留)。
  冒烟 82 项 0 失败 + 专项浏览器验证 18 项 0 失败(双 UI × 新版/经典 × 双格式)。
  本轮另踩两坑(均已入库): 手工跑子集把 cmd.exe 的 `set "TMPDIR=..."` 照搬进 Git Bash ⇒ TMPDIR 没导出
  (tmpdir.md 复发 2); `test_commands_engine.py` 两条 GBK 守阵在本 shell 恒红 = `PYTHONUTF8=1` 注入
  (patching.md 已有记载), `env -u` 后全绿, 非回归。详见
  `tasks/26-09-25-webui-log-level-filter.md` 与 `pitfalls/backend/format-driven-parse.md`。
