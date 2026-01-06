"""
Database functions for progress tracking (Phase 4)
"""
from datetime import date, datetime, timedelta
from db import get_supabase_client


# ============================================
# STRENGTH PROGRESS QUERIES
# ============================================

def get_exercise_history(user_id: str, exercise_ids: list, start_date: date = None, end_date: date = None):
    """
    Get weight/rep history for specific exercises over time.
    Returns data suitable for line charts.
    
    Args:
        user_id: User's ID
        exercise_ids: List of exercise UUIDs to fetch
        start_date: Start of date range (optional)
        end_date: End of date range (optional)
    
    Returns:
        List of records with exercise_id, exercise_name, date, weight, reps, set_number
    """
    supabase = get_supabase_client()
    
    # Build query to join workout_sets with user_workouts
    query = supabase.table('workout_sets')\
        .select('exercise_id, exercise_name, weight, reps, set_number, user_workouts!inner(user_id, completed_at)')\
        .in_('exercise_id', exercise_ids)\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .not_.is_('user_workouts.completed_at', 'null')
    
    if start_date:
        query = query.gte('user_workouts.completed_at', start_date.isoformat())
    if end_date:
        query = query.lte('user_workouts.completed_at', end_date.isoformat())
    
    # Note: Can't order by joined table column in PostgREST, so we sort in Python
    response = query.execute()
    
    # Format results
    results = []
    for row in response.data or []:
        workout_data = row.get('user_workouts', {})
        results.append({
            'exercise_id': row['exercise_id'],
            'exercise_name': row['exercise_name'],
            'date': workout_data.get('completed_at', '')[:10] if workout_data.get('completed_at') else None,
            'weight': row['weight'],
            'reps': row['reps'],
            'set_number': row['set_number']
        })
    
    # Sort by date in Python
    results.sort(key=lambda x: x['date'] or '')
    
    return results


def get_exercise_progress_summary(user_id: str, exercise_id: str, start_date: date = None, end_date: date = None):
    """
    Get aggregated progress for a single exercise.
    Returns best weight per workout session for charting.
    """
    supabase = get_supabase_client()
    
    # Get all sets for this exercise
    query = supabase.table('workout_sets')\
        .select('weight, reps, user_workouts!inner(user_id, completed_at)')\
        .eq('exercise_id', exercise_id)\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .not_.is_('user_workouts.completed_at', 'null')
    
    if start_date:
        query = query.gte('user_workouts.completed_at', start_date.isoformat())
    if end_date:
        query = query.lte('user_workouts.completed_at', end_date.isoformat())
    
    response = query.order('user_workouts.completed_at').execute()
    
    # Group by date and get max weight per session
    sessions = {}
    for row in response.data or []:
        workout_data = row.get('user_workouts', {})
        date_str = workout_data.get('completed_at', '')[:10] if workout_data.get('completed_at') else None
        if date_str:
            if date_str not in sessions:
                sessions[date_str] = {'max_weight': 0, 'total_volume': 0, 'sets': 0}
            
            weight = row['weight'] or 0
            reps = row['reps'] or 0
            
            sessions[date_str]['max_weight'] = max(sessions[date_str]['max_weight'], weight)
            sessions[date_str]['total_volume'] += weight * reps
            sessions[date_str]['sets'] += 1
    
    # Convert to sorted list
    return [{'date': d, **v} for d, v in sorted(sessions.items())]


def get_user_exercises(user_id: str, limit: int = 100):
    """
    Get list of exercises the user has performed, with counts and metadata.
    Useful for populating exercise selector in strength chart.
    Returns exercises with muscle_group and is_compound for filtering.
    """
    supabase = get_supabase_client()
    
    # Get distinct exercises from user's workout sets
    response = supabase.table('workout_sets')\
        .select('exercise_id, exercise_name, user_workouts!inner(user_id)')\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .execute()
    
    # Count and deduplicate
    exercise_counts = {}
    for row in response.data or []:
        ex_id = row['exercise_id']
        if ex_id not in exercise_counts:
            exercise_counts[ex_id] = {
                'id': ex_id,
                'name': row['exercise_name'],
                'count': 0,
                'muscle_group': None,
                'is_compound': False
            }
        exercise_counts[ex_id]['count'] += 1
    
    # Fetch exercise metadata (muscle_group, is_compound) for all found exercises
    if exercise_counts:
        exercise_ids = list(exercise_counts.keys())
        exercises_response = supabase.table('exercises')\
            .select('id, muscle_group, is_compound')\
            .in_('id', exercise_ids)\
            .execute()
        
        # Merge metadata
        for ex in exercises_response.data or []:
            if ex['id'] in exercise_counts:
                exercise_counts[ex['id']]['muscle_group'] = ex.get('muscle_group')
                exercise_counts[ex['id']]['is_compound'] = ex.get('is_compound', False)
    
    # Sort by count (most used first) and return
    return sorted(exercise_counts.values(), key=lambda x: -x['count'])[:limit]


# ============================================
# VOLUME TRACKING QUERIES
# ============================================

def get_volume_by_workout_type(user_id: str, start_date: date = None, end_date: date = None):
    """
    Calculate total volume (sets × reps × weight) per workout type over time.
    Groups by template_name (Push+Pull, Legs+Push, Pull+Legs, etc.)
    """
    supabase = get_supabase_client()
    
    # Get all completed workouts with their sets
    query = supabase.table('user_workouts')\
        .select('id, template_name, completed_at, workout_sets(weight, reps)')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')
    
    if start_date:
        query = query.gte('completed_at', start_date.isoformat())
    if end_date:
        query = query.lte('completed_at', end_date.isoformat())
    
    response = query.order('completed_at').execute()
    
    # Calculate volume per workout
    results = []
    for workout in response.data or []:
        total_volume = 0
        total_sets = 0
        
        for s in workout.get('workout_sets', []):
            weight = s.get('weight') or 0
            reps = s.get('reps') or 0
            total_volume += weight * reps
            total_sets += 1
        
        results.append({
            'date': workout['completed_at'][:10] if workout['completed_at'] else None,
            'workout_type': workout['template_name'] or 'Workout',
            'volume': total_volume,
            'sets': total_sets
        })
    
    return results


def get_volume_summary_by_week(user_id: str, weeks: int = 8):
    """
    Get weekly volume summaries grouped by workout type.
    Returns data for stacked bar chart.
    """
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)
    
    raw_data = get_volume_by_workout_type(user_id, start_date, end_date)
    
    # Group by week and workout type
    weeks_data = {}
    for row in raw_data:
        if not row['date']:
            continue
        
        workout_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
        # Get Monday of that week
        week_start = workout_date - timedelta(days=workout_date.weekday())
        week_key = week_start.isoformat()
        
        if week_key not in weeks_data:
            weeks_data[week_key] = {}
        
        workout_type = row['workout_type']
        if workout_type not in weeks_data[week_key]:
            weeks_data[week_key][workout_type] = 0
        
        weeks_data[week_key][workout_type] += row['volume']
    
    # Convert to list format
    return [{'week': k, **v} for k, v in sorted(weeks_data.items())]


# ============================================
# CONSISTENCY TRACKING QUERIES
# ============================================

def get_consistency_stats(user_id: str, start_date: date = None, end_date: date = None, target_days_per_week: int = 3):
    """
    Calculate workout consistency metrics.
    Returns completion rate based on actual workouts vs target days per week.
    Uses the user's first workout date as the baseline (not arbitrary timeframes).
    """
    supabase = get_supabase_client()
    
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)
    
    # Get completed workouts
    workouts_query = supabase.table('user_workouts')\
        .select('completed_at')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .gte('completed_at', start_date.isoformat())\
        .lte('completed_at', end_date.isoformat())\
        .order('completed_at')
    
    workouts_response = workouts_query.execute()
    completed_workouts = workouts_response.data or []
    
    if not completed_workouts:
        return {
            'completion_rate': 0,
            'total_workouts': 0,
            'target_workouts': 0,
            'weeks_active': 0,
            'total_weeks': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'calendar_data': {}
        }
    
    # Use the FIRST workout date as the actual start (not arbitrary timeframe)
    first_workout_str = completed_workouts[0]['completed_at'][:10]
    first_workout_date = datetime.strptime(first_workout_str, '%Y-%m-%d').date()
    
    # Effective start is the later of: timeframe start OR first workout
    effective_start = max(start_date, first_workout_date)
    
    # Calculate weeks from effective start to end
    total_weeks = max(1, ((end_date - effective_start).days // 7) + 1)
    
    # Calculate completion rate
    total_workouts = len(completed_workouts)
    target_workouts = total_weeks * target_days_per_week
    completion_rate = round((total_workouts / target_workouts * 100) if target_workouts > 0 else 0)
    completion_rate = min(100, completion_rate)
    
    # Group workouts by week for weeks_active count
    weeks_with_workouts = set()
    workout_dates = {}
    for w in completed_workouts:
        if w['completed_at']:
            date_str = w['completed_at'][:10]
            workout_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            week_start = workout_date - timedelta(days=workout_date.weekday())
            weeks_with_workouts.add(week_start.isoformat())
            workout_dates[date_str] = workout_dates.get(date_str, 0) + 1
    
    # Calculate streak
    streak = calculate_streak(user_id, supabase)
    
    return {
        'completion_rate': completion_rate,
        'total_workouts': total_workouts,
        'target_workouts': target_workouts,
        'weeks_active': len(weeks_with_workouts),
        'total_weeks': total_weeks,
        'current_streak': streak['current'],
        'longest_streak': streak['longest'],
        'calendar_data': workout_dates
    }


def calculate_streak(user_id: str, supabase=None):
    """
    Calculate current and longest workout streaks.
    A streak is consecutive weeks with at least one workout.
    """
    if not supabase:
        supabase = get_supabase_client()
    
    # Get all completed workout dates
    response = supabase.table('user_workouts')\
        .select('completed_at')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .order('completed_at', desc=True)\
        .execute()
    
    if not response.data:
        return {'current': 0, 'longest': 0}
    
    # Get unique weeks (week number of year)
    weeks_with_workout = set()
    for w in response.data:
        if w['completed_at']:
            workout_date = datetime.strptime(w['completed_at'][:10], '%Y-%m-%d').date()
            # Use ISO week number
            year_week = workout_date.isocalendar()[:2]  # (year, week)
            weeks_with_workout.add(year_week)
    
    if not weeks_with_workout:
        return {'current': 0, 'longest': 0}
    
    # Sort weeks
    sorted_weeks = sorted(weeks_with_workout, reverse=True)
    
    # Calculate current streak
    current_streak = 0
    today = date.today()
    current_year_week = today.isocalendar()[:2]
    
    # Check if current or last week has a workout
    last_week = (today - timedelta(weeks=1)).isocalendar()[:2]
    
    if current_year_week in weeks_with_workout or last_week in weeks_with_workout:
        # Count consecutive weeks backwards
        check_week = current_year_week if current_year_week in weeks_with_workout else last_week
        
        for year_week in sorted_weeks:
            if year_week == check_week:
                current_streak += 1
                # Move to previous week
                check_date = date.fromisocalendar(check_week[0], check_week[1], 1) - timedelta(weeks=1)
                check_week = check_date.isocalendar()[:2]
            elif year_week < check_week:
                break
    
    # Calculate longest streak
    longest_streak = 0
    current_count = 0
    prev_week = None
    
    for year_week in sorted(weeks_with_workout):
        if prev_week is None:
            current_count = 1
        else:
            # Check if consecutive
            prev_date = date.fromisocalendar(prev_week[0], prev_week[1], 1)
            curr_date = date.fromisocalendar(year_week[0], year_week[1], 1)
            diff = (curr_date - prev_date).days
            
            if diff <= 7:  # Consecutive weeks
                current_count += 1
            else:
                longest_streak = max(longest_streak, current_count)
                current_count = 1
        
        prev_week = year_week
    
    longest_streak = max(longest_streak, current_count)
    
    return {'current': current_streak, 'longest': longest_streak}


def get_calendar_heatmap_data(user_id: str, days: int = 365):
    """
    Get workout counts by day for calendar heatmap visualization.
    Returns dict mapping date strings to workout counts.
    Queries last N days (default 365) to match the heatmap display.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    supabase = get_supabase_client()
    
    response = supabase.table('user_workouts')\
        .select('completed_at')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .gte('completed_at', start_date.isoformat())\
        .lte('completed_at', end_date.isoformat())\
        .execute()
    
    # Count workouts per day
    counts = {}
    for w in response.data or []:
        date_str = w['completed_at'][:10] if w['completed_at'] else None
        if date_str:
            counts[date_str] = counts.get(date_str, 0) + 1
    
    return counts


# ============================================
# PERSONAL RECORDS QUERIES
# ============================================

def get_personal_records(user_id: str):
    """Get all current personal records for a user."""
    supabase = get_supabase_client()
    
    response = supabase.table('personal_records')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('achieved_at', desc=True)\
        .execute()
    
    return response.data or []


def check_and_update_pr(user_id: str, exercise_id: str, exercise_name: str, 
                        weight: float, reps: int, workout_set_id: str = None):
    """
    Check if a lift is a new PR and update records.
    Only counts as PR if:
    1. Reps <= user's pr_rep_threshold
    2. Weight > previous best for this exercise
    3. There WAS a previous record (first lift doesn't count)
    
    Returns: {'is_pr': bool, 'improvement': float or None, 'previous': float or None}
    """
    supabase = get_supabase_client()
    
    # Get user's PR threshold - FIXED: use limit(1) instead of single()
    try:
        profile_resp = supabase.table('profiles')\
            .select('pr_rep_threshold')\
            .eq('id', user_id)\
            .limit(1)\
            .execute()
        threshold = profile_resp.data[0].get('pr_rep_threshold', 5) if profile_resp.data else 5
    except Exception as e:
        print(f"Error getting PR threshold: {e}")
        threshold = 5  # Default fallback
    
    # Only count if reps are at or below threshold
    if reps > threshold:
        return {'is_pr': False, 'reason': 'reps_too_high'}
    
    # Get current PR for this exercise
    current_pr = supabase.table('personal_records')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('exercise_id', exercise_id)\
        .execute()
    
    current = current_pr.data[0] if current_pr.data else None
    
    # If no previous PR exists, record this as the baseline (but don't celebrate)
    if not current:
        supabase.table('personal_records').insert({
            'user_id': user_id,
            'exercise_id': exercise_id,
            'exercise_name': exercise_name,
            'weight': weight,
            'reps': reps,
            'achieved_at': datetime.utcnow().isoformat(),
            'workout_set_id': workout_set_id,
            'previous_record_weight': None
        }).execute()
        
        return {'is_pr': False, 'reason': 'first_record', 'weight': weight}
    
    # Check if this beats the current PR
    if weight > current['weight']:
        old_weight = current['weight']
        
        # Update the PR
        supabase.table('personal_records').update({
            'weight': weight,
            'reps': reps,
            'achieved_at': datetime.utcnow().isoformat(),
            'workout_set_id': workout_set_id,
            'previous_record_weight': old_weight
        }).eq('id', current['id']).execute()
        
        # Add to history
        supabase.table('pr_history').insert({
            'user_id': user_id,
            'exercise_id': exercise_id,
            'exercise_name': exercise_name,
            'weight': weight,
            'reps': reps,
            'achieved_at': datetime.utcnow().isoformat()
        }).execute()
        
        return {
            'is_pr': True,
            'improvement': weight - old_weight,
            'previous': old_weight,
            'new': weight
        }
    
    return {'is_pr': False, 'reason': 'not_heavier'}


def get_pr_history(user_id: str, exercise_id: str = None, limit: int = 50):
    """Get PR improvement history, optionally filtered by exercise."""
    supabase = get_supabase_client()
    
    query = supabase.table('pr_history')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('achieved_at', desc=True)\
        .limit(limit)
    
    if exercise_id:
        query = query.eq('exercise_id', exercise_id)
    
    response = query.execute()
    return response.data or []


def get_recent_prs(user_id: str, days: int = 30, limit: int = 10):
    """Get PRs achieved in the last N days."""
    supabase = get_supabase_client()
    
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    response = supabase.table('pr_history')\
        .select('*')\
        .eq('user_id', user_id)\
        .gte('achieved_at', since)\
        .order('achieved_at', desc=True)\
        .limit(limit)\
        .execute()
    
    return response.data or []


# ============================================
# DATE RANGE HELPERS
# ============================================

def get_cycle_date_range(user_id: str, cycle_id: str = None):
    """Get start and end dates for a cycle (or active cycle if not specified)."""
    supabase = get_supabase_client()
    
    try:
        if cycle_id:
            response = supabase.table('cycles')\
                .select('start_date, length_weeks')\
                .eq('id', cycle_id)\
                .limit(1)\
                .execute()
        else:
            response = supabase.table('cycles')\
                .select('start_date, length_weeks')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .limit(1)\
                .execute()
        
        if response.data and len(response.data) > 0:
            cycle = response.data[0]
            start = datetime.strptime(cycle['start_date'], '%Y-%m-%d').date()
            end = start + timedelta(weeks=cycle['length_weeks'])
            return start, end
    except Exception as e:
        print(f"Error getting cycle date range: {e}")
    
    return None, None


def get_date_range_for_timeframe(timeframe: str, user_id: str = None):
    """
    Convert timeframe string to date range.
    
    Args:
        timeframe: 'cycle', 'year', 'all'
        user_id: Required for 'cycle' timeframe
    
    Returns:
        (start_date, end_date) tuple
    """
    today = date.today()
    
    if timeframe == 'cycle' and user_id:
        start, end = get_cycle_date_range(user_id)
        if start:
            return start, min(end, today)
        # Fallback to last 8 weeks if no active cycle
        return today - timedelta(weeks=8), today
    
    elif timeframe == 'year':
        return today - timedelta(days=365), today
    
    else:  # 'all' or default
        return date(2020, 1, 1), today  # Arbitrary early date