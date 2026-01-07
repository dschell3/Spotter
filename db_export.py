"""
Database functions for exporting workout data (Phase 4)
"""
import csv
import io
from datetime import date, datetime, timedelta
from db import get_supabase_client

# For PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def get_export_data(user_id: str, start_date: date = None, end_date: date = None):
    """
    Get all workout data for export within a date range.
    Returns structured data suitable for both CSV and PDF generation.
    """
    supabase = get_supabase_client()
    
    # Build query for workouts with sets
    query = supabase.table('user_workouts')\
        .select('id, template_name, started_at, completed_at, workout_sets(exercise_name, set_number, weight, reps, completed)')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .order('completed_at', desc=True)
    
    if start_date:
        query = query.gte('completed_at', start_date.isoformat())
    if end_date:
        # Add one day to include the end date fully
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.lte('completed_at', end_dt.isoformat())
    
    response = query.execute()
    
    return response.data or []


def get_export_summary(user_id: str, start_date: date = None, end_date: date = None):
    """
    Get summary statistics for the export period.
    """
    supabase = get_supabase_client()
    
    # Get workouts in range
    query = supabase.table('user_workouts')\
        .select('id, completed_at, workout_sets(weight, reps)')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')
    
    if start_date:
        query = query.gte('completed_at', start_date.isoformat())
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.lte('completed_at', end_dt.isoformat())
    
    response = query.execute()
    workouts = response.data or []
    
    # Calculate stats
    total_workouts = len(workouts)
    total_volume = 0
    total_sets = 0
    
    for workout in workouts:
        for s in workout.get('workout_sets', []):
            weight = s.get('weight') or 0
            reps = s.get('reps') or 0
            total_volume += weight * reps
            total_sets += 1
    
    avg_volume = total_volume / total_workouts if total_workouts > 0 else 0
    
    # Calculate weeks for completion rate
    if start_date and end_date:
        days = (end_date - start_date).days + 1
        weeks = max(1, days / 7)
    elif workouts:
        # Use first and last workout dates
        dates = [w['completed_at'][:10] for w in workouts if w.get('completed_at')]
        if dates:
            first = datetime.strptime(min(dates), '%Y-%m-%d').date()
            last = datetime.strptime(max(dates), '%Y-%m-%d').date()
            days = (last - first).days + 1
            weeks = max(1, days / 7)
        else:
            weeks = 1
    else:
        weeks = 1
    
    # Get user's target days per week
    profile = supabase.table('profiles').select('days_per_week').eq('id', user_id).limit(1).execute()
    target_days = profile.data[0].get('days_per_week', 3) if profile.data else 3
    
    target_workouts = int(weeks * target_days)
    completion_rate = min(100, round((total_workouts / target_workouts * 100) if target_workouts > 0 else 0))
    
    # Get PRs in this period
    pr_query = supabase.table('personal_records')\
        .select('exercise_name, weight, reps, achieved_at')\
        .eq('user_id', user_id)
    
    if start_date:
        pr_query = pr_query.gte('achieved_at', start_date.isoformat())
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        pr_query = pr_query.lte('achieved_at', end_dt.isoformat())
    
    prs = pr_query.execute().data or []
    
    # Calculate streaks (simplified - current streak)
    streak = calculate_current_streak(user_id, supabase)
    
    return {
        'total_workouts': total_workouts,
        'total_volume': total_volume,
        'total_sets': total_sets,
        'avg_volume_per_workout': round(avg_volume),
        'completion_rate': completion_rate,
        'current_streak': streak,
        'prs': prs
    }


def calculate_current_streak(user_id: str, supabase=None):
    """Calculate current streak in weeks."""
    if not supabase:
        supabase = get_supabase_client()
    
    response = supabase.table('user_workouts')\
        .select('completed_at')\
        .eq('user_id', user_id)\
        .not_.is_('completed_at', 'null')\
        .order('completed_at', desc=True)\
        .execute()
    
    if not response.data:
        return 0
    
    # Get unique weeks with workouts
    weeks_with_workout = set()
    for w in response.data:
        if w['completed_at']:
            workout_date = datetime.strptime(w['completed_at'][:10], '%Y-%m-%d').date()
            year_week = workout_date.isocalendar()[:2]
            weeks_with_workout.add(year_week)
    
    if not weeks_with_workout:
        return 0
    
    # Count consecutive weeks from current
    today = date.today()
    current_week = today.isocalendar()[:2]
    last_week = (today - timedelta(weeks=1)).isocalendar()[:2]
    
    if current_week not in weeks_with_workout and last_week not in weeks_with_workout:
        return 0
    
    streak = 0
    check_week = current_week if current_week in weeks_with_workout else last_week
    
    while check_week in weeks_with_workout:
        streak += 1
        check_date = date.fromisocalendar(check_week[0], check_week[1], 1) - timedelta(weeks=1)
        check_week = check_date.isocalendar()[:2]
    
    return streak


def generate_csv(user_id: str, start_date: date = None, end_date: date = None) -> str:
    """
    Generate CSV export of workout data.
    Returns CSV string.
    """
    workouts = get_export_data(user_id, start_date, end_date)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow(['Date', 'Workout', 'Exercise', 'Set', 'Weight (lbs)', 'Reps', 'Volume'])
    
    # Data rows - one row per set
    for workout in workouts:
        workout_date = workout['completed_at'][:10] if workout.get('completed_at') else ''
        workout_name = workout.get('template_name', 'Workout')
        
        for s in workout.get('workout_sets', []):
            if not s.get('completed', True):
                continue
                
            weight = s.get('weight') or 0
            reps = s.get('reps') or 0
            volume = weight * reps
            
            writer.writerow([
                workout_date,
                workout_name,
                s.get('exercise_name', ''),
                s.get('set_number', ''),
                weight,
                reps,
                volume
            ])
    
    return output.getvalue()


def generate_pdf(user_id: str, user_name: str, start_date: date = None, end_date: date = None) -> bytes:
    """
    Generate PDF report of workout data.
    Returns PDF bytes.
    """
    workouts = get_export_data(user_id, start_date, end_date)
    summary = get_export_summary(user_id, start_date, end_date)
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=20
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("WORKOUT REPORT", title_style))
    
    # Date range subtitle
    if start_date and end_date:
        date_range = f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
    elif start_date:
        date_range = f"From {start_date.strftime('%b %d, %Y')}"
    elif end_date:
        date_range = f"Through {end_date.strftime('%b %d, %Y')}"
    else:
        date_range = "All Time"
    
    elements.append(Paragraph(f"{user_name} • {date_range}", subtitle_style))
    
    # Summary Section
    elements.append(Paragraph("SUMMARY", section_style))
    
    summary_data = [
        ['Total Workouts', 'Total Volume', 'Avg Volume/Workout', 'Completion Rate', 'Current Streak'],
        [
            str(summary['total_workouts']),
            f"{summary['total_volume']:,} lbs",
            f"{summary['avg_volume_per_workout']:,} lbs",
            f"{summary['completion_rate']}%",
            f"{summary['current_streak']} weeks"
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.4*inch, 1.4*inch, 1.5*inch, 1.2*inch, 1.1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
    ]))
    elements.append(summary_table)
    
    # Personal Records Section
    if summary['prs']:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("PERSONAL RECORDS", section_style))
        
        pr_data = [['Exercise', 'Weight', 'Reps', 'Date']]
        for pr in summary['prs']:
            pr_data.append([
                pr.get('exercise_name', ''),
                f"{pr.get('weight', 0)} lbs",
                str(pr.get('reps', '')),
                pr.get('achieved_at', '')[:10] if pr.get('achieved_at') else ''
            ])
        
        pr_table = Table(pr_data, colWidths=[2.5*inch, 1.2*inch, 0.8*inch, 1.2*inch])
        pr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ]))
        elements.append(pr_table)
    
    # Workout Log Section
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("WORKOUT LOG", section_style))
    
    if workouts:
        log_data = [['Date', 'Workout', 'Exercises', 'Sets', 'Volume']]
        
        for workout in workouts[:50]:  # Limit to 50 most recent
            workout_date = workout['completed_at'][:10] if workout.get('completed_at') else ''
            workout_name = workout.get('template_name', 'Workout')
            
            sets = workout.get('workout_sets', [])
            exercise_names = set(s.get('exercise_name', '') for s in sets)
            num_exercises = len(exercise_names)
            num_sets = len([s for s in sets if s.get('completed', True)])
            
            volume = sum((s.get('weight') or 0) * (s.get('reps') or 0) for s in sets)
            
            log_data.append([
                workout_date,
                workout_name[:20] + '...' if len(workout_name) > 20 else workout_name,
                str(num_exercises),
                str(num_sets),
                f"{volume:,}"
            ])
        
        log_table = Table(log_data, colWidths=[1.1*inch, 2*inch, 1*inch, 0.8*inch, 1.2*inch])
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ]))
        elements.append(log_table)
        
        if len(workouts) > 50:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"... and {len(workouts) - 50} more workouts", styles['Normal']))
    else:
        elements.append(Paragraph("No workouts recorded in this period.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    return buffer.getvalue()
