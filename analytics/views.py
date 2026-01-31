from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth, ExtractMonth
from django.utils import timezone
from .models import Pharmacy, SalesDocument, SalesLine, Product, Zone, Client
from surveys.models import Visit, StockoutObservation, FormDefinition, FormFieldDefinition, FormSubmission, FormAnswer

import csv
from django.http import HttpResponse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, CustomUserUpdateForm
from django.contrib.auth.models import User

class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/home.html"

class UserCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    form_class = CustomUserCreationForm
    template_name = "analytics/user_form.html"
    success_url = reverse_lazy('analytics:user_list')

class UserListView(LoginRequiredMixin, SuperUserRequiredMixin, ListView):
    model = User
    template_name = "analytics/user_list.html"
    context_object_name = "users"

class UserUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserUpdateForm
    template_name = "analytics/user_form.html"
    success_url = reverse_lazy('analytics:user_list')

class OrderMasterListView(LoginRequiredMixin, ListView):
    model = SalesLine
    template_name = "analytics/order_master_list.html"
    paginate_by = 50
    
    def get_queryset(self):
        qs = SalesLine.objects.select_related(
            'document', 'document__pharmacy', 'document__pharmacy__territory__zone',
            'product', 'product__category'
        ).order_by('-document__date')
        
        # Filtering
        source_ids = self.request.GET.getlist('source')
        combo_names = self.request.GET.getlist('combo')
        ret_statuses = self.request.GET.getlist('ret_status')
        zone_ids = self.request.GET.getlist('zone')
        
        # Clean empty strings
        source_ids = [s for s in source_ids if s]
        combo_names = [c for c in combo_names if c]
        ret_statuses = [r for r in ret_statuses if r]
        zone_ids = [z for z in zone_ids if z]

        if source_ids:
            qs = qs.filter(document__order_source__in=source_ids)
        if combo_names:
            if 'NULL' in combo_names:
                # If filtering "Sin Combo" (NULL) and other combos
                valid_combos = [c for c in combo_names if c != 'NULL']
                if valid_combos:
                    qs = qs.filter(Q(combo_name="") | Q(combo_name__in=valid_combos))
                else:
                    qs = qs.filter(combo_name="")
            else:
                qs = qs.filter(combo_name__in=combo_names)
        if ret_statuses:
            qs = qs.filter(return_status__in=ret_statuses)
        if zone_ids:
            qs = qs.filter(document__pharmacy__territory__zone_id__in=zone_ids)
            
        date_start = self.request.GET.get('date_start')
        date_end = self.request.GET.get('date_end')

        if date_start:
            qs = qs.filter(document__date__date__gte=date_start)
        if date_end:
            qs = qs.filter(document__date__date__lte=date_end)
            
        return qs

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def export_csv(self):
        queryset = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reporte_detallado.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Pedido ID', 'Fecha', 'Origen', 'Estado', 'Farmacia', 'Zona', 'SKU', 'Producto', 'Categoría', 'Cant', 'Combo', 'Cupón', 'Desc.', 'Retorno'])
        
        for line in queryset:
            writer.writerow([
                line.document.external_id,
                line.document.date.strftime("%d/%m/%Y %H:%M"),
                line.document.order_source or "-",
                line.document.status,
                line.document.pharmacy.display_name,
                line.document.pharmacy.territory.zone.name if line.document.pharmacy.territory and line.document.pharmacy.territory.zone else "-",
                line.product.sku,
                line.product.name,
                line.product.category.name if line.product.category else "-",
                line.quantity,
                line.combo_name or "-",
                line.document.coupon_code or "-",
                f"-${line.discount_coupon_amount:.0f}" if line.discount_coupon_amount > 0 else "-",
                line.get_return_status_display()
            ])
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Context for filters
        context['sources'] = SalesDocument.objects.values_list('order_source', flat=True).distinct().order_by('order_source')
        context['combos'] = SalesLine.objects.exclude(combo_name="").values_list('combo_name', flat=True).distinct().order_by('combo_name')
        context['return_statuses'] = SalesLine.RETURN_STATUS
        # Need to import Zone if not already imported, or use values
        context['zones'] = Pharmacy.objects.values_list('territory__zone__name', 'territory__zone__id').distinct().order_by('territory__zone__name')
        
        # Pass selected values for UI
        context['selected_sources'] = self.request.GET.getlist('source')
        context['selected_combos'] = self.request.GET.getlist('combo')
        context['selected_ret_statuses'] = self.request.GET.getlist('ret_status')
        context['selected_zones'] = self.request.GET.getlist('zone')
        
        # Preserve filters in pagination
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        if 'export' in query_params:
            del query_params['export']
        context['current_url_params'] = query_params.urlencode()
        
        return context

class DashboardContextMixin:
    """Mixin to handle common dashboard filtering and initial context."""
    def get_dashboard_context(self, request):
        # --- Filters ---
        pharmacy_ids = request.GET.getlist('pharmacy')
        zone_ids = request.GET.getlist('zone')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')

        # Base QuerySets
        sales_qs = SalesDocument.objects.all()
        visit_qs = Visit.objects.all()
        oos_qs = StockoutObservation.objects.all()
        
        # Filter out empty strings if any
        pharmacy_ids = [pid for pid in pharmacy_ids if pid]
        zone_ids = [zid for zid in zone_ids if zid]

        if pharmacy_ids:
            sales_qs = sales_qs.filter(pharmacy_id__in=pharmacy_ids)
            visit_qs = visit_qs.filter(pharmacy_id__in=pharmacy_ids)
            oos_qs = oos_qs.filter(visit__pharmacy_id__in=pharmacy_ids)
        
        if zone_ids:
            sales_qs = sales_qs.filter(pharmacy__territory__zone_id__in=zone_ids)
            visit_qs = visit_qs.filter(pharmacy__territory__zone_id__in=zone_ids)
            oos_qs = oos_qs.filter(visit__pharmacy__territory__zone_id__in=zone_ids)
            
        if date_start:
            sales_qs = sales_qs.filter(date__date__gte=date_start)
            visit_qs = visit_qs.filter(started_at__date__gte=date_start)
            oos_qs = oos_qs.filter(visit__started_at__date__gte=date_start)
            
        if date_end:
            sales_qs = sales_qs.filter(date__date__lte=date_end)
            visit_qs = visit_qs.filter(started_at__date__lte=date_end)
            oos_qs = oos_qs.filter(visit__started_at__date__lte=date_end)

        return {
            'sales_qs': sales_qs,
            'visit_qs': visit_qs,
            'oos_qs': oos_qs,
            'filter_zones': Pharmacy.objects.values_list('territory__zone__name', 'territory__zone__id').distinct().exclude(territory__zone__isnull=True).order_by('territory__zone__name'),
            'filter_pharmacies': Pharmacy.objects.values_list('display_name', 'id').order_by('display_name'),
            'selected_zones': zone_ids,
            'selected_pharmacies': pharmacy_ids,
        }

class DashboardView(LoginRequiredMixin, TemplateView, DashboardContextMixin):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_dashboard_context(self.request)
        
        sales_qs = data['sales_qs']
        visit_qs = data['visit_qs']
        oos_qs = data['oos_qs']

        # --- KPIs Globales ---
        context.update({
            'kpi_total_sales': sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0,
            'kpi_pharmacies': sales_qs.values('pharmacy_id').distinct().count(),
            'kpi_visits': visit_qs.count(),
            'kpi_oos': oos_qs.count(),
            'filter_zones': data['filter_zones'],
            'filter_pharmacies': data['filter_pharmacies'],
            'selected_zones': data['selected_zones'],
            'selected_pharmacies': data['selected_pharmacies'],
        })

        # --- Top Farmacias (General View) ---
        context['top_pharmacies'] = sales_qs.values(
            'pharmacy__display_name', 'pharmacy__segment_data'
        ).annotate(
            total_sales=Sum('total_amount'),
            ticket_count=Count('id')
        ).order_by('-total_sales')[:10]
        
        return context

class SalesDashboardView(LoginRequiredMixin, TemplateView, DashboardContextMixin):
    template_name = "analytics/dashboard_sales.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_dashboard_context(self.request)
        sales_qs = data['sales_qs']
        line_qs = SalesLine.objects.filter(document__in=sales_qs)

        # --- Gráfico 1: Facturación Mensual ---
        sales_by_month = sales_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('total_amount')).order_by('month')
        
        # --- Gráfico 2: Cantidad de Pedidos por Zona ---
        orders_by_zone = sales_qs.values('pharmacy__territory__zone__name').annotate(count=Count('id')).order_by('-count')
        
        # --- Gráfico 3: Top Combos ---
        top_combos = line_qs.exclude(combo_name="").values('combo_name').annotate(units=Sum('quantity')).order_by('-units')[:5]
        
        # --- Gráfico 4: Origen de Pedidos ---
        sales_by_source = sales_qs.values('order_source').annotate(count=Count('id')).order_by('-count')

        context.update({
            'sales_months': [s['month'].strftime('%Y-%m') for s in sales_by_month if s['month']],
            'sales_values': [float(s['total']) for s in sales_by_month if s['month']],
            'zone_labels': [z['pharmacy__territory__zone__name'] or 'Sin Zona' for z in orders_by_zone],
            'zone_values': [z['count'] for z in orders_by_zone],
            'combo_labels': [c['combo_name'] for c in top_combos],
            'combo_values': [c['units'] for c in top_combos],
            'source_labels': [s['order_source'] for s in sales_by_source],
            'source_values': [s['count'] for s in sales_by_source],
            'filter_zones': data['filter_zones'],
            'filter_pharmacies': data['filter_pharmacies'],
            'selected_zones': data['selected_zones'],
            'selected_pharmacies': data['selected_pharmacies'],
        })
        return context

class OpsDashboardView(LoginRequiredMixin, TemplateView, DashboardContextMixin):
    template_name = "analytics/dashboard_ops.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.get_dashboard_context(self.request)
        visit_qs = data['visit_qs']
        oos_qs = data['oos_qs']

        # --- Gráfico 1: Visitas por Zona ---
        visits_by_zone = visit_qs.values('pharmacy__territory__zone__name').annotate(count=Count('id')).order_by('-count')
        
        # --- Gráfico 2: Quiebres por Fuente (OOS) ---
        oos_by_source = oos_qs.values('cluster_source').annotate(count=Count('id')).order_by('-count')

        context.update({
             # KPIs Específicos Ops
            'kpi_visits': visit_qs.count(),
            'kpi_oos': oos_qs.count(),
            'kpi_visit_duration': 0, # Mocked until calculated field added
            
            'visits_zone_labels': [z['pharmacy__territory__zone__name'] or 'Sin Zona' for z in visits_by_zone],
            'visits_zone_values': [z['count'] for z in visits_by_zone],
            'oos_source_labels': [o['cluster_source'] for o in oos_by_source],
            'oos_source_values': [o['count'] for o in oos_by_source],
            'filter_zones': data['filter_zones'],
            'filter_pharmacies': data['filter_pharmacies'],
            'selected_zones': data['selected_zones'],
            'selected_pharmacies': data['selected_pharmacies'],
        })
        return context

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/profile.html"

class PharmacyListView(LoginRequiredMixin, ListView):
    model = Pharmacy
    template_name = "analytics/pharmacy_list.html"
    context_object_name = "pharmacies"
    paginate_by = 20
    
    def get_queryset(self):
        qs = Pharmacy.objects.all().order_by('-created_at')
        zone_ids = self.request.GET.getlist('zone')
        status_ids = self.request.GET.getlist('status')
        segment_ids = self.request.GET.getlist('segment')
        
        zone_ids = [z for z in zone_ids if z]
        status_ids = [s for s in status_ids if s]
        segment_ids = [s for s in segment_ids if s]

        if zone_ids:
            qs = qs.filter(territory__zone_id__in=zone_ids)
        if status_ids:
            # Map ACTIVE/INACTIVE to True/False
            is_active_vals = [True if s == 'ACTIVE' else False for s in status_ids]
            qs = qs.filter(is_active__in=is_active_vals)
        if segment_ids:
             qs = qs.filter(segment_data__cluster__in=segment_ids)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zones'] = Pharmacy.objects.values_list('territory__zone__name', 'territory__zone__id').distinct().exclude(territory__zone__isnull=True).order_by('territory__zone__name')
        context['statuses'] = ['ACTIVE', 'INACTIVE']
        context['segments'] = ['A', 'B', 'C']
        
        context['selected_zones'] = self.request.GET.getlist('zone')
        context['selected_statuses'] = self.request.GET.getlist('status')
        context['selected_segments'] = self.request.GET.getlist('segment')
        return context

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "analytics/product_list.html"
    context_object_name = "products"
    paginate_by = 20
    
    def get_queryset(self):
        qs = Product.objects.select_related('category', 'brand').all().order_by('name')
        cat_ids = self.request.GET.getlist('category')
        brand_ids = self.request.GET.getlist('brand')
        
        cat_ids = [c for c in cat_ids if c]
        brand_ids = [b for b in brand_ids if b]
        
        if cat_ids:
            qs = qs.filter(category_id__in=cat_ids)
        if brand_ids:
            qs = qs.filter(brand_id__in=brand_ids)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Product.objects.values_list('category__name', 'category__id').distinct().order_by('category__name')
        context['brands'] = Product.objects.values_list('brand__name', 'brand__id').distinct().order_by('brand__name')
        
        context['selected_categories'] = self.request.GET.getlist('category')
        context['selected_brands'] = self.request.GET.getlist('brand')
        return context

# Form Views moved to surveys app.

