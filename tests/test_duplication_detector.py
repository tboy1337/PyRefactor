"""Tests for duplication detector."""

import ast
from pathlib import Path

import pytest

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
        """Test detection of structurally identical code blocks in different functions."""
        source = """
def process_a(data):
    validated = validate(data)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result

def process_b(data):
    validated = validate(data)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert len(issues) >= 1
        assert any(issue.rule_id == "D001" for issue in issues)

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

        # Different classes with different methods should not trigger duplication
        assert len(issues) == 0

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

    def test_min_duplicate_lines_boundary(self) -> None:
        """Test duplication detection at min_duplicate_lines=2 boundary."""
        config = Config()
        config.duplication.min_duplicate_lines = 2
        source = """
def func1():
    x = 1
    return x

def func2():
    x = 1
    return x
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(config, "test.py", lines)
        issues = detector.analyze(tree)

        assert any(issue.rule_id == "D001" for issue in issues)

    def test_high_similarity_threshold_excludes_near_duplicates(self) -> None:
        """Test strict similarity threshold ignores loosely similar blocks."""
        config = Config()
        config.duplication.similarity_threshold = 1.0
        source = """
def func1():
    alpha = 1
    beta = 2
    gamma = 3
    delta = 4
    result = alpha + beta + gamma + delta
    return result

def func2():
    one = 1
    two = 2
    three = 3
    four = 4
    total = one + two + three + four
    return total
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(config, "test.py", lines)
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_disabled_via_analyzer(self, tmp_path: Path) -> None:
        """Test duplication detector disabled through analyzer config."""
        from pyrefactor.analyzer import Analyzer

        config = Config()
        config.duplication.enabled = False
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
        target = tmp_path / "dup.py"
        target.write_text(source, encoding="utf-8")

        result = Analyzer(config).analyze_file(target)
        assert not any(issue.rule_id == "D001" for issue in result.issues)

    def test_rule_specific_suppression(self, default_config: Config) -> None:
        """Test D001 respects rule-specific suppression comments."""
        source = """
def func1():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result

# pyrefactor: ignore D001
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

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_other_rule_suppression_does_not_suppress_d001(
        self, default_config: Config
    ) -> None:
        """Test R001 suppression does not suppress D001."""
        source = """
def func1():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result

# pyrefactor: ignore R001
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

        assert any(issue.rule_id == "D001" for issue in issues)

    def test_max_lines_analyzed_boundary(
        self, default_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test duplication detector only scans the first MAX_LINES_ANALYZED lines."""
        from pyrefactor.detectors.duplication import DuplicationDetector as DupDet

        max_lines = 50
        monkeypatch.setattr(DupDet, "MAX_LINES_ANALYZED", max_lines)
        filler = "\n".join(f"_line_{i} = {i}" for i in range(max_lines))
        duplicate_block = """
def func1():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    total = a + b + c + d + e
    return total

def func2():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    total = a + b + c + d + e
    return total
"""
        source = filler + "\n" + duplicate_block
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_max_block_size_boundary(
        self, default_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test blocks longer than MAX_BLOCK_SIZE are not compared."""
        from pyrefactor.detectors.duplication import DuplicationDetector as DupDet

        monkeypatch.setattr(DupDet, "MAX_BLOCK_SIZE", 4)
        duplicate_block = """
def func1():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    total = a + b + c + d + e + f + g
    return total

def func2():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    total = a + b + c + d + e + f + g
    return total
"""
        source = duplicate_block
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_max_blocks_stored_boundary(
        self, default_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test duplicate detection stops after MAX_BLOCKS_STORED unique blocks."""
        from pyrefactor.detectors.duplication import DuplicationDetector as DupDet

        monkeypatch.setattr(DupDet, "MAX_BLOCKS_STORED", 3)
        unique_blocks = "\n".join(f"""
def unique_{index}():
    x = {index}
    y = {index + 1}
    z = {index + 2}
    w = {index + 3}
    return x + y + z + w
""".strip() for index in range(10))
        duplicate_pair = """
def duplicate_a():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    return a + b + c + d + e

def duplicate_b():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    return a + b + c + d + e
"""
        source = unique_blocks + "\n" + duplicate_pair
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_tuple_literal_exclusion(self, default_config: Config) -> None:
        """Test tuple literals are excluded from duplication detection."""
        source = """
PAIR_A = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
)

PAIR_B = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
)
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "D001" for issue in issues)

    def test_async_function_docstring_exclusion(self, default_config: Config) -> None:
        """Test async function docstrings are excluded from duplication detection."""
        source = '''
async def worker_one():
    """Shared async worker documentation block."""
    return 1

async def worker_two():
    """Shared async worker documentation block."""
    return 2
'''
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert len(issues) == 0
