from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response
from functools import wraps
from config import Config
from datetime import date, datetime, timedelta
import db
import db_cycles
import db_progress
import db_export
import db_notifications
import db_social
import workout_generator
import notification_service
import db_exercise_notes

app = Flask(__name__)
app.config.from_object(Config)

# ============================================
# AUTH HELPERS
# ============================================

def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the current logged-in user from session."""
    return session.get('user')


# ============================================
# AUTH ROUTES
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if 'user' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
        
        try:
            supabase = db.get_supabase_client()
            response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            # Store user info in session
            session['user'] = {
                'id': response.user.id,
                'email': response.user.email,
                'access_token': response.session.access_token,
                'display_name': email.split('@')[0]  # Default display name
            }
            
            # Try to get profile, but don't fail if it doesn't exist
            try:
                profile = db.get_user_profile(response.user.id)
                if profile and profile.get('display_name'):
                    session['user']['display_name'] = profile['display_name']
            except Exception as e:
                print(f"Profile fetch error (non-fatal): {e}")
            
            flash('Welcome back!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            error_msg = str(e)
            if 'Invalid login credentials' in error_msg:
                flash('Invalid email or password.', 'error')
            else:
                flash(f'Login failed: {error_msg}', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html', config=app.config)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler."""
    if 'user' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/signup.html')
        
        try:
            supabase = db.get_supabase_client()
            response = supabase.auth.sign_up({
                'email': email,
                'password': password
            })
            
            if response.user:
                # Auto-login after signup if session exists
                if response.session:
                    session['user'] = {
                        'id': response.user.id,
                        'email': response.user.email,
                        'access_token': response.session.access_token,
                        'display_name': email.split('@')[0]
                    }
                    flash('Account created! Welcome to Workout Tracker.', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Please check your email to confirm your account.', 'info')
                    return redirect(url_for('login'))
                
        except Exception as e:
            error_msg = str(e)
            if 'already registered' in error_msg.lower():
                flash('This email is already registered. Try logging in.', 'error')
            else:
                flash(f'Signup failed: {error_msg}', 'error')
            return render_template('auth/signup.html')
    
    return render_template('auth/signup.html')


@app.route('/logout')
def logout():
    """Log out the current user."""
    try:
        if 'user' in session and session['user'].get('access_token'):
            supabase = db.get_supabase_client()
            supabase.auth.sign_out()
    except:
        pass  # Ignore logout errors
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/auth/google')
def auth_google():
    """Initiate Google OAuth flow via Supabase."""
    supabase = db.get_supabase_client()
    
    # Determine redirect URL based on environment
    if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
        redirect_url = 'http://localhost:5000/auth/google/callback'
    else:
        redirect_url = 'https://spotter-a1ux.onrender.com/auth/google/callback'
    
    response = supabase.auth.sign_in_with_oauth({
        'provider': 'google',
        'options': {
            'redirect_to': redirect_url,
            'skip_http_refresh': False
        }
    })
    
    # Store PKCE verifier in session for later exchange
    if hasattr(supabase.auth, '_code_verifier'):
        session['pkce_verifier'] = supabase.auth._code_verifier
    
    # Redirect to Google's OAuth page
    return redirect(response.url)


@app.route('/auth/google/callback')
def auth_google_callback():
    """Handle Google OAuth callback - use JS client to handle PKCE."""
    return render_template('auth/google_callback.html', config=app.config)


@app.route('/auth/google/complete')
def auth_google_complete():
    """Complete Google OAuth with tokens from client-side."""
    access_token = request.args.get('access_token')
    refresh_token = request.args.get('refresh_token')
    
    if not access_token:
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('login'))
    
    try:
        supabase = db.get_supabase_client()
        response = supabase.auth.get_user(access_token)
        user = response.user
        
        if user:
            session['user'] = {
                'id': user.id,
                'email': user.email,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'display_name': user.user_metadata.get('full_name') or user.user_metadata.get('name') or user.email.split('@')[0]
            }
            
            try:
                profile = db.get_user_profile(user.id)
                if not profile:
                    db.create_user_profile(
                        user_id=user.id,
                        email=user.email,
                        display_name=session['user']['display_name']
                    )
                elif profile.get('display_name'):
                    session['user']['display_name'] = profile['display_name']
            except Exception as e:
                print(f"Profile setup error (non-fatal): {e}")
            
            flash('Welcome! Signed in with Google.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Could not get user info.', 'error')
            return redirect(url_for('login'))
            
    except Exception as e:
        print(f"Google complete error: {e}")
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('login'))

# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    """Landing page - shows workout selection or redirects to plan."""
    user = get_current_user()
    
    # If user is logged in and has an active cycle, redirect to plan
    if user:
        try:
            active_cycle = db_cycles.get_active_cycle(user['id'])
            if active_cycle:
                return redirect(url_for('plan'))
        except Exception as e:
            print(f"Error checking active cycle: {e}")
    
    # Split type display names and descriptions
    SPLIT_DISPLAY_NAMES = {
        'ppl_3day': 'PPL×2 (3 Day)',
        'ppl_6day': 'PPL (6 Day)',
        'upper_lower_4day': 'Upper/Lower (4 Day)',
        'full_body_3day': 'Full Body (3 Day)',
        'custom': 'Custom'
    }
    
    SPLIT_DESCRIPTIONS = {
        'ppl_3day': 'Push/Pull/Legs hit twice per week in 3 training days',
        'ppl_6day': 'Push/Pull/Legs split across 6 training days',
        'upper_lower_4day': 'Upper and Lower body across 4 training days',
        'full_body_3day': 'Full body workouts 3 days per week',
        'custom': 'Custom training split'
    }
    
    try:
        routine = db.get_routine('ppl_3day')
    except Exception as e:
        # Fallback to hardcoded routine if DB fails
        print(f"Database error: {e}")
        from data.routines import get_routine as get_local_routine
        routine = get_local_routine('ppl_3day')
    
    # Get active cycle and profile if user is logged in
    active_cycle = None
    profile = None
    split_display_name = SPLIT_DISPLAY_NAMES.get('ppl_3day')
    split_description = SPLIT_DESCRIPTIONS.get('ppl_3day')
    
    if user:
        try:
            active_cycle = db_cycles.get_active_cycle(user['id'])
        except Exception as e:
            print(f"Error fetching active cycle: {e}")
        
        try:
            profile = db.get_user_profile(user['id'])
            if profile and profile.get('split_type'):
                split_type = profile.get('split_type')
                split_display_name = SPLIT_DISPLAY_NAMES.get(split_type, split_type.replace('_', ' ').title())
                split_description = SPLIT_DESCRIPTIONS.get(split_type, f"{profile.get('days_per_week', 3)} days per week training")
        except Exception as e:
            print(f"Error fetching profile: {e}")
    
    response = make_response(render_template('index.html', 
                         routine=routine, 
                         user=user, 
                         active_cycle=active_cycle,
                         profile=profile,
                         split_display_name=split_display_name,
                         split_description=split_description))
    # Prevent browser from caching this page (so back button doesn't show stale content)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


@app.route('/workout/<day_id>')
def workout(day_id):
    """Workout execution view for a specific day (legacy/template-based)."""
    user = get_current_user()
    
    try:
        routine = db.get_routine('ppl_3day')
    except Exception as e:
        print(f"Database error: {e}")
        from data.routines import get_routine as get_local_routine
        routine = get_local_routine('ppl_3day')
    
    if not routine:
        flash('Routine not found.', 'error')
        return redirect(url_for('index'))
    
    # Find the day - support both UUID and day_number
    day = None
    for d in routine['days']:
        if str(d.get('id')) == day_id or str(d.get('day_number')) == day_id:
            day = d
            break
    
    if not day:
        flash('Workout day not found.', 'error')
        return redirect(url_for('index'))
    
    return render_template('workout.html', 
                         day=day, 
                         day_number=day['day_number'], 
                         total_days=len(routine['days']),
                         user=user)


@app.route('/history')
@login_required
def history():
    """View workout history."""
    user = get_current_user()
    
    workouts = db.get_user_workouts(
        user['id'], 
        user.get('access_token', '')
    )
    
    return render_template('history.html', workouts=workouts, user=user)


@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    user = get_current_user()
    profile_data = db.get_user_profile(user['id'])
    
    # Get active cycle
    active_cycle = None
    try:
        active_cycle = db_cycles.get_active_cycle(user['id'])
    except Exception as e:
        print(f"Error fetching active cycle: {e}")
    
    return render_template('profile.html', profile=profile_data, user=user, active_cycle=active_cycle)

@app.route('/progress')
@login_required
def progress():
    """Progress tracking dashboard."""
    user = get_current_user()
    
    # Get timeframe from query params (default to cycle)
    timeframe = request.args.get('timeframe', 'cycle')
    
    # Get date range
    start_date, end_date = db_progress.get_date_range_for_timeframe(timeframe, user['id'])
    
    # Get user's profile for target days per week
    profile = db.get_user_profile(user['id'])
    days_per_week = profile.get('days_per_week', 3) if profile else 3
    
    # Get user's exercises for selector
    user_exercises = db_progress.get_user_exercises(user['id'])
    
    # Get volume data
    volume_by_week = db_progress.get_volume_summary_by_week(user['id'], weeks=12)
    
    # Calculate volume stats
    volume_data = db_progress.get_volume_by_workout_type(user['id'], start_date, end_date)
    total_volume = sum(v['volume'] for v in volume_data)
    total_sets = sum(v['sets'] for v in volume_data)
    workouts_count = len(volume_data)
    avg_volume = total_volume / workouts_count if workouts_count > 0 else 0
    
    volume_stats = {
        'total_volume': total_volume,
        'total_sets': total_sets,
        'workouts_count': workouts_count,
        'avg_volume_per_workout': avg_volume
    }
    
    # Get consistency stats (pass target days per week)
    consistency_stats = db_progress.get_consistency_stats(
        user['id'], start_date, end_date, 
        target_days_per_week=days_per_week
    )
    
    # Get calendar heatmap data
    calendar_data = db_progress.get_calendar_heatmap_data(user['id'])
    
    # Calculate weekly workout counts for chart (not completion rates)
    workouts_by_week = calculate_workouts_per_week(user['id'], weeks=12)
    
    # Get PR data
    pr_threshold = profile.get('pr_rep_threshold', 5) if profile else 5
    
    all_prs = db_progress.get_personal_records(user['id'])
    # Add is_recent flag to each PR
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    for pr in all_prs:
        if pr.get('achieved_at'):
            # Parse the date string
            achieved = datetime.fromisoformat(pr['achieved_at'].replace('Z', '+00:00').replace('+00:00', ''))
            pr['is_recent'] = achieved > thirty_days_ago
        else:
            pr['is_recent'] = False
    
    return render_template('progress.html',
                         user=user,
                         timeframe=timeframe,
                         user_exercises=user_exercises,
                         volume_by_week=volume_by_week,
                         volume_stats=volume_stats,
                         consistency_stats=consistency_stats,
                         calendar_data=calendar_data,
                         workouts_by_week=workouts_by_week,
                         days_per_week=days_per_week,
                         pr_threshold=pr_threshold,
                         all_prs=all_prs)

def calculate_workouts_per_week(user_id: str, weeks: int = 12):
    """Calculate actual workout count per week for the chart."""
    from datetime import date, timedelta
    
    supabase = db.get_supabase_client()
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)
    
    # Get completed workouts
    workouts = supabase.table('user_workouts')\
        .select('completed_at')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .gte('completed_at', start_date.isoformat())\
        .lte('completed_at', end_date.isoformat())\
        .execute()
    
    # Group by week
    weeks_data = {}
    for w in workouts.data or []:
        if w['completed_at']:
            d = datetime.strptime(w['completed_at'][:10], '%Y-%m-%d').date()
            week_start = d - timedelta(days=d.weekday())
            week_key = week_start.isoformat()
            weeks_data[week_key] = weeks_data.get(week_key, 0) + 1
    
    # Fill in missing weeks with 0
    result = []
    current = start_date - timedelta(days=start_date.weekday())  # Start from Monday
    while current <= end_date:
        week_key = current.isoformat()
        result.append({
            'week': week_key,
            'count': weeks_data.get(week_key, 0)
        })
        current += timedelta(weeks=1)
    
    return result

def calculate_weekly_completion_rates(user_id: str, weeks: int = 12):
    """Calculate completion rate per week for the chart."""
    from datetime import date, timedelta
    
    supabase = db.get_supabase_client()
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)
    
    # Get scheduled workouts
    scheduled = supabase.table('scheduled_workouts')\
        .select('scheduled_date, status')\
        .eq('user_id', user_id)\
        .gte('scheduled_date', start_date.isoformat())\
        .lte('scheduled_date', end_date.isoformat())\
        .execute()
    
    # Group by week
    weeks_data = {}
    for w in scheduled.data or []:
        d = datetime.strptime(w['scheduled_date'], '%Y-%m-%d').date()
        week_start = d - timedelta(days=d.weekday())
        week_key = week_start.isoformat()
        
        if week_key not in weeks_data:
            weeks_data[week_key] = {'scheduled': 0, 'completed': 0}
        
        weeks_data[week_key]['scheduled'] += 1
        if w['status'] == 'completed':
            weeks_data[week_key]['completed'] += 1
    
    # Calculate rates
    result = []
    for week, data in sorted(weeks_data.items()):
        rate = round((data['completed'] / data['scheduled'] * 100) if data['scheduled'] > 0 else 0)
        result.append({'week': week, 'rate': rate})
    
    return result


@app.route('/api/progress/strength')
@login_required
def api_progress_strength():
    """Get strength progress data for selected exercises."""
    user = get_current_user()
    
    exercise_ids = request.args.get('exercises', '').split(',')
    exercise_ids = [e.strip() for e in exercise_ids if e.strip()]
    
    if not exercise_ids:
        return jsonify([])
    
    timeframe = request.args.get('timeframe', 'cycle')
    start_date, end_date = db_progress.get_date_range_for_timeframe(timeframe, user['id'])
    
    data = db_progress.get_exercise_history(user['id'], exercise_ids, start_date, end_date)
    
    return jsonify(data)


@app.route('/api/progress/volume')
@login_required
def api_progress_volume():
    """Get volume data for charts."""
    user = get_current_user()
    
    weeks = request.args.get('weeks', 12, type=int)
    data = db_progress.get_volume_summary_by_week(user['id'], weeks)
    
    return jsonify(data)


@app.route('/api/progress/consistency')
@login_required
def api_progress_consistency():
    """Get consistency stats."""
    user = get_current_user()
    
    timeframe = request.args.get('timeframe', 'cycle')
    start_date, end_date = db_progress.get_date_range_for_timeframe(timeframe, user['id'])
    
    data = db_progress.get_consistency_stats(user['id'], start_date, end_date)
    
    return jsonify(data)


@app.route('/api/progress/check-pr', methods=['POST'])
@login_required
def api_check_pr():
    """Check if a lift is a new PR and record it."""
    user = get_current_user()
    data = request.json
    
    result = db_progress.check_and_update_pr(
        user_id=user['id'],
        exercise_id=data['exercise_id'],
        exercise_name=data['exercise_name'],
        weight=data['weight'],
        reps=data['reps'],
        workout_set_id=data.get('workout_set_id')
    )
    
    return jsonify(result)

# ============================================
# PLANNING ROUTES (Phase 3)
# ============================================

@app.route('/plan')
@login_required
def plan():
    """Weekly planning view."""
    user = get_current_user()
    
    # Get active cycle
    cycle = db_cycles.get_active_cycle(user['id'])
    
    # Get today's date
    today = date.today()
    
    # Determine which week to show
    requested_week = request.args.get('week', type=int)
    
    if cycle:
        # Calculate current week based on cycle start date
        cycle_start = datetime.strptime(cycle['start_date'], '%Y-%m-%d').date()
        days_since_start = (today - cycle_start).days
        actual_current_week = max(1, min(cycle.get('length_weeks', 6), (days_since_start // 7) + 1))
        
        # Use requested week or default to actual current week
        if requested_week:
            current_week = max(1, min(cycle.get('length_weeks', 6), requested_week))
        else:
            current_week = actual_current_week
        
        # Calculate week_start for the requested week (always align to Monday)
        cycle_week_start = cycle_start + timedelta(weeks=current_week - 1)
        week_start = cycle_week_start - timedelta(days=cycle_week_start.weekday())
        
        # Determine if viewing the actual current week
        is_current_week = (current_week == actual_current_week)
    else:
        # No cycle - just show current calendar week
        current_week = 1
        week_start = today - timedelta(days=today.weekday())  # Monday of current week
        is_current_week = True
    
    # Calculate week_end (Sunday)
    week_end = week_start + timedelta(days=6)
    
    # Generate week_dates (list of 7 dates, Mon-Sun)
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    
    # Get scheduled workouts for this week
    scheduled_workouts = []
    if cycle:
        scheduled_workouts = db_cycles.get_scheduled_workouts_for_week(user['id'], week_start)
    
    # Organize workouts by day of week (0=Monday, 6=Sunday)
    scheduled_by_day = {}
    for workout in scheduled_workouts:
        workout_date = datetime.strptime(workout['scheduled_date'], '%Y-%m-%d').date()
        day_index = workout_date.weekday()
        if day_index not in scheduled_by_day:
            scheduled_by_day[day_index] = []
        scheduled_by_day[day_index].append(workout)
    
    # Calculate week stats
    total_scheduled = len(scheduled_workouts)
    completed = sum(1 for w in scheduled_workouts if w.get('status') == 'completed')
    scheduled_remaining = sum(1 for w in scheduled_workouts if w.get('status') in ('scheduled', 'rescheduled'))
    
    week_stats = {
        'total': total_scheduled,
        'completed': completed,
        'scheduled': scheduled_remaining,
        'completion_rate': round((completed / total_scheduled * 100) if total_scheduled > 0 else 0)
    }
    
    # Find next workout (first scheduled or rescheduled workout from today forward)
    next_workout = None
    for workout in sorted(scheduled_workouts, key=lambda w: w['scheduled_date']):
        workout_date = datetime.strptime(workout['scheduled_date'], '%Y-%m-%d').date()
        if workout.get('status') in ['scheduled', 'rescheduled'] and workout_date >= today:
            next_workout = workout
            break
    
    return render_template('plan.html', 
                         user=user, 
                         cycle=cycle,
                         current_week=current_week,
                         week_start=week_start,
                         week_end=week_end,
                         week_dates=week_dates,
                         scheduled_by_day=scheduled_by_day,
                         today=today,
                         is_current_week=is_current_week,
                         week_stats=week_stats,
                         next_workout=next_workout)


@app.route('/cycle/new')
@login_required
def cycle_new():
    """Create new cycle wizard."""
    user = get_current_user()
    profile = db.get_user_profile(user['id'])
    
    # Get previous cycle for copy option
    previous_cycle = db_cycles.get_previous_cycle(user['id'])
    
    # Get all exercises for selection
    try:
        exercises = db.get_all_exercises()
    except:
        from data.routines import EXERCISES
        exercises = list(EXERCISES.values())
    
    # Calculate next Monday for default start date
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, use next Monday
    next_monday = today + timedelta(days=days_until_monday)
    
    return render_template('cycle_new.html', 
                         user=user, 
                         profile=profile,
                         previous_cycle=previous_cycle,
                         exercises=exercises,
                         today=today,
                         next_monday=next_monday)


@app.route('/cycle/<cycle_id>')
@login_required
def cycle_view(cycle_id):
    """View/edit a specific cycle."""
    user = get_current_user()
    
    cycle = db_cycles.get_cycle_by_id(cycle_id)
    if not cycle:
        flash('Cycle not found.', 'error')
        return redirect(url_for('plan'))
    
    # Get workout slots and exercises
    workout_slots = db_cycles.get_cycle_workout_slots(cycle_id)
    exercises = db_cycles.get_cycle_exercises(cycle_id)
    
    # Organize exercises by slot
    exercises_by_slot = {}
    for ex in exercises:
        slot_id = ex['cycle_workout_slot_id']
        if slot_id not in exercises_by_slot:
            exercises_by_slot[slot_id] = []
        exercises_by_slot[slot_id].append(ex)
    
    # Calculate stats
    total_workouts = len(workout_slots) * cycle.get('length_weeks', 6)
    completed_workouts = 0
    current_week = 1
    progress_by_week = {}
    
    # Initialize progress_by_week
    for week in range(1, cycle.get('length_weeks', 6) + 1):
        progress_by_week[week] = {'completed': 0, 'total': len(workout_slots)}
    
    # Try to get scheduled workouts for stats
    try:
        scheduled = db_cycles.get_scheduled_workouts_for_cycle(cycle_id)
        for w in scheduled:
            week_num = w.get('week_number', 1)
            if w.get('status') == 'completed':
                completed_workouts += 1
                if week_num in progress_by_week:
                    progress_by_week[week_num]['completed'] += 1
        
        # Calculate current week based on start date
        if cycle.get('start_date'):
            start = datetime.strptime(cycle['start_date'], '%Y-%m-%d').date()
            days_elapsed = (date.today() - start).days
            current_week = max(1, min(cycle.get('length_weeks', 6), (days_elapsed // 7) + 1))
    except Exception as e:
        print(f"Error calculating stats: {e}")
    
    stats = {
        'total': total_workouts,
        'completed': completed_workouts,
        'completion_rate': round((completed_workouts / total_workouts * 100) if total_workouts > 0 else 0)
    }
    
    # Calculate end date
    end_date = ''
    if cycle.get('start_date'):
        start = datetime.strptime(cycle['start_date'], '%Y-%m-%d').date()
        end = start + timedelta(weeks=cycle.get('length_weeks', 6))
        end_date = end.strftime('%Y-%m-%d')
    
    return render_template('cycle_view.html',
                         user=user,
                         cycle=cycle,
                         workout_slots=workout_slots,
                         exercises_by_slot=exercises_by_slot,
                         stats=stats,
                         current_week=current_week,
                         end_date=end_date,
                         progress_by_week=progress_by_week)


@app.route('/workout/schedule/<scheduled_id>')
@login_required
def workout_from_schedule(scheduled_id):
    """Start a workout from the scheduled calendar - loads cycle-specific exercises."""
    user = get_current_user()
    
    # Get the scheduled workout
    supabase = db.get_supabase_client()
    
    try:
        # Fetch the scheduled workout with its slot info
        scheduled_response = supabase.table('scheduled_workouts')\
            .select('*, cycle_workout_slots(*)')\
            .eq('id', scheduled_id)\
            .single()\
            .execute()
        
        scheduled_workout = scheduled_response.data
        if not scheduled_workout:
            flash('Scheduled workout not found.', 'error')
            return redirect(url_for('plan'))
        
        slot = scheduled_workout.get('cycle_workout_slots')
        if not slot:
            flash('Workout slot not found.', 'error')
            return redirect(url_for('plan'))
        
        cycle_id = scheduled_workout['cycle_id']
        slot_id = slot['id']
        week_number = scheduled_workout.get('week_number', 1)
        
        # Get cycle to determine rotation_weeks
        cycle = db_cycles.get_cycle_by_id(cycle_id)
        rotation_weeks = cycle.get('rotation_weeks', 1) if cycle else 1
        
        # Get exercises for this slot and week (with fallback to all-weeks exercises)
        cycle_exercises = db_cycles.get_cycle_exercises_for_week(
            cycle_id=cycle_id,
            slot_id=slot_id,
            week_number=week_number
        )
        
        # Build the day data structure that workout.html expects
        day = {
            'id': slot_id,
            'name': slot.get('workout_name', 'Workout'),
            'day_number': week_number,
            'focus': slot.get('is_heavy_focus', []),
            'exercises': []
        }
        
        # Determine if this is a heavy or light day for each exercise
        heavy_focuses = slot.get('is_heavy_focus', [])
        
        for ce in cycle_exercises:
            exercise_data = ce.get('exercises', {}) or {}
            
            # Determine if this exercise should use heavy or light settings
            is_heavy = ce.get('is_heavy', False)
            
            # Use the appropriate sets/reps based on heavy vs light
            if is_heavy:
                sets = ce.get('sets_heavy', 4)
                rep_range = ce.get('rep_range_heavy', '6-8')
                rest_seconds = ce.get('rest_seconds_heavy', 180)
            else:
                sets = ce.get('sets_light', 3)
                rep_range = ce.get('rep_range_light', '10-12')
                rest_seconds = ce.get('rest_seconds_light', 90)
            
            day['exercises'].append({
                'id': ce.get('exercise_id'),
                'name': ce.get('exercise_name', exercise_data.get('name', 'Unknown')),
                'muscle_group': ce.get('muscle_group', exercise_data.get('muscle_group', '')),
                'equipment': exercise_data.get('equipment', ''),
                'cues': exercise_data.get('cues', []),
                'video_url': exercise_data.get('video_url', ''),
                'is_compound': exercise_data.get('is_compound', False),
                'sets': sets,
                'rep_range': rep_range,
                'rest_seconds': rest_seconds,
                'is_heavy': is_heavy
            })
        
        # If no exercises found, show error
        if not day['exercises']:
            flash('No exercises found for this workout. Please set up your cycle exercises.', 'error')
            return redirect(url_for('plan'))
        
        # Get cycle info for display
        total_days = cycle.get('length_weeks', 6) * 3  # Approximate
        
        return render_template('workout_cycle.html',
                             day=day,
                             scheduled_workout=scheduled_workout,
                             cycle=cycle,
                             day_number=week_number,
                             total_days=total_days,
                             user=user)
        
    except Exception as e:
        print(f"Error loading scheduled workout: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading workout: {str(e)}', 'error')
        return redirect(url_for('plan'))


# ============================================
# API ROUTES
# ============================================

@app.route('/api/workout/start', methods=['POST'])
def api_start_workout():
    """Start a new workout session."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    template_id = data.get('template_id')
    template_name = data.get('template_name')
    
    workout = db.create_user_workout(
        user['id'],
        template_id,
        template_name,
        user.get('access_token', '')
    )
    
    if workout:
        return jsonify({'workout_id': workout['id']})
    return jsonify({'error': 'Failed to create workout'}), 500


@app.route('/api/workout/<workout_id>/complete', methods=['POST'])
def api_complete_workout(workout_id):
    """Complete a workout and save all sets."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    sets_data = data.get('sets', [])
    
    # Save sets
    db.save_workout_sets(
        workout_id,
        sets_data,
        user.get('access_token', '')
    )
    
    # Mark workout complete
    workout = db.complete_user_workout(
        workout_id,
        user.get('access_token', '')
    )
    
    if workout:
        return jsonify({'success': True, 'workout': workout})
    return jsonify({'error': 'Failed to complete workout'}), 500


@app.route('/api/workout/save-cycle', methods=['POST'])
@login_required
def api_save_cycle_workout():
    """Save a cycle-based workout and mark scheduled workout as completed."""
    user = get_current_user()
    
    data = request.json
    scheduled_id = data.get('scheduled_id')
    
    # Create the workout record
    workout = db.create_user_workout(
        user['id'],
        None,  # template_id - not used for cycle-based workouts
        data.get('workout_name', 'Workout'),
        user.get('access_token', '')
    )
    
    if not workout:
        return jsonify({'error': 'Failed to create workout'}), 500
    
    # Save sets
    sets_data = []
    for exercise in data.get('exercises', []):
        for i, s in enumerate(exercise.get('sets', [])):
            if s.get('completed'):
                sets_data.append({
                    'exercise_id': exercise.get('id'),
                    'exercise_name': exercise.get('name'),
                    'set_number': i + 1,
                    'weight': s.get('weight'),
                    'reps': s.get('reps'),
                    'completed': True
                })
    
    db.save_workout_sets(
        workout['id'],
        sets_data,
        user.get('access_token', '')
    )
    
    # Mark workout complete
    db.complete_user_workout(
        workout['id'],
        user.get('access_token', '')
    )
    
    # Mark the scheduled workout as completed
    if scheduled_id:
        db_cycles.complete_scheduled_workout(scheduled_id, workout['id'])
    
    return jsonify({'success': True, 'workout_id': workout['id']})


@app.route('/api/workout/save-local', methods=['POST'])
def api_save_local_workout():
    """Save a workout that was stored locally (for logged-in users syncing)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    # Create the workout
    workout = db.create_user_workout(
        user['id'],
        data.get('template_id'),
        data.get('template_name', 'Workout'),
        user.get('access_token', '')
    )
    
    if not workout:
        return jsonify({'error': 'Failed to create workout'}), 500
    
    # Save sets
    sets_data = []
    for exercise in data.get('exercises', []):
        for i, s in enumerate(exercise.get('sets', [])):
            if s.get('completed'):
                sets_data.append({
                    'exercise_id': exercise.get('id'),
                    'exercise_name': exercise.get('name'),
                    'set_number': i + 1,
                    'weight': s.get('weight'),
                    'reps': s.get('reps'),
                    'completed': True
                })
    
    db.save_workout_sets(
        workout['id'],
        sets_data,
        user.get('access_token', '')
    )
    
    # Mark complete
    db.complete_user_workout(
        workout['id'],
        user.get('access_token', '')
    )
    
    return jsonify({'success': True, 'workout_id': workout['id']})


@app.route('/api/exercises')
def api_exercises():
    """API endpoint to get all exercises."""
    try:
        exercises = db.get_all_exercises()
        return jsonify(exercises)
    except:
        from data.routines import EXERCISES
        return jsonify(list(EXERCISES.values()))


@app.route('/api/exercises/<muscle_group>')
def api_exercises_by_muscle(muscle_group):
    """API endpoint to get exercises by muscle group."""
    try:
        exercises = db.get_exercises_by_muscle_group(muscle_group)
        return jsonify(exercises)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/exercises/<muscle_group>/substitutes')
def api_exercise_substitutes(muscle_group):
    """Get substitute exercises for a muscle group."""
    current = request.args.get('current')
    equipment = request.args.get('equipment')
    
    try:
        substitutes = db_cycles.get_exercise_substitutions(
            exercise_id=current,
            muscle_group=muscle_group,
            equipment=equipment
        )
        return jsonify(substitutes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/exercises/add', methods=['POST'])
def api_add_exercise():
    """Add a new exercise to the library."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    name = data.get('name', '').strip()
    muscle_group = data.get('muscle_group', '')
    equipment = data.get('equipment', '')
    cues = data.get('cues', [])
    
    if not name or not muscle_group:
        return jsonify({'error': 'Name and muscle group required'}), 400
    
    try:
        supabase = db.get_supabase_client()
        response = supabase.table('exercises').insert({
            'name': name,
            'muscle_group': muscle_group,
            'equipment': equipment,
            'is_compound': False,
            'cues': cues if cues else []
        }).execute()
        
        if response.data:
            return jsonify(response.data[0])
        return jsonify({'error': 'Failed to add exercise'}), 500
    except Exception as e:
        print(f"Add exercise error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exercises/generate-cues', methods=['POST'])
def api_generate_cues():
    """Generate form cues for an exercise using AI."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    name = data.get('name', '').strip()
    muscle_group = data.get('muscle_group', '')
    equipment = data.get('equipment', '')
    
    if not name:
        return jsonify({'error': 'Exercise name required'}), 400
    
    try:
        import requests
        
        # Use Anthropic API to generate cues
        api_key = app.config.get('ANTHROPIC_API_KEY') or ''
        
        if not api_key:
            # Return default cues if no API key
            default_cues = [
                "Maintain proper form throughout",
                "Control the movement on both concentric and eccentric phases",
                "Breathe steadily - exhale on exertion",
                "Focus on mind-muscle connection"
            ]
            return jsonify({'cues': default_cues, 'generated': False})
        
        prompt = f"""Generate 3-5 concise, actionable form cues for the exercise "{name}".
Equipment: {equipment or 'bodyweight'}
Target muscle group: {muscle_group}

Return ONLY a JSON array of strings, each string being one form cue. Example:
["Cue 1", "Cue 2", "Cue 3"]

Focus on:
- Proper body positioning
- Movement execution
- Common mistakes to avoid
- Muscle engagement tips"""

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 500,
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '[]')
            # Parse the JSON array from the response
            import json
            cues = json.loads(content)
            return jsonify({'cues': cues, 'generated': True})
        else:
            raise Exception(f"API error: {response.status_code}")
            
    except Exception as e:
        print(f"Generate cues error: {e}")
        # Return sensible defaults on error
        default_cues = [
            "Maintain proper form throughout",
            "Control the movement",
            "Breathe steadily"
        ]
        return jsonify({'cues': default_cues, 'generated': False, 'error': str(e)})


@app.route('/api/exercises/<exercise_id>/suggest-video')
def api_suggest_video(exercise_id):
    """Search YouTube for a short demo video for an exercise."""
    exercise_name = request.args.get('name', '')
    exclude_ids = [x for x in request.args.get('exclude', '').split(',') if x]
    
    if not exercise_name:
        return jsonify({'error': 'Exercise name required'}), 400
    
    youtube_api_key = app.config.get('YOUTUBE_API_KEY') or ''
    
    if not youtube_api_key:
        return jsonify({'error': 'YouTube API not configured', 'video': None})
    
    try:
        import requests
        
        # Search for short exercise form demos
        search_query = f"{exercise_name} form demo"
        
        response = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoDuration': 'short',
                'maxResults': 10,
                'order': 'relevance',
                'safeSearch': 'strict',
                'key': youtube_api_key
            },
            timeout=10
        )
        
        if response.status_code != 200:
            error_data = response.json()
            print(f"YouTube API error: {error_data}")
            return jsonify({'error': 'YouTube search failed', 'details': error_data}), 500
        
        data = response.json()
        items = data.get('items', [])
        
        # Filter out excluded videos
        items = [item for item in items if item['id']['videoId'] not in exclude_ids]
        
        if not items:
            return jsonify({'video': None, 'message': 'No more videos found'})
        
        # Get video details to check duration
        video_ids = ','.join([item['id']['videoId'] for item in items])
        
        details_response = requests.get(
            'https://www.googleapis.com/youtube/v3/videos',
            params={
                'part': 'contentDetails,snippet',
                'id': video_ids,
                'key': youtube_api_key
            },
            timeout=10
        )
        
        if details_response.status_code == 200:
            details_data = details_response.json()
            videos = [v for v in details_data.get('items', []) if v['id'] not in exclude_ids]
            
            # Find the first video under 30 seconds
            for video in videos:
                duration = video['contentDetails']['duration']
                seconds = parse_youtube_duration(duration)
                
                if seconds <= 30:
                    video_id = video['id']
                    return jsonify({
                        'video': {
                            'id': video_id,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'embed_url': f'https://www.youtube.com/embed/{video_id}',
                            'thumbnail': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
                            'title': video['snippet']['title'],
                            'channel': video['snippet']['channelTitle'],
                            'duration': seconds
                        }
                    })
            
            # If no videos under 30 seconds, return the shortest one
            if videos:
                shortest = min(videos, key=lambda v: parse_youtube_duration(v['contentDetails']['duration']))
                video_id = shortest['id']
                return jsonify({
                    'video': {
                        'id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'thumbnail': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
                        'title': shortest['snippet']['title'],
                        'channel': shortest['snippet']['channelTitle'],
                        'duration': parse_youtube_duration(shortest['contentDetails']['duration'])
                    },
                    'note': 'No videos under 1 minute found, showing shortest available'
                })
            else:
                return jsonify({'video': None, 'message': 'No more videos found'})
        
        # Fallback to first search result
        if items:
            first = items[0]
            video_id = first['id']['videoId']
            return jsonify({
                'video': {
                    'id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'embed_url': f'https://www.youtube.com/embed/{video_id}',
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
                    'title': first['snippet']['title'],
                    'channel': first['snippet']['channelTitle']
                }
            })
        
        return jsonify({'video': None, 'message': 'No more videos found'})
        
    except Exception as e:
        print(f"YouTube search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'video': None}), 500


def parse_youtube_duration(duration: str) -> int:
    """Parse ISO 8601 duration (PT1M30S) to seconds."""
    import re
    
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    return 0


@app.route('/api/exercises/<exercise_id>/save-video', methods=['POST'])
def api_save_video(exercise_id):
    """Save approved video URL to an exercise."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    video_url = data.get('video_url', '').strip()
    
    if not video_url:
        return jsonify({'error': 'Video URL required'}), 400
    
    try:
        supabase = db.get_supabase_client()
        
        response = supabase.table('exercises')\
            .update({'video_url': video_url})\
            .eq('id', exercise_id)\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'exercise': response.data[0]})
        return jsonify({'error': 'Exercise not found'}), 404
        
    except Exception as e:
        print(f"Save video error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exercises/<exercise_id>/clear-video', methods=['POST'])
def api_clear_video(exercise_id):
    """Clear video URL from an exercise."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = db.get_supabase_client()
        
        response = supabase.table('exercises')\
            .update({'video_url': None})\
            .eq('id', exercise_id)\
            .execute()
        
        if response.data:
            return jsonify({'success': True})
        return jsonify({'error': 'Exercise not found'}), 404
        
    except Exception as e:
        print(f"Clear video error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/routine/<routine_id>')
def api_routine(routine_id):
    """API endpoint to get a routine."""
    try:
        routine = db.get_routine(routine_id)
        if routine:
            return jsonify(routine)
        return jsonify({'error': 'Routine not found'}), 404
    except:
        from data.routines import get_routine as get_local_routine
        routine = get_local_routine(routine_id)
        if routine:
            return jsonify(routine)
        return jsonify({'error': 'Routine not found'}), 404


@app.route('/api/debug/cycles')
def api_debug_cycles():
    """Debug endpoint to check cycles table."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not logged in', 'user': None})
    
    try:
        supabase = db.get_supabase_client()
        all_cycles = supabase.table('cycles').select('*').eq('user_id', user['id']).execute()
        active = db_cycles.get_active_cycle(user['id'])
        
        return jsonify({
            'user_id': user['id'],
            'all_cycles': all_cycles.data,
            'active_cycle': active,
            'cycle_count': len(all_cycles.data) if all_cycles.data else 0
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()})


@app.route('/api/schedule/preview')
def api_schedule_preview():
    """Generate and return a schedule preview based on split type and days per week."""
    split_type = request.args.get('split', 'ppl')
    days_per_week = request.args.get('days', 3, type=int)
    
    if days_per_week < 2 or days_per_week > 6:
        return jsonify({'error': 'Days per week must be between 2 and 6'}), 400
    
    valid_splits = ['full_body', 'upper_lower', 'ppl', 'custom']
    if split_type not in valid_splits:
        return jsonify({'error': f'Invalid split type. Must be one of: {valid_splits}'}), 400
    
    try:
        schedule = workout_generator.generate_schedule_dict(split_type, days_per_week)
        return jsonify(schedule)
    except Exception as e:
        print(f"Schedule preview error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile/preferred-days')
@login_required
def api_profile_preferred_days():
    """Get the user's preferred training days."""
    user = get_current_user()
    profile = db.get_user_profile(user['id'])
    
    if profile and profile.get('preferred_days'):
        return jsonify({'preferred_days': profile['preferred_days']})
    
    return jsonify({'preferred_days': ['monday', 'wednesday', 'friday']})


# ============================================
# PROFILE API
# ============================================

@app.route('/api/profile/settings', methods=['POST'])
def api_profile_settings():
    """Update user profile training settings."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    print(f"Profile settings update request: {data}")
    
    # Handle pr_rep_threshold directly
    if 'pr_rep_threshold' in data:
        result = db.update_user_profile(user['id'], {'pr_rep_threshold': data['pr_rep_threshold']})
        print(f"PR threshold update result: {result}")
        if result:
            return jsonify({'success': True, 'pr_rep_threshold': data['pr_rep_threshold']})
        return jsonify({'error': 'Failed to update PR threshold'}), 500

    try:
        result = db_cycles.update_profile_training_settings(
            user_id=user['id'],
            email=user.get('email'),
            split_type=data.get('split_type'),
            days_per_week=data.get('days_per_week'),
            cycle_length_weeks=data.get('cycle_length_weeks'),
            preferred_days=data.get('preferred_days')
        )
        
        print(f"Profile update result: {result}")
        
        if result:
            return jsonify({'success': True, 'profile': result})
        return jsonify({'error': 'Failed to update settings - no result returned'}), 500
        
    except Exception as e:
        import traceback
        print(f"Profile update error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e), 'details': traceback.format_exc()}), 500


# ============================================
# CYCLE API
# ============================================

@app.route('/api/cycle/create', methods=['POST'])
def api_create_cycle():
    """Create a new training cycle with support for per-week exercises."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    try:
        # Parse start date
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        # Get rotation_weeks from the schedule (for rotating splits)
        rotation_weeks = data.get('rotation_weeks', 1)
        
        # Create cycle with rotation_weeks
        supabase = db.get_supabase_client()
        cycle_response = supabase.table('cycles').insert({
            'user_id': user['id'],
            'name': data.get('name', f"Cycle starting {start_date}"),
            'start_date': start_date.isoformat(),
            'length_weeks': data.get('length_weeks', 6),
            'split_type': data.get('split_type', 'ppl'),
            'status': 'planning',
            'rotation_weeks': rotation_weeks
        }).execute()
        
        if not cycle_response.data:
            return jsonify({'error': 'Failed to create cycle'}), 500
        
        cycle = cycle_response.data[0]
        
        # Handle workout_slots with nested exercises and week_pattern
        workout_slots = data.get('workout_slots', [])
        
        # Collect ALL exercises for bulk insert
        all_exercises = []
        
        # Create workout slots
        created_slots = []
        for i, slot_data in enumerate(workout_slots):
            slot = db_cycles.create_cycle_workout_slot(
                cycle_id=cycle['id'],
                day_of_week=slot_data.get('day_of_week', slot_data.get('dayOfWeek', i)),
                template_id=slot_data.get('template_id'),
                workout_name=slot_data.get('workout_name', slot_data.get('workoutName', f'Workout {i+1}')),
                is_heavy_focus=slot_data.get('is_heavy_focus', slot_data.get('heavyFocus', [])),
                order_index=slot_data.get('order_index', i),
                week_pattern=slot_data.get('week_pattern')
            )
            if slot:
                created_slots.append(slot)
                
                # Collect exercises for this slot (base exercises for all weeks)
                slot_exercises = slot_data.get('exercises', [])
                for j, ex_data in enumerate(slot_exercises):
                    all_exercises.append({
                        'cycle_id': cycle['id'],
                        'slot_id': slot['id'],
                        'exercise_id': ex_data.get('exercise_id', ex_data.get('id')),
                        'exercise_name': ex_data.get('exercise_name', ex_data.get('name')),
                        'muscle_group': ex_data.get('muscle_group', ''),
                        'is_heavy': ex_data.get('is_heavy', False),
                        'order_index': j,
                        'sets_heavy': ex_data.get('sets_heavy', 4),
                        'sets_light': ex_data.get('sets_light', 3),
                        'rep_range_heavy': ex_data.get('rep_range_heavy', '6-8'),
                        'rep_range_light': ex_data.get('rep_range_light', '10-12'),
                        'rest_heavy': ex_data.get('rest_heavy', 180),
                        'rest_light': ex_data.get('rest_light', 90),
                        'week_number': None  # Base exercises apply to all weeks
                    })
        
        # Handle weekly_exercises structure (per-week customizations)
        weekly_exercises = data.get('weekly_exercises', {})
        
        if weekly_exercises:
            for week_num_str, week_workouts in weekly_exercises.items():
                week_num = int(week_num_str)
                
                for workout_idx_str, exercises in week_workouts.items():
                    workout_idx = int(workout_idx_str)
                    
                    if workout_idx < len(created_slots):
                        slot = created_slots[workout_idx]
                        
                        if week_num > 1:
                            # Collect week-specific exercises
                            for j, ex_data in enumerate(exercises):
                                all_exercises.append({
                                    'cycle_id': cycle['id'],
                                    'slot_id': slot['id'],
                                    'exercise_id': ex_data.get('exercise_id', ex_data.get('id')),
                                    'exercise_name': ex_data.get('exercise_name', ex_data.get('name')),
                                    'muscle_group': ex_data.get('muscle_group', ''),
                                    'is_heavy': ex_data.get('is_heavy', False),
                                    'order_index': j,
                                    'sets_heavy': ex_data.get('sets_heavy', 4),
                                    'sets_light': ex_data.get('sets_light', 3),
                                    'rep_range_heavy': ex_data.get('rep_range_heavy', '6-8'),
                                    'rep_range_light': ex_data.get('rep_range_light', '10-12'),
                                    'rest_heavy': ex_data.get('rest_heavy', 180),
                                    'rest_light': ex_data.get('rest_light', 90),
                                    'week_number': week_num
                                })
        
        # BULK INSERT all exercises in one database call
        if all_exercises:
            db_cycles.create_cycle_exercises_bulk(all_exercises)
        
        # Generate the schedule for all weeks (with rotation support)
        if created_slots:
            db_cycles.generate_cycle_schedule(
                user_id=user['id'],
                cycle_id=cycle['id'],
                start_date=start_date,
                length_weeks=data.get('length_weeks', 6),
                workout_slots=created_slots,
                rotation_weeks=rotation_weeks
            )
        
        # Activate the cycle immediately
        db_cycles.activate_cycle(cycle['id'])
        
        return jsonify({'success': True, 'cycle': cycle, 'cycle_id': cycle['id']})
        
    except Exception as e:
        print(f"Create cycle error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'code': getattr(e, 'code', None)}), 500


@app.route('/api/cycle/<cycle_id>/activate', methods=['POST'])
def api_activate_cycle(cycle_id):
    """Activate a cycle and generate schedule."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get cycle details
        cycle = db_cycles.get_cycle_by_id(cycle_id)
        if not cycle:
            return jsonify({'error': 'Cycle not found'}), 404
        
        # Get workout slots
        slots = db_cycles.get_cycle_workout_slots(cycle_id)
        
        # Generate schedule
        start_date = datetime.strptime(cycle['start_date'], '%Y-%m-%d').date()
        rotation_weeks = cycle.get('rotation_weeks', 1)
        
        db_cycles.generate_cycle_schedule(
            user_id=user['id'],
            cycle_id=cycle_id,
            start_date=start_date,
            length_weeks=cycle['length_weeks'],
            workout_slots=slots,
            rotation_weeks=rotation_weeks
        )
        
        # Activate cycle
        result = db_cycles.activate_cycle(cycle_id)
        
        return jsonify({'success': True, 'cycle': result})
        
    except Exception as e:
        print(f"Activate cycle error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cycle/<cycle_id>/complete', methods=['POST'])
def api_complete_cycle(cycle_id):
    """Mark a cycle as completed."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        result = db_cycles.complete_cycle(cycle_id)
        return jsonify({'success': True, 'cycle': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cycle/<cycle_id>/delete', methods=['POST', 'DELETE'])
@login_required
def api_delete_cycle(cycle_id):
    """Delete a cycle and all associated data."""
    user = get_current_user()
    
    try:
        supabase = db.get_supabase_client()
        
        # Delete in order due to foreign keys
        supabase.table('scheduled_workouts').delete().eq('cycle_id', cycle_id).execute()
        supabase.table('cycle_exercises').delete().eq('cycle_id', cycle_id).execute()
        supabase.table('cycle_workout_slots').delete().eq('cycle_id', cycle_id).execute()
        supabase.table('cycles').delete().eq('id', cycle_id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Delete cycle error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/<scheduled_id>/reschedule', methods=['POST'])
def api_reschedule_workout(scheduled_id):
    """Reschedule a workout."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    new_date = datetime.strptime(data['new_date'], '%Y-%m-%d').date()
    
    try:
        # Check if workout is already completed
        workout = db_cycles.get_scheduled_workout_by_id(scheduled_id)
        if workout and workout.get('status') == 'completed':
            return jsonify({'error': 'Cannot reschedule a completed workout'}), 400
        
        result = db_cycles.reschedule_workout(scheduled_id, new_date)
        return jsonify({'success': True, 'workout': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/clean', methods=['POST'])
def api_debug_clean():
    """Clean all cycle data for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = db.get_supabase_client()
        
        cycles_resp = supabase.table('cycles').select('id').eq('user_id', user['id']).execute()
        cycle_ids = [c['id'] for c in (cycles_resp.data or [])]
        
        deleted = {'scheduled_workouts': 0, 'cycle_exercises': 0, 'cycle_workout_slots': 0, 'cycles': 0}
        
        if cycle_ids:
            resp = supabase.table('scheduled_workouts').delete().eq('user_id', user['id']).execute()
            deleted['scheduled_workouts'] = len(resp.data) if resp.data else 0
            
            for cid in cycle_ids:
                resp = supabase.table('cycle_exercises').delete().eq('cycle_id', cid).execute()
                deleted['cycle_exercises'] += len(resp.data) if resp.data else 0
            
            for cid in cycle_ids:
                resp = supabase.table('cycle_workout_slots').delete().eq('cycle_id', cid).execute()
                deleted['cycle_workout_slots'] += len(resp.data) if resp.data else 0
            
            resp = supabase.table('cycles').delete().eq('user_id', user['id']).execute()
            deleted['cycles'] = len(resp.data) if resp.data else 0
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/debug/schedule')
def api_debug_schedule():
    """Debug endpoint to check schedule data."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        cycle = db_cycles.get_active_cycle(user['id'])
        supabase = db.get_supabase_client()
        
        cycles_resp = supabase.table('cycles').select('*').eq('user_id', user['id']).execute()
        scheduled_resp = supabase.table('scheduled_workouts').select('*').eq('user_id', user['id']).execute()
        
        slots_resp = None
        if cycle:
            slots_resp = supabase.table('cycle_workout_slots').select('*').eq('cycle_id', cycle['id']).execute()
        
        return jsonify({
            'user_id': user['id'],
            'active_cycle': cycle,
            'all_cycles': cycles_resp.data if cycles_resp else [],
            'all_scheduled_workouts': scheduled_resp.data if scheduled_resp else [],
            'cycle_workout_slots': slots_resp.data if slots_resp else [],
            'today': date.today().isoformat()
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/schedule/<scheduled_id>/skip', methods=['POST'])
def api_skip_workout(scheduled_id):
    """Skip a scheduled workout."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json or {}
    
    try:
        result = db_cycles.skip_scheduled_workout(scheduled_id, data.get('notes'))
        return jsonify({'success': True, 'workout': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# EXPORT ROUTES
# ============================================

@app.route('/api/export/csv')
@login_required
def export_csv():
    """Export workout data as CSV."""
    user = get_current_user()
    
    # Parse date range from query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate CSV
    csv_data = db_export.generate_csv(user['id'], start_date, end_date)
    
    # Create response with CSV
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    
    # Filename with date range
    if start_date and end_date:
        filename = f"workout_export_{start_date}_{end_date}.csv"
    else:
        filename = f"workout_export_all_time.csv"
    
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


@app.route('/api/export/pdf')
@login_required
def export_pdf():
    """Export workout report as PDF."""
    user = get_current_user()
    
    # Parse date range from query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get user name for report
    profile = db.get_user_profile(user['id'])
    user_name = profile.get('display_name', user['email'].split('@')[0]) if profile else user['email'].split('@')[0]
    
    # Generate PDF
    pdf_data = db_export.generate_pdf(user['id'], user_name, start_date, end_date)
    
    # Create response with PDF
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    
    # Filename with date range
    if start_date and end_date:
        filename = f"workout_report_{start_date}_{end_date}.pdf"
    else:
        filename = f"workout_report_all_time.pdf"
    
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

"""
Notification API Endpoints (Phase 5a)
Add these routes to your app.py file

Required imports to add at top of app.py:
    import db_notifications
    import notification_service
"""


# ============================================
# NOTIFICATION PREFERENCES API
# ============================================

@app.route('/api/notifications/preferences', methods=['GET'])
@login_required
def api_get_notification_preferences():
    """Get current user's notification preferences."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        prefs = db_notifications.get_notification_preferences(user['id'])
        return jsonify({'preferences': prefs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/preferences', methods=['POST'])
@login_required
def api_update_notification_preferences():
    """Update notification preferences."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    # Whitelist allowed fields
    allowed_fields = {
        'phone_number',
        'phone_confirmed',
        'workout_reminder_enabled',
        'workout_reminder_hours',
        'workout_reminder_channel',
        'inactivity_nudge_enabled',
        'inactivity_week_via_email',
        'inactivity_month_via_sms'
    }
    
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    try:
        result = db_notifications.upsert_notification_preferences(user['id'], updates)
        return jsonify({'success': True, 'preferences': result})
    except Exception as e:
        print(f"Notification preferences update error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/phone', methods=['POST'])
@login_required
def api_update_phone():
    """Update phone number with confirmation step."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    phone_number = data.get('phone_number', '').strip()
    confirmed = data.get('confirmed', False)
    
    # Basic phone validation (US format, can be expanded)
    import re
    phone_clean = re.sub(r'[^\d+]', '', phone_number)
    
    if phone_number and len(phone_clean) < 10:
        return jsonify({'error': 'Please enter a valid phone number'}), 400
    
    try:
        # Check if this is a NEW phone number (for welcome SMS)
        existing_prefs = db_notifications.get_notification_preferences(user['id'])
        is_new_phone = (
            confirmed and 
            phone_clean and 
            (not existing_prefs or existing_prefs.get('phone_number') != phone_clean)
        )
        
        result = db_notifications.update_phone_number(
            user['id'], 
            phone_clean if phone_number else None,
            confirmed=confirmed
        )
        
        # Send welcome SMS if this is a new confirmed phone number
        welcome_sms_result = None
        if is_new_phone:
            profile = db.get_user_profile(user['id'])
            user_name = profile.get('display_name') if profile else user['email'].split('@')[0]
            
            success, error = notification_service.send_welcome_sms(phone_clean, user_name)
            
            # Log the notification
            db_notifications.log_notification(
                user_id=user['id'],
                notification_type='welcome_sms',
                channel='sms',
                status='sent' if success else 'failed',
                error_message=error
            )
            
            welcome_sms_result = {'sent': success, 'error': error}
        
        return jsonify({
            'success': True, 
            'preferences': result,
            'welcome_sms': welcome_sms_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/history', methods=['GET'])
@login_required
def api_notification_history():
    """Get notification history for current user."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        history = db_notifications.get_notification_history(user['id'])
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# NOTIFICATION PREFERENCES PAGE ROUTE
# ============================================

@app.route('/notifications')
@login_required
def notifications_settings():
    """Notification settings page."""
    user = get_current_user()
    profile = db.get_user_profile(user['id'])
    prefs = db_notifications.get_notification_preferences(user['id'])
    
    # Only show test section in development
    is_debug = os.environ.get('FLASK_ENV') == 'development' or app.debug
    
    return render_template('notifications.html',
                         user=user,
                         profile=profile,
                         preferences=prefs,
                         is_debug=is_debug)


"""
Cron Job Handlers (Phase 5b)
These endpoints are called by cron-job.org to process notifications.

Add these routes to your app.py file.

Required imports to add at top of app.py:
    import notification_service
    from datetime import datetime, date, timedelta
"""

import os
from functools import wraps

# Simple secret key for cron job authentication
# Set this in your environment variables
CRON_SECRET = os.environ.get('CRON_SECRET', 'change-me-in-production')


def cron_auth_required(f):
    """
    Decorator to protect cron endpoints.
    Requires X-Cron-Secret header or ?secret= query param.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')
        if secret != CRON_SECRET:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================
# CRON ENDPOINTS
# ============================================

@app.route('/api/cron/notifications', methods=['GET', 'POST'])
@cron_auth_required
def cron_process_notifications():
    """
    Main cron endpoint - processes all notification types.
    Called hourly by cron-job.org.
    
    URL: https://your-app.onrender.com/api/cron/notifications?secret=YOUR_SECRET
    """
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'workout_reminders': {'processed': 0, 'sent': 0, 'errors': 0},
        'inactivity_week': {'processed': 0, 'sent': 0, 'errors': 0},
        'inactivity_month': {'processed': 0, 'sent': 0, 'errors': 0}
    }
    
    # Process workout reminders
    try:
        reminder_results = process_workout_reminders()
        results['workout_reminders'] = reminder_results
    except Exception as e:
        print(f"[CRON ERROR] Workout reminders failed: {e}")
        results['workout_reminders']['error'] = str(e)
    
    # Process inactivity nudges (only check once per day, early morning)
    current_hour = datetime.utcnow().hour
    if current_hour == 14:  # 2 PM UTC = ~6-9 AM across US timezones
        try:
            week_results = process_inactivity_nudges(days=7, nudge_type='inactivity_week')
            results['inactivity_week'] = week_results
        except Exception as e:
            print(f"[CRON ERROR] Week inactivity failed: {e}")
            results['inactivity_week']['error'] = str(e)
        
        try:
            month_results = process_inactivity_nudges(days=30, nudge_type='inactivity_month')
            results['inactivity_month'] = month_results
        except Exception as e:
            print(f"[CRON ERROR] Month inactivity failed: {e}")
            results['inactivity_month']['error'] = str(e)
    
    return jsonify(results)


@app.route('/api/cron/workout-reminders', methods=['GET', 'POST'])
@cron_auth_required
def cron_workout_reminders():
    """Process only workout reminders."""
    try:
        results = process_workout_reminders()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/inactivity', methods=['GET', 'POST'])
@cron_auth_required
def cron_inactivity():
    """Process only inactivity nudges."""
    results = {}
    
    try:
        results['week'] = process_inactivity_nudges(days=7, nudge_type='inactivity_week')
    except Exception as e:
        results['week'] = {'error': str(e)}
    
    try:
        results['month'] = process_inactivity_nudges(days=30, nudge_type='inactivity_month')
    except Exception as e:
        results['month'] = {'error': str(e)}
    
    return jsonify(results)


# ============================================
# NOTIFICATION PROCESSING LOGIC
# ============================================

def process_workout_reminders():
    """
    Find users with workouts scheduled today and send reminders
    based on their preferred reminder time (X hours before).
    """
    results = {'processed': 0, 'sent': 0, 'errors': 0, 'skipped': 0}
    
    # Get users who need reminders
    users_to_notify = db_notifications.get_users_for_workout_reminders(hours_ahead=24)
    
    now = datetime.utcnow()
    today = now.date()
    
    for user in users_to_notify:
        results['processed'] += 1
        
        user_id = user['user_id']
        workout_id = user['workout_id']
        reminder_hours = user.get('reminder_hours', 2)
        channel = user.get('channel', 'email')
        
        # Check if already sent
        if db_notifications.was_notification_sent(user_id, 'workout_reminder', reference_id=workout_id):
            results['skipped'] += 1
            continue
        
        # For now, send reminders for today's workouts
        # A more sophisticated version would calculate exact timing
        workout_date_str = user.get('scheduled_date')
        if workout_date_str:
            workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d').date()
            if workout_date != today:
                results['skipped'] += 1
                continue
        
        # Send notification
        user_name = user.get('display_name') or user.get('email', '').split('@')[0]
        workout_name = user.get('workout_name', 'Workout')
        
        success = False
        error_msg = None
        
        if channel == 'email' and user.get('email'):
            success, error_msg = notification_service.send_workout_reminder_email(
                to_email=user['email'],
                user_name=user_name,
                workout_name=workout_name
            )
        elif channel == 'sms' and user.get('phone_number'):
            success, error_msg = notification_service.send_workout_reminder_sms(
                to_phone=user['phone_number'],
                user_name=user_name,
                workout_name=workout_name
            )
        else:
            error_msg = f"No valid {channel} address"
        
        # Log the notification
        db_notifications.log_notification(
            user_id=user_id,
            notification_type='workout_reminder',
            channel=channel,
            reference_id=workout_id,
            status='sent' if success else 'failed',
            error_message=error_msg
        )
        
        if success:
            results['sent'] += 1
        else:
            results['errors'] += 1
    
    return results


def process_inactivity_nudges(days: int, nudge_type: str):
    """
    Find users who haven't worked out in X days and send nudges.
    """
    results = {'processed': 0, 'sent': 0, 'errors': 0, 'skipped': 0}
    
    users_to_notify = db_notifications.get_users_for_inactivity_nudge(days_inactive=days)
    today = date.today()
    
    for user in users_to_notify:
        results['processed'] += 1
        
        user_id = user['user_id']
        channel = user.get('channel', 'email')
        
        # Check if already sent today (prevent multiple nudges)
        if db_notifications.was_notification_sent(user_id, nudge_type, reference_date=today):
            results['skipped'] += 1
            continue
        
        # Also check if we've sent this nudge in the past week (don't spam)
        # For month nudge, only send once per month
        recent_cutoff = today - timedelta(days=7 if nudge_type == 'inactivity_week' else 30)
        if db_notifications.was_notification_sent(user_id, nudge_type, reference_date=recent_cutoff):
            results['skipped'] += 1
            continue
        
        user_name = user.get('display_name') or user.get('email', '').split('@')[0]
        last_workout = user.get('last_workout_date')
        
        success = False
        error_msg = None
        
        if nudge_type == 'inactivity_week':
            # Week nudge is always email
            if user.get('email'):
                success, error_msg = notification_service.send_inactivity_week_email(
                    to_email=user['email'],
                    user_name=user_name,
                    last_workout_date=last_workout
                )
            else:
                error_msg = "No email address"
                
        elif nudge_type == 'inactivity_month':
            # Month nudge can be SMS or email
            if channel == 'sms' and user.get('phone_number'):
                success, error_msg = notification_service.send_inactivity_month_sms(
                    to_phone=user['phone_number'],
                    user_name=user_name
                )
            elif user.get('email'):
                success, error_msg = notification_service.send_inactivity_month_email(
                    to_email=user['email'],
                    user_name=user_name,
                    last_workout_date=last_workout
                )
            else:
                error_msg = "No valid contact method"
        
        # Log the notification
        db_notifications.log_notification(
            user_id=user_id,
            notification_type=nudge_type,
            channel=channel,
            reference_date=today,
            status='sent' if success else 'failed',
            error_message=error_msg
        )
        
        if success:
            results['sent'] += 1
        else:
            results['errors'] += 1
    
    return results


# ============================================
# TEST ENDPOINT (for development)
# ============================================

@app.route('/api/cron/test-email', methods=['POST'])
@login_required
def test_notification_email():
    """
    Send a test email to the current user.
    For development/testing only.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    profile = db.get_user_profile(user['id'])
    user_name = profile.get('display_name') if profile else user['email'].split('@')[0]
    
    data = request.json or {}
    email_type = data.get('type', 'workout_reminder')
    
    if email_type == 'workout_reminder':
        success, error = notification_service.send_workout_reminder_email(
            to_email=user['email'],
            user_name=user_name,
            workout_name='Push Day (Test)'
        )
    elif email_type == 'inactivity_week':
        success, error = notification_service.send_inactivity_week_email(
            to_email=user['email'],
            user_name=user_name,
            last_workout_date='January 1, 2025'
        )
    elif email_type == 'inactivity_month':
        success, error = notification_service.send_inactivity_month_email(
            to_email=user['email'],
            user_name=user_name,
            last_workout_date='December 1, 2024'
        )
    else:
        return jsonify({'error': 'Invalid email type'}), 400
    
    if success:
        return jsonify({'success': True, 'message': f'Test email sent to {user["email"]}'})
    else:
        return jsonify({'success': False, 'error': error}), 500


@app.route('/api/cron/test-sms', methods=['POST'])
@login_required
def test_notification_sms():
    """
    Send a test SMS to the current user's phone.
    For development/testing only.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get user's phone number from notification preferences
    prefs = db_notifications.get_notification_preferences(user['id'])
    if not prefs or not prefs.get('phone_number'):
        return jsonify({'error': 'No phone number configured'}), 400
    
    phone_number = prefs['phone_number']
    
    profile = db.get_user_profile(user['id'])
    user_name = profile.get('display_name') if profile else user['email'].split('@')[0]
    
    data = request.json or {}
    sms_type = data.get('type', 'workout_reminder')
    
    if sms_type == 'workout_reminder':
        success, error = notification_service.send_workout_reminder_sms(
            to_phone=phone_number,
            user_name=user_name,
            workout_name='Push Day (Test)'
        )
    elif sms_type == 'welcome':
        success, error = notification_service.send_welcome_sms(
            to_phone=phone_number,
            user_name=user_name
        )
    elif sms_type == 'inactivity_month':
        success, error = notification_service.send_inactivity_month_sms(
            to_phone=phone_number,
            user_name=user_name
        )
    else:
        return jsonify({'error': 'Invalid SMS type'}), 400
    
    if success:
        return jsonify({'success': True, 'message': f'Test SMS sent to {phone_number}'})
    else:
        return jsonify({'success': False, 'error': error}), 500


"""
Social Features API Endpoints (Phase 6)
Add these routes to your app.py file

Required imports to add at top of app.py:
    import db_social
"""


# ============================================
# SHARE CYCLE ENDPOINTS
# ============================================

@app.route('/api/cycle/<cycle_id>/share', methods=['POST'])
@login_required
def api_share_cycle(cycle_id):
    """Share a cycle, generating a unique link."""
    user = get_current_user()
    data = request.json or {}
    
    # Verify user owns the cycle
    cycle = db_cycles.get_cycle_by_id(cycle_id)
    if not cycle or cycle.get('user_id') != user['id']:
        return jsonify({'error': 'Cycle not found'}), 404
    
    try:
        result = db_social.share_cycle(
            user_id=user['id'],
            cycle_id=cycle_id,
            is_public=data.get('is_public', False),
            is_template=data.get('is_template', False),
            title=data.get('title'),
            description=data.get('description'),
            tags=data.get('tags')
        )
        
        if result:
            share_url = f"{request.host_url}shared/cycle/{result['share_code']}"
            return jsonify({
                'success': True,
                'share_code': result['share_code'],
                'share_url': share_url,
                'is_public': result.get('is_public'),
                'is_template': result.get('is_template')
            })
        else:
            return jsonify({'error': 'Failed to share cycle'}), 500
            
    except Exception as e:
        print(f"Error sharing cycle: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cycle/<cycle_id>/unshare', methods=['POST'])
@login_required
def api_unshare_cycle(cycle_id):
    """Remove a cycle from sharing."""
    user = get_current_user()
    
    try:
        db_social.unshare_cycle(user['id'], cycle_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cycle/<cycle_id>/share-settings', methods=['GET'])
@login_required
def api_get_share_settings(cycle_id):
    """Get current share settings for a cycle."""
    user = get_current_user()
    
    shared_cycles = db_social.get_user_shared_cycles(user['id'])
    
    for shared in shared_cycles:
        if shared.get('cycle_id') == cycle_id:
            return jsonify({
                'is_shared': True,
                'share_code': shared['share_code'],
                'share_url': f"{request.host_url}shared/cycle/{shared['share_code']}",
                'is_public': shared.get('is_public', False),
                'is_template': shared.get('is_template', False),
                'title': shared.get('title'),
                'description': shared.get('description'),
                'tags': shared.get('tags', []),
                'copy_count': shared.get('copy_count', 0),
                'view_count': shared.get('view_count', 0)
            })
    
    return jsonify({'is_shared': False})


@app.route('/api/my-shared-cycles', methods=['GET'])
@login_required
def api_my_shared_cycles():
    """Get all cycles shared by current user."""
    user = get_current_user()
    
    try:
        cycles = db_social.get_user_shared_cycles(user['id'])
        
        # Add share URLs
        for cycle in cycles:
            cycle['share_url'] = f"{request.host_url}shared/cycle/{cycle['share_code']}"
        
        return jsonify({'cycles': cycles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# PUBLIC LIBRARY ENDPOINTS
# ============================================

@app.route('/api/library/cycles', methods=['GET'])
def api_library_cycles():
    """Get public cycles for the library (no auth required)."""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    split_type = request.args.get('split_type')
    sort_by = request.args.get('sort', 'recent')
    
    try:
        cycles = db_social.get_public_cycles(
            limit=min(limit, 50),  # Cap at 50
            offset=offset,
            split_type=split_type,
            sort_by=sort_by
        )
        
        # Clean up response
        for cycle in cycles:
            cycle['share_url'] = f"{request.host_url}shared/cycle/{cycle['share_code']}"
            # Get author name
            profile = cycle.get('profiles')
            if profile:
                cycle['author_name'] = profile.get('public_display_name') or profile.get('display_name') or 'Anonymous'
                cycle['is_trainer'] = profile.get('is_trainer', False)
            else:
                cycle['author_name'] = 'Anonymous'
                cycle['is_trainer'] = False
        
        return jsonify({'cycles': cycles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/library/templates', methods=['GET'])
def api_library_templates():
    """Get trainer templates."""
    trainer_id = request.args.get('trainer_id')
    
    try:
        templates = db_social.get_template_cycles(trainer_id)
        
        for template in templates:
            template['share_url'] = f"{request.host_url}shared/cycle/{template['share_code']}"
            profile = template.get('profiles')
            if profile:
                template['trainer_name'] = profile.get('public_display_name') or profile.get('display_name') or 'Trainer'
            else:
                template['trainer_name'] = 'Trainer'
        
        return jsonify({'templates': templates})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# COPY CYCLE ENDPOINT
# ============================================

@app.route('/api/shared/cycle/<share_code>/copy', methods=['POST'])
@login_required
def api_copy_shared_cycle(share_code):
    """Copy a shared cycle to user's account."""
    user = get_current_user()
    data = request.json or {}
    
    try:
        new_cycle_id, error = db_social.copy_shared_cycle(
            share_code=share_code,
            user_id=user['id'],
            new_name=data.get('name')
        )
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'cycle_id': new_cycle_id,
            'message': 'Cycle copied to your account!'
        })
    except Exception as e:
        print(f"Error copying cycle: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# SHARED CYCLE VIEW (Public)
# ============================================

@app.route('/shared/cycle/<share_code>')
def view_shared_cycle(share_code):
    """Public page to view a shared cycle."""
    shared = db_social.get_shared_cycle_by_code(share_code)
    
    if not shared:
        return render_template('errors/404.html', message="Shared cycle not found"), 404
    
    cycle = shared.get('training_cycles')
    
    # Get workout templates for preview
    templates = []
    if cycle:
        templates = db_cycles.get_cycle_workout_templates(cycle['id'])
    
    # Check if current user is logged in
    current_user = None
    try:
        current_user = get_current_user()
    except:
        pass
    
    # Get author info
    author_profile = None
    try:
        author_profile = db.get_user_profile(shared['user_id'])
    except:
        pass
    
    return render_template('shared_cycle.html',
                         shared=shared,
                         cycle=cycle,
                         templates=templates,
                         author=author_profile,
                         current_user=current_user,
                         share_code=share_code)


# ============================================
# SHARE ACHIEVEMENT (PR, Workout, etc.)
# ============================================

@app.route('/api/share/achievement', methods=['POST'])
@login_required
def api_share_achievement():
    """Create a shareable achievement."""
    user = get_current_user()
    data = request.json
    
    if not data.get('type') or not data.get('data'):
        return jsonify({'error': 'Missing type or data'}), 400
    
    profile = db.get_user_profile(user['id'])
    display_name = data.get('display_name') or (profile.get('display_name') if profile else None) or 'Someone'
    
    try:
        result = db_social.create_shared_achievement(
            user_id=user['id'],
            achievement_type=data['type'],
            achievement_data=data['data'],
            display_name=display_name,
            expires_days=data.get('expires_days', 30)  # Default 30 day expiry
        )
        
        if result:
            share_url = f"{request.host_url}shared/{data['type']}/{result['share_code']}"
            return jsonify({
                'success': True,
                'share_code': result['share_code'],
                'share_url': share_url
            })
        else:
            return jsonify({'error': 'Failed to create share'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/shared/pr/<share_code>')
def view_shared_pr(share_code):
    """Public page to view a shared PR."""
    achievement = db_social.get_shared_achievement(share_code)
    
    if not achievement or achievement.get('achievement_type') != 'pr':
        return render_template('errors/404.html', message="Shared PR not found or expired"), 404
    
    return render_template('shared_pr.html',
                         achievement=achievement,
                         pr_data=achievement.get('achievement_data', {}))


@app.route('/shared/workout/<share_code>')
def view_shared_workout(share_code):
    """Public page to view a shared workout."""
    achievement = db_social.get_shared_achievement(share_code)
    
    if not achievement or achievement.get('achievement_type') != 'workout':
        return render_template('errors/404.html', message="Shared workout not found or expired"), 404
    
    return render_template('shared_workout.html',
                         achievement=achievement,
                         workout_data=achievement.get('achievement_data', {}))


# ============================================
# PUBLIC LIBRARY PAGE
# ============================================

@app.route('/library')
def cycle_library():
    """Public cycle library page."""
    current_user = None
    try:
        current_user = get_current_user()
    except:
        pass
    
    return render_template('library.html', current_user=current_user)


# ============================================
# PUBLIC PROFILE
# ============================================

@app.route('/api/profile/public', methods=['POST'])
@login_required
def api_update_public_profile():
    """Update public profile settings."""
    user = get_current_user()
    data = request.json
    
    # Validate slug if provided
    if data.get('profile_slug'):
        slug = data['profile_slug'].lower().strip()
        if not slug.isalnum() or len(slug) < 3 or len(slug) > 30:
            return jsonify({'error': 'Slug must be 3-30 alphanumeric characters'}), 400
        
        if not db_social.check_profile_slug_available(slug, user['id']):
            return jsonify({'error': 'This profile URL is already taken'}), 400
        
        data['profile_slug'] = slug
    
    try:
        result = db_social.update_public_profile(user['id'], data)
        return jsonify({'success': True, 'profile': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/u/<profile_slug>')
def view_public_profile(profile_slug):
    """View a user's public profile."""
    profile = db_social.get_public_profile(profile_slug)
    
    if not profile:
        return render_template('errors/404.html', message="Profile not found"), 404
    
    # Get their public shared cycles
    shared_cycles = []
    try:
        all_shared = db_social.get_user_shared_cycles(profile['user_id'])
        shared_cycles = [c for c in all_shared if c.get('is_public')]
    except:
        pass
    
    # Get their PRs if enabled
    prs = []
    if profile.get('show_prs_publicly'):
        try:
            prs = db_progress.get_personal_records(profile['user_id'])[:10]  # Top 10
        except:
            pass
    
    return render_template('public_profile.html',
                         profile=profile,
                         shared_cycles=shared_cycles,
                         prs=prs)


# ============================================
# EXERCISE NOTES API
# ============================================

@app.route('/api/exercises/<exercise_id>/note', methods=['GET'])
@login_required
def api_get_exercise_note(exercise_id):
    """Get the current user's note for an exercise."""
    user = get_current_user()
    
    note = db_exercise_notes.get_user_exercise_note(user['id'], exercise_id)
    
    if note:
        return jsonify({
            'has_note': True,
            'note_text': note['note_text'],
            'updated_at': note['updated_at']
        })
    else:
        return jsonify({
            'has_note': False,
            'note_text': '',
            'updated_at': None
        })


@app.route('/api/exercises/<exercise_id>/note', methods=['POST', 'PUT'])
@login_required
def api_save_exercise_note(exercise_id):
    """Create or update a note for an exercise."""
    user = get_current_user()
    data = request.json
    
    note_text = data.get('note_text', '').strip()
    
    # Validate length
    if len(note_text) > 500:
        return jsonify({'error': 'Note must be 500 characters or less'}), 400
    
    # Empty note = delete
    if not note_text:
        db_exercise_notes.delete_user_exercise_note(user['id'], exercise_id)
        return jsonify({'success': True, 'deleted': True})
    
    result = db_exercise_notes.upsert_user_exercise_note(
        user_id=user['id'],
        exercise_id=exercise_id,
        note_text=note_text
    )
    
    if result:
        return jsonify({
            'success': True,
            'note': result
        })
    else:
        return jsonify({'error': 'Failed to save note'}), 500


@app.route('/api/exercises/<exercise_id>/note', methods=['DELETE'])
@login_required
def api_delete_exercise_note(exercise_id):
    """Delete a note for an exercise."""
    user = get_current_user()
    
    success = db_exercise_notes.delete_user_exercise_note(user['id'], exercise_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete note'}), 500


@app.route('/api/exercises/notes/bulk', methods=['POST'])
@login_required
def api_get_exercise_notes_bulk():
    """
    Get notes for multiple exercises at once.
    Used when loading a workout to get all notes in one request.
    
    Request body: { "exercise_ids": ["uuid1", "uuid2", ...] }
    Response: { "notes": { "uuid1": "note text", "uuid2": "note text" } }
    """
    user = get_current_user()
    data = request.json
    
    exercise_ids = data.get('exercise_ids', [])
    
    if not exercise_ids:
        return jsonify({'notes': {}})
    
    notes = db_exercise_notes.get_user_exercise_notes_bulk(user['id'], exercise_ids)
    
    return jsonify({'notes': notes})


@app.route('/api/exercises/notes/all', methods=['GET'])
@login_required
def api_get_all_exercise_notes():
    """
    Get all exercise notes for the current user.
    Useful for a notes management page or export.
    """
    user = get_current_user()
    
    notes = db_exercise_notes.get_all_user_notes(user['id'])
    
    return jsonify({'notes': notes})


# ============================================
# PWA ROUTES
# ============================================

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')


@app.route('/sw.js')
def service_worker():
    return app.send_static_file('js/sw.js'), 200, {'Content-Type': 'application/javascript'}


# ============================================
# CONTEXT PROCESSORS
# ============================================

@app.context_processor
def inject_user():
    """Make user available in all templates."""
    return {'current_user': get_current_user()}


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)