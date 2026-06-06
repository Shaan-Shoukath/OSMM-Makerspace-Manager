import { useQuery } from "@tanstack/react-query";

import {
  fetchPublicInventory,
  fetchPublicMakerspaces,
  publicInventoryKey,
  publicMakerspacesKey,
} from "./api";

export function usePublicMakerspaces() {
  return useQuery({
    queryKey: publicMakerspacesKey,
    queryFn: fetchPublicMakerspaces,
  });
}

export function usePublicInventory(slug: string) {
  return useQuery({
    queryKey: publicInventoryKey(slug),
    queryFn: () => fetchPublicInventory(slug),
  });
}
