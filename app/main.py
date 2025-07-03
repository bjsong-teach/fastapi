#./app/main.py
from fastapi import FastAPI, Query, Depends, HTTPException, status
from typing import Optional, List
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import Text 
from pydantic import BaseModel
#from app.database import create_db_and_tables, get_session
from database import engine


class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str 

class Profiles(SQLModel, table=True):
    user_id:Optional[int] = Field(default=None, primary_key=True)
    bio: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    phone:Optional[str] = Field(default=None, max_length=20, nullable=True)

class Posts(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None, sa_type=Text, nullable=True)
    user_id: Optional[int] = Field(default=None, nullable=True)
    cnt: Optional[int] = Field(default=0, ge=0)
#nullable=True

class UsersProfile(SQLModel):
    id: int
    username:str
    email:str
    # phone과 bio 필드를 최상위 레벨에 Optional로 추가
    phone: Optional[str] = None
    bio: Optional[str] = None

class UserProfile(SQLModel):
    id: int
    username:str
    email:str
    profile: Optional[Profiles] = None

app = FastAPI()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

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
@app.get("/users/{id}", response_model=Users)
def read_user(id: int):
    with Session(engine) as session:  # 세션 열기
        user = session.get(Users, id)  # ID로 조회
        if not user:  # 없으면 404 에러
            raise HTTPException(status_code=404, detail="User not found")
        return user  # 사용자 반환 
@app.get("/profiles/{user_id}", response_model=Profiles)
def read_profiles(user_id: int):
    with Session(engine) as session:  # 세션 열기
        profiles = session.get(Profiles, user_id)  # ID로 조회
        if not profiles:  # 없으면 404 에러
            raise HTTPException(status_code=404, detail="User not found")
        return profiles  # 사용자 반환 

@app.get("/profiles/all/", response_model=List[Profiles])
def read_all_profiles():
    with Session(engine) as session:  # 세션 열기
        statement = select(Profiles)
        profiles = session.exec(statement).all()
        return profiles
@app.get("/users/all/", response_model=List[Users])
def read_all_users():
    with Session(engine) as session:  # 세션 열기
        statement = select(Users)
        users = session.exec(statement).all()
        return users
    
@app.get("/users/", response_model=List[Users])
def read_paging_users(page:int=Query(1,ge=1)):
    with Session(engine) as session:  # 세션 열기
        size = 10
        offset = (page-1)*size
        statement = select(Users).offset(offset).limit(size)
        users = session.exec(statement).all()
        return users
@app.get("/posts/", response_model=List[Posts])
def read_paging_posts(page:int=Query(1,ge=1)):
    with Session(engine) as session:  # 세션 열기
        size = 10
        offset = (page-1)*size
        statement = select(Posts).offset(offset).limit(size)
        posts = session.exec(statement).all()
        return posts    
    
@app.get("/users/profile/{id}", response_model=UserProfile)
def read_user_profile(id:int):
    with Session(engine) as session:
        statement = (
            select(Users, Profiles)
            .join(Profiles, Users.id==Profiles.user_id)
            .where(Users.id==id)
        )
        result = session.exec(statement).first()
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
