from django.contrib import admin
from .models import (
    Client, AuditLog, Region, Zone, Territory, Rep, Pharmacy, 
    ProductBrand, ProductCategory, Product,
    Catalog, CatalogOption, FormDefinition, FormFieldDefinition,
    Visit, FormSubmission, FormAnswer, EvidenceFile,
    PopType, PopPlacement, StockoutObservation,
    SalesDocument, SalesLine
)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('model_name', 'action', 'timestamp')

@admin.register(Rep)
class RepAdmin(admin.ModelAdmin):
    list_display = ('user', 'external_id', 'client', 'territory')
    search_fields = ('user__username', 'external_id')
    list_filter = ('client',)

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name', 'client', 'city', 'state', 'is_active')
    search_fields = ('code', 'name_legal', 'name_trade')
    list_filter = ('client', 'state', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'brand', 'category', 'client')
    search_fields = ('sku', 'name')
    list_filter = ('client', 'brand', 'category')

class FormFieldInline(admin.TabularInline):
    model = FormFieldDefinition
    extra = 1

@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'version', 'client', 'is_active')
    list_filter = ('client', 'is_active')
    inlines = [FormFieldInline]

class CatalogOptionInline(admin.TabularInline):
    model = CatalogOption
    extra = 1

@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'client')
    inlines = [CatalogOptionInline]

class FormAnswerInline(admin.TabularInline):
    model = FormAnswer
    extra = 0
    readonly_fields = ('raw_value',)

@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('visit', 'form_definition', 'submitted_at', 'is_valid')
    inlines = [FormAnswerInline]

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'rep', 'pharmacy', 'status', 'scheduled_at', 'started_at')
    list_filter = ('status', 'client')
    search_fields = ('pharmacy__name_trade', 'rep__user__username')

# Register others simply
admin.site.register(Region)
admin.site.register(Zone)
admin.site.register(Territory)
admin.site.register(ProductBrand)
admin.site.register(ProductCategory)
admin.site.register(EvidenceFile)
admin.site.register(PopType)
admin.site.register(PopPlacement)
admin.site.register(StockoutObservation)
admin.site.register(SalesDocument)
admin.site.register(SalesLine)
