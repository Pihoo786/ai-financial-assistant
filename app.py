import streamlit as st
import boto3
import json
import base64

# AWS client
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

def analyze_receipt(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
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
                "text": """You are a financial assistant. Analyze this receipt and:
1. List all items and their prices
2. Categorize the expenses (Food, Transport, Shopping, etc.)
3. Give the total amount spent
4. Give 2-3 simple suggestions to improve spending

Be clear, friendly, and simple in your explanation."""
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

# Streamlit UI
st.title("💰 AI Financial Clarity Assistant")
st.write("Upload a receipt and get instant spending insights!")

uploaded_file = st.file_uploader("Upload your receipt image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Receipt", use_column_width=True)
    
    if st.button("Analyze Receipt"):
        with st.spinner("Analyzing your receipt..."):
            image_bytes = uploaded_file.read()
            analysis = analyze_receipt(image_bytes)
            
        st.success("Analysis Complete!")
        st.markdown("### 📊 Your Financial Insights")
        st.write(analysis)

