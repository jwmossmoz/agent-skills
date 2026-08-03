# Remote-expense workflow

Follow this reference completely for every run. Current policy and prior
approved reports are inputs; do not encode a person's providers, account data,
approver, or reimbursement amounts in reusable files.

## Privacy and financial safety

- Keep statements and receipts local. Never add them, screenshots, recordings,
  or copied page source to a repository.
- Do not print or persist account numbers, addresses, phone numbers, personal
  email addresses, payment-card details, receipt URLs, report IDs, or session
  tokens. Redact them from diagnostics and summaries.
- Use provider names only while operating the user's accounts. Do not bake a
  user's provider list into the skill, evals, notes, or output artifacts.
- Create drafts. Submission, approval, reimbursement, or any later workflow
  state is a separate financial action requiring explicit authorization.
- Do not delete or alter unrelated expenses, reports, receipts, or downloads.
- Browser recordings can capture sensitive billing data. Record only when the
  user requests it, keep recordings local, and never commit them.

## Establish the approved pattern

1. Open Expensify's report list with `browser-harness`.
2. Inspect the most recent approved report for every requested expense type.
3. Retain only the reusable shape needed for this run: title convention,
   workspace, approver path, category, cadence, reimbursable split, date
   convention, and receipt count.
4. Do not copy unique IDs, URLs, or account metadata into notes or output.

Prefer the latest approved convention. If recent reports disagree, explain the
discrepancy and ask before choosing one.

## Read current Mana policy

Use Atlassian MCP, not browser automation, to find and retrieve the current
Mana page for remote-work expenses. Extract only what this run needs:

- employee eligibility;
- eligible expense types;
- ceiling and currency;
- submission deadline or exception;
- Expensify category;
- bundle or itemization rules.

Do not copy Mana content into public artifacts or quote internal policy in the
skill. The live page is authoritative. Compare requested months with the
current date and policy window. Tell the user which are eligible and flag other
missing eligible months, but do not expand scope without consent.

## Download final statements

For each eligible month and merchant:

1. Switch to the already-authenticated billing tab.
2. Open billing history or past statements.
3. Confirm the statement date, total, and billing-period end date.
4. Prefer the detailed or printable final PDF supporting the eligible charge.
5. Treat a current balance, provisional bill, or statement with a future
   period end as incomplete. A month label alone is not proof of finality.
6. If any required provider lacks a final statement, the report may be staged
   as a draft but is not submission-ready. State what is missing and leave the
   report open until the final statement exists.
7. Save PDFs in a local task directory such as
   `~/Downloads/expense-reports-YYYY/`, using neutral names containing only a
   merchant type and statement month.
8. Verify every expected file exists and has non-zero size.

If a printable PDF opens in a same-origin `blob:` tab, capture its URL and
trigger a named download from the originating billing page. The PDF viewer tab
may not honor a download itself.

## Calculate eligible amounts

Use the lower of the documented eligible charge, current policy ceiling, and
any explicitly approved fixed allowance. When several providers contribute to
one capped expense, preserve actual charges until the cap is reached and
reduce only the final component needed to land exactly on the ceiling. Never
claim more than the statements or policy permit.

Stop and surface a conflict when the approved report pattern and current policy
disagree.

## Create draft reports and expenses

For each month and expense type:

1. Create a draft in the correct Expensify workspace.
2. Rename it using the latest approved naming convention.
3. From Expenses, choose **New Expense → Scan Receipt** and upload each PDF.
   Upload creates an unreported expense; do not also save a manual duplicate.
4. Open the resulting expense and verify or correct merchant, statement date,
   eligible amount, category, and destination report.
5. Save the expense. Report assignment should put it in the correct workspace.

Use accessibility nodes and coordinate clicks. Generated autocomplete IDs
change between dialogs, so locate category and report inputs by visible labels.
SmartScan may infer the full bill even when the eligible amount is capped or
fixed; correct it before report assignment.

## Audit before handoff

Re-open every new report and verify:

- title, month, and draft state;
- workspace and approver path;
- total against the policy calculation;
- category;
- merchant, date, and amount for each expense;
- expected receipt count and no missing-receipt indicator;
- no duplicate or unrelated expenses;
- final versus incomplete status of each source statement.

A service period, statement date, payment date, and scanned date may differ.
Follow the approved convention and retain any Expensify warning rather than
falsifying receipt data. Keep any report with an open underlying billing period
in draft, even when a current PDF is downloadable.

Finally, verify the report list shows the expected drafts and totals. Report
which drafts are submission-ready and which must wait for final statements.
