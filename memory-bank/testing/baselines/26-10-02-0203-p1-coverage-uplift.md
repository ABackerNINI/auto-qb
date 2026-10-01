# 基线 · 2143 passed + 3 skipped / 96% —— 测试覆盖率提升 P1 服务与路由层(T1.1-T1.4)

> 摘要: 计划 26-10-01-2157(测试覆盖率提升 91%→96%)P1 阶段收官基线 —— hr 错误路径 + hr 二线长尾 + webui 二线 + infra 长尾四块落地, 综合覆盖率 93.24% → 96.49%(已越过 P1 目标线 95%, 达到 P2 终点区 96%±)。
> 档案: [plans/26-10-01-2157-plan-test-coverage-uplift.html](../../plans/26-10-01-2157-plan-test-coverage-uplift.html)。
> 基线时间: 2026-10-02 02:03, develop @ effa6e2c(与远端合流后的新基线上实测; 工作树含本笔改动与收尾回写, 未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告 —— 两侧都重测前不当作两侧事实源)。

TOTAL **2143 passed + 3 skipped / 96%**(13378 语句 / 396 未覆盖 / 4444 分支 / 170 partial,
test.full 28.50s 实测汇总行 / 引擎墙钟 29.1s, rc=0)。**精确综合口径**(coverage json 导出, 行 + 分支出口合计):
**17,196 / 17,822 = 96.49%**(语句 12,982/13,378 = 97.04%, 分支 4,214/4,444 = 94.82%)。
相对 P0 基线(26-10-02-0025: 16,616/17,821 = 93.24%)**+580 已覆盖单位**(预估 +400±50, 实测 +45%);
分母 +1(合流的远端提交 7cff3adb 带入 LaneStatus.lane_text 一行, 已由远端自带测试与本笔共同覆盖)。
**hr 包行覆盖 3,488/3,498 = 99.71%**(验收线 ≥96%)。

## 本笔改动面 (P1 任务逐项, 只改 tests/ 下 19 个测试文件, 产品代码零改动)

- T1.1 `hr/service.py` 错误路径系统补齐(plan 欠账 180)→ test_hr_service.py +25:
  站点守卫三态与锁占用 / 内部异常收容 / 扩展硬上限让位与一次性告警 / 登录页 adapter 识别 /
  挑战页波级截断 / 必填字段缺失第 2 页截断 / 日额用尽与无 sleeper 让位(等满再试仍拒与等不起双路径) /
  _Budget 等待记账与双上限 / 页数耗尽未轮到档收尾 / 方向翻转与跨页乱序强制早停 / 停翻2. 跨页重算 /
  行处理身份接管与放行撤销 / 下载队列四分支 / 非法 .torrent 计失败 / 只读退化与 persist=False /
  波次纯函数单元(摘要/淘汰/位置覆盖/缺席证明) / 对象集守卫(空 hash/非活跃/漂移回炉) /
  通道状态四态 / 连续失效 ERROR 升级 / 冻结与观察期守卫。
- T1.2 hr 二线长尾 → 各对应现有文件扩展: bencode +6(_skip 直调/顶层未闭合/info 非字典/缺冒号)、
  server +6(混合回传计数/OPTIONS 真请求/413/500 容错/停机超时/头解析单元)、store +8(读失败/根非字典/
  字段解析失败/quarantine 双路径/备份读失败/告警去重/session.site)、report +8(URL 档位变体/确认戳三态/
  观察期文案/CJK 截断/时刻占位/共享目录/视图行)、resolve +6(漂移四分支/三态文案/视图工厂/免锚判定/免罪毕业标签/未知档位跳过)、
  status +7(时长四档/两个 to_dict/过窗文案/模型谓词与解析边界/infohash 回落/反查表过滤/脏放行记录丢弃)、
  parse +11(数值容错边界/无 href 锚点/表头非首行/页脚区间/多处逆序/dl_id 回落/tid 越界与非数字/缺编号列降级)、
  worker +5(start 幂等/停机超时/受理过滤/启动发布失败补 WARNING 与节流)、runtime +3(sleeper 即抛/转发 wake/events 直调)、
  queue +2(回执 TTL/缺 received_at)、fetcher +2(NullFetcher 双入口/tid 提取容错)、ratelimit +2(日额下次可取/now_ts)、
  channel +4(空 token 文件再生成/白名单跳过/绝对下载回退/回执可选字段)。
- T1.3 webui 二线 → test_web.py +21: runtime 直测(SSE 丢弃计数/在途汇报确认全路径/补刷新计时分级/
  回执表 TTL 淘汰与 truth/受影响种子三形态与异常退化/真值直查失败不回落快照)、commands 直测
  (delete 透传/汇报缺失回执/recheck 与 skip-check 拒绝回执/限速部分方向/分享限制 -2 补齐/重命名文件夹/
  批量参数四类错误/批量缺失分列/批量 recheck 经 ops/添加种子受理与拒绝)、路由补遗
  (pause/resume/delete/skip-check/limits 入队形状/add 端点 base64 校验/config 树形状 400 与 preview 不落盘/
  表达式求值期失败/快捷键校验往返/分类标签空入参 400/限速托管直读与断连/fs 端点错误语义化 404·501·403·400)。
- T1.4 infra 长尾 → test_utils.py +12、test_file_access.py +4、test_locking.py +3、test_ui.py +1:
  atomic_write 备份失败与失败清理/长路径相对路径/match_tracker_confs 容错/集数模板空跳过/timer 单位/
  _win_shell_open PIDL 三分支与 COM 配对(shell32/ole32 全假替身, 经 sidefx._saved 取回原函数避开记账假阳性)/
  user32·kernel32 绑定/Explorer 枚举与置前三层矩阵/复用窗口标题匹配与重试封顶/
  file_access 折叠边界与抽象守卫/自检探测失败/锁释放幂等与失败静验/meta 写失败/自启注册注销失败语义。

## 红验与防回沉

- 变异红验 7 条(≥10% 抽样, 全部当场红、逐条精确还原, 还原后 `git status src/` 干净):
  ①service `_warn_ext_quota` 去重条件翻转 → test_channel_quota_lets_wave_yield_and_warns_once 红;
  ②service readonly 注记分支短路 → test_readonly_degradation_noted_in_result 红;
  ③bencode 字典键类型守卫摘除 → test_bdecode_rejects_malformed_direct[di1e1:xe] 红
  (首轮 mutant 对 `di1ee` 假绿 —— 守卫摘除后仍被「非法字节」分支拦下, 按 unreached-branch-guard
  把夹具换成能完整解析出 dict 的 `di1e1:xe` 后判别力成立);
  ④webui/runtime queue.Full 丢弃计数摘除 → test_web_runtime_notify_drops_are_counted 红;
  ⑤utils atomic_write 备份失败静默改上抛 → test_atomic_write_backup_failure_continues 红;
  ⑥locking meta 写失败静默改上抛 → test_single_instance_lock_meta_write_failure 红;
  ⑦commands 分享限制缺失维度补齐值 -2→-1 → test_web_commands_limits_partial_directions 红
  (首轮 mutant 落在 ratio 维度未被本测覆盖, 改种 seeding_time 维度后红)。
- P3-M1 阈值随本切片抬起: pytest.ini `--cov-fail-under` 92 → 94(实测 96.49% − 1 个点余量的
  整数档取 94, 口径见计划 §5 与 P1 DoD; test.quick 的 --no-cov 豁免不动)。
- 范围外发现(只记录, 不修不入池): ①`hr/service.py` `_do_wave` 的 `except HrFetchError` 582-585 行
  不可达 —— `_run_pages` 内层把无 Retry-After 的页面失败全部就地截断, 能上抛的只有 retry_after>0;
  ②`_finish_wave` 末尾无条件 `discard` 三个告警去重集合, 使「登录失效/无通道每站只报一次」的
  设计注释与实际行为不符(每波都会重报, test_login_page_detected_by_adapter_and_warned_once 已按实测行为断言);
  ③`HrRefreshService._prune_index` 静态方法与模块级 `_prune_index` 同体重复, 前者无生产调用方
  (测试已按双口径各钉一条)。
