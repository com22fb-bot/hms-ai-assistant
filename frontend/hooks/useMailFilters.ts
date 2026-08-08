"use client";

import { useMemo, useState } from "react";

import type { GmailMessage, MailFilter } from "@/types/mail";

export function containsLabel(
  message: GmailMessage,
  label: string,
): boolean {
  return message.labels.includes(label);
}

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function useMailFilters(messages: GmailMessage[]) {
  const [activeFilter, setActiveFilter] =
    useState<MailFilter>("all");

  const [searchTerm, setSearchTerm] = useState("");

  const unreadCount = useMemo(
    () => messages.filter((message) => message.is_unread).length,
    [messages],
  );

  const personalCount = useMemo(
    () =>
      messages.filter((message) =>
        containsLabel(message, "CATEGORY_PERSONAL"),
      ).length,
    [messages],
  );

  const promotionsCount = useMemo(
    () =>
      messages.filter((message) =>
        containsLabel(message, "CATEGORY_PROMOTIONS"),
      ).length,
    [messages],
  );

  const filteredMessages = useMemo(() => {
    const normalizedSearch = normalizeText(searchTerm.trim());

    return messages.filter((message) => {
      let matchesFilter = true;

      switch (activeFilter) {
        case "unread":
          matchesFilter = message.is_unread;
          break;

        case "personal":
          matchesFilter = containsLabel(
            message,
            "CATEGORY_PERSONAL",
          );
          break;

        case "promotions":
          matchesFilter = containsLabel(
            message,
            "CATEGORY_PROMOTIONS",
          );
          break;

        case "social":
          matchesFilter = containsLabel(
            message,
            "CATEGORY_SOCIAL",
          );
          break;

        case "updates":
          matchesFilter = containsLabel(
            message,
            "CATEGORY_UPDATES",
          );
          break;

        default:
          matchesFilter = true;
      }

      if (!matchesFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      const searchableText = normalizeText(
        [
          message.subject,
          message.sender,
          message.sender_email ?? "",
          message.snippet,
        ].join(" "),
      );

      return searchableText.includes(normalizedSearch);
    });
  }, [activeFilter, messages, searchTerm]);

  return {
    activeFilter,
    searchTerm,
    filteredMessages,
    unreadCount,
    personalCount,
    promotionsCount,
    setActiveFilter,
    setSearchTerm,
  };
}
