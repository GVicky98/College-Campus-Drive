// The five placement-policy kinds and their parameters (the server validates the same ranges).
export const POLICY_KINDS = {
  max_offers: { label: 'Maximum accepted offers', help: 'Blocks applying and accepting once a student has this many accepted offers.',
    fields: [{ key: 'maxAcceptedOffers', label: 'Max accepted offers', type: 'number', min: 1, max: 20 }], defaults: { maxAcceptedOffers: 2 } },
  tier_restriction: { label: 'Dream / Super Dream tier rule', help: 'After accepting an offer, a student may only go for higher-tier companies.',
    fields: [{ key: 'allowOnlyHigherTier', label: 'Allow only higher tiers after an accepted offer', type: 'bool' }], defaults: { allowOnlyHigherTier: true } },
  application_limit: { label: 'Concurrent application limit', help: 'How many active applications a student may have at once.',
    fields: [{ key: 'maxActiveApplications', label: 'Max active applications', type: 'number', min: 1, max: 100 }], defaults: { maxActiveApplications: 8 } },
  accepted_offer: { label: 'Offer acceptance window', help: 'The usual number of days a student gets to respond (shown to students).',
    fields: [{ key: 'acceptanceWindowDays', label: 'Days to respond', type: 'number', min: 1, max: 90 }], defaults: { acceptanceWindowDays: 14 } },
  exception_approval: { label: 'Eligibility exception approval', help: 'What an eligibility exception must record.',
    fields: [{ key: 'requireReason', label: 'Require a reason', type: 'bool' }, { key: 'requireApprover', label: 'Require an approver', type: 'bool' }],
    defaults: { requireReason: true, requireApprover: true } },
}

export function describeParams(kind, params) {
  return (POLICY_KINDS[kind]?.fields || []).map((f) => `${f.label}: ${f.type === 'bool' ? (params[f.key] ? 'yes' : 'no') : params[f.key]}`).join(' · ')
}
