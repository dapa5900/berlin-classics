#!/usr/bin/env bash
# Non-interactive rebase to fix .env.example in first commit
# Change 'pick' to 'edit' for first commit, then continue

# Reset to parent of first commit
git reset --hard 7bfecb5

# Re-create the first commit without .env.example
git add -A -- ':!venv' ':!.pytest_cache' ':!.ruff_cache' ':!__pycache__' ':!cache' ':!output' ':!*.pyc' ':!.env'
git commit -m "Add daily newsletter scheduler with cleanup

- scripts/run_scheduled.bat: runs fresh scrape and keeps only latest newsletter
- scripts/setup_scheduler.bat: one-time setup for daily 18:00 task
- scripts/unscheduler.bat: removes the scheduled task"

# Re-apply the .env.example fix on top
git add .env.example
git commit -m "Fix .env.example: remove real API key, add placeholder"
