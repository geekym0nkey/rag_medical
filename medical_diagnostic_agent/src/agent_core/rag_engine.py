import os
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma


def generate_clinical_response(query: str, api_key: str):
    """
    接收問題與 Gemini API Key，進行向量檢索並呼叫 LLM 產生臨床建議。
    回傳值: (AI_回答字串, 參考文獻清單)
    """
    # 1. 設定 Gemini API Key 環境變數
    os.environ["GOOGLE_API_KEY"] = api_key

    # 2. 定位資料庫路徑
    # rag_engine.py 在 src/agent_core/ 下，往上推三層回到專案根目錄
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_dir = base_dir / "data" / "chroma_db"

    if not db_dir.exists():
        return "錯誤：找不到向量資料庫，請先執行 vector_builder.py。",[]

    # 3. 載入 ChromaDB 向量資料庫
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=str(db_dir), embedding_function=embeddings)

    # 4. 進行語意檢索 (取前 5 篇最相關資料)
    retriever = db.as_retriever(search_kwargs={"k": 5})
    retrieved_docs = retriever.invoke(query)

    # 5. 整理檢索到的證據與來源 (Metadata)
    context_text = ""
    source_links = []

    for i, doc in enumerate(retrieved_docs):
        meta = doc.metadata
        source_type = meta.get("source_type", "Unknown")
        seen_dois = set() #record DOI

        # 組合給 AI 看的上下文
        context_text += f"\n[證據 {i + 1}] 來源: {source_type}\n內容: {doc.page_content}\n"

        # 組合給醫師看的事後驗證連結
        if source_type in  ("PubMed", "medRxiv"):
            doi = meta.get('doi', '') #retreive DOI first
            if doi and doi in seen_dois:  # already appeared, skip this one
                continue
            seen_dois.add(doi)  # add this current doi to the "set"
            doi_link = f"https://doi.org/{doi}" if meta.get('doi') else "無 DOI"

            source_links.append(f"**[{source_type}] {meta.get('title')}**\n- 作者: {meta.get('authors')}\n- 連結: {doi_link}")

        elif source_type == "KEGG":
            gene_id = meta.get('gene_id', '')
            if gene_id in seen_dois:  # ✅ KEGG 用 gene_id 去重
                continue
            seen_dois.add(gene_id)
            source_links.append(f"**[KEGG 基因] {meta.get('gene_id')}**\n- 路徑: {meta.get('pathway')}")

    # 6. 設計嚴謹的醫療提示詞 (Prompt) 防範幻覺
    system_prompt = """
    你是一位頂尖的肝臟科醫師與生化學家。請根據以下提供的[檢索證據]，回答關於黃疸或罕見肝病的臨床問題。

    【嚴格規則】：
    1. 你只能基於下方提供的[檢索證據]進行回答，絕不能捏造或使用外部記憶。
    2. 如果證據中沒有答案，請直接回答「目前的資料庫中沒有足夠的證據來回答這個問題」。
    3. 在回答的每個推論後面，必須標註來源（例如：[證據 1]、[證據 3]）。
    4. 請將回答結構化，包含可能的病因、生化代謝路徑異常分析，並給出建議。
    5. 患者為50歲左右，所以”新生兒黃疸“的資料只能當作”生化路徑“參考而非疾病依據。 
    6. 患者的黃疸曾經高至22 但是肝指數如同ggt等卻未有明顯異常，肝臟切片酒精性肝炎不嚴重。   
    7. 曾接受類固醇治療，但在類固醇治療後肺部感染嚴重。
    [檢索證據]：
    {context}
    """

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])

    # 7. 呼叫 Gemini 模型
    # temperature=0 代表讓模型給出最保守、最精準的回答，不隨意發散想像
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
        chain = qa_prompt | llm

        # 執行 LangChain 決策鏈
        response = chain.invoke({"context": context_text, "input": query})
        return response.content, source_links

    except Exception as e:
        return f"LLM 呼叫發生錯誤: {str(e)}",[]


# 簡單的本機測試
if __name__ == "__main__":
    # 若要單獨測試此腳本，請在這裡填入您的 API Key
    MY_API_KEY = "AIzaSyDGkc3uivECPSEetF2hVoLlUqu4luh5ofg"
    test_query = "What are the rare genetic causes of jaundice or hyperbilirubinemia?"

    print("正在思考與檢索中...\n")
    answer, sources = generate_clinical_response(test_query, MY_API_KEY)

    print("=== AI 參謀回答 ===")
    print(answer)
    print("\n=== 參考文獻 ===")
    for s in sources:
        print(s)