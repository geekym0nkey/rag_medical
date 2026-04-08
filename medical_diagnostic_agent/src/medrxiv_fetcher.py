import requests
import pandas as pd
import os

def fetch_recent_medrxiv_papers(start_date: str, end_date: str) -> pd.DataFrame:
    """
    從 medRxiv 抓取指定日期範圍內的未發表臨床醫學文獻。
    API 格式要求: https://api.medrxiv.org/details/medrxiv/[start_date]/[end_date]/[cursor]/json
    """
    
    all_papers = []
    cursor = 0  # API 分頁指標，預設從 0 開始

    print(f"開始抓取 {start_date} 至 {end_date} 的 medRxiv 臨床文獻...")

    while True:
        # 組裝 API 網址，每次抓取 100 筆資料
        url = f"https://api.medrxiv.org/details/medrxiv/{start_date}/{end_date}/{cursor}/json"
        response = requests.get(url)

        # 檢查網路請求是否成功
        if response.status_code != 200:
            print(f"API 請求失敗，狀態碼: {response.status_code}")
            break

        data = response.json()
        #取得 messages 狀態,先抓出列表，如果抓不到就給空列表 []

        messages = data.get('messages', [])

        if not messages or messages[0].get('status') != 'ok':
            print("資料抓取完畢或發生錯誤。")
            break

        # 為了後面能抓到 'total'，我們可以先把這個字典存起來
        status_info = messages[0]

        # 論文的詳細資料放在 'collection' 陣列中
        collection = data.get('collection', [])

        for paper in collection:
            # 安全地獲取標題與摘要
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')

            # 轉換為小寫以便於關鍵字比對
            title_lower = title.lower()
            abstract_lower = abstract.lower()

            # 醫學關鍵字過濾
            if ('jaundice' in title_lower or 'jaundice' in abstract_lower
                    or 'bilirubin' in title_lower or 'bilirubin' in abstract_lower
                    or 'rare liver disease' in title_lower or 'rare liver disease' in abstract_lower
                    or "hyperbilirubinemia" in title_lower or 'hyperbilirubinemia' in abstract_lower
            ) :
                all_papers.append({
                    'Title': title,
                    'Authors': paper.get('authors', ''),
                    'Abstract': abstract,
                    'Date': paper.get('date', ''),
                    'DOI': paper.get('doi', ''),
                    'Source': 'medRxiv (Preprint)'
                })


        
        total_count = int(status_info.get('total', 0))
        cursor += 100
        if cursor >= total_count:
            break

    df = pd.DataFrame(all_papers)
    print(f"抓取完成，共找到 {len(df)} 篇相關的最新文獻。")

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "medrxiv_fetcher.csv")

    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"medrxiv資訊抓取完成！基因相關資料已成功儲存至:\n {output_path}")

    return df



# 測試程式碼
if __name__ == "__main__":
    # 搜尋 2000 年後的資料
    df_results = fetch_recent_medrxiv_papers("2000-01-01", "2026-03-01")
    if not df_results.empty:
        # 印出前幾筆資料
        print(df_results.head())
