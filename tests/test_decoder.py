"""Unit tests for Solution Decoding, Validation, and State Classification."""

import unittest
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
)
from optimization.emergency import EmergencyConstraints
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    validate_solution,
    decode_solution,
)


class TestDecoderAndValidation(unittest.TestCase):
    """Test suite for Solution Decoding, Constraint Validation, and Signal Plan Generation."""

    def test_valid_signal_plans_decoding(self):
        """Verify clean decoding of valid 12-bit solutions into signal plans."""
        # I1: 15s, I2: 30s, I3: 45s, I4: 30s
        x = [
            1, 0, 0,  # I1: 15s
            0, 1, 0,  # I2: 30s
            0, 0, 1,  # I3: 45s
            0, 1, 0,  # I4: 30s
        ]
        self.assertTrue(is_valid_onehot(x))
        valid, err = validate_solution(x)
        self.assertTrue(valid)
        self.assertIsNone(err)

        plan = decode_solution(x)
        self.assertEqual(plan, {"I1": 15, "I2": 30, "I3": 45, "I4": 30})

    def test_all_zeros_rejected(self):
        """Verify all zeros (0 active durations) is rejected with clear error."""
        x = [0] * NUM_VARIABLES
        self.assertFalse(is_valid_onehot(x))
        valid, err = validate_solution(x)
        self.assertFalse(valid)
        self.assertIn("one-hot constraint", err)

        with self.assertRaises(ValueError):
            decode_solution(x)

    def test_all_ones_rejected(self):
        """Verify all ones (3 active durations per intersection) is rejected."""
        x = [1] * NUM_VARIABLES
        self.assertFalse(is_valid_onehot(x))
        valid, err = validate_solution(x)
        self.assertFalse(valid)
        with self.assertRaises(ValueError):
            decode_solution(x)

    def test_multiple_active_at_one_intersection_rejected(self):
        """Verify state with 2 active choices at one intersection is rejected."""
        x = [
            1, 1, 0,  # I1: 2 active choices (invalid)
            0, 1, 0,  # I2: valid
            0, 0, 1,  # I3: valid
            0, 1, 0,  # I4: valid
        ]
        self.assertFalse(is_valid_onehot(x))
        valid, err = validate_solution(x)
        self.assertFalse(valid)
        self.assertIn("I1", err)
        with self.assertRaises(ValueError):
            decode_solution(x)

    def test_zero_active_at_one_intersection_rejected(self):
        """Verify state with 0 active choices at one intersection is rejected."""
        x = [
            0, 0, 0,  # I1: 0 active choices (invalid)
            0, 1, 0,  # I2: valid
            0, 0, 1,  # I3: valid
            0, 1, 0,  # I4: valid
        ]
        self.assertFalse(is_valid_onehot(x))
        valid, err = validate_solution(x)
        self.assertFalse(valid)
        self.assertIn("I1", err)
        with self.assertRaises(ValueError):
            decode_solution(x)

    def test_invalid_length_or_values_rejected(self):
        """Verify vectors with incorrect length or non-binary entries are rejected."""
        with self.assertRaises(ValueError):
            decode_solution([1, 0, 0])  # length 3 instead of 12

        with self.assertRaises(ValueError):
            decode_solution([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0])  # non-binary '2'

    def test_emergency_compliance_validation(self):
        """Verify validate_solution and is_valid_emergency check corridor compliance."""
        em = EmergencyConstraints(route=["I1", "I2", "I4"], forced_duration=45)

        # Compliant state: I1->45s, I2->45s, I3->15s, I4->45s
        x_comp = [
            0, 0, 1,  # I1: 45s (compliant)
            0, 0, 1,  # I2: 45s (compliant)
            1, 0, 0,  # I3: 15s
            0, 0, 1,  # I4: 45s (compliant)
        ]
        self.assertTrue(is_valid_emergency(x_comp, em))
        valid_comp, err_comp = validate_solution(x_comp, em)
        self.assertTrue(valid_comp)
        self.assertIsNone(err_comp)

        # Violating state: I2 selects 30s instead of 45s
        x_viol = [
            0, 0, 1,  # I1: 45s
            0, 1, 0,  # I2: 30s (VIOLATION)
            1, 0, 0,  # I3: 15s
            0, 0, 1,  # I4: 45s
        ]
        self.assertFalse(is_valid_emergency(x_viol, em))
        valid_viol, err_viol = validate_solution(x_viol, em)
        self.assertFalse(valid_viol)
        self.assertIn("Emergency route intersection 'I2'", err_viol)


if __name__ == "__main__":
    unittest.main()
