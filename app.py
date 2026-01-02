from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from functools import wraps
from config import Config
import db

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
    """Landing page - shows workout selection."""
    user = get_current_user()
    
    try:
        routine = db.get_routine('ppl_3day')
    except Exception as e:
        # Fallback to hardcoded routine if DB fails
        print(f"Database error: {e}")
        from data.routines import get_routine as get_local_routine
        routine = get_local_routine('ppl_3day')
    
    return render_template('index.html', routine=routine, user=user)


@app.route('/workout/<day_id>')
def workout(day_id):
    """Workout execution view for a specific day."""
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
    
    return render_template('profile.html', profile=profile_data, user=user)


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
        return jsonify(EXERCISES)


@app.route('/api/exercises/<muscle_group>')
def api_exercises_by_muscle(muscle_group):
    """API endpoint to get exercises by muscle group."""
    try:
        exercises = db.get_exercises_by_muscle_group(muscle_group)
        return jsonify(exercises)
    except Exception as e:
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
