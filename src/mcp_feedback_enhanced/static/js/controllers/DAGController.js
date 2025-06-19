/**
 * DAG控制器 - 负责DAG图形界面的交互和管理
 * 版本: v2.0
 * 
 * 依赖关系:
 * ```mermaid
 * graph TD
 *     A[DAGController] --> B[cytoscape.js]
 *     A --> C[WebSocket]
 *     A --> D[四层DAG工具]
 *     A --> E[MCP工具调用]
 * ```
 * 
 * 核心功能:
 * - 初始化DAG图形界面
 * - 处理用户交互事件
 * - 调用四层DAG构建工具
 * - 保存和加载DAG数据
 * - 提供DAG文件管理界面
 */

class DAGController {
    constructor() {
        this.cy = null;
        this.layoutOptions = {
            name: 'dagre',
            rankDir: 'TB',
            animate: true,
            animationDuration: 500
        };
        this.wsClient = null;
        this.init();
    }

    // 初始化
    init() {
        this.initCytoscape();
        this.initWebSocket();
        this.setupEventListeners();
    }

    // 初始化Cytoscape
    initCytoscape() {
        this.cy = cytoscape({
            container: document.getElementById('dag-container'),
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#666',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': 'white',
                        'font-size': '12px',
                        'width': '80px',
                        'height': '40px',
                        'shape': 'roundrectangle'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    }
                }
            ],
            layout: this.layoutOptions
        });
    }

    // 初始化WebSocket连接
    initWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            this.wsClient = new WebSocket(wsUrl);
            
            this.wsClient.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket消息解析失败:', error);
                }
            };
        } catch (error) {
            console.warn('WebSocket连接失败:', error);
        }
    }

    // 处理WebSocket消息
    handleWebSocketMessage(data) {
        if (data.type === 'mcp_response') {
            this.handleMCPToolResponse(data.payload);
        }
    }

    // 设置事件监听器
    setupEventListeners() {
        // 绑定按钮事件
        document.getElementById('loadDAG')?.addEventListener('click', () => this.loadSavedDAG());
        document.getElementById('saveDAG')?.addEventListener('click', () => this.saveDAG());
        document.getElementById('syncDAG')?.addEventListener('click', () => this.syncDAGData());
        document.getElementById('refreshDAG')?.addEventListener('click', () => this.refreshDAGView());
        document.getElementById('buildFunction')?.addEventListener('click', () => this.buildFunctionLayer());
        document.getElementById('buildLogic')?.addEventListener('click', () => this.buildLogicLayer());
        document.getElementById('buildCode')?.addEventListener('click', () => this.buildCodeLayer());
        document.getElementById('buildOrder')?.addEventListener('click', () => this.buildOrderLayer());
    }

    // 调用MCP工具
    async callMCPTool(toolName, parameters = {}) {
        try {
            const response = await fetch('/call_mcp_tool', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tool: toolName,
                    params: parameters
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('MCP工具调用失败:', error);
            throw error;
        }
    }

    // 调用多个MCP工具
    async callMCPTools(tools) {
        try {
            const response = await fetch('/call_mcp_tools', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ tools })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('批量MCP工具调用失败:', error);
            throw error;
        }
    }

    // 调用四层DAG构建工具
    async callFourLayerDAGTools(layerType, params) {
        const toolMap = {
            'function': 'build_function_layer_dag',
            'logic': 'build_logic_layer_dag', 
            'code': 'build_code_layer_dag',
            'order': 'build_order_layer_dag'
        };

        const toolName = toolMap[layerType];
        if (!toolName) {
            throw new Error(`未知的层级类型: ${layerType}`);
        }

        return await this.callMCPTool(toolName, params);
    }

    // 处理MCP工具响应
    handleMCPToolResponse(response) {
        if (response.success && response.dag_data) {
            this.loadDAGFromResponse(response);
            this.updateUI(`${response.layer_name} 构建成功`, 'success');
        } else {
            this.updateUI(`DAG构建失败: ${response.error || '未知错误'}`, 'error');
        }
    }

    // 从响应加载DAG
    loadDAGFromResponse(response) {
        try {
            const dagData = response.dag_data;
            
            // 清空当前图
            this.cy.elements().remove();
            
            // 添加节点和边
            if (dagData.nodes) {
                this.cy.add(dagData.nodes);
            }
            if (dagData.edges) {
                this.cy.add(dagData.edges);
            }
            
            // 应用布局
            this.cy.layout(this.layoutOptions).run();
            
            // 显示层级信息
            this.displayLayerInfo(response);
            
        } catch (error) {
            console.error('加载DAG失败:', error);
            this.updateUI('加载DAG失败: ' + error.message, 'error');
        }
    }

    // 构建功能层DAG
    async buildFunctionLayer() {
        try {
            const businessReq = document.getElementById('businessRequirements')?.value || '';
            const projectDesc = document.getElementById('projectDescription')?.value || '';
            
            if (!businessReq && !projectDesc) {
                this.updateUI('请输入业务需求或项目描述', 'warning');
                return;
            }

            this.updateUI('正在构建功能层DAG...', 'info');
            
            const response = await this.callFourLayerDAGTools('function', {
                business_requirements: businessReq,
                project_description: projectDesc,
                mermaid_dag: ''
            });

            this.handleMCPToolResponse(response);
            
        } catch (error) {
            console.error('构建功能层失败:', error);
            this.updateUI('构建功能层失败: ' + error.message, 'error');
        }
    }

    // 构建逻辑层DAG
    async buildLogicLayer() {
        try {
            const techArch = document.getElementById('technicalArchitecture')?.value || '';
            
            this.updateUI('正在构建逻辑层DAG...', 'info');
            
            const response = await this.callFourLayerDAGTools('logic', {
                function_layer_result: '',
                technical_architecture: techArch,
                mermaid_dag: ''
            });

            this.handleMCPToolResponse(response);
            
        } catch (error) {
            console.error('构建逻辑层失败:', error);
            this.updateUI('构建逻辑层失败: ' + error.message, 'error');
        }
    }

    // 构建代码层DAG
    async buildCodeLayer() {
        try {
            const implDetails = document.getElementById('implementationDetails')?.value || '';
            
            this.updateUI('正在构建代码层DAG...', 'info');
            
            const response = await this.callFourLayerDAGTools('code', {
                logic_layer_result: '',
                implementation_details: implDetails,
                mermaid_dag: ''
            });

            this.handleMCPToolResponse(response);
            
        } catch (error) {
            console.error('构建代码层失败:', error);
            this.updateUI('构建代码层失败: ' + error.message, 'error');
        }
    }

    // 构建排序层DAG
    async buildOrderLayer() {
        try {
            const execStrategy = document.getElementById('executionStrategy')?.value || '';
            
            this.updateUI('正在构建排序层DAG...', 'info');
            
            const response = await this.callFourLayerDAGTools('order', {
                code_layer_result: '',
                execution_strategy: execStrategy,
                mermaid_dag: ''
            });

            this.handleMCPToolResponse(response);
            
        } catch (error) {
            console.error('构建排序层失败:', error);
            this.updateUI('构建排序层失败: ' + error.message, 'error');
        }
    }

    // 保存DAG
    async saveDAG() {
        try {
            const elements = this.cy.elements().jsons();
            const dagData = {
                nodes: elements.filter(el => el.group === 'nodes'),
                edges: elements.filter(el => el.group === 'edges'),
                timestamp: new Date().toISOString()
            };

            // 保存到localStorage
            const savedDAGs = JSON.parse(localStorage.getItem('savedDAGs') || '{}');
            const key = `dag_${Date.now()}`;
            savedDAGs[key] = dagData;
            localStorage.setItem('savedDAGs', JSON.stringify(savedDAGs));

            this.updateUI('DAG已保存到本地存储', 'success');
        } catch (error) {
            console.error('保存DAG失败:', error);
            this.updateUI('保存DAG失败: ' + error.message, 'error');
        }
    }

    // 加载已保存的DAG
    async loadSavedDAG() {
        try {
            // 首先尝试从新的API端点直接读取DAG数据
            const response = await fetch('/api/dag-data');
            
            if (response.ok) {
                const savedDags = await response.json();
                
                if (savedDags.success && savedDags.summary.total_files > 0) {
                    // 创建选择对话框
                    const selectedDAG = await this.showDAGSelectionDialog(savedDags);
                    
                    if (selectedDAG) {
                        // 加载选中的DAG
                        this.loadDAGFromData(selectedDAG);
                        this.updateUI('已加载保存的DAG (直接API)', 'success');
                        return;
                    }
                } else if (savedDags.success) {
                    this.updateUI(savedDags.message || '没有找到DAG文件', 'warning');
                    return;
                }
            }
            
            // 如果API调用失败，回退到MCP工具调用
            this.updateUI('正在通过MCP工具获取DAG数据...', 'info');
            const mcpResponse = await this.callMCPTool('get_saved_dags', {});
            
            if (mcpResponse.result && mcpResponse.result.success) {
                const savedDags = mcpResponse.result;
                
                if (savedDags.summary.total_files > 0) {
                    // 创建选择对话框
                    const selectedDAG = await this.showDAGSelectionDialog(savedDags);
                    
                    if (selectedDAG) {
                        // 加载选中的DAG
                        this.loadDAGFromData(selectedDAG);
                        this.updateUI('已加载保存的DAG (MCP工具)', 'success');
                        return;
                    }
                }
            }
            
            // 最后尝试从localStorage加载
            const savedDAGs = localStorage.getItem('savedDAGs');
            if (savedDAGs) {
                const dags = JSON.parse(savedDAGs);
                
                // 显示可用的DAG列表
                const keys = Object.keys(dags);
                if (keys.length === 0) {
                    this.updateUI('没有找到已保存的DAG', 'warning');
                    return;
                }
                
                // 简单选择第一个
                const firstKey = keys[0];
                const dagData = dags[firstKey];
                
                this.loadDAGFromData(dagData);
                this.updateUI('已加载保存的DAG (localStorage)', 'success');
            } else {
                this.updateUI('没有找到已保存的DAG', 'warning');
            }
        } catch (error) {
            console.error('加载DAG失败:', error);
            this.updateUI('加载DAG失败: ' + error.message, 'error');
        }
    }
    
    // 显示DAG选择对话框
    async showDAGSelectionDialog(savedDags) {
        return new Promise((resolve) => {
            // 创建模态框
            const modal = document.createElement('div');
            modal.className = 'dag-selection-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>选择要加载的DAG</h3>
                        <span class="close" onclick="this.closest('.dag-selection-modal').remove()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="dag-summary">
                            <p>项目路径: ${savedDags.project_path}</p>
                            <p>找到 ${savedDags.summary.total_files} 个DAG文件，涵盖 ${savedDags.summary.layers_found.length} 个层级</p>
                        </div>
                        <div class="dag-list">
                            ${this.renderDAGList(savedDags.dags)}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-cancel" onclick="this.closest('.dag-selection-modal').remove()">取消</button>
                    </div>
                </div>
            `;
            
            // 添加样式
            const style = document.createElement('style');
            style.textContent = `
                .dag-selection-modal {
                    position: fixed;
                    z-index: 10000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .dag-selection-modal .modal-content {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    max-width: 80%;
                    max-height: 80%;
                    overflow-y: auto;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                }
                .dag-selection-modal .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }
                .dag-selection-modal .close {
                    font-size: 24px;
                    cursor: pointer;
                    color: #aaa;
                }
                .dag-selection-modal .close:hover {
                    color: #000;
                }
                .dag-summary {
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                }
                .dag-item {
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }
                .dag-item:hover {
                    background-color: #f0f0f0;
                }
                .dag-layer-title {
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 10px;
                }
                .dag-file-info {
                    font-size: 0.9em;
                    color: #666;
                }
                .btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin: 0 5px;
                }
                .btn-cancel {
                    background: #6c757d;
                    color: white;
                }
            `;
            
            document.head.appendChild(style);
            document.body.appendChild(modal);
            
            // 添加点击事件
            modal.addEventListener('click', (e) => {
                if (e.target.classList.contains('dag-item')) {
                    const dagData = JSON.parse(e.target.dataset.dagData);
                    modal.remove();
                    style.remove();
                    resolve(dagData);
                } else if (e.target === modal) {
                    modal.remove();
                    style.remove();
                    resolve(null);
                }
            });
        });
    }
    
    // 渲染DAG列表
    renderDAGList(dags) {
        let html = '';
        
        for (const [layerType, files] of Object.entries(dags)) {
            if (files && files.length > 0) {
                html += `<div class="dag-layer-title">${layerType.toUpperCase()} Layer (${files.length} 个文件)</div>`;
                
                files.forEach(file => {
                    html += `
                        <div class="dag-item" data-dag-data='${JSON.stringify(file.dag_data)}'>
                            <div><strong>${file.layer_name}</strong></div>
                            <div class="dag-file-info">
                                文件: ${file.file_name}<br>
                                时间: ${file.timestamp || file.created_time}<br>
                                大小: ${(file.file_size / 1024).toFixed(1)} KB
                            </div>
                        </div>
                    `;
                });
            }
        }
        
        if (!html) {
            html = '<p>没有找到DAG文件</p>';
        }
        
        return html;
    }
    
    // 从DAG数据加载
    loadDAGFromData(dagData) {
        try {
            // 清空当前图
            this.cy.elements().remove();
            
            // 加载节点和边
            if (dagData.dag_data && dagData.dag_data.nodes) {
                this.cy.add(dagData.dag_data.nodes);
            }
            if (dagData.dag_data && dagData.dag_data.edges) {
                this.cy.add(dagData.dag_data.edges);
            }
            
            // 应用布局
            this.cy.layout(this.layoutOptions).run();
            
            // 更新层级信息显示
            this.displayLayerInfo(dagData);
            
        } catch (error) {
            console.error('加载DAG数据失败:', error);
            throw error;
        }
    }
    
    // 显示层级信息
    displayLayerInfo(dagData) {
        const infoPanel = document.getElementById('layerInfo');
        if (infoPanel && dagData) {
            infoPanel.innerHTML = `
                <h4>${dagData.layer_name || 'DAG Layer'}</h4>
                <p><strong>类型:</strong> ${dagData.layer_type || 'Unknown'}</p>
                <p><strong>文件:</strong> ${dagData.file_name || 'Unknown'}</p>
                <p><strong>时间:</strong> ${dagData.timestamp || dagData.created_time || 'Unknown'}</p>
                ${dagData.layer_description ? `<p><strong>描述:</strong> ${dagData.layer_description}</p>` : ''}
            `;
        }
    }

    // 更新UI状态
    updateUI(message, type = 'info') {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status ${type}`;
            
            // 3秒后清除状态
            setTimeout(() => {
                if (statusElement.textContent === message) {
                    statusElement.textContent = '';
                    statusElement.className = 'status';
                }
            }, 3000);
        }
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    // 同步DAG数据 - 直接从API获取
    async syncDAGData() {
        try {
            this.updateUI('正在同步DAG数据...', 'info');
            
            const response = await fetch('/api/dag-data');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const dagData = await response.json();
            
            if (dagData.success) {
                // 更新页面显示
                this.updateDAGSummary(dagData.summary);
                this.updateUI(`同步成功！找到 ${dagData.summary.total_files} 个DAG文件`, 'success');
                
                // 如果有DAG文件，显示最新的一个
                if (dagData.summary.total_files > 0) {
                    this.displayAvailableDAGs(dagData.dags);
                }
            } else {
                this.updateUI(dagData.error || '同步失败', 'error');
            }
            
        } catch (error) {
            console.error('同步DAG数据失败:', error);
            this.updateUI('同步失败: ' + error.message, 'error');
        }
    }
    
    // 刷新DAG视图
    async refreshDAGView() {
        try {
            this.updateUI('正在刷新视图...', 'info');
            
            // 重新应用布局
            if (this.cy.elements().length > 0) {
                this.cy.layout(this.layoutOptions).run();
                this.updateUI('视图已刷新', 'success');
            } else {
                this.updateUI('没有DAG数据可显示', 'warning');
            }
            
        } catch (error) {
            console.error('刷新视图失败:', error);
            this.updateUI('刷新失败: ' + error.message, 'error');
        }
    }
    
    // 更新DAG摘要信息
    updateDAGSummary(summary) {
        const summaryElement = document.getElementById('dagSummary');
        if (summaryElement) {
            summaryElement.innerHTML = `
                <div class="dag-summary-card">
                    <h4>📊 DAG数据概览</h4>
                    <div class="summary-stats">
                        <div class="stat-item">
                            <span class="stat-label">总文件数:</span>
                            <span class="stat-value">${summary.total_files}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">层级类型:</span>
                            <span class="stat-value">${summary.layers_found.join(', ') || '无'}</span>
                        </div>
                        ${Object.entries(summary.layer_counts).map(([layer, count]) => `
                            <div class="stat-item">
                                <span class="stat-label">${layer}层:</span>
                                <span class="stat-value">${count}个</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    }
    
    // 显示可用的DAG列表
    displayAvailableDAGs(dags) {
        const listElement = document.getElementById('dagList');
        if (listElement) {
            let html = '<div class="available-dags"><h4>📁 可用的DAG文件</h4>';
            
            for (const [layerType, files] of Object.entries(dags)) {
                if (files && files.length > 0) {
                    html += `
                        <div class="layer-group">
                            <div class="layer-header">${layerType.toUpperCase()} Layer (${files.length})</div>
                            <div class="file-list">
                    `;
                    
                    files.forEach((file, index) => {
                        html += `
                            <div class="file-item" onclick="window.dagController.loadSpecificDAG('${layerType}', ${index})">
                                <div class="file-name">${file.layer_name}</div>
                                <div class="file-info">
                                    ${file.file_name} | ${(file.file_size / 1024).toFixed(1)}KB | ${file.timestamp.split('T')[0]}
                                </div>
                            </div>
                        `;
                    });
                    
                    html += '</div></div>';
                }
            }
            
            html += '</div>';
            listElement.innerHTML = html;
            
            // 保存DAG数据以供后续使用
            this.cachedDAGData = dags;
        }
    }
    
    // 加载特定的DAG文件
    async loadSpecificDAG(layerType, fileIndex) {
        try {
            if (!this.cachedDAGData || !this.cachedDAGData[layerType]) {
                this.updateUI('DAG数据不可用，请先同步', 'warning');
                return;
            }
            
            const file = this.cachedDAGData[layerType][fileIndex];
            if (!file) {
                this.updateUI('指定的DAG文件不存在', 'error');
                return;
            }
            
            this.loadDAGFromData(file);
            this.updateUI(`已加载 ${file.layer_name}`, 'success');
            
        } catch (error) {
            console.error('加载特定DAG失败:', error);
            this.updateUI('加载失败: ' + error.message, 'error');
        }
    }
    
    // 更新统计信息 - 接收来自DAGManager的统计数据
    updateStatistics(stats) {
        console.log('📊 接收到统计信息更新:', stats);
        
        // 更新各层级计数器的显示 - 使用HTML模板中实际定义的ID
        const updates = [
            { selector: '#functionNodesCount', value: stats.function, layer: 'Function' },
            { selector: '#logicNodesCount', value: stats.logic, layer: 'Logic' },
            { selector: '#codeNodesCount', value: stats.code, layer: 'Code' },
            { selector: '#orderNodesCount', value: stats.order, layer: 'Order' }
        ];
        
        updates.forEach(update => {
            const element = document.querySelector(update.selector);
            if (element) {
                element.textContent = update.value;
                console.log(`📊 更新${update.layer}层计数器: ${update.value}`);
            } else {
                console.warn(`⚠️ 找不到${update.layer}层计数器元素: ${update.selector}`);
            }
        });
        
        // 更新总节点数显示
        const totalNodes = Object.values(stats).reduce((sum, count) => sum + count, 0);
        const totalElement = document.querySelector('#total-nodes, .total-nodes-count');
        if (totalElement) {
            totalElement.textContent = totalNodes;
            console.log(`📊 更新总节点数: ${totalNodes}`);
        }
        
        // 更新状态指示
        const hasData = totalNodes > 0;
        const statusElement = document.querySelector('#dag-status, .dag-status');
        if (statusElement) {
            statusElement.textContent = hasData ? `已加载 ${totalNodes} 个节点` : '无DAG数据';
            statusElement.className = hasData ? 'dag-status loaded' : 'dag-status empty';
        }
        
        console.log(`📊 统计信息更新完成，总计 ${totalNodes} 个节点`);
    }
}

// 导出类
window.DAGController = DAGController; 