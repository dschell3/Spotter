"""
Dummy Data Generator for Progress Dashboard Testing

This script creates a test user and generates 6-8 weeks of realistic
workout data with progressive overload patterns.

Run this script locally with your Supabase credentials to populate test data.
"""

import os
import random
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Configuration
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "testpassword123"
WEEKS_OF_DATA = 7  # 7 weeks of data
WORKOUTS_PER_WEEK = 3  # PPL x2 compressed to 3 days

# Realistic starting weights and progression for common exercises
EXERCISE_BASELINES = {
    # Compounds - heavier, slower progression
    'Barbell Bench Press': {'start': 135, 'increment': 5, 'variance': 5, 'rep_range': (5, 8)},
    'Barbell Back Squat': {'start': 185, 'increment': 5, 'variance': 10, 'rep_range': (5, 8)},
    'Barbell Row': {'start': 135, 'increment': 5, 'variance': 5, 'rep_range': (6, 10)},
    'Overhead Press': {'start': 95, 'increment': 2.5, 'variance': 5, 'rep_range': (6, 10)},
    'Romanian Deadlift': {'start': 155, 'increment': 5, 'variance': 10, 'rep_range': (8, 10)},
    'Pull-Up': {'start': 0, 'increment': 0, 'variance': 0, 'rep_range': (5, 10)},  # Bodyweight
    'Barbell Hip Thrust': {'start': 135, 'increment': 10, 'variance': 10, 'rep_range': (8, 12)},
    'Leg Press': {'start': 270, 'increment': 10, 'variance': 20, 'rep_range': (8, 12)},
    'Incline Dumbbell Press': {'start': 50, 'increment': 5, 'variance': 5, 'rep_range': (8, 12)},
    'Seated Cable Row': {'start': 120, 'increment': 5, 'variance': 10, 'rep_range': (8, 12)},
    'Walking Lunge': {'start': 40, 'increment': 5, 'variance': 5, 'rep_range': (10, 12)},
    
    # Isolations - lighter, can progress faster on reps
    'Lat Pulldown': {'start': 100, 'increment': 5, 'variance': 5, 'rep_range': (8, 12)},
    'Cable Fly': {'start': 25, 'increment': 2.5, 'variance': 2.5, 'rep_range': (10, 15)},
    'Face Pull': {'start': 40, 'increment': 2.5, 'variance': 5, 'rep_range': (12, 20)},
    'Tricep Pushdown': {'start': 50, 'increment': 2.5, 'variance': 5, 'rep_range': (10, 15)},
    'Barbell Curl': {'start': 50, 'increment': 2.5, 'variance': 5, 'rep_range': (8, 12)},
    'Hammer Curl': {'start': 25, 'increment': 2.5, 'variance': 2.5, 'rep_range': (10, 12)},
    'Lateral Raise': {'start': 15, 'increment': 2.5, 'variance': 2.5, 'rep_range': (10, 15)},
    'Lying Leg Curl': {'start': 70, 'increment': 5, 'variance': 5, 'rep_range': (10, 15)},
    'Leg Extension': {'start': 90, 'increment': 5, 'variance': 10, 'rep_range': (10, 15)},
    'Standing Calf Raise': {'start': 135, 'increment': 10, 'variance': 10, 'rep_range': (12, 20)},
}

# PPL x2 compressed - 3 day split
WORKOUT_TEMPLATES = [
    {
        'name': 'Push + Pull',
        'exercises': [
            ('Barbell Bench Press', 4),
            ('Barbell Row', 4),
            ('Overhead Press', 3),
            ('Lat Pulldown', 3),
            ('Cable Fly', 3),
            ('Face Pull', 3),
            ('Tricep Pushdown', 3),
            ('Barbell Curl', 3),
        ]
    },
    {
        'name': 'Legs + Push',
        'exercises': [
            ('Barbell Back Squat', 4),
            ('Romanian Deadlift', 3),
            ('Incline Dumbbell Press', 3),
            ('Leg Press', 3),
            ('Lateral Raise', 3),
            ('Lying Leg Curl', 3),
            ('Standing Calf Raise', 4),
        ]
    },
    {
        'name': 'Pull + Legs',
        'exercises': [
            ('Pull-Up', 4),
            ('Barbell Hip Thrust', 4),
            ('Seated Cable Row', 3),
            ('Walking Lunge', 3),
            ('Face Pull', 3),
            ('Leg Extension', 3),
            ('Hammer Curl', 3),
        ]
    }
]


def get_supabase_client():
    """Create Supabase client from environment variables."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    
    return create_client(url, key)


def create_test_user(supabase):
    """Create the test user account."""
    try:
        # Try to sign up
        response = supabase.auth.sign_up({
            'email': TEST_USER_EMAIL,
            'password': TEST_USER_PASSWORD
        })
        
        if response.user:
            print(f"✓ Created test user: {TEST_USER_EMAIL}")
            return response.user.id
        else:
            raise Exception("No user returned from signup")
            
    except Exception as e:
        if 'already registered' in str(e).lower():
            # User exists, try to sign in to get their ID
            print(f"Test user already exists, signing in...")
            response = supabase.auth.sign_in_with_password({
                'email': TEST_USER_EMAIL,
                'password': TEST_USER_PASSWORD
            })
            if response.user:
                print(f"✓ Signed in as test user: {TEST_USER_EMAIL}")
                return response.user.id
        raise e


def ensure_profile_exists(supabase, user_id):
    """Make sure the user has a profile."""
    # Check if profile exists
    response = supabase.table('profiles').select('id').eq('id', user_id).execute()
    
    if not response.data:
        # Create profile
        supabase.table('profiles').insert({
            'id': user_id,
            'email': TEST_USER_EMAIL,
            'display_name': 'Test User',
            'days_per_week': 3,
            'split_type': 'ppl',
            'pr_rep_threshold': 5
        }).execute()
        print("✓ Created user profile")
    else:
        print("✓ Profile already exists")


def get_exercise_id(supabase, exercise_name):
    """Get exercise ID from name, with caching."""
    if not hasattr(get_exercise_id, 'cache'):
        get_exercise_id.cache = {}
    
    if exercise_name in get_exercise_id.cache:
        return get_exercise_id.cache[exercise_name]
    
    response = supabase.table('exercises').select('id').eq('name', exercise_name).execute()
    
    if response.data:
        exercise_id = response.data[0]['id']
        get_exercise_id.cache[exercise_name] = exercise_id
        return exercise_id
    
    return None


def calculate_weight_for_week(exercise_name, week_num):
    """Calculate weight for an exercise in a given week with progression."""
    baseline = EXERCISE_BASELINES.get(exercise_name)
    if not baseline:
        # Default for unknown exercises
        return random.randint(20, 100)
    
    # Base weight with weekly progression
    base = baseline['start']
    increment = baseline['increment']
    variance = baseline['variance']
    
    # Progressive overload - increase every 2 weeks roughly
    progression_weeks = week_num // 2
    progressed_weight = base + (progression_weeks * increment)
    
    # Add some variance (+/-)
    final_weight = progressed_weight + random.uniform(-variance/2, variance/2)
    
    # Round to nearest 2.5 for dumbbells, 5 for barbells
    if 'Dumbbell' in exercise_name or 'Curl' in exercise_name or 'Lateral' in exercise_name:
        return round(final_weight / 2.5) * 2.5
    else:
        return round(final_weight / 5) * 5


def calculate_reps_for_set(exercise_name, set_num, total_sets):
    """Calculate reps for a set - typically decreasing as fatigue builds."""
    baseline = EXERCISE_BASELINES.get(exercise_name)
    if not baseline:
        return random.randint(8, 12)
    
    rep_low, rep_high = baseline['rep_range']
    
    # First sets get more reps, later sets fewer (fatigue)
    fatigue_factor = set_num / total_sets  # 0 to 1
    base_reps = rep_high - int((rep_high - rep_low) * fatigue_factor)
    
    # Add some variance
    return max(rep_low, base_reps + random.randint(-1, 1))


def generate_dummy_workouts(supabase, user_id):
    """Generate weeks of workout data."""
    print(f"\nGenerating {WEEKS_OF_DATA} weeks of workout data...")
    
    # Start date - go back WEEKS_OF_DATA weeks from today
    today = date.today()
    start_date = today - timedelta(weeks=WEEKS_OF_DATA)
    
    # Find the Monday of that week
    start_monday = start_date - timedelta(days=start_date.weekday())
    
    workouts_created = 0
    sets_created = 0
    
    for week in range(WEEKS_OF_DATA):
        week_start = start_monday + timedelta(weeks=week)
        
        # Generate 3 workouts this week (Mon, Wed, Fri typically)
        workout_days = [0, 2, 4]  # Monday, Wednesday, Friday
        
        for day_idx, day_offset in enumerate(workout_days):
            workout_date = week_start + timedelta(days=day_offset)
            
            # Skip future dates
            if workout_date > today:
                continue
            
            # Occasionally skip a workout (90% completion rate)
            if random.random() > 0.90:
                continue
            
            template = WORKOUT_TEMPLATES[day_idx]
            workout_time = datetime.combine(workout_date, datetime.min.time().replace(hour=random.randint(6, 19)))
            
            # Create workout
            workout_response = supabase.table('user_workouts').insert({
                'user_id': user_id,
                'template_name': template['name'],
                'started_at': workout_time.isoformat(),
                'completed_at': (workout_time + timedelta(minutes=random.randint(45, 90))).isoformat()
            }).execute()
            
            if not workout_response.data:
                print(f"  ✗ Failed to create workout for {workout_date}")
                continue
            
            workout_id = workout_response.data[0]['id']
            workouts_created += 1
            
            # Generate sets for each exercise
            for exercise_name, num_sets in template['exercises']:
                exercise_id = get_exercise_id(supabase, exercise_name)
                
                weight = calculate_weight_for_week(exercise_name, week)
                
                for set_num in range(1, num_sets + 1):
                    reps = calculate_reps_for_set(exercise_name, set_num, num_sets)
                    
                    # Slight weight variation between sets
                    set_weight = weight
                    if set_num > 2 and random.random() > 0.7:
                        set_weight = weight - 5  # Drop set
                    
                    supabase.table('workout_sets').insert({
                        'user_workout_id': workout_id,
                        'exercise_id': exercise_id,
                        'exercise_name': exercise_name,
                        'set_number': set_num,
                        'weight': max(0, set_weight),  # No negative weights
                        'reps': reps,
                        'completed': True
                    }).execute()
                    
                    sets_created += 1
        
        print(f"  Week {week + 1}: Generated workouts")
    
    print(f"\n✓ Created {workouts_created} workouts with {sets_created} sets")
    return workouts_created, sets_created


def clear_test_user_data(supabase, user_id):
    """Clear existing workout data for the test user."""
    print("\nClearing existing test data...")
    
    # Get all workouts for user
    workouts = supabase.table('user_workouts').select('id').eq('user_id', user_id).execute()
    
    if workouts.data:
        workout_ids = [w['id'] for w in workouts.data]
        
        # Delete sets
        for wid in workout_ids:
            supabase.table('workout_sets').delete().eq('user_workout_id', wid).execute()
        
        # Delete workouts
        supabase.table('user_workouts').delete().eq('user_id', user_id).execute()
        
        print(f"  ✓ Cleared {len(workout_ids)} existing workouts")
    
    # Clear PRs
    supabase.table('personal_records').delete().eq('user_id', user_id).execute()
    supabase.table('pr_history').delete().eq('user_id', user_id).execute()
    print("  ✓ Cleared PR data")


def main():
    """Main function to generate all dummy data."""
    print("=" * 50)
    print("Dummy Data Generator for Progress Dashboard")
    print("=" * 50)
    
    supabase = get_supabase_client()
    
    # Create or get test user
    user_id = create_test_user(supabase)
    print(f"User ID: {user_id}")
    
    # Ensure profile exists
    ensure_profile_exists(supabase, user_id)
    
    # Clear existing data
    clear_test_user_data(supabase, user_id)
    
    # Generate new dummy data
    workouts, sets = generate_dummy_workouts(supabase, user_id)
    
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Test User: {TEST_USER_EMAIL}")
    print(f"  Password: {TEST_USER_PASSWORD}")
    print(f"  Workouts: {workouts}")
    print(f"  Sets: {sets}")
    print("=" * 50)
    print("\nYou can now log in as the test user to see the progress dashboard!")


if __name__ == '__main__':
    main()
