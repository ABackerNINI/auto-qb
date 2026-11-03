# 4944 passed, 10 skipped, 3 warnings in 179.14s (0:02:59); TOTAL 22830 stmts / 152 miss / 7760 branch / 135 partial / 99% —— 缺失站点导出/导入 tracker 合并 M5 全量测试基线

> 摘要: 缺失站点导出/导入 tracker 合并 M5 全量测试基线
> 基线时间: 2026-11-04 00:35
**Refs:**

## 验收数字

- 汇总行: `4944 passed, 10 skipped, 3 warnings in 179.14s (0:02:59)`
- 覆盖率 TOTAL: `22830 stmts / 152 miss / 7760 branch / 135 partial / 99%`
- 口径: `commands run test.full` 本机 Windows 实测(M1~M4 全部提交后的一次全量, 含生成物守卫); Linux (WSL) 侧未重测

## 本改动面

- `src/auto_qb/core/exporter.py`(M1): 新增缺失站点共现分组构件(`group_missing_domains` union-find 传递闭包 + `build_merged_entry`, 代表域名取最短字典序)
- `src/auto_qb/core/exporter.py` + `src/auto_qb/cli.py`(M2): `export_yaml_template` 默认合并共现缺失域名, `--split-trackers` 拆回逐域名条目; CLI 加配合校验(缺 `--export-yaml` 即 parser.error)
- `src/auto_qb/webui/server/routes/sites.py`(M3): `/api/sites/missing` 响应追加 `groups` 分组字段
- `src/auto_qb/webui/static/shared/config_hub_tracker.js` + `ui_feedback.js`(M4): 导入缺失站点三钮自适应引导(存在 ≥2 域名组才引导, 合并导入为默认)
- 本轮 M5 仅基线切片与文档回写, 无产品代码改动; 全量为上述改动后的 pytest 全量
