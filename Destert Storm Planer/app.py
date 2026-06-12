import streamlit as st
import pandas as pd
import json
from PIL import Image, ImageDraw, ImageFont
import io
from streamlit_sortables import sort_items

# Seitenkonfiguration (Muss ganz oben stehen)
st.set_page_config(page_title="Last War: Desert Storm Planner", layout="wide")

# -----------------------------------------------------------------------------
# 1. INITIALISIERUNG DER SESSION STATES
# -----------------------------------------------------------------------------
if "players_A" not in st.session_state:
    st.session_state.players_A = []
if "players_B" not in st.session_state:
    st.session_state.players_B = []
if "assignments_A" not in st.session_state:
    st.session_state.assignments_A = {}
if "assignments_B" not in st.session_state:
    st.session_state.assignments_B = {}

st.title("⚔️ Last War: Survival - Desert Storm Planner")
st.write("Plane deine Allianz-Teams, verteile sie strategisch und generiere taktische Roster-Bilder.")

# -----------------------------------------------------------------------------
# 2. INFORMATIONSTAB (REGELN IN EN / DE)
# -----------------------------------------------------------------------------
tab_info, tab_A, tab_B = st.tabs(["ℹ️ Rules / Regeln", "👥 Group A", "👥 Group B"])

with tab_info:
    col_en, col_de = st.columns(2)
    
    with col_en:
        st.subheader("🇺🇸 Assignment Rules")
        st.markdown("""
        The algorithm automatically sorts and distributes players based on their **Hero Power** and **Commitment Status**.
        
        ### 🔝 Priority & Logic
        * **Commitment First:** Players with `Commitment = Yes` are always prioritized over `Maybe`, regardless of power.
        * **Power Balancing:** Buildings are filled by pairing stronger players with weaker players to balance lanes.
        """)
        
        rules_df_en = pd.DataFrame({
            "Building": ["Jumper", "Info Center", "Tech Center", "Hospital I", "Hospital II", "Hospital III", "Hospital IV", "Oil Refinery I", "Oil Refinery II", "Backup / Reserve"],
            "Slots / Logic": [
                "Top 4 strongest players (Min. 2 if low player count)",
                "Rank #1 and Rank #4",
                "Rank #2 and Rank #3",
                "Rank #5 and Rank #11",
                "Rank #6 and Rank #12",
                "Rank #7 and Rank #13",
                "Rank #8 and Rank #14",
                "Rank #9 and Rank #15",
                "Rank #10 and Rank #16",
                "All remaining players who didn't fit into tactical positions"
            ]
        })
        st.table(rules_df_en)

    with col_de:
        st.subheader("🇩🇪 Einteilungsregeln")
        st.markdown("""
        Der Algorithmus sortiert und verteilt die Spieler automatisch basierend auf ihrer **Helden-Kampfkraft** und ihrem **Commitment-Status**.
        
        ### 🔝 Priorität & Logik
        * **Commitment zuerst:** Spieler mit `Commitment = Yes` werden immer vor `Maybe` priorisiert, unabhängig von ihrer Kampfkraft.
        * **Stärkenausgleich:** Gebäude werden so besetzt, dass stärkere Spieler mit schwächeren Spielern gemischt werden.
        """)
        
        rules_df_de = pd.DataFrame({
            "Gebäude": ["Jumper", "Info Center", "Tech Center", "Hospital I", "Hospital II", "Hospital III", "Hospital IV", "Oil Refinery I", "Oil Refinery II", "Reserve"],
            "Slots / Logik": [
                "Top 4 stärkste Spieler (Mind. 2 bei geringer Spieleranzahl)",
                "Platz #1 und Platz #4",
                "Platz #2 und Platz #3",
                "Platz #5 und Platz #11",
                "Platz #6 und Platz #12",
                "Platz #7 und Platz #13",
                "Platz #8 und Platz #14",
                "Platz #9 und Platz #15",
                "Platz #10 und Platz #16",
                "Alle restlichen Spieler, die in kein Gebäude gepasst haben"
            ]
        })
        st.table(rules_df_de)

# -----------------------------------------------------------------------------
# 3. DATEN-MANAGEMENT (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.header("💾 Data Management")

config_data = {
    "players_A": st.session_state.players_A,
    "players_B": st.session_state.players_B
}
config_json = json.dumps(config_data, indent=4)
st.sidebar.download_button(
    label="📥 Download Config File",
    data=config_json,
    file_name="desert_storm_config.json",
    mime="application/json"
)

uploaded_file = st.sidebar.file_uploader("📤 Upload Config File", type=["json"])
if uploaded_file is not None:
    try:
        loaded_data = json.load(uploaded_file)
        st.session_state.players_A = loaded_data.get("players_A", [])
        st.session_state.players_B = loaded_data.get("players_B", [])
        st.sidebar.success("Configuration loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")

# -----------------------------------------------------------------------------
# 4. SPIELER-EINGABEBEREICH (FORMULARE & BULK)
# -----------------------------------------------------------------------------
def player_input_section(group_key):
    st.subheader(f"Manage Players for {group_key}")
    
    with st.form(f"add_player_{group_key}", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 2, 2])
        name = col1.text_input("Player Name")
        power = col2.number_input("Hero Power (e.g., in Millions)", min_value=0.0, step=0.1, format="%.2f")
        commitment = col3.selectbox("Commitment", ["Yes", "Maybe"])
        
        submitted = st.form_submit_button("Add Player")
        if submitted and name:
            new_player = {"name": name.strip(), "power": power, "commitment": commitment}
            if group_key == "Group A":
                st.session_state.players_A.append(new_player)
            else:
                st.session_state.players_B.append(new_player)
            st.success(f"Added {name}!")
            st.rerun()

    with st.expander("📝 Bulk Import (Text Copy-Paste)"):
        bulk_text = st.text_area("Format: Name, Power, Commitment (One player per line)", 
                                 placeholder="Player1, 25.5, Yes\nPlayer2, 22.1, Maybe", key=f"bulk_{group_key}")
        if st.button("Load Bulk Data", key=f"btn_bulk_{group_key}"):
            lines = bulk_text.strip().split("\n")
            for line in lines:
                if "," in line:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 3:
                        try:
                            p_dict = {"name": parts[0], "power": float(parts[1]), "commitment": parts[2]}
                            if group_key == "Group A": st.session_state.players_A.append(p_dict)
                            else: st.session_state.players_B.append(p_dict)
                        except: pass
            st.success("Bulk data loaded!")
            st.rerun()

    current_players = st.session_state.players_A if group_key == "Group A" else st.session_state.players_B
    if current_players:
        df = pd.DataFrame(current_players)
        st.dataframe(df.sort_values(by="power", ascending=False), use_container_width=True)
        if st.button(f"🗑️ Clear {group_key} List"):
            if group_key == "Group A": st.session_state.assignments_A = {}
            else: st.session_state.assignments_B = {}
            if group_key == "Group A": st.session_state.players_A = []
            else: st.session_state.players_B = []
            st.rerun()
    else:
        st.info("No players registered yet.")

with tab_A:
    player_input_section("Group A")
with tab_B:
    player_input_section("Group B")

# -----------------------------------------------------------------------------
# 5. ALGORITHMUS: WÜSTENSTURM-BERECHNUNG
# -----------------------------------------------------------------------------
def plan_group(players):
    if not players:
        return {}
    
    yes_players = sorted([p for p in players if p["commitment"] == "Yes"], key=lambda x: x["power"], reverse=True)
    maybe_players = sorted([p for p in players if p["commitment"] == "Maybe"], key=lambda x: x["power"], reverse=True)
    
    sorted_pool = yes_players + maybe_players
    total_players = len(sorted_pool)
    
    assignments = {
        "Hospital I": [], "Hospital II": [], "Hospital III": [], "Hospital IV": [],
        "Tech Center": [], "Info Center": [], 
        "Oil Refinery I": [], "Oil Refinery II": [],
        "Jumper": [], "Reserve": []
    }
    
    if total_players == 0:
        return assignments

    jumper_count = 4 if total_players >= 16 else (2 if total_players >= 2 else total_players)
    assignments["Jumper"] = sorted_pool[:jumper_count]
    
    rest = sorted_pool[jumper_count:]
    
    building_slots = {
        "Info Center": [0, 3],
        "Tech Center": [1, 2],
        "Hospital I": [4, 10],
        "Hospital II": [5, 11],
        "Hospital III": [6, 12],
        "Hospital IV": [7, 13],
        "Oil Refinery I": [8, 14],
        "Oil Refinery II": [9, 15],
    }
    
    assigned_indices = set()
    for building, slots in building_slots.items():
        for slot_idx in slots:
            if slot_idx < len(rest):
                assignments[building].append(rest[slot_idx])
                assigned_indices.add(slot_idx)
                
    for idx, p in enumerate(rest):
        if idx not in assigned_indices:
            assignments["Reserve"].append(p)
            
    return assignments

st.write("---")
if st.button("🚀 Plan Desert Storm", type="primary"):
    st.session_state.assignments_A = plan_group(st.session_state.players_A)
    st.session_state.assignments_B = plan_group(st.session_state.players_B)
    st.success("Calculated strategic lane setups successfully!")

# -----------------------------------------------------------------------------
# 6. DRAG & DROP STRATEGIE-BOARD (STABILISIERTE VERSION GEGEN DATENVERLUST)
# -----------------------------------------------------------------------------
def display_and_adjust_assignments(group_key):
    assignments = st.session_state.assignments_A if group_key == "Group A" else st.session_state.assignments_B
    
    if not assignments:
        st.info(f"Please click 'Plan Desert Storm' to create the initial setup for {group_key}.")
        return

    st.subheader(f"🖱️ Interactive Drag & Drop Board - {group_key}")
    st.caption("Ziehe Spieler in andere Gebäude oder ändere die Reihenfolge. Das Bild wird basierend darauf erstellt.")

    sortable_data = []
    for building, players in assignments.items():
        player_strings = [
            f"{p['name']} ({p['power']}M){' ❓' if p['commitment'] == 'Maybe' else ''}" 
            for p in players
        ]
        sortable_data.append({"header": building, "items": player_strings})

    # Drag & Drop Widget aufrufen
    updated_data = sort_items(
        sortable_data, 
        multi_containers=True, 
        direction="vertical", 
        key=f"sortable_board_{group_key}"
    )

    # GUARD LOGIC: Verhindert das Leeren beim Rerun durch den "Generate Image"-Klick
    if updated_data:
        temp_assignments = {}
        all_players = st.session_state.players_A if group_key == "Group A" else st.session_state.players_B
        found_any_player = False
        
        for section in updated_data:
            building_name = section["header"]
            item_list = section["items"]
            assigned_players = []
            
            for item_str in item_list:
                # Extrahiere sauber den reinen Namen vor dem String-Zusatz " ("
                extracted_name = item_str.split(" (")[0].strip()
                original_player = next((p for p in all_players if p["name"] == extracted_name), None)
                if original_player:
                    assigned_players.append(original_player)
                    found_any_player = True
            
            temp_assignments[building_name] = assigned_players
        
        # WICHTIG: Nur in den echten State schreiben, wenn die Komponente valide Daten geliefert hat
        if found_any_player:
            if group_key == "Group A":
                st.session_state.assignments_A = temp_assignments
            else:
                st.session_state.assignments_B = temp_assignments

col_col1, col_col2 = st.columns(2)
with col_col1:
    display_and_adjust_assignments("Group A")
with col_col2:
    display_and_adjust_assignments("Group B")

# -----------------------------------------------------------------------------
# 7. PIL GRAFIKGENERATOR (ÜBERLAPPUNGEN & SYMBOLE KORRIGIERT)
# -----------------------------------------------------------------------------
def generate_tactical_image(group_name, assignments):
    width = 900
    
    # Schriftarten definieren
    try:
        font_alliance = ImageFont.truetype("arial.ttf", 60)
        font_sub = ImageFont.truetype("arial.ttf", 24)
        font_b_title = ImageFont.truetype("arial.ttf", 22)
        font_b_sub = ImageFont.truetype("arial.ttf", 16)
        font_p_text = ImageFont.truetype("arial.ttf", 20)
    except:
        font_alliance = font_sub = font_b_title = font_b_sub = font_p_text = ImageFont.load_default()

    # --- HILFSFUNKTION FÜR DYNAMISCHE HÖHENBERECHNUNG ---
    # Berechnet, wie hoch eine Karte sein muss, basierend auf der Spieleranzahl
    def get_card_height(players):
        base_header_space = 105 # Platz für Titel, Subtitel und "Members:"
        player_count = max(1, len(players)) # Mindestens Platz für eine "Leer"-Zeile oder Infos
        player_space = player_count * 32    # Jede Spielerzeile benötigt 32px
        padding_bottom = 20
        return base_header_space + player_space + padding_bottom

    # Farbschemata
    themes = {
        "Group A": {"bg": "#0a110d", "border": "#19543e", "header": "#48ffb0"},
        "Group B": {"bg": "#0a0f16", "border": "#1a3a5f", "header": "#4da6ff"}
    }
    theme = themes[group_name]

    # --- 1. GEBÄUDE-GRID POSITIONIERUNG & HÖHEN-ANALYSE ---
    start_x = 45
    h_width = 190
    h_gap = 18
    mid_width = 399
    
    # Zeile 1: Krankenhäuser
    hospitals = [("Hospital I", "STEELHEARTS"), ("Hospital II", "UNSHAKABLES"), ("Hospital III", "LIFEKEEPERS"), ("Hospital IV", "GUARDIANS")]
    y_top = 220
    
    max_h_height = 0
    hospital_heights = []
    for name, _ in hospitals:
        h = get_card_height(assignments.get(name, []))
        hospital_heights.append(h)
        if h > max_h_height:
            max_h_height = h
            
    # Zeile 2: Strategic Centers (Tech / Info)
    y_mid = y_top + max_h_height + 25
    h_tech = get_card_height(assignments.get("Tech Center", []))
    h_info = get_card_height(assignments.get("Info Center", []))
    max_mid_height = max(h_tech, h_info)
    
    # Zeile 3: Raffinerien
    y_ref = y_mid + max_mid_height + 25
    h_ref1 = get_card_height(assignments.get("Oil Refinery I", []))
    h_ref2 = get_card_height(assignments.get("Oil Refinery II", []))
    max_ref_height = max(h_ref1, h_ref2)
    
    # Zeile 4: Jumper
    y_j = y_ref + max_ref_height + 25
    h_jumper = get_card_height(assignments.get("Jumper", []))
    
    # Zeile 5: Reserve-Text Umbruch Logik & Höhe
    all_res_players = assignments.get("Reserve", [])
    res_strings = [f"{p['name']}{' (?)' if p['commitment'] == 'Maybe' else ''}" for p in all_res_players]
    
    lines = []
    if res_strings:
        current_line = ""
        for s in res_strings:
            test_line = s if not current_line else current_line + "   |   " + s
            if len(test_line) < 80: 
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = s
        lines.append(current_line)
    else:
        lines = ["No backup units assigned."]
        
    reserve_box_height = 50 + (len(lines) * 32) + 20
    y_r_top = y_j + h_jumper + 40
    y_r_bottom = y_r_top + reserve_box_height
    
    # Gesamthöhe des Bildes komplett dynamisch zusammensetzen
    dynamic_height = y_r_bottom + 110
    
    # --- 2. BILD ERSTELLEN UND ZEICHNEN ---
    img = Image.new("RGB", (width, int(dynamic_height)), color=theme["bg"])
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((width//2, 60), "LAST WAR", fill="#ffffff", font=font_alliance, anchor="mm")
    draw.text((width//2, 120), f"DESERT STORM SETUP - {group_name.upper()}", fill=theme["header"], font=font_sub, anchor="mm")
    draw.text((width//2, 155), "WE STAND UNITED, STRIKE HARD, AND GIVE NO GROUND.", fill="#aaaaaa", font=font_sub, anchor="mm")
    draw.line([(50, 190), (width - 50, 190)], fill="#444444", width=3)
    
    # Standardisierte Card-Zeichen-Funktion mit dynamischer Endhöhe y2
    def draw_card(x1, y1, x2, y2, title, subtitle, subtitle_color, players):
        draw.rectangle([(x1, y1), (x2, y2)], outline=theme["border"], width=3, fill="#11151c")
        draw.line([(x1, y1 + 60), (x2, y1 + 60)], fill=theme["border"], width=2)
        
        draw.text((x1 + 15, y1 + 8), title, fill="#ffffff", font=font_b_title)
        draw.text((x1 + 15, y1 + 36), f'"{subtitle}"', fill=subtitle_color, font=font_b_sub)
        draw.text((x1 + 15, y1 + 75), "Members:", fill="#777777", font=font_b_sub)
        
        curr_y = y1 + 105
        if not players:
            draw.text((x1 + 15, curr_y), "• Empty", fill="#555555", font=font_p_text)
        else:
            for p in players:
                maybe_suffix = " (?)" if p["commitment"] == "Maybe" else ""
                p_display = f"• {p['name']}{maybe_suffix}"
                text_color = "#ffffff" if p["commitment"] == "Yes" else "#888888"
                draw.text((x1 + 15, curr_y), p_display, fill=text_color, font=font_p_text)
                curr_y += 32

    # Krankenhäuser zeichnen (Nutzen alle die maximale Zeilenhöhe für symmetrische Optik der Reihe)
    for i, (name, sub) in enumerate(hospitals):
        bx1 = start_x + i * (h_width + h_gap)
        draw_card(bx1, y_top, bx1 + h_width, y_top + max_h_height, name, sub, "#4caf50", assignments.get(name, []))
        
    # Centers zeichnen
    draw_card(start_x, y_mid, start_x + mid_width, y_mid + max_mid_height, "Tech Center", "THE SUPPLIERS", "#ffb300", assignments.get("Tech Center", []))
    draw_card(start_x + mid_width + 12, y_mid, width - start_x, y_mid + max_mid_height, "Info Center", "THE SCOUTS", "#ffb300", assignments.get("Info Center", []))

    # Raffinerien zeichnen
    draw_card(start_x, y_ref, start_x + mid_width, y_ref + max_ref_height, "Oil Refinery I", "EXTRACTORS A", "#00bcd4", assignments.get("Oil Refinery I", []))
    draw_card(start_x + mid_width + 12, y_ref, width - start_x, y_ref + max_ref_height, "Oil Refinery II", "EXTRACTORS B", "#00bcd4", assignments.get("Oil Refinery II", []))

    # Jumper zeichnen
    draw_card(start_x, y_j, width - start_x, y_j + h_jumper, "JUMPER SQUAD", "THE ASSAULT SQUAD", "#f44336", assignments.get("Jumper", []))

    # --- RESERVE BOX ZEICHNEN ---
    draw.rectangle([(start_x, y_r_top), (width - start_x, y_r_bottom)], outline=theme["border"], width=3, fill="#11151c")
    draw.text((start_x + 15, y_r_top + 15), "RESERVE UNITS", fill="#ffffff", font=font_b_title)
    
    curr_y_res = y_r_top + 55
    for line in lines:
        draw.text((start_x + 15, curr_y_res), line, fill="#aaaaaa", font=font_p_text)
        curr_y_res += 32

    # --- FOOTER MOTTO ---
    footer_y = y_r_bottom + 55
    draw.text((width//2, footer_y), "WE HOLD THE LINE AND LEAVE THE FIELD AS VICTORS!", fill="#ffffff", font=font_sub, anchor="mm")

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()# -----------------------------------------------------------------------------
# 8. BILDER-EXPORT UI-BEREICH
# -----------------------------------------------------------------------------
st.write("---")
st.subheader("🖼️ Export Roster Visuals")

if st.button("🖼️ Generate Tactical Image", type="secondary"):
    if st.session_state.assignments_A or st.session_state.assignments_B:
        col_img1, col_img2 = st.columns(2)
        
        if st.session_state.assignments_A:
            with col_img1:
                st.write("**Group A Tactical Graphic:**")
                img_data_A = generate_tactical_image("Group A", st.session_state.assignments_A)
                st.image(img_data_A)
                st.download_button("💾 Download Image A", data=img_data_A, file_name="Desert_Storm_Group_A.png", mime="image/png")
                
        if st.session_state.assignments_B:
            with col_img2:
                st.write("**Group B Tactical Graphic:**")
                img_data_B = generate_tactical_image("Group B", st.session_state.assignments_B)
                st.image(img_data_B)
                st.download_button("💾 Download Image B", data=img_data_B, file_name="Desert_Storm_Group_B.png", mime="image/png")
    else:
        st.warning("Bitte berechne zuerst ein Layout mit 'Plan Desert Storm'.")