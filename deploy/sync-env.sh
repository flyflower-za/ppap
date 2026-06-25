#!/bin/bash
# 自动同步 .env.example 到 .env
# 用法：./sync-env.sh

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "Error: $ENV_EXAMPLE not found"
    exit 1
fi

# 如果 .env 不存在，从 .env.example 复制
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created $ENV_FILE from $ENV_EXAMPLE"
    exit 0
fi

# 读取 .env.example 中的所有键
while IFS='=' read -r key value; do
    # 跳过注释和空行
    [[ $key =~ ^#.*$ ]] && continue
    [[ -z $key ]] && continue
    
    # 去除键名中的空白
    key=$(echo "$key" | xargs)
    
    # 检查 .env 中是否已有此键
    if ! grep -q "^${key}=" "$ENV_FILE"; then
        # 添加缺失的键
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "Added new config: $key"
    fi
done < "$ENV_EXAMPLE"

echo "Config sync completed"
