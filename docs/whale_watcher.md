# Creating a Whale Watcher Agent

This guide walks you through creating a whale watcher agent that monitors blockchain transactions for large transfers (whale movements).

## Prerequisites

- Ensure you have `auto_dev` installed and set up
- Access to an Ethereum RPC endpoint (you'll need to set this in your environment variables)
- Basic understanding of blockchain concepts and ERC20 tokens

## Step-by-Step Guide

### 1. Scaffold the Repository

First, create a new repository structure:

```bash
adev scaffold repo some_agent
```

### 2. Create the Agent

Create a new agent based on the base template:

```bash
adev create your_name/some_agent -t eightballer/base --no-clean-up
```

### 3. Navigate to Agent Directory

```bash
cd some_agent
```

### 4. Eject the Metrics Skill

```bash
aea -s eject skill eightballer/metrics
```

### 5. Create the FSM Configuration

Create a file named `your_fsm.yaml` with the following content:

```yaml
alphabet_in:
  - BLOCK_RECEIVED        # A new Ethereum block is detected
  - TX_OVER_THRESHOLD     # A transaction exceeds the whale threshold
  - TX_UNDER_THRESHOLD    # A transaction is under the whale threshold
  - DONE                  # All transactions for this block are processed
  - TIMEOUT              # A timeout or other error occurs

default_start_state: IdleRound

final_states:
  - ErrorRound
  - DoneRound

label: WhaleWatcherAbciApp

start_states:
  - IdleRound

states:
  - IdleRound
  - BlockReceivedRound
  - AlertRound
  - DoneRound
  - ErrorRound

transition_func:
  # 1. From Idle -> BlockReceived when a new block arrives
  (IdleRound, BLOCK_RECEIVED): BlockReceivedRound

  # 2. In BlockReceived, if a transaction is over threshold -> Alert
  (BlockReceivedRound, TX_OVER_THRESHOLD): AlertRound

  # 3. In BlockReceived, if a transaction is under threshold -> stay in BlockReceived
  (BlockReceivedRound, TX_UNDER_THRESHOLD): BlockReceivedRound

  # 4. After all transactions are processed in BlockReceived -> DoneState
  (BlockReceivedRound, DONE): DoneRound

  # 5. From Alert, once done handling that whale transaction -> DoneState
  (AlertRound, DONE): DoneRound

  # 6. Any TIMEOUT event -> ErrorState
  (BlockReceivedRound, TIMEOUT): ErrorRound
  (AlertRound, TIMEOUT): ErrorRound
```

### 6. Generate Behaviour Code

Generate the behaviour code from your FSM configuration:

```bash
adev scaffold behaviour --behaviour-type simple_fsm your_fsm.yaml > skills/metrics/behaviours.py
```

### 7. Update Skill Configuration

Modify the `skill.yaml` file to include your behaviour:

```yaml
behaviours:
  metrics_handler:
    args: {}
    class_name: WhalewatcherabciappFsmBehaviour
```

### 8. Fingerprint the Skill

```bash
aea fingerprint skill your_name/metrics:0.1.0
```

### 9. Publish Locally

```bash
aea publish --local --push-missing
```

### 10. Run the Agent

```bash
cd .. && adev run your_name/some_agent
```

## Environment Variables

Create a `.env` file in your agent's directory with:

```env
RPC_URL=your_ethereum_rpc_endpoint
WHALE_THRESHOLD=1000  # Threshold in ETH to consider an address a whale
```

## Customization

The whale watcher agent can be customized by:

1. Adjusting the `WHALE_THRESHOLD` in your environment variables
2. Modifying the alert format in the `AlertRound` class
3. Adding additional monitoring parameters in the `BlockReceivedRound` class
4. Implementing different alert delivery mechanisms in the `AlertRound` class

## Monitoring Features

The agent monitors:
- ERC20 token transfers
- Whale addresses (addresses with balance > threshold)
- Transaction details and balances
- Block-by-block updates

## Alert Format

Alerts include:
- Transaction hash and link
- Token contract address
- Sender and receiver addresses
- Wallet balances
- Blockchain explorer links

## Error Handling

The agent includes comprehensive error handling:
- Timeout management
- RPC connection issues
- Transaction decoding errors
- Recovery mechanisms

## Best Practices

1. Always use environment variables for sensitive data
2. Implement proper error handling
3. Use checksum addresses
4. Cache known whale addresses
5. Implement rate limiting for RPC calls
6. Monitor gas usage and costs
7. Keep logs for debugging and monitoring

## Troubleshooting

Common issues and solutions:
1. RPC Connection Issues: Check your RPC endpoint and internet connection
2. Missing Environment Variables: Ensure all required environment variables are set
3. Decoding Errors: Verify contract ABI and event signatures
4. Performance Issues: Adjust batch sizes and polling intervals 