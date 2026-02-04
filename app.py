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

# --- CSS Styling ---
st.markdown("""
    <style>
        .stApp { background-color: #0E4E5A; }
        header {visibility: hidden;} 
        .block-container { padding-top: 2rem !important; max-width: 95%; }
        .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; }
        .section-header { 
            background-color: white; padding: 12px 20px; border-radius: 10px; 
            color: #0E4E5A; font-weight: 700; font-size: 1.1rem; 
            margin-bottom: 15px; display: flex; align-items: center; gap: 10px; 
        }
        .stTextArea textarea { font-size: 1.1rem; border-radius: 10px; }
        .stButton>button { border-radius: 8px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: AssemblyAI Transcription with Fallback ---
def transcribe_dental_audio(audio_data):
    aai.settings.api_key = st.secrets["ASSEMBLY_AI_KEY"] # GOOD! SECURE
    
    # Save audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_data.getvalue())
        tmp_path = tmp_file.name

    transcriber = aai.Transcriber()
    dental_keywords = ["periodontitis", "mesio-occlusal", "distal", "buccal", "caries", "molar", "incisor", "composite", "amalgam"]

    try:
        # 1. Attempt "Best" Model (High Quality)
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            punctuate=True,
            format_text=True,
            word_boost=dental_keywords,
            boost_param="high"
        )
        transcript = transcriber.transcribe(tmp_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            if "balance" in transcript.error.lower() or "credit" in transcript.error.lower():
                raise Exception("Credits Exhausted")
            return f"Error: {transcript.error}"
        return transcript.text

    except Exception:
        # 2. Fallback to "Nano" Model (Cheaper/Free Tier)
        st.toast("Using Nano Engine...", icon="🔄")
        config_nano = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.nano,
            punctuate=True,
            format_text=True
        )
        transcript_nano = transcriber.transcribe(tmp_path, config=config_nano)
        return transcript_nano.text if transcript_nano.status != aai.TranscriptStatus.error else "Transcription Failed."
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
    img_ext = os.path.splitext(st.session_state.image_path)[1]
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, f"Tooth_{st.session_state.tooth_number}{img_ext}"))
    
    with open(os.path.join(save_dir, "Clinical_Notes.txt"), "w", encoding="utf-8") as f:
        f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return save_dir

# --- Main Layout ---
col_left, col_space, col_right = st.columns([0.45, 0.05, 0.50])

# ================= LEFT COLUMN =================
with col_left:
    st.markdown('<h1 style="color:white; margin-bottom:20px;">🦷 ClariDent AI</h1>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Info</div>', unsafe_allow_html=True)
        st.session_state.patient_name = st.text_input("Full Name", value=st.session_state.patient_name)
        st.session_state.tooth_number = st.text_input("Tooth Number/Position", value=st.session_state.tooth_number)

    st.markdown('<div class="section-header">🎙️ Clinical Voice Notes</div>', unsafe_allow_html=True)
    
    # Audio Input with Incremental Transcription Logic
    audio_data = st.audio_input("Record observations")

    if audio_data:
        audio_bytes = audio_data.getvalue()
        current_hash = hashlib.md5(audio_bytes).hexdigest()
        
        # Only transcribe if this is a new recording segment
        if current_hash not in st.session_state.processed_audio_hashes:
            with st.spinner("Transcribing..."):
                new_text = transcribe_dental_audio(audio_data)
                if st.session_state.transcribed_text:
                    st.session_state.transcribed_text += f" {new_text}"
                else:
                    st.session_state.transcribed_text = new_text
                
                st.session_state.processed_audio_hashes.add(current_hash)
                st.rerun()

    st.session_state.transcribed_text = st.text_area("Live Transcript", value=st.session_state.transcribed_text, height=200)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.rerun()
    with c2:
        if st.button("💾 SAVE RECORD", type="primary", use_container_width=True):
            path = save_record_permanently()
            if path:
                st.success(f"Saved: {os.path.basename(path)}")
                st.balloons()
            else:
                st.error("Missing Info or Photo")

# ================= RIGHT COLUMN =================
with col_right:
    st.markdown('<div class="section-header">📸 Intraoral Photo</div>', unsafe_allow_html=True)
    
    # Stable Camera Logic: Swap widget for image without flicker
    camera_placeholder = st.empty()

    if st.session_state.image_path is None:
        with camera_placeholder.container():
            cam_img = st.camera_input("Capture Image")
            if cam_img:
                # Save temp image
                if not os.path.exists("temp_data"): os.makedirs("temp_data")
                temp_path = os.path.join("temp_data", f"temp_{datetime.now().strftime('%H%M%S')}.jpg")
                Image.open(cam_img).save(temp_path)
                st.session_state.image_path = temp_path
                st.rerun()
    else:
        with camera_placeholder.container():
            st.image(st.session_state.image_path, use_container_width=True)
            if st.button("🗑️ Retake Photo", use_container_width=True):
                st.session_state.image_path = None
                st.rerun()