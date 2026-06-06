export type Availability =
  | null
  | {
      mode: "status_only" | "exact_count";
      label?: "Available" | "Limited" | "Unavailable";
      count?: number;
    };

export type Product = {
  id: number;
  name: string;
  description: string;
  image_url: string;
  availability: Availability;
};

export type Makerspace = {
  name: string;
  slug: string;
  location: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
