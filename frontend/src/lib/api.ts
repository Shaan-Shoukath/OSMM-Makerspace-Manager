export const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

const HMAC_CLIENT_ID = import.meta.env.VITE_HMAC_CLIENT_ID ?? "";
const HMAC_SECRET = import.meta.env.VITE_HMAC_SECRET ?? "";

function messageForStatus(status: number): string {
  if (status === 401) {
    return "Inventory client is not authorized";
  }

  if (status === 404) {
    return "Makerspace not found";
  }

  if (status >= 500) {
    return "Inventory service is unavailable";
  }

  return "Unable to load inventory";
}

async function hmacSha256Hex(message: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(message));

  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function signedHeaders(url: string): Promise<HeadersInit> {
  if (!HMAC_CLIENT_ID || !HMAC_SECRET) {
    return {};
  }

  const timestamp = Math.floor(Date.now() / 1000).toString();
  const parsedUrl = new URL(url, window.location.origin);
  const canonicalPath = `${parsedUrl.pathname}${parsedUrl.search}`;
  const message = ["GET", canonicalPath, timestamp, ""].join("\n");

  return {
    "X-Client-Id": HMAC_CLIENT_ID,
    "X-Timestamp": timestamp,
    "X-Signature": await hmacSha256Hex(message, HMAC_SECRET),
  };
}

export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: await signedHeaders(url),
  });

  if (!response.ok) {
    throw new Error(`${messageForStatus(response.status)} (${response.status})`);
  }

  return (await response.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return fetchJson<T>(`${API_URL}${path}`);
}
