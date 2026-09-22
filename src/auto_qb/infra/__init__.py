"""auto_qb 基础设施包（infra）

由根目录平铺文件归拢而来（plan 26-09-22-2112 · 方案 C · W4a）:
- errors.py    AutoQbError 错误根（CLI 单点捕获）+ ConfigError / SingleInstanceLockError / QbCompatError
- locking.py   单实例锁（filelock + 伴生 meta.json）
- logging.py   日志配置（控制台 + RotatingFileHandler；⚠ 与 stdlib logging 同名，包内一律相对导入）
- utils.py     通用工具（解析/匹配/路径/变量替换）
- notify.py    主动通知（WinRT toast / notify-send / osascript，零第三方依赖）
- autostart.py 开机自启（HKCU Run / XDG autostart / LaunchAgents）

依赖纪律: infra 只被依赖 —— 不 import core / 表现层 / config（见计划 §04 依赖方向表）。
本包内部互引用一层相对导入（from .errors / from .utils），包目录再调整时零改动。
"""
