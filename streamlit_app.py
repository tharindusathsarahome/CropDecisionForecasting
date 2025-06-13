import streamlit as st
from google import generativeai as genai
from PIL import Image
import io

# --- Streamlit පිටු සැකසුම ---
st.set_page_config(
    page_title="Plant Disease Analyzer",
    page_icon="🌱",
    layout="centered"
)

# --- API යතුර සැකසීම ---
try:
    # Streamlit රහස් වලින් API යතුර ලබා ගැනීම
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- AI ආකෘති සඳහා පද්ධති උපදෙස් ---

# 1. ශාක හඳුනාගැනීම සඳහා වන සරල උපදෙස
IDENTIFICATION_INSTRUCTION = """
ඔබේ එකම කාර්යය වන්නේ ලබා දී ඇති ඡායාරූපයේ ඇති ශාකයේ නම සිංහලෙන් හඳුනා ගැනීමයි. 
පිළිතුර ලෙස ශාකයේ නම පමණක් ලබා දෙන්න. වෙනත් කිසිවක් ඇතුළත් නොකරන්න.
උදාහරණයක් ලෙස: 'රෝස' හෝ 'අඹ'.
"""

# 2. සවිස්තරාත්මක විශ්ලේෂණය සඳහා වන උපදෙස
ANALYSIS_INSTRUCTION = """
ඔබ පිළිතුරු සැපයිය යුත්තේ සිංහල භාෂාවෙන් පමණි.

ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. ඔබගේ කාර්යය වන්නේ පරිශීලකයා විසින් උඩුගත කරන ලද ශාක ඡායාරූප විශ්ලේෂණය කර ඔවුන්ගේ ප්‍රශ්නවලට සිංහල භාෂාවෙන් පිළිතුරු දීමයි.

පරිශීලකයා මුලින්ම ඡායාරූපයක් සහ ප්‍රශ්නයක් එවන විට, මෙම මාර්ගෝපදේශය භාවිතයෙන් එය හොඳින් විශ්ලේෂණය කරන්න:
1.  *පෙනෙන ශාක කොටස් හඳුනාගන්න*: කොළ, මල්, කඳන්, පස ආදිය සටහන් කරගන්න.
2.  *ශාක විශේෂය හඳුනාගන්න*: ශාකය හඳුනා ගැනීමට උත්සාහ කරන්න. අවිනිශ්චිත නම්, "හඳුනා නොගත් විශේෂය" ලෙස සඳහන් කර එහි ලක්ෂණ විස්තර කරන්න.
3.  *ශාක සෞඛ්‍යය තක්සේරු කරන්න*: රෝග, පළිබෝධකයන් හෝ පීඩනකාරී තත්ත්වයන්ගේ ලක්ෂණ සොයන්න (වර්ණය වෙනස්වීම, ලප, සිදුරු, කොළ හැකිලීම, මැලවීම, කෘමීන්, දැල්).
4.  *මූලික ප්‍රතිචාරය සකසන්න*: ඔබගේ විශ්ලේෂණය සහ පරිශීලකයාගේ ප්‍රශ්නය මත පදනම්ව, සවිස්තරාත්මක වාර්තාවක් සපයන්න.
    *   *සෘජු පිළිතුර*: පළමුව, පරිශීලකයාගේ ප්‍රශ්නයට කෙලින්ම පිළිතුරු දෙන්න.
    *   *සමස්ත සෞඛ්‍ය තත්ත්වය*: (උදා: සෞඛ්‍ය සම්පන්න, පීඩනයට ලක්වූ, රෝගී).
    *   *නිරීක්ෂණය කළ රෝග ලක්ෂණ*: ඔබ හඳුනාගත් නිශ්චිත සලකුණු විස්තර කරන්න.
    *   *විය හැකි හේතු*: (උදා: දිලීර ආසාදනය, ජලය වැඩිවීම, පෝෂක ඌනතාවය).
    *   *සත්කාර සහ ප්‍රතිකාර යෝජනා*: පැහැදිලි, ක්‍රියාත්මක කළ හැකි පියවර සපයන්න.

පසුව අසන සියලුම ප්‍රශ්න සඳහා, මුල් ඡායාරූපයේ සහ සංවාදයේ සන්දර්භය පවත්වා ගන්න. සංක්ෂිප්ත, ප්‍රයෝජනවත් පිළිතුරු සපයන්න.
"""

# --- ආකෘති සැකසුම ---
# සවිස්තරාත්මක විශ්ලේෂණය සඳහා ප්‍රධාන ආකෘතිය
analysis_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest", # gemini-1.5-pro is good for this
    system_instruction=ANALYSIS_INSTRUCTION
)
# ශාක හඳුනාගැනීම සඳහා වන ආකෘතිය
identification_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=IDENTIFICATION_INSTRUCTION
)

# --- සැසි තත්ත්වය (Session State) ආරම්භ කිරීම ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "image" not in st.session_state:
    st.session_state.image = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
# නව තත්ත්වයන් (states) එකතු කිරීම
if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False
if "plant_name" not in st.session_state:
    st.session_state.plant_name = ""

# --- ක්‍රියාකාරීත්වයන් (Functions) ---

def reset_session():
    """සම්පූර්ණ සැසිය නැවත සකසයි"""
    st.session_state.chat_session = None
    st.session_state.messages = []
    st.session_state.image = None
    st.session_state.awaiting_confirmation = False
    st.session_state.plant_name = ""
    st.session_state.uploader_key += 1
    st.rerun()

def handle_image_upload():
    """ඡායාරූපය උඩුගත කළ විට ක්‍රියාත්මක වේ"""
    uploaded_file = st.session_state[f"uploader_{st.session_state.uploader_key}"]
    if uploaded_file:
        # පෙර දත්ත ඉවත් කිරීම
        st.session_state.messages = []
        st.session_state.chat_session = None
        
        image = Image.open(uploaded_file)
        st.session_state.image = image

        # ශාකය හඳුනාගැනීම සඳහා AI වෙත ඉල්ලීම යැවීම
        with st.spinner("ශාකය හඳුනාගනිමින් පවතී..."):
            try:
                response = identification_model.generate_content(["මෙම ශාකය කුමක්ද?", image])
                plant_name = response.text.strip()
                st.session_state.plant_name = plant_name

                # පරිශීලකයාගෙන් තහවුරු කිරීම ඉල්ලීම
                confirmation_question = f"මෙය '{plant_name}' ශාකයක්ද? (ඔව් / නැත)"
                st.session_state.messages.append({"role": "assistant", "content": confirmation_question})
                st.session_state.awaiting_confirmation = True
            except Exception as e:
                st.error(f"ශාකය හඳුනාගැනීමේදී දෝෂයක් ඇතිවිය: {e}")
                reset_session()

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් (Side Bar) උඩුගත කරන්න. ඉන්පසු, අපගේ සහායකයා ඔබෙන් ප්‍රශ්නයක් අසනු ඇත.")

# --- ගොනු උඩුගත කිරීම සහ පාලනය සඳහා පැති තීරුව ---
with st.sidebar:
    st.header("ඔබේ ශාකය")
    
    uploaded_file = st.file_uploader(
        "ඡායාරූපයක් උඩුගත කරන්න", 
        type=["jpg", "jpeg", "png"],
        # uploader එක reset කිරීමට key එක සහ on_change ශ්‍රිතය භාවිතා කිරීම
        key=f"uploader_{st.session_state.uploader_key}",
        on_change=handle_image_upload 
    )
    
    if st.session_state.image:
        st.image(st.session_state.image, caption="ඔබේ ශාකය")

    if st.button("නව සංවාදයක්"):
        reset_session()

# --- සංවාද ඉතිහාසය පෙන්වීම ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- චැට් ආදාන ක්‍රියාවලිය ---
if prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    # ඡායාරූපයක් නොමැතිනම්, කිසිවක් නොකරන්න
    if st.session_state.image is None:
        st.warning("කරුණාකර පළමුව පැති තීරුවේ ශාකයේ ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()

    # පරිශීලකයාගේ පිළිතුර පණිවිඩ ලැයිස්තුවට එක් කිරීම
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. ශාක නාමය තහවුරු කිරීමේ අදියර
    if st.session_state.awaiting_confirmation:
        # "ඔව්" සඳහා සමාන වචන පරීක්ෂා කිරීම
        if any(word in prompt.lower() for word in ["ඔව්", "ඔවු", "ow", "yes", " అవును"]):
            st.session_state.awaiting_confirmation = False
            with st.spinner("විශ්ලේෂණය කරමින් පවතී..."):
                try:
                    # සවිස්තරාත්මක විශ්ලේෂණය ආරම්භ කිරීම
                    analysis_prompt = f"මෙම '{st.session_state.plant_name}' ශාකයේ සෞඛ්‍ය තත්ත්වය විශ්ලේෂණය කර, ගැටලු ඇත්නම් ඒවාට විසඳුම් ලබා දෙන්න."
                    
                    st.session_state.chat_session = analysis_model.start_chat()
                    response = st.session_state.chat_session.send_message(
                        [analysis_prompt, st.session_state.image],
                        stream=True
                    )
                    
                    with st.chat_message("assistant"):
                        full_response = ""
                        placeholder = st.empty()
                        for chunk in response:
                            full_response += chunk.text
                            placeholder.markdown(full_response + "▌")
                        placeholder.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                except Exception as e:
                    st.error(f"විශ්ලේෂණයේදී දෝෂයක් ඇතිවිය: {e}")

        # "නැත" සඳහා ප්‍රතිචාරය
        else:
            st.session_state.awaiting_confirmation = False
            rejection_message = "තේරුම් ගත්තා. කරුණාකර වෙනත්, වඩාත් පැහැදිලි ඡායාරූපයක් උඩුගත කරන්න."
            st.session_state.messages.append({"role": "assistant", "content": rejection_message})
            with st.chat_message("assistant"):
                st.markdown(rejection_message)
            # තත්පර 2ක් රැඳී සිට සැසිය reset කිරීම
            import time
            time.sleep(2)
            reset_session()

    # 2. සාමාන්‍ය සංවාද අදියර (තහවුරු කිරීමෙන් පසු)
    elif st.session_state.chat_session:
        with st.spinner("පිළිතුරු සකසමින්..."):
            try:
                response = st.session_state.chat_session.send_message(
                    prompt,
                    stream=True
                )
                
                with st.chat_message("assistant"):
                    full_response = ""
                    placeholder = st.empty()
                    for chunk in response:
                        full_response += chunk.text
                        placeholder.markdown(full_response + "▌")
                    placeholder.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් නොවේ.")