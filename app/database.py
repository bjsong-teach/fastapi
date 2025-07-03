from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)  # "True" -> True