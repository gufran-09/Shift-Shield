import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';

const phases = [
  { number: '01', title: 'City forecast', detail: 'Weather is only the starting point.', icon: ArrowDownRight },
  { number: '02', title: 'Site WBGT', detail: 'Sun, surface and shelter change exposure.', icon: ArrowRight },
  { number: '03', title: 'Work / rest', detail: 'A deterministic plan for the shift.', icon: ArrowRight },
  { number: '04', title: 'Confirm the rest', detail: 'Supervisor + anonymous worker record.', icon: ArrowUpRight },
];

export function RouteHint() {
  return <div className="route-hint">{phases.map(({ number, title, detail, icon: Icon }) => <div className="route-hint__step" key={number}><span>{number}</span><strong>{title}</strong><small>{detail}</small><Icon size={16} /></div>)}</div>;
}
