"""
utils/i18n.py
-------------
English / Marathi text for the farmer-facing pages (navigation, headings, buttons, status labels).

    t("nav_home")            -> "Home"  or  "मुख्यपृष्ठ"   (depends on the language chosen in the header)
    t("greeting_morning")    -> ...

How it works: the header toggle (see utils/farm.top_bar) stores "en" or "mr" in st.session_state, which
survives page changes. Units (mm, °C) and the technical pages are NOT translated. Crop names ARE: crop_name() gives the Marathi farmer name (CROP_MR, draft, to be reviewed by farmers).
To add a word: add one row to TEXT with both languages. A missing Marathi entry falls back to English.
The Marathi wording should be checked by a Marathi speaker before it is shown to farmers.
"""
import streamlit as st

from core.crops import CROP_LIST
from core.features import FEATURE_LIST

LANGS = {"EN": "en", "मराठी": "mr"}
LANG_KEY = "lang"             # the language in use ("en" or "mr"), kept across pages
CHOICE_KEY = "lang_choice"    # the header toggle widget

TEXT = {
    # navigation
    "nav_home": ("Home", "मुख्यपृष्ठ"),
    "nav_grow": ("What should I grow?", "मी काय पिकवावे?"),
    "nav_doctor": ("Crop Doctor", "पीक डॉक्टर"),
    "nav_planb": ("Plan B", "पर्यायी योजना"),
    "nav_teachers": ("For teachers", "शिक्षकांसाठी"),
    "tagline": ("Better decisions today, greener harvests tomorrow.",
                "आजचे चांगले निर्णय, उद्याची हिरवी कापणी."),
    # header
    "greeting_morning": ("Good morning, Farmer!", "शुभ प्रभात, शेतकरी!"),
    "greeting_afternoon": ("Good afternoon, Farmer!", "शुभ दुपार, शेतकरी!"),
    "greeting_evening": ("Good evening, Farmer!", "शुभ संध्या, शेतकरी!"),
    "home_sub": ("Here's a quick look at your field and the best suggestions for your crops.",
                 "तुमच्या शेताची झलक आणि पिकांसाठी सर्वोत्तम सूचना."),
    "new_check": ("New Soil Check", "नवीन माती तपासणी"),
    "language": ("Language", "भाषा"),
    # summary cards
    "kpi_records": ("Soil records", "माती नोंदी"),
    "kpi_records_note": ("{n} measurements each", "प्रत्येकी {n} मोजमापे"),
    "kpi_crops": ("Crops explored", "अभ्यासलेली पिके"),
    "kpi_crops_note": ("about {n} records per crop", "प्रति पीक सुमारे {n} नोंदी"),
    "kpi_saved": ("Saved assessments", "जतन केलेल्या तपासण्या"),
    "kpi_saved_none": ("none saved yet", "अजून काही जतन नाही"),
    "kpi_saved_last": ("last on {d}", "शेवटची {d}"),
    # cards
    "hero_title": ("Your field, at a glance", "तुमचे शेत, एका नजरेत"),
    "best_crop": ("Best crop", "सर्वोत्तम पीक"),
    "view_details": ("View details", "तपशील पहा"),
    "hero_empty": ("Do a soil check to see the best crop for your field.",
                   "तुमच्या शेतासाठी सर्वोत्तम पीक पाहण्यासाठी माती तपासणी करा."),
    "hero_why": ("Your soil and weather readings are close to what {crop} usually grows in.",
                 "तुमच्या मातीची आणि हवामानाची मोजमापे {crop} साठी नेहमीच्या परिस्थितीच्या जवळ आहेत."),
    "model_prob": ("Naive Bayes probability", "नेव्ह बेज संभाव्यता"),
    "tree_agrees": ("Decision tree agrees", "निर्णय वृक्ष सहमत आहे"),
    "tree_differs": ("Decision tree suggests {crop}", "निर्णय वृक्ष {crop} सुचवतो"),
    "soil_ph": ("Soil pH", "मातीचा सामू (pH)"),
    "temperature": ("Temperature", "तापमान"),
    "rainfall": ("Rainfall", "पाऊस"),
    "humidity": ("Humidity", "आर्द्रता"),
    "top3_title": ("Top 3 crops", "सर्वोत्तम ३ पिके"),
    "top3_sub": ("Closest to your soil and climate", "तुमच्या माती आणि हवामानाला सर्वात जवळची"),
    "match_score": ("Match score", "जुळणी गुण"),
    "doctor_title": ("Crop Doctor", "पीक डॉक्टर"),
    "doctor_sub": ("Soil health at a glance", "मातीचे आरोग्य एका नजरेत"),
    "overall_health": ("Overall soil health", "मातीचे एकूण आरोग्य"),
    "planb_title": ("Plan B – Backup crops", "पर्यायी योजना – पर्यायी पिके"),
    "planb_sub": ("If your main crop doesn't work out", "मुख्य पीक जमले नाही तर"),
    "farms_title": ("Farms like yours", "तुमच्यासारखी शेती"),
    "farms_sub": ("Groups of similar soil and weather conditions", "सारख्या माती आणि हवामानाचे गट"),
    "your_field": ("Your field", "तुमचे शेत"),
    "needs_title": ("What each crop needs", "प्रत्येक पिकाला काय हवे"),
    "needs_sub": ("Rainfall and temperature each crop grows in", "प्रत्येक पिक कोणत्या पाऊस व तापमानात येते"),
    "needs_help": ("Find your rainfall and temperature on the axes: crops near that spot grow in similar conditions.",
                   "अक्षांवर तुमचा पाऊस आणि तापमान शोधा: त्या जागेजवळची पिके तशाच परिस्थितीत येतात."),
    "tech_title": ("Technical insights", "तांत्रिक माहिती"),
    "tech_sub": ("The mining algorithms behind these suggestions", "या सूचनांमागील डेटा-खनन पद्धती"),
    "recent_title": ("Recent assessments", "अलीकडील तपासण्या"),
    # status words
    "good": ("Good", "चांगले"),
    "moderate": ("Moderate", "मध्यम"),
    "attention": ("Needs attention", "लक्ष द्यावे"),
    "strong": ("Strong match", "उत्तम जुळणी"),
    "hero_sub": ("Based on your latest soil check", "तुमच्या ताज्या माती तपासणीवर आधारित"),
    "req_title": ("Crop requirements summary", "पीक गरजांचा सारांश"),
    "req_sub": ("Key conditions for your top crop ({crop})", "तुमच्या सर्वोत्तम पिकासाठी ({crop}) प्रमुख अटी"),
    "ideal": ("Ideal", "योग्य"),
    "check": ("Check", "तपासा"),
    "gain_title": ("What matters most", "सर्वात महत्त्वाचे काय"),
    "gain_sub": ("{f} splits the crops best", "{f} पिके सर्वोत्तम वेगळी करते"),
    "pat_title": ("Patterns found", "आढळलेले नमुने"),
    "pat_sub": ("{n} crop combinations in the data", "डेटामधील {n} पीक संयोजने"),
    "best_choice": ("Best choice", "सर्वोत्तम निवड"),
    "details": ("Details", "तपशील"),
    "most_often": ("most often", "बहुधा"),
    "tech_note_sample": ("a sample record", "नमुना नोंद"),
    "fair": ("Fair", "बरे"),
    "consider": ("Consider", "विचार करा"),
    "pending": ("Pending", "प्रलंबित"),
    "predicted": ("Predicted", "अंदाज झाला"),
    "saved_only": ("Saved, not predicted yet", "जतन केले, अंदाज बाकी"),
    # features
    # detail pages
    "grow_sub": ("Enter your soil and weather readings to see which crops suit your field and why.",
                 "तुमच्या मातीची आणि हवामानाची मोजमापे भरा आणि कोणती पिके तुमच्या शेताला योग्य आहेत ते पहा."),
    "doctor_page_sub": ("Check each soil and weather reading against what your chosen crop usually grows in.",
                        "तुमच्या निवडलेल्या पिकाला नेहमी लागणाऱ्या परिस्थितीशी प्रत्येक मोजमापाची तुलना करा."),
    "planb_page_sub": ("If your preferred crop is a poor fit, see which crops suit your field better.",
                       "तुमचे आवडते पीक योग्य नसेल तर तुमच्या शेताला कोणती पिके जास्त योग्य आहेत ते पहा."),
    "teachers_sub": ("The data mining algorithms behind AgriMine, with a link to each technical page.",
                     "AgriMine मागील डेटा-खनन पद्धती आणि प्रत्येक तांत्रिक पानाचा दुवा."),
    "your_readings": ("Your readings", "तुमची मोजमापे"),
    "preferred_crop": ("Crop you want to grow", "तुम्हाला पिकवायचे पीक"),
    "measured": ("Your value", "तुमचे मूल्य"),
    "recommended": ("Usual range for {crop}", "{crop} साठी नेहमीची श्रेणी"),
    "status": ("Status", "स्थिती"),
    "what_to_do": ("What you can do", "तुम्ही काय करू शकता"),
    "all_ok": ("Every reading is in the usual range for {crop}.", "प्रत्येक मोजमाप {crop} साठी नेहमीच्या श्रेणीत आहे."),
    "nutrients": ("Soil nutrients and pH", "मातीतील अन्नद्रव्ये आणि सामू"),
    "climate": ("Weather", "हवामान"),
    "ranking_title": ("All crops, ranked", "सर्व पिके, क्रमवारीनुसार"),
    "why_title": ("Why {crop}?", "{crop} का?"),
    "compare_title": ("Compare crops side by side", "पिकांची तुलना"),
    "pref_ok": ("{crop} looks suitable for your field.", "{crop} तुमच्या शेतासाठी योग्य दिसते."),
    "pref_poor": ("{crop} is a weaker fit for your field. These crops match your conditions better:",
                  "{crop} तुमच्या शेतासाठी कमी योग्य आहे. ही पिके तुमच्या परिस्थितीशी जास्त जुळतात:"),
    "pref_mid": ("{crop} is a fair fit. These crops match a little better:", "{crop} बरे जुळते. ही पिके थोडी अधिक जुळतात:"),
    "alt_needs": ("What it needs", "त्याला काय हवे"),
    "how_decided": ("How is this decided?", "हे कसे ठरते?"),
    # page-level
    "open_page": ("Open full page", "पूर्ण पान उघडा"),
    "no_check": ("No soil check yet", "अजून माती तपासणी नाही"),
}


# Crop names as farmers say them in Marathi (the field-crop name, e.g. भात for rice, not तांदूळ the grain).
# DRAFT: written by the developer, to be reviewed by farmers before release.
CROP_MR = {c.key: c.label_mr for c in CROP_LIST}   # from core/crops.py (draft, farmers review)


TEXT.update({f"f_{f.key}": (f.label, f.label_mr) for f in FEATURE_LIST})   # feature labels: core/features.py


def get_lang() -> str:
    """The language in use: "en" or "mr". Reads the header toggle first, then the saved choice."""
    choice = LANGS.get(st.session_state.get(CHOICE_KEY))
    if choice:
        st.session_state[LANG_KEY] = choice
    return st.session_state.get(LANG_KEY, "en")


def t(key: str, **fmt) -> str:
    """Text for `key` in the current language; {placeholders} are filled from fmt."""
    en, mr = TEXT[key]
    text = mr if get_lang() == "mr" and mr else en
    return text.format(**fmt) if fmt else text


def crop_name(crop) -> str:
    """Display name of a crop in the language in use (English title or the Marathi farmer name); data keys stay English."""
    from utils.style import crop_title   # local import: style.py does not depend on i18n
    return CROP_MR.get(str(crop), crop_title(crop)) if get_lang() == "mr" else crop_title(crop)
