import logging
import os
from typing import Iterable, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from prompts import SYSTEM_AGENT
from app.core.config import AgentConfig, OpenAIConfig
from app.core.errors import UpstreamError
from app.core.utils import normalize_text

logger = logging.getLogger(__name__)


class ConversationAgent:
    """
    LangChain-based chat agent with optional OpenAI tool calling.
    """

    def __init__(self, openai_cfg: OpenAIConfig, agent_cfg: AgentConfig):
        key = (openai_cfg.api_key or "").strip() or os.getenv(openai_cfg.api_key_env)
        if not key:
            raise RuntimeError(
                f"Missing OpenAI API key. Set it in config.yaml or env var {openai_cfg.api_key_env}."
            )
        os.environ[openai_cfg.api_key_env] = key
        self.llm = ChatOpenAI(
            model=openai_cfg.model,
            temperature=openai_cfg.temperature,
            top_p=openai_cfg.top_p,
        )
        self.system_prompt = (agent_cfg.system_prompt or SYSTEM_AGENT).strip()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder("chat_history"),
                ("system", "Context (optional):\n{context}"),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

    def _convert_history(self, history: Optional[Iterable[dict]]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for item in history or []:
            role = (item.get("role") or "user").strip()
            content = (item.get("content") or "").strip()
            if not content:
                continue
            if role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def generate(
        self,
        user_message: str,
        history: Optional[Iterable[dict]] = None,
        context: str | None = None,
        tools: Optional[list[BaseTool]] = None,
    ) -> str:
        def to_text(value: object) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)

        history_messages = self._convert_history(history)
        context_text = (context or "").strip()
        try:
            if tools:
                agent = create_openai_tools_agent(self.llm, tools, self.prompt)
                executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=False,
                    max_iterations=3,
                )
                result = executor.invoke(
                    {
                        "input": user_message,
                        "context": context_text,
                        "chat_history": history_messages,
                    }
                )
                text = to_text(result.get("output"))
            else:
                chain = self.prompt | self.llm
                result = chain.invoke(
                    {
                        "input": user_message,
                        "context": context_text,
                        "chat_history": history_messages,
                        "agent_scratchpad": [],
                    }
                )
                text = to_text(getattr(result, "content", ""))
        except Exception:
            logger.exception("LLM request failed")
            raise UpstreamError("Upstream LLM provider error")
        return normalize_text(text)
