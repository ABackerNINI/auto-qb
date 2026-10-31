# 3769 passed + 10 skipped(根) —— WEBUI右键菜单文案统一:动词+灰色种子计数

> 摘要: WEBUI右键菜单文案统一:动词+灰色种子计数
> 基线时间: 2026-10-20 04:03

**Refs:** memory-bank/tasks/26-10-20-webui-menu-label-unify.md,memory-bank/plans/26-10-20-0145-plan-webui-menu-label-unify.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20362    391   6982    262    98%
3769 passed, 10 skipped in 35.56s
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件, 默认端口): `322 passed, 10 skipped (11.0m)`, 0 failed。
- 新增守阵 1 条电池段(注册表 node 电池第 ⑭ 段「动词族灰色后缀」): 四支 12 个动词项各带
  「N 个种子」后缀且其余项无后缀 + 分隔线项 note 恒空 —— 该段在 node 缺席时会静默跳过
  (与既有电池同约定), 本机 node 22.14 实跑。
- 红验(本轮): 改前 `trigger-scope` 等五 spec 按旧文案断言(批量启动/启动该种子/启动整组/
  停止整集…), 文案统一后必然红; 改挂 `data-kind`/`data-count`/`data-item` 后全绿。

## 本改动面

| 文件 | 改动 |
|---|---|
| `shared/ctx_menu.js` | 12 项(四支×启动/停止/删除)label 统一为动词; 新增 `note` 字段(`CTX_SEED_NOTE` = `ctxSeedCount() + " 个种子"`); `ctxRenderItem` 产出 `note`(分隔线项恒空串); 字段注释补 `note` |
| `shared/tpl/ctx-menus.html` | 容器绑 `:data-kind` / `:data-count`; 六处项渲染绑 `:data-item="it.id"` + `<span class="ctx-text">标签 <span class="ctx-note">后缀</span></span>`(含次级面板与「更多操作」父项); 头注补文案口径 |
| `shared/selection.js` | 新增 `_seedCountOf(keys, hashes)` —— 种子计数单点(组按成员闭包展开 + hashes 去重) |
| `shared/menu.js` | 新增 `_ctxScope()`(菜单态 → C1 锚点描述)、`ctxMenuKind()`(data-kind)、`ctxSeedCount()`(data-count/后缀) |
| `shared/commands.js` | `_actCore` 收掉 `what`/`countSuffix` 参数, 恒 `已执行: {动作}(N 个种子)` / `{动作}失败: …`; 四个调用点同步删参 |
| `shared/shows.js` | `actEpisode` 不再按整集/整剧传 toast 文案 |
| `atlas/console/prism css/components.css` | `.ctx-note` 并入 `.strip-note` 的同一条声明(11.5px + `--fg-muted`; atlas 已顶 700 行上限, 共用声明零增行) |
| `e2e/lib/gestures.mjs` | 新增 `ctxItemById()`(按 `data-item`)与 `ctxMenuScope()`(读 `data-kind`/`data-count`) |
| `e2e/trigger-scope/multiselect-shows/optimistic/menus/delta-sync` | scope 断言改挂容器属性 + 形态正则; 动词项点击改按 id; `pausableRow` 去掉文案参数 |
| `tests/test_webui_ctx_menu_registry.py` | ⑫ 段改口径(整集/整剧文案与 scope 无关、组删除不再出现辅种名词); 新增 ⑭ 段(动词族后缀); vm 桩补 `ctxSeedCount` |
| `memory-bank/conventions/webui.md` | 术语行「开始/暂停」→ 启动/停止(标退役); 新增「动作文案口径 = 动词 + 灰色种子数」约定 |

未触及: 强制重新汇报/重新检查/限速/移动/导出等无 scope 变体的项、「更多操作」状态开关族
(强制启动/超级做种/自动种子管理)、快捷键面板、删除确认框的标题与构成分解、`.strip-note` 既有语义。
