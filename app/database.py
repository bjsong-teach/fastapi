from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# 환경 변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # DATABASE_URL이 설정되지 않은 경우 오류 발생
    raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)

logger.info(f"Database engine created for URL: {DATABASE_URL}")

# 이 파일에서는 세션 의존성 주입 함수를 제공하지 않습니다.
# 각 FastAPI 라우트에서 직접 세션을 생성해야 합니다.
