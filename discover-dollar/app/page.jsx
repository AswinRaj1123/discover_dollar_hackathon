"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  approveListing,
  claimListing,
  getAppData,
  postShift,
  rejectListing,
  unclaimListing,
  withdrawListing,
} from "./lib/api";

function formatDate(value) {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatTimeRange(shift) {
  return `${formatDate(shift.start)} – ${new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(shift.end))}`;
}

function getStaffName(staff, id) {
  return staff.find((person) => person.id === id)?.name || id || "Unassigned";
}

function StatusPill({ status }) {
  return <span className={`status-pill status-${status.toLowerCase()}`}>{status}</span>;
}

function ActionButton({ busy, children, ...props }) {
  return (
    <button disabled={busy} {...props}>
      {busy ? "Working..." : children}
    </button>
  );
}

function RecentActivity({ history, staff }) {
  const recentEvents = [...history].reverse().slice(0, 5);

  return (
    <section className="panel history-panel">
      <div className="section-heading">
        <div><p className="eyebrow">Recent activity</p><h2>Action history</h2></div>
        <span className="count-label">Latest {recentEvents.length}</span>
      </div>
      {recentEvents.length === 0 ? (
        <div className="empty-inline">No actions have been recorded yet.</div>
      ) : (
        <div className="history-list">
          {recentEvents.map((event) => (
            <div className="history-row" key={event.id}>
              <div>
                <strong>{event.action.replaceAll("_", " ")}</strong>
                <span>
                  {event.actor_id ? getStaffName(staff, event.actor_id) : "System"} ·{" "}
                  {event.entity_id || "Application"}
                </span>
              </div>
              <div>
                <span>{event.outcome || event.details?.outcome || "RECORDED"}</span>
                <time>{event.created_at}</time>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ShiftCard({ shift, ownerName, listing, currentUser, staff, onAction, actionBusy }) {
  const isOwner = shift.assigned_to === currentUser.id;
  const isManager = currentUser.role === "MANAGER";
  const canPost = isOwner && !isManager && !listing;
  const canWithdraw = isOwner && listing?.status === "OPEN";
  const canClaim = !isOwner && !isManager && listing?.status === "OPEN";
  const canUnclaim = listing?.status === "CLAIMED" && listing.claimed_by === currentUser.id;

  return (
    <article className="shift-card">
      <div className="card-heading">
        <div>
          <span className="shift-id">{shift.id}</span>
          <h3>{formatTimeRange(shift)}</h3>
        </div>
        {listing ? <StatusPill status={listing.status} /> : <span className="status-pill status-assigned">ASSIGNED</span>}
      </div>
      <div className="shift-meta">
        <span>Owner: {ownerName}</span>
        {shift.required_certification ? (
          <span>Certification: {shift.required_certification}</span>
        ) : (
          <span>No certification required</span>
        )}
      </div>
      {listing?.status === "OPEN" && !isOwner && !isManager && (
        <p className="eligibility-note">
          Eligibility: checked by the backend when you claim
        </p>
      )}
      {listing?.status === "CLAIMED" && (
        <p className="muted-note">
          Claimed by {getStaffName(staff, listing.claimed_by)}
        </p>
      )}
      <div className="card-actions">
        {canPost && (
          <ActionButton
            busy={actionBusy === `post-${shift.id}`}
            onClick={() => onAction("post", shift.id)}
          >
            Post for swap
          </ActionButton>
        )}
        {canWithdraw && (
          <ActionButton
            className="button-secondary"
            busy={actionBusy === `withdraw-${listing.id}`}
            onClick={() => onAction("withdraw", listing.id)}
          >
            Withdraw
          </ActionButton>
        )}
        {canClaim && (
          <ActionButton
            busy={actionBusy === `claim-${listing.id}`}
            onClick={() => onAction("claim", listing.id)}
          >
            Claim shift
          </ActionButton>
        )}
        {canUnclaim && (
          <ActionButton
            className="button-secondary"
            busy={actionBusy === `unclaim-${listing.id}`}
            onClick={() => onAction("unclaim", listing.id)}
          >
            Unclaim
          </ActionButton>
        )}
      </div>
    </article>
  );
}

export default function Home() {
  const [data, setData] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [hasEntered, setHasEntered] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const nextData = await getAppData();
      setData(nextData);
      setSelectedId((current) => current || nextData.staff[0]?.id || "");
      setError(null);
    } catch (loadError) {
      setError({ message: loadError.message, reasons: loadError.reasons || [] });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial data synchronization is intentionally performed once on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [loadData]);

  const currentUser = data?.staff.find((person) => person.id === selectedId);
  const shiftsById = useMemo(
    () => new Map((data?.shifts || []).map((shift) => [shift.id, shift])),
    [data?.shifts],
  );
  const activeListings = useMemo(
    () => new Map(
      (data?.listings || [])
        .filter((listing) => listing.status === "OPEN" || listing.status === "CLAIMED")
        .map((listing) => [listing.shift_id, listing]),
    ),
    [data?.listings],
  );
  const ownShifts = useMemo(
    () => (data?.shifts || []).filter((shift) => shift.assigned_to === selectedId),
    [data?.shifts, selectedId],
  );
  const openListings = useMemo(
    () => (data?.listings || []).filter((listing) => {
      const shift = shiftsById.get(listing.shift_id);
      return listing.status === "OPEN" && shift?.assigned_to !== selectedId;
    }),
    [data?.listings, shiftsById, selectedId],
  );
  const claimedListings = useMemo(
    () => (data?.listings || []).filter((listing) => listing.status === "CLAIMED"),
    [data?.listings],
  );
  const isManager = currentUser?.role === "MANAGER";

  if (data && !hasEntered) {
    return (
      <main className="welcome-shell">
        <section className="welcome-card">
          <div className="brand-mark"><span /> ShiftSwap</div>
          <p className="eyebrow">Clinic operations</p>
          <h1>Who are you?</h1>
          <p className="welcome-copy">
            Choose a staff member or manager to enter ShiftSwap.
          </p>
          <label className="person-picker">
            <span>Select your profile</span>
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {(data.staff || []).map((person) => (
                <option value={person.id} key={person.id}>
                  {person.name} · {person.role}
                </option>
              ))}
            </select>
          </label>
          <button className="welcome-button" onClick={() => setHasEntered(true)}>
            Continue to ShiftSwap
          </button>
          <p className="welcome-note">Your profile controls the actions available to you.</p>
        </section>
      </main>
    );
  }

  async function handleAction(action, id) {
    if (!currentUser) return;
    setActionBusy(`${action}-${id}`);
    setError(null);
    setSuccess("");
    try {
      const actions = {
        post: () => postShift(id, currentUser.id),
        withdraw: () => withdrawListing(id, currentUser.id),
        claim: () => claimListing(id, currentUser.id),
        unclaim: () => unclaimListing(id, currentUser.id),
        approve: () => approveListing(id, currentUser.id),
        reject: () => rejectListing(id, currentUser.id),
      };
      await actions[action]();
      await loadData();
      setSuccess(`${action[0].toUpperCase()}${action.slice(1)} completed.`);
    } catch (actionError) {
      setError({ message: actionError.message, reasons: actionError.reasons || [] });
    } finally {
      setActionBusy("");
    }
  }

  if (loading && !data) {
    return <main className="loading-screen"><span className="loader" />Loading ShiftSwap…</main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-mark"><span /> ShiftSwap</div>
          <p className="eyebrow">Clinic operations</p>
        </div>
        <div className="topbar-actions">
          <div className="connection-status">
            <span className={`connection-dot ${data ? "is-online" : ""}`} />
            {data ? "Connected" : "Unavailable"}
          </div>
          <button
            className="button-secondary logout-button"
            onClick={() => {
              setHasEntered(false);
              setError(null);
              setSuccess("");
            }}
          >
            Log out
          </button>
        </div>
      </header>

      <section className="intro-row">
        <div>
          <p className="eyebrow">Today&apos;s workspace</p>
          <h2>Manage shift coverage clearly.</h2>
          <p>Post your shifts, review available coverage, and keep every decision visible.</p>
        </div>
        <div className="signed-in-as">
          Signed in as <strong>{currentUser?.name}</strong>
          <span>{currentUser?.role}</span>
        </div>
      </section>

      {error && (
        <section className="feedback feedback-error" role="alert">
          <strong>{error.message}</strong>
          {error.reasons?.length > 0 && (
            <ul>
              {error.reasons.map((reason, index) => (
                <li key={`${reason.rule}-${index}`}>
                  <strong>{reason.rule}:</strong> {reason.message}
                  {reason.conflicting_shift && <span> ({reason.conflicting_shift})</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {success && <section className="feedback feedback-success">{success}</section>}

      {!data ? (
        <section className="empty-state">
          <h2>Connect to the backend to continue</h2>
          <p>Start FastAPI on port 8000, then try again.</p>
          <button onClick={loadData}>Retry connection</button>
        </section>
      ) : (
        <>
          <section className="summary-grid" aria-label="Shift summary">
                <div><span>My shifts</span><strong>{ownShifts.length}</strong><small>Assigned to you</small></div>
                <div><span>Open listings</span><strong>{openListings.length}</strong><small>Available to review</small></div>
                <div><span>History events</span><strong>{data.history.length}</strong><small>Recorded actions</small></div>
                <div><span>Role</span><strong>{currentUser?.role || "—"}</strong><small>Current access</small></div>
          </section>

          <div className="content-grid">
            <section className="panel">
              <div className="section-heading">
                <div><p className="eyebrow">Your schedule</p><h2>My shifts</h2></div>
                <span className="count-label">{ownShifts.length} shifts</span>
              </div>
              {ownShifts.length === 0 ? (
                <div className="empty-inline">No shifts are assigned to this person.</div>
              ) : (
                <div className="card-list">
                  {ownShifts.map((shift) => (
                    <ShiftCard
                      key={shift.id}
                      shift={shift}
                      ownerName={getStaffName(data.staff, shift.assigned_to)}
                      listing={activeListings.get(shift.id)}
                      currentUser={currentUser}
                      staff={data.staff}
                      onAction={handleAction}
                      actionBusy={actionBusy}
                    />
                  ))}
                </div>
              )}
            </section>

            <section className="panel">
              <div className="section-heading">
                <div><p className="eyebrow">Coverage marketplace</p><h2>Open listings</h2></div>
                <span className="count-label">{openListings.length} available</span>
              </div>
              {isManager && <p className="notice">Managers can review claims, but cannot claim or post shifts.</p>}
              {openListings.length === 0 ? (
                <div className="empty-inline">There are no open listings from other staff.</div>
              ) : (
                <div className="card-list">
                  {openListings.map((listing) => {
                    const shift = shiftsById.get(listing.shift_id);
                    return (
                      <ShiftCard
                        key={listing.id}
                        shift={shift}
                        ownerName={getStaffName(data.staff, shift.assigned_to)}
                        listing={listing}
                        currentUser={currentUser}
                        staff={data.staff}
                        onAction={handleAction}
                        actionBusy={actionBusy}
                      />
                    );
                  })}
                </div>
              )}
            </section>
          </div>

          {isManager && (
            <section className="panel manager-panel">
              <div className="section-heading">
                <div><p className="eyebrow">Manager review</p><h2>Claimed listings</h2></div>
                <span className="count-label">{claimedListings.length} pending</span>
              </div>
              {claimedListings.length === 0 ? (
                <div className="empty-inline">No claims need review.</div>
              ) : (
                <div className="card-list">
                  {claimedListings.map((listing) => {
                    const shift = shiftsById.get(listing.shift_id);
                    return (
                      <article className="review-card" key={listing.id}>
                        <div>
                          <span className="shift-id">{shift.id}</span>
                          <h3>{formatTimeRange(shift)}</h3>
                          <p>{getStaffName(data.staff, shift.assigned_to)} → {getStaffName(data.staff, listing.claimed_by)}</p>
                        </div>
                        <div className="card-actions">
                          <button
                            disabled={Boolean(actionBusy)}
                            onClick={() => handleAction("approve", listing.id)}
                          >
                            {actionBusy === `approve-${listing.id}` ? "Working..." : "Approve"}
                          </button>
                          <button
                            className="button-secondary"
                            disabled={Boolean(actionBusy)}
                            onClick={() => handleAction("reject", listing.id)}
                          >
                            {actionBusy === `reject-${listing.id}` ? "Working..." : "Reject"}
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          <RecentActivity history={data.history} staff={data.staff} />
        </>
      )}
    </main>
  );
}
