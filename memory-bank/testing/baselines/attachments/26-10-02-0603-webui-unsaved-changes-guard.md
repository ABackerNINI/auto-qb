# 基线 · 2289 passed + 3 skipped / 99% —— 设置页未保存改动防护(U1-b: 自绘刷新框 + 原生兜底)

> 摘要: issue 26-09-25-1702 实施收官基线 —— 键盘刷新(F5 / Ctrl+R 族)走自绘三选一框(保存并刷新 / 放弃改动并刷新 / 留在此页), 其余真实导航靠原生 beforeunload 兜底(随 cfgDirty 挂摘), 刷新即清零不做草稿恢复; 静态守阵 +1(test_frontend_unsaved_changes_guard_wiring)。纯前端改动(JS/HTML/守阵), 产品代码无新增语句。
> 档案: [tasks/26-10-02-webui-unsaved-changes-guard.md](../../tasks/26-10-02-webui-unsaved-changes-guard.md)。
> 基线时间: 2026-10-02 06:03, develop @ 300f8aa5 + 本笔工作树(阈值 98 下 test.full 实测; 收尾回写未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2289 passed + 3 skipped / 99%**(13,357 语句 / 91 未覆盖 / 4,448 分支 / 86 partial,
test.full 47.7s, rc=0; test.quick 同 2289 passed + 3 skipped / 38.4s)。
相对上一条基线(26-10-02-0459: 2288 passed / 13,259 语句 / 88 未覆盖 / 4,448 分支 / 85 partial /
99.01%)**+1 passed**(新增守阵一条)、语句覆盖 13,171 → 13,266(+95, 分母 +98: 期间并入的远端提交带了新代码),
分支 partial 85 → 86(+1, 新守阵的分支), 综合口径仍 **99%**(远高于阈值 98)。
改动面: `config_editor.js`(守卫 + cfgSave 返回布尔)/ `ui_feedback.js` + `tpl/popovers.html`(三选一框第三钮)/
`lifecycle.js`(监听注册撤除)/ `state.js`(cfgDirty watcher)/ `tests/test_web.py`(+1 守阵 + 测试计划清单一行)。
未做: 报告 §8-4 的 chromium 实弹走查(本轮未起真浏览器)—— 键盘路径的实弹验证留给下次。
