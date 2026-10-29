import { useId, useMemo, useState, type ReactNode } from "react";
import "./table.css";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  className?: string;
  render: (row: T) => ReactNode;
  /** Sem sortValue a coluna não é ordenável. Números ordenam como números, textos em ordem alfabética pt-BR. */
  sortValue?: (row: T) => string | number;
}

export interface Sort {
  key: string;
  dir: "asc" | "desc";
}

interface SortableTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string;
  caption: string;
  initialSort?: Sort;
  /** Clique na linha inteira (o teclado usa o botão dentro da linha, que dispara o mesmo clique). */
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string | undefined;
}

const ARIA_SORT = { asc: "ascending", desc: "descending" } as const;
const DIR_WORD = { asc: "crescente", desc: "decrescente" } as const;

export function SortableTable<T>({ columns, rows, getKey, caption, initialSort, onRowClick, rowClassName }: SortableTableProps<T>) {
  const [sort, setSort] = useState<Sort | null>(initialSort ?? null);
  const selectId = useId();

  const sorted = useMemo(() => {
    const column = columns.find((c) => c.key === sort?.key);
    if (!sort || !column?.sortValue) return rows;
    const value = column.sortValue;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = value(a);
      const y = value(b);
      const order = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "pt-BR");
      return order * factor;
    });
  }, [columns, rows, sort]);

  // chaves repetidas (dois sinais bloqueados iguais, por exemplo) ganham um sufixo em vez de colidir
  const keys = useMemo(() => {
    const seen = new Map<string, number>();
    return sorted.map((row) => {
      const base = getKey(row);
      const n = seen.get(base) ?? 0;
      seen.set(base, n + 1);
      return n === 0 ? base : `${base}#${n}`;
    });
  }, [sorted, getKey]);

  const sortable = columns.filter((c) => c.sortValue);
  const toggle = (key: string) =>
    setSort((current) => (current?.key === key && current.dir === "asc" ? { key, dir: "desc" } : { key, dir: "asc" }));

  return (
    <>
      {/* no celular o cabeçalho some (as linhas viram cartões), então a ordenação ganha um controle próprio */}
      <div className="mobile-sort">
        <label htmlFor={selectId}>Ordenar por</label>
        <select
          id={selectId}
          value={sort ? `${sort.key}:${sort.dir}` : ""}
          onChange={(e) => {
            const [key, dir] = e.target.value.split(":") as [string, Sort["dir"]];
            setSort({ key, dir });
          }}
        >
          {!sort && <option value="">Ordem original</option>}
          {sortable.flatMap((c) =>
            (["asc", "desc"] as const).map((dir) => (
              <option key={`${c.key}:${dir}`} value={`${c.key}:${dir}`}>
                {c.header} ({DIR_WORD[dir]})
              </option>
            )),
          )}
        </select>
      </div>
      <table className="sortable" role="table">
        <caption className="sr-only">{caption}</caption>
        <thead role="rowgroup">
          <tr role="row">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={c.align === "right" ? "right" : undefined}
                aria-sort={c.sortValue ? (sort?.key === c.key ? ARIA_SORT[sort.dir] : "none") : undefined}
              >
                {c.sortValue ? (
                  <button type="button" onClick={() => toggle(c.key)}>
                    {c.header}
                    <span className="sort-mark" aria-hidden="true">
                      {sort?.key === c.key ? (sort.dir === "asc" ? "↑" : "↓") : ""}
                    </span>
                  </button>
                ) : (
                  c.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody role="rowgroup">
          {sorted.map((row, i) => (
            <tr key={keys[i]} role="row" className={rowClassName?.(row)} onClick={onRowClick ? () => onRowClick(row) : undefined}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  role="cell"
                  data-label={c.header}
                  className={[c.align === "right" ? "right" : "", c.className ?? ""].join(" ").trim() || undefined}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
