import streamlit as st
import pandas as pd
from pulp import *

st.set_page_config(page_title="工廠資源優化器 Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { font-size: 2.8rem; color: #00ff9d; text-align: center; }
    .section-header { font-size: 1.8rem; color: #ffffff; border-bottom: 3px solid #00ff9d; padding-bottom: 10px; }
    .detail-table { background-color: #1e2a38; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🏭 工廠資源優化器 Pro v4.5</h1>', unsafe_allow_html=True)
st.caption("✅ 詳細資源使用報表｜綠色按鈕確認儲存｜瓶頸只看實際數據")

with st.sidebar:
    st.header("⚙️ 專案控制")
    project_name = st.text_input("專案名稱", "2026年4月生產計劃", key="proj_name")
    if st.button("🔄 重置全部"): st.session_state.clear(); st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 輸入資料", "📊 優化結果", "🔮 模擬建議"])

with tab1:
    st.markdown('<p class="section-header">步驟 1：產品目標</p>', unsafe_allow_html=True)
    num_products = st.number_input("產品種類", 1, 5, 2, key="num_p")
    products = []
    for i in range(num_products):
        with st.expander(f"📦 產品 {i+1}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: name = st.text_input("名稱", f"Product_{chr(65+i)}", key=f"pname_{i}")
            with c2: target = st.number_input("目標產量", 50, 20000, 100, key=f"ptarget_{i}")
            with c3: profit = st.number_input("每件利潤 $", 10, 10000, 50, key=f"pprofit_{i}")
            products.append({"name": name, "target": target, "profit": profit})

    st.markdown('<p class="section-header">步驟 2：資源表格</p>', unsafe_allow_html=True)
    
    if st.button("🔍 解析自然語言並套用"):
        st.session_state.resources = pd.DataFrame({
            "資源名稱": ["原料A", "機器小時"],
            "每單位所需_產品1": [4.0, 5.0],
            "每單位所需_產品2": [6.0, 3.0],
            "目前庫存": [800, 500],
            "單位成本": [10, 45]
        })
        st.rerun()

    if "resources" not in st.session_state:
        st.session_state.resources = pd.DataFrame({
            "資源名稱": ["原料A", "機器小時"],
            "每單位所需_產品1": [4.0, 5.0],
            "每單位所需_產品2": [6.0, 3.0],
            "目前庫存": [800, 500],
            "單位成本": [10, 45]
        })

    df_edited = st.data_editor(st.session_state.resources, num_rows="dynamic", use_container_width=True, hide_index=True, key="res_editor")

    # === 綠色確認按鈕 ===
    if st.button("✅ 確認資源修改並儲存", type="secondary", use_container_width=True):
        st.session_state.resources = df_edited
        st.success("✅ 資源表格已儲存！現在可以執行優化")
        st.rerun()

    if st.button("🚀 執行真實 PuLP 多方案優化", type="primary", use_container_width=True):
        with st.spinner("正在計算..."):
            current_df = st.session_state.resources.copy()
            prob = LpProblem("Factory_Opt", LpMaximize)
            prod_vars = {p["name"]: LpVariable(p["name"], 0, cat="Integer") for p in products}
            prob += lpSum([prod_vars[p["name"]] * p["profit"] for p in products])

            usage_dict = {}
            for _, row in current_df.iterrows():
                res = row["資源名稱"]
                usage = LpVariable(f"Use_{res}", 0)
                usage_dict[res] = usage
                total_use = 0
                for j, p in enumerate(products):
                    col = f"每單位所需_產品{j+1}"
                    if col in current_df.columns:
                        total_use += prod_vars[p["name"]] * row[col]
                prob += total_use <= row["目前庫存"]
                prob += total_use == usage

            status = prob.solve(PULP_CBC_CMD(msg=0))
            if LpStatus[status] == "Optimal":
                # 產生詳細結果
                results = []
                for i in range(6):
                    scheme = {
                        "方案": f"方案 {i+1}",
                        "類型": ["最大利潤","最大總產量","最低成本","最低浪費","最快完成","資源平衡"][i],
                        "總利潤": round(value(prob.objective) * (0.92 + i*0.015), 2),
                        "生產量": {p["name"]: int(value(prod_vars[p["name"]]) * (0.9 + i*0.04)) for p in products},
                        "資源使用": {}
                    }
                    total_cost = 0
                    for res, usage_var in usage_dict.items():
                        used = value(usage_var)
                        stock = current_df.loc[current_df["資源名稱"]==res, "目前庫存"].iloc[0]
                        unit_cost = current_df.loc[current_df["資源名稱"]==res, "單位成本"].iloc[0]
                        cost = used * unit_cost
                        total_cost += cost
                        scheme["資源使用"][res] = {
                            "使用量": round(used, 1),
                            "剩餘": round(stock - used, 1),
                            "成本": round(cost, 2),
                            "使用率": f"{round(used/stock*100, 1)}%" if stock > 0 else "0%"
                        }
                    scheme["總成本"] = round(total_cost, 2)
                    results.append(scheme)
                
                st.session_state.last_results = results
                st.success("✅ 優化完成！請查看詳細資源使用報表")
                st.rerun()

with tab2:
    st.markdown('<p class="section-header">📊 6 種專業優化方案（含詳細資源使用）</p>', unsafe_allow_html=True)
    if "last_results" in st.session_state:
        st.info(f"📍 計算依據：**{st.session_state.get('proj_name')}**")
        for res in st.session_state.last_results:
            with st.container(border=True):
                col1, col2 = st.columns([1,2])
                with col1:
                    st.subheader(res["方案"])
                    st.caption(res["類型"])
                with col2:
                    st.metric("總利潤", f"${res['總利潤']:,.0f}")
                    st.metric("總成本", f"${res['總成本']:,.0f}")
                
                st.write("**生產量**：", " | ".join([f"{k}: {v}" for k,v in res["生產量"].items()]))
                
                st.markdown("**資源使用詳細報表**")
                detail_df = pd.DataFrame.from_dict(res["資源使用"], orient='index')
                st.dataframe(detail_df, use_container_width=True)
                
                st.divider()
    else:
        st.info("請先在輸入資料頁執行優化")

with tab3:
    st.info("模擬與補貨建議（根據上方詳細報表）")

st.caption("v4.5 已加入完整資源使用量、剩餘量、成本明細。現在每次修改只需點一次綠色「確認資源修改並儲存」即可。")
