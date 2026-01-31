from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, TemplateView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import FormDefinition, FormFieldDefinition, FormSubmission, FormAnswer, Visit, StockoutObservation, CatalogOption
# Import Core Models from Analytics
from analytics.models import Client, Pharmacy, Product, Rep, SalesDocument, SalesLine, CommercialAgreement
from analytics.services.prediction import ReorderPredictor

class FormListView(LoginRequiredMixin, ListView):
    model = FormDefinition
    template_name = "surveys/form_list.html"
    context_object_name = "forms"

    def get_queryset(self):
        # Filter filters by active and client.
        client = None
        if hasattr(self.request.user, 'rep_profile'):
            rep = self.request.user.rep_profile.first()
            if rep:
                client = rep.client
        
        if not client:
             client = Client.objects.first() 
        
        return FormDefinition.objects.filter(is_active=True, client=client)

class FormFillView(LoginRequiredMixin, TemplateView):
    template_name = "surveys/form_fill.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form_code = kwargs.get('code')
        form_def = FormDefinition.objects.filter(code=form_code, is_active=True).order_by('-version').first()
        if not form_def:
            pass # Handle 404
            
        context['form_def'] = form_def
        context['fields'] = form_def.fields.all().order_by('order')
        context['pharmacies'] = Pharmacy.objects.filter(is_active=True, client=form_def.client)[:50]
        
        return context

    def post(self, request, *args, **kwargs):
        form_code = kwargs.get('code')
        form_def = FormDefinition.objects.filter(code=form_code, is_active=True).order_by('-version').first()
        
        pharmacy_id = request.POST.get('pharmacy_id')
        pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id)
        
        with transaction.atomic():
            # 1. Create Visit
            visit = Visit.objects.create(
                client=form_def.client,
                rep=request.user.rep_profile.first() if hasattr(request.user, 'rep_profile') else None,
                pharmacy=pharmacy,
                started_at=timezone.now(),
                status='IN_PROGRESS'
            )

            # 2. Create Submission
            submission = FormSubmission.objects.create(
                visit=visit,
                form_definition=form_def
            )
            
            # Pre-fetch products for OOS logic
            oos_product_map = {}
            oos_skus = [f.code[4:] for f in form_def.fields.all() if f.code.startswith('OOS_')]
            if oos_skus:
                products = Product.objects.filter(client=form_def.client, sku__in=oos_skus)
                oos_product_map = {p.sku: p for p in products}

            # 3. Save Answers
            fields = form_def.fields.all()
            for field in fields:
                if field.field_type == 'SECTION_HEADER':
                    continue

                raw_value = request.POST.get(field.code)
                
                if field.field_type == 'BOOL':
                     raw_value = 'true' if raw_value == 'on' else 'false'
                
                if field.field_type == 'MULTI_SELECT':
                    raw_values = request.POST.getlist(field.code)
                    raw_value = ",".join(raw_values) if raw_values else None

                if raw_value is not None:
                     FormAnswer.objects.create(
                        submission=submission,
                        field_definition=field,
                        raw_value=raw_value
                    )
                     
                     # 4. Special Logic: Stockouts
                     if field.code.startswith('OOS_') and raw_value == 'true':
                         sku = field.code[4:]
                         product = oos_product_map.get(sku)
                         if product:
                             StockoutObservation.objects.create(
                                 visit=visit,
                                 product=product,
                                 is_oos=True,
                                 cluster_source='VISIT'
                             )
            
            visit.completed_at = timezone.now()
            visit.status = 'COMPLETED'
            visit.save()

        return redirect('surveys:form_list')

class SubmissionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = FormSubmission
    template_name = "surveys/submission_list.html"
    context_object_name = "submissions"
    ordering = ['-visit__completed_at']

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        return FormSubmission.objects.select_related('visit', 'visit__pharmacy', 'visit__rep__user', 'form_definition').order_by('-visit__completed_at')

class SubmissionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = FormSubmission
    template_name = "surveys/submission_detail.html"
    context_object_name = "submission"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['answers'] = (
            self.object.answers
            .select_related('field_definition', 'field_definition__catalog')
            .order_by('field_definition__order')
        )
        return context

class PharmacyContextView(LoginRequiredMixin, View):
    def get(self, request, pharmacy_id):
        pharmacy = get_object_or_404(Pharmacy, id=pharmacy_id)
        
        # Date Range: Last 30 Days (from start of day)
        end_date = timezone.now()
        start_date = (end_date - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Query Sales Documents
        docs = SalesDocument.objects.filter(
            pharmacy=pharmacy,
            date__range=(start_date, end_date)
        )
        
        # Aggregations
        orders_count = docs.count()
        total_sales = docs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Top Products (by quantity)
        top_products = (
            SalesLine.objects
            .filter(document__in=docs)
            .values('product__name')
            .annotate(qty=Sum('quantity'))
            .order_by('-qty')[:3]
        )
        
        # Agreement Data
        agreement = CommercialAgreement.objects.filter(
            pharmacy=pharmacy,
            is_active=True,
            end_date__gte=timezone.now().date()
        ).first()

        # Prediction (Local AI)
        predictor = ReorderPredictor(pharmacy.id)
        suggestions = predictor.get_suggestions()

        data = {
            'pharmacy_name': pharmacy.display_name,
            'orders_count': orders_count,
            'total_sales': float(total_sales),
            'top_products': list(top_products),
            'has_agreement': bool(agreement),
            'agreement_summary': agreement.description if agreement else "",
            'predictions': suggestions
        }
        
        return JsonResponse(data)
