# YAAM Infrastructure Connectivity Audit

**Date:** April 5, 2026

## 1. Executive Summary

This report confirms that the foundation of the YAAM data layer is fully accessible and operationally ready. An infrastructure audit conducted from the development node (`skz-dev-lv`) verified uninterrupted connectivity to the underlying services running on the remote data node (`skz-data-lv`). The core database, vector storage, and search indexer are actively listening on their expected ports, enabling robust and direct integrations aligned with the target architecture for Variant B.

## 2. Network Map

The following services have been verified and are deployed in adherence to our architectural constraints. All connection strings have been structured utilizing network-accessible IP boundaries, explicitly adhering to the "No Localhost" rule. 

| Component | Target Node / IP Address | Target Port | Status | Protocol / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** (L2 Storage) | `192.168.107.187` | `5432` | 🟢 Verified | Direct TCP |
| **Qdrant** (Vector Store) | `192.168.107.187` | `6333` | 🟢 Verified | HTTP/TCP |
| **Typesense** (L4 Semantic Memory)| `192.168.107.187` | `8108` | 🟢 Verified | HTTP/TCP |

All endpoints have been exposed accurately on the remote node without relying on loopback interfaces.

## 3. Architectural Verdict

> [!IMPORTANT]  
> The explicit deployment omission of the YAAM Frontgate service on port `8002` marks a crucial shift toward Variant B architecture.

The connection audit confirmed that port `8002` resulted in a deliberate `Connection refused` mapping on both `192.168.107.172` and `192.168.107.187`. 

Therefore, any reference to **`YAAM_API_URL` targeting port `8002` is officially classified as deprecated legacy**. Specifically, placeholder variables matching this configuration found within the `scm-cognitive-sandwich` Orchestrator's `.env.example` must no longer be utilized.

Moving forward, the `scm-cognitive-sandwich` orchestrator will integrate with the YAAM components exclusively via **direct database drivers**, communicating directly over the endpoints verified and listed in the Network Map above. The external consolidator intermediary is being fully deprecated in favor of this direct communication pathway.
