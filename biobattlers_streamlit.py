import streamlit as st

# MUST be first Streamlit command
st.set_page_config(page_title="BioBattlers Prototype", layout="centered")

# Add logo to sidebar
def add_logo():
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                background-image: url("https://biobattlers-images.s3.eu-north-1.amazonaws.com/logo2.jpg");
                background-repeat: no-repeat;
                background-position: top center;
                background-size: 160px;
                padding-top: 170px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    

add_logo()

import os
import requests
import streamlit.components.v1 as components
import json

# API Keys and URLs
KINDWISE_API_KEY = st.secrets["KINDWISE_API_KEY"]
IUCN_API_KEY = st.secrets["IUCN_API_KEY"]
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

# --- Get IUCN Status ---
def get_iucn_status(species_name):
    query = species_name.replace(" ", "%20")
    url = f"https://apiv3.iucnredlist.org/api/v3/species/{query}?token={IUCN_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            if result['result']:
                return result['result'][0]['category']
    except:
        pass
    return "Unknown"

# --- Rarity Mapping ---
RARITY_MAP = {
    "LC": "Common (🟢)",
    "NT": "Uncommon (🔵)",
    "VU": "Rare (🟠)",
    "EN": "Epic (🔴)",
    "CR": "Legendary (💀)",
    "Unknown": "???"
}

# --- Streamlit App ---
st.title("🪲🐝BioBattlers Prototype🦋🐜")
st.write("🔍Scan an insect!")
st.write("Created by Jack Llewellyn")

# Initialize captured collection from cookie
if 'collection' not in st.session_state:
    st.session_state.collection = get_cookies()

# Upload image
uploaded_file = st.file_uploader("Upload an insect photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    with st.spinner("Scanning with Kindwise..."):
        headers = {
            "Api-Key": KINDWISE_API_KEY,
            "Accept": "application/json"
        }

        response = requests.post(KINDWISE_API_URL, headers=headers, files={"images": uploaded_file})

        if response.status_code == 201:
            data = response.json()
            try:
                species_name = data["result"]["classification"]["suggestions"][0]["name"]
                parts = species_name.split()
                genus = parts[0].lower()
                species = parts[1].lower() if len(parts) > 1 else ""
                filename = f"{genus}_{species}.png"
                image_url = AWS_BUCKET_URL + filename

                # Check AWS for genus_species.png
                img_check = requests.get(image_url)
                if img_check.status_code != 200:
                    # Try genus.png
                    filename = f"{genus}.png"
                    image_url = AWS_BUCKET_URL + filename
                    img_check = requests.get(image_url)

                if img_check.status_code != 200:
                    image_url = "https://via.placeholder.com/300x200.png?text=Monster+Coming+Soon"
                    stats = "???"
                else:
                    stats = "Attack: 10 | Defense: 8 | Speed: 7"

                rarity_raw = get_iucn_status(species_name)
                rarity = RARITY_MAP.get(rarity_raw, "???")

                st.image(image_url, caption=species_name)
                st.text(f"Stats: {stats}")
                st.text(f"Rarity: {rarity}")

                if st.button("Capture This Creature"):
                    st.session_state.collection.append({
                        "name": species_name,
                        "imageUrl": image_url,
                        "stats": stats,
                        "rarity": rarity
                    })
                    set_cookies(st.session_state.collection)
                    st.success(f"{species_name} added to your collection!")

            except (KeyError, IndexError):
                st.error("Couldn't identify the species properly. Try again.")
        else:
            st.error("Error contacting Kindwise API. Try again later.")

# Display collection
if st.session_state.collection:
    st.subheader("📚 Your Collection")
    for creature in st.session_state.collection:
        st.image(creature["imageUrl"], width=150, caption=creature["name"])
        st.text(creature["stats"])
        st.text(f"Rarity: {creature.get('rarity', '???')}")
