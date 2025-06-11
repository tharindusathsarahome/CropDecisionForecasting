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

When the user first sends an image and a question, analyze it carefully using this guide:
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
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- Session State Initialization ---
# This is the core of the chatbot functionality
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "image" not in st.session_state:
    st.session_state.image = None


# --- UI and Logic ---
st.title("🌱 Plant Health Analyzer")
st.write("Upload a plant photo, then ask questions in the chat box below.")

# --- Sidebar for File Upload and Control ---
with st.sidebar:
    st.header("Your Plant")
    uploaded_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file:
        st.session_state.image = Image.open(uploaded_file)
        st.image(st.session_state.image, caption="Your Plant")

    if st.button("New Chat"):
        # Reset the chat session and messages
        st.session_state.chat_session = None
        st.session_state.messages = []
        st.session_state.image = None
        st.rerun() # Rerun to clear the page

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input Logic ---
if prompt := st.chat_input("Ask a question about your plant..."):
    # 1. Check if an image has been uploaded
    if st.session_state.image is None:
        st.warning("Please upload a plant photo in the sidebar first.")
        st.stop()

    # 2. Add user's message to the display history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Handle the conversation with the model
    with st.spinner("Analyzing..."):
        try:
            # If it's the first message, start a new chat with the image
            if st.session_state.chat_session is None:
                st.session_state.chat_session = model.start_chat()
                # Send the image and the first prompt
                response = st.session_state.chat_session.send_message(
                    [prompt, st.session_state.image],
                    stream=True
                )
            # For subsequent messages, just send the prompt
            else:
                response = st.session_state.chat_session.send_message(
                    prompt,
                    stream=True
                )
            
            # 4. Stream the response to the UI
            with st.chat_message("assistant"):
                full_response = ""
                placeholder = st.empty()
                for chunk in response:
                    full_response += chunk.text
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
            
            # 5. Add the full response to the message history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"An error occurred: {e}")

st.divider()
st.caption("Disclaimer: This AI analysis is for informational purposes only and is not a substitute for professional botanical or agricultural advice.")