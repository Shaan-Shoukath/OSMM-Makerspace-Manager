import { apiGet, fetchJson } from "../../lib/api";
import type {
  Makerspace,
  PaginatedResponse,
  Product,
} from "../../types/inventory";

export const publicMakerspacesKey = ["public-makerspaces"] as const;

export const publicInventoryKey = (slug: string) =>
  ["public-inventory", slug] as const;

export async function fetchPublicMakerspaces(): Promise<Makerspace[]> {
  return apiGet<Makerspace[]>("/public/makerspaces/");
}

// The API is paginated (PAGE_SIZE 24). A public browse must show every public
// item, so we follow `next` links and accumulate all pages rather than
// silently dropping everything past the first page.
export async function fetchPublicInventory(slug: string): Promise<Product[]> {
  const products: Product[] = [];
  let page: PaginatedResponse<Product> | null = await apiGet<
    PaginatedResponse<Product>
  >(`/public/${slug}/inventory/`);

  while (page) {
    products.push(...page.results);
    page = page.next
      ? await fetchJson<PaginatedResponse<Product>>(page.next)
      : null;
  }

  return products;
}
