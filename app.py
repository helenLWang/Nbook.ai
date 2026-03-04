from app import create_app


# region agent log
def _agent_debug_log(hypothesis_id: str, message: str, data: dict | None = None) -> None:
    """调试日志：写入 NDJSON 到 .cursor/debug.log，用于定位启动问题。"""
    import json
    import time
    import os

    log_path = r"c:\Users\13360\Desktop\dist\nbook_ai\.cursor\debug.log"
    ts = int(time.time() * 1000)
    payload = {
        "id": f"log_{ts}",
        "timestamp": ts,
        "location": "app.py",
        "message": message,
        "data": data or {},
        "runId": "run1",
        "hypothesisId": hypothesis_id,
    }
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        # 如果日志写入失败，忽略以免影响主流程
        pass
# endregion


_agent_debug_log("H1", "before_create_app", {})
try:
    app = create_app()
    _agent_debug_log("H1", "create_app_success", {})
except Exception as e:  # noqa: BLE001
    _agent_debug_log("H1", "create_app_exception", {"error": repr(e)})
    raise


if __name__ == "__main__":
    _agent_debug_log("H2", "before_app_run", {"debug": True})
    app.run(debug=True)

