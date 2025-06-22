import requests
import json
from oauthlib.oauth2 import WebApplicationClient
from flask import redirect, url_for, request
from flask_login import login_user, current_user
from models import db, User
from config import Config

client = WebApplicationClient(Config.GOOGLE_CLIENT_ID)

def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    google_provider_cfg = requests.get(Config.GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=Config.REDIRECT_URI,
        scope=["openid", "email", "profile"],
    )
    return request_uri

def handle_google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get("code")
    google_provider_cfg = requests.get(Config.GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=Config.REDIRECT_URI,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(Config.GOOGLE_CLIENT_ID, Config.GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))
    
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
        
        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(id=str(unique_id), name=users_name, email=users_email)
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return True, user
    
    return False, None 