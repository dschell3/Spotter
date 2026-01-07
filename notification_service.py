"""
Notification Service (Phase 5b)
Handles sending emails via Resend and SMS via Twilio (Phase 5c)

Required environment variables:
    RESEND_API_KEY=re_xxxxxxxxx
    NOTIFICATION_FROM_EMAIL=notifications@yourdomain.com (or onboarding@resend.dev for testing)
    APP_NAME=Spotter (optional, defaults to "Spotter")
"""

import os
import resend
from datetime import datetime, date

# Config - loaded lazily to ensure .env is loaded first
FROM_EMAIL = None
APP_NAME = None
_initialized = False


def _ensure_initialized():
    """Initialize Resend API key and config on first use."""
    global FROM_EMAIL, APP_NAME, _initialized
    
    if _initialized:
        return
    
    resend.api_key = os.environ.get('RESEND_API_KEY')
    FROM_EMAIL = os.environ.get('NOTIFICATION_FROM_EMAIL', 'onboarding@resend.dev')
    APP_NAME = os.environ.get('APP_NAME', 'Spotter')
    _initialized = True
    
    if resend.api_key:
        print(f"[NOTIFICATIONS] Resend initialized with FROM_EMAIL={FROM_EMAIL}")
    else:
        print("[NOTIFICATIONS] WARNING: RESEND_API_KEY not set")


# ============================================
# EMAIL TEMPLATES
# ============================================

def get_workout_reminder_email(user_name: str, workout_name: str, scheduled_time: str = None):
    """Generate workout reminder email content."""
    _ensure_initialized()
    
    time_str = f" at {scheduled_time}" if scheduled_time else " today"
    
    subject = f"🏋️ Reminder: {workout_name}{time_str}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #1a1a1a; color: #e5e5e5; padding: 20px; margin: 0;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #262626; border-radius: 12px; padding: 32px;">
            <h1 style="color: #22c55e; font-size: 24px; margin: 0 0 16px 0;">
                Time to train! 💪
            </h1>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Hey {user_name},
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                You have <strong style="color: #22c55e;">{workout_name}</strong> scheduled{time_str}.
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Get after it! 🔥
            </p>
            <hr style="border: none; border-top: 1px solid #404040; margin: 24px 0;">
            <p style="font-size: 12px; color: #737373; margin: 0;">
                You're receiving this because you enabled workout reminders in {APP_NAME}.
            </p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Time to train!

Hey {user_name},

You have {workout_name} scheduled{time_str}.

Get after it!

---
You're receiving this because you enabled workout reminders in {APP_NAME}.
    """
    
    return subject, html, text


def get_inactivity_week_email(user_name: str, last_workout_date: str = None):
    """Generate 1-week inactivity nudge email."""
    _ensure_initialized()
    
    subject = f"👋 We miss you, {user_name}!"
    
    last_workout_str = f"Your last workout was on {last_workout_date}." if last_workout_date else "It's been a little while since your last workout."
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #1a1a1a; color: #e5e5e5; padding: 20px; margin: 0;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #262626; border-radius: 12px; padding: 32px;">
            <h1 style="color: #22c55e; font-size: 24px; margin: 0 0 16px 0;">
                Hey {user_name} 👋
            </h1>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                {last_workout_str}
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Life gets busy — we get it! But even a quick session can help you stay on track.
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Your muscles are waiting. Let's go! 💪
            </p>
            <hr style="border: none; border-top: 1px solid #404040; margin: 24px 0;">
            <p style="font-size: 12px; color: #737373; margin: 0;">
                You're receiving this because you enabled inactivity nudges in {APP_NAME}.
                Don't want these? Update your notification settings in the app.
            </p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Hey {user_name},

{last_workout_str}

Life gets busy — we get it! But even a quick session can help you stay on track.

Your muscles are waiting. Let's go!

---
You're receiving this because you enabled inactivity nudges in {APP_NAME}.
Don't want these? Update your notification settings in the app.
    """
    
    return subject, html, text


def get_inactivity_month_email(user_name: str, last_workout_date: str = None):
    """Generate 1-month inactivity nudge email (more urgent tone)."""
    _ensure_initialized()
    
    subject = f"🚨 {user_name}, it's been a month!"
    
    last_workout_str = f"Your last logged workout was {last_workout_date}." if last_workout_date else "It's been about a month since we've seen you."
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #1a1a1a; color: #e5e5e5; padding: 20px; margin: 0;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #262626; border-radius: 12px; padding: 32px;">
            <h1 style="color: #f59e0b; font-size: 24px; margin: 0 0 16px 0;">
                Time for a comeback! 🔥
            </h1>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Hey {user_name},
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                {last_workout_str} That's okay — what matters is getting back on track.
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Start small. One workout. Today.
            </p>
            <p style="font-size: 18px; line-height: 1.6; margin: 0 0 24px 0; color: #22c55e;">
                You've got this. 💪
            </p>
            <hr style="border: none; border-top: 1px solid #404040; margin: 24px 0;">
            <p style="font-size: 12px; color: #737373; margin: 0;">
                You're receiving this because you enabled inactivity nudges in {APP_NAME}.
            </p>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Time for a comeback!

Hey {user_name},

{last_workout_str} That's okay — what matters is getting back on track.

Start small. One workout. Today.

You've got this.

---
You're receiving this because you enabled inactivity nudges in {APP_NAME}.
    """
    
    return subject, html, text


# ============================================
# EMAIL SENDING
# ============================================

def send_email(to_email: str, subject: str, html: str, text: str = None):
    """
    Send an email via Resend.
    Returns (success: bool, error_message: str or None)
    """
    _ensure_initialized()
    
    if not resend.api_key:
        print("[ERROR] RESEND_API_KEY not configured")
        return False, "RESEND_API_KEY not configured"
    
    try:
        params = {
            "from": f"{APP_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        
        if text:
            params["text"] = text
        
        response = resend.Emails.send(params)
        
        print(f"[EMAIL] Sent to {to_email}: {subject}")
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {error_msg}")
        return False, error_msg


# ============================================
# HIGH-LEVEL NOTIFICATION FUNCTIONS
# ============================================

def send_workout_reminder_email(to_email: str, user_name: str, workout_name: str, scheduled_time: str = None):
    """Send a workout reminder email."""
    subject, html, text = get_workout_reminder_email(user_name, workout_name, scheduled_time)
    return send_email(to_email, subject, html, text)


def send_inactivity_week_email(to_email: str, user_name: str, last_workout_date: str = None):
    """Send a 1-week inactivity nudge email."""
    subject, html, text = get_inactivity_week_email(user_name, last_workout_date)
    return send_email(to_email, subject, html, text)


def send_inactivity_month_email(to_email: str, user_name: str, last_workout_date: str = None):
    """Send a 1-month inactivity nudge email."""
    subject, html, text = get_inactivity_month_email(user_name, last_workout_date)
    return send_email(to_email, subject, html, text)


# ============================================
# SMS FUNCTIONS (Phase 5c - Placeholder)
# ============================================

def send_sms(to_phone: str, message: str):
    """
    Send an SMS via Twilio.
    TODO: Implement in Phase 5c
    """
    _ensure_initialized()
    print(f"[SMS TODO] Would send to {to_phone}: {message}")
    return False, "Twilio not yet configured"


def send_workout_reminder_sms(to_phone: str, user_name: str, workout_name: str):
    """Send a workout reminder SMS."""
    _ensure_initialized()
    message = f"Hey {user_name}! Reminder: {workout_name} is coming up. Time to get after it! 💪"
    return send_sms(to_phone, message)


def send_inactivity_month_sms(to_phone: str, user_name: str):
    """Send a 1-month inactivity nudge SMS."""
    _ensure_initialized()
    message = f"Hey {user_name}, it's been a month since your last workout. Time for a comeback! 🔥"
    return send_sms(to_phone, message)


def send_welcome_sms(to_phone: str, user_name: str):
    """Send welcome SMS when user confirms phone number."""
    _ensure_initialized()
    message = f"Welcome to {APP_NAME}, {user_name}! You'll now receive workout reminders at this number. Reply STOP to unsubscribe."
    return send_sms(to_phone, message)