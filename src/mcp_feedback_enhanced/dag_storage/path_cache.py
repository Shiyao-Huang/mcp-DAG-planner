#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path Cache Manager - 项目路径缓存管理器

Version: v1.0.0
Date: 2025-06-18
Purpose: 管理本地项目路径缓存，避免硬编码路径问题

```mermaid
graph TD
    A[用户设置路径] --> B[更新YAML缓存]
    B --> C[验证路径有效性]
    C --> D[存储到缓存文件]
    
    E[获取存储路径] --> F[读取YAML缓存]
    F --> G[验证缓存路径]
    G --> H[返回有效路径]
    
    I[缓存文件位置] --> J[~/.mcp_dag_cache.yaml]
    I --> K[项目根目录/.dag_cache.yaml]
```

功能特性：
- YAML格式存储项目路径信息
- 支持多项目路径缓存
- 自动验证路径有效性
- 提供fallback机制
"""

import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class PathCacheManager:
    """项目路径缓存管理器"""
    
    def __init__(self):
        """初始化缓存管理器"""
        # 缓存文件位置 - 优先在用户home目录
        self.home_cache_file = Path.home() / ".mcp_dag_cache.yaml"
        self.local_cache_file = Path.cwd() / ".dag_cache.yaml"
        
        # 确保缓存文件存在
        self._ensure_cache_files()
    
    def _ensure_cache_files(self) -> None:
        """确保缓存文件存在"""
        for cache_file in [self.home_cache_file, self.local_cache_file]:
            if not cache_file.exists():
                self._create_empty_cache(cache_file)
    
    def _create_empty_cache(self, cache_file: Path) -> None:
        """创建空的缓存文件"""
        empty_cache = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "projects": {},
            "last_active_project": None,
            "settings": {
                "auto_detect": True,
                "cache_ttl_hours": 24,
                "max_projects": 50
            }
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                yaml.dump(empty_cache, f, default_flow_style=False, allow_unicode=True, indent=2)
            print(f"✅ 创建缓存文件: {cache_file}")
        except Exception as e:
            print(f"⚠️ 创建缓存文件失败 {cache_file}: {e}")
    
    def _load_cache(self, cache_file: Path) -> Dict[str, Any]:
        """加载缓存数据"""
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️ 读取缓存文件失败 {cache_file}: {e}")
        
        return {}
    
    def _save_cache(self, cache_file: Path, data: Dict[str, Any]) -> bool:
        """保存缓存数据"""
        try:
            data["updated_at"] = datetime.now().isoformat()
            with open(cache_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
            return True
        except Exception as e:
            print(f"⚠️ 保存缓存文件失败 {cache_file}: {e}")
            return False
    
    def add_project_path(self, project_name: str, project_path: str, description: str = "") -> Dict[str, Any]:
        """添加项目路径到缓存"""
        try:
            project_path_obj = Path(project_path).resolve()
            edata_path = project_path_obj / ".EDATA"
            
            # 验证路径有效性
            if not project_path_obj.exists():
                return {
                    "success": False,
                    "error": f"项目路径不存在: {project_path}"
                }
            
            if not edata_path.exists():
                return {
                    "success": False,
                    "error": f".EDATA目录不存在: {edata_path}"
                }
            
            config_file = edata_path / "config.json"
            if not config_file.exists():
                return {
                    "success": False,
                    "error": f"配置文件不存在: {config_file}"
                }
            
            # 加载现有缓存
            cache_data = self._load_cache(self.home_cache_file)
            if not cache_data:
                cache_data = {
                    "version": "1.0.0",
                    "projects": {},
                    "settings": {}
                }
            
            # 添加项目信息
            project_info = {
                "path": str(project_path_obj),
                "edata_path": str(edata_path),
                "config_file": str(config_file),
                "description": description,
                "added_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "is_valid": True,
                "access_count": cache_data.get("projects", {}).get(project_name, {}).get("access_count", 0) + 1
            }
            
            cache_data["projects"][project_name] = project_info
            cache_data["last_active_project"] = project_name
            
            # 保存到两个缓存文件
            home_saved = self._save_cache(self.home_cache_file, cache_data)
            local_saved = self._save_cache(self.local_cache_file, cache_data)
            
            return {
                "success": True,
                "project_name": project_name,
                "project_path": str(project_path_obj),
                "edata_path": str(edata_path),
                "cache_files_updated": {
                    "home_cache": home_saved,
                    "local_cache": local_saved
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"添加项目路径失败: {e}"
            }
    
    def get_project_path(self, project_name: str = None) -> Dict[str, Any]:
        """获取项目路径信息"""
        try:
            # 优先从home缓存读取
            cache_data = self._load_cache(self.home_cache_file)
            if not cache_data:
                cache_data = self._load_cache(self.local_cache_file)
            
            if not cache_data or "projects" not in cache_data:
                return {
                    "success": False,
                    "error": "缓存文件为空或无效"
                }
            
            projects = cache_data["projects"]
            
            if not projects:
                return {
                    "success": False,
                    "error": "缓存中没有项目记录"
                }
            
            # 确定要返回的项目
            if project_name:
                if project_name not in projects:
                    return {
                        "success": False,
                        "error": f"项目 '{project_name}' 不在缓存中"
                    }
                target_project = project_name
            else:
                # 使用最后活跃的项目
                target_project = cache_data.get("last_active_project")
                if not target_project or target_project not in projects:
                    # 使用最近访问的项目
                    sorted_projects = sorted(
                        projects.items(),
                        key=lambda x: x[1].get("last_accessed", ""),
                        reverse=True
                    )
                    if sorted_projects:
                        target_project = sorted_projects[0][0]
                    else:
                        return {
                            "success": False,
                            "error": "缓存中没有有效的项目"
                        }
            
            project_info = projects[target_project]
            
            # 验证路径是否仍然有效
            project_path = Path(project_info["path"])
            edata_path = Path(project_info["edata_path"])
            config_file = Path(project_info["config_file"])
            
            is_valid = all([
                project_path.exists(),
                edata_path.exists(),
                config_file.exists()
            ])
            
            # 更新访问记录
            if is_valid:
                project_info["last_accessed"] = datetime.now().isoformat()
                project_info["access_count"] = project_info.get("access_count", 0) + 1
                cache_data["last_active_project"] = target_project
                self._save_cache(self.home_cache_file, cache_data)
            
            return {
                "success": True,
                "project_name": target_project,
                "project_info": project_info,
                "is_valid": is_valid,
                "all_projects": list(projects.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取项目路径失败: {e}"
            }
    
    def list_projects(self) -> Dict[str, Any]:
        """列出所有缓存的项目"""
        try:
            cache_data = self._load_cache(self.home_cache_file)
            if not cache_data:
                cache_data = self._load_cache(self.local_cache_file)
            
            if not cache_data or "projects" not in cache_data:
                return {
                    "success": True,
                    "projects": [],
                    "total_count": 0
                }
            
            projects_list = []
            for name, info in cache_data["projects"].items():
                project_path = Path(info["path"])
                edata_path = Path(info["edata_path"])
                config_file = Path(info["config_file"])
                
                is_valid = all([
                    project_path.exists(),
                    edata_path.exists(),
                    config_file.exists()
                ])
                
                projects_list.append({
                    "name": name,
                    "path": info["path"],
                    "description": info.get("description", ""),
                    "added_at": info.get("added_at"),
                    "last_accessed": info.get("last_accessed"),
                    "access_count": info.get("access_count", 0),
                    "is_valid": is_valid
                })
            
            # 按最近访问时间排序
            projects_list.sort(key=lambda x: x.get("last_accessed", ""), reverse=True)
            
            return {
                "success": True,
                "projects": projects_list,
                "total_count": len(projects_list),
                "last_active": cache_data.get("last_active_project"),
                "cache_files": {
                    "home_cache": str(self.home_cache_file),
                    "local_cache": str(self.local_cache_file)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"列出项目失败: {e}"
            }
    
    def remove_project(self, project_name: str) -> Dict[str, Any]:
        """从缓存中移除项目"""
        try:
            cache_data = self._load_cache(self.home_cache_file)
            if not cache_data or "projects" not in cache_data:
                return {
                    "success": False,
                    "error": "缓存文件为空或无效"
                }
            
            if project_name not in cache_data["projects"]:
                return {
                    "success": False,
                    "error": f"项目 '{project_name}' 不在缓存中"
                }
            
            # 移除项目
            removed_project = cache_data["projects"].pop(project_name)
            
            # 如果是当前活跃项目，重置为None
            if cache_data.get("last_active_project") == project_name:
                cache_data["last_active_project"] = None
                # 如果还有其他项目，设置为最近访问的
                if cache_data["projects"]:
                    sorted_projects = sorted(
                        cache_data["projects"].items(),
                        key=lambda x: x[1].get("last_accessed", ""),
                        reverse=True
                    )
                    cache_data["last_active_project"] = sorted_projects[0][0]
            
            # 保存缓存
            home_saved = self._save_cache(self.home_cache_file, cache_data)
            local_saved = self._save_cache(self.local_cache_file, cache_data)
            
            return {
                "success": True,
                "removed_project": project_name,
                "removed_info": removed_project,
                "remaining_projects": len(cache_data["projects"]),
                "cache_files_updated": {
                    "home_cache": home_saved,
                    "local_cache": local_saved
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"移除项目失败: {e}"
            }


# 全局缓存管理器实例
_cache_manager = None


def get_cache_manager() -> PathCacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = PathCacheManager()
    return _cache_manager


def get_project_path_from_cache(project_name: str = None) -> str:
    """从缓存中获取项目路径（简化接口）"""
    cache_manager = get_cache_manager()
    result = cache_manager.get_project_path(project_name)
    
    if result["success"] and result.get("is_valid"):
        return result["project_info"]["path"]
    
    return None 