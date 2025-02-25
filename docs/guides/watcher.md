# Guide: Creating a Whale Watcher Agent

This guide walks you through creating a whale watcher agent that monitors blockchain transactions for transfers.

Auto Dev will scaffold the enitre project allowing you to focus on the business logic of the application, rather than the structure.

**Note**: Replace `author` in the commands below with your author name (e.g., alice, bob, etc.)

### Steps
- Plan the agent
- Scaffold the agent
- Implement the business logic

## 1. Create the FSM Specification from a Mermaid Diagram

First, create a [Mermaid diagram](https://mermaid.live/edit#pako:eNqNkm1rgzAQx7-K3MuhZZr5-GKw1kDLugralrE5StD0gakpaSzrit99me2U0TqWV7n__e5yd7kjJCyl4MFOEEH9DVlxkmt7Iy4UeV5v3hRNu1ciKsptyMoi9ZRIEC5O7lauqVGa0TPkBxN8YhqxRvoZS95DmtDNnqZntj8OBo-LEA_waI79U9QlV4c_ZJSLc9j0eRHMcbiYDkMcDYPx35HXHpYZZhP_3yl8Vly211bUzTTixSy7xnSd6agLc874T0ujJxzMpldr6-RaR83JT--uvnGCCjnlOdmkcnmO32gMYk1zGoMnryldkjITMcRFJVFSChYdigQ8wUuqAmflag3ekmQ7aZXbtF2-Rt2S4oWxXzZ4R_gAT0NIN3ro1kSW7bqW4dhIhYPULVfvmbZu39kWMl1Hr1T4rFMYPUvXkYtcwzEN20GGWX0BPbntug) to visualize the FSM. Create `whale_watcher_diagram.mmd`:

```text
stateDiagram-v2
    [*] --> SetupRound: Start
    SetupRound --> IdleRound: DONE
    IdleRound --> BlockReceivedRound: BLOCK_RECEIVED
    BlockReceivedRound --> AlertRound: TX_OVER_THRESHOLD
    BlockReceivedRound --> BlockReceivedRound: TX_UNDER_THRESHOLD
    BlockReceivedRound --> DoneRound: DONE
    AlertRound --> DoneRound: DONE
    DoneRound --> SetupRound: DONE
    IdleRound --> SetupRound: DONE
    BlockReceivedRound --> ErrorRound: TIMEOUT
    AlertRound --> ErrorRound: TIMEOUT
    ErrorRound --> [*]: DONE
    DoneRound --> [*]: DONE
```

```mermaid
stateDiagram-v2
    [*] --> SetupRound: Start
    SetupRound --> IdleRound: DONE
    IdleRound --> BlockReceivedRound: BLOCK_RECEIVED
    BlockReceivedRound --> AlertRound: TX_OVER_THRESHOLD
    BlockReceivedRound --> BlockReceivedRound: TX_UNDER_THRESHOLD
    BlockReceivedRound --> DoneRound: DONE
    AlertRound --> DoneRound: DONE
    DoneRound --> SetupRound: DONE
    IdleRound --> SetupRound: DONE
    BlockReceivedRound --> ErrorRound: TIMEOUT
    AlertRound --> ErrorRound: TIMEOUT
    ErrorRound --> [*]: DONE
    DoneRound --> [*]: DONE
```

This diagram represents the following states and transitions:
- `SetupRound`: Initial setup and configuration
- `IdleRound`: Waiting for new blocks
- `BlockReceivedRound`: Processing a new block's transactions
- `AlertRound`: Handling whale transactions
- `DoneRound`: Completed processing
- `ErrorRound`: Error handling state

Now convert the Mermaid diagram to FSM specification which is used to scaffold the agent.

```bash
adev fsm from-file whale_watcher_diagram.mmd WhaleWatcherAbciApp --in-type mermaid --output fsm_spec > whale_watcher_fsm.yaml
```

This will create `whale_watcher_fsm.yaml` with the FSM specification that includes:
- Input alphabet (events like BLOCK_RECEIVED, TX_OVER_THRESHOLD)
- States and transitions
- Start and final states
- Complete transition function

The [FSM SPecification](https://docs.autonolas.network/open-autonomy/key_concepts/fsm/) defines the states that the agent will move between.

## 2. Create Agent from FSM

Generate the initial agent structure from the FSM definition:

```bash
adev create_from_fsm author/whale_watcher whale_watcher_fsm.yaml
```

This will create an agent with a very basic fsm in place.

The agent will be ejected to the local packages registry.

### 2.a) (OPTIONAL)

Run generated tests to verify the agent;

```bash
adev test -p packages/author/agents/whale_watcher
```

## 3. Extend the Scaffold to interact with contracts and components.

Install the necessary contract and connection:

```bash
cd whale_watcher
aea add connection bafybeigntoericenpzvwejqfuc3kqzo2pscs76qoygg5dbj6f4zxusru5e
aea add contract bafybeigovz3fg5g46f5geyy33fpvuof3ewktslxswipk37fqpmfj42uysi
```

## 4. Eject and Customize the Skill

```bash
adev eject skill author/whale_watcher_abci_app author/whale_watcher_abci_app
```

## 5. Implement the Components

Create the following files in your skill directory:

- `behaviours.py`: Implements the FSM behavior states
- `dialogues.py`: Handles dialogue management
- `handlers.py`: Implements message handlers
- `skill.yaml`: Configures the skill components

## 6. Publish the Agent

```bash
cd whale_watcher
adev publish author/whale_watcher --force
```

## 7. Run the Agent

```bash
cd ..
adev run dev author/whale_watcher --force
```

## 8. (optional) convert the agent to a service

```bash
adev convert author/whale_watcher author/finished_whale_watcher
```
and then run it

```bash
autonomy generate-key ethereum -n 1 

adev run prod author/finished_whale_watcher
```

To see the complete implementation, you can fetch the finished agent:

```bash
aea fetch bafybeicr5wi5r4f272rxybgb4jcpksnylktm5qnzi3ldltbdxnjk4yq24e
```
