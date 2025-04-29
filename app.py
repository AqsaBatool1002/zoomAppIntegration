import os
from flask import Flask, redirect, request, jsonify
import urllib.parse
from dotenv import load_dotenv

# Load environment variables (Optional if you're using .env)
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
CLIENT_ID = "EMBHBncrSteZR4jaEuQYCw"  # Your Zoom Client ID
REDIRECT_URI = "https://zygomorphic-maribeth-aqsabatool1002-821660b4.koyeb.app/callback"  # Your Koyeb redirect URI
ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"  # Zoom OAuth URL

@app.route("/")
def home():
    """Redirect user to Zoom OAuth page"""
    scopes = "phone:write phone:read"  # User-level scopes
    url = (
        f"{ZOOM_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(scopes, safe='')}"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    """Handle OAuth callback to get the authorization code"""
    code = request.args.get("code")
    if not code:
        return "Authorization code not found. Please try again."

    # Display the authorization code for copying
    return f"Authorization code: {code}. You can now hardcode it in your application."

if __name__ == "__main__":
    app.run(debug=True, port=5000)
