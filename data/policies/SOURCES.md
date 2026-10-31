# Policy sources (public CMS documents, unmodified)

| File | Document | Origin |
|---|---|---|
| `opd-faqs-11.14.24.pdf` / `cms_opd_prior_auth_faq.txt` | *Prior Authorization Process for Certain Hospital Outpatient Department (OPD) Services - FAQs*, Nov 14, 2024 (13 pp.) | https://www.cms.gov/files/document/opd-frequently-asked-questions.pdf |
| `LCD-L38765-v27.pdf` / `lcd_l38765_facet_joint_interventions.txt` | *LCD L38765, Facet Joint Interventions for Pain Management*, Palmetto GBA (MAC, Jurisdiction J-J), version 27, revision effective for services on/after 04/09/2026 (43 pp.) | https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=38765 |

- The PDFs were downloaded from cms.gov (printed from the Medicare Coverage Database, 9/4/26, for the LCD).
- The `.txt` files are machine extraction only: `pdftotext -layout <pdf>`. No text was written or edited by hand.
- Scope caveat: L38765 is the LCD of the Palmetto GBA jurisdiction (AL, GA, TN, NC, SC, VA, WV). Other MACs publish their own facet-joint LCDs.
- Cases in `data/cases/` are summaries of real, public, name-redacted Texas Department of Insurance IRO decisions (and one open-access PMC case report). Nothing in this project is synthetic. See `data/cases/MAPPING_NOTES.md`.
