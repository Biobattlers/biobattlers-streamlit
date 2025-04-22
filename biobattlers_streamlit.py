
import os
import requests
import streamlit as st
import streamlit.components.v1 as components
import json

# --- STYLE ---
st.markdown(
    """
    <style>
    body {
        background: none !important;
    }
    .stApp {
        background: none;
        position: relative;
    }

    .stApp::before {
        content: "";
        background-image: url("https://biobattlers-images.s3.eu-north-1.amazonaws.com/Background.png");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        opacity: 0.3;
        z-index: -1;
    }

    .block-container {
        background-color: rgba(0, 0, 0, 0.6);
        border-radius: 12px;
        padding: 2rem;
    }

    h1, h2, h3, p, span, div {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# API Keys and URLs
KINDWISE_API_KEY = "NXDFLm5Gc7uH4H2spUOiqeRLcMDjj0PRcFBjD1cRfbPBzZzBEp"
IUCN_API_KEY = "hbMZdzpTrj8UTF5d73211DMdpcRCdRBH1hCL"
KINDWISE_API_URL = "https://insect.kindwise.com/api/v1/identification"
AWS_BUCKET_URL = "https://biobattlers-images.s3.eu-north-1.amazonaws.com/"
COOKIE_NAME = "biobattlers_collection"

# --- Cookie Helpers ---
def get_cookies():
    cookies = st.experimental_get_query_params().get(COOKIE_NAME, ["[]"])[0]
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
st.set_page_config(page_title="BioBattlers Prototype", layout="centered")
st.title("🪲 BioBattlers Scanner")
st.write("Scan an insect to see if we’ve got a monster card for it!")

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
