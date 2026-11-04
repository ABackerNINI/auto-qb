"""ops 闸门/证据叶: 跳检闸门三分流判定与校验证据(自 ops_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 ops_mod.py 原文件逐字一致。
"""
from datetime import date
from typing import Optional

from ...rules.base import ActionResult
from ...rules.checking_meta import INFLIGHT_TTL, is_piece_checking, recheck_fail_count
from ...torrents import TorrentRecord
from ..state import prune_day_keys
from .ops_common import GATE_BLOCKED, GATE_FORCE, GATE_OK, GateVerdict, logger


class VerdictMixin:
    def skip_check_precheck(self, hashes: list) -> list:
        """跳检预检(只读 dry-run, plan 26-10-05-0314 D6/D9): 逐 hash 给出三分流判定, 供 WEB 确认框
        在用户确认之前摊开「该不该跳检、赌什么」; 执行路径闸门原样全跑 —— 预检与执行之间无信任传递。

        只读承诺(T20): 不写 state(skip_check_day 不写入不 prune)、不 pop、无任何 qB 写 API、
        种子零变动 —— 内部仅走 _skip_gates_detail(零副作用判定)与 check_filelist(torrents_files
        只读); _skip_gates 的 prune 副作用不得经 detail 泄入本路径。经命令队列在主循环线程执行
        (与写命令串行化, 快照无撕裂)。

        返回 list[dict] 单 hash 一条, 字段命名对齐 S2 的 HTTP 回执形状
        {results: [{hash, name, cls, reasons}], summary: {ok, force, blocked}}(summary 由调用方聚合):
        - cls: 单 hash 总三分流, blocked > force > ok(任一未过闸门 blocked 即 blocked;
          否则存在 force 类未过即 force; 全过 ok);
        - reasons: [{gate, cls, text}, ...] 即 _skip_gates_detail 的全部未过闸门; tor 已不在
          客户端(store 无记录)时单条 gone/blocked, 文案「已不在客户端」(S2 端点测试 T21 依赖)。
        """
        results = []
        for h in hashes:
            tor = self._ctx.store.get(h)
            if tor is None:
                results.append(
                    {
                        "hash": h,
                        "name": "",
                        "cls": GATE_BLOCKED,
                        "reasons": [{
                            "gate": "gone",
                            "cls": GATE_BLOCKED,
                            "text": "已不在客户端(可能已被删除), 无法跳检"
                        }],
                    }
                )
                continue
            verdicts = self._skip_gates_detail(h, tor)
            if any(v.cls == GATE_BLOCKED for v in verdicts):
                cls = GATE_BLOCKED
            elif verdicts:  # 只剩 force 类未过
                cls = GATE_FORCE
            else:
                cls = GATE_OK
            results.append(
                {
                    "hash": h,
                    "name": tor.name,
                    "cls": cls,
                    "reasons": [{
                        "gate": v.gate,
                        "cls": v.cls,
                        "text": v.text
                    } for v in verdicts],
                }
            )
        return results

    def _skip_gates(self, hash: str, tor: TorrentRecord, force: bool = False) -> Optional[ActionResult]:
        """跳检前置闸门(执行路径): 从 _skip_gates_detail 派生 —— 取首个未过闸门转 ActionResult,
        谓词只写一遍、执行与预检两路径同源(防两套谓词漂移, T18 同源断言钉死)。

        - 返回形态与既有语义一致: dedup 沿用 skip, 其余闸门 fail; None = 全部通过。
        - force=True 仅把 cls=force 的未过闸门降级为 warning 日志后放行(另记 INFO 审计:
          哪个 hash 豁越了哪个闸门); cls=blocked 一律硬拒。
        - 全部通过(含 force 豁越后)时顺带清理非当日 skip_check_day 记录(防 state 无界增长)
          —— 这是本路径**专属副作用**, detail(预检)零写入(T20)。
        """
        for v in self._skip_gates_detail(hash, tor):
            if force and v.cls == GATE_FORCE:
                logger.warning(f"{tor.log_repr} | force 豁越跳检闸门 {v.gate}: {v.text}")
                logger.info(f"force 审计: hash={hash} 豁越闸门 {v.gate}(跳检继续)")
                continue
            if v.gate == "dedup":
                return ActionResult.skip(v.text)
            return ActionResult.fail(v.text)
        skip_day = self.state.get("skip_check_day")
        if skip_day:
            # 只留当日 = 保留窗 keep_days=0 的特例(prune_day_keys 单点, 对齐
            # state/_prune_exec_history 与 speed_curve 的日键淘汰口径)
            prune_day_keys(skip_day, date.today(), 0, lambda k, v: v)
        return None

    @staticmethod
    def _dur_text(age: Optional[float]) -> str:
        """「已 N 分钟」文案片段(不足 1 分钟 / 时长未知 -> 空串); 纯展示, 不参与判定"""
        if age is None or age < 60:
            return ""
        return f", 已 {int(age // 60)} 分钟"

    def _checking_evidence(self, hash: str, tor: Optional[TorrentRecord]) -> Optional[tuple]:
        """「该种子有全量校验在途」的证据 -> (来源, 已进行秒数) 或 None(无)

        两半视野, 都只读本地已有的真相, **不发起任何 qB 查询**(命令后直查不可靠: 运行状态是
        qB 按 RefreshInterval 刷新的缓存, 见 issue 26-10-21-1812-bug-decision-moment-live-query):
        - 快照生效证据 is_piece_checking(checkingDL/checkingUP): 覆盖外部/手动发起的校验。
          !盲区: qB 对**停止态**种子不报 checking*(torrentimpl.updateState 的 checking_files
          分支要求 !isStopped, 停止时落回 stoppedDL/UP), 暂停中的校验在状态上看不见;
        - 队列在途登记(带 INFLIGHT_TTL): 覆盖本程序发起、qB 状态暂时看不见的校验; 超时视为
          登记泄漏(轮询任务已被丢弃) -> 记 WARNING 后忽略, 不让一个泄漏登记永久挡住闸门。
        """
        state = tor.state if tor is not None else ""
        if is_piece_checking(state):
            return ("state", self._ctx.store.state_age(hash))
        age = self._ctx.task_queue.active_check_age(hash)
        if age is None:
            return None
        if age > INFLIGHT_TTL:
            logger.warning(f"在途校验登记超时({age:.0f}s > {INFLIGHT_TTL:.0f}s): hash={hash[:8]} 视为登记泄漏并忽略"
                           f"(对应轮询任务已不存在)")
            return None
        return ("inflight", age)

    def _skip_gates_detail(self, hash: str, tor: TorrentRecord) -> list:
        """跳检前置闸门判定单点(只读): 按固定顺序逐闸门判定, 返回**全部未过**闸门(全过 = 空列表)

        三分流 cls 与谓词同点定义(见 GateVerdict)。执行路径 _skip_gates 取首个未过闸门, 预检
        skip_check_precheck 消费完整列表 —— 两路径同源。

        零副作用铁律(T20): 本判定不写 state、不 prune、不 pop、无任何 qB 写 API —— 预检
        「只是看看」不得改状态; skip_check_day 的清理留在执行路径(_skip_gates 尾部)。

        顺序与短路: dedup → G3 → G4 → G5 → G6 → G7 → G8 → partial → filelist(排最后, plan 插入点由
        skip_check 的执行序保证: R2 实时复核之后、导出之前)。前面已有 **blocked** 未过时短路
        跳过 filelist(省一次 files API + N 次 stat —— 结论已注定 blocked); 仅 force 类未过时
        **不**短路: force=True 豁越后 filelist 仍须真跑(case 1 硬闸不得被短路绕过)。

        各闸门口径:
        - dedup: 跨规则同日去重(全来源) —— 多条规则都配 checking 时, 同一种子当日只跳检一次
          (跳检必然清空本地统计, 重复跳检只会再丢一次而毫无收益)。排最前(26-10-11-2045):
          跳检成功 ⇒ 种子必为已完成 ⇒ 「已完成」(G3)与「今日已跳检」恒同时成立, dedup 若排在
          G3 之后即被结构性遮蔽(执行路径取首个未过, 文案与 skip 类别双双被改写); 「今日已
          跳检过」也是重复请求的最直接答案 —— 谓词全组最便宜(一次 dict 查询), 前移零副作用(T20 只读)。
        - G3 已完成(progress>=1, 无论状态) / G4 活跃中(非 stopped 且 p<1): 放行谓词逐字同
          rules/actions/checking.py:88 决策链 0(两处注释互指); stalledDL 等边缘态口径由
          state_enum 现有语义决定, 与规则侧天然一致(同一谓词), 不发明 WEB 特有口径(plan §03)。
        - G5 同 hash 校验在途(ctx.task_queue.active_check_hashes(), recheck 在途互斥同款原语):
          跳检删种会杀死在途校验轮询 —— case 2(组内其它成员校验在途同归 case 2, 见 G7)。
        - G6 组内有活跃下载成员(经 store.group_has_downloading, S1a 上移的组级判定单点):
          组内共享物理文件, 下载方正在写, 跳检把全部块标有效 = 脏数据。
        - G7 组内其它成员 full-checking 在途(case 2): 谓词逐字镜像
          rules/actions/full_checking.py _wait_for_group_checking.others_checking(决策链 1.5,
          others-only 排除自身), 两半视野: 队列登记 active_check_hashes(规则发起) ∪ store 快照
          is_checking(后半覆盖用户手动 recheck —— G5 的队列视野看不见它)。判决窗口抢跑是真不确定:
          判决通过即证明共享文件完好, 判决失败则洗白坏数据 —— 同 G5 给 force 逃生(D4/D8 拍板)。
        - G8 组内成员校验失败推断(case 1): 四要件逐字镜像
          rules/actions/full_checking.py _skip_on_group_check_failed(决策链 1.6, others-only):
          其它成员 / 当日计数(recheck_fails, 含宽限耗尽/异常噪声 —— 继承规则侧既有假阳性面,
          同日窗口+自愈条件兜底, 不发明更锐利谓词) / 假失败自愈**只读变体**: 记录指向已完成/
          已删成员时不参与推断且不 pop(规则侧此处 pop, full_checking.py:146) —— 清理仍归规则侧
          与次日重置, 本判定零副作用铁律(T20) / 文件映射一致(group_sizes)。出路 = 对该组做
          full-checking 修数据。
        - partial(0<p<1): 预分配使文件尺寸=完整尺寸, filelist 尺寸检查无法发现未下载的零块,
          is_skip_checking 会把全部块标记有效 -> 零块被上传(垃圾数据)。仅 progress==0(全新辅种,
          数据完整)可跳检; full-checking 对部分下载安全, 不设限。
        - filelist: 前置文件检查, 调 check_filelist(checking.py:121 决策链 4 同一原语, 规则侧
          双查为计划明文接受); 失败语义 blocked(fail), 不是 skip; 映射 miss(路径不可判定)保守
          停住, 文案自带「修 fs.path_map 配置」出路。
        """
        verdicts: list = []
        progress = tor.progress
        state_enum = tor.state_enum

        # dedup 跨规则同日去重(排最前, 26-10-11-2045): 跳检成功 ⇒ 种子必为已完成 ⇒ G3 与 dedup
        # 恒同时成立, dedup 排后即被 G3 结构性遮蔽(执行路径取首个未过, 文案与 skip 类别被改写);
        # 只读判定(不 setdefault 不 prune), 前移零副作用(T20)
        skip_day = self.state.get("skip_check_day") or {}
        if skip_day.get(hash) == date.today().isoformat():
            verdicts.append(GateVerdict("dedup", GATE_BLOCKED, "今日已跳检过该种子(跨规则去重)"))

        # G3/G4 共用放行谓词 —— 逐字同 rules/actions/checking.py:88 决策链 0(两处注释互指):
        # 仅「暂停中未完成」放行; 做种态 p=1 落 G3/G5, 下载中等非 stopped 态 p<1 落 G4。
        # (当日已跳检的种子已被 dedup 先拦 —— G3 在此只对「已完成且当日未跳检」成判)
        paused_incomplete = state_enum.is_stopped and progress < 1.0
        evidence = self._checking_evidence(hash, tor)

        def g5_verdict() -> GateVerdict:
            """G5 同 hash 校验在途(case 2): 判决窗口抢跑是真不确定 —— 强制 = 杀死在途校验
            (已花 I/O 作废)且不经其判决断言数据有效; 用户明知本轮校验无意义(如误发起)时留逃生"""
            kind, age = evidence
            detail = f"state={tor.state}" if kind == "state" else "校验已提交, qB 状态尚未回流"
            return GateVerdict(
                "G5", GATE_FORCE, f"该种子正在全量校验({detail}{self._dur_text(age)}): 跳检会删除种子并使在途校验作废, "
                f"且不经其判决断言数据有效(若数据坏将被洗白); 确知本轮校验无意义时方可强制"
            )

        if not paused_incomplete:
            if progress >= 1.0:
                if evidence is not None:
                    # 已完成但在验(checkingUP): 必须走 G5 而不是 G3 —— 「已完成, 跳检无意义」在这里
                    # 是错话(它正在校验), 且 G3 是 blocked 无逃生, 会把「误发起的 recheck」堵死
                    verdicts.append(g5_verdict())
                else:
                    # G3 已完成: 数据已通过哈希校验, 跳检零收益纯损失(case 1, 用户点名项)
                    verdicts.append(
                        GateVerdict(
                            "G3", GATE_BLOCKED, f"种子已完成(progress={progress}): 数据已通过哈希校验, 跳检无任何意义, "
                            f"只会清零本地做种统计; 无需跳检"
                        )
                    )
            else:
                # G4 活跃中: 活跃且 p<1 = 下载中, 同部分下载的垃圾上传危害(case 1);
                # 出路 = 先暂停再跳检(暂停后 p=0 可过全部闸门, 不需要 force)
                verdicts.append(
                    GateVerdict(
                        "G4", GATE_BLOCKED, f"种子活跃中(state={tor.state}): 未暂停且未完成, 未验证块会被标有效并上传垃圾数据; "
                        f"请先暂停再跳检"
                    )
                )
        elif evidence is not None:
            # 暂停未完成但在验: qB 对停止态种子不报 checking*(updateState 的 checking_files
            # 分支要求 !isStopped), 状态上看不见 —— 只能靠证据(在途登记/快照)提示
            verdicts.append(g5_verdict())

        # G6 组内有活跃下载成员: 共享物理文件被下载方写入, force 也救不回确定性脏数据(case 1);
        # 出路 = 先暂停下载方(组内暂停后 G6 过, 流程合法)
        if self._ctx.store.group_has_downloading(hash):
            verdicts.append(
                GateVerdict("G6", GATE_BLOCKED, "组内有种子正在下载: 组内成员共享同一物理文件, 下载方正在写入, "
                            "跳检会把全部块标有效(脏数据); 请先暂停组内下载方再跳检")
            )

        # ---- G7/G8 组内镜像闸门(S1b-2): members 数据源与规则侧同一真相(checking.py:93
        # grouping._group_members 即委托 store.group_members), 谓词逐字镜像, 镜像注释互指在 ops 侧
        members = self._ctx.store.group_members(hash)
        others = [h for h in members if h != hash]

        # G7 组内其它成员 full-checking 在途(case 2): 与 G8 同口径 —— 只有**文件映射一致**的
        # 成员才参与(映射不同 = 校验的是另一份数据, 其判决与本次跳检的赌注无关; 组键
        # group_key_of 不含文件大小, 同路径不同大小的种子会落进同一组, 见 grouping_mod.py:49)。
        # 判定用 _checking_evidence(快照生效证据 ∪ 带 TTL 的在途登记), 不再用 state_enum.is_checking
        # —— 后者含 checkingResumeData(qB 启动/加种时的 resume data 比对, 通常几百 ms 内完成、
        # 批量加种还会排队, 且**不产生数据完整性判决**), 把它算作"在验"会让整组在 qB 重启期被挡。
        # 文案点名 blocker(hash8 + 名字 + state + 时长): 不点名时 N 个目标产出 N 条逐字相同的
        # 文案, 用户既不知道是谁在验、也无法去 qB 核对。
        key = self._ctx.store.member_to_key.get(hash)
        sizes = self._ctx.store.group_sizes.get(key, {}) if key is not None else {}
        mine = sizes.get(hash)
        for h in others:
            if mine and sizes.get(h) and sizes.get(h) != mine:
                continue  # 映射不一致: 不参与推断(对齐 G8 的 sizes.get(h) == mine)
            rec = self._ctx.store.get(h)
            ev = self._checking_evidence(h, rec)
            if ev is None:
                continue
            kind, age = ev
            detail = f"state={rec.state}" if kind == "state" and rec is not None else "校验已提交, qB 状态尚未回流"
            name = f"《{rec.name}》" if rec is not None and rec.name else ""
            verdicts.append(
                GateVerdict(
                    "G7", GATE_FORCE, f"同组种子 {h[:8]}{name}正在全量校验({detail}{self._dur_text(age)}): "
                    f"等其结束后再跳检, 校验通过即证明共享文件完好; 强制跳检将不经其判决断言数据有效, "
                    f"若判决为失败坏数据将被永久洗白"
                )
            )
            break  # 首个命中的 blocker 即成判(与 G8 同语义)

        # G8 组内成员校验失败推断(case 1): 四要件逐字镜像 rules/actions/full_checking.py
        # _skip_on_group_check_failed(决策链 1.6, others-only): 其它成员 / 当日计数(recheck_fails,
        # 含宽限耗尽/异常噪声 —— 继承规则侧既有假阳性面, 同日窗口+自愈条件兜底, 不发明更锐利谓词) /
        # 假失败自愈只读变体 / 文件映射一致。当日校验失败+同映射 = 数据已被证伪, 强制跳检 = 明知坏
        # 仍标有效并上传, force 无正当用途(「赌已输」与 G7 的「赌未定」有本质区别)
        # key / sizes / mine 与 G7 共用同一份组映射(上面已算), 不再各自重算
        if key is not None and mine:
            for h in members:
                if h == hash or recheck_fail_count(self._ctx.state, h) <= 0:
                    continue
                rec = self._ctx.store.get(h)
                if rec is None or rec.progress >= 1.0:
                    # 只读自愈(T20): 假失败记录不参与推断且**不 pop**(规则侧此处 pop 记录,
                    # full_checking.py:146) —— 清理仍归规则侧与次日重置, 本判定零副作用
                    continue
                if sizes.get(h) == mine:
                    verdicts.append(
                        GateVerdict(
                            "G8", GATE_BLOCKED, f"同组种子 {h[:8]} 今日校验失败且文件映射一致, "
                            "共享数据已证实有问题, 禁止跳检; 请先对该组做 full-checking"
                        )
                    )
                    break  # 同规则侧返回语义: 首个同映射失败成员即成判

        # partial 部分下载(既有闸门并入 detail, 文案零变化)
        if 0.0 < progress < 1.0:
            verdicts.append(
                GateVerdict("partial", GATE_BLOCKED, f"部分下载的种子禁止跳检(progress={progress}), 请改用 full-checking")
            )

        # filelist 前置文件检查(排最后): 前面已有 blocked 未过 -> 短路(结论已注定, 省 files API);
        # 仅 force 类未过不短路(force 豁越后本闸门仍须真跑)
        if not any(v.cls == GATE_BLOCKED for v in verdicts):
            err = self.check_filelist(self._ctx.api, tor)
            if err is not None:
                text = f"跳检前置文件检查未通过: {err}"
                if err.startswith("路径不可判定"):  # 与 check_filelist 的映射 miss 文案前缀同源(同模块单点)
                    text += "; 请修正 fs.path_map 配置后重试"
                verdicts.append(GateVerdict("filelist", GATE_BLOCKED, text))
        return verdicts
