import streamlit as st
import os
import requests
import streamlit.components.v1 as components
import json
import random

# --- Page Configuration ---
st.set_page_config(page_title="BioBattlers Prototype", layout="centered")

# --- Sidebar Logo ---
def add_sidebar_logo():
    st.markdown(
        '''
        <style>
        section[data-testid="stSidebar"] {
            background-image: url("https://biobattlers-images.s3.eu-north-1.amazonaws.com/logo2.jpg");
            background-repeat: no-repeat;
            background-position: top center;
            background-size: 160px;
            padding-top: 170px;
        }
        </style>
        ''',
        unsafe_allow_html=True
    )

add_sidebar_logo()

# --- Main Logo ---
st.markdown(
    '''
    <div style='text-align: center; margin-top: 20px;'>
        <img src='https://biobattlers-images.s3.eu-north-1.amazonaws.com/Logo.png' width='220'/>
    </div>
    ''',
    unsafe_allow_html=True
)

# --- Title & Subtitle ---
st.markdown("<h1 style='text-align: center; color: #1f4e79;'>🪲 BioBattlers: Scan • Capture • Collect 🐝</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.1em;'>Created by Jack Llewellyn – BioBattlers Ltd. All rights reserved © 2025</p>", unsafe_allow_html=True)

# --- Load Creature Stats from JSON ---
try:
    with open("creatures.json", "r") as f:
        CREATURE_STATS = json.load(f)
except FileNotFoundError:
    CREATURE_STATS = {}
    st.error("⚠️ creatures.json not found. Creatures will have default stats.")

# --- API Keys & URLs ---
KINDWISE_API_KEY = st.secrets["KINDWISE_API_KEY"]
KINDWISE_API_URL = "https://insect.kindwise.com/api/v1/identification"
AWS_BUCKET_URL = "https://biobattlers-images.s3.eu-north-1.amazonaws.com/"
COOKIE_NAME = "biobattlers_collection"

# --- Cookie Helpers ---
def get_cookies():
    cookies = st.query_params.get(COOKIE_NAME, ["[]"])[0]
    try:
        return json.loads(cookies)
    except json.JSONDecodeError:
        return []

def set_cookies(collection):
    json_collection = json.dumps(collection)
    components.html(f"""
        <script>
        document.cookie = '{COOKIE_NAME}={json_collection};path=/';
        window.location.href = window.location.href.split('?')[0] + '?{COOKIE_NAME}=' + encodeURIComponent(JSON.stringify({json_collection}));
        </script>
    """, height=0)

# --- IUCN Placeholder ---
def get_iucn_status(species_name):
    return "Unknown"

RARITY_MAP = {
    "LC": "Common (🟢)",
    "NT": "Uncommon (🔵)",
    "VU": "Rare (🟠)",
    "EN": "Epic (🔴)",
    "CR": "Legendary (💀)",
    "Unknown": "???"
}

# --- Session State Init ---
if 'collection' not in st.session_state:
    st.session_state.collection = get_cookies()
if 'kindwise_result' not in st.session_state:
    st.session_state.kindwise_result = None
if 'last_uploaded_name' not in st.session_state:
    st.session_state.last_uploaded_name = None

# --- Wild Battle Function ---
def run_wild_battle():
    if not st.session_state.collection:
        st.warning("📦 You need at least one creature in your collection to battle!")
        return

    creature_names = [c["name"] for c in st.session_state.collection]

    # Safely handle selected battler state
    default_index = 0
    if "selected_battler" in st.session_state and st.session_state.selected_battler in creature_names:
        default_index = creature_names.index(st.session_state.selected_battler)
    else:
        st.session_state.selected_battler = creature_names[0]

    selected_name = st.selectbox("Choose your battler:", creature_names, index=default_index)
    st.session_state.selected_battler = selected_name

    if st.button("🎮 Fight Wild Creature!"):
        player_creature = next(c for c in st.session_state.collection if c["name"] == st.session_state.selected_battler)

        wild_key = random.choice(list(CREATURE_STATS.keys()))
        wild_stats = CREATURE_STATS[wild_key]["stats"]
        wild_image = AWS_BUCKET_URL + f"{wild_key}.png"

        def parse_stats(stats_str):
            try:
                parts = stats_str.split("|")
                return sum([int(part.strip().split(":")[1]) for part in parts])
            except:
                return 0

        player_score = parse_stats(player_creature["stats"])
        wild_score = parse_stats(f"Attack: {wild_stats['attack']} | Defense: {wild_stats['defense']} | Speed: {wild_stats['speed']}")

        st.markdown("## ⚔️ Wild Battle Begins!")
        st.image(player_creature["imageUrl"], width=150, caption=f"🧬 {player_creature['name']}")
        st.image(wild_image, width=150, caption=f"🌿 Wild {wild_key.title().replace('_', ' ')}")
        st.markdown(f"**Your Power:** {player_score}  |  **Wild Power:** {wild_score}")

        if player_score > wild_score:
            player_creature["wins"] = player_creature.get("wins", 0) + 1
            st.success(f"🎉 You won! {player_creature['name']} now has {player_creature['wins']} win(s)!")
        elif player_score < wild_score:
            st.error("💀 Defeat! The wild creature overpowered you.")
        else:
            st.info("🤝 It's a draw. The wild creature retreats... for now.")

# --- Upload + Scan ---
st.markdown("### 📸 Upload an insect photo to scan:")
uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

if uploaded_file:
    with st.spinner("🔎 Scanning new Biobattler..."):

        if uploaded_file.name != st.session_state.last_uploaded_name:
            headers = {
                "Api-Key": KINDWISE_API_KEY,
                "Accept": "application/json"
            }
            response = requests.post(KINDWISE_API_URL, headers=headers, files={"images": uploaded_file})
            if response.status_code == 201:
                st.session_state.kindwise_result = response.json()
                st.session_state.last_uploaded_name = uploaded_file.name
            else:
                st.error("❌ Error contacting Kindwise API. Try again later.")
                st.stop()

        data = st.session_state.kindwise_result

        try:
            species_name = data["result"]["classification"]["suggestions"][0]["name"]
            parts = species_name.split()
            genus = parts[0].lower()
            species = parts[1].lower() if len(parts) > 1 else ""
            creature_key = f"{genus}_{species}".strip("_") if species else genus

            image_variants = []
            if species:
                image_variants.append(f"{genus}_{species}.png")
                image_variants.append(f"{genus}+{species}.png")
            image_variants.append(f"{genus}.png")

            image_url = None
            for filename in image_variants:
                candidate_url = AWS_BUCKET_URL + filename
                img_check = requests.get(candidate_url)
                if img_check.status_code == 200:
                    image_url = candidate_url
                    break

            if not image_url:
                image_url = "https://biobattlers-images.s3.eu-north-1.amazonaws.com/noclue.png"

            creature_data = CREATURE_STATS.get(creature_key)
            if not creature_data:
                creature_data = CREATURE_STATS.get(genus)

            if creature_data:
                stats = creature_data["stats"]
                stat_string = f"Attack: {stats['attack']} | Defense: {stats['defense']} | Speed: {stats['speed']}"
            else:
                stat_string = "Attack: ??? | Defense: ??? | Speed: ???"

            rarity_raw = get_iucn_status(species_name)
            rarity = RARITY_MAP.get(rarity_raw, "???")

            st.image(image_url, caption=species_name, width=300)
            st.markdown(f"**Stats:** {stat_string}")
            st.markdown(f"**Rarity:** {rarity}")

            if st.button("🎯 Capture This Creature"):
                st.session_state.collection.append({
                    "name": species_name,
                    "imageUrl": image_url,
                    "stats": stat_string,
                    "rarity": rarity,
                    "wins": 0
                })
                set_cookies(st.session_state.collection)
                st.success(f"{species_name} added to your collection!")

        except (KeyError, IndexError):
            st.error("❌ Couldn't identify the species properly. Try again.")

# --- Show Collection ---
if st.session_state.collection:
    st.markdown("## 📚 Your BioBattlers Collection")
    for creature in st.session_state.collection:
        st.image(creature["imageUrl"], width=150, caption=creature["name"])
        st.text(creature["stats"])
        st.text(f"Rarity: {creature.get('rarity', '???')}")
        if "wins" in creature:
            st.text(f"🏅 Wins: {creature['wins']}")

    st.markdown("### 🧪 Ready to Battle?")
    run_wild_battle()

# --- Footer ---
st.markdown("""
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: #f0f2f6;
            padding: 10px 0;
            text-align: center;
            font-size: 0.8rem;
            color: #6c757d;
            z-index: 999;
        }
    </style>
    <div class="footer">
        This app has been created by Jack Llewellyn – <strong>BIOBATTLERS LTD</strong>.<br>
        All rights reserved &copy; 2025
    </div>
""", unsafe_allow_html=True)
