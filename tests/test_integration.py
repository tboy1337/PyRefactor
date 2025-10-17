"""Integration tests for PyRefactor."""

from pathlib import Path

from pyrefactor.analyzer import Analyzer
from pyrefactor.config import Config


class TestIntegration:
    """Integration tests."""

    def test_full_analysis_workflow(self, tmp_path: Path) -> None:
        """Test complete analysis workflow."""
        # Create a Python file with various issues
        file_path = tmp_path / "sample.py"
        file_path.write_text(
            """
def problematic_function(a, b, c, d, e, f, g, h):
    '''Function with multiple issues.'''
    result_str = ""
    var1 = 1
    var2 = 2
    var3 = 3
    var4 = 4
    var5 = 5
    var6 = 6
    var7 = 7
    var8 = 8
    var9 = 9
    var10 = 10
    var11 = 11
    var12 = 12
    var13 = 13
    var14 = 14
    var15 = 15
    var16 = 16

    if a:
        if b:
            if c:
                if d:
                    if e == True:
                        for item in items:
                            result_str += str(item)

    if x and y and z and w and q:
        pass

    for i in range(len(data)):
        print(data[i])

    return result_str
"""
        )

        # Analyze the file
        config = Config()
        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Verify issues were detected
        assert len(analysis.issues) > 0

        # Check for different types of issues
        rule_ids = {issue.rule_id for issue in analysis.issues}

        # Should have complexity issues
        assert any(rule_id.startswith("C") for rule_id in rule_ids)

        # Should have boolean logic issues
        assert any(rule_id.startswith("B") for rule_id in rule_ids)

        # Should have performance issues
        assert any(rule_id.startswith("P") for rule_id in rule_ids)

        # Should have loop issues
        assert any(rule_id.startswith("L") for rule_id in rule_ids)

    def test_multi_file_analysis(self, tmp_path: Path) -> None:
        """Test analyzing multiple files."""
        # Create multiple files
        (tmp_path / "file1.py").write_text(
            """
def simple1():
    return 1
"""
        )

        (tmp_path / "file2.py").write_text(
            """
def simple2():
    return 2
"""
        )

        code = "\n".join([f"    x = {i}" for i in range(60)])
        (tmp_path / "file3.py").write_text(f"def long_func():\n{code}\n    return x")

        # Analyze directory
        config = Config()
        analyzer = Analyzer(config)
        result = analyzer.analyze_directory(tmp_path)

        # Should analyze all files
        assert result.files_analyzed() == 3

        # At least one file should have issues
        assert result.files_with_issues() >= 1

    def test_real_world_scenario(self, tmp_path: Path) -> None:
        """Test a real-world-like scenario."""
        # Create a more realistic Python module
        file_path = tmp_path / "service.py"
        file_path.write_text(
            """
class UserService:
    def process_user_data(self, user_id, username, email, phone, address,
                         city, state, zip_code, country, preferences):
        '''Process user data with validation.'''
        result = []

        if len(username) > 0:
            if len(email) > 0:
                if user_id is not None:
                    if phone is not None:
                        if address is not None:
                            # Nested validation
                            result.append(username)

        # String building in loop
        output = ""
        for item in result:
            output += item + ","

        # Inefficient lookup
        for user in users:
            for role in roles:
                if user.id == role.user_id:
                    user.roles.append(role)

        return output

def duplicate_logic1():
    data = fetch_data()
    validated = validate(data)
    processed = process(validated)
    saved = save(processed)
    return saved

def duplicate_logic2():
    data = fetch_data()
    validated = validate(data)
    processed = process(validated)
    saved = save(processed)
    return saved
"""
        )

        # Analyze
        config = Config()
        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Should detect multiple issue types
        assert len(analysis.issues) > 0

        # Check severity distribution
        severities = {issue.severity for issue in analysis.issues}
        assert len(severities) > 1  # Should have multiple severity levels

    def test_disabled_detectors(self, tmp_path: Path) -> None:
        """Test that disabled detectors don't run."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            """
for i in range(len(items)):
    print(items[i])
"""
        )

        # Analyze with loops detector enabled
        config1 = Config()
        config1.loops.enabled = True
        analyzer1 = Analyzer(config1)
        analysis1 = analyzer1.analyze_file(file_path)

        # Should have loop issues
        loop_issues1 = [i for i in analysis1.issues if i.rule_id.startswith("L")]
        assert len(loop_issues1) > 0

        # Analyze with loops detector disabled
        config2 = Config()
        config2.loops.enabled = False
        analyzer2 = Analyzer(config2)
        analysis2 = analyzer2.analyze_file(file_path)

        # Should not have loop issues
        loop_issues2 = [i for i in analysis2.issues if i.rule_id.startswith("L")]
        assert len(loop_issues2) == 0

    def test_custom_thresholds(self, tmp_path: Path) -> None:
        """Test custom configuration thresholds."""
        file_path = tmp_path / "test.py"
        code = "\n".join([f"    x = {i}" for i in range(30)])
        file_path.write_text(f"def func():\n{code}\n    return x")

        # Default threshold (50 lines)
        config1 = Config()
        analyzer1 = Analyzer(config1)
        analysis1 = analyzer1.analyze_file(file_path)

        # Should not trigger (30 lines < 50)
        long_func_issues1 = [i for i in analysis1.issues if i.rule_id == "C001"]
        assert len(long_func_issues1) == 0

        # Custom threshold (20 lines)
        config2 = Config()
        config2.complexity.max_function_lines = 20
        analyzer2 = Analyzer(config2)
        analysis2 = analyzer2.analyze_file(file_path)

        # Should trigger (30 lines > 20)
        long_func_issues2 = [i for i in analysis2.issues if i.rule_id == "C001"]
        assert len(long_func_issues2) > 0
