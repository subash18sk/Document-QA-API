"""Shared text helpers: tokenising, light stemming and sentence splitting."""
import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?:])\s+(?=[A-Z0-9\"'(])")

# Function words and question words carry no meaning for matching ("how many days do I get").
STOPWORDS = frozenset(
    """a about above after again all also am an and any are as at be because been before being below
    between both but by can could did do does doing done during each either for from further get gets
    got had has have having he her here hers him his how i if in into is it its itself just let may me
    might more most much must my no nor not of off on once only or other our ours out over own per
    please same shall she should so some such than that the their them then there these they this those
    through to too under until up upon us very via was we were what when where which while who whom
    whose why will with within without would you your yours many tell know""".split()
)


def stem(token: str) -> str:
    """Light suffix stripper so word forms match: leave/leaves, reimburse/reimbursed/reimburses,
    employee/employees, work/working, policy/policies. Not linguistically perfect — it only has to
    map related forms to the same key."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    while len(token) > 4 and token.endswith("e"):   # employee/employe -> employ
        token = token[:-1]
    return token


def is_heading(sentence: str) -> bool:
    return sentence.endswith(":")


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.split(text.replace("\n", " ")) if s.strip()]
