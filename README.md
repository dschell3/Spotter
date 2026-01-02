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

### Phase 2 (Current) ✅
- Supabase PostgreSQL database
- User authentication (email/password)
- Cloud-synced workout history
- Profile page with user settings
- Workout history view
- Exercises and templates stored in database

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

# Run development server
python app.py
```

Visit `http://localhost:5000` in your browser.

## Database Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run `schema.sql`
3. Run `seed.sql` to populate exercises and templates
4. Update `config.py` with your Supabase URL and anon key

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
- User authentication (email + password)
- Cloud-synced workout history

### Phase 2.5: Google OAuth
- [ ] Google sign-in integration
- [ ] Apple sign-in (future)

### Phase 3: Planning Dashboard
- [ ] Weekly workout planning view
- [ ] Exercise library management
- [ ] Exercise substitution suggestions (by muscle group)
- [ ] Custom routine builder

### Phase 4: Progress Tracking
- [ ] Profile dashboard
- [ ] Progress charts (weight per exercise, volume, consistency)
- [ ] Personal records tracking
- [ ] Export workout data

### Phase 5: Polish
- [ ] Video links for exercise demos
- [ ] Notifications/reminders
- [ ] Social features (optional)

## Project Structure

```
workout-app/
├── app.py                 # Flask application
├── config.py              # Configuration settings
├── db.py                  # Database queries
├── requirements.txt       # Python dependencies
├── schema.sql             # Database schema
├── seed.sql               # Exercise/template seed data
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
    ├── profile.html       # User profile
    └── auth/
        ├── login.html     # Login page
        └── signup.html    # Signup page
```

## License

Personal project - feel free to use as inspiration for your own workout tracker!
