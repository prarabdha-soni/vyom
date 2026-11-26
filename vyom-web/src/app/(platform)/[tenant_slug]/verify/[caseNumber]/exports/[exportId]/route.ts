import { getSession, credentials } from '@/lib/console/data';
import { sampleCaseExport, samplePermissions } from '@/lib/console/sample';
import { osFetch } from '@/lib/gateway/api-client';

/** Streams an E2B(R3) draft export. Same rule as Vyom OS: only roles that may export may download. */
export async function GET(_request: Request, { params }: RouteContext<'/[tenant_slug]/verify/[caseNumber]/exports/[exportId]'>) {
  const { tenant_slug: slug, caseNumber: rawNumber, exportId } = await params;
  const caseNumber = decodeURIComponent(rawNumber);
  const session = await getSession();
  if (!session) return new Response('Sign in first.', { status: 401 });
  if (session.tenantSlug !== slug) return new Response('Not found.', { status: 404 });
  if (!/^\d+$/.test(exportId)) return new Response('Not found.', { status: 404 });

  let xml: string;
  let sha256: string | null;
  if (session.mode === 'sample') {
    if (!samplePermissions(session.role).includes('case.export')) {
      return new Response('Your role cannot download exports.', { status: 403 });
    }
    const found = sampleCaseExport(caseNumber, exportId);
    if (!found) return new Response('Not found.', { status: 404 });
    ({ xml, sha256 } = found);
  } else {
    const result = await osFetch<string>(
      credentials(session),
      `/v1/cases/${encodeURIComponent(caseNumber)}/exports/${exportId}`,
      { text: true },
    );
    if (!result.ok) return new Response(result.error, { status: result.status });
    xml = result.data;
    sha256 = result.headers.get('x-content-sha256');
  }

  const filename = `${caseNumber}-export-${exportId}-e2b-draft.xml`.replace(/[^A-Za-z0-9._-]/g, '_');
  return new Response(xml, {
    headers: {
      'content-type': 'application/xml; charset=utf-8',
      'content-disposition': `attachment; filename="${filename}"`,
      'cache-control': 'no-store',
      ...(sha256 ? { 'x-content-sha256': sha256 } : {}),
    },
  });
}
