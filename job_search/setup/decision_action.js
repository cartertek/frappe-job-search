function setupForm({ doc, $dialog, call, toast }) {
  if (!doc.js_is_job_search || doc.js_review_status !== 'Pending') return { actions: [] }
  const choiceMap = {
    'Pursue or Decline': ['Pursue', 'Decline'],
    'Authorize or Decline Application': ['Authorize Application', 'Decline Application'],
    'Accept or Reject Offer': ['Accept Offer', 'Reject Offer'],
    'Withdraw': ['Withdraw'],
    'Override': ['Override'],
  }
  const choices = choiceMap[doc.js_review_request] || []
  if (!choices.length) return { actions: [] }
  return { actions: [{
    label: 'Record Decision',
    icon: 'check-circle',
    onClick: () => {
      const id = 'js-decision-' + Math.random().toString(36).slice(2)
      const options = choices.map(v => `<option value="${v}">${v}</option>`).join('')
      $dialog({
        title: 'Record Human Decision', size: 'md',
        message: 'Review the opportunity and supporting evidence before submitting. Your decision will be retained in the audit history.',
        html: `<div id="${id}" class="flex flex-col gap-3 mt-3">
          <label class="text-sm font-medium">Decision
            <select class="mt-1 w-full border rounded p-2" data-js-decision>${options}</select>
          </label>
          <label class="text-sm font-medium">Rationale
            <textarea class="mt-1 w-full border rounded p-2" rows="4" data-js-rationale placeholder="Explain your decision" required></textarea>
          </label></div>`,
        actions: [
          {label: 'Cancel', onClick: (close) => close()},
          {label: 'Submit Decision', variant: 'solid', onClick: async (close) => {
            const root = document.getElementById(id)
            const decision = root?.querySelector('[data-js-decision]')?.value
            const rationale = root?.querySelector('[data-js-rationale]')?.value.trim()
            if (!rationale) { toast.error('Decision rationale is required'); return }
            try {
              await call('job_search.api.record_human_decision', {
                opportunity: doc.name, decision, rationale,
              })
              close()
              toast.success('Decision recorded')
              window.location.reload()
            } catch (error) {
              toast.error(error?.messages?.[0] || 'Could not record decision')
            }
          }},
        ],
      })
    },
  }] }
}
