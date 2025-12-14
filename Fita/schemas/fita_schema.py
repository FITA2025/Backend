from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# Room Schema
class Room(BaseModel):
    room_id: str = Field(..., min_length=4, max_length=6)

# Anchor Schema
class Anchor(BaseModel):
    room_id: str = Field(..., min_length=4, max_length=6)  # Room 참조
    anchor_id: int
    fire_dt: Optional[datetime] = None

# Anchor 응답 시 Room 정보 포함 (Nested)
class AnchorWithRoom(Anchor):
    room: Optional[Room] = None

# User Schema (DB에는 detect_obj 없음 → 별도 테이블에서 가져와 리스트로 매핑)
class User(BaseModel):
    user_id: Optional[int] = None  # AUTO_INCREMENT
    age: int = Field(..., ge=0, le=120)
    room_loc: str = Field(..., min_length=4, max_length=6)  # Room 참조
    anchor_loc: int  # Anchor 참조
    detect_obj: Optional[List[str]] = None  # user_detect_obj 테이블과 조인해서 채움

# User 응답 시 Anchor 정보 포함 (Nested)
class UserWithAnchorSchema(User):
    anchor: Optional[Anchor] = None

# Relation Schema
class RelationSchema(BaseModel):
    source_anchor_id: int  # Anchor 참조
    target_anchor_id: int  # Anchor 참조
    relation_type: Optional[str] = Field(None, max_length=50)

# Relation 응답 시 Anchor 상세 정보 포함 (Nested)
class RelationWithAnchorsSchema(RelationSchema):
    source_anchor: Optional[Anchor] = None
    target_anchor: Optional[Anchor] = None