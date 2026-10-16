"""自启: 三平台幂等注册/卸载 (S0 骨架, 实现在 S5).

  Windows  schtasks /SC ONLOGON (当前用户, TR 指向本工具 venv python)
  Linux    ~/.config/systemd/user/gtm.service + systemctl --user enable --now
  macOS    ~/Library/LaunchAgents/ plist + launchctl bootstrap

幂等: 注册前检查存在则跳过, 卸载反向; 先探测平台再执行, 不支持的平台给出
明确提示。由 auto-qb WebUI 设置页开关调用, 也可命令行 gtm install-autostart
直接跑 (S5 随 CLI 一起落地)。
"""

# S0 骨架: 未实现。S5 落地平台探测与幂等注册。
