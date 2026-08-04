from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config import Settings


def create_app(settings: Settings, store=None, yt=None, llm=None) -> FastAPI:
    app = FastAPI(title="youtube-trends")
    app.state.settings = settings
    app.state.store = store
    app.state.yt = yt
    app.state.llm = llm

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        # ALB 헬스체크: 프로세스 생존만 확인한다. DynamoDB 장애가 태스크 교체 폭풍을
        # 일으키지 않도록 어떤 외부 의존에도 접근하지 않는다.
        return "ok"

    return app
