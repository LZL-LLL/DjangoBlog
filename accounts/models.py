from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from djangoblog.utils import get_current_site


# Create your models here.

class BlogUser(AbstractUser):
    nickname = models.CharField(_('nick name'), max_length=100, blank=True)
    avatar = models.ImageField(_('avatar'), upload_to='avatar/', blank=True, null=True)
    bio = models.TextField(_('bio'), max_length=500, blank=True, default='')
    location = models.CharField(_('location'), max_length=200, blank=True, default='')
    skills = models.CharField(_('skills'), max_length=500, blank=True, default='')
    creation_time = models.DateTimeField(_('creation time'), default=now)
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)
    source = models.CharField(_('create source'), max_length=100, blank=True)

    def get_absolute_url(self):
        return reverse(
            'blog:author_detail', kwargs={
                'author_name': self.username})

    def __str__(self):
        return self.email

    def get_full_url(self):
        site = get_current_site().domain
        url = "https://{site}{path}".format(site=site,
                                            path=self.get_absolute_url())
        return url

    class Meta:
        ordering = ['-id']
        verbose_name = _('user')
        verbose_name_plural = verbose_name
        get_latest_by = 'id'


class ViewHistory(models.Model):
    """文章浏览记录"""
    user = models.ForeignKey(BlogUser, on_delete=models.CASCADE, verbose_name=_('user'))
    article = models.ForeignKey('blog.Article', on_delete=models.CASCADE, verbose_name=_('article'))
    viewed_at = models.DateTimeField(_('view time'), auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        verbose_name = _('view history')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user} - {self.article.title}'


class Subscription(models.Model):
    """用户订阅"""
    subscriber = models.ForeignKey(BlogUser, on_delete=models.CASCADE, related_name='subscriptions', verbose_name=_('subscriber'))
    author = models.ForeignKey(BlogUser, on_delete=models.CASCADE, related_name='subscribers', verbose_name=_('author'))
    created_at = models.DateTimeField(_('subscribe time'), auto_now_add=True)

    class Meta:
        unique_together = ('subscriber', 'author')
        ordering = ['-created_at']
        verbose_name = _('subscription')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.subscriber} -> {self.author}'


class Bookmark(models.Model):
    """文章收藏"""
    user = models.ForeignKey(BlogUser, on_delete=models.CASCADE, related_name='bookmarks', verbose_name=_('user'))
    article = models.ForeignKey('blog.Article', on_delete=models.CASCADE, related_name='bookmarks', verbose_name=_('article'))
    created_at = models.DateTimeField(_('bookmark time'), auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-created_at']
        verbose_name = _('bookmark')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user} - {self.article.title}'
