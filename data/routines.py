# Hardcoded PPL×2 routine compressed into 3 days
# Each day combines two muscle group focuses to hit everything 2x/week

EXERCISES = {
    # Push exercises
    "bench_press": {
        "id": "bench_press",
        "name": "Barbell Bench Press",
        "muscle_group": "chest",
        "equipment": "barbell",
        "cues": ["Retract shoulder blades", "Feet flat on floor", "Bar path: nipple line to lockout", "Control the descent"],
        "is_compound": True
    },
    "ohp": {
        "id": "ohp",
        "name": "Overhead Press",
        "muscle_group": "shoulders",
        "equipment": "barbell",
        "cues": ["Brace core tight", "Bar starts at collarbone", "Press straight up, head through at top", "Squeeze glutes"],
        "is_compound": True
    },
    "incline_db_press": {
        "id": "incline_db_press",
        "name": "Incline Dumbbell Press",
        "muscle_group": "chest",
        "equipment": "dumbbell",
        "cues": ["30-45 degree incline", "Dumbbells at shoulder level", "Press up and slightly in", "Feel the stretch at bottom"],
        "is_compound": True
    },
    "lateral_raise": {
        "id": "lateral_raise",
        "name": "Lateral Raise",
        "muscle_group": "shoulders",
        "equipment": "dumbbell",
        "cues": ["Slight bend in elbows", "Lead with elbows, not hands", "Raise to shoulder height", "Control the negative"],
        "is_compound": False
    },
    "tricep_pushdown": {
        "id": "tricep_pushdown",
        "name": "Tricep Pushdown",
        "muscle_group": "triceps",
        "equipment": "cable",
        "cues": ["Elbows pinned to sides", "Full extension at bottom", "Squeeze triceps hard", "Slow negative"],
        "is_compound": False
    },
    "cable_fly": {
        "id": "cable_fly",
        "name": "Cable Fly",
        "muscle_group": "chest",
        "equipment": "cable",
        "cues": ["Slight bend in elbows throughout", "Bring hands together at chest height", "Squeeze at peak contraction", "Feel the stretch on return"],
        "is_compound": False
    },
    
    # Pull exercises
    "barbell_row": {
        "id": "barbell_row",
        "name": "Barbell Row",
        "muscle_group": "back",
        "equipment": "barbell",
        "cues": ["Hinge at hips, flat back", "Pull to lower chest/upper abs", "Squeeze shoulder blades together", "Control the descent"],
        "is_compound": True
    },
    "pull_up": {
        "id": "pull_up",
        "name": "Pull-Up",
        "muscle_group": "back",
        "equipment": "bodyweight",
        "cues": ["Start from dead hang", "Pull elbows down and back", "Chin over bar", "Full extension at bottom"],
        "is_compound": True
    },
    "lat_pulldown": {
        "id": "lat_pulldown",
        "name": "Lat Pulldown",
        "muscle_group": "back",
        "equipment": "cable",
        "cues": ["Slight lean back", "Pull to upper chest", "Squeeze lats at bottom", "Control the return"],
        "is_compound": True
    },
    "face_pull": {
        "id": "face_pull",
        "name": "Face Pull",
        "muscle_group": "rear_delts",
        "equipment": "cable",
        "cues": ["High pulley position", "Pull to face, elbows high", "External rotate at end", "Squeeze rear delts"],
        "is_compound": False
    },
    "barbell_curl": {
        "id": "barbell_curl",
        "name": "Barbell Curl",
        "muscle_group": "biceps",
        "equipment": "barbell",
        "cues": ["Elbows pinned to sides", "Full range of motion", "Squeeze at top", "Control the negative"],
        "is_compound": False
    },
    "hammer_curl": {
        "id": "hammer_curl",
        "name": "Hammer Curl",
        "muscle_group": "biceps",
        "equipment": "dumbbell",
        "cues": ["Neutral grip throughout", "Elbows stationary", "Squeeze brachialis at top", "Alternate or together"],
        "is_compound": False
    },
    "cable_row": {
        "id": "cable_row",
        "name": "Seated Cable Row",
        "muscle_group": "back",
        "equipment": "cable",
        "cues": ["Sit tall, chest up", "Pull to lower chest", "Squeeze shoulder blades", "Full stretch forward"],
        "is_compound": True
    },
    
    # Legs exercises
    "squat": {
        "id": "squat",
        "name": "Barbell Back Squat",
        "muscle_group": "quads",
        "equipment": "barbell",
        "cues": ["Bar on upper traps", "Brace core, big breath", "Break at hips and knees together", "Knees track over toes"],
        "is_compound": True
    },
    "rdl": {
        "id": "rdl",
        "name": "Romanian Deadlift",
        "muscle_group": "hamstrings",
        "equipment": "barbell",
        "cues": ["Slight knee bend, fixed", "Hinge at hips, push butt back", "Feel hamstring stretch", "Squeeze glutes at top"],
        "is_compound": True
    },
    "leg_press": {
        "id": "leg_press",
        "name": "Leg Press",
        "muscle_group": "quads",
        "equipment": "machine",
        "cues": ["Feet shoulder width on platform", "Lower until 90 degrees", "Press through heels", "Don't lock knees at top"],
        "is_compound": True
    },
    "leg_curl": {
        "id": "leg_curl",
        "name": "Lying Leg Curl",
        "muscle_group": "hamstrings",
        "equipment": "machine",
        "cues": ["Hips flat on pad", "Curl heels to glutes", "Squeeze at top", "Slow negative"],
        "is_compound": False
    },
    "leg_extension": {
        "id": "leg_extension",
        "name": "Leg Extension",
        "muscle_group": "quads",
        "equipment": "machine",
        "cues": ["Back flat against pad", "Extend to full lockout", "Squeeze quads hard", "Control the descent"],
        "is_compound": False
    },
    "calf_raise": {
        "id": "calf_raise",
        "name": "Standing Calf Raise",
        "muscle_group": "calves",
        "equipment": "machine",
        "cues": ["Full stretch at bottom", "Rise onto balls of feet", "Pause at top", "Slow negative"],
        "is_compound": False
    },
    "hip_thrust": {
        "id": "hip_thrust",
        "name": "Barbell Hip Thrust",
        "muscle_group": "glutes",
        "equipment": "barbell",
        "cues": ["Upper back on bench", "Bar on hip crease", "Drive through heels", "Squeeze glutes at top, pause"],
        "is_compound": True
    },
    "walking_lunge": {
        "id": "walking_lunge",
        "name": "Walking Lunge",
        "muscle_group": "quads",
        "equipment": "dumbbell",
        "cues": ["Upright torso", "90 degree angles both knees", "Push through front heel", "Keep core braced"],
        "is_compound": True
    },
}

# PPL×2 compressed into 3 days
ROUTINES = {
    "ppl_3day": {
        "name": "PPL×2 (3 Day)",
        "description": "Push/Pull/Legs hit twice per week in 3 training days",
        "days": [
            {
                "day_number": 1,
                "name": "Push + Pull",
                "focus": ["chest", "shoulders", "triceps", "back", "biceps"],
                "exercises": [
                    {"exercise_id": "bench_press", "sets": 4, "rep_range": "6-8", "rest_seconds": 180},
                    {"exercise_id": "barbell_row", "sets": 4, "rep_range": "6-8", "rest_seconds": 180},
                    {"exercise_id": "ohp", "sets": 3, "rep_range": "8-10", "rest_seconds": 120},
                    {"exercise_id": "lat_pulldown", "sets": 3, "rep_range": "8-12", "rest_seconds": 90},
                    {"exercise_id": "cable_fly", "sets": 3, "rep_range": "12-15", "rest_seconds": 60},
                    {"exercise_id": "face_pull", "sets": 3, "rep_range": "15-20", "rest_seconds": 60},
                    {"exercise_id": "tricep_pushdown", "sets": 3, "rep_range": "10-12", "rest_seconds": 60},
                    {"exercise_id": "barbell_curl", "sets": 3, "rep_range": "10-12", "rest_seconds": 60},
                ]
            },
            {
                "day_number": 2,
                "name": "Legs + Push",
                "focus": ["quads", "hamstrings", "glutes", "calves", "chest", "shoulders"],
                "exercises": [
                    {"exercise_id": "squat", "sets": 4, "rep_range": "6-8", "rest_seconds": 180},
                    {"exercise_id": "rdl", "sets": 3, "rep_range": "8-10", "rest_seconds": 120},
                    {"exercise_id": "incline_db_press", "sets": 3, "rep_range": "8-10", "rest_seconds": 120},
                    {"exercise_id": "leg_press", "sets": 3, "rep_range": "10-12", "rest_seconds": 90},
                    {"exercise_id": "lateral_raise", "sets": 3, "rep_range": "12-15", "rest_seconds": 60},
                    {"exercise_id": "leg_curl", "sets": 3, "rep_range": "10-12", "rest_seconds": 60},
                    {"exercise_id": "calf_raise", "sets": 4, "rep_range": "12-15", "rest_seconds": 60},
                ]
            },
            {
                "day_number": 3,
                "name": "Pull + Legs",
                "focus": ["back", "biceps", "rear_delts", "hamstrings", "glutes"],
                "exercises": [
                    {"exercise_id": "pull_up", "sets": 4, "rep_range": "6-10", "rest_seconds": 180},
                    {"exercise_id": "hip_thrust", "sets": 4, "rep_range": "8-10", "rest_seconds": 120},
                    {"exercise_id": "cable_row", "sets": 3, "rep_range": "8-12", "rest_seconds": 90},
                    {"exercise_id": "walking_lunge", "sets": 3, "rep_range": "10-12 each", "rest_seconds": 90},
                    {"exercise_id": "face_pull", "sets": 3, "rep_range": "15-20", "rest_seconds": 60},
                    {"exercise_id": "leg_extension", "sets": 3, "rep_range": "12-15", "rest_seconds": 60},
                    {"exercise_id": "hammer_curl", "sets": 3, "rep_range": "10-12", "rest_seconds": 60},
                ]
            },
        ]
    }
}


def get_routine(routine_id):
    """Get a routine with full exercise details populated."""
    routine = ROUTINES.get(routine_id)
    if not routine:
        return None
    
    # Deep copy and populate exercise details
    result = {
        "name": routine["name"],
        "description": routine["description"],
        "days": []
    }
    
    for day in routine["days"]:
        day_data = {
            "day_number": day["day_number"],
            "name": day["name"],
            "focus": day["focus"],
            "exercises": []
        }
        
        for ex in day["exercises"]:
            exercise = EXERCISES.get(ex["exercise_id"])
            if exercise:
                day_data["exercises"].append({
                    **exercise,
                    "sets": ex["sets"],
                    "rep_range": ex["rep_range"],
                    "rest_seconds": ex["rest_seconds"]
                })
        
        result["days"].append(day_data)
    
    return result
