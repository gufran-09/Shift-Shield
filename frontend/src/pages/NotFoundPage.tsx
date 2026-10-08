import { ArrowLeft, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return <section className="not-found"><div><Search size={22} /></div><span className="eyebrow">PAGE NOT FOUND</span><h1>This route isn’t<br /><em>on the shift plan.</em></h1><p>The page may have moved or the link may be out of date.</p><Link className="button button--primary" to="/"><ArrowLeft size={16} /> BACK TO HEAT CHECK</Link></section>;
}
