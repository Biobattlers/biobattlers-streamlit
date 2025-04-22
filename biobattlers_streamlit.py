import os
import requests
import streamlit as st
import streamlit.components.v1 as components
import json

# API Keys and URLs
KINDWISE_API_KEY = "NXDFLm5Gc7uH4H2spUOiqeRLcMDjj0PRcFBjD1cRfbPBzZzBEp"
KINDWISE_API_URL = "https://insect.kindwise.com/api/v1/identification"
AWS_BUCKET_URL = "https://biobattlers-images.s3.eu-north-1.amazonaws.com/"
IUCN_API_KEY = "hbMZdzpTrj8UTF5d73211DMdpcRCdRBH1hCL"
IUCN_API_URL = "https://apiv3.iucnredlist.org/api/v3/species/"
COOKIE_NAME = "biobattlers_collection"

RARITY_MAP = {
    "LC": "Common",
    "NT": "Uncommon",
    "VU": "Rare",
    "EN": "Epic",
    "CR": "Legendary"
}

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

# --- Fetch rarity from IUCN ---
def fetch_rarity(species_name):
    try:
        url = f"{IUCN_API_URL}{species_name.replace(' ', '%20')}?token={IUCN_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("result"):
                category = data["result"][0].get("category", "")
                return RARITY_MAP.get(category, "???")
    except:
        pass
    return "???"

# --- Custom Styling ---
st.markdown(
    f"""
    <style>
body {
    background-image: url('https://biobattlers-images.s3.eu-north-1.amazonaws.com/Background.png');
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
}
.stApp {
    background-color: rgba(0, 0, 0, 0.5);
}
.button-img {
    border: none;
    background: none;
    padding: 0;
    cursor: pointer;
}
</style>
    """,
    unsafe_allow_html=True
)

# --- Streamlit App ---
st.set_page_config(page_title="BioBattlers Prototype", layout="centered")
st.title("\U0001FAB2 BioBattlers Scanner")
st.write("Scan an insect to see if we’ve got a monster card for it!")

# Initialize captured collection from cookie
if 'collection' not in st.session_state:
    st.session_state.collection = get_cookies()

if 'show_collection' not in st.session_state:
    st.session_state.show_collection = False

# Upload image
uploaded_file = st.file_uploader("Upload an insect photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    scan_clicked = st.image("https://biobattlers-images.s3.eu-north-1.amazonaws.com/Scan.png", use_column_width=True)
    with st.spinner("Scanning with Kindwise..."):
        headers = {
            "Api-Key": KINDWISE_API_KEY,
            "Accept": "application/json"
        }
        files = {"images": uploaded_file.getvalue()}

        response = requests.post(KINDWISE_API_URL, headers=headers, files={"images": uploaded_file})

        if response.status_code == 201:
            data = response.json()
            try:
                species_name = data["result"]["classification"]["suggestions"][0]["name"]

                # Get rarity
                rarity = fetch_rarity(species_name)

                # Split genus and species
                parts = species_name.split()
                genus = parts[0].lower()
                species = parts[1].lower() if len(parts) > 1 else ""

                # Try full species first
                filename = f"{genus}_{species}.png"
                image_url = AWS_BUCKET_URL + filename
                img_check = requests.get(image_url)

                # If not found, try genus only
                if img_check.status_code != 200:
                    filename = f"{genus}.png"
                    image_url = AWS_BUCKET_URL + filename
                    img_check = requests.get(image_url)

                # Final fallback if still not found
                if img_check.status_code != 200:
                    image_url = "https://via.placeholder.com/300x200.png?text=Monster+Coming+Soon"
                    stats = "???"
                else:
                    stats = "Attack: 10 | Defense: 8 | Speed: 7"

                monster_card = {
                    "name": species_name,
                    "imageUrl": image_url,
                    "stats": stats,
                    "rarity": rarity
                }

                st.image(monster_card["imageUrl"], caption=monster_card["name"])
                st.text(monster_card["stats"])
                st.markdown(f"**Rarity:** {monster_card['rarity']}")

                if st.button("Capture This Creature"):
                    st.session_state.collection.append(monster_card)
                    set_cookies(st.session_state.collection)
                    st.success(f"{monster_card['name']} added to your collection!")

            except (KeyError, IndexError):
                st.error("Couldn't identify the species properly. Try again.")
        else:
            st.error("Error contacting Kindwise API. Try again later.")

# View Collection Toggle
if st.session_state.collection:
    if st.button("View Collection"):
        st.session_state.show_collection = not st.session_state.show_collection

    if st.session_state.show_collection:
        st.image("https://biobattlers-images.s3.eu-north-1.amazonaws.com/Collection.png", width=200)
        st.subheader("\U0001F4DA Your Collection")
        for creature in st.session_state.collection:
            st.image(creature["imageUrl"], width=150, caption=creature["name"])
            st.text(creature["stats"])
            st.markdown(f"**Rarity:** {creature['rarity']}")
