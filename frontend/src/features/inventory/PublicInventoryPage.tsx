import { useParams } from "react-router-dom";

import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { ProductCard } from "./ProductCard";
import { usePublicInventory } from "./usePublicInventory";

function formatSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function LoadingState() {
  return (
    <div className="grid min-h-64 place-items-center">
      <Spinner />
    </div>
  );
}

function EmptyState() {
  return (
    <Card className="mx-auto max-w-lg text-center">
      <h2 className="text-xl font-semibold text-ink">No public items yet.</h2>
      <p className="mt-2 text-sm leading-6 text-ink/70">
        This makerspace has not shared any inventory items publicly.
      </p>
    </Card>
  );
}

function ErrorState({ error }: { error: Error }) {
  return (
    <Card className="mx-auto max-w-lg text-center">
      <h2 className="text-xl font-semibold text-ink">{error.message}</h2>
      <p className="mt-2 text-sm leading-6 text-ink/70">
        This makerspace may not exist or its public inventory is disabled.
      </p>
    </Card>
  );
}

export function PublicInventoryPage() {
  const { slug } = useParams();
  const makerspaceSlug = slug ?? "";
  const inventoryQuery = usePublicInventory(makerspaceSlug);
  const title = `${formatSlug(makerspaceSlug) || "Makerspace"} Inventory`;

  return (
    <main className="min-h-screen bg-bg">
      <header className="border-b border-line bg-tinker">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-8 sm:px-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-ink/70">
            Public Inventory
          </p>
          <h1 className="text-3xl font-bold text-ink sm:text-5xl">{title}</h1>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-8 sm:px-8 sm:py-12">
        {inventoryQuery.isLoading ? <LoadingState /> : null}

        {inventoryQuery.isError ? (
          <ErrorState error={inventoryQuery.error} />
        ) : null}

        {inventoryQuery.data && inventoryQuery.data.length === 0 ? (
          <EmptyState />
        ) : null}

        {inventoryQuery.data && inventoryQuery.data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {inventoryQuery.data.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
