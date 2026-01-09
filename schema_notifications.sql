-- ============================================
-- NOTIFICATION SYSTEM SCHEMA (Phase 5a)
-- Run this in Supabase SQL Editor after existing schema
-- ============================================

-- ============================================
-- NOTIFICATION PREFERENCES TABLE
-- ============================================
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Contact info
    phone_number TEXT,
    phone_confirmed BOOLEAN DEFAULT false,  -- Soft confirmation (user double-checked)
    
    -- Workout reminder settings
    workout_reminder_enabled BOOLEAN DEFAULT false,
    workout_reminder_hours INTEGER DEFAULT 2,  -- Hours before scheduled workout
    workout_reminder_channel TEXT DEFAULT 'email',  -- 'email' or 'sms'
    
    -- Inactivity nudge settings  
    inactivity_nudge_enabled BOOLEAN DEFAULT false,
    inactivity_week_via_email BOOLEAN DEFAULT true,   -- 7 days no workout
    inactivity_month_via_sms BOOLEAN DEFAULT false,   -- 30 days no workout (SMS = more urgent)
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- ============================================
-- NOTIFICATION LOG TABLE
-- Tracks sent notifications to prevent duplicates
-- ============================================
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,  -- 'workout_reminder', 'inactivity_week', 'inactivity_month'
    reference_id UUID,                 -- scheduled_workout_id if applicable
    reference_date DATE,               -- For inactivity checks (the date we checked)
    channel TEXT NOT NULL,             -- 'email' or 'sms'
    status TEXT DEFAULT 'sent',        -- 'sent', 'failed', 'bounced'
    error_message TEXT,                -- If failed, why
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Fast lookup for checking if notification already sent
CREATE INDEX idx_notification_log_dedup 
ON notification_log(user_id, notification_type, reference_id);

-- For inactivity checks (find by date to prevent re-sending same day)
CREATE INDEX idx_notification_log_date 
ON notification_log(user_id, notification_type, reference_date);

-- Find users with notifications enabled
CREATE INDEX idx_notification_prefs_enabled 
ON notification_preferences(workout_reminder_enabled, inactivity_nudge_enabled);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

-- Users can only see/edit their own preferences
CREATE POLICY "Users can view own notification preferences" 
ON notification_preferences FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences" 
ON notification_preferences FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences" 
ON notification_preferences FOR UPDATE 
USING (auth.uid() = user_id);

-- Users can view their own notification history
CREATE POLICY "Users can view own notification log" 
ON notification_log FOR SELECT 
USING (auth.uid() = user_id);

-- Only backend/service role should insert logs, but for simplicity:
CREATE POLICY "Users can insert own notification log" 
ON notification_log FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- ============================================
-- HELPER: Auto-update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_notification_prefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notification_prefs_updated
    BEFORE UPDATE ON notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_notification_prefs_timestamp();
