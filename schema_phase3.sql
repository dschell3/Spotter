-- =============================================
-- PHASE 3: TRAINING CYCLES SCHEMA
-- =============================================
-- Run this in Supabase SQL Editor after schema.sql and seed.sql

-- =============================================
-- TRAINING CYCLES
-- =============================================
-- A cycle is a multi-week training block

CREATE TABLE IF NOT EXISTS training_cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    length_weeks INTEGER DEFAULT 6,
    days_per_week INTEGER DEFAULT 3,
    split_type TEXT DEFAULT 'ppl',  -- 'ppl', 'upper_lower', 'full_body', 'bro_split'
    status TEXT DEFAULT 'planned',   -- 'planned', 'active', 'completed', 'abandoned'
    copied_from UUID REFERENCES training_cycles(id),
    rotation_weeks INTEGER DEFAULT 1,  -- For PPL rotation pattern
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding user's cycles
CREATE INDEX IF NOT EXISTS idx_training_cycles_user ON training_cycles(user_id);
CREATE INDEX IF NOT EXISTS idx_training_cycles_status ON training_cycles(user_id, status);


-- =============================================
-- CYCLE WORKOUT SLOTS
-- =============================================
-- Defines which workouts happen on which days of the cycle

CREATE TABLE IF NOT EXISTS cycle_workout_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,  -- 0=Monday, 6=Sunday
    template_id UUID REFERENCES workout_templates(id),
    workout_name TEXT NOT NULL,
    is_heavy_focus BOOLEAN DEFAULT true,
    order_index INTEGER DEFAULT 0,
    week_pattern TEXT,  -- For rotation patterns
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cycle_slots_cycle ON cycle_workout_slots(cycle_id);


-- =============================================
-- CYCLE EXERCISES
-- =============================================
-- Specific exercises assigned to each workout slot in a cycle

CREATE TABLE IF NOT EXISTS cycle_exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    cycle_workout_slot_id UUID NOT NULL REFERENCES cycle_workout_slots(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT NOT NULL,
    muscle_group TEXT,
    is_heavy BOOLEAN DEFAULT true,
    order_index INTEGER DEFAULT 0,
    sets_heavy INTEGER DEFAULT 4,
    sets_light INTEGER DEFAULT 3,
    rep_range_heavy TEXT DEFAULT '6-8',
    rep_range_light TEXT DEFAULT '10-12',
    rest_seconds_heavy INTEGER DEFAULT 180,
    rest_seconds_light INTEGER DEFAULT 90,
    week_number INTEGER,  -- NULL = all weeks, specific number = only that week
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cycle_exercises_cycle ON cycle_exercises(cycle_id);
CREATE INDEX IF NOT EXISTS idx_cycle_exercises_slot ON cycle_exercises(cycle_workout_slot_id);


-- =============================================
-- SCHEDULED WORKOUTS
-- =============================================
-- Individual workout instances scheduled for specific dates

CREATE TABLE IF NOT EXISTS scheduled_workouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cycle_id UUID REFERENCES training_cycles(id) ON DELETE CASCADE,
    cycle_workout_slot_id UUID REFERENCES cycle_workout_slots(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    workout_name TEXT NOT NULL,
    week_number INTEGER,  -- Which week of the cycle
    status TEXT DEFAULT 'scheduled',  -- 'scheduled', 'completed', 'skipped', 'missed'
    user_workout_id UUID REFERENCES user_workouts(id),  -- Link to completed workout
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_workouts_user ON scheduled_workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_workouts_date ON scheduled_workouts(user_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_scheduled_workouts_cycle ON scheduled_workouts(cycle_id);


-- =============================================
-- CYCLE WORKOUT TEMPLATES (Alternative structure)
-- =============================================
-- For storing full workout template data within a cycle

CREATE TABLE IF NOT EXISTS cycle_workout_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    day_of_week INTEGER,
    week_number INTEGER,
    workout_type TEXT,  -- 'heavy', 'light', 'standard'
    exercises JSONB DEFAULT '[]'::jsonb,  -- Array of exercise objects
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cycle_templates_cycle ON cycle_workout_templates(cycle_id);


-- =============================================
-- ADD PROFILE COLUMNS FOR TRAINING PREFERENCES
-- =============================================

-- Add training preference columns if they don't exist
DO $$ 
BEGIN
    -- Cycle length preference
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'cycle_length') THEN
        ALTER TABLE profiles ADD COLUMN cycle_length INTEGER DEFAULT 6;
    END IF;
    
    -- Preferred training days
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'preferred_days') THEN
        ALTER TABLE profiles ADD COLUMN preferred_days INTEGER[] DEFAULT ARRAY[0, 2, 4];
    END IF;
END $$;


-- =============================================
-- DISABLE ROW LEVEL SECURITY (for simplicity)
-- =============================================

ALTER TABLE training_cycles DISABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_workout_slots DISABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_exercises DISABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_workouts DISABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_workout_templates DISABLE ROW LEVEL SECURITY;


-- =============================================
-- SUMMARY
-- =============================================
-- Tables created:
--   - training_cycles: Multi-week training blocks
--   - cycle_workout_slots: Which workouts on which days
--   - cycle_exercises: Exercises for each slot
--   - scheduled_workouts: Specific dated workout instances
--   - cycle_workout_templates: Full workout templates (JSON)
--
-- Profile columns added:
--   - cycle_length: Default cycle duration (weeks)
--   - preferred_days: Which days user typically trains
