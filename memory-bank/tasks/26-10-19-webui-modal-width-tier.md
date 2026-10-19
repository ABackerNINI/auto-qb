# 26-10-19-webui-modal-width-tier — 重命名弹窗加宽 860: modal 宽度档位修(cls 选项 + 三皮肤), 长种子名零裁剪

**Status:** Done
**Added:** 2026-10-19
**Updated:** 2026-10-19
**Summary:** 重命名弹窗加宽 860 落地: 通用 modal 增 cls 附加类选项 + `.modal.rename-dialog` 走 --modal-w-add 三皮肤成对, 97 字符真实长名零裁剪(旧态裁 223px); 静态 + e2e 双守阵(各自红验), 全量三档验证全绿(数字见基线切片 26-10-19-2256), 零回归
**Topics:** webui-modal-width-tier
**Refs:** memory-bank/pitfalls/web-ui/modal-width-tier.md, memory-bank/testing/baselines/26-10-19-2256-webui-modal-width-tier.md

## 原始请求

1. 「修改：WEBUI重命名弹窗太小」(2026-10-19 22:2x) —— 承接同日 22:07 已修的「设定位置弹窗太小」同族报障。

## 思考过程与决策

- 定位: 重命名走通用 `_openModal`(popovers.html 单例模态), 未传任何宽度修饰 ⇒ 骑 `.modal` 基档 `--modal-w-base` 520px(该档原话「标准: 确认框 / 输入框」, 为提示类对话框设计)。编辑类对话框字段值 = 完整种子显示名(真实 80~120 字符), 与基档的内容前提错配。
- 复验先行(临时几何探针, 1440x900 双皮肤): 对话框 520x226, 输入框 474px, 注入 97 字符真实长名后 `scrollWidth 695 > clientWidth 472` ⇒ 裁 223px; 桩名 43 字符恰好不裁 ⇒ 既有冒烟从未暴露。**桩数据不暴露 ≠ 没缺陷**, 几何守阵必须注入真实感长名。
- 宽度档位表(三皮肤 tokens/style.css 同值): narrow 460 / base 520 / form 560 / add 860 / wide 920。拍板走 **--modal-w-add 860**(与添加种子/设定位置同档; 同一右键菜单里相邻的编辑对话框同宽), 不新造变量(档位表是跨对话框语义层, 新一档要改全部注释与文档)。
- 挂法拍板: 不为单对话框复制模板, 给通用 modal 加 **cls 附加类选项**(ui_feedback.js `_modalInit` 单点声明 + popovers.html 类绑定并入 + 调用方传 `cls: "rename-dialog"`)—— 空 = 既有对话框零变化, 且成为后续同类需求的正当出口。不用既有的 `wide`(那是 920 删除确认档, 语义会脏)。

## 实现计划

1. 复验: 临时探针量旧态几何(红) → 修复后同探针量新态(绿) → 探针删除;
2. 修法四件: `_modalInit` cls 字段 + popovers.html 类绑定 + editRename 传类 + 三皮肤 CSS 宽档;
3. 双守阵: 静态四锚(cls 字段/绑定/传类/三皮肤规则) + e2e 双皮肤(860 + 长名零裁剪 + 取消零提交), 各自红验;
4. 全量验证 + 知识库回写(新坑档 modal-width-tier + 档案 + 基线切片)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 探针复验 + 修复(四件: cls 选项/模板绑定/传类/三皮肤 CSS) | Done (2026-10-19) |
| 2 | 静态守阵 test_frontend_rename_dialog_width_wiring(四锚, 红验 ×2) | Done (2026-10-19) |
| 3 | e2e rename-dialog-fit.spec.mjs 双皮肤(三断言各自红验) | Done (2026-10-19) |
| 4 | 全量验证: 静态 / e2e fast / 全量 e2e 三档全绿(逐档数字与零回归账见基线切片) | Done (2026-10-19) |
| 5 | 知识库: 新坑档 modal-width-tier + 基线切片 2256 + 本档案 | Done (2026-10-19) |

## 进度日志

### R0 · 立档 (2026-10-19)

用户报「WEBUI重命名弹窗太小」。定位 = 通用 modal 基档 520 与「字段值是长文本」的编辑形态错配; 探针实测 97 字符长名裁 223px(桩名不裁, 冒烟失明)。修法 = cls 附加类选项 + `.modal.rename-dialog` 走 `--modal-w-add` 860(与设定位置/添加种子同档), 四件成对(ui_feedback/popovers/drawer/三皮肤 CSS)。修复后实测: 对话框 860x226, 输入框 814px, 97 字符长名零裁剪。双守阵 + 各自红验(回退 CSS: 宽度 860→520、输入框 814→474、裁剪 0→223 逐个判红)。验证: 全量三档(静态守阵 / e2e fast / 全量 e2e)全绿, 逐档数字与零回归账誊在基线切片 26-10-19-2256(见 kb.baseline)。坑档新立 `pitfalls/web-ui/modal-width-tier.md`(含档位表 + 桩数据不暴露教训 + cls 出口)。
