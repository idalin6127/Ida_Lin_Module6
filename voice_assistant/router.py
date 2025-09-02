# router.py — Enhanced version: Robust JSON extraction + Weather rules
import json, re
from typing import Optional
from tools import ToolResult, calculate, get_weather, search_arxiv


# Convert English/Chinese spoken math words to symbols and clean up extra characters
def text_to_math_expr(q: str) -> str:
    s = q.lower()

            # Replace multi-word phrases first (longer ones first)
    replacements = [
        ("open parenthesis", "("),
        ("close parenthesis", ")"),
        ("open bracket", "("),
        ("close bracket", ")"),
        ("to the power of", "**"),
        ("raised to the power of", "**"),
        ("multiplied by", "*"),
        ("times", "*"),
        ("divide by", "/"),
        ("divided by", "/"),
        ("all over", "/"),
        ("over", "/"),

        # Common Chinese expressions
        ("加上", "+"), ("加", "+"),
        ("减去", "-"), ("减", "-"),
        ("乘以", "*"), ("乘", "*"),
        ("除以", "/"), ("除", "/"),
    ]

    # Single word replacements
    single_words = [
        ("plus", "+"),
        ("minus", "-"),
        ("mod", "%"),
        ("modulo", "%"),
        ("squared", "**2"),
        ("cubed", "**3"),
    ]

    noise = [
        "what is", "what's", "whats", "result", "equals", "calculate", "compute",
        "请问", "等于多少", "结果是多少", "计算一下", "帮我算"
    ]

    for k, v in replacements:
        s = re.sub(r"\b" + re.escape(k) + r"\b", v, s)

    for k, v in single_words:
        s = re.sub(r"\b" + re.escape(k) + r"\b", v, s)

    for k in noise:
        s = re.sub(r"\b" + re.escape(k) + r"\b", " ", s)

    # Keep only numbers, decimals, operators and parentheses
    s = re.sub(r"[^0-9\.\+\-\*\/\%\(\)\s]", " ", s)
    # Merge extra spaces and remove spaces
    s = re.sub(r"\s+", "", s)

    # Final cleanup: merge duplicate operators
    s = re.sub(r"\+{2,}", "+", s)
    s = re.sub(r"-{2,}", "-", s)
    s = re.sub(r"/{2,}", "/", s)
    s = s.replace("**+", "**")
    return s


# ---------- 1) Extract {"function":...} from any text ----------
def _extract_json_call(text: str) -> Optional[dict]:
    s = text.strip()

    # 1) Try to parse the entire text directly
    try:
        obj = json.loads(s)
        if isinstance(obj, dict) and "function" in obj:
            return obj
    except Exception:
        pass

    # 2) Try to extract from triple backtick code blocks ```json {...} ```
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.S | re.I):
        block = m.group(1).strip()
        try:
            obj = json.loads(block)
            if isinstance(obj, dict) and "function" in obj:
                return obj
        except Exception:
            continue

    # 3) Search for JSON starting with {"function" in the entire text and do bracket matching
    idx = s.find('{"function"')
    if idx != -1:
        depth = 0
        for j in range(idx, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    chunk = s[idx:j+1]
                    try:
                        obj = json.loads(chunk)
                        if isinstance(obj, dict) and "function" in obj:
                            return obj
                    except Exception:
                        break
    return None

def try_route_llm_function_call(llm_output: str) -> Optional[str]:
    obj = _extract_json_call(llm_output)
    if not obj:
        return None

        # ✅ Alias mapping: model can match even if names are wrong
    ALIASES = {
        "recent_papers": "search_arxiv",
        "search_papers": "search_arxiv",
        "find_papers": "search_arxiv",
        "arxiv_search": "search_arxiv",
    }

    func = obj.get("function")
    func = ALIASES.get(func, func)     # Normalize
    args = obj.get("arguments", {}) or {}

    try:
        if func == "get_weather":
            r: ToolResult = get_weather(args.get("location", ""))
            return r.content if r.ok else f"Error from get_weather: {r.content}"

        if func == "calculate":
            r = calculate(args.get("expression", ""))
            return r.content if r.ok else f"Error from calculate: {r.content}"

        if func == "search_arxiv":
            r = search_arxiv(args.get("query", ""))
            return r.content if r.ok else f"Error from search_arxiv: {r.content}"


        return f"Error: Unknown function '{func}'"
    except Exception as e:
        return f"Error: Could not process function call. Details: {e}"

# ---------- 2) Rule fallback ----------
_math_re = re.compile(r"^[\s\d\.\+\-\*\/\^\(\)]+$")

MATH_TRIGGERS = [
    # 英文
    "equals", "what is", "what's", "result", "compute", "calculate",
    "how much is", "evaluate", "mod", "modulo", "remainder",
    "to the power of", "power", "squared", "cubed",
    # 中文
    "等于多少", "结果是多少", "计算", "帮我算", "取余", "余数"
]

def maybe_call_by_rules(user_text: str) -> Optional[str]:
    q = user_text.strip()
    ql = q.lower()

    # First try to convert spoken language -> math expression
    expr = text_to_math_expr(q)

    # If we can extract an expression and it contains one or more operators, call calculate
    if expr and re.search(r'(\*\*|[\+\-\*\/\%\^])', expr):
        r = calculate(expr)
        return r.content if r.ok else f"Error from calculate: {r.content}"

    # Weather: priority over arXiv
    if any(w in ql for w in [
        "weather","forecast","temperature",
        "下雨","天气","气温","预报"
    ]):
        # Simple city extraction: weather in/at/for <city>
        m = re.search(r"weather\s+(?:in|at|for)\s+([a-zA-Z\s,]+)", ql)
        city = m.group(1).strip() if m else ""
        # Clean city name, remove time words and extra descriptions
        city = re.sub(r'\b(today|tomorrow|now|tonight|morning|afternoon|evening|night)\b', '', city, flags=re.IGNORECASE).strip()
        city = re.sub(r'\s+', ' ', city).strip()
        r = get_weather(city)
        return r.content if r.ok else f"Error from get_weather: {r.content}"

    # arXiv: English/Chinese keywords
    if any(w in ql for w in [
        "arxiv","paper","papers","literature","recent research","latest research",
        "论文","检索","文献","最近研究"
    ]):
        r = search_arxiv(q)
        return r.content if r.ok else f"Error from search_arxiv: {r.content}"

    # No rules matched → return None
    return None
