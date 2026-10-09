import { CheckCircle2, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';

interface CertificateData {
  certificate_id: string;
  site_id?: string;
  site_name?: string;
  date?: string;
  heat_risk_hours?: number;
  rest_minutes_prescribed?: number;
  rest_minutes_confirmed?: number;
  signature?: string;
  verification_url?: string;
  issuer?: string;
  issued_at?: string;
}

export function VerifyPage() {
  const { certificateId = '' } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [valid, setValid] = useState<boolean | null>(null);
  const [status, setStatus] = useState('');
  const [certificate, setCertificate] = useState<CertificateData | null>(null);

  const verify = useCallback(async () => {
    if (!certificateId) {
      setError('No certificate ID provided.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await api.verifyCertificate(certificateId);
      setValid(result.valid);
      setStatus(result.status);
      setCertificate(result.certificate as unknown as CertificateData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Certificate not found or verification failed.');
    } finally {
      setLoading(false);
    }
  }, [certificateId]);

  useEffect(() => { void verify(); }, [verify]);

  if (loading) {
    return (
      <div className="verify-page">
        <div className="verify-card">
          <div className="verify-loading">
            <ShieldCheck size={48} className="spin" />
            <h2>Verifying certificate…</h2>
            <p>Checking cryptographic signature for <code>{certificateId}</code></p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="verify-page">
        <div className="verify-card verify-card--error">
          <div className="verify-header">
            <XCircle size={48} color="#d32f2f" />
            <h1>Certificate Not Found</h1>
            <p>{error}</p>
          </div>
          <div className="verify-id-box">
            <span className="eyebrow">CERTIFICATE ID</span>
            <code>{certificateId}</code>
          </div>
          <p className="verify-footer">
            This certificate ID does not exist in the ShiftShield record. If you received this link from someone,
            ask them to verify the certificate ID is correct.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="verify-page">
      <div className={`verify-card ${valid ? 'verify-card--valid' : 'verify-card--invalid'}`}>
        <div className="verify-header">
          {valid ? (
            <>
              <CheckCircle2 size={56} color="#2d6a4f" />
              <h1>Certificate Verified</h1>
              <p className="verify-status verify-status--valid">
                CRYPTOGRAPHICALLY VERIFIED
              </p>
            </>
          ) : (
            <>
              <ShieldAlert size={56} color="#d32f2f" />
              <h1>Verification Failed</h1>
              <p className="verify-status verify-status--invalid">
                {status?.toUpperCase().replaceAll('_', ' ') || 'TAMPERED OR INVALID'}
              </p>
            </>
          )}
        </div>

        {certificate && (
          <>
            <div className="verify-id-box">
              <span className="eyebrow">CERTIFICATE ID</span>
              <code>{certificate.certificate_id}</code>
            </div>

            <div className="verify-details">
              <div className="verify-detail-row">
                <span className="verify-label">Site</span>
                <span className="verify-value">{certificate.site_name || '—'}</span>
              </div>
              <div className="verify-detail-row">
                <span className="verify-label">Date</span>
                <span className="verify-value">{certificate.date || '—'}</span>
              </div>
              <div className="verify-detail-row">
                <span className="verify-label">Issuer</span>
                <span className="verify-value">{certificate.issuer || '—'}</span>
              </div>
              <div className="verify-detail-row">
                <span className="verify-label">Issued At</span>
                <span className="verify-value">{certificate.issued_at ? new Date(certificate.issued_at).toLocaleString() : '—'}</span>
              </div>
            </div>

            <div className="verify-metrics">
              <div className="verify-metric">
                <strong>{certificate.heat_risk_hours?.toFixed(1) ?? '—'}<small>h</small></strong>
                <span>HEAT RISK HOURS</span>
              </div>
              <div className="verify-metric">
                <strong>{certificate.rest_minutes_prescribed ?? '—'}<small>m</small></strong>
                <span>REST PRESCRIBED</span>
              </div>
              <div className="verify-metric">
                <strong>{certificate.rest_minutes_confirmed ?? '—'}<small>m</small></strong>
                <span>REST CONFIRMED</span>
              </div>
            </div>

            <div className="verify-signature">
              <span className="eyebrow">HMAC-SHA256 SIGNATURE</span>
              <code className="verify-sig-value">{certificate.signature || '—'}</code>
            </div>
          </>
        )}

        <div className="verify-footer">
          <p>
            This certificate records what the supervisor and anonymous workers reported through ShiftShield.
            The HMAC signature detects later edits to the record. It does not independently prove a break happened.
          </p>
          <p className="verify-disclaimer">
            Decision support only, not medical or legal advice. ShiftShield is a hackathon prototype; thresholds are
            pending occupational-safety review.
          </p>
        </div>
      </div>

      <div className="verify-branding">
        <ShieldCheck size={16} /> ShiftShield · Verified Rest Record
      </div>
    </div>
  );
}
