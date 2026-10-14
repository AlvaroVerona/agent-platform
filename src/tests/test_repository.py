import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import RunRepository


@pytest.fixture()
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    session = sessionmaker(bind=engine)()

    yield RunRepository(session)

    session.close()


def test_run_lifecycle(repo):
    run = repo.create_run(idea="una idea", status="CREATED")

    assert run.id is not None
    assert run.final_tech_spec is None

    repo.set_product_spec(run.id, {"goal": "x"})
    repo.update_status(run.id, "PRODUCT_DONE")

    stored = repo.get_run(run.id)
    assert stored.product_spec == {"goal": "x"}
    assert stored.status == "PRODUCT_DONE"


def test_one_run_many_iterations(repo):
    run = repo.create_run(idea="idea", status="CREATED")

    for i in range(1, 4):
        repo.create_iteration(
            run_id=run.id,
            index=i,
            tech_spec={"v": i},
            qa_report={"score": 0.5},
            approved=(i == 3),
        )

    # una sola fila en runs, tres en iterations
    assert len(repo.get_all_runs()) == 1

    iterations = repo.get_iterations(run.id)
    assert [it.index for it in iterations] == [1, 2, 3]
    assert iterations[-1].approved is True


def test_final_tech_spec_set_on_approval(repo):
    run = repo.create_run(idea="idea", status="CREATED")

    repo.set_final_tech_spec(run.id, {"stack": ["Python"]})
    repo.update_status(run.id, "QA_APPROVED")

    stored = repo.get_run(run.id)
    assert stored.final_tech_spec == {"stack": ["Python"]}
    assert stored.status == "QA_APPROVED"


def test_delete_run_cascades_iterations(repo):
    run = repo.create_run(idea="idea", status="CREATED")

    repo.create_iteration(
        run_id=run.id,
        index=1,
        tech_spec={},
        qa_report={},
        approved=False,
    )

    repo.delete_run(run.id)

    assert repo.get_run(run.id) is None
    assert repo.get_iterations(run.id) == []
