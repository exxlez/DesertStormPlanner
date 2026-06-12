import streamlit as st
import pandas as pd
import json
from PIL import Image, ImageDraw, ImageFont
import io

st.set_page_config(page_title="Last War: Desert Storm Planner", layout="wide")

# -----------------------------------------------------------------------------
# 1. INITIALIZATION & CACHE MANAGEMENT
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
st.write("Plan your alliance teams, distribute them strategically, and generate tactical roster images.")

# -----------------------------------------------------------------------------
# 2. INFORMATION TAB (RULES IN EN / DE)
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
# 3. IMPORT / EXPORT CONFIGURATION
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
# 4. PLAYER INPUT SECTION
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
            new_player = {"name": name, "power": power, "commitment": commitment}
            if group_key == "Group A":
                st.session_state.players_A.append(new_player)
            else:
                st.session_state.players_B.append(new_player)
            st.success(f"Added {name}!")

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
            st.rerun()

    current_players = st.session_state.players_A if group_key == "Group A" else st.session_state.players_B
    if current_players:
        df = pd.DataFrame(current_players)
        st.dataframe(df.sort_values(by="power", ascending=False), use_container_width=True)
        if st.button(f"🗑️ Clear {group_key} List"):
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
# 5. ALGORITHM: DESERT STORM PLANNING
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

# -----------------------------------------------------------------------------
# 6. ACTION CONTROL & MANUAL SWAPS
# -----------------------------------------------------------------------------
st.write("---")
if st.button("🚀 Plan Desert Storm", type="primary"):
    st.session_state.assignments_A = plan_group(st.session_state.players_A)
    st.session_state.assignments_B = plan_group(st.session_state.players_B)
    st.success("Calculated strategic lane setups successfully!")

def display_and_adjust_assignments(group_key):
    assignments = st.session_state.assignments_A if group_key == "Group A" else st.session_state.assignments_B
    if not assignments:
        return
    
    st.subheader(f"Setup {group_key}")
    all_buildings = list(assignments.keys())
    
    for b in all_buildings:
        st.markdown(f"**🏢 {b}**")
        players_in_b = assignments[b]
        if not players_in_b:
            st.text(" Empty")
        else:
            for idx, p in enumerate(players_in_b):
                suffix = " ❓" if p['commitment'] == 'Maybe' else ""
                col_p, col_move = st.columns([3, 2])
                col_p.write(f"- {p['name']} ({p['power']}M){suffix}")
                
                new_b = col_move.selectbox(f"Move {p['name']}", options=all_buildings, index=all_buildings.index(b), key=f"move_{group_key}_{b}_{idx}_{p['name']}")
                if new_b != b:
                    player_to_move = assignments[b].pop(idx)
                    assignments[new_b].append(player_to_move)
                    st.rerun()

col_col1, col_col2 = st.columns(2)
with col_col1:
    display_and_adjust_assignments("Group A")
with col_col2:
    display_and_adjust_assignments("Group B")

# -----------------------------------------------------------------------------
# 7. PIL TACTICAL GRAPHIC GENERATOR (MATCHING image_5a7b58.jpg GRID & COLORS)
# -----------------------------------------------------------------------------
def generate_tactical_image(group_name, assignments):
    # Abmessungen leicht erhöht für mehr vertikalen Atemraum
    width, height = 800, 1150
    
    if group_name == "Group A":
        bg_color = "#0a110d"       # Dunkles taktisches Grün
        border_main = "#19543e"   # Grüner Rahmen
        header_text = "#48ffb0"   # Grüner Titel
    else:
        bg_color = "#0a0f16"       # Dunkles taktisches Blau
        border_main = "#1a3a5f"   # Blauer Rahmen
        header_text = "#4da6ff"   # Blauer Titel
        
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    try:
        font_alliance = ImageFont.truetype("arial.ttf", 48)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_b_title = ImageFont.truetype("arial.ttf", 15)
        font_b_sub = ImageFont.truetype("arial.ttf", 12)
        font_p_text = ImageFont.truetype("arial.ttf", 14)
    except:
        font_alliance = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_b_title = ImageFont.load_default()
        font_b_sub = ImageFont.load_default()
        font_p_text = ImageFont.load_default()
        
    # --- HEADER SECTION ---
    draw.text((width//2, 50), "LAST WAR", fill="#ffffff", font=font_alliance, anchor="mm")
    draw.text((width//2, 100), f"DESERT STORM OPERATIONAL SETUP - {group_name.upper()}", fill=header_text, font=font_sub, anchor="mm")
    draw.text((width//2, 130), "WE STAND UNITED, STRIKE HARD, AND GIVE NO GROUND.", fill="#aaaaaa", font=font_sub, anchor="mm")
    
    draw.line([(40, 160), (width - 40, 160)], fill="#444444", width=2)
    
    # --- KORRIGIERTE CARD-ZEICHNEN-FUNKTION ---
    def draw_card(x1, y1, x2, y2, title, subtitle, subtitle_color, players):
        # Hintergrund & Rahmen
        draw.rectangle([(x1, y1), (x2, y2)], outline=border_main, width=2, fill="#11151c")
        
        # Titel-Box-Höhe erweitert auf 45px, um Platz für ZWEI Zeilen zu machen
        draw.line([(x1, y1 + 45), (x2, y1 + 45)], fill=border_main, width=1)
        
        # Zeile 1: Hauptname des Gebäudes (linksbündig)
        draw.text((x1 + 10, y1 + 6), title, fill="#ffffff", font=font_b_title)
        
        # Zeile 2: Taktischer Untertitel (SAUBER DARUNTER platziert statt überlappend!)
        draw.text((x1 + 10, y1 + 25), f'"{subtitle}"', fill=subtitle_color, font=font_b_sub)
        
        # Mitglieder-Liste
        draw.text((x1 + 10, y1 + 55), "Members:", fill="#777777", font=font_p_text)
        
        curr_y = y1 + 78
        for p in players:
            maybe_suffix = " (?)" if p["commitment"] == "Maybe" else ""
            p_display = f"- {p['name']} ({p['power']}M){maybe_suffix}"
            
            text_color = "#ffffff" if p["commitment"] == "Yes" else "#888888"
            draw.text((x1 + 10, curr_y), p_display, fill=text_color, font=font_p_text)
            curr_y += 22

    # --- ROW 1: HOSPITALS (4 Spalten angepasst für 800px Breite) ---
    h_width = 165
    h_gap = 14
    start_x = 40
    y_top_row = 190
    y_bot_row = 380
    
    hospitals = ["Hospital I", "Hospital II", "Hospital III", "Hospital IV"]
    h_subs = ["STEELHEARTS", "UNSHAKABLES", "LIFEKEEPERS", "GUARDIANS"]
    
    for i, h_name in enumerate(hospitals):
        bx1 = start_x + i * (h_width + h_gap)
        bx2 = bx1 + h_width
        draw_card(bx1, y_top_row, bx2, y_bot_row, h_name, h_subs[i], "#4caf50", assignments.get(h_name, []))
        
    # --- ROW 2: STRATEGIC BUILDINGS (2 Spalten) ---
    mid_width = 353
    mid_gap = 14
    y_mid_top = 405
    y_mid_bot = 565
    
    # Tech Center
    draw_card(start_x, y_mid_top, start_x + mid_width, y_mid_bot, "Tech Center", "THE SUPPLIERS", "#ffb300", assignments.get("Tech Center", []))
    # Info Center
    draw_card(start_x + mid_width + mid_gap, y_mid_top, width - start_x, y_mid_bot, "Info Center", "THE SCOUTS", "#ffb300", assignments.get("Info Center", []))

    # --- ROW 3: REFINERIES (2 Spalten) ---
    y_ref_top = 590
    y_ref_bot = 750
    # Oil Refinery I
    draw_card(start_x, y_ref_top, start_x + mid_width, y_ref_bot, "Oil Refinery I", "EXTRACTORS A", "#00bcd4", assignments.get("Oil Refinery I", []))
    # Oil Refinery II
    draw_card(start_x + mid_width + mid_gap, y_ref_top, width - start_x, y_ref_bot, "Oil Refinery II", "EXTRACTORS B", "#00bcd4", assignments.get("Oil Refinery II", []))

    # --- ROW 4: JUMPERS (Volle Breite) ---
    y_j_top = 775
    y_j_bot = 955
    # "AMPERSAND / TEXT" statt fehlerhaftem Emoji-Symbol, um leere Boxen zu vermeiden
    draw_card(start_x, y_j_top, width - start_x, y_j_bot, "JUMPER SQUAD", "THE ASSAULT SQUAD", "#f44336", assignments.get("Jumper", []))

    # --- ROW 5: RESERVE / BACKUPS ---
    y_r_top = 980
    y_r_bot = 1070
    
    draw.rectangle([(start_x, y_r_top), (width - start_x, y_r_bot)], outline=border_main, width=2, fill="#11151c")
    draw.text((start_x + 12, y_r_top + 10), "RESERVE UNITS", fill="#ffffff", font=font_b_title)
    
    reserve_players = assignments.get("Reserve", [])
    if not reserve_players:
        draw.text((start_x + 12, y_r_top + 45), "No remaining backup units assigned.", fill="#777777", font=font_p_text)
    else:
        res_strings = [f"{p['name']} ({p['power']}M){' (?)' if p['commitment'] == 'Maybe' else ''}" for p in reserve_players]
        res_text = "  |  ".join(res_strings)
        if len(res_text) > 90:
            res_text = res_text[:87] + "..."
        draw.text((start_x + 12, y_r_top + 45), f"Units: {res_text}", fill="#aaaaaa", font=font_p_text)

    # --- FOOTER MOTTO ---
    draw.text((width//2, 1110), "WE HOLD THE LINE AND LEAVE THE FIELD AS VICTORS!", fill="#ffffff", font=font_sub, anchor="mm")

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()
# -----------------------------------------------------------------------------
# 8. EXPORT GRAPHICS UI
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
        st.warning("Please compute layouts using 'Plan Desert Storm' before generating graphics.")