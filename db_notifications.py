"""
Database functions for notification system (Phase 5a)
Add this as a new file or merge into db.py
"""

from db import get_supabase_client
from datetime import datetime, date, timedelta


# ============================================
# NOTIFICATION PREFERENCES
# ============================================

def get_notification_preferences(user_id: str):
    """Get user's notification preferences, or None if not set."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('notification_preferences')\
            .select('*')\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        return response.data
    except Exception as e:
        # No preferences set yet
        if 'No rows' in str(e) or 'PGRST116' in str(e):
            return None
        raise e


def upsert_notification_preferences(user_id: str, preferences: dict):
    """Create or update notification preferences."""
    supabase = get_supabase_client()
    
    data = {
        'user_id': user_id,
        **preferences,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    try:
        # Try to get existing
        existing = get_notification_preferences(user_id)
        
        if existing:
            # Update
            response = supabase.table('notification_preferences')\
                .update(data)\
                .eq('user_id', user_id)\
                .execute()
        else:
            # Insert
            response = supabase.table('notification_preferences')\
                .insert(data)\
                .execute()
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        print(f"Error upserting notification preferences: {e}")
        raise e


def update_phone_number(user_id: str, phone_number: str, confirmed: bool = False):
    """Update user's phone number."""
    return upsert_notification_preferences(user_id, {
        'phone_number': phone_number,
        'phone_confirmed': confirmed
    })


# ============================================
# NOTIFICATION LOG
# ============================================

def log_notification(user_id: str, notification_type: str, channel: str, 
                     reference_id: str = None, reference_date: date = None,
                     status: str = 'sent', error_message: str = None):
    """Log a sent notification."""
    supabase = get_supabase_client()
    
    data = {
        'user_id': user_id,
        'notification_type': notification_type,
        'channel': channel,
        'status': status
    }
    
    if reference_id:
        data['reference_id'] = reference_id
    if reference_date:
        data['reference_date'] = reference_date.isoformat()
    if error_message:
        data['error_message'] = error_message
    
    try:
        response = supabase.table('notification_log')\
            .insert(data)\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error logging notification: {e}")
        return None


def was_notification_sent(user_id: str, notification_type: str, 
                          reference_id: str = None, reference_date: date = None):
    """Check if a notification was already sent (prevent duplicates)."""
    supabase = get_supabase_client()
    
    try:
        query = supabase.table('notification_log')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('notification_type', notification_type)\
            .eq('status', 'sent')
        
        if reference_id:
            query = query.eq('reference_id', reference_id)
        if reference_date:
            query = query.eq('reference_date', reference_date.isoformat())
        
        response = query.execute()
        return len(response.data) > 0
        
    except Exception as e:
        print(f"Error checking notification status: {e}")
        return False  # Err on side of sending


def get_notification_history(user_id: str, limit: int = 20):
    """Get recent notification history for a user."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('notification_log')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('sent_at', desc=True)\
            .limit(limit)\
            .execute()
        return response.data
    except Exception as e:
        print(f"Error getting notification history: {e}")
        return []


# ============================================
# QUERIES FOR NOTIFICATION JOBS (Phase 5b)
# ============================================

def get_users_for_workout_reminders(hours_ahead: int = 24):
    """
    Find users who have workouts scheduled within the next X hours
    and have workout reminders enabled.
    
    Returns list of dicts with user info, preferences, and workout details.
    """
    supabase = get_supabase_client()
    
    now = datetime.utcnow()
    window_end = now + timedelta(hours=hours_ahead)
    today = now.date()
    
    try:
        # Get all users with workout reminders enabled
        prefs_response = supabase.table('notification_preferences')\
            .select('user_id, phone_number, workout_reminder_hours, workout_reminder_channel')\
            .eq('workout_reminder_enabled', True)\
            .execute()
        
        if not prefs_response.data:
            return []
        
        results = []
        
        for pref in prefs_response.data:
            user_id = pref['user_id']
            reminder_hours = pref.get('workout_reminder_hours', 2)
            
            # Get user's email from profile
            profile_response = supabase.table('profiles')\
                .select('email, display_name')\
                .eq('id', user_id)\
                .single()\
                .execute()
            
            if not profile_response.data:
                continue
                
            profile = profile_response.data
            
            # Get scheduled workouts for today
            workouts_response = supabase.table('scheduled_workouts')\
                .select('id, scheduled_date, workout_name, cycle_id')\
                .eq('user_id', user_id)\
                .eq('status', 'scheduled')\
                .gte('scheduled_date', today.isoformat())\
                .lte('scheduled_date', (today + timedelta(days=1)).isoformat())\
                .execute()
            
            for workout in (workouts_response.data or []):
                results.append({
                    'user_id': user_id,
                    'email': profile.get('email'),
                    'display_name': profile.get('display_name'),
                    'phone_number': pref.get('phone_number'),
                    'channel': pref.get('workout_reminder_channel', 'email'),
                    'reminder_hours': reminder_hours,
                    'workout_id': workout['id'],
                    'workout_name': workout.get('workout_name', 'Workout'),
                    'scheduled_date': workout['scheduled_date']
                })
        
        return results
        
    except Exception as e:
        print(f"Error getting users for workout reminders: {e}")
        return []


def get_users_for_inactivity_nudge(days_inactive: int):
    """
    Find users who haven't completed a workout in X days
    and have inactivity nudges enabled.
    """
    supabase = get_supabase_client()
    
    cutoff_date = (datetime.utcnow() - timedelta(days=days_inactive)).date()
    today = date.today()
    
    try:
        # Get users with inactivity nudges enabled
        prefs_response = supabase.table('notification_preferences')\
            .select('user_id, phone_number, inactivity_week_via_email, inactivity_month_via_sms')\
            .eq('inactivity_nudge_enabled', True)\
            .execute()
        
        if not prefs_response.data:
            return []
        
        results = []
        
        for pref in prefs_response.data:
            user_id = pref['user_id']
            
            # Check last completed workout
            workout_response = supabase.table('user_workouts')\
                .select('completed_at')\
                .eq('user_id', user_id)\
                .not_.is_('completed_at', 'null')\
                .order('completed_at', desc=True)\
                .limit(1)\
                .execute()
            
            last_workout_date = None
            if workout_response.data:
                last_workout_str = workout_response.data[0].get('completed_at')
                if last_workout_str:
                    last_workout_date = datetime.fromisoformat(
                        last_workout_str.replace('Z', '+00:00')
                    ).date()
            
            # Check if they qualify for nudge
            if last_workout_date is None or last_workout_date <= cutoff_date:
                # Get user profile
                profile_response = supabase.table('profiles')\
                    .select('email, display_name')\
                    .eq('id', user_id)\
                    .single()\
                    .execute()
                
                if profile_response.data:
                    profile = profile_response.data
                    
                    # Determine channel based on days
                    if days_inactive >= 30:
                        channel = 'sms' if pref.get('inactivity_month_via_sms') else 'email'
                        nudge_type = 'inactivity_month'
                    else:
                        channel = 'email' if pref.get('inactivity_week_via_email') else None
                        nudge_type = 'inactivity_week'
                    
                    if channel:
                        results.append({
                            'user_id': user_id,
                            'email': profile.get('email'),
                            'display_name': profile.get('display_name'),
                            'phone_number': pref.get('phone_number'),
                            'channel': channel,
                            'nudge_type': nudge_type,
                            'days_inactive': days_inactive,
                            'last_workout_date': last_workout_date.isoformat() if last_workout_date else None
                        })
        
        return results
        
    except Exception as e:
        print(f"Error getting users for inactivity nudge: {e}")
        return []
