"""WEB UI 浏览器冒烟桩服务(dev-only): 真实 create_app + 合成种子, 不连 qB

为什么需要它
------------
没有可用的浏览器自动化就跑不了这类验证, 而本项目有一整类改动**单测根本测不到**:
(历史背景: 写本脚本时 `agent-browser` 插件还是 1.0.0, 它的 SessionStart hook 在 Windows 上
直接判 `WINDIR` 打印"不支持 Windows"并退出, 连 CLI 都不装 ⇒ 当时只能自己搭。1.3.0 起该插件
已支持 Windows x64; 但本脚本走的是 Playwright, 与它无关, 不因此改变做法。
环境细节见 `memory-bank/techContext.md`「浏览器冒烟环境 (Playwright)」。)
乐观 UI 的半透明与失败回滚、按视图回传后切视图、表头同步是否还在每帧强制布局、
行窗口化后滚动是否跳动 —— 这些都属于"pytest 全绿但界面废掉"的故障形态(见
`test_web.py::test_frontend_static_bundle_health` 的同类守阵思路: 静态能查的静态查,
查不了的只能真跑浏览器)。

本脚本用**真实的** `auto_qb.webui.create_app` 起服务(端点/鉴权/静态挂载全是生产代码),
只把 manager 换成"灌了合成种子的真实 QbManager + FakeClient" —— 因此前端拿到的
响应体与真机同构(字段集/版本号/rid 门控均一致), 只是数据是人造的。

用法
----
    uv run python scripts/ui_harness.py --torrents 3000 --port 8099
    # 另开一个终端:
    node scripts/ui_smoke.cjs --base http://127.0.0.1:8099

参数
----
    --torrents N   合成种子总数(默认 1500; 用 3000 复现大库)
    --groups G     前 G×2 个种子两两归组(默认 200 组), 其余为未归组单种子
    --port P       监听端口(默认 8099)
    --no-groups    不建分组(纯平铺, 测种子页窗口化最快)
    --cmd-result   ok|error|hang(默认 ok): 兜底命令泵给每条命令的回执 ——
                   error 用于验证 P0-3 乐观 UI 的**失败回滚**, hang 用于验证 3s 回落真值

注意
----
* 仅开发期使用, 不参与打包; 数据全在内存 + 临时 state 文件, 关闭即弃。
* 鉴权走 `skip_local_verify`(本机免密钥), 浏览器不需要带 token。
  ❗正因如此 `--host` **只接受回环地址**(127.0.0.0/8 / ::1 / localhost) —— 绑 0.0.0.0
  等于把一个免鉴权的 WEB UI 交给整个局域网(合成数据也含配置结构), 直接拒绝启动。
"""
import argparse
import ipaddress
import os
import queue
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from auto_qb.config import WebConfig  # noqa: E402
from auto_qb.webui import create_app  # noqa: E402
from tests.helpers import FakeClient, FakeTorrent, make_manager, seed_store  # noqa: E402

_STATES = ["stalledUP", "uploading", "downloading", "pausedUP", "pausedDL", "stalledDL", "checkingUP", "errored"]
_SIZES = [2 * 1024**3, 8 * 1024**3, 25 * 1024**3, 60 * 1024**3]


def _make_torrents(count: int, site_conf):
    """合成种子: 名字/大小/状态/进度轮转, 保证每行列宽不整齐(更接近真机)"""
    out = []
    for i in range(count):
        size = _SIZES[i % len(_SIZES)]
        state = _STATES[i % len(_STATES)]
        done = i % 3 != 0  # 1/3 未完成, 让进度条/ETA 列有内容
        out.append(
            FakeTorrent(
                hash=f"{i:040x}",
                name=f"Some.Show.S01E{(i % 24) + 1:02d}.1080p.WEB-DL.x265-GROUP{i}",
                size=size,
                total_size=size,
                state=state,
                progress=1.0 if done else (i % 10) / 10,
                downloaded=size if done else size // 3,
                uploaded=int(size * ((i % 20) / 10)),
                dlspeed=0 if done else 1024 * (i % 900),
                upspeed=1024 * (i % 400),
                seeding_time=(i % 400) * 3600,
                ratio=(i % 30) / 10,
                added_on=1700000000 + i * 37,
                # magnet: 真实 qB 恒有(合成名 + 40 位 hash)。**必须给** —— 前端"复制磁力"
                # 要按需取详情读它(BUG-9), 桩里留空则那条断言退化成"永远提示没有 magnet"。
                magnet_uri=f"magnet:?xt=urn:btih:{i:040x}&dn=Some.Show.S01E{(i % 24) + 1:02d}",
                category=["", "Movies", "TV", "Anime"][i % 4],
                tags=",".join([t for k, t in enumerate(["HHan", "seed-3D", "low-ratio"]) if (i >> k) & 1]),
                tracker=f"https://tracker.hhanclub.net/announce/{i}",
                num_seeds=i % 40,
                num_leechs=i % 7,
                tracker_conf=site_conf,
            )
        )
    return out


# 桩服务"真改状态"用的目标状态(与后端 _state_kind 的口径一致: pausedDL -> kind=paused,
# uploading -> seeding, downloading -> downloading) —— 前端乐观补丁写的就是这几个 kind。
_PAUSED_STATE = "pausedDL"
_RESUME_DONE = "uploading"
_RESUME_TODO = "downloading"
# ❗刻意让**回执先到、状态后改**(复刻真机竞态: 服务端 P0-5 补刷新在回执**之后**才跑,
# 见 mixins/web_commands.py)。前端"回执后立刻拉真值"第一次会扑空(rid 还没变),
# 必须靠退避重试才拿得到 —— 这段延迟就是为了让重试逻辑被测到(issue 26-09-19-2024)。
_TRUTH_DELAY = 0.12


def _target_hashes(mgr, cmd: str, body: dict):
    """命令影响到的 hash 列表(桩里没有真实 qB, 只能按 payload 展开)"""
    if cmd in ("pause_torrent", "resume_torrent"):
        h = body.get("hash")
        return [h] if h else []
    if cmd in ("pause_group", "resume_group"):
        return list(mgr.store.groups.get(body.get("key") or (), []))
    if cmd == "bulk_torrents":
        out = list(body.get("hashes") or [])
        for k in body.get("keys") or []:
            out.extend(mgr.store.groups.get(k, []))
        return list(dict.fromkeys(out))
    return []


def _restore_state(mgr, hashes):
    """把 _apply_truth 改过的种子还原成**最初**的 state

    ❗为什么需要: 真机上"暂停"是永久的, 但桩服务是**长驻**的(起一次要跑很多轮冒烟, 红绿双验
    更是同一进程反复跑)。状态一旦永久累积, 跑过一轮"整剧暂停"(合成数据里一剧 = 全部种子)之后,
    下一轮冒烟里**所有行都是 s-paused** ⇒ 所有"挑一个未暂停的行"的断言全部假失败 —— 实测第二轮
    就 4 条断言因此变红, 而它们跟被测代码毫无关系。
    ❗记的是**最初**值(不是上一次命令后的值): pause→resume 连续两次操作同一批种子时, 若记
    "上一次", 回弹会把它们还原成暂停态。
    """
    orig = getattr(mgr, "_harness_orig_state", None) or {}
    touched = False
    for h in hashes:
        tor = mgr.store.by_hash.get(h)
        if tor is None or h not in orig:
            continue
        tor.state = orig[h]
        touched = True
    if touched:
        mgr.rebuild_views()


def _revert_after_consume(mgr, hashes, wait_ms: int):
    """等真值这一版**真的被 /api/state 取走**之后, 再等 wait_ms 回弹

    ❗不能直接 `Timer(revert_ms)` 定时回弹: 回弹可能跑在前端看到真值**之前**(实测一次"整组暂停"
    的撤下因此被拖到 4149ms —— 真值被回弹改回去了, 前端要等到下一次回弹才碰巧对上)。以
    `_web_pending_ver` 判"这一版已被消费"(它在 `ensure_group_state` 里被清空), 再等一小段,
    回弹就一定落在前端观测之后。
    """
    deadline = time.time() + 8.0
    while time.time() < deadline and getattr(mgr, "_web_pending_ver", None) is not None:
        time.sleep(0.05)
    time.sleep(max(0, wait_ms) / 1000.0)
    _restore_state(mgr, hashes)


def _apply_truth(mgr, cmd: str, body: dict, revert_ms: int = 0):
    """把命令**真的**落到合成数据上 —— 否则真值永远不到, 乐观态只能靠 3s 兜底收尾,
    于是任何「真值对齐」类断言都测不到东西(只会测到"走满 3s")。

    这也是本桩此前最大的失真: 只回 ok 不改状态, 于是 issue 26-09-19-2024 那种
    "真值到了也不清 pending"的缺陷在本地完全无法暴露。

    `revert_ms` > 0 时, 真值被前端取走后再等这么久把它还原(见 _revert_after_consume) ——
    让长驻桩服务可以反复跑而不累积状态。
    """
    act = body.get("action") if cmd == "bulk_torrents" else cmd.split("_", 1)[0]
    if act not in ("pause", "resume"):
        return
    orig = getattr(mgr, "_harness_orig_state", None)
    if orig is None:
        orig = {}
        mgr._harness_orig_state = orig
    hashes = _target_hashes(mgr, cmd, body)
    for h in hashes:
        tor = mgr.store.by_hash.get(h)
        if tor is None:
            continue
        orig.setdefault(h, tor.state)  # 只记最初值(见 _restore_state)
        if act == "pause":
            tor.state = _PAUSED_STATE
        else:
            tor.state = _RESUME_DONE if getattr(tor, "progress", 0) >= 1 else _RESUME_TODO
    mgr.rebuild_views()  # 版本号自增 ⇒ 前端下一次 /api/state 拿到新数组(而不是"版本未变"空响应)
    if revert_ms > 0 and hashes:
        threading.Thread(target=_revert_after_consume, args=(mgr, hashes, revert_ms), daemon=True).start()


def _start_command_pump(mgr, mode: str, revert_ms: int = 0, wait_ms: int = 0):
    """兜底命令泵: 桩服务没有主循环, 命令没人消费 ⇒ 前端 waitCmd 会一直轮询到超时。

    这里不**执行**命令(合成数据没有真实 qB 可打), 只按 mode 直接写回执, 让前端的命令
    闭环可测: ok = 正常完成(乐观值被真值取代), error = 失败(乐观值必须**回滚**),
    hang = 不回执(验证 3s 回落真值, 不留假状态)。
    """
    if mode == "hang":
        return None

    def _loop():
        while True:
            try:
                # ❗队列元素是 **2 元组** (cmd, body), cmd_id 在 body 里 —— 按 3 元组解包会抛
                # ValueError, 命令被吃掉且永远没有回执(前端一直轮询, 表现为"点了没反应")。
                _cmd, body = mgr.web_commands.get(timeout=0.2)
            except queue.Empty:
                continue
            except Exception:
                time.sleep(0.2)
                continue
            cmd_id = (body or {}).get("cmd_id")
            if not cmd_id:
                continue
            if mode == "error":
                # 失败**不改状态**: 前端必须回滚到原值(回滚干净由冒烟 error 模式断言)
                mgr._web_results[cmd_id] = {"status": "error", "error": "桩服务注入的失败(用于验证乐观 UI 回滚)"}
            else:
                if wait_ms:
                    # ❗模拟真机「主循环正忙着, 命令排在后面」: 回执与真值是**同一轮主循环**里
                    # 出来的, 所以两者一起延后 —— 不是只延后回执。本地桩没有主循环, wait_ms 恒为 0,
                    # 于是"命令投递到回执"这一段在本地从来测不到, 而真机上它恰恰是最长的那一段。
                    time.sleep(wait_ms / 1000.0)
                mgr._web_results[cmd_id] = {
                    "status": "ok",
                    "wait_ms": round(wait_ms, 1),  # 埋点口径与后端 _timing() 一致: 排队等主循环
                    "exec_ms": 1,
                }
                # 先回执、后改状态(复刻真机补刷新的错位, 见 _TRUTH_DELAY 注释)
                time.sleep(_TRUTH_DELAY)
                try:
                    _apply_truth(mgr, _cmd, body, revert_ms)  # ❗队列解出来的是 _cmd(与 cmd 区分开)
                except Exception as e:  # 桩的健壮性优先: 同步失败也不能拖死命令泵
                    print(f"[harness] 状态同步失败: {e}", file=sys.stderr)

    t = threading.Thread(target=_loop, name="harness-cmd-pump", daemon=True)
    t.start()
    return t


def _is_loopback(host: str) -> bool:
    """只认回环地址: `localhost` / `::1` / 127.0.0.0/8(含 `0.0.0.0` 之外的任何写法)"""
    if host in ("localhost", "::1"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="WEB UI 浏览器冒烟桩服务")
    ap.add_argument("--torrents", type=int, default=1500, help="合成种子总数")
    ap.add_argument("--groups", type=int, default=200, help="归组数量(每组 2 个种子)")
    ap.add_argument("--no-groups", action="store_true", help="不建分组(纯平铺)")
    ap.add_argument("--cmd-result", choices=["ok", "error", "hang"], default="ok", help="命令泵回执(默认 ok)")
    ap.add_argument(
        "--state-revert-ms",
        type=int,
        default=1500,
        help="真值**被 /api/state 取走后**再等多少 ms 还原成初始状态(默认 1500, 让长驻桩服务可反复跑;"
        " 0 = 不还原, 永久生效)。注意不是「真值生效后 N ms」—— 定时回弹会跑到前端观测之前"
        "(见 _revert_after_consume)",
    )
    ap.add_argument(
        "--cmd-wait-ms",
        type=int,
        default=0,
        help="模拟真机「主循环正忙, 命令排在其后」: 回执与真值**一起**延后这么久(两者出自同一轮"
        "主循环)。本地桩没有主循环, wait_ms 恒为 0 ⇒ 「命令投递→回执」这一段从来测不到, "
        "而真机上它往往是最长的那一段。0 = 瞬时(默认)",
    )
    ap.add_argument("--host", default="127.0.0.1", help="监听地址(**只接受回环**)")
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()

    # ❗本服务故意免鉴权(skip_local_verify), 绑到非回环等于把 WEB UI 交给整个局域网。
    if not _is_loopback(args.host):
        print(
            f"[harness] 拒绝启动: --host 只接受回环地址(127.0.0.0/8 / ::1 / localhost), 收到 {args.host!r}\n"
            "          该服务免鉴权, 绑非回环会把它暴露给同网段的任何人。",
            file=sys.stderr
        )
        return 2

    tmp = tempfile.mkdtemp(prefix="aqb-harness-")
    state_file = os.path.join(tmp, "state.json")
    mgr = make_manager(state_file)
    mgr.client = FakeClient()
    mgr.config.web = WebConfig(enabled=True, host=args.host, port=args.port, token="", skip_local_verify=True)
    mgr._last_conn_ok = True  # 状态栏显示"已连接"(否则前端走断连提示分支)

    site_conf = mgr.config.trackers["HHan"]
    torrents = _make_torrents(args.torrents, site_conf)
    seed_store(mgr, torrents)
    for tor in torrents:  # 抽屉/详情端点按 hash 取, 与 store 保持一致
        mgr.client.torrents[tor.hash] = tor

    if not args.no_groups:
        groups = {}
        for i in range(min(args.groups, len(torrents) // 2)):
            a, b = torrents[i * 2], torrents[i * 2 + 1]
            b.name = a.name  # 同组同名(真机: 同文件不同站)
            groups[(a.name, ())] = [a.hash, b.hash]
        mgr.store.groups = groups
    mgr.rebuild_views()
    _start_command_pump(mgr, args.cmd_result, args.state_revert_ms, args.cmd_wait_ms)

    app = create_app(mgr)
    print(
        f"[harness] http://{args.host}:{args.port}/atlas/  /prism/  种子={args.torrents} 组={len(mgr.store.groups)} 命令回执={args.cmd_result}",
        flush=True
    )

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
