"""
core/crops.py
-------------
THE one place that describes the 22 crops: key (as in the dataset), English name, Marathi farmer name, family.
Display code (style.py, i18n.py, the API later) reads from here. Emojis and drawings are UI and live elsewhere.

label_mr is the name farmers say for the FIELD crop (भात for rice, not तांदूळ the grain).
DRAFT: written by the developer, to be reviewed by farmers before release.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Crop:
    key: str
    label: str
    label_mr: str
    family: str


CROP_LIST = [
    Crop("rice", "Rice", "भात", "Cereals"), Crop("maize", "Maize", "मका", "Cereals"),
    Crop("chickpea", "Chickpea", "हरभरा", "Pulses"), Crop("kidneybeans", "Kidney Beans", "राजमा", "Pulses"),
    Crop("pigeonpeas", "Pigeon Peas", "तूर", "Pulses"), Crop("mothbeans", "Moth Beans", "मटकी", "Pulses"),
    Crop("mungbean", "Mung Bean", "मूग", "Pulses"), Crop("blackgram", "Black Gram", "उडीद", "Pulses"),
    Crop("lentil", "Lentil", "मसूर", "Pulses"),
    Crop("pomegranate", "Pomegranate", "डाळिंब", "Fruits"), Crop("banana", "Banana", "केळी", "Fruits"),
    Crop("mango", "Mango", "आंबा", "Fruits"), Crop("grapes", "Grapes", "द्राक्षे", "Fruits"),
    Crop("watermelon", "Watermelon", "कलिंगड", "Fruits"), Crop("muskmelon", "Muskmelon", "खरबूज", "Fruits"),
    Crop("apple", "Apple", "सफरचंद", "Fruits"), Crop("orange", "Orange", "संत्री", "Fruits"),
    Crop("papaya", "Papaya", "पपई", "Fruits"), Crop("coconut", "Coconut", "नारळ", "Fruits"),
    Crop("cotton", "Cotton", "कापूस", "Fibre & cash crops"), Crop("jute", "Jute", "ताग", "Fibre & cash crops"),
    Crop("coffee", "Coffee", "कॉफी", "Fibre & cash crops"),
]
CROPS_BY_KEY = {c.key: c for c in CROP_LIST}
FAMILIES = list(dict.fromkeys(c.family for c in CROP_LIST))      # in the order above

# Crop families (used to colour charts and shown in their legends): key -> (English, Marathi). Marathi: draft, farmers review.
FAMILY_LABELS = {
    "Cereals": ("Cereals", "तृणधान्ये"),
    "Pulses": ("Pulses", "कडधान्ये"),
    "Fruits": ("Fruits", "फळे"),
    "Fibre & cash crops": ("Fibre & cash crops", "तंतू व नगदी पिके"),
}
