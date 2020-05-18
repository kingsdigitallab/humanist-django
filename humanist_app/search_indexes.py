from haystack import indexes
from .models import ArchiveEmail, Edition


class ArchiveEmailIndex(indexes.SearchIndex, indexes.Indexable):
    url = indexes.CharField(indexed=False)
    title = indexes.CharField(indexed=False)
    text = indexes.CharField(document=True, use_template=True, null=True)

    def get_model(self):
        return ArchiveEmail

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare_url(self, obj):
        return "/{}".format(obj.url)

    def prepare_title(self, obj):
        return ' '.join(obj.url.split('/')[1:])


class EditionIndex(indexes.SearchIndex, indexes.Indexable):
    url = indexes.CharField(indexed=False)
    text = indexes.CharField(document=True, use_template=True, null=True)
    title = indexes.CharField(indexed=False)

    def get_model(self):
        return Edition

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(sent=True)

    def prepare_url(self, obj):
        return '/volume/{}/{}'.format(obj.volume, obj.issue)

    def prepare_title(self, obj):
        return obj.subject
