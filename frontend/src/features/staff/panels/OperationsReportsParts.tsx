import type React from "react";

export type ReportCell = string | number | null;
export type ReportRows = { rows: ReportCell[][] };

type ChartRow = { label: string; value: number };

export function reportRows(data?: ReportRows) {
  return data?.rows?.slice(1) ?? [];
}

function headers(data?: ReportRows) {
  return (data?.rows?.[0] ?? []).map(String);
}

function rowValue(row: ReportCell[], header: string[], key: string) {
  return row[header.indexOf(key)];
}

export function chartRows(data: ReportRows | undefined, labelKey: string, valueKey: string): ChartRow[] {
  const header = headers(data);
  return reportRows(data)
    .map((row) => ({
      label: String(rowValue(row, header, labelKey) ?? "Unknown"),
      value: Number(rowValue(row, header, valueKey) ?? 0),
    }))
    .filter((row) => row.value > 0);
}

export function DataState(props: { loading: boolean; error: unknown; empty: boolean; children: React.ReactNode }) {
  if (props.loading) return <p className="mt-3 text-sm text-muted">Loading reports...</p>;
  if (props.error) return <p className="mt-3 text-sm text-red-600">{props.error instanceof Error ? props.error.message : "Unable to load report."}</p>;
  if (props.empty) return <p className="mt-3 text-sm text-muted">No records.</p>;
  return <>{props.children}</>;
}

export function StatCards({ stats }: { stats: [string, number | undefined][] }) {
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map(([label, value]) => (
        <div key={label} className="rounded-md border border-line bg-surface p-3">
          <p className="text-2xl font-bold text-ink">{formatNumber(value ?? 0)}</p>
          <p className="text-xs text-muted">{label}</p>
        </div>
      ))}
    </div>
  );
}

export function BarChart({ rows, valueLabel }: { rows: ChartRow[]; valueLabel?: string }) {
  const maxValue = Math.max(...rows.map((row) => row.value), 0);
  if (!rows.length || maxValue <= 0) return <p className="text-sm text-muted">No chart data.</p>;

  return (
    <div className="space-y-2">
      {rows.map((row, index) => {
        const width = `${Math.max((row.value / maxValue) * 100, 4)}%`;
        return (
          <div key={`${row.label}-${index}`} className="grid grid-cols-[minmax(7rem,11rem)_1fr_auto] items-center gap-2 text-sm">
            <span className="truncate text-ink" title={row.label}>
              {row.label}
            </span>
            <div className="h-3 overflow-hidden rounded bg-bg">
              <div className="h-full rounded bg-accent" style={{ width }} />
            </div>
            <span className="min-w-14 text-right text-xs text-muted">
              {formatNumber(row.value)} {valueLabel ?? ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function ReportTable({ data }: { data?: ReportRows }) {
  const tableHeaders = headers(data);
  const rows = reportRows(data);
  if (!tableHeaders.length || !rows.length) return <p className="text-sm text-muted">No records.</p>;

  return (
    <div className="mt-4 max-h-80 overflow-auto rounded-md border border-line">
      <table className="min-w-full divide-y divide-line text-left text-sm">
        <thead className="sticky top-0 bg-surface text-xs uppercase tracking-wide text-muted">
          <tr>
            {tableHeaders.map((header) => (
              <th key={header} className="whitespace-nowrap px-3 py-2 font-semibold">
                {header.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-bg text-ink">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {tableHeaders.map((header, cellIndex) => (
                <td key={`${header}-${cellIndex}`} className="whitespace-nowrap px-3 py-2 text-sm">
                  {formatCell(row[cellIndex])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: ReportCell | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return formatNumber(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return new Date(value).toLocaleString();
  return value;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value);
}
