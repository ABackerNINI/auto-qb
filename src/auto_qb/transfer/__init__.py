"""种子转移执行层(计划 26-10-31-0306 §03/§04 W2)

「导出 -> 字段映射 -> 目标添加 -> 验证 -> 删源」移动管线的执行层落点。

- adapters/: DownloaderAdapter 协议 + 注册表(D10)+ qb 实现 + tr stub(T2)
- orchestrator: 串行逐种子编排 —— 状态门/导出/映射/添加/验证/删源/失败分类(T3);
  结果结构单点 TorrentTransferResult(状态三态 TransferStatus + 分类 TransferOutcomeCode)

设计底线(不变量, 违反即错, 计划 §01): 数据文件永不移动/永不删除; 任何不成功路径
不碰源; 未完成种子绝不以跳检形式添加; 凭据只从服务端出网。
"""
from .adapters import (  # noqa: F401 —— 调用方单点导入 re-export
    AddResult,
    AddStatus,
    DownloaderAdapter,
    TransferAdapterError,
    UnknownAdapterTypeError,
    adapter_type_known,
    create_adapter,
)
from .orchestrator import (  # noqa: F401
    TorrentTransferResult,
    TransferOutcomeCode,
    TransferOrchestrator,
    TransferStatus,
)
