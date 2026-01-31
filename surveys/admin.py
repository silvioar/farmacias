from django.contrib import admin
from .models import (
    Catalog, CatalogOption, FormDefinition, FormFieldDefinition,
    Visit, FormSubmission, FormAnswer, EvidenceFile,
    PopType, PopPlacement, StockoutObservation
)

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

admin.site.register(EvidenceFile)
admin.site.register(PopType)
admin.site.register(PopPlacement)
admin.site.register(StockoutObservation)
