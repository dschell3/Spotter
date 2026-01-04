# Workout Tracker

A personal workout tracking PWA inspired by Persist, designed for hypertrophy training with a compressed PPL split.

## Features

### Phase 1 (MVP) ✅
- Mobile-optimized workout execution view
- Hardcoded PPL×2 routine (3 days)
- Set/rep/weight tracking with local storage
- Form cues for each exercise
- Progress bar and completion tracking
- PWA installable on mobile devices
- High-contrast dark theme for gym visibility

### Phase 2 ✅
- Supabase PostgreSQL database
- User authentication (email/password)
- Cloud-synced workout history
- Profile page with user settings
- Exercises and templates stored in database

### Phase 3 (NEW) ✅
- **Training Cycles**: Plan 4, 6, or 8 week training blocks
- **Weekly Planning View**: Horizontal calendar showing scheduled workouts
- **Smart Scheduling**: Auto-populates based on your split type and preferred training days
- **Heavy/Light Structure**: PPL×2 with intelligent heavy/light rotation
- **Exercise Substitution**: Swap exercises with same muscle group alternatives
- **Drag & Reschedule**: Move workouts within the week as your schedule changes
- **Cycle Copy**: Start new cycles from previous ones with tweaks
- **Progressive Overload Suggestions**: Weight increase recommendations based on performance
- **Profile Training Settings**: Configure split type, days/week, cycle length, preferred days

## Tech Stack

- **Backend**: Flask
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth
- **Frontend**: Jinja2 + Tailwind CSS + Vanilla JS
- **Hosting**: Render (planned)

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Run development server
python app.py
```

Visit `http://localhost:5000` in your browser.

## Database Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run these scripts in order:
   - `schema.sql` - Base tables
   - `seed.sql` - Exercises and workout templates
   - `schema_phase3.sql` - Cycles and planning tables
   - `seed_phase3.sql` - Additional exercises for substitutions
3. Update your `.env` file with Supabase URL and anon key

## New in Phase 3: Cycles & Planning

### Training Cycles
A cycle is a 4-8 week training block where:
- Exercises stay consistent throughout (no weekly rotation)
- Progressive overload is tracked week-to-week
- Heavy/Light structure alternates each session

### PPL×2 (3-Day) Structure
- **Day 1**: Push (Heavy) + Pull (Light)
- **Day 2**: Legs (Heavy) + Push (Light)  
- **Day 3**: Pull (Heavy) + Legs (Light)

Heavy = lower rep ranges (4-8), longer rest
Light = higher rep ranges (10-15), shorter rest

### Weekly Planning
Navigate to `/plan` to see your weekly calendar:
- Workouts auto-populate based on your cycle
- Drag to reschedule within the week
- Mark workouts as completed or skipped
- View progress across the full cycle

### Creating a New Cycle
1. Go to Profile → New Cycle (or `/cycle/new`)
2. Choose: Start fresh from template OR copy from previous cycle
3. Select your split type and cycle length
4. Set your preferred training days
5. Review and swap exercises as needed
6. Start the cycle

## PWA Installation

On mobile (iOS/Android):
1. Open the app in Safari/Chrome
2. Tap "Share" → "Add to Home Screen"
3. The app will work offline and feel native

## Project Roadmap

### Phase 1: MVP ✅
- Workout execution view
- Local storage persistence
- PWA setup

### Phase 2: Database & Auth ✅
- Supabase integration
- User authentication
- Cloud-synced workout history

### Phase 3: Planning Dashboard ✅
- Training cycles (4/6/8 weeks)
- Weekly workout planning view
- Exercise substitution by muscle group
- Profile training settings
- Smart workout suggestions

### Phase 4: Progress Tracking
- [ ] Progress charts (weight per exercise, volume, consistency)
- [ ] Personal records tracking
- [ ] Export workout data
- [ ] Visual progress dashboard

### Phase 5: Polish
- [ ] Video links for exercise demos
- [ ] Notifications/reminders
- [ ] Google OAuth
- [ ] Social features (optional)

## Project Structure

```
workout-app/
├── app.py                 # Flask application
├── config.py              # Configuration settings
├── db.py                  # Database queries (base)
├── db_cycles.py           # Database queries (cycles/planning)
├── requirements.txt       # Python dependencies
├── schema.sql             # Base database schema
├── schema_phase3.sql      # Phase 3 schema additions
├── seed.sql               # Exercise/template seed data
├── seed_phase3.sql        # Additional exercise variations
├── data/
│   └── routines.py        # Fallback hardcoded data
├── static/
│   ├── icons/             # PWA icons
│   ├── js/
│   │   └── sw.js          # Service worker
│   └── manifest.json      # PWA manifest
└── templates/
    ├── base.html          # Base template with Tailwind
    ├── index.html         # Day selection page
    ├── workout.html       # Workout execution view
    ├── history.html       # Workout history
    ├── profile.html       # User profile + training settings
    ├── plan.html          # Weekly planning view (NEW)
    ├── cycle_new.html     # Create new cycle wizard (NEW)
    ├── cycle_view.html    # Cycle overview (NEW)
    └── auth/
        ├── login.html     
        └── signup.html    
```

## API Endpoints (Phase 3)

### Cycles
- `POST /api/cycle/create` - Create new cycle
- `POST /api/cycle/<id>/activate` - Start a cycle
- `POST /api/cycle/<id>/complete` - End a cycle

### Scheduling
- `POST /api/schedule/<id>/reschedule` - Move workout to new date
- `POST /api/schedule/<id>/skip` - Skip a workout

### Exercises
- `GET /api/exercises/<muscle_group>/substitutes` - Get replacement options

### Profile
- `POST /api/profile/settings` - Update training preferences

## License

Personal project - feel free to use as inspiration for your own workout tracker!