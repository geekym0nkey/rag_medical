import os
import pandas as pd
from pathlib import Path
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


def build_vector_database():
    print("開始讀取 CSV 資料並建置向量資料庫...")

    # 1. 設定路徑：定位到專案的 data 資料夾
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    db_dir = data_dir / "chroma_db"  # 向量資料庫的儲存位置

    documents = []

    # 2. 讀取並處理 PubMed 正式文獻
    pubmed_path = data_dir / "pubmed_papers.csv"
    if pubmed_path.exists():
        df_pubmed = pd.read_csv(pubmed_path).fillna("").drop_duplicates(subset=["DOI"])  # 將空值填補為空字串
        for _, row in df_pubmed.iterrows():
            # 將標題與摘要組合成要被向量化的文本
            content = f"Title: {row['Title']}\nAbstract: {row['Abstract']}"
            # 建立元數據 (Metadata)，方便未來溯源
            metadata = {
                "source_type": "PubMed",
                "title": row['Title'],
                "authors": row['Authors'],
                "date": str(row['Date']),
                "doi": str(row['DOI']),
                "pmid": str(row.get('PMID', ''))
            }
            documents.append(Document(page_content=content, metadata=metadata))
        print(f"已載入 {len(df_pubmed)} 篇 PubMed 文獻。")

    # 3. 讀取並處理 medRxiv 預印本文獻
    medrxiv_path = data_dir / "medrxiv_fetcher.csv"
    if medrxiv_path.exists():
        df_medrxiv = pd.read_csv(medrxiv_path).fillna("").drop_duplicates(subset=["DOI"])
        for _, row in df_medrxiv.iterrows():
            content = f"Title: {row['Title']}\nAbstract: {row['Abstract']}"
            metadata = {
                "source_type": "medRxiv",
                "title": row['Title'],
                "authors": row['Authors'],
                "date": str(row['Date']),
                "doi": str(row['DOI'])
            }
            documents.append(Document(page_content=content, metadata=metadata))
        print(f"已載入 {len(df_medrxiv)} 篇 medRxiv 文獻。")

    # 4. 讀取並處理 KEGG 基因路徑
    kegg_path = data_dir / "kegg_analysis.csv"
    if kegg_path.exists():
        df_kegg = pd.read_csv(kegg_path).fillna("")
        for _, row in df_kegg.iterrows():
            # 醫學邏輯的文本
            content = f"Gene ID: {row['gene_id']}\nFunction/Description: {row['description']}"
            metadata = {
                "source_type": "KEGG",
                "gene_id": str(row['gene_id']),
                "pathway": "hsa04976 (Bile secretion)"
            }
            documents.append(Document(page_content=content, metadata=metadata))
        print(f"已載入 {len(df_kegg)} 筆 KEGG 基因資料。")

    if not documents:
        print("錯誤：在 data/ 目錄下找不到任何 CSV 檔案，請先執行抓取腳本。")
        return None

    # 5. 載入開源且適合在 Mac 本機執行的 Embedding 模型
    print("正在載入 HuggingFace Embedding 模型 (初次執行會下載模型檔案，請稍候)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 6. 建立 Chroma 向量資料庫並持久化儲存到硬碟
    print("正在計算向量並建立 ChromaDB...")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(db_dir)
    )

    print(f"\n✅ 向量資料庫建置完成！資料庫已儲存至: {db_dir}")
    return vector_store


if __name__ == "__main__":
    # 執行建置
    db = build_vector_database()

    # 建置完成後，進行一次簡單的語意檢索測試
    if db:
        print("\n--- 🧠 測試語意檢索 (Similarity Search) ---")
        test_query = "What are the rare genetic causes of jaundice or hyperbilirubinemia?"
        print(f"問題: {test_query}\n")

        # 檢索最相關的前 3 筆資料
        results = db.similarity_search(test_query, k=3)
        for i, res in enumerate(results):
            print(f"[排名 {i + 1}] 來源庫: {res.metadata.get('source_type')}")
            print(f"相關屬性: {res.metadata}")
            # 只印出前 150 個字元預覽
            print(f"內容節錄: {res.page_content[:150]}...\n")