import { tenantPublicRequest } from "../../lib/api";

export type PublicToolLoanResult = {
  public_token: string;
  status: string;
  target_type: string;
  target_label: string;
  items: { product_name: string; quantity: number }[];
};

export function checkoutTool(
  slug: string,
  identifier: string,
  payload: string,
) {
  return tenantPublicRequest<PublicToolLoanResult>(
    slug,
    `/public/${slug}/tools/checkout`,
    {
      method: "POST",
      body: JSON.stringify({ identifier, payload }),
    },
  );
}

export function returnTool(slug: string, identifier: string, payload: string) {
  return tenantPublicRequest<PublicToolLoanResult>(
    slug,
    `/public/${slug}/tools/return`,
    {
      method: "POST",
      body: JSON.stringify({ identifier, payload }),
    },
  );
}
