# 5479 passed + 10 skipped(根) —— kb.nav 关系图落地后全量

> 摘要: kb.nav 抽屉关系图 (局部环/关联泳道/全库) + 认领链五态解析落地后的全量基线
> 基线时间: 2026-11-07 03:39

## 验收数字

`commands run test.full` (2026-11-07 03:39 实测):

```text
TOTAL                                                24538     74   8396    41    99%
Required test coverage of 99.5% reached. Total coverage: 99.63%
5479 passed, 10 skipped, 1 warning in 138.69s (0:02:18)
```

相对上一版基线 +2 例 (新增 5 条导航守卫: 五态解析 / 围栏 / 反向边 / 组件零依赖 / 档位不被轮询洗, 其中部分与被替换用例相抵)。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_data.py`: `collect_nav()` 增 `items[].targets` (ok/ext/repo/basename/dead 五态) 与顶层 `ext` (库外件反向边); 判据对齐 `check_claim_chain` (仓库根相对 + 仅 baselines 前缀走归档回退) + 路径围栏 (`_inside` / `_denied`, 穿越路径与 `config.yml` / `auto-qb-data/` 一律判死)。
- `.agents/skills/memory-bank/scripts/nav_graph.js` (新): 关系图组件, 局部同心环 / 族泳道团级图, 零依赖手写 SVG, 只暴露 `window.MBGraph`。
- `.agents/skills/memory-bank/scripts/nav_server.py`: `GET /nav_graph.js` 路由; `gen_static` 内联组件成单文件 + 链接前缀按 `out_dir` 现算 (跨盘退 file:// 绝对前缀)。
- `.agents/skills/memory-bank/scripts/nav_page.html`: 抽屉 `#dGraph` 挂载 + 全屏层 `#gStage` 三档 + 节点下钻 + 档位存 `S.graph` 抗轮询重挂; 认领链/反向引用列表改五态渲染。
- `tests/test_kb_nav_data.py` / `test_kb_nav_shell.py` / `test_kb_nav_server.py`: 五态解析 / 围栏 / 反向边 / 组件零依赖 / 静态件单文件 / 档位不被轮询洗, 共 6 条守卫。
- `memory-bank/README.md` / `conventions/doc-forms.md`: 导航页口径回写 (五态 + 判据对齐说明)。
