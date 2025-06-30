#./app/main.py
from fastapi import FastAPI, Query
from typing import Optional

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message":"Hellow everyone"}

@app.get("/items/{item_id}")
async def read_item(item_id:int):
    return {"item_id":item_id, "message": f"아이템 번호는 {item_id}입니다."}

@app.get("/user/{user_id}/items/{item_id}")
async def read_item(user_id:int,item_id:int):
    return {"item_id":item_id, "user_id":user_id, "message": f"아이템 번호는 {item_id}, user_id는 {user_id}입니다."}

@app.get("/user/me")
async def read_user_me():
    return {"user_id":"current_user", "message":"나야 나"}

@app.get("/user/{user_id}")
async def read_user_me(user_id:int):
    return {"user_id":"current_user", "message":f"{user_id}나야 나"}



import uuid
@app.get("/products/{product_uuid}")
async def get_product_by_uuid(product_uuid:uuid.UUID):
    return {"product_uuid": str(product_uuid), "message":"product id by UUID"}




@app.get("/product/")
async def read_products(
    q: Optional[str]=None,
    short: bool=False,
    skip: int=0,
    limit:int=10
):
    results = {"skip":skip, "limit":limit}
    if q:
        results.update({"q":q})
    if not short:
        results.update({"description":"dsalfj/a;lwl"})
    return results

@app.get("/search_items/")
async def search_items(
    keyword:str= Query(...,min_length=3, max_length=50, description="검색키워드 3자에서 50자"),
    max_price:Optional[float] = Query(None, gt=0, description="최대가격이 0보다 커야한다."),
    min_price:Optional[float] = Query(None, ge=0, description="최대가격이 0보다 크거나 같아야 한다.")
):
    results = {"keyword":f"{keyword}"}
    if max_price is not None:
        results.update({"max_price":max_price})
    if min_price is not None:
        results.update({"min_price":min_price})
    return results
