import { useState } from "react";

export default function RCAForm({ onSubmit, busy }) {
  const [rootCause, setRootCause] = useState("");
  const [mitigation, setMitigation] = useState("");
  const [prevention, setPrevention] = useState("");
  const [submittedBy, setSubmittedBy] = useState("");

  const valid =
    rootCause.trim().length >= 20 &&
    mitigation.trim().length > 0 &&
    prevention.trim().length > 0 &&
    submittedBy.includes("@");

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    onSubmit({
      root_cause: rootCause,
      mitigation,
      prevention,
      submitted_by: submittedBy
    });
  };

  return (
    <form className="section" onSubmit={handleSubmit}>
      <div className="section-title">Root Cause Analysis</div>
      <textarea
        className="textarea"
        value={rootCause}
        onChange={(event) => setRootCause(event.target.value)}
        placeholder="Root cause (min 20 chars)"
      />
      <input
        className="input"
        value={mitigation}
        onChange={(event) => setMitigation(event.target.value)}
        placeholder="Mitigation"
      />
      <input
        className="input"
        value={prevention}
        onChange={(event) => setPrevention(event.target.value)}
        placeholder="Prevention"
      />
      <input
        className="input"
        value={submittedBy}
        onChange={(event) => setSubmittedBy(event.target.value)}
        placeholder="Submitted by (email)"
      />
      <button className="button accent" type="submit" disabled={!valid || busy}>
        {busy ? "Submitting..." : "Submit RCA"}
      </button>
    </form>
  );
}
