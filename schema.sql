-- ============================================
-- WORKOUT TRACKER DATABASE SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension (should already be enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PROFILES TABLE (extends Supabase auth.users)
-- ============================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,
    days_per_week INTEGER DEFAULT 3,
    split_type TEXT DEFAULT 'ppl',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile when user signs up
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================
-- EXERCISES TABLE
-- ============================================
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    muscle_group TEXT NOT NULL,
    equipment TEXT,
    cues TEXT[], -- Array of form cues
    video_url TEXT,
    is_compound BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- WORKOUT TEMPLATES
-- ============================================
CREATE TABLE workout_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    split_type TEXT NOT NULL, -- 'ppl', 'upper_lower', 'full_body', etc.
    day_number INTEGER NOT NULL,
    description TEXT,
    focus TEXT[], -- Array of muscle groups
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TEMPLATE EXERCISES (exercises in a template)
-- ============================================
CREATE TABLE template_exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES workout_templates(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    sets INTEGER NOT NULL,
    rep_range_low INTEGER,
    rep_range_high INTEGER,
    rep_range_text TEXT, -- For things like "10-12 each"
    rest_seconds INTEGER DEFAULT 90,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USER WORKOUTS (logged workout sessions)
-- ============================================
CREATE TABLE user_workouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    template_id UUID REFERENCES workout_templates(id),
    template_name TEXT, -- Denormalized for history
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- WORKOUT SETS (individual set performance)
-- ============================================
CREATE TABLE workout_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_workout_id UUID REFERENCES user_workouts(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT, -- Denormalized for history
    set_number INTEGER NOT NULL,
    weight DECIMAL(6,2),
    reps INTEGER,
    rpe INTEGER, -- Rate of perceived exertion (optional)
    completed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE workout_sets ENABLE ROW LEVEL SECURITY;

-- Profiles: users can only see/edit their own
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- User workouts: users can only see/edit their own
CREATE POLICY "Users can view own workouts" ON user_workouts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workouts" ON user_workouts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workouts" ON user_workouts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own workouts" ON user_workouts
    FOR DELETE USING (auth.uid() = user_id);

-- Workout sets: users can manage sets for their own workouts
CREATE POLICY "Users can view own workout sets" ON workout_sets
    FOR SELECT USING (
        auth.uid() = (SELECT user_id FROM user_workouts WHERE id = user_workout_id)
    );

CREATE POLICY "Users can insert own workout sets" ON workout_sets
    FOR INSERT WITH CHECK (
        auth.uid() = (SELECT user_id FROM user_workouts WHERE id = user_workout_id)
    );

CREATE POLICY "Users can update own workout sets" ON workout_sets
    FOR UPDATE USING (
        auth.uid() = (SELECT user_id FROM user_workouts WHERE id = user_workout_id)
    );

CREATE POLICY "Users can delete own workout sets" ON workout_sets
    FOR DELETE USING (
        auth.uid() = (SELECT user_id FROM user_workouts WHERE id = user_workout_id)
    );

-- Exercises and templates are public (read-only for all)
ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE workout_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_exercises ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Exercises are viewable by everyone" ON exercises
    FOR SELECT USING (true);

CREATE POLICY "Templates are viewable by everyone" ON workout_templates
    FOR SELECT USING (true);

CREATE POLICY "Template exercises are viewable by everyone" ON template_exercises
    FOR SELECT USING (true);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX idx_user_workouts_user_id ON user_workouts(user_id);
CREATE INDEX idx_user_workouts_completed_at ON user_workouts(completed_at);
CREATE INDEX idx_workout_sets_workout_id ON workout_sets(user_workout_id);
CREATE INDEX idx_template_exercises_template_id ON template_exercises(template_id);
CREATE INDEX idx_exercises_muscle_group ON exercises(muscle_group);
