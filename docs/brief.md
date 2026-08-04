# Notice Comparison Tool Brief

## Summary
The Notice Comparison Tool compares two structured extraction results from different versions of the same notice and determines whether they are the same or materially different. The tool is intended to support a human reviewer by surfacing likely changes, highlighting the evidence, and making the final decision reviewable.

## Problem Statement
Organizations often receive multiple versions of notices over time, such as legal notices, regulatory updates, or contractual communications. These versions may contain minor wording changes, formatting updates, or substantive changes that affect obligations, deadlines, payments, parties, or compliance requirements. Manually comparing them is time-consuming and error-prone.

This tool aims to reduce that effort by automatically comparing the structured extracted data from two notices and classifying the result as:
- same,
- materially different, or
- uncertain / needs human review.

## Product Goal
Provide a reliable, explainable comparison workflow that helps users quickly identify whether two notice versions are effectively unchanged or materially different, with a human in the loop to confirm the outcome.

## Primary Users
- Compliance analysts
- Legal operations teams
- Operations staff handling notice intake and review
- Teams maintaining document extraction pipelines

## Core Use Case
A user uploads or references two extraction results for notice versions A and B. The system compares the structured data, identifies differences, assesses whether those differences are likely material, and returns a recommendation along with supporting evidence. A human reviewer then confirms or overrides the result.

## Functional Requirements
1. Compare two structured extraction results.
2. Normalize values where appropriate to reduce noise from formatting or representation differences.
3. Detect and categorize differences such as:
   - added or removed fields,
   - changed values,
   - changed dates or amounts,
   - changed parties or obligations,
   - reordered or repeated sections.
4. Produce a comparison summary with clear evidence for each difference.
5. Classify the result as:
   - same,
   - materially different,
   - uncertain / requires review.
6. Support human confirmation or override of the automated result.
7. Preserve auditability by recording the comparison inputs, detected differences, and final decision.

## Comparison Logic
The tool should not rely only on exact string equality. It should account for common variations such as:
- whitespace differences,
- date format differences,
- unit conversions,
- case differences,
- reordering of list items when order is not meaningful,
- empty versus missing values.

The system should also prioritize changes that are likely to matter in practice, such as modifications to:
- deadlines,
- obligations,
- parties involved,
- financial amounts,
- jurisdiction or applicability,
- critical legal language.

## Edge Cases
The tool should handle the following carefully:
- One or both extraction results are incomplete or partially missing data.
- OCR or extraction errors introduce minor inconsistencies.
- A change is purely cosmetic, such as reformatting or punctuation.
- A change is semantically equivalent but expressed differently.
- The same information appears in a different section or order.
- A field is present in one version but absent in the other.
- Values are close but not identical, such as dates or amounts that differ slightly.
- The comparison is ambiguous, and a human reviewer is needed.

## Assumptions
- The input data is already structured and can be compared programmatically.
- Each extraction result contains enough metadata to identify the underlying notice and version.
- The tool is intended to support review, not replace legal judgment.
- "Material difference" is assessed using a practical business rule set, with human review available for exceptions.
- The system may use heuristics and configurable rules rather than a perfect legal interpretation engine.

## Non-Goals
- Fully interpreting legal meaning without human review
- Replacing formal legal advice
- Parsing raw documents from scratch if structured extraction data is already available
- Guaranteeing perfect accuracy in every edge case

## Success Criteria
The tool is successful if it helps users quickly identify likely differences, reduces manual comparison effort, and produces clear, explainable outputs that a human reviewer can trust and confirm.
