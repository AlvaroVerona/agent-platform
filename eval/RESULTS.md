# Eval results: llama3.1, 20 fixed ideas (eval/ideas.json), 3 repetitions per version

| versión | reps | aprobadas (media y rango) | pasan el gate estricto | iteraciones medias |
|---|---|---|---|---|
| Baseline (código original) | 3 | 53% (50% a 55%) | 88% (85% a 90%) | 2.38 (2.15 a 2.60) |
| Mejorado | 3 | 95% (95% a 95%) | 95% (95% a 95%) | 1.20 (1.20 a 1.20) |

Por tanda: baseline 11/20, 10/20, 11/20 (una tanda previa sin specs guardados dio 15/20); mejorado 19/20 en las tres.
Segundos por run: baseline 166 (máquina con otra carga), 82 y 69; mejorado 51 a 53. Fallbacks y errores: 0 en todas las tandas.

## Cómo leerlo
- El mejorado usa temperatura 0, así que sus tres tandas son prácticamente la misma ejecución: la repetición **no** añade
  información sobre su variabilidad. La variación real del baseline (temperatura por defecto) sí se ve: 50% a 55%, con un
  15/20 aislado en la tanda previa.
- La subida de aprobación mezcla tres cambios no separados: temperatura 0, aprobación sin el `is_valid` del LLM, y el
  resto (structured outputs, gate, prompts neutrales). El gate estricto aplicado a ambos da 88% vs 95%: la diferencia en
  coherencia de los specs finales es mucho menor que la de aprobación.
- Fallbacks y contenido inventado fueron 0 en las seis tandas: esas defensas no se ejercitaron.
- Un solo modelo (llama3.1) y un solo conjunto de 20 ideas.
