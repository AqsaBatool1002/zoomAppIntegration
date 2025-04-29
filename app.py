import os
import logging
import urllib.parse
import requests
from flask import Flask, redirect, request, jsonify, render_template_string
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("ZOOM_REDIRECT_URI")
ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE_URL = "https://api.zoom.us/v2"

# Store the access token in memory (in production, use a database or secure storage)
access_token = None

@app.route("/")
def home():
    """Home page with instructions and call initiation form"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zoom Phone Integration</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #2D8CFF; }
            .card { background: #f9f9f9; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn { background: #2D8CFF; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #2681E7; }
            input, select { padding: 8px; margin: 8px 0; width: 100%; box-sizing: border-box; }
            label { font-weight: bold; }
            .note { font-size: 0.9em; color: #666; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Zoom Phone Integration</h1>
            
            <div class="card">
                <h2>Authorization</h2>
                <p>Before making calls, you need to authorize this application with Zoom.</p>
                <a href="/authorize" class="btn">Authorize with Zoom</a>
                <p class="note">Status: """ + ("✅ Authorized" if access_token else "❌ Not Authorized") + """</p>
            </div>
            
            <div class="card">
                <h2>Make a Call</h2>
                <form action="/make-call" method="post">
                    <div>
                        <label for="extension">Extension to Call:</label>
                        <input type="text" id="extension" name="extension" value="804" required>
                        <p class="note">Enter the extension you want to call (e.g., 804)</p>
                    </div>
                    
                    <div>
                        <label for="caller_number_type">Caller Number Type:</label>
                        <select id="caller_number_type" name="caller_number_type">
                            <option value="phone_number">Company Phone Number</option>
                            <option value="extension_number">Extension Number</option>
                        </select>
                    </div>
                    
                    <div>
                        <label for="caller_number">Caller Number or Extension:</label>
                        <input type="text" id="caller_number" name="caller_number" required>
                        <p class="note">Your phone number or extension that will be used to make the call</p>
                    </div>
                    
                    <button type="submit" class="btn">Initiate Call</button>
                </form>
            </div>
            
            <div class="card">
                <h2>Webhook Status</h2>
                <p>Configure your Zoom webhook to point to:</p>
                <code>https://your-koyeb-app-url.koyeb.app/webhook</code>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/authorize")
def authorize():
    """ Step 1: Redirect user to Zoom OAuth for Authorization """
    scopes = "phone:write:admin phone:read:admin"  # Add scopes needed for making calls
    url = (
        f"{ZOOM_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(scopes, safe='')}"
    )
    logger.info(f"Redirecting to Zoom OAuth: {url}")
    return redirect(url)

@app.route("/callback")
def callback():
    """ Step 2: Handle OAuth Callback and Exchange Code for Access Token """
    code = request.args.get("code")
    if not code:
        logger.error("Authorization code not found in callback")
        return "❌ Authorization code not found.", 400
    
    try:
        token_response = requests.post(
            ZOOM_TOKEN_URL,
            params={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            auth=(CLIENT_ID, CLIENT_SECRET),
            timeout=10  # Add timeout for the request
        )
        
        token_response.raise_for_status()  # Raise exception for non-200 status codes
        
        token_data = token_response.json()
        global access_token
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        
        if not access_token:
            logger.error("Access token not found in response")
            return "❌ Access token not found in response.", 500
        
        # In a production app, you would store these tokens in a database
        logger.info(f"✅ Authorization successful. Token expires in {expires_in} seconds")
        
        # Return success page to user
        return """
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
                <h1>✅ Authorization Complete</h1>
                <p>Server is now authorized to make Zoom Phone calls!</p>
                <p><a href="/" style="color: #2D8CFF; text-decoration: none;">Return to Home</a></p>
            </body>
        </html>
        """
        
    except requests.RequestException as e:
        logger.error(f"Failed to get access token: {str(e)}")
        return f"❌ Failed to get access token: {str(e)}", 500

@app.route("/make-call", methods=["POST"])
def make_call():
    """Initiate a call to the specified extension"""
    global access_token
    
    if not access_token:
        return "❌ Not authorized. Please authorize with Zoom first.", 401
    
    extension = request.form.get("extension")
    caller_number_type = request.form.get("caller_number_type")
    caller_number = request.form.get("caller_number")
    
    if not extension or not caller_number:
        return "❌ Missing required parameters.", 400
    
    # Prepare the request to Zoom API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # API endpoint for initiating a call
    call_url = f"{ZOOM_API_BASE_URL}/phone/call"
    
    # Prepare the payload
    payload = {
        "to_contact": {
            "extension_number": extension  # Extension to call
        },
        "from_contact": {
            caller_number_type: caller_number  # Your caller ID
        }
    }
    
    try:
        response = requests.post(call_url, headers=headers, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 201 or response.status_code == 200:
            logger.info(f"✅ Call initiated successfully: {response_data}")
            return """
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
                    <h1>✅ Call Initiated!</h1>
                    <p>Your call to extension """ + extension + """ has been initiated.</p>
                    <p><a href="/" style="color: #2D8CFF; text-decoration: none;">Return to Home</a></p>
                </body>
            </html>
            """
        else:
            logger.error(f"❌ Failed to initiate call: {response_data}")
            error_message = response_data.get("message", "Unknown error")
            return f"""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
                    <h1>❌ Call Failed</h1>
                    <p>Error: {error_message}</p>
                    <p><a href="/" style="color: #2D8CFF; text-decoration: none;">Return to Home</a></p>
                </body>
            </html>
            """
    except requests.RequestException as e:
        logger.error(f"❌ Error initiating call: {str(e)}")
        return f"❌ Error initiating call: {str(e)}", 500

@app.route("/webhook", methods=["POST"])
def webhook():
    """ Receive Inbound Call Webhook Event """
    # Verify request content type
    if not request.is_json:
        logger.warning("Received non-JSON webhook payload")
        return jsonify({"status": "error", "message": "Expected JSON payload"}), 400
    
    try:
        data = request.json
        logger.info("🚨 Call Webhook Received 🚨")
        
        # Extract important info from the webhook payload
        event_type = data.get("event")
        payload = data.get("payload", {})
        call_object = payload.get("object", {})
        
        # Call details
        caller_number = call_object.get("caller_number")
        callee_number = call_object.get("callee_number")
        call_id = call_object.get("id")
        call_time = call_object.get("date_time")
        
        # Extract extension if available
        extension = call_object.get("extension_number", "No extension")
        
        # Log call details
        logger.info(f"📞 Call Details:")
        logger.info(f" - Event Type: {event_type}")
        logger.info(f" - Caller Number: {caller_number}")
        logger.info(f" - Callee Number: {callee_number}")
        logger.info(f" - Extension: {extension}")
        logger.info(f" - Call ID: {call_id}")
        logger.info(f" - Call Time: {call_time}")
        
        return jsonify({"status": "received", "event": event_type}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health")
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200

# In Koyeb, port is provided via PORT environment variable
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)