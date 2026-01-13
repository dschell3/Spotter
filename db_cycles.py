"""
Database functions for cycles and planning (Phase 3)
Now supports week_pattern for rotating splits and week_number for per-week exercises.
"""
from datetime import date, datetime, timedelta
from db import get_supabase_client


# ============================================
# CYCLE QUERIES
# ============================================

def get_active_cycle(user_id: str):
    """Get the user's current active cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('status', 'active')\
        .order('start_date', desc=True)\
        .limit(1)\
        .execute()
    
    return response.data[0] if response.data else None


def get_cycle_by_id(cycle_id: str):
    """Get a cycle by ID with all related data."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .select('*')\
        .eq('id', cycle_id)\
        .single()\
        .execute()
    
    return response.data


def get_user_cycles(user_id: str, limit: int = 10):
    """Get all cycles for a user."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('start_date', desc=True)\
        .limit(limit)\
        .execute()
    
    return response.data


def create_cycle(user_id: str, name: str, start_date: date, length_weeks: int, 
                 split_type: str, copied_from: str = None):
    """Create a new cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles').insert({
        'user_id': user_id,
        'name': name,
        'start_date': start_date.isoformat(),
        'length_weeks': length_weeks,
        'split_type': split_type,
        'status': 'planning',
        'copied_from_cycle_id': copied_from
    }).execute()
    
    return response.data[0] if response.data else None


def activate_cycle(cycle_id: str):
    """Set a cycle to active status."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .update({'status': 'active'})\
        .eq('id', cycle_id)\
        .execute()
    
    return response.data[0] if response.data else None


def complete_cycle(cycle_id: str):
    """Mark a cycle as completed."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .update({
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat()
        })\
        .eq('id', cycle_id)\
        .execute()
    
    return response.data[0] if response.data else None


def get_previous_cycle(user_id: str):
    """Get the most recent completed cycle for a user."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycles')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('status', 'completed')\
        .order('completed_at', desc=True)\
        .limit(1)\
        .execute()
    
    return response.data[0] if response.data else None


# ============================================
# CYCLE WORKOUT SLOTS
# ============================================

def get_cycle_workout_slots(cycle_id: str):
    """Get all workout slots for a cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_workout_slots')\
        .select('*')\
        .eq('cycle_id', cycle_id)\
        .order('week_pattern', nullsfirst=True)\
        .order('day_of_week')\
        .order('order_index')\
        .execute()
    
    return response.data


def get_cycle_workout_slots_for_week(cycle_id: str, week_number: int, rotation_weeks: int = 1):
    """
    Get workout slots applicable to a specific week number.
    
    For rotating splits, filters by week_pattern:
    - 2-week rotation: odd/even
    - 3-week rotation: week_mod_0, week_mod_1, week_mod_2
    """
    supabase = get_supabase_client()
    
    if rotation_weeks == 1:
        # No rotation - all slots apply
        response = supabase.table('cycle_workout_slots')\
            .select('*')\
            .eq('cycle_id', cycle_id)\
            .order('day_of_week')\
            .order('order_index')\
            .execute()
    elif rotation_weeks == 2:
        # 2-week rotation (odd/even)
        pattern = 'odd' if week_number % 2 == 1 else 'even'
        response = supabase.table('cycle_workout_slots')\
            .select('*')\
            .eq('cycle_id', cycle_id)\
            .or_(f'week_pattern.is.null,week_pattern.eq.{pattern}')\
            .order('day_of_week')\
            .order('order_index')\
            .execute()
    else:
        # 3+ week rotation
        mod = week_number % rotation_weeks
        if mod == 0:
            mod = rotation_weeks  # Week 3 in 3-week rotation = mod_0, but we store as week_mod_0
        pattern = f'week_mod_{mod % rotation_weeks}'
        response = supabase.table('cycle_workout_slots')\
            .select('*')\
            .eq('cycle_id', cycle_id)\
            .or_(f'week_pattern.is.null,week_pattern.eq.{pattern}')\
            .order('day_of_week')\
            .order('order_index')\
            .execute()
    
    return response.data


def create_cycle_workout_slot(cycle_id: str, day_of_week: int, template_id: str,
                               workout_name: str, is_heavy_focus: list, order_index: int,
                               week_pattern: str = None):
    """Create a workout slot for a cycle."""
    supabase = get_supabase_client()
    
    data = {
        'cycle_id': cycle_id,
        'day_of_week': day_of_week,
        'template_id': template_id,
        'workout_name': workout_name,
        'is_heavy_focus': is_heavy_focus,
        'order_index': order_index
    }
    
    if week_pattern:
        data['week_pattern'] = week_pattern
    
    response = supabase.table('cycle_workout_slots').insert(data).execute()
    
    return response.data[0] if response.data else None


def update_cycle_workout_slot(slot_id: str, day_of_week: int):
    """Update a workout slot's day."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_workout_slots')\
        .update({'day_of_week': day_of_week})\
        .eq('id', slot_id)\
        .execute()
    
    return response.data[0] if response.data else None


# ============================================
# CYCLE EXERCISES
# ============================================

def get_cycle_exercises(cycle_id: str, slot_id: str = None, week_number: int = None):
    """
    Get exercises for a cycle, optionally filtered by slot and/or week.
    
    If week_number is provided, returns exercises where:
    - week_number matches exactly, OR
    - week_number is NULL (applies to all weeks)
    
    Week-specific exercises take precedence over NULL (all-weeks) exercises.
    """
    supabase = get_supabase_client()
    
    query = supabase.table('cycle_exercises')\
        .select('*, exercises(*)')\
        .eq('cycle_id', cycle_id)\
        .order('order_index')
    
    if slot_id:
        query = query.eq('cycle_workout_slot_id', slot_id)
    
    if week_number is not None:
        # Get exercises for this specific week OR exercises that apply to all weeks
        query = query.or_(f'week_number.is.null,week_number.eq.{week_number}')
    
    response = query.execute()
    exercises = response.data or []
    
    # If we have week-specific filtering, deduplicate by preferring week-specific over NULL
    if week_number is not None and exercises:
        # Group by (slot_id, order_index) and prefer week-specific
        seen = {}
        for ex in exercises:
            key = (ex.get('cycle_workout_slot_id'), ex.get('order_index'))
            existing = seen.get(key)
            if existing is None:
                seen[key] = ex
            elif ex.get('week_number') is not None and existing.get('week_number') is None:
                # Prefer week-specific over generic
                seen[key] = ex
        exercises = list(seen.values())
        exercises.sort(key=lambda x: x.get('order_index', 0))
    
    return exercises


def get_cycle_exercises_for_week(cycle_id: str, slot_id: str, week_number: int):
    """
    Get exercises for a specific workout slot and week.
    Returns week-specific exercises if they exist, otherwise falls back to all-weeks exercises.
    """
    supabase = get_supabase_client()
    
    # First try to get week-specific exercises
    response = supabase.table('cycle_exercises')\
        .select('*, exercises(*)')\
        .eq('cycle_id', cycle_id)\
        .eq('cycle_workout_slot_id', slot_id)\
        .eq('week_number', week_number)\
        .order('order_index')\
        .execute()
    
    if response.data:
        return response.data
    
    # Fall back to all-weeks exercises (week_number is NULL)
    response = supabase.table('cycle_exercises')\
        .select('*, exercises(*)')\
        .eq('cycle_id', cycle_id)\
        .eq('cycle_workout_slot_id', slot_id)\
        .is_('week_number', 'null')\
        .order('order_index')\
        .execute()
    
    return response.data or []


def create_cycle_exercise(cycle_id: str, slot_id: str, exercise_id: str, 
                          exercise_name: str, muscle_group: str, is_heavy: bool,
                          order_index: int, sets_heavy: int = 4, sets_light: int = 3,
                          rep_range_heavy: str = '6-8', rep_range_light: str = '10-12',
                          rest_heavy: int = 180, rest_light: int = 90,
                          week_number: int = None):
    """
    Add an exercise to a cycle.
    
    If week_number is None, the exercise applies to all weeks.
    If week_number is specified (1-8), the exercise only applies to that week.
    """
    supabase = get_supabase_client()
    
    data = {
        'cycle_id': cycle_id,
        'cycle_workout_slot_id': slot_id,
        'exercise_id': exercise_id,
        'exercise_name': exercise_name,
        'muscle_group': muscle_group,
        'is_heavy': is_heavy,
        'order_index': order_index,
        'sets_heavy': sets_heavy,
        'sets_light': sets_light,
        'rep_range_heavy': rep_range_heavy,
        'rep_range_light': rep_range_light,
        'rest_seconds_heavy': rest_heavy,
        'rest_seconds_light': rest_light
    }
    
    if week_number is not None:
        data['week_number'] = week_number
    
    response = supabase.table('cycle_exercises').insert(data).execute()
    
    return response.data[0] if response.data else None


def create_cycle_exercises_bulk(exercises: list):
    """
    Bulk insert multiple cycle exercises in a single database call.
    
    Args:
        exercises: List of dicts, each containing:
            - cycle_id, cycle_workout_slot_id, exercise_id, exercise_name,
            - muscle_group, is_heavy, order_index, sets_heavy, sets_light,
            - rep_range_heavy, rep_range_light, rest_seconds_heavy, rest_seconds_light,
            - week_number (optional)
    
    Returns:
        List of created exercise records
    """
    if not exercises:
        return []
    
    supabase = get_supabase_client()
    
    # Normalize the data structure for each exercise
    insert_data = []
    for ex in exercises:
        data = {
            'cycle_id': ex['cycle_id'],
            'cycle_workout_slot_id': ex['slot_id'],
            'exercise_id': ex['exercise_id'],
            'exercise_name': ex['exercise_name'],
            'muscle_group': ex.get('muscle_group', ''),
            'is_heavy': ex.get('is_heavy', False),
            'order_index': ex.get('order_index', 0),
            'sets_heavy': ex.get('sets_heavy', 4),
            'sets_light': ex.get('sets_light', 3),
            'rep_range_heavy': ex.get('rep_range_heavy', '6-8'),
            'rep_range_light': ex.get('rep_range_light', '10-12'),
            'rest_seconds_heavy': ex.get('rest_heavy', 180),
            'rest_seconds_light': ex.get('rest_light', 90)
        }
        
        if ex.get('week_number') is not None:
            data['week_number'] = ex['week_number']
        
        insert_data.append(data)
    
    response = supabase.table('cycle_exercises').insert(insert_data).execute()
    
    return response.data or []


def update_cycle_exercise(exercise_id: str, updates: dict):
    """Update a cycle exercise."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_exercises')\
        .update(updates)\
        .eq('id', exercise_id)\
        .execute()
    
    return response.data[0] if response.data else None


def delete_cycle_exercise(exercise_id: str):
    """Remove an exercise from a cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_exercises')\
        .delete()\
        .eq('id', exercise_id)\
        .execute()
    
    return response.data


def delete_cycle_exercises_for_week(cycle_id: str, slot_id: str, week_number: int):
    """Delete all exercises for a specific slot and week."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_exercises')\
        .delete()\
        .eq('cycle_id', cycle_id)\
        .eq('cycle_workout_slot_id', slot_id)\
        .eq('week_number', week_number)\
        .execute()
    
    return response.data


def swap_cycle_exercise(cycle_exercise_id: str, new_exercise_id: str, new_exercise_name: str):
    """Swap one exercise for another in a cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('cycle_exercises')\
        .update({
            'exercise_id': new_exercise_id,
            'exercise_name': new_exercise_name
        })\
        .eq('id', cycle_exercise_id)\
        .execute()
    
    return response.data[0] if response.data else None


# ============================================
# SCHEDULED WORKOUTS
# ============================================

def get_scheduled_workouts_for_week(user_id: str, week_start: date):
    """Get scheduled workouts for a specific week."""
    supabase = get_supabase_client()
    
    week_end = week_start + timedelta(days=6)
    
    response = supabase.table('scheduled_workouts')\
        .select('*, cycle_workout_slots(*)')\
        .eq('user_id', user_id)\
        .gte('scheduled_date', week_start.isoformat())\
        .lte('scheduled_date', week_end.isoformat())\
        .order('scheduled_date')\
        .execute()
    
    return response.data


def get_scheduled_workouts_for_cycle(cycle_id: str):
    """Get all scheduled workouts for a cycle."""
    supabase = get_supabase_client()
    
    response = supabase.table('scheduled_workouts')\
        .select('*, cycle_workout_slots(*)')\
        .eq('cycle_id', cycle_id)\
        .order('scheduled_date')\
        .execute()
    
    return response.data


def create_scheduled_workout(user_id: str, cycle_id: str, slot_id: str, 
                             scheduled_date: date, week_number: int):
    """Create a scheduled workout entry."""
    supabase = get_supabase_client()
    
    response = supabase.table('scheduled_workouts').insert({
        'user_id': user_id,
        'cycle_id': cycle_id,
        'cycle_workout_slot_id': slot_id,
        'scheduled_date': scheduled_date.isoformat(),
        'week_number': week_number,
        'status': 'scheduled'
    }).execute()
    
    return response.data[0] if response.data else None


def reschedule_workout(scheduled_id: str, new_date: date):
    """Reschedule a workout to a different date."""
    supabase = get_supabase_client()
    
    response = supabase.table('scheduled_workouts')\
        .update({
            'scheduled_date': new_date.isoformat(),
            'status': 'rescheduled',
            'updated_at': datetime.utcnow().isoformat()
        })\
        .eq('id', scheduled_id)\
        .execute()
    
    return response.data[0] if response.data else None


def complete_scheduled_workout(scheduled_id: str, user_workout_id: str):
    """Mark a scheduled workout as completed and link to actual workout."""
    supabase = get_supabase_client()
    
    response = supabase.table('scheduled_workouts')\
        .update({
            'status': 'completed',
            'user_workout_id': user_workout_id,
            'updated_at': datetime.utcnow().isoformat()
        })\
        .eq('id', scheduled_id)\
        .execute()
    
    return response.data[0] if response.data else None


def skip_scheduled_workout(scheduled_id: str, notes: str = None):
    """Mark a scheduled workout as skipped."""
    supabase = get_supabase_client()
    
    update_data = {
        'status': 'skipped',
        'updated_at': datetime.utcnow().isoformat()
    }
    if notes:
        update_data['notes'] = notes
    
    response = supabase.table('scheduled_workouts')\
        .update(update_data)\
        .eq('id', scheduled_id)\
        .execute()
    
    return response.data[0] if response.data else None


def generate_cycle_schedule(user_id: str, cycle_id: str, start_date: date, 
                            length_weeks: int, workout_slots: list, rotation_weeks: int = 1):
    """
    Generate all scheduled workouts for a cycle.
    
    For rotating splits, only schedules workouts from slots that match the week's pattern.
    """
    supabase = get_supabase_client()
    
    scheduled = []
    
    for week_num in range(1, length_weeks + 1):
        week_start = start_date + timedelta(weeks=week_num - 1)
        
        # Determine which week_pattern applies to this week
        if rotation_weeks == 1:
            applicable_pattern = None
        elif rotation_weeks == 2:
            applicable_pattern = 'odd' if week_num % 2 == 1 else 'even'
        else:
            mod = week_num % rotation_weeks
            applicable_pattern = f'week_mod_{mod}'
        
        for slot in workout_slots:
            slot_pattern = slot.get('week_pattern')
            
            # Check if this slot applies to this week
            if slot_pattern is not None and applicable_pattern is not None:
                if slot_pattern != applicable_pattern:
                    continue  # Skip this slot for this week
            
            # Calculate the actual date for this workout
            # Find Monday of this week, then add day_of_week
            week_monday = week_start - timedelta(days=week_start.weekday())
            workout_date = week_monday + timedelta(days=slot['day_of_week'])
            
            scheduled.append({
                'user_id': user_id,
                'cycle_id': cycle_id,
                'cycle_workout_slot_id': slot['id'],
                'scheduled_date': workout_date.isoformat(),
                'week_number': week_num,
                'status': 'scheduled'
            })
    
    if scheduled:
        response = supabase.table('scheduled_workouts').insert(scheduled).execute()
        return response.data
    
    return []


# ============================================
# WEIGHT SUGGESTIONS
# ============================================

def get_weight_suggestion(user_id: str, exercise_id: str, cycle_id: str = None, 
                          week_number: int = None, is_heavy: bool = None):
    """Get weight suggestion for an exercise."""
    supabase = get_supabase_client()
    
    query = supabase.table('weight_suggestions')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('exercise_id', exercise_id)
    
    if cycle_id:
        query = query.eq('cycle_id', cycle_id)
    if week_number:
        query = query.eq('week_number', week_number)
    if is_heavy is not None:
        query = query.eq('is_heavy', is_heavy)
    
    response = query.order('created_at', desc=True).limit(1).execute()
    
    return response.data[0] if response.data else None


def create_weight_suggestion(user_id: str, cycle_id: str, exercise_id: str,
                             week_number: int, suggested_weight: float,
                             is_heavy: bool, based_on_workout_id: str = None):
    """Create a weight suggestion."""
    supabase = get_supabase_client()
    
    response = supabase.table('weight_suggestions').insert({
        'user_id': user_id,
        'cycle_id': cycle_id,
        'exercise_id': exercise_id,
        'week_number': week_number,
        'suggested_weight': suggested_weight,
        'is_heavy': is_heavy,
        'based_on_workout_id': based_on_workout_id
    }).execute()
    
    return response.data[0] if response.data else None


def calculate_weight_progression(last_weight: float, reps_achieved: int, 
                                 target_reps_low: int, target_reps_high: int,
                                 is_heavy: bool = False) -> float:
    """
    Calculate suggested weight for next workout based on performance.
    
    Logic:
    - If achieved reps >= target_reps_high: increase weight
    - If achieved reps < target_reps_low: keep same or decrease
    - Otherwise: keep same weight
    
    Heavy exercises: +5 lbs increments
    Light exercises: +2.5 lbs increments
    """
    if last_weight is None or reps_achieved is None:
        return last_weight
    
    increment = 5.0 if is_heavy else 2.5
    
    if reps_achieved >= target_reps_high:
        return last_weight + increment
    elif reps_achieved < target_reps_low:
        # Keep same weight to try again, or decrease if really struggling
        if reps_achieved < target_reps_low - 2:
            return max(last_weight - increment, 0)
        return last_weight
    else:
        return last_weight


# ============================================
# EXERCISE SUBSTITUTION
# ============================================

def get_exercise_substitutions(exercise_id: str, muscle_group: str, 
                               equipment: str = None, limit: int = 10):
    """
    Get substitute exercises for a given exercise.
    Prioritizes same equipment, then shows other options.
    """
    supabase = get_supabase_client()
    
    # Get exercises with same muscle group, excluding the current one
    response = supabase.table('exercises')\
        .select('*')\
        .eq('muscle_group', muscle_group)\
        .neq('id', exercise_id)\
        .execute()
    
    exercises = response.data or []
    
    # Sort: same equipment first, then others
    if equipment:
        same_equipment = [e for e in exercises if e.get('equipment') == equipment]
        diff_equipment = [e for e in exercises if e.get('equipment') != equipment]
        exercises = same_equipment + diff_equipment
    
    return exercises[:limit]


# ============================================
# PROFILE UPDATES
# ============================================

def update_profile_training_settings(user_id: str, split_type: str = None,
                                     days_per_week: int = None,
                                     cycle_length_weeks: int = None,
                                     preferred_days: list = None,
                                     pr_rep_threshold: int = None,  
                                     email: str = None):
    """Update user's training preferences. Creates profile if it doesn't exist."""
    supabase = get_supabase_client()
    
    updates = {}
    if split_type is not None:
        updates['split_type'] = split_type
    if days_per_week is not None:
        updates['days_per_week'] = days_per_week
    if cycle_length_weeks is not None:
        updates['cycle_length_weeks'] = cycle_length_weeks
    if pr_rep_threshold is not None:
        updates['pr_rep_threshold'] = pr_rep_threshold
    if preferred_days is not None:
        # Supabase Python client handles list -> JSONB conversion automatically
        updates['preferred_days'] = preferred_days
    
    if not updates:
        return {'message': 'No updates provided'}
    
    print(f"Updating profile {user_id} with: {updates}")
    
    try:
        # First check if profile exists
        check_response = supabase.table('profiles')\
            .select('id')\
            .eq('id', user_id)\
            .execute()
        
        if not check_response.data:
            # Profile doesn't exist - create it with the updates
            print(f"Profile doesn't exist, creating new profile for {user_id}")
            create_data = {
                'id': user_id,
                'email': email,
                'display_name': email.split('@')[0] if email else 'User',
                **updates
            }
            response = supabase.table('profiles').insert(create_data).execute()
        else:
            # Profile exists - update it
            response = supabase.table('profiles')\
                .update(updates)\
                .eq('id', user_id)\
                .execute()
        
        print(f"Profile operation response: {response}")
        
        if response.data:
            return response.data[0]
        else:
            # Fetch the profile to return it
            fetch_response = supabase.table('profiles')\
                .select('*')\
                .eq('id', user_id)\
                .single()\
                .execute()
            return fetch_response.data if fetch_response.data else {'updated': True}
            
    except Exception as e:
        print(f"Database error in update_profile_training_settings: {e}")
        raise e


# ============================================
# HELPER: Get next workout suggestion
# ============================================

def get_next_workout_suggestion(user_id: str):
    """
    Determine what workout the user should do next based on:
    1. Active cycle schedule
    2. What was last completed
    3. Days since last workout
    """
    from datetime import date
    
    # Get active cycle
    cycle = get_active_cycle(user_id)
    if not cycle:
        return None
    
    # Get today's date
    today = date.today()
    
    # Get scheduled workouts from today forward
    supabase = get_supabase_client()
    
    response = supabase.table('scheduled_workouts')\
        .select('*, cycle_workout_slots(*)')\
        .eq('cycle_id', cycle['id'])\
        .eq('status', 'scheduled')\
        .gte('scheduled_date', today.isoformat())\
        .order('scheduled_date')\
        .limit(1)\
        .execute()
    
    if response.data:
        return response.data[0]
    
    return None


# ============================================
# COPY CYCLE
# ============================================

def copy_cycle(user_id: str, source_cycle_id: str, new_name: str, 
               new_start_date: date, new_length_weeks: int = None):
    """
    Create a new cycle by copying from a previous one.
    Copies workout slots and exercises (including per-week exercises).
    """
    # Get source cycle
    source = get_cycle_by_id(source_cycle_id)
    if not source:
        return None
    
    # Create new cycle
    new_cycle = create_cycle(
        user_id=user_id,
        name=new_name,
        start_date=new_start_date,
        length_weeks=new_length_weeks or source['length_weeks'],
        split_type=source['split_type'],
        copied_from=source_cycle_id
    )
    
    if not new_cycle:
        return None
    
    # Copy workout slots
    source_slots = get_cycle_workout_slots(source_cycle_id)
    slot_mapping = {}  # old_id -> new_id
    
    for slot in source_slots:
        new_slot = create_cycle_workout_slot(
            cycle_id=new_cycle['id'],
            day_of_week=slot['day_of_week'],
            template_id=slot['template_id'],
            workout_name=slot['workout_name'],
            is_heavy_focus=slot['is_heavy_focus'],
            order_index=slot['order_index'],
            week_pattern=slot.get('week_pattern')
        )
        if new_slot:
            slot_mapping[slot['id']] = new_slot['id']
    
    # Copy exercises (including week_number)
    source_exercises = get_cycle_exercises(source_cycle_id)
    
    for ex in source_exercises:
        new_slot_id = slot_mapping.get(ex['cycle_workout_slot_id'])
        if new_slot_id:
            create_cycle_exercise(
                cycle_id=new_cycle['id'],
                slot_id=new_slot_id,
                exercise_id=ex['exercise_id'],
                exercise_name=ex['exercise_name'],
                muscle_group=ex['muscle_group'],
                is_heavy=ex['is_heavy'],
                order_index=ex['order_index'],
                sets_heavy=ex['sets_heavy'],
                sets_light=ex['sets_light'],
                rep_range_heavy=ex['rep_range_heavy'],
                rep_range_light=ex['rep_range_light'],
                rest_heavy=ex['rest_seconds_heavy'],
                rest_light=ex['rest_seconds_light'],
                week_number=ex.get('week_number')  # Preserve week-specific exercises
            )
    
    return new_cycle