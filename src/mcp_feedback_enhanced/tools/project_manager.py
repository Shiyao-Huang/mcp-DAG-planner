#!/usr/bin/env python3
"""
项目管理工具模块 - 智能项目初始化和路径管理

此模块提供统一的项目管理功能，合并了原来分散的初始化工具：
- get_current_path
- set_path  
- init_path
- initialize_project_config
- get_project_path

主要功能：
- 智能项目路径检测和设置
- 自动初始化项目结构
- 路径缓存管理
- 项目状态验证

版本: 1.0.0
"""

import json
import sys
import datetime
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

# 导入调试功能
from ..debug import server_debug_log as debug_log


async def smart_project_manager(
    mcp: FastMCP,
    action: Annotated[str, Field(description="操作类型：check(检查状态)、setup(设置路径)、init(强制初始化)、info(获取信息)")] = "check",
    project_path: Annotated[str, Field(description="项目根目录路径，如果为空则使用当前目录")] = "",
    force_reinit: Annotated[bool, Field(description="是否强制重新初始化，即使已存在配置")] = False,
) -> str:
    """
    智能项目管理器 - 统一的项目初始化和路径管理工具
    
    此工具整合了所有项目初始化相关功能，提供一站式项目管理服务。
    可以智能检测项目状态，自动进行必要的初始化操作。
    
    支持的操作：
    - check: 检查项目初始化状态和路径信息
    - setup: 智能设置项目路径（自动检查并初始化）
    - init: 强制进行项目初始化
    - info: 获取详细的项目信息和环境状态
    
    Args:
        action: 操作类型，默认为check
        project_path: 项目根目录路径，为空时使用当前目录
        force_reinit: 是否强制重新初始化
        
    Returns:
        str: JSON格式的操作结果，包含项目状态和路径信息
    """
    try:
        debug_log(f"智能项目管理器启动 - 操作: {action}, 路径: {project_path}")
        
        # 确定项目路径
        if not project_path:
            # 使用当前工作目录或脚本所在位置推断
            current_dir = Path.cwd()
            script_dir = Path(__file__).resolve().parent.parent.parent.parent
            
            # 优先使用当前目录，除非它是脚本内部目录
            if current_dir.is_relative_to(script_dir):
                base_path = script_dir
            else:
                base_path = current_dir
        else:
            base_path = Path(project_path).resolve()
        
        debug_log(f"确定的项目根路径: {base_path}")
        
        # 检查项目结构
        edata_path = base_path / ".EDATA"
        config_file = edata_path / "config.json"
        
        # 检查初始化状态
        is_initialized = edata_path.exists() and config_file.exists()
        
        # 根据操作类型执行相应逻辑
        if action == "check":
            return await _check_project_status(base_path, edata_path, config_file, is_initialized)
        elif action == "setup":
            return await _setup_project_path(base_path, edata_path, config_file, is_initialized, force_reinit)
        elif action == "init":
            return await _initialize_project(base_path, edata_path, config_file, force_reinit)
        elif action == "info":
            return await _get_project_info(base_path, edata_path, config_file, is_initialized)
        else:
            raise ValueError(f"不支持的操作类型: {action}")
            
    except Exception as e:
        error_result = {
            "success": False,
            "action": action,
            "error": str(e),
            "error_type": "project_manager_error",
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"智能项目管理器失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def _check_project_status(base_path: Path, edata_path: Path, config_file: Path, is_initialized: bool) -> str:
    """检查项目状态"""
    try:
        # 检查路径缓存
        cache_info = {}
        try:
            from ..dag_storage.path_cache import get_cache_manager
            cache_manager = get_cache_manager()
            cached_path = cache_manager.get_project_path(None)
            if cached_path["success"]:
                cache_info = {
                    "cached_project_found": True,
                    "cached_project_name": cached_path.get("project_name"),
                    "cached_project_path": cached_path.get("project_path"),
                    "is_current_path": str(base_path) == cached_path.get("project_path")
                }
            else:
                cache_info = {"cached_project_found": False}
        except Exception as e:
            cache_info = {"cache_error": str(e)}
        
        result = {
            "success": True,
            "action": "check",
            "project_status": {
                "project_root": str(base_path),
                "edata_path": str(edata_path),
                "config_file": str(config_file),
                "is_initialized": is_initialized,
                "status": "initialized" if is_initialized else "not_initialized"
            },
            "cache_status": cache_info,
            "recommendations": []
        }
        
        # 添加建议
        if not is_initialized:
            result["recommendations"].append("项目未初始化，建议使用 action='setup' 进行设置")
        else:
            result["recommendations"].append("项目已初始化，可以开始使用DAG构建工具")
            
        if not cache_info.get("cached_project_found"):
            result["recommendations"].append("项目未在缓存中，建议使用 action='setup' 添加到缓存")
        
        debug_log(f"项目状态检查完成 - 初始化状态: {is_initialized}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        raise Exception(f"检查项目状态失败: {e}")


async def _setup_project_path(base_path: Path, edata_path: Path, config_file: Path, is_initialized: bool, force_reinit: bool) -> str:
    """智能设置项目路径"""
    try:
        if is_initialized and not force_reinit:
            # 已初始化，直接设置路径并更新缓存
            debug_log("项目已初始化，直接设置路径")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            
            result = {
                "success": True,
                "action": "setup",
                "operation_type": "path_set",
                "message": "项目路径设置成功，使用现有配置",
                "project_path": str(base_path),
                "existing_config": existing_config,
                "was_already_initialized": True
            }
        else:
            # 需要初始化
            debug_log("执行项目初始化")
            
            # 创建目录结构
            directories_to_create = [
                edata_path,
                edata_path / "dags",
                edata_path / "backups",
                edata_path / "temp",
                edata_path / "configs", 
                edata_path / "sessions",
                edata_path / "logs"
            ]
            
            created_dirs = []
            for directory in directories_to_create:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(directory))
            
            # 创建配置文件
            config_data = _create_default_config(base_path, edata_path)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            result = {
                "success": True,
                "action": "setup",
                "operation_type": "initialized_and_set",
                "message": "项目初始化并设置成功",
                "project_path": str(base_path),
                "created_directories": created_dirs,
                "new_config": config_data,
                "was_already_initialized": False
            }
        
        # 更新缓存
        try:
            from ..dag_storage.path_cache import get_cache_manager
            cache_manager = get_cache_manager()
            project_name = base_path.name
            cache_result = cache_manager.add_project_path(
                project_name=project_name,
                project_path=str(base_path),
                description=f"通过智能项目管理器添加 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            result["cache_updated"] = cache_result["success"]
            result["cache_project_name"] = project_name
            if not cache_result["success"]:
                result["cache_error"] = cache_result.get("error")
                
        except Exception as e:
            result["cache_updated"] = False
            result["cache_error"] = str(e)
        
        result["next_steps"] = [
            "可以开始使用四层DAG构建工具",
            "使用 build_function_layer_dag 开始构建功能层",
            "项目已加入缓存，后续操作更便捷"
        ]
        
        debug_log(f"项目设置完成: {base_path}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        raise Exception(f"设置项目路径失败: {e}")


async def _initialize_project(base_path: Path, edata_path: Path, config_file: Path, force_reinit: bool) -> str:
    """强制初始化项目"""
    try:
        debug_log(f"强制初始化项目: {base_path}")
        
        if config_file.exists() and not force_reinit:
            return json.dumps({
                "success": False,
                "action": "init",
                "error": "项目已初始化，如需重新初始化请设置 force_reinit=true"
            }, ensure_ascii=False, indent=2)
        
        # 创建目录结构
        directories_to_create = [
            edata_path,
            edata_path / "dags",
            edata_path / "backups",
            edata_path / "temp",
            edata_path / "configs",
            edata_path / "sessions", 
            edata_path / "logs"
        ]
        
        created_dirs = []
        for directory in directories_to_create:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(directory))
        
        # 创建配置文件
        config_data = _create_default_config(base_path, edata_path)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 创建初始化记录
        init_record_file = edata_path / "initialization_record.json"
        init_record = {
            "initialization_time": datetime.datetime.now().isoformat(),
            "initialization_method": "smart_project_manager_force_init",
            "project_path": str(base_path),
            "edata_path": str(edata_path),
            "created_directories": created_dirs,
            "config_file": str(config_file),
            "force_reinit": force_reinit,
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version.split()[0]
            }
        }
        
        with open(init_record_file, 'w', encoding='utf-8') as f:
            json.dump(init_record, f, ensure_ascii=False, indent=2)
        
        result = {
            "success": True,
            "action": "init",
            "message": "项目强制初始化成功",
            "project_path": str(base_path),
            "created_directories": created_dirs,
            "config_data": config_data,
            "init_record": init_record,
            "initialization_time": datetime.datetime.now().isoformat()
        }
        
        debug_log(f"项目强制初始化完成: {base_path}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        raise Exception(f"强制初始化项目失败: {e}")


async def _get_project_info(base_path: Path, edata_path: Path, config_file: Path, is_initialized: bool) -> str:
    """获取详细项目信息"""
    try:
        debug_log("获取详细项目信息")
        
        # 基础信息
        result = {
            "success": True,
            "action": "info",
            "project_info": {
                "project_root": str(base_path),
                "project_name": base_path.name,
                "edata_path": str(edata_path),
                "config_file": str(config_file),
                "is_initialized": is_initialized
            },
            "environment_info": {
                "python_executable": sys.executable,
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "script_location": str(Path(__file__).resolve().parent)
            },
            "directory_structure": {}
        }
        
        # 如果已初始化，获取配置信息
        if is_initialized:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                result["config_data"] = config_data
                
                # 检查目录结构
                required_dirs = ["dags", "backups", "temp", "configs", "sessions", "logs"]
                for dir_name in required_dirs:
                    dir_path = edata_path / dir_name
                    result["directory_structure"][dir_name] = {
                        "exists": dir_path.exists(),
                        "path": str(dir_path),
                        "file_count": len(list(dir_path.iterdir())) if dir_path.exists() else 0
                    }
            except Exception as e:
                result["config_error"] = str(e)
        
        # 缓存信息
        try:
            from ..dag_storage.path_cache import get_cache_manager
            cache_manager = get_cache_manager()
            cache_list = cache_manager.list_projects()
            result["cache_info"] = cache_list
        except Exception as e:
            result["cache_error"] = str(e)
        
        debug_log("详细项目信息获取完成")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        raise Exception(f"获取项目信息失败: {e}")


def _create_default_config(base_path: Path, edata_path: Path) -> dict:
    """创建默认配置"""
    return {
        "project_info": {
            "name": base_path.name,
            "root_path": str(base_path),
            "edata_path": str(edata_path),
            "created_at": datetime.datetime.now().isoformat(),
            "version": "1.0.0",
            "initialized_by": "smart_project_manager"
        },
        "dag_storage": {
            "base_path": str(edata_path),
            "dags_path": str(edata_path / "dags"),
            "backups_path": str(edata_path / "backups"),
            "temp_path": str(edata_path / "temp"),
            "configs_path": str(edata_path / "configs")
        },
        "memory_layer": {
            "current_session": None,
            "last_active_dag": None,
            "session_count": 0,
            "layer_status": {
                "function": "not_started",
                "logic": "not_started",
                "code": "not_started",
                "order": "not_started"
            },
            "execution_history": []
        },
        "settings": {
            "auto_backup": True,
            "debug_mode": True,
            "max_backup_files": 10,
            "auto_cleanup": True,
            "log_level": "INFO"
        },
        "statistics": {
            "total_dags_created": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "last_execution": None
        }
    } 