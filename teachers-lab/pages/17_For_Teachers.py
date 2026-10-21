"""
pages/17_For_Teachers.py
------------------------
For teachers: where each data mining algorithm of the project lives and what the farmer pages use it for,
with a link to every technical page and the model evaluation numbers (computed, with the split stated).
"""
import pandas as pd
import streamlit as st

from utils.farm_ui import safe_link, top_bar
from utils.i18n import t
from core.models import benchmark_miners, model_scores, train_id3, train_naive_bayes
from utils.style import ALGO, apply_style, show_table

apply_style()
top_bar(t("nav_teachers"), t("teachers_sub"))

# (page file, title, algorithm, accent, what the farmer sees, what to look for here)
PAGES = [
    ("pages/3_Crop_Advisor.py", "Crop Advisor", "ID3 decision tree", ALGO["id3"],
     "Home: 'What matters most' (information gain)", "Entropy, information gain, the decision path for one assessment."),
    ("pages/8_Model_Council.py", "Model Council", "Gaussian Naive Bayes", ALGO["naive_bayes"],
     "Home and What should I grow?: the recommended crop and its probability", "Priors, per-crop bell curves, the Bayes formula with your numbers."),
    ("pages/6_Cluster_Explorer.py", "Cluster Explorer", "K-Means + PCA", ALGO["kmeans"],
     "Home: 'Farms like yours'", "k-means++ start, elbow and silhouette, PCA map."),
    ("pages/10_Hierarchical.py", "Hierarchical", "Agglomerative + DIANA", ALGO["hierarchical"],
     "Home (technical insights): 'Crops that are alike'", "Four linkages, dendrogram, cophenetic correlation, divisive splits."),
    ("pages/5_Pattern_Mining.py", "Pattern Mining", "Apriori", ALGO["apriori"],
     "Home: 'Patterns found'", "Support, confidence and lift; rules that end in a crop."),
    ("pages/11_FP-Growth_and_Eclat.py", "FP-Growth and Eclat", "FP-Growth, Eclat", ALGO["fpgrowth"],
     "Home (technical insights): 'Itemset miners'", "Same itemsets from three miners; measured run times; closed and maximal sets."),
    ("pages/9_Water_Lab.py", "Water Lab", "Linear regression", ALGO["regression"],
     "Not on Home", "Simple and multiple regression, residuals, held-out R-squared."),
    ("pages/7_Data_Insights.py", "Data Insights", "OLAP star schema", ALGO["olap"],
     "Not on Home", "Slice, dice, roll-up and drill-down over the SQLite warehouse."),
    ("pages/12_Data_Lake.py", "Data Lake", "Raw / curated / warehouse", ALGO["lake"],
     "Not on Home", "ETL from the curated file, catalog.json with hashes."),
    ("pages/13_Data_Prep.py", "Data Prep", "Preprocessing", ALGO["prep"],
     "Not on Home", "Statistics, IQR outliers, scaling, binning, PCA reduction."),
    ("pages/4_What-if_Lab.py", "What-if Lab", "ID3 + K-Means", ALGO["whatif"],
     "Not on Home", "Change the readings and compare predictions before and after."),
    ("pages/2_Soil_Analysis.py", "Soil Analysis", "Percentile categories", ALGO["soil"],
     "New Soil Check", "Low / medium / high = bottom, middle and top third of the data."),
]

st.subheader("Algorithms and where to find them")
for row in range(0, len(PAGES), 3):
    cols = st.columns(3)
    for col, (page, title, algo, color, farmer, look) in zip(cols, PAGES[row:row + 3]):
        with col:
            st.markdown(f'<div class="hub-card"><b>{title}</b><span class="hub-algo" style="background:{color}">{algo}</span>'
                        f'<p><b>Farmers see:</b> {farmer}<br><b>Look for:</b> {look}</p></div>', unsafe_allow_html=True)
            safe_link(page, f"Open {title}", ":material/arrow_forward:")

st.subheader("Model evaluation")
nb, id3 = train_naive_bayes(), train_id3()
st.markdown(f"Both classifiers use the **same stratified 80/20 split** (seed 42): trained on {nb['n_train']:,} rows and tested on "
            f"{nb['n_test']:,} rows they never saw. Metric: share of test rows classified correctly (accuracy).")
show_table(model_scores().assign(Accuracy=lambda d: d["Accuracy"]),
           column_config={"Accuracy": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})

st.subheader("Itemset miners (measured on this machine)")
bench = benchmark_miners((0.01,))
show_table(bench.assign(Milliseconds=bench["Seconds"] * 1000)[["Min support", "Algorithm", "Milliseconds", "Itemsets", "Same as Apriori"]],
           column_config={"Milliseconds": st.column_config.NumberColumn(format="%.1f")})
st.caption("Times are the best of three runs when the page was first opened and vary by machine. "
           "All three miners return identical itemsets and counts.")

with st.expander("How the farmer pages use the algorithms"):
    show_table(pd.DataFrame({
        "Farmer feature": ["Best crop", "Top 3 / Plan B ranking", "Crop Doctor status", "Farms like yours", "Patterns found"],
        "Computed by": ["Naive Bayes probability, checked against the ID3 tree", "Profile match score (distance from each crop's average, in units of its spread)",
                        "10th to 90th percentile and min to max of the crop's records", "K-Means groups on all seven readings", "Apriori rules ending in a crop"],
        "Code": ["utils/advice.recommend()", "utils/advice.match_scores()", "utils/advice.soil_health()", "utils/charts.farm_cluster_chart()", "utils/models.crop_rules()"],
    }))
