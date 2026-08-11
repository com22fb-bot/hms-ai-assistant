"use client";

import { Info } from "lucide-react";

import { ACCOUNT_VS_MAILBOX } from "@/lib/accountVsMailbox";

import "./account-vs-mailbox-hint.css";

type HintVariant = "login" | "connect" | "step2" | "compact";

type AccountVsMailboxHintProps = {
  variant?: HintVariant;
  className?: string;
};

const TEXT: Record<HintVariant, string> = {
  login: ACCOUNT_VS_MAILBOX.loginHelper,
  connect: ACCOUNT_VS_MAILBOX.connectBanner,
  step2: ACCOUNT_VS_MAILBOX.step2Body,
  compact: ACCOUNT_VS_MAILBOX.oneLiner,
};

/**
 * Recordatorio visual: cuenta Donexto ≠ credenciales del buzón.
 */
export function AccountVsMailboxHint({
  variant = "compact",
  className,
}: AccountVsMailboxHintProps) {
  const classes = [
    "dx-avm-hint",
    `dx-avm-hint--${variant}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <p className={classes} role="note">
      <Info size={16} aria-hidden className="dx-avm-hint__icon" />
      <span>{TEXT[variant]}</span>
    </p>
  );
}
