# DjangoBlog 部署指南: PythonAnywhere + Cloudflare

**域名**: `lll2.top`
**PythonAnywhere 用户名**: `LZLLLL`
**项目仓库**: `https://github.com/LZL-LLL/DjangoBlog.git`

---

## Part A: PythonAnywhere 部署

### A1. 运行部署脚本

1. 登录 [PythonAnywhere](https://www.pythonanywhere.com/)
2. 进入 **Dashboard** → 点击 **Bash** 打开一个终端
3. 运行部署脚本：

```bash
cd ~
# 如果本地已有 deploy_pa.sh，直接运行；否则先从仓库拉取
bash deploy_pa.sh
```

脚本会自动完成：
- 克隆/更新仓库到 `/home/LZLLLL/DjangoBlog-master`
- 创建 Python 3.11 虚拟环境
- 安装 `requirements-pa.txt` 依赖
- 运行数据库迁移 (`migrate`)
- 收集静态文件 (`collectstatic`)
- 构建搜索索引 (`rebuild_index`)
- 编译翻译文件 (`compilemessages`)

### A2. 配置 Web App

进入 **Web** 标签页，点击 **Add a new web app**：

1. **选择域名**: 输入 `LZLLLL.pythonanywhere.com`
2. **选择框架**: 选择 **Manual configuration**
3. **选择 Python 版本**: 选择 **Python 3.11**

### A3. 配置 Virtualenv

在 Web 标签页的 **Virtualenv section**：

```
/home/LZLLLL/.virtualenvs/djangoblog
```

### A4. 配置 WSGI 文件

在 Web 标签页，点击 **WSGI configuration file** 链接（路径类似 `/var/www/LZLLLL_pythonanywhere_com_wsgi.py`）。

**清空原有内容**，替换为以下内容（或直接指向项目中的 `passenger_wsgi.py`）：

```python
"""PythonAnywhere WSGI entry point for lll2.top."""
import os
import sys

# Add project root to Python path
path = '/home/LZLLLL/DjangoBlog-master'
if path not in sys.path:
    sys.path.append(path)

# ============ Production settings for PythonAnywhere ============
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoblog.settings')
os.environ.setdefault('DJANGO_DEBUG', 'False')
os.environ.setdefault('COMPRESS_ENABLED', 'False')

# Domain configuration for lll2.top
os.environ.setdefault('ALLOWED_HOSTS', 'lll2.top,www.lll2.top,.pythonanywhere.com,localhost')
os.environ.setdefault(
    'CSRF_TRUSTED_ORIGINS',
    'https://lll2.top,https://www.lll2.top,https://*.pythonanywhere.com'
)

# Secret key (generated for production)
os.environ.setdefault(
    'DJANGO_SECRET_KEY',
    'zMEFxz-BCPe-8XGu51Ko1sxZWD1d8hSUH-RY6SHYXCJftB84JIXYSFikj_owM8pPCOk'
)

# Disable Redis (use local memory cache instead on PA)
if 'DJANGO_REDIS_URL' in os.environ:
    del os.environ['DJANGO_REDIS_URL']

# ============ WSGI Application ============
from djangoblog.wsgi import application
```

> **注意**: `path` 变量必须指向 `/home/LZLLLL/DjangoBlog-master`，而不是默认生成的路径。

### A5. 配置 Static Files

在 Web 标签页的 **Static files** section，添加两条映射：

| URL | Directory |
|---|---|
| `/static/` | `/home/LZLLLL/DjangoBlog-master/collectedstatic` |
| `/media/` | `/home/LZLLLL/DjangoBlog-master/uploads` |

### A6. 配置日志文件（可选）

在 Web 标签页的 **Log files** section，确保 Error log 路径可写。项目日志会自动写入：
```
/home/LZLLLL/DjangoBlog-master/logs/djangoblog.log
```

### A7. Reload

点击页面顶部的 **Reload** 按钮，等待应用启动。

此时可以通过 `https://LZLLLL.pythonanywhere.com` 访问博客（还未配置自定义域名）。

---

## Part B: Cloudflare DNS 配置

### B1. 添加 DNS 记录

登录 [Cloudflare Dashboard](https://dash.cloudflare.com/) → 选择 `lll2.top` 域名 → **DNS** → **Records**：

**添加第一条记录**:
- Type: `CNAME`
- Name: `lll2.top`（或 `@`）
- Target: `LZLLLL.pythonanywhere.com`
- Proxy status: **Proxied** (橙色云朵)
- TTL: Auto

**添加第二条记录**:
- Type: `CNAME`
- Name: `www`
- Target: `LZLLLL.pythonanywhere.com`
- Proxy status: **Proxied** (橙色云朵)
- TTL: Auto

### B2. 配置 SSL/TLS

进入 **SSL/TLS** → **Overview**：

- 加密模式选择: **Full**

> 不能选 "Flexible"，因为 PythonAnywhere 已有 HTTPS，Flexible 会导致重定向循环。

### B3. 启用 HTTPS

进入 **SSL/TLS** → **Edge Certificates**：

- **Always Use HTTPS**: 开启
- **Automatic HTTPS Rewrites**: 开启

### B4. 配置 Page Rules（可选但推荐）

进入 **Rules** → **Page Rules**，创建一条规则：

- URL: `www.lll2.top/*`
- Setting: **Forwarding URL** (301 Permanent Redirect)
- Destination: `https://lll2.top/$1`

这样 `www.lll2.top` 会自动 301 跳转到 `lll2.top`。

### B5. Cloudflare Cache 插件配置（可选）

如果需要在文章更新时自动清除 Cloudflare 缓存，需要创建 API Token：

1. 进入 **My Profile** → **API Tokens** → **Create Token**
2. 选择 **Custom token** 模板
3. 权限: `Zone - Cache Purge - Purge`
4. Zone Resources: `Include - Specific zone - lll2.top`
5. 创建后复制 Token

然后在 PythonAnywhere 的 Bash console 中设置环境变量：
```bash
# 编辑 passenger_wsgi.py，添加以下两行：
os.environ.setdefault('CLOUDFLARE_ZONE_ID', '你的Zone ID')
os.environ.setdefault('CLOUDFLARE_API_TOKEN', '你的API Token')
```

Zone ID 可在 Cloudflare 域名概览页面的右下角找到。

---

## Part C: PythonAnywhere 自定义域名（免费版限制）

> **重要**: PythonAnywhere **免费版不支持自定义域名**。免费用户只能使用 `*.pythonanywhere.com` 子域名。
>
> 自定义域名需要 **Hacker 付费方案** ($5/月)。

### 如果使用免费版

通过 Cloudflare Workers 实现域名跳转（无需付费方案）：

1. 在 Cloudflare 进入 **Workers & Pages**
2. 创建一个 Worker，代码如下：

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = 'LZLLLL.pythonanywhere.com';
    return Response.redirect(url.toString(), 301);
  }
};
```

3. 设置路由: `lll2.top/*` → 该 Worker
4. 同样处理 `www.lll2.top/*`

> 这种方式访问者会看到 URL 变为 `LZLLLL.pythonanywhere.com`，不够理想。

### 如果使用 Hacker 付费方案

1. 进入 PythonAnywhere **Account** → **Web** tab
2. 在 **Custom domains** section 添加 `lll2.top`
3. PythonAnywhere 会显示一个 CNAME target（类似 `webapp-xxxxx.pythonanywhere.com`）
4. 在 Cloudflare DNS 中将 CNAME target 更新为这个地址

---

## Part D: 部署后验证

### D1. 基本功能检查

| 检查项 | URL | 预期结果 |
|---|---|---|
| 首页 | `https://lll2.top` | 博客首页正常加载 |
| WWW 重定向 | `https://www.lll2.top` | 跳转到 `lll2.top` 或正常显示 |
| 管理后台 | `https://lll2.top/admin/` | Django Admin 登录页 |
| 静态文件 | `https://lll2.top/static/...` | CSS/JS/图片正常加载 |
| 文章详情 | 点击任意文章 | 文章内容正常显示 |
| 搜索功能 | 使用搜索框 | 搜索结果正常返回 |

### D2. Cloudflare 验证

在浏览器中打开任意页面，检查 Response Headers：

```
cf-cache-status: HIT       # Cloudflare 缓存命中
cf-ray: xxxxx               # Cloudflare 请求 ID
server: cloudflare          # 由 Cloudflare 代理
```

### D3. SSL 证书验证

访问 `https://lll2.top`，点击浏览器地址栏的锁图标，确认：
- 证书由 Cloudflare 签发
- 连接安全（TLS 1.2/1.3）

### D4. 常见问题排查

**问题: 502 Bad Gateway**
- 检查 WSGI 文件路径是否正确
- 检查 virtualenv 路径是否正确
- 查看 Error log（Web 标签页）

**问题: 静态文件 404**
- 确认 Static files 映射已添加
- 重新运行 `python manage.py collectstatic --noinput`

**问题: CSRF 验证失败**
- 检查 `CSRF_TRUSTED_ORIGINS` 是否包含当前访问的域名
- 确认 Cloudflare SSL 模式为 **Full**（不是 Flexible）

**问题: Cloudflare 重定向循环**
- SSL/TLS 模式必须是 **Full** 或 **Full (strict)**
- 不能用 Flexible（Cloudflare → HTTP → PA 重定向到 HTTPS → 循环）

**问题: 搜索不工作**
- 重新运行: `python manage.py rebuild_index --noinput`

---

## 一键更新部署

后续更新代码后，在 PythonAnywhere Bash console 运行：

```bash
cd /home/LZLLLL/DjangoBlog-master
git pull origin main
source /home/LZLLLL/.virtualenvs/djangoblog/bin/activate
pip install -r requirements-pa.txt --no-cache-dir
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py rebuild_index --noinput 2>/dev/null || true
```

然后在 Web 标签页点击 **Reload**。

---

## 项目配置文件说明

| 文件 | 用途 |
|---|---|
| `passenger_wsgi.py` | PA WSGI 入口，设置生产环境变量 |
| `requirements-pa.txt` | PA 专用依赖（移除 MySQL/ES/gevent） |
| `deploy_pa.sh` | 自动化部署脚本 |
| `djangoblog/settings.py` | Django 主配置，从环境变量读取所有生产设置 |
