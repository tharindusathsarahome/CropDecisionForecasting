import streamlit as st
from google import generativeai as genai
from PIL import Image
import io

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Plant Health Analyzer",
    page_icon="🌱",
    layout="centered"
)

# --- Streamlit UI ---
st.title("🌱 Plant Health Analyzer")
st.write("Upload a plant photo, ask a question, and get AI-powered analysis. You can ask follow-up questions in the chat!")

# --- API Configuration ---
# Get API key directly from Streamlit secrets
try:
    api_key = st.secrets['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("GEMINI_API_KEY not found. Please add it to your Streamlit secrets.")
    st.stop()


# --- System Instruction for the AI Model ---
SYSTEM_INSTRUCTION = """
You are an expert botanist and plant pathologist. Your goal is to analyze user-uploaded plant images and answer their questions in a conversational manner.

When the user first uploads an image and asks a question, analyze it carefully using this guide:
1.  **Identify Visible Plant Parts**: Note leaves, flowers, stems, soil, etc.
2.  **Identify Plant Species**: Attempt to identify the plant. If unsure, state "Unknown species" but describe its features.
3.  **Assess Plant Health**: Look for signs of disease, pests, or stress (discoloration, spots, holes, curling, wilting, insects, webs).
4.  **Formulate Initial Response**: Based on your analysis and the user's specific question, provide a comprehensive report.
    *   **Direct Answer**: First, directly answer the user's question.
    *   **Overall Health Status**: (e.g., Healthy, Stressed, Diseased).
    *   **Symptoms Observed**: Detail the specific signs you've identified.
    *   **Possible Causes**: Suggest potential reasons (e.g., fungal infection, overwatering, nutrient deficiency).
    *   **Care & Treatment Suggestions**: Provide clear, actionable steps.

For all follow-up questions, maintain the context of the original image and conversation. Provide concise, helpful answers. If the image is unclear or lacks detail for a specific question, state that and politely explain what you can and cannot see.
"""

# --- Model Configuration ---
model_name = "gemini-1.5-pro-latest"
model = genai.GenerativeModel(
    model_name=model_name,
    system_instruction=SYSTEM_INSTRUCTION
)

# --- Session State Initialization ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper function to handle image processing ---
def process_image(uploaded_file):
    image = Image.open(uploaded_file)
    # Convert image to RGB to handle all formats (like PNG with transparency)
    rgb_image = image.convert('RGB')
    img_byte_arr = io.BytesIO()
    rgb_image.save(img_byte_arr, format='JPEG')
    return {
        "mime_type": "image/jpeg",
        "data": img_byte_arr.getvalue()
    }

# --- Sidebar for Initial Input ---
with st.sidebar:
    st.header("New Analysis")
    uploaded_file = st.file_uploader("1. Upload a photo of your plant", type=["jpg", "jpeg", "png"])
    initial_question = st.text_input("2. Ask an initial question", placeholder="e.g., Why are the leaves yellow?")

    if st.button("Start Analysis", type="primary"):
        if uploaded_file and initial_question:
            with st.spinner("Starting analysis..."):
                try:
                    # Reset chat for new analysis
                    st.session_state.messages = []
                    st.session_state.chat_session = model.start_chat(history=[]) # Start a new fresh chat
                    
                    image_part = process_image(uploaded_file)
                    
                    # Add user's first message to display history
                    st.session_state.messages.append({"role": "user", "content": [{"type": "text", "text": initial_question}, {"type": "image_url", "image_url": uploaded_file}]})

                    # Send the initial prompt with the image to Gemini
                    response = st.session_state.chat_session.send_message([initial_question, image_part])
                    
                    # Add Gemini's response to display history
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    st.rerun() # Rerun to display the chat
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please upload a photo and ask a question.")

# --- Main Chat Interface ---

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Handle the complex content of the user's first message
        if isinstance(message["content"], list):
            for part in message["content"]:
                if part["type"] == "text":
                    st.markdown(part["text"])
                elif part["type"] == "image_url":
                    st.image(part["image_url"], width=250)
        else: # For assistant messages and subsequent user messages
             st.markdown(message["content"])

# Chat input for follow-up questions
if prompt := st.chat_input("Ask a follow-up question..."):
    if not st.session_state.chat_session:
        st.warning("Please start a new analysis from the sidebar first.")
        st.stop()

    # Add user's new message to display history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send the follow-up prompt to Gemini
    with st.spinner("Thinking..."):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            # Add Gemini's response to display history
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            # Rerun to display the new message immediately
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")

st.divider()
st.caption("Disclaimer: This AI analysis is for informational purposes only and is not a substitute for professional botanical or agricultural advice.")