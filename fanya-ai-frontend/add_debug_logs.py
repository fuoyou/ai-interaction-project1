# -*- coding: utf-8 -*-
"""
添加调试日志到 handleResolveSupplement 函数
"""

file_path = r'd:\Users\DELL\Desktop\project_new_f\project_new\ai-interaction-project1\fanya-ai-frontend\src\views\StudentClassroom\index.vue'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_code = '''// 【功能】处理点击"我理解了"的逻辑
const handleResolveSupplement = (msgIndex) => {
    chatHistory.value[msgIndex].resolved = true
    isRhythmAdjusting.value = false // 停止顶部闪烁
    ElNotification({
        title: '节奏同步成功',
        message: '已为您切换回原讲授节点，继续讲解。',
        type: 'success',
        duration: 2000
    })
    currentMode.value = 'lecture'
    
    // 【创新点四】切换回讲解模式时，触发数字人讲解当前讲稿（可能是简化版）
    if (currentScript.value && currentScript.value.trim()) {
        console.log('[讲授节奏调整] 返回讲解模式，触发数字人讲解简化版讲稿')
        // 使用 nextTick 确保模式切换完成后再触发讲解
        nextTick(() => {
            handleSpeakContent(currentScript.value)
        })
    }
}'''

new_code = '''// 【功能】处理点击"我理解了"的逻辑
const handleResolveSupplement = (msgIndex) => {
    console.log('[调试] ========== 点击"我理解了，继续讲解" ==========')
    console.log('[调试] msgIndex:', msgIndex)
    console.log('[调试] currentScript 长度:', currentScript.value?.length || 0)
    console.log('[调试] currentMode:', currentMode.value)
    
    chatHistory.value[msgIndex].resolved = true
    isRhythmAdjusting.value = false // 停止顶部闪烁
    ElNotification({
        title: '节奏同步成功',
        message: '已为您切换回原讲授节点，继续讲解。',
        type: 'success',
        duration: 2000
    })
    
    console.log('[调试] 准备切换到讲解模式...')
    currentMode.value = 'lecture'
    console.log('[调试] 已切换，currentMode:', currentMode.value)
    
    // 【创新点四】切换回讲解模式时，触发数字人讲解当前讲稿（可能是简化版）
    if (currentScript.value && currentScript.value.trim()) {
        console.log('[讲授节奏调整] 返回讲解模式，触发数字人讲解简化版讲稿')
        console.log('[调试] 讲稿内容（前100字）:', currentScript.value.substring(0, 100))
        // 使用 nextTick 确保模式切换完成后再触发讲解
        nextTick(() => {
            console.log('[调试] nextTick 执行，调用 handleSpeakContent')
            handleSpeakContent(currentScript.value)
        })
    } else {
        console.log('[调试] ❌ currentScript 为空或无内容，不触发讲解')
    }
}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 调试日志添加成功！")
else:
    print("❌ 未找到匹配的代码")
    print("尝试查找函数名...")
    if 'handleResolveSupplement' in content:
        print("✓ 找到函数名")
    else:
        print("✗ 未找到函数名")
