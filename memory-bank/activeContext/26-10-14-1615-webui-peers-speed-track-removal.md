# webui-peers-speed-track-removal — 用户页速度数值下方多余暗色条: 行级微条 track 退役(专题 Done)

> 摘要: 专题 webui-peers-speed-track-removal.
> 最后活动: 2026-10-14 16:15

## 正在进行

- Done: 用户报「四卡仪表/五区分组表中上传/下载速度数值下方有多余的暗色条, 移除」—— 根cause = 行级速度微条 track(.dt07-spd/.dt08-spd .track, 全宽 3px --bg-sunken)里的填充 `<i>` 无任何 background(模板只置 inline width)⇒ 填充恒透明, track 即全宽暗色条不论速度; 用户所报的"多余暗色条"= 这条失填充形态, 不是设计元素.
- 修法按用户字「移除」: 整 track 退役 —— xtpl-cells.html 四速度格删 track span · 07/08 变体删 `.track` CSS 两规则 + 退役死字段 upBar/downBar 与 rowsFn maxUp/maxDown 满刻度求值(grep 无其它消费点)· 卡 1 tip 文案「与列表行内速度微条同色」引用摘.
- 保持: 速度数值文字方向色(--today-up/--today-down)不动; 卡 1 flowbar/dirbar/进度条(有 background 真渲染)不动; 变体 09 占用列条不动(用户只字 07/08).
- 验证: 真浏览器两变体速度格零 track + 两截图; e2e @fast 全绿; 静态守阵 targeted 绿; test.full 全绿(数字见 kb.baseline, 切片 26-10-14-1615).

## 下一步

- 无 —— 专题 Done, 已沉淀到档案 tasks/26-10-14-webui-peers-speed-track-removal.md.
