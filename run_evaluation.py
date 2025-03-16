from app.evaluators.evaluation import evaluate_all_datasets
import asyncio

if __name__ == "__main__":
    asyncio.run(evaluate_all_datasets())