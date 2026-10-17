@echo off
rem 由 gtm 工具侧维护的启动器 (计划 26-10-17-0339 / D19) —— 工具侧唯一知道「怎么起」的地方。
rem auto-qb 只做「找本文件 -> detached 执行」, 不认识 uv / 入口名 / 子命令; 工具升级换命令
rem 形态只改本文件, auto-qb 零改动。
rem 恒定携带自启意图 (--autostart): 是否真注册由工具 config autostart 唯一裁决 (用户关过不被装回)。
rem 不传 --data-dir: 数据落点由工具自解析 (被拉起/自启时 PWD 不可信)。
rem 优先工具自带 venv 的 **pythonw.exe** (26-10-17-1737 S5/D7): 它属 GUI 子系统, 由它起的进程
rem 不会弹控制台 —— 这是「去黑框」的第二道保险 (第一道是 auto-qb 侧 CREATE_NO_WINDOW);
rem 直接双击本文件 / 自启拉起时也靠它。缺 pythonw 时退回 python.exe, 再兜底 uv。
rem 排障提示: pythonw 没有 stderr, 输出全部丢弃; 要看日志就把下面的 pythonw 临时换成 python.exe。
setlocal
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    "%~dp0.venv\Scripts\pythonw.exe" -m gtm run --autostart
) else if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m gtm run --autostart
) else (
    uv run --project "%~dp0." global-traffic-monitor run --autostart
)
