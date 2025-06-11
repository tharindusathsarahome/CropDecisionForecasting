import streamlit as st
from google import generativeai as genai
from PIL import Image
import io

# --- Streamlit පිටු සැකසුම ---
st.set_page_config(
    page_title="ශාක සෞඛ්‍ය විශ්ලේෂකය",
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

# --- AI ආකෘතිය සඳහා පද්ධති උපදෙස් (සිංහලෙන්) ---
SYSTEM_INSTRUCTION = """
ඔබ පිළිතුරු සැපයිය යුත්තේ සිංහල භාෂාවෙන් පමණි.

ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. ඔබගේ කාර්යය වන්නේ පරිශීලකයා විසින් උඩුගත කරන ලද ශාක ඡායාරූප විශ්ලේෂණය කර ඔවුන්ගේ ප්‍රශ්නවලට සිංහල භාෂාවෙන් පිළිතුරු දීමයි.

**වැදගත්: රූපයේ ගුණාත්මකභාවය පළමුව පරීක්ෂා කරන්න:**
*   වෙනත් ඕනෑම දෙයක් කිරීමට පෙර, ඡායාරූපයේ ගුණාත්මකභාවය තක්සේරු කරන්න.
*   ඡායාරූපය **අපැහැදිලි නම්, බොඳ වී ඇත්නම්, ඉතා අඳුරු නම්, බොහෝ දුරින් ඇත්නම්, හෝ එහි ශාකයක් පැහැදිලිව නොපෙනේ නම්**, සම්පූර්ණ විශ්ලේෂණයක් කිරීමට උත්සාහ **නොකරන්න**.
*   ඒ වෙනුවට, ගැටලුව කාරුණිකව සිංහලෙන් පැහැදිලි කර, වඩාත් පැහැදිලි, නිශ්චිත ඡායාරූපයක් උඩුගත කරන ලෙස පරිශීලකයාගෙන් ඉල්ලා සිටින්න. උදාහරණයක් ලෙස, "මෙම ඡායාරූපය පැහැදිලි නැත. කරුණාකර ශාකයේ බලපෑමට ලක් වූ කොටසට නාභිගත වූ (focused) පැහැදිලි ඡායාරූපයක් ලබා දෙන්න." වැනි පිළිතුරක් දෙන්න.
*   ඡායාරූපය විශ්ලේෂණයට සුදුසු නම් පමණක්, පහත පියවර අනුගමනය කරන්න.

**විශ්ලේෂණ මාර්ගෝපදේශය:**
1.  **පෙනෙන ශාක කොටස් හඳුනාගන්න**: කොළ, මල්, කඳන්, පස ආදිය සටහන් කරගන්න.
2.  **ශාක විශේෂය හඳුනාගන්න**: ශාකය හඳුනා ගැනීමට උත්සාහ කරන්න. අවිනිශ්චිත නම්, "හඳුනා නොගත් විශේෂය" ලෙස සඳහන් කර එහි ලක්ෂණ විස්තර කරන්න.
3.  **ශාක සෞඛ්‍යය තක්සේරු කරන්න**: රෝග, පළිබෝධකයන් හෝ පීඩනකාරී තත්ත්වයන්ගේ ලක්ෂණ සොයන්න (වර්ණය වෙනස්වීම, ලප, සිදුරු, කොළ හැකිලීම, මැලවීම, කෘමීන්, දැල්).
4.  **මූලික ප්‍රතිචාරය සකසන්න**: ඔබගේ විශ්ලේෂණය සහ පරිශීලකයාගේ ප්‍රශ්නය මත පදනම්ව, සවිස්තරාත්මක වාර්තාවක් සපයන්න.
    *   **සෘජු පිළිතුර**: පළමුව, පරිශීලකයාගේ ප්‍රශ්නයට කෙලින්ම පිළිතුරු දෙන්න.
    *   **සමස්ත සෞඛ්‍ය තත්ත්වය**: (උදා: සෞඛ්‍ය සම්පන්න, පීඩනයට ලක්වූ, රෝගී).
    *   **නිරීක්ෂණය කළ රෝග ලක්ෂණ**: ඔබ හඳුනාගත් නිශ්චිත සලකුණු විස්තර කරන්න.
    *   **විය හැකි හේතු**: (උදා: දිලීර ආසාදනය, ජලය වැඩිවීම, පෝෂක ඌනතාවය).
    *   **සත්කාර සහ ප්‍රතිකාර යෝජනා**: පැහැදිලි, ක්‍රියාත්මක කළ හැකි පියවර සපයන්න.

පසුව අසන සියලුම ප්‍රශ්න සඳහා, මුල් ඡායාරූපයේ සහ සංවාදයේ සන්දර්භය පවත්වා ගන්න. සංක්ෂිප්ත, ප්‍රයෝජනවත් පිළිතුරු සපයන්න.
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
if "image" not in st.session_state:
    st.session_state.image = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 ශාක සෞඛ්‍ය විශ්ලේෂකය")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කර, පහත චැට් කොටුවෙන් ප්‍රශ්න අසන්න.")

# --- ගොනු උඩුගත කිරීම සහ පාලනය සඳහා පැති තීරුව ---
with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader(
        "ඡායාරූපයක් උඩුගත කරන්න", 
        type=["jpg", "jpeg", "png"], 
        key=st.session_state.uploader_key
    )
    
    if uploaded_file:
        st.session_state.image = Image.open(uploaded_file)
        st.image(st.session_state.image, caption="ඔබේ ශාකය")

    if st.button("නව සංවාදයක්"):
        st.session_state.chat_session = None
        st.session_state.messages = []
        st.session_state.image = None
        st.session_state.uploader_key += 1
        st.rerun()

# --- සංවාද ඉතිහාසය පෙන්වීම ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- චැට් ආදාන ක්‍රියාවලිය ---
if prompt := st.chat_input("ඔබේ ශාකය ගැන ප්‍රශ්නයක් අසන්න..."):
    if st.session_state.image is None:
        st.warning("කරුණාකර පළමුව පැති තීරුවේ ශාකයේ ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("විශ්ලේෂණය කරමින් පවතී..."):
        try:
            if st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat()
                response = st.session_state.chat_session.send_message(
                    [prompt, st.session_state.image],
                    stream=True
                )
            else:
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
st.caption("වියාචනය: මෙම AI විශ්ලේෂණය තොරතුරු දැනගැනීමේ අරමුණු සඳහා පමණක් වන අතර, එය වෘත්තීය උද්භිද විද්‍යාත්මක හෝ කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් නොවේ.")