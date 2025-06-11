import streamlit as st
from google import generativeai as genai
from PIL import Image
import io
import base64  # Required to encode the image

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Plant Health Analyzer",
    page_icon="🌿",  # A more detailed emoji
    layout="centered"
)

# --- Function to encode image to Base64 ---
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- Custom CSS for Background and UI Elements ---
def add_custom_css():
    try:
        # Get the encoded image
        img_encoded = get_img_as_base64("background.jpg")
        
        # Define the CSS
        # This CSS will apply the background, style the chat messages, and the sidebar
        css = f"""
        <style>
            /* --- Main App Background --- */
            [data-testid="stAppViewContainer"] > .main {{
                background-image: url("data:image/png;base64,{img_encoded}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}

            /* --- Title and Header --- */
            h1, h2, h3 {{
                color: #FFFFFF; /* White text for titles */
                text-shadow: 2px 2px 4px #000000; /* Black shadow for readability */
            }}
            
            /* --- Sidebar Styling --- */
            [data-testid="stSidebar"] {{
                background: rgba(20, 40, 20, 0.7); /* Dark green, semi-transparent */
                backdrop-filter: blur(5px); /* Frosted glass effect */
                border-right: 2px solid rgba(255, 255, 255, 0.1);
            }}
            
            /* --- Chat Message Styling --- */
            [data-testid="stChatMessage"] {{
                background: rgba(255, 255, 255, 0.85); /* Light, semi-transparent */
                backdrop-filter: blur(5px);
                border-radius: 15px;
                border: 1px solid rgba(0, 0, 0, 0.1);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                color: #1E1E1E; /* Dark text for chat bubbles */
            }}
            
            /* Change the user message bubble color slightly */
            [data-testid="stChatMessage"] .message-content-user {{
                 background: rgba(200, 230, 200, 0.85); /* A light green tint for user messages */
            }}

            /* --- Other UI elements --- */
            .st-bk, .st-b3, .st-bb {{ /* Targets various text elements for readability */
                color: #FFFFFF;
                text-shadow: 1px 1px 2px #000000;
            }}

            [data-testid="stFileUploader"] label, [data-testid="stCaptionContainer"] p {{
                color: #E0E0E0; /* Lighter text for labels and captions */
                text-shadow: 1px 1px 2px #000000;
            }}
            
            /* --- Chat Input --- */
            [data-testid="stChatInput"] {{
                 background: transparent;
            }}
            [data-testid="stChatInput"] > div {{
                background: rgba(255, 255, 255, 0.9); /* White semi-transparent input box */
                border-radius: 15px;
            }}
            
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

    except FileNotFoundError:
        st.warning("`background.jpg` not found. Please add it to your project directory for the custom background.")


# Apply the custom UI
add_custom_css()


# --- API Configuration ---
try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("GEMINI_API_KEY not found. Please add it to your Streamlit secrets.")
    st.stop()

# --- System Instruction for the AI Model ---
SYSTEM_INSTRUCTION = "You are an expert botanist and plant pathologist. Your goal is to analyze user-uploaded plant images and answer their questions in a conversational manner..." # Same as before, truncated for brevity

# --- Model Configuration ---
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- Session State Initialization ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "image" not in st.session_state:
    st.session_state.image = None

# --- UI and Logic ---
st.title("🌿 Plant Health Analyzer")
st.write("Upload a plant photo, then ask questions in the chat box below.")

# --- Sidebar for File Upload and Control ---
with st.sidebar:
    st.header("Your Plant")
    uploaded_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file:
        st.session_state.image = Image.open(uploaded_file)
        st.image(st.session_state.image, caption="Your Plant")

    if st.button("✨ New Chat"):
        st.session_state.chat_session = None
        st.session_state.messages = []
        st.session_state.image = None
        st.rerun()

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input Logic ---
if prompt := st.chat_input("Ask a question about your plant..."):
    if st.session_state.image is None:
        st.warning("Please upload a plant photo in the sidebar first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Analyzing..."):
        try:
            if st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat()
                response = st.session_state.chat_session.send_message(
                    [prompt, st.session_state.image], stream=True
                )
            else:
                response = st.session_state.chat_session.send_message(
                    prompt, stream=True
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
            st.error(f"An error occurred: {e}")

st.divider()
st.caption("Disclaimer: This AI analysis is for informational purposes only.")