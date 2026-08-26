import re

def detect_language(text):
    marathi_chars = sum(1 for c in text if "\u0900" <= c <= "\u097f")
    total_chars = len([c for c in text if c.isalpha()])

    if total_chars == 0:
        return "english"

    devanagari_percentage = (
        (marathi_chars / total_chars) * 100 if total_chars > 0 else 0
    )

    marathi_words = [
        "आहे",
        "होते",
        "काय",
        "कसे",
        "कोण",
        "कुठे",
        "केव्हा",
        "मला",
        "तुम्हाला",
        "माहिती",
        "सांगा",
        "कृपया",
    ]
    marathi_word_count = sum(1 for word in marathi_words if word in text)

    hindi_words = [
        "है",
        "हैं",
        "था",
        "थे",
        "क्या",
        "कैसे",
        "कौन",
        "कहाँ",
        "कब",
        "मुझे",
        "आपको",
        "बताइए",
        "कृपया",
    ]
    hindi_word_count = sum(1 for word in hindi_words if word in text)

    if devanagari_percentage > 50:
        if marathi_word_count > hindi_word_count:
            return "marathi"
        elif hindi_word_count > marathi_word_count:
            return "hindi"
        else:
            return "marathi"
    elif devanagari_percentage > 10:
        return "mixed"
    else:
        return "english"


def analyze_document_for_fraud(text):
    warnings = []

    dates = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
    if len(set(dates)) > 1:
        warnings.append("⚠️ Multiple different dates found")

    names = re.findall(r"\b[A-Z][a-z]{2,15}\s[A-Z][a-z]{2,15}\b", text)
    for name in names:
        if re.search(r"(.)\1{2,}", name):
            warnings.append(f"⚠️ Suspicious name pattern: '{name}'")

    legal_keywords = ["signature", "seal", "stamp", "authorized", "certified"]
    found_keywords = [kw for kw in legal_keywords if kw.lower() in text.lower()]
    if len(found_keywords) < 2:
        warnings.append("⚠️ Document may be missing official stamps/signatures")

    if text.count("  ") > len(text) / 50:
        warnings.append("⚠️ Unusual spacing detected")

    return warnings
