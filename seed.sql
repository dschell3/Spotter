-- ============================================
-- SEED DATA: EXERCISES AND TEMPLATES
-- Run this AFTER schema.sql
-- ============================================

-- ============================================
-- EXERCISES
-- ============================================

-- Push exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound) VALUES
('11111111-1111-1111-1111-111111111101', 'Barbell Bench Press', 'chest', 'barbell', 
 ARRAY['Retract shoulder blades', 'Feet flat on floor', 'Bar path: nipple line to lockout', 'Control the descent'], true),

('11111111-1111-1111-1111-111111111102', 'Overhead Press', 'shoulders', 'barbell',
 ARRAY['Brace core tight', 'Bar starts at collarbone', 'Press straight up, head through at top', 'Squeeze glutes'], true),

('11111111-1111-1111-1111-111111111103', 'Incline Dumbbell Press', 'chest', 'dumbbell',
 ARRAY['30-45 degree incline', 'Dumbbells at shoulder level', 'Press up and slightly in', 'Feel the stretch at bottom'], true),

('11111111-1111-1111-1111-111111111104', 'Lateral Raise', 'shoulders', 'dumbbell',
 ARRAY['Slight bend in elbows', 'Lead with elbows, not hands', 'Raise to shoulder height', 'Control the negative'], false),

('11111111-1111-1111-1111-111111111105', 'Tricep Pushdown', 'triceps', 'cable',
 ARRAY['Elbows pinned to sides', 'Full extension at bottom', 'Squeeze triceps hard', 'Slow negative'], false),

('11111111-1111-1111-1111-111111111106', 'Cable Fly', 'chest', 'cable',
 ARRAY['Slight bend in elbows throughout', 'Bring hands together at chest height', 'Squeeze at peak contraction', 'Feel the stretch on return'], false),

-- Pull exercises
('11111111-1111-1111-1111-111111111201', 'Barbell Row', 'back', 'barbell',
 ARRAY['Hinge at hips, flat back', 'Pull to lower chest/upper abs', 'Squeeze shoulder blades together', 'Control the descent'], true),

('11111111-1111-1111-1111-111111111202', 'Pull-Up', 'back', 'bodyweight',
 ARRAY['Start from dead hang', 'Pull elbows down and back', 'Chin over bar', 'Full extension at bottom'], true),

('11111111-1111-1111-1111-111111111203', 'Lat Pulldown', 'back', 'cable',
 ARRAY['Slight lean back', 'Pull to upper chest', 'Squeeze lats at bottom', 'Control the return'], true),

('11111111-1111-1111-1111-111111111204', 'Face Pull', 'rear_delts', 'cable',
 ARRAY['High pulley position', 'Pull to face, elbows high', 'External rotate at end', 'Squeeze rear delts'], false),

('11111111-1111-1111-1111-111111111205', 'Barbell Curl', 'biceps', 'barbell',
 ARRAY['Elbows pinned to sides', 'Full range of motion', 'Squeeze at top', 'Control the negative'], false),

('11111111-1111-1111-1111-111111111206', 'Hammer Curl', 'biceps', 'dumbbell',
 ARRAY['Neutral grip throughout', 'Elbows stationary', 'Squeeze brachialis at top', 'Alternate or together'], false),

('11111111-1111-1111-1111-111111111207', 'Seated Cable Row', 'back', 'cable',
 ARRAY['Sit tall, chest up', 'Pull to lower chest', 'Squeeze shoulder blades', 'Full stretch forward'], true),

-- Leg exercises
('11111111-1111-1111-1111-111111111301', 'Barbell Back Squat', 'quads', 'barbell',
 ARRAY['Bar on upper traps', 'Brace core, big breath', 'Break at hips and knees together', 'Knees track over toes'], true),

('11111111-1111-1111-1111-111111111302', 'Romanian Deadlift', 'hamstrings', 'barbell',
 ARRAY['Slight knee bend, fixed', 'Hinge at hips, push butt back', 'Feel hamstring stretch', 'Squeeze glutes at top'], true),

('11111111-1111-1111-1111-111111111303', 'Leg Press', 'quads', 'machine',
 ARRAY['Feet shoulder width on platform', 'Lower until 90 degrees', 'Press through heels', 'Don''t lock knees at top'], true),

('11111111-1111-1111-1111-111111111304', 'Lying Leg Curl', 'hamstrings', 'machine',
 ARRAY['Hips flat on pad', 'Curl heels to glutes', 'Squeeze at top', 'Slow negative'], false),

('11111111-1111-1111-1111-111111111305', 'Leg Extension', 'quads', 'machine',
 ARRAY['Back flat against pad', 'Extend to full lockout', 'Squeeze quads hard', 'Control the descent'], false),

('11111111-1111-1111-1111-111111111306', 'Standing Calf Raise', 'calves', 'machine',
 ARRAY['Full stretch at bottom', 'Rise onto balls of feet', 'Pause at top', 'Slow negative'], false),

('11111111-1111-1111-1111-111111111307', 'Barbell Hip Thrust', 'glutes', 'barbell',
 ARRAY['Upper back on bench', 'Bar on hip crease', 'Drive through heels', 'Squeeze glutes at top, pause'], true),

('11111111-1111-1111-1111-111111111308', 'Walking Lunge', 'quads', 'dumbbell',
 ARRAY['Upright torso', '90 degree angles both knees', 'Push through front heel', 'Keep core braced'], true);

-- ============================================
-- WORKOUT TEMPLATES (PPL 3-Day)
-- ============================================

-- Day 1: Push + Pull
INSERT INTO workout_templates (id, name, split_type, day_number, description, focus) VALUES
('22222222-2222-2222-2222-222222222201', 'Push + Pull', 'ppl_3day', 1, 
 'Combined push and pull movements', 
 ARRAY['chest', 'shoulders', 'triceps', 'back', 'biceps']);

-- Day 2: Legs + Push
INSERT INTO workout_templates (id, name, split_type, day_number, description, focus) VALUES
('22222222-2222-2222-2222-222222222202', 'Legs + Push', 'ppl_3day', 2,
 'Lower body with push accessories',
 ARRAY['quads', 'hamstrings', 'glutes', 'calves', 'chest', 'shoulders']);

-- Day 3: Pull + Legs
INSERT INTO workout_templates (id, name, split_type, day_number, description, focus) VALUES
('22222222-2222-2222-2222-222222222203', 'Pull + Legs', 'ppl_3day', 3,
 'Pull movements with lower body',
 ARRAY['back', 'biceps', 'rear_delts', 'hamstrings', 'glutes']);

-- ============================================
-- TEMPLATE EXERCISES
-- ============================================

-- Day 1: Push + Pull exercises
INSERT INTO template_exercises (template_id, exercise_id, order_index, sets, rep_range_low, rep_range_high, rep_range_text, rest_seconds) VALUES
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111101', 1, 4, 6, 8, '6-8', 180),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111201', 2, 4, 6, 8, '6-8', 180),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111102', 3, 3, 8, 10, '8-10', 120),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111203', 4, 3, 8, 12, '8-12', 90),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111106', 5, 3, 12, 15, '12-15', 60),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111204', 6, 3, 15, 20, '15-20', 60),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111105', 7, 3, 10, 12, '10-12', 60),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111205', 8, 3, 10, 12, '10-12', 60);

-- Day 2: Legs + Push exercises
INSERT INTO template_exercises (template_id, exercise_id, order_index, sets, rep_range_low, rep_range_high, rep_range_text, rest_seconds) VALUES
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111301', 1, 4, 6, 8, '6-8', 180),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111302', 2, 3, 8, 10, '8-10', 120),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111103', 3, 3, 8, 10, '8-10', 120),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111303', 4, 3, 10, 12, '10-12', 90),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111104', 5, 3, 12, 15, '12-15', 60),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111304', 6, 3, 10, 12, '10-12', 60),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111306', 7, 4, 12, 15, '12-15', 60);

-- Day 3: Pull + Legs exercises
INSERT INTO template_exercises (template_id, exercise_id, order_index, sets, rep_range_low, rep_range_high, rep_range_text, rest_seconds) VALUES
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111202', 1, 4, 6, 10, '6-10', 180),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111307', 2, 4, 8, 10, '8-10', 120),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111207', 3, 3, 8, 12, '8-12', 90),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111308', 4, 3, 10, 12, '10-12 each', 90),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111204', 5, 3, 15, 20, '15-20', 60),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111305', 6, 3, 12, 15, '12-15', 60),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111206', 7, 3, 10, 12, '10-12', 60);
