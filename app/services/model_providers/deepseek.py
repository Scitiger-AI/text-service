import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from .base import ModelProvider
from ...core.logging import logger
from ...core.config import settings


class DeepSeekProvider(ModelProvider):
    """DeepSeek 模型提供商"""
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "deepseek"
    
    @property
    def supported_models(self) -> List[str]:
        """从配置文件中获取支持的模型列表"""
        return settings.PROVIDER_SUPPORTED_MODELS.get("deepseek", [
            "deepseek-chat", "deepseek-reasoner"
        ])
    
    async def validate_parameters(self, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证模型参数
        
        Args:
            model: 模型名称
            parameters: 模型参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
        """
        # 检查模型是否支持
        if model not in self.supported_models:
            supported = ", ".join(self.supported_models)
            raise ValueError(f"Model '{model}' not supported. Supported models: {supported}")
        
        # 验证必需参数
        if "prompt" not in parameters and "messages" not in parameters:
            raise ValueError("Parameter 'prompt' or 'messages' is required")
        
        # 首先复制所有原始参数，保留自定义参数
        validated = parameters.copy()
        
        # 添加模型信息
        validated["model"] = model
        
        # 处理消息参数
        if "messages" in parameters:
            validated["messages"] = parameters["messages"]
        elif "prompt" in parameters:
            # 如果提供的是prompt，转换为messages格式
            validated["messages"] = [
                {"role": "user", "content": parameters["prompt"]}
            ]
            # 移除原始prompt参数，避免与messages冲突
            if "prompt" in validated:
                del validated["prompt"]
        
        # 处理并规范化一些核心参数，但不删除其他自定义参数
        
        # 处理最大令牌数
        if "max_tokens" in validated:
            validated["max_tokens"] = min(int(validated["max_tokens"]), 32768)
        else:
            # DeepSeek默认值
            validated["max_tokens"] = 4096
        
        # 处理温度参数
        if "temperature" in validated and model != "deepseek-reasoner":
            validated["temperature"] = max(0.0, min(float(validated["temperature"]), 2.0))
        elif model != "deepseek-reasoner":
            validated["temperature"] = 0.7
        
        # 处理top_p参数
        if "top_p" in validated and model != "deepseek-reasoner":
            validated["top_p"] = max(0.0, min(float(validated["top_p"]), 1.0))
        elif model != "deepseek-reasoner":
            validated["top_p"] = 0.9
        
        # 处理流式输出参数
        if "stream" in validated:
            validated["stream"] = bool(validated["stream"])
        else:
            validated["stream"] = False
            
        # 记录完整的验证后参数
        logger.info(f"Validated parameters for DeepSeek API: {validated}")
        
        return validated
    
    async def call_model(self, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用模型
        
        Args:
            model: 模型名称
            parameters: 模型参数
            
        Returns:
            Dict[str, Any]: 模型调用结果
        """
        # 验证参数
        validated_params = await self.validate_parameters(model, parameters)
        
        # 获取API密钥
        api_key = settings.DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError("DeepSeek API key not configured")
        
        # 获取API基础URL
        base_url = settings.DEEPSEEK_API_URL or "https://api.deepseek.com"
        
        # 记录API调用
        logger.info(f"Calling DeepSeek model {model}")
        
        try:
            # 创建OpenAI客户端
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            # 调用聊天完成API
            response = await client.chat.completions.create(**validated_params)
            
            # 处理响应结果
            result = {
                "id": response.id,
                "object": response.object,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model": response.model,
                "choices": []
            }
            
            # 处理选择项
            for choice in response.choices:
                choice_data = {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content
                    },
                    "finish_reason": choice.finish_reason
                }
                
                # 处理推理内容（如果存在）
                if model == "deepseek-reasoner" and hasattr(choice.message, "reasoning_content"):
                    choice_data["message"]["reasoning_content"] = choice.message.reasoning_content
                    logger.info("Received reasoning content from DeepSeek-Reasoner")
                
                # 处理函数调用（如果存在）
                if hasattr(choice.message, "function_call") and choice.message.function_call:
                    choice_data["message"]["function_call"] = {
                        "name": choice.message.function_call.name,
                        "arguments": choice.message.function_call.arguments
                    }
                
                result["choices"].append(choice_data)
            
            # 处理使用量信息
            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            return result
                
        except Exception as e:
            logger.error(f"Error calling DeepSeek model: {str(e)}")
            raise ValueError(f"DeepSeek API error: {str(e)}")


# 注册提供商
from . import register_provider
register_provider(DeepSeekProvider) 