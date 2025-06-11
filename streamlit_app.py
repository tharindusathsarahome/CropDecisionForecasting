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
st.write("Upload a plant photo, ask a question, and get an AI-powered diagnosis and care recommendations.")

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
You are an expert botanist and plant pathologist. Your goal is to analyze user-uploaded plant images and answer their questions.

Analyze plant images carefully using this guide:

1.  **Identify Visible Plant Parts**: Note leaves, flowers, stems, soil, etc.
2.  **Identify Plant Species**: Attempt to identify the plant. If unsure, state "Unknown species" but describe its features.
3.  **Assess Plant Health**: Look for signs of disease, pests, or stress.
    *   **Leaves**: Check for discoloration (yellowing, browning), spots, holes, curling, or wilting.
    *   **Stems/Branches**: Look for weakness, breaks, spots, or mold.
    *   **Flowers**: Note wilting, discoloration, or lack of blooms.
    *   **Pests/Damage**: Look for insects, webs, eggs, or bite marks.
4.  **Formulate Response**: Based on your analysis and the user's specific question, provide a comprehensive report.
    *   **Direct Answer**: First, directly answer the user's question.
    *   **Overall Health Status**: (e.g., Healthy, Stressed, Diseased).
    *   **Symptoms Observed**: Detail the specific signs you've identified.
    *   **Possible Causes**: Suggest potential reasons (e.g., fungal infection, overwatering, nutrient deficiency, pest infestation).
    *   **Care & Treatment Suggestions**: Provide clear, actionable steps for treatment and future care.

If the image is unclear or insufficient, state that and politely request more specific photos (e.g., a close-up of leaves, a view of the whole plant).
"""

# --- Model Configuration ---
model_name = "gemini-1.5-pro-latest"  # A powerful vision model
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

# Initialize the model
model = genai.GenerativeModel(
    model_name=model_name,
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION  # Set the system instruction
)


# --- User Input Fields ---
uploaded_file = st.file_uploader("1. Upload a photo of your plant", type=["jpg", "jpeg", "png"])
user_question = st.text_input("2. Ask a question about your plant", placeholder="e.g., Why are the leaves turning yellow?")

# Display the uploaded image if available
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Your Uploaded Plant Image", use_column_width=True)

# --- Analysis Trigger ---
if st.button("Analyze Plant Health", type="primary"):
    if uploaded_file is None:
        st.warning("Please upload an image first.")
    elif not user_question:
        st.warning("Please ask a question about your plant.")
    else:
        with st.spinner("Analyzing your plant... This may take a moment."):
            try:
                # Prepare image for Gemini API
                img_byte_arr = io.BytesIO()
                # Convert image to RGB to handle all formats (like PNG with transparency)
                rgb_image = image.convert('RGB')
                rgb_image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()
                
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": img_bytes
                }

                # Combine the user question and the image into a single prompt
                prompt_parts = [
                    image_part,
                    user_question,
                ]
                
                # Generate content using the new prompt structure
                response = model.generate_content(prompt_parts)
                
                # Display results
                st.subheader("Analysis Results")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"An error occurred during analysis: {str(e)}")
                st.info("Please try again. If the problem persists, the image might be corrupted or there could be an issue with the API.")

st.divider()
st.caption("Disclaimer: This AI analysis is for informational purposes only and is not a substitute for professional botanical or agricultural advice.")