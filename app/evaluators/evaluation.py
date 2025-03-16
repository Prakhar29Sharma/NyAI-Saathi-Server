import asyncio
from app.services.qdrant_service import QdrantService
from app.services.embedder_service import EmbedderService
from app.evaluators.context import judgement_context, laws_context
from app.dependencies.qdrant import get_qdrant_client
from app.core.config import settings
import google.generativeai as genai
import pandas as pd
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
if hasattr(settings, "GOOGLE_API_KEY"):
    api_key = settings.GOOGLE_API_KEY
else:
    api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("Google API Key not found in settings or environment variables")

# Configure Gemini API
genai.configure(api_key=api_key)

async def getQueryResponse(query: str, context: str, context_type: str = "judgement") -> str:
    """Get a response from Gemini for a legal query with context."""
    
    if context_type == "judgement":
        prompt = f"""
        You're a legal research assistant and given the following context of judgement,
        answer the user query and also provide references / document links for the verification of same.
        context : 
        {context}

        Question: {query}
        Answer:
        """
    else:  # laws
        prompt = f"""
        You're a legal research assistant and given the following context of laws and statutes,
        answer the user query by explaining the relevant legal provisions and citing specific sections.
        context : 
        {context}

        Question: {query}
        Answer:
        """

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return f"Error generating response: {str(e)}"

async def evaluate_faithfulness(context: str, answer: str) -> float:
    """
    Evaluate if the answer is faithful to the given context.
    Faithfulness measures if the generated answer is factually consistent with the provided context.
    """
    
    prompt = f"""
    Task: Evaluate if the answer is faithful to the given context.
    
    Context:
    {context}
    
    Answer:
    {answer}
    
    Instructions:
    1. Check if all information in the answer is present in the context.
    2. Check for any contradictions between the answer and context.
    3. Identify any hallucinated content (facts stated in the answer that aren't in the context).
    4. Rate the answer's faithfulness on a scale from 0 to 10.
    5. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating faithfulness: {e}")
        return 5.0

async def evaluate_answer_relevancy(question: str, answer: str) -> float:
    """
    Evaluate if the answer is relevant to the question asked.
    Answer relevancy measures if the generated answer actually addresses the question.
    """
    
    prompt = f"""
    Task: Evaluate if the answer is relevant to the question.
    
    Question:
    {question}
    
    Answer:
    {answer}
    
    Instructions:
    1. Check if the answer directly addresses the specific question asked.
    2. Consider whether the answer focuses on the main intent of the question.
    3. Rate the answer's relevancy on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating answer relevancy: {e}")
        return 5.0

async def evaluate_context_relevancy(question: str, context: str) -> float:
    """
    Evaluate if the retrieved context is relevant to the question.
    Context relevancy measures if the RAG system retrieved appropriate documents.
    """
    
    prompt = f"""
    Task: Evaluate if the retrieved context is relevant to the question.
    
    Question:
    {question}
    
    Retrieved context:
    {context[:1500]}...
    
    Instructions:
    1. Check if the retrieved context contains information needed to answer the question.
    2. Consider whether the context focuses on the topic of the question.
    3. Rate the context relevancy on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating context relevancy: {e}")
        return 5.0

async def evaluate_context_precision(question: str, answer: str, context: str) -> float:
    """
    Evaluate the precision of the retrieved context.
    Context precision measures how much of the retrieved context was actually necessary.
    """
    
    prompt = f"""
    Task: Evaluate the precision of the retrieved context relative to the question and answer.
    
    Question:
    {question}
    
    Answer:
    {answer}
    
    Retrieved context:
    {context[:1500]}...
    
    Instructions:
    1. Check what percentage of the context was actually relevant to answering the question.
    2. Consider whether there is excessive irrelevant information in the context.
    3. Rate the context precision on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 to 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating context precision: {e}")
        return 5.0

async def evaluate_answer_completeness(question: str, answer: str, context: str) -> float:
    """
    Evaluate the completeness of the answer.
    Completeness measures if the answer includes all the relevant information from the context.
    """
    
    prompt = f"""
    Task: Evaluate the completeness of the answer based on the retrieved context.
    
    Question:
    {question}
    
    Answer:
    {answer}
    
    Retrieved context:
    {context[:1500]}...
    
    Instructions:
    1. Check if the answer includes all relevant information from the context that pertains to the question.
    2. Identify any important details from the context that are missing from the answer.
    3. Rate the answer's completeness on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating answer completeness: {e}")
        return 5.0

async def evaluate_citation_quality(answer: str) -> float:
    """
    Evaluate the quality of citations in the answer.
    Citation quality measures how well the answer references the source documents.
    """
    
    prompt = f"""
    Task: Evaluate the quality of citations in the legal answer.
    
    Answer:
    {answer}
    
    Instructions:
    1. Check if the answer properly cites legal cases, statutes, or other authorities.
    2. Consider whether citations are specific and relevant.
    3. Rate the citation quality on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating citation quality: {e}")
        return 5.0

async def evaluate_legal_reasoning(question: str, answer: str) -> float:
    """
    Evaluate the quality of legal reasoning in the answer.
    Legal reasoning measures how well the answer applies legal principles.
    """
    
    prompt = f"""
    Task: Evaluate the quality of legal reasoning in the answer.
    
    Question:
    {question}
    
    Answer:
    {answer}
    
    Instructions:
    1. Check if the answer properly applies legal principles and analysis.
    2. Consider whether the reasoning is logical and considers relevant legal doctrines.
    3. Rate the quality of legal reasoning on a scale from 0 to 10.
    4. Return ONLY the numerical score between 0 and 10.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        score_text = response.text.strip()
        score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
        if score_match:
            return float(score_match.group(1))
        return 5.0
    except Exception as e:
        print(f"Error evaluating legal reasoning: {e}")
        return 5.0

async def comprehensive_evaluate(question: str, context: str, answer: str, ground_truth: str = None):
    """Run comprehensive RAG evaluation with multiple metrics."""
    # Existing implementation unchanged
    
    # Initialize with base metrics that don't need ground truth
    metrics = {}
    
    print("Evaluating faithfulness...")
    metrics["faithfulness"] = await evaluate_faithfulness(context, answer)
    
    print("Evaluating answer relevancy...")
    metrics["answer_relevancy"] = await evaluate_answer_relevancy(question, answer)
    
    print("Evaluating context relevancy...")
    metrics["context_relevancy"] = await evaluate_context_relevancy(question, context)
    
    print("Evaluating context precision...")
    metrics["context_precision"] = await evaluate_context_precision(question, answer, context)
    
    print("Evaluating answer completeness...")
    metrics["answer_completeness"] = await evaluate_answer_completeness(question, answer, context)
    
    print("Evaluating citation quality...")
    metrics["citation_quality"] = await evaluate_citation_quality(answer)
    
    print("Evaluating legal reasoning...")
    metrics["legal_reasoning"] = await evaluate_legal_reasoning(question, answer)
    
    # If ground truth is available, add golden-reference metrics
    if ground_truth:
        # Ground truth comparison
        print("Evaluating against ground truth...")
        
        # Generate ground truth answer for comparison
        ground_truth_answer = await getQueryResponse(question, ground_truth)
        
        # Semantic similarity evaluation using Gemini
        try:
            similarity_prompt = f"""
            Task: Rate the semantic similarity between these two legal texts on a scale from 0 to 10.
            
            Text 1 (Generated Answer):
            {answer}
            
            Text 2 (Ground Truth Answer):
            {ground_truth_answer}
            
            Instructions:
            1. Consider semantic meaning and legal content, not just lexical overlap.
            2. Return ONLY the numerical score between 0 and 10.
            """
            
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(similarity_prompt)
            score_text = response.text.strip()
            score_match = re.search(r'\b(\d+(\.\d+)?)\b', score_text)
            
            if score_match:
                metrics["answer_similarity"] = float(score_match.group(1))
            else:
                metrics["answer_similarity"] = 5.0
                
            metrics["ground_truth_answer"] = ground_truth_answer
        except Exception as e:
            print(f"Error evaluating answer similarity: {e}")
            metrics["answer_similarity"] = 5.0
    
    # Calculate overall weighted score
    # Higher weights for legal-specific metrics
    weights = {
        "faithfulness": 1.5,
        "answer_relevancy": 1.2,
        "context_relevancy": 1.0,
        "context_precision": 0.8,
        "answer_completeness": 1.0,
        "citation_quality": 1.5,
        "legal_reasoning": 1.5,
    }
    
    if "answer_similarity" in metrics:
        weights["answer_similarity"] = 1.0
    
    weighted_sum = sum(metrics[metric] * weights[metric] for metric in metrics if isinstance(metrics[metric], (int, float)))
    total_weight = sum(weights[metric] for metric in metrics if metric in weights and isinstance(metrics[metric], (int, float)))
    weighted_average = weighted_sum / total_weight
    
    metrics["weighted_average"] = weighted_average
    
    return metrics

async def evaluate_dataset(dataset_type: str = "judgement"):
    """Main evaluation function for a single query."""
    print(f"\n===== STARTING RAG EVALUATION FOR {dataset_type.upper()} =====\n")
    start_time = datetime.now()
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set appropriate query and ground truth based on dataset type
    if dataset_type == "judgement":
        query = "Tell me about 'Central Bureau Of Investigation vs Mohammed Yousuf on 25 January, 2016' case in detail"
        ground_truth = judgement_context
        collection_name = "judgement"
    else:  # laws
        query = "What is the procedure for filing a plaint in a civil case in India?"
        ground_truth = laws_context
        collection_name = "laws"
    
    try:
        client = await get_qdrant_client()
        qdrant_service = QdrantService(client, collection_name)
        embedder = EmbedderService()
        
        print(f"Processing query for {dataset_type} dataset: {query}")
        
        # Get embedding and search
        print("Getting query embedding...")
        query_embedding = await embedder.get_query_embedding(query)
        
        print("Searching Qdrant...")
        search_results = await qdrant_service.search_similar(query_embedding, 1)
        
        if not search_results:
            print("No search results found.")
            return {"error": f"No search results found in {dataset_type} dataset."}
        
        print(f"Found result with similarity score: {search_results[0].score}")
        
        # Extract context from search result
        payload = search_results[0].payload
        print(f"Payload keys: {list(payload.keys())}")
        
        # Extract context from this result
        result_context = None
        if "content" in payload:
            result_context = payload["content"]
        elif "text" in payload:
            result_context = payload["text"]
        else:
            # Use first string field
            for key, value in payload.items():
                if isinstance(value, str) and len(value) > 50:
                    result_context = value
                    print(f"Using field '{key}' as context")
                    break
            
            if result_context is None:
                # Fallback: convert whole payload to string
                result_context = str(payload)
                print("Using string representation of payload")
        
        if not result_context:
            print("No usable context found in search result.")
            return {"error": f"No usable context found in {dataset_type} search result."}
            
        print(f"Context length: {len(result_context)} characters")
        
        # Truncate if too large
        max_context_length = 8000  # Reasonable limit for most models
        if len(result_context) > max_context_length:
            print(f"Context too long ({len(result_context)} chars), truncating...")
            result_context = result_context[:max_context_length] + "..."
        
        # Generate answer using RAG with context
        print("Generating answer with retrieved context...")
        answer = await getQueryResponse(query, result_context, dataset_type)
        
        print(f"Answer generated: {len(answer)} characters")
        
        # Run comprehensive evaluation with ground truth
        print("Running comprehensive evaluation...")
        eval_results = await comprehensive_evaluate(query, result_context, answer, ground_truth)
        
        # Format results as pandas DataFrame for display
        metrics_df = pd.DataFrame({
            "Metric": [k for k, v in eval_results.items() if isinstance(v, (int, float))],
            "Score": [v for k, v in eval_results.items() if isinstance(v, (int, float))]
        })
        
        # Display results
        print(f"\n===== {dataset_type.upper()} EVALUATION RESULTS =====")
        print(metrics_df)
        print(f"\nWeighted Average Score: {eval_results['weighted_average']:.2f}/10")
        
        # Create results
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_type": dataset_type,
            "query": query,
            "retrieved_context": result_context[:500] + "..." if len(result_context) > 500 else result_context,
            "ground_truth": ground_truth[:500] + "..." if len(ground_truth) > 500 else ground_truth,
            "answer": answer,
            "ground_truth_answer": eval_results.get("ground_truth_answer", ""),
            "context_length": len(result_context),
            "metrics": {k: v for k, v in eval_results.items() if isinstance(v, (int, float))},
            "similarity_score": float(search_results[0].score),
            "execution_time_seconds": (datetime.now() - start_time).total_seconds()
        }
        
        # Create results directory if it doesn't exist
        os.makedirs("evaluation_results", exist_ok=True)
        
        # Save to file
        report_filename = f"evaluation_results/{dataset_type}_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\nEvaluation report saved to {report_filename}")
        
        return result
        
    except Exception as e:
        print(f"Error in {dataset_type} evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

async def evaluate_judgements_dataset():
    """Evaluate judgement dataset."""
    return await evaluate_dataset("judgement")

async def evaluate_laws_dataset():
    """Evaluate laws dataset."""
    return await evaluate_dataset("indian_laws")

async def evaluate_all_datasets():
    """Evaluate both judgement and laws datasets."""
    print("\n===== STARTING COMPREHENSIVE EVALUATION OF ALL DATASETS =====\n")
    
    judgement_results = await evaluate_judgements_dataset()
    laws_results = await evaluate_laws_dataset()
    
    # Combine results
    combined_results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "judgement_evaluation": judgement_results,
        "laws_evaluation": laws_results
    }
    
    # Save combined results
    combined_filename = f"evaluation_results/combined_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_filename, "w") as f:
        json.dump(combined_results, f, indent=2)
    
    print(f"\nCombined evaluation report saved to {combined_filename}")
    
    # Print summary
    if "error" not in judgement_results and "error" not in laws_results:
        print("\n===== EVALUATION SUMMARY =====")
        print(f"Judgement Dataset Weighted Score: {judgement_results['metrics']['weighted_average']:.2f}/10")
        print(f"Laws Dataset Weighted Score: {laws_results['metrics']['weighted_average']:.2f}/10")
        
        # Calculate combined average
        combined_avg = (judgement_results['metrics']['weighted_average'] + laws_results['metrics']['weighted_average']) / 2
        print(f"Overall Average Score: {combined_avg:.2f}/10")
    
    return combined_results
