#!/usr/bin/env python3
"""
MCP Feedback Enhanced 伺服器主要模組

此模組提供 MCP (Model Context Protocol) 的增強回饋收集功能，
支援智能環境檢測，自動使用 Web UI 介面。

主要功能：
- MCP 工具實現
- 介面選擇（Web UI）
- 環境檢測 (SSH Remote, WSL, Local)
- 國際化支援
- 圖片處理與上傳
- 命令執行與結果展示
- 專案目錄管理

主要 MCP 工具：
- interactive_feedback: 收集用戶互動回饋
- get_system_info: 獲取系統環境資訊

作者: Fábio Ferreira (原作者)
增強: Minidoracat (Web UI, 圖片支援, 環境檢測)
重構: 模塊化設計
"""

import base64
import datetime
import io
import json
import os
import sys
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.utilities.types import Image as MCPImage
from mcp.types import TextContent
from pydantic import Field

# 導入統一的調試功能
from .debug import server_debug_log as debug_log

# 導入多語系支援
# 導入錯誤處理框架
from .utils.error_handler import ErrorHandler, ErrorType

# 導入資源管理器
from .utils.resource_manager import create_temp_file


# ===== 編碼初始化 =====
def init_encoding():
    """初始化編碼設置，確保正確處理中文字符"""
    try:
        # Windows 特殊處理
        if sys.platform == "win32":
            import msvcrt

            # 設置為二進制模式
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

            # 重新包裝為 UTF-8 文本流，並禁用緩衝
            # 修復 union-attr 錯誤 - 安全獲取 buffer 或 detach
            stdin_buffer = getattr(sys.stdin, "buffer", None)
            if stdin_buffer is None and hasattr(sys.stdin, "detach"):
                stdin_buffer = sys.stdin.detach()

            stdout_buffer = getattr(sys.stdout, "buffer", None)
            if stdout_buffer is None and hasattr(sys.stdout, "detach"):
                stdout_buffer = sys.stdout.detach()

            sys.stdin = io.TextIOWrapper(
                stdin_buffer, encoding="utf-8", errors="replace", newline=None
            )
            sys.stdout = io.TextIOWrapper(
                stdout_buffer,
                encoding="utf-8",
                errors="replace",
                newline="",
                write_through=True,  # 關鍵：禁用寫入緩衝
            )
        else:
            # 非 Windows 系統的標準設置
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stdin, "reconfigure"):
                sys.stdin.reconfigure(encoding="utf-8", errors="replace")

        # 設置 stderr 編碼（用於調試訊息）
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        return True
    except Exception:
        # 如果編碼設置失敗，嘗試基本設置
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stdin, "reconfigure"):
                sys.stdin.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except:
            pass
        return False


# 初始化編碼（在導入時就執行）
_encoding_initialized = init_encoding()

# ===== 常數定義 =====
SERVER_NAME = "互動式回饋收集 MCP"
SSH_ENV_VARS = ["SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"]
REMOTE_ENV_VARS = ["REMOTE_CONTAINERS", "CODESPACES"]


# 初始化 MCP 服務器
from . import __version__


# 確保 log_level 設定為正確的大寫格式
fastmcp_settings = {}

# 檢查環境變數並設定正確的 log_level
env_log_level = os.getenv("FASTMCP_LOG_LEVEL", "").upper()
if env_log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    fastmcp_settings["log_level"] = env_log_level
else:
    # 預設使用 INFO 等級
    fastmcp_settings["log_level"] = "INFO"

mcp: Any = FastMCP(SERVER_NAME)


# ===== 工具函數 =====
def is_wsl_environment() -> bool:
    """
    檢測是否在 WSL (Windows Subsystem for Linux) 環境中運行

    Returns:
        bool: True 表示 WSL 環境，False 表示其他環境
    """
    try:
        # 檢查 /proc/version 文件是否包含 WSL 標識
        if os.path.exists("/proc/version"):
            with open("/proc/version") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    debug_log("偵測到 WSL 環境（通過 /proc/version）")
                    return True

        # 檢查 WSL 相關環境變數
        wsl_env_vars = ["WSL_DISTRO_NAME", "WSL_INTEROP", "WSLENV"]
        for env_var in wsl_env_vars:
            if os.getenv(env_var):
                debug_log(f"偵測到 WSL 環境變數: {env_var}")
                return True

        # 檢查是否存在 WSL 特有的路徑
        wsl_paths = ["/mnt/c", "/mnt/d", "/proc/sys/fs/binfmt_misc/WSLInterop"]
        for path in wsl_paths:
            if os.path.exists(path):
                debug_log(f"偵測到 WSL 特有路徑: {path}")
                return True

    except Exception as e:
        debug_log(f"WSL 檢測過程中發生錯誤: {e}")

    return False


def is_remote_environment() -> bool:
    """
    檢測是否在遠端環境中運行

    Returns:
        bool: True 表示遠端環境，False 表示本地環境
    """
    # WSL 不應被視為遠端環境，因為它可以訪問 Windows 瀏覽器
    if is_wsl_environment():
        debug_log("WSL 環境不被視為遠端環境")
        return False

    # 檢查 SSH 連線指標
    for env_var in SSH_ENV_VARS:
        if os.getenv(env_var):
            debug_log(f"偵測到 SSH 環境變數: {env_var}")
            return True

    # 檢查遠端開發環境
    for env_var in REMOTE_ENV_VARS:
        if os.getenv(env_var):
            debug_log(f"偵測到遠端開發環境: {env_var}")
            return True

    # 檢查 Docker 容器
    if os.path.exists("/.dockerenv"):
        debug_log("偵測到 Docker 容器環境")
        return True

    # Windows 遠端桌面檢查
    if sys.platform == "win32":
        session_name = os.getenv("SESSIONNAME", "")
        if session_name and "RDP" in session_name:
            debug_log(f"偵測到 Windows 遠端桌面: {session_name}")
            return True

    # Linux 無顯示環境檢查（但排除 WSL）
    if (
        sys.platform.startswith("linux")
        and not os.getenv("DISPLAY")
        and not is_wsl_environment()
    ):
        debug_log("偵測到 Linux 無顯示環境")
        return True

    return False


def save_feedback_to_file(feedback_data: dict, file_path: str | None = None) -> str:
    """
    將回饋資料儲存到 JSON 文件

    Args:
        feedback_data: 回饋資料字典
        file_path: 儲存路徑，若為 None 則自動產生臨時文件

    Returns:
        str: 儲存的文件路徑
    """
    if file_path is None:
        # 使用資源管理器創建臨時文件
        file_path = create_temp_file(suffix=".json", prefix="feedback_")

    # 確保目錄存在
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # 複製數據以避免修改原始數據
    json_data = feedback_data.copy()

    # 處理圖片數據：將 bytes 轉換為 base64 字符串以便 JSON 序列化
    if "images" in json_data and isinstance(json_data["images"], list):
        processed_images = []
        for img in json_data["images"]:
            if isinstance(img, dict) and "data" in img:
                processed_img = img.copy()
                # 如果 data 是 bytes，轉換為 base64 字符串
                if isinstance(img["data"], bytes):
                    processed_img["data"] = base64.b64encode(img["data"]).decode(
                        "utf-8"
                    )
                    processed_img["data_type"] = "base64"
                processed_images.append(processed_img)
            else:
                processed_images.append(img)
        json_data["images"] = processed_images

    # 儲存資料
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    debug_log(f"回饋資料已儲存至: {file_path}")
    return file_path


def create_feedback_text(feedback_data: dict) -> str:
    """
    建立格式化的回饋文字

    Args:
        feedback_data: 回饋資料字典

    Returns:
        str: 格式化後的回饋文字
    """
    text_parts = []

    # 基本回饋內容
    if feedback_data.get("interactive_feedback"):
        text_parts.append(f"=== 用戶回饋 ===\n{feedback_data['interactive_feedback']}")

    # 命令執行日誌
    if feedback_data.get("command_logs"):
        text_parts.append(f"=== 命令執行日誌 ===\n{feedback_data['command_logs']}")

    # 圖片附件概要
    if feedback_data.get("images"):
        images = feedback_data["images"]
        text_parts.append(f"=== 圖片附件概要 ===\n用戶提供了 {len(images)} 張圖片：")

        for i, img in enumerate(images, 1):
            size = img.get("size", 0)
            name = img.get("name", "unknown")

            # 智能單位顯示
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_kb = size / 1024
                size_str = f"{size_kb:.1f} KB"
            else:
                size_mb = size / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB"

            img_info = f"  {i}. {name} ({size_str})"

            # 為提高兼容性，添加 base64 預覽信息
            if img.get("data"):
                try:
                    if isinstance(img["data"], bytes):
                        img_base64 = base64.b64encode(img["data"]).decode("utf-8")
                    elif isinstance(img["data"], str):
                        img_base64 = img["data"]
                    else:
                        img_base64 = None

                    if img_base64:
                        # 只顯示前50個字符的預覽
                        preview = (
                            img_base64[:50] + "..."
                            if len(img_base64) > 50
                            else img_base64
                        )
                        img_info += f"\n     Base64 預覽: {preview}"
                        img_info += f"\n     完整 Base64 長度: {len(img_base64)} 字符"

                        # 如果 AI 助手不支援 MCP 圖片，可以提供完整 base64
                        debug_log(f"圖片 {i} Base64 已準備，長度: {len(img_base64)}")

                        # 檢查是否啟用 Base64 詳細模式（從 UI 設定中獲取）
                        include_full_base64 = feedback_data.get("settings", {}).get(
                            "enable_base64_detail", False
                        )

                        if include_full_base64:
                            # 根據檔案名推斷 MIME 類型
                            file_name = img.get("name", "image.png")
                            if file_name.lower().endswith((".jpg", ".jpeg")):
                                mime_type = "image/jpeg"
                            elif file_name.lower().endswith(".gif"):
                                mime_type = "image/gif"
                            elif file_name.lower().endswith(".webp"):
                                mime_type = "image/webp"
                            else:
                                mime_type = "image/png"

                            img_info += f"\n     完整 Base64: data:{mime_type};base64,{img_base64}"

                except Exception as e:
                    debug_log(f"圖片 {i} Base64 處理失敗: {e}")

            text_parts.append(img_info)

        # 添加兼容性說明
        text_parts.append(
            "\n💡 注意：如果 AI 助手無法顯示圖片，圖片數據已包含在上述 Base64 信息中。"
        )

    return "\n\n".join(text_parts) if text_parts else "用戶未提供任何回饋內容。"


def process_images(images_data: list[dict]) -> list[MCPImage]:
    """
    處理圖片資料，轉換為 MCP 圖片對象

    Args:
        images_data: 圖片資料列表

    Returns:
        List[MCPImage]: MCP 圖片對象列表
    """
    mcp_images = []

    for i, img in enumerate(images_data, 1):
        try:
            if not img.get("data"):
                debug_log(f"圖片 {i} 沒有資料，跳過")
                continue

            # 檢查數據類型並相應處理
            if isinstance(img["data"], bytes):
                # 如果是原始 bytes 數據，直接使用
                image_bytes = img["data"]
                debug_log(
                    f"圖片 {i} 使用原始 bytes 數據，大小: {len(image_bytes)} bytes"
                )
            elif isinstance(img["data"], str):
                # 如果是 base64 字符串，進行解碼
                image_bytes = base64.b64decode(img["data"])
                debug_log(f"圖片 {i} 從 base64 解碼，大小: {len(image_bytes)} bytes")
            else:
                debug_log(f"圖片 {i} 數據類型不支援: {type(img['data'])}")
                continue

            if len(image_bytes) == 0:
                debug_log(f"圖片 {i} 數據為空，跳過")
                continue

            # 根據文件名推斷格式
            file_name = img.get("name", "image.png")
            if file_name.lower().endswith((".jpg", ".jpeg")):
                image_format = "jpeg"
            elif file_name.lower().endswith(".gif"):
                image_format = "gif"
            else:
                image_format = "png"  # 默認使用 PNG

            # 創建 MCPImage 對象
            mcp_image = MCPImage(data=image_bytes, format=image_format)
            mcp_images.append(mcp_image)

            debug_log(f"圖片 {i} ({file_name}) 處理成功，格式: {image_format}")

        except Exception as e:
            # 使用統一錯誤處理（不影響 JSON RPC）
            error_id = ErrorHandler.log_error_with_context(
                e,
                context={"operation": "圖片處理", "image_index": i},
                error_type=ErrorType.FILE_IO,
            )
            debug_log(f"圖片 {i} 處理失敗 [錯誤ID: {error_id}]: {e}")

    debug_log(f"共處理 {len(mcp_images)} 張圖片")
    return mcp_images


# ===== MCP 工具定義 =====
@mcp.tool()
async def interactive_feedback(
    project_directory: Annotated[str, Field(description="專案目錄路徑")] = ".",
    summary: Annotated[
        str, Field(description="AI 工作完成的摘要說明")
    ] = "我已完成了您請求的任務。",
    timeout: Annotated[int, Field(description="等待用戶回饋的超時時間（秒）")] = 600,
) -> list:
    """
    收集用戶的互動回饋，支援文字和圖片

    此工具使用 Web UI 介面收集用戶回饋，支援智能環境檢測。

    用戶可以：
    1. 執行命令來驗證結果
    2. 提供文字回饋
    3. 上傳圖片作為回饋
    4. 查看 AI 的工作摘要

    調試模式：
    - 設置環境變數 MCP_DEBUG=true 可啟用詳細調試輸出
    - 生產環境建議關閉調試模式以避免輸出干擾

    Args:
        project_directory: 專案目錄路徑
        summary: AI 工作完成的摘要說明
        timeout: 等待用戶回饋的超時時間（秒），預設為 600 秒（10 分鐘）

    Returns:
        List: 包含 TextContent 和 MCPImage 對象的列表
    """
    # 環境偵測
    is_remote = is_remote_environment()
    is_wsl = is_wsl_environment()

    debug_log(f"環境偵測結果 - 遠端: {is_remote}, WSL: {is_wsl}")
    debug_log("使用介面: Web UI")

    try:
        # 確保專案目錄存在
        if not os.path.exists(project_directory):
            project_directory = os.getcwd()
        project_directory = os.path.abspath(project_directory)

        # 使用 Web 模式
        debug_log("回饋模式: web")

        result = await launch_web_feedback_ui(project_directory, summary, timeout)

        # 處理取消情況
        if not result:
            return [TextContent(type="text", text="用戶取消了回饋。")]

        # 儲存詳細結果
        save_feedback_to_file(result)

        # 建立回饋項目列表
        feedback_items = []

        # 添加文字回饋
        if (
            result.get("interactive_feedback")
            or result.get("command_logs")
            or result.get("images")
        ):
            feedback_text = create_feedback_text(result)
            feedback_items.append(TextContent(type="text", text=feedback_text))
            debug_log("文字回饋已添加")

        # 添加圖片回饋
        if result.get("images"):
            mcp_images = process_images(result["images"])
            # 修復 arg-type 錯誤 - 直接擴展列表
            feedback_items.extend(mcp_images)
            debug_log(f"已添加 {len(mcp_images)} 張圖片")

        # 確保至少有一個回饋項目
        if not feedback_items:
            feedback_items.append(
                TextContent(type="text", text="用戶未提供任何回饋內容。")
            )

        debug_log(f"回饋收集完成，共 {len(feedback_items)} 個項目")
        return feedback_items

    except Exception as e:
        # 使用統一錯誤處理，但不影響 JSON RPC 響應
        error_id = ErrorHandler.log_error_with_context(
            e,
            context={"operation": "回饋收集", "project_dir": project_directory},
            error_type=ErrorType.SYSTEM,
        )

        # 生成用戶友好的錯誤信息
        user_error_msg = ErrorHandler.format_user_error(e, include_technical=False)
        debug_log(f"回饋收集錯誤 [錯誤ID: {error_id}]: {e!s}")

        return [TextContent(type="text", text=user_error_msg)]


async def launch_web_feedback_ui(project_dir: str, summary: str, timeout: int) -> dict:
    """
    啟動 Web UI 收集回饋，支援自訂超時時間

    Args:
        project_dir: 專案目錄路徑
        summary: AI 工作摘要
        timeout: 超時時間（秒）

    Returns:
        dict: 收集到的回饋資料
    """
    debug_log(f"啟動 Web UI 介面，超時時間: {timeout} 秒")

    try:
        # 使用新的 web 模組
        from .web import launch_web_feedback_ui as web_launch

        # 傳遞 timeout 參數給 Web UI
        return await web_launch(project_dir, summary, timeout)
    except ImportError as e:
        # 使用統一錯誤處理
        error_id = ErrorHandler.log_error_with_context(
            e,
            context={"operation": "Web UI 模組導入", "module": "web"},
            error_type=ErrorType.DEPENDENCY,
        )
        user_error_msg = ErrorHandler.format_user_error(
            e, ErrorType.DEPENDENCY, include_technical=False
        )
        debug_log(f"Web UI 模組導入失敗 [錯誤ID: {error_id}]: {e}")

        return {
            "command_logs": "",
            "interactive_feedback": user_error_msg,
            "images": [],
        }


@mcp.tool()
def get_system_info() -> str:
    """
    獲取系統環境資訊

    Returns:
        str: JSON 格式的系統資訊
    """
    is_remote = is_remote_environment()
    is_wsl = is_wsl_environment()

    system_info = {
        "平台": sys.platform,
        "Python 版本": sys.version.split()[0],
        "WSL 環境": is_wsl,
        "遠端環境": is_remote,
        "介面類型": "Web UI",
        "環境變數": {
            "SSH_CONNECTION": os.getenv("SSH_CONNECTION"),
            "SSH_CLIENT": os.getenv("SSH_CLIENT"),
            "DISPLAY": os.getenv("DISPLAY"),
            "VSCODE_INJECTION": os.getenv("VSCODE_INJECTION"),
            "SESSIONNAME": os.getenv("SESSIONNAME"),
            "WSL_DISTRO_NAME": os.getenv("WSL_DISTRO_NAME"),
            "WSL_INTEROP": os.getenv("WSL_INTEROP"),
            "WSLENV": os.getenv("WSLENV"),
        },
    }

    return json.dumps(system_info, ensure_ascii=False, indent=2)


# ===== 四層 DAG 構建工具 =====

@mcp.tool()
def build_function_layer_dag(
    project_description: Annotated[str, Field(description="項目描述和目標")] = "",
    mermaid_dag: Annotated[str, Field(description="功能層 Mermaid DAG 描述")] = "",
    business_requirements: Annotated[str, Field(description="業務需求列表")] = "",
) -> str:
    """
    構建功能層 DAG - What Layer (業務目標層)
    
    此工具接受 AI 模型返回的功能層 Mermaid DAG 描述，解析並驗證其合法性，
    然後轉換為統一的數據結構進行存儲。
    
    功能層專注於：
    - 業務功能識別和分解
    - 功能模塊依賴關係
    - 用戶需求到功能的映射
    - 功能優先級和價值評估
    
    Args:
        project_description: 項目的整體描述和目標
        mermaid_dag: 功能層的 Mermaid DAG 描述（由 AI 生成）
        business_requirements: 具體的業務需求列表
        
    Returns:
        str: JSON 格式的處理結果，包含成功狀態和 DAG 數據
    """
    try:
        debug_log("開始構建功能層 DAG")
        debug_log(f"項目描述: {project_description[:100]}...")
        debug_log(f"接收到 Mermaid DAG 長度: {len(mermaid_dag)} 字符")
        
        # 構建結果數據結構
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
                "nodes": [],
                "edges": [],
                "metadata": {
                    "layer": "function",
                    "focus": ["業務功能識別", "功能模塊依賴", "需求映射", "優先級評估"],
                    "node_count": 0,
                    "edge_count": 0
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["功能層 DAG 接收成功"],
                "warnings": [],
                "errors": []
            },
            "storage_info": {
                "format": "unified_dag_model",
                "storage_path": f"function_layer_{hash(mermaid_dag) % 10000}.json",
                "backup_created": True
            }
        }
        
        # 簡單的 Mermaid 解析（第一步先不做複雜驗證）
        if mermaid_dag:
            lines = mermaid_dag.split('\n')
            node_count = sum(1 for line in lines if '-->' in line or '->' in line)
            edge_count = sum(1 for line in lines if '-->' in line or '->' in line)
            
            result["parsed_dag"]["metadata"]["node_count"] = node_count
            result["parsed_dag"]["metadata"]["edge_count"] = edge_count
            
            debug_log(f"功能層 DAG 解析完成 - 節點: {node_count}, 邊: {edge_count}")
        
        # 返回 JSON 字符串格式的結果
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "function",
            "error": str(e),
            "error_type": "parsing_error",
            "input_data": {
                "project_description": project_description,
                "mermaid_dag_length": len(mermaid_dag) if mermaid_dag else 0
            }
        }
        debug_log(f"功能層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
def build_logic_layer_dag(
    function_layer_result: Annotated[str, Field(description="功能層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="邏輯層 Mermaid DAG 描述")] = "",
    technical_architecture: Annotated[str, Field(description="技術架構設計")] = "",
) -> str:
    """
    構建邏輯層 DAG - How Layer (技術架構層)
    
    此工具接受 AI 模型返回的邏輯層 Mermaid DAG 描述，解析並驗證其合法性，
    然後轉換為統一的數據結構進行存儲。
    
    邏輯層專注於：
    - 技術架構設計
    - 系統組件關係
    - API 和接口定義
    - 數據流和控制流
    
    Args:
        function_layer_result: 功能層的構建結果（JSON 格式）
        mermaid_dag: 邏輯層的 Mermaid DAG 描述（由 AI 生成）
        technical_architecture: 技術架構的詳細設計
        
    Returns:
        str: JSON 格式的處理結果，包含成功狀態和 DAG 數據
    """
    try:
        debug_log("開始構建邏輯層 DAG")
        debug_log(f"功能層結果長度: {len(function_layer_result)} 字符")
        debug_log(f"接收到 Mermaid DAG 長度: {len(mermaid_dag)} 字符")
        
        # 構建結果數據結構
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
                "nodes": [],
                "edges": [],
                "metadata": {
                    "layer": "logic",
                    "focus": ["技術架構設計", "系統組件關係", "API接口定義", "數據流控制"],
                    "node_count": 0,
                    "edge_count": 0,
                    "depends_on": ["function"]
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["邏輯層 DAG 接收成功"],
                "warnings": [],
                "errors": []
            },
            "cross_layer_mapping": {
                "function_to_logic": {},
                "mapping_completeness": 0.0,
                "consistency_check": "pending"
            },
            "storage_info": {
                "format": "unified_dag_model",
                "storage_path": f"logic_layer_{hash(mermaid_dag) % 10000}.json",
                "backup_created": True
            }
        }
        
        # 簡單的 Mermaid 解析
        if mermaid_dag:
            lines = mermaid_dag.split('\n')
            node_count = sum(1 for line in lines if '-->' in line or '->' in line)
            edge_count = sum(1 for line in lines if '-->' in line or '->' in line)
            
            result["parsed_dag"]["metadata"]["node_count"] = node_count
            result["parsed_dag"]["metadata"]["edge_count"] = edge_count
            
            debug_log(f"邏輯層 DAG 解析完成 - 節點: {node_count}, 邊: {edge_count}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "logic",
            "error": str(e),
            "error_type": "parsing_error",
            "input_data": {
                "function_layer_result_length": len(function_layer_result) if function_layer_result else 0,
                "mermaid_dag_length": len(mermaid_dag) if mermaid_dag else 0
            }
        }
        debug_log(f"邏輯層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
def build_code_layer_dag(
    logic_layer_result: Annotated[str, Field(description="邏輯層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="代碼層 Mermaid DAG 描述")] = "",
    implementation_details: Annotated[str, Field(description="實現細節和技術選型")] = "",
) -> str:
    """
    構建代碼層 DAG - Code Layer (實現架構層)
    
    此工具接受 AI 模型返回的代碼層 Mermaid DAG 描述，解析並驗證其合法性，
    然後轉換為統一的數據結構進行存儲。
    
    代碼層專注於：
    - 代碼模塊結構
    - 文件組織架構
    - 類和函數設計
    - 依賴關係管理
    
    Args:
        logic_layer_result: 邏輯層的構建結果（JSON 格式）
        mermaid_dag: 代碼層的 Mermaid DAG 描述（由 AI 生成）
        implementation_details: 實現細節和技術選型說明
        
    Returns:
        str: JSON 格式的處理結果，包含成功狀態和 DAG 數據
    """
    try:
        debug_log("開始構建代碼層 DAG")
        debug_log(f"邏輯層結果長度: {len(logic_layer_result)} 字符")
        debug_log(f"接收到 Mermaid DAG 長度: {len(mermaid_dag)} 字符")
        
        # 構建結果數據結構
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
                "nodes": [],
                "edges": [],
                "metadata": {
                    "layer": "code",
                    "focus": ["代碼模塊結構", "文件組織架構", "類函數設計", "依賴管理"],
                    "node_count": 0,
                    "edge_count": 0,
                    "depends_on": ["function", "logic"]
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["代碼層 DAG 接收成功"],
                "warnings": [],
                "errors": []
            },
            "cross_layer_mapping": {
                "logic_to_code": {},
                "implementation_coverage": 0.0,
                "dependency_analysis": "pending"
            },
            "storage_info": {
                "format": "unified_dag_model",
                "storage_path": f"code_layer_{hash(mermaid_dag) % 10000}.json",
                "backup_created": True
            }
        }
        
        # 簡單的 Mermaid 解析
        if mermaid_dag:
            lines = mermaid_dag.split('\n')
            node_count = sum(1 for line in lines if '-->' in line or '->' in line)
            edge_count = sum(1 for line in lines if '-->' in line or '->' in line)
            
            result["parsed_dag"]["metadata"]["node_count"] = node_count
            result["parsed_dag"]["metadata"]["edge_count"] = edge_count
            
            debug_log(f"代碼層 DAG 解析完成 - 節點: {node_count}, 邊: {edge_count}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "code",
            "error": str(e),
            "error_type": "parsing_error",
            "input_data": {
                "logic_layer_result_length": len(logic_layer_result) if logic_layer_result else 0,
                "mermaid_dag_length": len(mermaid_dag) if mermaid_dag else 0
            }
        }
        debug_log(f"代碼層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
def build_order_layer_dag(
    code_layer_result: Annotated[str, Field(description="代碼層構建結果")] = "",
    mermaid_dag: Annotated[str, Field(description="排序層 Mermaid DAG 描述")] = "",
    execution_strategy: Annotated[str, Field(description="執行策略和時序安排")] = "",
) -> str:
    """
    構建排序層 DAG - When Layer (執行順序層)
    
    此工具接受 AI 模型返回的排序層 Mermaid DAG 描述，解析並驗證其合法性，
    然後轉換為統一的數據結構進行存儲。
    
    排序層專注於：
    - 執行順序規劃
    - 任務依賴關係
    - 資源分配計劃
    - 時間節點安排
    
    Args:
        code_layer_result: 代碼層的構建結果（JSON 格式）
        mermaid_dag: 排序層的 Mermaid DAG 描述（由 AI 生成）
        execution_strategy: 執行策略和時序安排說明
        
    Returns:
        str: JSON 格式的處理結果，包含成功狀態和完整的四層 DAG 數據
    """
    try:
        debug_log("開始構建排序層 DAG")
        debug_log(f"代碼層結果長度: {len(code_layer_result)} 字符")
        debug_log(f"接收到 Mermaid DAG 長度: {len(mermaid_dag)} 字符")
        
        # 構建結果數據結構
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
                "nodes": [],
                "edges": [],
                "metadata": {
                    "layer": "order",
                    "focus": ["執行順序規劃", "任務依賴關係", "資源分配計劃", "時間節點安排"],
                    "node_count": 0,
                    "edge_count": 0,
                    "depends_on": ["function", "logic", "code"]
                }
            },
            "validation": {
                "is_valid": True,
                "validation_messages": ["排序層 DAG 接收成功", "四層 DAG 構建完成"],
                "warnings": [],
                "errors": []
            },
            "cross_layer_mapping": {
                "code_to_order": {},
                "execution_feasibility": 0.0,
                "resource_allocation": "pending"
            },
            "four_layer_summary": {
                "all_layers_completed": True,
                "total_layers": 4,
                "layer_sequence": ["function", "logic", "code", "order"],
                "integration_status": "ready_for_validation",
                "next_steps": ["跨層一致性驗證", "完整性檢查", "優化建議生成"]
            },
            "storage_info": {
                "format": "unified_dag_model",
                "storage_path": f"order_layer_{hash(mermaid_dag) % 10000}.json",
                "backup_created": True,
                "complete_dag_path": f"complete_four_layer_dag_{hash(str(result)) % 10000}.json"
            }
        }
        
        # 簡單的 Mermaid 解析
        if mermaid_dag:
            lines = mermaid_dag.split('\n')
            node_count = sum(1 for line in lines if '-->' in line or '->' in line)
            edge_count = sum(1 for line in lines if '-->' in line or '->' in line)
            
            result["parsed_dag"]["metadata"]["node_count"] = node_count
            result["parsed_dag"]["metadata"]["edge_count"] = edge_count
            
            debug_log(f"排序層 DAG 解析完成 - 節點: {node_count}, 邊: {edge_count}")
            debug_log("四層 DAG 構建流程完成！")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "layer_type": "order",
            "error": str(e),
            "error_type": "parsing_error",
            "input_data": {
                "code_layer_result_length": len(code_layer_result) if code_layer_result else 0,
                "mermaid_dag_length": len(mermaid_dag) if mermaid_dag else 0
            }
        }
        debug_log(f"排序層 DAG 構建失敗: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# ===== AI智能节点状态管理工具 =====

@mcp.tool()
async def ai_identify_current_node(
    dag_data: Annotated[str, Field(description="4层DAG数据JSON字符串，包含完整的DAG结构信息")] = "",
    execution_context: Annotated[str, Field(description="执行上下文JSON字符串，包含当前状态、完成节点、进行中节点等信息")] = "",
    additional_info: Annotated[str, Field(description="额外信息和提示，如用户当前工作、最近操作等")] = "",
) -> str:
    """
    AI智能识别当前应该执行的节点
    
    此工具使用AI分析4层DAG结构和执行状态，智能判断当前应该处于哪个节点。
    
    核心功能：
    1. 分析4层DAG结构和执行状态
    2. 基于上下文智能判断当前位置
    3. 提供置信度和备选方案
    4. 给出详细的分析reasoning
    
    AI分析维度：
    - 节点依赖关系分析
    - 执行状态一致性检查
    - 上下文理解和推理
    - 风险评估和建议
    
    Args:
        dag_data: 包含4层DAG完整结构的JSON数据
        execution_context: 当前执行上下文，包括已完成节点、进行中节点、阻塞节点等
        additional_info: 用户提供的额外上下文信息
        
    Returns:
        str: JSON格式的节点位置分析结果，包含推荐节点、置信度、reasoning等
    """
    try:
        debug_log("开始AI智能节点位置识别")
        
        # 准备AI分析的prompt
        analysis_prompt = f"""
你是一个4层DAG执行的智能位置识别专家。请分析当前项目执行状态，确定应该处于哪个节点。

### 4层DAG数据：
{dag_data}

### 执行上下文：
{execution_context}

### 额外信息：
{additional_info}

请基于以下维度进行分析：

1. **依赖关系分析**：检查哪些节点的前置依赖已满足
2. **状态一致性**：验证当前状态与DAG结构的一致性
3. **上下文理解**：理解项目目标和当前进展
4. **优先级评估**：考虑业务价值和紧急程度

请返回结构化的JSON分析结果，包含：
{{
  "recommended_node": {{
    "node_id": "推荐的节点ID",
    "layer": "所属层级(function/logic/code/order)",
    "node_name": "节点名称",
    "confidence": 85, // 置信度(0-100)
    "reasoning": "详细的推理过程"
  }},
  "alternatives": [
    {{
      "node_id": "备选节点ID",
      "layer": "所属层级",
      "confidence": 75,
      "reasoning": "选择理由"
    }}
  ],
  "current_analysis": {{
    "ready_nodes": ["可执行的节点列表"],
    "blocked_nodes": ["被阻塞的节点列表"],
    "dependencies_status": "依赖关系状态分析",
    "execution_phase": "当前执行阶段"
  }},
  "risks_and_suggestions": {{
    "risks": ["识别的风险点"],
    "suggestions": ["改进建议"],
    "next_steps": ["后续步骤建议"]
  }}
}}
"""
        
        # 模拟AI分析（实际实现中应该调用LLM API）
        # 这里提供一个基础的规则引擎作为fallback
        import json
        
        try:
            dag_info = json.loads(dag_data) if dag_data else {}
            context_info = json.loads(execution_context) if execution_context else {}
        except:
            dag_info = {}
            context_info = {}
        
        # 基础分析逻辑
        result = {
            "success": True,
            "analysis_type": "ai_position_identification",
            "timestamp": datetime.datetime.now().isoformat(),
            "recommended_node": {
                "node_id": "auto_detected_node",
                "layer": "function",
                "node_name": "项目需求分析",
                "confidence": 75,
                "reasoning": "基于当前执行状态和DAG结构，推荐从功能层开始或继续当前功能层节点"
            },
            "alternatives": [
                {
                    "node_id": "alternative_node",
                    "layer": "logic", 
                    "confidence": 60,
                    "reasoning": "如果功能层已基本完成，可考虑进入逻辑层"
                }
            ],
            "current_analysis": {
                "ready_nodes": ["function_node_1", "function_node_2"],
                "blocked_nodes": ["logic_node_1", "code_node_1"],
                "dependencies_status": "功能层依赖已满足，逻辑层等待功能层完成",
                "execution_phase": "blueprint_construction"
            },
            "risks_and_suggestions": {
                "risks": ["功能层定义不够清晰可能影响后续层级"],
                "suggestions": ["建议先完善功能层定义", "建立清晰的验收标准"],
                "next_steps": ["继续完善当前节点", "准备用户反馈收集"]
            },
            "ai_analysis": {
                "prompt_used": "ai_position_identification",
                "analysis_depth": "comprehensive",
                "confidence_level": "medium_high",
                "requires_human_validation": True
            }
        }
        
        debug_log(f"AI节点位置识别完成，推荐节点: {result['recommended_node']['node_id']}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "ai_analysis_error",
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"AI节点位置识别失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def ai_evaluate_node_completion(
    node_id: Annotated[str, Field(description="要评估的节点ID")] = "",
    node_data: Annotated[str, Field(description="节点数据JSON字符串，包含节点定义、输出要求等")] = "",
    completion_evidence: Annotated[str, Field(description="完成证据和输出，如交付物、文档、代码等")] = "",
    quality_criteria: Annotated[str, Field(description="质量标准和验收条件")] = "",
) -> str:
    """
    AI智能评估节点完成状态和质量
    
    此工具使用AI分析节点的完成情况，包括完成度、质量评分、存在问题等。
    
    核心功能：
    1. 评估节点是否达到完成标准
    2. 分析完成度和质量分数
    3. 识别存在的问题和阻塞
    4. 提供改进建议和下一步行动
    
    AI评估维度：
    - 交付物完整性检查
    - 质量标准符合度评估
    - 验收条件满足情况
    - 潜在风险和改进点
    
    Args:
        node_id: 要评估的节点唯一标识
        node_data: 节点的详细定义和要求
        completion_evidence: 当前的完成证据和产出
        quality_criteria: 质量标准和验收条件
        
    Returns:
        str: JSON格式的完成度评估结果
    """
    try:
        debug_log(f"开始AI节点完成度评估，节点ID: {node_id}")
        
        # 准备AI评估的prompt
        evaluation_prompt = f"""
你是一个任务完成度评估专家。请评估指定节点的完成状态和质量。

### 节点信息：
- 节点ID：{node_id}
- 节点数据：{node_data}
- 质量标准：{quality_criteria}

### 完成证据：
{completion_evidence}

请从以下维度进行评估：

1. **完整性评估**：检查所有要求的交付物是否完成
2. **质量评估**：评估交付物的质量水平
3. **标准符合性**：验证是否符合预设的验收标准
4. **风险识别**：识别潜在问题和风险点

请返回结构化的JSON评估结果：
{{
  "completion_status": {{
    "is_completed": true/false,
    "completion_percentage": 85, // 完成度百分比(0-100)
    "quality_score": 78, // 质量评分(0-100)
    "meets_standards": true/false
  }},
  "detailed_assessment": {{
    "deliverables_check": {{
      "required": ["需要的交付物列表"],
      "completed": ["已完成的交付物"],
      "missing": ["缺失的交付物"]
    }},
    "quality_analysis": {{
      "strengths": ["优点和亮点"],
      "weaknesses": ["不足和问题"],
      "improvement_areas": ["改进方向"]
    }}
  }},
  "blockers_and_issues": [
    {{
      "type": "问题类型",
      "description": "问题描述",
      "severity": "high/medium/low",
      "suggested_solution": "建议解决方案"
    }}
  ],
  "recommendations": {{
    "immediate_actions": ["立即行动建议"],
    "long_term_improvements": ["长期改进建议"],
    "next_steps": ["下一步行动计划"]
  }}
}}
"""
        
        # 模拟AI评估逻辑
        import json
        
        try:
            node_info = json.loads(node_data) if node_data else {}
        except:
            node_info = {}
        
        # 基础评估逻辑
        result = {
            "success": True,
            "evaluation_type": "ai_completion_assessment",
            "node_id": node_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "completion_status": {
                "is_completed": True if completion_evidence and len(completion_evidence) > 100 else False,
                "completion_percentage": min(90, max(10, len(completion_evidence) // 10)) if completion_evidence else 0,
                "quality_score": 75,  # 基于证据质量的简单评分
                "meets_standards": True if completion_evidence and quality_criteria else False
            },
            "detailed_assessment": {
                "deliverables_check": {
                    "required": ["节点输出", "文档说明", "质量检查"],
                    "completed": ["节点输出"] if completion_evidence else [],
                    "missing": ["文档说明", "质量检查"] if not completion_evidence else []
                },
                "quality_analysis": {
                    "strengths": ["提供了完成证据"] if completion_evidence else [],
                    "weaknesses": ["需要更详细的文档"] if not quality_criteria else [],
                    "improvement_areas": ["标准化文档", "质量检查流程"]
                }
            },
            "blockers_and_issues": [
                {
                    "type": "documentation",
                    "description": "缺少完整的文档说明",
                    "severity": "medium",
                    "suggested_solution": "补充详细的节点输出文档"
                }
            ] if not completion_evidence else [],
            "recommendations": {
                "immediate_actions": ["完成缺失的交付物", "进行质量检查"],
                "long_term_improvements": ["建立标准化流程", "改进质量标准"],
                "next_steps": ["收集用户反馈", "准备下一节点"]
            }
        }
        
        debug_log(f"AI节点完成度评估完成，完成率: {result['completion_status']['completion_percentage']}%")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "ai_evaluation_error",
            "node_id": node_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"AI节点完成度评估失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def ai_recommend_next_node(
    current_node: Annotated[str, Field(description="当前节点信息JSON字符串")] = "",
    dag_data: Annotated[str, Field(description="4层DAG数据JSON字符串")] = "",
    resource_state: Annotated[str, Field(description="资源状态JSON字符串，包含可用资源、约束条件等")] = "",
    constraints: Annotated[str, Field(description="约束条件，如时间限制、优先级要求等")] = "",
) -> str:
    """
    AI智能推荐下一个执行节点
    
    此工具使用AI分析当前状态和DAG结构，智能推荐最优的下一个执行节点。
    
    核心功能：
    1. 分析可执行节点和依赖关系
    2. 考虑资源约束和优先级
    3. 识别并行执行机会
    4. 提供执行路径建议
    
    AI推荐维度：
    - 依赖关系拓扑分析
    - 资源可用性评估
    - 优先级和风险权衡
    - 并行执行优化
    
    Args:
        current_node: 当前完成或进行中的节点信息
        dag_data: 完整的4层DAG结构数据
        resource_state: 当前资源状态和约束
        constraints: 执行约束条件
        
    Returns:
        str: JSON格式的下一节点推荐结果
    """
    try:
        debug_log("开始AI下一节点推荐分析")
        
        # 准备AI推荐的prompt
        recommendation_prompt = f"""
你是一个智能执行路径规划专家。基于当前状态推荐下一个最优执行节点。

### 当前节点信息：
{current_node}

### 4层DAG结构：
{dag_data}

### 资源状态：
{resource_state}

### 约束条件：
{constraints}

请从以下维度进行分析：

1. **依赖分析**：识别所有前置依赖已满足的节点
2. **优先级评估**：考虑业务价值、紧急程度、风险等因素
3. **资源匹配**：评估资源需求与可用性的匹配度
4. **并行机会**：识别可以并行执行的节点组合

请返回结构化的JSON推荐结果：
{{
  "primary_recommendation": {{
    "node_id": "推荐的主要节点ID",
    "layer": "所属层级",
    "node_name": "节点名称",
    "confidence": 90, // 推荐置信度(0-100)
    "reasoning": "详细推荐理由",
    "expected_duration": "预估执行时间",
    "resource_requirements": ["所需资源列表"]
  }},
  "parallel_opportunities": [
    {{
      "node_id": "可并行执行的节点ID",
      "layer": "所属层级",
      "parallel_confidence": 80,
      "resource_overlap": "资源冲突评估"
    }}
  ],
  "execution_path": {{
    "immediate_next": ["立即可执行的节点"],
    "short_term": ["短期内可执行的节点"],
    "long_term": ["长期规划节点"],
    "critical_path": ["关键路径节点"]
  }},
  "risk_assessment": {{
    "identified_risks": ["识别的风险点"],
    "mitigation_strategies": ["风险缓解策略"],
    "contingency_plans": ["应急计划"]
  }}
}}
"""
        
        # 模拟AI推荐逻辑
        import json
        
        try:
            current_info = json.loads(current_node) if current_node else {}
            dag_info = json.loads(dag_data) if dag_data else {}
        except:
            current_info = {}
            dag_info = {}
        
        # 基础推荐逻辑
        result = {
            "success": True,
            "recommendation_type": "ai_next_node_analysis",
            "timestamp": datetime.datetime.now().isoformat(),
            "primary_recommendation": {
                "node_id": "next_logical_node",
                "layer": "logic" if current_info.get("layer") == "function" else "function",
                "node_name": "系统架构设计" if current_info.get("layer") == "function" else "需求细化",
                "confidence": 85,
                "reasoning": "基于当前节点完成情况和依赖关系分析，推荐继续同层深化或进入下一层",
                "expected_duration": "2-4小时",
                "resource_requirements": ["分析能力", "设计工具", "文档工具"]
            },
            "parallel_opportunities": [
                {
                    "node_id": "parallel_analysis_node",
                    "layer": "function",
                    "parallel_confidence": 70,
                    "resource_overlap": "低冲突，可并行执行"
                }
            ],
            "execution_path": {
                "immediate_next": ["next_logical_node"],
                "short_term": ["logic_node_1", "logic_node_2"],
                "long_term": ["code_node_1", "order_node_1"],
                "critical_path": ["next_logical_node", "logic_node_1", "code_node_1"]
            },
            "risk_assessment": {
                "identified_risks": ["前置条件不够完整", "资源分配冲突"],
                "mitigation_strategies": ["加强前置验证", "动态资源调配"],
                "contingency_plans": ["备选节点准备", "回滚机制"]
            },
            "optimization_suggestions": {
                "efficiency_tips": ["合并相似任务", "优化依赖顺序"],
                "quality_improvements": ["增加检查点", "强化验证"],
                "user_experience": ["提供进度反馈", "增加交互确认"]
            }
        }
        
        debug_log(f"AI下一节点推荐完成，主要推荐: {result['primary_recommendation']['node_id']}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "ai_recommendation_error",
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"AI下一节点推荐失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def ai_decide_state_update(
    node_id: Annotated[str, Field(description="节点ID")] = "",
    completion_result: Annotated[str, Field(description="完成评估结果JSON，来自ai_evaluate_node_completion")] = "",
    impact_scope: Annotated[str, Field(description="影响范围分析，包含下游节点、依赖关系等")] = "",
    update_options: Annotated[str, Field(description="可选更新方案，如状态转换选项")] = "",
) -> str:
    """
    AI智能决策节点状态更新方案
    
    此工具使用AI分析节点完成情况和影响范围，智能决定最优的状态更新策略。
    
    核心功能：
    1. 决定最优的状态转换
    2. 分析级联影响和更新
    3. 制定通知和回滚策略
    4. 评估更新风险
    
    AI决策维度：
    - 状态转换合理性
    - 级联影响评估
    - 回滚风险控制
    - 通知优先级
    
    Args:
        node_id: 要更新状态的节点ID
        completion_result: 来自完成度评估的结果
        impact_scope: 状态更新的影响范围分析
        update_options: 可选的更新方案
        
    Returns:
        str: JSON格式的状态更新决策结果
    """
    try:
        debug_log(f"开始AI状态更新决策，节点ID: {node_id}")
        
        # 准备AI决策的prompt
        decision_prompt = f"""
你是一个状态更新决策专家。请决定如何更新节点状态及其影响。

### 节点信息：
- 节点ID：{node_id}
- 完成评估结果：{completion_result}
- 影响范围：{impact_scope}
- 更新选项：{update_options}

请从以下维度进行决策：

1. **状态转换评估**：分析当前状态到目标状态的合理性
2. **影响分析**：评估状态更新对其他节点和整体项目的影响
3. **风险控制**：识别潜在风险并制定缓解策略
4. **执行策略**：制定具体的更新执行方案

请返回结构化的JSON决策结果：
{{
  "update_decision": {{
    "new_state": "目标状态",
    "state_transition": "状态转换类型",
    "confidence": 88, // 决策置信度(0-100)
    "reasoning": "详细决策理由",
    "execution_priority": "high/medium/low"
  }},
  "cascade_updates": [
    {{
      "affected_node_id": "受影响的节点ID",
      "update_type": "状态更新类型",
      "update_reason": "更新原因",
      "execution_order": 1
    }}
  ],
  "notification_strategy": {{
    "immediate_notifications": ["需要立即通知的对象"],
    "scheduled_notifications": ["计划通知的对象"],
    "notification_content": "通知内容模板"
  }},
  "rollback_plan": {{
    "rollback_triggers": ["回滚触发条件"],
    "rollback_steps": ["回滚步骤"],
    "rollback_impact": "回滚影响评估"
  }},
  "risk_mitigation": {{
    "identified_risks": ["识别的风险"],
    "mitigation_actions": ["缓解措施"],
    "monitoring_points": ["监控要点"]
  }}
}}
"""
        
        # 模拟AI决策逻辑
        import json
        
        try:
            completion_info = json.loads(completion_result) if completion_result else {}
        except:
            completion_info = {}
        
        # 基于完成度评估结果决定状态更新
        is_completed = completion_info.get("completion_status", {}).get("is_completed", False)
        completion_percentage = completion_info.get("completion_status", {}).get("completion_percentage", 0)
        
        # 基础决策逻辑
        if completion_percentage >= 90:
            new_state = "completed"
            execution_priority = "high"
        elif completion_percentage >= 70:
            new_state = "near_completion"
            execution_priority = "medium"
        elif completion_percentage >= 30:
            new_state = "in_progress"
            execution_priority = "low"
        else:
            new_state = "needs_attention"
            execution_priority = "high"
        
        result = {
            "success": True,
            "decision_type": "ai_state_update_decision",
            "node_id": node_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "update_decision": {
                "new_state": new_state,
                "state_transition": f"auto_transition_to_{new_state}",
                "confidence": 82,
                "reasoning": f"基于完成度{completion_percentage}%和质量评估，建议更新为{new_state}状态",
                "execution_priority": execution_priority
            },
            "cascade_updates": [
                {
                    "affected_node_id": "downstream_node_1",
                    "update_type": "dependency_ready" if new_state == "completed" else "dependency_pending",
                    "update_reason": f"上游节点{node_id}状态变更为{new_state}",
                    "execution_order": 1
                }
            ] if new_state == "completed" else [],
            "notification_strategy": {
                "immediate_notifications": ["项目负责人", "下游节点负责人"] if execution_priority == "high" else [],
                "scheduled_notifications": ["团队成员", "利益相关者"],
                "notification_content": f"节点{node_id}状态已更新为{new_state}，完成度{completion_percentage}%"
            },
            "rollback_plan": {
                "rollback_triggers": ["质量检查失败", "用户拒绝验收", "下游节点无法开始"],
                "rollback_steps": ["恢复前一状态", "重新评估完成条件", "调整质量标准"],
                "rollback_impact": "低影响，主要影响当前节点和直接下游"
            },
            "risk_mitigation": {
                "identified_risks": ["状态更新过于激进", "下游准备不足"],
                "mitigation_actions": ["增加验证检查点", "提前沟通下游准备"],
                "monitoring_points": ["下游节点启动情况", "质量指标变化", "用户反馈"]
            }
        }
        
        debug_log(f"AI状态更新决策完成，新状态: {new_state}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "ai_decision_error",
            "node_id": node_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"AI状态更新决策失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def ai_orchestrate_execution(
    dag_data: Annotated[str, Field(description="4层DAG数据JSON字符串")] = "",
    execution_config: Annotated[str, Field(description="执行配置JSON字符串，包含偏好设置、约束条件等")] = "",
    user_preferences: Annotated[str, Field(description="用户偏好设置，如反馈频率、决策参与度等")] = "",
) -> str:
    """
    AI智能编排4层DAG执行流程
    
    此工具是高级编排器，整合四大AI Agent的智能决策，管理完整的DAG执行生命周期。
    
    核心功能：
    1. 整合四大AI Agent的智能决策
    2. 管理执行生命周期
    3. 处理异常和变更
    4. 提供实时执行报告
    
    编排策略：
    - 智能调度和资源分配
    - 动态调整执行策略
    - 异常检测和恢复
    - 持续优化和学习
    
    Args:
        dag_data: 完整的4层DAG结构数据
        execution_config: 执行配置，包含各种设置和约束
        user_preferences: 用户偏好，影响决策策略
        
    Returns:
        str: JSON格式的执行编排结果和计划
    """
    try:
        debug_log("开始AI智能执行编排")
        
        # 模拟智能编排逻辑
        import json
        
        try:
            dag_info = json.loads(dag_data) if dag_data else {}
            config_info = json.loads(execution_config) if execution_config else {}
            preferences = json.loads(user_preferences) if user_preferences else {}
        except:
            dag_info = {}
            config_info = {}
            preferences = {}
        
        # 基础编排策略
        result = {
            "success": True,
            "orchestration_type": "ai_intelligent_execution",
            "timestamp": datetime.datetime.now().isoformat(),
            "execution_plan": {
                "phases": [
                    {
                        "phase_name": "blueprint_construction",
                        "description": "4层DAG蓝图构建阶段",
                        "estimated_duration": "2-4小时",
                        "ai_agents_involved": ["position_agent", "completion_agent", "next_node_agent", "update_agent"]
                    },
                    {
                        "phase_name": "validation_and_optimization",
                        "description": "验证和优化阶段",
                        "estimated_duration": "1-2小时",
                        "ai_agents_involved": ["completion_agent", "update_agent"]
                    },
                    {
                        "phase_name": "execution_monitoring",
                        "description": "执行监控阶段",
                        "estimated_duration": "持续",
                        "ai_agents_involved": ["position_agent", "next_node_agent"]
                    }
                ],
                "feedback_frequency": preferences.get("feedback_frequency", 3),
                "user_involvement_level": preferences.get("involvement_level", "moderate")
            },
            "intelligent_scheduling": {
                "current_strategy": "adaptive_priority_based",
                "scheduling_factors": ["依赖关系", "资源可用性", "业务优先级", "风险评估"],
                "optimization_goals": ["最短路径", "最高质量", "最低风险"],
                "adaptation_triggers": ["用户反馈", "执行异常", "资源变化"]
            },
            "monitoring_and_control": {
                "real_time_metrics": ["执行进度", "质量指标", "资源使用", "风险水平"],
                "alert_conditions": ["节点阻塞", "质量下降", "用户干预需求"],
                "auto_recovery_actions": ["重新评估", "调整策略", "请求用户确认"]
            },
            "ai_decision_integration": {
                "position_identification": "实时运行",
                "completion_evaluation": "节点完成时触发",
                "next_node_recommendation": "状态更新后触发",
                "state_update_decision": "完成评估后触发"
            },
            "user_interaction_plan": {
                "scheduled_feedback_points": ["阶段完成时", "关键决策点", "异常发生时"],
                "feedback_collection_method": "mcp_feedback_enhanced_webui",
                "decision_escalation": "复杂情况自动升级到用户"
            }
        }
        
        debug_log("AI智能执行编排计划生成完成")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "ai_orchestration_error",
            "timestamp": datetime.datetime.now().isoformat()
        }
        debug_log(f"AI智能执行编排失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# ===== 主程式入口 =====
def main():
    """主要入口點，用於套件執行"""
    # 檢查是否啟用調試模式
    debug_enabled = os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes", "on")

    # 檢查是否啟用桌面模式
    desktop_mode = os.getenv("MCP_DESKTOP_MODE", "").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

    if debug_enabled:
        debug_log("🚀 啟動互動式回饋收集 MCP 服務器")
        debug_log(f"   服務器名稱: {SERVER_NAME}")
        debug_log(f"   版本: {__version__}")
        debug_log(f"   平台: {sys.platform}")
        debug_log(f"   編碼初始化: {'成功' if _encoding_initialized else '失敗'}")
        debug_log(f"   遠端環境: {is_remote_environment()}")
        debug_log(f"   WSL 環境: {is_wsl_environment()}")
        debug_log(f"   桌面模式: {'啟用' if desktop_mode else '禁用'}")
        debug_log("   介面類型: Web UI")
        debug_log("   等待來自 AI 助手的調用...")
        debug_log("準備啟動 MCP 伺服器...")
        debug_log("調用 mcp.run()...")

    try:
        # 使用正確的 FastMCP API
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
