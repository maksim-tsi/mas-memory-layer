# Embedding Test Data

This directory contains test documents for evaluating embedding generation and semantic similarity.

## Contents

### Computer Science Topics (3 documents)

1. **distributed_systems.md** (~1000 words)
   - Topics: Distributed systems architecture, microservices, CAP theorem, data management patterns
   - Focus: Software engineering, system design, scalability

2. **mlops_practices.txt** (~1000 words)
   - Topics: MLOps, CI/CD for ML, model deployment, monitoring, experiment tracking
   - Focus: Machine learning operations, DevOps, production ML systems

3. **quantum_computing.html** (~1000 words)
   - Topics: Quantum computing fundamentals, qubits, quantum algorithms, hardware implementations
   - Focus: Quantum mechanics, computational theory, emerging technologies

### Logistics Topics (3 documents)

1. **supply_chain_optimization.md** (~1000 words)
   - Topics: Network analysis, optimization models, mathematical programming, simulation
   - Focus: Supply chain management, operations research, logistics optimization

2. **warehouse_automation.txt** (~1000 words)
   - Topics: WMS, autonomous robots, AS/RS, inventory management, slotting optimization
   - Focus: Warehouse operations, automation technologies, material handling

3. **last_mile_delivery.html** (~1000 words)
   - Topics: Last-mile logistics, route optimization, alternative delivery models, sustainability
   - Focus: Urban logistics, delivery operations, customer experience

## Usage

These documents are used for:
- Testing embedding generation with `gemini-embedding-001`
- Evaluating semantic similarity and clustering
- Validating episode consolidation in the memory system
- Benchmarking vector search performance

## Format Diversity

The documents use three different formats (.md, .txt, .html) to test:
- Content extraction from various file types
- Consistent embedding quality across formats
- Format-agnostic processing pipelines
