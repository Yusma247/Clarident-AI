import streamlit as st
import assemblyai as aai
from PIL import Image
from datetime import datetime
import os
import shutil
import io
import hashlib
import tempfile

# --- Page Configuration ---
st.set_page_config(
    page_title="ClariDent AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize Session State ---
if 'patient_name' not in st.session_state: st.session_state.patient_name = ""
if 'tooth_number' not in st.session_state: st.session_state.tooth_number = ""
if 'image_path' not in st.session_state: st.session_state.image_path = None
if 'transcribed_text' not in st.session_state: st.session_state.transcribed_text = ""
if 'processed_audio_hashes' not in st.session_state: st.session_state.processed_audio_hashes = set()
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

# --- CSS Styling ---
st.markdown("""
    <style>
        .stApp { background-color: #0E4E5A; }
        header {visibility: hidden;} 
        .block-container { padding-top: 1.5rem !important; max-width: 98%; }
        .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; }
        .section-header { 
            background-color: white; padding: 10px 15px; border-radius: 8px; 
            color: #0E4E5A; font-weight: 700; font-size: 1rem; 
            margin-bottom: 15px; display: flex; align-items: center; gap: 10px; 
        }
        .stTextArea textarea { font-size: 1.1rem; border-radius: 10px; background-color: #f9f9f9; }
        /* Style the camera area */
        [data-testid="stCameraInput"] { border: 3px solid white; border-radius: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: AssemblyAI Transcription ---
def transcribe_dental_audio(audio_data):
    try:
        aai.settings.api_key = st.secrets["ASSEMBLY_AI_KEY"]
    except:
        return "Error: API Key missing in Secrets."
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_data.getvalue())
        tmp_path = tmp_file.name

    transcriber = aai.Transcriber()
    dental_keywords = ["periodontitis", "mesio-occlusal", "distal", "buccal", "caries", "molar", "cavity", "filling"]

    try:
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            punctuate=True,
            format_text=True,
            word_boost=dental_keywords,
            boost_param="high"
        )
        transcript = transcriber.transcribe(tmp_path, config=config)
        return transcript.text if transcript.status != aai.TranscriptStatus.error else "Transcription Error."
    except:
        # Final Fallback
        config_nano = aai.TranscriptionConfig(speech_model=aai.SpeechModel.nano)
        return transcriber.transcribe(tmp_path, config=config_nano).text
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

# --- Logic: Permanent Saving ---
def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{timestamp}"
    save_dir = os.path.join("saved_records", folder_name)
    
    os.makedirs(save_dir, exist_ok=True)
    img_filename = f"Tooth_{st.session_state.tooth_number}.jpg"
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, img_filename))
    
    with open(os.path.join(save_dir, "Notes.txt"), "w", encoding="utf-8") as f:
        f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return save_dir

# --- Main Layout ---
col_left, col_right = st.columns([0.45, 0.55], gap="large")

# ================= LEFT COLUMN: INFO & VOICE =================
with col_left:
    st.markdown('<h1 style="color:white; margin-top:0;">🦷 ClariDent AI</h1>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Details</div>', unsafe_allow_html=True)
        st.session_state.patient_name = st.text_input("Name", value=st.session_state.patient_name)
        st.session_state.tooth_number = st.text_input("Tooth #", value=st.session_state.tooth_number)

    st.markdown('<div class="section-header">🎙️ Clinical Recorder</div>', unsafe_allow_html=True)
    
    # Use dynamic key to force reset the audio widget
    audio_data = st.audio_input("Speak notes", key=f"voice_input_{st.session_state.audio_key}")

    if audio_data:
        audio_bytes = audio_data.getvalue()
        current_hash = hashlib.md5(audio_bytes).hexdigest()
        
        if current_hash not in st.session_state.processed_audio_hashes:
            with st.spinner("Transcribing..."):
                new_text = transcribe_dental_audio(audio_data)
                if st.session_state.transcribed_text:
                    st.session_state.transcribed_text += f" {new_text}"
                else:
                    st.session_state.transcribed_text = new_text
                st.session_state.processed_audio_hashes.add(current_hash)
                st.rerun()

    st.session_state.transcribed_text = st.text_area("Observations", value=st.session_state.transcribed_text, height=180)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.session_state.audio_key += 1  # Destroys and remakes the audio widget
            st.rerun()
    with c2:
        if st.button("💾 SAVE RECORD", type="primary", use_container_width=True):
            path = save_record_permanently()
            if path:
                st.success("Record Saved!")
                st.balloons()
            else:
                st.error("Missing Info")

# ================= RIGHT COLUMN: PHOTO (NO FLICKER) =================
with col_right:
    st.markdown('<div class="section-header">📸 Intraoral Camera</div>', unsafe_allow_html=True)
    
    # 1. ALWAYS show the camera. This prevents hardware flicker.
    cam_img = st.camera_input("Viewfinder", label_visibility="collapsed")
    
    if cam_img:
        if not os.path.exists("temp_data"): os.makedirs("temp_data")
        temp_path = os.path.join("temp_data", "current_capture.jpg")
        Image.open(cam_img).save(temp_path)
        st.session_state.image_path = temp_path
        # We don't rerun here to keep the camera live and steady

    # 2. Show the Captured Preview below if it exists
    if st.session_state.image_path:
        st.markdown('<div style="margin-top:20px; color:white; font-weight:bold;">✅ Latest Capture:</div>', unsafe_allow_html=True)
        st.image(st.session_state.image_path, use_container_width=True)
        
        if st.button("🗑️ Discard Photo", use_container_width=True):
            st.session_state.image_path = None
            st.rerun()
    else:
        st.info("Snap a photo using the 'Take Photo' button inside the camera view.")