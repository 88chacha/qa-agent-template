"""문의 하나를 처리하는 흐름: 라우팅 → 근거 문서 선택 → 답변 초안.

1. 라우팅: 모델이 문의를 분류한다. 고위험 문의와 확신이 낮은 문의는 담당자에게 넘긴다(router.py).
2. 근거 문서: 라우팅 결과에 연결된 FAQ·정책 문서를 고른다(routes.py).
3. 답변 초안: 고른 문서만 근거로 모델이 초안을 쓴다. 최종 발송은 사람이 한다.
"""
from app.logs import log
from app.router import route

ANSWER_PROMPT = """너는 온라인 쇼핑몰 '하루마켓' 상담 담당자의 답변 초안을 쓰는 도우미다.
- 아래 [근거 문서]에 적힌 내용만 근거로 답한다. 문서에 없는 금액, 기간, 약속은 만들지 않는다.
- 문서로 답할 수 없는 부분은 "문서에서 확인할 수 없어 담당자 확인이 필요합니다"라고 쓴다.
- 고객에게 보낼 존댓말 초안으로 3~5문장 안에서 쓴다."""


def draft_stream(question, docs, llm):
    """고른 문서만 근거로 답변 초안을 조금씩 돌려준다."""
    log("INFO", "답변 초안 생성", sources=[d.doc_id for d in docs], length=len(question))
    context = "\n\n".join(f"[{d.title}]\n{d.body}" for d in docs)
    user = f"[근거 문서]\n{context}\n\n[고객 문의]\n{question}"
    yield from llm.stream(ANSWER_PROMPT, user)


def answer_stream(question, llm, kb):
    """/ask 가 쓰는 전체 흐름. 라우팅부터 초안까지 한 번에 처리해 글자로 돌려준다."""
    r = route(question, llm)
    if r.action == "escalate":
        yield f"담당자 검토가 필요한 문의입니다(사유: {r.action_reason}). AI 답변 초안을 만들지 않았습니다."
        return
    if r.action == "out_of_scope":
        yield "근거가 될 FAQ나 정책 문서가 없는 문의입니다. 담당자 확인이 필요합니다."
        return
    docs = kb.for_routes(r.routes)
    yield from draft_stream(question, docs, llm)
    yield "\n\n근거: " + ", ".join(d.title for d in docs)
