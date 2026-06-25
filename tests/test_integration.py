"""Integration tests for PyRefactor."""

from pathlib import Path

import pytest

from pyrefactor.analyzer import Analyzer
from pyrefactor.config import Config


@pytest.mark.integration
class TestIntegration:
    """Integration tests."""

    def test_full_analysis_workflow(self, tmp_path: Path) -> None:
        """Test complete analysis workflow."""
        # Create a Python file with various issues
        file_path = tmp_path / "sample.py"
        file_path.write_text("""
data = {"key": "value"}

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
                            result_str += str(item)
                            result_str += str(item)
                            cached = expensive_compute(item)
                            other = expensive_compute(item)
                            total = expensive_compute(item)

    if x and y and z and w and q:
        pass

    for i in range(len(data)):
        print(data[i])

    if "key" in data:
        value = data["key"]

    f = open("output.txt")
    f.write(result_str)

    if check():
        return result_str
    else:
        return None

    return result_str

def duplicate_a():
    x = 1
    y = 2
    z = x + y
    w = z * 2
    return w

def duplicate_b():
    x = 1
    y = 2
    z = x + y
    w = z * 2
    return w
""")

        # Analyze the file
        config = Config()
        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Verify issues were detected
        assert len(analysis.issues) > 0

        rule_ids = {issue.rule_id for issue in analysis.issues}
        expected_rules = {
            "B001",
            "C003",
            "C004",
            "C005",
            "D001",
            "L001",
            "P001",
            "P007",
            "R001",
            "R002",
            "R015",
        }
        assert expected_rules.issubset(rule_ids)

    def test_multi_file_analysis(self, tmp_path: Path) -> None:
        """Test analyzing multiple files."""
        # Create multiple files
        (tmp_path / "file1.py").write_text("""
def simple1():
    return 1
""")

        (tmp_path / "file2.py").write_text("""
def simple2():
    return 2
""")

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

        file3_analysis = next(
            analysis
            for analysis in result.file_analyses
            if analysis.file_path.endswith("file3.py")
        )
        assert any(issue.rule_id == "C001" for issue in file3_analysis.issues)

    def test_real_world_scenario(self, tmp_path: Path) -> None:
        """Test a real-world-like scenario."""
        # Create a more realistic Python module
        file_path = tmp_path / "service.py"
        file_path.write_text("""
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
""")

        # Analyze
        config = Config()
        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Should detect multiple issue types
        rule_ids = {issue.rule_id for issue in analysis.issues}
        expected_rules = {"P001", "P005", "P006", "C002", "D001"}
        assert expected_rules & rule_ids

        # Check severity distribution
        severities = {issue.severity for issue in analysis.issues}
        assert len(severities) > 1  # Should have multiple severity levels

    def test_disabled_detectors(self, tmp_path: Path) -> None:
        """Test that disabled detectors don't run."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""
for i in range(len(items)):
    print(items[i])
""")

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

    @pytest.mark.parametrize(
        ("detector_attr", "rule_prefix", "sample_code"),
        [
            (
                "boolean_logic",
                "B",
                "if a and b and c and d and e:\n    pass\n",
            ),
            (
                "context_manager",
                "R001",
                "f = open('file.txt')\n",
            ),
            (
                "control_flow",
                "R00",
                "def f():\n    if x:\n        return 1\n    else:\n        return 0\n",
            ),
            (
                "comparisons",
                "R01",
                "if x == None:\n    pass\n",
            ),
            (
                "dict_operations",
                "R0",
                "if key in my_dict:\n    value = my_dict[key]\nelse:\n    value = default\n",
            ),
            (
                "complexity",
                "C",
                "def f(a, b, c, d, e, f, g, h):\n    return a + b\n",
            ),
            (
                "performance",
                "P",
                "result_str = ''\nfor item in items:\n    result_str += item\n    result_str += item\n    result_str += item\n",
            ),
            (
                "duplication",
                "D",
                "def func1():\n"
                "    x = 1\n"
                "    y = 2\n"
                "    z = 3\n"
                "    result = x + y + z\n"
                "    return result\n"
                "\n"
                "def func2():\n"
                "    x = 1\n"
                "    y = 2\n"
                "    z = 3\n"
                "    result = x + y + z\n"
                "    return result\n",
            ),
            (
                "loops",
                "L",
                "for i in range(len(items)):\n    print(items[i])\n",
            ),
        ],
    )
    def test_disabled_detector_produces_no_issues(
        self,
        tmp_path: Path,
        detector_attr: str,
        rule_prefix: str,
        sample_code: str,
    ) -> None:
        """Test each detector can be disabled via config."""
        file_path = tmp_path / "sample.py"
        file_path.write_text(sample_code, encoding="utf-8")

        enabled_config = Config()
        enabled_analysis = Analyzer(enabled_config).analyze_file(file_path)
        enabled_rules = [
            issue.rule_id
            for issue in enabled_analysis.issues
            if issue.rule_id.startswith(rule_prefix)
        ]
        assert enabled_rules

        disabled_config = Config()
        getattr(disabled_config, detector_attr).enabled = False
        disabled_analysis = Analyzer(disabled_config).analyze_file(file_path)
        disabled_rules = [
            issue.rule_id
            for issue in disabled_analysis.issues
            if issue.rule_id.startswith(rule_prefix)
        ]
        assert not disabled_rules

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

    def test_issues_include_code_snippets(self, tmp_path: Path) -> None:
        """Test analyzed issues include source code snippets."""
        from io import StringIO

        from pyrefactor.reporter import ConsoleReporter

        file_path = tmp_path / "snippet.py"
        file_path.write_text("if x == True:\n    pass\n")

        analyzer = Analyzer(Config())
        analysis = analyzer.analyze_file(file_path)

        assert any(issue.code_snippet for issue in analysis.issues)

        output = StringIO()
        reporter = ConsoleReporter(output=output)
        result = analyzer.analyze_files([file_path])
        reporter.report(result)

        assert "if x == True:" in output.getvalue()
