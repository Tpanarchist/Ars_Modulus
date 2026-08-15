import datetime
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

import orjson
from pydantic import BaseModel, Field, HttpUrl, SecretStr


def orjson_dumps(v, *, default, **kwargs):
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    return orjson.dumps(v, default=default, **kwargs).decode()


def now_tz():
    # Need datetime w/ timezone for cleanliness
    # https://stackoverflow.com/a/24666683
    return datetime.datetime.now(datetime.timezone.utc)


class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    function_call: Optional[str] = None
    received_at: datetime.datetime = Field(default_factory=now_tz)
    finish_reason: Optional[str] = None
    prompt_length: Optional[int] = None
    completion_length: Optional[int] = None
    total_length: Optional[int] = None

    def __str__(self) -> str:
        return str(self.model_dump(exclude_none=True))


class ChatSession(BaseModel):
    id: Union[str, UUID] = Field(default_factory=uuid4)
    created_at: datetime.datetime = Field(default_factory=now_tz)
    auth: Dict[str, SecretStr]
    api_url: HttpUrl
    model: str
    system: str
    params: Dict[str, Any] = {}
    messages: List[ChatMessage] = []
    input_fields: Set[str] = {}
    recent_messages: Optional[int] = None
    save_messages: Optional[bool] = True
    total_prompt_length: int = 0
    total_completion_length: int = 0
    total_length: int = 0
    title: Optional[str] = None

    def __str__(self) -> str:
        sess_start_str = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        last_message_str = self.messages[-1].received_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"""Chat session started at {sess_start_str}:
        - {len(self.messages):,} Messages
        - Last message sent at {last_message_str}"""

    def format_input_messages(
        self, system_message: ChatMessage, user_message: ChatMessage
    ) -> list:
        selected_history = select_history(
            self.messages,
            self.recent_messages,
        )

        provider_messages = lower_messages(
            system_message=system_message,
            history=selected_history,
            current_message=user_message,
            input_fields=self.input_fields,
        )

        return provider_messages

    def add_messages(
        self,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        save_messages: bool = None,
    ) -> None:
        # if save_messages is explicitly defined, always use that choice
        # instead of the default
        to_save = isinstance(save_messages, bool)

        if to_save:
            if save_messages:
                self.messages.append(user_message)
                self.messages.append(assistant_message)
        elif self.save_messages:
            self.messages.append(user_message)
            self.messages.append(assistant_message)


def select_history(
    messages: List[ChatMessage], recent_messages: Optional[int]
) -> List[ChatMessage]:
    return messages[-recent_messages:] if recent_messages else messages


def lower_messages(
    system_message: ChatMessage,
    history: List[ChatMessage],
    current_message: ChatMessage,
    input_fields: Set[str],
) -> list:
    return (
        [system_message.model_dump(include=input_fields, exclude_none=True)]
        + [
            message.model_dump(include=input_fields, exclude_none=True)
            for message in history
        ]
        + [current_message.model_dump(include=input_fields, exclude_none=True)]
    )
