# 7036 passed + 6 skipped —— 计划 26-11-23-1339 落地批后基线 —— 基础代廉价解析推断站点名 + site_provisional 临时态压暗 + 结算 full 翻假 + 真 no_site_conf

> 摘要: 计划 26-11-23-1339 落地批后基线 —— 基础代纯内存推断站点名 + site_provisional 临时态压暗 + 结算 full 翻假报真 no_site_conf; ≤2s 真机判据本轮未重采(见文内如实说明), 不预填实测数字。
> 基线时间: 2026-11-23 20:39
**Refs:** memory-bank/plans/26-11-23-1339-plan-webui-boot-first-site-provisional.html

## 验收数字

`commands run test.full` 实测: 7036 passed, 6 skipped, 覆盖率 99.53%(标题数字按惯例四舍五入)。新增用例来自 dfe254b2(S3 守阵)与 95bd22f6(缺口修复)两批。

## ≤2s 真机判据: 本轮未重采(如实说明)

本轮不重采 flat/singles/shows 首份数据 ≤2s 真机判据, 不虚报实测数字。理由:

1. 测试实例未起 —— real.* 轨道本轮一律不跑, 无真机数字可取。
2. 零 qB 调用计数桩已钉 —— b2ce154b 的基础代推断走 rec.tracker 纯内存解析, 不绑 conf、不调 qB, 首份数据关键路径零新增 qB 往返。
3. 三处改动均不在首份数据关键路径 —— S1 推断与透传、S2 前端 sa-provisional 压暗、S4 补全代 provisional 结算 full 翻假都不触及 flat/singles/shows 首份数据的发布时刻与管线节拍。
4. 既有 S3 余量 —— 0269 S3 三轮 flat/singles/shows ≤2s 已 PASS, 探测轮空窗 1.49s→0.050s 收缩为一拍; 余量 margin 足以覆盖本轮纯展示层与结算层改动, 故判定为「无需重采」而非「默认通过」。

若需本轮真机数字, 须在测试实例就绪后按 real.* 轨道重跑, 本切片不预填。

## 本改动面

- 四批本地提交: b2ce154b(S1 后端廉价解析 + 临时态透传), 5084d47e(S2 前端四皮肤 sa-provisional 压暗 + 行指纹纳新), dfe254b2(S3 守阵: 真未配二拍告警 / 备用自愈 / 四视图同源), 95bd22f6(缺口修复: 收尾补 full 结算翻 False + 真 no_site_conf)。
- `e2e/boot-first-two-hop.spec.mjs`: 两跳追加站点 chip 临时态视觉断言(基础代 sa-provisional 压暗 + 推断名 HHan + 无假 sa-no-conf; 补全代 provisional 翻假 + 真值保持 + 不误报), Playwright chromium 单文件实跑通过。
- `scripts/ui_harness.py`: boot-first 桩补 rec.tracker 注入(tracker 是快照扩展字段, 不在 FakeClient.sync_maindata 的字段表, 与单测 _inject_trackers 同款), 使已配域名种子在 e2e 下真钉推断名而非空跑。
- 文档回写: 计划 26-11-23-1339 翻 Done + R2; 0269 计划 R3; 任务档案 wrap 新专题切片; 新建 2 条坑档。
