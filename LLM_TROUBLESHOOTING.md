# LLM配置故障排除指南

## 常见问题及解决方案

### 1. URL格式错误

#### ❌ 错误示例
```
Base URL: https://open.bigmodel.cn/api/coding/paas/v4
错误信息: Error code: 404 - path: '/v4%20chat/completions'
```

#### ✅ 正确配置
```
Base URL: https://open.bigmodel.cn/api/paas/v4
注意：不要有多余的空格，确保路径正确
```

#### 🔧 解决方案
1. **检查URL路径**：确保端点路径正确，智谱AI的正确端点是 `/api/paas/v4`
2. **去除空格**：系统会自动去除首尾空格和尾部斜杠
3. **验证格式**：确保URL以 `http://` 或 `https://` 开头

### 2. 连接测试失败

#### 问题：Connection timeout
```bash
# 检查网络连接
curl -I https://open.bigmodel.cn/api/paas/v4

# 如果无法访问，可能是：
# 1. 网络问题
# 2. 防火墙阻止
# 3. URL配置错误
```

#### 问题：401 Unauthorized
```bash
# 可能原因：
# 1. API Key错误或过期
# 2. API Key格式不正确
# 3. 账户余额不足

# 解决方案：
# 1. 重新生成API Key
# 2. 检查账户余额
# 3. 确认API Key权限
```

#### 问题：404 Not Found
```bash
# 可能原因：
# 1. Base URL路径错误
# 2. 模型名称不正确
# 3. API版本不匹配

# 解决方案：
# 1. 检查官方文档确认正确的端点
# 2. 确认模型名称拼写正确
# 3. 检查API版本
```

### 3. 模型特定配置

#### 智谱AI (GLM) 配置
```python
# ✅ 正确配置
{
    "name": "智谱GLM",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "your-zhipu-api-key",
    "model_name": "glm-4-flash",  # 或 glm-4-plus, glm-4-air
    "model_type": "text"
}

# ❌ 错误配置
{
    "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",  # 路径错误
    "model_name": "glm-4"  # 模型名称可能不完全正确
}
```

#### DeepSeek 配置
```python
# ✅ 正确配置
{
    "name": "DeepSeek",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-your-deepseek-key",
    "model_name": "deepseek-chat",
    "model_type": "text"
}
```

### 4. URL清理规则

系统会自动处理以下情况：
- ✅ 去除首尾空格： `" https://api.com/v1 " → "https://api.com/v1"`
- ✅ 去除尾部斜杠： `"https://api.com/v1/" → "https://api.com/v1"`
- ✅ 验证协议： 必须以 `http://` 或 `https://` 开头

### 5. 调试技巧

#### 使用curl测试连接
```bash
# 测试智谱AI
curl -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 测试DeepSeek
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer your-deepseek-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### 检查日志
```bash
# 查看应用日志
tail -f backend/logs/app.log

# 查找LLM相关错误
grep "LLM\|OpenAI\|API" backend/logs/app.log
```

### 6. 支持的提供商配置示例

#### OpenAI 官方
```python
{
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o-mini"
}
```

#### SiliconFlow (国内推荐)
```python
{
    "base_url": "https://api.siliconflow.cn/v1",
    "model_name": "Qwen/Qwen2.5-7B-Instruct"
}
```

#### 本地 Ollama
```python
{
    "base_url": "http://localhost:11434/v1",
    "model_name": "qwen2.5:7b"
}
```

#### Azure OpenAI
```python
{
    "base_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment",
    "model_name": "gpt-4o"
}
```

### 7. 快速诊断清单

遇到问题时，按顺序检查：

- [ ] **URL格式**：是否正确（无多余空格，路径正确）
- [ ] **API Key**：是否有效且未过期
- [ ] **模型名称**：是否与提供商文档一致
- [ ] **网络连接**：是否能访问API端点
- [ ] **权限设置**：API Key是否有相应权限
- [ ] **账户余额**：是否足够支付API费用
- [ ] **防火墙/代理**：是否阻止了API请求

### 8. 获取帮助

如果问题仍未解决：

1. **查看日志**：检查详细的错误信息
2. **官方文档**：查阅LLM提供商的最新API文档
3. **测试工具**：使用提供的 `test_llm_config.py` 进行测试
4. **联系支持**：提供详细的错误信息和配置内容

---

**最后更新**: 2026-05-26  
**适用版本**: v1.1.0+