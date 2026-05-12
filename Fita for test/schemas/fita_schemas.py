from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# anchor Type
class AnchorType(str, Enum):
    normal = "normal"
    roomgate = "roomgate"
    way = "way"
    elevator = "elevator"
    toilet = "toilet"
    exit = "exit"

# anchor
class Anchor(BaseModel):
    uuid: str = Field(..., len=36)
    floor: int
    roomID: str = Field(..., min_length=5, max_length=7)
    anchorNUM: int = Field(..., ge=0, le=99)
    anchorTYPE: AnchorType
    fireDT: datetime | None = Field(default=None)

# user
class User(BaseModel):
    userID: str = Field(..., len=7)
    age: int = Field(..., ge=2, le=100)
    loc: str = Field(..., len=36)

# obj
class Object(BaseModel):
    userID: str = Field(..., len=7)
    faucet: bool = Field(default=False)
    hydrant: bool = Field(default=False)
    extinguisher: bool = Field(default=False)