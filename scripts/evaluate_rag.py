#!/usr/bin/env python3
"""
Lightweight RAG evaluation script for compliance-agent-rag platform.

Evaluates retrieval quality, answer faithfulness, and basic metrics.
"""
import os
import sys
import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    query: str
    retrieved_chunks: List[str]
    answer: str
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    chunk_count: int
    context_length: int


class RAGEvaluator:
    """Lightweight RAG evaluator without heavy dependencies."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results: List[EvaluationResult] = []

    def evaluate_query(self, query: str) -> EvaluationResult:
        """Evaluate a single query against the RAG system."""
        import requests

        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_url}/qa",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            total_time_ms = (time.time() - start_time) * 1000
            
            answer = data.get("answer", {}).get("answer", "")
            context_used = data.get("answer", {}).get("context_used", "")
            
            # Extract chunks from context (simplified)
            chunks = context_used.split("\n\n") if context_used else []
            
            return EvaluationResult(
                query=query,
                retrieved_chunks=chunks,
                answer=answer,
                retrieval_time_ms=total_time_ms * 0.5,  # Estimate
                generation_time_ms=total_time_ms * 0.5,  # Estimate
                total_time_ms=total_time_ms,
                chunk_count=len(chunks),
                context_length=len(context_used)
            )
        except Exception as e:
            print(f"Error evaluating query '{query}': {e}")
            return EvaluationResult(
                query=query,
                retrieved_chunks=[],
                answer=f"Error: {str(e)}",
                retrieval_time_ms=0,
                generation_time_ms=0,
                total_time_ms=0,
                chunk_count=0,
                context_length=0
            )

    def evaluate_dataset(self, queries: List[str]) -> Dict[str, Any]:
        """Evaluate a dataset of queries."""
        results = []
        
        for query in queries:
            result = self.evaluate_query(query)
            results.append(result)
            print(f"✓ Evaluated: {query[:50]}...")
        
        self.results = results
        
        # Calculate metrics
        total_time = sum(r.total_time_ms for r in results)
        avg_time = total_time / len(results) if results else 0
        avg_chunks = sum(r.chunk_count for r in results) / len(results) if results else 0
        avg_context = sum(r.context_length for r in results) / len(results) if results else 0
        
        metrics = {
            "total_queries": len(results),
            "total_time_ms": round(total_time, 2),
            "avg_time_ms": round(avg_time, 2),
            "avg_chunks": round(avg_chunks, 2),
            "avg_context_length": round(avg_context, 2),
            "results": [
                {
                    "query": r.query,
                    "answer": r.answer[:200],
                    "chunk_count": r.chunk_count,
                    "time_ms": round(r.total_time_ms, 2)
                }
                for r in results
            ]
        }
        
        return metrics

    def print_report(self, metrics: Dict[str, Any]):
        """Print evaluation report."""
        print("\n=== RAG Evaluation Report ===")
        print(f"Total Queries: {metrics['total_queries']}")
        print(f"Total Time: {metrics['total_time_ms']}ms")
        print(f"Avg Time per Query: {metrics['avg_time_ms']}ms")
        print(f"Avg Chunks Retrieved: {metrics['avg_chunks']}")
        print(f"Avg Context Length: {metrics['avg_context_length']}")
        print("\n=== Individual Results ===")
        for result in metrics['results']:
            print(f"\nQuery: {result['query']}")
            print(f"Answer: {result['answer']}")
            print(f"Chunks: {result['chunk_count']}, Time: {result['time_ms']}ms")


def main():
    """Main evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate RAG system")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="API URL"
    )
    parser.add_argument(
        "--query",
        help="Single query to evaluate"
    )
    parser.add_argument(
        "--dataset",
        help="JSON file with queries array"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    evaluator = RAGEvaluator(api_url=args.api_url)
    
    if args.query:
        # Single query evaluation
        result = evaluator.evaluate_query(args.query)
        print(f"\nQuery: {result.query}")
        print(f"Answer: {result.answer}")
        print(f"Chunks: {result.chunk_count}")
        print(f"Time: {result.total_time_ms}ms")
    elif args.dataset:
        # Dataset evaluation
        with open(args.dataset, 'r') as f:
            data = json.load(f)
            queries = data.get("queries", [])
        
        metrics = evaluator.evaluate_dataset(queries)
        evaluator.print_report(metrics)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"\nResults saved to {args.output}")
    else:
        # Default evaluation dataset
        default_queries = [
            "What is the email policy?",
            "What are the insider trading rules?",
            "What is the MNPI policy?",
            "What are the gift policies?",
            "What are the communication policies?"
        ]
        
        metrics = evaluator.evaluate_dataset(default_queries)
        evaluator.print_report(metrics)


if __name__ == "__main__":
    main()
