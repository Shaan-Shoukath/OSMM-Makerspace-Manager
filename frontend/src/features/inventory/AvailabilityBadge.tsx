import { Badge } from "../../components/ui/Badge";
import type { Availability } from "../../types/inventory";

type AvailabilityBadgeProps = {
  availability: Availability;
};

function toneForAvailability(
  label: NonNullable<Availability>["label"],
): "success" | "warn" | "danger" | "neutral" {
  if (label === "Limited") {
    return "warn";
  }

  if (label === "Unavailable") {
    return "danger";
  }

  if (label === "Available") {
    return "success";
  }

  return "neutral";
}

function textForAvailability(availability: NonNullable<Availability>): string {
  const label = availability.label;

  if (availability.mode === "exact_count" && availability.count != null) {
    if (label === "Unavailable") {
      return "Unavailable";
    }

    if (label === "Limited") {
      return `${availability.count} limited`;
    }

    return `${availability.count} available`;
  }

  return label ?? "Available";
}

export function AvailabilityBadge({ availability }: AvailabilityBadgeProps) {
  if (availability === null) {
    return null;
  }

  return (
    <Badge tone={toneForAvailability(availability.label)}>
      {textForAvailability(availability)}
    </Badge>
  );
}
