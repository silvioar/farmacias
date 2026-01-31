from django.core.management.base import BaseCommand
from surveys.models import FormDefinition, FormFieldDefinition, Catalog, CatalogOption
from analytics.models import Client, Product, ProductBrand
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the Primera Visita form structure'

    def handle(self, *args, **options):
        client = Client.objects.first()
        if not client:
            client = Client.objects.create(name="Bagó", code="BAGO_ARG")
            self.stdout.write("Created default client: Bagó")

        # 1. Define Products for Stockouts (Quiebres)
        products_list = [
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
            "BAGOVIT SOLAR FAMILY CARE FPS50 EMU200ML",
            "BAG.SOLAR FPS50 SPRAY TRANSP. X 200 ML",
            "BAGOVIT SOLAR FPS 40 SPY CONT EMUX 170ML",
            "BAGOVIT SOLAR FPS 35 LAL X 5 G",
            "BAGÓVIT SOLAR FPS 75 BEBÉS EMU X 180 G",
            "BAGOVIT SOLAR FAMILY CARE FPS30 EMU200ML",
            "BAGÓVIT SOLAR FACIAL CRM X 50 G A/E NF",
            "BAGOVIT SOLAR FPS 30 SPY CONT EMUX 170ML",
            "BAGOVIT SOLAR ACEL BRONC FPS 30 SPY X200",
            "BAGOVIT SOLAR ACEL BRONC FPS 15 SPY X200",
            "BAGOVIT SOLAR FAMILY CARE FPS20 EMU200ML",
            "BAGOVIT POST SOLAR C/AVAL 80% GEL X350",
            "BAGOVIT POST SOLAR C/AVAL 80% GEL X200",
            "BAGOVIT SOLAR FAMILY CARE X350",
        ]

        created_count = 0
        bagovit_brand, _ = ProductBrand.objects.get_or_create(
            client=client, 
            name="Bagovit Solar"
        )

        for p_name in products_list:
            sku = slugify(p_name).upper().replace("-", "_")
            product, created = Product.objects.get_or_create(
                client=client, 
                sku=sku,
                defaults={'name': p_name, 'brand': bagovit_brand}
            )
            if created:
                created_count += 1
        self.stdout.write(f"Synced {len(products_list)} products (Created {created_count} new).")

        # 2. Create Form Definition
        form_code = "PRIMERA_VISITA_V1"
        form, created = FormDefinition.objects.get_or_create(
            client=client,
            code=form_code,
            defaults={
                'title': 'Primera Visita (Full)',
                'version': 1,
                'description': 'Relevamiento completo de Farmacia: Infraestructura, Solar, POP y Quiebres.',
                'is_active': True
            }
        )
        if not created:
            self.stdout.write("Form already exists. Clearing old fields to rebuild...")
            form.fields.all().delete()
        
        # Helper to add fields
        order_counter = 1
        def add_field(label, type, code=None, required=False, catalog=None):
            nonlocal order_counter
            if not code:
                code = slugify(label).upper().replace("-", "_")
            
            FormFieldDefinition.objects.create(
                form=form,
                order=order_counter,
                label=label,
                code=code,
                field_type=type,
                required=required,
                catalog=catalog
            )
            order_counter += 1

        # --- SECCION 1: Identificación y Contexto ---
        add_field("Identificación y Contexto", "SECTION_HEADER")
        # Metadata logic handles User, Pharmacy, Date. We only need the explicit Boolean questions.
        add_field("¿Es una Farmacia?", "BOOL", "ES_FARMACIA", True)
        add_field("¿Te permite trabajar la farmacia?", "BOOL", "PERMITE_TRABAJAR", True)

        # --- SECCION 2: Infraestructura ---
        add_field("Infraestructura y Exhibición", "SECTION_HEADER")
        add_field("¿Tiene todo exhibido detrás de mostrador?", "BOOL")
        add_field("¿Tiene las góndolas / vitrinas sectorizadas?", "BOOL")
        add_field("Cantidad de Góndolas", "INT", "CANT_GONDOLAS")
        add_field("¿Cuenta con suplementos exhibidos fuera del mostrador?", "BOOL")
        add_field("¿Tiene OTC exhibidos en góndola fuera del mostrador?", "BOOL")
        add_field("¿Tiene Checkout?", "BOOL")
        add_field("¿Tiene Capilares exhibidos en el PDV?", "BOOL")

        # --- SECCION 3: Solar Fotos y Frentes ---
        add_field("Solar: Fotos y Frentes", "SECTION_HEADER")
        add_field("Foto Panorámica Góndola Solar", "PHOTO")
        add_field("Cantidad de Frentes Góndola Solar", "INT", "FRENTES_SOLAR_TOTAL")
        add_field("Cantidad de Frentes Bagovit Solar", "INT", "FRENTES_SOLAR_BAGOVIT")
        add_field("Cantidad de Frentes Dermaglos Solar", "INT", "FRENTES_SOLAR_DERMAGLOS")
        
        # Catalog for "Paso a Paso"
        paso_cat, _ = Catalog.objects.get_or_create(client=client, code="CAT_PASO_A_PASO", name="Pasos Bagovit Solar")
        if paso_cat.options.count() == 0:
            CatalogOption.objects.create(catalog=paso_cat, code="LIMPIEZA", label="Limpieza", order=1)
            CatalogOption.objects.create(catalog=paso_cat, code="PROTECCION", label="Protección", order=2)
            CatalogOption.objects.create(catalog=paso_cat, code="POST_SOLAR", label="Post Solar", order=3)
        
        add_field("Paso a Paso Bagovit Solar", "MULTI_SELECT", "PASO_A_PASO_CHECKLIST", catalog=paso_cat)

        # --- SECCION 4: POP (Bloque 1) ---
        add_field("Material POP (Liviano)", "SECTION_HEADER")
        pop_types_1 = [
            "Exhibidor de pie", "Exhibidor de mostrador", "Bandejas", "Cenefas abajo", 
            "Cenefas arriba", "Flejeras con logo", "Flejeras sin logo", "Movies", 
            "Cubos", "Mini totems", "Pancartas", "Espaldares", "Solares Bandejas"
        ]
        for pt in pop_types_1:
            code = "POP1_" + slugify(pt).upper().replace("-", "_")
            add_field(f"Unidades colocadas: {pt}", "INT", code)

        add_field("Foto POP Liviano", "PHOTO")
        add_field("Foto Comunicación Instore", "PHOTO")
        add_field("Foto Exhibición Adicional", "PHOTO")

        # --- SECCION 5: Descuento & Competencia ---
        add_field("Descuento y Competencia", "SECTION_HEADER")
        add_field("¿Está la dinámica de descuento ejecutada?", "BOOL")
        add_field("¿Hay material diferencial de la competencia?", "BOOL")
        add_field("Foto Competencia", "PHOTO")

        # --- SECCION 6: POP (Bloque 2) ---
        add_field("Material POP (Solares / Adicional)", "SECTION_HEADER")
        pop_types_2 = [
            "Solares Cenefas Abajo", "Solares Cenefas Arriba", "Exhibidor de Mostrador (Solar)",
            "Exhibidor de Pie (Solar)", "Corpóreo", "Mini Totem (Solar)", "Flejeras (Solar)",
            "Espaldares (Solar)", "Tiras de Impulso", "Conectores de Beneficios", 
            "Conectores de Descuento", "Movies (Solar)", "Parasol", "Etiqueta de Viaje"
        ]
        for pt in pop_types_2:
             code = "POP2_" + slugify(pt).upper().replace("-", "_")
             add_field(f"Unidades colocadas: {pt}", "INT", code)

        # --- SECCION 7: Quiebres (Stockouts) ---
        add_field("Relevo de Quiebres", "SECTION_HEADER")
        self.stdout.write("Generating Stockout Fields...")
        
        for p_name in products_list:
            sku = slugify(p_name).upper().replace("-", "_")
            # Field Code MUST start with OOS_ for local logic to work
            field_code = f"OOS_{sku}"
            add_field(f"¿Quiebre? {p_name}", "BOOL", field_code)

        # --- Final ---
        add_field("Observaciones", "SECTION_HEADER")
        add_field("Comentarios Generales", "TEXT_AREA", "COMENTARIOS")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded form '{form.title}' with {order_counter} fields."))
