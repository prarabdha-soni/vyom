'use client';

import { useActionState } from 'react';
import { loginCopy } from '@/content/console';
import { type SignInState, signIn } from '@/lib/auth/actions';
import { Field, SubmitButton, inputClass } from './forms';

const initial: SignInState = { error: null };

export function LoginForm({ next }: { readonly next: string | null }) {
  const [state, action] = useActionState(signIn, initial);
  return (
    <form action={action} className="flex flex-col gap-4">
      {next ? <input type="hidden" name="next" value={next} /> : null}
      <Field label={loginCopy.email}>
        <input type="email" name="email" defaultValue={state.email} required autoComplete="username" className={inputClass} />
      </Field>
      <Field label={loginCopy.password}>
        <input type="password" name="password" required autoComplete="current-password" className={inputClass} />
      </Field>
      {state.error ? (
        <p role="alert" className="m-0 rounded-control border border-rose-line bg-rose-soft px-3 py-2 text-[13.5px] text-rose">
          {state.error}
        </p>
      ) : null}
      <SubmitButton pending={loginCopy.pending} className="w-full">
        {loginCopy.submit}
      </SubmitButton>
    </form>
  );
}
