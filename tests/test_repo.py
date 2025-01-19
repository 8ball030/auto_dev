"""Tests for the click cli."""

import subprocess
from pathlib import Path

import toml
from aea.cli.utils.config import get_default_author_from_cli_config

from auto_dev.utils import change_dir


class BaseTestRepo:
    """Test scaffolding new repository."""

    repo_name = "dummy"
    type_of_repo: str
    make_commands: tuple[str]

    @property
    def cli_args(self):
        """CLI arguments."""
        return ["adev", "repo", "scaffold", self.repo_name, "-t", self.type_of_repo]

    @property
    def parent_dir(self):
        """Parent directory of newly scaffolded repo."""
        return Path.cwd()

    @property
    def repo_path(self):
        """Path of newly scaffolded repo."""
        return self.parent_dir / self.repo_name

    def test_repo_new(self, cli_runner, test_clean_filesystem):
        """Test the format command works with the current package."""

        assert test_clean_filesystem
        runner = cli_runner(self.cli_args)
        result = runner.execute()
        assert result, runner.output
        assert self.repo_path.exists(), f"Repository directory was not created: {self.repo_path}"
        assert (self.repo_path / ".git").exists()

    def test_repo_new_fail(self, cli_runner, test_filesystem):
        """Test the format command works with the current package."""

        assert test_filesystem
        self.repo_path.mkdir()
        runner = cli_runner(self.cli_args)
        result = runner.execute()
        assert runner.return_code == 1, result.output

    def test_makefile(self, cli_runner, test_clean_filesystem):
        """Test scaffolding of Makefile."""
        assert test_clean_filesystem

        runner = cli_runner(self.cli_args)
        result = runner.execute(self.cli_args)
        assert result, (runner.stdout, "\n".join(runner.stderr))
        makefile = self.repo_path / "Makefile"
        assert makefile.exists(), result.output
        assert makefile.read_text(encoding="utf-8")
        assert self.repo_path.exists()

    def test_make_command_executes(self, cli_runner, test_clean_filesystem):
        """Test that the make command can execute properly."""
        error_messages = {}
        assert test_clean_filesystem

        # Ensure the repository is created before changing directory
        runner = cli_runner(self.cli_args)
        result = runner.execute()
        assert result, runner.output
        assert self.repo_path.exists(), f"Repository directory was not created: {self.repo_path}"

        with change_dir(self.repo_path):
            for command in self.make_commands:
                result = subprocess.run(
                    f"make {command}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if runner.return_code != 0:
                    error_messages[command] = runner.stderr
        assert not error_messages


class TestRepoPython(BaseTestRepo):
    """Test scaffolding new python repository."""

    type_of_repo = "python"
    make_commands = "fmt", "lint", "test"


class TestRepoAutonomy(BaseTestRepo):
    """Test scaffolding new autonomy repository."""

    author = get_default_author_from_cli_config()
    type_of_repo = "autonomy"
    make_commands = "fmt", "test", "lint", "hashes"

    def test_gitignore(self, cli_runner, test_clean_filesystem):
        """Test the .gitignore works as expected."""

        assert test_clean_filesystem
        runner = cli_runner(self.cli_args)
        result = runner.execute()
        assert runner.return_code == 0, runner.output

        packages_folder = self.repo_path / "packages"
        author_packages = packages_folder / self.author
        author_packages.mkdir(parents=True)

        # create files that should be ignored in the authors folder
        for folder in ("protocols", "connections", "skills", "agents", "services"):
            subfolder = author_packages / folder
            subfolder.mkdir()
            (subfolder / "keys.json").write_text("SECRET")
            (subfolder / "ethereum_private_key.txt").write_text("SECRET")
            (subfolder / "my_private_keys").write_text("SECRET")
            (subfolder / "__pycache__").mkdir()
            (subfolder / "__pycache__" / "cachefile").write_text("cache data")

        with change_dir(self.repo_path):
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
            assert result.returncode == 0

            # any other file created in the author's own package directory should be detected
            (author_packages / "some_other_file").write_text("to_be_committed")
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
            assert result.returncode == 0
            assert "packages" in result.stdout

    def test_run_single_agent(self, cli_runner, test_clean_filesystem):
        """Test the scripts/run_single_agent.sh is generated."""

        assert test_clean_filesystem
        runner = cli_runner(self.cli_args)
        result = runner.execute()

        assert runner.return_code == 0, result.output
        expected_path = self.repo_path / "scripts" / "run_single_agent.sh"
        assert expected_path.exists()

    def test_pyproject_versions(
        self,
    ):
        """Test the pyproject.toml versions are updated."""

        # We read in the pyproject.toml file and check the versions
        current_pyproject = self.parent_dir / "pyproject.toml"
        repo_pyproject = (
            self.parent_dir / "auto_dev" / "data" / "repo" / "templates" / "autonomy" / "pyproject.toml.template"
        )  # pylint: disable=line-too-long

        auto_dev_deps = toml.loads(current_pyproject.read_text())["tool"]["poetry"]["dependencies"]
        repo_deps = toml.loads(
            repo_pyproject.read_text().format(
                project_name=self.repo_name,
                author=self.author,
            )
        )["tool"]["poetry"]["dependencies"]

        errors = []
        for key in auto_dev_deps:
            if key not in repo_deps:
                continue
            if auto_dev_deps[key] == repo_deps[key]:
                continue
            val = f"{key} New: {auto_dev_deps[key]} old: {repo_deps[key]}"
            errors.append(val)
        assert not errors, errors
