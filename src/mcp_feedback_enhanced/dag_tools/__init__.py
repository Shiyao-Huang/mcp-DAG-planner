#!/usr/bin/env python3
"""
四层DAG构建工具模块

Version: v1.0.0
Author: AI Assistant + User
Date: 2024-12-20
Purpose: 实现四层DAG循环迭代构建系统的核心工具
Dependencies: FastMCP, Mermaid, graphology, ReactFlow, MCP协议
"""

"""
```mermaid
graph TD
    subgraph "四层DAG构建工具依赖关系"
        A[__init__.py] --> B[four_layer_iterator.py]
        A --> C[dag_validator.py]
        A --> D[mermaid_parser.py]
        A --> E[data_converter.py]
        
        B --> F[Function Layer Builder]
        B --> G[Logic Layer Builder] 
        B --> H[Code Layer Builder]
        B --> I[Order Layer Builder]
        
        C --> J[Mermaid语法验证]
        C --> K[DAG一致性检查]
        C --> L[跨层关系验证]
        
        D --> M[Mermaid解析器]
        D --> N[节点边抽取]
        D --> O[语法树构建]
        
        E --> P[graphology格式]
        E --> Q[ReactFlow格式]
        E --> R[统一数据模型]
    end
    
    subgraph "核心功能"
        F1[build_function_layer_dag<br/>功能层构建]
        F2[build_logic_layer_dag<br/>逻辑层构建]
        F3[build_code_layer_dag<br/>代码层构建]
        F4[build_order_layer_dag<br/>排序层构建]
    end
    
    subgraph "数据流向"
        S1[AI模型] --> S2[Mermaid DAG]
        S2 --> S3[工具接收]
        S3 --> S4[解析验证]
        S4 --> S5[数据转换]
        S5 --> S6[JSON返回]
    end
```
"""

# 重要变量和函数列表
__all__ = [
    # 四层DAG构建函数（在server.py中定义）
    "build_function_layer_dag",
    "build_logic_layer_dag", 
    "build_code_layer_dag",
    "build_order_layer_dag",
    
    # 工具版本信息
    "__version__",
    "__author__",
    "__purpose__"
]

# 模块元信息
__version__ = "1.0.0"
__author__ = "AI Assistant + User"
__purpose__ = "四层DAG循环迭代构建工具集"

# 四层DAG类型定义
LAYER_TYPES = {
    "function": {
        "name": "功能层 (What Layer)", 
        "description": "业务目标和功能需求层",
        "focus": ["业务功能识别", "功能模块依赖", "需求映射", "优先级评估"]
    },
    "logic": {
        "name": "逻辑层 (How Layer)",
        "description": "技术架构和系统设计层", 
        "focus": ["技术架构设计", "系统组件关系", "API接口定义", "数据流控制"]
    },
    "code": {
        "name": "代码层 (Code Layer)",
        "description": "代码实现和模块组织层",
        "focus": ["代码模块结构", "文件组织架构", "类函数设计", "依赖管理"]
    },
    "order": {
        "name": "排序层 (When Layer)", 
        "description": "执行顺序和时序安排层",
        "focus": ["执行顺序规划", "任务依赖关系", "资源分配计划", "时间节点安排"]
    }
}

# DAG构建状态
BUILD_STATES = {
    "PENDING": "等待构建",
    "BUILDING": "构建中", 
    "VALIDATING": "验证中",
    "SUCCESS": "构建成功",
    "ERROR": "构建失败"
}

from .four_layer_iterator import (
    FourLayerIterator,
    IterationStrategy,
    ConvergenceEvaluator
)

from .approval_interface import (
    ApprovalInterfaceManager,
    ApprovalDecision,
    ApprovalData
)

from .feedback_processor import (
    FeedbackProcessor,
    StrategyAdjuster,
    QualityAnalyzer
)

from .export_manager import (
    MultiFormatExporter,
    ReportGenerator,
    ExportFormat
)

__all__ = [
    # 迭代引擎
    "FourLayerIterator",
    "IterationStrategy", 
    "ConvergenceEvaluator",
    
    # 批准界面
    "ApprovalInterfaceManager",
    "ApprovalDecision",
    "ApprovalData",
    
    # 反馈处理
    "FeedbackProcessor",
    "StrategyAdjuster",
    "QualityAnalyzer",
    
    # 导出管理
    "MultiFormatExporter",
    "ReportGenerator",
    "ExportFormat",
]

# 版本信息
__version__ = "1.0.0" 