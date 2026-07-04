from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="AEGIS-X API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aegis-x-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X",
        "phase": "foundation",
        "components": {
            "api": "online",
            "telemetry": "planned",
            "detection": "planned",
            "attack_graph": "planned",
            "investigator": "planned",
            "response": "planned",
        },
    }
