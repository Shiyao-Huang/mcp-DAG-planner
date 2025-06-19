#!/usr/bin/env python3
"""
缓存管理工具模块

此模块提供项目路径缓存的管理功能，包括：
- list_cached_projects: 列出所有缓存的项目
- get_cached_project_path: 获取缓存的项目路径
- add_project_to_cache: 添加项目到缓存
- remove_project_from_cache: 从缓存移除项目

版本: 1.0.0
"""

import json
import datetime
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

# 导入调试功能
from ..debug import server_debug_log as debug_log


async def list_cached_projects(mcp: FastMCP) -> str:
    """
    列出所有缓存的项目路径
    
    从YAML缓存中列出所有已缓存的项目路径信息，包含项目状态验证
    
    Returns:
        str: JSON格式的项目列表，包含项目名称、路径、有效性等信息
    """
    try:
        from ..dag_storage.path_cache import get_cache_manager
        cache_manager = get_cache_manager()
        result = cache_manager.list_projects()
        
        debug_log(f"缓存项目列表查询完成，找到 {result.get('total_count', 0)} 个项目")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "cache_list_error",
            "message": f"获取缓存项目列表失败: {e}"
        }
        debug_log(f"获取缓存项目列表失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def get_cached_project_path(
    mcp: FastMCP,
    project_name: Annotated[str, Field(description="项目名称，如果不指定则返回最近活跃的项目")] = "",
) -> str:
    """
    从缓存中获取项目路径
    
    Args:
        project_name: 项目名称，如果不指定则返回最近活跃的项目
        
    Returns:
        str: JSON格式的项目路径信息
    """
    try:
        from ..dag_storage.path_cache import get_cache_manager
        cache_manager = get_cache_manager()
        result = cache_manager.get_project_path(project_name if project_name else None)
        
        if result["success"]:
            debug_log(f"从缓存获取项目路径成功: {result.get('project_name')}")
        else:
            debug_log(f"从缓存获取项目路径失败: {result.get('error')}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "cache_get_error",
            "message": f"从缓存获取项目路径失败: {e}"
        }
        debug_log(f"从缓存获取项目路径失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def add_project_to_cache(
    mcp: FastMCP,
    project_name: Annotated[str, Field(description="项目名称")] = "",
    project_path: Annotated[str, Field(description="项目根目录路径")] = "",
    description: Annotated[str, Field(description="项目描述")] = "",
) -> str:
    """
    手动添加项目路径到缓存
    
    Args:
        project_name: 项目名称
        project_path: 项目根目录路径  
        description: 项目描述
        
    Returns:
        str: JSON格式的添加结果
    """
    try:
        if not project_name:
            raise ValueError("project_name 参数必须指定")
        if not project_path:
            raise ValueError("project_path 参数必须指定")
        
        from ..dag_storage.path_cache import get_cache_manager
        cache_manager = get_cache_manager()
        result = cache_manager.add_project_path(project_name, project_path, description)
        
        if result["success"]:
            debug_log(f"项目已手动添加到缓存: {project_name}")
        else:
            debug_log(f"添加项目到缓存失败: {result.get('error')}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "cache_add_error",
            "message": f"添加项目到缓存失败: {e}"
        }
        debug_log(f"添加项目到缓存失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def remove_project_from_cache(
    mcp: FastMCP,
    project_name: Annotated[str, Field(description="要移除的项目名称")] = "",
) -> str:
    """
    从缓存中移除项目
    
    Args:
        project_name: 要移除的项目名称
        
    Returns:
        str: JSON格式的移除结果
    """
    try:
        if not project_name:
            raise ValueError("project_name 参数必须指定")
        
        from ..dag_storage.path_cache import get_cache_manager
        cache_manager = get_cache_manager()
        result = cache_manager.remove_project(project_name)
        
        if result["success"]:
            debug_log(f"项目已从缓存移除: {project_name}")
        else:
            debug_log(f"从缓存移除项目失败: {result.get('error')}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "cache_remove_error",
            "message": f"从缓存移除项目失败: {e}"
        }
        debug_log(f"从缓存移除项目失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2) 