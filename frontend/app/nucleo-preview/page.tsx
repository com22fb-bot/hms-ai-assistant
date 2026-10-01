import { redirect } from "next/navigation";

import { NucleoPreviewClient } from "@/app/nucleo-preview/preview-client";

export const dynamic = "force-dynamic";

export default function NucleoPreviewPage() {
  if (process.env.NODE_ENV === "production") {
    redirect("/");
  }
  return <NucleoPreviewClient />;
}
