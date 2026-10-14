import json
import logging

from sqlalchemy.orm import Session

from src.agents.product_manager_agent import ProductManagerAgent
from src.agents.qa_agent import QAAgent
from src.agents.tech_architect_agent import TechArchitectAgent
from src.agents.utils.tech_diff import TechDiffApplier
from src.database.database import SessionLocal
from src.database.repository import RunRepository
from src.domain.run_states import RunStatus

logger = logging.getLogger(__name__)


class RunService:
    """
    Orquesta una ejecución completa del pipeline:

        Idea
          ↓
    Product Manager
          ↓
    Tech Architect
          ↓
           QA
          ↓
      Persistencia
    """

    def __init__(self):

        self.pm = ProductManagerAgent()
        self.tech = TechArchitectAgent()
        self.qa = QAAgent()
        self.last_run_id = None

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def _extract_patch(self, qa_report):

        if not qa_report:
            return {}

        patch = getattr(qa_report, "patch", None)

        if not patch:
            return {}

        #ya es diccionario en este punto  
        if isinstance(patch, dict): 
            return patch
        #si el modelo es pydantic, lo convertimos a diccionario
        if hasattr(patch, "model_dump"):
            return patch.model_dump(exclude_none=True)
        
        return {}

    def _build_tech_context(self, tech_state, qa_report):
        """
        Contexto para la re-iteración del arquitecto:
        el spec (parcheado) + el feedback real de QA.
        """

        context = {"previous_tech_spec": tech_state}

        if qa_report:

            issues = [
                issue for issue in getattr(qa_report, "issues", [])
                if isinstance(issue, dict) and issue.get("description")
            ]

            if issues:
                context["qa_issues"] = issues

            suggestions = getattr(qa_report, "suggestions", [])

            if suggestions:
                context["qa_suggestions"] = suggestions

        return context

    def _qa_approved(self, qa_report):

        if not qa_report:
            return False

        # El booleano is_valid del LLM no se usa: duplica al score y es poco
        # fiable. La coherencia dura la garantiza QAGate (que fuerza score <= 0.5
        # y un issue crítico cuando falla).

        # Umbral calibrado para llama3.1: 0.95 + cero warnings era
        # inalcanzable en la práctica (el sanitizador marca "warning"
        # por defecto). Solo bloquean los issues críticos.
        if getattr(qa_report, "score", 0.0) < 0.8:
            return False

        issues = getattr(qa_report, "issues", [])

        for issue in issues:

            if not isinstance(issue, dict):
                continue

            severity = issue.get("severity", "").lower()

            if severity == "critical":
                return False

        return True

    # ==========================================================
    # PIPELINE
    # ==========================================================

    def execute(self, idea: str):

        tech_state = None

        max_iterations = 3

        db: Session = SessionLocal()
        repository = RunRepository(db)
        run = None
        self.last_run_id = None

        try:

            # --------------------------------------------------
            # CREAR RUN (UNA SOLA FILA POR EJECUCIÓN)
            # --------------------------------------------------

            run = repository.create_run(
                idea=idea,
                status=RunStatus.CREATED,
            )
            self.last_run_id = run.id

            # --------------------------------------------------
            # PRODUCT MANAGER
            # --------------------------------------------------

            product_spec = self.pm.run(idea)

            repository.set_product_spec(
                run.id,
                product_spec.model_dump(),
            )

            repository.update_status(
                run.id,
                RunStatus.PRODUCT_DONE,
            )

            for iteration in range(1, max_iterations + 1):

                logger.info(
                    "Run %d — iteración %d/%d",
                    run.id, iteration, max_iterations,
                )

                # --------------------------------------------------
                # TECH
                # --------------------------------------------------

                tech_spec = self.tech.run(
                    product_spec.model_dump(),
                    tech_state,
                )

                tech_dict = tech_spec.model_dump()

                repository.update_status(
                    run.id,
                    RunStatus.TECH_GENERATED,
                )

                # --------------------------------------------------
                # QA
                # --------------------------------------------------

                repository.update_status(
                    run.id,
                    RunStatus.QA_RUNNING,
                )

                qa_report = self.qa.run(
                    product_spec.model_dump(),
                    tech_dict,
                )

                approved = self._qa_approved(qa_report)

                repository.create_iteration(
                    run_id=run.id,
                    index=iteration,
                    tech_spec=tech_dict,
                    qa_report=qa_report.model_dump(),
                    approved=approved,
                )

                # --------------------------------------------------
                # QA APROBADO
                # --------------------------------------------------

                if approved:

                    logger.info(
                        "Run %d — QA aprobado en la iteración %d "
                        "(score %.2f)",
                        run.id, iteration,
                        getattr(qa_report, "score", 0.0),
                    )

                    repository.set_final_tech_spec(
                        run.id,
                        tech_dict,
                    )

                    repository.update_status(
                        run.id,
                        RunStatus.QA_APPROVED,
                    )

                    return tech_dict

                # --------------------------------------------------
                # APLICAR PATCH DEL QA
                # --------------------------------------------------

                patch = self._extract_patch(qa_report)

                if patch:

                    logger.info(
                        "Run %d — aplicando patch de QA", run.id
                    )
                    logger.debug(
                        "QA patch:\n%s",
                        json.dumps(patch, indent=2, ensure_ascii=False),
                    )

                    patched = TechDiffApplier.apply_patch(
                        tech_dict,
                        patch,
                    )

                else:

                    logger.info(
                        "Run %d — QA no devolvió patch", run.id
                    )

                    patched = tech_dict

                # El arquitecto recibe el spec + el feedback real de QA
                tech_state = self._build_tech_context(
                    patched,
                    qa_report,
                )

            # --------------------------------------------------
            # SI AGOTAMOS ITERACIONES
            # --------------------------------------------------

            logger.info(
                "Run %d — agotadas %d iteraciones sin aprobación",
                run.id, max_iterations,
            )

            repository.update_status(
                run.id,
                RunStatus.QA_FAILED,
            )

            return None

        except Exception:

            # Un fallo del pipeline no debe dejar el run colgado en un estado intermedio
            if run is not None:
                repository.update_status(run.id, RunStatus.ERROR)
            raise

        finally:

            db.close()

    # ==========================================================
    # CRUD
    # ==========================================================

    def get_all_runs(self):

        db = SessionLocal()

        try:

            repository = RunRepository(db)
            return repository.get_all_runs()

        finally:

            db.close()

    def get_run(self, run_id: int):

        db = SessionLocal()

        try:

            repository = RunRepository(db)
            return repository.get_run(run_id)

        finally:

            db.close()

    def delete_run(self, run_id: int):

        db = SessionLocal()

        try:

            repository = RunRepository(db)
            return repository.delete_run(run_id)

        finally:

            db.close()