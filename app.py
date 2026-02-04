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
if 'camera_key' not in st.session_state: st.session_state.camera_key = 0

# --- CSS Styling ---
st.markdown("""
    <style>
        .stApp { background-color: #0E4E5A; }
        header {visibility: hidden;} 
        .block-container { padding-top: 1.5rem !important; max-width: 98%; }
        .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; font-size: 0.9rem; }
        .section-header { 
            background-color: white; padding: 8px 15px; border-radius: 8px; 
            color: #0E4E5A; font-weight: 700; font-size: 0.95rem; 
            margin-bottom: 12px; display: flex; align-items: center; gap: 10px; 
        }
        .stTextArea textarea { font-size: 1rem; border-radius: 10px; background-color: #f9f9f9; }
        /* Keep camera widget style clean */
        [data-testid="stCameraInput"] { border: 2px solid white; border-radius: 12px; margin-bottom: 10px; }
        .preview-label { color: white; font-weight: bold; font-size: 0.85rem; margin-top: 10px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: AssemblyAI Transcription ---
def transcribe_dental_audio(audio_data):
    try:
        aai.settings.api_key = st.secrets["ASSEMBLY_AI_KEY"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data.getvalue())
            tmp_path = tmp_file.name
        
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            punctuate=True,
            format_text=True,
            word_boost=["periodontitis", "mesio-occlusal", "buccal", "distal", "caries"],
            boost_param="high"
        )
        transcript = transcriber.transcribe(tmp_path, config=config)
        return transcript.text if transcript.status != aai.TranscriptStatus.error else "Error in transcription."
    except:
        return "Transcription failed."
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path): os.remove(tmp_path)

# --- Logic: Permanent Saving ---
def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{timestamp}"
    save_dir = os.path.join("saved_records", folder_name)
    os.makedirs(save_dir, exist_ok=True)
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, f"Tooth_{st.session_state.tooth_number}.jpg"))
    with open(os.path.join(save_dir, "Notes.txt"), "w") as f:
        f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return save_dir

# --- Main Layout ---
col_left, col_right = st.columns([0.45, 0.55], gap="medium")

# ================= LEFT COLUMN: INFO & VOICE =================
with col_left:
    st.markdown('<h2 style="color:white; margin-top:0; font-size:1.8rem;">🦷 ClariDent AI</h2>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Details</div>', unsafe_allow_html=True)
        i1, i2 = st.columns(2)
        with i1: st.session_state.patient_name = st.text_input("Full Name", value=st.session_state.patient_name)
        with i2: st.session_state.tooth_number = st.text_input("Tooth #", value=st.session_state.tooth_number)

    st.markdown('<div class="section-header">🎙️ Clinical Recorder</div>', unsafe_allow_html=True)
    audio_data = st.audio_input("Record Notes", key=f"audio_{st.session_state.audio_key}", label_visibility="collapsed")

    if audio_data:
        h = hashlib.md5(audio_data.getvalue()).hexdigest()
        if h not in st.session_state.processed_audio_hashes:
            with st.spinner("Processing..."):
                txt = transcribe_dental_audio(audio_data)
                st.session_state.transcribed_text += f" {txt}" if st.session_state.transcribed_text else txt
                st.session_state.processed_audio_hashes.add(h)
                st.rerun()

    st.session_state.transcribed_text = st.text_area("Observations", value=st.session_state.transcribed_text, height=180)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear All Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.session_state.audio_key += 1
            st.rerun()
    with c2:
        if st.button("💾 SAVE RECORD", type="primary", use_container_width=True):
            if save_record_permanently():
                st.success("Record Saved!")
                st.balloons()
            else: st.error("Incomplete Info")

# ================= RIGHT COLUMN: PHOTO =================
with col_right:
    st.markdown('<div class="section-header">📸 Intraoral Photo</div>', unsafe_allow_html=True)
    
    # 1. CAMERA WIDGET (Always at the top)
    # It naturally freezes when a photo is taken
    cam_img = st.camera_input("Capture", label_visibility="collapsed", key=f"cam_{st.session_state.camera_key}")
    
    if cam_img:
        if not os.path.exists("temp_data"): os.makedirs("temp_data")
        temp_path = os.path.join("temp_data", "latest_capture.jpg")
        Image.open(cam_img).save(temp_path)
        st.session_state.image_path = temp_path

    # 2. PREVIEW AREA (Appears below when a photo is taken)
    if st.session_state.image_path:
        st.markdown('<div class="preview-label">LATEST CAPTURE:</div>', unsafe_allow_html=True)
        
        # Use columns to make the preview smaller (thumbnail size)
        p1, p2 = st.columns([0.4, 0.6]) 
        with p1:
            st.image(st.session_state.image_path, use_container_width=True)
        with p2:
            st.caption("Confirm patient info and notes before saving.")
            if st.button("🗑️ Discard & Retake", use_container_width=True):
                st.session_state.image_path = None
                # This resets the camera widget back to LIVE mode
                st.session_state.camera_key += 1 
                st.rerun()
    else:
        st.info("Live feed active. Click 'Take Photo' to capture a snapshot.")