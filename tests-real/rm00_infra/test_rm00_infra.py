"""[RM00] 基建用例: 守卫三层 + 假种子 L1 + 双实例互传 L2。

对应规程 `memory-bank/testing/real-machine.md` §03 的验收三条; 计划 26-10-31-0705 §04 的 S2/S4/S5。
每条用例的四行(前置 / 副作用 / 回滚 / 失败判据)写在 docstring 里 —— 这是本轨的固定体例。
"""
from __future__ import annotations

import time

import pytest

from lib import guard, net, torrent

PRIMARY, SECONDARY = 36595, 36596


def _purge(qb, infohash: str) -> None:
    """幂等清理: 上一条用例失败时可能留下同 infohash 的种子(qB 对重复 add 返回 409 Conflict)。"""
    try:
        if qb.torrent(infohash):
            qb.delete(infohash, delete_files=True)
    except Exception:
        pass


def _tracker_urls(qb, infohash: str) -> set:
    """取种子上的真实 tracker 地址。

    `/torrents/trackers` 会把 DHT / PeX / LSD 也当条目返回, url 形如 `** [DHT] **`,
    它们不是网络地址, 直接丢进 is_local_url 会误报, 所以先按 http 前缀滤掉。
    """
    return {tr["url"] for tr in qb.trackers(infohash)
            if str(tr.get("url") or "").startswith("http")}


def _wait(fn, timeout: float, interval: float = 1.0, what: str = "条件"):
    """轮询直到 fn() 为真; 超时返回最后一次取值(由调用方断言, 便于把现场写进失败信息)。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    return last


# ---------------------------------------------------------------- RM00-01
def test_rm00_01_guard_whitelist():
    """[RM00-01] 守卫第一层: 非白名单端口一律拒跑, 白名单端口必须核出测试目录下的镜像路径。

    前置: 36595 实例在跑(L0)。
    副作用: 无(只读端口与进程)。
    回滚: 无需。
    失败判据: 非白名单端口未抛 GuardError, 或白名单端口核不出镜像路径 / 镜像不在测试目录下。
    """
    for bad in (9999, 8080, 16585):
        with pytest.raises(guard.GuardError):
            guard.check_port(bad)
    rep = guard.check_port(PRIMARY)
    assert rep["image"].lower().startswith(tuple(p.lower() for p in guard.IMAGE_PREFIXES)), rep


# ---------------------------------------------------------------- RM00-02
def test_rm00_02_guard_pauses_real_torrents(env):
    """[RM00-02] 守卫第二层: 真实种子全部非活跃(前置归零的结果, 也是看门狗的保护面)。

    前置: 两实例在跑; 36595 有真实种子(L0)。
    副作用: 无(只读状态; 归零已在 fixture 里做过)。
    回滚: 无需。
    失败判据: 任一受保护种子处于活跃状态或速率非 0。
    """
    for port, hashes in env["protected"].items():
        qb = env["qbs"][port]
        bad = guard.active_torrents(qb, hashes)
        assert not bad, f"端口 {port} 有真实种子活跃: {[(t['name'], t['state'], t['upspeed']) for t in bad]}"


# ---------------------------------------------------------------- RM00-03
def test_rm00_03_instances_online(env):
    """[RM00-03] 守卫第 1.5 层: 两实例都必须"在线"(有可用 BT 监听 socket)。

    前置: 两实例在跑。
    副作用: 无(只读 `/transfer/info`)。
    回滚: 无需。
    失败判据: 任一实例 `connection_status == disconnected` —— 此时它一个 announce 都不会发,
              后面所有"零流量"结论都是假的(实测 36596 的 BT 端口撞上生产实例就是这样)。

    注意 `firewalled` 是**通过**: 本地互传不需要端口映射, 只要有监听 socket 就行。
    """
    for port, rep in env["reports"].items():
        assert rep["connection"] in ("connected", "firewalled"), f"端口 {port} 状态异常: {rep['connection']}"
        # 复核一次: fixture 到用例之间可能有人动过实例
        assert env["qbs"][port].connection_status() != "disconnected", f"端口 {port} 在用例执行时掉线"


# ---------------------------------------------------------------- RM00-04
def test_rm00_04_l1_fake_torrent_zero_traffic(primary, tracker, workdir):
    """[RM00-04] L1 正向: 构造种子 + 伪 tracker ⇒ 做种中但零流量, 且 qB 真的报到过。

    前置: 36595 在跑 + 伪 tracker 在跑(L1)。
    副作用: 往 36595 加一个自造种子(announce 只指本机, 见 lib/net.py 为何不用 127.0.0.1), 结束后连文件一起删。
    回滚: finally 里 delete(delete_files=True) + 删临时目录。
    失败判据: 60s 内未进入稳定态 / 伪 tracker 零 announce / 60s 内出现非 0 速率 / tracker 里有非本地地址。
    """
    data = torrent.payload()
    raw, ih = torrent.build("rm00-l1.bin", data, tracker.url)
    save = workdir / "l1"
    torrent.write_payload(str(save), "rm00-l1.bin", data)
    _purge(primary, ih)
    try:
        primary.add_torrent(raw, savepath=str(save), paused=False, infohash_hint=ih)
        t = _wait(lambda: (primary.torrent(ih) or {}).get("state") in ("stalledUP", "uploading", "pausedUP")
                  and tracker.count(ih) >= 1 and primary.torrent(ih), 60, what="稳定态+announce")
        assert t, f"60s 内未稳定: {primary.torrent(ih)} / announce={tracker.count(ih)}"
        assert tracker.count(ih) >= 1, "伪 tracker 没收到 announce —— stalledUP 可能只是没报到"

        samples = []
        for _ in range(30):  # 30 × 2s = 60s, 与规程 §03 的「持续 ≥60s」对齐
            cur = primary.torrent(ih)
            samples.append((cur["upspeed"], cur["dlspeed"]))
            time.sleep(2)
        assert all(u == 0 and d == 0 for u, d in samples), f"出现非零速率: {samples}"

        urls = _tracker_urls(primary, ih)
        assert urls and all(net.is_local_url(u) for u in urls), f"tracker 含非本机地址: {urls}"
    finally:
        _purge(primary, ih)


# ---------------------------------------------------------------- RM00-05
def test_rm00_05_l1_no_external_contact(primary, tracker, workdir):
    """[RM00-05] L1 反向: 伪 tracker 挂掉后种子不产生任何外连(证明流量物理上出不去)。

    前置: 同 RM00-04。
    副作用: 同 RM00-04(种子在用例内自删)。
    回滚: finally 删种子与临时目录。
    失败判据: 出现 peer 连接 / 速率非 0 / tracker 列表里有非本机地址。
    """
    data = torrent.payload(seed=b"auto-qb-rm00-reverse")
    raw, ih = torrent.build("rm00-l1-rev.bin", data, tracker.url)
    save = workdir / "l1rev"
    torrent.write_payload(str(save), "rm00-l1-rev.bin", data)
    _purge(primary, ih)
    try:
        primary.add_torrent(raw, savepath=str(save), paused=False, infohash_hint=ih)
        assert _wait(lambda: tracker.count(ih) >= 1, 60, what="首次 announce"), "伪 tracker 一次 announce 都没收到"
        before = tracker.count(ih)
        tracker.stop()
        time.sleep(10)  # 给 qB 至少两轮重连(interval=5s)
        cur = primary.torrent(ih)
        assert tracker.count(ih) == before, "tracker 已停但 announce 计数还在涨 —— 停的不是它"
        assert cur["connections_count"] == 0, f"出现了 peer 连接: {cur['connections_count']}"
        assert cur["upspeed"] == 0 and cur["dlspeed"] == 0, (cur["upspeed"], cur["dlspeed"])
        urls = _tracker_urls(primary, ih)
        assert urls and all(net.is_local_url(u) for u in urls), f"tracker 含非本机地址: {urls}"
    finally:
        _purge(primary, ih)


# ---------------------------------------------------------------- RM00-06
def test_rm00_06_l2_peer_transfer(primary, secondary, tracker, workdir, transfer_limits):
    """[RM00-06] L2: 双实例互传 —— 36596 从 36595 拉完同一构造种子, 全程只打本地 tracker。

    前置: 两实例在跑 + 伪 tracker 在跑; 两端 listen_port 不同且都绑在局域网 IP 上(实测 26803 / 60539)。
    副作用: 两端各加一个自造种子并互传 2MB; 限速临时钉成 256 KiB/s(见 transfer_limits), 结束后还原。
    回滚: finally 里两端 delete(delete_files=True); 限速由 fixture 还原。
    失败判据: 180s 内 progress < 1.0 / 做种端 upspeed>0 观测不足 5s / 完成后 seeding_time 不增长 /
              任一端 tracker 非本地 / 伪 tracker 只收到一端 announce。
    """
    payload = 2 * 1024 * 1024
    data = torrent.payload(size=payload, seed=b"auto-qb-rm00-l2")
    raw, ih = torrent.build("rm00-l2.bin", data, tracker.url)
    src, dst = workdir / "seed", workdir / "leech"
    torrent.write_payload(str(src), "rm00-l2.bin", data)
    dst.mkdir(parents=True, exist_ok=True)

    seed_port = int(primary.prefs()["listen_port"])
    tracker.peers = [(net.local_host(), seed_port)]
    _purge(primary, ih)
    _purge(secondary, ih)
    try:
        primary.add_torrent(raw, savepath=str(src), paused=False, infohash_hint=ih)
        secondary.add_torrent(raw, savepath=str(dst), paused=False, infohash_hint=ih)
        up_seconds = 0
        done = None
        deadline = time.time() + 180
        while time.time() < deadline:
            t1, t2 = primary.torrent(ih), secondary.torrent(ih)
            if t1 and t1["upspeed"] > 0:
                up_seconds += 1
            if t2 and t2["progress"] >= 1.0:
                done = t2
                break
            time.sleep(1)
        assert done is not None, (
            f"180s 未完成: leech={secondary.torrent(ih)} / seed={primary.torrent(ih)} / announce={tracker.count(ih)}")
        assert up_seconds >= 5, f"做种端 upspeed>0 只观测到 {up_seconds}s(需 ≥5s)"
        assert done["downloaded"] >= payload, f"leech 实际下载量不足: {done['downloaded']} < {payload}"
        # qB 的 uploaded 计数比 progress 慢一拍(实测差 ~20KB), 给它 15s 追平, 不要卡死在临界值上
        assert _wait(lambda: primary.torrent(ih)["uploaded"] >= payload, 15), \
            f"seed 实际上传量不足: {primary.torrent(ih)['uploaded']} < {payload}"
        assert tracker.count(ih) >= 2, f"伪 tracker 只收到 {tracker.count(ih)} 次 announce(需两端各至少一次)"

        st_before = primary.torrent(ih)["seeding_time"]
        time.sleep(6)
        assert primary.torrent(ih)["seeding_time"] > st_before, "完成后做种时间没有增长"
        for label, qb in (("seed", primary), ("leech", secondary)):
            urls = _tracker_urls(qb, ih)
            assert urls and all(net.is_local_url(u) for u in urls), f"{label} 端 tracker 含非本机地址: {urls}"
    finally:
        _purge(primary, ih)
        secondary.delete(ih, delete_files=True)
