# RM08 附加轮(读侧): /api/sites/missing groups 分组字段 3/3 全绿 —— WebUI 读侧共现分组/空场/不粘合/引导数据前提首验, 零产品缺陷(1 条数据新鲜度观察项在案)

> 摘要: RM08 附加轮(计划 plans/26-11-04-0140-plan-real-rm08-addendum-missing-merge.html), 被测面 = 缺失站点导出/导入 tracker 合并功能的 **WebUI 读侧**(功能计划 plans/26-11-03-2337 M3/M4, 已入库至 b01609ca; CLI 导出面已由 RM10 附加轮切片 26-11-04-0126 钉住)。并入 RM08 片, 新建 3 条(RM08-10~12, 落 tests-real/rm08_webui_read/test_rm08_missing_groups.py, 与既有 RM08 片共享 conftest 串行锁与环境 fixture; **id 从 RM08-10 起顺延** —— 排期指令建议的 RM08-09 已被计划 26-11-02-0351 千文件用例占用, 编号不复用): ① groups 分组契约(**新建即 L2**: 共现 union-find 传递闭包 3 元素组 + 组名与 sites 同 taken 序列顺延撞名加 `_1` 后缀 + 单元素组)② 负向对照(**新建即 L3**: 空场 sites/groups 双空数组非 null/缺键 + 已配置域不粘合两缺失域 D1 语义真机验证, 两条红验真跑)③ 三分支自适应引导数据面前提(**新建即 L2**: 全单组/多组两形态的「存在 ≥2 域名组」闸门在端点载荷上可判)。读侧驱动 = dev.webui 安全模式(§2.4), 只发 GET, 零写侧操作。三态 **3/0/0**; **零产品缺陷入池**, 1 条数据新鲜度观察项在案(§03.1, 交主会话裁决是否入池)。造场复用 RM10 配方(互异 127.x IP 字面量 + 死端口 announce, 种子全程 paused, 零 DNS 零外连)。
> 基线时间: 2026-11-04 01:53(官方合跑 = 3 条一次, 30.52s; 首跑 01:49 RM08-12 测试侧假红, 修复后官方轮全绿, 见 §04)
> 基线 commit: `b01609ca`(官方合跑时刻 HEAD; 本轮禁止 git 写操作, 用例/计划/切片全部留工作树未提交 —— 与规程 §06.7「用例照常 ship.commit」的偏差由本轮排期指令硬约束所致, 提交动作移交主会话)

## 01 验收数字

`uv run pytest tests-real/rm08_webui_read/test_rm08_missing_groups.py -q --no-cov`(2026-11-04 01:53, 环境2):

```text
3 passed in 30.52s
```

- 产品缺陷 0 个入池; FAIL 0(官方轮); BLOCKED 0。
- 档位分布 **L0/L1/L2/L3 = 0/0/2/1**(L2×2: 10/12, L3×1: 11 新建即档)。
- 升档核验(计划 §03.2): 本轮 3 条纯新增(功能新面), RM08-11 新建即 L3 —— 红验真跑两条: ①空场「设计域应在 sites」故意错位断言真红 ②「P/Q 应同组」故意错位断言真红(must_be_red 自证, RM10-13 同款口径)。满足「每轮至少 1 条升一档」硬要求。

逐条结果(档位按计划 §03.1):

| 用例 | 内容 | 档位 | 结果 |
|---|---|---|---|
| RM08-10 | groups 分组契约: 3 枚 paused 假种子(A=[127.0.0.7,127.0.0.12] / B=[127.0.0.12,127.0.0.13] / C=[127.0.0.14])→ torrents==3 / domains==4; sites 原形(逐域名 name=`127_0_0_*`/entry 逐键); groups 恰 2 组 —— 合并组 domains==[127.0.0.12, 127.0.0.13, 127.0.0.7](传递闭包)、name=`127_0_0_7_1`(代表=组内最短, 与 sites 同 taken 序列顺延)+ 单元素组 `127_0_0_14_1`; 组 entry.domains==组内全域名 sorted、tags==[""]、hr/限速示例段与 sites 同源; sites 与 groups 名字集零交集 | L2 | PASS |
| RM08-11 | 负向对照: 腿① 配置 domains=["127.0.0"](双向包含匹配覆盖全部 127.0.0.x)→ sites==[] 且 groups==[](双空数组, isinstance 校验非 null/缺键), torrents/domains 计数照常; 腿② X=127.0.1.5 已配置, 种A=[X,P] 种B=[X,Q](P=127.0.0.21 / Q=127.0.0.22 缺失且从不同现)→ groups 恰 [[P],[Q]] 各自成组、零「同时含 P 与 Q」的组(**D1 不粘合语义真机验证**); 两条红验自证真红 | **L3**(新建即档) | PASS |
| RM08-12 | 三分支自适应引导数据面前提: 同一造场(S1=[127.0.0.31] S2=[127.0.0.32])两形态 —— 全单组: 组数==sites 数==2、逐组 entry==逐 site entry 逐键相等、组名==site 名+`_1` 顺延、闸门(存在 ≥2 域名组)判 False; S1 经 addTrackers 追加 127.0.0.32 共现后(**新起一份产品进程**, 见 §03.1)闸门判 True、恰一组 domains==[S1,S2]、sites 原形保持 —— 同一载荷自带 groups, 前端免第二次请求即可判定 | L2 | PASS |

**三态: PASS 3 / FAIL 0 / BLOCKED 0。**

**零外连红线**: 全程成立。announce 全部 `http://127.0.0.x:1/announce`(IP 字面量零 DNS + 死端口连接即 RST); 种子全程 paused(stopped*)不 announce; 产品进程只发 GET 读侧请求; 实例内真实种子 0 枚; real-fake 收尾删净; guard 复跑绿。

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境 | 环境2(C盘机), `QBT_REAL_ENV=2` 显式指定; token 经环境变量注入(QBT_TEST_56589/56590), 全程零落盘(repo 全仓 grep 两条 token 字面值零命中, 官方轮后实测) |
| 实例版本 | qBittorrent v5.2.3(两实例同 build) |
| 56589(主) | pid 8228(开工=收尾一致, 零重启), firewalled, 真实种子 **0 个**; 本轮零触碰(收尾实测 torrents 0) |
| 56590(副) | pid 7596(开工=收尾一致, 零重启), firewalled; 造场与产品配置都指向它(空凭据直连); 收尾 real-fake 残留 0、种子 0 |
| bypass_local_auth | True(环境2 标准配置, 56590, 本轮未触碰) |
| 产品解释器 | `.venv` → CPython 3.13.15(uv 管理); 产品进程 = `python -m auto_qb <cfg>`(dev.webui 安全模式最小配置, 自动任务全关), 每条用例起停(收尾 taskkill /F /T 整树, 收尾实测零 auto_qb 残留进程) |
| 产品配置 | 每条(每形态)派生独立配置落 `.work/rm08/rm08_1x/config.yml`; schema_version: 5; 指 56590 空凭据(**api_key: ""**, D2 拍板); trackers 段按腿注入: rm08grp_invalid(rm08grp.invalid, 与 announce 零命中)/ rm08_cover(["127.0.0"] 全覆盖)/ rm08_glue(["127.0.1.5"]) |
| 落点 | 假种子数据只落 `tests-real/.work/rm08/rm08_1x/seeds/`(KB 级 2-3 枚/场 ×4 场); real-fake 标签收尾删净; `.work` 全清(real.seed.clean 实测「已清空」) |
| 收尾进程口径 | qB 进程比对恰开工两枚(8228/7596); 产品 python 进程零残留 |

## 03 本轮实测确认的代码事实(回写素材)

1. **产品 store 对种子 tracker 列表惰性缓存, 绕产品的 qB 直改对在跑进程不可见**(本轮唯一观察项, 交主会话裁决是否入池): `/api/sites/missing` 逐种查 tracker 走 facade `torrents_trackers`(qbapi.py:334-337)→ store 命中时读记录级惰性缓存(`record.py:269-276`, `_trackers_info` 一经拉取持久持有), 该缓存**只在产品自身 tracker 写操作时失效**(`qbapi.py:261-268`, torrents_add_trackers/remove_trackers 后 invalidate), 同步循环不失效。复现: 同一产品进程内先 GET 一次(缓存落定)→ 直接对 qB `/torrents/addTrackers` 追加域 → 再 GET 仍回旧域名集(本循环 RM08-12 首跑实测, 共现组不出现)。影响面: 用户在 qB 侧改 tracker 后回到产品 WebUI 二次点「导入缺失站点」, 第二次扫描吃到第一次的缓存 —— 数据新鲜度口径问题, 非崩溃级; 「当轮不修」纪律下记录待裁决。
2. **groups 分组契约真机首验成立**(官方轮): 共现 union-find 跨种子传递闭包(A∩B 经 127.0.0.12 传递)、组名与 sites 同一 taken 序列顺延(sites 先取名, 组名撞名加 `_N`)、空场双空数组、已配置域双向包含匹配(configured in host)真机可观测 —— sites.py 端点面零缺陷。
3. **「全单组退化」逐键对应**: 单元素组 entry 与对应 site entry **dict 逐键相等**(同 build_tracker_entry 同参产出)、组名恰为 site 名 + `_1`(gen_tracker_name 首撞即 `_1`)—— 前端「sites/groups 不互查名字」注释口径(sites.py:71-75)真机成立。
4. **RM08-07⑥ 的 sites/missing 旧断言与 groups 兼容**: 空库无 announce 场景 groups 为空数组 —— 加字段向后兼容在真机确认(旧断言 `sm["sites"] == []` 不受影响)。

## 04 排障与复跑记录

| 轮次 | 内容 | 结论 |
|---|---|---|
| 首跑 01:49 | RM08-10/11 PASS; RM08-12 FAIL(共现后复扫仍回全单组, groups 不出现 2 域名组) | **测试侧造法假红**(未考虑 §03.1 的 store tracker 惰性缓存: qB tracker 视图已可见但产品进程缓存未失效), 修用例 = 形态二新起一份产品进程(新 store), 产品零改动 |
| 官方轮 01:53 | `3 passed in 30.52s` | 一轮即绿, 零 FAIL 零假红; 用例代码官方轮前定稿, 官方轮后零改动 |

## 05 遗留与解锁条件

- **三分支自适应引导的三钮框观感与交互**: L0 目视挂账(本轮只钉数据前提 —— 闸门判定在端点载荷上可判; 与 RM08 D3 横滚条、RM10 三钮同批, 归用户下次目视清单)。
- **RM08 既有 9 条(RM08-01~09)**: 本轮附加面不重跑。漂移体检(§07)显示 RM08 glob 自 b65520ad 后另有非本功能命中(GTM 横幅/flux 皮肤/大文件窗口化/搜索修复/move-only 拆分), 各归其主已由各自轮次覆盖 —— **记账建议: 下次 RM08 正式排期轮按 §07 对这些命中补整片回归**(现有 9 条复跑即可)。
- **§03.1 数据新鲜度观察项**: 待主会话裁决入池与否; 若入池, 修复后 RM08-12 的「单进程双形态」变体可作回归红验。

## 06 基线 commit

本轮为 RM08 **附加轮**(基线 b65520ad 本 clone 解析不到 —— 合流 rebase 改写 lineage, 漂移体检按「写不出 commit」口径以 author date + 文件历史近似判定, 见 §07)。**基线 commit = `b01609ca`**(官方合跑时刻 HEAD, 与功能面基线一致; 本轮改动全部留工作树, 收尾无提交)。下次漂移体检用它做
`git log b01609ca..HEAD -- src/auto_qb/webui/views.py src/auto_qb/webui/runtime.py src/auto_qb/webui/server/routes/state.py src/auto_qb/webui/server/routes/torrent_detail.py src/auto_qb/webui/server/routes/sites.py src/auto_qb/webui/server/routes/events.py "src/auto_qb/webui/static/shared/**"`(glob 以锚件 §03 RM08 行现值为准)。

## 07 记账与结论

- **glob 自检**(§05 规则 8, 2026-11-04 `git ls-files` 实测): 本功能两个落点均被 RM08 行 glob 覆盖 —— `src/auto_qb/webui/server/routes/sites.py` 为行内显式条目; `src/auto_qb/webui/static/shared/config_hub_tracker.js` 落在 `src/auto_qb/webui/static/shared/**` 通配内。命中非零, 片未失效, 不拆不并。
- **漂移体检**(§07): 基线 b65520ad 解析不到(bad revision, rebase 改写), 近似判定(文件历史): 本功能命中 = dc98fb44(M3 sites.py 追加 groups, **纯新增字段**)+ 0fae1a66(M4 config_hub_tracker.js/ui_feedback.js 三钮引导, **纯新增前端面**)+ b01609ca(纯注释)—— 判据变即本轮被测面本身。RM08 glob 其余 11-02 以来命中(GTM 横幅 d3a0cf98/26cc51fb、flux 皮肤 S5-S7、大文件窗口化 e6b02991、搜索修复、move-only 拆分 20a74274/deb1168d 等)各归其主, 不在本附加轮 scope, 整片回归记账到下次 RM08 正式轮(§05)。
- **测试侧改动清单**(产品 src/ 零改动): 新增 tests-real/rm08_webui_read/test_rm08_missing_groups.py(3 条, 复用同目录基座模块); pytest.ini 未动; RM08 既有用例零改动。
- **收尾核净**: 两实例种子 0 / real-fake 残留 0(real.seed.rm --all 命中 0 + clean 实测「已清空」); guard 复跑绿(双 firewalled); 进程比对恰开工两枚(56589=8228 / 56590=7596, 零重启); 产品 python 进程零残留; token 零落盘(repo 全仓 grep 两条 token 字面值零命中)。
