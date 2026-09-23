"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { FileStack } from "lucide-react";
import type { PolicyChunk } from "@/types";

const TRUNCATE_AT = 400;

function ChunkCard({ chunk }: { chunk: PolicyChunk }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = chunk.content.length > TRUNCATE_AT;
  const shown = expanded || !isLong ? chunk.content : `${chunk.content.slice(0, TRUNCATE_AT)}…`;

  const heading = [chunk.section_number, chunk.section_title].filter(Boolean).join(" ");

  return (
    <Card>
      <CardContent className="flex flex-col gap-2 pt-5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {heading || `Chunk ${chunk.chunk_index + 1}`}
          </p>
          <span className="shrink-0 text-xs text-slate-400">#{chunk.chunk_index}</span>
        </div>
        <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-slate-700">
          {shown}
        </pre>
        {isLong && (
          <Button
            variant="link"
            size="sm"
            className="h-auto w-fit px-0 text-xs"
            onClick={() => setExpanded((e) => !e)}
          >
            {expanded ? "Show less" : "Show more"}
          </Button>
        )}
        {chunk.page_number !== null && chunk.page_number !== undefined && (
          <p className="text-xs text-slate-400">Page {chunk.page_number}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function ChunkViewer({ chunks }: { chunks: PolicyChunk[] }) {
  if (chunks.length === 0) {
    return (
      <EmptyState
        icon={FileStack}
        title="No chunks available"
        description="This policy hasn't been ingested into chunks yet."
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {chunks.map((chunk) => (
        <ChunkCard key={chunk.id} chunk={chunk} />
      ))}
    </div>
  );
}
