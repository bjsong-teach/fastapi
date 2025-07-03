from fastapi import FastAPI, Query, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select, delete
from pydantic import BaseModel
from sqlalchemy.sql.sqltypes import Integer, Text, DateTime
from sqlalchemy import Column
from datetime import datetime

# database.py에서 engine만 임포트합니다. get_session은 더 이상 사용하지 않습니다.
from database import engine

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SQLModel Models ---
class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str 

class Profiles(SQLModel, table=True):
    user_id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=False))
    bio: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    phone:Optional[str] = Field(default=None, max_length=20, nullable=True)

class Posts(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    user_id: Optional[int] = Field(default=None, nullable=True)
    cnt: Optional[int] = Field(default=0, ge=0)

# --- Pydantic Models for Request/Response ---
class UserCreate(SQLModel):
    username: str
    email: str

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None

class PostCreate(SQLModel):
    title: str
    content: Optional[str] = None
    user_id: Optional[int] = None # user_id는 클라이언트가 제공하거나 추론될 수 있습니다.

class PostUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    cnt: Optional[int] = None


# --- FastAPI App Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    """
    FastAPI 애플리케이션 시작 시 실행되는 이벤트 핸들러.
    데이터베이스 테이블을 생성합니다.
    """
    logger.info("데이터베이스 테이블 생성 중...")
    SQLModel.metadata.create_all(engine)
    logger.info("데이터베이스 테이블 생성 완료.")

# --- HTML Endpoints ---
@app.get("/register/", response_class=HTMLResponse)
async def get_register_page(request: Request):
    """
    등록 HTML 페이지를 제공합니다.
    """
    return templates.TemplateResponse("register.html", {"request": request})

# --- API Endpoints for Users ---

@app.post("/users/", response_model=Users, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """
    데이터베이스에 새 사용자를 생성합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        db_user = Users.model_validate(user)
        try:
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            # 새 사용자를 위한 프로필 자동 생성
            db_profile = Profiles(user_id=db_user.id, bio="기본 자기소개", phone=None)
            session.add(db_profile)
            session.commit()
            session.refresh(db_profile)
            logger.info(f"사용자 {db_user.username} ID: {db_user.id}로 생성됨")
            return db_user
        except Exception as e:
            session.rollback()
            logger.error(f"사용자 생성 오류: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"사용자 생성 오류: {e}")

@app.get("/users/", response_model=List[Users])
async def read_users(offset: int = 0, limit: int = Query(default=100, le=100)):
    """
    페이지네이션을 사용하여 데이터베이스에서 사용자 목록을 검색합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        users = session.exec(select(Users).offset(offset).limit(limit)).all()
        return users

@app.get("/users/{user_id}", response_model=Users)
async def read_user(user_id: int):
    """
    ID로 단일 사용자를 검색합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return user

@app.patch("/users/{user_id}", response_model=Users)
async def update_user(user_id: int, user_update: UserUpdate):
    """
    기존 사용자의 정보를 업데이트합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

        # 요청에 제공된 필드 업데이트
        user_data = user_update.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user, key, value)

        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"사용자 ID {user_id} 업데이트됨.")
        return user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """
    데이터베이스에서 사용자와 연결된 프로필을 삭제합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        user = session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

        # 외래 키 제약 조건 때문에 연결된 프로필 먼저 삭제
        profile = session.get(Profiles, user_id)
        if profile:
            session.delete(profile)
            session.commit()
            logger.info(f"사용자 ID {user_id}의 프로필 삭제됨.")

        session.delete(user)
        session.commit()
        logger.info(f"사용자 ID {user_id} 삭제됨.")
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={"message": "사용자 및 연결된 프로필이 성공적으로 삭제되었습니다."})


# --- API Endpoints for Posts ---

@app.post("/posts/", response_model=Posts, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate):
    """
    데이터베이스에 새 게시물을 생성합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        # 선택 사항: user_id가 제공된 경우 유효성 검사
        if post.user_id:
            user = session.get(Users, post.user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="제공된 user_id에 해당하는 사용자를 찾을 수 없습니다.")

        db_post = Posts.model_validate(post)
        session.add(db_post)
        session.commit()
        session.refresh(db_post)
        logger.info(f"게시물 '{db_post.title}' ID: {db_post.id}로 생성됨")
        return db_post

@app.get("/posts/", response_model=List[Posts])
async def read_posts(offset: int = 0, limit: int = Query(default=100, le=100)):
    """
    페이지네이션을 사용하여 데이터베이스에서 게시물 목록을 검색합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        posts = session.exec(select(Posts).offset(offset).limit(limit)).all()
        return posts

@app.get("/posts/{post_id}", response_model=Posts)
async def read_post(post_id: int):
    """
    ID로 단일 게시물을 검색합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        post = session.get(Posts, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")
        return post

@app.patch("/posts/{post_id}", response_model=Posts)
async def update_post(post_id: int, post_update: PostUpdate):
    """
    기존 게시물의 정보를 업데이트합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        post = session.get(Posts, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")

        post_data = post_update.model_dump(exclude_unset=True)
        for key, value in post_data.items():
            setattr(post, key, value)
        post.updated_at = datetime.now() # 타임스탬프 수동 업데이트

        session.add(post)
        session.commit()
        session.refresh(post)
        logger.info(f"게시물 ID {post_id} 업데이트됨.")
        return post

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int):
    """
    ID로 게시물을 삭제합니다.
    """
    with Session(engine) as session: # 세션 직접 생성
        post = session.get(Posts, post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")

        session.delete(post)
        session.commit()
        logger.info(f"게시물 ID {post_id} 삭제됨.")
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={"message": "게시물이 성공적으로 삭제되었습니다."})
