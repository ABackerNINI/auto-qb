"""RM03 规则引擎漂移复测轮 —— 新增 8 条(W1-W5 新面 5 条 + checking 跳检/全量 3 条)。

验证面对准冻结计划 plans/26-11-01-1031-plan-real-machine-rm03-drift-plan.html §04 C/D 两组:
条件组合树 all/any/not(RM03-10)· choose 编排块(RM03-11)· 动作 on_error 三档(RM03-12)·
per-run trace(RM03-13)· 退役键面(RM03-14)· checking 全量段(RM03-15)· 分段选择(RM03-16)·
跳检四阶段+同日去重(RM03-17)。复测 8 条与 RM03-05 重写在 test_rm03_rules.py。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 退役键面(rules_mod.py:49-93): RETIRED_CONTROL_KEYS = (stop_following_rules_if,
  ignore_next_action_error); 载入即「转未启用(enabled=false)」+ 每次载入 WARNING
  「规则[全名] 含已退役控制键 … 转为未启用」, 启用数日志「加载规则 N 条(启用 M 条)」按实况断言;
- 条件求值出错新话术(base.py:718): ERROR「本条规则本轮跳过(条件求值出错)」(同因 300s 节流,
  节流键不含 hash —— 断言不咬该日志的 hash 归属, 归属证据走 per-run trace);
- on_error 三档(base.py:_dispatch_result): stop(缺省)ERROR「动作[x] 失败: …」后不再执行后续动作;
  continue WARNING「失败(continue, 继续后续动作)」后照跑; retry WARNING「失败(retry N/M, Xs 后重试)」
  + 任务级 requeue(retry_delay=backoff, 无 run 内 sleep), 耗尽 ERROR「重试 N 次仍失败, 中止本条动作链」;
- per-run trace(state.py:313 record_rule_trace): 键 rule_traces["{规则全名}:{hash}"], 每维环形
  _TRACE_KEEP_PER_DIM=5 条, 单条序列化 >2048 字节降级为 {ts,date,verdict,truncated} 存根;
  落盘随 state_save_interval/优雅退出 —— 涉 trace 断言的用例一律 graceful_after 起停(§2.10 口径);
  skip 级动作结果 INFO 日志不可见(DEBUG), skip 文案断言一律走 trace 不走日志;
- choose(base.py:_pick_choose_branch): 按序求 when 首中短路, 无命中走 default, 无 default 空操作;
  嵌套 choose 装载期 ConfigError(validation/rules.py allow_choose=False, dry-run 起程即验);
- checking 决策链(actions/checking.py:77-136): 0 只校验「暂停中未完成」/ 1 组内活跃下载整组跳过 /
  2 basic_check 参考筛选 / 3 有无参考分段 / 4 前置文件检查; full-checking 执行体 ops_mod.recheck
  (提交行「ops[rule] … full-checking 校验已提交」+ 成功行「校验成功」, 均 INFO);
  skip-checking 执行体 ops_mod.skip_submit 四阶段相位机(删除行「跳检删除种子(保留文件)」+
  完成行「跳检完成, 已打标签 <skip_checking_tag>」, 均 INFO; 无参考高风险告警「无参考跳检(高风险)」
  仅规则源 WARNING); 同日去重闸门文案「今日已跳检过该种子(跨规则去重)」(dedup, skip);
- 同组判据(grouping_mod.group_key_of): (规范化 save_path, 排序后文件相对路径元组) —— 同组造法 =
  同名同大小同 savepath 的多枚种子(grouping.enabled 必须开, 关着 store 组表为空);
  文件内容一致 + piece_len 不同 ⇒ infohash 不同(lib/torrent._make_torrent 的 info 只含
  name/length/piece length/pieces/private, announce 在 info 外不影响 infohash), 参考与目标
  共享同一物理文件且都能通过真校验;
- stalledDL 假种子(qbittorrentapi TorrentState 实测): is_downloading=True 且非 stopped ——
  构成决策链 1 的「活跃下载族」(D5 拍板: 判据是状态族谓词不认真速率, 零外连零真流量);
  落不了下载族该腿记 BLOCKED 不硬造。

造法校准(2026-11-01 执行段开工探针实测, qB 5.2.3; 计划预登记的两个未核事实按实况落定):
- /torrents/add 的 skip_checking 实测语义: +有数据 → 视为已完成(stoppedUP progress=1, 不校验);
  +无数据 → missingFiles —— 两形态都造不出「暂停中未完成」, 计划草案的 skip_checking 造法不成立;
- 「暂停中未完成」正确造法 = paused 加种 + 数据在场 + **不带** skip_checking → stoppedDL
  progress=0(qB 5.2.3 暂停加种只查 resume data 不做全量校验, 探针实测);
- stalledDL 活跃下载族造法 = 不暂停 + 无数据 + 不带 skip_checking(is_downloading=True 且
  amount_left>0, 谓词 _is_active_download 命中; skip_checking+无数据落 missingFiles 不算下载族);
- full-checking 证据闩(store 快照 1S 同步 + 2S 轮询)要求校验窗口 ≥3s: 实测 2GB 数据 recheck 的
  checkingDL 窗口 ~3s(0.43s→3.46s), 512MB 窗口毫秒级不可捕 —— RM03-15/16 的目标种子数据量取
  2GB(写盘 ~5s, 收尾 real.seed.clean 清), RM03-17 走跳检无证据窗维持 KB 级;
- 跳检重加(is_skip_checking+is_stopped)+数据在场 → progress=1(视为已完成): 成功跳检后的种子
  会被决策链 0 拦住, 同日去重闸永远走不到 —— RM03-17 的去重红验须先把目标种子删掉重加回
  「暂停中未完成」态(同 hash, paused+数据在场), 第二次触发才能穿透链 0 到闸门。

跑法: `commands run real.suite -- --slice RM03 --yes`(不要裸 pytest)。真实种子全程非活跃;
全部 L1 假种子(死端口 announce, 零外连); 假种子一律 real-fake 标签; 产品 data_dir 指用例临时
目录, 不碰仓库根 auto-qb-data/; 种子数据只落 tests-real/.work/rm03/。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import warnings
from pathlib import Path
from typing import Callable

import pytest
import yaml
from qbittorrentapi import TorrentState

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, instances, torrent  # noqa: E402
from lib.net import local_host  # noqa: E402
from lib.qb import QbError, _multipart  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(进程起停)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm03"
TAG = "real-fake"
SKIP_TAG = "zSkipChecked"  # config.skip_checking_tag 缺省值(models.py:570, 本轮不覆盖)
# full-checking 证据窗校准(探针实测, 见模块头注): 2GB → checkingDL ~3s, 能被 1S 快照+2S 轮询捕获
CHECK_DATA_SIZE = 2 * 1024 * 1024 * 1024
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}

# 假种子 announce 指本机死端口(零外连); 匹配按 hostname 不含端口, localhost 走本机 hosts 同样零外连
FAKE_HOST = local_host()
ANNOUNCE_IP = f"http://{FAKE_HOST}:1/announce"

RULESET = "rm03_rules"  # 规则集键: loaders.py 只认以 _rules 结尾的 config 顶层键

# ---------------------------------------------------------------- 基座(与 test_rm03_rules.py 同配方)


def qbfake():
    return instances.make(instances.SECONDARY)


def _tags_of(t) -> set[str]:
    """qB tags 字段的容错解析: 多标签「, 」连接, 一律 strip 后判成员(26-10-31-1215 用例侧防御)。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def wait_until(fn, timeout: float, desc: str | Callable[[], str], interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。

    desc 支持 str 或惰性 callable(超时构造报错时才求值): 调用点拼带「最后观测值」的
    f-string desc 必须传 lambda —— str 在调用期求值, 超时报错里显示的是等待前的旧值
    而非超时时刻实况(issue 26-11-08-0044, RM07-11 首版踩过)。
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc() if callable(desc) else desc}; 最后观测: {last}")


def settle(qb, ih: str, timeout: float = 30.0) -> dict:
    """等种子走完 check/alloc 拿到稳定态。"""
    deadline = time.time() + timeout
    t: dict = {}
    while time.time() < deadline:
        t = qb.torrent(ih) or {}
        if t.get("state") in SETTLED:
            return t
        time.sleep(0.3)
    return t


def log_text(case: Path) -> str:
    return app.read_log(case)


def count_anchor(case: Path, pattern: str) -> int:
    return len(re.findall(pattern, log_text(case)))


def assert_no_crash(case: Path) -> None:
    """通例负向守卫: 产品日志不得出现未捕获堆栈或「规则执行异常」。"""
    log = log_text(case)
    assert "Traceback" not in log, "产品日志出现未捕获异常堆栈"
    assert "规则执行异常" not in log, "产品日志出现「规则执行异常」(规则面抛了未捕获异常)"


def rule_traces(case: Path) -> dict:
    """state.json 里的 rule_traces(per-run trace, W4; 键 = {规则全名}:{hash},
    每维环形 5 条; 优雅退出/周期落盘时刷盘 —— 调用方须 graceful_after 起停)。"""
    p = case / "data" / "state.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("rule_traces") or {}


def purge_tree(root) -> None:
    root = Path(root)
    if not root.exists():
        return
    shutil.rmtree(root, ignore_errors=True)


def case_dir(name: str) -> Path:
    purge_tree(WORK / name)
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def rm_all_fakes(qb) -> list[str]:
    """删光 副实例 里本片自造的种子(连数据), 返回删掉的名字(证据用)。
    顺序 = 先删后摘标签(删失败时保留 real-fake 标记让下次清场还能看见它)。"""
    gone = []
    for t in qb.torrents():
        if TAG in _tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            try:
                qb.remove_tags(t["hash"], TAG)
            except Exception:  # noqa: BLE001 —— 种子已删时该调用无害失败
                pass
            gone.append(t["name"])
    if gone:
        wait_until(lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 15, f"清理后仍有 real-fake 残留: {gone}")
    return gone


def tracker_conf_entry(domains: list[str], rules: bool = True) -> dict:
    entry: dict = {"domains": list(domains)}
    if rules:
        entry["rules"] = [f"@{RULESET}"]
    return entry


def write_cfg(case: Path, trackers: dict, rule_sets: dict, *, grouping_enabled: bool = False) -> Path:
    """生成临时配置(schema_version: 6, 直连副实例)。rule_sets = {规则集名: {规则名: spec}}。"""
    cfg: dict = {
        "schema_version": 6,
        "qbittorrent": {
            "host": "127.0.0.1",
            "port": instances.SECONDARY,
            "username": "",
            "password": ""
        },
        "data_dir": (case / "data").as_posix(),
        "main_tick": "2S",
        "sync_interval": "1S",  # checking 面取证窗: 同步间隔压到下限附近, 缩小 checking 态漏采窗口
        "state_save_interval": "30S",
        "log": {
            "level": "INFO"
        },
        "grouping": {
            "enabled": grouping_enabled
        },
        "notify": {
            "enabled": False
        },
        "trackers": trackers,
    }
    cfg["web"] = {"enabled": False}
    cfg.update(rule_sets)
    # 产品 YAML 的根节点是 `config:`(RM04 CONFIG_TEMPLATE 同款), 全部键嵌在其下
    path = case / "config.yml"
    path.write_text(yaml.safe_dump({"config": cfg}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if f"port: {instances.PRIMARY}" in text:
        raise AssertionError(f"配置指向了 {instances.PRIMARY}(真实种子), 拒跑: {path}")
    if f"port: {instances.SECONDARY}" not in text:
        raise AssertionError(f"配置没指向副实例(空库草稿本), 拒跑: {path}")
    if "schema_version: 6" not in text:
        raise AssertionError(f"配置缺 schema_version: 6(会触发迁移改写), 拒跑: {path}")
    return path


def fake_seed(qb, name: str, size: int, savepath, salt: str, piece_len: int = torrent.PIECE_LEN) -> str:
    """造一枚 L1 假种子(无数据)并加入 副实例(带 real-fake 标签)。announce 缺省指本机死端口。"""
    savepath = Path(savepath)
    os.makedirs(savepath, exist_ok=True)  # savepath 得存在; 文件不写 ⇒ 永远 progress 0
    raw, ih = torrent.build_stream(name, size, "random", salt, ANNOUNCE_IP, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def _add_retry(qb, raw: bytes, savepath: str, ih: str, *, skip_checking: bool = False, paused: bool = False) -> None:
    """加种子, 409 双义处理(重复 infohash 一律删旧重加, 绝不收养, §2.9 第 2 条)。"""
    for attempt in range(4):
        try:
            _add_raw(qb, raw, savepath, ih, skip_checking=skip_checking, paused=paused)
            return
        except QbError as e:
            if "409" not in str(e):
                raise
            stale = qb.torrent(ih)
            if stale is None:
                time.sleep(1.5)  # 409 竞态落空型(未见副本): 稍候重试
                continue
            qb.delete(stale["hash"], delete_files=True)
            wait_until(lambda: qb.torrent(ih) is None, 15, f"409 同 infohash 旧副本删除未生效: {ih[:8]}")
    raise AssertionError(f"add 持续 409: {ih[:8]} @ {savepath}")


def _add_raw(qb, raw: bytes, savepath: str, ih: str, *, skip_checking: bool, paused: bool) -> None:
    """带 skip_checking 的原始加种(lib.qb.add_torrent 不支持该参数, 直发表单同款收据解析)。"""
    fields = {
        "savepath": savepath,
        "paused": "true" if paused else "false",
        "stopped": "true" if paused else "false",
        "tags": TAG,
    }
    if skip_checking:
        fields["skip_checking"] = "true"
    body, ctype = _multipart(fields, "torrents", "realqb.torrent", raw)
    resp = qb._call("/torrents/add", body, ctype).decode(errors="replace").strip()
    if resp.startswith("{"):
        try:
            receipt = json.loads(resp)
        except ValueError:
            raise QbError(f"add_torrent 收据不是合法 JSON: {resp[:120]!r}") from None
        if not receipt.get("success_count"):
            raise QbError(f"add_torrent 失败: {resp[:200]!r}")
    elif resp not in ("Ok.", ""):
        raise QbError(f"add_torrent 被拒: {resp!r}")
    if not paused:
        # 与 lib.qb.add_torrent 同款补 start(qB 5.2 传 paused=false 仍可能落 stopped 态)
        cur = qb.torrent(ih)
        if cur and cur["state"].startswith("stopped"):
            qb.resume(ih)


def group_pair_from_file(path, name: str) -> tuple[str, str, bytes, bytes]:
    """同一文件造两枚 infohash 不同的种子(参考+目标共享物理文件, 见模块头注):
    返回 (ih_ref, ih_target, raw_ref, raw_target)。"""
    raw_ref, ih_ref = torrent.build_from_path(str(path), name, ANNOUNCE_IP, torrent.PIECE_LEN)
    raw_tgt, ih_tgt = torrent.build_from_path(str(path), name, ANNOUNCE_IP, torrent.PIECE_LEN * 2)
    assert ih_ref != ih_tgt, "同文件双 piece_len 未产生不同 infohash(造法失效)"
    return ih_ref, ih_tgt, raw_ref, raw_tgt


def is_downloading_family(state: str) -> bool:
    """「活跃下载族」谓词(与 store.group_has_downloading 同口径): is_downloading 且非停止非校验。"""
    try:
        st = TorrentState(state)
    except ValueError:
        return False
    return bool(st.is_downloading) and not st.is_stopped and not st.is_checking


def trace_actions_of(traces: dict, rule_name: str, h: str) -> list:
    """某规则×种子 trace 维度里全部条目的 actions 明细(无维度返回空表)。"""
    dim = traces.get(f"{RULESET}.{rule_name}:{h}") or []
    return [a for e in dim for a in (e.get("actions") or [])]


# ================================================================ RM03-10


def test_rm03_10_condition_combo_tree():
    """[RM03-10] 条件组合树 all/any/not: 组合命中 + any 短路 + not 取反对照 + 扁平列表旧形态等价

    前置: 3 枚假种子(256K/512K/2MiB, 产品启动前入库); 四条规则 ——
          c10all={all:[size>=200KiB, size<=384KiB]} 只中 256K;
          c10any={any:[size<=384KiB, expr 除零]} 256K 首叶短路(不触 expr 错), 512K/2MiB 走到 expr 报错;
          c10not={not:{size<=384KiB}} 命中一切 >384KiB(B 与 C; 取反对照 = 256K 必须不得中,
          方向反了(退化为 size<=384KiB)则 A 中而 B/C 不中 —— 红验内建);
          c10flat=同 c10all 的扁平列表旧形态(W2-A 隐式 all 包裹, 行为必须与显式 all 一致)。
    副作用: 加 3 假种子; 打 rm03-all/rm03-any/rm03-not/rm03-flat 标签。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: all 任一叶假仍命中(AND 失效); not 方向反; 扁平与显式 all 行为不一致;
              any 短路失效(256K 的 trace 里出现 expr 叶/报错明细);
              执行段警告: D5 无关, 本条无外连面。
    注: 首跑假红复盘(官方第二轮): 原断言「rm03-not 只中 2MiB」数学上就错 —— not(size<=384KiB)
        对 512K 亦为真, 512K 本该被 not 命中(产品行为正确); 已按取反语义修正期望。
    """
    case = case_dir("rm03_10")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c10all":
                        {
                            "trigger": "interval",
                            "conditions": {
                                "all": [{
                                    "size": ">=200KiB"
                                }, {
                                    "size": "<=384KiB"
                                }]
                            },
                            "actions": [{
                                "add_tags": ["rm03-all"]
                            }],
                        },
                    "c10any":
                        {
                            "trigger": "interval",
                            "conditions": {
                                "any": [{
                                    "size": "<=384KiB"
                                }, {
                                    "expr": "(1 / 0) > 0"
                                }]
                            },
                            "actions": [{
                                "add_tags": ["rm03-any"]
                            }],
                        },
                    "c10not":
                        {
                            "trigger": "interval",
                            "conditions": {
                                "not": {
                                    "size": "<=384KiB"
                                }
                            },
                            "actions": [{
                                "add_tags": ["rm03-not"]
                            }],
                        },
                    "c10flat":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "size": ">=200KiB"
                            }, {
                                "size": "<=384KiB"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-flat"]
                            }],
                        },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_10"
        ha = fake_seed(qb, "rm03c10a.bin", 256 * 1024, savepath, "rm03c10-a")
        hb = fake_seed(qb, "rm03c10b.bin", 512 * 1024, savepath, "rm03c10-b")
        hc = fake_seed(qb, "rm03c10c.bin", 2 * 1024 * 1024, savepath, "rm03c10-c")
        settle(qb, ha)
        settle(qb, hb)
        settle(qb, hc)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case, graceful_after=25.0)  # trace 断言走优雅退出拿落盘账
        assert p.wait_log("加载规则 4 条(启用 4 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        wait_until(
            lambda: {"rm03-all", "rm03-any", "rm03-flat"} <= _tags_of(qb.torrent(ha) or {}),
            25,
            lambda: (f"A(256K)未按 all/any/flat 命中: {sorted(_tags_of(qb.torrent(ha) or {}))}"),
        )
        wait_until(
            lambda: "rm03-not" in _tags_of(qb.torrent(hb) or {}) and "rm03-not" in _tags_of(qb.torrent(hc) or {}),
            20,
            "B(512K)/C(2MiB)未被 not 规则命中(取反失效; not(size<=384KiB) 对一切 >384KiB 为真)",
        )
        time.sleep(8)  # ≥4 节拍: 负向窗口
        ta, tb, tc = (_tags_of(qb.torrent(h) or {}) for h in (ha, hb, hc))
        assert "rm03-not" not in ta, f"对照红验失效: A(256K)被 not 规则命中(取反方向反了): {sorted(ta)}"
        assert "rm03-all" not in tb and "rm03-flat" not in tb, f"对照红验失效: B(512K)被 all/flat 命中(AND 失效): {sorted(tb)}"
        assert "rm03-any" not in tb, f"B(512K)被 any 命中(首叶假第二叶除零报错不该有动作): {sorted(tb)}"
        assert "rm03-all" not in tc and "rm03-flat" not in tc, f"C(2MiB)被 all/flat 命中(上界叶失效): {sorted(tc)}"
        assert "rm03-any" not in tc, f"C(2MiB)被 any 命中(expr 报错不该有动作): {sorted(tc)}"
        assert not [t for t in tb if t.startswith("rm03-") and t != "rm03-not"], \
            f"B(512K)被 not 以外的规则打标: {sorted(tb)}"
        assert not [t for t in tc if t.startswith("rm03-") and t != "rm03-not"], \
            f"C(2MiB)被 not 以外的规则打标: {sorted(tc)}"

        rc = p.wait(90)
        p = None
        assert rc == 0, f"优雅退出非 0: {rc}\n{log_text(case)[-600:]}"

        # ---- 短路与求值明细(per-run trace): any 首叶真 = 只求一叶; 首叶假 = 走到 expr 并记 error
        traces = rule_traces(case)
        conds_a = [e.get("conditions") for e in (traces.get(f"{RULESET}.c10any:{ha}") or [])]
        assert conds_a and all(c == [{"c": "size", "r": True}] for c in conds_a), \
            f"A(256K)的 any 求值明细非单叶短路(短路失效): {conds_a[:2]}"
        conds_b = [e.get("conditions") for e in (traces.get(f"{RULESET}.c10any:{hb}") or [])]
        assert conds_b and any(
            isinstance(c, list) and len(c) == 2 and c[1].get("c") == "expr" and c[1].get("e") for c in conds_b
        ), f"B(512K)的 any 求值明细未走到 expr 叶(第二叶求值面失效): {conds_b[:2]}"
        verdicts_not = [e.get("verdict") for e in (traces.get(f"{RULESET}.c10not:{ha}") or [])]
        assert verdicts_not and all(v == "no_match" for v in verdicts_not), \
            f"A(256K)的 not 规则 trace verdict 非 no_match: {verdicts_not[:2]}"
        # 扁平列表旧形态与显式 all 行为等价(W2-A 兼容): 标签面已对照, trace 再对一次求值叶数
        conds_flat = [e.get("conditions") for e in (traces.get(f"{RULESET}.c10flat:{ha}") or [])]
        conds_all = [e.get("conditions") for e in (traces.get(f"{RULESET}.c10all:{ha}") or [])]
        assert conds_flat and conds_all and len(conds_flat[-1]) == len(conds_all[-1]) == 2, \
            f"扁平列表与显式 all 的求值明细不一致(W2-A 兼容回归): {conds_flat[-1]!r} vs {conds_all[-1]!r}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-11


def test_rm03_11_choose_block():
    """[RM03-11] choose 编排块: 分支首中短路 + default 兜底 + 无 default 空操作 + 嵌套拒绝(装载期红验)

    前置: 3 枚假种子(256K/640K/2MiB); c11choose 两分支(<=384KiB→a / >=1MiB→b)+default(→d);
          c11nodef 同分支无 default(640K 无命中 = 空操作); 装载期负向 = then 里嵌套 choose。
    副作用: 加 3 假种子; 打 rm03-cho-a/b/d 与 rm03-nd-a/b 标签。
    回滚: 删光 real-fake 种子 + 删用例目录(含装载期负向临时 case 目录)。
    失败判据: 多分支同中(首中短路失效, 一枚种子并发两 cho 标签); 640K 误走 a/b(条件错)或不走
              default(兜底失效); c11nodef 对 640K 报错或打标(空操作语义被破坏); 嵌套 choose 静默通过。
    """
    case = case_dir("rm03_11")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"

        # ---- 装载期红验: choose 内嵌套 choose 装载即被拒(独立 CLI, dry-run 起程即验, 不进主断言)
        case_bad = case_dir("rm03_11_load")
        bad_actions = [
            {
                "choose":
                    [
                        {
                            "when": {
                                "size": "<=1MiB"
                            },
                            "then": [{
                                "choose": [{
                                    "when": {
                                        "size": "<=1MiB"
                                    },
                                    "then": [{
                                        "add_tags": ["rm03-bad"]
                                    }]
                                }]
                            }]
                        }
                    ]
            }
        ]
        cfg_bad = write_cfg(
            case_bad, {"rm03fake": tracker_conf_entry([FAKE_HOST])},
            {RULESET: {
                "c11bad": {
                    "trigger": "interval",
                    "actions": bad_actions
                }
            }}
        )
        r = app.run_cli([str(cfg_bad), "--dry-run"], timeout=60)
        sinks = (r.stdout or "") + (r.stderr or "") + log_text(case_bad)
        assert r.returncode != 0, f"装载期红验失效: 嵌套 choose 被静默通过(rc=0):\n{sinks[-500:]}"
        assert "c11bad" in sinks and "choose" in sinks, f"装载期拒绝但输出缺规则名/choose 锚点:\n{sinks[-600:]}"
        purge_tree(case_bad)

        # ---- 主现场: 首中短路 + default 兜底 + 无 default 空操作
        rules = {
            RULESET:
                {
                    "c11choose":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "choose":
                                            [
                                                {
                                                    "when": {
                                                        "size": "<=384KiB"
                                                    },
                                                    "then": [{
                                                        "add_tags": ["rm03-cho-a"]
                                                    }]
                                                },
                                                {
                                                    "when": {
                                                        "size": ">=1MiB"
                                                    },
                                                    "then": [{
                                                        "add_tags": ["rm03-cho-b"]
                                                    }]
                                                },
                                            ],
                                        "default": [{
                                            "add_tags": ["rm03-cho-d"]
                                        }],
                                    }
                                ],
                        },
                    "c11nodef":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "choose":
                                            [
                                                {
                                                    "when": {
                                                        "size": "<=384KiB"
                                                    },
                                                    "then": [{
                                                        "add_tags": ["rm03-nd-a"]
                                                    }]
                                                },
                                                {
                                                    "when": {
                                                        "size": ">=1MiB"
                                                    },
                                                    "then": [{
                                                        "add_tags": ["rm03-nd-b"]
                                                    }]
                                                },
                                            ]
                                    }
                                ],
                        },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_11"
        ha = fake_seed(qb, "rm03c11a.bin", 256 * 1024, savepath, "rm03c11-a")
        hm = fake_seed(qb, "rm03c11m.bin", 640 * 1024, savepath, "rm03c11-m")
        hc = fake_seed(qb, "rm03c11c.bin", 2 * 1024 * 1024, savepath, "rm03c11-c")
        for h in (ha, hm, hc):
            settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 2 条(启用 2 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        wait_until(lambda: "rm03-cho-a" in _tags_of(qb.torrent(ha) or {}), 25, "A(256K)未命中首分支(分支条件/求值失效)")
        wait_until(lambda: "rm03-cho-d" in _tags_of(qb.torrent(hm) or {}), 20, "M(640K)未走 default 兜底(两分支皆不中)")
        wait_until(lambda: "rm03-cho-b" in _tags_of(qb.torrent(hc) or {}), 20, "C(2MiB)未命中第二分支")
        wait_until(lambda: "rm03-nd-a" in _tags_of(qb.torrent(ha) or {}), 15, "无 default 规则的命中腿失效")
        time.sleep(8)  # ≥4 节拍: 短路与空操作负向窗口
        ta, tm, tc = (_tags_of(qb.torrent(h) or {}) for h in (ha, hm, hc))
        assert "rm03-cho-b" not in ta and "rm03-cho-d" not in ta, \
            f"首中短路失效: A(256K)并发多分支标签: {sorted(ta)}"
        assert "rm03-cho-a" not in tc and "rm03-cho-d" not in tc, f"C(2MiB)并发多分支标签: {sorted(tc)}"
        assert not [t for t in tm if t.startswith("rm03-cho-") and t != "rm03-cho-d"], \
            f"M(640K)误入分支(只该走 default): {sorted(tm)}"
        assert not [t for t in tm if t.startswith("rm03-nd-")], \
            f"空操作语义被破坏: 无 default 且无命中的 M(640K)被打标: {sorted(tm)}"
        assert "rm03-nd-b" in tc and "rm03-nd-a" not in tc, f"无 default 规则在 C 上分支错乱: {sorted(tc)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(WORK / "rm03_11_load")


# ================================================================ RM03-12


def test_rm03_12_on_error_policies():
    """[RM03-12] 动作 on_error 三档: stop(缺省)止住后续动作 / continue 后续照跑 / retry requeue 后耗尽按 stop 收场

    前置: 1 枚假种子; 必败动作 = move_to 指向空路径(transfer.py:28 装载后运行即 fail
          「move_to.path 为空」, 不触 qB 零副作用); 三条规则各 [必败 move_to, add_tags]:
          c12stop 缺省 / c12cont on_error{policy: continue} / c12retry on_error{policy: retry,
          retries: 1, backoff: 2}。
    副作用: 加 1 假种子; 只出现 rm03-oe-continue 标签; 产品日志 requeue/耗尽行。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: stop 下后续动作照跑(缺省止损失效, rm03-oe-stop 出现); continue 下后续不跑
              (rm03-oe-continue 缺失 —— 对照腿坏了即红); retry 无 requeue 痕迹或不耗尽收场
              (rm03-oe-retry 出现 = 重试后动作误执行, 无限重试 = 高优 FAIL)。
    """
    case = case_dir("rm03_12")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"

        def _rule(tag: str, on_error: dict | None) -> dict:
            move = {"move_to": {"path": ""}}
            if on_error is not None:
                move["on_error"] = on_error
            return {"trigger": "interval", "actions": [move, {"add_tags": [tag]}]}

        rules = {
            RULESET:
                {
                    "c12stop": _rule("rm03-oe-stop", None),
                    "c12cont": _rule("rm03-oe-continue", {"policy": "continue"}),
                    "c12retry": _rule("rm03-oe-retry", {
                        "policy": "retry",
                        "retries": 1,
                        "backoff": 2
                    }),
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_12"
        h = fake_seed(qb, "rm03c12.bin", 256 * 1024, savepath, "rm03c12")
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 3 条(启用 3 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # ---- continue 对照腿: 失败后后续动作照跑(这条腿坏了, 对照即红)
        wait_until(
            lambda: "rm03-oe-continue" in _tags_of(qb.torrent(h) or {}), 25, "continue 档后续 add_tags 未执行(后续照跑语义失效)"
        )
        assert count_anchor(case, r"动作\[move_to\] 失败\(continue, 继续后续动作\)") >= 1, \
            "continue 档缺「失败(continue, 继续后续动作)」WARNING"
        # ---- retry 档: requeue 痕迹 + 耗尽收场
        wait_until(
            lambda: count_anchor(case, r"动作\[move_to\] 失败\(retry 1/1, 2s 后重试\)") >= 1, 25,
            "retry 档无「失败(retry 1/1, 2s 后重试)」requeue WARNING"
        )
        wait_until(
            lambda: count_anchor(case, r"动作\[move_to\] 失败\(重试 1 次仍失败, 中止本条动作链\)") >= 1, 30,
            "retry 档无「重试 1 次仍失败, 中止本条动作链」耗尽 ERROR"
        )
        # ---- stop 档(缺省): 失败行在, 后续动作永不跑
        assert count_anchor(case, r"规则\[rm03_rules\.c12stop\].*动作\[move_to\] 失败: ") >= 1, \
            "stop 档缺「动作[move_to] 失败」ERROR(必败动作没失败, 前提不成立)"
        time.sleep(12)  # ≥6 节拍: 若止损失效/重试误执行, 标签必然出现
        tags = _tags_of(qb.torrent(h) or {})
        assert "rm03-oe-stop" not in tags, f"对照红验失效: stop(缺省)档后续动作照跑: {sorted(tags)}"
        assert "rm03-oe-retry" not in tags, f"retry 档重试后动作被误执行(耗尽未收场): {sorted(tags)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-13


def test_rm03_13_rule_trace_state_surface():
    """[RM03-13] per-run trace: state.json rule_traces 键面(全名:hash 键 / 环形 5 条 / 超长条目 2KiB 截断)

    前置: 1 枚假种子; c13small = 常规规则(add_tags, 每轮一条 trace); c13big = 30 个
          print_torrent_details 动作(单条 trace 明细体积超 2048 字节, 触发 state 层截断存根);
          产品 graceful_after 起停拿落盘账(§2.10 exec_history 同款, 不硬等 30S 周期)。
    副作用: 产品 data_dir(用例临时目录)落 trace 账; 1 假种子 + 1 标签。
    回滚: 删临时 data_dir + 删光 real-fake 种子 + 删用例目录。
    失败判据: 键名不含规则全名/hash; 常规维度条目无 verdict/条件/动作结构; 条目数无界(>5, 环形失效);
              超长条目未被截断(2KiB 兜底失效)或截断存根丢了 verdict。
    注: trace 保留期 prune(7 天)口径跨天造不出 —— 由单测覆盖, 本条只记账不断言(计划预登记)。
    """
    case = case_dir("rm03_13")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c13small":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "size": "<=1MiB"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-tr"]
                            }],
                        },
                    "c13big": {
                        "trigger": "interval",
                        "actions": [{
                            "print_torrent_details": True
                        }] * 30,
                    },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_13"
        h = fake_seed(qb, "rm03c13.bin", 256 * 1024, savepath, "rm03c13")
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case, graceful_after=25.0)  # ≥12 个节拍: 环形逐出可见
        assert p.wait_log("加载规则 2 条(启用 2 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"
        wait_until(lambda: "rm03-tr" in _tags_of(qb.torrent(h) or {}), 25, "c13small 未命中(命中面前提不成立)")
        rc = p.wait(90)
        p = None
        assert rc == 0, f"优雅退出非 0: {rc}\n{log_text(case)[-600:]}"

        traces = rule_traces(case)
        small_key = f"{RULESET}.c13small:{h}"
        big_key = f"{RULESET}.c13big:{h}"
        assert small_key in traces, f"rule_traces 无全名键 {small_key}(键面/前缀失效): {sorted(traces)[:5]}"
        dim = traces[small_key]
        assert 1 <= len(dim) <= 5, f"trace 维度条目数 {len(dim)} 越界(环形 5 条失效)"
        for e in dim:
            assert e.get("verdict") in ("executed", "no_op"), f"常规 trace verdict 异常: {e.get('verdict')!r}"
            assert isinstance(e.get("conditions"), list) and e["conditions"], "常规 trace 缺条件求值明细"
            assert e["conditions"][-1].get("c") == "size", f"条件明细不含条件名: {e['conditions']}"
            assert e.get("actions") and e["actions"][-1].get("name") == "add_tags", "动作明细缺 add_tags 步"
            assert "ts" in e and "date" in e, "trace 条目缺 ts/date(排序字段)"
            assert e.get("truncated") is not True, "常规条目被误截断"
        # 超长条目: state 层 2KiB 字节兜底 → 截断存根(保留 verdict 与排序字段)
        assert big_key in traces, f"rule_traces 无 {big_key}"
        big = traces[big_key]
        assert big, "c13big trace 维度为空(30 动作规则没执行)"
        stub = big[-1]
        assert stub.get("truncated") is True, f"超长条目未被截断(2KiB 兜底失效): {sorted(stub)}"
        assert set(stub) <= {"ts", "date", "verdict", "truncated"}, f"截断存根带出了未截断明细: {sorted(stub)}"
        assert stub.get("verdict") == "executed", f"截断存根丢了 verdict: {stub.get('verdict')!r}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-14


def test_rm03_14_retired_control_keys():
    """[RM03-14] 退役键面: 含 stop_following_rules_if / ignore_next_action_error 的规则载入转未启用 + 零执行

    前置: 1 枚命中的假种子; 三条条件/动作同源的规则 —— c14ret 带规则级 stop_following_rules_if,
          c14ign 的 actions 带伪动作 ignore_next_action_error, c14ok 干净对照; 全部启动前入库。
    副作用: 加 1 假种子; 只有对照规则打 rm03-ok 标签。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: 甲照样执行(退役面失效, 高优 —— rm03-retired/rm03-ign 标签出现);
              无 WARNING(静默吞 —— 日志缺「含已退役控制键」结构化锚点);
              启用数 ≠1(载入层误伤合法规则或没拦住); 对照规则也没执行(载入层误伤)。
    """
    case = case_dir("rm03_14")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c14ret":
                        {
                            "trigger": "interval",
                            "stop_following_rules_if": "always",
                            "conditions": [{
                                "size": "<=1MiB"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-retired"]
                            }],
                        },
                    "c14ign":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "size": "<=1MiB"
                            }],
                            "actions": [{
                                "ignore_next_action_error": True
                            }, {
                                "add_tags": ["rm03-ign"]
                            }],
                        },
                    "c14ok":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "size": "<=1MiB"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-ok"]
                            }],
                        },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_14"
        h = fake_seed(qb, "rm03c14.bin", 256 * 1024, savepath, "rm03c14")
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 3 条(启用 1 条)", 40), \
            f"启用数不对(退役键没拦住或误伤合法规则):\n{p.log()[-800:]}"
        # WARNING 结构化锚点(R8: 咬「含已退役控制键」+ 全名, 不咬整句措辞)
        assert count_anchor(case, r"规则\[rm03_rules\.c14ret\] 含已退役控制键 stop_following_rules_if") >= 1, \
            "c14ret 缺退役键 WARNING(静默吞)"
        assert count_anchor(case, r"规则\[rm03_rules\.c14ign\] 含已退役控制键 ignore_next_action_error") >= 1, \
            "c14ign 缺伪动作 WARNING(静默吞)"

        wait_until(lambda: "rm03-ok" in _tags_of(qb.torrent(h) or {}), 25, "对照规则 c14ok 未命中(载入层误伤合法规则)")
        time.sleep(9)  # ≥4 节拍: 退役面失效的话标签必然出现
        tags = _tags_of(qb.torrent(h) or {})
        assert "rm03-retired" not in tags, f"对照红验失效: 含退役键规则照样执行: {sorted(tags)}"
        assert "rm03-ign" not in tags, f"对照红验失效: 含伪动作规则照样执行: {sorted(tags)}"
        assert count_anchor(case, r"规则\[rm03_rules\.c14ret\].*动作\[add_tags\] 成功") == 0, \
            "日志出现退役规则的 add_tags 成功行(转未启用失效)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-15


def test_rm03_15_full_checking_submit_and_gates():
    """[RM03-15] checking 全量段: recheck 提交+轮询+成功; 决策链 0/1 闸门红验(已完成对照 / 组内活跃下载)

    前置: grouping 开; 同组两枚假种子(A=参考: 带数据非暂停加种即校验完成; B=目标: paused+数据
          在场加种 → stoppedDL progress=0 未校验, 与 A 同文件同大小故同组且能真校验通过, 数据 2GB
          保证据窗) + 独立第二组(D=不暂停无数据 → 预期落活跃下载族 stalledDL; Bz=同组 paused
          无数据目标); 规则 checking basic_check=filelist, with_reference 段 mode=full-checking。
    副作用: B 被真 recheck(qB 校验读盘, 2GB 级数秒)并完成; .work 落种子数据。
    回滚: 删光 real-fake 种子(连数据)+ 删用例目录。
    失败判据: recheck 从未提交(无 ops[rule] 提交/成功行且 B progress 不动); 已完成对照 A 被真校验
              (决策链 0 失效 —— A 的 trace 动作不是 skip「种子非暂停中未完成状态」); 校验结果无证据
              背书被误判成功(证据门控失效); Bz 未被「组内有种子正在下载」拦下(决策链 1 失效)。
    造法注记: skip_checking 加种实测造不出「暂停中未完成」(+数据=视为已完成, 无数据=missingFiles,
              见模块头注探针校准) —— 目标态一律 paused+数据在场; D 腿(D5)是状态族谓词, stalledDL
              假种子落不了下载族时该腿记 BLOCKED(warn)不硬造。
    """
    case = case_dir("rm03_15")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c15chk":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "checking":
                                            {
                                                "basic_check": "filelist",
                                                "with_reference": {
                                                    "enabled": True,
                                                    "mode": "full-checking"
                                                },
                                            }
                                    }
                                ],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        # ---- 组1: 参考 A(带数据非暂停, 加种即校验完成) + 目标 B(paused+数据在场 → stoppedDL
        #      progress=0), 同文件 ⇒ 同组。造法校准: paused 加种不自动校验, 数据量 2GB 保证证据窗
        savepath = WORK / "rm03_15"
        f1 = torrent.write_file(str(savepath / "rm03c15.bin"), CHECK_DATA_SIZE, "random", "rm03c15")
        ih_a, ih_b, raw_a, raw_b = group_pair_from_file(f1, "rm03c15.bin")
        _add_retry(qb, raw_a, str(savepath), ih_a)  # 非暂停+数据: qB 加种即校验 → 完成(参考种子)
        settle(qb, ih_a)
        assert (qb.torrent(ih_a) or {}).get("progress") == 1.0, "参考种子 A 未完成(带数据假种子校验失效)"
        _add_retry(qb, raw_b, str(savepath), ih_b, paused=True)
        time.sleep(2)
        tb = qb.torrent(ih_b) or {}
        assert tb.get("progress", 1.0) < 1.0, f"目标 B 加种即完成(暂停加种造法失效): state={tb.get('state')}"
        # ---- 组2: 下载者 D(不暂停+无数据, 预期 stalledDL 活跃下载族) + 目标 Bz(paused+无数据)
        f2 = torrent.write_file(str(savepath / "rm03c15d.bin"), 128 * 1024, "random", "rm03c15d")
        ih_d, ih_bz, raw_d, raw_bz = group_pair_from_file(f2, "rm03c15d.bin")
        os.remove(f2)  # 组2 不落数据: D 不暂停无数据 → stalledDL(下载族); skip_checking+无数据=missingFiles 反而不算
        _add_retry(qb, raw_d, str(savepath), ih_d, paused=False)
        _add_retry(qb, raw_bz, str(savepath), ih_bz, paused=True)
        dl_state = None
        deadline = time.time() + 25.0
        while time.time() < deadline:  # 落不了下载族该腿降级 BLOCKED(warn), 不让它炸整条用例(D5)
            st = (qb.torrent(ih_d) or {}).get("state") or ""
            if is_downloading_family(st):
                dl_state = st
                break
            time.sleep(1.0)

        cfg = write_cfg(case, trackers, rules, grouping_enabled=True)
        p = app.start(cfg, case, graceful_after=70.0)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # ---- 正向: B 被提交 recheck 且校验完成(API 回读 progress + ops[rule] 两行 INFO)
        wait_until(lambda: (qb.torrent(ih_b) or {}).get("progress", 0) >= 1.0, 60, "B 未被真校验完成(recheck 未提交或未生效)")
        assert count_anchor(case, rf"ops\[rule\].*\({ih_b[:8]}\).*full-checking 校验已提交") >= 1, \
            "B 缺「full-checking 校验已提交」提交行"
        # 成功行要等产品的证据轮询落账(2S 一跳, 见 seen_checking 才下 SUCCESS): progress=1.0 的
        # qB 直读会跑赢它 1-3s, 这里必须 wait_until 不能 assert(官方第二轮假红复盘)
        wait_until(
            lambda: count_anchor(case, rf"ops\[rule\].*\({ih_b[:8]}\).*校验成功") >= 1,
            30,
            "B 缺「校验成功」行(轮询未按证据门控收口)",
        )
        assert SKIP_TAG not in _tags_of(qb.torrent(ih_b) or {}), "B 被打跳检标签(走错分段: 该走 full-checking)"

        rc = p.wait(120)
        p = None
        assert rc == 0, f"优雅退出非 0: {rc}\n{log_text(case)[-600:]}"

        # ---- 决策链 0 红验: 已完成的 A 必须 skip「种子非暂停中未完成状态」(trace 文案, skip 不进 INFO 日志)
        traces = rule_traces(case)
        acts_a = trace_actions_of(traces, "c15chk", ih_a)
        assert acts_a and all(
            a.get("st") == "skipped" and "种子非暂停中未完成状态" in (a.get("msg") or "") for a in acts_a
        ), f"决策链 0 失效: 已完成对照 A 的 trace 动作非 skip 文案: {acts_a[:2]}"
        # ---- 决策链 1 红验(D5 腿): 组内有活跃下载 → 整组跳过
        if is_downloading_family(dl_state or ""):
            acts_bz = trace_actions_of(traces, "c15chk", ih_bz)
            assert acts_bz and any("组内有种子正在下载" in (a.get("msg") or "") for a in acts_bz), \
                f"决策链 1 失效: 组内有活跃下载未整组跳过: {acts_bz[:2]}"
        else:
            warnings.warn(
                f"[RM03-15][BLOCKED-腿] stalledDL 假种子未构成活跃下载族(state={dl_state!r}), "
                "决策链 1 红验腿记 BLOCKED(D5: 不为它开 L2 互传)",
                stacklevel=1,
            )
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-16


def test_rm03_16_reference_segment_selection():
    """[RM03-16] checking 分段选择: 有参考 → with_reference(full-checking) / 无参考 → without_reference(skip-checking)

    前置: grouping 开; 一条 checking 规则两段都配且 mode 可区分 —— 组1: A1(带数据非暂停加种
          即校验完成, 参考)+ B1(paused+数据在场加种 → stoppedDL progress=0, 数据 2GB 保证证据窗)
          同组 → B1 应走 with_reference(full-checking, 校验完成); 组2: C1 单独成组(同大小文件在盘,
          paused 加种 → stoppedDL progress=0, 无其它成员)→ C1 走 without_reference(skip-checking,
          真删重加 + zSkipChecked 标签 + 仅规则源的「无参考跳检(高风险)」告警)。
    副作用: B1 被真 recheck; C1 被真删除重加(keep 文件); .work 落种子数据。
    回滚: 删光 real-fake 种子(连数据)+ 删用例目录。
    失败判据: 有无参考两轮走同一段(参考判定失效 —— B1 拿到 zSkipChecked 或 C1 被真校验完成);
              无参考轮缺「无参考跳检(高风险)」告警; C1 重加后种子丢失或文件被真删。
    造法注记: skip_checking 加种实测造不出「暂停中未完成」(见模块头注探针校准) —— 目标态一律
              paused+数据在场。
    """
    case = case_dir("rm03_16")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c16seg":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "checking":
                                            {
                                                "basic_check": "filelist",
                                                "with_reference": {
                                                    "enabled": True,
                                                    "mode": "full-checking"
                                                },
                                                "without_reference": {
                                                    "enabled": True,
                                                    "mode": "skip-checking"
                                                },
                                            }
                                    }
                                ],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_16"
        # ---- 组1(有参考): A1 完成(非暂停加种即校验) + B1 暂停未完成(paused+数据在场, 2GB 保证证据窗)
        f1 = torrent.write_file(str(savepath / "rm03c16a.bin"), CHECK_DATA_SIZE, "random", "rm03c16a")
        ih_a1, ih_b1, raw_a1, raw_b1 = group_pair_from_file(f1, "rm03c16a.bin")
        _add_retry(qb, raw_a1, str(savepath), ih_a1)
        settle(qb, ih_a1)
        assert (qb.torrent(ih_a1) or {}).get("progress") == 1.0, "参考 A1 未完成"
        _add_retry(qb, raw_b1, str(savepath), ih_b1, paused=True)
        # ---- 组2(无参考): C1 单枚, 文件在盘(paused+数据 → stoppedDL progress=0), 组内无其它成员
        f2 = torrent.write_file(str(savepath / "rm03c16b.bin"), 128 * 1024, "random", "rm03c16b")
        raw_c1, ih_c1 = torrent.build_from_path(f2, "rm03c16b.bin", ANNOUNCE_IP, torrent.PIECE_LEN)
        _add_retry(qb, raw_c1, str(savepath), ih_c1, paused=True)
        time.sleep(2)
        assert (qb.torrent(ih_c1) or {}).get("progress", 1.0) < 1.0, "C1 加种即完成(skip_checking 造法失效)"

        cfg = write_cfg(case, trackers, rules, grouping_enabled=True)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # ---- 轮1: B1 有参考 → full-checking(校验完成, 不打跳检标签)
        wait_until(lambda: (qb.torrent(ih_b1) or {}).get("progress", 0) >= 1.0, 60, "B1 未被真校验完成(有参考段失效)")
        assert count_anchor(case, rf"ops\[rule\].*\({ih_b1[:8]}\).*full-checking 校验已提交") >= 1, "B1 缺 recheck 提交行"
        assert SKIP_TAG not in _tags_of(qb.torrent(ih_b1) or {}), \
            "对照红验失效: B1 被跳检(有参考却走了 without_reference 段, 参考判定失效)"
        # ---- 轮2: C1 无参考 → skip-checking(真删重加, 同 hash, zSkipChecked 标签)
        wait_until(lambda: SKIP_TAG in _tags_of(qb.torrent(ih_c1) or {}), 60, "C1 未打跳检标签(无参考段未执行或四阶段未走完)")
        assert qb.torrent(ih_c1) is not None, "C1 重加后不在库(删除后重加失败)"
        assert (savepath / "rm03c16b.bin").is_file(), "灾难: C1 的数据文件被真删(跳检必须保留文件)"
        assert count_anchor(case, rf"ops\[rule\].*\({ih_c1[:8]}\).*无参考跳检\(高风险\)") == 1, \
            "无参考高风险告警缺失或重复(仅规则源且仅无参考轮该有)"
        assert count_anchor(case, rf"ops\[rule\].*\({ih_b1[:8]}\).*无参考跳检") == 0, "B1(有参考)误发无参考告警"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-17


def test_rm03_17_skip_checking_phases_and_dedup():
    """[RM03-17] checking 跳检段: 四阶段真删重加(同 hash/文件保留/打标/当日记账)+ 同日去重红验

    前置: grouping 开; 同组 A(带数据非暂停加种即校验完成, 参考)+ B(paused+数据在场加种 →
          stoppedDL progress=0 暂停未完成目标, 文件在盘); with_reference 段 mode=skip-checking。
          高风险动作面 —— 只对 real-fake 自造种子执行, 绝不碰真实种子(环境2 主实例真实种子 0 枚,
          guard 快照计数为证)。
    副作用: B 被真删除重加(keep 文件); 备份产物(成功即清); zSkipChecked 标签; state skip_check_day
          记账; 去重红验段 B 被测试侧删掉重加一次(keep 文件, 造回目标态)。
    回滚: 删光 real-fake 种子(连数据)+ 清 skip_checking_tag 标签残留 + 删用例目录。
    失败判据: 灾难级: 数据文件被真删(文件不在)→ 本条 FAIL 现场留档入池; 种子重加后不在库;
              去重失效(同日第二次又真跑四阶段 —— 「跳检删除种子」行 >1); skip 标签未打;
              state 无 skip_check_day 当日记账。
    造法注记: 跳检重加(is_skip_checking+is_stopped)+数据在场 → progress=1(视为已完成), 成功跳检
          后的种子被决策链 0 拦住, 去重闸走不到 —— 去重红验前置: 首跳完成后把 B 删掉重加回
          「暂停中未完成」态(同 hash, paused+数据在场), 第二次触发才能穿透链 0 到闸门(模块头注)。
    """

    case = case_dir("rm03_17")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "c17skip":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "checking":
                                            {
                                                "basic_check": "filelist",
                                                "with_reference": {
                                                    "enabled": True,
                                                    "mode": "skip-checking"
                                                },
                                            }
                                    }
                                ],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_17"
        data_file = savepath / "rm03c17.bin"
        f1 = torrent.write_file(str(data_file), 256 * 1024, "random", "rm03c17")
        ih_a, ih_b, raw_a, raw_b = group_pair_from_file(f1, "rm03c17.bin")
        _add_retry(qb, raw_a, str(savepath), ih_a)
        settle(qb, ih_a)
        assert (qb.torrent(ih_a) or {}).get("progress") == 1.0, "参考 A 未完成"
        _add_retry(qb, raw_b, str(savepath), ih_b, paused=True)  # paused+数据在场 → stoppedDL progress=0
        time.sleep(2)
        assert (qb.torrent(ih_b) or {}).get("progress", 1.0) < 1.0, "B 加种即完成(暂停加种造法失效)"

        cfg = write_cfg(case, trackers, rules, grouping_enabled=True)
        p = app.start(cfg, case, graceful_after=35.0)  # 窗口覆盖首跳四阶段 + 第二次触发撞去重
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # ---- 首跳四阶段: 删除行 → 重加完成(同 hash 在库 + 文件保留 + 跳检标签)
        wait_until(
            lambda: count_anchor(case, rf"ops\[rule\].*\({ih_b[:8]}\).*跳检删除种子\(保留文件\)") >= 1, 40, "跳检未进入删除阶段(四阶段未启动)"
        )
        wait_until(lambda: SKIP_TAG in _tags_of(qb.torrent(ih_b) or {}), 40, "跳检完成标签未打(四阶段未收尾)")
        assert qb.torrent(ih_b) is not None, "B 重加后不在库(非同种子重加)"
        assert data_file.is_file(), "灾难: 数据文件被真删(跳检必须保留文件) —— 立即停手留档入池"
        assert count_anchor(case, rf"ops\[rule\].*\({ih_b[:8]}\).*跳检完成, 已打标签 {SKIP_TAG}") >= 1, \
            "缺「跳检完成, 已打标签」行"
        # 同日记账(ops 收尾即时落盘, 不等优雅退出)
        wait_until(
            lambda: (lambda d: (d.get("skip_check_day") or {}).get(ih_b) == time.strftime("%Y-%m-%d"))
            (_state_payload(case)),
            15,
            "state.json 无 skip_check_day 当日记账",
        )
        # ---- 去重红验前置: 首跳重加(skip_checking)后 B progress=1, 决策链 0 会先拦, 去重闸走不到
        #      (造法校准, 见模块头注) —— 删掉重加回「暂停中未完成」态(同 hash, paused+数据在场)
        qb.delete(ih_b, delete_files=False)  # 保留数据文件
        wait_until(lambda: qb.torrent(ih_b) is None, 15, "去重前置: B 删除未生效")
        _add_retry(qb, raw_b, str(savepath), ih_b, paused=True)
        assert (qb.torrent(ih_b) or {}).get("progress", 1.0) < 1.0, "去重前置: B 重加回未完成态失败"
        time.sleep(10)  # 第二次触发窗口: 穿透链 0 → 闸门撞同日去重

        rc = p.wait(90)
        p = None
        assert rc == 0, f"优雅退出非 0: {rc}\n{log_text(case)[-600:]}"

        # ---- 去重红验: 同日第二次触发必须 skip「今日已跳检过」, 绝不再真跑四阶段
        n_del = count_anchor(case, rf"ops\[rule\].*\({ih_b[:8]}\).*跳检删除种子\(保留文件\)")
        assert n_del == 1, f"去重失效: 同日第二次又真跑四阶段(删除行 {n_del} 条)"
        traces = rule_traces(case)
        acts_b = trace_actions_of(traces, "c17skip", ih_b)
        assert any(a.get("st") == "skipped" and "今日已跳检过" in (a.get("msg") or "") for a in acts_b), \
            f"去重 skip 文案未进 trace(skip 面或去重闸失效): {acts_b[-2:]}"
        # 备份产物收尾清零(成功路径 _clear_backup)
        st = _state_payload(case)
        assert not (st.get("skip_check_backup") or {}), f"跳检备份元数据残留: {sorted(st.get('skip_check_backup') or {})}"
        backup_dir = case / "data" / "skip-check-backup"
        assert not backup_dir.exists() or not any(backup_dir.iterdir()), "跳检备份目录残留产物"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        qb2 = qbfake()
        gone = rm_all_fakes(qb2)
        if not gone:  # real-fake 失明兜底(26-10-31-1215): 按 hash 扫描无标签残留
            for t in qb2.torrents():
                if t.get("name", "").startswith("rm03c17"):
                    qb2.delete(t["hash"], delete_files=True)
        purge_tree(case)


def _state_payload(case: Path) -> dict:
    """state.json 原始载荷(skip_check_day/skip_check_backup 等 ops 即时落盘键)。"""
    p = case / "data" / "state.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
