import httpx
import json
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

from .base import ModelProvider
from ...core.logging import logger
from ...core.config import settings


class AliyunProvider(ModelProvider):
    """阿里云模型提供商"""
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "aliyun"
    
    @property
    def supported_models(self) -> List[str]:
        """从配置文件中获取支持的模型列表"""
        return settings.PROVIDER_SUPPORTED_MODELS.get("aliyun", [
            "qwen-turbo", "qwen-plus", "qwen-max", 
            "qwen3-235b-a22b", "qwen3-30b-a3b", "qwen-plus-latest", 
            "qwen-turbo-latest", "qwen-vl-max", "qwen-vl-plus"
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
            
        # 处理并规范化一些核心参数，但不删除其他自定义参数
        
        # 处理最大令牌数
        if "max_tokens" in validated:
            validated["max_tokens"] = min(int(validated["max_tokens"]), 6000)
        else:
            validated["max_tokens"] = 2048
        
        # 处理温度参数
        if "temperature" in validated:
            validated["temperature"] = max(0.0, min(float(validated["temperature"]), 1.0))
        else:
            validated["temperature"] = 0.7
        
        # 处理top_p参数
        if "top_p" in validated:
            validated["top_p"] = max(0.0, min(float(validated["top_p"]), 1.0))
        else:
            validated["top_p"] = 0.9
            
        # 处理top_k参数
        if "top_k" in validated:
            validated["top_k"] = max(1, min(int(validated["top_k"]), 100))
        
        # 处理流式输出参数
        if "stream" in validated:
            validated["stream"] = bool(validated["stream"])
        else:
            validated["stream"] = False
            
        # 处理seed参数，确保是整数
        if "seed" in validated:
            validated["seed"] = int(validated["seed"])
            
        # 处理enable_thinking参数
        if "enable_thinking" not in validated:
            validated["enable_thinking"] = False
            
        return validated
      
    async def call_model(self, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用阿里云模型
        
        Args:
            model: 模型名称
            parameters: 模型参数
            
        Returns:
            Dict[str, Any]: 模型调用结果
        """
        # 验证参数
        validated_params = await self.validate_parameters(model, parameters)
        
        # 获取API密钥和URL
        api_key = settings.ALIYUN_API_KEY
        api_url = settings.ALIYUN_API_URL
        
        if not api_key:
            raise ValueError("Aliyun API key not configured")
        
        if not api_url:
            # 使用默认API URL
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        logger.info(f"Calling Aliyun model {model}")
        
        try:
            # 准备请求数据
            request_data = {
                "model": validated_params["model"],
                "input": {
                    "messages": validated_params["messages"]
                },
                "parameters": {}
            }
            
            # 将所有除了特定排除参数之外的参数添加到请求的parameters中
            exclude_keys = ["model", "messages", "prompt"]  # 这些参数不属于parameters部分
            
            for key, value in validated_params.items():
                if key not in exclude_keys:
                    request_data["parameters"][key] = value
                    
            # 记录完整的请求参数
            logger.info(f"Request data for Aliyun API: {json.dumps(request_data, ensure_ascii=False)}")
            
            # 是否流式输出
            stream = validated_params.get("stream", False)
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-DashScope-SSE": "enable" if stream else "disable",
                "X-DashScope-DataInspection": "disable",  # 禁止数据检查
            }
            
            # 调用API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    api_url,
                    json=request_data,
                    headers=headers
                )
                
                # 检查响应状态
                response.raise_for_status()
                result = response.json()
                
                # 格式化响应结果
                return self._format_response(result, validated_params)
                
        except httpx.HTTPStatusError as e:
            error_detail = {}
            try:
                error_detail = e.response.json()
            except:
                error_detail = {"message": e.response.text}
                
            error_msg = f"Aliyun API HTTP error: {e.response.status_code}, {error_detail}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        except Exception as e:
            logger.error(f"Error calling Aliyun model: {str(e)}")
            raise ValueError(f"Aliyun API error: {str(e)}")
            
    def _format_response(self, api_response: Dict[str, Any], original_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化阿里云API响应
        
        Args:
            api_response: API原始响应
            original_params: 原始参数
            
        Returns:
            Dict[str, Any]: 格式化的响应
        """
        # 提取输出内容
        output = api_response.get("output", {})
        
        # 构建统一格式的响应
        formatted_response = {
            "id": api_response.get("request_id", str(uuid.uuid4())),
            "model": original_params.get("model", ""),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "choices": [],
            "usage": {}
        }
        
        # 添加选择项
        if "text" in output:
            formatted_response["choices"].append({
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output["text"]
                },
                "finish_reason": output.get("finish_reason", "stop")
            })
        elif "choices" in output:
            for i, choice in enumerate(output["choices"]):
                choice_data = {
                    "index": i,
                    "message": {
                        "role": "assistant",
                        "content": choice.get("message", {}).get("content", "")
                    },
                    "finish_reason": choice.get("finish_reason", "stop")
                }
                
                # 处理工具调用
                if "tool_calls" in choice.get("message", {}):
                    choice_data["message"]["tool_calls"] = choice["message"]["tool_calls"]
                    
                formatted_response["choices"].append(choice_data)
        
        # 添加使用量信息
        usage = api_response.get("usage", {})
        if usage:
            formatted_response["usage"] = {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
        return formatted_response


# 注册提供商
from . import register_provider
register_provider(AliyunProvider) 