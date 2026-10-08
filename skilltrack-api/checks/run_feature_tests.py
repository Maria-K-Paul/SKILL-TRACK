"""Run Nizzy's HTTP feature tests (test_new_features.py) against a local API on port 8002, skipping the two
that open a SQLite file on Nizzy's own computer.

    1. Start the API on port 8002 with DATABASE_URL set to a TEST database
       (uvicorn app.main:app --port 8002), after running checks/set_demo_passwords.py on that database.
    2. python checks/run_feature_tests.py

Expected today: 18 PASS and 1 FAIL ("Expected 409" in the double-booking test: students can currently book
another level's slot in their domain, which is an open design question for Nizzy and Tharun).
"""
import _guard  # noqa: F401  (puts skilltrack-api on the import path)
import test_new_features as t

TESTS = ("test_domains_list", "test_domain_detail", "test_single_active_enrollment", "test_parallel_enrollments",
         "test_booking_acknowledgement", "test_booking_success_and_cancel", "test_double_booking",
         "test_capacity_race", "test_cross_student_isolation")
SKIPPED = ("test_after_window_expired", "test_noshow_idempotency")  # both use paths on Nizzy's computer

for name in TESTS:
    getattr(t, name)()
print(f"\n(skipped {', '.join(SKIPPED)}: they open files on Nizzy's computer)")
