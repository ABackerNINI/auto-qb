# 2772 —— 流量图版式改基线(设置控件上提头部 + 图例并入统计栏)

> 摘要: 用户报「流量图被其它元素占用了高度, 主要信息(图本身)被压缩」。四条版式改: ①时间档位
> (13 档)与纵轴设置自正文上提到「qB流量图」头部标题栏; ②两处注释(正文工具条「qB 口径 · 程序
> 运行期间…」与图下行「…· 悬停查看详情」)全部移除; ③上行/下行图例并入统计栏(窗口 N 桶 之前);
> ④统计栏与状态栏间距减小(10px → 6px)。标题缩短为「qB流量图」。**只改经典 UI**, `shared/drawer_tpl/`
> 15 个变体零改动。相对上基线 26-10-08-0559(2772+4)passed **±0**(本轮只改断言口径, 未新增测试
> 函数), 覆盖率口径逐位持平。
> 档案: memory-bank/tasks/26-10-08-webui-qb-traffic-head-layout.md
> 基线时间: 2026-10-08 07:13

**Refs:** memory-bank/tasks/26-10-08-webui-qb-traffic-head-layout.md

## test.full 实测

- 分支: `develop`(工作树含本专题回写件)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2772 passed + 4 skipped, 0 failed, 34.76s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0559](26-10-08-0559-webui-qb-traffic-yaxis-annotation.md)
  (2772 passed + 4 skipped @ 48.44s, 同 16476 / 165 / 5694 / 149):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: **未新增测试函数** —— 本轮只**改写** `tests/test_webui_static_dom_panel.py` 里两条
  既有守阵的断言口径(旧「图例 hint 两处同步」退役; `.qb-tools` 落点断言从正文改为头部)与
  docstring 清单, 故 passed 逐位不变。4 skipped 仍为 Windows 侧 POSIX 专属存量。
- 旁证(非 pytest): 真浏览器 Chromium 1440x900 三皮肤目检 —— 头部 44px(未新增行)/ 图 266px
  (吃满余量)/ 统计栏贴面板底缘 / 页面零 pageerror / `.hist-legend` 计数 0 而 `.hs-leg` 计数 2。

## 本专题面要点(非 pytest)

- 控件落点单点: 时间档位 `.qb-tabs` 与纵轴 `.qb-tools` 在**流量形态头部** `.drawer-head` 内;
  正文只剩图 + 统计栏。三挂点(全局/分组/单种)共用同一段头部与正文。
- 头部版式: `.drawer-head:has(> .qb-tabs){flex-wrap: wrap}` + 档位/纵轴区 `flex: 0 0 auto` ——
  宽视口不换行(实测仍 44px), 窄视口换行而非挤出控件。
- 图例: 上行/下行并入 `.hist-summary` 首部(`.hs-leg`, 排「窗口 N 桶」之前); 独立 `.hist-legend`
  行已从本面板退场(popovers.html 历史流量弹层仍用, 属另一处)。
- 注释: 两处口径/悬停说明文案全移除(信息在悬停 tooltip 内给)。

## 对照判据(后续沿用)

- 以本切片(2772+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
