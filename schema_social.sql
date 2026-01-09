-- =============================================
-- PHASE 6: SOCIAL FEATURES SCHEMA
-- =============================================
-- Run this in Supabase SQL Editor after previous schemas

-- =============================================
-- SHARED CYCLES
-- =============================================
-- Tracks cycles that have been shared (either publicly or via link)

CREATE TABLE IF NOT EXISTS shared_cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Share settings
    share_code VARCHAR(12) UNIQUE NOT NULL,  -- Short code for URLs (e.g., "abc123xyz")
    is_public BOOLEAN DEFAULT false,          -- Show in public library
    is_template BOOLEAN DEFAULT false,        -- Marked as trainer template
    
    -- Metadata for library display
    title VARCHAR(100),                       -- Custom title (defaults to cycle name)
    description TEXT,                         -- Description of the program
    tags VARCHAR(50)[],                       -- e.g., ['hypertrophy', 'beginner', 'ppl']
    
    -- Stats
    copy_count INTEGER DEFAULT 0,             -- How many times copied
    view_count INTEGER DEFAULT 0,             -- How many times viewed
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up by share code
CREATE INDEX IF NOT EXISTS idx_shared_cycles_share_code ON shared_cycles(share_code);

-- Index for public library queries
CREATE INDEX IF NOT EXISTS idx_shared_cycles_public ON shared_cycles(is_public, created_at DESC) WHERE is_public = true;

-- Index for user's shared cycles
CREATE INDEX IF NOT EXISTS idx_shared_cycles_user ON shared_cycles(user_id);


-- =============================================
-- CYCLE COPIES (TRACKING)
-- =============================================
-- Tracks who copied which shared cycle (for analytics)

CREATE TABLE IF NOT EXISTS cycle_copies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shared_cycle_id UUID NOT NULL REFERENCES shared_cycles(id) ON DELETE CASCADE,
    source_cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    new_cycle_id UUID NOT NULL REFERENCES training_cycles(id) ON DELETE CASCADE,
    copied_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    copied_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding copies of a shared cycle
CREATE INDEX IF NOT EXISTS idx_cycle_copies_shared ON cycle_copies(shared_cycle_id);


-- =============================================
-- PUBLIC PROFILE SETTINGS
-- =============================================
-- Extends profiles with public/social settings

ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS public_display_name VARCHAR(50),
ADD COLUMN IF NOT EXISTS bio TEXT,
ADD COLUMN IF NOT EXISTS is_trainer BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS show_prs_publicly BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS profile_slug VARCHAR(30) UNIQUE;

-- Index for public profile lookups
CREATE INDEX IF NOT EXISTS idx_profiles_slug ON profiles(profile_slug) WHERE profile_slug IS NOT NULL;


-- =============================================
-- SHARED ACHIEVEMENTS (for social sharing)
-- =============================================
-- Stores shareable snapshots of PRs/workouts for social media

CREATE TABLE IF NOT EXISTS shared_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    share_code VARCHAR(12) UNIQUE NOT NULL,
    
    -- What's being shared
    achievement_type VARCHAR(20) NOT NULL,  -- 'pr', 'workout', 'streak', 'cycle_complete'
    
    -- Snapshot data (JSON so it persists even if underlying data changes)
    achievement_data JSONB NOT NULL,
    
    -- Display settings
    display_name VARCHAR(50),  -- Name to show (can be anonymous)
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- Optional expiry for temporary shares
);

-- Index for looking up by share code
CREATE INDEX IF NOT EXISTS idx_shared_achievements_code ON shared_achievements(share_code);


-- =============================================
-- HELPER FUNCTION: Generate share code
-- =============================================

CREATE OR REPLACE FUNCTION generate_share_code(length INTEGER DEFAULT 8)
RETURNS VARCHAR AS $$
DECLARE
    chars TEXT := 'abcdefghijkmnpqrstuvwxyz23456789';  -- Removed confusing chars (0,o,1,l)
    result VARCHAR := '';
    i INTEGER;
BEGIN
    FOR i IN 1..length LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::integer, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- =============================================
-- ROW LEVEL SECURITY (Disabled for simplicity)
-- =============================================

ALTER TABLE shared_cycles DISABLE ROW LEVEL SECURITY;
ALTER TABLE cycle_copies DISABLE ROW LEVEL SECURITY;
ALTER TABLE shared_achievements DISABLE ROW LEVEL SECURITY;


-- =============================================
-- SUMMARY
-- =============================================
-- Tables created:
--   - shared_cycles: Tracks shared/public cycles
--   - cycle_copies: Tracks who copied what
--   - shared_achievements: Snapshots for social media sharing
--
-- Modified:
--   - user_profiles: Added public profile fields
--
-- To share a cycle:
--   1. INSERT into shared_cycles with share_code
--   2. Link is: /shared/cycle/{share_code}
--
-- To copy a shared cycle:
--   1. Look up shared_cycles by share_code
--   2. Copy the cycle data to new training_cycle
--   3. Record in cycle_copies
--   4. Increment copy_count
