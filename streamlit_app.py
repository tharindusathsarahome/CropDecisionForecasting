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
except (KeyError, Exception):
    st.error("GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- AI ආකෘති සඳහා පද්ධති උපදෙස් ---

# 1. ශාක හඳුනාගැනීම සඳහා වන සරල උපදෙස
IDENTIFICATION_INSTRUCTION = """
ඔබේ එකම කාර්යය වන්නේ ලබා දී ඇති ඡායාරූපයේ ඇති ශාකයේ නම සිංහලෙන් හඳුනා ගැනීමයි. 
පිළිතුර ලෙස ශාකයේ නම පමණක් ලබා දෙන්න. වෙනත් කිසිවක් ඇතුළත් නොකරන්න.
උදාහරණයක් ලෙස: 'රෝස' හෝ 'තක්කාලි'.
"""

# 2. සවිස්තරාත්මක විශ්ලේෂණය සඳහා වන උපදෙස
ANALYSIS_INSTRUCTION = """
ඔබ පිළිතුරු සැපයිය යුත්තේ සිංහල භාෂාවෙන් පමණි.

ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. ඔබගේ කාර්යය වන්නේ පරිශීලකයා විසින් උඩුගත කරන ලද ශාක ඡායාරූප විශ්ලේෂණය කර ඔවුන්ගේ ප්‍රශ්නවලට සිංහල භාෂාවෙන් පිළිතුරු දීමයි.

පරිශීලකයා මුලින්ම ඡායාරූපයක් සහ ප්‍රශ්නයක් එවන විට, මෙම මාර්ගෝපදේශය භාවිතයෙන් එය හොඳින් විශ්ලේෂණය කරන්න:
1.  *පෙනෙන ශාක කොටස් හඳුනාගන්න*: කොළ, මල්, කඳන්, පස ආදිය සටහන් කරගන්න.
2.  *ශාක විශේෂය තහවුරු කරන්න*: පරිශීලකයා විසින් තහවුරු කරන ලද ශාකයේ නම මත පදනම්ව විශ්ලේෂණය කරන්න.
3.  *ශාක සෞඛ්‍යය තක්සේරු කරන්න*: රෝග, පළිබෝධකයන් හෝ පීඩනකාරී තත්ත්වයන්ගේ ලක්ෂණ සොයන්න (වර්ණය වෙනස්වීම, ලප, සිදුරු, කොළ හැකිලීම, මැලවීම, කෘමීන්, දැල්).
4.  *මූලික ප්‍රතිචාරය සකසන්න*: ඔබගේ විශ්ලේෂණය මත පදනම්ව, සවිස්තරාත්මක වාර්තාවක් සපයන්න.
    *   *සමස්ත සෞඛ්‍ය තත්ත්වය*: (උදා: සෞඛ්‍ය සම්පන්න, පීඩනයට ලක්වූ, රෝගී).
    *   *නිරීක්ෂණය කළ රෝග ලක්ෂණ*: ඔබ හඳුනාගත් නිශ්චිත සලකුණු විස්තර කරන්න.
    *   *විය හැකි හේතු*: (උදා: දිලීර ආසාදනය, ජලය වැඩිවීම, පෝෂක ඌනතාවය).
    *   *සත්කාර සහ ප්‍රතිකාර යෝජනා*: පැහැදිලි, ක්‍රියාත්මක කළ හැකි පියවර සපයන්න.

පසුව අසන සියලුම ප්‍රශ්න සඳහා, මුල් ඡායාරූපයේ සහ සංවාදයේ සන්දර්භය පවත්වා ගන්න. සංක්ෂිප්ත, ප්‍රයෝජනවත් පිළිතුරු සපයන්න.
"""

# --- ආකෘති සැකසුම ---
analysis_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=ANALYSIS_INSTRUCTION
)
identification_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=IDENTIFICATION_INSTRUCTION
)

# --- සැසි තත්ත්වය (Session State) ආරම්භ කිරීම ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False
if "plant_name" not in st.session_state:
    st.session_state.plant_name = ""
# අලුතින් උඩුගත කළ ගොනුවක් හඳුනාගැනීම සඳහා නව state එකක්
if "processed_file_id" not in st.session_state:
    st.session_state.processed_file_id = None

# --- ක්‍රියාකාරීත්වයන් (Functions) ---

def reset_session():
    """සම්පූර්ණ සැසිය නැවත සකසයි"""
    st.session_state.chat_session = None
    st.session_state.messages = []
    st.session_state.awaiting_confirmation = False
    st.session_state.plant_name = ""
    st.session_state.processed_file_id = None
    # uploader එක reset කිරීම සඳහා key එකක් භාවිතා කිරීම අනවශ්‍යයි,
    # නමුත් එය තබාගැනීමෙන් පැහැදිලිව uploader එක clear කළ හැකිය.
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0
    st.session_state.uploader_key += 1
    st.rerun()

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් (Side Bar) උඩුගත කරන්න.")

# --- ගොනු උඩුගත කිරීම සහ පාලනය සඳහා පැති තීරුව ---
with st.sidebar:
    st.header("ඔබේ ශාකය")
    
    # on_change ඉවත් කර ඇත.
    uploaded_file = st.file_uploader(
        "ඡායාරූපයක් උඩුගත කරන්න", 
        type=["jpg", "jpeg", "png"],
        key=f"uploader_{st.session_state.get('uploader_key', 0)}"
    )
    
    if st.button("නව සංවාදයක්"):
        reset_session()

# --- ස්වයංක්‍රීයව ශාකය හඳුනාගැනීමේ ක්‍රියාවලිය ---
# ඡායාරූපයක් උඩුගත කර ඇත්නම් සහ එය පෙර විශ්ලේෂණය කළ එකම ඡායාරූපය නොවේ නම්...
if uploaded_file and uploaded_file.file_id != st.session_state.processed_file_id:
    # නව සැසියක් සඳහා පැරණි දත්ත ඉවත් කිරීම
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.awaiting_confirmation = True
    st.session_state.processed_file_id = uploaded_file.file_id

    image = Image.open(uploaded_file)

    with st.spinner("ශාකය හඳුනාගනිමින් පවතී..."):
        try:
            response = identification_model.generate_content(["මෙම ශාකය කුමක්ද?", image])
            plant_name = response.text.strip()
            st.session_state.plant_name = plant_name
            
            confirmation_question = f"මෙය '{plant_name}' ශාකයක්ද? (ඔව් / නැත)"
            st.session_state.messages.append({"role": "assistant", "content": confirmation_question})
            
            # වෙනස්කම් පෙන්වීම සඳහා පිටුව නැවත ක්‍රියාත්මක කිරීම
            st.rerun()

        except Exception as e:
            st.error(f"ශාකය හඳුනාගැනීමේදී දෝෂයක් ඇතිවිය: {e}")
            reset_session()


# --- සංවාද ඉතිහාසය පෙන්වීම ---
# යෙදුම නැවත ක්‍රියාත්මක වන විට, AI ඇසූ ප්‍රශ්නය මෙහිදී දර්ශනය වේ.
if uploaded_file:
    with st.sidebar:
        st.image(uploaded_file, caption="ඔබේ ශාකය")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- චැට් ආදාන ක්‍රියාවලිය ---
if prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    if not st.session_state.processed_file_id:
        st.warning("කරුණාකර පළමුව පැති තීරුවේ ශාකයේ ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. ශාක නාමය තහවුරු කිරීමේ අදියර
    if st.session_state.awaiting_confirmation:
        st.session_state.awaiting_confirmation = False
        
        if any(word in prompt.lower() for word in ["ඔව්", "ඔවු", "ow", "yes"]):
            with st.spinner("විශ්ලේෂණය කරමින් පවතී..."):
                try:
                    analysis_prompt = f"මෙම '{st.session_state.plant_name}' ශාකයේ සෞඛ්‍ය තත්ත්වය විශ්ලේෂණය කර, ගැටලු ඇත්නම් ඒවාට විසඳුම් ලබා දෙන්න."
                    
                    # විශ්ලේෂණය සඳහා රූපය නැවත ලබා ගැනීම
                    # uploaded_file එක තවමත් පවතින නිසා, එයින් image object එක නැවත සෑදිය හැකියි
                    image_for_analysis = Image.open(uploaded_file)

                    st.session_state.chat_session = analysis_model.start_chat(history=[])
                    response = st.session_state.chat_session.send_message(
                        [analysis_prompt, image_for_analysis],
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
        else:
            rejection_message = "තේරුම් ගත්තා. කරුණාකර වෙනත්, වඩාත් පැහැදිලි ඡායාරූපයක් උඩුගත කරන්න. මෙම සංවාදය ස්වයංක්‍රීයව නැවත ආරම්භ වේ."
            st.session_state.messages.append({"role": "assistant", "content": rejection_message})
            with st.chat_message("assistant"):
                st.markdown(rejection_message)
            
            time.sleep(3)
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
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")