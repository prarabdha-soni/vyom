/** Liveness for the load balancer and container probes. Touches nothing else. */
export const dynamic = 'force-dynamic';

export function GET(): Response {
  return new Response('ok\n', {
    headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' },
  });
}
