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
- Accepting uploaded PDF or JPEG notice documents
- Extracting structured fields automatically into the schema expected by the diff engine
- Comparing two structured extraction results
- Identifying field-level differences
- Presenting comparison results in a human-readable side-by-side format
- Supporting a human confirmation step
- Recording comparison input, evidence, and final decision

Out of scope:
- Fully replacing legal judgment
- Providing a general-purpose document OCR platform beyond notice extraction
- Guaranteeing perfect interpretation of every ambiguous change without human review

## 5. Epic 8: Notice Comparison Tool

### Story 8.0: Extract structured fields from a PDF or JPEG notice
As a reviewer, I want the system to extract structured notice fields from an uploaded PDF or JPEG using an LLM so that I can begin the comparison workflow without manually pasting or uploading JSON.

#### Acceptance Criteria
- The system accepts an uploaded PDF or JPEG notice as input.
- The system extracts a structured dict matching the schema already expected by the diff engine.
- The system handles multi-page PDFs and returns the combined structured result.
- The system returns a clear error when extraction fails, when confidence is too low, or when the document cannot be interpreted reliably.
- The system makes extraction automatic so the app’s input model is “upload PDF/JPEG, extraction happens automatically” rather than “paste/upload JSON.”

### Story 8.1: Field-by-field diff between two extraction results
As a reviewer, I want the system to compare two extraction results field by field so that I can quickly identify what changed and assess whether the difference is material.

#### Acceptance Criteria
- The system accepts two structured extraction results produced by Story 8.0 (or equivalent preprocessing) as input.
- The system compares shared fields and identifies added, removed, and changed values.
- The system normalizes common formatting differences such as case, whitespace, and date formatting where appropriate.
- The system marks differences with field name, source value, target value, and a simple change type (added, removed, changed).
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

## 6. Functional Requirements
- FR1: The system shall accept uploaded PDF or JPEG notices and automatically extract structured fields via an LLM.
- FR2: The system shall compare two structured extraction results for the same notice.
- FR3: The system shall identify field-level differences including added, removed, and modified values.
- FR4: The system shall support normalization for common formatting differences where safe and appropriate.
- FR5: The system shall provide a summary of differences with supporting evidence.
- FR6: The system shall classify the comparison as same, materially different, or needs review.
- FR7: The system shall provide a human-readable side-by-side comparison view.
- FR8: The system shall allow a human reviewer to confirm, override, or reject the automated classification.
- FR9: The system shall preserve an audit trail containing the input data, detected differences, and final reviewer decision.
- FR10: The system shall handle partial, incomplete, or noisy extraction data gracefully.

## 7. Non-Functional Requirements
- NFR1: The system should return a comparison result in a timely manner for typical notice review workloads.
- NFR2: The comparison output should be explainable and easy for a human reviewer to interpret.
- NFR3: The system should avoid false positives for clearly cosmetic changes where possible.
- NFR4: The system should be robust to missing values, inconsistent formatting, and extraction noise.
- NFR5: The system should maintain auditability and traceability for each comparison decision.
- NFR6: The system should support future rule tuning or configuration without requiring a redesign.

## 8. Confirm Step Success Metrics
The confirm step is the human review action that validates or overrides the system’s recommendation. Success will be measured by the following metrics:
- Confirmation completion rate: at least 95% of generated comparisons should reach a completed confirm action.
- Median confirm time: the average reviewer should be able to confirm a comparison in under 60 seconds for standard cases.
- Reviewer agreement rate: at least 85% of confirm decisions should align with the system’s recommendation when the comparison is clear and non-ambiguous.
- Override rate: the rate of reviewer overrides should remain low for straightforward cases and be reviewed to improve comparison quality over time.
- Audit completeness: 100% of confirm actions should be stored with the relevant comparison evidence and final decision.

## 9. Success Criteria
The initiative is successful if the tool reduces manual review effort, surfaces relevant changes clearly, and gives reviewers enough confidence to make fast, consistent confirm decisions.
