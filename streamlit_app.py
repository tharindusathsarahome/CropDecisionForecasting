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
# Streamlit රහස් වලින් API යතුර ලබාගැනීම
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

පරිශීලකයා මුලින්ම ඡායාරූපයක් සහ ප්‍රශ්නයක් එවන විට, මෙම මාර්ගෝපදේශය භාවිතයෙන් එය හොඳින් විශ්ලේෂණය කරන්න:
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


# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 ශාක සෞඛ්‍ය විශ්ලේෂකය")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් උඩුගත කර, පහත ඇති චැට් කොටුවෙන් ප්‍රශ්න අසන්න.")

# --- ගොනු උඩුගත කිරීම සහ පාලනය සඳහා පැති තීරුව ---
with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader("ඡායාරූපයක් උඩුගත කරන්න", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file:
        st.session_state.image = Image.open(uploaded_file)
        st.image(st.session_state.image, caption="ඔබේ ශාකය")

    if st.button("නව සංවාදයක්"):
        # සැසිය සහ පණිවිඩ නැවත සැකසීම
        st.session_state.chat_session = None
        st.session_state.messages = []
        st.session_state.image = None
        st.rerun()

# --- සංවාද ඉතිහාසය පෙන්වීම ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- චැට් ආදාන ක්‍රියාවලිය ---
if prompt := st.chat_input("ඔබේ ශාකය ගැන ප්‍රශ්නයක් අසන්න..."):
    # 1. ඡායාරූපයක් උඩුගත කර ඇත්දැයි පරීක්ෂා කිරීම
    if st.session_state.image is None:
        st.warning("කරුණාකර පළමුව පැති තීරුවේ ශාකයේ ඡායාරූපයක් උඩුගත කරන්න.")
        st.stop()

    # 2. පරිශීලකයාගේ පණිවිඩය ඉතිහාසයට එක් කිරීම
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. ආකෘතිය සමඟ සංවාදය හැසිරවීම
    with st.spinner("විශ්ලේෂණය කරමින් පවතී..."):
        try:
            # පළමු පණිවිඩය නම්, ඡායාරූපය සමඟ නව සංවාදයක් ආරම්භ කිරීම
            if st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat()
                # ඡායාරූපය සහ පළමු ප්‍රශ්නය යැවීම
                response = st.session_state.chat_session.send_message(
                    [prompt, st.session_state.image],
                    stream=True
                )
            # පසු පණිවිඩ සඳහා, ප්‍රශ්නය පමණක් යැවීම
            else:
                response = st.session_state.chat_session.send_message(
                    prompt,
                    stream=True
                )
            
            # 4. ප්‍රතිචාරය UI වෙත සජීවීව පෙන්වීම
            with st.chat_message("assistant"):
                full_response = ""
                placeholder = st.empty()
                for chunk in response:
                    full_response += chunk.text
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
            
            # 5. සම්පූර්ණ ප්‍රතිචාරය ඉතිහාසයට එක් කිරීම
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("වියාචනය: මෙම AI විශ්ලේෂණය තොරතුරු දැනගැනීමේ අරමුණු සඳහා පමණක් වන අතර, එය වෘත්තීය උද්භිද විද්‍යාත්මක හෝ කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් නොවේ.")