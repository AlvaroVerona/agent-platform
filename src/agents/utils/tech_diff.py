from copy import deepcopy
from typing import Any


class TechDiffApplier:
    """
    Aplica un patch generado por QA sobre un TechSpec existente.

    Reglas:

    - Nunca sobrescribe información útil con listas vacías.
    - Hace merge recursivo de diccionarios.
    - Para listas:
        * si el patch está vacío -> conserva la lista original
        * si el patch tiene contenido -> reemplaza
    - Ignora valores nulos o placeholders.
    """

    @staticmethod
    def apply_patch(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:

        base = deepcopy(base or {})
        patch = patch or {}

        if not isinstance(base, dict):
            base = {}

        if not isinstance(patch, dict):
            return base

        for key, value in patch.items():

            # ==================================================
            # IGNORAR PLACEHOLDERS
            # ==================================================

            if value is None:
                continue

            if value == "...":
                continue

            # ==================================================
            # MERGE RECURSIVO DE DICCIONARIOS
            # ==================================================

            if isinstance(value, dict):

                current = base.get(key, {})

                if not isinstance(current, dict):
                    current = {}

                base[key] = TechDiffApplier.apply_patch(
                    current,
                    value,
                )

                continue

            # ==================================================
            # LISTAS
            # ==================================================

            if isinstance(value, list):

                # No borrar información existente
                if len(value) == 0:
                    continue

                # Si la lista contiene únicamente elementos vacíos
                valid_items = []

                for item in value:

                    if item is None:
                        continue

                    if item == "...":
                        continue

                    if isinstance(item, dict) and len(item) == 0:
                        continue

                    valid_items.append(item)

                if len(valid_items) == 0:
                    continue

                base[key] = valid_items
                continue

            # ==================================================
            # ESCALARES
            # ==================================================

            base[key] = value

        return base