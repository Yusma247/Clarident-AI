import streamlit as st
import assemblyai as aai
from PIL import Image
from datetime import datetime
import os
import hashlib
import tempfile
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

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
        .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; font-size: 0.9rem; }
        .section-header { 
            background-color: white; padding: 8px 15px; border-radius: 8px; 
            color: #0E4E5A; font-weight: 700; font-size: 0.95rem; 
            margin-bottom: 12px; display: flex; align-items: center; gap: 10px; 
        }
        .stTextArea textarea { font-size: 1rem; border-radius: 10px; background-color: #f9f9f9; }
        [data-testid="stCameraInput"] { border: 2px solid white; border-radius: 12px; margin-bottom: 10px; }
        .preview-label { color: white; font-weight: bold; font-size: 0.85rem; margin-top: 15px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- Google Drive Logic ---
def get_gdrive_service():
    """Authenticates with Google Drive using Streamlit Secrets."""
    # 1. Get the secret
    creds_info = st.secrets["GDRIVE_SERVICE_ACCOUNT"]
    
    # 2. If it's a string (from the ''' method), parse it. 
    # If it's already a dict/AttrDict, just use it.
    if isinstance(creds_info, str):
        creds_info = json.loads(creds_info)
    else:
        # Convert Streamlit AttrDict to a standard Python dict
        creds_info = dict(creds_info)
    
    # 3. CRITICAL: Fix the private key formatting 
    # (Sometimes \n characters get double-escaped in TOML)
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def find_or_create_folder(folder_name, parent_id=None):
    """Checks if folder exists, if not creates it. Returns Folder ID."""
    service = get_gdrive_service()
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id] if parent_id else []
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_to_drive(file_path, file_name, folder_id, mime_type):
    """Uploads a file to a specific Google Drive folder."""
    service = get_gdrive_service()
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

# --- AssemblyAI Logic ---
def transcribe_dental_audio(audio_data):
    try:
        aai.settings.api_key = st.secrets["ASSEMBLY_AI_KEY"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data.getvalue())
            tmp_path = tmp_file.name
        
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        transcript = transcriber.transcribe(tmp_path, config=config)
        return transcript.text if transcript.text else ""
    except Exception:
        return ""
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path): 
            os.remove(tmp_path)

# --- UI Fragments ---
@st.fragment
def audio_section():
    st.markdown('<div class="section-header">🎙️ Clinical Recorder</div>', unsafe_allow_html=True)
    audio_data = st.audio_input("Record", key=f"audio_{st.session_state.audio_key}", label_visibility="collapsed")
    
    if audio_data:
        h = hashlib.md5(audio_data.getvalue()).hexdigest()
        if h not in st.session_state.processed_audio_hashes:
            with st.spinner("Transcribing..."):
                txt = transcribe_dental_audio(audio_data)
                if txt:
                    st.session_state.transcribed_text += f" {txt}"
                st.session_state.processed_audio_hashes.add(h)
                st.rerun()
    
    st.session_state.transcribed_text = st.text_area(
        "Observations", value=st.session_state.transcribed_text, height=180
    )

@st.fragment
def camera_section():
    st.markdown('<div class="section-header">📸 Intraoral Photo</div>', unsafe_allow_html=True)
    cam_img = st.camera_input("Capture", label_visibility="collapsed")
    
    if cam_img:
        # We use tempfile to ensure compatibility with Streamlit Cloud
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "latest_capture.jpg")
        Image.open(cam_img).save(temp_path)
        st.session_state.image_path = temp_path
        
        st.markdown('<div class="preview-label">LATEST CAPTURE:</div>', unsafe_allow_html=True)
        st.image(st.session_state.image_path, width=400)
    else:
        st.session_state.image_path = None

# --- Main Logic: Save to Drive ---
def save_everything():
    if not st.session_state.patient_name or not st.session_state.image_path:
        st.error("Please provide Patient Name and Photo.")
        return

    try:
        with st.spinner("Uploading to Google Drive..."):
            # 1. Root Folder ID from your secrets
            root_id = st.secrets["GDRIVE_ROOT_FOLDER_ID"]
            
            # 2. Folder for the Patient (Shared across multiple teeth)
            patient_folder_id = find_or_create_folder(st.session_state.patient_name, root_id)
            
            # 3. Folder for this specific visit/tooth
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            tooth_folder_name = f"Tooth_{st.session_state.tooth_number}_{timestamp}"
            visit_folder_id = find_or_create_folder(tooth_folder_name, patient_folder_id)
            
            # 4. Upload Image
            upload_to_drive(st.session_state.image_path, "photo.jpg", visit_folder_id, "image/jpeg")
            
            # 5. Upload Notes as Text File
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tf:
                tf.write(f"Patient: {st.session_state.patient_name}\n")
                tf.write(f"Tooth: {st.session_state.tooth_number}\n")
                tf.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                tf.write(f"Notes:\n{st.session_state.transcribed_text}")
                notes_path = tf.name
            
            upload_to_drive(notes_path, "Clinical_Notes.txt", visit_folder_id, "text/plain")
            os.remove(notes_path)
            
            st.success(f"Saved to Drive: {st.session_state.patient_name} > {tooth_folder_name}")
            st.balloons()
    except Exception as e:
        st.error(f"Sync Error: {e}")

# --- Layout ---
col_left, col_right = st.columns([0.45, 0.55], gap="medium")

with col_left:
    st.markdown('<h2 style="color:white; margin-top:0; font-size:1.8rem;">🦷 ClariDent AI</h2>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Details</div>', unsafe_allow_html=True)
        i1, i2 = st.columns(2)
        with i1: st.session_state.patient_name = st.text_input("Full Name", value=st.session_state.patient_name)
        with i2: st.session_state.tooth_number = st.text_input("Tooth #", value=st.session_state.tooth_number)

    audio_section()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear All", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.session_state.audio_key += 1
            st.rerun()
    with c2:
        if st.button("💾 SAVE TO DRIVE", type="primary", use_container_width=True):
            save_everything()

with col_right:
    camera_section()