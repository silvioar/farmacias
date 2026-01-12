import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

# Fallback for JSONField
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

# ==========================================
# 1. CORE & TENANCY
# ==========================================

class Client(models.Model):
    """
    Tenant configuration. Every major entity belongs to a Client.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Nombre"), max_length=255)
    code = models.CharField(_("Código"), max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        permissions = [
            ("view_dashboard", "Can view dashboard"),
            ("view_visits", "Can view visits"),
            ("view_routes", "Can view optimized routes"),
        ]

    def __str__(self):
        return self.name

class AuditLog(models.Model):
    """
    Audit trail for critical changes (FormDefinition, Catalog, etc).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

# ==========================================
# 2. MASTER DATA (Locations, Products, Reps)
# ==========================================

class Region(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(_("Nombre"), max_length=100)
    
    class Meta:
        verbose_name = _("Región")

    def __str__(self):
        return self.name

class Zone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(_("Nombre"), max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Zona")

    def __str__(self):
        return self.name

class Territory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(_("Nombre"), max_length=100)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = _("Territorio")

    def __str__(self):
        return self.name

class Rep(models.Model):
    """
    Field Representative / Visitador.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rep_profile')
    external_id = models.CharField(_("ID Legajo/Externo"), max_length=100, blank=True)
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Visitador (Rep)")
        verbose_name_plural = _("Visitadores")
        unique_together = ('client', 'external_id')

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Pharmacy(models.Model):
    """
    Point of Sale (PDV) / Farmacia.
    Expanded with logic for deduplication and segmentation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    # Identification
    code = models.CharField(_("Código Interno"), max_length=50, help_text="Código único en el sistema del cliente")
    external_id = models.CharField(_("ID Externo"), max_length=100, blank=True, help_text="ID en sistema origen/ERP")
    
    # Names
    name_legal = models.CharField(_("Razón Social"), max_length=200)
    name_trade = models.CharField(_("Nombre Fantasía"), max_length=200)
    display_name = models.CharField(_("Nombre Visual"), max_length=200)
    
    # Hierarchy
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location
    address = models.CharField(_("Dirección"), max_length=255)
    city = models.CharField(_("Ciudad"), max_length=100)
    state = models.CharField(_("Provincia"), max_length=100)
    zip_code = models.CharField(_("CP"), max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Classification (JSON for flexibility, or could use Normalized Tables)
    segment_data = JSONField(default=dict, blank=True, help_text="Tags, Cluster, Segmento")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Farmacia (PDV)")
        verbose_name_plural = _("Farmacias")
        unique_together = ('client', 'code')
        indexes = [
            models.Index(fields=['client', 'code']),
            models.Index(fields=['client', 'city']),
        ]

    def __str__(self):
        return f"{self.code} - {self.display_name}"

class ProductBrand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = _("Marca")
    
    def __str__(self):
        return self.name

class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _("Categoría de Producto")
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Product Master for Stockouts and Sales.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    sku = models.CharField(_("SKU"), max_length=50) # CODIGO MATERIAL
    ean = models.CharField(_("EAN"), max_length=50, blank=True)
    name = models.CharField(_("Nombre"), max_length=200)
    
    brand = models.ForeignKey(ProductBrand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        unique_together = ('client', 'sku')
        ordering = ['name']

    def __str__(self):
        return self.name

# ==========================================
# 3. DYNAMIC FORMS ENGINE
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
    # Format: {"field_code": "HAS_GONDOLA", "operator": "eq", "value": true}
    conditions = JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order']
        unique_together = ('form', 'code')

    def __str__(self):
        return f"{self.label} ({self.field_type})"

# ==========================================
# 4. EXECUTION (Visits & Answers)
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
    Separate from Visit to allow multiple forms per visit (e.g. Audit + Coaching).
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
    
    # Storing values strongly typed for querying
    value_text = models.TextField(blank=True, null=True)
    value_int = models.IntegerField(blank=True, null=True)
    value_decimal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_catalog_options = models.ManyToManyField(CatalogOption, blank=True) # For Multi-Select
    
    # Helper for simple display
    raw_value = models.TextField(blank=True, help_text="String representation for quick display")

    class Meta:
        unique_together = ('submission', 'field_definition')

class EvidenceFile(models.Model):
    """
    Photos or files attached to a submission or specific answer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="evidence")
    answer = models.ForeignKey(FormAnswer, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos")
    
    file = models.FileField(upload_to="evidence/%Y/%m/%d/")
    file_type = models.CharField(max_length=20, default='PHOTO') # PHOTO, SIGNATURE, DOC
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

# ==========================================
# 5. SPECIALIZED / NORMALIZED DOMAINS (POP & OOS)
# ==========================================

class PopType(models.Model):
    """
    Catalog of POP Materials (e.g. 'Exhibidor de Pie', 'Cenefa').
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50) # e.g. "FLOOR_DISPLAY"
    
    class Meta:
        unique_together = ('client', 'code')

    def __str__(self):
        return self.name

class PopPlacement(models.Model):
    """
    Normalized record of POP placement execution.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="pop_placements")
    pop_type = models.ForeignKey(PopType, on_delete=models.PROTECT)
    
    quantity = models.IntegerField(default=0)
    photo = models.ForeignKey(EvidenceFile, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('visit', 'pop_type')

class StockoutObservation(models.Model):
    """
    Normalized record of Product Availability (Quiebres).
    Replaces "RELEVO DE QUIEBRES [SKU]" columns.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="stockouts")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    is_oos = models.BooleanField(default=False, verbose_name="Is Out of Stock")
    
    # Metadata
    cluster_source = models.CharField(max_length=50, default='VISIT') # VISIT, SYSTEM
    
    class Meta:
        unique_together = ('visit', 'product')
        indexes = [
            models.Index(fields=['visit', 'product', 'is_oos']),
        ]

# ==========================================
# 6. LEGACY / DASHBOARD SUPPORT (Preserved)
# ==========================================

class SalesDocument(models.Model):
    # Needed for DashboardView
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=100)
    date = models.DateTimeField()
    
    doc_type = models.CharField(max_length=50, default='TICKET') 
    channel = models.CharField(max_length=50, default='OFFLINE') 
    order_source = models.CharField(max_length=100, blank=True) 
    coupon_code = models.CharField(max_length=50, blank=True) 
    status = models.CharField(max_length=50, default='COMPLETED') 
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    
    def __str__(self):
        return self.external_id

class SalesLine(models.Model):
    # Needed for OrderMasterListView
    id = models.AutoField(primary_key=True)
    document = models.ForeignKey(SalesDocument, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_coupon_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    combo_name = models.CharField(max_length=150, blank=True)
    is_promo = models.BooleanField(default=False)
    
    RETURN_STATUS = (('DELIVERED', 'Entregado'), ('REJECTED', 'Rechazado'), ('MISSING', 'Faltante'))
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS, default='DELIVERED')
    
    def __str__(self):
        return f"{self.product} x {self.quantity}"
