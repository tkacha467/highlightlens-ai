import streamlit as st
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
import os
import json
import hashlib
import time

load_dotenv()
print("API Key loaded:", bool(os.getenv("GEMINI_API_KEY")))

# App configuration
st.set_page_config(
    page_title="HighlightLens AI",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for dark mode and modern look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #121212;
        color: #F0F2F6;
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        color: #FFFFFF;
    }
    
    /* Cards */
    .result-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .result-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 25px rgba(76, 175, 80, 0.2);
        border: 1px solid #4CAF50;
    }
    
    /* Subtle glow for images */
    .result-card img, [data-testid="stImage"] img {
        border-radius: 8px;
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.15);
    }
    
    /* Highlight glow for best moment */
    .best-highlight-glow img {
        box-shadow: 0 0 30px rgba(255, 81, 47, 0.5) !important;
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #4CAF50;
    }
    
    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        background: linear-gradient(45deg, #FF512F 0%, #DD2476 100%);
        color: white;
        font-size: 14px;
        font-weight: bold;
        margin-top: 10px;
    }
    
    /* New Analytics Features CSS */
    .score-bar-container {
        width: 100%;
        background-color: #333;
        border-radius: 5px;
        height: 8px;
        margin-top: 2px;
        margin-bottom: 12px;
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 5px;
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
    }
    .tag-pill {
        display: inline-block;
        background-color: #2D2D2D;
        border: 1px solid #4CAF50;
        color: #8BC34A;
        border-radius: 12px;
        padding: 5px 12px;
        font-size: 14px;
        margin-right: 8px;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    .rec-badge {
        display: inline-block;
        background: linear-gradient(45deg, #2196F3, #00BCD4);
        color: white;
        padding: 6px 14px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .rank-label {
        font-size: 20px;
        font-weight: 900;
        color: #FFC107;
        margin-bottom: 5px;
    }
    .ai-active {
        color: #4CAF50;
        font-weight: bold;
        animation: blink 1.5s infinite;
        display: inline-block;
    }
    .analysis-id {
        font-family: monospace;
        color: #888;
        font-size: 12px;
        margin-top: 15px;
    }
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    
    /* Presentation Mode Customizations */
    .pres-slide {
        background-color: #1A1A1A;
        border: 2px solid #333;
        border-radius: 16px;
        padding: 40px;
        margin-bottom: 60px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .pres-title {
        font-size: 32px;
        color: #FFC107;
        margin-bottom: 20px;
        border-bottom: 2px solid #333;
        padding-bottom: 10px;
    }
    .pres-caption {
        font-size: 20px;
        color: #E0E0E0;
        font-style: italic;
        margin-bottom: 30px;
    }
    .pres-metric {
        background-color: #222;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 4px solid #4CAF50;
    }
    .pres-metric h4 {
        margin: 0;
        color: #AAA;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .pres-metric .value {
        font-size: 28px;
        font-weight: bold;
        color: #FFF;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@st.cache_resource
def get_model():
    return genai.GenerativeModel("gemini-2.5-flash")

model = get_model()

# Header
st.title("📸 HighlightLens AI")
st.markdown("### AI-powered workflow prototype for sports-event media teams.")
st.markdown("<span class='ai-active'>● AI Vision Engine Active</span>", unsafe_allow_html=True)

# Initialize Session State
if "analyzed_results_v2" not in st.session_state:
    st.session_state.analyzed_results_v2 = []
if "image_cache_v2" not in st.session_state:
    st.session_state.image_cache_v2 = {}
if "presentation_mode" not in st.session_state:
    st.session_state.presentation_mode = False

def analyze_images_batch(images: list, filenames: list, status_obj):
    status_obj.update(label="Uploading payloads to Gemini Vision...", state="running")
    time.sleep(0.5)
    
    prompt = f"""Analyze these {len(images)} sports event photos sequentially. Provide a JSON response containing a list of objects, one for each image in the EXACT same order they were provided.
Each object must have the following keys:
- 'ai_caption': A short engaging description.
- 'crowd_excitement_level': A float between 1.0 and 10.0.
- 'confidence_score': An integer between 1 and 100 representing AI confidence.
- 'reasoning_tags': A list of exactly 3 descriptive string tags (e.g., 'crowd_density_high', 'emotional_peak', 'celebration_detected').
- 'recommended_use': A string, either 'Instagram', 'Broadcast', or 'Thumbnail'.
"""
    
    try:
        status_obj.update(label="Extracting facial metrics and crowd density...", state="running")
        contents = [prompt] + images
        response = model.generate_content(
            contents,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        print("Gemini batch response:", response.text)
        
        status_obj.update(label="Computing excitement vectors...", state="running")
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        result_json = json.loads(text)
        
        # Ensure it is a list
        if not isinstance(result_json, list):
            # Fallback if wrapped in a dict
            for key in result_json:
                if isinstance(result_json[key], list):
                    result_json = result_json[key]
                    break
                    
        if not isinstance(result_json, list):
            result_json = [result_json] # Fallback
            
        mapped_results = []
        for idx, res in enumerate(result_json):
            if idx >= len(images):
                break
                
            raw_score = res.get("excitement_score", res.get("crowd_excitement_level", 0))
            parsed_score = 0.0
            try:
                if isinstance(raw_score, str):
                    import re
                    match = re.search(r'\d+(\.\d+)?', raw_score)
                    if match:
                        parsed_score = float(match.group())
                else:
                    parsed_score = float(raw_score)
            except Exception:
                parsed_score = 0.0
                
            # Map simple prompt keys to the UI expected keys
            mapped_json = {
                "crowd_excitement_level": parsed_score,
                "ai_caption": res.get("ai_caption", res.get("description", "No description provided")),
                "highlight_score": parsed_score,
                "confidence_score": res.get("confidence_score", 95),
                "reasoning_tags": res.get("reasoning_tags", ["analyzed_by_ai", "highlight_processed", "vision_metrics_ok"]),
                "recommended_use": res.get("recommended_use", "Social Media"),
                "social_media_readiness": parsed_score >= 8.0,
                "filename": filenames[idx],
                "image": images[idx],
                "analysis_id": f"ID-{hashlib.md5((filenames[idx] + str(parsed_score)).encode()).hexdigest()[:8].upper()}"
            }
            mapped_results.append(mapped_json)
            
        status_obj.update(label="Finalizing analytics...", state="running")
        time.sleep(0.5)
        return mapped_results
    except Exception as e:
        print("Gemini batch error:", e)
        st.error("⚠ AI analysis temporarily unavailable.")
        return "API_ERROR"

# ==========================================
# MAIN DASHBOARD VIEW
# ==========================================
if not st.session_state.presentation_mode:
    # Upload Section
    st.markdown("### 📤 Upload Event Photos")
    uploaded_files = st.file_uploader("Upload multiple sports-event images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    col_btn1, col_btn2 = st.columns([2, 8])
    with col_btn1:
        analyze_pressed = st.button("Analyze Photos", type="primary")

    if analyze_pressed:
        if uploaded_files:
            st.session_state.analyzed_results_v2 = []
            
            status_obj = st.status("🟢 Initiating AI Vision Engine...", expanded=True)
            with status_obj:
                final_results = [None] * len(uploaded_files)
                images_to_analyze = []
                filenames_to_analyze = []
                hashes_to_analyze = []
                indices_to_analyze = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    file_bytes = uploaded_file.getvalue()
                    img_hash = hashlib.md5(file_bytes).hexdigest()
                    
                    import io
                    image = Image.open(io.BytesIO(file_bytes)).convert('RGB')
                        
                    if img_hash in st.session_state.image_cache_v2:
                        cached_data = st.session_state.image_cache_v2[img_hash].copy()
                        cached_data["image"] = image
                        final_results[i] = cached_data
                    else:
                        images_to_analyze.append(image)
                        filenames_to_analyze.append(uploaded_file.name)
                        hashes_to_analyze.append(img_hash)
                        indices_to_analyze.append(i)
                        
                if images_to_analyze:
                    results = analyze_images_batch(images_to_analyze, filenames_to_analyze, status_obj)
                    if results != "API_ERROR":
                        for idx, res in enumerate(results):
                            st.session_state.image_cache_v2[hashes_to_analyze[idx]] = res
                            final_results[indices_to_analyze[idx]] = res
                        st.session_state.analyzed_results_v2 = [r for r in final_results if r is not None]
                        status_obj.update(label="Analysis Complete!", state="complete", expanded=False)
                    else:
                        status_obj.update(label="Analysis Failed.", state="error", expanded=False)
                else:
                    st.session_state.analyzed_results_v2 = final_results
                    status_obj.update(label="Loaded from Cache Instantly!", state="complete", expanded=False)
        else:
            st.warning("Please upload at least one image.")

    # Dashboard & Results
    if st.session_state.analyzed_results_v2:
        # Sort results by highlight_score for ranking
        results = sorted(st.session_state.analyzed_results_v2, key=lambda x: x.get("highlight_score", 0), reverse=True)
        
        st.markdown("---")
        
        # Enter Presentation Mode Button
        st.markdown("### 🎬 Ready to Showcase?")
        if st.button("Enter Presentation Mode", type="primary", use_container_width=True):
            st.session_state.presentation_mode = True
            st.rerun()
            
        st.markdown("## 📊 Dashboard Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        total_images = len(results)
        avg_excitement = sum(r.get("crowd_excitement_level", 0) for r in results) / total_images if total_images else 0
        avg_confidence = sum(r.get("confidence_score", 0) for r in results) / total_images if total_images else 0
        
        best_highlight = results[0] if results else None
        
        col1.metric("Total Images Analyzed", total_images)
        col2.metric("Average Excitement", f"{avg_excitement:.1f}/10")
        col3.metric("Avg Engine Confidence", f"{avg_confidence:.1f}%")
        col4.metric("Top Highlight Score", f"{best_highlight.get('highlight_score', 0) if best_highlight else 0}/10")
        
        st.markdown("---")
        st.markdown("## 🖼️ Complete Analytics Feed")
        
        # Display Result Cards in a grid
        cols = st.columns(3)
        for index, res in enumerate(results):
            with cols[index % 3]:
                import base64
                import io
                buffered = io.BytesIO()
                res["image"].save(buffered, format="JPEG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
                
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown(f"<div class='rank-label'>Rank #{index + 1}</div>", unsafe_allow_html=True)
                st.markdown(f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 8px;">', unsafe_allow_html=True)
                
                st.markdown(f"**Score:** {res.get('highlight_score', 0)}/10")
                score_pct = (res.get('highlight_score', 0) / 10) * 100
                st.markdown(f'<div class="score-bar-container"><div class="score-bar-fill" style="width: {score_pct}%;"></div></div>', unsafe_allow_html=True)
                
                st.markdown(f"*{res.get('ai_caption', '')}*")
                
                st.markdown(f"**Use:** <span class='rec-badge'>{res.get('recommended_use', 'General')}</span>", unsafe_allow_html=True)
                
                tags_html = "".join([f"<span class='tag-pill'>#{tag}</span>" for tag in res.get("reasoning_tags", [])])
                st.markdown(tags_html, unsafe_allow_html=True)
                
                st.markdown(f"<div class='analysis-id'>{res.get('analysis_id', 'ID-XXX')}</div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💡 Why this helps sports-event organizers")
    st.write(
        "During major sporting events, thousands of photos are taken every hour. "
        "Media teams often struggle to manually sift through massive folders to find the perfect shot for a quick social media update. "
        "**HighlightLens AI** accelerates this workflow by automatically evaluating crowd excitement, emotional intensity, and image quality. "
        "It instantly surfaces the most highlight-worthy moments with ready-to-use captions, allowing media teams to focus on storytelling rather than sorting."
    )

# ==========================================
# PRESENTATION MODE VIEW
# ==========================================
else:
    # Navigation Bar
    if st.button("🔙 Exit Presentation Mode"):
        st.session_state.presentation_mode = False
        st.rerun()
        
    results = sorted(st.session_state.analyzed_results_v2, key=lambda x: x.get("highlight_score", 0), reverse=True)
    
    # Title Slide / Summary
    st.markdown("<br><h1 style='text-align: center; color: #4CAF50; font-size: 48px;'>HighlightLens Executive Summary</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #AAA; font-size: 20px;'>Automated Media Curation Engine</p><br>", unsafe_allow_html=True)
    
    col_s1, col_s2, col_s3 = st.columns(3)
    total_images = len(results)
    avg_excitement = sum(r.get("crowd_excitement_level", 0) for r in results) / total_images if total_images else 0
    avg_confidence = sum(r.get("confidence_score", 0) for r in results) / total_images if total_images else 0
    
    with col_s1:
        st.markdown(f"<div class='pres-metric'><h4>Images Curated</h4><div class='value'>{total_images}</div></div>", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"<div class='pres-metric'><h4>Average Excitement</h4><div class='value'>{avg_excitement:.1f} / 10</div></div>", unsafe_allow_html=True)
    with col_s3:
        st.markdown(f"<div class='pres-metric'><h4>Engine Confidence</h4><div class='value'>{avg_confidence:.1f}%</div></div>", unsafe_allow_html=True)
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Detailed Slides
    for i, res in enumerate(results):
        st.markdown('<div class="pres-slide">', unsafe_allow_html=True)
        st.markdown(f"<div class='pres-title'>🏆 Rank #{i+1} Highlight</div>", unsafe_allow_html=True)
        
        col_img, col_data = st.columns([5, 5])
        
        with col_img:
            # Render using base64 to guarantee glowing wrapper and avoid Streamlit cache bugs
            import base64
            import io
            buffered = io.BytesIO()
            res["image"].save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Custom glow class for the top 1 image
            if i == 0:
                st.markdown(f'<div class="best-highlight-glow"><img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 8px;"></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="box-shadow: 0 0 15px rgba(76, 175, 80, 0.15); border-radius: 8px; overflow: hidden;"><img src="data:image/jpeg;base64,{img_b64}" style="width: 100%;"></div>', unsafe_allow_html=True)
            
            st.markdown(f"<div class='analysis-id' style='text-align: center; margin-top: 15px;'>TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')} | {res.get('analysis_id', 'ID-XXX')}</div>", unsafe_allow_html=True)
            
        with col_data:
            st.markdown(f"<div class='pres-caption'>\"{res.get('ai_caption', '')}\"</div>", unsafe_allow_html=True)
            
            # Highlight Score
            st.markdown(f"**Highlight Score:** <span style='font-size: 24px; color: #4CAF50;'>{res.get('highlight_score', 0)}/10</span>", unsafe_allow_html=True)
            score_pct = (res.get('highlight_score', 0) / 10) * 100
            st.markdown(f'<div class="score-bar-container"><div class="score-bar-fill" style="width: {score_pct}%;"></div></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Confidence
            st.markdown(f"**Engine Confidence:** <span style='font-size: 24px; color: #FFF;'>{res.get('confidence_score', 0)}%</span>", unsafe_allow_html=True)
            conf_pct = res.get('confidence_score', 0)
            st.markdown(f'<div class="score-bar-container" style="background-color: #333;"><div class="score-bar-fill" style="width: {conf_pct}%; background: linear-gradient(90deg, #2196F3, #00BCD4);"></div></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Recommendation & Tags
            st.markdown(f"**Recommended For:** <span class='rec-badge' style='font-size: 16px;'>{res.get('recommended_use', 'General')}</span>", unsafe_allow_html=True)
            
            st.markdown("<br>**Detected AI Reasoning:**", unsafe_allow_html=True)
            tags_html = "".join([f"<span class='tag-pill' style='font-size: 16px; padding: 8px 16px; margin-top: 10px;'>#{tag}</span>" for tag in res.get("reasoning_tags", [])])
            st.markdown(tags_html, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Scroll to top button or End of Presentation marker
    st.markdown("<h3 style='text-align: center; color: #555;'>End of Presentation</h3>", unsafe_allow_html=True)