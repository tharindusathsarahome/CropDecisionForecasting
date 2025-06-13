import streamlit as st
from google import generativeai as genai
from PIL import Image
import io
import time
import re

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
IDENTIFICATION_INSTRUCTION = """
ඔබේ එකම කාර්යය වන්නේ ලබා දී ඇති ඡායාරූපයේ ඇති ශාකයේ නම සිංහලෙන් හඳුනා ගැනීමයි.
පිළිතුර ලෙස ශාකයේ නම පමණක් ලබා දෙන්න. උදාහරණයක් ලෙස: 'රෝස' හෝ 'තක්කාලි'. හඳුනාගත නොහැකි නම්, "හඳුනාගත නොහැක" ලෙස පමණක් සඳහන් කරන්න.
"""

PRELIMINARY_ANALYSIS_INSTRUCTION = """
ඔබ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. ඔබගේ කාර්යය සිංහල භාෂාවෙන් පමණක් කළ යුතුය.
ලබා දී ඇති ඡායාරූපය සහ ශාකයේ නම මත පදනම්ව, රෝගය නිවැරදිව හඳුනාගැනීමට උපකාරී වන සරල ප්‍රශ්න 2-3ක් සිංහලෙන් අසන්න. මෙම ප්‍රශ්න කාලගුණය, හිරු එළිය, සහ ජලය දැමීම වැනි දේ ගැන විය යුතුය.
ප්‍රතිචාරය පහත ආකෘතියට අනුව පමණක් ලබා දෙන්න:
[ANALYSIS]: <ඔබ හඳුනාගත් රෝග ලක්ෂණ පිළිබඳ කෙටි සාරාංශයක්>
[QUESTIONS]: <ප්‍රශ්නය 1> | <ප්‍රශ්නය 2>
"""

FINAL_ANALYSIS_INSTRUCTION = """
ඔබ පිළිතුරු සැපයිය යුත්තේ සිංහල භාෂාවෙන් පමණි. ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ විශේෂඥයෙකි.
ඔබට දැන් මූලික රෝග ලක්ෂණ විශ්ලේෂණයක් සහ පරිශීලකයා විසින් සපයන ලද පාරිසරික තොරතුරු ලැබී ඇත.
මෙම සියලු තොරතුරු භාවිතා කර, පහත සඳහන් දෑ ඇතුළත් සවිස්තරාත්මක සහ අවසාන වාර්තාවක් සපයන්න:
1.  *නිශ්චිත රෝග විනිශ්චය:* විය හැකි රෝගයේ නම.
2.  *හේතු:* පරිශීලකයාගේ පිළිතුරු ද සැලකිල්ලට ගනිමින් හේතු පැහැදිලි කරන්න.
3.  *විසඳුම් සහ පාලනය:* ක්ෂණික පියවර, කාබනික ප්‍රතිකාර, රසායනික ප්‍රතිකාර, සහ වැළැක්වීමේ ක්‍රම ලෙස කොටස් කර ඉදිරිපත් කරන්න.
"""

FOLLOW_UP_INSTRUCTION = """
ඔබ ශාක රෝග පිළිබඳ උපකාරශීලී විශේෂඥ සහායකයෙකි. ඔබ සිංහල භාෂාවෙන් පිළිතුරු දිය යුතුය.
පරිශීලකයාට දැනටමත් තම ශාකයේ ගැටලුව පිළිබඳ සවිස්තරාත්මක විශ්ලේෂණයක් ලැබී ඇත. ඔවුන් දැන් ඒ සම්බන්ධයෙන් තවත් ප්‍රශ්න අසමින් සිටී.
සම්පූර්ණ සංවාද ඉතිහාසය සහ ඡායාරූපය භාවිතා කර, ඔවුන්ගේ නව ප්‍රශ්නවලට කෙටියෙන් සහ උපකාරශීලී ලෙස පිළිතුරු දෙන්න.ඔවුන් ඉංග්‍රීසියෙන් ඇසුවද, සිංහලෙන් උපකාරශීලීව පිළිතුරු දෙන්න.
"""

# --- ආකෘති සැකසුම ---
identification_model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", system_instruction=IDENTIFICATION_INSTRUCTION)
preliminary_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=PRELIMINARY_ANALYSIS_INSTRUCTION)
final_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FINAL_ANALYSIS_INSTRUCTION)
follow_up_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FOLLOW_UP_INSTRUCTION)


# --- සැසි තත්ත්වය (Session State) ආරම්භ කිරීම ---
if "messages" not in st.session_state: st.session_state.messages = []
if "awaiting_confirmation" not in st.session_state: st.session_state.awaiting_confirmation = False
if "awaiting_environmental_info" not in st.session_state: st.session_state.awaiting_environmental_info = False
if "plant_name" not in st.session_state: st.session_state.plant_name = ""
if "initial_analysis" not in st.session_state: st.session_state.initial_analysis = ""
if "processed_file_id" not in st.session_state: st.session_state.processed_file_id = None
if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

def reset_session():
    """Clears the entire session state and prepares for a new upload."""
    uploader_key = st.session_state.get('uploader_key', 0)
    st.session_state.clear()
    st.session_state.uploader_key = uploader_key + 1
    st.rerun()

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කරන්න.")

with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader("ඡායාරූපයක් උඩුගත කරන්න", type=["jpg", "jpeg", "png"], key=f"uploader_{st.session_state.uploader_key}")
    if st.button("නව සංවාදයක්"):
        reset_session()

# --- ස්වයංක්‍රීයව ශාකය හඳුනාගැනීමේ ක්‍රියාවලිය ---
if uploaded_file and uploaded_file.file_id != st.session_state.get('processed_file_id'):
    reset_session() # Reset everything for a new image
    st.session_state.processed_file_id = uploaded_file.file_id
    image = Image.open(uploaded_file)
    with st.spinner("ශාකය හඳුනාගනිමින් පවතී..."):
        try:
            response = identification_model.generate_content(image)
            plant_name = response.text.strip()
            
            unrecognized_keywords = ["හඳුනාගත", "නොහැක", "අපහසුයි", "පැහැදිලි නැත"]
            is_unrecognized = (
                not plant_name or
                any(keyword in plant_name for keyword in unrecognized_keywords) or
                len(plant_name.split()) > 3 
            )
            
            if is_unrecognized:
                st.error("සමාවන්න, මෙම ඡායාරූපයෙන් ශාකය පැහැදිලිව හඳුනාගත නොහැක. කරුණාකර වඩාත් පැහැදිලි ඡායාරූපයක් උඩුගත කරන්න.")
                time.sleep(3); reset_session()
            else:
                st.session_state.plant_name = plant_name
                st.session_state.awaiting_confirmation = True
                st.session_state.messages.append({"role": "assistant", "content": f"මෙය '{plant_name}' ශාකයක්ද? (ඔව් / නැත)"})
                st.rerun()
        except Exception as e:
            st.error(f"ශාකය හඳුනාගැනීමේදී දෝෂයක් ඇතිවිය: {e}")
            time.sleep(3); reset_session()

# --- සංවාද ඉතිහාසය සහ චැට් ආදානය ---
if st.session_state.get('processed_file_id') and uploaded_file:
    with st.sidebar:
        st.image(uploaded_file, caption="ඔබේ ශාකය")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("ඔබේ පිළිතුර මෙහි ඇතුළත් කරන්න..."):
    if not st.session_state.get('processed_file_id'):
        st.warning("කරුණාකර පළමුව ඡායාරූපයක් උඩුගත කරන්න."); st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # අදියර 1: ශාකයේ නම තහවුරු කිරීම
    if st.session_state.awaiting_confirmation:
        st.session_state.awaiting_confirmation = False
        if any(word in prompt.lower() for word in ["ඔව්", "ඔවු", "ow", "yes"]):
            with st.spinner("මූලික විශ්ලේෂණය කරමින්..."):
                try:
                    image = Image.open(uploaded_file)
                    response = preliminary_model.generate_content([f"මෙය {st.session_state.plant_name} ශාකයකි.", image])
                    analysis_match = re.search(r"\[ANALYSIS\]: (.*?)\n\[QUESTIONS\]:", response.text, re.DOTALL)
                    questions_match = re.search(r"\[QUESTIONS\]: (.*)", response.text, re.DOTALL)

                    if analysis_match and questions_match:
                        st.session_state.initial_analysis = analysis_match.group(1).strip()
                        questions = questions_match.group(1).strip().replace(" | ", "\n- ")
                        follow_up_message = (f"හොඳයි. මූලික නිරීක්ෂණයට අනුව, {st.session_state.initial_analysis.lower()}.\n\n"
                                           f"රෝගය නිවැරදිව හඳුනාගැනීම සඳහා, කරුණාකර මෙම ප්‍රශ්නවලට පිළිතුරු දෙන්න:\n- {questions}")
                        st.session_state.messages.append({"role": "assistant", "content": follow_up_message})
                        st.session_state.awaiting_environmental_info = True
                        st.rerun()
                    else:
                        st.error("විශ්ලේෂණය කිරීමේදී දෝෂයක් ඇතිවිය (ආකෘතියේ ප්‍රතිචාරය නොගැලපේ). කරුණාකර නැවත උත්සාහ කරන්න.")
                except Exception as e:
                    st.error(f"මූලික විශ්ලේෂණයේදී දෝෂයක්: {e}")
        else:
            st.session_state.messages.append({"role": "assistant", "content": "තේරුම් ගත්තා. කරුණාකර වෙනත් ඡායාරූපයක් උඩුගත කරන්න."})
            time.sleep(3); reset_session()

    # අදියර 2: අවසන් විශ්ලේෂණ වාර්තාව ලබා දීම
    elif st.session_state.awaiting_environmental_info:
        st.session_state.awaiting_environmental_info = False
        with st.chat_message("assistant"):
            image = Image.open(uploaded_file)
            final_prompt = (f"ශාකය: {st.session_state.plant_name}.\n"
                            f"මූලික රෝග ලක්ෂණ: {st.session_state.initial_analysis}.\n"
                            f"පරිශීලකයාගේ පිළිතුරු: {prompt}\n\n"
                            "ඉහත සියලු තොරතුරු සහ ඡායාරූපය මත පදනම්ව සවිස්තරාත්මක, අවසන් වාර්තාව සපයන්න.")
            
            response_stream = final_model.generate_content([final_prompt, image], stream=True)
            full_response = st.write_stream(response_stream)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

    # >>>>>>>> නිවැරදි කළ කොටස: අඛණ්ඩ සංවාදය <<<<<<<<<
    # අදියර 3: විශ්ලේෂණයෙන් පසු තවත් ඕනෑම ප්‍රශ්නයකට පිළිතුරු දීම
    else:
        with st.spinner("පිළිතුර සකසමින්..."):
            try:
                # සන්දර්භය සඳහා සම්පූර්ණ සංවාද ඉතිහාසය ලබා දීම
                history_for_model = []
                for msg in st.session_state.messages[:-1]: # වත්මන් ප්‍රශ්නය හැර
                    role = "model" if msg["role"] == "assistant" else "user"
                    history_for_model.append({"role": role, "parts": [msg["content"]]})

                image = Image.open(uploaded_file)
                chat = follow_up_model.start_chat(history=history_for_model)
                
                # Streaming සමඟ පිළිතුර යැවීම
                response_stream = chat.send_message([prompt, image], stream=True)
                
                with st.chat_message("assistant"):
                    full_response = st.write_stream(response_stream)
                
                # සංවාද ඉතිහාසයට නව පිළිතුර එක් කිරීම
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"පිළිතුරු දීමේදී දෝෂයක්: {e}")

st.divider()
st.caption("⚠ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")