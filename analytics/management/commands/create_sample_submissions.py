
from django.core.management.base import BaseCommand
from analytics.models import Client, FormDefinition, FormSubmission, FormAnswer, Visit, Pharmacy, StockoutObservation, Product, Rep
from django.utils import timezone
from django.contrib.auth.models import User
import random

class Command(BaseCommand):
    help = 'Create sample submissions for existing forms'

    def handle(self, *args, **kwargs):
        client = Client.objects.first()
        admin_user = User.objects.filter(is_superuser=True).first()
        pharmacies = list(Pharmacy.objects.filter(client=client, is_active=True)[:10])
        reps = list(Rep.objects.filter(client=client)) # Get available reps
        
        if not pharmacies:
            self.stdout.write(self.style.ERROR("No pharmacies found. Run seed_demo_data first."))
            return
        
        if not reps:
             # Fallback if no reps exist (should not happen if seed_demo_data ran)
             # Create a dummy rep
             dummy_user, _ = User.objects.get_or_create(username="dummy_rep", defaults={'is_active': False})
             rep = Rep.objects.create(client=client, user=dummy_user, name="Dummy Rep", external_id="DUMMY")
             reps = [rep]

        forms = FormDefinition.objects.filter(is_active=True)
        
        for form_def in forms:
            self.stdout.write(f"Generating samples for: {form_def.title}")
            fields = list(form_def.fields.all())
            
            # Map for OOS products
            oos_product_map = {}
            if 'Full' in form_def.title:
                oos_skus = [f.code[4:] for f in fields if f.code.startswith('OOS_')]
                products = Product.objects.filter(client=client, sku__in=oos_skus)
                oos_product_map = {p.sku: p for p in products}

            for i in range(5): # 5 submissions per form
                pharmacy = random.choice(pharmacies)
                rep = random.choice(reps)
                
                # Create Visit
                visit = Visit.objects.create(
                    client=client,
                    pharmacy=pharmacy,
                    rep=rep,
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    status='COMPLETED'
                )
                
                # Create Submission
                submission = FormSubmission.objects.create(
                    visit=visit,
                    form_definition=form_def
                )

                # Answers
                for field in fields:
                    if field.field_type == 'SECTION_HEADER':
                        continue
                    
                    val = None
                    if field.field_type == 'BOOL':
                        val = 'true' if random.choice([True, False]) else 'false'
                    elif field.field_type == 'INT':
                        val = str(random.randint(0, 10))
                    elif field.field_type == 'TEXT':
                        val = f"Comentario de prueba {random.randint(100,999)}"
                    elif field.field_type == 'SELECT':
                        if field.catalog and field.catalog.options.exists():
                           val = field.catalog.options.first().code
                    elif field.field_type == 'MULTI_SELECT':
                        if field.catalog and field.catalog.options.exists():
                           val = field.catalog.options.first().code
                    
                    if val:
                        FormAnswer.objects.create(
                            submission=submission,
                            field_definition=field,
                            raw_value=val
                        )

                        # OOS Logic for Seed
                        if field.code.startswith('OOS_') and val == 'true':
                             sku = field.code[4:]
                             product = oos_product_map.get(sku)
                             if product:
                                 StockoutObservation.objects.create(
                                     visit=visit,
                                     product=product,
                                     is_oos=True,
                                     cluster_source='VISIT'
                                 )
        
        self.stdout.write(self.style.SUCCESS('Successfully generated sample submissions.'))
