import os
import requests
import streamlit as st
import streamlit.components.v1 as components
import json

# API Keys and URLs
KINDWISE_API_KEY = "NXDFLm5Gc7uH4H2spUOiqeRLcMDjj0PRcFBjD1cRfbPBzZzBEp"
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
        files = {"images": uploaded_file.getvalue()}

        # Proper format for requests with file-like object
        response = requests.post(KINDWISE_API_URL, headers=headers, files={"images": uploaded_file})

        if response.status_code == 201:
            data = response.json()
            try:
                species_name = data["result"]["classification"]["suggestions"][0]["name"]
                filename = species_name.lower().replace(" ", "_") + ".png"
                image_url = AWS_BUCKET_URL + filename

                # Check if image exists on AWS (very basic check)
                img_check = requests.get(image_url)
                if img_check.status_code == 200:
                    stats = "Attack: 10 | Defense: 8 | Speed: 7"  # Placeholder stats
                    monster_card = {
                        "name": species_name,
                        "imageUrl": image_url,
                        "stats": stats
                    }
                else:
                    monster_card = {
                        "name": species_name,
                        "imageUrl": "https://via.placeholder.com/300x200.png?text=Monster+Coming+Soon",
                        "stats": "???"
                    }

                st.image(monster_card["imageUrl"], caption=monster_card["name"])
                st.text(monster_card["stats"])

                if st.button("Capture This Creature"):
                    st.session_state.collection.append(monster_card)
                    set_cookies(st.session_state.collection)
                    st.success(f"{monster_card['name']} added to your collection!")

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
