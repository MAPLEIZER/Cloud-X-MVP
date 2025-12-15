# 2-Week Development Plan: Cloud-X Next.js UI

This document outlines a 14-day plan to develop a new web-based UI for the Cloud-X Security Scanner using Next.js, shad/cn UI, React, and Tailwind CSS.

## Week 1: Foundation & Core UI Development

### Day 1-2: Project Setup & API Integration Strategy

- **Task**: Initialize a new Next.js project.
- **Task**: Install and configure Tailwind CSS.
- **Task**: Set up `shad/cn` and initialize the required theme and base components.
- **Task**: Analyze the existing Flask API endpoints to understand the data contracts for scans, results, and AI features.
- **Task**: Define and implement a strategy for the Next.js app to communicate with the Flask backend (e.g., using a proxy in `next.config.js` to handle CORS and simplify API calls).

### Day 3-4: Core Component Library & Application Layout

- **Task**: Build a library of reusable UI components using `shad/cn`. This includes:
  - `Button`
  - `Card`, `CardHeader`, `CardContent`, `CardFooter`
  - `Input`
  - `Progress`
  - `Tabs`
  - `Accordion`
  - `Alert`, `AlertTitle`, `AlertDescription`
- **Task**: Design and implement the main application layout (`layout.tsx`) including a persistent sidebar for navigation and a header.

### Day 5: Dashboard & Scan Initiation

- **Task**: Develop the main dashboard page (`/`).
- **Task**: Implement the primary feature: a simple input form for users to enter a domain and start a security scan.
- **Task**: Manage form state using React hooks (`useState`, `useForm`).
- **Task**: Implement the API call to the Flask backend to initiate a new scan job and handle the response, redirecting to the progress page upon success.

### Day 6-7: Real-Time Scan Progress Page

- **Task**: Create the dynamic scan progress page at `/scan/[job_id]`.
- **Task**: Implement a mechanism to fetch and display real-time scan progress. This will likely involve polling a status endpoint from the Flask/Celery backend every few seconds.
- **Task**: Use `Progress` bars and textual updates (`e.g., "Running Nmap port scan..."`) to provide visual feedback to the user, as described in the `README.md`.
- **Task**: Implement a "close and return later" feature, allowing the user to navigate away while the scan continues in the background.

## Week 2: Results, Reporting & Final Polish

### Day 8-9: Vulnerability Results Page

- **Task**: Develop the results page at `/results/[job_id]`.
- **Task**: Display the high-level executive summary using `Card` components to show counts of Critical, Medium, and Low-risk findings.
- **Task**: Implement a detailed findings list using an `Accordion` component, allowing users to expand each vulnerability to see details, AI-generated summaries, and MITRE ATT&CK context.
- **Task**: Style findings based on severity (e.g., red for Critical, orange for Medium).

### Day 10-11: AI-Powered Reporting & Smart Summaries

- **Task**: Integrate the AI-generated report content from the backend.
- **Task**: Use `Tabs` to create different views for various report types (Executive, Technical, Compliance).
- **Task**: Display AI-generated executive summaries and remediation advice prominently.
- **Task**: Implement a feature to download the reports.

### Day 12: Scan History & Search

- **Task**: Create a `/history` page that lists all previous scans for the user.
- **Task**: Fetch the list of scans from the backend and display it in a `Table` component.
- **Task**: Implement the client-side UI for the "Semantic Vulnerability Search" feature, allowing users to search across all scan results.

### Day 13: Responsiveness & End-to-End Testing

- **Task**: Ensure the entire application is fully responsive and provides a seamless experience on mobile, tablet, and desktop devices.
- **Task**: Conduct end-to-end testing of the user flow: starting a scan, viewing progress, and analyzing results.
- **Task**: Identify and fix any remaining bugs or UI inconsistencies.

### Day 14: Documentation & Final Polish

- **Task**: Update the project's `README.md` to reflect the new Next.js frontend stack.
- **Task**: Add a section on how to run the new frontend development server.
- **Task**: Perform a final review of the UI/UX for polish and clarity.
- **Task**: Prepare for a final demo and deployment.
