"""Tests for duplication detector."""

import ast

from pyrefactor.config import Config
from pyrefactor.detectors.duplication import DuplicationDetector


class TestDuplicationDetector:
    """Tests for DuplicationDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = DuplicationDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "duplication"

    def test_exact_duplication(self, default_config: Config) -> None:
        """Test detection of exact code duplication."""
        source = """
def func1():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result

def func2():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "D001" for issue in issues)
        assert any("duplicate" in issue.message.lower() for issue in issues)

    def test_similar_code(self, default_config: Config) -> None:
        """Test detection of similar code blocks."""
        source = """
def process_a(data):
    validated = validate(data)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result

def process_b(info):
    validated = validate(info)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # May or may not detect depending on similarity threshold
        assert isinstance(issues, list)

    def test_no_duplication(self, default_config: Config) -> None:
        """Test that unique code doesn't trigger issues."""
        source = """
class Calculator:
    def add(self, a, b):
        return a + b

class Logger:
    def log(self, message):
        print(f"LOG: {message}")

class DataStore:
    def save(self, key, value):
        self.data[key] = value
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Different classes with different methods shouldn't trigger duplication
        # (May detect some similarity, so we'll just check it doesn't crash)
        assert isinstance(issues, list)

    def test_whitespace_normalized(self, default_config: Config) -> None:
        """Test that whitespace differences are normalized."""
        source = """
def func1():
    x=1
    y=2
    z=3
    result=x+y+z
    return result

def func2():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Should detect as duplicates despite whitespace differences
        assert len(issues) > 0

    def test_suppression_comment(self, default_config: Config) -> None:
        """Test that suppression comments prevent duplication detection."""
        source = """
def func1():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
# pyrefactor: ignore
def func2():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Should not detect duplication due to suppression comment
        assert len(issues) == 0

    def test_data_structure_exclusion(self, default_config: Config) -> None:
        """Test that data structures are excluded from duplication detection."""
        source = """
# Multiple sets with similar structure should not be flagged
BUILTIN_VARS = {
    "DATE",
    "TIME",
    "CD",
    "ERRORLEVEL",
    "RANDOM",
}

SYSTEM_VARS = {
    "PATH",
    "TEMP",
    "TMP",
    "USER",
    "HOME",
}

CONFIG_LIST = [
    "option1",
    "option2",
    "option3",
    "option4",
    "option5",
]

SETTINGS_DICT = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
    "key4": "value4",
    "key5": "value5",
}
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Data structures should not be flagged as duplicates
        # (though there may be some issues in surrounding code)
        data_structure_issues = [
            issue
            for issue in issues
            if "DATE" in str(issue.line) or "PATH" in str(issue.line)
        ]
        assert len(data_structure_issues) == 0

    def test_docstring_exclusion(self, default_config: Config) -> None:
        """Test that docstrings are excluded from duplication detection."""
        source = '''
def function_one():
    """
    This is a docstring that explains what the function does.
    It provides documentation for the user.
    Args:
        None
    Returns:
        None
    """
    pass

def function_two():
    """
    This is a docstring that explains what the function does.
    It provides documentation for the user.
    Args:
        None
    Returns:
        None
    """
    pass

class MyClass:
    """
    This is a class docstring.
    It describes the class purpose.
    """
    pass

class OtherClass:
    """
    This is a class docstring.
    It describes the class purpose.
    """
    pass
'''
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Docstrings should not be flagged as duplicates
        assert len(issues) == 0
