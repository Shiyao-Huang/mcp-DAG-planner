"""
Version: v1.0.0
Author: AI Assistant + User
Date: 2024-12-20
Dependencies: pathlib, json, datetime
"""

"""
DAG数据存储管理器

```mermaid
graph TD
    A[DAGDataStorage] --> B[save_dag保存DAG]
    A --> C[load_dag加载DAG]
    A --> D[list_dags列出DAG]
    A --> E[delete_dag删除DAG]
    
    B --> B1[创建目录结构]
    B --> B2[写入JSON文件]
    B --> B3[创建备份]
    
    C --> C1[验证文件存在]
    C --> C2[读取JSON数据]
    C --> C3[数据反序列化]
    
    D --> D1[扫描DAG目录]
    D --> D2[获取文件元信息]
    D --> D3[返回DAG列表]
    
    E --> E1[删除主文件]
    E --> E2[清理备份]
    E --> E3[更新索引]
```

本文件实现DAG数据的持久化存储和管理功能。

核心功能：
- save_dag: 保存DAG数据到JSON文件
- load_dag: 从JSON文件加载DAG数据
- list_dags: 列出所有保存的DAG
- delete_dag: 删除指定的DAG
- backup_dag: 创建DAG备份
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import shutil
import hashlib


class DAGDataStorage:
    """DAG数据存储管理器"""
    
    def __init__(self, base_path: str = "dag_data"):
        """
        初始化存储管理器
        
        Args:
            base_path: 存储基础路径，可以是相对路径或绝对路径
        """
        from pathlib import Path
        
        # 判断是否为绝对路径
        base_path_obj = Path(base_path)
        if base_path_obj.is_absolute():
            # 如果是绝对路径，直接使用
            self.base_path = base_path_obj
        else:
            # 如果是相对路径，在当前工作目录下创建
            current_working_dir = Path.cwd().resolve()
            self.base_path = current_working_dir / base_path
        
        self.dags_path = self.base_path / "dags"
        self.backups_path = self.base_path / "backups"
        self.temp_path = self.base_path / "temp"
        
        print(f"🔍 当前工作目录: {Path.cwd()}")
        print(f"🔍 DAG存储基础路径: {self.base_path}")
        print(f"🔍 DAG文件路径: {self.dags_path}")
        print(f"🔍 备份路径: {self.backups_path}")
        print(f"🔍 临时路径: {self.temp_path}")
        
        # 创建必要的目录
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保所有必要的目录存在"""
        directories = [self.base_path, self.dags_path, self.backups_path, self.temp_path]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _generate_file_hash(self, data: Dict[str, Any]) -> str:
        """生成数据的哈希值用于文件命名"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    def save_dag(self, dag_data: Dict[str, Any], dag_id: Optional[str] = None) -> Dict[str, Any]:
        """
        保存DAG数据到文件
        
        Args:
            dag_data: DAG数据字典
            dag_id: 可选的DAG ID，如果不提供将自动生成
            
        Returns:
            Dict包含保存结果信息
        """
        try:
            print(f"🔥 开始保存DAG数据，数据大小: {len(str(dag_data))} 字符")
            print(f"🔥 存储基础路径: {self.base_path}")
            print(f"🔥 DAG路径: {self.dags_path}")
            
            # 添加时间戳
            dag_data["timestamp"] = datetime.now().isoformat()
            
            # 生成文件名
            if not dag_id:
                dag_id = self._generate_file_hash(dag_data)
            
            layer_type = dag_data.get("layer_type", "unknown")
            filename = f"{layer_type}_layer_{dag_id}.json"
            file_path = self.dags_path / filename
            
            print(f"🔥 准备写入文件: {file_path}")
            
            # 确保目录存在
            self.dags_path.mkdir(parents=True, exist_ok=True)
            
            # 如果文件已存在，创建备份
            if file_path.exists():
                print(f"🔥 文件已存在，创建备份")
                self._create_backup(file_path)
            
            # 保存主文件
            print(f"🔥 正在写入JSON数据...")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dag_data, f, ensure_ascii=False, indent=2)
            
            # 验证文件是否真的被创建
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"🔥 文件成功创建! 大小: {file_size} 字节")
            else:
                print(f"🔥 错误: 文件没有被创建!")
                return {
                    "success": False,
                    "error": "文件创建失败",
                    "error_type": "file_creation_failed"
                }
            
            # 返回保存信息
            result = {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "dag_id": dag_id,
                "size_bytes": file_path.stat().st_size,
                "backup_created": file_path.with_suffix('.backup.json').exists()
            }
            
            print(f"✅ DAG数据已保存到: {file_path}")
            return result
            
        except Exception as e:
            print(f"🔥 保存过程中发生错误: {e}")
            print(f"🔥 错误类型: {type(e).__name__}")
            import traceback
            print(f"🔥 堆栈跟踪: {traceback.format_exc()}")
            
            error_result = {
                "success": False,
                "error": str(e),
                "error_type": "storage_error"
            }
            print(f"❌ 保存DAG数据失败: {e}")
            return error_result
    
    def load_dag(self, filename: str) -> Dict[str, Any]:
        """
        从文件加载DAG数据
        
        Args:
            filename: 要加载的文件名
            
        Returns:
            Dict包含DAG数据或错误信息
        """
        try:
            file_path = self.dags_path / filename
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {filename}",
                    "error_type": "file_not_found"
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                dag_data = json.load(f)
            
            result = {
                "success": True,
                "data": dag_data,
                "filename": filename,
                "file_path": str(file_path),
                "loaded_at": datetime.now().isoformat()
            }
            
            print(f"✅ DAG数据已从文件加载: {file_path}")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "error_type": "load_error"
            }
            print(f"❌ 加载DAG数据失败: {e}")
            return error_result
    
    def list_dags(self) -> Dict[str, Any]:
        """
        列出所有保存的DAG文件
        
        Returns:
            Dict包含DAG文件列表
        """
        try:
            dag_files = []
            
            for file_path in self.dags_path.glob("*.json"):
                if not file_path.name.endswith('.backup.json'):
                    stat = file_path.stat()
                    dag_files.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
            
            # 按修改时间排序
            dag_files.sort(key=lambda x: x["modified_at"], reverse=True)
            
            return {
                "success": True,
                "dags": dag_files,
                "total_count": len(dag_files),
                "scan_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "list_error"
            }
    
    def delete_dag(self, filename: str) -> Dict[str, Any]:
        """
        删除指定的DAG文件
        
        Args:
            filename: 要删除的文件名
            
        Returns:
            Dict包含删除结果
        """
        try:
            file_path = self.dags_path / filename
            backup_path = file_path.with_suffix('.backup.json')
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {filename}",
                    "error_type": "file_not_found"
                }
            
            # 删除主文件
            file_path.unlink()
            
            # 删除备份文件（如果存在）
            backup_deleted = False
            if backup_path.exists():
                backup_path.unlink()
                backup_deleted = True
            
            return {
                "success": True,
                "filename": filename,
                "backup_deleted": backup_deleted,
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "delete_error"
            }
    
    def _create_backup(self, file_path: Path) -> bool:
        """
        创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            backup_path = file_path.with_suffix('.backup.json')
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"⚠️ 创建备份失败: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            Dict包含存储统计信息
        """
        try:
            dag_files = list(self.dags_path.glob("*.json"))
            backup_files = list(self.backups_path.glob("*.json"))
            temp_files = list(self.temp_path.glob("*"))
            
            total_size = sum(f.stat().st_size for f in dag_files)
            backup_size = sum(f.stat().st_size for f in backup_files)
            
            return {
                "success": True,
                "stats": {
                    "total_dags": len([f for f in dag_files if not f.name.endswith('.backup.json')]),
                    "backup_files": len(backup_files),
                    "temp_files": len(temp_files),
                    "total_size_bytes": total_size,
                    "backup_size_bytes": backup_size,
                    "storage_path": str(self.base_path)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "stats_error"
            }


# 全局存储实例
_storage_instance = None


def get_storage(project_path: str = None) -> DAGDataStorage:
    """获取全局存储实例，优先使用YAML缓存中的项目路径"""
    global _storage_instance
    if _storage_instance is None:
        if project_path:
            # 使用指定的项目路径
            edata_path = Path(project_path) / ".EDATA"
            _storage_instance = DAGDataStorage(str(edata_path))
        else:
            # 优先从YAML缓存获取项目路径
            try:
                from .path_cache import get_project_path_from_cache
                cached_project_path = get_project_path_from_cache()
                
                if cached_project_path:
                    edata_path = Path(cached_project_path) / ".EDATA"
                    print(f"🎯 从缓存获取项目路径: {cached_project_path}")
                    _storage_instance = DAGDataStorage(str(edata_path))
                else:
                    # 如果缓存中没有，使用fallback机制
                    current_dir = Path.cwd()
                    
                    possible_paths = [
                        current_dir / ".EDATA", 
                        current_dir.parent / ".EDATA",
                        Path("/Users/swmt/Desktop/hsy/大模型/MCP-some/.EDATA")  # 默认项目路径
                    ]
                    
                    edata_path = None
                    for path in possible_paths:
                        if path.exists() and (path / "config.json").exists():
                            edata_path = path
                            print(f"🔍 使用fallback路径: {path.parent}")
                            break
                    
                    if edata_path:
                        _storage_instance = DAGDataStorage(str(edata_path))
                    else:
                        # 最后创建在当前目录下
                        print("⚠️ 未找到有效路径，在当前目录创建.EDATA")
                        _storage_instance = DAGDataStorage(".EDATA")
                        
            except Exception as e:
                print(f"⚠️ 缓存读取失败，使用fallback: {e}")
                # 发生错误时使用原来的fallback机制
                current_dir = Path.cwd()
                
                possible_paths = [
                    current_dir / ".EDATA", 
                    current_dir.parent / ".EDATA",
                    Path("/Users/swmt/Desktop/hsy/大模型/MCP-some/.EDATA")
                ]
                
                edata_path = None
                for path in possible_paths:
                    if path.exists() and (path / "config.json").exists():
                        edata_path = path
                        break
                
                if edata_path:
                    _storage_instance = DAGDataStorage(str(edata_path))
                else:
                    _storage_instance = DAGDataStorage(".EDATA")
    
    return _storage_instance 