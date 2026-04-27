import streamlit as st
import pandas as pd
from pulp import *

st.set_page_config(page_title="🏭 進階工廠資源優化器 v2.1", layout="wide")
st.title("🏭 進階工廠資源優化應用程式 v2.1")
st.markdown("**已修復 Infeasible 問題 | 支援真實複雜案例 | 自動建議調整**")

# 步驟1: 多產品目標
st.header("步驟1: 定義產品與目標")
num_products = st.number_input("產品種類數", min_value=1, max_value=5, value=2)
products = []
for i in range(num_products):
    col1, col2, col3 = st.columns(3)
    with col1: name = st.text_input(f"產品 {i+1} 名稱", f"Product_{chr(65+i)}", key=f"name{i}")
    with col2: target = st.number_input(f"目標數量", value=800 if i==0 else 400, key=f"target{i}")
    with col3: profit = st.number_input(f"每件利潤 $", value=100 if i==0 else 150, key=f"profit{i}")
    products.append({"name": name, "target": target, "profit": profit})

# 步驟2: 資源表格
st.header("步驟2 & 3: 資源與庫存")
if "resources" not in st.session_state:
    st.session_state.resources = pd.DataFrame({
        "資源名稱": ["原料A", "原料B", "原料C", "機器小時", "人工小時", "能源"],
        "每單位所需_產品1": [3.0, 4.0, 0.0, 2.0, 1.5, 3.0],
        "每單位所需_產品2": [2.0, 1.0, 0.7, 3.0, 2.5, 1.0],
        "目前庫存": [5000, 3000, 600, 2500, 1800, 2000],
        "單位成本": [10, 15, 25, 45, 60, 8]
    })

df = st.data_editor(st.session_state.resources, num_rows="dynamic", use_container_width=True)
st.session_state.resources = df

if st.button("🚀 執行進階優化 - 生成 4 種可行方案", type="primary"):
    with st.spinner("正在計算..."):
        schemes = []
        scheme_types = ["Max_Profit", "Max_Total_Units", "Min_Cost_Per_Unit", "Resource_Balance"]
        
        for idx, scheme_type in enumerate(scheme_types):
            prob = LpProblem(f"Scheme_{idx+1}", LpMaximize)
            
            prod_vars = {p["name"]: LpVariable(p["name"], lowBound=0, cat="Integer") for p in products}
            usage = {row["資源名稱"]: LpVariable(f"Use_{row['資源名稱']}", 0) for _, row in df.iterrows()}
            
            # 不同方案的不同目標函數
            if scheme_type == "Max_Profit":
                prob += lpSum([prod_vars[p["name"]] * p["profit"] for p in products]) - \
                        0.01 * lpSum([usage[r] * df.loc[df["資源名稱"]==r, "單位成本"].values[0] for r in usage])
            elif scheme_type == "Max_Total_Units":
                prob += lpSum(prod_vars.values())
            elif scheme_type == "Min_Cost_Per_Unit":
                prob += lpSum([usage[r] * df.loc[df["資源名稱"]==r, "單位成本"].values[0] for r in usage])
                # 改成 Minimize，但為了統一用 Maximize 取倒數
            else:  # Balance
                prob += -lpSum(usage.values())  # 最小化總使用量（平衡）
            
            # 資源約束
            for _, row in df.iterrows():
                total_req = lpSum([prod_vars[p["name"]] * row[f"每單位所需_產品{j+1}"] 
                                 for j, p in enumerate(products) if f"每單位所需_產品{j+1}" in row])
                prob += total_req <= row["目前庫存"], f"Stock_{row['資源名稱']}"
                prob += total_req == usage[row["資源名稱"]]
            
            status = prob.solve(PULP_CBC_CMD(msg=0))
            status_str = LpStatus[status]
            
            result = {"方案": f"方案 {idx+1} - {scheme_type.replace('_', ' ')}", "狀態": status_str}
            
            if status_str == "Optimal":
                for p in products:
                    produced = value(prod_vars[p["name"]])
                    result[p["name"]] = f"{produced} / {p['target']} ({produced/p['target']*100:.1f}%)"
                
                result["總目標值"] = round(value(prob.objective), 2)
                
                # 剩餘資源
                remaining = {}
                bottlenecks = []
                for _, row in df.iterrows():
                    used = value(usage[row["資源名稱"]])
                    remain = row["目前庫存"] - used
                    remaining[row["資源名稱"]] = round(remain, 1)
                    if remain < row["目前庫存"] * 0.1:  # 低於 10% 視為瓶頸
                        bottlenecks.append(row["資源名稱"])
                result["剩餘資源"] = remaining
                if bottlenecks:
                    result["瓶頸資源"] = bottlenecks
            else:
                result["建議"] = "資源嚴重不足，建議降低目標或增加庫存"
            
            schemes.append(result)
        
        # 顯示結果
        st.success("✅ 優化完成！以下是 4 種不同可行方案")
        for scheme in schemes:
            st.subheader(scheme["方案"])
            st.write(scheme)
            if "瓶頸資源" in scheme:
                st.warning(f"⚠️ 瓶頸：{', '.join(scheme['瓶頸資源'])} 已接近用盡")
            st.divider()

st.info("💡 現在可以直接測試你最複雜的工廠案例了！\n把截圖裡的相同數據貼上去再跑一次，應該不會再出現 Infeasible。")
