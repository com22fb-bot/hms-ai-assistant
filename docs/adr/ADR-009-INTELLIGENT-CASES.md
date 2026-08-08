# ADR-009 — Intelligent Cases as Primary Domain Model

**Status:** Accepted  
**Date:** 2026-07-31

## Decision

The primary domain entity will be the Intelligent Case, not the email message or provider thread.

## Rationale

Business work frequently spans multiple messages, participants, folders, forwards and threads. A provider thread is insufficient to represent responsibility, fulfillment, risk and closure.

## Consequences

- A correlation layer is mandatory.
- Messages become evidence linked to cases.
- Dashboard, notifications and statistics operate primarily on cases.
- Provider-specific identifiers remain technical references only.
