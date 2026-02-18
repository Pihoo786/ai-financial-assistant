import streamlit as st
import boto3
import json
import base64
from PIL import Image
import io

# Page config
st.set_page_config(
    page_title="AI Financial Clarity Assistant",
    page_icon="💰",
    layout="centered"
)

# Custom CSS
st.markdown("""
    <style>
    .main {background-color: #f5f7fa;}
    .title {font-size: 2.5rem; font-weight: 800; color: #1a1a2e;}
    .subtitle {font-size: 1.1rem; color: #555; margin-bottom: 2rem;}
    .insight-box {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-top: 1rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-size: 1rem;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
""", unsafe_allow_html=True)

# AWS client
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

def convert_to_jpeg(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def analyze_receipt(image_bytes):
    jpeg_bytes = convert_to_jpeg(image_bytes)
    image_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')

    message = {
        "role": "user",
        "content": [
            {
                "image": {
                    "format": "jpeg",
                    "source": {
                        "bytes": image_base64
                    }
                }
            },
            {
                "text": """You are a friendly financial assistant. Analyze this receipt and respond in this exact format:

**🧾 Items Purchased:**
List each item with its price on a new line

**📂 Category:**
State the main spending category (Food, Transport, Shopping, Entertainment, Health, Other)

**💵 Total Spent:**
State the total amount

**📊 Spending Summary:**
2-3 sentences explaining the spending pattern in simple, friendly language

**💡 Smart Suggestions:**
Give 3 specific, actionable tips to save money based on what was purchased

Keep the tone friendly and encouraging."""
            }
        ]
    }

    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        body=json.dumps({
            "messages": [message],
            "inferenceConfig": {
                "maxTokens": 1000
            }
        })
    )

    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]

# UI
st.markdown('<p class="title">💰 AI Financial Clarity Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload a receipt and get instant AI-powered spending insights</p>', unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📤 Upload Receipt")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "avif", "webp"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="Your Receipt", use_container_width=True)
        analyze_btn = st.button("🔍 Analyze My Spending")

with col2:
    st.markdown("### 📊 Your Insights")
    
    if uploaded_file and analyze_btn:
        with st.spinner("Nova is analyzing your receipt..."):
            image_bytes = uploaded_file.read()
            analysis = analyze_receipt(image_bytes)
        
        st.markdown(analysis)
        
        st.success("✅ Analysis complete!")
        
        # Download option
        st.download_button(
            label="📥 Download Insights",
            data=analysis,
            file_name="spending_insights.txt",
            mime="text/plain"
        )
    elif not uploaded_file:
        st.info("👈 Upload a receipt to get started!")

st.divider()
st.markdown("<center><small>Powered by Amazon Nova on AWS Bedrock</small></center>", unsafe_allow_html=True)
