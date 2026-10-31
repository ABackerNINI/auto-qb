"""RM03 规则引擎 —— 九条真机用例(条件命中 / 动作真作用于 qB / 变量替换 / 表达式)。

验证面对准冻结计划 plans/26-10-31-1228-plan-real-RM03.html §02 的六行代码映射:
条件命中·interval 主链(RM03-01)· on_torrent_added 事件分派→add_category(RM03-02)·
限速下发+API 回读+奇数 KiB 手动限速不覆盖(RM03-03)· 变量替换 ${required_seeding_time}
(RM03-04)· 表达式条件命中+装载期/运行期负向(RM03-05)· on_torrent_deleted 删除触发面
快照留档(RM03-06)· 动作序列 stop→start+remove_tags regex(RM03-07)·
execute_once/cooldown 规则层去重(RM03-08)· dry-run 零 qB 写(RM03-09)。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 规则集 = config 段下**以 `_rules` 结尾的顶层键**(loaders.py:629), tracker 条目
  `rules: ["@rm03_rules"]` 引用; tracker 绑定是规则面的前置死门 —— 假种子必须带本机死端口
  announce(http://<本机IP>:1/announce, §2.9 第①条), 匹配按 hostname 不含端口(utils.match_tracker_confs);
- 规则动作日志锚点: 「规则[名] <log_repr> | 动作[名] 成功/失败」(base.py:247/256);
  条件求值出错 = ERROR「条件求值出错, 停止后续规则」(base.py:280, 优先于 stop_following_rules_if);
  skip 级是 DEBUG(INFO 日志不可见), 断言不咬 skip 文案;
- 限速断言只认 qB API 回读(torrents/info 的 dl_limit/up_limit); 奇数 KiB = 手动限速
  (utils.is_manual_speed_limit), 动作必须 skip 不覆盖;
- execute_once 合法枚举实况 = never/once/daily/hourly(fields.py:181) —— 计划写的
  "execute_once: always" 不是合法值, RM03-08 按「窗口内只执行一次」同一意图落 `once`(切片记偏差);
- 规则 interval 键**省略** = 每 tick 级别(队列归一化 1s)—— 计划写的 "interval: 0S=每轮" 不成立,
  0S 被配置校验拒绝(「必须为正时间」, 预检实测), 留空才是每轮语义(切片记偏差);
- 运行期负向表达式用 `(1 / 0) > 0`(eval.py 对除零显式抛 ExprError, 确定性不依赖盘符);
- 去重断言走**规则层**: exec_history(state.json)的 ts 只在执行时写 —— 去重失效会被每轮刷新,
  而动作级幂等(add_tags skip)在 INFO 日志不可见, 只数成功行数分不出来(计划 §08 风险 5);
- tag 解析一律 strip(§2.9: qB 多标签以「, 」连接, RM04 已入池的基建缺陷用例侧防御);
- 产品日志追加式, 断言计数前先等新行; state.json 的 exec_history 只在优雅退出/周期落盘时刷盘
  (配置端下限 30S), RM03-08 用 graceful_after 走优雅退出拿权威账。

跑法: `commands run real.suite -- --slice RM03 --yes`(不要裸 pytest)。真实种子全程非活跃;
九条全部 L1 假种子(死端口 announce, 零外连); 假种子一律 real-fake 标签; 删除动作只删自造种子;
产品 data_dir 指用例临时目录, 不碰仓库根 auto-qb-data/。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import urllib.parse
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, torrent  # noqa: E402
from lib.net import local_host  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm03"
TAG = "real-fake"
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}

# 假种子 announce 指本机死端口(零外连): tracker 绑定死门(计划 §08 风险 2) —— 无匹配 tracker
# 配置的种子 interval 补建与事件分派双路跳过, 规则面整个不发生。匹配按 hostname 不含端口,
# 多 conf 分流(RM03-04)用不同 host(本机IP vs localhost, 都是本机, 零外连; 别用假域名走 DNS)。
FAKE_HOST = local_host()
ANNOUNCE_IP = f"http://{FAKE_HOST}:1/announce"
ANNOUNCE_LH = "http://localhost:1/announce"

RULESET = "rm03_rules"  # 规则集键: loaders.py 只认以 _rules 结尾的 config 顶层键

# ---------------------------------------------------------------- 基座


def qbfake():
    from lib import instances
    return instances.make(36596)


def _tags_of(t) -> set[str]:
    """qB tags 字段的容错解析: qB 多标签用「, 」连接, 一律 strip 后判成员
    (§2.9 / 已入池 26-10-31-1215 的用例侧防御)。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def _add_retry(qb, raw: bytes, savepath: str, ih: str) -> None:
    """加种子, 409 双义处理(qB 5.2 重复 infohash 返回 409 Conflict)。

    同 infohash 旧副本在场时**一律删掉重加, 绝不收养**(§2.9 第②条: 收养把上轮预打标/
    预暂停状态带进本跑, 触发源永不触发 → 假 FAIL 自续)。"""
    from lib.qb import QbError
    for attempt in range(4):
        try:
            qb.add_torrent(raw, savepath=savepath, tags=TAG, infohash_hint=ih)
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


def rm_all_fakes(qb) -> list[str]:
    """删光 36596 里本片自造的种子(连数据), 返回删掉的名字(证据用)。
    顺序 = 先删后摘标签(删失败时保留 real-fake 标记让下次清场还能看见它, RM04 实测口径)。"""
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


def categories_of(qb) -> dict:
    """qB 全部分类(GET /torrents/categories): {name: {...}}"""
    return json.loads(qb._call("/torrents/categories") or b"{}")


def remove_category(qb, name: str) -> None:
    body = urllib.parse.urlencode({"categories": name}).encode()
    qb._call("/torrents/removeCategories", body, "application/x-www-form-urlencoded")


def cleanup_rm03_categories(qb) -> list[str]:
    """清掉本片造的 rm03* 分类(分类定义独立于种子存活, 种子删除不带走)。"""
    gone = [n for n in categories_of(qb) if n.startswith("rm03")]
    for n in gone:
        remove_category(qb, n)
    if gone:
        wait_until(lambda: not [n for n in categories_of(qb) if n.startswith("rm03")], 10, f"分类删除未生效: {gone}")
    return gone


def set_limit_raw(qb, h: str, direction: str, limit_bytes: int) -> None:
    """qB 原生单种限速(lib/qb.py 无封装, 直发表单; RM03-03 预置奇数 KiB 手动限速用)。"""
    body = urllib.parse.urlencode({"hashes": h, "limit": str(limit_bytes)}).encode()
    qb._call(f"/torrents/set{direction}Limit", body, "application/x-www-form-urlencoded")


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


def fake_seed(
    qb,
    name: str,
    size: int,
    savepath,
    salt: str,
    announce: str = ANNOUNCE_IP,
    with_data: bool = False,
    piece_len: int = torrent.PIECE_LEN,
) -> str:
    """造一枚 L1 假种子并加入 36596(带 real-fake 标签)。announce 缺省指本机死端口。"""
    savepath = Path(savepath)
    if with_data:
        torrent.write_file(str(savepath / name), size, "random", salt)
        raw, ih = torrent.build_from_path(str(savepath / name), name, announce, piece_len)
    else:
        os.makedirs(savepath, exist_ok=True)  # savepath 得存在; 文件不写 ⇒ 永远 progress 0
        raw, ih = torrent.build_stream(name, size, "random", salt, announce, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def write_cfg(case: Path, trackers: dict, rule_sets: dict, *, web: bool = True) -> Path:
    """生成临时配置(schema_version: 5, 直连 36596)。rule_sets = {规则集名: {规则名: spec}},
    经 yaml.safe_dump 落盘(键序 = 插入序, 规则执行顺序随定义序)。"""
    cfg: dict = {
        "schema_version": 5,
        "qbittorrent": {
            "host": "127.0.0.1",
            "port": 36596,
            "username": "",
            "password": ""
        },
        "data_dir": (case / "data").as_posix(),
        "main_tick": "2S",
        "sync_interval": "1.5S",
        "state_save_interval": "30S",
        "log": {
            "level": "INFO"
        },
        "grouping": {
            "enabled": False
        },
        "notify": {
            "enabled": False
        },
        "trackers": trackers,
    }
    if web:
        cfg["web"] = {"enabled": True, "host": "127.0.0.1", "port": app.free_port(), "skip_local_verify": True}
    else:
        cfg["web"] = {"enabled": False}
    cfg.update(rule_sets)
    # 产品 YAML 的根节点是 `config:`(RM04 CONFIG_TEMPLATE 同款), 全部键嵌在其下
    path = case / "config.yml"
    path.write_text(yaml.safe_dump({"config": cfg}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {path}")
    if "port: 36596" not in text:
        raise AssertionError(f"配置没指向 36596(空库草稿本), 拒跑: {path}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {path}")
    return path


def wait_until(fn, timeout: float, desc: str, interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc}; 最后观测: {last}")


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
    """通例负向守卫: 产品日志不得出现未捕获堆栈或「规则执行异常」(条件求值出错是另一条锚点, 不在此列)。"""
    log = log_text(case)
    assert "Traceback" not in log, "产品日志出现未捕获异常堆栈"
    assert "规则执行异常" not in log, "产品日志出现「规则执行异常」(规则面抛了未捕获异常)"


def exec_history(case: Path) -> dict:
    """state.json 里的 exec_history(规则层去重的权威账; 优雅退出/周期落盘时刷盘)。"""
    p = case / "data" / "state.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("exec_history") or {}


def tracker_conf_entry(domains: list[str], rules: bool = True) -> dict:
    entry: dict = {"domains": list(domains)}
    if rules:
        entry["rules"] = [f"@{RULESET}"]
    return entry


# ================================================================ RM03-01


def test_rm03_01_interval_size_condition_contrast():
    """[RM03-01] 条件命中·interval 主链: size 条件分流 256K 命中 / 512K 对照不得命中(红验内建)

    前置: 产品非 dry-run 连 36596; A(256K)/B(512K) 两枚假种子(死端口 announce 同一
          tracker 条目引 @rm03_rules)在产品启动前入库(interval 存量补建拾取, 免竞态)。
    副作用: 36596 加 2 假种子; A 被打 rm03-hit 标签。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: ≥3 节拍后 A 仍无标签; B 也被打标(条件分流失效, 对照必须能红);
              日志出现「规则执行异常」/Traceback。
    """
    case = case_dir("rm03_01")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c1size":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "size": "<=384KiB"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-hit"]
                            }],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_01"
        ha = fake_seed(qb, "rm03c1a.bin", 256 * 1024, savepath, "rm03c1-a")
        hb = fake_seed(qb, "rm03c1b.bin", 512 * 1024, savepath, "rm03c1-b")
        settle(qb, ha)
        settle(qb, hb)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        wait_until(lambda: "rm03-hit" in _tags_of(qb.torrent(ha) or {}), 25, "A(256K)未被规则打标(条件命中失效)")
        n_a = count_anchor(case, r"规则\[rm03_rules.rm03c1size\].*动作\[add_tags\] 成功")
        assert n_a >= 1, "日志无 rm03c1size 的 add_tags 成功行(标签不是规则打的)"
        time.sleep(9)  # ≥3 个节拍: 若条件分流失效, B 必然在此窗口被打标
        assert "rm03-hit" not in _tags_of(qb.torrent(hb) or {}), \
            "对照红验失效: B(512K)也被打标 —— size 条件分流失效"
        assert count_anchor(case, rf"规则\[rm03_rules.rm03c1size\].*\({hb[:8]}\).*动作\[add_tags\] 成功") == 0, \
            "日志出现 B 的 add_tags 成功行(对照种子被规则执行)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-02


def test_rm03_02_on_added_dispatch_category():
    """[RM03-02] on_torrent_added 即时分派 → add_category 真建分类并赋给种子

    前置: 产品先起(库空), 后加 1 枚假种子 —— 事件规则即时分派, 不等节拍
          (复跑遇 qB 5.2 重复 infohash 409 → 删旧重加, 不收养)。
    副作用: 加 1 假种子; qB categories 出现 rm03-added 且该种子 category=rm03-added。
    回滚: 删光 real-fake 种子 + 删 rm03* 分类 + 删用例目录。
    失败判据: categories 无 rm03-added; 或分类建了种子未赋上; 或产品日志无该规则成功行。
    """
    case = case_dir("rm03_02")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm03_categories(qb)
        rules = {
            RULESET:
                {
                    "rm03c2cat":
                        {
                            "trigger": "on_torrent_added",
                            "actions": [{
                                "add_category": {
                                    "format": "rm03-added",
                                    "overwrite": False
                                }
                            }],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        savepath = WORK / "rm03_02"
        h = fake_seed(qb, "rm03c2.bin", 256 * 1024, savepath, "rm03c2")
        settle(qb, h)

        wait_until(lambda: "rm03-added" in categories_of(qb), 20, "qB categories 未出现 rm03-added(分类没真建)")
        wait_until(
            lambda: ((qb.torrent(h) or {}).get("category") or "").strip() == "rm03-added",
            15,
            "分类建了但种子未被赋上(add 与赋值两步断开)",
        )
        wait_until(
            lambda: count_anchor(case, r"规则\[rm03_rules.rm03c2cat\].*动作\[add_category\] 成功") >= 1,
            10,
            "日志无 rm03c2cat 的 add_category 成功行",
        )
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        qb2 = qbfake()
        rm_all_fakes(qb2)
        cleanup_rm03_categories(qb2)
        purge_tree(case)


# ================================================================ RM03-03


def test_rm03_03_speed_limits_and_manual_odd_skip():
    """[RM03-03] 限速动作: 偶数目标真下发+API 回读; 预置奇数 KiB 手动限速的种子乙不得被覆盖(负向红验)

    前置: 甲乙两枚假种子在产品启动前入库; 乙先经 qB API 预置 dl/up=2001KiB/s(奇数 =
          is_manual_speed_limit 项目约定); 规则无条件(全匹配)下发 64KiB/s(下)+128KiB/s(上)。
    副作用: 甲的限速被改; 乙原样。
    回滚: 删光 real-fake 种子(限速随种子删除一并消失)+ 删用例目录。
    失败判据: 甲回读 dl_limit≠64KiB/s 或 up_limit≠128KiB/s(只认 API 回读);
              乙限速被覆盖(手动保护失效); 同一种子限速成功行反复出现(重复下发不 skip「已设置」)。
    """
    case = case_dir("rm03_03")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c3limit":
                        {
                            "trigger": "interval",
                            "actions": [{
                                "download_speed_limit": "64KiB/s"
                            }, {
                                "upload_speed_limit": "128KiB/s"
                            }],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_03"
        ha = fake_seed(qb, "rm03c3a.bin", 256 * 1024, savepath, "rm03c3-a")
        hb = fake_seed(qb, "rm03c3b.bin", 256 * 1024, savepath, "rm03c3-b")
        settle(qb, ha)
        settle(qb, hb)
        set_limit_raw(qb, hb, "Download", 2001 * 1024)  # 预置在产品启动前, 规则首轮快照即奇数
        set_limit_raw(qb, hb, "Upload", 2001 * 1024)
        assert (qb.torrent(hb) or {}).get("dl_limit") == 2001 * 1024, "乙的下载限速预置未生效"
        assert (qb.torrent(hb) or {}).get("up_limit") == 2001 * 1024, "乙的上传限速预置未生效"

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # ---- 甲: 下发后 API 回读断言(验证口径只认回读, 不咬日志)
        wait_until(
            lambda: (qb.torrent(ha) or {}).get("dl_limit") == 64 * 1024 and
            (qb.torrent(ha) or {}).get("up_limit") == 128 * 1024,
            25,
            f"甲限速回读不符: dl={(qb.torrent(ha) or {}).get('dl_limit')} up={(qb.torrent(ha) or {}).get('up_limit')}",
        )
        # ---- 乙: 奇数 KiB 手动限速必须原样(负向红验, ≥3 节拍窗口)
        time.sleep(9)
        b = qb.torrent(hb) or {}
        assert b.get("dl_limit") == 2001 * 1024 and b.get("up_limit") == 2001 * 1024, \
            f"对照红验失效: 乙(奇数 KiB 手动限速)被覆盖: dl={b.get('dl_limit')} up={b.get('up_limit')}"
        # ---- 重复节拍不反复下发: 甲同一种子的限速成功行在稳定后不再增长
        n1 = count_anchor(case, rf"规则\[rm03_rules.rm03c3limit\].*\({ha[:8]}\).*动作\[download_speed_limit\] 成功")
        assert n1 >= 1, "日志无甲的 download_speed_limit 成功行(限速不是规则下发的)"
        time.sleep(7)
        n2 = count_anchor(case, rf"规则\[rm03_rules.rm03c3limit\].*\({ha[:8]}\).*动作\[download_speed_limit\] 成功")
        assert n2 == n1, f"限速动作在值已设置的后续节拍反复成功下发({n1} -> {n2}), skip「已设置」失效(日志刷屏)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-04


def test_rm03_04_var_replacement_with_and_without_hr():
    """[RM03-04] 变量替换: ${required_seeding_time} → hr raw("3D"); 无 hr 的 tracker 条目留原文(对照)

    前置: trackers 双条目分流 —— 甲 domains=[本机IP] 带 hr(required_seeding_time: 3D),
          乙 domains=[localhost] 无 hr(localhost 走本机 hosts, connect 死端口同样零外连);
          两枚假种子 announce 分别指两 host(匹配按 hostname 不含端口)。
    副作用: 加 2 假种子; 甲标签 keep-3D, 乙标签字面 keep-${required_seeding_time}。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: 甲标签未替换出 3D; 乙标签不是原文(无 hr 被替换成空串/抛错);
              HR 模块对假种子发起在线动作(记 BLOCKED 归 RM06)。
    """
    case = case_dir("rm03_04")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c4var": {
                        "trigger": "interval",
                        "actions": [{
                            "add_tags": ["keep-${required_seeding_time}"]
                        }],
                    }
                }
        }
        trackers = {
            "rm03ip": {
                **tracker_conf_entry([FAKE_HOST]), "hr": {
                    "required_seeding_time": "3D"
                }
            },
            "rm03lh": tracker_conf_entry(["localhost"]),
        }
        savepath = WORK / "rm03_04"
        ha = fake_seed(qb, "rm03c4a.bin", 256 * 1024, savepath, "rm03c4-a", announce=ANNOUNCE_IP)
        hb = fake_seed(qb, "rm03c4b.bin", 256 * 1024, savepath, "rm03c4-b", announce=ANNOUNCE_LH)
        settle(qb, ha)
        settle(qb, hb)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        wait_until(
            lambda: "keep-3D" in _tags_of(qb.torrent(ha) or {}), 25,
            f"甲标签未替换出 keep-3D: {sorted(_tags_of(qb.torrent(ha) or {}))}"
        )
        wait_until(
            lambda: "keep-${required_seeding_time}" in _tags_of(qb.torrent(hb) or {}),
            15,
            f"乙标签不是字面原文(无 hr 被替换/丢失): {sorted(_tags_of(qb.torrent(hb) or {}))}",
        )
        # HR 模块牵动检查(计划 §08 风险 7): 带了 hr 配置, 若 HR 面对假种子发起动作, 日志必留痕
        log = log_text(case)
        assert "在线核实" not in log, "HR 模块对假种子发起了在线核实(计划预登记 BLOCKED 归 RM06)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-05


def test_rm03_05_expr_condition_hit_and_negatives():
    """[RM03-05] 表达式条件: 正向求值命中打标; 坏语法装载期被拒(ConfigError);
    运行期除零 → 条件出错停规则 ERROR 且动作不执行、后续规则被停

    前置: 1 枚 256K 假种子; 正向规则 expr=(tor.size >= 200KiB) and (len(tor.name) > 0);
          运行期负向规则 expr=(1 / 0) > 0(装载期合法, 求值抛 ExprError);
          其后再挂一条无条件规则(必须被停, 验证 stop 语义)。
    副作用: 加 1 假种子; 正向打标 rm03-expr-hit。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: 正向不命中(按实况修期望值重跑一次, 仍不中记 FAIL); 装载期坏语法静默通过;
              运行期负向无 ERROR 且动作照跑(停规则语义失效); 被停的后续规则打了标。
    """
    case = case_dir("rm03_05")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"

        # ---- 装载期负向: 坏语法表达式在配置加载即被拒(独立起一次 CLI, dry-run 不进主循环)
        case_bad = case_dir("rm03_05_load")
        bad_rules = {
            RULESET:
                {
                    "rm03c5bad":
                        {
                            "trigger": "interval",
                            "conditions": [{
                                "expr": "tor.size >"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-bad"]
                            }],
                        }
                }
        }
        cfg_bad = write_cfg(case_bad, {"rm03fake": tracker_conf_entry([FAKE_HOST])}, bad_rules, web=False)
        r = app.run_cli([str(cfg_bad), "--dry-run"], timeout=60)
        sinks = (r.stdout or "") + (r.stderr or "") + log_text(case_bad)
        assert r.returncode != 0, f"装载期红验失效: 坏语法表达式被静默通过(rc=0):\n{sinks[-500:]}"
        assert "rm03c5bad" in sinks, f"装载期拒绝但日志/输出不含规则名(证据不足):\n{sinks[-600:]}"
        purge_tree(case_bad)

        # ---- 主现场: 正向命中 + 运行期负向停规则
        rules = {
            RULESET:
                {
                    "rm03c5expr":
                        {
                            "trigger": "interval",
                            "stop_following_rules_if": "never",
                            "conditions": [{
                                "expr": "(tor.size >= 200KiB) and (len(tor.name) > 0)"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-expr-hit"]
                            }],
                        },
                    "rm03c5err":
                        {
                            "trigger": "interval",
                            "stop_following_rules_if": "never",
                            "conditions": [{
                                "expr": "(1 / 0) > 0"
                            }],
                            "actions": [{
                                "add_tags": ["rm03-never"]
                            }],
                        },
                    "rm03c5after": {
                        "trigger": "interval",
                        "actions": [{
                            "add_tags": ["rm03-after"]
                        }],
                    },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_05"
        h = fake_seed(qb, "rm03c5.bin", 256 * 1024, savepath, "rm03c5")
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 3 条(启用 3 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        wait_until(lambda: "rm03-expr-hit" in _tags_of(qb.torrent(h) or {}), 25, "正向表达式不命中(求值结果与真机字段实况分叉)")
        wait_until(
            lambda: count_anchor(case, r"规则\[rm03_rules.rm03c5err\].*条件求值出错, 停止后续规则") >= 1,
            20,
            "运行期负向表达式未产生「条件求值出错, 停止后续规则」ERROR(静默通过, 停规则语义失效)",
        )
        time.sleep(6)  # ≥3 节拍: 若停规则失效, rm03-never / rm03-after 必然出现
        tags = _tags_of(qb.torrent(h) or {})
        assert "rm03-never" not in tags, f"运行期负向规则的动作照跑了(出错后未停): {sorted(tags)}"
        assert "rm03-after" not in tags, f"排在出错规则后的规则未被停(停止后续规则失效): {sorted(tags)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)
        purge_tree(WORK / "rm03_05_load")


# ================================================================ RM03-06


def test_rm03_06_on_deleted_trigger_snapshot():
    """[RM03-06] 删除触发面 on_torrent_deleted: 删自造种子 → 删除前快照留档(只删 real-fake)

    前置: 产品先起(库空); 探针规则(on_torrent_added + print_torrent_details)确认种子
          进了 store; 再加 on_torrent_deleted 规则(动作 print_torrent_details —— 删除面
          唯一合法只读动作, 规则引擎 12 动作无 delete 类, 本条验的是删除事件触发面)。
    副作用: 删除 1 枚自造种子(本就要删, 无额外副作用)。
    回滚: 无残留(种子已删); 删用例目录; 断言只认假种子 hash。
    失败判据: 删除后产品日志无该规则 print 输出(快照路径失效); 输出里种子字段全空;
              该规则的输出出现非本假种子的 hash(真实种子误触发 —— 断言日志只出现假种子 hash)。
    """
    case = case_dir("rm03_06")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c6probe": {
                        "trigger": "on_torrent_added",
                        "actions": [{
                            "print_torrent_details": True
                        }],
                    },
                    "rm03c6del": {
                        "trigger": "on_torrent_deleted",
                        "actions": [{
                            "print_torrent_details": True
                        }],
                    },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 2 条(启用 2 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        savepath = WORK / "rm03_06"
        h = fake_seed(qb, "rm03c6.bin", 256 * 1024, savepath, "rm03c6")
        # 探针: added 规则的 print 行出现 = 种子已进 store(否则删除事件无从谈起)
        wait_until(
            lambda: count_anchor(case, rf"规则\[rm03_rules.rm03c6probe\].*\({h[:8]}\).*打印种子详情") >= 1,
            25,
            "探针规则未见种子(added 分派/入库失败, 前提不成立)",
        )

        qb.delete(h, delete_files=True)  # 删自造种子(删除动作只删 real-fake, 红线)
        wait_until(
            lambda: count_anchor(case, rf"规则\[rm03_rules.rm03c6del\].*\({h[:8]}\).*打印种子详情.*名称=rm03c6\.bin") >= 1,
            25,
            "删除后无 on_torrent_deleted 规则的 print 输出(快照路径失效)",
        )
        # 快照没接上的形态: 字段全空(名称=-)
        del_lines = re.findall(rf"规则\[rm03_rules.rm03c6del\].*\({h[:8]}\).*打印种子详情.*", log_text(case))
        assert del_lines and all("名称=-" not in ln for ln in del_lines), \
            f"删除前快照没接上(字段全空): {del_lines[:2]}"
        # 真实种子误触发检查: 该规则输出里只允许出现本假种子的 hash
        foreign = [ln for ln in re.findall(r"规则\[rm03_rules.rm03c6del\].*\((\w{8})\)", log_text(case)) if ln != h[:8]]
        assert not foreign, f"rm03c6del 规则输出出现了非本假种子的 hash: {foreign}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-07


def test_rm03_07_action_sequence_stop_start_and_remove_tags():
    """[RM03-07] 启停与清理向动作: add_tags → remove_tags(regex:rm03-t\\d+) → stop → start 序列语义

    前置: 1 枚带数据假种子(可 start 做种); 规则串四动作, 每轮顺序执行。
    副作用: 种子被暂停又恢复(每轮); 标签加又删(每轮)。
    回滚: 删光 real-fake 种子(连数据)+ 删残留标签 + 删用例目录;
          regex 若误删 real-fake 导致清场失明, 收尾按 hash 兜底删(26-10-31-1215 坑在池)。
    失败判据: regex 未命中应删标签 / 删掉了 real-fake; 序列里 stop/start 成功行缺失;
              动作顺序错乱(轮末仍有 rm03-t* 残留)。
    """
    case = case_dir("rm03_07")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c7seq":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "add_tags": ["rm03-t1", "rm03-t2"]
                                    },
                                    {
                                        "remove_tags": ["regex:rm03-t\\d+"]
                                    },
                                    {
                                        "stop": True
                                    },
                                    {
                                        "start": True
                                    },
                                ],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_07"
        h = fake_seed(qb, "rm03c7.bin", 256 * 1024, savepath, "rm03c7", with_data=True)
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"

        # 序列跨轮重复: 标签每轮删掉 → 下轮 add_tags 再次成功; ≥2 行证明动作序列真在跑
        wait_until(
            lambda: count_anchor(case, rf"规则\[rm03_rules.rm03c7seq\].*\({h[:8]}\).*动作\[add_tags\] 成功") >= 2,
            30,
            "add_tags 成功行 <2(序列没有跨轮重复执行, 或 remove_tags 没删掉标签)",
        )
        for act in ("remove_tags", "stop", "start"):
            wait_until(
                lambda act=act: count_anchor(case, rf"规则\[rm03_rules.rm03c7seq\].*\({h[:8]}\).*动作\[{act}\] 成功") >= 1,
                20,
                f"日志无 {act} 成功行(动作没执行)",
            )
        rm_msg = re.search(rf"规则\[rm03_rules.rm03c7seq\].*\({h[:8]}\).*动作\[remove_tags\] 成功: (.*)", log_text(case))
        assert rm_msg and "rm03-t1" in rm_msg.group(1) and "rm03-t2" in rm_msg.group(1), \
            f"remove_tags 删的不是预期标签: {rm_msg.group(1) if rm_msg else '无'}"
        # 轮末稳态: real-fake 仍在(regex 收紧未误伤管理标签), rm03-t* 已收敛, 状态恢复做种
        wait_until(
            lambda: (qb.torrent(h) or {}).get("state", "stopped").find("stopped") == -1,
            25,
            "start 动作后种子未恢复非 stopped 态(启停往返失效)",
        )
        tags = _tags_of(qb.torrent(h) or {})
        assert TAG in tags, f"regex 误删了 real-fake 管理标签: {sorted(tags)}"
        assert not [t for t in tags if re.match(r"rm03-t\d+$", t)], \
            f"轮末仍有 rm03-t* 标签残留(动作顺序错乱或 regex 未命中): {sorted(tags)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        qb2 = qbfake()
        gone = rm_all_fakes(qb2)
        if not gone:  # real-fake 失明兜底(26-10-31-1215): 按 hash 扫描无标签残留
            for t in qb2.torrents():
                if t.get("name", "").startswith("rm03c7"):
                    qb2.delete(t["hash"], delete_files=True)
        purge_tree(case)


# ================================================================ RM03-08


def test_rm03_08_dedup_execute_once_and_cooldown():
    """[RM03-08] 去重语义: execute_once=once 与 cooldown=60S 的规则层去重(跨 ≥3 节拍首轮后不再执行)

    前置: 1 枚假种子; 两条规则各配 once / cooldown 60S, 动作各打不同标签;
          产品以 graceful_after 起跑(观察窗 ≥3 节拍后优雅退出, exec_history 才落盘)。
    副作用: 2 个标签。
    回滚: 删光 real-fake 种子 + 删用例目录。
    失败判据: exec_history 的 ts 在首轮后仍被刷新(规则层去重失效 —— 断言走规则层,
              不被动作级幂等骗过去重失效); 或优雅退出非 0(观察窗没走完)。
    注: 计划写 execute_once: always, 实况合法枚举 = never/once/daily/hourly(fields.py:181),
        按「窗口内只执行一次」同一意图落 once(切片记偏差)。
    """
    case = case_dir("rm03_08")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        rules = {
            RULESET:
                {
                    "rm03c8once":
                        {
                            "trigger": "interval",
                            "execute_once": "once",
                            "stop_following_rules_if": "never",
                            "actions": [{
                                "add_tags": ["rm03-once"]
                            }],
                        },
                    "rm03c8cool":
                        {
                            "trigger": "interval",
                            "cooldown": "60S",
                            "stop_following_rules_if": "never",
                            "actions": [{
                                "add_tags": ["rm03-cool"]
                            }],
                        },
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_08"
        h = fake_seed(qb, "rm03c8.bin", 256 * 1024, savepath, "rm03c8")
        settle(qb, h)

        cfg = write_cfg(case, trackers, rules)
        p = app.start(cfg, case, graceful_after=30.0)  # 首轮执行后还有 ≥10 个节拍的观察窗
        # 首轮执行完成点(标签出现 ≈ record_execution 时刻)
        t_first = wait_until(
            lambda: time.time() if
            ("rm03-once" in _tags_of(qb.torrent(h) or {}) and "rm03-cool" in _tags_of(qb.torrent(h) or {})) else None,
            30,
            "首轮执行未发生(两条标签都没出现)",
        )
        time.sleep(12)  # 观察窗余量: 若去重失效, ts 会在后续节拍被反复刷新
        rc = p.wait(90)
        p = None
        assert rc == 0, f"优雅退出非 0(观察窗没走完): {rc}\n{log_text(case)[-600:]}"

        hist = exec_history(case)
        for rname in ("rm03c8once", "rm03c8cool"):
            rec = hist.get(f"{RULESET}.{rname}:{h}")
            assert rec, f"exec_history 无 {rname} 的执行记录(执行没记账, 去重面无从谈起)"
            assert rec["ts"] < t_first + 3.0, \
                f"{rname} 的执行 ts 在首轮后被刷新({rec['ts'] - t_first:.1f}s 后): 规则层去重失效"
        for rname in ("rm03c8once", "rm03c8cool"):
            assert count_anchor(case, rf"规则\[{RULESET}.{rname}\].*\({h[:8]}\).*动作\[add_tags\] 成功") == 1, \
                f"{rname} 的 add_tags 成功行 ≠1(多轮重复执行了动作)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes(qbfake())
        purge_tree(case)


# ================================================================ RM03-09


def test_rm03_09_dry_run_zero_qb_write():
    """[RM03-09] dry-run 面: 条件命中但零 qB 写(约束面负向)

    前置: 先直接经 qB API 加 1 枚假种子并留底快照(tags/categories/限速); 换 dry-run
          配置(--dry-run, 不带 WEB)起产品连 36596。
    副作用: qB 侧零写(这正是被验对象); 产品侧仅日志。
    回滚: 删光 real-fake 种子 + 停产品 + 删用例目录。
    失败判据: dry-run 下 qB 侧出现标签/分类/限速变化(高优 FAIL, 约束面被破坏);
              全程零规则命中日志且确认管线不分派 → 记 BLOCKED 非 FAIL(计划预登记)。
    """
    case = case_dir("rm03_09")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm03_categories(qb)
        rules = {
            RULESET:
                {
                    "rm03c9dry":
                        {
                            "trigger":
                                "interval",
                            "actions":
                                [
                                    {
                                        "add_tags": ["rm03-dry"]
                                    },
                                    {
                                        "add_category": {
                                            "format": "rm03-drycat",
                                            "overwrite": False
                                        }
                                    },
                                    {
                                        "download_speed_limit": "64KiB/s"
                                    },
                                ],
                        }
                }
        }
        trackers = {"rm03fake": tracker_conf_entry([FAKE_HOST])}
        savepath = WORK / "rm03_09"
        h = fake_seed(qb, "rm03c9.bin", 256 * 1024, savepath, "rm03c9")
        settle(qb, h)
        before = {
            "tags": sorted(_tags_of(qb.torrent(h) or {})),
            "category": (qb.torrent(h) or {}).get("category") or "",
            "dl_limit": (qb.torrent(h) or {}).get("dl_limit"),
            "categories": sorted(categories_of(qb)),
        }

        cfg = write_cfg(case, trackers, rules, web=False)
        p = app.start(cfg, case, dry_run=True)
        assert p.wait_log("加载规则 1 条(启用 1 条)", 40), f"规则没加载上:\n{p.log()[-800:]}"
        time.sleep(20)  # ≥10 个节拍: 若管线分派, 规则命中行必然出现

        log = log_text(case)
        dispatched = count_anchor(case, r"规则\[rm03_rules.rm03c9dry\]") > 0
        if not dispatched:
            p.stop()
            p = None
            pytest.skip(
                "BLOCKED: dry-run 下规则管线不分派(20s/≥10 节拍零规则命中日志)—— "
                "RM02 只验了 dry-run 不落盘, 种子同步是否执行未实测; 解锁条件 = 查明 dry-run 管线分派路径"
            )

        assert count_anchor(case, r"规则\[rm03_rules.rm03c9dry\].*动作\[add_tags\] 成功") >= 1, \
            "管线有规则活动但未见 add_tags 成功行(命中判据不成立)"
        t = qb.torrent(h) or {}
        after = {
            "tags": sorted(_tags_of(t)),
            "category": t.get("category") or "",
            "dl_limit": t.get("dl_limit"),
            "categories": sorted(categories_of(qb)),
        }
        assert after["tags"] == before["tags"], f"dry-run 下 qB 侧标签被写: {before['tags']} -> {after['tags']}"
        assert after["category"] == before["category"
                                          ], f"dry-run 下分类被写: {before['category']!r} -> {after['category']!r}"
        assert after["dl_limit"] == before["dl_limit"], f"dry-run 下限速被写: {before['dl_limit']} -> {after['dl_limit']}"
        assert after["categories"] == before["categories"], f"dry-run 下新建了分类: {after['categories']}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        qb2 = qbfake()
        rm_all_fakes(qb2)
        cleanup_rm03_categories(qb2)
        purge_tree(case)
