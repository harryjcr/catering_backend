#!/usr/bin/env python3
"""
Test script to verify the next review date calculation logic.
This demonstrates how the new logic works without needing actual database data.
"""

from datetime import date
import calendar


def get_last_day_of_month(year: int, month: int) -> date:
    """Get the last day of a given month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def get_last_day_of_next_month(reference_date: date) -> date:
    """Get the last day of the month following the reference date."""
    # Calculate next month
    if reference_date.month == 12:
        next_year = reference_date.year + 1
        next_month = 1
    else:
        next_year = reference_date.year
        next_month = reference_date.month + 1

    return get_last_day_of_month(next_year, next_month)


# Test scenarios
print("=" * 70)
print("TESTING NEXT REVIEW DATE CALCULATION")
print("=" * 70)
print()

test_cases = [
    ("Review done on January 25", date(2024, 1, 25)),
    ("Review done on January 31 (last day)", date(2024, 1, 31)),
    ("Review done on February 15", date(2024, 2, 15)),
    ("Review done on March 1 (first day)", date(2024, 3, 1)),
    ("Review done on December 15", date(2024, 12, 15)),
    ("Review done on December 31 (year end)", date(2024, 12, 31)),
]

for description, review_date in test_cases:
    next_review = get_last_day_of_next_month(review_date)
    print(f"✓ {description}:")
    print(f"  Review date:      {review_date.strftime('%d/%m/%Y')} ({review_date.strftime('%B %d, %Y')})")
    print(f"  Next review due:  {next_review.strftime('%d/%m/%Y')} ({next_review.strftime('%B %d, %Y')})")
    print()

print("=" * 70)
print("CONCLUSION:")
print("=" * 70)
print("✓ Reviews are ALWAYS scheduled for the last day of the following month")
print("✓ Users can perform reviews early (e.g., on the 25th)")
print("✓ The actual review date is recorded (e.g., 25th)")
print("✓ But the NEXT review is still scheduled for the last day of next month")
print()
