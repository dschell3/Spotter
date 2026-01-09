-- =============================================
-- PHASE 3: ADDITIONAL EXERCISES SEED DATA
-- =============================================
-- Run this after schema_phase3.sql to add exercise variations
-- for the substitution feature

-- Additional Chest Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111401', 'Incline Dumbbell Press', 'chest', 'dumbbell',
 ARRAY['30-45 degree incline', 'Elbows at 45 degrees', 'Touch outer chest', 'Press up and slightly in'], true, NULL),
('11111111-1111-1111-1111-111111111402', 'Cable Fly', 'chest', 'cable',
 ARRAY['Slight bend in elbows', 'Squeeze at the center', 'Control the negative', 'Keep chest up'], false, NULL),
('11111111-1111-1111-1111-111111111403', 'Dumbbell Fly', 'chest', 'dumbbell',
 ARRAY['Slight bend in elbows throughout', 'Lower until stretch', 'Squeeze pecs at top', 'Controlled tempo'], false, NULL),
('11111111-1111-1111-1111-111111111404', 'Machine Chest Press', 'chest', 'machine',
 ARRAY['Adjust seat height', 'Grip at chest level', 'Full range of motion', 'Squeeze at contraction'], true, NULL),
('11111111-1111-1111-1111-111111111405', 'Push-Up', 'chest', 'bodyweight',
 ARRAY['Hands shoulder width', 'Core tight', 'Full range of motion', 'Elbows 45 degrees'], true, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Back Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111411', 'T-Bar Row', 'back', 'barbell',
 ARRAY['Chest on pad if available', 'Pull to lower chest', 'Squeeze shoulder blades', 'Control the weight'], true, NULL),
('11111111-1111-1111-1111-111111111412', 'Single Arm Dumbbell Row', 'back', 'dumbbell',
 ARRAY['Knee on bench', 'Pull to hip', 'Keep back flat', 'Full stretch at bottom'], true, NULL),
('11111111-1111-1111-1111-111111111413', 'Lat Pulldown', 'back', 'cable',
 ARRAY['Lean back slightly', 'Pull to upper chest', 'Squeeze lats at bottom', 'Control the negative'], true, NULL),
('11111111-1111-1111-1111-111111111414', 'Chest Supported Row', 'back', 'dumbbell',
 ARRAY['Chest on incline bench', 'Pull to lower chest', 'Squeeze shoulder blades', 'No momentum'], true, NULL),
('11111111-1111-1111-1111-111111111415', 'Straight Arm Pulldown', 'back', 'cable',
 ARRAY['Arms straight throughout', 'Pull down to thighs', 'Squeeze lats hard', 'Control the movement'], false, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Shoulder Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111421', 'Dumbbell Shoulder Press', 'shoulders', 'dumbbell',
 ARRAY['Seated or standing', 'Press straight up', 'Lower to ear level', 'Core braced'], true, NULL),
('11111111-1111-1111-1111-111111111422', 'Arnold Press', 'shoulders', 'dumbbell',
 ARRAY['Start palms facing you', 'Rotate as you press', 'Full extension at top', 'Controlled descent'], true, NULL),
('11111111-1111-1111-1111-111111111423', 'Cable Lateral Raise', 'shoulders', 'cable',
 ARRAY['Slight bend in elbow', 'Raise to shoulder height', 'Control the negative', 'Lead with elbow'], false, NULL),
('11111111-1111-1111-1111-111111111424', 'Machine Shoulder Press', 'shoulders', 'machine',
 ARRAY['Adjust seat properly', 'Grip at shoulder width', 'Press to full extension', 'Control descent'], true, NULL),
('11111111-1111-1111-1111-111111111425', 'Front Raise', 'shoulders', 'dumbbell',
 ARRAY['Slight bend in elbows', 'Raise to eye level', 'Control the weight', 'Alternate or together'], false, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Triceps Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111431', 'Close Grip Bench Press', 'triceps', 'barbell',
 ARRAY['Hands shoulder width', 'Elbows tucked', 'Touch lower chest', 'Lock out at top'], true, NULL),
('11111111-1111-1111-1111-111111111432', 'Overhead Tricep Extension', 'triceps', 'dumbbell',
 ARRAY['Elbows pointed up', 'Lower behind head', 'Extend to full lockout', 'Keep elbows still'], false, NULL),
('11111111-1111-1111-1111-111111111433', 'Tricep Dips', 'triceps', 'bodyweight',
 ARRAY['Elbows back not flared', 'Lower to 90 degrees', 'Press to lockout', 'Lean forward slightly for chest'], true, NULL),
('11111111-1111-1111-1111-111111111434', 'Cable Kickback', 'triceps', 'cable',
 ARRAY['Upper arm parallel to floor', 'Extend fully', 'Squeeze at contraction', 'Control the negative'], false, NULL),
('11111111-1111-1111-1111-111111111435', 'Skull Crushers', 'triceps', 'barbell',
 ARRAY['Lower to forehead', 'Elbows stay fixed', 'Extend to full lockout', 'Use EZ bar if available'], false, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Biceps Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111441', 'Preacher Curl', 'biceps', 'barbell',
 ARRAY['Armpits at top of pad', 'Full stretch at bottom', 'Squeeze at top', 'Control the negative'], false, NULL),
('11111111-1111-1111-1111-111111111442', 'Concentration Curl', 'biceps', 'dumbbell',
 ARRAY['Elbow on inner thigh', 'Full range of motion', 'Squeeze at top', 'No swinging'], false, NULL),
('11111111-1111-1111-1111-111111111443', 'Cable Curl', 'biceps', 'cable',
 ARRAY['Elbows at sides', 'Curl to shoulders', 'Squeeze at top', 'Control descent'], false, NULL),
('11111111-1111-1111-1111-111111111444', 'Incline Dumbbell Curl', 'biceps', 'dumbbell',
 ARRAY['45 degree incline', 'Arms hang straight down', 'Curl to shoulders', 'Great stretch at bottom'], false, NULL),
('11111111-1111-1111-1111-111111111445', 'Spider Curl', 'biceps', 'dumbbell',
 ARRAY['Chest on incline bench', 'Arms hang straight', 'Curl and squeeze', 'No momentum'], false, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Quad Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111451', 'Front Squat', 'quads', 'barbell',
 ARRAY['Elbows high', 'Upright torso', 'Full depth', 'Drive through midfoot'], true, NULL),
('11111111-1111-1111-1111-111111111452', 'Bulgarian Split Squat', 'quads', 'dumbbell',
 ARRAY['Rear foot elevated', '90 degree front knee', 'Upright torso', 'Push through front heel'], true, NULL),
('11111111-1111-1111-1111-111111111453', 'Hack Squat', 'quads', 'machine',
 ARRAY['Feet shoulder width', 'Full depth', 'Push through heels', 'Control the negative'], true, NULL),
('11111111-1111-1111-1111-111111111454', 'Sissy Squat', 'quads', 'bodyweight',
 ARRAY['Hold for balance', 'Lean back as you squat', 'Knees travel forward', 'Squeeze quads'], false, NULL),
('11111111-1111-1111-1111-111111111455', 'Goblet Squat', 'quads', 'dumbbell',
 ARRAY['Hold dumbbell at chest', 'Elbows inside knees', 'Full depth', 'Upright torso'], true, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Hamstring Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111461', 'Lying Leg Curl', 'hamstrings', 'machine',
 ARRAY['Pad above heels', 'Curl all the way up', 'Control the negative', 'Hips stay down'], false, NULL),
('11111111-1111-1111-1111-111111111462', 'Seated Leg Curl', 'hamstrings', 'machine',
 ARRAY['Adjust pad position', 'Full range of motion', 'Squeeze at contraction', 'Control negative'], false, NULL),
('11111111-1111-1111-1111-111111111463', 'Good Morning', 'hamstrings', 'barbell',
 ARRAY['Bar on upper back', 'Hinge at hips', 'Slight knee bend', 'Feel hamstring stretch'], true, NULL),
('11111111-1111-1111-1111-111111111464', 'Nordic Curl', 'hamstrings', 'bodyweight',
 ARRAY['Anchor feet securely', 'Lower slowly', 'Catch yourself at bottom', 'Push back up'], false, NULL),
('11111111-1111-1111-1111-111111111465', 'Single Leg Deadlift', 'hamstrings', 'dumbbell',
 ARRAY['Hinge at hip', 'Back leg extends behind', 'Keep hips square', 'Squeeze glute to stand'], true, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Glute Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111471', 'Cable Pull Through', 'glutes', 'cable',
 ARRAY['Face away from cable', 'Hinge at hips', 'Squeeze glutes to stand', 'Keep arms straight'], true, NULL),
('11111111-1111-1111-1111-111111111472', 'Glute Bridge', 'glutes', 'barbell',
 ARRAY['Bar on hip crease', 'Feet flat on floor', 'Drive through heels', 'Squeeze at top'], true, NULL),
('11111111-1111-1111-1111-111111111473', 'Step Up', 'glutes', 'dumbbell',
 ARRAY['Full foot on box', 'Drive through heel', 'Control the descent', 'No push off back foot'], true, NULL),
('11111111-1111-1111-1111-111111111474', 'Kickback', 'glutes', 'cable',
 ARRAY['Slight forward lean', 'Kick straight back', 'Squeeze at top', 'Control the movement'], false, NULL),
('11111111-1111-1111-1111-111111111475', 'Sumo Deadlift', 'glutes', 'barbell',
 ARRAY['Wide stance, toes out', 'Grip inside knees', 'Push floor apart', 'Squeeze glutes at top'], true, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Calf Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111481', 'Seated Calf Raise', 'calves', 'machine',
 ARRAY['Knees at 90 degrees', 'Full stretch at bottom', 'Pause at top', 'Slow negatives'], false, NULL),
('11111111-1111-1111-1111-111111111482', 'Donkey Calf Raise', 'calves', 'machine',
 ARRAY['Bend at hips', 'Full range of motion', 'Pause at top', 'Stretch at bottom'], false, NULL),
('11111111-1111-1111-1111-111111111483', 'Single Leg Calf Raise', 'calves', 'dumbbell',
 ARRAY['Hold for balance', 'Full stretch at bottom', 'Squeeze at top', 'Control the negative'], false, NULL),
('11111111-1111-1111-1111-111111111484', 'Leg Press Calf Raise', 'calves', 'machine',
 ARRAY['Balls of feet on platform', 'Full extension', 'Slow and controlled', 'Feel the stretch'], false, NULL)
ON CONFLICT (id) DO NOTHING;

-- Additional Rear Delt Exercises
INSERT INTO exercises (id, name, muscle_group, equipment, cues, is_compound, video_url) VALUES
('11111111-1111-1111-1111-111111111491', 'Reverse Pec Deck', 'rear_delts', 'machine',
 ARRAY['Chest against pad', 'Arms slightly bent', 'Squeeze shoulder blades', 'Control the negative'], false, NULL),
('11111111-1111-1111-1111-111111111492', 'Cable Face Pull', 'rear_delts', 'cable',
 ARRAY['Pull to face', 'Elbows high', 'External rotate at end', 'Squeeze rear delts'], false, NULL),
('11111111-1111-1111-1111-111111111493', 'Bent Over Reverse Fly', 'rear_delts', 'dumbbell',
 ARRAY['Hinge forward', 'Slight bend in elbows', 'Lead with elbows', 'Squeeze at top'], false, NULL),
('11111111-1111-1111-1111-111111111494', 'Prone Y Raise', 'rear_delts', 'dumbbell',
 ARRAY['Lie face down on incline', 'Arms form Y shape', 'Thumbs up', 'Squeeze upper back'], false, NULL)
ON CONFLICT (id) DO NOTHING;
