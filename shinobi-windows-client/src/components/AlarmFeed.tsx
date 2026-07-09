import { useAlarmStore } from "../store/alarms";

export function AlarmFeed() {
  const alarms = useAlarmStore((state) => state.alarms);
  const clearAlarms = useAlarmStore((state) => state.clearAlarms);

  return (
    <section className="alarm-feed">
      <header className="alarm-feed-header">
        <div>
          <p className="eyebrow">Security Desk</p>
          <h3>Live Events</h3>
        </div>
        <button type="button" onClick={clearAlarms}>
          Clear
        </button>
      </header>
      <div className="alarm-list">
        {alarms.length === 0 ? (
          <p className="status-line">No events yet. Monitoring server activity...</p>
        ) : (
          alarms.map((alarm) => (
            <article
              key={alarm.id}
              className={`alarm-item alarm-${alarm.level}`}
            >
              <strong>{alarm.time}</strong>
              <span>{alarm.monitorName ?? alarm.monitorId}</span>
              <p>{alarm.message}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
