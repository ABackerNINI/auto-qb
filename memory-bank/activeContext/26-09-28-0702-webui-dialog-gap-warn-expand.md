# WEBUI 弹窗按钮排间隙 + 跳检警告塌缩展开

> 摘要: 用户报「标签弹层『完成』与添加种子『取消/添加』与上文间隙太小」+「跳检警告留空突兀, 改为勾选时动画展开」。三套皮肤 `.modal-actions` 统一 margin-top 16px(margin 折叠不叠加); 警告行从 FX-21「常驻占位」反转成塌缩/展开(max-height+margin+opacity 过渡 0.22s, 零占位, 下方内容平滑下移)。根因/量测详见 tasks/26-09-28-webui-dialog-gap-warn-expand.md 与基线 26-09-28-0702; 量测假象坑条入 pitfalls/web-ui/dialog-measure.md。
> 最后活动: 2026-09-28 07:02

## 已完成

- 三套皮肤(atlas/prism/console) `.modal-actions` +`margin-top: 16px` —— 修 `.mgr-hint`/`.add-dialog-body` 与按钮排贴死; margin 折叠取最大, 对已有 18px 的确认框零影响。
- 跳检警告行三套 CSS 重写: 塌缩态(max-height/margin-top/opacity 全零 + overflow hidden) ↔ 展开态(max-height 4.5em + margin-top 7px), 过渡 0.22s; 节点仍常驻(高度过渡量真实文本), 模板零改动仅 FX-21 注释改口径。
- 验证: 全量冒烟 96 项(2 失败为既有「列设置·隐藏列宽度保留」, 干净 HEAD 复现同红); 专项 Playwright 三套 UI 量测全绿(塌缩 0px/展开 17-18px/收回 0px, 下方内容下移 25-30px, 间隙 16px); test.full 稳态 1817 passed / 3 skipped / 91%。
- 收尾回写: 档案 tasks/26-09-28-webui-dialog-gap-warn-expand.md + 基线 26-09-28-0702 + 新坑 web-ui/dialog-measure.md + smoke.md 端口坑复发 +1; 蒸馏掉已提交沉淀的切片 26-09-28-0041(主题 e897870 已入库)腾回上限位。

## 正在进行

- (无 —— 等用户下一条反馈)
