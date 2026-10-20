#!/bin/sh
# 由 gtm 工具侧维护的 claim 启动器 (计划 26-10-20-1316 §03 / D4) —— 人工易主唯一通道。
# 零参数契约 (D19 同族): 意图 (python -m gtm claim) 写在脚本内容里, auto-qb 只做
# 「找本文件 -> /bin/sh <脚本> 有界前台执行」(不依赖 exec 位), 不认识 uv / 入口名 /
# 子命令; 形态升级只改本文件。
# 与 launch.sh 的分工: launch 起服务 (恒定带 --autostart), claim 只动正主记录
# (护栏在工具侧: 运行中拒绝 / 数据归属异拒绝)。缺本文件 = 旧安装, 提示升级。
# 编译态: 本文件内容退化为调用同目录的可执行文件 (由打包流程生成, 不在此维护)。
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$HERE/.venv/bin/python" ]; then
    exec "$HERE/.venv/bin/python" -m gtm claim
else
    exec uv run --project "$HERE" global-traffic-monitor claim
fi
