from app.db.database import SessionLocal

from app.services.data_generator import (
    generate_company,
    generate_vendors,
    generate_transactions,
    generate_invoices,
    generate_bank_transactions,
)


def seed_database():

    db = SessionLocal()

    try:

        print("Creating company...")

        company = generate_company(db)

        print("Generating vendors...")

        vendors = generate_vendors(
            db,
            count=100,
        )

        print("Generating transactions...")

        transactions = generate_transactions(
            db,
            vendors,
            count=10000,
        )

        print("Generating invoices...")

        invoices = generate_invoices(
            db,
            vendors,
            count=3000,
        )

        print("Generating bank transactions...")

        bank_transactions = generate_bank_transactions(
            db,
            transactions,
            count=5000,
        )

        db.commit()

        print()
        print("================================")
        print("RazControl database seeded")
        print("================================")
        print(f"Company: {company.name}")
        print(f"Vendors: {len(vendors)}")
        print(f"Transactions: {len(transactions)}")
        print(f"Invoices: {len(invoices)}")
        print(
            f"Bank transactions: "
            f"{len(bank_transactions)}"
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_database()