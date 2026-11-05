"""ConfigMixin: 配置/刷新/分类/标签/添加种子域命令处理器

move-only 自 commands.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
"""
from collections.abc import Mapping

from ..config import Config
from ..core.traffic_source import paths as traffic_paths

from .commands_common import _add_outcome, logger


class ConfigMixin:
    def _category_action(self, name: str, save_path: str, method: str, verb: str, tail: str) -> None:
        """分类写命令单点: create/edit 只差方法名 / 日志动词 / 日志尾部(尾部由调用方给, 文案不变)"""
        getattr(self.api, method)(name=name, save_path=save_path or None)
        logger.info(f"WEB UI | {verb}分类: {name}{tail}")

    def _tags_action(self, tags, method: str, verb: str) -> None:
        """标签写命令单点: create/delete 只差方法名与日志动词"""
        getattr(self.api, method)(tags=tags)
        logger.info(f"WEB UI | {verb}标签: {', '.join(tags)}")

    def _cmd_reload_config(self, config: Config):
        """配置热重载 + **切源即刷新**(计划 26-10-17-1737 S8 / 26-10-18-0813 P0)

        来源身份(`enabled` / `provider` / 文件来源路径)一变, 立刻投递现成的 `refresh_traffic`:
        历史流量图与顶栏 pill 不必等到下一个曲线 interval 才换数据(#7: 切到工具后历史图仍显示
        TM 数据); 关源时该命令发 off 快照, 前端立即转「来源已关闭」关闭态。

        !**投递**而不是在这里直接调用刷新体: 刷新体单点在 `refresh_traffic` handler(26-10-18-0813
        A5 起已改指 `traffic_snapshot.refresh()`), 本处只负责判定「该刷了」—— 两条触发(工具事件 /
        配置切源)共用一条执行路径, 不新增第二份读盘逻辑。命令在本轮 drain 内即被执行
        (consume_commands 是 while 取空队列), 对用户仍是「保存完图表就变了」。
        """
        before = traffic_paths.source_signature(self.ctx.config)
        self.apply_new_config(config)
        after = traffic_paths.source_signature(self.ctx.config)
        if after == before:
            return
        logger.info(f"配置热重载 | 流量来源变更 {before} -> {after}, 立即投递历史流量刷新")
        self.web.post_command("refresh_traffic", {"trigger": "config"})

    def _cmd_refresh_traffic(
        self,
        event_id=None,
        day: str = "",
        trigger: str = "notify",
        up_bytes=None,
        down_bytes=None,
    ):
        """WEB UI 命令: 流量来源刷新(计划 26-10-16-0541 S7 接收面; 26-10-21 事件零读盘补丁)

        两种形态, 判据在**是否带载荷**(up_bytes/down_bytes):

        - **载荷补丁**(notify 触发, 26-10-21 起): 工具阈值事件自带当日权威累计 -> 模块
          `publish_event` **零读盘**补丁 periods 的 day 行(每日高水位钳制)。文件读盘全部
          收拢在 refresh_interval 闸门(用户拍板「读盘本身就是副作用, 要尽量减少读盘」),
          事件路径一次读盘都没有;
        - **全量刷新**(无载荷: 配置切源 `trigger=config` / 兜底): 读一次来源文件并重发
          快照(模块 `refresh()`)。

        两个触发源, 一条执行路径(判据在 `trigger`):
        - `notify`(缺省): **工具进程**的阈值事件(经 POST /api/traffic/monitor/notify 投递),
          不是用户点击 —— 只写 DEBUG 日志, 无回执/通知需求(端点已即时回 200, 不阻塞工具侧
          3s 推送超时; 高频链路记 INFO 会刷屏, 26-10-18 降级, 与接收面/快照发布两级同口径);
        - `config`: 配置热重载发现流量来源变了(见 `_cmd_reload_config`, 1737-S8) —— 保存后立刻
          换图, 日志口径据此区分(事件号为空是常态, 不能说成「监视器通知」)。

        为什么经命令队列而不在端点/热重载里直接发布: 读盘 + 快照发布归主循环线程(黄金法则 5),
        投递方只表达意图; 命令带上事件号与日键只为日志可追。

        刷新体自 26-10-18-0813(A5/D11)起在 **traffic_snapshot 模块**: 快照所有权跟着来源走了
        (历史行 + 各 period 累计 + 来源态), 曲线模块只剩 limit 段。「刷新图」仍是通知链路的
        **唯一**联动动作(不查档、不写 qB 限速, 黄金法则 2)—— 而且现在曲线没配也能刷新:
        这正是「没配曲线就永远没有历史图」那个死角的修复面。命令名 / 端点 / 回执语义不变。
        """
        mod = self.host.get("traffic_snapshot")
        if up_bytes is not None and down_bytes is not None and day:
            patched = bool(mod is not None and mod.publish_event(day, up_bytes, down_bytes))
            logger.debug(f"WEB UI | 监视器事件补丁今日流量: 事件 #{event_id}({day}), "
                         f"状态={'已补丁' if patched else '未变化(高水位钳制)'}")
            return
        refreshed = bool(mod is not None and mod.refresh())
        state = "已刷新" if refreshed else "跳过"
        if trigger == "config":
            logger.info(f"配置热重载 | 流量来源已切换, 立即刷新历史流量: 状态={state}")
            return
        # DEBUG: 通知触发随工具事件密度来(与接收面放行/快照发布两级同口径, 26-10-18 降级)——
        # config 触发是用户保存动作, 一次一笔, 保持 INFO。
        logger.debug(f"WEB UI | 监视器通知刷新历史流量: 事件 #{event_id}({day or '-'}), 状态={state}")

    # ---------- 管理命令(R2B: 分类/标签/限速覆盖/添加种子) ----------

    def _cmd_create_category(self, name: str, save_path: str = ""):
        self._category_action(
            name, save_path, "torrents_create_category", "新建", f"(保存路径 {save_path})" if save_path else ""
        )

    def _cmd_edit_category(self, name: str, save_path: str = ""):
        self._category_action(name, save_path, "torrents_edit_category", "修改", f" -> 保存路径 {save_path or '(未设置)'}")

    def _cmd_remove_categories(self, names=None):
        self.api.torrents_remove_categories(categories=names)
        logger.info(f"WEB UI | 删除分类: {', '.join(names)}")

    def _cmd_create_tags(self, tags=None):
        self._tags_action(tags, "torrents_create_tags", "新建")

    def _cmd_delete_tags(self, tags=None):
        self._tags_action(tags, "torrents_delete_tags", "删除")

    def _cmd_add_torrents(
        self,
        files=None,
        urls=None,
        save_path: str = "",
        category: str = "",
        tags=None,
        paused: bool = False,
        skip_checking: bool = False,
        sequential: bool = False,
        first_last_piece_prio: bool = False,
        auto_tmm: bool = False,
        cmd_id: str = ""
    ):
        """WEB UI 添加种子: .torrent 原始 bytes 经命令队列传给主循环线程, 内存直交 qB(qbittorrent-api
        _normalize_torrent_files 原生支持 bytes) —— 零临时文件。

        回执由本 handler 依 qB 结果串写(**三态**, 单次调用判定见 `_add_outcome`) ——
        "指令已发"与"qB 接受"分开:
          · 全部受理(文件与链接两次调用都无被拒) -> `ok`;
          · **部分受理**(有加进去的、也有被拒的, 典型"其余已存在") -> `warn`, 文案带计数详情
            —— qB 对重复种子是**整批里挑着拒**(HTTP 200 + failure_count>0), 不是整批 409,
            所以"部分成功"是常态路径而不是异常; 前端按 warn 关窗(详见下方回执段注释);
          · 全部被拒 -> `error`(全部重复时 qB 回 HTTP 409, 库抛 Conflict409Error, 由命令
            分发层写 error 回执, 走不到这里)。
        skip_checking 属高危选项, 前端默认关 + 警告, 此处照传(用户显式动作, 不做二次拦截)。

        选项下发口径: **qB 侧 `std::optional` 的两个选项(停止位 / 自动管理)恒显式传布尔**,
        其余普通 `bool` 选项为假时省略(缺省即 false, 省略安全) —— 判据见下方注释与
        `memory-bank/pitfalls/backend/qb-api.md`。"""
        kwargs = dict(
            save_path=save_path or None,
            category=category or None,
            tags=tags or None,
            is_skip_checking=bool(skip_checking),
            is_sequential_download=bool(sequential),
            is_first_last_piece_priority=bool(first_last_piece_prio),
        )
        kwargs = {k: v for k, v in kwargs.items() if v not in (None, False)}
        # !停止位是**唯一必须显式下发**的布尔选项(既不能省, 也不能用 is_paused 传), 两处坑叠加
        #   才会让前端「添加后开始」勾了等于没勾(2026-09-24 实测 bug):
        #   1. qB 侧 `stopped` 缺省时**不是** false, 而是回落到会话级默认 —— SessionImpl::
        #      initLoadTorrentParams 里 `addStopped.value_or(isAddTorrentStopped())`, 那个会话值由
        #      qB 自己的添加对话框/选项("不自动开始")写入 ⇒ 用户勾了「添加后开始」照样按停止添加;
        #   2. qbittorrent-api 的 `is_stopped = is_paused or is_stopped` 会把 **is_paused=False 折成
        #      None**(`False or None` == None) ⇒ 传 is_paused=False 等于没传(实测请求体为空字符串);
        #      只有 is_stopped=False 才会真的发出 `paused=false&stopped=false`。
        #   qB 自家 WebUI 同此口径: addtorrent.js 恒传 stopped=true/false, 从不省略。
        kwargs["is_stopped"] = bool(paused)
        # 自动管理同理**必须显式下发**(qB 侧 `useAutoTMM` 也是 `std::optional`):
        # 缺省时 `SessionImpl::initLoadTorrentParams` 走
        # `value_or(savePath 空 ∧ downloadPath 空 ∧ !isAutoTMMDisabledByDefault())`
        # ⇒ 不填保存路径且 qB 全局是"自动管理"时会被判成 True, 前端那个勾选框等于没勾。
        # (填了保存路径时缺省恰好也得 false, 所以这个隐患只在"未勾 + 未填路径"这一支暴露。)
        # qB 自家 WebUI 的 autoTMM 是 `<select name="autoTMM">`(Manual=false 默认 / Automatic=true),
        # 随表单恒提交 —— 同此口径。
        # !只有 qB 侧声明为 `std::optional` 的选项才需要这样显式下发; 普通 `bool` 的
        #   (sequential / firstLastPiecePriority / skip_checking) 缺省就是 false, 省略安全。
        kwargs["use_auto_torrent_management"] = bool(auto_tmm)
        results = []
        if files:
            results.append(self.api.torrents_add(torrent_files=files, **kwargs))
        if urls:
            results.append(self.api.torrents_add(urls=urls, **kwargs))
        outcomes = [_add_outcome(r) for r in results]
        states = [s for s, _d in outcomes]
        detail = "; ".join(d for _s, d in outcomes)
        # 期望落地登记(issue 26-10-30-0626 候选 A): 回执里的 added_torrent_ids 是**期望新增
        # 集合**, 而 qB 的 200 只代表受理 —— torrent 还要过 6~40ms 的异步管线才进 session,
        # 命令后那次补刷新距此仅 0.5~0.8ms, 必然只拿到一部分。登记后主循环有界追平
        # (80ms × ≤3 次), 让这一批在 ~100ms 内全部可见, 而不是等下一个 1.5s 节拍。
        self._expect_landing(results)
        # 聚合判据(受理态三值, 见 _add_outcome): "加进去了没有"与"有被拒的没有"是两个
        # 独立问题 —— 旧布尔把 partial 与 fail 压成同一值, 于是部分成功只能报 error。
        #   added ∧ ¬rejected -> ok(全部受理);
        #   added ∧ rejected  -> warn(部分受理: 文件/链接两次调用各自可能 ok/partial/fail,
        #                            跨调用混合同样收敛到这一档);
        #   ¬added            -> error(全部被拒; 空 outcomes 也落这里)。
        added_any = any(s in ("ok", "partial") for s in states)
        rejected_any = any(s in ("fail", "partial") for s in states)
        if cmd_id:
            if added_any and not rejected_any:
                self._set_web_result(cmd_id, "ok")
            elif added_any:
                self._set_web_result(cmd_id, "warn", f"部分种子未添加(可能已存在): {detail}")
            else:
                self._set_web_result(cmd_id, "error", f"qB 未接受添加: {detail}")
        # 级别即通知语义(见 conventions/code-style.md 日志规范): 受理成功走 INFO —— 原写法用
        # WARNING, 而 NotifyHandler 挂在 auto_qb logger 上 ⇒ **每次添加成功都往桌面推一条
        # "auto-qb WARNING" 弹窗**, 用户据此以为添加失败。部分受理同样走 WARNING(有种子没进去)。
        line = f"WEB UI | 添加种子: 文件 {len(files or [])} 个, 链接 {len(urls or [])} 条 -> {detail}"
        if added_any and not rejected_any:
            logger.info(line)
        elif added_any:
            logger.warning(line + "(部分受理)")
        else:
            logger.warning(line + "(qB 未接受)")

    def _expect_landing(self, results) -> None:
        """把 add 回执里的 added_torrent_ids 登记为「待落地」(issue 26-10-30-0626 候选 A)

        只有 Web API >= 2.14.0 的 JSON 回执带这个字段(见 `_add_outcome`); 老版 qB 是纯文本
        `Ok.`/`Fails.`, 拿不到 id —— 那种版本上静默跳过, 现象退回"等常规节拍", 不因此报错
        (老版 qB 连 `success_count` 都没有, 编不出集合, 硬猜只会引入误登记)。

        登记是**幂等合并**语义: 同一批文件+链接两次调用各自登记, 与并发添加互不覆盖。
        """
        ids: list[str] = []
        for r in results:
            if isinstance(r, Mapping):
                ids.extend(str(x) for x in (r.get("added_torrent_ids") or []) if x)
        if ids:
            self.store.expect_hashes(ids)
