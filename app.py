import streamlit as st
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from google import genai
from google.genai import types
from vertexai.preview.vision_models import ImageGenerationModel
import os
import time
from io import BytesIO
import base64
from PIL import Image

def generate_content(project_id: str, location: str, model_name: str, prompt_data: dict, starting_image_path: str = None):
    """Generates content using a generative model."""
    vertexai.init(project=project_id, location=location)

    if "veo" in model_name:
        try:
            client = genai.Client(vertexai=True, project=project_id, location=location)

            if "prompt" in prompt_data:
                final_prompt = prompt_data["prompt"]
                st.info(f"Using Custom Prompt: {final_prompt}")
            else:
                keywords = [
                    prompt_data.get('subject'),
                    prompt_data.get('action'),
                    prompt_data.get('scene')
                ]
                optional_keywords = [
                    prompt_data.get('camera_angle'),
                    prompt_data.get('camera_movement'),
                    prompt_data.get('lens_effects'),
                    prompt_data.get('style'),
                    prompt_data.get('temporal_elements'),
                    prompt_data.get('sound_effects'),
                ]
                for keyword in optional_keywords:
                    if keyword and keyword != "None":
                        keywords.append(keyword)

                dialogue = prompt_data.get('dialogue', "")
                if dialogue:
                    keywords.append(dialogue)

                keywords = [k for k in keywords if k]

                persona = prompt_data.get('persona')
                persona_instruction = ""
                if persona and persona != "None":
                    persona_instruction = f"The final video should be tailored for this persona: {persona}."

                gemini_prompt = f"""
You are an expert video prompt engineer for Google's Veo model. Your task is to construct the most effective and optimal prompt string using the following keywords. {persona_instruction} Every single keyword MUST be included. Synthesize them into a single, cohesive, and cinematic instruction. Do not add any new core concepts. Output ONLY the final prompt string, without any introduction or explanation. Mandatory Keywords: {",".join(keywords)}
"""
                gemini_model = "gemini-2.5-flash"
                response = client.models.generate_content(
                    model=gemini_model,
                    contents=gemini_prompt,
                )
                final_prompt = response.text.strip()
                st.info(f"Generated Prompt: {final_prompt}")

            video_model = veo_model_name # Or the specific model name from the UI
            generate_videos_args = {
                "model": video_model,
                "prompt": final_prompt,
                "config": types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    number_of_videos=1,
                    duration_seconds=8,
                    person_generation="allow_adult",
                    enhance_prompt=prompt_data.get('enhance_prompt', True),
                    generate_audio=prompt_data.get('generate_audio', True),
                ),
            }
            if starting_image_path:
                generate_videos_args["image"] = types.Image.from_file(location=starting_image_path)

            operation = client.models.generate_videos(**generate_videos_args)
            # This will block until the video is generated.
            st.info("Video generation in progress... this may take a few minutes.")
            while not operation.done:
                time.sleep(15)
                operation = client.operations.get(operation)
                print(operation)

            if operation.response:
                result = operation.result.generated_videos[0].video.video_bytes
            st.info("generation done!")
            return result

        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None
    elif "imagen" in model_name:
        try:
            generation_model = ImageGenerationModel.from_pretrained(model_name)
            response = generation_model.generate_images(
                prompt=prompt_data.get('prompt'),
                negative_prompt=prompt_data.get('negative_prompt'),
                aspect_ratio=prompt_data.get('aspect_ratio', "1:1"),
            )
            # Return the first generated image
            return response.images[0]
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None
    else:
        if model_name == "gemini-2.5-flash-image":
            try:
                client = genai.Client(vertexai=True, project=project_id, location=location)
                # generation_model = ImageGenerationModel.from_pretrained(model_name)
                content = []
                image_paths = prompt_data.get('images')
                text = prompt_data.get('prompt')
                if image_paths:
                    if(text):
                        content.append(text)
                    for image_path in image_paths:
                        content.append(Image.open(image_path))
                    response = client.models.generate_content(
                        model=model_name,
                        contents=content
                    )
                else:
                    response = client.models.generate_content(
                        prompt=prompt_data.get('prompt'),
                    )
                # Return the first generated image
                
                return response
            except Exception as e:
                st.error(f"An error occurred: {e}")
                return None
        else:
            return f"Unknown model selected: {model_name}"

# Page configuration
st.set_page_config(page_title="Genmedia Playground", layout="wide")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    project_id = st.text_input("GCP Project ID", "")
    location = st.text_input("GCP Location", "us-central1")

    st.header("Prompting Tips")
    st.info(
        """
        - **Be specific:** The more detailed your prompt, the better the result.
        - **Provide context:** Give the model context to understand your request.
        - **Use examples:** Show the model what you want with examples.
        - **Experiment:** Try different phrasings and see what works best.
        """
    )

# Main content
st.title("VEO & Imagen Prompt Interface")

tab1, tab2, tab3 = st.tabs(["VEO", "Imagen", "Gemini 2.5 Flash Image (Nano Banana)"])

with tab1:
    try:
        st.header("VEO Models")
        veo_model_name = st.selectbox(
            "Choose a VEO model:",
            ("veo-3.0-generate-preview"), 
            key="veo_model"
        )
        prompt_option = st.radio(
            "Choose your prompt method:",
            ("Generate from keywords", "Use custom prompt"),
            key="veo_prompt_option"
        )

        if prompt_option == "Generate from keywords":
            st.subheader("Prompt Keywords")
            personas = [
                "None",
                "Woman, 30 years old, Hiking, Nature, Lives in Jakarta, Housewife",
                "Man, 25, Tech enthusiast, Lives in New York, Likes video games",
                "Teenager, 16, High-school student, Loves pop music and fashion",
                "Father, 40, Works in finance, Enjoys cars and sports",
                "Grandmother, 65, Retired, Loves cooking and gardening",
            ]
            persona = st.selectbox("Select a Persona (Optional)", personas, key="veo_persona")

            col1, col2 = st.columns(2)
            with col1:
                subject = st.text_input("Subject", key="veo_subject")
                action = st.text_input("Action", key="veo_action")
                scene = st.text_input("Scene", key="veo_scene")
                dialogue = st.text_area("Dialogue", key="veo_dialogue")
            with col2:
                camera_angle = st.text_input("Camera Angle", key="veo_camera_angle")
                camera_movement = st.text_input("Camera Movement", key="veo_camera_movement")
                lens_effects = st.text_input("Lens Effects", key="veo_lens_effects")
                style = st.text_input("Style", key="veo_style")
                temporal_elements = st.text_input("Temporal Elements", key="veo_temporal_elements")
                sound_effects = st.text_input("Sound Effects", key="veo_sound_effects")
        else:
            custom_prompt = st.text_area("Enter your custom prompt:", height=200, key="veo_custom_prompt")

        st.subheader("Generation Settings")
        enhance_prompt = st.checkbox("Enhance Prompt", True, key="veo_enhance_prompt")
        generate_audio = st.checkbox("Generate Audio", True, key="veo_generate_audio")

        starting_image = st.file_uploader("Upload Starting Image (Optional)", type=["png", "jpg", "jpeg"])


        if st.button("Generate VEO Content"):
            if project_id and location:
                prompt_data = {
                    "enhance_prompt": enhance_prompt,
                    "generate_audio": generate_audio,
                }

                if prompt_option == "Generate from keywords":
                    if subject and action and scene:
                        prompt_data.update({
                            "subject": subject,
                            "action": action,
                            "scene": scene,
                            "camera_angle": camera_angle,
                            "camera_movement": camera_movement,
                            "lens_effects": lens_effects,
                            "style": style,
                            "temporal_elements": temporal_elements,
                            "sound_effects": sound_effects,
                            "dialogue": dialogue,
                            "persona": persona,
                        })
                    else:
                        st.error("Please fill in at least Subject, Action, and Scene for keyword-based generation.")
                        st.stop()
                else: # Custom prompt
                    if custom_prompt:
                        prompt_data["prompt"] = custom_prompt
                    else:
                        st.error("Please enter a custom prompt.")
                        st.stop()

                starting_image_path = None
                if starting_image:
                    # Save the uploaded file to a temporary location
                    with open(os.path.join("tempDir",starting_image.name),"wb") as f:
                        f.write(starting_image.getbuffer())
                    starting_image_path = os.path.join("tempDir",starting_image.name)


                with st.spinner("Generating content..."):
                    response = generate_content(project_id, location, veo_model_name, prompt_data, starting_image_path)
                    if response:
                        st.success("Video generated successfully!")
                        st.video(response)
                        st.download_button(
                            label=f"Download Video",
                            data=response,
                            file_name=f"generated_video.mp4",
                            mime="video/mp4"
                        )
            else:
                st.error("Please fill in all the configuration details.")
    except Exception as e:
        st.error(e)
        print(e)

with tab2:
    st.header("Imagen Models")
    imagen_model_name = st.selectbox(
        "Choose an Imagen model:",
        ("imagen-3.0-generate-002","imagen-4.0-fast-generate-preview-06-06", "imagen-4.0-generate-preview-06-06"),  # Example model versions
        key="imagen_model"
    )
    imagen_prompt = st.text_area("Enter your prompt for Imagen:", height=200, key="imagen_prompt")
    negative_prompt = st.text_area("Enter a negative prompt:", height=100, key="imagen_negative_prompt")
    aspect_ratio = st.selectbox(
        "Aspect Ratio:",
        ("1:1", "16:9", "9:16", "4:3", "3:4"),
        key="imagen_aspect_ratio"
    )

    if st.button("Generate Imagen Content"):
        if project_id and location and imagen_prompt:
            prompt_data = {
                "prompt": imagen_prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": aspect_ratio,
            }
            with st.spinner("Generating content..."):
                response = generate_content(project_id, location, imagen_model_name, prompt_data)
                if response:
                    st.success("Image generated successfully!")
                    img_bytes = response._image_bytes
                    st.image(img_bytes)

                    # Add a download button for the image
                    st.download_button(
                        label="Download Image",
                        data=img_bytes,
                        file_name="generated_image.png",
                        mime="image/png"
                    )
        else:
            st.error("Please fill in all the configuration details and a prompt.")

with tab3:
    st.header("Gemini 2.5 Flash Image (Nano Banana)")
    gemini_image_model_name = st.selectbox(
        "Choose a Gemini Image model:",
        ("gemini-2.5-flash-image",),  # Example model versions
        key="gemini_image_model"
    )
    gemini_image_prompt = st.text_area("Enter your prompt for Gemini Image:", height=200, key="gemini_image_prompt")
    gemini_image_uploads = st.file_uploader("Upload images for editing (optional)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if st.button("Generate Gemini Image Content"):
        if project_id and location and gemini_image_prompt:
            prompt_data = {
                "prompt": gemini_image_prompt,
                "images": [],
            }
            if gemini_image_uploads:
                for image in gemini_image_uploads:
                    # Save the uploaded file to a temporary location
                    with open(os.path.join("tempDir",image.name),"wb") as f:
                        f.write(image.getbuffer())
                    prompt_data["images"].append(os.path.join("tempDir",image.name))
            with st.spinner("Generating content..."):
                response = generate_content(project_id, location, gemini_image_model_name, prompt_data)
                if response:
                    for part in response.candidates[0].content.parts:
                        if part.text is not None:
                            st.write(part.text)
                        elif part.inline_data is not None:
                            st.success("Image generated successfully!")
                            st.image(BytesIO(part.inline_data.data))

                            # Add a download button for the image
                            st.download_button(
                                label="Download Image",
                                data=BytesIO(part.inline_data.data),
                                file_name="generated_image.png",
                                mime="image/png"
                            )
        else:
            st.error("Please fill in all the configuration details and a prompt.")
