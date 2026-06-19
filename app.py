import streamlit as st
import pandas as pd
import math
import os
from fpdf import FPDF
from datetime import datetime

# 👇 AGREGA ESTAS DOS LÍNEAS 👇
from PIL import Image, ImageDraw, ImageFont
import tempfile

VERSION = "12.0.9"

# 1. ESTO DEBE SER LO PRIMERO Y ÚNICO EN TODO EL CÓDIGO
st.set_page_config(page_title=f"MVI Engineering V{VERSION}", page_icon="⚙️", layout="wide")

# --- INICIO DEL SISTEMA DE SEGURIDAD ---
def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<br><br><h1 style='text-align: center;'>🔒 MVI Engineering V12</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Staff Only - Ingresa la clave de acceso</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        password = st.text_input("Password", type="password")
        if password:
            # 👇 AQUÍ PONES LA CONTRASEÑA QUE QUIERAS
            if password == "MVI2026":
                st.session_state["password_correct"] = True
                st.rerun() # Recarga la página y deja pasar al usuario
            else:
                st.error("🚨 Contraseña incorrecta. Intenta de nuevo.")
    return False

if not check_password():
    st.stop() # 🛑 Detiene el programa aquí si no hay contraseña
# --- FIN DEL SISTEMA DE SEGURIDAD ---

# --- 1. INITIAL SETUP ---
# (Fíjate que aquí ya borramos el segundo set_page_config)

z_d = []
z_p = []

# --- 2. LÓGICA DE COORDENADAS (get_pts) ---
def get_pts(c_s, c_e, r_s, r_e, direction, start, style="Snake", u_limit=None):
    c_range, r_range = list(range(c_s, c_e)), list(range(r_s, r_e))
    if "Right" in start: c_range.reverse()
    if "Bottom" in start: r_range.reverse()
    pts = []
    cab_count = 0 # Contador para saber en qué gabinete del puerto vamos
    
    if direction == "Vertical":
        for i, c in enumerate(c_range):
            curr_r = list(r_range)
            
            # Lógica para invertir la columna dependiendo del estilo
            if style == "Snake":
                if i % 2 != 0: curr_r.reverse()
            elif style == "Snake (Reset per Port)" and u_limit:
                cabs_in_port = cab_count % u_limit
                col_in_port = cabs_in_port // len(r_range)
                if col_in_port % 2 != 0:
                    curr_r.reverse()
                    
            for r in curr_r:
                pts.append((r, c))
                cab_count += 1
    else:
        for i, r in enumerate(r_range):
            curr_c = list(c_range)
            
            if style == "Snake":
                if i % 2 != 0: curr_c.reverse()
            elif style == "Snake (Reset per Port)" and u_limit:
                cabs_in_port = cab_count % u_limit
                row_in_port = cabs_in_port // len(c_range)
                if row_in_port % 2 != 0:
                    curr_c.reverse()
                    
            for c in curr_c:
                pts.append((r, c))
                cab_count += 1
    return pts

# --- 3. DRAWING ENGINE (draw_map) ---
def draw_map(cols, rows, zones, u_limit, mode, is_data=True, backup=False):
    is_pdf_draw = (mode == "PDF_MODE")
    bg_color = (255, 255, 255) if (mode == "Light Mode" or is_pdf_draw) else (15, 15, 20)
    text_color = (0, 0, 0) if (mode == "Light Mode" or is_pdf_draw) else (255, 255, 255)
    
    img = Image.new('RGB', (1600, 1200), bg_color)
    draw = ImageDraw.Draw(img)
    
    m_x, m_y = 100, 160
    bw, bh = (1400//cols), (850//rows)
    
    if is_data:
        colors = [(88, 166, 255), (248, 81, 73), (63, 185, 80), (210, 153, 255), (255, 165, 0), (56, 220, 220)]
    else:
        colors = [(248, 81, 73), (63, 185, 80), (88, 166, 255), (210, 153, 255), (255, 165, 0), (56, 220, 220)]
    
    for r in range(rows):
        for c in range(cols):
            grid_w = max(1, int(bw * 0.015)) 
            draw.rectangle([m_x+c*bw, m_y+r*bh, m_x+c*bw+bw, m_y+r*bh+bh], outline=(80,80,80), width=grid_w)

    for z_idx, zone in enumerate(zones):
        z_col = colors[z_idx % len(colors)]
            
        for i, p in enumerate(zone):
            is_end = ((i + 1) % u_limit == 0) or (i == len(zone) - 1)
            if not is_end:
                pNext = zone[i+1]
                x1, y1 = m_x + p[1]*bw + bw//2, m_y + p[0]*bh + bh//2
                x2, y2 = m_x + pNext[1]*bw + bw//2, m_y + pNext[0]*bh + bh//2
                
                w_cable = max(4, int(bw * 0.15)) 
                dist = ((x2-x1)**2 + (y2-y1)**2)**0.5
                if dist > bw*1.8: w_cable = max(2, int(w_cable * 0.5))
                
                draw.line([x1, y1, x2, y2], fill=z_col, width=w_cable)

    p_count = 1
    f_size = 16 if cols > 20 else 20
    try: font = ImageFont.truetype("arial.ttf", f_size)
    except: font = ImageFont.load_default()

    for z_idx, zone in enumerate(zones):
        z_col = colors[z_idx % len(colors)]
            
        for i, p in enumerate(zone):
            x, y = m_x + p[1]*bw + bw//2, m_y + p[0]*bh + bh//2
            is_start = (i % u_limit == 0)
            is_end = ((i + 1) % u_limit == 0) or (i == len(zone) - 1)
            
            radius = max(6, int(bw * 0.20))
            border_w = max(2, int(radius * 0.3))
            
            draw.ellipse([x-radius-border_w, y-radius-border_w, x+radius+border_w, y+radius+border_w], fill=(0,0,0))
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=(255,204,0) if is_start else z_col)
            
            if is_start:
                label_txt = f"{'P' if is_data else 'AC'}{p_count}"
                if p[0] >= (rows / 2):
                    offset_y = max(20, int(radius * 2.5))
                    draw.text((x - 14, y + offset_y), label_txt, fill=text_color, font=font)
                else:
                    offset_y = max(40, int(bh * 0.7))
                    draw.text((x - 14, y - offset_y), label_txt, fill=text_color, font=font)
                p_count += 1
            
            if is_data and backup and is_end:
                line_ext = max(30, int(bh * 0.5))
                if p[0] < (rows / 2):
                    draw.line([x, y, x, y - line_ext], fill=(248, 81, 73), width=4)
                    draw.text((x - 28, y - line_ext - 22), "BACKUP", fill=(248, 81, 73), font=font)
                else:
                    draw.line([x, y, x, y + line_ext], fill=(248, 81, 73), width=4)
                    draw.text((x - 28, y + line_ext + 8), "BACKUP", fill=(248, 81, 73), font=font)
                
    return img

# --- 4. SIDEBAR (INPUTS & CSS) ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    ui_mode = st.radio("Display Mode", ["Dark Mode", "Light Mode"])
    unit_sys = st.radio("Unit System", ["Metric (kg/m)", "Imperial (lbs/ft)"])
    u_label, dist_label = ("kg", "m") if "Metric" in unit_sys else ("lbs", "ft")
    u_conv, dist_conv = (1.0, 1.0) if "Metric" in unit_sys else (2.20462, 3.28084)
    
    bg_c, text_c = ("#0e1117", "#ffffff") if ui_mode == "Dark Mode" else ("#ffffff", "#1a1a1a")

    theme_css = f"""
    <style>
        .stApp {{ background-color: {bg_c}; }}
        .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp span {{ color: {text_c} !important; }}
        
        .stButton > button, .stDownloadButton > button {{
            background-color: {"#262730" if ui_mode == "Dark Mode" else "#ffffff"} !important;
            color: {text_c} !important;
            border: 1px solid {"#4b4c52" if ui_mode == "Dark Mode" else "#d5d6d8"} !important;
            font-weight: bold;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: #ff4b4b !important; color: #ff4b4b !important;
        }}

        [data-testid="stFullScreenFrame"] :fullscreen,
        [data-testid="stFullScreenFrame"] :-webkit-full-screen,
        [data-testid="stFullScreenFrame"] :-moz-full-screen,
        [data-testid="stFullScreenFrame"] :-ms-fullscreen {{
            background-color: {bg_c} !important; color: {text_c} !important;
        }}
        :fullscreen p, :fullscreen h1, :fullscreen h2, :fullscreen h3, :fullscreen span {{ color: {text_c} !important; }}

        .plotly-graph-div .modebar-container {{
            background-color: {"rgba(14, 17, 23, 0.85)" if ui_mode == "Dark Mode" else "rgba(255, 255, 255, 0.85)"} !important;
            border: 1px solid {"#4b4c52" if ui_mode == "Dark Mode" else "#d5d6d8"} !important;
            border-radius: 4px; padding: 2px; opacity: 1 !important; transition: background-color 0.2s ease;
        }}
        .modebar-btn {{ background-color: transparent !important; color: {text_c} !important; }}
        .modebar-btn path {{ fill: {text_c} !important; }}
        .modebar-btn:hover path {{ fill: #ff4b4b !important; }}
        .plotly-graph-div .notifier-note {{
            background-color: {"#31333F" if ui_mode == "Dark Mode" else "#F0F2F6"} !important;
            color: {text_c} !important; border: 1px solid {"#4b4c52" if ui_mode == "Dark Mode" else "#d5d6d8"} !important;
        }}

        [data-testid="stSidebar"] {{ background-color: {"#262730" if ui_mode == "Dark Mode" else "#F0F2F6"}; }}

        button[title="View fullscreen"], [data-testid="StyledFullScreenButton"] {{
            background-color: transparent !important; border: none !important; box-shadow: none !important;
            width: auto !important; padding: 5px 10px !important;
        }}
        button[title="View fullscreen"] svg, [data-testid="StyledFullScreenButton"] svg {{
            display: none !important; 
        }}
        button[title="View fullscreen"]::after, [data-testid="StyledFullScreenButton"]::after {{
            content: "⛶ Fullscreen";
            font-size: 14px; font-weight: 500;
            color: {"rgba(255, 255, 255, 0.7)" if ui_mode == "Dark Mode" else "rgba(0, 0, 0, 0.6)"} !important;
            background-color: {"rgba(255, 255, 255, 0.1)" if ui_mode == "Dark Mode" else "rgba(0, 0, 0, 0.05)"} !important;
            padding: 6px 12px; border-radius: 4px;
            border: 1px solid {"rgba(255, 255, 255, 0.2)" if ui_mode == "Dark Mode" else "rgba(0, 0, 0, 0.1)"};
            transition: all 0.2s ease;
        }}
        button[title="View fullscreen"]:hover::after, [data-testid="StyledFullScreenButton"]:hover::after {{
            color: {text_c} !important;
            background-color: {"rgba(255, 255, 255, 0.2)" if ui_mode == "Dark Mode" else "rgba(0, 0, 0, 0.1)"} !important;
            border-color: #ff4b4b !important;
        }}
    </style>
    """
    st.markdown(theme_css, unsafe_allow_html=True)

    st.markdown("---")
    job_name = st.text_input("Project Name", "MVI Show", max_chars=40) 
    venue_name = st.text_input("Venue", "MVI Shop")
    lead_tech = st.text_input("Lead Tech", "Your Name Here")
    
    st.subheader("🖼️ SCREEN HARDWARE")
    # ... (aquí sigue tu código normal del CSV y los gabinetes)
    try:
        df = pd.read_csv("modelos.csv", encoding='latin-1', sep=None, engine='python').fillna(0)
        cols_norm = {c.strip().lower(): c for c in df.columns}
        def safe_get_col(key):
            for k in cols_norm:
                if key.lower() in k: return cols_norm[k]
            raise ValueError(f"Column '{key}' not found")
        c_model = safe_get_col('model'); c_watts = safe_get_col('watts')
        c_weight = safe_get_col('weight'); c_pxw = safe_get_col('pixels_w'); c_pxh = safe_get_col('pixels_h')
        c_mmw = safe_get_col('width_mm'); c_mmh = safe_get_col('height_mm')
        selected_model = st.selectbox("Panel Model", df[c_model].unique())
        m_data = df[df[c_model] == selected_model].iloc[0]
        db_watts, kg_val = float(m_data[c_watts]), float(m_data[c_weight])
        px_w, px_h = int(m_data[c_pxw]), int(m_data[c_pxh])
        mm_w, mm_h = float(m_data[c_mmw]), float(m_data[c_mmh])
    except Exception as e:
        st.error(f"⚠️ **CSV ERROR:** Could not load 'modelos.csv' or missing columns. Details: {e}")
        st.stop()

    cols_in = st.number_input("Total Cols", 1, 150, 20)
    rows_in = st.number_input("Total Rows", 1, 150, 8)
    
    st.markdown("---")
    st.subheader("🔵 DATA SETUP")
    col_d1, col_d2 = st.columns(2)
    with col_d1: d_div_h = st.number_input("Data Splits (H)", 1, 10, 1, key="data_split_h")
    with col_d2: d_div_v = st.number_input("Data Splits (V)", 1, 10, 1, key="data_split_v")
    
    u_data = st.number_input("Panels/Port", 1, 500, 10, key="data_Panels_port")
    d_dir = st.selectbox("Data Direction", ["Vertical", "Horizontal"], index=1)
    d_start = st.selectbox("Data Start Point", ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right", "Center-Out (Radical Center-Point)"])
    d_style = st.selectbox("Data Wiring Style", ["Snake", "Linear", "Snake (Reset per Port)"])
    show_backup = st.checkbox("Mark Backup Returns", value=True)
    
    # 📍 NUEVA UBICACIÓN: Justo aquí abajo de la casilla de verificación
    view_mode = st.selectbox("Diagram View", ["FRONT VIEW", "REAR VIEW (BACK)"], index=1)

    st.markdown("---")
    st.subheader("🔴 POWER SETUP (SoCa)")
    col_split_1, col_split_2 = st.columns(2)
    with col_split_1: div_h = st.number_input("SoCa Splits (H)", 1, 10, 1)
    with col_split_2: div_v = st.number_input("SoCa Splits (V)", 1, 10, 1)
    v_mode = st.selectbox("Voltage (V)", [110, 120, 208, 220], index=2)
    breaker_size = st.selectbox("Breaker (Amp)", [15, 20], index=1)
    u_pwr = st.number_input("Cabs/Circuit", 1, 100, 15, key="pwr_panels_circuit")
    p_dir = st.selectbox("Power Direction", ["Vertical", "Horizontal"], index=1)
    p_start = st.selectbox("Power Start Point", ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"], index=2)
    p_style = st.selectbox("Power Wiring Style", ["Snake", "Linear", "Snake (Reset per Port)"], index=1)
    # Alerta visual en la app
    if p_style == "Snake":
        st.warning("[WARNING]: 'Snake' routing requires extra-long power jumpers on return rows. ")
        

    st.markdown("---")
    st.subheader("📝 DIAGRAM NOTES")
    data_notes = st.text_area("Data Wiring Notes", placeholder="E.g.: Use ports 1-4 for Main, 5-8 for Redundancy...", height=100)
    pwr_notes = st.text_area("Power Distro Notes", placeholder="E.g.: Phase A for circuits 1-3, Phase B for 4-6...", height=100)
    
# --- 5. CORE CALCULATIONS (Versión Radial Universal) ---

# 1. MOTOR MATEMÁTICO (Fijo con redondeo exacto con math.ceil)
d_step_c = max(1, math.ceil(cols_in / d_div_h))
d_step_r = max(1, math.ceil(rows_in / d_div_v))
step_c = max(1, math.ceil(cols_in / div_h)) # SoCa
step_r = max(1, math.ceil(rows_in / div_v)) # SoCa

# --- 2. GENERACIÓN DE ZONAS DE DATOS ---
z_d = []
# Usamos range sobre el grid de zonas para saber EXACTAMENTE en qué zona estamos parados
for zone_row_idx in range(d_div_v):
    for zone_col_idx in range(d_div_h):
        
        # Calculamos las coordenadas del grid de píxeles basadas en la zona
        c_div = zone_col_idx * d_step_c
        r_div = zone_row_idx * d_step_r
        
        r_end = min(r_div + d_step_r, rows_in)
        c_end = min(c_div + d_step_c, cols_in)
        
        # Lógica Radial Center-Out
        current_d_start = d_start # default
        
        if "Center" in d_start or "Centro" in d_start or "Radical" in d_start:
            # Determinamos si la zona está en la mitad superior o inferior del grid
            is_top_half = zone_row_idx < (d_div_v / 2)
            # Determinamos si la zona está en la mitad izquierda o derecha del grid
            is_left_half = zone_col_idx < (d_div_h / 2)
            
            # Asignamos el punto de inicio de Center-Out específico para esta zona
            if is_top_half: # Zonas Z1 o Z2
                current_d_start = "Bottom-Right" if is_left_half else "Bottom-Left"
            else: # Zonas Z3 o Z4
                current_d_start = "Top-Right" if is_left_half else "Top-Left"
                
        # Appendpts list
        z_d.append(get_pts(c_div, c_end, r_div, r_end, d_dir, current_d_start, d_style, u_data))

# --- 3. GENERACIÓN DE ZONAS DE CORRIENTE (Manteniendo el SoCa Original) ---
z_p = []
# (Esta parte la dejo igual que tu código original, porque el SoCa no suele ser Center-Out Radial)
for r_div in range(0, rows_in, step_r):
    for c_div in range(0, cols_in, step_c):
        r_end = min(r_div + step_r, rows_in)
        c_end = min(c_div + step_c, cols_in)
        z_p.append(get_pts(c_div, c_end, r_div, r_end, p_dir, p_start, p_style, u_pwr))

# --- EL RESTO DEL CÓDIGO SE QUEDA IGUAL ---
total_cabs = cols_in * rows_in
res_w, res_h = cols_in * px_w, rows_in * px_h
# ... (dejas tu código normal para aspect ratio, energía, etc.)

# --- A PARTIR DE AQUÍ DEJAS TU CÓDIGO NORMAL ---
# total_cabs = cols_in * rows_in
# res_w, res_h = cols_in * px_w, rows_in * px_h
# ...

step_c = max(1, math.ceil(cols_in / div_h))
step_r = max(1, math.ceil(rows_in / div_v))
z_p = []
for r_div in range(0, rows_in, step_r):
    for c_div in range(0, cols_in, step_c):
        r_end = min(r_div + step_r, rows_in)
        c_end = min(c_div + step_c, cols_in)
        z_p.append(get_pts(c_div, c_end, r_div, r_end, p_dir, p_start, p_style, u_pwr))

total_cabs = cols_in * rows_in
res_w, res_h = cols_in * px_w, rows_in * px_h
total_w_phys, total_h_phys = ((cols_in * mm_w) / 1000) * dist_conv, ((rows_in * mm_h) / 1000) * dist_conv
screen_weight_final = (total_cabs * kg_val) * u_conv
amps_per_circuit = u_pwr * (db_watts / v_mode)
total_amps = total_cabs * (db_watts / v_mode)
px_per_port = px_w * px_h * u_data

gcd_val = math.gcd(res_w, res_h)
aspect_w = res_w // gcd_val
aspect_h = res_h // gcd_val
ratio_dec = res_w / res_h
aspect_ratio_str = f"{aspect_w}:{aspect_h} ({ratio_dec:.2f}:1)"

safety_limit = 18.0 if breaker_size == 20 else 14.0

total_amps_global = 0
phase_loads = {"Phase X": 0, "Phase Y": 0, "Phase Z": 0}
phases = ["Phase X", "Phase Y", "Phase Z"]
p_idx = 0

for zone in z_p:
    for j in range(0, len(zone), u_pwr):
        n_c = len(zone[j : j + u_pwr])
        curr_amps = (n_c * db_watts) / v_mode
        total_amps_global += curr_amps
        phase_loads[phases[p_idx % 3]] += curr_amps
        p_idx += 1

# --- 6. USER INTERFACE ---
st.title(job_name.upper())
st.write(f"📍 {venue_name} | 👷 Lead: {lead_tech}")

st.markdown("### 📊 TECHNICAL REQUIREMENTS")

# --- FILA 1: ENERGÍA Y SEÑAL ---
m1, m2, m3, m4, m5, m6 = st.columns(6)

cargas = list(phase_loads.values())
desbalance_maximo = max(cargas) - min(cargas)

if desbalance_maximo > 5.0:
    balance_label = f"-⚠️ Unbalanced (Δ {desbalance_maximo:.1f}A)"
else:
    balance_label = "✅ Balanced"

# 1. Resolución de la pantalla y Aspect Ratio
m1.metric("Resolution (px)", f"{res_w} x {res_h}", f"{res_w * res_h:,} Total px")
m1.caption(f"📐 **Ratio:** {aspect_ratio_str}")

# 2. Puertos de Datos
m2.metric("Data Ports", int(-(-total_cabs // u_data)), f"{px_per_port:,} px/max")

# 3. Circuitos de Corriente
m3.metric("AC Circuits", p_idx, f"Cabs/Circ: {u_pwr}") 

# 4. Consumo Total
m4.metric("Total Load (3-Ph)", f"{total_amps_global:.2f} A", "Consumption")

# 5. Promedio por Fase y Balance
m5.metric("Avg Load / Ph", f"{total_amps_global / 3:.2f} A", balance_label)

# 6. Voltaje y Breaker
m6.metric("Volts / Breaker", f"{v_mode}V", f"{breaker_size}A Breaker")

st.markdown("---")

# --- RECOMENDACIÓN DE PROCESADORES ---
st.markdown("#### 🎛️ PROCESSOR RECOMMENDATIONS")

# 1. Tu inventario de empresa (Ordenado de mayor a menor)
inventory = {
    "Novastar H5 (Modular)": {"max_px": 39000000, "ports": 60}, 
    "Novastar VX16s": {"max_px": 10400000, "ports": 16},
    "Novastar MX40 Pro": {"max_px": 8800000, "ports": 20},
    "Novastar MCTRL4K": {"max_px": 8800000, "ports": 16},
    "NovaPro HD": {"max_px": 2350000, "ports": 4},
    "Novastar MCTRL660 PRO": {"max_px": 2300000, "ports": 6},
    "Novastar MCTRL600": {"max_px": 2300000, "ports": 4}
}

total_pixels = res_w * res_h
req_ports = int(-(-total_cabs // u_data)) # Redondeo hacia arriba para sacar el total de puertos

valid_procs = []
for proc, specs in inventory.items():
    if specs["max_px"] >= total_pixels and specs["ports"] >= req_ports:
        valid_procs.append(f"- **{proc}** (Soporta {specs['max_px']:,} px / {specs['ports']} puertos max)")

if valid_procs:
    st.success("✅ **Compatible Processors found in inventory:**")
    st.markdown("\n".join(valid_procs))
else:
    st.error(f"🚨 **Overload:** No single processor in inventory can handle {total_pixels:,} px and {req_ports} ports. You will need multiple synced units!")


st.markdown("---")

# --- FILA 2: ESPECIFICACIONES FÍSICAS ---
st.markdown("#### 📏 PHYSICAL SPECIFICATIONS")
p1, p2, p3 = st.columns(3)

# Cálculos fijos de conversiones
w_m = (cols_in * mm_w) / 1000
h_m = (rows_in * mm_h) / 1000
w_ft = w_m * 3.28084
h_ft = h_m * 3.28084
peso_kg = total_cabs * kg_val
peso_lbs = peso_kg * 2.20462

# --- LÓGICA DE INTERCAMBIO SEGÚN TU BARRA LATERAL ---
# Verificamos si tu sistema elegido es el Métrico (kg)
if u_label == "kg":
    # El Métrico va en GRANDE, el Imperial en la ETIQUETA AZUL
    dim_main = f"{w_m:.2f}m x {h_m:.2f}m"
    peso_main = f"{peso_kg:.1f} kg"
    
    dim_sub = f"{w_ft:.2f}ft x {h_ft:.2f}ft"
    peso_sub = f"{peso_lbs:.1f} lbs"
else:
    # El Imperial va en GRANDE, el Métrico en la ETIQUETA AZUL
    dim_main = f"{w_ft:.2f}ft x {h_ft:.2f}ft"
    peso_main = f"{peso_lbs:.1f} lbs"
    
    dim_sub = f"{w_m:.2f}m x {h_m:.2f}m"
    peso_sub = f"{peso_kg:.1f} kg"

# Función Pro Badge (dejamos tu azul fuerte #0D6EFD que elegiste)
def pro_badge_metric(label, main_val, sub_val):
    return f"""
    <div style="font-family: sans-serif; margin-bottom: 10px;">
        <p style="font-size: 0.9rem; color: #a0aec0; margin: 0 0 5px 0;">{label}</p>
        <p style="font-size: 2.2rem; font-weight: 700; color: #ffffff; margin: 0 0 12px 0; line-height: 1;">{main_val}</p>
        <span style="font-size: 0.85rem; font-weight: 600; color: #ffffff; background-color: #0D6EFD; padding: 4px 10px; border-radius: 6px; box-shadow: 0px 2px 4px rgba(0,0,0,0.3);">
            {sub_val}
        </span>
    </div>
    """

# Inyectamos el HTML en las 3 columnas usando las variables dinámicas
with p1:
    st.markdown(pro_badge_metric("Total Panels", f"{total_cabs} Panels", f"Grid: {cols_in}x{rows_in}"), unsafe_allow_html=True)
with p2:
    st.markdown(pro_badge_metric("Screen Dimensions", dim_main, dim_sub), unsafe_allow_html=True)
with p3:
    st.markdown(pro_badge_metric("Total Weight", peso_main, peso_sub), unsafe_allow_html=True)

st.markdown("---")

col_diag1, col_diag2 = st.columns(2)
with col_diag1:
    st.subheader("1. Data Wiring Map")
    img_d = draw_map(cols_in, rows_in, z_d, u_data, ui_mode, True, show_backup)
    st.image(img_d, use_container_width=True)
    if px_per_port > 650000: st.error(f"🚨 **DATA OVERLOAD:** {px_per_port:,} px exceeds limit.")
    else: st.success(f"✅ Data safe: {len(z_d)} signal runs detected.")

with col_diag2:
    st.subheader("2. Power / SoCa Distribution")
    img_p = draw_map(cols_in, rows_in, z_p, u_pwr, ui_mode, False, False)
    st.image(img_p, use_container_width=True)
    if amps_per_circuit > safety_limit: st.error(f"🔥 **POWER OVERLOAD:** {amps_per_circuit:.2f}A exceeds limit of {safety_limit}A.")
    else: st.success(f"✅ Power load safe for {breaker_size}A breaker.")

st.markdown("---")
st.subheader("📋 Power Phase Balance")
c_izq, c_cen, c_der = st.columns([1, 2, 1])
with c_cen:
    phase_summary = [{"Phase": k, "Estimated Load": f"{v:.2f} A"} for k, v in phase_loads.items()]
    st.table(pd.DataFrame(phase_summary).set_index("Phase"))

st.markdown("---")

# --- 7. PDF EXPORT FUNCTION ---
def export_pdf(data_notes, pwr_notes, z_d, z_p, view_mode):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    watermark_text = f"CONFIDENTIAL & PROPRIETARY  |  GENERATED: {now_str}  |  MVI ENGINEERING V{VERSION}"

    class PDFReport(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, watermark_text, align='C')

    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf_total_amps = 0
    pdf_phase_loads = {"Phase X": 0, "Phase Y": 0, "Phase Z": 0}
    pdf_phases = ["Phase X", "Phase Y", "Phase Z"]
    pdf_phase_idx = 0

    def add_page_template(pdf_obj, title_sheet):
        pdf_obj.add_page() 
        
        logo_filename = "logo_mvi.png"
        if os.path.exists(logo_filename):
            try: pdf_obj.image(logo_filename, 10, 10, 35)
            except: pass
            
        pdf_obj.set_xy(50, 12) 
        pdf_obj.set_font("Arial", "B", 14) 
        pdf_obj.set_text_color(40, 40, 40)
        
        # Limitamos a ~40 letras (aprox 2 renglones completos) para mantener todo bajo control
        safe_job_name = job_name[:40] + "..." if len(job_name) > 40 else job_name
        full_title = f"{title_sheet}: {safe_job_name.upper()}"
        pdf_obj.multi_cell(150, 6, full_title, align="R") 
        
        current_y = pdf_obj.get_y()
        
        pdf_obj.set_xy(50, current_y + 1) 
        pdf_obj.set_font("Arial", "", 10) 
        pdf_obj.set_text_color(120, 120, 120)
        pdf_obj.multi_cell(150, 5, f"Venue: {venue_name[:20]}   |   Lead: {lead_tech[:20]}", align="R")
        
        # Etiqueta de FRONT/REAR VIEW acomodada justo debajo del Venue
        pdf_obj.set_y(pdf_obj.get_y() + 2)
        if "FRONT" in view_mode:
            pdf_obj.set_fill_color(63, 185, 80) # Verde
        else:
            pdf_obj.set_fill_color(248, 81, 73) # Rojo
            
        pdf_obj.set_text_color(255, 255, 255)
        pdf_obj.set_font("Arial", "B", 11)
        pdf_obj.set_x(155) 
        pdf_obj.cell(45, 6, f" {view_mode} ", border=0, ln=True, align="C", fill=True)
        
        # --- EL ANCLA (FIX MAESTRO) ---
        # Clavamos el inicio de la caja de información en Y=46. 
        # Esto asegura que terminará exactamente en Y=63 y tu diagrama empezará en Y=65. Cero empalmes.
        pdf_obj.set_y(46) 
        
        pdf_obj.set_fill_color(44, 62, 80) 
        pdf_obj.rect(10, pdf_obj.get_y(), 190, 1.5, 'F') 
        pdf_obj.set_y(pdf_obj.get_y() + 1.5)
        pdf_obj.set_fill_color(248, 248, 250)
        pdf_obj.set_text_color(40, 40, 40)
        pdf_obj.set_font("Arial", "B", 10)
        pdf_obj.cell(190, 8, f"  MODEL: {selected_model}    |    RES: {res_w}x{res_h}px    |    ASPECT: {aspect_ratio_str}", ln=True, align="C", fill=True)
        pdf_obj.set_text_color(80, 80, 80)
        pdf_obj.set_font("Arial", "", 9)
        pdf_obj.cell(190, 7, f"  SIZE: {w_m:.2f}x{h_m:.2f}m ({w_ft:.2f}x{h_ft:.2f}ft)  |  WEIGHT: {peso_kg:.1f}kg ({peso_lbs:.1f}lbs)  |  LOAD: {amps_per_circuit:.2f}A/Circ", ln=True, align="C", fill=True)
        pdf_obj.set_fill_color(220, 220, 220)
        pdf_obj.rect(10, pdf_obj.get_y(), 190, 0.5, 'F')
        
        pdf_obj.set_text_color(0, 0, 0) 

    add_page_template(pdf, "1. DATA WIRING MAP")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as t1:
        img_d_pdf = draw_map(cols_in, rows_in, z_d, u_data, "PDF_MODE", True, show_backup)
        img_d_pdf.save(t1.name)
        pdf.image(t1.name, x=15, y=65, w=180) 
    
    pdf.set_y(195) 
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(88, 166, 255)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " DATA LOAD SUMMARY (BY PORT)", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(60, 8, "Port ID", border=1)
    pdf.cell(60, 8, "Panels", border=1)
    pdf.cell(70, 8, "Total Port Pixels", border=1, ln=True)
    pdf.set_font("Courier", "", 10)
    port_count = 1
    for zone in z_d:
        for j in range(0, len(zone), u_data):
            cabs_in_this_port = len(zone[j : j + u_data])
            px_this_port = cabs_in_this_port * px_w * px_h
            pdf.cell(60, 8, f"Port P{port_count}", border=1)
            pdf.cell(60, 8, f"{cabs_in_this_port} Cabs", border=1)
            pdf.cell(70, 8, f"{px_this_port:,} px", border=1, ln=True)
            port_count += 1

    if data_notes.strip():
        pdf.ln(3)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "NOTES:", ln=True)
        pdf.set_font("Courier", "", 9)
        pdf.multi_cell(0, 5, data_notes, border=1)

    add_page_template(pdf, "2. POWER / SOCA DISTRO")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as t2:
        img_p_pdf = draw_map(cols_in, rows_in, z_p, u_pwr, "PDF_MODE", False, False)
        img_p_pdf.save(t2.name)
        pdf.image(t2.name, x=15, y=65, w=180)

    pdf.set_y(195)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(248, 81, 73)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " POWER LOAD SUMMARY (6-WAY SOCAPEX UNITS)", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    
    ac_count = 1
    s_id = 1
    for zone in z_p: 
        for k in range(0, len(zone), u_pwr * 6):
            pdf.set_font("Courier", "B", 9)
            pdf.cell(45, 7, "Circuit ID", border=1)
            pdf.cell(45, 7, "Panels", border=1)
            pdf.cell(50, 7, "Source SoCa", border=1)
            pdf.cell(50, 7, "Est. Load (Amps)", border=1, ln=True)
            
            s_amps = 0
            c_in_s = 1
            s_chunk = zone[k : k + (u_pwr * 6)]
            
            pdf.set_font("Courier", "", 9)
            for j in range(0, len(s_chunk), u_pwr):
                n_c = len(s_chunk[j : j + u_pwr])
                a = (n_c * db_watts) / v_mode
                s_amps += a
                pdf_total_amps += a
                current_phase = pdf_phases[pdf_phase_idx % 3]
                pdf_phase_loads[current_phase] += a
                pdf_phase_idx += 1
                
                pdf.cell(45, 7, f"AC{ac_count} (Ch {c_in_s})", border=1)
                pdf.cell(45, 7, f"{n_c} Cabs", border=1)
                pdf.cell(50, 7, f"SoCa {s_id}", border=1)
                pdf.cell(50, 7, f"{a:.2f} A", border=1, ln=True)
                
                c_in_s += 1
                ac_count += 1
            
            pdf.set_font("Courier", "B", 9)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(140, 7, f" >> TOTAL SOCA {s_id} LOAD:", border=1, align="R", fill=True)
            pdf.cell(50, 7, f"{s_amps:.2f} A", border=1, ln=True, fill=True)
            pdf.ln(5)
            s_id += 1

    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " TOTAL POWER REQUIREMENTS SUMMARY", ln=True, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(95, 8, "Description", border=1)
    pdf.cell(95, 8, "Total Amperage", border=1, ln=True)
    pdf.set_font("Courier", "", 10)
    pdf.cell(95, 8, "TOTAL SCREEN CONSUMPTION", border=1)
    pdf.cell(95, 8, f"{pdf_total_amps:.2f} A", border=1, ln=True)
    for phase, load in pdf_phase_loads.items():
        pdf.cell(95, 8, f"ESTIMATED LOAD {phase}", border=1)
        pdf.cell(95, 8, f"{load:.2f} A", border=1, ln=True)

    if pwr_notes.strip():
        pdf.ln(3)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "NOTES:", ln=True)
        pdf.set_font("Courier", "", 9)
        pdf.multi_cell(0, 5, pwr_notes, border=1)

    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        # Si estamos en Windows (versión antigua de FPDF devuelve texto)
        return pdf_out.encode('latin-1')
    else:
        # Si estamos en la Raspberry (versión nueva de FPDF devuelve bytes)
        return bytes(pdf_out)

# --- 9. EXPORT PDF BUTTON (AFUERA, HASTA ABAJO) ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if z_d and z_p:
        # Inyectar advertencia en las notas del PDF
        final_pwr_notes = pwr_notes
        if p_style == "Snake":
            # 👇 AHORA EN INGLÉS
            alerta_snake = "[WARNING]: 'Snake' routing requires extra-long power jumpers on return rows. "
            final_pwr_notes = alerta_snake + final_pwr_notes
            
        st.download_button(
            label="📄 Generate PDF Report",
            data=export_pdf(data_notes, final_pwr_notes, z_d, z_p, view_mode), 
            file_name=f"MVI_Report_{job_name[:15].replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        