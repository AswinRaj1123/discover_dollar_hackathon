const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://discover-dollar-shiftswap.onrender.com";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "The request could not be completed.");
    error.reasons = data.reasons || [];
    throw error;
  }
  return data;
}

export function getAppData() {
  return Promise.all([
    request("/api/health"),
    request("/api/staff"),
    request("/api/shifts"),
    request("/api/listings"),
    request("/api/history"),
  ]).then(([health, staff, shifts, listings, history]) => ({
    health,
    staff: staff.staff || [],
    shifts: shifts.shifts || [],
    listings: listings.listings || [],
    history: history.history || [],
  }));
}

function actorBody(actorId) {
  return JSON.stringify({ actor_id: actorId });
}

export function postShift(shiftId, actorId) {
  return request(`/api/shifts/${shiftId}/listings`, {
    method: "POST",
    body: actorBody(actorId),
  });
}

export function withdrawListing(listingId, actorId) {
  return request(`/api/listings/${listingId}/withdraw`, {
    method: "POST",
    body: actorBody(actorId),
  });
}

export function claimListing(listingId, actorId) {
  return request(`/api/listings/${listingId}/claim`, {
    method: "POST",
    body: actorBody(actorId),
  });
}

export function unclaimListing(listingId, actorId) {
  return request(`/api/listings/${listingId}/unclaim`, {
    method: "POST",
    body: actorBody(actorId),
  });
}

export function approveListing(listingId, actorId) {
  return request(`/api/listings/${listingId}/approve`, {
    method: "POST",
    body: actorBody(actorId),
  });
}

export function rejectListing(listingId, actorId) {
  return request(`/api/listings/${listingId}/reject`, {
    method: "POST",
    body: actorBody(actorId),
  });
}
