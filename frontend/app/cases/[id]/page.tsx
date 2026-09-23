"use client";

import { use } from "react";
import { CaseDetailView } from "@/components/cases/CaseDetailView";

// Next.js 16: `params` is now a Promise. Since this page needs interactivity
// (tabs, mutations, dialogs) it is a Client Component, so we unwrap the
// promise with React's `use()` hook rather than `await` and delegate the
// actual data fetching / rendering to a client component tree below.
export default function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <CaseDetailView caseId={id} />;
}
