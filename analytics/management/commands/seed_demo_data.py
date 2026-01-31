import random
import datetime
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from analytics.models import (
    Client, Region, Zone, Territory, Pharmacy, ProductBrand,
    ProductCategory, Product, SalesDocument, SalesLine, Rep, CommercialAgreement
)
from surveys.models import Visit

class Command(BaseCommand):
    help = 'Genera datos de demostración para el año completo 2025'

    def handle(self, *args, **kwargs):
        self.stdout.write("Limpiando datos transaccionales existentes...")
        SalesDocument.objects.all().delete()
        Visit.objects.all().delete()
        CommercialAgreement.objects.all().delete()
        
        self.stdout.write("Generando datos de demostración para 2025...")

        # 1. Crear Cliente
        client, _ = Client.objects.get_or_create(
            code="default_code",
            defaults={'name': 'Bioderma Demo', 'is_active': True}
        )

        # 2. Geografía - Estructura Nacional
        reg_ba, _ = Region.objects.get_or_create(client=client, name="Buenos Aires")
        reg_centro, _ = Region.objects.get_or_create(client=client, name="Centro")
        reg_cuyo, _ = Region.objects.get_or_create(client=client, name="Cuyo")
        
        # Zonas
        zone_cab, _ = Zone.objects.get_or_create(client=client, name="CABA", region=reg_ba)
        zone_gba, _ = Zone.objects.get_or_create(client=client, name="GBA", region=reg_ba)
        zone_cba, _ = Zone.objects.get_or_create(client=client, name="Córdoba", region=reg_centro)
        zone_sf, _ = Zone.objects.get_or_create(client=client, name="Santa Fe", region=reg_centro)
        zone_mdz, _ = Zone.objects.get_or_create(client=client, name="Mendoza", region=reg_cuyo)
        
        # Territorios
        terr_belgrano, _ = Territory.objects.get_or_create(client=client, name="Belgrano/Norte", zone=zone_cab)
        terr_caballito, _ = Territory.objects.get_or_create(client=client, name="Caballito/Centro", zone=zone_cab)
        terr_palermo, _ = Territory.objects.get_or_create(client=client, name="Palermo", zone=zone_cab)
        terr_san_isidro, _ = Territory.objects.get_or_create(client=client, name="San Isidro", zone=zone_gba)
        terr_cba_cap, _ = Territory.objects.get_or_create(client=client, name="Córdoba Capital", zone=zone_cba)
        terr_rosario, _ = Territory.objects.get_or_create(client=client, name="Rosario", zone=zone_sf)
        terr_mdz_cap, _ = Territory.objects.get_or_create(client=client, name="Mendoza Capital", zone=zone_mdz)

        # 3. Productos y Categorías
        cat_sun, _ = ProductCategory.objects.get_or_create(client=client, name="Protección Solar")
        cat_face, _ = ProductCategory.objects.get_or_create(client=client, name="Cuidado Facial")
        
        brand, _ = ProductBrand.objects.get_or_create(client=client, name="Bioderma")
        
        products = []
        product_names = [
            ("Photoderm Max SPF 50+", cat_sun, 25000),
            ("Photoderm Nude Touch", cat_sun, 28000),
            ("Sensibio H2O 500ml", cat_face, 18000),
            ("Sebium Gel Moussant", cat_face, 15000),
            ("Hydrabio Serum", cat_face, 22000),
        ]
        
        for i, (name, cat, price) in enumerate(product_names):
            p, _ = Product.objects.get_or_create(
                client=client,
                sku=f"SKU-{100+i}",
                defaults={
                    'name': name,
                    'brand': brand,
                    'category': cat,
                }
            )
            # Store price tuple for later
            p.demo_price = price
            products.append(p)

        # 4. Crear 10 Farmacias con perfiles y ubicaciones variadas
        # (Nombre, Segmento, VentaTarget, Visitas, Territorio)
        pharmacy_profiles = [
            ("Farmacia Azul Belgrano", "A", 1200000, 50, terr_belgrano),
            ("Farmacity Cabildo", "A", 2500000, 120, terr_belgrano),
            ("Farmacia Social Córdoba", "B", 800000, 30, terr_cba_cap),
            ("Farmacia Del Pueblo Ros", "C", 300000, 10, terr_rosario),
            ("GPS Farma Palermo", "A", 1500000, 60, terr_palermo),
            ("Farmacia Cuyo", "B", 700000, 25, terr_mdz_cap),
            ("Dr. Ahorro Centro", "C", 400000, 15, terr_caballito),
            ("Farmacia Suiza CBA", "A", 1800000, 55, terr_cba_cap),
            ("Farmacia Zona Norte", "B", 600000, 20, terr_san_isidro),
            ("Farmacia Los Andes", "C", 250000, 8, terr_mdz_cap),
        ]

        # Crear Reps por zona (Create Users first)
        from django.contrib.auth.models import User
        
        user_ba, _ = User.objects.get_or_create(username='rep_ba', defaults={'first_name': 'Juan', 'last_name': 'Perez'})
        if not _: user_ba.set_password('123'); user_ba.save()
        
        user_int, _ = User.objects.get_or_create(username='rep_int', defaults={'first_name': 'Maria', 'last_name': 'Gomez'})
        if not _: user_int.set_password('123'); user_int.save()

        rep_ba, _ = Rep.objects.get_or_create(client=client, user=user_ba, defaults={'territory': terr_belgrano})
        rep_int, _ = Rep.objects.get_or_create(client=client, user=user_int, defaults={'territory': terr_cba_cap})

        # Define 2025 Date Range
        start_date = datetime.date(2025, 1, 1)
        end_date = datetime.date(2025, 12, 31)
        delta_days = (end_date - start_date).days + 1

        for i, (name, segment, target_sales, visits, pharm_territory) in enumerate(pharmacy_profiles):
            code = f"PH-{1000+i}"
            pharmacy, _ = Pharmacy.objects.get_or_create(
                client=client,
                code=code,
                defaults={
                    'name_legal': f"{name} S.A.",
                    'name_trade': name,
                    'display_name': name,
                    'external_id': code,
                    'territory': pharm_territory,
                    'city': pharm_territory.zone.name,
                    'state': pharm_territory.zone.region.name,
                    'address': 'Calle Falsa 123',
                    'segment_data': {"cluster": segment, "loyalty_tier": "Gold" if segment == "A" else "Silver", "ecommerce": segment == "A"},
                    'is_active': True
                }
            )
            
            if pharmacy.territory != pharm_territory:
                pharmacy.territory = pharm_territory
                pharmacy.save()
            
            # Create Agreement for ~50% of pharmacies
            if i % 2 == 0:
                CommercialAgreement.objects.create(
                    client=client,
                    pharmacy=pharmacy,
                    start_date=start_date,
                    end_date=end_date,
                    description="Acuerdo Anual 2025: Exhibición preferencial en góndola principal + 2 punteras. Descuento 15% en línea Photoderm.",
                    is_active=True
                )

            self.stdout.write(f"  -> Generando datos 2025 para: {name} ({segment}) - {pharm_territory.zone.name}")

            assigned_rep = rep_int if pharm_territory.zone.name in ["Córdoba", "Santa Fe", "Mendoza"] else rep_ba
            
            # Predictable product pattern for AI testing - DIVERSIFIED PER PHARMACY
            # We rotate the product we want to trigger suggestions for based on pharmacy index
            
            # Products: 
            # 0: Photoderm Max (Sun)
            # 1: Photoderm Nude (Sun)
            # 2: Sensibio H2O (Face)
            # 3: Sebium Gel (Face)
            # 4: Hydrabio Serum (Face)

            idx_controlled = i % len(products) # Rotate 0..4
            controlled_product = products[idx_controlled]
            
            # Different cycles and stop dates to make it look organic
            # Cycle: 30 to 60 days
            cycle_days = 30 + (i * 5) % 30  # 30, 35, 40, 45...
            
            # Stop date (Days ago): 40 to 100 days
            # Must be > cycle_days to trigger alert
            days_stopped = cycle_days + 15 + (i * 7) % 50
            
            last_controlled_date = None

            # Generar Ventas (Full Year 2025)
            for day_offset in range(delta_days):
                current_date = start_date + timedelta(days=day_offset)
                
                # Logic for Controlled Product (AI Suggestion Trigger)
                buy_controlled = False
                
                # Only buy if we are BEFORE the stop date
                # Stop date is from END of year backwards? OR from TODAY?
                # The logic uses 2025 full year. Let's assume "Today" is end of 2025 or we just simulate gaps.
                # If we want a gap at the END of the data (Dec 31 2025), we stop N days before Delta.
                
                if (day_offset % cycle_days == 0) and (day_offset < delta_days - days_stopped): 
                     buy_controlled = True
                
                is_summer = current_date.month in [1, 2, 12]
                seasonality_factor = 1.5 if is_summer else 1.0
                
                if segment == "A":
                    num_tx = int(random.randint(3, 8) * seasonality_factor)
                elif segment == "B":
                    num_tx = int(random.randint(1, 3) * seasonality_factor)
                else:
                    num_tx = int(random.randint(0, 2) * seasonality_factor)
                
                # If we need to buy controlled product but rng gave 0 tx, force 1
                if buy_controlled and num_tx == 0:
                    num_tx = 1

                for _ in range(num_tx):
                    tx_time = datetime.time(random.randint(9, 20), random.randint(0, 59))
                    tx_datetime = timezone.make_aware(datetime.datetime.combine(current_date, tx_time))

                    has_coupon = random.random() < 0.2
                    coupon = f"PROMO-{random.randint(10,99)}" if has_coupon else ""
                    source = random.choice(['Mostrador', 'Web', 'App', 'Call Center'])
                    
                    sales_doc = SalesDocument.objects.create(
                        client=client,
                        pharmacy=pharmacy,
                        external_id=f"TRX-{pharmacy.code}-{current_date.strftime('%j')}-{random.randint(1000,9999)}",
                        date=tx_datetime,
                        doc_type="TICKET",
                        order_source=source,
                        coupon_code=coupon,
                        status="COMPLETED",
                        total_amount=0,
                        currency="ARS"
                    )
                    
                    total = 0
                    
                    # Add items
                    items_to_add = []
                    
                    if buy_controlled:
                        items_to_add.append(controlled_product)
                        buy_controlled = False # Added once per day is enough
                    
                    # Add random other items
                    # Exclude controlled product from random pool to protect the pattern
                    random_pool = [p for p in products if p != controlled_product]
                    
                    for _ in range(random.randint(1, 4)):
                        items_to_add.append(random.choice(random_pool))

                    for prod in items_to_add:
                        qty = random.randint(1, 3)
                        price = prod.demo_price
                        
                        is_combo = random.random() < 0.1
                        combo = random.choice(["Combo Solar", "Combo Rutina", "Combo Verano"]) if is_combo else ""
                        
                        ret_status = 'REJECTED' if random.random() < 0.05 else 'DELIVERED'
                        
                        line_total = qty * price
                        
                        SalesLine.objects.create(
                            document=sales_doc,
                            product=prod,
                            quantity=qty,
                            unit_price=price,
                            total_price=line_total,
                            combo_name=combo,
                            discount_coupon_amount=line_total * 0.1 if has_coupon else 0,
                            return_status=ret_status,
                            is_promo=(is_combo or has_coupon)
                        )
                        total += line_total
                    
                    sales_doc.total_amount = total
                    sales_doc.save()

            # Generar Visitas
            num_visits = random.randint(12, 24)
            for _ in range(num_visits):
                visit_offset = random.randint(0, delta_days - 1)
                visit_date = start_date + timedelta(days=visit_offset)
                visit_time = datetime.time(random.randint(10, 16), 0)
                started_dt = timezone.make_aware(datetime.datetime.combine(visit_date, visit_time))
                duration = random.randint(15, 45)
                completed_dt = started_dt + timedelta(minutes=duration)
                
                Visit.objects.create(
                    client=client,
                    rep=assigned_rep,
                    pharmacy=pharmacy,
                    status='VALIDATED',
                    scheduled_at=started_dt - timedelta(days=1),
                    started_at=started_dt,
                    completed_at=completed_dt,
                    latitude_check_in=pharmacy.latitude,
                    longitude_check_in=pharmacy.longitude,
                    distance_from_target=0
                )

        self.stdout.write(self.style.SUCCESS('Datos de demostración 2025 generados exitosamente.'))
