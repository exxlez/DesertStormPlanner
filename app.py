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
if "mode_A" not in st.session_state:
    st.session_state.mode_A = "4-2"
if "mode_B" not in st.session_state:
    st.session_state.mode_B = "4-2"
if "squad_A" not in st.session_state:
    st.session_state.squad_A = {}  # {Spielername: "M1"/"M2"} - nachträglich editierbar
if "squad_B" not in st.session_state:
    st.session_state.squad_B = {}

# Bezeichnungen der beiden Zuordnungslogiken (global verfügbar)
MODE_LABELS = {
    "4-2": "4 Jumpers, 2 Hospitals",
    "2-3": "2 Jumpers, 3 Hospitals",
}

# Anzeige-Namen für Gebäude (interner Datenschlüssel bleibt "Tech Center" zur
# Abwärtskompatibilität mit alten Zuordnungen; angezeigt wird überall "Science Hub")
BUILDING_DISPLAY_NAMES = {
    "Tech Center": "Science Hub",
}
def building_display(key):
    return BUILDING_DISPLAY_NAMES.get(key, key)

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
            "Building": ["Jumper", "Info Center", "Science Hub", "Hospital I", "Hospital II", "Hospital III", "Hospital IV", "Oil Refinery I", "Oil Refinery II", "Backup / Reserve"],
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
            "Gebäude": ["Jumper", "Info Center", "Science Hub", "Hospital I", "Hospital II", "Hospital III", "Hospital IV", "Oil Refinery I", "Oil Refinery II", "Reserve"],
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
    "players_B": st.session_state.players_B,
    "squad_A": st.session_state.get("squad_A", {}),
    "squad_B": st.session_state.get("squad_B", {})
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
        # Abwärtskompatibilität: falls die Config noch alte M1/M2-Zuordnungen
        # pro Spieler enthält (squad_A/squad_B), übernehmen wir sie als Startzustand
        st.session_state.squad_A = loaded_data.get("squad_A", {})
        st.session_state.squad_B = loaded_data.get("squad_B", {})
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
def plan_group(players, mode="4-2"):
    if not players:
        return {}, 0
    
    yes_players = sorted([p for p in players if p["commitment"] == "Yes"], key=lambda x: x["power"], reverse=True)
    maybe_players = sorted([p for p in players if p["commitment"] == "Maybe"], key=lambda x: x["power"], reverse=True)
    
    sorted_pool = yes_players + maybe_players

    # HARTER DECKEL: Pro Gruppe können maximal 20 Personen an Gebäuden UND
    # maximal 10 Personen in der Reserve stehen -> insgesamt max. 30 Personen.
    # Alles darüber hinaus (die schwächsten, nach Power sortiert) wird gar
    # nicht erst zugeordnet und separat als "Überschuss" zurückgemeldet.
    MAX_TOTAL_PARTICIPANTS = 30
    overflow_count = 0
    if len(sorted_pool) > MAX_TOTAL_PARTICIPANTS:
        overflow_count = len(sorted_pool) - MAX_TOTAL_PARTICIPANTS
        sorted_pool = sorted_pool[:MAX_TOTAL_PARTICIPANTS]

    total_players = len(sorted_pool)

    # Beide Modi nutzen dieselben 9 Gebäude (4 Hospitals + 2 Öl-Raffinerien existieren
    # strukturell immer) - nur die Personenanzahl pro Gebäude unterscheidet sich.
    assignments = {
        "Hospital I": [], "Hospital II": [], "Hospital III": [], "Hospital IV": [],
        "Tech Center": [], "Info Center": [], 
        "Oil Refinery I": [], "Oil Refinery II": [],
        "Jumper": [], "Reserve": []
    }
    
    if total_players == 0:
        return assignments, overflow_count

    if mode == "2-3":
        # Logik "2 Jumpers, 3 Hospitals":
        # Gesamt-Gebäudekapazität ist wie im Standardmodus auf 20 Plätze begrenzt
        # (Jumper + alle anderen Gebäude zusammen), Rest geht in die Reserve.
        # 1./2. staerkste -> Jumper. Danach werden die restlichen 18 Nicht-Jumper-
        # Plaetze im Round-Robin ueber Science Hub, Info Center, alle 4 Hospitals
        # und beide Oel Raffinerien verteilt (jeweils ein Slot pro Runde, bis die
        # jeweilige Gebaeude-Kapazitaet erreicht ist), sodass staerkere und
        # schwaechere Spieler gleichmaessig gemischt werden:
        # Science Hub: 2 | Info Center: 2 | Hospital I-IV: je 3 | Oel Raffinerie I+II: je 1
        # macht 2 Jumper + 18 Gebaeude-Plaetze = exakt 20 Plaetze an Gebaeuden.
        jumper_count = 2 if total_players >= 2 else total_players
        assignments["Jumper"] = sorted_pool[:jumper_count]
        rest = sorted_pool[jumper_count:]

        building_slots = {
            "Tech Center": [0, 8],
            "Info Center": [1, 9],
            "Hospital I": [2, 10, 14],
            "Hospital II": [3, 11, 15],
            "Hospital III": [4, 12, 16],
            "Hospital IV": [5, 13, 17],
            "Oil Refinery I": [6],
            "Oil Refinery II": [7],
        }
    else:
        # Logik "4 Jumpers, 2 Hospitals" (Standard)
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
            
    return assignments, overflow_count

st.write("---")
st.subheader("🧭 Zuordnungslogik wählen")
mode_option = st.radio(
    "Verteilungsstrategie:",
    options=["4-2", "2-3"],
    format_func=lambda m: MODE_LABELS[m],
    horizontal=True,
    key="assignment_mode_choice"
)

if st.button("🚀 Plan Desert Storm", type="primary"):
    st.session_state.assignments_A, overflow_A = plan_group(st.session_state.players_A, mode_option)
    st.session_state.assignments_B, overflow_B = plan_group(st.session_state.players_B, mode_option)
    st.session_state.mode_A = mode_option
    st.session_state.mode_B = mode_option
    st.success(f"Calculated strategic lane setups successfully! ({MODE_LABELS[mode_option]})")
    if overflow_A:
        st.warning(f"⚠️ Group A: {overflow_A} Spieler mit der niedrigsten Power wurden NICHT zugeordnet, da maximal 30 Personen pro Gruppe (20 an Gebäuden + 10 Reserve) unterstützt werden.")
    if overflow_B:
        st.warning(f"⚠️ Group B: {overflow_B} Spieler mit der niedrigsten Power wurden NICHT zugeordnet, da maximal 30 Personen pro Gruppe (20 an Gebäuden + 10 Reserve) unterstützt werden.")

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

    squad_state_key = "squad_A" if group_key == "Group A" else "squad_B"
    squad_state = st.session_state[squad_state_key]

    sortable_data = []
    for building, players in assignments.items():
        player_strings = []
        for p in players:
            squad_tag = squad_state.get(p["name"])
            tag_str = f" [{squad_tag}]" if squad_tag else ""
            maybe_str = " ❓" if p["commitment"] == "Maybe" else ""
            player_strings.append(f"{p['name']} ({p['power']}M){tag_str}{maybe_str}")
        sortable_data.append({"header": building_display(building), "items": player_strings})

    # Drag & Drop Widget aufrufen
    updated_data = sort_items(
        sortable_data, 
        multi_containers=True, 
        direction="vertical", 
        key=f"sortable_board_{group_key}"
    )

    # Rückwärts-Zuordnung von Anzeigename -> internem Datenschlüssel (z.B. "Science Hub" -> "Tech Center")
    reverse_display = {v: k for k, v in BUILDING_DISPLAY_NAMES.items()}

    # GUARD LOGIC: Verhindert das Leeren beim Rerun durch den "Generate Image"-Klick
    if updated_data:
        temp_assignments = {}
        all_players = st.session_state.players_A if group_key == "Group A" else st.session_state.players_B
        found_any_player = False
        
        for section in updated_data:
            building_name = reverse_display.get(section["header"], section["header"])
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


def render_squad_editor(group_key):
    """Nachträgliche M1/M2-Zuordnung: unabhängig von der Spieler-Stammdaten,
    da sich die Marschgruppen-Zuteilung von Event zu Event ändern kann.
    Wird direkt nach der Gebäude-Zuordnung gepflegt, pro Spieler in seinem
    aktuell zugewiesenen Gebäude."""
    assignments = st.session_state.assignments_A if group_key == "Group A" else st.session_state.assignments_B
    if not assignments:
        return

    squad_state_key = "squad_A" if group_key == "Group A" else "squad_B"
    squad_state = st.session_state[squad_state_key]

    assigned_players = [p for building, players in assignments.items() if building != "Reserve" for p in players]
    if not assigned_players:
        return

    with st.expander(f"🏷️ M1 / M2 Zuordnung bearbeiten - {group_key}", expanded=False):
        st.caption("Lege pro Spieler optional fest, ob er in M1 oder M2 mitläuft. Ein Tag ist nicht Pflicht und kann sich jedes Mal ändern.")
        squad_options = ["Kein Tag", "M1", "M2"]
        for building, players in assignments.items():
            if building == "Reserve" or not players:
                continue
            st.markdown(f"**{building_display(building)}**")
            for p in players:
                current = squad_state.get(p["name"])  # None = kein Tag gesetzt
                current_idx = 0 if current is None else (1 if current == "M1" else 2)
                key = f"squadsel_{group_key}_{building}_{p['name']}"
                new_val = st.radio(
                    p["name"], squad_options,
                    index=current_idx,
                    key=key, horizontal=True, label_visibility="visible"
                )
                if new_val == "Kein Tag":
                    squad_state.pop(p["name"], None)
                else:
                    squad_state[p["name"]] = new_val

col_col1, col_col2 = st.columns(2)
with col_col1:
    display_and_adjust_assignments("Group A")
    render_squad_editor("Group A")
with col_col2:
    display_and_adjust_assignments("Group B")
    render_squad_editor("Group B")

# -----------------------------------------------------------------------------
# 7. PIL GRAFIKGENERATOR (UNICODE-FALLBACK, EINSPALTIGES LAYOUT)
# -----------------------------------------------------------------------------
import os
import unicodedata

# Verzeichnis mit den mitgelieferten Schriftdateien (liegen neben dieser app.py).
# WICHTIG: Der Ordner "fonts/" mit DejaVuSans.ttf, DejaVuSans-Bold.ttf und
# NotoSansCJK-Regular.ttc muss mit ins Repository/Deployment übernommen werden.
# So hängt die Darstellung NICHT davon ab, welche Schriften auf dem Server
# (z.B. Streamlit Cloud) zufällig installiert sind - das war der Grund, warum
# z.B. 達人, 발SMITH oder ニスモ vorher nicht korrekt angezeigt wurden.
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _load_font_with_fallback(bundled_names, system_candidates, size, index=0):
    """Versucht zuerst die mitgelieferten Fonts, dann System-Fonts, dann Default."""
    for name in bundled_names:
        try:
            return ImageFont.truetype(os.path.join(FONT_DIR, name), size, index=index)
        except Exception:
            continue
    for path in system_candidates:
        try:
            return ImageFont.truetype(path, size, index=index)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1, skalierbar
    except TypeError:
        return ImageFont.load_default()


def load_latin_font(size):
    """Schrift fuer lateinische Zeichen, Ziffern, Umlaute, Sonderzeichen (¿, Ä, …)."""
    return _load_font_with_fallback(
        ["DejaVuSans.ttf"],
        [
            "arial.ttf", "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
        size,
    )


def load_cjk_font(size):
    """Schrift fuer chinesische/japanische/koreanische Zeichen (Hanzi, Kana, Hangul)."""
    return _load_font_with_fallback(
        ["NotoSansCJK-Regular.ttc"],
        [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ],
        size,
    )


def _is_cjk_char(ch):
    """Bestimmt anhand des Unicode-Codepoints, ob ein Zeichen CJK/Hangul/Kana ist
    und damit die Noto-CJK-Schrift statt der lateinischen Schrift benoetigt."""
    cp = ord(ch)
    ranges = [
        (0x1100, 0x11FF),   # Hangul Jamo
        (0x3040, 0x30FF),   # Hiragana + Katakana
        (0x3100, 0x312F),   # Bopomofo
        (0x3130, 0x318F),   # Hangul Compatibility Jamo
        (0x3400, 0x4DBF),   # CJK Extension A
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0xA960, 0xA97F),   # Hangul Jamo Extended-A
        (0xAC00, 0xD7A3),   # Hangul Syllables
        (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
        (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth Forms
    ]
    return any(lo <= cp <= hi for lo, hi in ranges)


def _segment_mixed_text(text):
    """Zerlegt einen String in zusammenhaengende Abschnitte, jeweils markiert
    ob sie mit der CJK-Schrift oder der lateinischen Schrift gezeichnet werden."""
    if not text:
        return []
    segments = []
    current = text[0]
    current_is_cjk = _is_cjk_char(text[0])
    for ch in text[1:]:
        ch_is_cjk = _is_cjk_char(ch)
        if ch_is_cjk == current_is_cjk:
            current += ch
        else:
            segments.append((current, current_is_cjk))
            current = ch
            current_is_cjk = ch_is_cjk
    segments.append((current, current_is_cjk))
    return segments


class MixedFont:
    """Kapselt ein zusammenpassendes Latein/CJK-Schriftpaar in gleicher Groesse
    und erlaubt Messen & Zeichnen von Text, der beide Zeichensaetze mischt
    (z.B. "達人Panda" oder "발SMITH"), ohne dass Zeichen fehlen oder als
    Kaestchen dargestellt werden."""

    def __init__(self, size):
        self.size = size
        self.latin = load_latin_font(size)
        self.cjk = load_cjk_font(size)

    def _font_for(self, is_cjk):
        return self.cjk if is_cjk else self.latin

    def length(self, draw_ctx, text):
        total = 0.0
        for chunk, is_cjk in _segment_mixed_text(text):
            total += draw_ctx.textlength(chunk, font=self._font_for(is_cjk))
        return total

    def draw(self, draw_ctx, xy, text, fill, bold=False):
        x, y = xy
        stroke_w = 1 if bold else 0
        for chunk, is_cjk in _segment_mixed_text(text):
            font = self._font_for(is_cjk)
            draw_ctx.text((x, y), chunk, fill=fill, font=font, stroke_width=stroke_w, stroke_fill=fill)
            x += draw_ctx.textlength(chunk, font=font)


def generate_tactical_image(group_name, assignments, mode="4-2", squad_map=None):
    width = 1300
    squad_map = squad_map or {}

    font_alliance = load_latin_font(60)
    font_sub = load_latin_font(24)
    font_b_title = load_latin_font(23)
    font_b_sub = load_latin_font(16)
    font_p_badge = load_latin_font(14)      # Badge [M1]/[M2] ist immer ASCII
    font_p_text = MixedFont(20)             # Namen: gemischte Schrift mit Unicode-Fallback

    MIN_NAME_CHARS = 20  # garantierte Mindestbreite pro Namen (in Zeichen)

    # --- HILFSFUNKTION: TEXT AUF VERFÜGBARE BREITE KÜRZEN (mixed-font-sicher) ---
    def fit_mixed(draw_ctx, text, font, max_width):
        if font.length(draw_ctx, text) <= max_width:
            return text
        while text and font.length(draw_ctx, text + "…") > max_width:
            text = text[:-1]
        return (text + "…") if text else "…"

    # --- HILFSFUNKTION FÜR DYNAMISCHE HÖHENBERECHNUNG ---
    def get_card_height(players):
        base_header_space = 105
        player_count = max(1, len(players))
        player_space = player_count * 33
        padding_bottom = 20
        return base_header_space + player_space + padding_bottom

    # Farbschemata
    themes = {
        "Group A": {"bg": "#0a110d", "border": "#19543e", "header": "#48ffb0"},
        "Group B": {"bg": "#0a0f16", "border": "#1a3a5f", "header": "#4da6ff"}
    }
    theme = themes[group_name]

    start_x = 45
    col_gap = 24
    col_width = (width - 2 * start_x - col_gap) / 2
    col_x1 = [start_x, start_x + col_width + col_gap]
    col_x2 = [start_x + col_width, width - start_x]

    # Sanity-Check: reicht die Spaltenbreite tatsaechlich fuer >= 20 Zeichen aus?
    # (bei col_width ~ 605px und Schriftgroesse 20 liegt das komfortabel bei 25+ Zeichen)

    # --- 1. GEBÄUDE-REIHENFOLGE, AUFGETEILT AUF 2 SPALTEN ---
    # Alle 9 Gebäude existieren strukturell in beiden Modi; im "2-3"-Modus bleiben
    # Hospital-Slots ggf. leer bzw. Oil Refinery II ungenutzt ("• Empty").
    # "Reserve Units" wird wie ein normales Gebäude behandelt und ans Ende der
    # rechten Spalte gehängt, damit das Bild kompakt in 2 Spalten bleibt statt
    # sich stark in die Länge zu ziehen.
    buildings = [
        ("Jumper", "JUMPER SQUAD", "THE ASSAULT SQUAD", "#f44336"),
        ("Tech Center", "Science Hub", "THE SUPPLIERS", "#ffb300"),
        ("Info Center", "Info Center", "THE SCOUTS", "#ffb300"),
        ("Hospital I", "Hospital I", "STEELHEARTS", "#4caf50"),
        ("Hospital II", "Hospital II", "UNSHAKABLES", "#4caf50"),
        ("Hospital III", "Hospital III", "LIFEKEEPERS", "#4caf50"),
        ("Hospital IV", "Hospital IV", "GUARDIANS", "#4caf50"),
        ("Oil Refinery I", "Oil Refinery I", "EXTRACTORS A", "#00bcd4"),
        ("Oil Refinery II", "Oil Refinery II", "EXTRACTORS B", "#00bcd4"),
        ("Reserve", "Reserve Units", "BACKUP", "#9e9e9e"),
    ]

    card_gap = 20
    y_top = 220

    half = (len(buildings) + 1) // 2
    columns = [buildings[:half], buildings[half:]]

    # Höhen je Spalte vorab berechnen, um die Bildhöhe zu bestimmen
    col_heights = []
    for col_buildings in columns:
        heights = [get_card_height(assignments.get(key, [])) for key, _, _, _ in col_buildings]
        total = sum(heights) + card_gap * max(0, len(col_buildings) - 1)
        col_heights.append((heights, total))

    max_col_total = max(h for _, h in col_heights)
    dynamic_height = y_top + max_col_total + 110

    # --- 2. BILD ERSTELLEN UND ZEICHNEN ---
    img = Image.new("RGB", (width, int(dynamic_height)), color=theme["bg"])
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((width//2, 60), "LAST WAR", fill="#ffffff", font=font_alliance, stroke_width=1, stroke_fill="#ffffff", anchor="mm")
    draw.text((width//2, 120), f"DESERT STORM SETUP - {group_name.upper()} ({MODE_LABELS.get(mode, mode)})", fill=theme["header"], font=font_sub, anchor="mm")
    draw.text((width//2, 155), "WE STAND UNITED, STRIKE HARD, AND GIVE NO GROUND.", fill="#aaaaaa", font=font_sub, anchor="mm")
    draw.line([(50, 190), (width - 50, 190)], fill="#444444", width=3)

    # Standardisierte Card-Zeichen-Funktion (Spaltenbreite statt volle Breite)
    def draw_card(x1, x2, y1, y2, title, subtitle, subtitle_color, players):
        draw.rectangle([(x1, y1), (x2, y2)], outline=theme["border"], width=3, fill="#11151c")
        draw.line([(x1, y1 + 60), (x2, y1 + 60)], fill=theme["border"], width=2)

        draw.text((x1 + 18, y1 + 8), title, fill="#ffffff", font=font_b_title, stroke_width=1, stroke_fill="#ffffff")
        draw.text((x1 + 18, y1 + 36), f'"{subtitle}"', fill=subtitle_color, font=font_b_sub)
        draw.text((x1 + 18, y1 + 75), "Members:", fill="#999999", font=font_b_sub)

        curr_y = y1 + 105
        max_text_width = (x2 - x1) - 36  # Innenabstand links/rechts der Karte

        if not players:
            empty_label = "No backup units assigned." if title == "Reserve Units" else "• Empty"
            draw.text((x1 + 18, curr_y), empty_label, fill="#555555", font=font_p_text.latin)
        else:
            for p in players:
                squad = squad_map.get(p["name"])  # None = kein Tag gesetzt
                maybe_suffix = " (?)" if p["commitment"] == "Maybe" else ""
                name_color = "#ffffff" if p["commitment"] == "Yes" else "#bbbbbb"

                if squad:
                    # M1/M2 als deutlich sichtbares, farbiges Tag zeichnen (M1=Orange, M2=Blau)
                    badge_bg = "#ff9800" if squad == "M1" else "#2196f3"
                    badge_text_w = draw.textlength(squad, font=font_p_badge)
                    badge_pad_x = 7
                    badge_h = 22
                    badge_w = badge_text_w + badge_pad_x * 2
                    badge_y1 = curr_y + 1
                    badge_y2 = badge_y1 + badge_h
                    draw.rounded_rectangle([(x1 + 18, badge_y1), (x1 + 18 + badge_w, badge_y2)], radius=5, fill=badge_bg)
                    draw.text((x1 + 18 + badge_pad_x, badge_y1 + 3), squad, fill="#ffffff", font=font_p_badge, stroke_width=1, stroke_fill="#ffffff")
                    name_x = x1 + 18 + badge_w + 10
                    available_w = max_text_width - (badge_w + 10)
                else:
                    name_x = x1 + 18
                    available_w = max_text_width

                # Name platzieren (gemischte Schrift mit Unicode-Fallback,
                # garantiert mindestens MIN_NAME_CHARS Zeichen Platz durch die
                # Spaltenbreite; nur im theoretischen Extremfall gekürzt)
                p_display = fit_mixed(draw, f"• {p['name']}{maybe_suffix}", font_p_text, available_w)
                font_p_text.draw(draw, (name_x, curr_y + 1), p_display, name_color, bold=True)
                curr_y += 33

    # Beide Spalten unabhängig voneinander von oben nach unten zeichnen
    for col_idx, col_buildings in enumerate(columns):
        heights, _ = col_heights[col_idx]
        x1, x2 = col_x1[col_idx], col_x2[col_idx]
        y_cursor = y_top
        for (key, title, subtitle, color), h in zip(col_buildings, heights):
            draw_card(x1, x2, y_cursor, y_cursor + h, title, subtitle, color, assignments.get(key, []))
            y_cursor += h + card_gap

    # --- FOOTER MOTTO ---
    footer_y = y_top + max_col_total + 55
    draw.text((width//2, footer_y), "WE HOLD THE LINE AND LEAVE THE FIELD AS VICTORS!", fill="#ffffff", font=font_sub, anchor="mm")

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()
# -----------------------------------------------------------------------------
# 8. BILDER-EXPORT UI-BEREICH
# -----------------------------------------------------------------------------
st.write("---")
st.subheader("🖼️ Export Roster Visuals")

if st.button("🖼️ Generate Tactical Image", type="secondary"):
    if st.session_state.assignments_A or st.session_state.assignments_B:
        col_img1, col_img2 = st.columns(2)
        
        if st.session_state.assignments_A:
            with col_img1:
                st.write(f"**Group A Tactical Graphic** ({MODE_LABELS.get(st.session_state.mode_A, st.session_state.mode_A)})")
                img_data_A = generate_tactical_image("Group A", st.session_state.assignments_A, st.session_state.mode_A, st.session_state.squad_A)
                st.image(img_data_A)
                st.download_button("💾 Download Image A", data=img_data_A, file_name="Desert_Storm_Group_A.png", mime="image/png")
                
        if st.session_state.assignments_B:
            with col_img2:
                st.write(f"**Group B Tactical Graphic** ({MODE_LABELS.get(st.session_state.mode_B, st.session_state.mode_B)})")
                img_data_B = generate_tactical_image("Group B", st.session_state.assignments_B, st.session_state.mode_B, st.session_state.squad_B)
                st.image(img_data_B)
                st.download_button("💾 Download Image B", data=img_data_B, file_name="Desert_Storm_Group_B.png", mime="image/png")
    else:
        st.warning("Bitte berechne zuerst ein Layout mit 'Plan Desert Storm'.")
