import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
  SortingState,
  getGroupedRowModel,
  getExpandedRowModel,
} from "@tanstack/react-table";
import { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import Button from "./Button";

export function Table({
  children,
  className,
}: {
  children: any;
  className?: string;
}) {
  return (
    <table className={className ?? "min-w-full divide-y divide-slate-200 bg-white shadow rounded"}>
      {children}
    </table>
  );
}

export function TableHead({ children }: { children: any }) {
  return <thead className="bg-slate-50">{children}</thead>;
}
export function TableRow({ key, children }: { key: any; children: any }) {
  return <tr key={key}>{children}</tr>;
}

export function TableHeaderCell({
  key,
  children,
  onClick,
}: {
  key: any;
  children: any;
  onClick?: (value: any) => void;
}) {
  return (
    <td
      key={key}
      className="px-4 py-2.5 text-left text-micro-label"
      onClick={onClick}
    >
      {children}
    </td>
  );
}
export function TableCell({ children }: { children: any }) {
  return (
    <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
      {children}
    </td>
  );
}

export function TableBody({ children }: { children: any }) {
  return <tbody className="divide-y divide-slate-100">{children}</tbody>;
}

export function TableCommon({
  data,
  columns,
  onRowClick,
  bare = false,
}: {
  data: any[];
  columns: any[];
  onRowClick?: (row: any) => void;
  // When the table is already embedded in its own card (border/shadow/rounded
  // container), pass `bare` to drop Table's own card chrome and avoid a
  // double-boxed look.
  bare?: boolean;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const table = useReactTable({
    data,
    columns,
    // state: { sorting, grouping: ["category"], expanded },
    initialState: { grouping: ["category"] }, // let table manage expanded/sorting
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  });

  return (
    <Table className={bare ? "min-w-full divide-y divide-slate-100" : undefined}>
      <TableHead>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              const sorted = header.column.getIsSorted();
              const canSort = header.column.getCanSort();
              return (
                <TableHeaderCell
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                  {canSort && (
                    <>
                      {sorted ? (
                        sorted === "asc" ? (
                          <span>↑</span>
                        ) : (
                          <span>↓</span>
                        )
                      ) : (
                        <span className="opacity-50 text-xs">↕</span>
                      )}
                    </>
                  )}
                </TableHeaderCell>
              );
            })}
          </TableRow>
        ))}
      </TableHead>
      <tbody className="divide-y divide-slate-100">
        {table.getRowModel().rows.map((row) => (
          <tr
            key={row.id}
            onClick={() => onRowClick?.(row.original)}
            className="hover:bg-slate-50 cursor-pointer"
          >
            {row.getVisibleCells().map((cell) => {
              // IMPORTANT: use cell-level helpers (v8)
              const isGrouped = cell.getIsGrouped();
              const isAggregated = cell.getIsAggregated();
              const isPlaceholder = cell.getIsPlaceholder();

              // Render grouped row: usually only one column (the grouped column) should show
              if (isGrouped) {
                // show expander + the grouped value + count of subRows
                return (
                  <td
                    key={cell.id}
                    className="px-4 py-2.5 text-left text-sm font-normal text-slate-700"
                  >
                    <Button
                      variant="expander"
                      onClick={row.getToggleExpandedHandler()}
                      className="mr-2 align-middle"
                      title={row.getIsExpanded() ? "Collapse group" : "Expand group"}
                    >
                      {row.getIsExpanded() ? (
                        <ChevronDown size={15} className="text-slate-400" />
                      ) : (
                        <ChevronRight size={15} className="text-slate-400" />
                      )}
                    </Button>
                    <strong className="mr-2 text-slate-800">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </strong>
                    <span className="text-slate-400">
                      ({row.subRows.length})
                    </span>
                  </td>
                );
              }

              // Aggregated (subtotal) cell
              if (isAggregated) {
                return (
                  <td
                    key={cell.id}
                    className="px-4 py-2.5 text-left text-sm font-normal text-slate-700"
                  >
                    {flexRender(
                      cell.column.columnDef.aggregatedCell ??
                        cell.column.columnDef.cell,
                      cell.getContext(),
                    )}
                  </td>
                );
              }

              // Placeholder cell for grouped layout (keep cell empty)
              if (isPlaceholder) {
                return <td key={cell.id} className="px-4 py-2.5" />;
              }

              // Normal cell
              return (
                <td
                  key={cell.id}
                  className="px-4 py-2.5 text-left text-sm font-normal text-slate-700"
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
