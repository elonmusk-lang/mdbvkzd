from flask import Flask, request, jsonify
import requests
import json
import re
import time
import base64

app = Flask(__name__)

# ---------------- CONFIG ----------------
OWNER = "https://t.me/ThirdEyeOSINT"

# ---------------- GST HELPERS ----------------

def extract_pan_from_gst(gst_number):
    if len(gst_number) == 15:
        return gst_number[2:12]
    return None

def validate_gst_number(gst_number):
    gst_number = gst_number.upper().strip()

    if len(gst_number) != 15:
        return False, "GST number must be exactly 15 characters long"

    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'

    if not re.match(pattern, gst_number):
        return False, "Invalid GST number format"

    return True, "Valid GST number"

# ---------------- FETCH DATA ----------------

def fetch_gst_details(gst_number):
    encoded_api_url = "aHR0cHM6Ly9jbGVhcnRheC5pbi9mL2NvbXBsaWFuY2UtcmVwb3J0Lw=="
    encoded_search_url = "aHR0cHM6Ly9jbGVhcnRheC5pbi9nc3QtbnVtYmVyLXNlYXJjaC8="

    api_base_url = base64.b64decode(encoded_api_url).decode('utf-8')
    search_page_url = base64.b64decode(encoded_search_url).decode('utf-8')

    encoded_headers = "ewogICJVc2VyLUFnZW50IjogIk1vemlsbGEvNS4wIiwKICAiQWNjZXB0IjogImFwcGxpY2F0aW9uL2pzb24iLAogICJSZWZlcmVyIjogImh0dHBzOi8vY2xlYXJ0YXguaW4vZ3N0LW51bWJlci1zZWFyY2gvIgp9"

    headers = json.loads(base64.b64decode(encoded_headers).decode('utf-8'))

    session = requests.Session()

    try:
        # Step 1: Open search page
        session.get(search_page_url, headers=headers, timeout=10)

        # Step 2: Call API
        api_url = f"{api_base_url}{gst_number}/"
        time.sleep(1)

        response = session.get(api_url, headers=headers, timeout=30)

        if response.status_code == 200:
            return response.json()

        return None

    except:
        return None

# ---------------- FORMAT RESPONSE ----------------

def format_response(data, gst_number):
    taxpayer_info = data.get('taxpayerInfo', {}) if data else {}

    return {
        "gst_number": gst_number,
        "pan_number": extract_pan_from_gst(gst_number),
        "business_info": {
            "legal_name": taxpayer_info.get('lgnm'),
            "trade_name": taxpayer_info.get('tradeNam'),
            "constitution": taxpayer_info.get('ctb'),
            "taxpayer_type": taxpayer_info.get('dty'),
            "status": taxpayer_info.get('sts'),
            "registration_date": taxpayer_info.get('rgdt'),
            "cancellation_date": taxpayer_info.get('cxdt')
        },
        "nature_of_business": taxpayer_info.get('nba', []),
        "address": taxpayer_info.get('pradr', {}).get('addr', {})
    }

# ---------------- API ROUTE ----------------

@app.route("/gst", methods=["GET"])
def gst_lookup():
    gst_number = request.args.get("number", "").upper().strip()

    if not gst_number:
        return build_response(False, "GST number is required", 400)

    is_valid, message = validate_gst_number(gst_number)

    if not is_valid:
        return build_response(False, message, 400)

    data = fetch_gst_details(gst_number)

    if not data:
        return build_response(False, "Failed to fetch GST details", 500)

    return build_response(True, "Success", 200, format_response(data, gst_number))

# ---------------- RESPONSE BUILDER ----------------

def build_response(success, message, status_code, data=None):
    response_body = {
        "success": success,
        "message": message,
        "meta": {
            "owner": OWNER,
            "api": "GST Lookup API"
        }
    }

    if data:
        response_body["data"] = data

    response = jsonify(response_body)
    response.status_code = status_code

    # Add hidden header credit
    response.headers["X-Credit"] = OWNER

    return response

# ---------------- ROOT ----------------

@app.route("/")
def home():
    return jsonify({
        "message": "GST Lookup API Running",
        "usage": "/gst?number=GSTIN",
        "meta": {
            "owner": OWNER
        }
    })

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)
