# Lab 8: platform inspection

This folder starts with only this README. Lab 8 is a read-only inspection of your own
`Agentic Bootcamp/APAutomation_<user_name>` folder; the one thing it creates in the tenant is the
`InvoiceEvidence_Lab` storage bucket. Paste the prompts from the Lab 8 page of the bootcamp site.

## What the lab writes here

`inspection-report.md`, committed as "Lab 8: platform inspection report". It covers:

- **Folder**: type, parent, users counted by role (with inherited users), machines on the folder and on
  `Agentic Bootcamp`, runtimes, robot and library associations.
- **Storage bucket**: the `InvoiceEvidence_Lab` configuration and the result of the test upload.
- **Data Fabric**: `AP_Invoice_<user_name>` fields, data types, scope, record count, and up to five sample
  records read with `selectedFields`.
- **Queue**: `InvoiceQueue_<user_name>` configuration, items by status, and a small sample of safe metadata.
- **Operational health**: recent job states, durations, versions, runtime assignments and triggers for the
  Lab 2-5 processes, including the solution sub-folders, plus observations to hand to uipath-troubleshoot.

## Redaction list

The report and anything else saved here must not contain:

- colleagues' emails or names (count users by role instead);
- VendorTaxId, TotalAmount and ApprovalPackageJson values (exclude them with `selectedFields`);
- bank details or other vendor business data from queue items or logs;
- job EnvironmentVariables, InputArguments or OutputArguments (the Lab 3 jobs carry the signed ERP URL);
- tokens, signed URLs, keys, or tenant and folder ids.

Known noise to report as such, not as faults: "Resource overwrites read from …uipath.json (0 entries)" and the
Lab 5 governance 403 logged at Error level on Successful jobs.
