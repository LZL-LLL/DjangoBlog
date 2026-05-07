import time

from django.conf import settings

ELASTICSEARCH_ENABLED = hasattr(settings, 'ELASTICSEARCH_DSL')

if ELASTICSEARCH_ENABLED:
    import elasticsearch.client
    from elasticsearch_dsl import Document, InnerDoc, Date, Integer, Long, Text, Object, GeoPoint, Keyword, Boolean
    from elasticsearch_dsl.connections import connections
    from blog.models import Article

    from elasticsearch import Elasticsearch

    es_config = settings.ELASTICSEARCH_DSL['default']

    # 处理 hosts 配置，确保有 scheme
    hosts = es_config['hosts']
    if isinstance(hosts, str):
        if not hosts.startswith(('http://', 'https://')):
            hosts = f'http://{hosts}'
        hosts = [hosts]
    elif isinstance(hosts, list):
        processed_hosts = []
        for host in hosts:
            if not host.startswith(('http://', 'https://')):
                host = f'http://{host}'
            processed_hosts.append(host)
        hosts = processed_hosts

    es_params = {
        'hosts': hosts,
        'verify_certs': es_config.get('verify_certs', False),
    }

    if 'username' in es_config and 'password' in es_config:
        es_params['basic_auth'] = (es_config['username'], es_config['password'])
    if 'api_key' in es_config:
        es_params['api_key'] = es_config['api_key']
    if 'ca_certs' in es_config:
        es_params['ca_certs'] = es_config['ca_certs']
    if 'client_cert' in es_config and 'client_key' in es_config:
        es_params['client_cert'] = es_config['client_cert']
        es_params['client_key'] = es_config['client_key']

    es = Elasticsearch(**es_params)
    connections.create_connection(**es_params)

    try:
        es.ingest.get_pipeline(id='geoip')
    except elasticsearch.exceptions.NotFoundError:
        es.ingest.put_pipeline(id='geoip', body={
            "description": "Add geoip info",
            "processors": [{"geoip": {"field": "ip"}}]
        })

    class GeoIp(InnerDoc):
        continent_name = Keyword()
        country_iso_code = Keyword()
        country_name = Keyword()
        location = GeoPoint()

    class UserAgentBrowser(InnerDoc):
        Family = Keyword()
        Version = Keyword()

    class UserAgentOS(UserAgentBrowser):
        pass

    class UserAgentDevice(InnerDoc):
        Family = Keyword()
        Brand = Keyword()
        Model = Keyword()

    class UserAgent(InnerDoc):
        browser = Object(UserAgentBrowser, required=False)
        os = Object(UserAgentOS, required=False)
        device = Object(UserAgentDevice, required=False)
        string = Text()
        is_bot = Boolean()

    class ElapsedTimeDocument(Document):
        url = Keyword()
        time_taken = Long()
        log_datetime = Date()
        ip = Keyword()
        geoip = Object(GeoIp, required=False)
        useragent = Object(UserAgent, required=False)

        class Index:
            name = 'performance'
            settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class ElaspedTimeDocumentManager:
        @staticmethod
        def build_index():
            client = Elasticsearch(**es_params)
            res = client.indices.exists(index="performance")
            if not res:
                ElapsedTimeDocument.init()

        @staticmethod
        def delete_index():
            es = Elasticsearch(**es_params)
            try:
                es.indices.delete(index='performance')
            except elasticsearch.exceptions.NotFoundError:
                pass

        @staticmethod
        def create(url, time_taken, log_datetime, useragent, ip):
            ElaspedTimeDocumentManager.build_index()
            ua = UserAgent()
            ua.browser = UserAgentBrowser()
            ua.browser.Family = useragent.browser.family
            ua.browser.Version = useragent.browser.version_string
            ua.os = UserAgentOS()
            ua.os.Family = useragent.os.family
            ua.os.Version = useragent.os.version_string
            ua.device = UserAgentDevice()
            ua.device.Family = useragent.device.family
            ua.device.Brand = useragent.device.brand
            ua.device.Model = useragent.device.model
            ua.string = useragent.ua_string
            ua.is_bot = useragent.is_bot
            doc = ElapsedTimeDocument(
                meta={'id': int(round(time.time() * 1000))},
                url=url, time_taken=time_taken,
                log_datetime=log_datetime, useragent=ua, ip=ip)
            doc.save(pipeline="geoip")

    class ArticleDocument(Document):
        body = Text(analyzer='ik_max_word', search_analyzer='ik_smart')
        title = Text(analyzer='ik_max_word', search_analyzer='ik_smart')
        author = Object(properties={
            'nickname': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
            'id': Integer()
        })
        category = Object(properties={
            'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
            'id': Integer()
        })
        tags = Object(properties={
            'name': Text(analyzer='ik_max_word', search_analyzer='ik_smart'),
            'id': Integer()
        })
        pub_time = Date()
        status = Text()
        comment_status = Text()
        type = Text()
        views = Integer()
        article_order = Integer()

        class Index:
            name = 'blog'
            settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class ArticleDocumentManager:
        def __init__(self):
            self.create_index()

        def create_index(self):
            ArticleDocument.init()

        def delete_index(self):
            es = Elasticsearch(**es_params)
            try:
                es.indices.delete(index='blog')
            except elasticsearch.exceptions.NotFoundError:
                pass

        def convert_to_doc(self, articles):
            return [ArticleDocument(
                meta={'id': article.id},
                body=article.body, title=article.title,
                author={'nickname': article.author.username, 'id': article.author.id},
                category={'name': article.category.name, 'id': article.category.id},
                tags=[{'name': t.name, 'id': t.id} for t in article.tags.all()],
                pub_time=article.pub_time, status=article.status,
                comment_status=article.comment_status, type=article.type,
                views=article.views, article_order=article.article_order
            ) for article in articles]

        def rebuild(self, articles=None):
            ArticleDocument.init()
            articles = articles if articles else Article.objects.all()
            docs = self.convert_to_doc(articles)
            for doc in docs:
                doc.save()

        def update_docs(self, docs):
            for doc in docs:
                doc.save()

else:
    # ES not enabled — provide no-op stubs so importers don't crash
    class ElaspedTimeDocumentManager:
        @staticmethod
        def create(*args, **kwargs):
            pass

    class ArticleDocumentManager:
        pass
