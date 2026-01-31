import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from surveys.models import FormDefinition, FormFieldDefinition, FormSubmission, FormAnswer, Visit, StockoutObservation, CatalogOption
from analytics.models import Client, Pharmacy, Product, Rep
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Seeds 10 random answers for the Primera Visita form'

    def handle(self, *args, **options):
        form_code = "PRIMERA_VISITA_V1"
        form_def = FormDefinition.objects.filter(code=form_code, is_active=True).first()
        
        if not form_def:
            self.stdout.write(self.style.ERROR(f"Form {form_code} not found. Run seed_primera_visita first."))
            return

        client = form_def.client
        pharmacies = list(Pharmacy.objects.filter(client=client))
        if not pharmacies:
             self.stdout.write(self.style.ERROR("No pharmacies found."))
             return

        # Ensure a Rep exists
        user, _ = User.objects.get_or_create(username="demo_rep", defaults={'is_staff': True})
        rep, _ = Rep.objects.get_or_create(client=client, external_id="REP_DEMO", defaults={'user': user})

        # Pre-fetch products for OOS logic
        oos_skus = [f.code[4:] for f in form_def.fields.all() if f.code.startswith('OOS_')]
        oos_product_map = {}
        if oos_skus:
             products = Product.objects.filter(client=client, sku__in=oos_skus)
             oos_product_map = {p.sku: p for p in products}

        self.stdout.write(f"Seeding 10 submissions for {form_def.title}...")

        fields = form_def.fields.all().order_by('order')

        for i in range(10):
            pharmacy = random.choice(pharmacies)
            # Random date in last 7 days
            visit_date = timezone.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))

            visit = Visit.objects.create(
                client=client,
                rep=rep,
                pharmacy=pharmacy,
                started_at=visit_date,
                completed_at=visit_date + timedelta(minutes=random.randint(15, 45)),
                status='COMPLETED'
            )

            submission = FormSubmission.objects.create(
                visit=visit,
                form_definition=form_def,
                submitted_at=visit.completed_at
            )

            for field in fields:
                if field.field_type == 'SECTION_HEADER':
                    continue

                answer = FormAnswer(submission=submission, field_definition=field)
                val_raw = None

                # Generate Random Values
                if field.field_type == 'BOOL':
                    val = random.choice([True, False])
                    answer.value_bool = val
                    val_raw = "true" if val else "false"
                    
                    # Logic for Stockouts
                    if field.code.startswith('OOS_') and val:
                        sku = field.code[4:]
                        product = oos_product_map.get(sku)
                        if product:
                            StockoutObservation.objects.create(
                                visit=visit,
                                product=product,
                                is_oos=True,
                                cluster_source='VISIT'
                            )

                elif field.field_type == 'INT':
                    val = random.randint(0, 20)
                    answer.value_int = val
                    val_raw = str(val)

                elif field.field_type == 'TEXT_AREA':
                    val = random.choice(["Todo en orden", "Falta material", "Muy buena exhibición", "Sin novedades"])
                    answer.value_text = val
                    val_raw = val

                elif field.field_type == 'MULTI_SELECT':
                    if field.catalog:
                        options = list(field.catalog.options.all())
                        if options:
                            selected = random.sample(options, k=random.randint(0, len(options)))
                            # We can't set M2M until saved, handle below
                            val_raw = ",".join([o.label for o in selected])

                elif field.field_type == 'PHOTO':
                    val_raw = "[FOTO_SIMULADA.jpg]"

                if val_raw is not None:
                    answer.raw_value = val_raw
                    answer.save()
                    
                    # Post-save M2M
                    if field.field_type == 'MULTI_SELECT' and field.catalog:
                         options = list(field.catalog.options.all())
                         if options and val_raw:
                             # Re-select based on label match from the random sample above?
                             # Or just re-select random to keep it simple as we just need data
                             # We already picked 'selected' above but lost scope. Let's just pick again.
                             pass # Ideally we set answer.value_catalog_options.set(selected) but scope is tricky. 
                             # Simpler:
                             if options:
                                selected = random.sample(options, k=random.randint(1, min(3, len(options))))
                                answer.value_catalog_options.set(selected)
                                answer.raw_value = ",".join([o.label for o in selected])
                                answer.save()

            self.stdout.write(f" - Created submission {i+1} for {pharmacy.display_name}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded 10 answers."))
