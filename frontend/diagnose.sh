#!/bin/bash

echo "========================================"
echo "前端诊断脚本"
echo "========================================"

cd "$(dirname "$0")"

echo ""
echo "1. 检查 TypeScript 编译错误..."
npx tsc --noEmit 2>&1 | head -50

echo ""
echo "2. 检查是否有语法错误..."
npx eslint src --ext .ts,.tsx --max-warnings 0 2>&1 | head -30 || echo "  (ESLint 未配置或有警告)"

echo ""
echo "3. 检查关键文件是否存在..."
files=(
    "src/pages/debug/TemplatePlayground.tsx"
    "src/api/debug.ts"
    "src/App.tsx"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
    fi
done

echo ""
echo "4. 检查依赖..."
if [ -d "node_modules" ]; then
    echo "  ✅ node_modules 存在"
else
    echo "  ❌ node_modules 不存在，需要运行 npm install"
fi

echo ""
echo "5. 尝试构建（检测编译错误）..."
timeout 30s npm run build 2>&1 | grep -E "(error|Error|failed|Failed)" | head -10 || echo "  构建检查完成（或超时）"

echo ""
echo "========================================"
echo "诊断完成"
echo "========================================"


