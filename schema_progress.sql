-- =============================================
-- PHASE 4: PROGRESS TRACKING SCHEMA
-- =============================================
-- Run this in Supabase SQL Editor after schema_phase3.sql

-- =============================================
-- PERSONAL RECORDS
-- =============================================
-- Tracks PRs for each exercise

CREATE TABLE IF NOT EXISTS personal_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT NOT NULL,  -- Denormalized for history
    
    -- PR data
    weight DECIMAL(10,2) NOT NULL,
    reps INTEGER NOT NULL,
    estimated_1rm DECIMAL(10,2),  -- Calculated: weight × (1 + reps/30)
    
    -- When it was set
    achieved_at TIMESTAMPTZ DEFAULT NOW(),
    workout_set_id UUID REFERENCES workout_sets(id),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding user's PRs
CREATE INDEX IF NOT EXISTS idx_personal_records_user ON personal_records(user_id);
CREATE INDEX IF NOT EXISTS idx_personal_records_exercise ON personal_records(user_id, exercise_id);

-- Unique constraint: one PR per user per exercise
CREATE UNIQUE INDEX IF NOT EXISTS idx_personal_records_unique 
ON personal_records(user_id, exercise_id) 
WHERE exercise_id IS NOT NULL;


-- =============================================
-- PR HISTORY
-- =============================================
-- Keeps history of all PRs (not just current best)

CREATE TABLE IF NOT EXISTS pr_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT NOT NULL,
    weight DECIMAL(10,2) NOT NULL,
    reps INTEGER NOT NULL,
    estimated_1rm DECIMAL(10,2),
    achieved_at TIMESTAMPTZ DEFAULT NOW(),
    workout_set_id UUID REFERENCES workout_sets(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pr_history_user ON pr_history(user_id);
CREATE INDEX IF NOT EXISTS idx_pr_history_exercise ON pr_history(user_id, exercise_id);


-- =============================================
-- ADD COLUMNS TO PROFILES FOR PR SETTINGS
-- =============================================

DO $$ 
BEGIN
    -- PR rep threshold (only count PRs at or below this rep count)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'profiles' AND column_name = 'pr_rep_threshold') THEN
        ALTER TABLE profiles ADD COLUMN pr_rep_threshold INTEGER DEFAULT 8;
    END IF;
END $$;


-- =============================================
-- FUNCTION: Calculate Estimated 1RM
-- =============================================
-- Uses Brzycki formula: weight × (36 / (37 - reps))

CREATE OR REPLACE FUNCTION calculate_estimated_1rm(weight DECIMAL, reps INTEGER)
RETURNS DECIMAL AS $$
BEGIN
    IF reps >= 37 THEN
        RETURN weight;  -- Formula breaks down at high reps
    END IF;
    RETURN ROUND(weight * (36.0 / (37.0 - reps)), 2);
END;
$$ LANGUAGE plpgsql;


-- =============================================
-- FUNCTION: Check and Update PR
-- =============================================
-- Call this after logging a set to check if it's a new PR

CREATE OR REPLACE FUNCTION check_pr(
    p_user_id UUID,
    p_exercise_id UUID,
    p_exercise_name TEXT,
    p_weight DECIMAL,
    p_reps INTEGER,
    p_workout_set_id UUID DEFAULT NULL
)
RETURNS TABLE(is_pr BOOLEAN, previous_weight DECIMAL, previous_reps DECIMAL) AS $$
DECLARE
    v_estimated_1rm DECIMAL;
    v_current_pr RECORD;
    v_is_pr BOOLEAN := FALSE;
BEGIN
    -- Calculate estimated 1RM for this lift
    v_estimated_1rm := calculate_estimated_1rm(p_weight, p_reps);
    
    -- Get current PR for this exercise
    SELECT * INTO v_current_pr
    FROM personal_records
    WHERE user_id = p_user_id AND exercise_id = p_exercise_id;
    
    -- Check if this is a new PR (higher estimated 1RM)
    IF v_current_pr IS NULL OR v_estimated_1rm > v_current_pr.estimated_1rm THEN
        v_is_pr := TRUE;
        
        -- Record in PR history
        INSERT INTO pr_history (user_id, exercise_id, exercise_name, weight, reps, estimated_1rm, workout_set_id)
        VALUES (p_user_id, p_exercise_id, p_exercise_name, p_weight, p_reps, v_estimated_1rm, p_workout_set_id);
        
        -- Update or insert current PR
        INSERT INTO personal_records (user_id, exercise_id, exercise_name, weight, reps, estimated_1rm, workout_set_id)
        VALUES (p_user_id, p_exercise_id, p_exercise_name, p_weight, p_reps, v_estimated_1rm, p_workout_set_id)
        ON CONFLICT (user_id, exercise_id) 
        DO UPDATE SET
            weight = p_weight,
            reps = p_reps,
            estimated_1rm = v_estimated_1rm,
            workout_set_id = p_workout_set_id,
            achieved_at = NOW(),
            updated_at = NOW();
    END IF;
    
    -- Return result
    RETURN QUERY SELECT 
        v_is_pr,
        v_current_pr.weight,
        v_current_pr.reps::DECIMAL;
END;
$$ LANGUAGE plpgsql;


-- =============================================
-- VIEW: Exercise Progress Summary
-- =============================================
-- Aggregated view for charting progress over time

CREATE OR REPLACE VIEW exercise_progress_summary AS
SELECT 
    ws.user_workout_id,
    uw.user_id,
    uw.completed_at::DATE as workout_date,
    ws.exercise_id,
    ws.exercise_name,
    COUNT(*) as total_sets,
    MAX(ws.weight) as max_weight,
    SUM(ws.weight * ws.reps) as total_volume,
    AVG(ws.weight) as avg_weight
FROM workout_sets ws
JOIN user_workouts uw ON ws.user_workout_id = uw.id
WHERE uw.completed_at IS NOT NULL
GROUP BY ws.user_workout_id, uw.user_id, uw.completed_at::DATE, ws.exercise_id, ws.exercise_name;


-- =============================================
-- VIEW: Weekly Volume Summary
-- =============================================

CREATE OR REPLACE VIEW weekly_volume_summary AS
SELECT 
    uw.user_id,
    DATE_TRUNC('week', uw.completed_at)::DATE as week_start,
    COUNT(DISTINCT uw.id) as workouts_completed,
    COUNT(ws.id) as total_sets,
    SUM(ws.weight * ws.reps) as total_volume
FROM user_workouts uw
LEFT JOIN workout_sets ws ON ws.user_workout_id = uw.id
WHERE uw.completed_at IS NOT NULL
GROUP BY uw.user_id, DATE_TRUNC('week', uw.completed_at)::DATE;


-- =============================================
-- DISABLE ROW LEVEL SECURITY
-- =============================================

ALTER TABLE personal_records DISABLE ROW LEVEL SECURITY;
ALTER TABLE pr_history DISABLE ROW LEVEL SECURITY;


-- =============================================
-- SUMMARY
-- =============================================
-- Tables created:
--   - personal_records: Current PR for each exercise
--   - pr_history: All PR achievements over time
--
-- Functions created:
--   - calculate_estimated_1rm(): Brzycki formula
--   - check_pr(): Check if a lift is a new PR
--
-- Views created:
--   - exercise_progress_summary: For progress charts
--   - weekly_volume_summary: For volume tracking
