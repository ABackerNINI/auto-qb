"""auto_qb 致命错误根: CLI 单点捕获 (stderr 干净输出 + 退出码 1, 无堆栈)"""


class AutoQbError(Exception):
    """auto-qb 致命错误基类

    子类按错误类别并列:
    - ConfigError (config/errors.py): 配置文件读取/YAML 解析/校验失败/启动期规则 spec 错误
    - SingleInstanceLockError (locking.py): 单实例锁竞争/锁文件错误
    - QbCompatError (torrents.py): qBittorrent torrent info 字段与预期不符(版本不兼容)

    其它异常(程序 bug)不在此列, 照常抛出保留堆栈。
    """
