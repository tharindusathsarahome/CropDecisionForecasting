import streamlit as st
from google import generativeai as genai
from PIL import Image
import io
import time

# --- Streamlit පිටු සැකසුම ---
st.set_page_config(
    page_title="Plant Disease Analyzer",
    page_icon="🌱",
    layout="centered"
)

# --- API යතුර සැකසීම ---
try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception) as e:
    st.error(f"GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- AI ආකෘතිය සඳහා සවිස්තරාත්මක පද්ධති උපදෙස් ---
SYSTEM_INSTRUCTION = """
ඔබ ශාක රෝග පිළිබඳ විශේෂඥ, මිත්‍රශීලී සිංහල සහායකයෙකි. ඔබගේ කාර්යය වන්නේ පරිශීලකයා සමඟ සංවාදයක් හරහා ඔවුන්ගේ ශාකයේ ගැටලුව හඳුනාගෙන විසඳුම් ලබා දීමයි. මෙම පියවරයන් අනුගමනය කරන්න:

**පියවර 1: මූලික හැඳින්වීම සහ ප්‍රශ්නය**
- පරිශීලකයා ඡායාරූපයක් සහ පළමු ප්‍රශ්නය ("මේකට මොකද වෙලා තියෙන්නෙ?") එවු විට, පළමුව ඡායාරූපය විශ්ලේෂණය කර ශාකය හඳුනා ගන්න.
- ඉන්පසු, මෙවැනි ප්‍රතිචාරයක් දක්වන්න: "ආයුබෝවන්! ඔබ ලබාදුන් ඡායාරූපයේ පෙනෙන ආකාරයට මෙය [හඳුනාගත් ශාකයේ නම] ශාකයක්. එය නිවැරදිද?"
- හඳුනාගත නොහැකි නම්, "මෙම ශාකය කුමක්දැයි මට පැවසිය හැකිද?" ಎಂದು අසන්න.

**පියවර 2: මූලික විශ්ලේෂණය සහ පාරිසරික ප්‍රශ්න**
- පරිශීලකයා ශාකය තහවුරු කළ පසු ("ඔව්"), ඡායාරූපයේ පෙනෙන රෝග ලක්ෂණ ගැන කෙටි සටහනක් දෙන්න. (උදා: "හොඳයි. මම දකින විදිහට, කොළවල සුදු පැහැති ලප සහ යටි පැත්තේ පුස් වැනි ස්වභාවයක් තියෙනවා.")
- ඉන්පසු, ගැටලුව තවදුරටත් තේරුම් ගැනීමට මෙවැනි විවෘත ප්‍රශ්නයක් අසන්න: "රෝගය නිවැරදිව හඳුනාගැනීමට, කරුණාකර මට තව ටිකක් විස්තර කියන්න. මේ දිනවල කාලගුණය කොහොමද? අධික වර්ෂාවක් හෝ පින්නක් තිබෙනවාද? ශාකයට හොඳින් හිරු එළිය ලැබෙනවාද?"

**පියවර 3: සවිස්තරාත්මක විශ්ලේෂණය සහ විසඳුම්**
- පරිශීලකයා පාරිසරික තොරතුරු ලබා දුන් පසු, එම සියලු තොරතුරු (ඡායාරූපය, රෝග ලක්ෂණ, කාලගුණය) එකට ගලපා, සවිස්තරාත්මක වාර්තාවක් ලබා දෙන්න.
- මෙම වාර්තාවේ පහත දෑ අනිවාර්යයෙන්ම ඇතුළත් විය යුතුය:
    1.  **නිශ්චිත රෝග විනිශ්චය:** (උදා: යටි පුස් රෝගය - Downy Mildew).
    2.  **හේතු:** පරිශීලකයාගේ පිළිතුරු සමඟ සම්බන්ධ කරමින් හේතු පැහැදිලි කරන්න.
    3.  **විසඳුම් සහ පාලනය:** ක්ෂණික පියවර, කාබනික සහ රසායනික ප්‍රතිකාර, සහ වැළැක්වීමේ ක්‍රම ලෙස කොටස් කර පැහැදිලිව ඉදිරිපත් කරන්න.

**පියවර 4: පසු විපරම**
- ඔබගේ සවිස්තරාත්මක පිළිතුරෙන් පසුව, "මේ ගැන ඔබට තවත් ප්‍රශ්න තිබේද?" ಎಂದು අසමින් සංවාදය විවෘතව තබන්න. පරිශීලකයාගේ ඕනෑම අමතර ප්‍රශ්නයකට කෙටි සහ ප්‍රයෝජනවත් පිළිතුරු දෙන්න.

සෑම විටම සිංහල භාෂාව පමණක් භාවිතා කරන්න.
"""

# --- ආකෘති සැකසුම ---
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- සැසි තත්ත්වය (Session State) ආරම්භ කිරීම ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# --- ක්‍රියාකාරීත්වයන් ---
def reset_session():
    """සම්පූර්ණ සැසිය නැවත සකසයි"""
    st.session_state.clear()
    st.rerun()

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කර, පහත චැට් කොටුවෙන් ප්‍රශ්න අසන්න.")

with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader(
        "ඡායාරූපයක් උඩුගත කරන්න",
        type=["jpg", "jpeg", "png"],
        key=f"uploader_{st.session_state.get('uploader_key', 0)}"
    )
    if uploaded_file:
        st.image(uploaded_file, caption="ඔබේ ශාකය")
    if st.button("නව සංවාදයක්"):
        reset_session()

# --- සංවාද ඉතිහාසය පෙන්වීම ---
for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- චැට් ආදාන ක්‍රියාවලිය ---
if prompt := st.chat_input("ඔබේ ශාකය ගැන ප්‍රශ්නයක් අසන්න..."):
    # පළමු වතාවට නම්, ඡායාරූපයක් අනිවාර්යයි
    if not st.session_state.get("chat_session") and not uploaded_file:
        st.warning("කරුණාකර පළමුව ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()

    # පරිශීලකයාගේ පණිවිඩය පෙන්වීම
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("පිළිතුරු සකසමින්..."):
        try:
            # සංවාදය ආරම්භ කිරීම හෝ පවත්වාගෙන යාම
            if st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat(history=[])
                # පළමු පණිවිඩය සමඟ ඡායාරූපය යැවීම
                image_obj = Image.open(uploaded_file)
                response = st.session_state.chat_session.send_message([prompt, image_obj], stream=True)
            else:
                # දැනටමත් පවතින සංවාදයකට පණිවිඩය යැවීම
                response = st.session_state.chat_session.send_message(prompt, stream=True)

            # AI ප්‍රතිචාරය streaming ආකාරයට පෙන්වීම
            with st.chat_message("assistant"):
                full_response = ""
                placeholder = st.empty()
                for chunk in response:
                    full_response += chunk.text
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
            
            # සම්පූර්ණ ප්‍රතිචාරය ඉතිහාසයට එක් කිරීම
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"සංවාදයේදී දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")