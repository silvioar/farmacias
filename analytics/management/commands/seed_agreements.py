from django.core.management.base import BaseCommand
from analytics.models import Pharmacy, CommercialAgreement, Client
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seeds Commercial Agreements for ALL active Pharmacies'

    def handle(self, *args, **kwargs):
        pharmacies = Pharmacy.objects.filter(is_active=True)
        count_created = 0
        count_updated = 0

        self.stdout.write(f"Found {pharmacies.count()} active pharmacies. Starting seeding...")

        import random
        
        # Product lines and benefits for randomization
        lines = ["Solar", "Facial", "Capilar", "Corporal", "Bebé"]
        products = ["Photoderm", "Sensibio", "Hydrabio", "Sebium", "Atoderm"]
        benefits = [
            "Material POP bonificado",
            "Capacitación trimestral para el staff",
            "Eventos de dermoconsejería mensual",
            "Muestras gratis (sachets) x500 u/mes",
            "Tester de mostrador bonificado"
        ]
        
        self.stdout.write(f"Found {pharmacies.count()} active pharmacies. Starting seeding...")

        for pharmacy in pharmacies:
             # Default Client (fallback)
            client = pharmacy.client
            
            # Start dates randomized slightly to look realistic
            days_ago = random.randint(10, 60)
            start_date = timezone.now().date() - timedelta(days=days_ago)
            end_date = timezone.now().date() + timedelta(days=365)
            
            # Randomize Terms
            line_bonus = random.choice(lines)
            product_stock = random.choice(products)
            bonus_pct = random.choice([5, 8, 10, 12, 15])
            stock_min = random.choice([20, 30, 50, 80, 100])
            
            # Random Benefis (Pick 2)
            selected_benefits = random.sample(benefits, 2)
            
            description = f"""
            **Acuerdo Comercial: {pharmacy.display_name}**
            
            **Condiciones:**
            1. Exhibición preferencial en mostrador principal.
            2. Bonificación del {bonus_pct}% en línea {line_bonus}.
            3. Stock mínimo de {stock_min} unidades de {product_stock}.

            **Beneficios:**
            - {selected_benefits[0]}.
            - {selected_benefits[1]}.
            """

            agreement, created = CommercialAgreement.objects.get_or_create(
                pharmacy=pharmacy,
                defaults={
                    'client': client,
                    'start_date': start_date,
                    'end_date': end_date,
                    'description': description.strip(),
                    'is_active': True
                }
            )

            if not created:
                agreement.start_date = start_date
                agreement.end_date = end_date
                agreement.description = description.strip()
                agreement.is_active = True
                agreement.save()
                count_updated += 1
            else:
                count_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed agreements. Created: {count_created}, Updated: {count_updated}"))
