"""
core/features.py
----------------
THE one place that describes the seven measurements: key, names (English and Marathi), unit, allowed input range.
Everything else (input validation, chart axes, page labels, translations, the API later) reads from here, so a name
or a range is changed once.

N, P and K have NO unit on purpose: the dataset does not state one (Kaggle only calls them "ratios"), so kg/ha is not
claimed until the source is confirmed.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    key: str            # column name in the dataset
    label: str          # "Nitrogen (N)"
    label_mr: str       # Marathi label (draft: to be reviewed by farmers)
    name: str           # short plain name: "N", "pH", "Temperature"
    unit: str           # "", "°C", "%", "mm"
    lo: float           # smallest allowed input
    hi: float           # largest allowed input

    @property
    def label_unit(self) -> str:
        """'Temperature (°C)'; N, P and K have no unit: 'Nitrogen (N)'."""
        return f"{self.label} ({self.unit})" if self.unit else self.label

    @property
    def axis(self) -> str:
        """Axis title: 'N', 'pH', 'Temperature (°C)'."""
        return f"{self.name} ({self.unit})" if self.unit else self.name


FEATURE_LIST = [
    Feature("N", "Nitrogen (N)", "नायट्रोजन (N)", "N", "", 0, 140),
    Feature("P", "Phosphorus (P)", "स्फुरद (P)", "P", "", 5, 145),
    Feature("K", "Potassium (K)", "पालाश (K)", "K", "", 5, 205),
    Feature("temperature", "Temperature", "तापमान", "Temperature", "°C", 8.0, 44.0),
    Feature("humidity", "Humidity", "आर्द्रता", "Humidity", "%", 14.0, 100.0),
    Feature("ph", "pH", "सामू (pH)", "pH", "", 3.5, 10.0),
    Feature("rainfall", "Rainfall", "पाऊस", "Rainfall", "mm", 20.0, 300.0),
]
FEATURES_BY_KEY = {f.key: f for f in FEATURE_LIST}

# Ready-made lookups, so a page can write LABEL_UNIT[key] instead of keeping its own dict.
LABEL = {f.key: f.label for f in FEATURE_LIST}
LABEL_UNIT = {f.key: f.label_unit for f in FEATURE_LIST}
NAME = {f.key: f.name for f in FEATURE_LIST}
AXIS = {f.key: f.axis for f in FEATURE_LIST}
