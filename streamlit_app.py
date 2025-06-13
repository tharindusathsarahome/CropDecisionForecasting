import streamlit as st
from google import generativeai as genai
from PIL import Image
import io
import time
import re
from fpdf import FPDF

# --- Streamlit පිටු සැකසුම ---
st.set_page_config(
    page_title="Plant Disease Analyzer",
    page_icon="🌱",
    layout="centered"
)

# --- PDF Generation Function ---
class PDF(FPDF):
    def header(self):
        pass
    def footer(self):
        self.set_y(-15)
    # Italic ('I') වෙනුවට Regular ('') භාවිතා කරන්න
        self.set_font('IskoolaPota', '', 8) 
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(text):
    pdf = PDF()
    try:
        # uni=True is important for Unicode fonts
        pdf.add_font('IskoolaPota', '', 'fonts/IskoolaPota-Regular.ttf', uni=True) 
    except RuntimeError:
        st.error("ෆොන්ට් ගොනුව ('fonts/IskoolaPota-Regular.ttf') සොයාගත නොහැක. කරුණාකර එය නිවැරදිව ස්ථානගත කරන්න.")
        return None
        
    pdf.set_font('IskoolaPota', '', 12)
    pdf.add_page()
    pdf.multi_cell(0, 10, text)
    
    # .encode('latin-1') කොටස ඉවත් කරන්න.
    # pdf.output(dest='S') මගින් කෙලින්ම bytes ලබා දේ.
    return pdf.output(dest='S')

# --- API යතුර සැකසීම ---
try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("GEMINI_API_KEY සොයාගත නොහැක. කරුණාකර එය ඔබගේ Streamlit රහස් වෙත එක් කරන්න.")
    st.stop()

# --- AI ආකෘති සඳහා පද්ධති උපදෙස් ---
IDENTIFICATION_INSTRUCTION = "ඔබේ එකම කාර්යය වන්නේ ලබා දී ඇති ඡායාරූපයේ ඇති ශාකයේ නම සිංහලෙන් හඳුනා ගැනීමයි. පිළිතුර ලෙස ශාකයේ නම පමණක් ලබා දෙන්න. උදාහරණයක් ලෙස: 'රෝස' හෝ 'තක්කාලි'. හඳුනාගත නොහැකි නම්, 'හඳුනාගත නොහැක' ලෙස පමණක් සඳහන් කරන්න."
PRELIMINARY_ANALYSIS_INSTRUCTION = "ඔබ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. ඔබගේ සියලුම පිළිතුරු සිංහල භාෂාවෙන් පමණක් ලබා දෙන්න. ලබා දී ඇති ඡායාරූපය සහ ශාකයේ නම මත පදනම්ව, රෝගය නිවැරදිව හඳුනාගැනීමට උපකාරී වන සරල ප්‍රශ්න 2-3ක් සිංහලෙන් අසන්න. මෙම ප්‍රශ්න කාලගුණය, හිරු එළිය, සහ ජලය දැමීම වැනි දේ ගැන විය යුතුය. ප්‍රතිචාරය පහත ආකෘතියට අනුව පමණක් ලබා දෙන්න:\n[ANALYSIS]: <ඔබ හඳුනාගත් රෝග ලක්ෂණ පිළිබඳ කෙටි සාරාංශයක්>\n[QUESTIONS]: <ප්‍රශ්නය 1> | <ප්‍රශ්නය 2>"
FINAL_ANALYSIS_INSTRUCTION = "ඔබ පිළිතුරු සැපයිය යුත්තේ සිංහල භාෂාවෙන් පමණි. ඔබ උද්භිද විද්‍යාව සහ ශාක රෝග පිළිබඳ විශේෂඥයෙකි. පරිශීලකයා ඉංග්‍රීසියෙන් ඇසුවද ඔබේ පිළිතුරු සිංහලෙන් විය යුතුය. ඔබට දැන් මූලික රෝග ලක්ෂණ විශ්ලේෂණයක් සහ පරිශීලකයා විසින් සපයන ලද පාරිසරික තොරතුරු ලැබී ඇත. මෙම සියලු තොරතුරු භාවිතා කර, පහත සඳහන් දෑ ඇතුළත් සවිස්තරාත්මක සහ අවසාන වාර්තාවක් සපයන්න:\n1.  **නිශ්චිත රෝග විනිශ්චය:** විය හැකි රෝගයේ නම.\n2.  **හේතු:** පරිශීලකයාගේ පිළිතුරු ද සැලකිල්ලට ගනිමින් හේතු පැහැදිලි කරන්න.\n3.  **විසඳුම් සහ පාලනය:** ක්ෂණික පියවර, කාබනික ප්‍රතිකාර, රසායනික ප්‍රතිකාර, සහ වැළැක්වීමේ ක්‍රම ලෙස කොටස් කර ඉදිරිපත් කරන්න."
FOLLOW_UP_INSTRUCTION = "ඔබ ශාක රෝග පිළිබඳ විශේෂඥ සහායකයෙකි. ඔබ සහ පරිශීලකයා අතර සම්පූර්ණ සංවාදයක් මේ වන විට සිදුවී ඇත. සංවාදයේ සන්දර්භය (ශාකයේ නම, රෝග ලක්ෂණ, ඔබගේ පෙර විශ්ලේෂණය) මත පදනම්ව පරිශීලකයාගේ වැඩිදුර ප්‍රශ්නවලට පිළිතුරු දෙන්න. ඔබේ සියලුම පිළිතුරු සිංහල භාෂාවෙන් පමණක් ලබා දෙන්න, පරිශීලකයා ඉංග්‍රීසියෙන් ප්‍රශ්න ඇසුවද. පිළිතුරු කෙටි සහ අදාළ ලෙස තබා ගන්න."

# --- ආකෘති සැකසුම (නිවැරදි කරන ලදී) ---
identification_model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", system_instruction=IDENTIFICATION_INSTRUCTION)
preliminary_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=PRELIMINARY_ANALYSIS_INSTRUCTION)
final_report_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FINAL_ANALYSIS_INSTRUCTION)
follow_up_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", system_instruction=FOLLOW_UP_INSTRUCTION)

# --- Session State ආරම්භ කිරීම ---
if "messages" not in st.session_state: st.session_state.messages = []
if "conversation_stage" not in st.session_state: st.session_state.conversation_stage = "initial"
if "plant_name" not in st.session_state: st.session_state.plant_name = ""
if "initial_analysis" not in st.session_state: st.session_state.initial_analysis = ""
if "final_report_content" not in st.session_state: st.session_state.final_report_content = ""
if "processed_file_id" not in st.session_state: st.session_state.processed_file_id = None
if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
if "image_bytes" not in st.session_state: st.session_state.image_bytes = None

def reset_session():
    uploader_key = st.session_state.get('uploader_key', 0)
    st.session_state.clear()
    st.session_state.uploader_key = uploader_key + 1
    st.session_state.conversation_stage = "initial"
    st.rerun()

# --- UI සහ ක්‍රියාවලි ---
st.title("🌱 Plant Disease Analyzer")
st.write("ඔබේ ශාකයේ රෝගී තත්ත්වයක් ඇති කොටසක පැහැදිලි ඡායාරූපයක් පැති තීරුවෙන් උඩුගත කරන්න.")

with st.sidebar:
    st.header("ඔබේ ශාකය")
    uploaded_file = st.file_uploader("ඡායාරූපයක් උඩුගත කරන්න", type=["jpg", "jpeg", "png"], key=f"uploader_{st.session_state.uploader_key}")
    if st.button("🔄 නව සංවාදයක්"):
        reset_session()

# --- හඳුනාගැනීමේ ක්‍රියාවලිය ---
if uploaded_file and uploaded_file.file_id != st.session_state.processed_file_id:
    st.session_state.messages = []
    st.session_state.final_report_content = ""
    st.session_state.processed_file_id = uploaded_file.file_id
    img_bytes = uploaded_file.getvalue()
    st.session_state.image_bytes = img_bytes
    image = Image.open(io.BytesIO(img_bytes))
    with st.spinner("ශාකය හඳුනාගනිමින් පවතී..."):
        try:
            response = identification_model.generate_content(image)
            plant_name = response.text.strip()
            unrecognized_keywords = ["හඳුනාගත", "නොහැක", "අපහසුයි", "පැහැදිලි නැත"]
            is_unrecognized = (not plant_name or any(keyword in plant_name for keyword in unrecognized_keywords) or len(plant_name.split()) > 3)
            if is_unrecognized:
                st.error("සමාවන්න, මෙම ඡායාරූපයෙන් ශාකය පැහැදිලිව හඳුනාගත නොහැක. කරුණාකර වඩාත් පැහැදිලි ඡායාරූපයක් උඩුගත කරන්න.")
                time.sleep(3)
                reset_session()
            else:
                st.session_state.plant_name = plant_name
                st.session_state.conversation_stage = "awaiting_confirmation"
                st.session_state.messages.append({"role": "assistant", "content": f"මෙය '{plant_name}' ශාකයක්ද? (ඔව් / නැත)"})
                st.rerun()
        except Exception as e:
            st.error(f"ශාකය හඳුනාගැනීමේදී දෝෂයක් ඇතිවිය: {e}")
            time.sleep(3); reset_session()

# --- සංවාද ඉතිහාසය සහ UI ---
if st.session_state.processed_file_id:
    with st.sidebar:
        st.image(st.session_state.image_bytes, caption="ඔබේ ශාකය")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.final_report_content:
    pdf_bytes = generate_pdf(st.session_state.final_report_content)
    if pdf_bytes:
        st.download_button(label="📄 වාර්තාව PDF ලෙස බාගන්න", data=pdf_bytes, file_name=f"{st.session_state.plant_name}_analysis_report.pdf", mime="application/pdf")

def handle_streaming_response(response_stream):
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        for chunk in response_stream:
            full_response += chunk.text
            placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    return full_response

# --- චැට් ආදානය සහ ක්‍රියාවලි ---
if prompt := st.chat_input("ඔබේ පිළිතුර/ප්‍රශ්නය මෙහි ඇතුළත් කරන්න..."):
    if not st.session_state.processed_file_id:
        st.warning("කරුණාකර පළමුව ඡායාරූපයක් උඩුගත කරන්න."); st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    stage = st.session_state.conversation_stage
    image = Image.open(io.BytesIO(st.session_state.image_bytes))

    if stage == "awaiting_confirmation":
        if any(word in prompt.lower() for word in ["ඔව්", "ඔවු", "ow", "yes"]):
            with st.spinner("මූලික විශ්ලේෂණය කරමින්..."):
                try:
                    response = preliminary_model.generate_content([f"මෙය {st.session_state.plant_name} ශාකයකි.", image])
                    analysis_match = re.search(r"\[ANALYSIS\]: (.*?)\n\[QUESTIONS\]:", response.text, re.DOTALL)
                    questions_match = re.search(r"\[QUESTIONS\]: (.*)", response.text, re.DOTALL)
                    if analysis_match and questions_match:
                        st.session_state.initial_analysis = analysis_match.group(1).strip()
                        questions = questions_match.group(1).strip().replace(" | ", "\n- ")
                        follow_up_message = (f"හොඳයි. මූලික නිරීක්ෂණයට අනුව, {st.session_state.initial_analysis.lower()}.\n\n"
                                           f"රෝගය නිවැරදිව හඳුනාගැනීම සඳහා, කරුණාකර මෙම ප්‍රශ්නවලට පිළිතුරු දෙන්න:\n- {questions}")
                        st.session_state.messages.append({"role": "assistant", "content": follow_up_message})
                        st.session_state.conversation_stage = "awaiting_environmental_info"
                        st.rerun()
                    else: st.error("විශ්ලේෂණය කිරීමේදී දෝෂයක් ඇතිවිය (ආකෘතියේ ප්‍රතිචාරය නොගැලපේ).")
                except Exception as e: st.error(f"මූලික විශ්ලේෂණයේදී දෝෂයක්: {e}")
        else:
            st.session_state.messages.append({"role": "assistant", "content": "තේරුම් ගත්තා. කරුණාකර වෙනත් ඡායාරූපයක් උඩුගත කරන්න."})
            time.sleep(3); reset_session()

    elif stage == "awaiting_environmental_info":
        with st.spinner("ඔබගේ පිළිතුරු අනුව අවසන් වාර්තාව සකසමින්..."):
            try:
                final_prompt = (f"ශාකය: {st.session_state.plant_name}.\n"
                                f"මූලික රෝග ලක්ෂණ: {st.session_state.initial_analysis}.\n"
                                f"පරිශීලකයාගේ පිළිතුරු: {prompt}\n\n"
                                "ඉහත සියලු තොරතුරු සහ ඡායාරූපය මත පදනම්ව සවිස්තරාත්මක, අවසන් වාර්තාව සපයන්න.")
                
                # නිවැරදි, වෙන් කරන ලද ආකෘතිය භාවිතා කිරීම
                response_stream = final_report_model.generate_content([final_prompt, image], stream=True)
                
                full_response = handle_streaming_response(response_stream)
                st.session_state.final_report_content = full_response
                
                follow_up_prompt_msg = "විශ්ලේෂණය අවසන්. ඔබට මේ සම්බන්ධයෙන් තවත් ප්‍රශ්න ඇත්නම් දැන් විමසන්න."
                st.session_state.messages.append({"role": "assistant", "content": follow_up_prompt_msg})
                
                st.session_state.conversation_stage = "follow_up_chat"
                st.rerun()
            except Exception as e:
                st.error(f"අවසාන විශ්ලේෂණයේදී දෝෂයක්: {e}")

    elif stage == "follow_up_chat":
        with st.spinner("පිළිතුර සකසමින්..."):
            try:
                chat_history = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.messages]
                chat_history.pop()

                # නිවැරදි, වෙන් කරන ලද ආකෘතිය භාවිතා කිරීම
                chat = follow_up_model.start_chat(history=chat_history)
                response_stream = chat.send_message(prompt, stream=True)
                handle_streaming_response(response_stream)
                st.rerun()
            except Exception as e:
                st.error(f"පිළිතුර සැකසීමේදී දෝෂයක් ඇතිවිය: {e}")

st.divider()
st.caption("⚠️ මෙම AI විශ්ලේෂණය වෘත්තීය කෘෂිකාර්මික උපදෙස් සඳහා ආදේශකයක් වේ.")