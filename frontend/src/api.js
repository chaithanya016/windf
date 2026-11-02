export async function api(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api/${path}${qs ? "?" + qs : ""}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}
