# Product Requirements Document

## Project: Notice Comparison Tool

## 1. Overview
The Notice Comparison Tool accepts uploaded notice documents (PDF or JPEG), extracts structured fields automatically using an LLM (Claude API), compares two versions of the same notice, and determines whether they are the same or materially different. The system supports a human reviewer by surfacing differences, presenting them clearly, and enabling a confirmation step before the result is finalized.

## 2. Problem Statement
Teams often receive multiple versions of notices that may differ in subtle but consequential ways. Manually comparing extraction results is slow, inconsistent, and prone to missed changes. This tool reduces review effort by automating comparison, highlighting evidence, and making the confirmation process auditable.

## 3. Product Goal
Provide a reliable, explainable comparison workflow that helps users identify whether two notice versions are effectively unchanged or materially different, with a human confirming the final outcome.

## 4. Scope
In scope:
- Accepting uploaded PDF or JPEG documents, including notices, leases, and other text-based documents
- Extracting structured fields automatically where the document contains recognizable label/value pairs
- Comparing two structured extraction results
- Identifying field-level differences
- Providing a full-document paragraph-by-paragraph text diff for prose and clause-based content
- Showing added, removed, and changed wording across the full document
- Presenting comparison results in a human-readable side-by-side format
- Supporting a human confirmation step
- Recording comparison input, evidence, and final decision

Out of scope:
- Fully replacing legal judgment
- Providing a general-purpose document OCR platform beyond document comparison
- Guaranteeing perfect interpretation of every ambiguous change without human review
- Requiring all documents to use a fixed structured schema in order to compare them

## 5. Epic 8: Notice Comparison Tool

### Story 8.0: Extract structured fields from a PDF or JPEG notice
As a reviewer, I want the system to extract the label/value pairs present in an uploaded notice so that I can begin the comparison workflow without manually pasting or uploading JSON.

#### Acceptance Criteria
- The system accepts an uploaded PDF or JPEG notice as input.
- The system extracts whatever field labels and values are present in the document, without assuming a fixed four-field schema such as notice_id, recipient, amount_due, and due_date.
- The system returns a structured mapping of labels to values that covers the union of all recognized entries in the notice, including document-specific fields not known in advance.
- The system handles multi-page PDFs and returns the combined structured result.
- The system returns a clear error when extraction fails, when confidence is too low, or when the document cannot be interpreted reliably.
- The system makes extraction automatic so the app’s input model is “upload PDF/JPEG, extraction happens automatically” rather than “paste/upload JSON.”
- Constraint/limitation: extraction depends on the document having a recognizable label/value structure, such as repeated “Field Name: value” patterns or other consistent line-by-line key/value formatting; plain narrative text without discernible field labels is not a supported input pattern.

### Story 8.1: Field-by-field diff between two extraction results
As a reviewer, I want the system to compare two extraction results field by field so that I can quickly identify what changed and assess whether the difference is material.

#### Acceptance Criteria
- The system accepts two structured extraction results produced by Story 8.0 (or equivalent preprocessing) as input.
- The system compares the union of all labels found across both notices, not just the intersection of a predefined schema.
- The system identifies added, removed, changed, and missing values across both documents, and it flags fields present in one notice but absent in the other as "missing" rather than silently ignoring them.
- The system normalizes common formatting differences such as case, whitespace, and date formatting where appropriate.
- The system marks differences with field name, source value, target value, and a simple change type (added, removed, changed, missing).
- The system returns a comparison summary that clearly indicates whether the notices appear equivalent, materially different, or ambiguous.
- The system handles missing or incomplete data without crashing.

### Story 8.2: Side-by-side human-readable view
As a reviewer, I want a side-by-side view of both extraction results so that I can inspect differences in context and make a confident decision.

#### Acceptance Criteria
- The system renders a side-by-side comparison view for the two extraction results.
- The view shows corresponding fields next to each other and highlights differences visually.
- The view includes enough context to understand the change without needing to inspect the raw data separately.
- The view supports reviewing nested or repeated fields in a readable format.
- The view clearly indicates when a field is missing in one version.
- The view is understandable to a human reviewer without technical expertise.

### Story 8.3: Full-text paragraph-level diff for prose and clause-based documents
As a reviewer, I want the system to compare the full text of two documents paragraph by paragraph so that I can identify changes in prose, clauses, and narrative language even when the documents do not fit a rigid field schema.

#### Acceptance Criteria
- The system accepts two uploaded documents of any type, including notices, leases, and other text-heavy content.
- The system presents both of the following in the comparison workflow: (a) any structured field/value pairs it could identify, and (b) a paragraph-by-paragraph text diff across the full document.
- The paragraph-level diff identifies added, removed, and changed wording at the paragraph level, and it preserves reading order for easy review.
- The system highlights wording differences within a paragraph, not just whole-paragraph additions/removals, when the text changes materially.
- The system still shows structured field extraction when recognizable label/value pairs are present, even in the same document that also contains narrative prose.
- The system handles documents with mixed structured and unstructured content without crashing or forcing a fixed schema.
- The system clearly separates structured-field comparison from full-text comparison so the reviewer can understand which parts are machine-extracted fields and which are narrative/clause-level changes.
- The system works for documents that are not notices and may contain legal or contractual language, not only highly structured notices.

## 6. Functional Requirements
- FR1: The system shall accept uploaded PDF or JPEG documents and automatically extract labeled field/value pairs when the document contains recognizable structured content, without requiring a fixed schema in advance.
- FR2: The system shall compare two structured extraction results produced from the same or related document set.
- FR3: The system shall identify field-level differences across the union of labels found in both documents, including added, removed, changed, and missing values; a field present in one document and absent in the other shall be flagged as "missing" instead of being ignored.
- FR4: The system shall support normalization for common formatting differences where safe and appropriate.
- FR5: The system shall provide a summary of differences with supporting evidence.
- FR6: The system shall classify the comparison as same, materially different, or needs review.
- FR7: The system shall provide a human-readable side-by-side comparison view for structured fields.
- FR8: The system shall provide a paragraph-by-paragraph full-text diff for the complete document body, showing added, removed, and changed wording across the document.
- FR9: The system shall present both the structured field summary and the full-text prose diff in the same review workflow so that a reviewer can inspect both the extracted values and the narrative language changes.
- FR10: The system shall allow a human reviewer to confirm, override, or reject the automated classification.
- FR11: The system shall preserve an audit trail containing the input data, detected differences, and final reviewer decision.
- FR12: The system shall handle partial, incomplete, or noisy extraction data gracefully.
- FR13: The extraction workflow shall operate on documents that present recognizable label/value structure (for example, “Field Name: value” per line or similar consistent key/value formatting); if the document lacks that structure, the system shall surface that as a limitation or failure condition rather than pretending to extract a complete schema.
- FR14: The full-text review workflow shall support prose and clause-based documents, including contracts, leases, and other narrative documents that do not necessarily align to a fixed field schema.

## 7. Non-Functional Requirements
- NFR1: The system should return a comparison result in a timely manner for typical document review workloads.
- NFR2: The comparison output should be explainable and easy for a human reviewer to interpret.
- NFR3: The system should avoid false positives for clearly cosmetic changes where possible.
- NFR4: The system should be robust to missing values, inconsistent formatting, and extraction noise.
- NFR5: The system should maintain auditability and traceability for each comparison decision.
- NFR6: The system should support future rule tuning or configuration without requiring a redesign.
- NFR7: The extraction approach should explicitly acknowledge the constraint that it assumes documents contain recognizable label/value structure; unsupported formats must be treated as a known limitation during validation and user-facing messaging.
- NFR8: The full-text diff capability should preserve document ordering and make paragraph-level additions, removals, and wording changes easy to review in context.
- NFR9: The user-facing workflow should clearly distinguish between structured extraction results and full-document prose comparison so both views can be interpreted accurately.

## 8. Confirm Step Success Metrics
The confirm step is the human review action that validates or overrides the system’s recommendation. Success will be measured by the following metrics:
- Confirmation completion rate: at least 95% of generated comparisons should reach a completed confirm action.
- Median confirm time: the average reviewer should be able to confirm a comparison in under 60 seconds for standard cases.
- Reviewer agreement rate: at least 85% of confirm decisions should align with the system’s recommendation when the comparison is clear and non-ambiguous.
- Override rate: the rate of reviewer overrides should remain low for straightforward cases and be reviewed to improve comparison quality over time.
- Audit completeness: 100% of confirm actions should be stored with the relevant comparison evidence and final decision.

## 9. Success Criteria
The initiative is successful if the tool reduces manual review effort, surfaces relevant changes clearly, and gives reviewers enough confidence to make fast, consistent confirm decisions.
