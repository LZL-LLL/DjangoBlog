from django.core.management.base import BaseCommand
from blog.models import Tag

COMMON_TAGS = [
    'Python',
    'Django',
    'JavaScript',
    'TypeScript',
    'Vue',
    'React',
    'HTML',
    'CSS',
    'Tailwind',
    'Node.js',
    '前端',
    '后端',
    '全栈',
    '数据库',
    'MySQL',
    'Redis',
    'Linux',
    'Docker',
    'Git',
    'API',
    'REST',
    '算法',
    '教程',
    '笔记',
    '随笔',
    '分享',
    '项目',
    '工具',
]


class Command(BaseCommand):
    help = '创建常用标签预设'

    def handle(self, *args, **options):
        created = 0
        for name in COMMON_TAGS:
            tag, is_new = Tag.objects.get_or_create(name=name)
            if is_new:
                self.stdout.write(self.style.SUCCESS(f'  + {name}'))
                created += 1

        total = Tag.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\n新增 {created} 个标签，现有共 {total} 个标签')
        )
