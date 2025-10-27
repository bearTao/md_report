# Pandoc安装指南

## 什么是Pandoc？

Pandoc是一个通用的文档转换工具，可以在多种文档格式之间进行转换。本项目使用Pandoc将Markdown格式的报告转换为Word文档。

## 安装方法

### 方法1：使用Conda安装（推荐）

由于您的系统使用miniforge环境，使用conda安装是最简单的方法：

```bash
# 激活您的环境
conda activate test_md

# 安装pandoc
conda install -c conda-forge pandoc

# 验证安装
pandoc --version
```

### 方法2：使用系统包管理器

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install pandoc
```

#### CentOS/RHEL
```bash
sudo yum install pandoc
```

#### Arch Linux
```bash
sudo pacman -S pandoc
```

### 方法3：从源码编译（高级用户）

```bash
# 下载最新版本
wget https://github.com/jgm/pandoc/releases/download/3.1.11/pandoc-3.1.11-linux-amd64.tar.gz

# 解压
tar xvzf pandoc-3.1.11-linux-amd64.tar.gz

# 移动到系统路径
sudo mv pandoc-3.1.11/bin/pandoc /usr/local/bin/

# 验证
pandoc --version
```

## 验证安装

安装完成后，运行以下命令验证：

```bash
pandoc --version
```

预期输出类似：
```
pandoc 3.1.11
Features: +server +lua
Scripting engine: Lua 5.4
User data directory: /home/user/.local/share/pandoc
```

## 测试转换功能

安装完成后，可以测试一下基本的转换功能：

```bash
# 创建测试Markdown文件
echo "# 测试标题

这是测试内容。

## 二级标题

- 列表项1
- 列表项2
" > test.md

# 转换为Word
pandoc test.md -o test.docx

# 检查生成的文件
ls -lh test.docx
```

如果成功生成了`test.docx`文件，说明pandoc安装正确。

## 在项目中使用

安装完pandoc后，重启后端服务：

```bash
cd /data/tao/code/xuqiu/backend

# 如果使用supervisor或systemd
sudo systemctl restart your-app-service

# 或者直接重启Python进程
# 找到进程并kill，然后重新启动
```

现在您可以在报告历史页面使用"转换Word"功能了。

## 故障排查

### 问题1：command not found

**错误**：
```
pandoc: command not found
```

**解决**：
1. 确认pandoc已安装：`which pandoc`
2. 检查PATH环境变量：`echo $PATH`
3. 如果使用conda，确保环境已激活
4. 重新安装pandoc

### 问题2：权限错误

**错误**：
```
Permission denied
```

**解决**：
```bash
# 给pandoc执行权限
sudo chmod +x /usr/local/bin/pandoc

# 或使用sudo安装
sudo conda install -c conda-forge pandoc
```

### 问题3：版本太旧

**错误**：
```
某些功能不支持
```

**解决**：
```bash
# 更新到最新版
conda update -c conda-forge pandoc

# 或使用系统包管理器更新
sudo apt-get update && sudo apt-get upgrade pandoc
```

## 推荐配置

为了获得最佳转换效果，建议安装以下额外组件：

### LaTeX支持（可选）

如果需要转换包含复杂数学公式的文档：

```bash
# Ubuntu/Debian
sudo apt-get install texlive-xetex

# Conda
conda install -c conda-forge texlive-core
```

### 字体支持（可选）

安装中文字体以支持中文文档：

```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-zenhei fonts-wqy-microhei

# 验证字体
fc-list :lang=zh
```

## 性能优化

### 大文件处理

如果需要处理大型报告（>1MB），可以调整pandoc参数：

```bash
# 在document_converter.py中可以添加以下选项：
# --resource-path 指定资源路径
# --embed-resources 嵌入所有资源
# --standalone 生成独立文档
```

### 并发限制

建议在nginx或应用层面限制并发转换数量：

```python
# 在reports.py中可以添加信号量控制
import asyncio

# 最多同时3个转换任务
conversion_semaphore = asyncio.Semaphore(3)

async def convert_report_to_word(...):
    async with conversion_semaphore:
        # 转换逻辑
        ...
```

## 相关资源

- Pandoc官方文档：https://pandoc.org/
- Pandoc用户手册：https://pandoc.org/MANUAL.html
- GitHub仓库：https://github.com/jgm/pandoc
- 中文社区：https://pandoc-discuss.narkive.com/

## 快速安装命令（推荐）

```bash
# 一键安装（使用conda）
conda activate test_md && conda install -c conda-forge pandoc && pandoc --version
```

安装成功后，刷新浏览器页面即可使用Word转换功能！

