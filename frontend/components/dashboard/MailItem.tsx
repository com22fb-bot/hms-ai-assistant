import type {
  GmailMessage,
  MailCategory,
} from "@/types/mail";

function containsLabel(
  message: GmailMessage,
  label: string,
): boolean {
  return message.labels.includes(label);
}

function getCategory(message: GmailMessage): MailCategory {
  if (containsLabel(message, "CATEGORY_PERSONAL")) {
    return {
      label: "Personal",
      className: "category category-personal",
    };
  }

  if (containsLabel(message, "CATEGORY_PROMOTIONS")) {
    return {
      label: "Promoción",
      className: "category category-promotions",
    };
  }

  if (containsLabel(message, "CATEGORY_SOCIAL")) {
    return {
      label: "Social",
      className: "category category-social",
    };
  }

  if (containsLabel(message, "CATEGORY_UPDATES")) {
    return {
      label: "Actualización",
      className: "category category-updates",
    };
  }

  return {
    label: "General",
    className: "category category-general",
  };
}

function formatMessageDate(value: string | null): string {
  if (!value) {
    return "Fecha no disponible";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getInitials(name: string): string {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  return initials || "✉";
}

interface MailItemProps {
  message: GmailMessage;
}

export default function MailItem({ message }: MailItemProps) {
  const category = getCategory(message);

  return (
    <article
      className={
        message.is_unread
          ? "mail-item mail-item-unread"
          : "mail-item"
      }
    >
      <div className="sender-avatar">
        {getInitials(message.sender)}
      </div>

      <div className="mail-body">
        <div className="mail-primary-row">
          <div className="mail-sender-row">
            {message.is_unread ? (
              <span
                className="unread-dot"
                title="Correo no leído"
              />
            ) : null}

            <strong>{message.sender}</strong>

            <span className={category.className}>
              {category.label}
            </span>
          </div>

          <time dateTime={message.received_at ?? undefined}>
            {formatMessageDate(message.received_at)}
          </time>
        </div>

        <h3>{message.subject || "Sin asunto"}</h3>

        <p>
          {message.snippet || "Sin vista previa disponible."}
        </p>

        <div className="mail-footer">
          <span>
            {message.sender_email || "Correo no disponible"}
          </span>

          <span className={message.is_unread ? "unread-label" : undefined}>
            {message.is_unread ? "No leído" : "Leído"}
          </span>
        </div>
      </div>
    </article>
  );
}
