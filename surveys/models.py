import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from analytics.models import Client, Rep, Pharmacy, Product, Territory  # Importing from Analytics

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

# ==========================================
# 1. DYNAMIC FORMS ENGINE
# ==========================================

class Catalog(models.Model):
    """
    Lists of options for Select/MultiSelect fields (e.g., 'Motivos de Rechazo', 'Marcas Competencia').
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50) # e.g. "REJECTION_REASONS"
    
    class Meta:
        unique_together = ('client', 'code')

    def __str__(self):
        return self.name

class CatalogOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="options")
    code = models.CharField(max_length=50) # Value stored in DB
    label = models.CharField(max_length=200) # Display value
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'label']

    def __str__(self):
        return self.label

class FormDefinition(models.Model):
    """
    Versioned definition of a form (Survey/Checklist).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50) # e.g. "VISIT_FORM_V1"
    version = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    
    # Configuration
    allow_photos = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('client', 'code', 'version')

    def __str__(self):
        return f"{self.title} v{self.version}"

class FormFieldDefinition(models.Model):
    """
    Single field within a form (Question).
    """
    FIELD_TYPES = (
        ('TEXT', 'Texto Libre'),
        ('INT', 'Número Entero'),
        ('DECIMAL', 'Decimal'),
        ('BOOL', 'Sí/No'),
        ('DATE', 'Fecha'),
        ('SELECT', 'Selección Única'),
        ('MULTI_SELECT', 'Selección Múltiple'),
        ('PHOTO', 'Foto'),
        ('SECTION_HEADER', 'Encabezado de Sección'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(FormDefinition, on_delete=models.CASCADE, related_name="fields")
    order = models.IntegerField(default=0)
    
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    label = models.CharField(max_length=300)
    code = models.CharField(max_length=50, help_text="Internal slug for reporting")
    
    required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=200, blank=True)
    
    # Logic & Data
    catalog = models.ForeignKey(Catalog, on_delete=models.SET_NULL, null=True, blank=True, help_text="For select fields")
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Visibility Logic
    conditions = JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order']
        unique_together = ('form', 'code')

    def __str__(self):
        return f"{self.label} ({self.field_type})"

# ==========================================
# 2. EXECUTION (Visits & Answers)
# ==========================================

class Visit(models.Model):
    """
    Core Execution Entity. A Rep goes to a Pharmacy.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Borrador'),
        ('SUBMITTED', 'Enviado'),
        ('VALIDATED', 'Validado'),
        ('REJECTED', 'Rechazado'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    rep = models.ForeignKey(Rep, on_delete=models.CASCADE)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Timestamps
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Geo
    latitude_check_in = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_check_in = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_from_target = models.IntegerField(help_text="Meters from pharmacy location", null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['client', 'rep', 'started_at']),
            models.Index(fields=['client', 'pharmacy']),
        ]

    def __str__(self):
        return f"Visit {self.pharmacy} by {self.rep} on {self.started_at}"

class FormSubmission(models.Model):
    """
    Instance of a filled form for a visit. 
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="submissions")
    form_definition = models.ForeignKey(FormDefinition, on_delete=models.PROTECT)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('visit', 'form_definition')

class FormAnswer(models.Model):
    """
    Specific answer to a Question. Strongly typed values.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="answers")
    field_definition = models.ForeignKey(FormFieldDefinition, on_delete=models.PROTECT)
    
    # Storing values strongly typed
    value_text = models.TextField(blank=True, null=True)
    value_int = models.IntegerField(blank=True, null=True)
    value_decimal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_catalog_options = models.ManyToManyField(CatalogOption, blank=True) 
    
    raw_value = models.TextField(blank=True, help_text="String representation for quick display")

    class Meta:
        unique_together = ('submission', 'field_definition')

class EvidenceFile(models.Model):
    """
    Photos or files attached to a submission.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="evidence")
    answer = models.ForeignKey(FormAnswer, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos")
    
    file = models.FileField(upload_to="evidence/%Y/%m/%d/")
    file_type = models.CharField(max_length=20, default='PHOTO') 
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

# ==========================================
# 3. SPECIALIZED DOMAINS (POP & OOS)
# ==========================================

class PopType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50) 
    
    class Meta:
        unique_together = ('client', 'code')

    def __str__(self):
        return self.name

class PopPlacement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="pop_placements")
    pop_type = models.ForeignKey(PopType, on_delete=models.PROTECT)
    
    quantity = models.IntegerField(default=0)
    photo = models.ForeignKey(EvidenceFile, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('visit', 'pop_type')

class StockoutObservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="stockouts")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    is_oos = models.BooleanField(default=False, verbose_name="Is Out of Stock")
    cluster_source = models.CharField(max_length=50, default='VISIT') 
    
    class Meta:
        unique_together = ('visit', 'product')
        indexes = [
            models.Index(fields=['visit', 'product', 'is_oos']),
        ]
