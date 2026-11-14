# 26-11-14-webui-frozen-col-fx-stamp — fx 基线改写致固定列悬停竖带与 stamp 生命周期

**Status:** Done
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** 用户三报「新增种子固定列 hover 竖带」的根因 = fx.css [data-fx] 基线把被 stamp 行的行板过渡顶成 opacity/transform, D4-7 复位规则 + stamp 生命周期收口 + 三面守阵双红绿; 顺带放行 relocate :928 平台断言既有红(issue 26-11-14-1727)
**Topics:** webui-frozen-col-fx-stamp
**Refs:** memory-bank/pitfalls/web-ui/frozen-column.md,memory-bank/issues/26-11-14-1727-test-relocate-casefold-posix.html

## 本篇只回答

「flux 新增种子行(被 fx 差分 stamp 的行)悬停时固定列与其它列短暂异色」这一缺陷家族的第 N 次复发如何定位到 fx 基线改写这一新机理、修成什么形态、守阵怎么钉住两个独立面(级联复位 / stamp 摘除生命周期)。机制细节的单点沉淀在坑档 frozen-column.md, 本档案只留决策与验证链。

## 原始请求

1. 「WEBUI新增种子固定列hover进入时背景与其它列不一致, 约0.几秒恢复」
2. (环境三问后)行语言 flat / 浏览器 Chrome 系 / 皮肤 flux
3. 「顺手修」—— 授权修 stamp 永驻残留(H&R 裁高 / sticky 宿主改写)
4. 「既有红(Linux 平台分支)立 issue, commit」—— 入池 relocate 既有红 + 走完整收尾提交

## 思考过程与决策

- 定位路径: 静态核对(四皮肤首格镜像/过渡同源全在位, e2e pinned 全家 30 例绿)→ 真浏览器逐帧探针(flat 全皮肤/双浏览器/三视图/新行/更新中悬停全 0 差)→ 环境三问锁定 flux → fx 挂载层逐行读出 `data-fx="row-in"` stamp → 逐帧实测坐实(行板 transition 被 fx.css [data-fx] 基线换成 opacity/transform, background 不再过渡; 首格保留 160ms => 竖带)。**盲区机理**: 行插入差分「首轮只建缓存」= 页面加载即在的行不 stamp, 既有 e2e 探针全打初始行 => 全绿假象。
- D-拍板1: 修在 flux 挂载层(fx-mount.css 复位规则)而非改 fx.css 库基线的作用域 —— 库契约不动、单规则外科。
- D-拍板2: 两个独立面分开钉 —— CSS 级联复位(合成 stamp 段确定性测)与 JS 摘除生命周期(真 stamp 段测), 互不背书。
- D-拍板3: stampSeen 硬断言(评审轮 2 改定)—— 运行时 stamp 管线无其它行为守卫, 宁红勿假绿。
- D-拍板4(用户): stamp 永驻残留「顺手修」—— 实测行高覆写 --fx-row-h 防摘除跳变 + animationend 名/目标双守卫主路 + 280ms 兜底(spawnGhost 兜底同值, 其本身纯超时单路)。
- D-拍板5(用户指令推定): ship.gate 被 relocate :928 既有红硬卡死(闸门口径红必修完才 pack, 无逃生口), 按 issue 建议修法 A 当场修(:928 数据改大小写全同), issue 26-11-14-1727 同批翻 Done 留全案记录。

## 实现计划

无分步计划文档(单会话完成), 总体思路: 真浏览器取证 → 环境收敛 → 机理坐实 → 红绿双验 → 三面守阵 → 评审循环 → 收尾入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 真浏览器取证(探针全部 /tmp, 未入仓) + 环境三问收敛到 flux/flat/Chromium | Done(2026-11-14) |
| 2 | 机理坐实: fx.css [data-fx] 基线顶掉行板过渡(逐帧 RED 29/255) | Done(2026-11-14) |
| 3 | fx-mount.css D4-7 行板过渡复位规则 | Done(2026-11-14) |
| 4 | fx-mount.js stamp 生命周期(实测行高 + 摘除双路) | Done(2026-11-14) |
| 5 | 守阵三面(e2e 两段式用例 / parity 钉5 / fx_wiring 生命周期钉 / r4 电池真跑) | Done(2026-11-14) |
| 6 | 评审 3 轮(派发 2: 正确性/测试守卫面)零 actionable 出口 | Done(2026-11-14) |
| 7 | relocate :928 既有红修复 + issue 26-11-14-1727 入池翻 Done | Done(2026-11-14) |
| 8 | 收尾回写(坑档 frozen-column 第9条复发与反向形态 + 基线切片) | Done(2026-11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

- 用户报障三入复现盲区(flat+flux+Chromium 全是既有守阵绿面), 真浏览器逐帧探针排除 flat 全部面后按皮肤收敛, fx 挂载层读出 row-in stamp 机理, RED 29/255 坐实。
- 修复两件: D4-7 复位规则(级联面) + stamp 生命周期收口(用户顺手修授权); 守阵四面落位, 红绿双验各自独立(单撤 JS=生命周期红, 单撤 CSS=缺陷面红 29/255)。
- 评审: 派发 2(正确性/测试守卫面), 六轮累计送检 16 发现, 10 过检全修, 6 修后补检 refute(引文指向修前状态), 轮 6 零 actionable —— 轮 2 起为修复循环复评(守阵 docstring 同步 / e2e 采样序与 :hover 硬断言 / stampSeen 正向面 / 措辞准确化 / 坑档计数同步), 修复增量全部过审。
- ship.gate 被 relocate :928 既有红卡死, 用户「立 issue, commit」指令下按建议修法 A 放行, issue 26-11-14-1727 同批 Done。
- 真机轨判定: 纯观感面(CSS/JS 悬停高亮), 桩数据不失真结论(真浏览器逐帧采样即真机级验证), 不入真机轨准入, 理由记此。
- 测试全绿(见 kb.baseline); 全案机制沉淀坑档 frozen-column.md 第9条(复发+1, 反向形态)。
