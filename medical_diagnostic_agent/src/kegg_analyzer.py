import requests
import pandas as pd
import re
import os


def fetch_kegg_pathway_genes(pathway_id: str):
    """
    透過 KEGG REST API 獲取特定代謝路徑中的基因資訊。
    優化版本：提高可讀性並修正型別錯誤。
    """
    url = f"http://rest.kegg.jp/get/{pathway_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"連線失敗: {e}"}

    # 1. 提取 GENE 區塊：利用正規表達式直接抓出 GENE 到下一個大項之前的內容
    # KEGG 格式的大項（如 COMPOUND, REFERENCE）都是全大寫開頭
    pattern = r"GENE\s+(.*?)(?=\n[A-Z]|\Z)"
    match = re.search(pattern, response.text, re.DOTALL)

    if not match:
        return {"error": "找不到 GENE 區塊"}

    gene_block = match.group(1)
    genes_info = {}

    # 2. 逐行解析基因資訊
    for line in gene_block.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # KEGG 基因行格式通常是： "ID  Symbol; Description"
        # 先用分號切開「名稱」與「描述」
        parts = line.split(';', 1)

        # 處理前半部 (ID 與 Symbol)
        name_part = parts[0].strip()
        # 使用 split(maxsplit=1) 確保只切出第一個空格（即 ID）
        name_elements = name_part.split(None, 1)

        if len(name_elements) >= 1:
            gene_id = name_elements[0]
            # 加這行 debug
            print(f"gene_id type={type(gene_id)}, value={repr(gene_id)}")

            # 取得描述（如果沒有描述則給予空字串）
            description = parts[1].strip() if len(parts) > 1 else ""

            genes_info[gene_id] = description

    # 修正重點 1：將字典轉換為具有明確欄位名稱的 DataFrame
    df = pd.DataFrame(list(genes_info.items()), columns=["gene_id", "description"])

    return df


if __name__ == "__main__":
    pathways = ["hsa04976", "hsa00860", "hsa02010"] #hard coded related pathway...
    all_results = []

    for pathway in pathways:
        print(f"正在解析 KEGG 路径: {pathway}...")
        result = fetch_kegg_pathway_genes(pathway)

    # 修正重點 2：判斷回傳的是錯誤字典還是成功的 DataFrame
        if isinstance(result, dict) and "error" in result:
            print(f"[{pathway}] 錯誤：{result["error"]}")
        else:
            # 加上來源 pathway 欄位，方便後續區分
            result["pathway_id"] = pathway
            all_results.append(result)
        # 合併所有 pathway 的結果並統一儲存
    if all_results and len(all_results) == len(pathways):
        combined_df = pd.concat(all_results, ignore_index=True)

        # 儲存路徑邏輯：定位到專案的 data 資料夾
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "kegg_analysis.csv")

        # 輸出為 CSV，使用 utf-8-sig 確保 Excel 開啟時不會有中文亂碼
        combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\nKegg資訊抓取完成！所有 pathway 資料已合併儲存至：\n {output_path}")

        # 印出前 20 筆基因資料預覽
        print("\n前 20 筆基因資料預覽：")
        for index, row in combined_df.head(20).iterrows():
            print(f"[{index}] {row['pathway_id']} | {row['gene_id']}: {row['description']}")