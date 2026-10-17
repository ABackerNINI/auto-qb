@echo off
rem 由 gtm 工具侧维护的启动器 (计划 26-10-17-0339 / D19) —— 工具侧唯一知道「怎么起」的地方。
rem auto-qb 只做「找本文件 -> detached 执行」, 不认识 uv / 入口名 / 子命令; 工具升级换命令
rem 形态只改本文件, auto-qb 零改动。
rem 恒定携带自启意图 (--autostart): 是否真注册由工具 config autostart 唯一裁决 (用户关过不被装回)。
rem 不传 --data-dir: 数据落点由工具自解析 (被拉起/自启时 PWD 不可信)。
rem 优先工具自带 venv 解释器 (装依赖时已建); 缺失才兜底 uv。
rem 编译态: 本文件内容退化为调用同目录的可执行文件 (由打包流程生成, 不在此维护)。
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m gtm run --autostart
) else (
    uv run --project "%~dp0." global-traffic-monitor run --autostart
)
