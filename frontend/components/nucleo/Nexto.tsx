"use client";

import { useId } from "react";

type Pose = "idle" | "explaining" | "thinking";

export function Nexto({
  pose = "idle",
  className,
  label,
}: {
  pose?: Pose;
  className?: string;
  label: string;
}) {
  const tilt = pose === "explaining" ? -5 : pose === "thinking" ? 6 : 0;
  const id = useId().replace(/:/g, "");
  const arm = (x1: number, y1: number, x2: number, y2: number, id: string) => (
    <>
      <path d={`M${x1} ${y1} L${x2} ${y2}`} stroke="#8E97AB" strokeWidth="11" strokeLinecap="round" />
      <path d={`M${x1} ${y1} L${x2} ${y2}`} stroke={`url(#${id}b)`} strokeWidth="8" strokeLinecap="round" />
    </>
  );
  return (
    <svg
      className={className}
      viewBox="-12 -14 146 158"
      role="img"
      aria-label={label}
    >
      <defs>
        <linearGradient id={`${id}b`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F6F8FC" />
          <stop offset="1" stopColor="#C4CBDA" />
        </linearGradient>
        <radialGradient id={`${id}h`} cx=".34" cy=".22" r=".6">
          <stop offset="0" stopColor="#fff" stopOpacity=".95" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}v`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1A2030" />
          <stop offset="1" stopColor="#06080C" />
        </linearGradient>
        <radialGradient id={`${id}e`} cx=".45" cy=".4" r=".6">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset=".35" stopColor="#C9CEFF" />
          <stop offset="1" stopColor="#6E79F5" />
        </radialGradient>
      </defs>
      <ellipse cx="60" cy="136" rx={pose === "thinking" ? 20 : 24} ry="4.5" fill="#000" opacity=".42" />
      <g transform={`rotate(${tilt} 60 75)`}>
        {pose === "explaining" ? arm(22, 84, 7, 64, id) : arm(22, 88, 15, 104, id)}
        {pose === "thinking" ? arm(98, 88, 86, 97, id) : arm(98, 88, 105, 104, id)}
        <path d="M60 27 Q60 18 65 12" fill="none" stroke="#8E97AB" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="65.5" cy="10" r={pose === "thinking" ? 5.5 : 4.5} fill="#8F98FF" />
        <circle cx="64.3" cy="8.8" r="1.4" fill="#fff" opacity=".85" />
        <rect x="14" y="58" width="9" height="22" rx="4.5" fill="#2E3546" />
        <rect x="97" y="58" width="9" height="22" rx="4.5" fill="#2E3546" />
        <path d="M60 24C88 24 100 44 100 70C100 99 83 117 60 117C37 117 20 99 20 70C20 44 32 24 60 24Z" fill={`url(#${id}b)`} stroke="#AEB6C7" strokeWidth="1" />
        <path d="M60 24C88 24 100 44 100 70C100 99 83 117 60 117C37 117 20 99 20 70C20 44 32 24 60 24Z" fill={`url(#${id}h)`} />
        <rect x="29" y="45" width="62" height="33" rx="16.5" fill={`url(#${id}v)`} stroke="#39415A" strokeWidth="1.5" />
        {pose === "explaining" ? (
          <path d="M49.5 67 Q60 47 70.5 67 Q60 58.5 49.5 67 Z" fill={`url(#${id}e)`} stroke="#D3D7FF" strokeWidth="1.2" />
        ) : (
          <circle cx={pose === "thinking" ? 68 : 60} cy={pose === "thinking" ? 58 : 62} r={pose === "thinking" ? 7 : 9} fill={`url(#${id}e)`} />
        )}
        {pose === "explaining" ? (
          <g fill="#8F98FF">
            <rect x="50" y="93" width="3" height="7" rx="1.5" />
            <rect x="55" y="90" width="3" height="13" rx="1.5" />
            <rect x="60" y="92" width="3" height="9" rx="1.5" />
            <rect x="65" y="89" width="3" height="15" rx="1.5" />
            <rect x="70" y="93" width="3" height="7" rx="1.5" />
          </g>
        ) : (
          <rect x="52" y="94" width="16" height="5" rx="2.5" fill="#8F98FF" opacity={pose === "thinking" ? 0.35 : 0.6} />
        )}
      </g>
    </svg>
  );
}
