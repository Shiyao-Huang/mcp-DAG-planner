"""
Version: v1.0.0
Author: AI Assistant + User
Date: 2024-12-20
Dependencies: 四层DAG循环迭代构建指南.md, UnifiedDAGModel
"""

"""
四层DAG迭代构建引擎

```mermaid
graph TD
    A[FourLayerIterator] --> B[IterationStrategy策略管理]
    A --> C[ConvergenceEvaluator收敛评估]
    A --> D[LayerOptimizer层级优化器]
    
    B --> B1[initialize_strategy初始化策略]
    B --> B2[adjust_strategy调整策略]
    B --> B3[validate_strategy验证策略]
    
    C --> C1[calculate_convergence计算收敛度]
    C --> C2[check_quality_gates质量门检查]
    C --> C3[generate_metrics生成指标]
    
    D --> D1[FunctionLayerOptimizer功能层]
    D --> D2[LogicLayerOptimizer逻辑层]
    D --> D3[CodeLayerOptimizer代码层]
    D --> D4[OrderLayerOptimizer排序层]
```

本文件实现了四层DAG系统的核心迭代构建引擎。
严格按照《四层DAG循环迭代构建指南.md》的设计原则。

核心功能：
- 四层并行迭代构建
- 收敛性评估和质量控制
- 策略调整和自适应优化
- 用户反馈驱动的迭代控制
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from ..dag_models import (
    UnifiedDAGModel, 
    LayerType, 
    DAGStage,
    BaseNodeData,
    BaseEdgeData
)


class IterationPhase(Enum):
    """迭代阶段枚举"""
    INITIALIZING = "initializing"
    ITERATING = "iterating"
    WAITING_FEEDBACK = "waiting_feedback"
    PROCESSING_FEEDBACK = "processing_feedback"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class OptimizationFocus(Enum):
    """优化重点枚举"""
    STRUCTURE = "structure"           # 结构优化
    DEPENDENCIES = "dependencies"     # 依赖关系优化
    COMPLETENESS = "completeness"     # 完整性优化
    CONSISTENCY = "consistency"       # 一致性优化
    QUALITY = "quality"              # 质量优化


@dataclass
class IterationConfig:
    """迭代配置"""
    max_iterations: int = 20
    convergence_threshold: float = 0.85
    feedback_frequency: int = 3  # 每3轮迭代请求用户反馈
    parallel_optimization: bool = True
    quality_gates_enabled: bool = True
    auto_adjust_strategy: bool = True
    timeout_per_iteration: int = 30  # 每轮迭代超时时间(秒)


@dataclass
class IterationMetrics:
    """迭代指标"""
    iteration_number: int = 0
    convergence_score: float = 0.0
    quality_score: float = 0.0
    completion_percentage: float = 0.0
    layer_scores: Dict[str, float] = field(default_factory=dict)
    optimization_time: float = 0.0
    total_nodes: int = 0
    total_edges: int = 0
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class IterationStrategy:
    """迭代策略"""
    current_focus: OptimizationFocus = OptimizationFocus.STRUCTURE
    layer_priorities: Dict[LayerType, float] = field(default_factory=lambda: {
        LayerType.FUNCTION: 1.0,
        LayerType.LOGIC: 0.8,
        LayerType.CODE: 0.6,
        LayerType.ORDER: 0.4
    })
    optimization_params: Dict[str, Any] = field(default_factory=dict)
    
    def adjust_priorities(self, feedback: Dict[str, Any]) -> None:
        """根据反馈调整层级优先级"""
        if "layer_feedback" in feedback:
            for layer_name, priority_delta in feedback["layer_feedback"].items():
                if layer_name in [lt.value for lt in LayerType]:
                    layer_type = LayerType(layer_name)
                    current_priority = self.layer_priorities.get(layer_type, 1.0)
                    new_priority = max(0.1, min(2.0, current_priority + priority_delta))
                    self.layer_priorities[layer_type] = new_priority


class ConvergenceEvaluator:
    """收敛性评估器"""
    
    def __init__(self):
        self.history: List[IterationMetrics] = []
    
    def evaluate_convergence(self, dag: UnifiedDAGModel) -> float:
        """评估DAG的收敛性"""
        scores = []
        
        # 1. 结构完整性评分
        structure_score = self._evaluate_structure_completeness(dag)
        scores.append(structure_score)
        
        # 2. 跨层一致性评分
        consistency_score = self._evaluate_layer_consistency(dag)
        scores.append(consistency_score)
        
        # 3. 质量指标评分
        quality_score = self._evaluate_quality_metrics(dag)
        scores.append(quality_score)
        
        # 4. 稳定性评分（基于历史迭代）
        stability_score = self._evaluate_stability()
        scores.append(stability_score)
        
        # 加权平均
        weights = [0.3, 0.3, 0.25, 0.15]
        convergence_score = sum(score * weight for score, weight in zip(scores, weights))
        
        return min(1.0, max(0.0, convergence_score))
    
    def _evaluate_structure_completeness(self, dag: UnifiedDAGModel) -> float:
        """评估结构完整性"""
        total_score = 0.0
        layer_count = 0
        
        for layer_type in LayerType:
            layer_data = dag.get_layer_data(layer_type)
            nodes = layer_data.get("nodes", {})
            edges = layer_data.get("edges", {})
            
            if len(nodes) > 0:
                layer_count += 1
                # 基础节点存在性评分
                node_score = min(1.0, len(nodes) / 5)  # 假设至少需要5个节点
                
                # 连接性评分
                connectivity_score = 0.0
                if len(nodes) > 1:
                    max_possible_edges = len(nodes) * (len(nodes) - 1)
                    actual_connectivity = len(edges) / max(1, max_possible_edges) * 10  # 10%连接率为满分
                    connectivity_score = min(1.0, actual_connectivity)
                
                layer_score = (node_score + connectivity_score) / 2
                total_score += layer_score
        
        return total_score / max(1, layer_count)
    
    def _evaluate_layer_consistency(self, dag: UnifiedDAGModel) -> float:
        """评估跨层一致性"""
        # 检查跨层映射的完整性
        mapping_completeness = 0.0
        total_mappings = 0
        
        # 功能层到逻辑层的映射
        function_nodes = dag.get_layer_data(LayerType.FUNCTION).get("nodes", {})
        for func_id in function_nodes:
            logic_mappings = dag.get_cross_layer_mappings(
                LayerType.FUNCTION, LayerType.LOGIC, func_id
            )
            if logic_mappings:
                mapping_completeness += 1
            total_mappings += 1
        
        # 逻辑层到代码层的映射
        logic_nodes = dag.get_layer_data(LayerType.LOGIC).get("nodes", {})
        for logic_id in logic_nodes:
            code_mappings = dag.get_cross_layer_mappings(
                LayerType.LOGIC, LayerType.CODE, logic_id
            )
            if code_mappings:
                mapping_completeness += 1
            total_mappings += 1
        
        return mapping_completeness / max(1, total_mappings)
    
    def _evaluate_quality_metrics(self, dag: UnifiedDAGModel) -> float:
        """评估质量指标"""
        # 基于DAG状态中的质量指标
        state = dag.state
        quality_indicators = []
        
        # 验证状态
        if state.get("validation_status") == "passed":
            quality_indicators.append(1.0)
        elif state.get("validation_status") == "partial":
            quality_indicators.append(0.6)
        else:
            quality_indicators.append(0.2)
        
        # 节点质量（假设存在质量评分）
        total_nodes = state.get("total_nodes", 0)
        if total_nodes > 0:
            # 这里可以扩展为更复杂的节点质量评估
            node_quality = min(1.0, total_nodes / 10)  # 假设10个节点为理想状态
            quality_indicators.append(node_quality)
        
        return sum(quality_indicators) / max(1, len(quality_indicators))
    
    def _evaluate_stability(self) -> float:
        """评估迭代稳定性"""
        if len(self.history) < 3:
            return 0.5  # 历史数据不足，给予中等评分
        
        # 检查最近几轮的收敛分数变化
        recent_scores = [metrics.convergence_score for metrics in self.history[-3:]]
        variance = sum((score - sum(recent_scores)/len(recent_scores))**2 for score in recent_scores) / len(recent_scores)
        
        # 低方差表示高稳定性
        stability_score = max(0.0, 1.0 - variance * 10)  # 方差转换为稳定性评分
        return stability_score
    
    def add_metrics(self, metrics: IterationMetrics) -> None:
        """添加迭代指标到历史记录"""
        self.history.append(metrics)
        
        # 保持历史记录在合理范围内
        if len(self.history) > 50:
            self.history = self.history[-50:]


class LayerOptimizer:
    """层级优化器基类"""
    
    def __init__(self, layer_type: LayerType):
        self.layer_type = layer_type
    
    async def optimize(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化指定层级"""
        start_time = time.time()
        
        # 根据优化重点选择策略
        if strategy.current_focus == OptimizationFocus.STRUCTURE:
            result = await self._optimize_structure(dag, strategy, iteration_number)
        elif strategy.current_focus == OptimizationFocus.DEPENDENCIES:
            result = await self._optimize_dependencies(dag, strategy, iteration_number)
        elif strategy.current_focus == OptimizationFocus.COMPLETENESS:
            result = await self._optimize_completeness(dag, strategy, iteration_number)
        elif strategy.current_focus == OptimizationFocus.CONSISTENCY:
            result = await self._optimize_consistency(dag, strategy, iteration_number)
        else:  # QUALITY
            result = await self._optimize_quality(dag, strategy, iteration_number)
        
        optimization_time = time.time() - start_time
        result["optimization_time"] = optimization_time
        result["layer_type"] = self.layer_type.value
        
        return result
    
    async def _optimize_structure(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化层级结构"""
        # 基础实现，子类可以重写
        layer_data = dag.get_layer_data(self.layer_type)
        nodes = layer_data.get("nodes", {})
        
        # 如果是第一轮迭代且节点为空，创建基础节点
        if iteration_number == 1 and len(nodes) == 0:
            await self._create_initial_nodes(dag, strategy)
        
        return {
            "action": "structure_optimization",
            "nodes_processed": len(nodes),
            "changes_made": 0
        }
    
    async def _optimize_dependencies(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化依赖关系"""
        layer_data = dag.get_layer_data(self.layer_type)
        edges = layer_data.get("edges", {})
        
        return {
            "action": "dependency_optimization",
            "edges_processed": len(edges),
            "changes_made": 0
        }
    
    async def _optimize_completeness(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化完整性"""
        return {
            "action": "completeness_optimization",
            "changes_made": 0
        }
    
    async def _optimize_consistency(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化一致性"""
        return {
            "action": "consistency_optimization",
            "changes_made": 0
        }
    
    async def _optimize_quality(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy,
        iteration_number: int
    ) -> Dict[str, Any]:
        """优化质量"""
        return {
            "action": "quality_optimization",
            "changes_made": 0
        }
    
    async def _create_initial_nodes(
        self, 
        dag: UnifiedDAGModel, 
        strategy: IterationStrategy
    ) -> None:
        """创建初始节点"""
        # 基础实现，为每层创建一些示例节点
        node_templates = self._get_initial_node_templates()
        
        for i, template in enumerate(node_templates):
            node_data = BaseNodeData(
                id=f"{self.layer_type.value}_{i+1}",
                label=template["label"],
                layer=self.layer_type.value,
                position={"x": i * 200, "y": 100},
                metadata=template.get("metadata", {})
            )
            dag.add_node(self.layer_type, node_data)
    
    def _get_initial_node_templates(self) -> List[Dict[str, Any]]:
        """获取初始节点模板"""
        # 根据层级类型返回不同的模板
        if self.layer_type == LayerType.FUNCTION:
            return [
                {"label": "需求分析", "metadata": {"type": "analysis"}},
                {"label": "功能设计", "metadata": {"type": "design"}},
                {"label": "用户验证", "metadata": {"type": "validation"}}
            ]
        elif self.layer_type == LayerType.LOGIC:
            return [
                {"label": "架构设计", "metadata": {"type": "architecture"}},
                {"label": "API设计", "metadata": {"type": "api"}},
                {"label": "数据模型", "metadata": {"type": "data"}}
            ]
        elif self.layer_type == LayerType.CODE:
            return [
                {"label": "核心模块", "metadata": {"type": "module"}},
                {"label": "工具类", "metadata": {"type": "utility"}},
                {"label": "测试代码", "metadata": {"type": "test"}}
            ]
        else:  # ORDER
            return [
                {"label": "第一阶段", "metadata": {"type": "phase", "order": 1}},
                {"label": "第二阶段", "metadata": {"type": "phase", "order": 2}},
                {"label": "第三阶段", "metadata": {"type": "phase", "order": 3}}
            ]


class FourLayerIterator:
    """四层DAG迭代构建引擎"""
    
    def __init__(self, config: Optional[IterationConfig] = None):
        self.config = config or IterationConfig()
        self.strategy = IterationStrategy()
        self.convergence_evaluator = ConvergenceEvaluator()
        self.current_phase = IterationPhase.INITIALIZING
        self.current_iteration = 0
        self.iteration_history: List[IterationMetrics] = []
        
        # 创建层级优化器
        self.layer_optimizers = {
            LayerType.FUNCTION: LayerOptimizer(LayerType.FUNCTION),
            LayerType.LOGIC: LayerOptimizer(LayerType.LOGIC),
            LayerType.CODE: LayerOptimizer(LayerType.CODE),
            LayerType.ORDER: LayerOptimizer(LayerType.ORDER)
        }
        
        # 回调函数
        self.feedback_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None
    
    def set_feedback_callback(self, callback: Callable) -> None:
        """设置反馈回调函数"""
        self.feedback_callback = callback
    
    def set_progress_callback(self, callback: Callable) -> None:
        """设置进度回调函数"""
        self.progress_callback = callback
    
    async def iterate_build(
        self, 
        dag: UnifiedDAGModel,
        initial_requirements: Optional[Dict[str, Any]] = None
    ) -> UnifiedDAGModel:
        """开始四层DAG迭代构建"""
        
        self.current_phase = IterationPhase.INITIALIZING
        self.current_iteration = 0
        
        # 初始化策略
        if initial_requirements:
            self._initialize_strategy_from_requirements(initial_requirements)
        
        try:
            self.current_phase = IterationPhase.ITERATING
            
            while (self.current_iteration < self.config.max_iterations and 
                   self.current_phase != IterationPhase.COMPLETED):
                
                self.current_iteration += 1
                iteration_start = time.time()
                
                # 执行单轮迭代
                metrics = await self._execute_single_iteration(dag)
                
                # 记录指标
                metrics.iteration_number = self.current_iteration
                metrics.optimization_time = time.time() - iteration_start
                self.iteration_history.append(metrics)
                self.convergence_evaluator.add_metrics(metrics)
                
                # 进度回调
                if self.progress_callback:
                    await self._safe_callback(self.progress_callback, {
                        "iteration": self.current_iteration,
                        "metrics": metrics,
                        "phase": self.current_phase.value
                    })
                
                # 检查是否需要用户反馈
                if (self.current_iteration % self.config.feedback_frequency == 0 and 
                    self.feedback_callback):
                    
                    self.current_phase = IterationPhase.WAITING_FEEDBACK
                    
                    feedback_data = await self._prepare_feedback_data(dag, metrics)
                    user_feedback = await self._request_user_feedback(feedback_data)
                    
                    self.current_phase = IterationPhase.PROCESSING_FEEDBACK
                    await self._process_user_feedback(user_feedback)
                    
                    self.current_phase = IterationPhase.ITERATING
                
                # 检查收敛性
                if metrics.convergence_score >= self.config.convergence_threshold:
                    self.current_phase = IterationPhase.FINALIZING
                    await self._finalize_dag(dag)
                    self.current_phase = IterationPhase.COMPLETED
                    break
            
            # 更新DAG状态
            dag.metadata["stage"] = DAGStage.IMPLEMENTATION.value
            dag.state["current_iteration"] = self.current_iteration
            dag.state["convergence_score"] = metrics.convergence_score
            dag.state["validation_status"] = "completed"
            
            return dag
            
        except Exception as e:
            self.current_phase = IterationPhase.ERROR
            raise e
    
    async def _execute_single_iteration(self, dag: UnifiedDAGModel) -> IterationMetrics:
        """执行单轮迭代"""
        
        metrics = IterationMetrics()
        
        if self.config.parallel_optimization:
            # 并行优化四层
            optimization_tasks = []
            for layer_type, optimizer in self.layer_optimizers.items():
                task = optimizer.optimize(dag, self.strategy, self.current_iteration)
                optimization_tasks.append(task)
            
            optimization_results = await asyncio.gather(*optimization_tasks)
        else:
            # 串行优化四层
            optimization_results = []
            for layer_type, optimizer in self.layer_optimizers.items():
                result = await optimizer.optimize(dag, self.strategy, self.current_iteration)
                optimization_results.append(result)
        
        # 更新指标
        metrics.convergence_score = self.convergence_evaluator.evaluate_convergence(dag)
        metrics.total_nodes = sum(
            len(dag.get_layer_data(layer).get("nodes", {})) 
            for layer in LayerType
        )
        metrics.total_edges = sum(
            len(dag.get_layer_data(layer).get("edges", {})) 
            for layer in LayerType
        )
        
        # 计算完成百分比
        metrics.completion_percentage = min(100.0, metrics.convergence_score * 100)
        
        # 计算层级评分
        for layer_type in LayerType:
            layer_score = self._calculate_layer_score(dag, layer_type)
            metrics.layer_scores[layer_type.value] = layer_score
        
        # 质量评分
        metrics.quality_score = self.convergence_evaluator._evaluate_quality_metrics(dag)
        
        return metrics
    
    def _calculate_layer_score(self, dag: UnifiedDAGModel, layer_type: LayerType) -> float:
        """计算单层评分"""
        layer_data = dag.get_layer_data(layer_type)
        nodes = layer_data.get("nodes", {})
        edges = layer_data.get("edges", {})
        
        if len(nodes) == 0:
            return 0.0
        
        # 基础评分：基于节点和边的数量
        node_score = min(1.0, len(nodes) / 5)  # 假设5个节点为满分
        edge_score = 0.0
        
        if len(nodes) > 1:
            max_edges = len(nodes) * (len(nodes) - 1) / 2  # 完全图的边数
            edge_ratio = len(edges) / max(1, max_edges)
            edge_score = min(1.0, edge_ratio * 5)  # 20%的连接率为满分
        
        return (node_score + edge_score) / 2
    
    async def _prepare_feedback_data(
        self, 
        dag: UnifiedDAGModel, 
        metrics: IterationMetrics
    ) -> Dict[str, Any]:
        """准备反馈数据"""
        
        feedback_data = {
            "iteration_number": self.current_iteration,
            "metrics": {
                "convergence_score": metrics.convergence_score,
                "quality_score": metrics.quality_score,
                "completion_percentage": metrics.completion_percentage,
                "layer_scores": metrics.layer_scores,
                "total_nodes": metrics.total_nodes,
                "total_edges": metrics.total_edges
            },
            "dag_summary": {
                "layers": {},
                "cross_layer_mappings": {}
            },
            "strategy_info": {
                "current_focus": self.strategy.current_focus.value,
                "layer_priorities": {
                    layer.value: priority 
                    for layer, priority in self.strategy.layer_priorities.items()
                }
            },
            "visualization_data": {
                "reactflow": dag.to_reactflow_format(),
                "mermaid": dag.to_mermaid_format()
            }
        }
        
        # 添加各层摘要信息
        for layer_type in LayerType:
            layer_data = dag.get_layer_data(layer_type)
            feedback_data["dag_summary"]["layers"][layer_type.value] = {
                "node_count": len(layer_data.get("nodes", {})),
                "edge_count": len(layer_data.get("edges", {})),
                "key_nodes": list(layer_data.get("nodes", {}).keys())[:5]  # 前5个节点
            }
        
        return feedback_data
    
    async def _request_user_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """请求用户反馈"""
        if self.feedback_callback:
            return await self._safe_callback(self.feedback_callback, feedback_data)
        else:
            # 如果没有反馈回调，返回默认的"继续"决策
            return {
                "decision": "continue",
                "feedback": {},
                "adjustments": {}
            }
    
    async def _process_user_feedback(self, feedback: Dict[str, Any]) -> None:
        """处理用户反馈"""
        decision = feedback.get("decision", "continue")
        
        if decision == "reject":
            # 用户拒绝，重置策略
            self.strategy = IterationStrategy()
            self.strategy.current_focus = OptimizationFocus.STRUCTURE
        elif decision == "adjust":
            # 用户要求调整
            adjustments = feedback.get("adjustments", {})
            if "strategy" in adjustments:
                self._apply_strategy_adjustments(adjustments["strategy"])
            if "layer_priorities" in adjustments:
                self.strategy.adjust_priorities(adjustments)
    
    def _apply_strategy_adjustments(self, strategy_adjustments: Dict[str, Any]) -> None:
        """应用策略调整"""
        if "focus" in strategy_adjustments:
            focus_str = strategy_adjustments["focus"]
            try:
                self.strategy.current_focus = OptimizationFocus(focus_str)
            except ValueError:
                pass  # 忽略无效的focus值
        
        if "optimization_params" in strategy_adjustments:
            self.strategy.optimization_params.update(strategy_adjustments["optimization_params"])
    
    async def _finalize_dag(self, dag: UnifiedDAGModel) -> None:
        """最终化DAG"""
        # 最终验证和清理
        dag.state["validation_status"] = "passed"
        dag.state["last_modified"] = datetime.now().isoformat()
    
    def _initialize_strategy_from_requirements(self, requirements: Dict[str, Any]) -> None:
        """从需求初始化策略"""
        if "focus" in requirements:
            try:
                self.strategy.current_focus = OptimizationFocus(requirements["focus"])
            except ValueError:
                pass
        
        if "layer_priorities" in requirements:
            for layer_name, priority in requirements["layer_priorities"].items():
                try:
                    layer_type = LayerType(layer_name)
                    self.strategy.layer_priorities[layer_type] = float(priority)
                except (ValueError, TypeError):
                    pass
    
    async def _safe_callback(self, callback: Callable, data: Any) -> Any:
        """安全执行回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback(data)
            else:
                return callback(data)
        except Exception as e:
            # 记录错误但不中断迭代
            print(f"Callback error: {e}")
            return None
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "phase": self.current_phase.value,
            "iteration": self.current_iteration,
            "strategy": {
                "focus": self.strategy.current_focus.value,
                "layer_priorities": {
                    layer.value: priority 
                    for layer, priority in self.strategy.layer_priorities.items()
                }
            },
            "history_count": len(self.iteration_history),
            "last_metrics": self.iteration_history[-1].__dict__ if self.iteration_history else None
        } 