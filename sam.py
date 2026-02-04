import streamlit as st
import numpy as np
import cv2
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates
from ultralytics import SAM
import os
import torch

# --- 1. FIXED Configuration & Caching ---
@st.cache_resource
def load_sam():
    """Load the official Ultralytics SAM model (auto-downloads)."""
    # Use standard SAM model name - fixes the FileNotFoundError
    return SAM("sam_b.pt")

model = load_sam()

# --- 2. Session State for Interactive Editing ---
if 'points' not in st.session_state: 
    st.session_state.points = []
if 'labels' not in st.session_state: 
    st.session_state.labels = []
if 'current_mask' not in st.session_state: 
    st.session_state.current_mask = None
if 'input_image' not in st.session_state: 
    st.session_state.input_image = None
if 'image_np' not in st.session_state: 
    st.session_state.image_np = None

# --- 3. Helper Functions ---
def reset_segmentation():
    st.session_state.points = []
    st.session_state.labels = []
    st.session_state.current_mask = None

def process_image_for_sam(image_pil):
    """Convert PIL image to numpy array for SAM."""
    image_np = np.array(image_pil.convert("RGB"))
    return image_np

def show_mask(image_np, mask):
    """Overlay the SAM mask on the image."""
    if mask is None: 
        return image_np
    
    # Ensure mask is 2D boolean
    if mask.ndim > 2:
        mask = mask.squeeze()
    
    mask_float = mask.astype(np.float32)
    color = np.array([30, 144, 255])  # Dodger Blue for teeth
    
    h, w = mask_float.shape
    mask_image = mask_float.reshape(h, w, 1) * color.reshape(1, 1, 3)
    
    # Blend images
    overlay = image_np.copy().astype(np.float32)
    overlay[mask_float > 0.5] = (image_np[mask_float > 0.5] * 0.5 + 
                                mask_image[mask_float > 0.5] * 0.5)
    return overlay.astype(np.uint8)

# --- 4. Main Interface ---
st.title("🦷 Smart Tooth Selector (Ultralytics SAM)")

col1, col2 = st.columns([2, 1])

with col1:
    # A. Camera Input
    img_file = st.camera_input("Capture Patient Mouth")
    
    if img_file:
        # Reset if new image
        if st.session_state.input_image != img_file.name:
            reset_segmentation()
            st.session_state.input_image = img_file.name
            
        image = Image.open(img_file)
        image_np = process_image_for_sam(image)
        st.session_state.image_np = image_np
        
        # B. Interactive Image (Click to Select)
        st.write("👉 **Click** to add points. Use controls to Add/Remove areas.")
        
        # Draw the image WITH the current mask overlay
        display_img = image_np.copy()
        if st.session_state.current_mask is not None:
            display_img = show_mask(image_np, st.session_state.current_mask)
        
        # Draw points on top for visual feedback
        for i, pt in enumerate(st.session_state.points):
            color = (0, 255, 0) if st.session_state.labels[i] == 1 else (255, 0, 0)
            cv2.circle(display_img, (int(pt[0]), int(pt[1])), 8, color, -1)
        
        # CAPTURE CLICKS - Fixed key for proper reactivity
        value = streamlit_image_coordinates(
            Image.fromarray(display_img),
            key=f"canvas_{hash(str(st.session_state.points))}"
        )
        
        # C. Process Clicks
        if value is not None:
            point = np.array([value['x'], value['y']])
            
            # Check if this is a new point
            existing_points = np.array(st.session_state.points)
            if len(existing_points) == 0 or not np.any(np.all(np.abs(existing_points - point) < 5, axis=1)):
                
                # Determine mode (Add or Remove)
                mode = st.session_state.get('click_mode', 'Add Area')
                label = 1 if mode == 'Add Area' else 0
                
                st.session_state.points.append(point.tolist())
                st.session_state.labels.append(label)
                
                # ULTRALYTICS SAM PREDICTION - Simplified
                try:
                    if len(st.session_state.points) >= 1:
                        results = model.predict(
                            st.session_state.image_np,
                            points=np.array(st.session_state.points),
                            point_labels=np.array(st.session_state.labels),
                            save=False,
                            verbose=False,
                            imgsz=640  # Smaller for speed
                        )
                        
                        # Extract best mask
                        if results and len(results) > 0 and results[0].masks is not None:
                            mask = results[0].masks.data[0][0].cpu().numpy()
                            # Resize mask to match image if needed
                            if mask.shape != st.session_state.image_np.shape[:2]:
                                mask = cv2.resize(mask.astype(np.uint8), 
                                                (st.session_state.image_np.shape[1], 
                                                 st.session_state.image_np.shape[0]), 
                                                interpolation=cv2.INTER_NEAREST)
                                mask = mask.astype(bool)
                            st.session_state.current_mask = mask
                        else:
                            st.warning("No mask detected. Try more points near teeth edges.")
                            
                except Exception as e:
                    st.error(f"Prediction failed: {str(e)}")
                    st.info("Try: pip install -U ultralytics")
                
                st.rerun()

with col2:
    st.markdown("### 🎛️ Controls")
    
    # Toggle between Adding (Green) and Removing (Red) areas
    mode = st.radio("Click Mode", ["Add Area", "Remove Area"], key='click_mode')
    
    st.info(f"🖱️ Points: {len(st.session_state.points)}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Reset All"):
            reset_segmentation()
            st.rerun()
    
    if st.session_state.current_mask is not None and st.session_state.image_np is not None:
        st.success("✅ Tooth Segmented!")
        
        col_save1, col_save2 = st.columns(2)
        with col_save1:
            if st.button("💾 Save Image"):
                final_overlay = show_mask(st.session_state.image_np, st.session_state.current_mask)
                safe_filename = f"tooth_{st.session_state.input_image.replace(' ', '_')[:20]}.jpg"
                Image.fromarray(final_overlay).save(safe_filename)
                st.success(f"✅ Saved: {safe_filename}")
                st.balloons()
        
        with col_save2:
            if st.button("📋 Show Mask Info"):
                mask = st.session_state.current_mask
                st.info(f"Mask shape: {mask.shape}, Pixels: {np.sum(mask)}")

# --- Footer ---
st.markdown("---")
with st.expander("🔧 Debug - Click to check status"):
    st.write("**Model:**", "✅ Loaded" if model else "❌ Failed")
    st.write("**Image:**", "✅ Ready" if st.session_state.image_np is not None else "⏳ Waiting")
    st.write("**Points:**", st.session_state.points)
    st.write("**Ultralytics version:**", SAM.__version__ if hasattr(SAM, '__version__') else "Check with: pip show ultralytics")
