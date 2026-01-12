from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import VisitStatus
import os
import pandas as pd
from scipy.spatial.distance import pdist, squareform
import folium
from folium import Map, Marker, PolyLine, DivIcon, Popup
from geopy.geocoders import Nominatim

# Use the new location inside routes/files
FILE_PATH = os.path.join(settings.BASE_DIR, 'routes', 'files', 'farmacias_geoloc.xlsx')

@login_required
def optimized_route_view(request):
    try:
        df = pd.read_excel(FILE_PATH)
    except FileNotFoundError:
        return render(request, "routes/route.html", {
            "error": "Error: File 'farmacias_geoloc.xlsx' not found.",
            "localidades": [],
            "localidad": ""
        })

    all_localidades = sorted(df['LOCALIDAD'].dropna().unique().tolist())
    localidad = (request.GET.get("localidad") or "").strip()
    start_address = request.POST.get("start_address") or request.GET.get("start_address")

    if not localidad:
        return render(request, "routes/route.html", {
            "map": None,
            "farmacias": [],
            "localidad": "",
            "localidades": all_localidades,
            "start_address": start_address
        })

    # Handle POST to toggle visit status (Fallback if AJAX fails, though we use AJAX mostly)
    if request.method == "POST" and "toggle_visit" in request.POST:
        # Check if it's the toggle form submission (legacy/fallback)
        pass 
        # Actually the view below handles AJAX toggles. 
        # If we restart the page via POST, we might handle it here OR separate view.
        # The original code had mixed logic. Let's keep it clean.
    
    # Filter by locality
    df_filtered = df[df['LOCALIDAD'].str.upper() == localidad.upper()].dropna(subset=['LAT', 'LON']).reset_index(drop=True)
    
    if df_filtered.empty:
        return render(request, "routes/route.html", {
            "error": f"No farmacias se encontraron en {localidad}.",
            "localidades": all_localidades,
            "localidad": localidad,
            "start_address": start_address
        })

    # Geocode and add starting point if provided
    if start_address:
        geolocator = Nominatim(user_agent="geoapi_routes")
        try:
            location = geolocator.geocode(start_address)
            if location:
                start_point = pd.DataFrame([{
                    "APELLIDO": "Inicio",
                    "DIRECCION": start_address,
                    "LOCALIDAD": localidad,
                    "LAT": location.latitude,
                    "LON": location.longitude
                }])
                df_filtered = pd.concat([start_point, df_filtered], ignore_index=True)
            else:
                return render(request, "routes/route.html", {
                    "error": f"No se pudo geolocalizar la dirección de inicio: {start_address}",
                    "localidades": all_localidades,
                    "localidad": localidad,
                    "start_address": start_address
                })
        except Exception as e:
             return render(request, "routes/route.html", {
                    "error": f"Error de geolocalización: {str(e)}",
                    "localidades": all_localidades,
                    "localidad": localidad,
                    "start_address": start_address
                })

    # TSP path with fixed start at index 0 (or random start if no specific start)
    if len(df_filtered) > 1:
        coords = df_filtered[['LAT', 'LON']].to_numpy()
        distance_matrix = squareform(pdist(coords))

        def tsp_with_fixed_start(dm):
            n = len(dm)
            unvisited = set(range(1, n))  # start at 0
            path = [0]
            while unvisited:
                last = path[-1]
                next_city = min(unvisited, key=lambda city: dm[last][city])
                path.append(next_city)
                unvisited.remove(next_city)
            return path

        path = tsp_with_fixed_start(distance_matrix)
        ordered_df = df_filtered.iloc[path].copy()
    else:
        ordered_df = df_filtered.copy()


    # Assign visit order (starting from 1, skip "Inicio")
    ordered_df['Visit_Order'] = None
    counter = 1
    for idx, row in ordered_df.iterrows():
        if row['APELLIDO'] != "Inicio":
            ordered_df.at[idx, 'Visit_Order'] = counter
            counter += 1

    # Add visitado status
    def get_visitado(row):
        if row['APELLIDO'] == "Inicio":
            return None
        vs = VisitStatus.objects.filter(
            user=request.user,
            apellido=row['APELLIDO'],
            direccion=row['DIRECCION'],
            localidad=row['LOCALIDAD']
        ).first()
        return vs.visitado if vs else False

    ordered_df['visitado'] = ordered_df.apply(get_visitado, axis=1)

    # Build farmacia list (exclude start point for the list view usually, but we keep it in map)
    farmacia_list = []
    for _, row in ordered_df.iterrows():
        if row['APELLIDO'] == "Inicio":
            continue
        farmacia_list.append({
            "Visit_Order": row['Visit_Order'],
            "APELLIDO": row['APELLIDO'],
            "DIRECCION": row['DIRECCION'],
            "LOCALIDAD": row['LOCALIDAD'],
            "visitado": row['visitado'],
            "LAT": row['LAT'],
            "LON": row['LON'],
        })

    # Center map
    center_lat = ordered_df['LAT'].mean()
    center_lon = ordered_df['LON'].mean()
    m = Map(location=[center_lat, center_lon], zoom_start=14)

    # Add markers
    for _, row in ordered_df.iterrows():
        if row['APELLIDO'] == "Inicio":
            color = "#0ea5e9" # Primary blue
            badge = "🏁 Inicio"
            label = "Inicio"
        else:
            color = "#10b981" if row['visitado'] else "#64748b" # Success green or Slate 500
            badge = "✅ Visitado" if row['visitado'] else "❌ Pendiente"
            label = str(row["Visit_Order"])

        popup_html = f"""
        <div style='font-family:sans-serif; font-size:13px; line-height:1.4; color: #1e293b;'>
            <strong style='font-size:15px;'>📍 {label} {row['APELLIDO']}</strong><br>
            📫 <span style='color:#64748b;'>{row['DIRECCION']}</span><br>
            🏙️ <span style='color:#94a3b8; font-size:12px;'>{row['LOCALIDAD']}</span><br>
            <span style='display:inline-block; margin-top:4px; padding:2px 6px; border-radius:4px; background-color:{color}; color:white; font-size:12px;'>
                {badge}
            </span>
        </div>
        """

        marker_html = f'''
        <div id="marker_{label}" style="font-size:10pt;
                    color:white;
                    background:{color};
                    border-radius:50%;
                    text-align:center;
                    width:24px;
                    height:24px;
                    line-height:24px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    border: 2px solid white;">
            {label if label != "Inicio" else "🏁"}
        </div>'''

        marker = Marker(
            location=[row['LAT'], row['LON']],
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=marker_html
            ),
            popup=Popup(popup_html, max_width=250)
        )
        marker.add_to(m)

    # Draw route
    PolyLine(locations=ordered_df[['LAT', 'LON']].values.tolist(), color='#3b82f6', weight=3, opacity=0.8).add_to(m)
    
    # Inject script to keep map accessible
    m.get_root().html.add_child(folium.Element('<script>window.map = map;</script>'))

    return render(request, "routes/route.html", {
        "map": m._repr_html_(),
        "farmacias": farmacia_list,
        "localidad": localidad,
        "localidades": all_localidades,
        "start_address": start_address,
    })


@csrf_exempt
@login_required
def toggle_visitado(request):
    if request.method == "POST":
        apellido = request.POST.get("apellido")
        direccion = request.POST.get("direccion")
        localidad = request.POST.get("localidad")

        vs, _ = VisitStatus.objects.get_or_create(
            user=request.user,
            apellido=apellido,
            direccion=direccion,
            localidad=localidad
        )
        vs.visitado = not vs.visitado
        vs.save()
        return JsonResponse({"status": "ok", "visitado": vs.visitado})

    return JsonResponse({"status": "error"}, status=400)
