export function Spinner() {
  return (
    <div role="status" className="inline-flex items-center gap-3 text-ink/70">
      <span className="h-8 w-8 animate-spin rounded-full border-4 border-line border-t-tinker" />
      <span className="sr-only">Loading</span>
    </div>
  );
}
