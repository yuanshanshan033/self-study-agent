import json
import sys
import os

# 添加 vendor 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

from flask import Flask, request, Response
from config import CHROMA_SERVER_PORT
from chroma_store import query_and_answer_stream

app = Flask(__name__)


@app.route("/query", methods=["POST"])
def handle_query():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not question:
        return Response("data: {\"error\": \"question is required\"}\n\ndata: [DONE]\n\n",
                        mimetype="text/event-stream")

    def generate():
        for token in query_and_answer_stream(question):
            chunk = json.dumps({"content": token}, ensure_ascii=False)
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    print(f"Chroma HTTP 服务启动 http://127.0.0.1:{CHROMA_SERVER_PORT}")
    app.run(host="127.0.0.1", port=CHROMA_SERVER_PORT, threaded=True)