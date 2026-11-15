"""Run:  uv run python sweep.py

Prints the threshold table and saves results/sweep.md + results/sweep.csv.
These are the numbers for your README and resume.
"""
from app.config import RESULTS_DIR
from app.evaluate import write_reports

if __name__ == "__main__":
    print(write_reports(RESULTS_DIR))
    print(f"Saved to {RESULTS_DIR}")
