from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os

#.env file load
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
#database engine 생성
engine = create_engine(DATABASE_URL, echo="True")