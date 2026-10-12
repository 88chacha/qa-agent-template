"""설정 읽기. 앱이 시작할 때 한 번 실행된다.

AI 키가 없으면 오류 로그를 남기고 바로 종료한다.
키 없이 시작해서 질문마다 오류를 돌려주는 것보다, 배포 단계에서 바로 실패하는 편이 문제를 빨리 찾을 수 있다.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.logs import log

ROOT = Path(__file__).resolve().parent.parent

# LLM 제공자별 기본값. 모델 이름은 바뀔 수 있으므로 LLM_MODEL 환경변수로 덮어쓸 수 있다.
PROVIDERS = {
    "openai": {"base_url": None, "model": "gpt-4o-mini"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-3.8-flash"},
    "fake": {"base_url": None, "model": "fake"},
}


@dataclass
class Settings:
    provider: str
    api_key: str
    model: str
    base_url: str | None
    env: str
    commit: str
    revision: str


def load_dotenv(path):
    """노트북에서 실행할 때만 .env 파일을 읽는다. 배포할 때는 .env가 올라가지 않는다."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings():
    load_dotenv(ROOT / ".env")

    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    if provider not in PROVIDERS:
        log("ERROR", f"LLM_PROVIDER 값 '{provider}' 를 알 수 없어 앱을 시작하지 않습니다. openai, gemini, fake 중 하나를 쓰세요.")
        sys.exit(1)

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if provider != "fake" and not api_key:
        log("ERROR", "LLM_API_KEY 환경변수가 없어 앱을 시작하지 않습니다.")
        sys.exit(1)

    defaults = PROVIDERS[provider]
    settings = Settings(
        provider=provider,
        api_key=api_key,
        model=os.environ.get("LLM_MODEL", "").strip() or defaults["model"],
        base_url=defaults["base_url"],
        env=os.environ.get("ENV", "local").strip(),
        commit=os.environ.get("COMMIT_SHA", "local").strip(),
        revision=os.environ.get("K_REVISION", "local"),  # Cloud Run이 리비전 이름을 넣어 준다
    )
    log("INFO", f"앱을 시작합니다. 제공자={settings.provider}, 모델={settings.model}, 환경={settings.env}")
    return settings
