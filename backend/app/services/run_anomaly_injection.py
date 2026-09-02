from app.db.database import SessionLocal
from app.services.anomaly_injector import inject_all_anomalies


def main():

    db = SessionLocal()

    try:

        print()
        print("===================================")
        print("RazControl AI - Anomaly Injection")
        print("===================================")
        print()

        results = inject_all_anomalies(db)

        db.commit()

        print()
        print("===================================")
        print("Anomaly injection completed")
        print("===================================")
        print()

        for result in results:
            print(result)

        print()
        print(
            f"Total injected anomalies: "
            f"{len(results)}"
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()