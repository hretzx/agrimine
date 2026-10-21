# 3-minute demo script (farmer first, then the algorithms)

Start with `python -m api` and open http://127.0.0.1:8000 (the technical lab starts by itself on :8501).
Numbers below come from the real 2,200-row dataset and the sample field N 90, P 42, K 43, 20.9 °C, humidity 82 %, pH 6.5, rainfall 202.9 mm.
Read times and anything not listed here off the screen: they can differ slightly by machine. Use a fresh database (`AGRIMINE_DB=/tmp/demo.db`) to start from "nothing saved".

**0:00 Home, no soil check yet (10 s)**
"This is what a farmer sees first: 2,200 soil records, 22 crops, and a clear next step." Click **New soil check**.

**0:10 New soil check (20 s)**
Enter the sample values and save. "Each value is checked against the range it can really have. The check is saved together with its prediction in one step." You land on Home for that check.

**0:30 Home, one screen (60 s)**
- Hero card: "**Rice**, Naive Bayes probability 99.7 %: the chance of rice among all 22 crops given these seven readings. The ID3 decision tree agrees."
- Top 3 crops: "Match score 60 for rice, 45 for jute, 32 for coffee: how close the field is to each crop's usual conditions."
- Crop Doctor card: "Nitrogen, phosphorus, potassium and pH are all inside the range rice grows in: soil health Good."
- Plan B: "If rice does not work out: jute, coffee, papaya, with what each needs."
- Farms like yours (K-Means groups; the red X is this field), What each crop needs, What matters most (ID3 information gain), Patterns found (Apriori: K high + humidity low → chickpea, confidence 100 %, lift 22).
- Click **मराठी**: "The same page in Marathi." Open it on a phone, or narrow the window: "It works on a phone too."

**1:30 What should I grow? / Crop Doctor / Plan B (30 s)**
**What should I grow?**: all 22 crops ranked, with the reasons; change a reading to try a value (nothing is saved). **Crop Doctor**: choose *Coffee* and show which readings are outside its range, with advice. **Plan B**: choose *Cotton* (a weaker fit) and show the better crops.

**2:00 For teachers (60 s)**
"Every algorithm is shown working, on the same check." Open, in this order:
1. **ID3 decision tree**: the questions it asked (humidity first, then rainfall, then temperature) with their information gain, ending at Rice; 90.2 % held-out accuracy on 440 unseen rows.
2. **Naive Bayes**: the two models agree; Naive Bayes 99.7 % (99.5 % held-out accuracy). The bars show temperature pushing hardest; they add up to the log of the odds (rice is about 356 times more likely than jute); Bayes' formula is worked out with these numbers.
3. **K-Means**: move the slider for k; the map, the group of this field, the elbow and silhouette charts.
4. **Apriori**: move the support and confidence sliders and watch the rules change (821 rules at the defaults); click a column heading to sort.
5. **Hierarchical**: the dendrogram of the 22 crops; switch the linkage; DIANA splits from the top.

**3:00 The technical lab (10 s)**
"Open the technical lab" on For teachers: FP-Growth and Eclat, Data Insights (OLAP star schema), Data Lake, Data Prep, Water Lab (regression) and What-if Lab are here, on the same check.

Say plainly: rules and clusters describe the historical data, not causes; the match score is a similarity score, not a probability or a yield forecast; accuracy numbers are computed on rows the model never saw.
