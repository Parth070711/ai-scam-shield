import streamlit as st
import os
from pymongo import MongoClient
import certifi
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Safely pull the keys from the Streamlit Secrets menu you set up earlier
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
MONGO_URI = st.secrets["MONGO_URI"]

# Validate credentials are loaded
if not GEMINI_API_KEY or not MONGO_URI:
    st.error("❌ Missing credentials. Set GEMINI_API_KEY and MONGO_URI in environment variables or .env file")
    st.stop()

# Connect to Gemini Brain
client = genai.Client(api_key=GEMINI_API_KEY)

# Connect to Real MongoDB Cloud Cluster (Updated Secure Version)
@st.cache_resource
def init_mongodb():
    # Adding extra arguments to force the handshake past Windows firewalls
    db_client = MongoClient(
        MONGO_URI, 
        tlsCAFile=certifi.where(),
        tlsAllowInvalidCertificates=True,  # Bypasses local network handshake issues
        serverSelectionTimeoutMS=5000     # Stops the script from hanging forever
    )
    db = db_client["fraud_shield_db"]
    collection = db["known_scams"]

    
    # Pre-populate database with live scam definitions if empty
    if collection.count_documents({}) == 0:
        collection.insert_many([
            {"type": "text link", "details": "🚨 HIGH RISK: Known 'Package Delivery' SMS scam. Clicking the link steals card details. Action: Block number."},
            {"type": "bank alert", "details": "🚨 CRITICAL RISK: Urgency fraud. Banks never ask for pins/passwords over text. Action: Call the number on your physical card."},
            {"type": "crypto investment", "details": "⚠️ FRAUD WARNING: Fake WhatsApp investment scam. Promises of daily guaranteed profits are fraudulent."}
        ])
    return collection

try:
    scam_collection = init_mongodb()
except Exception as e:
    st.error(f"MongoDB Connection Error: {e}")

# 2. Real Live Database Tool
def query_scam_database(scam_type: str) -> str:
    """Queries the live MongoDB Atlas cluster database for matching fraud pattern records."""
    search_key = scam_type.lower().strip()
    result = scam_collection.find_one({"type": search_key})
    
    if result:
        return f"MongoDB Database Match Found: {result['details']}"
    return "ℹ️ Pattern not logged in MongoDB cluster history yet. Treat any urgent monetary request as highly suspicious."

my_tools = [query_scam_database]
instructions = "You are an AI Scam Shield Agent. Use the MongoDB tool to look up fraud patterns and give safety steps."

# 3. Web User Interface Setup
st.title("🛡️ AI Scam Shield Agent")
st.caption("Financial Services Track — Powered by Gemini & MongoDB Atlas Cluster")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_prompt := st.chat_input("Paste a suspicious message or email here..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.chat_message("user").write(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Connecting to MongoDB cluster and analyzing text..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        tools=my_tools,
                        system_instruction=instructions,
                    )
                )
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as error:
                st.error(f"Processing error: {error}")
