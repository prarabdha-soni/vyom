import { getSession, credentials } from '@/lib/console/data';
import { sampleReportMarkdown } from '@/lib/console/sample';
import { osFetch } from '@/lib/gateway/api-client';

/** The periodic report as Markdown, for review outside the console. */
export async function GET(_request: Request, { params }: RouteContext<'/[tenant_slug]/dossier/[reportNumber]/export'>) {
  const { tenant_slug: slug, reportNumber: rawNumber } = await params;
  const reportNumber = decodeURIComponent(rawNumber);
  const session = await getSession();
  if (!session) return new Response('Sign in first.', { status: 401 });
  if (session.tenantSlug !== slug) return new Response('Not found.', { status: 404 });

  let markdown: string | null;
  if (session.mode === 'sample') {
    markdown = sampleReportMarkdown(reportNumber);
    if (markdown === null) return new Response('Not found.', { status: 404 });
  } else {
    const result = await osFetch<string>(credentials(session), `/v1/reports/${encodeURIComponent(reportNumber)}/export`, { text: true });
    if (!result.ok) return new Response(result.error, { status: result.status });
    markdown = result.data;
  }

  const filename = `${reportNumber}.md`.replace(/[^A-Za-z0-9._-]/g, '_');
  return new Response(markdown, {
    headers: {
      'content-type': 'text/markdown; charset=utf-8',
      'content-disposition': `attachment; filename="${filename}"`,
      'cache-control': 'no-store',
    },
  });
}
