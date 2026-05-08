# MyBlog

<p align="center">
  <b>基于 Django 开发的现代化个人博客系统</b>
</p>

***

个人技术博客项目，采用 Django 5.2 + Python 开发，前端使用 Tailwind CSS + Alpine.js + HTMX。旨在学习现代 Web 开发技术，构建一个功能完善、性能优异的个人博客平台。

## 功能亮点

- **强大的内容管理** — 支持文章、独立页面、分类和标签的完整管理。内置 Markdown 编辑器，支持代码语法高亮
- **全文搜索** — 集成 Whoosh/Elasticsearch 搜索引擎，提供快速、精准的文章内容搜索，支持关键词高亮显示
- **互动评论系统** — 支持回复、邮件提醒等功能，评论内容同样支持 Markdown。现代化评论界面，支持无限嵌套回复
- **灵活的侧边栏** — 可自定义展示最新文章、最热文章、标签云等模块
- **社交化登录** — 内置 OAuth 支持，已集成 GitHub 等主流平台
- **黑夜模式** — 支持浅色/深色主题自动切换，可跟随系统设置，提供舒适的阅读体验
- **现代化前端** — 基于 Alpine.js + Tailwind CSS + HTMX 构建，提供 SPA 般的无刷新浏览体验，支持 HTML-over-the-wire 架构
- **高性能缓存** — 原生支持 Redis 缓存，并提供自动刷新机制，确保网站高速响应
- **SEO 友好** — 具备基础 SEO 功能，新内容发布后可自动通知 Google 和百度
- **便捷的插件系统** — 通过创建独立的插件来扩展博客功能，代码解耦，易于维护。已内置多个实用插件！
- **自动化构建** — 使用 Vite 构建前端资源，支持热更新和自动压缩优化

## 快速开始

### 环境要求

- Python 3.10+
- MySQL/MariaDB 或 SQLite
- Node.js >= 18 (前端开发)

### 开发模式

```bash
# 克隆项目到本地
git clone https://github.com/yourusername/MyBlog.git
cd MyBlog

# 安装 Python 依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py migrate
python manage.py createsuperuser

# 安装前端依赖
cd frontend
npm install

# 启动开发服务器
# 终端1: Django 后端
python manage.py runserver

# 终端2: Vite 前端热更新
cd frontend
npm run dev
```

### 生产构建

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 构建前端资源
cd frontend
npm install
npm run build

# 启动生产服务器
gunicorn djangoblog.wsgi:application --bind 0.0.0.0:8000
```

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      Django 后端                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  博客模型     │  │   插件系统    │  │   OAuth 集成    │  │
│  │  Article     │  │  BasePlugin  │  │  GitHub/Google  │  │
│  │  Category    │  │  Hooks       │  │                 │  │
│  │  Comment     │  │              │  │                 │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│         │                 │                  │               │
│         └────────┬────────┴─────────────────┘               │
│                  │                                          │
├─────────────────┼──────────────────────────────────────────┤
│                 ▼                                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            前端 (Tailwind + Alpine + HTMX)             │  │
│  │   响应式设计 / 夜间模式 / 动态壁纸 / 评论系统            │  │
│  └───────────────────────────────────────────────────────┘  │
│                    渲染进程                                   │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
MyBlog/
├── accounts/                  # 用户认证模块
│   ├── models.py            # BlogUser 模型
│   ├── views.py            # 登录/注册视图
│   └── urls.py
├── blog/                    # 博客核心模块
│   ├── models.py           # Article/Category/Tag 模型
│   ├── views.py            # 博客视图
│   ├── urls.py
│   ├── context_processors.py  # 上下文处理器
│   └── templatetags/      # 自定义模板标签
├── comments/                # 评论系统
│   ├── models.py
│   ├── views.py
│   └── forms.py
├── oauth/                   # OAuth 第三方登录
│   ├── models.py
│   └── views.py
├── plugins/                 # 插件系统
│   ├── article_copyright/  # 文章版权插件
│   ├── view_count/        # 浏览统计插件
│   ├── seo_optimizer/     # SEO 优化插件
│   └── ...
├── templates/               # HTML 模板
│   ├── blog/              # 博客页面
│   ├── account/           # 用户账户页面
│   └── share_layout/      # 公共布局
├── frontend/               # 前端资源 (Vite)
│   ├── src/
│   │   ├── main.js
│   │   ├── styles/        # Tailwind CSS
│   │   └── components/    # 前端组件
│   └── vite.config.js
├── djangoblog/            # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── utils.py           # 工具函数 (每日壁纸)
├── manage.py
└── requirements.txt
```

## 技术栈

| 项        | 选型                           |
| -------- | ---------------------------- |
| 后端框架     | Django 5.2                   |
| 开发语言     | Python 3.10+                 |
| 数据库      | MySQL, SQLite                |
| 缓存       | Redis, LocalMem              |
| 前端框架     | Vue 3 (Electron) / Alpine.js |
| CSS 框架   | Tailwind CSS 3.4             |
| JS 工具    | HTMX 1.9, Vite 5.4           |
| 搜索引擎     | Whoosh, Elasticsearch        |
| Markdown | mdeditor                     |

## 数据存储

```
MyBlog/
├── db.sqlite3              # SQLite 数据库 (开发环境)
├── uploads/                # 用户上传文件
│   ├── avatar/            # 头像
│   └── background/        # 背景图片
├── whoosh_index/          # Whoosh 搜索引擎索引
├── collectedstatic/        # 收集的静态文件
└── logs/                  # 日志文件
```

## 许可证

MIT License

## 🙏 鸣谢

特别感谢 **JetBrains** 为本项目提供的免费开源许可证。

<p align="center">
  <a href="">
    <img src="/docs/imgs/pycharm_logo.png" width="150" alt="JetBrains Logo">
  </a>
</p>
