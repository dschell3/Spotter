"""
Database functions for user exercise notes
Personal notes per exercise (user-specific, global across all workouts)
"""
from datetime import datetime
from db import get_supabase_client

# Maximum note length (enforced at application level)
MAX_NOTE_LENGTH = 500


def get_user_exercise_note(user_id: str, exercise_id: str):
    """
    Get a user's note for a specific exercise.
    
    Returns:
        Note dict with id, note_text, created_at, updated_at
        or None if no note exists
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('user_exercise_notes')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('exercise_id', exercise_id)\
            .limit(1)\
            .execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting exercise note: {e}")
        return None


def get_user_exercise_notes_bulk(user_id: str, exercise_ids: list):
    """
    Get notes for multiple exercises at once (efficient for loading workout).
    
    Args:
        user_id: User's ID
        exercise_ids: List of exercise UUIDs
    
    Returns:
        Dict mapping exercise_id -> note_text
    """
    if not exercise_ids:
        return {}
    
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('user_exercise_notes')\
            .select('exercise_id, note_text')\
            .eq('user_id', user_id)\
            .in_('exercise_id', exercise_ids)\
            .execute()
        
        # Return as dict for easy lookup
        return {note['exercise_id']: note['note_text'] for note in (response.data or [])}
    except Exception as e:
        print(f"Error getting exercise notes bulk: {e}")
        return {}


def upsert_user_exercise_note(user_id: str, exercise_id: str, note_text: str):
    """
    Create or update a user's note for an exercise.
    
    Args:
        user_id: User's ID
        exercise_id: Exercise UUID
        note_text: Note content (max 500 chars, enforced here)
    
    Returns:
        The created/updated note dict, or None on error
    """
    supabase = get_supabase_client()
    
    # Enforce max length
    note_text = note_text.strip()
    if len(note_text) > MAX_NOTE_LENGTH:
        note_text = note_text[:MAX_NOTE_LENGTH]
    
    # Don't save empty notes - delete instead
    if not note_text:
        return delete_user_exercise_note(user_id, exercise_id)
    
    try:
        # Check if note exists
        existing = get_user_exercise_note(user_id, exercise_id)
        
        if existing:
            # Update existing note
            response = supabase.table('user_exercise_notes')\
                .update({
                    'note_text': note_text,
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('id', existing['id'])\
                .execute()
        else:
            # Create new note
            response = supabase.table('user_exercise_notes')\
                .insert({
                    'user_id': user_id,
                    'exercise_id': exercise_id,
                    'note_text': note_text
                })\
                .execute()
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        print(f"Error upserting exercise note: {e}")
        return None


def delete_user_exercise_note(user_id: str, exercise_id: str):
    """
    Delete a user's note for an exercise.
    
    Returns:
        True if deleted (or didn't exist), False on error
    """
    supabase = get_supabase_client()
    
    try:
        supabase.table('user_exercise_notes')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('exercise_id', exercise_id)\
            .execute()
        
        return True
    except Exception as e:
        print(f"Error deleting exercise note: {e}")
        return False


def get_all_user_notes(user_id: str):
    """
    Get all exercise notes for a user.
    Useful for settings/export page.
    
    Returns:
        List of note dicts with exercise info
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('user_exercise_notes')\
            .select('*, exercises(name, muscle_group)')\
            .eq('user_id', user_id)\
            .order('updated_at', desc=True)\
            .execute()
        
        return response.data or []
    except Exception as e:
        print(f"Error getting all user notes: {e}")
        return []
