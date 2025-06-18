"""
DAG Planner 配置模块
管理 DAG Planner 专用的端口和服务配置
"""

import os
from typing import Dict, Any


class DAGPlannerConfig:
    """DAG Planner 专用配置类"""
    
    # 默认端口配置
    DEFAULT_WEB_PORT = 9005
    DEFAULT_SERVER_PORT = 9004
    DEFAULT_HOST = "127.0.0.1"
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = {
            "web_port": self._get_web_port(),
            "server_port": self._get_server_port(),
            "host": self._get_host(),
            "debug": self._get_debug_mode(),
        }
        return config
    
    def _get_web_port(self) -> int:
        """获取 Web UI 端口"""
        env_port = os.getenv("MCP_WEB_PORT")
        if env_port:
            try:
                port = int(env_port)
                if 1024 <= port <= 65535 or port == 0:
                    return port
            except ValueError:
                pass
        return self.DEFAULT_WEB_PORT
    
    def _get_server_port(self) -> int:
        """获取 MCP Server 端口"""
        env_port = os.getenv("MCP_SERVER_PORT")
        if env_port:
            try:
                port = int(env_port)
                if 1024 <= port <= 65535:
                    return port
            except ValueError:
                pass
        return self.DEFAULT_SERVER_PORT
    
    def _get_host(self) -> str:
        """获取服务器主机地址"""
        return os.getenv("MCP_HOST", self.DEFAULT_HOST)
    
    def _get_debug_mode(self) -> bool:
        """获取调试模式"""
        return os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes", "on")
    
    @property
    def web_port(self) -> int:
        """Web UI 端口"""
        return self._config["web_port"]
    
    @property
    def server_port(self) -> int:
        """MCP Server 端口"""
        return self._config["server_port"]
    
    @property
    def host(self) -> str:
        """服务器主机地址"""
        return self._config["host"]
    
    @property
    def debug(self) -> bool:
        """调试模式"""
        return self._config["debug"]
    
    def get_web_url(self) -> str:
        """获取 Web UI URL"""
        return f"http://{self.host}:{self.web_port}"
    
    def get_server_url(self) -> str:
        """获取 MCP Server URL"""
        return f"http://{self.host}:{self.server_port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._config.copy()


# 全局配置实例
_dag_config = None


def get_dag_config() -> DAGPlannerConfig:
    """获取 DAG Planner 配置实例"""
    global _dag_config
    if _dag_config is None:
        _dag_config = DAGPlannerConfig()
    return _dag_config 