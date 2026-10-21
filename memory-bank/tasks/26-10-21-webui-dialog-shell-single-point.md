# 26-10-21-webui-dialog-shell-single-point — 前端对话框外壳三段式收敛: aq-modal 单点(遮罩手势/标题头/动作栏 + 管理对话框合并 + 行式明细合并)

**Status:** In Progress
**Added:** 2026-10-21
**Updated:** 2026-10-21
**Summary:** 前端对话框外壳三段式收敛: aq-modal 单点(遮罩手势/标题头/动作栏 + 管理对话框合并 + 行式明细合并)
**Topics:** webui-dialog-shell-single-point
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-dialog-shell-template-dup.html, memory-bank/testing/baselines/26-10-21-1408-webui-dialog-shell-single-point.md, memory-bank/testing/baselines/26-10-21-1459-webui-dialog-shell-single-point.md

## 原始请求

1. 用户指派:「认领并修复 memory-bank/issues/26-10-20-2231-refactor-fe-dialog-shell-template-dup.html」——R23 前端模板重复代码审查(台账 `memory-bank/tasks/26-10-20-frontend-dup-code-audit.md` R23-A-02/A-03/A-08)入池的 refactor 便签: 对话框外壳三段式(遮罩关窗手势 10 处 / modal-title 头 11 处 / modal-actions 栏 11 处)逐字手抄, 管理对话框双胞胎(标签/分类)同构约 40 行, modal-details 行式键值两套; 建议抽 `<aq-modal>` 外壳一份 + 中部插槽, 管理对话框表驱动合并, 明细行合一并顺带修 `String(d.value || '')` 在 value===0 时不出复制钮的边界。

## 思考过程与决策

- **组件形态沿 aq-combo-input 同范式**(issue 26-10-20-2230 先例): `window.AQ_MODAL*_COMPONENT` 定义在 dialogs.js 尾(免新增 JS 分片与 scripts 清单行), 模板挂新分片 `tpl/dialog-shell.html`(x-template, into: body), app.js 注册。纯模板件: 数据一律 props, 行为经 `$root` 回调根实例(遮罩手势 maskDownSelf/maskCloseIfArmed 读根 `_maskArmed`, 见坑档 web-ui/component-ref-ownership)。
- **D1 两个组件而非一个**: `aq-modal-head`(标题头: 图标+标题+关闭钮)单独存在, 供无遮罩异形 speed-pop 直用; `aq-modal`(遮罩+.modal+head+body+actions)覆盖全部 10 个带遮罩对话框。三处异形吸收: hist 头插页签走 `#extra` 插槽、无 body 包裹(body-class 空=裸插槽)与无动作栏($slots.actions 条件渲染); kb-help 标题 h3 走 `#title` 插槽; speed-pop 用 aq-modal-head 直拼(根 .speed-pop 的定位/ref/@click.stop 是调用方关切)。
- **D2 关窗经 props 不写内联箭头**: `:close`(Function) + `:close-args`(Array, 通用确认框 `resolveModal`+`[false]`)——项目纪律 dialogs.js::closeHistory 注释「免得在模板里写内联箭头」。hist/kbHelp 的关闭钮从内联赋值统一到具名方法 closeHistory/closeKbHelp(语义等价)。
- **D3 管理对话框合并 = 单份模板 + mgrDef 数据表**(state.js 根 computed, 按「computed 不进 mixin」纪律): kind/图标/标题/loading/空态/行(名字+可选副列+行内动作闭包)/新建字段表/addDisabled/提示行全部表驱动; 新建草稿 3 个散根属性 mgrNewTags/mgrNewCatName/mgrNewCatPath 收成 `mgrNew` 对象(tags/catName/catPath)以支持 `v-model="mgrNew[f.key]"` 表驱动(保留 v-model 的 IME 组合期语义, 不改裸 :value+@input); 提交/回填经 mgrSubmitNew 单点分派。
- **D4 行式明细合并 = modalDetailRows 根 computed**(state.js): verdict 行(copy:false, key 'v'+i 保序)在前、details 行(copy:true, key=label)在后; 单一渲染块; 复制钮显形边界 `String(d.value || '')` → `String(d.value ?? '')`(0 不再被吞, null/undefined 仍不出钮)。
- **D5 shell 行数顶格消解**: prism/index.html 210 行贴上限——新分片不新增清单行, 追加到三份 shell 既有 `into: body` 行尾(JSON 空白不参与清单等价比对, 坑档 web-ui/frontend-split 腾行配方的等价手段)。
- **D6 `$slots` 进模板保留前缀白名单**: hist 无动作栏必须条件渲染 actions 包裹, `$slots.actions` 是 Vue 内建(组件实例真实存在), 按坑档既定路径加白名单并同步活性探针, 不用无前缀别名中转。

## 实现计划

1. 新分片 `tpl/dialog-shell.html`(tpl-aq-modal-head + tpl-aq-modal 两个 x-template) + 三份 index.html body 行追加 + app.js 注册两行。
2. dialogs.js 尾部两个组件定义(props 表, 零方法); state.js computed 加 mgrDef + modalDetailRows, data 的 mgrNewTags/mgrNewCatName/mgrNewCatPath 收成 mgrNew 对象; dialogs.js 管理对话框草稿读写/提交分派改 mgrNew.* 与 mgrSubmitNew。
3. 四个模板分片改写: dialogs-mgr(add/dirBrowse 走 aq-modal, 删分类管理块)、dialogs(stats 走 aq-modal, speed-pop 头换 aq-modal-head)、popovers(删标签管理块, 落合并版管理对话框; meta/confirm/hist/kbHelp 走 aq-modal; confirm 明细两块并一)、move-dialog(走 aq-modal, pop-open 并入 width-class)。
4. 守阵同轮改读取面不改口径: 遮罩成对手势守阵(单点化后扫组件模板+调用点清点)、verdict 渲染区断言、move/pop-open/cls 绑定断言、metaOpen/kbHelpOpen v-if 断言改 :open、冗余 tooltip 黑名单加 dialog-shell.html、保留前缀白名单加 $slots; 新增 `test_frontend_dialog_shell_single_point`(三段字面量只许在组件模板 + 调用点清点 + mgrDef/modalDetailRows 单点 + 复制钮 0 边界)。
5. 验证: node 语法检查(JS 片) → `commands run test.quick` 静态面先行 → 红验三类突变逐类判红 → `commands run test.full` + `commands run dev.e2e` 真浏览器 → 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 认领链与建档(issue In Progress + doc-refs 双向) | Done(2026-10-21) |
| S2 | dialog-shell 分片 + 三 shell 清单 + app.js 注册 + dialogs.js 组件定义 | Done(2026-10-21) |
| S3 | state.js(mgrDef/modalDetailRows/mgrNew) + dialogs.js 草稿改道 | Done(2026-10-21) |
| S4 | 四模板分片改写 + 管理对话框合并落位 | Done(2026-10-21) |
| S5 | 守阵改读取面 + 新增单点守阵 + 红验 | Done(2026-10-21) |
| S6 | test.quick → test.full → dev.e2e → 基线切片 | Done(2026-10-21) |
| S7 | 收尾回写(issue Done / 档案 / 坑档判定 / kb.index) | Done(2026-10-21) |

## 进度日志

### R0 · 立档 (2026-10-21)

- 用户指派认领修复; 锚点复验: 遮罩手势 10 处 / 标题头 11 处 / 关闭钮 9 处逐字同, 管理双胞胎与明细两套俱在——台账小差: modal-actions 实为 10 处(.issue 写 11), 修复时在 issue 报告里更正。
- 实施 S1-S7 全部完成, 详见切片与 issue 报告; 测试数字见基线切片(`commands run kb.baseline`)。

- 2026-10-21 14:10 修复落地: 三段式外壳收敛 aq-modal/aq-modal-head + 管理对话框 mgrDef 合并 + modalDetailRows 并一(复制钮 value===0 边界修复); 守阵单点化+红验三类; test.full 3978+2 全绿(基线切片 26-10-21-1408) + e2e 336+10 全绿; issue 置 Done
