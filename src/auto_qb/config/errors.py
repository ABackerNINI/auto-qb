"""配置错误异常: 文件读取失败/YAML 解析失败/校验失败/启动期规则 spec 错误的统一载体"""


class ConfigError(ValueError):
    """配置错误(文件读取失败/YAML 解析失败/校验失败/启动期规则 spec 错误)

    继承 ValueError 以兼容既有 except ValueError 调用方; CLI 层捕获本异常输出干净
    错误信息(无堆栈)并以非零码退出, 其它类型异常(程序 bug)不在此列, 照常抛出。
    """
