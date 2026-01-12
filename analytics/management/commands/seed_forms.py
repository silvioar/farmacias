from django.core.management.base import BaseCommand
from analytics.models import Client, FormDefinition, FormFieldDefinition, Catalog, CatalogOption, PopType, Product, ProductBrand, ProductCategory

class Command(BaseCommand):
    help = 'Seeds initial Dynamic Forms and Master Data'

    def handle(self, *args, **kwargs):
        # Ensure Client
        client, _ = Client.objects.get_or_create(code="default_code", defaults={'name': 'Bioderma Demo', 'is_active': True})
        self.stdout.write(f"Using Client: {client}")

        # --- 1. Master Data: Products for Stockouts ---
        brand_bagovit, _ = ProductBrand.objects.get_or_create(client=client, name="Bagovit")
        cat_solar, _ = ProductCategory.objects.get_or_create(client=client, name="Solares")

        # List of SKUs from User Request
        sku_list = [
            "BAGOVIT POST SOLAR ALOE VERA X 350G",
            "BAGOVIT SOLAR F40 SPRAY X 200G",
            "BAGOVIT SOLAR F15 SPRAY C/ ACEL BRONZ X 200G",
            "BAGOVIT POST SOLAR C/A.V. GEL X 200",
            "PROT SOLAR BAGOVIT C/ACEL DE BRO SPRY F30 X 200ML",
            "BAGOVIT SOLAR FAMILY CARE FPS20 EMU 200ML",
            "BAGOVIT SOLAR FAMILY CARE FPS30 EMU 200ML",
            "BAGOVIT SOLAR FAMILY CARE FPS50 EMU 200ML",
            "BAGOVIT SOLAR FAMILY CARE KID FPS50 EMU 200ML",
            "PROT SOLAR BAGOVIT FACIAL FPS45 CREMA X50ML",
            "CREMA BAGOVIT SOLAR FPS30 SPRAY CONTINUO X 170ML",
            "CREMA BAGOVIT SOLAR FPS40 SPRAY CONTINUO X 170ML",
            "CREMA BAGOVIT SOLAR FPS35 LABIAL X 5G",
            "CREMA BAGOVIT SOLAR FPS75 EMU X 180G",
            "BAGOVIT SOLAR FAM.CARE KIDS F50 EMU200ML",
            "BAG.SOLAR FPS50 SPRAY TRANSP. X 200 ML",
            "BAGOVIT SOLAR FPS 40 SPY CONT EMUX 170ML",
            "BAGOVIT SOLAR FPS 35 LAL X 5 G",
            "BAGÓVIT SOLAR FPS 75 BEBÉS EMU X 180 G",
            "BAGÓVIT SOLAR FACIAL CRM X 50 G A/E NF",
            "BAGOVIT SOLAR FPS 30 SPY CONT EMUX 170ML",
            "BAGOVIT SOLAR ACEL BRONC FPS 30 SPY X200",
            "BAGOVIT SOLAR ACEL BRONC FPS 15 SPY X200",
            "BAGOVIT POST SOLAR C/AVAL 80% GEL X350"
        ]

        for sku_name in sku_list:
            Product.objects.get_or_create(
                client=client, 
                sku=sku_name[:50], # Truncate if too long for SKU field, but try to keep unique
                defaults={
                    'name': sku_name,
                    'brand': brand_bagovit,
                    'category': cat_solar
                }
            )

        # --- 2. Catalogs ---
        # Paso a Paso Bagovit
        cat_paso, _ = Catalog.objects.get_or_create(client=client, code="PASO_A_PASO", defaults={'name': 'Paso a Paso Bagovit'})
        if cat_paso:
            steps = ["Limpieza", "Tratamiento", "Fotoprotección", "Hidratación"]
            for i, label in enumerate(steps, 1):
                CatalogOption.objects.get_or_create(catalog=cat_paso, code=f"STEP_{i}", defaults={'label': label, 'order': i})

        # Competitors (Keep existing)
        cat_competitors, _ = Catalog.objects.get_or_create(client=client, code="COMPETITORS", defaults={'name': 'Marcas Competencia'})
        if cat_competitors:
             CatalogOption.objects.get_or_create(catalog=cat_competitors, code="LA_ROCHE", defaults={'label': 'La Roche-Posay', 'order': 1})
             CatalogOption.objects.get_or_create(catalog=cat_competitors, code="VICHY", defaults={'label': 'Vichy', 'order': 2})
             CatalogOption.objects.get_or_create(catalog=cat_competitors, code="EUCERIN", defaults={'label': 'Eucerin', 'order': 3})

        
        # --- 3. Form Definition "Primera Visita" ---
        form_code = "VISIT_V2_FULL" # New version
        FormDefinition.objects.filter(code=form_code).delete() # Reset for development

        form = FormDefinition.objects.create(
            client=client, 
            code=form_code, 
            version=1,
            title='Primera Visita (Full)',
            description='Relevamiento Completo 2026',
            is_active=True,
            allow_photos=True
        )

        self.stdout.write("Creating Form Fields...")
        
        order = 10
        def add_field(ftype, label, code, **kwargs):
            nonlocal order
            FormFieldDefinition.objects.create(
                form=form, order=order, field_type=ftype, label=label, code=code, **kwargs
            )
            order += 10

        # --- SECCION 1: Identificación y Contexto ---
        add_field('SECTION_HEADER', 'Contexto', 'SEC_CTX')
        # User, PDV, Address handled by App Context/UI, asking explicit questions only
        add_field('BOOL', '¿Es una Farmacia?', 'IS_PHARMACY', required=True)
        add_field('BOOL', '¿Te permite trabajar la farmacia?', 'ALLOW_WORK', required=True)

        # --- SECCION 2: Infraestructura ---
        add_field('SECTION_HEADER', 'Infraestructura y Layout', 'SEC_INFRA')
        add_field('BOOL', '¿Tiene todo exhibido detrás de mostrador?', 'INFRA_BEHIND_COUNTER')
        add_field('BOOL', '¿Tiene góndolas sectorizadas?', 'INFRA_SECTORIZED')
        add_field('INT', 'Cantidad de Góndolas', 'INFRA_GONDOLA_QTY', min_value=0)
        add_field('BOOL', '¿Suplementos fuera de mostrador?', 'INFRA_SUPPLEMENTS')
        add_field('BOOL', '¿OTC fuera de mostrador?', 'INFRA_OTC')
        add_field('BOOL', '¿Tiene Checkout?', 'INFRA_CHECKOUT')
        add_field('BOOL', '¿Capilares exhibidos?', 'INFRA_HAIR')

        # --- SECCION 3: Solar ---
        add_field('SECTION_HEADER', 'Solar - Fotos y Frentes', 'SEC_SOLAR')
        add_field('PHOTO', 'Foto Panorámica Góndola Solar', 'PHOTO_SOLAR_PANORAMA')
        add_field('INT', 'Cant. Frentes Góndola Solar', 'QTY_FRONT_SOLAR_TOTAL', min_value=0)
        add_field('INT', 'Cant. Frentes Bagovit Solar', 'QTY_FRONT_SOLAR_BAGOVIT', min_value=0)
        add_field('INT', 'Cant. Frentes Dermaglós Solar', 'QTY_FRONT_SOLAR_DERMA', min_value=0)
        add_field('MULTI_SELECT', 'Paso a Paso Bagovit Solar', 'CHECKLIST_PASO_a_PASO', catalog=cat_paso)

        # --- SECCION 4: POP Colocado (Solares / Adicional) ---
        add_field('SECTION_HEADER', 'Material POP', 'SEC_POP')
        
        pop_items = [
            ("Exhibidor de Pie", "POP_FLOOR"),
            ("Exhibidor de Mostrador", "POP_COUNTER"),
            ("Bandejas", "POP_TRAY"),
            ("Cenefas Abajo", "POP_SHELF_DOWN"),
            ("Cenefas Arriba", "POP_SHELF_UP"),
            ("Flejeras", "POP_STRIPS"),
            ("Movies", "POP_MOVIES"),
            ("Cubos", "POP_CUBES"),
            ("Mini Totems", "POP_TOTEM_MINI"),
            ("Pancartas", "POP_BANNER"),
            ("Espaldares", "POP_BACK"),
            ("Tiras de Impulso", "POP_IMPULSE"),
        ]

        for label, code_suffix in pop_items:
            add_field('INT', f'Unidades Colocadas: {label}', f'QTY_{code_suffix}', min_value=0)

        add_field('PHOTO', 'Foto POP Liviano', 'PHOTO_POP_LIGHT')
        add_field('PHOTO', 'Foto Comunicación Instore', 'PHOTO_POP_INSTORE')

        # --- SECCION 5: Descuento / Competencia ---
        add_field('SECTION_HEADER', 'Descuento y Competencia', 'SEC_COMP')
        add_field('BOOL', '¿Dinámica de Descuento Ejecutada?', 'DISCOUNT_EXECUTED')
        add_field('BOOL', '¿Material Diferencial Competencia?', 'COMP_DIFF_MATERIAL')
        add_field('PHOTO', 'Foto Competencia', 'PHOTO_COMP')

        # --- SECCION 6: Relevo de Quiebres (Stockouts) ---
        add_field('SECTION_HEADER', 'Relevo de Quiebres (Stockouts)', 'SEC_OOS')
        
        # Here we create fields mapped to products. 
        # Convention: Code starts with 'OOS_' followed by SKU (or ID, but SKU is cleaner for reading)
        
        for sku_name in sku_list:
            sku_clean = sku_name[:50]
            add_field('BOOL', sku_name, f'OOS_{sku_clean}')

        # Observaciones
        add_field('SECTION_HEADER', 'Cierre', 'SEC_CLOSE')
        add_field('TEXT', 'Comentarios Generales', 'COMMENTS')

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded form: {form.title}'))

        # --- 4. Form Definition "Visita Integral Farmacia" (V1 - Simple) ---
        form_code_v1 = "VISIT_V1"
        FormDefinition.objects.filter(code=form_code_v1).delete()

        form_v1 = FormDefinition.objects.create(
            client=client, 
            code=form_code_v1, 
            version=1,
            title='Visita Integral Farmacia',
            description='Relevamiento Básico (Stock y Visibilidad)',
            is_active=True,
            allow_photos=True
        )

        order_v1 = 10
        def add_field_v1(ftype, label, code, **kwargs):
            nonlocal order_v1
            FormFieldDefinition.objects.create(
                form=form_v1, order=order_v1, field_type=ftype, label=label, code=code, **kwargs
            )
            order_v1 += 10

        add_field_v1('SECTION_HEADER', 'Datos Básicos', 'SEC_BASIC')
        add_field_v1('BOOL', '¿Farmacia Abierta?', 'IS_OPEN', required=True)
        add_field_v1('SECTION_HEADER', 'Visibilidad', 'SEC_VIS')
        add_field_v1('PHOTO', 'Foto de Vidriera', 'PHOTO_WINDOW')
        add_field_v1('INT', 'Cantidad de Frentes Bioderma', 'SHARE_SHELF_QTY', min_value=0)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded form: {form_v1.title}'))
