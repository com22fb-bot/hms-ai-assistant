"use client";

import type {
  MailFilter,
  MailFilterOption,
} from "@/types/mail";

interface FilterButtonsProps {
  filters: MailFilterOption[];
  activeFilter: MailFilter;
  onChange: (filter: MailFilter) => void;
}

export default function FilterButtons({
  filters,
  activeFilter,
  onChange,
}: FilterButtonsProps) {
  return (
    <div className="filters" aria-label="Filtros de correo">
      {filters.map((filter) => (
        <button
          key={filter.id}
          className={
            activeFilter === filter.id
              ? "filter-button filter-button-active"
              : "filter-button"
          }
          type="button"
          onClick={() => onChange(filter.id)}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}
