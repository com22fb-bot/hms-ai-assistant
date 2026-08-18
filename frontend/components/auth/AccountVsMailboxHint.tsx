"use client";

import { Info } from "lucide-react";

import {
  ACCOUNT_VS_MAILBOX,
  connectBannerFor,
  loginHelperFor,
  oneLinerFor,
} from "@/lib/accountVsMailbox";

import "./account-vs-mailbox-hint.css";

type HintVariant = "login" | "connect" | "step2" | "compact";

type AccountVsMailboxHintProps = {
  variant?: HintVariant;
  className?: string;
  email?: string;
};

/**
 * Recordatorio visual: Donexto no pide la contraseña del buzón;
 * el correo de la cuenta es el mismo que se autoriza a leer.
 */
export function AccountVsMailboxHint({
  variant = "compact",
  className,
  email,
}: AccountVsMailboxHintProps) {
  const classes = [
    "dx-avm-hint",
    `dx-avm-hint--${variant}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const text =
    variant === "login"
      ? loginHelperFor(email)
      : variant === "connect"
        ? connectBannerFor(email)
        : variant === "step2"
          ? ACCOUNT_VS_MAILBOX.step2Body
          : oneLinerFor(email);

  return (
    <p className={classes} role="note">
      <Info size={16} aria-hidden className="dx-avm-hint__icon" />
      <span>{text}</span>
    </p>
  );
}
