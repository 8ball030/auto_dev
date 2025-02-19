# Updating Dependencies

Updating hthe depenedncies of autodev projects is handled simply and easily by the `adev` applciation.

```mermaid
graph TD
  setupRound
  checkRepoDependenciesRound
  noUpdatesRound
  updatesRound
  createPrRound
  alertOwnerRound
  finalRound

  setupRound -->|DONE| checkRepoDependenciesRound
  checkRepoDependenciesRound -->|DONE| noUpdatesRound
  checkRepoDependenciesRound -->|UPDATES_FOUND| updatesRound
  noUpdatesRound -->|DONE| finalRound

  updatesRound -->|DONE| createPrRound
  createPrRound -->|DONE| alertOwnerRound
  createPrRound -->|DONE| finalRound
  finalRound -->|DONE| setupRound
```

The above command fsm represents the necessary flwo to perform the the updates manually.

Effectively the necessary steps are;

1. checkout main

2. run the following command;

```bash
adev deps bump --latest --strict
```
