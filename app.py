from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response
from functools import wraps
from config import Config
from datetime import date, datetime, timedelta
import db
import db_cycles
import workout_generator

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
    
    return render_template('auth/login.html')


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
        
        # Calculate week_start for the requested week
        week_start = cycle_start + timedelta(weeks=current_week - 1)
        
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
    scheduled_remaining = sum(1 for w in scheduled_workouts if w.get('status') == 'scheduled')
    
    week_stats = {
        'total': total_scheduled,
        'completed': completed,
        'scheduled': scheduled_remaining,
        'completion_rate': round((completed / total_scheduled * 100) if total_scheduled > 0 else 0)
    }
    
    # Find next workout (first scheduled workout from today forward)
    next_workout = None
    for workout in sorted(scheduled_workouts, key=lambda w: w['scheduled_date']):
        workout_date = datetime.strptime(workout['scheduled_date'], '%Y-%m-%d').date()
        if workout.get('status') == 'scheduled' and workout_date >= today:
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
        
        # Get exercises for this slot
        exercises_response = supabase.table('cycle_exercises')\
            .select('*, exercises(*)')\
            .eq('cycle_workout_slot_id', slot_id)\
            .order('order_index')\
            .execute()
        
        cycle_exercises = exercises_response.data or []
        
        # Build the day data structure that workout.html expects
        day = {
            'id': slot_id,
            'name': slot.get('workout_name', 'Workout'),
            'day_number': scheduled_workout.get('week_number', 1),
            'focus': slot.get('is_heavy_focus', []),
            'exercises': []
        }
        
        # Determine if this is a heavy or light day for each exercise
        heavy_focuses = slot.get('is_heavy_focus', [])
        
        for ce in cycle_exercises:
            exercise_data = ce.get('exercises', {})
            
            # Determine if this exercise should use heavy or light settings
            # An exercise is heavy if its muscle group's focus is in the heavy_focuses list
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
        cycle = db_cycles.get_cycle_by_id(cycle_id)
        total_days = cycle.get('length_weeks', 6) * 3  # Approximate
        
        return render_template('workout_cycle.html',
                             day=day,
                             scheduled_workout=scheduled_workout,
                             cycle=cycle,
                             day_number=scheduled_workout.get('week_number', 1),
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
    # Note: Pass None for template_id since cycle workouts use cycle_workout_slots, not templates
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
    exclude_ids = [x for x in request.args.get('exclude', '').split(',') if x]  # List of video IDs to exclude
    
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
                'videoDuration': 'short',  # Under 4 minutes
                'maxResults': 10,  # Get more results to allow for exclusions
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
            
            # Filter out excluded videos from details too
            videos = [v for v in details_data.get('items', []) if v['id'] not in exclude_ids]
            
            # Find the first video under 30 seconds
            for video in videos:
                duration = video['contentDetails']['duration']
                # Parse ISO 8601 duration (e.g., PT1M30S, PT45S, PT2M)
                seconds = parse_youtube_duration(duration)
                
                if seconds <= 30:  # Under 30 seconds
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
    
    # Handle PT format
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
    """Clear video URL from an exercise (to search again)."""
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
        
        # Get all cycles for this user
        all_cycles = supabase.table('cycles').select('*').eq('user_id', user['id']).execute()
        
        # Get active cycle specifically
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
    
    # Validate inputs
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
    
    # Default to Mon, Wed, Fri
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
    
    try:
        result = db_cycles.update_profile_training_settings(
            user_id=user['id'],
            email=user.get('email'),  # Pass email for profile creation
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
    """Create a new training cycle."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    try:
        # Parse start date
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        # Create cycle
        cycle = db_cycles.create_cycle(
            user_id=user['id'],
            name=data.get('name', f"Cycle starting {start_date}"),
            start_date=start_date,
            length_weeks=data.get('length_weeks', 6),
            split_type=data.get('split_type', 'ppl_3day')
        )
        
        if not cycle:
            return jsonify({'error': 'Failed to create cycle'}), 500
        
        # Handle both old format (schedule + exercises) and new format (workout_slots with nested exercises)
        workout_slots = data.get('workout_slots', [])
        
        # Create workout slots
        created_slots = []
        for i, slot_data in enumerate(workout_slots):
            slot = db_cycles.create_cycle_workout_slot(
                cycle_id=cycle['id'],
                day_of_week=slot_data.get('day_of_week', slot_data.get('dayOfWeek', i)),
                template_id=slot_data.get('template_id'),
                workout_name=slot_data.get('workout_name', slot_data.get('workoutName', f'Workout {i+1}')),
                is_heavy_focus=slot_data.get('is_heavy_focus', slot_data.get('heavyFocus', [])),
                order_index=slot_data.get('order_index', i)
            )
            if slot:
                created_slots.append(slot)
                
                # Create exercises for this slot (nested in workout_slots)
                slot_exercises = slot_data.get('exercises', [])
                for j, ex_data in enumerate(slot_exercises):
                    db_cycles.create_cycle_exercise(
                        cycle_id=cycle['id'],
                        slot_id=slot['id'],
                        exercise_id=ex_data.get('exercise_id', ex_data.get('id')),
                        exercise_name=ex_data.get('exercise_name', ex_data.get('name')),
                        muscle_group=ex_data.get('muscle_group', ''),
                        is_heavy=ex_data.get('is_heavy', False),
                        order_index=j,
                        sets_heavy=ex_data.get('sets_heavy', 4),
                        sets_light=ex_data.get('sets_light', 3),
                        rep_range_heavy=ex_data.get('rep_range_heavy', '6-8'),
                        rep_range_light=ex_data.get('rep_range_light', '10-12'),
                        rest_heavy=ex_data.get('rest_heavy', 180),
                        rest_light=ex_data.get('rest_light', 90)
                    )
        
        # Generate the schedule for all weeks
        if created_slots:
            db_cycles.generate_cycle_schedule(
                user_id=user['id'],
                cycle_id=cycle['id'],
                start_date=start_date,
                length_weeks=data.get('length_weeks', 6),
                workout_slots=created_slots
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
        db_cycles.generate_cycle_schedule(
            user_id=user['id'],
            cycle_id=cycle_id,
            start_date=start_date,
            length_weeks=cycle['length_weeks'],
            workout_slots=slots
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
        # 1. Delete scheduled workouts
        supabase.table('scheduled_workouts').delete().eq('cycle_id', cycle_id).execute()
        
        # 2. Delete cycle exercises
        supabase.table('cycle_exercises').delete().eq('cycle_id', cycle_id).execute()
        
        # 3. Delete cycle workout slots
        supabase.table('cycle_workout_slots').delete().eq('cycle_id', cycle_id).execute()
        
        # 4. Delete the cycle itself
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
        result = db_cycles.reschedule_workout(scheduled_id, new_date)
        return jsonify({'success': True, 'workout': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/clean', methods=['POST'])
def api_debug_clean():
    """Clean all cycle data for the current user. USE WITH CAUTION."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        supabase = db.get_supabase_client()
        
        # Get all cycles for user
        cycles_resp = supabase.table('cycles').select('id').eq('user_id', user['id']).execute()
        cycle_ids = [c['id'] for c in (cycles_resp.data or [])]
        
        deleted = {'scheduled_workouts': 0, 'cycle_exercises': 0, 'cycle_workout_slots': 0, 'cycles': 0}
        
        if cycle_ids:
            # Delete scheduled workouts
            resp = supabase.table('scheduled_workouts').delete().eq('user_id', user['id']).execute()
            deleted['scheduled_workouts'] = len(resp.data) if resp.data else 0
            
            # Delete cycle exercises
            for cid in cycle_ids:
                resp = supabase.table('cycle_exercises').delete().eq('cycle_id', cid).execute()
                deleted['cycle_exercises'] += len(resp.data) if resp.data else 0
            
            # Delete cycle workout slots
            for cid in cycle_ids:
                resp = supabase.table('cycle_workout_slots').delete().eq('cycle_id', cid).execute()
                deleted['cycle_workout_slots'] += len(resp.data) if resp.data else 0
            
            # Delete cycles
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
        # Get active cycle
        cycle = db_cycles.get_active_cycle(user['id'])
        
        # Get all data for debugging
        supabase = db.get_supabase_client()
        
        # All cycles for user
        cycles_resp = supabase.table('cycles').select('*').eq('user_id', user['id']).execute()
        
        # All scheduled workouts for user
        scheduled_resp = supabase.table('scheduled_workouts').select('*').eq('user_id', user['id']).execute()
        
        # All workout slots for active cycle
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