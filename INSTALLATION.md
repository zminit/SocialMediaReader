# SocialMediaReader 安装指南

## 环境配置完成情况

✅ **已完成：**
1. uv 包管理器已安装（位于 `/home/zm/.local/bin/uv`）
2. Python 虚拟环境已创建（`.venv` 目录）
3. `.env` 配置文件已创建

⚠️ **待完成：**
- 安装 Python 依赖包（由于网络问题暂未完成）

## 安装依赖的方法

由于网络连接问题，你可以尝试以下几种方法安装依赖：

### 方法 1：使用 uv（推荐，但需要网络）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 使用 uv 安装（尝试不同的镜像源）
/home/zm/.local/bin/uv pip install -r requirements.txt

# 或使用清华镜像
/home/zm/.local/bin/uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
/home/zm/.local/bin/uv pip install -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/
```

### 方法 2：先安装 pip 到虚拟环境

```bash
# 下载 get-pip.py
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

# 使用虚拟环境的 Python 安装 pip
.venv/bin/python get-pip.py

# 然后使用 pip 安装依赖
.venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 方法 3：检查代理设置

如果你使用代理，可能需要设置环境变量：

```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port

# 然后再尝试安装
/home/zm/.local/bin/uv pip install -r requirements.txt
```

### 方法 4：离线安装（如果有其他机器可以下载）

在有网络的机器上：
```bash
pip download -r requirements.txt -d packages/
```

然后将 packages 目录复制到当前机器，再安装：
```bash
/home/zm/.local/bin/uv pip install --no-index --find-links=packages/ -r requirements.txt
```

## 验证安装

安装完成后，运行以下命令验证：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行示例代码
python examples/basic_usage.py

# 运行测试
pytest tests/
```

## 项目依赖

项目需要以下 Python 包：
- `requests` - HTTP 请求库
- `python-dotenv` - 环境变量管理
- `pydantic` - 数据验证
- `aiohttp` - 异步 HTTP 客户端
- `pytest` - 测试框架
- `pytest-asyncio` - 异步测试支持

## 配置 GitHub Token

编辑 `.env` 文件，添加你的 GitHub Personal Access Token：

```bash
GITHUB_TOKEN=your_github_token_here
```

获取 GitHub Token：
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo`, `read:user`
4. 生成并复制 token
5. 粘贴到 `.env` 文件中

## 故障排除

### 网络连接问题
- 检查是否需要配置代理
- 尝试不同的 PyPI 镜像源
- 检查防火墙设置

### 虚拟环境问题
如果虚拟环境有问题，可以重新创建：
```bash
rm -rf .venv
/home/zm/.local/bin/uv venv
```

## 下一步

安装完成后，你可以：
1. 查看 `collector/README.md` 了解 Collector 模块的使用方法
2. 查看 `examples/basic_usage.py` 了解基本用法
3. 运行测试确保一切正常：`pytest tests/`
4. 开始开发其他模块（Parser、Storage、API）
