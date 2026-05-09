import logging
import mimetypes
import os
import uuid

from django.conf import settings
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from haystack.views import SearchView

from blog.models import Article, Category, GuestbookMessage, LinkShowType, Links, Tag
from comments.forms import CommentForm
from djangoblog.plugin_manage import hooks
from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME
from djangoblog.utils import cache, get_blog_setting, get_sha256
from djangoblog.mixins import (
    SlugCachedMixin,
    ArticleListMixin,
    OptimizedArticleQueryMixin,
    CachedListViewMixin,
    PageNumberMixin
)

logger = logging.getLogger(__name__)


class ArticleListView(CachedListViewMixin, PageNumberMixin, ListView):
    """
    文章列表视图基类（重构版）

    使用 Mixin 简化代码，消除重复逻辑
    子类只需实现 get_queryset_data() 和 get_queryset_cache_key() 方法
    """
    # template_name属性用于指定使用哪个模板进行渲染
    template_name = 'blog/article_index.html'

    # context_object_name属性用于给上下文变量取名（在模板中使用该名字）
    context_object_name = 'article_list'

    # 页面类型，分类目录或标签列表等
    page_type = ''
    paginate_by = settings.PAGINATE_BY
    page_kwarg = 'page'
    link_type = LinkShowType.L

    def get_view_cache_key(self):
        return self.request.get['pages']

    def get_context_data(self, **kwargs):
        kwargs['linktype'] = self.link_type
        return super(ArticleListView, self).get_context_data(**kwargs)


class IndexView(OptimizedArticleQueryMixin, ArticleListView):
    """
    首页视图（重构版）

    继承 OptimizedArticleQueryMixin 获得优化的查询方法
    """
    # 友情链接类型
    link_type = LinkShowType.I

    def get_queryset_data(self):
        # 使用 Mixin 提供的优化查询方法
        return self.get_optimized_article_queryset().filter(
            type='a', status='p'
        )

    def get_queryset_cache_key(self):
        return f'index_{self.page_number}'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blog_setting = get_blog_setting()
        # 提供基础SEO数据
        context['seo_title'] = f"{blog_setting.site_name} | {blog_setting.site_description}"
        context['seo_description'] = blog_setting.site_seo_description
        context['seo_keywords'] = blog_setting.site_keywords
        return context


class ArticleDetailView(DetailView):
    '''
    文章详情页面
    '''
    template_name = 'blog/article_detail.html'
    model = Article
    pk_url_kwarg = 'article_id'
    context_object_name = "article"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # 记录浏览历史
        if self.request.user.is_authenticated:
            from accounts.models import ViewHistory
            ViewHistory.objects.update_or_create(
                user=self.request.user,
                article=obj,
                defaults={'viewed_at': __import__('django').utils.timezone.now()}
            )
        return obj

    def get_context_data(self, **kwargs):
        comment_form = CommentForm()

        # 优化：直接查询父评论，减少数据库查询
        from comments.models import Comment
        parent_comments = Comment.objects.filter(
            article=self.object,
            parent_comment=None,
            is_enable=True
        ).select_related('author').prefetch_related(
            'comment_set__author'  # 预加载子评论及其作者
        ).order_by('-id')

        # 获取所有评论用于总数显示
        article_comments = self.object.comment_list()

        blog_setting = get_blog_setting()
        paginator = Paginator(parent_comments, blog_setting.article_comment_count)
        page = self.request.GET.get('comment_page', '1')
        if not page.isnumeric():
            page = 1
        else:
            page = int(page)
            if page < 1:
                page = 1
            if page > paginator.num_pages:
                page = paginator.num_pages

        p_comments = paginator.page(page)
        next_page = p_comments.next_page_number() if p_comments.has_next() else None
        prev_page = p_comments.previous_page_number() if p_comments.has_previous() else None

        if next_page:
            kwargs[
                'comment_next_page_url'] = self.object.get_absolute_url() + f'?comment_page={next_page}#commentlist-container'
        if prev_page:
            kwargs[
                'comment_prev_page_url'] = self.object.get_absolute_url() + f'?comment_page={prev_page}#commentlist-container'
        kwargs['form'] = comment_form
        kwargs['article_comments'] = article_comments
        kwargs['p_comments'] = p_comments
        kwargs['comment_count'] = len(
            article_comments) if article_comments else 0

        kwargs['next_article'] = self.object.next_article
        kwargs['prev_article'] = self.object.prev_article

        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        article = self.object

        # 订阅状态
        context['is_subscribed'] = False
        if self.request.user.is_authenticated:
            from accounts.models import Subscription
            context['is_subscribed'] = Subscription.objects.filter(
                subscriber=self.request.user,
                author=article.author
            ).exists()

        # 收藏状态
        context['is_bookmarked'] = False
        if self.request.user.is_authenticated:
            from accounts.models import Bookmark
            context['is_bookmarked'] = Bookmark.objects.filter(
                user=self.request.user,
                article=article
            ).exists()

        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        from django.utils.html import strip_tags
        from django.utils.text import Truncator
        from djangoblog.utils import CommonMarkdown
        
        # 处理description：markdown -> HTML -> 纯文本，彻底去除格式
        html_content = CommonMarkdown.get_markdown(article.body)
        description = strip_tags(html_content)
        description = ' '.join(description.split())  # 规范化空白字符
        description = Truncator(description).chars(150, truncate='...')
        
        # 处理keywords：去除空格，用逗号分隔
        tags = [tag.name.strip() for tag in article.tags.all()]
        keywords = ", ".join(tags) if tags else blog_setting.site_keywords
        
        context['seo_title'] = f"{article.title} | {blog_setting.site_name}"
        context['seo_description'] = description
        context['seo_keywords'] = keywords
        
        # 触发文章详情加载钩子，让插件可以添加额外的上下文数据
        from djangoblog.plugin_manage.hook_constants import ARTICLE_DETAIL_LOAD
        hooks.run_action(ARTICLE_DETAIL_LOAD, article=article, context=context, request=self.request)
        
        # Action Hook, 通知插件"文章详情已获取"
        hooks.run_action('after_article_body_get', article=article, request=self.request)
        return context


class CategoryDetailView(SlugCachedMixin, OptimizedArticleQueryMixin, ArticleListView):
    """
    分类目录列表（重构版）

    使用 SlugCachedMixin 避免重复查询 Category
    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = "分类目录归档"
    slug_url_kwarg = 'category_name'
    slug_model = Category

    def get_queryset_data(self):
        # 使用 Mixin 缓存的对象，只查询一次
        category = self.get_slug_object()
        categorynames = [c.name for c in category.get_sub_categorys()]

        return self.get_optimized_article_queryset().filter(
            category__name__in=categorynames, status='p'
        )

    def get_queryset_cache_key(self):
        # 复用缓存的对象，不再重复查询数据库
        category = self.get_slug_object()
        return f'category_list_{category.name}_{self.page_number}'

    def get_context_data(self, **kwargs):
        category = self.get_slug_object()
        categoryname = category.name

        try:
            categoryname = categoryname.split('/')[-1]
        except BaseException:
            pass

        kwargs['page_type'] = CategoryDetailView.page_type
        kwargs['tag_name'] = categoryname
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{categoryname} | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览 {categoryname} 分类下的所有文章，共 {article_count} 篇文章。"
        kwargs['seo_keywords'] = f"{categoryname}, {blog_setting.site_keywords}"
        
        return super(CategoryDetailView, self).get_context_data(**kwargs)


class AuthorDetailView(OptimizedArticleQueryMixin, ArticleListView):
    """
    作者详情页（重构版）

    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '作者文章归档'

    def get_queryset_cache_key(self):
        from uuslug import slugify
        author_name = slugify(self.kwargs['author_name'])
        return f'author_{author_name}_{self.page_number}'

    def get_queryset_data(self):
        author_name = self.kwargs['author_name']
        return self.get_optimized_article_queryset().filter(
            author__username=author_name, type='a', status='p'
        )

    def get_context_data(self, **kwargs):
        author_name = self.kwargs['author_name']
        kwargs['page_type'] = AuthorDetailView.page_type
        kwargs['tag_name'] = author_name
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{author_name} 的文章 | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览 {author_name} 发表的所有文章，共 {article_count} 篇。"
        kwargs['seo_keywords'] = f"{author_name}, {blog_setting.site_keywords}"
        
        return super(AuthorDetailView, self).get_context_data(**kwargs)


class TagDetailView(SlugCachedMixin, OptimizedArticleQueryMixin, ArticleListView):
    """
    标签列表页面（重构版）

    使用 SlugCachedMixin 避免重复查询 Tag
    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '分类标签归档'
    slug_url_kwarg = 'tag_name'
    slug_model = Tag

    def get_queryset_data(self):
        # 使用 Mixin 缓存的对象，只查询一次
        tag = self.get_slug_object()
        return self.get_optimized_article_queryset().filter(
            tags__name=tag.name, type='a', status='p'
        )

    def get_queryset_cache_key(self):
        # 复用缓存的对象，不再重复查询数据库
        tag = self.get_slug_object()
        return f'tag_{tag.name}_{self.page_number}'

    def get_context_data(self, **kwargs):
        tag = self.get_slug_object()
        kwargs['page_type'] = TagDetailView.page_type
        kwargs['tag_name'] = tag.name
        
        # 添加基础SEO数据
        blog_setting = get_blog_setting()
        article_count = self.get_queryset().count()
        kwargs['seo_title'] = f"{tag.name} | {blog_setting.site_name}"
        kwargs['seo_description'] = f"浏览所有关于 {tag.name} 的文章，共 {article_count} 篇内容。"
        kwargs['seo_keywords'] = f"{tag.name}, {blog_setting.site_keywords}"
        
        return super(TagDetailView, self).get_context_data(**kwargs)


class ArchivesView(OptimizedArticleQueryMixin, ArticleListView):
    """
    文章归档页面（重构版）

    使用 OptimizedArticleQueryMixin 优化文章查询
    """
    page_type = '文章归档'
    paginate_by = None
    page_kwarg = None
    template_name = 'blog/article_archives.html'

    def get_queryset_data(self):
        return self.get_optimized_article_queryset().filter(status='p')

    def get_queryset_cache_key(self):
        return 'archives'


class LinkListView(ListView):
    model = Links
    template_name = 'blog/links_list.html'

    def get_queryset(self):
        return Links.objects.filter(is_enable=True)


class GuestbookView(ListView):
    """留言板"""
    model = GuestbookMessage
    template_name = 'blog/guestbook.html'
    context_object_name = 'message_list'
    paginate_by = 20

    def get_queryset(self):
        return GuestbookMessage.objects.filter(is_enable=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blog_setting = get_blog_setting()
        context['seo_title'] = f"留言板 | {blog_setting.site_name}"
        context['seo_description'] = "欢迎在留言板留下您的宝贵意见"
        context['seo_keywords'] = f"留言板, {blog_setting.site_keywords}"
        return context

    def post(self, request, *args, **kwargs):
        nickname = request.POST.get('nickname', '').strip()
        email = request.POST.get('email', '').strip()
        body = request.POST.get('body', '').strip()

        if not body:
            return render(request, self.template_name, {
                'message_list': self.get_queryset(),
                'error': '留言内容不能为空',
                'nickname': nickname,
                'email': email,
            })

        if not nickname:
            nickname = '匿名'

        GuestbookMessage.objects.create(
            nickname=nickname,
            email=email or None,
            body=body,
            is_enable=True
        )

        from django.shortcuts import redirect
        return redirect('blog:guestbook')


class EsSearchView(SearchView):
    def build_form(self, form_kwargs=None):
        """Override to enable highlighting"""
        if form_kwargs is None:
            form_kwargs = {}

        # Enable highlighting for search results
        from haystack.query import SearchQuerySet
        if self.searchqueryset is None:
            sqs = SearchQuerySet().highlight()
        else:
            sqs = self.searchqueryset.highlight()

        form_kwargs['searchqueryset'] = sqs
        return super().build_form(form_kwargs=form_kwargs)

    def get_context(self):
        paginator, page = self.build_page()
        context = {
            "query": self.query,
            "form": self.form,
            "page": page,
            "paginator": paginator,
            "suggestion": None,
        }
        if hasattr(self.results, "query") and self.results.query.backend.include_spelling:
            context["suggestion"] = self.results.query.get_spelling_suggestion()
        context.update(self.extra_context())

        return context


@csrf_exempt
def fileupload(request):
    """
    该方法需自己写调用端来上传图片，该方法仅提供图床功能
    :param request:
    :return:
    """
    if request.method == 'POST':
        sign = request.GET.get('sign', None)
        if not sign:
            return HttpResponseForbidden()
        if not sign == get_sha256(get_sha256(settings.SECRET_KEY)):
            return HttpResponseForbidden()
        response = []
        for filename in request.FILES:
            timestr = timezone.now().strftime('%Y/%m/%d')
            imgextensions = ['jpg', 'png', 'jpeg', 'bmp']
            fname = u''.join(str(filename))
            isimage = len([i for i in imgextensions if fname.find(i) >= 0]) > 0
            base_dir = os.path.join(settings.STATICFILES, "files" if not isimage else "image", timestr)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            savepath = os.path.normpath(os.path.join(base_dir, f"{uuid.uuid4().hex}{os.path.splitext(filename)[-1]}"))
            if not savepath.startswith(base_dir):
                return HttpResponse("only for post")
            with open(savepath, 'wb+') as wfile:
                for chunk in request.FILES[filename].chunks():
                    wfile.write(chunk)
            if isimage:
                from PIL import Image
                image = Image.open(savepath)
                image.save(savepath, quality=20, optimize=True)
            url = static(savepath)
            response.append(url)
        return HttpResponse(response)

    else:
        return HttpResponse("only for post")


# ===== 错误处理视图 =====
# 注意：这些函数保留是为了向后兼容
# 实际实现已经移动到 djangoblog.error_views
# 可以在 urls.py 中直接引用新的实现

from djangoblog.error_views import (
    page_not_found_view,
    server_error_view,
    permission_denied_view
)


@csrf_exempt
def ai_chat(request):
    """AI 小助手聊天接口"""
    import json
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': '仅支持POST请求'}, status=405)

    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': '无效的请求数据'}, status=400)

    if not message:
        return JsonResponse({'error': '消息不能为空'}, status=400)

    if len(message) > 500:
        return JsonResponse({'error': '消息太长啦，请控制在500字以内'}, status=400)

    ai_response = _get_ai_response(message)

    return JsonResponse({
        'reply': ai_response,
        'status': 'ok'
    })


def _get_ai_response(message):
    """
    获取 AI 回复
    优先使用外部 API（如配置），否则使用内置回复
    """
    api_key = getattr(settings, 'AI_ASSISTANT_API_KEY', None)
    api_url = getattr(settings, 'AI_ASSISTANT_API_URL', None)

    if api_key and api_url:
        try:
            return _call_external_api(message, api_key, api_url)
        except Exception as e:
            logger.warning(f'AI API call failed: {e}, using fallback')
            return _get_fallback_response(message)

    return _get_fallback_response(message)


def _call_external_api(message, api_key, api_url):
    """调用外部 AI API (兼容 OpenAI 格式)"""
    import requests
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    system_prompt = getattr(settings, 'AI_ASSISTANT_SYSTEM_PROMPT',
        '你是一个技术博客的AI助手，帮助博主优化博客内容、回答问题、提供技术建议。'
        '你热情友好，专业但不枯燥。回复简短精炼，使用中文。')

    payload = {
        'model': getattr(settings, 'AI_ASSISTANT_MODEL', 'Qwen/Qwen2.5-7B-Instruct'),
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': message}
        ],
        'max_tokens': 500,
        'temperature': 0.7,
        'stream': False,
    }
    resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    # 兼容不同 API 返回格式
    if 'choices' in result and len(result['choices']) > 0:
        return result['choices'][0]['message']['content']
    return str(result)


def _get_fallback_response(message):
    """内置智能回复（当未配置外部 API 时使用）"""
    import random

    greetings = ['你好', '嗨', 'hello', 'hi', '您好', '你好呀', '在吗', 'hey']
    thanks = ['谢谢', '感谢', '多谢', 'thx', 'thanks']
    blog_questions = ['博客', '优化', '建议', '改进', '文章', '内容']
    tech_questions = ['python', 'django', '教程', '学习', '编程', '代码', '技术', '前端', '后端']
    about_site = ['网站', '功能', '主题', '部署', 'pythonanywhere', '速度', 'seo']

    msg_lower = message.lower()

    if any(g in msg_lower for g in greetings):
        return random.choice([
            '你好呀！我是博客小助手，有什么可以帮你的吗？😊',
            '嗨！欢迎来找我聊天～有什么想问的或想讨论的吗？',
            '你好！我正在这里呢，有什么需要帮助的吗？',
        ])

    if any(t in msg_lower for t in thanks):
        return random.choice([
            '不客气！随时找我聊天哦～',
            '应该的！有什么想法随时告诉我 😊',
            '别客气，一起让博客变得更好吧！',
        ])

    if any(b in msg_lower for b in blog_questions):
        if '优化' in msg_lower or '建议' in msg_lower:
            return random.choice([
                '关于博客优化，我有几个建议：\n\n'
                '1. 📝 **内容为王** - 定期更新高质量的原创内容\n'
                '2. 🔍 **SEO优化** - 注意文章标题和描述的SEO设置\n'
                '3. ⚡ **加载速度** - 优化图片大小，使用缓存\n'
                '4. 📱 **移动端体验** - 确保在手机上阅读舒适\n'
                '5. 💬 **互动** - 多和读者互动，回复评论\n\n'
                '你对哪方面比较感兴趣？我可以详细说说！',
                '想让博客更受欢迎？可以试试：\n\n'
                '🎯 找准定位，持续输出某个领域的深度内容\n'
                '📊 分析访问数据，了解读者喜好\n'
                '🔗 和其他博主交换友链，互推流量\n'
                '🎨 优化页面设计，提升阅读体验\n\n'
                '你觉得哪个方向最适合现在的博客？',
            ])

        return random.choice([
            '你的博客已经做得很棒了！要继续保持更新频率哦 💪\n'
            '如果想新增功能或者改进设计，随时告诉我～',
            '写博客最重要的是坚持！你已经迈出了最重要的一步。'
            '有什么想要增加的新功能或内容方向吗？我们可以一起规划！',
        ])

    if any(t in msg_lower for t in tech_questions):
        return random.choice([
            '技术学习最重要的是动手实践！遇到具体问题随时问我～\n'
            '比如 Django 配置、前端样式、部署运维等，我都可以帮你分析。',
            '在技术选型上，我建议选择社区活跃、文档完善的技术栈。\n'
            '你现在用的 Django + Tailwind + Alpine.js 就是一个很棒的组合！\n'
            '有什么具体的技术问题想讨论吗？',
        ])

    if any(s in msg_lower for s in about_site):
        return random.choice([
            '关于网站功能，目前已有的功能包括：\n'
            '✨ 文章管理（分类/标签/归档）\n'
            '💬 评论系统（支持 emoji 反应）\n'
            '🔍 全文搜索\n'
            '🌙 深色模式\n'
            '📱 响应式设计\n\n'
            '你还想添加什么新功能吗？我帮你实现！',
            '网站目前部署在 PythonAnywhere，速度和稳定性都不错。\n'
            '如果访问量增长，可以考虑升级套餐或迁移到云服务器。\n'
            '有什么部署或性能方面的问题吗？',
        ])

    # Default responses
    return random.choice([
        '很有意思的话题！能多说说你的想法吗？我很想听听 😊',
        '原来你是这么想的呀！让我想想怎么帮你～',
        '我收到了！可以再具体一点描述你的需求吗？\n这样我能给出更有针对性的建议～',
        '好问题！让我想想… 你可以先在博客上写一篇文章分享你的观点，\n然后我们可以一起讨论和优化！',
        '你的想法很棒！作为一个博客助手，我建议可以把这些想法\n整理成文章分享出来，一定会很有价值！',
    ])


def clean_cache_view(request):
    cache.clear()
    return HttpResponse('ok')


def download_attachment(request, attachment_id):
    """下载文章附件（优先本地，不存在时重定向到 GitHub Release）"""
    from blog.models import ArticleAttachment
    from django.http import FileResponse, HttpResponseRedirect
    attachment = get_object_or_404(ArticleAttachment, pk=attachment_id)
    if not attachment.file:
        return HttpResponse('文件不存在', status=404)
    import os.path
    file_path = attachment.file.path
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
        response['Content-Length'] = attachment.file_size or os.path.getsize(file_path)
        return response
    # 本地文件不存在时，重定向到 GitHub Release（适用于 PythonAnywhere）
    from django.conf import settings
    base_url = getattr(settings, 'GITHUB_ATTACHMENT_BASE_URL', '')
    if base_url:
        from urllib.parse import quote
        # 使用实际文件名（file.name 是 upload_to 相对路径）
        actual_filename = os.path.basename(attachment.file.name)
        redirect_url = f'{base_url.rstrip("/")}/{quote(actual_filename)}'
        return HttpResponseRedirect(redirect_url)
    return HttpResponse('文件不存在', status=404)


def daily_wallpaper(request):
    """提供每日壁纸文件"""
    from djangoblog.utils import get_daily_wallpaper
    wallpaper = get_daily_wallpaper()
    if not wallpaper:
        return HttpResponse(status=204)
    file_path = wallpaper['path']
    if not os.path.exists(file_path):
        return HttpResponse(status=204)
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'video/mp4' if wallpaper['type'] == 'video' else 'image/jpeg'
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Cache-Control'] = 'public, max-age=86400'
    return response
