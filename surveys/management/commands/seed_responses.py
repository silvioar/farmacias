import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from surveys.models import FormDefinition, Visit, FormSubmission, FormAnswer, FormFieldDefinition
from analytics.models import Client, Rep, Pharmacy

class Command(BaseCommand):
    help = 'Seeds 10 responses for the Primera Visita form'

    def handle(self, *args, **options):
        # 1. Get Setup Data
        client = Client.objects.first()
        if not client:
            self.stdout.write(self.style.ERROR("No Client found. Run seed_primera_visita first."))
            return

        form_code = "PRIMERA_VISITA_V1"
        try:
            form_def = FormDefinition.objects.get(client=client, code=form_code, is_active=True)
        except FormDefinition.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Form {form_code} not found. Run seed_primera_visita first."))
            return

        pharmacies = list(Pharmacy.objects.filter(client=client))
        if not pharmacies:
            self.stdout.write(self.style.ERROR("No Pharmacies found."))
            return

        # 2. Get or Create 10 Reps
        reps = []
        for i in range(1, 11):
            username = f"rep_demo_{i}"
            user, created = User.objects.get_or_create(username=username, defaults={
                'email': f"{username}@example.com",
                'first_name': f"Rep {i}",
                'last_name': "Demo"
            })
            if created:
                user.set_password("demo123")
                user.save()
            
            rep, _ = Rep.objects.get_or_create(client=client, user=user)
            reps.append(rep)
        
        self.stdout.write(f"Ensured {len(reps)} reps exist.")

        # 3. Create Submissions
        fields = FormFieldDefinition.objects.filter(form=form_def)
        
        for i in range(10):
            rep = reps[i] # One unique rep per submission
            pharmacy = random.choice(pharmacies)
            
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            visit_date = timezone.now() - timedelta(days=days_ago)

            # Create Visit
            visit = Visit.objects.create(
                client=client,
                rep=rep,
                pharmacy=pharmacy,
                status='SUBMITTED',
                scheduled_at=visit_date,
                started_at=visit_date,
                completed_at=visit_date + timedelta(minutes=random.randint(15, 60)),
                distance_from_target=random.randint(0, 50)
            )

            # Create Submission
            submission = FormSubmission.objects.create(
                visit=visit,
                form_definition=form_def,
                submitted_at=visit.completed_at
            )

            # Create Answers
            for field in fields:
                if field.field_type == 'SECTION_HEADER':
                    continue
                
                # Logic to generate random but plausible answers
                if field.field_type == 'BOOL':
                    val = random.choice([True, False])
                    FormAnswer.objects.create(submission=submission, field_definition=field, value_bool=val, raw_value="Sí" if val else "No")
                
                elif field.field_type == 'INT':
                    val = random.randint(0, 20)
                    FormAnswer.objects.create(submission=submission, field_definition=field, value_int=val, raw_value=str(val))
                
                elif field.field_type == 'MULTI_SELECT':
                    if field.catalog:
                        options = list(field.catalog.options.all())
                        if options:
                            selected = random.sample(options, k=random.randint(1, len(options)))
                            ans = FormAnswer.objects.create(submission=submission, field_definition=field, raw_value=", ".join([o.label for o in selected]))
                            ans.value_catalog_options.set(selected)

                elif field.field_type == 'TEXT_AREA':
                    comments = [
                        "Todo en orden.",
                        "Falta stock de solares.",
                        "Farmacia con alta rotación.",
                        "El encargado no estaba.",
                        "Exhibición impecable.",
                        "Material POP colocado correctamente."
                    ]
                    val = random.choice(comments)
                    FormAnswer.objects.create(submission=submission, field_definition=field, value_text=val, raw_value=val)
                
                # ... Add other types if needed, but this covers most of the form

            self.stdout.write(f"Created submission for {rep} at {pharmacy}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded 10 responses."))
