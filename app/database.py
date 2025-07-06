from dotenv import load_dotenv
import os
from sqlmodel import create_engine, Session as SQLM_Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, Session as SQLModelSession
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

# 비동기 데이터베이스 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True)

# AsyncSession 팩토리 설정
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# FastAPI의 Depends에서 사용할 비동기 세션 생성기
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session