---
name: expensify-remote-expenses
description: >
  Create recurring Mozilla home-internet and on-call phone expense-report
  drafts in Expensify using browser-harness, authenticated billing portals,
  and current Mana guidance. Use when gathering monthly statements and
  recreating prior approved reimbursement patterns. DO NOT USE FOR travel or
  one-off purchases.
metadata:
  version: "1.0"
---

# Expensify Remote Expenses

Create privacy-safe draft reports for recurring home-internet and eligible
on-call phone reimbursements.

## Prerequisites

- `browser-harness` connected to the user's Chrome session.
- Existing authenticated Expensify and billing-portal tabs.
- Atlassian MCP access to Mozilla Mana/Confluence.

Before taking any action, read [references/workflow.md](references/workflow.md)
completely. It contains the required privacy, policy, billing-cycle, financial,
and verification rules.

## Usage

Check the browser connection before starting:

```bash
browser-harness skill
browser-harness --doctor
```

Use Atlassian MCP for Mana and `browser-harness` for authenticated sites. Stop
for passwords, MFA, consent, or ambiguous account selection.

## Workflow

1. Inspect the latest matching approved Expensify reports.
2. Read current Mana policy; never rely on a hard-coded cap or deadline.
3. Download final statements whose billing periods have closed.
4. Calculate amounts and create reports as drafts.
5. Upload receipts, assign expenses, and audit every report.

Never submit, approve, reimburse, or advance a report without explicit user
authorization. A month with any open billing period may be staged but must stay
in draft.

## Gotchas

- **Scan Receipt** creates an unreported expense; do not create a second manual
  expense with the same receipt.
- A month label does not prove finality. Check every billing-period end date.
- Report-title saves are asynchronous; verify them in the report list.
- Expense filters persist and can hide newly uploaded receipts.
- Local Chrome is shared; sequence browser-harness work.

## Examples

"Prepare the missing monthly internet drafts and leave incomplete bills open."

## Troubleshooting

Stop on authentication or policy conflicts; use the Gotchas above for UI issues.

## Related Skills

- Use `writing-skills` when changing this skill or its evals.
- Use `skill-checker` before merging changes.
