"use client";

export function DonextoBrand({
  compact = false,
}: {
  compact?: boolean;
}) {
  return (
    <div className={compact ? "dx-brand is-compact" : "dx-brand"}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className="dx-brand__logo"
        src="/brand/brand-logo-3d.jpg"
        width={72}
        height={72}
        alt="Donexto — Do Next To…"
      />
      {compact ? null : (
        <span className="dx-brand__text">
          <strong>Donexto</strong>
          <small>
            <span className="dx-c">Do</span>{" "}
            <span className="dx-m">Next</span>{" "}
            <span className="dx-c">To…</span>
          </small>
        </span>
      )}
    </div>
  );
}
