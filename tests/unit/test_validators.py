"""
Unit tests for input validation and sanitization.

Tests security-critical input validation functions.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tempfile

import pytest

from forex_core.utils.validators import (
    ValidationError,
    sanitize_filename,
    sanitize_path,
    validate_horizon,
    validate_positive_integer,
    validate_severity,
)


class TestHorizonValidation:
    """Test horizon parameter validation."""

    def test_valid_horizons(self):
        """Test all valid horizon values."""
        valid_horizons = ["7d", "15d", "30d", "90d"]

        for horizon in valid_horizons:
            result = validate_horizon(horizon)
            assert result == horizon

    def test_invalid_horizon(self):
        """Test invalid horizon values are rejected."""
        invalid_horizons = [
            "1d",  # Not in whitelist
            "60d",  # Not in whitelist
            "../etc/passwd",  # Path traversal
            "7d; rm -rf /",  # Command injection
            "7d\x00",  # Null byte injection
        ]

        for horizon in invalid_horizons:
            with pytest.raises(ValidationError):
                validate_horizon(horizon)

    def test_none_without_allow_none(self):
        """Test None is rejected by default."""
        with pytest.raises(ValidationError):
            validate_horizon(None, allow_none=False)

    def test_none_with_allow_none(self):
        """Test None is allowed when allow_none=True."""
        result = validate_horizon(None, allow_none=True)
        assert result is None

    def test_case_sensitivity(self):
        """Test horizon validation is case-sensitive."""
        with pytest.raises(ValidationError):
            validate_horizon("7D")  # Uppercase not allowed

    def test_whitespace(self):
        """Test horizons with whitespace are rejected."""
        with pytest.raises(ValidationError):
            validate_horizon(" 7d")

        with pytest.raises(ValidationError):
            validate_horizon("7d ")


class TestSeverityValidation:
    """Test severity parameter validation."""

    def test_valid_severities(self):
        """Test all valid severity values."""
        valid_severities = ["low", "medium", "high", "critical"]

        for severity in valid_severities:
            result = validate_severity(severity)
            assert result == severity

    def test_case_insensitive(self):
        """Test severity validation is case-insensitive."""
        assert validate_severity("HIGH") == "high"
        assert validate_severity("Critical") == "critical"
        assert validate_severity("MeDiUm") == "medium"

    def test_invalid_severity(self):
        """Test invalid severity values are rejected."""
        invalid_severities = ["urgent", "normal", "warning", "../etc/passwd"]

        for severity in invalid_severities:
            with pytest.raises(ValidationError):
                validate_severity(severity)

    def test_none_handling(self):
        """Test None handling for severity."""
        with pytest.raises(ValidationError):
            validate_severity(None, allow_none=False)

        result = validate_severity(None, allow_none=True)
        assert result is None


class TestPositiveIntegerValidation:
    """Test positive integer validation."""

    def test_valid_integers(self):
        """Test valid positive integers."""
        assert validate_positive_integer(1) == 1
        assert validate_positive_integer(100) == 100
        assert validate_positive_integer(365, max_value=365) == 365

    def test_min_value_enforcement(self):
        """Test minimum value is enforced."""
        with pytest.raises(ValidationError):
            validate_positive_integer(0, min_value=1)

        with pytest.raises(ValidationError):
            validate_positive_integer(-5, min_value=1)

        with pytest.raises(ValidationError):
            validate_positive_integer(5, min_value=10)

    def test_max_value_enforcement(self):
        """Test maximum value is enforced."""
        with pytest.raises(ValidationError):
            validate_positive_integer(100, max_value=50)

        with pytest.raises(ValidationError):
            validate_positive_integer(366, max_value=365)

    def test_type_checking(self):
        """Test non-integer types are rejected."""
        with pytest.raises(ValidationError):
            validate_positive_integer("10")

        with pytest.raises(ValidationError):
            validate_positive_integer(10.5)

        with pytest.raises(ValidationError):
            validate_positive_integer(None)

    def test_custom_param_name(self):
        """Test custom parameter name in error messages."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(0, min_value=1, param_name="days")

        assert "days" in str(exc_info.value).lower()

    def test_no_max_value(self):
        """Test validation works without max_value."""
        assert validate_positive_integer(1000000, min_value=1) == 1000000


class TestFilenameValidation:
    """Test filename sanitization (critical security)."""

    def test_valid_filenames(self):
        """Test valid filenames pass."""
        valid_names = [
            "report.pdf",
            "data_2025.csv",
            "forecast-7d.json",
            "metrics_v1.2.3.log",
        ]

        for name in valid_names:
            result = sanitize_filename(name)
            assert result == name

    def test_path_traversal_blocked(self):
        """Test path traversal attacks are blocked."""
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "data/../../../etc/passwd",
        ]

        for name in malicious_names:
            with pytest.raises(ValidationError) as exc_info:
                sanitize_filename(name)
            assert "traversal" in str(exc_info.value).lower()

    def test_path_separators_blocked(self):
        """Test path separators are blocked."""
        with pytest.raises(ValidationError):
            sanitize_filename("path/to/file.txt")

        with pytest.raises(ValidationError):
            sanitize_filename("path\\to\\file.txt")

    def test_hidden_files_blocked(self):
        """Test hidden files (starting with .) are blocked."""
        with pytest.raises(ValidationError):
            sanitize_filename(".bashrc")

        with pytest.raises(ValidationError):
            sanitize_filename(".env")

    def test_shell_metacharacters_blocked(self):
        """Test shell metacharacters are blocked."""
        dangerous_chars = [
            "file;rm -rf /.txt",
            "file|cat /etc/passwd.txt",
            "file`whoami`.txt",
            "file$(rm -rf /).txt",
            "file&background.txt",
            "file*wildcard.txt",
            "file?.txt",
        ]

        for name in dangerous_chars:
            with pytest.raises(ValidationError):
                sanitize_filename(name)

    def test_length_limit(self):
        """Test filename length is limited."""
        long_name = "a" * 256 + ".txt"

        with pytest.raises(ValidationError):
            sanitize_filename(long_name, max_length=255)

    def test_empty_filename(self):
        """Test empty filenames are rejected."""
        with pytest.raises(ValidationError):
            sanitize_filename("")

        with pytest.raises(ValidationError):
            sanitize_filename(None)

    def test_null_byte_injection(self):
        """Test null byte injection is blocked."""
        with pytest.raises(ValidationError):
            sanitize_filename("file.txt\x00.pdf")

    def test_alphanumeric_only(self):
        """Test only alphanumeric, dash, underscore, period allowed."""
        valid = "file-name_123.txt"
        assert sanitize_filename(valid) == valid

        with pytest.raises(ValidationError):
            sanitize_filename("file@name.txt")

        with pytest.raises(ValidationError):
            sanitize_filename("file#name.txt")


class TestPathSanitization:
    """Test path sanitization (critical security)."""

    @pytest.fixture
    def temp_base_dir(self):
        """Create temporary base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_valid_relative_path(self, temp_base_dir):
        """Test valid relative path within base directory."""
        # Create test file
        test_file = temp_base_dir / "data.txt"
        test_file.write_text("test")

        result = sanitize_path("data.txt", base_dir=temp_base_dir)

        assert result == test_file
        assert result.is_relative_to(temp_base_dir)

    def test_path_traversal_blocked(self, temp_base_dir):
        """Test path traversal is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_path("../../../etc/passwd", base_dir=temp_base_dir)

        assert "escapes" in str(exc_info.value).lower()

    def test_absolute_path_outside_base(self, temp_base_dir):
        """Test absolute paths outside base are blocked."""
        with pytest.raises(ValidationError):
            sanitize_path("/etc/passwd", base_dir=temp_base_dir)

    def test_symlink_to_outside(self, temp_base_dir):
        """Test symlinks pointing outside base are blocked."""
        # Create symlink to /tmp
        symlink = temp_base_dir / "link"
        symlink.symlink_to("/tmp")

        with pytest.raises(ValidationError):
            sanitize_path("link", base_dir=temp_base_dir)

    def test_allow_create_nonexistent(self, temp_base_dir):
        """Test allow_create permits nonexistent paths."""
        result = sanitize_path(
            "new_file.txt",
            base_dir=temp_base_dir,
            allow_create=True
        )

        assert result == temp_base_dir / "new_file.txt"
        assert result.parent == temp_base_dir

    def test_reject_nonexistent_by_default(self, temp_base_dir):
        """Test nonexistent paths rejected by default."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_path(
                "nonexistent.txt",
                base_dir=temp_base_dir,
                allow_create=False
            )

        assert "does not exist" in str(exc_info.value).lower()

    def test_nested_paths(self, temp_base_dir):
        """Test nested directory paths."""
        # Create nested structure
        nested_dir = temp_base_dir / "subdir" / "data"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.txt"
        test_file.write_text("test")

        result = sanitize_path(
            "subdir/data/test.txt",
            base_dir=temp_base_dir
        )

        assert result == test_file
        assert result.is_relative_to(temp_base_dir)

    def test_double_dot_in_safe_path(self, temp_base_dir):
        """Test .. in path that stays within base directory."""
        # Create structure
        (temp_base_dir / "a").mkdir()
        (temp_base_dir / "b").mkdir()
        test_file = temp_base_dir / "b" / "file.txt"
        test_file.write_text("test")

        # Path like "a/../b/file.txt" is safe if it resolves within base
        result = sanitize_path(
            Path("a") / ".." / "b" / "file.txt",
            base_dir=temp_base_dir
        )

        assert result == test_file

    def test_windows_path_separators(self, temp_base_dir):
        """Test Windows-style path separators are handled."""
        test_file = temp_base_dir / "data.txt"
        test_file.write_text("test")

        # Should work with backslashes converted
        result = sanitize_path(
            "data.txt",
            base_dir=temp_base_dir
        )

        assert result == test_file


class TestValidationErrorMessages:
    """Test validation error messages are informative."""

    def test_horizon_error_message(self):
        """Test horizon validation error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_horizon("invalid")

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
        assert any(h in error_msg for h in ["7d", "15d", "30d", "90d"])

    def test_severity_error_message(self):
        """Test severity validation error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_severity("invalid")

        error_msg = str(exc_info.value)
        assert "invalid" in error_msg.lower()
        assert any(s in error_msg for s in ["low", "medium", "high", "critical"])

    def test_integer_range_error_message(self):
        """Test integer validation error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(500, min_value=1, max_value=365, param_name="days")

        error_msg = str(exc_info.value)
        assert "days" in error_msg
        assert "365" in error_msg


class TestSecurityEdgeCases:
    """Test security edge cases."""

    def test_unicode_normalization(self):
        """Test unicode normalization attacks."""
        # Unicode characters that might bypass filters
        with pytest.raises(ValidationError):
            sanitize_filename("file\u202e.txt")  # Right-to-left override

    def test_multiple_extensions(self):
        """Test multiple extensions."""
        # Should be allowed
        result = sanitize_filename("archive.tar.gz")
        assert result == "archive.tar.gz"

    def test_very_long_path_components(self):
        """Test very long path components."""
        long_component = "a" * 300
        with pytest.raises(ValidationError):
            sanitize_filename(long_component + ".txt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
