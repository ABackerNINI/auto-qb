"""RM06 HR 在线核实(L1 数据面)—— 八条真机用例(取数通道鉴权/发现 · 任务下发回传 · 三态判定 · 频控 · 排除表 · 状态读面)。

验证面对准冻结计划 plans/26-10-31-1350-plan-real-RM06.html §03 的八条 spec:
通道鉴权与发现(RM06-01)· 任务下发与回传正向(RM06-02)· 命中侧管束打标(RM06-03)·
未命中侧放行+对照(RM06-04)· 错误侧登录页/超时(RM06-05)· 频控间隔+日额(RM06-06)·
HR 排除表动态开关(RM06-07)· 站点状态读面+HR 关闭守卫(RM06-08)。

代码实况落刀点(计划给意图, 这里按 src 实况; 文件:行号为 2026-10-31 HEAD 锚点):
- 零外连红线: 产品取数唯一分支点 build_channel_fetcher(fetcher.py:236-253) —— channel.enabled=true
  时只有 ChannelFetcher, 它把任务排进本地队列并由扩展经 http://127.0.0.1:<port>/api/hr/* 取走;
  本片测试**扮演扩展**(HTTP 客户端), 回传本地构造的 HTML/种子字节, 结构上不出网卡。正向之外
  每条收尾 assert_zero_external 扫产品日志(无堆栈/无对外网络错误痕迹)兜底。
- 回传两道关(server.py:_result_response → queue.submit): 任务 id 必须是**派发过的** + 域名一致
  —— 桩一律先 GET /api/hr/tasks 拿任务原文再回传, 绝不自造 id; 任务 URL 域名断言 == 站点档案域
  (UrlPolicy SSRF 边界, channel.py:180-223)。
- 回传 HTML 全部经 tests/hr_helpers.py 的 myhr_page()/row() 产物(计划 §08 风险 1: 对齐 parse.py
  口径, 已在本地单测验证 btschool adapter parse_page A/B/C 全过 + LOGIN_PAGE looks_like_login 命中
  + lib.torrent 字节 compute_infohashes == qB infohash); 行名设计按 K=12 粗配口径(service.py:128)。
- 档位语义: A=考察中(行无条件身份下载, service.py:984)/B=已达标/C=未达标(终态行**粗配疑似**才下,
  _row_looks_local service.py:987 —— 候选面只含**受管(未排除)**种子名, issue 26-10-08-1304)。
  RM06-07 的「驱动任务」观测面 = 身份下载任务(按 tid 计): 页面任务是站点级的, 与单个种子无关。
- 立即拉取: POST /api/hr/refresh(force 旗标, runtime.request_refresh 单点)跳过复用窗与拉取间隔,
  min_interval/日额照常(service.py:539-590); 锚点每 run_once 现采(worker.py:292) ⇒ 排除标签
  动态开关在下一 force 波即生效。
- 校验下限(config/validation/sections.py): min_interval>=5S / reuse_window>=60S /
  request_timeout 5S-3600S —— 测试配置全部按各自用例配小但不越界。
- 判定输出观测面: /api/hr/status(sites[0].lane_counts/quota/lanes)· /api/hr/sites/<site>/entries
  (条目明细 local_present)· /api/hr/history(波次/defer 行)· data/hr/<site>.json(index/verified)
  · qB API 回读 tags(一律 strip, §2.9 26-10-31-1215 用例侧防御)。

跑法: `commands run real.suite -- --slice RM06 --yes`(不要裸 pytest)。真实种子全程非活跃;
八条全部 L1 假种子(announce 本机死端口, 零外连), 一律 real-fake 标签; 标签/排除模式全部收紧
rm06- 前缀, 绝不出现能匹配 real-fake 或真实标签的宽泛模式; 产品 data_dir 各条独立临时目录,
不碰仓库根 auto-qb-data/。L2 站点侧(真实站点取数)按拍板全部 BLOCKED, 解锁=用户单独授权。
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))

import hr_helpers  # noqa: E402  (tests/hr_helpers.py: myhr_page/row/LOGIN_PAGE/torrent_blob)
from lib import app, torrent  # noqa: E402
from lib.net import local_host  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm06"
TAG = "real-fake"
SITE_PRESET = "btschool"  # 内置站点档案 id(config/site_presets.py; 仅用于 hr_check.sites 键)
SITE_DOMAIN = "pt.btschool.club"  # 站点档案 tracker 域(config/site_presets.py), 也是任务 URL 域
SITE_TRACKER = "rm06site"  # trackers 条目名(显式映射 hr_check.sites.btschool.tracker)
# !产品实况(2026-10-31 RM06-03 实测): 服务侧站点键 = **trackers 条目名**(config.hr_site_confs 按
# tracker 名派生, runtime 日志「取数线程已启动: 站点 rm06site」)—— 站点数据文件名 / 任务 site 字段
# / WebUI /api/hr/sites/<site> 路径全部用条目名, 不是档案 id。
SITE_KEY = SITE_TRACKER
TOKEN = "rm06-test-token"  # 通道密钥写死测试值(不靠随机落盘)
DISC_PORT = 39788  # 发现端口显式独立值(默认 18788 防撞; 候选 39788-39790)
HR_TAG = "rm06-hr"  # 考察中管束标签(RM06-03+)
SAT_TAG = "rm06-sat"  # 达标标签(断言**不**被打, RM06-03)
EXCL_TAG = "rm06-excl"  # 排除表标签(RM06-07)
EXT_ORIGIN = "chrome-extension://" + "a" * 32  # 合法扩展 origin(id 32 位 a~p)
BAD_ORIGIN = "https://evil.example"  # 非扩展 origin(必须 403)
SETTLED = {
    "stalledUP", "stalledDL", "pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "missingFiles", "error", "moving"
}

# 假种子 announce 指本机死端口(零外连, §2.9 第①条); 匹配按 hostname 不含端口。
FAKE_HOST = local_host()
ANNOUNCE_IP = f"http://{FAKE_HOST}:1/announce"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY: 127.0.0.1 不走代理

# ---------------------------------------------------------------- 基座(照 RM05 体例)


def qbfake():
    from lib import instances
    return instances.make(36596)


def _tags_of(t) -> set[str]:
    """qB tags 字段容错解析: 多标签以「, 」连接, 一律 strip 后判成员(§2.9 / 26-10-31-1215 用例侧防御)。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def _add_retry(qb, raw: bytes, savepath: str, ih: str) -> None:
    """加种子, 409 双义处理(qB 5.2 重复 infohash 返回 409 Conflict; §2.9 第②条: 绝不收养)。"""
    from lib.qb import QbError
    for _attempt in range(4):
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


def rm_all_fakes_with_sweep(qb, name_prefix: str) -> list[str]:
    """清场: 先按 real-fake 标签删, 再按 rm06 名字前缀扫无标签残留兜底(26-10-31-1215 失明防御)。"""
    gone = []
    for t in qb.torrents():
        if TAG in _tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            gone.append(t["name"])
    if gone:
        wait_until(lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 15, f"清理后仍有 real-fake 残留: {gone}")
    for t in qb.torrents():
        if t.get("name", "").startswith(name_prefix):
            qb.delete(t["hash"], delete_files=True)
            gone.append(f"[sweep]{t['name']}")
    if gone:
        wait_until(lambda: not qb.torrents(), 15, f"清场后 36596 仍有种子残留: {gone}")
    return gone


def global_tags(qb) -> list[str]:
    return json.loads(qb._call("/torrents/tags"))


def delete_global_tags(qb, names: list[str]) -> None:
    if not names:
        return
    body = urllib.parse.urlencode({"tags": ",".join(names)}).encode()
    qb._call("/torrents/deleteTags", body, "application/x-www-form-urlencoded")


def cleanup_rm06_defs(qb) -> list[str]:
    """清掉本片造的 rm06-* 标签定义(模式收紧 rm06 前缀, 绝不碰 real-fake/真实标签)。"""
    gone = [t for t in global_tags(qb) if t.startswith("rm06")]
    delete_global_tags(qb, gone)
    if gone:
        wait_until(lambda: not [t for t in global_tags(qb) if t.startswith("rm06")], 10, f"标签定义删除未生效: {gone}")
    return gone


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


def wait_until(fn, timeout: float, desc: str, interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。

    fn 抛异常视同「还没就绪」继续轮询(启动竞态实况 2026-10-31 RM06-05: 端点启动行比 WEB 行
    晚 ~1ms, 首轮 fn 内 assert 直接炸掉会假红); 超时消息带最后一个异常。"""
    deadline = time.time() + timeout
    last = None
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            last = fn()
        except (AssertionError, OSError, ValueError) as e:  # 观测型异常 = 还没就绪
            last, last_exc = None, e
        if last:
            return last
        time.sleep(interval)
    tail = f"; 最后异常: {last_exc}" if last_exc is not None else ""
    raise AssertionError(f"等待超时({timeout}s): {desc}; 最后观测: {last}{tail}")


def settle(qb, ih: str, timeout: float = 30.0) -> dict:
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
    assert "Traceback" not in log_text(case), "产品日志出现未捕获异常堆栈"


def assert_zero_external(case: Path) -> None:
    """零外连兜底: 结构性保证在 fetcher.py:252(唯一分支点, 端点只听 127.0.0.1); 这里扫日志痕。"""
    log = log_text(case)
    assert "Traceback" not in log, "产品日志出现未捕获异常堆栈"
    for pat in ("Max retries exceeded", "Connection refused", "Name or service not known", "getaddrinfo failed"):
        assert pat not in log, f"产品日志出现疑似对外的网络错误痕迹(零外连红线): {pat}"


def fake_seed(qb, name: str, salt: str, savepath) -> tuple[str, bytes]:
    """造一枚 L1 假种子并加入 36596(带 real-fake 标签); 返回 (infohash, .torrent 原始字节)。

    字节必须留着: 身份登记路径是「站点行下载 .torrent → compute_infohashes → 与本地 infohash
    对碰」(service._run_downloads), 桩回传的就是这份字节 ⇒ 条目绑定到本地种子(RM06-02 正向链)。"""
    savepath = Path(savepath)
    savepath.mkdir(parents=True, exist_ok=True)  # savepath 得存在; 文件不写 ⇒ 永远 progress 0
    raw, ih = torrent.build_stream(name, 256 * 1024, "random", salt, ANNOUNCE_IP)
    _add_retry(qb, raw, str(savepath), ih)
    settle(qb, ih)
    return ih, raw


# ---------------------------------------------------------------- 配置


def write_cfg(
    case: Path,
    *,
    web_port: int,
    add_tag: str = "",
    add_tag_satisfied: str = "",
    exclude_tags: list[str] | None = None,
    min_interval_s: int = 5,
    max_requests_per_day: int = 240,
    request_timeout_s: int = 20,
    hr_check_enabled: bool = True
) -> Path:
    """生成临时配置(schema_version: 5, 直连 36596 空库; 计划 §03 基座口径)。

    - trackers 恰 1 条目: domains=[站点档案 tracker 域]+[本机 IP] —— 域名交集派生站点绑定
      (loaders._resolve_hr_site_bindings), 本机 IP 使假种子(announce=本机IP:1)进匹配管线;
      条目必带 hr 段(绑定校验: 「已绑定站点…未配置 hr 段」ConfigError, §2.11)。
    - hr_check.channel: 回环 + token 写死 + port=0 随机 + discovery_port 显式独立值(防 18788 撞车);
      request_timeout/min_interval 配小但不越校验下限(min_interval>=5S, request_timeout>=5S)。
    - 站点 refresh_interval/idle 配大(3600S): 波次一律由 POST /api/hr/refresh(force)驱动, 不干等节拍。
    """
    entry: dict = {
        "domains": [SITE_DOMAIN, FAKE_HOST],
        "hr": {
            "required_seeding_time": "3D"
        },
    }
    if add_tag:
        entry["hr"]["add_tag"] = add_tag
    if add_tag_satisfied:
        entry["hr"]["add_tag_for_satisfied"] = add_tag_satisfied
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
        "interval": "3S",
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
        "web": {
            "enabled": True,
            "host": "127.0.0.1",
            "port": web_port,
            "skip_local_verify": True
        },
        "trackers": {
            SITE_TRACKER: entry
        },
    }
    if hr_check_enabled:
        cfg["hr_check"] = {
            "enabled": True,
            "min_interval": f"{min_interval_s}S",
            "max_requests_per_day": max_requests_per_day,
            "reuse_window": "60S",
            "channel":
                {
                    "enabled": True,
                    "host": "127.0.0.1",
                    "port": 0,
                    "discovery_port": DISC_PORT,
                    "pairing": "auto",
                    "token": TOKEN,
                    "request_timeout": f"{request_timeout_s}S",
                },
            "sites":
                {
                    SITE_PRESET:
                        {
                            "enabled": True,
                            "tracker": SITE_TRACKER,
                            "refresh_interval": "3600S",
                            "idle_refresh_interval": "3600S",
                        }
                },
        }
    if exclude_tags:
        cfg["hr"] = {"exclude_tags": list(exclude_tags)}
    path = case / "config.yml"
    path.write_text(yaml.safe_dump({"config": cfg}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {path}")
    if "port: 36596" not in text:
        raise AssertionError(f"配置没指向 36596(空库草稿本), 拒跑: {path}")
    return path


def web_req(web_port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    """产品 WebUI 本地请求(经 /api/hr/* 只读面; RM05-02 同款绕代理 opener)。"""
    req = urllib.request.Request(
        f"http://127.0.0.1:{web_port}{path}",
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _OPENER.open(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"detail": raw}


def hr_status(web_port: int) -> dict:
    code, payload = web_req(web_port, "GET", "/api/hr/status")
    assert code == 200, f"GET /api/hr/status -> {code}: {payload}"
    return payload


def site_of_status(st: dict) -> dict:
    sites = [s for s in st.get("sites", []) if s.get("site") == SITE_KEY]
    assert sites, f"/api/hr/status 无站点 {SITE_KEY}: {json.dumps(st, ensure_ascii=False)[:400]}"
    return sites[0]


def site_file(case: Path) -> dict:
    """站点数据文件 <data_dir>/hr/<site>.json(store.py:6 落点; 外部观测面之一)。"""
    p = case / "data" / "hr" / f"{SITE_KEY}.json"
    assert p.is_file(), f"站点文件不存在: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def site_index(case: Path) -> dict[int, dict]:
    """站点文件 index(tid -> 条目)。注意 JSON 落盘形态是**列表**(每项含 tid), 不是字典。"""
    raw = site_file(case).get("index") or []
    items = raw if isinstance(raw, list) else list(raw.values())
    return {int(e.get("tid") or 0): e for e in items if isinstance(e, dict)}


def site_verified(case: Path) -> set[str]:
    """站点文件 verified 放行记录的 infohash 集合(落盘形态同样是列表, 每项含 infohash)。"""
    raw = site_file(case).get("verified") or []
    items = raw if isinstance(raw, list) else list(raw.values())
    return {str(e.get("infohash") or "").lower() for e in items if isinstance(e, dict)}


def keep_log(case: Path) -> None:
    """把产品日志留档到 WORK(排障证据面; 收尾 purge 会删用例目录, 日志先抢救出来)。"""
    src = case / "data" / "logs" / "auto-qb.log"
    if src.is_file():
        try:
            (WORK / f"{case.name}.log").write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        except OSError:
            pass


def endpoint_port_from_log(case: Path) -> int:
    """从产品日志取数据端点实绑端口(port=0 随机; 启动行「HR 取数通道端点已启动: http://…」)。"""
    m = re.findall(r"HR 取数通道端点已启动: http://127\.0\.0\.1:(\d+)", log_text(case))
    assert m, f"日志无端点启动行:\n{log_text(case)[-800:]}"
    return int(m[-1])


def start_product(cfg: Path, case: Path, timeout: float = 40.0):
    """起产品并等到三件事: qB 管理器 / WEB UI / HR 取数通道端点全部就绪。

    !任何等待失败都必须把进程停掉再抛(2026-10-31 实测: 泄漏的产品进程会持 state.lock +
    继续写同路径日志 + 向发现注册表心跳, 毒化后续所有用例 —— RM06-05 两轮假红同根源)。"""
    p = app.start(cfg, case)
    try:
        assert p.wait_log("启动 qB 管理器", timeout), f"产品没起来:\n{p.log()[-800:]}"
        assert p.wait_log("WEB UI 已启动", timeout), f"WEB UI 没起来:\n{p.log()[-800:]}"
        wait_until(lambda: endpoint_port_from_log(case), 20, "HR 取数通道端点未启动")
    except BaseException:
        p.stop()
        raise
    return p


# ---------------------------------------------------------------- 扩展桩(HTTP 客户端)


class HrStub:
    """测试侧扮演浏览器扩展: 对产品本地数据端点拉任务/回传(全部 127.0.0.1, 结构上零外连)。

    两道关口径(计划 §08 风险 2): 一律先 GET /api/hr/tasks 拿**派发过的任务原文**, 按任务 id 与
    域名一致回传, 绝不自造 id。page 任务按 scope(A/B/C)回传 HTML; torrent 任务按 tid 回传字节。
    """
    def __init__(self, port: int, token: str = TOKEN):
        self.base = f"http://127.0.0.1:{port}"
        self.token = token
        self.seen: list[tuple[float, dict]] = []  # (monotonic, task 原文) —— 间隔/计数断言的证据面

    def mark(self) -> int:
        """记当前 seen 长度(逐波记账用: 下一波的任务 = seen[mark():])"""
        return len(self.seen)

    def _req(self, method: str, path: str, headers: dict | None = None, body: bytes | None = None):
        req = urllib.request.Request(self.base + path, method=method, data=body)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with _OPENER.open(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"detail": raw}

    def auth_headers(self, *, origin: str | None = None, token: str | None = None) -> dict:
        h = {}
        tok = self.token if token is None else token
        if tok:
            h["X-Hr-Token"] = tok
        if origin is not None:
            h["Origin"] = origin
        return h

    def get_tasks(self, **kw):
        return self._req("GET", "/api/hr/tasks", self.auth_headers(**kw))

    def post_result(
        self, task: dict, *, ok: bool = True, body: bytes = b"", status: int = 200, error: str = "", kind: str = ""
    ):
        payload = {
            "id": task["id"],
            "ok": ok,
            "status": status,
            "url": task["url"],
            "body_b64": base64.b64encode(body).decode("ascii"),
        }
        if error:
            payload["error"] = error
        if kind:
            payload["kind"] = kind
        h = self.auth_headers()
        h["Content-Type"] = "application/json"
        return self._req("POST", "/api/hr/result", h, json.dumps({"results": [payload]}).encode("utf-8"))

    def force(self):
        return self._req("POST", "/api/hr/refresh", self.auth_headers())

    def discover(self, disc_port: int = DISC_PORT):
        """发现端点(免 token; 回环 pairing 默认关, discovery.py:378-397)。

        !发现服务与数据端点是**两个监听**(discovery_port 独立, 本片 39788) —— 打数据端口的
        /api/hr/discover 会 401(数据端点只认四路数据路由, RM06-01 实测)。"""
        req = urllib.request.Request(f"http://127.0.0.1:{disc_port}/api/hr/discover", method="GET")
        try:
            with _OPENER.open(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"detail": raw}

    # ---- 驱动 ----

    def drive(self, answer, *, max_seconds: float = 90.0, quiet_s: float = 12.0, poll: float = 0.3) -> list[dict]:
        """轮询拉任务并回传, 直到波静默(quiet_s 无新任务)或超时; 返回本轮见过的任务列表。

        answer(task) -> dict(ok/body/status/error/kind) | None(None = 不回传, RM06-05② 用)。"""
        deadline = time.monotonic() + max_seconds
        last_task_ts: float | None = None
        seen: list[dict] = []
        while time.monotonic() < deadline:
            code, payload = self.get_tasks()
            assert code == 200, f"GET /api/hr/tasks -> {code}: {payload}"
            tasks = payload.get("tasks") or []
            if tasks:
                last_task_ts = time.monotonic()
                for t in tasks:
                    self.seen.append((time.monotonic(), t))
                    seen.append(t)
                    resp = answer(t)
                    if resp is not None:
                        c, rbody = self.post_result(t, **resp)
                        assert c == 200, f"回传被拒(kind={t.get('kind')}): {c} {rbody}"
            elif last_task_ts is not None and time.monotonic() - last_task_ts >= quiet_s:
                break
            time.sleep(poll)
        return seen

    def drain(self, seconds: float, poll: float = 0.4) -> list[dict]:
        """只看不回传地观察 seconds 秒内的任务(频控截断/超时不回传场景的计数面)。"""
        deadline = time.monotonic() + seconds
        seen: list[dict] = []
        while time.monotonic() < deadline:
            code, payload = self.get_tasks()
            assert code == 200, f"GET /api/hr/tasks -> {code}: {payload}"
            for t in payload.get("tasks") or []:
                self.seen.append((time.monotonic(), t))
                seen.append(t)
            time.sleep(poll)
        return seen

    def tasks_since(self, mark: int) -> list[dict]:
        return [t for _, t in self.seen[mark:]]

    def page_task_times(self, lane: str) -> list[float]:
        return [ts for ts, t in self.seen if t.get("kind") == "page" and t.get("scope") == lane]

    def torrent_tids(self) -> list[int]:
        return [int(t.get("tid") or 0) for _, t in self.seen if t.get("kind") == "torrent"]


def page_answer(page_by_lane: dict[str, str], blobs: dict[int, bytes]):
    """构造 drive() 的 answer: page 任务按 scope 回传 HTML(缺该档 = 报错回传), torrent 按 tid 回传字节。"""
    def answer(task: dict):
        kind = task.get("kind")
        if kind == "page":
            html = page_by_lane.get(task.get("scope") or "")
            if html is None:
                return {"ok": False, "status": 0, "error": "stub 无该档页面", "kind": "network"}
            return {"ok": True, "status": 200, "body": html.encode("utf-8")}
        if kind == "torrent":
            tid = int(task.get("tid") or 0)
            blob = blobs.get(tid)
            if blob is None:
                return {"ok": False, "status": 0, "error": "stub 无该 tid 的 .torrent", "kind": "network"}
            return {"ok": True, "status": 200, "body": blob}
        return {"ok": True, "status": 200, "body": b""}

    return answer


def task_domain(task: dict) -> str:
    return urllib.parse.urlparse(task.get("url") or "").hostname or ""


# ================================================================ RM06-01


def test_rm06_01_channel_auth_and_discovery():
    """[RM06-01] 通道鉴权与发现: 无/错 token 401 · 非扩展 origin 403 · 正确凭据 200 + 发现端点自动分发(负向内建)

    前置: 完整通道基座(§03); 1 枚假种子(保证任务队列非空); 数据端点 port=0 随机, 实绑端口取自产品日志。
    副作用: 1 假种子; hr.token/站点文件落用例临时 data_dir; 36596 无写。
    回滚: real.seed.rm --all + 删用例临时目录; 实例无残留。
    失败判据: 错 token 拿到 200(鉴权失效, 高优 FAIL); 正确凭据被 401/403; 401 时通道接触状态仍被写;
              发现回执缺端口或 token; 任务 URL 域名不是站点档案域名(UrlPolicy 失守 = SSRF 红线);
              出现对站点域名的真实连接(零外连红线, 立即停手)。
    """
    case = case_dir("rm06_01")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        fake_seed(qb, "rm06c1.bin", "rm06c1", WORK / "rm06_01")
        cfg = write_cfg(case, web_port=app.free_port(), request_timeout_s=8)
        p = start_product(cfg, case)
        wp = _web_port_of(cfg)
        port = endpoint_port_from_log(case)
        stub = HrStub(port)

        # ---- 无 token → 401 且不写任何状态
        code, body = stub.get_tasks(token="")
        assert code == 401, f"无 token 应 401: {code} {body}"
        # ---- 错 token → 401
        code, body = stub.get_tasks(token="rm06-wrong-token")
        assert code == 401, f"错 token 应 401: {code} {body}"
        # ---- 正确 token + 非扩展 origin → 403
        code, body = stub.get_tasks(origin=BAD_ORIGIN)
        assert code == 403, f"非扩展 origin 应 403: {code} {body}"
        # ---- 401/403 不得写通道接触状态(last_contact 仍为 0), 被拒面进日志(RejectThrottle)
        st = hr_status(wp)
        chan = st.get("channel") or {}
        assert chan.get("listening") is True, f"端点应已在监听: {chan}"
        assert not chan.get("last_contact_ts"), f"被拒敲门不该写 last_contact(契约破): {chan}"
        # 注: 不断言 pending==0 —— 产品启动即跑首轮 auto 波, 队列里有在途任务是常态;
        # 「401 不写状态」的契约落在 last_contact_ts 上(它只被成功鉴权的接触写, server.py:395)。
        # 被拒面进日志(RejectThrottle): 同类被拒「状态变化报一次 + 长周期提醒」(server.py:87-117),
        # 两次 401 同 kind ⇒ 只有一条 WARNING「鉴权失败」—— 记一次即证被拒面被记账。
        wait_until(lambda: count_anchor(case, r"鉴权失败") >= 1, 10, "日志无 401 记录(RejectThrottle 未记)")
        wait_until(lambda: count_anchor(case, r"拒绝非白名单 origin") >= 1, 10, "日志无 403 记录(RejectThrottle 未记)")

        # ---- 正确 token + 扩展 origin: force 后 200 拿到任务 JSON(结构含 id 与 URL)
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"POST /api/hr/refresh 受理失败: {code} {r}"
        code, payload = stub.get_tasks(origin=EXT_ORIGIN)
        assert code == 200, f"正确凭据应 200: {code} {payload}"
        tasks = payload.get("tasks") or []
        assert tasks, f"任务队列为空(种子没进对象集/波次没派发): {payload}"
        page_tasks = [t for t in tasks if t.get("kind") == "page"]
        assert page_tasks, f"无 page 任务: {tasks}"
        assert all(task_domain(t) == SITE_DOMAIN for t in tasks), \
            f"任务 URL 域名不是站点档案域名(UrlPolicy SSRF 边界失守): {tasks}"
        assert all(t.get("id") and t.get("site") == SITE_KEY for t in tasks), f"任务结构缺 id/site: {tasks}"

        # ---- 发现端点: 一个地址拿到 数据端点 + token(回环 pairing 默认关)
        code, disc = stub.discover()
        assert code == 200, f"发现端点应 200: {code} {disc}"
        instances_ = disc.get("instances") or []
        assert instances_, f"发现回执无实例: {disc}"
        # 注册表是跨进程共享文件(discovery.InstanceRegistry, TTL 120s): 本机其它存活实例也会在列
        # —— 按本实例的 token + 实绑端口挑出自己的那条; 回执 endpoint 是 base(http://host:port, 无路径)。
        mine = [e for e in instances_ if e.get("token") == TOKEN and str(e.get("endpoint", "")).endswith(f":{port}")]
        assert mine, f"发现回执缺本实例(token={TOKEN}, port={port}): {disc}"
        entry = mine[0]
        assert entry["endpoint"] == f"http://127.0.0.1:{port}", \
            f"发现回执端点与实绑数据端口不符: {entry} vs {port}"
        assert entry.get("token") == TOKEN, f"发现回执 token 不符(扩展无法配对): {entry.get('token')!r}"
        assert entry.get("id") and entry.get("name"), f"发现回执缺 id/name: {entry}"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c1")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


def _web_port_of(cfg: Path) -> int:
    """从配置文件读回 web 端口(用例自分配的值, 不从日志猜)。"""
    tree = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    return int(tree["config"]["web"]["port"])


# ================================================================ RM06-02


def test_rm06_02_task_dispatch_and_result_roundtrip():
    """[RM06-02] 任务下发与结果回传正向: 种子进对象集 → 页面任务 → 回传命中 HTML → 站点数据落 index

    前置: 基座 + 1 枚假种子(名含特征串); request_timeout 配小(20S); 波次由 force 驱动不干等节拍。
    副作用: 1 假种子; hr 站点文件写临时 data_dir。
    回滚: real.seed.rm --all + 删临时目录。
    失败判据: 收不到任务(种子没进对象集 —— 查绑定/锚点链路, 排不通记 BLOCKED); 回传被拒(两道关口径
              分叉); status 无考察中条目; index 落了错误 infohash(命中识别分叉)。
    """
    case = case_dir("rm06_02")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        name = "rm06c2beta marker show 2026"
        ih, raw = fake_seed(qb, name, "rm06c2-a", WORK / "rm06_02")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp)
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"

        # A 档一页含命中行(tid 601); B/C 档空表(合法空结果); 601 下载回传**假种子原字节** ⇒
        # 身份登记 compute_infohashes == 本地 infohash ⇒ 命中绑定(local_hashes 命中面)。
        hit_html = hr_helpers.myhr_page([hr_helpers.row(601, name)])
        empty_html = hr_helpers.myhr_page([])
        seen = stub.drive(page_answer({"A": hit_html, "B": empty_html, "C": empty_html}, {601: raw}), max_seconds=60)
        page_tasks = [t for t in seen if t.get("kind") == "page"]
        assert page_tasks, f"整波没收到任何 page 任务(对象集/绑定链路不通): {len(seen)} 条"
        assert all(task_domain(t) == SITE_DOMAIN for t in seen), f"任务 URL 域名越界: {seen}"
        dl = [t for t in seen if t.get("kind") == "torrent"]
        assert dl and dl[0].get("tid") == 601, f"A 档行应无条件触发身份下载任务: {seen}"

        # ---- 站点数据落 index + 绑定本地 infohash
        entry = wait_until(lambda: site_index(case).get(601), 20, "站点文件 index 未出现 601 条目(回传/解析/落盘链路断)")
        got = entry.get("infohash_v1") or entry.get("infohash_v2")
        assert got and got.lower() == ih.lower(), f"index infohash 与本地种子不符: {got} vs {ih}"

        # ---- WebUI status: 考察中计数 + entries 的 local_present
        st = hr_status(wp)
        s0 = site_of_status(st)
        assert (s0.get("lane_counts") or {}).get("A", 0) >= 1, f"lane A 计数应 >=1: {s0.get('lane_counts')}"
        code, entries = web_req(wp, "GET", f"/api/hr/sites/{SITE_KEY}/entries")
        assert code == 200, f"entries 端点应 200: {code}"
        rows = entries.get("entries") or []
        assert rows, f"entries 无行: {entries}"
        r0 = rows[0]
        assert r0.get("local_present") is True, f"条目应绑定本地 infohash(local_present): {r0}"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c2")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


# ================================================================ RM06-03


def test_rm06_03_hit_lane_a_tagging():
    """[RM06-03] 三态判定·命中侧: 行命中 → 考察中管束 → HR 标签下发(全量纳入口径)

    前置: 基座 + 1 假种子 + 站点 hr 段 add_tag: rm06-hr(另配 add_tag_for_satisfied: rm06-sat 作达标
          负向对照); 回传命中 HTML 使条目进 lane=A。
    副作用: 1 假种子被打 rm06-hr; hr 站点文件写临时 data_dir。
    回滚: real.seed.rm --all + 清 rm06-* 标签与定义 + 删临时目录。
    失败判据: 考察中种子未被打 rm06-hr(管束/打标链路断); 打了达标标签 rm06-sat(分流分叉);
              qB 回读 tags 缺 strip 导致断言假红(测试侧缺陷, 修用例); 断言咬内部实现而非外部观测(口径错)。
    """
    case = case_dir("rm06_03")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        name = "rm06c3beta marker show"
        ih, raw = fake_seed(qb, name, "rm06c3-a", WORK / "rm06_03")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp, add_tag=HR_TAG, add_tag_satisfied=SAT_TAG)
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"

        hit_html = hr_helpers.myhr_page([hr_helpers.row(601, name)])
        empty_html = hr_helpers.myhr_page([])
        stub.drive(page_answer({"A": hit_html, "B": empty_html, "C": empty_html}, {601: raw}), max_seconds=60)
        wait_until(lambda: site_index(case).get(601), 20, "index 未出现 601 条目")

        # ---- 管束打标: 考察中绝对权威 → 维护管线把 rm06-hr 打上种子(qB API 回读, strip 口径)
        wait_until(
            lambda: HR_TAG in _tags_of(qb.torrent(ih) or {}), 30,
            f"考察中种子未被打 {HR_TAG}: {sorted(_tags_of(qb.torrent(ih) or {}))}"
        )
        tags = _tags_of(qb.torrent(ih) or {})
        assert SAT_TAG not in tags, f"达标标签不该被打(做种 0s < required): {sorted(tags)}"
        assert TAG in tags, f"real-fake 管理标签丢了(种子侧入库问题): {sorted(tags)}"
        # ---- status 考察中 +1
        st = hr_status(wp)
        s0 = site_of_status(st)
        assert (s0.get("lane_counts") or {}).get("A", 0) >= 1, f"lane_counts 考察中应 +1: {s0.get('lane_counts')}"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c3")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


# ================================================================ RM06-04


def test_rm06_04_miss_lane_release_and_contrast():
    """[RM06-04] 三态判定·未命中侧: 全不重合 → 未列出放行记录生效 + 对照种子照常管束(对照内建)

    前置: 基座 + 2 假种子(甲名与 HTML 行全不重合, 乙名命中其中一行); 回传一份含两行的 HTML。
    副作用: 2 假种子; 乙被打 rm06-hr; 甲获放行记录(站点文件 verified)。
    回滚: real.seed.rm --all + 清 rm06-* 标签与定义 + 删临时目录。
    失败判据: 甲被误判考察中/误打标(粗配过宽 —— K=12 语义分叉); 甲未得放行记录(对账侧漏);
              放行记录未生效: 第二波再签发甲的放行(对照必须红 —— 红不了如实降 L2); 乙反而被放行。
    """
    case = case_dir("rm06_04")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        miss_name = "rm06c4 miss alpha one"  # 甲: 与两行名全不重合(K=12 无连续重合段)
        hit_name = "rm06c4beta marker show"  # 乙: 行 601 名命中
        ih_miss, _ = fake_seed(qb, miss_name, "rm06c4-a", WORK / "rm06_04")
        ih_hit, raw_hit = fake_seed(qb, hit_name, "rm06c4-b", WORK / "rm06_04")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp, add_tag=HR_TAG)
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))

        # 行 601 名命中乙(下载回乙字节 → 绑定); 行 602 名与甲不重合(下载回无关字节 → 绑到非本地,
        # 不产生失败重试噪音)。甲的 infohash 全程不经回传 ⇒ 不可能被绑定。
        hit_html = hr_helpers.myhr_page(
            [
                hr_helpers.row(601, hit_name + " 2026"),
                hr_helpers.row(602, "completely unrelated title here"),
            ]
        )
        empty_html = hr_helpers.myhr_page([])
        foreign = hr_helpers.torrent_blob(name="completely unrelated title here")
        answers = page_answer({"A": hit_html, "B": empty_html, "C": empty_html}, {601: raw_hit, 602: foreign})

        def force_wave(max_seconds: float = 45.0):
            """force + 驱动到波静默。!编排实况(2026-10-31 实测): 产品启动即跑首轮 auto 波(锚点
            采集先于首轮 qB 同步 ⇒ 空锚点, 只有站点级取数无命中/放行), force 旗标一次性且落在
            min_interval 闸内会被 defer —— 所以「先 drive 完当前波, 再 force 下一波」; drive 的
            12s 静默窗已盖过 min_interval 5s, force 不会被 defer。"""
            code, r = stub.force()
            assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"
            return stub.drive(answers, max_seconds=max_seconds)

        # 波 1(启动 auto 波): 站点级取数 + 身份下载(空锚点, 无命中/放行)
        force_wave(60)
        wait_until(lambda: site_index(case).get(601), 20, "index 未出现 601(乙)")

        # 波 2(锚点在场): 乙命中(行 601 已绑定本地 infohash), 甲(未对账)得「未列出」放行记录
        force_wave(60)
        wait_until(lambda: ih_miss.lower() in site_verified(case), 20, "甲未得放行记录(verified 未签发, 对账侧漏)")
        assert (site_index(case).get(601) or {}).get("infohash_v1", "").lower() == ih_hit.lower(), \
            "行 601 未绑定乙的 infohash"
        releases_1 = count_anchor(case, r"本波签发「未列出」放行")
        assert releases_1 >= 1, "无「未列出」放行日志(对账签发面未发生)"
        wait_until(
            lambda: HR_TAG in _tags_of(qb.torrent(ih_hit) or {}), 30,
            f"对照乙未被打 {HR_TAG}: {sorted(_tags_of(qb.torrent(ih_hit) or {}))}"
        )
        # 甲在站点数据到位前会被行 4 本地兜底保守打标(maintenance_mod「其余全量纳入」), 打标先于
        # 放行证据; RELEASED 的语义是「不打标维持现状」不摘标 —— 故甲的放行判据咬 verified 记录,
        # 不咬标签 absence(那会咬到启动期兜底打标, 不是本条验证面)。

        # ---- 放行记录生效: 下一波不再为甲签发放行(甲出对象集) —— 签发计数守恒红验
        force_wave(45)
        releases_2 = count_anchor(case, r"本波签发「未列出」放行")
        assert releases_2 == releases_1, \
            f"放行记录未生效: 下一波又为甲签发放行(对象集未清): {releases_1} -> {releases_2}"
        assert ih_miss.lower() in site_verified(case), "下一波后甲的放行记录丢失"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c4")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


# ================================================================ RM06-05


def test_rm06_05_error_paths_login_and_timeout():
    """[RM06-05] 三态判定·错误侧: 登录页回传 → HrLoginExpired 分档 + 超时不回传 → 失败分档且锁释放

    前置: 基座 + 1 假种子 ×2 段; ①② 各自独立临时目录(独立 data_dir); ② request_timeout 配小(8S)。
    副作用: 1 假种子 ×2; 临时目录内站点文件。
    回滚: real.seed.rm --all + 删临时目录 ×2。
    失败判据: 登录页被当正常页面解析(分档失明, 站点数据被污染); 超时后站点锁永久持住(下一波收不到
              任务 —— request_timeout 要防的事故); 超时未计入失败/中断(记账漏); 断言等满默认 180s(测试侧配置漏)。
    """
    qb = qbfake()
    # ---------- ① 登录页回传 ----------
    case1 = case_dir("rm06_05a")
    p1 = None
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c5"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        fake_seed(qb, "rm06c5a.bin", "rm06c5-a", WORK / "rm06_05a")
        cfg = write_cfg(case1, web_port=app.free_port())
        p1 = start_product(cfg, case1)
        stub = HrStub(endpoint_port_from_log(case1))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"
        seen = stub.drive(
            lambda t: (
                {
                    "ok": True,
                    "status": 200,
                    "body": hr_helpers.LOGIN_PAGE.encode("utf-8")
                } if t.get("kind") == "page" else {
                    "ok": True,
                    "status": 200,
                    "body": b""
                }
            ),
            max_seconds=30
        )
        assert any(t.get("kind") == "page" for t in seen), "没收到 page 任务(前置链路断)"
        # 登录态失效: WARNING 日志 + 波次历史 error 分档; 站点数据不被污染(无半写 index)
        wait_until(lambda: "登录" in log_text(case1), 15, "日志无登录态失效记录(HrLoginExpired 分档失明)")
        wp1 = _web_port_of(cfg)
        st = hr_status(wp1)
        s0 = site_of_status(st)
        assert not (s0.get("index_total") or 0), f"登录页不该写任何 index 条目(数据被污染): {s0.get('index_total')}"
        code, hist = web_req(wp1, "GET", "/api/hr/history")
        assert code == 200, f"history 应 200: {code}"
        blob = json.dumps(hist, ensure_ascii=False)
        assert "error" in blob or "登录" in blob, f"history 无 error/登录分档痕迹: {blob[:400]}"
        assert_no_crash(case1)
    finally:
        if p1 is not None:
            p1.stop()
        keep_log(case1)
        rm_all_fakes_with_sweep(qbfake(), "rm06c5a")
        cleanup_rm06_defs(qbfake())
        purge_tree(case1)

    # ---------- ② 超时不回传 ----------
    case2 = case_dir("rm06_05b")
    p2 = None
    try:
        fake_seed(qb, "rm06c5b.bin", "rm06c5-b", WORK / "rm06_05b")
        cfg = write_cfg(case2, web_port=app.free_port(), request_timeout_s=8)
        p2 = start_product(cfg, case2)
        stub = HrStub(endpoint_port_from_log(case2))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"
        taken = stub.drain(3.0)
        assert any(t.get("kind") == "page" for t in taken), "没收到 page 任务(前置链路断)"
        # ---- 不回传, 等 request_timeout(8S)过: 波必须自己收场(锁释放), 而不是永久挂住
        wait_until(lambda: "超时" in log_text(case2), 25, "25s 内日志无取数超时记录(request_timeout 未生效或未记账)")
        # ---- 锁最终释放: 下一波还能收到任务(request_timeout 存在的意义)
        code, r = stub.force()
        assert code == 200, f"第二波 force 失败: {code} {r}"
        seen2 = wait_until(lambda: stub.drain(2.0) or None, 30, "超时后下一波收不到任务(站点锁被永久持住)")
        assert any(t.get("kind") == "page" for t in seen2), f"第二波任务异常: {seen2}"
        # ---- 中断计入波次历史(分档可见)
        code, hist = web_req(_web_port_of(cfg), "GET", "/api/hr/history")
        assert code == 200, f"history 应 200: {code}"
        blob = json.dumps(hist, ensure_ascii=False)
        assert ("超时" in blob) or ("no-channel" in blob) or ("error" in blob), \
            f"history 无超时/中断分档痕迹: {blob[:400]}"
        assert_no_crash(case2)
        assert_zero_external(case2)
    finally:
        if p2 is not None:
            p2.stop()
        keep_log(case2)
        rm_all_fakes_with_sweep(qbfake(), "rm06c5b")
        cleanup_rm06_defs(qbfake())
        purge_tree(case2)


# ================================================================ RM06-06


def test_rm06_06_rate_limit_interval_and_daily_quota():
    """[RM06-06] 频控: min_interval 间隔兑现 + max_requests_per_day 日额截断 + status 配额回读(负向内建)

    前置: 基座 + 1 假种子; min_interval=5S(可观测下限) + max_requests_per_day=3(日额刻意配小:
          A 页 + 601 身份下载 + B 页恰好耗尽, C 档被截断 —— 「第 3 波之后拿不到任务」的对照面);
          波次由启动 auto 波 + force 驱动; 日窗重置不在本条断言面。
    副作用: 1 假种子; 频控账本写临时 data_dir。
    回滚: real.seed.rm --all + 删临时目录。
    失败判据: 相邻任务间隔 < min_interval(频控失效, 高优); 日额 3 用尽后 C 档仍派发任务(限额失效 ——
              对照必须红); status 配额数字与实际发出数不符(账实分叉); 下一波 force 照常下发(日额闸漏)。
    """
    case = case_dir("rm06_06")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        name = "rm06c6beta marker show"
        ih, raw = fake_seed(qb, name, "rm06c6-a", WORK / "rm06_06")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp, min_interval_s=5, max_requests_per_day=3)
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"

        hit_html = hr_helpers.myhr_page([hr_helpers.row(601, name)])
        empty_html = hr_helpers.myhr_page([])
        foreign = hr_helpers.torrent_blob(name=name)  # 601 绑到非本地 infohash, 不牵动判定面
        stub.drive(page_answer({"A": hit_html, "B": empty_html, "C": empty_html}, {601: foreign}), max_seconds=60)
        # ---- 第一波: 请求预算 = A 页(#1) + 601 身份下载(#2) + B 页(#3), C 档被日额截断
        times_a = stub.page_task_times("A")
        times_b = stub.page_task_times("B")
        times_c = stub.page_task_times("C")
        assert len(times_a) == 1 and len(times_b) == 1, \
            f"第一波页面任务数异常(A={len(times_a)}, B={len(times_b)}): 日额/档位逻辑分叉"
        assert not times_c, "对照红验失效: 日额 3 用尽后 C 档仍派发了任务(限额失效)"
        assert 601 in stub.torrent_tids(), "第一波缺 601 身份下载任务(预算消耗序列断)"
        gap = times_b[0] - times_a[0]
        # 实测间隔恒 >= min_interval(抖动只向上, ratelimit.JITTER_RATIO); 0.6s 为两次轮询观测误差
        assert gap >= 5.0 - 0.6, f"相邻页面任务间隔 {gap:.2f}s < min_interval 5s(频控失效, 高优)"

        # ---- QuotaStatus 经 /api/hr/status 回读: 日额耗尽(账实一致: 恰好 3 次请求)
        st = hr_status(wp)
        quota = (site_of_status(st).get("quota") or {})
        assert quota.get("day_max") == 3 and quota.get("day") == 3 and quota.get("left") == 0, \
            f"status 配额回读与实际发出数不符: {quota}"
        # 波内截断注记进历史(「档位 C 配额/间隔受限」)
        code, hist = web_req(wp, "GET", "/api/hr/history")
        blob = json.dumps(hist, ensure_ascii=False)
        assert ("受限" in blob) or ("日额" in blob), f"history 无配额/间隔受限注记: {blob[:400]}"

        # ---- 下一波 force: 日额闸仍在 —— 一个任务都拿不到(defer, 不是再发 3 个)
        code, r = stub.force()
        assert code == 200, f"第二波 force 失败: {code} {r}"
        extra = stub.drain(10.0)
        assert not extra, f"对照红验失效: 日额耗尽后下一波仍下发任务: {extra}"
        code, hist2 = web_req(wp, "GET", "/api/hr/history")
        blob2 = json.dumps(hist2, ensure_ascii=False)
        assert "日配额" in blob2 or "未到可取时刻" in blob2, f"第二波 defer 未记入历史: {blob2[:400]}"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c6")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


# ================================================================ RM06-07


def test_rm06_07_exclude_table_dynamic_switch():
    """[RM06-07] HR 排除表: 命中种子出对象集+不打标+动态开关生效, 对照种子照常(对照内建)

    前置: 全局 hr 段 exclude_tags: ["rm06-excl"]; 两枚假种子: 甲预打 rm06-excl, 乙不带;
          C 档行 602 名匹配乙(受管 ⇒ 驱动身份下载)、603 名匹配甲(排除 ⇒ 不得驱动)。
          「驱动任务」观测面 = 身份下载任务按 tid 计(页面任务是站点级的, 与单种子无关 ——
          _row_looks_local 候选面只含受管种子名, service.py:987, issue 26-10-08-1304)。
    副作用: 2 假种子; 乙被打 rm06-hr; 标签 rm06-excl 增删。
    回滚: real.seed.rm --all + 清 rm06-* 标签与定义 + 删临时目录。
    失败判据: 甲被驱动下载任务或被打标(排除优先级失效, 高优); 乙加排除标签后 602 仍被驱动(「现算、
              下一轮生效」失效, 对照必须红); 删标签后 602 永远不回来(恢复面断); 排除模式误匹配
              real-fake(模式过宽, 红线级立即停手)。
    """
    case = case_dir("rm06_07")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        excl_name = "rm06c7 alpha excluded one"  # 甲: 预打 rm06-excl
        hit_name = "rm06c7beta marker show"  # 乙: 不带排除标签
        ih_excl, _ = fake_seed(qb, excl_name, "rm06c7-a", WORK / "rm06_07")
        qb.add_tags(ih_excl, EXCL_TAG)  # 甲预打排除标签(409 已由 _add_retry 删旧重加防御)
        wait_until(lambda: EXCL_TAG in _tags_of(qb.torrent(ih_excl) or {}), 10, "甲预打 rm06-excl 未生效")
        ih_hit, raw_hit = fake_seed(qb, hit_name, "rm06c7-b", WORK / "rm06_07")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp, add_tag=HR_TAG, exclude_tags=[EXCL_TAG])
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))

        hit_html = hr_helpers.myhr_page([hr_helpers.row(601, hit_name)])
        lane_c_html = hr_helpers.myhr_page(
            [
                hr_helpers.row(602, hit_name),  # 匹配乙(受管) ⇒ 应驱动下载
                hr_helpers.row(603, excl_name),  # 匹配甲(排除) ⇒ 绝不驱动下载
            ]
        )
        empty_html = hr_helpers.myhr_page([])

        def answer(t):
            if t.get("kind") == "torrent" and int(t.get("tid") or 0) == 602:
                # 602 故意回「普通失败」(不带 kind!) ⇒ 条目保持未绑定 ⇒ 每波重试, 下载任务成为
                # 「乙是否受管」的逐波信号。!kind="network" 是 KIND_NETWORK ⇒ HrExtensionNetwork
                # 波级让位(整波 no-channel 中止), 不是种子级失败 —— RM06-07 实测踩过。
                return {"ok": False, "status": 0, "error": "stub 故意不回 602 字节(保持未绑定)"}
            return page_answer({"A": hit_html, "B": empty_html, "C": lane_c_html}, {601: raw_hit})(t)

        def force_wave(max_seconds: float = 45.0) -> list[dict]:
            """force + 驱动到波静默(编排口径同 RM06-04: 先 drive 完当前波再 force 下一波,
            12s 静默窗盖过 min_interval 5s ⇒ force 不被 defer; 启动 auto 波锚点可能为空,
            受管名候选面要到锚点同步后才有内容 —— 终态行下载任务以第二波为准)。"""
            code, r = stub.force()
            assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"
            return stub.drive(answer, max_seconds=max_seconds)

        # ---- 波 1(启动 auto 波, 锚点可能尚未同步): A 档行 601 无条件下载; 被排除的甲绝不被驱动
        force_wave(60)
        wait_until(
            lambda: HR_TAG in _tags_of(qb.torrent(ih_hit) or {}), 30,
            f"对照乙未被打 {HR_TAG}(排除表误伤受管种子?): {sorted(_tags_of(qb.torrent(ih_hit) or {}))}"
        )
        tids_1 = stub.torrent_tids()
        assert 601 in tids_1, f"波 1 缺 601 身份下载任务(A 档行无条件): {tids_1}"
        assert 603 not in tids_1, f"对照红验失效: 被排除的甲仍驱动了下载任务(603): {tids_1}"
        tags_excl = _tags_of(qb.torrent(ih_excl) or {})
        assert HR_TAG not in tags_excl, f"对照红验失效: 被排除的甲被打 {HR_TAG}: {sorted(tags_excl)}"

        # ---- 波 2(锚点在场): C 档行 602 名匹配乙(受管) ⇒ 驱动身份下载; 603(甲, 排除)恒不驱动
        mark_1 = stub.mark()
        force_wave(60)
        tids_2 = [int(t.get("tid") or 0) for t in stub.tasks_since(mark_1) if t.get("kind") == "torrent"]
        assert 602 in tids_2, f"波 2 缺 602 下载任务(受管种子名未驱动终态行下载): {tids_2}"
        assert 603 not in tids_2, f"被排除的甲被驱动下载(603): {tids_2}"

        # ---- 动态开关(加): qB API 给乙加 rm06-excl → 下一 force 波 602 不再被驱动(无需重启)
        # !排除态现算自产品 store 快照(sync_interval 1.5S) —— qB API 可见 ≠ 产品已见, 等 4s 再 force
        # (RM06-07 实测: 不等就 force 会拿旧快照, 假红)。
        qb.add_tags(ih_hit, EXCL_TAG)
        wait_until(lambda: EXCL_TAG in _tags_of(qb.torrent(ih_hit) or {}), 10, "乙加 rm06-excl 未生效")
        time.sleep(4)
        mark_2 = stub.mark()
        force_wave()
        tids_3 = [int(t.get("tid") or 0) for t in stub.tasks_since(mark_2) if t.get("kind") == "torrent"]
        assert 602 not in tids_3, \
            f"对照红验失效: 乙加排除标签后 602 仍被驱动下载(「现算、下一轮生效」失效): {tids_3}"
        assert 603 not in tids_3, f"被排除的甲被驱动下载(603): {tids_3}"

        # ---- 动态开关(删): 删掉乙的 rm06-excl → 下一 force 波 602 恢复被驱动(「撤销排除后重新进本循环」)
        qb.remove_tags(ih_hit, EXCL_TAG)
        wait_until(lambda: EXCL_TAG not in _tags_of(qb.torrent(ih_hit) or {}), 10, "乙删 rm06-excl 未生效")
        time.sleep(4)
        mark_3 = stub.mark()
        force_wave()
        tids_4 = [int(t.get("tid") or 0) for t in stub.tasks_since(mark_3) if t.get("kind") == "torrent"]
        assert 602 in tids_4, \
            f"恢复面断: 删除排除标签后乙(602)重新受管, 但不再驱动下载任务: {tids_4}"
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c7")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)


# ================================================================ RM06-08


def test_rm06_08_status_read_face_and_guard():
    """[RM06-08] 站点状态读面: /api/hr/status · entries · history 结构与分档 + HR 未起时前置守卫

    前置: 一份带数据的会话(RM06-03 同款先跑一波); 另一份 hr_check 整段缺省(未启用)的配置。
    副作用: 零 qB 写(只读面); 临时目录。
    回滚: 删临时目录; 无实例残留。
    失败判据: 只读端点改写状态(status/history 必须零写 —— 发现写痕迹即 FAIL); hr 关闭时端点仍按
              已启用响应(守卫失效); status 分档数字与站点文件实况不符(读面账实分叉); history 超 limit。
    """
    case = case_dir("rm06_08")
    p = None
    qb = qbfake()
    try:
        assert not rm_all_fakes_with_sweep(qb, "rm06c"), "开跑前 36596 有 real-fake 残留, 先清场"
        cleanup_rm06_defs(qb)
        name = "rm06c8beta marker show"
        ih, raw = fake_seed(qb, name, "rm06c8-a", WORK / "rm06_08")

        wp = app.free_port()
        cfg = write_cfg(case, web_port=wp, add_tag=HR_TAG)
        p = start_product(cfg, case)
        stub = HrStub(endpoint_port_from_log(case))
        code, r = stub.force()
        assert code == 200 and (r.get("requested") or []), f"force 受理失败: {code} {r}"
        hit_html = hr_helpers.myhr_page([hr_helpers.row(601, name)])
        empty_html = hr_helpers.myhr_page([])
        stub.drive(page_answer({"A": hit_html, "B": empty_html, "C": empty_html}, {601: raw}), max_seconds=60)
        wait_until(lambda: site_index(case).get(601), 20, "index 未出现 601(前置数据)")

        # ---- /api/hr/status: 结构字段(站点聚合: lane 计数/配额/通道状态)
        st = hr_status(wp)
        assert st.get("enabled") is True, f"status enabled 应 true: {st.get('enabled')}"
        s0 = site_of_status(st)
        for key in ("lane_counts", "quota", "index_total", "channel_state", "lanes", "idle_mode"):
            assert key in s0, f"status 缺字段 {key}: {list(s0)}"
        assert (s0["lane_counts"] or {}).get("A", 0) >= 1, f"lane_counts 与站点文件实况不符: {s0['lane_counts']}"
        assert s0["index_total"] >= 1, f"index_total 与站点文件实况不符: {s0['index_total']}"
        chan = st.get("channel") or {}
        assert chan.get("listening") is True and chan.get("port"), f"通道状态缺监听事实: {chan}"
        assert chan.get("enabled") is True, f"通道 enabled 应 true: {chan}"

        # ---- /api/hr/sites/<site>/entries: 条目明细(档位/做种要求文本)
        code, entries = web_req(wp, "GET", f"/api/hr/sites/{SITE_KEY}/entries")
        assert code == 200, f"entries 应 200: {code}"
        rows = entries.get("entries") or []
        assert rows, f"entries 无行: {entries}"
        r0 = rows[0]
        for key in ("lane", "need_seed_text", "local_present", "infohash_v1"):
            assert key in r0, f"entries 行缺字段 {key}: {list(r0)}"
        assert r0["local_present"] is True, f"条目应绑定本地种子: {r0}"

        # ---- /api/hr/history: 行结构 + limit 生效
        code, hist = web_req(wp, "GET", "/api/hr/history?limit=2")
        assert code == 200, f"history 应 200: {code}"
        rows_h = hist.get("rows") or []
        assert len(rows_h) <= 2, f"history limit=2 仍返回 {len(rows_h)} 行(截断失效)"
        assert rows_h, "history 无行(波次历史未记账)"
        # 只读面: 连读 status 不改变站点文件 revision(读面零写痕)
        rev0 = site_file(case).get("revision")
        hr_status(wp)
        hr_status(wp)
        assert site_file(case).get("revision") == rev0, "只读端点改写了站点文件(读面有写痕, FAIL)"

        # ---- HR 未起(整段缺省)的另一份配置: 守卫拒绝(状态码 + 文案), 且零取数痕迹
        case2 = case_dir("rm06_08_off")
        try:
            wp2 = app.free_port()
            cfg2 = write_cfg(case2, web_port=wp2, hr_check_enabled=False)
            p2 = app.start(cfg2, case2)
            try:
                assert p2.wait_log("启动 qB 管理器", 40), f"产品没起来:\n{p2.log()[-600:]}"
                assert p2.wait_log("WEB UI 已启动", 40), f"WEB UI 没起来:\n{p2.log()[-600:]}"
                code, off = web_req(wp2, "GET", "/api/hr/status")
                assert code == 200 and off.get("enabled") is False, f"hr 关闭时 status 应回空态: {code} {off}"
                assert "未启用" in str(off.get("note", "")), f"空态 note 缺人话说明: {off}"
                code, e1 = web_req(wp2, "GET", f"/api/hr/sites/{SITE_KEY}/entries")
                assert code == 400 and "未启用" in str(e1), f"entries 守卫应 400: {code} {e1}"
                code, e2 = web_req(wp2, "GET", "/api/hr/history")
                assert code == 400 and "未启用" in str(e2), f"history 守卫应 400: {code} {e2}"
                code, e3 = web_req(wp2, "POST", "/api/hr/refresh", {"site": SITE_KEY})
                assert code in (400, 409), f"refresh 守卫应 400/409: {code} {e3}"
                off_log = log_text(case2)
                assert "HR 取数通道端点已启动" not in off_log, "hr 关闭时端点仍启动了(零取数痕迹破)"
            finally:
                p2.stop()
                keep_log(case2)
        finally:
            purge_tree(case2)
        assert_zero_external(case)
    finally:
        if p is not None:
            p.stop()
        keep_log(case)
        rm_all_fakes_with_sweep(qbfake(), "rm06c8")
        cleanup_rm06_defs(qbfake())
        purge_tree(case)
