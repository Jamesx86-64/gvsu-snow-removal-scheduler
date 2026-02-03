[![CI](https://github.com/Jamesx86-64/gvsu-snow-removal-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/Jamesx86-64/gvsu-snow-removal-scheduler/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![Built with devenv](https://devenv.sh/assets/devenv-badge.svg)](https://devenv.sh)
![License](https://img.shields.io/badge/license-MIT-green)

# GVSU Rowing Snow Removal Calculator

A Python automation tool built to manage snow removal logistics for the Grand
Valley State University (GVSU) Rowing Team.

> This project demonstrates real-world management, scheduling, API integration,
> CI/CD practices, and a fairness-driven algorithm design.

## Context & Motivation

As an executive board member of the GVSU Rowing Team, I am tasked with
coordinating our fundraising partnership with GVSU Facilities, where
student-athletes are contracted to clear snow from campus walkways in order to
help the community and pay for their rowing dues.

Coordinating these efforts manually takes time, and is prone to error and bias.
We needed to dispatch 6-person teams on short notice while ensuring:

- **Safety:** Every team has an experienced Team Leader and a balance of Varsity
  and Novice rowers.

- **Fairness:** Work is distributed evenly across the roster, prioritizing those
  who haven't done as many snow removals.

- **Speed:** Our contract is on call often between 12 to 24 hours before the
  snow removal the following morning at 5 AM, schedules need to be built
  quickly.

I developed this application to automate the scheduling logic, saving
administrative time and ensuring equitable treatment for all athletes.

## Features

- **Google Sheets API Integration:** Seamless access to live team data.

- **Constraint-Based Scheduling:** Intelligently balances Varsity/Novice ratios.

- **Fairness Priority:** Automatic sorting by historical participation to ensure
  fairness.

- **Data Validation:** Automatic detection of duplicate submissions or roster
  mismatches.

## How It Works

1. Athletes submit availability via Google Forms.

1. Responses are synced to Google Sheets.

1. This tool:

   - validates submissions

   - ranks candidates by fairness

   - applies safety and roster constraints

1. A 6-person snow removal team is generated automatically.

## Algorithm & Architecture

This tool integrates with the Google Sheets API to fetch real-time availability
and roster data. It employs a custom scheduling algorithm and efficient data
structures to compute the optimal team:

1. **Data Ingestion:** Pulls availability and roster data into memory.

1. **The Algorithm:**

- Candidates are stored in a list of dictionaries and sorted by the number of
  shifts they have done.

- Greedily iterates through sorted candidates from least to greatest amount of
  snow removals done:

  - **Find a Leader:** First available Team Leader is selected.

  - **Fill Roster:** Remaining spots filled with priority on fairness and
    Varsity/Novice balance.

- This ensures that people who have done less snow removals are chosen first.

## Prerequisites

- Python 3.10+

- Google Cloud Service Account credentials

- Access to the target Google Sheet

### Optional (Recommended)

- **Devenv**: Provides a fully reproducible development environment, including
  Python, formatting tools, linters, and test dependencies.

Dependencies are pinned via `devenv.lock` and `uv.lock` to ensure reproducible
environments across local development and CI.

## Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/Jamesx86-64/gvsu-snow-removal-scheduler
   cd gvsu-snow-removal-scheduler
   ```

1. Set up the development environment (recommended):

   ```bash
   devenv shell
   ```

1. Edit `config.json` file:

   ```json
   {
     "api_key_path": "path/to/credentials.json",
     "sheet_name": "Sheet Name",
     "worksheets": {
       "responses": "Worksheet Name",
       "records": "Worksheet Name"
     }
   }
   ```

1. Run the tool:

   Using `just` (recommended):

   ```bash
   just run
   ```

   or directly:

   ```bash
   python src/snow_removal_calculator/main.py
   ```

## Tech Stack

- **Python 3.10+**

- **Google Sheets API**

- **GitHub Actions** – CI

- **pytest** – testing

- **treefmt** – formatting

- **ruff** – linting

- **pyright** – type checking

- **uv** – package management

- **just** – command runner

- **devenv** – reproducible dev environment

## Testing & Quality Assurance

- All checks as well as trufflehog run automatically in CI on every push and
  pull request

- All checks are enforced locally via Git pre-commit hooks when using `devenv`

- Unit tests are written using `pytest`

- Static analysis is performed with `ruff` and `pyright`

- Formatting is enforced with `treefmt`

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE)
file for details.
