
// 在浏览器开发者控制台中运行此脚本来测试UI修复
console.log('🧪 开始测试DAG UI修复效果...');

// 1. 检查DAG控制器是否存在
if (window.dagController) {
    console.log('✅ DAG控制器已初始化');
    
    // 2. 检查DAG管理器
    if (window.dagController.dagManager) {
        console.log('✅ DAG管理器已初始化');
        
        // 3. 获取当前统计信息
        const stats = window.dagController.getLayerStatistics();
        console.log('📊 当前统计信息:', stats);
        
        // 4. 手动更新统计显示
        window.dagController.updateStatistics(stats);
        console.log('🔄 已手动更新统计显示');
        
        // 5. 检查UI元素是否存在并更新
        const elements = {
            function: document.querySelector('#functionNodesCount'),
            logic: document.querySelector('#logicNodesCount'),
            code: document.querySelector('#codeNodesCount'),
            order: document.querySelector('#orderNodesCount')
        };
        
        console.log('🔍 UI元素检查:');
        for (const [layer, element] of Object.entries(elements)) {
            if (element) {
                console.log(`  ✅ ${layer}: 找到元素，当前值=${element.textContent}`);
                element.textContent = stats[layer];
                console.log(`  🔄 ${layer}: 已更新为${stats[layer]}`);
            } else {
                console.log(`  ❌ ${layer}: 未找到元素`);
            }
        }
        
        // 6. 尝试重新加载DAG数据
        console.log('📥 尝试重新加载DAG数据...');
        window.dagController.dagManager.loadSavedDAG()
            .then(() => {
                console.log('✅ DAG数据重新加载完成');
                const newStats = window.dagController.getLayerStatistics();
                console.log('📊 重新加载后的统计:', newStats);
                window.dagController.updateStatistics(newStats);
            })
            .catch(err => {
                console.error('❌ DAG数据重新加载失败:', err);
            });
            
    } else {
        console.error('❌ DAG管理器未初始化');
    }
} else {
    console.error('❌ DAG控制器未初始化');
}

console.log('🧪 测试脚本执行完成，请查看上述输出结果');
