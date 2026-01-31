from django.contrib import admin
from .models import (
    Client, AuditLog, Region, Zone, Territory, Rep, Pharmacy, 
    ProductBrand, ProductCategory, Product,
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

# Register others simply
admin.site.register(Region)
admin.site.register(Zone)
admin.site.register(Territory)
admin.site.register(ProductBrand)
admin.site.register(ProductCategory)
admin.site.register(SalesDocument)
admin.site.register(SalesLine)
