@echo off
rem 由 gtm 工具侧维护的 claim 启动器 (计划 26-10-20-1316 §03 / D4) —— 人工易主唯一通道。
rem 零参数契约 (D19 同族): 意图 (python -m gtm claim) 写在脚本内容里, auto-qb 只做
rem 「找本文件 -> 有界前台执行」, 不认识 uv / 入口名 / 子命令; 形态升级只改本文件。
rem 与 launch.cmd 的分工: launch 起服务 (恒定带 --autostart), claim 只动正主记录
rem (护栏在工具侧: 运行中拒绝 / 数据归属异拒绝)。缺本文件 = 旧安装, 提示升级。
rem 编译态: 本文件内容退化为调用同目录的可执行文件 (由打包流程生成, 不在此维护)。
rem 排障提示: 要看 stderr 输出就把下面的 pythonw 临时换成 python.exe。
setlocal
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    "%~dp0.venv\Scripts\pythonw.exe" -m gtm claim
) else if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m gtm claim
) else (
    uv run --project "%~dp0." global-traffic-monitor claim
)
echo global-traffic-monitor: claim 退出码 %ERRORLEVEL%
exit /b %ERRORLEVEL%
