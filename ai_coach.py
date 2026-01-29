"""
AI Coach Module
================
Provides intelligent workout suggestions, deload/progression detection,
and week adaptation features.

Features:
1. Weight/Rep Suggestions (algorithmic, no AI cost)
2. Deload/Progression Detection (rule-based) + AI Prescription
3. Adapt My Week (AI-powered workout suggestions)
"""
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from config import Config
import db_coach


# ============================================
# CONFIGURATION
# ============================================

AI_CONFIG = {
    'enabled': True,
    'model': 'claude-sonnet-4-20250514',
    'max_tokens': 800,
    'daily_limit_per_user': 10,
    'cache_recommendations_hours': 24
}

# Weight increment settings
WEIGHT_INCREMENT_HEAVY = 5.0  # lbs for compound/heavy exercises
WEIGHT_INCREMENT_LIGHT = 2.5  # lbs for isolation/light exercises


# ============================================
# FEATURE 1: WEIGHT/REP SUGGESTIONS
# ============================================

@dataclass
class WeightSuggestion:
    """Weight suggestion for an exercise."""
    suggested_weight: Optional[float]
    reason: str  # 'increase', 'maintain', 'decrease', 'no_history'
    confidence: str  # 'high', 'medium', 'low'
    explanation: str  # Human-readable explanation
    last_weight: Optional[float] = None
    last_reps: Optional[int] = None
    based_on_sessions: int = 0


def calculate_weight_suggestion(
    user_id: str,
    exercise_id: str,
    target_rep_low: int = 6,
    target_rep_high: int = 12,
    is_heavy: bool = True,
    use_cache: bool = True
) -> WeightSuggestion:
    """
    Calculate weight suggestion for an exercise based on recent performance.
    
    Logic:
    - Hit top of rep range 2+ sessions → suggest increase
    - Below bottom of range → suggest same or decrease
    - Otherwise → suggest same weight
    
    Args:
        user_id: User's ID
        exercise_id: Exercise UUID
        target_rep_low: Bottom of target rep range
        target_rep_high: Top of target rep range
        is_heavy: Whether this is a heavy/compound movement
        use_cache: Whether to check cache first
    
    Returns:
        WeightSuggestion with recommendation
    """
    # Check cache first
    if use_cache:
        cached = db_coach.get_cached_weight_suggestion(user_id, exercise_id)
        if cached:
            return WeightSuggestion(
                suggested_weight=cached['suggested_weight'],
                reason=cached['suggestion_reason'],
                confidence=cached['confidence'],
                explanation=_get_suggestion_explanation(cached['suggestion_reason']),
                last_weight=cached['last_weight'],
                last_reps=cached['last_reps'],
                based_on_sessions=cached['based_on_sessions']
            )
    
    # Get recent performance
    history = db_coach.get_recent_exercise_performance(user_id, exercise_id, limit=3)
    
    if not history:
        return WeightSuggestion(
            suggested_weight=None,
            reason='no_history',
            confidence='low',
            explanation='No previous data - enter your starting weight',
            based_on_sessions=0
        )
    
    # Analyze recent sessions
    last_session = history[0]
    last_weight = last_session.get('working_weight')
    last_avg_reps = last_session.get('avg_reps', 0)
    
    if last_weight is None:
        return WeightSuggestion(
            suggested_weight=None,
            reason='no_history',
            confidence='low', 
            explanation='No weight data found - enter your working weight',
            based_on_sessions=len(history)
        )
    
    # Determine increment based on exercise type
    increment = WEIGHT_INCREMENT_HEAVY if is_heavy else WEIGHT_INCREMENT_LIGHT
    
    # Count how many recent sessions hit the top of rep range
    sessions_at_ceiling = 0
    sessions_below_floor = 0
    
    for session in history[:3]:
        avg_reps = session.get('avg_reps', 0)
        if avg_reps >= target_rep_high:
            sessions_at_ceiling += 1
        elif avg_reps < target_rep_low:
            sessions_below_floor += 1
    
    # Decision logic
    if sessions_at_ceiling >= 2:
        # Ready to progress
        suggested = last_weight + increment
        reason = 'increase'
        confidence = 'high'
        explanation = f'You hit {target_rep_high}+ reps twice - increase to {suggested:.1f} lbs'
    
    elif sessions_below_floor >= 2:
        # Struggling - consider decrease
        if last_avg_reps < target_rep_low - 2:
            # Really struggling
            suggested = max(last_weight - increment, 0)
            reason = 'decrease'
            confidence = 'medium'
            explanation = f'Reps below target - try {suggested:.1f} lbs'
        else:
            # Just below, keep trying
            suggested = last_weight
            reason = 'maintain'
            confidence = 'medium'
            explanation = f'Stick with {suggested:.1f} lbs and aim for {target_rep_low}+ reps'
    
    else:
        # In the middle - maintain
        suggested = last_weight
        reason = 'maintain'
        confidence = 'high'
        explanation = f'Good progress - continue with {suggested:.1f} lbs'
    
    result = WeightSuggestion(
        suggested_weight=suggested,
        reason=reason,
        confidence=confidence,
        explanation=explanation,
        last_weight=last_weight,
        last_reps=int(last_avg_reps),
        based_on_sessions=len(history)
    )
    
    # Cache the result
    if use_cache:
        db_coach.cache_weight_suggestion(user_id, exercise_id, {
            'suggested_weight': suggested,
            'reason': reason,
            'confidence': confidence,
            'based_on_sessions': len(history),
            'last_weight': last_weight,
            'last_reps': int(last_avg_reps),
            'target_rep_range': f'{target_rep_low}-{target_rep_high}'
        })
    
    return result


def _get_suggestion_explanation(reason: str) -> str:
    """Get human-readable explanation for suggestion reason."""
    explanations = {
        'increase': 'Ready to increase weight',
        'maintain': 'Keep current weight',
        'decrease': 'Consider reducing weight',
        'no_history': 'No previous data'
    }
    return explanations.get(reason, 'Continue as planned')


def get_workout_weight_suggestions(
    user_id: str,
    exercises: List[Dict],
    cycle_week: int = None
) -> Dict[str, WeightSuggestion]:
    """
    Get weight suggestions for all exercises in a workout.
    
    Args:
        user_id: User's ID
        exercises: List of exercise dicts with 'id', 'is_heavy', 'rep_range_heavy', 'rep_range_light'
        cycle_week: Current week number (for periodization)
    
    Returns:
        Dict mapping exercise_id to WeightSuggestion
    """
    suggestions = {}
    
    for ex in exercises:
        exercise_id = ex.get('id') or ex.get('exercise_id')
        if not exercise_id:
            continue
        
        is_heavy = ex.get('is_heavy', True)
        
        # Parse rep range
        rep_range = ex.get('rep_range_heavy' if is_heavy else 'rep_range_light', '8-12')
        try:
            if '-' in str(rep_range):
                parts = str(rep_range).replace(' ', '').split('-')
                rep_low = int(parts[0])
                rep_high = int(parts[1].split()[0])  # Handle "10-12 each"
            else:
                rep_low = rep_high = int(rep_range)
        except:
            rep_low, rep_high = 8, 12
        
        suggestions[exercise_id] = calculate_weight_suggestion(
            user_id=user_id,
            exercise_id=exercise_id,
            target_rep_low=rep_low,
            target_rep_high=rep_high,
            is_heavy=is_heavy
        )
    
    return suggestions


# ============================================
# FEATURE 2: DELOAD/PROGRESSION DETECTION
# ============================================

class SignalType(Enum):
    DELOAD = 'deload'
    PROGRESSION = 'progression'


@dataclass
class TrainingSignal:
    """A detected training signal (deload needed, ready to progress, etc.)"""
    signal_type: SignalType
    signal_name: str
    description: str
    confidence: float  # 0-1
    data: Dict[str, Any]  # Supporting data


def detect_training_signals(user_id: str, cycle_id: str = None) -> Dict[str, List[TrainingSignal]]:
    """
    Detect if user needs a deload or is ready to progress.
    Returns signals grouped by type.
    """
    signals = {'deload': [], 'progression': []}
    
    # Get training data
    weekly_summaries = db_coach.get_weekly_training_summary(user_id, weeks_back=4)
    compound_trends = db_coach.get_compound_lift_trends(user_id, weeks_back=4)
    
    if len(weekly_summaries) < 2:
        # Not enough data to analyze
        return signals
    
    # ---- DELOAD SIGNALS ----
    
    # 1. Plateau detection - compound lifts not progressing
    stalled_lifts = _detect_stalled_compounds(compound_trends)
    if len(stalled_lifts) >= 3:
        signals['deload'].append(TrainingSignal(
            signal_type=SignalType.DELOAD,
            signal_name='plateau',
            description=f'{len(stalled_lifts)} compound lifts have stalled',
            confidence=0.8,
            data={'stalled_lifts': stalled_lifts}
        ))
    
    # 2. Volume drop detection
    volume_change = _calculate_volume_trend(weekly_summaries)
    if volume_change < -0.15:  # >15% drop
        signals['deload'].append(TrainingSignal(
            signal_type=SignalType.DELOAD,
            signal_name='volume_drop',
            description=f'Training volume down {abs(volume_change)*100:.0f}%',
            confidence=0.7,
            data={'volume_change': volume_change}
        ))
    
    # 3. Completion rate drop
    completion_rate = _calculate_completion_rate(weekly_summaries)
    if completion_rate < 0.70:
        signals['deload'].append(TrainingSignal(
            signal_type=SignalType.DELOAD,
            signal_name='completion_drop',
            description=f'Workout completion at {completion_rate*100:.0f}%',
            confidence=0.6,
            data={'completion_rate': completion_rate}
        ))
    
    # ---- PROGRESSION SIGNALS ----
    
    # 1. Exercises at rep ceiling
    exercises_at_ceiling = _detect_exercises_at_ceiling(user_id, compound_trends)
    if len(exercises_at_ceiling) >= 3:
        signals['progression'].append(TrainingSignal(
            signal_type=SignalType.PROGRESSION,
            signal_name='rep_ceiling',
            description=f'{len(exercises_at_ceiling)} exercises ready for weight increase',
            confidence=0.85,
            data={'exercises': exercises_at_ceiling}
        ))
    
    # 2. Consistent completion + volume trending up
    if completion_rate > 0.90 and volume_change > 0.05:
        signals['progression'].append(TrainingSignal(
            signal_type=SignalType.PROGRESSION,
            signal_name='consistent_progress',
            description='Strong consistency and volume trending up',
            confidence=0.75,
            data={'completion_rate': completion_rate, 'volume_change': volume_change}
        ))
    
    return signals


def _detect_stalled_compounds(compound_trends: Dict[str, List[Dict]]) -> List[str]:
    """Detect compound lifts that haven't increased in 2+ weeks."""
    stalled = []
    
    for exercise_name, sessions in compound_trends.items():
        if len(sessions) < 3:
            continue
        
        # Check if max weight hasn't increased in last 3 sessions
        recent_maxes = [s['max_weight'] for s in sessions[-3:]]
        if len(set(recent_maxes)) == 1 or max(recent_maxes) == recent_maxes[0]:
            # No increase
            stalled.append(exercise_name)
    
    return stalled


def _calculate_volume_trend(weekly_summaries: List[Dict]) -> float:
    """Calculate volume change trend. Returns % change."""
    if len(weekly_summaries) < 2:
        return 0.0
    
    # Compare last 2 weeks to prior 2 weeks
    recent = weekly_summaries[:2]
    prior = weekly_summaries[2:4] if len(weekly_summaries) >= 4 else weekly_summaries[2:]
    
    recent_vol = sum(w['total_volume'] for w in recent) / len(recent) if recent else 0
    prior_vol = sum(w['total_volume'] for w in prior) / len(prior) if prior else 0
    
    if prior_vol == 0:
        return 0.0
    
    return (recent_vol - prior_vol) / prior_vol


def _calculate_completion_rate(weekly_summaries: List[Dict]) -> float:
    """Calculate workout completion rate over recent weeks."""
    if not weekly_summaries:
        return 1.0
    
    # Assume 3-4 workouts per week as target
    recent = weekly_summaries[:2]
    total_workouts = sum(w['workouts_completed'] for w in recent)
    expected = len(recent) * 3  # Assume 3 per week minimum
    
    return min(total_workouts / expected, 1.0) if expected > 0 else 1.0


def _detect_exercises_at_ceiling(user_id: str, compound_trends: Dict) -> List[Dict]:
    """Detect exercises where user is hitting top of rep range consistently."""
    # This would need rep data - simplified for now
    at_ceiling = []
    
    for exercise_name, sessions in compound_trends.items():
        if len(sessions) >= 2:
            # Check if weight has been same but still completing sets
            recent = sessions[-2:]
            if all(s['max_weight'] == recent[0]['max_weight'] for s in recent):
                at_ceiling.append({
                    'name': exercise_name,
                    'current_weight': recent[-1]['max_weight']
                })
    
    return at_ceiling


# ============================================
# AI PRESCRIPTION GENERATION
# ============================================

def generate_deload_prescription(user_id: str, signals: List[TrainingSignal], 
                                 context: Dict = None) -> Optional[Dict]:
    """
    Generate AI prescription for deload based on detected signals.
    """
    if not AI_CONFIG['enabled']:
        return _get_default_deload_prescription(signals)
    
    if not db_coach.check_daily_ai_limit(user_id, AI_CONFIG['daily_limit_per_user']):
        return _get_default_deload_prescription(signals)
    
    # Build prompt
    signal_descriptions = [f"- {s.signal_name}: {s.description}" for s in signals]
    
    prompt = f"""You are a concise fitness coach. Generate a brief, encouraging deload recommendation.

USER CONTEXT:
- Signals detected:
{chr(10).join(signal_descriptions)}

OUTPUT FORMAT (JSON only, no markdown):
{{
  "title": "Recovery Week Recommended",
  "explanation": "1-2 sentences on why this will help",
  "prescription": "Specific instructions (e.g., reduce sets, use lighter weights)",
  "duration": "1 week",
  "motivation": "Brief encouraging message"
}}

Keep it brief and actionable. Be encouraging, not alarming."""

    result = _call_anthropic_api(prompt, user_id, 'deload_prescription')
    
    if result:
        return result
    else:
        return _get_default_deload_prescription(signals)


def generate_progression_prescription(user_id: str, signals: List[TrainingSignal],
                                      context: Dict = None) -> Optional[Dict]:
    """
    Generate AI prescription for progression based on detected signals.
    """
    if not AI_CONFIG['enabled']:
        return _get_default_progression_prescription(signals)
    
    if not db_coach.check_daily_ai_limit(user_id, AI_CONFIG['daily_limit_per_user']):
        return _get_default_progression_prescription(signals)
    
    # Build exercise list from signals
    exercises_data = []
    for signal in signals:
        if signal.signal_name == 'rep_ceiling':
            exercises_data = signal.data.get('exercises', [])
            break
    
    exercises_str = '\n'.join([
        f"- {ex['name']}: currently at {ex['current_weight']} lbs"
        for ex in exercises_data[:5]
    ]) or "- Multiple compound lifts showing consistent performance"

    prompt = f"""You are a concise fitness coach. The user is ready to progress.

USER CONTEXT:
- Exercises ready for progression:
{exercises_str}

OUTPUT FORMAT (JSON only, no markdown):
{{
  "title": "Ready to Progress! 💪",
  "exercises": [
    {{"name": "Exercise Name", "current": 135, "suggested": 140, "tip": "Brief form reminder"}}
  ],
  "explanation": "1 sentence of encouragement",
  "general_tip": "One key thing to remember when increasing weight"
}}

Be specific with numbers (suggest 5 lb increases for compounds, 2.5 for isolation). Keep it brief and encouraging."""

    result = _call_anthropic_api(prompt, user_id, 'progression_prescription')
    
    if result:
        return result
    else:
        return _get_default_progression_prescription(signals)


def _get_default_deload_prescription(signals: List[TrainingSignal]) -> Dict:
    """Fallback deload prescription when AI is unavailable."""
    return {
        'title': 'Recovery Week Recommended',
        'explanation': 'Your body could use some recovery time to adapt and come back stronger.',
        'prescription': 'This week: Keep the same exercises but reduce to 3 sets instead of 4, and use weights from 2 weeks ago. Focus on movement quality.',
        'duration': '1 week',
        'motivation': "Rest is part of progress. You've earned it!"
    }


def _get_default_progression_prescription(signals: List[TrainingSignal]) -> Dict:
    """Fallback progression prescription when AI is unavailable."""
    exercises = []
    for signal in signals:
        if signal.data.get('exercises'):
            for ex in signal.data['exercises'][:3]:
                exercises.append({
                    'name': ex['name'],
                    'current': ex['current_weight'],
                    'suggested': ex['current_weight'] + 5,
                    'tip': 'Maintain good form'
                })
            break
    
    return {
        'title': 'Ready to Progress! 💪',
        'exercises': exercises,
        'explanation': "You've been consistent and strong. Time to challenge yourself!",
        'general_tip': 'Increase weight by 5 lbs and aim for the bottom of your rep range.'
    }


# ============================================
# FEATURE 3: ADAPT MY WEEK
# ============================================

def should_show_adapt_option(user_id: str, cycle_id: str) -> Tuple[bool, str]:
    """
    Check if user might benefit from week adaptation.
    Returns (should_show, reason).
    """
    week_status = db_coach.get_current_week_status(user_id, cycle_id)
    
    completed = len(week_status['completed'])
    scheduled = len(week_status['scheduled'])
    remaining = len(week_status['remaining'])
    missed = len(week_status.get('missed', []))  # Actually missed (past dates)
    days_left = week_status['days_remaining']
    day_of_week = week_status['day_of_week']
    
    # Condition 1: Actually missed workouts (past dates, not completed)
    if missed >= 1:
        return True, f"You've missed {missed} scheduled workout{'s' if missed > 1 else ''}. Want to adapt your week?"
    
    # Condition 2: Behind schedule late in week (it's Thursday+ and haven't started)
    if completed == 0 and scheduled > 0 and day_of_week >= 3:  # Thursday or later
        return True, "You haven't started this week's workouts yet. Want to adapt your plan?"
    
    # Condition 3: Completed everything early (might want to add extra)
    if completed == scheduled and scheduled > 0 and days_left >= 2:
        return True, "Great work completing your workouts! Want to add an extra session?"
    
    return False, ""


def gather_adaptation_context(user_id: str, cycle_id: str, user_request: str = None) -> Dict:
    """
    Gather all context needed for AI to generate workout adaptations.
    """
    from db import get_all_exercises
    from db_cycles import get_cycle_by_id
    
    week_status = db_coach.get_current_week_status(user_id, cycle_id)
    muscle_coverage = db_coach.get_muscle_coverage_this_week(user_id, cycle_id)
    
    # Get cycle info
    cycle = get_cycle_by_id(cycle_id) if cycle_id else None
    
    # Get available exercises grouped by muscle
    all_exercises = get_all_exercises()
    exercises_by_muscle = {}
    for ex in all_exercises:
        muscle = ex.get('muscle_group', 'other')
        if muscle not in exercises_by_muscle:
            exercises_by_muscle[muscle] = []
        exercises_by_muscle[muscle].append({
            'id': ex['id'],
            'name': ex['name'],
            'equipment': ex.get('equipment', 'bodyweight'),
            'is_compound': ex.get('is_compound', False)
        })
    
    return {
        'week_status': week_status,
        'muscle_coverage': muscle_coverage,
        'cycle': {
            'name': cycle.get('name') if cycle else 'Current Cycle',
            'split_type': cycle.get('split_type') if cycle else 'custom',
            'week_number': cycle.get('current_week', 1) if cycle else 1
        } if cycle else None,
        'exercises_by_muscle': exercises_by_muscle,
        'user_request': user_request or 'Adapt my remaining week to be as effective as possible'
    }


def generate_week_adaptation(user_id: str, cycle_id: str, 
                            user_request: str = None) -> Optional[Dict]:
    """
    Generate adapted workout suggestions for the week.
    """
    if not db_coach.check_daily_ai_limit(user_id, AI_CONFIG['daily_limit_per_user']):
        return {'error': 'Daily AI limit reached. Try again tomorrow.'}
    
    context = gather_adaptation_context(user_id, cycle_id, user_request)
    
    # Build a focused prompt
    week = context['week_status']
    muscles = context['muscle_coverage']
    
    # Create a simplified exercise list for the prompt
    exercise_list = []
    for muscle in muscles['untrained'][:4]:  # Focus on untrained muscles
        exs = context['exercises_by_muscle'].get(muscle, [])[:3]
        for ex in exs:
            exercise_list.append(f"{ex['name']} ({muscle}, {ex['equipment']})")
    
    # Get info about skipped/missed workouts
    skipped_info = []
    for w in week.get('skipped', []) + week.get('missed', []):
        skipped_info.append(f"- {w.get('name', 'Workout')} (was scheduled for {w.get('scheduled_date', 'earlier')})")
    
    skipped_section = ""
    if skipped_info:
        skipped_section = f"""
SKIPPED/MISSED WORKOUTS THAT NEED TO BE MADE UP:
{chr(10).join(skipped_info)}

IMPORTANT: The adapted workout MUST incorporate exercises from the skipped workouts above. 
The primary goal is to ensure the user still hits the muscle groups they missed."""

    prompt = f"""You are a fitness coach helping adapt a training week.

SITUATION:
- Completed workouts: {len(week['completed'])}
- Remaining scheduled: {len(week['remaining'])}
- Days left in week: {week['days_remaining']}
- Muscles NOT trained yet: {', '.join(muscles['untrained'][:6]) or 'None'}
- Muscles already trained: {', '.join(muscles['trained'][:6]) or 'None'}
{skipped_section}

USER REQUEST: {user_request or 'Adapt my remaining week to make up for missed workouts'}

AVAILABLE EXERCISES (use only these):
{chr(10).join(exercise_list[:15])}

Generate 1-2 workout suggestions. Each must:
1. Use ONLY exercises from the list above
2. Prioritize untrained muscle groups
3. Have 5-7 exercises
4. Include sets (3-4) and reps (6-12 range)

OUTPUT FORMAT (JSON only, no markdown):
{{
  "situation_summary": "Brief 1-sentence assessment",
  "suggestions": [
    {{
      "name": "Workout Name",
      "rationale": "Why this workout makes sense",
      "exercises": [
        {{"name": "Exercise Name", "sets": 4, "reps": "8-10", "muscle": "chest"}}
      ],
      "estimated_minutes": 45,
      "muscles_covered": ["chest", "back", "shoulders"]
    }}
  ],
  "tip": "One practical tip for the user"
}}"""

    result = _call_anthropic_api(prompt, user_id, 'adapt_week')
    
    if result:
        # Save the adaptation request
        db_coach.save_adaptation_request(
            user_id=user_id,
            cycle_id=cycle_id,
            context=context,
            suggestions=result.get('suggestions', []),
            user_request=user_request,
            model=AI_CONFIG['model']
        )
        return result
    
    # Fallback response
    return _get_default_adaptation(context)


def _get_default_adaptation(context: Dict) -> Dict:
    """Generate a simple adaptation without AI."""
    muscles = context['muscle_coverage']
    exercises_by_muscle = context['exercises_by_muscle']
    
    # Build a simple full-body workout from untrained muscles
    exercises = []
    for muscle in muscles['untrained'][:5]:
        exs = exercises_by_muscle.get(muscle, [])
        compound = next((e for e in exs if e.get('is_compound')), None)
        if compound:
            exercises.append({
                'name': compound['name'],
                'sets': 3,
                'reps': '8-12',
                'muscle': muscle
            })
    
    # Add a couple more if needed
    if len(exercises) < 5:
        for muscle in muscles['trained'][:2]:
            exs = exercises_by_muscle.get(muscle, [])
            if exs:
                exercises.append({
                    'name': exs[0]['name'],
                    'sets': 3,
                    'reps': '10-12',
                    'muscle': muscle
                })
    
    return {
        'situation_summary': f"You have {context['week_status']['days_remaining']} days left and haven't hit {', '.join(muscles['untrained'][:3])}.",
        'suggestions': [{
            'name': 'Full Body Catch-Up',
            'rationale': 'Hit your missed muscle groups with a balanced session',
            'exercises': exercises[:6],
            'estimated_minutes': 45,
            'muscles_covered': muscles['untrained'][:5]
        }],
        'tip': 'Focus on compound movements to maximize your time.'
    }


# ============================================
# ANTHROPIC API HELPER
# ============================================

def _call_anthropic_api(prompt: str, user_id: str, feature: str) -> Optional[Dict]:
    """
    Call Anthropic API and parse JSON response.
    Handles errors gracefully and logs usage.
    """
    api_key = Config.ANTHROPIC_API_KEY
    
    if not api_key:
        print(f"AI Coach: No API key configured for {feature}")
        return None
    
    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': AI_CONFIG['model'],
                'max_tokens': AI_CONFIG['max_tokens'],
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '{}')
            
            # Log usage
            usage = result.get('usage', {})
            db_coach.log_ai_usage(
                user_id=user_id,
                feature=feature,
                model=AI_CONFIG['model'],
                input_tokens=usage.get('input_tokens', 0),
                output_tokens=usage.get('output_tokens', 0)
            )
            
            # Parse JSON from response
            # Handle potential markdown code blocks
            content = content.strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            return json.loads(content)
        else:
            print(f"AI Coach API error: {response.status_code} - {response.text}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"AI Coach JSON parse error: {e}")
        return None
    except requests.exceptions.Timeout:
        print("AI Coach API timeout")
        return None
    except Exception as e:
        print(f"AI Coach error: {e}")
        return None


# ============================================
# HIGH-LEVEL CHECK FUNCTION
# ============================================

def check_and_get_recommendation(user_id: str, cycle_id: str = None) -> Optional[Dict]:
    """
    Main entry point: Check if user needs any coaching intervention.
    Returns a recommendation if warranted, None otherwise.
    
    Call this when user views their weekly plan.
    """
    # First check for existing pending recommendation
    existing = db_coach.get_pending_recommendation(user_id, cycle_id)
    if existing:
        return {
            'id': existing['id'],
            'type': existing['recommendation_type'],
            'prescription': existing['prescription'],
            'created_at': existing['created_at'],
            'is_cached': True
        }
    
    # Detect new signals
    signals = detect_training_signals(user_id, cycle_id)
    
    # Prioritize deload signals
    if signals['deload']:
        prescription = generate_deload_prescription(user_id, signals['deload'])
        if prescription:
            rec = db_coach.create_recommendation(
                user_id=user_id,
                cycle_id=cycle_id,
                rec_type='deload',
                signals=[{'name': s.signal_name, 'description': s.description} for s in signals['deload']],
                prescription=prescription,
                model=AI_CONFIG['model']
            )
            return {
                'id': rec['id'] if rec else None,
                'type': 'deload',
                'prescription': prescription,
                'is_cached': False
            }
    
    # Then check progression signals
    if signals['progression']:
        prescription = generate_progression_prescription(user_id, signals['progression'])
        if prescription:
            rec = db_coach.create_recommendation(
                user_id=user_id,
                cycle_id=cycle_id,
                rec_type='progression',
                signals=[{'name': s.signal_name, 'description': s.description} for s in signals['progression']],
                prescription=prescription,
                model=AI_CONFIG['model']
            )
            return {
                'id': rec['id'] if rec else None,
                'type': 'progression',
                'prescription': prescription,
                'is_cached': False
            }
    
    return None
