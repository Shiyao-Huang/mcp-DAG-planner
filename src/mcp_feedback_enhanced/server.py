#!/usr/bin/env python3
"""
MCP Feedback Enhanced 精简服务器 - 工具导入版

此版本将所有工具拆分到独立文件中，server.py只负责工具注册和服务器启动。

重构改进：
- 工具模块化：每类工具独立文件管理
- 减少工具数量：合并相关功能（如初始化工具）
- 清晰结构：server.py专注于工具注册和启动
- 易于维护：工具分离后更容易维护和扩展

版本: 2.0.0 (模块化重构版)
作者: MCP DAG Planner Team
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# 导入调试功能
from .debug import server_debug_log as debug_log

# 初始化编码设置
from . import __version__

# ===== 常数定义 =====
SERVER_NAME = "互動式回饋收集 MCP (模块化版)"

# 确保 log_level 设定为正确的大寫格式
fastmcp_settings = {}
env_log_level = os.getenv("FASTMCP_LOG_LEVEL", "").upper()
if env_log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    fastmcp_settings["log_level"] = env_log_level
else:
    fastmcp_settings["log_level"] = "INFO"

# 初始化 MCP 服务器
mcp: Any = FastMCP(SERVER_NAME)

# ===== 工具注册 =====

# 系统工具
from .tools.system_tools import get_system_info as _get_system_info

@mcp.tool()
async def get_system_info() -> str:
    """获取系统环境资讯"""
    return await _get_system_info(mcp)


# 项目路径工具
from .tools.project_tools import get_current_project_root as _get_current_project_root

@mcp.tool()
async def get_current_project_root(
    start_path: str = ".",
    project_markers: list = None,
) -> str:
    """
    获取当前项目的根路径
    
    此工具通过向上搜索项目标识文件来确定项目根目录，确保不同工作区的项目隔离。
    这是解决MCP多工作区路径混乱问题的核心工具。
    
    Args:
        start_path: 开始搜索的路径，默认为当前工作目录
        project_markers: 项目根目录标识文件列表，默认包含常见的项目文件
        
            Returns:
            包含项目根路径信息的文本字符串
    """
    return await _get_current_project_root(mcp, start_path, project_markers)


# 项目管理工具（合并后的智能管理器）
from .tools.project_manager import smart_project_manager as _smart_project_manager

@mcp.tool()
async def smart_project_manager(
    action: str = "check",
    project_path: str = "",
    force_reinit: bool = False,
) -> str:
    """
    智能项目管理器 - 统一的项目初始化和路径管理工具
    
    此工具整合了原来的 get_current_path、set_path、init_path、initialize_project_config 等功能。
    
    支持的操作：
    - check: 检查项目初始化状态和路径信息
    - setup: 智能设置项目路径（自动检查并初始化）
    - init: 强制进行项目初始化
    - info: 获取详细的项目信息和环境状态
    """
    return await _smart_project_manager(mcp, action, project_path, force_reinit)


# 缓存管理工具
from .tools.cache_manager import (
    list_cached_projects as _list_cached_projects,
    get_cached_project_path as _get_cached_project_path,
    add_project_to_cache as _add_project_to_cache,
    remove_project_from_cache as _remove_project_from_cache
)

@mcp.tool()
async def list_cached_projects() -> str:
    """列出所有缓存的项目路径"""
    return await _list_cached_projects(mcp)

@mcp.tool()
async def get_cached_project_path(project_name: str = "") -> str:
    """从缓存中获取项目路径"""
    return await _get_cached_project_path(mcp, project_name)

@mcp.tool()
async def add_project_to_cache(
    project_name: str = "",
    project_path: str = "",
    description: str = "",
) -> str:
    """手动添加项目路径到缓存"""
    return await _add_project_to_cache(mcp, project_name, project_path, description)

@mcp.tool()
async def remove_project_from_cache(project_name: str = "") -> str:
    """从缓存中移除项目"""
    return await _remove_project_from_cache(mcp, project_name)


# 交互工具
from .tools.interactive_tools import interactive_feedback as _interactive_feedback

@mcp.tool()
async def interactive_feedback(
    project_directory: str = ".",
    summary: str = "我已完成了您請求的任務。",
    timeout: int = 120,
) -> list:
    """收集用戶的互動回饋，支援文字和圖片"""
    return await _interactive_feedback(mcp, project_directory, summary, timeout)


# DAG构建工具
from .tools.dag_tools import (
    build_function_layer_dag as _build_function_layer_dag,
    build_logic_layer_dag as _build_logic_layer_dag,
    build_code_layer_dag as _build_code_layer_dag,
    build_order_layer_dag as _build_order_layer_dag,
    get_saved_dags as _get_saved_dags
)

@mcp.tool()
async def build_function_layer_dag(
    project_path: str = "",
    project_description: str = "",
    mermaid_dag: str = "",
    business_requirements: str = "",
) -> str:
    """構建功能層 DAG - What Layer (業務目標層)，project_path 留空時自動檢測項目根路徑"""
    return await _build_function_layer_dag(mcp, project_path, project_description, mermaid_dag, business_requirements)

@mcp.tool()
async def build_logic_layer_dag(
    project_path: str = "",
    function_layer_result: str = "",
    mermaid_dag: str = "",
    technical_architecture: str = "",
) -> str:
    """構建邏輯層 DAG - How Layer (技術架構層)，project_path 留空時自動檢測項目根路徑"""
    return await _build_logic_layer_dag(mcp, project_path, function_layer_result, mermaid_dag, technical_architecture)

@mcp.tool()
async def build_code_layer_dag(
    project_path: str = "",
    logic_layer_result: str = "",
    mermaid_dag: str = "",
    implementation_details: str = "",
) -> str:
    """構建代碼層 DAG - Code Layer (實現架構層)，project_path 留空時自動檢測項目根路徑"""
    return await _build_code_layer_dag(mcp, project_path, logic_layer_result, mermaid_dag, implementation_details)

@mcp.tool()
async def build_order_layer_dag(
    project_path: str = "",
    code_layer_result: str = "",
    mermaid_dag: str = "",
    execution_strategy: str = "",
) -> str:
    """構建排序層 DAG - When Layer (執行順序層)，project_path 留空時自動檢測項目根路徑"""
    return await _build_order_layer_dag(mcp, project_path, code_layer_result, mermaid_dag, execution_strategy)

@mcp.tool()
async def get_saved_dags(project_path: str = "") -> str:
    """获取已保存的DAG文件列表和内容，project_path 留空時自動檢測項目根路徑"""
    return await _get_saved_dags(mcp, project_path)


# AI智能工具
from .tools.ai_tools import (
    ai_identify_current_node as _ai_identify_current_node,
    ai_evaluate_node_completion as _ai_evaluate_node_completion,
    ai_recommend_next_node as _ai_recommend_next_node,
    ai_decide_state_update as _ai_decide_state_update,
    ai_orchestrate_execution as _ai_orchestrate_execution
)

@mcp.tool()
async def ai_identify_current_node(
    dag_data: str = "",
    execution_context: str = "",
    additional_info: str = "",
) -> str:
    """AI智能识别当前应该执行的节点"""
    return await _ai_identify_current_node(mcp, dag_data, execution_context, additional_info)

@mcp.tool()
async def ai_evaluate_node_completion(
    node_id: str = "",
    node_data: str = "",
    completion_evidence: str = "",
    quality_criteria: str = "",
) -> str:
    """AI智能评估节点完成状态和质量"""
    return await _ai_evaluate_node_completion(mcp, node_id, node_data, completion_evidence, quality_criteria)

@mcp.tool()
async def ai_recommend_next_node(
    current_node: str = "",
    dag_data: str = "",
    resource_state: str = "",
    constraints: str = "",
) -> str:
    """AI智能推荐下一个执行节点"""
    return await _ai_recommend_next_node(mcp, current_node, dag_data, resource_state, constraints)

@mcp.tool()
async def ai_decide_state_update(
    node_id: str = "",
    completion_result: str = "",
    impact_scope: str = "",
    update_options: str = "",
) -> str:
    """AI智能决策节点状态更新方案"""
    return await _ai_decide_state_update(mcp, node_id, completion_result, impact_scope, update_options)

@mcp.tool()
async def ai_orchestrate_execution(
    dag_data: str = "",
    execution_config: str = "",
    user_preferences: str = "",
) -> str:
    """AI智能编排4层DAG执行流程"""
    return await _ai_orchestrate_execution(mcp, dag_data, execution_config, user_preferences)


# ===== 主程式入口 =====
def main():
    """主要入口點，用於套件執行"""
    debug_enabled = os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes", "on")
    desktop_mode = os.getenv("MCP_DESKTOP_MODE", "").lower() in ("true", "1", "yes", "on")

    if debug_enabled:
        debug_log("🚀 啟動互動式回饋收集 MCP 服務器 (模块化版)")
        debug_log(f"   服務器名稱: {SERVER_NAME}")
        debug_log(f"   版本: {__version__}")
        debug_log(f"   平台: {sys.platform}")
        debug_log(f"   桌面模式: {'啟用' if desktop_mode else '禁用'}")
        debug_log("   介面類型: Web UI")
        debug_log("   工具架构: 模块化独立文件")
        debug_log(f"   已注册工具数量: 17个 (1个系统+1个项目管理+4个缓存+5个DAG构建+5个AI智能+1个交互工具)")
        debug_log("   功能完整性: ✅ 全部工具已模块化并重新整合，名称冲突已修复，数据流转已连通")
        debug_log("   等待來自 AI 助手的調用...")

    try:
        mcp.run()
    except KeyboardInterrupt:
        if debug_enabled:
            debug_log("收到中斷信號，正常退出")
        sys.exit(0)
    except Exception as e:
        if debug_enabled:
            debug_log(f"MCP 服務器啟動失敗: {e}")
            import traceback
            debug_log(f"詳細錯誤: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()