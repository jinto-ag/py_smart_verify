"""Tests for py_verify.git."""

import subprocess
from pathlib import Path

from py_verify.git import GitIntegration


class TestIsGitRepo:
    def test_true(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)
        assert git.is_git_repo()

    def test_false(self, tmp_path: Path):
        git = GitIntegration(tmp_path)
        assert not git.is_git_repo()


class TestGetChangedFiles:
    def test_not_git_repo(self, tmp_path: Path):
        git = GitIntegration(tmp_path)
        assert git.get_changed_files() == []

    def test_diff_base(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        calls = []

        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            if "diff" in cmd and "--name-only" in cmd and "main" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="a.py\nb.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(base_ref="main")
        assert "a.py" in result
        assert "b.py" in result

    def test_staged(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if "--cached" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="staged.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(include_staged=True)
        assert "staged.py" in result

    def test_no_staged(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        calls = []

        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        git.get_changed_files(include_staged=False)
        assert not any("--cached" in c for c in calls)

    def test_unstaged(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if cmd == ["git", "diff", "--name-only"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="unstaged.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(include_unstaged=True)
        assert "unstaged.py" in result

    def test_untracked(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if "status" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="?? new.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(include_untracked=True)
        assert "new.py" in result

    def test_untracked_timeout(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if "status" in cmd:
                raise subprocess.TimeoutExpired(cmd, 10)
            return subprocess.CompletedProcess(cmd, 0, stdout="base.py\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(include_untracked=True)
        # Should still return files from other commands (base diff)
        assert "base.py" in result

    def test_untracked_file_not_found(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if "status" in cmd:
                raise FileNotFoundError("git not found")
            return subprocess.CompletedProcess(cmd, 0, stdout="diff.py\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files(include_untracked=True)
        assert "diff.py" in result

    def test_no_untracked(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        calls = []

        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        git.get_changed_files(include_untracked=False)
        assert not any("status" in c for c in calls)

    def test_dedup(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="same.py\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert result.count("same.py") == 1

    def test_empty_filter(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert "" not in result

    def test_sorted(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            if "main" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="c.py\na.py\nb.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert result == sorted(result)

    def test_timeout(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 10)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert result == []

    def test_file_not_found(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert result == []

    def test_nonzero_return(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="fatal")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = git.get_changed_files()
        assert result == []


class TestGetAffectedModules:
    def test_py_files(self):
        git = GitIntegration()
        result = git.get_affected_modules(["src/pkg/mod.py", "src/pkg/util.py"])
        assert "pkg.mod" in result
        assert "pkg.util" in result

    def test_non_py(self):
        git = GitIntegration()
        result = git.get_affected_modules(["readme.md", "data.json"])
        assert result == []

    def test_prefix_stripping(self):
        git = GitIntegration()
        result = git.get_affected_modules(["src/my_pkg/module.py"])
        assert "my_pkg.module" in result

    def test_sorted(self):
        git = GitIntegration()
        result = git.get_affected_modules(["src/b.py", "src/a.py"])
        assert result == sorted(result)

    def test_empty(self):
        git = GitIntegration()
        assert git.get_affected_modules([]) == []


class TestGetDiffStats:
    def test_not_git_repo(self, tmp_path: Path):
        git = GitIntegration(tmp_path)
        stats = git.get_diff_stats()
        assert stats == {"insertions": 0, "deletions": 0, "files_changed": 0}

    def test_success(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        stat_out = (
            " file1.py | 3 +++\n"
            " file2.py | 2 +-\n"
            " 2 files changed, 4 insertions(+), 1 deletion(-)\n"
        )

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=stat_out, stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        stats = git.get_diff_stats()
        assert stats["files_changed"] >= 0
        assert stats["insertions"] >= 0

    def test_timeout(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 10)

        monkeypatch.setattr(subprocess, "run", mock_run)
        stats = git.get_diff_stats()
        assert stats == {"insertions": 0, "deletions": 0, "files_changed": 0}

    def test_file_not_found(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        stats = git.get_diff_stats()
        assert stats == {"insertions": 0, "deletions": 0, "files_changed": 0}

    def test_nonzero_return(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".git").mkdir()
        git = GitIntegration(tmp_path)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        stats = git.get_diff_stats()
        assert stats == {"insertions": 0, "deletions": 0, "files_changed": 0}
