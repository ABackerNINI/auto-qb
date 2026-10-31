# 基线切片 26-10-04-0054 — 添加种子三下拉 label 闪烁第三轮修复(mousedown.prevent)

> 摘要: 用户报 a7ebbe14 未修住「点字段 label 稳定复现下拉闪烁」。真浏览器埋点定位: label 的
> mousedown 默认动作 blur 输入框, 40ms 失焦合帧定时器在人手按住期间(80~150ms)先收层, 松手回焦
> 重开 = 必闪。修法 = 四个字段 label `@mousedown.prevent`(根除 blur)。

- 时间: 2026-10-04 00:54 (GMT+8); 合并远端 30143bda 后于新基线重测
- 分支: develop @ (本轮回写件, 随主提交一并入库; 会话起点 sync 至 926d1f66 → 合并 30143bda)
- 命令: `commands run test.full`
- 实测: **2418 passed + 3 skipped, 32.03s, 覆盖率 99%** (Required coverage of 98% reached;
  合并远端抽屉动画 3c7df550 + issue 回写 30143bda 后重测, 较首测 2417 多 1 条为远端新守阵)
- 真浏览器走查(Playwright + scripts/ui_harness.py 桩后端, click delay=150ms 模拟人手按住):
  **三皮肤(atlas/prism/console) × (保存路径/分类/标签/meta分类) × 两场景 = 24/24 通过** ——
  菜单开着按住 150ms 点 label 零收层翻转(rAF 追踪 flips=[]), 关闭态点 label 正常开且焦点落位;
  根因侧: pre-fix delay=150 复现闪烁(open=false→true 相隔 116ms), post-fix 消失。
- 改动面:
  - `src/auto_qb/webui/static/shared/tpl/dialogs-mgr.html` — 三个字段 label 加 `@mousedown.prevent` + 注释改写真根因
  - `src/auto_qb/webui/static/shared/tpl/popovers.html` — meta 分类 label 同款
  - `src/auto_qb/webui/static/shared/add_torrent.js` — addPopBlurClose 注释修正(40ms 窗只兜瞬时焦点迁移, label blur 已由模板根除)
  - `tests/test_web.py` — 守阵第 1 组扩为双断言 + docstring/测试计划头改写
  - `memory-bank/pitfalls/web-ui/combobox-focusout-close.md` — 复发+1(第三轮条目 + 教训)
- 未验证面: 真机(真实 qB + 真实数据)走查仍待用户执行
