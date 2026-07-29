from langchain.chat_models import init_chat_model
from configs.config import settings

def create_llm():
    model = init_chat_model(
        model="glm-4.5-air",
        model_provider="openai",
        api_key=settings.ZAI_API_KEY,
        base_url=settings.ZAI_BASE_URL,
        temperature=0.7,  # 适度创意
        max_tokens=1000,  # 限制输出长度
        timeout=30,  # 超时设置
        max_retries=2,  # 重试次数
    )
    return model