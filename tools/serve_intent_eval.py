"""Serve the real UI + intent API with temporary learner storage on port 8789.

Never runs Plan/lesson model generation. Stop with Ctrl-C; temporary data is removed.
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn
    from starlette.responses import JSONResponse
    from backend import main as api
    with tempfile.TemporaryDirectory(prefix="learning-intent-browser-") as directory:
        api.SERVER_ROOT = Path(directory)
        api.latest_release = lambda: ROOT / "workspace/dev"

        @api.app.middleware("http")
        async def intent_only(request, call_next):
            if request.method == "POST" and request.url.path != "/api/onboarding/intent":
                return JSONResponse({"detail": {"message": "隔离评测：只测试意图，不生成正式课程。"}}, status_code=409)
            return await call_next(request)

        uvicorn.run(api.app, host="127.0.0.1", port=8789)
