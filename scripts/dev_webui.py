"""一键起一个**只开 WEB UI**的 auto-qb, 连真机 qBittorrent 用来看界面/试交互

为什么单开一个脚本:
    平时跑 auto-qb 会带上规则、标签/分类维护、辅种分组、跳检备份等一堆自动任务。
    想"连真机看一眼界面"时, 这些自动任务会**真的去改 qB 里的种子**(打标签/改分类/
    删文件), 不该在这种场景发生。本脚本生成一份**最小配置**: 关掉所有带开关的自动行为,
    只留「同步快照 + WEB UI」, 数据目录独立(不碰仓库里的 auto-qb-data)。

用法:
    uv run python scripts/dev_webui.py --qb-port 8080 --qb-user admin --qb-password x
    uv run python scripts/dev_webui.py --qb-host 192.168.1.10 --qb-port 8080 --web-port 8177

    # 不自动开浏览器(比如已经开着 / 在远程桌面里)
    uv run python scripts/dev_webui.py --qb-port 8080 --no-open

⚠⚠ **必须知道的两件事**:
    1. **WebUI 上的手动命令会真的作用到 qB** —— 点"暂停"就是真暂停种子。
       这是测试乐观 UI 的前提(要有真的状态变化), 但也意味着别在正在做种的关键机上乱点。
    2. **`dry_run` 不能用** —— 项目里 `if not dry_run and web.enabled` 才起 WEB 服务,
       开 dry_run 等于连界面都没有。所以"关功能"是靠配置把所有自动任务关掉, 不是靠 dry_run。

    仍可能写 qB 的残留路径: 辅种分组(`config.grouping`)在归组时可能写分类/标签 ——
    本脚本已把 `check_missing_files` 关掉并把 `missing_tag` 置空, 但仍**建议**先在不重要的
    qB 上跑一次, 确认没有意外写入再长期用。
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import threading
import time
import webbrowser

CONFIG_TMPL = """---
# 由 scripts/dev_webui.py 生成 —— 最小配置: 关掉所有自动任务, 只开 WEB UI
config:
    # 任务间隔拉到 1 天: 种子级内置功能/规则等任务在这段会话里基本不会被触发
    interval: 86400S
    main_tick: {main_tick}S
    # 同步间隔保持 1.5s: 界面数据新鲜度靠它(与 qB 自带 WebUI 同量级)
    sync_interval: 1.5S
    max_tasks_per_tick: 20
    state_file: "{state_file}"
    # ---- 关掉的自动行为 ----
    remove_similar_tags: false
    skip_checking_tag: zSkipChecked
    add_episode_tags:
        enabled: false          # 不给种子补集数标签
    delete_tags: []             # 不做全局标签清理
    # ❗规则集: 不写任何 `*_rules` 段即可 —— 规则是按键名 `_rules` 结尾自动发现的,
    #   没有这样的键 = 没有规则 ⇒ 不会自动删种/改限速/打 HR 标签。(写成 rules_config: {{}}
    #   反而会被 validate_config 判"未知键", 已实测)
    hr:
        add_tag: ""
        add_category: ""
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: ""
        overwrite_category_for_satisfied: false
    grouping:
        enabled: true           # 保留: 辅种页/追剧页要它才能出视图(只读归组)
        missing_tag: ""         # 置空 => 不写 MISSING 标签
        check_missing_files: false  # 不做缺文件扫描(它会写标签)
    qbittorrent:
        host: "{qb_host}"
        port: "{qb_port}"
        username: "{qb_user}"
        password: "{qb_password}"
    log:
        level: INFO
        file: "{log_file}"
        max_bytes: 50MiB
    web:
        enabled: true
        host: "{web_host}"
        port: {web_port}
        token: ""               # 留空 => 首次启动随机生成并持久化到 data_dir/web.token
        skip_local_verify: true # 本机回环免密钥(浏览器直接开, 不用输 token)
    # trackers 留空: 不按站点打标签/不改分类(这也是"关掉自动行为"的一部分)
    trackers: {{}}
"""


def _port_listening(host: str, port: int, timeout: float = 0.6) -> bool:
    """该端口上是否已有服务在听(用于: qB 连不上要早失败 / WEB 端口被占要换一个)"""
    import socket

    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_web_port(host: str, want: int, tries: int = 20) -> int:
    """端口被占就往上找一个空的 —— 一键脚本不该让用户自己去查是谁占了

    常见成因: 上一次 dev_webui 没退干净(进程还在), 或这个端口本来就有别的服务。
    """
    if not _port_listening(host, want):
        return want
    for p in range(want + 1, want + 1 + tries):
        if not _port_listening(host, p):
            return p
    return want  # 都不行就交回原值, 让后端报它自己的错(语义不变)


def main() -> int:
    ap = argparse.ArgumentParser(description="连真机 qBittorrent, 关掉所有自动任务, 只开 WEB UI")
    ap.add_argument("--qb-host", default="127.0.0.1", help="qBittorrent WebUI 地址(默认 127.0.0.1)")
    ap.add_argument("--qb-port", default="8080", help="qBittorrent WebUI 端口(默认 8080)")
    ap.add_argument("--qb-user", default="", help="qB 用户名(默认空)")
    ap.add_argument("--qb-password", default="", help="qB 密码(默认空)")
    ap.add_argument("--web-host", default="127.0.0.1", help="WEB UI 监听地址(默认 127.0.0.1)")
    ap.add_argument("--web-port", type=int, default=8177, help="WEB UI 端口(默认 8177, 避开常用端口)")
    ap.add_argument("--main-tick", type=float, default=2.0, help="主循环间隔(秒, 默认 2)")
    ap.add_argument("--data-dir", default="", help="运行时数据目录(默认系统临时目录下的一个子目录)")
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()

    # ---- 启动前自检: 两条都是"启动后才炸、还得读栈"的典型, 提前拦掉 ----
    # ① qB 端口不通 => 直接退出并给出排查清单(否则要等 Web 起来、主循环连一轮才知道)
    if not _port_listening(args.qb_host, args.qb_port):
        print(f"\n[失败] 连不上 qBittorrent: {args.qb_host}:{args.qb_port} 没有服务在听\n")
        print("  请依次确认:")
        print("    1. qBittorrent 正在运行")
        print("    2. 设置 → Web UI → 已勾选「启用 Web 用户界面」")
        print("    3. 端口对: qB 里显示的端口才是端口(默认 8080, 不一定是它)")
        print(f"       改端口: --qb-port <qB 里那个端口>")
        print("    4. 若 qB 只监听了具体网卡, 用 --qb-host 指定那个地址")
        return 2
    # ② WEB 端口被占 => 自动换一个(实测: 上一次进程没退干净最常见)
    web_port = args.web_port
    if _port_listening(args.web_host, web_port):
        alt = _pick_web_port(args.web_host, web_port)
        print(f"[提示] WEB 端口 {args.web_host}:{web_port} 已被占用(多为上一次没退干净的进程)")
        if alt != web_port:
            print(f"       自动改用 {alt}\n")
            web_port = alt
        else:
            print("       附近也没找到空端口, 仍按原端口启动(失败信息以后端为准)\n")

    if args.data_dir:
        data_dir = os.path.abspath(args.data_dir)
    else:
        data_dir = os.path.join(tempfile.gettempdir(), "auto-qb-dev-webui")
    os.makedirs(data_dir, exist_ok=True)

    cfg_path = os.path.join(data_dir, "config.yml")
    text = CONFIG_TMPL.format(
        main_tick=args.main_tick,
        state_file=os.path.join(data_dir, "state.json").replace("\\", "/"),
        log_file=os.path.join(data_dir, "auto-qb.log").replace("\\", "/"),
        qb_host=args.qb_host,
        qb_port=args.qb_port,
        qb_user=args.qb_user,
        qb_password=args.qb_password,
        web_host=args.web_host,
        web_port=web_port,
    )
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(text)

    url = f"http://{args.web_host}:{web_port}/atlas/"
    print("=" * 68)
    print("auto-qb · 最小配置 · 只开 WEB UI")
    print("=" * 68)
    print(f"  qB      : {args.qb_host}:{args.qb_port}")
    print(f"  WEB UI  : {url}   (prism: .../prism/)")
    print(f"  配置     : {cfg_path}")
    print(f"  数据目录 : {data_dir}")
    print(f"  日志     : {os.path.join(data_dir, 'auto-qb.log')}")
    print()
    print("  已关闭: 规则集(HR/限速/删种) / 集数标签 / 标签清理 / 缺文件扫描 / 站点标签")
    print("  已保留: 同步快照(1.5s) + 辅种分组(只读归组) + WEB UI")
    print()
    print("  ⚠ WebUI 上的**手动**命令会真的作用到 qB(点暂停就是真暂停)。")
    print("  ⚠ 别在正在做种的关键机上乱点。Ctrl+C 退出。")
    print("=" * 68)

    if not args.no_open:
        # 等服务起来再开浏览器(run() 内部起 web 服务, 这里只做一次延迟打开)
        threading.Thread(target=lambda: (time.sleep(4.0), webbrowser.open(url)), daemon=True).start()

    # 交给正式 CLI: 与 `python -m auto_qb <config>` 完全等价(含单实例锁/托盘/日志初始化)
    sys.argv = ["auto-qb", cfg_path]
    from auto_qb.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
