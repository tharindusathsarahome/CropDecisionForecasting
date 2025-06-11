import streamlit as st
from google import generativeai as genai
from PIL import Image
import base64
import os
import io

# Streamlit UI
st.title("🌱 Plant Health AAnalyzer")
st.write("Upload a plant photo for health diagnosis and care recommendations")

# Get API key directly from Streamlit secrets
api_key = st.secrets['GEMINI_API_KEY']

# Configure the Gemini API
genai.configure(api_key=api_key)

# System instruction for plant analysis
SYSTEM_INSTRUCTION = """
Analyze plant images carefully using this guide:

1. Identify visible plant parts:
   - Leaves, flowers, stems/branches, roots, soil, or whole plant

2. Try to identify plant species:
   - Based on leaf shape, flower color, structure
   - Say "Unknown species" if unsure

3. Check plant health by examining:
   - Leaves: Color, shape, spots, discoloration, curling, deformities
   - Flowers: Bloom status, color, damage, wilting
   - Stems/Branches: Firmness, cracks, spots, mold, rot
   - Soil/Base: Moisture level, mold, pests (if visible)
   - Pests/Damage: Insects, eggs, webs, bite marks, sticky residue
   - Growth/Environment: Healthy/stunted, sunburn, frost damage, stress

4. If photo is unclear/insufficient:
   - Say: "This image doesn't show enough details to properly assess the plant."
   - Request additional photos: close-ups of leaves (top/underside), flowers, stems, full plant view, roots/soil area

5. For sufficient images, provide full report:
   - Plant parts analyzed
   - Identified plant name/possible species
   - Health status: Healthy, Slightly affected, Clearly diseased
   - Symptoms observed
   - Possible causes: fungal infection, pests, environmental stress, nutrient deficiency, etc.
   - Basic care/treatment suggestions

"""

# Set the model name
model_name = "gemini-2.5-pro-preview-06-05"  # Using the vision model that can process images

# Set generation parameters
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 2048
}

# Initialize the model
model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    
    with st.spinner("Analyzing plant health..."):
        try:
            # Prepare image for Gemini
            # Convert the image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Create prompt
            prompt = "Analyze this plant image based on the following guidelines: " + SYSTEM_INSTRUCTION
            
            # Generate content
            response = model.generate_content(
                [
                    prompt,
                    {"mime_type": f"image/{image.format.lower() if image.format else 'jpeg'}", "data": img_byte_arr}
                ]
            )
            
            # Display results
            st.subheader("Analysis Results")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"Error analyzing image: {str(e)}")
            st.info("Please try again with a clearer or different photo")

st.divider()
st.caption("Note: For best results, provide clear, well-lit photos showing specific plant parts. "
           "The AI may request additional images if needed for accurate diagnosis.")