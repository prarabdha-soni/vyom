import { redirect } from 'next/navigation';

/** The old console route; the workspace now opens on the dashboard. */
export default async function ConsoleRedirect({ params }: PageProps<'/[tenant_slug]/console'>) {
  const { tenant_slug: slug } = await params;
  redirect(`/${slug}/dashboard/`);
}
