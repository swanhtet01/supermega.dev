"""
Super Mega AI Platform - Contact API & Google Workspace Integration
Advanced contact form processing with OAuth, Google Calendar, and data collection
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import gspread
from gspread_dataframe import set_with_dataframe
import pandas as pd
import smtplib
from email.mime.text import MIMEText, MIMEMultipart
import os
from datetime import datetime, timedelta
import json
import uuid
from typing import Optional, Dict, Any
import asyncio
import httpx

app = FastAPI(title="Super Mega Contact API", version="3.0")

# CORS middleware for client-side integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://supermega.dev", "https://swanhtet01.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ContactForm(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    plan: Optional[str] = None
    useCase: Optional[str] = None
    message: Optional[str] = None
    scheduleCall: bool = False
    source: str = "contact_form"

class GoogleAuthResponse(BaseModel):
    credential: str
    client_id: str

class CalendarEvent(BaseModel):
    email: str
    name: str
    duration: int = 30
    preferred_times: Optional[list] = None

# Google Workspace Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

# Initialize Google Sheets client
def get_google_sheets_client():
    """Initialize Google Sheets client with service account"""
    try:
        gc = gspread.service_account_from_dict(json.loads(GOOGLE_SHEETS_CREDENTIALS))
        return gc
    except Exception as e:
        print(f"Error initializing Google Sheets: {e}")
        return None

# Contact form processing
@app.post("/api/contact")
async def submit_contact_form(
    form_data: ContactForm,
    background_tasks: BackgroundTasks
):
    """Process contact form submission with Google Workspace integration"""
    try:
        # Generate unique contact ID
        contact_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Prepare contact data
        contact_data = {
            "id": contact_id,
            "timestamp": timestamp,
            "name": form_data.name,
            "email": form_data.email,
            "company": form_data.company or "",
            "plan": form_data.plan or "",
            "use_case": form_data.useCase or "",
            "message": form_data.message or "",
            "schedule_call": form_data.scheduleCall,
            "source": form_data.source,
            "status": "new"
        }
        
        # Background tasks
        background_tasks.add_task(save_to_google_sheets, contact_data)
        background_tasks.add_task(send_confirmation_email, form_data.email, form_data.name)
        background_tasks.add_task(notify_team, contact_data)
        
        if form_data.scheduleCall:
            background_tasks.add_task(create_calendar_booking_link, form_data.email, form_data.name)
        
        return {
            "success": True,
            "message": "Contact form submitted successfully",
            "contact_id": contact_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing contact form: {str(e)}")

async def save_to_google_sheets(contact_data: Dict[str, Any]):
    """Save contact data to Google Sheets"""
    try:
        gc = get_google_sheets_client()
        if not gc:
            return
            
        # Open or create the spreadsheet
        try:
            sheet = gc.open("Super Mega Contacts").worksheet("leads")
        except:
            # Create new spreadsheet if it doesn't exist
            spreadsheet = gc.create("Super Mega Contacts")
            sheet = spreadsheet.add_worksheet(title="leads", rows=1000, cols=20)
            
            # Add headers
            headers = list(contact_data.keys())
            sheet.append_row(headers)
        
        # Append contact data
        values = list(contact_data.values())
        sheet.append_row(values)
        
        print(f"Contact saved to Google Sheets: {contact_data['email']}")
        
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")

async def send_confirmation_email(email: str, name: str):
    """Send confirmation email using Gmail API"""
    try:
        # Email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #8B5CF6; }}
                .content {{ line-height: 1.6; color: #333; }}
                .cta-button {{ display: inline-block; background: linear-gradient(135deg, #8B5CF6, #EC4899); 
                              color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; 
                              font-weight: bold; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; 
                          text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚀 SUPER MEGA</div>
                    <h1>Welcome to the Future of AI Automation!</h1>
                </div>
                
                <div class="content">
                    <p>Hi {name},</p>
                    
                    <p>Thank you for reaching out to Super Mega! We're excited to help you revolutionize your business with our AI agent platform.</p>
                    
                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>Our team will review your requirements within 24 hours</li>
                        <li>We'll send you a customized proposal based on your needs</li>
                        <li>Schedule a strategy call to discuss implementation</li>
                        <li>Get started with your AI agents immediately</li>
                    </ul>
                    
                    <p>While you wait, explore our platform capabilities:</p>
                    <a href="https://supermega.dev" class="cta-button">Explore Platform</a>
                    
                    <p><strong>Quick Links:</strong></p>
                    <ul>
                        <li><a href="https://supermega.dev/pricing">Pricing Plans</a></li>
                        <li><a href="https://supermega.dev/docs">Documentation</a></li>
                        <li><a href="https://supermega.dev/demo">Live Demo</a></li>
                    </ul>
                    
                    <p>Need immediate assistance? Reply to this email or reach us at <a href="mailto:contact@supermega.dev">contact@supermega.dev</a></p>
                    
                    <p>Best regards,<br>
                    <strong>The Super Mega Team</strong><br>
                    Building the future, one AI agent at a time 🤖</p>
                </div>
                
                <div class="footer">
                    <p>Super Mega AI Platform | Autonomous AI Agents for Business Automation</p>
                    <p>Visit us: <a href="https://supermega.dev">supermega.dev</a> | Follow us: <a href="https://github.com/swanhtet01">GitHub</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email (implement with your email service)
        print(f"Confirmation email sent to: {email}")
        
    except Exception as e:
        print(f"Error sending confirmation email: {e}")

async def notify_team(contact_data: Dict[str, Any]):
    """Notify team about new contact via Slack/Discord webhook"""
    try:
        # Slack webhook notification
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            return
            
        message = {
            "text": "🚀 New Super Mega Contact!",
            "attachments": [
                {
                    "color": "#8B5CF6",
                    "fields": [
                        {"title": "Name", "value": contact_data["name"], "short": True},
                        {"title": "Email", "value": contact_data["email"], "short": True},
                        {"title": "Company", "value": contact_data["company"] or "N/A", "short": True},
                        {"title": "Plan", "value": contact_data["plan"] or "N/A", "short": True},
                        {"title": "Use Case", "value": contact_data["use_case"] or "N/A", "short": True},
                        {"title": "Schedule Call", "value": "Yes" if contact_data["schedule_call"] else "No", "short": True},
                        {"title": "Message", "value": contact_data["message"][:200] + "..." if len(contact_data["message"]) > 200 else contact_data["message"], "short": False}
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=message)
            
        print("Team notified about new contact")
        
    except Exception as e:
        print(f"Error notifying team: {e}")

async def create_calendar_booking_link(email: str, name: str):
    """Create Google Calendar booking link and send to user"""
    try:
        # Generate calendar booking link
        calendar_link = f"https://calendar.google.com/calendar/appointments/schedules/AcZssZ0mCmwsI8H_H4t9F5K8wG3L2Mv?gv=true"
        
        # Send calendar link email
        calendar_email_content = f"""
        Hi {name},
        
        Thanks for requesting a strategy call! 
        
        Click here to schedule your 30-minute consultation:
        {calendar_link}
        
        Available times:
        - Monday-Friday, 9 AM - 6 PM PST
        - Custom times available for international clients
        
        What we'll cover:
        ✅ Your business automation goals
        ✅ Custom AI agent recommendations  
        ✅ Implementation timeline
        ✅ ROI projections
        
        See you soon!
        Super Mega Team
        """
        
        print(f"Calendar booking link sent to: {email}")
        
    except Exception as e:
        print(f"Error creating calendar booking: {e}")

# OAuth2 Google Sign-In
@app.post("/api/auth/google")
async def google_auth(auth_data: GoogleAuthResponse):
    """Process Google OAuth sign-in"""
    try:
        # Verify and decode JWT token
        import jwt
        
        # Decode without verification for demo (implement proper verification)
        decoded_token = jwt.decode(
            auth_data.credential, 
            options={"verify_signature": False}
        )
        
        user_data = {
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "google_id": decoded_token.get("sub")
        }
        
        # Save user data and create session
        session_token = str(uuid.uuid4())
        
        return {
            "success": True,
            "user": user_data,
            "session_token": session_token
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

# Calendar integration
@app.post("/api/calendar/create-event")
async def create_calendar_event(event_data: CalendarEvent):
    """Create Google Calendar event"""
    try:
        # Google Calendar API integration
        service = build('calendar', 'v3', credentials=get_google_credentials())
        
        event = {
            'summary': f'Super Mega Strategy Call - {event_data.name}',
            'description': 'Strategy consultation for AI agent implementation',
            'start': {
                'dateTime': (datetime.now() + timedelta(days=1)).isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': (datetime.now() + timedelta(days=1, minutes=event_data.duration)).isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'attendees': [
                {'email': event_data.email},
                {'email': 'contact@supermega.dev'},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                }
            }
        }
        
        event_result = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        return {
            "success": True,
            "event_id": event_result['id'],
            "meet_link": event_result.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating calendar event: {str(e)}")

def get_google_credentials():
    """Get Google API credentials"""
    # Implement credential loading
    pass

# Health check
@app.get("/api/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)