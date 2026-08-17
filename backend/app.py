from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

CORS(app)


@app.route("/api/health")
def health():
    return {
        "success": True,
        "message": "Nexora API is running"
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)