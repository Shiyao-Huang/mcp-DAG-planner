/**
 * 四层DAG控制器
 * ===============
 * 
 * Version: v1.0.0
 * Author: AI Assistant + User
 * Date: 2024-12-20
 * Purpose: 集成DAG管理器到MCP Feedback Enhanced主应用
 * Dependencies: DAGManager, WebSocket, MCP Tools, UI Manager
 */

/**
 * ```mermaid
 * graph TD
 *     A[DAGController] --> B[DAGManager]
 *     A --> C[MCP Tools Bridge]
 *     A --> D[UI Event Handler]
 *     A --> E[Data Synchronizer]
 *     
 *     B --> F[可视化渲染]
 *     B --> G[布局管理]
 *     B --> H[交互控制]
 *     
 *     C --> I[四层构建工具调用]
 *     C --> J[AI智能工具调用]
 *     C --> K[数据格式转换]
 *     
 *     D --> L[按钮事件处理]
 *     D --> M[文本输入处理]
 *     D --> N[选择器变化]
 *     
 *     E --> O[本地存储同步]
 *     E --> P[WebSocket同步]
 *     E --> Q[状态更新]
 * ```
 */

(function() {
    'use strict';

    // 确保命名空间存在
    window.MCPFeedback = window.MCPFeedback || {};
    window.MCPFeedback.DAG = window.MCPFeedback.DAG || {};

    /**
     * DAG控制器
     */
    function DAGController() {
        this.dagManager = null;
        this.logger = window.MCPFeedback.Logger;
        this.webSocketManager = null;
    }

    /**
     * 初始化DAG控制器
     */
    DAGController.prototype.init = function() {
        const self = this;
        this.logger.debug('初始化 DAGController...');

        try {
            this.dagManager = new window.MCPFeedback.DAG.DAGManager({
                containerId: 'dag-container',
                enableEdit: true,
                enableSync: true
            });

            this.dagManager.init()
                .then(function() {
                    self.logger.info('📥 开始加载DAG数据...');
                    return self.dagManager.loadSavedDAG();
                })
                .then(function() {
                    self.logger.info('📊 更新统计信息...');
                    // 获取实际的统计数据并更新UI
                    const stats = self.getLayerStatistics();
                    self.updateStatistics(stats);
                    
                    self.setupEventListeners();
                    self.setupWebSocketListener();
                    
                    self.isInitialized = true;
                    self.logger.info('✅ DAGController 初始化完成');
                })
                .catch(function(error) {
                    self.logger.error('❌ DAGManager 初始化失败:', error);
                });
        } catch (error) {
            this.logger.error('❌ DAGController 初始化异常:', error);
        }
    };

    /**
     * 设置WebSocket监听器
     */
    DAGController.prototype.setupWebSocketListener = function() {
        const self = this;
        
        // 确保WebSocketManager可用
        if (window.MCPFeedback && window.MCPFeedback.WebSocketManager) {
            this.webSocketManager = window.MCPFeedback.WebSocketManager;
            
            // 添加消息处理器
            this.webSocketManager.addMessageHandler('dag_update', function(data) {
                self.logger.info('收到DAG更新消息:', data);
                if (self.dagManager && typeof self.dagManager.updateDAGFromExternal === 'function') {
                    self.dagManager.updateDAGFromExternal(data.data);
                }
            });
            
            this.logger.info('🔌 DAG WebSocket监听器设置完成');
        } else {
            this.logger.warn('WebSocketManager 未找到，延迟设置监听器');
            setTimeout(function() {
                self.setupWebSocketListener();
            }, 1000);
        }
    };

    /**
     * 设置事件监听器
     */
    DAGController.prototype.setupEventListeners = function() {
        const self = this;

        return new Promise(function(resolve) {
            // 加载示例按钮
            const loadTestDAGBtn = document.getElementById('loadTestDAG');
            if (loadTestDAGBtn) {
                loadTestDAGBtn.addEventListener('click', function() {
                    self.loadTestDAG();
                });
            }

            // 保存DAG按钮
            const saveDAGBtn = document.getElementById('saveDAG');
            if (saveDAGBtn) {
                saveDAGBtn.addEventListener('click', function() {
                    self.saveDAG();
                });
            }

            // 导出DAG按钮
            const exportDAGBtn = document.getElementById('exportDAG');
            if (exportDAGBtn) {
                exportDAGBtn.addEventListener('click', function() {
                    self.exportDAG();
                });
            }

            // 加载DAG按钮
            const loadDAGBtn = document.getElementById('loadDAGBtn');
            if (loadDAGBtn) {
                loadDAGBtn.addEventListener('click', function() {
                    self.loadDAGFromInput();
                });
            }

            // 调用MCP工具按钮
            const callMCPToolsBtn = document.getElementById('callMCPTools');
            if (callMCPToolsBtn) {
                callMCPToolsBtn.addEventListener('click', function() {
                    self.callMCPTools();
                });
            }

            // 清空DAG按钮
            const clearDAGBtn = document.getElementById('clearDAG');
            if (clearDAGBtn) {
                clearDAGBtn.addEventListener('click', function() {
                    self.clearDAG();
                });
            }

            // 层级选择器
            const layerSelect = document.getElementById('dagLayerSelect');
            if (layerSelect) {
                layerSelect.addEventListener('change', function(e) {
                    self.currentLayer = e.target.value;
                });
            }

            // Mermaid输入框快捷键
            const mermaidInput = document.getElementById('dagMermaidInput');
            if (mermaidInput) {
                mermaidInput.addEventListener('keydown', function(e) {
                    // Ctrl+Enter 快速加载
                    if (e.ctrlKey && e.key === 'Enter') {
                        e.preventDefault();
                        self.loadDAGFromInput();
                    }
                });
            }

            // 示例：显示/隐藏日志
            document.getElementById('toggle-logs-btn').addEventListener('click', function() {
                const logsContainer = document.getElementById('logs-container');
                logsContainer.style.display = logsContainer.style.display === 'none' ? 'block' : 'none';
            });

            // 添加一个按钮来加载测试数据
            document.getElementById('load-test-data-btn').addEventListener('click', () => {
                this.loadTestDAGData();
            });

            resolve();
        });
    };

    /**
     * 设置MCP工具桥接
     */
    DAGController.prototype.setupMCPToolsBridge = function() {
        const self = this;

        return new Promise(function(resolve) {
            // 如果WebSocket管理器可用，设置消息监听
            if (self.webSocketManager) {
                // 监听MCP工具响应
                self.webSocketManager.on('mcp_tool_response', function(data) {
                    self.handleMCPToolResponse(data);
                });

                self.logger.info('🔧 MCP工具桥接设置完成');
            }

            resolve();
        });
    };

    /**
     * 创建测试样本
     */
    DAGController.prototype.createTestSamples = function() {
        return {
            function: `graph TD
    A[用户需求分析] --> B[功能规格定义]
    B --> C[用户界面设计]
    C --> D[数据模型设计]
    D --> E[API接口规划]
    E --> F[系统集成规划]`,
            
            logic: `graph TD
    A[前端React应用] --> B[API网关]
    B --> C[用户服务]
    B --> D[数据服务]
    C --> E[用户数据库]
    D --> F[业务数据库]
    B --> G[缓存服务Redis]`,
            
            code: `graph TD
    A[src/components/] --> B[src/services/]
    A --> C[src/hooks/]
    B --> D[src/models/]
    C --> D
    D --> E[src/utils/]`,
            
            order: `graph TD
    A[Phase1:环境搭建] --> B[Phase2:数据模型]
    B --> C[Phase3:API开发]
    C --> D[Phase4:前端组件]
    D --> E[Phase5:集成测试]`
        };
    };

    /**
     * 加载测试DAG
     */
    DAGController.prototype.loadTestDAG = function() {
        try {
            const layers = ['function', 'logic', 'code', 'order'];
            
            layers.forEach(layer => {
                if (this.testDAGSamples[layer]) {
                    this.dagManager.loadDAG(layer, this.testDAGSamples[layer]);
                }
            });

            this.updateStatistics();
            this.showNotification('✅ 测试DAG数据加载完成', 'success');
            
            this.logger.info('📥 测试DAG数据加载完成');
        } catch (error) {
            this.logger.error('❌ 加载测试DAG失败:', error);
            this.showNotification('❌ 加载测试DAG失败: ' + error.message, 'error');
        }
    };

    /**
     * 从输入框加载DAG
     */
    DAGController.prototype.loadDAGFromInput = function() {
        try {
            const mermaidInput = document.getElementById('dagMermaidInput');
            const layerSelect = document.getElementById('dagLayerSelect');
            
            if (!mermaidInput || !layerSelect) {
                throw new Error('必需的DOM元素未找到');
            }

            const mermaidText = mermaidInput.value.trim();
            const selectedLayer = layerSelect.value;

            if (!mermaidText) {
                throw new Error('请输入Mermaid DAG定义');
            }

            // 使用DAG管理器加载数据
            this.dagManager.loadDAG(selectedLayer, mermaidText);
            
            // 更新统计信息
            this.updateStatistics();
            
            // 清空输入框
            mermaidInput.value = '';
            
            this.showNotification(`✅ ${this.getLayerDisplayName(selectedLayer)}数据加载完成`, 'success');
            this.logger.info(`📥 ${selectedLayer} 层DAG数据加载完成`);
            
        } catch (error) {
            this.logger.error('❌ 从输入加载DAG失败:', error);
            this.showNotification('❌ 加载DAG失败: ' + error.message, 'error');
        }
    };

    /**
     * 保存DAG
     */
    DAGController.prototype.saveDAG = function() {
        try {
            this.dagManager.saveDAG();
            this.showNotification('💾 DAG数据已保存', 'success');
            this.logger.info('💾 DAG数据保存完成');
        } catch (error) {
            this.logger.error('❌ 保存DAG失败:', error);
            this.showNotification('❌ 保存DAG失败: ' + error.message, 'error');
        }
    };

    /**
     * 导出DAG
     */
    DAGController.prototype.exportDAG = function() {
        try {
            const format = 'json'; // 可以后续扩展为用户选择
            const data = this.dagManager.exportDAG(format);
            
            // 创建下载链接
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `four-layer-dag-${new Date().toISOString().slice(0, 10)}.json`;
            
            // 触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            this.showNotification('📤 DAG数据导出完成', 'success');
            this.logger.info('📤 DAG数据导出完成');
            
        } catch (error) {
            this.logger.error('❌ 导出DAG失败:', error);
            this.showNotification('❌ 导出DAG失败: ' + error.message, 'error');
        }
    };

    /**
     * 调用MCP工具
     */
    DAGController.prototype.callMCPTools = function() {
        try {
            if (!this.webSocketManager) {
                throw new Error('WebSocket连接不可用');
            }

            const layers = this.dagManager.dagLayers;
            const hasData = Object.keys(layers).some(layer => 
                layers[layer].nodes.length > 0
            );

            if (!hasData) {
                throw new Error('请先加载DAG数据');
            }

            this.showNotification('🚀 正在调用MCP构建工具...', 'info');

            // 调用四层DAG构建工具
            this.callFourLayerDAGTools();

        } catch (error) {
            this.logger.error('❌ 调用MCP工具失败:', error);
            this.showNotification('❌ 调用MCP工具失败: ' + error.message, 'error');
        }
    };

    /**
     * 调用四层DAG构建工具
     */
    DAGController.prototype.callFourLayerDAGTools = function() {
        const self = this;
        const layers = this.dagManager.dagLayers;

        // 按顺序调用四个工具
        Promise.resolve()
            .then(function() {
                if (layers.function.nodes.length > 0) {
                    return self.callMCPTool('build_function_layer_dag', {
                        project_description: '智能项目管理系统构建',
                        mermaid_dag: self.dagManager.exportToMermaid(),
                        business_requirements: '四层DAG可视化系统需求'
                    });
                }
            })
            .then(function(functionResult) {
                if (layers.logic.nodes.length > 0 && functionResult) {
                    return self.callMCPTool('build_logic_layer_dag', {
                        function_layer_result: JSON.stringify(functionResult),
                        mermaid_dag: self.dagManager.exportToMermaid(),
                        technical_architecture: '微服务架构设计'
                    });
                }
            })
            .then(function(logicResult) {
                if (layers.code.nodes.length > 0 && logicResult) {
                    return self.callMCPTool('build_code_layer_dag', {
                        logic_layer_result: JSON.stringify(logicResult),
                        mermaid_dag: self.dagManager.exportToMermaid(),
                        implementation_details: 'React + FastAPI 技术栈实现'
                    });
                }
            })
            .then(function(codeResult) {
                if (layers.order.nodes.length > 0 && codeResult) {
                    return self.callMCPTool('build_order_layer_dag', {
                        code_layer_result: JSON.stringify(codeResult),
                        mermaid_dag: self.dagManager.exportToMermaid(),
                        execution_strategy: '敏捷开发迭代策略'
                    });
                }
            })
            .then(function(orderResult) {
                self.showNotification('✅ MCP四层DAG构建工具调用完成', 'success');
                self.logger.info('✅ MCP工具调用完成');
                
                // 可以在这里处理最终结果
                if (orderResult) {
                    self.logger.info('📊 四层DAG构建结果:', orderResult);
                }
            })
            .catch(function(error) {
                self.logger.error('❌ MCP工具调用失败:', error);
                self.showNotification('❌ MCP工具调用失败: ' + error.message, 'error');
            });
    };

    /**
     * 调用单个MCP工具
     */
    DAGController.prototype.callMCPTool = function(toolName, params) {
        const self = this;

        return new Promise(function(resolve, reject) {
            if (!self.webSocketManager) {
                reject(new Error('WebSocket连接不可用'));
                return;
            }

            // 发送MCP工具调用请求
            const message = {
                type: 'mcp_tool_call',
                tool: toolName,
                params: params,
                timestamp: new Date().toISOString()
            };

            // 设置响应监听器
            const responseHandler = function(data) {
                if (data.tool === toolName) {
                    self.webSocketManager.off('mcp_tool_response', responseHandler);
                    
                    if (data.success) {
                        resolve(data.result);
                    } else {
                        reject(new Error(data.error || '工具调用失败'));
                    }
                }
            };

            self.webSocketManager.on('mcp_tool_response', responseHandler);

            // 发送请求
            self.webSocketManager.send(message);

            // 设置超时
            setTimeout(function() {
                self.webSocketManager.off('mcp_tool_response', responseHandler);
                reject(new Error('工具调用超时'));
            }, 30000); // 30秒超时
        });
    };

    /**
     * 清空DAG
     */
    DAGController.prototype.clearDAG = function() {
        try {
            // 清空所有层级数据
            Object.keys(this.dagManager.dagLayers).forEach(layer => {
                this.dagManager.dagLayers[layer].nodes = [];
                this.dagManager.dagLayers[layer].edges = [];
            });

            // 重新渲染
            this.dagManager.render();
            
            // 更新统计信息
            this.updateStatistics();
            
            // 清空输入框
            const mermaidInput = document.getElementById('dagMermaidInput');
            if (mermaidInput) {
                mermaidInput.value = '';
            }

            this.showNotification('🗑️ DAG数据已清空', 'info');
            this.logger.info('🗑️ DAG数据清空完成');
            
        } catch (error) {
            this.logger.error('❌ 清空DAG失败:', error);
            this.showNotification('❌ 清空DAG失败: ' + error.message, 'error');
        }
    };

    /**
     * 处理节点选择
     */
    DAGController.prototype.handleNodeSelect = function(node, layer) {
        this.logger.info('节点选择:', node.data.label, '层级:', layer);
        this.showNotification(`选择了 ${this.getLayerDisplayName(layer)} 节点: ${node.data.label}`, 'info');
    };

    /**
     * 处理数据变化
     */
    DAGController.prototype.handleDataChange = function() {
        this.updateStatistics();
    };

    /**
     * 处理MCP工具响应
     */
    DAGController.prototype.handleMCPToolResponse = function(data) {
        this.logger.info('收到MCP工具响应:', data);
        
        if (data.success) {
            this.showNotification(`✅ ${data.tool} 执行成功`, 'success');
        } else {
            this.showNotification(`❌ ${data.tool} 执行失败: ${data.error}`, 'error');
        }
    };

    /**
     * 获取各层级的统计信息
     */
    DAGController.prototype.getLayerStatistics = function() {
        const stats = {
            function: 0,
            logic: 0,
            code: 0,
            order: 0
        };
        
        if (this.dagManager && this.dagManager.dagLayers) {
            for (const layer in this.dagManager.dagLayers) {
                if (stats.hasOwnProperty(layer)) {
                    stats[layer] = this.dagManager.dagLayers[layer].nodes.length;
                }
            }
        }
        
        this.logger.debug('📊 获取层级统计:', stats);
        return stats;
    };

    /**
     * 更新统计信息 - 接收来自DAGManager的统计数据
     */
    DAGController.prototype.updateStatistics = function(stats) {
        this.logger.info('📊 更新统计信息:', stats);
        
        // 更新各层级计数器的显示 - 使用HTML模板中实际定义的ID
        const counterMap = {
            function: '#functionNodesCount',
            logic: '#logicNodesCount', 
            code: '#codeNodesCount',
            order: '#orderNodesCount'
        };
        
        for (const [layer, selector] of Object.entries(counterMap)) {
            const element = document.querySelector(selector);
            if (element) {
                const count = stats[layer] || 0;
                element.textContent = count;
                this.logger.debug(`📊 更新${layer}层计数器: ${count}`);
            } else {
                this.logger.warn(`⚠️ 找不到${layer}层计数器元素: ${selector}`);
            }
        }
        
        // 计算总节点数
        const totalNodes = Object.values(stats).reduce((sum, count) => sum + (count || 0), 0);
        this.logger.info(`📊 统计信息更新完成，总计 ${totalNodes} 个节点`);
    };

    /**
     * 获取层级显示名称
     */
    DAGController.prototype.getLayerDisplayName = function(layer) {
        const names = {
            function: '功能层',
            logic: '逻辑层',
            code: '代码层',
            order: '排序层'
        };
        return names[layer] || layer;
    };

    /**
     * 显示通知
     */
    DAGController.prototype.showNotification = function(message, type) {
        // 使用主应用的通知系统
        if (this.uiManager && this.uiManager.showNotification) {
            this.uiManager.showNotification(message, type);
        } else {
            // 回退到简单通知
            console.log(`[${type.toUpperCase()}] ${message}`);
            
            // 可以在这里添加简单的UI通知
            const notification = document.createElement('div');
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                padding: 10px 15px;
                border-radius: 6px;
                color: white;
                font-size: 14px;
                max-width: 300px;
                background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(function() {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);
        }
    };

    /**
     * 销毁DAG控制器
     */
    DAGController.prototype.destroy = function() {
        if (this.dagManager) {
            this.dagManager.destroy();
        }

        // 清理事件监听器
        // (这里可以添加具体的清理代码)

        this.isInitialized = false;
        this.logger.info('🗑️ DAGController 已销毁');
    };

    /**
     * 加载测试用的DAG数据
     */
    DAGController.prototype.loadTestDAGData = function() {
        this.logger.info('📥 加载测试DAG数据...');

        const testData = {
            function: `graph TD
    A[核心游戏循环] --> B(设计与建造)
    A --> C(发射与飞行)
    A --> D(任务与科学)
    B --> B1(零件选择)
    B --> B2(组装载具)
    C --> C1(物理模拟)
    C --> C2(轨道力学)
    D --> D1(合同系统)
    D --> D2(科技树)
    D --> D3(科学实验)`,
            logic: `graph TD
    subgraph "游戏核心 (GODOT)"
        Node_GameManager[GameManager]
        Node_SceneLoader[SceneLoader]
        Node_InputHandler[InputHandler]
    end
    subgraph "载具编辑器"
        Node_VAB[VAB_UI]
        Node_PartSelector[PartSelector]
        Node_Assembly[VehicleAssembly]
    end
    subgraph "飞行与物理"
        Node_FlightSim[FlightSimulator]
        Node_PhysicsEngine[GodotPhysics]
        Node_OrbitalCalc[OrbitalCalculator]
    end
    Node_GameManager --> Node_SceneLoader
    Node_GameManager --> Node_InputHandler
    Node_SceneLoader --> Node_VAB
    Node_SceneLoader --> Node_FlightSim
    Node_VAB --> Node_PartSelector
    Node_VAB --> Node_Assembly
    Node_FlightSim --> Node_PhysicsEngine
    Node_FlightSim --> Node_OrbitalCalc`,
            code: `graph TD
    subgraph "autoloads"
        GameManager["game_manager.gd"]
    end
    subgraph "scenes"
        VAB["vab.tscn"]
        Flight["flight.tscn"]
    end
    subgraph "scripts"
        VAB_Script["vab.gd"]
        Flight_Script["flight.gd"]
        Part_Script["part.gd"]
        Rocket_Script["rocket.gd"]
    end
    GameManager --> VAB
    GameManager --> Flight
    VAB --> VAB_Script
    Flight --> Flight_Script
    VAB_Script --> Part_Script
    Flight_Script --> Rocket_Script
    Rocket_Script --> Part_Script`,
            order: `graph TD
    subgraph "Sprint 1"
        Task1[实现GameManager]
        Task2[实现场景加载]
        Task3[搭建VAB基础UI]
    end
    subgraph "Sprint 2"
        Task4[实现飞行物理]
        Task5[实现轨道计算]
    end
    subgraph "Sprint 3"
        Task6[实现合同系统]
        Task7[实现科技树]
    end
    Task1 --> Task2
    Task2 --> Task3
    Task3 --> Task4
    Task4 --> Task5
    Task5 --> Task6
    Task6 --> Task7`
        };

        try {
            for (const layer in testData) {
                if (testData.hasOwnProperty(layer)) {
                    this.dagManager.loadDAG(layer, testData[layer]);
                }
            }
            this.logger.success('✅ 测试DAG数据加载完成');
        } catch (error) {
            this.logger.error('❌ 加载测试DAG数据失败', error);
        }
    };

    // 导出到全局命名空间
    window.MCPFeedback.DAG.DAGController = DAGController;

    console.log('🎮 DAG控制器模块加载完成');

})(); 