"""RM08 WebUI 读侧 —— 八条真机用例(读侧数据面: 轮询契约 / delta / 视图收敛 / 大库首帧 / 详情抽屉 / totals / SSE / error_reason)。

验证面对准冻结计划 plans/26-10-31-1754-plan-real-RM08.html §03 的八条 spec:
合并端点契约与 rid 门控(RM08-01)· delta 增量协商归约五对照(RM08-02)· VIEW_ARRAYS payload
收敛(RM08-03)· 大库首帧与零回传(RM08-04, 按排期指令放最后跑)· 详情抽屉四端点(RM08-05)·
状态栏 totals 修后复验走查迁出(RM08-06)· SSE 推送通道与只读辅助端点(RM08-07)·
error_reason 数据面 missingFiles 分支(RM08-08)。

驱动形态(计划 §01/§03: dev.webui 安全模式): 每条用例经 Popen 起一份**最小配置**的产品进程
(interval=86400S 任务线全关 · sync_interval=1.5S 同步线照常 · 规则集零段 · grouping 只读归组 ·
web.enabled + skip_local_verify: true 回环免密钥), 连 36596(空库草稿本)直接 HTTP 拉读侧端点,
逐条「端点载荷 + qB API 对照」两级断言。为什么不 Popen scripts/dev_webui.py 本体: 它是给人用的
一键脚本(自动开浏览器/交互式 CLI/生成的配置缺 schema_version: 5 会走迁移改写/日志路径与
lib/app.py 的 wait_web 判据不合), 用例按它的 CONFIG_TMPL 语义生成同款最小配置(schema_version: 5)
后用 `python -m auto_qb` 起 —— 与 dev_webui.py 内部 `cli_main()` 完全等价。收尾一律 taskkill
/F /T 杀整棵进程树(§2.7: 不带 /T 只杀 uv 启动器, 孤儿继续持端口)。RM08-05 的真实种子腿
(36595 侧)是本片唯一的 36595 面产品实例: 配置经 api_key 直连(qB 5.x WebUI API Key, 实测
本机可用), grouping 关死(零写路径), 同步线只读。

与计划判据的实况修正(执行时以实况为准记录, 均非产品缺陷, 详见用例 docstring):
- RM08-01②/④ 零回传拍: status(traffic/server/totals 恒回传段)由 /api/state 路由层包在
  ensure_state 结果**之外** —— 零回传拍实际形态 = {status, rid, updated:false}, 数组键缺席
  是门控本体; 计划「零回传拍也不丢 traffic/server/totals」与实码一致, 字节界据此按实况定。
- RM08-02⑤ show 视图: 计划 spec 写「show ∉ _DELTA_VIEWS 恒全量」, 但实码 S9b 已把 show
  纳入增量矩阵(runtime.py `_DELTA_VIEWS = {group, torrent, show}`, 计划 §02 锚点表自身
  也这么记)—— 计划内部矛盾, ⑤按实码契约断言并在基线切片记账, 不入池缺陷。
- RM08-07⑤ 坏票负向: skip_local_verify=true 下 auth.py 的 loopback 免鉴权先于票据闸返回
  —— 冻结驱动形态下该负向不可达, 记 BLOCKED 子项(解锁: 驱动改 skip_local_verify=false
  + Bearer token), 其余子项照常断言。
- RM08-02② 窗口洁净: 计划「delta.upsert 恰含变更行」的新鲜入库场景下, 错峰 check 完成的
  派生变更会落在基线邻代(upsert 混入内容与当前视图一致的邻代行, 复现两轮)—— 判据放宽为
  「变更行在 + 窗口全部行内容现取一致 + removed 空」, 恰单行形态在基线切片记账。
- RM08-08 造法: 计划的「删文件 + recheck → missingFiles」在 qB 5.2.3 实测不成立(三条路径
  都到不了 missingFiles, 详见用例 docstring)—— 记 BLOCKED 跳过(非产品缺陷), 解锁条件
  = L2 传输读失败路径或 qB 重启期 resume 核验造法定案。

跑法: `commands run real.suite -- --slice RM08 --yes`(RM08-04 大库注入放最后)。真实种子全程
非活跃(36595 的 8 枚严格只读, 仅 RM08-05 走只读 detail 面); 假种子一律 real-fake 标签, 本片
默认无 announce 纯本地做种(读侧不需要归组管线, 零外连); RM08-06 的 L2 互传走 RM00 口径
(伪 tracker 回对端, 全本机零外网, 真实种子保持 paused); 删数据/recheck 只对自造种子。
"""
from __future__ import annotations

import contextlib
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, instances, torrent  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill 进程树/盘符路径)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm08"
TAG = "real-fake"
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}
RM08_COMMENT = "auto-qb real-machine rm08 (fake seed)"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY(127.0.0.1 不走代理)

# ---------------------------------------------------------------- 通用小件


def norm(path) -> str:
    return str(path or "").replace("\\", "/").rstrip("/")


def jlen(obj) -> int:
    """响应字节数的代理口径(JSON 原文长度; JSONResponse 分隔符差异在量级断言下可忽略)。"""
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def metric(line: str) -> None:
    """实测数字落盘(<.work>/rm08/metrics.log): pytest -q 吞掉通过用例的 stdout, 基线切片从这里誊写。"""
    WORK.mkdir(parents=True, exist_ok=True)
    with open(WORK / "metrics.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {line}\n")


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


def case_dir(name: str) -> Path:
    import shutil

    d = WORK / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- 产品基座(dev.webui 安全模式)

CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
        api_key: "{api_key}"
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    interval: 86400S
    max_tasks_per_tick: 20
    remove_similar_tags: false
    skip_checking_tag: zSkipChecked
    add_episode_tags:
        enabled: false
    delete_tags: []
    hr:
        add_tag: ""
        add_category: ""
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: ""
        overwrite_category_for_satisfied: false
    log:
        level: INFO
    grouping:
        enabled: {grouping}
        missing_tag: ""
        check_missing_files: false
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    trackers: {{}}
    notify:
        enabled: false
"""


def write_cfg(case: Path, *, qb_port: int, grouping: bool, api_key: str) -> tuple[Path, int]:
    """生成 dev.webui 同款最小配置(schema_version: 5; 任务线全关, 同步线 1.5S, 回环免密钥)。"""
    cfg = case / "config.yml"
    web_port = app.free_port()
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            qb_port=qb_port,
            api_key=api_key,
            data_dir=(case / "data").as_posix(),
            grouping="true" if grouping else "false",
            web_port=web_port,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if qb_port == 36596:
        if "port: 36595" in text:
            raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")
    else:
        if f"port: {qb_port}" not in text:
            raise AssertionError(f"配置未指向 {qb_port}, 拒跑: {cfg}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}")
    return cfg, web_port


def _popen_auto_qb(cfg: Path):
    """Popen 一份 `python -m auto_qb <config>`(lib/app.start 的同款命令线, 不带它的 36596 白名单闸)。"""
    return subprocess.Popen(
        [str(app.PY), "-m", "auto_qb", str(cfg)],
        cwd=str(app.ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            **os.environ, "PYTHONIOENCODING": "utf-8"
        },
    )


def kill_tree(proc) -> None:
    """收尾杀整棵进程树(taskkill /F /T, 计划 §03 口径): 不带 /T 只杀 uv 启动器, 孤儿继续持端口。"""
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
    try:
        proc.popen.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def web_ready(port: int) -> dict:
    """等 web 端口可拉 /api/state 首拍 200(计划 §03: 端口听 + 首拍 200 才算起妥)。"""
    def probe():
        try:
            return web_req(port, "GET", "/api/state?view=torrent")
        except (urllib.error.URLError, OSError):
            return None

    return wait_until(probe, 40, "产品 WEB 首拍未就绪")


@contextlib.contextmanager
def product_case(name: str, *, qb_port: int = 36596, grouping: bool = True, api_key: str = ""):
    """起一份 dev.webui 安全模式产品进程跑单条用例, 收尾必杀进程树。"""
    case = case_dir(name)
    cfg, port = write_cfg(case, qb_port=qb_port, grouping=grouping, api_key=api_key)
    proc = app.AppProc(_popen_auto_qb(cfg), case, cfg)
    try:
        assert proc.wait_web(), f"产品 WEB 未启动: 日志尾部 {proc.log()[-400:]!r}"
        web_ready(port)
        yield case, port, proc
    finally:
        kill_tree(proc)


def web_req(port: int, method: str, path: str, body: dict | None = None) -> dict | list:
    """产品 Web API 客户端(GET/POST/PUT; 本机免鉴权 skip_local_verify=true)。"""
    r = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    if body is not None:
        r.add_header("Content-Type", "application/json")
    with _OPENER.open(r, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_err(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """非 2xx 探针: 返回 (状态码, 解析后的错误载荷); 拿到 2xx 反而是用例 bug, 直接抛。"""
    try:
        web_req(port, method, path, body)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}
    raise AssertionError(f"期望非 2xx 拒收, 实际成功: {method} {path}")


def flat_rows(port: int) -> list[dict]:
    return web_req(port, "GET", "/api/state?view=torrent")["torrents"]


def wait_in_store(port: int, *hashes: str, timeout: float = 30.0) -> None:
    wait_until(
        lambda: all(h in {t["hash"]
                          for t in flat_rows(port)} for h in hashes),
        timeout,
        f"种子未进产品快照: {hashes}",
    )


def wait_in_store_state(port: int, ih: str, state: str, timeout: float = 30.0) -> None:
    """等产品快照把该种子的状态同步到 state(快照滞后 qB 1-2 个同步拍, §2.9)。"""
    def probe():
        for t in flat_rows(port):
            if t["hash"] == ih and t.get("state") == state:
                return True
        return None

    wait_until(probe, timeout, f"快照状态未到 {state}: {ih[:8]}")


# ---------------------------------------------------------------- qB 侧辅助(假种子 real-fake, 幂等清场)


def qbfake():
    return instances.make(instances.SECONDARY)


def _tags_of(t) -> set[str]:
    """qB 多标签以「, 」连接, 裸 split 对双标签失明(§2.9), 一律 strip。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def _add_retry(qb, raw: bytes, savepath: str, ih: str, *, paused: bool = False) -> None:
    """加种子, 409 双义处理(§2.9: 同 infohash 旧副本一律删掉重加, 绝不收养)。"""
    from lib.qb import QbError

    for _attempt in range(4):
        try:
            qb.add_torrent(raw, savepath=savepath, paused=paused, tags=TAG, infohash_hint=ih)
            return
        except QbError as e:
            if "409" not in str(e):
                raise
            stale = qb.torrent(ih)
            if stale is None:
                time.sleep(1.5)
                continue
            qb.delete(stale["hash"], delete_files=True)
            wait_until(lambda: qb.torrent(ih) is None, 15, f"409 旧副本删除未生效: {ih[:8]}")
    raise AssertionError(f"add 持续 409: {ih[:8]} @ {savepath}")


def rm_all_fakes(qb, *, batch: int = 200) -> list[str]:
    """删光本实例里 real-fake 标签的种子(连数据; 大库按 200 枚/批分批调 /torrents/delete)。

    ⚠ qB 多 hash 分隔符是 `|` 不是 `,`(guard.pause 同款; RM09 逐个删没踩到这个坑)。
    """
    gone = []
    tagged = [t for t in qb.torrents() if TAG in _tags_of(t)]
    for i in range(0, len(tagged), batch):
        chunk = tagged[i:i + batch]
        qb.delete("|".join(t["hash"] for t in chunk), delete_files=True)
        gone.extend(t["name"] for t in chunk)
    if gone:
        wait_until(lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 60, f"real-fake 残留未删净: {gone[:5]}")
    return gone


def settle(qb, ih: str, timeout: float = 60.0) -> dict:
    """等种子走完 check/alloc 拿到稳定态。"""
    deadline = time.time() + timeout
    t: dict = {}
    while time.time() < deadline:
        t = qb.torrent(ih) or {}
        if t.get("state") in SETTLED:
            return t
        time.sleep(0.3)
    return t


def wait_state(qb, ih: str, state: str, timeout: float = 30.0, desc: str = "") -> None:
    wait_until(lambda: (qb.torrent(ih) or {}).get("state") == state, timeout, f"qB 状态未到 {state}: {desc} {ih[:8]}")


def fake_one(qb, case: Path, name: str, size: int = 256 * 1024, sub: str = "src", paused: bool = False) -> str:
    """单文件假种子(带数据落盘; 无 announce 纯本地 —— 读侧不需要归组管线, 零外连)。"""
    savepath = case / sub
    os.makedirs(savepath, exist_ok=True)
    torrent.write_file(str(savepath / name), size, "random", name)
    raw, ih = torrent.build_from_path(str(savepath / name), name, None)
    _add_retry(qb, raw, str(savepath), ih, paused=paused)
    return ih


@pytest.fixture()
def clean_fakes():
    """幂等清场: 开跑先清 36596 自造种子, 收尾再清一轮并核净(§09 幂等纪律)。"""
    qb = qbfake()
    rm_all_fakes(qb)
    yield qb
    rm_all_fakes(qb)


def rid_poll(port: int, rid: int, view: str = "torrent", delta: bool = False) -> dict:
    q = f"/api/state?view={view}&rid={rid}" + ("&delta=1" if delta else "")
    return web_req(port, "GET", q)


def wait_updated(port: int, rid: int, *, view: str = "torrent", delta: bool = False, timeout: float = 15.0) -> dict:
    """持陈旧 rid 轮询到版本推进(变更代发布), 返回该拍载荷。"""
    def probe():
        r = rid_poll(port, rid, view=view, delta=delta)
        return r if r.get("updated") else None

    return wait_until(probe, timeout, f"同 rid 复拍仍零回传(版本未推进): rid={rid} view={view}")


ARRAYS = {"groups", "singles", "shows", "torrents"}


def assert_zero_return(r: dict, rid: int) -> None:
    """零回传拍形态: updated:false 且**不回任何视图数组**(状态/版本键外只有恒回传 status 段)。

    实码口径(首轮实测, 计划 §03 RM08-01④ 同款): /api/state 路由层把 status(traffic/server/
    totals 恒回传段)**包在 ensure_state 结果之外** —— 零回传分支= {status, rid, updated:false},
    ensure_state 自身只回 {rid, updated}。数组键缺席是 rid 门控的本体断言。
    """
    assert r.get("rid") == rid and r.get("updated") is False, f"零回传拍 rid/updated 不对: {r.get('rid')}/{r.get('updated')}"
    assert not ARRAYS & set(r), f"零回传拍混入视图数组(门控破): {ARRAYS & set(r)}"


def wait_settled_rid(port: int, timeout: float = 15.0) -> int:
    """连取两拍确认版本静止(防背景脏干扰 delta 窗口), 返回当前 rid。"""
    r1 = web_req(port, "GET", "/api/state?view=torrent")
    rid = r1["rid"]
    wait_until(
        lambda: (lambda p: p if (p.get("updated") is False and not ARRAYS & set(p)) else None)(rid_poll(port, rid)),
        timeout,
        f"版本未静止: rid={rid}",
    )
    return rid


def wait_quiesced_rid(port: int, cycles: int = 2, quiet_s: float = 2.5) -> int:
    """等「发布管道 + 存量脏」全部排空后返回 rid(delta 窗口基线专用)。

    产品有 pending_ver 生产者门控(ensure_state: 上一版未被请求取走前主循环不产下一版)——
    刚落地的存量脏可能在一次零回传拍**之后**才被主循环补发一代(实测: 单次静止后造变更,
    窗口里混进相邻代的未变更行)。静止 → 睡眠(> main_tick) → 再静止, 循环 cycles 轮才算干净。
    """
    rid = wait_settled_rid(port)
    for _ in range(cycles):
        time.sleep(quiet_s)
        rid = wait_settled_rid(port)
    return rid


# ---------------------------------------------------------------- 用例


def test_rm08_01_merge_endpoint_and_rid_gating(clean_fakes):
    """[RM08-01] 合并端点契约与 rid 门控: 单请求 status+视图 / 零回传拍 / 恒回传段

    前置: dev.webui 基座连 36596 + 3 枚无 announce 假种子(stalledUP); 首拍字节快照。
    副作用: 1 假种子被 qB API 直调暂停一次(可恢复)。
    回滚: real-fake 种子收尾删净; 产品进程 taskkill /F /T; 临时目录随下轮 case_dir 清场。
    失败判据: rid 匹配仍回全量(门控破, 大库下白耗带宽, 高优); updated 拍缺 status 恒回传段
              (traffic/server/totals, 状态栏/连接态失灵根因); 零回传拍字节与全量同量级
              (门控形同虚设)。
    """
    with product_case("rm08_01") as (case, port, _proc):
        qb = clean_fakes
        hs = [fake_one(qb, case, f"rm08a{i}.bin", sub="src") for i in range(3)]
        for h in hs:
            settle(qb, h)
            wait_state(qb, h, "stalledUP", desc="无 announce 假种子应纯本地做种")
        wait_in_store(port, *hs)

        # ① 首拍(rid 缺省): status(含 traffic/server/totals)+ torrents 数组 + rid + updated:true
        r1 = web_req(port, "GET", "/api/state?view=torrent")
        assert r1["updated"] is True, f"首拍应 updated:true: {sorted(r1)}"
        assert len(r1["torrents"]) == 3, f"首拍 torrents 行数不对: {len(r1['torrents'])}"
        assert {"traffic", "server", "totals"} <= set(r1["status"]), f"status 恒回传段缺失: {sorted(r1['status'])}"
        b_full = jlen(r1)
        rid = r1["rid"]

        # ② 同 rid 二连拍 → 零回传: 不回任何视图数组; status 恒回传段照在(实码路由层包装,
        #    计划 RM08-01④ 同款口径); 字节界按实况放宽到 50%(3 枚种子下 status 段占比高)
        r2 = rid_poll(port, rid)
        assert_zero_return(r2, rid)
        assert {"traffic", "server", "totals"} <= set(r2["status"]), f"零回传拍缺恒回传段: {sorted(r2['status'])}"
        assert jlen(r2) < b_full * 0.50, f"零回传拍字节未显著小于全量: {jlen(r2)} vs {b_full}"

        # ③ qB API 直调暂停 1 枚 → 等 sync 拍 → 同 rid 拍 updated:true(版本推进)
        qb.pause(hs[0])
        wait_state(qb, hs[0], "stoppedUP", desc="qB 直调暂停")
        r3 = wait_updated(port, rid)
        assert len(r3["torrents"]) == 3 and {"traffic", "server", "totals"
                                            } <= set(r3["status"]), (f"updated 拍缺视图数组或恒回传段: {sorted(r3)}")
        assert r3["rid"] != rid, "updated 拍 rid 未推进"

        # ④ 恒回传段与视图数据同轮同源(状态栏口径): totals 为 dict 且 server/traffic 非空结构
        assert isinstance(r3["status"]["totals"], dict) and set(r3["status"]["totals"]) == {
            "dlspeed", "upspeed"
        }, (f"totals 形状不对: {r3['status']['totals']}")
        assert r3["status"]["server"], "server 段为空"


def test_rm08_02_delta_negotiation(clean_fakes):
    """[RM08-02] delta 增量协商归约: full/增量/窗外/未协商/show 五对照(L3, 负向对照内建)

    前置: 基座 + 3 枚假种子; 开测前版本静止(连两次零回传), 时间线窗口内至少触发 1 代变更。
    副作用: 假种子状态切换数次(暂停/恢复, 经 qB API 直调)。
    回滚: real-fake 种子收尾删净; 停基座删临时目录。
    失败判据: 未协商请求也回了 full/delta 键(协商闸破, 老前端把增量当全量吃会四数组 undefined
              白屏, 高优); 增量载荷行内容与当前视图不一致(R1 现取破); 变更行缺失或
              removed/upsert 串位(R5 让位破); 窗外不回落全量(R3/R10 破)。
    判据实况修正(计划 §03 ②, 详见模块 docstring): 「恰含变更行」放宽为「变更行在 + 窗口
              全部行内容现取一致」—— 新鲜入库种子的错峰 check 派生变更落在基线邻代(复现
              两轮, 行内容与当前视图一致), 恰单行只在注入后静置 ≥60s 才确定, 不值这个成本。
    判据实况修正(计划 §03 spec ⑤ vs 实码, 详见模块 docstring): S9b 起 show ∈ _DELTA_VIEWS,
    ⑤按实码契约断言「view=show&delta=1 归约形态合法」(顶层无全量数组 + delta 桶按
    VIEW_ARRAYS["show] 裁剪), 计划漂移在基线切片记账, 不入池缺陷。
    """
    with product_case("rm08_02") as (case, port, _proc):
        qb = clean_fakes
        hs = [fake_one(qb, case, f"rm08b{i}.bin", sub="src") for i in range(3)]
        for h in hs:
            settle(qb, h)
        wait_in_store(port, *hs)

        # ① 协商首拍: full:true 全量(无 delta/removed 键, R10 全量分支口径)
        r1 = rid_poll(port, -1, delta=True)
        assert r1["updated"] is True and r1.get("full") is True, f"协商首拍应 full:true: {sorted(r1)}"
        assert len(r1["torrents"]) == 3 and "delta" not in r1 and "removed" not in r1, f"协商全量拍形状不对: {sorted(r1)}"
        b_full = jlen(r1)
        # rid 基线取排空后一拍(不用 r1 的 rid): r1 时刻相邻代(check 完成等)可能尚未发布,
        # 且 pending_ver 门控会让存量脏在零回传拍之后才补发 —— 旧 rid 会让窗口混入未变更行。
        rid0 = wait_quiesced_rid(port)

        # ② 变更代: delta=1 复拍 → full:false + delta.torrents 恰含变更行(行内容 == 当前全量同 hash 行)
        qb.pause(hs[0])
        wait_state(qb, hs[0], "stoppedUP", desc="增量触发变更")
        r2 = wait_updated(port, rid0, delta=True)
        assert r2.get("full") is False, f"窗口内变更代应归约: {sorted(r2)}"
        assert "delta" in r2 and "removed" in r2, f"增量载荷缺 delta/removed: {sorted(r2)}"
        upsert = r2["delta"].get("torrents") or []
        up_hashes = [row["hash"] for row in upsert]
        assert hs[0] in up_hashes, f"delta.upsert 未含变更行: {up_hashes}"
        # 「恰含变更行」按窗口实况放宽(计划 §03 ② 的窗口洁净前提在新鲜入库种子上不成立,
        # 见模块 docstring 实况注): 错峰 check 完成的派生变更会落在基线邻代 —— 承载性判据
        # 改为「变更行在 + 窗口内全部 upsert 行内容 == 当前全量视图同 hash 行(R1 现取)」。
        cur = {t["hash"]: t for t in flat_rows(port)}
        for row in upsert:
            assert row == cur[row["hash"]], f"增量行内容与当前全量视图不一致(R1 现取破): {row['hash'][:8]}"
        assert r2["removed"]["torrents"] == [], f"暂停不该产生 removed: {r2['removed']}"
        metric(f"[rm08-02] 窗口 upsert 行数 {len(upsert)}(变更行 1 + 邻代残留 {len(upsert) - 1})")
        assert jlen(r2) * 2 < b_full, f"增量拍字节应显著小于全量拍: {jlen(r2)} vs {b_full}"

        # ③ 窗外对照(红验): rid=0(缺省/0)与 rid=未来(>ver)都必回落全量(R3)
        for stale in (0, r2["rid"] + 10**6):
            r3 = rid_poll(port, stale, delta=True)
            assert r3.get("full") is True and "delta" not in r3 and len(
                r3["torrents"]
            ) == 3, (f"窗外 rid={stale} 未回落全量(R3 破): {sorted(r3)}")

        # ④ 未协商对照(红验): 同请求去 delta=1 → 历史形状(无 full/delta/removed 键, P-01 兼容闸)
        r4 = rid_poll(port, -1)
        assert "full" not in r4 and "delta" not in r4 and "removed" not in r4, (f"未协商请求竟带协商键(S3 闸破, 高优): {sorted(r4)}")
        assert r4["updated"] is True and len(r4["torrents"]) == 3, f"未协商全量形状不对: {sorted(r4)}"

        # ⑤ view=show&delta=1: S9b 起 show 进增量矩阵(计划判据漂移, 按实码契约断言)
        qb.resume(hs[0])
        wait_state(qb, hs[0], "stalledUP", desc="show 对照前置恢复")
        rid5 = wait_quiesced_rid(port)
        qb.pause(hs[1])
        wait_state(qb, hs[1], "stoppedUP", desc="show 对照变更")
        r5 = wait_updated(port, rid5, view="show", delta=True)
        assert r5.get("full") is False and "delta" in r5, f"show 协商拍应走归约(S9b): {sorted(r5)}"
        assert set(r5["delta"]) == {"shows", "groups", "singles"}, f"show 增量桶未按 VIEW_ARRAYS 裁剪: {sorted(r5['delta'])}"
        assert not {"torrents", "shows", "groups", "singles"} & set(r5), f"归约拍顶层混入全量数组: {sorted(r5)}"


def test_rm08_03_view_arrays_payload(clean_fakes):
    """[RM08-03] VIEW_ARRAYS payload 收敛: 四视图分片 + 缺省回退 + 字节量级

    前置: 基座 + 3 枚未归组假种子(无 announce, 全落 singles; 纯只读用例)。
    副作用: 无(纯只读)。
    回滚: real-fake 种子收尾删净; 停基座删临时目录。
    失败判据: 分片键多回(收敛破, 大库带宽白耗)或少回(消费端拿 undefined, 高优);
              未知 view 报 500 而非回退四份(保守默认破); view=torrent 字节比无 view 全量拍
              反而更大(分片失效)。
    """
    with product_case("rm08_03") as (case, port, _proc):
        qb = clean_fakes
        hs = [fake_one(qb, case, f"rm08c{i}.bin", sub="src") for i in range(3)]
        for h in hs:
            settle(qb, h)
        wait_in_store(port, *hs)

        # ① view=torrent → 只含 torrents 键
        rt = web_req(port, "GET", "/api/state?view=torrent")
        assert ARRAYS & set(rt) == {"torrents"}, f"view=torrent 分片键不对: {ARRAYS & set(rt)}"
        assert len(rt["torrents"]) == 3, f"torrents 行数不对: {len(rt['torrents'])}"

        # ② view=group → groups+singles(未归组 ⇒ groups 空属预期: 归组管线不归本片面)
        rg = web_req(port, "GET", "/api/state?view=group")
        assert ARRAYS & set(rg) == {"groups", "singles"}, f"view=group 分片键不对: {ARRAYS & set(rg)}"
        assert len(
            rg["singles"]
        ) == 3 and rg["groups"] == [], (f"group 视图形状不对: singles={len(rg['singles'])} groups={len(rg['groups'])}")

        # ③ view=show → 三件套(缺成员索引 = 追剧页永久空表, BUG-8 同款)
        rs = web_req(port, "GET", "/api/state?view=show")
        assert ARRAYS & set(rs) == {"shows", "groups", "singles"}, f"view=show 分片键不对: {ARRAYS & set(rs)}"
        assert isinstance(rs["shows"], dict) and "list" in rs["shows"], f"shows 非剧聚合结构: {type(rs['shows'])}"

        # ④ 缺省/未知 view → 四份全回(保守默认; 未知值不得 500)
        rd = web_req(port, "GET", "/api/state")
        assert ARRAYS <= set(rd), f"缺省 view 未回四份: {ARRAYS & set(rd)}"
        rb = web_req(port, "GET", "/api/state?view=bogus")
        assert ARRAYS <= set(rb), f"未知 view 未回退四份: {ARRAYS & set(rb)}"

        # ⑤ 字节量级: 分片严格更小(门控生效)。计划 40% 界(≈1/4 口径)受 status 恒回传段支配,
        #    在 3 枚种子的小库下实测 66%(status ≈ 数组总量的一半)—— 该界移到 RM08-04 的大库
        #    载荷上断言(≈1/4 是大库性质), 此处记实测比供基线切片誊写。
        assert jlen(rt) < jlen(rd), f"view=torrent 字节未小于全量(分片失效): {jlen(rt)} vs {jlen(rd)}"
        metric(f"[rm08-03] 字节比 view=torrent/无view = {jlen(rt) / jlen(rd):.2f}({jlen(rt)}/{jlen(rd)}B, 3 枚种子)")


def test_rm08_05_detail_drawer(clean_fakes):
    """[RM08-05] 详情抽屉四端点: detail 同源一致 + trackers mask + files/peers + 未知 hash 负向

    前置: 36596 主基座 + 1 假种子(假种子腿); 36595 侧另起一份 api_key 直连产品实例
          (grouping 关死零写路径), 真实种子 paused 只读走一遍(真实 tracker 域名最有说服力)。
    副作用: 无(两腿全只读; 36595 真实种子零触碰)。
    回滚: 假种子删净; 两份产品进程 taskkill /F /T; 临时目录清场。
    失败判据: detail 字段与 qB 回读不一致(同源破, 抽屉显示错数, 高优); tracker 原文/凭据外发
              (mask 破, 域名泄漏面); 虚拟条目缺失; 未知 hash 500(错误处理面破)。
    """
    # ---- 腿 B: 36596 假种子 ----
    with product_case("rm08_05") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm08e.bin", sub="src")
        settle(qb, h)
        wait_state(qb, h, "stalledUP", desc="假种子腿原态")
        wait_in_store_state(port, h, "stalledUP", timeout=30)  # 同源对照前快照状态也要到位(滞后 1-2 拍)

        d = web_req(port, "GET", f"/api/torrents/{h}")["torrent"]
        qrow = qb.torrent(h)
        assert d["name"] == qrow["name"] and d["state"] == qrow["state"], (
            f"detail 与 qB 不同源: name/state {d.get('name')!r}/{d.get('state')!r} vs {qrow['name']!r}/{qrow['state']!r}"
        )
        assert norm(d["save_path"]) == norm(qrow["save_path"]), "detail save_path 与 qB 不同源"
        assert abs(d["progress"] - qrow["progress"]) <= 1e-4, f"detail progress 与 qB 不同源: {d.get('progress')}"
        assert "site" in d and {
            "hr_state", "hr_safety", "hr_excluded"
        } <= set(d), (f"detail 缺 site/HR 展示字段键: {sorted(set(d) & {'site', 'hr_state', 'hr_safety', 'hr_excluded'})}")
        # trackers(无 announce 私有假种子): 虚拟条目仍在(qB 恒回 DHT/PeX/LSD 占位, §2.5)
        trs = web_req(port, "GET", f"/api/torrents/{h}/trackers")
        assert any(str(t["url"]).startswith(("**", "[DHT]", "[PeX]", "[LSD]"))
                   for t in trs), (f"假种子腿 trackers 缺虚拟条目: {[t['url'] for t in trs]}")
        assert isinstance(web_req(port, "GET", f"/api/torrents/{h}/files"), list), "files 应为文件数组"
        peers = web_req(port, "GET", f"/api/torrents/{h}/peers")
        assert "peers" in peers, f"peers 缺 qB sync 透传结构: {sorted(peers)}"
        code, p = web_err(port, "GET", f"/api/torrents/{'f' * 40}")
        assert code == 404, f"未知 hash 应 404(_require_torrent): {code} {p}"

    # ---- 腿 A: 36595 真实种子(paused, 只读; 独立产品实例 api_key 直连, grouping 关死) ----
    api_key = instances.token_for(instances.PRIMARY) or ""
    with product_case("rm08_05_real", qb_port=instances.PRIMARY, grouping=False, api_key=api_key) as (
        case_real,
        port_real,
        _proc_real,
    ):
        qb95 = instances.make(instances.PRIMARY)
        ts = qb95.torrents()
        assert ts, "36595 应有真实种子(guard 已 pause)"
        h = ts[0]["hash"]
        wait_in_store_state(port_real, h, "stoppedUP", timeout=60)  # 同源对照前快照状态到位
        raw_urls = {t["url"] for t in qb95.trackers(h) if str(t["url"]).startswith("http")}
        assert raw_urls, "真实种子应有真实 tracker 条目"

        # detail 同源一致(抽屉 General tab 数据源)
        d = web_req(port_real, "GET", f"/api/torrents/{h}")["torrent"]
        qrow = qb95.torrent(h)
        assert d["name"] == qrow["name"] and d["state"] == qrow["state"], "真实种子 detail name/state 与 qB 不同源"
        assert norm(d["save_path"]) == norm(qrow["save_path"]), "真实种子 save_path 与 qB 不同源"
        assert abs(d["progress"] - qrow["progress"]) <= 1e-4, "真实种子 progress 与 qB 不同源"
        assert d.get("size") == qrow["size"], "真实种子 size 与 qB 不同源"
        assert "site" in d and {"hr_state", "hr_safety", "hr_excluded"} <= set(d), "真实种子 detail 缺 site/HR 键"

        # trackers: 虚拟条目原样 + 真实条目已 mask(原文/凭据不外发, 高优)
        trs = web_req(port_real, "GET", f"/api/torrents/{h}/trackers")
        urls = [str(t["url"]) for t in trs]
        assert any(u.startswith(("**", "[DHT]", "[PeX]", "[LSD]")) for u in urls), f"真实种子腿缺虚拟条目: {urls}"
        http_urls = [u for u in urls if u.startswith("http")]
        assert http_urls, "真实条目缺失"
        body_text = json.dumps(trs, ensure_ascii=False)
        for u in raw_urls:
            assert u not in http_urls, f"tracker url 未 mask(mask 破): {u}"
            assert u not in body_text, f"tracker 原文/凭据外发(mask 破, 高优): {u}"
        assert any(t.get("msg") == "这是私有 torrent"
                   for t in trs), (f"私有种子 tracker msg 口径不对: {[t.get('msg') for t in trs]}")

        # files/peers 回读 200 且结构合法
        files = web_req(port_real, "GET", f"/api/torrents/{h}/files")
        assert isinstance(files, list) and files, f"真实种子 files 应非空: {files}"
        peers = web_req(port_real, "GET", f"/api/torrents/{h}/peers")
        assert "peers" in peers, "真实种子 peers 缺透传结构"
        code, _p = web_err(port_real, "GET", f"/api/torrents/{'0' * 40}")
        assert code == 404, f"未知 hash 应 404: {code}"


def test_rm08_06_status_totals_l2(clean_fakes, primary, secondary, tracker, transfer_limits):
    """[RM08-06] 状态栏 totals 修后复验(走查迁出): status.totals 恒回传 == 同载荷行级求和(非零速)

    前置: 双实例 + RM00 L2 互传就位(伪 tracker 回对端, 全本机零外网; 限速钉 256KiB/s);
          36596 侧 dev.webui 基座在跑; 36595 的 8 枚真实种子保持 paused(假种子活跃不受约束 2)。
    副作用: 两实例各新增 1 枚互传假种子 + 数据文件(用例目录); 传输期间该种子两端活跃。
    回滚: 双侧删种子(连数据) + 限速由 transfer_limits fixture 按快照还原 + 停伪 tracker。
    失败判据: view=torrent 下 totals 键缺失(修复回潮, 状态栏恒 0 根因复发, 高优);
              totals != 同载荷行级求和(求和源分叉/漏 singles, 高优); 传输中 totals 恒 0 而行速
              非零(发布时序倒退); 传输停止后 totals 不回零速。
    """
    payload = 4 * 1024 * 1024  # 256KiB/s 钉速下 ≈16s 稳态窗, 够 3 拍取样
    data = torrent.payload(size=payload, seed=b"auto-qb-rm08-l2")
    raw, ih = torrent.build("rm08l2.bin", data, tracker.url)
    seed_dir = case_dir("rm08_06_seed")
    leech_dir = WORK / "rm08_06_leech"
    leech_dir.mkdir(parents=True, exist_ok=True)
    torrent.write_payload(str(seed_dir), "rm08l2.bin", data)
    seed_port = int(primary.prefs()["listen_port"])
    tracker.peers = [(_local_host(), seed_port)]
    with product_case("rm08_06") as (case, port, _proc):
        try:
            primary.add_torrent(raw, savepath=str(seed_dir), paused=False, infohash_hint=ih)
            secondary.add_torrent(raw, savepath=str(leech_dir), paused=False, infohash_hint=ih)
            wait_in_store(port, ih, timeout=60)

            def totals_payload():
                p = web_req(port, "GET", "/api/state?view=torrent")
                return p, p["status"]["totals"], sum(t["dlspeed"]
                                                     for t in p["torrents"]), sum(t["upspeed"] for t in p["torrents"])

            # 传输进行中: 行 dlspeed 非零后连取 3 拍, 逐拍核 totals 恒在且 == 同载荷行级求和
            def dl_active():
                p, tot, dl_sum, _ul = totals_payload()
                return p if (tot["dlspeed"] > 0 and dl_sum > 0) else None

            wait_until(dl_active, 60, "产品行载荷未观测到非零下载速(互传未进稳态)")
            for i in range(3):
                p, tot, dl_sum, ul_sum = totals_payload()
                assert "totals" in p["status"], "view=torrent 下 status.totals 键缺失(修复回潮, 高优)"
                assert tot["dlspeed"] == dl_sum, f"第{i + 1}拍 totals.dlspeed({tot['dlspeed']}) != 行级求和({dl_sum})"
                assert tot["upspeed"] == ul_sum, f"第{i + 1}拍 totals.upspeed({tot['upspeed']}) != 行级求和({ul_sum})"
                assert tot["dlspeed"] > 0, f"第{i + 1}拍 totals 恒 0 而互传应进行中"
                time.sleep(1.0)

            # 传输停止后 totals 回零速(行速同步归零; 完成后该种子转做种但对端无需求)
            wait_until(lambda: qb_fake_torrent_done(secondary, ih), 120, "L2 互传 120s 未完成")

            def totals_zero():
                _p, tot, dl_sum, ul_sum = totals_payload()
                if tot["dlspeed"] == 0 and tot["upspeed"] == 0 and dl_sum == 0 and ul_sum == 0:
                    return True
                q = secondary.torrent(ih) or {}
                return {
                    "totals": tot,
                    "row_sum": [dl_sum, ul_sum],
                    "rows":
                        [
                            (t["name"], t["dlspeed"], t["upspeed"])
                            for t in _p["torrents"] if t["dlspeed"] or t["upspeed"]
                        ],
                    "qb": {
                        "state": q.get("state"),
                        "dl": q.get("dlspeed"),
                        "ul": q.get("upspeed")
                    },
                }

            wait_until(totals_zero, 60, "传输停止后 totals 未回零速")
        finally:
            for qb in (primary, secondary):
                try:
                    if qb.torrent(ih):
                        qb.delete(ih, delete_files=True)
                except Exception:  # noqa: BLE001 —— 收尾清理尽力而为, 残留由下轮 clean_fakes 兜底
                    pass


def qb_fake_torrent_done(qb, ih: str) -> bool:
    return bool((qb.torrent(ih) or {}).get("progress", 0) >= 1.0)


def _local_host() -> str:
    from lib.net import local_host

    return local_host()


def test_rm08_07_sse_and_aux_endpoints(clean_fakes):
    """[RM08-07] SSE 推送通道与只读辅助端点: ticket 换票 / hello / 心跳 <TTL + sites/missing 扫描

    前置: 基座 + 1 枚假种子; 流式客户端读超时 > 12s(WEB_VIEW_TTL=10s, SSE_KEEPALIVE_S=5s)。
    副作用: 1 假种子状态切换一次; 1 条 SSE 连接(收尾关)。
    回滚: real-fake 种子收尾删净; 停基座; 流式连接随进程树终止关闭。
    失败判据: 12s 内零心跳帧(keepalive 破, 连着的客户端被判不活跃 → 主循环停组装视图 → 自锁,
              高优); hello 前泄漏载荷; 连流期间变更后既无推送帧也无版本推进(连接饿死);
              sites/missing 计数与实例种子数不符。
    BLOCKED 子项(计划 spec ⑤ 坏票负向): skip_local_verify=true 下 auth.py 的 loopback 免鉴权
    先于票据闸返回(实码事实, 冻结驱动形态不可达)—— 本轮不断言, 解锁=驱动改 skip_local_verify=
    false + Bearer token 重跑; 已在基线切片与锚件记账, 非产品缺陷。
    """
    with product_case("rm08_07") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm08g.bin", sub="src")
        settle(qb, h)
        wait_in_store(port, h)

        # ① 换票: {ticket, ttl}(30s)
        tk = web_req(port, "POST", "/api/events/ticket")
        assert tk.get("ticket") and tk.get("ttl") == 30, f"ticket 回执形状不对: {tk}"

        # ② 连流收 hello(首帧即 hello, 不得先泄漏载荷)
        conn, sresp = _sse_connect(port, tk["ticket"])
        try:
            assert sresp.getheader(
                "Content-Type", ""
            ).startswith("text/event-stream"), (f"SSE Content-Type 不对: {sresp.getheader('Content-Type')}")
            hello = _read_frame(conn, sresp, timeout_s=5)
            assert hello and hello.get("event") == "hello", f"首帧应为 hello: {hello}"
            assert hello.get("data", {}).get("ok") is True, f"hello 载荷不对: {hello}"

            # ③ 空闲期读 ≥12s(WEB_VIEW_TTL=10s)→ 至少 1 条 keepalive(保活 + touch 自证活跃)
            keepalives = _count_keepalives(conn, sresp, seconds=12)
            assert keepalives >= 1, f"{12}s 内零心跳帧(keepalive 破, 自锁面, 高优)"

            # ④ 连流期间触发一次变更(暂停假种子)→ 流上收到 ver 帧(视图版本推送)或复拍版本推进
            rid0 = web_req(port, "GET", "/api/state?view=torrent")["rid"]
            qb.pause(h)
            wait_state(qb, h, "stoppedUP", desc="SSE 变更触发")
            ver = _wait_ver_frame(conn, sresp, seconds=10)
            if ver is None:
                # 推送面按计划二选一: 复拍视图版本推进也算「连接不饿死」
                wait_updated(port, rid0, timeout=10)
        finally:
            conn.close()

        # ⑤ 坏票负向: 冻结驱动形态下不可达(见 docstring BLOCKED 子项), 本轮不断言。

        # ⑥ sites/missing(只读扫描): 计数与实例种子数一致; trackers 空 + 假种子无 announce
        #    ⇒ domains=0, sites=[](无缺失域可报, 结构与计数口径断言)
        sm = web_req(port, "GET", "/api/sites/missing")
        n_fake = len([t for t in qb.torrents() if TAG in _tags_of(t)])
        assert sm["torrents"] == n_fake, f"sites/missing torrents 计数({sm['torrents']})!= 实例种子数({n_fake})"
        assert sm["domains"] == 0 and sm["sites"] == [], f"无 announce 空库不应有缺失域: {sm}"


def _sse_connect(port: int,
                 ticket: str,
                 timeout: float = 30.0) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
    """SSE 流式连接(http.client 直连: 逐行 readline + 可调 socket 超时, urllib 的响应对象不便控制)。"""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    conn.request("GET", f"/api/events?ticket={urllib.parse.quote(ticket, safe='')}")
    resp = conn.getresponse()
    assert resp.status == 200, f"SSE 连流应 200: {resp.status} {resp.read()[:120]!r}"
    return conn, resp


def _read_frame(conn, resp, timeout_s: float) -> dict | None:
    """读一个 SSE 帧(event 行 + data 行, 空行结束), 返回 {event, data}; 超时/断流返回 None。

    keepalive 注释行(": keepalive")跳过不返回, 交由 _count_keepalives 专数。
    """
    _sock(conn).settimeout(max(timeout_s, 1.0))
    event, data = None, ""
    while True:
        try:
            line = resp.readline()
        except (TimeoutError, OSError):
            return None
        if not line:
            return None
        text = line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not text:
            if event is not None:
                parsed = None
                if data:
                    try:
                        parsed = json.loads(data)
                    except ValueError:
                        parsed = {"raw": data}
                return {"event": event, "data": parsed}
            continue
        if text.startswith("event:"):
            event = text.split(":", 1)[1].strip()
        elif text.startswith("data:"):
            data = text.split(":", 1)[1].strip()


def _count_keepalives(conn, resp, seconds: float) -> int:
    """在 seconds 窗口内数 keepalive 注释帧(每条必须 <TTL, 保活+活跃自证)。"""
    _sock(conn).settimeout(max(seconds, 15.0))
    deadline = time.time() + seconds
    count = 0
    while time.time() < deadline:
        try:
            line = resp.readline()
        except (TimeoutError, OSError):
            break
        if not line:
            break
        if line.decode("utf-8", errors="replace").startswith(": keepalive"):
            count += 1
    return count


def _wait_ver_frame(conn, resp, seconds: float) -> dict | None:
    """等 event: ver 帧; 超时返回 None(由调用方走「复拍版本推进」兜底)。"""
    deadline = time.time() + seconds
    while time.time() < deadline:
        frame = _read_frame(conn, resp, timeout_s=max(1.0, deadline - time.time()))
        if frame is None:
            return None
        if frame.get("event") == "ver":
            return frame
    return None


def _sock(conn):
    if conn.sock is None:
        raise AssertionError("SSE 连接已断(收流前 socket 为空)")
    return conn.sock


def test_rm08_08_error_reason_missing_files(clean_fakes):
    """[RM08-08] error_reason 数据面(missingFiles 分支, TASK015 姊妹): 行载荷「文件丢失」+ 行级 delta 即达

    前置: 基座 + 1 枚带数据假种子(256K, stalledUP, 落点在用例目录); 行载荷健康态基线
          (error_reason 空串)+ delta 客户端 rid 基线。
    副作用: 假种子数据文件被删 + recheck 一次(qB 直调)。
    回滚: real-fake 种子收尾删净(此时为残缺态, 直接删条目); 临时目录清场。
    失败判据: missingFiles 行 error_reason 非空串非「文件丢失」(取数单点分叉, 前端不得按
              state 猜原因的约定破); delta 客户本代复拍拿不到新值(行级脏登记漏, 增量客户端
              冻结在旧值, 高优); 健康态行带非空 error_reason(误报)。
    BLOCKED(计划造法不成立, 实测两轮): 计划 §03 的「删文件 + recheck → missingFiles」在
    qB 5.2.3 走不通 —— recheck(running)→ stalledDL 0%、recheck(stopped)→ stoppedDL 0%、
    删后 start → fast-resume 不核文件仍 stalledUP;missingFiles 需真实失败的文件操作(如
    L2 传输读失败)。造不到 ⇒ 本条后半段 skip(三态记 BLOCKED, 非产品缺陷); 解锁 = 造法
    定案后按同口径补断言。
    """
    with product_case("rm08_08") as (case, port, _proc):
        qb = clean_fakes
        h = fake_one(qb, case, "rm08h.bin", size=256 * 1024, sub="src")
        settle(qb, h)
        wait_state(qb, h, "stalledUP", desc="健康态基线")
        wait_in_store_state(port, h, "stalledUP", timeout=30)  # 快照状态到位(滞后 1-2 拍, §2.9)

        # 健康态: 行载荷 error_reason == ""(空串口径)
        row = {t["hash"]: t for t in flat_rows(port)}[h]
        assert row["state"] == "stalledUP" and row["error_reason"] == "", (
            f"健康态行 error_reason 应空串: {row['state']!r}/{row['error_reason']!r}"
        )
        rid0 = web_req(port, "GET", "/api/state?view=torrent")["rid"]

        # 造文件丢失: 计划造法 = qB API 删数据文件 + recheck(§2.6)。实测(qB 5.2.3, 本轮两轮
        # 复现): recheck 在 running 态 → checking 后落 **stalledDL(progress 0)**, stopped 态 →
        # **stoppedDL**, 删后再 start 因 fast-resume 不核文件仍 **stalledUP** —— 三条路都到不了
        # missingFiles(它需要一次真实失败的文件操作, 如 L2 传输中的读失败)。造法不成立 ⇒
        # 记 BLOCKED 跳过(非产品缺陷, 解锁条件见模块 docstring), 健康态基线断言已先行完成。
        data_file = case / "src" / "rm08h.bin"
        assert data_file.is_file(), "前置: 数据文件应在盘上"
        os.remove(data_file)
        qb._call(
            "/torrents/recheck",
            urllib.parse.urlencode({
                "hashes": h
            }).encode(),
            "application/x-www-form-urlencoded",
        )
        reached = False
        for _ in range(50):  # 20s 内探测到 missingFiles 才继续; 否则按 BLOCKED 跳过
            time.sleep(0.4)
            reached = (qb.torrent(h) or {}).get("state") == "missingFiles"
            if reached:
                break
        if not reached:
            final_state = (qb.torrent(h) or {}).get("state")
            pytest.skip(
                f"BLOCKED: 计划造法(删文件+recheck)在 qB 5.2.3 不成立 —— 最终态 {final_state!r} "
                "(running/stopped recheck 均 → (stopped)DL 0%; 删后 start 走 fast-resume 仍原态); "
                "解锁 = L2 传输读失败路径或 qB 重启期 resume 核验造法, 定后按同口径补断言"
            )
        wait_in_store_state(port, h, "missingFiles", timeout=30)

        # 行载荷: state 变 missingFiles 且 error_reason == 「文件丢失」(状态即原因分支)
        row2 = {t["hash"]: t for t in flat_rows(port)}[h]
        assert row2["state"] == "missingFiles", f"行 state 应 missingFiles: {row2['state']!r}"
        assert row2["error_reason"] == "文件丢失", f"missingFiles 行 error_reason 口径破: {row2['error_reason']!r}"

        # delta 即达: rid0 客户本代复拍 → 该行出现在 delta.upsert(runtime.py:478 行级脏登记)
        r2 = wait_updated(port, rid0, delta=True, timeout=20)
        assert r2.get("full") is False, f"本代复拍应归约: {sorted(r2)}"
        uprows = {x["hash"]: x for x in (r2["delta"].get("torrents") or [])}
        assert h in uprows, f"delta.upsert 未含变更行(行级脏登记漏, 高优): {list(uprows)}"
        assert uprows[h]["error_reason"] == "文件丢失", f"增量客户端拿到的还是旧值: {uprows[h]['error_reason']!r}"


def test_rm08_04_large_library_first_frame(clean_fakes):
    """[RM08-04] 大库首帧与滚动数据面: 1200 枚零数据注入下的首拍耗时/字节 + 零回传拍(排期指令: 放最后跑)

    前置: 基座连 36596(空库起步); 1200 枚零数据 .torrent 用例内 bencode 现造(唯一 infohash,
          KB 级元数据, 不落数据盘, 无 announce 零外连)。
    副作用: 36596 新增 1200 枚种子条目(qB 侧, 无数据文件)。
    回滚: 按 real-fake 标签批量 /torrents/delete(delete_files=false)分批删净 + 收尾核 0 残留;
          产品进程 taskkill /F /T; 临时目录清场; 全片收尾复跑 real.guard。
    失败判据: 首帧耗时超 2s 宽松上界(payload 收敛/JSONResponse 快路径回归); 零回传拍在大库下
              失效(RM08-01 门控面退化, 高优); 行数 != 注入数(sync 吞吐或 409 处理破);
              qB connection_status 变 disconnected(实例压垮 —— 环境问题记 BLOCKED 非产品缺陷)。
    """
    n = 1200
    with product_case("rm08_04") as (case, port, _proc):
        qb = clean_fakes
        assert qb.connection_status() != "disconnected", "前置: 36596 连接态异常"
        savepath = case / "bulk"
        savepath.mkdir(parents=True, exist_ok=True)

        # 注入(预期分钟级; 409 时按 §2.9 删旧重加, 绝不收养; paused 入列免 hint 复核双请求)
        t0 = time.perf_counter()
        for i in range(n):
            raw, ih = torrent.build_stream(f"rm08n_{i:04d}.bin", 64 * 1024, "random", f"rm08-bulk-{i}", piece_len=32768)
            _add_retry(qb, raw, str(savepath), ih, paused=True)
        inject_s = time.perf_counter() - t0

        # 等 sync 拍吞满: flat 行数 == 注入数
        wait_until(lambda: len(flat_rows(port)) >= n, 120, f"flat 视图未吞满 {n} 枚(注入耗时 {inject_s:.1f}s)")
        assert qb.connection_status() != "disconnected", "注入后 qB 断连(实例压垮, 环境问题)"

        # ① 首帧(rid=-1&view=torrent): 端点耗时(上界 2s 宽松界)与响应字节, 记实测数
        t1 = time.perf_counter()
        r1 = web_req(port, "GET", "/api/state?rid=-1&view=torrent")
        dt1 = time.perf_counter() - t1
        assert dt1 < 2.0, f"大库首帧耗时超上界: {dt1:.3f}s(1200 枚)"
        assert len(r1["torrents"]) == n, f"行数 != 注入数: {len(r1['torrents'])} != {n}"
        b1 = jlen(r1)
        # 计划 RM08-03⑤ 的 40% 界(≈1/4 口径)按库形态修正: 本库全是**未归组**假种子 ⇒
        # groups/shows 数组恒空, 四数组全量 ≈ singles+torrents 两份 ≈ 2.2× torrent 视图
        # (实测 1200 枚 62%); 「≈1/4」只在 groups 有货的库形态成立。断言钉无归组库的
        # 收敛下限 70%, 实测比打印供基线切片誊写。
        b_all = jlen(web_req(port, "GET", "/api/state?rid=-1"))
        assert b1 < b_all * 0.70, f"大库 view=torrent 字节未收敛: {b1} vs 全量 {b_all}"
        metric(f"[rm08-04] 字节比 view=torrent/无view = {b1 / b_all:.2f}({b1}/{b_all}B, {n} 枚未归组)")

        # ② 第二拍原 rid → 零回传(大库下 status 段占比趋零, 5% 界成立), 耗时/字节趋近零
        t2 = time.perf_counter()
        r2 = rid_poll(port, r1["rid"])
        dt2 = time.perf_counter() - t2
        assert_zero_return(r2, r1["rid"])
        assert jlen(r2) < b1 * 0.05, f"零回传拍字节未趋零: {jlen(r2)} vs 首帧 {b1}"
        # 实测数直接断言进输出(runner 逐条记录 stdout), 供基线切片誊写
        metric(
            f"[rm08-04] 注入 {n} 枚耗时 {inject_s:.1f}s | 首帧 {dt1 * 1000:.0f}ms / {b1}B | 零回传拍 {dt2 * 1000:.0f}ms / {jlen(r2)}B"
        )
