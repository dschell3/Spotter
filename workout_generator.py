"""
Workout Generator Module

Generates workout structures based on split type and days per week.
Handles combining workouts and weekly rotations automatically.

Now includes week_pattern for rotating splits (odd/even weeks).
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class SplitType(Enum):
    FULL_BODY = "full_body"
    UPPER_LOWER = "upper_lower"
    PPL = "ppl"
    CUSTOM = "custom"


@dataclass
class WorkoutFocus:
    """Represents a single focus within a workout day."""
    name: str  # e.g., "Push", "Pull", "Legs", "Upper", "Lower", "Full Body"
    is_heavy: bool
    muscle_groups: List[str]


@dataclass
class WorkoutDay:
    """Represents a single workout day, potentially with multiple focuses."""
    day_number: int  # 1-indexed within the week
    name: str  # Display name like "Push + Pull"
    focuses: List[WorkoutFocus]
    week_pattern: Optional[str] = None  # 'odd', 'even', or None (all weeks)
    
    @property
    def display_name(self) -> str:
        if len(self.focuses) == 1:
            return self.focuses[0].name
        heavy = [f.name for f in self.focuses if f.is_heavy]
        light = [f.name for f in self.focuses if not f.is_heavy]
        if heavy and light:
            return f"{heavy[0]} (Heavy) + {light[0]} (Light)"
        return " + ".join(f.name for f in self.focuses)


@dataclass
class WeekStructure:
    """Represents one week's workout structure."""
    week_number: int
    days: List[WorkoutDay]


@dataclass
class GeneratedSchedule:
    """Complete generated schedule that may span multiple week patterns."""
    split_type: SplitType
    days_per_week: int
    rotation_weeks: int  # How many weeks before pattern repeats
    weeks: List[WeekStructure]
    summary: str  # Human-readable summary
    # New: flat list of all unique workout slots with week_pattern
    workout_slots: List[Dict] = field(default_factory=list)


# Muscle group definitions for each focus type
FOCUS_MUSCLE_GROUPS = {
    "Push": ["chest", "shoulders", "triceps"],
    "Pull": ["back", "biceps", "rear_delts"],
    "Legs": ["quads", "hamstrings", "glutes", "calves"],
    "Upper": ["chest", "back", "shoulders", "biceps", "triceps"],
    "Lower": ["quads", "hamstrings", "glutes", "calves"],
    "Full Body": ["chest", "back", "shoulders", "quads", "hamstrings", "glutes", "biceps", "triceps"],
}


def generate_schedule(split_type: str, days_per_week: int) -> GeneratedSchedule:
    """
    Main entry point: generates a workout schedule based on split and days.
    
    Args:
        split_type: One of 'full_body', 'upper_lower', 'ppl', 'custom'
        days_per_week: Number of training days (2-6)
    
    Returns:
        GeneratedSchedule with all weeks and workout structures
    """
    split = SplitType(split_type)
    
    if split == SplitType.FULL_BODY:
        return _generate_full_body(days_per_week)
    elif split == SplitType.UPPER_LOWER:
        return _generate_upper_lower(days_per_week)
    elif split == SplitType.PPL:
        return _generate_ppl(days_per_week)
    else:
        # Custom returns empty structure for user to fill
        return _generate_custom(days_per_week)


def _generate_full_body(days_per_week: int) -> GeneratedSchedule:
    """
    Full Body: Each session hits everything.
    Simple - just repeat full body workouts.
    """
    days = []
    workout_slots = []
    
    for i in range(days_per_week):
        focus = WorkoutFocus(
            name="Full Body",
            is_heavy=(i % 2 == 0),  # Alternate heavy/light
            muscle_groups=FOCUS_MUSCLE_GROUPS["Full Body"]
        )
        day = WorkoutDay(
            day_number=i + 1,
            name=f"Full Body {'A' if i % 2 == 0 else 'B'}",
            focuses=[focus],
            week_pattern=None  # Same every week
        )
        days.append(day)
        
        workout_slots.append({
            'day_number': i + 1,
            'name': day.name,
            'week_pattern': None,
            'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
        })
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.FULL_BODY,
        days_per_week=days_per_week,
        rotation_weeks=1,
        weeks=[week],
        summary=f"Full Body {days_per_week}x/week - alternate heavy/light sessions",
        workout_slots=workout_slots
    )


def _generate_upper_lower(days_per_week: int) -> GeneratedSchedule:
    """
    Upper/Lower: Alternate between upper and lower body.
    
    2 days: U, L (each 1x/week) - no rotation
    3 days: Rotate - W1: U,L,U → W2: L,U,L (uses week_pattern)
    4 days: U, L, U, L (each 2x/week) - no rotation
    5 days: Rotate - W1: U,L,U,L,U → W2: L,U,L,U,L (uses week_pattern)
    6 days: U, L, U, L, U, L (each 3x/week) - no rotation
    """
    
    if days_per_week % 2 == 0:
        # Even days - no rotation needed
        days = []
        workout_slots = []
        
        for i in range(days_per_week):
            is_upper = (i % 2 == 0)
            focus_name = "Upper" if is_upper else "Lower"
            # First occurrence of each is heavy, second is light
            occurrence = i // 2
            is_heavy = (occurrence % 2 == 0)
            
            focus = WorkoutFocus(
                name=focus_name,
                is_heavy=is_heavy,
                muscle_groups=FOCUS_MUSCLE_GROUPS[focus_name]
            )
            day = WorkoutDay(
                day_number=i + 1,
                name=f"{focus_name} {'(Heavy)' if is_heavy else '(Light)'}",
                focuses=[focus],
                week_pattern=None
            )
            days.append(day)
            
            workout_slots.append({
                'day_number': i + 1,
                'name': day.name,
                'week_pattern': None,
                'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
            })
        
        week = WeekStructure(week_number=1, days=days)
        freq = days_per_week // 2
        
        return GeneratedSchedule(
            split_type=SplitType.UPPER_LOWER,
            days_per_week=days_per_week,
            rotation_weeks=1,
            weeks=[week],
            summary=f"Upper/Lower - each {freq}x/week",
            workout_slots=workout_slots
        )
    else:
        # Odd days - need 2-week rotation with week_pattern
        weeks = []
        workout_slots = []
        patterns = ["Upper", "Lower"]
        
        for week_num in range(1, 3):
            days = []
            start_idx = 0 if week_num == 1 else 1  # Alternate starting point
            week_pattern = 'odd' if week_num == 1 else 'even'
            
            for i in range(days_per_week):
                focus_name = patterns[(start_idx + i) % 2]
                is_heavy = (i < days_per_week // 2 + 1)  # First half heavy
                
                focus = WorkoutFocus(
                    name=focus_name,
                    is_heavy=is_heavy,
                    muscle_groups=FOCUS_MUSCLE_GROUPS[focus_name]
                )
                day = WorkoutDay(
                    day_number=i + 1,
                    name=f"{focus_name} {'(Heavy)' if is_heavy else '(Light)'}",
                    focuses=[focus],
                    week_pattern=week_pattern
                )
                days.append(day)
                
                workout_slots.append({
                    'day_number': i + 1,
                    'name': day.name,
                    'week_pattern': week_pattern,
                    'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
                })
            
            weeks.append(WeekStructure(week_number=week_num, days=days))
        
        return GeneratedSchedule(
            split_type=SplitType.UPPER_LOWER,
            days_per_week=days_per_week,
            rotation_weeks=2,
            weeks=weeks,
            summary=f"Upper/Lower - 2-week rotation to balance frequency",
            workout_slots=workout_slots
        )


def _generate_ppl(days_per_week: int) -> GeneratedSchedule:
    """
    Push/Pull/Legs: Goal is to hit each 2x/week.
    
    6 days: P, P, L, P, P, L (classic PPL x2)
    5 days: Rotate weekly
    4 days: Rotate weekly  
    3 days: Combine - Push+Pull, Legs+Push, Pull+Legs (each focus 2x)
    2 days: Combine + rotate over 3 weeks
    """
    
    if days_per_week >= 6:
        return _generate_ppl_6day()
    elif days_per_week == 5:
        return _generate_ppl_5day()
    elif days_per_week == 4:
        return _generate_ppl_4day()
    elif days_per_week == 3:
        return _generate_ppl_3day()
    else:  # 2 days
        return _generate_ppl_2day()


def _generate_ppl_6day() -> GeneratedSchedule:
    """Classic PPL x2: Push, Pull, Legs, Push, Pull, Legs"""
    pattern = [
        ("Push", True), ("Pull", True), ("Legs", True),
        ("Push", False), ("Pull", False), ("Legs", False)
    ]
    
    days = []
    workout_slots = []
    
    for i, (name, is_heavy) in enumerate(pattern):
        focus = WorkoutFocus(
            name=name,
            is_heavy=is_heavy,
            muscle_groups=FOCUS_MUSCLE_GROUPS[name]
        )
        day = WorkoutDay(
            day_number=i + 1,
            name=f"{name} {'(Heavy)' if is_heavy else '(Light)'}",
            focuses=[focus],
            week_pattern=None
        )
        days.append(day)
        
        workout_slots.append({
            'day_number': i + 1,
            'name': day.name,
            'week_pattern': None,
            'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
        })
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=6,
        rotation_weeks=1,
        weeks=[week],
        summary="Classic PPL x2 - each muscle group 2x/week",
        workout_slots=workout_slots
    )


def _generate_ppl_5day() -> GeneratedSchedule:
    """PPL with 5 days: Rotate to balance over 3 weeks."""
    # Sequence: P,P,L,P,P → L,P,P,L,P → P,L,P,P,L
    sequences = [
        [("Push", True), ("Pull", True), ("Legs", True), ("Push", False), ("Pull", False)],
        [("Legs", False), ("Push", True), ("Pull", True), ("Legs", True), ("Push", False)],
        [("Pull", False), ("Legs", False), ("Push", True), ("Pull", True), ("Legs", True)],
    ]
    
    # Map week numbers to patterns: 1,4,7...=week1, 2,5,8...=week2, 3,6,9...=week3
    week_patterns = ['week_mod_1', 'week_mod_2', 'week_mod_0']  # week % 3 == pattern
    
    weeks = []
    workout_slots = []
    
    for week_num, sequence in enumerate(sequences, 1):
        days = []
        week_pattern = week_patterns[week_num - 1]
        
        for i, (name, is_heavy) in enumerate(sequence):
            focus = WorkoutFocus(
                name=name,
                is_heavy=is_heavy,
                muscle_groups=FOCUS_MUSCLE_GROUPS[name]
            )
            day = WorkoutDay(
                day_number=i + 1,
                name=f"{name} {'(Heavy)' if is_heavy else '(Light)'}",
                focuses=[focus],
                week_pattern=week_pattern
            )
            days.append(day)
            
            workout_slots.append({
                'day_number': i + 1,
                'name': day.name,
                'week_pattern': week_pattern,
                'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
            })
        
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=5,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 5-day - 3-week rotation for balanced frequency",
        workout_slots=workout_slots
    )


def _generate_ppl_4day() -> GeneratedSchedule:
    """PPL with 4 days: Upper/Lower hybrid or rotation."""
    # Combine into 4 focused days with some overlap
    # Day 1: Push (Heavy)
    # Day 2: Pull (Heavy)
    # Day 3: Legs (Heavy)
    # Day 4: Push + Pull (Light) - combined upper
    # Rotate starting point each week
    
    weeks = []
    workout_slots = []
    base_pattern = [
        [("Push", True)],
        [("Pull", True)],
        [("Legs", True)],
        [("Push", False), ("Pull", False)],  # Combined light upper
    ]
    
    # Map: week 1,4,7...=mod_1, week 2,5,8...=mod_2, week 3,6,9...=mod_0
    week_patterns = ['week_mod_1', 'week_mod_2', 'week_mod_0']
    
    for week_num in range(1, 4):
        days = []
        # Rotate the pattern
        offset = (week_num - 1) % 4
        rotated = base_pattern[offset:] + base_pattern[:offset]
        week_pattern = week_patterns[week_num - 1]
        
        for i, focuses_data in enumerate(rotated):
            focuses = []
            names = []
            for name, is_heavy in focuses_data:
                focuses.append(WorkoutFocus(
                    name=name,
                    is_heavy=is_heavy,
                    muscle_groups=FOCUS_MUSCLE_GROUPS[name]
                ))
                names.append(f"{name}{'(H)' if is_heavy else '(L)'}")
            
            day = WorkoutDay(
                day_number=i + 1,
                name=" + ".join(names),
                focuses=focuses,
                week_pattern=week_pattern
            )
            days.append(day)
            
            workout_slots.append({
                'day_number': i + 1,
                'name': day.name,
                'week_pattern': week_pattern,
                'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
            })
        
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=4,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 4-day - combines one upper day, rotates for balance",
        workout_slots=workout_slots
    )


def _generate_ppl_3day() -> GeneratedSchedule:
    """
    PPL compressed to 3 days: Each day combines two focuses.
    
    Day 1: Push (Heavy) + Pull (Light)
    Day 2: Legs (Heavy) + Push (Light)
    Day 3: Pull (Heavy) + Legs (Light)
    
    This hits each muscle group 2x/week (once heavy, once light).
    """
    combinations = [
        [("Push", True), ("Pull", False)],
        [("Legs", True), ("Push", False)],
        [("Pull", True), ("Legs", False)],
    ]
    
    days = []
    workout_slots = []
    
    for i, combo in enumerate(combinations):
        focuses = []
        for name, is_heavy in combo:
            focuses.append(WorkoutFocus(
                name=name,
                is_heavy=is_heavy,
                muscle_groups=FOCUS_MUSCLE_GROUPS[name]
            ))
        
        heavy_name = combo[0][0]
        light_name = combo[1][0]
        
        day = WorkoutDay(
            day_number=i + 1,
            name=f"{heavy_name} (Heavy) + {light_name} (Light)",
            focuses=focuses,
            week_pattern=None  # Same every week
        )
        days.append(day)
        
        workout_slots.append({
            'day_number': i + 1,
            'name': day.name,
            'week_pattern': None,
            'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
        })
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=3,
        rotation_weeks=1,
        weeks=[week],
        summary="PPL x2 compressed - each muscle 2x/week (heavy + light)",
        workout_slots=workout_slots
    )


def _generate_ppl_2day() -> GeneratedSchedule:
    """
    PPL with only 2 days: Heavy combining + 3-week rotation.
    
    Week 1: Push+Legs, Pull+Legs  
    Week 2: Push+Pull, Legs+Push
    Week 3: Pull+Legs, Push+Pull
    
    Over 3 weeks, each pairing is hit twice, balancing frequency.
    """
    week_patterns_data = [
        ([[("Push", True), ("Legs", False)], [("Pull", True), ("Legs", True)]], 'week_mod_1'),
        ([[("Push", True), ("Pull", False)], [("Legs", True), ("Push", False)]], 'week_mod_2'),
        ([[("Pull", True), ("Legs", False)], [("Push", True), ("Pull", True)]], 'week_mod_0'),
    ]
    
    weeks = []
    workout_slots = []
    
    for week_num, (pattern, week_pattern) in enumerate(week_patterns_data, 1):
        days = []
        for day_num, combo in enumerate(pattern, 1):
            focuses = []
            names = []
            for name, is_heavy in combo:
                focuses.append(WorkoutFocus(
                    name=name,
                    is_heavy=is_heavy,
                    muscle_groups=FOCUS_MUSCLE_GROUPS[name]
                ))
                names.append(name)
            
            day = WorkoutDay(
                day_number=day_num,
                name=" + ".join(names),
                focuses=focuses,
                week_pattern=week_pattern
            )
            days.append(day)
            
            workout_slots.append({
                'day_number': day_num,
                'name': day.name,
                'week_pattern': week_pattern,
                'focuses': [{'name': f.name, 'is_heavy': f.is_heavy, 'muscle_groups': f.muscle_groups} for f in day.focuses]
            })
        
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=2,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 2-day - 3-week rotation, combines workouts for coverage",
        workout_slots=workout_slots
    )


def _generate_custom(days_per_week: int) -> GeneratedSchedule:
    """Custom: Empty structure for user to define."""
    days = []
    workout_slots = []
    
    for i in range(days_per_week):
        day = WorkoutDay(
            day_number=i + 1,
            name=f"Day {i + 1}",
            focuses=[],
            week_pattern=None
        )
        days.append(day)
        
        workout_slots.append({
            'day_number': i + 1,
            'name': day.name,
            'week_pattern': None,
            'focuses': []
        })
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.CUSTOM,
        days_per_week=days_per_week,
        rotation_weeks=1,
        weeks=[week],
        summary="Custom split - define your own workout structure",
        workout_slots=workout_slots
    )


def get_week_pattern_for_week(week_number: int, rotation_weeks: int) -> str:
    """
    Determine which week_pattern applies to a given week number.
    
    For 2-week rotations (odd/even):
        - Week 1, 3, 5, 7... → 'odd'
        - Week 2, 4, 6, 8... → 'even'
    
    For 3-week rotations:
        - Week 1, 4, 7... → 'week_mod_1'
        - Week 2, 5, 8... → 'week_mod_2'
        - Week 3, 6, 9... → 'week_mod_0'
    """
    if rotation_weeks == 1:
        return None  # No pattern needed
    elif rotation_weeks == 2:
        return 'odd' if week_number % 2 == 1 else 'even'
    elif rotation_weeks == 3:
        mod = week_number % 3
        if mod == 1:
            return 'week_mod_1'
        elif mod == 2:
            return 'week_mod_2'
        else:
            return 'week_mod_0'
    else:
        # For other rotations, use modulo
        return f'week_mod_{week_number % rotation_weeks}'


def schedule_to_dict(schedule: GeneratedSchedule) -> dict:
    """Convert GeneratedSchedule to JSON-serializable dict."""
    return {
        "split_type": schedule.split_type.value,
        "days_per_week": schedule.days_per_week,
        "rotation_weeks": schedule.rotation_weeks,
        "summary": schedule.summary,
        "workout_slots": schedule.workout_slots,
        "weeks": [
            {
                "week_number": week.week_number,
                "days": [
                    {
                        "day_number": day.day_number,
                        "name": day.name,
                        "display_name": day.display_name,
                        "week_pattern": day.week_pattern,
                        "focuses": [
                            {
                                "name": focus.name,
                                "is_heavy": focus.is_heavy,
                                "muscle_groups": focus.muscle_groups
                            }
                            for focus in day.focuses
                        ]
                    }
                    for day in week.days
                ]
            }
            for week in schedule.weeks
        ]
    }


# Convenience function for API
def generate_schedule_dict(split_type: str, days_per_week: int) -> dict:
    """Generate schedule and return as dictionary."""
    schedule = generate_schedule(split_type, days_per_week)
    return schedule_to_dict(schedule)