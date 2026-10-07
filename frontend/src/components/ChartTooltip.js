import React from 'react';

// Shared tooltip: text in ink colors, a small colored swatch carries series identity.
export default function ChartTooltip({ active, payload, label, labelFormat, valueFormat }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="tooltip">
      <div className="t-title">{labelFormat ? labelFormat(label) : label}</div>
      {payload
        .filter((p) => p.value != null)
        .map((p) => (
          <div key={p.dataKey}>
            <span
              aria-hidden="true"
              style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: p.color, marginRight: 6 }}
            />
            {p.name}: {valueFormat ? valueFormat(p.value) : p.value}
          </div>
        ))}
    </div>
  );
}
