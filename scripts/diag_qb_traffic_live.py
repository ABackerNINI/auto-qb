"""Interactive live traffic stub for x-axis/grid jitter retest (issue 26-11-17-0936).

Why a separate script
---------------------
The e2e harness (scripts/ui_harness.py) keeps qb_traffic disabled and has no
v4 traffic files, so /api/traffic/qb/global returns an empty payload and the
status-bar entry is hidden. This stub reuses the SAME production app assembly
(create_app + real QbManager + FakeClient + synthetic torrents) but adds:

  1. qb_traffic enabled, main_tick = 1.5s, multiplier = 1
     -> sample interval 1.5s; 1m window grid = 41 buckets at 1.5s (the exact
        geometry where the two-beat ulp grid jump was captured).
  2. a synthetic "today" traffic period so the status-bar qB entry renders
     (qbHistEntryOn = qb_traffic_enabled AND todayTraffic).
  3. a monkey-patch of QbTrafficChartApi.payload_global that recomputes the
     grid from the REAL wall-clock build_grid on every poll and fills it with
     deterministic synthetic values. xs0 therefore advances exactly as in
     production, so the L0 end-frame ulp boundary condition is reproducible.

The patch is process-local only: no production source or e2e harness is edited.

Usage
-----
    uv run python scripts/diag_qb_traffic_live.py            # default port 8391
    uv run python scripts/diag_qb_traffic_live.py --port 8392

Open http://127.0.0.1:8391/prism/ (or /atlas/), click the qB chart button in
the status bar (or press Ctrl+backslash), then switch the window tab to 1m.
Watch the bottom tick labels + vertical grid lines for the two-beat jump.
Paste scripts/diag_xaxis_grid_probe.js into the DevTools console to auto-capture.

Binds loopback only (the app disables local auth in this stub).
"""
import argparse
import atexit
import os
import shutil
import socket
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
for _p in (ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "tests", "unit"), HERE):
    sys.path.insert(0, _p)

from auto_qb.config import WebConfig  # noqa: E402
from auto_qb.config.models import QbTraffic  # noqa: E402
from auto_qb.webui import create_app  # noqa: E402
from auto_qb.webui.server.traffic_qb import QbTrafficChartApi  # noqa: E402
from tests.unit.helpers import FakeClient, make_manager, seed_store  # noqa: E402
import ui_harness as H  # noqa: E402

SAMPLE_S = 1.5


def _live_payload_global(self, window: str) -> dict:
    """Recompute the grid from the real wall clock every poll and fill synthetic values.

    self._grid() calls the production build_grid(window, now, sample_interval),
    so bucket timestamps advance with the exact same float-anchor geometry as
    the real backend. The frontend reconstructs xs from points[0].t + interval,
    giving the same L0 end-frame ulp boundary that produced the jump.
    """
    grid = self._grid(window)
    pts = []
    totals = []
    for i, t in enumerate(grid.buckets):
        base = 4_000_000 + ((i * 37) % 211) * 9000
        row = {"t": float(t), "up": base, "dl": int(base * 0.63)}
        pts.append(row)
        totals.append(dict(row))
    return {
        "points": pts,
        "totals": totals,
        "limits": [],
        "meta": self._meta(grid, stale=False),
    }


# Process-local patch. All three routers construct their own QbTrafficChartApi
# instance, but patching the class method covers every instance.
QbTrafficChartApi.payload_global = _live_payload_global


def _is_loopback(host: str) -> bool:
    import ipaddress
    # No DNS/hosts resolution: only the IPv6 loopback literal or an IP literal
    # that ipaddress proves is loopback. "localhost" is deliberately NOT trusted
    # (a tampered hosts file could resolve it to a routable address).
    if host == "::1":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="live qB global traffic stub for jitter retest")
    ap.add_argument("--host", default="127.0.0.1", help="loopback only")
    ap.add_argument("--port", type=int, default=8391, help="listen port (default 8391)")
    ap.add_argument("--torrents", type=int, default=30, help="synthetic torrent count (page needs a few)")
    args = ap.parse_args()

    if not _is_loopback(args.host):
        print(f"[live-traffic] refuse: --host must be loopback, got {args.host!r}", file=sys.stderr)
        return 2

    family = socket.AF_INET6 if ":" in args.host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.bind((args.host, args.port))
    except OSError as exc:
        print(f"[live-traffic] bind failed {args.host}:{args.port} ({exc}); pick another --port", file=sys.stderr)
        sock.close()
        return 2
    actual = sock.getsockname()[1]

    tmp = tempfile.mkdtemp(prefix="aqb-live-traffic-")
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    mgr = make_manager(os.path.join(tmp, "state.json"))
    mgr.client = FakeClient()
    mgr.config.web = WebConfig(
        enabled=True,
        host=args.host,
        port=actual,
        token="",
        skip_local_verify=True,
        skip_check_menu=True,
    )
    mgr._last_conn_ok = True

    # 1.5s sample interval: 1m window -> interval 1.5s, n = 41 (the jitter geometry).
    mgr.config.main_tick = SAMPLE_S
    mgr.config.qb_traffic = QbTraffic(
        enabled=True,
        sample_interval_multiplier=1,
        flush_interval=600.0,
        raw_window=86400.0,
        rollup_window=2592000.0,
    )
    mgr.config_path = os.path.join(tmp, "config.yml")
    mgr.config.data_dir = tmp
    H._materialize_config(mgr.config_path, actual, True)

    site_conf = mgr.config.trackers["HHan"]
    torrents = H._make_torrents(args.torrents, site_conf)
    H._inject_hr_category(torrents, site_conf)
    seed_store(mgr, torrents)
    for tor in torrents:
        mgr.client.torrents[tor.hash] = tor
    mgr.store.apply_sync(mgr.api)
    H._inject_add_options(mgr, torrents)
    mgr.web.rebuild_views()

    # 2. Make qbHistEntryOn true: status-bar entry needs qb_traffic_enabled AND
    #    todayTraffic (a "day" period row). Nothing publishes traffic_view in
    #    the stub, so inject the row directly.
    mgr.web.traffic_view["state"] = "ok"
    mgr.web.traffic_view["periods"] = [
        {
            "period": "day",
            "label": "today",
            "up": 123_456_789,
            "down": 98_765_432
        },
    ]

    app = create_app(mgr)
    print(
        f"[live-traffic] http://127.0.0.1:{actual}/prism/  /atlas/  "
        f"sample={SAMPLE_S}s window=1m(41 buckets) qb_traffic=on",
        flush=True,
    )
    print(
        "[live-traffic] open the qB chart button in the status bar (or Ctrl+\\), switch to 1m, watch the grid.",
        flush=True
    )

    import uvicorn
    uv_config = uvicorn.Config(app, host=args.host, port=actual, log_level="warning")
    try:
        uvicorn.Server(uv_config).run(sockets=[sock])
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
