from src.database.database import SessionLocal
from src.database.models import Run


def main():
    db = SessionLocal()

    runs = db.query(Run).all()

    print(f"\n📊 TOTAL RUNS: {len(runs)}\n")

    for r in runs:
        print(
            f"ID: {r.id} | {r.created_at} | {r.status}"
            f" | iteraciones: {len(r.iterations)}"
            f" | aprobado: {'sí' if r.final_tech_spec else 'no'}"
        )


if __name__ == "__main__":
    main()
