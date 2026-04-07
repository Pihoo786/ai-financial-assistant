import streamlit as st
import boto3
import json
import base64
import re
from PIL import Image
import io
import os
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)
st.set_page_config(
    page_title="AI Financial Clarity Assistant",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
    <style>
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .metric-label {font-size: 0.85rem; color: #888; margin-bottom: 4px;}
    .metric-value {font-size: 1.8rem; font-weight: 800; color: #1a1a2e;}
    .chat-msg-user {
        background: #e8f4fd;
        border-radius: 10px;
        padding: 0.7rem 1rem;
        margin: 0.3rem 0;
        text-align: right;
    }
    .chat-msg-ai {
        background: #f0faf0;
        border-radius: 10px;
        padding: 0.7rem 1rem;
        margin: 0.3rem 0;
    }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)





# Session state
for key, val in {
    "history": [],
    "last_analysis": None,
    "chat_messages": [],
    "spending_score": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

def get_pdf_pages_as_jpeg(pdf_bytes):
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        pages.append(pix.tobytes("jpeg"))
    return pages

def convert_to_jpeg(file_bytes):
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def analyze_receipt(file_bytes):
    jpeg_bytes = convert_to_jpeg(file_bytes)
    image_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')
    message = {
        "role": "user",
        "content": [
            {"image": {"format": "jpeg", "source": {"bytes": image_base64}}},
            {"text": """You are a friendly financial assistant. Analyze this receipt and respond in this exact format:

**🧾 Items Purchased:**
List each item with its price on a new line

**📂 Category:**
State ONE main category (Food, Transport, Shopping, Entertainment, Health, Other)

**💵 Total Spent:**
State the total like: ₹259.02

**📊 Spending Summary:**
2-3 sentences explaining the spending pattern in simple, friendly language

**💡 Smart Suggestions:**
Give 3 specific, actionable tips to save money

Keep the tone friendly and encouraging."""}
        ]
    }
    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        body=json.dumps({"messages": [message], "inferenceConfig": {"maxTokens": 1000}})
    )
    return json.loads(response["body"].read())["output"]["message"]["content"][0]["text"]

def extract_total(text):
    # Sum ALL amounts found in the text
    matches = re.findall(r'₹\s*([\d,]+\.?\d*)', text)
    if not matches:
        return 0.0
    # Return the largest value (most likely the grand total)
    return max(float(m.replace(',', '')) for m in matches)

def extract_category(text):
    # Find all categories mentioned and pick most common
    categories = ["Food", "Transport", "Shopping", "Entertainment", "Health", "Other"]
    found = []
    for c in categories:
        if c.lower() in text.lower():
            found.append(c)
    return found[0] if found else "Other"

def get_spending_score(history):
    summary = "\n".join([f"Receipt {i+1}: {r['name']}, ₹{r['total']}, Category: {r['category']}" 
                         for i, r in enumerate(history)])
    message = {
        "role": "user",
        "content": [{"text": f"""Based on this spending data, give a financial health score:

{summary}

Respond in this exact format:
**Score: X/10**
**Rating:** (Excellent/Good/Fair/Needs Improvement)
**Why:** 2 sentences explaining the score
**Top Tip:** One most important improvement

Be honest but encouraging."""}]
    }
    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        body=json.dumps({"messages": [message], "inferenceConfig": {"maxTokens": 300}})
    )
    return json.loads(response["body"].read())["output"]["message"]["content"][0]["text"]

def chat_with_nova(question, history):
    summary = "\n".join([f"Receipt: {r['name']}, Total: ₹{r['total']}, Category: {r['category']}\nAnalysis: {r['analysis'][:300]}" 
                         for r in history])
    message = {
        "role": "user",
        "content": [{"text": f"""You are a friendly financial advisor. The user has analyzed these receipts:

{summary}

User question: {question}

Answer in 2-4 sentences, be specific to their actual spending data, friendly and helpful."""}]
    }
    response = client.invoke_model(
        modelId="amazon.nova-lite-v1:0",
        body=json.dumps({"messages": [message], "inferenceConfig": {"maxTokens": 400}})
    )
    return json.loads(response["body"].read())["output"]["message"]["content"][0]["text"]

# ── HEADER ──
st.title("💰 AI Financial Clarity Assistant")
st.markdown("*Your personal AI-powered spending advisor — powered by Amazon Nova*")
st.divider()

# ── DASHBOARD METRICS ──
if st.session_state.history:
    total = sum(r["total"] for r in st.session_state.history)
    count = len(st.session_state.history)
    categories = [r["category"] for r in st.session_state.history]
    top_cat = max(set(categories), key=categories.count)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">💸 Total Spent</div><div class="metric-value">₹{total:.2f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">🧾 Receipts</div><div class="metric-value">{count}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">🏷️ Top Category</div><div class="metric-value" style="font-size:1.3rem">{top_cat}</div></div>', unsafe_allow_html=True)
    with c4:
        avg = total / count
        st.markdown(f'<div class="metric-card"><div class="metric-label">📊 Avg per Receipt</div><div class="metric-value">₹{avg:.2f}</div></div>', unsafe_allow_html=True)
    st.divider()

# ── BUDGET GOAL ──
with st.sidebar:
    st.markdown("### 🎯 Budget Goal")
    budget = st.number_input("Set monthly budget (₹)", min_value=0, value=5000, step=100)
    if st.session_state.history:
        total_spent = sum(r["total"] for r in st.session_state.history)
        pct = min(total_spent / budget * 100, 100) if budget > 0 else 0
        color = "🟢" if pct < 60 else "🟡" if pct < 85 else "🔴"
        st.markdown(f"**{color} ₹{total_spent:.2f} / ₹{budget}**")
        st.progress(pct / 100)
        remaining = budget - total_spent
        if remaining > 0:
            st.success(f"₹{remaining:.2f} remaining")
        else:
            st.error(f"Over budget by ₹{abs(remaining):.2f}!")

    st.divider()

    # Spending Score
    st.markdown("### 🏆 Spending Score")
    if st.session_state.history:
        if st.button("Get My Score"):
            with st.spinner("Calculating..."):
                st.session_state.spending_score = get_spending_score(st.session_state.history)
        if st.session_state.spending_score:
            st.markdown(st.session_state.spending_score)
    else:
        st.info("Analyze receipts to get your score!")

    st.divider()
    if st.session_state.history:
        if st.button("🗑️ Clear All Data"):
            for key in ["history", "last_analysis", "chat_messages", "spending_score"]:
                st.session_state[key] = [] if key != "last_analysis" and key != "spending_score" else None
            st.rerun()

# ── MAIN CONTENT ──
tab1, tab2, tab3 = st.tabs(["📤 Analyze Receipt", "💬 Chat with Nova", "🗂️ History & Charts"])

with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Upload Receipt")
        uploaded_file = st.file_uploader("Choose an image or PDF", type=["jpg", "jpeg", "png", "avif", "webp", "pdf"])
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                st.info("📄 PDF uploaded successfully!")
            else:
                st.image(uploaded_file, use_container_width=True)

        analyze_btn = st.button("🔍 Analyze My Spending", use_container_width=True)

        if analyze_btn and uploaded_file:
            with st.spinner("Nova is analyzing your receipt..."):
                file_bytes = uploaded_file.read()
                if uploaded_file.type == "application/pdf":
                    pages = get_pdf_pages_as_jpeg(file_bytes)
                    if len(pages) > 10:
                        st.warning(f"PDF has {len(pages)} pages. Analyzing first 10 only.")
                        pages = pages[:10]
                    all_analysis = []
                    for i, page_bytes in enumerate(pages):
                        analysis = analyze_receipt(page_bytes)
                        all_analysis.append(f"**Page {i+1}:**\n{analysis}")
                    analysis = "\n\n---\n\n".join(all_analysis)
                else:
                    analysis = analyze_receipt(file_bytes)
                total = extract_total(analysis)
                category = extract_category(analysis)
                st.session_state.last_analysis = analysis
                st.session_state.spending_score = None
                st.session_state.history.append({
                    "name": uploaded_file.name,
                    "analysis": analysis,
                    "total": total,
                    "category": category
                })
            st.success("✅ Analysis complete!")
        elif analyze_btn:
            st.warning("Please upload a receipt first!")

    with col2:
        st.markdown("### Your Insights")
        if st.session_state.last_analysis:
            st.markdown(st.session_state.last_analysis)
            st.download_button(
                label="📥 Download Insights",
                data=st.session_state.last_analysis,
                file_name="spending_insights.txt",
                mime="text/plain"
            )
        else:
            st.info("👈 Upload a receipt to see insights here!")

with tab2:
    st.markdown("### 💬 Ask Nova About Your Spending")

    if not st.session_state.history:
        st.info("Analyze at least one receipt first, then come back to chat!")
    else:
        st.markdown("*Ask me anything about your spending — I know your receipts!*")

        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-msg-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-msg-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

        question = st.text_input("Ask a question...", placeholder="e.g. Am I spending too much on food?")
        if st.button("Send 💬") and question:
            with st.spinner("Nova is thinking..."):
                answer = chat_with_nova(question, st.session_state.history)
            st.session_state.chat_messages.append({"role": "user", "content": question})
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
            st.rerun()

with tab3:
    st.markdown("### 🗂️ All Receipts")

    if not st.session_state.history:
        st.info("No receipts analyzed yet!")
    else:
        # Category chart
        try:
            import pandas as pd
            cat_data = {}
            for r in st.session_state.history:
                cat_data[r["category"]] = cat_data.get(r["category"], 0) + r["total"]
            df = pd.DataFrame(list(cat_data.items()), columns=["Category", "Amount"])
            st.markdown("#### Spending by Category")
            st.bar_chart(df.set_index("Category"))
        except:
            pass

        for i, record in enumerate(reversed(st.session_state.history)):
            with st.expander(f"📄 {record['name']} — ₹{record['total']:.2f} ({record['category']})"):
                st.markdown(record["analysis"])

st.divider()
st.markdown("<center><small>Powered by Amazon Nova on AWS Bedrock</small></center>", unsafe_allow_html=True)
