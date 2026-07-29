"use client";

import { Mail, SearchX } from "lucide-react";

import EmptyState from "@/components/dashboard/EmptyState";
import LoadingState from "@/components/dashboard/LoadingState";
import MailItem from "@/components/dashboard/MailItem";
import type { GmailMessage } from "@/types/mail";

interface MailListProps {
  messages: GmailMessage[];
  loading: boolean;
  connected: boolean;
  onConnect: () => void;
}

export default function MailList({
  messages,
  loading,
  connected,
  onConnect,
}: MailListProps) {
  if (loading) {
    return (
      <div className="mail-list">
        <LoadingState />
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="mail-list">
        <EmptyState
          icon={<Mail size={26} />}
          title="Conecta tu cuenta de Google"
          description="Autoriza Gmail para visualizar los correos en este panel."
          actionLabel="Conectar Gmail"
          onAction={onConnect}
        />
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="mail-list">
        <EmptyState
          icon={<SearchX size={26} />}
          title="No encontramos correos"
          description="Modifica el filtro o la búsqueda para ver otros resultados."
        />
      </div>
    );
  }

  return (
    <div className="mail-list">
      {messages.map((message) => (
        <MailItem key={message.id} message={message} />
      ))}
    </div>
  );
}
