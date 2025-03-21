from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    query_text = data.get("query")

    if not query_text:
        return jsonify({"error": "Query text is required"}), 400

    try:
        # Execute query directly with proper argument handling
        result = subprocess.run(
            ["python3", "query_data.py", query_text],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse JSON output directly
        response = json.loads(result.stdout)
        return jsonify(response)

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "Query processing failed",
            "details": e.stderr
        }), 500
        
    except json.JSONDecodeError:
        return jsonify({
            "error": "Invalid response format",
            "raw_output": result.stdout
        }), 500

    except Exception as e:
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)