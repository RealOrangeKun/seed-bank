import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDatasets } from "@/features/datasets/api";
import { useModels } from "@/features/models/api";
import { useSeedTypes, useSuppliers } from "@/features/catalog/api";
import type { ModelKind, ModelStatus } from "@/lib/api/types";

export interface SelectOption {
  value: string;
  label: string;
  hint?: string;
}

interface ResourceSelectProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  /** Render a leading "none" choice that maps to the empty string. */
  includeNone?: boolean;
  noneLabel?: string;
  loading?: boolean;
  disabled?: boolean;
}

// Radix forbids an empty-string <SelectItem> value, so the "none" choice uses a
// sentinel and is mapped back to "" at the boundary.
const NONE = "__none__";

/**
 * Dropdown over a list of resources. Emits the selected id (or "" when the
 * optional none-choice is picked) — callers store the id, users see a label.
 */
export function ResourceSelect({
  id,
  value,
  onChange,
  options,
  placeholder = "Select…",
  includeNone = false,
  noneLabel = "— None —",
  loading = false,
  disabled = false,
}: ResourceSelectProps) {
  const selectValue = value ? value : includeNone ? NONE : undefined;
  const isEmpty = !loading && options.length === 0;

  return (
    <Select
      value={selectValue}
      onValueChange={(next) => onChange(next === NONE ? "" : next)}
      disabled={disabled || loading || isEmpty}
    >
      <SelectTrigger id={id}>
        <SelectValue
          placeholder={loading ? "Loading…" : isEmpty ? "None available" : placeholder}
        />
      </SelectTrigger>
      <SelectContent>
        {includeNone ? <SelectItem value={NONE}>{noneLabel}</SelectItem> : null}
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
            {opt.hint ? (
              <span className="ml-1 text-muted-foreground">· {opt.hint}</span>
            ) : null}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// ── Entity-specific selectors ────────────────────────────────────────────────

interface BaseSelectProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  includeNone?: boolean;
  disabled?: boolean;
}

export function SeedTypeSelect({ includeNone = true, ...props }: BaseSelectProps) {
  const query = useSeedTypes();
  const options: SelectOption[] = (query.data ?? []).map((s) => ({
    value: s.id,
    label: s.display_name,
  }));
  return (
    <ResourceSelect
      {...props}
      options={options}
      loading={query.isPending}
      placeholder="Select a seed type"
      includeNone={includeNone}
      noneLabel="Any seed type"
    />
  );
}

export function SupplierSelect({ includeNone = true, ...props }: BaseSelectProps) {
  const query = useSuppliers();
  const options: SelectOption[] = (query.data ?? []).map((s) => ({
    value: s.id,
    label: s.name,
    hint: s.is_global ? "global" : "private",
  }));
  return (
    <ResourceSelect
      {...props}
      options={options}
      loading={query.isPending}
      placeholder="Select a supplier"
      includeNone={includeNone}
      noneLabel="No supplier"
    />
  );
}

interface ModelSelectProps extends BaseSelectProps {
  kind?: ModelKind;
  status?: ModelStatus;
  noneLabel?: string;
}

export function ModelSelect({
  kind,
  status,
  includeNone = false,
  noneLabel,
  ...props
}: ModelSelectProps) {
  const query = useModels({ page: 1, pageSize: 100, kind, status });
  const options: SelectOption[] = (query.data?.data ?? []).map((m) => ({
    value: m.id,
    label: `${m.name} ${m.version}`,
    hint: m.status,
  }));
  return (
    <ResourceSelect
      {...props}
      options={options}
      loading={query.isPending}
      placeholder="Select a model"
      includeNone={includeNone}
      noneLabel={noneLabel ?? "Auto (traffic router)"}
    />
  );
}

export function DatasetSelect({ includeNone = false, ...props }: BaseSelectProps) {
  const query = useDatasets({ page: 1, pageSize: 100 });
  const options: SelectOption[] = (query.data?.data ?? []).map((d) => ({
    value: d.id,
    label: d.name,
  }));
  return (
    <ResourceSelect
      {...props}
      options={options}
      loading={query.isPending}
      placeholder="Select a dataset"
      includeNone={includeNone}
    />
  );
}
