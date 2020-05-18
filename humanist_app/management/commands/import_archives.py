from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
import os
from ...models import ArchiveEmail


class Command(BaseCommand):
    help = 'Imports Archived emails for searching'

    def add_arguments(self, parser):
        args = '<import_path import_path ...>'  # noqa
        parser.add_argument('import_path', nargs='+', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Clear before importing',)

    def handle(self, *args, **options):
        import_path = options['import_path'][0]
        file_types = ('.txt', '.html')
        exclude_list = ('index.html', 'subject.html', 'date.html')

        if options['delete']:
            ArchiveEmail.objects.all().delete()

        for root, directories, filenames in os.walk(import_path):
            for filename in filenames:
                if filename.endswith(file_types) and not filename.endswith(
                        exclude_list):
                    file_path = os.path.join(root, filename)

                    print("Importing: {}".format(file_path))

                    file_body = open(
                        file_path,
                        encoding="ascii",
                        errors="surrogateescape").read(
                    ).encode('utf8', 'surrogateescape')

                    if file_path.endswith('.html'):
                        # HTML - additional processing required
                        soup = BeautifulSoup(file_body)
                        file_body = soup.get_text()

                    archive_email = ArchiveEmail()
                    archive_email.filename = file_path
                    archive_email.body = file_body
                    archive_email.save()
