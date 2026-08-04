# UX Specification: Side-by-Side Human-Readable Comparison View

## 1. Purpose
This specification defines the user experience for Story 8.2: a side-by-side comparison view that helps a human reviewer inspect two notice extraction results in parallel, understand the differences clearly, and confirm whether the notices match or materially differ.

## 2. User Context
Users are reviewers who need to compare two versions of a notice quickly and confidently. They may not want to inspect raw structured data directly, so the interface should present the comparison in a readable, contextual format with obvious visual cues.

## 3. Core Experience
The interface displays two documents side by side:
- Left panel: Version A / original extraction result
- Right panel: Version B / revised extraction result

Each panel shows the extracted fields in a readable structure, with differences highlighted between the two sides.

## 4. Layout
### 4.1 Page Structure
- Top header:
  - Document titles or identifiers
  - Comparison status badge (e.g. "No material differences", "Material differences detected", "Needs review")
  - Primary action buttons: "Confirm Match", "Confirm Mismatch", "Need More Review"
- Main comparison area:
  - Two-column layout, one column per document
  - A vertical divider separates the columns
- Optional summary panel:
  - A compact list of key changes above or below the main comparison view

### 4.2 Column Behavior
- Each column scrolls independently when the content is long.
- The two columns remain aligned by logical field groupings so that the reviewer can compare corresponding sections effortlessly.
- When a field is missing in one version, the interface displays an empty state or a clearly labeled "Not present" indicator.

## 5. Visual Language for Differences
The following visual treatments should be used consistently:

- Added field:
  - Highlight with a green background or green left border
  - Label: "Added"
  - Optional icon: "+"

- Removed field:
  - Highlight with a red background or red left border
  - Label: "Removed"
  - Optional icon: "-"

- Changed field:
  - Highlight with an amber or blue background
  - Label: "Changed"
  - Show old value and new value in a stacked or inline comparison format

- Unchanged field:
  - Neutral styling with no special highlight

### 5.1 Field Row Design
Each field row should include:
- Field name
- Value for Version A
- Value for Version B
- A status chip indicating whether the field is unchanged, added, removed, or changed

## 6. Comparison Patterns
### 6.1 Simple Scalar Fields
For fields such as dates, amounts, names, or statuses:
- Show values directly in each column
- Highlight the row if values differ
- Display the old/new values in a compact inline comparison if space allows

### 6.2 Lists or Repeated Items
For repeated entries or arrays:
- Display each item as a separate sub-row
- Preserve order where meaningful, but allow grouping when order is not meaningful
- Highlight item-level additions, removals, and changes

### 6.3 Nested Sections
For grouped or nested data:
- Render section headers and nested rows in a tree-like structure
- Allow expansion/collapse of sections
- Keep associated sections aligned across both columns

## 7. Confirmation Flow
### 7.1 Match / Mismatch Confirmation
The reviewer should be able to confirm the result with a clear, low-friction action set:
- Confirm Match: use when the documents are effectively the same
- Confirm Mismatch: use when the documents are materially different
- Need More Review: use when the comparison is ambiguous or incomplete

### 7.2 Confirmation Interaction Pattern
- The reviewer reviews the comparison view
- The reviewer selects one primary action
- The system prompts for optional comments or rationale if needed
- The system records the decision and the reviewed evidence

### 7.3 Confirmation States
- Default state: action buttons enabled, no selection made
- Selected state: chosen action is highlighted
- Submitted state: confirmation is stored and the page updates to show the final status

## 8. Accessibility Considerations
The interface should be accessible to users with varying abilities and device constraints.

### 8.1 Visual Accessibility
- Use sufficient color contrast for highlighted states
- Do not rely on color alone to indicate added, removed, or changed fields
- Include text labels and icons for each status
- Support keyboard navigation for all interactive elements

### 8.2 Screen Reader Support
- Each difference row should expose semantic meaning through screen-reader-friendly labels
- Status chips should be announced clearly (for example, “Changed field”)
- The comparison view should have a logical reading order

### 8.3 Motion and Focus
- Avoid unnecessary animation
- Provide visible focus indicators for buttons and rows
- Ensure the layout remains usable at browser zoom levels and on smaller screens

### 8.4 Language and Clarity
- Use plain, direct language for labels such as “Added”, “Removed”, and “Changed”
- Keep field names readable and consistent
- Avoid overloading the interface with technical jargon

## 9. Content and Interaction Details
- The default view should prioritize high-signal differences first
- The system should allow the reviewer to jump to the next difference quickly
- The interface should preserve context for each highlighted field to reduce confusion
- If the review is inconclusive, the user should be able to leave the comparison unresolved and request further review

## 10. Success Criteria
The experience is successful if a reviewer can:
- understand the differences between two notice versions quickly,
- identify whether the changes are material or cosmetic,
- make a confident confirmation decision with minimal effort,
- and complete the review without needing to inspect raw extraction data manually.
