from fastapi import status, Form, WebSocket
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from schemas.fita_schemas import AnchorType, Anchor, User, Object

def get_user_info(conn: Connection, userID: str):
    try:
        query = f"""
        SELECT userID, age, loc from user
        WHERE userID = :id
        """
        stmt = text(query)
        bind_stmt = stmt.bindparams(id=userID)
        result = conn.execute(bind_stmt)
        
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"해당 id {userID}는(은) 존재하지 않습니다.")

        row = result.fetchone()
        user = User(userID=row[0], age=row[1], loc=row[2])
        result.close()
        return user
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="요청하신 서비스가 잠시 내부적으로 문제가 발생하였습니다.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="알 수 없는 이유로 서비스 오류가 발생하였습니다.")
    
def get_user_obj(conn: Connection, userID: str):
    try:
        query = f"""
        SELECT userID, faucet, hydrant, extinguisher from obj
        WHERE userID = :id
        """
        stmt = text(query)
        bind_stmt = stmt.bindparams(id=userID)
        result = conn.execute(bind_stmt)
        
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"해당 id {userID}는(은) 존재하지 않습니다.")

        row = result.fetchone()
        obj = Object(userID=row[0], faucet=row[1], hydrant=row[2], extinguisher=row[3])
        result.close()
        return obj
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="요청하신 서비스가 잠시 내부적으로 문제가 발생하였습니다.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="알 수 없는 이유로 서비스 오류가 발생하였습니다.")
    
def get_user_loc(conn: Connection, userID: str):
    try:
        query = f"""
        SELECT anchor.* from anchor
        INNER JOIN user on user.loc = anchor.uuid
        WHERE userID = :id
        """
        stmt = text(query)
        bind_stmt = stmt.bindparams(id=userID)
        result = conn.execute(bind_stmt)
        
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"해당 id {userID}는(은) 존재하지 않습니다.")

        row = result.fetchone()
        loc = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                     anchorTYPE=row[4], fireDT=row[5])
        result.close()
        return loc
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="요청하신 서비스가 잠시 내부적으로 문제가 발생하였습니다.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="알 수 없는 이유로 서비스 오류가 발생하였습니다.")
    
def get_loc(conn: Connection, uuid: str):
    try:
        query = """
            SELECT * FROM anchor
            WHERE uuid = :uuid
            """
        stmt = text(query)
        bind_stmt = stmt.bindparams(uuid=uuid)
        result = conn.execute(bind_stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"해당 id {uuid}는(은) 존재하지 않습니다.")
        row = result.fetchone()
        anchor = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                     anchorTYPE=row[4], fireDT=row[5])
        result.close()
        return anchor
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="요청하신 서비스가 잠시 내부적으로 문제가 발생하였습니다.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="알 수 없는 이유로 서비스 오류가 발생하였습니다.")
    
def update_obj(conn: Connection,
               userID: str = Form(...), faucet: bool = Form(...),
               hydrant: bool = Form(...), extinguisher: bool = Form(...)):
        try:
            query = f"""
            UPDATE obj
            SET faucet = :faucet, hydrant = :hydrant, extinguisher = :extinguisher
            where userID = :userID
            """
            bind_stmt = text(query).bindparams(userID = userID, faucet = faucet,
                                               hydrant = hydrant, extinguisher = extinguisher)
            result = conn.execute(bind_stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"해당 id {userID}는(은) 존재하지 않습니다.")
            conn.commit()
            
        except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="요청데이터가 제대로 전달되지 않았습니다.")
        
def update_user(conn: Connection,
                userID: str = Form(...), loc: str = Form(...)):
        try:
            query = f"""
            UPDATE user
            SET loc =:loc
            where userID =:userID
            """
            bind_stmt = text(query).bindparams(userID = userID, loc = loc)
            result = conn.execute(bind_stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"해당 id {userID}는(은) 존재하지 않습니다.")
            conn.commit()
            
        except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="요청데이터가 제대로 전달되지 않았습니다.")