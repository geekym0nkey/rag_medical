import os
import pandas as pd
from Bio import Entrez
import ssl
import time

# 忽略 Mac 預設的 SSL 憑證驗證錯誤
ssl._create_default_https_context = ssl._create_unverified_context
Entrez.email = "studyissofun.@gmail.com"


def fetch_pubmed_discussion(query: str, max_results: int = 50) -> pd.DataFrame:
    """
    搜尋 PubMed 並嘗試從 PMC 抓取全文中的 Discussion 部分。
    """
    print(f"開始搜尋具備全文的文獻: {query}...")

    # 第一階段：搜尋 PubMed 中有連結到 PMC (全文) 的文獻
    # 加入 "pubmed pmc local"[filter] 確保我們抓得到全文

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

    # 第二階段：從 PMC 抓取 XML 全文
    for pmcid in pmcid_list:
        try:
            # 加上 sleep 防止請求過快被封鎖
            time.sleep(0.3)
            fetch_handle = Entrez.efetch(db="pmc", id=pmcid, retmode="xml")
            article_data = Entrez.read(fetch_handle)
            fetch_handle.close()

            # 解析 XML 結構尋找 Discussion
            # PMC 的結構通常是：Front (Meta), Body (Content), Back (Refs)
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

    # 第三階段：轉換為 DataFrame 並輸出
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
    # 使用您的搜尋條件
    test_query = '("undiagnosed jaundice" OR "rare liver disease")'

    df_result = fetch_pubmed_discussion(test_query, max_results=100)

    if not df_result.empty:
        print("\n第一筆 Discussion 片段預覽：")
        print(df_result['Discussion'].iloc[0][:500] + "...")
'''
import os
import pandas as pd
from Bio import Entrez
import ssl

# 忽略 Mac 預設的 SSL 憑證驗證錯誤
ssl._create_default_https_context = ssl._create_unverified_context
# 這是 NCBI 的強制規定，請務必填入您的 Email
# 若伺服器過載，NCBI 才能聯絡您，否則 IP 可能會被封鎖
Entrez.email = "studyissofun.@gmail.com"


def fetch_pubmed_papers(query: str, max_results: int = 1000) -> pd.DataFrame:
    """
    從 PubMed 抓取正式發表的醫學文獻，並自動輸出為 CSV 檔案。
    """
    print(f"開始在 PubMed 搜尋: {query}...")

    # 第一階段：使用 esearch 取得文獻的 PMID 清單
    try:
        search_handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
        search_results = Entrez.read(search_handle)
        search_handle.close()
    except Exception as e:
        print(f"API 搜尋時發生錯誤: {e}")
        return pd.DataFrame()

    # 確保正確賦予空列表
    id_list = search_results.get("IdList", )
    if not id_list:
        print("找不到任何相關文獻。")
        return pd.DataFrame()

    print(f"成功找到 {len(id_list)} 篇文獻，開始抓取詳細 XML 資料...")

    # 第二階段：使用 efetch 透過 PMID 清單取得詳細的 XML 結構資料
    try:
        fetch_handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
        papers = Entrez.read(fetch_handle)
        fetch_handle.close()
    except Exception as e:
        print(f"抓取詳細資料時發生錯誤: {e}")
        return pd.DataFrame()

    # 絕對正確的空列表初始化
    all_papers = []

    # 第三階段：解析深層的字典結構，加入預設空列表
    pubmed_articles = papers.get('PubmedArticle', )

    for paper in pubmed_articles:
        medline_citation = paper.get('MedlineCitation', {})
        article = medline_citation.get('Article', {})
        pubmed_data = paper.get('PubmedData', {})

        # 1. 取得 PMID (PubMed 唯一識別碼)
        pmid = str(medline_citation.get('PMID', ''))

        # 2. 取得標題
        title = article.get('ArticleTitle', '')

        # 3. 取得摘要
        abstract_text = ''
        if 'Abstract' in article and 'AbstractText' in article['Abstract']:
            abstract_raw = article['Abstract']

            # PubMed 上的結構化摘要 (如 Background, Methods) 會被解析成 List
            if isinstance(abstract_raw, list):
                abstract_text = ' '.join(str(text) for text in abstract_raw)
            else:
                abstract_text = str(abstract_raw)

        # 4. 取得作者清單
        authors_list = []
        if 'AuthorList' in article:
            for author in article['AuthorList']:
                last_name = author.get('LastName', '')
                fore_name = author.get('ForeName', '')
                if last_name or fore_name:
                    authors_list.append(f"{fore_name} {last_name}".strip())
        authors = ', '.join(authors_list)

        # 5. 取得出版日期
        pub_date = ''
        if 'History' in pubmed_data:
            for date_info in pubmed_data['History']:
                # 確保 attributes 存在再進行比對
                if hasattr(date_info, 'attributes') and date_info.attributes.get('PubStatus') == 'pubmed':
                    pub_date = f"{date_info.get('Year', '')}-{date_info.get('Month', '')}-{date_info.get('Day', '')}"
                    break

        # 6. 取得 DOI 連結
        doi = ''
        if 'ArticleIdList' in pubmed_data:
            for article_id in pubmed_data['ArticleIdList']:
                if hasattr(article_id, 'attributes') and article_id.attributes.get('IdType') == 'doi':
                    doi = str(article_id)
                    break

        # 只有在標題或摘要存在時才加入清單
        if title or abstract_text:
            all_papers.append({
                'PMID': pmid,
                'Title': title,
                'Authors': authors,
                'Abstract': abstract_text,
                'Date': pub_date,
                'DOI': doi,
                'Source': 'PubMed (Published)'
            })

    # 第四階段：轉換為 DataFrame 並輸出為 CSV
    df = pd.DataFrame(all_papers)

    # 儲存路徑邏輯：定位到專案的 data 資料夾
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    output_path = os.path.join(output_dir, "pubmed_papers.csv")

    # 輸出為 CSV，使用 utf-8-sig 確保 Excel 開啟時不會有中文亂碼
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"抓取完成！共 {len(df)} 篇正式文獻已成功儲存至:\n {output_path}")
    return df


if __name__ == "__main__":
    # 測試執行：搜尋未確診黃疸或罕見肝病相關文獻
    test_query = '("undiagnosed jaundice" OR "viral jaundice" OR "rare liver disease" OR "unexplained high bilirubin" ) AND ("2018/01/01" : "2026/12/31"[dp])'
    df_result = fetch_pubmed_papers(test_query, max_results=1000)

    if not df_result.empty:
        print("\n前三筆資料預覽：")
        print(df_result.head(3))
'''