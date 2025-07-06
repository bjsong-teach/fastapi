#./app/main.py
from fastapi import FastAPI, Query, Depends, HTTPException, status, Request
#html 인식
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from typing import Optional, List
#sqlmodel 핵심 기능
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship, delete
from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Text, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload #selectinlload
#pydantic BaseModel 출력용으로 사용
from pydantic import BaseModel

# AsyncSessionLocal은 startup에서 데이터 삽입용
from database import engine, AsyncSessionLocal, get_session
import logging
logger = logging.getLogger(__name__) # __name__을 사용하면 모듈 이름을 로거 이름으로 가집니다.
logger.setLevel(logging.INFO) # 여기서는 INFO 레벨 이상만 기록하도록 설정


class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    profile:Optional["Profiles"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin":"Users.id == Profiles.user_id",
            "foreign_keys":"[Profiles.user_id]",
            "uselist":False,
            "cascade":"all, delete-orphan"
        }
    )

    posts:Optional["Posts"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "primaryjoin":"Users.id == Posts.user_id",
            "foreign_keys":"[Posts.user_id]",
            "uselist":False,
            "cascade":"all, delete-orphan"
        }
    )


class Profiles(SQLModel, table=True):
    #user_id:Optional[int] = Field(default=None, primary_key=True)
    user_id:Optional[int] = Field(sa_column=Column(Integer, primary_key=True, autoincrement=False))
    bio: Optional[str] = Field(sa_type=Text, nullable=True)
    phone:Optional[str] = Field(default=None, max_length=20, nullable=True)

    user:Optional["Users"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={
            "primaryjoin":"Profiles.user_id == Users.id",
            "foreign_keys":"[Profiles.user_id]",
            "uselist":False
        }
    )

class Posts(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    user_id: Optional[int] = Field(default=None, nullable=True)
    cnt: Optional[int] = Field(default=0, ge=0)
    
    user:Optional["Users"] = Relationship(
        back_populates="posts",
        sa_relationship_kwargs={
            "primaryjoin":"Posts.user_id == Users.id",
            "foreign_keys":"[Posts.user_id]",
        }
    )

#nullable=True

class UsersProfile(BaseModel):
    id: int
    username:str
    email:str
    # phone과 bio 필드를 최상위 레벨에 Optional로 추가
    phone: Optional[str] = None
    bio: Optional[str] = None

class UserProfile(BaseModel):
    id: int
    username:str
    email:str
    profile: Optional[Profiles] = None
    class config:
        from_attributes:True

class PostOutput(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    cnt: int
    class config:
        from_attributes:True
class UserPosts(BaseModel):
    id: int
    username:str
    email:str
    posts: List[PostOutput] 
    class config:
        from_attributes:True

class UserRead(BaseModel):
    id:int
    username:str
    email:str
    class config:
        from_attributes:True # orm 객체에서 속성 가져오기 허용

class ProfileRead(BaseModel):
    user_id: int
    bio:Optional[str] = None
    phone:Optional[str] = None
    class config:
        from_attributes:True # orm 객체에서 속성 가져오기 허용

class PostRead(BaseModel):
    id:int
    title:str
    content:Optional[str] = None
    user_id:Optional[int] = None
    cnt:Optional[int] = None

class UserCreate(SQLModel):
    username: str
    email: str
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None    

app = FastAPI()
templates = Jinja2Templates(directory="templates")
@app.on_event("startup")
async def on_startup():
    #SQLModel.metadata.create_all(engine)
    async with engine.begin() as conn: # 비동기 컨넥션 시작
        await conn.run_sync(SQLModel.metadata.create_all) # <-- 이 부분 수정!

@app.get("/register", response_class="HTMLResponse")
async def get_register_page(request: Request):
    return templates.TemplateResponse("register.html",{"request":request})
# 샘플 데이터 초기화
@app.post("/users/init/")
def init_users():
    sample_users = [
        Users(username=f"User{i}", email=f"user{i}@example.com") for i in range(1, 21)
    ]
    with Session(engine) as session:
        for user in sample_users:
            session.add(user)
        session.commit()
    return {"message": "20 users initialized"}

# 특정 사용자 조회 (ID로 한 명)
@app.get("/users/{id}", response_class=HTMLResponse)
async def read_user(
        request: Request,
        id: int, 
        session: Session=Depends(get_session)
    ):
    user = await session.get(Users, id)  # ID로 조회
    if not user:  # 없으면 404 에러
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        "register1.html",
        {
            "request": request,
            "user": user
        }
    )
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
    await session.refresh(user) 
    logger.info(f"사용자 ID {user_id} 업데이트됨.")
    return user    

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    """
    데이터베이스에서 사용자와 연결된 프로필을 삭제합니다.
    """
    logger.info(f"--- 사용자 ID {user_id} 삭제 프로세스 시작 ---")

    user = await session.get(Users, user_id)
    if not user:
        logger.warning(f"삭제 실패: 사용자 ID {user_id}를 찾을 수 없습니다.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    logger.info(f"✅ 1단계: 사용자 '{user.username}' (ID: {user_id}) 조회 완료.")

    # [수정] .exec() 대신 .execute() 사용
    profile_statement = select(Profiles).where(Profiles.user_id == user_id)
    result = await session.execute(profile_statement)
    profile = result.scalars().first() # .scalars()를 추가해야 합니다.

    if profile:
        await session.delete(profile)
        logger.info(f"✅ 2단계: 연결된 프로필 삭제 준비 완료.")
    else:
        logger.info(f"ℹ️ 2단계: 연결된 프로필이 없어 건너뜁니다.")

    await session.delete(user)
    logger.info(f"✅ 3단계: 사용자 '{user.username}' 삭제 준비 완료.")

    await session.commit()
    logger.info(f"✅ 4단계: 모든 변경사항을 데이터베이스에 커밋했습니다.")
    logger.info(f"--- 사용자 ID {user_id} 삭제 프로세스 성공적으로 완료 ---")

    return
'''
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

'''
@app.get("/profiles/{user_id}", response_class=HTMLResponse)
async def read_profiles(
        request: Request,
        user_id: int, 
        session: Session=Depends(get_session)
    ):
    profiles = await session.get(Profiles, user_id)  # ID로 조회
    if not profiles:  # 없으면 404 에러
        raise HTTPException(status_code=404, detail="Profile not found")
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "profiles": profiles
        }
    )
    
@app.patch("/profiles/{user_id}", response_model=Profiles)
async def update_profiles(user_id: int, session: Session=Depends(get_session)):
    profiles = await session.get(Profiles, user_id)  # ID로 조회
    if not profiles:  # 없으면 404 에러
        raise HTTPException(status_code=404, detail="Profile not found")
    return profiles  # 사용자 정보 반환 

@app.get("/post/{id}", response_model=PostRead)
async def read_profiles(id: int, session: Session=Depends(get_session)):
    post = await session.get(Posts, id)  # ID로 조회
    if not post:  # 없으면 40 4 에러
        raise HTTPException(status_code=404, detail="Post not found")
    return post  # 글 반환 

@app.get("/profiles/all/", response_class=HTMLResponse)
async def read_all_profiles(
   request: Request, 
    session: AsyncSession = Depends(get_session)
):
    statement = select(Profiles)
    result = await session.execute(statement)
    profiles = result.scalars().all()  # 꼭 scalars().all()로!
    
    return templates.TemplateResponse(
        "profile_list.html", 
        {
            "request": request,   # 여기서 request 쓰려면 인자로 받아야 함!
            "profiles": profiles
        }
    )

@app.get("/users/all/", response_class=HTMLResponse)
async def read_all_users(
    request: Request, 
    session: AsyncSession=Depends(get_session)
):
    statement = select(Users)
    result = await session.execute(statement)
    users = result.scalars().all()  # 결과에서 스칼라 객체 추출
    return templates.TemplateResponse(
        "users_list.html", 
        {
            "request": request,   # 여기서 request 쓰려면 인자로 받아야 함!
            "users": users
        }
    )
'''
@app.get("/posts/all/", response_model=List[PostRead])
async def read_all_posts(session: Session=Depends(get_session)):
    statement = select(Posts)
    result = await session.execute(statement)
    posts = result.scalars().all()  # 결과에서 스칼라 객체 추출
    return posts
'''    
@app.get("/users/", response_model=List[UserRead])
async def read_paging_users(page:int=Query(1,ge=1),session: Session=Depends(get_session)):
    size = 10
    offset = (page-1)*size
    statement = select(Users).offset(offset).limit(size)
    result = await session.execute(statement)
    users = result.scalars().all()  # 결과에서 스칼라 객체 추출
    return users
@app.post("/users/", response_model=Users, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: Session=Depends(get_session)):
    db_user = Users.model_validate(user)
    try:
        session.add(db_user)
        await session.commit()
        session.refresh(db_user)
        db_profile = Profiles(user_id=db_user.id, bio="skdmfls;lksdjfㅇㄴ말ㅇㄴㅁ;ㅣ", phone=None)
        session.add(db_profile)
        await session.commit()
        session.refresh(db_profile)
        logger.info(f"사용자 명 {db_user.username}")
        return db_user
    except Exception as e:
        session.rollback()
        logger.info(f"사용자 생성오류: {e}")
        raise HTTPException(status_code=404, detail="사용자 추가에 실패했습니다.")
@app.get("/posts/", response_model=List[PostRead])
async def read_paging_posts(page:int=Query(1,ge=1),session: Session=Depends(get_session)):
    size = 10
    offset = (page-1)*size
    statement = select(Posts).offset(offset).limit(size)
    result = await session.execute(statement)
    posts = result.scalars().all()  # 결과에서 스칼라 객체 추출
    return posts
    
@app.get("/users/profile/{id}", response_model=UserProfile)
async def read_user_profile(id:int,session: Session=Depends(get_session)):
    statement = (
        select(Users, Profiles)
        .join(Profiles, Users.id==Profiles.user_id)
        .where(Users.id==id)
    )
    result = (await session.execute(statement)).first()
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    user, profile = result
    
    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        profile=profile
    )

@app.get("/users/profile/", response_model=List[UsersProfile])
def read_paging_user_profile(page:int=Query(1,ge=1)):
    with Session(engine) as session:  # 세션 열기
        size = 10
        offset = (page-1)*size
        statement = (
            select(Users, Profiles)
            .join(Profiles, Users.id==Profiles.user_id)
            .offset(offset).limit(size)
        )
        results = session.exec(statement).all()
        user_profiles_list = []
        for user, profile in results:
            if user: # user 객체가 유효한 경우에만 처리
                # phone과 bio를 담을 변수를 None으로 초기화
                phone_data = None
                bio_data = None

                if profile: # profile 객체가 실제로 존재하는 경우
                    phone_data = profile.phone
                    bio_data = profile.bio

                # UsersProfile 모델에 맞게 데이터 구성
                user_profiles_list.append(
                    UsersProfile(
                        id=user.id,
                        username=user.username,
                        email=user.email,
                        phone=phone_data, # phone 데이터를 직접 매핑
                        bio=bio_data      # bio 데이터를 직접 매핑
                    )
                )
        return user_profiles_list # 최종 리스트 반환
        
        #select(Posts).offset(offset).limit(size)
from sqlalchemy.exc import OperationalError        
@app.get("/users/posts/{user_id}/", response_model=UserPosts)
async def read_user_posts(user_id: int, page: int = Query(1, ge=1), session: Session = Depends(get_session)):
    size = 10
    offset = (page - 1) * size

    user_stmt = select(Users).where(Users.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    posts_stmt = (
        select(Posts)
        .where(Posts.user_id == user_id)
        .offset(offset)
        .limit(size)
    )
    posts_result = await session.execute(posts_stmt)
    posts_list_from_db = posts_result.scalars().all()

    return UserPosts(
        id=user.id,
        username=user.username,
        email=user.email,
        posts=[PostOutput.model_validate(post, from_attributes=True) for post in posts_list_from_db]  
    )
