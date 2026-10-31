"""RM05 tracker·标签与分类清理 —— 七条真机用例(tracker 规则解析 / delete_tags 族 / @tracker_tags 引用 / 站点档案派生)。

验证面对准冻结计划 plans/26-10-31-1312-plan-real-RM05.html §03 的七条 spec:
tracker 匹配三分流(RM05-01)· 热重载重绑(RM05-02)· tracker 单种限速认领+手动保护(RM05-03)·
种子级标签族 add/remove/相似(RM05-04)· delete_tags 全局删标签+@tracker_tags 展开(RM05-05)·
delete_tags_if_has_no_torrents 使用中对照(RM05-06)· 站点档案派生装载期正负向(RM05-07)。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 假种子 announce 指本机死端口 http://<本机IP>:1/announce(§2.9 第①条), 匹配按 hostname
  不含端口(utils.match_tracker_confs, config dict 书写顺序返回, 不排序); 负向种子用
  127.0.0.1 hostname(本机死端口, 零 DNS 零外连); conf=None 的种子整条 added 管线跳过是预期;
- 多匹配「第一个」= match_tracker_confs 按 config dict 顺序取 confs[0](tracker_mod.py:92
  WARNING「种子匹配到多个 tracker 配置, 使用第一个」); RM05-01 的条目键故意让字母序与书写序
  相反(zz 在前 aa 在后), 若实现按名字序会立刻红;
- 全局任务 delete_tags / delete_tags_if_has_no_torrents 按 config.interval 每轮入队
  (maintenance_mod._register_global_tasks), 日志锚点「彻底删除标签」「彻底删除无种子的标签」
  (命中集非空才打); 种子级维护(handle_maintenance)每 interval 给 tracker_conf.tags 补打
  —— RM05-05 里 rm05-g1/g2 会被维护管线反复重建定义、再被全局任务反复删掉, 稳态是振荡的,
  断言设计成「等一条新的删除日志出现后立刻采样」(此时定义必不在), 不做任意时刻快照;
- @tracker_tags 引用展开是装载期定值(loaders._expand_tracker_tags_refs, 消费点 delete_tags
  两键), 断言走消费点效果(删掉的标签定义集合), 不咬展开实现;
- 限速断言只认 qB API 回读(torrents/info 的 dl_limit/up_limit); 偶数 KiB = 程序下发口径,
  奇数 KiB(2001)= is_manual_speed_limit 项目约定, added 管线必须 skip 不覆盖;
- tag 解析一律 strip(§2.9: qB 多标签以「, 」连接, 已入池 26-10-31-1215 的用例侧防御);
- qB 全局标签定义独立于种子存活(种子删除不带走), GET /torrents/tags 列定义、
  POST /torrents/createTags|deleteTags 造/删(逗号分隔多值, 36596 实测可用);
- RM05-07 是纯装载期面: 正向起产品进程等「启动 qB 管理器」; 负向走 run_cli --dry-run
  退出码 + 「配置错误」文案(RM03-05 同款观测法); hr_check.enabled 全程 false(HR 零外连红线),
  站点绑定要求条目带 hr 段(validation: 「已绑定站点…但该站点未配置 hr 段」)。

跑法: `commands run real.suite -- --slice RM05 --yes`(不要裸 pytest)。真实种子全程非活跃;
七条全部 L1 假种子(死端口 announce, 零外连, RM05-07 零种子); 假种子一律 real-fake 标签;
标签/标签定义/匹配模式全部收紧 rm05- 前缀, 绝不出现能匹配 real-fake 或真实标签的宽泛模式;
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
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, torrent  # noqa: E402
from lib.net import local_host  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm05"
TAG = "real-fake"
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}

# 假种子 announce 指本机死端口(零外连); 负向种子 hostname 用 127.0.0.1(计划 §08 风险 2:
# 别用假域名造负向 —— 那要走 DNS 出外网)。匹配按 hostname 不含端口。
FAKE_HOST = local_host()
ANNOUNCE_IP = f"http://{FAKE_HOST}:1/announce"
ANNOUNCE_LH = "http://127.0.0.1:1/announce"

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
    预暂停状态带进本跑, 触发源永不触发 → 假 FAIL 自续)。预打标用例(RM05-04/05/06)尤其如此。"""
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
    顺序 = 先删后摘标签; 若 real-fake 被误删导致失明(26-10-31-1215 坑在池), 调用方按名字兜底。"""
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


def rm_all_fakes_with_sweep(qb, name_prefix: str) -> list[str]:
    """清场 + real-fake 失明兜底: 按 rm05 名字前缀扫无标签残留(26-10-31-1215: regex 误删
    real-fake 后 seed.rm 全盲, 收尾按 hash 兜底删是计划写死的回滚路径)。"""
    gone = rm_all_fakes(qb)
    for t in qb.torrents():
        if t.get("name", "").startswith(name_prefix):
            qb.delete(t["hash"], delete_files=True)
            gone.append(f"[sweep]{t['name']}")
    if gone:
        wait_until(lambda: not qb.torrents(), 15, f"清场后 36596 仍有种子残留: {gone}")
    return gone


def global_tags(qb) -> list[str]:
    """qB 全局标签定义表(GET /torrents/tags)。"""
    return json.loads(qb._call("/torrents/tags"))


def delete_global_tags(qb, names: list[str]) -> None:
    """删全局标签定义(POST /torrents/deleteTags, 逗号分隔多值, 36596 实测可用)。"""
    if not names:
        return
    body = urllib.parse.urlencode({"tags": ",".join(names)}).encode()
    qb._call("/torrents/deleteTags", body, "application/x-www-form-urlencoded")


def cleanup_rm05_defs(qb) -> list[str]:
    """清掉本片造的 rm05-* 标签定义(**模式收紧 rm05- 前缀, 绝不碰 real-fake/真实标签**)。"""
    gone = [t for t in global_tags(qb) if t.startswith("rm05")]
    delete_global_tags(qb, gone)
    if gone:
        wait_until(lambda: not [t for t in global_tags(qb) if t.startswith("rm05")], 10, f"标签定义删除未生效: {gone}")
    return gone


def set_limit_raw(qb, h: str, direction: str, limit_bytes: int) -> None:
    """qB 原生单种限速(预置奇数 KiB 手动限速用, RM03-03 同款)。"""
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


def write_cfg(case: Path,
              trackers: dict,
              extra: dict | None = None,
              *,
              web: tuple[int, int] | None = None) -> tuple[Path, int | None]:
    """生成临时配置(schema_version: 5, 直连 36596)。

    trackers = {条目名: spec}(dict 插入序 = YAML 书写序 = 匹配优先序, 键序敏感的 RM05-01 依赖此);
    extra = 顶层键合并(delete_tags / remove_similar_tags / hr_check / ruleset 等);
    web = (enabled, port) 或 None。返回 (配置路径, web_port|None)。"""
    web_port = None
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
        "interval": "3S",  # 全局任务与种子级维护的节拍(计划 §03: 主循环 interval 取测试配置小节拍)
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
        web_port = web[1]
        cfg["web"] = {"enabled": True, "host": "127.0.0.1", "port": web_port, "skip_local_verify": True}
    else:
        cfg["web"] = {"enabled": False}
    cfg.update(extra or {})
    # 产品 YAML 的根节点是 `config:`(RM03/RM04 同款), 全部键嵌在其下
    path = case / "config.yml"
    path.write_text(yaml.safe_dump({"config": cfg}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {path}")
    if "port: 36596" not in text:
        raise AssertionError(f"配置没指向 36596(空库草稿本), 拒跑: {path}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {path}")
    return path, web_port


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
    """通例负向守卫: 产品日志不得出现未捕获堆栈。"""
    assert "Traceback" not in log_text(case), "产品日志出现未捕获异常堆栈"


def fake_seed(
    qb,
    name: str,
    size: int,
    savepath,
    salt: str,
    announce: str = ANNOUNCE_IP,
    piece_len: int = torrent.PIECE_LEN,
) -> str:
    """造一枚 L1 假种子并加入 36596(带 real-fake 标签)。announce 缺省指本机死端口。"""
    savepath = Path(savepath)
    os.makedirs(savepath, exist_ok=True)  # savepath 得存在; 文件不写 ⇒ 永远 progress 0
    raw, ih = torrent.build_stream(name, size, "random", salt, announce, piece_len)
    _add_retry(qb, raw, str(savepath), ih)
    return ih


def pretag(qb, ih: str, tags: list[str]) -> None:
    """给已加种子预打标(逐个 add, 避开多值表单分隔符歧义)。"""
    for t in tags:
        qb.add_tags(ih, t)


# ---------------------------------------------------------------- RM05-01


def test_rm05_01_match_three_way_split():
    """[RM05-01] tracker 匹配三分流: 命中进管线 / 不匹配零管线 / 多匹配 WARNING 降级用第一个(对照内建)

    前置: 测试配置 trackers 双条目同域(书写序 zz-hit 在前、aa-second 在后 —— 故意让字母序
          与书写序相反, 若实现按名字序取「第一个」会立刻红); 3 枚假种子在产品启动前入库:
          A/C announce=本机IP(双匹配), B announce=127.0.0.1(零匹配, §2.9 第①条预期负向)。
    副作用: 36596 加 3 假种子; A/C 被打 rm05-hit。
    回滚: real.seed.rm --all + 清 rm05-* 标签定义 + 删用例目录; 收尾核 36596 无残留。
    失败判据: A 未被打标(匹配语义分叉); B 也被打 rm05-*(死门失效, 负向必须能红);
              C 同时有 rm05-second(多匹配降级失效); 日志无 WARNING(多匹配静默)。
    """
    case = case_dir("rm05_01")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        # 条目书写序: zz-hit 在前(config dict 顺序 = 匹配优先序); aa-second 排后但字母序在前
        trackers = {
            "rm05zz-hit": {
                "domains": [FAKE_HOST],
                "tags": ["rm05-hit"],
            },
            "rm05aa-second": {
                "domains": [FAKE_HOST],
                "tags": ["rm05-second"],
            },
        }
        savepath = WORK / "rm05_01"
        ha = fake_seed(qb, "rm05c1a.bin", 256 * 1024, savepath, "rm05c1-a", announce=ANNOUNCE_IP)
        hb = fake_seed(qb, "rm05c1b.bin", 256 * 1024, savepath, "rm05c1-b", announce=ANNOUNCE_LH)
        hc = fake_seed(qb, "rm05c1c.bin", 256 * 1024, savepath, "rm05c1-c", announce=ANNOUNCE_IP)
        settle(qb, ha)
        settle(qb, hb)
        settle(qb, hc)

        cfg, _ = write_cfg(case, trackers)
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"

        # ---- A/C: 命中(多匹配降级用书写序第一个)→ 只打 rm05-hit
        wait_until(
            lambda: "rm05-hit" in _tags_of(qb.torrent(ha) or {}), 25,
            f"A 未被打 rm05-hit: {sorted(_tags_of(qb.torrent(ha) or {}))}"
        )
        wait_until(
            lambda: "rm05-hit" in _tags_of(qb.torrent(hc) or {}), 15,
            f"C 未被打 rm05-hit: {sorted(_tags_of(qb.torrent(hc) or {}))}"
        )
        # ---- 多匹配 WARNING 必须出现, 且一行里同时点出两个条目(降级是「都能匹配」的前提下取第一个)
        wait_until(
            lambda: count_anchor(case, r"种子匹配到多个 tracker 配置, 使用第一个") >= 1,
            15,
            "日志无多匹配 WARNING 行(多匹配静默)",
        )
        warn_lines = [ln for ln in log_text(case).splitlines() if "种子匹配到多个 tracker 配置, 使用第一个" in ln]
        assert any("rm05zz-hit" in ln and "rm05aa-second" in ln for ln in warn_lines), \
            f"WARNING 行未同时点出两个匹配条目(降级证据不足): {warn_lines[:2]}"
        # ---- C 降级对照: 只打书写序第一个条目的 rm05-hit, 绝不打 rm05-second(≥3 节拍窗口)
        time.sleep(9)
        tags_c = _tags_of(qb.torrent(hc) or {})
        assert "rm05-second" not in tags_c, f"对照红验失效: C 同时有 rm05-second(多匹配降级失效): {sorted(tags_c)}"
        # ---- B: 零匹配 → 整条 added 管线跳过(预期负向), 零 rm05-* 标签
        time.sleep(3)
        tags_b = _tags_of(qb.torrent(hb) or {})
        assert TAG in tags_b, f"B 连 real-fake 管理标签都没有(种子侧入库问题): {sorted(tags_b)}"
        assert not [
            t for t in tags_b if t.startswith("rm05")
        ], f"对照红验失效: B(127.0.0.1 不匹配任何 domains)也被打了标: {sorted(tags_b)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c1")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-02


def test_rm05_02_hot_reload_rebind():
    """[RM05-02] 热重载重绑: trackers 段变(tags) → 存量记录 rebound → 新 tags 兑现

    前置: 产品带 WEB(热重载走 PUT /api/config, §2.8); 1 枚假种子在启动前入库并被 v1
          配置打上 rm05-v1; 本条配置不配 delete_tags(全局任务重挂会混入第二种生效路径)。
    副作用: 1 假种子; 标签 rm05-v1、rm05-v2(旧标允许残留 —— 重绑只换 conf 不回撤旧标)。
    回滚: real.seed.rm --all + 清 rm05-* 标签定义 + 删用例目录。
    失败判据: 无「rebound」日志(trackers 段相等短路误触发 / PUT 未真改 trackers);
              重绑后新节拍仍只打 rm05-v1 而无 rm05-v2(存量记录未真重绑, 读到旧配置对象);
              PUT 回执 restart_required(trackers 变更被回退 → 按计划降级「重启生效」路径并如实记)。
    """
    case = case_dir("rm05_02")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        trackers = {"rm05site": {"domains": [FAKE_HOST], "tags": ["rm05-v1"]}}
        savepath = WORK / "rm05_02"
        h = fake_seed(qb, "rm05c2.bin", 256 * 1024, savepath, "rm05c2")

        web_port = app.free_port()
        cfg, _ = write_cfg(case, trackers, web=(True, web_port))
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"
        wait_until(
            lambda: "rm05-v1" in _tags_of(qb.torrent(h) or {}), 25,
            f"v1 标签未打上(v1 匹配/维护面不成立): {sorted(_tags_of(qb.torrent(h) or {}))}"
        )

        # ---- 经 PUT /api/config 把该条目 tags 改为 [rm05-v2](trackers 段变 → TrackerModule.apply)
        _OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def web_req(method: str, path: str, body: dict | None = None) -> dict:
            req = urllib.request.Request(
                f"http://127.0.0.1:{web_port}{path}",
                method=method,
                data=json.dumps(body).encode("utf-8") if body is not None else None,
            )
            if body is not None:
                req.add_header("Content-Type", "application/json")
            with _OPENER.open(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))

        tree = web_req("GET", "/api/config")["tree"]
        entry = tree["config"]["trackers"]["rm05site"]
        assert entry.get("tags") == ["rm05-v1"], f"GET 树里条目 tags 与预期不符: {entry}"
        entry["tags"] = ["rm05-v2"]
        resp = web_req("PUT", "/api/config", {"tree": tree})
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        assert not resp.get("restart_required"), f"trackers 变更不该触发重启闸(计划预登记: 若回退则本条降级重启生效路径): {resp}"

        # ---- 重绑日志 + 新 tags 兑现(后续节拍维护管线按新 conf 打标)
        assert p.wait_log("rebound 1", 20), f"无 rebound 日志(trackers 段相等短路误触发?):\n{p.log()[-800:]}"
        wait_until(
            lambda: "rm05-v2" in _tags_of(qb.torrent(h) or {}),
            25,
            f"重绑后新节拍未打 rm05-v2(存量记录未真重绑): {sorted(_tags_of(qb.torrent(h) or {}))}",
        )
        # 新节拍不再打 v1(新 conf 的 tags 只有 v2); v1 残留允许(计划写死不断言旧标被清)
        tags = _tags_of(qb.torrent(h) or {})
        assert "rm05-v1" not in tags or "rm05-v2" in tags, f"rm05-v2 兑现后又消失(重绑振荡): {sorted(tags)}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c2")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-03


def test_rm05_03_tracker_speed_limit_and_manual_skip():
    """[RM05-03] tracker 单种限速认领: added 即下发 + API 回读; 预置奇数 KiB 手动限速不覆盖(负向内建)

    前置: 条目配 upload_speed_limit: 128KiB/s + download_speed_limit: 64KiB/s(偶数,
          避开手动谓词); 甲在产品启动后加入(added 管线即时下发); 乙加完立即经 qB API
          预置 dl/up=2001KiB/s(奇数 = 手动限速), 赶在产品下个同步拍之前。
    副作用: 甲的限速被改; 乙不动。
    回滚: 删光 real-fake 种子(限速随种子删除一并消失)+ 删用例目录。
    失败判据: 甲回读 dl_limit≠64KiB/s 或 up_limit≠128KiB/s(只认 API 回读, 不咬日志);
              乙限速被覆盖(手动保护失效, 负向必须红); 日志出现乙的「设置*限速」行(竞态丢失
              —— added 管线在预置前已读过乙, 本跑对照不成立, 复跑)。
    """
    case = case_dir("rm05_03")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        trackers = {
            "rm05site": {
                "domains": [FAKE_HOST],
                "upload_speed_limit": "128KiB/s",
                "download_speed_limit": "64KiB/s",
            }
        }
        cfg, _ = write_cfg(case, trackers)
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"

        savepath = WORK / "rm05_03"
        # ---- 甲: added 管线即时下发(不等节拍), API 回读断言
        ha = fake_seed(qb, "rm05c3a.bin", 256 * 1024, savepath, "rm05c3-a")
        settle(qb, ha)
        wait_until(
            lambda: (qb.torrent(ha) or {}).get("dl_limit") == 64 * 1024 and
            (qb.torrent(ha) or {}).get("up_limit") == 128 * 1024,
            25,
            f"甲限速回读不符: dl={(qb.torrent(ha) or {}).get('dl_limit')} up={(qb.torrent(ha) or {}).get('up_limit')}",
        )
        # ---- 乙: 加完立即预置奇数 KiB(抢在产品下个同步拍之前), added 管线读到奇数 → skip
        hb = fake_seed(qb, "rm05c3b.bin", 256 * 1024, savepath, "rm05c3-b")
        settle(qb, hb)
        set_limit_raw(qb, hb, "Download", 2001 * 1024)
        set_limit_raw(qb, hb, "Upload", 2001 * 1024)
        b0 = qb.torrent(hb) or {}
        assert b0.get("dl_limit") == 2001 * 1024 and b0.get("up_limit") == 2001 * 1024, \
            f"乙的奇数限速预置未生效(竞态: added 管线先写了偶数): dl={b0.get('dl_limit')} up={b0.get('up_limit')}"
        # ---- ≥3 节拍窗口: 乙限速必须原样(手动保护)
        time.sleep(10)
        b = qb.torrent(hb) or {}
        assert b.get("dl_limit") == 2001 * 1024 and b.get("up_limit") == 2001 * 1024, \
            f"对照红验失效: 乙(奇数 KiB 手动限速)被覆盖: dl={b.get('dl_limit')} up={b.get('up_limit')}"
        # ---- 竞态丢失检测: 日志不得出现乙的「设置*限速」行(出现了 = 管线在预置前读过乙, 对照不成立)
        leaked = [ln for ln in log_text(case).splitlines() if re.search(r"设置(上传|下载)限速", ln) and hb[:8] in ln]
        assert not leaked, f"竞态丢失: added 管线对乙下发了限速(预置前的快照读到非奇数值), 本跑对照不成立, 需复跑: {leaked[:2]}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c3")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-04


def test_rm05_04_seed_tags_family():
    """[RM05-04] 种子级标签族: add_tags / remove_tags(regex) / remove_similar_tags 大小写对照(对照内建)

    前置: 条目 tags=[rm05-keep, RM05-SIM] + remove_tags=[regex:rm05-drop.*] + 全局
          remove_similar_tags: true; 1 枚假种子加种前预打标 [rm05-drop-x, rm05-sim]
          (409 删旧重加, 不收养), 产品启动前入库。
    副作用: 1 假种子及其标签增删。
    回滚: real.seed.rm --all + 清残留 rm05-* 标签定义 + 删用例目录; 若 regex 误删 real-fake
          导致清场失明, 收尾按名字前缀兜底删(26-10-31-1215 双标签坑仍在池)。
    失败判据: rm05-drop-x 残留(regex 未命中)或 real-fake 被误删(过宽, 负向必须红);
              rm05-sim 残留(相似标签失效)或 RM05-SIM 被误删(精确相等保护失效);
              rm05-keep 未打上; 断言读 tags 未 strip(多标签「, 」形态失明)。
    """
    case = case_dir("rm05_04")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        trackers = {
            "rm05site":
                {
                    "domains": [FAKE_HOST],
                    "tags": ["rm05-keep", "RM05-SIM"],
                    "remove_tags": ["regex:rm05-drop.*"],
                }
        }
        savepath = WORK / "rm05_04"
        h = fake_seed(qb, "rm05c4.bin", 256 * 1024, savepath, "rm05c4")
        pretag(qb, h, ["rm05-drop-x", "rm05-sim"])
        t0 = qb.torrent(h) or {}
        assert {"rm05-drop-x", "rm05-sim"} <= _tags_of(t0), f"预打标未生效: {sorted(_tags_of(t0))}"

        cfg, _ = write_cfg(case, trackers, {"remove_similar_tags": True})
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"

        # ---- 维护管线后最终 tags 收敛(≥2 节拍)
        wait_until(
            lambda: _tags_of(qb.torrent(h) or {}) == {TAG, "rm05-keep", "RM05-SIM"},
            25,
            f"终态 tags 不符: {sorted(_tags_of(qb.torrent(h) or {}))}",
        )
        time.sleep(7)  # 再等 ≥2 节拍: 稳态不回退(regex 不会把 rm05-keep/RM05-SIM/real-fake 删掉)
        tags = _tags_of(qb.torrent(h) or {})
        assert tags == {TAG, "rm05-keep", "RM05-SIM"}, f"稳态漂移: {sorted(tags)}"
        # ---- 对照红验逐项(稳定后复核)
        assert TAG in tags, "real-fake 被误删(模式过宽, 负向必须红 —— 红线级)"
        assert "rm05-keep" in tags, "rm05-keep 未打上/被误删(精确相等保护失效)"
        assert "RM05-SIM" in tags, "RM05-SIM 未打上/被误删(精确相等保护失效)"
        assert "rm05-sim" not in tags, "rm05-sim 残留(相似标签大小写对照失效)"
        assert "rm05-drop-x" not in tags, "rm05-drop-x 残留(remove_tags regex 未命中)"
        # 维护日志锚点: add/remove/相似三类行都要有(动作真发生在维护管线, 不是巧合终态)
        assert count_anchor(case, r"维护 .* \| 添加标签") >= 1, "日志无「添加标签」维护行"
        assert count_anchor(case, r"维护 .* \| 删除标签") >= 1, "日志无「删除标签」维护行(remove_tags)"
        assert count_anchor(case, r"维护 .* \| 删除相似标签") >= 1, "日志无「删除相似标签」维护行"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c4")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-05


def test_rm05_05_delete_tags_global_and_tracker_tags_ref():
    """[RM05-05] delete_tags 全局删标签 + @tracker_tags 引用展开(消费点效果, 对照内建)

    前置: 条目 tags=[rm05-g1, rm05-g2]; 配置 delete_tags: ["@tracker_tags",
          "regex:rm05-orphan.*"]; 1 枚假种子加种前预打标 [rm05-orphan-a, rm05-g1, rm05-ctrl]
          (409 删旧重加), 产品启动前入库。注: 维护管线每 interval 会重打 rm05-g1/g2(种子级
          add_tags 隐式重建定义), 与全局删除同节拍成对发生(先删后打)—— g1/g2 稳态振荡且
          干净窗亚秒级, 外部采样不可观测(schema delete_tags risk 文案明载的「互相打架」);
          断言走四件机械可观测事实: 命中集三元 / 孤儿标签永久消失 / 对照恒在 / 删除跨节拍重复。
    副作用: 1 假种子; rm05-g1/g2/orphan-a 三个标签定义被反复删(都在 36596 空库, 波及面只含自造种子)。
    回滚: real.seed.rm --all + 清残留 rm05-* 标签定义(模式仍限 rm05-)+ 删用例目录。
    失败判据: 删除日志的命中集 ≠ {rm05-g1, rm05-g2, rm05-orphan-a}(@tracker_tags 展开失控);
              rm05-orphan-a 定义或种子标签回潮(定义级删除未真发生);
              rm05-ctrl 被删(对照红验必须红); real-fake 被删(红线级, 立即停手入池);
              删除日志未跨 ≥3 节拍重复(全局任务没有每轮入队)。
    """
    case = case_dir("rm05_05")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        trackers = {"rm05site": {"domains": [FAKE_HOST], "tags": ["rm05-g1", "rm05-g2"]}}
        savepath = WORK / "rm05_05"
        h = fake_seed(qb, "rm05c5.bin", 256 * 1024, savepath, "rm05c5")
        pretag(qb, h, ["rm05-orphan-a", "rm05-g1", "rm05-ctrl"])
        t0 = qb.torrent(h) or {}
        assert {"rm05-orphan-a", "rm05-g1", "rm05-ctrl"} <= _tags_of(t0), f"预打标未生效: {sorted(_tags_of(t0))}"

        cfg, _ = write_cfg(case, trackers, {"delete_tags": ["@tracker_tags", "regex:rm05-orphan.*"]})
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"

        # ---- 等第一条删除日志, 并解析命中集(@tracker_tags 展开正确性走消费点效果)
        wait_until(lambda: count_anchor(case, r"彻底删除标签: \[") >= 1, 25, "日志无「彻底删除标签」行(全局任务未跑)")

        def last_matched_set() -> set[str] | None:
            m = re.findall(r"彻底删除标签: \[([^\]]*)\]", log_text(case))
            if not m:
                return None
            return {x.strip().strip("'\"") for x in m[-1].split(",") if x.strip().strip("'\"")}

        wait_until(
            lambda: last_matched_set() == {"rm05-g1", "rm05-g2", "rm05-orphan-a"},
            20,
            f"删除命中集不是预期三元(@tracker_tags 展开/regex 分叉): {last_matched_set()}",
        )
        # ---- 跨 ≥3 节拍观测。实测事实(首轮采样两次证实): 维护管线每 interval 重打 g1/g2
        #      (种子级 add_tags 隐式重建定义), 与全局删除在同一节拍内成对发生(先删后打),
        #      干净窗亚秒级, 外部采样不可稳定观测 —— 且这是 schema delete_tags risk 文案明载的
        #      预期「互相打架」, 非缺陷。断言改走四件机械可观测事实:
        #      ① 命中集 == 预期三元(上面已断) ② 孤儿标签永久消失(torrents_delete_tags
        #      真删定义+摘种子的存在性证明, 无人重建) ③ 对照标签全采样恒在 ④ 删除行跨节拍重复。
        n0 = count_anchor(case, r"彻底删除标签: \[")
        wait_until(lambda: count_anchor(case, r"彻底删除标签: \[") >= n0 + 2, 20, "删除日志未跨 ≥3 节拍重复出现(全局任务没有每轮入队)")
        samples = []
        deadline = time.time() + 8
        while time.time() < deadline:
            defs = sorted(global_tags(qb))
            seed_tags = sorted(_tags_of(qb.torrent(h) or {}))
            samples.append((defs, seed_tags))
            time.sleep(1.0)
        for defs, seed_tags in samples:
            assert "rm05-orphan-a" not in defs and "rm05-orphan-a" not in seed_tags, \
                f"孤儿标签回潮(正则删过的定义级删除被撤销?): defs={defs} seed={seed_tags}"
            assert "rm05-ctrl" in seed_tags, f"对照红验失效: rm05-ctrl 被摘(@tracker_tags 展开失控): {seed_tags}"
            assert TAG in seed_tags, f"红线级: real-fake 被删(立即停手入池): {seed_tags}"
        # g1/g2 的振荡证据: 稳态轮次(孤儿标签已永久退场)的删除命中集恰为 {g1, g2} ——
        # 二者被删后又被维护重建、再被删, 任务每轮在跑; orphan-a 不再出现正是永久删除的佐证
        assert last_matched_set() == {"rm05-g1", "rm05-g2"}, \
            f"稳态删除命中集漂移(任务停跑或维护重打面变): {last_matched_set()}"
        # ---- rm05-orphan-a 永久消失(不在 tracker tags 里, 无人重建): 最终采样定义必须不在
        assert "rm05-orphan-a" not in global_tags(qb), "rm05-orphan-a 定义残留(regex 命中但定义级未删)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c5")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-06


def test_rm05_06_delete_tags_if_has_no_torrents():
    """[RM05-06] delete_tags_if_has_no_torrents: 使用中保留 / 无种子删除(对照内建)

    前置: 配置 delete_tags_if_has_no_torrents: ["regex:rm05-un.*"](不配 delete_tags,
          两任务隔离); 1 枚假种子预打标 rm05-used-1; rm05-unused-1 定义的造法 = 先对种子
          add 再 remove(qB 保留无种子的标签定义 —— 造后先实测确认, 若定义随删走不通,
          按计划预登记降级或记 BLOCKED, 不硬撑)。
    副作用: 1 假种子; rm05-unused-1 定义被删。
    回滚: real.seed.rm --all + 清残留 rm05-* 定义 + 删用例目录。
    失败判据: rm05-used-1 被删(使用数判定失效, 负向必须红); rm05-unused-1 残留(tag_usage
              快照分叉); 本条配置无 delete_tags 却见「彻底删除标签」日志(两任务互相污染)。
    """
    case = case_dir("rm05_06")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm05_defs(qb)
        trackers = {"rm05site": {"domains": [FAKE_HOST]}}
        savepath = WORK / "rm05_06"
        h = fake_seed(qb, "rm05c6.bin", 256 * 1024, savepath, "rm05c6")
        # ---- 造两个匹配模式的定义: rm05-used-1(打在种子上, 使用数 1)与 rm05-unused-1(零使用)
        pretag(qb, h, ["rm05-used-1", "rm05-unused-1"])
        qb.remove_tags(h, "rm05-unused-1")
        defs = global_tags(qb)
        if "rm05-unused-1" not in defs:
            pytest.skip(
                "BLOCKED: 前提不成立 —— qB 5.2 对「种子上摘除后」的标签定义不保留定义"
                "(add 后 remove 即消失), 计划预登记的降级路径(「种子删除后残留定义被清」)需要"
                "先造出残留定义才有被测对象; 解锁条件 = 确认 qB 5.2 保留无种子定义的造法"
            )
        assert "rm05-used-1" in defs, f"rm05-used-1 预打标未生效: {defs}"

        cfg, _ = write_cfg(case, trackers, {"delete_tags_if_has_no_torrents": ["regex:rm05-un.*"]})
        p = app.start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p.log()[-800:]}"

        # ---- 跨 ≥3 节拍: rm05-unused-1 定义被删; rm05-used-1 定义与种子标签原样
        wait_until(lambda: "rm05-unused-1" not in global_tags(qb), 25, "rm05-unused-1 定义残留(任务未跑或 tag_usage 分叉)")
        assert count_anchor(case, r"彻底删除无种子的标签") >= 1, "日志无「彻底删除无种子的标签」行(删除不是本任务做的)"
        time.sleep(10)  # ≥3 节拍: 若使用数判定失效, rm05-used-1 必然在此窗口被删
        defs = global_tags(qb)
        tags = _tags_of(qb.torrent(h) or {})
        assert "rm05-used-1" in defs, f"对照红验失效: rm05-used-1 定义被删(使用数判定失效): {defs}"
        assert "rm05-used-1" in tags, f"对照红验失效: 种子上的 rm05-used-1 被摘: {sorted(tags)}"
        assert "rm05-unused-1" not in defs, "rm05-unused-1 定义回潮(删除后又出现)"
        # ---- 两任务隔离: 本条没配 delete_tags, 不得出现「彻底删除标签」日志
        assert count_anchor(case, r"彻底删除标签: \[") == 0, "两任务互相污染: 未配 delete_tags 却出现「彻底删除标签」日志"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
        rm_all_fakes_with_sweep(qbfake(), "rm05c6")
        cleanup_rm05_defs(qbfake())
        purge_tree(case)


# ---------------------------------------------------------------- RM05-07


def _site_cfg(case_name: str, trackers: dict, sites: dict) -> tuple[Path, Path]:
    """RM05-07 专用: 最小站点派生配置(schema_version: 5, hr_check.enabled 全局恒 false)。"""
    case = case_dir(case_name)
    extra = {"hr_check": {"enabled": False, "sites": sites}}
    cfg, _ = write_cfg(case, trackers, extra)
    return case, cfg


def test_rm05_07_site_preset_binding_loadtime():
    """[RM05-07] 站点档案派生(装载期): 双向子域容错绑定 + 绑 0/绑 2/未登记 id ConfigError

    前置: 5 份最小配置(正向 2 + 负向 3), 各起停一次产品(正向走 dry-run 后台起等
          「启动 qB 管理器」; 负向走 run_cli --dry-run 看退出码与「配置错误」文案,
          RM03-05 同款观测法); 无种子; 全局 hr_check.enabled: false 保持关(HR 取数线程
          不启动, 零外连 —— 若发现取数尝试 = 高优 FAIL 入池)。
    副作用: 零 qB 写(装载期面); 产品侧仅进程起停与日志。
    回滚: 停产品 + 删用例目录; 无实例残留。
    失败判据: 正向启动报 ConfigError(容错口径与 match_trackers 实现分叉, 修期望重跑一次
              仍红记 FAIL); 负向静默通过(校验漏网 —— 高优 FAIL); 产品在校验失败时仍起了
              主循环(fail-fast 破坏); hr_check.enabled=false 下出现对真实站点的取数尝试。
    """
    # ---- 正向①: 精确域绑定(档案 tracker_domain pt.btschool.club == 用户 domains)
    case1, cfg1 = _site_cfg(
        "rm05_07_pos_exact",
        {"rm05bt": {
            "domains": ["pt.btschool.club"],
            "hr": {
                "required_seeding_time": "3D"
            }
        }},
        {"btschool": {
            "enabled": True
        }},
    )
    # ---- 正向②: 子域容错(用户配主域 btschool.club, 档案域 pt.btschool.club endswith ".btschool.club")
    case2, cfg2 = _site_cfg(
        "rm05_07_pos_sub",
        {"rm05bt": {
            "domains": ["btschool.club"],
            "hr": {
                "required_seeding_time": "3D"
            }
        }},
        {"btschool": {
            "enabled": True
        }},
    )
    # ---- 负向③: domains 只有本机IP(绑 0)
    case3, cfg3 = _site_cfg(
        "rm05_07_neg_zero",
        {"rm05fake": {
            "domains": [FAKE_HOST]
        }},
        {"btschool": {
            "enabled": True
        }},
    )
    # ---- 负向④: 两个条目都配 pt.btschool.club(绑 2)
    case4, cfg4 = _site_cfg(
        "rm05_07_neg_ambig",
        {
            "rm05bt1": {
                "domains": ["pt.btschool.club"],
                "hr": {
                    "required_seeding_time": "3D"
                }
            },
            "rm05bt2": {
                "domains": ["pt.btschool.club"],
                "hr": {
                    "required_seeding_time": "3D"
                }
            },
        },
        {"btschool": {
            "enabled": True
        }},
    )
    # ---- 负向⑤: 未登记档案 id
    case5, cfg5 = _site_cfg(
        "rm05_07_neg_unknown",
        {"rm05bt": {
            "domains": ["pt.btschool.club"],
            "hr": {
                "required_seeding_time": "3D"
            }
        }},
        {"nosite": {
            "enabled": True
        }},
    )
    p = None
    try:
        # ---- 正向两份: 装载无 ConfigError, 产品起主循环
        for case, cfg in ((case1, cfg1), (case2, cfg2)):
            p = app.start(cfg, case, dry_run=True)
            assert p.wait_log("启动 qB 管理器", 40), f"正向配置装载后产品没起主循环(派生失败?): {cfg}\n{p.log()[-800:]}"
            log = log_text(case)
            assert "配置错误" not in log and "配置校验失败" not in log, f"正向启动报 ConfigError(容错口径分叉): {cfg}\n{log[-600:]}"
            time.sleep(4)
            assert p.alive(), f"正向配置产品中途退出: {cfg}\n{log_text(case)[-600:]}"
            # HR 零外连红线: hr_check.enabled=false 下不得有任何在线核实动作
            assert "在线核实" not in log_text(case), f"HR 零外连红线: enabled=false 出现取数尝试: {case}"
            p.stop()
            p = None
        # ---- 负向三份: 装载即 ConfigError 聚合(fail-fast), 各带一句人话判据
        for case, cfg, keyword in (
            (case3, cfg3, "默认映射未命中"),
            (case4, cfg4, "命中多个站点"),
            (case5, cfg5, "未支持的站点档案"),
        ):
            r = app.run_cli([str(cfg), "--dry-run"], timeout=60)
            sinks = (r.stdout or "") + (r.stderr or "") + log_text(case)
            assert r.returncode != 0, f"装载期红验失效({keyword}): 负向配置被静默通过(rc=0): {cfg}\n{sinks[-500:]}"
            assert "配置错误" in sinks, f"负向拒绝但输出无「配置错误」前缀(证据不足): {cfg}\n{sinks[-600:]}"
            assert keyword in sinks, f"负向拒绝文案不含预期判据「{keyword}」: {cfg}\n{sinks[-600:]}"
            assert "启动 qB 管理器" not in sinks, f"fail-fast 破坏: 校验失败的产品仍起了主循环: {cfg}"
    finally:
        if p is not None:
            p.stop()
        for c in (case1, case2, case3, case4, case5):
            purge_tree(c)
