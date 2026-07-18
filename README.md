# Spotter

A personal workout tracking PWA designed for hypertrophy training with customizable training splits. Built for personal trainers and fitness enthusiasts who want a simple, mobile-first workout companion.

Largely Vibe-coded with Claude Code.

**Live Demo**: [spotter-a1ux.onrender.com](https://spotter-a1ux.onrender.com)

## Features

### Workout Tracking
- Mobile-optimized workout execution view
- Set/rep/weight tracking with cloud sync
- Form cues and exercise demonstrations (YouTube integration)
- Progress bar and completion tracking
- High-contrast dark theme for gym visibility
- PWA installable on mobile devices

### Training Cycles
- Plan 4, 6, or 8 week training blocks
- Multiple split types: PPL, Upper/Lower, Full Body, Custom
- Heavy/Light structure with intelligent rotation
- Drag-and-drop workout rescheduling
- Exercise substitution by muscle group
- Copy previous cycles as templates

### Progress Analytics
- Strength progression charts per exercise
- Volume tracking over time
- Consistency heatmap (GitHub-style)
- Personal records (PR) tracking and celebrations
- Export data to CSV or PDF

### AI Coach
- **Weight Suggestions** - Algorithmic recommendations based on recent performance
  - Suggests weight increases when hitting top of rep range
  - Advises maintaining or decreasing based on struggle patterns
  - No AI cost (pure algorithm)
- **Deload/Progression Detection** - Rule-based analysis with AI prescriptions
  - Detects plateaus, volume drops, and completion rate changes
  - Generates encouraging, actionable recommendations
  - Triggers ~every 2-4 weeks when signals detected
- **Adapt My Week** - AI-powered workout modifications
  - Appears when you've missed scheduled workouts
  - Suggests modified workouts prioritizing missed muscle groups
  - Uses your existing exercise library

### Notifications
- Email workout reminders (configurable hours before)
- SMS notifications for important nudges
- Inactivity reminders (1 week and 1 month)
- Powered by Resend (email) and Twilio (SMS)

### Social & Sharing
- Share training cycles via unique links
- Public cycle library for discovery
- Trainer templates for client distribution
- Share PRs and workout completions to social media
- Copy shared cycles to your account with one click

### Authentication
- Email/password authentication
- Google OAuth sign-in
- Secure session management via Supabase Auth

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Flask (Python) |
| **Database** | Supabase (PostgreSQL) |
| **Auth** | Supabase Auth + Google OAuth |
| **Frontend** | Jinja2 + Tailwind CSS + Vanilla JS |
| **Charts** | Chart.js |
| **AI** | Anthropic Claude API |
| **Email** | Resend |
| **SMS** | Twilio |
| **Hosting** | Render |
| **Cron Jobs** | cron-job.org |

## Quick Start

### Prerequisites
- Python 3.9+
- Supabase account
- (Optional) Anthropic API key for AI coach features
- (Optional) Resend account for emails
- (Optional) Twilio account for SMS

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/workout-app.git
cd workout-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run development server
python app.py
```

Visit `http://localhost:5000` in your browser.

### Environment Variables

```env
# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key            # anon key: browser Supabase Auth handshake only
SUPABASE_SERVICE_KEY=your-service-role-key  # SERVER-ONLY, never expose to the browser

# Cron auth
CRON_SECRET=random-secret-for-cron-auth

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# AI Coach (optional - features work with defaults if not set)
ANTHROPIC_API_KEY=sk-ant-xxx

# Notifications (optional)
RESEND_API_KEY=re_xxx
NOTIFICATION_FROM_EMAIL=notifications@yourdomain.com
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
CRON_SECRET=random-secret-for-cron-auth
```

## Security Model

Spotter uses a single trust boundary at the Flask server:

- **Server = `service_role`**: The Flask backend performs all database access with
  the Supabase `service_role` key (`SUPABASE_SERVICE_KEY`), which bypasses RLS.
  Authorization is enforced entirely at the application layer — session-based auth
  plus explicit `user_id` / ownership checks on every query that touches
  user-owned data.
- **PostgREST = fully locked**: `migrations/phase1_rls_lockdown.sql` enables RLS on
  every table in `public` with no policies and revokes all direct privileges from
  the `anon` and `authenticated` roles. Nothing can be read or written through the
  public REST API. (Run this migration only *after* the service-role code is
  deployed — see the header of that file.)
- **Anon key = auth handshake only**: The browser anon key (`SUPABASE_KEY`) is used
  solely for the client-side Supabase Auth (Google OAuth PKCE) flow. It is never
  used to query application tables and must never be given the service key.

The `SUPABASE_SERVICE_KEY` is server-only: it must never be rendered into a
template, shipped in client-side JavaScript, or otherwise exposed to the browser.

## Database Setup

Run these SQL scripts in Supabase SQL Editor (in order):

1. `schema.sql` - Base tables (users, exercises, workouts)
2. `seed.sql` - Exercise library and workout templates
3. `schema_phase3.sql` - Training cycles and scheduling
4. `seed_phase3.sql` - Additional exercise variations
5. `schema_progress.sql` - Progress tracking and PRs
6. `schema_notifications.sql` - Notification preferences
7. `schema_social.sql` - Sharing and social features
8. `schema_ai_coach.sql` - AI coach recommendations and usage tracking

## Project Structure

```
workout-app/
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings
├── db.py                     # Core database queries
├── db_cycles.py              # Cycle/planning queries
├── db_progress.py            # Progress tracking queries
├── db_notifications.py       # Notification queries
├── db_social.py              # Social feature queries
├── db_export.py              # CSV/PDF export
├── db_coach.py               # AI coach database queries
├── ai_coach.py               # AI coach logic and detection
├── notification_service.py   # Email/SMS sending
├── workout_generator.py      # Workout generation logic
├── requirements.txt          # Python dependencies
│
├── schema.sql                # Base database schema
├── schema_phase3.sql         # Cycles schema
├── schema_progress.sql       # Progress schema
├── schema_notifications.sql  # Notifications schema
├── schema_social.sql         # Social features schema
├── schema_ai_coach.sql       # AI coach schema
├── seed.sql                  # Exercise seed data
│
├── static/
│   ├── icons/                # PWA icons
│   ├── js/
│   │   ├── sw.js             # Service worker
│   │   └── ai_coach.js       # AI coach frontend
│   └── manifest.json         # PWA manifest
│
└── templates/
    ├── base.html             # Base template
    ├── index.html            # Home/workout selection
    ├── workout.html          # Workout execution
    ├── plan.html             # Weekly planning view
    ├── progress.html         # Progress dashboard
    ├── history.html          # Workout history
    ├── profile.html          # User profile
    ├── notifications.html    # Notification settings
    ├── library.html          # Public cycle library
    ├── cycle_new.html        # New cycle wizard
    ├── cycle_view.html       # Cycle overview
    ├── shared_cycle.html     # Public shared cycle view
    ├── shared_pr.html        # Shareable PR card
    ├── shared_workout.html   # Shareable workout card
    └── auth/
        ├── login.html
        ├── signup.html
        └── google_callback.html
```

## API Endpoints

### Authentication
- `POST /login` - Email/password login
- `POST /signup` - Create account
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - Google OAuth callback
- `POST /logout` - Log out

### Workouts
- `GET /workout/<day_id>` - Workout execution view
- `POST /api/workout/start` - Start a workout
- `POST /api/workout/<id>/set` - Log a set
- `POST /api/workout/<id>/complete` - Complete workout

### Cycles
- `POST /api/cycle/create` - Create new cycle
- `POST /api/cycle/<id>/activate` - Start a cycle
- `POST /api/cycle/<id>/complete` - End a cycle
- `POST /api/schedule/<id>/reschedule` - Move workout
- `POST /api/schedule/<id>/skip` - Skip workout

### Progress
- `GET /api/progress/exercise-history` - Exercise progression data
- `GET /api/progress/volume` - Volume over time
- `GET /api/progress/consistency` - Consistency stats
- `POST /api/progress/check-pr` - Check for new PR
- `GET /api/export/csv` - Export to CSV
- `GET /api/export/pdf` - Export to PDF

### AI Coach
- `GET /api/coach/weight-suggestion/<exercise_id>` - Get weight suggestion for exercise
- `POST /api/coach/workout-suggestions` - Batch weight suggestions for workout
- `GET /api/coach/check` - Check for deload/progression recommendations
- `POST /api/coach/recommendation/<id>/apply` - Apply a recommendation
- `POST /api/coach/recommendation/<id>/dismiss` - Dismiss a recommendation
- `GET /api/coach/adapt-check` - Check if adapt option should show
- `POST /api/coach/adapt-week` - Generate adapted workout suggestions
- `POST /api/coach/apply-adaptation` - Apply an adapted workout
- `GET /api/coach/usage` - Get AI usage statistics

### Social
- `POST /api/cycle/<id>/share` - Share a cycle
- `POST /api/cycle/<id>/unshare` - Remove sharing
- `GET /api/library/cycles` - Browse public cycles
- `POST /api/shared/cycle/<code>/copy` - Copy shared cycle
- `POST /api/share/achievement` - Share PR/workout

### Notifications
- `GET /api/notifications/preferences` - Get settings
- `POST /api/notifications/preferences` - Update settings
- `GET /api/cron/notifications` - Process notifications (cron)

## PWA Installation

### iOS
1. Open the app in Safari
2. Tap the Share button
3. Select "Add to Home Screen"

### Android
1. Open the app in Chrome
2. Tap the menu (⋮)
3. Select "Add to Home Screen"

## Deployment

### Render

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Add environment variables in Render dashboard

### Cron Jobs

Set up at [cron-job.org](https://cron-job.org) (free):
- URL: `https://your-app.onrender.com/api/cron/notifications?secret=YOUR_CRON_SECRET`
- Schedule: Every hour (`0 * * * *`)

## Development Roadmap

### Completed ✅

- **Phase 1**: MVP - Workout execution, PWA, local storage
- **Phase 2**: Database & Auth - Supabase, user accounts, cloud sync
- **Phase 3**: Planning - Training cycles, scheduling, exercise substitution
- **Phase 4**: Progress - Charts, PRs, heatmap, CSV/PDF export
- **Phase 5**: Notifications - Email reminders, SMS nudges, cron automation
- **Phase 6**: Social - Cycle sharing, public library, trainer templates
- **Phase 6.1**: Personal Exercise Notes - User-specific notes per exercise
- **Phase 6.2**: Mid-Workout Exercise Swap - Substitute exercises on-the-fly
  - One-time swap (doesn't affect future scheduled workouts)
  - Option to make swap permanent for the current cycle
  - Quick access to substitutes filtered by same muscle group
  - Swap disabled after completing any sets for that exercise
- **Phase 7**: AI Coach - Intelligent workout assistance
  - Weight/rep suggestions based on recent performance (algorithmic, free)
  - Deload/progression detection with AI-generated prescriptions
  - "Adapt My Week" for missed workout recovery
  - Usage tracking and daily limits for cost control

### Future Ideas 💡

- **AI "Snap to Identify"** - Photo-based equipment identification
  - Take a photo of a gym machine → AI identifies it
  - Shows relevant form cues and suggested exercises
- Apple Watch / Wear OS companion app
- Integration with fitness trackers
- Multi-language support

## Contributing

This is a personal project, but suggestions and feedback are welcome! Feel free to open an issue or submit a PR.

## License

MIT License - feel free to use as inspiration for your own workout tracker!