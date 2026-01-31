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

# Sections 3, 4, 5 moved to 'surveys' app.

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

class CommercialAgreement(models.Model):
    """
    Acuerdo Comercial / Commercial Contract
    Stores the terms agreed between the Lab and the Pharmacy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='agreements')
    
    start_date = models.DateField(_("Fecha Inicio"))
    end_date = models.DateField(_("Fecha Fin"))
    
    description = models.TextField(_("Descripción / Términos"), help_text="Condiciones, beneficios y productos acordados")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Acuerdo Comercial")
        verbose_name_plural = _("Acuerdos Comerciales")
        ordering = ['-start_date']

    def __str__(self):
        return f"Acuerdo {self.pharmacy.display_name} ({self.start_date})"
