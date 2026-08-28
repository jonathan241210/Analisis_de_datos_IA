from pydantic import BaseModel, Field


class WranglingRequest(BaseModel):
    op: str
    columns: list[str] = Field(default_factory=list)
    strategy: str | None = None
    value: str | None = None
    target_type: str | None = None
    method: str | None = None
    new_name: str | None = None
    decimals: int = 0


class SupervisedRequest(BaseModel):
    target: str
    features: list[str]
    task_type: str
    algorithm: str
    test_size: float = 0.2


class UnsupervisedRequest(BaseModel):
    features: list[str]
    method: str
    max_k: int = 10
    k: int = 3
    eps: float = 0.5
    min_samples: int = 5
    n_components: int = 2


class ChatRequest(BaseModel):
    message: str
    tab: str = "eda"
    replace_last: bool = False


class AgentApplyRequest(BaseModel):
    op: str
    columns: list[str] = Field(default_factory=list)
    strategy: str | None = None
    value: str | None = None
    target_type: str | None = None
    method: str | None = None
    new_name: str | None = None


class ExecuteRequest(BaseModel):
    code: str
