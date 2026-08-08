"use client";

import { Search, X } from "lucide-react";

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
}

export default function SearchBox({
  value,
  onChange,
}: SearchBoxProps) {
  return (
    <label className="search-box">
      <Search size={17} aria-hidden="true" />

      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Buscar asunto o remitente"
        aria-label="Buscar correos"
      />

      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Limpiar búsqueda"
        >
          <X size={15} />
        </button>
      ) : null}
    </label>
  );
}
