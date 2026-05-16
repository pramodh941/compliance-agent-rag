# Contributing to compliance-agent-rag

Thanks for your interest in contributing.

## Project Goals

This project focuses on:
- compliance-oriented RAG systems
- agent orchestration
- grounded retrieval
- lightweight local-first AI infrastructure
- production-oriented architecture patterns

## Contribution Guidelines

Please discuss large architectural or workflow changes before implementation.

Especially for:
- ingestion pipeline redesigns
- agent orchestration changes
- retrieval/reranking architecture
- API contract modifications
- infrastructure/runtime changes

## Design Principles

Contributions should preserve:

- local-lite compatibility
- CPU-only usability where possible
- optional heavy dependencies
- clear separation of services
- reproducible local development
- grounded retrieval behavior

## Dependency Policy

Heavy dependencies must remain optional whenever practical.

Examples:
- OCR tooling
- GPU-only libraries
- large embedding/reranking frameworks

## Pull Requests

Before opening a PR:

- run tests locally
- verify Docker compose startup
- avoid unrelated refactors
- keep PRs focused and small when possible

## Branching

Please avoid pushing directly to `main`.

Use:
- feature branches
- pull requests
- discussion-first workflow for major changes

## Security

Do not commit:
- secrets
- credentials
- API keys
- production datasets
- internal infrastructure configs

## Questions / Ideas

Use GitHub Discussions or Issues before implementing major proposals.