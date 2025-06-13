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

# --- 2. ඒකාබද්ධ පද්ධති උපදෙස ---
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
"""

# --- 3. ආකෘතිය සහ Session State සැකසීම ---
def get_chat_model():
    # ආකෘතිය session state හි ගබඩා කිරීමෙන් අනවශ්‍ය ලෙස නැවත නැවතත් නිර්මාණය වීම වැළැක්වීම
    if "chat_model" not in st.session_state:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            system_instruction=SYSTEM_INSTRUCTION
        )
        st.session_state.chat_model = model.start_chat(history=[])
    return st.session_state.chat_model

# uploader key එක session state හි ආරම්භ කිරීම
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def reset_chat():
    st.session_state.uploader_key += 1
    # session state හි ඇති chat model එක සහ අනෙකුත් දෑ මකා දැමීම
    keys_to_delete = ["chat_model", "processed_file"]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
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

# --- 5. ප්‍රධාන ක්‍රියාවලිය (සරල සහ ස්ථාවර) ---
chat = get_chat_model()

# සංවාද ඉතිහාසය පෙන්වීම
for message in chat.history:
    role = "assistant" if message.role == "model" else message.role
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# පරිශීලක ආදානය හැසිරවීම
prompt_content = None

# නව ඡායාරූපයක් උඩුගත කළ විට
if uploaded_file and uploaded_file.id != st.session_state.get("processed_file"):
    st.session_state.processed_file = uploaded_file.id
    prompt_content = [Image.open(uploaded_file)]

# text ආදානයක් ලැබුණු විට
elif prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    # ඡායාරූපයක් උඩුගත කර නොමැති නම් අනතුරු ඇඟවීම
    if not hasattr(st.session_state, 'processed_file'):
        st.warning("කරුණාකර පළමුව ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()
    prompt_content = [prompt]

# AI වෙත යැවීමට අන්තර්ගතයක් ඇත්නම් පමණක් ක්‍රියාත්මක වීම
if prompt_content:
    if isinstance(prompt_content[0], str):
        with st.chat_message("user"):
            st.markdown(prompt_content[0])

    with st.spinner("පිළිතුර සකසමින්..."):
        with st.chat_message("assistant"):
            try:
                # `send_message` වෙතින් ලැබෙන stream එක කෙලින්ම `write_stream` වෙත ලබා දීම
                response_stream = chat.send_message(prompt_content, stream=True)
                st.write_stream(response_stream)
            except Exception as e:
                st.error(f"දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")