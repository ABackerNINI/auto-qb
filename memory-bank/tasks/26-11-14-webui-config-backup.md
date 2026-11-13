# 26-11-14-webui-config-backup — WEBUI 配置导出/导入（配置备份 bundle）

**Status:** In Progress
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** WEBUI 配置导出/导入专题：计划 26-11-14-0624 入库（Open），S1-S5 待显式开工；grilling D1-D12 拍板
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
| S1 | 后端导出：GET /api/backup/export + mask_yaml_text 单点 + 金清单 | Open |
| S2 | 后端导入：POST /api/backup/import 全管线（掩码 resolve/readonly 回退/聚合校验/.bak/热重载） | Open |
| S3 | 前端：ui_prefs.js 双清单 + actbar 按钮 + 导出/导入流 | Open |
| S4 | 守阵：test_webui_static_ui_prefs.py（扫描+交叉+负例）+ e2e | Open |
| S5 | 收尾：文档回写 + test.full 基线 + 真机目检（用户） | Open |

## 进度日志

### R0 · 立档 (2026-11-14)

grilling 12 问拍板 D1-D12 + 三路只读取证 + 计划 26-11-14-0624 入库（Open）+ diff 预览入池 26-11-14-0625 + 本档案立档；零代码改动，kb.check 全绿（主键/认领链/回写守卫全过）；S1-S5 待显式开工。

- 2026-11-14 06:32 grilling 12 问拍板 D1-D12 + 三路只读取证 + 计划 26-11-14-0624 入库(Open, S1-S5 待显式开工) + diff 预览入池 26-11-14-0625 + 档案立档; 零代码改动
- 2026-11-14 06:4x 提交轮评审(分面 2 派遣): 送检 6 全过检(检 6/6), 5 minor+1 nit 当场全修(load_keys_doc 行号/PREF_EXCLUDED 补 drawerOpen+legacy v3/v4/旧版本迁移语义钉死/扫描前缀三形态口径/D6 引文忠实/未知键忽略层级); R1 复评送检 2 全过检(扫描口径撞 cookie/事件名+gtm.config 未知键例外)当场修; R2 复评零 actionable 出口; 全轮检 8/8 修 8 blocker 0
