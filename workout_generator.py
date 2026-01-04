"""
Workout Generator Module

Generates workout structures based on split type and days per week.
Handles combining workouts and weekly rotations automatically.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
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
    for i in range(days_per_week):
        focus = WorkoutFocus(
            name="Full Body",
            is_heavy=(i % 2 == 0),  # Alternate heavy/light
            muscle_groups=FOCUS_MUSCLE_GROUPS["Full Body"]
        )
        days.append(WorkoutDay(
            day_number=i + 1,
            name=f"Full Body {'A' if i % 2 == 0 else 'B'}",
            focuses=[focus]
        ))
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.FULL_BODY,
        days_per_week=days_per_week,
        rotation_weeks=1,
        weeks=[week],
        summary=f"Full Body {days_per_week}x/week - alternate heavy/light sessions"
    )


def _generate_upper_lower(days_per_week: int) -> GeneratedSchedule:
    """
    Upper/Lower: Alternate between upper and lower body.
    
    2 days: U, L (each 1x/week)
    3 days: Rotate - W1: U,L,U → W2: L,U,L
    4 days: U, L, U, L (each 2x/week)
    5 days: Rotate - W1: U,L,U,L,U → W2: L,U,L,U,L
    6 days: U, L, U, L, U, L (each 3x/week)
    """
    
    if days_per_week % 2 == 0:
        # Even days - no rotation needed
        days = []
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
            days.append(WorkoutDay(
                day_number=i + 1,
                name=f"{focus_name} {'(Heavy)' if is_heavy else '(Light)'}",
                focuses=[focus]
            ))
        
        week = WeekStructure(week_number=1, days=days)
        freq = days_per_week // 2
        
        return GeneratedSchedule(
            split_type=SplitType.UPPER_LOWER,
            days_per_week=days_per_week,
            rotation_weeks=1,
            weeks=[week],
            summary=f"Upper/Lower - each {freq}x/week"
        )
    else:
        # Odd days - need 2-week rotation
        weeks = []
        patterns = ["Upper", "Lower"]
        
        for week_num in range(1, 3):
            days = []
            start_idx = 0 if week_num == 1 else 1  # Alternate starting point
            
            for i in range(days_per_week):
                focus_name = patterns[(start_idx + i) % 2]
                is_heavy = (i < days_per_week // 2 + 1)  # First half heavy
                
                focus = WorkoutFocus(
                    name=focus_name,
                    is_heavy=is_heavy,
                    muscle_groups=FOCUS_MUSCLE_GROUPS[focus_name]
                )
                days.append(WorkoutDay(
                    day_number=i + 1,
                    name=f"{focus_name} {'(Heavy)' if is_heavy else '(Light)'}",
                    focuses=[focus]
                ))
            
            weeks.append(WeekStructure(week_number=week_num, days=days))
        
        return GeneratedSchedule(
            split_type=SplitType.UPPER_LOWER,
            days_per_week=days_per_week,
            rotation_weeks=2,
            weeks=weeks,
            summary=f"Upper/Lower - 2-week rotation to balance frequency"
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
    for i, (name, is_heavy) in enumerate(pattern):
        focus = WorkoutFocus(
            name=name,
            is_heavy=is_heavy,
            muscle_groups=FOCUS_MUSCLE_GROUPS[name]
        )
        days.append(WorkoutDay(
            day_number=i + 1,
            name=f"{name} {'(Heavy)' if is_heavy else '(Light)'}",
            focuses=[focus]
        ))
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=6,
        rotation_weeks=1,
        weeks=[week],
        summary="Classic PPL x2 - each muscle group 2x/week"
    )


def _generate_ppl_5day() -> GeneratedSchedule:
    """PPL with 5 days: Rotate to balance over 3 weeks."""
    # Sequence: P,P,L,P,P → L,P,P,L,P → P,L,P,P,L
    sequences = [
        [("Push", True), ("Pull", True), ("Legs", True), ("Push", False), ("Pull", False)],
        [("Legs", False), ("Push", True), ("Pull", True), ("Legs", True), ("Push", False)],
        [("Pull", False), ("Legs", False), ("Push", True), ("Pull", True), ("Legs", True)],
    ]
    
    weeks = []
    for week_num, sequence in enumerate(sequences, 1):
        days = []
        for i, (name, is_heavy) in enumerate(sequence):
            focus = WorkoutFocus(
                name=name,
                is_heavy=is_heavy,
                muscle_groups=FOCUS_MUSCLE_GROUPS[name]
            )
            days.append(WorkoutDay(
                day_number=i + 1,
                name=f"{name} {'(Heavy)' if is_heavy else '(Light)'}",
                focuses=[focus]
            ))
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=5,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 5-day - 3-week rotation for balanced frequency"
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
    base_pattern = [
        [("Push", True)],
        [("Pull", True)],
        [("Legs", True)],
        [("Push", False), ("Pull", False)],  # Combined light upper
    ]
    
    for week_num in range(1, 4):
        days = []
        # Rotate the pattern
        offset = (week_num - 1) % 4
        rotated = base_pattern[offset:] + base_pattern[:offset]
        
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
            
            days.append(WorkoutDay(
                day_number=i + 1,
                name=" + ".join(names),
                focuses=focuses
            ))
        
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=4,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 4-day - combines one upper day, rotates for balance"
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
        
        days.append(WorkoutDay(
            day_number=i + 1,
            name=f"{heavy_name} (Heavy) + {light_name} (Light)",
            focuses=focuses
        ))
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=3,
        rotation_weeks=1,
        weeks=[week],
        summary="PPL x2 compressed - each muscle 2x/week (heavy + light)"
    )


def _generate_ppl_2day() -> GeneratedSchedule:
    """
    PPL with only 2 days: Heavy combining + 3-week rotation.
    
    Week 1: Push+Legs, Pull+Legs  
    Week 2: Push+Pull, Legs+Push
    Week 3: Pull+Legs, Push+Pull
    
    Over 3 weeks, each pairing is hit twice, balancing frequency.
    """
    week_patterns = [
        [[("Push", True), ("Legs", False)], [("Pull", True), ("Legs", True)]],
        [[("Push", True), ("Pull", False)], [("Legs", True), ("Push", False)]],
        [[("Pull", True), ("Legs", False)], [("Push", True), ("Pull", True)]],
    ]
    
    weeks = []
    for week_num, pattern in enumerate(week_patterns, 1):
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
            
            days.append(WorkoutDay(
                day_number=day_num,
                name=" + ".join(names),
                focuses=focuses
            ))
        
        weeks.append(WeekStructure(week_number=week_num, days=days))
    
    return GeneratedSchedule(
        split_type=SplitType.PPL,
        days_per_week=2,
        rotation_weeks=3,
        weeks=weeks,
        summary="PPL 2-day - 3-week rotation, combines workouts for coverage"
    )


def _generate_custom(days_per_week: int) -> GeneratedSchedule:
    """Custom: Empty structure for user to define."""
    days = []
    for i in range(days_per_week):
        days.append(WorkoutDay(
            day_number=i + 1,
            name=f"Day {i + 1}",
            focuses=[]
        ))
    
    week = WeekStructure(week_number=1, days=days)
    
    return GeneratedSchedule(
        split_type=SplitType.CUSTOM,
        days_per_week=days_per_week,
        rotation_weeks=1,
        weeks=[week],
        summary="Custom split - define your own workout structure"
    )


def schedule_to_dict(schedule: GeneratedSchedule) -> dict:
    """Convert GeneratedSchedule to JSON-serializable dict."""
    return {
        "split_type": schedule.split_type.value,
        "days_per_week": schedule.days_per_week,
        "rotation_weeks": schedule.rotation_weeks,
        "summary": schedule.summary,
        "weeks": [
            {
                "week_number": week.week_number,
                "days": [
                    {
                        "day_number": day.day_number,
                        "name": day.name,
                        "display_name": day.display_name,
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