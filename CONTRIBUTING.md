# Contributing

Thanks for your interest in contributing to auto_dev! Please take a moment to review this document **before submitting a pull request.**

If you want to contribute but aren't sure where to start, you can create a [new discussion](https://github.com/8ball030/auto_dev/discussions) or open an issue.

## Get started

This guide is intended to help you get started with contributing. By following these steps, you will understand the development process and workflow.

- [Fork the repository](#fork-the-repository)
- [Install Python and Poetry](#install-python-and-poetry)
- [Install dependencies](#install-dependencies)
- [Build the project](#build-the-project)
- [Write documentation](#write-documentation)
- [Submit a pull request](#submit-a-pull-request)
- [That's it!](#thats-it)

<br>

---

<br>

## Fork the repository

To start contributing to the project, [create a fork](https://github.com/8ball030/auto_dev/fork) and clone it to your machine using `git clone`.

Or, use the [GitHub CLI](https://cli.github.com) to create a fork and clone it in one command:

```bash
gh repo fork 8ball030/auto_dev --clone
```

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## Install Python and Poetry

auto_dev uses [Poetry](https://python-poetry.org/) for dependency management. You need to install **Python 3.9 or higher** and **Poetry < 2.0**.

You can run the following commands in your terminal to check your local Python and Poetry versions:

```bash
python --version
poetry --version
```

If the versions are not correct or you don't have Python or Poetry installed:

- Install Python from the [official website](https://python.org) or using [pyenv](https://github.com/pyenv/pyenv)
- Install [Poetry](https://python-poetry.org/docs/#installation)

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## Install dependencies

In the root directory, run the following command to install the project's dependencies:

```bash
poetry install
```

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## Build the project

In the root directory, run the build command:

```bash
pip install -e .
```

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>


When adding new features or fixing bugs, it's important to add test cases in /tests to cover any new or updated behavior.

### Code Quality Checks

Before pushing your changes, make sure to run the following quality checks:

```bash
# Format code
make fmt

# Run linting checks
make lint

# Run tests
make test
```

These commands will ensure your code:
- Follows the project's formatting standards
- Passes all linting rules
- Successfully runs all tests

Running these checks locally before pushing will help catch issues early and speed up the review process.

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## Write documentation

auto_dev uses [MkDocs](https://www.mkdocs.org/) with Material theme for the documentation website. To start the docs website in dev mode, run:

```bash
poetry run mkdocs serve
```

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## Submit a pull request

When you're ready to submit a pull request, follow these naming conventions:

- Pull request titles use the [imperative mood](https://en.wikipedia.org/wiki/Imperative_mood) (e.g., `Add something`, `Fix something`).
- Commit messages should be clear and descriptive.

When you submit a pull request, GitHub Actions will automatically lint, build, and test your changes. If you see an ❌, it's most likely a problem with your code. Inspect the logs through the GitHub Actions UI to find the cause.

<div align="right">
  <a href="#get-started">&uarr; back to top</a></b>
</div>

## That's it!

If you still have questions, please create a [new issue](https://github.com/8ball030/auto_dev/issues).