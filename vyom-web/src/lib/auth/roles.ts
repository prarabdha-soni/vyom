/** Roles defined by Vyom OS. Kept edge-safe: no imports. */

export const ROLES = ['reviewer', 'safety_physician', 'qppv', 'admin', 'ops'] as const;
export type Role = (typeof ROLES)[number];

/** Roles that work inside a tenant workspace. `ops` works across tenants at /ops. */
export const TENANT_ROLES = ['reviewer', 'safety_physician', 'qppv', 'admin'] as const;
export type TenantRole = (typeof TENANT_ROLES)[number];

export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value);
}

export const roleLabel: Record<Role, string> = {
  reviewer: 'PV reviewer',
  safety_physician: 'Safety physician',
  qppv: 'QPPV',
  admin: 'Tenant admin',
  ops: 'Vyom operations',
};
