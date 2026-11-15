# 26-11-14-webui-config-backup — WEBUI 配置导出/导入（配置备份 bundle）

**Status:** Done
**Added:** 2026-11-14
**Updated:** 2026-11-15
**Summary:** WEBUI 配置导出/导入专题：计划 26-11-14-0624 Done，S1-S5 全部落地（四阶段提交 fbaae3d5/9b8ff460/d2bba5f0/c85e53bd + S5 收尾回写/基线/坑档）
**Topics:** webui-config-backup
**Refs:** memory-bank/plans/26-11-14-0624-plan-webui-config-backup.html,memory-bank/issues/26-11-14-0625-feat-webui-config-import-diff.html

## 本篇只回答

WEBUI 配置导出/导入专题做到哪、按什么方案做 —— 实施进度与验收的单点事实源；方案细节权威在计划件（§03/§04），本档案只记进度与决策指针。

## 原始请求

1. 在 WEBUI 上新增导出/导入 config / WEBUI 配置功能；
2. 先 grilling 再出一个计划；
3. 用户点名需考虑：两套配置合并成一个文件还是分开；tools 工具配置怎么办；其它落盘文件适不适合导出。

## 思考过程与决策

- 三路只读取证（同会话并行）：①配置系统全貌（config.yml 读写链/敏感字段面/auto-qb-data 落盘清单）②webui API 面与前端结构（92 条端点/四皮肤/设置页 actbar）③gtm 读写机制（status 回显读通道 + PUT 代理写通道 + 离线无通道且架构禁文件通道）。
- grilling 三轮 12 问拍板 D1-D12（完整结论表 = 计划 §06）：单文件 bundle（D1）/ 一律掩码（D2）/ 浏览器偏好纳入（D3）/ gtm 纳入（D4）/ 运行时数据全不纳入（D5）/ 整份替换+三道闸（D6）/ 入口=设置页 actbar 放弃改动左（D7）/ 显式清单+登记闸（D8）/ gtm 在线 HTTP 通道（D9）/ 机器路径原样+提示（D10）/ 静态守阵（D11）/ 导出读磁盘+导入先确认（D12）。
- 显式移出本期：导入 diff 预览 → 入池 issue（见 Refs）。

## 实现计划

计划 26-11-14-0624 §04 分期表：S1 后端导出端点+掩码文本化 → S2 后端导入管线 → S3 前端 ui_prefs+actbar+导出导入流 → S4 静态守阵双清单+e2e → S5 文档回写+基线+真机目检（用户）。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | grilling 12 问拍板 + 三路只读取证 + 计划入库 + diff 预览入池 + 立档 | Done(2026-11-14) |
| S1 | 后端导出：GET /api/backup/export + mask_yaml_text 单点 + 金清单 | Done(2026-11-15, fbaae3d5) |
| S2 | 后端导入：POST /api/backup/import 全管线（掩码 resolve/readonly 回退/聚合校验/.bak/热重载） | Done(2026-11-15, 9b8ff460) |
| S3 | 前端：ui_prefs.js 双清单 + actbar 按钮 + 导出/导入流 | Done(2026-11-15, d2bba5f0) |
| S4 | 守阵：test_webui_static_ui_prefs.py（扫描+交叉+负例）+ e2e | Done(2026-11-15, c85e53bd) |
| S5 | 收尾：文档回写 + test.full 基线 + 真机目检（用户） | Done(2026-11-15, 回写/基线/坑档已落; 真机目检待用户) |

## 进度日志

### R0 · 立档 (2026-11-14)

grilling 12 问拍板 D1-D12 + 三路只读取证 + 计划 26-11-14-0624 入库（Open）+ diff 预览入池 26-11-14-0625 + 本档案立档；零代码改动，kb.check 全绿（主键/认领链/回写守卫全过）；S1-S5 待显式开工。

- 2026-11-14 06:32 grilling 12 问拍板 D1-D12 + 三路只读取证 + 计划 26-11-14-0624 入库(Open, S1-S5 待显式开工) + diff 预览入池 26-11-14-0625 + 档案立档; 零代码改动
- 2026-11-14 06:4x 提交轮评审(分面 2 派遣): 送检 6 全过检(检 6/6), 5 minor+1 nit 当场全修(load_keys_doc 行号/PREF_EXCLUDED 补 drawerOpen+legacy v3/v4/旧版本迁移语义钉死/扫描前缀三形态口径/D6 引文忠实/未知键忽略层级); R1 复评送检 2 全过检(扫描口径撞 cookie/事件名+gtm.config 未知键例外)当场修; R2 复评零 actionable 出口; 全轮检 8/8 修 8 blocker 0

### R1 · S1-S4 四阶段实施 (2026-11-15)

按计划 §04 分四阶段派子代理实施, 每阶段独立提交并实测:

- 2026-11-15 S1 后端导出(fbaae3d5): GET /api/backup/export(routes/backup.py), bundle=format auto-qb-config-bundle/bundle_version 1/config_yaml(掩码化 ruamel 原文)/webui_keys/gtm 四 section; writer.py 新单点 mask_yaml_text(与 mask_tree 同一套 SENSITIVE_KEY_PARTS/TRANSFER_TARGETS_PATH/TARGET_SECRET_KEYS, 注释 byte 级保留; 非映射/空串当空); gtm 经 _source_status 单点离线 null; 掩码失败 500 detail 只含异常类型名(DuplicateKeyError 会回显明文值, 不进响应); 金清单 92→93
- 2026-11-15 S2 后端导入(9b8ff460): POST /api/backup/import, body={bundle_version?, sections{config_yaml,webui_keys,gtm}} 只带勾选段; 响应 {applied, skipped[{section,reason}], warnings}; 管线=内存闸(解析+形状闸[1MiB 上限+alias 共享引用拒收+节点/深度上限]+段形状闸[缺失/空/非映射 422 拒]+双版本闸)→ commit_import_yaml_doc 单锁闭环(现读旧值→unmask resolve[空串/None/哨兵=不可 resolve 聚合 422 逐路径]→readonly 回退→load_config 聚合校验→残留哨兵全树扫描(find_residual_sentinels, R1 堵列表旁路)→.bak+原子写)→reload enqueue; keys 复用 sanitize; gtm 走 _ready_endpoint+PUT 代理(离线 skip/400 透传 warnings); 旧版本 bundle 原样落盘(schema 迁移靠启动链); tool_client.error_text 非 dict payload 兜底; 金清单 93→94
- 2026-11-15 S3 前端(d2bba5f0): static/shared/ui_prefs.js(PREF_KEYS 18 键+PREF_EXCLUDED 7 键双清单单点, grep 实测补计划表遗漏的 autoqb.ui.qbFx/autoqb.ui.kbdPersist 两键)+ collect/apply(未登记键/非字符串忽略+警告; ui_prefs 写回在 POST 成功后, 失败=本机零改动)+ 导出/导入交互流(D6 三闸/D10 机器路径固定提示行/D12 脏态: 导出提示不阻断、导入先确认再 cfgLoad)+ actbar 两钮(settings-detail.html shared 模板, 四皮肤 parity)+ e2e/settings-backup.spec.mjs(6 用例 @fast, prism/atlas 12 例全过)
- 2026-11-15 S4 守阵(c85e53bd): tests/test_webui_static_ui_prefs.py —— 递归 static/ 全树 .js 收存储键字面量(含 const 单键/无插值反引号模板; 注释剥离后代码位), 与双清单交叉验证+死登记红+一键双登红+负例红绿双验四形态(tmp 副本注入); 当前 25 键全登记双向对账零差
- 2026-11-15 四阶段累计实测: test.quick 全绿(基线口径见 kb.baseline), e2e @fast 子集 prism/atlas 12 例全过 —— 全量数字单点见 `commands run kb.baseline`

## 范围外列报 (2026-11-15)

- 2026-11-15 存量 e2e 失败 4 例(与本分支无关, 干净 HEAD 差分实证, 待入池): 2 例 flux chip 语义色/辉光 + 2 例 views 种子计数 300 vs 301 —— 本期不修不写成因结论
- 2026-11-15 T2 报告列报: S1/S2 导出夹具不统一问题(测试基建一致性问题, 不影响行为正确性) —— 待入池
- 2026-11-15 覆盖率闸红(评审新增闸门分支未带测试)→ **已回补闭环**: S1/S2 评审轮加入的防御闸门(alias 共享引用/深度/节点数上限/聚合先验 `_aggregate_config_precheck`/gtm echo 分支等)无对应测试, test.full 覆盖率总闸 99.47% < 99.5(Windows)首度显形 —— S1-S4 阶段只跑 test.quick(跳过覆盖率闸)所以未暴露; 评审后已补 +19 用例(全部进 tests/test_web_backup.py, docstring 测试计划同步), 终态全绿基线切片 26-11-15-1253(见 kb.baseline; 闸红快照 26-11-15-1226 为不可变测量快照保留)

- 2026-11-15 12:27 S5 收尾: webui.md 配置备份节+README 功能行+计划 Done(R1)+档案 S1-S5 翻转+范围外列报(存量 e2e 4 例/夹具不统一/覆盖率闸红)+坑档 2 件 4 条+基线切片; 零代码改动
