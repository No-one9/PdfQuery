# from flask import Flask, request, jsonify
# import subprocess
# import re

# app = Flask(__name__)

# def parse_output(output):
#     """Parse terminal output into structured data"""
#     answer_match = re.search(r"Answer:\n(.+?)\n\nSource:", output, re.DOTALL)
#     source_match = re.search(r"Source: (.+)", output)
#     confidence_match = re.search(r"Confidence: (\d+\.\d+)", output)
    
#     return {
#         "answer": answer_match.group(1).strip() if answer_match else "No answer found",
#         "source": source_match.group(1) if source_match else "Unknown",
#         "confidence": float(confidence_match.group(1)) if confidence_match else 0.0
#     }

# @app.route("/query", methods=["POST"])
# def query():
#     data = request.json
#     query_text = data.get("query")

#     if not query_text:
#         return jsonify({"error": "Query text is required"}), 400
#     output=""
#     try:
#         result = subprocess.run(
#             ["python3", "query_data.py", f'"{query_text}"'],
#             capture_output=True,
#             text=True
#         )
        
#         if result.returncode != 0:
#             return jsonify({"error": result.stderr}), 500

#         return jsonify(parse_output(result.stdout))

#     except Exception as e:
#         return jsonify({
#             "error": str(e),
#             "output": output,
#             "stderr": result.stderr if 'result' in locals() else None
#         }), 500

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000)

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