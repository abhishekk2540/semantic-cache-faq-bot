import re

NEGATION_WORDS = {
    "not", "no", "never", "without", "cannot",
    "nahi", "nahin", "nhi", "nai", "mat",
}


def _words(text):
    text = text.lower().replace("n't", " not")  # "can't" -> "ca not"
    return set(re.findall(r"\w+", text))


def has_negation(text):
    return len(_words(text) & NEGATION_WORDS) > 0


def negation_mismatch(a, b):
    """True when exactly one of the two sentences has a negation word."""
    return has_negation(a) != has_negation(b)


# 6+ digits in a row (order id, phone), an email, or "my name is ..." style intros
PII_PATTERN = re.compile(
    r"\d{6,}|[\w.+-]+@[\w-]+\.\w+|\bmy name is\b|\bmera naam\b",
    re.IGNORECASE,
)


def contains_pii(text):
    return bool(PII_PATTERN.search(text))
