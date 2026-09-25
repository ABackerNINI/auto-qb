# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1607 collected: 1606 passed + 1 skipped / Windows** —— 2026-09-25 **HR 删除安全档位 WEB UI 呈现落地**
(计划 [26-09-25-1823-plan-webui-hr-safety-display](../plans/26-09-25-1823-plan-webui-hr-safety-display.html),
档案 `26-09-25-webui-hr-safety-display`)。**+4 条**: `test_hr_resolve.py` safety_display 三档位派生 3 条
(站点档位即结论 A/C 不能删·B 可删且来源记「在线」/ 身份层放行·超龄豁免恒可删与 mode=all·新鲜度闸门落
「策略」桶 / judged None 回落本地兜底) + `test_web.py::test_frontend_hr_safety_wiring` 前端接线守阵
(hr.js token 映射表与后端 `SRC_*` 常量逐字一致 / 做种时长列两套 UI 各 3 处换绑 hrDurClass·hrSrcBadge·
hrDurTitle / 新样式两套 CSS 成对 / js 引用的 `m.hr_*` 字段 ⊆ `_hr_view_fields` 键集); 另把
`test_hr_view_fields_three_state` 扩到新三字段(站点档位 A/B/C 与本地兜底路径各一)并让
`_scan_filter_facets` 同查 `hrSrcOptions`。落地面: 后端 `hr/resolve.py::safety_display` 删除安全档位 ×
来源档位派生单点 + `views.py::_hr_view_fields` 透出 `hr_safety`/`hr_safety_text`/`hr_safety_src`
(**退役二值 `hr_satisfied_src`**); 前端做种时长列按安全档位着色(站点结论优先于本地)+ 来源 2 字徽标 +
悬停全文、删除确认框 HR 风险点名行、H&R 筛选两档→四档 + HR 来源副筛选、批量条「含 N 个不能删」。
TOTAL **91%**(10991 语句 / 791 未覆盖 / 3612 分支 / 327 partial; `hr/resolve.py` 98% / `webui/views.py` 97%);
双 UI 浏览器冒烟 **94 项全过 0 失败**(桩服务 1500 种子)。
**上一态 2026-09-25 HR v3.0 达标判定来源优先级: 1602 collected: 1601 passed + 1 skipped**
(+2 守阵 `test_hr_resolve.py`: `test_lane_verdict_ignores_remain_and_local` —— A 档命中即未达标, 剩余达标时间
归零/缺失都不改结论(退出达标推导); `test_judge_record_double_hit_prefers_lane_order` —— hybrid 双命中按
档位序 A>B>C 取, 与键序无关; 连同改写的 `test_judge_record_carries_site_satisfied_verdict` 共 **3 条红验全红**
后还原)。落地面: `hr/model.py::satisfied_verdict` 改**档位即结论**(A 考察中/C 未达标 ⇒ False, B ⇒ True;
删「A/D 档看剩余达标时间归零⇒已达标」推导 —— v2.8 实证该字段是考核窗口倒计时, 方向相反 —— 与缺字段
回落本地) + `hr/resolve.py::judge_record` 双命中档位序; 动机见计划 v3.0 §9/§12/§14 与档案
`26-09-22-backend-partial-hr-verify`。
**上一态 2026-09-25 两线合一: 1601 collected: 1600 passed + 1 skipped** —— HR 超龄豁免(develop)并入 GBK 修复/搜索分隔符(master)
(HR 线 **+17 条(1579 → 1596)**: 判定收口超龄豁免 7 条(`test_hr_resolve.py`)+ 取数侧行过滤与翻页早停 8 条
(`test_hr_service.py`)+ 门面透传 1 条(`test_hr_runtime.py`)+ 配置解析与取值范围 1 条(`test_hr_config.py`);
新键 `trackers.<站>.hr_check.completed_age_limit`(0=关闭, 默认不变), 动机与取舍见档案
`26-09-22-backend-partial-hr-verify` 与计划 v2.8。master 线 **+2 条(1579 → 1581)**: GBK 防回潮守阵
`test_local_codepage_ignores_utf8_mode` 1 条(引擎码页回退改问系统 ANSI 码页, 本会话 `PYTHONUTF8=1`
下已全绿, 见 [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md))+ 搜索分隔符回归守阵 1 条
(`test_search_torrents_separator_normalized` —— 空格查询词命中点/下划线/连字符分隔的种子名与文件名;
views.py 归一口径 `_search_norm`)。两线增量明细见 [baseline-history.md](baseline-history.md)。)
**同日 DND-01 拖拽添加种子 +1 守阵**(`test_frontend_add_torrent_drag_drop_wiring`, 全局拖拽接线四点:
事件对称/drop 必 preventDefault/判据不放宽 text/plain/双 UI 遮罩成对 —— 1597 → 1598, 见切片
`26-09-25-0848-webui-dnd-add-torrent`);
**同日右键次级菜单 +1 守阵**(`test_web.py::test_frontend_ctx_submenu_single_entry_and_hover_close`,
钉住「一级只有一个「更多操作」入口 / 移出父项延迟收起 / hover 图标规则限直接子级且压特异性」——
1598 → **1599**, 见切片 `26-09-24-2310-webui-ctx-submenu` 与档案 `26-09-24-webui-ctx-submenu`);
**同日 UI 位置持久化 +1 守阵**(`test_web.py::test_frontend_page_location_persisted` —— 顶层 `page` 与设置分区
`hub.view` 落盘 + 读侧白名单 + **启动补一次 `cfgLoad`** + 分区 key 对 schema 校验, 用户报"设置页刷新会回到种子页" ——
1599 → **1600**, 见切片 `26-09-25-1655-webui-page-location-persist` 与档案 `26-09-25-webui-page-location-persist`)。
TOTAL **91%**(10950 语句 / 791 未覆盖 / 3594 分支 / 326 partial —— 并行采样; **HR 包 93%**:
2814 / 147 / 774 / 93), sidefx 台账并行汇总 / **越界 0**。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-25 HR v3.0 达标来源优先级)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **18.6 / 18.1s**(2 次采样, 全部 test.full)

**上一态(2026-09-25 两线合一)**: 并行 20.5 / 18.8s(2 次采样, 全部 test.full, 合并态)。

**更早(2026-09-25 HR 超龄豁免)**: 并行 19.9 / 36.8s(2 次采样; 后者为同机其它 clone 并行工作时的负载离群, 前者为常态)。

**更早(2026-09-25 搜索分隔符归一)**: 并行 17.0 / 17.9s(热采 2 次; 另有首跑冷缓存 37.6s 不计入, 全部 test.full)。

**更早(2026-09-25 GBK 回退修复)**: 并行 14.3 / 20.9 / 21.2s(3 次采样, 全部 test.full)。

**更早(2026-09-25 扩展运行日志)**: 并行 17.6 / 19.8 / 19.9 / 20.5s(test.quick ×1 + test.full ×3)。

**更早(2026-09-25 禁令解除回写, 两线合一前的旧基线)**: 并行 19.5 / 18.5s(2 次采样; 2 failed 为当时已记载的 GBK 假红, 已随 a760da0 修复)。

**更早(2026-09-25 v2.8 明细表改版)**: 并行 18.3 / 18.7 / 19.1s(test.quick ×1 + test.full ×2)。

**更早(2026-09-25 v2.6/v2.7 通道时序 + 增量落盘 / M4 多站点)**: 并行 19.3 / 20.0 / 21.7s 与 18.1 / 18.1 / 19.2s。
⚠ 扩展守阵真跑 node(现为一次运行覆盖四个场景 + 登录页场景各一次) ⇒ 耗时比 M1 末态高约 5s, 属预期的环境成本。

⚠ M2 用例含真回环 socket、线程启停与「等扩展回传」场景 ⇒ 整体比 M1 末态(~9s)慢约一倍;
其中一处 10s 级浪费是**真缺陷**(关停时线程正阻塞等扩展回传, 白等到 `request_timeout`)——
已修为「先叫停队列再 join」, 并有 `test_stop_is_prompt_while_waiting_for_extension` 守死。

**上一态(2026-09-24 告警分档 + `--hr-status`)**: 并行 16.88–21.40s / 串行 30.93s。

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: **当前**并行 `10853 语句 / 789 未覆盖 / 3598 分支 / 326 partial`, TOTAL **91%**(HR 包 93%)。
  下面这组"并行 vs 串行"的对照取自 2026-09-23 采样(结论不变, 数字不再逐轮重采):
  并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`, TOTAL 都是 **91%**
  ⇒ 换默认并行后**分支 partial 多 1**(语句数一致)。
- **成因(单点: [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md))**: 本机每次文件操作
  曾收一笔**固定开销**(初始 写 20ms / 删 43ms, 三盘一致、与数据量无关; 一次全量建 577 个临时目录 ⇒ 约 26s)。
  **已由系统层排除项治好** —— 现 `mkdir` 0.13ms / 写 0.21ms / `remove` 0.16ms / `rmdir` 0.14ms(全部 <1ms)。
  ⇒ 这 3.8× 来自**环境**, 不是代码优化。
- **并行**: 已是**默认**(`pytest.ini` 的 `addopts = -n 4`, dev 依赖 `pytest-xdist==3.8.0`);
  单文件排查用 `-n 0`。台账回传与覆盖率差异见
  [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。

⚠ throttle 守阵(`test_run_loop_throttles_without_stop_event`)文件级/全量跑偶发假红(Windows sleep(50ms) 精度 46ms < 0.05 下限, 容差无余量), 单跑恒绿 —— 已入池 [issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html](../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html), 稳态数字取自 deselect 该用例的全量。

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 变更流水

逐次增量的完整流水(最近在上)已外迁 → [baseline-history.md](baseline-history.md)。
