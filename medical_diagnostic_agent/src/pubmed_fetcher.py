import os
import pandas as pd
from Bio import Entrez
import ssl
import time

# 忽略 Mac 預設的 SSL 憑證驗證錯誤
ssl._create_default_https_context = ssl._create_unverified_context
    Entrez.email = "YOUR EMAIL ADDRESS"


def fetch_pubmed_discussion(query: str, max_results: int = 50) -> pd.DataFrame:
    """
    搜尋 PubMed 並嘗試從 PMC 抓取全文中的 Discussion 部分。
    """
    print(f"開始搜尋具備全文的文獻: {query}...")

    # 1.搜尋 PubMed 中有連結到 PMC (全文) 的文獻

    pmc_query = f"({query}) AND \"open access\"[filter]"

    try:
        search_handle = Entrez.esearch(db="pmc", term=pmc_query, retmax=max_results, sort="relevance")
        search_results = Entrez.read(search_handle)
        search_handle.close()
    except Exception as e:
        print(f"API 搜尋時發生錯誤: {e}")
        return pd.DataFrame()

    pmcid_list = search_results.get("IdList", [])
    if not pmcid_list:
        print("找不到任何具備全文 Discussion 的文獻。")
        return pd.DataFrame()

    print(f"成功找到 {len(pmcid_list)} 篇全文文獻，開始解析 Discussion 區塊...")

    all_data = []

    # 2.從 PMC 抓取 XML 全文
    for pmcid in pmcid_list:
        try:
            # 加上 sleep 防止請求過快被封鎖
            time.sleep(0.3)
            fetch_handle = Entrez.efetch(db="pmc", id=pmcid, retmode="xml")
            article_data = Entrez.read(fetch_handle)
            fetch_handle.close()

            # 解析 XML 結構尋找 Discussion
            
            article = article_data[0]

            # 取得基本資訊
            title = article['front'].get('article-meta', {}).get('title-group', {}).get('article-title', 'No Title')
            if isinstance(title, list): title = " ".join(title)  # 處理特殊格式

            # 尋找 Body 中的 Discussion 區塊
            discussion_text = ""
            body = article.get('body', {})

            if body:
                # 遍歷所有段落(sec)，尋找標題包含 "Discussion" 的部分
                for section in body.get('sec', []):
                    sec_title = str(section.get('title', '')).lower()
                    if 'discussion' in sec_title:
                        # 抓取該區塊下的所有文字段落 (p)
                        paragraphs = section.get('p', [])
                        if isinstance(paragraphs, list):
                            discussion_text = "\n".join([str(p) for p in paragraphs])
                        else:
                            discussion_text = str(paragraphs)
                        break

            if discussion_text:
                all_data.append({
                    'PMCID': pmcid,
                    'Title': title,
                    'Discussion': discussion_text,
                    'Source': 'PMC Full-Text'
                })
                print(f"成功擷取 PMCID: {pmcid} 的 Discussion")

        except Exception as e:
            print(f"處理 PMCID {pmcid} 時跳過，原因: {e}")
            continue

    # 3.轉換為 DataFrame 並輸出
    df = pd.DataFrame(all_data)

    # 儲存路徑
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "data"))
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    output_path = os.path.join(output_dir, "pubmed_discussions.csv")

    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n任務完成！共抓取 {len(df)} 篇 Discussion。")
    print(f"檔案儲存於: {output_path}")
    return df


if __name__ == "__main__":
    test_query = '("undiagnosed jaundice" OR "rare liver disease")'

    df_result = fetch_pubmed_discussion(test_query, max_results=100)

    if not df_result.empty:
        print("\n第一筆 Discussion 片段預覽：")
        print(df_result['Discussion'].iloc[0][:500] + "...")
