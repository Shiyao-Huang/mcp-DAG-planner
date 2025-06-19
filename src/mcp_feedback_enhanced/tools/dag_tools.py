#!/usr/bin/env python3
"""
DAG构建工具模块

此模块提供四层DAG构建功能，包括：
- build_function_layer_dag: 构建功能层DAG
- build_logic_layer_dag: 构建逻辑层DAG
- build_code_layer_dag: 构建代码层DAG
- build_order_layer_dag: 构建排序层DAG

版本: 1.0.0
"""

import json
import datetime
import asyncio
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

# 导入调试功能
from ..debug import server_debug_log as debug_log

# 导入项目路径工具
from .project_tools import _find_project_root


def _auto_detect_project_path(provided_path: str = "") -> str:
    """
    自动检测项目根路径
    
    Args:
        provided_path: 用户提供的路径，如果为空则自动检测
        
    Returns:
        项目根路径
    """
    if provided_path:
        debug_log(f"使用用户提供的项目路径: {provided_path}")
        return provided_path
    
    # 自动检测项目根路径
    project_markers = [
        ".git", "pyproject.toml", "package.json", "Cargo.toml", 
        "go.mod", "pom.xml", "build.gradle", ".project", 
        "Makefile", "requirements.txt", "setup.py", ".cursorrules"
    ]
    
    import os
    
    # 策略1: 尝试从环境变量获取
    env_project_path = os.getenv("MCP_PROJECT_ROOT")
    if env_project_path and os.path.exists(env_project_path):
        debug_log(f"从环境变量获取项目路径: {env_project_path}")
        return env_project_path
    
    # 策略2: 尝试从已知的项目路径搜索
    candidate_paths = [
        "/Users/swmt/Desktop/hsy/大模型/MCP-some",  # 已知的项目根路径
        "/Users/swmt/Desktop/hsy/大模型/MCP-some/mcp-DAG-planner",  # MCP项目路径
        os.path.expanduser("~/Desktop/hsy/大模型/MCP-some"),  # 用户主目录相对路径
        os.path.expanduser("~/Desktop/hsy/大模型/MCP-some/mcp-DAG-planner"),
    ]
    
    for candidate in candidate_paths:
        if os.path.exists(candidate):
            detected_path = _find_project_root(candidate, project_markers)
            if detected_path:
                debug_log(f"从候选路径检测到项目根路径: {detected_path}")
                return detected_path
    
    # 策略3: 尝试从当前工作目录开始搜索
    start_path = os.getcwd()
    debug_log(f"当前工作目录: {start_path}")
    
    # 如果当前工作目录是根目录，这通常不是我们想要的
    if start_path == "/" or start_path.startswith("/tmp"):
        debug_log("当前工作目录不可用，使用默认项目路径")
        # 使用已知的MCP项目路径作为默认值
        default_path = "/Users/swmt/Desktop/hsy/大模型/MCP-some/mcp-DAG-planner"
        if os.path.exists(default_path):
            return default_path
        else:
            return "/Users/swmt/Desktop/hsy/大模型/MCP-some"
    
    detected_path = _find_project_root(start_path, project_markers)
    
    if detected_path:
        debug_log(f"自动检测到项目根路径: {detected_path}")
        return detected_path
    else:
        # 回退到当前工作目录
        debug_log(f"未能自动检测项目根路径，使用当前工作目录: {start_path}")
        return start_path


async def build_function_layer_dag(
    mcp: FastMCP,
    project_path: Annotated[str, Field(description="項目根目錄路徑，留空時自動檢測")] = "",
    project_description: Annotated[str, Field(description="項目描述和目標")] = "",
    mermaid_dag: Annotated[str, Field(description="功能層 Mermaid DAG 描述")] = "",
    business_requirements: Annotated[str, Field(description="業務需求列表")] = "",
) -> str:
    """构建功能层DAG"""
    try:
        debug_log("開始功能層 DAG 構建")
        
        # 自动检测或使用提供的项目路径
        actual_project_path = _auto_detect_project_path(project_path)
        debug_log(f"實際使用的項目路徑: {actual_project_path}")
        
        current_path = Path(actual_project_path).resolve()
        edata_path = current_path / ".EDATA"
        config_file = edata_path / "config.json"
        
        # 检查项目初始化状态
        if not edata_path.exists() or not config_file.exists():
            debug_log("項目未初始化，開始自動初始化...")
            
            directories_to_create = [
                edata_path, edata_path / "dags", edata_path / "backups", 
                edata_path / "temp", edata_path / "configs", 
                edata_path / "sessions", edata_path / "logs"
            ]
            
            for directory in directories_to_create:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
            
            # 创建配置文件
            config_data = {
                "project_info": {
                    "name": current_path.name,
                    "root_path": str(current_path),
                    "edata_path": str(edata_path),
                    "created_at": datetime.datetime.now().isoformat(),
                    "version": "1.0.0"
                },
                "dag_storage": {
                    "base_path": str(edata_path),
                    "dags_path": str(edata_path / "dags"),
                    "backups_path": str(edata_path / "backups"),
                    "temp_path": str(edata_path / "temp")
                },
                "memory_layer": {
                    "layer_status": {
                        "function": "not_started", "logic": "not_started",
                        "code": "not_started", "order": "not_started"
                    }
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 加载配置
        with open(config_file, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 构建DAG结果
        result = {
            "success": True,
            "layer_type": "function",
            "layer_name": "功能層 (What Layer)",
            "description": "業務目標和功能需求層",
            "input_data": {
                "project_description": project_description,
                "mermaid_dag": mermaid_dag,
                "business_requirements": business_requirements,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "parsed_dag": {
                "nodes": [], "edges": [],
                "metadata": {
                    "layer": "function",
                    "focus": ["業務功能識別", "功能模塊依賴"],
                    "node_count": len(mermaid_dag.split('\n')) if mermaid_dag else 0
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["功能層 DAG 接收成功"]
            }
        }
        
        # 保存DAG数据
        dag_storage_path = Path(project_config["dag_storage"]["dags_path"])
        dag_id = f"function_layer_{hash(mermaid_dag) % 100000}"
        dag_file = dag_storage_path / f"{dag_id}.json"
        
        with open(dag_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        result["storage_info"] = {
            "file_path": str(dag_file),
            "dag_id": dag_id,
            "saved_successfully": True
        }
        
        debug_log(f"功能層 DAG 成功保存到: {dag_file}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "function",
            "error": str(e)
        }
        debug_log(f"功能層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def build_logic_layer_dag(
    mcp: FastMCP,
    project_path: Annotated[str, Field(description="項目根目錄路徑，留空時自動檢測")] = "",
    function_layer_result: Annotated[str, Field(description="功能層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="邏輯層 Mermaid DAG 描述")] = "",
    technical_architecture: Annotated[str, Field(description="技術架構設計")] = "",
) -> str:
    """构建逻辑层DAG"""
    try:
        debug_log("開始構建邏輯層 DAG")
        
        # 自动检测或使用提供的项目路径
        actual_project_path = _auto_detect_project_path(project_path)
        debug_log(f"實際使用的項目路徑: {actual_project_path}")
        
        current_path = Path(actual_project_path).resolve()
        dags_path = current_path / ".EDATA" / "dags"
        
        result = {
            "success": True,
            "layer_type": "logic",
            "layer_name": "邏輯層 (How Layer)",
            "description": "技術架構和系統設計層",
            "input_data": {
                "function_layer_result": function_layer_result,
                "mermaid_dag": mermaid_dag,
                "technical_architecture": technical_architecture,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "parsed_dag": {
                "nodes": [], "edges": [],
                "metadata": {
                    "layer": "logic",
                    "focus": ["架構設計", "技術選型"],
                    "node_count": len(mermaid_dag.split('\n')) if mermaid_dag else 0
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["邏輯層 DAG 接收成功"]
            }
        }
        
        # 保存DAG数据
        dag_id = f"logic_layer_{hash(mermaid_dag) % 100000}"
        dag_file = dags_path / f"{dag_id}.json"
        
        with open(dag_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        result["storage_info"] = {
            "file_path": str(dag_file),
            "dag_id": dag_id,
            "saved_successfully": True
        }
        
        debug_log(f"邏輯層 DAG 成功保存到: {dag_file}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "logic",
            "error": str(e)
        }
        debug_log(f"邏輯層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def build_code_layer_dag(
    mcp: FastMCP,
    project_path: Annotated[str, Field(description="項目根目錄路徑，留空時自動檢測")] = "",
    logic_layer_result: Annotated[str, Field(description="邏輯層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="代碼層 Mermaid DAG 描述")] = "",
    implementation_details: Annotated[str, Field(description="實現細節和技術選型")] = "",
) -> str:
    """构建代码层DAG"""
    try:
        debug_log("開始構建代碼層 DAG")
        
        # 自动检测或使用提供的项目路径
        actual_project_path = _auto_detect_project_path(project_path)
        debug_log(f"實際使用的項目路徑: {actual_project_path}")
        
        current_path = Path(actual_project_path).resolve()
        dags_path = current_path / ".EDATA" / "dags"
        
        result = {
            "success": True,
            "layer_type": "code",
            "layer_name": "代碼層 (Code Layer)",
            "description": "代碼實現和模塊組織層",
            "input_data": {
                "logic_layer_result": logic_layer_result,
                "mermaid_dag": mermaid_dag,
                "implementation_details": implementation_details,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "parsed_dag": {
                "nodes": [], "edges": [],
                "metadata": {
                    "layer": "code",
                    "focus": ["代碼模塊", "實現細節"],
                    "node_count": len(mermaid_dag.split('\n')) if mermaid_dag else 0
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["代碼層 DAG 接收成功"]
            }
        }
        
        # 保存DAG数据
        dag_id = f"code_layer_{hash(mermaid_dag) % 100000}"
        dag_file = dags_path / f"{dag_id}.json"
        
        with open(dag_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        result["storage_info"] = {
            "file_path": str(dag_file),
            "dag_id": dag_id,
            "saved_successfully": True
        }
        
        debug_log(f"代碼層 DAG 成功保存到: {dag_file}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "code",
            "error": str(e)
        }
        debug_log(f"代碼層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def build_order_layer_dag(
    mcp: FastMCP,
    project_path: Annotated[str, Field(description="項目根目錄路徑，留空時自動檢測")] = "",
    code_layer_result: Annotated[str, Field(description="代碼層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="排序層 Mermaid DAG 描述")] = "",
    execution_strategy: Annotated[str, Field(description="執行策略和時序安排")] = "",
) -> str:
    """构建排序层DAG"""
    try:
        debug_log("開始構建排序層 DAG")
        
        # 自动检测或使用提供的项目路径
        actual_project_path = _auto_detect_project_path(project_path)
        debug_log(f"實際使用的項目路徑: {actual_project_path}")
        
        current_path = Path(actual_project_path).resolve()
        dags_path = current_path / ".EDATA" / "dags"
        
        result = {
            "success": True,
            "layer_type": "order",
            "layer_name": "排序層 (When Layer)",
            "description": "執行順序和時序安排層",
            "input_data": {
                "code_layer_result": code_layer_result,
                "mermaid_dag": mermaid_dag,
                "execution_strategy": execution_strategy,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "parsed_dag": {
                "nodes": [], "edges": [],
                "metadata": {
                    "layer": "order",
                    "focus": ["執行順序", "時序控制"],
                    "node_count": len(mermaid_dag.split('\n')) if mermaid_dag else 0
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["排序層 DAG 接收成功"]
            }
        }
        
        # 保存DAG数据
        dag_id = f"order_layer_{hash(mermaid_dag) % 100000}"
        dag_file = dags_path / f"{dag_id}.json"
        
        with open(dag_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        result["storage_info"] = {
            "file_path": str(dag_file),
            "dag_id": dag_id,
            "saved_successfully": True
        }
        
        debug_log(f"排序層 DAG 成功保存到: {dag_file}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "order",
            "error": str(e)
        }
        debug_log(f"排序層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


async def get_saved_dags(
    mcp: FastMCP,
    project_path: str = "",
) -> str:
    """获取已保存的DAG文件列表和内容"""
    try:
        debug_log("开始获取已保存的DAG文件")
        
        # 自动检测或使用提供的项目路径
        actual_project_path = _auto_detect_project_path(project_path)
        debug_log(f"實際使用的項目路徑: {actual_project_path}")
        
        current_path = Path(actual_project_path).resolve()
        dags_path = current_path / ".EDATA" / "dags"
        
        if not dags_path.exists():
            debug_log(f"DAG目录不存在: {dags_path}")
            return json.dumps({
                "success": True,
                "dags": {},
                "message": "DAG目录不存在，尚未创建任何DAG"
            }, ensure_ascii=False, indent=2)
        
        # 扫描DAG文件
        dag_files = {}
        
        # 按层分类收集DAG文件
        for json_file in dags_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    dag_data = json.load(f)
                
                layer_type = dag_data.get("layer_type", "unknown")
                
                if layer_type not in dag_files:
                    dag_files[layer_type] = []
                
                # 添加文件信息
                file_info = {
                    "file_name": json_file.name,
                    "file_path": str(json_file),
                    "layer_type": layer_type,
                    "layer_name": dag_data.get("layer_name", f"{layer_type.title()} Layer"),
                    "timestamp": dag_data.get("input_data", {}).get("timestamp", ""),
                    "dag_data": dag_data,
                    "file_size": json_file.stat().st_size,
                    "created_time": datetime.datetime.fromtimestamp(json_file.stat().st_ctime).isoformat()
                }
                
                dag_files[layer_type].append(file_info)
                
            except Exception as e:
                debug_log(f"读取DAG文件失败 {json_file}: {e}")
                continue
        
        # 按时间排序每个层的文件
        for layer in dag_files:
            dag_files[layer].sort(key=lambda x: x["timestamp"], reverse=True)
        
        # 统计信息
        total_files = sum(len(files) for files in dag_files.values())
        
        result = {
            "success": True,
            "project_path": str(current_path),
            "dags_directory": str(dags_path),
            "dags": dag_files,
            "summary": {
                "total_files": total_files,
                "layers_found": list(dag_files.keys()),
                "layer_counts": {layer: len(files) for layer, files in dag_files.items()}
            },
            "last_scan": datetime.datetime.now().isoformat()
        }
        
        debug_log(f"找到 {total_files} 个DAG文件，涵盖 {len(dag_files)} 个层级")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "project_path": project_path
        }
        debug_log(f"获取DAG文件失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2) 