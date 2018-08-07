from django.core.management.base import BaseCommand
import MySQLdb as mysql
import csv


class Command(BaseCommand):
    help = 'Creates a CSV of users'

    def handle(self, *args, **options):

        # Note - these credentials are only valid for the local
        # development environment
        db_host = '127.0.0.1'
        db_user = 'root'
        db_pass = 'humanist'
        db_name = 'humanist_users'
        db_table = 'active_members'

        # NEVER make this file public - it should remain local
        # at all times
        filename = 'private_data/users.csv'

        # Open database connection
        db = mysql.connect(db_host, db_user, db_pass, db_name)
        c = db.cursor()

        # Query!
        c.execute('select * from {}'.format(db_table))
        users = c.fetchall()

        db_count = len(users)
        print('Found {} users.'.format(db_count))

        # Open our CSV:
        with open(filename, 'w') as csvfile:
            fw = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)

            # Headers
            fw.writerow(['firstname', 'initial', 'surname',
                         'email', 'mailmanpass', 'bio'])

            '''
            Fields we are interested in
            0: first name
            1: initial??
            2: surname
            3: email
            4: mailman generated pass
            5: bio
            '''
            for u in users:
                fw.writerow(u[0:6])
        # disconnect from server
        db.close()

        # Verify CSV length:
        with open(filename, 'rt') as csvfile:
            fr = csv.reader(csvfile, delimiter=',', quotechar='|')

            csv_count = sum(1 for row in fr) - 1

            if db_count == csv_count:
                print('CSV count matches database count!')
            else:
                print('###################################')
                print('# WARNING!!!!')
                print('# CSV COUNT AND DATABASE COUNT')
                print('# DO NOT MATCH!')
                print('# CSV: {}, DB: {}'.format(csv_count, db_count))
                print('###################################')
