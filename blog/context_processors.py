import logging

from django.utils import timezone

from djangoblog.utils import cache, get_blog_setting
from .models import Category, Article

logger = logging.getLogger(__name__)


def seo_processor(requests):
    key = 'seo_processor'
    value = cache.get(key)
    if value:
        # 更新动态值（不需要缓存的内容）
        value['SITE_BASE_URL'] = requests.scheme + '://' + requests.get_host() + '/'
        value['CURRENT_YEAR'] = timezone.now().year
        return value
    else:
        logger.info('set processor cache.')
        setting = get_blog_setting()

        # 优化查询：预加载关联数据
        nav_category_list = Category.objects.all()
        nav_pages = Article.objects.filter(
            type='p',
            status='p'
        )

        value = {
            'SITE_NAME': setting.site_name,
            'SHOW_GOOGLE_ADSENSE': setting.show_google_adsense,
            'GOOGLE_ADSENSE_CODES': setting.google_adsense_codes,
            'SITE_SEO_DESCRIPTION': setting.site_seo_description,
            'SITE_DESCRIPTION': setting.site_description,
            'SITE_KEYWORDS': setting.site_keywords,
            'SITE_BASE_URL': requests.scheme + '://' + requests.get_host() + '/',
            'ARTICLE_SUB_LENGTH': setting.article_sub_length,
            'nav_category_list': nav_category_list,  # 保持QuerySet
            'nav_pages': nav_pages,  # 保持QuerySet
            'OPEN_SITE_COMMENT': setting.open_site_comment,
            'BEIAN_CODE': setting.beian_code,
            'ANALYTICS_CODE': setting.analytics_code,
            "BEIAN_CODE_GONGAN": setting.gongan_beiancode,
            "SHOW_GONGAN_CODE": setting.show_gongan_code,
            "CURRENT_YEAR": timezone.now().year,
            "GLOBAL_HEADER": setting.global_header,
            "GLOBAL_FOOTER": setting.global_footer,
            "COMMENT_NEED_REVIEW": setting.comment_need_review,
            "COLOR_SCHEME": setting.color_scheme,
            "AVATAR_URL": setting.avatar.url if setting.avatar else None,
            "BACKGROUND_URL": setting.background_image.url if setting.background_image else None,
            "BIO": setting.bio or '',
            "LOCATION": setting.location or '',
            "PERSONAL_WEBSITE": setting.personal_website or '',
            "SKILLS": [s.strip() for s in setting.skills.split(',') if s.strip()] if setting.skills else [],
            "DAILY_WALLPAPER": True,
        }
        cache.set(key, value, 60 * 60 * 10)
        return value


def wallpaper_processor(requests):
    """每日壁纸信息（不缓存，轻量）"""
    import mimetypes

    from djangoblog.utils import get_daily_wallpaper
    wallpaper = get_daily_wallpaper()
    if wallpaper:
        mime, _ = mimetypes.guess_type(wallpaper['path'])
        if mime is None:
            mime = 'video/mp4' if wallpaper['type'] == 'video' else 'image/jpeg'
        return {
            'WALLPAPER_TYPE': wallpaper['type'],
            'WALLPAPER_URL': '/daily-wallpaper',
            'WALLPAPER_MIME': mime,
        }
    return {}
