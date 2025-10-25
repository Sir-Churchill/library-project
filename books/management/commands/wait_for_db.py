import time

from django.core.management import BaseCommand
from django.db import connections, OperationalError


class Command(BaseCommand):
    help = "Waits until database is available"

    def handle(self, *args, **options):
        self.stdout.write("Waiting until database is available")
        db_ready = False

        while not db_ready:
            try:
                conn = connections["default"]
                conn.cursor()
                db_ready = True
            except OperationalError:
                self.stdout.write("Database not available, waiting...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available"))
