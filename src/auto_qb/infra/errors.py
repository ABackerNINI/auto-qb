"""auto_qb 致命错误根: CLI 单点捕获 (stderr 干净输出 + 退出码 1, 无堆栈)"""


class AutoQbError(Exception):
    """auto-qb 致命错误基类

    子类按错误类别并列:
    - ConfigError (config/errors.py): 配置文件读取/YAML 解析/校验失败/启动期规则 spec 错误
    - SingleInstanceLockError (locking.py): 单实例锁竞争/锁文件错误
    - QbCompatError (torrents.py): qBittorrent torrent info 字段与预期不符(版本不兼容)

    其它异常(程序 bug)不在此列, 照常抛出保留堆栈。
    """


class SchemaVersionError(AutoQbError):
    """落盘文件 schema 版本问题(比程序新 / 非法值 / 迁移表缺项)

    与「文件内容损坏」区别对待: 版本问题**不做** .bak 回退 —— 备份与主文件同版本,
    回退没有意义(hr/store 的既有判例); 报错说明两个版本号, fail-fast 启动失败。
    所以各读点不得把它折进损坏三态(_CORRUPT), 要直接放出去走 CLI 干净出口。
    """
