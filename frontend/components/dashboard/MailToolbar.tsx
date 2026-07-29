"use client";

import FilterButtons from "@/components/dashboard/FilterButtons";
import SearchBox from "@/components/dashboard/SearchBox";
import {
  MAIL_FILTERS,
  type MailFilter,
} from "@/types/mail";

interface MailToolbarProps {
  activeFilter: MailFilter;
  searchTerm: string;
  onFilterChange: (filter: MailFilter) => void;
  onSearchChange: (value: string) => void;
}

export default function MailToolbar({
  activeFilter,
  searchTerm,
  onFilterChange,
  onSearchChange,
}: MailToolbarProps) {
  return (
    <div className="mail-toolbar">
      <FilterButtons
        filters={MAIL_FILTERS}
        activeFilter={activeFilter}
        onChange={onFilterChange}
      />

      <SearchBox value={searchTerm} onChange={onSearchChange} />
    </div>
  );
}
