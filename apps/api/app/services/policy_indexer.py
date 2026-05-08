import os
import re
import uuid

from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding
from app.services.hybrid_retriever import hybrid_retriever

COLLECTION_NAME = "policies"


def parse_policy_file(text: str) -> dict:
    """
    Parse structured policy text file.
    """

    lines = [l.strip() for l in text.splitlines()]

    policy_name = lines[0] if lines else "Unknown Policy"

    sections = {
        "Purpose": "",
        "Definition": "",
        "Violation Indicators": [],
        "Examples": [],
        "Risk Level": "",
        "Escalation Guidance": ""
    }

    current_section = None

    for line in lines[1:]:

        if not line:
            continue

        matched_section = False

        for section in sections.keys():

            if line.startswith(f"{section}:"):

                current_section = section

                value = line.replace(f"{section}:", "").strip()

                if isinstance(sections[section], list):
                    if value:
                        sections[section].append(value)
                else:
                    sections[section] = value

                matched_section = True
                break

        if matched_section:
            continue

        if current_section:

            if isinstance(sections[current_section], list):

                cleaned = re.sub(r"^- ", "", line).strip()

                if cleaned:
                    sections[current_section].append(cleaned)

            else:
                sections[current_section] += " " + line

    return {
        "policy_name": policy_name,
        "purpose": sections["Purpose"].strip(),
        "definition": sections["Definition"].strip(),
        "violation_indicators": sections["Violation Indicators"],
        "examples": sections["Examples"],
        "risk_level": sections["Risk Level"].strip(),
        "escalation_guidance": sections["Escalation Guidance"].strip()
    }


def build_embedding_text(policy: dict) -> str:
    """
    Build normalized semantic text for embedding + BM25.
    """

    return f"""
Policy: {policy['policy_name']}

Purpose:
{policy['purpose']}

Definition:
{policy['definition']}

Violation Indicators:
{' '.join(policy['violation_indicators'])}

Examples:
{' '.join(policy['examples'])}

Risk Level:
{policy['risk_level']}

Escalation Guidance:
{policy['escalation_guidance']}
""".strip()


def validate_policy(policy: dict, source_file: str):

    required_fields = [
        "policy_name",
        "definition",
        "risk_level"
    ]

    for field in required_fields:

        if not policy.get(field):

            print(
                f"[PolicyIndexer] WARNING: Missing field "
                f"'{field}' in {source_file}"
            )


def index_policies():

    client = get_qdrant_client()

    print("[PolicyIndexer] Recreating Qdrant collection")

    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "size": 768,
            "distance": "Cosine"
        }
    )

    policies_path = "app/data/policies"

    all_files = [
        f for f in os.listdir(policies_path)
        if f.endswith(".txt")
    ]

    all_vectors = []
    all_payloads = []
    all_ids = []

    bm25_docs = []

    print(f"[PolicyIndexer] Found {len(all_files)} policy files")

    for file in all_files:

        path = os.path.join(policies_path, file)

        print(f"[PolicyIndexer] Processing {file}")

        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        policy = parse_policy_file(raw_text)

        validate_policy(policy, file)

        embedding_text = build_embedding_text(policy)

        vector = get_embedding(embedding_text)

        if vector is None:
            print(f"[PolicyIndexer] Embedding failed for {file}")
            continue

        policy_id = str(uuid.uuid4())
        policy_key = file.replace(".txt", "")

        payload = {
            "text": embedding_text,
            "content": embedding_text,

            "policy_name": policy["policy_name"],
            "policy_key": policy_key,
            "policy_file": file,
            "purpose": policy["purpose"],
            "definition": policy["definition"],

            "violation_indicators": policy["violation_indicators"],
            "examples": policy["examples"],

            "risk_level": policy["risk_level"],
            "escalation_guidance": policy["escalation_guidance"],

            "source": file,
            "doc_type": "policy",

            "page": None,

            "keywords": (
                policy["violation_indicators"]
                + policy["examples"]
                + [policy["risk_level"]]
            )
        }

        all_vectors.append(vector)
        all_payloads.append(payload)
        all_ids.append(policy_id)

        bm25_docs.append({
            "text": embedding_text,
            "source": file,
            "page": None,
            "doc_type": "policy"
        })

        print(f"[PolicyIndexer] Indexed policy: {policy['policy_name']}")

    print("[Hybrid] Building BM25 index for policies")

    hybrid_retriever.add_documents(bm25_docs)

    print(
        f"[Hybrid] BM25 loaded with "
        f"{len(bm25_docs)} policies"
    )

    print(
        f"[PolicyIndexer] Uploading "
        f"{len(all_vectors)} vectors to Qdrant"
    )

    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=all_vectors,
        payload=all_payloads,
        ids=all_ids
    )

    collection_info = client.get_collection(COLLECTION_NAME)

    print(
        "[PolicyIndexer] Collection stats: "
        f"points={collection_info.points_count}, "
        f"indexed_vectors={collection_info.indexed_vectors_count}"
    )

    return {
        "status": "policies_indexed",
        "policies": len(all_vectors)
    }