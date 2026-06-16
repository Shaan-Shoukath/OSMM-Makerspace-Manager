import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Badge } from "../../components/ui";
import { staffRequest } from "../../lib/api";
import { Panel, type Makerspace, useStaffGet } from "./StaffPanels";

type Props = {
  makerspace: Makerspace;
  isSuperadmin: boolean;
};

export function MakerspaceSettingsPanel({ makerspace, isSuperadmin }: Props) {
  const queryClient = useQueryClient();
  const settings = useStaffGet<Makerspace>(
    ["makerspace-settings", makerspace.id],
    `/admin/makerspaces/${makerspace.id}`,
  );
  const superadminAccessEnabled =
    settings.data?.superadmin_access_enabled ?? makerspace.superadmin_access_enabled ?? true;
  const reEnableBlocked = isSuperadmin && !superadminAccessEnabled;

  const updateAccess = useMutation({
    mutationFn: (next: boolean) =>
      staffRequest<Makerspace>(`/admin/makerspaces/${makerspace.id}`, {
        method: "PATCH",
        body: JSON.stringify({ superadmin_access_enabled: next }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["makerspace-settings", makerspace.id] });
      queryClient.invalidateQueries({ queryKey: ["makerspaces"] });
      queryClient.invalidateQueries({ queryKey: ["staff", "makerspaces"] });
    },
  });

  const nextValue = !superadminAccessEnabled;
  const disabled = settings.isLoading || updateAccess.isPending || reEnableBlocked;

  return (
    <Panel title="Makerspace settings">
      <div className="rounded-md border border-line bg-bg p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="grid max-w-2xl gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-ink">Superadmin access</h3>
              <Badge tone={superadminAccessEnabled ? "success" : "warn"}>
                {superadminAccessEnabled ? "On" : "Off"}
              </Badge>
            </div>
            <p className="text-sm text-muted">
              When off, this makerspace is hidden from the superadmin's reports, dashboards, audit,
              and admin lists. It does not revoke the superadmin's platform/database access. Only
              the makerspace admin can turn it back on.
            </p>
            {reEnableBlocked ? (
              <p className="text-sm text-muted">Re-enable is controlled by the makerspace admin.</p>
            ) : null}
            {updateAccess.error ? <p className="text-sm text-danger">{updateAccess.error.message}</p> : null}
          </div>
          <button
            className={superadminAccessEnabled ? "desk-button" : "desk-button-primary"}
            type="button"
            disabled={disabled}
            onClick={() => updateAccess.mutate(nextValue)}
          >
            {updateAccess.isPending
              ? "Saving..."
              : superadminAccessEnabled
                ? "Turn off access"
                : "Turn on access"}
          </button>
        </div>
      </div>
    </Panel>
  );
}
