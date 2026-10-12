"""FAQ와 정책 문서를 읽어 두고, 라우팅 결과에 맞는 문서를 꺼내 준다."""
import re
from dataclasses import dataclass
from pathlib import Path

from app.routes import ROUTES


@dataclass
class Doc:
    doc_id: str
    title: str
    body: str


def bigrams(text):
    """글자를 두 개씩 묶은 조각. 가짜 응답 모드에서 문장을 고를 때 쓴다."""
    text = re.sub(r"\s+", "", text.lower())
    return {text[i:i + 2] for i in range(len(text) - 1)}


class KnowledgeBase:
    def __init__(self, folder):
        self.docs = {}
        for path in sorted(Path(folder).glob("*.md")):
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.docs[path.stem] = Doc(path.stem, lines[0].lstrip("# ").strip(), "\n".join(lines[1:]).strip())

    def for_routes(self, routes):
        """라우팅 결과(분류 목록)에 연결된 문서를 순서대로 돌려준다."""
        return [self.docs[ROUTES[r]["doc"]] for r in routes if r in ROUTES]
