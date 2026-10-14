from sqlalchemy.orm import Session

from src.database.models import Iteration, Run


class RunRepository:
    """
    Repositorio responsable únicamente del acceso a la base de datos.

    No crea sesiones.
    No hace lógica de negocio.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========================================================
    # RUNS
    # ==========================================================

    def create_run(
        self,
        *,
        idea: str,
        status: str,
        product_spec: dict | None = None,
    ) -> Run:

        run = Run(
            idea=idea,
            status=status,
            product_spec=product_spec,
        )

        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        return run

    def get_all_runs(self):

        return (
            self.db.query(Run)
            .order_by(Run.created_at.desc())
            .all()
        )

    def get_run(self, run_id: int):

        return (
            self.db.query(Run)
            .filter(Run.id == run_id)
            .first()
        )

    def delete_run(self, run_id: int):

        run = self.get_run(run_id)

        if run:
            self.db.delete(run)
            self.db.commit()

        return run

    def update_status(self, run_id: int, status: str):

        run = self.get_run(run_id)

        if run:
            run.status = status
            self.db.commit()
            self.db.refresh(run)

        return run

    def set_product_spec(self, run_id: int, product_spec: dict):

        run = self.get_run(run_id)

        if run:
            run.product_spec = product_spec
            self.db.commit()
            self.db.refresh(run)

        return run

    def set_final_tech_spec(self, run_id: int, tech_spec: dict):

        run = self.get_run(run_id)

        if run:
            run.final_tech_spec = tech_spec
            self.db.commit()
            self.db.refresh(run)

        return run

    # ==========================================================
    # ITERATIONS
    # ==========================================================

    def create_iteration(
        self,
        *,
        run_id: int,
        index: int,
        tech_spec: dict,
        qa_report: dict,
        approved: bool,
    ) -> Iteration:

        iteration = Iteration(
            run_id=run_id,
            index=index,
            tech_spec=tech_spec,
            qa_report=qa_report,
            approved=approved,
        )

        self.db.add(iteration)
        self.db.commit()
        self.db.refresh(iteration)

        return iteration

    def get_iterations(self, run_id: int):

        return (
            self.db.query(Iteration)
            .filter(Iteration.run_id == run_id)
            .order_by(Iteration.index)
            .all()
        )
