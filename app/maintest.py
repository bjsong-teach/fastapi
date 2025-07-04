from fastapi import FastAPI, Query, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from sqlmodel import SQLModel, Field, select, delete # SQLModel의 select, delete 임포트
from sqlalchemy.ext.asyncio import AsyncSession # 비동기 세션 타입 힌트를 위해 임포트
from sqlalchemy.sql.sqltypes import Integer, Text # SQLAlchemy 컬럼 타입을 위해 임포트
from sqlalchemy import Column # SQLAlchemy 컬럼을 위해 임포트
from datetime import datetime

# database.py에서 비동기 세션 제공 함수와 비동기 엔진을 임포트합니다.
from database import get_session, async_engine

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- SQLModel Models ---
# SQLModel은 Pydantic BaseModel을 상속받으므로, 별도의 Pydantic 모델 정의가 필요 없습니다.
class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True) # 사용자 이름은 인덱싱되고 고유해야 함
    email: str = Field(index=True, unique=True) # 이메일은 인덱싱되고 고유해야 함

class Profiles(SQLModel, table=True):
    # user_id는 기본 키이자 외래 키 역할을 합니다.
    user_id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=False))
    bio: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    phone: Optional[str] = Field(default=None, max_length=20, nullable=True)

class Posts(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=100)
    content: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", nullable=True) # Users 테이블의 id를 참조
    cnt: Optional[int] = Field(default=0, ge=0) # 조회수
    created_at: datetime = Field(default_factory=datetime.now) # 생성 시간 자동 기록
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now}) # 업데이트 시간 자동 기록

# --- FastAPI App Setup ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def on_startup():
    """
    FastAPI 애플리케이션 시작 시 실행되는 이벤트 핸들러.
    데이터베이스 테이블을 생성합니다 (비동기).
    """
    logger.info("데이터베이스 테이블 생성 중...")
    # 비동기 엔진을 사용하여 동기 함수인 create_all을 실행합니다.
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("데이터베이스 테이블 생성 완료.")

# --- HTML Endpoints ---
@app.get("/register/", response_class=HTMLResponse)
async def get_register_page(request: Request):
    """
    등록 HTML 페이지를 제공합니다.
    """
    return templates.TemplateResponse("register.html", {"request": request})

# 사용자 정보 수정 HTML 페이지 렌더링
@app.get("/users/edit/{user_id}", response_class=HTMLResponse)
async def get_user_edit_page(request: Request, user_id: int, session: AsyncSession = Depends(get_session)):
    """
    특정 사용자의 정보 수정 페이지를 렌더링합니다.
    """
    user = await session.get(Users, user_id) # 비동기 세션 사용, await 필요
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    return templates.TemplateResponse("html_template_for_patch.html", {"request": request, "user": user})

# 프로필 수정 HTML 페이지 렌더링
@app.get("/profiles/edit/{user_id}", response_class=HTMLResponse)
async def get_profile_edit_page(request: Request, user_id: int, session: AsyncSession = Depends(get_session)):
    """
    특정 사용자의 프로필 수정 페이지를 렌더링합니다.
    """
    user = await session.get(Users, user_id) # 비동기 세션 사용, await 필요
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 사용자를 찾을 수 없습니다.")

    profile = await session.get(Profiles, user_id) # 비동기 세션 사용, await 필요
    if not profile:
        # 프로필이 없다면 기본 프로필을 생성하여 폼에 빈 값을 표시
        profile = Profiles(user_id=user_id, bio="", phone="")
        logger.info(f"사용자 ID {user_id}의 프로필을 찾을 수 없어 빈 프로필 객체 전달.")
    
    return templates.TemplateResponse("html_template_for_profile_patch.html", {"request": request, "user": user, "profile": profile})

# 프로필 조회 HTML 페이지 렌더링
@app.get("/profiles/{user_id}", response_class=HTMLResponse)
async def read_profiles_html( # 함수명 변경: API 엔드포인트와 구분
        request: Request,
        user_id: int, 
        session: AsyncSession = Depends(get_session)
    ):
    """
    특정 사용자 ID의 프로필 정보를 조회하여 HTML 페이지로 표시합니다.
    """
    logger.info(f"GET 요청 수신: /profiles/{user_id} (HTML)")
    
    profile = await session.get(Profiles, user_id) # 비동기 세션 사용, await 필요
    
    if not profile:
        logger.warning(f"프로필 조회 실패: 사용자 ID {user_id}의 프로필을 찾을 수 없습니다.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    logger.info(f"프로필 조회 성공: 사용자 ID {user_id}, 프로필 데이터: {profile.model_dump()}")
    
    return templates.TemplateResponse(
        "profile.html", # 템플릿 파일명
        {
            "request": request,
            "profile": profile # 'profiles'가 아니라 'profile' 단일 객체로 전달
        }
    )

# --- API Endpoints for Users ---

@app.post("/users/", response_model=Users, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    데이터베이스에 새 사용자를 생성합니다.
    """
    db_user = Users.model_validate(user)
    try:
        session.add(db_user) # add는 await 필요 없음
        await session.commit() # commit은 await 필요
        session.refresh(db_user) # refresh는 await 필요 없음
        
        # 새 사용자를 위한 프로필 자동 생성
        db_profile = Profiles(user_id=db_user.id, bio="기본 자기소개", phone=None)
        session.add(db_profile) # add는 await 필요 없음
        await session.commit() # commit은 await 필요
        session.refresh(db_profile) # refresh는 await 필요 없음
        
        logger.info(f"사용자 {db_user.username} ID: {db_user.id}로 생성됨")
        return db_user
    except Exception as e:
        await session.rollback() # rollback은 await 필요
        logger.error(f"사용자 생성 오류: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"사용자 생성 오류: {e}")

@app.get("/users/", response_model=List[Users])
async def read_users(offset: int = 0, limit: int = Query(default=100, le=100), session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    페이지네이션을 사용하여 데이터베이스에서 사용자 목록을 검색합니다.
    """
    users = (await session.exec(select(Users).offset(offset).limit(limit))).all() # exec에 await 필요
    return users

@app.get("/users/{user_id}", response_model=Users)
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    ID로 단일 사용자를 검색합니다.
    """
    user = await session.get(Users, user_id) # 비동기 세션 사용, await 필요
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user

@app.patch("/users/{user_id}", response_model=Users)
async def update_user(user_id: int, user_update: UserUpdate, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    기존 사용자의 정보를 업데이트합니다.
    """
    user = await session.get(Users, user_id) # 비동기 세션 사용, await 필요
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    user_data = user_update.model_dump(exclude_unset=True)
    if not user_data: # 업데이트할 필드가 없는 경우
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 필드를 제공해주세요.")

    for key, value in user_data.items():
        setattr(user, key, value)

    session.add(user) # add는 await 필요 없음
    await session.commit() # commit은 await 필요
    session.refresh(user) # refresh는 await 필요 없음
    logger.info(f"사용자 ID {user_id} 업데이트됨.")
    return user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    데이터베이스에서 사용자와 연결된 프로필을 삭제합니다.
    """
    user = await session.get(Users, user_id) # 비동기 세션 사용, await 필요
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    # 외래 키 제약 조건 때문에 연결된 프로필 먼저 삭제
    # SQLModel의 delete(Model).where(condition) 패턴 사용
    profile_statement = select(Profiles).where(Profiles.user_id == user_id)
    profile_result = await session.exec(profile_statement) # exec에 await 필요
    profile = profile_result.first()

    if profile:
        await session.delete(profile) # delete는 await 필요
        await session.commit() # commit은 await 필요
        logger.info(f"사용자 ID {user_id}의 프로필 삭제됨.")

    await session.delete(user) # delete는 await 필요
    await session.commit() # commit은 await 필요
    logger.info(f"사용자 ID {user_id} 삭제됨.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={"message": "사용자 및 연결된 프로필이 성공적으로 삭제되었습니다."})


# --- API Endpoints for Profiles ---

# 프로필 정보 업데이트 (PATCH) 엔드포인트
@app.patch("/profiles/{user_id}", response_model=Profiles)
async def update_profiles(user_id: int, profile_update: ProfileUpdate, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    기존 사용자의 프로필 정보를 업데이트합니다.
    """
    logger.info(f"PATCH 요청 수신: /profiles/{user_id} - 데이터: {profile_update.model_dump(exclude_unset=True)}")

    try:
        profile = await session.get(Profiles, user_id) # 비동기 세션 사용, await 필요

        if not profile:
            logger.warning(f"업데이트 실패: 사용자 ID {user_id}의 프로필을 찾을 수 없습니다.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로필을 찾을 수 없습니다.")

        update_data = profile_update.model_dump(exclude_unset=True)

        if not update_data:
            logger.info(f"프로필 user_id {user_id} 업데이트 시도: 변경할 데이터가 없습니다.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 필드를 제공해주세요.")

        for key, value in update_data.items():
            setattr(profile, key, value)

        session.add(profile) # add는 await 필요 없음
        await session.commit() # commit은 await 필요
        session.refresh(profile) # refresh는 await 필요 없음

        logger.info(f"프로필 user_id {user_id} 업데이트 완료. 반환 데이터: {profile.model_dump()}")
        return profile # 업데이트된 프로필 정보 반환

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback() # rollback은 await 필요
        logger.error(f"프로필 user_id {user_id} 업데이트 중 예상치 못한 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류로 프로필 정보를 업데이트할 수 없습니다.")

# --- API Endpoints for Posts ---

@app.post("/posts/", response_model=Posts, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    데이터베이스에 새 게시물을 생성합니다.
    """
    # 선택 사항: user_id가 제공된 경우 유효성 검사
    if post.user_id:
        user = await session.get(Users, post.user_id) # 비동기 세션 사용, await 필요
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="제공된 user_id에 해당하는 사용자를 찾을 수 없습니다.")

    db_post = Posts.model_validate(post)
    session.add(db_post) # add는 await 필요 없음
    await session.commit() # commit은 await 필요
    session.refresh(db_post) # refresh는 await 없음
    logger.info(f"게시물 '{db_post.title}' ID: {db_post.id}로 생성됨")
    return db_post

@app.get("/posts/", response_model=List[Posts])
async def read_posts(offset: int = 0, limit: int = Query(default=100, le=100), session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    페이지네이션을 사용하여 데이터베이스에서 게시물 목록을 검색합니다.
    """
    posts = (await session.exec(select(Posts).offset(offset).limit(limit))).all() # exec에 await 필요
    return posts

@app.get("/posts/{post_id}", response_model=Posts)
async def read_post(post_id: int, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    ID로 단일 게시물을 검색합니다.
    """
    post = await session.get(Posts, post_id) # 비동기 세션 사용, await 필요
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")
    return post

@app.patch("/posts/{post_id}", response_model=Posts)
async def update_post(post_id: int, post_update: PostUpdate, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    기존 게시물의 정보를 업데이트합니다.
    """
    post = await session.get(Posts, post_id) # 비동기 세션 사용, await 필요
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")

    post_data = post_update.model_dump(exclude_unset=True)
    if not post_data: # 업데이트할 필드가 없는 경우
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 필드를 제공해주세요.")
        
    for key, value in post_data.items():
        setattr(post, key, value)
    post.updated_at = datetime.now() # 타임스탬프 수동 업데이트 (SQLModel의 onupdate가 자동 처리할 수도 있음)

    session.add(post) # add는 await 필요 없음
    await session.commit() # commit은 await 필요
    session.refresh(post) # refresh는 await 필요 없음
    logger.info(f"게시물 ID {post_id} 업데이트됨.")
    return post

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, session: AsyncSession = Depends(get_session)): # 비동기 세션 사용
    """
    ID로 게시물을 삭제합니다.
    """
    post = await session.get(Posts, post_id) # 비동기 세션 사용, await 필요
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시물을 찾을 수 없습니다.")

    await session.delete(post) # delete는 await 필요
    await session.commit() # commit은 await 필요
    logger.info(f"게시물 ID {post_id} 삭제됨.")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={"message": "게시물이 성공적으로 삭제되었습니다."})


