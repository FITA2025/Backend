from fastapi import status, Form, WebSocket
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from schemas.fita_schemas import AnchorType, Anchor, User, Object
import datetime

def get_anchor(conn: Connection, uuid: str = Form(...)):
      try:
            query = f"""
            SELECT * from anchor
            WHERE uuid = :uuid
            """
            stmt = text(query)
            bind_stmt = stmt.bindparams(uuid = uuid)
            result = conn.execute(bind_stmt)

            if result.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"no anchor {uuid}")
            row = result.fetchone()
            anchor = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                            anchorTYPE=row[4], fireDT=row[5])
            result.close()
            return anchor
      except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="internal server error")
      except SQLAlchemyError as e:
           print(e)
           conn.rollback()
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="data is not delivered to DB")

def get_fire_expand(conn: Connection, uuid: str):
    try:
        center = get_anchor(conn, uuid)

        query = f"""
        SELECT uuid from anchor
        WHERE (fireDT is NULL and
         ((roomID = :roomID and anchorNUM in (:case1, :case2, :case3, :case4, :case5, :case6))
                or (anchorNUM = :anchorNUM and floor in (:floor1, :floor2) and anchorTYPE = :anchorTYPE)))
        """
        case7 = 0
        case8 = 0
        if center.anchorNUM < 35:
             case7 = center.anchorNUM + 18
        elif center.anchorNUM < 54:
             case7 = center.anchorNUM - 18
             case8 = center.anchorNUM + 16
        else:
             case7 = center.anchorNUM + 16
        
        if center.anchorTYPE == "roomgate":
             query += f"or (fireDT is NULL and (anchorTYPE = 'way' and anchorNUM = '{case7}'))"
        elif center.anchorTYPE == "way":
             query += f"or (fireDT is NULL and (anchorTYPE = 'roomgate' and anchorNUM in '{case7}', '{case8}'))"
        stmt = text(query)
        bind_stmt = stmt.bindparams(roomID = center.roomID, anchorNUM = center.anchorNUM, anchorTYPE = center.anchorTYPE,
                                    case1 = center.anchorNUM - 17, case2 = center.anchorNUM +17,
                                    case3 = center.anchorNUM - 9, case4 = center.anchorNUM + 9,
                                    case5 = center.anchorNUM - 1, case6 = center.anchorNUM + 1,
                                    floor1 = center.floor + 1, floor2 = center.floor - 1)
        result = conn.execute(bind_stmt)
        rows = result.fetchall()
        if not rows:
             return []
        all_anchors = [row[0] for row in rows]
        print(uuid, all_anchors)
        return all_anchors
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="internal server error")
    except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="data is not delivered to DB")

def get_fire_where(conn: Connection, floor: int):
     try:
        query = f"""
        SELECT uuid from anchor
        WHERE floor = :floor and fireDT IS NOT NULL
        """
        bind_stmt = text(query).bindparams(floor = floor)
        result = conn.execute(bind_stmt)
        if result.rowcount == 0:
            fire_uuid = []
        fire_uuid = [row[0] for row in result]
        result.close()
        return fire_uuid
        
     except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="internal server error")
     except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="data is not delivered to DB")

def update_fireDT(conn: Connection, uuid: str = Form(...)):
    try:
            query = f"""
            UPDATE anchor
            SET fireDT = :fireDT
            where uuid = :uuid and fireDT is NULL
            """
            bind_stmt = text(query).bindparams(uuid = uuid, fireDT = datetime.datetime.now())
            result = conn.execute(bind_stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"no anchor {uuid}")
            conn.commit()


    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="internal server error")
    except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="data is not delivered to DB")