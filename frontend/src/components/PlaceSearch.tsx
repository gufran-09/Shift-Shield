import { Search } from 'lucide-react';
import { useState, type KeyboardEvent } from 'react';

type Place = { id: number; name: string; latitude: number; longitude: number; timezone?: string; admin1?: string; admin2?: string; country?: string };

const GEOCODER = 'https://geocoding-api.open-meteo.com/v1/search';

/** Type a place name, pick a match, and the coordinates fill in. Uses Open-Meteo's free geocoder; only the typed name is sent. */
export function PlaceSearch({ onPick }: { onPick: (place: { latitude: number; longitude: number; timezone?: string; label: string }) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Place[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const search = async () => {
    const name = query.trim();
    if (name.length < 2) { setMessage('Type at least 2 letters.'); return; }
    setBusy(true); setMessage(''); setResults([]);
    try {
      const response = await fetch(`${GEOCODER}?${new URLSearchParams({ name, count: '6', language: 'en', format: 'json' })}`);
      if (!response.ok) throw new Error(String(response.status));
      const data = (await response.json()) as { results?: Place[] };
      const found = data.results ?? [];
      // Indian places first, since ShiftShield's plans and demo are Indian.
      found.sort((a, b) => Number(b.country === 'India') - Number(a.country === 'India'));
      setResults(found);
      if (!found.length) setMessage('No match. Try a city or area name, or enter coordinates.');
    } catch {
      setMessage('Place search is unavailable right now. Enter coordinates below.');
    } finally {
      setBusy(false);
    }
  };

  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') { event.preventDefault(); void search(); }
  };

  const pick = (place: Place) => {
    const label = [place.name, place.admin2 && place.admin2 !== place.name ? place.admin2 : '', place.admin1, place.country].filter(Boolean).join(', ');
    onPick({ latitude: Number(place.latitude.toFixed(5)), longitude: Number(place.longitude.toFixed(5)), timezone: place.timezone, label });
    setResults([]);
    setQuery(label);
    setMessage(`Using ${label}.`);
  };

  return (
    <div className="place-search">
      <div className="form-grid form-grid--location">
        <label style={{ gridColumn: 'span 2' }}>Search place
          <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={onKey} placeholder="e.g. Gachibowli, Hyderabad" aria-label="Search place by name" />
        </label>
        <button type="button" className="location-btn" onClick={() => void search()} disabled={busy}><Search size={15} /> {busy ? 'Searching…' : 'Find'}</button>
      </div>
      {results.length > 0 && (
        <ul role="listbox" aria-label="Matching places" style={{ listStyle: 'none', margin: '6px 0 0', padding: 0, border: '1px solid #deded5', borderRadius: 6, background: '#fff', overflow: 'hidden' }}>
          {results.map((place) => (
            <li key={place.id}>
              <button type="button" role="option" aria-selected={false} onClick={() => pick(place)} style={{ display: 'block', width: '100%', textAlign: 'left', padding: '8px 10px', border: 0, borderBottom: '1px solid #eeede6', background: 'transparent', font: '11px Manrope, sans-serif', color: '#2f3d34', cursor: 'pointer' }}>
                <strong>{place.name}</strong>{' '}
                <span style={{ color: '#7a8279' }}>{[place.admin2 && place.admin2 !== place.name ? place.admin2 : '', place.admin1, place.country].filter(Boolean).join(', ')}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {message && <p className="inline-hint" style={{ marginTop: 6 }}>{message}</p>}
      <p className="inline-hint" style={{ marginTop: 4 }}>Place search by Open-Meteo.com</p>
    </div>
  );
}
