import streamlit as st
from google import generativeai as genai
from PIL import Image
import time
import re

# --- 1. පිටු සැකසුම සහ API යතුර ---
st.set_page_config(
    page_title="Plant Disease Analyzer",
    page_icon="🌱",
    layout="centered"
)

try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- 2. AI ආකෘති සඳහා පද්ධති උපදෙස් ---
IDENTIFICATION_INSTRUCTION = "ඔබේ එකම කාර්යය වන්නේ ලබා දී ඇති ඡායාරූපයේ ඇති ශාකයේ නම සිංහලෙන් හඳුනා ගැනීමයි. පිළිතුර ලෙස ශාකයේ නම පමණක් ලබා දෙන්න. උදාහරණයක් ලෙස: 'රෝස'. හඳුනාගත නොහැකි නම්, 'හඳුනාගත නොහැක' ලෙස පමණක් සඳහන් කරන්න."
PRELIMINARY_ANALYSIS_INSTRUCTION = "ඔබ ශාක රෝග පිළිබඳ සිංහල විශේෂඥයෙකි. ඡායාරූපය සහ ශාකයේ නම මත පදනම්ව, රෝගය නිවැරදිව හඳුනාගැනීමට උපකාරී වන සරල ප්‍රශ්න 2-3ක් සිංහලෙන් අසන්න (කාලගුණය, ජලය, හිරු එළිය). ප්‍රතිචාරය මෙම ආකෘතියට *පමණක්* දෙන්න:\n[ANALYSIS]: <කෙටි රෝග ලක්ෂණ සාරාංශය>\n[QUESTIONS]: <ප්‍රශ්නය 1> | <ප්‍රශ්නය 2>"
FINAL_ANALYSIS_INSTRUCTION = "ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ සිංහල විශේෂඥයෙකි. ඔබට මූලික විශ්ලේෂණයක් සහ පරිශීලකයාගේ පාරිසරික පිළිතුරු ලැබී ඇත. මෙම සියලු තොරතුරු සහ ඡායාරූපය භාවිතා කර, සවිස්තරාත්මක අවසන් වාර්තාවක් සපයන්න: 1. රෝග විනිශ්චය 2. හේතු 3. විසඳුම් (ක්ෂණික, කාබනික, රසායනික, වැළැක්වීම)."
FOLLOW_UP_INSTRUCTION = "ඔබ ශාක රෝග පිළිබඳ උපකාරශීලී සිංහල සහායකයෙකි. පරිශීලකයාට දැනටමත් විශ්ලේෂණයක් ලැබී ඇති අතර, ඔවුන් දැන් ඒ ගැන තවත් ප්‍රශ්න අසයි. සම්පූර්ණ සංවාද ඉතිහාසය සහ ඡායාරූපය භාවිතා කර, ඔවුන්ගේ නව ප්‍රශ්නවලට කෙටියෙන් සහ උපකාරශීලීව පිළිතුරු දෙන්න."

# --- 3. ආකෘති සහ Session State සැකසීම ---
@st.cache_resource
def load_models():
    return {
        "identification": genai.GenerativeModel(model_name="gemini-1.5-flash-latest", system_instruction=IDENTIFICATION_INSTRUCTION),
        "preliminary": genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=PRELIMINARY_ANALYSIS_INSTRUCTION),
        "final": genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FINAL_ANALYSIS_INSTRUCTION),
        "follow_up": genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FOLLOW_UP_INSTRUCTION)
    }
models = load_models()

def init_session_state():
    # Keep uploader_key and messages across reruns for the same session
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Reset other state variables
    st.session_state.stage = "initial" # Stages: initial, awaiting_confirmation, awaiting_info, chat
    st.session_state.plant_name = ""
    st.session_state.initial_analysis = ""
    st.session_state.processed_file_id = None

def reset_conversation():
    # Increment key to force re-render of file uploader
    st.session_state.uploader_key += 1
    init_session_state() # Reset all state variables for a new conversation
    st.rerun()

# Initialize state if it's the first run
if "stage" not in st.session_state:
    init_session_state()

# --- 4. UI කොටස ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කර සංවාදය ආරම්භ කරන්න.")

with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader("ඡායාරූපයක් උඩුගත කරන්න", type=["jpg", "jpeg", "png"], key=f"uploader_{st.session_state.uploader_key}")
    if st.button("නව සංවාදයක්"):
        reset_conversation()

# --- 5. ප්‍රධාන ක්‍රියාවලිය ---

# නව ඡායාරූපයක් උඩුගත කළ විට සියල්ල නැවත සකස් කිරීම
if uploaded_file and uploaded_file.file_id != st.session_state.processed_file_id:
    # A new file is uploaded, reset everything
    init_session_state()
    st.session_state.processed_file_id = uploaded_file.file_id
    image = Image.open(uploaded_file)
    with st.spinner("ශාකය හඳුනාගනිමින් පවතී..."):
        try:
            response = models["identification"].generate_content(image)
            plant_name = response.text.strip()
            if "හඳුනාගත නොහැක" in plant_name or not plant_name or len(plant_name.split()) > 3:
                st.error("සමාවන්න, ශාකය පැහැදිලිව හඳුනාගත නොහැක. කරුණාකර වඩාත් පැහැදිලි ඡායාරූපයක් උඩුගත කරන්න.")
                time.sleep(3)
                reset_conversation()
            else:
                st.session_state.plant_name = plant_name
                st.session_state.stage = "awaiting_confirmation"
                st.session_state.messages.append({"role": "assistant", "content": f"මෙය '{st.session_state.plant_name}' ශාකයක්ද? (ඔව් / නැත)"})
                st.rerun()
        except Exception as e:
            st.error(f"ශාකය හඳුනාගැනීමේදී දෝෂයක්: {e}")
            time.sleep(3)
            reset_conversation()

# සංවාද ඉතිහාසය පෙන්වීම
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# පරිශීලක ආදානය හැසිරවීම
if prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    if not st.session_state.processed_file_id:
        st.warning("කරුණාකර පළමුව ඡායාරූපයක් උඩුගත කරන්න."); st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- තාර්කික ප්‍රවාහය (Logic Flow) ---
    current_stage = st.session_state.stage
    image = Image.open(uploaded_file)

    # අදියර 1: ශාකයේ නම තහවුරු කිරීම
    if current_stage == "awaiting_confirmation":
        if any(word in prompt.lower() for word in ["ඔව්", "ඔවු", "ow", "yes"]):
            with st.spinner("මූලික විශ්ලේෂණය කරමින්..."):
                response = models["preliminary"].generate_content([f"මෙය {st.session_state.plant_name} ශාකයකි.", image])
                analysis_match = re.search(r"\[ANALYSIS\]:\s*(.*?)\s*\n\[QUESTIONS\]:", response.text, re.DOTALL)
                questions_match = re.search(r"\[QUESTIONS\]:\s*(.*)", response.text, re.DOTALL)

                if analysis_match and questions_match:
                    st.session_state.initial_analysis = analysis_match.group(1).strip()
                    questions = questions_match.group(1).strip().replace(" | ", "\n- ")
                    msg = (f"හොඳයි. මූලික නිරීක්ෂණයට අනුව, {st.session_state.initial_analysis.lower()}.\n\n"
                           f"රෝගය නිවැරදිව හඳුනාගැනීමට, කරුණාකර මෙම ප්‍රශ්නවලට පිළිතුරු දෙන්න:\n- {questions}")
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                    st.session_state.stage = "awaiting_info"
                    st.rerun()
                else:
                    st.error("මූලික විශ්ලේෂණය කිරීමේදී දෝෂයක්. කරුණාකර නැවත උත්සාහ කරන්න.")
        else:
            reset_conversation()

    # අදියර 2: අවසන් විශ්ලේෂණ වාර්තාව ලබා දීම
    elif current_stage == "awaiting_info":
        with st.chat_message("assistant"):
            final_prompt = (f"ශාකය: {st.session_state.plant_name}.\n"
                            f"මූලික රෝග ලක්ෂණ: {st.session_state.initial_analysis}.\n"
                            f"පරිශීලකයාගේ පිළිතුරු: {prompt}\n\n"
                            "ඉහත තොරතුරු සහ ඡායාරූපය මත පදනම්ව සවිස්තරාත්මක, අවසන් වාර්තාව සපයන්න.")
            response_stream = models["final"].generate_content([final_prompt, image], stream=True)
            full_response = st.write_stream(response_stream)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.stage = "chat" # <<< අඛණ්ඩ සංවාදය සඳහා යතුර!
            st.rerun()

    # අදියර 3: අඛණ්ඩ සංවාදය (Follow-up Chat)
    elif current_stage == "chat":
        with st.chat_message("assistant"):
            history_for_model = [{"role": "model" if msg["role"] == "assistant" else "user", "parts": [msg["content"]]} for msg in st.session_state.messages[:-1]]
            chat = models["follow_up"].start_chat(history=history_for_model)
            response_stream = chat.send_message([prompt, image], stream=True)
            full_response = st.write_stream(response_stream)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun()

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")