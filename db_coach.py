"""
Database functions for AI Coach features
- Weight suggestions
- Deload/progression detection
- Week adaptation
"""
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from db import get_supabase_client


# ============================================
# WEIGHT SUGGESTION QUERIES
# ============================================

def get_recent_exercise_performance(user_id: str, exercise_id: str, limit: int = 3) -> List[Dict]:
    """
    Get last N completed sessions for an exercise.
    Returns session-level aggregates for weight suggestion calculation.
    """
    supabase = get_supabase_client()
    
    # Get sets grouped by workout session
    response = supabase.table('workout_sets')\
        .select('weight, reps, set_number, user_workouts!inner(id, completed_at, user_id)')\
        .eq('exercise_id', exercise_id)\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .not_.is_('user_workouts.completed_at', 'null')\
        .order('user_workouts.completed_at', desc=True)\
        .execute()
    
    if not response.data:
        return []
    
    # Group by workout session
    sessions = {}
    for row in response.data:
        workout_id = row['user_workouts']['id']
        completed_at = row['user_workouts']['completed_at']
        
        if workout_id not in sessions:
            sessions[workout_id] = {
                'workout_id': workout_id,
                'date': completed_at[:10] if completed_at else None,
                'sets': [],
                'max_weight': 0,
                'total_reps': 0,
                'working_weight': None  # Most common weight used
            }
        
        sessions[workout_id]['sets'].append({
            'weight': row['weight'],
            'reps': row['reps'],
            'set_number': row['set_number']
        })
        
        if row['weight'] and row['weight'] > sessions[workout_id]['max_weight']:
            sessions[workout_id]['max_weight'] = row['weight']
        
        if row['reps']:
            sessions[workout_id]['total_reps'] += row['reps']
    
    # Calculate working weight (mode of weights used) and avg reps
    for session in sessions.values():
        weights = [s['weight'] for s in session['sets'] if s['weight']]
        if weights:
            # Working weight = most common weight (mode)
            session['working_weight'] = max(set(weights), key=weights.count)
        
        reps = [s['reps'] for s in session['sets'] if s['reps']]
        session['avg_reps'] = sum(reps) / len(reps) if reps else 0
        session['set_count'] = len(session['sets'])
    
    # Sort by date descending and limit
    sorted_sessions = sorted(sessions.values(), key=lambda x: x['date'] or '', reverse=True)
    return sorted_sessions[:limit]


def get_cached_weight_suggestion(user_id: str, exercise_id: str) -> Optional[Dict]:
    """Get cached weight suggestion if still valid."""
    supabase = get_supabase_client()
    
    response = supabase.table('weight_suggestion_cache')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('exercise_id', exercise_id)\
        .gt('valid_until', datetime.utcnow().isoformat())\
        .limit(1)\
        .execute()
    
    return response.data[0] if response.data else None


def cache_weight_suggestion(user_id: str, exercise_id: str, suggestion: Dict) -> Dict:
    """Cache a weight suggestion for 24 hours."""
    supabase = get_supabase_client()
    
    data = {
        'user_id': user_id,
        'exercise_id': exercise_id,
        'suggested_weight': suggestion.get('suggested_weight'),
        'suggestion_reason': suggestion.get('reason'),
        'confidence': suggestion.get('confidence', 'medium'),
        'based_on_sessions': suggestion.get('based_on_sessions', 0),
        'last_weight': suggestion.get('last_weight'),
        'last_reps': suggestion.get('last_reps'),
        'target_rep_range': suggestion.get('target_rep_range'),
        'valid_until': (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    
    # Upsert (update if exists, insert if not)
    response = supabase.table('weight_suggestion_cache')\
        .upsert(data, on_conflict='user_id,exercise_id')\
        .execute()
    
    return response.data[0] if response.data else data


# ============================================
# PROGRESS DETECTION QUERIES  
# ============================================

def get_weekly_training_summary(user_id: str, weeks_back: int = 4) -> List[Dict]:
    """
    Get weekly training summaries for trend analysis.
    Returns volume, completion rate, and compound lift performance per week.
    """
    supabase = get_supabase_client()
    
    start_date = (datetime.utcnow() - timedelta(weeks=weeks_back)).isoformat()
    
    # Get all completed workouts in period
    response = supabase.table('user_workouts')\
        .select('id, completed_at, template_name')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .gte('completed_at', start_date)\
        .order('completed_at')\
        .execute()
    
    if not response.data:
        return []
    
    # Get sets for these workouts
    workout_ids = [w['id'] for w in response.data]
    
    sets_response = supabase.table('workout_sets')\
        .select('user_workout_id, exercise_id, exercise_name, weight, reps, completed')\
        .in_('user_workout_id', workout_ids)\
        .eq('completed', True)\
        .execute()
    
    # Group by week
    weeks = {}
    for workout in response.data:
        completed_at = datetime.fromisoformat(workout['completed_at'].replace('Z', '+00:00'))
        week_start = completed_at - timedelta(days=completed_at.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key not in weeks:
            weeks[week_key] = {
                'week_start': week_key,
                'workouts_completed': 0,
                'total_sets': 0,
                'total_volume': 0,  # weight * reps
                'exercises': {}
            }
        
        weeks[week_key]['workouts_completed'] += 1
    
    # Add set data to weeks
    workout_dates = {w['id']: w['completed_at'] for w in response.data}
    for s in sets_response.data or []:
        workout_id = s['user_workout_id']
        if workout_id not in workout_dates:
            continue
            
        completed_at = datetime.fromisoformat(workout_dates[workout_id].replace('Z', '+00:00'))
        week_start = completed_at - timedelta(days=completed_at.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key in weeks:
            weeks[week_key]['total_sets'] += 1
            weight = s['weight'] or 0
            reps = s['reps'] or 0
            weeks[week_key]['total_volume'] += weight * reps
            
            # Track per-exercise max weights
            ex_name = s['exercise_name']
            if ex_name not in weeks[week_key]['exercises']:
                weeks[week_key]['exercises'][ex_name] = {'max_weight': 0, 'exercise_id': s['exercise_id']}
            if weight > weeks[week_key]['exercises'][ex_name]['max_weight']:
                weeks[week_key]['exercises'][ex_name]['max_weight'] = weight
    
    return sorted(weeks.values(), key=lambda x: x['week_start'], reverse=True)


def get_compound_lift_trends(user_id: str, weeks_back: int = 4) -> Dict[str, List[Dict]]:
    """
    Get weight trends for compound lifts to detect plateaus.
    Returns max weight per session for each compound exercise.
    """
    supabase = get_supabase_client()
    
    start_date = (datetime.utcnow() - timedelta(weeks=weeks_back)).isoformat()
    
    # Get compound exercises the user has done
    response = supabase.table('workout_sets')\
        .select('exercise_id, exercise_name, weight, user_workouts!inner(user_id, completed_at)')\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .not_.is_('user_workouts.completed_at', 'null')\
        .gte('user_workouts.completed_at', start_date)\
        .execute()
    
    if not response.data:
        return {}
    
    # Get which exercises are compound
    exercise_ids = list(set(r['exercise_id'] for r in response.data if r['exercise_id']))
    if not exercise_ids:
        return {}
        
    exercises_response = supabase.table('exercises')\
        .select('id, name, is_compound')\
        .in_('id', exercise_ids)\
        .eq('is_compound', True)\
        .execute()
    
    compound_ids = {e['id'] for e in exercises_response.data or []}
    
    # Group by exercise and session
    trends = {}
    for row in response.data:
        if row['exercise_id'] not in compound_ids:
            continue
            
        ex_name = row['exercise_name']
        session_date = row['user_workouts']['completed_at'][:10]
        
        if ex_name not in trends:
            trends[ex_name] = {}
        
        if session_date not in trends[ex_name]:
            trends[ex_name][session_date] = {'date': session_date, 'max_weight': 0}
        
        weight = row['weight'] or 0
        if weight > trends[ex_name][session_date]['max_weight']:
            trends[ex_name][session_date]['max_weight'] = weight
    
    # Convert to sorted lists
    return {
        ex: sorted(sessions.values(), key=lambda x: x['date'])
        for ex, sessions in trends.items()
    }


def get_current_week_status(user_id: str, cycle_id: str = None) -> Dict:
    """
    Get current week's workout status for adaptation suggestions.
    """
    supabase = get_supabase_client()
    
    # Get current week boundaries (Monday to Sunday)
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    result = {
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'today': today.isoformat(),
        'day_of_week': today.weekday(),  # 0=Monday
        'days_remaining': (week_end - today).days,
        'scheduled': [],
        'completed': [],
        'skipped': [],
        'remaining': []
    }
    
    if not cycle_id:
        return result
    
    # Get scheduled workouts for this week
    scheduled_response = supabase.table('scheduled_workouts')\
        .select('*, cycle_workout_slots(workout_name, is_heavy_focus)')\
        .eq('cycle_id', cycle_id)\
        .gte('scheduled_date', week_start.isoformat())\
        .lte('scheduled_date', week_end.isoformat())\
        .order('scheduled_date')\
        .execute()
    
    for sw in scheduled_response.data or []:
        workout_info = {
            'id': sw['id'],
            'scheduled_date': sw['scheduled_date'],
            'status': sw['status'],
            'name': sw.get('cycle_workout_slots', {}).get('workout_name', 'Workout'),
            'is_heavy': sw.get('cycle_workout_slots', {}).get('is_heavy_focus', True)
        }
        
        result['scheduled'].append(workout_info)
        
        if sw['status'] == 'completed':
            result['completed'].append(workout_info)
        elif sw['status'] == 'skipped':
            result['skipped'].append(workout_info)
        else:
            # Parse the scheduled date for comparison
            scheduled_date_str = sw['scheduled_date'][:10]  # Get just 'YYYY-MM-DD'
            
            if scheduled_date_str < today.isoformat():
                # Scheduled date is BEFORE today = actually missed
                if 'missed' not in result:
                    result['missed'] = []
                result['missed'].append(workout_info)
            
            result['remaining'].append(workout_info)
    
    return result


def get_muscle_coverage_this_week(user_id: str, cycle_id: str = None) -> Dict:
    """
    Analyze which muscle groups have been trained this week.
    """
    supabase = get_supabase_client()
    
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    
    # Get completed workouts this week
    response = supabase.table('workout_sets')\
        .select('exercise_name, user_workouts!inner(user_id, completed_at)')\
        .eq('user_workouts.user_id', user_id)\
        .eq('completed', True)\
        .not_.is_('user_workouts.completed_at', 'null')\
        .gte('user_workouts.completed_at', week_start.isoformat())\
        .execute()
    
    # Map exercises to muscle groups
    exercise_names = list(set(r['exercise_name'] for r in response.data or [] if r['exercise_name']))
    
    muscle_hits = {
        'chest': 0, 'back': 0, 'shoulders': 0, 
        'biceps': 0, 'triceps': 0, 'quads': 0,
        'hamstrings': 0, 'glutes': 0, 'calves': 0
    }
    
    if exercise_names:
        exercises_response = supabase.table('exercises')\
            .select('name, muscle_group')\
            .in_('name', exercise_names)\
            .execute()
        
        ex_to_muscle = {e['name']: e['muscle_group'] for e in exercises_response.data or []}
        
        for row in response.data or []:
            muscle = ex_to_muscle.get(row['exercise_name'])
            if muscle and muscle in muscle_hits:
                muscle_hits[muscle] += 1
    
    return {
        'hits': muscle_hits,
        'trained': [m for m, count in muscle_hits.items() if count > 0],
        'untrained': [m for m, count in muscle_hits.items() if count == 0]
    }


# ============================================
# COACH RECOMMENDATION QUERIES
# ============================================

def get_pending_recommendation(user_id: str, cycle_id: str = None) -> Optional[Dict]:
    """Get any pending coach recommendation for the user."""
    supabase = get_supabase_client()
    
    query = supabase.table('coach_recommendations')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('status', 'pending')\
        .gt('expires_at', datetime.utcnow().isoformat())
    
    if cycle_id:
        query = query.eq('cycle_id', cycle_id)
    
    response = query.order('created_at', desc=True).limit(1).execute()
    return response.data[0] if response.data else None


def create_recommendation(user_id: str, cycle_id: str, rec_type: str, 
                         signals: List[Dict], prescription: Dict,
                         model: str = None, tokens: int = None) -> Dict:
    """Create a new coach recommendation."""
    supabase = get_supabase_client()
    
    response = supabase.table('coach_recommendations').insert({
        'user_id': user_id,
        'cycle_id': cycle_id,
        'recommendation_type': rec_type,
        'signals_detected': signals,
        'prescription': prescription,
        'ai_model': model,
        'tokens_used': tokens
    }).execute()
    
    return response.data[0] if response.data else None


def update_recommendation_status(recommendation_id: str, status: str) -> Dict:
    """Update recommendation status (applied, dismissed)."""
    supabase = get_supabase_client()
    
    update_data = {'status': status}
    if status == 'applied':
        update_data['applied_at'] = datetime.utcnow().isoformat()
    elif status == 'dismissed':
        update_data['dismissed_at'] = datetime.utcnow().isoformat()
    
    response = supabase.table('coach_recommendations')\
        .update(update_data)\
        .eq('id', recommendation_id)\
        .execute()
    
    return response.data[0] if response.data else None


# ============================================
# ADAPTED WORKOUT QUERIES
# ============================================

def save_adaptation_request(user_id: str, cycle_id: str, context: Dict, 
                           suggestions: List[Dict], user_request: str = None,
                           model: str = None, tokens: int = None) -> Dict:
    """Save an adapt-my-week request and response."""
    supabase = get_supabase_client()
    
    response = supabase.table('adapted_workouts').insert({
        'user_id': user_id,
        'cycle_id': cycle_id,
        'suggestion_context': context,
        'suggestions': suggestions,
        'user_request': user_request,
        'ai_model': model,
        'tokens_used': tokens
    }).execute()
    
    return response.data[0] if response.data else None


def mark_adaptation_applied(adaptation_id: str, suggestion_index: int) -> Dict:
    """Mark an adaptation as applied."""
    supabase = get_supabase_client()
    
    response = supabase.table('adapted_workouts')\
        .update({
            'applied': True,
            'applied_at': datetime.utcnow().isoformat(),
            'selected_suggestion_index': suggestion_index
        })\
        .eq('id', adaptation_id)\
        .execute()
    
    return response.data[0] if response.data else None


# ============================================
# AI USAGE TRACKING
# ============================================

def log_ai_usage(user_id: str, feature: str, model: str, 
                 input_tokens: int = 0, output_tokens: int = 0) -> Dict:
    """Log AI API usage for tracking."""
    supabase = get_supabase_client()
    
    # Rough cost estimation (Claude Sonnet pricing as of 2024)
    # $3 per 1M input tokens, $15 per 1M output tokens
    input_cost = (input_tokens / 1_000_000) * 3 * 100  # cents
    output_cost = (output_tokens / 1_000_000) * 15 * 100  # cents
    
    response = supabase.table('ai_usage_log').insert({
        'user_id': user_id,
        'feature': feature,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'estimated_cost_cents': input_cost + output_cost
    }).execute()
    
    return response.data[0] if response.data else None


def check_daily_ai_limit(user_id: str, limit: int = 10) -> bool:
    """Check if user is under their daily AI call limit."""
    supabase = get_supabase_client()
    
    yesterday = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    
    response = supabase.table('ai_usage_log')\
        .select('id', count='exact')\
        .eq('user_id', user_id)\
        .gt('created_at', yesterday)\
        .execute()
    
    return response.count < limit


def get_ai_usage_stats(user_id: str, days: int = 30) -> Dict:
    """Get AI usage statistics for a user."""
    supabase = get_supabase_client()
    
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    response = supabase.table('ai_usage_log')\
        .select('*')\
        .eq('user_id', user_id)\
        .gt('created_at', start_date)\
        .execute()
    
    if not response.data:
        return {'total_calls': 0, 'total_cost_cents': 0, 'by_feature': {}}
    
    by_feature = {}
    total_cost = 0
    
    for row in response.data:
        feature = row['feature']
        if feature not in by_feature:
            by_feature[feature] = {'calls': 0, 'cost_cents': 0}
        by_feature[feature]['calls'] += 1
        by_feature[feature]['cost_cents'] += row.get('estimated_cost_cents', 0)
        total_cost += row.get('estimated_cost_cents', 0)
    
    return {
        'total_calls': len(response.data),
        'total_cost_cents': total_cost,
        'by_feature': by_feature
    }
