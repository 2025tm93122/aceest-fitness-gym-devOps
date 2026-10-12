# ACEest Fitness & Gym

## Automated CI/CD Pipeline using GitHub, Jenkins, SonarQube, Docker and GitHub Actions

## 1. Project Overview

ACEest Fitness & Gym is a Flask-based fitness management application
developed for the Introduction to DevOps - Assignment 1.

The project demonstrates an end-to-end DevOps lifecycle using Python
3.12, Flask, SQLite, Git/GitHub, Pytest, Jenkins, SonarQube, Docker,
Gunicorn, and GitHub Actions.

The implementation evolved incrementally from the supplied ACEest Python
application versions into a Flask web application. Each meaningful
milestone was tested, committed, tagged, pushed to GitHub, built in
Jenkins, and analyzed with SonarQube before progressing to later stages.

The final workflow is:

``` text
Local Development
       |
       v
Syntax Check + Pytest
       |
       v
Git Commit / Tag
       |
       v
GitHub Repository
      /          \
     v            v
 Jenkins      GitHub Actions
    |              |
    v              v
 Pytest          Pytest
    |              |
    v              v
SonarQube      Docker Build
    |              |
    v              v
Quality Gate   Docker Pytest
      \          /
       v        v
      Validated Build
```

## 2. Assignment Objectives

The implementation addresses the following objectives:

-   Develop a functional Flask application for ACEest Fitness & Gym.
-   Maintain source code using Git and GitHub.
-   Use meaningful incremental commits and version tags.
-   Implement automated tests with Pytest.
-   Generate test coverage reports.
-   Containerize the application with Docker.
-   Configure Jenkins as the primary automated BUILD environment.
-   Integrate SonarQube static analysis and Quality Gate validation.
-   Configure GitHub Actions for automated validation on pushes and pull
    requests.
-   Provide professional documentation that another engineer can follow
    independently.

## 3. Project Development Approach

The supplied ACEest Python scripts represented different application
milestones. Instead of creating an unrelated Flask application, the
existing functionality was studied and converted incrementally.

The development approach was:

``` text
Provided Python Versions
        |
        v
Understand Existing Features
        |
        v
Convert Milestone to Flask
        |
        v
Run Locally
        |
        v
Create / Update Pytest
        |
        v
Syntax + Test Validation
        |
        v
Git Commit + Version Tag
        |
        v
Push to GitHub
        |
        v
Jenkins Build
        |
        v
SonarQube Analysis
        |
   +----+----+
   |         |
 PASS       FAIL
   |         |
   |         v
   |     Fix Issue
   |         |
   +---------+
        |
        v
Next Milestone
        |
        v
Docker + GitHub Actions
```

Git stores the historical application versions, so duplicate final files
such as `app_v1.py`, `app_v2.py`, and `app_final.py` are unnecessary.

## 4. Project Journey

### 4.1 Flask Conversion

The supplied ACEest application logic was adapted into Flask. This
introduced HTTP routes, browser-based forms, a health endpoint, client
management, fitness program functionality, and persistent data where
required.

### 4.2 Incremental Git Development

Each milestone updated the active `app.py`. Meaningful commits and
annotated tags were used to preserve the history.

### 4.3 Automated Testing

Pytest was added to validate application behavior before code reached
CI. Testing was subsequently reused by Jenkins, Docker, and GitHub
Actions.

### 4.4 Jenkins CI

Jenkins was configured to retrieve code from GitHub and execute a clean
build using Python 3.12. The pipeline performs syntax validation,
Pytest, coverage generation, SonarQube analysis, and Quality Gate
enforcement.

### 4.5 SonarQube

SonarQube was integrated as a quality-control layer. Findings such as
unsafe development-server network binding and excessive Cognitive
Complexity were fixed rather than ignored.

### 4.6 Docker

Docker was added to provide a reproducible runtime. Gunicorn is used for
container execution so Docker networking is separated from Flask's local
development-server configuration.

### 4.7 GitHub Actions

GitHub Actions provides repository-native CI/CD validation for pushes
and pull requests, including syntax/lint validation, Pytest, Docker
image assembly, and Pytest inside Docker.

## 5. Technology Stack

  Technology       Purpose
  ---------------- ----------------------------------
  Python 3.12      Application runtime
  Flask            Web application framework
  SQLite           Application persistence
  Pytest           Automated testing
  pytest-cov       Coverage reporting
  Flake8           Syntax/lint validation
  Git              Version control
  GitHub           Remote repository
  Jenkins          Continuous Integration
  SonarQube        Static analysis and Quality Gate
  SonarScanner     SonarQube analysis client
  Docker           Containerization
  Gunicorn         Container WSGI server
  GitHub Actions   Repository CI/CD

## 6. Application Evolution

  Version   Milestone
  --------- ---------------------------------------
  v1.0      Initial Flask fitness application
  v1.1      Client profile and calorie estimation
  v1.1.2    Multiple-client functionality
  v2.0.1    SQLite persistence and progress
  v2.1.2    Progress functionality refinement
  v2.2.1    Progress visualization
  v2.2.4    Expanded workout/fitness metrics
  v3.0.1    Application refinement
  v3.1.2    Advanced functionality
  v3.2.4    Final milestone

Example tag:

``` bash
git tag -a v2.2.1 -m "ACEest Fitness Flask v2.2.1"
git push origin v2.2.1
```

## 7. Repository Structure

``` text
aceest-fitness-gym-devOp/
|-- app.py
|-- requirements.txt
|-- Jenkinsfile
|-- sonar-project.properties
|-- Dockerfile
|-- .dockerignore
|-- .gitignore
|-- README.md
|-- tests/
|   `-- test_app.py
`-- .github/
    `-- workflows/
        `-- main.yml
```

  File                           Purpose
  ------------------------------ ----------------------------
  `app.py`                       Main Flask application
  `requirements.txt`             Python dependencies
  `tests/test_app.py`            Pytest suite
  `Jenkinsfile`                  Jenkins pipeline
  `sonar-project.properties`     SonarQube settings
  `Dockerfile`                   Container image definition
  `.dockerignore`                Docker build exclusions
  `.gitignore`                   Git exclusions
  `.github/workflows/main.yml`   GitHub Actions workflow
  `README.md`                    Project documentation

## 8. Prerequisites

Local development requires Git, Python 3.12, pip, and
virtual-environment support. Docker is required for container
validation. Jenkins requires the Git, Pipeline, and SonarQube Scanner
plugins. SonarQube and SonarScanner are required for static analysis.

## 9. Local Setup and Execution

### Clone the repository

``` bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd aceest-fitness-gym-devOp
```

### Verify Python

``` bash
python3.12 --version
```

Expected: `Python 3.12.x`.

### Create and activate a virtual environment

``` bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Upgrade pip and install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Verify tools

``` bash
python -m flask --version
pytest --version
```

### Run the application

``` bash
python app.py
```

The local application is available at:

``` text
http://127.0.0.1:5000
```

Verify the health endpoint:

``` bash
curl http://127.0.0.1:5000/health
```

Expected:

``` json
{"status":"healthy"}
```

Stop the development server with `Ctrl+C`.

## 10. Manual Testing

Testing should be performed before committing application changes.

### Syntax validation

``` bash
python -m py_compile app.py
```

No output means compilation succeeded.

### Run Pytest

``` bash
pytest -v
```

Typical output includes individual tests marked `PASSED`. The exact test
names depend on the final milestone.

### Run tests with coverage

``` bash
pytest -v   --junitxml=junit.xml   --cov=app   --cov-report=term-missing   --cov-report=xml:coverage.xml
```

This creates `junit.xml` for test reporting and `coverage.xml` for
SonarQube coverage import.

The testing strategy covers important application behavior such as
health checks, homepage availability, client validation, calorie
calculations, persistence, progress tracking, and milestone-specific
functionality.

## 11. Git and GitHub Strategy

A normal change follows:

``` text
Modify Code -> Syntax Check -> Pytest -> git add -> git commit -> git push -> CI
```

Examples of meaningful commits:

``` text
feat: initialize ACEest Fitness Flask application v1.0
feat: upgrade ACEest Fitness application to v1.1 with client profile and calorie estimation
feat: upgrade ACEest Fitness application to v2.2.1 with progress visualization
fix: resolve SonarQube network binding security issue
fix: resolve SonarQube security and cognitive complexity issues
ci: add Docker GitHub Actions and project documentation
docs: add comprehensive project documentation
```

Useful commands:

``` bash
git log --oneline --decorate
git remote -v
git tag
```

## 12. Jenkins Continuous Integration

Jenkins is the primary controlled BUILD environment. The job uses
**Pipeline script from SCM**, Git as the SCM provider, `main` as the
branch, and `Jenkinsfile` as the Script Path.

High-level integration:

``` text
Git Push
   |
   v
GitHub Repository
   |
   v
Jenkins Detects Change
   |
   v
Checkout Latest Commit
   |
   v
Read Jenkinsfile
   |
   v
Execute Pipeline
```

### Jenkins stages

``` text
Checkout
   |
   v
Setup Python 3.12
   |
   v
Syntax Check
   |
   v
Pytest + Coverage
   |
   v
SonarQube Analysis
   |
   v
Quality Gate
   |
   v
Build Result
```

Jenkins recreates `.venv` for a clean build:

``` bash
rm -rf .venv
python3.12 -m venv .venv
```

It installs dependencies from `requirements.txt`, runs
`python -m py_compile app.py`, executes Pytest with JUnit and coverage
reports, invokes SonarScanner, and waits for the Quality Gate result.

A fully successful pipeline ends with:

``` text
Finished: SUCCESS
```

## 13. SonarQube Integration

SonarQube provides static code analysis. Project configuration is stored
in `sonar-project.properties`.

The integration was established by:

1.  Starting SonarQube.
2.  Creating the ACEest Fitness Gym project.
3.  Generating a project analysis token.
4.  Storing the token securely in Jenkins Credentials.
5.  Configuring the SonarQube server in Jenkins.
6.  Configuring SonarScanner.
7.  Running SonarScanner from the Jenkins pipeline.

Example Jenkins server configuration:

``` text
Name       : SonarQube
Server URL : http://localhost:9000
```

The token is never stored directly in source control.

### Quality improvements

Earlier Flask code used `0.0.0.0` with the development server. SonarQube
identified this as a security concern, so local execution was changed to
`127.0.0.1`.

Earlier versions also had large route functions containing request
handling, validation, database operations, and rendering. SonarQube
reported high Cognitive Complexity. These were refactored into smaller
helper functions.

The quality cycle is:

``` text
Commit -> Jenkins -> Pytest -> SonarQube -> Quality Gate
                                      |
                                FAIL -> Fix -> Recommit
```

## 14. Docker Containerization

Docker provides a portable and reproducible application environment.

The project uses `python:3.12-slim` to reduce unnecessary image size.
Dependencies are installed before copying the full application so Docker
can reuse layers when possible.

### Build the image

``` bash
docker build -t aceest-fitness:latest .
```

### Verify the image

``` bash
docker images | grep aceest
```

### Run the container

``` bash
docker run -d   --name aceest-app   -p 5000:5000   aceest-fitness:latest
```

### Verify

``` bash
docker ps
curl http://localhost:5000/health
```

Expected:

``` json
{"status":"healthy"}
```

### Logs

``` bash
docker logs aceest-app
```

### Stop and remove

``` bash
docker stop aceest-app
docker rm aceest-app
```

Gunicorn handles container networking using a command equivalent to:

``` text
gunicorn --bind 0.0.0.0:5000 app:app
```

This keeps Flask local development restricted while allowing the Docker
container to expose port 5000.

## 15. Testing Inside Docker

Run:

``` bash
docker run --rm aceest-fitness:latest pytest -v
```

This confirms that the Python runtime, dependencies, source code, and
tests work together inside the container.

## 16. GitHub Actions CI/CD

The GitHub Actions workflow is stored in:

``` text
.github/workflows/main.yml
```

It is configured for pushes and pull requests targeting `main`.

High-level workflow:

``` text
Push / Pull Request
       |
       v
Checkout
       |
       v
Python 3.12
       |
       v
Install Dependencies
       |
       v
Syntax Check
       |
       v
Lint
       |
       v
Pytest
       |
       v
Docker Build
       |
       v
Pytest Inside Docker
       |
       v
Workflow Result
```

The workflow therefore validates both the normal Python environment and
the containerized environment.

## 17. Jenkins and GitHub Actions Integration Logic

Both CI systems are intentionally used.

  Jenkins                           GitHub Actions
  --------------------------------- ------------------------------
  Controlled VM BUILD environment   GitHub-hosted runner
  Pulls source from GitHub          Triggered by GitHub events
  Clean Python environment          Clean Python environment
  Syntax validation                 Syntax/lint validation
  Pytest                            Pytest
  Coverage reporting                Docker build
  SonarQube analysis                Docker testing
  Quality Gate                      Repository-native validation

Jenkins focuses on BUILD quality and SonarQube. GitHub Actions focuses
on event-driven validation and container consistency.

## 18. Security and Repository Hygiene

SonarQube tokens are stored in Jenkins Credentials rather than source
control.

`.gitignore` excludes generated/local files such as:

``` text
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
coverage.xml
junit.xml
*.db
.scannerwork/
```

`.dockerignore` excludes unnecessary build context such as:

``` text
.git
.venv
__pycache__
.pytest_cache
.scannerwork
*.db
coverage.xml
junit.xml
```

## 19. Troubleshooting

### Wrong Python version

``` bash
python3 --version
python3.12 --version
```

Use Python 3.12.

### Broken virtual environment

``` bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Syntax failure

``` bash
python -m py_compile app.py
```

### Pytest failure

``` bash
pytest -v
```

Fix the first failing test before proceeding.

### Jenkins failure

Open:

``` text
Jenkins -> ACEest-Fitness-CI -> Build Number -> Console Output
```

Fix the first failed stage before investigating later skipped stages.

### SonarQube Quality Gate failure

Open:

``` text
SonarQube -> ACEest Fitness Gym -> Issues
```

Correct the reported code issue instead of disabling the gate.

### Docker failure

``` bash
docker build -t aceest-fitness:latest .
docker ps -a
docker logs aceest-app
```

## 20. Final Verification Checklist

Before submission verify:

### Local application

``` bash
python -m py_compile app.py
pytest -v
python app.py
curl http://127.0.0.1:5000/health
```

### Coverage

``` bash
pytest --cov=app --cov-report=term-missing
```

### Docker

``` bash
docker build -t aceest-fitness:latest .
docker run --rm aceest-fitness:latest pytest -v
```

### Jenkins expected result

``` text
Checkout              SUCCESS
Setup Python           SUCCESS
Syntax Check           SUCCESS
Pytest                 SUCCESS
SonarQube Analysis     SUCCESS
Quality Gate           PASSED
Pipeline               SUCCESS
```

### SonarQube expected result

``` text
Quality Gate: PASSED
```

### GitHub Actions expected result

``` text
Checkout Repository       PASSED
Set Up Python             PASSED
Install Dependencies      PASSED
Python Syntax Check       PASSED
Lint Application          PASSED
Run Pytest                PASSED
Build Docker Image        PASSED
Run Pytest Inside Docker  PASSED
```

## 21. Assignment Deliverables

  Required Deliverable         Project Artifact
  ---------------------------- ------------------------------
  Flask source code            `app.py`
  Python dependencies          `requirements.txt`
  Pytest suite                 `tests/test_app.py`
  Docker infrastructure        `Dockerfile`
  Docker exclusions            `.dockerignore`
  Jenkins BUILD pipeline       `Jenkinsfile`
  SonarQube configuration      `sonar-project.properties`
  GitHub Actions               `.github/workflows/main.yml`
  Git exclusions               `.gitignore`
  Professional documentation   `README.md`
  Version history              Git commits
  Release milestones           Git tags
  Remote repository            GitHub

## 22. Evaluation Criteria Mapping

### Application Integrity

The Flask application is validated through local execution, the health
endpoint, Pytest, Jenkins, Docker, and GitHub Actions.

### VCS Maturity

The project demonstrates incremental commits, meaningful commit
messages, version tags, fix commits, infrastructure commits,
documentation commits, and synchronization with GitHub.

### Testing Coverage

Testing is performed through local Pytest, Jenkins Pytest, coverage
reporting, Docker Pytest, and GitHub Actions.

### Docker Efficiency

The image uses `python:3.12-slim`, `pip install --no-cache-dir`, and
`.dockerignore` to reduce unnecessary image contents and build context.

### Pipeline Reliability

Jenkins validates checkout, Python setup, syntax, tests, coverage,
SonarQube, and the Quality Gate. GitHub Actions validates syntax/lint,
tests, Docker assembly, and tests inside Docker.

### Documentation Clarity

This README is designed so another engineer can independently understand
the project, clone it, configure Python, install dependencies, run the
application, run tests, generate coverage, understand Git/versioning,
understand Jenkins and SonarQube, build and run Docker, understand
GitHub Actions, and troubleshoot common problems.

## 23. Key Learnings

The project demonstrates that DevOps combines:

``` text
Development
    +
Version Control
    +
Testing
    +
Automation
    +
Quality Validation
    +
Containerization
    +
Delivery
```

Important lessons include:

-   Runtime versions should be consistent across environments.
-   Automated tests provide fast feedback.
-   Static analysis finds issues that functional tests may not find.
-   Quality Gates should drive improvements rather than be bypassed.
-   Docker improves portability and consistency.
-   Jenkins and GitHub Actions provide complementary CI validation.
-   Git commits and tags provide a clean application history.

## 24. Conclusion

ACEest Fitness & Gym demonstrates an end-to-end DevOps implementation.

The project began with supplied ACEest Python application versions and
evolved incrementally into a Flask web application with Git version
control, automated Pytest validation, Jenkins CI, SonarQube static
analysis and Quality Gate enforcement, Docker containerization, and
GitHub Actions CI/CD.

The final repository is designed so another engineer can clone the
source, reproduce the development environment, execute tests, build and
run the container, and understand the automated CI/CD architecture using
this README.

The final lifecycle is:

``` text
Application Development
          |
          v
Git Version Control
          |
          v
Automated Testing
          |
          v
Jenkins CI
          |
          v
SonarQube Quality Gate
          |
          v
Docker Containerization
          |
          v
GitHub Actions CI/CD
          |
          v
Validated Final Application
```

------------------------------------------------------------------------

## Author

**BITS Pilani**\
**Introduction to DevOps - Assignment 1**\
**Project: ACEest Fitness & Gym - Automated CI/CD Pipeline**
