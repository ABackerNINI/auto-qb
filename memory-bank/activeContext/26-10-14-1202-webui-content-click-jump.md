# webui-content-click-jump — 内容页树表点击跳动: CSS 入场动画重播(四复查定案, 专题 Done)

> 摘要: 专题 webui-content-click-jump.
> 最后活动: 2026-10-14 14:01

## 正在进行

- 四复查「点击跳动, 持续 0.x 秒后回位」定案, 专题 Done.
- 根因(逐帧采样探针实锤): anchFill 每帧摘插锚 = 元素移除再插入
  = CSS 动画重启 ⇒ atlas/console 的 page-in(translateY(4px)+淡入,
  .22s)每次点击重渲整表瞬跳 4px 后缓回; prism 无该规则.
- 与三复查的 withScroll 是两条位移路径(滚动位现算 vs 动画位移),
  别互相顶罪; 桩内 scrollTop 本就无偏移.
- 修法: 两皮肤 views.css 抽屉作用域 animation:none(主列表表格
  随视图真重建才播, 不受影响).
- 量具元教训: 瞬态缺陷必须逐帧采样(rAF+4ms 双路), before/after
  比对式量具必然错过 —— 前三轮全绿的盲区即此.
- 验证: 守阵 #9 双皮肤绿 + 红验通过; test.full + e2e @fast
  全量绿, 数字见 kb.baseline(切片 26-10-14-1401).

## 下一步

- 无 —— 专题 Done, 已沉淀到档案 tasks/26-10-14-webui-content-click-jump.md.
- 若用户五复查仍报: 先问「持续多久回位/哪个皮肤」, 按坑档
  frame-swap-scroll-reset 两条路径分账; 85px 真机形态仍未入桩
  (布局/设备像素比等环境量), 需要时上真机录屏.
