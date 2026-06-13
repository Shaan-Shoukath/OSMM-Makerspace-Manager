import type { ReactNode } from "react";

import { Modal } from "../../../components/ui";
import type { Makerspace } from "./shared";

export type StaffForm = {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role: "space_manager" | "inventory_manager" | "guest_admin" | "print_manager";
  makerspace_id: string;
};
export type RestrictForm = { status: "restricted" | "suspended"; reason: string };
export type MakerspaceForm = { name: string; public_code: string; slug: string; location: string };

const roleOptions = [
  ["space_manager", "Space Manager"],
  ["inventory_manager", "Inventory Manager"],
  ["guest_admin", "Guest Admin"],
  ["print_manager", "Print Manager"],
] as const;

export function AddStaffModal({
  open,
  form,
  makerspaces,
  pending,
  error,
  onChange,
  onClose,
  onSubmit,
}: {
  open: boolean;
  form: StaffForm;
  makerspaces: Makerspace[];
  pending: boolean;
  error: unknown;
  onChange: (form: StaffForm) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  const errors = validationErrors(error);
  // Password is required: the API does not return an auto-generated one, so a
  // blank password would create an account nobody can sign into.
  const disabled = pending || !form.username.trim() || !form.makerspace_id || !form.password;
  return (
    <Modal open={open} onClose={onClose} title="Add staff" footer={<ModalActions pending={pending} disabled={disabled} onClose={onClose} onSubmit={onSubmit} />}>
      <form className="grid gap-3 text-sm" onSubmit={(event) => { event.preventDefault(); if (!disabled) onSubmit(); }}>
        <Field label="Username" error={errors.username}>
          <input className="desk-input w-full" value={form.username} onChange={(event) => onChange({ ...form, username: event.target.value })} />
        </Field>
        <Field label="Email" error={errors.email}>
          <input className="desk-input w-full" type="email" value={form.email} onChange={(event) => onChange({ ...form, email: event.target.value })} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="First name" error={errors.first_name}>
            <input className="desk-input w-full" value={form.first_name} onChange={(event) => onChange({ ...form, first_name: event.target.value })} />
          </Field>
          <Field label="Last name" error={errors.last_name}>
            <input className="desk-input w-full" value={form.last_name} onChange={(event) => onChange({ ...form, last_name: event.target.value })} />
          </Field>
        </div>
        <Field label="Password" hint="Required — share it with the new staff member." error={errors.password}>
          <input className="desk-input w-full" type="password" value={form.password} onChange={(event) => onChange({ ...form, password: event.target.value })} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Role" error={errors.role}>
            <select className="desk-input w-full" value={form.role} onChange={(event) => onChange({ ...form, role: event.target.value as StaffForm["role"] })}>
              {roleOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </Field>
          <Field label="Makerspace" error={errors.makerspace_id}>
            <select className="desk-input w-full" value={form.makerspace_id} onChange={(event) => onChange({ ...form, makerspace_id: event.target.value })}>
              <option value="">Select makerspace</option>
              {makerspaces.map((space) => <option key={space.id} value={space.id}>{space.name}</option>)}
            </select>
          </Field>
        </div>
        <GeneralError error={error} errors={errors} />
      </form>
    </Modal>
  );
}

export function RestrictUserModal({
  open,
  userLabel,
  form,
  pending,
  error,
  onChange,
  onClose,
  onSubmit,
}: {
  open: boolean;
  userLabel: string;
  form: RestrictForm;
  pending: boolean;
  error: unknown;
  onChange: (form: RestrictForm) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  const errors = validationErrors(error);
  const disabled = pending || !form.reason.trim();
  return (
    <Modal open={open} onClose={onClose} title={`Restrict ${userLabel}`} footer={<ModalActions pending={pending} disabled={disabled} submitLabel="Apply" onClose={onClose} onSubmit={onSubmit} />}>
      <form className="grid gap-3 text-sm" onSubmit={(event) => { event.preventDefault(); if (!disabled) onSubmit(); }}>
        <Field label="Status" error={errors.status}>
          <select className="desk-input w-full" value={form.status} onChange={(event) => onChange({ ...form, status: event.target.value as RestrictForm["status"] })}>
            <option value="restricted">Restricted</option>
            <option value="suspended">Suspended</option>
          </select>
        </Field>
        <Field label="Reason" error={errors.reason}>
          <textarea className="desk-input h-24 w-full" value={form.reason} onChange={(event) => onChange({ ...form, reason: event.target.value })} />
        </Field>
        <GeneralError error={error} errors={errors} />
      </form>
    </Modal>
  );
}

export function CreateMakerspaceModal({
  open,
  form,
  pending,
  error,
  onChange,
  onClose,
  onSubmit,
}: {
  open: boolean;
  form: MakerspaceForm;
  pending: boolean;
  error: unknown;
  onChange: (form: MakerspaceForm) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  const errors = validationErrors(error);
  const disabled = pending || !form.name.trim() || !form.public_code.trim() || !form.slug.trim();
  return (
    <Modal open={open} onClose={onClose} title="Create makerspace" footer={<ModalActions pending={pending} disabled={disabled} onClose={onClose} onSubmit={onSubmit} />}>
      <form className="grid gap-3 text-sm" onSubmit={(event) => { event.preventDefault(); if (!disabled) onSubmit(); }}>
        <Field label="Name" error={errors.name}>
          <input className="desk-input w-full" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Public code" error={errors.public_code}>
            <input className="desk-input w-full uppercase" maxLength={4} value={form.public_code} onChange={(event) => onChange({ ...form, public_code: event.target.value.toUpperCase() })} />
          </Field>
          <Field label="Slug" error={errors.slug}>
            <input className="desk-input w-full" value={form.slug} onChange={(event) => onChange({ ...form, slug: event.target.value })} />
          </Field>
        </div>
        <Field label="Location" error={errors.location}>
          <input className="desk-input w-full" value={form.location} onChange={(event) => onChange({ ...form, location: event.target.value })} />
        </Field>
        <GeneralError error={error} errors={errors} />
      </form>
    </Modal>
  );
}

function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <label className="grid gap-1 font-semibold text-ink">
      <span>{label}</span>
      {children}
      {hint ? <span className="text-xs font-normal text-muted">{hint}</span> : null}
      {error ? <span className="text-xs font-normal text-danger">{error}</span> : null}
    </label>
  );
}

function ModalActions({
  pending,
  disabled,
  submitLabel = "Save",
  onClose,
  onSubmit,
}: {
  pending: boolean;
  disabled: boolean;
  submitLabel?: string;
  onClose: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="desk-actions flex flex-wrap justify-end gap-2">
      <button className="desk-button" type="button" disabled={pending} onClick={onClose}>Cancel</button>
      <button className="desk-button-primary" type="button" disabled={disabled} onClick={onSubmit}>{submitLabel}</button>
    </div>
  );
}

function GeneralError({ error, errors }: { error: unknown; errors: Record<string, string> }) {
  const message = error instanceof Error ? error.message : "";
  if (!message || Object.keys(errors).length) return null;
  return <p className="text-sm text-danger">{message}</p>;
}

function validationErrors(error: unknown) {
  if (!error || !(error instanceof Error)) return {};
  try {
    const parsed = JSON.parse(error.message) as Record<string, unknown>;
    return flattenErrors(parsed);
  } catch {
    return {};
  }
}

function flattenErrors(value: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      Array.isArray(item) ? item.join(" ") : typeof item === "string" ? item : JSON.stringify(item),
    ]),
  );
}
