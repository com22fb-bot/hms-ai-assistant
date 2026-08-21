type DonextoMarkProps = {
  className?: string;
  size?: number;
  /** Leave empty when a visible “Donexto” wordmark sits next to the mark. */
  alt?: string;
};

/** Placa 3D: Do / Next / To + @ morada sobre los tres puntos. */
export const DONEXTO_APP_ICON_SRC = "/brand/donexto-3d-2026.png";

export function DonextoMark({
  className,
  size = 72,
  alt = "",
}: DonextoMarkProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static brand asset in /public
    <img
      className={className}
      src={DONEXTO_APP_ICON_SRC}
      width={size}
      height={size}
      alt={alt}
      decoding="async"
    />
  );
}
