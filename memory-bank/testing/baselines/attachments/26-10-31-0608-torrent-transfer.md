# 4288 passed + 10 skipped —— 种子转移到其它下载器 T1-T8 收尾全量基线

> 摘要: 种子转移到其它下载器 T1-T8 收尾全量基线
> 基线时间: 2026-10-31 06:08
**Refs:** memory-bank/plans/26-10-31-0306-plan-torrent-transfer.html

## 验收数字

`commands run test.full` 实测(2026-10-31 06:08, HEAD = f999092f, 分支 feat/torrent-transfer):

- 汇总行: `4288 passed, 10 skipped in 79.39s (0:01:19)`
- 覆盖率 TOTAL: `21548 stmts, 163 miss, 7400 branch, 126 partial, 99%`(99.0% 门槛判定通过, rc=0)

## 本改动面

- 新模块 `src/auto_qb/transfer/`(`__init__` / `orchestrator.py` / `adapters/`: base 协议 + qb 实现 + tr stub, 978 行含 API 路由) —— T2/T3: 状态门 / 导出 / 字段映射 / 路径映射 / 跳检自动降级 / 验证轮询 / 删源与失败分类。
- 配置层 T1: `config.web.transfer`(`targets[]` per-target 字段集 / after_state / skip_check / path_map)+ `validate_config` / `config/schema.py` 同步 + `memory-bank/config-reference/keys.md` 补键。
- API 层 T3: `webui/server/routes/transfer.py`(`POST /api/transfer/run` + `/test`)。
- T4/T4.5: 设置页「WebUI」卡目标编辑器 + targets 密码掩码下钻修复(mask/unmask 按 name 配对, 堵 GET /api/config 明文外送)。
- 前端 T5/T6: 四支右键菜单「转移到」submenu + 确认弹窗四段式(预检/明细/执行/结算)。
- T7: 全程 test.quick 绿; T8: 本切片 test.full 全量基线。
- 真机验收(真实双 qB 手工转移核对)不在本轮, 留待用户。
