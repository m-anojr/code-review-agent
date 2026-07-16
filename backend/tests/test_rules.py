from app.models import FileDiff, Hunk, Severity, Category
from app.rules.secrets import check_secrets
from app.rules.sql_injection import check_sql_injection
from app.rules.exceptions import check_exceptions


def _make_diff(filename: str, lines: list[str]) -> FileDiff:
    """Helper: create a FileDiff with a single hunk from added lines."""
    diff_lines = [f"+{line}" for line in lines]
    return FileDiff(
        filename=filename,
        hunks=[
            Hunk(old_start=0, old_count=0, new_start=1, new_count=len(lines), lines=diff_lines)
        ],
        is_new=True,
    )


class TestSecretDetection:
    def test_detects_aws_access_key(self):
        diff = _make_diff("config.py", ['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'])
        findings = check_secrets(diff)
        assert len(findings) >= 1
        assert findings[0].severity == Severity.CRITICAL
        assert findings[0].category == Category.SECURITY

    def test_detects_github_token(self):
        diff = _make_diff("deploy.py", ['token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"'])
        findings = check_secrets(diff)
        assert len(findings) >= 1

    def test_ignores_env_example(self):
        diff = _make_diff(".env.example", ['API_KEY = "sk-test-abc123def456ghi789"'])
        findings = check_secrets(diff)
        assert len(findings) == 0

    def test_no_false_positive_on_normal_code(self):
        diff = _make_diff("utils.py", ["x = 42", "name = 'hello'"])
        findings = check_secrets(diff)
        assert len(findings) == 0


class TestSqlInjection:
    def test_detects_fstring_query(self):
        diff = _make_diff("db.py", ['query = f"SELECT * FROM users WHERE id = {user_id}"'])
        findings = check_sql_injection(diff)
        assert len(findings) >= 1
        assert findings[0].severity == Severity.HIGH

    def test_detects_format_query(self):
        diff = _make_diff("db.py", ['"SELECT * FROM users WHERE name = \'{}\'".format(name)'])
        findings = check_sql_injection(diff)
        assert len(findings) >= 1

    def test_no_false_positive_on_parameterized(self):
        diff = _make_diff("db.py", ['cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))'])
        findings = check_sql_injection(diff)
        assert len(findings) == 0


class TestExceptionChecks:
    def test_detects_bare_except(self):
        diff = _make_diff("handler.py", ["try:", "    do_thing()", "except:", "    pass"])
        findings = check_exceptions(diff)
        assert len(findings) >= 1
        assert findings[0].severity == Severity.MEDIUM

    def test_detects_swallowed_exception(self):
        diff = _make_diff("handler.py", ["try:", "    do_thing()", "except Exception as e:", "    pass"])
        findings = check_exceptions(diff)
        assert len(findings) >= 1

    def test_no_false_positive_on_handled_exception(self):
        diff = _make_diff("handler.py", [
            "try:",
            "    do_thing()",
            "except ValueError as e:",
            "    logger.error(e)",
        ])
        findings = check_exceptions(diff)
        assert len(findings) == 0
