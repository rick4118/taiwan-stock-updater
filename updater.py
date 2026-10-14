import streamlit as st
import requests
import pandas as pd
import io

# 設定網頁標題
st.set_page_config(
    page_title="台灣股市代號自動更新器 (受保護)",
    page_icon="🇹🇼",
    layout="centered"
)

# 初始化 Session State 用來記憶前次抓取的資料，達到比對功能
if 'prev_tw_set' not in st.session_state:
    st.session_state['prev_tw_set'] = set()
if 'prev_two_set' not in st.session_state:
    st.session_state['prev_two_set'] = set()

st.title("🇹🇼 台灣股市最新代號自動抓取器")
st.write("請先輸入管理密碼，再點擊更新。系統將自動從證交所下載最新股票代號並與前次進行變動比對！")

# 1. 密碼驗證
pwd_input = st.text_input("🔒 請輸入管理密碼:", type="password")

# 2. 開始更新按鈕
update_btn = st.button("🔄 開始下載與比對股票名單", use_container_width=True)

if update_btn:
    # 驗證密碼
    if pwd_input.strip() != "592888":
        st.error("❌ 密碼錯誤，拒絕存取數據！")
    else:
        with st.spinner("⏳ 正在連線至證交所與櫃買中心下載最新數據，請稍候..."):
            try: 
                # 模擬瀏覽器 User-Agent 避免阻擋
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }

                # --- A. 下載上市股票 (TWSE) ---
                tw_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
                tw_res = requests.get(tw_url, headers=headers, timeout=15)
                tw_res.raise_for_status()

                # 使用 io.StringIO 包裝，避免 Pandas 將 HTML 內容誤判為本機檔案路徑
                tables = pd.read_html(io.StringIO(tw_res.text))
                df_tw = tables[0]

                current_tw_list = []
                for val in df_tw[0].values:
                    if isinstance(val, str):
                        parts = val.split('\u3000')
                        if len(parts) >= 1:
                            ticker = parts[0].strip()
                            if len(ticker) == 4 and ticker.isdigit():
                                current_tw_list.append(f"{ticker}.TW")
                current_tw_set = set(current_tw_list)

                # --- B. 下載上櫃股票 (TPEx) ---
                two_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
                two_res = requests.get(two_url, headers=headers, timeout=15)
                two_res.raise_for_status()

                # 使用 io.StringIO 包裝
                tables_otc = pd.read_html(io.StringIO(two_res.text))
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

                # --- C. 進行增減比對並呈現 ---
                st.success(f"✅ 成功更新資料！最新上市股票 {len(current_tw_set)} 檔，上櫃股票 {len(current_two_set)} 檔。")

                # 顯示比對變動
                prev_tw = st.session_state['prev_tw_set']
                prev_two = st.session_state['prev_two_set']

                st.subheader("🔄 股票變動分析 (與上次比對)")
                if not prev_tw and not prev_two:
                    st.info("ℹ️ 這是本瀏覽器工作階段的第一次下載紀錄，暫無前次數據對比。下次點擊按鈕將會呈現新上市公司或下市公司！")
                else:
                    added_tw = sorted(list(current_tw_set - prev_tw))
                    removed_tw = sorted(list(prev_tw - current_tw_set))
                    added_two = sorted(list(current_two_set - prev_two))
                    removed_two = sorted(list(prev_two - current_two_set))

                    col_comparison1, col_comparison2 = st.columns(2)
                    with col_comparison1:
                        st.markdown("**📈 上市股票 (.TW) 變動：**")
                        st.write(f"🟢 新增個股: {', '.join(added_tw) if added_tw else '無'}")
                        st.write(f"🔴 下市個股: {', '.join(removed_tw) if removed_tw else '無'}")
                    with col_comparison2:
                        st.markdown("**📉 上櫃股票 (.TWO) 變動：**")
                        st.write(f"🟢 新增個股: {', '.join(added_two) if added_two else '無'}")
                        st.write(f"🔴 下市個股: {', '.join(removed_two) if removed_two else '無'}")

                # 儲存本次抓取，留待下次對比
                st.session_state['prev_tw_set'] = current_tw_set.copy()
                st.session_state['prev_two_set'] = current_two_set.copy()

                # 輸出格式化字串方便使用者複製
                tw_output = ", ".join(sorted(list(current_tw_set)))
                two_output = ", ".join(sorted(list(current_two_set)))

                st.subheader("📋 最新代號清單 (點選框框右上角一鍵複製)")

                st.write("**🟢 上市股票 (.TW):**")
                st.code(tw_output, language="text")

                st.write("**🔵 上櫃股票 (.TWO):**")
                st.code(two_output, language="text")

            except Exception as e:
                st.error(f"❌ 處理數據時發生錯誤: {str(e)}")
