"""
Version: v1.0.0
Author: AI Assistant + User
Date: 2024-12-20
Dependencies: None
"""

"""
DAG存储管理模块

```mermaid
graph TD
    A[DAG存储管理] --> B[ExecutionStateManager执行状态管理]
    A --> C[DAGDataStorage数据存储]
    A --> D[VersionControl版本控制]
    A --> E[StateRecovery状态恢复]
    
    B --> B1[节点状态管理]
    B --> B2[执行历史记录]
    B --> B3[状态验证]
    
    C --> C1[JSON格式存储]
    C --> C2[备份管理]
    C --> C3[数据压缩]
    
    D --> D1[版本创建]
    D --> D2[版本比较]
    D --> D3[版本回滚]
    
    E --> E1[检查点创建]
    E --> E2[状态恢复]
    E --> E3[数据一致性检查]
```

本模块提供4层DAG执行状态的持久化存储和管理功能。

核心组件：
- ExecutionStateManager: 执行状态管理器
- DAGDataStorage: DAG数据存储管理器
- VersionControl: 版本控制管理器
- StateRecovery: 状态恢复管理器
"""

from .execution_state_manager import ExecutionStateManager
from .dag_data_storage import DAGDataStorage
from .version_control import VersionControl
from .state_recovery import StateRecovery

__all__ = [
    'ExecutionStateManager',
    'DAGDataStorage', 
    'VersionControl',
    'StateRecovery'
] 