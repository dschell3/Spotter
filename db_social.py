"""
Database functions for Social Features (Phase 6)
Handles sharing cycles, public library, and social sharing.
"""

from db import get_supabase_client
from datetime import datetime
import secrets
import string


def generate_share_code(length=8):
    """Generate a URL-safe share code."""
    # Using only unambiguous characters
    alphabet = 'abcdefghijkmnpqrstuvwxyz23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================
# SHARE CYCLE
# ============================================

def share_cycle(user_id: str, cycle_id: str, is_public: bool = False, 
                is_template: bool = False, title: str = None, 
                description: str = None, tags: list = None):
    """
    Share a cycle, generating a unique share link.
    
    Args:
        user_id: Owner of the cycle
        cycle_id: The cycle to share
        is_public: Whether to show in public library
        is_template: Whether this is a trainer template
        title: Custom title (optional)
        description: Description for library (optional)
        tags: List of tags for filtering (optional)
    
    Returns:
        The shared_cycle record with share_code
    """
    # Check if already shared
    existing = get_supabase_client().table('shared_cycles').select('*').eq('cycle_id', cycle_id).eq('user_id', user_id).execute()
    
    if existing.data:
        # Update existing share settings
        result = get_supabase_client().table('shared_cycles').update({
            'is_public': is_public,
            'is_template': is_template,
            'title': title,
            'description': description,
            'tags': tags,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', existing.data[0]['id']).execute()
        return result.data[0] if result.data else None
    
    # Generate unique share code
    share_code = generate_share_code()
    
    # Ensure uniqueness (retry if collision)
    for _ in range(5):
        check = get_supabase_client().table('shared_cycles').select('id').eq('share_code', share_code).execute()
        if not check.data:
            break
        share_code = generate_share_code()
    
    # Create share record
    result = get_supabase_client().table('shared_cycles').insert({
        'cycle_id': cycle_id,
        'user_id': user_id,
        'share_code': share_code,
        'is_public': is_public,
        'is_template': is_template,
        'title': title,
        'description': description,
        'tags': tags or []
    }).execute()
    
    return result.data[0] if result.data else None


def unshare_cycle(user_id: str, cycle_id: str):
    """Remove a cycle from sharing."""
    result = get_supabase_client().table('shared_cycles').delete().eq('cycle_id', cycle_id).eq('user_id', user_id).execute()
    return result.data[0] if result.data else None


def get_shared_cycle_by_code(share_code: str):
    """
    Get a shared cycle by its share code.
    Also increments view count.
    """
    # Get the shared cycle record
    result = get_supabase_client().table('shared_cycles').select('''
        *,
        training_cycles (
            id,
            name,
            split_type,
            length_weeks,
            days_per_week,
            created_at
        )
    ''').eq('share_code', share_code).execute()
    
    if not result.data:
        return None
    
    shared = result.data[0]
    
    # Increment view count
    get_supabase_client().table('shared_cycles').update({
        'view_count': shared.get('view_count', 0) + 1
    }).eq('id', shared['id']).execute()
    
    return shared


def get_user_shared_cycles(user_id: str):
    """Get all cycles shared by a user."""
    result = get_supabase_client().table('shared_cycles').select('''
        *,
        training_cycles (
            id,
            name,
            split_type,
            length_weeks,
            days_per_week
        )
    ''').eq('user_id', user_id).order('created_at', desc=True).execute()
    
    return result.data or []


# ============================================
# PUBLIC LIBRARY
# ============================================

def get_public_cycles(limit: int = 20, offset: int = 0, 
                      split_type: str = None, tags: list = None,
                      sort_by: str = 'recent'):
    """
    Get public cycles for the library.
    
    Args:
        limit: Number of results
        offset: Pagination offset
        split_type: Filter by split type
        tags: Filter by tags (any match)
        sort_by: 'recent', 'popular', 'most_copied'
    """
    query = get_supabase_client().table('shared_cycles').select('''
        *,
        training_cycles (
            id,
            name,
            split_type,
            length_weeks,
            days_per_week
        ),
        profiles!shared_cycles_user_id_fkey (
            display_name,
            public_display_name,
            is_trainer
        )
    ''').eq('is_public', True)
    
    # Apply filters
    if split_type:
        query = query.eq('training_cycles.split_type', split_type)
    
    # Sort
    if sort_by == 'popular':
        query = query.order('view_count', desc=True)
    elif sort_by == 'most_copied':
        query = query.order('copy_count', desc=True)
    else:  # recent
        query = query.order('created_at', desc=True)
    
    # Pagination
    query = query.range(offset, offset + limit - 1)
    
    result = query.execute()
    return result.data or []


def get_template_cycles(trainer_id: str = None):
    """Get template cycles, optionally filtered by trainer."""
    query = get_supabase_client().table('shared_cycles').select('''
        *,
        training_cycles (
            id,
            name,
            split_type,
            length_weeks,
            days_per_week
        ),
        profiles!shared_cycles_user_id_fkey (
            display_name,
            public_display_name,
            is_trainer
        )
    ''').eq('is_template', True)
    
    if trainer_id:
        query = query.eq('user_id', trainer_id)
    
    result = query.order('created_at', desc=True).execute()
    return result.data or []


# ============================================
# COPY CYCLE
# ============================================

def copy_shared_cycle(share_code: str, user_id: str, new_name: str = None):
    """
    Copy a shared cycle to a user's account.
    
    Returns the new cycle ID if successful.
    """
    # Get the shared cycle
    shared = get_shared_cycle_by_code(share_code)
    if not shared:
        return None, "Shared cycle not found"
    
    source_cycle = shared.get('training_cycles')
    if not source_cycle:
        return None, "Source cycle not found"
    
    # Get the full cycle details including workout templates
    from db_cycles import get_cycle_by_id, get_cycle_workout_templates
    
    source_cycle_full = get_cycle_by_id(source_cycle['id'])
    if not source_cycle_full:
        return None, "Could not load source cycle"
    
    # Get workout templates for the cycle
    templates = get_cycle_workout_templates(source_cycle['id'])
    
    # Create new cycle for user
    cycle_name = new_name or f"{source_cycle.get('name', 'Copied Cycle')} (Copy)"
    
    new_cycle_data = {
        'user_id': user_id,
        'name': cycle_name,
        'split_type': source_cycle.get('split_type'),
        'length_weeks': source_cycle.get('length_weeks'),
        'days_per_week': source_cycle.get('days_per_week'),
        'status': 'planned'  # Start as planned, not active
    }
    
    result = get_supabase_client().table('training_cycles').insert(new_cycle_data).execute()
    if not result.data:
        return None, "Failed to create cycle"
    
    new_cycle_id = result.data[0]['id']
    
    # Copy workout templates
    for template in templates:
        template_data = {
            'cycle_id': new_cycle_id,
            'name': template.get('name'),
            'day_of_week': template.get('day_of_week'),
            'week_number': template.get('week_number'),
            'workout_type': template.get('workout_type'),
            'exercises': template.get('exercises', [])
        }
        get_supabase_client().table('cycle_workout_templates').insert(template_data).execute()
    
    # Record the copy
    get_supabase_client().table('cycle_copies').insert({
        'shared_cycle_id': shared['id'],
        'source_cycle_id': source_cycle['id'],
        'new_cycle_id': new_cycle_id,
        'copied_by_user_id': user_id
    }).execute()
    
    # Increment copy count
    get_supabase_client().table('shared_cycles').update({
        'copy_count': shared.get('copy_count', 0) + 1
    }).eq('id', shared['id']).execute()
    
    return new_cycle_id, None


# ============================================
# SHARED ACHIEVEMENTS (Social Media)
# ============================================

def create_shared_achievement(user_id: str, achievement_type: str, 
                               achievement_data: dict, display_name: str = None,
                               expires_days: int = None):
    """
    Create a shareable achievement snapshot.
    
    Args:
        user_id: The user sharing
        achievement_type: 'pr', 'workout', 'streak', 'cycle_complete'
        achievement_data: JSON data for the achievement
        display_name: Name to display (can be anonymous)
        expires_days: Days until share expires (None = permanent)
    """
    share_code = generate_share_code()
    
    # Ensure uniqueness
    for _ in range(5):
        check = get_supabase_client().table('shared_achievements').select('id').eq('share_code', share_code).execute()
        if not check.data:
            break
        share_code = generate_share_code()
    
    data = {
        'user_id': user_id,
        'share_code': share_code,
        'achievement_type': achievement_type,
        'achievement_data': achievement_data,
        'display_name': display_name
    }
    
    if expires_days:
        from datetime import timedelta
        data['expires_at'] = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
    
    result = get_supabase_client().table('shared_achievements').insert(data).execute()
    return result.data[0] if result.data else None


def get_shared_achievement(share_code: str):
    """Get a shared achievement by code."""
    result = get_supabase_client().table('shared_achievements').select('*').eq('share_code', share_code).execute()
    
    if not result.data:
        return None
    
    achievement = result.data[0]
    
    # Check expiry
    if achievement.get('expires_at'):
        expires = datetime.fromisoformat(achievement['expires_at'].replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=expires.tzinfo) > expires:
            return None  # Expired
    
    return achievement


# ============================================
# PUBLIC PROFILE
# ============================================

def update_public_profile(user_id: str, updates: dict):
    """Update public profile settings."""
    allowed_fields = {
        'public_display_name',
        'bio',
        'is_trainer',
        'show_prs_publicly',
        'profile_slug'
    }
    
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not filtered:
        return None
    
    result = get_supabase_client().table('profiles').update(filtered).eq('id', user_id).execute()
    return result.data[0] if result.data else None


def get_public_profile(profile_slug: str):
    """Get a public profile by slug."""
    result = get_supabase_client().table('profiles').select('''
        id,
        display_name,
        public_display_name,
        bio,
        is_trainer,
        show_prs_publicly,
        profile_slug
    ''').eq('profile_slug', profile_slug).execute()
    
    if not result.data:
        return None
    
    # Add user_id field for compatibility
    profile = result.data[0]
    profile['user_id'] = profile['id']
    return profile


def check_profile_slug_available(slug: str, exclude_user_id: str = None):
    """Check if a profile slug is available."""
    query = get_supabase_client().table('profiles').select('id').eq('profile_slug', slug)
    
    if exclude_user_id:
        query = query.neq('id', exclude_user_id)
    
    result = query.execute()
    return len(result.data) == 0