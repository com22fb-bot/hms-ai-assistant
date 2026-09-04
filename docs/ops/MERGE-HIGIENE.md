# Higiene de merges — hms-ai-assistant

**Última revisión:** 2026-09-04 · **`main`:** `5119231` (PR #35 mergeado)

Héctor hace merge manual en `main`. Los agentes Cursor abren PRs en ramas `cursor/*`.

## Regla

- **No dejar PRs obsoletos abiertos.** Si el cambio ya está en `main`, fue superseded, o contradice el producto actual → cerrar con comentario y borrar la rama remota.
- **Un solo PR “siguiente” en cola** salvo urgencia explícita.
- Tras merge: borrar rama remota `cursor/*` si GitHub no la eliminó sola.

## Cola de merges (orden)

| Orden | PR | Rama | Estado | Notas |
| --- | --- | --- | --- | --- |
| **1 (siguiente)** | [#36](https://github.com/com22fb-bot/hms-ai-assistant/pull/36) | `cursor/docs-matriz-buzones-gobierno` | OPEN · MERGEABLE · CLEAN | Matriz P1 buzones personal / empresa / gobierno MX. **Merge lo hace Héctor.** |
| — | — | — | — | Nada más en cola tras #36. |

## PRs activos válidos

Solo **#36** debe permanecer abierto hasta merge.

## PRs obsoletos — cerrar y limpiar

El token del Cloud Agent **no tiene permiso** para `closePullRequest` en GitHub. Héctor (o cuenta con write) debe cerrarlos desde la UI o con `gh pr close` local. Ramas remotas obsoletas ya borradas o listadas abajo.

| PR | Rama | Motivo de cierre | Rama remota |
| --- | --- | --- | --- |
| [#22](https://github.com/com22fb-bot/hms-ai-assistant/pull/22) | `cursor/continuar-no-yahoo-unknown-3d73` | Superseded por **#35** (Continuar sin Yahoo / cuenta Donexto ya en `main`). Conflictos `DIRTY`. | **Rama borrada** (2026-09-04) |
| [#7](https://github.com/com22fb-bot/hms-ai-assistant/pull/7) | `cursor/p00-pendientes-3d73` | Docs P00 ya en `main` (`docs/ops/P00-pendientes.md`, etc.). Conflictos `DIRTY`. | **Rama borrada** (2026-09-04) |
| [#4](https://github.com/com22fb-bot/hms-ai-assistant/pull/4) | `cursor/yahoo-mailbox-guide-3d73` | Guía Yahoo 16 dígitos obsoleta — producto **OAuth only** (`docs/ops/YAHOO_OAUTH.md`). | **Rama borrada** (2026-09-04) |
| [#2](https://github.com/com22fb-bot/hms-ai-assistant/pull/2) | `cursor/import-actions-visible-3d73` | Login/marca ago-18 superseded por **#34** + **#35**. Conflictos `DIRTY`. | **Rama borrada** (2026-09-04) |
| [#3](https://github.com/com22fb-bot/hms-ai-assistant/pull/3) draft | `cursor/dev-environment-setup-75f1` | Draft obsoleto: solo `AGENTS.md` raíz + `.gitignore` (ago-18), nunca mergeado. Re-documentar Cloud/Codespace en PR nuevo si hace falta. | **Rama borrada** (2026-09-04) |

### Comentarios sugeridos al cerrar

Copiar/pegar al cerrar cada PR en GitHub:

- **#22:** *Cerrado por higiene de merges: superseded por PR #35 (Continuar/Yahoo sin cuenta Donexto ya está en `main` en 5119231). Rama obsoleta con conflictos.*
- **#7:** *Cerrado por higiene de merges: contenido P00/docs ya incorporado en `main`; PR con conflictos y sin valor de merge independiente.*
- **#4:** *Cerrado por higiene de merges: guía Yahoo de código de 16 dígitos obsoleta — OAuth únicamente. Rama remota eliminada.*
- **#2:** *Cerrado por higiene de merges: login/marca Donexto superseded por PR #34 y #35. Conflictos con `main`.*
- **#3:** *Cerrado (draft obsoleto): infra Cloud Agent de ago-18; abrir PR nuevo si se necesita documentación de entorno.*

### Ramas remotas obsoletas (2026-09-04)

Ya eliminadas del remoto:

- `cursor/continuar-no-yahoo-unknown-3d73`
- `cursor/p00-pendientes-3d73`
- `cursor/yahoo-mailbox-guide-3d73`
- `cursor/import-actions-visible-3d73`
- `cursor/dev-environment-setup-75f1`

**No tocar:** `main`, `cursor/docs-matriz-buzones-gobierno`.

## PRs recién mergeados (referencia)

| PR | Título | Merge |
| --- | --- | --- |
| #35 | P0b: login claro, buzones honestos, celular, Plan Normal $19.99 | 2026-09-02 → `5119231` |
| #34 | Gate Continuar / monitorear | Antes de #35 |
| #32 | GitHub higiene | Mergeado |
| #33 | Plan original pasos | Mergeado |

Ramas remotas de PRs ya mergeados (`cursor/p0b-claro-waitlist-mobile-03a9`, `cursor/gate-continuar-monitorear-921c`, etc.) pueden borrarse en una pasada opcional de limpieza; no bloquean la cola.

## Checklist post-merge (#36)

1. Merge #36 en GitHub (Héctor).
2. `git fetch origin main`
3. Borrar `cursor/docs-matriz-buzones-gobierno` si queda en remoto.
4. Actualizar esta tabla de cola (vacía hasta el siguiente PR).
