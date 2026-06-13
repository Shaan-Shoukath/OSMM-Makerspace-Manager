const STAGES = ["Requested", "Approved", "Collected", "Returned"] as const;

function statusStageIndex(status: string): number {
  switch (status) {
    case "accepted":
      return 1;
    case "issued":
    case "partially_returned":
      return 2;
    case "returned":
    case "closed_with_issue":
      return 3;
    case "draft":
    case "pending_approval":
    case "rejected":
    default:
      return 0;
  }
}

export function statusStageLabel(status: string): string {
  if (status === "rejected") return "Rejected";
  return STAGES[statusStageIndex(status)] ?? STAGES[0];
}

function StepMarker({
  step,
  state,
  rejected,
}: {
  step: number;
  state: "completed" | "current" | "upcoming";
  rejected: boolean;
}) {
  if (rejected && step === 0) {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-accent bg-surface text-xs font-semibold text-accent">
        1
      </span>
    );
  }

  if (state === "upcoming") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-xs font-semibold text-muted">
        {step + 1}
      </span>
    );
  }

  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-accent bg-accent text-xs font-semibold text-white">
      {step + 1}
    </span>
  );
}

function RejectedBadge() {
  return (
    <span className="rounded-full border border-danger bg-danger/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-danger">
      Rejected
    </span>
  );
}

export function StatusStepper({ status }: { status: string }) {
  const rejected = status === "rejected";
  const activeIndex = rejected ? 0 : statusStageIndex(status);

  return (
    <nav
      aria-label={`Request status: ${statusStageLabel(status)}`}
      className="w-full"
    >
      <ol className="grid grid-cols-4 items-start gap-0">
        {STAGES.map((stage, index) => {
          const state =
            index < activeIndex
              ? "completed"
              : index === activeIndex
                ? "current"
                : "upcoming";
          const active = state === "completed" || state === "current";
          const lineActive = index < activeIndex;

          return (
            <li
              className="relative flex min-w-0 flex-col items-center text-center"
              key={stage}
            >
              {index < STAGES.length - 1 ? (
                <span
                  aria-hidden="true"
                  className={`absolute left-1/2 top-3 w-full border-t ${
                    lineActive ? "border-accent" : "border-line"
                  }`}
                />
              ) : null}
              <span className="relative z-10 bg-surface px-1">
                <StepMarker step={index} state={state} rejected={rejected} />
              </span>
              <span
                aria-current={state === "current" ? "step" : undefined}
                className={`mt-1 min-w-0 text-[11px] font-medium leading-tight ${
                  active ? "text-accent" : "text-muted"
                }`}
              >
                {stage}
              </span>
              {rejected && index === 0 ? (
                <span className="mt-1">
                  <RejectedBadge />
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
