import type { Metadata } from "next";

import { AssistChat } from "./AssistChat";

import "./asistencia.css";

export const metadata: Metadata = {
  title: "Asistencia personalizada · Donexto",
  description: "Habla con el asistente de Donexto después de verificar tu correo.",
  robots: { index: false, follow: false },
};

export default function AsistenciaPage() {
  return <AssistChat />;
}
