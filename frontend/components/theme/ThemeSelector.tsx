"use client";

import { Palette } from "lucide-react";

import {
  ThemeId,
  useTheme,
} from "@/components/theme/ThemeProvider";

const OPTIONS: Array<{
  id: ThemeId;
  label: string;
}> = [
  { id: "obsidian", label: "Fado Black" },
  { id: "aurora", label: "Aurora Blue" },
  { id: "graphite", label: "Graphite Pro" },
  { id: "arctic", label: "Arctic Light" },
];

export default function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <label
      className="premium-theme-selector"
      title="Cambiar apariencia"
    >
      <Palette size={16} />
      <select
        value={theme}
        aria-label="Tema visual"
        onChange={(event) =>
          setTheme(event.target.value as ThemeId)
        }
      >
        {OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
