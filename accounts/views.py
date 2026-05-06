import logging
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, ListView

from djangoblog.utils import send_email, get_sha256, get_current_site, generate_code, delete_sidebar_cache
from djangoblog.base_views import SecureFormView, LoginFormView, LogoutRedirectView
from . import utils
from .forms import RegisterForm, LoginForm, ForgetPasswordForm, ForgetPasswordCodeForm
from .models import BlogUser, ViewHistory, Subscription, Bookmark
from blog.models import Article, Category, Tag

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


# Create your views here.

class RegisterView(SecureFormView):
    """
    用户注册视图（重构版）

    使用 SecureFormView 基类，自动提供 CSRF 保护
    """
    form_class = RegisterForm
    template_name = 'account/registration_form.html'

    def form_valid(self, form):
        if form.is_valid():
            user = form.save(False)
            user.is_active = False
            user.source = 'Register'
            user.save(True)
            site = get_current_site().domain
            sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))

            if settings.DEBUG:
                site = '127.0.0.1:8000'
            path = reverse('account:result')
            url = "http://{site}{path}?type=validation&id={id}&sign={sign}".format(
                site=site, path=path, id=user.id, sign=sign)

            content = """
                            <p>请点击下面链接验证您的邮箱</p>

                            <a href="{url}" rel="bookmark">{url}</a>

                            再次感谢您！
                            <br />
                            如果上面链接无法打开，请将此链接复制至浏览器。
                            {url}
                            """.format(url=url)
            send_email(
                emailto=[
                    user.email,
                ],
                title='验证您的电子邮箱',
                content=content)

            url = reverse('account:result') + \
                  '?type=register&id=' + str(user.id)
            return HttpResponseRedirect(url)
        else:
            return self.render_to_response({
                'form': form
            })


class LogoutView(LogoutRedirectView):
    """
    用户登出视图（重构版）

    使用 LogoutRedirectView 基类，自动禁用缓存
    """
    url = '/login/'

    def get(self, request, *args, **kwargs):
        logout(request)
        delete_sidebar_cache()
        # 获取响应对象并删除登录标记 cookie
        response = super(LogoutView, self).get(request, *args, **kwargs)
        response.delete_cookie('logged_user')
        return response


class LoginView(LoginFormView):
    """
    用户登录视图（重构版）

    使用 LoginFormView 基类，自动提供：
    - 敏感参数保护（password）
    - CSRF 保护
    - 禁用缓存
    """
    form_class = LoginForm
    template_name = 'account/login.html'
    success_url = '/'
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_context_data(self, **kwargs):
        redirect_to = self.request.GET.get(self.redirect_field_name)
        if redirect_to is None:
            redirect_to = '/'
        kwargs['redirect_to'] = redirect_to

        return super(LoginView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        form = AuthenticationForm(data=self.request.POST, request=self.request)

        if form.is_valid():
            delete_sidebar_cache()
            logger.info(self.redirect_field_name)

            auth.login(self.request, form.get_user())
            # 设置登录有效期
            if self.request.POST.get("remember"):
                self.request.session.set_expiry(settings.REMEMBER_ME_LOGIN_TTL)
                cookie_max_age = settings.REMEMBER_ME_LOGIN_TTL
            else:
                # 使用Django默认的2周
                self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                cookie_max_age = settings.SESSION_COOKIE_AGE

            # 获取响应对象并设置登录标记 cookie
            response = super(LoginView, self).form_valid(form)
            response.set_cookie(
                'logged_user',
                'true',
                max_age=cookie_max_age,
                httponly=False,  # 允许 JavaScript 访问
                samesite='Lax'
            )
            return response
            # return HttpResponseRedirect('/')
        else:
            return self.render_to_response({
                'form': form
            })

    def get_success_url(self):

        redirect_to = self.request.POST.get(self.redirect_field_name)
        if not url_has_allowed_host_and_scheme(
                url=redirect_to, allowed_hosts=[
                    self.request.get_host()]):
            redirect_to = self.success_url
        return redirect_to


def account_result(request):
    type = request.GET.get('type')
    id = request.GET.get('id')

    user = get_object_or_404(get_user_model(), id=id)
    logger.info(type)
    if user.is_active:
        return HttpResponseRedirect('/')
    if type and type in ['register', 'validation']:
        if type == 'register':
            content = '''
    恭喜您注册成功，一封验证邮件已经发送到您的邮箱，请验证您的邮箱后登录本站。
    '''
            title = '注册成功'
        else:
            c_sign = get_sha256(get_sha256(settings.SECRET_KEY + str(user.id)))
            sign = request.GET.get('sign')
            if sign != c_sign:
                return HttpResponseForbidden()
            user.is_active = True
            user.save()
            content = '''
            恭喜您已经成功的完成邮箱验证，您现在可以使用您的账号来登录本站。
            '''
            title = '验证成功'
        return render(request, 'account/result.html', {
            'title': title,
            'content': content
        })
    else:
        return HttpResponseRedirect('/')


class ForgetPasswordView(SecureFormView):
    """
    忘记密码视图（重构版）

    使用 SecureFormView 基类，自动提供 CSRF 保护
    """
    form_class = ForgetPasswordForm
    template_name = 'account/forget_password.html'

    def form_valid(self, form):
        if form.is_valid():
            blog_user = BlogUser.objects.filter(email=form.cleaned_data.get("email")).get()
            blog_user.password = make_password(form.cleaned_data["new_password2"])
            blog_user.save()
            return HttpResponseRedirect('/login/')
        else:
            return self.render_to_response({'form': form})


class ForgetPasswordEmailCode(View):

    def post(self, request: HttpRequest):
        form = ForgetPasswordCodeForm(request.POST)
        if not form.is_valid():
            return HttpResponse("错误的邮箱")
        to_email = form.cleaned_data["email"]

        code = generate_code()
        utils.send_verify_email(to_email, code)
        utils.set_code(to_email, code)

        return HttpResponse("ok")


# ==================== 个人中心 ====================

class ProfileView(LoginRequiredMixin, TemplateView):
    """个人中心页面"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['profile_user'] = user
        context['my_articles'] = Article.objects.filter(author=user).order_by('-creation_time')
        context['view_history'] = ViewHistory.objects.filter(user=user).select_related('article')[:30]
        context['bookmarks'] = Bookmark.objects.filter(user=user).select_related('article')[:30]
        context['subscriptions'] = Subscription.objects.filter(subscriber=user).select_related('author')
        context['subscribers'] = Subscription.objects.filter(author=user).select_related('subscriber')
        context['user_skills'] = [s.strip() for s in user.skills.split(',') if s.strip()] if user.skills else []
        return context

    def post(self, request, *args, **kwargs):
        user = request.user

        # 修改密码
        old_pw = request.POST.get('old_password', '')
        new_pw1 = request.POST.get('new_password1', '')
        new_pw2 = request.POST.get('new_password2', '')
        if old_pw and new_pw1 and new_pw2:
            if not user.check_password(old_pw):
                messages.error(request, '原密码错误')
            elif new_pw1 != new_pw2:
                messages.error(request, '两次输入的新密码不一致')
            elif len(new_pw1) < 6:
                messages.error(request, '密码长度不能少于6位')
            else:
                user.set_password(new_pw1)
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, '密码修改成功')

        # 修改资料
        nickname = request.POST.get('nickname', '').strip()
        email = request.POST.get('email', '').strip()
        bio = request.POST.get('bio', '').strip()
        location = request.POST.get('location', '').strip()
        skills = request.POST.get('skills', '').strip()
        if nickname:
            user.nickname = nickname
        if email and email != user.email:
            user.email = email
        user.bio = bio
        user.location = location
        user.skills = skills

        # 头像上传
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']

        user.save()
        return HttpResponseRedirect(reverse('account:profile'))


class ArticleCreateView(LoginRequiredMixin, CreateView):
    """创建文章"""
    model = Article
    fields = ['title', 'body', 'category', 'tags', 'status', 'comment_status', 'show_toc']
    template_name = 'accounts/article_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['all_tags'] = Tag.objects.all()
        context['selected_tags'] = []
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.type = 'a'
        if not form.instance.status:
            form.instance.status = 'd'
        self.object = form.save()
        # 手动处理标签
        tag_ids = self.request.POST.getlist('tags')
        tag_ids = [int(t) for t in tag_ids if t.isdigit()]
        self.object.tags.set(tag_ids)
        # 处理附件上传
        if self.request.FILES.get('attachment_file'):
            from blog.models import ArticleAttachment
            f = self.request.FILES['attachment_file']
            ArticleAttachment.objects.create(
                article=self.object,
                filename=f.name,
                file=f,
                file_size=f.size,
            )
            messages.success(self.request, f'附件 "{f.name}" 上传成功')
        else:
            messages.success(self.request, '文章创建成功')
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('account:profile')


class ArticleEditView(LoginRequiredMixin, UpdateView):
    """编辑文章（仅作者可编辑）"""
    model = Article
    fields = ['title', 'body', 'category', 'tags', 'status', 'comment_status', 'show_toc']
    template_name = 'accounts/article_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['all_tags'] = Tag.objects.all()
        context['editing'] = True
        context['selected_tags'] = list(self.object.tags.values_list('id', flat=True))
        return context

    def dispatch(self, request, *args, **kwargs):
        article = self.get_object()
        if article.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        # 手动处理标签
        tag_ids = self.request.POST.getlist('tags')
        tag_ids = [int(t) for t in tag_ids if t.isdigit()]
        self.object.tags.set(tag_ids)
        # 处理附件上传
        if self.request.FILES.get('attachment_file'):
            from blog.models import ArticleAttachment
            f = self.request.FILES['attachment_file']
            ArticleAttachment.objects.create(
                article=self.object,
                filename=f.name,
                file=f,
                file_size=f.size,
            )
            messages.success(self.request, f'附件 "{f.name}" 上传成功')
        else:
            messages.success(self.request, '文章修改已保存')
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('account:profile')


class ArticleDeleteView(LoginRequiredMixin, DeleteView):
    """删除文章（仅作者可删除）"""
    model = Article
    template_name = 'accounts/article_confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        article = self.get_object()
        if article.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('account:profile')


class SubscribeToggleView(LoginRequiredMixin, View):
    """切换订阅/取消订阅作者"""
    def post(self, request, *args, **kwargs):
        from django.http import HttpResponseBadRequest
        author_id = request.POST.get('author_id')
        if not author_id:
            return HttpResponseBadRequest()
        author = get_object_or_404(BlogUser, id=author_id)
        if author == request.user:
            return HttpResponseBadRequest('不能订阅自己')
        sub, created = Subscription.objects.get_or_create(
            subscriber=request.user,
            author=author
        )
        if not created:
            sub.delete()
            return HttpResponse('unsubscribed')
        return HttpResponse('subscribed')


class BookmarkToggleView(LoginRequiredMixin, View):
    """切换收藏/取消收藏文章"""
    def post(self, request, *args, **kwargs):
        from django.http import HttpResponseBadRequest
        article_id = request.POST.get('article_id')
        if not article_id:
            return HttpResponseBadRequest()
        article = get_object_or_404(Article, id=article_id)
        bm, created = Bookmark.objects.get_or_create(
            user=request.user,
            article=article
        )
        if not created:
            bm.delete()
            return HttpResponse('unbookmarked')
        return HttpResponse('bookmarked')
