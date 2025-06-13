import streamlit as st
from google import generativeai as genai
from PIL import Image
import io

# --- 1. පිටු සැකසුම සහ API යතුර ---
st.set_page_config(
    page_title="Plant Disease Analyzer",
    page_icon="🌱",
    layout="centered"
)

# API යතුර ලබා ගැනීම
try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except Exception:
    st.error("GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- 2. නව, ඒකාබද්ධ පද්ධති උපදෙස (යාවත්කාලීන කළ) ---
SYSTEM_INSTRUCTION = """
ඔබ ශාක රෝග පිළිබඳ විශේෂඥ, උපකාරශීලී සිංහල සහායකයෙකි. ඔබගේ සංවාදය අදියර තුනකින් සමන්විත වේ.

ප්‍රධාන රීතිය: ඔබගේ සියලුම පිළිතුරු අනිවාර්යයෙන්ම සිංහල භාෂාවෙන් විය යුතුය. පරිශීලකයා ඉංග්‍රීසියෙන් ප්‍රශ්න ඇසුවද, ඔබගේ පිළිතුර සිංහලෙන් ලබා දෙන්න.

අදියර 1: හඳුනාගැනීම සහ තහවුරු කිරීම
- පරිශීලකයා ඡායාරූපයක් ලබා දුන් විට, ඔබේ පළමු කාර්යය වන්නේ එහි ඇති ශාකය සිංහලෙන් හඳුනා ගැනීමයි.
- ඉන්පසු, පරිශීලකයාගෙන් "මෙය 'ශාකයේ නම' ද?" ලෙස අසා තහවුරු කරගන්න.

අදියර 2: ප්‍රශ්න ඇසීම සහ විශ්ලේෂණය
- පරිශීලකයා "ඔව්" හෝ ඒ හා සමාන පිළිතුරක් දුන් විට, රෝගය නිවැරදිව හඳුනා ගැනීමට අදාළ සරල ප්‍රශ්න 2-3ක් (උදා: කාලගුණය, ජලය, හිරු එළිය ගැන) අසන්න.
- පරිශීලකයා එම ප්‍රශ්නවලට පිළිතුරු දුන් පසු, එම තොරතුරු සහ ඡායාරූපය පදනම් කරගෙන සවිස්තරාත්මක වාර්තාවක් සපයන්න. වාර්තාවේ: 1. රෝග විනිශ්චය, 2. හේතු, 3. විසඳුම් (කාබනික, රසායනික, වැළැක්වීම) අඩංගු විය යුතුය.

අදියර 3: අඛණ්ඩ සංවාදය
- සවිස්තරාත්මක වාර්තාව ලබා දීමෙන් පසුව, සංවාදය අවසන් නොකරන්න.
- පරිශීලකයා අසන ඕනෑම වැඩිදුර ප්‍රශ්නයකට (follow-up questions), ඔවුන් ඉංග්‍රීසියෙන් ඇසුවද, සිංහලෙන් උපකාරශීලීව පිළිතුරු දෙන්න.
- පරිශීලකයා "නැත" කියා ශාකය වැරදි බව පැවසුවහොත්, සමාව අයැද වෙනත් ඡායාරූපයක් ඉල්ලා සිටින්න.
""
"""

# --- 3. ආකෘතිය සහ Session State සැකසීම ---

# session state ආරම්භ කිරීම
if "chat" not in st.session_state:
    # අපි දැන් ආකෘතිය session state එකේම ගබඩා කරනවා.
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest",
        system_instruction=SYSTEM_INSTRUCTION
    )
    st.session_state.chat = model.start_chat(history=[])

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def reset_chat():
    st.session_state.uploader_key += 1
    # session state හි ඇති සියල්ල මකා දමා නැවත ආරම්භ කිරීම
    st.session_state.clear()
    st.rerun()

# --- 4. UI කොටස ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කර සංවාදය ආරම්භ කරන්න.")

with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader(
        "ඡායාරූපයක් උඩුගත කරන්න",
        type=["jpg", "jpeg", "png"],
        key=f"uploader_{st.session_state.uploader_key}"
    )
    if st.button("නව සංවාදයක්"):
        reset_chat()

# --- 5. ප්‍රධාන ක්‍රියාවලිය (දැන් ඉතා සරලයි) ---

# සංවාද ඉතිහාසය පෙන්වීම
for message in st.session_state.chat.history:
    # API එකෙන් ලැබෙන 'model' role එක 'assistant' ලෙස වෙනස් කිරීම
    role = "assistant" if message.role == "model" else message.role
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# පරිශීලක ආදානය හැසිරවීම
prompt_content = None
# පළමු වරට ඡායාරූපයක් උඩුගත කළ විට, එය පළමු prompt එක ලෙස සලකනවා
if uploaded_file and not st.session_state.chat.history:
    prompt_content = [Image.open(uploaded_file)]
    st.sidebar.image(uploaded_file, caption="ඔබේ ශාකය")

# සාමාන්‍ය chat ආදානය
elif prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    prompt_content = [prompt]

# AI වෙත යැවිය යුතු දෙයක් ඇත්නම් පමණක් ක්‍රියාත්මක වීම
if prompt_content:
    with st.chat_message("user"):
        # ඡායාරූපයක් නම්, එය නොපෙන්වයි; text එකක් නම්, එය පෙන්වයි
        if isinstance(prompt_content[0], str):
            st.markdown(prompt_content[0])

    # AI වෙත ඉල්ලීම යවා, පිළිතුර stream කිරීම
    with st.spinner("පිළිතුර සකසමින්..."):
        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat.send_message(prompt_content, stream=True)
                st.write_stream(response)
            except Exception as e:
                st.error(f"දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")