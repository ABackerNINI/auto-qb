# 窗口化表格 e2e 选靶行必须取自已渲染 DOM 的顶部稳定区

> 摘要: 行窗口化(rowWin, ROW_WIN_MIN=200)下给 locator 选点击目标, 不能拿 vm 数据序的行当靶 —— vm.groups 是服务端插入序(added_on 升序), 组视图按最近添加降序渲染, 插入序首组排最末、恰在窗外不渲染(点击等元素 30s 超时, 默认档 150 组 < 阈值不开窗所以不触发); 也不能取「已渲染集合里插入序第一个」—— 那是窗口尾缘行, 行高实测收敛推 _rowHVer++ 重算收窄后离场(挑选时在场、点击时已消失)。唯一稳定区 = DOM 序最前的顶部行(滚动顶部窗口 start 恒钳 0, 任何窗口状态下都在场)。
> 触发: e2e/冒烟在大库档(E2E_TORRENTS=3000 矩阵轮等)点组行/种子行超时; 给窗口化表格写「挑一行来点」的 arrange; 修完可达性后仍偶发点击超时(尾缘行竞速)。

**机理**(2026-11-13 实证, 锚 `e2e/group-hash-ref.spec.mjs` test4 + issue 26-11-13-0130): `_rowWindow`(columns_grid.js)按滚动位置切片, `app.js` ROW_WIN_*=MIN 200/OVERSCAN 10/EST_MIN 200/EST_H(group 44); 首访 n>=EST_MIN 直接按 EST_H 估算开窗(@3000 档 200 组首包即 active/start=0/end 约 27), 行高逐行实测落定(实测均值 47.46px)即重算收窄(end 22) —— 尾缘约 5 行在这拍离场; `_winViewH` 在 mounted 首句即设, 稳态流不存在「先全量再收窗」的阶段。滚动/resize 监听在 lifecycle.js mounted 注册, rAF 合帧写 `_winScrollY` 在 columns_grid.js `_onWinScroll`, resize 路径 `_onWinResize` 直写 `_winViewH`/`_winScrollY` 不经 rAF —— 本类用例无滚动, 三者全不触发。

**判别**: 点击超时先解码等的那串 data-key(base64, 形如 `["R:\Downloads\Set000", []]`)对回插入序位次; 再用离线探针采样 `document.querySelectorAll('.group-row[data-table="group"][data-key]')` 的数量/首末 key + `vm.groupWin`(active/start/end) + `vm.groups.length` —— 目标 key 不在任何采样集 = 渲染可达性问题, 不是功能缺陷; 别急着改产品代码。

**处置**: ①选靶遍历**已渲染 DOM 行键**反查 vm 数据(业务前提过滤如「含非暂停成员」照旧), 取 **DOM 序最前**命中 —— 已渲染集合的唯一真值在 DOM; ②**不在 vm 侧复算窗口边界**(前缀和/视口几何再算一份 = 第二份窗口实现, 漂移即假红); ③**不用滚动检索找行**(滚动循环是负载型 flake 面, 对照 26-11-11 f43e71af 防竞态先例); ④红绿双验按档各跑: 机制红验(还原旧挑组 + `--grep` 定向)= 2 failed, 绿验 = 定向 2 passed + 全 spec `--repeat-each 3` 矩阵轮 24 passed + 默认档 8 passed。
