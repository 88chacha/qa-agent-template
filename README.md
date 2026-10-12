# 고객 문의 응대 에이전트 서비스

가상 온라인 쇼핑몰 '하루마켓'의 고객 문의를 받아 답변 초안을 만드는 에이전트 서비스입니다. 모델이 문의를 분류(라우팅)하고, 분류에 연결된 FAQ·정책 문서를 근거로 답변 초안을 스트리밍으로 돌려줍니다. 고위험 문의와 분류 확신이 낮은 문의는 초안 없이 담당자 검토로 넘깁니다. 최종 발송은 사람이 합니다.

화면과 API를 FastAPI 하나가 함께 제공하는 단일 서비스이고, 배포·운영 실습의 예시 코드로 씁니다.

## 저장소 만들기

이 저장소는 GitHub 템플릿 저장소입니다. 오른쪽 위의 **Use this template > Create a new repository** 를 눌러 내 계정에 **공개(Public)** 저장소로 만든 뒤, 내 노트북으로 내려받습니다.

```text
git clone https://github.com/<내 계정>/<저장소 이름>.git
cd <저장소 이름>
```

## 구성

| 경로 | 내용 |
| --- | --- |
| `app/main.py` | 화면(`/`)과 API(`/health`, `/version`, `/ask`, 화면용 `/api/inquiries`, `/api/route`, `/api/draft`) |
| `app/agent.py` | 문의 하나를 처리하는 흐름: 라우팅 → 근거 문서 선택 → 답변 초안 |
| `app/router.py` | 모델 라우터와 안전장치(고위험 표현, 확신도 기준). fake 모드에서는 키워드 규칙 라우터 |
| `app/routes.py` | 분류 목록과 분류별 근거 문서 |
| `app/knowledge.py` | FAQ와 정책 문서 읽기 |
| `app/llm.py` | LLM 호출 (OpenAI, Gemini, 가짜 응답) |
| `app/config.py` | 설정 읽기. AI 키가 없으면 시작하지 않는다 |
| `static/index.html` | 상담 담당자 화면: 문의함, 답변 초안, 라우팅 결과와 근거 문서 |
| `data/docs/` | 가상 쇼핑몰 FAQ와 정책 문서 8개 |
| `data/inquiries.json` | 문의 샘플 30개와 기대하는 분류(라우팅 정답표) |
| `hello/` | 배포 연습용 최소 앱 (AI를 부르지 않음) |
| `Procfile` | Cloud Run이 앱을 시작할 때 쓰는 명령 |
| `AGENTS.md`, `CLAUDE.md` | 코딩 에이전트와 사람이 지키는 작업 규칙 |
| `.claude/settings.json` | 코딩 에이전트(Claude Code)가 실행하지 못하는 명령과 매번 묻는 명령 |
| `docs/deploy-notes.md` | 배포 기록 양식 |
| `JOURNEY.md` | 작업 일지 양식 |

## 환경변수

| 이름 | 값 | 설명 |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai`, `gemini`, `fake` | 기본값 `openai`. `fake` 는 키 없이 가짜 응답을 돌려준다 |
| `LLM_API_KEY` | AI 회사 API 키 | `fake` 가 아니면 필수. 없으면 앱이 시작하지 않는다 |
| `LLM_MODEL` | 모델 이름 | 비우면 제공자별 기본값(`app/config.py`)을 쓴다. 모델 이름은 바뀔 수 있으니 필요하면 지정한다 |
| `ENV` | `local`, `staging`, `production` | `staging` 이면 화면 위에 테스트 환경 표시가 나온다 |
| `COMMIT_SHA` | 커밋 해시 | `/version` 에 표시된다. 자동 배포에서 넣는다 |

## 노트북에서 실행하기

```text
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # .env 를 열어 값을 채운다. 처음에는 LLM_PROVIDER=fake 로 두어도 된다
uvicorn app.main:app --port 8080
```

브라우저에서 `http://localhost:8080` 을 열고 왼쪽 문의함에서 문의를 골라 "초안 만들기"를 누릅니다. 오른쪽에 라우팅 결과(분류, 확신도, 분류 이유, 작동한 안전장치)와 근거 문서가, 가운데에 답변 초안이 한 글자씩 표시됩니다. `LLM_PROVIDER=fake` 이면 모델 대신 키워드 규칙이 분류하고, 근거 문서의 문장을 골라 초안처럼 엮어 보여 줍니다. `.env` 는 노트북에서 실행할 때만 읽고, 저장소와 배포에는 올라가지 않습니다(`.gitignore`, `.gcloudignore`).

## Cloud Run에 배포하기

```text
# hello 앱 (hello/ 폴더 안에서)
gcloud run deploy hello --source . --region us-central1 --allow-unauthenticated

# 에이전트 서비스 (저장소 루트에서)
gcloud run deploy qa-agent --source . --region us-central1 --allow-unauthenticated
```

에이전트 서비스는 `LLM_API_KEY` 가 없으면 시작하지 않으므로, 키를 넣기 전 첫 배포는 실패합니다. 키를 넣는 방법과 Secret Manager 연결은 교안을 따라 진행합니다.
