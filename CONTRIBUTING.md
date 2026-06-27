# Contributing to RedactAI

First off, thank you for considering contributing to RedactAI! It's people like you that make open source such a great community to learn, inspire, and create.

This document serves as the hub for all things related to contributing to the project.

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Environment](#development-environment)
4. [Branching Strategy](#branching-strategy)
5. [Commit Message Conventions](#commit-message-conventions)
6. [Pull Request Process](#pull-request-process)
7. [Semantic Versioning Policy](#semantic-versioning-policy)
8. [Release Checklist](#release-checklist)

---

## Code of Conduct
By participating in this project, you are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior to the repository maintainers.

## Getting Started
- If you find a bug, please check the [Issue Tracker](https://github.com/snahadhar18/Redact-AI/issues) first to see if it's already reported.
- If it's a new bug, submit an issue using the Bug Report template.
- For feature requests, submit an issue using the Feature Request template.
- Join the conversation in our [GitHub Discussions](https://github.com/snahadhar18/Redact-AI/discussions).

## Development Environment

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Git
- Docker (optional, for gateway testing)

### Setup
1. Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Redact-AI.git
   cd Redact-AI
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the project in editable mode with all development dependencies:
   ```bash
   pip install -e ".[dev,api,json,ai,scale]"
   ```

### Running Tests and Linters
We enforce strict linting and type checking. Before committing, ensure the following commands pass:

```bash
# Run unit and integration tests
pytest tests/

# Run the linter
ruff check src/ tests/

# Run type checking
mypy src/
```

## Branching Strategy
We use a lightweight GitHub Flow strategy:
- `main`: The primary, stable branch. Always deployable.
- `feature/*`: For new features (e.g., `feature/add-gcp-detector`).
- `bugfix/*`: For fixing bugs (e.g., `bugfix/fix-memory-leak`).
- `docs/*`: For documentation updates.

## Commit Message Conventions
We follow [Conventional Commits](https://www.conventionalcommits.org/). This allows us to auto-generate changelogs and version bumps.

Format:
```
<type>(<scope>): <subject>

<body>
```

**Types:**
- `feat`: A new feature (correlates with MINOR in semantic versioning).
- `fix`: A bug fix (correlates with PATCH in semantic versioning).
- `docs`: Documentation only changes.
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `perf`: A code change that improves performance.
- `test`: Adding missing tests or correcting existing tests.
- `ci`: Changes to our CI configuration files and scripts.

**Example:**
`feat(detectors): add regex detector for GCP service accounts`

## Pull Request Process
1. Update the `README.md` or `docs/` with details of changes to the interface or architecture, if applicable.
2. Ensure you have added corresponding tests in the `tests/` directory.
3. Open a PR using our Pull Request Template.
4. Once CI passes, a maintainer will review your code.
5. Address any feedback. Once approved, the maintainer will merge your PR.

## Semantic Versioning Policy
RedactAI adheres to [Semantic Versioning 2.0.0](https://semver.org/).
- **MAJOR** version when you make incompatible API changes,
- **MINOR** version when you add functionality in a backwards compatible manner, and
- **PATCH** version when you make backwards compatible bug fixes.

*Note: The CLI surface, the REST API endpoints, and the `Detector` interface are considered our public API.*

## Release Checklist
For maintainers, follow these steps before cutting a new release:
1. Verify all CI pipelines are passing on `main`.
2. Update the `CHANGELOG.md` with all changes since the last release.
3. Bump the version in `src/redactai/engine/__init__.py`.
4. Commit the changes: `git commit -m "chore: bump version to vX.Y.Z"`.
5. Tag the commit: `git tag vX.Y.Z`.
6. Push the tag: `git push origin vX.Y.Z`.
7. Draft a new GitHub Release referencing the tag and pasting the changelog section.
