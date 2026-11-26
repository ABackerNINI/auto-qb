"""重启后 WebUI 首份数据测量(计划 26-11-18-0259 S0/S3 共用同一口径)。

测什么: 产品 WebUI 的 /api/state 轮询时间线 —— 从 t0(产品进程 spawn)起, 间隔 ≤300ms
轮询 `/api/state?rid=-1`(四视图全量, rid=-1 恒回传当前已发布代), 记录:
  - 首个 HTTP 200 时刻(web 可用)与首个响应的行数(空代判定: torrents==0);
  - flat(torrents)/singles/shows(shows.list)/groups 各视图首份非空数据出现时刻;
  - rid 代际跃迁(空代/基础代发布 → 管线完成后的含归组数据代, 根因链 plan §02.2 直观测证据);
  - 每次 /api/state 采样的行数快照(紧凑存档)。

计时口径(对齐产品日志): 每个采样记两组时间 —— offset_s = 采样**响应完成**时刻相对 t0
(time.monotonic, 无挂钟跳变), epoch = 响应完成的绝对墙钟(time.time); 与产品日志时间戳
逐行对照用 epoch, 相对 t0 的时长用 offset_s。另记每次 fetch 耗时(fetch_s)。

判据对接(plan §02.2/S0): 首份数据出现时刻 ≈ 首轮管线完成时刻 —— 本脚本量前者,
后者由产品日志锚点(检测到新增种子 N 个)与产品日志时间窗对照。

用法(独立可复用; S3 修复后同口径复测):
  uv run python tests/real/tools/measure_boot_first_data.py \
      --url http://127.0.0.1:39101 --out <json 路径> [--interval 0.15] [--timeout 150] \
      [--t0 <unix epoch 秒> --t0-mono <monotonic 秒>] [--token <bearer>]
  t0 缺省 = 本脚本启动时刻; 驱动脚本(run_s0_boot.py)传产品进程 spawn 的双时钟零点。
凭据: 派生配置 skip_local_verify: true 时免鉴权零凭据(真机轨口径, real-machine.md §2.3);
      若复测带 token 的实例, --token 以 Bearer 头携带。
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

# 绕 HTTP_PROXY: 127.0.0.1 不走代理(RM08 同款)
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

VIEWS = ("torrents", "singles", "shows", "groups")  # /api/state 响应键; shows 是 {list, unrecognized}


def row_count(payload: dict, key: str) -> int:
    """视图数组行数(非空判定): list 直取长度; shows 为 {list, unrecognized} 取 list。"""
    v = payload.get(key)
    if v is None:
        return -1  # 键缺席(零回传拍/异常)
    if isinstance(v, dict):
        return len(v.get("list") or [])
    return len(v)


def fetch_once(url: str, token: str = "", timeout: float = 10.0) -> dict:
    req = urllib.request.Request(f"{url}/api/state?rid=-1", method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with _OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_measurement(
    url: str,
    out_path: str,
    *,
    t0_epoch: float | None = None,
    t0_mono: float | None = None,
    interval: float = 0.15,
    timeout: float = 150.0,
    token: str = "",
    fetch_timeout: float = 10.0
) -> dict:
    """轮询直到四视图全部非空(或超时), 返回并落盘 JSON 时间线。

    fetch_timeout: 单次 HTTP 超时秒。探测空代竞态(首请求抢在首轮 apply_sync 落库前)时调短
    (如 0.1)—— connect 挂起到 web bind 的 SYN 重传窗(~1s)会被超时切断, 首个成功请求即可
    落在 web bind 后极早时刻; 默认 10s 时首个请求会被 SYN 重传拖到落库之后(实测)。
    """
    if t0_epoch is None:
        t0_epoch = time.time()
    if t0_mono is None:
        t0_mono = time.monotonic()
    result: dict = {
        "url": url,
        "t0_epoch": t0_epoch,
        "t0_mono": t0_mono,
        "interval_s": interval,
        "timeout_s": timeout,
        "fetch_timeout_s": fetch_timeout,
        "web_up": None,  # {offset_s, epoch, fetch_s}: 首个 200(响应完成时刻)
        "first_response": None,  # 首个 200 响应的行数快照(空代判定)
        "rid_sequence": [],  # [offset_s, epoch, rid] 代际跃迁(响应完成时刻)
        "first_nonempty": {},  # view -> [offset_s, epoch, rows] 首份非空(响应完成时刻)
        "all_nonempty": None,  # [offset_s, epoch]
        "error": None,
        "samples": [],  # [offset_s, epoch, fetch_s, rid, torrents, singles, shows, groups]
    }
    seen_nonempty: set[str] = set()
    last_rid = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        started_mono = time.monotonic()
        try:
            payload = fetch_once(url, token=token, timeout=fetch_timeout)
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(max(0.0, interval - (time.monotonic() - started_mono)))
            continue
        done_mono = time.monotonic()
        off = round(done_mono - t0_mono, 3)
        epoch = round(time.time(), 3)
        fetch_s = round(done_mono - started_mono, 3)
        rid = payload.get("rid")
        counts = {k: row_count(payload, k) for k in VIEWS}
        result["samples"].append(
            [off, epoch, fetch_s, rid, counts["torrents"], counts["singles"], counts["shows"], counts["groups"]]
        )
        if result["web_up"] is None:
            result["web_up"] = {"offset_s": off, "epoch": epoch, "fetch_s": fetch_s}
            result["first_response"] = {k: counts[k] for k in VIEWS}
        if rid != last_rid:
            result["rid_sequence"].append([off, epoch, rid])
            last_rid = rid
        for k in VIEWS:
            if k not in seen_nonempty and counts[k] > 0:
                seen_nonempty.add(k)
                result["first_nonempty"][k] = [off, epoch, counts[k]]
        if len(seen_nonempty) == len(VIEWS):
            result["all_nonempty"] = [off, epoch]
            break
        time.sleep(max(0.0, interval - (time.monotonic() - started_mono)))
    if result["all_nonempty"] is None:
        result["error"] = f"超时({timeout}s)仍有视图未出非空数据: 已见 {sorted(seen_nonempty)}"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    ne = result["first_nonempty"]
    fr = result["first_response"]
    web = result["web_up"]
    print(
        f"[measure] web_up={web['offset_s'] if web else '-'}s "
        f"首响应行数={fr if fr else '(未取得)'} "
        f"首份非空: flat={ne.get('torrents', ['-'])[0]}s singles={ne.get('singles', ['-'])[0]}s "
        f"shows={ne.get('shows', ['-'])[0]}s groups={ne.get('groups', ['-'])[0]}s "
        f"全齐={result['all_nonempty'][0] if result['all_nonempty'] else '-'}s"
    )
    if result["error"]:
        print(f"[measure][红] {result['error']}")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="重启后 WebUI 首份数据时间线测量(S0/S3 共用口径)")
    ap.add_argument("--url", required=True, help="产品 WebUI 地址, 如 http://127.0.0.1:39101")
    ap.add_argument("--out", required=True, help="JSON 时间线输出路径")
    ap.add_argument("--t0", type=float, default=None, help="计时零点(unix epoch 秒), 缺省=脚本启动时刻")
    ap.add_argument("--t0-mono", type=float, default=None, help="计时零点(time.monotonic 秒), 与 --t0 配对")
    ap.add_argument("--interval", type=float, default=0.15, help="轮询间隔秒(≤0.3)")
    ap.add_argument("--timeout", type=float, default=150.0, help="总超时秒")
    ap.add_argument("--token", default="", help="Bearer 令牌(skip_local_verify=true 的派生配置不需要)")
    ap.add_argument("--fetch-timeout", type=float, default=10.0, help="单次 HTTP 超时秒(探测空代竞态用 0.1)")
    args = ap.parse_args(argv)
    result = run_measurement(
        args.url,
        args.out,
        t0_epoch=args.t0,
        t0_mono=args.t0_mono,
        interval=args.interval,
        timeout=args.timeout,
        token=args.token,
        fetch_timeout=args.fetch_timeout,
    )
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
