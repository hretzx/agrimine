/** The hero's landscape band: sun (moon in dark mode), hills, trees, field rows. Pure SVG drawn with theme tokens, so it follows light and dark. */
export function Scenery() {
  const trees = [[60, 84, 9], [92, 86, 7], [150, 82, 10], [210, 85, 8], [330, 83, 9], [420, 85, 8], [500, 82, 10], [560, 86, 7]];
  return (
    <svg viewBox="0 0 600 122" preserveAspectRatio="xMidYMax slice" aria-hidden="true" className="absolute inset-0 size-full">
      <defs>
        <linearGradient id="scene-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--scene-sky1)" />
          <stop offset="1" stopColor="var(--scene-sky2)" />
        </linearGradient>
        <radialGradient id="scene-sun">
          <stop offset="0" stopColor="var(--scene-sun)" stopOpacity="0.95" />
          <stop offset="1" stopColor="var(--scene-sun)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="600" height="122" fill="url(#scene-sky)" />
      <circle cx="505" cy="38" r="46" fill="url(#scene-sun)" />
      <circle cx="505" cy="38" r="15" fill="var(--scene-sun)" />
      <path d="M0 84 L70 44 L130 70 L210 32 L290 68 L370 40 L450 66 L530 46 L600 70 V122 H0Z" fill="var(--scene-m1)" />
      <path d="M0 94 Q90 66 180 88 T360 84 T600 88 V122 H0Z" fill="var(--scene-m2)" />
      {trees.map(([x, y, r]) => <circle key={x} cx={x} cy={y} r={r} fill="var(--scene-tree)" />)}
      <path d="M0 100 Q150 86 300 98 T600 96 V122 H0Z" fill="var(--scene-m3)" />
      <path d="M0 104 Q300 90 600 106 V122 H0Z" fill="var(--scene-f2)" />
      {[96, 106, 116, 126].map((y) => <path key={y} d={`M-10 ${y} Q300 ${y - 14} 610 ${y + 6}`} stroke="var(--scene-f1)" strokeWidth="3" fill="none" opacity="0.55" />)}
    </svg>
  );
}
