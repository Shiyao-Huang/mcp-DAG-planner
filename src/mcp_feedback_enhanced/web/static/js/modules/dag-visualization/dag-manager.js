#!/usr/bin/env
/**
 * 四层DAG可视化管理器
 * ===================
 * 
 * Version: v1.0.0
 * Author: AI Assistant + User
 * Date: 2024-12-20
 * Purpose: 集成ReactFlow实现四层DAG的可视化展示和编辑
 * Dependencies: ReactFlow, DAGRE, Mermaid, WebSocket, MCP协议
 */

/**
 * ```mermaid
 * graph TD
 *     A[DAGManager] --> B[ReactFlow渲染器]
 *     A --> C[DAGRE布局算法] 
 *     A --> D[Mermaid解析器]
 *     A --> E[WebSocket通信]
 *     A --> F[四层数据模型]
 *     
 *     B --> G[节点组件]
 *     B --> H[边组件]
 *     B --> I[控制面板]
 *     
 *     C --> J[自动布局]
 *     C --> K[层级排列]
 *     
 *     D --> L[Mermaid转ReactFlow]
 *     D --> M[格式验证]
 *     
 *     E --> N[实时同步]
 *     E --> O[状态更新]
 *     
 *     F --> P[功能层Function]
 *     F --> Q[逻辑层Logic]
 *     F --> R[代码层Code]
 *     F --> S[排序层Order]
 * ```
 */

(function() {
    'use strict';

    // 确保命名空间存在
    window.MCPFeedback = window.MCPFeedback || {};
    window.MCPFeedback.DAG = window.MCPFeedback.DAG || {};

    /**
     * 四层DAG管理器
     */
    function DAGManager(options) {
        this.options = Object.assign({
            containerId: 'dag-container',
            enableEdit: true,
            enableSync: true,
            layoutAlgorithm: 'dagre',
            onNodeSelect: null,
            onEdgeSelect: null,
            onLayoutChange: null,
            onDataChange: null
        }, options || {});

        // 四层DAG数据模型
        this.dagLayers = {
            function: { nodes: [], edges: [], visible: true, color: '#4CAF50' },
            logic: { nodes: [], edges: [], visible: true, color: '#2196F3' },
            code: { nodes: [], edges: [], visible: true, color: '#FF9800' },
            order: { nodes: [], edges: [], visible: true, color: '#9C27B0' }
        };

        // ReactFlow 相关
        this.reactFlowInstance = null;
        this.currentLayer = 'function';
        this.viewMode = 'single'; // single, multi, integrated
        
        // DAGRE 布局算法
        this.dagreGraph = null;
        this.layoutConfig = {
            rankdir: 'TB',
            nodesep: 100,
            ranksep: 100,
            marginx: 50,
            marginy: 50
        };

        // WebSocket 通信
        this.webSocketManager = null;
        this.syncEnabled = this.options.enableSync;

        // Mermaid 解析器
        this.mermaidParser = null;

        // 状态管理
        this.isInitialized = false;
        this.isDirty = false;
        this.lastSavedState = null;

        console.log('🎨 DAGManager 初始化完成');
    }

    /**
     * 初始化DAG管理器
     */
    DAGManager.prototype.init = function() {
        const self = this;

        return new Promise(function(resolve, reject) {
            try {
                self.initializeContainer()
                    .then(function() {
                        return self.initializeMermaidParser();
                    })
                    .then(function() {
                        return self.setupWebSocketSync();
                    })
                    .then(function() {
                        return self.setupEventListeners();
                    })
                    .then(function() {
                        self.isInitialized = true;
                        console.log('✅ DAGManager 初始化完成');
                        resolve();
                    })
                    .catch(function(error) {
                        console.error('❌ DAGManager 初始化失败:', error);
                        reject(error);
                    });
            } catch (error) {
                console.error('❌ DAGManager 初始化异常:', error);
                reject(error);
            }
        });
    };

    /**
     * 初始化容器
     */
    DAGManager.prototype.initializeContainer = function() {
        const self = this;

        return new Promise(function(resolve) {
            const container = document.getElementById(self.options.containerId);
            if (!container) {
                throw new Error('DAG 容器不存在: ' + self.options.containerId);
            }

            // 设置容器样式
            container.style.width = '100%';
            container.style.height = '600px';
            container.style.border = '1px solid #ddd';
            container.style.borderRadius = '8px';
            container.style.position = 'relative';

            // 创建层级控制面板
            self.createLayerControls(container);

            // 创建 SVG 容器
            self.createSVGRenderer(container);

            resolve();
        });
    };

    /**
     * 创建层级控制面板
     */
    DAGManager.prototype.createLayerControls = function(container) {
        const controlPanel = document.createElement('div');
        controlPanel.className = 'dag-layer-controls';
        controlPanel.style.cssText = `
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        `;

        // 视图模式切换
        const viewModeSelect = document.createElement('select');
        viewModeSelect.innerHTML = `
            <option value="single">单层视图</option>
            <option value="multi">多层视图</option>
            <option value="integrated">集成视图</option>
        `;
        viewModeSelect.addEventListener('change', (e) => {
            this.setViewMode(e.target.value);
        });

        // 层级切换按钮
        const layerButtons = document.createElement('div');
        layerButtons.style.marginTop = '10px';

        Object.keys(this.dagLayers).forEach(layer => {
            const button = document.createElement('button');
            button.textContent = this.getLayerDisplayName(layer);
            button.style.cssText = `
                margin-right: 5px;
                padding: 5px 10px;
                border: 1px solid ${this.dagLayers[layer].color};
                background: ${layer === this.currentLayer ? this.dagLayers[layer].color : 'white'};
                color: ${layer === this.currentLayer ? 'white' : this.dagLayers[layer].color};
                border-radius: 4px;
                cursor: pointer;
            `;
            button.addEventListener('click', () => {
                this.setCurrentLayer(layer);
            });
            layerButtons.appendChild(button);
        });

        controlPanel.appendChild(viewModeSelect);
        controlPanel.appendChild(layerButtons);
        container.appendChild(controlPanel);

        this.controlPanel = controlPanel;
    };

    /**
     * 创建SVG渲染器
     */
    DAGManager.prototype.createSVGRenderer = function(container) {
        const svgContainer = document.createElement('div');
        svgContainer.id = 'svg-container';
        svgContainer.style.cssText = `
            width: 100%;
            height: 100%;
            overflow: hidden;
        `;

        // 创建SVG元素
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.background = '#fafafa';

        // 添加定义
        const defs = this.createSVGDefs();
        svg.appendChild(defs);

        // 添加网格背景
        const gridRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        gridRect.setAttribute('width', '100%');
        gridRect.setAttribute('height', '100%');
        gridRect.setAttribute('fill', 'url(#grid)');
        svg.appendChild(gridRect);

        // 主绘图组
        this.svgGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        svg.appendChild(this.svgGroup);

        svgContainer.appendChild(svg);
        container.appendChild(svgContainer);

        this.svg = svg;
        this.svgContainer = svgContainer;

        console.log('📊 SVG 渲染器创建完成');
    };

    /**
     * 创建SVG定义
     */
    DAGManager.prototype.createSVGDefs = function() {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

        // 网格模式
        const pattern = document.createElementNS('http://www.w3.org/2000/svg', 'pattern');
        pattern.setAttribute('id', 'grid');
        pattern.setAttribute('width', '20');
        pattern.setAttribute('height', '20');
        pattern.setAttribute('patternUnits', 'userSpaceOnUse');

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 20 0 L 0 0 0 20');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', '#e0e0e0');
        path.setAttribute('stroke-width', '1');

        pattern.appendChild(path);
        defs.appendChild(pattern);

        // 箭头标记
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrowhead');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '7');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '3.5');
        marker.setAttribute('orient', 'auto');

        const arrowPath = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrowPath.setAttribute('points', '0 0, 10 3.5, 0 7');
        arrowPath.setAttribute('fill', '#666');

        marker.appendChild(arrowPath);
        defs.appendChild(marker);

        return defs;
    };

    /**
     * 初始化 Mermaid 解析器
     */
    DAGManager.prototype.initializeMermaidParser = function() {
        const self = this;

        return new Promise(function(resolve) {
            self.mermaidParser = {
                parse: function(mermaidText) {
                    return self.parseMermaidText(mermaidText);
                }
            };
            console.log('🧩 Mermaid 解析器初始化完成');
            resolve();
        });
    };

    /**
     * 解析 Mermaid 文本
     */
    DAGManager.prototype.parseMermaidText = function(mermaidText) {
        const lines = mermaidText.split('\n').filter(line => line.trim());
        const nodes = [];
        const edges = [];
        const nodeMap = new Set();

        lines.forEach(line => {
            line = line.trim();

            // 跳过图形声明和注释
            if (line.startsWith('graph') || line.startsWith('%%') || !line) {
                return;
            }

            // 解析节点定义: A[label] 或 A(label)
            const nodeMatch = line.match(/(\w+)\[(.*?)\]|(\w+)\((.*?)\)/);
            if (nodeMatch) {
                const id = nodeMatch[1] || nodeMatch[3];
                const label = nodeMatch[2] || nodeMatch[4];
                if (!nodeMap.has(id)) {
                    nodes.push({
                        id: id,
                        data: { label: label },
                        position: { x: 0, y: 0 }
                    });
                    nodeMap.add(id);
                }
            }

            // 解析边定义: A --> B 或 A -> B
            const edgeMatch = line.match(/(\w+)\s*--?>\s*(\w+)/);
            if (edgeMatch) {
                const sourceId = edgeMatch[1];
                const targetId = edgeMatch[2];

                // 确保源和目标节点存在
                if (!nodeMap.has(sourceId)) {
                    nodes.push({
                        id: sourceId,
                        data: { label: sourceId },
                        position: { x: 0, y: 0 }
                    });
                    nodeMap.add(sourceId);
                }
                if (!nodeMap.has(targetId)) {
                    nodes.push({
                        id: targetId,
                        data: { label: targetId },
                        position: { x: 0, y: 0 }
                    });
                    nodeMap.add(targetId);
                }

                edges.push({
                    id: `${sourceId}-${targetId}`,
                    source: sourceId,
                    target: targetId
                });
            }
        });

        return { nodes, edges };
    };

    /**
     * 设置 WebSocket 同步
     */
    DAGManager.prototype.setupWebSocketSync = function() {
        const self = this;

        return new Promise(function(resolve) {
            if (self.syncEnabled && window.MCPFeedback && window.MCPFeedback.WebSocketManager) {
                // 等待WebSocket管理器初始化
                setTimeout(function() {
                    self.webSocketManager = window.MCPFeedback.WebSocketManager;

                    if (self.webSocketManager) {
                        console.log('🔄 WebSocket 同步设置完成');
                    }
                }, 1000);
            }
            resolve();
        });
    };

    /**
     * 设置事件监听器
     */
    DAGManager.prototype.setupEventListeners = function() {
        const self = this;

        return new Promise(function(resolve) {
            // 窗口大小变化
            window.addEventListener('resize', function() {
                self.handleResize();
            });

            console.log('👂 事件监听器设置完成');
            resolve();
        });
    };

    /**
     * 获取层级显示名称
     */
    DAGManager.prototype.getLayerDisplayName = function(layer) {
        const names = {
            function: '功能层',
            logic: '逻辑层',
            code: '代码层',
            order: '排序层'
        };
        return names[layer] || layer;
    };

    /**
     * 加载DAG数据
     */
    DAGManager.prototype.loadDAG = function(layer, data) {
        if (!this.dagLayers[layer]) {
            throw new Error('无效的层级: ' + layer);
        }

        try {
            // 处理不同的输入格式
            if (typeof data === 'string') {
                // Mermaid 格式
                const parsed = this.mermaidParser.parse(data);
                this.dagLayers[layer].nodes = parsed.nodes;
                this.dagLayers[layer].edges = parsed.edges;
            } else if (data.nodes && data.edges) {
                // ReactFlow 格式
                this.dagLayers[layer].nodes = data.nodes;
                this.dagLayers[layer].edges = data.edges;
            } else {
                throw new Error('不支持的数据格式');
            }

            // 应用布局
            this.applySimpleLayout(layer);

            // 渲染
            this.render();

            // 标记为已修改
            this.isDirty = true;
            
            // 保存更改
            this.saveDAG();

            console.log(`📥 加载 ${layer} 层数据完成 - 节点: ${this.dagLayers[layer].nodes.length}, 边: ${this.dagLayers[layer].edges.length}`);
        } catch (error) {
            console.error(`❌ 加载 ${layer} 层数据失败:`, error);
            throw error;
        }
    };

    /**
     * 从外部（如WebSocket）更新DAG数据
     */
    DAGManager.prototype.updateDAGFromExternal = function(data) {
        try {
            if (data && data.layer && data.dag) {
                const { layer, dag } = data;
                this.loadDAG(layer, dag);
                this.setCurrentLayer(layer);
                console.log(`🔄 从外部更新 ${layer} 层DAG数据完成`);
            }
        } catch (error) {
            console.error('❌ 从外部更新DAG数据失败:', error);
        }
    };

    /**
     * 简单布局算法
     */
    DAGManager.prototype.applySimpleLayout = function(layer) {
        const layerData = this.dagLayers[layer];
        const nodesPerRow = Math.ceil(Math.sqrt(layerData.nodes.length));

        layerData.nodes.forEach((node, index) => {
            const row = Math.floor(index / nodesPerRow);
            const col = index % nodesPerRow;

            node.position = {
                x: col * 150 + 100,
                y: row * 100 + 100
            };
        });

        console.log(`📐 ${layer} 层简单布局完成`);
    };

    /**
     * 渲染DAG图形
     */
    DAGManager.prototype.render = function() {
        if (!this.isInitialized) {
            return;
        }

        // 清除之前的渲染
        this.svgGroup.innerHTML = '';

        // 根据视图模式渲染
        switch (this.viewMode) {
            case 'single':
                this.renderSingleLayer();
                break;
            case 'multi':
                this.renderMultiLayer();
                break;
            case 'integrated':
                this.renderIntegratedView();
                break;
        }

        console.log(`🎨 渲染完成 - 模式: ${this.viewMode}`);
    };

    /**
     * 渲染单层视图
     */
    DAGManager.prototype.renderSingleLayer = function() {
        const layerData = this.dagLayers[this.currentLayer];
        this.renderLayerNodes(layerData, this.currentLayer);
        this.renderLayerEdges(layerData, this.currentLayer);
    };

    /**
     * 渲染多层视图
     */
    DAGManager.prototype.renderMultiLayer = function() {
        let yOffset = 0;

        Object.keys(this.dagLayers).forEach(layer => {
            if (this.dagLayers[layer].visible) {
                const layerGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                layerGroup.setAttribute('transform', `translate(0, ${yOffset})`);

                // 添加层级标题
                const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                title.setAttribute('x', '20');
                title.setAttribute('y', '20');
                title.setAttribute('font-size', '16');
                title.setAttribute('font-weight', 'bold');
                title.setAttribute('fill', this.dagLayers[layer].color);
                title.textContent = this.getLayerDisplayName(layer);
                layerGroup.appendChild(title);

                this.renderLayerNodes(this.dagLayers[layer], layer, layerGroup, { yOffset: 30 });
                this.renderLayerEdges(this.dagLayers[layer], layer, layerGroup, { yOffset: 30 });

                this.svgGroup.appendChild(layerGroup);
                yOffset += 250; // 层级间距
            }
        });
    };

    /**
     * 渲染集成视图
     */
    DAGManager.prototype.renderIntegratedView = function() {
        // 渲染所有层级在同一视图中，不同颜色区分
        Object.keys(this.dagLayers).forEach(layer => {
            if (this.dagLayers[layer].visible) {
                this.renderLayerNodes(this.dagLayers[layer], layer);
                this.renderLayerEdges(this.dagLayers[layer], layer);
            }
        });
    };

    /**
     * 渲染层级节点
     */
    DAGManager.prototype.renderLayerNodes = function(layerData, layer, container, offset) {
        const group = container || this.svgGroup;
        const color = this.dagLayers[layer].color;
        const yOffset = offset?.yOffset || 0;

        layerData.nodes.forEach(node => {
            const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            nodeGroup.setAttribute('class', `node node-${layer}`);
            nodeGroup.setAttribute('transform', `translate(${node.position.x}, ${node.position.y + yOffset})`);

            // 节点矩形
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('width', '120');
            rect.setAttribute('height', '60');
            rect.setAttribute('rx', '8');
            rect.setAttribute('fill', color);
            rect.setAttribute('stroke', '#fff');
            rect.setAttribute('stroke-width', '2');

            // 节点文本
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', '60');
            text.setAttribute('y', '35');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.setAttribute('fill', 'white');
            text.setAttribute('font-size', '12');
            text.textContent = node.data.label;

            nodeGroup.appendChild(rect);
            nodeGroup.appendChild(text);

            // 添加交互事件
            nodeGroup.addEventListener('click', () => {
                this.handleNodeClick(node, layer);
            });

            nodeGroup.style.cursor = 'pointer';
            group.appendChild(nodeGroup);
        });
    };

    /**
     * 渲染层级边
     */
    DAGManager.prototype.renderLayerEdges = function(layerData, layer, container, offset) {
        const group = container || this.svgGroup;
        const color = this.dagLayers[layer].color;
        const yOffset = offset?.yOffset || 0;

        layerData.edges.forEach(edge => {
            const sourceNode = layerData.nodes.find(n => n.id === edge.source);
            const targetNode = layerData.nodes.find(n => n.id === edge.target);

            if (sourceNode && targetNode) {
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

                const sx = sourceNode.position.x + 60;
                const sy = sourceNode.position.y + 60 + yOffset;
                const tx = targetNode.position.x + 60;
                const ty = targetNode.position.y + yOffset;

                const pathData = `M ${sx} ${sy} Q ${sx} ${sy + 30} ${tx} ${ty}`;

                path.setAttribute('d', pathData);
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke', color);
                path.setAttribute('stroke-width', '2');
                path.setAttribute('marker-end', 'url(#arrowhead)');

                group.appendChild(path);
            }
        });
    };

    /**
     * 处理节点点击
     */
    DAGManager.prototype.handleNodeClick = function(node, layer) {
        console.log('节点点击:', node, layer);

        if (this.options.onNodeSelect) {
            this.options.onNodeSelect(node, layer);
        }

        // 高亮选中的节点
        this.highlightNode(node.id, layer);
    };

    /**
     * 高亮节点
     */
    DAGManager.prototype.highlightNode = function(nodeId, layer) {
        // 清除之前的高亮
        const prevHighlighted = this.svgGroup.querySelectorAll('.node-highlighted');
        prevHighlighted.forEach(el => {
            el.classList.remove('node-highlighted');
            const rect = el.querySelector('rect');
            if (rect) {
                rect.setAttribute('stroke-width', '2');
            }
        });

        // 高亮新节点
        const nodeElement = this.svgGroup.querySelector(`.node-${layer}`);
        if (nodeElement) {
            nodeElement.classList.add('node-highlighted');
            const rect = nodeElement.querySelector('rect');
            if (rect) {
                rect.setAttribute('stroke-width', '4');
            }
        }
    };

    /**
     * 设置当前层级
     */
    DAGManager.prototype.setCurrentLayer = function(layer) {
        if (this.dagLayers[layer]) {
            this.currentLayer = layer;
            this.updateLayerControls();
            this.render();

            console.log(`🎯 切换到 ${layer} 层`);
        }
    };

    /**
     * 设置视图模式
     */
    DAGManager.prototype.setViewMode = function(mode) {
        this.viewMode = mode;
        this.render();

        console.log(`👁️ 切换视图模式: ${mode}`);
    };

    /**
     * 更新层级控制面板
     */
    DAGManager.prototype.updateLayerControls = function() {
        const buttons = this.controlPanel.querySelectorAll('button');
        buttons.forEach((button, index) => {
            const layer = Object.keys(this.dagLayers)[index];
            if (layer === this.currentLayer) {
                button.style.background = this.dagLayers[layer].color;
                button.style.color = 'white';
            } else {
                button.style.background = 'white';
                button.style.color = this.dagLayers[layer].color;
            }
        });
    };

    /**
     * 处理窗口大小变化
     */
    DAGManager.prototype.handleResize = function() {
        // 重新渲染以适应新的容器大小
        this.render();
    };

    /**
     * 将所有层级的DAG数据保存到localStorage
     */
    DAGManager.prototype.saveDAG = function() {
        this.logger.info('💾 保存所有层级的数据到 localStorage...');
        try {
            const dataToSave = {};
            for (const layer in this.dagLayers) {
                if (this.dagLayers.hasOwnProperty(layer)) {
                    dataToSave[layer] = {
                        nodes: this.dagLayers[layer].nodes,
                        edges: this.dagLayers[layer].edges
                    };
                }
            }
            const jsonData = JSON.stringify(dataToSave);
            localStorage.setItem('dag-data-all', jsonData);
            this.logger.success('✅ 所有层级的数据已成功保存');
        } catch (error) {
            this.logger.error('❌ 保存所有层级的数据失败', error);
        }
    };

    /**
     * 从后端API和localStorage加载所有保存的DAG层级
     * 优先从后端API获取，如果失败则回退到localStorage
     */
    DAGManager.prototype.loadSavedDAG = function() {
        const self = this;
        this.logger.info('📥 开始加载DAG数据...');
        
        // 返回Promise确保控制器可以等待完成
        return this.syncDAGData().then(function(apiSuccess) {
            if (!apiSuccess) {
                // API获取失败，回退到localStorage
                self.loadFromLocalStorage();
            }
            return apiSuccess;
        }).catch(function(error) {
            self.logger.error('❌ API同步失败，回退到localStorage:', error);
            self.loadFromLocalStorage();
            return false;
        });
    };

    /**
     * 从localStorage加载DAG数据
     */
    DAGManager.prototype.loadFromLocalStorage = function() {
        this.logger.info('📥 从 localStorage 加载数据...');
        try {
            const jsonData = localStorage.getItem('dag-data-all');
            if (jsonData) {
                const savedData = JSON.parse(jsonData);
                for (const layer in savedData) {
                    if (this.dagLayers.hasOwnProperty(layer)) {
                        this.dagLayers[layer].nodes = savedData[layer].nodes || [];
                        this.dagLayers[layer].edges = savedData[layer].edges || [];
                    }
                }
                
                this.logger.success('✅ localStorage数据加载成功');
                this.render();
            } else {
                this.logger.warn('⚠️ 未找到localStorage数据');
            }
        } catch (error) {
            this.logger.error('❌ localStorage数据加载失败', error);
        }
    };

    /**
     * 从后端API同步DAG数据
     */
    DAGManager.prototype.syncDAGData = function() {
        const self = this;
        return new Promise(function(resolve) {
            self.logger.info('🔄 从后端API同步DAG数据...');
            
            // 不传递项目路径参数，让后端自动检测
            const apiUrl = '/api/dag-data';
            
            self.logger.debug(`📡 API请求URL: ${apiUrl} (自动检测项目路径)`);
            
            fetch(apiUrl)
                .then(function(response) {
                    self.logger.debug(`📡 API响应状态: ${response.status}`);
                    if (!response.ok) {
                        throw new Error('API响应失败: ' + response.status);
                    }
                    return response.json();
                })
                .then(function(data) {
                    self.logger.debug('📦 API返回数据:', data);
                    
                    if (data.success && data.dags) {
                        self.logger.info('✅ 成功获取到API数据');
                        self.logger.info(`📁 项目路径: ${data.project_path}`);
                        self.logger.info(`📂 DAG目录: ${data.dags_directory}`);
                        
                        self.updateDAGSummary(data.summary);
                        self.displayAvailableDAGs(data.dags);
                        
                        // 如果有DAG数据，加载最新的
                        const hasData = self.loadLatestDAGFromAPI(data.dags);
                        resolve(hasData);
                    } else {
                        self.logger.warn('⚠️ API返回空数据或失败:', data);
                        resolve(false);
                    }
                })
                .catch(function(error) {
                    self.logger.error('❌ API请求失败:', error);
                    resolve(false);
                });
        });
    };

    /**
     * 从API数据中加载最新的DAG
     */
    DAGManager.prototype.loadLatestDAGFromAPI = function(dags) {
        let hasData = false;
        
        // 按层级加载最新的DAG文件
        const layerMap = {
            'function': 'function',
            'logic': 'logic', 
            'code': 'code',
            'order': 'order'
        };
        
        for (const [apiLayer, dagLayer] of Object.entries(layerMap)) {
            if (dags[apiLayer] && dags[apiLayer].length > 0) {
                const latestDAG = dags[apiLayer][0]; // 第一个是最新的（已按时间排序）
                this.loadSpecificDAG(latestDAG, dagLayer);
                hasData = true;
            }
        }
        
        if (hasData) {
            this.logger.success('✅ 从API加载DAG数据成功');
            this.render();
            this.updateStatistics(); // 更新统计信息
        }
        
        return hasData;
    };

    /**
     * 加载特定的DAG文件
     */
    DAGManager.prototype.loadSpecificDAG = function(dagInfo, targetLayer) {
        try {
            this.logger.debug(`🔍 加载${targetLayer}层DAG:`, dagInfo);
            
            // 检查数据结构
            const dagData = dagInfo.dag_data;
            if (!dagData) {
                this.logger.warn(`⚠️ ${targetLayer}层没有dag_data字段`);
                return;
            }
            
            // 尝试多种可能的Mermaid内容路径
            let mermaidContent = null;
            
            // 路径1: dag_data.input_data.mermaid_dag
            if (dagData.input_data && dagData.input_data.mermaid_dag) {
                mermaidContent = dagData.input_data.mermaid_dag;
                this.logger.debug(`📍 找到Mermaid内容 (路径1): ${mermaidContent.substring(0, 50)}...`);
            }
            // 路径2: dagData.mermaid_dag 
            else if (dagData.mermaid_dag) {
                mermaidContent = dagData.mermaid_dag;
                this.logger.debug(`📍 找到Mermaid内容 (路径2): ${mermaidContent.substring(0, 50)}...`);
            }
            // 路径3: dagInfo.input_data.mermaid_dag (直接从文件结构)
            else if (dagInfo.input_data && dagInfo.input_data.mermaid_dag) {
                mermaidContent = dagInfo.input_data.mermaid_dag;
                this.logger.debug(`📍 找到Mermaid内容 (路径3): ${mermaidContent.substring(0, 50)}...`);
            }
            
            if (mermaidContent) {
                // 解析Mermaid内容并转换为节点和边
                this.logger.debug(`🔍 解析${targetLayer}层Mermaid内容`);
                
                const parsed = this.parseMermaidToDAG(mermaidContent);
                if (parsed && this.dagLayers[targetLayer]) {
                    this.dagLayers[targetLayer].nodes = parsed.nodes || [];
                    this.dagLayers[targetLayer].edges = parsed.edges || [];
                    this.dagLayers[targetLayer].metadata = {
                        layer_name: dagInfo.layer_name || `${targetLayer} Layer`,
                        file_name: dagInfo.file_name || '',
                        timestamp: dagInfo.timestamp || '',
                        mermaid_source: mermaidContent
                    };
                    this.logger.info(`✅ 加载${targetLayer}层DAG成功，节点${parsed.nodes.length}个，边${parsed.edges.length}条`);
                } else {
                    this.logger.warn(`⚠️ ${targetLayer}层解析结果为空或目标层不存在`);
                }
            } else {
                this.logger.warn(`⚠️ ${targetLayer}层没有找到Mermaid内容`);
                this.logger.debug(`🔍 可用的数据字段:`, Object.keys(dagData));
            }
        } catch (error) {
            this.logger.error(`❌ 加载${targetLayer}层DAG失败:`, error);
        }
    };

    /**
     * 显示可用的DAG文件列表
     */
    DAGManager.prototype.displayAvailableDAGs = function(dags) {
        // 这里可以在UI中显示可用的DAG文件
        this.logger.info('📋 可用的DAG文件:');
        for (const [layer, files] of Object.entries(dags)) {
            if (files.length > 0) {
                this.logger.info(`  ${layer}: ${files.length}个文件`);
            }
        }
    };

    /**
     * 更新DAG摘要信息
     */
    DAGManager.prototype.updateDAGSummary = function(summary) {
        if (summary) {
            this.logger.info(`📊 DAG统计: 总计${summary.total_files}个文件，涵盖${summary.layers_found.length}个层级`);
        }
    };

    /**
     * 解析Mermaid内容为DAG节点和边
     */
    DAGManager.prototype.parseMermaidToDAG = function(mermaidContent) {
        if (!mermaidContent || typeof mermaidContent !== 'string') {
            this.logger.warn('⚠️ Mermaid内容为空或格式错误');
            return { nodes: [], edges: [] };
        }

        const nodes = [];
        const edges = [];
        const nodeSet = new Set();

        try {
            const lines = mermaidContent.split('\n');
            
            for (const line of lines) {
                const trimmed = line.trim();
                
                // 跳过注释和空行
                if (!trimmed || trimmed.startsWith('%%') || trimmed.startsWith('graph')) {
                    continue;
                }

                // 解析边关系: A --> B 或 A[Label] --> B[Label2]
                const edgeMatch = trimmed.match(/(\w+)(?:\[([^\]]+)\])?\s*-->\s*(\w+)(?:\[([^\]]+)\])?/);
                if (edgeMatch) {
                    const [, sourceId, sourceLabel, targetId, targetLabel] = edgeMatch;
                    
                    // 添加源节点
                    if (!nodeSet.has(sourceId)) {
                        nodes.push({
                            id: sourceId,
                            label: sourceLabel || sourceId,
                            x: Math.random() * 400 + 50,
                            y: Math.random() * 300 + 50
                        });
                        nodeSet.add(sourceId);
                    }
                    
                    // 添加目标节点
                    if (!nodeSet.has(targetId)) {
                        nodes.push({
                            id: targetId,
                            label: targetLabel || targetId,
                            x: Math.random() * 400 + 50,
                            y: Math.random() * 300 + 50
                        });
                        nodeSet.add(targetId);
                    }
                    
                    // 添加边
                    edges.push({
                        id: `${sourceId}-${targetId}`,
                        source: sourceId,
                        target: targetId
                    });
                }
                
                // 解析单独的节点: A[Label]
                const nodeMatch = trimmed.match(/^(\w+)\[([^\]]+)\]$/);
                if (nodeMatch && !nodeSet.has(nodeMatch[1])) {
                    const [, nodeId, nodeLabel] = nodeMatch;
                    nodes.push({
                        id: nodeId,
                        label: nodeLabel,
                        x: Math.random() * 400 + 50,
                        y: Math.random() * 300 + 50
                    });
                    nodeSet.add(nodeId);
                }
            }

            this.logger.info(`🔄 Mermaid解析完成: ${nodes.length}个节点, ${edges.length}条边`);
            return { nodes, edges };
            
        } catch (error) {
            this.logger.error('❌ Mermaid解析失败:', error);
            return { nodes: [], edges: [] };
        }
    };

    /**
     * 从外部数据更新DAG（用于WebSocket更新）
     */
    DAGManager.prototype.updateDAGFromExternal = function(data) {
        if (!data) return;
        
        this.logger.info('🔄 从外部数据更新DAG...');
        
        try {
            const layer = data.layer || 'function';
            if (data.mermaid_content && this.dagLayers[layer]) {
                const parsed = this.parseMermaidToDAG(data.mermaid_content);
                this.dagLayers[layer].nodes = parsed.nodes;
                this.dagLayers[layer].edges = parsed.edges;
                
                // 如果当前显示的是这个层级，重新渲染
                if (this.currentLayer === layer) {
                    this.render();
                }
                
                this.logger.success(`✅ ${layer}层DAG更新成功`);
            }
        } catch (error) {
            this.logger.error('❌ 外部DAG更新失败:', error);
        }
    };

    /**
     * 导出DAG数据
     */
    DAGManager.prototype.exportDAG = function(format) {
        format = format || 'json';

        switch (format) {
            case 'json':
                return JSON.stringify(this.dagLayers, null, 2);
            case 'mermaid':
                return this.exportToMermaid();
            default:
                throw new Error('不支持的导出格式: ' + format);
        }
    };

    /**
     * 导出为Mermaid格式
     */
    DAGManager.prototype.exportToMermaid = function() {
        let mermaid = 'graph TD\n';

        Object.keys(this.dagLayers).forEach(layer => {
            const layerData = this.dagLayers[layer];

            // 添加层级注释
            mermaid += `    %% ${this.getLayerDisplayName(layer)}\n`;

            // 添加边
            layerData.edges.forEach(edge => {
                mermaid += `    ${edge.source} --> ${edge.target}\n`;
            });

            mermaid += '\n';
        });

        return mermaid;
    };

    /**
     * 销毁DAG管理器
     */
    DAGManager.prototype.destroy = function() {
        // 清理事件监听器
        window.removeEventListener('resize', this.handleResize);

        // 清理DOM
        if (this.controlPanel) {
            this.controlPanel.remove();
        }

        if (this.svgContainer) {
            this.svgContainer.remove();
        }

        this.isInitialized = false;

        console.log('🗑️ DAGManager 已销毁');
    };

    /**
     * 计算各层级的统计信息
     */
    DAGManager.prototype.calculateStatistics = function() {
        const stats = {
            function: this.dagLayers.function.nodes.length,
            logic: this.dagLayers.logic.nodes.length,
            code: this.dagLayers.code.nodes.length,
            order: this.dagLayers.order.nodes.length
        };
        
        this.logger.debug('📊 计算统计信息:', stats);
        return stats;
    };

    /**
     * 更新统计信息
     */
    DAGManager.prototype.updateStatistics = function() {
        const stats = this.calculateStatistics();
        this.updateStatsInUI(stats);
        
        // 触发数据变化事件
        if (this.options.onDataChange) {
            this.options.onDataChange(stats);
        }
    };

    /**
     * 在UI中更新统计信息
     */
    DAGManager.prototype.updateStatsInUI = function(stats) {
        // 更新各层级的计数器 - 使用HTML模板中实际定义的ID
        const counterElements = {
            function: document.querySelector('#functionNodesCount'),
            logic: document.querySelector('#logicNodesCount'),
            code: document.querySelector('#codeNodesCount'),
            order: document.querySelector('#orderNodesCount')
        };
        
        for (const [layer, element] of Object.entries(counterElements)) {
            if (element) {
                element.textContent = stats[layer];
                this.logger.debug(`📊 更新${layer}层计数器: ${stats[layer]}`);
            } else {
                this.logger.warn(`⚠️ 找不到${layer}层计数器元素`);
            }
        }
        
        // 如果有DAG控制器，通知它更新
        if (window.dagController && typeof window.dagController.updateStatistics === 'function') {
            window.dagController.updateStatistics(stats);
        }
    };

    // 导出到全局命名空间
    window.MCPFeedback.DAG.DAGManager = DAGManager;

    console.log('📦 DAG可视化管理器模块加载完成');

})(); 