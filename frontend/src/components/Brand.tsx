import { Link } from 'react-router-dom';

export function Brand({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  return (
    <Link className={`brand${compact ? ' brand--compact' : ''}${light ? ' brand--light' : ''}`} to="/" aria-label="ShiftShield home">
      <svg className="brand__mark" viewBox="0 0 40 40" role="img" aria-label="">
        <path d="M20 3.5 34 8.6v10.1c0 8.5-5.7 14.9-14 18-8.3-3.1-14-9.5-14-18V8.6L20 3.5Z" fill="none" stroke="currentColor" strokeWidth="2.2" />
        <path d="M12 25.5V17m8 8.5V12m8 13.5v-6" stroke="currentColor" strokeWidth="2.7" strokeLinecap="round" />
        <path d="M10 29h20" stroke="#ea643f" strokeWidth="2.3" strokeLinecap="round" />
      </svg>
      <span className="brand__word"><strong>SHIFT</strong><i /> <strong>SHIELD</strong><small>HEAT SAFETY, PROVEN</small></span>
    </Link>
  );
}
