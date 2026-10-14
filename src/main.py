import json
import logging
import sys

from src.services.run_service import RunService


def main():
    # Consola: eventos del pipeline a INFO.
    # Para ver las respuestas crudas del LLM: level=logging.DEBUG
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    )

    service = RunService()

    idea = " ".join(sys.argv[1:]) or "Quiero crear una plataforma para diseñar agentes IA"

    result = service.execute(idea)

    if result:
        print("\n🏁 FINAL TECH SPEC\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Workflow finished without approved solution.")


if __name__ == "__main__":
    main()
