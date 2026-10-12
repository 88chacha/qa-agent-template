"""라우팅 분류와, 분류마다 근거로 쓸 문서.

분류 하나가 FAQ·정책 문서 하나에 대응한다. 문서를 늘리거나 분류를 바꿀 때는 이 표만 고치면 된다.
"""

ROUTES = {
    "SHIPPING": {"label": "배송", "doc": "01_shipping", "desc": "배송 기간, 배송비, 배송 조회, 제주·도서산간 배송"},
    "RETURN_EXCHANGE": {"label": "교환·반품", "doc": "02_return_exchange", "desc": "교환·반품 신청 기간과 방법, 반품 배송비, 반품이 안 되는 경우"},
    "REFUND": {"label": "환불", "doc": "03_refund", "desc": "환불 시점, 결제 수단별 환불 반영 기간 같은 환불 정책 안내"},
    "CANCEL": {"label": "주문 취소", "doc": "04_cancel", "desc": "출발 전 주문 취소, 배송 중 취소, 예약 상품 취소"},
    "POINTS": {"label": "적립금·등급", "doc": "05_points", "desc": "적립률, 적립금 사용과 유효 기간, 회원 등급"},
    "PAYMENT": {"label": "결제", "doc": "06_payment", "desc": "결제 수단, 무통장 입금 기한, 할부, 결제 수단 변경"},
    "WARRANTY": {"label": "보증·A/S", "doc": "07_warranty", "desc": "제품 고장과 불량, 무상 수리, A/S"},
    "ACCOUNT": {"label": "계정·개인정보", "doc": "08_account", "desc": "비밀번호, 회원 정보와 배송지 변경, 탈퇴, 개인정보 요청"},
}

# 문서로 답하지 않는 분류
SPECIAL = {
    "ESCALATE": {"label": "담당자 검토", "desc": "환불을 지금 확정해 달라는 요구, 법적 대응 언급, 건강·안전 피해 언급처럼 사람이 직접 판단해야 하는 문의"},
    "OTHER": {"label": "범위 밖", "desc": "위 분류 어디에도 속하지 않는 문의(매장, 입점, 채용 등)"},
}


def label(route_id):
    return (ROUTES.get(route_id) or SPECIAL.get(route_id) or {"label": route_id})["label"]
