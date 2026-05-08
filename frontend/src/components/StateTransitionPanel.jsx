const TRANSITIONS = {
  OPEN: ["INVESTIGATING", "RESOLVED"],
  INVESTIGATING: ["RESOLVED", "OPEN"],
  RESOLVED: ["CLOSED", "INVESTIGATING"],
  CLOSED: []
};

export default function StateTransitionPanel({ incident, onTransition }) {
  const options = TRANSITIONS[incident.status] || [];

  if (!options.length) {
    return <div className="helper">No further transitions available.</div>;
  }

  return (
    <div className="button-row">
      {options.map((target) => (
        <button
          key={target}
          className={target === "CLOSED" ? "button accent" : "button secondary"}
          onClick={() => onTransition(target)}
        >
          {target}
        </button>
      ))}
    </div>
  );
}
