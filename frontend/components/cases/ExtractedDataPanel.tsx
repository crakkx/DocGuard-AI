import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { cn, formatPercent, formatCurrency } from "@/lib/utils";
import { FileStack } from "lucide-react";
import type { CaseDetail, ExtractedField } from "@/types";

interface Row {
  fieldName: string;
  po?: ExtractedField;
  invoice?: ExtractedField;
  grn?: ExtractedField;
}

function buildRows(caseDetail: CaseDetail): Row[] {
  const rows = new Map<string, Row>();

  const add = (key: "po" | "invoice" | "grn", fields: ExtractedField[] | undefined) => {
    for (const f of fields ?? []) {
      const existing = rows.get(f.field_name) ?? { fieldName: f.field_name };
      existing[key] = f;
      rows.set(f.field_name, existing);
    }
  };

  add("po", caseDetail.po_document?.extracted_data);
  add("invoice", caseDetail.invoice_document?.extracted_data);
  add("grn", caseDetail.grn_document?.extracted_data);

  return Array.from(rows.values()).sort((a, b) => a.fieldName.localeCompare(b.fieldName));
}

function valuesDiffer(row: Row): boolean {
  const values = [row.po?.field_value, row.invoice?.field_value, row.grn?.field_value].filter(
    (v): v is string => v !== undefined
  );
  if (values.length < 2) return false;
  return new Set(values).size > 1;
}

function formatFieldValue(fieldName: string, rawValue: string): string {
  if (!rawValue) return "—";
  const trimmed = rawValue.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        if (parsed.length === 0) return "0 items";
        const first = parsed[0];
        const desc = first?.item_description || first?.description || first?.name || "Item";
        if (parsed.length === 1) return String(desc);
        return `${desc} (+${parsed.length - 1} more)`;
      } else if (typeof parsed === "object" && parsed !== null) {
        const parts: string[] = [];
        for (const [k, v] of Object.entries(parsed)) {
          if (typeof v === "object" && v !== null && "amount" in v) {
            parts.push(`${k}: ${formatCurrency(Number((v as any).amount))}`);
          } else if (typeof v === "string" || typeof v === "number") {
            parts.push(`${k}: ${v}`);
          }
        }
        if (parts.length > 0) return parts.join(", ");
        return JSON.stringify(parsed);
      }
    } catch {
      // ignore parse errors
    }
  }
  if (["total_amount", "subtotal", "unit_price", "amount"].includes(fieldName.toLowerCase())) {
    const num = Number(rawValue.replace(/,/g, ""));
    if (!Number.isNaN(num)) return formatCurrency(num);
  }
  return rawValue;
}

function Cell({ field }: { field?: ExtractedField }) {
  if (!field) return <span className="text-slate-300">—</span>;
  return (
    <div className="flex items-center gap-1.5 min-w-0 max-w-[280px]">
      <span
        className="truncate font-medium text-slate-800 text-xs"
        title={field.field_value}
      >
        {formatFieldValue(field.field_name, field.field_value)}
      </span>
      <span className="shrink-0 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 tabular-nums">
        {formatPercent(field.confidence)}
      </span>
    </div>
  );
}

export function ExtractedDataPanel({ caseDetail }: { caseDetail: CaseDetail }) {
  const rows = buildRows(caseDetail);
  const hasAnyDocument =
    caseDetail.po_document || caseDetail.invoice_document || caseDetail.grn_document;

  if (!hasAnyDocument || rows.length === 0) {
    return (
      <EmptyState
        icon={FileStack}
        title="Nothing to compare yet"
        description="Link at least one document with extracted fields to see a comparison."
      />
    );
  }

  return (
    <Card>
      <CardContent className="pt-5">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Field</TableHead>
              <TableHead>Purchase Order</TableHead>
              <TableHead>Invoice</TableHead>
              <TableHead>Goods Receipt</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const mismatch = valuesDiffer(row);
              return (
                <TableRow key={row.fieldName} className={cn(mismatch && "bg-amber-50")}>
                  <TableCell className="font-medium text-slate-700">{row.fieldName}</TableCell>
                  <TableCell className={cn(mismatch && "text-amber-900")}>
                    <Cell field={row.po} />
                  </TableCell>
                  <TableCell className={cn(mismatch && "text-amber-900")}>
                    <Cell field={row.invoice} />
                  </TableCell>
                  <TableCell className={cn(mismatch && "text-amber-900")}>
                    <Cell field={row.grn} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
