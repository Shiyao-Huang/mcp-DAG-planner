"""
项目路径管理工具

版本: v1.0.0
作者: MCP-DAG-planner Team
创建时间: 2025-06-19
最后更新: 2025-06-19

功能描述:
- 获取当前项目根路径
- 项目路径验证和规范化
- 支持多工作区隔离

依赖关系:
```mermaid
graph TD
    A[project_tools.py] --> B[get_current_project_root]
    B --> C[项目路径检测]
    C --> D[.git目录查找]
    C --> E[pyproject.toml查找]
    C --> F[package.json查找]
    D --> G[路径规范化]
    E --> G
    F --> G
    G --> H[返回绝对路径]
```

关键函数和变量:
- get_current_project_root(): 获取当前项目根路径
- _find_project_root(): 向上查找项目根目录
- _is_project_root(): 判断是否为项目根目录
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from typing_extensions import Annotated

# 导入MCP相关模块
try:
    from fastmcp import FastMCP
except ImportError:
    # 如果没有fastmcp，使用简单的替代
    class FastMCP:
        def __init__(self, name: str):
            self.name = name

from ..debug import debug_log


async def get_current_project_root(
    mcp: FastMCP,
    start_path: Annotated[str, Field(description="开始搜索的路径，默认为当前工作目录")] = ".",
    project_markers: Annotated[List[str], Field(description="项目根目录标识文件")] = None,
) -> str:
    """
    获取当前项目的根路径
    
    此工具通过向上搜索项目标识文件来确定项目根目录，确保不同工作区的项目隔离。
    
    Args:
        start_path: 开始搜索的路径，默认为当前工作目录
        project_markers: 项目根目录标识文件列表，默认包含常见的项目文件
        
    Returns:
        包含项目根路径信息的文本字符串
        
    工作流程:
        1. 从指定路径开始向上搜索
        2. 查找项目标识文件(.git, pyproject.toml等)
        3. 返回找到的第一个项目根目录
        4. 如果没找到，返回当前工作目录
    """
    
    debug_log("🔍 开始获取当前项目根路径...")
    
    try:
        # 默认项目标识文件
        if project_markers is None:
            project_markers = [
                ".git",           # Git仓库
                "pyproject.toml", # Python项目
                "package.json",   # Node.js项目
                "Cargo.toml",     # Rust项目
                "go.mod",         # Go项目
                "pom.xml",        # Maven项目
                "build.gradle",   # Gradle项目
                ".project",       # Eclipse项目
                "Makefile",       # Make项目
                "requirements.txt", # Python依赖
                "setup.py",       # Python包
                ".cursorrules",   # Cursor规则文件
            ]
        
        # 规范化起始路径
        start_path = os.path.abspath(start_path) if start_path != "." else os.getcwd()
        debug_log(f"🔍 起始搜索路径: {start_path}")
        
        # 查找项目根目录
        project_root = _find_project_root(start_path, project_markers)
        
        if project_root:
            debug_log(f"✅ 找到项目根路径: {project_root}")
            
            # 验证路径存在性
            if not os.path.exists(project_root):
                raise FileNotFoundError(f"项目根路径不存在: {project_root}")
            
            # 获取项目信息
            project_info = _get_project_info(project_root, project_markers)
            
            result_text = f"""✅ 项目根路径获取成功

📁 项目根路径: {project_root}
🏷️  项目名称: {project_info['name']}
📋 项目类型: {project_info['type']}
🔍 识别文件: {', '.join(project_info['markers'])}
📊 目录统计: {project_info['stats']}

🎯 使用建议:
- 将此路径作为所有MCP工具的project_directory参数
- 确保.EDATA目录在此路径下创建
- 避免使用MCP服务的工作目录，保持项目隔离
"""
            
            return result_text
            
        else:
            # 没找到项目根，使用当前工作目录
            current_dir = os.getcwd()
            debug_log(f"⚠️ 未找到项目根，使用当前工作目录: {current_dir}")
            
            result_text = f"""⚠️ 未找到明确的项目根目录

📁 当前工作目录: {current_dir}
🔍 搜索起始路径: {start_path}
📋 查找的标识文件: {', '.join(project_markers)}

💡 建议:
- 确保在项目根目录下运行
- 检查是否存在项目标识文件(.git, pyproject.toml等)
- 可以手动指定project_directory参数
"""
            
            return result_text
            
    except Exception as e:
        error_msg = f"❌ 获取项目根路径失败: {str(e)}"
        debug_log(error_msg)
        return error_msg


def _find_project_root(start_path: str, markers: List[str]) -> Optional[str]:
    """
    向上搜索项目根目录
    
    Args:
        start_path: 开始搜索的路径
        markers: 项目标识文件列表
        
    Returns:
        项目根路径，如果未找到返回None
    """
    current_path = Path(start_path).resolve()
    
    # 向上搜索，直到根目录
    while current_path != current_path.parent:
        if _is_project_root(current_path, markers):
            return str(current_path)
        current_path = current_path.parent
    
    # 检查根目录
    if _is_project_root(current_path, markers):
        return str(current_path)
    
    return None


def _is_project_root(path: Path, markers: List[str]) -> bool:
    """
    判断路径是否为项目根目录
    
    Args:
        path: 要检查的路径
        markers: 项目标识文件列表
        
    Returns:
        如果是项目根目录返回True
    """
    for marker in markers:
        marker_path = path / marker
        if marker_path.exists():
            debug_log(f"🎯 找到项目标识: {marker_path}")
            return True
    return False


def _get_project_info(project_root: str, markers: List[str]) -> dict:
    """
    获取项目详细信息
    
    Args:
        project_root: 项目根路径
        markers: 项目标识文件列表
        
    Returns:
        包含项目信息的字典
    """
    root_path = Path(project_root)
    
    # 获取项目名称
    project_name = root_path.name
    
    # 检测项目类型和存在的标识文件
    found_markers = []
    project_types = []
    
    for marker in markers:
        marker_path = root_path / marker
        if marker_path.exists():
            found_markers.append(marker)
            
            # 根据标识文件确定项目类型
            if marker == ".git":
                project_types.append("Git仓库")
            elif marker == "pyproject.toml":
                project_types.append("Python项目")
            elif marker == "package.json":
                project_types.append("Node.js项目")
            elif marker == "Cargo.toml":
                project_types.append("Rust项目")
            elif marker == "go.mod":
                project_types.append("Go项目")
            elif marker in ["pom.xml", "build.gradle"]:
                project_types.append("Java项目")
            elif marker == ".cursorrules":
                project_types.append("Cursor项目")
    
    # 目录统计
    try:
        files_count = len([f for f in root_path.iterdir() if f.is_file()])
        dirs_count = len([d for d in root_path.iterdir() if d.is_dir()])
        stats = f"{files_count}个文件, {dirs_count}个目录"
    except Exception:
        stats = "无法获取统计信息"
    
    return {
        "name": project_name,
        "type": " + ".join(project_types) if project_types else "未知类型",
        "markers": found_markers,
        "stats": stats
    } 