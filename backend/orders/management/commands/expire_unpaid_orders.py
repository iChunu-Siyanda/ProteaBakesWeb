from django.core.management.base import BaseCommand

from orders.services import expire_unpaid_orders


class Command(BaseCommand):
    help = (
        "Cancel PENDING orders that were never paid and release their stock. "
        "Run every few minutes from cron / a scheduler."
    )

    def handle(self, *args, **options):
        count = expire_unpaid_orders()
        self.stdout.write(self.style.SUCCESS(f"Cancelled {count} unpaid order(s)."))
