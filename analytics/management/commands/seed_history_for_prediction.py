from django.core.management.base import BaseCommand
from analytics.models import Pharmacy, SalesDocument, SalesLine, Product, Client
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds historical sales to trigger AI prediction for Farmacia Azul Belgrano'

    def handle(self, *args, **kwargs):
        # 1. Setup Context
        try:
            pharmacy = Pharmacy.objects.get(display_name__icontains="Azul Belgrano", is_active=True)
            # Find a target product (e.g., one of the Biodermas)
            product = Product.objects.filter(name__icontains="Photoderm").first()
            if not product:
                self.stdout.write(self.style.ERROR("Product not found"))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            return

        client = pharmacy.client
        
        # 2. Simulate a Buying Cycle (Every 15 days)
        # We want to create orders at T-60, T-45, T-30.
        # So the last order was 30 days ago.
        # Average cycle = 15 days.
        # Days since last = 30.
        # Threshold = 15 * 1.2 = 18.
        # 30 > 18 -> TRIGGER!

        dates = [60, 45, 30]
        
        for days_ago in dates:
            date = timezone.now() - timedelta(days=days_ago)
            ext_id = f"HIST-{days_ago}"
            
            doc, _ = SalesDocument.objects.get_or_create(
                pharmacy=pharmacy,
                external_id=ext_id,
                defaults={
                    'client': client,
                    'date': date,
                    'status': 'COMPLETED',
                    'total_amount': Decimal('50000.00'),
                    'doc_type': 'TICKET'
                }
            )
            
            SalesLine.objects.get_or_create(
                document=doc,
                product=product,
                defaults={
                    'quantity': 20,
                    'unit_price': Decimal('2500.00'),
                    'total_price': Decimal('50000.00')
                }
            )
            
        self.stdout.write(self.style.SUCCESS(f"Seeded 3 historical orders for {product.name}. Last order was 30 days ago (Cycle ~15 days). Prediction should trigger."))
