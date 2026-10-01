# Lab 1 — Extract Invoice Data with UiPath IXP

**What you build:** an IXP (Document Understanding) project called `Vendor Invoice <user_name>` that reads a
vendor invoice PDF and returns eight fields: Vendor Name, Vendor Tax ID, Invoice Number, Invoice Date,
PO Number, Total Amount, Currency, Due Date. Every later lab works from these fields, never from the PDF.

**How you build it:** in the Claude Code desktop app, on your own copy of this repo, paste the prompts from the
Lab 1 page of the bootcamp site. Start with:

```text
Work inside commercial_bootcamp_<user_name>/lab1-ixp for the rest of this session. List the files you find.
```

## What is in this folder

| File / folder | What it is | Who uses it |
|---|---|---|
| `commercial-invoice-006…010-*.pdf` | Five one-page US vendor invoices (Great Lakes Steel, Liberty Print, Summit Facilities, Vertex Analytics, Pacific Timber). Three layouts rotate so the same field appears under different labels. | You upload these to the IXP project and annotate them. |
| `emails/*.eml` | The same five invoices as the vendor's email to `invoices@globex-ap.example`, PDF attached. Open one in Mail or Outlook to see how an invoice really arrives. | Context; Lab 2 processes the PDFs from a storage bucket. |
| `fields-to-extract.md` | The eight fields with the instruction text for each one. Claude Code reads this to create the field group. | You and Claude Code. |
| `reference/` | **The answer key.** `expected-extractions.json` / `.csv` hold the correct value of every field on every invoice (all ten, including the Lab 2 five). `taxonomy.json` is the field definition Claude Code should end up with. `annotation-guide.md` says which label carries each field on each layout and how to score a model. | You, at the end of the lab, to check your model. Facilitators, to grade. |

## How to know you are done

1. The project `Vendor Invoice <user_name>` exists in the Training tenant with one field group and the eight fields.
2. The five PDFs are uploaded, annotated, and a model version is published as **live**.
3. Running the live version on the five PDFs and comparing with `reference/expected-extractions.json` gives a
   match on **PO Number and Total Amount for all five**. Those two fields decide the `Valid?` gateway in Lab 2;
   misses on the other fields tell you which labels to annotate more.
4. Your results are committed to your repository (`lab1-ixp/my-results.md`, last step of the lab).

## Common mistakes

- Annotating **Subtotal** or **Amount Due** as Total Amount. Total Amount is the `TOTAL DUE` / `BALANCE DUE` /
  `TOTAL (USD)` line, tax included.
- Skipping the **live** publish. Lab 2's extraction agent calls the live version by project name.
- Creating the project under a different name. Everything downstream expects `Vendor Invoice <user_name>`.

All vendors, amounts and identifiers are synthetic.
