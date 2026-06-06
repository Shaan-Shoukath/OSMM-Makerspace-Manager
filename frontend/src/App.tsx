import { Link, Route, Routes } from "react-router-dom";

import { Card } from "./components/ui/Card";
import { Spinner } from "./components/ui/Spinner";
import { PublicInventoryPage } from "./features/inventory/PublicInventoryPage";
import { usePublicMakerspaces } from "./features/inventory/usePublicInventory";

function LandingPage() {
  const makerspacesQuery = usePublicMakerspaces();

  return (
    <main className="min-h-screen bg-bg px-6 py-12">
      <section className="mx-auto flex max-w-5xl flex-col gap-8">
        <div className="h-2 w-24 rounded-full bg-tinker" />
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-ink/60">
            TinkerSpace
          </p>
          <h1 className="text-4xl font-bold text-ink sm:text-5xl">
            Public Inventory
          </h1>
          <p className="max-w-xl text-base leading-7 text-ink/70">
            Browse shared makerspace items that are available to the public.
          </p>
        </div>

        {makerspacesQuery.isLoading ? (
          <div className="grid min-h-32 place-items-center">
            <Spinner />
          </div>
        ) : null}

        {makerspacesQuery.isError ? (
          <Card className="max-w-lg">
            <h2 className="text-xl font-semibold text-ink">
              Makerspaces are unavailable
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink/70">
              The public makerspace directory could not be loaded.
            </p>
          </Card>
        ) : null}

        {makerspacesQuery.data && makerspacesQuery.data.length === 0 ? (
          <Card className="max-w-lg">
            <h2 className="text-xl font-semibold text-ink">
              No public makerspaces yet
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink/70">
              Public inventory appears here after a makerspace is enabled.
            </p>
          </Card>
        ) : null}

        {makerspacesQuery.data && makerspacesQuery.data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {makerspacesQuery.data.map((makerspace) => (
              <Link
                key={makerspace.slug}
                className="rounded-lg border border-line bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ink focus:ring-offset-2"
                to={`/m/${makerspace.slug}`}
              >
                <h2 className="text-xl font-semibold text-ink">
                  {makerspace.name}
                </h2>
                {makerspace.location ? (
                  <p className="mt-2 text-sm text-ink/60">
                    {makerspace.location}
                  </p>
                ) : null}
                <p className="mt-4 text-sm font-semibold text-ink">
                  Open inventory
                </p>
              </Link>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-bg px-6">
      <div className="text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-ink/50">
          404
        </p>
        <h1 className="mt-2 text-3xl font-bold text-ink">Page not found</h1>
      </div>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/m/:slug" element={<PublicInventoryPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
