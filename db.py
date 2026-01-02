from supabase import create_client, Client
from config import Config

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def get_authenticated_client(access_token: str) -> Client:
    """Get a Supabase client authenticated with user's token for RLS."""
    client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    client.auth.set_session(access_token, "")
    return client


# ============================================
# EXERCISE QUERIES
# ============================================

def get_all_exercises():
    """Fetch all exercises from database."""
    supabase = get_supabase_client()
    response = supabase.table('exercises').select('*').execute()
    return response.data


def get_exercises_by_muscle_group(muscle_group: str):
    """Fetch exercises filtered by muscle group."""
    supabase = get_supabase_client()
    response = supabase.table('exercises').select('*').eq('muscle_group', muscle_group).execute()
    return response.data


# ============================================
# TEMPLATE QUERIES
# ============================================

def get_templates_by_split(split_type: str):
    """Fetch workout templates for a split type."""
    supabase = get_supabase_client()
    response = supabase.table('workout_templates')\
        .select('*')\
        .eq('split_type', split_type)\
        .order('day_number')\
        .execute()
    return response.data


def get_template_with_exercises(template_id: str):
    """Fetch a template with all its exercises."""
    supabase = get_supabase_client()
    
    # Get template
    template_response = supabase.table('workout_templates')\
        .select('*')\
        .eq('id', template_id)\
        .single()\
        .execute()
    
    if not template_response.data:
        return None
    
    template = template_response.data
    
    # Get template exercises with exercise details
    exercises_response = supabase.table('template_exercises')\
        .select('*, exercises(*)')\
        .eq('template_id', template_id)\
        .order('order_index')\
        .execute()
    
    # Format exercises for the frontend
    template['exercises'] = []
    for te in exercises_response.data:
        exercise = te['exercises']
        exercise['sets'] = te['sets']
        exercise['rep_range'] = te['rep_range_text'] or f"{te['rep_range_low']}-{te['rep_range_high']}"
        exercise['rest_seconds'] = te['rest_seconds']
        template['exercises'].append(exercise)
    
    return template


def get_routine(split_type: str = 'ppl_3day'):
    """Get a complete routine with all days and exercises."""
    supabase = get_supabase_client()
    
    # Get all templates for this split
    templates = get_templates_by_split(split_type)
    
    routine = {
        'name': 'PPL×2 (3 Day)' if split_type == 'ppl_3day' else split_type,
        'description': 'Push/Pull/Legs hit twice per week in 3 training days',
        'days': []
    }
    
    for template in templates:
        day_data = get_template_with_exercises(template['id'])
        if day_data:
            routine['days'].append({
                'id': day_data['id'],
                'day_number': day_data['day_number'],
                'name': day_data['name'],
                'focus': day_data['focus'] or [],
                'exercises': day_data['exercises']
            })
    
    return routine


# ============================================
# USER WORKOUT QUERIES (require auth)
# ============================================

def create_user_workout(user_id: str, template_id: str, template_name: str, access_token: str):
    """Create a new workout session for a user."""
    supabase = get_supabase_client()
    
    response = supabase.table('user_workouts').insert({
        'user_id': user_id,
        'template_id': template_id,
        'template_name': template_name
    }).execute()
    
    return response.data[0] if response.data else None


def save_workout_sets(user_workout_id: str, sets_data: list, access_token: str):
    """Save all sets for a workout."""
    supabase = get_supabase_client()
    
    # Format sets for insertion
    sets_to_insert = []
    for s in sets_data:
        sets_to_insert.append({
            'user_workout_id': user_workout_id,
            'exercise_id': s.get('exercise_id'),
            'exercise_name': s.get('exercise_name'),
            'set_number': s.get('set_number'),
            'weight': s.get('weight'),
            'reps': s.get('reps'),
            'completed': s.get('completed', False)
        })
    
    if sets_to_insert:
        response = supabase.table('workout_sets').insert(sets_to_insert).execute()
        return response.data
    return []


def complete_user_workout(workout_id: str, access_token: str):
    """Mark a workout as completed."""
    supabase = get_supabase_client()
    
    from datetime import datetime
    response = supabase.table('user_workouts')\
        .update({'completed_at': datetime.utcnow().isoformat()})\
        .eq('id', workout_id)\
        .execute()
    
    return response.data[0] if response.data else None


def get_user_workouts(user_id: str, access_token: str, limit: int = 20):
    """Get recent workouts for a user."""
    supabase = get_supabase_client()
    
    response = supabase.table('user_workouts')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('created_at', desc=True)\
        .limit(limit)\
        .execute()
    
    return response.data


def get_workout_with_sets(workout_id: str, access_token: str):
    """Get a workout with all its sets."""
    supabase = get_supabase_client()
    
    # Get workout
    workout_response = supabase.table('user_workouts')\
        .select('*')\
        .eq('id', workout_id)\
        .single()\
        .execute()
    
    if not workout_response.data:
        return None
    
    workout = workout_response.data
    
    # Get sets
    sets_response = supabase.table('workout_sets')\
        .select('*')\
        .eq('user_workout_id', workout_id)\
        .order('exercise_name')\
        .order('set_number')\
        .execute()
    
    workout['sets'] = sets_response.data
    return workout


# ============================================
# PROFILE QUERIES
# ============================================

def get_user_profile(user_id: str):
    """Get user profile."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('profiles')\
            .select('*')\
            .eq('id', user_id)\
            .execute()
        
        # Return first result or None if no profile exists
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None


def update_user_profile(user_id: str, updates: dict):
    """Update user profile."""
    supabase = get_supabase_client()
    
    response = supabase.table('profiles')\
        .update(updates)\
        .eq('id', user_id)\
        .execute()
    
    return response.data[0] if response.data else None
