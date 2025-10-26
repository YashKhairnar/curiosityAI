import type { DataPoint } from "@/types/plotly";

const DEFAULT_BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;

export async function postExtractor(keywords: string[], base = DEFAULT_BACKEND_BASE) {
  const url = base ? `${base}/api/v1/extractor` : "http://:8000/api/v1/extractor";
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keywords }),
  });
  if (!res.ok) throw new Error(`Extractor request failed: ${res.status}`);
  return res.json() as Promise<unknown>;
}

export async function get3DPoints(base = DEFAULT_BACKEND_BASE): Promise<DataPoint[]> {
  const url = base ? `${base}/api/v1/get3Dpoints` : "http://10.0.5.250:8000/api/v1/get3Dpoints";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`get3Dpoints failed: ${res.status}`);
  const json = await res.json();
  const points: unknown = json;
  const arr = Array.isArray(points)
    ? points
    : points && typeof points === "object" && "results" in points
      ? (points as { results: DataPoint[] }).results
      : [];
  return arr as DataPoint[];
}
