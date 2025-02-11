# Guide: Creating a Whale Watcher Agent

This guide walks you through creating a whale watcher agent that monitors blockchain transactions for transfers.

**Note**: Replace `author` in the commands below with your author name (e.g., alice, bob, etc.)

## 1. Create the FSM Definition

Create `whale_watcher_fsm.yaml`:

```yaml
alphabet_in:
  - BLOCK_RECEIVED        # A new Ethereum block is detected
  - TX_OVER_THRESHOLD     # A transaction exceeds the whale threshold
  - TX_UNDER_THRESHOLD    # A transaction is under the whale threshold
  - DONE                  # All transactions for this block are processed
  - TIMEOUT              # A timeout or other error occurs

default_start_state: SetupRound
label: WhaleWatcherAbciApp

states:
  - SetupRound
  - IdleRound
  - BlockReceivedRound
  - AlertRound
  - DoneRound
  - ErrorRound

start_states:
  - SetupRound

final_states:
  - ErrorRound
  - DoneRound

transition_func:
  (SetupRound, DONE): IdleRound
  (IdleRound, BLOCK_RECEIVED): BlockReceivedRound
  (BlockReceivedRound, TX_OVER_THRESHOLD): AlertRound
  (BlockReceivedRound, TX_UNDER_THRESHOLD): BlockReceivedRound
  (BlockReceivedRound, DONE): DoneRound
  (AlertRound, DONE): DoneRound
  (DoneRound, DONE): SetupRound
  (IdleRound, DONE): SetupRound
  (BlockReceivedRound, TIMEOUT): ErrorRound
  (AlertRound, TIMEOUT): ErrorRound
```

## 2. Create Agent from FSM

Generate the initial agent structure from the FSM definition:

```bash
adev create_from_fsm author/whale_watcher whale_watcher_fsm.yaml
```

## 3. Add Required Components

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
aea fetch bafybeia3yyss6j3ac2hbhmhg7o7mbytspe4cgqfrpg6y5eskowln2rlqxe
```