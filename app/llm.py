"""LLM 호출을 한곳에 모아 둔다.

OpenAI와 Gemini는 같은 OpenAI SDK로 부르고, 주소(base_url)와 모델 이름만 다르다.
fake 는 키 없이 화면과 흐름을 확인하거나 테스트할 때 쓰는 가짜 응답이다.
"""
import json
import re
import time

from app.knowledge import bigrams


class OpenAICompatibleLLM:
    can_route = True  # 라우팅을 모델에게 맡길 수 있다

    def __init__(self, api_key, model, base_url=None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def complete_json(self, system, user):
        """라우팅처럼 정해진 형식의 답이 필요할 때. JSON 하나를 받아 dict로 돌려준다."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def stream(self, system, user):
        """답을 만들어지는 대로 조금씩 돌려준다(스트리밍)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            stream=True,
        )
        for event in response:
            if event.choices and event.choices[0].delta.content:
                yield event.choices[0].delta.content


class FakeLLM:
    """AI를 부르지 않는다. 라우팅은 키워드 규칙이 맡고(can_route=False),
    초안은 근거 문서에서 질문과 가장 가까운 문장을 골라 엮는다.

    비용이 들지 않고 같은 질문에는 늘 같은 답을 돌려주므로, 키 없이 화면을 확인하거나 테스트할 때 쓴다.
    """

    can_route = False

    def __init__(self, delay=0.03):
        self.delay = delay

    def stream(self, system, user):
        context, _, question = user.partition("[고객 문의]")
        sentences = []
        for line in context.replace("[근거 문서]", "").splitlines():
            line = line.strip()
            if not line or line.startswith("["):
                continue
            sentences += [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]

        q = bigrams(question)
        ranked = sorted(range(len(sentences)), key=lambda i: len(q & bigrams(sentences[i])), reverse=True)
        picked = [sentences[i] for i in sorted(ranked[:2])]

        text = "안녕하세요, 하루마켓 고객센터입니다. " + " ".join(picked) + " 더 궁금하신 점이 있으면 편하게 문의해 주세요."
        for i in range(0, len(text), 6):
            time.sleep(self.delay)
            yield text[i:i + 6]


def make_llm(settings):
    if settings.provider == "fake":
        return FakeLLM()
    return OpenAICompatibleLLM(settings.api_key, settings.model, settings.base_url)
