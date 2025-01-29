# Autonolas Documentation

## Overview

Autonolas is a decentralized protocol designed to automate complex workflows and operations on blockchain networks. It enables the creation and management of autonomous agents that can interact with smart contracts, resulting in enhanced efficiency and scalability for decentralized applications. This page provides insights into the architectures of Open AEA and Open Autonomy, which auto_dev relies on, as well as the role of registry contracts within this framework.

## Open AEA Architecture

The Open Autonomous Economic Agent (AEA) framework is designed to support the development of intelligent agents that operate autonomously on behalf of their owners. The key components of the Open AEA architecture include:

![Open AEA Architecture](assets/simplified-aea.svg)

1. **Agent Framework**: The core component where autonomous agents are defined and managed. It encompasses the logic for executing tasks based on specific triggers and conditions. Agents can be customized to suit various operational needs.

2. **Decision Maker**: The economic brain of the AEA, managing goals, preferences, and wallet control. It determines the best actions for the agent to take based on its objectives.

3. **Skills**: Self-contained capabilities that agents can adopt to enhance effectiveness. Skills can implement both reactive and proactive behaviors, allowing agents to adapt to their environments dynamically.

4. **Envelopes and Protocols**: Envelopes are used for message wrapping, while protocols define the rules for communication between agents, facilitating interaction in a multi-agent ecosystem.

5. **Connections**: Managed by a multiplexer, connections enable agents to communicate with other agents and external services through the Agent Communication Network (ACN).

## Open Autonomy Architecture

![Agent Service Architecture](assets/agent_service_architecture.svg)

The Open Autonomy framework expands the capabilities of the Open AEA by providing tools for creating agent services that run as a multi-agent system (MAS). Key components of the Open Autonomy architecture include:

1. **Agent Services**: Off-chain autonomous services that leverage the capabilities of multiple AEAs to execute complex operations. These services enhance the functionality of traditional smart contracts.

2. **Registry Contracts**: Essential for managing the registration and management of agents, components, and services. They provide structured storage and retrieval of information, ensuring reliable interactions within the ecosystem.

   ### Types of Registry Contracts

   - **Component Registry**: Manages the registration of components, tracking metadata, dependencies, and enabling lookup by agents.
   - **Service Registry**: Maintains a list of available services, allowing agents to discover and interact with service providers.
   - **Registries Manager**: Centralized controller for managing different types of registries, ensuring unified management and access control.

3. **Event Listener**: Monitors the blockchain for relevant events that trigger agent actions, enabling real-time responsiveness.

4. **Task Scheduler**: Manages the timing of task execution for agents, ensuring that they operate according to their defined schedules and conditions.

5. **Monitoring and Analytics**: Provides tools for tracking agent performance and logging actions, facilitating data analysis for optimization.

## Workflow of Autonolas Agents

The workflow of an Autonolas agent involves several sequential steps:

1. **Initialization**: Define the agent's purpose, conditions, and tasks.
2. **Deployment**: Deploy the agent on the blockchain, making it operational.
3. **Event Monitoring**: Continuously listen for relevant blockchain events that may trigger agent actions.
4. **Execution**: Upon detecting a trigger event, the agent executes its predefined tasks, potentially interacting with registry contracts to access components and services.
5. **Feedback Loop**: Monitor outcomes and adjust the agent's logic as necessary to enhance operational efficiency.

## Conclusion

The combined architectures of Open AEA and Open Autonomy, alongside the role of registry contracts, provide a robust foundation for developing and deploying autonomous agents within blockchain ecosystems. This framework enables efficient automation of complex workflows while ensuring reliability and scalability.
