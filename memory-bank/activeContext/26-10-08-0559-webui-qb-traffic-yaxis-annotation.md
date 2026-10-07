# webui-qb-traffic-yaxis-annotation — 流量图纵轴固定模式 + 画布注解层

> 摘要: 用户命题「WEBUI 流量图添加纵轴最大值固定模式(可切换; [限速+20%] 或手动输入值; 峰值超出最大值按峰值显示; 覆盖全局流量 / 种子 / 辅种分组)」, 并一并认领 issue [26-10-07-0149](../issues/26-10-07-0149-feat-webui-traffic-chart-annotation-layer.html)(限速虚线/缺口斜纹注解层)。拍板: 限速一律取 **qB 全局限速**(三作用域同源) / 方向取**上下行较大者** / 手动值 **MiB/s** / 偏好**三作用域各自独立**; 注解层画在**共享图面**(三挂点全生效), 自动模式下**峰值超过限速才画**限速线。全部落地, 已闭环。
> 最后活动: 2026-10-08 05:59

**Refs:** memory-bank/tasks/26-10-08-webui-qb-traffic-yaxis-annotation.md,memory-bank/testing/baselines/26-10-08-0559-webui-qb-traffic-yaxis-annotation.md

- 任务档案: [26-10-08-webui-qb-traffic-yaxis-annotation](../tasks/26-10-08-webui-qb-traffic-yaxis-annotation.md) —— 拍板记录、坐标口径论证、子任务状态表与实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/qb_traffic_chart.js` 纵轴三态 `auto/limit/manual`(`_qbYCapOf` 上限派生 + `_qbYRange` 值域纯函数「上限只保底, 峰值超上限按峰值」)+ 画布注解层(`drawClear` 缺口斜纹 / `draw` 限速虚线, `_qbCanvasScale` 按 `uPlot.pxRatio` 换算设备像素)+ 三作用域独立持久化(`autoqb.ui.qbYAxis{Global,Torrent,Group}`)+ `mounted` `$watch` 限速变化重排; `state.js` 三字段; `shared/tpl/drawer.html` 控件(`.qb-tools`/`.qb-seg`/手动输入/上限读数); 三皮肤 `views.css` 成对。
- 关键判据(易被后人改坏): 限速线只画 `0 < 限速 < yMax` 的线(一条判据覆盖「固定模式恒画 / 自动模式超限速才画」两态, 不写模式分支); 缺口 = 上下行**皆** null; 切档/改值走 `setData` 重排(**不重建图、不重取数**)。
- 实测: test.full **2772 passed + 4 skipped / 0 failed / 48.44s / TOTAL 99%**(基线切片 [26-10-08-0559](../testing/baselines/26-10-08-0559-webui-qb-traffic-yaxis-annotation.md)); 旁证 `npm run test:e2e:fast` **8 passed**(含渲染健康无运行时错误) + 真浏览器注解钩子自检零 pageerror(带钩子比不带多 9,870 已绘制像素)。
- 取色面回写: `conventions/webui.md` 流量方向色族消费面补注画布注解层同源取色(限速线随方向 / 斜纹取 `grid`)。
- 关联: issue [26-10-07-0149](../issues/26-10-07-0149-feat-webui-traffic-chart-annotation-layer.html) 置 Done(认领链双向闭合); 同族未做的另两件备选(P-02 per-tracker 汇报倒计时 / P-05 14 变体解读栏联动)仍在 issues 池。
