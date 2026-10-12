"""고객 문의 응대 에이전트 서비스.

화면(/)과 API를 FastAPI 하나가 함께 제공한다.
- /health, /version: 서비스 상태와 배포 버전
- /ask: 라우팅부터 답변 초안까지 한 번에 처리해 스트리밍으로 돌려준다
- /api/inquiries, /api/route, /api/draft: 화면에서 쓰는 문의 샘플, 라우팅 결과, 답변 초안
"""
import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.agent import answer_stream, draft_stream
from app.config import ROOT, load_settings
from app.knowledge import KnowledgeBase
from app.llm import make_llm
from app.router import route
from app.routes import ROUTES, label

settings = load_settings()  # 키가 없으면 여기서 종료한다
kb = KnowledgeBase(ROOT / "data" / "docs")
llm = make_llm(settings)
inquiries = json.loads((ROOT / "data" / "inquiries.json").read_text(encoding="utf-8"))

app = FastAPI(title="고객 문의 응대 에이전트")


def get_llm():
    """테스트에서는 이 함수를 가짜 LLM을 돌려주는 함수로 바꿔 끼운다."""
    return llm


class AskRequest(BaseModel):
    question: str


class DraftRequest(BaseModel):
    question: str
    routes: list[str]


@app.get("/", response_class=HTMLResponse)
def home():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    banner = "" if settings.env in ("production", "local") else f'<div class="banner">테스트 환경 ({settings.env})</div>'
    return html.replace("<!--ENV_BANNER-->", banner)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"commit": settings.commit, "revision": settings.revision, "env": settings.env,
            "llm": settings.provider, "model": settings.model}


@app.post("/ask")
def ask(req: AskRequest, model=Depends(get_llm)):
    return StreamingResponse(answer_stream(req.question, model, kb), media_type="text/plain; charset=utf-8")


@app.get("/api/inquiries")
def list_inquiries():
    # 기대 결과(expected)는 테스트용 정답이라 화면에는 보내지 않는다
    return [{"id": q["id"], "text": q["text"]} for q in inquiries]


@app.post("/api/route")
def route_only(req: AskRequest, model=Depends(get_llm)):
    r = route(req.question, model)
    docs = kb.for_routes(r.routes) if r.action == "answer" else []
    return {
        "routes": [{"id": x, "label": label(x)} for x in r.routes],
        "confidence": r.confidence,
        "reason": r.reason,
        "decided_by": r.decided_by,
        "action": r.action,
        "action_reason": r.action_reason,
        "guards": r.guards,
        "docs": [{"id": d.doc_id, "title": d.title, "body": d.body,
                  "route": next(k for k, v in ROUTES.items() if v["doc"] == d.doc_id)} for d in docs],
    }


@app.post("/api/draft")
def draft(req: DraftRequest, model=Depends(get_llm)):
    routes = [r for r in req.routes if r in ROUTES]
    if not routes:
        raise HTTPException(400, "답변할 수 있는 분류가 없습니다")
    return StreamingResponse(draft_stream(req.question, kb.for_routes(routes), model),
                             media_type="text/plain; charset=utf-8")
