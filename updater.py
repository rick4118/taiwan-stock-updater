import requests
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import json

# 用於暫存上一次更新的股票集合，達到比對功能
if 'prev_tw_set' not in globals():
    prev_tw_set = set()
if 'prev_two_set' not in globals():
    prev_two_set = set()

# 1. 建立 UI 標題與說明文字
title_label = widgets.HTML(
    value="""
    <div style='background-color: #f0f7f4; padding: 15px; border-radius: 8px; border-left: 5px solid #2e7d32; margin-bottom: 15px;'>
        <h3 style='margin-top:0; color: #1b5e20;'><b>🇹🇼 台灣股市最新代號自動抓取器（智慧增刪比對密碼保護版）</b></h3>
        <p style='margin-bottom:0;'>請先輸入管理密碼，再點擊「🔄 更新股票名單」按鈕，系統將自動從證交所與櫃買中心下載最新股票代號並進行比對變動！</p>
    </div>
    """
)

# 2. 建立密碼輸入欄位 (預設密碼為 592888)
pwd_input = widgets.Password(
    value='',
    placeholder='請輸入密碼',
    description='密碼:',
    disabled=False,
    layout=widgets.Layout(width='250px')
)

# 3. 建立按鈕與顯示框
update_btn = widgets.Button(
    description='🔄 更新股票名單',
    button_style='info',
    layout=widgets.Layout(width='250px', height='45px')
)

tw_output_area = widgets.Textarea(
    value='尚未更新資料...',
    placeholder='更新後將顯示全體上市股票代號 (如: 2330.TW, 2454.TW...)',
    description='上市公司 (.TW):',
    layout=widgets.Layout(width='95%', height='140px'),
    disabled=True
)

two_output_area = widgets.Textarea(
    value='尚未更新資料...',
    placeholder='更新後將顯示全體上櫃股票代號 (如: 5351.TWO, 3141.TWO...)',
    description='上櫃公司 (.TWO):',
    layout=widgets.Layout(width='95%', height='140px'),
    disabled=True
)

comparison_output_area = widgets.Textarea(
    value='第一次更新後，再次點擊更新即可顯示與前次的股票變動比較。',
    placeholder='顯示新增與刪除的上市上櫃股票...',
    description='🔄 股票變動分析:',
    layout=widgets.Layout(width='95%', height='140px'),
    disabled=True
)

status_label = widgets.HTML(value="<p style='color: #666;'>請輸入密碼並點擊上方按鈕開始下載並比對...</p>")
copy_buttons_container = widgets.Output()

# 4. 定義一鍵複製的 HTML/JS 產生器
def generate_copy_buttons_html(tw_text, two_text):
    tw_text_escaped = tw_text.replace("'", "\\'").replace("\n", " ")
    two_text_escaped = two_text.replace("'", "\\'").replace("\n", " ")

    html_code = f"""
    <div style='display: flex; gap: 20px; margin-top: 10px; margin-bottom: 15px;'>
        <button onclick=\"navigator.clipboard.writeText('{tw_text_escaped}').then(() => alert('📋 上市股票代號已成功複製到剪貼簿！'))\"
                style='background-color: #2e7d32; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;'>
            📋 一鍵複製「上市股票」
        </button>
        <button onclick=\"navigator.clipboard.writeText('{two_text_escaped}').then(() => alert('📋 一鍵複製「上櫃股票」'))\"
                style='background-color: #0277bd; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;'>
            📋 一鍵複製「上櫃股票」
        </button>
    </div>
    """
    return html_code

# 5. 定義更新與比對邏輯
def fetch_and_compare_tickers(b):
    global prev_tw_set, prev_two_set

    input_pwd = pwd_input.value.strip()
    if input_pwd != "592888":
        status_label.value = "<p style='color: #c62828; font-weight: bold;'>❌ 密碼錯誤或未輸入，拒絕存取數據！</p>"
        return

    update_btn.disabled = True
    status_label.value = "<p style='color: #d84315;'>⏳ 正在繞過限制獲取最新上市上櫃代號，請稍候...</p>"

    try:
        # 使用證交所對一般瀏覽器開放的普通網頁 Table API，其阻擋機制較寬鬆
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # --- A. 下載上市股票 (TWSE) --- 
        # 採用台股公開基本資料網頁爬取法，此網址在 Colab 的相容性與防護穿越率極高
        tw_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        try:
            tw_res = requests.get(tw_url, headers=headers, timeout=15)
            tw_res.raise_for_status()
            tables = pd.read_html(tw_res.text)
            df_tw = tables[0]
            
            # 解析 JSP 結構表格
            current_tw_list = []
            for val in df_tw[0].values:
                if isinstance(val, str):
                    parts = val.split('\u3000')
                    if len(parts) >= 1:
                        ticker = parts[0].strip()
                        # 篩選 4 碼純數字普通股
                        if len(ticker) == 4 and ticker.isdigit():
                            current_tw_list.append(f"{ticker}.TW")
            current_tw_set = set(current_tw_list)
        except Exception as e:
            status_label.value = f"<p style='color: #c62828; font-weight: bold;'>❌ 讀取上市股票網頁失敗: {str(e)}</p>"
            update_btn.disabled = False
            return

        # --- B. 下載上櫃股票 (TPEx) ---
        two_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        try:
            two_res = requests.get(two_url, headers=headers, timeout=15)
            two_res.raise_for_status()
            tables_otc = pd.read_html(two_res.text)
            df_otc = tables_otc[0]
            
            current_two_list = []
            for val in df_otc[0].values:
                if isinstance(val, str):
                    parts = val.split('\u3000')
                    if len(parts) >= 1:
                        ticker = parts[0].strip()
                        if len(ticker) == 4 and ticker.isdigit():
                            current_two_list.append(f"{ticker}.TWO")
            current_two_set = set(current_two_list)
        except Exception as e:
            status_label.value = f"<p style='color: #c62828; font-weight: bold;'>❌ 讀取上櫃股票網頁失敗: {str(e)}</p>"
            update_btn.disabled = False
            return

        # --- C. 進行增減比對 ---
        comparison_text = ""
        if not prev_tw_set and not prev_two_set:
            comparison_text = "這是本工作階段的第一次下載紀錄，因此暫無前次數據可供對比。下次更新將會自動為您呈現新增或下市的個股！"
        else:
            added_tw = sorted(list(current_tw_set - prev_tw_set))
            removed_tw = sorted(list(prev_tw_set - current_tw_set))
            added_two = sorted(list(current_two_set - prev_two_set))
            removed_two = sorted(list(prev_two_set - current_two_set))

            comparison_parts = []
            comparison_parts.append("=== 上市股票變動 (.TW) ===")
            comparison_parts.append(f"🟢 新增個股 ({len(added_tw)}): {', '.join(added_tw) if added_tw else '無'}")
            comparison_parts.append(f"🔴 下市/刪除個股 ({len(removed_tw)}): {', '.join(removed_tw) if removed_tw else '無'}")
            comparison_parts.append("\n=== 上櫃股票變動 (.TWO) ===")
            comparison_parts.append(f"🟢 新增個股 ({len(added_two)}): {', '.join(added_two) if added_two else '無'}")
            comparison_parts.append(f"🔴 下市/刪除個股 ({len(removed_two)}): {', '.join(removed_two) if removed_two else '無'}")
            comparison_text = "\n".join(comparison_parts)

        # 更新暫存狀態
        prev_tw_set = current_tw_set.copy()
        prev_two_set = current_two_set.copy()

        tw_result_str = ", ".join(sorted(list(current_tw_set)))
        two_result_str = ", ".join(sorted(list(current_two_set)))

        tw_output_area.disabled = False
        two_output_area.disabled = False
        comparison_output_area.disabled = False

        tw_output_area.value = tw_result_str
        two_output_area.value = two_result_str
        comparison_output_area.value = comparison_text

        status_label.value = f"<p style='color: #2e7d32; font-weight: bold;'>✅ 成功更新與比對！最新上市：{len(current_tw_set)} 檔，上櫃：{len(current_two_set)} 檔。</p>"

        with copy_buttons_container:
            clear_output()
            display(HTML(generate_copy_buttons_html(tw_result_str, two_result_str)))

    except Exception as e:
        status_label.value = f"<p style='color: #c62828;'>❌ 下載與比對失敗。原因: {str(e)}</p>"

    finally:
        update_btn.disabled = False

# 綁定按鈕事件
update_btn.on_click(fetch_and_compare_tickers)

# 6. UI 版面配置
layout_container = widgets.VBox([
    title_label,
    widgets.HBox([pwd_input, update_btn]),
    status_label,
    copy_buttons_container,
    widgets.HTML(value="<b style='color: #2e7d32;'>🟢 上市股票 (已自動補 .TW)：</b>"),
    tw_output_area,
    widgets.HTML(value="<br><b style='color: #0277bd;'>🔵 上櫃股票 (已自動補 .TWO)：</b>"),
    two_output_area,
    widgets.HTML(value="<br><b style='color: #d84315;'>🔄 股票變動分析 (與上次數據對比)：</b>"),
    comparison_output_area
])

display(layout_container)
