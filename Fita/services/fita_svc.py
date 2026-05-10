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
                                detail=f"User {userID} does not exist.")

        row = result.fetchone()
        user = User(userID=row[0], age=row[1], loc=row[2])
        result.close()
        return user
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service went wrong.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")
    
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
                                detail=f"User {userID} does not exist.")

        row = result.fetchone()
        obj = Object(userID=row[0], faucet=row[1], hydrant=row[2], extinguisher=row[3])
        result.close()
        return obj
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service went wrong.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")
    
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
                                detail=f"User {userID} does not exist.")

        row = result.fetchone()
        loc = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                     anchorTYPE=row[4], fireDT=row[5])
        result.close()
        return loc
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service went wrong.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")
    
def get_loc(conn: Connection, uuid: str):
    try:
        query = """
            SELECT * FROM Anchor
            WHERE uuid = :uuid
            """
        stmt = text(query)
        bind_stmt = stmt.bindparams(uuid=uuid)
        result = conn.execute(bind_stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Anchor {uuid} does not exist.")
        row = result.fetchone()
        anchor = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                     anchorTYPE=row[4], fireDT=row[5])

        if anchor.anchorNUM == 80:
            query = f"""
            SELECT * FROM Anchor
            WHERE anchorNUM = 68 and floor = {anchor.floor}
            """
        elif anchor.anchorNUM == 81:
            query = f"""
            SELECT * FROM Anchor
            WHERE anchorNUM = 79 and floor = {anchor.floor}
            """
        result = conn.execute(text(query))
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Data does not exist.")
        row = result.fetchone()
        anchor = Anchor(uuid=row[0], floor=row[1], roomID=row[2], anchorNUM=row[3],
                     anchorTYPE=row[4], fireDT=row[5])
        result.close()

        return anchor
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service went wrong.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")

def get_uuid_byNUM(conn: Connection, anchorNUM: int, floor: int):
    try:
        query = f"""
            SELECT uuid from anchor
            where anchorNUM = :anchorNUM and floor = :floor
            """
        stmt = text(query)
        bind_stmt = stmt.bindparams(anchorNUM = anchorNUM, floor = floor)
        result = conn. execute (bind_stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Anchor {uuid} does not exist.")
        row = result.fetchone()
        uuid = row[0]
        result.close()
        return uuid
    
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Service went wrong.")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")
    
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
                                    detail=f"User {userID} does not exist.")
            conn.commit()
        
        except SQLAlchemyError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Service went wrong.")

        except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Data is not delivered to DB.")
        
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
                                    detail=f"User {userID} does not exist.")
            conn.commit()
            
        except SQLAlchemyError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Service went wrong.")
        except SQLAlchemyError as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Data is not delivered to DB.")
        

