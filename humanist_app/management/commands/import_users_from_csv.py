from django.core.management.base import BaseCommand
import csv
from django.contrib.auth.models import User
from ...models import Subscriber


class Command(BaseCommand):
    help = 'Creates a CSV of users'

    def handle(self, *args, **options):

        # NEVER make this file public - it should remain local
        # at all times
        filename = 'private_data/users.csv'

        # open CSV:
        with open(filename, 'rt') as csvfile:
            fr = csv.reader(csvfile, delimiter=',', quotechar='|')

            next(fr)  # Skip headers

            '''
            Fields we are interested in
            0: first name
            1: initial??
            2: surname
            3: email
            4: mailman generated pass
            5: bio
            '''
            count = 0
            skip = 0

            for u in fr:

                user_email = u[3]
                if '\n' in user_email:
                    user_email = user_email.split('\n')[0]

                if User.objects.filter(email=user_email).count():
                    print(
                        ' - Skipping user: {} ({})'.format(
                            user_email, count + skip))
                    skip = skip + 1
                else:
                    count = count + 1
                    print(
                        ' - Importing user: {} ({})'.format(
                            user_email, count + skip))

                    user = User()
                    user.first_name = u[0]
                    user.last_name = u[2]
                    user.email = user_email
                    user.username = user_email
                    user.set_password(u[4])
                    user.is_active = True
                    user.save()

                    sub = Subscriber()
                    sub.user = user
                    sub.bio = u[5]
                    sub.save()

            print('###################################')
            print('{} Users imported'.format(count))
            print('{} Users skipped'.format(skip))
            print('###################################')
