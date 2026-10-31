import concurrent.futures
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.product import Product
from app.models.subscription import (
    Subscription,
    SubscriptionCounter,
    SubscriptionLine,
    SubscriptionRenewalRecord,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.modules.subscriptions.services import (
    _generate_subscription_number,
    renew_subscription,
)


def run_pg_concurrency_tests():
    print(f"Connecting to PostgreSQL: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_engine(settings.DATABASE_URL, pool_size=20, max_overflow=10)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    current_year = datetime.now(timezone.utc).year

    # --------------------------------------------------------------------------
    # TEST 1: Simultaneous First-Time Subscription Number Generation (10 threads)
    # --------------------------------------------------------------------------
    print("\n--- TEST 1: Concurrent Subscription Number Generation ---")
    with SessionLocal() as db:
        # Delete counter row for current year to simulate cold start
        counter = db.get(SubscriptionCounter, current_year)
        if counter:
            db.delete(counter)
            db.commit()

    generated_numbers = []
    errors = []

    def generate_number_task():
        with SessionLocal() as db:
            try:
                num = _generate_subscription_number(db)
                db.commit()
                return num
            except Exception as e:
                db.rollback()
                return f"ERROR: {e}"

    num_threads = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(generate_number_task) for _ in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res.startswith("ERROR:"):
                errors.append(res)
            else:
                generated_numbers.append(res)

    print(f"Threads launched: {num_threads}")
    print(f"Numbers generated: {len(generated_numbers)}")
    print(f"Errors encountered: {len(errors)}")
    if errors:
        print(f"Error details: {errors}")
        sys.exit(1)

    # Validate uniqueness
    unique_numbers = set(generated_numbers)
    assert len(unique_numbers) == num_threads, f"Duplicates found! {generated_numbers}"

    # Extract sequences and sort
    seqs = sorted([int(n.split("-")[-1]) for n in generated_numbers])
    print(f"Sequences obtained: {seqs}")
    assert seqs == list(range(1, num_threads + 1)), f"Gaps or non-sequential: {seqs}"

    with SessionLocal() as db:
        counter = db.get(SubscriptionCounter, current_year)
        assert counter is not None, "Counter row does not exist!"
        assert counter.next_seq == num_threads + 1, f"Counter next_seq expected {num_threads + 1}, got {counter.next_seq}"

    print(">> TEST 1 PASSED: 10 concurrent threads generated 10 unique, sequential subscription numbers with zero errors!")

    # --------------------------------------------------------------------------
    # TEST 2: Concurrent Renewal Idempotency & Locking (5 simultaneous threads)
    # --------------------------------------------------------------------------
    print("\n--- TEST 2: Concurrent Renewal Idempotency Guard ---")
    test_sub_id = None
    with SessionLocal() as db:
        # Create test customer & plan
        cust = Customer(
            display_name="PG Concurrency Corp",
            billing_email=f"pg_conc_{uuid.uuid4().hex[:6]}@example.com",
            billing_state="Maharashtra",
            billing_country_code="IN",
            is_active=True,
        )
        db.add(cust)

        plan = Plan(
            name=f"PG Conc Plan {uuid.uuid4().hex[:6]}",
            price=Decimal("100.00"),
            currency="INR",
            billing_interval="MONTHLY",
            interval_count=1,
            allow_renewal=True,
            is_active=True,
        )
        db.add(plan)
        db.flush()

        sub = Subscription(
            subscription_number=f"SUB-TEST-{uuid.uuid4().hex[:6]}",
            customer_id=cust.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=date(2026, 11, 1),
            expiry_date=date(2026, 12, 1),
            next_billing_date=date(2026, 12, 1),
            current_period_start=date(2026, 11, 1),
            current_period_end=date(2026, 12, 1),
            billing_interval="MONTHLY",
            interval_count=1,
            recurring_subtotal=Decimal("100.00"),
            currency="INR",
            cancel_at_period_end=False,
            billing_cycle_count=1,
        )
        db.add(sub)
        db.commit()
        test_sub_id = sub.id

    target_date = date(2026, 12, 1)

    def renew_task():
        with SessionLocal() as db:
            try:
                renewed = renew_subscription(
                    db,
                    test_sub_id,
                    actor=None,
                    expected_renewal_date=target_date,
                )
                db.commit()
                return "SUCCESS"
            except Exception as e:
                db.rollback()
                return f"REJECTED: {type(e).__name__} - {getattr(e, 'detail', str(e))}"

    renewal_workers = 5
    renewal_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=renewal_workers) as executor:
        futures = [executor.submit(renew_task) for _ in range(renewal_workers)]
        for f in concurrent.futures.as_completed(futures):
            renewal_results.append(f.result())

    success_count = sum(1 for r in renewal_results if r == "SUCCESS")
    rejected_count = sum(1 for r in renewal_results if r.startswith("REJECTED:"))
    print(f"Renewal workers: {renewal_workers}")
    print(f"Success count: {success_count}")
    print(f"Rejected / Idempotent guard count: {rejected_count}")
    for r in renewal_results:
        print(f"  Result: {r}")

    assert success_count == 1, f"Expected exactly 1 renewal success, got {success_count}!"
    assert rejected_count == renewal_workers - 1, f"Expected {renewal_workers - 1} rejections, got {rejected_count}!"

    with SessionLocal() as db:
        # Verify exactly one renewal record exists for period Nov 1 -> Dec 1
        records = (
            db.query(SubscriptionRenewalRecord)
            .filter(SubscriptionRenewalRecord.subscription_id == test_sub_id)
            .all()
        )
        assert len(records) == 1, f"Expected 1 renewal record, got {len(records)}!"
        assert records[0].period_start == date(2026, 12, 1)
        assert records[0].period_end == date(2027, 1, 1)
        assert records[0].cycle_number == 2

        sub = db.get(Subscription, test_sub_id)
        assert sub.billing_cycle_count == 2
        assert sub.expiry_date == date(2027, 1, 1)

    print(">> TEST 2 PASSED: Exactly 1 renewal succeeded, 4 concurrent requests safely rejected by idempotency / row lock!")
    print("\nALL POSTGRESQL CONCURRENCY & IDEMPOTENCY TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_pg_concurrency_tests()
