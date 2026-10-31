# TOTAL                                                20719      73   7012      89    99% —— 3978 passed + 2 skipped —— 对话框外壳三段式收敛(aq-modal 单点)后全量基线

> 摘要: 3978 passed + 2 skipped —— 对话框外壳三段式收敛(aq-modal 单点)后全量基线
> 基线时间: 2026-10-21 14:08
**Refs:** memory-bank/tasks/26-10-21-webui-dialog-shell-single-point.md, memory-bank/pitfalls/kb/artifact-secret-write-guard.md

## 验收数字

```text
TOTAL                                                20719      73   7012      89    99%
3978 passed, 2 skipped in 146.27s (0:02:26)
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛 99%, 实测 99.41%); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- 真浏览器 e2e 同轮全绿: **336 passed + 10 skipped / 0 failed**(9.9m, dev.e2e 全量集, chromium 双皮肤)。
- 红验三类突变逐类判红后还原(test.one 定向): ①dialogs.html 手抄标题头回潮 → 字面量 census 红; ②复制钮边界 `??` 退回 `||` → 边界断言红; ③mgrDef 分类分支键名打错 → 数据表针脚红; 还原后定向回绿。
- 基线树 = 远端 2ae6a15f 快进后 + 本修复全部改动在工作树未入库状态; 测的就是这个组合。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

生产(src/auto_qb/webui/static/):

- `shared/tpl/dialog-shell.html`(新分片, into: body): `<aq-modal>`(遮罩+.modal+标题头+中部+动作栏)与 `<aq-modal-head>`(标题头五段)两份 x-template —— 三段式外壳(遮罩手势对 10 / 标题头 11 / 动作栏 10)只此一份; 差异参数化(mask-class/width-class/body-class/icon-class/label/x/close/close-args) + 插槽(title/head-extra/actions)。
- `shared/dialogs.js`: 尾部两个组件定义(props 表, 零方法, 行为经 $root 回调根实例); 管理对话框草稿收成 `mgrNew.{tags,catName,catPath}` + `mgrSubmitNew()` 分派单点。
- `shared/state.js`: 根 computed `mgrDef`(管理对话框两态数据表: 图标/标题/文案/行/字段/提示全表驱动)与 `modalDetailRows`(verdict 行 copy=false 在前 + details 行 copy=true 在后, 单一行表); data 三个散草稿属性收成 mgrNew 对象。
- `shared/app.js`: 注册 aq-modal / aq-modal-head 两组件。
- 四模板分片换壳: dialogs-mgr.html(add/dirBrowse 走 aq-modal, 分类管理块整体迁出)、dialogs.html(stats 走 aq-modal, speed-pop 头换 aq-modal-head)、popovers.html(合并版管理对话框落位; meta/confirm/hist/kbHelp 走 aq-modal; verdict+details 两套明细并一, 复制钮显形边界 `String(d.value || '')` → `String(d.value ?? '')` 修 value===0 不出钮)、move-dialog.html(走 aq-modal, pop-open 动态类并入 width-class 数组)。
- 三份 index.html: 分片清单在既有 `into: body` 行尾追加 dialog-shell.html(prism 210 行顶格, 零增行)。

守阵(tests/):

- `test_webui_static_dom_panel.py`: 新增 `test_frontend_dialog_shell_single_point`(字面量 census + 调用点清点 + mgrDef/modalDetailRows 单点 + 复制钮边界); 遮罩手势守阵改「组件模板一处手势对 + 调用点 :close 清点」; verdict 渲染区、moveOpen/pop-open/cls 绑定、metaOpen 断言按新读取面同轮改写(口径不变); tooltip 黑名单加 dialog-shell.html。
- `test_webui_static_dom_page.py`: 模板保留前缀白名单加 `$slots`(Vue 内建, hist 无动作栏条件渲染所需) + 活性探针同步。
- `test_web_shortcuts.py`: kbHelp 浮层模板针脚 v-if → :open(同轮改读取面)。

知识库: 任务档案 26-10-21-webui-dialog-shell-single-point.md + 坑档 pitfalls/kb/artifact-secret-write-guard.md(写入守卫整文件扫描误判的处置路径) + 本切片。
