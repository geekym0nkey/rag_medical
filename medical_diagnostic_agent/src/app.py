import streamlit as st
from agent_core.rag_engine import generate_clinical_response

# ==========================================
# 1. 網頁介面與環境設定
# ==========================================
st.set_page_config(page_title="黃疸與罕見肝病 AI 參謀", page_icon="🩺", layout="wide")
st.title("🩺 黃疸與罕見肝病 AI 臨床參謀系統")
st.markdown("基於最新 PubMed、medRxiv 臨床文獻與 KEGG 生化代謝路徑的 RAG 決策支援系統。")

# 側邊欄：設定 Gemini API Key
with st.sidebar:
    st.header("⚙️ 系統設定")
    st.markdown("請輸入您的 Google Gemini API Key。這只會在本次執行中有效，確保安全。")
    api_key = st.text_input("Gemini API Key:", type="password")
    if api_key:
        st.success("API Key 已設定！系統準備就緒。")
    else:
        st.warning("請先輸入 API Key 以啟用系統。")

# ==========================================
# 2. 聊天室歷史紀錄初始化
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "您好！我是您的臨床決策參謀。請描述病患的黃疸症狀、檢驗數值，"
                       "或是想探討的生化代謝路徑，我將為您檢索最新文獻並提供分析。",
        }
    ]

# 繪製歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 3. 接收使用者輸入與呼叫 RAG 大腦
# ==========================================
if prompt := st.chat_input(
    "例如：患者黃疸指數過高，但超音波無膽管阻塞，可能涉及哪些 UGT 酵素異常？"
):
    # FIX 1: Guard before doing anything
    if not api_key:
        st.error("請先在左側輸入 Gemini API Key！")
        st.stop()

    # Display and store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display AI response
    with st.chat_message("assistant"):
        with st.spinner("正在檢索最新醫學文獻與 KEGG 生化路徑，並進行邏輯推演..."):
            try:
                # FIX 2: Wrap the engine call in try/except
                result = generate_clinical_response(prompt, api_key)

                # FIX 3: Safely unpack — tolerate None or missing values
                if isinstance(result, tuple) and len(result) == 2:
                    answer, sources = result
                else:
                    answer, sources = str(result), []

                # FIX 4: Fallback if answer is empty or None
                if not answer:
                    answer = "⚠️ 系統未能產生回應，請稍後再試或確認 API Key 是否正確。"

                st.markdown(answer)

                # FIX 5: Append only after confirmed successful response
                st.session_state.messages.append({"role": "assistant", "content": answer})

                # FIX 6: Guard against empty list before showing expander
                if sources and isinstance(sources, list) and len(sources) > 0:
                    with st.expander("📚 點擊查看 AI 參考的醫學文獻與基因路徑 (事後驗證)"):
                        for link in sources:
                            st.info(link)

            except Exception as e:
                error_msg = f"⚠️ 系統發生錯誤：{e}"
                st.error(error_msg)
                # Store the error in chat history so the conversation stays coherent
                st.session_state.messages.append({"role": "assistant", "content": error_msg})