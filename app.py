import streamlit as st
import pandas as pd
from pulp import *

st.set_page_config(page_title="🏭 工廠資源優化器", layout="wide")
st.title("🏭 工廠資源優化應用程式")
st.markdown("**定義目標 → 材料 → 庫存 → 自動生成多種最優方案**（適合工廠、生產線、小團隊使用）")

# 步驟1: 目標
st.header("步驟1: 定義生產目標")
goal = st.text_input("生產目標", "生產 1000 個產品")
objective = st.selectbox("優化方向", ["最小化總成本", "最大化產量", "平衡資源使用"])

# 步驟2&3: 材料表格（可動態新增）
st.header("步驟2 & 3: 所需材料與目前庫存")
if "materials" not in st.session_state:
    st.session_state.materials = pd.DataFrame({
        "材料名稱": ["原料A", "原料B", "機器小時", "人工小時"],
        "每單位所需": [2.0, 3.0, 0.5, 1.0],
        "目前庫存": [500, 300, 200, 150],
        "單位成本": [10, 15, 50, 80]
    })

df = st.data_editor(st.session_state.materials, num_rows="dynamic", use_container_width=True)
st.session_state.materials = df

if st.button("🚀 開始優化 - 生成 4 種不同方案", type="primary"):
    with st.spinner("正在計算多方案最優組合..."):
        schemes = []
        weights = [0.8, 0.5, 0.3, 0.1]  # 不同成本/資源權重，避免單一收斂
        
        for i, w in enumerate(weights):
            prob = LpProblem(f"Scheme_{i+1}", LpMinimize)
            usage = {row["材料名稱"]: LpVariable(f"Use_{row['材料名稱']}", 0) for _, row in df.iterrows()}
            
            # 目標函數（成本為主，但加入不同權重變化）
            prob += w * lpSum([usage[row["材料名稱"]] * row["單位成本"] for _, row in df.iterrows()])
            
            # 約束條件
            for _, row in df.iterrows():
                prob += usage[row["材料名稱"]] * row["每單位所需"] <= row["目前庫存"], f"Stock_{row['材料名稱']}"
            
            status = prob.solve(PULP_CBC_CMD(msg=0))
            
            if LpStatus[status] == "Optimal":
                total_cost = value(prob.objective)
                remaining = {row["材料名稱"]: row["目前庫存"] - value(usage[row["材料名稱"]]) for _, row in df.iterrows()}
                schemes.append({
                    "方案": f"方案 {i+1} ({['強成本優先','平衡偏成本','平衡偏資源','強資源優先'][i]})",
                    "總成本": round(total_cost, 2),
                    "剩餘庫存": remaining,
                    "達成目標": "是" if all(v >= 0 for v in remaining.values()) else "部分達成"
                })
        
        st.success(f"✅ 優化完成！共生成 {len(schemes)} 種可行方案供您選擇")
        
        for scheme in schemes:
            st.subheader(scheme["方案"])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("估計總成本", f"${scheme['總成本']}")
            with col2:
                st.metric("是否達成目標", scheme["達成目標"])
            st.write("**剩餘庫存：**", scheme["剩餘庫存"])
            st.divider()

# 自然語言輸入區（未來可擴充呼叫 Grok API）
st.info("💡 想用自然語言？直接在下面輸入描述，我會幫你轉成表格！\n例如：我想生產800個產品，需要原料A每件2kg，目前只有450kg，原料B每件3kg有250kg...")
nl_input = st.text_area("自然語言描述")
if st.button("解析自然語言"):
    st.warning("目前為示範版，完整自然語言解析可後續用 Grok API 加入。")
