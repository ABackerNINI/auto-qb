# 26-11-03-memory-bank-kb-nav-searchbox — kb.nav 搜索支持文件名与相对路径

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** kb.nav 搜索支持文件名与相对路径 (navSearchText 单点, 三视图共用)
**Topics:** memory-bank-kb-nav-searchbox

## 原始请求

1. 修复 kb.nav 搜索框不支持按文件名/文件路径搜索: #gq 输入 `memory-bank/reports/26-11-01-0057-report-rule-engine-redesign.html` 无匹配。
2. 先按会话协议同步, 定位搜索索引构建与前端过滤逻辑 (生成物 + 源脚本), 写清索引当前收录字段与路径不可搜的根因。
3. 最小修复: basename 与相对路径可命中, 原标题/关键词行为、排序与展示不变; 不把正文塞进索引; 大小写/分词问题一并最小处理。
4. 补守阵: basename、完整相对路径命中, 原搜索用例不回归; 同步测试文件头部「## 测试计划」清单。
5. task id 跑针对性测试与 test.full; 用实际生成页/索引数据验证复现; 不 commit/push, 不改产品 `src/` 与红线文件。
6. 用户确认「提交」后按规程收尾并推送 Gitee。

## 思考过程与决策

- 根因: 搜索 haystack 只拼 `title + topic + issue-summary`, `link` 未入索引, 且匹配是对整串做 `includes`; 正文本来就不在索引里 (也不应加入, 体积口径)。
- 决策: 壳内新增 `navSearchText()` / `navSearchQuery()` 单点, 索引加法式补 `link` (basename 随之可搜) 与 `memory-bank/<link>` 仓库根相对形态; 台账 `aFiltered` / 控制台 `renderChannels` / 卡片墙 `cVisibleItems` 统一消费, 避免三份 haystack 漂移。匹配统一小写 + 反斜杠归一; 不引入分词/模糊匹配 (保持原有整串 includes 行为)。
- 数据层无需改动: `gen_doc_map.collect()` 已输出 `link`, 服务层/静态导出原样注入 DATA; 用 `kb.nav --gen-static` 重生成页面做真实数据验证。
- 提交闸门暴露 vnu 规范错误 (`main` 不得作 `section` 后代): 台账外层 `section` 改 `div`, 最小 markup 修复。
- 合流后远端 `61b04b85` 新增真机守阵误红: 受控桩默认依赖 `tmp_path` 所在卷与祖先目录属性, 本机 `TMP=C:/AppData` 必然红; 桩化 `SystemDrive` 与非 `hid` 属性, 仅测试改动。

## 实现计划

1. 同步 + 按 memory-bank 路由定位 `nav_page.html` 过滤逻辑与 `nav_data` 字段。
2. 加搜索单点并替换三处过滤; 生成静态页用真实 DATA 验证复现用例。
3. 补 `test_search_matches_file_name_and_relative_path` (node 回放页内真实 JS) + 同步测试计划清单。
4. 文档回写 (`nav_page.html` docstring + `progress/implemented-tooling.md`), `kb.wrap` 收尾。
5. `test.full` 绿后落基线切片; 提交闸门红处置 (vnu + 远端真机守阵) 后 `ship.commit`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 同步 + 定位实现 | Done(2026-11-03) |
| 2 | 搜索单点最小修复 + 生成页验证 | Done(2026-11-03) |
| 3 | 守阵 + 测试计划清单 | Done(2026-11-03) |
| 4 | 文档回写 + kb.wrap | Done(2026-11-03) |
| 5 | test.full + 基线 + 提交推送 | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

- 2026-11-03 搜索修复落地: `navSearchText` 单点补 `link` 与 `memory-bank/` 形态, 三视图统一消费, 守阵 +1; 全量绿, 数字见 kb.baseline。
- 2026-11-03 提交闸门处置: vnu 错误 (台账 `section`→`div`) 与远端新真机守阵环境依赖 (桩化 `SystemDrive`/祖先属性), 复跑全绿后 `ship.commit`。
