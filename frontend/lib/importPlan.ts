// Espejo exacto de backend download_plan (import_categories.py): mensajes únicos que se procesarán.
export const REVIEW_ID = "revisar";
export const PROTECT_PREFIX = "proteger:";

export type PlanPreview = {
  areas?: Record<string, number>;
  review?: number;
  area_protected?: Record<string, Record<string, number>>;
};
export type DownloadPlan = { selected: number; protected: number; excluded: number; to_process: number; total: number };

export function downloadPlan(preview: PlanPreview, exclude: string[]): DownloadPlan {
  const off = new Set(exclude);
  const areas: Record<string, number> = { ...(preview.areas || {}), [REVIEW_ID]: preview.review ?? 0 };
  let selected = 0;
  let prot = 0;
  let dropped = 0;
  for (const [area, count] of Object.entries(areas)) {
    if (!off.has(area)) { selected += count; continue; }
    const kept = Object.entries(preview.area_protected?.[area] || {})
      .filter(([cls]) => !off.has(PROTECT_PREFIX + cls))
      .reduce((sum, [, n]) => sum + n, 0);
    prot += kept;
    dropped += count - kept;
  }
  return { selected, protected: prot, excluded: dropped, to_process: selected + prot, total: selected + prot + dropped };
}
