#Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# MySQL 클라이언트 라이브러리와 pkg-config 등 빌드 도구 설치
# apt-get update: 패키지 목록 업데이트
# apt-get install -y: 필요한 패키지 설치 (-y는 확인 질문 없이 설치)
#   default-libmysqlclient-dev: MySQL 클라이언트 개발 파일 (mysqlclient 빌드에 필요)
#   gcc: C 컴파일러 (파이썬 C 확장 모듈 빌드에 필요)
#   pkg-config: 라이브러리 정보 찾기 도구 (mysqlclient 빌드에 필요)
#   python3-dev: 파이썬 개발 헤더 파일 (파이썬 C 확장 모듈 빌드에 필요)
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev gcc pkg-config python3-dev && \
    rm -rf /var/lib/apt/lists/*   # 설치 후 캐시 파일 삭제하여 이미지 크기 줄이기

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 