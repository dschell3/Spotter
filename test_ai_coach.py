"""
AI Coach Unit Tests
===================
Run with: python -m pytest test_ai_coach.py -v

Or run individual tests:
python test_ai_coach.py
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the module to test
import ai_coach
from ai_coach import (
    WeightSuggestion,
    calculate_weight_suggestion,
    detect_training_signals,
    SignalType,
    TrainingSignal,
    _detect_stalled_compounds,
    _calculate_volume_trend,
)


class TestWeightSuggestions(unittest.TestCase):
    """Tests for Feature 1: Weight/Rep Suggestions"""
    
    @patch('ai_coach.db_coach')
    def test_no_history_returns_no_suggestion(self, mock_db):
        """Should return no_history when user has no data for exercise"""
        mock_db.get_cached_weight_suggestion.return_value = None
        mock_db.get_recent_exercise_performance.return_value = []
        
        result = calculate_weight_suggestion(
            user_id='user123',
            exercise_id='exercise456',
            use_cache=False
        )
        
        self.assertEqual(result.reason, 'no_history')
        self.assertIsNone(result.suggested_weight)
        self.assertEqual(result.confidence, 'low')
    
    @patch('ai_coach.db_coach')
    def test_hit_rep_ceiling_suggests_increase(self, mock_db):
        """Should suggest weight increase when hitting top of rep range"""
        mock_db.get_cached_weight_suggestion.return_value = None
        mock_db.get_recent_exercise_performance.return_value = [
            {'working_weight': 135, 'avg_reps': 12, 'date': '2024-01-03'},
            {'working_weight': 135, 'avg_reps': 12, 'date': '2024-01-01'},
        ]
        mock_db.cache_weight_suggestion.return_value = {}
        
        result = calculate_weight_suggestion(
            user_id='user123',
            exercise_id='exercise456',
            target_rep_low=8,
            target_rep_high=12,
            is_heavy=True,
            use_cache=False
        )
        
        self.assertEqual(result.reason, 'increase')
        self.assertEqual(result.suggested_weight, 140)  # 135 + 5
        self.assertEqual(result.confidence, 'high')

    # FIXME: RSL in SupaBase is preventing functionality.
    # Bypass the security feature to finish the function.
    @patch('ai_coach.db_coach')
    def test_below_rep_floor_suggests_maintain(self, mock_db):
        """Should suggest maintaining weight when slightly below rep range"""
        mock_db.get_cached_weight_suggestion.return_value = None
        mock_db.get_recent_exercise_performance.return_value = [
            {'working_weight': 150, 'avg_reps': 7, 'date': '2024-01-03'},
            {'working_weight': 150, 'avg_reps': 6, 'date': '2024-01-01'},
        ]
        mock_db.cache_weight_suggestion.return_value = {}
        
        result = calculate_weight_suggestion(
            user_id='user123',
            exercise_id='exercise456',
            target_rep_low=8,
            target_rep_high=12,
            is_heavy=True,
            use_cache=False
        )
        
        self.assertEqual(result.reason, 'maintain')  # Slightly below floor
        self.assertEqual(result.suggested_weight, 150)  # Same weight
    
    @patch('ai_coach.db_coach')
    def test_light_exercise_uses_smaller_increment(self, mock_db):
        """Should use 2.5 lb increment for light/isolation exercises"""
        mock_db.get_cached_weight_suggestion.return_value = None
        mock_db.get_recent_exercise_performance.return_value = [
            {'working_weight': 25, 'avg_reps': 15, 'date': '2024-01-03'},
            {'working_weight': 25, 'avg_reps': 15, 'date': '2024-01-01'},
        ]
        mock_db.cache_weight_suggestion.return_value = {}
        
        result = calculate_weight_suggestion(
            user_id='user123',
            exercise_id='exercise456',
            target_rep_low=10,
            target_rep_high=15,
            is_heavy=False,  # Light exercise
            use_cache=False
        )
        
        self.assertEqual(result.reason, 'increase')
        self.assertEqual(result.suggested_weight, 27.5)  # 25 + 2.5


class TestDeloadDetection(unittest.TestCase):
    """Tests for Feature 2: Deload/Progression Detection"""
    
    def test_detect_stalled_compounds(self):
        """Should detect when compound lifts haven't progressed"""
        trends = {
            'Bench Press': [
                {'date': '2024-01-01', 'max_weight': 185},
                {'date': '2024-01-08', 'max_weight': 185},
                {'date': '2024-01-15', 'max_weight': 185},
            ],
            'Squat': [
                {'date': '2024-01-01', 'max_weight': 225},
                {'date': '2024-01-08', 'max_weight': 230},
                {'date': '2024-01-15', 'max_weight': 235},
            ],
            'Deadlift': [
                {'date': '2024-01-01', 'max_weight': 315},
                {'date': '2024-01-08', 'max_weight': 315},
                {'date': '2024-01-15', 'max_weight': 315},
            ]
        }
        
        stalled = _detect_stalled_compounds(trends)
        
        self.assertIn('Bench Press', stalled)
        self.assertIn('Deadlift', stalled)
        self.assertNotIn('Squat', stalled)  # This one progressed
    
    def test_calculate_volume_trend_decrease(self):
        """Should detect volume decrease"""
        summaries = [
            {'week_start': '2024-01-15', 'total_volume': 8000},
            {'week_start': '2024-01-08', 'total_volume': 8500},
            {'week_start': '2024-01-01', 'total_volume': 10000},
            {'week_start': '2023-12-25', 'total_volume': 10500},
        ]
        
        trend = _calculate_volume_trend(summaries)
        
        # Recent avg: 8250, Prior avg: 10250
        # Change: (8250 - 10250) / 10250 = -0.195
        self.assertLess(trend, -0.15)
    
    def test_calculate_volume_trend_increase(self):
        """Should detect volume increase"""
        summaries = [
            {'week_start': '2024-01-15', 'total_volume': 12000},
            {'week_start': '2024-01-08', 'total_volume': 11500},
            {'week_start': '2024-01-01', 'total_volume': 10000},
            {'week_start': '2023-12-25', 'total_volume': 9500},
        ]
        
        trend = _calculate_volume_trend(summaries)
        
        self.assertGreater(trend, 0.1)
    
    @patch('ai_coach.db_coach')
    def test_detect_signals_finds_plateau(self, mock_db):
        """Should detect deload signal when lifts plateau"""
        mock_db.get_weekly_training_summary.return_value = [
            {'week_start': '2024-01-15', 'total_volume': 10000, 'workouts_completed': 3},
            {'week_start': '2024-01-08', 'total_volume': 10000, 'workouts_completed': 3},
            {'week_start': '2024-01-01', 'total_volume': 10000, 'workouts_completed': 3},
            {'week_start': '2023-12-25', 'total_volume': 10000, 'workouts_completed': 3},
        ]
        mock_db.get_compound_lift_trends.return_value = {
            'Bench Press': [{'date': d, 'max_weight': 185} for d in ['2024-01-01', '2024-01-08', '2024-01-15']],
            'Squat': [{'date': d, 'max_weight': 225} for d in ['2024-01-01', '2024-01-08', '2024-01-15']],
            'Deadlift': [{'date': d, 'max_weight': 315} for d in ['2024-01-01', '2024-01-08', '2024-01-15']],
        }
        
        signals = detect_training_signals('user123')
        
        # Should have plateau signal in deload
        self.assertTrue(len(signals['deload']) > 0)
        plateau_signal = next((s for s in signals['deload'] if s.signal_name == 'plateau'), None)
        self.assertIsNotNone(plateau_signal)


class TestAdaptMyWeek(unittest.TestCase):
    """Tests for Feature 3: Adapt My Week"""
    
    @patch('ai_coach.db_coach')
    def test_should_show_adapt_when_behind(self, mock_db):
        """Should show adapt option when user is behind schedule"""
        mock_db.get_current_week_status.return_value = {
            'completed': [],
            'scheduled': [{'id': '1'}, {'id': '2'}, {'id': '3'}],
            'remaining': [{'id': '1'}, {'id': '2'}, {'id': '3'}],
            'days_remaining': 3,
            'day_of_week': 3,  # Thursday
        }
        
        should_show, reason = ai_coach.should_show_adapt_option('user123', 'cycle456')
        
        self.assertTrue(should_show)
        self.assertIn('missed', reason.lower())
    
    @patch('ai_coach.db_coach')
    def test_should_not_show_adapt_when_on_track(self, mock_db):
        """Should not show adapt when user is on track"""
        mock_db.get_current_week_status.return_value = {
            'completed': [{'id': '1'}, {'id': '2'}],
            'scheduled': [{'id': '1'}, {'id': '2'}, {'id': '3'}],
            'remaining': [{'id': '3'}],
            'days_remaining': 2,
            'day_of_week': 4,  # Friday
        }
        
        should_show, reason = ai_coach.should_show_adapt_option('user123', 'cycle456')
        
        self.assertFalse(should_show)


class TestDefaultPrescriptions(unittest.TestCase):
    """Tests for fallback prescriptions when AI is unavailable"""
    
    def test_default_deload_prescription(self):
        """Should return sensible default deload prescription"""
        signals = [
            TrainingSignal(
                signal_type=SignalType.DELOAD,
                signal_name='plateau',
                description='3 compound lifts stalled',
                confidence=0.8,
                data={'stalled_lifts': ['Bench', 'Squat', 'Deadlift']}
            )
        ]
        
        prescription = ai_coach._get_default_deload_prescription(signals)
        
        self.assertIn('title', prescription)
        self.assertIn('prescription', prescription)
        self.assertIn('3 sets', prescription['prescription'].lower())
    
    def test_default_progression_prescription(self):
        """Should return sensible default progression prescription"""
        signals = [
            TrainingSignal(
                signal_type=SignalType.PROGRESSION,
                signal_name='rep_ceiling',
                description='3 exercises at ceiling',
                confidence=0.85,
                data={'exercises': [
                    {'name': 'Bench Press', 'current_weight': 185},
                    {'name': 'Squat', 'current_weight': 225},
                ]}
            )
        ]
        
        prescription = ai_coach._get_default_progression_prescription(signals)
        
        self.assertIn('title', prescription)
        self.assertIn('exercises', prescription)
        # Should suggest +5 lbs
        self.assertEqual(prescription['exercises'][0]['suggested'], 190)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
