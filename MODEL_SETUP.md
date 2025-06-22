# 模型配置说明

本项目已添加对以下新模型的支持：

## DeepSeek 模型

### 支持的模型
- **DeepSeek Coder**: `deepseek:deepseek-coder`
- **DeepSeek Chat**: `deepseek:deepseek-chat`  
- **DeepSeek Coder Instruct**: `deepseek:deepseek-coder-instruct`

### 配置方法
1. 访问 [DeepSeek API](https://platform.deepseek.com/) 获取API密钥
2. 在环境变量中设置：
```bash
DEEPSEEK_API_KEY="your_deepseek_api_key"
```

## Morpheus 模型

### 支持的模型
- **Morpheus**: `morpheus:morpheus`

### 配置方法
1. 获取Morpheus模型的API访问凭证
2. 在环境变量中设置：
```bash
MORPHEUS_API_KEY="your_morpheus_api_key"
MORPHEUS_BASE_URL="https://api.morpheus.com"  # 根据实际API地址调整
```

## 智谱 GLM4 模型

### 支持的模型
- **智谱 GLM4**: `zhipu:glm-4`

### 配置方法
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 获取API密钥
2. 在环境变量中设置：
```bash
ZHIPU_API_KEY="your_zhipu_api_key"
```

**注意**: 智谱GLM4模型目前需要额外的依赖配置，可能需要手动安装兼容的langchain集成包。

## 环境变量配置

将上述API密钥添加到你的 `.env` 文件中。你可以参考 `env.example` 文件作为模板：

```bash
# 复制示例文件
cp env.example .env

# 然后编辑 .env 文件，填入你的实际API密钥
```

或者手动创建 `.env` 文件并添加以下配置：

```bash
# 现有配置
SUPABASE_URL="your_supabase_url"
SUPABASE_KEY="your_supabase_key"

# 新增模型配置
DEEPSEEK_API_KEY="your_deepseek_api_key"
MORPHEUS_API_KEY="your_morpheus_api_key"
MORPHEUS_BASE_URL="https://api.morpheus.com"
ZHIPU_API_KEY="your_zhipu_api_key"
```

## 使用说明

1. 安装依赖：
```bash
uv sync
```

2. 配置环境变量后，重启服务：
```bash
uv run langgraph dev --no-browser
```

3. 在Open Agent Platform界面中，你可以在模型选择下拉菜单中看到新添加的模型选项。

## 注意事项

- 确保API密钥的安全性，不要将其提交到版本控制系统
- 不同模型的API调用方式和参数可能有所不同
- 如果遇到模型连接问题，请检查API密钥是否正确以及网络连接是否正常
- 智谱GLM4模型可能需要额外的配置步骤，请参考相关文档 