import type { Metadata } from 'next';
import Link from 'next/link';
import { siteConfig } from '~/site.config';
import { loginCopy } from '@/content/console';
import { LoginForm } from '@/components/console/LoginForm';
import { ArrowRightIcon } from '@/components/icons';
import { Logo, SkyWash } from '@/components/site';
import { ButtonLink, Eyebrow, SampleDataChip } from '@/components/ui';
import { openSampleWorkspace, signOut } from '@/lib/auth/actions';
import { roleLabel } from '@/lib/auth/roles';
import { homePath, safeNextPath } from '@/lib/auth/session';
import { sessionSecret } from '@/lib/auth/token';
import { getSession } from '@/lib/console/data';
import { osBaseUrl } from '@/lib/gateway/api-client';

export const metadata: Metadata = {
  title: 'Sign in',
  description: 'Sign in to your Vyom workspace, or explore the sample workspace with fictional data.',
  robots: { index: false, follow: false },
};

export default async function LoginPage({ searchParams }: PageProps<'/login'>) {
  const query = await searchParams;
  const next = safeNextPath(typeof query.next === 'string' ? query.next : null);
  const expired = query.expired === '1';
  const session = await getSession();
  const liveReady = Boolean(osBaseUrl() && sessionSecret());

  return (
    <main id="main" className="relative isolate flex min-h-dvh flex-col overflow-hidden">
      <SkyWash variant="cta" />
      <div className="relative mx-auto flex w-full max-w-[1040px] flex-1 flex-col gap-10 px-5 py-8 sm:px-8 lg:py-12">
        <Logo />
        <div className="grid flex-1 grid-cols-1 items-start gap-6 lg:grid-cols-2 lg:gap-8">
          <section aria-labelledby="sign-in" className="flex flex-col gap-6 rounded-panel border border-line bg-surface p-6 shadow-panel sm:p-8">
            <div className="flex flex-col gap-3">
              <Eyebrow>{loginCopy.eyebrow}</Eyebrow>
              <h1 id="sign-in" className="m-0 text-[30px] leading-[1.1] font-semibold tracking-[-0.03em] text-primary">
                {loginCopy.heading}
              </h1>
              <p className="m-0 text-[15px] leading-[1.55] text-muted">{loginCopy.lead}</p>
            </div>
            {expired ? (
              <p role="status" className="m-0 rounded-control border border-line bg-raised px-3 py-2 text-[13.5px] text-secondary">
                {loginCopy.expired}
              </p>
            ) : null}
            {session ? (
              <div className="flex flex-col gap-3">
                <p className="m-0 text-[14.5px] text-secondary">
                  {loginCopy.signedInAs(session.mode === 'live' ? session.claims.email : `${roleLabel[session.role]} in the sample workspace`)}
                </p>
                <div className="flex flex-wrap gap-2">
                  <ButtonLink href={homePath(session.role, session.tenantSlug)} variant="panelPrimary">
                    {loginCopy.continue}
                  </ButtonLink>
                  <form action={signOut}>
                    <button type="submit" className="min-h-[44px] cursor-pointer rounded-control border border-button bg-surface px-4 text-[14px] font-medium text-primary hover:bg-raised">
                      Sign out
                    </button>
                  </form>
                </div>
              </div>
            ) : liveReady ? (
              <LoginForm next={next} />
            ) : (
              <p className="m-0 rounded-control border border-dashed border-dash bg-raised px-3 py-2.5 text-[13.5px] leading-[1.5] text-secondary">
                {loginCopy.notConfigured}
              </p>
            )}
            <Link href="/" className="text-[14px] font-medium text-secondary hover:text-primary hover:underline">
              {loginCopy.home}
            </Link>
          </section>

          {siteConfig.sampleWorkspace ? (
            <section aria-labelledby="sample" className="flex flex-col gap-5 rounded-panel border border-line bg-surface/90 p-6 sm:p-8">
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Eyebrow>{loginCopy.sample.eyebrow}</Eyebrow>
                  <SampleDataChip />
                </div>
                <h2 id="sample" className="m-0 text-[22px] leading-[1.2] font-semibold tracking-[-0.02em] text-primary">
                  {loginCopy.sample.heading}
                </h2>
                <p className="m-0 text-[14.5px] leading-[1.55] text-muted">{loginCopy.sample.lead}</p>
              </div>
              <form action={openSampleWorkspace} className="flex flex-col gap-2">
                {next ? <input type="hidden" name="next" value={next} /> : null}
                {loginCopy.sample.roles.map((role) => (
                  <button
                    key={role.value}
                    type="submit"
                    name="role"
                    value={role.value}
                    className="group flex min-h-[56px] w-full cursor-pointer items-center gap-3 rounded-button border border-line bg-surface px-4 py-2.5 text-left transition-colors hover:border-strong hover:bg-panel-header"
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="text-[15px] font-medium text-primary">
                        <span className="sr-only">{loginCopy.sample.submit} </span>
                        {role.label}
                      </span>
                      <span className="text-[13px] text-meta">{role.hint}</span>
                    </span>
                    <ArrowRightIcon size={16} className="shrink-0 text-meta transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                  </button>
                ))}
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </main>
  );
}
