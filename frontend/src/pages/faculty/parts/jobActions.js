// Which lifecycle buttons a job offers (the server enforces the same rules).
export function jobActions(job) {
  if (job.archivedAt) return ['restore']
  return { draft: ['publish', 'cancel', 'archive'], published: ['close', 'unpublish', 'cancel'], closed: ['reopen', 'archive'], cancelled: ['archive'] }[job.status] || []
}

export const ACTION_INFO = {
  publish: { label: 'Publish', title: 'Publish this job?', tone: 'primary', text: 'Eligible students can see and apply to it straight away. The deadline must be in the future.' },
  unpublish: { label: 'Unpublish', title: 'Move back to draft?', tone: 'warning', text: 'Only possible while nobody has applied. Students will no longer see it.' },
  close: { label: 'Close applications', title: 'Close applications?', tone: 'warning', text: 'No new applications are accepted. Existing applicants keep moving through the rounds.' },
  reopen: { label: 'Reopen', title: 'Reopen applications?', tone: 'primary', text: 'Applications open again until the deadline (which must be in the future).' },
  cancel: { label: 'Cancel job', title: 'Cancel this job?', tone: 'danger', text: 'This is final. Active applicants are notified with your reason.', reason: true },
  archive: { label: 'Archive', title: 'Archive this job?', tone: 'warning', text: 'It is hidden from lists and becomes read-only. History is kept.' },
  restore: { label: 'Restore', title: 'Restore this job?', tone: 'primary', text: 'It appears in lists again.' },
}

export const canEditJob = (auth, job) => auth.can('jobs.create') && !job.archivedAt && ['draft', 'published'].includes(job.status)
