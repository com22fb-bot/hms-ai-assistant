import path from "node:path";
import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const nextConfig: NextConfig = {
  turbopack: {
    // El repositorio tiene otro package-lock.json en la raíz general.
    // Fijar esta raíz evita que Next.js/Turbopack use el directorio equivocado.
    root: path.resolve(process.cwd()),
  },
};

export default nextConfig;

initOpenNextCloudflareForDev();
