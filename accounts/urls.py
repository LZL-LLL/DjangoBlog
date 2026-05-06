from django.urls import path, re_path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    re_path(r'^login/$',
            views.LoginView.as_view(success_url='/'),
            name='login',
            kwargs={'authentication_form': LoginForm}),
    re_path(r'^register/$',
            views.RegisterView.as_view(success_url="/"),
            name='register'),
    re_path(r'^logout/$',
            views.LogoutView.as_view(),
            name='logout'),
    path(r'account/result.html',
         views.account_result,
         name='result'),
    re_path(r'^forget_password/$',
            views.ForgetPasswordView.as_view(),
            name='forget_password'),
    re_path(r'^forget_password_code/$',
            views.ForgetPasswordEmailCode.as_view(),
            name='forget_password_code'),
    # 个人中心
    path('profile/',
         views.ProfileView.as_view(),
         name='profile'),
    path('article/create/',
         views.ArticleCreateView.as_view(),
         name='article_create'),
    path('article/<int:pk>/edit/',
         views.ArticleEditView.as_view(),
         name='article_edit'),
    path('article/<int:pk>/delete/',
         views.ArticleDeleteView.as_view(),
         name='article_delete'),
    path('subscribe/toggle/',
         views.SubscribeToggleView.as_view(),
         name='subscribe_toggle'),
    path('bookmark/toggle/',
         views.BookmarkToggleView.as_view(),
         name='bookmark_toggle'),
]
