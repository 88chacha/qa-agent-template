"""문의를 분류하는 라우터.

1. 모델이 문의를 읽고 분류를 1~3개 고른다. 확신도(0~1)와 이유를 함께 낸다.
2. 안전장치: 고위험 표현이 있으면 모델 판단과 상관없이 담당자 검토로 넘긴다(코드 규칙).
3. 안전장치: 확신도가 기준보다 낮으면 초안을 만들지 않고 담당자에게 넘긴다.
fake 모드처럼 모델을 쓰지 않을 때는 키워드 규칙 라우터가 같은 형식으로 답한다.
"""
from dataclasses import dataclass, field

from app.logs import log
from app.routes import ROUTES, SPECIAL

CONFIDENCE_THRESHOLD = 0.6

ESCALATION_RULES = [
    ("환불 확정 요청", ["환불해 주세요", "환불해주세요", "환불 처리해", "돈 돌려", "환불 확정", "당장 환불"]),
    ("법적 대응 언급", ["소송", "고소", "법적", "변호사", "소비자원", "신고하겠"]),
    ("건강 피해 언급", ["병원", "알레르기", "다쳤", "부작용", "화상"]),
]

KEYWORDS = {
    "SHIPPING": ["배송비가", "도착", "송장", "배송 조회", "제주", "도서산간", "얼마나 걸"],
    "RETURN_EXCHANGE": ["반품", "교환", "사이즈", "색상", "태그"],
    "REFUND": ["환불", "환불은 언제", "언제 환불", "환불이 아직"],
    "CANCEL": ["취소"],
    "POINTS": ["적립", "VIP", "등급"],
    "PAYMENT": ["결제", "입금", "할부", "계좌이체"],
    "WARRANTY": ["고장", "수리", "A/S", "불량", "안 켜", "지퍼", "보증"],
    "ACCOUNT": ["비밀번호", "탈퇴", "배송지", "회원 정보", "개인정보"],
}

ROUTER_PROMPT = "\n".join([
    "너는 온라인 쇼핑몰 '하루마켓'의 고객 문의를 분류하는 라우터다.",
    "고를 수 있는 분류:",
    *[f"- {k}: {v['desc']}" for k, v in ROUTES.items()],
    *[f"- {k}: {v['desc']}" for k, v in SPECIAL.items()],
    "",
    "규칙:",
    "- routes 에는 문의에 답하는 데 필요한 분류를 중요한 순서로 1~3개 넣는다. 꼭 필요한 분류만 넣는다.",
    "- ESCALATE 나 OTHER 에 해당하면 그 분류 하나만 넣는다.",
    "- confidence 는 분류가 맞을 확신을 0과 1 사이 숫자로 쓴다.",
    "- reason 은 그 분류를 고른 이유를 한국어 한 문장으로 쓴다.",
    '- 반드시 JSON 하나로만 답한다: {"routes": ["..."], "confidence": 0.0, "reason": "..."}',
])


@dataclass
class RouteResult:
    routes: list
    confidence: float
    reason: str
    decided_by: str                      # model, rule
    action: str = "answer"               # answer, escalate, out_of_scope
    action_reason: str | None = None
    guards: list = field(default_factory=list)   # 작동한 안전장치 설명


def escalation_rule(question):
    for reason, keywords in ESCALATION_RULES:
        if any(k in question for k in keywords):
            return reason
    return None


def rule_route(question):
    """모델 없이 키워드로 고른다. fake 모드와, 모델 호출이 실패했을 때 쓴다."""
    scores = {r: sum(question.count(k) for k in ks) for r, ks in KEYWORDS.items()}
    hits = [r for r, s in sorted(scores.items(), key=lambda x: x[1], reverse=True) if s > 0][:2]
    if not hits:
        return RouteResult(["OTHER"], 0.5, "어느 분류의 키워드에도 해당하지 않습니다.", "rule")
    names = ", ".join(ROUTES[h]["label"] for h in hits)
    return RouteResult(hits, 0.7, f"'{names}' 관련 키워드가 들어 있습니다.", "rule")


def model_route(question, llm):
    data = llm.complete_json(ROUTER_PROMPT, question)
    allowed = set(ROUTES) | set(SPECIAL)
    routes = [r for r in data.get("routes", []) if r in allowed][:3]
    if not routes:
        raise ValueError(f"알 수 없는 분류: {data.get('routes')}")
    if any(r in SPECIAL for r in routes):
        routes = [next(r for r in routes if r in SPECIAL)]
    confidence = max(0.0, min(1.0, float(data.get("confidence", 0))))
    return RouteResult(routes, confidence, str(data.get("reason", "")), "model")


def route(question, llm):
    if getattr(llm, "can_route", False):
        try:
            result = model_route(question, llm)
        except Exception as error:  # 모델 응답이 형식에 맞지 않으면 규칙으로 대신한다
            log("WARNING", "모델 라우팅 실패, 규칙 라우터로 대신함", error=type(error).__name__)
            result = rule_route(question)
            result.guards.append("모델 응답을 읽지 못해 키워드 규칙으로 분류했습니다.")
    else:
        result = rule_route(question)

    # 안전장치 1: 고위험 표현은 모델 판단과 상관없이 담당자 검토
    risk = escalation_rule(question)
    if risk and result.routes != ["ESCALATE"]:
        result.guards.append(f"고위험 표현({risk})이 있어 담당자 검토로 바꿨습니다.")
        result.routes = ["ESCALATE"]
    if result.routes == ["ESCALATE"]:
        result.action, result.action_reason = "escalate", risk or result.reason
    elif result.routes == ["OTHER"]:
        result.action, result.action_reason = "out_of_scope", "준비된 FAQ·정책 문서의 범위 밖입니다."
    # 안전장치 2: 확신이 낮으면 초안을 만들지 않는다
    elif result.confidence < CONFIDENCE_THRESHOLD:
        result.action, result.action_reason = "escalate", f"분류 확신도 {result.confidence:.2f}가 기준 {CONFIDENCE_THRESHOLD} 미만입니다."
        result.guards.append("확신도가 낮아 초안을 만들지 않고 담당자에게 넘겼습니다.")

    log("INFO", "라우팅", routes=result.routes, confidence=round(result.confidence, 2),
        decided_by=result.decided_by, action=result.action)
    return result
