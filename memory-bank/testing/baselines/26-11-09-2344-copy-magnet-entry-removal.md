# 5876 —— 复制 magnet 入口移除批全量绿

> 摘要: issue 26-11-09-0639 三处复制 magnet 入口移除批实测: 5876 passed, 2 skipped (113.50s), 覆盖率 99% (26153 stmts / 41 miss)
> 基线时间: 2026-11-09 23:44
**Refs:** memory-bank/issues/26-11-09-0639-bug-webui-copy-magnet-masked-degrade.html

## 验收数字

```text
TOTAL                                                26153     41   9102     53    99%
5876 passed, 2 skipped in 113.50s (0:01:53)
```

(实测时点: HEAD 77b649fc + 本批工作树改动, `commands run test.full` 2026-11-09 23:44)

## 本改动面

- **移除三处复制 magnet 入口**(issue 26-11-09-0639, 用户拍板候选①): `ctx_menu.js` copy-magnet 菜单项、`shortcuts.js` Shift+KeyG 快捷键、`drawer_tpl/02-general-cards-low.js` 与 `03-general-dossier-collapsed.js` 的 magnet 标识行 + `act === "magnet"` handler。
- `drawer_files.js` `copyTorrentInfo` 收窄为 name/hash 两用(去 magnet 分支/`_editDetail` 按需取数/async)。
- 过时注释同步: `decorate.js` / `drawer_templates.js` / `commands_send.js` / `views_row.py` / `record.py` / 两模板头部(评审 2 轮, 终轮零 actionable)。
- 守阵同步: `test_webui_ctx_menu_registry.py`(EXPECT 次级序去 copy-magnet, 计数 11→10)、`test_webui_static_dom_panel_misc.py`(复制族三项改两项 + 活项零回潮断言)、`helpers.py` docstring。
- 生产 `config.yml` 存量 copy-magnet id 不动(红线), `ctxMergeLayout` 未知 id 忽略口径兜住。
